#!/usr/bin/env python3
"""Alibaba Cloud OSS Media Processing Script.

Translates structured operation parameters into OSS processing syntax
and executes the request against an OSS bucket.

Supports:
- Image processing (resize, crop, rotate, watermark, blur, etc.)
- Blind watermark embedding/extraction
- AI detection (faces, bodies, cars, codes, labels, score)
- Video processing (convert, snapshot, animation, sprite, snapshots, concat)
- Audio processing (convert, concat, info)
- HLS streaming (m3u8)

Processing modes:
- Synchronous: x-oss-process (default)
- Asynchronous: x-oss-async-process (--async flag)

Usage:
    python process.py --bucket BUCKET --region REGION --source KEY --operations OP [OP ...]
    python process.py --bucket BUCKET --region REGION --source KEY --operations OP --async --wait

Environment Variables / Aliyun CLI:
    Credentials auto-discovered via alibabacloud-credentials SDK
    (Supports ~/.aliyun/config.json, ECS instance metadata).
    ALIBABA_CLOUD_OSS_BUCKET         Default OSS bucket name
    ALIBABA_CLOUD_OSS_REGION         Default OSS region (e.g., cn-hangzhou)
    ALIBABA_CLOUD_IMM_PROJECT        IMM project name (for blindwatermark-extract)
"""

import argparse
import base64
import hashlib
import importlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from errors import die as _die

# Ensure sibling modules (load_env, imm_client, etc.) are importable
# regardless of the working directory when invoked via absolute path.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

oss2 = None  # Lazy-loaded when OSS connection is needed

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Basic image processing operations
BASIC_OPERATIONS = {
    "resize", "crop", "indexcrop", "rotate", "flip", "quality", "format",
    "watermark",
    "blur", "sharpen", "bright", "contrast",
    "auto-orient", "circle", "rounded-corners", "interlace",
    "info", "average-hue",
}

# IMM AI detection operations (synchronous via x-oss-process)
IMM_DETECT_OPERATIONS = {"faces", "bodies", "cars", "codes", "labels", "score"}

# IMM async operations (require IMM SDK polling)
IMM_ASYNC_OPERATIONS = {"blindwatermark-extract"}

# IMM operations that require saveas (synchronous via process_object)
IMM_SAVEAS_OPERATIONS = {"blindwatermark-embed"}

# Video operations (sync-capable)
VIDEO_SYNC_OPERATIONS = {"video/snapshot", "video/info"}

# Video operations (async-only)
VIDEO_ASYNC_ONLY_OPERATIONS = {
    "video/convert", "video/animation", "video/sprite", "video/snapshots", "video/concat",
}

# Audio operations (async-only)
AUDIO_ASYNC_ONLY_OPERATIONS = {"audio/convert", "audio/concat"}

# Audio operations (sync-capable)
AUDIO_SYNC_OPERATIONS = {"audio/info"}

# HLS operations
HLS_OPERATIONS = {"hls/m3u8"}

# All video/audio/HLS operations
MEDIA_OPERATIONS = (
    VIDEO_SYNC_OPERATIONS | VIDEO_ASYNC_ONLY_OPERATIONS
    | AUDIO_ASYNC_ONLY_OPERATIONS | AUDIO_SYNC_OPERATIONS
    | HLS_OPERATIONS
)

# Operations that ONLY support async
ASYNC_ONLY_OPERATIONS = VIDEO_ASYNC_ONLY_OPERATIONS | AUDIO_ASYNC_ONLY_OPERATIONS

# File operations (plain upload/download, no processing)
FILE_OPERATIONS = {"upload", "download"}

# All valid operations
VALID_OPERATIONS = (
    BASIC_OPERATIONS | IMM_DETECT_OPERATIONS
    | IMM_ASYNC_OPERATIONS | IMM_SAVEAS_OPERATIONS
    | MEDIA_OPERATIONS | FILE_OPERATIONS
)

# Operations that return JSON info directly (routed to _mode_info)
INFO_OPERATIONS = {"info", "average-hue"} | IMM_DETECT_OPERATIONS

# Media info operations (return JSON metadata)
MEDIA_INFO_OPERATIONS = {"video/info", "audio/info"}

# Strength mapping for blind watermark embed
STRENGTH_MAP = {
    "low": "strength_low",
    "medium": "strength_middle",
    "high": "strength_high",
}

# Mapping from friendly operation names to OSS process action names
OPERATION_NAME_MAP = {
    "resize": "resize",
    "crop": "crop",
    "indexcrop": "indexcrop",
    "rotate": "rotate",
    "flip": "flip",
    "quality": "quality",
    "format": "format",
    "watermark": "watermark",
    "blur": "blur",
    "sharpen": "sharpen",
    "bright": "bright",
    "contrast": "contrast",
    "auto-orient": "auto-orient",
    "circle": "circle",
    "rounded-corners": "rounded-corners",
    "interlace": "interlace",
    "info": "info",
    "average-hue": "average-hue",
    # IMM operations
    "blindwatermark-embed": "blindwatermark",
    "blindwatermark-extract": "blindwatermark-extract",
    "faces": "faces",
    "bodies": "bodies",
    "cars": "cars",
    "codes": "codes",
    "labels": "labels",
    "score": "score",
    # Video operations
    "video/convert": "video/convert",
    "video/snapshot": "video/snapshot",
    "video/info": "video/info",
    "video/animation": "video/animation",
    "video/sprite": "video/sprite",
    "video/snapshots": "video/snapshots",
    "video/concat": "video/concat",
    # Audio operations
    "audio/convert": "audio/convert",
    "audio/concat": "audio/concat",
    "audio/info": "audio/info",
    # HLS
    "hls/m3u8": "hls/m3u8",
}

# Parameters that require URL-safe Base64 encoding
BASE64_PARAMS = {
    "watermark": {"text", "image", "type", "shadow"},
    "blindwatermark-embed": {"content"},
}

# OSS parameter key mapping: friendly key -> OSS key
OSS_KEY_MAP = {
    "quality": {"q": "Q"},
    "format": {"target": ""},  # special handling
    "watermark": {
        "text": "text",
        "size": "size",
        "color": "color",
        "opacity": "t",
        "g": "g",
        "x": "x",
        "y": "y",
        "type": "type",
        "shadow": "shadow",
        "image": "image",
        "tile": "P",
        "rw": "rw",
        "rh": "rh",
        "aw": "aw",
        "ah": "ah",
        "preprocess": "",  # special: watermark image preprocessing pipeline
    },
    "resize": {
        "w": "w",
        "h": "h",
        "mode": "m",
        "l": "l",
        "s": "s",
        "p": "p",
        "limit": "limit",
        "color": "color",
    },
    "crop": {
        "w": "w",
        "h": "h",
        "x": "x",
        "y": "y",
        "g": "g",
    },
    "indexcrop": {
        "x": "x",
        "y": "y",
        "i": "i",
    },
    "rotate": {
        "angle": "",  # special: value-only parameter
        "degree": "",  # alias for angle
        "a": "a",
    },
    "blur": {"r": "r", "s": "s"},
    "sharpen": {"v": ""},   # value-only
    "bright": {"v": ""},    # value-only
    "contrast": {"v": ""},  # value-only
    "circle": {"r": "r"},
    "rounded-corners": {"r": "r"},
    "interlace": {"mode": ""},  # value-only
    "blindwatermark-embed": {
        "content": "content",
        "s": "",  # strength: handled specially in _translate_operation
    },
}

# Operations that use positional (value-only) parameters
VALUE_ONLY_PARAMS = {
    "rotate": ("angle", "degree"),
    "flip": "v",
    "sharpen": "v",
    "bright": "v",
    "contrast": "v",
    "interlace": "mode",
    "auto-orient": "v",
}

# Gravity abbreviation normalization: short form -> OSS official form
# OSS API requires full names: north, west, center, east, south
# but users/agents may pass abbreviated: n, w, c, e, s
GRAVITY_NORMALIZE = {
    "n": "north",
    "w": "west",
    "c": "center",
    "e": "east",
    "s": "south",
}

# Parameter validation rules: operation -> {param: (type, *args)}
PARAM_VALIDATION_RULES = {
    "resize": {
        "w": ("positive_int",),
        "h": ("positive_int",),
        "l": ("positive_int",),
        "s": ("positive_int",),
        "p": ("int_range", 1, 1000),
        "limit": ("enum", ["0", "1"]),
        "mode": ("enum", ["lfit", "mfit", "fill", "pad", "fixed"]),
    },
    "crop": {
        "w": ("positive_int",),
        "h": ("positive_int",),
        "x": ("non_negative_int",),
        "y": ("non_negative_int",),
        "g": ("enum", ["nw", "north", "ne", "west", "center", "east", "sw", "south", "se", "auto", "face",
                       "n", "w", "c", "e", "s"]),
        "p": ("int_range", 1, 200),
    },
    "indexcrop": {
        "x": ("positive_int",),
        "y": ("positive_int",),
        "i": ("non_negative_int",),
    },
    "rotate": {
        "angle": ("int_range", 0, 360),
        "degree": ("int_range", 0, 360),
    },
    "flip": {
        "v": ("enum", ["0", "1", "2"]),
    },
    "quality": {
        "q": ("int_range", 1, 100),
    },
    "blur": {
        "r": ("int_range", 1, 50),
        "s": ("int_range", 1, 50),
        "g": ("enum", ["face", "faces"]),
        "p": ("int_range", 1, 200),
    },
    "sharpen": {
        "v": ("int_range", 50, 399),
    },
    "bright": {
        "v": ("int_range", -100, 100),
    },
    "contrast": {
        "v": ("int_range", -100, 100),
    },
    "circle": {
        "r": ("positive_int",),
    },
    "rounded-corners": {
        "r": ("positive_int",),
    },
    "interlace": {
        "mode": ("enum", ["0", "1"]),
    },
    "auto-orient": {
        "v": ("enum", ["0", "1"]),
    },
    "format": {
        "target": ("enum", ["jpg", "jpeg", "png", "webp", "bmp", "gif",
                             "avif", "tiff", "heic"]),
    },
    "watermark": {
        "size": ("positive_int",),
        "opacity": ("int_range", 0, 100),
        "x": ("non_negative_int",),
        "y": ("non_negative_int",),
        "g": ("enum", ["nw", "north", "ne", "west", "center", "east", "sw", "south", "se",
                       "n", "w", "c", "e", "s"]),
        "tile": ("enum", ["0", "1"]),
        "rw": ("int_range", 1, 1000),
        "rh": ("int_range", 1, 1000),
        "aw": ("positive_int",),
        "ah": ("positive_int",),
    },
    "video/convert": {
        "vb": ("positive_int",),
        "fps": ("positive_int",),
        "gop": ("positive_int",),
        "s": ("resolution",),
    },
    "video/animation": {
        "w": ("positive_int",),
        "h": ("positive_int",),
        "fps": ("positive_int",),
        "t": ("positive_int",),
    },
    "video/snapshot": {
        "t": ("positive_int",),
        "w": ("positive_int",),
        "h": ("positive_int",),
    },
    "video/snapshots": {
        "interval": ("positive_int",),
        "inter": ("positive_int",),
        "num": ("positive_int",),
        "w": ("positive_int",),
        "h": ("positive_int",),
    },
    "video/sprite": {
        "sw": ("positive_int",),
        "sh": ("positive_int",),
        "tw": ("positive_int",),
        "th": ("positive_int",),
        "cols": ("positive_int",),
        "rows": ("positive_int",),
        "num": ("positive_int",),
        "inter": ("positive_int",),
    },
    "audio/convert": {
        "ab": ("positive_int",),
        "ar": ("positive_int",),
    },
    "hls/m3u8": {
        "ss": ("non_negative_int",),
        "t": ("positive_int",),
        "fps": ("positive_int",),
        "vb": ("positive_int",),
        "ab": ("positive_int",),
        "s": ("resolution",),
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _b64_encode(text: str) -> str:
    """URL-safe Base64 encode without padding."""
    encoded = base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


SENSITIVE_URL_QUERY_KEYS = {
    "ossaccesskeyid",
    "accesskeyid",
    "x-oss-credential",
    "x_oss_credential",
    "signature",
    "x-oss-signature",
    "x_oss_signature",
    "security-token",
    "securitytoken",
    "sts_token",
}


def _redact_presigned_url(url: str) -> str:
    """Redact sensitive signing query parameters before printing or logging."""
    parts = urllib.parse.urlsplit(url)
    if not parts.query:
        return url

    query_pairs = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    redacted_pairs = []
    for key, value in query_pairs:
        normalized_key = key.strip().lower()
        if normalized_key in SENSITIVE_URL_QUERY_KEYS:
            redacted_pairs.append((key, "***"))
        else:
            redacted_pairs.append((key, value))

    return urllib.parse.urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path,
        urllib.parse.urlencode(redacted_pairs),
        parts.fragment,
    ))


def _split_csv_respecting_quotes(text: str) -> list:
    """Split a comma-separated string while preserving quoted segments."""
    parts = []
    current = []
    quote_char = None

    for ch in text:
        if quote_char:
            if ch == quote_char:
                quote_char = None
            current.append(ch)
            continue
        if ch in ("'", '"'):
            quote_char = ch
            current.append(ch)
            continue
        if ch == ",":
            parts.append("".join(current))
            current = []
            continue
        current.append(ch)

    parts.append("".join(current))
    return parts


def _strip_matching_quotes(value: str) -> str:
    """Remove matching single or double quotes around a value."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


# ---------------------------------------------------------------------------
# URI helpers (--uri support)
# ---------------------------------------------------------------------------


def _is_url(uri: str) -> bool:
    """Return True if the URI looks like an HTTP(S) URL."""
    return uri.lower().startswith(("http://", "https://"))


def _resolve_uri(uri: str):
    """Download a URL or read a local file, returning (filename, file_bytes)."""
    if _is_url(uri):
        parsed = urllib.parse.urlparse(uri)
        filename = os.path.basename(parsed.path) or "image"
        try:
            resp = urllib.request.urlopen(uri, timeout=60)  # noqa: S310
            file_bytes = resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            _die(
                f"Failed to download URI: {exc}",
                "Check the URL is accessible and try again.",
            )
        return filename, file_bytes

    # Local file path
    if not os.path.isfile(uri):
        _die(
            f"Local file not found: {uri}",
            "Check the file path and try again.",
        )
    with open(uri, "rb") as fh:
        file_bytes = fh.read()
    return os.path.basename(uri), file_bytes


def _compute_upload_temp_key(filename: str, file_bytes: bytes) -> str:
    """Generate a deterministic temp key for uploaded content."""
    content_hash = hashlib.sha256(file_bytes).hexdigest()[:16]
    safe_name = re.sub(r"[^\w.\-]", "_", filename)
    return f"_upload_tmp/{content_hash}_{safe_name}"


def _upload_uri_to_oss(bucket, uri: str) -> str:
    """Resolve a URI (URL or local path), upload to OSS, return the temp key."""
    filename, file_bytes = _resolve_uri(uri)
    temp_key = _compute_upload_temp_key(filename, file_bytes)
    try:
        bucket.put_object(temp_key, file_bytes)
    except Exception as exc:
        _die(
            f"Failed to upload to OSS: {exc}",
            "Check bucket permissions and credentials.",
        )
    print(
        json.dumps({"status": "uploaded", "temp_key": temp_key,
                     "size": len(file_bytes)}),
        file=sys.stderr,
    )
    return temp_key


def _cleanup_upload_tmp(bucket, temp_key: str) -> None:
    """Best-effort delete of the uploaded temp object."""
    try:
        bucket.delete_object(temp_key)
        print(
            json.dumps({"status": "cleaned_up", "temp_key": temp_key}),
            file=sys.stderr,
        )
    except Exception as exc:
        print(
            json.dumps({"status": "warning",
                         "message": f"Failed to clean up temp object: {exc}"}),
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# File operations (plain upload / download)
# ---------------------------------------------------------------------------


def _mode_file_upload(bucket, uri: str, target_key: str = None) -> dict:
    """Upload a local file or URL content to an OSS object key."""
    filename, file_bytes = _resolve_uri(uri)
    if not target_key:
        target_key = filename
    try:
        result = bucket.put_object(target_key, file_bytes)
    except Exception as exc:
        _die(
            f"Failed to upload to OSS: {exc}",
            "Check bucket permissions and credentials.",
        )
    request_id = getattr(result, "request_id", None)
    return {
        "success": True,
        "mode": "upload",
        "target_key": target_key,
        "size": len(file_bytes),
        "request_id": request_id,
    }


def _mode_file_download(bucket, source: str, output_path: str) -> dict:
    """Download a raw file from OSS to a local path (no processing)."""
    try:
        result = bucket.get_object(source)
    except Exception as exc:
        _die(
            f"Failed to download from OSS: {exc}",
            "Check that the object key exists and you have read permission.",
        )

    request_id = getattr(result, "request_id", None)

    parent_dir = os.path.dirname(output_path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    size = 0
    with open(output_path, "wb") as f:
        for chunk in result:
            f.write(chunk)
            size += len(chunk)

    abs_path = os.path.abspath(output_path)

    return {
        "success": True,
        "mode": "download",
        "path": abs_path,
        "size": size,
        "request_id": request_id,
    }


def _parse_operation(op_str: str):
    """Parse an operation string like 'resize:w=400,h=300' into (name, params_dict).
    
    Special handling for video/concat and audio/concat which use segment syntax:
    video/concat:f=mp4,vcodec=h264,acodec=aac/sur,o_<base64>,ss_0,t_30000/pre,o_<base64>
    """
    # Special handling for concat operations with segments
    if op_str.startswith("video/concat:") or op_str.startswith("audio/concat:"):
        return _parse_concat_operation(op_str)
    
    if ":" in op_str:
        name, params_raw = op_str.split(":", 1)
        name = name.strip()
        params = {}
        if name == "watermark":
            known_keys = {"image", "text", "size", "color", "opacity", "g", "x", "y", "type", "shadow", "tile", "rw", "rh", "aw", "ah", "preprocess"}
            parts = _split_csv_respecting_quotes(params_raw)
            i = 0
            while i < len(parts):
                pair = parts[i].strip()
                if not pair:
                    i += 1
                    continue
                if "=" not in pair:
                    _die(
                        f"Invalid parameter format '{pair}' in operation '{name}'.",
                        "Expected format: key=value (e.g., w=400)."
                    )
                k, v = pair.split("=", 1)
                k = k.strip()
                v = _strip_matching_quotes(v.strip())
                if k == "preprocess":
                    preprocess_parts = [v]
                    i += 1
                    while i < len(parts):
                        next_pair = parts[i].strip()
                        if "=" in next_pair:
                            next_k = next_pair.split("=", 1)[0].strip()
                            if next_k in known_keys:
                                break
                        preprocess_parts.append(_strip_matching_quotes(next_pair))
                        i += 1
                    params[k] = ",".join(preprocess_parts)
                elif k == "shadow":
                    shadow_parts = [v]
                    i += 1
                    while i < len(parts):
                        next_pair = parts[i].strip()
                        if "=" in next_pair:
                            next_k = next_pair.split("=", 1)[0].strip()
                            if next_k in known_keys:
                                break
                        shadow_parts.append(_strip_matching_quotes(next_pair))
                        i += 1
                    params[k] = ",".join(shadow_parts)
                else:
                    params[k] = v
                    i += 1
        else:
            # format is a common single-value shorthand in user prompts.
            # Accept format:webp and normalize it to format:target=webp.
            if name == "format" and "=" not in params_raw and "," not in params_raw:
                shorthand = _strip_matching_quotes(params_raw.strip())
                if shorthand:
                    params["target"] = shorthand
                    return name, params
            for pair in _split_csv_respecting_quotes(params_raw):
                pair = pair.strip()
                if not pair:
                    continue
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k.strip()] = _strip_matching_quotes(v.strip())
                else:
                    _die(
                        f"Invalid parameter format '{pair}' in operation '{name}'.",
                        "Expected format: key=value (e.g., w=400)."
                    )
        return name, params
    else:
        return op_str.strip(), {}


def _parse_concat_operation(op_str: str):
    """Parse video/concat or audio/concat operation with segment syntax.
    
    Format: video/concat:f=mp4,vcodec=h264,acodec=aac/sur,o_<base64>,ss_0,t_30000/pre,o_<base64>
    Returns: (name, params_dict) where params_dict includes '_segments' key
    """
    # Split by ':' to get name and rest
    if ":" not in op_str:
        _die(
            f"Invalid concat operation: '{op_str}'.",
            "Expected format: video/concat:f=mp4,vcodec=h264,acodec=aac/sur,o_<key>/pre,o_<key>"
        )
    
    name, rest = op_str.split(":", 1)
    name = name.strip()
    
    # Split by '/' to separate base params from segments
    # But we need to be careful: base64 keys may contain '/'
    # Strategy: split by '/' and identify segments by looking for 'o_' prefix
    parts = rest.split("/")
    
    # First part should be base params (f=mp4,vcodec=h264,acodec=aac)
    base_params_str = parts[0]
    params = {}
    for pair in base_params_str.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if "=" in pair:
            k, v = pair.split("=", 1)
            params[k.strip()] = v.strip()
        else:
            _die(
                f"Invalid parameter format '{pair}' in {name} base params.",
                "Expected format: key=value (e.g., f=mp4)."
            )
    
    # Remaining parts are segments (/sur,o_<key>,ss_0,t_30000 or /pre,o_<key>)
    segments = []
    i = 1
    while i < len(parts):
        segment_str = parts[i].strip()
        if not segment_str:
            i += 1
            continue
        
        # Check if this is a segment (starts with 'sur,' or 'pre,')
        if segment_str.startswith("sur,") or segment_str.startswith("pre,"):
            seg_type = segment_str[:3]  # 'sur' or 'pre'
            seg_params_str = segment_str[4:]  # rest after 'sur,' or 'pre,'
            
            # Parse segment parameters: o_<base64>,ss_0,t_30000
            seg_params = {"type": seg_type}
            for pair in seg_params_str.split(","):
                pair = pair.strip()
                if not pair:
                    continue
                if "_" in pair:
                    # Format: o_<base64> or ss_0 or t_30000
                    k, v = pair.split("_", 1)
                    seg_params[k.strip()] = v.strip()
                else:
                    _die(
                        f"Invalid segment parameter format '{pair}'.",
                        "Expected format: key_value (e.g., o_<base64_key>, ss_0, t_30000)."
                    )
            
            segments.append(seg_params)
        else:
            # This might be a continuation of base params or an error
            # Try to parse as base param
            if "=" in segment_str:
                k, v = segment_str.split("=", 1)
                params[k.strip()] = v.strip()
            else:
                _die(
                    f"Invalid concat syntax: '{segment_str}'.",
                    "Segments must start with 'sur,' or 'pre,'."
                )
        
        i += 1
    
    if not segments:
        _die(
            f"{name} requires at least one segment (/sur or /pre).",
            f"Example: {name}:f=mp4,vcodec=h264,acodec=aac/sur,o_<base64_key>"
        )
    
    params["_segments"] = segments
    return name, params


def _validate_operation_params(name: str, params: dict) -> None:
    """Validate parameter types and ranges for a given operation."""
    rules = PARAM_VALIDATION_RULES.get(name)
    if not rules:
        return
    for key, value in params.items():
        rule = rules.get(key)
        if not rule:
            continue
        rule_type = rule[0]
        if rule_type == "positive_int":
            try:
                iv = int(value)
            except ValueError:
                _die(
                    f"Parameter '{key}' for '{name}' must be a positive integer, "
                    f"got '{value}'.",
                    f"Provide a positive integer value (e.g., {key}=400)."
                )
            if iv <= 0:
                _die(
                    f"Parameter '{key}' for '{name}' must be a positive integer, "
                    f"got '{value}'.",
                    f"Provide a value greater than 0."
                )
        elif rule_type == "non_negative_int":
            try:
                iv = int(value)
            except ValueError:
                _die(
                    f"Parameter '{key}' for '{name}' must be a non-negative integer, "
                    f"got '{value}'.",
                    f"Provide a non-negative integer value (e.g., {key}=0)."
                )
            if iv < 0:
                _die(
                    f"Parameter '{key}' for '{name}' must be a non-negative integer, "
                    f"got '{value}'.",
                    f"Provide a value >= 0."
                )
        elif rule_type == "int_range":
            lo, hi = rule[1], rule[2]
            try:
                iv = int(value)
            except ValueError:
                _die(
                    f"Parameter '{key}' for '{name}' must be an integer "
                    f"between {lo} and {hi}, got '{value}'.",
                    f"Provide an integer in [{lo}, {hi}]."
                )
            if iv < lo or iv > hi:
                _die(
                    f"Parameter '{key}' for '{name}' must be an integer "
                    f"between {lo} and {hi}, got '{value}'.",
                    f"Adjust the value to be within [{lo}, {hi}]."
                )
        elif rule_type == "enum":
            allowed = rule[1]
            if value not in allowed:
                _die(
                    f"Parameter '{key}' for '{name}' must be one of "
                    f"{allowed}, got '{value}'.",
                    f"Use one of the allowed values: {', '.join(allowed)}."
                )
        elif rule_type == "resolution":
            if not re.fullmatch(r"\d+x\d+", value):
                _die(
                    f"Parameter '{key}' for '{name}' must use WIDTHxHEIGHT format, "
                    f"got '{value}'.",
                    f"Provide a value like {key}=1280x720."
                )


def _classify_operations(operations, force_async=False):
    """Classify a list of (name, params) tuples into a routing category.

    Returns one of: 'basic', 'info', 'saveas', 'async', 'media_sync',
                     'media_async', 'media_info', 'file'.
    Raises error for incompatible combinations.
    """
    has_basic = False
    has_info = False
    has_detect = False
    has_saveas = False
    has_imm_async = False
    has_file = False
    has_media = False
    has_media_info = False
    has_async_only_media = False

    basic_info_ops = {"info", "average-hue"}

    for name, _ in operations:
        if name in IMM_ASYNC_OPERATIONS:
            has_imm_async = True
        elif name in IMM_SAVEAS_OPERATIONS:
            has_saveas = True
        elif name in IMM_DETECT_OPERATIONS:
            has_detect = True
        elif name in FILE_OPERATIONS:
            has_file = True
        elif name in MEDIA_INFO_OPERATIONS:
            has_media_info = True
        elif name in MEDIA_OPERATIONS:
            has_media = True
            if name in ASYNC_ONLY_OPERATIONS:
                has_async_only_media = True
        elif name in basic_info_ops:
            has_info = True
        else:
            has_basic = True

    # --- file operations must be used alone ---
    if has_file and len(operations) > 1:
        _die(
            "File operations (upload, download) must be used alone.",
            "Use upload or download in a separate command."
        )
    if has_file:
        return "file"

    # --- image info operations must be used alone ---
    if has_info and len(operations) > 1:
        _die(
            "Image info operations (info, average-hue) must be used alone.",
            "Run info or average-hue in a separate command against the saved OSS object."
        )

    # --- media operations cannot be mixed with image operations ---
    if (has_media or has_media_info) and (
        has_basic or has_info or has_detect or has_saveas or has_imm_async
    ):
        _die(
            "Video/audio operations cannot be combined with image operations.",
            "Use video/audio operations in a separate command."
        )

    # --- media operations: only one per request ---
    if (has_media or has_media_info) and len(operations) > 1:
        _die(
            "Only one video/audio operation can be specified per request.",
            "Use separate commands for multiple video/audio operations."
        )

    # --- media info operations ---
    if has_media_info:
        return "media_info"

    # --- media operations ---
    if has_media:
        if has_async_only_media or force_async:
            return "media_async"
        return "media_sync"

    # --- incompatible image combinations ---
    if has_imm_async and len(operations) > 1:
        _die(
            "blindwatermark-extract must be used alone.",
            "Use blindwatermark-extract in a separate command."
        )

    if has_detect and (has_basic or has_saveas or has_imm_async):
        _die(
            "AI detection operations (faces, bodies, cars, codes, labels, score) "
            "cannot be combined with basic processing or blind watermark operations.",
            "Use detection operations in a separate command."
        )

    if has_saveas and (has_detect or has_imm_async):
        _die(
            "blindwatermark-embed cannot be combined with detection or extract operations.",
            "Use blindwatermark-embed in a separate command."
        )

    if has_saveas and has_info:
        _die(
            "blindwatermark-embed cannot be combined with info/average-hue operations.",
            "Use blindwatermark-embed in a separate command."
        )

    if has_saveas and len(operations) > 1:
        last_name = operations[-1][0]
        if last_name not in IMM_SAVEAS_OPERATIONS:
            _die(
                "blindwatermark-embed must be the last operation in the chain.",
                "Move blindwatermark-embed to the end of your operations list."
            )

    # --- return category ---
    if has_imm_async:
        return "async"
    if has_saveas:
        return "saveas"
    if has_detect or has_info:
        return "info"
    return "basic"


def _translate_operation(name: str, params: dict) -> str:
    """Translate a single operation into OSS x-oss-process syntax."""
    oss_name = OPERATION_NAME_MAP.get(name, name)

    # Operations without parameters
    if not params:
        # auto-orient requires a value: 0=keep original, 1=auto-rotate
        if name == "auto-orient":
            return f"{oss_name},1"
        return oss_name

    # Normalize gravity abbreviations to OSS official full names
    if name in ("crop", "watermark") and "g" in params:
        g_val = params["g"]
        normalized = GRAVITY_NORMALIZE.get(g_val)
        if normalized:
            params = dict(params)  # Don't mutate original
            params["g"] = normalized

    parts = [oss_name]

    # Handle format specially: format,target
    if name == "format":
        target = params.get("target")
        if target:
            parts.append(target)
        return ",".join(parts)

    # Handle blindwatermark-embed specially
    if name == "blindwatermark-embed":
        content = params.get("content")
        if not content:
            _die(
                "blindwatermark-embed requires 'content' parameter.",
                "Example: blindwatermark-embed:content=HelloWorld"
            )
        content_b64 = _b64_encode(content)
        parts.append(f"content_{content_b64}")

        strength = params.get("s", "low")
        oss_strength = STRENGTH_MAP.get(strength)
        if not oss_strength:
            _die(
                f"Invalid strength '{strength}' for blindwatermark-embed.",
                f"Valid values: {', '.join(sorted(STRENGTH_MAP.keys()))}"
            )
        parts.append(oss_strength)
        return ",".join(parts)

    # Handle watermark specially
    if name == "watermark":
        image_path = params.get("image", "")
        preprocess = params.pop("preprocess", None)
        if preprocess and image_path:
            oss_preprocess = preprocess.replace("+", "/")
            image_path = f"{image_path}?x-oss-process=image/{oss_preprocess}"
            params["image"] = image_path
        elif not image_path:
            params.pop("image", None)

    # Handle video/audio operations: pass params through as key_value
    if name in MEDIA_OPERATIONS:
        # Special handling for concat operations with segments
        if name in ("video/concat", "audio/concat") and "_segments" in params:
            segments = params["_segments"]  # Don't pop, just reference
            
            # Build base params (exclude _segments)
            base_parts = [oss_name]
            for k, v in params.items():
                if k != "_segments":
                    base_parts.append(f"{k}_{v}")
            
            # Build segment strings
            segment_strs = []
            for seg in segments:
                seg_type = seg["type"]  # Access, don't pop
                seg_params = []
                for k, v in seg.items():
                    if k != "type":  # Skip the type key in params
                        seg_params.append(f"{k}_{v}")
                segment_strs.append(f"{seg_type},{','.join(seg_params)}")
            
            # Combine: base/segment1/segment2
            return "/".join([",".join(base_parts)] + segment_strs)
        
        # Regular media operations without segments
        for k, v in params.items():
            parts.append(f"{k}_{v}")
        return ",".join(parts)

    # Build parameter list for image operations
    key_map = OSS_KEY_MAP.get(name, {})
    b64_keys = BASE64_PARAMS.get(name, set())
    value_only_key = VALUE_ONLY_PARAMS.get(name)

    for k, v in params.items():
        if k in b64_keys:
            v = _b64_encode(v)

        oss_key = key_map.get(k, k)

        is_value_only = False
        if isinstance(value_only_key, tuple):
            is_value_only = k in value_only_key
        elif value_only_key:
            is_value_only = k == value_only_key

        if is_value_only:
            parts.append(str(v))
        elif oss_key == "":
            parts.append(str(v))
        else:
            parts.append(f"{oss_key}_{v}")

    # For text watermark, inject default font type
    if name == "watermark" and "text" in params and "type" not in params:
        parts.append("type_d3F5LW1pY3JvaGVp")

    return ",".join(parts)


def _build_process_string(operations: list, media_type: str = "image") -> str:
    """Build the full x-oss-process string from a list of (name, params) tuples.

    Args:
        operations: list of (name, params) tuples
        media_type: 'image', 'video', or 'audio' — determines the prefix
    """
    prefix = f"{media_type}/"
    translated = []
    for name, params in operations:
        t = _translate_operation(name, params)
        # Strip media_type prefix from translated names to avoid double-prefixing.
        # e.g. video/sprite → sprite (then prefix re-added below → video/sprite)
        # but  hls/m3u8 stays as hls/m3u8 (→ video/hls/m3u8)
        if t.startswith(prefix):
            t = t[len(prefix):]
        translated.append(t)
    return prefix + "/".join(translated)


def _determine_media_type(operations: list) -> str:
    """Determine media type prefix based on operation names."""
    if not operations:
        return "image"
    name = operations[0][0]
    if name.startswith("video/"):
        return "video"
    if name.startswith("audio/"):
        return "audio"
    if name.startswith("hls/"):
        return "video"
    return "image"


# ---------------------------------------------------------------------------
# OSS Interaction
# ---------------------------------------------------------------------------


def _get_bucket(bucket_name: str, region: str, endpoint: str = None):
    """Create and return an oss2.Bucket instance."""
    global oss2
    if oss2 is None:
        try:
            import oss2 as _oss2
            oss2 = _oss2
        except ImportError:
            _die(
                "Missing dependency: oss2.",
                "Install it with: pip install -r scripts/requirements.txt"
            )

    from credential import USER_AGENT, get_oss_credentials_provider
    credentials_provider = get_oss_credentials_provider()

    if not endpoint:
        endpoint = f"https://oss-{region}.aliyuncs.com"

    auth = oss2.ProviderAuth(credentials_provider)
    return oss2.Bucket(
        auth, endpoint, bucket_name,
        connect_timeout=(30, 60),
        app_name=USER_AGENT,
    )


def _get_imm_client(region: str):
    """Create and return an IMM client. Delegates to shared imm_client module."""
    from imm_client import get_imm_client
    return get_imm_client(region)


def _ensure_runtime_dependencies(operations: list) -> None:
    """Fail fast with install guidance when required SDKs are missing."""
    required_modules = [
        ("oss2", "oss2"),
        ("credential", "alibabacloud-credentials"),
    ]

    operation_names = {name for name, _params in operations}
    needs_imm_sdk = bool(
        operation_names
        & (
            IMM_DETECT_OPERATIONS
            | IMM_ASYNC_OPERATIONS
            | IMM_SAVEAS_OPERATIONS
            | MEDIA_OPERATIONS
        )
    )
    if needs_imm_sdk:
        required_modules.extend(
            [
                ("alibabacloud_imm20200930", "alibabacloud_imm20200930"),
                ("alibabacloud_tea_openapi", "alibabacloud_tea_openapi"),
            ]
        )

    missing_packages = []
    for module_name, package_name in required_modules:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing_packages.append(package_name)

    if missing_packages:
        packages = ", ".join(missing_packages)
        _die(
            f"Missing required Python dependencies: {packages}.",
            "Install them with: pip install -r scripts/requirements.txt",
        )


def _mode_url(bucket, source: str, process_str: str, expires: int) -> dict:
    """Generate a signed URL for the processed file."""
    url = bucket.sign_url(
        "GET",
        source,
        expires,
        params={"x-oss-process": process_str},
    )
    return {
        "success": True,
        "mode": "url",
        "url": _redact_presigned_url(url),
        "expires_in": expires,
    }


def _mode_download(bucket, source: str, process_str: str, output_path: str) -> dict:
    """Download the processed file to a local file."""
    result = bucket.get_object(source, params={"x-oss-process": process_str})

    request_id = getattr(result, "request_id", None)

    parent_dir = os.path.dirname(output_path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    size = 0
    with open(output_path, "wb") as f:
        for chunk in result:
            f.write(chunk)
            size += len(chunk)

    abs_path = os.path.abspath(output_path)

    return {
        "success": True,
        "mode": "download",
        "path": abs_path,
        "size": size,
        "request_id": request_id,
    }


def _mode_save(bucket, source: str, process_str: str, target_key: str, bucket_name: str) -> dict:
    """Save the processed file as a new OSS object."""
    encoded_key = _b64_encode(target_key)
    encoded_bucket = _b64_encode(bucket_name)
    save_style = f"{process_str}|sys/saveas,o_{encoded_key},b_{encoded_bucket}"

    result = bucket.process_object(source, save_style)
    request_id = getattr(result, "request_id", None)

    return {
        "success": True,
        "mode": "save",
        "target_key": target_key,
        "bucket": bucket_name,
        "request_id": request_id,
    }


def _mode_info(bucket, source: str, process_str: str) -> dict:
    """Fetch image/video/audio info or AI detection results."""
    result = bucket.get_object(source, params={"x-oss-process": process_str})
    request_id = getattr(result, "request_id", None)
    body = result.read().decode("utf-8")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        data = body
    return {"success": True, "mode": "info", "data": data, "request_id": request_id}


# ---------------------------------------------------------------------------
# Async Media Processing (x-oss-async-process)
# ---------------------------------------------------------------------------


def _download_keys(bucket, keys: list, output_path: str) -> list:
    """Download multiple OSS objects to a local directory.

    Returns a list of dicts with download results for each key.
    If output_path looks like a directory (ends with / or is an existing dir),
    files are saved using their basename. Otherwise, for a single key,
    output_path is used as the file path directly.
    """
    results = []
    is_dir = output_path.endswith(os.sep) or output_path.endswith("/") or os.path.isdir(output_path)

    if is_dir or len(keys) > 1:
        # Treat output_path as a directory
        out_dir = output_path.rstrip("/").rstrip(os.sep)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        for key in keys:
            basename = os.path.basename(key)
            local_path = os.path.join(out_dir, basename)
            try:
                result = bucket.get_object(key)
                req_id = getattr(result, "request_id", None)
                size = 0
                with open(local_path, "wb") as f:
                    for chunk in result:
                        f.write(chunk)
                        size += len(chunk)
                results.append({
                    "key": key,
                    "path": os.path.abspath(local_path),
                    "size": size,
                    "request_id": req_id,
                })
            except Exception as exc:
                results.append({
                    "key": key,
                    "error": str(exc),
                })
    else:
        # Single file, use output_path as the file path
        key = keys[0]
        parent_dir = os.path.dirname(output_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        try:
            result = bucket.get_object(key)
            req_id = getattr(result, "request_id", None)
            size = 0
            with open(output_path, "wb") as f:
                for chunk in result:
                    f.write(chunk)
                    size += len(chunk)
            results.append({
                "key": key,
                "path": os.path.abspath(output_path),
                "size": size,
                "request_id": req_id,
            })
        except Exception as exc:
            results.append({
                "key": key,
                "error": str(exc),
            })

    return results


def _decode_concat_object_key(encoded_key: str) -> str:
    """Decode a URL-safe base64 OSS object key for concat validation."""
    raw_bytes = base64.urlsafe_b64decode(encoded_key + "==")
    return raw_bytes.decode("utf-8", errors="replace")


def _validate_concat_inputs(bucket, source: str, process_str: str, bucket_name: str) -> dict:
    """Validate video/concat inputs for compatibility.
    
    Checks resolution, frame rate, codec, and audio sample rate across all videos.
    Returns validation result with warnings or errors.
    """
    import re
    
    # Extract segment keys from process string
    # Format: video/concat:.../sur,o_<base64_key>,.../sur,o_<base64_key>,...
    segment_pattern = r'/sur,o_([A-Za-z0-9_-]+)'
    base64_keys = re.findall(segment_pattern, process_str)
    
    # Include the source video
    all_keys = [source] + [_decode_concat_object_key(k) for k in base64_keys]
    
    if len(all_keys) < 2:
        return {"valid": True, "warnings": []}
    
    video_infos = []
    for key in all_keys:
        try:
            info_str = f"video/info"
            result = bucket.get_object(key, params={"x-oss-process": info_str})
            body = result.read().decode("utf-8")
            info = json.loads(body)
            video_infos.append({"key": key, "info": info})
        except Exception as e:
            return {"valid": False, "error": f"Failed to get info for {key}: {str(e)}"}
    
    # Extract parameters for comparison
    def extract_params(info):
        streams = info.get("Streams", {})
        video_stream = streams.get("VideoStream", [{}])[0]
        audio_stream = streams.get("AudioStream", [{}])[0]
        
        return {
            "resolution": f"{video_stream.get('Width', '?')}x{video_stream.get('Height', '?')}",
            "width": video_stream.get("Width"),
            "height": video_stream.get("Height"),
            "fps": video_stream.get("FrameRate"),
            "video_codec": video_stream.get("CodecName"),
            "audio_codec": audio_stream.get("CodecName"),
            "audio_sample_rate": audio_stream.get("SampleRate"),
        }
    
    params_list = [extract_params(v["info"]) for v in video_infos]
    
    warnings = []
    errors = []
    
    # Check resolution consistency
    resolutions = set(p["resolution"] for p in params_list)
    if len(resolutions) > 1:
        errors.append(
            f"Resolution mismatch: {', '.join(resolutions)}. "
            f"video/concat requires all videos to have the same resolution, or you must specify -s WxH to unify them."
        )
    
    # Check frame rate consistency
    fps_values = [p["fps"] for p in params_list if p["fps"]]
    if len(set(fps_values)) > 1:
        warnings.append(
            f"Frame rate mismatch: {', '.join(str(f) + 'fps' for f in fps_values)}. "
            f"OSS may use the first video's frame rate or fail silently. Consider specifying -fps to unify."
        )
    
    # Check video codec consistency
    vcodecs = set(p["video_codec"] for p in params_list if p["video_codec"])
    if len(vcodecs) > 1:
        warnings.append(
            f"Video codec mismatch: {', '.join(vcodecs)}. "
            f"Consider specifying -vcodec to unify codecs."
        )
    
    # Check audio sample rate consistency
    sample_rates = [p["audio_sample_rate"] for p in params_list if p["audio_sample_rate"]]
    if len(set(sample_rates)) > 1:
        warnings.append(
            f"Audio sample rate mismatch: {', '.join(str(r) + 'Hz' for r in sample_rates)}. "
            f"Consider specifying -ar to unify sample rates."
        )
    
    # Check audio codec consistency
    acodecs = set(p["audio_codec"] for p in params_list if p["audio_codec"])
    if len(acodecs) > 1:
        warnings.append(
            f"Audio codec mismatch: {', '.join(acodecs)}. "
            f"Consider specifying -acodec to unify codecs."
        )
    
    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}
    
    return {"valid": True, "warnings": warnings}


def _validate_concat_output(output_path: str, source: str, process_str: str, bucket) -> dict:
    """Validate video/concat output file after download.
    
    Checks if the output duration is reasonable (should be close to sum of input durations).
    Uses ffprobe if available, otherwise falls back to basic file size check.
    """
    import subprocess
    
    warnings = []
    
    try:
        # Try to use ffprobe to get output duration
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
             "-of", "json", output_path],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            import json as json_mod
            probe_data = json_mod.loads(result.stdout)
            output_duration = float(probe_data.get("format", {}).get("duration", 0))
            
            # Get source video duration for comparison
            try:
                info_str = "video/info"
                info_result = bucket.get_object(source, params={"x-oss-process": info_str})
                info_body = info_result.read().decode("utf-8")
                source_info = json.loads(info_body)
                source_duration = float(source_info.get("Format", {}).get("Duration", 0))
                
                # If output duration is significantly less than source, something went wrong
                if output_duration < source_duration * 0.9:
                    warnings.append(
                        f"Output duration ({output_duration:.1f}s) is less than source duration ({source_duration:.1f}s). "
                        f"Concatenation may have failed or only the first video was kept."
                    )
            except Exception:
                pass  # Cannot get source info, skip duration check
        else:
            warnings.append("ffprobe not available or failed. Cannot validate output duration.")
    except FileNotFoundError:
        warnings.append("ffprobe not found. Install ffmpeg to enable output validation.")
    except Exception:
        pass  # Silently skip validation if anything goes wrong
    
    return {"valid": len(warnings) == 0, "warnings": warnings}


def _mode_media_async(
    bucket, source: str, process_str: str,
    target_key: str, bucket_name: str, wait: bool,
    output_path: str = None, timeout_seconds: int = 600,
) -> dict:
    """Execute an asynchronous media processing operation via x-oss-async-process.

    Uses oss2's async_process_object API (requires oss2 >= 2.18.4).
    The process string is sent with sys/saveas appended for the output target.

    If output_path is provided and wait is True, automatically downloads
    the output file(s) after completion. For video/snapshots, downloads all
    generated numbered files to output_path as a directory.
    """
    if not target_key:
        _die(
            "--target-key is required for async media operations.",
            "Specify the OSS path for the processed output file."
        )

    # Validate video/concat inputs before processing
    if "video/concat" in process_str:
        validation = _validate_concat_inputs(bucket, source, process_str, bucket_name)
        if not validation["valid"]:
            error_lines = validation.get("errors", [])
            warning_lines = validation.get("warnings", [])
            message = "video/concat validation failed"
            if error_lines:
                message = f"{message}: {'; '.join(error_lines)}"
            hint_parts = warning_lines + [
                "Use --dry-run to preview the command without executing."
            ]
            _die(
                message,
                " ".join(hint_parts),
            )
        elif validation.get("warnings"):
            print(
                json.dumps({"validation_warnings": validation["warnings"]}),
                file=sys.stderr,
            )

    encoded_key = _b64_encode(target_key)
    encoded_bucket = _b64_encode(bucket_name)
    async_style = f"{process_str}|sys/saveas,o_{encoded_key},b_{encoded_bucket}"

    # Use oss2's dedicated async processing API (POST with x-oss-async-process)
    result = bucket.async_process_object(source, async_style)

    # oss2's async_process_object returns AsyncProcessObject with parsed attributes
    task_id = getattr(result, 'task_id', None)
    event_id = getattr(result, 'event_id', None)
    request_id = getattr(result, 'async_request_id', None) or getattr(result, 'request_id', None)

    if not wait:
        return {
            "success": True,
            "mode": "async",
            "task_id": task_id,
            "event_id": event_id,
            "request_id": request_id,
            "target_key": target_key,
            "bucket": bucket_name,
            "status": "submitted",
        }

    # Poll for completion
    max_wait_sec = timeout_seconds
    poll_interval = 5
    elapsed = 0

    # For snapshots, OSS generates numbered files (e.g., frame_0_1.jpg, frame_0_2.jpg)
    # based on target_key. Use prefix listing to detect completion.
    # Correct target-key format: "output/frames/frame" (NO extension).
    # OSS generates: output/frames/frame_0_1.jpg, output/frames/frame_0_2.jpg, etc.
    # Old incorrect format "output/frame.jpg" caused all frames to overwrite same file.
    is_snapshots = "video/snapshots" in process_str
    if is_snapshots:
        # Use target_key as prefix directly (should already be extension-less for snapshots)
        # e.g., "output/frames/frame" matches "output/frames/frame_0_1.jpg"
        list_prefix = target_key
    else:
        list_prefix = None

    while elapsed < max_wait_sec:
        time.sleep(poll_interval)
        elapsed += poll_interval

        try:
            if is_snapshots:
                # List objects with prefix to find generated snapshot files
                result_list = bucket.list_objects(prefix=list_prefix, max_keys=1000)
                generated_keys = [
                    obj.key for obj in (result_list.object_list or [])
                    if obj.key != target_key  # exclude exact target_key if it exists
                ]
                if generated_keys:
                    sorted_keys = sorted(generated_keys)
                    completed_result = {
                        "success": True,
                        "mode": "async",
                        "task_id": task_id,
                        "request_id": request_id,
                        "target_key": target_key,
                        "generated_keys": sorted_keys,
                        "file_count": len(sorted_keys),
                        "bucket": bucket_name,
                        "status": "completed",
                        "elapsed_seconds": elapsed,
                    }
                    # Auto-download if output_path provided
                    if output_path:
                        downloaded = _download_keys(
                            bucket, sorted_keys, output_path,
                        )
                        completed_result["downloaded"] = downloaded
                    return completed_result
            else:
                # Single output file: check exact target key
                bucket.head_object(target_key)
                completed_result = {
                    "success": True,
                    "mode": "async",
                    "task_id": task_id,
                    "request_id": request_id,
                    "target_key": target_key,
                    "bucket": bucket_name,
                    "status": "completed",
                    "elapsed_seconds": elapsed,
                }
                # Auto-download if output_path provided
                if output_path:
                    downloaded = _download_keys(
                        bucket, [target_key], output_path,
                    )
                    completed_result["downloaded"] = downloaded
                
                # Post-validation for video/concat
                if "video/concat" in process_str and output_path:
                    validation = _validate_concat_output(output_path, source, process_str, bucket)
                    if not validation["valid"]:
                        completed_result["success"] = False
                        completed_result["validation_error"] = validation.get("error")
                        completed_result["validation_warnings"] = validation.get("warnings", [])
                    elif validation.get("warnings"):
                        completed_result["validation_warnings"] = validation["warnings"]
                
                return completed_result
        except Exception:
            pass

        print(
            json.dumps({"status": "polling", "elapsed": elapsed}),
            file=sys.stderr,
        )

    return {
        "success": False,
        "mode": "async",
        "target_key": target_key,
        "status": "timeout",
        "elapsed_seconds": elapsed,
        "hint": f"Task may still be running. Check if '{target_key}' exists later.",
    }


# ---------------------------------------------------------------------------
# Blind Watermark Operations
# ---------------------------------------------------------------------------


def _mode_blindwatermark_embed(
    bucket, source, operations,
    output_mode, target_key, bucket_name,
    output_path, expires,
):
    """Embed a blind watermark into the source image."""
    process_str = _build_process_string(operations)

    if output_mode == "save":
        if not target_key:
            _die(
                "--target-key is required for blindwatermark-embed with save mode.",
                "Add --target-key path/to/output.jpg to your command."
            )
        return _mode_save(bucket, source, process_str, target_key, bucket_name)

    content_hash = hashlib.sha256(
        f"{source}|{process_str}".encode()
    ).hexdigest()[:16]
    temp_key = f"_blindwatermark_tmp/{content_hash}_{os.path.basename(source)}"

    encoded_key = _b64_encode(temp_key)
    encoded_bucket = _b64_encode(bucket_name)
    save_style = f"{process_str}|sys/saveas,o_{encoded_key},b_{encoded_bucket}"
    bucket.process_object(source, save_style)

    if output_mode == "download":
        if not output_path:
            _die(
                "--output-path is required for blindwatermark-embed with download mode.",
                "Add --output-path /path/to/output.jpg to your command."
            )
        parent_dir = os.path.dirname(output_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        result = bucket.get_object(temp_key)
        size = 0
        with open(output_path, "wb") as f:
            for chunk in result:
                f.write(chunk)
                size += len(chunk)

        bucket.delete_object(temp_key)

        return {
            "success": True,
            "mode": "download",
            "path": os.path.abspath(output_path),
            "size": size,
        }

    # url mode (default)
    url = bucket.sign_url("GET", temp_key, expires)

    lifecycle_days = max(1, (expires + 86399) // 86400)
    lifecycle_update = _ensure_blindwatermark_lifecycle(bucket, lifecycle_days)
    if lifecycle_update["status"] != "updated":
        print(
            json.dumps({"status": "warning", "message":
                        lifecycle_update["message"]}),
            file=sys.stderr,
        )
    if lifecycle_update["status"] == "updated":
        cleanup_message = (
            f"Temp object '{temp_key}' will be auto-deleted after "
            f"{lifecycle_days} day(s) via OSS lifecycle rule. "
            f"You can also delete it manually after downloading."
        )
    else:
        cleanup_message = (
            f"Temp object '{temp_key}' was created for URL delivery. "
            f"Automatic lifecycle cleanup was not configured; delete it manually after use."
        )

    return {
        "success": True,
        "mode": "url",
        "url": _redact_presigned_url(url),
        "expires_in": expires,
        "temp_key": temp_key,
        "auto_cleanup_days": lifecycle_days,
        "cleanup": cleanup_message,
        "lifecycle_status": lifecycle_update["status"],
    }


def _mode_blindwatermark_extract(
    bucket_name, region, source, imm_project, params,
):
    """Extract blind watermark using IMM SDK async polling."""
    try:
        from alibabacloud_imm20200930 import models
    except ImportError:
        _die(
            "Missing dependencies for IMM operations: alibabacloud_imm20200930.",
            "Install with: pip install -r scripts/requirements.txt"
        )

    imm_client = _get_imm_client(region)

    source_uri = f"oss://{bucket_name}/{source}"
    target_uri = f"oss://{bucket_name}/_blindwatermark_result/"

    create_request = models.CreateDecodeBlindWatermarkTaskRequest(
        project_name=imm_project,
        source_uri=source_uri,
        target_uri=target_uri,
    )

    strength = params.get("s")
    if strength:
        valid_levels = {"low", "medium", "high"}
        if strength not in valid_levels:
            _die(
                f"Invalid strength '{strength}' for blindwatermark-extract.",
                f"Valid values: {', '.join(sorted(valid_levels))}"
            )
        create_request.strength_level = strength

    model = params.get("model")
    if model:
        create_request.watermark_model = model

    print(
        json.dumps({"status": "creating_task", "source": source_uri},
                    ensure_ascii=False),
        file=sys.stderr,
    )
    create_response = imm_client.create_decode_blind_watermark_task(create_request)
    task_id = create_response.body.task_id
    print(
        json.dumps({"status": "task_created", "task_id": task_id},
                    ensure_ascii=False),
        file=sys.stderr,
    )

    max_wait = 120
    interval = 3
    content = None

    for _ in range(max_wait // interval):
        time.sleep(interval)
        get_task_request = models.GetTaskRequest(
            project_name=imm_project,
            task_id=task_id,
            task_type="DecodeBlindWatermark",
        )
        get_task_response = imm_client.get_task(get_task_request)
        status = get_task_response.body.status
        print(
            json.dumps({"status": "polling", "task_status": status},
                        ensure_ascii=False),
            file=sys.stderr,
        )

        if status == "Succeeded":
            # Retrieve watermark content via the dedicated result API.
            # GetTask does NOT include the decoded content; we must call
            # GetDecodeBlindWatermarkResult to obtain it.
            result_request = models.GetDecodeBlindWatermarkResultRequest(
                project_name=imm_project,
                task_id=task_id,
                task_type="DecodeBlindWatermark",
            )
            result_response = imm_client.get_decode_blind_watermark_result(
                result_request
            )
            content = getattr(result_response.body, "content", None)
            break
        elif status in ("Failed", "Canceled"):
            msg = getattr(get_task_response.body, "message", "Unknown error")
            _die(f"Blind watermark extraction task {status}: {msg}")
    else:
        _die(
            f"Blind watermark extraction task timed out after {max_wait}s.",
            "The task may still be running. Check IMM console for task_id: "
            + task_id,
        )

    if content:
        try:
            decoded = base64.b64decode(content).decode("utf-8")
            content = decoded
        except Exception:
            pass

    return {
        "success": True,
        "mode": "info",
        "data": {"content": content, "task_id": task_id},
    }


def _ensure_blindwatermark_lifecycle(bucket, lifecycle_days: int) -> dict:
    """Safely add or update the temp-object lifecycle rule without dropping others."""
    try:
        import oss2 as _oss2
    except ImportError:
        return {
            "status": "skipped",
            "message": "oss2 SDK not installed; cannot manage lifecycle cleanup.",
        }

    rule_id = "blindwatermark-tmp-cleanup"
    new_rule = _oss2.models.LifecycleRule(
        rule_id,
        "_blindwatermark_tmp/",
        status=_oss2.models.LifecycleRule.ENABLED,
        expiration=_oss2.models.LifecycleExpiration(days=lifecycle_days),
    )

    try:
        existing = bucket.get_bucket_lifecycle()
        rules = list(getattr(existing, "rules", []) or [])
    except Exception as exc:
        error_str = str(exc)
        if any(token in error_str for token in ("NoSuchLifecycle", "NoSuchBucketLifecycle", "404")):
            rules = []
        else:
            return {
                "status": "skipped",
                "message": f"Failed to inspect existing lifecycle rules: {exc}",
            }

    updated = False
    merged_rules = []
    for rule in rules:
        if getattr(rule, "id", None) == rule_id:
            merged_rules.append(new_rule)
            updated = True
        else:
            merged_rules.append(rule)
    if not updated:
        merged_rules.append(new_rule)

    try:
        lifecycle = _oss2.models.BucketLifecycle(merged_rules)
        bucket.put_bucket_lifecycle(lifecycle)
        return {
            "status": "updated",
            "message": "Lifecycle rule configured for blind watermark temp objects.",
        }
    except Exception as exc:
        return {
            "status": "skipped",
            "message": f"Failed to set lifecycle rule without overwriting existing rules: {exc}",
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process media files (images, video, audio) stored in "
                    "Alibaba Cloud OSS using x-oss-process and x-oss-async-process.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Generate a resized thumbnail URL\n"
            "  python process.py --bucket my-bkt --region cn-hangzhou \\\n"
            "    --source img.jpg --operations 'resize:w=400'\n\n"
            "  # Get video metadata\n"
            "  python process.py --bucket my-bkt --region cn-hangzhou \\\n"
            "    --source video.mp4 --operations 'video/info'\n\n"
            "  # Async video transcoding (auto-detected)\n"
            "  python process.py --bucket my-bkt --region cn-hangzhou \\\n"
            "    --source video.mp4 --operations 'video/convert:f=mp4,vcodec=h264' \\\n"
            "    --output-mode save --target-key out.mp4\n\n"
            "  # Convert video to animated GIF (async auto-detected)\n"
            "  python process.py --bucket my-bkt --region cn-hangzhou \\\n"
            "    --source video.mp4 --operations 'video/animation:f=gif,w=480,h=320' \\\n"
            "    --output-mode save --target-key preview.gif\n\n"
            "  # Audio transcoding (async auto-detected)\n"
            "  python process.py --bucket my-bkt --region cn-hangzhou \\\n"
            "    --source audio.wav --operations 'audio/convert:f=mp3,ab=192000' \\\n"
            "    --output-mode save --target-key out.mp3\n"
        ),
    )
    parser.add_argument(
        "--source",
        help="OSS object key of the source file (e.g., photos/original.jpg). "
             "Mutually exclusive with --uri.",
    )
    parser.add_argument(
        "--uri",
        help="URL (http/https) or local file path to upload to OSS as source. "
             "Mutually exclusive with --source.",
    )
    parser.add_argument(
        "--operations", required=True, nargs="+",
        help=(
            "One or more operation strings. "
            "Format: name:key=value,key=value (e.g., 'resize:w=400,h=300'). "
            "For video/audio: 'video/convert:f=mp4,vcodec=h264'. "
            "Operations without parameters use just the name (e.g., 'info', 'video/info')."
        ),
    )
    parser.add_argument(
        "--bucket",
        default=os.environ.get("ALIBABA_CLOUD_OSS_BUCKET"),
        help="Name of the OSS bucket. "
             "Falls back to ALIBABA_CLOUD_OSS_BUCKET environment variable.",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("ALIBABA_CLOUD_OSS_REGION"),
        help="OSS region identifier (e.g., cn-hangzhou). "
             "Falls back to ALIBABA_CLOUD_OSS_REGION environment variable.",
    )
    parser.add_argument(
        "--endpoint",
        help="Custom OSS endpoint URL. Defaults to https://oss-{region}.aliyuncs.com.",
    )
    parser.add_argument(
        "--output-mode", choices=["url", "download", "save"], default="url",
        help="Output mode: url (default), download, or save.",
    )
    parser.add_argument(
        "--output-path",
        help="Local file path for download mode or download operation.",
    )
    parser.add_argument(
        "--target-key",
        help="Target OSS object key for save mode or upload operation.",
    )
    parser.add_argument(
        "--expires", type=int, default=3600,
        help="URL expiration time in seconds (default: 3600). Only used in url mode.",
    )
    parser.add_argument(
        "--imm-project",
        help=(
            "IMM project name. Required for blindwatermark-extract. "
            "Falls back to ALIBABA_CLOUD_IMM_PROJECT environment variable."
        ),
    )
    parser.add_argument(
        "--async", dest="async_mode", action="store_true",
        help="Enable asynchronous processing mode (x-oss-async-process).",
    )
    parser.add_argument(
        "--wait", action="store_true",
        help="Poll until async operation completes. Auto-enabled for auto-detected async ops.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=int(os.environ.get("ALIBABA_CLOUD_ASYNC_TIMEOUT_SECONDS", "600")),
        help=(
            "Maximum time to wait for async media completion in seconds "
            "(default: 600, or ALIBABA_CLOUD_ASYNC_TIMEOUT_SECONDS)."
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the generated process string and exit without executing.",
    )
    return parser


def validate_args(args, category: str, operations=None) -> None:
    """Validate argument combinations based on operation category."""
    if category == "file" and operations:
        op_name = operations[0][0]
        if op_name == "upload":
            if not args.uri:
                _die(
                    "--uri is required for the upload operation.",
                    "Use --uri to specify the local file or URL to upload.",
                )
            if args.source:
                _die(
                    "--source is not used with upload. Use --uri instead.",
                    "Example: --uri /path/to/file.pdf --operations upload",
                )
        elif op_name == "download":
            if not args.source:
                _die(
                    "--source is required for the download operation.",
                    "Use --source to specify the OSS object key to download.",
                )
            if args.uri:
                _die(
                    "--uri is not used with download. Use --source instead.",
                    "Example: --source docs/file.pdf --operations download",
                )
            if not args.output_path:
                _die(
                    "--output-path is required for the download operation.",
                    "Add --output-path /path/to/local/file to your command.",
                )
        return

    # --source and --uri are mutually exclusive; exactly one is required
    if args.source and args.uri:
        _die(
            "--source and --uri are mutually exclusive.",
            "Use --source for existing OSS objects, or --uri for local/URL files."
        )
    if not args.source and not args.uri:
        _die(
            "Either --source or --uri is required.",
            "Use --source for an existing OSS object key, "
            "or --uri for a local file path or URL."
        )

    if args.expires <= 0:
        _die(
            f"--expires must be a positive integer, got {args.expires}.",
            "Use a value like 3600 (1 hour) or 86400 (1 day)."
        )
    if args.timeout_seconds <= 0:
        _die(
            f"--timeout-seconds must be a positive integer, got {args.timeout_seconds}.",
            "Use a value like --timeout-seconds 600."
        )

    if category in ("basic", "saveas"):
        if args.output_mode == "download" and not args.output_path:
            _die(
                "--output-path is required when --output-mode is 'download'.",
                "Add --output-path /path/to/output.jpg to your command."
            )
        if args.output_mode == "save" and not args.target_key:
            _die(
                "--target-key is required when --output-mode is 'save'.",
                "Add --target-key path/to/target.jpg to your command."
            )

    if category in ("media_sync",):
        if args.output_mode == "download" and not args.output_path:
            _die(
                "--output-path is required when --output-mode is 'download'.",
                "Add --output-path /path/to/output to your command."
            )
        if args.output_mode == "save" and not args.target_key:
            _die(
                "--target-key is required when --output-mode is 'save'.",
                "Add --target-key path/to/target to your command."
            )

    if category == "media_async":
        if not args.target_key:
            _die(
                "--target-key is required for async media operations.",
                "Specify the OSS path for the processed output file."
            )


def main() -> None:
    # Load environment variables from config files (does not override existing)
    from load_env import ensure_env_loaded
    ensure_env_loaded(verbose=False)

    parser = build_parser()
    args = parser.parse_args()

    # Validate required bucket/region
    if not args.bucket:
        _die(
            "Bucket name is required. Use --bucket, set "
            "ALIBABA_CLOUD_OSS_BUCKET env var, or run:\n"
            "  aliyun configure set oss_bucket <your-bucket>",
            "Example: --bucket my-bucket or "
            "export ALIBABA_CLOUD_OSS_BUCKET='my-bucket'",
        )
    if not args.region:
        _die(
            "Region is required. Use --region, set "
            "ALIBABA_CLOUD_OSS_REGION env var, or run:\n"
            "  aliyun configure set oss_region <your-region>",
            "Example: --region cn-hangzhou or "
            "export ALIBABA_CLOUD_OSS_REGION='cn-hangzhou'",
        )

    # Parse and validate operations
    operations = []
    for op_str in args.operations:
        name, params = _parse_operation(op_str)
        if name not in VALID_OPERATIONS:
            available = ", ".join(sorted(VALID_OPERATIONS))
            _die(
                f"Unknown operation '{name}'.",
                f"Available operations: {available}"
            )
        _validate_operation_params(name, params)
        operations.append((name, params))

    _ensure_runtime_dependencies(operations)

    # Classify operations to determine routing
    force_async = getattr(args, "async_mode", False)
    category = _classify_operations(operations, force_async=force_async)

    # Auto-upgrade to async for async-only operations
    if category == "media_async" and not force_async:
        # These operations only support async, auto-enable it
        force_async = True
        # Auto-enable waiting so the caller gets completed results
        args.wait = True

    # Validate arguments with category context
    validate_args(args, category, operations)

    # --- dry-run: print process string and exit ---
    if args.dry_run:
        uri_info = {}
        if args.uri:
            uri_info["uri"] = args.uri
            uri_info["uri_type"] = "url" if _is_url(args.uri) else "local"
            uri_info["upload_prefix"] = "_upload_tmp/"
            if uri_info["uri_type"] == "url":
                uri_info["note"] = (
                    "File would be downloaded from URL and uploaded "
                    "to bucket before processing."
                )
            else:
                uri_info["note"] = (
                    "File would be uploaded from local path "
                    "to bucket before processing."
                )

        if category == "file":
            op_name = operations[0][0]
            output = {
                "dry_run": True,
                "category": "file",
                "operation": op_name,
            }
            if op_name == "upload":
                output["uri"] = args.uri
                output["target_key"] = args.target_key or "(derived from filename)"
                output["note"] = "File would be uploaded to OSS bucket."
            elif op_name == "download":
                output["source"] = args.source
                output["output_path"] = args.output_path
                output["note"] = "File would be downloaded from OSS bucket."
        elif category == "async":
            output = {
                "dry_run": True,
                "category": "async",
                "operations": [{"name": n, "params": p} for n, p in operations],
                "hint": "blindwatermark-extract uses IMM SDK, no x-oss-process string.",
                **uri_info,
            }
        elif category in ("media_sync", "media_async", "media_info"):
            media_type = _determine_media_type(operations)
            process_str = _build_process_string(operations, media_type=media_type)
            output = {
                "dry_run": True,
                "category": category,
                "media_type": media_type,
                "process_string": process_str,
                "operations": [{"name": n, "params": p} for n, p in operations],
                "async": category == "media_async" or force_async,
                **uri_info,
            }
        else:
            process_str = _build_process_string(operations)
            output = {
                "dry_run": True,
                "category": category,
                "process_string": process_str,
                "operations": [{"name": n, "params": p} for n, p in operations],
                **uri_info,
            }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    # --- file: upload / download (no processing) ---
    if category == "file":
        bucket = _get_bucket(args.bucket, args.region, args.endpoint)
        op_name = operations[0][0]
        if op_name == "upload":
            result = _mode_file_upload(bucket, args.uri, args.target_key)
        else:  # download
            result = _mode_file_download(bucket, args.source, args.output_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # --- Resolve --uri: upload to OSS, set args.source ---
    uploaded_temp_key = None
    bucket = None
    if args.uri:
        bucket = _get_bucket(args.bucket, args.region, args.endpoint)
        uploaded_temp_key = _upload_uri_to_oss(bucket, args.uri)
        args.source = uploaded_temp_key

    try:
        # --- async: blindwatermark-extract (IMM SDK) ---
        if category == "async":
            name, params = operations[0]
            imm_project = (
                args.imm_project or os.environ.get("ALIBABA_CLOUD_IMM_PROJECT")
            )
            if not imm_project:
                _die(
                    "IMM project name is required for blindwatermark-extract.",
                    "Set --imm-project or ALIBABA_CLOUD_IMM_PROJECT env variable."
                )
            result = _mode_blindwatermark_extract(
                args.bucket, args.region, args.source, imm_project, params,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        # Connect to OSS (if not already connected via --uri)
        if bucket is None:
            bucket = _get_bucket(args.bucket, args.region, args.endpoint)

        # --- media async operations ---
        if category == "media_async":
            media_type = _determine_media_type(operations)
            process_str = _build_process_string(operations, media_type=media_type)
            print(f"Process string: {process_str}", file=sys.stderr)
            result = _mode_media_async(
                bucket, args.source, process_str,
                args.target_key, args.bucket, args.wait,
                output_path=args.output_path,
                timeout_seconds=args.timeout_seconds,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        # --- media info (video/info, audio/info) ---
        if category == "media_info":
            media_type = _determine_media_type(operations)
            process_str = _build_process_string(operations, media_type=media_type)
            print(f"Process string: {process_str}", file=sys.stderr)
            result = _mode_info(bucket, args.source, process_str)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        # --- media sync operations ---
        if category == "media_sync":
            media_type = _determine_media_type(operations)
            process_str = _build_process_string(operations, media_type=media_type)
            print(f"Process string: {process_str}", file=sys.stderr)

            if args.output_mode == "url":
                result = _mode_url(bucket, args.source, process_str, args.expires)
            elif args.output_mode == "download":
                result = _mode_download(bucket, args.source, process_str, args.output_path)
            elif args.output_mode == "save":
                result = _mode_save(
                    bucket, args.source, process_str, args.target_key, args.bucket,
                )
            else:
                _die(f"Unknown output mode '{args.output_mode}'.")

            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        # Build OSS process string for image operations
        process_str = _build_process_string(operations)
        print(f"Process string: {process_str}", file=sys.stderr)

        # --- saveas: blindwatermark-embed ---
        if category == "saveas":
            result = _mode_blindwatermark_embed(
                bucket, args.source, operations,
                args.output_mode, args.target_key, args.bucket,
                args.output_path, args.expires,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        # --- info / detect ---
        if category == "info":
            result = _mode_info(bucket, args.source, process_str)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        # --- basic: standard image processing ---
        if args.output_mode == "url":
            result = _mode_url(bucket, args.source, process_str, args.expires)
        elif args.output_mode == "download":
            result = _mode_download(bucket, args.source, process_str, args.output_path)
        elif args.output_mode == "save":
            result = _mode_save(
                bucket, args.source, process_str, args.target_key, args.bucket,
            )
        else:
            _die(f"Unknown output mode '{args.output_mode}'.")

        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        if uploaded_temp_key and bucket:
            _cleanup_upload_tmp(bucket, uploaded_temp_key)


if __name__ == "__main__":
    main()
