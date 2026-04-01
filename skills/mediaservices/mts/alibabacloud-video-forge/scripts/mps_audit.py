#!/usr/bin/env python3
"""
阿里云 MPS 内容审核脚本

功能：
  调用 MPS SubmitMediaCensorJob API 提交内容审核任务，
  调用 QueryMediaCensorJobDetail API 查询审核结果。
  
  支持审核类型：porn（涉黄）、terrorism（暴恐）、ad（广告）、
               live（直播）、logo（logo识别）、audio（音频反垃圾）

用法：
  # 对 URL 进行全类型审核（默认）
  python mps_audit.py --url https://example.com/video.mp4

  # 指定审核类型
  python mps_audit.py --url https://example.com/video.mp4 --scenes porn terrorism

  # 使用 OSS 对象作为输入
  python mps_audit.py --oss-object /input/video.mp4

  # 异步模式（不等待结果）
  python mps_audit.py --url https://example.com/video.mp4 --async

  # 查询已有任务结果
  python mps_audit.py --query-job-id your-job-id

  # Dry Run 模式
  python mps_audit.py --url https://example.com/video.mp4 --dry-run

环境变量：
  ALIBABA_CLOUD_OSS_BUCKET         - OSS Bucket 名称
  ALIBABA_CLOUD_REGION             - 阿里云区域，默认 cn-shanghai
  
  凭证通过 alibabacloud_credentials 默认凭证链获取，请使用 'aliyun configure' 配置。
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import re

# 导入本地模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load_env import ensure_env_loaded, get_region_with_inference


def validate_url(url: str) -> bool:
    """Validate URL format and security."""
    if not url:
        return False
    
    try:
        result = urllib.parse.urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False
        
        # Only allow http/https protocols
        if result.scheme not in ('http', 'https'):
            print(f"Error: Only HTTP/HTTPS URLs are supported, got: {result.scheme}", file=sys.stderr)
            return False
        
        # Prevent SSRF: block private IP addresses
        hostname = result.hostname
        if hostname:
            # Check hostname string patterns first (fast path)
            private_patterns = [
                'localhost', '127.', '10.', '172.16.', '172.17.', '172.18.',
                '172.19.', '172.20.', '172.21.', '172.22.', '172.23.',
                '172.24.', '172.25.', '172.26.', '172.27.', '172.28.',
                '172.29.', '172.30.', '172.31.', '192.168.', '0.0.0.0'
            ]
            if any(pattern in hostname for pattern in private_patterns):
                print(f"Error: URL hostname appears to be internal/private: {hostname}", file=sys.stderr)
                return False
            
            # DNS rebinding protection: resolve hostname and verify IP
            import socket
            import ipaddress
            try:
                resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_INET)
                for info in resolved_ips:
                    ip_str = info[4][0]
                    ip_obj = ipaddress.ip_address(ip_str)
                    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved:
                        print(f"Error: URL resolves to private/reserved IP: {ip_str}", file=sys.stderr)
                        return False
            except socket.gaierror:
                # DNS resolution failed, hostname may be invalid
                print(f"Error: Failed to resolve hostname: {hostname}", file=sys.stderr)
                return False
        
        return True
    except Exception:
        return False


def validate_oss_path(path: str) -> bool:
    """Validate OSS object path security."""
    if not path:
        return False
    
    path = path.strip()
    
    if not path.startswith('/'):
        print(f"Error: OSS path must start with '/', got: {path}", file=sys.stderr)
        return False
    
    if '..' in path:
        print(f"Error: OSS path contains invalid traversal sequence '..': {path}", file=sys.stderr)
        return False
    
    if path.startswith('//') or '//' in path.replace('oss://', ''):
        print(f"Error: OSS path contains invalid double slashes: {path}", file=sys.stderr)
        return False
    
    if not re.match(r'^/[a-zA-Z0-9/_\-.]+$', path):
        print(f"Error: OSS path contains invalid characters: {path}", file=sys.stderr)
        return False
    
    return True


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


# Audit scenes
AUDIT_SCENES = ["porn", "terrorism", "ad", "live", "logo", "audio"]

# Scene descriptions
SCENE_DESC = {
    "porn": "Porn detection",
    "terrorism": "Terrorism detection",
    "ad": "Ad detection",
    "live": "Live streaming detection",
    "logo": "Logo recognition",
    "audio": "Audio anti-spam",
}

# Suggestion mapping
SUGGESTION_MAP = {
    "pass": "Pass",
    "review": "Review",
    "block": "Block",
}


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
        # For URL input
        return {
            "Bucket": bucket,
            "Location": f"oss-{region}",
            "Object": url
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


def parse_scenes(scenes_list):
    """
    Parse audit scenes list.
    
    Args:
        scenes_list: List of scene strings
    
    Returns:
        List of valid scenes
    """
    if not scenes_list:
        return ["porn", "terrorism"]  # Default scenes
    
    valid_scenes = []
    for scene in scenes_list:
        scene_lower = scene.lower().strip()
        if scene_lower in AUDIT_SCENES:
            valid_scenes.append(scene_lower)
    
    return valid_scenes if valid_scenes else ["porn", "terrorism"]


def build_censor_config(scenes, output_bucket=None, output_prefix=None):
    """
    Build video censor configuration.
    
    Args:
        scenes: List of audit scenes
        output_bucket: Output OSS bucket
        output_prefix: Output file prefix
    
    Returns:
        VideoCensorConfig dict
    """
    bucket = output_bucket or os.environ.get("ALIBABA_CLOUD_OSS_BUCKET", "")
    region = os.environ.get("ALIBABA_CLOUD_REGION", "cn-shanghai")
    
    config = {
        "Scenes": scenes,
        "SaveType": "abnormal",  # Save abnormal frames only
        "BizType": "common"
    }
    
    # Output file configuration (for saving abnormal frames)
    if bucket:
        prefix = output_prefix or "audit/{Count}"
        config["OutputFile"] = {
            "Bucket": bucket,
            "Location": f"oss-{region}",
            "Object": f"{prefix}.jpg"
        }
    
    return config


def submit_censor_job(client, input_config, censor_config):
    """
    Submit media censor job.
    
    Args:
        client: MtsClient instance
        input_config: Input configuration dict
        censor_config: VideoCensorConfig dict
    
    Returns:
        Job ID
    """
    request = mts_models.SubmitMediaCensorJobRequest(
        input=json.dumps(input_config),
        video_censor_config=json.dumps(censor_config)
    )
    
    response = _call_with_retry(client.submit_media_censor_job, request)
    result = response.body.to_map() if hasattr(response.body, 'to_map') else json.loads(response.body.to_json())

    # to_map() returns data directly without body wrapper
    # SubmitMediaCensorJob returns JobId at top level
    job_id = result.get("JobId", "")
    if not job_id:
        # Fallback: check if it's in MediaCensorJob
        media_censor_job = result.get("MediaCensorJob", {})
        job_id = media_censor_job.get("JobId", "") if media_censor_job else ""
    
    return job_id, result


def query_censor_job(client, job_id):
    """
    Query media censor job detail.
    
    Args:
        client: MtsClient instance
        job_id: Job ID
    
    Returns:
        Query result dict
    """
    request = mts_models.QueryMediaCensorJobDetailRequest(
        job_id=job_id
    )
    response = _call_with_retry(client.query_media_censor_job_detail, request)
    result = response.body.to_map() if hasattr(response.body, 'to_map') else json.loads(response.body.to_json())
    return result


def format_censor_result(result, verbose=False):
    """Format censor result output with sensitive data masking.
    
    Args:
        result: Censor job result dictionary
        verbose: If True, show detailed timeline and label information
    
    Returns:
        Formatted string representation
    """
    lines = []
    
    # to_map() 返回的数据直接包含字段，没有 body 层级
    # 但为了兼容性，也检查是否有 body 层级（旧版本 SDK 或不同响应格式）
    data = result.get("body") if "body" in result else result
    job_detail = data.get("MediaCensorJobDetail", {})
    
    if not job_detail:
        return "No job detail found"
    
    state = job_detail.get("State", "")
    lines.append("=" * 60)
    lines.append("Content Audit Result")
    lines.append("=" * 60)
    lines.append(f"Job State: {state}")
    
    # Overall suggestion
    suggestion = job_detail.get("Suggestion", "")
    label = job_detail.get("Label", "")
    rate = job_detail.get("Rate", "")
    
    if suggestion:
        suggestion_display = SUGGESTION_MAP.get(suggestion, suggestion)
        lines.append(f"\nOverall Suggestion: {suggestion_display}")
    if label:
        lines.append(f"Label: {label}")
    if rate:
        lines.append(f"Confidence Rate: {rate}")
    
    # Video Censor Results (VensorCensorResult in SDK)
    video_censor = job_detail.get("VensorCensorResult", {})
    if video_censor:
        censor_results = video_censor.get("CensorResults", {}).get("CensorResult", [])
        if censor_results:
            lines.append("\nVideo Censor Results:")
            for result_item in censor_results:
                scene = result_item.get("Scene", "")
                result_suggestion = result_item.get("Suggestion", "")
                result_label = result_item.get("Label", "")
                result_rate = result_item.get("Rate", "")
                
                desc = SCENE_DESC.get(scene, scene)
                icon = "✓" if result_suggestion == "pass" else "⚠" if result_suggestion == "review" else "✗"
                
                lines.append(f"  {icon} {desc} ({scene}):")
                lines.append(f"     Suggestion: {SUGGESTION_MAP.get(result_suggestion, result_suggestion)}")
                # 非 verbose 模式下不显示详细的 label 和 rate
                if verbose:
                    if result_label:
                        lines.append(f"     Label: {result_label}")
                    if result_rate:
                        lines.append(f"     Rate: {result_rate}")
        
        # Video timelines - 仅在 verbose 模式下显示详细信息
        video_timelines = video_censor.get("VideoTimelines", {}).get("VideoTimeline", [])
        if video_timelines:
            if verbose:
                lines.append(f"\nProblematic Video Segments ({len(video_timelines)} found):")
                for idx, timeline in enumerate(video_timelines[:10], 1):  # Show first 10
                    timestamp = timeline.get("Timestamp", "")
                    timeline_results = timeline.get("CensorResults", {}).get("CensorResult", [])
                    
                    for t_result in timeline_results:
                        t_suggestion = t_result.get("Suggestion", "")
                        t_label = t_result.get("Label", "")
                        t_rate = t_result.get("Rate", "")
                        t_scene = t_result.get("Scene", "")
                        
                        line = f"  {idx}."
                        if t_scene:
                            line += f" Scene={t_scene}"
                        if t_label:
                            line += f" Label={t_label}"
                        if t_rate:
                            line += f" Rate={t_rate}"
                        line += f" Suggestion={SUGGESTION_MAP.get(t_suggestion, t_suggestion)}"
                        lines.append(line)
            else:
                # 非 verbose 模式只显示汇总信息
                lines.append(f"\nFound {len(video_timelines)} problematic segment(s) (use --verbose for details)")
            
            if len(video_timelines) > 10:
                lines.append(f"  ... and {len(video_timelines) - 10} more")
    
    # Audio Censor Results
    audio_censor = job_detail.get("AudioCensorResult", {})
    if audio_censor:
        audio_results = audio_censor.get("AudioDetailResultList", {}).get("AudioDetailResult", [])
        if audio_results:
            lines.append(f"\nAudio Censor Results ({len(audio_results)} found):")
            for idx, audio_result in enumerate(audio_results[:5], 1):
                a_suggestion = audio_result.get("Suggestion", "")
                a_label = audio_result.get("Label", "")
                a_rate = audio_result.get("Rate", "")
                a_text = audio_result.get("Text", "")
                
                line = f"  {idx}."
                if a_label:
                    line += f" Label={a_label}"
                if a_rate:
                    line += f" Rate={a_rate}"
                line += f" Suggestion={SUGGESTION_MAP.get(a_suggestion, a_suggestion)}"
                if a_text:
                    lines.append(line)
                    lines.append(f"     Text: {a_text[:100]}{'...' if len(a_text) > 100 else ''}")
                else:
                    lines.append(line)
    
    # Cover Image Censor Results
    cover_results = job_detail.get("CoverImageCensorResults", {}).get("CoverImageCensorResult", [])
    if cover_results:
        lines.append(f"\nCover Image Censor Results ({len(cover_results)} found):")
        for idx, cover in enumerate(cover_results[:5], 1):
            cover_results_list = cover.get("Results", {}).get("Result", [])
            for c_result in cover_results_list:
                c_suggestion = c_result.get("Suggestion", "")
                c_label = c_result.get("Label", "")
                c_rate = c_result.get("Rate", "")
                c_scene = c_result.get("Scene", "")
                
                line = f"  {idx}."
                if c_scene:
                    line += f" Scene={c_scene}"
                if c_label:
                    line += f" Label={c_label}"
                if c_rate:
                    line += f" Rate={c_rate}"
                line += f" Suggestion={SUGGESTION_MAP.get(c_suggestion, c_suggestion)}"
                lines.append(line)
    
    lines.append("=" * 60)
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Alibaba Cloud MPS Content Audit Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full audit (default scenes: porn, terrorism)
  python mps_audit.py --url https://example.com/video.mp4

  # Specify audit scenes
  python mps_audit.py --url https://example.com/video.mp4 --scenes porn terrorism ad

  # OSS object input
  python mps_audit.py --oss-object /input/video.mp4

  # Async mode (don't wait for result)
  python mps_audit.py --url https://example.com/video.mp4 --async

  # Query existing job result
  python mps_audit.py --query-job-id your-job-id

  # Dry Run mode
  python mps_audit.py --url https://example.com/video.mp4 --dry-run
        """
    )
    
    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--url", type=str, help="Media file public URL")
    input_group.add_argument("--oss-object", type=str, help="OSS object path (e.g., /input/video.mp4)")
    input_group.add_argument("--query-job-id", type=str, help="Query existing job result")
    
    # Audit configuration
    parser.add_argument("--scenes", type=str, nargs="+",
                        choices=AUDIT_SCENES,
                        help=f"Audit scenes, default: porn terrorism. Available: {', '.join(AUDIT_SCENES)}")
    parser.add_argument("--output-prefix", type=str, default="audit/{Count}",
                        help="Output file prefix for abnormal frames, default: audit/{Count}")
    parser.add_argument("--output-bucket", type=str, help="Output OSS Bucket name")
    
    # Other parameters
    parser.add_argument("--pipeline-id", type=str, help="MPS pipeline ID")
    parser.add_argument("--region", type=str, default=None, help="MPS service region (auto-inferred from OSS input, or fallback to ALIBABA_CLOUD_REGION env var, or cn-shanghai)")
    parser.add_argument("--async", action="store_true", help="Submit only, don't wait for result")
    parser.add_argument("--dry-run", action="store_true", help="Print request parameters only, don't call API")
    
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
    
    # Validate input parameters
    if args.url:
        if not validate_url(args.url):
            print("Error: Invalid URL format or security check failed", file=sys.stderr)
            sys.exit(1)
    
    if args.oss_object:
        if not validate_oss_path(args.oss_object):
            print("Error: Invalid OSS object path format or security check failed", file=sys.stderr)
            sys.exit(1)
    
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
        pipeline_id = ensure_pipeline(region=args.region, pipeline_type="audit")
        print(f"[Auto] Using audit pipeline: {pipeline_id}")
    
    # Query existing job
    if args.query_job_id:
        print(f"Querying job result: {args.query_job_id}")
        try:
            result = query_censor_job(client, args.query_job_id)
            print(format_censor_result(result, verbose=args.verbose))
        except Exception as e:
            print(f"Error: Query failed: {e}", file=sys.stderr)
            sys.exit(1)
        return
    
    # Build input configuration
    input_config = build_input(url=args.url, oss_object=args.oss_object)
    
    # Parse audit scenes
    scenes = parse_scenes(args.scenes)
    
    # Determine output bucket
    output_bucket = args.output_bucket or os.environ.get("ALIBABA_CLOUD_OSS_BUCKET", "")
    
    # Build censor configuration
    censor_config = build_censor_config(
        scenes=scenes,
        output_bucket=output_bucket,
        output_prefix=args.output_prefix
    )
    
    if args.dry_run:
        print("=" * 60)
        print("[Dry Run Mode] Printing request parameters only")
        print("=" * 60)
        print(f"Input: {json.dumps(input_config, ensure_ascii=False, indent=2)}")
        print(f"VideoCensorConfig: {json.dumps(censor_config, ensure_ascii=False, indent=2)}")
        print(f"Scenes: {', '.join([SCENE_DESC.get(s, s) for s in scenes])}")
        print(f"Region: {args.region}")
        return
    
    # Print execution info
    print("=" * 60)
    print("Alibaba Cloud MPS Content Audit")
    print("=" * 60)
    if args.url:
        print(f"Input URL: {args.url}")
    else:
        bucket = os.environ.get("ALIBABA_CLOUD_OSS_BUCKET", "")
        print(f"Input OSS: oss://{bucket}{args.oss_object}")
    print(f"Audit Scenes: {', '.join([SCENE_DESC.get(s, s) for s in scenes])}")
    print(f"Region: {args.region}")
    print("-" * 60)
    
    # Submit job
    try:
        job_id, result = submit_censor_job(
            client=client,
            input_config=input_config,
            censor_config=censor_config
        )
        
        print(f"Job submitted successfully!")
        print(f"  Job ID: {job_id}")
        
        # Poll for result (unless async mode)
        if not getattr(args, 'async'):
            from poll_task import poll_mps_job
            final_result = poll_mps_job(job_id, "audit", region=args.region)
            if final_result:
                print(format_censor_result(final_result, verbose=args.verbose))
        else:
            print("\nAsync mode: Job is processing in background.")
            print(f"  To check result: python scripts/poll_task.py --job-id {job_id} --job-type audit --region {args.region}")
        
    except Exception as e:
        print(f"Error: Request failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
