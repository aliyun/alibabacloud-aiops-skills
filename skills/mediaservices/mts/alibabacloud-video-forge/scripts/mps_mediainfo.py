#!/usr/bin/env python3
"""
阿里云 MPS 媒体信息探测脚本

功能：
  调用 MPS SubmitMediaInfoJob API 异步获取媒体文件的基础信息，
  包括分辨率、编码格式、时长、码率、帧率、音频信息等。

重要说明：
  ⚠️ 本脚本始终使用异步模式 (async=true) 提交任务，然后轮询获取结果。
  ⚠️ 同步模式 (async=false) 容易超时，不推荐使用。

用法：
  # 使用公网 URL 探测媒体信息
  python mps_mediainfo.py --url https://example.com/video.mp4

  # 使用 OSS 对象路径探测（自动从环境变量获取 bucket）
  python mps_mediainfo.py --oss-object /input/video.mp4

  # 输出完整 JSON 格式
  python mps_mediainfo.py --url https://example.com/video.mp4 --json

  # 指定地域和管道
  python mps_mediainfo.py --url https://example.com/video.mp4 --region cn-shanghai --pipeline-id your-pipeline-id

  # Dry Run 模式（仅打印请求参数）
  python mps_mediainfo.py --url https://example.com/video.mp4 --dry-run

CLI 等价命令:
  # 异步提交 + 轮询结果 (推荐)
  aliyun mts submit-media-info-job --input '...' --pipeline-id '...' --async true
  
  # 然后轮询
  aliyun mts query-media-info-job-detail --job-id '...'

环境变量：
  ALIBABA_CLOUD_OSS_BUCKET         - OSS Bucket 名称
  ALIBABA_CLOUD_OSS_REGION         - OSS Bucket 所在地域
  
  凭证通过 alibabacloud_credentials 默认凭证链获取，请使用 'aliyun configure' 配置。
"""

import argparse
import json
import os
import sys
import time
import urllib.parse

# Import local modules
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

# SDK imports will be done in functions to allow --help without SDK installed
_sdk_available = None
_sdk_error = None

# Try to import ensure_pipeline
try:
    from mps_pipeline import ensure_pipeline
    _PIPELINE_AVAILABLE = True
except ImportError:
    _PIPELINE_AVAILABLE = False
    ensure_pipeline = None

def _check_sdk():
    global _sdk_available, _sdk_error
    if _sdk_available is None:
        try:
            from alibabacloud_credentials.client import Client as CredClient
            from alibabacloud_mts20140618.client import Client as MtsClient
            from alibabacloud_mts20140618.models import SubmitMediaInfoJobRequest
            from alibabacloud_tea_openapi.models import Config as OpenApiConfig
            _sdk_available = True
        except ImportError as e:
            _sdk_available = False
            _sdk_error = str(e)
    return _sdk_available


def _get_sdk_classes():
    """Lazy load SDK classes."""
    if not _check_sdk():
        print(f"Error: Please install Alibaba Cloud SDK: pip install alibabacloud-mts20140618 alibabacloud-credentials", file=sys.stderr)
        print(f"SDK Error: {_sdk_error}", file=sys.stderr)
        sys.exit(1)
    from alibabacloud_credentials.client import Client as CredClient
    from alibabacloud_mts20140618.client import Client as MtsClient
    from alibabacloud_mts20140618.models import SubmitMediaInfoJobRequest
    from alibabacloud_tea_openapi.models import Config as OpenApiConfig
    return CredClient, MtsClient, SubmitMediaInfoJobRequest, OpenApiConfig


def get_credentials():
    """Get Alibaba Cloud credentials using default credential chain."""
    if not _check_sdk():
        print(f"Error: Please install Alibaba Cloud SDK: pip install alibabacloud-mts20140618 alibabacloud-credentials", file=sys.stderr)
        sys.exit(1)
    
    CredClient, _, _, _ = _get_sdk_classes()
    try:
        cred = CredClient()
        return cred
    except Exception as e:
        print(f"Error: Failed to get Alibaba Cloud credentials: {e}", file=sys.stderr)
        print("Please configure credentials using 'aliyun configure' command", file=sys.stderr)
        sys.exit(1)


def create_client(region):
    """Create MPS client with timeout and user-agent configuration.
    
    Args:
        region: MPS service region
    
    Returns:
        MtsClient instance with proper configuration
    """
    CredClient, MtsClient, _, OpenApiConfig = _get_sdk_classes()
    cred = get_credentials()
    config = OpenApiConfig(
        credential=cred,
        endpoint=f"mts.{region}.aliyuncs.com",
        region_id=region,
        connect_timeout=5000,  # 5 seconds connection timeout
        read_timeout=30000,    # 30 seconds read timeout
        user_agent='AlibabaCloud-Agent-Skills',  # Required user-agent
    )
    return MtsClient(config)


def build_input(url=None, oss_object=None, region=None):
    """
    Build Input JSON for MPS job.
    
    Args:
        url: Public URL
        oss_object: OSS object path
        region: OSS region (default from ALIBABA_CLOUD_REGION env var or cn-shanghai)
    
    Returns:
        Input JSON string
    """
    if region is None:
        region = os.environ.get("ALIBABA_CLOUD_REGION", "cn-shanghai")
    if url:
        # For URL input
        return json.dumps({"URL": url})
    
    if oss_object:
        bucket = os.environ.get("ALIBABA_CLOUD_OSS_BUCKET", "")
        if not bucket:
            print("Error: ALIBABA_CLOUD_OSS_BUCKET environment variable is required for OSS object input", file=sys.stderr)
            sys.exit(1)
        
        # Build OSS location
        oss_location = f"oss-{region}"
        
        # Remove leading slash if present and URL encode the object path
        obj = oss_object.lstrip("/")
        encoded_obj = urllib.parse.quote(obj, safe='/')
        
        # Create Input JSON with OSS bucket and object
        return json.dumps({
            "Bucket": bucket,
            "Location": oss_location,
            "Object": encoded_obj
        })
    
    return None


def submit_media_info_job(client, input_json, pipeline_id=None, user_data=None, async_flag=True):
    """
    Submit media info job to MPS.
    
    Args:
        client: MtsClient instance
        input_json: Input JSON string
        pipeline_id: Pipeline ID (optional)
        user_data: User data (optional)
        async_flag: Async flag (default True) - Always use async mode to avoid timeout
    
    Returns:
        Job ID
    
    Note:
        IMPORTANT: Always use async=True for production use. Sync mode (async=False) 
        will wait for job completion but is prone to timeouts for large files.
    """
    _, _, SubmitMediaInfoJobRequest, _ = _get_sdk_classes()
    request = SubmitMediaInfoJobRequest(
        input=input_json,
        async_=async_flag  # Default True, always use async mode
    )
    
    if pipeline_id:
        request.pipeline_id = pipeline_id
    
    if user_data:
        request.user_data = user_data
    
    response = _call_with_retry(client.submit_media_info_job, request)
    result = response.body.to_map() if hasattr(response.body, 'to_map') else json.loads(response.body.to_json())

    # to_map() returns data directly without body wrapper
    media_info_job = result.get("MediaInfoJob", {})
    job_id = media_info_job.get("JobId", "") if media_info_job else ""
    if not job_id:
        raise Exception(f"Failed to get JobId from response: {result}")
    
    return job_id


def extract_media_info(result):
    """
    Extract media info from job result.
    
    Args:
        result: Job result dict
    
    Returns:
        Dict with media properties
    """
    # to_map() returns data directly without body wrapper
    # Structure: MediaInfoJobList.MediaInfoJob[0].Properties
    data = result.get("body") if "body" in result else result
    job_list = data.get("MediaInfoJobList", {}).get("MediaInfoJob", [])
    if not job_list:
        return {
            "duration": "N/A",
            "fps": "N/A",
            "bitrate": "N/A",
            "width": "N/A",
            "height": "N/A",
            "file_format": "N/A",
            "streams": {}
        }
    
    job = job_list[0]
    properties = job.get("Properties", {}) or {}
    
    info = {
        "duration": properties.get("Duration", "N/A"),
        "fps": properties.get("Fps", "N/A"),
        "bitrate": properties.get("Bitrate", "N/A"),
        "width": properties.get("Width", "N/A"),
        "height": properties.get("Height", "N/A"),
        "file_format": properties.get("FileFormat", "N/A"),
        "streams": {}
    }
    
    # Video streams
    video_streams = properties.get("VideoStreamList", {}).get("VideoStream", [])
    if video_streams:
        info["streams"]["video"] = []
        for vs in video_streams:
            info["streams"]["video"].append({
                "codec": vs.get("CodecName", "N/A"),
                "width": vs.get("Width", "N/A"),
                "height": vs.get("Height", "N/A"),
                "bitrate": vs.get("Bitrate", "N/A"),
                "fps": vs.get("Fps", "N/A"),
                "duration": vs.get("Duration", "N/A"),
                "pix_fmt": vs.get("PixFmt", "N/A"),
            })
    
    # Audio streams
    audio_streams = properties.get("AudioStreamList", {}).get("AudioStream", [])
    if audio_streams:
        info["streams"]["audio"] = []
        for aus in audio_streams:
            info["streams"]["audio"].append({
                "codec": aus.get("CodecName", "N/A"),
                "sample_rate": aus.get("SampleRate", "N/A"),
                "bitrate": aus.get("Bitrate", "N/A"),
                "channels": aus.get("Channels", "N/A"),
                "duration": aus.get("Duration", "N/A"),
            })
    
    # Subtitle streams
    subtitle_streams = properties.get("SubtitleStreamList", {}).get("SubtitleStream", [])
    if subtitle_streams:
        info["streams"]["subtitle"] = len(subtitle_streams)
    
    return info


def format_media_info(info):
    """
    Format media info for human-readable output.
    
    Args:
        info: Media info dict
    
    Returns:
        Formatted string
    """
    lines = []
    lines.append("=" * 60)
    lines.append("Media Information")
    lines.append("=" * 60)
    
    # Basic info
    lines.append(f"\nDuration: {info['duration']} seconds")
    lines.append(f"FPS: {info['fps']}")
    lines.append(f"Bitrate: {info['bitrate']} bps")
    lines.append(f"Resolution: {info['width']} x {info['height']}")
    lines.append(f"File Format: {info['file_format']}")
    
    # Video streams
    video_streams = info["streams"].get("video", [])
    if video_streams:
        lines.append("\n【Video Streams】")
        for idx, vs in enumerate(video_streams, 1):
            lines.append(f"  Video Stream #{idx}:")
            lines.append(f"    Codec: {vs['codec']}")
            lines.append(f"    Resolution: {vs['width']} x {vs['height']}")
            lines.append(f"    Bitrate: {vs['bitrate']} bps")
            lines.append(f"    FPS: {vs['fps']}")
            lines.append(f"    Duration: {vs['duration']} seconds")
            lines.append(f"    Pixel Format: {vs['pix_fmt']}")
    
    # Audio streams
    audio_streams = info["streams"].get("audio", [])
    if audio_streams:
        lines.append("\n【Audio Streams】")
        for idx, aus in enumerate(audio_streams, 1):
            lines.append(f"  Audio Stream #{idx}:")
            lines.append(f"    Codec: {aus['codec']}")
            lines.append(f"    Sample Rate: {aus['sample_rate']} Hz")
            lines.append(f"    Bitrate: {aus['bitrate']} bps")
            lines.append(f"    Channels: {aus['channels']}")
            lines.append(f"    Duration: {aus['duration']} seconds")
    
    # Subtitle streams
    subtitle_count = info["streams"].get("subtitle", 0)
    if subtitle_count:
        lines.append(f"\n【Subtitle Streams】Count: {subtitle_count}")
    
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Alibaba Cloud MPS Media Info Detection Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using public URL
  python mps_mediainfo.py --url https://example.com/video.mp4

  # Using OSS object path (auto-get bucket from env)
  python mps_mediainfo.py --oss-object /input/video.mp4

  # Output full JSON
  python mps_mediainfo.py --url https://example.com/video.mp4 --json

  # Specify region and pipeline
  python mps_mediainfo.py --url https://example.com/video.mp4 --region cn-shanghai --pipeline-id your-pipeline-id
        """
    )
    
    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--url", type=str, help="Media file public URL")
    input_group.add_argument("--oss-object", type=str, help="OSS object path (e.g., /input/video.mp4)")
    
    # Other parameters
    parser.add_argument("--region", type=str, default=None, help="MPS service region (auto-inferred from OSS input, or fallback to ALIBABA_CLOUD_REGION env var, or cn-shanghai)")
    parser.add_argument("--pipeline-id", type=str, help="Pipeline ID")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output full JSON format")
    parser.add_argument("--dry-run", action="store_true", help="Only print request parameters without calling API")
    parser.add_argument("--user-data", type=str, help="User data for the job")
    
    args = parser.parse_args()
    
    # Smart region inference: explicit --region > OSS URL/bucket > env var > default
    bucket = os.environ.get("ALIBABA_CLOUD_OSS_BUCKET")
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
    
    # Build input
    input_obj = build_input(url=args.url, oss_object=args.oss_object, region=args.region)
    
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
    
    if args.dry_run:
        print("=" * 60)
        print("[Dry Run Mode] Only print request parameters, no actual API call")
        print("=" * 60)
        print(f"Input: {input_obj.to_map()}")
        print(f"Region: {args.region}")
        print(f"Pipeline ID: {pipeline_id}")
        print(f"User Data: {args.user_data or 'Not specified'}")
        return
    
    # Print execution info
    print("=" * 60)
    print("Alibaba Cloud MPS Media Info Detection")
    print("=" * 60)
    if args.url:
        print(f"Input URL: {args.url}")
    else:
        bucket = os.environ.get("ALIBABA_CLOUD_OSS_BUCKET", "")
        print(f"Input: oss://{bucket}{args.oss_object}")
    print(f"Region: {args.region}")
    print(f"Pipeline ID: {pipeline_id}")
    print("-" * 60)
    
    # Import poll function here to allow --help without SDK
    try:
        from poll_task import poll_mps_job
    except ImportError as e:
        print(f"Error: Cannot import poll_mps_job from poll_task: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Create client and submit job
    try:
        client = create_client(args.region)
        
        # IMPORTANT: Always use async=True to avoid timeout issues
        # The job will be submitted asynchronously and then polled for completion
        job_id = submit_media_info_job(
            client, 
            input_obj, 
            pipeline_id=pipeline_id,
            user_data=args.user_data,
            async_flag=True  # Always use async mode
        )
        print(f"\nMedia info job submitted successfully!")
        print(f"Job ID: {job_id}")
        
        # Poll for job completion
        # Default timeout: 60 seconds for mediainfo tasks
        result = poll_mps_job(job_id, "mediainfo", region=args.region)
        
        if result is None:
            print("\nFailed to get job result (timeout or error)", file=sys.stderr)
            sys.exit(1)
        
        # Check job state
        # to_map() returns data directly without body wrapper
        data = result.get("body") if "body" in result else result
        job_list = data.get("MediaInfoJobList", {}).get("MediaInfoJob", [])
        job = job_list[0] if job_list else {}
        state = job.get("State", "")
        
        if state in ["Fail", "Failed"]:
            error_code = job.get("Code", "Unknown")
            error_msg = job.get("Message", "Unknown error")
            print(f"\nJob failed: {error_code} - {error_msg}", file=sys.stderr)
            sys.exit(1)
        
        # Extract and display media info
        if args.json_output:
            print("\nFull Response:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            info = extract_media_info(result)
            print("\n" + format_media_info(info))
        
    except Exception as e:
        print(f"\nRequest failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
