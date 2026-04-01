#!/usr/bin/env python3
"""
阿里云 MPS 智能标签分析脚本

功能：
  调用 MPS SubmitSmarttagJob API 对视频进行智能标签分析，
  包括视频标签、文字标签、元数据、ASR 语音识别、OCR 文字识别等。

用法：
  # 使用公网 URL 分析视频
  python mps_smarttag.py --url https://example.com/video.mp4 --title "Video Title"

  # 使用 OSS 对象路径分析
  python mps_smarttag.py --oss-object /input/video.mp4 --title "Video Title"

  # 启用 ASR 和 OCR
  python mps_smarttag.py --url https://example.com/video.mp4 --title "Video Title" --enable-asr --enable-ocr

  # 指定语言和模板
  python mps_smarttag.py --url https://example.com/video.mp4 --title "Video Title" --language en --template-id your-template-id

  # 输出完整 JSON 格式
  python mps_smarttag.py --url https://example.com/video.mp4 --title "Video Title" --json

  # Dry Run 模式（仅打印请求参数）
  python mps_smarttag.py --url https://example.com/video.mp4 --title "Video Title" --dry-run

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
            from alibabacloud_mts20140618.models import SubmitSmarttagJobRequest
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
    from alibabacloud_mts20140618.models import SubmitSmarttagJobRequest
    from alibabacloud_tea_openapi.models import Config as OpenApiConfig
    return CredClient, MtsClient, SubmitSmarttagJobRequest, OpenApiConfig


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
    """Create MPS client with user-agent configuration."""
    CredClient, MtsClient, _, OpenApiConfig = _get_sdk_classes()
    cred = get_credentials()
    config = OpenApiConfig(
        credential=cred,
        endpoint=f"mts.{region}.aliyuncs.com",
        region_id=region,
        user_agent='AlibabaCloud-Agent-Skills',  # Required user-agent
    )
    return MtsClient(config)


def build_input_url(url=None, oss_object=None):
    """
    Build input URL for smarttag job.
    
    Args:
        url: Public URL
        oss_object: OSS object path
    
    Returns:
        Input URL string
    """
    if url:
        return url
    
    if oss_object:
        bucket = os.environ.get("ALIBABA_CLOUD_OSS_BUCKET", "")
        if not bucket:
            print("Error: ALIBABA_CLOUD_OSS_BUCKET environment variable is required for OSS object input", file=sys.stderr)
            sys.exit(1)
        # Remove leading slash if present and URL encode the path
        obj = oss_object.lstrip("/")
        encoded_obj = urllib.parse.quote(obj, safe='/')
        # Return oss://bucket/path format
        return f"oss://{bucket}/{encoded_obj}"
    
    return None


def build_params(enable_asr=False, enable_ocr=False, language="cn", summarization=False):
    """
    Build params JSON for smarttag job.
    
    Args:
        enable_asr: Whether to enable ASR
        enable_ocr: Whether to enable OCR
        language: Source language (cn/en/yue)
        summarization: Whether to enable summarization
    
    Returns:
        Params JSON string
    """
    params = {}
    
    if enable_asr:
        params["needAsrData"] = True
    
    if enable_ocr:
        params["needOcrData"] = True
    
    # NLP params
    nlp_params = {}
    if language:
        nlp_params["sourceLanguage"] = language
    if summarization:
        nlp_params["summarizationEnabled"] = True
    
    if nlp_params:
        params["nlpParams"] = nlp_params
    
    return json.dumps(params) if params else None


def submit_smarttag_job(client, input_url, title, pipeline_id, content=None, 
                        template_id=None, params=None, notify_url=None, user_data=None):
    """
    Submit smarttag job to MPS.
    
    Args:
        client: MtsClient instance
        input_url: Input URL (oss://bucket/path, http://..., or vod://MediaId)
        title: Video title for NLP analysis
        pipeline_id: Pipeline ID (required)
        content: Video description (optional)
        template_id: Analysis template ID (optional)
        params: Params JSON string (optional)
        notify_url: Callback URL (optional)
        user_data: User data (optional)
    
    Returns:
        Job ID
    """
    _, _, SubmitSmarttagJobRequest, _ = _get_sdk_classes()
    request = SubmitSmarttagJobRequest(
        input=input_url,
        title=title,
        pipeline_id=pipeline_id
    )
    
    if content:
        request.content = content
    
    if template_id:
        request.template_id = template_id
    
    if params:
        request.params = params
    
    if notify_url:
        request.notify_url = notify_url
    
    if user_data:
        request.user_data = user_data
    
    response = _call_with_retry(client.submit_smarttag_job, request)
    result = response.body.to_map() if hasattr(response.body, 'to_map') else json.loads(response.body.to_json())

    # to_map() returns data directly without body wrapper
    job_id = result.get("JobId", "")
    if not job_id:
        raise Exception(f"Failed to get JobId from response: {result}")
    
    return job_id


def format_smarttag_result(result):
    """
    Format smarttag result for human-readable output.
    
    Args:
        result: Job result dict
    
    Returns:
        Formatted string
    """
    lines = []
    lines.append("=" * 60)
    lines.append("Smart Tag Analysis Results")
    lines.append("=" * 60)
    
    body = result.get("body", {}) or {}
    results = body.get("Results", [])
    
    if not results:
        lines.append("\nNo analysis results found.")
        return "\n".join(lines)
    
    for result_item in results:
        result_type = result_item.get("Type", "Unknown")
        data = result_item.get("Data", "{}")
        
        try:
            data_obj = json.loads(data) if isinstance(data, str) else data
        except json.JSONDecodeError:
            data_obj = {}
        
        lines.append(f"\n【{result_type}】")
        
        if result_type == "VideoLabel":
            tags = data_obj.get("Tags", [])
            if tags:
                lines.append("  Video Labels:")
                for tag in tags[:10]:  # Show top 10
                    tag_name = tag.get("Tag", "")
                    confidence = tag.get("Confidence", "")
                    time_range = ""
                    if "StartTime" in tag and "EndTime" in tag:
                        time_range = f" [{tag['StartTime']}s - {tag['EndTime']}s]"
                    if tag_name:
                        lines.append(f"    • {tag_name} (Confidence: {confidence}){time_range}")
                if len(tags) > 10:
                    lines.append(f"    ... and {len(tags) - 10} more tags")
            else:
                lines.append("  No video labels found.")
        
        elif result_type == "TextLabel":
            tags = data_obj.get("Tags", [])
            if tags:
                lines.append("  Text Labels:")
                for tag in tags[:10]:
                    tag_name = tag.get("Tag", "")
                    confidence = tag.get("Confidence", "")
                    if tag_name:
                        lines.append(f"    • {tag_name} (Confidence: {confidence})")
                if len(tags) > 10:
                    lines.append(f"    ... and {len(tags) - 10} more tags")
            else:
                lines.append("  No text labels found.")
        
        elif result_type == "Meta":
            lines.append("  Metadata:")
            for key, value in data_obj.items():
                lines.append(f"    {key}: {value}")
        
        elif result_type == "ASR":
            texts = data_obj.get("Texts", [])
            if texts:
                lines.append("  ASR Results:")
                for text_item in texts[:5]:  # Show top 5
                    text = text_item.get("Text", "")
                    start_time = text_item.get("StartTime", "")
                    end_time = text_item.get("EndTime", "")
                    lines.append(f"    [{start_time}s - {end_time}s]: {text}")
                if len(texts) > 5:
                    lines.append(f"    ... and {len(texts) - 5} more segments")
            else:
                lines.append("  No ASR results found.")
        
        elif result_type == "OCR":
            texts = data_obj.get("Texts", [])
            if texts:
                lines.append("  OCR Results:")
                for text_item in texts[:5]:
                    text = text_item.get("Text", "")
                    start_time = text_item.get("StartTime", "")
                    end_time = text_item.get("EndTime", "")
                    lines.append(f"    [{start_time}s - {end_time}s]: {text}")
                if len(texts) > 5:
                    lines.append(f"    ... and {len(texts) - 5} more segments")
            else:
                lines.append("  No OCR results found.")
        
        else:
            # Generic output for other types
            lines.append(f"  Data: {json.dumps(data_obj, ensure_ascii=False, indent=4)}")
    
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Alibaba Cloud MPS Smart Tag Analysis Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze video with URL
  python mps_smarttag.py --url https://example.com/video.mp4 --title "My Video"

  # Analyze video with OSS object
  python mps_smarttag.py --oss-object /input/video.mp4 --title "My Video"

  # Enable ASR and OCR
  python mps_smarttag.py --url https://example.com/video.mp4 --title "My Video" --enable-asr --enable-ocr

  # Specify language and template
  python mps_smarttag.py --url https://example.com/video.mp4 --title "My Video" --language en --template-id your-template-id

  # Output full JSON
  python mps_smarttag.py --url https://example.com/video.mp4 --title "My Video" --json
        """
    )
    
    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--url", type=str, help="Media file public URL")
    input_group.add_argument("--oss-object", type=str, help="OSS object path (e.g., /input/video.mp4)")
    
    # Required parameters
    parser.add_argument("--title", type=str, required=True, help="Video title for NLP analysis")
    
    # Optional parameters
    parser.add_argument("--content", type=str, help="Video description")
    parser.add_argument("--template-id", type=str, help="Analysis template ID")
    parser.add_argument("--pipeline-id", type=str, help="Pipeline ID (auto-select if not specified)")
    parser.add_argument("--region", type=str, default=None, help="MPS service region (auto-inferred from OSS input, or fallback to ALIBABA_CLOUD_REGION env var, or cn-shanghai)")
    parser.add_argument("--enable-asr", action="store_true", help="Enable ASR (Automatic Speech Recognition)")
    parser.add_argument("--enable-ocr", action="store_true", help="Enable OCR (Optical Character Recognition)")
    parser.add_argument("--language", type=str, default="cn", choices=["cn", "en", "yue"], 
                        help="Source language for NLP analysis (cn/en/yue), default cn")
    parser.add_argument("--enable-summarization", action="store_true", help="Enable summarization")
    parser.add_argument("--notify-url", type=str, help="Callback URL")
    parser.add_argument("--user-data", type=str, help="User data for the job")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output full JSON format")
    parser.add_argument("--dry-run", action="store_true", help="Only print request parameters without calling API")
    parser.add_argument("--async", action="store_true", dest="async_mode", help="Async mode: submit job and exit without polling")
    
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
    
    # Build input URL
    input_url = build_input_url(url=args.url, oss_object=args.oss_object)
    
    # Build params
    params = build_params(
        enable_asr=args.enable_asr,
        enable_ocr=args.enable_ocr,
        language=args.language,
        summarization=args.enable_summarization
    )
    
    # Determine pipeline_id: use provided or auto-select
    if args.pipeline_id:
        pipeline_id = args.pipeline_id
    else:
        if not _PIPELINE_AVAILABLE:
            print("Error: --pipeline-id not specified and ensure_pipeline not available.", file=sys.stderr)
            print("Please either specify --pipeline-id or ensure mps_pipeline.py is available.", file=sys.stderr)
            sys.exit(1)
        pipeline_id = ensure_pipeline(region=args.region, pipeline_type="smarttag")
        print(f"[Auto] Using smarttag pipeline: {pipeline_id}")
    
    if args.dry_run:
        print("=" * 60)
        print("[Dry Run Mode] Only print request parameters, no actual API call")
        print("=" * 60)
        print(f"Input URL: {input_url}")
        print(f"Title: {args.title}")
        print(f"Content: {args.content or 'Not specified'}")
        print(f"Pipeline ID: {pipeline_id}")
        print(f"Template ID: {args.template_id or 'Not specified'}")
        print(f"Region: {args.region}")
        print(f"Params: {params or 'Not specified'}")
        print(f"Notify URL: {args.notify_url or 'Not specified'}")
        print(f"User Data: {args.user_data or 'Not specified'}")
        return
    
    # Print execution info
    print("=" * 60)
    print("Alibaba Cloud MPS Smart Tag Analysis")
    print("=" * 60)
    print(f"Input: {input_url}")
    print(f"Title: {args.title}")
    print(f"Pipeline ID: {pipeline_id}")
    print(f"Region: {args.region}")
    if args.content:
        print(f"Content: {args.content}")
    if args.template_id:
        print(f"Template ID: {args.template_id}")
    if args.enable_asr:
        print("ASR: Enabled")
    if args.enable_ocr:
        print("OCR: Enabled")
    print(f"Language: {args.language}")
    print("-" * 60)
    
    # Create client and submit job
    try:
        client = create_client(args.region)
        job_id = submit_smarttag_job(
            client,
            input_url=input_url,
            title=args.title,
            pipeline_id=pipeline_id,
            content=args.content,
            template_id=args.template_id,
            params=params,
            notify_url=args.notify_url,
            user_data=args.user_data
        )
        print(f"\nSmart tag job submitted successfully!")
        print(f"Job ID: {job_id}")
        
        # If async mode, exit here
        if args.async_mode:
            print("\nAsync mode: Job submitted. Use poll_task.py to check status.")
            print(f"  python scripts/poll_task.py --job-id {job_id} --job-type smarttag --region {args.region}")
            return
        
        # Import poll function here to allow --help without SDK
        try:
            from poll_task import poll_mps_job
        except ImportError as e:
            print(f"Error: Cannot import poll_mps_job from poll_task: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Poll for job completion
        result = poll_mps_job(job_id, "smarttag", region=args.region)
        
        if result is None:
            print("\nFailed to get job result (timeout or error)", file=sys.stderr)
            sys.exit(1)
        
        # Check job status
        body = result.get("body", {}) or {}
        results = body.get("Results", [])
        
        if results:
            status = results[0].get("Status", "")
            if status == "Fail":
                print("\nJob failed.", file=sys.stderr)
                if args.json_output:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                sys.exit(1)
        
        # Display results
        if args.json_output:
            print("\nFull Response:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("\n" + format_smarttag_result(result))
        
    except Exception as e:
        print(f"\nRequest failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
