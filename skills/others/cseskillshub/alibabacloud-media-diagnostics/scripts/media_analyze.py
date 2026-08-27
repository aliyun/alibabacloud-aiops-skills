#!/usr/bin/env python3
#
# SECURITY:
#   - This script is part of a READ-ONLY media diagnostics toolkit.
#   - It only inspects the single file/URL explicitly provided by the
#     user as an argument and never modifies it.
#   - No cloud credentials, API keys or tokens are required or used.
#
# Exit codes:
#   0: analysis completed and JSON result printed to stdout
#   1: missing input argument, or ffprobe failed to parse the input
#      (JSON result still printed on stdout, [WARN] written to stderr)
#   127: required external tool (ffprobe) missing; a degraded JSON
#      result (category "degraded") with the plain-language fields
#      (summary / recommended_actions / severity_human) is still printed
#      on stdout and a [WARN] line goes to stderr
"""
Media file diagnostic analysis script
Detects common playback issues: moov position, codec compatibility,
container format, bitrate/framerate anomalies, etc.
Refactored version: uses the shared modules under lib/
"""

import os
import sys
from datetime import datetime

# Allow running directly from the project directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.format import (
    is_url, is_hls, is_ts_file, format_size,
    detect_moov_position
)
from lib.cmd import ffprobe_json, mediainfo_json
from lib.checker import (
    check_ts_continuity, check_dts_monotonic,
    analyze_bitrate_distribution, estimate_gop
)
from lib.report import attach_report, emit_json, gloss, render_report


def analyze_streams(probe_data):
    """Analyze stream info; detect codec compatibility and bitrate/framerate issues"""
    issues = []
    warnings = []
    info = {}

    if not probe_data:
        return {"issues": issues, "warnings": warnings, "info": info}

    streams = probe_data.get("streams", [])
    fmt = probe_data.get("format", {})

    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    # Basic info
    info["format_name"] = fmt.get("format_name", "unknown")
    info["duration"] = float(fmt.get("duration", 0))
    info["size"] = int(fmt.get("size", 0))
    info["bit_rate"] = int(fmt.get("bit_rate", 0))

    # === Video stream analysis ===
    for vs in video_streams:
        codec = vs.get("codec_name", "").lower()
        profile = vs.get("profile", "").lower()
        width = vs.get("width", 0)
        height = vs.get("height", 0)
        pix_fmt = vs.get("pix_fmt", "")

        info["video_codec"] = vs.get("codec_name", "unknown")
        info["resolution"] = f"{width}x{height}"
        info["profile"] = vs.get("profile", "unknown")
        info["pix_fmt"] = pix_fmt

        # H.265/HEVC compatibility
        if codec in ("hevc", "h265"):
            issues.append({
                "type": "codec_compat",
                "severity": "high",
                "title": "H.265/HEVC codec in use",
                "detail": "H.265 has poor compatibility in web browsers (Chrome/Firefox); only Safari/iOS support it natively",
                "fix": "Transcode to H.264: ffmpeg -i input -c:v libx264 -preset medium -crf 23 output.mp4"
            })

        # 10-bit color depth
        if "10" in pix_fmt or "10le" in pix_fmt or "10be" in pix_fmt:
            warnings.append({
                "type": "codec_compat",
                "severity": "medium",
                "title": f"10-bit color depth ({pix_fmt})",
                "detail": "10-bit video cannot be hardware-decoded on some mobile devices, which may cause playback stuttering",
                "fix": "Transcode to 8-bit: ffmpeg -i input -c:v libx264 -pix_fmt yuv420p output.mp4"
            })

        # B-frame detection
        has_b_frames = int(vs.get("has_b_frames", 0))
        if has_b_frames > 4:
            warnings.append({
                "type": "codec_config",
                "severity": "low",
                "title": f"High B-frame count ({has_b_frames})",
                "detail": "Too many B-frames increase decoding latency and are unsuitable for realtime/low-latency scenarios",
                "fix": "Limit B-frames: ffmpeg -i input -c:v libx264 -bf 2 output.mp4"
            })

        # Frame rate analysis
        r_frame_rate = vs.get("r_frame_rate", "0/1")
        avg_frame_rate = vs.get("avg_frame_rate", "0/1")
        try:
            r_num, r_den = map(int, r_frame_rate.split("/"))
            avg_num, avg_den = map(int, avg_frame_rate.split("/"))
            r_fps = r_num / r_den if r_den else 0
            avg_fps = avg_num / avg_den if avg_den else 0
            info["fps"] = round(avg_fps, 2)

            if r_fps > 0 and avg_fps > 0 and abs(r_fps - avg_fps) / r_fps > 0.1:
                warnings.append({
                    "type": "framerate",
                    "severity": "medium",
                    "title": f"Variable frame rate (VFR): r_frame_rate={r_fps:.2f}, avg={avg_fps:.2f}",
                    "detail": "Variable frame rate may cause audio-video desynchronization; some players handle it poorly",
                    "fix": "Force constant frame rate: ffmpeg -i input -c:v libx264 -r 30 -vsync cfr output.mp4"
                })
        except (ValueError, ZeroDivisionError):
            pass

    # === Audio stream analysis ===
    for audio_s in audio_streams:
        acodec = audio_s.get("codec_name", "").lower()
        aprofile = audio_s.get("profile", "").lower()
        sample_rate = audio_s.get("sample_rate", "0")

        info["audio_codec"] = audio_s.get("codec_name", "unknown")
        info["sample_rate"] = sample_rate

        # AAC-HE/HEv2
        if "he" in aprofile or "hev2" in aprofile:
            warnings.append({
                "type": "codec_compat",
                "severity": "medium",
                "title": f"AAC {aprofile} Profile",
                "detail": "HE-AAC/HEv2 have poor decoding compatibility on some older devices",
                "fix": "Transcode to AAC-LC: ffmpeg -i input -c:a aac -profile:a aac_low output.mp4"
            })

    # === Audio/video duration alignment ===
    if video_streams and audio_streams:
        v_duration = float(video_streams[0].get("duration", 0) or 0)
        a_duration = float(audio_streams[0].get("duration", 0) or 0)
        if v_duration > 0 and a_duration > 0:
            diff = abs(v_duration - a_duration)
            if diff > 0.5:
                issues.append({
                    "type": "av_sync",
                    "severity": "high",
                    "title": f"Audio/video duration mismatch (diff {diff:.2f}s)",
                    "detail": f"Video duration {v_duration:.2f}s, audio duration {a_duration:.2f}s, difference exceeds 0.5s",
                    "fix": "Align by trimming: ffmpeg -i input -c copy -shortest output.mp4"
                })

    # === Container format detection ===
    format_name = fmt.get("format_name", "")
    if "flv" in format_name:
        tags = fmt.get("tags", {})
        if not tags.get("hasKeyframes") and not tags.get("keyframes"):
            issues.append({
                "type": "container",
                "severity": "high",
                "title": "FLV missing keyframe index",
                "detail": "Timeline seeking is not possible",
                "fix": "Rebuild index: ffmpeg -i input.flv -c copy -flvflags add_keyframe_index output.flv"
            })

    # === Rough bitrate spike detection ===
    if info.get("bit_rate") and info.get("duration"):
        expected_size = info["bit_rate"] * info["duration"] / 8
        actual_size = info["size"]
        if actual_size > 0 and expected_size > 0:
            ratio = actual_size / expected_size
            if ratio > 3.0 or ratio < 0.3:
                warnings.append({
                    "type": "bitrate",
                    "severity": "medium",
                    "title": f"Actual size does not match average bitrate (ratio {ratio:.1f}x)",
                    "detail": "Bitrate spike intervals may exist, causing buffering/stuttering",
                    "fix": "Inspect individual frames: ffprobe -show_frames -select_streams v input | grep pkt_size"
                })

    return {"issues": issues, "warnings": warnings, "info": info}


def analyze_live_stream(probe_data, input_path):
    """
    Dedicated live stream diagnostics
    Checks: B-frames (zero tolerance), audio codec compliance, combined latency factor analysis
    """
    issues = []
    warnings = []
    latency_factors = {
        "has_b_frames": False,
        "b_frame_count": 0,
        "gop_size": None,
        "keyframe_interval": None,
        "video_codec": None,
        "audio_codec": None,
        "audio_compliant": True,
        "estimated_encoder_latency_ms": 0,
        "factors": []
    }

    streams = probe_data.get("streams", [])
    fmt = probe_data.get("format", {})
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    # === B-frame detection (zero tolerance) ===
    for vs in video_streams:
        has_b_frames = int(vs.get("has_b_frames", 0))
        codec = vs.get("codec_name", "").lower()
        profile = vs.get("profile", "")
        latency_factors["video_codec"] = vs.get("codec_name", "unknown")
        latency_factors["b_frame_count"] = has_b_frames

        if has_b_frames > 0:
            latency_factors["has_b_frames"] = True
            r_frame_rate = vs.get("r_frame_rate", "30/1")
            try:
                num, den = map(int, r_frame_rate.split("/"))
                fps = num / den if den else 30
            except (ValueError, ZeroDivisionError):
                fps = 30
            frame_delay_ms = round(has_b_frames * (1000 / fps))
            latency_factors["estimated_encoder_latency_ms"] += frame_delay_ms
            latency_factors["factors"].append(
                f"B-frames add {has_b_frames} frames of delay (~{frame_delay_ms}ms @ {fps:.0f}fps)"
            )

            issues.append({
                "type": "live_bframe",
                "severity": "high",
                "title": f"Live stream contains B-frames (has_b_frames={has_b_frames})",
                "detail": f"Encoder: {codec}, Profile: {profile}. B-frames increase encode/decode latency by about {frame_delay_ms}ms, unsuitable for realtime live streaming",
                "fix": "Disable B-frames when pushing: ffmpeg -i input -c:v libx264 -preset veryfast -tune zerolatency -bf 0 -g 50 -f flv rtmp://..."
            })

    # GOP estimation
    gop_info = estimate_gop(input_path)
    if gop_info.get("keyframe_interval"):
        latency_factors["keyframe_interval"] = gop_info["keyframe_interval"]
        latency_factors["gop_size"] = gop_info["gop_size"]

    # === Audio codec compliance check ===
    format_name = fmt.get("format_name", "")
    is_flv_rtmp = "flv" in format_name or "live_flv" in format_name

    for audio_s in audio_streams:
        acodec = audio_s.get("codec_name", "").lower()
        aprofile = audio_s.get("profile", "").lower()
        sample_rate = int(audio_s.get("sample_rate", 0) or 0)
        channels = int(audio_s.get("channels", 0) or 0)

        latency_factors["audio_codec"] = audio_s.get("codec_name", "unknown")

        if is_flv_rtmp and acodec != "aac":
            latency_factors["audio_compliant"] = False
            issues.append({
                "type": "live_audio_codec",
                "severity": "high",
                "title": f"Live stream audio codec non-compliant: {acodec} (RTMP/FLV requires AAC)",
                "detail": f"Current audio codec: {acodec}, sample rate: {sample_rate}Hz, channels: {channels}. The RTMP/FLV protocol only supports AAC audio",
                "fix": "Transcode audio when pushing: ffmpeg -i input -c:v copy -c:a aac -ar 44100 -b:a 128k -f flv rtmp://..."
            })
        elif acodec == "aac":
            if "he" in aprofile or "hev2" in aprofile:
                warnings.append({
                    "type": "live_audio_profile",
                    "severity": "medium",
                    "title": f"Live stream uses AAC {aprofile}; AAC-LC is recommended",
                    "detail": "HE-AAC has higher decoding latency than AAC-LC and poorer compatibility in some players",
                    "fix": "Use AAC-LC: ffmpeg -i input -c:a aac -profile:a aac_low -b:a 128k -f flv rtmp://..."
                })
            if sample_rate not in (44100, 48000, 0):
                warnings.append({
                    "type": "live_audio_samplerate",
                    "severity": "low",
                    "title": f"Non-standard audio sample rate {sample_rate}Hz",
                    "detail": "44100Hz or 48000Hz is recommended for live streaming; some CDNs/players handle non-standard sample rates poorly",
                    "fix": "Resample: ffmpeg -i input -c:v copy -c:a aac -ar 44100 -f flv rtmp://..."
                })
        elif acodec not in ("aac", "mp3", "opus"):
            warnings.append({
                "type": "live_audio_codec",
                "severity": "medium",
                "title": f"Live stream audio codec: {acodec} (non-AAC)",
                "detail": "AAC-LC is the recommended audio codec for live streaming with the best compatibility",
                "fix": "Transcode to AAC: ffmpeg -i input -c:v copy -c:a aac -b:a 128k output"
            })

    # === Combined latency factor analysis ===
    if latency_factors.get("keyframe_interval") and latency_factors["keyframe_interval"] > 4:
        kf_interval = latency_factors["keyframe_interval"]
        latency_factors["factors"].append(
            f"Keyframe interval too large ({kf_interval:.1f}s), hurting startup speed and stream switching latency"
        )
        warnings.append({
            "type": "live_gop",
            "severity": "medium",
            "title": f"Keyframe interval too large ({kf_interval:.1f}s)",
            "detail": "A keyframe interval of 1-2s (GOP=fps*1~2) is recommended for live streaming; a larger interval causes long first-frame waits and slow stream/ABR switching",
            "fix": "Set GOP: ffmpeg -i input -c:v libx264 -g 50 -keyint_min 50 -f flv rtmp://... (assuming 25fps, 2s GOP)"
        })

    for vs in video_streams:
        profile = vs.get("profile", "").lower()
        if "baseline" in profile:
            latency_factors["factors"].append(
                "Baseline Profile (no CABAC/B-frames), suitable for low-latency scenarios"
            )

    return {"issues": issues, "warnings": warnings, "latency_factors": latency_factors}


def main():
    if len(sys.argv) < 2:
        print("[WARN] missing input argument: usage is "
              "media_analyze.py <input_file_or_url> [--live]", file=sys.stderr)
        results = {"error": "Usage: media_analyze.py <input_file_or_url> [--live]"}
        summary = ("The analysis needs a file or URL to inspect, but none "
                   "was provided, so nothing was checked. Provide the media "
                   "file path or URL and run the analysis again.")
        actions = ["Provide the media file path or URL you want to analyze",
                   "Re-run: media_analyze.py <input_file_or_url> [--live]"]
        attach_report(results, summary, "minor", actions)
        emit_json(results)
        render_report(summary, [], ["no input file or URL was provided"], actions)
        sys.exit(1)

    # Parse arguments
    args = sys.argv[1:]
    live_mode = "--live" in args
    non_flag_args = [a for a in args if not a.startswith("--")]
    if not non_flag_args:
        print("[WARN] no input file or URL provided (only flags were given): "
              "usage is media_analyze.py <input_file_or_url> [--live]",
              file=sys.stderr)
        results = {"error": "Usage: media_analyze.py <input_file_or_url> [--live]"}
        summary = ("Only option flags were provided, without a file or URL "
                   "to analyze, so nothing was checked. Add the media file "
                   "path or URL and run the analysis again.")
        actions = ["Provide the media file path or URL you want to analyze",
                   "Re-run: media_analyze.py <input_file_or_url> [--live]"]
        attach_report(results, summary, "minor", actions)
        emit_json(results)
        render_report(summary, [],
                      ["only flags were provided; no input file or URL"], actions)
        sys.exit(1)
    input_path = non_flag_args[0]

    # Auto-detect live streams
    auto_live = any(input_path.lower().startswith(p) for p in ("rtmp://", "rtsp://", "srt://"))

    results = {
        "input": input_path,
        "timestamp": datetime.now().isoformat(),
        "is_url": is_url(input_path),
        "is_hls": is_hls(input_path),
        "live_mode": live_mode or auto_live,
        "issues": [],
        "warnings": [],
        "info": {},
        "moov_check": None,
        "ts_check": None,
        "dts_check": None,
        "bitrate_distribution": None,
        "live_diagnosis": None
    }

    # 1. ffprobe basic info
    probe_data = ffprobe_json(input_path, show_chapters=True)
    if not probe_data:
        results["error"] = "ffprobe failed to parse this file"
        print(f"[WARN] ffprobe failed to parse the input (missing file, "
              f"unreachable URL, or unsupported/corrupted media): {input_path}",
              file=sys.stderr)
        summary = ("The media could not be analyzed because the probing "
                   "tool failed to read it. This usually means the file is "
                   "missing or corrupted, the URL is unreachable, or the "
                   "format is not recognized. If this is a local file, "
                   "confirm it exists and is a valid media file; if it is "
                   "a URL, confirm it is reachable.")
        actions = ["Confirm the file path or URL is correct and accessible",
                   "Try playing the file locally to check whether it is corrupted",
                   "Re-run the analysis once the input is readable"]
        attach_report(results, summary, "prompt_attention", actions)
        emit_json(results)
        render_report(summary, [f"parsing the media with ffprobe: {input_path}"],
                      ["ffprobe failed to parse the input"], actions)
        sys.exit(1)

    # 2. Stream analysis
    stream_analysis = analyze_streams(probe_data)
    results["issues"].extend(stream_analysis["issues"])
    results["warnings"].extend(stream_analysis["warnings"])
    results["info"] = stream_analysis["info"]

    # 3. moov position detection (local MP4/MOV files only)
    format_name = probe_data.get("format", {}).get("format_name", "")
    if not is_url(input_path) and ("mp4" in format_name or "mov" in format_name or "m4a" in format_name):
        moov_result = detect_moov_position(input_path)
        results["moov_check"] = moov_result
        if moov_result.get("issue"):
            results["issues"].append({
                "type": "container",
                "severity": "high",
                "title": moov_result["issue"],
                "detail": f"moov offset: {moov_result['moov_offset']}, mdat offset: {moov_result['mdat_offset']}, moov size: {format_size(moov_result['moov_size'] or 0)}",
                "fix": "ffmpeg -i input.mp4 -c copy -movflags +faststart output.mp4"
            })
        if moov_result.get("moov_size") and moov_result["moov_size"] > 10 * 1024 * 1024:
            results["warnings"].append({
                "type": "container",
                "severity": "medium",
                "title": f"moov atom too large ({format_size(moov_result['moov_size'])})",
                "detail": "An oversized moov increases startup time and memory consumption",
                "fix": "Consider chunked upload or using the fMP4 format"
            })

    # 4. TS continuity check (local TS files only)
    if not is_url(input_path) and is_ts_file(input_path):
        ts_result = check_ts_continuity(input_path)
        results["ts_check"] = ts_result
        if ts_result["errors"] > 0:
            results["issues"].append({
                "type": "ts_continuity",
                "severity": "high",
                "title": f"TS continuity counter discontinuous ({ts_result['errors']} errors)",
                "detail": "; ".join(ts_result["details"][:5]),
                "fix": "Re-segment: ffmpeg -i source.mp4 -c copy -f hls -hls_time 10 output.m3u8"
            })

    # 5. DTS monotonicity check
    dts_issues = check_dts_monotonic(input_path)
    results["dts_check"] = dts_issues
    if dts_issues:
        results["issues"].append({
            "type": "dts",
            "severity": "high",
            "title": f"DTS not monotonically increasing ({len(dts_issues)} regressions)",
            "detail": "; ".join(dts_issues[:3]),
            "fix": "Fix timestamps: ffmpeg -i input -c copy -fflags +genpts output.mp4"
        })

    # 6. Bitrate distribution analysis
    bitrate_dist = analyze_bitrate_distribution(input_path)
    results["bitrate_distribution"] = bitrate_dist
    if bitrate_dist and bitrate_dist["peak_to_avg_ratio"] > 3.0:
        results["warnings"].append({
            "type": "bitrate",
            "severity": "medium",
            "title": f"Severe bitrate spikes (peak/avg = {bitrate_dist['peak_to_avg_ratio']}x)",
            "detail": f"Average {bitrate_dist['avg_bitrate_bps']//1000}kbps, peak {bitrate_dist['max_bitrate_bps']//1000}kbps, spike timestamps (s): {bitrate_dist['spike_seconds'][:5]}",
            "fix": "Consider CBR encoding or VBV buffer limits: ffmpeg -i input -c:v libx264 -b:v 2M -maxrate 4M -bufsize 4M output.mp4"
        })

    # 7. mediainfo enrichment (optional)
    mediainfo_data = mediainfo_json(input_path)
    results["mediainfo_available"] = mediainfo_data is not None

    # 8. Dedicated live stream diagnostics
    if results["live_mode"]:
        live_result = analyze_live_stream(probe_data, input_path)
        results["live_diagnosis"] = live_result["latency_factors"]
        results["issues"].extend(live_result["issues"])
        results["warnings"].extend(live_result["warnings"])

    # 9. Plain-language report layer (machine-readable JSON unchanged)
    issues = results["issues"]
    warnings = results["warnings"]
    info = results.get("info", {})
    basic_parts = []
    if info.get("format_name"):
        basic_parts.append(f"container {info['format_name']}")
    if info.get("video_codec"):
        basic_parts.append(f"video codec {info['video_codec']}")
    if info.get("audio_codec"):
        basic_parts.append(f"audio codec {info['audio_codec']}")
    if info.get("resolution"):
        basic_parts.append(f"resolution {info['resolution']}")
    if info.get("duration"):
        basic_parts.append(f"duration {info['duration']:.1f}s")
    basic = ", ".join(basic_parts) if basic_parts else "basic media information"

    high_issues = [i for i in issues if i.get("severity") == "high"]
    if high_issues:
        severity_key = "prompt_attention"
        summary = (f"The media was analyzed successfully and problems were "
                   f"found that are very likely to cause the symptoms you "
                   f"see. There are {len(high_issues)} serious finding(s) "
                   f"plus {len(warnings)} minor note(s). Each finding below "
                   f"includes what it means and how to fix it.")
    elif warnings:
        severity_key = "needs_attention"
        summary = (f"The media is playable, but the analysis found "
                   f"{len(warnings)} thing(s) that are not ideal. They "
                   f"usually do not break playback, but fixing them "
                   f"improves compatibility and smoothness. See the "
                   f"findings for details.")
    else:
        severity_key = "minor"
        summary = (f"No problems were found. The media looks healthy "
                   f"({basic}) and should play normally.")

    actions = []
    action_hints = {
        "container": "Apply the suggested re-mux/index rebuild command on a copy of the file",
        "codec_compat": "Consider the suggested transcode if playback on browsers or mobile matters",
        "live_bframe": "Re-push the stream with B-frames disabled (see the suggested command)",
        "live_audio_codec": "Re-push the stream with AAC audio (see the suggested command)",
        "ts_continuity": "Re-segment the source file (see the suggested command)",
        "dts": "Regenerate timestamps with the suggested command on a copy of the file",
        "av_sync": "Trim-align audio and video with the suggested command",
        "bitrate": "Re-encode with a bitrate cap as suggested",
        "framerate": "Convert to a constant frame rate if sync issues occur",
        "codec_config": "Limit B-frames for low-latency scenarios",
        "live_gop": "Shorten the keyframe interval when pushing the stream",
        "live_audio_profile": "Switch the audio profile to AAC-LC",
        "live_audio_samplerate": "Resample audio to 44100Hz or 48000Hz",
    }
    for issue in issues:
        hint = action_hints.get(issue.get("type"))
        if hint and hint not in actions:
            actions.append(hint)
    if not actions and warnings:
        actions.append("Review the warnings in 'warnings' and apply the suggested fixes if the symptoms persist")
    if not actions:
        actions = ["No action required"]

    checked = [f"full media analysis of: {input_path}", basic]
    if results.get("moov_check"):
        checked.append(gloss("moov atom position (MP4 startup layout)"))
    if results.get("ts_check"):
        checked.append(gloss("TS continuity counters"))
    if results.get("dts_check") is not None:
        checked.append(gloss("DTS timestamp monotonicity"))
    if results.get("bitrate_distribution"):
        checked.append(gloss("bitrate distribution and spikes"))
    if results.get("live_diagnosis"):
        checked.append(gloss("live latency factors (B-frames, GOP, audio compliance)"))

    findings = [gloss(f"[problem] {i['title']}") for i in issues]
    findings += [gloss(f"[note] {w['title']}") for w in warnings]

    attach_report(results, summary, severity_key, actions)
    emit_json(results)
    render_report(summary, checked, findings, actions)


if __name__ == "__main__":
    main()
