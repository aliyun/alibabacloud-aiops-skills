#!/usr/bin/env python3
"""
image_processing_diagnosis.py -- OSS image-processing diagnosis entry
======================================================================
SECURITY: READ-ONLY. Only issues read-class OSS calls (GetBucketInfo,
HeadObject, capped GET probes with/without the read-only x-oss-process
rendering query, ListBuckets fallback) and GetCallerIdentity to STS. Never
mutates anything -- image style creation/changes are manual guidance only.
Credentials come exclusively from the default credential chain; AK/SK are
never read, printed, or passed explicitly.

Diagnoses:
  * x-oss-process parameter syntax validation (offline pure function:
    action names, parameter names, value ranges -- no network needed)
  * "processing not effective" attribution tree: source not a supported
    format / source size beyond the 20 MB limit / parameter error /
    missing object / original-image protection 403 / default-domain
    forced download
  * three-step source verification SOP: declared Content-Type (mime) ->
    object size -> magic-number verification of the leading bytes
  * default-domain forced-download explanation (Content-Disposition)

Output contract (04-spec): stdout carries a structured JSON report followed
by the machine-consumable lines:
    STATUS: OK | DEGRADED
    NEXT_ACTION: <one actionable sentence>

Usage:
  python3 image_processing_diagnosis.py --process "image/resize,w_300"
  python3 image_processing_diagnosis.py --bucket <name> --object <key> \
      [--process <x-oss-process-string>] [--region <region>] \
      [--question "<customer original wording>"]
"""

from __future__ import annotations

import argparse
import json
import sys

import _oss_client
from _doc_lookup import SKILL_TOPICS, lookup_config_topic
from _oss_client import OssClientError

# Inline contract assertion: an illegal bucket name must degrade to the
# unified OssClientError(category="invalid") -- never a bare oss2
# ClientError Traceback (measured on oss2 2.19.1: oss2.Bucket.__init__
# raises ClientError 'The bucket_name is invalid'; _build_bucket converts
# it, the entry records [WARN] + errors[] and still emits STATUS: DEGRADED
# with exit 0). No network call happens on this path.
try:
    _oss_client._build_bucket("Invalid_Bucket!", "oss-cn-hangzhou.aliyuncs.com")
    _INVALID_BUCKET_CATEGORY = "no-error"
except OssClientError as _e:
    _INVALID_BUCKET_CATEGORY = _e.category
except Exception:  # pragma: no cover - regression guard
    _INVALID_BUCKET_CATEGORY = "unexpected-traceback"
assert _INVALID_BUCKET_CATEGORY == "invalid"  # invalid: illegal bucket name


# Official-doc verification leg (read-only, help.aliyun.com only). Customer
# first questions for this skill are often advisory ("how do I add a
# watermark / can I convert to webp"), so the verification leg also runs
# when the wording carries an advisory signal, even after a conclusive
# route.
_ADVISORY_SIGNALS = (
    "怎么", "怎样", "如何", "是否", "能否", "能不能", "可以", "可不可以",
    "配置", "开通", "设置", "开启", "支持", "限制", "办法", "如何反驳",
    "how ", "how to", "can i", "is it possible", "what is", "how do",
)


def is_advisory_question(question: str) -> bool:
    """Pure check: does the customer wording look like a configuration /
    usage advisory question (as opposed to a pure error report)?"""
    if not isinstance(question, str):
        return False
    text = question.strip().lower()
    if not text:
        return False
    return any(sig in text for sig in _ADVISORY_SIGNALS)


assert is_advisory_question("图片怎么添加水印？") is True                # normal: zh signal
assert is_advisory_question("how do I convert images to webp?") is True  # normal: en signal
assert is_advisory_question("缩放参数不生效，返回原图") is False  # boundary: pure error report
assert is_advisory_question("") is False and is_advisory_question(None) is False  # invalid

# Inline contract assertion: a 404 NoSuchStyle error (measured: probing
# ?x-oss-process=style/xxx against a non-existent style) must classify as
# not_found, NOT endpoint -- the error body carries the endpoint HostId,
# which used to falsely trigger the endpoint-hint branch.
_NO_SUCH_STYLE = _oss_client.oss2.exceptions.OssError(
    404, {"x-oss-request-id": "assert"},
    b"", {"Code": "NoSuchStyle",
          "Message": "The style you get is not found.",
          "HostId": "example-bucket.oss-cn-hangzhou.aliyuncs.com"})
_NO_SUCH_STYLE_ERR = _oss_client._normalize_oss_error(
    _NO_SUCH_STYLE, "ProbeObject bucket=example-bucket key=img.jpg")
assert _NO_SUCH_STYLE_ERR.category == "not_found"  # normal: style missing
assert _NO_SUCH_STYLE_ERR.code == "NoSuchStyle"  # code preserved for hints
# boundary: a real wrong-region error still classifies as endpoint.
_WRONG_REGION = _oss_client.oss2.exceptions.OssError(
    403, {"x-oss-request-id": "assert"},
    b"", {"Code": "AccessDenied",
          "Message": "The bucket you access must be accessed using the "
                     "specified endpoint: oss-cn-beijing.aliyuncs.com"})
assert _oss_client._normalize_oss_error(
    _WRONG_REGION, "HeadObject").category == "endpoint"  # boundary: real endpoint error unaffected

# Inline contract assertion (live ticket M-I1, groupE round-3): probing
# image/resize,w_99999999 returned 400 InvalidArgument with
# EC=0040-00000312, Message 'The value: 99999999 of parameter: w is
# invalid.' -- the HostId carries the endpoint host and used to misroute
# the error to the endpoint category ("switch endpoint"). It must classify
# as process, consistent with the local process_validation verdict.
_PARAM_OUT_OF_RANGE = _oss_client.oss2.exceptions.OssError(
    400, {"x-oss-request-id": "assert"},
    b"", {"Code": "InvalidArgument",
          "Message": "The value: 99999999 of parameter: w is invalid.",
          "EC": "0040-00000312",
          "HostId": "example-bucket.oss-cn-hangzhou.aliyuncs.com"})
_PARAM_REJECT_ERR = _oss_client._normalize_oss_error(
    _PARAM_OUT_OF_RANGE,
    "GetObject bucket=example-bucket key=img.jpg x-oss-process=image/resize,w_99999999")
assert _PARAM_REJECT_ERR.category == "process"  # normal: parameter family, not endpoint
assert _PARAM_REJECT_ERR.code == "InvalidArgument"
assert "do not" in _PARAM_REJECT_ERR.hint and "endpoint" in _PARAM_REJECT_ERR.hint
# boundary: a 400 InvalidArgument WITHOUT the 0040-* EC / parameter-invalid
# signature keeps the generic invalid classification (no over-routing).
_GENERIC_400 = _oss_client.oss2.exceptions.OssError(
    400, {"x-oss-request-id": "assert"},
    b"", {"Code": "InvalidArgument",
          "Message": "The XML you provided is not well-formed."})
assert _oss_client._normalize_oss_error(
    _GENERIC_400, "PutLifecycle").category == "invalid"  # boundary: non-parameter 400 unaffected

# Inline contract assertion (live ticket B04, eval IPM-1, same family as
# M-I1): probing image/crop,x_10,y_10,w_100,h_100 against a 1x1 source
# returns 400 CutEdgeExceedRange -- NO 0040-* EC field, message "Advance
# cut's position is out of image." -- whose error body carries the bucket
# HostId (an endpoint-shaped string) that used to falsely route the error
# to the endpoint category ("switch endpoint"). The IMG-specific 400
# family must classify as process.
_CUT_EDGE = _oss_client.oss2.exceptions.OssError(
    400, {"x-oss-request-id": "assert"},
    b"", {"Code": "CutEdgeExceedRange",
          "Message": "Advance cut's position is out of image.",
          "HostId": "test-agentceping.oss-cn-hangzhou.aliyuncs.com"})
_CUT_EDGE_ERR = _oss_client._normalize_oss_error(
    _CUT_EDGE,
    "GetObject bucket=test-agentceping key=test-assets/sample.jpg "
    "x-oss-process=image/crop,x_10,y_10,w_100,h_100")
assert _CUT_EDGE_ERR.category == "process"  # normal: IMG 400 family, not endpoint
assert _CUT_EDGE_ERR.code == "CutEdgeExceedRange"  # code preserved for hints
assert "do not" in _CUT_EDGE_ERR.hint and "endpoint" in _CUT_EDGE_ERR.hint

# Same-root-cause boundary (live ticket B14): 403 UserDisable (EC
# 0003-00000801) also carries a HostId in its body and used to fall into
# the endpoint category via the HostId regex. It is an account-level
# risk-control block on the resource owner -- server side, never endpoint.
_USER_DISABLE = _oss_client.oss2.exceptions.OssError(
    403, {"x-oss-request-id": "assert"},
    b"", {"Code": "UserDisable",
          "Message": "The user is disabled.",
          "EC": "0003-00000801",
          "HostId": "nexprint-test0707.oss-cn-hangzhou.aliyuncs.com"})
_USER_DISABLE_ERR = _oss_client._normalize_oss_error(
    _USER_DISABLE, "HeadObject bucket=nexprint-test0707 key=a.jpg")
assert _USER_DISABLE_ERR.category == "server"  # boundary: account block, not endpoint
assert _USER_DISABLE_ERR.code == "UserDisable"
assert "risk control" in _USER_DISABLE_ERR.hint

# Boundary: a 400 whose body carries an endpoint-shaped HostId but whose
# code is NOT in the IMG whitelist must not be over-routed to process; it
# falls to the generic invalid/unknown path and is still never endpoint
# (HostId alone is not an endpoint signal any more).
_HOSTID_ONLY_400 = _oss_client.oss2.exceptions.OssError(
    400, {"x-oss-request-id": "assert"},
    b"", {"Code": "SomeOtherCode",
          "Message": "weird failure",
          "HostId": "test-agentceping.oss-cn-hangzhou.aliyuncs.com"})
_HOSTID_ONLY_ERR = _oss_client._normalize_oss_error(
    _HOSTID_ONLY_400, "PutObject")
assert _HOSTID_ONLY_ERR.category in ("invalid", "unknown")  # boundary: no over-routing
assert _HOSTID_ONLY_ERR.category != "endpoint"  # HostId alone must not mean endpoint

_DEFAULT_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"

# ---------------------------------------------------------------------------
# Official limits (verified against help.aliyun.com, see references/
# params-limits.md for the exact URLs and retrieval date):
#   source formats: JPG, PNG, BMP, GIF, WebP, TIFF, HEIC, AVIF
#   source size   : <= 20 MB
#   resize target : width/height <= 16384 px
#   resize percent: p in [1, 1000]
# ---------------------------------------------------------------------------
_SOURCE_LIMIT_BYTES = 20 * 1024 * 1024
_RESIZE_PIXEL_RANGE = (1, 16384)
_RESIZE_PERCENT_RANGE = (1, 1000)
_SUSPICIOUS_SMALL_BYTES = 50

SUPPORTED_SOURCE_MIMES = {
    "image/jpeg", "image/jpg", "image/png", "image/bmp", "image/gif",
    "image/webp", "image/tiff", "image/heic", "image/heif", "image/avif",
}

# Official new-version action set (help.aliyun.com image processing overview)
KNOWN_ACTIONS = {
    "resize", "watermark", "crop", "quality", "format", "info",
    "auto-orient", "circle", "indexcrop", "rounded-corners", "blur",
    "rotate", "interlace", "average-hue", "bright", "sharpen", "contrast",
}
RESIZE_MODES = {"lfit", "mfit", "fill", "pad", "fixed"}
FORMAT_TARGETS = {"jpg", "jpeg", "png", "bmp", "gif", "webp", "tiff",
                  "heic", "heif", "avif"}
# Actions that take no key-value parameters at all
NO_PARAM_ACTIONS = {"info", "average-hue", "auto-orient"}


# ---------------------------------------------------------------------------
# Pure function 1: x-oss-process string validation (offline, no network).
# Each pure function carries inline boundary assertions:
# normal / boundary / invalid inputs.
# ---------------------------------------------------------------------------

def _is_pos_int(text: str) -> bool:
    return text.isdigit() and int(text) > 0


def _in_range(text: str, lo: int, hi: int) -> bool:
    return text.isdigit() and lo <= int(text) <= hi


assert _is_pos_int("1") and _is_pos_int("16384")  # normal
assert not _is_pos_int("0") and not _is_pos_int("-3")  # boundary/invalid
assert not _is_pos_int("12.5") and not _is_pos_int("")  # invalid
assert _in_range("16384", 1, 16384) and _in_range("1", 1, 16384)  # boundary
assert not _in_range("16385", 1, 16384) and not _in_range("0", 1, 16384)  # invalid


def _check_resize_pairs(pairs, issues) -> None:
    """Validate the key_value pairs of one image/resize,... segment."""
    seen = set()
    for key, value in pairs:
        seen.add(key)
        if key in ("w", "h", "l", "s"):
            if not _in_range(value, *_RESIZE_PIXEL_RANGE):
                issues.append(
                    f"resize {key}={value!r} out of range: official range "
                    f"is [{_RESIZE_PIXEL_RANGE[0]},{_RESIZE_PIXEL_RANGE[1]}] "
                    "px, positive integer")
        elif key == "p":
            if not _in_range(value, *_RESIZE_PERCENT_RANGE):
                issues.append(
                    f"resize p={value!r} out of range: official range is "
                    f"[{_RESIZE_PERCENT_RANGE[0]},{_RESIZE_PERCENT_RANGE[1]}] "
                    "(percentage), positive integer")
        elif key == "m":
            if value not in RESIZE_MODES:
                issues.append(
                    f"resize m={value!r} invalid: official modes are "
                    f"{sorted(RESIZE_MODES)}")
        elif key in ("limit", "e"):
            # Official resize switches: limit_0/limit_1 (whether to enlarge
            # when the target resolution exceeds the source, default 1 =
            # return the original, i.e. resize never enlarges by default)
            # and e_0/e_1 (long-edge / short-edge priority).
            if value not in ("0", "1"):
                issues.append(
                    f"resize {key}={value!r} invalid: official values are "
                    "0 or 1")
        elif key == "color":
            v = value.lower()
            if not (len(v) == 6
                    and all(c in "0123456789abcdef" for c in v)):
                issues.append(
                    f"resize color={value!r} invalid: expect a 6-digit RGB "
                    "hex value such as FF0000")
        elif key not in ("w", "h", "l", "s", "p", "m", "limit", "e",
                        "color"):
            issues.append(
                f"resize: unknown parameter {key!r}; official parameters "
                "are w, h, l, s, p, m, limit, e, color (warn)")


def _validate_format_segment(action: str, tokens: list, issues: list) -> None:
    """Validate the bare-value tokens of an image/format,... segment.

    Official syntax (help.aliyun.com 图片格式转换, convert-image-formats-2.md):
    the format action takes ONE bare target value, e.g. image/format,webp
    or chained image/resize,w_100/format,jpg. The f_<target> key_value form
    is NOT official: live OSS rejects it with 400 InvalidArgument EC
    0040-00000206 ("The value: f of parameter: f is invalid.", measured
    2026-09-02 on bucket test-agentceping for f_png/f_jpg/f_webp/f_bmp and
    chained forms), while the bare form returns 200.
    """
    if not tokens:
        issues.append(
            "format: requires a bare target value, e.g. image/format,webp "
            "(official form; see convert-image-formats-2.md)")
        return
    for token in tokens:
        low = token.lower()
        if low.startswith("f_"):
            issues.append(
                f"format: {token!r} uses the f_<target> form, which live OSS "
                "rejects with 400 InvalidArgument EC 0040-00000206; the "
                f"official syntax is the bare value: format,{low[2:]}")
            if low[2:] not in FORMAT_TARGETS:
                issues.append(
                    f"format: {low[2:]!r} is not a legal target either; "
                    f"official targets are {sorted(FORMAT_TARGETS)}")
        elif low not in FORMAT_TARGETS:
            issues.append(
                f"format: {token!r} is not a legal target; official targets "
                f"are {sorted(FORMAT_TARGETS)} (bare value form, no f_ "
                "prefix)")


def _validate_rotate_segment(tokens: list, issues: list) -> None:
    """Validate the bare-value tokens of an image/rotate,... segment.

    Official syntax (help.aliyun.com/zh/oss/user-guide/rotate): rotate takes a
    SINGLE BARE angle value in [0,360] (clockwise), e.g. image/rotate,90 --
    NOT a key_value form. The a_<angle> form and any non-numeric / out-of-range
    value are rejected live with 400 InvalidArgument EC 0040-00000217
    ("rotate operator parameter format illegal"). Measured 2026-09-07 on bucket
    test-agentceping: image/rotate,90 and image/rotate,70 -> 200; while
    image/rotate,a_90, image/rotate,abc and image/rotate,400 -> 400 EC
    0040-00000217. This mirrors the IPM-2 format inversion: the validator must
    match live behaviour in BOTH directions.
    """
    if not tokens:
        issues.append(
            "rotate: requires a bare angle value, e.g. image/rotate,90 "
            "(official form; range [0,360] clockwise)")
        return
    if len(tokens) > 1:
        issues.append(
            f"rotate: takes exactly ONE bare angle value; got {tokens!r} "
            "(official form is image/rotate,90)")
        return
    token = tokens[0]
    if "_" in token:
        low = token.lower()
        if low.startswith("a_") and _in_range(low[2:], 0, 360):
            issues.append(
                f"rotate: {token!r} uses the a_<angle> key_value form, which "
                "live OSS rejects with 400 InvalidArgument EC 0040-00000217; "
                f"the official syntax is the bare value: rotate,{low[2:]}")
        else:
            issues.append(
                f"rotate: {token!r} is not a bare angle; the official syntax "
                "is image/rotate,<angle> with angle in [0,360] (live OSS "
                "rejects the key_value form with EC 0040-00000217)")
        return
    if not token.isdigit():
        issues.append(
            f"rotate: angle {token!r} is not a non-negative integer; the "
            "official syntax is image/rotate,<angle> (EC 0040-00000217)")
        return
    if not _in_range(token, 0, 360):
        issues.append(
            f"rotate: angle {token!r} out of range; official range is [0,360] "
            "degrees clockwise (EC 0040-00000217)")
        return


def _validate_action_segment(segment: str, issues: list) -> None:
    """Validate one 'action,key_value,key_value' segment of image/... ."""
    parts = segment.split(",")
    action = parts[0].strip()
    if not action:
        issues.append("empty action name in segment")
        return
    if action not in KNOWN_ACTIONS:
        issues.append(
            f"unknown action {action!r}; official actions are: "
            f"{', '.join(sorted(KNOWN_ACTIONS))}")
        return
    # The format and rotate actions take a BARE value (not key_value): the
    # official syntax is image/format,webp and image/rotate,90. Validate them
    # before the generic key_value loop so the bare forms are accepted.
    if action == "format":
        tokens = [t.strip() for t in parts[1:] if t.strip()]
        _validate_format_segment(action, tokens, issues)
        return
    if action == "rotate":
        tokens = [t.strip() for t in parts[1:] if t.strip()]
        _validate_rotate_segment(tokens, issues)
        return
    pairs = []
    for token in parts[1:]:
        token = token.strip()
        if not token:
            continue
        if "_" not in token:
            issues.append(
                f"{action}: parameter {token!r} must use the key_value form")
            continue
        key, _, value = token.partition("_")
        pairs.append((key, value))

    if action in NO_PARAM_ACTIONS and pairs:
        issues.append(f"{action}: takes no key_value parameters")
        return
    if action == "resize":
        _check_resize_pairs(pairs, issues)
        return
    if action == "quality":
        # Official semantics (help.aliyun.com 质量变换, adjust-image-quality.md):
        # q = RELATIVE quality (percent of the source quality), Q = ABSOLUTE
        # quality (never compresses below the source quality); range [1,100];
        # effective only for lossy JPG/WebP sources -- PNG and other lossless
        # formats are unaffected.
        for key, value in pairs:
            if key not in ("q", "Q") or not _in_range(value, 1, 100):
                issues.append(
                    "quality: use quality,q_<1-100> (relative, percent of "
                    "source quality) or quality,Q_<1-100> (absolute, JPG/"
                    f"WebP only; PNG unaffected); got {key}={value!r}")
        return
    if action == "interlace":
        for key, value in pairs:
            if value not in ("0", "1"):
                issues.append(
                    f"interlace: value must be 0 or 1; got {key}={value!r}")
        return
    if action == "sharpen":
        for key, value in pairs:
            if not _in_range(value, 50, 399):
                issues.append(
                    f"sharpen: value range is [50,399]; got "
                    f"{key}={value!r}")
        return
    if action in ("bright", "contrast"):
        for key, value in pairs:
            v = value.lstrip("-")
            if not (v.isdigit() and -100 <= int(value) <= 100):
                issues.append(
                    f"{action}: value range is [-100,100]; got "
                    f"{key}={value!r}")
        return
    if action == "blur":
        for key, value in pairs:
            if key == "r" and not _in_range(value, 1, 50):
                issues.append(f"blur r={value!r}: range is [1,50]")
            elif key == "s" and not _in_range(value, 1, 50):
                issues.append(f"blur s={value!r}: range is [1,50]")
        return
    # crop / circle / rounded-corners / indexcrop / watermark: parameters
    # vary widely by official spec; validate shape only (non-empty values,
    # positive integers for pixel-valued keys).
    for key, value in pairs:
        if not value:
            issues.append(f"{action}: parameter {key!r} has an empty value")
        elif key in ("w", "h", "x", "y", "r") and not _is_pos_int(value):
            if action != "crop" or not value.startswith("-"):
                issues.append(
                    f"{action} {key}={value!r}: expect a positive integer "
                    "(warn)")


def validate_process_string(process: str) -> dict:
    """Validate an x-oss-process value OFFLINE (pure function, no network).

    Accepted official forms:
      image/<action>,<key_value>[/<action>,<key_value>...]
      style/<style-name>
    Returns {"valid": bool, "form": "image"|"style"|"unknown",
             "issues": [str]} -- issues with a trailing "(warn)" are
    non-blocking observations.
    """
    issues: list = []
    raw = (process or "").strip()
    if not raw:
        return {"valid": False, "form": "unknown",
                "issues": ["empty x-oss-process value"]}
    if raw.startswith("style/"):
        style_name = raw[len("style/"):]
        if not style_name or "/" in style_name or style_name.strip() != style_name:
            issues.append(
                "style/<style-name>: style name must be non-empty and "
                "contain no slash/whitespace -- the style must already "
                "exist in the bucket console (this skill never creates "
                "styles; verify it was saved)")
        return {"valid": not issues, "form": "style", "issues": issues}
    if not raw.startswith("image/"):
        return {"valid": False, "form": "unknown",
                "issues": ["x-oss-process must start with 'image/' or "
                           "'style/'"]}
    body = raw[len("image/"):]
    if not body:
        return {"valid": False, "form": "image",
                "issues": ["'image/' carries no action"]}
    for segment in body.split("/"):
        _validate_action_segment(segment, issues)
    blocking = [i for i in issues if not i.endswith("(warn)")]
    return {"valid": not blocking, "form": "image", "issues": issues}


assert validate_process_string("image/resize,w_300")["valid"]  # normal
assert validate_process_string(
    "image/resize,m_fixed,w_100,h_100/rotate,90")["valid"]  # normal multi
assert validate_process_string("style/small")["valid"]  # normal style form
assert validate_process_string("image/resize,w_16384")["valid"]  # boundary max
assert not validate_process_string("image/resize,w_16385")["valid"]  # range
assert not validate_process_string("image/resize,p_0")["valid"]  # range
assert not validate_process_string("image/resize,m_stretch")["valid"]  # mode
assert not validate_process_string("image/resiz,w_100")["valid"]  # typo action
assert not validate_process_string("video/resize,w_100")["valid"]  # bad prefix
assert not validate_process_string("")["valid"]  # invalid: empty
assert not validate_process_string("style/")["valid"]  # invalid: no style name
assert validate_process_string(
    "image/resize,w_300,bogus_1")["valid"] is False or \
    any("(warn)" in i for i in validate_process_string(
        "image/resize,w_300,bogus_1")["issues"])  # unknown param -> warning

# IPM-2 contract: the OFFICIAL format syntax is the bare value form
# (convert-image-formats-2.md; live-probed 200 for format,webp/png/jpg/heic
# on 2026-09-02, bucket test-agentceping), while the f_<target> form is
# rejected by live OSS with 400 EC 0040-00000206 -- the validator must match
# live behavior in BOTH directions (it used to accept f_webp and reject the
# bare form, sending users toward a request that always fails online).
assert validate_process_string("image/format,webp")["valid"]  # normal: official bare form
assert validate_process_string(
    "image/resize,w_100/format,jpg")["valid"]  # normal: official chained form
assert not validate_process_string("image/format,f_webp")["valid"]  # invalid: f_ form rejected live (EC 0040-00000206)
assert not validate_process_string("image/format,f_mp4")["valid"]  # invalid: f_ + bad target
assert not validate_process_string("image/format,mp4")["valid"]  # invalid: bad target
assert not validate_process_string("image/format")["valid"]  # invalid: no target
_f_webp_issues = validate_process_string("image/format,f_webp")["issues"]
assert any("0040-00000206" in i and "format,webp" in i
           for i in _f_webp_issues)  # f_ issue must name the official fix
# K2 contract: quality q = relative, Q = absolute, official range [1,100].
assert validate_process_string("image/quality,q_90")["valid"]  # normal: relative
assert validate_process_string("image/quality,Q_90")["valid"]  # normal: absolute
assert not validate_process_string("image/quality,q_0")["valid"]  # boundary: below [1,100]
assert not validate_process_string("image/quality,q_101")["valid"]  # boundary: above [1,100]
assert not validate_process_string("image/quality,x_90")["valid"]  # invalid: bad key
_q_issue = validate_process_string("image/quality,q_0")["issues"][0]
assert "relative" in _q_issue and "absolute" in _q_issue  # official semantics
# K1 contract: resize knows the official limit/e switches.
assert validate_process_string(
    "image/resize,w_1500,h_1125,limit_0")["valid"]  # normal: explicit enlarge
assert not validate_process_string("image/resize,limit_2")["valid"]  # invalid: limit 0/1 only
# Rotate contract (live-verified 2026-09-07 on bucket test-agentceping): the
# OFFICIAL rotate syntax is the BARE angle image/rotate,90 (live 200); the
# a_<angle> key_value form and non-numeric / out-of-range values are rejected
# live with 400 InvalidArgument EC 0040-00000217 -- the validator must match
# live behaviour in BOTH directions (it used to accept a_90 and reject the
# bare 90, the same inversion class as IPM-2 format).
assert validate_process_string("image/rotate,90")["valid"]  # normal: official bare form (live 200)
assert validate_process_string("image/rotate,0")["valid"]  # boundary: min angle
assert validate_process_string("image/rotate,360")["valid"]  # boundary: max angle
assert validate_process_string(
    "image/resize,w_100/format,jpg/rotate,90")["valid"]  # normal: chained bare form
assert not validate_process_string("image/rotate,a_90")["valid"]  # invalid: a_ form rejected live (EC 0040-00000217)
assert not validate_process_string("image/rotate,361")["valid"]  # invalid: above [0,360]
assert not validate_process_string("image/rotate,abc")["valid"]  # invalid: non-numeric
assert not validate_process_string("image/rotate")["valid"]  # invalid: no angle
_rot_a_issues = validate_process_string("image/rotate,a_90")["issues"]
assert any("0040-00000217" in i and "rotate,90" in i
           for i in _rot_a_issues)  # a_ issue must name the official bare fix


# ---------------------------------------------------------------------------
# Pure function 2: magic-number identification (leading bytes -> format)
# ---------------------------------------------------------------------------

_MAGIC_TABLE = (
    # (format, predicate on the header bytes)
    ("png", lambda b: b[:8] == b"\x89PNG\r\n\x1a\n"),
    ("jpeg", lambda b: b[:3] == b"\xff\xd8\xff"),
    ("gif", lambda b: b[:4] == b"GIF8"),
    ("webp", lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP"),
    ("bmp", lambda b: b[:2] == b"BM"),
    ("tiff", lambda b: b[:4] in (b"II*\x00", b"MM\x00*")),
    ("heic", lambda b: b[4:8] == b"ftyp" and b[8:12] in
        (b"heic", b"heix", b"hevc", b"mif1")),
    ("avif", lambda b: b[4:8] == b"ftyp" and b[8:12] in (b"avif", b"avis")),
)


def identify_format(header: bytes) -> str:
    """Identify the real image format from the leading bytes (magic number).

    Returns one of: png, jpeg, gif, webp, bmp, tiff, heic, avif,
    placeholder (all-zero / trivial single-char text content), unknown.
    """
    if header is None or len(header) == 0:
        return "unknown"
    if header == b"\x00" * len(header):
        return "placeholder"
    if len(header) == 1 and 0x20 <= header[0] <= 0x7e:
        return "placeholder"
    if header[:8].strip() and all(0x20 <= c <= 0x7e for c in header[:8]) \
            and not header.startswith(b"GIF8") and not header.startswith(b"BM"):
        # printable ASCII head that matches no magic -> not binary image data
        for fmt, check in _MAGIC_TABLE:
            if check(header):
                return fmt
        return "unknown"
    for fmt, check in _MAGIC_TABLE:
        if check(header):
            return fmt
    return "unknown"


assert identify_format(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8) == "png"  # normal
assert identify_format(b"\xff\xd8\xff\xe0JFIF") == "jpeg"  # normal
assert identify_format(b"GIF89a\x01\x00") == "gif"  # normal
assert identify_format(b"RIFF\x24\x00\x00\x00WEBPVP8 ") == "webp"  # normal
assert identify_format(b"BM\x36\x10") == "bmp"  # normal
assert identify_format(b"II*\x00\x08\x00") == "tiff"  # normal
assert identify_format(b"\x00\x00\x00\x18ftypheic") == "heic"  # normal
assert identify_format(b"\x00\x00\x00\x1cftypavif") == "avif"  # normal
assert identify_format(b"1") == "placeholder"  # boundary: 1-byte '1'
assert identify_format(b"\x00\x00\x00\x00") == "placeholder"  # boundary zeros
assert identify_format(b"hello wo") == "unknown"  # invalid: plain text
assert identify_format(b"") == "unknown"  # invalid: empty


# ---------------------------------------------------------------------------
# Pure function 3: declared mime-type / size screening (SOP steps 1+2)
# ---------------------------------------------------------------------------

def mime_is_supported(mime: str) -> bool:
    """True when the declared Content-Type is an official source format."""
    m = (mime or "").strip().lower()
    if not m:
        return False
    m = m.split(";", 1)[0].strip()
    return m in SUPPORTED_SOURCE_MIMES


assert mime_is_supported("image/jpeg")  # normal
assert mime_is_supported("IMAGE/PNG; charset=binary")  # boundary: case+params
assert not mime_is_supported("video/mp4")  # invalid: video
assert not mime_is_supported("application/pdf")  # invalid: non-image
assert not mime_is_supported("")  # invalid: empty


def size_screen(content_length: int) -> str:
    """Screen the object size against the official source limit.

    Returns ok | suspicious_small | over_limit.
    """
    if content_length < 0:
        return "suspicious_small"
    if content_length > _SOURCE_LIMIT_BYTES:
        return "over_limit"
    if content_length < _SUSPICIOUS_SMALL_BYTES:
        return "suspicious_small"
    return "ok"


assert size_screen(102400) == "ok"  # normal
assert size_screen(20 * 1024 * 1024) == "ok"  # boundary: exactly 20 MB
assert size_screen(20 * 1024 * 1024 + 1) == "over_limit"  # boundary: 20MB+1
assert size_screen(1) == "suspicious_small"  # invalid: placeholder-like
assert size_screen(-1) == "suspicious_small"  # invalid: negative


def cross_verdict(mime_supported: bool, magic_format: str,
                  declared_mime: str) -> str:
    """Cross-check declared Content-Type against the real magic format.

    Returns magic_ok | magic_mismatch | placeholder_content | unknown_magic
    | mime_unsupported.
    """
    if not mime_supported:
        return "mime_unsupported"
    if magic_format == "placeholder":
        return "placeholder_content"
    if magic_format == "unknown":
        return "unknown_magic"
    declared = (declared_mime or "").split(";", 1)[0].strip().lower()
    declared = {"image/jpg": "jpeg", "image/heif": "heic"}.get(
        declared, declared.replace("image/", ""))
    if declared in ("jpeg", "jpg"):
        declared = "jpeg"
    if declared == magic_format:
        return "magic_ok"
    return "magic_mismatch"


assert cross_verdict(True, "png", "image/png") == "magic_ok"  # normal
assert cross_verdict(True, "jpeg", "image/png") == "magic_mismatch"  # mismatch
assert cross_verdict(True, "placeholder", "image/png") == "placeholder_content"
assert cross_verdict(True, "unknown", "image/png") == "unknown_magic"
assert cross_verdict(False, "unknown", "video/mp4") == "mime_unsupported"


def _process_error_flavor(code: str, hint: str) -> str:
    """Classify a process-category render error: "source" or "parameter".

    Eval IPM-3: the blanket NEXT_ACTION wording ("image processing
    rejected the source ...") sent PARAMETER-error users to inspect their
    source image, contradicting the parameter hint recorded in the same
    JSON. Flavor split by the normalized error signature:
      * source    -- the render probe hit the "not processable as an
                     image" family (code BadRequest / hint "source object
                     is not processable", EC 0040-00000005): the
                     three-step source SOP applies (verify Content-Type,
                     size, magic bytes);
      * parameter -- every other process error (InvalidArgument with an
                     0040-* EC, MissingArgument, CutEdgeExceedRange,
                     WatermarkError, ImageTooLarge, MemLimitExceeded,
                     BadWebPImage, NotImplemented): correct the
                     x-oss-process parameters per references/
                     params-limits.md.
    """
    c = (code or "").strip().lower() if isinstance(code, str) else ""
    h = (hint or "").lower() if isinstance(hint, str) else ""
    if c == "badrequest" or "source object is not processable" in h:
        return "source"
    return "parameter"


assert _process_error_flavor(
    "BadRequest", "The source object is not processable as an image"
) == "source"  # normal: A12 non-image source (EC 0040-00000005)
assert _process_error_flavor(
    "InvalidArgument", "An x-oss-process parameter value is outside"
) == "parameter"  # normal: A13/B02 out-of-range parameter
assert _process_error_flavor(
    "MissingArgument", "") == "parameter"  # normal: B01 missing parameter
assert _process_error_flavor(
    "CutEdgeExceedRange", "") == "parameter"  # normal: B04 crop bounds
assert _process_error_flavor("", "") == "parameter"  # boundary: default
assert _process_error_flavor(None, None) == "parameter"  # invalid: non-str


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _endpoint_from_location(location: str) -> str:
    loc = (location or "").strip().lower()
    if not loc:
        return ""
    if loc.startswith("oss-"):
        return f"{loc}.aliyuncs.com"
    return f"oss-{loc}.aliyuncs.com"


def build_recommendations(verdicts: dict, process_validation: dict,
                          forced_download: bool) -> list:
    """Evidence-based recommendations (manual guidance; nothing is applied)."""
    recs = []
    cross = verdicts.get("cross")
    if verdicts.get("size_screen") == "over_limit":
        recs.append(
            "The source object exceeds the official 20 MB image-processing "
            "limit; compress or resize the source before upload, or request "
            "a quota increase via a support ticket.")
    if cross == "mime_unsupported":
        recs.append(
            f"The declared Content-Type "
            f"({verdicts.get('content_type')!r}) is not an image type; OSS "
            "image processing supports only JPG/PNG/BMP/GIF/WebP/TIFF/HEIC/"
            "AVIF sources. Video or document files cannot be processed -- "
            "use a media processing service for video instead.")
    if cross == "placeholder_content":
        recs.append(
            "The object content is a placeholder (trivial text/all-zero "
            "bytes), not real image data -- the upload code stored a "
            "placeholder instead of the image bytes; re-upload the correct "
            "file.")
    if cross == "magic_mismatch":
        recs.append(
            "The real format (magic number) differs from the declared "
            "Content-Type -- the file was likely renamed or uploaded with a "
            "wrong Content-Type; re-upload with the correct Content-Type.")
    if cross == "unknown_magic":
        recs.append(
            "The leading bytes match no known image magic number -- the "
            "content is corrupted or truncated; re-upload the original "
            "image.")
    if process_validation and not process_validation.get("valid"):
        recs.append(
            "The x-oss-process string is invalid; fix the parameter issues "
            "listed in process_validation.issues before retrying -- invalid "
            "parameters make the processing request fail or be ignored.")
    if process_validation and process_validation.get("form") == "style":
        recs.append(
            "Style-based access requires the style to exist in the bucket "
            "(max 50 styles per bucket); if it was never saved or was "
            "deleted, the request cannot apply it. Verify/recreate the "
            "style manually in the OSS console -- this skill cannot create "
            "styles (read-only).")
    if forced_download:
        recs.append(
            "The processed/original image is served with "
            "Content-Disposition: attachment when accessed through the OSS "
            "default domain, so browsers download it instead of previewing. "
            "Bind a custom domain (CNAME) to the bucket, or serve via CDN, "
            "or add response-content-disposition=inline on signed URLs.")
    if not recs:
        recs.append(
            "No anomaly found in the checked dimensions; if a specific "
            "rendering still misbehaves, compare the probe response headers "
            "and re-run with the exact x-oss-process string used by the "
            "client.")
    return recs


assert isinstance(build_recommendations({}, {}, False), list)  # boundary empty
assert any("20 MB" in r for r in build_recommendations(
    {"size_screen": "over_limit"}, {}, False))  # normal: over limit
assert any("Content-Disposition" in r for r in build_recommendations(
    {}, {}, True))  # normal: forced download
assert any("placeholder" in r for r in build_recommendations(
    {"cross": "placeholder_content", "content_type": "image/png"}, {}, False))


def _emit(report: dict, status: str, next_action: str, question: str = "") -> int:
    """Print the structured report + STATUS/NEXT_ACTION contract lines.
    When --question is supplied and the run is inconclusive or advisory,
    attach the official-doc verification leg (never changes STATUS /
    NEXT_ACTION and never raises)."""
    if question and (status != "OK" or is_advisory_question(question)):
        report["doc_verification"] = lookup_config_topic(
            question, SKILL_TOPICS)
    report["status"] = status
    report["next_action"] = next_action
    # bytes are not JSON serializable -- the probe body is exported as hex
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"STATUS: {status}")
    print(f"NEXT_ACTION: {next_action}")
    if question and "doc_verification" in report:
        # Human-readable Doc verification tail (spec section 2.4).
        dv = report["doc_verification"]
        if dv.get("matched"):
            print("Doc verification: matched via official OSS docs "
                  "(llms-index):")
            for doc in dv["docs"]:
                print(f"  - {doc['title']}: {doc['url']}")
        else:
            print("Doc verification: DEGRADED (offline) — conclusions are "
                  "based on embedded knowledge only.")
    return 0 if status in ("OK", "DEGRADED") else 1



def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose OSS image processing issues "
                    "(x-oss-process validation, rendering attribution, "
                    "source verification) -- read-only",
    )
    parser.add_argument("--bucket", default="",
                        help="OSS bucket name (required together with "
                             "--object for live probes)")
    parser.add_argument("--object", dest="object_key", default="",
                        help="Object key of the image to inspect")
    parser.add_argument("--process", default="",
                        help="x-oss-process value to validate and/or probe "
                             "(e.g. image/resize,w_300 or style/small)")
    parser.add_argument("--endpoint", default="",
                        help="Endpoint of the bucket region (optional; "
                             "auto-derived from GetBucketInfo otherwise)")
    parser.add_argument("--region", default="",
                        help="Region hint used to derive the query endpoint "
                             "when --endpoint is absent")
    parser.add_argument("--question", default="",
                        help="Customer's original question wording; enables "
                             "the official-doc verification leg "
                             "(doc_verification section in the JSON)")
    args = parser.parse_args()
    question = args.question.strip() if isinstance(args.question, str) else ""

    # UA-SKILL-VERSION: read and validate the skill version from
    # references/manifest.json BEFORE the first cloud call of this run. The
    # version is never invented, guessed or reused -- a missing or invalid
    # manifest stops the run (STATUS: FAIL, exit 1) with no cloud call made.
    try:
        _oss_client.skill_version()
    except _oss_client.SkillVersionError as e:
        sys.exit(_emit(
            {"skill": "alibabacloud-oss-image-processing-diagnosis",
             "bucket": args.bucket or None,
             "errors": [{"category": "invalid_arguments",
                         "code": "SkillVersionUnavailable",
                         "message": str(e)[:200]}],
             "auto_filled": []}, "FAIL",
            "Fix this skill's references/manifest.json (a valid `version` "
            "field is required to build the User-Agent); no cloud call was "
            "made and no conclusion can be drawn without it.", question))

    if not args.process and not (args.bucket and args.object_key):
        # Contract instead of a bare usage error: tell the caller exactly which
        # input is missing and what this credential can already see.
        _hint = []
        try:
            _hint = [b["name"] for b in _oss_client.list_buckets()][:30]
        except Exception as e:
            print(f"[WARN] ListBuckets bucket-name hint degraded: {e}",
                  file=sys.stderr)
        _rep = {"skill": "alibabacloud-oss-image-processing-diagnosis",
                "bucket": args.bucket, "buckets_in_account": _hint,
                "errors": [], "auto_filled": []}
        sys.exit(_emit(_rep, "FAIL",
                       "Ask the user for an x-oss-process parameter to "
                       "validate offline, or for the bucket plus object key to "
                       "probe live; buckets_in_account lists buckets visible "
                       "to the current credential.", question))

    auto_filled = []
    uid = _oss_client.resolve_uid()

    report = {
        "skill": "alibabacloud-oss-image-processing-diagnosis",
        "identity": {"uid": uid,
                     "note": "derived via sts get-caller-identity; empty "
                             "means the identity pre-check degraded"},
        "bucket": args.bucket or None,
        "object": args.object_key or None,
        "process_string": args.process or None,
        "process_validation": None,
        "bucket_info": None,
        "object_meta": None,
        "source_screen": None,
        "render_probe": None,
        "forced_download": False,
        "auto_filled": auto_filled,
        "recommendations": [],
        "errors": [],
    }
    if question:
        report["question"] = question

    degraded = False

    # Step 1 (offline, deterministic): x-oss-process syntax validation.
    if args.process:
        report["process_validation"] = validate_process_string(args.process)

    # Step 2: resolve the bucket region endpoint for live probes.
    probe_endpoint = args.endpoint.strip().lower() if args.endpoint else ""
    if args.bucket:
        query_endpoint = probe_endpoint
        if not query_endpoint:
            if args.region.strip():
                query_endpoint = f"oss-{args.region.strip().lower()}.aliyuncs.com"
                auto_filled.append(
                    f"query endpoint derived from --region: {query_endpoint}")
            else:
                query_endpoint = _DEFAULT_ENDPOINT
                auto_filled.append(
                    f"query endpoint auto-defaulted to {query_endpoint} "
                    "(no --endpoint/--region provided)")
        try:
            info = _oss_client.get_bucket_info(args.bucket, query_endpoint)
            report["bucket_info"] = info
            derived = _endpoint_from_location(info.get("location", ""))
            if derived and derived != query_endpoint:
                auto_filled.append(
                    f"probe endpoint derived from bucket location "
                    f"{info.get('location')}: {derived}")
                probe_endpoint = derived
            else:
                probe_endpoint = query_endpoint
        except OssClientError as e:
            print(f"[WARN] GetBucketInfo degraded ({e.category}): {e}",
                  file=sys.stderr)
            report["errors"].append(e.to_dict())
            degraded = True
            probe_endpoint = query_endpoint
            # Fallback: locate the bucket region via ListBuckets.
            try:
                located = _oss_client.list_buckets(prefix=args.bucket)
                hits = [b for b in located if b["name"] == args.bucket]
                if hits:
                    derived = _endpoint_from_location(hits[0]["location"])
                    report["bucket_info"] = {
                        "name": hits[0]["name"],
                        "location": hits[0]["location"],
                        "source": "ListBuckets fallback "
                                  "(GetBucketInfo degraded)",
                    }
                    if derived:
                        probe_endpoint = derived
            except OssClientError as e2:
                print(f"[WARN] ListBuckets fallback degraded "
                      f"({e2.category}): {e2}", file=sys.stderr)
                report["errors"].append(e2.to_dict())

    # Step 3: source screening SOP -- mime_type (step 1) + object_size
    # (step 2) via HeadObject.
    verdicts: dict = {}
    if args.bucket and args.object_key:
        try:
            meta = _oss_client.head_object_meta(
                args.bucket, probe_endpoint, args.object_key)
            report["object_meta"] = meta
            mime_ok = mime_is_supported(meta["content_type"])
            screen = size_screen(meta["content_length"])
            verdicts = {
                "content_type": meta["content_type"],
                "content_length": meta["content_length"],
                "mime_supported": mime_ok,
                "size_screen": screen,
            }
            report["source_screen"] = dict(verdicts)

            # Step 4 (SOP step 3): magic-number verification -- range GET
            # of the leading bytes of the ORIGINAL object (read-only).
            if screen != "over_limit":
                try:
                    head = _oss_client.probe_object(
                        args.bucket, probe_endpoint, args.object_key,
                        byte_range=(0, 15))
                    fmt = identify_format(head["body"])
                    verdicts["magic_format"] = fmt
                    verdicts["magic_hex"] = head["body"].hex()
                    verdicts["cross"] = cross_verdict(
                        mime_ok, fmt, meta["content_type"])
                    report["source_screen"].update({
                        "magic_format": fmt,
                        "magic_hex": verdicts["magic_hex"][:64],
                        "cross": verdicts["cross"],
                    })
                except OssClientError as e:
                    print(f"[WARN] magic-number probe degraded "
                          f"({e.category}): {e}", file=sys.stderr)
                    report["errors"].append(e.to_dict())
                    degraded = True
        except OssClientError as e:
            print(f"[WARN] HeadObject degraded ({e.category}): {e}",
                  file=sys.stderr)
            report["errors"].append(e.to_dict())
            degraded = True
            verdicts["head_error"] = e.to_dict()

        # Step 5: rendering probe with the x-oss-process string (if any).
        if args.process:
            try:
                rendered = _oss_client.probe_object(
                    args.bucket, probe_endpoint, args.object_key,
                    process=args.process)
                disposition = rendered["content_disposition"]
                report["render_probe"] = {
                    "status": rendered["status"],
                    "content_type": rendered["content_type"],
                    "content_disposition": disposition,
                    "body_size": rendered["body_size"],
                }
                if "attachment" in disposition.lower():
                    report["forced_download"] = True
            except OssClientError as e:
                print(f"[WARN] render probe degraded ({e.category}): {e}",
                      file=sys.stderr)
                report["errors"].append(e.to_dict())
                degraded = True
                report["render_probe"] = {
                    "status": e.status, "code": e.code,
                    "category": e.category, "hint": e.hint,
                }
                if e.category == "process":
                    if _process_error_flavor(e.code, e.hint) == "source":
                        verdicts["render_rejected"] = (
                            "image processing rejected the source: not a "
                            "processable image format or beyond source "
                            "limits")
                    else:
                        verdicts["render_rejected"] = (
                            "image processing rejected the request: an "
                            "x-oss-process parameter problem (bad/missing/"
                            "out-of-range parameter, or a crop region "
                            "beyond the source bounds), not a source "
                            "problem")
                if e.category == "permission":
                    verdicts["render_rejected"] = (
                        "403 on the render request: missing permission, or "
                        "original-image protection is enabled on the bucket")

    report["recommendations"] = build_recommendations(
        verdicts, report["process_validation"], report["forced_download"])

    # Step 6: status + next action.
    if args.process and not (args.bucket and args.object_key):
        pv = report["process_validation"]
        na = ("Fix the listed parameter issues and rebuild the URL as "
              "?x-oss-process=<corrected-value>."
              if not pv["valid"] else
              "The x-oss-process string is syntactically valid; if the "
              "rendering still fails, re-run with --bucket and --object to "
              "probe the source object.")
        sys.exit(_emit(report, "OK", na, question))

    live_ok = bool(verdicts.get("cross") or verdicts.get("head_error")
                   or report["render_probe"])
    if degraded or not live_ok:
        root = report["errors"][0] if report["errors"] else {}
        cat = root.get("category", "unknown")
        if cat == "not_found":
            na = ("Bucket / object / image style not found "
                  "(NoSuchBucket/NoSuchKey/NoSuchStyle); verify the bucket "
                  "name, object key and style name spelling (styles live "
                  "under the bucket's Image Processing settings) and the "
                  "owning account, then re-run.")
        elif cat == "permission":
            na = ("Access denied (403): grant the caller the read actions in "
                  "references/ram-policies.md, confirm bucket ownership, and "
                  "check whether original-image protection is enabled.")
        elif cat == "process":
            if _process_error_flavor(root.get("code", ""),
                                     root.get("hint", "")) == "source":
                na = ("Image processing rejected the source (unsupported "
                      "format or size beyond limits); follow the SOP in "
                      "references/image-processing-playbook.md to verify "
                      "the source, then re-run.")
            else:
                na = ("The x-oss-process parameters were rejected by "
                      "image processing; correct the parameter per "
                      "references/params-limits.md (an out-of-range "
                      "value, a bad/missing parameter, or a crop region "
                      "beyond the source bounds), then re-run.")
        elif cat == "credentials":
            na = ("No credentials in the environment credential chain; "
                  "configure the default credential chain, never pass AK/SK "
                  "manually.")
        else:
            na = ("Part of the diagnosis degraded; review the recorded "
                  "errors and re-run after fixing the root cause.")
        sys.exit(_emit(report, "DEGRADED", na, question))

    cross = verdicts.get("cross", "")
    if cross == "magic_ok" and not report["process_validation"] or (
            cross == "magic_ok"
            and report["process_validation"]
            and report["process_validation"]["valid"]):
        na = ("Source format and x-oss-process syntax verified; if the "
              "client still sees wrong output, compare against the probe "
              "evidence recorded in this report.")
    elif cross in ("placeholder_content", "unknown_magic", "magic_mismatch"):
        na = ("The source object content is not a valid image; re-upload the "
              "correct file (see recommendations), then re-run.")
    elif verdicts.get("size_screen") == "over_limit":
        na = ("Source exceeds the 20 MB limit; shrink the source or request "
              "a quota increase, then re-run.")
    else:
        na = ("Diagnosis completed with the recorded evidence; follow the "
              "recommendations.")
    sys.exit(_emit(report, "OK", na, question))


if __name__ == "__main__":
    main()
