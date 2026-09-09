#!/usr/bin/env python3
"""
Live stream quality diagnosis.

Automated checks for a live stream: connectivity, codecs, bitrate and
framerate, GOP / B-frames, and audio-video sync.
Outputs diagnosis results and fix recommendations in JSON.
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from urllib.parse import urlparse


def run_cmd(cmd, timeout=10):
    """Run a command and return (stdout, returncode)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout, result.returncode
    except subprocess.TimeoutExpired:
        return "", -1
    except FileNotFoundError:
        return "", -2


class FfprobeMissing(Exception):
    """Raised when the ffprobe binary is not installed on this machine."""


def ffprobe_available():
    """Return True when the ffprobe binary can be found."""
    _, rc = run_cmd(["ffprobe", "-version"], timeout=5)
    return rc != -2


def check_connectivity(url):
    """Check live stream connectivity."""
    result = {"url": url, "reachable": False, "latency_ms": None, "error": None}

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    # For RTMP/SRT/RTSP etc., probe with ffprobe
    if scheme in ("rtmp", "rtmps", "rtsp", "srt", "artc"):
        if not ffprobe_available():
            result["error"] = (
                "Environment issue: ffprobe is not installed, so this stream "
                "scheme cannot be probed; install ffmpeg/ffprobe and retry"
            )
            return result
        start = time.time()
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            url,
        ]
        stdout, rc = run_cmd(cmd, timeout=8)
        elapsed_ms = int((time.time() - start) * 1000)

        if rc == 0:
            result["reachable"] = True
            result["latency_ms"] = elapsed_ms
        else:
            result["error"] = f"ffprobe exit code {rc}"
        return result

    # For HTTP/HTTPS, probe with curl
    if scheme in ("http", "https"):
        start = time.time()
        cmd = ["curl", "-sI", "-o", "/dev/null", "-w", "%{http_code}", "--connect-timeout", "5", url]
        stdout, rc = run_cmd(cmd, timeout=8)
        elapsed_ms = int((time.time() - start) * 1000)

        if rc == 0 and stdout.strip() in ("200", "206"):
            result["reachable"] = True
            result["latency_ms"] = elapsed_ms
        elif rc != 0:
            # Attribute the failure by curl exit code instead of reporting
            # a meaningless "HTTP status code: 000".
            curl_reasons = {
                6: "DNS resolution failed: the host could not be resolved",
                7: "Connection refused by the server",
                28: "Connection timed out",
            }
            result["error"] = curl_reasons.get(rc, f"Network probe failed (curl exit code {rc})")
        else:
            result["error"] = f"HTTP status code: {stdout.strip() if stdout else 'no response'}"
        return result

    # Local file or invalid input
    import os
    if os.path.isfile(url):
        result["reachable"] = True
        result["latency_ms"] = 0
    else:
        result["error"] = (
            "Invalid stream URL or missing file; check the URL spelling and "
            "the protocol scheme (e.g. rtmp://, https://)"
        )
    return result


def ffprobe_stream(url):
    """Get stream info using ffprobe.

    Raises FfprobeMissing when the ffprobe binary is not installed, so the
    caller can degrade gracefully instead of misreporting the failure.
    """
    if not ffprobe_available():
        raise FfprobeMissing()
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        url,
    ]
    stdout, rc = run_cmd(cmd, timeout=10)
    if rc != 0:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def check_encoding(probe_data, is_live=True):
    """Check codec information."""
    result = {
        "video_codec": None,
        "audio_codec": None,
        "video_profile": None,
        "audio_profile": None,
        "resolution": None,
        "b_frames": 0,
        "issues": [],
    }

    if not probe_data:
        result["issues"].append({"severity": "error", "detail": "Unable to get stream info"})
        return result

    streams = probe_data.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    # Video info
    if video_streams:
        vs = video_streams[0]
        result["video_codec"] = vs.get("codec_name", "unknown")
        result["video_profile"] = vs.get("profile", "unknown")
        w = vs.get("width", 0)
        h = vs.get("height", 0)
        result["resolution"] = f"{w}x{h}" if w and h else None
        result["b_frames"] = int(vs.get("has_b_frames", 0))

        # Live-specific checks
        if is_live:
            # B-frame check - zero tolerance for live streaming
            if result["b_frames"] > 0:
                result["issues"].append({
                    "severity": "critical",
                    "detail": f"B-frames detected (count={result['b_frames']}); a live stream should have no B-frames as they increase encoding and decoding latency",
                    "plain": "B-frames make the video wait for future frames before showing them, which adds delay; live streams should turn them off.",
                    "fix": "Use -bf 0 -tune zerolatency",
                })

            # HEVC check - not supported over RTMP
            if result["video_codec"] in ("hevc", "h265"):
                result["issues"].append({
                    "severity": "critical",
                    "detail": "Video codec is HEVC/H.265; the RTMP protocol does not support HEVC ingest",
                    "plain": "The video is encoded in a format (H.265) that the RTMP live protocol cannot carry; switch to H.264.",
                    "fix": "Transcode to H.264: ffmpeg -c:v libx264 -preset veryfast -crf 23",
                })
    else:
        result["issues"].append({
            "severity": "critical",
            "detail": "No video stream detected",
            "fix": "Check whether the publisher is streaming correctly",
        })

    # Audio info
    if audio_streams:
        aus = audio_streams[0]
        result["audio_codec"] = aus.get("codec_name", "unknown")
        result["audio_profile"] = aus.get("profile", "unknown")

        if is_live:
            # RTMP requires AAC
            if result["audio_codec"] not in ("aac", None):
                result["issues"].append({
                    "severity": "critical",
                    "detail": f"Audio codec is {result['audio_codec']}; RTMP requires AAC",
                    "plain": "The audio format is not the one (AAC) that live streaming expects, so viewers may get no sound.",
                    "fix": "Transcode audio: ffmpeg -c:a aac -ar 44100 -b:a 128k",
                })

            # AAC-HE compatibility
            profile = result["audio_profile"] or ""
            if "he" in profile.lower() or "hev2" in profile.lower():
                result["issues"].append({
                    "severity": "warning",
                    "detail": f"Audio profile is {result['audio_profile']}; some devices are not compatible",
                    "plain": "A high-efficiency audio variant is in use; older phones and players may fail to play it.",
                    "fix": "Downgrade to AAC-LC: -profile:a aac_low -b:a 128k",
                })
    else:
        result["issues"].append({
            "severity": "warning",
            "detail": "No audio stream detected",
            "fix": "Check the audio settings on the publisher side",
        })

    return result


def check_bitrate_framerate(probe_data):
    """Check bitrate and framerate."""
    result = {
        "video_bitrate": None,
        "audio_bitrate": None,
        "framerate": None,
        "avg_framerate": None,
        "issues": [],
    }

    if not probe_data:
        return result

    fmt = probe_data.get("format", {})
    streams = probe_data.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    # Total bitrate
    total_bitrate = int(fmt.get("bit_rate", 0) or 0)

    # Video bitrate
    if video_streams:
        vs = video_streams[0]
        v_bitrate = int(vs.get("bit_rate", 0) or 0)
        if not v_bitrate and total_bitrate:
            # Estimate: total bitrate - audio bitrate
            a_bitrate = int(audio_streams[0].get("bit_rate", 0) or 0) if audio_streams else 128000
            v_bitrate = total_bitrate - a_bitrate
        result["video_bitrate"] = f"{v_bitrate // 1000}k" if v_bitrate else "unknown"

        # Framerate
        r_fr = vs.get("r_frame_rate", "0/1")
        avg_fr = vs.get("avg_frame_rate", "0/1")
        try:
            num, den = map(int, r_fr.split("/"))
            result["framerate"] = round(num / den, 2) if den else 0
        except (ValueError, ZeroDivisionError):
            result["framerate"] = 0
        try:
            num, den = map(int, avg_fr.split("/"))
            result["avg_framerate"] = round(num / den, 2) if den else 0
        except (ValueError, ZeroDivisionError):
            result["avg_framerate"] = 0

        # Unstable framerate check
        if result["framerate"] > 0 and result["avg_framerate"] > 0:
            diff = abs(result["framerate"] - result["avg_framerate"]) / result["framerate"]
            if diff > 0.1:
                result["issues"].append({
                    "severity": "warning",
                    "detail": f"Unstable framerate (r_frame_rate={result['framerate']}, avg={result['avg_framerate']}); possibly VFR",
                    "plain": "The number of pictures per second keeps changing (variable framerate), which can cause stuttering in live playback.",
                    "fix": "Use a constant framerate: -r 30 -vsync cfr",
                })

        # Framerate too low
        if 0 < result["framerate"] < 15:
            result["issues"].append({
                "severity": "warning",
                "detail": f"Framerate too low ({result['framerate']}fps); playback may not be smooth",
                "fix": "Raise the framerate to at least 24fps",
            })

    # Audio bitrate
    if audio_streams:
        a_bitrate = int(audio_streams[0].get("bit_rate", 0) or 0)
        result["audio_bitrate"] = f"{a_bitrate // 1000}k" if a_bitrate else "unknown"

    return result


def check_gop(probe_data, is_live=True):
    """Check GOP / keyframe interval."""
    result = {
        "gop_size": None,
        "keyframe_interval_s": None,
        "issues": [],
    }

    if not probe_data:
        return result

    streams = probe_data.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]

    if not video_streams:
        return result

    vs = video_streams[0]

    # Try to get the GOP size.
    # ffprobe does not output GOP size directly; infer from the codec context.
    gop = int(vs.get("gop_size", 0) or 0)
    if not gop:
        # Inferring from key_frame gaps would need deeper analysis;
        # simplified handling: mark as estimated/unknown.
        result["gop_size"] = "unknown"
    else:
        result["gop_size"] = gop

    # Combine framerate with GOP to compute the keyframe interval
    r_fr = vs.get("r_frame_rate", "0/1")
    try:
        num, den = map(int, r_fr.split("/"))
        fps = num / den if den else 0
    except (ValueError, ZeroDivisionError):
        fps = 0

    if result["gop_size"] != "unknown" and fps > 0:
        interval = result["gop_size"] / fps
        result["keyframe_interval_s"] = round(interval, 2)

        if is_live:
            # Live streaming: warn when the keyframe interval exceeds 4s
            if interval > 4:
                result["issues"].append({
                    "severity": "warning",
                    "detail": f"Keyframe interval {interval:.1f}s is too long; it hurts first-frame time and seeking",
                    "plain": "GOP (the gap between full picture refreshes) is too long, so viewers wait longer when the stream starts or recovers.",
                    "fix": "Set -g 50 -keyint_min 50 (about one keyframe every 2s at 25fps)",
                })
            # Suggestion when the interval exceeds 2s
            elif interval > 2:
                result["issues"].append({
                    "severity": "info",
                    "detail": f"Keyframe interval {interval:.1f}s; for live streaming it is recommended to keep it within 2s",
                    "fix": f"Consider -g {fps*2:.0f} -keyint_min {fps*2:.0f}",
                })

    return result


def check_av_sync(probe_data):
    """Check audio-video synchronization."""
    result = {
        "pts_offset_ms": None,
        "audio_sample_rate": None,
        "issues": [],
    }

    if not probe_data:
        return result

    streams = probe_data.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    if not video_streams or not audio_streams:
        return result

    vs = video_streams[0]
    aus = audio_streams[0]

    # Check start PTS
    v_start = float(vs.get("start_time", 0) or 0)
    a_start = float(aus.get("start_time", 0) or 0)
    offset_ms = (v_start - a_start) * 1000
    result["pts_offset_ms"] = round(offset_ms, 2)

    # Audio sample rate
    result["audio_sample_rate"] = aus.get("sample_rate", "unknown")

    # Warn on large offsets
    if abs(offset_ms) > 200:
        result["issues"].append({
            "severity": "warning",
            "detail": f"Audio-video PTS offset is {offset_ms:.0f}ms; audio and video may drift out of sync",
            "plain": "The sound and the picture start at slightly different times, so lips and voices may not match.",
            "fix": "Fix timestamps with -fflags +genpts -avoid_negative_ts make_zero",
        })

    # Duration mismatch check
    v_duration = float(vs.get("duration", 0) or 0)
    a_duration = float(aus.get("duration", 0) or 0)
    if v_duration > 0 and a_duration > 0:
        diff_s = abs(v_duration - a_duration)
        if diff_s > 0.5:
            result["issues"].append({
                "severity": "warning",
                "detail": f"Audio-video duration differs by {diff_s:.1f}s; playback may end abnormally",
                "fix": "Truncate with -shortest or fix the timestamps",
            })

    return result


def run_diagnosis(url, quick=False):
    """Run the full diagnosis."""
    issues = []
    checks = {}

    # 1. Connectivity check
    conn = check_connectivity(url)
    checks["connectivity"] = conn
    if not conn["reachable"]:
        return {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unreachable",
            "severity": "critical",
            "summary": (
                "The live stream could not be reached, so no quality data was collected. "
                "Next: verify the URL spelling, confirm the broadcaster is live, and check "
                "whether the auth_key in the URL has expired."
            ),
            "checks": checks,
            "issues": [{
                "severity": "critical",
                "detail": f"Live stream unreachable: {conn.get('error', 'unknown error')}",
                "plain": "We could not connect to the stream at all, so nothing else could be checked.",
                "fix": "Check that the URL is correct, the auth key is not expired, and the network is reachable",
            }],
            "recommendations": [
                "Verify the publisher is streaming correctly",
                "Check whether the auth_key in the URL has expired (the signed part of the URL has a limited lifetime)",
            ],
        }

    # 2. ffprobe probing. When ffprobe is not installed, degrade gracefully:
    # the connectivity result above stays valid, codec-dependent checks are
    # skipped, and the missing tool is recorded as an environment issue.
    try:
        probe_data = ffprobe_stream(url)
    except FfprobeMissing:
        issues.append({
            "severity": "warning",
            "detail": (
                "Environment issue: ffprobe is not installed on this machine; "
                "the following checks were SKIPPED: "
                "(1) codec analysis - incompatible codecs such as HEVC-over-RTMP or "
                "non-AAC audio cannot be detected; "
                "(2) GOP & keyframe interval - slow first-frame and long stream recovery "
                "cannot be detected; "
                "(3) B-frames - extra encoding/decoding latency cannot be detected; "
                "(4) audio-video sync - lip-sync drift cannot be detected"
            ),
            "plain": (
                "The tool used to inspect the stream content (ffprobe) is "
                "missing here, so we could only test whether the stream is "
                "reachable. We cannot tell why a stream stutters, looks "
                "pixelated, or has bad sound until ffprobe is installed."
            ),
            "fix": (
                "STRONGLY RECOMMENDED: install ffmpeg (which provides ffprobe) and re-run "
                "the diagnosis - macOS: brew install ffmpeg; Linux: apt install ffmpeg or yum install ffmpeg"
            ),
        })
        return {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "overall_status": "degraded_environment",
            # Severity rationale: the core analysis is entirely unusable without
            # ffprobe, which is more serious than a single quality warning (medium),
            # but the script itself completed and connectivity was verified, so it
            # stops short of "critical". Exit code stays 0 (degraded_environment is
            # not a critical failure per the existing exit-code semantics).
            "severity": "high",
            "summary": (
                "The stream is reachable, but ffprobe is not installed on this machine. "
                "Without ffprobe only connectivity can be verified; root causes of "
                "stuttering, pixelation, latency and encoding issues CANNOT be diagnosed. "
                "Next: STRONGLY RECOMMENDED to install ffmpeg (macOS: brew install ffmpeg; "
                "Linux: apt install ffmpeg or yum install ffmpeg), then re-run the diagnosis "
                "for the full quality report."
            ),
            "checks": checks,
            "issues": issues,
            "recommendations": [
                "STRONGLY RECOMMENDED: install ffmpeg (which provides ffprobe); without it "
                "codec, GOP, B-frame and audio-video sync analysis are all unavailable "
                "(macOS: brew install ffmpeg; Linux: apt install ffmpeg or yum install ffmpeg)",
                "Re-run the diagnosis after installing ffmpeg to get the full quality report",
            ],
        }

    # 3. Codec check
    enc = check_encoding(probe_data, is_live=True)
    checks["encoding"] = {k: v for k, v in enc.items() if k != "issues"}
    issues.extend(enc.get("issues", []))

    if quick:
        return {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "overall_status": "quick_check_done",
            "severity": "high" if any(i["severity"] == "critical" for i in issues) else "info",
            "summary": (
                "Quick check finished (connectivity + codec only). "
                + (
                    "Problems were found; see the issues list for details and fixes."
                    if issues else "No problems found in the quick check."
                )
            ),
            "checks": checks,
            "issues": issues,
            "recommendations": [],
        }

    # 4. Bitrate / framerate check
    br = check_bitrate_framerate(probe_data)
    checks["bitrate_framerate"] = {k: v for k, v in br.items() if k != "issues"}
    issues.extend(br.get("issues", []))

    # 5. GOP check
    gop = check_gop(probe_data, is_live=True)
    checks["gop"] = {k: v for k, v in gop.items() if k != "issues"}
    issues.extend(gop.get("issues", []))

    # 6. Audio-video sync check
    sync = check_av_sync(probe_data)
    checks["av_sync"] = {k: v for k, v in sync.items() if k != "issues"}
    issues.extend(sync.get("issues", []))

    # Overall assessment
    has_critical = any(i["severity"] == "critical" for i in issues)
    has_warning = any(i["severity"] == "warning" for i in issues)

    if has_critical:
        overall = "critical"
        severity = "critical"
        summary = (
            f"Diagnosis finished and found {sum(1 for i in issues if i['severity'] == 'critical')} critical problem(s) "
            "that very likely break live viewing. Next: apply the fixes in the issues list on the publisher side."
        )
    elif has_warning:
        overall = "warning"
        severity = "medium"
        summary = (
            f"Diagnosis finished with {sum(1 for i in issues if i['severity'] == 'warning')} warning(s); "
            "the stream works but quality may suffer. Next: review the issues list and apply the suggested fixes."
        )
    else:
        overall = "healthy"
        severity = "info"
        summary = (
            "No problems found; the stream looks healthy. "
            "Next: no action is needed right now."
        )

    # Build recommendations
    recommendations = []
    for issue in issues:
        if issue.get("fix"):
            recommendations.append(issue["fix"])

    return {
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "overall_status": overall,
        "severity": severity,
        "summary": summary,
        "checks": checks,
        "issues": issues,
        "recommendations": recommendations,
    }


def main():
    parser = argparse.ArgumentParser(description="Live stream quality diagnosis")
    parser.add_argument("url", help="Live stream URL")
    parser.add_argument("--quick", action="store_true", help="Quick check (connectivity + codec only)")

    args = parser.parse_args()

    try:
        result = run_diagnosis(args.url, quick=args.quick)
    except Exception as e:
        # Last-resort guard: never end with a bare traceback; always emit a
        # valid JSON diagnosis (no fabricated data).
        result = {
            "url": args.url,
            "timestamp": datetime.now().isoformat(),
            "overall_status": "failed",
            "severity": "high",
            "summary": (
                f"The diagnosis could not be completed: {e} "
                "Next: resolve the issue above and retry."
            ),
            "checks": {},
            "issues": [],
            "recommendations": [],
        }
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Exit code semantics: non-zero only for critical failures (unreachable
    # stream or critical issues); warning-level results keep exit code 0.
    if result["overall_status"] in ("unreachable", "critical", "failed"):
        sys.exit(1)


if __name__ == "__main__":
    main()
