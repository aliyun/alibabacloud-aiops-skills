#!/usr/bin/env python3
"""
oss_endpoint_diagnosis.py -- OSS endpoint / internal-network access diagnosis
==============================================================================
SECURITY: READ-ONLY. Only issues GetBucketInfo (+ ListBuckets fallback) to
the OSS control plane and GetCallerIdentity to STS. Never mutates anything.
Credentials come exclusively from the default credential chain (environment
variables for the OSS SDK, aliyun CLI default chain for STS); AK/SK are
never read, printed, or passed explicitly.

Diagnoses:
  * bucket region vs. user-configured endpoint matching (GetBucketInfo)
  * internal endpoint vs. public endpoint selection advice
  * attribution of unexpected public network traffic cost (endpoint choice)
  * routing of "no such host" / "must use specified endpoint" style errors

Output contract (04-spec): stdout carries a structured JSON report followed
by the machine-consumable lines:
    STATUS: OK | DEGRADED
    NEXT_ACTION: <one actionable sentence>

Usage:
  python3 oss_endpoint_diagnosis.py --bucket <name> \
      [--endpoint <user-configured-endpoint>] [--region <expected-region>]
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import tempfile

import _doc_lookup
import _oss_client
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

# CNAME / custom-domain troubleshooting path -- the runtime projection of
# references/endpoint-rules.md §3.3 (E1: closes the knowledge-script gap where
# the reference already carried this path but classify_endpoint had no `cname`
# kind and the script emitted only a generic "use a valid endpoint" reply).
# Each entry is one ordered check the Agent walks with the customer.
CNAME_TROUBLESHOOTING_PATH = [
    "1. CNAME record: at the DNS provider the custom domain must CNAME to the "
    "bucket's public endpoint (<bucket>.oss-<region>.aliyuncs.com); a domain "
    "that does not resolve reproduces the customer-side UnknownHostException / "
    "'no such host' symptom.",
    "2. Bucket binding: the custom domain must be bound on the bucket (OSS "
    "console > Bucket > Transmission Management > Domain Names, read-only "
    "ListCname); an unbound domain returns 403 / no bucket resolution even "
    "with a correct CNAME.",
    "3. HTTPS certificate: HTTPS on the custom domain needs an SSL certificate "
    "hosted by OSS for that domain; without it HTTPS fails while HTTP may work.",
    "4. Billing unchanged: a CNAME does not change billing -- cross-region / "
    "overseas clients still pay public-egress traffic and follow the same "
    "region rules.",
    "5. SDK CNAME mode: if the tool accepts only an 'endpoint' field, entering "
    "the custom domain works only when the SDK is in CNAME mode "
    "(is_cname=True / equivalent); otherwise the SDK rebuilds a bucket domain "
    "that bypasses the custom domain and the request misroutes.",
    "6. Dedicated CNAME domain: instead of pointing at the standard bucket "
    "endpoint, OSS offers a dedicated intermediate domain "
    "(<BucketName>.<Region>.<dedicated-suffix>) that serves only as the CNAME "
    "target, keeping resolution stable when the standard endpoint is anomalous "
    "or blocked (dedicated-cname-domain-best-practices).",
    "7. ICP filing: for buckets in mainland-China regions the custom domain "
    "must have completed ICP filing before it can be bound.",
]


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
assert normalize_endpoint("https://OSS-CN-Beijing-Internal.aliyuncs.com/") == "oss-cn-beijing-internal.aliyuncs.com"  # boundary: scheme+case+slash
assert normalize_endpoint("") == ""  # invalid: empty string
assert normalize_endpoint(None) == ""  # invalid: missing value


def _is_ip_literal(host: str) -> bool:
    """True for an IPv4/IPv6 literal. A raw IP is NEVER a valid OSS endpoint
    (endpoint-rules.md §3.2: OSS public IPs are shared, access must use the
    bucket domain), so it stays `invalid`, not a custom domain (CNAME)."""
    h = (host or "").strip().lower().strip("[]")
    if not h:
        return False
    if ":" in h:                       # IPv6 literal (possibly bracket-stripped)
        return True
    parts = h.split(".")
    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255
                               for p in parts):
        return True                    # IPv4 literal
    return False


assert _is_ip_literal("172.27.16.9") is True    # normal: IPv4
assert _is_ip_literal("::1") is True            # boundary: IPv6
assert _is_ip_literal("test234.pier39.cn") is False  # boundary: real domain, not an IP
assert _is_ip_literal("") is False              # invalid: empty
assert _is_ip_literal("999.1.1.1") is False     # invalid: out-of-range octet is not an IPv4 literal


def _is_domain_shape(host: str) -> bool:
    """True for a well-formed DNS domain name: >=2 labels, each 1-63 chars of
    [a-z0-9-] not leading/trailing a hyphen, and an alphabetic TLD >=2 chars.
    Used to tell a custom domain (CNAME) from a malformed endpoint fragment."""
    h = (host or "").strip().lower().rstrip(".")
    if h.count(".") < 1:
        return False                   # single label (e.g. 'localhost') is not a FQDN
    labels = h.split(".")
    for lab in labels:
        if not lab or len(lab) > 63:
            return False
        if lab.startswith("-") or lab.endswith("-"):
            return False
        if not all(c.isalnum() or c == "-" for c in lab):
            return False
    tld = labels[-1]
    if not tld.isalpha() or len(tld) < 2:
        return False                   # TLD must be alphabetic (rejects '.con'-style typos of numeric form)
    return True


assert _is_domain_shape("test234.pier39.cn") is True   # normal: custom domain
assert _is_domain_shape("a.b") is False                # boundary: single-char TLD rejected
assert _is_domain_shape("mysite.com") is True          # normal: two labels
assert _is_domain_shape("-bad.example.com") is False   # invalid: leading hyphen label
assert _is_domain_shape("localhost") is False          # invalid: single label
assert _is_domain_shape("") is False                   # invalid: empty


def classify_endpoint(endpoint: str) -> dict:
    """Classify an OSS endpoint string.

    Returns {"kind": public|internal|accelerate|dualstack|cname|invalid,
             "region": str|None}.
      public      -- oss-<region>.aliyuncs.com
      internal    -- oss-<region>-internal.aliyuncs.com
      accelerate  -- oss-accelerate[-overseas].aliyuncs.com (transfer accel)
      dualstack   -- <region>.oss.aliyuncs.com (IPv4+IPv6; only some regions)
      cname       -- a custom domain bound to a bucket (a well-formed FQDN
                     that is NOT an *.aliyuncs.com host and NOT a raw IP);
                     the domain inherits the bucket's region underneath, so
                     endpoint-region rules still apply (endpoint-rules.md §3.3)
      invalid     -- empty, a raw IP, an *.aliyuncs.com host that is malformed
                     (missing oss- prefix / typo'd TLD), or a non-FQDN fragment
    """
    ep = normalize_endpoint(endpoint)
    if not ep:
        return {"kind": "invalid", "region": None}
    if ep in ("oss-accelerate.aliyuncs.com",
              "oss-accelerate-overseas.aliyuncs.com"):
        return {"kind": "accelerate", "region": None}
    # Dual-stack endpoint: <region>.oss.aliyuncs.com (official regions-and-
    # endpoints table; note the reversed layout vs the public endpoint).
    if ep.endswith(".oss.aliyuncs.com"):
        region = ep[:-len(".oss.aliyuncs.com")]
        dparts = region.split("-")
        if (region and len(dparts) >= 2
                and all(p and p.isalnum() for p in dparts)
                and dparts[0].isalpha()):
            return {"kind": "dualstack", "region": region}
        return {"kind": "invalid", "region": None}
    if not ep.startswith("oss-") or not ep.endswith(".aliyuncs.com"):
        # Not a standard OSS endpoint. Distinguish a custom domain (CNAME)
        # from a genuine typo / raw IP so the diagnosis can route to the
        # custom-domain troubleshooting path instead of a generic "use a
        # valid endpoint" reply (E1 knowledge-script gap fix).
        if _is_ip_literal(ep):
            # Raw IP: never a valid OSS endpoint (§3.2), and not a custom domain.
            return {"kind": "invalid", "region": None}
        if "aliyuncs" in ep:
            # An attempted OSS endpoint that is malformed (missing oss- prefix,
            # typo'd TLD such as .aliyuncs.con, a bucket virtual-hosted domain):
            # stays invalid, NOT a custom domain.
            return {"kind": "invalid", "region": None}
        if _is_domain_shape(ep):
            return {"kind": "cname", "region": None}
        return {"kind": "invalid", "region": None}
    host = ep[len("oss-"):-len(".aliyuncs.com")]
    internal = False
    if host.endswith("-internal"):
        internal = True
        host = host[:-len("-internal")]
    # region shape: letters-led, hyphen-separated segments, e.g. cn-shanghai,
    # ap-southeast-1, us-east-1
    parts = host.split("-")
    if not host or any(not p for p in parts) or len(parts) < 2:
        return {"kind": "invalid", "region": None}
    if not all(p.isalnum() for p in parts):
        return {"kind": "invalid", "region": None}
    if not parts[0].isalpha():
        return {"kind": "invalid", "region": None}
    return {"kind": "internal" if internal else "public", "region": host}


assert classify_endpoint("oss-cn-shanghai.aliyuncs.com") == {"kind": "public", "region": "cn-shanghai"}  # normal: public
assert classify_endpoint("oss-cn-shanghai-internal.aliyuncs.com") == {"kind": "internal", "region": "cn-shanghai"}  # normal: internal suffix variant
assert classify_endpoint("HTTPS://oss-ap-southeast-1-internal.aliyuncs.com") == {"kind": "internal", "region": "ap-southeast-1"}  # boundary: scheme+case
assert classify_endpoint("oss-accelerate.aliyuncs.com") == {"kind": "accelerate", "region": None}  # boundary: accelerate form
assert classify_endpoint("cn-hangzhou.oss.aliyuncs.com") == {"kind": "dualstack", "region": "cn-hangzhou"}  # boundary: dual-stack form
assert classify_endpoint("HTTPS://cn-beijing.oss.aliyuncs.com/") == {"kind": "dualstack", "region": "cn-beijing"}  # boundary: dual-stack case/slash
assert classify_endpoint(".oss.aliyuncs.com") == {"kind": "invalid", "region": None}  # invalid: dual-stack with empty region
assert classify_endpoint("") == {"kind": "invalid", "region": None}  # invalid: empty
assert classify_endpoint("cn-shanghai.aliyuncs.com") == {"kind": "invalid", "region": None}  # invalid: missing oss- prefix (aliyuncs host)
assert classify_endpoint("oss-.aliyuncs.com") == {"kind": "invalid", "region": None}  # invalid: empty region
assert classify_endpoint("oss-cn-chengdu.aliyuncs.con") == {"kind": "invalid", "region": None}  # invalid: OSS endpoint TLD typo, NOT a custom domain
assert classify_endpoint("172.27.16.9") == {"kind": "invalid", "region": None}  # invalid: raw IP literal (§3.2, never a valid endpoint)
# --- E1 CNAME classification asserts (normal / boundary / invalid) ---
assert classify_endpoint("test234.pier39.cn") == {"kind": "cname", "region": None}  # normal: real custom domain (CNAME asset)
assert classify_endpoint("gxyckj-filestore.image.yuncreatekj.com") == {"kind": "cname", "region": None}  # normal: multi-label custom domain (ticket 000B9R8YDC)
assert classify_endpoint("HTTPS://actp.mama100.com/") == {"kind": "cname", "region": None}  # boundary: scheme+case+slash custom domain (ticket 000F4RK8E8)
assert classify_endpoint("example.com") == {"kind": "cname", "region": None}  # boundary: generic custom-domain shape
assert classify_endpoint("localhost") == {"kind": "invalid", "region": None}  # invalid: single label, not a FQDN
assert classify_endpoint("-bad.pier39.cn") == {"kind": "invalid", "region": None}  # invalid: leading-hyphen label


def region_from_location(location: str) -> str:
    """Convert a bucket location (e.g. 'oss-cn-shanghai') to its region."""
    loc = (location or "").strip().lower()
    if loc.startswith("oss-"):
        return loc[len("oss-"):]
    return loc


assert region_from_location("oss-cn-shanghai") == "cn-shanghai"  # normal
assert region_from_location("cn-hangzhou") == "cn-hangzhou"  # boundary: already a region
assert region_from_location("") == ""  # invalid: empty


def match_verdict(user_region, bucket_region) -> str:
    """Compare the region of the user's endpoint with the bucket location.

    Returns matched | mismatch | unknown (either side missing/unparseable,
    or accelerate endpoint which is region-less).
    """
    if not user_region or not bucket_region:
        return "unknown"
    return "matched" if user_region == bucket_region else "mismatch"


assert match_verdict("cn-shanghai", "cn-shanghai") == "matched"  # normal
assert match_verdict("cn-beijing", "cn-shanghai") == "mismatch"  # normal: wrong region
assert match_verdict(None, "cn-shanghai") == "unknown"  # boundary: accelerate/no region
assert match_verdict("cn-shanghai", "") == "unknown"  # invalid: missing location


def rebuild_query_endpoint(location: str, extranet_endpoint: str,
                           current_endpoint: str) -> tuple:
    """Re-derive the query endpoint from the bucket's real location (B-7).

    Official basis (help.aliyun.com/zh/oss/user-guide/regions-and-endpoints):
      1. The `extranet_endpoint`真值 returned by GetBucketInfo/ListBuckets is
         AUTHORITATIVE and always wins -- it is correct for every cloud
         including finance cloud.
      2. Only when that真值 is absent do we fall back to the
         `<location>.aliyuncs.com` template, which is VALID ONLY for ordinary
         public-cloud regions.
      3. Finance-cloud locations (cn-hangzhou-finance / cn-shanghai-finance-1 /
         cn-shenzhen-finance-1 / cn-beijing-finance-1) do NOT follow the
         template: e.g. cn-hangzhou-finance -> oss-cn-hzfinance.aliyuncs.com,
         cn-shenzhen-finance-1 -> oss-cn-szfinance.aliyuncs.com,
         cn-shanghai-finance-1 -> oss-cn-shanghai-finance-1-pub.aliyuncs.com.
         For these we REFUSE template derivation, keep the caller's endpoint,
         and return a degraded note pointing at the official finance table.

    Returns (endpoint, note); note is "" when there is nothing to report.
    """
    loc = (location or "").strip().lower()
    extranet = (extranet_endpoint or "").strip()
    cur = (current_endpoint or "").strip()
    if not loc.startswith("oss-"):
        return cur, ""  # invalid/non-oss location: leave the endpoint alone
    if extranet:
        if extranet != cur:
            return extranet, (
                "query endpoint taken from GetBucketInfo extranet_endpoint "
                "for location %s: %s" % (loc, extranet))
        return cur, ""
    if "finance" in loc:
        return cur, (
            "finance-cloud location %s does NOT follow the "
            "<location>.aliyuncs.com template and GetBucketInfo returned no "
            "extranet_endpoint; kept the caller's query endpoint -- consult "
            "the official regions-and-endpoints finance-cloud table for the "
            "correct Endpoint" % loc)
    ep = loc + ".aliyuncs.com"
    if ep != cur:
        return ep, (
            "query endpoint re-derived from bucket location %s: %s"
            % (loc, ep))
    return cur, ""


# B-7 inline assertions (normal / boundary / invalid)
assert rebuild_query_endpoint(
    "oss-cn-shanghai", "", "oss-cn-beijing.aliyuncs.com") == (
    "oss-cn-shanghai.aliyuncs.com",
    "query endpoint re-derived from bucket location oss-cn-shanghai: "
    "oss-cn-shanghai.aliyuncs.com")  # normal: ordinary-region template fallback
assert rebuild_query_endpoint(
    "oss-cn-hangzhou-finance", "oss-cn-hzfinance.aliyuncs.com", "x")[0] == \
    "oss-cn-hzfinance.aliyuncs.com"  # normal: extranet真值 wins for finance
_fr, _fn = rebuild_query_endpoint(
    "oss-cn-hangzhou-finance", "", "oss-cn-hangzhou.aliyuncs.com")
assert _fr == "oss-cn-hangzhou.aliyuncs.com" and "finance-cloud" in _fn, \
    "B-7: finance-cloud with no真值 must refuse template derivation"
assert rebuild_query_endpoint(
    "oss-cn-shanghai", "", "oss-cn-shanghai.aliyuncs.com")[0] == \
    "oss-cn-shanghai.aliyuncs.com"  # boundary: already correct, no change
assert rebuild_query_endpoint(
    "", "", "ep")[0] == "ep"  # invalid: empty location -> unchanged
assert rebuild_query_endpoint(
    "cn-shanghai", "", "ep")[0] == "ep"  # invalid: non-oss location -> unchanged


# Finance-cloud detection helper (N-3: aligned with rebuild_query_endpoint B-7)
_FINANCE_CLOUD_ENDPOINTS = {
    "oss-cn-hangzhou-finance": {
        "extranet": "oss-cn-hzfinance.aliyuncs.com",
        "intranet": "oss-cn-hzfinance-internal.aliyuncs.com",
    },
    "oss-cn-shenzhen-finance-1": {
        "extranet": "oss-cn-szfinance.aliyuncs.com",
        "intranet": "oss-cn-szfinance-internal.aliyuncs.com",
    },
    "oss-cn-shanghai-finance-1": {
        "extranet": "oss-cn-shanghai-finance-1-pub.aliyuncs.com",
        "intranet": "oss-cn-shanghai-finance-1-internal.aliyuncs.com",
    },
    "oss-cn-beijing-finance-1": {
        "extranet": "oss-cn-beijing-finance-1-pub.aliyuncs.com",
        "intranet": "oss-cn-beijing-finance-1-internal.aliyuncs.com",
    },
}


def _is_finance_location(location: str) -> bool:
    """Detect finance-cloud locations that do NOT follow the template."""
    return "finance" in (location or "").lower()


def _finance_endpoint_hint(location: str, kind: str) -> str:
    """Return the official finance-cloud endpoint or a guidance string."""
    loc = (location or "").strip().lower()
    known = _FINANCE_CLOUD_ENDPOINTS.get(loc)
    if known:
        return known.get(kind, "")
    return ("consult the official regions-and-endpoints finance-cloud table "
            "(help.aliyun.com/zh/oss/user-guide/regions-and-endpoints)")


def build_recommendation(bucket_info: dict, classified: dict,
                         verdict: str,
                         user_provided: bool = True) -> list:
    """Generate internal/public endpoint selection advice from evidence.

    user_provided distinguishes an explicitly supplied --endpoint from the
    auto-defaulted query endpoint, so the invalid-endpoint guidance is only
    emitted when the user's own input is malformed.

    N-3 fix: finance-cloud locations MUST NOT use the
    <location>.aliyuncs.com / <location>-internal.aliyuncs.com template;
    aligned with rebuild_query_endpoint (B-7, defa503).
    """
    recs = []
    location = bucket_info.get("location", "") if bucket_info else ""
    intranet = bucket_info.get("intranet_endpoint", "") if bucket_info else ""
    extranet = bucket_info.get("extranet_endpoint", "") if bucket_info else ""
    kind = classified.get("kind", "invalid") if classified else "invalid"

    if verdict == "mismatch" and location:
        # N-3: finance-cloud locations refuse template derivation
        if _is_finance_location(location) and not extranet:
            _hint = _finance_endpoint_hint(location, "extranet")
            recs.append(
                f"Region mismatch: the bucket's location is {location} "
                f"(finance cloud). Finance-cloud endpoints do NOT follow the "
                f"<location>.aliyuncs.com template. Official endpoint: {_hint}. "
                f"GetBucketInfo returned no extranet_endpoint -- consult the "
                f"official regions-and-endpoints finance-cloud table or the "
                f"OSS console for the correct Endpoint. "
                "OSS requires the endpoint of the region where the bucket was "
                "created ('must use specified endpoint')."
            )
        else:
            recs.append(
                f"Region mismatch: the bucket's location is {location}; rebuild "
                f"the endpoint from it -- public: {extranet or location + '.aliyuncs.com'}, "
                f"internal: {intranet or location + '-internal.aliyuncs.com'}. "
                "OSS requires the endpoint of the region where the bucket was "
                "created ('must use specified endpoint')."
            )
    if kind == "internal" and verdict == "matched":
        recs.append(
            "The internal endpoint is only resolvable from the Alibaba Cloud "
            "network of the same region (ECS/containers with classic or VPC "
            "access). From the Internet it fails DNS ('no such host') -- use "
            "the public endpoint outside the cloud."
        )
    if kind == "public" and verdict == "matched":
        recs.append(
            "Same-region clients running on Alibaba Cloud (e.g. ECS in "
            f"{classified.get('region')}) should switch to the internal "
            f"endpoint ({intranet or 'oss-<region>-internal.aliyuncs.com'}): "
            "internal traffic is free of public network traffic cost and has "
            "lower latency."
        )
        # batch2: billing --bucket-usage referral for per-bucket traffic attribution
        recs.append(
            "For per-bucket public-network traffic breakdown (which bucket "
            "generates the most outbound traffic cost), use the billing skill: "
            "alibabacloud-oss-billing-diagnosis --bucket-usage. It provides "
            "NetOut/CdnOut per-bucket attribution data that complements this "
            "endpoint-level diagnosis."
        )
    if kind == "accelerate":
        recs.append(
            "Transfer acceleration endpoints are for cross-region / "
            "cross-border optimization and are billed separately; for "
            "same-region internal access use the internal endpoint instead."
        )
    if kind == "dualstack":
        recs.append(
            "This is a dual-stack endpoint (<region>.oss.aliyuncs.com) "
            "serving IPv4 and IPv6 clients; per the official regions-and-"
            "endpoints table it exists only in some regions (most mainland-"
            "China regions; many overseas regions do not support it). It is "
            "a public-network path: same-region Alibaba Cloud clients "
            "should still prefer the internal endpoint for cost and latency."
        )
    if kind == "invalid" and user_provided:
        recs.append(
            "The provided endpoint is not a valid OSS endpoint. Valid forms: "
            "oss-<region>.aliyuncs.com (public), "
            "oss-<region>-internal.aliyuncs.com (internal), "
            "oss-accelerate.aliyuncs.com (transfer acceleration). Do not "
            "access OSS through a raw IP address: OSS public IPs are shared "
            "and requests must use the bucket domain "
            "(<bucket>.<endpoint>)."
        )
    if kind == "cname":
        # E1: custom-domain (CNAME) knowledge path -- no live evidence needed,
        # build_recommendation stays a pure function; main() refines this with
        # the DNS / ListCname evidence via evaluate_cname().
        recs.append(
            "The value provided is a custom domain (CNAME), not a standard OSS "
            "endpoint. A custom domain is served through the bucket's own "
            "region endpoint, so endpoint-region rules still apply underneath. "
            "Walk the custom-domain troubleshooting path "
            "(references/endpoint-rules.md §3.3) in order:"
        )
        recs.extend(CNAME_TROUBLESHOOTING_PATH)
    if not recs and bucket_info:
        recs.append(
            "Endpoint configuration looks consistent with the bucket "
            "location; if costs are the concern, verify which clients use "
            "the public endpoint and move same-region traffic to the "
            "internal endpoint. For per-bucket traffic cost attribution, "
            "use alibabacloud-oss-billing-diagnosis --bucket-usage."
        )
        # E7: 固化 client-tools defer 转介为运行时话术 -- when the endpoint is
        # correct but a specific tool still fails, the residual cause is the
        # client tool (ossutil / ossbrowser / SDK config / concurrency), out of
        # this skill's in-domain scope (endpoint-rules.md §6).
        recs.append(
            "If the endpoint is correct but a specific tool still fails "
            "(ossutil / ossbrowser / SDK connection, timeout, or concurrency "
            "behaviour), that is a client-tool question -- use "
            "alibabacloud-oss-client-tools-diagnosis."
        )
    return recs


# N-3 inline assertions (finance-cloud / ordinary / unknown)
# 1) finance-cloud with no extranet -> must NOT produce template-derived endpoint
_fin_recs = build_recommendation(
    {"location": "oss-cn-hangzhou-finance",
     "intranet_endpoint": "",
     "extranet_endpoint": ""},
    classify_endpoint("oss-cn-beijing.aliyuncs.com"), "mismatch")
assert any("finance" in r and "oss-cn-hzfinance" in r for r in _fin_recs), \
    "N-3: finance-cloud mismatch must reference official endpoint, not template"
assert not any("oss-cn-hangzhou-finance.aliyuncs.com" in r for r in _fin_recs), \
    "N-3: finance-cloud must NOT produce template-derived endpoint"
# 2) finance-cloud WITH extranet真値 -> uses the authoritative value
_fin2_recs = build_recommendation(
    {"location": "oss-cn-hangzhou-finance",
     "intranet_endpoint": "oss-cn-hzfinance-internal.aliyuncs.com",
     "extranet_endpoint": "oss-cn-hzfinance.aliyuncs.com"},
    classify_endpoint("oss-cn-beijing.aliyuncs.com"), "mismatch")
assert any("oss-cn-hzfinance.aliyuncs.com" in r for r in _fin2_recs), \
    "N-3: finance-cloud with extranet真値 must use it"
# 3) ordinary region mismatch -> normal template derivation
assert isinstance(build_recommendation(
    {"location": "oss-cn-shanghai",
     "intranet_endpoint": "oss-cn-shanghai-internal.aliyuncs.com",
     "extranet_endpoint": "oss-cn-shanghai.aliyuncs.com"},
    classify_endpoint("oss-cn-beijing.aliyuncs.com"), "mismatch"), list)  # normal
assert any("oss-cn-shanghai.aliyuncs.com" in r for r in build_recommendation(
    {"location": "oss-cn-shanghai",
     "intranet_endpoint": "oss-cn-shanghai-internal.aliyuncs.com",
     "extranet_endpoint": "oss-cn-shanghai.aliyuncs.com"},
    classify_endpoint("oss-cn-beijing.aliyuncs.com"), "mismatch"))  # ordinary uses extranet
# 4) unknown finance location (not in the known table) -> guidance string
_fin3_recs = build_recommendation(
    {"location": "oss-cn-hangzhou-finance-1",
     "intranet_endpoint": "",
     "extranet_endpoint": ""},
    classify_endpoint("oss-cn-beijing.aliyuncs.com"), "mismatch")
assert any("finance" in r and "regions-and-endpoints" in r for r in _fin3_recs), \
    "N-3: unknown finance location must reference official table"
# 5) existing assertions preserved
assert any("internal" in r for r in build_recommendation(
    {"location": "oss-cn-shanghai",
     "intranet_endpoint": "oss-cn-shanghai-internal.aliyuncs.com",
     "extranet_endpoint": "oss-cn-shanghai.aliyuncs.com"},
    classify_endpoint("oss-cn-shanghai.aliyuncs.com"), "matched"))  # normal: public->internal advice
assert any("not a valid" in r for r in build_recommendation(
    {}, classify_endpoint(""), "unknown"))  # invalid endpoint advice
assert build_recommendation(
    {}, classify_endpoint(""), "unknown", user_provided=False) == [] or \
    not any("not a valid" in r for r in build_recommendation(
        {}, classify_endpoint(""), "unknown", user_provided=False))  # boundary: defaulted endpoint, no user input
assert build_recommendation(None, None, "unknown") != []  # boundary: empty evidence


def _cname_cross_skill_referrals(verdict):
    """E6: script-layer cross-skill referrals for the custom-domain context.

    A custom-domain question often fans out to a neighbouring skill once the
    CNAME binding itself is resolved (or is clearly a CDN/static-site matter).
    The endpoint skill is the network枢纽 (in-degree 1st, pointed at by 9
    skills) but historically emitted only one outbound referral (billing);
    these close real single-direction edges:
      * static-website  -- a bound domain that should open a webpage but does
        not (seed ticket 00057R7C3C: domain bound, files uploaded, page will
        not open) is a static-website-hosting / index-document question.
      * direct-access-link -- object preview (default domain forces download)
        and hotlink/Referer (防盗链) on the domain.
      * cdn-origin-config -- the domain is intentionally fronted by a CDN.
    Returned lines are appended after the §3.3 troubleshooting path; only for
    verdicts where the binding exists / resolution is the downstream question.
    """
    if verdict in ("CUSTOM_DOMAIN_CNAME_OK",
                   "CUSTOM_DOMAIN_CNAME_MISRESOLVED",
                   "CUSTOM_DOMAIN_CNAME_DISABLED",
                   "CUSTOM_DOMAIN_CNAME_PENDING"):
        return [
            "If the domain is meant to open a webpage (index.html / static "
            "site) but shows a download, a 404, or a blank page once the CNAME "
            "is healthy, that is a static-website-hosting question -- use "
            "alibabacloud-oss-static-website-diagnosis (index/error document, "
            "static-website endpoint).",
            "For object preview (the default OSS domain forces HTML/images to "
            "download) or hotlink / Referer 防盗链 on the domain, use "
            "alibabacloud-oss-direct-access-link-diagnosis.",
            "If the domain is intentionally fronted by a CDN (the resolution "
            "chain points at a CDN, not the bucket endpoint), the origin/回源 "
            "configuration is a CDN question -- use "
            "alibabacloud-oss-cdn-origin-config-diagnosis.",
        ]
    return []


assert _cname_cross_skill_referrals("CUSTOM_DOMAIN_CNAME_OK") != []          # normal: bound verdicts refer out
assert any("static-website" in r for r in _cname_cross_skill_referrals("CUSTOM_DOMAIN_CNAME_OK"))
assert any("direct-access-link" in r for r in _cname_cross_skill_referrals("CUSTOM_DOMAIN_CNAME_MISRESOLVED"))
assert _cname_cross_skill_referrals("CUSTOM_DOMAIN_CNAME_NOT_RESOLVED") == []  # boundary: DNS-fix verdict, no fan-out
assert _cname_cross_skill_referrals("CUSTOM_DOMAIN_CNAME_UNKNOWN") == []       # invalid: unknown verdict


def evaluate_cname(domain, dns_result, bound_cnames, bucket_extranet=""):
    """Pure CNAME verdict from evidence (no I/O -- main() gathers the evidence).

    Args:
      domain          -- the custom domain the customer reported
      dns_result      -- resolve_cname_target() output, or None when the DNS
                         probe was not run / unavailable
      bound_cnames    -- list_bucket_cname() output (list of {"domain","status"}),
                         or None when ListCname degraded (binding unknown)
      bucket_extranet -- the bucket's authoritative public endpoint (the
                         expected CNAME target), may be "" when undiscovered

    Returns a dict with a stable `verdict` code (CUSTOM_DOMAIN_CNAME_*) plus
    the evidence fields and the ordered recommendations (verdict-specific line
    followed by the §3.3 troubleshooting path). Never raises.
    """
    dom = (domain or "").strip().lower().rstrip(".")
    have_dns = isinstance(dns_result, dict)
    resolved = bool(dns_result.get("resolved")) if have_dns else False
    dns_error = (dns_result.get("error", "") if have_dns else "") or ""
    canonical = (dns_result.get("canonical", "") if have_dns else "") or ""
    aliases = list(dns_result.get("aliases", []) if have_dns else [])
    extranet = (bucket_extranet or "").strip().lower()

    binding = "unknown"      # unknown | unbound | enabled | disabled | pending
    bound_status = ""
    has_certificate = None   # None = ListCname unavailable; else bool
    cert_status = ""
    if isinstance(bound_cnames, list):
        match = [c for c in bound_cnames
                 if str(c.get("domain", "")).strip().lower() == dom]
        if not match:
            binding = "unbound"
        else:
            bound_status = str(match[0].get("status", "") or "").strip()
            has_certificate = bool(match[0].get("has_certificate"))
            cert_status = str(match[0].get("cert_status", "") or "").strip()
            _bs = bound_status.lower()
            if _bs == "enabled":
                binding = "enabled"
            elif _bs == "disabled":
                # Official ListCname Status enum: Enabled | Disabled.
                binding = "disabled"
            else:
                # A non-standard / empty Status. The OSS console's "待检测"
                # (pending verification) is a console-side CnameToken state and
                # is NOT an API Status value; treat any unexpected status as
                # pending rather than inventing a meaning.
                binding = "pending"

    if have_dns and not resolved:
        verdict = "CUSTOM_DOMAIN_CNAME_NOT_RESOLVED"
    elif binding == "unbound":
        verdict = "CUSTOM_DOMAIN_CNAME_NOT_BOUND"
    elif binding == "disabled":
        verdict = "CUSTOM_DOMAIN_CNAME_DISABLED"
    elif binding == "pending":
        verdict = "CUSTOM_DOMAIN_CNAME_PENDING"
    elif binding == "enabled" and resolved:
        if extranet:
            chain = " ".join([canonical] + aliases).lower()
            verdict = ("CUSTOM_DOMAIN_CNAME_OK" if extranet in chain
                       else "CUSTOM_DOMAIN_CNAME_MISRESOLVED")
        else:
            verdict = "CUSTOM_DOMAIN_CNAME_OK"
    else:
        verdict = "CUSTOM_DOMAIN_CNAME_UNKNOWN"

    target = extranet or "<bucket>.oss-<region>.aliyuncs.com"
    if verdict == "CUSTOM_DOMAIN_CNAME_NOT_RESOLVED":
        lead = (
            f"The custom domain '{dom}' does NOT resolve"
            + (f" ({dns_error})" if dns_error else "")
            + ". This reproduces the customer-side UnknownHostException / "
              "'no such host'. First fix the CNAME record at the DNS provider "
              f"so '{dom}' points at the bucket's public endpoint ({target}); "
              "until it resolves, no request can reach the bucket through this "
              "domain.")
    elif verdict == "CUSTOM_DOMAIN_CNAME_NOT_BOUND":
        lead = (
            f"The custom domain '{dom}' resolves, but it is NOT bound to this "
            "bucket (read-only ListCname returned no matching domain). Bind it "
            "in the OSS console (Bucket > Transmission Management > Domain "
            "Names); an unbound domain returns 403 / no bucket resolution even "
            "with a correct CNAME. For mainland-China buckets the domain must "
            "have completed ICP filing first.")
    elif verdict == "CUSTOM_DOMAIN_CNAME_DISABLED":
        lead = (
            f"The custom domain '{dom}' is bound to this bucket but its "
            "ListCname Status is 'Disabled' (official enum: Enabled | "
            "Disabled). A disabled binding does not serve requests. Re-enable "
            "it in the OSS console (Bucket > Transmission Management > Domain "
            "Names) and confirm the CNAME target and ICP filing are still "
            "valid.")
    elif verdict == "CUSTOM_DOMAIN_CNAME_PENDING":
        lead = (
            f"The custom domain '{dom}' is present in ListCname with a "
            f"non-Enabled status '{bound_status}'. NOTE: the OSS console shows "
            "a not-yet-verified binding as '待检测' (pending verification) -- "
            "that is a console-side CnameToken ownership-verification state, "
            "not an official ListCname Status value (the API enum is only "
            "Enabled | Disabled), and such a domain may not appear in "
            "ListCname until verification completes. Do not conclude the "
            "domain is healthy while verification is outstanding: confirm the "
            "CNAME record points at the bucket endpoint, complete the "
            "CnameToken ownership verification and ICP filing, then wait for "
            "the console state to clear.")
    elif verdict == "CUSTOM_DOMAIN_CNAME_MISRESOLVED":
        lead = (
            f"The custom domain '{dom}' is bound (Enabled) and resolves, but "
            f"its resolution chain ({canonical or ', '.join(aliases) or 'the resolved addresses'}) "
            f"does not reference the bucket's authoritative public endpoint "
            f"({target}). The CNAME likely points at a wrong or stale target "
            f"(e.g. a CDN or another endpoint). Re-point the CNAME at {target} "
            "or use the dedicated CNAME domain (§3.3 step 6). If the domain is "
            "intentionally fronted by a CDN, that is a CDN-origin "
            "configuration question -- use "
            "alibabacloud-oss-cdn-origin-config-diagnosis.")
    elif verdict == "CUSTOM_DOMAIN_CNAME_OK":
        _cert_note = ""
        if has_certificate is False:
            _cert_note = (
                " ListCname reports NO certificate bound for this domain, so "
                "HTTPS on it will fail while HTTP may work -- host an SSL "
                "certificate for the domain in OSS (§3.3 step 3).")
        elif has_certificate is True and cert_status.lower() == "disabled":
            _cert_note = (
                " ListCname reports a certificate whose Status is Disabled, so "
                "HTTPS on this domain may fail -- enable/renew the certificate "
                "(§3.3 step 3).")
        lead = (
            f"The custom domain '{dom}' resolves and is bound to this bucket "
            f"with status Enabled, and its resolution chain references the "
            f"bucket endpoint ({target}). The CNAME binding itself looks "
            "healthy; if access still fails, check the HTTPS certificate "
            "(§3.3 step 3), the SDK CNAME mode (step 5), and the Bucket "
            "Policy / ACL." + _cert_note)
    else:
        lead = (
            f"Insufficient evidence to conclude the custom-domain (CNAME) "
            f"state of '{dom}': the DNS probe and/or the read-only ListCname "
            "did not return usable data. Walk the manual troubleshooting path "
            "below and gather the missing evidence; never invent the binding "
            "state.")

    return {
        "domain": dom,
        "verdict": verdict,
        "resolved": resolved,
        "binding": binding,
        "bound_status": bound_status,
        "has_certificate": has_certificate,
        "cert_status": cert_status,
        "dns_error": dns_error,
        "expected_cname_target": target,
        "recommendations": ([lead] + list(CNAME_TROUBLESHOOTING_PATH)
                            + _cname_cross_skill_referrals(verdict)),
    }


# --- E1 evaluate_cname inline assertions (cname / non-cname-evidence / boundary) ---
# normal: bound Enabled + resolved + extranet in the chain -> OK
_ok = evaluate_cname("test234.pier39.cn",
                     {"resolved": True, "canonical": "nicer.oss-cn-shanghai.aliyuncs.com",
                      "aliases": [], "error": ""},
                     [{"domain": "test234.pier39.cn", "status": "Enabled"}],
                     "nicer.oss-cn-shanghai.aliyuncs.com")
assert _ok["verdict"] == "CUSTOM_DOMAIN_CNAME_OK", _ok["verdict"]
assert len(_ok["recommendations"]) == 1 + len(CNAME_TROUBLESHOOTING_PATH) + 3  # path + E6 referrals
# normal: does not resolve -> NOT_RESOLVED (UnknownHostException-class)
_nr = evaluate_cname("gxyckj-filestore.image.yuncreatekj.com",
                     {"resolved": False, "error": "Name or service not known"},
                     [], "")
assert _nr["verdict"] == "CUSTOM_DOMAIN_CNAME_NOT_RESOLVED", _nr["verdict"]
assert "UnknownHostException" in _nr["recommendations"][0]
# normal: resolves but not bound -> NOT_BOUND
_nb = evaluate_cname("actp.mama100.com",
                     {"resolved": True, "canonical": "actp.mama100.com",
                      "aliases": [], "error": ""},
                     [], "oss-cn-shanghai.aliyuncs.com")
assert _nb["verdict"] == "CUSTOM_DOMAIN_CNAME_NOT_BOUND", _nb["verdict"]
assert "ICP filing" in _nb["recommendations"][0]
# normal: bound but pending status -> PENDING (console "待检测")
_pd = evaluate_cname("shop.example.cn",
                     {"resolved": True, "canonical": "x", "aliases": [], "error": ""},
                     [{"domain": "shop.example.cn", "status": "待检测"}], "")
assert _pd["verdict"] == "CUSTOM_DOMAIN_CNAME_PENDING", _pd["verdict"]
assert _pd["bound_status"] == "待检测"
# normal: official Disabled status -> DISABLED (distinct from console pending)
_ds = evaluate_cname("off.example.cn",
                     {"resolved": True, "canonical": "b.oss-cn-hangzhou.aliyuncs.com",
                      "aliases": [], "error": ""},
                     [{"domain": "off.example.cn", "status": "Disabled"}],
                     "b.oss-cn-hangzhou.aliyuncs.com")
assert _ds["verdict"] == "CUSTOM_DOMAIN_CNAME_DISABLED", _ds["verdict"]
assert _ds["binding"] == "disabled"
# boundary: Enabled but no certificate -> OK verdict carries the HTTPS cert note
_nc = evaluate_cname("sec.example.cn",
                     {"resolved": True, "canonical": "b.oss-cn-hangzhou.aliyuncs.com",
                      "aliases": [], "error": ""},
                     [{"domain": "sec.example.cn", "status": "Enabled",
                       "has_certificate": False, "cert_status": ""}],
                     "b.oss-cn-hangzhou.aliyuncs.com")
assert _nc["verdict"] == "CUSTOM_DOMAIN_CNAME_OK", _nc["verdict"]
assert _nc["has_certificate"] is False and "NO certificate" in _nc["recommendations"][0]
# boundary: bound Enabled + resolved but the chain misses the bucket endpoint -> MISRESOLVED
_mr = evaluate_cname("cdn.example.com",
                     {"resolved": True, "canonical": "cdn.other.net",
                      "aliases": ["w.kunlun.com"], "error": ""},
                     [{"domain": "cdn.example.com", "status": "Enabled"}],
                     "nicer.oss-cn-shanghai.aliyuncs.com")
assert _mr["verdict"] == "CUSTOM_DOMAIN_CNAME_MISRESOLVED", _mr["verdict"]
# invalid / non-cname-evidence: no DNS probe and ListCname degraded -> UNKNOWN
_unk = evaluate_cname("whatever.example.com", None, None, "")
assert _unk["verdict"] == "CUSTOM_DOMAIN_CNAME_UNKNOWN", _unk["verdict"]
assert len(_unk["recommendations"]) == 1 + len(CNAME_TROUBLESHOOTING_PATH)
# boundary: domain matching is case-insensitive and dot-tolerant
_ci = evaluate_cname("TEST234.pier39.cn.",
                     {"resolved": True, "canonical": "nicer.oss-cn-shanghai.aliyuncs.com",
                      "aliases": [], "error": ""},
                     [{"domain": "test234.pier39.cn", "status": "Enabled"}],
                     "nicer.oss-cn-shanghai.aliyuncs.com")
assert _ci["verdict"] == "CUSTOM_DOMAIN_CNAME_OK", _ci["verdict"]
# --- end evaluate_cname inline assertions ---


# ---------------------------------------------------------------------------
# Official doc verification wiring (optional --question)
# Read-only enhancement per the doc-lookup integration spec: the embedded
# endpoint knowledge (classification + recommendation rules above) is
# Step A; endpoint selection / internal-access questions are configuration
# consultations, so any provided --question also goes through the
# llms-index official-doc leg (Step B). Never blocks the diagnosis:
# offline / failures degrade into a note; STATUS/NEXT_ACTION untouched.
# ---------------------------------------------------------------------------

def build_doc_verification(question):
    """Return the doc_verification block or None (empty question); the
    lookup leg never raises and never blocks the main diagnosis."""
    q = (question or "").strip() if isinstance(question, str) else ""
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
assert build_doc_verification("") is None        # invalid: empty skipped
assert build_doc_verification(None) is None      # invalid: None skipped
assert build_doc_verification("   ") is None     # boundary: whitespace skipped

# Online-shape self-test without network: stub the fetcher with a fake
# index + body and assert the matched/docs/excerpt wiring end-to-end.
_orig_fetch = _doc_lookup._fetch_text
_orig_cache = _doc_lookup.CACHE_FILE
_orig_write = _doc_lookup._atomic_write_cache
_fake_cache = os.path.join(
    tempfile.gettempdir(),
    "oss-skill-docs-selftest-%d" % os.getpid(), "never-written.txt")
_fake_index = ("- [内网访问](https://help.aliyun.com/zh/oss/internal.md): "
               "内网访问说明。\n")
_fake_body = "# 内网访问\n\n这是内网访问文档的正文段落。"


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
            "ECS 内网访问 OSS", _doc_lookup.SKILL_DOC_TOPICS)
finally:
    _doc_lookup._fetch_text = _orig_fetch
    _doc_lookup.CACHE_FILE = _orig_cache
    _doc_lookup._atomic_write_cache = _orig_write
assert _online_check["matched"] is True                        # online shape
assert _online_check["docs"][0]["url"].endswith("/internal.md")
assert _online_check["docs"][0]["excerpt"] == "这是内网访问文档的正文段落。"
assert _online_check["note"] is None
assert _online_check["source"] == "llms-index"

# Offline self-test without network: failing fetcher + absent cache must
# degrade (matched False, DEGRADED note) and never raise or block.
try:
    _doc_lookup._fetch_text = _stub_fetch_fail
    _doc_lookup.CACHE_FILE = _fake_cache
    with contextlib.redirect_stderr(io.StringIO()):
        _offline_check = _doc_lookup.lookup_config_topic(
            "ECS 内网访问 OSS", _doc_lookup.SKILL_DOC_TOPICS)
finally:
    _doc_lookup._fetch_text = _orig_fetch
    _doc_lookup.CACHE_FILE = _orig_cache
assert _offline_check["matched"] is False                      # offline shape
assert _offline_check["docs"] == []
assert _offline_check["note"].startswith("DEGRADED")


# ---------------------------------------------------------------------------
# Diagnosis orchestration
# ---------------------------------------------------------------------------

def _emit(report: dict, status: str, next_action: str) -> int:
    """Print the structured report + STATUS/NEXT_ACTION contract lines."""
    report["status"] = status
    report["next_action"] = next_action
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"STATUS: {status}")
    print(f"NEXT_ACTION: {next_action}")
    return 0 if status in ("OK", "DEGRADED") else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose OSS endpoint configuration and "
                    "internal/public access issues (read-only)",
    )
    parser.add_argument("--bucket", default="", required=False,
                        help="OSS bucket name to diagnose (required; when absent the script emits FAIL and asks)")
    parser.add_argument("--endpoint", default="",
                        help="The endpoint the user currently configured "
                             "(optional; analyzed and matched against the "
                             "bucket region)")
    parser.add_argument("--region", default="",
                        help="Expected region (optional; used to build the "
                             "query endpoint when --endpoint is absent)")
    parser.add_argument("--question", default="",
                        help="Customer's original wording (optional); "
                             "enables the official-doc verification leg")
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
            "skill": "alibabacloud-oss-endpoint-internal-diagnosis",
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
            "skill": globals().get("_SKILL_NAME", "alibabacloud-oss-endpoint-internal-diagnosis"),
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

    # Step 2: resolve the endpoint used to query GetBucketInfo.
    user_endpoint = normalize_endpoint(args.endpoint)
    user_classified = classify_endpoint(user_endpoint) if user_endpoint else None
    query_endpoint = ""
    if user_endpoint and user_classified and user_classified["kind"] not in ("invalid", "cname"):
        query_endpoint = user_endpoint
    elif args.region.strip():
        region = args.region.strip().lower()
        query_endpoint = f"oss-{region}.aliyuncs.com"
        auto_filled.append(f"query endpoint derived from --region: {query_endpoint}")
    else:
        query_endpoint = _DEFAULT_ENDPOINT
        auto_filled.append(
            f"query endpoint auto-defaulted to {query_endpoint} "
            "(no --endpoint/--region provided)")
    # E1: a custom domain (CNAME) is not a valid OSS query endpoint, so the
    # bucket region is discovered via GetBucketInfo/ListBuckets and the query
    # endpoint is rebuilt from the real location below.
    _is_cname = bool(user_classified and user_classified["kind"] == "cname")
    if _is_cname:
        auto_filled.append(
            f"the supplied value '{user_endpoint}' is a custom domain (CNAME), "
            "not a standard OSS endpoint; the bucket region is resolved via "
            "GetBucketInfo/ListBuckets and the query endpoint rebuilt from it")

    report = {
        "skill": "alibabacloud-oss-endpoint-internal-diagnosis",
        "bucket": args.bucket,
        "identity": {"uid": uid,
                     "note": "derived via sts get-caller-identity; empty "
                             "means the identity pre-check degraded"},
        "user_endpoint": user_endpoint or None,
        "query_endpoint": query_endpoint,
        "auto_filled": auto_filled,
        "bucket_info": None,
        "verdict": None,
        "recommendations": [],
        "errors": [],
    }

    # Step 2b: official doc verification (optional --question). Runs
    # alongside the embedded knowledge; never blocks the diagnosis. Without
    # --question the output is byte-identical to the pre-integration
    # behavior (no doc_verification key).
    doc_verification = build_doc_verification(args.question)
    if doc_verification is not None:
        report["doc_verification"] = doc_verification

    # Step 3: GetBucketInfo -- the core evidence call.
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
    # B-7: prefer the GetBucketInfo extranet_endpoint真值; the
    # <location>.aliyuncs.com template is only a fallback for ordinary
    # public-cloud regions, and finance-cloud locations refuse template
    # derivation (they use a separate official naming, e.g. oss-cn-hzfinance).
    _ep, _note = rebuild_query_endpoint(
        str((bucket_info or {}).get("location") or ""),
        str((bucket_info or {}).get("extranet_endpoint") or ""),
        query_endpoint)
    if _note:
        auto_filled.append(_note)
        if "finance-cloud" in _note:
            print(f"[WARN] {_note}", file=sys.stderr)
    if _ep and _ep != query_endpoint:
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

    # Step 3c (E1): CNAME / custom-domain evidence. Only when the user's
    # supplied value classified as a custom domain. Two read-only legs, both
    # fully degradable:
    #   * DNS probe (resolve_cname_target) -- OS resolver only, NOT a cloud
    #     API, no credential; grounds "does not resolve" (UnknownHostException)
    #     and "resolves to a target that misses the bucket endpoint".
    #   * ListCname (oss:ListCname) -- grounds "not bound" / "pending" status.
    cname_diagnosis = None
    if _is_cname:
        _domain = user_endpoint
        _dns = _oss_client.resolve_cname_target(_domain)
        if not _dns.get("resolved") and _dns.get("error"):
            print(f"[WARN] CNAME DNS probe: {_domain} not resolved: "
                  f"{_dns['error']}", file=sys.stderr)
        _bound = None
        if bucket_info:
            try:
                _bound = _oss_client.list_bucket_cname(args.bucket, query_endpoint)
            except OssClientError as e3:
                print(f"[WARN] ListCname degraded ({e3.category}): {e3}",
                      file=sys.stderr)
                report["errors"].append(e3.to_dict())
        else:
            print("[WARN] ListCname skipped: no bucket metadata available "
                  "(binding state unknown)", file=sys.stderr)
        _extranet = str((bucket_info or {}).get("extranet_endpoint") or "")
        cname_diagnosis = evaluate_cname(_domain, _dns, _bound, _extranet)
        cname_diagnosis["dns"] = _dns
        cname_diagnosis["bound_cnames"] = _bound
        report["cname_diagnosis"] = cname_diagnosis

    # Step 4: verdict + recommendations from whatever evidence exists.
    bucket_location = bucket_info.get("location") if bucket_info else None
    bucket_region = region_from_location(bucket_location) if bucket_location else None
    user_region = user_classified["region"] if user_classified else None
    verdict = match_verdict(user_region, bucket_region)
    report["verdict"] = {
        "user_endpoint_kind": user_classified["kind"] if user_classified else None,
        "user_endpoint_region": user_region,
        "bucket_location": bucket_location,
        "bucket_region": bucket_region,
        "region_match": verdict,
    }
    if cname_diagnosis is not None:
        # E1: the CNAME专项 findings lead; the region-match advice (if any) is
        # kept as context because a custom domain inherits the bucket region.
        report["verdict"]["cname_verdict"] = cname_diagnosis["verdict"]
        report["recommendations"] = list(cname_diagnosis["recommendations"])
    else:
        report["recommendations"] = build_recommendation(
            bucket_info, user_classified, verdict,
            user_provided=bool(user_endpoint))

    # Step 5: status + next action.
    if cname_diagnosis is not None:
        _cv = cname_diagnosis["verdict"]
        _na_map = {
            "CUSTOM_DOMAIN_CNAME_NOT_RESOLVED":
                "The custom domain does not resolve (UnknownHostException / "
                "'no such host'); fix the CNAME record at the DNS provider so "
                "it points at the bucket's public endpoint, then re-check.",
            "CUSTOM_DOMAIN_CNAME_NOT_BOUND":
                "The custom domain resolves but is not bound to this bucket "
                "(read-only ListCname shows no match); bind it in the OSS "
                "console (Transmission Management > Domain Names) after ICP "
                "filing, then re-check.",
            "CUSTOM_DOMAIN_CNAME_DISABLED":
                "The custom domain is bound but its ListCname Status is "
                "Disabled; re-enable it in the OSS console (Transmission "
                "Management > Domain Names) and confirm the CNAME target / ICP "
                "filing, then re-check.",
            "CUSTOM_DOMAIN_CNAME_PENDING":
                "The custom-domain binding shows a non-Enabled status (the "
                "console '待检测' is a CnameToken verification state, not an "
                "API Status value); confirm the CNAME target, complete "
                "ownership verification and ICP filing, wait for it to clear, "
                "then re-check.",
            "CUSTOM_DOMAIN_CNAME_MISRESOLVED":
                "The custom domain is bound but resolves to a target that is "
                "not the bucket endpoint; re-point the CNAME at the bucket's "
                "public endpoint (or use the dedicated CNAME domain), then "
                "re-check.",
            "CUSTOM_DOMAIN_CNAME_OK":
                "The custom domain resolves and is bound (Enabled) to the "
                "bucket endpoint; if access still fails, check the HTTPS "
                "certificate, the SDK CNAME mode (is_cname=True), and the "
                "Bucket Policy / ACL.",
            "CUSTOM_DOMAIN_CNAME_UNKNOWN":
                "Custom-domain evidence is incomplete (DNS probe and/or "
                "ListCname degraded); walk the CNAME troubleshooting path in "
                "references/endpoint-rules.md §3.3 and gather the missing "
                "evidence.",
        }
        next_action = _na_map.get(_cv, _na_map["CUSTOM_DOMAIN_CNAME_UNKNOWN"])
        # OK when usable CNAME evidence was obtained; DEGRADED only when the
        # verdict is UNKNOWN and no bucket metadata was available either.
        _status = ("DEGRADED"
                   if _cv == "CUSTOM_DOMAIN_CNAME_UNKNOWN" and not bucket_info
                   else "OK")
        sys.exit(_emit(report, _status, next_action))

    if bucket_info:
        if verdict == "mismatch":
            next_action = (
                f"Reconfigure the client endpoint to the bucket's region "
                f"({bucket_location}); use the internal endpoint for "
                "same-region Alibaba Cloud clients to avoid public network "
                "traffic cost.")
        elif user_classified and user_classified["kind"] == "public" and verdict == "matched":
            next_action = (
                "If clients run on Alibaba Cloud in the same region, switch "
                "them to the internal endpoint to remove public network "
                "traffic cost. For per-bucket traffic attribution (which "
                "bucket generates the most outbound cost), use "
                "alibabacloud-oss-billing-diagnosis --bucket-usage.")
        else:
            next_action = (
                "Endpoint configuration verified against the bucket "
                "location; no region mismatch found.")
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
            "oss:ListBuckets (see references/ram-policies.md) or confirm the "
            "bucket belongs to this account, then re-run.")
    elif cat == "endpoint":
        next_action = (
            "The request hit the wrong region's endpoint; re-run with the "
            "endpoint of the region where the bucket was created "
            "('must use specified endpoint').")
    elif cat == "network":
        next_action = (
            "Network/DNS failure reaching the endpoint host ('no such host' "
            "style): verify DNS resolution, and note internal endpoints "
            "resolve only inside the Alibaba Cloud network of that region.")
    elif cat == "credentials":
        next_action = (
            "No credentials in the environment credential chain; configure "
            "the default credential chain (aliyun configure / environment "
            "variables), never pass AK/SK manually.")
    elif cat == "invalid":
        next_action = (
            "The supplied bucket name is invalid (bucket names are 3-63 "
            "lowercase letters/digits/hyphens, no dots); fix the spelling "
            "and re-run -- if the value looks like an endpoint host, the "
            "bucket and endpoint arguments were likely swapped.")
    else:
        next_action = (
            "OSS control-plane query failed; review the recorded errors and "
            "re-run after fixing the root cause.")
    sys.exit(_emit(report, "DEGRADED", next_action))


if __name__ == "__main__":
    sys.exit(main())
