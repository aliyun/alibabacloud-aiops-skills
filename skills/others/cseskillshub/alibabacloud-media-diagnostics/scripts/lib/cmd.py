#!/usr/bin/env python3
#
# SECURITY:
#   - This module is part of a READ-ONLY media diagnostics toolkit.
#   - It only inspects files/URLs explicitly provided by the user and
#     never modifies them.
#   - No cloud credentials, API keys or tokens are required or used.
#   - External commands (ffprobe/mediainfo) are invoked strictly for
#     read-only media probing.
"""
Shared command execution module
Provides ffprobe/mediainfo probing and generic command execution primitives
"""

import json
import subprocess
import sys


def _exit_missing_tool(tool, hint):
    """Emit a stable English warning to stderr, a machine-readable JSON
    result on stdout and a plain-language report block, then exit 127
    when a required external executable is not available."""
    from .report import attach_report, emit_json, render_report

    print(f"[WARN] Required external tool '{tool}' is not installed or not "
          f"found in PATH. {hint}", file=sys.stderr)
    results = {
        "error": f"required external tool '{tool}' is not installed",
        "category": "degraded"
    }
    summary = (f"This run could only complete a degraded check because the "
               f"'{tool}' tool is missing from this environment. Without "
               f"ffprobe, deep analysis of container, codecs and frame "
               f"structure (moov position, codec compatibility, B-frame/GOP "
               f"layout, DTS order, bitrate) cannot be performed - only "
               f"basic structural checks remain, so the conclusion may be "
               f"incomplete. We strongly recommend that you or your "
               f"environment administrator install FFmpeg on this machine "
               f"(which also provides ffprobe), for example from the "
               f"official channel ffmpeg.org or your system package "
               f"manager, and then re-run the same diagnosis to get the "
               f"full analysis.")
    actions = ["Strongly recommended: you or your environment administrator "
               "install FFmpeg on this machine (it also provides ffprobe), "
               "for example from the official channel ffmpeg.org or your "
               "system package manager",
               "After the installation is complete, re-run the same "
               "diagnosis to get the full deep analysis",
               "Until then, refer to the degraded conclusion above as a "
               "limited structural check"]
    attach_report(results, summary, "needs_attention", actions)
    emit_json(results)
    render_report(summary, [f"availability of the '{tool}' tool"],
                  [f"'{tool}' is not installed or not found in PATH"],
                  actions)
    sys.exit(127)


# Remote probe limits: when ffprobe opens a URL (HTTP/HLS/live protocol)
# it may sequentially pull large amounts of data (e.g. every segment of an
# m3u8 stream). Cap probesize/analyzeduration for remote inputs so probing
# stays bounded; local files keep ffprobe defaults for full analysis quality.
REMOTE_PROBE_SIZE = "5000000"       # bytes
REMOTE_ANALYZE_DURATION = "5000000"  # microseconds


def _remote_probe_args(input_path):
    """Return ffprobe limiting options for remote inputs, [] for local files."""
    if "://" in input_path:
        return ["-probesize", REMOTE_PROBE_SIZE,
                "-analyzeduration", REMOTE_ANALYZE_DURATION]
    return []


def run_cmd(cmd, timeout=60):
    """Run a command and return (stdout, returncode).

    Special return codes:
      -1: command timed out
      -2: executable not found
    """
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout, result.returncode
    except subprocess.TimeoutExpired:
        return "", -1
    except FileNotFoundError:
        return "", -2


def ffprobe_json(input_path, show_chapters=False, timeout=60):
    """
    Fetch full media information via ffprobe (JSON).
    Returns: dict or None
    """
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
    ]
    if show_chapters:
        cmd.append("-show_chapters")
    cmd.extend(_remote_probe_args(input_path))
    cmd.append(input_path)

    stdout, rc = run_cmd(cmd, timeout=timeout)
    if rc == -2:
        _exit_missing_tool("ffprobe", "Deep analysis is unavailable without it; the degraded report below explains the impact and strongly recommends installing FFmpeg.")
    if rc != 0:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def ffprobe_quick(input_path, timeout=8):
    """
    Quick ffprobe probe (basic format + streams info only)
    Used during the triage stage, expected to return within seconds
    """
    return ffprobe_json(input_path, show_chapters=False, timeout=timeout)


def mediainfo_json(input_path, timeout=60):
    """Fetch mediainfo information (optional tool), returns dict or None.

    mediainfo is an optional enrichment tool; when its executable is
    missing we degrade gracefully: a [WARN] message is written to stderr
    and None is returned so callers can report mediainfo_available=false.
    """
    cmd = ["mediainfo", "--Output=JSON", input_path]
    stdout, rc = run_cmd(cmd, timeout=timeout)
    if rc == -2:
        print("[WARN] Optional external tool 'mediainfo' is not installed or "
              "not found in PATH; skipping mediainfo enrichment.", file=sys.stderr)
        return None
    if rc != 0:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def ffprobe_frames(input_path, entries="frame=pict_type,pts_time",
                   select_streams="v:0", read_intervals=None, timeout=30):
    """
    Fetch frame-level information
    entries: ffprobe -show_entries argument
    select_streams: stream selector
    read_intervals: read interval, e.g. %+5 means the first 5 seconds
    """
    cmd = [
        "ffprobe", "-v", "quiet",
        "-select_streams", select_streams,
        "-show_entries", entries,
        "-of", "json",
    ]
    if read_intervals:
        cmd.extend(["-read_intervals", read_intervals])
    cmd.extend(_remote_probe_args(input_path))
    cmd.append(input_path)

    stdout, rc = run_cmd(cmd, timeout=timeout)
    if rc == -2:
        _exit_missing_tool("ffprobe", "Deep analysis is unavailable without it; the degraded report below explains the impact and strongly recommends installing FFmpeg.")
    if rc != 0:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def ffprobe_packets(input_path, entries="packet=dts_time,size",
                    select_streams="v:0", timeout=30):
    """Fetch packet-level information"""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-select_streams", select_streams,
        "-show_entries", entries,
        "-print_format", "json",
    ]
    cmd.extend(_remote_probe_args(input_path))
    cmd.append(input_path)
    stdout, rc = run_cmd(cmd, timeout=timeout)
    if rc == -2:
        _exit_missing_tool("ffprobe", "Deep analysis is unavailable without it; the degraded report below explains the impact and strongly recommends installing FFmpeg.")
    if rc != 0:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None
