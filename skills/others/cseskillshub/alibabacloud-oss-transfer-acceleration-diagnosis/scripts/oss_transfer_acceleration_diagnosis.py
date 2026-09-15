#!/usr/bin/env python3
"""
oss_transfer_acceleration_diagnosis.py -- OSS transfer acceleration diagnosis
===============================================================================
SECURITY: READ-ONLY. Only issues GetBucketInfo, GetBucketTransferAcceleration
(+ ListBuckets fallback) to the OSS control plane and GetCallerIdentity to
STS. Never enables, disables, or mutates anything -- enabling transfer
acceleration is a console action described as manual guidance only.
Credentials come exclusively from the default credential chain (environment
variables for the OSS SDK, aliyun CLI default chain for STS); AK/SK are
never read, printed, or passed explicitly.

Diagnoses:
  * acceleration not taking effect (feature enabled but clients still use
    the plain endpoint instead of the accelerate domain, or the accelerate
    domain is used while the feature is not enabled)
  * product selection confusion: OSS Data Accelerator (same-region hot-data
    caching) vs Transfer Acceleration (cross-border / cross-region link
    optimization)
  * attribution of slow cross-border / cross-region access
  * transfer acceleration fee semantics (billed per direction, separately
    from and additionally to public internet traffic)

Output contract (04-spec): stdout carries a structured JSON report followed
by the machine-consumable lines:
    STATUS: OK | DEGRADED | FAIL
    NEXT_ACTION: <one actionable sentence>
Exit codes: 0 = OK/DEGRADED (usable conclusion), 1 = FAIL (required input
missing or every evidence call failed), 2 = argparse usage error only.

Usage:
  python3 oss_transfer_acceleration_diagnosis.py --bucket <name> \
      [--endpoint <endpoint-the-client-uses>] \
      [--client-location mainland|overseas|unknown] \
      [--access-pattern cross-border|cross-region|same-region|unknown] \
      [--workload hot-cache-read|upload-download|unknown] \
      [--region <expected-region>] [--scope adoption|selection|fee|all]
"""

from __future__ import annotations

import argparse
import json
import sys

import _oss_client
import _doc_lookup
from _oss_client import OssClientError

# Inline contract assertion: an illegal bucket name (including dot-bearing
# endpoint-shaped strings) must degrade to the unified
# OssClientError(category="invalid") -- never a bare oss2 ClientError
# Traceback (measured on oss2 2.19.1: oss2.Bucket.__init__ raises ClientError
# 'The bucket_name is invalid'; _build_bucket converts it, the entry records
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
    _oss_client._build_bucket("oss-cn-shenzhen.aliyuncs.com",
                              "oss-cn-hangzhou.aliyuncs.com")
    _DOTTED_BUCKET_CATEGORY = "no-error"
except OssClientError as _e:
    _DOTTED_BUCKET_CATEGORY = _e.category
except Exception:  # pragma: no cover - regression guard
    _DOTTED_BUCKET_CATEGORY = "unexpected-traceback"
assert _DOTTED_BUCKET_CATEGORY == "invalid"  # invalid: endpoint-shaped bucket name

_DEFAULT_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"
_ACCELERATE_DOMAINS = ("oss-accelerate.aliyuncs.com",
                       "oss-accelerate-overseas.aliyuncs.com")


# ---------------------------------------------------------------------------
# Pure verdict functions (each carries inline boundary assertions:
# normal / boundary / invalid inputs)
# ---------------------------------------------------------------------------

def normalize_endpoint(raw: str) -> str:
    """Strip scheme, surrounding whitespace, trailing slashes; lowercase."""
    ep = (raw or "").strip().lower()
    for scheme in ("https://", "http://"):
        if ep.startswith(scheme):
            ep = ep[len(scheme):]
    return ep.rstrip("/")


assert normalize_endpoint("oss-cn-shanghai.aliyuncs.com") == "oss-cn-shanghai.aliyuncs.com"  # normal
assert normalize_endpoint("HTTPS://OSS-Accelerate.aliyuncs.com/") == "oss-accelerate.aliyuncs.com"  # boundary: scheme+case+slash
assert normalize_endpoint("") == ""  # invalid: empty string
assert normalize_endpoint(None) == ""  # invalid: missing value


def classify_endpoint(endpoint: str) -> dict:
    """Classify the endpoint/domain a client currently uses.

    Returns {"kind": ..., "region": str|None} with kind in:
      accelerate           -- oss-accelerate.aliyuncs.com
      accelerate_overseas  -- oss-accelerate-overseas.aliyuncs.com
      malformed_accelerate -- <bucket>.oss-accelerate*.aliyuncs.com (bucket
                              name wrongly included in the endpoint; official
                              docs: this fails DNS resolution)
      public               -- oss-<region>.aliyuncs.com
      internal             -- oss-<region>-internal.aliyuncs.com
      custom_domain        -- any other hostname (custom domain / CDN / IP)
      invalid              -- empty input
    """
    ep = normalize_endpoint(endpoint)
    if not ep:
        return {"kind": "invalid", "region": None}
    if ep == _ACCELERATE_DOMAINS[0]:
        return {"kind": "accelerate", "region": None}
    if ep == _ACCELERATE_DOMAINS[1]:
        return {"kind": "accelerate_overseas", "region": None}
    if ep.endswith(".oss-accelerate.aliyuncs.com") or \
            ep.endswith(".oss-accelerate-overseas.aliyuncs.com"):
        return {"kind": "malformed_accelerate", "region": None}
    if ep.startswith("oss-") and ep.endswith(".aliyuncs.com"):
        host = ep[len("oss-"):-len(".aliyuncs.com")]
        internal = False
        if host.endswith("-internal"):
            internal = True
            host = host[:-len("-internal")]
        parts = host.split("-")
        if host and all(p.isalnum() for p in parts if p) and \
                len(parts) >= 2 and parts[0].isalpha():
            return {"kind": "internal" if internal else "public",
                    "region": host}
        return {"kind": "custom_domain", "region": None}
    return {"kind": "custom_domain", "region": None}


assert classify_endpoint("oss-accelerate.aliyuncs.com") == {"kind": "accelerate", "region": None}  # normal: accelerate
assert classify_endpoint("https://oss-accelerate-overseas.aliyuncs.com") == {"kind": "accelerate_overseas", "region": None}  # normal: overseas accelerate
assert classify_endpoint("oss-cn-shanghai.aliyuncs.com") == {"kind": "public", "region": "cn-shanghai"}  # normal: public
assert classify_endpoint("oss-cn-shanghai-internal.aliyuncs.com") == {"kind": "internal", "region": "cn-shanghai"}  # normal: internal
assert classify_endpoint("my-bucket.oss-accelerate.aliyuncs.com") == {"kind": "malformed_accelerate", "region": None}  # boundary: bucket wrongly prefixed
assert classify_endpoint("cdn.example.com") == {"kind": "custom_domain", "region": None}  # boundary: custom domain
assert classify_endpoint("") == {"kind": "invalid", "region": None}  # invalid: empty
assert classify_endpoint(None) == {"kind": "invalid", "region": None}  # invalid: missing


def adoption_verdict(ta_status: str, endpoint_kind: str) -> str:
    """Decide whether transfer acceleration is actually taking effect.

    ta_status: "enabled" | "disabled" | "unknown".
    endpoint_kind: classify_endpoint() kind (empty string when no endpoint
    was reported by the user).

    Returns:
      effective                              -- feature on + accelerate domain
      not_effective_endpoint_not_replaced    -- feature on but client still
                                                on plain/custom endpoint
      accelerate_endpoint_without_feature    -- accelerate domain used while
                                                the feature is not enabled
      feature_not_enabled                    -- feature off, no accelerate
                                                domain in use
      unknown                                -- feature state could not be
                                                determined
    """
    if ta_status == "unknown":
        return "unknown"
    accel_kinds = ("accelerate", "accelerate_overseas")
    if ta_status == "enabled":
        if endpoint_kind in accel_kinds:
            return "effective"
        return "not_effective_endpoint_not_replaced"
    # ta_status == "disabled"
    if endpoint_kind in accel_kinds:
        return "accelerate_endpoint_without_feature"
    return "feature_not_enabled"


assert adoption_verdict("enabled", "accelerate") == "effective"  # normal: working setup
assert adoption_verdict("enabled", "public") == "not_effective_endpoint_not_replaced"  # normal: classic not-taking-effect root cause
assert adoption_verdict("disabled", "accelerate") == "accelerate_endpoint_without_feature"  # normal: domain used without the feature
assert adoption_verdict("disabled", "public") == "feature_not_enabled"  # normal: nothing configured
assert adoption_verdict("disabled", "") == "feature_not_enabled"  # boundary: no endpoint reported
assert adoption_verdict("enabled", "malformed_accelerate") == "not_effective_endpoint_not_replaced"  # boundary: malformed domain also not the plain accelerate form
assert adoption_verdict("unknown", "accelerate") == "unknown"  # invalid/degraded: state unknown


def selection_advice(access_pattern: str, workload: str) -> dict:
    """Disambiguate OSS Data Accelerator vs Transfer Acceleration.

    Knowledge basis (official docs + ticket-proven pattern): the Data
    Accelerator is a same-region hot-data caching product (dedicated
    accelerator endpoint, cache-centric), while Transfer Acceleration
    optimizes cross-region / cross-border upload-download links via the
    global accelerate domains.

    access_pattern: cross-border | cross-region | same-region | unknown
    workload: hot-cache-read | upload-download | unknown
    Returns {"advised_product": ..., "rationale": ...}.
    """
    ap = (access_pattern or "unknown").strip().lower()
    wl = (workload or "unknown").strip().lower()
    if ap in ("cross-border", "cross-region"):
        return {
            "advised_product": "transfer_acceleration",
            "rationale": "Long-distance (cross-border / cross-region) "
                         "upload-download slowness is the transfer "
                         "acceleration use case: route through "
                         "oss-accelerate.aliyuncs.com (or the overseas "
                         "variant). The Data Accelerator only caches "
                         "hot data within the SAME region and cannot "
                         "optimize long-distance links.",
        }
    if ap == "same-region" and wl == "hot-cache-read":
        return {
            "advised_product": "data_accelerator",
            "rationale": "Same-region hot-data low-latency reads fit the "
                         "OSS Data Accelerator (cache product). Transfer "
                         "acceleration brings no benefit for same-region "
                         "access and only adds cost.",
        }
    if ap == "same-region":
        return {
            "advised_product": "neither",
            "rationale": "For same-region access neither product is "
                         "appropriate: clients on Alibaba Cloud should use "
                         "the free intranet endpoint; Internet clients use "
                         "the public endpoint. Transfer acceleration would "
                         "only add cost without speeding up same-region "
                         "transfers.",
        }
    return {
        "advised_product": "needs_clarification",
        "rationale": "Cannot choose between the Data Accelerator "
                     "(same-region hot-data caching) and Transfer "
                     "Acceleration (cross-border / cross-region link "
                     "optimization) without knowing where the clients run "
                     "and the access pattern; collect client location and "
                     "workload first.",
    }


assert selection_advice("cross-border", "upload-download")["advised_product"] == "transfer_acceleration"  # normal: cross-border
assert selection_advice("cross-region", "unknown")["advised_product"] == "transfer_acceleration"  # normal: cross-region
assert selection_advice("same-region", "hot-cache-read")["advised_product"] == "data_accelerator"  # normal: accelerator scenario
assert selection_advice("same-region", "upload-download")["advised_product"] == "neither"  # boundary: same-region, no product needed
assert selection_advice("unknown", "hot-cache-read")["advised_product"] == "needs_clarification"  # invalid: missing pattern
assert selection_advice("", "")["advised_product"] == "needs_clarification"  # invalid: empty inputs


def billing_notes(verdict: str) -> list:
    """Fee semantics of transfer acceleration (official doc facts).

    Facts verified against help.aliyun.com (transfer-acceleration-fees):
    enabling is free; only data actually transferred through the accelerate
    domain is billed; the acceleration fee is a SEPARATE billing item that
    stacks on top of public internet traffic fees; per-direction billing
    item codes AccM2M*/AccM2O*/AccO2M*/AccO2O*.
    """
    notes = [
        "Enabling transfer acceleration is free; fees occur only when data "
        "actually travels through the accelerate domain "
        "(oss-accelerate.aliyuncs.com / oss-accelerate-overseas.aliyuncs.com).",
        "Acceleration traffic is billed SEPARATELY from and IN ADDITION TO "
        "public internet traffic: using the accelerate domain incurs both "
        "an acceleration traffic item (AccM2MIn/Out, AccM2OIn/Out, "
        "AccO2MIn/Out, AccO2OIn/Out by direction) and the regular public "
        "internet traffic fee; using the plain public domain never incurs "
        "acceleration fees.",
        "Direction semantics: M2M = China mainland <-> China mainland, "
        "M2O = mainland -> outside mainland, O2M = outside mainland -> "
        "mainland, O2O = outside mainland <-> outside mainland. Direction-"
        "specific transfer-acceleration resource packages can offset these "
        "pay-as-you-go fees.",
    ]
    if verdict == "not_effective_endpoint_not_replaced":
        notes.append("Current setup: the feature is enabled but the client "
                     "does not use the accelerate domain, so NO "
                     "acceleration fee is produced yet (and no acceleration "
                     "effect either).")
    if verdict == "feature_not_enabled":
        notes.append("Current setup: transfer acceleration is not enabled "
                     "on this bucket, so no acceleration fee can exist; "
                     "all traffic is billed at regular rates.")
    if verdict == "accelerate_endpoint_without_feature":
        notes.append("Current setup: the accelerate domain is used while "
                     "the feature is not enabled -- requests via this "
                     "domain will fail; enable the feature (console, user "
                     "action) before expecting any effect or fee.")
    return notes


assert len(billing_notes("effective")) == 3  # normal: base facts only
assert any("NO" in n for n in billing_notes("not_effective_endpoint_not_replaced"))  # normal: extra note when not taking effect
assert any("not enabled" in n for n in billing_notes("feature_not_enabled"))  # boundary: disabled note
assert any("will fail" in n for n in billing_notes("accelerate_endpoint_without_feature"))  # boundary: feature-off note
assert isinstance(billing_notes(""), list) and len(billing_notes("")) == 3  # invalid: unknown verdict -> base facts only


def region_from_location(location: str) -> str:
    """Convert a bucket location (e.g. 'oss-cn-shanghai') to its region."""
    loc = (location or "").strip().lower()
    if loc.startswith("oss-"):
        return loc[len("oss-"):]
    return loc


assert region_from_location("oss-cn-shanghai") == "cn-shanghai"  # normal
assert region_from_location("cn-hangzhou") == "cn-hangzhou"  # boundary: already a region
assert region_from_location("") == ""  # invalid: empty


# ---------------------------------------------------------------------------
# Recommendation builder
# ---------------------------------------------------------------------------

def build_recommendations(ta_status: str, endpoint_classified: dict,
                          verdict: str, client_location: str,
                          bucket_info: dict) -> list:
    """Evidence-based advice; enablement is always user-executed guidance."""
    recs = []
    kind = endpoint_classified.get("kind") if endpoint_classified else None

    if verdict == "not_effective_endpoint_not_replaced":
        dom = _ACCELERATE_DOMAINS[0]
        if client_location == "overseas":
            dom = _ACCELERATE_DOMAINS[1]
        recs.append(
            f"Transfer acceleration is enabled but the client still uses a "
            f"non-accelerate endpoint -- this is the classic 'enabled but "
            f"not taking effect' root cause. Replace the client endpoint "
            f"with the accelerate domain '{dom}' (Endpoint value only, do "
            f"NOT include the bucket name in the endpoint string)."
        )
        recs.append(
            "Remember the feature needs ~30 minutes to propagate after "
            "being switched on; verify the effect only after the window. "
            "Clients testing through a VPN may exit from an unexpected "
            "location, which distorts the measured effect."
        )
    if verdict == "accelerate_endpoint_without_feature":
        recs.append(
            "The accelerate domain is in use but transfer acceleration is "
            "NOT enabled on this bucket; requests via the accelerate domain "
            "fail until the feature is enabled. Enabling is a user action "
            "in the OSS console (Bucket -> Transfer Acceleration -> Enable); "
            "this read-only skill never enables it."
        )
    if verdict == "feature_not_enabled":
        recs.append(
            "Transfer acceleration is not enabled on this bucket. If the "
            "symptom is slow cross-border / cross-region access, consider "
            "enabling it in the OSS console (user action) and switching "
            "clients to oss-accelerate.aliyuncs.com; acceleration traffic "
            "is billed separately, so weigh cost vs benefit."
        )
        recs.append(
            "If clients are all in the same region as the bucket, transfer "
            "acceleration is not the right tool: prefer the intranet "
            "endpoint for on-cloud clients or the plain public endpoint."
        )
    if verdict == "effective":
        recs.append(
            "Feature enabled and accelerate endpoint in use. Occasional "
            "502/504 on the accelerate domain can happen during automatic "
            "path switching -- implement client retries with exponential "
            "backoff. Cross-border results still depend on ISP link "
            "quality; acceleration cannot fully eliminate cross-border "
            "network fluctuation."
        )
        recs.append(
            "To keep costs down, route only long-distance clients through "
            "the accelerate domain and let same-region clients keep the "
            "plain public / intranet endpoints."
        )
    if kind == "malformed_accelerate":
        recs.append(
            "The configured endpoint embeds the bucket name "
            "(<bucket>.oss-accelerate.aliyuncs.com) -- official guidance: "
            "SDK/ossutil Endpoint must be exactly "
            "'oss-accelerate.aliyuncs.com' without the bucket name, "
            "otherwise DNS resolution fails."
        )
    if client_location == "overseas" and verdict in (
            "not_effective_endpoint_not_replaced", "effective"):
        recs.append(
            "For unregistered (no ICP filing) custom domains served to "
            "overseas clients via CNAME, point the CNAME at "
            "oss-accelerate-overseas.aliyuncs.com instead of the mainland "
            "accelerate domain."
        )
    if not recs and bucket_info:
        recs.append(
            "No adoption gap detected from the provided evidence; if access "
            "is still slow, collect the client location/ISP and a failing "
            "RequestId for deeper attribution."
        )
    return recs


assert any("Replace the client endpoint" in r for r in build_recommendations(
    "enabled", classify_endpoint("oss-cn-hangzhou.aliyuncs.com"),
    "not_effective_endpoint_not_replaced", "mainland", {"name": "b"}))  # normal: endpoint-not-replaced advice
assert any("NOT enabled" in r for r in build_recommendations(
    "disabled", classify_endpoint("oss-accelerate.aliyuncs.com"),
    "accelerate_endpoint_without_feature", "unknown", {"name": "b"}))  # normal: feature-off advice
assert any("without the bucket name" in r for r in build_recommendations(
    "enabled", classify_endpoint("b.oss-accelerate.aliyuncs.com"),
    "not_effective_endpoint_not_replaced", "mainland", {"name": "b"}))  # boundary: malformed endpoint advice
assert any("overseas" in r for r in build_recommendations(
    "enabled", classify_endpoint("oss-accelerate-overseas.aliyuncs.com"),
    "effective", "overseas", {"name": "b"}))  # boundary: overseas CNAME note
assert build_recommendations("unknown", None, "unknown", "unknown",
                             {"name": "b"}) != []  # invalid/degraded: fallback advice still emitted


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
        description="Diagnose OSS transfer acceleration adoption, product "
                    "selection, cross-border slowness attribution and fee "
                    "semantics (read-only)",
    )
    parser.add_argument("--bucket", default="", required=False,
                        help="OSS bucket name to diagnose (required; when absent the script emits FAIL and asks)")
    parser.add_argument("--endpoint", default="",
                        help="The endpoint/domain the client currently uses "
                             "(optional; classified for adoption verdict)")
    parser.add_argument("--client-location", default="unknown",
                        choices=["mainland", "overseas", "unknown"],
                        help="Where the affected clients run (optional)")
    parser.add_argument("--access-pattern", default="unknown",
                        choices=["cross-border", "cross-region",
                                 "same-region", "unknown"],
                        help="Distance pattern of the affected access "
                             "(optional; drives selection advice)")
    parser.add_argument("--workload", default="unknown",
                        choices=["hot-cache-read", "upload-download",
                                 "unknown"],
                        help="Workload shape (optional; drives selection "
                             "advice)")
    parser.add_argument("--region", default="",
                        help="Expected bucket region (optional; used to "
                             "build the query endpoint)")
    parser.add_argument("--scope", default="all",
                        choices=["adoption", "selection", "fee", "all"],
                        help="Diagnosis scope (default all)")
    parser.add_argument("--question", default="",
                        help="Customer's original wording (optional); when "
                             "provided, the report carries a doc_verification "
                             "section matched against official OSS docs")
    args = parser.parse_args()

    # UA-SKILL-VERSION: read and validate the skill version from
    # references/manifest.json BEFORE the first cloud call of this run. The
    # version is never invented, guessed or reused -- a missing or invalid
    # manifest stops the run (STATUS: FAIL, exit 1) with no cloud call made.
    try:
        _oss_client.skill_version()
    except _oss_client.SkillVersionError as e:
        return _emit({
            "skill": globals().get(
                "_SKILL_NAME", "alibabacloud-oss-transfer-acceleration-diagnosis"),
            "bucket": (args.bucket or "").strip(),
            "errors": [{"category": "invalid_arguments",
                        "code": "SkillVersionUnavailable",
                        "message": str(e)[:200]}],
            "auto_filled": [],
        }, "FAIL",
            "Fix this skill's references/manifest.json (a valid `version` "
            "field is required to build the User-Agent); no cloud call was "
            "made and no conclusion can be drawn without it.")

    # Record the customer's original wording BEFORE any early exit: the
    # missing-bucket guard below emits a report too, and the mandatory
    # doc-verification hook reads this module-level value.
    global _CUSTOMER_QUESTION
    _CUSTOMER_QUESTION = args.question or ""

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
            "skill": globals().get("_SKILL_NAME", "alibabacloud-oss-transfer-acceleration-diagnosis"),
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

    auto_filled = []
    # Step 1: identity pre-check / UID derivation (unconditional, degraded
    # with [WARN] on failure -- UID is only a traceability label).
    uid = _oss_client.resolve_uid()

    # Step 2: classify the client endpoint; derive the QUERY endpoint.
    # The accelerate domains cannot serve control-plane metadata queries
    # (official: accelerate domains support object access only), so the
    # query endpoint always comes from a regioned endpoint / --region /
    # the default, never from an accelerate or custom domain.
    user_endpoint = normalize_endpoint(args.endpoint)
    user_classified = classify_endpoint(user_endpoint) if user_endpoint else None
    query_endpoint = ""
    if user_classified and user_classified["kind"] in ("public", "internal"):
        query_endpoint = user_endpoint
    elif args.region.strip():
        region = args.region.strip().lower()
        query_endpoint = f"oss-{region}.aliyuncs.com"
        auto_filled.append(f"query endpoint derived from --region: {query_endpoint}")
    else:
        query_endpoint = _DEFAULT_ENDPOINT
        auto_filled.append(
            f"query endpoint auto-defaulted to {query_endpoint} "
            "(no usable --endpoint/--region provided)")

    report = {
        "skill": "alibabacloud-oss-transfer-acceleration-diagnosis",
        "bucket": args.bucket,
        "identity": {"uid": uid,
                     "note": "derived via sts get-caller-identity; empty "
                             "means the identity pre-check degraded"},
        "scope": args.scope,
        "user_endpoint": user_endpoint or None,
        "user_endpoint_kind": user_classified["kind"] if user_classified else None,
        "client_location": args.client_location,
        "query_endpoint": query_endpoint,
        "auto_filled": auto_filled,
        "bucket_info": None,
        "transfer_acceleration": {"status": "unknown", "detail": None},
        "verdict": {"adoption": "unknown"},
        "selection": None,
        "billing_notes": [],
        "recommendations": [],
        "errors": [],
    }

    # Step 3: GetBucketInfo -- bucket metadata evidence.
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

    # Step 4: GetBucketTransferAcceleration -- the core evidence call.
    ta_status = "unknown"
    try:
        ta = _oss_client.get_transfer_acceleration(args.bucket, query_endpoint)
        ta_status = "enabled" if ta["enabled"] else "disabled"
        report["transfer_acceleration"] = {
            "status": ta_status,
            "detail": "measured via oss2 GetBucketTransferAcceleration",
        }
    except OssClientError as e:
        # Degradation with [WARN] trace; if the endpoint was region-derived
        # and GetBucketInfo located the real region, retry once on it.
        print(f"[WARN] GetBucketTransferAcceleration degraded "
              f"({e.category}): {e}", file=sys.stderr)
        report["errors"].append(e.to_dict())
        real_region = region_from_location(
            bucket_info.get("location", "")) if bucket_info else ""
        retry_ep = f"oss-{real_region}.aliyuncs.com" if real_region else ""
        if retry_ep and retry_ep != query_endpoint:
            auto_filled.append(
                f"transfer-acceleration query retried on the bucket's real "
                f"region endpoint {retry_ep} (derived from GetBucketInfo "
                f"location)")
            try:
                ta = _oss_client.get_transfer_acceleration(
                    args.bucket, retry_ep)
                ta_status = "enabled" if ta["enabled"] else "disabled"
                report["transfer_acceleration"] = {
                    "status": ta_status,
                    "detail": "measured via oss2 "
                              "GetBucketTransferAcceleration on the "
                              "retry endpoint",
                }
                report["query_endpoint"] = retry_ep
            except OssClientError as e2:
                print(f"[WARN] GetBucketTransferAcceleration retry degraded "
                      f"({e2.category}): {e2}", file=sys.stderr)
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

    # Step 5: verdicts, selection advice, billing notes, recommendations.
    endpoint_kind = user_classified["kind"] if user_classified else ""
    verdict = adoption_verdict(ta_status, endpoint_kind)
    report["verdict"] = {
        "adoption": verdict,
        "transfer_acceleration_status": ta_status,
        "endpoint_kind": endpoint_kind or None,
    }
    if args.scope in ("selection", "all"):
        report["selection"] = selection_advice(args.access_pattern,
                                               args.workload)
    if args.scope in ("fee", "adoption", "all"):
        report["billing_notes"] = billing_notes(verdict)
    report["recommendations"] = build_recommendations(
        ta_status, user_classified, verdict, args.client_location,
        bucket_info)

    # Step 6: status + next action.
    if ta_status != "unknown":
        if verdict == "not_effective_endpoint_not_replaced":
            next_action = (
                "Replace the client endpoint with the accelerate domain "
                "(oss-accelerate.aliyuncs.com; overseas variant for "
                "outside-mainland clients) -- the feature is enabled but "
                "not taking effect because the client does not use it.")
        elif verdict == "accelerate_endpoint_without_feature":
            next_action = (
                "Enable transfer acceleration in the OSS console (user "
                "action; this skill is read-only), wait ~30 minutes for "
                "propagation, then re-verify the accelerate domain.")
        elif verdict == "feature_not_enabled":
            next_action = (
                "Transfer acceleration is not enabled on this bucket; if "
                "cross-border/cross-region slowness is the symptom, enable "
                "the feature in the console and switch the endpoint to "
                "oss-accelerate.aliyuncs.com, or keep plain endpoints for "
                "same-region access.")
        else:
            next_action = (
                "Transfer acceleration adoption looks effective (feature "
                "enabled + accelerate endpoint); if slowness persists, "
                "collect client location/ISP and a failing RequestId for "
                "deeper attribution.")
        sys.exit(_emit(report, "OK", next_action))

    # Degraded/failed: transfer-acceleration state unknown -- attribute
    # root error.
    # TAC-5 exit-code contract (SKILL.md: "every evidence call failed" ->
    # FAIL exit 1): the identity pre-check via the aliyun CLI default
    # chain is a traceability label, NOT OSS evidence. When neither the
    # bucket metadata (GetBucketInfo / ListBuckets fallback) nor the
    # transfer-acceleration reading succeeded, the report has zero
    # evidence to stand on -> FAIL. DEGRADED is reserved for partial
    # evidence (e.g. bucket located but the acceleration state itself
    # could not be read).
    # Inline boundary assertion on the gate logic itself (pure):
    #   both legs failed  -> FAIL,  any leg succeeded -> DEGRADED.
    def _tacd5_status(binfo, tstat):
        return "DEGRADED" if (binfo is not None or tstat != "unknown") \
            else "FAIL"
    assert _tacd5_status(None, "unknown") == "FAIL"      # invalid: zero evidence
    assert _tacd5_status({"name": "b"}, "unknown") == "DEGRADED"  # boundary
    assert _tacd5_status(None, "enabled") == "DEGRADED"  # boundary
    assert _tacd5_status({"name": "b"}, "disabled") == "DEGRADED"  # normal
    root = report["errors"][-1] if report["errors"] else {"category": "unknown"}
    cat = root.get("category", "unknown")
    if cat == "not_found":
        next_action = (
            f"Bucket '{args.bucket}' was not found (NoSuchBucket); verify "
            "the bucket name spelling and the account that owns it, then "
            "re-run the diagnosis.")
    elif cat == "permission":
        next_action = (
            "Access denied (403): grant the caller oss:GetBucketInfo / "
            "oss:GetBucketTransferAcceleration / oss:ListBuckets (see "
            "references/ram-policies.md) or confirm the bucket belongs to "
            "this account, then re-run.")
    elif cat == "credentials":
        next_action = (
            "No credentials in the environment credential chain; configure "
            "the default credential chain (aliyun configure / environment "
            "variables), never pass AK/SK manually.")
    elif cat == "network":
        next_action = (
            "Network/DNS failure reaching the endpoint host; verify DNS "
            "resolution and local network, then re-run.")
    elif cat == "invalid":
        next_action = (
            "The supplied bucket name is invalid (bucket names are 3-63 "
            "lowercase letters/digits/hyphens, no dots); fix the spelling "
            "and re-run.")
    else:
        next_action = (
            "Transfer acceleration state could not be queried; review the "
            "recorded errors and re-run after fixing the root cause, or "
            "ask the user for a console screenshot / status description of "
            "the bucket's Transfer Acceleration page and proceed on that "
            "evidence only.")
    sys.exit(_emit(report, _tacd5_status(bucket_info, ta_status),
                   next_action))


if __name__ == "__main__":
    sys.exit(main())
