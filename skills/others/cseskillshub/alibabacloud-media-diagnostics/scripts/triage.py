#!/usr/bin/env python3
#
# SECURITY:
#   - This script is part of a READ-ONLY media diagnostics toolkit.
#   - It only inspects the single file/URL explicitly provided by the
#     user as an argument and never modifies it.
#   - No cloud credentials, API keys or tokens are required or used.
#
# Exit codes:
#   0: triage completed and JSON result printed to stdout
#   1: missing input argument, or the input could not be probed
#      (category "unreachable"): the JSON result is still printed on
#      stdout and a [WARN] line explaining the failure goes to stderr
#   127: required external tool (ffprobe) missing; a degraded JSON
#      result (category "degraded") with the plain-language fields
#      (summary / recommended_actions / severity_human) is still printed
#      on stdout and a [WARN] line goes to stderr
"""
Media triage script (triage.py)
Quickly probes the input source and outputs a problem classification
and recommended actions within seconds.
Serves as the unified entry point of the alibabacloud-media-diagnostics skill.

Routing rules come from lib/registry.py; registering a new module in the
registry is enough for it to be dispatched automatically.
"""

import os
import sys

# Allow running directly from the project directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.format import detect_input_type, quick_moov_check, is_url
from lib.cmd import ffprobe_quick
from lib.registry import ROUTES
from lib.report import attach_report, emit_json, render_report


def classify(input_path, probe_data, input_type):
    """
    Classify the problem based on probe data
    Returns: {category, symptoms, actions, confidence}
    """
    symptoms = []
    actions = []
    category = "general"
    confidence = "high"

    if not probe_data:
        return {
            "category": "unreachable",
            "symptoms": ["input_unreadable"],
            "actions": ["check_url_accessibility", "verify_file_path"],
            "confidence": "high"
        }

    fmt = probe_data.get("format", {})
    streams = probe_data.get("streams", [])
    format_name = fmt.get("format_name", "")
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    # === Extract key metrics ===
    v_codec = video_streams[0].get("codec_name", "").lower() if video_streams else ""
    v_profile = video_streams[0].get("profile", "").lower() if video_streams else ""
    v_pix_fmt = video_streams[0].get("pix_fmt", "") if video_streams else ""
    has_b_frames = int(video_streams[0].get("has_b_frames", 0)) if video_streams else 0

    a_codec = audio_streams[0].get("codec_name", "").lower() if audio_streams else ""
    a_profile = audio_streams[0].get("profile", "").lower() if audio_streams else ""

    r_frame_rate = video_streams[0].get("r_frame_rate", "0/1") if video_streams else "0/1"
    avg_frame_rate = video_streams[0].get("avg_frame_rate", "0/1") if video_streams else "0/1"

    # === Extra matching for live streams ===
    is_live = input_type == "live_protocol"
    is_flv_live = "flv" in format_name and (input_type in ("http_url", "flv_file"))

    # === Classify according to the registry routes ===
    matched_route = None

    if is_live or is_flv_live:
        matched_route = ROUTES.get("live_stream")
        category = "live_stream"
    elif input_type == "hls":
        matched_route = ROUTES.get("hls_stream")
        category = "hls_stream"
    elif input_type == "ts_file":
        matched_route = ROUTES.get("ts_segment")
        category = "ts_segment"
    elif input_type in ("mp4_file", "local_file", "http_url"):
        matched_route = ROUTES.get("vod_file")
        category = "vod_file"

    if matched_route:
        actions = [s["name"] for s in matched_route.get("scripts", [])]

    # === Symptom detection ===
    if category == "live_stream":
        if has_b_frames > 0:
            symptoms.append("b_frame_present")
        if is_flv_live and a_codec != "aac":
            symptoms.append("audio_non_aac_in_rtmp")
        if a_codec == "aac" and ("he" in a_profile or "hev2" in a_profile):
            symptoms.append("aac_he_profile")
        if not symptoms:
            symptoms.append("live_general_check")

    elif category == "hls_stream":
        symptoms.append("hls_analysis")
        if has_b_frames > 0:
            symptoms.append("b_frame_present")

    elif category == "ts_segment":
        symptoms.append("ts_integrity_check")

    elif category == "vod_file":
        # moov position (local files only)
        if input_type in ("mp4_file", "local_file") and os.path.isfile(input_path):
            moov_status = quick_moov_check(input_path)
            if moov_status == "moov_at_end":
                symptoms.append("moov_not_faststart")

        # HEVC compatibility
        if v_codec in ("hevc", "h265"):
            symptoms.append("hevc_codec")

        # 10-bit
        if "10" in v_pix_fmt:
            symptoms.append("10bit_pixel_format")

        # VFR
        try:
            r_num, r_den = map(int, r_frame_rate.split("/"))
            avg_num, avg_den = map(int, avg_frame_rate.split("/"))
            r_fps = r_num / r_den if r_den else 0
            avg_fps = avg_num / avg_den if avg_den else 0
            if r_fps > 0 and avg_fps > 0 and abs(r_fps - avg_fps) / r_fps > 0.1:
                symptoms.append("variable_frame_rate")
        except (ValueError, ZeroDivisionError):
            pass

        # AAC-HE
        if "he" in a_profile or "hev2" in a_profile:
            symptoms.append("aac_he_profile")

        # B-frames (warn when >4 in VOD scenarios)
        if has_b_frames > 4:
            symptoms.append("excessive_b_frames")

        if not symptoms:
            symptoms.append("full_scan")
            confidence = "medium"
    else:
        category = "general"
        actions = ["media_analyze.py"]
        symptoms.append("unknown_format")
        confidence = "low"

    # Deduplicate
    actions = list(dict.fromkeys(actions))

    return {
        "category": category,
        "symptoms": symptoms,
        "actions": actions,
        "confidence": confidence
    }


def main():
    if len(sys.argv) < 2:
        print("[WARN] missing input argument: usage is triage.py <input_file_or_url>",
              file=sys.stderr)
        output = {
            "error": "Usage: triage.py <input_file_or_url>",
            "category": "error",
            "symptoms": [],
            "actions": [],
            "confidence": "none"
        }
        summary = ("The diagnosis needs a file or URL to check, but none was "
                   "provided, so nothing was analyzed. Provide the media "
                   "file path or URL and run the check again.")
        actions = ["Provide the media file path or URL you want to diagnose",
                   "Re-run: triage.py <input_file_or_url>"]
        attach_report(output, summary, "minor", actions)
        emit_json(output)
        render_report(summary, [], ["no input file or URL was provided"], actions)
        sys.exit(1)

    input_path = sys.argv[1]

    # 1. Detect input type
    input_type = detect_input_type(input_path)

    # 2. Quick ffprobe probe
    probe_data = ffprobe_quick(input_path)

    # 3. Classify
    result = classify(input_path, probe_data, input_type)

    # 4. Assemble output
    output = {
        "input": input_path,
        "input_type": input_type,
        "category": result["category"],
        "symptoms": result["symptoms"],
        "actions": result["actions"],
        "confidence": result["confidence"],
        "probe_summary": {}
    }

    # Attach probe summary
    if probe_data:
        fmt = probe_data.get("format", {})
        streams = probe_data.get("streams", [])
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

        output["probe_summary"] = {
            "format": fmt.get("format_name", "unknown"),
            "duration": float(fmt.get("duration", 0) or 0),
            "bit_rate": int(fmt.get("bit_rate", 0) or 0),
            "video_codec": video_streams[0].get("codec_name") if video_streams else None,
            "video_profile": video_streams[0].get("profile") if video_streams else None,
            "resolution": f"{video_streams[0].get('width')}x{video_streams[0].get('height')}" if video_streams else None,
            "has_b_frames": int(video_streams[0].get("has_b_frames", 0)) if video_streams else 0,
            "audio_codec": audio_streams[0].get("codec_name") if audio_streams else None,
            "audio_profile": audio_streams[0].get("profile") if audio_streams else None,
            "sample_rate": audio_streams[0].get("sample_rate") if audio_streams else None,
        }

    # Error path: input missing / probe failed. The JSON result is the
    # machine-readable contract; the [WARN] line documents the reason and
    # the non-zero exit code signals the failure to the caller.
    if output["category"] == "unreachable":
        print(f"[WARN] input could not be probed (missing file or "
              f"unreachable URL): {input_path}", file=sys.stderr)
        summary = ("This file or URL cannot be read right now. That usually "
                   "means the path is wrong, the file does not exist, the "
                   "URL signature has expired, or the network cannot reach "
                   "the server. Nothing is wrong with the diagnosis itself; "
                   "the target just needs to be made accessible before any "
                   "media checks can run.")
        if is_url(input_path):
            actions = [
                "Open the URL in a browser or with 'curl -I' to confirm it is reachable",
                "Check whether the URL signature or token has expired and get a fresh URL",
                "Re-run the diagnosis once the URL is accessible"
            ]
        else:
            actions = [
                "Confirm the file path is spelled correctly and the file exists",
                "Re-run the diagnosis once the file is accessible"
            ]
        attach_report(output, summary, "prompt_attention", actions)
        emit_json(output)
        render_report(summary, [f"quick probe of the input: {input_path}"],
                      ["the input could not be probed (missing file or "
                       "unreachable URL)"], actions)
        sys.exit(1)

    # Success path: build the plain-language layer from the probe summary
    probe = output.get("probe_summary") or {}
    parts = []
    if probe.get("format"):
        parts.append(f"container {probe['format']}")
    if probe.get("video_codec"):
        parts.append(f"video codec {probe['video_codec']}")
    if probe.get("audio_codec"):
        parts.append(f"audio codec {probe['audio_codec']}")
    if probe.get("duration"):
        parts.append(f"duration {probe['duration']:.1f}s")
    basic = ", ".join(parts) if parts else "basic media information"

    symptom_notes = {
        "moov_not_faststart": ("the file's index metadata sits at the end of "
                               "the file, which makes online playback start "
                               "slowly and breaks progress-bar seeking"),
        "hevc_codec": ("the video uses the H.265/HEVC codec, which many "
                       "browsers cannot play"),
        "10bit_pixel_format": ("the video uses 10-bit color, which some "
                               "devices decode slowly"),
        "variable_frame_rate": "the frame rate varies during the video, which can cause sync issues",
        "aac_he_profile": "the audio uses an HE-AAC profile with weaker device compatibility",
        "excessive_b_frames": "the video carries many B-frames, which adds decoding delay",
        "b_frame_present": "B-frames are present, which add latency for live playback",
        "audio_non_aac_in_rtmp": "the live audio codec is not AAC, which RTMP requires",
    }
    notable = [symptom_notes[s] for s in output["symptoms"] if s in symptom_notes]

    if notable:
        severity_key = "needs_attention"
        summary = (f"The media is readable and the triage found signs of "
                   f"real problems: {'; '.join(notable)}. This is what most "
                   f"likely causes the symptoms you see. A deep analysis "
                   f"script has been selected to confirm the details and "
                   f"suggest fixes.")
    else:
        severity_key = "minor"
        summary = (f"The media is readable and the quick probe looks healthy "
                   f"({basic}). No obvious problem stood out at triage "
                   f"level. A deep analysis script has been selected to "
                   f"confirm there are no hidden issues.")

    actions = []
    if output["actions"]:
        actions.append("Run the deep-analysis script(s) listed in 'actions' on the same input")
    if "moov_not_faststart" in output["symptoms"]:
        actions.append("Expect a fix suggestion to re-mux the file with the 'faststart' flag")
    if "hevc_codec" in output["symptoms"]:
        actions.append("If browser playback matters, expect a suggestion to transcode to H.264")
    if not actions:
        actions = ["No action required"]

    attach_report(output, summary, severity_key, actions)
    emit_json(output)
    render_report(summary,
                  [f"quick probe of the input: {input_path}", basic],
                  [f"classified as '{output['category']}' "
                   f"(symptoms: {', '.join(output['symptoms']) or 'none'})"],
                  actions)


if __name__ == "__main__":
    main()
