#!/usr/bin/env python3
"""
Video Translation Skill - Python SDK Implementation

This script provides Python SDK implementation for video translation operations
when CLI is not available or for more complex scenarios.

Dependencies:
    pip3 install -r requirements.txt

Usage:
    python video_translation.py submit-extract --input-media "oss://bucket/video.mp4" --output-media "oss://bucket/{source}-{timestamp}.srt" --region cn-shanghai
    python video_translation.py get-job --job-id "xxx" --region cn-shanghai
    python video_translation.py submit-translation --input-file "oss://bucket/video.mp4" --output-url "oss://bucket/output.mp4" --source-lang zh --target-lang en --region cn-shanghai
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient


# =============================================================================
# Input Validation Functions
# =============================================================================

class ValidationError(ValueError):
    """Raised when input validation fails."""
    pass


def validate_oss_url(url: str, param_name: str) -> str:
    """
    Validate OSS URL format.

    Allowed formats:
    - oss://bucket/path/object.ext
    - https://bucket.oss-region.aliyuncs.com/path/object.ext

    Args:
        url: URL to validate
        param_name: Parameter name for error messages

    Returns:
        Validated URL

    Raises:
        ValidationError: If URL format is invalid
    """
    if not url:
        raise ValidationError(f"{param_name} cannot be empty")

    # Check for dangerous characters that could be used for injection
    dangerous_chars = ['`', '$', '|', ';', '&', '<', '>', '\n', '\r']
    for char in dangerous_chars:
        if char in url:
            raise ValidationError(f"{param_name} contains invalid character: {repr(char)}")

    # Validate oss:// format
    if url.startswith("oss://"):
        # oss://bucket/path/object
        pattern = r'^oss://[a-z0-9][a-z0-9-]{1,61}[a-z0-9](?:/.*)?$'
        if not re.match(pattern, url):
            raise ValidationError(f"{param_name} invalid oss:// format. Expected: oss://bucket/path/object")
        return url

    # Validate https:// format
    if url.startswith("https://") or url.startswith("http://"):
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                raise ValidationError(f"{param_name} invalid URL: missing host")
            if not parsed.path or parsed.path == '/':
                raise ValidationError(f"{param_name} invalid URL: missing path")
            return url
        except Exception as e:
            raise ValidationError(f"{param_name} invalid URL format: {e}")

    raise ValidationError(
        f"{param_name} must start with 'oss://' or 'https://' (got: {url[:20]}...)"
    )


def validate_http_url(url: str, param_name: str) -> str:
    """
    Validate HTTP URL format (for video translation API).

    Args:
        url: URL to validate
        param_name: Parameter name for error messages

    Returns:
        Validated URL

    Raises:
        ValidationError: If URL format is invalid
    """
    if not url:
        raise ValidationError(f"{param_name} cannot be empty")

    # Check for dangerous characters
    dangerous_chars = ['`', '$', '|', ';', '&', '<', '>', '\n', '\r']
    for char in dangerous_chars:
        if char in url:
            raise ValidationError(f"{param_name} contains invalid character: {repr(char)}")

    # Must be http or https
    if not url.startswith("http://") and not url.startswith("https://"):
        raise ValidationError(f"{param_name} must start with 'http://' or 'https://'")

    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValidationError(f"{param_name} invalid URL: missing host")
        return url
    except Exception as e:
        raise ValidationError(f"{param_name} invalid URL format: {e}")


def validate_detext_area(area: Optional[str]) -> Optional[str]:
    """
    Validate DetextArea parameter to prevent injection.

    Allowed values:
    - None or empty (no text erasure)
    - "Auto" (automatic detection)
    - "[[x, y, w, h]]" format (custom coordinates, all values 0-1)

    Args:
        area: DetextArea value to validate

    Returns:
        Validated value

    Raises:
        ValidationError: If value is invalid
    """
    if area is None or area == "":
        return None

    # Check for dangerous characters
    dangerous_chars = ['`', '$', '|', ';', '&', '<', '>', '\n', '\r', '\\', '"']
    for char in dangerous_chars:
        if char in area:
            raise ValidationError(f"DetextArea contains invalid character: {repr(char)}")

    # Allow "Auto"
    if area == "Auto":
        return area

    # Validate coordinate format: [[x, y, w, h]] or [[x1,y1], [x2,y2]]
    # Only allow digits, decimal points, brackets, commas, and spaces
    allowed_pattern = r'^[\[\]\s\.\d,]+$'
    if not re.match(allowed_pattern, area):
        raise ValidationError(
            f"DetextArea must be 'Auto' or coordinate format like '[[0, 0.9, 1, 0.1]]'"
        )

    # Try to parse as JSON to validate structure
    try:
        coords = json.loads(area)
        # Validate it's a list
        if not isinstance(coords, list):
            raise ValidationError("DetextArea must be a list")
        # Could add more validation for coordinate values (0-1 range)
        for item in coords if isinstance(coords[0], list) else [coords]:
            if isinstance(item, (int, float)):
                if not 0 <= item <= 1:
                    raise ValidationError("DetextArea coordinates must be between 0 and 1")
    except json.JSONDecodeError:
        raise ValidationError(f"DetextArea invalid JSON format: {area}")

    return area


def validate_job_id(job_id: str) -> str:
    """
    Validate Job ID format.

    Args:
        job_id: Job ID to validate

    Returns:
        Validated Job ID

    Raises:
        ValidationError: If Job ID is invalid
    """
    if not job_id:
        raise ValidationError("Job ID cannot be empty")

    # Job IDs are typically alphanumeric with hyphens/underscores
    # Allow only safe characters
    allowed_pattern = r'^[a-zA-Z0-9_-]+$'
    if not re.match(allowed_pattern, job_id):
        raise ValidationError(f"Job ID contains invalid characters. Only alphanumeric, hyphen, and underscore allowed.")

    return job_id


def validate_language_code(code: str) -> str:
    """
    Validate language code.

    Args:
        code: Language code (e.g., 'zh', 'en', 'ja')

    Returns:
        Validated language code

    Raises:
        ValidationError: If language code is invalid
    """
    if not code:
        raise ValidationError("Language code cannot be empty")

    # Language codes are typically 2-4 lowercase letters
    allowed_pattern = r'^[a-z]{2,4}$'
    if not re.match(allowed_pattern, code):
        raise ValidationError(f"Language code must be 2-4 lowercase letters (got: {code})")

    return code


def validate_region(region: str) -> str:
    """
    Validate region ID.

    Args:
        region: Region ID (e.g., 'cn-shanghai', 'cn-beijing')

    Returns:
        Validated region ID

    Raises:
        ValidationError: If region is invalid
    """
    if not region:
        raise ValidationError("Region cannot be empty")

    # Region format: cn-city, us-city, etc.
    allowed_pattern = r'^[a-z]{2}-[a-z]+$'
    if not re.match(allowed_pattern, region):
        raise ValidationError(f"Invalid region format. Expected: 'cn-shanghai' (got: {region})")

    return region


def generate_client_token(
    input_media: str,
    output_media: str,
    extra: Optional[str] = None
) -> str:
    """
    生成确定性幂等键 (ClientToken)。

    基于输入输出路径生成 SHA256 哈希，确保相同参数产生相同 token。
    这可以防止因网络超时或错误重试导致的重复任务创建。

    Args:
        input_media: 输入媒体 URL
        output_media: 输出媒体 URL
        extra: 额外的区分参数 (如翻译配置等)

    Returns:
        64 字符的 SHA256 哈希字符串
    """
    # 构建确定性字符串
    content = f"{input_media}|{output_media}"
    if extra:
        content += f"|{extra}"

    # 生成 SHA256 哈希
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def generate_default_output_path(
    input_url: str,
    region: str,
    suffix: str = "translated",
    extension: str = ".mp4"
) -> str:
    """
    根据输入路径生成默认输出路径。
    
    Args:
        input_url: 输入视频的 OSS 地址 (oss://bucket/path/file.mp4)
        region: 服务区域 (cn-shanghai)
        suffix: 文件名后缀 (translated)
        extension: 文件扩展名 (.mp4 或 .srt)
    
    Returns:
        https:// 格式的输出路径
    
    Example:
        input: oss://my-bucket/videos/demo.mp4
        output: https://my-bucket.oss-cn-shanghai.aliyuncs.com/videos/demo_translated_1711440000.mp4
    """
    timestamp = int(time.time())
    
    # 解析 oss:// URL
    if input_url.startswith("oss://"):
        # oss://bucket/path/file.mp4
        path = input_url[6:]  # 移除 "oss://"
        parts = path.split("/", 1)
        bucket = parts[0]
        object_path = parts[1] if len(parts) > 1 else ""
    elif input_url.startswith("https://") or input_url.startswith("http://"):
        # https://bucket.oss-region.aliyuncs.com/path/file.mp4
        parsed = urlparse(input_url)
        bucket = parsed.netloc.split(".")[0]
        object_path = parsed.path.lstrip("/")
    else:
        raise ValueError(f"不支持的 URL 格式: {input_url}")
    
    # 获取目录和文件名
    dir_path = os.path.dirname(object_path)
    filename = os.path.basename(object_path)
    name_without_ext = os.path.splitext(filename)[0]
    
    # 生成新文件名
    new_filename = f"{name_without_ext}_{suffix}_{timestamp}{extension}"
    
    # 拼接新路径
    if dir_path:
        new_object_path = f"{dir_path}/{new_filename}"
    else:
        new_object_path = new_filename
    
    # 返回 https:// 格式
    return f"https://{bucket}.oss-{region}.aliyuncs.com/{new_object_path}"


def create_client(region: str) -> OpenApiClient:
    """Create ICE OpenAPI client."""
    credential = CredentialClient()
    config = open_api_models.Config(credential=credential)
    config.endpoint = f"ice.{region}.aliyuncs.com"
    config.user_agent = "AlibabaCloud-Agent-Skills"
    return OpenApiClient(config)


def submit_subtitle_extraction(
    client: OpenApiClient,
    input_media: str,
    output_media: str,
    name: Optional[str] = None,
    lang: Optional[str] = None,
    fps: Optional[int] = None,
    roi: Optional[list] = None,
    track: Optional[str] = None,
    client_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Submit CaptionExtraction job for subtitle extraction.

    Args:
        client: OpenAPI client
        input_media: Input video OSS URL
        output_media: Output SRT file OSS URL
        name: Job name
        lang: Recognition language
        fps: Sampling frame rate
        roi: Region of interest
        track: Track mode
        client_token: 幂等键，用于防止重复创建任务。
                      如果不提供，将基于 input_media 和 output_media 自动生成。

    Returns:
        API response dict
    """
    params = open_api_models.Params(
        action="SubmitIProductionJob",
        version="2020-11-09",
        protocol="HTTPS",
        method="POST",
        auth_type="AK",
        style="RPC",
        pathname="/",
        req_body_type="json",
        body_type="json",
    )

    # Build job_params - direct parameters without FunctionName/Config wrapper
    job_params = {}
    if fps is not None:
        job_params["fps"] = fps
    if roi is not None:
        job_params["roi"] = roi
    if lang is not None:
        job_params["lang"] = lang
    if track is not None:
        job_params["track"] = track

    queries = {
        "FunctionName": "CaptionExtraction",
        "Input.Type": "OSS",
        "Input.Media": input_media,
        "Output.Type": "OSS",
        "Output.Media": output_media,
    }
    if job_params:
        queries["JobParams"] = json.dumps(job_params)
    if name:
        queries["Name"] = name

    # 幂等性支持: 自动生成或使用提供的 ClientToken
    if client_token is None:
        client_token = generate_client_token(input_media, output_media)
    queries["ClientToken"] = client_token

    request = open_api_models.OpenApiRequest(query=OpenApiUtilClient.query(queries))
    runtime = util_models.RuntimeOptions(
        connect_timeout=10,  # 连接超时 10 秒
        read_timeout=30,     # 读取超时 30 秒
    )
    response = client.call_api(params, request, runtime)
    return response


def query_iproduction_job(client: OpenApiClient, job_id: str) -> Dict[str, Any]:
    """Query intelligent production job status (for CaptionExtraction etc.)."""
    params = open_api_models.Params(
        action="QueryIProductionJob",
        version="2020-11-09",
        protocol="HTTPS",
        method="POST",
        auth_type="AK",
        style="RPC",
        pathname="/",
        req_body_type="json",
        body_type="json",
    )

    queries = {"JobId": job_id}
    request = open_api_models.OpenApiRequest(query=OpenApiUtilClient.query(queries))
    runtime = util_models.RuntimeOptions(
        connect_timeout=10,
        read_timeout=30,
    )
    response = client.call_api(params, request, runtime)
    return response


def get_smart_handle_job(client: OpenApiClient, job_id: str) -> Dict[str, Any]:
    """Get video translation job result (for SubmitVideoTranslationJob)."""
    params = open_api_models.Params(
        action="GetSmartHandleJob",
        version="2020-11-09",
        protocol="HTTPS",
        method="POST",
        auth_type="AK",
        style="RPC",
        pathname="/",
        req_body_type="json",
        body_type="json",
    )

    queries = {"JobId": job_id}
    request = open_api_models.OpenApiRequest(query=OpenApiUtilClient.query(queries))
    runtime = util_models.RuntimeOptions(
        connect_timeout=10,
        read_timeout=30,
    )
    response = client.call_api(params, request, runtime)
    return response


def submit_video_translation_job(
    client: OpenApiClient,
    input_config: str,
    output_config: str,
    editing_config: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    client_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Submit video translation job.

    Args:
        client: OpenAPI client
        input_config: Input config JSON string
        output_config: Output config JSON string
        editing_config: Editing config JSON string
        title: Job title
        description: Job description
        client_token: 幂等键，用于防止重复创建任务。
                      如果不提供，将基于 input_config 和 output_config 自动生成。

    Returns:
        API response dict
    """
    params = open_api_models.Params(
        action="SubmitVideoTranslationJob",
        version="2020-11-09",
        protocol="HTTPS",
        method="POST",
        auth_type="AK",
        style="RPC",
        pathname="/",
        req_body_type="json",
        body_type="json",
    )

    queries = {
        "InputConfig": input_config,
        "OutputConfig": output_config,
        "EditingConfig": editing_config,
    }
    if title:
        queries["Title"] = title
    if description:
        queries["Description"] = description

    # 幂等性支持: 自动生成或使用提供的 ClientToken
    if client_token is None:
        # 基于 input_config 和 output_config 生成确定性 token
        client_token = generate_client_token(input_config, output_config, editing_config)
    queries["ClientToken"] = client_token

    request = open_api_models.OpenApiRequest(query=OpenApiUtilClient.query(queries))
    runtime = util_models.RuntimeOptions(
        connect_timeout=10,
        read_timeout=30,
    )
    response = client.call_api(params, request, runtime)
    return response


def wait_for_job(client: OpenApiClient, job_id: str, timeout: int = 3600, interval: int = 10) -> Dict[str, Any]:
    """Wait for job to complete."""
    start_time = time.time()
    while True:
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Job {job_id} timed out after {timeout} seconds")

        result = get_smart_handle_job(client, job_id)
        body = result.get("body", {})
        state = body.get("State", "")

        print(f"Job {job_id} state: {state}")

        if state == "Finished":
            return result
        elif state == "Failed":
            error_msg = body.get("ErrorMessage", "Unknown error")
            raise RuntimeError(f"Job {job_id} failed: {error_msg}")

        time.sleep(interval)


def asr_result_to_srt(asr_result: str) -> str:
    """Convert ASR result JSON to SRT format."""
    try:
        items = json.loads(asr_result)
    except json.JSONDecodeError:
        return asr_result

    srt_lines = []
    for i, item in enumerate(items, 1):
        content = item.get("content", "")
        from_time = item.get("from", 0)
        to_time = item.get("to", 0)

        # Convert seconds to SRT timestamp format
        from_ts = seconds_to_srt_timestamp(from_time)
        to_ts = seconds_to_srt_timestamp(to_time)

        srt_lines.append(f"{i}")
        srt_lines.append(f"{from_ts} --> {to_ts}")
        srt_lines.append(content)
        srt_lines.append("")

    return "\n".join(srt_lines)


def seconds_to_srt_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build_input_config(video_url: str, subtitle_url: Optional[str] = None) -> str:
    """Build InputConfig JSON."""
    config = {"Type": "Video", "Video": video_url}
    if subtitle_url:
        config["Subtitle"] = subtitle_url
    return json.dumps(config)


def build_output_config(media_url: str, width: Optional[int] = None, height: Optional[int] = None) -> str:
    """Build OutputConfig JSON."""
    config = {"MediaURL": media_url}
    if width:
        config["Width"] = width
    if height:
        config["Height"] = height
    return json.dumps(config)


def build_editing_config(
    source_language: str,
    target_language: str,
    translation_mode: str = "subtitle",
    bilingual: bool = False,
    font_size: str = "medium",
    position: str = "bottom",
    text_source: str = "OCR_ASR",
    custom_srt_type: Optional[str] = None,
    detext_area: Optional[str] = None,
) -> str:
    """
    Build EditingConfig JSON.

    Args:
        text_source: 字幕来源 - OCR_ASR(自动识别), SubtitleFile(外部SRT文件), ASR, OCR, ALL
        custom_srt_type: 当 text_source=SubtitleFile 时必填 - SourceSrt(原语种), TargetSrt(目标语种)
        detext_area: 字幕擦除区域 - None(不擦除), "Auto"(自动识别), "[[x,y,w,h]]"(自定义)

    Raises:
        ValidationError: If detext_area contains invalid characters
    """
    # Validate detext_area to prevent injection
    detext_area = validate_detext_area(detext_area)

    # Translation mode mapping
    need_speech = translation_mode == "speech"

    # Font size mapping
    font_size_map = {"small": 60, "medium": 95, "large": 130}
    font_size_value = font_size_map.get(font_size, 95)

    # Position mapping
    position_map = {"top": 0.15, "center": 0.5, "bottom": 0.85}
    y_value = position_map.get(position, 0.85)

    config = {
        "SourceLanguage": source_language,
        "TargetLanguage": target_language,
        "NeedSpeechTranslate": need_speech,
        "NeedFaceTranslate": False,  # 面容翻译明确不开启
        "BilingualSubtitle": bilingual,
        "SupportEditing": True,
        "TextSource": text_source,
    }

    # 当使用外部 SRT 文件时，需要指定 CustomSrtType
    if text_source == "SubtitleFile" and custom_srt_type:
        config["CustomSrtType"] = custom_srt_type

    # 字幕擦除配置
    if detext_area:
        config["DetextArea"] = detext_area
    
    if need_speech:
        # 语音级翻译: 使用 SpeechTranslate 配置
        config["SpeechTranslate"] = {
            "VoiceConfig": {
                "Voice": "zhiyan_emo"
            }
        }
    else:
        # 字幕级翻译: 使用 SubtitleTranslate 配置
        config["SubtitleTranslate"] = {
            "OcrArea": "Auto",
            "SubtitleConfig": {
                "Type": "Text",
                "FontSize": font_size_value,
                "FontColor": "#ffffff",
                "Font": "Alibaba PuHuiTi",
                "Y": y_value,
                "TextWidth": 0.9,
                "Alignment": "Center",
                "BorderStyle": 1,
            },
        }
    
    return json.dumps(config)


def main():
    parser = argparse.ArgumentParser(description="Video Translation Skill")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Submit subtitle extraction job (CaptionExtraction)
    extract_parser = subparsers.add_parser("submit-extract", help="Submit subtitle extraction job (ASR+OCR combined)")
    extract_parser.add_argument("--input-media", required=True, help="Input video OSS URL")
    extract_parser.add_argument("--output-media", required=True, help="Output SRT file OSS URL (supports placeholders: {source}, {timestamp}, {sequenceId})")
    extract_parser.add_argument("--region", default="cn-shanghai", help="Region ID")
    extract_parser.add_argument("--name", help="Job name")
    extract_parser.add_argument("--lang", help="Recognition language: ch/en/ch_ml (optional)")
    extract_parser.add_argument("--fps", type=int, help="Sampling frame rate (optional)")
    extract_parser.add_argument("--track", help="Track mode: 'main' for main subtitle only (optional)")
    extract_parser.add_argument("--client-token", help="Idempotent key for preventing duplicate jobs (auto-generated if not provided)")
    extract_parser.add_argument("--wait", action="store_true", help="Wait for job completion")

    # Get job result
    get_parser = subparsers.add_parser("get-job", help="Get job result")
    get_parser.add_argument("--job-id", required=True, help="Job ID")
    get_parser.add_argument("--region", default="cn-shanghai", help="Region ID")

    # Submit translation job
    trans_parser = subparsers.add_parser("submit-translation", help="Submit video translation job")
    trans_parser.add_argument("--input-file", required=True, help="Input video OSS URL or media ID")
    trans_parser.add_argument("--output-url", required=True, help="Output video OSS URL")
    trans_parser.add_argument("--source-lang", required=True, help="Source language code")
    trans_parser.add_argument("--target-lang", required=True, help="Target language code")
    trans_parser.add_argument("--region", default="cn-shanghai", help="Region ID")
    trans_parser.add_argument("--mode", default="subtitle", choices=["subtitle", "speech"], help="Translation mode")
    trans_parser.add_argument("--bilingual", action="store_true", help="Enable bilingual subtitles")
    trans_parser.add_argument("--font-size", default="medium", choices=["small", "medium", "large"], help="Subtitle font size")
    trans_parser.add_argument("--position", default="bottom", choices=["top", "center", "bottom"], help="Subtitle position")
    trans_parser.add_argument("--subtitle-url", help="Custom subtitle file URL")
    trans_parser.add_argument("--client-token", help="Idempotent key for preventing duplicate jobs (auto-generated if not provided)")
    trans_parser.add_argument("--wait", action="store_true", help="Wait for job completion")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # =================================================================
    # Input Validation
    # =================================================================
    try:
        # Validate region
        args.region = validate_region(args.region)

        if args.command == "submit-extract":
            args.input_media = validate_oss_url(args.input_media, "--input-media")
            args.output_media = validate_oss_url(args.output_media, "--output-media")

        elif args.command == "get-job":
            args.job_id = validate_job_id(args.job_id)

        elif args.command == "submit-translation":
            # input-file can be OSS URL or media ID (alphanumeric)
            if args.input_file.startswith("oss://") or args.input_file.startswith("http"):
                args.input_file = validate_oss_url(args.input_file, "--input-file")
            # Otherwise treat as media ID (validated by API)

            args.output_url = validate_http_url(args.output_url, "--output-url")
            args.source_lang = validate_language_code(args.source_lang)
            args.target_lang = validate_language_code(args.target_lang)

            if args.subtitle_url:
                args.subtitle_url = validate_http_url(args.subtitle_url, "--subtitle-url")

    except ValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # =================================================================
    # Execute Commands
    # =================================================================
    client = create_client(args.region)

    if args.command == "submit-extract":
        result = submit_subtitle_extraction(
            client,
            args.input_media,
            args.output_media,
            name=args.name,
            lang=args.lang,
            fps=args.fps,
            track=args.track,
            client_token=getattr(args, 'client_token', None),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

        if args.wait and result.get("body", {}).get("JobId"):
            job_id = result["body"]["JobId"]
            print(f"\nWaiting for extraction job {job_id}...")
            final_result = wait_for_job(client, job_id)
            print(json.dumps(final_result, indent=2, ensure_ascii=False))
            print(f"\nSRT file generated at: {args.output_media}")

    elif args.command == "get-job":
        result = get_smart_handle_job(client, args.job_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "submit-translation":
        input_config = build_input_config(args.input_file, args.subtitle_url)
        output_config = build_output_config(args.output_url)
        editing_config = build_editing_config(
            args.source_lang,
            args.target_lang,
            translation_mode=args.mode,
            bilingual=args.bilingual,
            font_size=args.font_size,
            position=args.position,
        )

        result = submit_video_translation_job(
            client,
            input_config,
            output_config,
            editing_config,
            client_token=getattr(args, 'client_token', None),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

        if args.wait and result.get("body", {}).get("Data", {}).get("JobId"):
            job_id = result["body"]["Data"]["JobId"]
            print(f"\nWaiting for translation job {job_id}...")
            final_result = wait_for_job(client, job_id)
            print(json.dumps(final_result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
