#!/usr/bin/env python3
"""
oss_event_notification_diagnosis.py -- OSS event-notification & upload-callback
================================================================================
diagnosis (read-only)
SECURITY: READ-ONLY. Only issues GetBucketInfo, GetBucketNotification and
GetBucketCallbackPolicy to the OSS control plane and GetCallerIdentity to
STS. Never mutates anything: event-notification rules and callback policies
are only READ; creating or changing them is the user's own console task.
Credentials come exclusively from the default credential chain (environment
variables for the OSS SDK, aliyun CLI default chain for STS); AK/SK are
never read, printed, or passed explicitly.

Diagnoses:
  * event-notification-not-triggering checklist: rule existence check
    (GetBucketNotification), expected-event-type matching against the rule
    set, per-region rule limit, dependent-service (SMQ/MNS, EventBridge)
    console check path, 10-minute rule propagation delay, versioned-delete
    caveat, x-oss-event-status response header check
  * upload-callback failure attribution (CallbackFailed): 5-second response
    limit, non-JSON response body, HTTP status (502/400/4xx), connectivity
    and HTTPS/SNI certificate constraints, bucket-level callback policy check
  * configuration-correctness advice (manual guidance only)

Output contract (04-spec): stdout carries a structured JSON report followed
by the machine-consumable lines:
    STATUS: OK | DEGRADED
    NEXT_ACTION: <one actionable sentence>

Usage:
  python3 oss_event_notification_diagnosis.py --bucket <name> \
      [--region <region>] [--expected-event <event-type>] \
      [--callback-error "<observed error message>"] \
      [--callback-url <callbackUrl>]
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import sys

import _oss_client
import _doc_lookup
from _oss_client import OssClientError

# Inline contract assertion: an illegal bucket name must degrade to the
# unified OssClientError(category="invalid") -- never a bare oss2 ClientError
# Traceback (measured on oss2 2.19.1: oss2.Bucket.__init__ raises ClientError
# 'The bucket_name is invalid'; the builders convert it, the entry records
# [WARN] + errors[] and still emits STATUS: DEGRADED with exit 0). No
# network call happens on this path.
try:
    _oss_client._build_bucket("Invalid_Bucket!", "oss-cn-hangzhou.aliyuncs.com")
    _INVALID_BUCKET_CATEGORY = "no-error"
except OssClientError as _e:
    _INVALID_BUCKET_CATEGORY = _e.category
except Exception:  # pragma: no cover - regression guard
    _INVALID_BUCKET_CATEGORY = "unexpected-traceback"
assert _INVALID_BUCKET_CATEGORY == "invalid"  # invalid: illegal bucket name
try:
    _oss_client._build_bucket_v4("Invalid_Bucket!",
                                 "https://oss-cn-hangzhou.aliyuncs.com",
                                 "cn-hangzhou")
    _INVALID_BUCKET_V4_CATEGORY = "no-error"
except OssClientError as _e:
    _INVALID_BUCKET_V4_CATEGORY = _e.category
except Exception:  # pragma: no cover - regression guard
    _INVALID_BUCKET_V4_CATEGORY = "unexpected-traceback"
assert _INVALID_BUCKET_V4_CATEGORY == "invalid"  # invalid: V4 builder path

_DEFAULT_REGION = "cn-hangzhou"
# Measured platform limit (official doc): at most 10 event-notification
# rules per region; exceeding it requires contacting technical support.
_MAX_RULES_PER_REGION = 10


# ---------------------------------------------------------------------------
# Pure functions (each carries inline boundary assertions:
# normal / boundary / invalid inputs)
# ---------------------------------------------------------------------------

def region_from_location(location: str) -> str:
    """Convert a bucket location (e.g. 'oss-cn-hangzhou') to its region."""
    loc = (location or "").strip().lower()
    if loc.startswith("oss-"):
        return loc[len("oss-"):]
    return loc


assert region_from_location("oss-cn-hangzhou") == "cn-hangzhou"  # normal
assert region_from_location("cn-shanghai") == "cn-shanghai"  # boundary: already a region
assert region_from_location("") == ""  # invalid: empty


def normalize_event_type(raw: str) -> str:
    """Normalize an OSS event type string (strip/lowercase-insensitive keep).

    Event type names are case-sensitive on the service side; only whitespace
    is stripped. Group wildcards like 'ObjectCreated:*' are preserved.
    """
    return (raw or "").strip()


assert normalize_event_type("ObjectCreated:PutObject") == "ObjectCreated:PutObject"  # normal
assert normalize_event_type("  ObjectRemoved:* ") == "ObjectRemoved:*"  # boundary: whitespace
assert normalize_event_type("") == ""  # invalid: empty
assert normalize_event_type(None) == ""  # invalid: missing


def event_type_covers(rule_events: list, expected_event: str) -> bool:
    """Whether a rule's event list covers the expected event type.

    Coverage semantics (per official doc): an exact match covers the event;
    a group wildcard '<Group>:*' covers every event of that group.
    """
    exp = normalize_event_type(expected_event)
    if not exp:
        return False
    for ev in rule_events or []:
        ev = normalize_event_type(ev)
        if not ev:
            continue
        if ev == exp:
            return True
        if ev.endswith(":*"):
            group = ev[:-2]
            if exp.split(":")[0] == group:
                return True
    return False


assert event_type_covers(["ObjectCreated:PutObject"], "ObjectCreated:PutObject") is True  # normal: exact
assert event_type_covers(["ObjectCreated:*"], "ObjectCreated:PostObject") is True  # normal: group wildcard
assert event_type_covers(["ObjectRemoved:*"], "ObjectCreated:PutObject") is False  # normal: different group
assert event_type_covers([], "ObjectCreated:PutObject") is False  # boundary: empty rule events
assert event_type_covers(["ObjectCreated:*"], "") is False  # invalid: empty expected


def any_rule_covers(rules: list, expected_event: str) -> bool:
    """Whether ANY configured rule covers the expected event type."""
    if not expected_event:
        return False
    for r in rules or []:
        if event_type_covers(r.get("events", []), expected_event):
            return True
    return False


assert any_rule_covers([{"events": ["ObjectCreated:*"]}], "ObjectCreated:PutObject") is True  # normal
assert any_rule_covers([], "ObjectCreated:PutObject") is False  # boundary: no rules
assert any_rule_covers([{"events": ["ObjectCreated:*"]}], "") is False  # invalid: no expected


def classify_callback_error(raw: str) -> dict:
    """Attribute an observed upload-callback error message to a root cause.

    Returns {"kind": ..., "attribution": ..., "advice": [...]} per the
    official 'upload callback errors' documentation:
      * CallbackFailed + non-JSON body     -> non_json_body
      * CallbackFailed + status -1 / timeout / can not connect
                                           -> timeout_or_unreachable (5s limit)
      * CallbackFailed + status 502        -> bad_gateway (server down /
                                              network / callbackUrl missing)
      * CallbackFailed + status 4xx/5xx    -> callback_server_status
      * InvalidArgument (callback json)    -> invalid_callback_argument
      * empty / unrecognized               -> unknown
    """
    msg = (raw or "").strip()
    if not msg:
        return {"kind": "none", "attribution": "", "advice": []}
    low = msg.lower()
    advice_5s = (
        "OSS waits at most 5 seconds for the callback response (fixed, not "
        "configurable); make the callback server answer within 5 seconds, "
        "e.g. move heavy processing to an async queue.")
    advice_json = (
        "The callback server must return HTTP 200 with a JSON body "
        "(Content-Type: application/json); strip any UTF-8 BOM header and "
        "avoid returning stack traces on exceptions.")
    advice_sni = (
        "For HTTPS callbackUrl, set callbackSNI=true so OSS sends SNI "
        "during the TLS handshake; a server that relies on SNI (virtual "
        "hosting / shared certificate) otherwise fails the handshake and "
        "surfaces as a 502 CallbackFailed.")
    if "callbackfailed" in low or "callback failed" in low \
            or "0007-00000203" in low:
        if "not valid json" in low or "json format" in low:
            return {"kind": "non_json_body",
                    "attribution": "the callback server answered OSS but the "
                                   "response body is not valid JSON",
                    "advice": [advice_json]}
        if "reply timeout" in low or "timeout" in low \
                or "can not connect" in low or "error status : -1" in low \
                or "error status: -1" in low:
            return {"kind": "timeout_or_unreachable",
                    "attribution": "OSS could not reach the callbackUrl or "
                                   "the callback server exceeded the "
                                   "5-second response limit",
                    "advice": [advice_5s,
                               "Verify callbackUrl DNS/port from a public "
                               "network; OSS callback source IPs are NOT "
                               "fixed, so IP allowlists cannot solve "
                               "connectivity -- fix DNS, firewall or move "
                               "the callback server onto a public/ECS "
                               "endpoint."]}
        if "error status : 502" in low or "error status: 502" in low \
                or "status : 502" in low or msg.find("502") >= 0:
            return {"kind": "bad_gateway",
                    "attribution": "the callback server (or a proxy in "
                                   "front of it) returned HTTP 502: the "
                                   "web service is not listening, the "
                                   "callbackUrl is wrong/missing, the TLS "
                                   "handshake failed, or the network path "
                                   "is broken",
                    "advice": [advice_sni,
                               "Confirm the callback server process is up "
                               "and listening on the callbackUrl port; "
                               "test with `curl -v <callbackUrl>` from the "
                               "public network; prefer an HTTP callbackUrl "
                               "while debugging, or deploy the callback "
                               "server on an ECS in the same region."]}
        if "error status : 4" in low or "error status: 4" in low \
                or "error status : 5" in low or "error status: 5" in low:
            return {"kind": "callback_server_status",
                    "attribution": "the callback server returned a non-200 "
                                   "HTTP status; OSS treats any non-200 as "
                                   "callback failure (upload itself still "
                                   "succeeded, surfaced as HTTP 203)",
                    "advice": ["Check the callback server logs and return "
                               "exactly HTTP 200 with a JSON body on the "
                               "success path."]}
        return {"kind": "callback_failed_unknown",
                "attribution": "CallbackFailed reported without a "
                               "recognizable sub-cause",
                "advice": [advice_5s, advice_json, advice_sni]}
    if "invalidargument" in low or "not json format" in low \
            or "callback configuration" in low:
        return {"kind": "invalid_callback_argument",
                "attribution": "the callback parameter carried by the upload "
                               "request is malformed (x-oss-callback / "
                               "callback query parameter is not valid "
                               "Base64(JSON))",
                "advice": ["Rebuild the callback parameter as "
                           "Base64(CallbackJson) with properly escaped "
                           "quotes inside callbackBody; custom variables "
                           "must be declared with the x: prefix "
                           "(x-oss-callback-var)."]}
    return {"kind": "unknown",
            "attribution": "the provided error text does not match a known "
                           "upload-callback error pattern",
            "advice": ["Provide the exact OSS error response (ErrorCode / "
                       "ErrorMessage / RequestId) of the failing upload "
                       "(PutObject / PostObject / CompleteMultipartUpload) "
                       "for attribution."]}


assert classify_callback_error("CallbackFailed, Message: Response body is not valid json format.")["kind"] == "non_json_body"  # normal: non-JSON
assert classify_callback_error("CallbackFailed Error status : -1 8.8.8.8:9090 reply timeout, cost:5000ms")["kind"] == "timeout_or_unreachable"  # normal: timeout
assert classify_callback_error("CallbackFailed, Message: Error status : 502.")["kind"] == "bad_gateway"  # normal: 502
assert classify_callback_error("CallbackFailed Error status : 400.")["kind"] == "callback_server_status"  # normal: 4xx
assert classify_callback_error("InvalidArgument: The callback configuration is not json format.")["kind"] == "invalid_callback_argument"  # normal: bad argument
assert classify_callback_error("")["kind"] == "none"  # invalid: empty
assert classify_callback_error("some random text")["kind"] == "unknown"  # invalid: unrecognized
assert classify_callback_error("RequestId: 64E3A7B203F5 500 InternalError")["kind"] == "unknown"  # boundary: a bare '203' substring (inside a RequestId) must NOT route to CallbackFailed


def _host_is_non_public(host: str) -> bool:
    """True when the callbackUrl host is a literal IP in a non-public range
    or a loopback hostname (localhost). Pure string/IP parsing, no DNS.

    Official contract (see references/callback-troubleshooting.md, 0007
    family): callbackUrl must resolve to a PUBLIC IP (0007-00000007);
    internal targets such as 127.0.0.1 are rejected (0007-00000008).
    """
    h = (host or "").strip().lower().rstrip(".")
    if not h:
        return False
    if h == "localhost" or h.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return False
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified)


assert _host_is_non_public("192.168.1.10") is True   # normal: RFC1918
assert _host_is_non_public("10.0.0.5") is True        # normal: RFC1918
assert _host_is_non_public("127.0.0.1") is True       # normal: loopback
assert _host_is_non_public("localhost") is True       # normal: loopback name
assert _host_is_non_public("172.16.9.9") is True      # normal: RFC1918
assert _host_is_non_public("47.98.18.238") is False   # boundary: public IP
assert _host_is_non_public("app.example.com") is False  # boundary: hostname (DNS out of scope)
assert _host_is_non_public("") is False               # invalid: empty


def check_callback_url(url: str) -> dict:
    """Sanity-check a user-provided callbackUrl (no network call is made).

    Returns {"valid": bool, "scheme": str, "notes": [...]}. Only static
    form checks; reachability must be verified by the user/server logs.
    """
    u = (url or "").strip()
    notes = []
    if not u:
        return {"valid": False, "scheme": "", "notes": [
            "No callbackUrl provided; OSS issues the callback to the "
            "callbackUrl carried by each upload request (x-oss-callback) or "
            "by the bucket-level callback policy."]}
    if not (u.startswith("http://") or u.startswith("https://")):
        return {"valid": False, "scheme": "", "notes": [
            "callbackUrl must start with http:// or https://."]}
    scheme = "https" if u.startswith("https://") else "http"
    authority = u[len(scheme) + 3:].split("/")[0]
    if authority.startswith("["):  # IPv6 literal, e.g. [::1]:8080
        host = authority[1:].split("]")[0]
    else:
        host = authority.split(":")[0]
    if not host:
        return {"valid": False, "scheme": scheme, "notes": [
            "callbackUrl has no host part."]}
    # OSS callbacks must target a PUBLIC endpoint: the callbackUrl must
    # resolve to a public IP (0007-00000007) and internal targets are
    # rejected (0007-00000008) -- see references/callback-troubleshooting.md.
    # A literal private/loopback IP (10.x / 172.16-31.x / 192.168.x /
    # 127.0.0.1) or 'localhost' can never be reached by the OSS callback
    # service, so flag it as invalid instead of passing silently.
    if _host_is_non_public(host):
        return {"valid": False, "scheme": scheme, "notes": [
            f"callbackUrl host '{host}' is a private/loopback address (or "
            "'localhost'). OSS callbacks must reach a PUBLIC endpoint: the "
            "callbackUrl must resolve to a public IP (rejected with "
            "0007-00000007 otherwise) and internal IPs such as 127.0.0.1 "
            "are rejected (0007-00000008). Expose the callback server on a "
            "public address (e.g. an ECS with a public IP / EIP) before "
            "configuring it as callbackUrl."]}
    if scheme == "https":
        notes.append(
            "HTTPS callbackUrl: OSS does not send SNI by default; set "
            "callbackSNI=true if the server hosts multiple TLS certificates "
            "on one IP, and ensure the certificate chain is complete and "
            "not expired.")
    if any(c in u for c in (" ", "\t", "\n")):
        return {"valid": False, "scheme": scheme,
                "notes": ["callbackUrl contains whitespace characters."]}
    return {"valid": True, "scheme": scheme, "notes": notes}


assert check_callback_url("http://app.example.com/callback")["valid"] is True  # normal: http
assert check_callback_url("https://app.example.com/callback")["scheme"] == "https"  # normal: https
assert check_callback_url("")["valid"] is False  # invalid: empty
assert check_callback_url("ftp://app.example.com")["valid"] is False  # invalid: bad scheme
assert check_callback_url("http:// /cb")["valid"] is False  # invalid: empty host
# Live gap (groupC round-3, E5): http://192.168.1.10:8080/callback used to
# pass with valid=true and empty notes; OSS callbacks require a public
# endpoint, so private/loopback hosts must now be flagged.
assert check_callback_url("http://192.168.1.10:8080/callback")["valid"] is False  # normal: private IPv4 flagged
assert check_callback_url("http://10.0.0.5/callback")["valid"] is False  # normal: RFC1918 flagged
assert check_callback_url("http://localhost:8080/cb")["valid"] is False  # normal: loopback name flagged
assert check_callback_url("http://127.0.0.1/cb")["valid"] is False  # normal: loopback IP flagged
assert check_callback_url("http://[::1]:8080/cb")["valid"] is False  # normal: IPv6 loopback flagged
assert check_callback_url("http://47.98.18.238:8080/callback")["valid"] is True  # boundary: public IP unaffected
assert check_callback_url("https://aos.example.cn/callback")["valid"] is True  # boundary: domain name unaffected


def build_notification_notes(rules: list) -> list:
    """Evidence-independent event-notification mechanism notes (official doc).

    Always relevant when rules exist or when advising rule creation.
    """
    notes = [
        "A newly created/updated event-notification rule takes about 10 "
        "minutes to propagate; test the trigger again after that window.",
        "Event notification depends on the dependent messaging service: the "
        "legacy path requires SMQ (formerly MNS) to be activated; verify "
        "activation in the SMQ/MNS console (OSS console: Data Processing > "
        "Event Notifications). EventBridge-based delivery must be checked "
        "in the EventBridge console (event tracing) -- this skill cannot "
        "query those services directly.",
        "Check the upload response header x-oss-event-status (Base64): "
        "decoded {\"Result\": \"Ok\"} means OSS successfully triggered the "
        "message service; anything else means the trigger failed.",
        "Per-region limit: at most 10 event-notification rules per region.",
        "On a versioning-enabled bucket, deleting an object WITHOUT a "
        "versionId does not fire ObjectRemoved events (it only adds a "
        "delete marker).",
        "Objects matched by multiple rules: the same target object may not "
        "share the same event type across two rules.",
    ]
    if len(rules) >= _MAX_RULES_PER_REGION:
        notes.insert(0,
                     f"This region already carries {len(rules)} rules, the "
                     "per-region limit; adding more requires contacting "
                     "technical support.")
    return notes


assert len(build_notification_notes([])) == 6  # boundary: no rules -> base notes only
assert isinstance(build_notification_notes([{"events": ["ObjectCreated:*"]}]), list)  # normal: rules present keeps list shape
assert any("10" in n for n in build_notification_notes(
    [{"events": []} for _ in range(10)]))  # boundary: at the rule limit


# ---------------------------------------------------------------------------
# Diagnosis orchestration
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Official-doc verification hook (runtime doc lookup, batch-3 integration)
# ---------------------------------------------------------------------------

_CUSTOMER_QUESTION = ""


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
        description="Diagnose OSS event-notification rules and upload "
                    "callback failures (read-only)",
    )
    parser.add_argument("--bucket", default="",
                             required=False,
                        help="OSS bucket name to diagnose (required)")
    parser.add_argument("--region", default="",
                        help="Expected bucket region (optional; used to "
                             "build the first query endpoint; the bucket's "
                             "real region is always re-derived from "
                             "GetBucketInfo)")
    parser.add_argument("--expected-event", default="",
                        help="Event type the user expects to be notified, "
                             "e.g. ObjectCreated:PutObject (optional; "
                             "matched against the configured rules)")
    parser.add_argument("--callback-error", default="",
                        help="The exact upload-callback error message the "
                             "user observed, e.g. 'CallbackFailed, Message: "
                             "Error status : 502' (optional)")
    parser.add_argument("--callback-url", default="",
                        help="The callbackUrl configured by the user "
                             "(optional; static form check only)")
    parser.add_argument("--question", default="",
                        help="Customer's original wording (optional); when "
                             "provided, the report carries a doc_verification "
                             "section matched against official OSS docs")
    args = parser.parse_args()

    # UA-SKILL-VERSION: resolve and validate the skill version from
    # references/manifest.json BEFORE the first cloud call of this run. The
    # version is never invented, guessed or reused -- a missing or invalid
    # manifest stops the run (STATUS: FAIL, exit 1) with no cloud call made.
    try:
        _oss_client.skill_version()
    except _oss_client.SkillVersionError as _e:
        print(f"[WARN] skill version unavailable: {_e}", file=sys.stderr)
        print(json.dumps({
            "skill": "alibabacloud-oss-event-notification-diagnosis",
            "status": "FAIL",
            "errors": [{"category": "invalid_arguments",
                        "code": "SkillVersionUnavailable",
                        "message": str(_e)[:200]}],
        }, ensure_ascii=False, indent=2))
        print("STATUS: FAIL")
        print("NEXT_ACTION: Fix this skill's references/manifest.json (a valid "
              "`version` field is required to build the User-Agent); no cloud "
              "call was made and no conclusion can be drawn without it.")
        sys.exit(1)

    # Missing-bucket guard: a bare argparse exit 2 leaves the customer with no
    # next step, so ask for the bucket explicitly and offer the buckets this
    # credential can see as candidates (same contract as the sibling skills).
    if not (args.bucket or "").strip():
        _hint, _herrs = [], []
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
        _rep = {"skill": "alibabacloud-oss-event-notification-diagnosis",
                "bucket": "", "buckets_in_account": _hint,
                "errors": _herrs, "auto_filled": []}
        _na = ("Ask the user which OSS bucket has the failing event "
               "notification or upload callback, plus the callback URL or "
               "event type they expected to fire; buckets_in_account lists "
               "up to 30 buckets visible to the current credential.")
        if not _hint:
            _na += (" No bucket is listable with the current credential: ask "
                    "for the exact bucket name and its region instead.")
        return _emit(_rep, "FAIL", _na)
    global _CUSTOMER_QUESTION
    _CUSTOMER_QUESTION = args.question or ""

    auto_filled = []
    # Step 1: identity pre-check / UID derivation (unconditional, degraded
    # with [WARN] on failure -- UID is only a traceability label).
    uid = _oss_client.resolve_uid()

    # Step 2: resolve the endpoint used for the first GetBucketInfo query.
    if args.region.strip():
        query_region = args.region.strip().lower()
        auto_filled.append(f"initial query region taken from --region: "
                           f"{query_region}")
    else:
        query_region = _DEFAULT_REGION
        auto_filled.append(
            f"initial query region auto-defaulted to {_DEFAULT_REGION} "
            "(no --region provided); the bucket's real region is "
            "re-derived from GetBucketInfo")
    query_endpoint = f"oss-{query_region}.aliyuncs.com"

    report = {
        "skill": "alibabacloud-oss-event-notification-diagnosis",
        "bucket": args.bucket,
        "identity": {"uid": uid,
                     "note": "derived via sts get-caller-identity; empty "
                             "means the identity pre-check degraded"},
        "query_endpoint": query_endpoint,
        "auto_filled": auto_filled,
        "bucket_info": None,
        "event_notification": None,
        "upload_callback": None,
        "recommendations": [],
        "errors": [],
    }

    # Step 3: GetBucketInfo -- bucket existence + real region (core anchor).
    bucket_info = None
    try:
        bucket_info = _oss_client.get_bucket_info(args.bucket, query_endpoint)
        report["bucket_info"] = bucket_info
    except OssClientError as e:
        print(f"[WARN] GetBucketInfo degraded ({e.category}): {e}",
              file=sys.stderr)
        report["errors"].append(e.to_dict())
        # Fallback: locate the bucket via ListBuckets so a wrong-region
        # endpoint does not silently skip every notification check.
        try:
            _located = _oss_client.list_buckets(prefix=args.bucket)
            _hits = [b for b in _located if b["name"] == args.bucket]
            if _hits:
                report["bucket_info"] = {
                    "name": _hits[0]["name"],
                    "location": _hits[0]["location"],
                    "source": "ListBuckets fallback (GetBucketInfo degraded)",
                }
                bucket_info = report["bucket_info"]
            elif _located is not None:
                report["errors"].append({
                    "category": "not_found", "code": "ListBucketsNoMatch",
                    "message": "ListBuckets(prefix=%s) returned %d bucket(s), "
                               "none named '%s' in this account"
                               % (args.bucket, len(_located), args.bucket),
                })
        except Exception as e2:
            print(f"[WARN] ListBuckets fallback degraded: {e2}",
                  file=sys.stderr)
            report["errors"].append({"category": "degraded",
                                     "code": "ListBucketsFailed",
                                     "message": str(e2)[:200]})

    bucket_region = ""
    if bucket_info:
        bucket_region = region_from_location(bucket_info.get("location", ""))

    # Step 4: GetBucketNotification (signature V4, bucket's real region).
    # Measured: no rule configured -> semantic finding "not configured"
    # (STATUS stays OK); missing permission / network -> [WARN] + errors[].
    notif = None
    if bucket_region:
        try:
            notif = _oss_client.get_bucket_notification(
                args.bucket, bucket_region)
        except OssClientError as e:
            print(f"[WARN] GetBucketNotification degraded ({e.category}): "
                  f"{e}", file=sys.stderr)
            report["errors"].append(e.to_dict())
    else:
        print("[WARN] GetBucketNotification skipped: bucket region unknown "
              "(GetBucketInfo degraded)", file=sys.stderr)
        report["errors"].append({
            "category": "unknown",
            "code": "NotificationSkipped",
            "message": "event-notification check skipped because the bucket "
                       "region could not be derived",
            "hint": "Re-run after resolving the GetBucketInfo error.",
        })

    expected_event = normalize_event_type(args.expected_event)
    if notif is not None:
        rules = notif.get("rules", [])
        covered = any_rule_covers(rules, expected_event) \
            if expected_event else None
        report["event_notification"] = {
            "configured": notif.get("configured", False),
            "rule_count": len(rules),
            "rules": rules,
            "expected_event": expected_event or None,
            "expected_event_covered": covered,
            "notes": build_notification_notes(rules),
        }
        if expected_event and notif.get("configured") and covered is False:
            report["event_notification"]["finding"] = (
                f"event-notification rules exist but NONE covers the "
                f"expected event type {expected_event} -- the notification "
                f"will never trigger for it; extend a rule's event types or "
                f"add a rule covering the target object prefix/suffix "
                f"(manual console task).")
        elif expected_event and not notif.get("configured"):
            report["event_notification"]["finding"] = (
                f"no event-notification rule is configured on this bucket, "
                f"so {expected_event} (or any other event) can never "
                f"trigger a notification.")

    # Step 5: GetBucketCallbackPolicy (bucket-level upload-callback policy).
    cbp = None
    if bucket_region:
        cbp_endpoint = f"oss-{bucket_region}.aliyuncs.com"
        try:
            cbp = _oss_client.get_bucket_callback_policy(
                args.bucket, cbp_endpoint)
        except OssClientError as e:
            print(f"[WARN] GetBucketCallbackPolicy degraded ({e.category}): "
                  f"{e}", file=sys.stderr)
            report["errors"].append(e.to_dict())

    # Step 6: upload-callback analysis (knowledge-based attribution).
    cb_analysis = classify_callback_error(args.callback_error)
    cb_url = check_callback_url(args.callback_url)
    report["upload_callback"] = {
        "bucket_callback_policy": (
            {"configured": cbp.get("configured", False)}
            if cbp is not None else None),
        "callback_error": {
            "observed": args.callback_error or None,
            "kind": cb_analysis["kind"],
            "attribution": cb_analysis["attribution"],
            "advice": cb_analysis["advice"],
        },
        "callback_url_check": {
            "provided": bool(args.callback_url.strip()),
            "valid": cb_url["valid"],
            "scheme": cb_url["scheme"],
            "notes": cb_url["notes"],
        },
        "mechanism_notes": [
            "Upload callback applies to PutObject / PostObject / "
            "CompleteMultipartUpload; a successful upload with a failed "
            "callback returns HTTP 203 with ErrorCode CallbackFailed -- the "
            "object IS stored.",
            "The callback timeout is a fixed 5 seconds; the callback server "
            "must return HTTP 200 with a JSON body; any non-200 or "
            "non-JSON response is treated as CallbackFailed.",
            "OSS callback source IPs are NOT fixed; use signature "
            "verification on the callback server instead of IP allowlists.",
        ],
    }

    # Step 7: recommendations.
    recs = []
    if notif is not None:
        if not notif.get("configured"):
            recs.append(
                "Event notification is NOT configured on this bucket. To "
                "enable it (manual console task): OSS console > the bucket "
                "> Data Processing > Event Notifications > Create Rule; "
                "activate SMQ (formerly MNS) first if required; a new rule "
                "takes about 10 minutes to take effect.")
        else:
            recs.append(
                f"{len(report['event_notification']['rules'])} event-"
                "notification rule(s) configured; verify the rule's event "
                "types and object prefix/suffix actually cover the objects "
                "and operations you expect, and confirm the dependent "
                "messaging service (SMQ/MNS or EventBridge) is activated "
                "and receiving (this skill cannot query those services "
                "directly -- check their consoles).")
    if cb_analysis["kind"] != "none":
        recs.extend(cb_analysis["advice"])
    if cb_url.get("notes") and args.callback_url.strip():
        recs.extend(cb_url["notes"])
    if not recs:
        recs.append(
            "No configuration defect was detected by the read-only checks; "
            "if notifications still do not arrive, verify the dependent "
            "messaging service (SMQ/MNS, EventBridge) in its own console "
            "and the x-oss-event-status response header of a fresh upload.")
    report["recommendations"] = recs

    # Step 8: status + next action.
    degraded = bool(report["errors"])
    if degraded:
        root = report["errors"][0]
        cat = root.get("category", "unknown")
        if cat == "not_found":
            next_action = (
                f"Bucket '{args.bucket}' was not found (NoSuchBucket); "
                "verify the bucket name spelling and the owning account, "
                "then re-run the diagnosis.")
        elif cat == "permission":
            next_action = (
                "Access denied (403): grant the caller the read-only "
                "actions listed in references/ram-policies.md (oss:"
                "GetBucketInfo / oss:GetBucketNotification / oss:"
                "GetBucketCallbackPolicy) or confirm the bucket belongs to "
                "this account, then re-run.")
        elif cat == "endpoint":
            next_action = (
                "The request hit the wrong region's endpoint; re-run with "
                "--region set to the region where the bucket was created.")
        elif cat == "credentials":
            next_action = (
                "No credentials in the environment credential chain; configure "
                "the default credential chain (aliyun configure / "
                "environment variables), never pass AK/SK manually.")
        elif cat == "invalid":
            next_action = (
                "The supplied bucket name is invalid (bucket names are 3-63 "
                "lowercase letters/digits/hyphens, no dots); fix the "
                "spelling and re-run.")
        elif cat == "network":
            next_action = (
                "Network failure reaching the OSS endpoint; verify DNS/"
                "connectivity and re-run.")
        else:
            next_action = (
                "OSS control-plane query degraded; review the recorded "
                "errors and re-run after fixing the root cause.")
        sys.exit(_emit(report, "DEGRADED", next_action))

    # OK path: every query answered (including 'not configured' semantics).
    if notif is not None and not notif.get("configured"):
        next_action = (
            "No event-notification rule is configured on bucket "
            f"'{args.bucket}'; create one in the OSS console (Data "
            "Processing > Event Notifications) after activating SMQ/MNS -- "
            "this skill is read-only and never creates rules itself.")
    elif expected_event and notif is not None \
            and not any_rule_covers(notif.get("rules", []), expected_event):
        next_action = (
            f"None of the configured rules covers {expected_event}; extend "
            "or add a rule in the OSS console so the event type and object "
            "prefix/suffix match your workload.")
    elif cb_analysis["kind"] not in ("none", "unknown"):
        next_action = (
            "Upload-callback failure attributed to: "
            f"{cb_analysis['attribution']}; apply the recorded advice "
            "(5-second JSON response, callbackSNI for HTTPS, server "
            "reachability) and re-test the upload.")
    else:
        next_action = (
            "Event-notification configuration verified; if events still do "
            "not arrive, check the dependent messaging service console and "
            "the x-oss-event-status response header of a fresh upload.")
    sys.exit(_emit(report, "OK", next_action))


if __name__ == "__main__":
    sys.exit(main())
