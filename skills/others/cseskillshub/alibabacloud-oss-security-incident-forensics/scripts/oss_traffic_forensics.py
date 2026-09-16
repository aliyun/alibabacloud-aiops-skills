#!/usr/bin/env python3
"""
oss_traffic_forensics.py -- OSS traffic-abuse / security-incident forensics
============================================================================
SECURITY: READ-ONLY. Only issues GetBucketInfo / GetBucketPolicy /
GetBucketPublicAccessBlock / GetBucketReferer (+ ListBuckets fallback) to
the OSS control plane and GetCallerIdentity to STS. Never mutates anything.
Credentials come exclusively from the default credential chain (environment
variables for the OSS SDK, aliyun CLI default chain for STS); AK/SK are
never read, printed, or passed explicitly.

Scope (customer-side observability only):
  1. Exposure-surface audit of the affected bucket: ACL, Bucket Policy
     anonymous-allow detection, Block Public Access state, anti-hotlink
     (Referer) configuration and the Requester Pays payer -- all via the oss2
     SDK control plane. Block Public Access and Requester Pays are exposure
     NEUTRALIZERS: either one makes a nominally public bucket not anonymously
     readable, so the audit reports effective exposure, not just nominal.
  2. Real-time-log (SLS) evidence: derives the dedicated project / logstore
     names from the official convention (oss-log-<owner-uid>-<regionId> /
     oss-log-store), EXECUTES the traffic-source sequence read-only against
     the customer's own log via `sls GetHistograms` (volume pre-count) and
     `sls GetLogs`, and interprets the rows into a conclusion. The sequence
     covers CDN origin-pull mix / auth mode / public-vs-intranet split /
     VPC origin / Top IP by count AND by bytes / IP C-segment / UA / Referer
     / Top objects / object prefix / Top request URIs, always excluding
     sync_request = cdn from the IP analysis. The interpreter can and does
     conclude "normal business traffic" -- over-diagnosing legitimate volume
     as an attack is a defect on a security skill. This leg is strictly
     additive: it never raises and never contributes to `errors`, so a
     disabled log, a permission gap or an over-cap window degrades to
     emit-only (statements handed over for the SLS console) without changing
     the exposure audit's STATUS.
  3. Root-cause routing across the four-way classification (public-read
     scraping / AK leak / hotlinking / signed-URL leak) and the matching
     containment + hardening checklist.

Output contract (04-spec): stdout carries a structured JSON report followed
by the machine-consumable lines:
    STATUS: OK | DEGRADED
    NEXT_ACTION: <one actionable sentence>

Usage:
  python3 oss_traffic_forensics.py --bucket <name> \
      [--region <expected-region>] [--time-window "<e.g. last 7 days>"] \
      [--question "<customer original wording>"]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time

import _log_evidence
import _oss_client
import _sls_query
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
# first questions for this skill are often advisory ("how do I stop the
# abuse / how do I read the logs"), so the verification leg also runs when
# the wording carries an advisory signal, even after a conclusive route.
_ADVISORY_SIGNALS = (
    "怎么", "怎样", "如何", "是否", "能否", "能不能", "可以", "可不可以",
    "配置", "开通", "设置", "开启", "支持", "限制", "办法", "如何反驳",
    # P3/V7: trade-off/choice questions ("A 还是 B", "哪个好") are advisory
    # too -- the doc-verification leg must run so both options are backed
    # by official docs (anti-hotlink config + read/write ACL docs).
    "哪个", "还是", "哪种", "选",
    "how ", "how to", "can i", "is it possible", "what is", "how do",
    "which",
)


def is_advisory_question(question: str) -> bool:
    """Pure check: does the customer wording look like a configuration /
    usage advisory question (as opposed to a pure incident report)?"""
    if not isinstance(question, str):
        return False
    text = question.strip().lower()
    if not text:
        return False
    return any(sig in text for sig in _ADVISORY_SIGNALS)


assert is_advisory_question("被恶意刷流量了怎么排查？") is True      # normal: zh signal
assert is_advisory_question("how do I find the attacking IPs?") is True  # normal: en signal
assert is_advisory_question("昨晚流量突增，账单异常") is False  # boundary: pure incident report
assert is_advisory_question("") is False and is_advisory_question(None) is False  # invalid
# P3/V7: the trade-off question wording is advisory (measured: without
# these signals a STATUS OK run never attaches doc_verification).
assert is_advisory_question("防盗链和改成私有读写权限哪个好") is True  # normal: choice signal
assert is_advisory_question("改成私有还是配防盗链？") is True  # normal: A-vs-B signal
assert is_advisory_question("which is better, private ACL or hotlink protection?") is True  # normal: en choice
assert is_advisory_question("凌晨3点流量暴涨10倍") is False  # boundary: pure incident report with numbers

_DEFAULT_QUERY_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"

# Official real-time-log asset naming convention (verified against
# help.aliyun.com "OSS访问日志实时查询功能介绍"): after enabling the OSS
# real-time-log query feature, the system creates project
# oss-log-<uid>-<regionId> and dedicated logstore oss-log-store.
_SLS_LOGSTORE = "oss-log-store"


# ---------------------------------------------------------------------------
# Pure verdict functions (each carries inline boundary assertions:
# normal / boundary / invalid inputs)
# ---------------------------------------------------------------------------

def region_from_location(location: str) -> str:
    """Convert a bucket location (e.g. 'oss-cn-shanghai') to its region."""
    loc = (location or "").strip().lower()
    if loc.startswith("oss-"):
        return loc[len("oss-"):]
    return loc


assert region_from_location("oss-cn-shanghai") == "cn-shanghai"  # normal
assert region_from_location("cn-hangzhou") == "cn-hangzhou"  # boundary
assert region_from_location("") == ""  # invalid: empty


def classify_acl(acl: str) -> str:
    """Classify the bucket ACL into an exposure grade.

    Returns open_public_read_write | open_public_read | private | unknown.
    """
    a = (acl or "").strip().lower()
    if a == "public-read-write":
        return "open_public_read_write"
    if a == "public-read":
        return "open_public_read"
    if a == "private":
        return "private"
    return "unknown"


assert classify_acl("public-read") == "open_public_read"  # normal
assert classify_acl("public-read-write") == "open_public_read_write"  # normal
assert classify_acl("private") == "private"  # normal
assert classify_acl("Public-Read") == "open_public_read"  # boundary: case
assert classify_acl("") == "unknown"  # invalid: missing


def policy_anonymous_open(policy_json: str):
    """Detect whether a bucket policy allows anonymous (public) access.

    Returns (state, evidence) where state is one of:
      open       -- an Allow statement whose Principal covers everyone
                    ("*" / {"RAM": ["*"]}) with no condition restricting it;
                    an unconditional open statement always wins over a
                    conditional one regardless of statement order
      conditional-- an Allow-everyone statement that carries Condition
                    keys (e.g. IpAddress / Referer restrictions), and no
                    unconditional open statement exists
      closed     -- no Allow-everyone statement found
      unknown    -- policy missing / unparseable
    """
    text = (policy_json or "").strip()
    if not text:
        return "unknown", "policy body empty or not retrieved"
    try:
        doc = json.loads(text)
    except ValueError:
        return "unknown", "policy body is not valid JSON"
    statements = doc.get("Statement") or []
    if not isinstance(statements, list):
        return "unknown", "policy has no Statement list"
    # Scan ALL statements first: an unconditional Allow-everyone wins over a
    # conditional one no matter which one appears earlier in the list.
    open_evidence = None
    conditional_evidence = None
    for st in statements:
        if not isinstance(st, dict) or st.get("Effect") != "Allow":
            continue
        principal = st.get("Principal")
        everyone = False
        if principal == "*":
            everyone = True
        elif isinstance(principal, dict):
            for members in principal.values():
                if isinstance(members, list) and "*" in members:
                    everyone = True
                elif members == "*":
                    everyone = True
        if not everyone:
            continue
        if st.get("Condition"):
            if conditional_evidence is None:
                conditional_evidence = (
                    "an Allow statement targets Principal '*' but carries "
                    "Condition restrictions; verify the condition actually "
                    "narrows access")
        elif open_evidence is None:
            open_evidence = ("an Allow statement targets Principal '*' with no "
                             "Condition -- anonymous access is permitted by "
                             "policy")
    if open_evidence is not None:
        return "open", open_evidence
    if conditional_evidence is not None:
        return "conditional", conditional_evidence
    return "closed", "no Allow statement targets Principal '*'"


assert policy_anonymous_open(json.dumps({"Statement": [{"Effect": "Allow", "Principal": "*", "Action": ["oss:GetObject"], "Resource": ["acs:oss:*:*:b/*"]}]}))[0] == "open"  # normal: star string
assert policy_anonymous_open(json.dumps({"Statement": [{"Effect": "Allow", "Principal": {"RAM": ["*"]}, "Action": ["oss:GetObject"], "Resource": ["x"], "Condition": {"IpAddress": {"acs:SourceIp": ["1.2.3.4"]}}}]}))[0] == "conditional"  # boundary: conditioned
assert policy_anonymous_open(json.dumps({"Statement": [{"Effect": "Allow", "Principal": {"RAM": ["acs:ram::123:user/a"]}, "Action": ["oss:GetObject"], "Resource": ["x"]}]}))[0] == "closed"  # normal: restricted principal
assert policy_anonymous_open(json.dumps({"Statement": [{"Effect": "Deny", "Principal": "*", "Action": ["oss:*"], "Resource": ["x"]}]}))[0] == "closed"  # boundary: Deny statement only
assert policy_anonymous_open("")[0] == "unknown"  # invalid: empty
assert policy_anonymous_open("{not json")[0] == "unknown"  # invalid: malformed
# boundary: mixed statement order -- an unconditional Allow-everyone must win
# over a conditional one even when the conditional statement comes first.
_COND_ST = {"Effect": "Allow", "Principal": {"RAM": ["*"]}, "Action": ["oss:GetObject"], "Resource": ["x"], "Condition": {"IpAddress": {"acs:SourceIp": ["1.2.3.4"]}}}
_OPEN_ST = {"Effect": "Allow", "Principal": "*", "Action": ["oss:GetObject"], "Resource": ["acs:oss:*:*:b/*"]}
assert policy_anonymous_open(json.dumps({"Statement": [_COND_ST, _OPEN_ST]}))[0] == "open"  # boundary: conditional first, open still wins
assert policy_anonymous_open(json.dumps({"Statement": [_OPEN_ST, _COND_ST]}))[0] == "open"  # boundary: open first


def classify_payer(payer: str) -> str:
    """Classify the GetBucketRequestPayment payer value.

    Returns requester_pays | owner_pays | unknown. Requester Pays is an
    exposure neutralizer measured on a real bucket: an anonymous request
    against a payer=Requester bucket is rejected with EC 0003-00000701
    ("<RequestPayer>Anonymous Access</RequestPayer>") even when the ACL is
    public-read, so the nominal public grant is not actually exploitable by
    anonymous scrapers.
    """
    p = (payer or "").strip().lower()
    if p == "requester":
        return "requester_pays"
    if p == "bucketowner":
        return "owner_pays"
    return "unknown"


assert classify_payer("Requester") == "requester_pays"  # normal
assert classify_payer("BucketOwner") == "owner_pays"  # normal
assert classify_payer("requester") == "requester_pays"  # boundary: case
assert classify_payer("") == "unknown"  # invalid: missing
assert classify_payer(None) == "unknown"  # invalid: None


def exposure_verdict(acl_grade: str, policy_state: str,
                     public_block_enabled, referer_cfg,
                     payer_state: str = "unknown") -> dict:
    """Combine the exposure evidence into a single graded verdict.

    Two mechanisms neutralize a nominal public grant at request time, so the
    graded level must reflect the EFFECTIVE exposure rather than the raw ACL:
      * bucket-level Block Public Access enabled -- overrides every public
        ACL and anonymous policy grant;
      * Requester Pays -- an anonymous request is rejected with EC
        0003-00000701 ("<RequestPayer>Anonymous Access</RequestPayer>"), so
        anonymous scraping cannot succeed even on a public-read ACL.
    A neutralized grant is graded medium (a latent misconfiguration that
    becomes high the moment the neutralizer is switched off), never high.
    """
    findings = []
    neutralizers = []
    level = "low"

    if acl_grade == "open_public_read_write":
        level = "high"
        findings.append("bucket ACL is public-read-write: anyone can read "
                        "AND write objects -- immediate containment needed")
    elif acl_grade == "open_public_read":
        level = "high"
        findings.append("bucket ACL is public-read: anonymous GetObject is "
                        "allowed -- typical scraping precondition")
    elif acl_grade == "private":
        findings.append("bucket ACL is private (anonymous direct reads are "
                        "denied at the ACL layer)")
    else:
        findings.append("bucket ACL could not be determined from the "
                        "retrieved metadata")

    if policy_state == "open":
        level = "high"
        findings.append("bucket policy allows anonymous access "
                        "(Principal '*', no condition)")
    elif policy_state == "conditional":
        if level == "low":
            level = "medium"
        findings.append("bucket policy has an Allow-everyone statement with "
                        "conditions -- manual review of the condition "
                        "required")
    elif policy_state == "closed":
        findings.append("bucket policy does not grant anonymous access")
    else:
        findings.append("bucket policy not retrieved (absent or degraded)")

    nominal_public = (acl_grade in ("open_public_read",
                                    "open_public_read_write")
                      or policy_state == "open")

    if public_block_enabled is True:
        neutralizers.append("block-public-access")
        findings.append("bucket-level Block Public Access is ENABLED "
                        "(public ACL/policy grants are overridden)")
    elif public_block_enabled is False:
        if level == "low":
            level = "medium"
        findings.append("bucket-level Block Public Access is DISABLED")
    else:
        findings.append("Block Public Access state not retrieved "
                        "(not configured or degraded)")

    if payer_state == "requester_pays":
        neutralizers.append("requester-pays")
        findings.append("Requester Pays is ENABLED: anonymous requests are "
                        "rejected with EC 0003-00000701 "
                        "(<RequestPayer>Anonymous Access</RequestPayer>), so "
                        "anonymous scraping cannot succeed; authenticated "
                        "cross-account reads still work and are billed to "
                        "the requester")
    elif payer_state == "owner_pays":
        findings.append("Requester Pays is disabled (the bucket owner pays "
                        "for requests)")
    else:
        findings.append("Requester Pays state not retrieved (degraded)")

    effectively_public = nominal_public and not neutralizers
    if nominal_public and neutralizers:
        level = "medium"
        findings.append(
            "EFFECTIVE exposure is lower than the nominal configuration: the "
            "public grant (" + ", ".join(neutralizers) + " neutralizes it) "
            "cannot be exploited anonymously right now, but it is a latent "
            "misconfiguration -- switching the neutralizer off restores "
            "anonymous exposure immediately, so remove the public grant "
            "itself")

    # Measured pitfall: a bucket that denies anonymous reads without Referer
    # configuration reports allow_empty_referer=true + empty whitelist, which
    # is NOT a weakness -- anti-hotlink protection only has meaning for
    # effectively publicly readable resources. Emit an informational note
    # instead of a finding.
    if referer_cfg:
        if not effectively_public:
            findings.append("anti-hotlink (Referer) settings only matter "
                            "for publicly readable resources; anonymous "
                            "reads are denied on this bucket (private ACL / "
                            "no anonymous policy grant, or a neutralizer "
                            "overrides the public grant), so the Referer "
                            "state is informational, not a weakness")
        elif referer_cfg.get("allow_empty_referer") and not referer_cfg.get(
                "referers"):
            findings.append("anti-hotlink (Referer) protection is not "
                            "effective: empty Referer allowed and whitelist "
                            "empty")
        elif referer_cfg.get("allow_empty_referer"):
            if level == "low":
                level = "medium"
            findings.append("anti-hotlink whitelist exists but empty "
                            "Referer is still allowed (direct-link scrapers "
                            "bypass it)")
        else:
            findings.append("anti-hotlink whitelist configured and empty "
                            "Referer denied")
    else:
        findings.append("anti-hotlink (Referer) configuration not retrieved")

    return {"level": level, "findings": findings,
            "nominal_public": nominal_public,
            "effectively_public": effectively_public,
            "neutralizers": neutralizers}


# Normal: a public-read ACL with NO neutralizer is the classic scraping
# precondition and stays high.
assert exposure_verdict("open_public_read", "closed", False, None,
                        "owner_pays")["level"] == "high"
# Regression (measured on a real bucket, 2026-09): Block Public Access
# overrides the public ACL, so the EFFECTIVE exposure is no longer high.
# The old code kept "high" here and emitted two contradictory findings.
_BPA = exposure_verdict("open_public_read", "closed", True, None,
                        "owner_pays")
assert _BPA["level"] == "medium"  # neutralized -> latent, not exploitable
assert _BPA["neutralizers"] == ["block-public-access"]
assert _BPA["nominal_public"] is True and _BPA["effectively_public"] is False
# Regression (measured on a real bucket, 2026-09): Requester Pays rejects
# anonymous access with EC 0003-00000701 even on a public-read ACL.
_RP = exposure_verdict("open_public_read", "closed", None, None,
                       "requester_pays")
assert _RP["level"] == "medium"
assert _RP["neutralizers"] == ["requester-pays"]
assert any("0003-00000701" in f for f in _RP["findings"])  # EC cited
_BOTH = exposure_verdict("open_public_read_write", "open", True, None,
                         "requester_pays")
assert _BOTH["level"] == "medium"  # boundary: both neutralizers stack
assert _BOTH["neutralizers"] == ["block-public-access", "requester-pays"]
assert exposure_verdict("private", "closed", True,
                        {"allow_empty_referer": False,
                         "referers": ["a"]})["level"] == "low"  # normal: fully closed
assert exposure_verdict("private", "open", None, None,
                        "owner_pays")["level"] == "high"  # normal: policy opens, no neutralizer
assert exposure_verdict("private", "closed", False, None)["level"] == "medium"  # boundary: block disabled only
assert exposure_verdict("private", "conditional", None, None)["level"] == "medium"  # boundary: conditional policy
assert exposure_verdict("unknown", "unknown", None, None)["level"] == "low"  # boundary: no evidence -> never claim high
# Invalid: an unknown payer state must NOT be treated as a neutralizer
# (never downgrade exposure on evidence we failed to retrieve).
assert exposure_verdict("open_public_read", "closed", None, None,
                        "unknown")["level"] == "high"
assert exposure_verdict("open_public_read", "closed", None, None,
                        "")["neutralizers"] == []
assert exposure_verdict("private", "closed", True,
                        {"allow_empty_referer": True, "referers": []})["level"] == "low"  # boundary: referer ineffective but block enabled keeps low
# Regression (measured on a real private bucket): a bucket that denies
# anonymous reads without Referer configuration must NOT be flagged
# 'anti-hotlink not effective' -- Referer protection only has meaning for
# effectively publicly readable resources.
_PRIV_REF = exposure_verdict("private", "closed", True,
                             {"allow_empty_referer": True, "referers": []})
assert not any("not effective" in f for f in _PRIV_REF["findings"])  # no false positive
assert any("informational" in f for f in _PRIV_REF["findings"])  # informational note present
# A neutralized public bucket gets the same informational treatment.
_NEUT_REF = exposure_verdict("open_public_read", "closed", True,
                             {"allow_empty_referer": True, "referers": []})
assert not any("not effective" in f for f in _NEUT_REF["findings"])  # neutralized -> informational
# Public-read buckets with no neutralizer still get the referer-weakness
# finding.
_PUB_REF = exposure_verdict("open_public_read", "closed", None,
                            {"allow_empty_referer": True, "referers": []})
assert any("not effective" in f for f in _PUB_REF["findings"])  # normal: public-read still flagged


def corrected_endpoint_from_location(bucket_info: dict | None,
                                     current_endpoint: str) -> str:
    """Return the endpoint rebuilt from the bucket's REAL location when it
    differs from the current query endpoint.

    Measured: GetBucketInfo can succeed against a wrong-region endpoint
    while GetBucketPolicy / GetBucketPublicAccessBlock / GetBucketReferer
    return 403 there -- so the exposure audit must run against the bucket's
    actual location, not the caller-supplied region.
    """
    if not bucket_info:
        return current_endpoint
    loc = str(bucket_info.get("location") or "").strip()
    if not loc:
        return current_endpoint
    real = f"{loc}.aliyuncs.com"
    return real if real != current_endpoint else current_endpoint


assert corrected_endpoint_from_location({"location": "oss-cn-shanghai"}, "oss-cn-hangzhou.aliyuncs.com") == "oss-cn-shanghai.aliyuncs.com"  # normal: wrong region corrected
assert corrected_endpoint_from_location({"location": "oss-cn-shanghai"}, "oss-cn-shanghai.aliyuncs.com") == "oss-cn-shanghai.aliyuncs.com"  # boundary: already correct stays
assert corrected_endpoint_from_location(None, "oss-cn-hangzhou.aliyuncs.com") == "oss-cn-hangzhou.aliyuncs.com"  # invalid: no bucket info
assert corrected_endpoint_from_location({"location": ""}, "oss-cn-hangzhou.aliyuncs.com") == "oss-cn-hangzhou.aliyuncs.com"  # invalid: empty location


def sls_asset_names(uid: str, region: str) -> dict:
    """Derive the dedicated SLS real-time-log asset names for the bucket.

    Naming convention verified against official documentation
    (help.aliyun.com, OSS real-time-log query feature): the system creates
    project oss-log-<uid>-<regionId> and logstore oss-log-store in the
    bucket's region when the feature is enabled.
    """
    u = (uid or "").strip()
    r = region_from_location((region or "").strip())
    if not u or not r:
        return {"project": None, "logstore": None,
                "complete": False,
                "note": "UID or bucket region unknown -- open the SLS "
                        "console of the bucket region and look for the "
                        "project named oss-log-<your-uid>-<regionId>"}
    return {"project": f"oss-log-{u}-{r}", "logstore": _SLS_LOGSTORE,
            "complete": True,
            "note": "If this project does not exist in the SLS console, "
                    "the real-time log feature is not enabled for this "
                    "bucket yet (OSS console -> bucket -> Operations & "
                    "Monitoring -> Real-time Log -> Enable)."}


assert sls_asset_names("1234567890", "cn-shanghai")["project"] == "oss-log-1234567890-cn-shanghai"  # normal
assert sls_asset_names("1234567890", "oss-cn-hangzhou")["project"] == "oss-log-1234567890-cn-hangzhou"  # boundary: location form
assert sls_asset_names("", "cn-shanghai")["complete"] is False  # invalid: no uid
assert sls_asset_names("123", "")["complete"] is False  # invalid: no region


def pick_project_uid(caller_uid: str, owner_id: str) -> tuple:
    """Select the UID used for the oss-log-<uid>-<regionId> project name.

    F-1 fix: the real-time log project lives in the bucket OWNER's account,
    so the owner_id returned by GetBucketInfo (issued under the same
    data-plane credential that reads the bucket) is the authoritative
    derivation source whenever it is available. This keeps the attribution
    consistent with the data-plane STS credential even when the identity
    pre-check (aliyun CLI default profile) carries a DIFFERENT account.
    Falls back to the caller UID when owner_id is missing. Returns
    (project_uid, mismatch); mismatch=True requires a consistency [WARN].
    """
    c = str(caller_uid or "").strip()
    o = str(owner_id or "").strip()
    if o.isdigit():
        return o, bool(c.isdigit() and c != o)
    return c, False


assert pick_project_uid("1552974654746705", "1552974654746705") == ("1552974654746705", False)  # normal: consistent
assert pick_project_uid("1772241626973633", "1552974654746705") == ("1552974654746705", True)  # normal: cross-account skew -> owner wins + mismatch
assert pick_project_uid("", "1552974654746705") == ("1552974654746705", False)  # boundary: caller degraded -> owner used
assert pick_project_uid("1552974654746705", "") == ("1552974654746705", False)  # boundary: owner missing -> caller fallback
assert pick_project_uid("", "") == ("", False)  # invalid: both degraded
assert pick_project_uid("abc", "not-a-uid") == ("abc", False)  # invalid: owner not numeric -> caller fallback


def build_sls_queries(bucket: str) -> list:
    """Generate the traffic-source analysis query sequence.

    Field names follow the official OSS real-time-log schema (verified via
    help.aliyun.com OSS log field documentation): sign_type / access_id /
    client_ip / user_agent / referer / object / request_uri / http_status /
    sync_request / response_body_length / host / vpc_id, topic
    oss_access_log. Every query excludes CDN origin-pull requests
    (sync_request = cdn): their source IPs are CDN edge nodes, not end
    users, and would poison Top-IP analysis.

    SLS filter syntax does NOT support bracket-OR such as
    `operation: (GetObject OR HeadObject)`. To cover several operations at
    once, keep the filter on a single value or move the predicate into the
    SQL part as `WHERE operation IN ('GetObject','HeadObject')`.
    """
    b = (bucket or "").strip() or "<BUCKET>"
    base = (f"__topic__: oss_access_log and bucket: {b} and "
            f"operation: GetObject and http_status: 200 "
            f"not sync_request: cdn")
    # FO-3 fix: 4 decimals round a sub-100 KB per-row total to 0.0 GB and
    # starve the byte-weighted interpreters (endpoint_split / referer read
    # no_data and the benign short-circuit becomes unreachable on
    # small-volume windows). 8 decimals keep byte-level resolution
    # (measured live: 0.55 MB window -> 0.00004997 GB instead of 0.0).
    gb = "round(sum(response_body_length) / 1073741824.0, 8) AS bytes_gb"
    return [
        {
            "step": "0-cdn-origin-check",
            "purpose": "Determine whether CDN origin-pull traffic is mixed "
                       "in; if all requests are sync_request=cdn the "
                       "investigation moves to the CDN side (OSS-side Top "
                       "IPs are edge nodes)",
            "query": (f"__topic__: oss_access_log and bucket: {b} | SELECT "
                      "sync_request, count(*) AS req_count GROUP BY "
                      "sync_request ORDER BY req_count DESC LIMIT 10"),
        },
        {
            "step": "1-auth-mode",
            "purpose": "Most decisive first: NotSign + access_id '-' means "
                       "anonymous reads (public-read scraping); NormalSign "
                       "(or NORMAL_SIGN4 / UriSign4 under V4 signing) with a "
                       "real AccessKey ID routes to the AK-leak branch",
            "query": (f"{base} | SELECT sign_type, access_id, count(*) AS "
                      "cnt GROUP BY sign_type, access_id ORDER BY cnt DESC "
                      "LIMIT 20"),
        },
        {
            "step": "1b-endpoint-split",
            "purpose": "Split public-internet egress from same-region "
                       "internal traffic: a host ending in "
                       "-internal.aliyuncs.com is an intranet endpoint "
                       "(usually the owner's own ECS in the same region, "
                       "not billed as internet outbound), everything else is "
                       "public egress and is what the bill charges. A high "
                       "internal share means the volume is likely legitimate "
                       "business traffic, not abuse.",
            "query": (f"{base} | SELECT CASE WHEN host LIKE "
                      "'%-internal.aliyuncs.com' THEN 'internal' ELSE "
                      "'public' END AS endpoint_type, count(*) AS cnt, "
                      f"{gb} GROUP BY endpoint_type ORDER BY bytes_gb DESC"),
        },
        {
            "step": "1c-vpc-split",
            "purpose": "A non-empty vpc_id means the request came from "
                       "inside a VPC (owner-side or a peered account); an "
                       "empty/'-' vpc_id with a large volume means external "
                       "clients. This is the discriminator between an "
                       "inside-out leak (a workload in someone's VPC "
                       "exfiltrating) and external theft.",
            "query": (f"{base} | SELECT vpc_id, count(*) AS cnt, {gb} "
                      "GROUP BY vpc_id ORDER BY bytes_gb DESC LIMIT 20"),
        },
        {
            "step": "1d-daily-trend",
            "purpose": "Daily volume trend for the three-pattern shape "
                       "classification (ported from the internal traffic-"
                       "abuse playbook): burst = one day is 3x+ the median "
                       "of the other days (a specific trigger event -- the "
                       "link got shared, a scraper found the bucket); "
                       "sustained = every day high and stable (long-running "
                       "business consumption or a long-lived scrape); spiky "
                       "= large fluctuations with sharp peaks (batch-pull "
                       "scraping, the classic theft signature). The shape "
                       "narrows the root cause before the per-request steps "
                       "are read -- it never replaces them.",
            "query": (f"{base} | SELECT date_trunc('day', "
                      "from_unixtime(__time__)) AS day, count(*) AS cnt, "
                      f"{gb} GROUP BY day ORDER BY day ASC LIMIT 30"),
        },
        {
            "step": "2-top-client-ip",
            "purpose": "Concentration on few IPs = scripted scraping from "
                       "fixed hosts; wide dispersion + third-party referers "
                       "= hotlinking. Ranked by request COUNT; always read "
                       "it together with step 2b.",
            "query": (f"{base} | SELECT client_ip, sign_type, count(*) AS "
                      "cnt GROUP BY client_ip, sign_type ORDER BY cnt DESC "
                      "LIMIT 30"),
        },
        {
            "step": "2b-top-client-ip-by-bytes",
            "purpose": "Ranked by BYTES, which is what the bill charges and "
                       "what decides the real abuser. Measured on real "
                       "tickets the count-top IP and the bytes-top IP are "
                       "frequently DIFFERENT hosts (one IP issuing many "
                       "small requests, another draining a few huge "
                       "objects), so a count-only ranking names the wrong "
                       "IP for containment.",
            "query": (f"{base} | SELECT client_ip, sign_type, count(*) AS "
                      f"cnt, {gb} GROUP BY client_ip, sign_type ORDER BY "
                      "bytes_gb DESC LIMIT 30"),
        },
        {
            "step": "2c-top-ip-c-segment",
            "purpose": "Aggregate to the /24 (C-segment): abuse fleets "
                       "rotate individual addresses inside one block, so "
                       "per-IP ranking understates a single actor. Block at "
                       "CIDR granularity (see containment_policy_template) "
                       "rather than chasing single IPs.",
            "query": (f"{base} | SELECT regexp_extract(client_ip, "
                      "'(^[0-9]+\\.[0-9]+\\.[0-9]+)') AS ip_c_segment, "
                      f"count(*) AS cnt, {gb} GROUP BY ip_c_segment ORDER "
                      "BY bytes_gb DESC LIMIT 30"),
        },
        {
            "step": "3-user-agent",
            "purpose": "Raw client UA (e.g. bare Java/python HTTP clients) "
                       "indicates bulk programmatic downloads. A browser UA "
                       "with a non-browser referer, or a scripting UA "
                       "(python/aiohttp/curl) with the owner's own site as "
                       "referer, means the business front-end was bypassed "
                       "and the storage layer is being hit directly.",
            "query": (f"{base} | SELECT user_agent, count(*) AS cnt, "
                      f"{gb} GROUP BY user_agent ORDER BY cnt DESC "
                      "LIMIT 30"),
        },
        {
            "step": "4-referer",
            "purpose": "Empty referer '-' = direct programmatic calls; "
                       "third-party domains = hotlinking (bandwidth theft). "
                       "An empty referer is not automatically malicious -- "
                       "native apps and server-side callers legitimately "
                       "send none, so cross-check against step 3 before "
                       "concluding.",
            "query": (f"{base} | SELECT referer, count(*) AS cnt, "
                      f"{gb} GROUP BY referer ORDER BY bytes_gb DESC "
                      "LIMIT 30"),
        },
        {
            "step": "5-top-objects",
            "purpose": "Same object fetched dozens/hundreds of times = "
                       "systematic bulk enumeration; do not infer file "
                       "content from key names",
            "query": (f"{base} | SELECT url_decode(object) AS object_name, "
                      f"count(*) AS cnt, {gb} GROUP BY object_name "
                      "ORDER BY bytes_gb DESC LIMIT 50"),
        },
        {
            "step": "5b-top-object-prefix",
            "purpose": "Aggregate to the first path segment: one directory "
                       "accounting for nearly all bytes means the abuser "
                       "targeted a specific dataset rather than crawling "
                       "the bucket, which narrows the containment scope to "
                       "that prefix.",
            "query": (f"{base} | SELECT split_part(url_decode(object), '/', "
                      f"1) AS top_prefix, count(*) AS cnt, {gb} GROUP BY "
                      "top_prefix ORDER BY bytes_gb DESC LIMIT 30"),
        },
        {
            "step": "6-top-request-uris",
            "purpose": "URLs carrying signature parameters (OSSAccessKeyId "
                       "/ Signature) = presigned URL leak or abuse; bare "
                       "repeated URLs = anonymous direct access",
            "query": (f"{base} | SELECT request_uri, count(*) AS cnt, "
                      f"{gb} GROUP BY request_uri ORDER BY cnt DESC "
                      "LIMIT 30"),
        },
    ]


_qs = build_sls_queries("example-bucket")
assert len(_qs) == 13 and all("bucket: example-bucket" in q["query"] for q in _qs)  # normal
# FO-3 regression guard: every bytes_gb projection keeps byte-level
# resolution (8 decimals); a ~50 KB per-group total must NOT round to 0.0
# (live-measured on a 24-request window: round(...,4) -> "0.0",
# round(...,8) -> "0.00004997").
assert any(", 8) AS bytes_gb" in q["query"] for q in _qs)  # normal
assert round(50 * 1024 / 1073741824.0, 4) == 0.0  # the defect: 4 decimals eat a 50 KB total
assert round(50 * 1024 / 1073741824.0, 8) > 0.0  # the fix: 8 decimals keep it
assert all("1073741824.0, 8)" in q["query"] or "bytes_gb" not in q["query"]
               or q["step"] == "0-cdn-origin-check" for q in _qs)  # normal: uniform precision
# P4 regression guard: the daily-trend step exists and uses the verified
# date_trunc syntax (live-measured 2026-09-02 on oss-log-<uid>-cn-hangzhou).
assert "date_trunc('day', from_unixtime(__time__))" in {
    q["step"]: q["query"] for q in _qs}["1d-daily-trend"]  # normal
assert all("sync_request: cdn" in q["query"] or q["step"] == "0-cdn-origin-check" for q in _qs)  # normal: CDN exclusion
assert "example-bucket" in build_sls_queries("")[0]["query"] or "<BUCKET>" in build_sls_queries("")[1]["query"]  # invalid: empty bucket falls back to placeholder
_IDS = [q["step"] for q in _qs]
# The seven original step ids are referenced by SKILL.md / references / evals
# and must survive any extension of the sequence.
assert [i for i in _IDS if i in ("0-cdn-origin-check", "1-auth-mode",
                                 "2-top-client-ip", "3-user-agent",
                                 "4-referer", "5-top-objects",
                                 "6-top-request-uris")] == \
    ["0-cdn-origin-check", "1-auth-mode", "2-top-client-ip", "3-user-agent",
     "4-referer", "5-top-objects", "6-top-request-uris"]
assert len(set(_IDS)) == len(_IDS)  # boundary: no duplicate step id
_Q = {q["step"]: q["query"] for q in _qs}
assert "ORDER BY bytes_gb DESC" in _Q["2b-top-client-ip-by-bytes"]  # normal: bytes ranking exists
assert "ORDER BY cnt DESC" in _Q["2-top-client-ip"]  # boundary: count ranking kept alongside
assert "-internal.aliyuncs.com" in _Q["1b-endpoint-split"]  # normal: public vs intranet split
assert "vpc_id" in _Q["1c-vpc-split"]  # normal: inside-out vs external discriminator
assert "regexp_extract" in _Q["2c-top-ip-c-segment"]  # normal: C-segment aggregation
assert "split_part" in _Q["5b-top-object-prefix"]  # normal: directory-level aggregation
assert not any("(" in q.split("|")[0] and " OR " in q.split("|")[0]
               for q in _Q.values())  # guardrail: SLS filter has no bracket-OR


_ANONYMOUS_BRANCHES = ("public-read-scraping", "hotlinking")

_NEUTRALIZER_EXCLUSION = {
    "block-public-access":
        "bucket-level Block Public Access overrides every public ACL and "
        "anonymous policy grant, so an unsigned (anonymous) request is "
        "rejected before it can download anything",
    "requester-pays":
        "Requester Pays rejects anonymous requests with EC 0003-00000701 "
        "(<RequestPayer>Anonymous Access</RequestPayer>), so an unsigned "
        "(anonymous) request cannot succeed",
}


def route_root_causes(acl_grade: str, policy_state: str,
                      verdict: dict | None = None) -> list:
    """Order the four-way root-cause classification by current evidence.

    The decisive evidence (sign_type / IP / UA / referer distributions)
    comes from the real-time-log queries; this function ranks the candidates
    using the exposure evidence already collected, so the Agent knows which
    branch to confirm first. When `verdict` carries a neutralizer (Block
    Public Access / Requester Pays), the two ANONYMOUS branches are ruled
    out by configuration alone -- that is a conclusion, not a direction, and
    it is stated as such instead of leaving the Agent to rank a branch that
    cannot happen.
    """
    causes = [
        {
            "id": "public-read-scraping",
            "name": "Public-read bucket scraped anonymously",
            "severity": "high",
            "log_signature": "sign_type=NotSign and access_id='-' dominate, "
                             "IPs concentrated on few hosts",
        },
        {
            "id": "ak-leak",
            "name": "AccessKey leaked and abused",
            "severity": "high",
            "log_signature": "sign_type=NormalSign (or NORMAL_SIGN4 for V4) "
                             "with an AccessKey ID the owner does not "
                             "recognize, source IPs outside the owner's "
                             "known servers",
        },
        {
            "id": "hotlinking",
            "name": "Public objects hotlinked by third-party sites",
            "severity": "medium",
            "log_signature": "sign_type=NotSign, many distinct IPs, referer "
                             "points at third-party domains",
        },
        {
            "id": "signed-url-leak",
            "name": "Presigned URL leaked or over-shared",
            "severity": "medium",
            "log_signature": "sign_type=NormalSign/UriSign (UriSign4 for V4) "
                             "from many distinct IPs with irregular user "
                             "agents; request_uri carries signature "
                             "parameters",
        },
    ]

    v = verdict or {}
    neutralizers = [n for n in (v.get("neutralizers") or [])
                    if n in _NEUTRALIZER_EXCLUSION]
    nominal_public = v.get("nominal_public")
    if nominal_public is None:
        nominal_public = (acl_grade in ("open_public_read",
                                        "open_public_read_write")
                          or policy_state == "open")
    effectively_public = v.get("effectively_public")
    if effectively_public is None:
        effectively_public = bool(nominal_public) and not neutralizers
    anon_ruled_out = bool(nominal_public) and bool(neutralizers)

    by_id = {c["id"]: c for c in causes}
    for c in causes:
        c["state"] = "candidate"
        if anon_ruled_out and c["id"] in _ANONYMOUS_BRANCHES:
            c["state"] = "ruled_out_by_config"
            c["excluded_by"] = list(neutralizers)
            c["exclusion_reason"] = "; ".join(
                _NEUTRALIZER_EXCLUSION[n] for n in neutralizers)

    if effectively_public:
        order = ["public-read-scraping", "hotlinking", "ak-leak",
                 "signed-url-leak"]
    elif acl_grade == "private" and policy_state == "closed":
        order = ["ak-leak", "signed-url-leak", "public-read-scraping",
                 "hotlinking"]
    elif anon_ruled_out:
        # Nominal public grant, but every anonymous branch is neutralized:
        # the traffic must be signed, so the credential branches lead.
        order = ["ak-leak", "signed-url-leak", "public-read-scraping",
                 "hotlinking"]
    else:
        order = ["public-read-scraping", "ak-leak", "hotlinking",
                 "signed-url-leak"]
    return [by_id[i] for i in order]


assert route_root_causes("open_public_read", "closed")[0]["id"] == "public-read-scraping"  # normal
assert route_root_causes("private", "closed")[0]["id"] == "ak-leak"  # normal: closed surface -> credential branch first
assert route_root_causes("unknown", "unknown")[0]["id"] == "public-read-scraping"  # boundary: no evidence keeps default order
assert len(route_root_causes("", "")) == 4  # boundary: always four candidates
# Normal: the exposure verdict drives the ranking, and a neutralized public
# grant rules the anonymous branches OUT by configuration (measured 2026-09
# on a public-read bucket whose anonymous GET was rejected by Requester Pays
# with EC 0003-00000701 while the old code still ranked scraping first).
_NEUT_V = exposure_verdict("open_public_read", "closed", None, None,
                           "requester_pays")
_NEUT_R = route_root_causes("open_public_read", "closed", _NEUT_V)
assert _NEUT_R[0]["id"] == "ak-leak"  # credential branch leads
assert _NEUT_R[-1]["state"] == "ruled_out_by_config"  # anonymous branch last
assert _NEUT_R[-1]["excluded_by"] == ["requester-pays"]
assert any("0003-00000701" in c.get("exclusion_reason", "")
           for c in _NEUT_R)  # EC carried into the exclusion reason
assert sum(1 for c in _NEUT_R
           if c["state"] == "ruled_out_by_config") == 2  # both anon branches
# Normal: an effectively public bucket keeps the scraping-first order.
_OPEN_V = exposure_verdict("open_public_read", "closed", False, None,
                           "owner_pays")
assert route_root_causes("open_public_read", "closed",
                         _OPEN_V)[0]["id"] == "public-read-scraping"
assert all(c["state"] == "candidate" for c in
           route_root_causes("open_public_read", "closed", _OPEN_V))
# Boundary: a verdict without neutralizer keys behaves like the 2-arg call.
assert [c["id"] for c in route_root_causes("open_public_read", "closed", {})] \
    == [c["id"] for c in route_root_causes("open_public_read", "closed")]
# Invalid: an unrecognized neutralizer name is ignored, never trusted.
assert route_root_causes(
    "open_public_read", "closed",
    {"nominal_public": True, "effectively_public": True,
     "neutralizers": ["not-a-mechanism"]})[0]["id"] == "public-read-scraping"
assert len(route_root_causes("", "", None)) == 4  # invalid: empty inputs


def containment_plan(cause_ids: list, latent_public_grant: bool = False) -> list:
    """Build the containment + hardening checklist for the ranked causes.

    Every item is MANUAL GUIDANCE for the customer; this skill never
    applies any change (read-only). `latent_public_grant` is True when a
    neutralizer (Block Public Access / Requester Pays) is currently masking
    a public ACL or anonymous policy grant.
    """
    items = []
    if "public-read-scraping" in cause_ids or "hotlinking" in cause_ids:
        items.append(
            "Pick the containment direction as a TRADE-OFF, never a "
            "one-sided default -- a real customer who was told only 'switch "
            "to Private' broke their site's images and switched the bucket "
            "back to public-read the same day. Decide by business "
            "dependency: (a) NO anonymous / legacy-link dependency -- switch "
            "the bucket ACL to Private (Permission Control -> Read/Write "
            "Permission) and remove any bucket-policy statement allowing "
            "Principal '*' (strongest security posture; readers move to "
            "signed URLs / STS); (b) business still depends on anonymous "
            "reads or existing public links (site images, app assets, "
            "shared URLs) -- keep public-read and layer the anti-hotlink "
            "Referer whitelist (deny empty Referer), optionally Requester "
            "Pays, knowing every client must then sign its requests; (b) "
            "keeps the business alive while (a) is being migrated. The "
            "full comparison table (security gain / cost / business impact "
            "/ preconditions) is in references/traffic-abuse-playbook.md.")
        items.append(
            "Enable Block Public Access for the bucket to override any "
            "residual public grant.")
        items.append(
            "Migrate legitimate readers to presigned URLs or STS temporary "
            "credentials instead of anonymous reads.")
    if latent_public_grant:
        items.append(
            "The public ACL / anonymous policy grant is currently masked by "
            "a neutralizer (Block Public Access or Requester Pays), so "
            "anonymous abuse cannot happen right now -- but the grant itself "
            "is still there. Remove it (ACL to Private, delete the "
            "Principal '*' statement) AND keep the neutralizer enabled: "
            "turning the neutralizer off restores anonymous exposure "
            "immediately.")
    if "hotlinking" in cause_ids:
        items.append(
            "Configure the anti-hotlink (Referer) whitelist (Permission "
            "Control -> Anti-Hotlink) with your own domains and deny empty "
            "Referer; for public static assets, serve them through CDN "
            "with URL authentication instead of direct OSS links.")
    if "ak-leak" in cause_ids:
        items.append(
            "Disable or rotate the leaked AccessKey in the RAM console "
            "immediately, issue a new one, and audit where the old key was "
            "stored (public code repositories, client bundles).")
        items.append(
            "Replace long-lived AK/SK with STS temporary credentials and "
            "least-privilege RAM policies scoped to the bucket.")
    if "signed-url-leak" in cause_ids:
        items.append(
            "Shorten presigned-URL expiration, stop sharing URLs in public "
            "channels, and rotate the signing AccessKey if the URL was "
            "posted externally.")
    items.append(
        "Set an outbound-traffic alarm on the bucket (OSS console -> "
        "Operations & Monitoring -> Monitoring -> Internet Outbound "
        "Traffic -> alarm rule at 3-5x normal volume).")
    items.append(
        "Block abusive source IPs by IP/CIDR with a Bucket Policy Deny "
        "statement (OSS console -> bucket -> Permission Control -> Bucket "
        "Policy -> add a Deny statement with condition acs:SourceIp set to "
        "the abuser's IP/CIDR range; Deny takes priority over any Allow). "
        "This is the high-frequency containment action in real tickets; "
        "keep the legitimate source IPs out of the blocked ranges.")
    items.append(
        "Keep the real-time log (SLS) feature enabled so the next anomaly "
        "can be traced with the query sequence from this report. "
        "Note: real-time log collection starts at enablement and is NOT "
        "retroactive -- enabling it today cannot recover yesterday's "
        "requests, so the traffic that already happened is only traceable "
        "if the feature was already on.")
    items.append(
        "OSS itself can only block specified source IPs; it has NO "
        "per-IP request-rate limiting ('block an IP after N requests per "
        "minute'). Rate-based control is a WAF / ESA (Edge Security "
        "Acceleration) capability -- put ESA or WAF in front of the bucket "
        "when the abuse is high-frequency request flooding rather than "
        "plain volume.")
    items.append(
        "If the bucket was moved into the SANDBOX (volumetric attack or "
        "violating content), it cannot be lifted by changing the ACL or a "
        "Bucket Policy; follow the DDoS-protection guidance in "
        "references/traffic-abuse-playbook.md and open a support ticket for "
        "the sandbox state itself.")
    return items


assert any("ACL" in i for i in containment_plan(["public-read-scraping"]))  # normal
assert any("AccessKey" in i for i in containment_plan(["ak-leak"]))  # normal
assert any("acs:SourceIp" in i for i in containment_plan([]))  # normal: IP/CIDR block guidance is universal
assert len(containment_plan([])) >= 2  # boundary: universal hardening still emitted
assert containment_plan(["hotlinking"]) != containment_plan(["ak-leak"])  # boundary: branch-specific
# Normal: a neutralized public grant still gets the latent-grant item.
_LATENT = containment_plan(["ak-leak"], latent_public_grant=True)
assert any("masked by a neutralizer" in i for i in _LATENT)
assert len(_LATENT) == len(containment_plan(["ak-leak"])) + 1  # exactly one extra
# Boundary: flag off keeps the checklist unchanged.
assert containment_plan([], latent_public_grant=False) == containment_plan([])
# Product-boundary knowledge measured in real tickets: customers ask OSS for
# per-IP rate limiting, which OSS does not provide.
assert any("rate limiting" in i for i in containment_plan([]))  # WAF/ESA boundary stated
assert any("NOT retroactive" in i for i in containment_plan([]))  # log history boundary stated
# P3/V7 regression: the containment for anonymous branches must present
# the private-vs-anti-hotlink TRADE-OFF (a real ticket switched back to
# public-read after a one-sided "go private" advice broke the site images).
_V7 = containment_plan(["public-read-scraping"])
assert any("TRADE-OFF" in i for i in _V7)  # normal: both directions offered
assert any("anti-hotlink" in i for i in _V7)  # option (b) exists in the same item or the hotlinking branch
assert any("playbook" in i for i in _V7)  # points at the full comparison table


def deny_ip_policy_template(bucket: str, ip_cidrs: list,
                            vpc_ids: list | None = None) -> dict:
    """Build a ready-to-paste Bucket Policy Deny statement for abusive IPs.

    This is the highest-frequency containment action in real traffic-abuse
    tickets, so the report hands over copyable JSON instead of prose. The
    condition-key guardrails below are official semantics, each one a
    measured pitfall:
      * `acs:SourceIp` matches PUBLIC-network requests only. A policy meant
        to keep specific VPCs working while blocking public IPs must also
        carry `acs:SourceVpc`, otherwise VPC clients are denied too.
      * Multiple condition operators inside ONE Statement are AND-ed
        (FO-2, measured): to keep specific VPCs reachable while denying
        blacklisted public IPs, the VPC condition MUST be negative --
        `StringNotEquals` on `acs:SourceVpc`. A positive `StringEquals`
        would require the request to come from a blacklisted public IP AND
        from the whitelisted VPC at the same time; a public-internet request
        never originates from a VPC, so the Deny would NEVER fire and the
        blacklist would silently do nothing. For a missing condition key
        (public requests carry no `acs:SourceVpc`), `StringNotEquals`
        evaluates true, which is exactly what a public-IP blacklist needs.
      * `StringEquals` does NOT support wildcards -- use the `IpAddress`
        operator for CIDR matching and `StringLike` with "*" for the
        "any public source" side.
      * Deny always wins over Allow, so the legitimate source IPs must be
        kept out of the blocked ranges.
      * There is no `acs:Referer` condition key for anti-hotlinking; the
        Referer whitelist is a bucket-level configuration
        (GetBucketReferer / console Anti-Hotlink), not a policy condition.
    """
    b = (bucket or "").strip() or "<BUCKET>"
    cidrs = [str(c).strip() for c in (ip_cidrs or []) if str(c).strip()]
    condition: dict = {}
    notes = [
        "Deny takes priority over any Allow, so verify the ranges contain no "
        "legitimate client before applying.",
        "Apply via OSS console -> bucket -> Permission Control -> Bucket "
        "Policy. This skill only drafts the statement; it never writes it.",
    ]
    if cidrs:
        condition["IpAddress"] = {"acs:SourceIp": cidrs}
    else:
        notes.append("No IP/CIDR supplied: the statement below carries an "
                     "empty acs:SourceIp list, which matches nothing. Fill "
                     "in the abusive ranges from the step-2 Top-client-IP "
                     "result first.")
    vpcs = [str(v).strip() for v in (vpc_ids or []) if str(v).strip()]
    if vpcs:
        condition["StringNotEquals"] = {"acs:SourceVpc": vpcs}
        notes.append(
            "Condition operators inside one Statement are AND-ed, so the "
            "VPC guard is NEGATIVE: Deny fires for the blacklisted "
            "IP/CIDR ranges AND any request NOT originating from the listed "
            "VPCs. Public-internet requests carry no acs:SourceVpc key, for "
            "which StringNotEquals evaluates true -- the blacklisted public "
            "IPs are therefore denied, while the listed VPCs stay reachable.")
    else:
        notes.append(
            "If legitimate clients reach this bucket from inside a VPC and "
            "must stay reachable, add a StringNotEquals acs:SourceVpc "
            "condition with those VPC IDs -- NOT StringEquals: inside a "
            "Deny statement a positive StringEquals would AND the two "
            "conditions, and since a public-internet abuser never originates "
            "from your VPC, the Deny would never fire for public IPs at all "
            "(a measured pitfall: a silently ineffective blacklist).")
    return {
        "Version": "1",
        "Statement": [
            {
                "Effect": "Deny",
                "Principal": ["*"],
                "Action": ["oss:*"],
                "Resource": [f"acs:oss:*:*:{b}", f"acs:oss:*:*:{b}/*"],
                "Condition": condition,
            }
        ],
        "notes": notes,
    }


_TPL = deny_ip_policy_template("my-bucket", ["1.2.3.0/24", "5.6.7.8"])
assert _TPL["Statement"][0]["Effect"] == "Deny"  # normal
assert _TPL["Statement"][0]["Condition"]["IpAddress"]["acs:SourceIp"] == ["1.2.3.0/24", "5.6.7.8"]
assert _TPL["Statement"][0]["Resource"] == ["acs:oss:*:*:my-bucket",
                                            "acs:oss:*:*:my-bucket/*"]
assert "acs:Referer" not in json.dumps(_TPL)  # guardrail: no invented condition key
# FO-2 regression: condition operators inside one Statement are AND-ed,
# so the VPC guard in a public-IP blacklist Deny MUST be StringNotEquals.
# Three input classes are asserted separately: public IP only, VPC only,
# and the mixed case (blacklisted public IP + whitelisted VPC).
_MIXED = deny_ip_policy_template("b", ["1.2.3.4"], ["vpc-abc"])  # mixed
assert _MIXED["Statement"][0]["Condition"] == {
    "IpAddress": {"acs:SourceIp": ["1.2.3.4"]},
    "StringNotEquals": {"acs:SourceVpc": ["vpc-abc"]}}  # normal: negative VPC guard
assert "StringEquals" not in json.dumps(
    _MIXED["Statement"][0]["Condition"])  # the AND-deadlock operator must not appear
assert any("AND-ed" in n for n in _MIXED["notes"])  # the semantics are explained
assert any("NEGATIVE" in n for n in _MIXED["notes"])  # the guard direction is stated
_PUB_ONLY = deny_ip_policy_template("b", ["1.2.3.4"])  # public IP only
assert _PUB_ONLY["Statement"][0]["Condition"] == {
    "IpAddress": {"acs:SourceIp": ["1.2.3.4"]}}  # normal: no VPC condition at all
assert any("StringNotEquals acs:SourceVpc" in n for n in _PUB_ONLY["notes"])
_VPC_ONLY = deny_ip_policy_template("b", [], ["vpc-abc"])  # vpc only, no IP list
assert _VPC_ONLY["Statement"][0]["Condition"] == {
    "StringNotEquals": {"acs:SourceVpc": ["vpc-abc"]}}  # boundary: guard alone
assert any("matches nothing" in n for n in _VPC_ONLY["notes"])  # empty IP list still warned
_EMPTY = deny_ip_policy_template("", [])
assert _EMPTY["Statement"][0]["Resource"][0] == "acs:oss:*:*:<BUCKET>"  # invalid: placeholder bucket
assert _EMPTY["Statement"][0]["Condition"] == {}  # invalid: no CIDR -> matches nothing
assert any("matches nothing" in n for n in _EMPTY["notes"])  # and says so
assert json.dumps(_TPL)  # serializable


# ---------------------------------------------------------------------------
# Forensics orchestration
# ---------------------------------------------------------------------------

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
        description="OSS traffic-abuse / security-incident forensics "
                    "(read-only: exposure audit + real-time-log query "
                    "toolkit + root-cause routing)",
    )
    parser.add_argument("--bucket", default="", required=False,
                        help="Affected OSS bucket name (required; when absent the script emits FAIL and asks)")
    parser.add_argument("--region", default="",
                        help="Expected bucket region (optional; used to "
                             "build the query endpoint when unknown)")
    parser.add_argument("--time-window", default="last 7 days",
                        help="Human-readable anomaly window echoed into the "
                             "report (e.g. 'last 7 days', "
                             "'2026-08-20 to 2026-08-26')")
    parser.add_argument("--question", default="",
                        help="Customer's original question wording; enables "
                             "the official-doc verification leg "
                             "(doc_verification section in the JSON)")
    parser.add_argument("--log-days", default="1",
                        help="How many days back to scan the OSS real-time "
                             "log (1-7; the log keeps a rolling 7 days). "
                             "Ignored when --time-window already states a "
                             "day count.")
    parser.add_argument("--no-log-execution", action="store_true",
                        help="Do not execute the real-time-log queries; emit "
                             "the statement sequence only (for offline review "
                             "or when the caller lacks log read permission)")
    args = parser.parse_args()

    try:
        args.log_days = int(str(args.log_days).strip())
    except (TypeError, ValueError):
        args.log_days = 1
    if args.log_days < 1:
        args.log_days = 1
    elif args.log_days > _sls_query.MAX_LOG_DAYS:
        args.log_days = _sls_query.MAX_LOG_DAYS

    # UA-SKILL-VERSION: read and validate the skill version from
    # references/manifest.json BEFORE the first cloud call of this run (OSS
    # control plane, STS identity and the SLS query leg all carry it in their
    # User-Agent). The version is never invented, guessed or reused -- a missing
    # or invalid manifest stops the run (STATUS: FAIL, exit 1) with no cloud call.
    try:
        _oss_client.skill_version()
    except _oss_client.SkillVersionError as e:
        return _emit({
            "skill": globals().get(
                "_SKILL_NAME", "alibabacloud-oss-security-incident-forensics"),
            "bucket": (args.bucket or "").strip(),
            "errors": [{"category": "invalid_arguments",
                        "code": "SkillVersionUnavailable",
                        "message": str(e)[:200]}],
            "auto_filled": [],
        }, "FAIL",
            "Fix this skill's references/manifest.json (a valid `version` "
            "field is required to build the User-Agent); no cloud call was "
            "made and no forensics conclusion can be drawn without it.")

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
            "skill": globals().get("_SKILL_NAME", "alibabacloud-oss-security-incident-forensics"),
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
    question = args.question.strip() if isinstance(args.question, str) else ""

    auto_filled = []
    # Step 1: identity pre-check / UID derivation (unconditional, degraded
    # with [WARN] on failure -- UID is only a traceability label and feeds
    # the SLS project-name derivation).
    uid = _oss_client.resolve_uid()

    # Step 2: resolve the endpoint used to query the control plane.
    if args.region.strip():
        region = args.region.strip().lower()
        region = region_from_location(region)
        query_endpoint = f"oss-{region}.aliyuncs.com"
    else:
        query_endpoint = _DEFAULT_QUERY_ENDPOINT
        auto_filled.append(
            f"query endpoint auto-defaulted to {query_endpoint} "
            "(no --region provided; falls back to ListBuckets location "
            "discovery on mismatch)")

    report = {
        "skill": "alibabacloud-oss-security-incident-forensics",
        "bucket": args.bucket,
        "time_window": args.time_window,
        "identity": {"uid": uid,
                     "note": "derived via sts get-caller-identity (aliyun "
                             "CLI default credential chain); empty means "
                             "the identity pre-check degraded. Bucket "
                             "attribution and the SLS project name are "
                             "derived from the bucket owner_id "
                             "(GetBucketInfo), not from this label, so the "
                             "identity chain and the data plane can never "
                             "disagree on ownership."},
        "query_endpoint": query_endpoint,
        "bucket_region": "",
        "auto_filled": auto_filled,
        "exposure": None,
        "realtime_log": None,
        "log_evidence": None,
        "root_cause_candidates": None,
        "containment": [],
        "containment_policy_template": None,
        "errors": [],
    }
    if question:
        report["question"] = question

    # Step 3: GetBucketInfo -- the core evidence call (region + ACL).
    bucket_info = None
    try:
        bucket_info = _oss_client.get_bucket_info(args.bucket, query_endpoint)
    except OssClientError as e:
        print(f"[WARN] GetBucketInfo degraded ({e.category}): {e}",
              file=sys.stderr)
        report["errors"].append(e.to_dict())
        # Fallback: ListBuckets prefix lookup to locate the bucket region,
        # then retry GetBucketInfo against the discovered endpoint.
        try:
            located = _oss_client.list_buckets(prefix=args.bucket)
            hits = [b for b in located if b["name"] == args.bucket]
            if hits:
                discovered = hits[0]["location"]
                retry_endpoint = (
                    f"{discovered}.aliyuncs.com" if discovered else "")
                if retry_endpoint and retry_endpoint != query_endpoint:
                    auto_filled.append(
                        f"bucket region discovered via ListBuckets: "
                        f"{discovered}; retried GetBucketInfo on "
                        f"{retry_endpoint}")
                    query_endpoint = retry_endpoint
                    try:
                        bucket_info = _oss_client.get_bucket_info(
                            args.bucket, query_endpoint)
                    except OssClientError as e3:
                        print(f"[WARN] GetBucketInfo retry degraded "
                              f"({e3.category}): {e3}", file=sys.stderr)
                        report["errors"].append(e3.to_dict())
                if bucket_info is None:
                    report["errors"].append({
                        "category": "unknown",
                        "code": "RegionDiscoveryIncomplete",
                        "message": f"ListBuckets located the bucket in "
                                   f"{discovered} but GetBucketInfo could "
                                   f"not be completed",
                    })
            else:
                report["errors"].append({
                    "category": "not_found",
                    "code": "ListBucketsNoMatch",
                    "message": f"ListBuckets(prefix={args.bucket}) returned "
                               f"{len(located)} bucket(s), none named "
                               f"'{args.bucket}' in this account",
                })
        except OssClientError as e2:
            print(f"[WARN] ListBuckets fallback degraded ({e2.category}): "
                  f"{e2}", file=sys.stderr)
            report["errors"].append(e2.to_dict())

    # Step 3.5: endpoint self-correction. Measured: GetBucketInfo can
    # succeed against a wrong-region endpoint while the exposure queries
    # (GetBucketPolicy / GetBucketPublicAccessBlock / GetBucketReferer)
    # 403 there; rebuild the endpoint from the bucket's REAL location
    # before running the exposure audit so wrong --region input does not
    # poison the findings.
    if bucket_info:
        corrected = corrected_endpoint_from_location(bucket_info,
                                                     query_endpoint)
        if corrected != query_endpoint:
            auto_filled.append(
                f"query endpoint self-corrected to the bucket's real "
                f"location: {query_endpoint} -> {corrected} (the supplied "
                "--region was not the bucket's region)")
            query_endpoint = corrected
            report["query_endpoint"] = corrected

    # Step 4: exposure surface (policy / public-access block / referer),
    # each query independently degraded with [WARN].
    acl = bucket_info.get("acl", "") if bucket_info else ""
    policy_state = "unknown"
    policy_text = ""
    try:
        policy_text = _oss_client.get_bucket_policy(args.bucket,
                                                    query_endpoint)
        policy_state, evidence = policy_anonymous_open(policy_text)
    except OssClientError as e:
        if e.category == "not_configured":
            policy_state, evidence = "closed", (
                "no bucket policy configured on this bucket")
        else:
            policy_state, evidence = "unknown", str(e)
            print(f"[WARN] GetBucketPolicy degraded ({e.category}): {e}",
                  file=sys.stderr)
            report["errors"].append(e.to_dict())

    public_block = None
    try:
        public_block = _oss_client.get_bucket_public_access_block(
            args.bucket, query_endpoint)
    except OssClientError as e:
        if e.category == "not_configured":
            public_block = False
        else:
            print(f"[WARN] GetBucketPublicAccessBlock degraded "
                  f"({e.category}): {e}", file=sys.stderr)
            report["errors"].append(e.to_dict())

    referer_cfg = None
    try:
        referer_cfg = _oss_client.get_bucket_referer(args.bucket,
                                                     query_endpoint)
    except OssClientError as e:
        print(f"[WARN] GetBucketReferer degraded ({e.category}): {e}",
              file=sys.stderr)
        report["errors"].append(e.to_dict())

    # GetBucketRequestPayment: a payer=Requester bucket rejects anonymous
    # requests with EC 0003-00000701, so a nominal public-read ACL is not
    # actually anonymously readable. Without this query the audit reports
    # the nominal configuration and over-rates the effective exposure.
    payer = None
    try:
        payer = _oss_client.get_bucket_request_payment(args.bucket,
                                                       query_endpoint)
    except OssClientError as e:
        if e.category == "not_configured":
            payer = "BucketOwner"
        else:
            print(f"[WARN] GetBucketRequestPayment degraded ({e.category}): "
                  f"{e}", file=sys.stderr)
            report["errors"].append(e.to_dict())

    acl_grade = classify_acl(acl) if bucket_info else "unknown"
    payer_state = classify_payer(payer)
    verdict = exposure_verdict(acl_grade, policy_state, public_block,
                               referer_cfg, payer_state)
    report["exposure"] = {
        "bucket_info": bucket_info,
        "acl_grade": acl_grade,
        "policy_state": policy_state,
        "policy_anonymous_evidence": evidence,
        "public_access_block_enabled": public_block,
        "referer": referer_cfg,
        "request_payer": payer,
        "payer_state": payer_state,
        "verdict": verdict,
    }

    # Step 5: real-time-log evidence. The query sequence is generated
    # locally AND executed read-only against the customer's OWN log project
    # (oss-log-<owner-uid>-<regionId> / oss-log-store) so the report carries
    # findings, not just statements to paste.
    # F-1 fix: the SLS project name is anchored on the bucket OWNER UID
    # (GetBucketInfo owner_id, data-plane credential) instead of the CLI
    # identity UID, so a cross-account identity-chain skew can never point
    # the toolkit at the wrong account's project.
    bucket_region = (region_from_location(bucket_info["location"])
                     if bucket_info and bucket_info.get("location") else "")
    report["bucket_region"] = bucket_region
    owner_id = str((bucket_info or {}).get("owner_id") or "")
    project_uid, uid_mismatch = pick_project_uid(uid, owner_id)
    if uid_mismatch:
        print(f"[WARN] identity consistency: caller UID {uid} (aliyun CLI "
              f"default profile) differs from the bucket owner UID "
              f"{owner_id} (GetBucketInfo via the data-plane credential); "
              f"bucket attribution and the SLS project name are derived "
              f"from the bucket owner. Align the identity chain with the "
              f"data plane (e.g. lock ALIBABA_CLOUD_PROFILE) to remove "
              f"this skew.",
              file=sys.stderr)
        auto_filled.append(
            f"SLS project UID taken from GetBucketInfo owner_id "
            f"({owner_id}) because the CLI identity UID ({uid}) points at "
            f"a different account")
    assets = sls_asset_names(project_uid, bucket_region)
    queries = build_sls_queries(args.bucket)

    log_execution = None
    skip_reason = ""
    if args.no_log_execution:
        skip_reason = ("real-time-log execution was disabled with "
                       "--no-log-execution, so only the query sequence is "
                       "emitted for the user to run in the SLS console")
    elif not assets.get("complete"):
        skip_reason = (
            "the real-time-log project name could not be derived (it needs "
            "both the bucket owner UID and the bucket region), so no query "
            "was executed")
        print(f"[WARN] real-time-log execution skipped: {skip_reason}",
              file=sys.stderr)
    else:
        window = _sls_query.resolve_window(args.time_window, int(time.time()),
                                           args.log_days)
        auto_filled.append(
            f"real-time-log window resolved to {window['description']} "
            f"(window source: {window['window_source']}; --log-days "
            f"{args.log_days} applies only when --time-window carries no "
            f"day/hour count)")
        log_execution = _sls_query.execute_query_plan(
            queries, assets["project"], assets["logstore"], bucket_region,
            window)
        if log_execution.get("outcome") != "ok":
            # Additive degradation: this leg never enters report["errors"],
            # so it can never turn a successful exposure audit into FAIL.
            print(f"[WARN] real-time-log execution degraded "
                  f"({log_execution.get('outcome')}): "
                  f"{log_execution.get('note')}", file=sys.stderr)

    report["realtime_log"] = {
        "channel": "customer-side OSS real-time log query (SLS)",
        "sls_query_api_called": bool(log_execution
                                     and log_execution.get("executed")),
        "read_only_apis_used": ["sls GetHistograms", "sls GetLogs"]
        if log_execution and log_execution.get("executed") else [],
        "sls_project": assets["project"],
        "sls_logstore": assets["logstore"],
        "availability_note": assets["note"],
        "field_schema_source": "official OSS real-time-log field "
                               "documentation (help.aliyun.com); every field "
                               "and SQL function used below was executed "
                               "against a real oss-log-store logstore",
        "queries": queries,
        "execution": log_execution,
        "execution_skipped_reason": skip_reason,
        "usage_note": "The statements above were executed against the "
                      "dedicated project/logstore when the real-time log is "
                      "enabled; they are also valid to paste into the SLS "
                      "console for a different window. The OSS real-time log "
                      "is free but keeps only a rolling "
                      f"{_sls_query.MAX_LOG_DAYS} days and is NOT retroactive "
                      "-- it records requests from the moment it is enabled. "
                      f"A single scan covers at most "
                      f"{_sls_query.LOG_SCAN_CAP} entries, so split the "
                      "window into sub-ranges and merge locally above that.",
    }
    report["log_evidence"] = _log_evidence.summarize_log_evidence(
        log_execution if log_execution is not None
        else {"outcome": "not_executed", "executed": False,
              "note": skip_reason, "results": []},
        effectively_public=bool(verdict.get("effectively_public")))

    # Step 6: root-cause routing + containment checklist. The router is
    # verdict-aware: branches that the measured configuration already rules
    # out (Block Public Access, Requester Pays) are pushed to the end and
    # labelled ruled_out_by_config, so the first candidate is the one the
    # evidence actually supports.
    causes = route_root_causes(acl_grade, policy_state, verdict)
    report["root_cause_candidates"] = causes
    latent_public_grant = bool(verdict.get("nominal_public")
                               and verdict.get("neutralizers"))
    report["containment"] = containment_plan(
        [c["id"] for c in causes[:2]], latent_public_grant=latent_public_grant)

    # Fill the Deny template with the ranges the executed log evidence
    # actually identified. Private addresses are never blockable: they are
    # the owner's own intranet traffic, and a Deny on them would break the
    # legitimate workload.
    block_cidrs = []
    log_ips = ((report["log_evidence"] or {}).get("steps", {})
               .get("ip_concentration", {}))
    top_ip = str(log_ips.get("top_by_bytes") or "")
    if top_ip and not _log_evidence.is_private_ip(top_ip) \
            and log_ips.get("verdict") == "concentrated":
        block_cidrs.append(top_ip)
    report["containment_policy_template"] = deny_ip_policy_template(
        args.bucket, block_cidrs)
    if block_cidrs:
        auto_filled.append(
            f"containment Deny statement pre-filled with {', '.join(block_cidrs)} "
            "from the bytes-ranked Top-client-IP log result (step 2b); verify "
            "it is not a legitimate client before applying")

    # Step 7: status + next action.
    if bucket_info:
        # Contract: ANY recorded error degrades the run -- a partial audit
        # must never report STATUS: OK (measured wrong-region scenario:
        # exposure queries 403'ing while the report claimed OK).
        if report["errors"]:
            failed = sorted({str(err.get("code") or err.get("category")
                                 or "unknown") for err in report["errors"]})
            next_action = (
                f"Exposure level: {verdict['level']}, but the audit is "
                f"DEGRADED -- these checks failed: {', '.join(failed)} "
                "(see 'errors'). The findings reflect only the checks that "
                "succeeded; resolve the recorded errors (permission / "
                "region / network) and re-run before acting on this "
                "report. The SLS query toolkit remains usable meanwhile.")
            sys.exit(_emit(report, "DEGRADED", next_action, question))
        top_cause = causes[0]
        log_ev = report["log_evidence"] or {}
        if log_ev.get("conclusion") not in (None, "", "not_executed"):
            next_action = (
                f"Exposure level: {verdict['level']}. The real-time log WAS "
                f"queried and the evidence points at "
                f"'{log_ev['conclusion']}' (severity "
                f"{log_ev.get('severity')}): {log_ev.get('statement')} "
                f"This measured conclusion outranks the configuration-based "
                f"ranking in 'root_cause_candidates' (whose first candidate "
                f"is '{top_cause['id']}'); use the log evidence as the "
                "primary basis and the candidate list only as the fallback "
                "for windows the log does not cover. Apply the containment "
                "checklist manually -- this skill never changes "
                "configuration.")
            if log_ev.get("benign_possible"):
                next_action += (
                    " The evidence does NOT establish an attack, so say that "
                    "plainly to the customer instead of implying one; "
                    "over-diagnosing legitimate traffic as abuse is itself a "
                    "defect.")
        else:
            next_action = (
                f"Exposure level: {verdict['level']}. The real-time-log "
                f"queries were not executed ({log_ev.get('statement', '')[:160]}). "
                f"Run the statement sequence from the 'realtime_log' section "
                f"of this report against project "
                f"{assets['project'] or 'oss-log-<uid>-<region>'} logstore "
                f"{assets['logstore']} for the time window "
                f"'{args.time_window}' to confirm the primary candidate root "
                f"cause '{top_cause['id']}' ({top_cause['log_signature']}). "
                "Apply the containment checklist manually -- this skill never "
                "changes configuration.")
        if latent_public_grant:
            next_action += (
                f" Note: the bucket carries a public grant that is currently "
                f"neutralized by {', '.join(verdict['neutralizers'])}, so "
                f"anonymous access is NOT the leading candidate and the "
                f"first-ranked cause '{top_cause['id']}' is a credentialed "
                "or referer-bound branch. Turning the neutralizer off would "
                "restore anonymous exposure immediately -- remove the public "
                "grant itself rather than relying on the neutralizer. "
                "'containment_policy_template' holds a copyable Bucket "
                "Policy Deny skeleton for the abusive source IPs found by "
                "step 2.")
        sys.exit(_emit(report, "OK", next_action, question))

    # Degraded: no bucket info obtained -- attribute the root error.
    root = report["errors"][0] if report["errors"] else {"category": "unknown"}
    cat = root.get("category", "unknown")
    if cat == "not_found":
        next_action = (
            f"Bucket '{args.bucket}' was not found (NoSuchBucket); verify "
            "the bucket name spelling and the owning account, then re-run.")
    elif cat == "permission":
        next_action = (
            "Access denied (403): grant the caller the read-only actions "
            "listed in references/ram-policies.md (oss:GetBucketInfo, "
            "oss:GetBucketPolicy, oss:GetBucketPublicAccessBlock, "
            "oss:GetBucketReferer, oss:GetBucketRequestPayment, "
            "oss:ListBuckets) or confirm the bucket "
            "belongs to this account, then re-run. Meanwhile the SLS query "
            "toolkit in this report remains usable with the real-time-log "
            "console.")
    elif cat == "endpoint":
        next_action = (
            "The request hit the wrong region's endpoint; re-run with "
            "--region set to the region where the bucket was created.")
    elif cat == "network":
        next_action = (
            "Network/DNS failure reaching the endpoint host: verify DNS "
            "resolution and local network, then re-run.")
    elif cat == "credentials":
        next_action = (
            "No credentials in the environment credential chain; configure "
            "the default credential chain (aliyun configure / environment "
            "variables), never pass AK/SK manually.")
    else:
        next_action = (
            "OSS control-plane query failed; review the recorded errors and "
            "re-run after fixing the root cause. The SLS query toolkit in "
            "this report is still valid for manual real-time-log analysis.")
    sys.exit(_emit(report, "DEGRADED", next_action, question))


if __name__ == "__main__":
    sys.exit(main())
