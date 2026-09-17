#!/usr/bin/env python3
"""
oss_cors_diagnosis.py -- Browser / mini-program direct-upload & CORS diagnosis
===============================================================================
SECURITY: READ-ONLY. Only issues GetBucketInfo, GetBucketCors (+ ListBuckets
fallback) to the OSS control plane and GetCallerIdentity to STS. Never
mutates anything: PutBucketCors / PutObject and any other write API are
ABSOLUTELY PROHIBITED -- the standard CORS rule and PostObject form
templates are printed as text for the user to apply manually. Credentials
come exclusively from the default credential chain (environment variables
for the OSS SDK, aliyun CLI default chain for STS); AK/SK are never read,
printed, or passed explicitly.

Diagnoses:
  * browser / mini-program direct-upload failures caused by missing or
    non-matching CORS rules (preflight OPTIONS rejected, no
    Access-Control-Allow-Origin, expose-headers gaps such as ETag /
    x-oss-request-id)
  * PostObject form direct-upload policy checks (expiration UTC semantics,
    form field completeness, x: custom variables as standalone form fields)
  * outputs the standard CORS configuration template and the PostObject
    form template (text only -- never applies any configuration)

Output contract (04-spec): stdout carries a structured JSON report followed
by the machine-consumable lines:
    STATUS: OK | DEGRADED
    NEXT_ACTION: <one actionable sentence>

Usage:
  python3 oss_cors_diagnosis.py --bucket <name> \
      [--origin <browser-Origin>] [--endpoint <endpoint>] [--region <region>] \
      [--policy-expiration <ISO8601-GMT>]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone

import _oss_client
import _doc_lookup
from _oss_client import OssClientError

_DEFAULT_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"

# Upload-relevant HTTP methods a browser preflight (OPTIONS) may ask for.
_UPLOAD_METHODS = ("PUT", "POST", "HEAD")


# ---------------------------------------------------------------------------
# Pure functions (each carries inline boundary assertions:
# normal / boundary / invalid inputs)
# ---------------------------------------------------------------------------

def normalize_origin(raw: str) -> str:
    """Normalize a browser Origin value for comparison (lowercase, trim)."""
    return (raw or "").strip().lower()


assert normalize_origin("https://App.Example.com") == "https://app.example.com"  # normal: case
assert normalize_origin("  http://a.com  ") == "http://a.com"  # boundary: whitespace
assert normalize_origin("") == ""  # invalid: empty
assert normalize_origin(None) == ""  # invalid: missing


_BUCKET_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")


def valid_bucket_name(name: str) -> bool:
    """OSS bucket name rule: 3-63 chars, lowercase letters/digits/hyphens,
    must start and end with a letter or digit."""
    return bool(_BUCKET_NAME_RE.match(name or ""))


assert valid_bucket_name("test-agentceping") is True  # normal
assert valid_bucket_name("abc") is True  # boundary: min length
assert valid_bucket_name("img-archive-prod-2026-07") is True  # boundary: digits
assert valid_bucket_name("ab") is False  # invalid: too short
assert valid_bucket_name("Test-Bucket") is False  # invalid: uppercase
assert valid_bucket_name("-abc") is False  # invalid: leading hyphen
assert valid_bucket_name("") is False  # invalid: empty


def origin_matches(pattern: str, origin: str) -> bool:
    """Match a CORS AllowedOrigin pattern against the request Origin.

    OSS rules (official CORS spec): the pattern may contain at most ONE '*'
    wildcard; '*' alone matches every origin; matching is case-insensitive.
    """
    p = normalize_origin(pattern)
    o = normalize_origin(origin)
    if not p or not o:
        return False
    if p == "*":
        return True
    if "*" not in p:
        return p == o
    # one wildcard: prefix + suffix match, non-overlapping
    prefix, _, suffix = p.partition("*")
    if "*" in suffix:  # more than one wildcard -> treat as no match
        return False
    return len(o) >= len(prefix) + len(suffix) and \
        o.startswith(prefix) and o.endswith(suffix)


assert origin_matches("https://app.example.com", "https://app.example.com") is True  # normal: exact
assert origin_matches("*", "https://anything.com") is True  # normal: wildcard-all
assert origin_matches("https://*.example.com", "https://a.example.com") is True  # boundary: wildcard subdomain
assert origin_matches("https://*.example.com", "https://example.com") is False  # boundary: bare domain vs subdomain wildcard
assert origin_matches("http://a.com", "https://a.com") is False  # invalid pair: scheme mismatch
assert origin_matches("", "https://a.com") is False  # invalid: empty pattern


def method_allowed(rule_methods, method: str) -> bool:
    """Whether a CORS rule's AllowedMethods covers the upload method."""
    m = (method or "").upper()
    if not m:
        return False
    return any((x or "").upper() == m for x in (rule_methods or []))


assert method_allowed(["GET", "PUT", "POST", "HEAD"], "PUT") is True  # normal
assert method_allowed(["get"], "GET") is True  # boundary: lowercase rule
assert method_allowed(["GET"], "POST") is False  # invalid: method absent
assert method_allowed([], "PUT") is False  # invalid: empty rule
assert method_allowed(["PUT"], "") is False  # invalid: empty method


def find_matching_rule(rules, origin: str, method: str):
    """Return (index, rule) of the first rule matching origin+method, else
    (None, None). OSS evaluates rules in order; the first match wins."""
    o = normalize_origin(origin)
    if not o or not rules:
        return None, None
    for i, rule in enumerate(rules):
        origins = rule.get("allowed_origins") or []
        if any(origin_matches(p, o) for p in origins) and \
                method_allowed(rule.get("allowed_methods"), method):
            return i, rule
    return None, None


_RULES_A = [{"allowed_origins": ["https://app.example.com"],
             "allowed_methods": ["PUT", "POST", "HEAD"],
             "allowed_headers": ["*"], "expose_headers": [],
             "max_age_seconds": 600}]
assert find_matching_rule(_RULES_A, "https://app.example.com", "PUT")[0] == 0  # normal
assert find_matching_rule(_RULES_A, "https://evil.com", "PUT") == (None, None)  # invalid: origin mismatch
assert find_matching_rule(_RULES_A, "https://app.example.com", "") == (None, None)  # invalid: no method
assert find_matching_rule([], "https://app.example.com", "PUT") == (None, None)  # boundary: no rules


def expose_headers_gap(rules) -> list:
    """Collect expose-headers that browser SDKs commonly need but none of
    the configured rules exposes (case-insensitive): ETag (the SDK needs it
    to confirm the uploaded object / drive resumable upload) and
    x-oss-request-id (troubleshooting)."""
    needed = {"etag": "ETag", "x-oss-request-id": "x-oss-request-id"}
    exposed = set()
    for rule in rules or []:
        for h in rule.get("expose_headers") or []:
            exposed.add((h or "").strip().lower())
    return [label for key, label in needed.items() if key not in exposed]


assert expose_headers_gap([{"expose_headers": ["ETag", "x-oss-request-id"]}]) == []  # normal: complete
assert expose_headers_gap([{"expose_headers": ["ETag"]}]) == ["x-oss-request-id"]  # boundary: partial
assert expose_headers_gap([{"expose_headers": []}]) == ["ETag", "x-oss-request-id"]  # boundary: none
assert expose_headers_gap([]) == ["ETag", "x-oss-request-id"]  # invalid: no rules


def parse_policy_expiration(expiration: str):
    """Parse a PostObject policy `expiration` into an aware UTC datetime.

    OSS treats ALL policy time values as UTC (anti-pattern 0006-00000213:
    do not blame timezone fill-in for 'policy expired'). Accepts ISO-8601
    with 'Z' or an explicit offset; returns None when unparseable.
    """
    s = (expiration or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        # Policy values must be UTC; a naive timestamp is ambiguous.
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


assert parse_policy_expiration("2026-08-27T10:00:00Z") is not None  # normal
assert parse_policy_expiration("2026-08-27T10:00:00+08:00").hour == 2  # boundary: offset converted to UTC
assert parse_policy_expiration("not-a-date") is None  # invalid
assert parse_policy_expiration("") is None  # invalid: empty


def policy_expiration_status(expiration: str, now_utc: datetime) -> str:
    """Classify a PostObject policy expiration: valid | expired |
    invalid_format. now_utc must be timezone-aware UTC."""
    dt = parse_policy_expiration(expiration)
    if dt is None:
        return "invalid_format"
    return "valid" if dt > now_utc else "expired"


_NOW = datetime(2026, 8, 27, 4, 0, 0, tzinfo=timezone.utc)
assert policy_expiration_status("2026-08-27T10:00:00Z", _NOW) == "valid"  # normal: future
assert policy_expiration_status("2026-08-27T03:59:59Z", _NOW) == "expired"  # boundary: past
assert policy_expiration_status("garbage", _NOW) == "invalid_format"  # invalid


# PostObject policy `expiration` timezone anti-pattern (EC 0006-00000213),
# ported verbatim in substance from cse-oss-assistant references/
# anti-patterns.md and re-verified against the official help.aliyun.com EC
# 0006-00000213 doc: OSS parses `expiration` as an ISO8601 GMT/UTC instant
# (trailing 'Z'), so a Beijing-time (UTC+8) value parses 8h LATER and does
# NOT expire early -- never blame a timezone fill-in mistake.
_POLICY_EXPIRATION_ANTIPATTERN = (
    "PostObject policy expiration is an ISO8601 GMT/UTC timestamp with a "
    "trailing 'Z' (e.g. 2023-02-19T13:19:00.000Z); OSS parses it as UTC "
    "(Beijing time = UTC+8). Filling Beijing time does NOT make it expire 8h "
    "early -- it parses 8h LATER -- so do NOT attribute EC 0006-00000213 to a "
    "timezone fill-in mistake. The real root causes are: (1) the validity "
    "window is too short (the client holds the policy, or network delay, so it "
    "arrives already expired); (2) the client caches and reuses a stale policy "
    "past expiry instead of re-issuing one per session; (3) the policy-issuing "
    "server's clock is skewed behind standard time. Official fix: make sure the "
    "expiration value is well-formed AND send the PostObject request before it "
    "expires.")


def build_policy_expiration_check(expiration: str, now_utc: datetime) -> dict:
    """Offline check of a customer-supplied PostObject policy `expiration`
    (pure function, no network). Classifies it against the current UTC time
    and always carries the timezone anti-pattern guidance."""
    status = policy_expiration_status(expiration, now_utc)
    dt = parse_policy_expiration(expiration)
    check = {
        "provided_expiration": expiration,
        "status": status,
        "parsed_utc": dt.isoformat().replace("+00:00", "Z") if dt else None,
        "server_now_utc": now_utc.isoformat().replace("+00:00", "Z"),
    }
    if status == "expired":
        check["finding"] = (
            "The policy expiration is already in the past relative to the "
            "current UTC time -- a PostObject request now would return EC "
            "0006-00000213 (policy expired).")
    elif status == "invalid_format":
        check["finding"] = (
            "The expiration value is not a valid ISO8601 GMT timestamp "
            "(expected e.g. 2023-02-19T13:19:00.000Z); OSS cannot parse it.")
    else:
        check["finding"] = (
            "The expiration is a valid future UTC timestamp; if uploads still "
            "report EC 0006-00000213, the window is too short or a stale "
            "policy is being reused.")
    check["timezone_antipattern"] = _POLICY_EXPIRATION_ANTIPATTERN
    return check


_PEC_NOW = datetime(2026, 8, 27, 4, 0, 0, tzinfo=timezone.utc)
assert build_policy_expiration_check("2026-08-27T10:00:00Z", _PEC_NOW)["status"] == "valid"  # normal: future
assert build_policy_expiration_check("2026-08-27T03:59:59Z", _PEC_NOW)["status"] == "expired"  # boundary: past
assert build_policy_expiration_check("garbage", _PEC_NOW)["status"] == "invalid_format"  # invalid
assert build_policy_expiration_check("", _PEC_NOW)["status"] == "invalid_format"  # invalid: empty
assert "0006-00000213" in build_policy_expiration_check("", _PEC_NOW)["timezone_antipattern"]  # anti-pattern carried
assert build_policy_expiration_check(
    "2026-08-27T12:00:00+08:00", _PEC_NOW)["parsed_utc"] == "2026-08-27T04:00:00Z"  # boundary: UTC+8 -> UTC (parses LATER, not earlier)


def build_recommendations(cors: dict, matched_idx, origin: str,
                          gaps: list, bucket_acl: str) -> list:
    """Evidence-based findings. Templates are output separately; this list
    only carries attribution and manual-guidance pointers."""
    recs = []
    if cors is None:
        recs.append(
            "CORS configuration could not be read (see recorded errors); "
            "grant oss:GetBucketCors per references/ram-policies.md and "
            "re-run, or check the bucket's CORS page in the OSS console "
            "manually.")
        return recs
    if not cors.get("configured"):
        recs.append(
            "The bucket has NO CORS rule configured (GetBucketCors returned "
            "NoSuchCORSConfiguration). Any cross-origin browser/mini-program "
            "request will be blocked by the browser's same-origin policy "
            "(no Access-Control-Allow-Origin in the response). Apply the "
            "standard CORS template from the report's `templates` section "
            "via the OSS console or PutBucketCors (manual operation -- this "
            "skill is read-only and never writes configuration).")
        if bucket_acl == "private":
            recs.append(
                "The bucket ACL is private: browser direct upload must carry "
                "a valid signature (PostObject policy signature, or a "
                "signed request from STS temporary credentials); CORS alone "
                "does not grant access.")
        return recs
    rules = cors.get("rules") or []
    if origin:
        if matched_idx is None:
            recs.append(
                f"No CORS rule matches Origin={origin} with the upload "
                "method: the preflight OPTIONS (or the actual request) gets "
                "no Access-Control-Allow-Origin and the browser blocks it. "
                "Check the rule's Allowed Origins (scheme included, at most "
                "one '*' wildcard), Allowed Methods (PUT/POST/HEAD for "
                "upload), and rule order; then clear the browser cache "
                "because preflight results are cached (MaxAgeSeconds).")
        else:
            recs.append(
                f"CORS rule #{matched_idx + 1} matches Origin={origin}; if "
                "the browser still reports a CORS error, the stale preflight "
                "cache is the usual cause -- clear the browser cache or test "
                "in private mode, and confirm no proxy/CDN in front of OSS "
                "strips CORS headers.")
    if gaps:
        recs.append(
            "Expose Headers gap: none of the rules exposes "
            f"{', '.join(gaps)}. Browsers hide these response headers from "
            "JavaScript unless listed; SDKs reading ETag (resumable upload, "
            "upload confirmation) or x-oss-request-id (troubleshooting) will "
            "fail or report empty values. Add them to Expose Headers "
            "('Please set the etag of expose-headers' is exactly this fix).")
    if not recs:
        recs.append(
            "CORS rules are configured; if a specific failure persists, "
            "capture the browser DevTools Network panel (OPTIONS status, "
            "response headers) and the x-oss-request-id, and check the "
            "PostObject policy window if the upload uses form direct "
            "upload.")
    return recs


assert isinstance(build_recommendations(None, None, "", [], "private"), list)  # degraded cors
assert any("NO CORS rule" in r for r in build_recommendations(
    {"configured": False}, None, "", [], "private"))  # normal: not configured
assert any("No CORS rule matches" in r for r in build_recommendations(
    {"configured": True, "rules": _RULES_A}, None, "https://evil.com", [], "private"))  # origin mismatch
assert any("Expose Headers gap" in r for r in build_recommendations(
    {"configured": True, "rules": _RULES_A}, 0, "https://app.example.com",
    ["ETag"], "private"))  # expose gap
assert build_recommendations({"configured": True, "rules": _RULES_A}, 0, "", [], "private") != []  # boundary: no origin


# ---------------------------------------------------------------------------
# Standard templates (text output ONLY -- never applied by this skill)
# ---------------------------------------------------------------------------

def standard_cors_template(origin: str) -> dict:
    """Standard CORS rule template for browser direct upload. Printed for
    the user to apply manually (console / PutBucketCors); NEVER executed."""
    origins = [origin] if normalize_origin(origin) else ["https://your-app.example.com"]
    return {
        "apply_via": "OSS console (Permission -> CORS) or PutBucketCors API"
                     " -- manual operation, this skill never writes it",
        "allowed_origins": origins,
        "allowed_origins_note": "exact scheme+host(+port) of the web page; "
                                "at most one '*' wildcard per entry; avoid "
                                "bare '*' in production",
        "allowed_methods": ["GET", "PUT", "POST", "HEAD"],
        "allowed_headers": ["*"],
        "expose_headers": ["ETag", "x-oss-request-id"],
        "expose_headers_note": "required so browser JS can read ETag "
                               "(upload confirmation / resumable upload) and "
                               "x-oss-request-id (troubleshooting)",
        "max_age_seconds": 600,
        "max_age_seconds_note": "preflight (OPTIONS) cache window; after "
                                "changing rules clear the browser cache or "
                                "test in private mode, stale preflight "
                                "results are a top 'CORS config not "
                                "working' cause",
        "return_vary_origin": True,
        "return_vary_origin_note": "enable 'Return Vary: Origin' when "
                                   "responses are cached (CDN/proxy), so "
                                   "different Origins do not share one "
                                   "cached CORS response",
    }


def postobject_form_template(bucket: str, endpoint_host: str) -> dict:
    """PostObject (form direct upload) template + policy checklist. Text
    output only; signing/issuing the policy stays on the user's server."""
    return {
        "endpoint": f"https://{bucket or '<bucket>'}.{endpoint_host or '<region>.aliyuncs.com'}",
        "method": "POST multipart/form-data (NOT PUT)",
        "form_fields_order_note": "the file field MUST be named `file` and "
                                  "be the LAST form field",
        "required_fields": {
            "key": "target object key, may contain ${filename} placeholder",
            "policy": "Base64(JSON policy) issued by YOUR server",
            "OSSAccessKeyId": "the AccessKey id (or STS temporary id)",
            "Signature": "Base64(HMAC-SHA1(policy-base64, AccessKeySecret))",
        },
        "optional_fields": {
            "x-oss-security-token": "REQUIRED when signing with STS "
                                    "temporary credentials",
            "success_action_status": "200/204 to control the success "
                                     "response code",
            "x:<name>": "each custom variable is its OWN standalone form "
                        "field with the x: prefix (case 6A2D1F5BF3B62D3630F7"
                        "8351: empty callback values trace back to empty or "
                        "missing x: form fields; do NOT use the "
                        "x-oss-callback-var header style of "
                        "PutObject/CompleteMultipartUpload here)",
        },
        "policy_checklist": {
            "expiration_is_utc": "expiration is an ISO8601 GMT/UTC "
                                 "timestamp with a trailing 'Z' (e.g. "
                                 "2023-02-19T13:19:00.000Z). OSS parses it "
                                 "as UTC (Beijing time = UTC+8). Filling "
                                 "Beijing time does NOT make it expire 8h "
                                 "early, so do not blame timezone fill-in "
                                 "for EC 0006-00000213; real causes: window "
                                 "too short, client reusing a stale cached "
                                 "policy, or the policy-issuing server clock "
                                 "skewed backward",
            "conditions_must_match_form": "every form field submitted must "
                                          "be covered by policy conditions "
                                          "(bucket, key prefix, "
                                          "content-length range), otherwise "
                                          "InvalidAccessKeyId/"
                                          "SignatureDoesNotMatch-style "
                                          "rejections occur",
            "reissue_before_expiry": "issue a fresh policy per upload "
                                     "session; never cache beyond the "
                                     "expiration window",
        },
    }


assert standard_cors_template("https://a.com")["allowed_origins"] == ["https://a.com"]  # normal
assert standard_cors_template("")["allowed_origins"] == ["https://your-app.example.com"]  # boundary: placeholder
assert "ETag" in standard_cors_template("")["expose_headers"]  # expose headers present
assert "file" in postobject_form_template("b", "oss-cn-hangzhou.aliyuncs.com")["form_fields_order_note"]  # normal
assert postobject_form_template("", "")["endpoint"].startswith("https://")  # boundary: empty args


# ---------------------------------------------------------------------------
# Diagnosis orchestration
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Official-doc verification hook (runtime doc lookup, batch-3 integration)
# ---------------------------------------------------------------------------

_CUSTOMER_QUESTION = ""
_POLICY_NOTE = ""


def _doc_verification(status: str):
    """Step B: verify the customer's original wording against official OSS
    docs. Skipped when --question is absent (no-arg regression unchanged)
    or when Step A already answered (status OK) a non-consultation error
    question. Returns the constant four-key dict from _doc_lookup; never
    raises and never blocks the main diagnosis."""
    q = _CUSTOMER_QUESTION.strip()
    if not q:
        return None
    if status == "OK" and not _doc_lookup.is_consult_question(q):
        return None  # Step A hit on a pure error question
    return _doc_lookup.lookup_config_topic(q)


assert _doc_verification("OK") is None  # invalid: no --question -> unchanged
_CUSTOMER_QUESTION = "InvalidObjectState error, rule not effective"
assert _doc_verification("OK") is None  # normal: Step A hit, non-consultation
_CUSTOMER_QUESTION = "how to configure it?"
assert _doc_lookup.is_consult_question(_CUSTOMER_QUESTION) is True  # signal
_CUSTOMER_QUESTION = ""


def _emit(report: dict, status: str, next_action: str) -> int:
    """Print the structured report + STATUS/NEXT_ACTION contract lines."""
    report["status"] = status
    if _POLICY_NOTE and _POLICY_NOTE not in next_action:
        next_action = (next_action.rstrip() + " " + _POLICY_NOTE).strip()
    report["next_action"] = next_action
    dv = _doc_verification(status)
    if dv is not None:
        report["doc_verification"] = dv
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"STATUS: {status}")
    print(f"NEXT_ACTION: {next_action}")
    return 0 if status in ("OK", "DEGRADED") else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose browser/mini-program direct-upload failures "
                    "and CORS configuration on an OSS bucket (read-only; "
                    "outputs templates, never writes configuration)",
    )
    parser.add_argument("--bucket", default="", required=False,
                        help="OSS bucket name to diagnose (required; when absent the script emits FAIL and asks)")
    parser.add_argument("--origin", default="",
                        help="The browser Origin the upload page sends "
                             "(optional; e.g. https://app.example.com). "
                             "When provided, it is matched against the "
                             "bucket's CORS rules.")
    parser.add_argument("--endpoint", default="",
                        help="Query endpoint (optional; the endpoint of the "
                             "region where the bucket was created)")
    parser.add_argument("--region", default="",
                        help="Expected region (optional; used to build the "
                             "query endpoint when --endpoint is absent)")
    parser.add_argument("--question", default="",
                        help="Customer's original wording (optional); when "
                             "provided, the report carries a doc_verification "
                             "section matched against official OSS docs")
    parser.add_argument("--policy-expiration", default="",
                        help="PostObject policy `expiration` value to check "
                             "offline (optional; ISO8601 GMT, e.g. "
                             "2023-02-19T13:19:00.000Z). Classifies it "
                             "against the current UTC time and restates the "
                             "timezone anti-pattern for EC 0006-00000213.")
    args = parser.parse_args()

    # Missing-bucket guard: most real tickets never name a bucket, so a bare
    # argparse exit 2 leaves the customer with no next step. Ask for the name
    # and surface the buckets this credential can actually see.
    if not (args.bucket or "").strip():
        _hint = []
        _herrs = []
        try:
            try:
                _all = _oss_client.list_buckets()
            except TypeError:
                _all = _oss_client.list_buckets(prefix="")
            _hint = [b["name"] for b in _all][:30]
        except Exception as e:
            _herrs.append({"category": "degraded", "code": "ListBucketsFailed",
                           "message": str(e)[:200]})
            print(f"[WARN] ListBuckets bucket-name hint degraded: {e}",
                  file=sys.stderr)
        _rep = {
            "skill": globals().get("_SKILL_NAME", "alibabacloud-oss-browser-upload-cors-diagnosis"),
            "bucket": "",
            "buckets_in_account": _hint,
            "errors": _herrs,
            "auto_filled": [],
        }
        _na = ("Ask the user which OSS bucket the issue concerns; "
               "buckets_in_account lists up to 30 buckets visible to the "
               "current credential.")
        if not _hint:
            _na += (" No bucket is listable with the current credential: ask "
                    "for the exact bucket name and its region instead.")
        return _emit(_rep, "FAIL", _na)
    global _CUSTOMER_QUESTION, _POLICY_NOTE
    _CUSTOMER_QUESTION = args.question or ""

    auto_filled = []
    origin = normalize_origin(args.origin)

    report = {
        "skill": "alibabacloud-oss-browser-upload-cors-diagnosis",
        "bucket": args.bucket,
        "origin": origin or None,
        "identity": {"uid": "",
                     "note": "derived via sts get-caller-identity; empty "
                             "means the identity pre-check degraded"},
        "query_endpoint": "",
        "auto_filled": auto_filled,
        "bucket_info": None,
        "cors": None,
        "matched_rule_index": None,
        "expose_headers_gap": [],
        "recommendations": [],
        "policy_expiration_check": None,
        "templates": {
            "cors_rule": standard_cors_template(origin),
            "postobject_form": postobject_form_template(args.bucket, ""),
        },
        "errors": [],
    }

    # Offline PostObject policy-expiration check (anti-pattern EC 0006-00000213):
    # when the customer supplies their policy `expiration`, classify it against
    # the current UTC time and carry the timezone anti-pattern into NEXT_ACTION.
    if (args.policy_expiration or "").strip():
        report["policy_expiration_check"] = build_policy_expiration_check(
            args.policy_expiration.strip(), datetime.now(timezone.utc))
        auto_filled.append(
            "policy expiration checked offline against the current UTC time "
            "(--policy-expiration)")
        if report["policy_expiration_check"]["status"] in ("expired",
                                                           "invalid_format"):
            _pec = report["policy_expiration_check"]
            _POLICY_NOTE = _pec["finding"] + " " + _pec["timezone_antipattern"]

    # Step 0: bucket name sanity (cheap, avoids a pointless round-trip and
    # converges invalid-name errors into a clear finding).
    if not valid_bucket_name(args.bucket):
        report["errors"].append({
            "category": "invalid",
            "code": "InvalidBucketName",
            "message": f"'{args.bucket}' is not a valid OSS bucket name "
                       "(3-63 chars, lowercase letters/digits/hyphens, must "
                       "start and end with a letter or digit)",
        })
        report["recommendations"] = [
            "Fix the bucket name and re-run; bucket names are global and "
            "case-sensitive lowercase."]
        sys.exit(_emit(
            report, "DEGRADED",
            "The bucket name is malformed; correct it (lowercase, 3-63 "
            "chars, no leading/trailing hyphen) and re-run the diagnosis."))

    # Step 1: identity pre-check / UID derivation (unconditional, degraded
    # with [WARN] on failure -- UID is only a traceability label).
    report["identity"]["uid"] = _oss_client.resolve_uid()

    # Step 2: resolve the query endpoint.
    endpoint = (args.endpoint or "").strip().lower().rstrip("/")
    for scheme in ("https://", "http://"):
        if endpoint.startswith(scheme):
            endpoint = endpoint[len(scheme):]
    if endpoint:
        pass
    elif args.region.strip():
        region = args.region.strip().lower()
        endpoint = f"oss-{region}.aliyuncs.com"
        auto_filled.append(f"query endpoint derived from --region: {endpoint}")
    else:
        endpoint = _DEFAULT_ENDPOINT
        auto_filled.append(
            f"query endpoint auto-defaulted to {endpoint} "
            "(no --endpoint/--region provided)")
    report["query_endpoint"] = endpoint
    report["templates"]["postobject_form"] = postobject_form_template(
        args.bucket, endpoint)

    # Step 3: GetBucketInfo -- existence + metadata evidence.
    bucket_info = None
    try:
        bucket_info = _oss_client.get_bucket_info(args.bucket, endpoint)
        report["bucket_info"] = bucket_info
    except OssClientError as e:
        print(f"[WARN] GetBucketInfo degraded ({e.category}): {e}",
              file=sys.stderr)
        report["errors"].append(e.to_dict())
        # Fallback: ListBuckets prefix lookup to locate the bucket region.
        try:
            located = _oss_client.list_buckets(prefix=args.bucket)
            hits = [b for b in located if b["name"] == args.bucket]
            if hits:
                report["bucket_info"] = {
                    "name": hits[0]["name"],
                    "location": hits[0]["location"],
                    "source": "ListBuckets fallback (GetBucketInfo degraded)",
                }
                bucket_info = report["bucket_info"]
            elif located is not None:
                report["errors"].append({
                    "category": "not_found",
                    "code": "ListBucketsNoMatch",
                    "message": f"ListBuckets(prefix={args.bucket}) returned "
                               f"{len(located)} bucket(s), none named "
                               f"'{args.bucket}' in this account",
                })
        except OssClientError as e2:
            print(f"[WARN] ListBuckets fallback degraded ({e2.category}): {e2}",
                  file=sys.stderr)
            report["errors"].append(e2.to_dict())

    # Re-derive the query endpoint from the bucket's real location. GetBucketInfo
    # answers on any public endpoint but reports the serving region, and the
    # ListBuckets fallback carries the same location; the region-scoped calls
    # below only succeed on that region's endpoint.
    _loc = str((bucket_info or {}).get("location") or "")
    if _loc.startswith("oss-"):
        _ep = _loc + ".aliyuncs.com"
        if _ep != endpoint:
            auto_filled.append(
                "query endpoint re-derived from bucket location %s: %s"
                % (_loc, _ep))
            endpoint = _ep
            report["query_endpoint"] = _ep

    # Identity-chain guard: identity.uid is resolved from the aliyun CLI
    # default profile while bucket evidence comes from the SDK credential
    # chain, so the two can belong to different accounts and silently
    # mislabel the scope of every conclusion below.
    _owner = str((bucket_info or {}).get("owner_id") or "")
    _caller = str((report.get("identity") or {}).get("uid") or "")
    if _owner:
        try:
            report["identity"]["bucket_owner_uid"] = _owner
            report["identity"]["uid_matches_bucket_owner"] = (_owner == _caller)
        except Exception:
            pass
        if _owner != _caller:
            print(f"[WARN] identity consistency: caller UID {_caller} (aliyun "
                  f"CLI default profile) differs from bucket owner UID "
                  f"{_owner} (resolved through the data-plane credential); "
                  f"findings reflect the data-plane account only.",
                  file=sys.stderr)

    if not bucket_info:
        # Degraded before the CORS check -- attribute the root error.
        root = report["errors"][0] if report["errors"] else {"category": "unknown"}
        cat = root.get("category", "unknown")
        report["recommendations"] = [
            "CORS state could not be read because the bucket metadata query "
            "failed; the standard templates in this report are still valid "
            "for manual application once access is restored."]
        if cat == "credentials":
            next_action = (
                "No credentials in the environment credential chain; configure "
                "the default credential chain (aliyun configure / "
                "environment variables), never pass AK/SK manually.")
        elif cat == "not_found":
            next_action = (
                f"Bucket '{args.bucket}' was not found (NoSuchBucket); "
                "verify the bucket name spelling and the account that owns "
                "it, then re-run the diagnosis.")
        elif cat == "permission":
            next_action = (
                "Access denied (403): grant the caller oss:GetBucketInfo / "
                "oss:GetBucketCors / oss:ListBuckets (see "
                "references/ram-policies.md) or confirm the bucket belongs "
                "to this account, then re-run.")
        elif cat == "endpoint":
            next_action = (
                "The request hit the wrong region's endpoint; re-run with "
                "the endpoint of the region where the bucket was created.")
        elif cat == "network":
            next_action = (
                "Network/DNS failure reaching the endpoint host; verify DNS "
                "resolution and local network, then re-run.")
        else:
            next_action = (
                "OSS control-plane query failed; review the recorded errors "
                "and re-run after fixing the root cause.")
        sys.exit(_emit(report, "DEGRADED", next_action))

    # Step 4: GetBucketCors -- the core CORS evidence call.
    cors = None
    try:
        cors = _oss_client.get_bucket_cors(args.bucket, endpoint)
        report["cors"] = cors
    except OssClientError as e:
        print(f"[WARN] GetBucketCors degraded ({e.category}): {e}",
              file=sys.stderr)
        report["errors"].append(e.to_dict())

    # Step 5: verdict + recommendations + template guidance.
    matched_idx = None
    if cors is not None and cors.get("configured") and origin:
        matched_idx, _matched = find_matching_rule(
            cors.get("rules"), origin, "POST")
        report["matched_rule_index"] = matched_idx
    if cors is not None and cors.get("configured"):
        report["expose_headers_gap"] = expose_headers_gap(cors.get("rules"))
    acl = (bucket_info or {}).get("acl", "")
    report["recommendations"] = build_recommendations(
        cors, matched_idx, origin, report["expose_headers_gap"], acl)
    if report.get("policy_expiration_check") and \
            report["policy_expiration_check"]["status"] in ("expired",
                                                            "invalid_format"):
        _pec = report["policy_expiration_check"]
        report["recommendations"].append(
            _pec["finding"] + " " + _pec["timezone_antipattern"])

    # Step 6: status + next action.
    if cors is None:
        # Bucket metadata OK but CORS unreadable -> degraded CORS check.
        root = report["errors"][-1] if report["errors"] else {}
        if root.get("category") == "permission":
            next_action = (
                "GetBucketCors was denied (403): grant oss:GetBucketCors "
                "(see references/ram-policies.md) and re-run; meanwhile the "
                "standard CORS/PostObject templates in this report can be "
                "applied manually from the OSS console.")
        else:
            next_action = (
                "The CORS query failed (see recorded errors); re-run after "
                "fixing the root cause, or inspect the bucket's CORS page "
                "in the OSS console manually.")
        sys.exit(_emit(report, "DEGRADED", next_action))

    if not cors.get("configured"):
        next_action = (
            "The bucket has no CORS rule configured ('CORS not configured' "
            "confirmed by GetBucketCors): apply the standard CORS template "
            "from this report via the OSS console or PutBucketCors (manual "
            "operation), then clear the browser cache and retry the upload.")
    elif origin and matched_idx is None:
        next_action = (
            f"No CORS rule matches Origin={origin}; update the rule's "
            "Allowed Origins/Methods manually per the template, clear the "
            "browser preflight cache, and retry.")
    elif report["expose_headers_gap"]:
        next_action = (
            "Add the missing Expose Headers ("
            + ", ".join(report["expose_headers_gap"]) +
            ") to the CORS rule manually per the template so browser JS can "
            "read them.")
    else:
        next_action = (
            "CORS configuration verified against the provided Origin; if the "
            "upload still fails, capture the browser DevTools Network panel "
            "(OPTIONS status + response headers) and check the PostObject "
            "policy checklist in this report.")
    sys.exit(_emit(report, "OK", next_action))


if __name__ == "__main__":
    sys.exit(main())
