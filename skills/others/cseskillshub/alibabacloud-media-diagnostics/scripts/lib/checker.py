#!/usr/bin/env python3
#
# SECURITY:
#   - This module is part of a READ-ONLY media diagnostics toolkit.
#   - It only reads files explicitly provided by the user and never
#     modifies them.
#   - No cloud credentials, API keys or tokens are required or used.
"""
Shared check functions module
Provides TS continuity checks, DTS monotonicity checks, bitrate distribution analysis, etc.
"""

import json
from .cmd import run_cmd, ffprobe_packets


def check_ts_continuity(file_path, max_packets=10000):
    """
    Check the continuity counter consistency of a TS file
    Returns: {'errors': int, 'total_packets': int, 'details': list}
    """
    result = {"errors": 0, "total_packets": 0, "details": []}
    TS_PACKET_SIZE = 188
    counters = {}

    try:
        with open(file_path, "rb") as f:
            # Locate the sync byte
            sync_offset = 0
            header = f.read(1024)
            for i in range(len(header)):
                if header[i] == 0x47:
                    if i + TS_PACKET_SIZE < len(header) and header[i + TS_PACKET_SIZE] == 0x47:
                        sync_offset = i
                        break

            f.seek(sync_offset)
            packet_count = 0

            while packet_count < max_packets:
                packet = f.read(TS_PACKET_SIZE)
                if len(packet) < TS_PACKET_SIZE:
                    break

                if packet[0] != 0x47:
                    result["details"].append(f"sync lost @ packet {packet_count}")
                    result["errors"] += 1
                    break

                pid = ((packet[1] & 0x1F) << 8) | packet[2]
                adaptation_field = (packet[3] >> 4) & 0x03
                cc = packet[3] & 0x0F

                if pid == 0x1FFF:
                    packet_count += 1
                    continue

                if adaptation_field in (0x01, 0x03):
                    if pid in counters:
                        expected_cc = (counters[pid] + 1) & 0x0F
                        if cc != expected_cc:
                            result["errors"] += 1
                            if len(result["details"]) < 10:
                                result["details"].append(
                                    f"PID 0x{pid:04X} continuity counter mismatch: expected {expected_cc}, got {cc} @ packet {packet_count}"
                                )
                    counters[pid] = cc

                packet_count += 1

            result["total_packets"] = packet_count

    except (IOError, OSError):
        result["details"].append("unable to read TS file")

    return result


def check_dts_monotonic(input_path, max_packets=5000, timeout=30):
    """
    Check whether DTS is monotonically increasing
    Returns: list of error strings (empty list means OK)
    """
    cmd = [
        "ffprobe", "-v", "quiet",
        "-select_streams", "v:0",
        "-show_entries", "packet=dts_time",
        "-print_format", "json",
        input_path
    ]
    stdout, rc = run_cmd(cmd, timeout=timeout)
    if rc != 0:
        return None

    try:
        data = json.loads(stdout)
        packets = data.get("packets", [])
    except json.JSONDecodeError:
        return None

    issues = []
    last_dts = None
    for i, pkt in enumerate(packets[:max_packets]):
        dts_str = pkt.get("dts_time")
        if dts_str is None or dts_str == "N/A":
            continue
        try:
            dts = float(dts_str)
        except ValueError:
            continue
        if last_dts is not None and dts < last_dts:
            issues.append(f"DTS regression @ packet {i}: {last_dts:.3f} -> {dts:.3f}")
            if len(issues) >= 5:
                break
        last_dts = dts

    return issues


def analyze_bitrate_distribution(input_path, timeout=30):
    """
    Analyze bitrate distribution and detect spikes
    Returns: dict or None
    """
    data = ffprobe_packets(input_path, entries="packet=size,dts_time", timeout=timeout)
    if not data:
        return None

    packets = data.get("packets", [])
    if len(packets) < 100:
        return None

    windows = {}
    for pkt in packets:
        dts_str = pkt.get("dts_time")
        size_str = pkt.get("size")
        if not dts_str or dts_str == "N/A" or not size_str:
            continue
        try:
            sec = int(float(dts_str))
            size = int(size_str)
        except ValueError:
            continue
        windows[sec] = windows.get(sec, 0) + size

    if not windows:
        return None

    bitrates = list(windows.values())
    avg_br = sum(bitrates) / len(bitrates)
    max_br = max(bitrates)
    min_br = min(bitrates)

    result = {
        "avg_bitrate_bps": int(avg_br * 8),
        "max_bitrate_bps": int(max_br * 8),
        "min_bitrate_bps": int(min_br * 8),
        "peak_to_avg_ratio": round(max_br / avg_br, 2) if avg_br > 0 else 0,
        "spike_seconds": []
    }

    threshold = avg_br * 3
    for sec, br in sorted(windows.items()):
        if br > threshold:
            result["spike_seconds"].append(sec)

    return result


def estimate_gop(input_path, timeout=15):
    """
    Estimate the GOP size by measuring the keyframe interval via ffprobe
    Returns: {'keyframe_interval': float|None, 'gop_size': int|None}
    """
    from .cmd import ffprobe_frames

    data = ffprobe_frames(
        input_path,
        entries="frame=pict_type,pts_time",
        select_streams="v:0",
        read_intervals="%+5",
        timeout=timeout
    )
    if not data:
        return {"keyframe_interval": None, "gop_size": None}

    frames = data.get("frames", [])
    keyframe_times = []
    for f in frames:
        if f.get("pict_type") == "I":
            pts = f.get("pts_time")
            if pts and pts != "N/A":
                try:
                    keyframe_times.append(float(pts))
                except ValueError:
                    pass

    if len(keyframe_times) >= 2:
        intervals = [keyframe_times[i+1] - keyframe_times[i] for i in range(len(keyframe_times)-1)]
        avg_interval = sum(intervals) / len(intervals)
        return {
            "keyframe_interval": round(avg_interval, 2),
            "gop_size": round(avg_interval * 30)
        }

    return {"keyframe_interval": None, "gop_size": None}
