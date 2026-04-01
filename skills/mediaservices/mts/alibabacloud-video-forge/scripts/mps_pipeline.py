#!/usr/bin/env python3
"""
mps_pipeline.py — Alibaba Cloud MPS Pipeline Management Script

Features:
  List all MPS pipelines for the current account.
  Auto-select the best pipeline based on name and state.

Usage Modes:
  # List all pipelines (table format)
  python3 mps_pipeline.py

  # Auto-select mode (outputs PipelineId only, for shell capture)
  python3 mps_pipeline.py --select

  # Specify preferred pipeline name
  python3 mps_pipeline.py --select --name my-pipeline

  # JSON output format
  python3 mps_pipeline.py --json

Python API:
  from mps_pipeline import get_pipeline_id
  pipeline_id = get_pipeline_id(region="cn-shanghai", preferred_name="mts-service-pipeline")
"""

import argparse
import json
import os
import sys
import time
from typing import List, Optional, Dict, Any

# Import local modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load_env import ensure_env_loaded


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
                print("[Retry] Network error detected, retrying in 2s...", file=sys.stderr)
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
except ImportError:
    _SDK_AVAILABLE = False
    CredClient = None
    MtsClient = None
    mts_models = None
    OpenApiConfig = None


def create_client(region: str) -> MtsClient:
    """Create MPS client with default credential chain and user-agent."""
    if not _SDK_AVAILABLE:
        raise RuntimeError(
            "Alibaba Cloud SDK not installed. "
            "Please install: pip install alibabacloud-mts20140618 alibabacloud-credentials"
        )
    cred = CredClient()
    config = OpenApiConfig(
        credential=cred,
        endpoint=f"mts.{region}.aliyuncs.com",
        region_id=region,
        user_agent='AlibabaCloud-Agent-Skills',  # Required user-agent
    )
    return MtsClient(config)


def search_pipelines(
    client: MtsClient, state: Optional[str] = None, page_size: int = 100,
    verbose: bool = False
) -> List[Dict[str, Any]]:
    """
    Search all pipelines using SearchPipeline API.

    Args:
        client: MTS client instance
        state: Filter by state (Active/Paused), None for all
        page_size: Number of results per page
        verbose: Print debug information

    Returns:
        List of pipeline dictionaries
    """
    request = mts_models.SearchPipelineRequest(
        page_number=1,
        page_size=page_size,
    )
    if state:
        request.state = state

    try:
        response = _call_with_retry(client.search_pipeline, request)
        result = response.body.to_map() if hasattr(response.body, 'to_map') else json.loads(response.body.to_json())

        if verbose:
            print(f"[search_pipelines] Raw response: {json.dumps(result, indent=2, default=str)[:2000]}", file=sys.stderr)

        # Handle different possible response structures
        pipeline_list = []
        if "PipelineList" in result:
            pipeline_list = result.get("PipelineList", {}).get("Pipeline", [])
        elif "pipeline_list" in result:
            pipeline_list = result.get("pipeline_list", {}).get("pipeline", [])
        
        # Ensure pipeline_list is a list
        if not isinstance(pipeline_list, list):
            if isinstance(pipeline_list, dict):
                pipeline_list = [pipeline_list]
            else:
                pipeline_list = []
        
        if verbose:
            print(f"[search_pipelines] Found {len(pipeline_list)} pipeline(s)", file=sys.stderr)
            for p in pipeline_list:
                print(f"  - Id={p.get('Id')}, Name={p.get('Name')}, State={p.get('State')}, Speed={p.get('Speed')}", file=sys.stderr)
        
        return pipeline_list
    except Exception as e:
        print(f"Error searching pipelines: {e}", file=sys.stderr)
        raise


def format_pipeline_table(pipelines: List[Dict[str, Any]]) -> str:
    """Format pipeline list as a readable table."""
    if not pipelines:
        return "No pipelines found."

    # Calculate column widths
    id_width = max(len(str(p.get("Id", ""))) for p in pipelines)
    id_width = max(id_width, len("PipelineId"))

    name_width = max(len(str(p.get("Name", ""))) for p in pipelines)
    name_width = max(name_width, len("Name"))

    state_width = max(len(str(p.get("State", ""))) for p in pipelines)
    state_width = max(state_width, len("State"))

    speed_width = max(len(str(p.get("Speed", ""))) for p in pipelines)
    speed_width = max(speed_width, len("Speed"))

    # Build table
    lines = []
    header = f"{'PipelineId':<{id_width}}  {'Name':<{name_width}}  {'State':<{state_width}}  {'Speed':<{speed_width}}"
    lines.append(header)
    lines.append("-" * len(header))

    for p in pipelines:
        pid = str(p.get("Id", "N/A"))
        name = str(p.get("Name", "N/A"))
        state = str(p.get("State", "N/A"))
        speed = str(p.get("Speed", "N/A"))
        lines.append(f"{pid:<{id_width}}  {name:<{name_width}}  {state:<{state_width}}  {speed:<{speed_width}}")

    return "\n".join(lines)


def select_pipeline(
    pipelines: List[Dict[str, Any]], preferred_name: str = "mts-service-pipeline"
) -> Optional[Dict[str, Any]]:
    """
    Select the best pipeline based on priority:
    1. Pipeline matching preferred_name with Active state
    2. Any pipeline with Active state (first one)
    3. None if no Active pipelines

    Args:
        pipelines: List of pipeline dictionaries
        preferred_name: Preferred pipeline name

    Returns:
        Selected pipeline dictionary or None
    """
    if not pipelines:
        return None

    # Priority 1: Name matches preferred_name and state is Active
    for p in pipelines:
        if p.get("Name") == preferred_name and p.get("State") == "Active":
            return p

    # Priority 2: Any Active pipeline
    for p in pipelines:
        if p.get("State") == "Active":
            return p

    # No Active pipelines found
    return None


def get_pipeline_id(
    region: str = None,
    preferred_name: str = "mts-service-pipeline",
    verbose: bool = False,
) -> str:
    """
    Get the best pipeline ID for the specified region.

    Args:
        region: Alibaba Cloud region (default from ALIBABA_CLOUD_REGION env var or cn-shanghai)
        preferred_name: Preferred pipeline name to match
        verbose: Print detailed logs

    Returns:
        Pipeline ID string

    Raises:
        RuntimeError: If no suitable pipeline is found
    """
    if region is None:
        region = os.environ.get("ALIBABA_CLOUD_REGION", "cn-shanghai")
    if verbose:
        print(f"[get_pipeline_id] Searching pipelines in region: {region}", file=sys.stderr)
        print(f"[get_pipeline_id] Preferred pipeline name: {preferred_name}", file=sys.stderr)

    client = create_client(region)
    pipelines = search_pipelines(client)

    if verbose:
        print(f"[get_pipeline_id] Found {len(pipelines)} pipeline(s)", file=sys.stderr)

    selected = select_pipeline(pipelines, preferred_name)

    if selected is None:
        raise RuntimeError(
            f"No Active pipeline found in region {region}. "
            f"Please create a pipeline or check your configuration."
        )

    pipeline_id = selected.get("Id")
    pipeline_name = selected.get("Name", "N/A")
    pipeline_state = selected.get("State", "N/A")

    if verbose:
        print(
            f"[get_pipeline_id] Selected pipeline: {pipeline_id} "
            f"(name={pipeline_name}, state={pipeline_state})",
            file=sys.stderr,
        )

    return pipeline_id


# Pipeline type configuration mapping
PIPELINE_TYPE_CONFIG = {
    "standard": {
        "speed": "Standard",
        "default_name": "mts-standard-pipeline",
    },
    "narrowband": {
        "speed": "NarrowBandHDV2",
        "default_name": "mts-narrowband-pipeline",
    },
    "audit": {
        "speed": "AIVideoCensor",
        "default_name": "mts-audit-pipeline",
    },
    "smarttag": {
        "speed": "AIVideoMCU",
        "default_name": "mts-smarttag-pipeline",
    },
}


def ensure_pipeline(region=None, pipeline_type="standard", preferred_name=None, verbose=False):
    """
    Ensure specified type of pipeline is available, create if not exists.

    Args:
        region: Alibaba Cloud region (default from ALIBABA_CLOUD_REGION env var or cn-shanghai)
        pipeline_type: Pipeline type, available values:
            - "standard"   → Speed: Standard    (Transcoding/Snapshot/MediaInfo)
            - "narrowband" → Speed: NarrowBandHDV2 (Narrowband HD Transcoding)
            - "audit"      → Speed: AIVideoCensor  (Content Audit)
            - "smarttag"   → Speed: AIVideoMCU     (Smart Tag)
        preferred_name: Preferred pipeline name for matching
        verbose: Print debug information

    Returns:
        pipeline_id (str)

    Raises:
        ValueError: If pipeline_type is invalid
        RuntimeError: If failed to create pipeline
    """
    if region is None:
        region = os.environ.get("ALIBABA_CLOUD_REGION", "cn-shanghai")
    if pipeline_type not in PIPELINE_TYPE_CONFIG:
        valid_types = ", ".join(PIPELINE_TYPE_CONFIG.keys())
        raise ValueError(f"Invalid pipeline_type '{pipeline_type}'. Valid types: {valid_types}")

    config = PIPELINE_TYPE_CONFIG[pipeline_type]
    target_speed = config["speed"]
    default_name = config["default_name"]

    # Use preferred_name if provided, otherwise use default name
    # Also check for common preferred name "mts-service-pipeline"
    name_to_match = preferred_name if preferred_name else default_name

    print(f"[ensure_pipeline] Searching {pipeline_type} pipelines (Speed={target_speed}) in {region}", file=sys.stderr)
    if verbose:
        print(f"[ensure_pipeline] Preferred name to match: {name_to_match}", file=sys.stderr)

    client = create_client(region)
    pipelines = search_pipelines(client, verbose=verbose)

    if verbose:
        print(f"[ensure_pipeline] Total pipelines found: {len(pipelines)}", file=sys.stderr)
        for p in pipelines:
            print(f"  - Id={p.get('Id')}, Name={p.get('Name')}, State={p.get('State')}, Speed={p.get('Speed')}", file=sys.stderr)

    # Filter pipelines by Speed and State
    matching_pipelines = []
    for p in pipelines:
        # Check state first - must be Active
        if p.get("State") != "Active":
            if verbose:
                print(f"[ensure_pipeline] Skipping pipeline {p.get('Name')} - not Active (State={p.get('State')})", file=sys.stderr)
            continue

        # Check Speed field - handle legacy pipelines without Speed
        pipeline_speed = p.get("Speed")
        if pipeline_speed is None:
            # Legacy pipeline without Speed field, skip for type-specific matching
            if verbose:
                print(f"[ensure_pipeline] Skipping pipeline {p.get('Name')} - no Speed field", file=sys.stderr)
            continue

        if pipeline_speed == target_speed:
            matching_pipelines.append(p)

    print(f"[ensure_pipeline] Found {len(matching_pipelines)} active {pipeline_type} pipeline(s)", file=sys.stderr)

    # Select pipeline: preferred name first, then any match
    selected = None
    if matching_pipelines:
        # Priority 1: Name matches preferred_name (or common names like "mts-service-pipeline")
        preferred_names = [name_to_match]
        if preferred_name != "mts-service-pipeline":
            # Also consider "mts-service-pipeline" as a fallback preferred name
            preferred_names.append("mts-service-pipeline")
        
        for preferred in preferred_names:
            for p in matching_pipelines:
                if p.get("Name") == preferred:
                    selected = p
                    if verbose:
                        print(f"[ensure_pipeline] Matched preferred name: {preferred}", file=sys.stderr)
                    break
            if selected:
                break

        # Priority 2: Any matching pipeline
        if selected is None:
            selected = matching_pipelines[0]
            if verbose:
                print(f"[ensure_pipeline] No preferred name match, using first available", file=sys.stderr)

    if selected:
        pipeline_id = selected.get("Id")
        pipeline_name = selected.get("Name", "N/A")
        print(f"[ensure_pipeline] Selected existing pipeline: {pipeline_id} (name={pipeline_name})", file=sys.stderr)
        return pipeline_id

    # No matching pipeline found, create new one
    print(f"[ensure_pipeline] No active {pipeline_type} pipeline found, creating new one...", file=sys.stderr)

    try:
        request = mts_models.AddPipelineRequest(
            name=name_to_match,
            speed=target_speed,
        )

        print(f"Creating new {pipeline_type} pipeline: {name_to_match} (Speed={target_speed})", file=sys.stderr)

        response = _call_with_retry(client.add_pipeline, request)
        result = response.body.to_map() if hasattr(response.body, 'to_map') else json.loads(response.body.to_json())

        # Extract pipeline ID from response
        pipeline_id = (
            result.get("Pipeline", {})
            .get("Id")
        )

        if not pipeline_id:
            raise RuntimeError(f"Failed to get pipeline ID from create response: {result}")

        print(f"Pipeline created: {pipeline_id}", file=sys.stderr)
        return pipeline_id

    except Exception as e:
        raise RuntimeError(f"Failed to create {pipeline_type} pipeline: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Alibaba Cloud MPS Pipeline Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all pipelines
  python3 mps_pipeline.py

  # Auto-select and output PipelineId only (for shell scripts)
  python3 mps_pipeline.py --select
  PIPELINE_ID=$(python3 mps_pipeline.py --select)

  # Specify preferred pipeline name
  python3 mps_pipeline.py --select --name my-custom-pipeline

  # List pipelines by type
  python3 mps_pipeline.py --type audit        # List audit pipelines
  python3 mps_pipeline.py --type smarttag     # List smarttag pipelines
  python3 mps_pipeline.py --type standard     # List standard pipelines

  # Auto-select by type (with auto-creation if not exists)
  python3 mps_pipeline.py --type audit --select
  python3 mps_pipeline.py --type smarttag --select

  # JSON output format
  python3 mps_pipeline.py --json

  # JSON output with selection
  python3 mps_pipeline.py --select --json
        """,
    )

    parser.add_argument(
        "--region",
        type=str,
        default=os.environ.get("ALIBABA_CLOUD_REGION", "cn-shanghai"),
        help="Service region (default from ALIBABA_CLOUD_REGION env var or cn-shanghai)",
    )
    parser.add_argument(
        "--select",
        action="store_true",
        help="Auto-select mode: output only the selected PipelineId",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="mts-service-pipeline",
        help="Preferred pipeline name for auto-selection (default: mts-service-pipeline)",
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["standard", "narrowband", "audit", "smarttag"],
        dest="pipeline_type",
        help="Filter/select pipelines by type (standard/narrowband/audit/smarttag)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Ensure environment variables are loaded
    if not ensure_env_loaded(verbose=args.verbose):
        from load_env import _print_setup_hint

        _print_setup_hint([])
        sys.exit(1)

    try:
        # If pipeline_type is specified, use ensure_pipeline for type-aware selection/creation
        if args.pipeline_type:
            pipeline_id = ensure_pipeline(
                region=args.region,
                pipeline_type=args.pipeline_type,
                preferred_name=args.name if args.name != "mts-service-pipeline" else None,
            )

            if args.json:
                output = {
                    "pipeline_id": pipeline_id,
                    "type": args.pipeline_type,
                    "region": args.region,
                }
                print(json.dumps(output, indent=2))
            else:
                print(pipeline_id)
            return

        # Standard mode - list or select from all pipelines
        client = create_client(args.region)
        pipelines = search_pipelines(client)

        if args.select:
            # Auto-select mode
            selected = select_pipeline(pipelines, args.name)

            if selected is None:
                print(
                    f"Error: No Active pipeline found in region {args.region}",
                    file=sys.stderr,
                )
                if pipelines:
                    print("\nAvailable pipelines:", file=sys.stderr)
                    print(format_pipeline_table(pipelines), file=sys.stderr)
                sys.exit(1)

            if args.json:
                # JSON output with selected pipeline details
                output = {
                    "pipeline_id": selected.get("Id"),
                    "name": selected.get("Name"),
                    "state": selected.get("State"),
                    "speed": selected.get("Speed"),
                    "speed_level": selected.get("SpeedLevel"),
                }
                print(json.dumps(output, indent=2))
            else:
                # Plain text output: just the PipelineId
                print(selected.get("Id"))
        else:
            # List mode
            if args.json:
                # Full JSON output of all pipelines
                output = {
                    "region": args.region,
                    "count": len(pipelines),
                    "pipelines": pipelines,
                }
                # Also include selected pipeline info
                selected = select_pipeline(pipelines, args.name)
                if selected:
                    output["selected"] = {
                        "pipeline_id": selected.get("Id"),
                        "name": selected.get("Name"),
                        "state": selected.get("State"),
                        "speed": selected.get("Speed"),
                    }
                print(json.dumps(output, indent=2))
            else:
                # Table format
                print(f"\nAlibaba Cloud MPS Pipelines (Region: {args.region})")
                print("=" * 80)
                print(format_pipeline_table(pipelines))

                # Show selection info
                selected = select_pipeline(pipelines, args.name)
                if selected:
                    print("\n" + "-" * 80)
                    print(
                        f"Selected Pipeline: {selected.get('Id')} "
                        f"(name={selected.get('Name')}, state={selected.get('State')})"
                    )
                else:
                    print("\n" + "-" * 80)
                    print("Warning: No Active pipeline found for auto-selection.")
                print("=" * 80)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
