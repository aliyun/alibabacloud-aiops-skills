#!/usr/bin/env python3
"""
Video Editor Script for Alibaba Cloud ICE (Intelligent Cloud Editing)

This script uses Alibaba Cloud Common SDK to:
1. Submit a video producing job with Timeline and OutputMediaConfig
2. Poll the job status until completion
3. Return the output video URL

Usage (region has no default — the agent must confirm it with the user first):
    # Submit a job and wait for completion
    python video_editor.py submit --timeline timeline.json --output-config output.json --region cn-shanghai --wait

    # Check job status
    python video_editor.py status --job-id <job_id> --region cn-shanghai

    # Resolve a MediaId to a signed (authenticated) playable URL
    python video_editor.py media-info --media-id <media_id> --region cn-shanghai

    # Submit an intelligent production job (single media in, algorithm result out)
    python video_editor.py iproduction --function Cover \
        --input oss://bucket/input.mp4 \
        --output "oss://bucket/cover/{source}-{sequenceId}.png" \
        --region cn-shanghai --wait

    # Check an intelligent production job
    python video_editor.py iproduction-status --job-id <job_id> --region cn-shanghai

    # Export the AI-expanded timeline of a finished project (real MediaURLs and timings)
    python video_editor.py export-timeline --project-id <project_id> \
        --bucket my-bucket --region cn-shanghai --output timeline_expanded.json --wait

Requirements:
    pip install -r scripts/requirements.txt

Environment:
    Credentials are automatically obtained via the default credential chain:
    - Environment variables
    - Credentials file (~/.alibabacloud/credentials.ini)
    - ECS RAM role (if running on ECS)
    
    Run `aliyun configure` to set up credentials.
"""

import argparse
import json
import os
import re
import sys
import time
import uuid
from typing import Optional, Tuple, List

# Valid Alibaba Cloud regions that support ICE service
VALID_REGIONS = [
    "cn-shanghai",
    "cn-beijing", 
    "cn-hangzhou",
    "cn-shenzhen",
    "cn-zhangjiakou",
    "ap-southeast-1",  # Singapore
]

# Regions where AI features run: AI_* clip types and effects in a Timeline
# (SKILL.md §3) and every SubmitIProductionJob algorithm (§7.1).
AI_FEATURE_REGIONS = ["cn-shanghai", "cn-beijing", "cn-hangzhou"]

# Printed when a submit runs with --yes. It must not read as "the plan was
# confirmed": this flag only silences the script's own stdin prompt.
SKIP_CONFIRM_NOTE = (
    "⏩ Skipping this script's stdin prompt (--yes / VIDEO_EDITOR_SKIP_CONFIRMATION=1).\n"
    "   That is not the SKILL.md §2.2 plan confirmation — no flag can stand in for it.\n"
    "   The plan must already be written out for the user before this command runs."
)

# Video resolution constraints
MIN_RESOLUTION = 128
MAX_RESOLUTION = 8192

# Job ID pattern (alphanumeric with hyphens)
JOB_ID_PATTERN = re.compile(r'^[a-zA-Z0-9\-]+$')

# Media ID pattern (32-char hex asset id)
MEDIA_ID_PATTERN = re.compile(r'^[a-zA-Z0-9\-]+$')

# FunctionName values accepted by SubmitIProductionJob (intelligent production)
IPRODUCTION_FUNCTIONS = [
    "Cover",
    "VideoClip",
    "VideoDelogo",
    "VideoDetext",
    "CaptionExtraction",
    "VideoGreenScreenMatting",
    "FaceBeauty",
    "VideoH2V",
    "MusicSegmentDetect",
    "AudioBeatDetection",
    "AudioQualityAssessment",
    "SpeechDenoise",
    "AudioMixing",
    "MusicDemix",
]

# Functions that write several output files: the OSS output path needs a placeholder
# so the files do not overwrite each other
IPRODUCTION_REQUIRED_PLACEHOLDERS = {
    "Cover": "{sequenceId}",
    "MusicDemix": "{resultType}",
}

# IProduction job statuses that mean "still running"
IPRODUCTION_RUNNING_STATUSES = ["Queuing", "Analysing"]

# Media asset business types accepted by Output.Biz
IPRODUCTION_OUTPUT_BIZ = ["IMS", "VOD"]

# Prefixes that identify an OSS media reference (as opposed to a media asset id)
OSS_MEDIA_PREFIXES = ("oss://", "http://", "https://")

# ClientToken pattern (alphanumeric with hyphens and underscores, max 64 chars)
CLIENT_TOKEN_PATTERN = re.compile(r'^[a-zA-Z0-9\-_]+$')
CLIENT_TOKEN_MAX_LENGTH = 64

# User-Agent for Alibaba Cloud API calls (required for tracking).
# Template: AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}
# session-id: the host's AGENT_SESSION_ID when it exports one, otherwise one
# 32-char lowercase hex id generated per process — so every call in a single
# run correlates. skill-version comes from references/manifest.json, read at
# import time — the read gate that runs before any cloud client is created.
SKILL_NAME = "alibabacloud-video-editor"


def _load_skill_version() -> str:
    manifest = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                            "references", "manifest.json")
    try:
        with open(manifest, encoding="utf-8") as f:
            return json.load(f)["version"]
    except (OSError, ValueError, KeyError) as exc:
        raise RuntimeError(f"cannot read skill version from {manifest}: {exc}") from exc


SKILL_VERSION = _load_skill_version()
SESSION_ID = os.environ.get("AGENT_SESSION_ID") or uuid.uuid4().hex
USER_AGENT = f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{SESSION_ID} skill-version/{SKILL_VERSION}"

try:
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_tea_openapi.client import Client as OpenApiClient
    from alibabacloud_tea_util import models as util_models
    from alibabacloud_credentials.client import Client as CredentialClient
    from alibabacloud_openapi_util.client import Client as OpenApiUtilClient
except ImportError:
    print("Error: Required packages not installed.")
    print("Please run: pip install -r scripts/requirements.txt")
    sys.exit(1)


class ValidationError(Exception):
    """Custom exception for input validation errors."""
    pass


def validate_region(region: str) -> str:
    """
    Validate region against whitelist.
    
    Args:
        region: Region ID to validate
        
    Returns:
        Validated region string
        
    Raises:
        ValidationError: If region is not in whitelist
    """
    if region not in VALID_REGIONS:
        raise ValidationError(
            f"Invalid region '{region}'. Must be one of: {', '.join(VALID_REGIONS)}"
        )
    return region


def validate_job_id(job_id: str) -> str:
    """
    Validate job ID format.
    
    Args:
        job_id: Job ID to validate
        
    Returns:
        Validated job ID string
        
    Raises:
        ValidationError: If job ID format is invalid
    """
    if not job_id or len(job_id) > 128:
        raise ValidationError("Job ID must be non-empty and no longer than 128 characters")
    if not JOB_ID_PATTERN.match(job_id):
        raise ValidationError("Job ID must contain only alphanumeric characters and hyphens")
    return job_id


def validate_media_id(media_id: str) -> str:
    """
    Validate media ID format.
    
    Args:
        media_id: Media ID to validate
        
    Returns:
        Validated media ID string
        
    Raises:
        ValidationError: If media ID format is invalid
    """
    if not media_id or len(media_id) > 128:
        raise ValidationError("Media ID must be non-empty and no longer than 128 characters")
    if not MEDIA_ID_PATTERN.match(media_id):
        raise ValidationError("Media ID must contain only alphanumeric characters and hyphens")
    return media_id


def generate_client_token() -> str:
    """
    Generate a unique ClientToken for idempotent API calls.
    
    Returns:
        A UUID-based token string
    """
    return str(uuid.uuid4())


def validate_client_token(token: Optional[str]) -> Optional[str]:
    """
    Validate ClientToken format if provided.
    
    Args:
        token: ClientToken to validate (can be None)
        
    Returns:
        Validated token or None
        
    Raises:
        ValidationError: If token format is invalid
    """
    if token is None:
        return None
    
    if len(token) > CLIENT_TOKEN_MAX_LENGTH:
        raise ValidationError(
            f"ClientToken must be no longer than {CLIENT_TOKEN_MAX_LENGTH} characters"
        )
    if not CLIENT_TOKEN_PATTERN.match(token):
        raise ValidationError(
            "ClientToken must contain only alphanumeric characters, hyphens, and underscores"
        )
    return token


def validate_timeline(timeline: dict) -> dict:
    """
    Validate Timeline JSON structure.
    
    Args:
        timeline: Timeline dict to validate
        
    Returns:
        Validated timeline dict
        
    Raises:
        ValidationError: If timeline structure is invalid
    """
    if not isinstance(timeline, dict):
        raise ValidationError("Timeline must be a JSON object")
    
    # Check required fields (at least one track type should exist)
    valid_track_types = ["VideoTracks", "AudioTracks", "SubtitleTracks"]
    has_tracks = any(key in timeline for key in valid_track_types)
    
    if not has_tracks:
        raise ValidationError(
            f"Timeline must contain at least one of: {', '.join(valid_track_types)}"
        )
    
    # Validate VideoTracks if present
    if "VideoTracks" in timeline:
        _validate_video_tracks(timeline["VideoTracks"])
    
    # Validate AudioTracks if present
    if "AudioTracks" in timeline:
        _validate_audio_tracks(timeline["AudioTracks"])
    
    # Validate SubtitleTracks if present
    if "SubtitleTracks" in timeline:
        _validate_subtitle_tracks(timeline["SubtitleTracks"])
    
    return timeline


def _validate_video_tracks(tracks: list) -> None:
    """Validate VideoTracks structure."""
    if not isinstance(tracks, list):
        raise ValidationError("VideoTracks must be an array")
    
    for i, track in enumerate(tracks):
        if not isinstance(track, dict):
            raise ValidationError(f"VideoTracks[{i}] must be an object")
        
        if "VideoTrackClips" in track:
            clips = track["VideoTrackClips"]
            if not isinstance(clips, list):
                raise ValidationError(f"VideoTracks[{i}].VideoTrackClips must be an array")
            
            for j, clip in enumerate(clips):
                _validate_clip(clip, f"VideoTracks[{i}].VideoTrackClips[{j}]")


def _validate_audio_tracks(tracks: list) -> None:
    """Validate AudioTracks structure."""
    if not isinstance(tracks, list):
        raise ValidationError("AudioTracks must be an array")
    
    for i, track in enumerate(tracks):
        if not isinstance(track, dict):
            raise ValidationError(f"AudioTracks[{i}] must be an object")
        
        if "AudioTrackClips" in track:
            clips = track["AudioTrackClips"]
            if not isinstance(clips, list):
                raise ValidationError(f"AudioTracks[{i}].AudioTrackClips must be an array")
            
            for j, clip in enumerate(clips):
                _validate_clip(clip, f"AudioTracks[{i}].AudioTrackClips[{j}]")


def _validate_subtitle_tracks(tracks: list) -> None:
    """Validate SubtitleTracks structure."""
    if not isinstance(tracks, list):
        raise ValidationError("SubtitleTracks must be an array")
    
    for i, track in enumerate(tracks):
        if not isinstance(track, dict):
            raise ValidationError(f"SubtitleTracks[{i}] must be an object")


def _validate_clip(clip: dict, path: str) -> None:
    """Validate a single clip structure."""
    if not isinstance(clip, dict):
        raise ValidationError(f"{path} must be an object")
    
    # Validate time fields if present (must be non-negative numbers)
    time_fields = ["In", "Out", "TimelineIn", "TimelineOut", "Duration"]
    for field in time_fields:
        if field in clip:
            value = clip[field]
            if not isinstance(value, (int, float)) or value < 0:
                raise ValidationError(f"{path}.{field} must be a non-negative number")
    
    # Validate MediaURL if present
    if "MediaURL" in clip:
        url = clip["MediaURL"]
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise ValidationError(f"{path}.MediaURL must be a valid HTTP/HTTPS URL")


def validate_output_config(config: dict) -> dict:
    """
    Validate OutputMediaConfig JSON structure.
    
    Args:
        config: OutputMediaConfig dict to validate
        
    Returns:
        Validated config dict
        
    Raises:
        ValidationError: If config structure is invalid
    """
    if not isinstance(config, dict):
        raise ValidationError("OutputMediaConfig must be a JSON object")
    
    # MediaURL is required
    if "MediaURL" not in config:
        raise ValidationError("OutputMediaConfig.MediaURL is required")
    
    media_url = config["MediaURL"]
    if not isinstance(media_url, str) or not media_url.startswith(("http://", "https://")):
        raise ValidationError("OutputMediaConfig.MediaURL must be a valid HTTP/HTTPS URL")
    
    # Validate Width if present
    if "Width" in config:
        width = config["Width"]
        if not isinstance(width, int) or width < MIN_RESOLUTION or width > MAX_RESOLUTION:
            raise ValidationError(
                f"OutputMediaConfig.Width must be an integer between {MIN_RESOLUTION} and {MAX_RESOLUTION}"
            )
    
    # Validate Height if present
    if "Height" in config:
        height = config["Height"]
        if not isinstance(height, int) or height < MIN_RESOLUTION or height > MAX_RESOLUTION:
            raise ValidationError(
                f"OutputMediaConfig.Height must be an integer between {MIN_RESOLUTION} and {MAX_RESOLUTION}"
            )
    
    return config


def load_json_input(input_str: str, input_name: str) -> dict:
    """
    Load JSON from file path or JSON string.
    
    Args:
        input_str: File path or JSON string
        input_name: Name of the input for error messages
        
    Returns:
        Parsed JSON dict
        
    Raises:
        ValidationError: If JSON parsing fails
    """
    try:
        # Try to load as file first
        with open(input_str, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Try to parse as JSON string
        try:
            return json.loads(input_str)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON for {input_name}: {e}")
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in file for {input_name}: {e}")


def create_client(region_id: str = "cn-shanghai") -> OpenApiClient:
    """
    Create an OpenAPI client using default credential chain.
    
    The credential chain will try:
    1. Environment variables (ALIBABA_CLOUD_ACCESS_KEY_ID, ALIBABA_CLOUD_ACCESS_KEY_SECRET)
    2. Credentials file (~/.alibabacloud/credentials.ini)
    3. ECS RAM role (if running on ECS)
    """
    credential = CredentialClient()
    config = open_api_models.Config(credential=credential)
    config.endpoint = f"ice.{region_id}.aliyuncs.com"
    config.user_agent = USER_AGENT
    return OpenApiClient(config)


def call_api(
    client: OpenApiClient,
    action: str,
    params: dict,
    region_id: str = "cn-shanghai",
    runtime: Optional[util_models.RuntimeOptions] = None
) -> dict:
    """
    Call Alibaba Cloud ICE API using Common Request.
    
    Args:
        client: OpenAPI client instance
        action: API action name (e.g., "SubmitMediaProducingJob")
        params: API parameters
        region_id: Region ID
        runtime: Optional runtime options (set read/connect_timeout here to bound the call)
    
    Returns:
        API response as dict
    """
    # Build the OpenAPI request
    api_request = open_api_models.OpenApiRequest(
        query=OpenApiUtilClient.query(params)
    )
    
    # Runtime options
    runtime = runtime or util_models.RuntimeOptions()
    
    # API parameters
    api_params = open_api_models.Params(
        action=action,
        version="2020-11-09",
        protocol="HTTPS",
        method="POST",
        auth_type="AK",
        style="RPC",
        pathname="/",
        req_body_type="json",
        body_type="json"
    )
    
    # Call the API
    response = client.call_api(api_params, api_request, runtime)
    
    # Response body is in response["body"]
    if response and "body" in response:
        return response["body"]
    return response


def submit_media_producing_job(
    client: OpenApiClient,
    timeline: dict,
    output_media_config: dict,
    region_id: str = "cn-shanghai",
    client_token: Optional[str] = None
) -> Tuple[str, str]:
    """
    Submit a media producing job to ICE with idempotency support.
    
    Args:
        client: OpenAPI client instance
        timeline: Timeline JSON object
        output_media_config: Output configuration including MediaURL, Width, Height
        region_id: Region ID
        client_token: Optional ClientToken for idempotency. If not provided, 
                      a new UUID will be generated automatically.
    
    Returns:
        Tuple of (job_id, client_token) - the client_token can be used for retries
    """
    # Generate ClientToken if not provided for idempotency
    if client_token is None:
        client_token = generate_client_token()
    
    params = {
        "Timeline": json.dumps(timeline, ensure_ascii=False),
        "OutputMediaConfig": json.dumps(output_media_config, ensure_ascii=False),
        "ClientToken": client_token
    }
    
    response = call_api(client, "SubmitMediaProducingJob", params, region_id)
    
    job_id = response.get("JobId")
    if not job_id:
        raise Exception(f"Failed to get JobId from response: {response}")
    
    return job_id, client_token


def get_media_producing_job(
    client: OpenApiClient,
    job_id: str,
    region_id: str = "cn-shanghai"
) -> dict:
    """Return the complete producing-job record, not just status and URL."""
    response = call_api(client, "GetMediaProducingJob", {"JobId": job_id}, region_id)
    job = response.get("MediaProducingJob", {})
    job.setdefault("JobId", job_id)
    if not job.get("Status"):
        raise Exception(f"Failed to get job status from response: {response}")
    return job


def _print_json_field(label: str, value) -> None:
    if value in (None, ""):
        return
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            pass
    print(f"{label}:")
    print(json.dumps(value, ensure_ascii=False, indent=2) if isinstance(value, (dict, list)) else value)


def print_media_producing_job(job: dict, details: bool = False) -> None:
    for label, key in (
        ("Status", "Status"),
        ("JobId", "JobId"),
        ("TemplateId", "TemplateId"),
        ("ProjectId", "ProjectId"),
        ("MediaId", "MediaId"),
        ("Output URL", "MediaURL"),
        ("Duration", "Duration"),
        ("Message", "Message"),
    ):
        if job.get(key) not in (None, ""):
            print(f"{label}: {job[key]}")
    if details:
        _print_json_field("ClipsParam", job.get("ClipsParam"))
        _print_json_field("Timeline", job.get("Timeline"))


def probe_stream_durations(media_url: str) -> Tuple[List[dict], Optional[str]]:
    """Read per-stream durations from a remote media URL without downloading it."""
    import subprocess

    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "stream=index,codec_type,duration", "-of", "json", media_url,
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        streams = json.loads(result.stdout).get("streams") or []
        return [
            {
                "Index": stream.get("index"),
                "Type": stream.get("codec_type"),
                "Duration": None if stream.get("duration") in (None, "N/A")
                else float(stream["duration"]),
            }
            for stream in streams
            if stream.get("codec_type") in ("video", "audio")
        ], None
    except FileNotFoundError:
        return [], "ffprobe is not installed; stream durations are unverified"
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        ValueError,
        json.JSONDecodeError,
    ):
        return [], "ffprobe failed; stream durations are unverified"


def print_stream_durations(streams: List[dict]) -> None:
    counts = {kind: sum(stream.get("Type") == kind for stream in streams)
              for kind in ("video", "audio")}
    for kind in ("video", "audio"):
        matching = [stream for stream in streams if stream.get("Type") == kind]
        if not matching:
            print(f"{kind.title()} stream: none")
            continue
        for position, stream in enumerate(matching, 1):
            suffix = f" #{position}" if counts[kind] > 1 else ""
            duration = stream.get("Duration")
            value = "unknown" if duration is None else f"{duration:.6f}"
            print(f"{kind.title()} stream{suffix} duration: {value}")
    if counts["audio"]:
        print(
            "Audio tail content: UNVERIFIED by stream duration; run "
            "silencedetect/volumedetect (references/11-output-verification.md)"
        )


def get_media_info(
    client: OpenApiClient,
    media_id: str,
    region_id: str = "cn-shanghai"
) -> dict:
    """
    Get media info for a MediaId, including the signed (authenticated) play URL.

    Output buckets are typically private, so the plain OSS URL is not viewable;
    GetMediaInfo returns a time-limited signed URL that can be opened directly.

    Args:
        client: OpenAPI client instance
        media_id: Media asset ID to resolve
        region_id: Region ID

    Returns:
        A dict with the useful fields extracted from the response:
        {
            "MediaId": ..., "MediaType": ..., "FileName": ...,
            "Duration": ..., "Width": ..., "Height": ...,
            "FileUrl": <signed url>, "OssUrl": <raw oss url>, "Region": ...
        }
    """
    params = {
        "MediaId": media_id,
        "OutputType": "oss"
    }

    response = call_api(client, "GetMediaInfo", params, region_id)

    media_info = response.get("MediaInfo", {})
    basic = media_info.get("MediaBasicInfo", {})
    file_info_list = media_info.get("FileInfoList", [])

    result = {
        "MediaId": basic.get("MediaId") or media_id,
        "MediaType": basic.get("MediaType"),
        "Title": basic.get("Title"),
        "Status": basic.get("Status"),
        "Region": region_id,
        "FileUrl": None,
        "OssUrl": None,
        "Duration": None,
        "Width": None,
        "Height": None,
        "FileName": None,
    }

    # The signed URL and technical metadata live in FileInfoList[].FileBasicInfo
    if file_info_list:
        file_basic = file_info_list[0].get("FileBasicInfo", {})
        result["FileUrl"] = file_info_list[0].get("FileUrl") or file_basic.get("FileUrl")
        result["OssUrl"] = file_basic.get("FileUrl")
        result["FileName"] = file_basic.get("FileName")
        result["Duration"] = file_basic.get("Duration")
        result["Width"] = file_basic.get("Width")
        result["Height"] = file_basic.get("Height")

    if not result["FileUrl"]:
        raise Exception(f"Failed to get a playable URL for MediaId {media_id} from response: {response}")

    return result


def validate_function_name(function_name: str) -> str:
    """
    Validate an intelligent production FunctionName against the API whitelist.

    Args:
        function_name: FunctionName to validate

    Returns:
        Validated function name

    Raises:
        ValidationError: If the function name is not supported
    """
    if function_name not in IPRODUCTION_FUNCTIONS:
        raise ValidationError(
            f"Invalid FunctionName '{function_name}'. Must be one of: "
            f"{', '.join(IPRODUCTION_FUNCTIONS)}"
        )
    return function_name


def validate_function_region(function_name: str, region_id: str) -> str:
    """
    Refuse an intelligent production job in a region that has no AI features.

    The API answers a wrong-region submission with InvalidParameter.FunctionNotSupported
    only after the call is made, so the gate has to be local (SKILL.md §2.1, §7.1).

    Args:
        function_name: Validated FunctionName
        region_id: Region the job would be submitted in

    Returns:
        Validated region id

    Raises:
        ValidationError: If the region cannot run the algorithm
    """
    if region_id not in AI_FEATURE_REGIONS:
        raise ValidationError(
            f"'{function_name}' is an AI feature and cannot run in '{region_id}'. "
            f"It needs one of {', '.join(AI_FEATURE_REGIONS)}, with the input asset "
            f"and the output bucket in that same region. Ask the user to pick the "
            f"region and a matching bucket — do not substitute either one yourself, "
            f"and do not retry in '{region_id}' (SKILL.md §2.1)."
        )
    return region_id


def detect_media_type(media: str) -> str:
    """
    Infer whether a media reference is an OSS path or a media asset id.

    Args:
        media: OSS address (oss:// or http(s)://) or a media asset id

    Returns:
        "OSS" or "Media"
    """
    return "OSS" if media.startswith(OSS_MEDIA_PREFIXES) else "Media"


def build_iproduction_input(media: str, media_type: Optional[str] = None) -> dict:
    """
    Build the Input object of SubmitIProductionJob.

    Args:
        media: OSS address or media asset id of the source file
        media_type: "OSS" or "Media"; inferred from the address when omitted

    Returns:
        Input dict, e.g. {"Type": "OSS", "Media": "oss://bucket/input.mp4"}

    Raises:
        ValidationError: If the media reference does not match the media type
    """
    if not media:
        raise ValidationError("Input media must not be empty")

    resolved_type = media_type or detect_media_type(media)
    if resolved_type not in ("OSS", "Media"):
        raise ValidationError("Input type must be either 'OSS' or 'Media'")

    if resolved_type == "OSS" and not media.startswith(OSS_MEDIA_PREFIXES):
        raise ValidationError(
            "An OSS input must be 'oss://bucket/object' or "
            "'http(s)://bucket.oss-[regionId].aliyuncs.com/object'"
        )
    if resolved_type == "Media":
        validate_media_id(media)

    return {"Type": resolved_type, "Media": media}


def build_iproduction_output(
    media: str,
    function_name: str,
    media_type: Optional[str] = None,
    biz: Optional[str] = None,
    output_url: Optional[str] = None
) -> dict:
    """
    Build the Output object of SubmitIProductionJob.

    Args:
        media: OSS address, an existing media asset id, or "" to create a new asset
               (only valid when the output type is "Media")
        function_name: FunctionName of the job — used to enforce the placeholders
                       that multi-output algorithms require
        media_type: "OSS" or "Media"; inferred from the address when omitted
        biz: "IMS" or "VOD" — which media asset library a new asset is written to
        output_url: OSS address of the output file when the type is "Media"

    Returns:
        Output dict

    Raises:
        ValidationError: If the output combination is invalid or a required
                         placeholder is missing
    """
    resolved_type = media_type or (detect_media_type(media) if media else "Media")
    if resolved_type not in ("OSS", "Media"):
        raise ValidationError("Output type must be either 'OSS' or 'Media'")

    if resolved_type == "OSS":
        if not media:
            raise ValidationError("An OSS output requires an output address")
        if not media.startswith(OSS_MEDIA_PREFIXES):
            raise ValidationError(
                "An OSS output must be 'oss://bucket/object' or "
                "'http(s)://bucket.oss-[RegionId].aliyuncs.com/object'"
            )
        required_placeholder = IPRODUCTION_REQUIRED_PLACEHOLDERS.get(function_name)
        if required_placeholder and required_placeholder not in media:
            raise ValidationError(
                f"{function_name} writes several output files, so its OSS output path must "
                f"contain the {required_placeholder} placeholder — otherwise the files "
                f"overwrite each other. Example: "
                f"oss://bucket/iproduction/{{source}}-{required_placeholder}.out"
            )
    elif media:
        validate_media_id(media)

    output = {"Type": resolved_type, "Media": media}

    if biz:
        if biz not in IPRODUCTION_OUTPUT_BIZ:
            raise ValidationError(
                f"Output Biz must be one of: {', '.join(IPRODUCTION_OUTPUT_BIZ)}"
            )
        output["Biz"] = biz

    if output_url:
        if resolved_type != "Media":
            raise ValidationError("OutputUrl only applies when the output type is 'Media'")
        if not output_url.startswith(OSS_MEDIA_PREFIXES):
            raise ValidationError("OutputUrl must be an OSS address")
        output["OutputUrl"] = output_url

    return output


def submit_iproduction_job(
    client: OpenApiClient,
    function_name: str,
    input_media: dict,
    output_media: dict,
    region_id: str = "cn-shanghai",
    name: Optional[str] = None,
    job_params: Optional[dict] = None,
    template_id: Optional[str] = None,
    model_id: Optional[str] = None,
    pipeline_id: Optional[str] = None,
    priority: Optional[int] = None,
    user_data: Optional[str] = None
) -> str:
    """
    Submit an intelligent production (algorithm) job to ICE.

    One source file in, one algorithm out — smart cover, logo/subtitle erasure,
    caption extraction, matting, beauty, portrait conversion, audio analysis, etc.

    Args:
        client: OpenAPI client instance
        function_name: Algorithm to run (see IPRODUCTION_FUNCTIONS)
        input_media: Input object from build_iproduction_input()
        output_media: Output object from build_iproduction_output()
        region_id: Region ID
        name: Optional job name (max 100 characters)
        job_params: Algorithm parameters — serialized to the JobParams JSON string
        template_id: Optional template ID
        model_id: Optional algorithm model ID (empty = the function's default model)
        pipeline_id: Optional pipeline ID (ScheduleConfig)
        priority: Optional priority 1-10 (ScheduleConfig)
        user_data: Optional user data returned as-is (max 256 characters)

    Returns:
        The intelligent production JobId
    """
    params = {
        "FunctionName": function_name,
        "Input": json.dumps(input_media, ensure_ascii=False),
        "Output": json.dumps(output_media, ensure_ascii=False),
    }

    if name:
        params["Name"] = name
    if job_params:
        params["JobParams"] = json.dumps(job_params, ensure_ascii=False)
    if template_id:
        params["TemplateId"] = template_id
    if model_id:
        params["ModelId"] = model_id
    if user_data:
        params["UserData"] = user_data

    schedule_config = {}
    if pipeline_id:
        schedule_config["PipelineId"] = pipeline_id
    if priority is not None:
        schedule_config["Priority"] = priority
    if schedule_config:
        params["ScheduleConfig"] = json.dumps(schedule_config, ensure_ascii=False)

    response = call_api(client, "SubmitIProductionJob", params, region_id)

    job_id = response.get("JobId")
    if not job_id:
        raise Exception(f"Failed to get JobId from response: {response}")

    return job_id


def query_iproduction_job(
    client: OpenApiClient,
    job_id: str,
    region_id: str = "cn-shanghai"
) -> dict:
    """
    Query an intelligent production job.

    Args:
        client: OpenAPI client instance
        job_id: Intelligent production JobId
        region_id: Region ID the job was submitted in

    Returns:
        The response body, whose fields are flat: Status ("Queuing", "Analysing",
        "Success", "Fail"), FunctionName, Result (JSON string), OutputFiles,
        OutputUrls, OutputMediaIds, CreateTime, FinishTime, ...
    """
    response = call_api(client, "QueryIProductionJob", {"JobId": job_id}, region_id)

    if not response.get("Status"):
        raise Exception(f"Failed to get job status from response: {response}")

    return response


def wait_for_iproduction_job(
    client: OpenApiClient,
    job_id: str,
    region_id: str = "cn-shanghai",
    poll_interval: int = 5,
    max_wait_time: int = 3600,
    verbose: bool = True
) -> dict:
    """
    Poll an intelligent production job until it finishes.

    Args:
        client: OpenAPI client instance
        job_id: Intelligent production JobId
        region_id: Region ID
        poll_interval: Seconds between status checks
        max_wait_time: Maximum seconds to wait
        verbose: Print progress messages

    Returns:
        The final job response (Status == "Success")

    Raises:
        Exception: If the job reports "Fail" or an unknown status
        TimeoutError: If the job does not finish within max_wait_time
    """
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait_time:
            raise TimeoutError(f"Job {job_id} did not complete within {max_wait_time} seconds")

        job = query_iproduction_job(client, job_id, region_id)
        status = job.get("Status")

        if verbose:
            print(f"[{int(elapsed)}s] Job {job_id}: {status}")

        if status == "Success":
            return job
        elif status == "Fail":
            raise Exception(f"Job failed: {job.get('Result') or job}")
        elif status in IPRODUCTION_RUNNING_STATUSES:
            time.sleep(poll_interval)
        else:
            raise Exception(f"Unknown job status: {status}")


def print_iproduction_job(job: dict) -> None:
    """
    Print the interesting fields of an intelligent production job response.

    Args:
        job: Response returned by query_iproduction_job() / wait_for_iproduction_job()
    """
    print(f"Status: {job.get('Status')}")
    if job.get("FunctionName"):
        print(f"FunctionName: {job['FunctionName']}")
    if job.get("CreateTime"):
        print(f"CreateTime: {job['CreateTime']}")
    if job.get("FinishTime"):
        print(f"FinishTime: {job['FinishTime']}")

    for label, key in (("Output files", "OutputFiles"),
                       ("Output URLs", "OutputUrls"),
                       ("Output MediaIds", "OutputMediaIds")):
        values = [value for value in (job.get(key) or []) if value]
        if values:
            print(f"{label}:")
            for value in values:
                print(f"  - {value}")

    result = job.get("Result")
    if result:
        # Result is a JSON string whose shape depends on FunctionName
        try:
            parsed = json.loads(result)
        except (TypeError, ValueError):
            print(f"Result: {result}")
        else:
            print("Result:")
            print(json.dumps(parsed, ensure_ascii=False, indent=2))


def oss_uri_to_https(uri: str, region_id: str) -> Optional[str]:
    """
    Convert an OSS address to an HTTPS URL, for the output existence pre-check.

    Args:
        uri: "oss://bucket/object" or an https OSS URL
        region_id: Region used to build the OSS endpoint

    Returns:
        An HTTPS URL, or None when the address cannot be checked
        (unknown scheme, or the path still contains placeholders)
    """
    if "{" in uri:
        # Placeholders are filled in by the service — nothing to check yet
        return None
    if uri.startswith(("http://", "https://")):
        return uri
    if uri.startswith("oss://"):
        bucket, _, object_key = uri[len("oss://"):].partition("/")
        if not bucket or not object_key:
            return None
        return f"https://{bucket}.oss-{region_id}.aliyuncs.com/{object_key}"
    return None


def confirm_iproduction_submission(
    function_name: str,
    input_media: dict,
    output_media: dict,
    region_id: str,
    job_params: Optional[dict] = None,
    skip_confirmation: bool = False
) -> bool:
    """
    Perform protective pre-checks before submitting an intelligent production job.

    Args:
        function_name: Algorithm to run
        input_media: Input object
        output_media: Output object
        region_id: Region ID
        job_params: Algorithm parameters, printed for review
        skip_confirmation: Skip the interactive prompt

    Returns:
        True if the operation should proceed, False if cancelled
    """
    print("\n" + "=" * 60)
    print("⚠️  HIGH-RISK OPERATION: Intelligent Production Job Submission")
    print("=" * 60)
    print(f"\n🧠 Function: {function_name}")
    print(f"📥 Input: {input_media['Type']} {input_media['Media']}")
    print(f"📤 Output: {output_media['Type']} {output_media.get('Media') or '(new media asset)'}")
    if output_media.get("OutputUrl"):
        print(f"📤 OutputUrl: {output_media['OutputUrl']}")
    if job_params:
        print(f"⚙️  JobParams: {json.dumps(job_params, ensure_ascii=False)}")
    print(f"🌍 Region: {region_id}")

    # Check if the output object already exists (only possible for a fixed OSS path)
    output_https = oss_uri_to_https(output_media.get("Media") or "", region_id) \
        if output_media["Type"] == "OSS" else None
    if output_https:
        print("\n🔍 Pre-check: Checking if output file exists...")
        if check_output_path_exists(output_https, region_id):
            print("⚠️  WARNING: Output file already exists!")
            print("   The existing file will be OVERWRITTEN.")
        else:
            print("✅ Output path is clear (file does not exist)")

    print("\n💰 Cost Warning:")
    print("   This operation will incur charges for:")
    print("   - Intelligent production (algorithm) processing")
    print("   - OSS storage for output files")

    print("\n" + "=" * 60)

    import os
    if skip_confirmation or os.environ.get('VIDEO_EDITOR_SKIP_CONFIRMATION') == '1':
        print(SKIP_CONFIRM_NOTE)
        return True

    try:
        response = input("\nDo you want to proceed? [y/N]: ").strip().lower()
        return response in ('y', 'yes')
    except (EOFError, KeyboardInterrupt):
        print("\n⚠️  Non-interactive environment detected.")
        print("   Set VIDEO_EDITOR_SKIP_CONFIRMATION=1 to skip this prompt.")
        return False


def wait_for_job_completion(
    client: OpenApiClient,
    job_id: str,
    region_id: str = "cn-shanghai",
    poll_interval: int = 5,
    max_wait_time: int = 3600,
    verbose: bool = True
) -> dict:
    """
    Wait for a job to complete by polling.
    
    Args:
        client: OpenAPI client instance
        job_id: Job ID to wait for
        region_id: Region ID
        poll_interval: Seconds between status checks
        max_wait_time: Maximum seconds to wait
        verbose: Print progress messages
    
    Returns:
        The complete final MediaProducingJob record.
    """
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait_time:
            raise TimeoutError(f"Job {job_id} did not complete within {max_wait_time} seconds")
        
        job = get_media_producing_job(client, job_id, region_id)
        status = job["Status"]
        
        if verbose:
            print(f"[{int(elapsed)}s] Job {job_id}: {status}")
        
        if status == "Success":
            return job
        elif status == "Failed":
            raise Exception(f"Job failed: {job.get('Message')}")
        elif status in ["Init", "Queuing", "Processing"]:
            time.sleep(poll_interval)
        else:
            raise Exception(f"Unknown job status: {status}")


def check_output_path_exists(media_url: str, region_id: str) -> bool:
    """
    Check if the output media URL already exists in OSS.
    
    Args:
        media_url: The output media URL to check
        region_id: Region ID for OSS client
        
    Returns:
        True if file exists, False otherwise
    """
    try:
        # Parse bucket and object key from URL
        # URL format: https://bucket.oss-region.aliyuncs.com/path/to/file.mp4
        from urllib.parse import urlparse
        parsed = urlparse(media_url)
        
        if not parsed.netloc or not parsed.path:
            return False
        
        # Extract bucket from hostname (bucket.oss-region.aliyuncs.com)
        hostname_parts = parsed.netloc.split('.')
        if len(hostname_parts) < 4:
            return False
        
        bucket_name = hostname_parts[0]
        object_key = parsed.path.lstrip('/')
        
        # Try to head object to check existence
        credential = CredentialClient()
        config = open_api_models.Config(credential=credential)
        config.endpoint = f"oss-{region_id}.aliyuncs.com"
        config.user_agent = USER_AGENT
        client = OpenApiClient(config)
        
        params = {
            "bucketName": bucket_name,
            "objectName": object_key
        }
        
        api_request = open_api_models.OpenApiRequest(
            query=OpenApiUtilClient.query(params)
        )
        runtime = util_models.RuntimeOptions()
        api_params = open_api_models.Params(
            action="HeadObject",
            version="2019-05-17",
            protocol="HTTPS",
            method="HEAD",
            auth_type="AK",
            style="ROA",
            pathname=f"/{object_key}",
            req_body_type="json",
            body_type="json"
        )
        
        response = client.call_api(api_params, api_request, runtime)
        # If we get here without exception, object exists
        return True
        
    except Exception:
        # Any error means file doesn't exist or we can't check
        return False


def confirm_high_risk_operation(output_config: dict, region_id: str, skip_confirmation: bool = False) -> bool:
    """
    Perform protective pre-checks before high-risk operations.
    
    Args:
        output_config: Output media configuration
        region_id: Region ID
        
    Returns:
        True if operation should proceed, False if cancelled
    """
    media_url = output_config.get("MediaURL", "")
    width = output_config.get("Width", "default")
    height = output_config.get("Height", "default")
    
    print("\n" + "=" * 60)
    print("⚠️  HIGH-RISK OPERATION: Media Producing Job Submission")
    print("=" * 60)
    print(f"\n📁 Output URL: {media_url}")
    print(f"📐 Resolution: {width} x {height}")
    print(f"🌍 Region: {region_id}")
    
    # Check if output file already exists
    print("\n🔍 Pre-check: Checking if output file exists...")
    if check_output_path_exists(media_url, region_id):
        print("⚠️  WARNING: Output file already exists!")
        print("   The existing file will be OVERWRITTEN.")
    else:
        print("✅ Output path is clear (file does not exist)")
    
    # Cost warning
    print("\n💰 Cost Warning:")
    print("   This operation will incur charges for:")
    print("   - Media processing/transcoding")
    print("   - OSS storage for output file")
    
    print("\n" + "=" * 60)
    
    # Check for skip confirmation flag (command line or environment variable)
    import os
    if skip_confirmation or os.environ.get('VIDEO_EDITOR_SKIP_CONFIRMATION') == '1':
        print(SKIP_CONFIRM_NOTE)
        return True
    
    try:
        response = input("\nDo you want to proceed? [y/N]: ").strip().lower()
        return response in ('y', 'yes')
    except (EOFError, KeyboardInterrupt):
        # Non-interactive environment
        print("\n⚠️  Non-interactive environment detected.")
        print("   Set VIDEO_EDITOR_SKIP_CONFIRMATION=1 to skip this prompt.")
        return False


def mask_token(token: str, visible_chars: int = 8) -> str:
    """
    Mask a token for logging - show only first N characters.
    
    Args:
        token: The token to mask
        visible_chars: Number of characters to show at the start
        
    Returns:
        Masked token string
    """
    if len(token) <= visible_chars:
        return token
    return f"{token[:visible_chars]}...***"


def submit_and_wait(
    timeline: dict,
    output_media_config: dict,
    region_id: str = "cn-shanghai",
    poll_interval: int = 5,
    max_wait_time: int = 3600,
    verbose: bool = True,
    client_token: Optional[str] = None
) -> str:
    """
    Submit a job and wait for completion.
    
    This is the main function for typical usage.
    
    Args:
        timeline: Timeline JSON object
        output_media_config: Output configuration
        region_id: Alibaba Cloud region
        poll_interval: Seconds between status checks
        max_wait_time: Maximum seconds to wait
        verbose: Print progress messages
        client_token: Optional ClientToken for idempotency
    
    Returns:
        Output media URL
    
    Example:
        timeline = {
            "VideoTracks": [...],
            "AudioTracks": [...],
            "SubtitleTracks": []
        }
        output_config = {
            "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/output.mp4",
            "Width": 1920,
            "Height": 1080
        }
        url = submit_and_wait(timeline, output_config)
        print(f"Video ready: {url}")
    """
    client = create_client(region_id)
    
    if verbose:
        print("Submitting job...")
    
    job_id, used_token = submit_media_producing_job(
        client, timeline, output_media_config, region_id, client_token
    )
    
    if verbose:
        print(f"Job submitted: {job_id}")
        print(f"ClientToken: {mask_token(used_token)} (save this for retry if needed)")
    
    job = wait_for_job_completion(
        client, job_id, region_id, poll_interval, max_wait_time, verbose
    )
    media_url = job.get("MediaURL")
    
    if verbose:
        print("Job completed!")
        print(f"Output URL: {media_url}")
    
    return media_url


# ---------------------------------------------------------------------------
# ASR — dialogue timeline (references/17-snapshot-and-asr.md §1)
# ---------------------------------------------------------------------------

SMART_HANDLE_RUNNING_STATES = ["Created", "Executing"]

# Only these three EditingConfig fields exist. Anything else is accepted by the
# API and silently ignored — measured, see 17-snapshot-and-asr.md §1.3.
ASR_EDITING_CONFIG_FIELDS = {
    "SentenceMaxLength",
    "EnableSemanticSentenceDetection",
    "HotwordLibraryIdList",
}

# Sentence-final punctuation. A segment ending here is a real sentence
# boundary; one ending without it was truncated mid-sentence by
# SentenceMaxLength (17-snapshot-and-asr.md §1.5).
SENTENCE_FINAL_PUNCT = "，。？！、；,.?!;"


def submit_asr_job(
    client: OpenApiClient,
    media: str,
    region_id: str,
    sentence_max_length: Optional[int] = None,
    semantic: bool = False,
    hotword_library_id: Optional[str] = None,
    start_time: Optional[str] = None,
    duration: Optional[str] = None,
    title: Optional[str] = None,
) -> str:
    """Submit a SubmitASRJob. Returns the JobId."""
    if not media:
        raise ValidationError("ASR input must not be empty")
    if detect_media_type(media) == "Media":
        validate_media_id(media)

    editing_config: dict = {}
    if sentence_max_length is not None:
        if not isinstance(sentence_max_length, int) or sentence_max_length < 1:
            raise ValidationError("--sentence-max-length must be a positive integer")
        editing_config["SentenceMaxLength"] = sentence_max_length
    if semantic:
        editing_config["EnableSemanticSentenceDetection"] = True
    if hotword_library_id:
        editing_config["HotwordLibraryIdList"] = hotword_library_id

    params: dict = {"InputFile": media}
    if editing_config:
        params["EditingConfig"] = json.dumps(editing_config, ensure_ascii=False)
    if start_time:
        params["StartTime"] = start_time
    if duration:
        params["Duration"] = duration
    if title:
        params["Title"] = title

    response = call_api(client, "SubmitASRJob", params, region_id)
    job_id = response.get("JobId")
    if not job_id:
        raise Exception(f"SubmitASRJob returned no JobId: {response}")
    return job_id


def get_smart_handle_job(client: OpenApiClient, job_id: str, region_id: str) -> dict:
    """Query a smart job (ASR / TextToSpeech / TextGenerate) by JobId."""
    return call_api(client, "GetSmartHandleJob", {"JobId": job_id}, region_id)


def wait_for_smart_handle_job(
    client: OpenApiClient,
    job_id: str,
    region_id: str,
    poll_interval: int = 10,
    max_wait: int = 900,
) -> dict:
    """Poll GetSmartHandleJob until Finished / Failed."""
    waited = 0
    while waited <= max_wait:
        job = get_smart_handle_job(client, job_id, region_id)
        state = job.get("State")
        if state in ("Finished", "Failed"):
            return job
        if state not in SMART_HANDLE_RUNNING_STATES:
            print(f"  unexpected State '{state}' — still polling")
        print(f"  {state} ({waited}s)")
        time.sleep(poll_interval)
        waited += poll_interval
    raise Exception(f"ASR job {job_id} did not finish within {max_wait}s")


def parse_asr_result(job: dict) -> List[dict]:
    """Pull the segment list out of JobResult.AiResult (a JSON *string*).

    Each segment gains two derived fields the cut rules depend on:
      gap_before  — seconds of silence since the previous segment
      sentence_end — whether it ends on sentence-final punctuation
    """
    state = job.get("State")
    if state == "Failed":
        raise Exception(
            f"ASR job failed: {job.get('ErrorCode')} {job.get('ErrorMessage')}"
        )
    raw = (job.get("JobResult") or {}).get("AiResult") or job.get("Output")
    if not raw:
        raise Exception(f"ASR job has no AiResult (State={state})")
    try:
        items = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise Exception(f"AiResult is not valid JSON: {exc}")
    if not isinstance(items, list):
        raise Exception("AiResult is not a JSON array")

    segments: List[dict] = []
    prev_end: Optional[float] = None
    for item in items:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content", ""))
        start = float(item.get("from", 0.0))
        end = float(item.get("to", 0.0))
        segments.append({
            "content": content,
            "from": start,
            "to": end,
            "gap_before": None if prev_end is None else round(start - prev_end, 3),
            "sentence_end": content[-1:] in SENTENCE_FINAL_PUNCT,
        })
        prev_end = end
    return segments


def print_asr_segments(segments: List[dict], gap_threshold: float = 0.3) -> None:
    """One line per segment. Marks seams that satisfy both cut conditions."""
    print(f"{len(segments)} segments")
    for i, seg in enumerate(segments):
        gap = seg["gap_before"]
        gap_txt = "        " if gap is None else f"gap {gap:5.2f}"
        # A cut may sit before this segment only if the *previous* segment
        # closed a sentence and the gap is wide enough (§1.5).
        prev_closed = segments[i - 1]["sentence_end"] if i else True
        cuttable = i > 0 and prev_closed and gap is not None and gap >= gap_threshold
        mark = "CUT" if cuttable else ("   " if i else "   ")
        print(f"  [{i:>3}] {seg['from']:>7.2f}-{seg['to']:<7.2f} {gap_txt} {mark}  "
              f"{seg['content']}")
    cuttable_total = sum(
        1 for i in range(1, len(segments))
        if segments[i - 1]["sentence_end"]
        and segments[i]["gap_before"] is not None
        and segments[i]["gap_before"] >= gap_threshold
    )
    print(f"  {cuttable_total} seam(s) satisfy punctuation + gap >= {gap_threshold}s "
          f"(references/17 §1.5)")


# ---------------------------------------------------------------------------
# Snapshot — frames, filmstrip, WebVTT time map (references/17 §2)
# ---------------------------------------------------------------------------

# mode → (template Subtype, TemplateConfig.Type, required output placeholder)
SNAPSHOT_MODES = {
    "normal": (1, "Normal", "{Count}"),
    "sprite": (2, "Sprite", "{TileCount}"),
    "webvtt": (3, "WebVtt", ".vtt"),
}

SNAPSHOT_TEMPLATE_TYPE = 2
SNAPSHOT_RUNNING_STATES = ["Init", "Queuing", "Analysing", "Processing", "Executing"]

# GetSnapshotUrls signing ceiling — 36 h, verified (references/17 §2.7).
SNAPSHOT_URL_MAX_TIMEOUT = 129600


def build_snapshot_template_config(
    mode: str,
    time_ms: int = 0,
    count: int = 40,
    interval: int = 2,
    width: Optional[int] = None,
    height: Optional[int] = None,
    columns: Optional[int] = None,
    lines: Optional[int] = None,
) -> dict:
    """Build a snapshot TemplateConfig.

    FrameType is pinned to 'normal'. 'intra' silently returns only the frames
    that happen to sit on an I-frame — 13 of 40 on a measured 89.6 s source —
    while the job still reports Success (references/17 §2.2).
    """
    if mode not in SNAPSHOT_MODES:
        raise ValidationError(
            f"Unknown snapshot mode '{mode}'. Valid: {', '.join(SNAPSHOT_MODES)}"
        )
    _subtype, config_type, _placeholder = SNAPSHOT_MODES[mode]

    if count < 1:
        raise ValidationError("--count must be >= 1")
    if interval < 1:
        raise ValidationError("--interval must be >= 1 (seconds)")
    if time_ms < 0:
        raise ValidationError("--time must be >= 0 (milliseconds)")

    config: dict = {
        "Type": config_type,
        "FrameType": "normal",
        "Time": time_ms,          # milliseconds
        "Count": count,
        "Interval": interval,     # seconds
    }
    if width:
        config["Width"] = width
    if height:
        config["Height"] = height

    if mode == "sprite":
        sprite: dict = {}
        if width:
            sprite["CellWidth"] = width
        if height:
            sprite["CellHeight"] = height
        if columns:
            sprite["Columns"] = columns
        if lines:
            sprite["Lines"] = lines
        if sprite:
            sprite.setdefault("Padding", 4)
            sprite.setdefault("Margin", 8)
            config["SpriteSnapshotConfig"] = sprite
    elif mode == "webvtt":
        # Vtt rejects SpriteSnapshotConfig outright:
        # InvalidParameter.NotSupport (references/17 §2.3). Layout is server-chosen.
        config["IsSptFrag"] = True

    return config


def validate_snapshot_output(output: str, mode: str) -> str:
    """Check the output object carries the placeholder this mode requires."""
    if not output.startswith(OSS_MEDIA_PREFIXES):
        raise ValidationError(
            "Snapshot output must be 'oss://bucket/object' or an http(s) OSS URL"
        )
    _subtype, _config_type, placeholder = SNAPSHOT_MODES[mode]
    if mode == "webvtt":
        if not output.endswith(".vtt"):
            raise ValidationError(
                "A WebVtt snapshot output object must end in '.vtt' (references/17 §2.6)"
            )
    elif placeholder not in output:
        raise ValidationError(
            f"A {mode} snapshot output object must contain the {placeholder} "
            f"placeholder, otherwise the files overwrite each other "
            f"(references/17 §2.6)"
        )
    return output


def ensure_snapshot_template(
    client: OpenApiClient,
    region_id: str,
    mode: str,
    config: dict,
) -> str:
    """Reuse a snapshot template of the same mode, else create it.

    Per-job values are supplied through OverwriteParams, so Time/Count/Interval
    changes must not create another persistent template.
    """
    subtype, config_type, _placeholder = SNAPSHOT_MODES[mode]

    try:
        listed = call_api(
            client, "ListCustomTemplates",
            {"Type": SNAPSHOT_TEMPLATE_TYPE, "PageSize": 100}, region_id,
        )
        for tpl in listed.get("CustomTemplateList") or []:
            raw = tpl.get("TemplateConfig")
            if not raw:
                continue
            try:
                existing = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                continue
            if existing.get("Type") == config_type:
                template_id = tpl.get("TemplateId")
                if template_id:
                    print(f"  reusing snapshot template: {template_id}")
                    return template_id
    except Exception as exc:  # listing is an optimisation, never fatal
        print(f"  could not list templates ({exc}); creating a new one")

    created = call_api(client, "CreateCustomTemplate", {
        "Name": f"skill-snapshot-{mode}",
        "Type": SNAPSHOT_TEMPLATE_TYPE,
        "Subtype": subtype,
        "TemplateConfig": json.dumps(config, ensure_ascii=False),
    }, region_id)
    template_id = (created.get("CustomTemplate") or {}).get("TemplateId")
    if not template_id:
        raise Exception(f"CreateCustomTemplate returned no TemplateId: {created}")
    print(f"  created snapshot template: {template_id}")
    return template_id


def submit_snapshot_job(
    client: OpenApiClient,
    media: str,
    output: str,
    template_id: str,
    region_id: str,
    overwrite_params: Optional[dict] = None,
) -> str:
    """Submit a SubmitSnapshotJob. Returns the JobId."""
    input_obj = build_iproduction_input(media)
    template_config: dict = {"TemplateId": template_id}
    if overwrite_params:
        template_config["OverwriteParams"] = overwrite_params

    response = call_api(client, "SubmitSnapshotJob", {
        "Input": json.dumps(input_obj, ensure_ascii=False),
        "Output": json.dumps({"Type": "OSS", "Media": output}, ensure_ascii=False),
        "TemplateConfig": json.dumps(template_config, ensure_ascii=False),
    }, region_id)
    job_id = response.get("JobId")
    if not job_id:
        raise Exception(f"SubmitSnapshotJob returned no JobId: {response}")
    return job_id


def wait_for_snapshot_job(
    client: OpenApiClient,
    job_id: str,
    region_id: str,
    poll_interval: int = 6,
    max_wait: int = 600,
) -> dict:
    """Poll GetSnapshotJob until a terminal state."""
    waited = 0
    while waited <= max_wait:
        response = call_api(client, "GetSnapshotJob", {"JobId": job_id}, region_id)
        job = response.get("SnapshotJob") or response
        state = job.get("State") or job.get("Status")
        if state in ("Success", "Finished"):
            return response
        if state in ("Fail", "Failed"):
            raise Exception(
                f"Snapshot job {job_id} failed: "
                f"{job.get('Message') or job.get('ErrorMessage') or state}"
            )
        print(f"  {state} ({waited}s)")
        time.sleep(poll_interval)
        waited += poll_interval
    raise Exception(f"Snapshot job {job_id} did not finish within {max_wait}s")


def get_snapshot_urls(
    client: OpenApiClient,
    job_id: str,
    region_id: str,
    timeout: int = SNAPSHOT_URL_MAX_TIMEOUT,
) -> dict:
    """Fetch signed snapshot URLs. Timeout tops out at 36 h (references/17 §2.7)."""
    if timeout < 1 or timeout > SNAPSHOT_URL_MAX_TIMEOUT:
        raise ValidationError(
            f"--url-timeout must be between 1 and {SNAPSHOT_URL_MAX_TIMEOUT} seconds"
        )
    return call_api(client, "GetSnapshotUrls", {
        "JobId": job_id, "PageSize": 30, "OrderBy": "Asc", "Timeout": timeout,
    }, region_id)


def print_snapshot_urls(result: dict) -> None:
    urls = result.get("SnapshotUrls") or []
    print(f"Total: {result.get('Total')}  ({len(urls)} URL(s) on this page)")
    for url in urls:
        print(f"  {url}")
    if result.get("WebVTTUrl"):
        print(f"WebVTT: {result['WebVTTUrl']}")


# ---------------------------------------------------------------------------
# Project export — the AI-expanded Timeline (references/21-timeline-export.md)
# ---------------------------------------------------------------------------
# A submitted Timeline carries AI *declarations* (AI_ASR, AI_TTS, AI_Avatar,
# VideoDetext): placeholders whose real media and real timing only exist once the
# engine has run the workflow. SubmitProjectExportJob returns the expanded
# Timeline — real MediaURLs, real durations, ASR sentences as an srt subtitle
# track — which is what a follow-up fine-tune has to start from.

PROJECT_EXPORT_TYPES = ["BaseTimeline", "AdobePremierePro"]

# AdobePremierePro export is region-limited; BaseTimeline is not.
PROJECT_EXPORT_PR_REGIONS = ["cn-shanghai", "cn-beijing", "cn-hangzhou", "cn-shenzhen"]

# GetProjectExportJob statuses that mean "still running". The job waits for any
# unfinished workflow task (sub-job mode), so Processing can last as long as the
# ASR / detext / TTS run it depends on.
PROJECT_EXPORT_RUNNING_STATUSES = ["Init", "Processing"]

# Clip Types / effect Types that the export expands. Anything from this set still
# present in the exported Timeline means the expansion did not cover it.
WORKFLOW_TASK_TYPES = {"AI_TTS", "AI_ASR", "AI_Avatar", "VideoDetext"}


def build_project_export_output_config(
    bucket: str,
    prefix: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> dict:
    """
    Build the OutputMediaConfig of a project export job.

    This is *not* the producing-job OutputMediaConfig: an export job writes
    intermediate artefacts (TTS audio, avatar takes, srt files) into a bucket and
    returns the Timeline in the response, so it takes Bucket/Prefix instead of a
    single MediaURL.
    """
    if not bucket or not bucket.strip():
        raise ValidationError("--bucket must not be empty")
    bucket = bucket.strip()
    if bucket.startswith(OSS_MEDIA_PREFIXES):
        raise ValidationError(
            "--bucket takes a bare bucket name, not an OSS address "
            "(e.g. 'my-bucket', not 'oss://my-bucket/path')"
        )
    if "/" in bucket:
        raise ValidationError(
            "--bucket takes a bare bucket name; put the path in --prefix"
        )

    for label, value in (("--width", width), ("--height", height)):
        if value is not None and not MIN_RESOLUTION <= value <= MAX_RESOLUTION:
            raise ValidationError(
                f"{label} must be between {MIN_RESOLUTION} and {MAX_RESOLUTION}"
            )

    config: dict = {"Bucket": bucket}
    if prefix:
        config["Prefix"] = prefix.strip().lstrip("/")
    if width:
        config["Width"] = width
    if height:
        config["Height"] = height
    return config


def validate_project_export_type(export_type: str, region_id: str) -> str:
    """Validate the export type, and the region for the region-limited one."""
    if export_type not in PROJECT_EXPORT_TYPES:
        raise ValidationError(
            f"Invalid --export-type '{export_type}'. Must be one of: "
            f"{', '.join(PROJECT_EXPORT_TYPES)}"
        )
    if export_type == "AdobePremierePro" and region_id not in PROJECT_EXPORT_PR_REGIONS:
        raise ValidationError(
            f"AdobePremierePro export is only available in: "
            f"{', '.join(PROJECT_EXPORT_PR_REGIONS)} (got '{region_id}')"
        )
    return export_type


def submit_project_export_job(
    client: OpenApiClient,
    output_media_config: dict,
    region_id: str,
    project_id: Optional[str] = None,
    timeline: Optional[dict] = None,
    export_type: str = "BaseTimeline",
    user_data: Optional[str] = None,
) -> str:
    """
    Submit a SubmitProjectExportJob. Returns the JobId.

    ProjectId and Timeline are mutually exclusive and one of them is required.
    Pass the ProjectId a producing job reported (GetMediaProducingJob) to expand
    exactly what was rendered; pass a Timeline to expand one that was never
    rendered.
    """
    if bool(project_id) == bool(timeline):
        raise ValidationError(
            "Pass exactly one of --project-id / --timeline — the API accepts "
            "ProjectId or Timeline, not both and not neither"
        )
    if project_id and (len(project_id) > 128
                       or not MEDIA_ID_PATTERN.match(project_id)):
        raise ValidationError(
            "ProjectId must be non-empty, alphanumeric with hyphens, and no "
            "longer than 128 characters"
        )

    params: dict = {
        "ExportType": export_type,
        "OutputMediaConfig": json.dumps(output_media_config, ensure_ascii=False),
    }
    if project_id:
        params["ProjectId"] = project_id
    else:
        params["Timeline"] = json.dumps(timeline, ensure_ascii=False)
    if user_data:
        params["UserData"] = user_data

    response = call_api(client, "SubmitProjectExportJob", params, region_id)
    job_id = response.get("JobId")
    if not job_id:
        raise Exception(f"SubmitProjectExportJob returned no JobId: {response}")
    return job_id


def get_project_export_job(
    client: OpenApiClient,
    job_id: str,
    region_id: str,
) -> dict:
    """Query a project export job. Returns the ProjectExportJob object."""
    response = call_api(client, "GetProjectExportJob", {"JobId": job_id}, region_id)
    job = response.get("ProjectExportJob") or {}
    if not job.get("Status"):
        raise Exception(f"Failed to get export job status from response: {response}")
    return job


def wait_for_project_export_job(
    client: OpenApiClient,
    job_id: str,
    region_id: str,
    poll_interval: int = 10,
    max_wait: int = 1800,
) -> dict:
    """
    Poll GetProjectExportJob until Success / Failed.

    max_wait is generous on purpose: when the source Timeline still holds an
    unfinished AI task the export blocks on it, so the wait covers a whole ASR or
    detext run and not just the timeline conversion.
    """
    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait:
            raise TimeoutError(
                f"Export job {job_id} did not complete within {max_wait} seconds. "
                f"It keeps running server-side — re-read it with: "
                f"export-timeline-status -j {job_id} -r {region_id}"
            )

        job = get_project_export_job(client, job_id, region_id)
        status = job.get("Status")
        print(f"[{int(elapsed)}s] Export job {job_id}: {status}")

        if status == "Success":
            return job
        if status == "Failed":
            raise Exception(
                f"Export job failed: {job.get('Code')} {job.get('Message')}"
            )
        if status not in PROJECT_EXPORT_RUNNING_STATUSES:
            print(f"  unexpected Status '{status}' — still polling")
        time.sleep(poll_interval)


def parse_exported_timeline(job: dict) -> dict:
    """Pull the expanded Timeline out of ExportResult.Timeline (a JSON *string*)."""
    raw = (job.get("ExportResult") or {}).get("Timeline")
    if not raw:
        raise Exception(
            f"Export job has no ExportResult.Timeline (Status={job.get('Status')}, "
            f"ExportType={job.get('ExportType')}). Only ExportType=BaseTimeline "
            f"returns a Timeline; AdobePremierePro returns ProjectUrl instead."
        )
    try:
        timeline = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise Exception(f"ExportResult.Timeline is not valid JSON: {exc}")
    if not isinstance(timeline, dict):
        raise Exception("ExportResult.Timeline is not a JSON object")
    return timeline


def summarize_exported_timeline(timeline: dict) -> None:
    """
    Print what the expansion produced, per track and per clip.

    The summary shows the two things a fine-tune needs and a raw JSON dump
    buries: the real time span of every clip, and where the ASR sentences went
    (an srt file referenced by a subtitle clip, not a Content string).
    """
    for track_key, clip_key in (("VideoTracks", "VideoTrackClips"),
                                ("AudioTracks", "AudioTrackClips"),
                                ("SubtitleTracks", "SubtitleTrackClips")):
        for track_index, track in enumerate(timeline.get(track_key) or []):
            if not isinstance(track, dict):
                continue
            clips = track.get(clip_key) or []
            print(f"{track_key}[{track_index}]  {len(clips)} clip(s)")
            for clip_index, clip in enumerate(clips):
                if not isinstance(clip, dict):
                    continue
                span = ""
                if _is_num(clip.get("TimelineIn")) and _is_num(clip.get("TimelineOut")):
                    span = f"{clip['TimelineIn']:.3f}-{clip['TimelineOut']:.3f}s"
                source = (clip.get("MediaURL") or clip.get("FileUrl")
                          or clip.get("MediaId") or "")
                if len(source) > 88:
                    source = source[:60] + "..." + source[-24:]
                bits = [f"  [{clip_index:>2}]", f"{span:>20}"]
                kind = clip.get("Type") or ("Subtitle" if clip.get("SubType") else "?")
                bits.append(str(kind))
                if clip.get("SubType"):
                    bits.append(f"({clip['SubType']})")
                if source:
                    bits.append(source)
                print(" ".join(bits))
                if clip.get("Content"):
                    print(f"        Content: {clip['Content']}")

    # The srt addresses are the one thing the response does not repeat: measured,
    # ExportResult.SrtList comes back empty, so the clip's FileUrl is the only
    # copy. Print them in full (the summary above truncates) and unsigned as
    # returned — they need signing before they can be read.
    srt_urls = [
        clip["FileUrl"]
        for clip, _path, _kind in _iter_clips(timeline)
        if clip.get("SubType") == "srt" and clip.get("FileUrl")
    ]
    if srt_urls:
        print("\nsrt file(s) holding the recognized text — sign before reading "
              "(private buckets 403 on the plain URL):")
        for url in srt_urls:
            print(f"  {url}")

    # Anything still declaring an AI task means the expansion did not cover it.
    unexpanded = []
    for clip, path, _kind in _iter_clips(timeline):
        if clip.get("Type") in WORKFLOW_TASK_TYPES:
            unexpanded.append(f"{path}.Type={clip['Type']}")
        for effect in _clip_effects(clip):
            if effect.get("Type") in WORKFLOW_TASK_TYPES:
                unexpanded.append(f"{path}.Effects[{effect['Type']}]")
    if unexpanded:
        print("\n  WARNING: still carrying AI declarations after export "
              "(they are expected to be gone — references/21 §2):")
        for item in unexpanded:
            print(f"  - {item}")


def print_project_export_job(job: dict, timeline_path: Optional[str] = None) -> None:
    """Print an export job, plus the expanded Timeline summary when it succeeded."""
    print(f"Status: {job.get('Status')}")
    if job.get("ExportType"):
        print(f"ExportType: {job['ExportType']}")
    if job.get("ProjectId"):
        print(f"ProjectId: {job['ProjectId']}")
    if job.get("Code") or job.get("Message"):
        print(f"Code: {job.get('Code')}")
        print(f"Message: {job.get('Message')}")

    result = job.get("ExportResult") or {}
    if result.get("ProjectUrl"):
        print(f"ProjectUrl: {result['ProjectUrl']}")
    if result.get("AudioUrl"):
        print(f"AudioUrl: {result['AudioUrl']}")
    for entry in result.get("SrtList") or []:
        if isinstance(entry, dict) and entry.get("SrtUrl"):
            print(f"Srt [{entry.get('Tag') or '-'}]: {entry['SrtUrl']}")

    if job.get("Status") != "Success" or not result.get("Timeline"):
        return

    timeline = parse_exported_timeline(job)
    print("\nExpanded Timeline")
    summarize_exported_timeline(timeline)

    if timeline_path:
        with open(timeline_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n")
        print(f"\nExpanded Timeline written to {timeline_path}")


def confirm_project_export_submission(
    output_media_config: dict,
    region_id: str,
    export_type: str,
    project_id: Optional[str],
    skip_confirmation: bool = False,
) -> bool:
    """Confirm before submitting an export job — it can trigger paid AI work."""
    print("\n" + "=" * 60)
    print("⚠️  BILLABLE OPERATION: Project Export Job Submission")
    print("=" * 60)
    print(f"\n📦 ExportType: {export_type}")
    print(f"📥 Source: {'ProjectId ' + project_id if project_id else 'inline Timeline'}")
    print(f"📤 Scratch bucket: {output_media_config['Bucket']}"
          f"/{output_media_config.get('Prefix', '')}")
    print(f"🌍 Region: {region_id}")

    print("\n💰 Cost Warning:")
    print("   This operation will incur charges for:")
    print("   - Any AI workflow task the source still declares — ASR / TTS /")
    print("     avatar / detext runs here if it has not run yet")
    print("   - OSS storage for the intermediate files written to the bucket")

    print("\n" + "=" * 60)

    import os
    if skip_confirmation or os.environ.get('VIDEO_EDITOR_SKIP_CONFIRMATION') == '1':
        print(SKIP_CONFIRM_NOTE)
        return True

    try:
        response = input("\nDo you want to proceed? [y/N]: ").strip().lower()
        return response in ('y', 'yes')
    except (EOFError, KeyboardInterrupt):
        print("\n⚠️  Non-interactive environment detected.")
        print("   Set VIDEO_EDITOR_SKIP_CONFIRMATION=1 to skip this prompt.")
        return False


# ---------------------------------------------------------------------------
# EDL — the editorial decision layer
# ---------------------------------------------------------------------------
# An EDL records *cut decisions* (which source, which range, which beat, why).
# The ICE Timeline is a render target, not a thinking medium: iterating on a
# 300-line Timeline means regenerating it, while iterating on an EDL means
# changing one number. `compile` turns the former into the latter and runs the
# SKILL.md §5 pre-submit checklist mechanically instead of from memory.

EDL_SCHEMA_VERSION = 1

# Bare names that must carry the AI_ prefix (§5-A).
BARE_AI_TYPES = {"ASR", "TTS", "Avatar", "Matting", "RealMatting"}

# These are effects placed in a clip's Effects, never clip Types (§5-A).
MATTING_TYPES = {"AI_Matting", "AI_RealMatting"}

# Flip/mirror must be a dedicated Flip effect, not a VFX SubType (25-error-index.md).
FLIP_VFX_SUBTYPES = {"hflip", "vflip", "flip", "mirror"}

# Two kept dialogue blocks closer than this cannot be cut apart cleanly:
# the producing engine rounds clip tails by ~0.2 s (references/18 §1.5).
MIN_DIALOGUE_GAP = 0.3

# Advanced effect ids that need a paid package enabled on the account (25-error-index.md).
ADVANCED_EFFECT_PREFIXES = ("OT0001-", "OV0001-")


def _is_num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _iter_clips(timeline: dict):
    """Yield (clip, path, kind) for every clip on every track kind."""
    for track_key, clip_key, kind in (
        ("VideoTracks", "VideoTrackClips", "video"),
        ("AudioTracks", "AudioTrackClips", "audio"),
        ("SubtitleTracks", "SubtitleTrackClips", "subtitle"),
    ):
        tracks = timeline.get(track_key)
        if not isinstance(tracks, list):
            continue
        for i, track in enumerate(tracks):
            if not isinstance(track, dict):
                continue
            clips = track.get(clip_key)
            if not isinstance(clips, list):
                continue
            for j, clip in enumerate(clips):
                if isinstance(clip, dict):
                    yield clip, f"{track_key}[{i}].{clip_key}[{j}]", kind


def _clip_effects(clip: dict) -> list:
    effects = clip.get("Effects")
    return [e for e in effects if isinstance(e, dict)] if isinstance(effects, list) else []


def _track_has_clips(timeline: dict, track_key: str, clip_key: str) -> bool:
    tracks = timeline.get(track_key)
    if not isinstance(tracks, list):
        return False
    for track in tracks:
        if isinstance(track, dict) and isinstance(track.get(clip_key), list) and track[clip_key]:
            return True
    return False


def lint_timeline(timeline: dict, region: Optional[str] = None) -> Tuple[List[str], List[str]]:
    """Run the §5 pre-submit checklist over a Timeline.

    Returns (blocking, warnings). A rule only blocks when a real failed job is
    on record for it (SKILL.md §5 / 25-error-index.md cite the error message). Everything
    else warns: ICE exposes no dry-run endpoint, so this validator is a local
    re-implementation of engine rules and will drift. A false positive that
    refuses a legal Timeline is worse than no check at all.
    """
    blocking: List[str] = []
    warnings: List[str] = []
    uses_ai = False

    for clip, path, kind in _iter_clips(timeline):
        clip_type = clip.get("Type")

        # §5-A — AI features are prefixed AI_
        if clip_type in BARE_AI_TYPES:
            blocking.append(
                f"{path}.Type = '{clip_type}' is missing the AI_ prefix; "
                f"use 'AI_{clip_type}' (§5-A)"
            )
        if isinstance(clip_type, str) and clip_type.startswith("AI_"):
            uses_ai = True

        # §5-A — matting is an effect, not a clip Type
        if clip_type in MATTING_TYPES:
            blocking.append(
                f"{path}.Type = '{clip_type}' — matting is an effect: move it into "
                f"the clip's Effects (§5-A)"
            )

        # §5-A — subtitle/text content field is Content, not Text
        if clip_type in ("Text", "Subtitle") and "Text" in clip and "Content" not in clip:
            blocking.append(
                f"{path} uses 'Text' for the string; the field is 'Content' (§5-A)"
            )

        # §5-A — one AI_Avatar clip per script
        if clip_type == "AI_Avatar" and kind != "video":
            blocking.append(
                f"{path} is an AI_Avatar clip on a {kind} track; it belongs in "
                f"VideoTrackClips (§5-A)"
            )

        for k, effect in enumerate(_clip_effects(clip)):
            epath = f"{path}.Effects[{k}]"
            etype = effect.get("Type")

            if etype in BARE_AI_TYPES:
                blocking.append(
                    f"{epath}.Type = '{etype}' is missing the AI_ prefix (§5-A)"
                )
            if isinstance(etype, str) and etype.startswith("AI_"):
                uses_ai = True

            # §5-A / 25-error-index.md — AI_Avatar in Effects → 'MediaId is empty'
            if etype == "AI_Avatar":
                blocking.append(
                    f"{epath} places AI_Avatar in Effects; it must be a clip in "
                    f"VideoTrackClips, otherwise the job fails with "
                    f"'InvalidTimelineFormat: ... MediaId is empty' (§5-A)"
                )

            # §5-A — matting subtype spelling
            if effect.get("SubType") == "Matting":
                blocking.append(
                    f"{epath} uses SubType 'Matting'; the effect Type is "
                    f"'AI_Matting' or 'AI_RealMatting' (§5-A)"
                )
            # Prefix-agnostic: a clip with both mistakes should surface both in
            # one pass instead of revealing the second only after fixing the first.
            if etype in ("Matting", "AI_Matting") and "ColorType" in effect:
                blocking.append(
                    f"{epath} uses 'ColorType'; the parameter is 'Color' "
                    f"(e.g. {{\"Type\": \"AI_Matting\", \"Color\": \"green\"}}) (§5-A)"
                )

            # 25-error-index.md — flip via VFX → 'Invalid vfx subType'
            if etype == "VFX":
                sub = effect.get("SubType")
                if isinstance(sub, str) and sub.lower() in FLIP_VFX_SUBTYPES:
                    blocking.append(
                        f"{epath} uses VFX SubType '{sub}' for a flip; use "
                        f"{{\"Type\": \"Flip\", \"Direction\": \"horizontal\"}} (§5-A)"
                    )

            # §5-B / 25-error-index.md — volume key is Gain
            if etype == "Volume" and "Volume" in effect:
                blocking.append(
                    f"{epath} sets 'Volume'; the key is 'Gain' "
                    f"(0 = mute, 1 = original) (§5-B)"
                )
            if etype == "Volume" and "Gain" not in effect and "Volume" not in effect:
                warnings.append(f"{epath} is a Volume effect with no Gain — no-op (§5-B)")

            # §5-A / 25-error-index.md — highlighting only works on video/audio track clips
            if etype == "AI_ASR" and kind == "subtitle" and (
                effect.get("NeedHighlighting") or "HighlightingStyle" in effect
            ):
                warnings.append(
                    f"{epath}: NeedHighlighting has no effect on SubtitleTracks — "
                    f"move AI_ASR into a VideoTracks/AudioTracks clip's Effects (§5-A)"
                )

            # 25-error-index.md — paid advanced effect package
            sub = effect.get("SubType")
            if isinstance(sub, str) and sub.startswith(ADVANCED_EFFECT_PREFIXES):
                warnings.append(
                    f"{epath}.SubType '{sub}' is an advanced effect; it is rejected "
                    f"unless the paid package is enabled on the account "
                    f"(references/25-error-index.md)"
                )

            # §5-C — regular Transition shortens the output
            if etype == "Transition":
                warnings.append(
                    f"{epath}: a regular Transition shortens the output by its "
                    f"Duration; use DLTransition to keep the total length (§5-C)"
                )

        if kind == "video" and clip.get("LoopMode"):
            warnings.append(
                f"{path} uses LoopMode on video, but only audio looping is "
                f"evidenced; repeat adjacent video clips instead (§5-B)"
            )

        # §5-C — GlobalImage needs an explicit Duration without real video
        if clip_type == "GlobalImage" and "Duration" not in clip:
            warnings.append(
                f"{path} is a GlobalImage without Duration; with no real video in "
                f"the timeline it shows on the first frame only (§5-C)"
            )

        if "MediaId" in clip and "MediaURL" in clip:
            warnings.append(
                f"{path} sets both MediaId and MediaURL; ICE uses one — drop the other"
            )

    # §5-C / 25-error-index.md — one effect kind per EffectTrack
    effect_tracks = timeline.get("EffectTracks")
    if isinstance(effect_tracks, list):
        for i, track in enumerate(effect_tracks):
            if not isinstance(track, dict):
                continue
            items = track.get("EffectTrackItems")
            if not isinstance(items, list):
                continue
            kinds = {it.get("Type") for it in items if isinstance(it, dict)}
            kinds.discard(None)
            if len(kinds) > 1:
                blocking.append(
                    f"EffectTracks[{i}].EffectTrackItems mixes effect kinds "
                    f"{sorted(kinds)}; each EffectTracks entry may hold only one "
                    f"kind — split them into separate entries (§5-C)"
                )
            for it in items:
                if isinstance(it, dict) and str(it.get("Type", "")).startswith("AI_"):
                    uses_ai = True

    # §5-D / 25-error-index.md — both video and audio tracks empty
    has_video = _track_has_clips(timeline, "VideoTracks", "VideoTrackClips")
    has_audio = _track_has_clips(timeline, "AudioTracks", "AudioTrackClips")
    if not has_video and not has_audio:
        blocking.append(
            "Timeline has no video and no audio clips; the job fails with "
            "'TimelineFormatError: Both video tracks and audio tracks are empty.' "
            "A text-only deliverable is not buildable — ask the user for a "
            "background image or BGM; never generate or upload one just to "
            "clear this check (§5-D)"
        )

    # §5-B — audio clips must not overlap on one track
    audio_tracks = timeline.get("AudioTracks")
    if isinstance(audio_tracks, list):
        for i, track in enumerate(audio_tracks):
            if not isinstance(track, dict):
                continue
            clips = track.get("AudioTrackClips")
            if not isinstance(clips, list):
                continue
            spans = []
            for j, clip in enumerate(clips):
                if not isinstance(clip, dict):
                    continue
                start, end = clip.get("TimelineIn"), clip.get("TimelineOut")
                if _is_num(start) and _is_num(end):
                    spans.append((start, end, j))
            spans.sort()
            for (s1, e1, j1), (s2, _e2, j2) in zip(spans, spans[1:]):
                if s2 < e1:
                    blocking.append(
                        f"AudioTracks[{i}]: clips [{j1}] ({s1}–{e1}) and [{j2}] "
                        f"(from {s2}) overlap; layer sounds on separate tracks (§5-B)"
                    )

    # 25-error-index.md — AI features outside an AI-capable region
    if uses_ai and region and region not in AI_FEATURE_REGIONS:
        blocking.append(
            f"Timeline uses AI_* features but the region is '{region}'; submit in "
            f"one of {', '.join(AI_FEATURE_REGIONS)} (§3)"
        )

    return blocking, warnings


def validate_edl(edl: dict) -> Tuple[dict, List[str]]:
    """Structural validation of an EDL. Returns (edl, warnings); raises on error."""
    if not isinstance(edl, dict):
        raise ValidationError("EDL must be a JSON object")

    version = edl.get("version", EDL_SCHEMA_VERSION)
    if not isinstance(version, int) or version > EDL_SCHEMA_VERSION:
        raise ValidationError(
            f"EDL version must be an integer <= {EDL_SCHEMA_VERSION}, got {version!r}"
        )

    sources = edl.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise ValidationError("EDL.sources must be a non-empty object of name → source")

    for name, src in sources.items():
        if not isinstance(src, dict):
            raise ValidationError(f"EDL.sources['{name}'] must be an object")
        if not (src.get("media_id") or src.get("url")):
            raise ValidationError(
                f"EDL.sources['{name}'] needs 'media_id' or 'url'"
            )
        if src.get("media_id") and src.get("url"):
            raise ValidationError(
                f"EDL.sources['{name}'] sets both 'media_id' and 'url'; pick one"
            )
        url = src.get("url")
        if url is not None and not str(url).startswith(("http://", "https://")):
            raise ValidationError(
                f"EDL.sources['{name}'].url must be an http(s) URL "
                f"(copy it verbatim — SKILL.md §4)"
            )
        dur = src.get("duration")
        if dur is not None and not _is_num(dur):
            raise ValidationError(f"EDL.sources['{name}'].duration must be a number")

    ranges = edl.get("ranges")
    if not isinstance(ranges, list) or not ranges:
        raise ValidationError("EDL.ranges must be a non-empty array")

    for i, rng in enumerate(ranges):
        if not isinstance(rng, dict):
            raise ValidationError(f"EDL.ranges[{i}] must be an object")
        src_name = rng.get("source")
        if src_name not in sources:
            raise ValidationError(
                f"EDL.ranges[{i}].source '{src_name}' is not declared in sources"
            )
        start, end = rng.get("in"), rng.get("out")
        for field, value in (("in", start), ("out", end)):
            if not _is_num(value) or value < 0:
                raise ValidationError(
                    f"EDL.ranges[{i}].{field} must be a non-negative number"
                )
        if end <= start:
            raise ValidationError(
                f"EDL.ranges[{i}]: out ({end}) must be greater than in ({start})"
            )
        dur = sources[src_name].get("duration")
        if _is_num(dur) and end > dur:
            raise ValidationError(
                f"EDL.ranges[{i}].out ({end}) exceeds source '{src_name}' "
                f"duration ({dur})"
            )

    warnings: List[str] = []

    # references/18 §1.5 — a gap narrower than 0.3 s cannot be cut cleanly
    for i in range(1, len(ranges)):
        prev, cur = ranges[i - 1], ranges[i]
        if prev.get("source") != cur.get("source"):
            continue
        gap = cur["in"] - prev["out"]
        if 0 < gap < MIN_DIALOGUE_GAP:
            warnings.append(
                f"ranges[{i - 1}]→[{i}]: {gap:.3f}s gap in '{cur['source']}' is under "
                f"{MIN_DIALOGUE_GAP}s — the engine rounds tails by ~0.2s, so this either "
                f"leaks the next line's start or clips the current tail. Either make the "
                f"ranges contiguous (out == in) or keep the whole block (references/18 §1.5)"
            )
        elif gap < 0:
            warnings.append(
                f"ranges[{i - 1}]→[{i}]: overlapping source ranges in "
                f"'{cur['source']}' ({prev['out']} > {cur['in']}); the same footage "
                f"plays twice"
            )

    # references/19 §4 — a highlight that keeps most of the source reads as unedited
    total = sum(r["out"] - r["in"] for r in ranges)
    known = {n: s["duration"] for n, s in sources.items() if _is_num(s.get("duration"))}
    used_sources = {r["source"] for r in ranges}
    if used_sources <= set(known) and known:
        source_total = sum(known[n] for n in used_sources)
        if source_total > 0:
            ratio = total / source_total
            if ratio > 0.5:
                warnings.append(
                    f"kept {total:.1f}s of {source_total:.1f}s ({ratio:.0%}); a highlight "
                    f"above 50% reads as 'not edited' — a real 79s→66s cut (84%) was "
                    f"rejected, 30s (38%) passed (references/19 §4)"
                )

    for i, rng in enumerate(ranges):
        if not rng.get("reason"):
            warnings.append(
                f"ranges[{i}] has no 'reason'; the field is what makes a cut "
                f"auditable on the next iteration"
            )

    return edl, warnings


def _source_ref(src: dict) -> dict:
    """Turn an EDL source into the clip fields that address it."""
    if src.get("media_id"):
        return {"MediaId": src["media_id"]}
    return {"MediaURL": src["url"]}


def compile_edl(edl: dict) -> dict:
    """Compile an EDL into an ICE Timeline.

    Video ranges go on one MainTrack in array order with In/Out and no
    TimelineIn/TimelineOut, so they play back-to-back (SKILL.md §5-D).
    """
    sources = edl["sources"]

    video_clips = []
    for rng in edl["ranges"]:
        src = sources[rng["source"]]
        clip = {"Type": "Image" if src.get("image") else "Video"}
        clip.update(_source_ref(src))
        clip["In"] = rng["in"]
        clip["Out"] = rng["out"]
        for edl_key, clip_key in (("speed", "Speed"), ("duration", "Duration")):
            if edl_key in rng:
                clip[clip_key] = rng[edl_key]
        effects = list(rng.get("effects") or [])
        if effects:
            clip["Effects"] = effects
        video_clips.append(clip)

    timeline: dict = {
        "VideoTracks": [{"MainTrack": True, "VideoTrackClips": video_clips}]
    }

    audio_clips = []
    for entry in edl.get("audio") or []:
        src = sources.get(entry.get("source"))
        if src is None:
            raise ValidationError(
                f"EDL.audio references undeclared source '{entry.get('source')}'"
            )
        clip: dict = {"Type": "Audio"}
        clip.update(_source_ref(src))
        for edl_key, clip_key in (
            ("in", "In"), ("out", "Out"),
            ("timeline_in", "TimelineIn"), ("timeline_out", "TimelineOut"),
        ):
            if edl_key in entry:
                clip[clip_key] = entry[edl_key]
        if entry.get("loop"):
            clip["LoopMode"] = True
        effects = list(entry.get("effects") or [])
        if "gain" in entry:
            effects.append({"Type": "Volume", "Gain": entry["gain"]})
        if effects:
            clip["Effects"] = effects
        audio_clips.append(clip)
    if audio_clips:
        timeline["AudioTracks"] = [{"AudioTrackClips": audio_clips}]

    subtitle_clips = []
    for entry in edl.get("subtitles") or []:
        clip = {"Type": entry.get("type", "Text")}
        clip.update({k: v for k, v in entry.items() if k not in ("type",)})
        subtitle_clips.append(clip)
    if subtitle_clips:
        timeline["SubtitleTracks"] = [{"SubtitleTrackClips": subtitle_clips}]

    for key in ("EffectTracks", "FECanvas", "MaxDuration"):
        if key in edl:
            timeline[key] = edl[key]

    return timeline


# ---------------------------------------------------------------------------
# decompile — an exported Timeline back into a fresh EDL (references/21 §5)
# ---------------------------------------------------------------------------
# An AI expansion has no EDL behind it: the aligner's sentence boundaries and the
# materialized TTS / erased-video artefacts exist only in the exported Timeline.
# Decompiling it into a *new* EDL restores the sanctioned loop — structural edits
# go back through `compile` — and because the sources are now the expanded
# artefacts, recompiling never re-runs (or re-bills) the AI.
#
# `compile_edl` is deliberately opinionated (one MainTrack, one audio track, one
# subtitle track, clips back-to-back in array order), so not every Timeline is
# expressible as an EDL. This decompiler refuses the shapes it cannot represent
# instead of silently flattening them.

# ASS/SSA numpad codes that the export normalizes `Alignment` into. Only
# 8 ↔ TopCenter is evidenced (a submitted "TopCenter" came back as "8"); the rest
# follow the ASS convention and are UNVERIFIED — frame-check after a re-render.
ASS_ALIGNMENT_CODES = {
    "1": "BottomLeft", "2": "BottomCenter", "3": "BottomRight",
    "4": "CenterLeft", "5": "CenterCenter", "6": "CenterRight",
    "7": "TopLeft", "8": "TopCenter", "9": "TopRight",
}

# Keys describing the srt carrier rather than the text style — dropped when a srt
# track is inlined into per-cue Text clips.
SRT_CARRIER_KEYS = {"Type", "SubType", "FileUrl", "Content",
                    "TimelineIn", "TimelineOut"}

# AI_ASR-only fields that mean nothing on a plain Text clip.
ASR_ONLY_EFFECT_KEYS = {"Type", "AlignmentText", "NeedHighlighting"}

# Clips are considered back-to-back within this many seconds.
CONTIGUITY_TOLERANCE = 0.002

SRT_TIME_RE = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*"
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})"
)


def _srt_clock(hours: str, minutes: str, seconds: str, millis: str) -> float:
    return (int(hours) * 3600 + int(minutes) * 60 + int(seconds)
            + int(millis.ljust(3, "0")) / 1000.0)


def parse_srt(text: str) -> List[dict]:
    """Parse srt into [{'start', 'end', 'lines'}] in file order.

    Tolerates BOM, CRLF and a missing trailing blank line. Cue numbering is
    ignored — the engine's own numbering is not load-bearing.
    """
    cues: List[dict] = []
    current: Optional[dict] = None
    for raw in text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip()
        match = SRT_TIME_RE.search(line)
        if match:
            groups = match.groups()
            current = {
                "start": _srt_clock(*groups[:4]),
                "end": _srt_clock(*groups[4:]),
                "lines": [],
            }
            cues.append(current)
            continue
        if not line:
            current = None
            continue
        if current is not None:
            current["lines"].append(line)
    return [cue for cue in cues if cue["lines"]]


def extract_asr_style(timeline: dict) -> dict:
    """Pull the style off the first AI_ASR effect of a *submitted* Timeline.

    Style is the one thing you already know — reading it back from the export
    means reading it after the engine normalized it (Alignment "TopCenter" comes
    back as "8"). Prefer this over the exported style block.
    """
    for clip, _path, _kind in _iter_clips(timeline):
        for effect in _clip_effects(clip):
            if effect.get("Type") == "AI_ASR":
                return {k: v for k, v in effect.items()
                        if k not in ASR_ONLY_EFFECT_KEYS}
    raise ValidationError(
        "--style-from timeline has no AI_ASR effect to take the subtitle style "
        "from; pass the Timeline that was submitted, or omit the flag"
    )


def _source_name(clip: dict, taken: set) -> str:
    """A short, stable, unique EDL key for a clip's material."""
    raw = clip.get("Title") or clip.get("MediaURL") or clip.get("MediaId") or "src"
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(raw).rsplit("/", 1)[-1])
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")[:28] or "src"
    name, n = base, 2
    while name in taken:
        name, n = f"{base}_{n}", n + 1
    return name


def _geometry_is_default(clip: dict) -> bool:
    return (clip.get("X") in (None, 0, 0.0)
            and clip.get("Y") in (None, 0, 0.0)
            and clip.get("Width") in (None, 1, 1.0)
            and clip.get("Height") in (None, 1, 1.0))


def decompile_timeline(
    timeline: dict,
    srt_texts: Optional[dict] = None,
    style: Optional[dict] = None,
) -> Tuple[dict, List[str]]:
    """Turn an exported Timeline into a fresh EDL.

    Args:
        timeline: an *expanded* Timeline (from `export-timeline`)
        srt_texts: FileUrl → srt file contents. When a srt track's text is
                   supplied it is inlined as per-cue Text clips; otherwise the
                   srt track passes through as-is.
        style: subtitle style for inlined cues (see extract_asr_style). When
               omitted, the srt clip's own style is reused and its numeric
               Alignment mapped back through ASS_ALIGNMENT_CODES.

    Returns:
        (edl, warnings)

    Raises:
        ValidationError: when the Timeline's shape is not expressible as an EDL
    """
    warnings: List[str] = []

    # An unexpanded Timeline must be exported first — decompiling it would put
    # the placeholder straight back into the EDL and lose nothing but time.
    for clip, path, _kind in _iter_clips(timeline):
        declarations = [clip["Type"]] if clip.get("Type") in WORKFLOW_TASK_TYPES else []
        declarations += [e["Type"] for e in _clip_effects(clip)
                         if e.get("Type") in WORKFLOW_TASK_TYPES]
        if declarations:
            raise ValidationError(
                f"{path} still declares {', '.join(declarations)}: this is a "
                f"submitted Timeline, not an expanded one. Run export-timeline "
                f"first (references/21-timeline-export.md §5)"
            )

    for track_key, limit_note in (("VideoTracks", "one MainTrack"),
                                  ("AudioTracks", "one audio track"),
                                  ("SubtitleTracks", "one subtitle track")):
        tracks = timeline.get(track_key) or []
        if len(tracks) > 1:
            raise ValidationError(
                f"{len(tracks)} {track_key} entries: compile emits {limit_note}, "
                f"so this composition is not expressible as an EDL. Keep editing "
                f"the exported Timeline directly (references/21 §5)"
            )

    video_tracks = timeline.get("VideoTracks") or []
    video_clips = (video_tracks[0].get("VideoTrackClips") or []) if video_tracks else []
    if not video_clips:
        raise ValidationError(
            "EDL.ranges cannot be empty — the Timeline has no video clips"
        )

    sources: dict = {}
    by_material: dict = {}
    ranges: List[dict] = []
    expected_start = 0.0

    for index, clip in enumerate(video_clips):
        path = f"VideoTracks[0].VideoTrackClips[{index}]"
        if not _geometry_is_default(clip):
            raise ValidationError(
                f"{path} carries non-default geometry "
                f"(X={clip.get('X')}, Y={clip.get('Y')}, "
                f"W={clip.get('Width')}, H={clip.get('Height')}); an EDL range "
                f"cannot express it (references/21 §5)"
            )

        media_id, media_url = clip.get("MediaId"), clip.get("MediaURL")
        if not (media_id or media_url):
            raise ValidationError(f"{path} has neither MediaId nor MediaURL")

        # An EDL source takes exactly one address. MediaId is preferred: it does
        # not expire and needs no signing, while the exported MediaURL comes back
        # unsigned and 403s on a private bucket.
        key = media_id or media_url
        if key not in by_material:
            name = _source_name(clip, set(sources))
            source: dict = {"media_id": media_id} if media_id else {"url": media_url}
            if _is_num(clip.get("VirginDuration")):
                source["duration"] = clip["VirginDuration"]
            else:
                warnings.append(
                    f"{path} has no VirginDuration; without 'duration' the "
                    f"range-exceeds-source and highlight-ratio checks stay off"
                )
            if clip.get("Type") == "Image":
                source["image"] = True
            if media_id and media_url:
                warnings.append(
                    f"source '{name}': kept MediaId {media_id} and dropped the "
                    f"exported MediaURL (an EDL source takes one address; the "
                    f"exported URL is unsigned and 403s on a private bucket)"
                )
            sources[name] = source
            by_material[key] = name
        name = by_material[key]

        clip_in, clip_out = clip.get("In"), clip.get("Out")
        if not (_is_num(clip_in) and _is_num(clip_out)):
            raise ValidationError(f"{path} has no numeric In/Out to build a range")
        rng: dict = {"source": name, "in": clip_in, "out": clip_out}
        speed = clip.get("Speed")
        if _is_num(speed) and speed != 1:
            rng["speed"] = speed
        effects = _clip_effects(clip)
        if effects:
            rng["effects"] = effects
        ranges.append(rng)

        # compile drops TimelineIn/TimelineOut and relies on array order, so a
        # layout that is not back-to-back from 0 cannot be reproduced.
        timeline_in, timeline_out = clip.get("TimelineIn"), clip.get("TimelineOut")
        if _is_num(timeline_in):
            if abs(timeline_in - expected_start) > CONTIGUITY_TOLERANCE:
                raise ValidationError(
                    f"{path} starts at {timeline_in}s but the clips before it end "
                    f"at {expected_start:.3f}s; compile lays ranges back-to-back, "
                    f"so gaps and explicit offsets are not expressible "
                    f"(references/21 §5)"
                )
            if _is_num(timeline_out):
                rendered = timeline_out - timeline_in
                intended = (clip_out - clip_in) / (speed if _is_num(speed) and speed else 1)
                if abs(rendered - intended) > 0.05:
                    warnings.append(
                        f"{path}: rendered span {rendered:.3f}s differs from "
                        f"(Out-In)/Speed = {intended:.3f}s; check the range"
                    )
                expected_start = timeline_out
            else:
                expected_start += clip_out - clip_in

    edl: dict = {"version": EDL_SCHEMA_VERSION, "sources": sources, "ranges": ranges}

    audio_tracks = timeline.get("AudioTracks") or []
    audio_entries: List[dict] = []
    for index, clip in enumerate((audio_tracks[0].get("AudioTrackClips") or [])
                                 if audio_tracks else []):
        path = f"AudioTracks[0].AudioTrackClips[{index}]"
        media_id, media_url = clip.get("MediaId"), clip.get("MediaURL")
        if not (media_id or media_url):
            raise ValidationError(f"{path} has neither MediaId nor MediaURL")
        key = media_id or media_url
        if key not in by_material:
            name = _source_name(clip, set(sources))
            sources[name] = {"media_id": media_id} if media_id else {"url": media_url}
            by_material[key] = name
        entry: dict = {"source": by_material[key]}
        for clip_key, edl_key in (("In", "in"), ("Out", "out"),
                                  ("TimelineIn", "timeline_in"),
                                  ("TimelineOut", "timeline_out")):
            if _is_num(clip.get(clip_key)):
                entry[edl_key] = clip[clip_key]
        if clip.get("LoopMode"):
            entry["loop"] = True
        residual = []
        for effect in _clip_effects(clip):
            if effect.get("Type") == "Volume" and _is_num(effect.get("Gain")):
                entry["gain"] = effect["Gain"]
            else:
                residual.append(effect)
        if residual:
            entry["effects"] = residual
        audio_entries.append(entry)
    if audio_entries:
        edl["audio"] = audio_entries

    subtitle_tracks = timeline.get("SubtitleTracks") or []
    subtitle_entries: List[dict] = []
    for index, clip in enumerate((subtitle_tracks[0].get("SubtitleTrackClips") or [])
                                 if subtitle_tracks else []):
        path = f"SubtitleTracks[0].SubtitleTrackClips[{index}]"
        srt_text = (srt_texts or {}).get(clip.get("FileUrl"))
        if clip.get("SubType") != "srt" or srt_text is None:
            if clip.get("SubType") == "srt":
                warnings.append(
                    f"{path}: srt track passed through as a file reference. The "
                    f"cues stay bound to this time base, so any structural edit "
                    f"desynchronizes them — inline it (--inline-srt) to make the "
                    f"EDL self-contained (references/21 §5)"
                )
            entry = {"type": clip.get("Type", "Text")}
            entry.update({k: v for k, v in clip.items() if k != "Type"})
            subtitle_entries.append(entry)
            continue

        cues = parse_srt(srt_text)
        if not cues:
            raise ValidationError(
                f"{path}: the srt at {clip['FileUrl']} parsed to zero cues"
            )

        if style is not None:
            cue_style = dict(style)
        else:
            cue_style = {k: v for k, v in clip.items() if k not in SRT_CARRIER_KEYS}
            alignment = cue_style.get("Alignment")
            if isinstance(alignment, str) and alignment in ASS_ALIGNMENT_CODES:
                cue_style["Alignment"] = ASS_ALIGNMENT_CODES[alignment]
                warnings.append(
                    f"{path}: mapped the exported numeric Alignment "
                    f"'{alignment}' back to '{cue_style['Alignment']}' (ASS "
                    f"convention; only 8 = TopCenter is evidenced). Prefer "
                    f"--style-from <submitted timeline>, and frame-check"
                )

        multiline = sum(1 for cue in cues if len(cue["lines"]) > 1)
        if multiline:
            warnings.append(
                f"{path}: {multiline} cue(s) span multiple srt lines, joined with "
                f"'\\n'; check the wrap against AdaptMode after rendering"
            )

        for cue in cues:
            entry = {"type": "Text", "Content": "\n".join(cue["lines"]),
                     "TimelineIn": cue["start"], "TimelineOut": cue["end"]}
            entry.update(cue_style)
            subtitle_entries.append(entry)

        # The carrier's span is the engine's own view of where the subtitles end;
        # a mismatch means the srt and the timeline disagree.
        carrier_out = clip.get("TimelineOut")
        if _is_num(carrier_out) and abs(cues[-1]["end"] - carrier_out) > 0.05:
            warnings.append(
                f"{path}: last cue ends at {cues[-1]['end']:.3f}s but the srt "
                f"clip spans to {carrier_out}s — verify the srt matches this track"
            )
        gaps = sum(1 for a, b in zip(cues, cues[1:])
                   if b["start"] - a["end"] > CONTIGUITY_TOLERANCE)
        warnings.append(
            f"{path}: inlined {len(cues)} cue(s) as Text clips, {gaps} gap(s) "
            f"between them copied verbatim — srt display is discontinuous by "
            f"nature, do not 'fix' the gaps into a contiguous run"
        )

    if subtitle_entries:
        edl["subtitles"] = subtitle_entries

    for key in ("EffectTracks", "FECanvas", "MaxDuration"):
        if key in timeline:
            edl[key] = timeline[key]

    warnings.append(
        f"no 'reason' on any of the {len(ranges)} range(s): a decompiled EDL "
        f"carries no rationale. This is a new task — write why each range stays"
    )
    return edl, warnings


def sign_oss_url(file_url: str, skill_dir: str, ttl: int = 3600) -> str:
    """Sign a plain OSS URL by delegating to the skill's own signer.

    oss_sign_clean.sh delegates V4 signing to ossutil and curl-checks the URL;
    reusing it keeps one AK/STS-compatible signing path in the skill (SKILL.md §8).
    """
    import os
    import subprocess
    from urllib.parse import urlparse

    parsed = urlparse(file_url)
    host_parts = parsed.netloc.split(".", 1)
    if len(host_parts) != 2 or not parsed.path:
        raise ValidationError(f"Cannot derive an OSS address from {file_url}")
    bucket, endpoint = host_parts
    key = parsed.path.lstrip("/")

    script = os.path.join(skill_dir, "scripts", "oss_sign_clean.sh")
    if not os.path.exists(script):
        raise ValidationError(f"Signer not found: {script}")
    result = subprocess.run(
        ["zsh", script, f"oss://{bucket}/{key}", str(ttl), endpoint],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if line.startswith("URL: "):
                return line[len("URL: "):].strip()
    raise ValidationError(
        f"Could not sign {file_url}: {result.stderr.strip() or result.stdout.strip()}"
    )


def fetch_srt_texts(timeline: dict, skill_dir: str, local_srt: Optional[str] = None) -> dict:
    """Collect FileUrl → srt contents for every srt subtitle clip.

    A local file (--srt) is used verbatim and keeps the whole run offline; other
    tracks are signed and fetched.
    """
    from urllib.request import urlopen

    urls = [clip["FileUrl"] for clip, _path, _kind in _iter_clips(timeline)
            if clip.get("SubType") == "srt" and clip.get("FileUrl")]
    if not urls:
        raise ValidationError(
            "--inline-srt: the Timeline has no srt subtitle clip to inline"
        )

    texts = {}
    for url in urls:
        if local_srt:
            with open(local_srt, "r", encoding="utf-8") as fh:
                texts[url] = fh.read()
            print(f"  srt from {local_srt} (offline) for {url}")
            continue
        signed = sign_oss_url(url, skill_dir)
        with urlopen(signed, timeout=30) as response:
            texts[url] = response.read().decode("utf-8")
        print(f"  fetched srt: {url}")
    return texts


def print_lint(blocking: List[str], warnings: List[str]) -> None:
    """Print lint results. Warnings first, blockers last so they stay visible."""
    for msg in warnings:
        print(f"  WARN   {msg}")
    for msg in blocking:
        print(f"  BLOCK  {msg}")
    if not blocking and not warnings:
        print("  checklist clean")
    else:
        print(f"  {len(blocking)} blocking, {len(warnings)} warning(s)")


def edl_summary(edl: dict) -> str:
    """One line per range — the human-readable view of the cut decisions."""
    lines = []
    offset = 0.0
    for i, rng in enumerate(edl["ranges"]):
        dur = rng["out"] - rng["in"]
        beat = rng.get("beat") or "-"
        quote = rng.get("quote") or ""
        lines.append(
            f"  [{i:>2}] {rng['source']:<12} {rng['in']:>7.2f}–{rng['out']:<7.2f} "
            f"({dur:5.2f}s)  @{offset:6.2f}  {beat:<10} {quote[:34]}"
        )
        offset += dur
    lines.append(f"  total {offset:.2f}s across {len(edl['ranges'])} ranges")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Video Editor for Alibaba Cloud ICE (using Common SDK)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Submit and wait for completion (region has no default — the user confirms it first)
  python video_editor.py submit -t timeline.json -o output.json -r cn-shanghai --wait

  # Submit without waiting
  python video_editor.py submit -t timeline.json -o output.json -r cn-shanghai

  # Compile an EDL (cut decisions) into a Timeline and run the §5 checklist
  python video_editor.py compile -e edl.json -O timeline.json -r cn-beijing

  # Checklist only, nothing written
  python video_editor.py compile -e edl.json

  # Check job status
  python video_editor.py status -j job_id_here -r cn-shanghai

  # Resolve a MediaId to a signed playable URL
  python video_editor.py media-info -m media_id_here -r cn-shanghai

  # Submit an intelligent production job (smart cover, de-logo, caption extraction, ...)
  python video_editor.py iproduction -f Cover -i oss://bucket/in.mp4 \
      -O "oss://bucket/cover/{source}-{sequenceId}.png" -r cn-shanghai --wait --yes

  # Check an intelligent production job
  python video_editor.py iproduction-status -j job_id_here -r cn-shanghai

  # Dialogue timeline (fine granularity; punctuation marks real sentence ends)
  python video_editor.py asr -i media_id_here -r cn-beijing \
      --sentence-max-length 4 --semantic --wait --json asr.json

  # Whole-video filmstrip + WebVTT time map, covering the full duration
  python video_editor.py snapshot -i media_id_here -r cn-beijing \
      --mode webvtt --cover 89.6 -O "oss://bucket/strip/ep01.vtt" --wait

  # Frames at one instant (Time is milliseconds, Interval is seconds)
  python video_editor.py snapshot -i media_id_here -r cn-beijing \
      --mode normal --time 18400 --count 5 --interval 1 \
      -O "oss://bucket/seam/f-{Count}.jpg" --wait

  # The timeline the engine actually computed (AI placeholders expanded)
  python video_editor.py export-timeline -P project_id_here -r cn-beijing \
      -b bucket-name --prefix export/ep01 -O timeline_expanded.json --wait --yes

  # Expanded timeline back to an EDL, subtitles inlined as per-cue Text clips
  python video_editor.py decompile -t timeline_expanded.json -O edl_v2.json \
      --inline-srt --style-from timeline.json
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Submit command
    submit_parser = subparsers.add_parser("submit", help="Submit a video producing job")
    submit_parser.add_argument(
        "--timeline", "-t",
        required=True,
        help="Path to Timeline JSON file or JSON string"
    )
    submit_parser.add_argument(
        "--output-config", "-o",
        required=True,
        help="Path to OutputMediaConfig JSON file or JSON string"
    )
    submit_parser.add_argument(
        "--region", "-r",
        required=True,
        help="Region ID — no default; must be the region the user confirmed. "
             "Valid values: " + ", ".join(VALID_REGIONS)
    )
    submit_parser.add_argument(
        "--wait", "-w",
        action="store_true",
        help="Wait for job completion"
    )
    submit_parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Poll interval in seconds (default: 5)"
    )
    submit_parser.add_argument(
        "--max-wait",
        type=int,
        default=3600,
        help="Maximum wait time in seconds (default: 3600)"
    )
    submit_parser.add_argument(
        "--client-token",
        help="ClientToken for idempotency (auto-generated if not provided). "
             "Use the same token to safely retry a failed submission."
    )
    submit_parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt for high-risk operations"
    )
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check job status")
    status_parser.add_argument(
        "--job-id", "-j",
        required=True,
        help="Job ID to check"
    )
    status_parser.add_argument(
        "--region", "-r",
        required=True,
        help="Region ID the job was submitted in — no default. "
             "Valid values: " + ", ".join(VALID_REGIONS)
    )
    status_parser.add_argument(
        "--wait", "-w",
        action="store_true",
        help="Wait for job completion"
    )
    status_parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Poll interval in seconds (default: 5)"
    )
    status_parser.add_argument(
        "--max-wait",
        type=int,
        default=3600,
        help="Maximum wait time in seconds (default: 3600)"
    )
    status_parser.add_argument(
        "--details",
        action="store_true",
        help="Also print the submitted ClipsParam and Timeline"
    )
    
    # Media-info command
    media_info_parser = subparsers.add_parser(
        "media-info",
        help="Resolve a MediaId and probe signed-media stream durations"
    )
    media_info_parser.add_argument(
        "--media-id", "-m",
        required=True,
        help="Media asset ID to resolve"
    )
    media_info_parser.add_argument(
        "--region", "-r",
        required=True,
        help="Region ID the media asset lives in — no default. "
             "Valid values: " + ", ".join(VALID_REGIONS)
    )

    # ASR command — dialogue timeline
    asr_parser = subparsers.add_parser(
        "asr",
        help="Submit an ASR job and return the dialogue timeline "
             "(references/17-snapshot-and-asr.md §1)"
    )
    asr_parser.add_argument("--input", "-i", required=True,
                            help="oss:// address, http(s) URL, or a MediaId")
    asr_parser.add_argument("--region", "-r", required=True,
                            help="Region ID — no default. Valid values: "
                                 + ", ".join(VALID_REGIONS))
    asr_parser.add_argument(
        "--sentence-max-length", type=int, default=None,
        help="Max characters per segment. 4 gives ~0.65s granularity (measured); "
             "omit for the coarse default of ~1.34s. Passing any value also turns "
             "on punctuation, which marks real sentence boundaries (§1.5)"
    )
    asr_parser.add_argument("--semantic", action="store_true",
                            help="EnableSemanticSentenceDetection")
    asr_parser.add_argument("--hotword-library-id", default=None,
                            help="Hotword library id (one only)")
    asr_parser.add_argument("--start-time", default=None, help='e.g. "00:00:00"')
    asr_parser.add_argument("--duration", default=None, help='e.g. "00:00:30"')
    asr_parser.add_argument("--gap-threshold", type=float, default=0.3,
                            help="Minimum gap for a cuttable seam (default: 0.3)")
    asr_parser.add_argument("--json", dest="json_out", default=None,
                            help="Write the parsed segments to this JSON file")
    asr_parser.add_argument("--wait", "-w", action="store_true",
                            help="Wait for the job to finish")
    asr_parser.add_argument("--poll-interval", type=int, default=10)
    asr_parser.add_argument("--max-wait", type=int, default=900)

    # ASR status
    asr_status_parser = subparsers.add_parser(
        "asr-status", help="Read an ASR (smart handle) job result by JobId")
    asr_status_parser.add_argument("--job-id", "-j", required=True)
    asr_status_parser.add_argument("--region", "-r", required=True,
                                   help="Region the job was submitted in")
    asr_status_parser.add_argument("--gap-threshold", type=float, default=0.3)
    asr_status_parser.add_argument("--json", dest="json_out", default=None)
    asr_status_parser.add_argument("--wait", "-w", action="store_true")
    asr_status_parser.add_argument("--poll-interval", type=int, default=10)
    asr_status_parser.add_argument("--max-wait", type=int, default=900)

    # Snapshot command — frames / filmstrip / WebVTT
    snapshot_parser = subparsers.add_parser(
        "snapshot",
        help="Submit a snapshot job: frames, sprite filmstrip, or WebVtt with a "
             "time-to-pixel map (references/17-snapshot-and-asr.md §2)"
    )
    snapshot_parser.add_argument("--input", "-i", required=True,
                                 help="oss:// address or a MediaId")
    snapshot_parser.add_argument("--output", "-O", required=True,
                                 help="oss://bucket/object. normal needs {Count}, "
                                      "sprite needs {TileCount}, webvtt must end .vtt")
    snapshot_parser.add_argument("--region", "-r", required=True,
                                 help="Region ID — no default. Valid values: "
                                      + ", ".join(VALID_REGIONS))
    snapshot_parser.add_argument("--mode", default="webvtt",
                                 choices=sorted(SNAPSHOT_MODES),
                                 help="normal | sprite | webvtt (default: webvtt)")
    snapshot_parser.add_argument("--time", type=int, default=0,
                                 help="Start time in MILLISECONDS (default: 0)")
    snapshot_parser.add_argument("--count", type=int, default=40,
                                 help="Number of frames (default: 40)")
    snapshot_parser.add_argument("--interval", type=int, default=2,
                                 help="Seconds between frames (default: 2)")
    snapshot_parser.add_argument(
        "--cover", type=float, default=None,
        help="Source duration in seconds. Sets --count so that "
             "count * interval >= duration, otherwise the tail is silently "
             "missing from the strip (§3)"
    )
    snapshot_parser.add_argument("--width", type=int, default=None)
    snapshot_parser.add_argument("--height", type=int, default=None)
    snapshot_parser.add_argument("--columns", type=int, default=None,
                                 help="sprite only")
    snapshot_parser.add_argument("--lines", type=int, default=None,
                                 help="sprite only")
    snapshot_parser.add_argument("--template-id", default=None,
                                 help="Use this template as-is")
    snapshot_parser.add_argument("--url-timeout", type=int,
                                 default=SNAPSHOT_URL_MAX_TIMEOUT,
                                 help="Signed-URL validity in seconds "
                                      f"(max {SNAPSHOT_URL_MAX_TIMEOUT} = 36h)")
    snapshot_parser.add_argument("--wait", "-w", action="store_true")
    snapshot_parser.add_argument("--poll-interval", type=int, default=6)
    snapshot_parser.add_argument("--max-wait", type=int, default=600)

    # Snapshot URLs
    snapshot_urls_parser = subparsers.add_parser(
        "snapshot-urls", help="Fetch signed URLs for a finished snapshot job")
    snapshot_urls_parser.add_argument("--job-id", "-j", required=True)
    snapshot_urls_parser.add_argument("--region", "-r", required=True)
    snapshot_urls_parser.add_argument("--url-timeout", type=int,
                                      default=SNAPSHOT_URL_MAX_TIMEOUT)

    # Compile command — EDL (cut decisions) → Timeline, offline
    compile_parser = subparsers.add_parser(
        "compile",
        help="Compile an EDL into a Timeline and run the §5 pre-submit checklist "
             "(offline: no credentials, no API call)"
    )
    compile_parser.add_argument(
        "--edl", "-e",
        required=True,
        help="Path to EDL JSON file or JSON string"
    )
    compile_parser.add_argument(
        "--output", "-O",
        help="Write the compiled Timeline here (default: stdout)"
    )
    compile_parser.add_argument(
        "--region", "-r",
        help="Optional. Enables the AI-feature region check. "
             "Valid values: " + ", ".join(VALID_REGIONS)
    )
    compile_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as blocking"
    )
    compile_parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Print only the Timeline (suppress the EDL summary and checklist)"
    )

    # IProduction command — single-media algorithm jobs
    iproduction_parser = subparsers.add_parser(
        "iproduction",
        help="Submit an intelligent production (algorithm) job on a single media file"
    )
    iproduction_parser.add_argument(
        "--function", "-f",
        required=True,
        help="Algorithm to run. Valid values: " + ", ".join(IPRODUCTION_FUNCTIONS)
    )
    iproduction_parser.add_argument(
        "--input", "-i",
        required=True,
        help="Source media: 'oss://bucket/object', "
             "'http(s)://bucket.oss-[regionId].aliyuncs.com/object', or a media asset id"
    )
    iproduction_parser.add_argument(
        "--output", "-O",
        required=True,
        help="Output media: an OSS address (placeholders {source}/{timestamp}/"
             "{sequenceId}/{resultType} are supported), an existing media asset id, "
             "or \"\" together with --output-type Media to create a new asset"
    )
    iproduction_parser.add_argument(
        "--input-type",
        choices=["OSS", "Media"],
        help="Input media type (inferred from --input when omitted)"
    )
    iproduction_parser.add_argument(
        "--output-type",
        choices=["OSS", "Media"],
        help="Output media type (inferred from --output when omitted)"
    )
    iproduction_parser.add_argument(
        "--output-biz",
        choices=IPRODUCTION_OUTPUT_BIZ,
        help="Media asset library a new output asset is written to (output type Media)"
    )
    iproduction_parser.add_argument(
        "--output-url",
        help="OSS address of the output file when --output-type is Media"
    )
    iproduction_parser.add_argument(
        "--job-params", "-p",
        help="Algorithm parameters: path to a JSON file or a JSON string, "
             "e.g. '{\"Model\":\"gif\"}'"
    )
    iproduction_parser.add_argument(
        "--region", "-r",
        required=True,
        help="Region ID — no default; must be the region the user confirmed and the "
             "region the input/output buckets live in. "
             "Valid values: " + ", ".join(VALID_REGIONS)
    )
    iproduction_parser.add_argument(
        "--name",
        help="Job name (max 100 characters)"
    )
    iproduction_parser.add_argument(
        "--template-id",
        help="Template ID"
    )
    iproduction_parser.add_argument(
        "--model-id",
        help="Algorithm model ID; leave empty to use the function's default model. "
             "VideoDetext also offers algo-video-detext-new (better erasure, slower, "
             "more expensive)"
    )
    iproduction_parser.add_argument(
        "--pipeline-id",
        help="Pipeline ID (ScheduleConfig)"
    )
    iproduction_parser.add_argument(
        "--priority",
        type=int,
        help="Job priority 1-10 (ScheduleConfig)"
    )
    iproduction_parser.add_argument(
        "--user-data",
        help="User data returned as-is when querying the job (max 256 characters)"
    )
    iproduction_parser.add_argument(
        "--wait", "-w",
        action="store_true",
        help="Wait for job completion"
    )
    iproduction_parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Poll interval in seconds (default: 5)"
    )
    iproduction_parser.add_argument(
        "--max-wait",
        type=int,
        default=3600,
        help="Maximum wait time in seconds (default: 3600)"
    )
    iproduction_parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt for high-risk operations"
    )

    # IProduction status command
    iproduction_status_parser = subparsers.add_parser(
        "iproduction-status",
        help="Check an intelligent production job (status, Result, output files)"
    )
    iproduction_status_parser.add_argument(
        "--job-id", "-j",
        required=True,
        help="Intelligent production JobId to check"
    )
    iproduction_status_parser.add_argument(
        "--region", "-r",
        required=True,
        help="Region ID the job was submitted in — no default. "
             "Valid values: " + ", ".join(VALID_REGIONS)
    )
    iproduction_status_parser.add_argument(
        "--wait", "-w",
        action="store_true",
        help="Wait for job completion"
    )
    iproduction_status_parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Poll interval in seconds (default: 5)"
    )
    iproduction_status_parser.add_argument(
        "--max-wait",
        type=int,
        default=3600,
        help="Maximum wait time in seconds (default: 3600)"
    )

    # Export-timeline command — the AI-expanded Timeline
    export_parser = subparsers.add_parser(
        "export-timeline",
        help="Export the AI-expanded Timeline of a project or a Timeline "
             "(references/21-timeline-export.md)"
    )
    export_source = export_parser.add_mutually_exclusive_group(required=True)
    export_source.add_argument(
        "--project-id", "-P",
        help="Cloud editing ProjectId to expand — the one GetMediaProducingJob "
             "reported for the render you want the real timeline of"
    )
    export_source.add_argument(
        "--timeline", "-t",
        help="Timeline JSON file path or JSON string to expand instead of a project"
    )
    export_parser.add_argument(
        "--bucket", "-b",
        required=True,
        help="OSS bucket for the intermediate files the expansion writes "
             "(bare bucket name, same region as the job)"
    )
    export_parser.add_argument(
        "--prefix",
        default=None,
        help="Object path prefix inside the bucket (default: bucket root)"
    )
    export_parser.add_argument(
        "--region", "-r",
        required=True,
        help="Region ID — no default; must be the region the project / media "
             "lives in. Valid values: " + ", ".join(VALID_REGIONS)
    )
    export_parser.add_argument(
        "--export-type",
        default="BaseTimeline",
        choices=PROJECT_EXPORT_TYPES,
        help="BaseTimeline returns the expanded Timeline; AdobePremierePro "
             "returns a downloadable PR project (default: BaseTimeline)"
    )
    export_parser.add_argument(
        "--output", "-O",
        dest="timeline_out",
        default=None,
        help="Write the expanded Timeline to this JSON file"
    )
    export_parser.add_argument("--width", type=int, default=None,
                               help="Target width; estimated from the source when omitted")
    export_parser.add_argument("--height", type=int, default=None,
                               help="Target height; estimated from the source when omitted")
    export_parser.add_argument("--user-data", default=None,
                               help="UserData JSON string echoed back on the job")
    export_parser.add_argument(
        "--wait", "-w",
        action="store_true",
        help="Poll until the export finishes (needed to get the Timeline)"
    )
    export_parser.add_argument(
        "--poll-interval",
        type=int,
        default=10,
        help="Poll interval in seconds (default: 10)"
    )
    export_parser.add_argument(
        "--max-wait",
        type=int,
        default=1800,
        help="Maximum wait in seconds (default: 1800 — the export blocks on any "
             "unfinished AI task in the source)"
    )
    export_parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip the confirmation prompt"
    )

    # Export-timeline status
    export_status_parser = subparsers.add_parser(
        "export-timeline-status",
        help="Read a project export job and its expanded Timeline by JobId"
    )
    export_status_parser.add_argument("--job-id", "-j", required=True)
    export_status_parser.add_argument(
        "--region", "-r",
        required=True,
        help="Region the export job was submitted in — no default. "
             "Valid values: " + ", ".join(VALID_REGIONS)
    )
    export_status_parser.add_argument(
        "--output", "-O",
        dest="timeline_out",
        default=None,
        help="Write the expanded Timeline to this JSON file"
    )
    export_status_parser.add_argument("--wait", "-w", action="store_true")
    export_status_parser.add_argument("--poll-interval", type=int, default=10)
    export_status_parser.add_argument("--max-wait", type=int, default=1800)

    # Decompile command — exported Timeline → a fresh EDL, offline
    decompile_parser = subparsers.add_parser(
        "decompile",
        help="Turn an exported (AI-expanded) Timeline back into an EDL so "
             "structural edits go through compile again "
             "(references/21-timeline-export.md §5)"
    )
    decompile_parser.add_argument(
        "--timeline", "-t",
        required=True,
        help="Path to the expanded Timeline JSON (from export-timeline), or a "
             "JSON string"
    )
    decompile_parser.add_argument(
        "--output", "-O",
        help="Write the EDL here (default: stdout)"
    )
    decompile_parser.add_argument(
        "--inline-srt",
        action="store_true",
        help="Expand the srt subtitle track into per-cue Text clips so the EDL "
             "stops depending on the srt file. Signs and fetches the srt unless "
             "--srt supplies it locally"
    )
    decompile_parser.add_argument(
        "--srt",
        default=None,
        help="Local srt file to inline instead of fetching (keeps the run offline)"
    )
    decompile_parser.add_argument(
        "--style-from",
        default=None,
        help="Timeline whose AI_ASR effect supplies the subtitle style for the "
             "inlined cues — normally the Timeline you submitted. Preferred over "
             "the exported style block, which the engine has normalized"
    )
    decompile_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as blocking"
    )
    decompile_parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Print only the EDL"
    )

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        # compile and decompile are offline — no region, no credentials, no API
        if args.command not in ("compile", "decompile"):
            validate_region(args.region)
        
        if args.command == "asr":
            client = create_client(args.region)
            job_id = submit_asr_job(
                client, args.input, args.region,
                sentence_max_length=args.sentence_max_length,
                semantic=args.semantic,
                hotword_library_id=args.hotword_library_id,
                start_time=args.start_time,
                duration=args.duration,
            )
            print(f"ASR job submitted: {job_id}")
            if args.sentence_max_length is None:
                print("  note: --sentence-max-length omitted; segments will be "
                      "~1.34s / no punctuation. Pass 4 for cut-grade timing "
                      "(references/17 §1.4)")
            if not args.wait:
                print(f"Read it with: asr-status -j {job_id} -r {args.region} --wait")
            else:
                job = wait_for_smart_handle_job(
                    client, job_id, args.region, args.poll_interval, args.max_wait
                )
                segments = parse_asr_result(job)
                print_asr_segments(segments, args.gap_threshold)
                if args.json_out:
                    with open(args.json_out, "w", encoding="utf-8") as fh:
                        json.dump(segments, fh, ensure_ascii=False, indent=2)
                    print(f"Segments written to {args.json_out}")

        elif args.command == "asr-status":
            validate_job_id(args.job_id)
            client = create_client(args.region)
            if args.wait:
                job = wait_for_smart_handle_job(
                    client, args.job_id, args.region,
                    args.poll_interval, args.max_wait
                )
            else:
                job = get_smart_handle_job(client, args.job_id, args.region)
            print(f"State: {job.get('State')}")
            if job.get("State") == "Finished":
                segments = parse_asr_result(job)
                print_asr_segments(segments, args.gap_threshold)
                if args.json_out:
                    with open(args.json_out, "w", encoding="utf-8") as fh:
                        json.dump(segments, fh, ensure_ascii=False, indent=2)
                    print(f"Segments written to {args.json_out}")
            elif job.get("State") == "Failed":
                print(f"ErrorCode: {job.get('ErrorCode')}")
                print(f"ErrorMessage: {job.get('ErrorMessage')}")

        elif args.command == "snapshot":
            count = args.count
            if args.cover is not None:
                if args.cover <= 0:
                    raise ValidationError("--cover must be positive")
                import math
                needed = math.ceil(args.cover / args.interval)
                if needed > count:
                    print(f"  --cover {args.cover}s at interval {args.interval}s "
                          f"needs Count {needed}; raising from {count}")
                count = max(count, needed)

            validate_snapshot_output(args.output, args.mode)
            config = build_snapshot_template_config(
                args.mode, time_ms=args.time, count=count,
                interval=args.interval, width=args.width, height=args.height,
                columns=args.columns, lines=args.lines,
            )
            client = create_client(args.region)
            template_id = args.template_id or ensure_snapshot_template(
                client, args.region, args.mode, config
            )
            job_id = submit_snapshot_job(
                client, args.input, args.output, template_id, args.region, config
            )
            print(f"Snapshot job submitted: {job_id}")
            print(f"  mode={args.mode}  Time={args.time}ms  Count={count}  "
                  f"Interval={args.interval}s  covers "
                  f"{count * args.interval}s from {args.time / 1000:.1f}s")
            if not args.wait:
                print(f"Read it with: snapshot-urls -j {job_id} -r {args.region}")
            else:
                wait_for_snapshot_job(
                    client, job_id, args.region, args.poll_interval, args.max_wait
                )
                print_snapshot_urls(get_snapshot_urls(
                    client, job_id, args.region, args.url_timeout
                ))

        elif args.command == "snapshot-urls":
            validate_job_id(args.job_id)
            client = create_client(args.region)
            print_snapshot_urls(get_snapshot_urls(
                client, args.job_id, args.region, args.url_timeout
            ))

        elif args.command == "compile":
            edl = load_json_input(args.edl, "edl")
            edl, edl_warnings = validate_edl(edl)

            region = getattr(args, "region", None)
            if region:
                validate_region(region)

            timeline = compile_edl(edl)
            validate_timeline(timeline)
            blocking, lint_warnings = lint_timeline(timeline, region)
            warnings = edl_warnings + lint_warnings

            if not args.quiet:
                print("EDL")
                print(edl_summary(edl))
                print("\nPre-submit checklist (SKILL.md §5)")
                print_lint(blocking, warnings)
                if region is None:
                    print("  note   --region not given; the AI-feature region "
                          "check was skipped")

            if blocking:
                print(
                    f"\nNot compiled: {len(blocking)} blocking violation(s). "
                    f"Each cites the SKILL.md section holding the failed job it "
                    f"prevents.",
                    file=sys.stderr,
                )
                sys.exit(1)
            if args.strict and warnings:
                print(
                    f"\nNot compiled: --strict and {len(warnings)} warning(s).",
                    file=sys.stderr,
                )
                sys.exit(1)

            payload = json.dumps(timeline, ensure_ascii=False, indent=2)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as fh:
                    fh.write(payload + "\n")
                if not args.quiet:
                    print(f"\nTimeline written to {args.output}")
            else:
                if not args.quiet:
                    print()
                print(payload)

        elif args.command == "submit":
            # Load and validate timeline
            timeline = load_json_input(args.timeline, "timeline")
            validate_timeline(timeline)

            # §5 pre-submit checklist. Blocks only on rules with a recorded
            # failed job; everything else is advisory — ICE has no dry-run
            # endpoint, so a false positive here would be worse than no check.
            blocking, warnings = lint_timeline(timeline, args.region)
            if blocking or warnings:
                print("Pre-submit checklist (SKILL.md §5)")
                print_lint(blocking, warnings)
                # The checklist goes to stdout and the error to stderr; without
                # a flush the two interleave unpredictably under a pipe.
                sys.stdout.flush()
            if blocking:
                raise ValidationError(
                    f"{len(blocking)} blocking checklist violation(s); each cites "
                    f"the SKILL.md section holding the failed job it prevents"
                )
            
            # Load and validate output config
            output_config = load_json_input(args.output_config, "output-config")
            validate_output_config(output_config)
            
            # Validate client token if provided
            client_token = validate_client_token(getattr(args, 'client_token', None))
            
            # Perform protective pre-check before high-risk operation
            if not confirm_high_risk_operation(output_config, args.region, getattr(args, 'yes', False)):
                print("\n❌ Operation cancelled by user.")
                sys.exit(0)
            
            client = create_client(args.region)
            job_id, used_token = submit_media_producing_job(
                client, timeline, output_config, args.region, client_token
            )
            print(f"Job submitted: {job_id}")
            print(f"ClientToken: {mask_token(used_token)} (save this for retry if needed)")
            
            if args.wait:
                job = wait_for_job_completion(
                    client, job_id, args.region, args.poll_interval, args.max_wait
                )
                print_media_producing_job(job)
        
        elif args.command == "status":
            # Validate job ID
            validate_job_id(args.job_id)
            
            client = create_client(args.region)
            
            if args.wait:
                job = wait_for_job_completion(
                    client, args.job_id, args.region, args.poll_interval, args.max_wait
                )
            else:
                job = get_media_producing_job(client, args.job_id, args.region)
            print_media_producing_job(job, args.details)
        
        elif args.command == "media-info":
            # Validate media ID
            validate_media_id(args.media_id)
            
            client = create_client(args.region)
            info = get_media_info(client, args.media_id, args.region)
            
            print(f"MediaId: {info['MediaId']}")
            if info.get("FileName"):
                print(f"FileName: {info['FileName']}")
            if info.get("MediaType"):
                print(f"MediaType: {info['MediaType']}")
            if info.get("Duration") is not None:
                print(f"Duration: {info['Duration']}")
            if info.get("Width") and info.get("Height"):
                print(f"Resolution: {info['Width']}x{info['Height']}")
            print(f"Region: {info['Region']}")
            print(f"Signed URL: {info['FileUrl']}")
            print("ℹ️  Metadata only — duration and resolution are not verification (SKILL.md §9).")
            print("   This signed URL expires in ~1 h and is for your own inspection;")
            print("   hand the user one from scripts/oss_sign_clean.sh instead (SKILL.md §8).")
            streams, probe_warning = probe_stream_durations(info["FileUrl"])
            if probe_warning:
                print(f"Stream probe warning: {probe_warning}", file=sys.stderr)
            else:
                print_stream_durations(streams)
    
        elif args.command == "iproduction":
            validate_function_name(args.function)
            validate_function_region(args.function, args.region)
            
            if args.name and len(args.name) > 100:
                raise ValidationError("Job name must be no longer than 100 characters")
            if args.user_data and len(args.user_data) > 256:
                raise ValidationError("UserData must be no longer than 256 characters")
            if args.priority is not None and not 1 <= args.priority <= 10:
                raise ValidationError("Priority must be between 1 and 10")
            
            input_media = build_iproduction_input(args.input, args.input_type)
            output_media = build_iproduction_output(
                args.output, args.function, args.output_type,
                args.output_biz, args.output_url
            )
            
            job_params = None
            if args.job_params:
                job_params = load_json_input(args.job_params, "job-params")
            
            # Perform protective pre-check before high-risk operation
            if not confirm_iproduction_submission(
                args.function, input_media, output_media, args.region,
                job_params, getattr(args, 'yes', False)
            ):
                print("\n❌ Operation cancelled by user.")
                sys.exit(0)
            
            client = create_client(args.region)
            job_id = submit_iproduction_job(
                client,
                args.function,
                input_media,
                output_media,
                args.region,
                name=args.name,
                job_params=job_params,
                template_id=args.template_id,
                model_id=args.model_id,
                pipeline_id=args.pipeline_id,
                priority=args.priority,
                user_data=args.user_data
            )
            print(f"Job submitted: {job_id}")
            
            if args.wait:
                job = wait_for_iproduction_job(
                    client, job_id, args.region, args.poll_interval, args.max_wait
                )
                print_iproduction_job(job)
        
        elif args.command == "iproduction-status":
            validate_job_id(args.job_id)
            
            client = create_client(args.region)
            
            if args.wait:
                job = wait_for_iproduction_job(
                    client, args.job_id, args.region, args.poll_interval, args.max_wait
                )
            else:
                job = query_iproduction_job(client, args.job_id, args.region)
            
            print_iproduction_job(job)

        elif args.command == "export-timeline":
            validate_project_export_type(args.export_type, args.region)
            output_media_config = build_project_export_output_config(
                args.bucket, args.prefix, args.width, args.height
            )

            timeline = None
            if args.timeline:
                timeline = load_json_input(args.timeline, "timeline")
                validate_timeline(timeline)

            if not confirm_project_export_submission(
                output_media_config, args.region, args.export_type,
                args.project_id, getattr(args, 'yes', False)
            ):
                print("\n❌ Operation cancelled by user.")
                sys.exit(0)

            client = create_client(args.region)
            job_id = submit_project_export_job(
                client, output_media_config, args.region,
                project_id=args.project_id,
                timeline=timeline,
                export_type=args.export_type,
                user_data=args.user_data,
            )
            print(f"Export job submitted: {job_id}")

            if not args.wait:
                print(f"Read it with: export-timeline-status -j {job_id} "
                      f"-r {args.region}")
            else:
                job = wait_for_project_export_job(
                    client, job_id, args.region, args.poll_interval, args.max_wait
                )
                print_project_export_job(job, args.timeline_out)

        elif args.command == "export-timeline-status":
            validate_job_id(args.job_id)

            client = create_client(args.region)

            if args.wait:
                job = wait_for_project_export_job(
                    client, args.job_id, args.region,
                    args.poll_interval, args.max_wait
                )
            else:
                job = get_project_export_job(client, args.job_id, args.region)

            print_project_export_job(job, args.timeline_out)

        elif args.command == "decompile":
            timeline = load_json_input(args.timeline, "timeline")
            validate_timeline(timeline)

            style = None
            if args.style_from:
                style = extract_asr_style(
                    load_json_input(args.style_from, "style-from")
                )

            srt_texts = None
            if args.inline_srt:
                import os as _os
                skill_dir = _os.path.dirname(
                    _os.path.dirname(_os.path.abspath(__file__))
                )
                srt_texts = fetch_srt_texts(timeline, skill_dir, args.srt)
            elif args.srt:
                raise ValidationError("--srt only applies together with --inline-srt")

            edl, warnings = decompile_timeline(timeline, srt_texts, style)

            # The EDL must survive its own front door, and the Timeline it
            # compiles back to must survive the §5 checklist.
            edl, edl_warnings = validate_edl(edl)
            recompiled = compile_edl(edl)
            validate_timeline(recompiled)
            blocking, lint_warnings = lint_timeline(recompiled)
            warnings = warnings + edl_warnings + lint_warnings

            if not args.quiet:
                print("EDL")
                print(edl_summary(edl))
                print("\nRound-trip checklist (SKILL.md §5, on the recompiled Timeline)")
                print_lint(blocking, warnings)
                sys.stdout.flush()

            if blocking:
                print(
                    f"\nNot decompiled: the recompiled Timeline has "
                    f"{len(blocking)} blocking violation(s).",
                    file=sys.stderr,
                )
                sys.exit(1)
            if args.strict and warnings:
                print(
                    f"\nNot decompiled: --strict and {len(warnings)} warning(s).",
                    file=sys.stderr,
                )
                sys.exit(1)

            payload = json.dumps(edl, ensure_ascii=False, indent=2)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as fh:
                    fh.write(payload + "\n")
                if not args.quiet:
                    print(f"\nEDL written to {args.output}")
            else:
                if not args.quiet:
                    print()
                print(payload)

    except ValidationError as e:
        print(f"Validation Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
