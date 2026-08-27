"""
Shared library for alibabacloud-media-diagnostics

Modules:
  - cmd: command execution and ffprobe/mediainfo probing
  - format: formatting helpers and MP4 box parsing
  - checker: TS/DTS/bitrate check functions
  - registry: route registry (pluggable extension point)
"""

from .cmd import run_cmd, ffprobe_json, ffprobe_quick, mediainfo_json
from .format import (
    format_size, format_duration,
    is_url, is_hls, is_ts_file,
    detect_input_type, quick_moov_check, detect_moov_position, parse_mp4_boxes
)
from .checker import (
    check_ts_continuity, check_dts_monotonic,
    analyze_bitrate_distribution, estimate_gop
)
from .registry import ROUTES, SYMPTOM_ROUTES, get_route, get_all_categories, get_scripts_for_category
