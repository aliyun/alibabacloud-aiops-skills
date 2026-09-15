#!/usr/bin/env python3
# SECURITY: knowledge-driven diagnosis only. This script performs NO network
# calls, invokes NO aliyun CLI, and calls NO cloud API. It maps a user-supplied
# OSS upload/download error to root-cause directions using the embedded
# official error-code catalog, then emits structured JSON plus STATUS/NEXT_ACTION.
"""Entry script for alibabacloud-oss-transfer-error-code-diagnosis.

Usage (all parameters optional):
  python3 oss_transfer_error_diagnosis.py \
      [--error-code CODE] [--http-status 403] [--request-id RID] \
      [--bucket BUCKET] [--operation upload|download]

Matching ladder (pure functions, unit-testable):
  1. exact catalog lookup (case-insensitive)          -> STATUS: OK
  2. client-term synonym lookup (e.g. ETIMEDOUT)      -> STATUS: DEGRADED
  3. fuzzy prefix/substring match against catalog     -> STATUS: DEGRADED
  4. HTTP-status-only candidate list                  -> STATUS: DEGRADED
  5. nothing recognizable                             -> STATUS: FAIL (exit 1)
"""

import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
import uuid

import _doc_lookup
from _error_catalog import (
    CATEGORY_LABELS,
    CLIENT_TERM_FAMILIES,
    CLIENT_TERM_SYNONYMS,
    DOMAIN_TRANSFER_GUARDS,
    EC_CODE_REFERRALS,
    ERROR_CATALOG,
    NETWORK_OPTIMIZATION_SUGGESTIONS,
    OSS_CONTEXT_ANCHORS,
    REQUEST_ID_GUIDANCE,
    STATUS_TO_CODES,
    SYMPTOM_KEYWORDS,
)

SKILL_NAME = "alibabacloud-oss-transfer-error-code-diagnosis"

# --- Observability (SA-2.11c): session id + User-Agent template ------------
# Even though this skill makes zero cloud API calls, the session id and the
# User-Agent string are generated here so any future HTTP usage is traceable.
SESSION_ID = uuid.uuid4().hex  # 32-char lowercase hex
SKILL_VERSION = "1.0.0"  # UA skill-version; matches references/manifest.json
USER_AGENT = "AlibabaCloud-Agent-Skills/{skill}/{session_id} skill-version/{version}".format(
    skill=SKILL_NAME, session_id=SESSION_ID, version=SKILL_VERSION
)

CODE_KEYS = sorted(ERROR_CATALOG.keys())


# --- Pure matching functions (no I/O, no side effects) ----------------------

def normalize_text(value):
    """Return stripped string, or '' for None/non-str input."""
    if not isinstance(value, str):
        return ""
    return value.strip()


def match_error_code(raw_code):
    """Match a raw error-code string against the catalog.

    Returns (match_type, canonical_code):
      ("exact",  code)  case-insensitive exact catalog hit
      ("synonym", code) client-term synonym hit (e.g. ETIMEDOUT)
      ("fuzzy",  code)  unique prefix/substring hit
      ("ambiguous", None) substring matches more than one code
      ("none",   None)  no hit / empty input
    """
    code = normalize_text(raw_code)
    if not code:
        return ("none", None)
    lowered = code.lower()
    for key in CODE_KEYS:
        if key.lower() == lowered:
            return ("exact", key)
    synonym = CLIENT_TERM_SYNONYMS.get(lowered)
    if synonym:
        return ("synonym", synonym)
    family = CLIENT_TERM_FAMILIES.get(lowered)
    if family:
        return ("synonym_family", list(family))
    fuzzy_hits = [
        key for key in CODE_KEYS
        if lowered in key.lower() or key.lower() in lowered
    ]
    if len(fuzzy_hits) == 1:
        return ("fuzzy", fuzzy_hits[0])
    if len(fuzzy_hits) > 1:
        return ("ambiguous", None)
    return ("none", None)


def match_symptoms(*texts):
    """Map free-text symptom wording to candidate catalog codes (pure).

    Iterates SYMPTOM_KEYWORDS longest-key-first (precise compound keys
    outrank generic ones, the presigned-skill routing-order pattern) and
    returns the deduplicated union of candidate codes; empty when no key
    hits. Subject discrimination lives in the keyword table itself:
    generic action words are never keys, every key pairs an action or size
    marker with a failure symptom.
    """
    combined = " ".join(t for t in (normalize_text(x) for x in texts) if t)
    text = combined.lower()
    if not text:
        return []
    candidates = []
    for keyword in sorted(SYMPTOM_KEYWORDS, key=lambda k: (-len(k), k)):
        if keyword in text:
            for code in SYMPTOM_KEYWORDS[keyword]:
                if code not in candidates:
                    candidates.append(code)
    return candidates


def has_oss_context(text):
    """True when the wording carries an OSS context anchor (pure)."""
    lowered = normalize_text(text).lower()
    if not lowered:
        return False
    return any(anchor in lowered for anchor in OSS_CONTEXT_ANCHORS)


def domain_guard_hit(text):
    """Pure check: does the wording mark a NON-OSS product?

    Returns the matched guard (tuple of word groups) when every group of
    some guard contributes at least one word present in the lowercased
    text AND the text carries no OSS context anchor; None otherwise. An
    OSS problem mentioned alongside a guard word stays in scope.
    """
    lowered = normalize_text(text).lower()
    if not lowered:
        return None
    if has_oss_context(lowered):
        return None
    for guard in DOMAIN_TRANSFER_GUARDS:
        if all(any(word in lowered for word in group) for group in guard):
            return guard
    return None


def ec_code_referral(raw_code):
    """Return the sibling-skill referral for a known non-transfer EC code.

    Pure dict lookup on the normalized (lowercased) input; None when the
    code is absent from EC_CODE_REFERRALS or the input is empty.
    """
    code = normalize_text(raw_code).lower()
    if not code:
        return None
    return EC_CODE_REFERRALS.get(code)


def resolve_http_status(raw_status):
    """Map an HTTP status (int or numeric string) to candidate error codes.

    Returns a list (possibly empty). Invalid input yields [].
    """
    try:
        status = int(normalize_text(str(raw_status)))
    except (TypeError, ValueError):
        return []
    return list(STATUS_TO_CODES.get(status, []))


def normalize_operation(raw_operation):
    """Return 'upload', 'download' or '' (case-insensitive, tolerant)."""
    op = normalize_text(raw_operation).lower()
    if op in ("upload", "put", "post", "multipart"):
        return "upload"
    if op in ("download", "get", "read"):
        return "download"
    return ""


def operation_hints(operation):
    """Extra transfer-side hints based on the operation type (ticket-based)."""
    if operation == "upload":
        return [
            "Use multipart/resumable upload so a retry does not restart from zero",
            "Keep part size in the 1-10 MB range on unstable links",
        ]
    if operation == "download":
        return [
            "Use range/resumable download for large objects so retries resume",
            "Verify the client timeout covers the expected transfer duration",
            "For many small files, raise client concurrency/parallelism (e.g. ossutil -j/--jobs) to lift throughput",
        ]
    return []


def build_diagnosis(canonical_code):
    """Build the diagnosis block for one canonical catalog code (pure)."""
    entry = ERROR_CATALOG[canonical_code]
    block = {
        "code": entry["code"],
        "http_status": entry["http_status"],
        "category": entry["category"],
        "category_label": CATEGORY_LABELS[entry["category"]],
        "side": entry["side"],
        "root_cause_directions": list(entry["root_cause_directions"]),
        "troubleshooting_steps": list(entry["troubleshooting_steps"]),
        "official_doc_ref": entry["official_doc_ref"],
    }
    if entry["category"] == "network" or entry["code"] in (
        "RequestTimeout", "ConnectionTimeout",
    ):
        block["network_optimization_suggestions"] = list(
            NETWORK_OPTIMIZATION_SUGGESTIONS
        )
    return block


def _candidate_summaries(codes):
    """Build the candidate summary list for a list of catalog codes (pure)."""
    return [
        {
            "code": c,
            "category": ERROR_CATALOG[c]["category"],
            "category_label": CATEGORY_LABELS[ERROR_CATALOG[c]["category"]],
        }
        for c in codes
    ]


def _referral_block(raw_code):
    """Return the EC-code referral block, or None when not applicable."""
    refer_to = ec_code_referral(raw_code)
    if not refer_to:
        return None
    return {
        "ec_code": normalize_text(raw_code).lower(),
        "refer_to": refer_to,
        "note": ("This EC numeric code is owned by another OSS skill; the "
                 "referral above usually resolves the case in one hop."),
    }


def diagnose(error_code=None, http_status=None, request_id=None,
             bucket=None, operation=None, question=None):
    """Pure decision function. Returns (exit_code, result_dict).

    Decision order (every layer degrades gracefully, never crashes):
      0. domain guard: customer wording marks a NON-OSS product (SSH/MySQL/
         CDN/host curl) with no OSS context -> FAIL with a boundary note
      1. exact / fuzzy / synonym error-code match        -> diagnosis
      1b. synonym family (a bare zh word: timeout)       -> candidate list
      2. HTTP-status-only candidate list                 -> DEGRADED
      3. ambiguous partial code                          -> DEGRADED
      4. RequestId present but no code                   -> FAIL + request-
         id guidance (client-type paths to recover the error body)
      5. symptom keywords in the customer wording        -> DEGRADED list
      6. nothing recognizable                            -> FAIL
    EC numeric codes owned by sibling skills attach an ec_code_referral
    block on layers 2-6 instead of being silently absorbed.
    """
    op = normalize_operation(operation)
    result = {
        "skill": SKILL_NAME,
        "session_id": SESSION_ID,
        "user_agent": USER_AGENT,
        "inputs": {
            "error_code": normalize_text(error_code),
            "http_status": normalize_text(http_status) if http_status is not None else "",
            "request_id": normalize_text(request_id),
            "bucket": normalize_text(bucket),
            "operation": op,
        },
        "references": [
            "references/error-code-catalog.md",
            "references/troubleshooting-playbook.md",
            "references/scope-and-limitations.md",
        ],
    }

    # Layer 0: out-of-domain guard. The customer wording (question, plus
    # the error-code text as fallback) is the authority for domain context;
    # an OSS anchor anywhere keeps the case in scope.
    guard_text = " ".join(t for t in (
        normalize_text(question), normalize_text(error_code)) if t)
    guard = domain_guard_hit(guard_text)
    if guard is not None:
        matched_words = [w for group in guard for w in group
                         if w in guard_text.lower()]
        result["match"] = {"type": "domain_guard", "code": None}
        result["domain_guard"] = {
            "matched_words": matched_words,
            "note": ("The customer wording points at a non-OSS product; "
                     "this skill only diagnoses Alibaba Cloud OSS "
                     "upload/download error codes."),
        }
        result["status"] = "FAIL"
        result["next_action"] = (
            "The wording marks a non-OSS product failure (matched: {words}). "
            "Confirm whether the failing request actually targets Alibaba "
            "Cloud OSS; if it does, ask for the OSS error response body and "
            "re-run. CDN back-to-origin cases route to "
            "alibabacloud-oss-cdn-origin-config-diagnosis; other products "
            "need their own support channel."
        ).format(words=", ".join(matched_words))
        return (1, result)

    match_type, canonical = match_error_code(error_code)

    if match_type in ("exact", "fuzzy", "synonym"):
        result["match"] = {"type": match_type, "code": canonical}
        result["diagnosis"] = build_diagnosis(canonical)
        if op:
            result["diagnosis"]["operation_hints"] = operation_hints(op)
        status = "OK" if match_type == "exact" else "DEGRADED"
        next_action = (
            "Report the root-cause directions and troubleshooting steps for "
            "{code} verbatim from the diagnosis block; follow "
            "references/troubleshooting-playbook.md for the {cat} track."
        ).format(code=canonical, cat=result["diagnosis"]["category"])
        result["status"] = status
        result["next_action"] = next_action
        return (0, result)

    if match_type == "synonym_family":
        candidates = list(canonical)
        result["match"] = {"type": "synonym_family", "code": None}
        result["candidates"] = candidates
        result["candidate_summaries"] = _candidate_summaries(candidates)
        if op:
            result["operation_hints"] = operation_hints(op)
        result["status"] = "DEGRADED"
        result["next_action"] = (
            "The client wording names a family of OSS error codes "
            "(RequestTimeout / ConnectionTimeout). Ask the user for the "
            "exact error code from the response body to pick one candidate "
            "before concluding."
        )
        return (0, result)

    candidates = resolve_http_status(http_status)
    if candidates:
        result["match"] = {"type": "status_only", "code": None}
        result["candidates"] = candidates
        result["candidate_summaries"] = _candidate_summaries(candidates)
        if op:
            result["operation_hints"] = operation_hints(op)
        referral = _referral_block(error_code)
        if referral:
            result["ec_code_referral"] = referral
            result["next_action"] = (
                "The EC code {ec} is owned by {target}; route the customer "
                "there first. If the OSS error body shows a different Code, "
                "ask the user for it to pick one candidate from the list."
            ).format(ec=referral["ec_code"], target=referral["refer_to"])
        else:
            result["next_action"] = (
                "Ask the user for the exact OSS error code (the <Code> field in "
                "the response body, e.g. AccessDenied or RequestTimeout) to pick "
                "one candidate; until then present the candidate list only."
            )
        result["status"] = "DEGRADED"
        return (0, result)

    if match_type == "ambiguous":
        result["match"] = {"type": "ambiguous", "code": None}
        result["candidates"] = [
            k for k in CODE_KEYS
            if normalize_text(error_code).lower() in k.lower()
            or k.lower() in normalize_text(error_code).lower()
        ]
        result["status"] = "DEGRADED"
        result["next_action"] = (
            "Ask the user to provide the complete error code string; the "
            "partial input matches multiple catalog entries."
        )
        return (0, result)

    # RequestId-only path: no code matched, but a RequestId was supplied.
    # STATUS stays FAIL and NEXT_ACTION keeps asking for the full error
    # body (no fabricated root cause); the guidance block adds the
    # client-type paths to recover that body around the RequestId.
    if normalize_text(request_id):
        result["match"] = {"type": "none", "code": None}
        result["request_id_guidance"] = {
            "note": REQUEST_ID_GUIDANCE["note"],
            "client_type_paths": list(
                REQUEST_ID_GUIDANCE["client_type_paths"]),
            "ec_hint": REQUEST_ID_GUIDANCE["ec_hint"],
            "doc_ref": REQUEST_ID_GUIDANCE["doc_ref"],
        }
        result["status"] = "FAIL"
        result["next_action"] = (
            "No recognizable OSS error code or HTTP status was provided. Ask the "
            "user for the full error response body (Code, Message, RequestId) "
            "before diagnosing; consult references/error-code-catalog.md."
        )
        return (1, result)

    # Symptom layer: no code/status/RequestId, but the customer wording
    # (question, plus the error-code text as fallback) carries routable
    # symptom keys -> present candidate directions and ask for the body.
    symptom_candidates = match_symptoms(question, error_code)
    if symptom_candidates:
        result["match"] = {"type": "symptom", "code": None}
        result["candidates"] = symptom_candidates
        result["candidate_summaries"] = _candidate_summaries(
            symptom_candidates)
        if op:
            result["operation_hints"] = operation_hints(op)
        result["status"] = "DEGRADED"
        result["next_action"] = (
            "No error code was provided, but the symptom wording maps to "
            "these candidate directions. Present the candidates, then ask "
            "the user for the full error response body (Code, Message, "
            "RequestId) to pin down the exact cause."
        )
        return (0, result)

    result["match"] = {"type": "none", "code": None}
    referral = _referral_block(error_code)
    if referral:
        result["ec_code_referral"] = referral
        result["next_action"] = (
            "No recognizable OSS error code or HTTP status was provided. Ask "
            "the user for the full error response body (Code, Message, "
            "RequestId) before diagnosing; consult "
            "references/error-code-catalog.md. The EC code {ec} is owned by "
            "{target}; route the customer there first."
        ).format(ec=referral["ec_code"], target=referral["refer_to"])
    else:
        result["next_action"] = (
            "No recognizable OSS error code or HTTP status was provided. Ask the "
            "user for the full error response body (Code, Message, RequestId) "
            "before diagnosing; consult references/error-code-catalog.md."
        )
    result["status"] = "FAIL"
    return (1, result)


# --- Inline boundary assertions (normal / boundary / invalid) ---------------
# Executed on every run before main; a failure here means the catalog or the
# matching ladder is broken and the script must not emit a diagnosis.

# normal: exact hits (canonical + case variants)
assert match_error_code("AccessDenied") == ("exact", "AccessDenied")
assert match_error_code("accessdenied") == ("exact", "AccessDenied")
assert match_error_code("  SignatureDoesNotMatch ") == ("exact", "SignatureDoesNotMatch")
assert match_error_code("REQUESTTIMEOUT") == ("exact", "RequestTimeout")

# client-term synonyms (real ticket terminology -> canonical catalog code)
assert match_error_code("SocketTimeout") == ("synonym", "ConnectionTimeout")
assert match_error_code("ETIMEDOUT") == ("synonym", "ConnectionTimeout")
assert match_error_code("net::ERR_EMPTY_RESPONSE") == ("synonym", "ConnectionTimeout")
assert match_error_code("sockettimeoutexception") == ("synonym", "ConnectionTimeout")
# SDK exception wrapper names + Chinese natural-language timeout terms must
# route like the English synonyms (ticket 0001ZRGGE6 regression: RequestError
# used to FAIL with match=none).
assert match_error_code("RequestError") == ("synonym", "ConnectionTimeout")
assert match_error_code("SocketException") == ("synonym", "ConnectionTimeout")
assert match_error_code("connection timed out") == ("synonym", "ConnectionTimeout")
assert match_error_code("\u8fde\u63a5\u8d85\u65f6") == ("synonym", "ConnectionTimeout")
assert match_error_code("\u8bf7\u6c42\u9519\u8bef") == ("synonym", "ConnectionTimeout")
assert match_error_code("\u8bf7\u6c42\u8d85\u65f6") == ("synonym", "RequestTimeout")
_re_exit, _re_result = diagnose(error_code="RequestError", operation="upload")
assert _re_exit == 0
assert _re_result["match"] == {"type": "synonym", "code": "ConnectionTimeout"}
_syn_exit, _syn_result = diagnose(error_code="ETIMEDOUT", operation="download")
assert _syn_exit == 0 and _syn_result["status"] == "DEGRADED"
assert _syn_result["match"] == {"type": "synonym", "code": "ConnectionTimeout"}
assert "network_optimization_suggestions" in _syn_result["diagnosis"]
# 499 (nginx-style client early-close) routes to the timeout family
assert resolve_http_status("499") == ["RequestTimeout", "ConnectionTimeout"]

# boundary: fuzzy and status mapping
assert match_error_code("Signature") == ("fuzzy", "SignatureDoesNotMatch")
assert match_error_code("TokenExpired") == ("fuzzy", "SecurityTokenExpired")
assert match_error_code("BucketAlreadyExists") == ("exact", "BucketAlreadyExists")
assert resolve_http_status("403")[0] == "AccessDenied"
assert resolve_http_status(503) == ["SlowDown", "ServiceUnavailable"]
assert resolve_http_status(409) == ["BucketAlreadyExists"]
assert resolve_http_status("999") == []
assert normalize_operation("UPLOAD") == "upload"
assert normalize_operation("get") == "download"
assert normalize_operation("weird") == ""

# invalid: unknown code / empty / None inputs
assert match_error_code("NoSuchCodeXyz") == ("none", None)
assert match_error_code("") == ("none", None)
assert match_error_code(None) == ("none", None)
assert resolve_http_status("not-a-number") == []
fail_exit, fail_result = diagnose()
assert fail_exit == 1 and fail_result["status"] == "FAIL"
ok_exit, ok_result = diagnose(error_code="RequestTimeout", operation="download")
assert ok_exit == 0 and ok_result["status"] == "OK"
assert "network_optimization_suggestions" in ok_result["diagnosis"]
deg_exit, deg_result = diagnose(http_status="400")
assert deg_exit == 0 and deg_result["status"] == "DEGRADED"
assert len(STATUS_TO_CODES) >= 7 and len(ERROR_CATALOG) >= 14

# --- Inline boundary assertions: 2026-09 routing-layer extensions ----------
# (normal / boundary / invalid for every new pure function and branch)

# bucket-name EC family (eval-fix backfill): symbolic codes hit exact, EC
# numeric aliases hit the synonym route with the full SOP behind them.
assert match_error_code("InvalidBucketName") == ("exact", "InvalidBucketName")  # normal
assert match_error_code("0015-00000001") == ("synonym", "InvalidBucketName")    # EC form
assert match_error_code("0015-00000101") == ("synonym", "NoSuchBucket")        # EC form
_ibn_exit, _ibn_result = diagnose(error_code="InvalidBucketName",
                                  http_status="400")
assert _ibn_exit == 0 and _ibn_result["status"] == "OK"                        # was DEGRADED
assert _ibn_result["match"] == {"type": "exact", "code": "InvalidBucketName"}
assert "0015-00000001" in " ".join(_ibn_result["diagnosis"]["root_cause_directions"])
_ns_exit, _ns_result = diagnose(error_code="NoSuchBucket", http_status="404",
                                bucket="my.bucket.name")
assert _ns_exit == 0 and _ns_result["status"] == "OK"
_ns_dir_text = " ".join(_ns_result["diagnosis"]["root_cause_directions"])
assert "0015-00000101" in _ns_dir_text and "0015-00000001" in _ns_dir_text

# multipart completeness family: exact hits with the sibling referral step.
for _mp in ("InvalidPart", "PartOutOfBounds", "InvalidPartOrder"):
    assert match_error_code(_mp) == ("exact", _mp)                              # normal

# connection-reset / DNS synonym family (previously FAIL inputs).
assert match_error_code("ConnectionReset") == ("synonym", "ConnectionTimeout")   # normal
assert match_error_code("ConnectionResetError") == ("synonym", "ConnectionTimeout")
assert match_error_code("ConnectionRefused") == ("synonym", "ConnectionTimeout")
assert match_error_code("BrokenPipeError") == ("synonym", "ConnectionTimeout")
assert match_error_code("ReadTimeout") == ("synonym", "RequestTimeout")
assert match_error_code("ClientError") == ("synonym", "ConnectionTimeout")
assert match_error_code("getaddrinfo failed") == ("synonym", "ConnectionTimeout")
assert match_error_code("NameResolutionError") == ("synonym", "ConnectionTimeout")
assert match_error_code("\u57df\u540d\u89e3\u6790\u5931\u8d25") == ("synonym", "ConnectionTimeout")

# Chinese family word: the bare timeout word (\u8d85\u65f6) yields both candidates.
assert match_error_code("\u8d85\u65f6") == ("synonym_family",
                                   ["RequestTimeout", "ConnectionTimeout"])  # normal
_to_exit, _to_result = diagnose(error_code="\u8d85\u65f6")
assert _to_exit == 0 and _to_result["status"] == "DEGRADED"
assert _to_result["match"]["type"] == "synonym_family"
assert _to_result["candidates"] == ["RequestTimeout", "ConnectionTimeout"]

# symptom layer: real-ticket phrasings route to candidate lists (all were
# previously unroutable FAILs).
assert match_symptoms("\u4e0a\u4f20\u5927\u6587\u4ef6\u603b\u662f\u65ad") == ["EntityTooLarge", "RequestTimeout",
                                           "ConnectionTimeout"]                  # normal
assert match_symptoms("\u4e0b\u8f7d\u5230\u4e00\u534a\u5c31\u5931\u8d25") == ["RequestTimeout",
                                            "ConnectionTimeout"]                # normal
assert match_symptoms("\u60f3\u4e0b\u8f7d\u6570\u636e\uff0c\u4e0b\u8f7d\u4e0d\u6210\u529f\uff0c\u5e94\u8be5\u600e\u4e48\u5bf9\u5e94\u5462") != []            # normal
assert match_symptoms("") == []                                              # invalid
assert match_symptoms(None, None) == []                                     # invalid
assert match_symptoms("\u968f\u4fbf\u804a\u804a") == []                                    # boundary: no key
_e6_exit, _e6_result = diagnose(question="\u4e0a\u4f20\u5927\u6587\u4ef6\u603b\u662f\u65ad", operation="upload")
assert _e6_exit == 0 and _e6_result["status"] == "DEGRADED"
assert _e6_result["match"]["type"] == "symptom"
assert "EntityTooLarge" in _e6_result["candidates"]
_e11_exit, _e11_result = diagnose(
    question="Endpoint \u53ef\u4ee5\u8bbf\u95ee\uff0c\u4f46\u52a0\u4e0a Bucket \u57df\u540d\u5c31\u8bbf\u95ee\u4e0d\u5230")
assert _e11_exit == 0 and _e11_result["match"]["type"] == "symptom"
assert _e11_result["candidates"] == ["ConnectionTimeout"]

# domain guard: non-OSS product wording without an OSS anchor is refused.
assert domain_guard_hit("\u670d\u52a1\u5668 SSH \u8fde\u63a5\u8d85\u65f6") is not None                   # normal: ssh
assert domain_guard_hit("MySQL \u8fde\u63a5\u8d85\u65f6") is not None                       # normal: mysql
assert domain_guard_hit("ECS \u4e0a curl \u63a5\u53e3\u8fd4\u56de 403") is not None            # normal: ecs+curl
assert domain_guard_hit("oss \u4e0a\u4f20\u8fde\u63a5\u8d85\u65f6") is None                        # boundary: OSS anchor
assert domain_guard_hit("ECS \u4e0a ossutil \u4e0a\u4f20\u62a5\u9519") is None                 # boundary: OSS anchor
assert domain_guard_hit("curl: (28) Connection timed out") is None        # boundary: curl alone
assert domain_guard_hit("") is None and domain_guard_hit(None) is None     # invalid
_gd_exit, _gd_result = diagnose(error_code="\u8fde\u63a5\u8d85\u65f6",
                                question="\u670d\u52a1\u5668 SSH \u8fde\u63a5\u8d85\u65f6")
assert _gd_exit == 1 and _gd_result["status"] == "FAIL"                    # refuse, not absorb
assert _gd_result["match"]["type"] == "domain_guard"
_gd2_exit, _gd2_result = diagnose(http_status="403",
                                  question="MySQL \u670d\u52a1\u8fde\u63a5\u8d85\u65f6\u62a5 403")
assert _gd2_exit == 1 and _gd2_result["match"]["type"] == "domain_guard"

# request-id-only path: FAIL semantics and NEXT_ACTION wording preserved,
# plus the client-type guidance block.
_rid_exit, _rid_result = diagnose(
    request_id="6A545F5FE4C5F835365B91AC",
    question="oss \u4e0a\u4f20\u7684\u65f6\u5019\u62a5\u9519\uff0c\u8fd4\u56de\u8fd9\u4e2arequestid 6A54 \u4f60\u5e2e\u6211\u8bca\u65ad\u4e00\u4e0b")
assert _rid_exit == 1 and _rid_result["status"] == "FAIL"                  # normal: FAIL kept
assert _rid_result["match"] == {"type": "none", "code": None}
assert "request_id_guidance" in _rid_result
assert _rid_result["next_action"].startswith(
    "No recognizable OSS error code or HTTP status was provided.")       # NEXT_ACTION kept
assert len(_rid_result["request_id_guidance"]["client_type_paths"]) >= 5

# EC-code referrals: wrong-door EC codes get a one-hop referral without
# changing the status semantics of the branch they land in.
assert ec_code_referral("0003-00000005") is not None                       # normal
assert ec_code_referral("") is None and ec_code_referral(None) is None     # invalid
_b7_exit, _b7_result = diagnose(error_code="0024-00000008")  # first-hand measured code, officially uncatalogued -> referral only
assert _b7_exit == 1 and _b7_result["status"] == "FAIL"                    # FAIL semantics kept
assert _b7_result["ec_code_referral"]["refer_to"].startswith(
    "alibabacloud-oss-transfer-acceleration-diagnosis")
_b5_exit, _b5_result = diagnose(error_code="0003-00000005", http_status="403")
assert _b5_exit == 0 and _b5_result["status"] == "DEGRADED"                # status_only kept
assert _b5_result["match"]["type"] == "status_only"
assert _b5_result["ec_code_referral"]["refer_to"].startswith(
    "alibabacloud-oss-direct-access-link-diagnosis")

# regression: the plain status-only path without an EC code keeps its
# original NEXT_ACTION wording (no referral contamination).
_st_exit, _st_result = diagnose(http_status="403")
assert _st_exit == 0 and "ec_code_referral" not in _st_result
assert _st_result["next_action"].startswith("Ask the user for the exact OSS")

# 429 after TooManyRequests removal (2026-08-26): the code no longer exists
# in the catalog, so HTTP-status-only 429 input must degrade through the
# status-only fallback (DEGRADED + candidates), never an exact code hit.
assert match_error_code("TooManyRequests") == ("none", None)
_tmr_exit, _tmr_result = diagnose(error_code="TooManyRequests")
assert _tmr_exit == 1 and _tmr_result["status"] == "FAIL" and _tmr_result["match"]["type"] == "none"
_429_exit, _429_result = diagnose(http_status="429")
assert _429_exit == 0 and _429_result["status"] == "DEGRADED"
assert _429_result["match"]["type"] == "status_only"
assert "TooManyRequests" not in _429_result["candidates"]
assert set(_429_result["candidates"]) <= set(ERROR_CATALOG.keys())


def degrade_warn_line(status: str, match_type: str) -> str:
    """[WARN] trace line emitted on stderr when the knowledge diagnosis
    cannot reach a full conclusion.

    F-3 fix: aligns the zero-cloud knowledge skills with the cloud-chain
    skills' dual-channel degradation trace (stdout JSON status + stderr
    [WARN]). Returns the formatted line; never raises.
    """
    return "[WARN] {0} degraded: {1}".format(
        SKILL_NAME, match_type or status.lower())


assert degrade_warn_line("DEGRADED", "status_only") == "[WARN] " + SKILL_NAME + " degraded: status_only"  # normal
assert degrade_warn_line("FAIL", "none").endswith("degraded: none")  # boundary: FAIL path
assert degrade_warn_line("FAIL", "") == "[WARN] " + SKILL_NAME + " degraded: fail"  # invalid: missing match type falls back to status


# --- Official doc verification wiring (optional --question) ---------------
# Read-only enhancement per the doc-lookup integration spec: embedded
# knowledge first (Step A, the matching ladder above), then the llms-index
# official-doc leg (Step B) for consultation-shaped questions or Step-A
# misses. Never blocks the diagnosis: offline / failures degrade into a
# note, the main output and STATUS/NEXT_ACTION stay intact.

# Chinese consultation markers ("how to", "can I", "why", "configure", ...)
# that read as a configuration question rather than an error report. Stored
# as \uXXXX escapes so the shipped source stays ASCII (static rule 4.1.2);
# Python decodes them at import, so matching behaviour is unchanged.
_CONSULT_SIGNALS = (
    "\u600e\u4e48", "\u5982\u4f55", "\u600e\u6837", "\u662f\u5426", "\u80fd\u5426", "\u53ef\u4ee5", "\u652f\u6301",
    "\u914d\u7f6e", "\u5f00\u901a", "\u8bbe\u7f6e", "\u4e3a\u4ec0\u4e48", "\u9650\u5236", "\u89e3\u51b3", "\u5904\u7406", "\u54a8\u8be2",
)


def is_config_consult(question):
    """True when the wording reads as a configuration/usage consultation."""
    q = normalize_text(question)
    return any(signal in q for signal in _CONSULT_SIGNALS)


def should_verify_doc(question, match_type):
    """Step B trigger: a Step-A miss (no recognizable error code), a
    symptom-routed candidate list (no hard code yet), or a consultation-
    shaped question routes to the doc verification leg."""
    if not normalize_text(question):
        return False
    if match_type in ("none", "symptom"):
        return True
    return is_config_consult(question)


def build_doc_verification(question):
    """Return the doc_verification block or None (empty question); the
    lookup leg never raises and never blocks the main diagnosis."""
    q = normalize_text(question)
    if not q:
        return None
    try:
        return _doc_lookup.lookup_config_topic(
            q, _doc_lookup.SKILL_DOC_TOPICS)
    except Exception as exc:  # defense in depth: lookup never raises
        return {"matched": False, "docs": [], "source": "llms-index",
                "note": "DEGRADED: %s" % exc}


# Inline boundary assertions for the doc-verification wiring
# (normal / boundary / invalid), executed on every run before main.
assert is_config_consult("\u600e\u4e48\u914d\u7f6e\u8de8\u57df") is True          # normal: consult signal
assert is_config_consult("AccessDenied") is False         # boundary: no signal
assert is_config_consult("") is False                     # invalid: empty
assert should_verify_doc("", "exact") is False            # invalid: empty question
assert should_verify_doc(None, "exact") is False          # invalid: None question
assert should_verify_doc("AccessDenied", "exact") is False  # normal: exact hit, not consult
assert should_verify_doc("AccessDenied \u600e\u4e48\u529e", "exact") is True  # normal: consult signal
assert should_verify_doc("\u5e2e\u6211\u770b\u770b\u5565\u95ee\u9898", "none") is True        # normal: Step-A miss
assert build_doc_verification("") is None                 # invalid: empty skipped
assert build_doc_verification(None) is None               # invalid: None skipped
assert build_doc_verification("   ") is None              # boundary: whitespace skipped

# Online-shape self-test without network: stub the fetcher with a fake
# index + body and assert the matched/docs/excerpt wiring end-to-end.
_orig_fetch = _doc_lookup._fetch_text
_orig_cache = _doc_lookup.CACHE_FILE
_orig_write = _doc_lookup._atomic_write_cache
_fake_cache = os.path.join(
    tempfile.gettempdir(),
    "oss-skill-docs-selftest-%d" % os.getpid(), "never-written.txt")
_fake_index = ("- [\u4e0a\u4f20\u5bf9\u8c61](https://help.aliyun.com/zh/oss/upload.md): "
               "\u4e0a\u4f20\u6587\u4ef6\u7684\u64cd\u4f5c\u8bf4\u660e\u3002\n")
_fake_body = "# \u4e0a\u4f20\u5bf9\u8c61\n\n\u8fd9\u662f\u4e0a\u4f20\u6587\u6863\u7684\u6b63\u6587\u6bb5\u843d\u3002"


def _stub_fetch_ok(url, timeout=15):
    if url.endswith("llms.txt"):
        return _fake_index
    return _fake_body


def _stub_fetch_fail(url, timeout=15):
    raise RuntimeError("offline-selftest")


try:
    _doc_lookup._fetch_text = _stub_fetch_ok
    _doc_lookup.CACHE_FILE = _fake_cache
    _doc_lookup._atomic_write_cache = lambda text: None
    with contextlib.redirect_stderr(io.StringIO()):
        _online_check = _doc_lookup.lookup_config_topic(
            "OSS \u4e0a\u4f20\u5931\u8d25", _doc_lookup.SKILL_DOC_TOPICS)
finally:
    _doc_lookup._fetch_text = _orig_fetch
    _doc_lookup.CACHE_FILE = _orig_cache
    _doc_lookup._atomic_write_cache = _orig_write
assert _online_check["matched"] is True                       # online shape
assert _online_check["docs"][0]["url"].endswith("/upload.md")
assert _online_check["docs"][0]["excerpt"] == "\u8fd9\u662f\u4e0a\u4f20\u6587\u6863\u7684\u6b63\u6587\u6bb5\u843d\u3002"
assert _online_check["note"] is None
assert _online_check["source"] == "llms-index"

# Offline self-test without network: failing fetcher + absent cache must
# degrade (matched False, DEGRADED note) and never raise or block.
try:
    _doc_lookup._fetch_text = _stub_fetch_fail
    _doc_lookup.CACHE_FILE = _fake_cache
    with contextlib.redirect_stderr(io.StringIO()):
        _offline_check = _doc_lookup.lookup_config_topic(
            "OSS \u4e0a\u4f20\u5931\u8d25", _doc_lookup.SKILL_DOC_TOPICS)
finally:
    _doc_lookup._fetch_text = _orig_fetch
    _doc_lookup.CACHE_FILE = _orig_cache
assert _offline_check["matched"] is False                     # offline shape
assert _offline_check["docs"] == []
assert _offline_check["note"].startswith("DEGRADED")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Knowledge-driven OSS upload/download error-code diagnosis "
                    "(zero cloud API calls)."
    )
    parser.add_argument("--error-code", dest="error_code", default=None,
                        help="OSS error code from the response body (fuzzy OK)")
    parser.add_argument("--http-status", dest="http_status", default=None,
                        help="HTTP status code, e.g. 403")
    parser.add_argument("--request-id", dest="request_id", default=None,
                        help="OSS RequestId, echoed for support escalation")
    parser.add_argument("--bucket", dest="bucket", default=None,
                        help="Bucket name for context (not validated remotely)")
    parser.add_argument("--operation", dest="operation", default=None,
                        help="upload or download")
    parser.add_argument("--question", dest="question", default=None,
                        help="Customer's original wording (optional); "
                             "enables the official-doc verification leg")
    args = parser.parse_args(argv)

    exit_code, result = diagnose(
        error_code=args.error_code,
        http_status=args.http_status,
        request_id=args.request_id,
        bucket=args.bucket,
        operation=args.operation,
        question=args.question,
    )
    # Step B: official-doc verification (embedded knowledge first, doc leg
    # second). NEXT_ACTION state machine is untouched; without --question
    # the output is byte-identical to the pre-integration behavior.
    if should_verify_doc(args.question,
                         (result.get("match") or {}).get("type")):
        doc_verification = build_doc_verification(args.question)
        if doc_verification is not None:
            result["doc_verification"] = doc_verification
    if result["status"] in ("DEGRADED", "FAIL"):
        # F-3: stderr [WARN] trace for degraded/failed knowledge runs.
        print(degrade_warn_line(result["status"],
                                (result.get("match") or {}).get("type") or ""),
              file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("STATUS: {0}".format(result["status"]))
    print("NEXT_ACTION: {0}".format(result["next_action"]))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
