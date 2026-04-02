#!/usr/bin/env python3
"""
Video Editor Script for Alibaba Cloud ICE (Intelligent Cloud Editing)

This script uses Alibaba Cloud Common SDK to:
1. Submit a video producing job with Timeline and OutputMediaConfig
2. Poll the job status until completion
3. Return the output video URL

Usage:
    # Submit a job and wait for completion
    python video_editor.py submit --timeline timeline.json --output-config output.json --wait

    # Check job status
    python video_editor.py status --job-id <job_id>

Requirements:
    pip install -r requirements.txt

Environment:
    Credentials are automatically obtained via the default credential chain:
    - Environment variables
    - Credentials file (~/.alibabacloud/credentials.ini)
    - ECS RAM role (if running on ECS)
    
    Run `aliyun configure` to set up credentials.
"""

import argparse
import json
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

# Video resolution constraints
MIN_RESOLUTION = 128
MAX_RESOLUTION = 8192

# Job ID pattern (alphanumeric with hyphens)
JOB_ID_PATTERN = re.compile(r'^[a-zA-Z0-9\-]+$')

# ClientToken pattern (alphanumeric with hyphens and underscores, max 64 chars)
CLIENT_TOKEN_PATTERN = re.compile(r'^[a-zA-Z0-9\-_]+$')
CLIENT_TOKEN_MAX_LENGTH = 64

# User-Agent for Alibaba Cloud API calls (required for tracking)
USER_AGENT = "AlibabaCloud-Agent-Skills"

try:
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_tea_openapi.client import Client as OpenApiClient
    from alibabacloud_tea_util import models as util_models
    from alibabacloud_credentials.client import Client as CredentialClient
    from alibabacloud_openapi_util.client import Client as OpenApiUtilClient
except ImportError:
    print("Error: Required packages not installed.")
    print("Please run: pip install -r requirements.txt")
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
    region_id: str = "cn-shanghai"
) -> dict:
    """
    Call Alibaba Cloud ICE API using Common Request.
    
    Args:
        client: OpenAPI client instance
        action: API action name (e.g., "SubmitMediaProducingJob")
        params: API parameters
        region_id: Region ID
    
    Returns:
        API response as dict
    """
    # Build the OpenAPI request
    api_request = open_api_models.OpenApiRequest(
        query=OpenApiUtilClient.query(params)
    )
    
    # Runtime options
    runtime = util_models.RuntimeOptions()
    
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
) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Get the status of a media producing job.
    
    Args:
        client: OpenAPI client instance
        job_id: Job ID to check
        region_id: Region ID
    
    Returns:
        Tuple of (status, media_url, error_message)
        - status: "Init", "Queuing", "Processing", "Success", "Failed"
        - media_url: Output media URL (only when status is "Success")
        - error_message: Error message (only when status is "Failed")
    """
    params = {
        "JobId": job_id
    }
    
    response = call_api(client, "GetMediaProducingJob", params, region_id)
    
    job = response.get("MediaProducingJob", {})
    status = job.get("Status")
    media_url = job.get("MediaURL")
    error_message = job.get("Message")
    
    if not status:
        raise Exception(f"Failed to get job status from response: {response}")
    
    return status, media_url, error_message


def wait_for_job_completion(
    client: OpenApiClient,
    job_id: str,
    region_id: str = "cn-shanghai",
    poll_interval: int = 5,
    max_wait_time: int = 3600,
    verbose: bool = True
) -> Tuple[str, Optional[str]]:
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
        Tuple of (final_status, media_url)
    """
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait_time:
            raise TimeoutError(f"Job {job_id} did not complete within {max_wait_time} seconds")
        
        status, media_url, error_message = get_media_producing_job(client, job_id, region_id)
        
        if verbose:
            print(f"[{int(elapsed)}s] Job {job_id}: {status}")
        
        if status == "Success":
            return status, media_url
        elif status == "Failed":
            raise Exception(f"Job failed: {error_message}")
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
        print("⏩ Skipping confirmation (use --yes or VIDEO_EDITOR_SKIP_CONFIRMATION=1)")
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
    
    status, media_url = wait_for_job_completion(
        client, job_id, region_id, poll_interval, max_wait_time, verbose
    )
    
    if verbose:
        print(f"Job completed!")
        print(f"Output URL: {media_url}")
    
    return media_url


def main():
    parser = argparse.ArgumentParser(
        description="Video Editor for Alibaba Cloud ICE (using Common SDK)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Submit and wait for completion
  python video_editor.py submit -t timeline.json -o output.json --wait

  # Submit without waiting
  python video_editor.py submit -t timeline.json -o output.json

  # Check job status
  python video_editor.py status -j job_id_here
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
        default="cn-shanghai",
        help="Region ID (default: cn-shanghai)"
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
        default="cn-shanghai",
        help="Region ID (default: cn-shanghai)"
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
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        # Validate region for all commands
        validate_region(args.region)
        
        if args.command == "submit":
            # Load and validate timeline
            timeline = load_json_input(args.timeline, "timeline")
            validate_timeline(timeline)
            
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
                status, media_url = wait_for_job_completion(
                    client, job_id, args.region, args.poll_interval, args.max_wait
                )
                print(f"Final status: {status}")
                if media_url:
                    print(f"Output URL: {media_url}")
        
        elif args.command == "status":
            # Validate job ID
            validate_job_id(args.job_id)
            
            client = create_client(args.region)
            
            if args.wait:
                status, media_url = wait_for_job_completion(
                    client, args.job_id, args.region, args.poll_interval, args.max_wait
                )
                print(f"Final status: {status}")
                if media_url:
                    print(f"Output URL: {media_url}")
            else:
                status, media_url, error_message = get_media_producing_job(
                    client, args.job_id, args.region
                )
                print(f"Status: {status}")
                if media_url:
                    print(f"Output URL: {media_url}")
                if error_message:
                    print(f"Error: {error_message}")
    
    except ValidationError as e:
        print(f"Validation Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
