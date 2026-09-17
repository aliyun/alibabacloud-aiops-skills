#!/usr/bin/env python3
"""
oss_direct_access_diagnosis.py -- OSS direct-access link diagnosis
===================================================================
SECURITY: READ-ONLY. Only issues GetBucketInfo, GetBucketReferer,
GetBucketWebsite, ListBucketCname (+ ListBuckets fallback) to the OSS
control plane, GetCallerIdentity to STS, and an ANONYMOUS (credential-free)
HEAD probe of the bucket's default domain when --object is given. Never
mutates anything: PutBucketReferer / PutBucketWebsite / PutObject and any
other write API are ABSOLUTELY PROHIBITED -- referer / domain / preview
configuration templates are printed as text for the user to apply manually.
Credentials come exclusively from the default credential chain (environment
variables for the OSS SDK, aliyun CLI default chain for STS); AK/SK are
never read, printed, or passed explicitly.

Diagnoses (scope, ~280 tickets/month class):
  * preview-turns-download attribution: OSS default-domain forced-download
    policy, Content-Disposition: attachment metadata, Content-Type
    mis-configuration (application/octet-stream), private-bucket anonymous
    403 as a diagnosis branch itself
  * custom domain binding check & failure attribution: ListBucketCname
    evidence, ICP filing requirement knowledge, CNAME resolution and
    certificate guidance
  * referer hotlink-protection false positives: whitelist matching,
    allow_empty_referer semantics (direct address-bar access carries NO
    Referer header)
  * static website hosting (GetBucketWebsite) is read ONLY to separate the
    boundary: hosting rules (index/404 pages) belong to the sibling
    endpoint-internal skill; this skill reports the state as context.

Output contract (04-spec): stdout carries a structured JSON report followed
by the machine-consumable lines:
    STATUS: OK | DEGRADED
    NEXT_ACTION: <one actionable sentence>

Usage:
  python3 oss_direct_access_diagnosis.py --bucket <name> \
      [--object <key>] [--domain <custom-domain>] \
      [--endpoint <endpoint>] [--region <region>]
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import _oss_client
import _doc_lookup
from _oss_client import OssClientError

_DEFAULT_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"
_PROBE_TIMEOUT = 15  # seconds, applied to the anonymous HEAD probe


# ---------------------------------------------------------------------------
# Pure functions (each carries inline boundary assertions:
# normal / boundary / invalid inputs)
# ---------------------------------------------------------------------------

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


def normalize_domain(raw: str) -> str:
    """Normalize a custom-domain value for comparison: strip scheme,
    lowercase, strip trailing slash / path / port."""
    s = (raw or "").strip().lower()
    if not s:
        return ""
    for scheme in ("https://", "http://"):
        if s.startswith(scheme):
            s = s[len(scheme):]
    s = s.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    return s.rstrip(".")


assert normalize_domain("https://Img.Example.com/a.jpg") == "img.example.com"  # normal
assert normalize_domain("http://www.a.com/") == "www.a.com"  # boundary: scheme+slash
assert normalize_domain("cdn.a.com") == "cdn.a.com"  # boundary: bare host
assert normalize_domain("") == ""  # invalid: empty
assert normalize_domain(None) == ""  # invalid: missing


def domain_bound(domain: str, cnames) -> bool:
    """Whether the normalized domain appears in the bucket's bound cname
    list (case-insensitive exact host match)."""
    d = normalize_domain(domain)
    if not d:
        return False
    for item in cnames or []:
        bound = normalize_domain((item or {}).get("domain", ""))
        if bound and bound == d:
            return True
    return False


_CNAMES_A = [{"domain": "img.example.com", "last_modified": ""}]
assert domain_bound("https://img.example.com/x.jpg", _CNAMES_A) is True  # normal
assert domain_bound("IMG.EXAMPLE.COM", _CNAMES_A) is True  # boundary: case
assert domain_bound("cdn.example.com", _CNAMES_A) is False  # invalid: unbound
assert domain_bound("", _CNAMES_A) is False  # invalid: empty
assert domain_bound("img.example.com", []) is False  # boundary: no cnames


def _strip_scheme_and_split(value: str):
    """Split a URL-like value into (host, rest) after stripping the scheme."""
    v = (value or "").strip().lower()
    for scheme in ("https://", "http://"):
        if v.startswith(scheme):
            v = v[len(scheme):]
    host, _, rest = v.partition("/")
    return host, rest


def referer_matches(pattern: str, referer: str) -> bool:
    """Match one OSS referer-whitelist entry against a request Referer.

    OSS semantics: entries may carry '*' and '?' wildcards (e.g.
    '*.example.com', 'http://www.example.com/*'); matching is
    case-insensitive. A host-only entry (no '/') matches the referer's
    host; an entry containing '/' is matched against host+path, so
    '*.example.com' matches 'http://a.example.com/p.jpg' (the wildcard
    spans the host part). An empty pattern never matches.
    """
    p = (pattern or "").strip().lower()
    if not p or not (referer or "").strip():
        return False
    r_host, r_rest = _strip_scheme_and_split(referer)
    p_host, p_rest = _strip_scheme_and_split(p)
    if not r_host or not p_host:
        return False
    if not p_rest and "/" not in p:
        return fnmatch.fnmatchcase(r_host, p_host)
    return fnmatch.fnmatchcase(
        r_host + "/" + r_rest, p_host + "/" + p_rest)


assert referer_matches("*.example.com", "http://a.example.com/p.jpg") is True  # normal: wildcard host
assert referer_matches("http://www.a.com", "http://www.a.com") is True  # normal: exact
assert referer_matches("http://www.a.com/*", "http://www.a.com/img/b.jpg") is True  # boundary: path wildcard
assert referer_matches("*.example.com", "http://evil.com") is False  # invalid: mismatch
assert referer_matches("", "http://a.com") is False  # invalid: empty pattern
assert referer_matches("*.example.com", "") is False  # invalid: empty referer


def referer_verdict(referer_cfg, page_referer: str) -> str:
    """Classify a request against the bucket's hotlink-protection config.

    Official OSS check order (help-center hotlink-protection doc):
      1. empty-referer check -- a request with NO Referer passes when
         allow_empty_referer=true; when false it is denied ONLY IF the
         whitelist is non-empty (deny-empty + empty whitelist passes).
      2. blacklist check      -- a NON-empty Referer matching any
         blacklist entry is denied immediately: the blacklist outranks
         the whitelist, which is not even consulted on a hit.
      3. whitelist check      -- a match passes; with an EMPTY whitelist
         a non-blacklisted referer passes (blacklist-only mode).

    Returns one of:
      not_configured   -- whitelist AND blacklist are empty (OSS default;
                          every request is allowed, no protection in force)
      allowed          -- the request passes per the rules above
      denied_empty     -- no Referer + allow_empty_referer=false +
                          non-empty whitelist (direct address-bar access,
                          some apps / WebView clients, privacy-stripping
                          proxies)
      denied_blacklist -- the Referer matches a blacklist entry (outranks
                          any whitelist match)
      denied_mismatch  -- whitelist entries exist, none matches
    """
    cfg = referer_cfg or {}
    whites = cfg.get("referers") or []
    blacks = cfg.get("black_referers") or []
    if not whites and not blacks:
        return "not_configured"
    r = (page_referer or "").strip()
    if not r:
        if cfg.get("allow_empty_referer", True):
            return "allowed"
        return "denied_empty" if whites else "allowed"
    if any(referer_matches(p, r) for p in blacks):
        return "denied_blacklist"
    if whites:
        if any(referer_matches(p, r) for p in whites):
            return "allowed"
        return "denied_mismatch"
    return "allowed"


_CFG_EMPTY = {"allow_empty_referer": True, "referers": [],
              "black_referers": []}
_CFG_STRICT = {"allow_empty_referer": False,
               "referers": ["*.example.com"]}
_CFG_BLACK = {"allow_empty_referer": True, "referers": ["*"],
              "black_referers": ["*bad.example"]}
assert referer_verdict(_CFG_EMPTY, "") == "not_configured"  # normal: OSS default
assert referer_verdict(_CFG_STRICT, "http://a.example.com") == "allowed"  # normal: match
assert referer_verdict(_CFG_STRICT, "") == "denied_empty"  # boundary: empty referer blocked
assert referer_verdict(_CFG_STRICT, "http://evil.com") == "denied_mismatch"  # boundary: mismatch
assert referer_verdict({"allow_empty_referer": True,
                        "referers": ["*.a.com"]}, "") == "allowed"  # boundary: empty allowed
assert referer_verdict(None, "") == "not_configured"  # invalid: missing cfg
# blacklist outranks the whitelist (official order: empty -> blacklist -> whitelist)
assert referer_verdict(_CFG_BLACK, "http://bad.example/x") == "denied_blacklist"  # normal: black hit
assert referer_verdict(_CFG_BLACK, "http://good.example/x") == "allowed"  # normal: black miss, white *
assert referer_verdict({"allow_empty_referer": False, "referers": [],
                        "black_referers": ["*.bad.example"]},
                       "http://ok.example") == "allowed"  # boundary: blacklist-only mode
assert referer_verdict({"allow_empty_referer": False, "referers": [],
                        "black_referers": ["*.bad.example"]},
                       "") == "allowed"  # boundary: deny-empty + empty whitelist passes


def classify_probe(status: int, content_type: str,
                   content_disposition: str, bucket_acl: str,
                   x_oss_force_download: str = "") -> dict:
    """Attribute a preview-vs-download outcome from an anonymous probe of
    the bucket's default domain.

    x_oss_force_download carries the 'X-Oss-Force-Download' response
    header: 'true' means OSS ITSELF injected the forced-download headers
    (0048 error-code family) -- stronger evidence than the attachment
    disposition alone, which can also come from object metadata.

    Returns {"verdict": ..., "attribution": [...]}:
      private_bucket_403 -- anonymous 403 against a private bucket is a
                            diagnosis branch itself: anonymous access is
                            denied by ACL/referer; preview needs a signed
                            URL or object/bucket public-read
      open_403           -- anonymous 403 on a NON-private bucket: the
                            EC 0003-00000005 bisection (referer ->
                            object private ACL -> Block Public Access ->
                            unattributed escalation, see M5) applies;
                            the entry script runs it and replaces this
                            provisional verdict
      forced_download    -- response carries Content-Disposition attachment
                            and/or x-oss-force-download: true
      content_type_misconfig -- Content-Type is application/octet-stream
                                (browser downloads unknown binary instead
                                of rendering)
      previewable        -- inline-renderable content type, no attachment
      http_error         -- other non-2xx status
    """
    ct = (content_type or "").strip().lower()
    cd = (content_disposition or "").strip().lower()
    attrs = []
    if status == 403:
        if (bucket_acl or "").lower() == "private":
            return {
                "verdict": "private_bucket_403",
                "attribution": [
                    "Anonymous access returned 403 and the bucket ACL is "
                    "private: anonymous requests are denied by design. To "
                    "preview, use a signed URL (presigned GET) or make the "
                    "object/bucket public-read; a 403 here does NOT prove "
                    "a referer misconfiguration by itself.",
                ],
            }
        return {
            "verdict": "open_403",
            "attribution": [
                "Anonymous access returned 403 on a non-private bucket "
                "(EC 0003-00000005 class): attribute it in the fixed order "
                "referer rules -> object-level private ACL -> Block Public "
                "Access -> unattributed escalation, per "
                "references/ec-0003-00000005-bisection.md; the diagnosis "
                "script runs this bisection automatically and replaces "
                "this provisional verdict.",
            ],
        }
    if status < 200 or status >= 300:
        return {
            "verdict": "http_error",
            "attribution": [
                f"Probe returned HTTP {status}; check object existence, "
                "bucket ACL and referer whitelist before the preview "
                "question is meaningful.",
            ],
        }
    if (x_oss_force_download or "").strip().lower() == "true":
        attrs.append(
            "The response carries 'x-oss-force-download: true': OSS itself "
            "injected the forced-download headers (0048 error-code "
            "family -- HTML for post-2017-10-01 buckets, the 12 image "
            "MIME types for post-2019-09 buckets, transfer-acceleration "
            "domains, APK/IPA files) -- this is the default-domain "
            "policy, NOT wrong object metadata. Preview for the affected "
            "types requires a bound custom domain.")
    if "attachment" in cd:
        attrs.append(
            "Content-Disposition: attachment is set on the object (or by "
            "the default-domain forced-download policy): the browser "
            "downloads instead of previewing. For preview, set "
            "Content-Disposition: inline on the object, or access through "
            "a bound custom domain where the default-domain download "
            "policy does not apply.")
    if ct.startswith("application/octet-stream"):
        attrs.append(
            "Content-Type is application/octet-stream: the browser treats "
            "it as unknown binary and downloads it. Fix the object's "
            "Content-Type to the real MIME type (e.g. image/jpeg, "
            "application/pdf).")
    if not attrs:
        return {
            "verdict": "previewable",
            "attribution": [
                "No attachment disposition and a renderable Content-Type; "
                "note that OSS DEFAULT domains (*.aliyuncs.com) force "
                "attachment downloads for browser-renderable text types "
                "(HTML/JS/CSS/JSON/..., 0048-00000001 family) and for the "
                "12 image MIME types on buckets created after the 2019-09 "
                "cutoffs (0048-00000100-00000105 family) -- bind a "
                "custom domain for full preview control of those types.",
            ],
        }
    return {"verdict": "forced_download" if ("attachment" in cd or
            (x_oss_force_download or "").strip().lower() == "true") else
            "content_type_misconfig", "attribution": attrs}


assert classify_probe(403, "", "", "private")["verdict"] == "private_bucket_403"  # normal: private 403
assert classify_probe(200, "image/jpeg", "", "public-read")["verdict"] == "previewable"  # normal
assert classify_probe(200, "image/jpeg", "attachment; filename=a.jpg", "public-read")["verdict"] == "forced_download"  # boundary: attachment
assert classify_probe(200, "application/octet-stream", "", "public-read")["verdict"] == "content_type_misconfig"  # boundary: octet-stream
assert classify_probe(404, "", "", "public-read")["verdict"] == "http_error"  # invalid: 404
assert classify_probe(403, "", "", "public-read")["verdict"] == "open_403"  # boundary: non-private 403 -> bisection
assert classify_probe(200, "image/jpeg", "", "public-read",
                      x_oss_force_download="true")["verdict"] == "forced_download"  # normal: 0048 header
assert classify_probe(200, "image/jpeg", "", "public-read",
                      x_oss_force_download="True")["verdict"] == "forced_download"  # boundary: header case
assert "x-oss-force-download" in classify_probe(
    200, "image/jpeg", "", "public-read",
    x_oss_force_download="true")["attribution"][0]  # normal: 0048 attribution


def icp_filing_required(region_or_location: str) -> bool:
    """ICP filing knowledge rule: custom domains bound to buckets located
    in MAINLAND CHINA require an ICP filing; regions outside the mainland
    do not enforce ICP filing for the bound domain.

    Official sources (B-2/B-3 fix, 2026-09-03):
      - access-buckets-via-custom-domain-names:12: "若Bucket位于中国内地，
        绑定的域名必须完成ICP备案。若Bucket位于非中国内地节点（如中国
        香港、新加坡等），绑定的自定义域名无需ICP备案。"
      - document_detail/2248436.html:7,10: regionless-attribute bucket
        (oss-rg-china-mainland) data is stored in mainland China.
      - regions-and-endpoints:67: mainland-to-HK is "cross-border".

    Implementation: explicit whitelist; NEVER use a bare ^oss-cn- prefix.

    H-3: this is the SINGLE AUTHORITATIVE ICP-region rule for the access-entry
    skill group. static-website-diagnosis `is_mainland_region()` is kept
    identical to it (same markers, same order, same unknown -> True
    conservatism, same self-test set). Do NOT let the two drift apart.
    """
    s = (region_or_location or "").strip().lower()
    if not s:
        return True  # unknown location -> conservative guidance
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


assert icp_filing_required("oss-cn-hangzhou") is True   # normal: mainland
assert icp_filing_required("cn-shanghai") is True       # boundary: short region
assert icp_filing_required("cn-hongkong") is False      # boundary: HK outside mainland ICP scope
assert icp_filing_required("oss-cn-hongkong") is False  # B-3: HK with oss- prefix
assert icp_filing_required("oss-ap-southeast-1") is False  # normal: overseas
assert icp_filing_required("") is True                  # invalid: unknown -> conservative
# B-2 fix: regionless-attribute bucket data is stored in mainland China
assert icp_filing_required("oss-rg-china-mainland") is True, \
    "B-2: oss-rg-china-mainland must require ICP filing"
assert icp_filing_required("rg-china-mainland") is True, \
    "B-2: rg-china-mainland (short form) must require ICP filing"
# G-3: local regions
assert icp_filing_required("oss-cn-wuhan-lr") is True
assert icp_filing_required("oss-cn-zhongwei") is True
assert icp_filing_required("oss-cn-fuzhou") is True


def normalize_object_key(raw: str) -> str:
    """Normalize the --object value into a bare object key.

    Accepts BOTH a bare key ('a/b.jpg') and a FULL URL pasted straight
    from a ticket or the browser address bar
    ('https://bucket.oss-cn-hangzhou.aliyuncs.com/a/b.jpg?Expires=...'):
    the URL form is stripped down to its decoded path (DAL-4), so users
    never have to manually cut the key out of a link.
    """
    s = (raw or "").strip()
    low = s.lower()
    if low.startswith("https://") or low.startswith("http://"):
        try:
            s = urllib.parse.unquote(urllib.parse.urlparse(s).path)
        except Exception:
            pass  # fall through to the bare-key normalization
    return s.strip().lstrip("/")


assert normalize_object_key("/a/b.jpg") == "a/b.jpg"  # normal
assert normalize_object_key("a/b.jpg") == "a/b.jpg"  # boundary
assert normalize_object_key(
    "https://test-agentceping.oss-cn-hangzhou.aliyuncs.com/test/header.png"
) == "test/header.png"  # normal: full URL pasted (DAL-4)
assert normalize_object_key(
    "https://b.oss-cn-hangzhou.aliyuncs.com/a%20b.jpg?Expires=1&Signature=x"
) == "a b.jpg"  # boundary: encoded key + query stripped
assert normalize_object_key(
    "https://b.oss-cn-hangzhou.aliyuncs.com/") == ""  # boundary: URL without key
assert normalize_object_key("") == ""  # invalid


# ---------------------------------------------------------------------------
# EC 0003-00000005 bisection SOP (ported from the internal CSE asset, DAL-1)
# ---------------------------------------------------------------------------

# Earliest of the region-dependent image forced-download cutoffs
# (0048-00000100 ~ 00000105: 2019-09-23 17:00 ~ 2019-09-30 15:00 Beijing
# time); the earliest value is the conservative answer when the exact
# region batch is unknown.
_IMAGE_FORCE_DOWNLOAD_CUTOFF = datetime.fromisoformat(
    "2019-09-23T17:00:00+08:00")


def image_force_download_cutoff(creation_date: str) -> bool:
    """Whether the bucket was created after the earliest image
    forced-download cutoff (2019-09-23 17:00 Beijing time), meaning the
    12 image MIME types are force-downloaded over the default domain
    (0048-00000100-00000105 family). Accepts ISO-8601 creation dates (UTC
    'Z' suffix or timezone-aware); unknown/malformed dates return True
    (conservative guidance)."""
    s = (creation_date or "").strip()
    if not s:
        return True  # unknown -> conservative guidance
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return True  # malformed -> conservative guidance
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)  # oss2 reports UTC
    return dt >= _IMAGE_FORCE_DOWNLOAD_CUTOFF


assert image_force_download_cutoff(
    "2024-05-08T09:00:00.000Z") is True  # normal: after cutoff
assert image_force_download_cutoff(
    "2019-09-23T09:00:00.000Z") is True  # boundary: exactly 17:00 Beijing
assert image_force_download_cutoff(
    "2019-09-23T08:59:59.000Z") is False  # boundary: one second before
assert image_force_download_cutoff(
    "2015-01-01T00:00:00.000Z") is False  # normal: old bucket
assert image_force_download_cutoff("") is True  # invalid: unknown -> conservative
assert image_force_download_cutoff("not-a-date") is True  # invalid: malformed


def ec_0003_00000005_bisection(bucket_acl, object_acl_state,
                               referer_denied) -> dict:
    """Ordered attribution for a 403 on a NON-private bucket (EC 0003-00000005).

    Official source: help.aliyun.com/zh/oss/user-guide/0003-00000005
    (B-12 fix, 2026-09-03 — rewritten to match the official 3-cause
    structure; the previous "exactly two documented causes" claim was
    contradicted by the official page).

    Official "问题原因" (two parallel entries):
      1. 您对某个Object发起了读请求，但是却没有该Object的读权限。
      2. 您提供的账号AccessKey ID或签名不正确导致身份认证失败。
    Official "问题示例" paragraph 2:
      Bucket开启了"阻止公共访问"功能，也会导致请求被拒绝。

    Attribution order (this function handles the anonymous-probe path;
    Cause-2 auth failure applies to signed requests and is documented in
    references/ec-0003-00000005-bisection.md section 4):
      precondition: referer rules deny -> referer_denied_403
      precondition: Block Public Access overrides public-read ->
                    block_public_access_403 (checked by the caller via
                    the playbook decision tree, not inside this function)
      Cause-1: object carries its own private ACL -> object_acl_private_403
      Cause-2: AK ID / signature incorrect (signed requests only) ->
               auth_failure_403 (not reachable from the anonymous probe;
               documented for completeness)
      Cause-3: no official cause remains -> unattributed_403 (escalation)

    Inputs:
      bucket_acl       -- bucket ACL label from GetBucketInfo
      object_acl_state -- None (GetObjectAcl degraded/unavailable) or
                          {"acl": "private" | "default" |
                           "public-read" | "public-read-write" | ""}
      referer_denied   -- whether hotlink rules deny the credential-free
                          probe (empty-referer denial with non-empty whitelist)

    Returns {"verdict", "root_cause", "attribution", "fix_template"}
    with verdict one of: referer_denied_403, object_acl_private_403,
    unattributed_403, object_acl_unverifiable, http_error.
    """
    ba = (bucket_acl or "").strip().lower()
    if referer_denied:
        return {
            "verdict": "referer_denied_403",
            "root_cause": "hotlink rules deny the credential-free probe",
            "attribution": [
                "The bucket's hotlink rules deny the anonymous probe "
                "(allow_empty_referer=false with a non-empty whitelist): "
                "the 403 comes from referer rules BEFORE the EC "
                "0003-00000005 causes are considered. Fix per M3 "
                "(AllowEmptyReferer or a matching entry), then re-probe.",
            ],
            "fix_template": "AllowEmptyReferer=true or add a matching "
                            "whitelist entry (manual operation; see "
                            "templates.referer_rule)",
        }
    oa = ((object_acl_state or {}).get("acl") or "").strip().lower()
    if oa == "private":
        return {
            "verdict": "object_acl_private_403",
            "root_cause": "EC 0003-00000005 Cause-1: bucket is "
                          f"'{ba or 'non-private'}' but the object carries "
                          "its own private ACL",
            "attribution": [
                "CAUSE-1 CONFIRMED (EC 0003-00000005, official 问题原因 "
                f"entry 1): the bucket allows public reads ('{ba}') but "
                "GetObjectAcl reports the object ACL as 'private', so "
                "anonymous GET/HEAD is denied on this object alone. This "
                "is the classic 'bucket public-read yet object 403' root "
                "cause.",
            ],
            "fix_template": (
                "Reset the object ACL to inherit the bucket ACL (manual "
                "operation -- this skill never writes): "
                "ossutil set-acl oss://<BUCKET>/<OBJECT_KEY> default; for "
                "many affected objects add -r to recurse over the prefix"),
        }
    if oa:
        # Cause-1 excluded (object ACL is not private). The anonymous probe
        # carries no Authorization header, so Cause-2 (auth failure) does
        # not apply to this path. No official cause remains -> escalate.
        return {
            "verdict": "unattributed_403",
            "root_cause": "EC 0003-00000005: Cause-1 excluded (object ACL "
                          f"is '{oa}', not private) on a "
                          f"'{ba or 'non-private'}' bucket; hotlink rules do "
                          "not deny the probe; no remaining official cause "
                          "applies to the anonymous probe path",
            "attribution": [
                "UNATTRIBUTED (EC 0003-00000005): Cause-1 is excluded "
                f"(object ACL is '{oa}', not private) and hotlink rules do "
                "not deny the probe. The official EC page documents three "
                "cause families (no read permission / AK-or-signature "
                "incorrect / Block Public Access overriding public-read); "
                "none applies to this anonymous-probe evidence. Boundary: "
                "no public query interface exists for internal block "
                "records. Escalate through the violation-handling channel "
                "(ticket / compliance appeal), or defer to the sibling "
                "security-incident-forensics skill for traffic-theft "
                "context. Also verify whether Block Public Access is "
                "enabled on the bucket/account (official 问题示例 "
                "paragraph 2) — that check is outside this function.",
            ],
            "fix_template": "Escalate to the violation-handling channel "
                            "(manual step); also check Block Public Access "
                            "(bucket/account level) and, for signed "
                            "requests, verify AK ID / signature / RAM "
                            "policy per Cause-2 in "
                            "references/ec-0003-00000005-bisection.md "
                            "section 4",
        }
    if ba in ("public-read", "public-read-write"):
        return {
            "verdict": "object_acl_unverifiable",
            "root_cause": "object ACL could not be read (GetObjectAcl "
                          "degraded) on a public-read bucket: Cause-1 "
                          "remains the leading hypothesis",
            "attribution": [
                "GetObjectAcl degraded, so Cause-1 (object private ACL) "
                "cannot be confirmed. Per the SOP inference rule: the "
                f"bucket ACL is '{ba}' and hotlink rules do not deny the "
                "probe, so Cause-1 (the object carrying its own private "
                "ACL) is the leading hypothesis -- have the owner verify "
                "the object ACL manually; only after Cause-1 is excluded "
                "check Block Public Access (precondition) and then "
                "escalate as unattributed.",
            ],
            "fix_template": "Verify the object ACL manually (ossutil ls "
                            "oss://<BUCKET>/<OBJECT_KEY> --acl) or grant "
                            "oss:GetObjectAcl and re-run; if the ACL is "
                            "not 'private', treat the 403 as unattributed "
                            "(check Block Public Access, then escalate via "
                            "the violation-handling channel)",
        }
    return {
        "verdict": "http_error",
        "root_cause": "anonymous 403 on a non-private bucket with no "
                      "attributable cause (bucket ACL unknown, object ACL "
                      "unavailable)",
        "attribution": [
            "Anonymous access returned 403 on a non-private bucket, but "
            "neither the bucket ACL nor the object ACL could be resolved "
            "into a documented cause; check the referer rules, any bucket "
            "policy denying the request, and Block Public Access, then "
            "re-run with credentials that can read the object ACL.",
        ],
        "fix_template": "",
    }


assert ec_0003_00000005_bisection(
    "public-read", {"acl": "private"}, False)["verdict"] == \
    "object_acl_private_403"  # normal: cause-1 confirmed
assert "set-acl" in ec_0003_00000005_bisection(
    "public-read", {"acl": "private"}, False)["fix_template"]  # fix template
assert ec_0003_00000005_bisection(
    "public-read", {"acl": "default"}, False)["verdict"] == \
    "unattributed_403"  # normal: cause-1 excluded -> escalate (B-12)
assert ec_0003_00000005_bisection(
    "public-read", None, False)["verdict"] == \
    "object_acl_unverifiable"  # boundary: ACL unreadable -> inference rule
assert ec_0003_00000005_bisection(
    "public-read", {"acl": "private"}, True)["verdict"] == \
    "referer_denied_403"  # boundary: referer denial outranks both causes
assert ec_0003_00000005_bisection(
    "", None, False)["verdict"] == "http_error"  # invalid: nothing attributable


# ---------------------------------------------------------------------------
# Out-of-scope referral guard (DAL-5: four-way domain transfer)
# ---------------------------------------------------------------------------

_DOMAIN_TRANSFER_GUARDS = (
    {"skill": "alibabacloud-oss-cdn-origin-config-diagnosis",
     "signals": ("cdn", "回源", "边缘节点"),
     "reason": "CDN origin-pull / failover configuration"},
    {"skill": "alibabacloud-oss-cross-account-auth-diagnosis",
     "signals": ("跨账号", "ram 用户", "ram用户", "ram user",
                 "cross-account", "其他账号", "另一个账号", "别的账号"),
     "reason": "cross-account RAM authorization"},
    {"skill": "alibabacloud-oss-presigned-url-v4-diagnosis",
     "signals": ("预签名", "签名url", "签名 url", "presign", "signed url",
                 "signaturedoesnotmatch"),
     "reason": "presigned URL signing and signature failures"},
    {"skill": "alibabacloud-oss-transfer-acceleration-diagnosis",
     "signals": ("传输加速", "加速域名", "oss-accelerate",
                 "transfer acceleration", "加速上传", "加速endpoint"),
     "reason": "transfer-acceleration endpoints and speed"},
)


def domain_transfer_guard(question: str) -> list:
    """Detect out-of-scope signals in the customer's wording and return
    referral entries for the sibling skill that owns them (DAL-5).

    A hit does NOT abort the run: the bucket evidence is still reported
    as context, but the recommendations and NEXT_ACTION lead with the
    referral so the question is not silently absorbed into a generic
    'diagnosis complete' conclusion."""
    q = (question or "").lower()
    hits = []
    for guard in _DOMAIN_TRANSFER_GUARDS:
        if any(sig in q for sig in guard["signals"]):
            hits.append({"skill": guard["skill"],
                         "reason": guard["reason"]})
    return hits


assert domain_transfer_guard(
    "CDN 域名 test234.pier39.cn 504 回源问题") == [
        {"skill": "alibabacloud-oss-cdn-origin-config-diagnosis",
         "reason": "CDN origin-pull / failover configuration"}]  # normal (E9)
assert domain_transfer_guard("跨账号 RAM 用户无法访问桶")[0]["skill"] == \
    "alibabacloud-oss-cross-account-auth-diagnosis"  # normal (E10)
assert domain_transfer_guard("预签名 URL SignatureDoesNotMatch")[0]["skill"] == \
    "alibabacloud-oss-presigned-url-v4-diagnosis"  # normal (E11)
assert domain_transfer_guard("传输加速域名上传慢")[0]["skill"] == \
    "alibabacloud-oss-transfer-acceleration-diagnosis"  # normal (E12)
assert domain_transfer_guard("图片默认域名直接下载怎么在线预览") == []  # in-scope (E1)
assert domain_transfer_guard("设置防盗链后图片全部加载失败") == []  # in-scope (E2)
assert domain_transfer_guard("pdf 打开直接下载想在线预览") == []  # in-scope (E8)
assert domain_transfer_guard("") == []  # invalid: empty


# ---------------------------------------------------------------------------
# Scenario-typed NEXT_ACTION hint (P4 output differentiation)
# ---------------------------------------------------------------------------

_SCENARIO_HINTS = (
    (("apk", "ipa", "安装包"),
     "APK/IPA files are force-downloaded (and forbidden for distribution "
     "on buckets covered by the newer policies, 0048-00000200-00000203 "
     "family) over OSS default domains -- distribute them through a "
     "bound custom domain or another channel"),
    (("css", "html", "javascript", "网页"),
     "HTML/CSS/JS never preview over the default domain (0048-00000001 "
     "family for buckets created after 2017-10-01): serve them through a "
     "bound custom domain"),
    (("视频", "video", "播放"),
     "video preview over the default domain needs a correct video/* "
     "Content-Type on the object and no attachment disposition; for "
     "streaming-grade delivery prefer a bound custom domain (or CDN)"),
    (("图片", "image", "照片"),
     "image preview over the default domain depends on the bucket "
     "creation date (0048-00000100-00000105 family: buckets created "
     "after the 2019-09 cutoffs force-download the 12 image MIME types); "
     "bind a custom domain for reliable image preview"),
    (("pdf",),
     "PDF previews over the default domain when the object's "
     "Content-Type is application/pdf and no attachment disposition is "
     "set; probe the object (--object) to verify its metadata"),
    (("预览", "下载", "preview", "download"),
     "check the preview_fix checklist (Content-Type / Content-Disposition: "
     "inline) and remember the default-domain forced-download families "
     "(0048 EC codes) when the metadata is correct"),
)


def scenario_hint(question: str) -> str:
    """Scenario-typed hint extracted from the customer's wording, used to
    differentiate NEXT_ACTION across question types (P4). Returns ''
    when nothing matches."""
    q = (question or "").lower()
    for signals, hint in _SCENARIO_HINTS:
        if any(s in q for s in signals):
            return hint
    return ""


assert "0048-00000200" in scenario_hint(
    "外网域名下载APK返回 ApkDownloadForbidden")  # normal (E6)
assert "0048-00000001" in scenario_hint("css 无法访问")  # normal (B5 sample)
assert "video" in scenario_hint("系统生成的视频URL没办法播放")  # normal (E5)
assert "0048-00000100" in scenario_hint(
    "图片默认域名直接下载怎么在线预览")  # normal (E1)
assert "PDF" in scenario_hint("pdf 打开直接下载想在线预览")  # normal (E8)
assert scenario_hint(
    "preview turns into download over the default domain") != ""  # boundary: generic (E4)
assert scenario_hint("") == ""  # invalid: empty


# ---------------------------------------------------------------------------
# Anonymous probe of the default domain (NO credentials required)
# ---------------------------------------------------------------------------

def probe_default_domain(bucket_name: str, endpoint: str, object_key: str,
                         timeout: int = _PROBE_TIMEOUT) -> dict:
    """Issue an ANONYMOUS HEAD request against
    https://<bucket>.<endpoint>/<key> -- exactly what a browser opening
    the default-domain URL does. No credentials, no signature: this is a
    data-plane observation, not a control-plane call. The endpoint value
    is scheme-stripped HERE as well (defense in depth, DAL-9) so direct
    unit-level callers cannot build malformed URLs either. The response
    also captures 'X-Oss-Force-Download' (DAL-2): OSS injects that header
    together with Content-Disposition: attachment when the 0048
    forced-download policy applies. All failures are captured in the
    returned dict; nothing raises."""
    key = normalize_object_key(object_key)
    host = (endpoint or "").strip().lower().rstrip("/")
    for scheme in ("https://", "http://"):
        if host.startswith(scheme):
            host = host[len(scheme):]
    host = host.lstrip("/")
    url = "https://{}.{}{}".format(
        bucket_name, host,
        urllib.parse.quote("/" + key) if key else "/")
    req = urllib.request.Request(
        url, method="HEAD",
        headers={"User-Agent": _oss_client.user_agent()})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {
                "url": url,
                "status": resp.status,
                "content_type": resp.headers.get("Content-Type", "") or "",
                "content_disposition":
                    resp.headers.get("Content-Disposition", "") or "",
                "x_oss_force_download":
                    resp.headers.get("X-Oss-Force-Download", "") or "",
            }
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read(512).decode("utf-8", "replace")
        except Exception:
            pass
        return {
            "url": url,
            "status": e.code,
            "content_type": e.headers.get("Content-Type", "") if e.headers else "",
            "content_disposition":
                (e.headers.get("Content-Disposition", "") if e.headers else "") or "",
            "x_oss_force_download":
                (e.headers.get("X-Oss-Force-Download", "") if e.headers else "") or "",
            "error_excerpt": body[:300],
        }
    except Exception as e:  # DNS / timeout / TLS / connection reset
        return {"url": url, "status": 0,
                "error_excerpt": f"network failure: {e}"}


# ---------------------------------------------------------------------------
# Standard templates (text output ONLY -- never applied by this skill)
# ---------------------------------------------------------------------------

def referer_rule_template(page_domain: str) -> dict:
    """Standard hotlink-protection (referer whitelist) template. Printed
    for the user to apply manually (console / PutBucketReferer); NEVER
    executed by this skill."""
    entry = f"*.{page_domain}" if page_domain else "*.your-site.example.com"
    return {
        "apply_via": "OSS console (Permission -> Hotlink Protection) or "
                     "PutBucketReferer API -- manual operation, this skill "
                     "never writes it",
        "allow_empty_referer_note":
            "AllowEmptyReferer controls requests with NO Referer header: "
            "direct address-bar access, some mobile apps / WebView, and "
            "privacy-stripping proxies send no Referer. Set false ONLY if "
            "you accept that such clients get 403; a legitimate user "
            "blocked after enabling protection is almost always "
            "denied_empty, not a malicious request.",
        "xml": (
            "<RefererConfiguration>\n"
            "  <AllowEmptyReferer>true</AllowEmptyReferer>\n"
            "  <RefererList>\n"
            f"    <Referer>{entry}</Referer>\n"
            "  </RefererList>\n"
            "</RefererConfiguration>"),
        "wildcard_note": "entries support * and ? wildcards; *.example.com "
                         "does NOT cover other second-level domains",
    }


def preview_fix_template(bucket: str, endpoint: str,
                         creation_date: str = "") -> dict:
    """Preview-vs-download fix checklist. Text output only.

    creation_date (the bucket's ISO-8601 date from GetBucketInfo) drives
    the image forced-download note (0048 family, DAL-2): buckets created
    after the 2019-09 cutoffs force-download the 12 image MIME types over
    the default domain, so "images preview normally on the default
    domain" only holds for older buckets."""
    if image_force_download_cutoff(creation_date):
        image_note = (
            "This bucket was created after (or unknown relative to) the "
            "2019-09 image forced-download cutoffs (earliest 2019-09-23 "
            "17:00 Beijing time, region-dependent up to 2019-09-30; EC "
            "0048-00000100-00000105): the 12 image MIME types (jpeg, gif, "
            "tiff, png, webp, svg+xml, bmp, x-ms-bmp, x-cmu-raster, exr, "
            "x-icon, heic) are force-downloaded over the default domain "
            "with 'x-oss-force-download: true' -- image preview on such "
            "buckets requires a bound custom domain, and setting "
            "Content-Disposition: inline on the object does NOT take "
            "effect.")
    else:
        image_note = (
            "This bucket predates the 2019-09 image forced-download "
            "cutoffs, so images with a correct Content-Type still preview "
            "over the default domain; if they download anyway, check the "
            "object's Content-Disposition / Content-Type first.")
    return {
        "checklist": [
            "Object Content-Type must be the real MIME type (image/jpeg, "
            "application/pdf, video/mp4 ...), NOT "
            "application/octet-stream -- octet-stream always downloads.",
            "Object Content-Disposition must be 'inline' (or absent); an "
            "object uploaded with 'attachment' always downloads regardless "
            "of Content-Type.",
            "OSS DEFAULT domains (*.aliyuncs.com) force attachment "
            "downloads for browser-renderable text types (HTML/JS/CSS/"
            "JSON/...; EC 0048-00000001 for buckets created after "
            "2017-10-01) as a security policy -- for those types, preview "
            "only works through a bound custom domain.",
            image_note,
            "A response header 'x-oss-force-download: true' proves OSS "
            "itself injected the download (0048 error-code family) rather "
            "than the object metadata being wrong.",
            "Private buckets deny anonymous GET (403): preview via a "
            "presigned GET URL or public-read object ACL; the 403 itself "
            "is the diagnosis, not a network fault.",
        ],
        "custom_domain_access":
            f"https://<your-domain>/<object-key> after binding the domain "
            f"to bucket '{bucket or '<bucket>'}' and pointing a CNAME "
            f"record to {bucket or '<bucket>'}.{endpoint or '<region>.aliyuncs.com'}",
        "content_disposition_fix":
            "Set the object meta Content-Disposition: inline when "
            "re-uploading, or update the object's HTTP headers in the "
            "console (manual operation -- this skill is read-only)",
    }


def fuse_doc_hits(recommendations, doc_verification) -> list:
    """Fuse high-relevance official-doc hits into the recommendations so
    the doc-verification evidence reaches the conclusion instead of
    running in parallel with it (DAL-7). Pass-through when the lookup did
    not match."""
    recs = list(recommendations or [])
    if not doc_verification or not doc_verification.get("matched"):
        return recs
    docs = doc_verification.get("docs") or []
    ec0048 = [d for d in docs if "0048-" in (d.get("url") or "")]
    if ec0048:
        top = ec0048[0]
        recs.append(
            "OFFICIAL-DOC VERIFICATION (fused): the help-center lookup hit "
            f"the 0048 forced-download error-code family "
            f"('{top.get('title')}', {top.get('url')}), which matches the "
            "reported symptom: over the OSS default domain, HTML is "
            "force-downloaded for buckets created after 2017-10-01 "
            "(0048-00000001), the 12 image MIME types for buckets created "
            "after the 2019-09 cutoffs (0048-00000100-00000105), "
            "transfer-acceleration-domain files (0048-00000106-00000112), "
            "new-user default-domain files after 2022-10-09 "
            "(0048-00000113) and APK/IPA files (0048-00000200-00000203); "
            "the fix is serving through a bound custom domain. "
            "Cross-check the probe/referer findings above against this "
            "official doc.")
    elif docs:
        top = docs[0]
        recs.append(
            "OFFICIAL-DOC VERIFICATION (fused): the help-center lookup hit "
            f"'{top.get('title')}' ({top.get('url')}); cross-check the "
            "diagnosis above against this official doc when advising the "
            "customer.")
    return recs


assert fuse_doc_hits([], None) == []  # invalid: no lookup
assert fuse_doc_hits([], {"matched": False, "docs": []}) == []  # unmatched
_DV_0048 = {"matched": True, "docs": [
    {"title": "0048-00000100",
     "url": "https://help.aliyun.com/zh/oss/user-guide/0048-00000100.md"}]}
assert any("0048" in r for r in fuse_doc_hits(["x"], _DV_0048))  # normal: EC family fused
_DV_PLAIN = {"matched": True, "docs": [
    {"title": "防盗链",
     "url": "https://help.aliyun.com/zh/oss/user-guide/hotlink-protection.md"}]}
assert any("防盗链" in r for r in fuse_doc_hits([], _DV_PLAIN))  # normal: generic fuse


def domain_binding_template(bucket: str, endpoint: str,
                            location: str) -> dict:
    """Custom-domain binding checklist (CNAME + ICP filing + certificate).
    Knowledge guidance only; binding stays a manual user operation."""
    filing = icp_filing_required(location)
    return {
        "steps": [
            "OSS console -> Bucket -> Transport Configuration -> Bind "
            "Custom Domain (Bucket Domain): add the domain first.",
            "Add a CNAME DNS record: <your-subdomain> -> "
            f"{bucket or '<bucket>'}.{endpoint or '<region>.aliyuncs.com'}"
            " (do NOT use an A record; keep only ONE CNAME for the host).",
            "Complete domain ownership verification if the console asks "
            "for it (add the TXT record it displays, e.g. "
            "_dnsauth.<your-subdomain>).",
        ],
        "icp_filing": (
            "ICP filing (bei'an) is REQUIRED before binding: the bucket is "
            "located in mainland China, and domains without "
            "a valid ICP filing are rejected at binding time. If the "
            "console says 'not filed' while you believe it is filed, "
            "verify the filing status belongs to THIS domain spelling and "
            "has been synced to the MIIT database, then retry."
            if filing else
            "This bucket's region is outside mainland China, so ICP filing "
            "is not enforced for the bound domain; if a filing message "
            "still appears, confirm the bucket region and retry."),
        "certificate":
            "HTTPS access through the custom domain needs a certificate "
            "for that exact domain (wildcards cover subdomains only); "
            "upload/host the certificate in the OSS domain-binding page "
            "or via the certificate service -- manual operation.",
        "common_failures": [
            "'domain already filed but cannot bind': filing record not "
            "synced, or the domain is bound/occupied by another bucket "
            "or another Alibaba Cloud product account.",
            "binding OK but access 404/does not resolve: CNAME record "
            "missing, conflicting A record, or DNS TTL not expired.",
            "HTTPS certificate errors: cert domain mismatch or expired "
            "certificate.",
        ],
    }


assert "AllowEmptyReferer" in referer_rule_template("")["xml"]  # normal
assert "*.a.com" in referer_rule_template("a.com")["xml"]  # boundary: domain entry
assert "inline" in preview_fix_template("b", "oss-cn-hangzhou.aliyuncs.com")["checklist"][1]  # normal
assert any("2019-09" in c for c in
           preview_fix_template("b", "e")["checklist"])  # boundary: unknown date -> conservative
assert any("predates" in c for c in preview_fix_template(
    "b", "e", "2015-01-01T00:00:00.000Z")["checklist"])  # normal: old bucket note
assert "ICP" in domain_binding_template("b", "oss-cn-hangzhou.aliyuncs.com", "oss-cn-hangzhou")["icp_filing"]  # normal
assert "not enforced" in domain_binding_template("b", "oss-ap-southeast-1.aliyuncs.com", "oss-ap-southeast-1")["icp_filing"]  # boundary: overseas


def build_recommendations(referer, cnames_result, website, bucket_info,
                          page_referer: str, domain: str) -> list:
    """Evidence-based findings combining referer / domain / website state."""
    recs = []
    acl = (bucket_info or {}).get("acl", "")
    location = (bucket_info or {}).get("location", "")

    # -- referer / hotlink protection --
    if referer is None:
        recs.append(
            "Hotlink-protection (referer) configuration could not be read "
            "(see recorded errors); grant oss:GetBucketReferer per "
            "references/ram-policies.md and re-run, or check the bucket's "
            "Hotlink Protection page in the OSS console manually.")
    elif not (referer.get("referers") or referer.get("black_referers")):
        recs.append(
            "Hotlink protection is NOT configured (GetBucketReferer "
            "returned an empty whitelist AND an empty blacklist with "
            f"allow_empty_referer={referer.get('allow_empty_referer')}): "
            "every referer is currently allowed, so referer rules cannot "
            "be the cause of any 403 right now. If protection is desired, "
            "apply the referer template from this report manually.")
    else:
        verdict = referer_verdict(referer, page_referer)
        if verdict == "allowed" and (page_referer or "").strip():
            recs.append(
                "The referer rules are configured and the provided page "
                "referer passes them (no blacklist hit, whitelist match); "
                "a persistent 403 then points at bucket ACL/permission or "
                "the EC 0003-00000005 causes instead of hotlink "
                "protection.")
        elif verdict == "allowed":
            recs.append(
                "Hotlink rules currently allow requests without a Referer "
                f"(allow_empty_referer={referer.get('allow_empty_referer')})"
                "; the blacklist (if any) is only consulted for non-empty "
                "referers. To attribute a specific 403, re-run with "
                "--page-referer set to the embedding page URL.")
        elif verdict == "denied_empty":
            recs.append(
                "REFERER FALSE POSITIVE ATTRIBUTED: allow_empty_referer is "
                "false and the request carries no Referer (direct "
                "address-bar access, mobile app/WebView, or a proxy "
                "stripping Referer). Whitelisting cannot fix empty-referer "
                "clients -- either set AllowEmptyReferer=true manually or "
                "accept that such clients are blocked.")
        elif verdict == "denied_blacklist":
            recs.append(
                "REFERER BLACKLIST ATTRIBUTED: the page referer "
                f"'{page_referer}' matches a blacklist entry "
                f"{referer.get('black_referers')} -- the blacklist OUTRANKS "
                "the whitelist (official check order: empty-referer -> "
                "blacklist -> whitelist), so even a whitelisted page is "
                "denied. Remove or narrow the matching blacklist entry "
                "manually (entries support * and ? wildcards; "
                "allow_truncate_query_string="
                f"{referer.get('allow_truncate_query_string')} controls "
                "whether the query string is truncated before matching).")
        elif verdict == "denied_mismatch":
            recs.append(
                f"REFERER FALSE POSITIVE ATTRIBUTED: the page referer "
                f"'{page_referer}' matches no whitelist entry "
                f"{referer.get('referers')} (and no blacklist entry). Add "
                "a matching entry (* and ? wildcards supported) manually "
                "per the template.")
        else:
            recs.append(
                "The referer rules are configured; re-run with "
                "--page-referer set to the embedding page URL to attribute "
                "a specific 403.")

    # -- custom domain binding --
    if cnames_result is None:
        recs.append(
            "Custom-domain (cname) list could not be read (see recorded "
            "errors); grant oss:ListBucketCname and re-run.")
    elif not cnames_result.get("cnames"):
        recs.append(
            "NO custom domain is bound to this bucket (ListBucketCname "
            "returned an empty list). Access currently works only through "
            "the OSS default domain, which carries the forced-download "
            "policy for renderable text types. To bind one, follow the "
            "domain_binding template (add domain -> CNAME record -> "
            "ownership verification -> ICP filing check -> certificate "
            "for HTTPS); binding is a manual console operation.")
    else:
        bound = [c.get("domain", "") for c in cnames_result.get("cnames")]
        if domain and not domain_bound(domain, cnames_result.get("cnames")):
            recs.append(
                f"The custom domain '{domain}' is NOT among the bound "
                f"cnames {bound}: binding has not taken effect. Check the "
                "domain_binding template failure list (ICP filing sync, "
                "occupied by another bucket, CNAME record).")
        elif domain:
            recs.append(
                f"The custom domain '{domain}' IS bound to this bucket; "
                "if access still fails, verify the CNAME DNS record and "
                "the HTTPS certificate for this exact domain.")
        else:
            recs.append(
                f"Bound custom domains: {', '.join(bound)}. Re-run with "
                "--domain to verify a specific domain's binding state.")

    # -- static website hosting (context / boundary marker) --
    if website is not None:
        if website.get("configured"):
            recs.append(
                "Static website hosting IS configured (index: "
                f"{website.get('index_file')}, error: "
                f"{website.get('error_file')}). Index/404 page rule "
                "questions belong to the static-website scope (sibling "
                "endpoint-internal skill); this skill only reports the "
                "state as context.")
        else:
            recs.append(
                "Static website hosting is NOT configured "
                "(GetBucketWebsite returned NoSuchWebsiteConfiguration). "
                "This is a configuration state, not an error; index/404 "
                "hosting rules are out of this skill's scope.")
    return recs


assert isinstance(build_recommendations(None, None, None, {}, "", ""), list)  # all degraded
assert any("NOT configured (GetBucketReferer" in r for r in build_recommendations(
    {"allow_empty_referer": True, "referers": []}, {"cnames": []},
    {"configured": False}, {"acl": "private", "location": "oss-cn-hangzhou"}, "", ""))  # real-bucket semantics
assert any("NOT configured (GetBucketReferer" in r for r in build_recommendations(
    {"allow_empty_referer": True, "referers": [], "black_referers": []},
    {"cnames": []}, None, {}, "", ""))  # boundary: empty black+white lists
assert any("FALSE POSITIVE" in r for r in build_recommendations(
    _CFG_STRICT, {"cnames": []}, None, {}, "", ""))  # denied_empty
assert any("BLACKLIST" in r for r in build_recommendations(
    {"allow_empty_referer": True, "referers": ["*"],
     "black_referers": ["*bad.example"]}, {"cnames": []}, None, {},
    "http://bad.example/x", ""))  # normal: blacklist attribution (DAL-3)
assert any("NOT among the bound" in r for r in build_recommendations(
    _CFG_EMPTY, {"cnames": _CNAMES_A}, None, {}, "", "cdn.other.com"))  # domain unbound


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
    """Print the structured report + STATUS/NEXT_ACTION contract lines.
    When the doc lookup matched, its hits are ALSO fused into the
    recommendations (DAL-7) so the official evidence reaches the
    conclusion instead of running in parallel with it."""
    report["status"] = status
    report["next_action"] = next_action
    dv = _doc_verification(status)
    if dv is not None:
        report["doc_verification"] = dv
        report["recommendations"] = fuse_doc_hits(
            report.get("recommendations"), dv)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"STATUS: {status}")
    print(f"NEXT_ACTION: {next_action}")
    return 0 if status in ("OK", "DEGRADED") else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose OSS direct-access links: preview-turns-"
                    "download attribution, custom domain binding check, "
                    "referer hotlink-protection false positives "
                    "(read-only; outputs templates, never writes "
                    "configuration)",
    )
    parser.add_argument("--bucket", default="", required=False,
                        help="OSS bucket name to diagnose (required; when absent the script emits FAIL and asks)")
    parser.add_argument("--object", default="",
                        help="Object key to probe anonymously over the "
                             "default domain (optional; enables the "
                             "preview-vs-download probe, no credentials "
                             "needed)")
    parser.add_argument("--domain", default="",
                        help="Custom domain to check against the bucket's "
                             "bound cname list (optional)")
    parser.add_argument("--page-referer", default="",
                        help="The Referer header value of the embedding "
                             "page (optional; used to attribute referer "
                             "false positives)")
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
            "skill": globals().get("_SKILL_NAME", "alibabacloud-oss-direct-access-link-diagnosis"),
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
    domain = normalize_domain(args.domain)

    report = {
        "skill": "alibabacloud-oss-direct-access-link-diagnosis",
        "bucket": args.bucket,
        "object": normalize_object_key(args.object) or None,
        "domain": domain or None,
        "identity": {"uid": "",
                     "note": "derived via sts get-caller-identity; empty "
                             "means the identity pre-check degraded"},
        "query_endpoint": "",
        "auto_filled": auto_filled,
        "bucket_info": None,
        "referer": None,
        "website": None,
        "cnames": None,
        "probe": None,
        "recommendations": [],
        "templates": {
            "referer_rule": referer_rule_template(domain),
            "preview_fix": preview_fix_template(args.bucket, ""),
            "domain_binding": domain_binding_template(args.bucket, "", ""),
        },
        "errors": [],
    }

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
    # DAL-6: an internal endpoint is unreachable from the public network;
    # cap the metadata attempt at a short connect timeout so a
    # public-network run fails over to the ListBuckets fallback in
    # seconds instead of hanging on 30s connect timeouts stacked with
    # SDK-internal retries (measured 121.7s before this guard).
    _info_timeout = _oss_client._DEFAULT_TIMEOUT
    if "-internal." in endpoint:
        _info_timeout = 5
        auto_filled.append(
            f"internal endpoint '{endpoint}' detected: reachable only "
            "inside the Alibaba Cloud network of that region; a short 5s "
            "connect timeout is applied to the metadata attempt so a "
            "public-network run falls back to ListBuckets quickly (if "
            "this host is an ECS instance in the same region, keep the "
            "internal endpoint)")
        print(f"[WARN] internal endpoint '{endpoint}' is only reachable "
              "inside the Alibaba Cloud network; applying a short 5s "
              "connect timeout to the metadata attempt",
              file=sys.stderr)
    report["query_endpoint"] = endpoint
    report["templates"]["preview_fix"] = preview_fix_template(
        args.bucket, endpoint)

    # Step 3: GetBucketInfo -- existence + metadata evidence.
    bucket_info = None
    try:
        bucket_info = _oss_client.get_bucket_info(
            args.bucket, endpoint, timeout=_info_timeout)
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
        # Degraded before the configuration checks -- attribute root error.
        root = report["errors"][0] if report["errors"] else {"category": "unknown"}
        cat = root.get("category", "unknown")
        report["recommendations"] = [
            "Direct-access configuration could not be read because the "
            "bucket metadata query failed; the standard templates in this "
            "report are still valid for manual application once access is "
            "restored."]
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
                "oss:GetBucketReferer / oss:GetBucketWebsite / "
                "oss:ListBucketCname (see references/ram-policies.md) or "
                "confirm the bucket belongs to this account, then re-run.")
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

    # Templates can now carry the real location (ICP-filing guidance)
    # and the real creation date (image forced-download cutoff note).
    location = bucket_info.get("location", "")
    report["templates"]["domain_binding"] = domain_binding_template(
        args.bucket, endpoint, location)
    report["templates"]["preview_fix"] = preview_fix_template(
        args.bucket, endpoint, bucket_info.get("creation_date", ""))

    # Step 4: GetBucketReferer -- hotlink protection evidence.
    try:
        report["referer"] = _oss_client.get_bucket_referer(
            args.bucket, endpoint)
    except OssClientError as e:
        print(f"[WARN] GetBucketReferer degraded ({e.category}): {e}",
              file=sys.stderr)
        report["errors"].append(e.to_dict())

    # Step 5: GetBucketWebsite -- hosting state as context/boundary marker
    # (NoSuchWebsiteConfiguration maps to configured=False, NOT an error).
    try:
        report["website"] = _oss_client.get_bucket_website(
            args.bucket, endpoint)
    except OssClientError as e:
        print(f"[WARN] GetBucketWebsite degraded ({e.category}): {e}",
              file=sys.stderr)
        report["errors"].append(e.to_dict())

    # Step 6: ListBucketCname -- custom domain binding evidence.
    try:
        report["cnames"] = _oss_client.list_bucket_cname(
            args.bucket, endpoint)
    except OssClientError as e:
        print(f"[WARN] ListBucketCname degraded ({e.category}): {e}",
              file=sys.stderr)
        report["errors"].append(e.to_dict())

    # Step 7: optional ANONYMOUS probe (no credentials) for preview vs
    # download attribution against the default domain.
    if report["object"]:
        probe = probe_default_domain(args.bucket, endpoint, report["object"])
        acl = bucket_info.get("acl", "")
        analysis = classify_probe(
            probe.get("status", 0), probe.get("content_type", ""),
            probe.get("content_disposition", ""), acl,
            x_oss_force_download=probe.get("x_oss_force_download", ""))
        # EC 0003-00000005 bisection (DAL-1): an anonymous 403 on a
        # NON-private bucket is attributed in the fixed order
        # referer rules -> cause-1 object private ACL -> cause-2 platform
        # block, ported from the internal CSE SOP (see
        # references/ec-0003-00000005-bisection.md).
        if probe.get("status") == 403 and (acl or "").lower() != "private":
            object_acl_state = None
            try:
                object_acl_state = _oss_client.get_object_acl(
                    args.bucket, report["object"], endpoint)
            except OssClientError as e:
                print(f"[WARN] GetObjectAcl degraded ({e.category}): {e}",
                      file=sys.stderr)
                report["errors"].append(e.to_dict())
            probe_referer_verdict = (
                referer_verdict(report["referer"], "")
                if report["referer"] is not None else "not_configured")
            analysis = ec_0003_00000005_bisection(
                acl, object_acl_state,
                probe_referer_verdict.startswith("denied"))
            if object_acl_state is not None:
                analysis["object_acl"] = object_acl_state.get("acl", "")
        probe["analysis"] = analysis
        report["probe"] = probe

    # Step 8: verdict + recommendations + template guidance.
    report["recommendations"] = build_recommendations(
        report["referer"], report["cnames"], report["website"],
        bucket_info, args.page_referer, domain)

    # DAL-5: out-of-scope referral guard -- CDN origin / cross-account RAM
    # / presigned URL / transfer-acceleration signals LEAD with a referral
    # to the sibling skill that owns them instead of a generic "diagnosis
    # complete" conclusion; the bucket evidence stays as context.
    guard_hits = domain_transfer_guard(args.question)
    if guard_hits:
        referral = guard_hits[0]
        report["recommendations"].insert(0, (
            "OUT-OF-SCOPE REFERRAL: the reported question matches "
            f"{referral['reason']}, which belongs to the sibling skill "
            f"'{referral['skill']}' -- this skill only covers "
            "direct-access links (preview-vs-download attribution, custom "
            "domain binding, referer false positives). Relay the "
            "referral; the bucket evidence in this report is context "
            "only, not the answer to the question."))

    # Step 9: status + next action.
    core_degraded = (report["referer"] is None and
                     report["cnames"] is None and
                     report["website"] is None)
    if core_degraded:
        next_action = (
            "All configuration queries failed (see recorded errors); grant "
            "the read-only actions in references/ram-policies.md or fix "
            "network access, then re-run. The templates in this report "
            "remain valid for manual application.")
        sys.exit(_emit(report, "DEGRADED", next_action))

    hint = scenario_hint(args.question)
    if guard_hits:
        referral = guard_hits[0]
        next_action = (
            f"The question matches {referral['reason']} -- defer it to "
            f"the sibling skill '{referral['skill']}' (direct-access "
            "diagnosis does not answer it); the bucket evidence in this "
            "report is context only.")
    elif report["probe"] is not None:
        verdict = report["probe"]["analysis"]["verdict"]
        if verdict == "private_bucket_403":
            next_action = (
                "The anonymous probe got 403 on a private bucket: preview "
                "requires a presigned GET URL or public-read object ACL; "
                "the 403 is expected behavior, not a network fault.")
        elif verdict == "referer_denied_403":
            next_action = (
                "The anonymous 403 is denied by hotlink rules "
                "(allow_empty_referer=false with a non-empty whitelist): "
                "apply the referer template manually (AllowEmptyReferer "
                "or a matching entry) per M3 BEFORE considering the EC "
                "0003-00000005 causes, then re-probe.")
        elif verdict == "object_acl_private_403":
            next_action = (
                "EC 0003-00000005 cause-1 CONFIRMED: the object carries "
                "its own private ACL on a public-read bucket -- reset it "
                "to inherit the bucket ACL manually (ossutil set-acl "
                "oss://<BUCKET>/<OBJECT_KEY> default; add -r for a batch "
                "of affected objects), then re-test the link.")
        elif verdict == "unattributed_403":
            next_action = (
                "EC 0003-00000005 UNATTRIBUTED (object ACL is not private "
                "and hotlink rules pass): first check whether Block Public "
                "Access is enabled on the bucket/account (official 问题示例 "
                "paragraph 2); if not, escalate through the "
                "violation-handling channel -- the official page documents "
                "the no-read-permission / AK-or-signature-incorrect / "
                "Block-Public-Access causes (see "
                "references/ec-0003-00000005-bisection.md).")
        elif verdict == "object_acl_unverifiable":
            next_action = (
                "Object ACL could not be read (grant oss:GetObjectAcl per "
                "references/ram-policies.md and re-run): on this "
                "public-read bucket the leading hypothesis is cause-1 "
                "(object private ACL); only after it is excluded check "
                "Block Public Access and then treat the 403 as "
                "unattributed and escalate.")
        elif verdict in ("forced_download", "content_type_misconfig"):
            next_action = (
                "Preview-turns-download attributed: follow the preview_fix "
                "checklist (Content-Disposition: inline + correct "
                "Content-Type, or bind a custom domain to leave the "
                "default-domain forced-download policy); all fixes are "
                "manual operations.")
        elif verdict == "http_error":
            next_action = (
                "The anonymous probe returned an error status without an "
                "attributable EC 0003-00000005 cause; review the recorded "
                "errors and recommendations, then re-run with credentials "
                "that can read the object ACL.")
        else:
            next_action = (
                "The probed object is previewable over the default domain; "
                "for renderable text types (HTML/JS/CSS) and images on "
                "post-2019-09 buckets remember the default-domain "
                "forced-download policy (0048 EC family) and prefer a "
                "bound custom domain.")
    elif domain and report["cnames"] is not None and not domain_bound(
            domain, report["cnames"].get("cnames")):
        next_action = (
            f"Custom domain '{domain}' is not bound to bucket "
            f"'{args.bucket}': follow the domain_binding template (ICP "
            "filing sync / occupied-domain / CNAME record failure list) "
            "and retry binding manually in the console.")
    elif report["referer"] is not None and not (
            report["referer"].get("referers")
            or report["referer"].get("black_referers")):
        if hint:
            next_action = (
                "Diagnosis complete: hotlink protection is not configured "
                "and no custom domain is bound (see recommendations); for "
                "the reported scenario: " + hint + ".")
        else:
            next_action = (
                "Diagnosis complete: hotlink protection is not configured, no "
                "custom domain is bound (see recommendations); current 403s "
                "cannot come from referer rules. Apply the referer / domain "
                "templates manually if protection or a custom domain is "
                "desired.")
    else:
        if hint:
            next_action = (
                "Diagnosis complete; relay the evidence-based "
                "recommendations (referer verdict, domain binding state, "
                "hosting state) and the templates as manual guidance; for "
                "the reported scenario: " + hint + ".")
        else:
            next_action = (
                "Diagnosis complete; relay the evidence-based recommendations "
                "(referer verdict, domain binding state, hosting state) and "
                "the templates as manual guidance.")
    sys.exit(_emit(report, "OK", next_action))


if __name__ == "__main__":
    sys.exit(main())
