#!/usr/bin/env python3
"""
oss_quota_diagnosis.py -- OSS QPS/bandwidth quota & throttling diagnosis
=========================================================================
SECURITY: READ-ONLY. Only issues GetBucketInfo (+ ListBuckets fallback) to
the OSS control plane and GetCallerIdentity to STS. Never mutates anything.
Credentials come exclusively from the default credential chain (environment
variables for the OSS SDK, aliyun CLI default chain for the identity check);
raw credential values are never read, printed, or passed explicitly.

Diagnoses (knowledge-grounded, no quota-watermark query API exists):
  * region-level quota context of the bucket's region (official defaults)
  * attribution of 503 / SlowDown / timeout symptoms to server-side
    throttling vs hotspot partition vs client-side/network causes
  * performance guidance (prefix hash distribution, concurrency control,
    multipart/range transfer, exponential backoff)
  * quota-increase / dedicated-resource application path (guidance only;
    this skill never submits any application)

KNOWLEDGE SOURCES (fetched from help.aliyun.com, 2026-08-27):
  * https://help.aliyun.com/zh/oss/user-guide/limits
    (per-region bandwidth table; QPS 10,000 total / 2,000 sequential;
     QPS limit increase is NOT self-service via the quota center --
     submit a ticket; throttled responses carry x-oss-qos-delay-time)
  * https://help.aliyun.com/zh/oss/user-guide/http-status-code-503
    (503 error codes: DownloadTrafficRateLimitExceeded,
     UploadTrafficRateLimitExceeded, TotalQpsLimitExceeded,
     MetaOperationQpsLimitExceeded, ActiveRequestLimitExceeded,
     CpuLimitExceeded, ServiceUnavailable)
  * https://help.aliyun.com/zh/oss/user-guide/oss-performance-best-practices/
    (hash/reversed prefixes, parallel requests, exponential backoff)
  * https://help.aliyun.com/zh/oss/troubleshoot-bandwidth-or-qps-overrun-for-buckets-in-oss
    (console watermark check: Usage Query > Basic Data; OSS has no
     user-defined rate-limit configuration)
  * https://help.aliyun.com/zh/oss/user-guide/oss-resource-pool-qos
    (resource pool QoS / dedicated bandwidth requires >= 400 Gbps and a
     ticket application)

IMPORTANT: OSS exposes NO public API to query the actual bandwidth/QPS
watermark (utilization) of an account or bucket. The watermark is
knowledge-guided only: check the OSS console (Usage Query > Basic Data)
or CloudMonitor OSS metrics, and inspect the x-oss-qos-delay-time header
on throttled responses. This script states that limitation explicitly and
never fabricates utilization figures.

Output contract (04-spec): stdout carries a structured JSON report followed
by the machine-consumable lines:
    STATUS: OK | DEGRADED
    NEXT_ACTION: <one actionable sentence>

Usage:
  python3 oss_quota_diagnosis.py --bucket <name> [--region <region>] \
      [--error-code <code>] [--symptom 503|timeout|slow] \
      [--direction upload|download|both] [--peak-qps <N>] \
      [--peak-bandwidth-gbps <N>] [--sequential-prefix yes|no]
"""

from __future__ import annotations

import argparse
import json
import sys

import _oss_client
import _doc_lookup
from _oss_client import OssClientError

# Inline contract assertion: an illegal bucket name must degrade to the
# unified OssClientError(category="invalid") -- never a bare oss2
# ClientError Traceback (measured on oss2 2.19.1; _build_bucket converts
# the client-side validation error, no network call happens).
try:
    _oss_client._build_bucket("Invalid_Bucket!", "oss-cn-hangzhou.aliyuncs.com")
    _INVALID_BUCKET_CATEGORY = "no-error"
except OssClientError as _e:
    _INVALID_BUCKET_CATEGORY = _e.category
except Exception:  # pragma: no cover - regression guard
    _INVALID_BUCKET_CATEGORY = "unexpected-traceback"
assert _INVALID_BUCKET_CATEGORY == "invalid"  # invalid: illegal bucket name

_DEFAULT_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"

_DOC_LIMITS = "https://help.aliyun.com/zh/oss/user-guide/limits"
_DOC_503 = "https://help.aliyun.com/zh/oss/user-guide/http-status-code-503"
_DOC_PERF = "https://help.aliyun.com/zh/oss/user-guide/oss-performance-best-practices/"
_DOC_TROUBLESHOOT = ("https://help.aliyun.com/zh/oss/troubleshoot-bandwidth-"
                     "or-qps-overrun-for-buckets-in-oss")
_DOC_RESOURCE_POOL = "https://help.aliyun.com/zh/oss/user-guide/oss-resource-pool-qos"

# Account-level QPS defaults (official limits doc, fetched 2026-08-27).
QPS_TOTAL_DEFAULT = 10000        # non-sequential reads/writes
QPS_SEQUENTIAL_DEFAULT = 2000    # sequential-prefix reads/writes
_NEAR_LIMIT_RATIO = 0.8          # >= 80% of a limit counts as "near"

# Per-region bandwidth defaults (official limits doc table, fetched
# 2026-08-27). Values in Gbps; None means "no separate cap beyond the
# total".
_BW_TIERS = {
    # major mainland regions: total 100 down / 20 up
    "cn-hangzhou": {"total_down": 100, "public_down": 20,
                    "total_up": 20, "public_up": 20},
    "cn-shanghai": {"total_down": 100, "public_down": 10,
                    "total_up": 20, "public_up": 10},
    "cn-shenzhen": {"total_down": 100, "public_down": 10,
                    "total_up": 20, "public_up": 10},
    "cn-beijing": {"total_down": 100, "public_down": 10,
                   "total_up": 20, "public_up": 10},
    "ap-southeast-1": {"total_down": 100, "public_down": 5,
                       "total_up": 20, "public_up": 5},
    "cn-zhangjiakou": {"total_down": 20, "public_down": None,
                       "total_up": 20, "public_up": None},
    # small local regions: 2 Gbps total. cn-nanjing (East China 5) and
    # cn-fuzhou (East China 6) are officially marked “关停中” (being shut
    # down) in the limits doc, so flag them for migration; cn-wuhan-lr is a
    # local region but is NOT marked as shutting down.
    "cn-nanjing": {"total_down": 2, "public_down": None,
                   "total_up": 2, "public_up": None,
                   "decommissioning": True},
    "cn-fuzhou": {"total_down": 2, "public_down": None,
                  "total_up": 2, "public_up": None,
                  "decommissioning": True},
    "cn-wuhan-lr": {"total_down": 2, "public_down": None,
                    "total_up": 2, "public_up": None},
    "ap-northeast-2": {"total_down": 2, "public_down": None,
                       "total_up": 2, "public_up": None},
    "ap-southeast-7": {"total_down": 2, "public_down": None,
                       "total_up": 2, "public_up": None},
}
_BW_MAINLAND_DEFAULT = {"total_down": 10, "public_down": None,
                        "total_up": 10, "public_up": None}
_BW_OVERSEAS_DEFAULT = {"total_down": 5, "public_down": None,
                        "total_up": 5, "public_up": None}
_MAINLAND_PREFIXES = ("cn-",)


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


def normalize_token(raw: str) -> str:
    """Strip whitespace, lowercase a user-supplied token (code/symptom)."""
    return (raw or "").strip().lower()


assert normalize_token("  TotalQpsLimitExceeded ") == "totalqpslimitexceeded"  # normal
assert normalize_token(None) == ""  # invalid: missing
assert normalize_token("") == ""  # invalid: empty


# 503 error-code table (official 503 doc, fetched 2026-08-27).
# category values: bandwidth / qps / meta / concurrency / image / server-busy
_ERROR_CODE_TABLE = {
    "downloadtrafficratelimitexceeded": {
        "throttle": True, "category": "bandwidth", "direction": "download",
        "advice": "Download bandwidth exceeded the region cap; check the "
                  "bandwidth watermark in the OSS console, reduce download "
                  "concurrency, or apply for a quota increase via a ticket."},
    "uploadtrafficratelimitexceeded": {
        "throttle": True, "category": "bandwidth", "direction": "upload",
        "advice": "Upload bandwidth exceeded the region cap; check the "
                  "bandwidth watermark in the OSS console, reduce upload "
                  "concurrency, or apply for a quota increase via a ticket."},
    "totalqpslimitexceeded": {
        "throttle": True, "category": "qps", "direction": "both",
        "advice": "Account total QPS exceeded the limit (10,000 "
                  "non-sequential / 2,000 sequential-prefix); control "
                  "request concurrency and retry with exponential backoff. "
                  "QPS increases are ticket-based, not self-service."},
    "metaoperationqpslimitexceeded": {
        "throttle": True, "category": "meta", "direction": "both",
        "advice": "Management-plane API QPS limit exceeded (GetService/"
                  "PutBucket/GetBucketLifecycle class); delay a few seconds "
                  "and retry."},
    "activerequestlimitexceeded": {
        "throttle": True, "category": "concurrency", "direction": "both",
        "advice": "Concurrent active request count exceeded the limit; "
                  "reduce client-side concurrency and contact technical "
                  "support if the business needs more."},
    "cpulimitexceeded": {
        "throttle": True, "category": "image", "direction": "both",
        "advice": "Image-processing concurrency exceeded the CPU cap; "
                  "reduce image-processing request concurrency."},
    "serviceunavailable": {
        "throttle": False, "category": "server-busy", "direction": "both",
        "advice": "OSS server busy (thread pool almost full); retry later "
                  "with exponential backoff."},
}


def classify_error_code(code: str) -> dict:
    """Classify an OSS error code against the throttling knowledge base.

    Returns {"throttle": bool, "category": str, "advice": str}. The generic
    SlowDown marker (returned by OSS 503 throttling responses) maps to the
    throttle family; unknown codes return category 'unknown'.
    """
    c = normalize_token(code)
    if not c:
        return {"throttle": False, "category": "unknown", "advice": ""}
    if "slowdown" in c:
        return {"throttle": True, "category": "slowdown", "direction": "both",
                "advice": "503 SlowDown is the generic throttling signal; "
                          "correlate with the bandwidth/QPS watermark in the "
                          "OSS console and the x-oss-qos-delay-time header."}
    entry = _ERROR_CODE_TABLE.get(c)
    if entry:
        return dict(entry)
    return {"throttle": False, "category": "unknown", "advice": ""}


assert classify_error_code("TotalQpsLimitExceeded")["throttle"] is True  # normal: QPS throttle
assert classify_error_code("DownloadTrafficRateLimitExceeded")["category"] == "bandwidth"  # normal: download bandwidth
assert classify_error_code("503 SlowDown")["throttle"] is True  # boundary: generic slowdown marker
assert classify_error_code("NoSuchBucket")["category"] == "unknown"  # boundary: unrelated code
assert classify_error_code("")["category"] == "unknown"  # invalid: empty
assert classify_error_code(None)["throttle"] is False  # invalid: missing


def parse_number(raw) -> float:
    """Parse a user-supplied numeric input; return -1.0 when invalid."""
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return -1.0
    return value


assert parse_number("12000") == 12000.0  # normal
assert parse_number(9500) == 9500.0  # boundary: already numeric
assert parse_number("abc") == -1.0  # invalid: non-numeric
assert parse_number(None) == -1.0  # invalid: missing


def compare_to_limit(peak: float, limit: float) -> str:
    """Compare a measured peak against a quota limit.

    Returns 'above' | 'near' (>= 80% of the limit) | 'below' | 'unknown'.
    """
    if peak < 0 or limit <= 0:
        return "unknown"
    if peak > limit:
        return "above"
    if peak >= limit * _NEAR_LIMIT_RATIO:
        return "near"
    return "below"


assert compare_to_limit(12000, QPS_TOTAL_DEFAULT) == "above"  # normal: over limit
assert compare_to_limit(8000, QPS_TOTAL_DEFAULT) == "near"  # boundary: exactly 80%
assert compare_to_limit(7999, QPS_TOTAL_DEFAULT) == "below"  # boundary: just under 80%
assert compare_to_limit(100, QPS_TOTAL_DEFAULT) == "below"  # normal
assert compare_to_limit(-1, QPS_TOTAL_DEFAULT) == "unknown"  # invalid: missing peak
assert compare_to_limit(100, 0) == "unknown"  # invalid: zero limit


def parse_bool(raw: str):
    """Parse yes/no style booleans; None when absent/unparseable."""
    v = (raw or "").strip().lower()
    if v in ("yes", "true", "1"):
        return True
    if v in ("no", "false", "0"):
        return False
    return None


assert parse_bool("yes") is True  # normal
assert parse_bool("False") is False  # normal: case-insensitive
assert parse_bool("") is None  # invalid: empty
assert parse_bool(None) is None  # invalid: missing


def bandwidth_tier_for_region(region: str) -> dict:
    """Return the official default bandwidth tier (Gbps) for a region.

    Table source: the OSS limits doc (fetched 2026-08-27). Regions without
    an explicit row fall back to the 'other mainland 10 Gbps' / 'other
    non-mainland 5 Gbps' defaults; an empty region returns the mainland
    default with tier='unknown'.
    """
    r = (region or "").strip().lower()
    if not r:
        return {"tier": "unknown", **_BW_MAINLAND_DEFAULT, "source": _DOC_LIMITS}
    if r in _BW_TIERS:
        return {"tier": r, **_BW_TIERS[r], "source": _DOC_LIMITS}
    if any(r.startswith(p) for p in _MAINLAND_PREFIXES):
        return {"tier": "other-mainland-default", **_BW_MAINLAND_DEFAULT,
                "source": _DOC_LIMITS}
    return {"tier": "other-overseas-default", **_BW_OVERSEAS_DEFAULT,
            "source": _DOC_LIMITS}


assert bandwidth_tier_for_region("cn-hangzhou")["total_down"] == 100  # normal: explicit row
assert bandwidth_tier_for_region("cn-wulanchabu")["tier"] == "other-mainland-default"  # boundary: fallback mainland 10
assert bandwidth_tier_for_region("us-east-1")["total_down"] == 5  # boundary: overseas fallback
assert bandwidth_tier_for_region("")["tier"] == "unknown"  # invalid: empty
# G3-4: cn-nanjing / cn-fuzhou are officially “关停中” (being shut down);
# cn-wuhan-lr is a local region but NOT shutting down; major regions carry
# no decommission flag.
assert bandwidth_tier_for_region("cn-nanjing").get("decommissioning") is True  # normal: officially 关停中
assert bandwidth_tier_for_region("cn-fuzhou").get("decommissioning") is True  # normal: officially 关停中
assert bandwidth_tier_for_region("cn-wuhan-lr").get("decommissioning") is None  # boundary: local region, NOT shutting down
assert bandwidth_tier_for_region("cn-hangzhou").get("decommissioning") is None  # boundary: major region, no flag


def decide_verdict(error_class: dict, symptom: str, direction: str,
                   qps_status: str, bw_status: str,
                   sequential_prefix) -> dict:
    """Decision tree mapping symptoms/evidence to a throttling verdict.

    Priority (knowledge from the official docs + ticket-proven attribution):
      1. an explicit throttle-family error code confirms server throttling
      2. measured peaks above the official region/account limits confirm
         quota pressure even without a captured error code
      3. sequential-prefix naming with pressure/hotspot symptoms points to
         a single-partition hotspot (per-partition 2,000 req/s capability)
      4. timeouts WITHOUT any server-side 5xx / throttle error code are
         attributed to the client-side or network path first
      5. otherwise the evidence is insufficient -> watermark check guidance

    Returns {"verdict": str, "reason": str}.
    """
    symptom = (symptom or "").strip().lower()
    if error_class.get("throttle"):
        return {
            "verdict": "server-throttle-confirmed",
            "reason": "The reported error code belongs to the OSS 503 "
                      "throttling family; server-side rate limiting is "
                      "confirmed by the error itself.",
        }
    if qps_status == "above" or bw_status == "above":
        return {
            "verdict": "region-quota-pressure-likely",
            "reason": "The reported peak exceeds the official default "
                      "bandwidth/QPS limit of the region/account; requests "
                      "at this level are throttled and rejected with 503.",
        }
    if sequential_prefix and (qps_status in ("above", "near")
                              or symptom in ("503", "slowdown", "slow")):
        return {
            "verdict": "hotspot-partition-likely",
            "reason": "Sequential object-key prefixes concentrate requests "
                      "on one partition; a single partition sustains about "
                      "2,000 requests/s, so hotspots throttle even when the "
                      "account-wide QPS is below the limit.",
        }
    if symptom == "timeout" and not error_class.get("throttle"):
        return {
            "verdict": "client-or-network-likely",
            "reason": "Client timeouts without server-side 5xx or throttle "
                      "error codes usually originate in the client-to-OSS "
                      "path (DNS, cross-region/cross-border links, client "
                      "bandwidth), not in OSS throttling; verify with "
                      "server access logs before concluding throttling.",
        }
    if symptom in ("503", "slowdown", "slow"):
        return {
            "verdict": "throttle-suspected-unverified",
            "reason": "Symptoms are consistent with throttling but no "
                      "throttle-family error code or peak measurement was "
                      "provided; verify against the console bandwidth/QPS "
                      "watermark and the x-oss-qos-delay-time header.",
        }
    return {
        "verdict": "evidence-insufficient",
        "reason": "Not enough symptom or measurement evidence to attribute "
                  "the problem; collect the error code, peaks, and console "
                  "watermark before concluding.",
    }


assert decide_verdict(classify_error_code("TotalQpsLimitExceeded"), "503", "both", "unknown", "unknown", None)["verdict"] == "server-throttle-confirmed"  # normal: code confirms
assert decide_verdict(classify_error_code(""), "", "both", "above", "unknown", None)["verdict"] == "region-quota-pressure-likely"  # normal: peak over limit
assert decide_verdict(classify_error_code(""), "503", "both", "near", "unknown", True)["verdict"] == "hotspot-partition-likely"  # boundary: sequential prefix hotspot
assert decide_verdict(classify_error_code(""), "timeout", "both", "unknown", "unknown", None)["verdict"] == "client-or-network-likely"  # normal: timeout without server errors
assert decide_verdict(classify_error_code(""), "503", "both", "unknown", "unknown", None)["verdict"] == "throttle-suspected-unverified"  # boundary: symptom only
assert decide_verdict(classify_error_code(""), "", "both", "unknown", "unknown", None)["verdict"] == "evidence-insufficient"  # invalid: no evidence


def build_recommendations(verdict: dict, error_class: dict, direction: str,
                          sequential_prefix, region: str) -> list:
    """Assemble evidence-based, manual-guidance-only recommendations."""
    recs = []
    v = verdict.get("verdict", "")
    direction = (direction or "both").lower()
    if error_class.get("advice"):
        recs.append(error_class["advice"])
    if v in ("server-throttle-confirmed", "region-quota-pressure-likely",
             "throttle-suspected-unverified"):
        recs.append(
            "Control client-side concurrency and retry with exponential "
            "backoff (e.g. wait 2s, then 4s); the latest OSS SDKs have "
            "built-in 503 retry handling. Source: " + _DOC_PERF)
        recs.append(
            "Check the actual bandwidth/QPS watermark in the OSS console "
            "(bucket -> Usage Query > Basic Data) or CloudMonitor; OSS "
            "provides no public API to query the watermark, and throttled "
            "responses carry the x-oss-qos-delay-time header. Source: "
            + _DOC_TROUBLESHOOT + " and " + _DOC_LIMITS)
        if direction in ("download", "both"):
            recs.append(
                "For hot public download traffic, front the bucket with CDN "
                "caching (increase cache TTL and preheat) to offload origin "
                "bandwidth. Source: " + _DOC_TROUBLESHOOT)
        recs.append(
            "Quota increases: QPS limit increases are NOT self-service in "
            "the quota center -- submit a ticket; bandwidth increases are "
            "also ticket-based. Resource pool QoS (dedicated/guaranteed "
            "bandwidth) requires the region bandwidth to reach 400 Gbps "
            "plus a ticket application. This skill only explains the path; "
            "it never submits applications. Source: " + _DOC_LIMITS
            + " and " + _DOC_RESOURCE_POOL)
    if v == "hotspot-partition-likely" or sequential_prefix:
        recs.append(
            "Replace sequential object-key prefixes with randomized ones: "
            "prepend a 4-char hex hash (e.g. MD5) prefix or reverse "
            "timestamp keys so requests spread across partitions "
            "(up to 65,536 hash slots). Source: " + _DOC_PERF)
    if v == "client-or-network-likely":
        recs.append(
            "Verify the client-to-OSS path: DNS resolution, cross-region/"
            "cross-border link quality, and the client's own bandwidth; "
            "compare with OSS access logs to confirm the server side "
            "returned no errors. Same-region clients should use the "
            "internal endpoint; cross-border slowness is not throttling.")
    if v == "evidence-insufficient":
        recs.append(
            "Collect the missing evidence before concluding: the exact "
            "error code / HTTP status, measured peak QPS and bandwidth, "
            "and the console watermark of the affected time window.")
    return recs


assert any("exponential backoff" in r for r in build_recommendations(
    decide_verdict(classify_error_code("TotalQpsLimitExceeded"), "503",
                   "both", "unknown", "unknown", None),
    classify_error_code("TotalQpsLimitExceeded"), "both", None,
    "cn-hangzhou"))  # normal: throttle path
assert any("hash" in r for r in build_recommendations(
    decide_verdict(classify_error_code(""), "503", "both", "near",
                   "unknown", True),
    classify_error_code(""), "both", True, "cn-hangzhou"))  # normal: hotspot advice
assert any("client-to-OSS" in r for r in build_recommendations(
    decide_verdict(classify_error_code(""), "timeout", "both", "unknown",
                   "unknown", None),
    classify_error_code(""), "both", None, "cn-hangzhou"))  # normal: client path
assert isinstance(build_recommendations(
    decide_verdict(classify_error_code(""), "", "both", "unknown",
                   "unknown", None),
    classify_error_code(""), "both", None, ""), list)  # boundary: empty evidence


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
        description="Assess OSS QPS/bandwidth quota and throttling "
                    "symptoms (read-only)",
    )
    parser.add_argument("--bucket", default="", required=False,
                        help="OSS bucket name to diagnose (required; when absent the script emits FAIL and asks)")
    parser.add_argument("--region", default="",
                        help="Expected region (optional; used to build the "
                             "query endpoint)")
    parser.add_argument("--endpoint", default="",
                        help="Query endpoint override (optional; normally "
                             "derived from the bucket's real region)")
    parser.add_argument("--error-code", default="",
                        help="Error code reported by the client, e.g. "
                             "TotalQpsLimitExceeded or '503 SlowDown'")
    parser.add_argument("--symptom", default="",
                        choices=["", "503", "timeout", "slow", "slowdown"],
                        help="Dominant symptom (optional)")
    parser.add_argument("--direction", default="both",
                        choices=["upload", "download", "both"],
                        help="Affected traffic direction (optional)")
    parser.add_argument("--peak-qps", default="",
                        help="Measured peak QPS during the incident "
                             "(optional)")
    parser.add_argument("--peak-bandwidth-gbps", default="",
                        help="Measured peak bandwidth in Gbps (optional)")
    parser.add_argument("--sequential-prefix", default="",
                        help="Whether object keys use sequential prefixes: "
                             "yes/no (optional)")
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
            "skill": "alibabacloud-oss-quota-throttling-diagnosis",
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
            "skill": globals().get("_SKILL_NAME", "alibabacloud-oss-quota-throttling-diagnosis"),
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
    global _CUSTOMER_QUESTION
    _CUSTOMER_QUESTION = args.question or ""

    auto_filled = []
    # Step 1: identity pre-check / UID derivation (unconditional, degraded
    # with [WARN] on failure -- UID is only a traceability label).
    uid = _oss_client.resolve_uid()

    # Step 2: resolve the endpoint used to query GetBucketInfo.
    query_endpoint = (args.endpoint or "").strip().lower().rstrip("/")
    for scheme in ("https://", "http://"):
        if query_endpoint.startswith(scheme):
            query_endpoint = query_endpoint[len(scheme):]
    if not query_endpoint:
        if args.region.strip():
            region = args.region.strip().lower()
            query_endpoint = f"oss-{region}.aliyuncs.com"
            auto_filled.append(
                f"query endpoint derived from --region: {query_endpoint}")
        else:
            query_endpoint = _DEFAULT_ENDPOINT
            auto_filled.append(
                f"query endpoint auto-defaulted to {query_endpoint} "
                "(no --endpoint/--region provided)")

    report = {
        "skill": "alibabacloud-oss-quota-throttling-diagnosis",
        "bucket": args.bucket,
        "identity": {"uid": uid,
                     "note": "derived via sts get-caller-identity; empty "
                             "means the identity pre-check degraded"},
        "inputs": {
            "symptom": normalize_token(args.symptom) or None,
            "error_code": args.error_code.strip() or None,
            "direction": args.direction,
            "peak_qps": parse_number(args.peak_qps)
            if args.peak_qps else None,
            "peak_bandwidth_gbps": parse_number(args.peak_bandwidth_gbps)
            if args.peak_bandwidth_gbps else None,
            "sequential_prefix": parse_bool(args.sequential_prefix),
        },
        "query_endpoint": query_endpoint,
        "auto_filled": auto_filled,
        "bucket_info": None,
        "quota_reference": None,
        "watermark_note": (
            "OSS exposes NO public API to query the actual bandwidth/QPS "
            "watermark (utilization). Verify utilization in the OSS console "
            "(bucket -> Usage Query > Basic Data) or CloudMonitor OSS "
            "metrics; throttled responses carry the x-oss-qos-delay-time "
            "header (upload: precise delay; download: estimated). The "
            "defaults below are the official quota context, not measured "
            "utilization."),
        "verdict": None,
        "recommendations": [],
        "errors": [],
    }

    # Step 3: GetBucketInfo -- locate the bucket's real region (evidence).
    bucket_info = None
    try:
        bucket_info = _oss_client.get_bucket_info(args.bucket, query_endpoint)
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
        if _ep != query_endpoint:
            auto_filled.append(
                "query endpoint re-derived from bucket location %s: %s"
                % (_loc, _ep))
            query_endpoint = _ep
            report["query_endpoint"] = _ep

    # Identity-chain guard: identity.uid is resolved from the aliyun CLI
    # default profile while bucket evidence comes from the SDK credential
    # chain, so the two can belong to different accounts and silently
    # mislabel the scope of every conclusion below.
    _owner = str((bucket_info or {}).get("owner_id") or "")
    if _owner:
        try:
            report["identity"]["bucket_owner_uid"] = _owner
            report["identity"]["uid_matches_bucket_owner"] = (_owner == str(uid or ""))
        except Exception:
            pass
        if _owner != str(uid or ""):
            print(f"[WARN] identity consistency: caller UID {uid} (aliyun CLI "
                  f"default profile) differs from bucket owner UID {_owner} "
                  f"(resolved through the data-plane credential); findings "
                  f"reflect the data-plane account only.",
                  file=sys.stderr)

    # Step 4: quota context of the bucket's region.
    bucket_location = bucket_info.get("location") if bucket_info else None
    bucket_region = region_from_location(bucket_location) if bucket_location else ""
    tier = bandwidth_tier_for_region(bucket_region)
    report["quota_reference"] = {
        "bucket_location": bucket_location,
        "bucket_region": bucket_region or None,
        "bandwidth_defaults_gbps": {
            "total_download": tier["total_down"],
            "public_download": tier["public_down"],
            "total_upload": tier["total_up"],
            "public_upload": tier["public_up"],
            "tier": tier["tier"],
            "region_status": (
                "关停中 (officially being shut down -- advise the user to "
                "plan a migration to another region before relying on this "
                "region's bandwidth)"
                if tier.get("decommissioning") else "active"),
            "source": tier["source"],
        },
        "qps_defaults": {
            "total_non_sequential": QPS_TOTAL_DEFAULT,
            "sequential_prefix": QPS_SEQUENTIAL_DEFAULT,
            "source": _DOC_LIMITS,
            "increase_path": "QPS limit increases are not self-service via "
                             "the quota center; submit a ticket.",
        },
    }

    # Step 5: classify evidence and run the decision tree.
    error_class = classify_error_code(args.error_code)
    symptom = normalize_token(args.symptom)
    peak_qps = parse_number(args.peak_qps) if args.peak_qps else -1
    peak_bw = (parse_number(args.peak_bandwidth_gbps)
               if args.peak_bandwidth_gbps else -1)
    sequential = parse_bool(args.sequential_prefix)
    qps_limit = (QPS_SEQUENTIAL_DEFAULT if sequential
                 else QPS_TOTAL_DEFAULT)
    qps_status = compare_to_limit(peak_qps, qps_limit)
    bw_limit = (tier["total_up"] if args.direction == "upload"
                else tier["total_down"]) or 0
    bw_status = compare_to_limit(peak_bw, float(bw_limit))
    verdict = decide_verdict(error_class, symptom, args.direction,
                             qps_status, bw_status, sequential)
    verdict["error_code_classified"] = error_class
    verdict["qps_vs_limit"] = {"peak": peak_qps if peak_qps >= 0 else None,
                               "limit": qps_limit, "status": qps_status}
    verdict["bandwidth_vs_limit"] = {
        "peak_gbps": peak_bw if peak_bw >= 0 else None,
        "limit_gbps": bw_limit, "status": bw_status,
        "direction": args.direction}
    report["verdict"] = verdict
    report["recommendations"] = build_recommendations(
        verdict, error_class, args.direction, sequential, bucket_region)

    # Step 6: status + next action.
    if bucket_info:
        v = verdict["verdict"]
        if v == "server-throttle-confirmed":
            next_action = (
                "Server-side throttling is confirmed by the error code; "
                "apply concurrency control + exponential backoff, check the "
                "console bandwidth/QPS watermark, and submit a ticket for a "
                "quota increase if the business needs more.")
        elif v == "region-quota-pressure-likely":
            next_action = (
                "The reported peak exceeds the region's official default "
                "limit; reduce concurrency now and submit a ticket to apply "
                "for a quota increase.")
        elif v == "hotspot-partition-likely":
            next_action = (
                "Requests likely concentrate on one partition; hash or "
                "reverse the sequential object-key prefixes to spread load "
                "before requesting any quota increase.")
        elif v == "client-or-network-likely":
            next_action = (
                "No server-side throttling evidence; verify the client/"
                "network path (DNS, cross-region link, client bandwidth) "
                "against OSS access logs before concluding throttling.")
        else:
            next_action = (
                "Quota context of the bucket region reported; collect the "
                "missing evidence (error code, peaks, console watermark) to "
                "attribute the throttling.")
        sys.exit(_emit(report, "OK", next_action))

    # Degraded: no bucket info obtained -- attribute the root error.
    root = report["errors"][0] if report["errors"] else {"category": "unknown"}
    cat = root.get("category", "unknown")
    if cat == "not_found":
        next_action = (
            f"Bucket '{args.bucket}' was not found (NoSuchBucket); verify "
            "the bucket name spelling and the account that owns it, then "
            "re-run the diagnosis.")
    elif cat == "permission":
        next_action = (
            "Access denied (403): grant the caller oss:GetBucketInfo / "
            "oss:ListBuckets (see references/ram-policies.md) or confirm "
            "the bucket belongs to this account, then re-run.")
    elif cat == "network":
        next_action = (
            "Network failure reaching the OSS endpoint host; verify DNS "
            "resolution and connectivity, then re-run.")
    elif cat == "credentials":
        next_action = (
            "No credentials in the environment credential chain; configure "
            "the default credential chain (aliyun configure / environment "
            "variables), never pass raw credential values manually.")
    elif cat == "invalid":
        next_action = (
            "The supplied bucket name is invalid (bucket names are 3-63 "
            "lowercase letters/digits/hyphens); fix the spelling and "
            "re-run.")
    else:
        next_action = (
            "OSS control-plane query failed; review the recorded errors and "
            "re-run after fixing the root cause.")
    sys.exit(_emit(report, "DEGRADED", next_action))


if __name__ == "__main__":
    sys.exit(main())
