#!/usr/bin/env python3
"""
阿里云 MPS 视频截图脚本

功能：
  调用 MPS SubmitSnapshotJob API 提交截图任务，支持：
  - normal: 指定时间点截图
  - sprite: 雪碧图

用法：
  # 普通截图（指定时间点，单位毫秒）
  python mps_snapshot.py --url https://example.com/video.mp4 --mode normal --time 5000

  # 雪碧图
  python mps_snapshot.py --url https://example.com/video.mp4 --mode sprite

  # 使用 OSS 对象作为输入
  python mps_snapshot.py --oss-object /input/video.mp4 --mode normal --time 5000

  # 自定义输出位置和数量
  python mps_snapshot.py --url https://example.com/video.mp4 --mode normal --time 5000 \
      --count 3 --interval 10

  # 异步模式（不等待结果）
  python mps_snapshot.py --url https://example.com/video.mp4 --mode normal --time 5000 --async

  # Dry Run 模式
  python mps_snapshot.py --url https://example.com/video.mp4 --mode normal --time 5000 --dry-run

  # 自动下载截图结果到本地
  python mps_snapshot.py --oss-object /input/video.mp4 --mode normal --time 5000 --download

  # 指定本地保存目录
  python mps_snapshot.py --oss-object /input/video.mp4 --mode normal --time 5000 --download --local-dir ./covers

环境变量：
  ALIBABA_CLOUD_OSS_BUCKET         - OSS Bucket 名称（用于输入和输出）
  ALIBABA_CLOUD_REGION             - 阿里云区域，默认 cn-shanghai
  
  凭证通过 alibabacloud_credentials 默认凭证链获取，请使用 'aliyun configure' 配置。
"""

import argparse
import json
import os
import sys
import time
import urllib.parse

# 导入本地模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load_env import ensure_env_loaded, get_region_with_inference


def _is_network_error(e):
    """Check if exception is a network error."""
    error_str = str(e).lower()
    return any(keyword in error_str for keyword in [
        'timeout', 'timed out', 'connection', 'network',
        'reset by peer', 'broken pipe', 'eof', 'refused',
        'unreachable', 'sdk.serverunreachable', 'read error',
    ])


def _call_with_retry(func, *args, **kwargs):
    """Call function with retry on network errors (max 1 retry)."""
    for attempt in range(2):  # 最多尝试2次
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == 0 and _is_network_error(e):
                print("[Retry] Network error detected, retrying in 2s...")
                time.sleep(2)
                continue
            raise

# Try to import SDK modules
try:
    from alibabacloud_credentials.client import Client as CredClient
    from alibabacloud_mts20140618.client import Client as MtsClient
    from alibabacloud_mts20140618 import models as mts_models
    from alibabacloud_tea_openapi.models import Config as OpenApiConfig
    _SDK_AVAILABLE = True
except ImportError as e:
    _SDK_AVAILABLE = False
    CredClient = None
    MtsClient = None
    mts_models = None
    OpenApiConfig = None

# Try to import ensure_pipeline
try:
    from mps_pipeline import ensure_pipeline
    _PIPELINE_AVAILABLE = True
except ImportError:
    _PIPELINE_AVAILABLE = False
    ensure_pipeline = None


def get_credentials():
    """Get credentials using Alibaba Cloud default credential chain."""
    if not _SDK_AVAILABLE:
        print(f"Error: Please install Alibaba Cloud SDK: pip install alibabacloud-mts20140618 alibabacloud-credentials", file=sys.stderr)
        sys.exit(1)
    try:
        cred = CredClient()
        return cred
    except Exception as e:
        print(f"Error: Failed to get Alibaba Cloud credentials: {e}", file=sys.stderr)
        print("Please configure credentials using 'aliyun configure' command", file=sys.stderr)
        sys.exit(1)


def create_client(region):
    """Create MPS client with user-agent configuration."""
    cred = get_credentials()
    config = OpenApiConfig(
        credential=cred,
        endpoint=f"mts.{region}.aliyuncs.com",
        region_id=region,
        user_agent='AlibabaCloud-Agent-Skills',  # Required user-agent
    )
    return MtsClient(config)


def build_input(url=None, oss_object=None):
    """Build input configuration."""
    bucket = os.environ.get("ALIBABA_CLOUD_OSS_BUCKET", "")
    region = os.environ.get("ALIBABA_CLOUD_REGION", "cn-shanghai")
    
    if url:
        # For URL input, we still need to provide bucket/location for the service
        # The URL will be used as the actual input
        return {
            "Bucket": bucket,
            "Location": f"oss-{region}",
            "Object": url  # MPS can handle URL via Object field in some cases
        }
    
    if oss_object:
        if not bucket:
            print("Error: ALIBABA_CLOUD_OSS_BUCKET environment variable is required for OSS input", file=sys.stderr)
            sys.exit(1)
        # Remove leading slash if present
        obj = oss_object.lstrip("/")
        # URL encode the object path (MPS requires URL encoding for Object field)
        encoded_obj = urllib.parse.quote(obj, safe='/')
        return {
            "Bucket": bucket,
            "Location": f"oss-{region}",
            "Object": encoded_obj
        }
    
    return None


def build_snapshot_config(mode, time_ms=None, count=1, interval=10, width=None, height=None, output_bucket=None, output_prefix=None):
    """
    Build snapshot configuration.
    
    Args:
        mode: Snapshot mode (normal, sprite)
        time_ms: Time offset in milliseconds for normal mode
        count: Number of snapshots
        interval: Interval between snapshots in seconds
        width: Output width
        height: Output height
        output_bucket: Output OSS bucket
        output_prefix: Output file prefix
    
    Returns:
        SnapshotConfig dict
    """
    bucket = output_bucket or os.environ.get("ALIBABA_CLOUD_OSS_BUCKET", "")
    region = os.environ.get("ALIBABA_CLOUD_REGION", "cn-shanghai")
    
    if not bucket:
        print("Error: Output bucket is required. Set via --output-bucket or ALIBABA_CLOUD_OSS_BUCKET", file=sys.stderr)
        sys.exit(1)
    
    config = {}
    
    # Time in milliseconds
    if time_ms is not None:
        config["Time"] = str(time_ms)
    
    # Number of snapshots
    config["Num"] = str(count)
    
    # Interval between snapshots
    config["Interval"] = str(interval)
    
    # Frame type: intra = keyframe
    config["FrameType"] = "intra"
    
    # Width and height
    if width:
        config["Width"] = str(width)
    if height:
        config["Height"] = str(height)
    
    # Output file configuration
    # {Count} is a placeholder that MPS will replace with snapshot index
    prefix = output_prefix or "snapshot/snapshot_{Count}"
    config["OutputFile"] = {
        "Bucket": bucket,
        "Location": f"oss-{region}",
        "Object": f"{prefix}.jpg"
    }
    
    # Sprite configuration
    if mode == "sprite":
        config["SpriteSnapshotConfig"] = {
            "Columns": "10",
            "Rows": "10",
            "Padding": "0",
            "Margin": "0",
            "Format": "jpg",
            "Width": str(width) if width else "128",
            "Height": str(height) if height else "128"
        }
    
    return config


def submit_snapshot_job(client, input_config, snapshot_config, pipeline_id=None):
    """
    Submit snapshot job.
    
    Args:
        client: MtsClient instance
        input_config: Input configuration dict
        snapshot_config: SnapshotConfig dict
        pipeline_id: Pipeline ID (optional)
    
    Returns:
        Job ID
    """
    request = mts_models.SubmitSnapshotJobRequest(
        input=json.dumps(input_config),
        snapshot_config=json.dumps(snapshot_config),
        pipeline_id=pipeline_id
    )
    
    response = _call_with_retry(client.submit_snapshot_job, request)
    result = response.body.to_map() if hasattr(response.body, 'to_map') else json.loads(response.body.to_json())

    # to_map() returns data directly without body wrapper
    snapshot_job = result.get("SnapshotJob", {})
    job_id = snapshot_job.get("Id", "") if snapshot_job else ""
    
    return job_id, result


def format_snapshot_result(result):
    """Format snapshot result output."""
    lines = []
    
    # poll_mps_job 返回的数据结构是 {"SnapshotJobList": {"SnapshotJob": [{...}]}}
    # 需要先从 SnapshotJobList.SnapshotJob 取第一个元素
    job_list = result.get("SnapshotJobList", {}).get("SnapshotJob", [])
    job = job_list[0] if job_list else {}
    
    if not job:
        return "No job result found"
    
    state = job.get("State", "")
    lines.append(f"Job State: {state}")
    
    # Output files - check multiple possible locations
    # Location 1: SnapshotConfig.OutputFile (MPS standard response)
    snapshot_config = job.get("SnapshotConfig", {})
    snapshot_output = snapshot_config.get("OutputFile", {})
    if snapshot_output:
        lines.append(f"\nOutput File:")
        bucket = snapshot_output.get("Bucket", "")
        location = snapshot_output.get("Location", "")
        obj = snapshot_output.get("Object", "")
        if bucket and obj:
            # Construct OSS URL
            file_url = f"oss://{bucket}/{obj}"
            lines.append(f"  Bucket: {bucket}")
            lines.append(f"  Location: {location}")
            lines.append(f"  Object: {obj}")
            lines.append(f"  URL: {file_url}")
    
    # Location 2: SnapshotConfig.OutputFile.OutputFile (array format)
    output_files = snapshot_config.get("OutputFile", {}).get("OutputFile", [])
    if output_files:
        lines.append(f"\nOutput Files ({len(output_files)} total):")
        for idx, f in enumerate(output_files[:5], 1):  # Show first 5
            file_url = f.get("FileURL", "")
            if file_url:
                lines.append(f"  {idx}. URL: {file_url}")
        if len(output_files) > 5:
            lines.append(f"  ... and {len(output_files) - 5} more")
    
    # Location 3: Direct OutputFile
    output_file = job.get("OutputFile", {})
    if output_file and not snapshot_output and not output_files:
        lines.append(f"\nOutput Files:")
        file_url = output_file.get("FileURL", "")
        if file_url:
            lines.append(f"  URL: {file_url}")
    
    # Sprite output
    sprite_output = job.get("SpriteOutput", {})
    if sprite_output:
        lines.append("\nSprite Output:")
        lines.append(f"  URL: {sprite_output.get('FileURL', 'N/A')}")
        lines.append(f"  Format: {sprite_output.get('Format', 'N/A')}")
    
    # Snapshot list
    snapshot_list = job.get("SnapshotList", [])
    if snapshot_list:
        lines.append(f"\nSnapshots ({len(snapshot_list)} total):")
        for idx, snapshot in enumerate(snapshot_list[:5], 1):  # Show first 5
            url = snapshot.get("FileURL", "")
            time_offset = snapshot.get("Time", "")
            lines.append(f"  {idx}. Time: {time_offset}ms, URL: {url}")
        if len(snapshot_list) > 5:
            lines.append(f"  ... and {len(snapshot_list) - 5} more")
    
    return "\n".join(lines)


def download_snapshots(result, local_dir, region):
    """
    Download snapshot results from OSS to local directory.
    
    Args:
        result: Snapshot job result dict
        local_dir: Local directory to save files
        region: Alibaba Cloud region
    """
    try:
        from oss_download import download_file
        from load_env import get_oss_auth
    except ImportError:
        print("\n[Warning] oss_download.py not found. Cannot auto download.", file=sys.stderr)
        print("  Please download manually using: python scripts/oss_download.py --oss-key <key> --local-file <path>", file=sys.stderr)
        return
    
    # poll_mps_job 返回的数据结构是 {"SnapshotJobList": {"SnapshotJob": [{...}]}}
    # 需要先从 SnapshotJobList.SnapshotJob 取第一个元素
    job_list = result.get("SnapshotJobList", {}).get("SnapshotJob", [])
    job = job_list[0] if job_list else {}
    if not job:
        print("\n[Warning] No job result found, skipping download.", file=sys.stderr)
        return
    
    # Get OSS config from environment
    bucket = os.environ.get("ALIBABA_CLOUD_OSS_BUCKET", "")
    endpoint = os.environ.get("ALIBABA_CLOUD_OSS_ENDPOINT", f"oss-{region}.aliyuncs.com")
    
    if not bucket:
        print("\n[Warning] Missing OSS bucket config for download.", file=sys.stderr)
        return
    
    # Get OSS auth using alibabacloud_credentials
    try:
        auth = get_oss_auth()
    except SystemExit:
        print("\n[Warning] Cannot get OSS credentials for download.", file=sys.stderr)
        return
    
    # Collect all snapshot URLs to download
    files_to_download = []
    
    # Location 1: From SnapshotConfig.OutputFile (MPS standard response)
    snapshot_config = job.get("SnapshotConfig", {})
    snapshot_output = snapshot_config.get("OutputFile", {})
    if snapshot_output:
        obj = snapshot_output.get("Object", "")
        if obj:
            files_to_download.append((obj, "snapshot.jpg"))
    
    # Location 2: From SnapshotConfig.OutputFile.OutputFile (array format with FileURL)
    if not files_to_download:
        output_files = snapshot_config.get("OutputFile", {}).get("OutputFile", [])
        for idx, f in enumerate(output_files):
            url = f.get("FileURL", "")
            if url:
                try:
                    parsed = urllib.parse.urlparse(url)
                    path = parsed.path.lstrip('/')
                    if path.startswith(bucket + '/'):
                        oss_key = path[len(bucket)+1:]
                    else:
                        oss_key = path
                    files_to_download.append((oss_key, f"snapshot_{idx+1}.jpg"))
                except Exception:
                    if f"{bucket}.{endpoint}" in url:
                        oss_key = url.split(f"{bucket}.{endpoint}/")[-1]
                        files_to_download.append((oss_key, f"snapshot_{idx+1}.jpg"))
    
    # Location 3: From SnapshotList
    if not files_to_download:
        snapshot_list = job.get("SnapshotList", [])
        for idx, snapshot in enumerate(snapshot_list):
            url = snapshot.get("FileURL", "")
            time_offset = snapshot.get("Time", "")
            if url:
                # Extract OSS key from URL
                # URL format: https://bucket.endpoint/object-key
                try:
                    # Parse URL to get object key
                    parsed = urllib.parse.urlparse(url)
                    path = parsed.path.lstrip('/')
                    # Remove bucket name from path if present
                    if path.startswith(bucket + '/'):
                        oss_key = path[len(bucket)+1:]
                    else:
                        oss_key = path
                    files_to_download.append((oss_key, f"snapshot_{time_offset}ms.jpg"))
                except Exception:
                    # Fallback: try to extract key from URL directly
                    if f"{bucket}.{endpoint}" in url:
                        oss_key = url.split(f"{bucket}.{endpoint}/")[-1]
                        files_to_download.append((oss_key, f"snapshot_{time_offset}ms.jpg"))
    
    # Location 4: From OutputFile (fallback for normal mode)
    if not files_to_download:
        output_file = job.get("OutputFile", {})
        file_url = output_file.get("FileURL", "")
        if file_url:
            try:
                parsed = urllib.parse.urlparse(file_url)
                path = parsed.path.lstrip('/')
                if path.startswith(bucket + '/'):
                    oss_key = path[len(bucket)+1:]
                else:
                    oss_key = path
                files_to_download.append((oss_key, "snapshot.jpg"))
            except Exception:
                if f"{bucket}.{endpoint}" in file_url:
                    oss_key = file_url.split(f"{bucket}.{endpoint}/")[-1]
                    files_to_download.append((oss_key, "snapshot.jpg"))
    
    # From SpriteOutput
    sprite_output = job.get("SpriteOutput", {})
    sprite_url = sprite_output.get("FileURL", "")
    if sprite_url:
        try:
            parsed = urllib.parse.urlparse(sprite_url)
            path = parsed.path.lstrip('/')
            if path.startswith(bucket + '/'):
                oss_key = path[len(bucket)+1:]
            else:
                oss_key = path
            files_to_download.append((oss_key, "sprite.jpg"))
        except Exception:
            if f"{bucket}.{endpoint}" in sprite_url:
                oss_key = sprite_url.split(f"{bucket}.{endpoint}/")[-1]
                files_to_download.append((oss_key, "sprite.jpg"))
    
    if not files_to_download:
        print("\n[Warning] No snapshot files found to download.", file=sys.stderr)
        return
    
    # Create local directory
    os.makedirs(local_dir, exist_ok=True)
    
    print(f"\n[Download] Downloading {len(files_to_download)} snapshot(s) to {local_dir}...")
    
    downloaded_files = []
    for oss_key, local_name in files_to_download:
        local_path = os.path.join(local_dir, local_name)
        print(f"  Downloading: {oss_key} -> {local_path}")
        result = download_file(
            oss_key=oss_key,
            local_file=local_path,
            bucket_name=bucket,
            endpoint=endpoint,
            auth=auth,
            sign_url_only=False,
            dry_run=False,
            verbose=False
        )
        if result:
            downloaded_files.append(local_path)
            print(f"    ✓ Success")
        else:
            print(f"    ✗ Failed")
    
    print(f"\n[Download] Completed: {len(downloaded_files)}/{len(files_to_download)} files downloaded to {local_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Alibaba Cloud MPS Video Snapshot Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Normal snapshot at 5 seconds (5000ms)
  python mps_snapshot.py --url https://example.com/video.mp4 --mode normal --time 5000

  # Sprite (thumbnail grid)
  python mps_snapshot.py --url https://example.com/video.mp4 --mode sprite

  # OSS object input
  python mps_snapshot.py --oss-object /input/video.mp4 --mode normal --time 5000

  # Multiple snapshots with custom interval
  python mps_snapshot.py --url https://example.com/video.mp4 --mode normal --time 5000 --count 5 --interval 10

  # Custom output size
  python mps_snapshot.py --url https://example.com/video.mp4 --mode normal --time 5000 --width 1280 --height 720

  # Async mode (don't wait for result)
  python mps_snapshot.py --url https://example.com/video.mp4 --mode normal --time 5000 --async

  # Auto download snapshot results to local
  python mps_snapshot.py --oss-object /input/video.mp4 --mode normal --time 5000 --download

  # Download to custom directory
  python mps_snapshot.py --oss-object /input/video.mp4 --mode normal --time 5000 --download --local-dir ./covers
        """
    )
    
    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--url", type=str, help="Media file public URL")
    input_group.add_argument("--oss-object", type=str, help="OSS object path (e.g., /input/video.mp4)")
    
    # Mode selection
    parser.add_argument("--mode", type=str, choices=["normal", "sprite"],
                        default="normal", help="Snapshot mode: normal=single point | sprite=thumbnail grid")
    parser.add_argument("--time", type=int, help="Snapshot time point in milliseconds (for normal mode)")
    parser.add_argument("--count", type=int, default=1, help="Number of snapshots, default 1")
    parser.add_argument("--interval", type=int, default=10, help="Interval between snapshots in seconds, default 10")
    
    # Output configuration
    parser.add_argument("--width", type=int, help="Output width in pixels")
    parser.add_argument("--height", type=int, help="Output height in pixels")
    parser.add_argument("--output-prefix", type=str, default="snapshot/{Count}",
                        help="Output file prefix, default: snapshot/{Count}")
    parser.add_argument("--output-bucket", type=str, help="Output OSS Bucket name")
    
    # Other parameters
    parser.add_argument("--pipeline-id", type=str, help="MPS pipeline ID")
    parser.add_argument("--region", type=str, default=None, help="MPS service region (auto-inferred from OSS input, or fallback to ALIBABA_CLOUD_REGION env var, or cn-shanghai)")
    parser.add_argument("--async", action="store_true", help="Submit only, don't wait for result")
    parser.add_argument("--dry-run", action="store_true", help="Print request parameters only, don't call API")
    
    # Download parameters
    parser.add_argument("--download", action="store_true", help="Auto download snapshot results to local after job completes")
    parser.add_argument("--local-dir", type=str, default="./output", help="Local directory to save downloaded snapshots (default: ./output)")
    
    args = parser.parse_args()
    
    # Smart region inference: explicit --region > OSS URL/bucket > env var > default
    bucket = args.output_bucket or os.environ.get("ALIBABA_CLOUD_OSS_BUCKET")
    endpoint = os.environ.get("ALIBABA_CLOUD_OSS_ENDPOINT")
    region = get_region_with_inference(
        explicit_region=args.region,
        url=args.url,
        endpoint=endpoint,
        bucket=bucket,
    )
    args.region = region
    
    # Ensure environment variables are loaded
    if not ensure_env_loaded(verbose=False):
        from load_env import _print_setup_hint
        _print_setup_hint([])
        sys.exit(1)
    
    # Create client
    client = create_client(args.region)
    
    # Determine pipeline_id: use provided or auto-select
    if args.pipeline_id:
        pipeline_id = args.pipeline_id
    else:
        if not _PIPELINE_AVAILABLE:
            print("Error: --pipeline-id not specified and ensure_pipeline not available.", file=sys.stderr)
            print("Please either specify --pipeline-id or ensure mps_pipeline.py is available.", file=sys.stderr)
            sys.exit(1)
        pipeline_id = ensure_pipeline(region=args.region, pipeline_type="standard")
        print(f"[Auto] Using standard pipeline: {pipeline_id}")
    
    # Build input configuration
    input_config = build_input(url=args.url, oss_object=args.oss_object)
    
    # Determine output bucket
    output_bucket = args.output_bucket or os.environ.get("ALIBABA_CLOUD_OSS_BUCKET", "")
    
    # Normal mode requires time parameter
    if args.mode == "normal" and args.time is None:
        parser.error("--mode normal requires --time parameter (snapshot time in milliseconds)")
    
    # Build snapshot configuration
    snapshot_config = build_snapshot_config(
        mode=args.mode,
        time_ms=args.time,
        count=args.count,
        interval=args.interval,
        width=args.width,
        height=args.height,
        output_bucket=output_bucket,
        output_prefix=args.output_prefix
    )
    
    if args.dry_run:
        print("=" * 60)
        print("[Dry Run Mode] Printing request parameters only")
        print("=" * 60)
        print(f"Input: {json.dumps(input_config, ensure_ascii=False, indent=2)}")
        print(f"SnapshotConfig: {json.dumps(snapshot_config, ensure_ascii=False, indent=2)}")
        print(f"Pipeline ID: {pipeline_id}")
        print(f"Region: {args.region}")
        return
    
    # Print execution info
    print("=" * 60)
    print("Alibaba Cloud MPS Video Snapshot")
    print("=" * 60)
    if args.url:
        print(f"Input URL: {args.url}")
    else:
        bucket = os.environ.get("ALIBABA_CLOUD_OSS_BUCKET", "")
        print(f"Input OSS: oss://{bucket}{args.oss_object}")
    print(f"Mode: {args.mode}")
    if args.mode == "normal":
        print(f"Time: {args.time}ms")
    print(f"Count: {args.count}")
    print(f"Interval: {args.interval}s")
    print(f"Region: {args.region}")
    print("-" * 60)
    
    # Submit job
    try:
        job_id, result = submit_snapshot_job(
            client=client,
            input_config=input_config,
            snapshot_config=snapshot_config,
            pipeline_id=pipeline_id
        )
        
        print(f"Job submitted successfully!")
        print(f"  Job ID: {job_id}")
        
        # Poll for result (unless async mode)
        if not getattr(args, 'async'):
            from poll_task import poll_mps_job
            final_result = poll_mps_job(job_id, "snapshot", region=args.region)
            if final_result:
                print("\nJob Result:")
                print(format_snapshot_result(final_result))
                
                # Auto download if requested
                if args.download:
                    download_snapshots(final_result, args.local_dir, args.region)
        else:
            print("\nAsync mode: Job is processing in background.")
            print(f"  To check result: python scripts/poll_task.py --job-id {job_id} --job-type snapshot --region {args.region}")
            if args.download:
                print(f"  Note: --download is ignored in async mode. Run poll_task.py first, then use oss_download.py to download.")
        
    except Exception as e:
        print(f"Error: Request failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
