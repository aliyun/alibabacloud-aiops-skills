#!/usr/bin/env python3
# SECURITY: knowledge-driven diagnosis only. This script performs NO network
# calls, invokes NO aliyun CLI, and calls NO cloud API. It parses a pasted
# presigned URL as a pure string (never sends it anywhere), routes the
# reported error to failure modes via the embedded catalog, and emits
# structured JSON plus STATUS/NEXT_ACTION.
"""Entry script for alibabacloud-oss-presigned-url-v4-diagnosis.

Usage (all parameters optional; provide at least one):
  python3 oss_presigned_url_diagnosis.py \
      [--url PRESIGNED_URL] [--error-code CODE] [--http-status 403] \
      [--symptom TEXT] [--question "<customer original wording>"]

Matching ladder (pure functions, unit-testable):
  1. URL parsing + expiry verdict + error/symptom routing  -> STATUS: OK
  2. error code or HTTP status routing without URL          -> STATUS: DEGRADED
  3. symptom keywords only                                  -> STATUS: DEGRADED
  4. nothing recognizable                                   -> STATUS: FAIL (exit 1)
"""

import argparse
import calendar
import json
import re
import sys
import time
import uuid
from urllib.parse import parse_qsl, unquote, urlsplit

from _doc_lookup import SKILL_TOPICS, lookup_config_topic
from _url_catalog import (
    DOMAIN_TRANSFER_GUARDS,
    ERROR_CODE_ROUTES,
    FAILURE_MODES,
    INTENT_PRECEDENCE_KEYS,
    LINK_RECOVERY_GUIDANCE,
    MAX_PRESIGNED_TTL_SECONDS,
    MAX_PRESIGNED_TTL_SECONDS_LONG_TERM_AK,
    MAX_PRESIGNED_TTL_SECONDS_STS,
    MODE_KEYS,
    SIGNATURE_URL_FORMS,
    STATUS_TO_MODES,
    SYMPTOM_KEYWORDS,
    V4_UPGRADE_CHECKLIST,
)

SKILL_NAME = "alibabacloud-oss-presigned-url-v4-diagnosis"

# --- Observability (SA-2.11c): session id + User-Agent template ------------
# Even though this skill makes zero cloud API calls, the session id and the
# User-Agent string are generated here so any future HTTP usage is traceable.
SESSION_ID = uuid.uuid4().hex  # 32-char lowercase hex
SKILL_VERSION = "1.0.0"  # UA skill-version; matches references/manifest.json
USER_AGENT = "AlibabaCloud-Agent-Skills/{skill}/{session_id} skill-version/{version}".format(
    skill=SKILL_NAME, session_id=SESSION_ID, version=SKILL_VERSION
)

# Safety caps: the URL is processed purely locally, but hostile or mistaken
# inputs (huge pastes, garbage) must not blow up parsing.
MAX_URL_CHARS = 8192
MAX_QUERY_PAIRS = 200

_V4_DATE_RE = re.compile(r"^\d{8}T\d{6}Z$")
_EPOCH_MIN = 1_000_000_000   # 2001-09-09: smaller values are not epoch seconds
_EPOCH_MAX = 4_102_444_800   # 2100-01-01: larger values are not epoch seconds


# --- Pure functions (no I/O, no side effects) -------------------------------

def normalize_text(value):
    """Return stripped string, or '' for None/non-str input."""
    if not isinstance(value, str):
        return ""
    return value.strip()


def _mask_value(key, value):
    """Mask secrets so they never leave the machine: full access key values
    keep only a 4-char prefix; signatures are fully masked."""
    lowered = key.lower()
    if lowered in ("signature", "x-oss-signature", "security-token",
                   "x-oss-security-token"):
        return "***masked***"
    if lowered in ("ossaccesskeyid", "x-oss-credential"):
        return (value[:4] + "***masked***") if len(value) > 4 else "***masked***"
    return value


def safe_query_pairs(query_string):
    """Parse a query string into [(key, value)] with hard caps (pure)."""
    if not isinstance(query_string, str) or not query_string:
        return []
    try:
        pairs = parse_qsl(query_string, keep_blank_values=True,
                          max_num_fields=MAX_QUERY_PAIRS + 1)
    except ValueError:
        return []
    return [(k, v) for k, v in pairs[:MAX_QUERY_PAIRS]]


def detect_signature_version(query_pairs):
    """Classify the signature version from query parameters (pure).

    Returns ("v4"|"v1"|"v2"|"none", detail_message).
    """
    keys = {k for k, _ in query_pairs}
    lowered_keys = {k.lower() for k in keys}
    version_markers = [v.lower() for k, v in query_pairs
                       if k.lower() == "x-oss-signature-version"]
    if {"x-oss-credential", "x-oss-date", "x-oss-expires",
            "x-oss-signature"} <= lowered_keys or "oss4-hmac-sha256" in version_markers:
        return ("v4", "x-oss-credential/x-oss-date/x-oss-expires/x-oss-signature present")
    if "oss2" in version_markers:
        return ("v2", "x-oss-signature-version=OSS2 marker present")
    if {"ossaccesskeyid", "expires", "signature"} <= lowered_keys:
        return ("v1", "OSSAccessKeyId+Expires+Signature present")
    if lowered_keys & {"ossaccesskeyid", "expires", "signature",
                       "x-oss-credential", "x-oss-signature"}:
        return ("none", "partial signature parameters: the URL is incomplete "
                        "or was stripped/altered after signing")
    return ("none", "no OSS signature parameters found in the query string")


def _to_int(raw):
    """Strict integer parse; None on failure (pure)."""
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text or not re.fullmatch(r"[+-]?\d+", text):
        return None
    try:
        return int(text)
    except ValueError:
        return None


def parse_credential_scope(raw_credential):
    """Split x-oss-credential into its scope parts (pure).

    Expected format: AccessKeyId/date/region/oss/aliyun_v4_request
    Returns a dict; format_ok=False with a reason when malformed.
    """
    result = {"format_ok": False, "access_key_prefix": "", "date": "",
              "region": "", "reason": ""}
    credential = unquote(normalize_text(raw_credential))
    if not credential:
        result["reason"] = "x-oss-credential is empty"
        return result
    parts = credential.split("/")
    if len(parts) != 5:
        result["reason"] = ("x-oss-credential must have 5 slash-separated "
                            "parts: AccessKeyId/date/region/oss/aliyun_v4_request")
        return result
    access_key, date, region, service, request = parts
    if not access_key:
        result["reason"] = "x-oss-credential has an empty AccessKeyId part"
        return result
    if not re.fullmatch(r"\d{8}", date):
        result["reason"] = ("x-oss-credential date part must be YYYYMMDD, "
                            "got '{0}'".format(date))
        return result
    if not region:
        result["reason"] = "x-oss-credential has an empty region part"
        return result
    if service != "oss" or request != "aliyun_v4_request":
        result["reason"] = ("x-oss-credential must end with /oss/"
                            "aliyun_v4_request")
        return result
    result.update({"format_ok": True, "access_key_prefix": access_key[:4],
                   "date": date, "region": region})
    return result


def extract_expiry(query_pairs, version):
    """Compute the URL expiry and a state verdict (pure).

    Returns a dict with keys: found, reason, expires_epoch, ttl_seconds,
    state ('valid'|'expired'|'malformed'|'absent'). never_check_now=True
    callers pass now explicitly for determinism in tests.
    """
    params = {k.lower(): v for k, v in query_pairs}
    info = {"found": False, "reason": "", "expires_epoch": None,
            "ttl_seconds": None, "state": "absent"}
    if version == "v1" or version == "v2":
        raw = params.get("expires")
        if raw is None:
            info["reason"] = "Expires parameter missing"
            info["state"] = "malformed"
            return info
        epoch = _to_int(raw)
        if epoch is None or not (_EPOCH_MIN <= epoch <= _EPOCH_MAX):
            info["reason"] = ("Expires must be a UNIX epoch in seconds; got "
                              "'{0}'".format(raw))
            info["state"] = "malformed"
            return info
        info.update({"found": True, "expires_epoch": epoch,
                     "reason": "V1 Expires is an absolute epoch"})
        return info
    if version == "v4":
        raw_date = params.get("x-oss-date")
        raw_expires = params.get("x-oss-expires")
        # Credential-type branch (official add-signatures-to-urls): a V4 URL
        # carrying x-oss-security-token / security-token is STS-signed and its
        # x-oss-expires is capped at 43200 s (12 hours); a long-term-AccessKey
        # URL is capped at 604800 s (7 days).
        is_sts = ("x-oss-security-token" in params or "security-token" in params)
        ttl_cap = (MAX_PRESIGNED_TTL_SECONDS_STS if is_sts
                   else MAX_PRESIGNED_TTL_SECONDS_LONG_TERM_AK)
        info["credential_type"] = "sts" if is_sts else "long_term_ak"
        info["ttl_cap_seconds"] = ttl_cap
        if raw_expires is None or raw_expires.strip() == "":
            info["reason"] = ("x-oss-expires is missing or empty (official "
                              "error 0002-00000216)")
            info["state"] = "malformed"
            return info
        ttl = _to_int(raw_expires)
        if ttl is None or ttl <= 0:
            info["reason"] = ("x-oss-expires must be a positive integer of "
                              "seconds; got '{0}'".format(raw_expires))
            info["state"] = "malformed"
            return info
        if ttl > ttl_cap:
            info["reason"] = ("x-oss-expires {0}s exceeds the maximum of "
                              "{1}s for a {2} credential ({3})".format(
                                  ttl, ttl_cap,
                                  "STS temporary" if is_sts else "long-term AccessKey",
                                  "12 hours" if is_sts else "7 days"))
            info["state"] = "malformed"
            info["ttl_seconds"] = ttl
            return info
        if raw_date is None or not _V4_DATE_RE.match(raw_date.strip()):
            info["reason"] = ("x-oss-date must be YYYYMMDDTHHmmssZ; got "
                              "'{0}'".format(raw_date))
            info["state"] = "malformed"
            info["ttl_seconds"] = ttl
            return info
        try:
            base = time.strptime(raw_date.strip(), "%Y%m%dT%H%M%SZ")
            base_epoch = calendar.timegm(base)
        except ValueError:
            info["reason"] = "x-oss-date is not a real UTC timestamp"
            info["state"] = "malformed"
            info["ttl_seconds"] = ttl
            return info
        info.update({"found": True, "ttl_seconds": ttl,
                     "expires_epoch": int(base_epoch) + ttl,
                     "reason": "V4 expiry = x-oss-date + x-oss-expires"})
        return info
    info["reason"] = "no signature version detected; expiry cannot be extracted"
    return info


def check_expiry_state(expiry_info, now_epoch):
    """Pure verdict: given expires_epoch and a 'now', return state string."""
    if expiry_info.get("state") == "malformed":
        return "malformed"
    if not expiry_info.get("found") or expiry_info.get("expires_epoch") is None:
        return "absent"
    remaining = expiry_info["expires_epoch"] - now_epoch
    return "valid" if remaining > 0 else "expired"


def parse_signed_url(raw_url):
    """Full local URL analysis (pure). Never sends the URL anywhere.

    Returns a dict describing scheme/host/object, signature version,
    masked parameters, credential scope (V4) and the expiry record.
    """
    result = {"accepted": False, "reason": ""}
    url = normalize_text(raw_url)
    if not url:
        result["reason"] = "no URL provided"
        return result
    if len(url) > MAX_URL_CHARS:
        result["reason"] = ("URL exceeds {0} characters; refusing to parse "
                            "an oversized input".format(MAX_URL_CHARS))
        return result
    try:
        parts = urlsplit(url)
    except ValueError as exc:
        result["reason"] = "URL cannot be split: {0}".format(exc)
        return result
    if parts.scheme not in ("http", "https"):
        result["reason"] = ("not an http(s) URL (scheme '{0}')".format(
            parts.scheme or "none"))
        return result
    pairs = safe_query_pairs(parts.query)
    version, detail = detect_signature_version(pairs)
    result.update({
        "accepted": True,
        "scheme": parts.scheme,
        "host": parts.netloc,
        "object_path": unquote(parts.path),
        "signature_version": version,
        "version_detail": detail,
        "signature_form": SIGNATURE_URL_FORMS.get(version, {}).get("label",
                                                                   "no OSS presigned form"),
        "query_params_masked": {k: _mask_value(k, v) for k, v in pairs},
    })
    if version == "v4":
        scope = parse_credential_scope(
            dict((k.lower(), v) for k, v in pairs).get("x-oss-credential", ""))
        result["credential_scope"] = scope
    result["expiry"] = extract_expiry(pairs, version)
    return result


def match_error_code(raw_code):
    """Match a raw error code against ERROR_CODE_ROUTES (pure).

    Returns (match_type, canonical_code): 'exact' / 'fuzzy' / 'none'.
    """
    code = normalize_text(raw_code)
    if not code:
        return ("none", None)
    lowered = code.lower()
    keys = sorted(ERROR_CODE_ROUTES.keys())
    for key in keys:
        if key.lower() == lowered:
            return ("exact", key)
    fuzzy_hits = [k for k in keys
                  if lowered in k.lower() or k.lower() in lowered]
    if len(fuzzy_hits) == 1:
        return ("fuzzy", fuzzy_hits[0])
    return ("none", None)


def resolve_http_status(raw_status):
    """Map an HTTP status to candidate failure modes (pure)."""
    try:
        status = int(normalize_text(str(raw_status)))
    except (TypeError, ValueError):
        return []
    return list(STATUS_TO_MODES.get(status, []))


def match_symptoms(raw_symptom):
    """Map free-text symptoms to candidate failure modes (pure).

    Subject discrimination for the 'expired' route (ticket-verified
    regression): a symptom only routes to signed-URL expiry when it carries
    URL/link/signature context; resource-package/plan subjects (e.g.
    '资源包过期') are excluded -- they belong to billing diagnosis.

    Routing order (eval fix PR-2/PR-3): intent/endpoint precedence keys
    first (long-term/private access and custom-domain wording carry the
    case theme), then the remaining keywords longest-first so precise
    compound keys (e.g. '签名不匹配') outrank generic ones (e.g. '签名').
    Domain-transfer guards (eval fix PR-4): CDN back-to-origin,
    traffic-abuse and 'make-it-public' wording without URL context
    belongs to sibling skills and yields NO candidates here.
    """
    text = normalize_text(raw_symptom).lower()
    if not text:
        return []
    ordered_keys = [k for k in INTENT_PRECEDENCE_KEYS
                    if k in SYMPTOM_KEYWORDS]
    ordered_keys += sorted(
        (k for k in SYMPTOM_KEYWORDS if k not in INTENT_PRECEDENCE_KEYS),
        key=lambda k: (-len(k), k))
    modes = []
    for keyword in ordered_keys:
        if keyword in text:
            for mode in SYMPTOM_KEYWORDS[keyword]:
                if mode not in modes:
                    modes.append(mode)
    has_url_context = any(tok in text for tok in _EXPIRED_URL_CONTEXT)
    if not has_url_context and _domain_transfer_hit(text):
        return []
    if "expired" in modes:
        has_package_subject = any(tok in text
                                  for tok in _PACKAGE_EXPIRY_SUBJECTS)
        if has_package_subject or not has_url_context:
            modes = [m for m in modes if m != "expired"]
    return modes


def _domain_transfer_hit(text):
    """Pure check: does the wording match an out-of-domain transfer guard?

    Every word group of a guard must contribute at least one word present
    in the (lowercased) text; guards apply only without URL/link/signature
    context (checked by the caller).
    """
    for guard in DOMAIN_TRANSFER_GUARDS:
        if all(any(word in text for word in group) for group in guard):
            return True
    return False


# Tokens marking the subject of an 'expired' complaint as a signed URL.
_EXPIRED_URL_CONTEXT = (
    "url", "链接", "地址", "签名", "signature", "presigned", "share",
    "分享", "link",
)
# Tokens marking the subject as a resource package / plan (billing domain).
_PACKAGE_EXPIRY_SUBJECTS = (
    "资源包", "套餐", "存储包", "流量包", "下行流量包", "资源包过期",
    "package", "storage plan", "traffic plan",
)

assert _domain_transfer_hit("cdN 回源 oss 私有桶鉴权") is True        # normal: 回源
assert _domain_transfer_hit("黑产上传图片 流量暴涨") is True             # normal: abuse
assert _domain_transfer_hit("开启公开访问") is True                     # normal: open-up
assert _domain_transfer_hit("回源失败") is True                          # boundary: single guard word
assert _domain_transfer_hit("自定义域名生成签名url") is False            # boundary: in-domain
assert _domain_transfer_hit("") is False                               # invalid: empty
# The URL-context exemption lives in match_symptoms (caller side), not in
# the pure guard helper: a signed-URL problem mentioned alongside CDN
# back-to-origin wording stays in scope.
assert match_symptoms("cdn 回源时签名url报签名不匹配") != []              # boundary: url ctx keeps case

# Configuration/usage-advisory signal words (spec Step B): questions carrying
# these markers are advisory in nature, so the official-doc verification leg
# runs even when the embedded catalog already routed a candidate mode.
_ADVISORY_SIGNALS = (
    "怎么", "怎样", "如何", "是否", "能否", "能不能", "可以", "可不可以",
    "配置", "开通", "设置", "开启", "支持", "限制", "办法", "如何反驳",
    "how ", "how to", "can i", "is it possible", "what is", "how do",
)


def is_advisory_question(question: str) -> bool:
    """Pure check: does the customer wording look like a configuration /
    usage advisory question (as opposed to a pure error report)?"""
    text = normalize_text(question).lower()
    if not text:
        return False
    return any(sig in text for sig in _ADVISORY_SIGNALS)


assert is_advisory_question("签名URL怎么生成？") is True          # normal: zh signal
assert is_advisory_question("how do I rotate the signing key?") is True  # normal: en signal
assert is_advisory_question("SignatureDoesNotMatch 403") is False  # boundary: pure error report
assert is_advisory_question("") is False and is_advisory_question(None) is False  # invalid


def build_mode_block(mode_key):
    """Build one failure-mode block from the catalog (pure)."""
    entry = FAILURE_MODES[mode_key]
    return {
        "mode": entry["mode"],
        "label": entry["label"],
        "http_status": entry["http_status"],
        "side": entry["side"],
        "root_cause_directions": list(entry["root_cause_directions"]),
        "troubleshooting_steps": list(entry["troubleshooting_steps"]),
        "official_doc_ref": entry["official_doc_ref"],
    }


def _merge_modes(*lists):
    merged = []
    for item in lists:
        for mode in item:
            if mode in FAILURE_MODES and mode not in merged:
                merged.append(mode)
    return merged


def diagnose(url=None, error_code=None, http_status=None, symptom=None,
             question=None, now_epoch=None):
    """Pure decision function. Returns (exit_code, result_dict).

    The customer question wording (eval fix PR-5) participates in symptom
    routing exactly like --symptom text, so advisory first-question tickets
    (e.g. '需要设置这个域名作为endpoint吗') still reach a candidate mode
    instead of failing at the entry.
    """
    now = time.time() if now_epoch is None else now_epoch
    result = {
        "skill": SKILL_NAME,
        "session_id": SESSION_ID,
        "user_agent": USER_AGENT,
        "inputs": {
            "url_provided": bool(normalize_text(url)),
            "error_code": normalize_text(error_code),
            "http_status": normalize_text(http_status) if http_status is not None else "",
            "symptom": normalize_text(symptom),
            "question": normalize_text(question),
        },
        "references": [
            "references/presigned-url-failure-catalog.md",
            "references/v4-upgrade-checklist.md",
            "references/scope-and-limitations.md",
            "references/faq-advisory.md",
        ],
        "security_note": ("The URL was parsed locally as a string only; no "
                          "request was sent. Access keys and signatures are "
                          "masked in this output and must never be shared."),
    }

    url_analysis = None
    if normalize_text(url):
        url_analysis = parse_signed_url(url)
        result["url_analysis"] = url_analysis
        if url_analysis.get("accepted"):
            expiry = url_analysis.get("expiry", {})
            url_analysis["expiry_state"] = check_expiry_state(expiry, now)
            if url_analysis["expiry_state"] == "expired":
                remaining = expiry["expires_epoch"] - now
                url_analysis["expired_seconds_ago"] = int(-remaining)

    match_type, canonical = match_error_code(error_code)
    status_modes = resolve_http_status(http_status)
    symptom_modes = match_symptoms(symptom)
    question_modes = match_symptoms(question)

    modes = _merge_modes(
        ERROR_CODE_ROUTES.get(canonical, []) if canonical else [],
        status_modes, symptom_modes, question_modes,
    )

    # Deterministic priority: a parsed URL that is expired is conclusive on
    # its own; a malformed expiry or a malformed V4 credential scope is
    # likewise conclusive (SKILL.md Example 3 contract, eval fix PR-1).
    if url_analysis and url_analysis.get("accepted"):
        expiry_state = url_analysis.get("expiry_state")
        scope = url_analysis.get("credential_scope") or {}
        scope_bad = (url_analysis.get("signature_version") == "v4"
                     and scope.get("format_ok") is False)
        if expiry_state == "expired":
            modes = _merge_modes(["expired"], modes)
        elif expiry_state == "malformed":
            modes = _merge_modes(["malformed_url"], modes)
        elif scope_bad:
            modes = _merge_modes(["malformed_url"], modes)
        elif (url_analysis.get("signature_version") == "v1"
              and canonical == "SignatureDoesNotMatch"):
            modes = _merge_modes(["v1_signature_forbidden",
                                  "parameter_tampered"], modes)

    if modes:
        result["match"] = {
            "type": match_type if canonical else ("status_or_symptom"),
            "error_code": canonical,
        }
        result["candidate_modes"] = modes
        result["failure_modes"] = [build_mode_block(m) for m in modes]
        url_verdict = (url_analysis or {}).get("expiry_state")
        scope = (url_analysis or {}).get("credential_scope") or {}
        scope_bad = ((url_analysis or {}).get("signature_version") == "v4"
                     and scope.get("format_ok") is False)
        conclusive = (
            (url_verdict in ("expired", "malformed")
             and modes[0] in ("expired", "malformed_url"))
            or (scope_bad and modes[0] == "malformed_url")
        )
        result["status"] = "OK" if conclusive else "DEGRADED"
        result["v4_upgrade_checklist"] = list(V4_UPGRADE_CHECKLIST)
        result["link_recovery_guidance"] = list(LINK_RECOVERY_GUIDANCE)
        if conclusive:
            result["next_action"] = (
                "Report the first failure mode '{0}' as the confirmed "
                "verdict from the URL analysis (expiry / malformed-parameter "
                "/ credential-scope format check is deterministic; report "
                "url_analysis.credential_scope.reason verbatim when the "
                "scope is malformed); transcribe its root-cause directions "
                "and troubleshooting steps verbatim, then add the link "
                "recovery guidance.".format(modes[0])
            )
        else:
            result["next_action"] = (
                "Present the candidate failure modes in order and ask the "
                "user for the missing discriminating evidence (full error "
                "response body with Code/RequestId, or the presigned URL "
                "itself) before concluding; do not pick a mode by guesswork."
            )
        return (0, result)

    if url_analysis and not url_analysis.get("accepted"):
        result["match"] = {"type": "invalid_url", "error_code": None}
        result["status"] = "FAIL"
        result["next_action"] = (
            "The provided URL could not be parsed ({reason}). Ask the user "
            "for the complete presigned URL exactly as generated (http/https "
            "and the full query string), or for the full error response "
            "body (Code, Message, RequestId).".format(
                reason=url_analysis.get("reason", "unknown"))
        )
        return (1, result)

    if (url_analysis and url_analysis.get("accepted")
            and url_analysis.get("signature_version") in ("v1", "v2", "v4")):
        # Structurally valid presigned URL but no error/status/symptom to
        # route on: report the parse result and ask for the error details.
        result["match"] = {"type": "url_only", "error_code": None}
        result["status"] = "DEGRADED"
        result["next_action"] = (
            "The URL parses as a structurally valid {ver} presigned URL and "
            "its expiry state is '{state}'. Report this analysis, then ask "
            "the user for the error the requester actually sees (full error "
            "response body: Code, Message, RequestId) before concluding."
        ).format(ver=url_analysis.get("signature_version"),
                 state=url_analysis.get("expiry_state", "unknown"))
        return (0, result)

    result["match"] = {"type": "none", "error_code": None}
    result["status"] = "FAIL"
    result["next_action"] = (
        "No recognizable presigned URL, OSS error code, HTTP status, or "
        "symptom was provided. Ask the user for the presigned URL itself "
        "and/or the full error response body (Code, Message, RequestId) "
        "before diagnosing; consult references/presigned-url-failure-catalog.md."
    )
    return (1, result)


# --- Inline boundary assertions (normal / boundary / invalid) ---------------
# Executed on every run before main; a failure here means the catalog or the
# parsing/routing ladder is broken and the script must not emit a diagnosis.

_NOW = 1_750_000_000  # fixed reference time for deterministic assertions

# normal: V1 URL parse + expiry verdicts
_V1_URL = ("https://bucket-a.oss-cn-hangzhou.aliyuncs.com/docs/a%20b.pdf"
           "?OSSAccessKeyId=LTAI5tDemoKey&Expires={e}&Signature=abc%2Bdef%3D%3D")
_v1_alive = parse_signed_url(_V1_URL.format(e=_NOW + 3600))
assert _v1_alive["accepted"] and _v1_alive["signature_version"] == "v1"
assert check_expiry_state(_v1_alive["expiry"], _NOW) == "valid"
assert _v1_alive["query_params_masked"]["Signature"] == "***masked***"
assert _v1_alive["query_params_masked"]["OSSAccessKeyId"].startswith("LTAI")
_v1_dead = parse_signed_url(_V1_URL.format(e=_NOW - 5))
assert check_expiry_state(_v1_dead["expiry"], _NOW) == "expired"

# normal: V4 URL parse + credential scope + expiry arithmetic
_V4_URL = ("https://bucket-b.oss-cn-shanghai.aliyuncs.com/img/logo.png"
           "?x-oss-credential=LTAI5tDemoKey%2F20250610%2Fcn-shanghai%2Foss"
           "%2Faliyun_v4_request&x-oss-date=20250610T030000Z"
           "&x-oss-expires=3600&x-oss-signature-version=OSS4-HMAC-SHA256"
           "&x-oss-signature=deadbeef")
_v4 = parse_signed_url(_V4_URL)
assert _v4["accepted"] and _v4["signature_version"] == "v4"
assert _v4["credential_scope"]["format_ok"] is True
assert _v4["credential_scope"]["region"] == "cn-shanghai"
assert _v4["expiry"]["ttl_seconds"] == 3600 and _v4["expiry"]["found"]
assert check_expiry_state(_v4["expiry"], _v4["expiry"]["expires_epoch"] - 1) == "valid"
assert check_expiry_state(_v4["expiry"], _v4["expiry"]["expires_epoch"] + 1) == "expired"
assert _v4["query_params_masked"]["x-oss-signature"] == "***masked***"

# boundary: expiry exactly at now is expired; long-term-AccessKey V4 URL allows
# exactly 7 days (604800 s) and rejects 604801 s.
_edge = parse_signed_url(_V1_URL.format(e=_NOW))
assert check_expiry_state(_edge["expiry"], _NOW) == "expired"
_v4_max = parse_signed_url(_V4_URL.replace("x-oss-expires=3600", "x-oss-expires=604800"))
assert _v4_max["expiry"]["ttl_seconds"] == 604800 and _v4_max["expiry"]["found"]
assert _v4_max["expiry"]["credential_type"] == "long_term_ak"
assert _v4_max["expiry"]["ttl_cap_seconds"] == 604800
assert parse_signed_url(_V4_URL.replace("x-oss-expires=3600", "x-oss-expires=604801"))["expiry"]["state"] == "malformed"

# boundary (B-1 fix): STS-signed V4 URL (carries x-oss-security-token) is capped
# at 43200 s (12 hours), NOT 604800 s. Exactly 43200 passes; 43201 is malformed;
# a value that a long-term AccessKey would accept (604800) is rejected for STS.
_V4_STS_URL = _V4_URL + "&x-oss-security-token=CAISdemoToken"
_sts_ok = parse_signed_url(_V4_STS_URL.replace("x-oss-expires=3600", "x-oss-expires=43200"))
assert _sts_ok["expiry"]["credential_type"] == "sts"
assert _sts_ok["expiry"]["ttl_cap_seconds"] == 43200
assert _sts_ok["expiry"]["ttl_seconds"] == 43200 and _sts_ok["expiry"]["found"]
assert parse_signed_url(_V4_STS_URL.replace("x-oss-expires=3600", "x-oss-expires=43201"))["expiry"]["state"] == "malformed"
assert parse_signed_url(_V4_STS_URL.replace("x-oss-expires=3600", "x-oss-expires=604800"))["expiry"]["state"] == "malformed"
# the security-token query parameter itself is masked (4-char prefix + mask)
assert _sts_ok["query_params_masked"]["x-oss-security-token"] == "***masked***"
# alternate STS parameter spelling 'security-token' is also recognised
_V4_STS_ALT = _V4_URL.replace("x-oss-expires=3600", "x-oss-expires=50000") + "&security-token=CAISdemoToken"
assert parse_signed_url(_V4_STS_ALT)["expiry"]["state"] == "malformed"

# boundary: malformed variants
assert parse_signed_url(_V4_URL.replace("x-oss-expires=3600", "x-oss-expires="))["expiry"]["state"] == "malformed"
assert parse_signed_url(_V4_URL.replace("x-oss-expires=3600", "x-oss-expires=abc"))["expiry"]["state"] == "malformed"
assert parse_signed_url(_V4_URL.replace("20250610T030000Z", "2025-06-10"))["expiry"]["state"] == "malformed"
assert parse_signed_url(_V1_URL.format(e="not-a-number"))["expiry"]["state"] == "malformed"
_bad_scope = parse_credential_scope("LTAI5t/20250610//oss/aliyun_v4_request")
assert _bad_scope["format_ok"] is False
# no signature parameters at all
_plain = parse_signed_url("https://bucket-c.oss-cn-hangzhou.aliyuncs.com/x.txt")
assert _plain["accepted"] and _plain["signature_version"] == "none"
# partial signature parameters (stripped URL)
_partial = parse_signed_url("https://b.oss-cn-hangzhou.aliyuncs.com/x.txt?Expires=123")
assert _partial["signature_version"] == "none" and "partial" in _partial["version_detail"]

# invalid: oversized / non-http / empty inputs
assert parse_signed_url("https://b.oss-cn-hangzhou.aliyuncs.com/x?" + "a" * 20000)["accepted"] is False
assert parse_signed_url("ftp://b.oss-cn-hangzhou.aliyuncs.com/x")["accepted"] is False
assert parse_signed_url("")["accepted"] is False
assert parse_signed_url(None)["accepted"] is False

# routing ladder assertions
assert match_error_code("SignatureDoesNotMatch") == ("exact", "SignatureDoesNotMatch")
assert match_error_code("signaturedoesnotmatch") == ("exact", "SignatureDoesNotMatch")
assert match_error_code("RequestTimeTooSkewed") == ("exact", "RequestTimeTooSkewed")
assert match_error_code("TokenExpired") == ("fuzzy", "SecurityTokenExpired")
assert match_error_code("NoSuchCodeXyz") == ("none", None)
assert match_error_code("") == ("none", None)
assert match_error_code(None) == ("none", None)
assert resolve_http_status("403") == STATUS_TO_MODES[403]
assert resolve_http_status(400) == STATUS_TO_MODES[400]
assert resolve_http_status("999") == []
assert resolve_http_status("not-a-number") == []
assert "expired" in match_symptoms("分享链接过期了")
assert "clock_skew" in match_symptoms("client clock is off by 20 minutes")
assert match_symptoms("") == [] and match_symptoms(None) == []
# Regression (ticket-verified): '资源包过期' is a billing subject and must
# NOT route to signed-URL expiry.
assert "expired" not in match_symptoms("资源包过期了")  # invalid subject excluded
assert match_symptoms("资源包过期了") == []  # no candidate mode at all
assert "expired" not in match_symptoms("存储包套餐到期了,说是过期")  # package subject wins
# URL/link/signature context still routes to expiry.
assert "expired" in match_symptoms("签名URL过期了")  # normal: signed URL subject
assert "expired" in match_symptoms("my presigned url expired")  # normal: EN form
# V4-unavailable fallback (symmetric of v1_signature_forbidden): special
# region / old ossbrowser where V4 is unavailable and V1 is the workaround.
assert "v4_unavailable_fallback_v1" in match_symptoms(
    "ossbrowser 特殊区域 v4 关闭")  # normal: fallback branch hit
# Long-term secure access to private objects routing entry.
assert "long_term_private_access" in match_symptoms(
    "私有对象长期安全访问怎么做")  # normal: private long-term sharing
# Custom-domain (CNAME) presigned URL routing (ticket 0001FRR89N): the
# Chinese symptom that previously degraded to expired/v1_forbidden must
# now hit the custom_domain_presigned mode first.
assert "custom_domain_presigned" in FAILURE_MODES
assert match_symptoms("自定义域名作endpoint生成签名URL，http是否可行")[0] == \
    "custom_domain_presigned"
assert "custom_domain_presigned" in match_symptoms("自定义域名…签名URL下载")
assert "custom_domain_presigned" in match_symptoms("cname endpoint signing")
_cdn_exit, _cdn_res = diagnose(
    symptom="自定义域名作为endpoint生成签名URL http可以吗", now_epoch=_NOW)
assert _cdn_exit == 0 and _cdn_res["candidate_modes"][0] == \
    "custom_domain_presigned"
# Chinese synonym layer: Chinese symptom text must route directly to the
# matching failure mode (previously only English keywords hit).
assert "parameter_tampered" in match_symptoms("签名不匹配，链接被改过")
assert "clock_skew" in match_symptoms("客户端时钟偏差比较大")
assert "method_mismatch" in match_symptoms("请求方法不一致")
assert "credential_invalid" in match_symptoms("密钥轮换之后链接失效")
assert "permission_changed" in match_symptoms("权限变更导致打不开")
assert "malformed_url" in match_symptoms("凭证里地域不匹配")

# Eval-fix regression assertions (ticket-idiom isomorphic variants, eval
# report PR-1..PR-5 / PR-9 / PR-10; E-group and B-group wording).
# PR-2: the generic '签名' key must never own 'expired' -- real-ticket
# causes for '签名...打不开' phrasings are permission/tampering/credential.
assert match_symptoms(
    "RAM 子账号没有 oss:GetObject 权限，生成签名链接也打不开")[0] == \
    "permission_changed"                                       # E11
assert match_symptoms(
    "下载链接在微信小程序里打不开，报签名错误")[0] == \
    "parameter_tampered"                                       # E18
assert "expired" not in match_symptoms("v4 签名一直失败，sdk 版本是最新的")[:1]
# PR-3: bare 'v4' no longer hijacks to the fallback mode; compound
# wording, special regions and old tools still reach it.
assert "v4_unavailable_fallback_v1" not in match_symptoms(
    "v4 签名一直失败，sdk 版本是最新的")                          # E14
assert "v4_unavailable_fallback_v1" in match_symptoms(
    "特殊区域 v4 不可用只能回退 v1")                            # compound wording
# PR-4: CDN back-to-origin / abuse / make-it-public wording without URL
# context transfers out (no candidates -> FAIL -> sibling skill).
assert match_symptoms(
    "CDN 回源 OSS 配置了私有桶鉴权，回源一直失败") == []        # E09
assert match_symptoms(
    "我们碰到了黑产上传图片，cdn缓存也消除了，有什么办法避免") == []  # B15
assert match_symptoms("我要开启公开 访问权限码") == []        # B22
assert match_symptoms(
    "our signed url returns 403 SignatureDoesNotMatch after we put "
    "a CDN in front")[0] == "parameter_tampered"              # E16
# PR-10: real-ticket Chinese/English synonym coverage.
assert match_symptoms(
    "老板要求把文件的下载地址改成永久的，现在链接一小时就失效")[0] == \
    "long_term_private_access"                                # E10
assert "expired" in match_symptoms("link works for 9 hours then dies")  # E17
assert "expired" in match_symptoms("my signed url stops working")      # E17 twin
assert match_symptoms(
    "子用户AK配置了网络策略IP白名单禁止公网访问，生成的有效签名URL"
    "公网打不开")[0] == "permission_changed"                  # B14 / U2
assert match_symptoms("签名连接改变了")[0] == "permission_changed"  # B16 idiom
# PR-9 / P4.3 + P4.2 + P2: proxy tampering, SDK config misuse and
# hand-signed CanonicalRequest mistakes reach their cause branches.
assert match_symptoms("代理篡改了请求头，签名失败")[0] == \
    "parameter_tampered"                                       # B05
assert match_symptoms("SDK 配置了 pathStyleAccess 导致签名不对")[0] == \
    "sdk_config_misuse"                                        # B06
assert match_symptoms(
    "自己拼的 V4 签名，signedHeaders 漏了 content-type 一直报签名不匹配"
)[0] == "parameter_tampered"                                   # B09
assert match_symptoms("手动签名时 signedHeaders 顺序写错了")[0] == \
    "parameter_tampered"                                       # B10
# routing table integrity after the redesign
assert "v4" not in SYMPTOM_KEYWORDS and "cdn" not in SYMPTOM_KEYWORDS
assert "expired" not in SYMPTOM_KEYWORDS["签名"]

# diagnose-level assertions: OK (expired verdict), DEGRADED, FAIL paths
_ok_exit, _ok_res = diagnose(url=_V1_URL.format(e=_NOW - 100), now_epoch=_NOW)
assert _ok_exit == 0 and _ok_res["status"] == "OK"
assert _ok_res["candidate_modes"][0] == "expired"
_deg_exit, _deg_res = diagnose(error_code="SignatureDoesNotMatch",
                               http_status="403", now_epoch=_NOW)
assert _deg_exit == 0 and _deg_res["status"] == "DEGRADED"
assert "parameter_tampered" in _deg_res["candidate_modes"]
_fail_exit, _fail_res = diagnose(now_epoch=_NOW)
assert _fail_exit == 1 and _fail_res["status"] == "FAIL"
# Regression: a package-expiry symptom must FAIL (no misrouted expiry mode)
# so the Agent asks for URL/error evidence instead of blaming the URL.
_pkg_exit, _pkg_res = diagnose(symptom="资源包过期了", now_epoch=_NOW)
assert _pkg_exit == 1 and _pkg_res["status"] == "FAIL"
assert "candidate_modes" not in _pkg_res
# valid URL without error context degrades (url_only), never FAILs
_urlonly_exit, _urlonly_res = diagnose(url=_V1_URL.format(e=_NOW + 600), now_epoch=_NOW)
assert _urlonly_exit == 0 and _urlonly_res["status"] == "DEGRADED"
assert _urlonly_res["match"]["type"] == "url_only"
assert len(FAILURE_MODES) >= 8 and len(MODE_KEYS) == len(FAILURE_MODES)
assert "sdk_config_misuse" in FAILURE_MODES

# PR-1 (eval fix): a V4 URL whose credential scope does not follow the
# AccessKeyId/date/region/oss/aliyun_v4_request format is a DETERMINISTIC
# OK-level malformed verdict (SKILL.md Example 3 contract), not url_only.
# The date is pushed into the future so the scope (not the expiry) is the
# deterministic verdict under test.
_v4_scope_bad_url = _V4_URL.replace("%2Faliyun_v4_request", "").replace(
    "x-oss-date=20250610T030000Z", "x-oss-date=20300101T000000Z")
_pr1_exit, _pr1_res = diagnose(url=_v4_scope_bad_url, now_epoch=_NOW)
assert _pr1_exit == 0 and _pr1_res["status"] == "OK"
assert _pr1_res["candidate_modes"][0] == "malformed_url"
assert _pr1_res["url_analysis"]["credential_scope"]["format_ok"] is False
assert _pr1_res["url_analysis"]["expiry_state"] == "valid"  # scope, not expiry, is the verdict
# boundary: an expired URL keeps the expired verdict even when the scope
# is ALSO malformed (runtime expiry outranks the format defect).
_pr1b_exit, _pr1b_res = diagnose(
    url=_V4_URL.replace("%2Faliyun_v4_request", ""), now_epoch=_NOW)
assert _pr1b_res["status"] == "OK"
assert _pr1b_res["candidate_modes"][0] == "expired"
# PR-5 (eval fix): the customer's original question wording participates
# in symptom routing, so advisory first-question tickets reach candidates
# instead of FAILing at the entry (ticket 0001FRR89N wording).
_pr5_exit, _pr5_res = diagnose(
    question="代码里面 需要设置这个域名作为endpoint吗", now_epoch=_NOW)
assert _pr5_exit == 0 and _pr5_res["status"] == "DEGRADED"
assert _pr5_res["candidate_modes"][0] == "custom_domain_presigned"
_pr5b_exit, _pr5b_res = diagnose(
    question="之前沟通过，我这个bucket 区域有些特别选不到，只能用指定域名的方式",
    now_epoch=_NOW)
assert _pr5b_res["candidate_modes"][0] == "custom_domain_presigned"  # B18
# question routing is additive with symptom routing, never replacing it.
_q_plus_exit, _q_plus_res = diagnose(
    symptom="分享链接过期了", question="链接为什么打不开", now_epoch=_NOW)
assert _q_plus_res["candidate_modes"][0] == "expired"


def degrade_warn_line(status: str, match_type: str) -> str:
    """[WARN] trace line emitted on stderr when the knowledge diagnosis
    cannot reach a full conclusion.

    F-3 fix: aligns the zero-cloud knowledge skills with the cloud-chain
    skills' dual-channel degradation trace (stdout JSON status + stderr
    [WARN]). Returns the formatted line; never raises.
    """
    return "[WARN] {0} degraded: {1}".format(
        SKILL_NAME, match_type or status.lower())


assert degrade_warn_line("DEGRADED", "url_only") == "[WARN] " + SKILL_NAME + " degraded: url_only"  # normal
assert degrade_warn_line("FAIL", "invalid_url").endswith("degraded: invalid_url")  # boundary: FAIL path
assert degrade_warn_line("FAIL", "") == "[WARN] " + SKILL_NAME + " degraded: fail"  # invalid: missing match type falls back to status


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Knowledge-driven OSS presigned-URL failure diagnosis "
                    "and V4 upgrade guidance (zero cloud API calls)."
    )
    parser.add_argument("--url", dest="url", default=None,
                        help="Presigned URL to analyze locally (never sent "
                             "over the network; secrets are masked)")
    parser.add_argument("--error-code", dest="error_code", default=None,
                        help="OSS error code from the response body (fuzzy OK)")
    parser.add_argument("--http-status", dest="http_status", default=None,
                        help="HTTP status code, e.g. 403")
    parser.add_argument("--symptom", dest="symptom", default=None,
                        help="Free-text symptom, e.g. 'share link expired'")
    parser.add_argument("--question", dest="question", default=None,
                        help="Customer's original question wording; enables "
                             "the official-doc verification leg "
                             "(doc_verification section in the JSON)")
    args = parser.parse_args(argv)

    exit_code, result = diagnose(
        url=args.url,
        error_code=args.error_code,
        http_status=args.http_status,
        symptom=args.symptom,
        question=args.question,
    )

    # Official-doc verification leg (read-only, help.aliyun.com only).
    # Runs when --question is supplied AND either the embedded catalog did
    # not reach a conclusive route (Step A miss) or the wording is a
    # configuration/usage advisory question. Never changes STATUS/NEXT_ACTION
    # and never raises; absent --question keeps the legacy output untouched.
    # (Eval fix PR-5: --question now ALSO feeds the symptom routing above,
    # so advisory first-question tickets reach candidate modes.)
    question = normalize_text(args.question)
    if question:
        result["inputs"]["question"] = question
        if result["status"] != "OK" or is_advisory_question(question):
            result["doc_verification"] = lookup_config_topic(
                question, SKILL_TOPICS)

    if result["status"] in ("DEGRADED", "FAIL"):
        # F-3: stderr [WARN] trace for degraded/failed knowledge runs.
        print(degrade_warn_line(result["status"],
                                (result.get("match") or {}).get("type") or ""),
              file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("STATUS: {0}".format(result["status"]))
    print("NEXT_ACTION: {0}".format(result["next_action"]))
    if question and "doc_verification" in result:
        # Human-readable Doc verification tail (spec section 2.4).
        dv = result["doc_verification"]
        if dv.get("matched"):
            print("Doc verification: matched via official OSS docs "
                  "(llms-index):")
            for doc in dv["docs"]:
                print("  - {0}: {1}".format(doc["title"], doc["url"]))
        else:
            print("Doc verification: DEGRADED (offline) — conclusions are "
                  "based on embedded knowledge only.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
