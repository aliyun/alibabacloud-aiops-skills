#!/usr/bin/env python3
#
# SECURITY:
#   - This module is part of a READ-ONLY media diagnostics toolkit.
#   - It only reads files explicitly provided by the user and never
#     modifies them.
#   - No cloud credentials, API keys or tokens are required or used.
"""
Shared formatting and parsing module
Provides file size/duration formatting, MP4 box parsing and URL detection helpers
"""

import struct
import os
from urllib.parse import urlparse


def format_size(size_bytes):
    """Format a byte count into a human readable size string"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_duration(seconds):
    """Format a duration in seconds into a human readable string"""
    if seconds <= 0:
        return "unknown"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    if h > 0:
        return f"{h}h {m}m {s:.1f}s"
    elif m > 0:
        return f"{m}m {s:.1f}s"
    else:
        return f"{s:.2f}s"


def is_url(path):
    """Check whether the given path is a URL"""
    parsed = urlparse(path)
    return parsed.scheme in ("http", "https", "rtmp", "rtsp", "srt")


def is_hls(path):
    """Check whether the given path points to an HLS playlist"""
    return path.lower().endswith(".m3u8") or "m3u8" in path.lower()


def is_ts_file(path):
    """Check whether the given path points to a TS file"""
    return path.lower().endswith(".ts")


def detect_input_type(input_path):
    """Detect the input type of the given file path or URL"""
    parsed = urlparse(input_path)
    scheme = parsed.scheme.lower()
    path_lower = input_path.lower()

    if scheme in ("rtmp", "rtsp", "srt"):
        return "live_protocol"
    elif path_lower.endswith(".m3u8") or "m3u8" in path_lower:
        return "hls"
    elif path_lower.endswith(".mpd"):
        return "dash"
    elif path_lower.endswith(".ts"):
        return "ts_file"
    elif path_lower.endswith(".flv"):
        return "flv_file"
    elif any(path_lower.endswith(ext) for ext in (".mp4", ".mov", ".m4a", ".m4v", ".3gp")):
        return "mp4_file"
    elif scheme in ("http", "https"):
        return "http_url"
    elif os.path.isfile(input_path):
        return "local_file"
    else:
        return "unknown"


def parse_mp4_boxes(file_path, max_bytes=None):
    """
    Parse the top-level ISO BMFF box structure of an MP4 file
    max_bytes: limit the number of bytes to scan (None = scan the whole file)
    Returns: [{'type': str, 'offset': int, 'size': int}, ...]
    """
    boxes = []
    try:
        file_size = os.path.getsize(file_path)
        scan_limit = max_bytes or file_size

        with open(file_path, "rb") as f:
            offset = 0
            while offset < scan_limit:
                f.seek(offset)
                header = f.read(8)
                if len(header) < 8:
                    break

                size = struct.unpack(">I", header[0:4])[0]
                box_type = header[4:8].decode("ascii", errors="ignore")

                if size == 1:
                    ext = f.read(8)
                    if len(ext) < 8:
                        break
                    size = struct.unpack(">Q", ext)[0]
                elif size == 0:
                    size = file_size - offset

                boxes.append({
                    "type": box_type,
                    "offset": offset,
                    "size": size,
                })

                if size == 0:
                    break
                offset += size

    except (IOError, OSError, struct.error):
        pass

    return boxes


def quick_moov_check(file_path):
    """
    Quickly detect the moov position (only the first 64KB is read)
    Returns: "faststart" | "moov_at_end" | "unknown" | "unreadable"
    """
    try:
        with open(file_path, "rb") as f:
            offset = 0
            file_size = os.path.getsize(file_path)
            first_boxes = []

            while offset < min(file_size, 65536):
                f.seek(offset)
                header = f.read(8)
                if len(header) < 8:
                    break
                size = struct.unpack(">I", header[0:4])[0]
                box_type = header[4:8].decode("ascii", errors="ignore")

                if size == 1:
                    ext = f.read(8)
                    if len(ext) < 8:
                        break
                    size = struct.unpack(">Q", ext)[0]
                elif size == 0:
                    size = file_size - offset

                first_boxes.append(box_type)

                if box_type == "moov":
                    return "faststart"

                if size == 0:
                    break
                offset += size

            if "mdat" in first_boxes:
                return "moov_at_end"
            return "unknown"
    except (IOError, OSError):
        return "unreadable"


def detect_moov_position(file_path):
    """
    Detect the position of the moov/mdat boxes in an MP4 file
    Returns: {'moov_offset': int|None, 'mdat_offset': int|None, 'moov_size': int|None, 'issue': str|None}
    """
    result = {
        "moov_offset": None,
        "mdat_offset": None,
        "moov_size": None,
        "issue": None
    }

    boxes = parse_mp4_boxes(file_path)
    for box in boxes:
        if box["type"] == "moov" and result["moov_offset"] is None:
            result["moov_offset"] = box["offset"]
            result["moov_size"] = box["size"]
        elif box["type"] == "mdat" and result["mdat_offset"] is None:
            result["mdat_offset"] = box["offset"]

        if result["moov_offset"] is not None and result["mdat_offset"] is not None:
            break

    if result["moov_offset"] is not None and result["mdat_offset"] is not None:
        if result["moov_offset"] > result["mdat_offset"]:
            result["issue"] = "moov box located after mdat (not faststart)"
    elif result["moov_offset"] is None and result["mdat_offset"] is not None:
        result["issue"] = "moov box not found (file may be corrupted)"

    return result
