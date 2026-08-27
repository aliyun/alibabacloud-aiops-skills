#!/usr/bin/env python3
#
# SECURITY:
#   - This module is part of a READ-ONLY media diagnostics toolkit.
#   - It only declares routing metadata; all diagnostic scripts it
#     references inspect files/URLs explicitly provided by the user.
#   - No cloud credentials, API keys or tokens are required or used.
"""
Route registry module
New modules register routing rules via the ROUTES dict; triage.py
automatically dispatches based on the registered information.

How to extend:
  1. Create a new script under scripts/ (e.g. cdn_diagnose.py)
  2. Register the corresponding routing rule in ROUTES below
  3. triage.py will automatically pick up the registration and dispatch

ROUTES structure:
  category: triage category name
  match_input_types: list of input types to match
  match_symptoms: list of symptoms that may trigger this route (used for SKILL.md documentation)
  scripts: scripts to execute, with their arguments
  description: route description
"""

# ============================================================
# Route registry - add routing rules for new modules here
# ============================================================

ROUTES = {
    "vod_file": {
        "description": "VOD file diagnostics (MP4/MOV/local file/HTTP URL)",
        "match_input_types": ["mp4_file", "local_file", "http_url"],
        "match_symptoms": [
            "moov_not_faststart", "hevc_codec", "10bit_pixel_format",
            "variable_frame_rate", "aac_he_profile", "excessive_b_frames",
            "full_scan"
        ],
        "scripts": [
            {"name": "media_analyze.py", "args": ["$INPUT"]},
        ],
    },
    "live_stream": {
        "description": "Live stream diagnostics (RTMP/RTSP/SRT/FLV)",
        "match_input_types": ["live_protocol"],
        "extra_match": "is_flv_live",  # Extra match condition: FLV container + http/flv_file
        "match_symptoms": [
            "b_frame_present", "audio_non_aac_in_rtmp",
            "aac_he_profile", "live_general_check"
        ],
        "scripts": [
            {"name": "media_analyze.py", "args": ["$INPUT", "--live"]},
        ],
    },
    "hls_stream": {
        "description": "HLS stream diagnostics (m3u8)",
        "match_input_types": ["hls"],
        "match_symptoms": ["hls_analysis", "b_frame_present"],
        # hls_check.py alone fully covers playlist-level diagnosis
        # (structure, reachability, duration consistency, TS integrity).
        # media_analyze.py is intentionally NOT routed here: ffprobe would
        # sequentially download every segment of the m3u8 stream, which is
        # extremely slow for long VOD playlists and unnecessary.
        "scripts": [
            {"name": "hls_check.py", "args": ["$INPUT"]},
        ],
    },
    "ts_segment": {
        "description": "TS segment diagnostics",
        "match_input_types": ["ts_file"],
        "match_symptoms": ["ts_integrity_check"],
        "scripts": [
            {"name": "media_analyze.py", "args": ["$INPUT"]},
        ],
    },
    # ── Add future extension modules here ──
    # "cdn_diagnose": {
    #     "description": "CDN delivery diagnostics",
    #     "match_input_types": ["http_url"],
    #     "match_symptoms": ["cdn_latency", "cdn_cache_miss"],
    #     "scripts": [
    #         {"name": "cdn_diagnose.py", "args": ["$INPUT"]},
    #     ],
    # },
}

# ============================================================
# Symptom routing table - used when the user only describes symptoms
# ============================================================

SYMPTOM_ROUTES = {
    "playback stuttering/buffering/slow loading":   {"category": "vod_file",    "symptoms": ["moov_not_faststart", "bitrate_spike"]},
    "seek/scrub failure":                           {"category": "vod_file",    "symptoms": ["moov_not_faststart", "flv_no_keyframe"]},
    "browser cannot play/unsupported format":       {"category": "vod_file",    "symptoms": ["hevc_codec", "10bit"]},
    "glitching/mosaic/green screen":                {"category": "ts_segment",  "symptoms": ["ts_continuity_error"]},
    "audio-video out of sync":                      {"category": "vod_file",    "symptoms": ["vfr", "av_duration_mismatch"]},
    "high live latency/slow first frame":           {"category": "live_stream", "symptoms": ["b_frame", "large_gop"]},
    "stream push failure/audio errors":             {"category": "live_stream", "symptoms": ["audio_non_aac"]},
    "repeated frames/repeated segments":            {"category": "vod_file",    "symptoms": ["cdn_reconnect_replay"]},
    "HLS playback interruption":                    {"category": "hls_stream",  "symptoms": ["ts_integrity", "segment_unreachable"]},
    # ── Future extensions ──
    # "high CDN latency/stuttering":                {"category": "cdn_diagnose", "symptoms": ["cdn_latency"]},
}


def get_route(category):
    """Get the routing information for the given category"""
    return ROUTES.get(category)


def get_all_categories():
    """Get all registered category names"""
    return list(ROUTES.keys())


def get_scripts_for_category(category):
    """Get the list of scripts to execute for the given category"""
    route = ROUTES.get(category)
    if route:
        return route["scripts"]
    return []
