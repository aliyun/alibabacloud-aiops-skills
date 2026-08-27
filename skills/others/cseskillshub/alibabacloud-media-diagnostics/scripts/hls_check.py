#!/usr/bin/env python3
#
# SECURITY:
#   - This script is part of a READ-ONLY media diagnostics toolkit.
#   - It only fetches (GET/HEAD) the m3u8 URL and its referenced
#     segments explicitly provided by the user; it never writes or
#     modifies any remote or local content.
#   - All HTTP requests carry an explicit timeout to avoid hanging.
#   - No cloud credentials, API keys or tokens are required or used.
#
# Exit codes:
#   0: check completed and JSON result printed to stdout
#   1: missing input argument, m3u8 fetch failed, or m3u8 parse failed
#      (JSON result still printed on stdout, [WARN] written to stderr)
"""
Dedicated HLS/M3U8 check script
Checks: segment reachability, duration consistency, discontinuity sanity,
TS segment integrity
Refactored version: uses the shared modules under lib/
"""

import os
import re
import sys
import uuid
from urllib.parse import urljoin, urlparse

# Allow running directly from the project directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.format import is_url
from lib.report import attach_report, emit_json, gloss, render_report

# Default HTTP timeout (seconds) for all network requests
DEFAULT_TIMEOUT = 15

# Maximum bytes downloaded per TS segment during integrity sampling.
# Rationale: sampled segments are only checked for structure (sync byte,
# PAT/PMT, 188-byte alignment), which is fully decidable from the first
# ~19 KB; a per-segment cap of 8 MB bounds worst-case download to ~24 MB
# (3 sampled segments) while still covering typical 1080p segments.

# Per-run session id for platform-level tracing (Observability):
# a 32-character lowercase hex string, generated once per script run and
# shared by every HTTP request of this run.
_SESSION_ID = uuid.uuid4().hex
_USER_AGENT = f"AlibabaCloud-Agent-Skills/alibabacloud-media-diagnostics/{_SESSION_ID}"


MAX_SEGMENT_BYTES = 8 * 1024 * 1024


def fetch_url(url, timeout=DEFAULT_TIMEOUT, method="GET"):
    """Fetch URL content (http/https/file schemes)"""
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError

    try:
        req = Request(url, method=method)
        req.add_header("User-Agent", _USER_AGENT)
        with urlopen(req, timeout=timeout) as resp:
            # file:// responses carry no numeric status; treat as 200
            status = getattr(resp, "status", None) or 200
            if method == "HEAD":
                return {"status": status, "headers": dict(resp.headers)}
            return {"status": status, "body": resp.read().decode("utf-8", errors="ignore")}
    except HTTPError as e:
        return {"status": e.code, "error": str(e)}
    except (URLError, OSError, ValueError) as e:
        return {"status": 0, "error": str(e)}


def parse_m3u8(content, base_url):
    """Parse an m3u8 playlist"""
    lines = content.strip().split("\n")
    result = {
        "is_master": False,
        "version": None,
        "target_duration": None,
        "segments": [],
        "discontinuities": [],
        "total_duration": 0,
        "variants": []
    }

    if "#EXTM3U" not in content:
        return None

    # Master Playlist
    if "#EXT-X-STREAM-INF" in content:
        result["is_master"] = True
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF"):
                attrs = {}
                for match in re.finditer(r'(\w+)=("[^"]*"|[^,]*)', line):
                    attrs[match.group(1)] = match.group(2).strip('"')
                if i + 1 < len(lines) and not lines[i + 1].startswith("#"):
                    variant_url = lines[i + 1].strip()
                    if not variant_url.startswith("http"):
                        variant_url = urljoin(base_url, variant_url)
                    attrs["url"] = variant_url
                result["variants"].append(attrs)
        return result

    # Media Playlist
    seg_index = 0
    current_duration = 0

    for i, line in enumerate(lines):
        line = line.strip()

        if line.startswith("#EXT-X-VERSION:"):
            try:
                result["version"] = int(line.split(":")[1])
            except (ValueError, IndexError):
                # Malformed tag value: keep version unknown and continue
                result["version"] = None
        elif line.startswith("#EXT-X-TARGETDURATION:"):
            try:
                result["target_duration"] = float(line.split(":")[1])
            except (ValueError, IndexError):
                # Malformed tag value: keep targetDuration unknown and continue
                result["target_duration"] = None
        elif line.startswith("#EXTINF:"):
            duration_str = line.split(":")[1].rstrip(",")
            try:
                current_duration = float(duration_str.split(",")[0])
            except ValueError:
                current_duration = 0
        elif line.startswith("#EXT-X-DISCONTINUITY"):
            result["discontinuities"].append(seg_index)
        elif not line.startswith("#") and line:
            seg_url = line
            if not seg_url.startswith("http"):
                seg_url = urljoin(base_url, seg_url)
            result["segments"].append({
                "index": seg_index,
                "url": seg_url,
                "duration": current_duration
            })
            result["total_duration"] += current_duration
            seg_index += 1
            current_duration = 0

    return result


def check_segment_accessibility(segments, sample_count=3):
    """Sample-check segment reachability (HTTP HEAD)"""
    results = []
    check_indices = []

    if len(segments) <= sample_count:
        check_indices = list(range(len(segments)))
    else:
        check_indices = [0, len(segments) // 2, len(segments) - 1]

    for idx in check_indices:
        seg = segments[idx]
        resp = fetch_url(seg["url"], method="HEAD")
        results.append({
            "index": idx,
            "url": seg["url"],
            "status": resp.get("status"),
            "accessible": resp.get("status") == 200,
            "error": resp.get("error")
        })

    return results


def check_duration_consistency(segments, target_duration):
    """Check segment duration consistency"""
    if not segments:
        return {"consistent": True, "issues": []}

    durations = [s["duration"] for s in segments]
    avg_duration = sum(durations) / len(durations)
    issues = []

    for seg in segments:
        if seg["duration"] <= 0:
            issues.append(f"segment #{seg['index']} has zero duration")
        elif target_duration and seg["duration"] > target_duration * 1.5:
            issues.append(f"segment #{seg['index']} duration {seg['duration']:.2f}s exceeds 1.5x targetDuration ({target_duration}s)")
        elif avg_duration > 0 and abs(seg["duration"] - avg_duration) / avg_duration > 0.5:
            issues.append(f"segment #{seg['index']} duration {seg['duration']:.2f}s deviates >50% from average {avg_duration:.2f}s")

    return {
        "consistent": len(issues) == 0,
        "avg_duration": round(avg_duration, 2),
        "min_duration": round(min(durations), 2) if durations else 0,
        "max_duration": round(max(durations), 2) if durations else 0,
        "issues": issues[:10]
    }


def check_ts_segment_integrity(url, timeout=DEFAULT_TIMEOUT):
    """Download and check the integrity of a single TS segment"""
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError

    try:
        req = Request(url)
        req.add_header("User-Agent", _USER_AGENT)
        with urlopen(req, timeout=timeout) as resp:
            # Chunked read with a hard per-segment byte cap so a huge
            # segment cannot blow up download volume or memory.
            chunks = []
            total = 0
            truncated = False
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_SEGMENT_BYTES:
                    keep = MAX_SEGMENT_BYTES - (total - len(chunk))
                    if keep > 0:
                        chunks.append(chunk[:keep])
                    truncated = True
                    break
                chunks.append(chunk)
            data = b"".join(chunks)
    except (HTTPError, URLError, OSError) as e:
        return {"url": url, "error": str(e), "valid": False}

    result = {"url": url, "size": len(data), "valid": True, "issues": []}
    if truncated:
        result["truncated_at_cap"] = True
        result["issues"].append(
            f"download capped at {MAX_SEGMENT_BYTES // (1024 * 1024)} MB; "
            f"structural checks below apply to the downloaded prefix only")

    # Check minimum size
    if len(data) < 188:
        result["valid"] = False
        result["issues"].append("file too small, less than one TS packet")
        return result

    # Check sync byte
    if data[0] != 0x47:
        found = False
        for i in range(min(188, len(data))):
            if data[i] == 0x47 and i + 188 < len(data) and data[i + 188] == 0x47:
                result["issues"].append(f"sync byte offset by {i} bytes (non-standard)")
                found = True
                break
        if not found:
            result["valid"] = False
            result["issues"].append("no valid TS sync byte (0x47) found")
            return result

    # Check PAT/PMT
    has_pat = False
    has_pmt = False
    offset = 0
    packet_count = 0

    while offset + 188 <= len(data) and packet_count < 100:
        if data[offset] != 0x47:
            offset += 1
            continue
        pid = ((data[offset + 1] & 0x1F) << 8) | data[offset + 2]
        if pid == 0x0000:
            has_pat = True
        elif pid < 0x1FFF and pid != 0x0000:
            if not has_pmt and (data[offset + 1] & 0x40):
                has_pmt = True
        offset += 188
        packet_count += 1

    if not has_pat:
        result["issues"].append("PAT table (PID 0x0000) not found in the first 100 packets")
    if not has_pmt:
        result["issues"].append("no explicit PMT table found in the first 100 packets")

    # Check truncation (skipped when we cut the download ourselves at the
    # byte cap: a remainder would then reflect the cap, not the segment)
    total_packets = len(data) // 188
    remainder = len(data) % 188
    if remainder != 0 and not truncated:
        result["issues"].append(f"file size is not a multiple of 188 bytes ({remainder} bytes remainder), possibly truncated")
        result["valid"] = False

    result["total_packets"] = total_packets

    return result


def main():
    if len(sys.argv) < 2:
        print("[WARN] missing input argument: usage is hls_check.py <m3u8_url>",
              file=sys.stderr)
        results = {"error": "Usage: hls_check.py <m3u8_url>"}
        summary = ("The HLS check needs a playlist to inspect, but no m3u8 "
                   "URL was provided, so nothing was checked. Provide the "
                   "playlist URL and run the check again.")
        actions = ["Provide the m3u8 playlist URL you want to check",
                   "Re-run: hls_check.py <m3u8_url>"]
        attach_report(results, summary, "minor", actions)
        emit_json(results)
        render_report(summary, [], ["no playlist URL was provided"], actions)
        sys.exit(1)

    m3u8_url = sys.argv[1]

    # Normalize file:// inputs back to a plain local path so they are
    # handled by the local-read branch below (is_url only whitelists
    # http/https-style schemes).
    local_path = None
    if m3u8_url.startswith("file://"):
        local_path = urlparse(m3u8_url).path
    elif not is_url(m3u8_url):
        local_path = m3u8_url

    results = {
        "input": m3u8_url,
        "issues": [],
        "warnings": [],
        "playlist": None,
        "accessibility": None,
        "duration_check": None,
        "segment_integrity": []
    }

    # 1. Fetch m3u8 content (local playlists are read directly; remote
    # ones over http/https are fetched with the shared User-Agent)
    if local_path is None:
        resp = fetch_url(m3u8_url)
        base_url = m3u8_url
    else:
        try:
            with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
                resp = {"status": 200, "body": f.read()}
        except (IOError, OSError) as e:
            resp = {"status": 0, "error": str(e)}
        # Resolve relative segment paths against the local file location
        base_url = "file://" + os.path.abspath(local_path)
    if resp.get("status") != 200:
        results["error"] = f"failed to fetch m3u8: HTTP {resp.get('status')} - {resp.get('error', '')}"
        print(f"[WARN] {results['error']}", file=sys.stderr)
        summary = ("The playlist could not be fetched, so the stream cannot "
                   "be analyzed right now. This usually means the URL is "
                   "wrong, the signature has expired, or the server/network "
                   "is unreachable. Viewers would see the stream fail to "
                   "start. Verify the URL and try again.")
        actions = ["Double-check the m3u8 URL (spelling, signature, expiry)",
                   "Open the URL in a browser or with 'curl -I' to confirm reachability",
                   "If it is a CDN URL, check CDN/origin availability",
                   "Re-run the check once the URL is reachable"]
        attach_report(results, summary, "prompt_attention", actions)
        emit_json(results)
        render_report(summary, [f"fetching the playlist: {m3u8_url}"],
                      [results["error"]], actions)
        sys.exit(1)

    # 2. Parse playlist
    playlist = parse_m3u8(resp["body"], base_url)
    if not playlist:
        results["error"] = "failed to parse m3u8 content (non-standard HLS format)"
        print(f"[WARN] {results['error']}", file=sys.stderr)
        summary = ("The playlist was downloaded but could not be understood "
                   "because it does not look like a standard HLS playlist. "
                   "Players are very likely to fail on it as well. Check "
                   "whether the URL really points to an m3u8 playlist and "
                   "whether the playlist file is complete.")
        actions = ["Confirm the URL points to a valid HLS playlist (must contain #EXTM3U)",
                   "Re-export or re-upload the playlist from the packaging tool",
                   "Re-run the check after fixing the playlist"]
        attach_report(results, summary, "prompt_attention", actions)
        emit_json(results)
        render_report(summary, [f"fetching and parsing the playlist: {m3u8_url}"],
                      [results["error"]], actions)
        sys.exit(1)

    results["playlist"] = {
        "is_master": playlist["is_master"],
        "version": playlist.get("version"),
        "target_duration": playlist.get("target_duration"),
        "segment_count": len(playlist.get("segments", [])),
        "total_duration": playlist.get("total_duration", 0),
        "discontinuity_count": len(playlist.get("discontinuities", [])),
        "variant_count": len(playlist.get("variants", []))
    }

    # Master Playlist
    if playlist["is_master"]:
        results["variants"] = playlist["variants"]
        results["warnings"].append({
            "type": "info",
            "severity": "low",
            "title": f"Master Playlist contains {len(playlist['variants'])} bitrate variants",
            "detail": "The individual Media Playlists need further analysis"
        })
        n_variants = len(playlist["variants"])
        summary = (f"The playlist is healthy and readable. It is a Master "
                   f"Playlist that points to {n_variants} quality variant(s) "
                   f"(for example different resolutions or bitrates). The "
                   f"actual video segments live in each variant's own "
                   f"playlist, which were not checked in this run.")
        actions = [f"Run hls_check.py on one of the variant media playlists listed in 'variants' to check segments",
                   "No fix is needed for the Master Playlist itself"]
        attach_report(results, summary, "minor", actions)
        emit_json(results)
        render_report(
            summary,
            [f"fetching and parsing the playlist: {m3u8_url}"],
            [f"Master Playlist with {n_variants} bitrate variant(s) found; "
             "segment-level checks require a media playlist"],
            actions)
        sys.exit(0)

    segments = playlist["segments"]

    # 3. Segment reachability check
    sample_count = min(3, len(segments))
    accessibility = check_segment_accessibility(segments, sample_count)
    results["accessibility"] = accessibility
    for acc in accessibility:
        if not acc["accessible"]:
            results["issues"].append({
                "type": "accessibility",
                "severity": "high",
                "title": f"segment #{acc['index']} not accessible (HTTP {acc['status']})",
                "detail": f"URL: {acc['url']}\nError: {acc.get('error', '')}",
                "fix": "Check CDN configuration and whether the origin file exists"
            })

    # 4. Duration consistency
    duration_check = check_duration_consistency(segments, playlist.get("target_duration"))
    results["duration_check"] = duration_check
    if not duration_check["consistent"]:
        results["warnings"].append({
            "type": "duration",
            "severity": "medium",
            "title": f"Inconsistent segment durations ({duration_check['min_duration']}s ~ {duration_check['max_duration']}s)",
            "detail": "; ".join(duration_check["issues"][:5]),
            "fix": "Ensure keyframe-aligned segmentation when re-segmenting: ffmpeg -i input -c copy -f hls -hls_time 10 -force_key_frames 'expr:gte(t,n_forced*10)' output.m3u8"
        })

    # 5. Discontinuity sanity
    disc_count = len(playlist["discontinuities"])
    seg_count = len(segments)
    if disc_count > 0 and seg_count > 0:
        disc_ratio = disc_count / seg_count
        if disc_ratio > 0.3:
            results["warnings"].append({
                "type": "discontinuity",
                "severity": "medium",
                "title": f"Too many DISCONTINUITY tags ({disc_count}/{seg_count})",
                "detail": "Excessive discontinuities increase player buffer switching and hurt the viewing experience",
                "fix": "Check whether this is the output of spliced transcoding; unify parameters and re-segment"
            })

    # 6. TS segment integrity sampling
    check_count = min(3, len(segments))
    for i in range(check_count):
        seg = segments[i]
        integrity = check_ts_segment_integrity(seg["url"])
        results["segment_integrity"].append(integrity)
        if not integrity.get("valid", True):
            results["issues"].append({
                "type": "ts_integrity",
                "severity": "high",
                "title": f"segment #{i} has structural anomalies",
                "detail": "; ".join(integrity.get("issues", [])),
                "fix": "Re-transcode the segment source file"
            })
        elif integrity.get("issues"):
            results["warnings"].append({
                "type": "ts_integrity",
                "severity": "medium",
                "title": f"segment #{i} has potential issues",
                "detail": "; ".join(integrity["issues"]),
                "fix": "Verify playback; re-segment if necessary"
            })

    # 7. Plain-language report layer (machine-readable JSON unchanged)
    if results["issues"]:
        severity_key = "prompt_attention"
        summary = ("Problems were found in this HLS stream that are very "
                   "likely to affect playback: some segments (the small "
                   "video files the playlist plays one after another) are "
                   "broken or unreachable, which typically shows up as "
                   "playback interruptions or a stream that fails to "
                   "start. The Findings section below lists each problem "
                   "and what to do about it.")
    elif results["warnings"]:
        severity_key = "needs_attention"
        summary = ("The HLS stream is playable, but a few things are not "
                   "ideal (for example uneven lengths of the segments, the "
                   "small video files the playlist plays one after "
                   "another, or minor structural warnings). These usually "
                   "do not break playback, but fixing them improves "
                   "reliability. See the Findings section for details.")
    else:
        severity_key = "minor"
        summary = ("No problems were found in this HLS stream. The playlist "
                   "is well formed, sampled segments (the small video "
                   "files the playlist plays one after another) are "
                   "reachable and structurally valid, and segment lengths "
                   "are consistent. Playback should work normally.")

    actions = []
    for issue in results["issues"]:
        if issue.get("type") == "accessibility":
            actions.append("Check the CDN/origin configuration and whether the segment files still exist")
        elif issue.get("type") == "ts_integrity":
            actions.append("Re-transcode and re-segment the affected segments from the source file")
    for warning in results["warnings"]:
        if warning.get("type") == "duration" and not actions:
            actions.append("Re-segment with keyframe alignment so all segments have similar lengths")
        elif warning.get("type") == "discontinuity":
            actions.append("Unify the segmentation parameters and re-segment, so the stream has fewer discontinuity breaks")
    if not actions:
        actions = ["No action required"]
    actions = list(dict.fromkeys(actions))

    checked = [f"fetching and parsing the playlist: {m3u8_url}"]
    if results.get("accessibility"):
        checked.append(f"reachability of {len(results['accessibility'])} sampled segment(s)")
    if results.get("duration_check"):
        checked.append("segment duration consistency")
    if results.get("segment_integrity"):
        checked.append(gloss(f"structure of {len(results['segment_integrity'])} sampled TS segment(s)"))

    findings = []
    for issue in results["issues"]:
        findings.append(gloss(f"[problem] {issue['title']}"))
    for warning in results["warnings"]:
        findings.append(gloss(f"[note] {warning['title']}"))

    attach_report(results, summary, severity_key, actions)
    emit_json(results)
    render_report(summary, checked, findings, actions)


if __name__ == "__main__":
    main()
