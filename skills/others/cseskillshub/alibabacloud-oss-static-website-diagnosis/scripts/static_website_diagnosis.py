#!/usr/bin/env python3
"""
static_website_diagnosis.py -- OSS static website hosting diagnosis entry
==========================================================================
SECURITY: STRICTLY READ-ONLY. This script only issues the metadata queries
GetBucketInfo / GetBucketWebsite / ListBucketCname through the shared client
layer (scripts/_oss_client.py) plus ONE anonymous, credential-free HTTPS GET
against the bucket's default domain. It NEVER calls any mutating API
(PutBucketWebsite, DeleteBucketWebsite, PutBucketPolicy, ACL changes ...).
Credentials come exclusively from the default credential chain environment
variables; AK/SK/STS tokens are never read, printed, or passed explicitly.

Dual-audience output:
  - Default (human-readable): a sectioned report ending with the contract
    lines `STATUS: OK | DEGRADED` and `NEXT_ACTION: <action>`.
  - --json (for Agents): the full structured report as JSON; the contract
    lines are still printed afterwards for grep-ability.

Diagnosis questions answered:
  1. Is static website hosting configured on the bucket (IndexDocument /
     ErrorDocument / routing rules)?        -> GetBucketWebsite
  2. Why does opening the site download the file / not render the page?
     (default-domain browser download policy, private ACL blocking anonymous
      access, missing custom domain)        -> GetBucketInfo + anonymous probe
  3. Is a custom domain bound, and what are the domain filing (ICP)
     requirements for mainland China regions?  -> ListBucketCname + knowledge

Usage:
  python3 static_website_diagnosis.py --bucket <name> [--endpoint <ep>] \
      [--region <region>] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys

import _oss_client
import _doc_lookup

_SKILL = "alibabacloud-oss-static-website-diagnosis"
_DEFAULT_QUERY_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"
# Mainland China regions require the custom domain to hold an ICP filing
# before it can be bound to an OSS bucket / used for website serving.
#
# Official rule (access-buckets-via-custom-domain-names:12 +
# document_detail/2248436.html:7,10):
#   - Bucket located in mainland China -> ICP filing REQUIRED
#   - Bucket located outside mainland China (e.g. cn-hongkong, ap-*) -> NOT required
#   - Regionless-attribute bucket (oss-rg-china-mainland): data is stored in
#     mainland China -> ICP filing REQUIRED
#   - oss-cn-hongkong: NOT mainland China (official cross-border designation)
#
# Implementation (B-2/B-3/H-3 fix, 2026-09-03): explicit whitelist markers,
# NEVER a bare ^oss-cn- prefix regex (it false-positives on oss-cn-hongkong and
# false-negatives on oss-rg-china-mainland). H-3: the classification rule below
# is the SINGLE AUTHORITATIVE ICP-region rule for the access-entry skill group
# and is kept identical to direct-access-link
# oss_direct_access_diagnosis.icp_filing_required() (same markers, same order,
# same unknown -> True conservatism, same self-test set). Do NOT let the two
# implementations drift apart.

_WARN_COUNT = 0


def warn(category: str, message: str) -> None:
    """Record a degraded step: [WARN] <category>: <message> on stderr."""
    global _WARN_COUNT
    _WARN_COUNT += 1
    print(f"[WARN] {category}: {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Pure helpers (with inline boundary assertions -- three-layer acceptance)
# ---------------------------------------------------------------------------

def classify_endpoint(endpoint: str) -> str:
    """Classify an OSS endpoint string.

    Returns one of: public | internal | accelerate | invalid.
    """
    ep = (endpoint or "").strip().lower()
    ep = re.sub(r"^https?://", "", ep).strip("/")
    if not re.fullmatch(r"[a-z0-9.-]+", ep) or not ep.endswith(".aliyuncs.com"):
        return "invalid"
    host = ep[: -len(".aliyuncs.com")]
    if host.endswith("-internal"):
        return "internal"
    if re.fullmatch(r"(.*\.)?oss-accelerate(-overseas)?", host):
        return "accelerate"
    if re.fullmatch(r"(.*\.)?oss-[a-z0-9-]+", host):
        return "public"
    return "invalid"


def derive_query_endpoint(endpoint: str, region: str) -> tuple:
    """Resolve the query endpoint from --endpoint / --region.

    Returns (endpoint, defaulted: bool, reason: str).
    """
    if endpoint and endpoint.strip():
        ep = endpoint.strip()
        if classify_endpoint(ep) == "invalid":
            return _DEFAULT_QUERY_ENDPOINT, True, (
                f"provided --endpoint '{ep}' is not a valid OSS endpoint; "
                f"auto-defaulted to {_DEFAULT_QUERY_ENDPOINT}")
        return ep, False, ""
    if region and region.strip():
        r = region.strip().lower().removeprefix("oss-")
        return f"oss-{r}.aliyuncs.com", True, (
            f"query endpoint derived from --region {region} "
            f"(no --endpoint provided)")
    return _DEFAULT_QUERY_ENDPOINT, True, (
        f"query endpoint auto-defaulted to {_DEFAULT_QUERY_ENDPOINT} "
        "(no --endpoint/--region provided)")


def derive_default_domain(bucket: str, location: str) -> str:
    """Build the bucket's default (extranet) domain host from its location.

    location is shaped like 'oss-cn-hangzhou'; returns '' when location is
    empty or malformed.
    """
    loc = (location or "").strip().lower()
    if not re.fullmatch(r"oss-[a-z0-9-]+", loc):
        return ""
    return f"{bucket}.{loc}.aliyuncs.com"


def is_mainland_region(location: str) -> bool:
    """True when the bucket location is a mainland China region (ICP filing
    required for any custom domain bound to the bucket).

    H-3: SINGLE AUTHORITATIVE ICP-region rule for the access-entry skill
    group; kept identical to direct-access-link
    oss_direct_access_diagnosis.icp_filing_required(). Official sources:
    access-buckets-via-custom-domain-names:12 + document_detail/2248436.html:7,10
    + regions-and-endpoints:67.
    """
    s = (location or "").strip().lower()
    if not s:
        return True  # unknown location -> conservative guidance (H-3)
    # Explicit non-mainland: cn-hongkong is officially outside mainland China
    non_mainland = ("cn-hongkong",)
    if any(s.startswith(m) or m in s for m in non_mainland):
        return False
    # Explicit mainland: regionless-attribute buckets (data stored in mainland)
    regionless_mainland = ("oss-rg-china-mainland", "rg-china-mainland")
    if s in regionless_mainland:
        return True
    # Standard mainland markers
    mainland_markers = ("cn-", "oss-cn")
    return any(m in s for m in mainland_markers)


def _selftest() -> None:
    """Inline boundary assertions for the pure helpers (normal / boundary /
    illegal inputs). Run with --selftest; also safe to import."""
    assert classify_endpoint("oss-cn-hangzhou.aliyuncs.com") == "public"
    assert classify_endpoint("https://oss-cn-shanghai-internal.aliyuncs.com") \
        == "internal"
    assert classify_endpoint("oss-accelerate.aliyuncs.com") == "accelerate"
    assert classify_endpoint("oss-accelerate-overseas.aliyuncs.com") == \
        "accelerate"
    assert classify_endpoint("") == "invalid"
    assert classify_endpoint("example.com") == "invalid"
    assert classify_endpoint("oss-cn-hangzhou.aliyuncs.com.evil.example") == \
        "invalid"

    ep, defaulted, reason = derive_query_endpoint(
        "oss-cn-shanghai.aliyuncs.com", "")
    assert ep == "oss-cn-shanghai.aliyuncs.com" and not defaulted
    ep, defaulted, _ = derive_query_endpoint("", "cn-beijing")
    assert ep == "oss-cn-beijing.aliyuncs.com" and defaulted
    ep, defaulted, _ = derive_query_endpoint("", "")
    assert ep == _DEFAULT_QUERY_ENDPOINT and defaulted
    ep, defaulted, reason = derive_query_endpoint("not-an-endpoint", "")
    assert ep == _DEFAULT_QUERY_ENDPOINT and defaulted and "not a valid" in \
        reason

    assert derive_default_domain("bkt", "oss-cn-hangzhou") == \
        "bkt.oss-cn-hangzhou.aliyuncs.com"
    assert derive_default_domain("bkt", "") == ""
    assert derive_default_domain("bkt", "weird//loc") == ""

    assert is_mainland_region("oss-cn-hangzhou") is True
    assert is_mainland_region("oss-cn-hangzhou-finance") is True
    assert is_mainland_region("oss-cn-shanghai") is True
    assert is_mainland_region("oss-cn-wuhan-lr") is True   # G-3: local region
    assert is_mainland_region("oss-cn-zhongwei") is True    # G-3: local region
    assert is_mainland_region("oss-cn-fuzhou") is True     # G-3: local region
    # B-3 fix: oss-cn-hongkong is NOT mainland China (official cross-border)
    assert is_mainland_region("oss-cn-hongkong") is False, \
        "B-3: oss-cn-hongkong must NOT be classified as mainland China"
    # B-2 fix: regionless-attribute bucket data is stored in mainland China
    assert is_mainland_region("oss-rg-china-mainland") is True, \
        "B-2: oss-rg-china-mainland must be classified as mainland China"
    assert is_mainland_region("rg-china-mainland") is True, \
        "B-2: rg-china-mainland (short form) must be classified as mainland"
    assert is_mainland_region("oss-ap-southeast-1") is False
    assert is_mainland_region("oss-us-west-1") is False
    # H-3 alignment with direct-access icp_filing_required(): short region form
    assert is_mainland_region("cn-hangzhou") is True
    assert is_mainland_region("cn-hongkong") is False
    # H-3: unknown/empty location -> conservative True (treat as mainland)
    assert is_mainland_region("") is True, \
        "H-3: unknown location must be conservative (treat as mainland)"
    print("SELFTEST: PASS")


# ---------------------------------------------------------------------------
# Diagnosis steps (each degrades independently with [WARN])
# ---------------------------------------------------------------------------

def step_identity(report: dict) -> None:
    try:
        identity = _oss_client.get_caller_identity()
        uid = str(identity.get("AccountId") or "").strip()
        report["uid"] = uid
        if not uid:
            warn("identity", "get-caller-identity returned no AccountId; "
                 "UID unavailable (traceability only)")
    except _oss_client.CliError as e:
        warn("identity", f"identity pre-check failed: {e}")
        report["uid"] = ""


def step_bucket_info(bucket: str, endpoint: str, report: dict) -> bool:
    """GetBucketInfo: location / ACL / extranet domain. Returns success."""
    try:
        info = _oss_client.get_bucket_info(bucket, endpoint)
        report["bucket_info"] = info
        return True
    except _oss_client.OssClientError as e:
        warn("get_bucket_info", f"{e}")
        report["errors"].append(e.to_dict())
        report["bucket_info"] = None
        return False


def step_bucket_website(bucket: str, endpoint: str, report: dict) -> str:
    """GetBucketWebsite: returns 'configured' | 'not_configured' | 'failed'."""
    try:
        ws = _oss_client.get_bucket_website(bucket, endpoint)
        report["website"] = ws
        return "configured"
    except _oss_client.OssClientError as e:
        if e.category == "not_configured":
            # Legitimate finding, not a failure: hosting simply not enabled.
            report["website"] = {
                "configured": False, "index_file": "", "error_file": "",
                "routing_rules": [],
                "evidence": {"code": e.code, "status": e.status,
                             "message": str(e)},
            }
            return "not_configured"
        warn("get_bucket_website", f"{e}")
        report["errors"].append(e.to_dict())
        report["website"] = None
        return "failed"


def step_cname(bucket: str, endpoint: str, report: dict) -> bool:
    try:
        cn = _oss_client.list_bucket_cname(bucket, endpoint)
        report["cnames"] = cn
        return True
    except _oss_client.OssClientError as e:
        warn("list_bucket_cname", f"{e}")
        report["errors"].append(e.to_dict())
        report["cnames"] = None
        return False


def step_probe(bucket: str, location: str, report: dict) -> None:
    """Anonymous GET on the default domain -- never raises, never needs
    credentials; evidence of what a visitor's browser actually receives."""
    probe = _oss_client.probe_default_domain(bucket, location)
    report["default_domain_probe"] = probe
    if probe.get("category") == "network":
        warn("default_domain_probe", probe.get("error", "probe failed"))


# ---------------------------------------------------------------------------
# Verdict & recommendations (knowledge + evidence attribution)
# ---------------------------------------------------------------------------

def build_verdict(report: dict) -> dict:
    """Attribute the symptom to concrete causes based on evidence + fixed
    OSS knowledge. Pure combination logic over report fields."""
    info = report.get("bucket_info")
    website = report.get("website")
    cnames = report.get("cnames")
    probe = report.get("default_domain_probe") or {}

    causes = []          # evidence-based root causes
    knowledge = []       # fixed OSS policy knowledge relevant to the symptom
    recommendations = []

    hosting_state = "unknown"
    if website is not None:
        hosting_state = "configured" if website.get("configured") else \
            "not_configured"

    if hosting_state == "not_configured":
        causes.append(
            "static website hosting is NOT configured on this bucket "
            "(GetBucketWebsite -> 404 NoSuchWebsiteConfiguration): the "
            "IndexDocument / ErrorDocument rules do not exist, so OSS treats "
            "every request as a plain object download")
        recommendations.append(
            "Enable static website hosting in the OSS console (Data "
            "Management -> Static Pages): set the default homepage (e.g. "
            "index.html) and optionally the 404 page. This is the "
            "PutBucketWebsite configuration -- a WRITE operation this "
            "read-only skill cannot and will not execute; perform it "
            "manually, then re-run this diagnosis.")

    if hosting_state == "configured":
        idx = website.get("index_file", "")
        err = website.get("error_file", "")
        if idx:
            recommendations.append(
                f"Homepage rule (IndexDocument) is '{idx}': make sure the "
                f"object '{idx}' actually exists at the bucket root and its "
                "Content-Type is text/html, otherwise the homepage rule "
                "matches nothing and the page appears blank or downloads.")
        else:
            causes.append(
                "hosting is configured but the homepage rule (IndexDocument) "
                "is EMPTY -- visitors hitting the root path get no default "
                "page")
        if not err:
            knowledge.append(
                "No 404 page rule (ErrorDocument) is set: OSS returns the "
                "raw XML error body on missing pages; setting a custom 404 "
                "page is recommended.")

    acl = (info or {}).get("acl", "") if info else ""
    if acl == "private" and probe.get("status") == 403:
        causes.append(
            "the bucket ACL is 'private' and the anonymous default-domain "
            "probe returned HTTP 403 AccessDenied ('Anonymous user has no "
            "right to access this bucket'): browsers cannot read any object, "
            "so the site cannot open at all")
        recommendations.append(
            "Static website serving requires anonymous read access: set the "
            "bucket ACL to public-read, or keep the bucket private and grant "
            "read via a bucket policy for the site prefix. These are WRITE "
            "operations -- manual guidance only, this skill never applies "
            "them.")

    cname_count = (cnames or {}).get("count", 0) if cnames is not None else \
        None
    if cname_count == 0:
        knowledge.append(
            "No custom domain (CNAME) is bound to this bucket (ListBucketCname "
            "returned 0). Browser access through the DEFAULT domain "
            "(<bucket>.<region>.aliyuncs.com) is subject to the OSS "
            "default-domain policy: the browser is forced to DOWNLOAD the "
            "object instead of rendering it (Content-Disposition: "
            "attachment). To render HTML pages in the browser you must bind "
            "a custom domain via CNAME (console: Bucket Settings -> Domain "
            "Names, a WRITE operation you perform manually).")
    elif cname_count:
        domains = ", ".join(c.get("domain", "") for c in
                            (cnames or {}).get("cnames", []))
        knowledge.append(
            f"Custom domain(s) bound: {domains}. If the page still downloads "
            "instead of rendering, open the site through the custom domain "
            "(not the default domain) and check the domain's DNS CNAME "
            "record points at the OSS extranet endpoint.")

    if info and is_mainland_region(info.get("location", "")):
        knowledge.append(
            "This bucket is in a MAINLAND CHINA region: any custom domain "
            "bound for website serving must hold a valid ICP filing, "
            "otherwise the binding / serving is rejected. For regions "
            "outside mainland China (e.g. oss-ap-southeast-1) no ICP filing "
            "is required.")
    elif info:
        knowledge.append(
            "This bucket is NOT in a mainland China region, so ICP filing "
            "is not required for its custom domain.")

    # Default-domain download policy always applies to default-domain access.
    knowledge.append(
        "OSS default-domain policy (EC 0048-00000001): for a Bucket created "
        "after 2017-10-01 00:00 (Beijing time), when a BROWSER opens an "
        "object via the default domain (<bucket>.<region>.aliyuncs.com) and "
        "the name ends in .htm/.html or the Content-Type is text/html, OSS "
        "injects x-oss-force-download: true + Content-Disposition: "
        "attachment, so the page is downloaded rather than rendered in "
        "place. This is exactly why 'the static website opens as a "
        "download'. Direct API/SDK/curl access is not affected. (The "
        "2019-09 cutoff belongs to the separate image MIME family "
        "0048-00000100~105, not the HTML family.)")

    if probe.get("status") == 200 and \
            "text/html" in (probe.get("content_type") or ""):
        recommendations.append(
            "The anonymous default-domain probe returned HTTP 200 with "
            "text/html, so the homepage itself is readable; the remaining "
            "symptom (download instead of render) is explained by the "
            "default-domain browser policy -- use a bound custom domain.")

    verdict = {
        "hosting_state": hosting_state,
        "acl": acl,
        "cname_count": cname_count,
        "probe_status": probe.get("status", 0),
        "causes": causes,
        "knowledge": knowledge,
        "recommendations": recommendations,
    }
    report["verdict"] = verdict
    return verdict


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def render_human(report: dict) -> None:
    v = report["verdict"]
    print("=" * 64)
    print("OSS Static Website Hosting Diagnosis")
    print("=" * 64)
    print(f"  Bucket          : {report['bucket']}")
    print(f"  Query endpoint  : {report['query_endpoint']}"
          + (" (auto-filled)" if report["endpoint_defaulted"] else ""))
    if report["endpoint_default_reason"]:
        print(f"    auto-fill note: {report['endpoint_default_reason']}")
    print(f"  Account UID     : {report['uid'] or '(unavailable, degraded)'}")

    info = report.get("bucket_info")
    if info:
        print("\n[Bucket]")
        print(f"  Location        : {info.get('location', '')}")
        print(f"  ACL             : {info.get('acl', '')}")
        print(f"  Extranet domain : {info.get('extranet_endpoint', '')}")

    ws = report.get("website")
    print("\n[Static Website Hosting (GetBucketWebsite)]")
    if ws is None:
        print("  unavailable (query failed -- see errors)")
    elif ws.get("configured"):
        print(f"  Hosting         : CONFIGURED")
        print(f"  IndexDocument   : {ws.get('index_file', '') or '(empty)'}")
        print(f"  ErrorDocument   : {ws.get('error_file', '') or '(not set)'}")
        rules = ws.get("routing_rules") or []
        print(f"  Routing rules   : {len(rules)}")
    else:
        ev = ws.get("evidence") or {}
        print("  Hosting         : NOT CONFIGURED")
        print(f"  Evidence        : {ev.get('code', '')} "
              f"(HTTP {ev.get('status', '')})")

    cn = report.get("cnames")
    print("\n[Custom Domains (ListBucketCname)]")
    if cn is None:
        print("  unavailable (query failed -- see errors)")
    else:
        print(f"  Bound count     : {cn.get('count', 0)}")
        for c in cn.get("cnames", []):
            print(f"    - {c.get('domain', '')} "
                  f"{('(' + c.get('status') + ')') if c.get('status') else ''}")

    probe = report.get("default_domain_probe") or {}
    print("\n[Anonymous Default-Domain Probe (no credentials)]")
    if not probe.get("executed"):
        print(f"  skipped         : {probe.get('error', 'unknown reason')}")
    else:
        print(f"  URL             : {probe.get('url', '')}")
        print(f"  HTTP status     : {probe.get('status', 0)}")
        if probe.get("content_type"):
            print(f"  Content-Type    : {probe['content_type']}")
        if probe.get("content_disposition"):
            print(f"  Content-Disposition: {probe['content_disposition']}")
        if probe.get("error_code"):
            print(f"  OSS error code  : {probe['error_code']}")

    print("\n[Findings]")
    if v["causes"]:
        for i, c in enumerate(v["causes"], 1):
            print(f"  Cause {i}: {c}")
    else:
        print("  No configuration defect detected by the control-plane "
              "checks.")
    for i, k in enumerate(v["knowledge"], 1):
        print(f"  Knowledge {i}: {k}")
    print("\n[Recommendations]")
    for i, r in enumerate(v["recommendations"], 1):
        print(f"  {i}. {r}")
    if report["errors"]:
        print("\n[Errors (degraded steps)]")
        for e in report["errors"]:
            print(f"  - [{e['category']}/{e['code']}] {e['message']}")
    dv = report.get("doc_verification")
    if dv:
        print("\n[Doc verification]")
        if dv.get("matched"):
            for doc in dv.get("docs", []):
                print(f"  - {doc['title']}: {doc['url']}")
        elif (dv.get("note") or "").startswith("DEGRADED"):
            print("  Doc verification: DEGRADED (offline) -- conclusions are "
                  "based on embedded knowledge only.")
        else:
            print("  No matching official doc entry.")


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only diagnosis of OSS static website hosting "
                    "(hosting config, render-vs-download attribution, "
                    "custom domain / ICP filing guidance)")
    parser.add_argument("--bucket", default="",
                             required=False,
                        help="OSS bucket name to diagnose")
    parser.add_argument("--endpoint", default="",
                        help="optional: the endpoint the user currently uses")
    parser.add_argument("--region", default="",
                        help="optional: expected region (derives the query "
                             "endpoint when --endpoint is absent)")
    parser.add_argument("--json", action="store_true",
                        help="emit the structured JSON report")
    parser.add_argument("--selftest", action="store_true",
                        help="run the pure-function boundary assertions only")
    parser.add_argument("--question", default="",
                        help="Customer's original wording (optional); when "
                             "provided, the report carries a doc_verification "
                             "section matched against official OSS docs")
    args = parser.parse_args()

    # Missing-bucket guard: a bare argparse exit 2 gives the customer no next
    # step, and most real tickets never name a bucket. Ask for it and list what
    # this credential can see.
    if not (args.bucket or "").strip():
        _hint = []
        try:
            _hint = [b["name"] for b in _oss_client.list_buckets()][:30]
        except Exception as e:
            print(f"[WARN] ListBuckets bucket-name hint degraded: {e}",
                  file=sys.stderr)
        _na = ("Ask the user which OSS bucket hosts the static website; "
               "buckets_in_account lists buckets visible to the current "
               "credential.")
        if not _hint:
            _na += (" No bucket is listable with the current credential: ask "
                    "for the exact bucket name and its region instead.")
        _rep = {"skill": "alibabacloud-oss-static-website-diagnosis",
                "bucket": "", "buckets_in_account": _hint,
                "errors": [], "auto_filled": []}
        if args.json:
            print(json.dumps(_rep, indent=2, ensure_ascii=False))
        else:
            print("No bucket name was supplied.")
            if _hint:
                print("Buckets visible to the current credential:")
                for _b in _hint:
                    print("  - " + _b)
        print(f"\nSTATUS: FAIL")
        print(f"NEXT_ACTION: {_na}")
        sys.exit(1)
    global _CUSTOMER_QUESTION
    _CUSTOMER_QUESTION = args.question or ""

    if args.selftest:
        _selftest()
        return

    report = {
        "skill": _SKILL,
        "bucket": args.bucket,
        "session_id": _oss_client.session_id(),
        "uid": "",
        "errors": [],
    }

    endpoint, defaulted, reason = derive_query_endpoint(args.endpoint,
                                                        args.region)
    report["query_endpoint"] = endpoint
    report["endpoint_defaulted"] = defaulted
    report["endpoint_default_reason"] = reason
    if defaulted:
        # Auto-fill declaration requirement (recorded in report metadata).
        print(f"[INFO] {reason}", file=sys.stderr)

    # Step 0: identity (traceability label; degrades on failure)
    step_identity(report)

    degraded = False

    # Step 1: bucket metadata (location / ACL). Hard dependency for the rest:
    # without location we cannot derive the default domain to probe.
    ok_info = step_bucket_info(args.bucket, endpoint, report)
    location = ""
    if ok_info and report["bucket_info"]:
        location = report["bucket_info"].get("location", "")
        # Self-heal endpoint: when the bucket lives in another region than
        # the query endpoint, re-run against the bucket's real region.
        real_ep = f"{location}.aliyuncs.com"
        if location and classify_endpoint(real_ep) == "public" and \
                real_ep != endpoint:
            warn("endpoint", f"bucket location {location} differs from query "
                 f"endpoint {endpoint}; re-querying with {real_ep}")
            endpoint = real_ep
            report["query_endpoint"] = real_ep
            report["endpoint_defaulted"] = True
            report["endpoint_default_reason"] = (
                f"query endpoint auto-corrected to {real_ep} based on the "
                "bucket's real location (GetBucketInfo)")
            ok_info = step_bucket_info(args.bucket, endpoint, report)
            if not ok_info:
                degraded = True
    else:
        degraded = True

    # Step 2: website hosting configuration (finding or error).
    if ok_info:
        ws_state = step_bucket_website(args.bucket, endpoint, report)
        if ws_state == "failed":
            degraded = True
    else:
        report["website"] = None

    # Step 3: bound custom domains (degrades independently).
    if ok_info:
        if not step_cname(args.bucket, endpoint, report):
            degraded = True

    # Step 4: anonymous default-domain probe (credential-free, best effort).
    if ok_info and location:
        step_probe(args.bucket, location, report)
    else:
        report["default_domain_probe"] = {
            "executed": False, "status": 0,
            "error": "skipped: bucket metadata unavailable, cannot derive "
                     "the default domain",
        }

    build_verdict(report)

    status = "DEGRADED" if degraded else "OK"
    report["status"] = status

    # NEXT_ACTION: single actionable line derived from the verdict.
    v = report["verdict"]
    if not ok_info and report["errors"]:
        e0 = report["errors"][0]
        if e0["category"] == "not_found":
            next_action = ("verify the bucket name spelling and the owning "
                           "account, then re-run this diagnosis")
        elif e0["category"] == "credentials":
            next_action = ("configure the default credential chain "
                           "(aliyun configure / environment variables) and "
                           "re-run; never pass AK/SK manually")
        elif e0["category"] == "permission":
            next_action = ("grant the read-only permissions listed in "
                           "references/ram-policies.md "
                           "(oss:GetBucketInfo, oss:GetBucketWebsite, "
                           "oss:ListBucketCname) and re-run")
        else:
            next_action = ("check the recorded errors, resolve the "
                           "connectivity issue and re-run this diagnosis")
    elif v["hosting_state"] == "not_configured":
        next_action = ("enable static website hosting in the OSS console "
                       "(set the default homepage, e.g. index.html -- manual "
                       "write operation), then re-run this diagnosis to "
                       "verify")
    elif v["acl"] == "private" and v["probe_status"] == 403:
        next_action = ("open the bucket for anonymous read (bucket ACL or "
                       "bucket policy -- manual write operation), or serve "
                       "the site behind a bound custom domain with proper "
                       "access rules")
    elif v["cname_count"] == 0:
        next_action = ("bind a custom domain via CNAME (ICP filing required "
                       "for mainland China regions -- manual operation), "
                       "then open the site through the custom domain instead "
                       "of the default domain")
    else:
        next_action = ("open the site through the bound custom domain; if "
                       "individual objects still misbehave, check their "
                       "Content-Type and the index/404 rules reported above")
    report["next_action"] = next_action

    dv = _doc_verification(status)
    if dv is not None:
        report["doc_verification"] = dv

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        # Contract lines stay on stdout, matching the majority convention
        # of the sibling OSS skills (21/22) and this script's own
        # docstring: the JSON report is printed first, then the
        # grep-able contract lines follow on stdout.
        print(f"\nSTATUS: {status}")
        print(f"NEXT_ACTION: {next_action}")
    else:
        render_human(report)
        print(f"\nSTATUS: {status}")
        print(f"NEXT_ACTION: {next_action}")
    sys.exit(0 if status in ("OK", "DEGRADED") else 1)


if __name__ == "__main__":
    main()
