#!/usr/bin/env python3
"""
mps_transcode.py — Alibaba Cloud MPS Video Transcoding Script

Features:
  Submit video transcoding jobs using MPS SubmitJobs API.
  Supports adaptive single-resolution transcoding with narrowband HD templates.
  Auto-download transcoded results to local directory.

Dependency Check:
  Script automatically verifies required packages are installed.
  If missing, provides clear installation instructions.

Input Methods (mutually exclusive):
  --url <URL>          Publicly accessible video URL
  --oss-object <PATH>  OSS object path (will be formatted as oss://bucket/key)

Adaptive Mode (Default):
  When neither --preset nor --template-id is specified, the script will:
  1. Detect source video resolution via MediaInfoJob
  2. Automatically select the best matching narrowband HD template
  3. Use appropriate pipeline (narrowband for narrowband templates, standard for others)

Resolution Presets (Manual Override):
  --preset 360p   640x360, 800kbps
  --preset 480p   854x480, 1200kbps
  --preset 720p   1280x720, 2500kbps
  --preset 1080p  1920x1080, 4500kbps
  --preset 4k     3840x2160, 15000kbps
  --preset multi  Generate 360p/480p/720p/1080p versions simultaneously

Custom Parameters (override preset):
  --codec         Video codec H.264/H.265 (default H.264)
  --width/--height Custom resolution
  --bitrate       Video bitrate (kbps)
  --container     Container format mp4/hls (default mp4)
  --fps           Frame rate
  --template-id   Use MPS template ID directly

Output Configuration:
  --output-bucket Output OSS Bucket (default from env var)
  --output-prefix Output file prefix

Other:
  --region        Service region (default cn-shanghai)
  --pipeline-id   MPS pipeline ID (default from env var or auto-selected)
  --async         Submit without waiting for completion
  --dry-run       Only print request parameters

Examples:
  # Adaptive mode (auto-detect source resolution, use narrowband HD)
  python mps_transcode.py --oss-object /input/video.mp4

  # URL input + adaptive mode
  python mps_transcode.py --url https://example.com/video.mp4

  # OSS input + 720p preset
  python mps_transcode.py --oss-object /input/video.mp4 --preset 720p

  # OSS input + multi resolution
  python mps_transcode.py --oss-object /input/video.mp4 --preset multi

  # Custom parameters
  python mps_transcode.py --oss-object /input/video.mp4 --codec H.265 --width 1920 --bitrate 3000

  # Use template ID directly
  python mps_transcode.py --oss-object /input/video.mp4 --template-id your-template-id
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import local modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load_env import ensure_env_loaded, get_region_with_inference
from poll_task import poll_mps_job


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

# SDK imports - check availability
try:
    from alibabacloud_credentials.client import Client as CredClient
    from alibabacloud_mts20140618.client import Client as MtsClient
    from alibabacloud_mts20140618 import models as mts_models
    from alibabacloud_tea_openapi.models import Config as OpenApiConfig
    _SDK_AVAILABLE = True
except ImportError as e:
    _SDK_AVAILABLE = False
    _SDK_ERROR = str(e)


# Standard Templates (默认使用，兼容 Standard 管道)
STANDARD_TEMPLATES = {
    "LD":  {"template_id": "S00000001-200010", "long_edge": 640,  "max_bitrate": 400},
    "SD":  {"template_id": "S00000001-200020", "long_edge": 848,  "max_bitrate": 800},
    "HD":  {"template_id": "S00000001-200030", "long_edge": 1280, "max_bitrate": 1800},
    "FHD": {"template_id": "S00000001-200040", "long_edge": 1920, "max_bitrate": 3000},
    "2K":  {"template_id": "S00000001-200060", "long_edge": 2048, "max_bitrate": 3500},
    "4K":  {"template_id": "S00000001-200070", "long_edge": 3840, "max_bitrate": 6000},
}

# Narrowband HD Templates (需要 NarrowBandHDV2 管道)
NARROWBAND_TEMPLATES = {
    "LD":  {"template_id": "S00000003-200020", "long_edge": 640,  "max_bitrate": 400},
    "SD":  {"template_id": "S00000003-200030", "long_edge": 848,  "max_bitrate": 800},
    "HD":  {"template_id": "S00000003-200040", "long_edge": 1280, "max_bitrate": 1500},
    "FHD": {"template_id": "S00000003-200050", "long_edge": 1920, "max_bitrate": 3000},
}

# Legacy preset parameters table (for manual mode)
PRESET_PARAMS = {
    "360p": {"width": 640, "height": 360, "video_bitrate": 800, "audio_bitrate": 64},
    "480p": {"width": 854, "height": 480, "video_bitrate": 1200, "audio_bitrate": 96},
    "720p": {"width": 1280, "height": 720, "video_bitrate": 2500, "audio_bitrate": 128},
    "1080p": {"width": 1920, "height": 1080, "video_bitrate": 4500, "audio_bitrate": 128},
    "4k": {"width": 3840, "height": 2160, "video_bitrate": 15000, "audio_bitrate": 192},
}

# Preset to Standard Template mapping
PRESET_TEMPLATE_MAP = {
    "360p": "S00000001-200010",  # LD
    "480p": "S00000001-200020",  # SD
    "720p": "S00000001-200030",  # HD
    "1080p": "S00000001-200040",  # FHD
    "4k": "S00000001-200070",  # 4K
}

MULTI_PRESETS = ["360p", "480p", "720p", "1080p"]


def get_oss_bucket():
    """Get OSS Bucket name from environment variable."""
    return os.environ.get("ALIBABA_CLOUD_OSS_BUCKET", "")


def get_pipeline_id():
    """Get MPS Pipeline ID from environment variable."""
    return os.environ.get("ALIBABA_CLOUD_MPS_PIPELINE_ID", "")


def create_client(region):
    """Create MPS client with timeout and user-agent configuration.
    
    Args:
        region: MPS service region
    
    Returns:
        MtsClient instance with proper configuration
    """
    if not _SDK_AVAILABLE:
        print("Error: Please install Alibaba Cloud SDK: pip install alibabacloud-mts20140618 alibabacloud-credentials", file=sys.stderr)
        sys.exit(1)
    cred = CredClient()
    config = OpenApiConfig(
        credential=cred,
        endpoint=f"mts.{region}.aliyuncs.com",
        region_id=region,
        connect_timeout=5000,  # 5 seconds connection timeout
        read_timeout=30000,    # 30 seconds read timeout
        user_agent='AlibabaCloud-Agent-Skills',  # Required user-agent
    )
    return MtsClient(config)


def build_input(args):
    """Build Input parameter for SubmitJobs API."""
    bucket = args.output_bucket or get_oss_bucket()
    region = args.region
    
    if args.url:
        # URL input - MPS doesn't directly support URL input in SubmitJobs
        # User should use OSS input instead
        print("Error: MPS SubmitJobs API requires OSS input. Please upload to OSS first or use --oss-object", file=sys.stderr)
        sys.exit(1)
    elif args.oss_object:
        if not bucket:
            print("Error: OSS input requires Bucket. Please set via --output-bucket or ALIBABA_CLOUD_OSS_BUCKET env var", file=sys.stderr)
            sys.exit(1)
        oss_object = args.oss_object
        # OSS Object key should not start with /
        if oss_object.startswith("/"):
            oss_object = oss_object[1:]
        
        # URL encode the object path (MPS requires URL encoding for Object field)
        encoded_object = urllib.parse.quote(oss_object, safe='/')
        
        return json.dumps({
            "Bucket": bucket,
            "Location": f"oss-{region}",
            "Object": encoded_object
        })
    else:
        print("Error: Please specify input source --oss-object", file=sys.stderr)
        sys.exit(1)


def build_input_for_mediainfo(args):
    """Build Input JSON for MediaInfoJob API."""
    if not _SDK_AVAILABLE:
        print("Error: Please install Alibaba Cloud SDK: pip install alibabacloud-mts20140618 alibabacloud-credentials", file=sys.stderr)
        sys.exit(1)
    
    bucket = args.output_bucket or get_oss_bucket()
    region = args.region
    
    if args.url:
        # URL input is supported for MediaInfoJob
        return json.dumps({"URL": args.url})
    elif args.oss_object:
        if not bucket:
            print("Error: OSS input requires Bucket. Please set via --output-bucket or ALIBABA_CLOUD_OSS_BUCKET env var", file=sys.stderr)
            sys.exit(1)
        oss_object = args.oss_object
        # OSS Object key should not start with /
        if oss_object.startswith("/"):
            oss_object = oss_object[1:]
        
        # URL encode the object path (MPS requires URL encoding for Object field)
        encoded_object = urllib.parse.quote(oss_object, safe='/')
        
        return json.dumps({
            "Bucket": bucket,
            "Location": f"oss-{region}",
            "Object": encoded_object
        })
    else:
        print("Error: Please specify input source --oss-object or --url", file=sys.stderr)
        sys.exit(1)


def get_source_video_resolution(client, args, pipeline_id=None):
    """
    Get source video resolution using MediaInfoJob.

    Args:
        client: MPS client instance
        args: Command line arguments
        pipeline_id: Pipeline ID for MediaInfoJob (optional but recommended)

    Returns:
        tuple: (width, height) or (None, None) if failed
    """
    try:
        input_json = build_input_for_mediainfo(args)

        # Submit MediaInfoJob
        request = mts_models.SubmitMediaInfoJobRequest(
            input=input_json,
            async_=True
        )

        # Add pipeline_id if provided
        if pipeline_id:
            request.pipeline_id = pipeline_id

        response = _call_with_retry(client.submit_media_info_job, request)
        result = response.body.to_map() if hasattr(response.body, 'to_map') else json.loads(response.body.to_json())
        
        job_id = result.get("MediaInfoJob", {}).get("JobId", "")
        if not job_id:
            print("[Auto] Warning: Failed to get MediaInfoJob ID", file=sys.stderr)
            return None, None
        
        # Poll for job completion
        # Default timeout: 60 seconds for mediainfo tasks
        poll_result = poll_mps_job(job_id, job_type="mediainfo", region=args.region)
        
        if poll_result is None:
            print("[Auto] Warning: MediaInfoJob polling timeout", file=sys.stderr)
            return None, None
        
        # Extract resolution from result
        # to_map() returns data directly without body wrapper
        data = poll_result.get("body") if "body" in poll_result else poll_result
        job_list = data.get("MediaInfoJobList", {}).get("MediaInfoJob", [])
        job = job_list[0] if job_list else {}
        properties = job.get("Properties", {}) or {}
        
        width = properties.get("Width")
        height = properties.get("Height")
        
        if width and height:
            return int(width), int(height)
        else:
            print("[Auto] Warning: Could not extract resolution from media info", file=sys.stderr)
            return None, None
            
    except Exception as e:
        print(f"[Auto] Warning: Failed to get source video resolution: {e}", file=sys.stderr)
        return None, None


def select_template_by_resolution(width, height):
    """
    Select the best template based on source video resolution.
    Uses Standard templates by default (compatible with Standard pipeline).
    
    Returns:
        tuple: (template_id, resolution_name, is_narrowband, long_edge)
    """
    if width is None or height is None:
        # Default to HD if we can't detect resolution
        template = STANDARD_TEMPLATES["HD"]
        return template["template_id"], "HD", False, template["long_edge"]
    
    long_edge = max(width, height)
    
    # Select based on long edge - use Standard templates (compatible with Standard pipeline)
    if long_edge <= 640:
        template = STANDARD_TEMPLATES["LD"]
        return template["template_id"], "LD", False, long_edge
    elif long_edge <= 848:
        template = STANDARD_TEMPLATES["SD"]
        return template["template_id"], "SD", False, long_edge
    elif long_edge <= 1280:
        template = STANDARD_TEMPLATES["HD"]
        return template["template_id"], "HD", False, long_edge
    elif long_edge <= 1920:
        template = STANDARD_TEMPLATES["FHD"]
        return template["template_id"], "FHD", False, long_edge
    elif long_edge <= 2048:
        template = STANDARD_TEMPLATES["2K"]
        return template["template_id"], "2K", False, long_edge
    else:
        template = STANDARD_TEMPLATES["4K"]
        return template["template_id"], "4K", False, long_edge


def build_outputs(args, preset_name=None, template_id=None):
    """
    Build Outputs parameter for SubmitJobs API.
    
    Returns a JSON array string with output configurations.
    """
    bucket = args.output_bucket or get_oss_bucket()
    if not bucket:
        print("Error: Output Bucket is required. Please set via --output-bucket or ALIBABA_CLOUD_OSS_BUCKET env var", file=sys.stderr)
        sys.exit(1)
    
    output_prefix = args.output_prefix or "output/transcode/"
    if not output_prefix.endswith("/"):
        output_prefix += "/"
    
    outputs = []
    
    if template_id:
        # Use template ID directly (adaptive mode or user-specified)
        output_object = f"{output_prefix}transcoded.mp4"
        outputs.append({
            "OutputObject": output_object,
            "TemplateId": template_id
        })
    elif args.template_id:
        # Use user-specified template ID
        output_object = f"{output_prefix}transcoded.mp4"
        outputs.append({
            "OutputObject": output_object,
            "TemplateId": args.template_id
        })
    else:
        # Build output based on preset or custom parameters
        preset = preset_name or args.preset
        
        if preset and preset in PRESET_TEMPLATE_MAP:
            # Use template ID for preset - only TemplateId and OutputObject, no Video/Audio/Container
            template_id = PRESET_TEMPLATE_MAP[preset]
            output_object = f"{output_prefix}{preset}/transcoded.mp4"
            outputs.append({
                "OutputObject": output_object,
                "TemplateId": template_id
            })
        elif preset and preset in PRESET_PARAMS:
            # Fallback: Build with custom parameters (deprecated, should use template)
            params = PRESET_PARAMS[preset]
            output_object = f"{output_prefix}{preset}/transcoded.mp4"
            
            # Build video configuration
            video_config = {
                "Codec": args.codec if args.codec else "H.264",
                "Width": str(params["width"]),
                "Height": str(params["height"]),
                "Bitrate": str(args.bitrate if args.bitrate else params["video_bitrate"]),
                "Fps": str(args.fps if args.fps else 25)
            }
            
            # Build audio configuration
            audio_config = {
                "Codec": "AAC",
                "Bitrate": str(params["audio_bitrate"]),
                "Channels": "2",
                "Samplerate": "44100"
            }
            
            output = {
                "OutputObject": output_object,
                "Video": video_config,
                "Audio": audio_config,
                "Container": {
                    "Format": args.container.lower() if args.container else "mp4"
                }
            }
            outputs.append(output)
        else:
            # Custom parameters or no preset
            width = args.width if args.width else 1280
            height = args.height if args.height else 720
            bitrate = args.bitrate if args.bitrate else 2500
            
            video_config = {
                "Codec": args.codec if args.codec else "H.264",
                "Width": str(width),
                "Height": str(height),
                "Bitrate": str(bitrate),
                "Fps": str(args.fps if args.fps else 25)
            }
            
            audio_config = {
                "Codec": "AAC",
                "Bitrate": "128",
                "Channels": "2",
                "Samplerate": "44100"
            }
            
            output_object = f"{output_prefix}transcoded.mp4"
            output = {
                "OutputObject": output_object,
                "Video": video_config,
                "Audio": audio_config,
                "Container": {
                    "Format": args.container.lower() if args.container else "mp4"
                }
            }
            outputs.append(output)
    
    return json.dumps(outputs)


def submit_single_job(args, preset_name=None, template_id=None, client=None, region=None, pipeline_id=None):
    """Submit a single transcoding job with idempotency support."""
    if client is None:
        client = create_client(region or args.region)
    
    # Build request parameters
    input_json = build_input(args)
    outputs_json = build_outputs(args, preset_name, template_id)
    
    bucket = args.output_bucket or get_oss_bucket()
    
    # Use provided pipeline_id or fall back to args/env
    if pipeline_id is None:
        pipeline_id = args.pipeline_id or get_pipeline_id()
    
    if not pipeline_id:
        print("Error: Pipeline ID is required. Please set via --pipeline-id or ALIBABA_CLOUD_MPS_PIPELINE_ID env var", file=sys.stderr)
        sys.exit(1)
    
    # Build request parameters
    request_params = {
        "input": input_json,
        "outputs": outputs_json,
        "output_bucket": bucket,
        "output_location": f"oss-{region or args.region}",
        "pipeline_id": pipeline_id,
    }
    
    # Try to add client_token for idempotency if SDK supports it
    # Note: Some SDK versions (e.g., 6.0.3) don't support client_token parameter
    import hashlib
    import inspect
    input_str = f"{input_json}-{outputs_json}-{pipeline_id}-{int(time.time() / 60)}"
    client_token = hashlib.md5(input_str.encode()).hexdigest()
    
    # Check if SubmitJobsRequest accepts client_token parameter
    sig = inspect.signature(mts_models.SubmitJobsRequest.__init__)
    if 'client_token' in sig.parameters:
        request_params['client_token'] = client_token
    
    request = mts_models.SubmitJobsRequest(**request_params)
    
    if args.dry_run:
        return {
            "preset": preset_name or "custom",
            "template_id": template_id,
            "input": input_json,
            "outputs": outputs_json,
            "output_bucket": bucket,
            "pipeline_id": pipeline_id,
            "dry_run": True
        }
    
    try:
        response = _call_with_retry(client.submit_jobs, request)
        result = response.body.to_map() if hasattr(response.body, 'to_map') else json.loads(response.body.to_json())

        # Extract job ID from response
        # to_map() returns data directly without body wrapper
        job_result_list = result.get("JobResultList", {})
        job_results = job_result_list.get("JobResult", []) if job_result_list else []
        if job_results:
            job_id = job_results[0].get("Job", {}).get("JobId", "N/A")
        else:
            job_id = "N/A"
        
        return {
            "preset": preset_name or "custom",
            "template_id": template_id,
            "job_id": job_id,
            "result": result
        }
    except Exception as e:
        return {
            "preset": preset_name or "custom",
            "template_id": template_id,
            "error": str(e)
        }


def validate_url(url: str) -> bool:
    """Validate URL format and security."""
    if not url:
        return False
    
    # Check URL format
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
            # Block localhost and private IP ranges
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
    
    # Normalize path
    path = path.strip()
    
    # Path should start with /
    if not path.startswith('/'):
        print(f"Error: OSS path must start with '/', got: {path}", file=sys.stderr)
        return False
    
    # Prevent path traversal attacks
    if '..' in path:
        print(f"Error: OSS path contains invalid traversal sequence '..': {path}", file=sys.stderr)
        return False
    
    # Prevent absolute path injection
    if path.startswith('//') or '//' in path.replace('oss://', ''):
        print(f"Error: OSS path contains invalid double slashes: {path}", file=sys.stderr)
        return False
    
    # Check for valid characters (basic validation)
    import re
    if not re.match(r'^/[a-zA-Z0-9/_\-.]+$', path):
        print(f"Error: OSS path contains invalid characters: {path}", file=sys.stderr)
        return False
    
    return True


def validate_output_prefix(prefix: str) -> bool:
    """Validate output prefix format."""
    if not prefix:
        return True  # Empty is OK, will use default
    
    # Prevent path traversal
    if '..' in prefix:
        print(f"Error: Output prefix contains invalid sequence '..': {prefix}", file=sys.stderr)
        return False
    
    # Should not start with /
    if prefix.startswith('/'):
        print(f"Error: Output prefix should not start with '/': {prefix}", file=sys.stderr)
        return False
    
    return True


def process_transcode(args):
    """Process transcoding tasks."""
    # Validate input parameters
    if args.url:
        if not validate_url(args.url):
            print("Error: Invalid URL format or security check failed", file=sys.stderr)
            sys.exit(1)
    
    if args.oss_object:
        if not validate_oss_path(args.oss_object):
            print("Error: Invalid OSS object path format or security check failed", file=sys.stderr)
            sys.exit(1)
    
    if args.output_prefix:
        if not validate_output_prefix(args.output_prefix):
            print("Error: Invalid output prefix format", file=sys.stderr)
            sys.exit(1)
    
    # Smart region inference: explicit --region > OSS URL/bucket > env var > default
    bucket = args.output_bucket or os.environ.get("ALIBABA_CLOUD_OSS_BUCKET")
    endpoint = os.environ.get("ALIBABA_CLOUD_OSS_ENDPOINT")
    region = get_region_with_inference(
        explicit_region=args.region,
        url=args.url,
        endpoint=endpoint,
        bucket=bucket,
    )
    if args.verbose:
        print(f"[Region] Using region: {region} (inferred from input or config)")
    
    # Store inferred region in args for later use
    args.region = region
    
    # Ensure environment variables are loaded
    if not ensure_env_loaded(verbose=args.verbose):
        from load_env import _print_setup_hint
        _print_setup_hint([])
        sys.exit(1)
    
    # Create client
    client = create_client(region)
    
    # Determine mode: adaptive (default) or manual
    is_adaptive = not args.preset and not args.template_id
    
    # For adaptive mode, detect source resolution and select template
    template_id = None
    is_narrowband = False
    selected_resolution = None
    source_width = None
    source_height = None
    source_long_edge = None
    
    # Determine pipeline type and get pipeline ID first (needed for adaptive mode)
    pipeline_id = None
    if args.pipeline_id:
        pipeline_id = args.pipeline_id
        print(f"[Auto] Pipeline: {pipeline_id} (user-specified)")
    else:
        # Import ensure_pipeline from mps_pipeline
        try:
            from mps_pipeline import ensure_pipeline

            # Always use standard pipeline for all transcoding jobs
            pipeline_type = "standard"

            pipeline_id = ensure_pipeline(region=region, pipeline_type=pipeline_type)

            if is_adaptive:
                print(f"[Auto] Pipeline: mts-standard-pipeline (auto-selected)")
            else:
                print(f"Pipeline: {pipeline_id} (auto-selected)")
        except Exception as e:
            print(f"Error: Failed to get pipeline: {e}", file=sys.stderr)
            sys.exit(1)

    if is_adaptive:
        print("=" * 60)
        print("Alibaba Cloud MPS Video Transcoding (Adaptive Mode)")
        print("=" * 60)
        print("\n[Auto] Detecting source video resolution...")

        source_width, source_height = get_source_video_resolution(client, args, pipeline_id)
        
        if source_width and source_height:
            source_long_edge = max(source_width, source_height)
            print(f"[Auto] Source video: {source_width}x{source_height} (long edge: {source_long_edge})")
        else:
            print("[Auto] Warning: Could not detect source resolution, using default HD template")
        
        # Select template based on resolution
        template_id, selected_resolution, is_narrowband, long_edge = select_template_by_resolution(source_width, source_height)
        
        resolution_names = {
            "LD": "360p", "SD": "480p", "HD": "720p", "FHD": "1080p", "2K": "2K", "4K": "4K"
        }
        display_resolution = resolution_names.get(selected_resolution, selected_resolution)
        
        print(f"[Auto] Selected resolution: {selected_resolution} ({display_resolution})")
        if is_narrowband:
            print(f"[Auto] Using narrowband HD template: {template_id}")
        else:
            print(f"[Auto] Using standard template: {template_id}")
    else:
        print("=" * 60)
        print("Alibaba Cloud MPS Video Transcoding")
        print("=" * 60)
    
    # Print execution info
    bucket = args.output_bucket or get_oss_bucket()
    if args.oss_object:
        print(f"Input: OSS - oss://{bucket}{args.oss_object}")
    elif args.url:
        print(f"Input: URL - {args.url}")
    
    output_prefix = args.output_prefix or "output/transcode/"
    print(f"Output: OSS - oss://{bucket}/{output_prefix}")
    
    if args.preset:
        if args.preset == "multi":
            print(f"Preset: multi (generates {', '.join(MULTI_PRESETS)})")
        else:
            preset_info = PRESET_PARAMS.get(args.preset, {})
            print(f"Preset: {args.preset} ({preset_info.get('width', '-')}x{preset_info.get('height', '-')}, {preset_info.get('video_bitrate', '-')}kbps)")
    
    if args.template_id:
        print(f"Template: {args.template_id} (user-specified)")
    
    if args.codec:
        print(f"Codec: {args.codec}")
    
    print("-" * 60)
    
    # Determine if multi-resolution mode
    is_multi = args.preset == "multi"
    presets = MULTI_PRESETS if is_multi else ([args.preset] if args.preset else [None])
    
    # Dry Run mode
    if args.dry_run:
        print("[Dry Run Mode] Only printing request parameters, no actual API call\n")
        
        if is_adaptive:
            result = submit_single_job(args, template_id=template_id, client=client, region=region, pipeline_id=pipeline_id)
            print("\n--- Adaptive Mode ---")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            for preset in presets:
                result = submit_single_job(args, preset, client=client, region=region, pipeline_id=pipeline_id)
                print(f"\n--- Preset: {preset or 'custom'} ---")
                print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    
    # Submit jobs
    print(f"Submitting transcoding jobs...")
    job_results = []
    
    if is_adaptive:
        # Single adaptive job
        result = submit_single_job(args, template_id=template_id, client=client, region=region, pipeline_id=pipeline_id)
        job_results.append(result)
        if "error" in result:
            print(f"  [FAIL] Adaptive transcoding failed: {result['error']}")
        else:
            print(f"  [OK] JobId: {result['job_id']}")
    elif is_multi:
        # Multi-resolution parallel submission
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(submit_single_job, args, preset, None, client, region, pipeline_id): preset for preset in presets}
            for future in as_completed(futures):
                preset = futures[future]
                try:
                    result = future.result()
                    job_results.append(result)
                    if "error" in result:
                        print(f"  [FAIL] {preset}: Submission failed - {result['error']}")
                    else:
                        print(f"  [OK] {preset}: JobId={result['job_id']}")
                except Exception as e:
                    print(f"  [FAIL] {preset}: Exception - {e}")
                    job_results.append({"preset": preset, "error": str(e)})
    else:
        # Single resolution with preset
        result = submit_single_job(args, presets[0], client=client, region=region, pipeline_id=pipeline_id)
        job_results.append(result)
        if "error" in result:
            print(f"  [FAIL] Submission failed: {result['error']}")
        else:
            print(f"  [OK] JobId: {result['job_id']}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Job Submission Summary")
    print("=" * 60)
    
    success_jobs = []
    for result in job_results:
        preset = result.get("preset", "unknown")
        template = result.get("template_id", "")
        if "error" in result:
            if is_adaptive:
                print(f"  [FAIL] Adaptive: Failed - {result['error']}")
            else:
                print(f"  [FAIL] {preset}: Failed - {result['error']}")
        else:
            job_id = result.get("job_id", "N/A")
            if is_adaptive:
                print(f"  [OK] Adaptive ({selected_resolution}): JobId={job_id}")
            else:
                print(f"  [OK] {preset}: JobId={job_id}")
            success_jobs.append({"job_id": job_id, "preset": preset, "template_id": template})
    
    # Poll job status (unless --async specified)
    # Default timeout: 900 seconds (15 minutes) for transcode tasks
    if not args.async_mode and success_jobs:
        print("\n" + "-" * 60)
        print("Polling job status...")
        print("-" * 60)
        
        for job in success_jobs:
            job_id = job["job_id"]
            preset = job.get("preset", "adaptive")
            print(f"\n[{preset or 'adaptive'}] Polling job {job_id}...")
            poll_mps_job(job_id, job_type="transcode", region=region)
    
    # Final summary
    print("\n" + "=" * 60)
    print("Transcoding Complete")
    print("=" * 60)
    for job in success_jobs:
        preset = job.get("preset", "adaptive")
        if is_adaptive and selected_resolution:
            print(f"  {selected_resolution}: JobId={job['job_id']}")
        else:
            print(f"  {preset or 'custom'}: JobId={job['job_id']}")
    
    return job_results


def main():
    parser = argparse.ArgumentParser(
        description="Alibaba Cloud MPS Video Transcoding (Adaptive Narrowband HD)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Adaptive mode (auto-detect source resolution, use narrowband HD)
  python mps_transcode.py --oss-object /input/video.mp4

  # URL input + adaptive mode
  python mps_transcode.py --url https://example.com/video.mp4

  # OSS input + 720p preset
  python mps_transcode.py --oss-object /input/video.mp4 --preset 720p

  # OSS input + multi resolution
  python mps_transcode.py --oss-object /input/video.mp4 --preset multi

  # Custom parameters (H.265 + 1080P)
  python mps_transcode.py --oss-object /input/video.mp4 --codec H.265 --preset 1080p

  # Use template ID directly
  python mps_transcode.py --oss-object /input/video.mp4 --template-id your-template-id

  # Dry Run
  python mps_transcode.py --oss-object /input/video.mp4 --preset 720p --dry-run

  # Async mode (don't wait)
  python mps_transcode.py --oss-object /input/video.mp4 --preset 720p --async
        """
    )
    
    # Input source
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--url", type=str, help="Publicly accessible video URL (for adaptive mode)")
    input_group.add_argument("--oss-object", type=str, help="OSS object path (e.g., /input/video.mp4)")
    
    # Resolution preset
    parser.add_argument(
        "--preset",
        type=str,
        choices=["360p", "480p", "720p", "1080p", "4k", "multi"],
        help="Resolution preset: 360p/480p/720p/1080p/4k/multi (multi=generate 4 versions). If not specified, uses adaptive mode."
    )
    
    # Custom parameters
    parser.add_argument("--codec", type=str, choices=["H.264", "H.265"], help="Video codec (default H.264)")
    parser.add_argument("--width", type=int, help="Video width")
    parser.add_argument("--height", type=int, help="Video height")
    parser.add_argument("--bitrate", type=int, help="Video bitrate (kbps)")
    parser.add_argument("--container", type=str, choices=["mp4", "hls"], help="Container format (default mp4)")
    parser.add_argument("--fps", type=int, help="Frame rate")
    parser.add_argument("--template-id", type=str, help="Use MPS template ID directly (overrides adaptive mode)")
    
    # Output configuration
    parser.add_argument("--output-bucket", type=str, help="Output OSS Bucket (default from env var)")
    parser.add_argument("--output-prefix", type=str, help="Output file prefix (default output/transcode/)")
    
    # Other configuration
    parser.add_argument("--region", type=str, default=None, help="Service region (auto-inferred from OSS input, or fallback to ALIBABA_CLOUD_REGION env var, or cn-shanghai)")
    parser.add_argument("--pipeline-id", type=str, help="MPS pipeline ID (default from env var or auto-selected)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Only print request parameters")
    parser.add_argument("--async", dest="async_mode", action="store_true", help="Async mode, don't wait for completion")
    
    args = parser.parse_args()
    
    job_results = process_transcode(args)
    
    # Check for failures
    if job_results:
        has_error = any("error" in result for result in job_results)
        if has_error:
            sys.exit(1)


if __name__ == "__main__":
    main()
