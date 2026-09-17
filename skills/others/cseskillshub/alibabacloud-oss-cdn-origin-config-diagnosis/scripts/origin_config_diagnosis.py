#!/usr/bin/env python3
"""
origin_config_diagnosis.py -- CDN back-to-origin (OSS) configuration diagnosis
===============================================================================
READ-ONLY cross-product diagnosis covering:
  1. Back-to-origin 403 attribution   -- private origin bucket detected but
     no origin authorization can be confirmed (guidance only)
  2. Traffic bypassing CDN            -- user-reported origin host points at
     an OSS endpoint directly, or does not match the configured origin
  3. Origin host / port configuration -- set_req_host_header vs the origin
     content, origin port sanity
  4. Domain state branches            -- domain offline / not configured /
     not found under this account

Channels (measured, finalized):
  * CDN control plane -> aliyun CLI plugin mode (lowercase-hyphenated):
      aliyun cdn describe-user-domains
      aliyun cdn describe-cdn-domain-detail   --domain-name <d>
      aliyun cdn describe-cdn-domain-configs  --domain-name <d> \
             --function-names set_req_host_header
  * OSS origin-bucket cross-check -> Python oss2 SDK (GetBucketInfo)
  * Caller identity -> aliyun sts get-caller-identity (via _oss_client)

Auth: credentials always come from the aliyun CLI default credential chain
(CDN/STS calls) and the ALIBABA_CLOUD_* environment variables (oss2 SDK).
This script performs no explicit credential handling and never mutates
anything.

Exit-code contract (unified with the sibling OSS skills, F-2): OK and
DEGRADED both exit 0 ("a conclusion was produced successfully"); exit 1
is reserved for FAIL cases where no diagnosis can run (invalid --domain
input, aliyun CLI missing). Documented in SKILL.md "Error Handling".

Usage:
  python3 origin_config_diagnosis.py --domain test234.pier39.cn
  python3 origin_config_diagnosis.py --domain d.example.com \
      --user-origin-host b.oss-cn-hangzhou.aliyuncs.com
  python3 origin_config_diagnosis.py --domain d.example.com --json
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

import _oss_client
import _doc_lookup

_SKILL_NAME = "alibabacloud-oss-cdn-origin-config-diagnosis"
_CLI_TIMEOUT = 60  # seconds, applied to every single aliyun CLI call

# Measured shape of an OSS bucket endpoint host: <bucket>.oss-<region>.aliyuncs.com
_OSS_HOST_RE = re.compile(r"^(?P<bucket>[a-z0-9][a-z0-9-]{1,61}[a-z0-9])\."
                          r"(?P<endpoint>oss-[a-z0-9-]+\.aliyuncs\.com)$")

# Special (non-region) OSS endpoint forms that also match _OSS_HOST_RE:
#   * transfer acceleration  -- oss-accelerate[-overseas].aliyuncs.com
#     (official: help.aliyun.com/zh/oss/user-guide/access-oss-via-bucket-domain-name,
#      "transfer-acceleration domain" section; CDN back-to-origin to the
#      accelerate endpoint is an official dual-acceleration architecture,
#      help.aliyun.com/zh/oss/user-guide/transfer-acceleration,
#      best practice "CDN + transfer acceleration: multi-layer architecture")
#   * internal               -- oss-<region>-internal.aliyuncs.com
#     (official: same page, "internal access domain" section -- same-region
#      Alibaba Cloud intranet clients (e.g. ECS) only,
#      reachable via internal VIP segments; public CDN edge nodes cannot
#      route to it, so it never works as a CDN origin)
_ACCELERATE_ENDPOINT_RE = re.compile(r"^oss-accelerate(-overseas)?\.aliyuncs\.com$")
_INTERNAL_ENDPOINT_RE = re.compile(r"^oss-[a-z0-9-]+-internal\.aliyuncs\.com$")


def classify_oss_endpoint(endpoint: str) -> str:
    """Classify an OSS endpoint host: 'accelerate' | 'internal' | 'public'.

    Region comparison in _attribute_bucket only applies to 'public'
    (oss-<region>.aliyuncs.com) endpoints; accelerate endpoints carry no
    region and internal endpoints carry a region but are unreachable for
    CDN back-to-origin.
    """
    ep = (endpoint or "").strip().lower()
    if _ACCELERATE_ENDPOINT_RE.match(ep):
        return "accelerate"
    if _INTERNAL_ENDPOINT_RE.match(ep):
        return "internal"
    return "public"

_USER_AGENT = _oss_client.user_agent  # resolved lazily per call (session-id)


# ---------------------------------------------------------------------------
# CLI backend (aliyun CLI plugin mode -- one interceptable path for CDN/STS)
# ---------------------------------------------------------------------------

def _parse_cli_error(stdout: str, stderr: str) -> Tuple[str, str]:
    """Extract (Code, Message) from aliyun CLI error output (JSON or plain)."""
    for text in (stdout, stderr):
        if not text:
            continue
        # The CLI may wrap the JSON payload after a "Data: " prefix or in a
        # multi-line SDKError block; try any embedded JSON object.
        candidates = [text]
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            candidates.append(m.group(0))
        for cand in candidates:
            try:
                data = json.loads(cand)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(data, dict) and data.get("Code"):
                return str(data["Code"]), str(data.get("Message", ""))
    detail = (stderr or stdout or "").strip()
    detail = re.sub(r"\s+", " ", detail)
    return "CliError", detail[:300]


def _run_cli(args: List[str]) -> Dict[str, Any]:
    """Run an aliyun CLI command (argument list, never shell) with timeout.

    Raises RuntimeError("<Code>: <Message>") on any failure so the caller can
    record the error and degrade gracefully with [WARN] + STATUS: DEGRADED.
    """
    cmd = ["aliyun"] + args + ["--user-agent", _USER_AGENT()]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=_CLI_TIMEOUT, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise RuntimeError("CliError: aliyun CLI request timed out after "
                           f"{_CLI_TIMEOUT}s")
    except FileNotFoundError:
        raise RuntimeError("CliError: aliyun CLI not found on PATH")
    if proc.returncode != 0:
        code, message = _parse_cli_error(proc.stdout, proc.stderr)
        raise RuntimeError(f"{code}: {message}")
    try:
        result = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        raise RuntimeError("CliError: unparseable response from aliyun CLI")
    if isinstance(result, dict) and result.get("Code"):
        raise RuntimeError(f"{result['Code']}: {result.get('Message', '')}")
    return result


def cdn_describe_user_domains(page_size: int = 50) -> Dict[str, Any]:
    """`aliyun cdn describe-user-domains` -- list the caller's CDN domains.

    Returns {'total_count', 'domains': [{domain_name, domain_status,
    sources: [{content, type, port, priority, weight}]}]}.
    """
    result = _run_cli(["cdn", "describe-user-domains",
                       "--page-size", str(page_size)])
    domains: List[Dict[str, Any]] = []
    for p in (result.get("Domains") or {}).get("PageData") or []:
        sources = []
        for s in (p.get("Sources") or {}).get("Source") or []:
            sources.append({
                "content": s.get("Content", ""),
                "type": s.get("Type", ""),
                "port": s.get("Port", 0),
                "priority": s.get("Priority", ""),
                "weight": s.get("Weight", ""),
            })
        domains.append({
            "domain_name": p.get("DomainName", ""),
            "domain_status": p.get("DomainStatus", ""),
            "sources": sources,
        })
    return {"total_count": result.get("TotalCount", len(domains)),
            "domains": domains}


def cdn_describe_domain_detail(domain: str) -> Dict[str, Any]:
    """`aliyun cdn describe-cdn-domain-detail --domain-name <d>` (measured)."""
    result = _run_cli(["cdn", "describe-cdn-domain-detail",
                       "--domain-name", domain])
    m = result.get("GetDomainDetailModel") or {}
    sources = []
    for s in (m.get("SourceModels") or {}).get("SourceModel") or []:
        sources.append({
            "content": s.get("Content", ""),
            "enabled": s.get("Enabled", ""),
            "type": s.get("Type", ""),
            "port": s.get("Port", 0),
            "priority": s.get("Priority", ""),
            "weight": s.get("Weight", ""),
        })
    return {
        "domain_name": m.get("DomainName", domain),
        "domain_status": m.get("DomainStatus", ""),
        "cname": m.get("Cname", ""),
        "gmt_created": m.get("GmtCreated", ""),
        "gmt_modified": m.get("GmtModified", ""),
        "sources": sources,
    }


def cdn_describe_origin_host_config(domain: str) -> Dict[str, Any]:
    """`aliyun cdn describe-cdn-domain-configs --domain-name <d>
    --function-names set_req_host_header` (measured).

    Returns {'configured': bool, 'origin_host': str|None, 'status': str,
    'config_id': int|None}.
    """
    result = _run_cli(["cdn", "describe-cdn-domain-configs",
                       "--domain-name", domain,
                       "--function-names", "set_req_host_header"])
    configs = (result.get("DomainConfigs") or {}).get("DomainConfig") or []
    for cfg in configs:
        if cfg.get("FunctionName") != "set_req_host_header":
            continue
        host = None
        for arg in (cfg.get("FunctionArgs") or {}).get("FunctionArg") or []:
            if arg.get("ArgName") == "domain_name":
                host = arg.get("ArgValue") or None
        return {"configured": True, "origin_host": host,
                "status": cfg.get("Status", ""),
                "config_id": cfg.get("ConfigId")}
    return {"configured": False, "origin_host": None, "status": "",
            "config_id": None}


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def parse_oss_origin_host(host: str) -> Optional[Dict[str, str]]:
    """Split '<bucket>.oss-<region>.aliyuncs.com' into bucket + endpoint.

    Returns {'bucket': ..., 'endpoint': ...} or None when the host is not an
    OSS endpoint host (ipaddr / third-party domain origins).
    """
    if not host:
        return None
    m = _OSS_HOST_RE.match(host.strip().lower())
    if not m:
        return None
    return {"bucket": m.group("bucket"), "endpoint": m.group("endpoint")}


def diagnose(domain: str, user_origin_host: Optional[str], uid: str,
             verbose: bool = True) -> Dict[str, Any]:
    """Run the full read-only diagnosis. Never raises on API errors -- every
    failure is recorded in `errors`, logged as [WARN] on stderr, and the
    report is still emitted with STATUS: DEGRADED."""

    def log(msg: str = "") -> None:
        if verbose:
            print(msg, flush=True)

    findings: List[Dict[str, str]] = []
    recommendations: List[str] = []
    errors: List[Dict[str, Any]] = []
    evidence: Dict[str, Any] = {}

    def warn(category: str, message: str, hint: str = "") -> None:
        errors.append({"category": category, "message": message,
                       "hint": hint})
        print(f"[WARN] {category}: {message}", file=sys.stderr)

    def add(code: str, severity: str, detail: str) -> None:
        findings.append({"code": code, "severity": severity,
                         "detail": detail})

    log("=" * 70)
    log("CDN back-to-origin (OSS) configuration diagnosis -- READ-ONLY")
    log("=" * 70)
    log(f"  Accelerated domain : {domain}")
    log(f"  Caller UID         : {uid or '(not derived)'}")
    if user_origin_host:
        log(f"  User-reported origin host: {user_origin_host}")

    # ---------------- Step 1: CDN domain detail ----------------
    log("\n[Step 1] Query CDN domain detail "
        "(aliyun cdn describe-cdn-domain-detail)")
    detail: Optional[Dict[str, Any]] = None
    domain_found = True
    try:
        detail = cdn_describe_domain_detail(domain)
        evidence["domain_detail"] = detail
        log(f"  DomainStatus : {detail['domain_status']}")
        log(f"  Cname        : {detail['cname']}")
        for s in detail["sources"]:
            log(f"  Origin       : {s['content']} "
                f"(Type={s['type']}, Port={s['port']}, "
                f"Priority={s['priority']}, Enabled={s['enabled']})")
    except RuntimeError as e:
        msg = str(e)
        if "InvalidDomain.NotFound" in msg:
            domain_found = False
            warn("domain_not_found", msg,
                 "The domain is not configured on CDN under this account.")
            add("DOMAIN_NOT_FOUND", "high",
                f"DescribeCdnDomainDetail returned InvalidDomain.NotFound "
                f"for '{domain}': the domain is not configured on CDN under "
                f"the current account, has been deleted, or belongs to "
                f"another account.")
            recommendations.append(
                "Verify the accelerated domain spelling and the account "
                "UID; if the domain was never added to CDN, this symptom is "
                "explained by 'domain not configured' -- add the domain and "
                "complete CNAME setup before back-to-origin can work.")
        else:
            warn("cdn_api_error", msg)
            add("CDN_QUERY_FAILED", "high",
                f"DescribeCdnDomainDetail failed: {msg}")

    # ---------------- Step 1b: domain inventory (context / candidates) ----
    log("\n[Step 1b] List CDN domains of this account "
        "(aliyun cdn describe-user-domains)")
    inventory: Optional[Dict[str, Any]] = None
    try:
        inventory = cdn_describe_user_domains()
        evidence["domain_inventory"] = inventory
        log(f"  Total CDN domains: {inventory['total_count']}")
        for d in inventory["domains"][:10]:
            log(f"    - {d['domain_name']} [{d['domain_status']}]")
        if not domain_found:
            candidates = [d["domain_name"] for d in inventory["domains"]]
            if candidates:
                recommendations.append(
                    "CDN domains present on this account: "
                    + ", ".join(candidates[:10])
                    + (" ..." if len(candidates) > 10 else "")
                    + ". Check whether the reported domain is among them "
                      "(mind spelling).")
    except RuntimeError as e:
        warn("cdn_api_error", f"DescribeUserDomains failed: {e}")

    if detail is None:
        # Nothing more to check without the domain record.
        return _finalize(domain, user_origin_host, uid, findings,
                         recommendations, errors, evidence,
                         degraded=True,
                         next_action="Verify the accelerated domain name "
                                     "and the owning account UID, then re-run")

    # ---------------- Step 2: domain state branch ----------------
    status = (detail.get("domain_status") or "").lower()
    if status and status != "online":
        add("DOMAIN_NOT_ONLINE", "high",
            f"CDN domain '{domain}' is in state '{status}' (not online). "
            f"A stopped/offline/configuring domain does not serve traffic; "
            f"back-to-origin problems are expected until it is re-enabled.")
        recommendations.append(
            f"The domain state is '{status}'. Re-enable (start) the domain "
            f"in the CDN console or confirm the expected state before "
            f"further back-to-origin investigation.")
        log(f"  [FINDING] domain state is '{status}' (not online)")

    # ---------------- Step 3: origin host header config ----------------
    log("\n[Step 2] Query origin Host header config "
        "(aliyun cdn describe-cdn-domain-configs set_req_host_header)")
    host_cfg: Dict[str, Any] = {"configured": False, "origin_host": None}
    try:
        host_cfg = cdn_describe_origin_host_config(domain)
        evidence["origin_host_config"] = host_cfg
        if host_cfg["configured"]:
            log(f"  set_req_host_header -> {host_cfg['origin_host']} "
                f"(Status={host_cfg['status']})")
        else:
            log("  set_req_host_header not configured "
                "(CDN sends the accelerated domain as Host by default)")
    except RuntimeError as e:
        warn("cdn_api_error",
             f"DescribeCdnDomainConfigs(set_req_host_header) failed: {e}")

    sources = detail.get("sources") or []
    if not sources:
        add("NO_ORIGIN_CONFIGURED", "high",
            "The domain record carries no origin source; CDN has nothing to "
            "fetch from. Back-to-origin 403/5xx is expected.")
        recommendations.append(
            "Configure an origin (OSS bucket endpoint or origin server) for "
            "this domain in the CDN console.")

    origin_checks: List[Dict[str, Any]] = []
    for idx, src in enumerate(sources, start=1):
        check = _check_one_origin(domain, src, host_cfg, uid,
                                  findings, recommendations, warn, log)
        check["index"] = idx
        origin_checks.append(check)
    evidence["origin_checks"] = origin_checks

    # ---------------- Step 4: traffic bypass detection ----------------
    if user_origin_host:
        _check_bypass(user_origin_host, sources, findings,
                      recommendations, log)

    degraded = bool(errors)
    if not findings:
        findings.append({"code": "CONFIG_LOOKS_CONSISTENT", "severity": "info",
                         "detail": "No configuration-level anomaly detected "
                                   "for this domain; origin host/port/state "
                                   "are consistent with the OSS origin."})
    # F-4: branch the NEXT_ACTION wording on whether any origin is an OSS
    # bucket (a parsed bucket name in the origin checks).
    has_oss_origin = any(c.get("bucket") for c in origin_checks)
    next_action = _compose_next_action(findings, degraded,
                                       has_oss_origin=has_oss_origin)
    return _finalize(domain, user_origin_host, uid, findings,
                     recommendations, errors, evidence,
                     degraded=degraded, next_action=next_action)


def _check_one_origin(domain: str, src: Dict[str, Any],
                      host_cfg: Dict[str, Any], uid: str,
                      findings: List[Dict[str, str]],
                      recommendations: List[str],
                      warn, log) -> Dict[str, Any]:
    """Cross-check a single CDN origin source; OSS origins go through oss2
    GetBucketInfo (read-only). Appends findings/recommendations in place."""
    content = (src.get("content") or "").strip().lower()
    src_type = src.get("type") or ""
    port = src.get("port") or 0
    check: Dict[str, Any] = {"content": content, "type": src_type,
                             "port": port, "oss_bucket_info": None,
                             "oss_error": None}

    parsed = parse_oss_origin_host(content)
    if not parsed:
        if src_type == "oss" or content.endswith(".aliyuncs.com"):
            findings.append({"code": "UNRECOGNIZED_OSS_ORIGIN",
                             "severity": "warn",
                             "detail": f"Origin '{content}' looks like an "
                                       f"OSS endpoint but does not match "
                                       f"<bucket>.oss-<region>.aliyuncs.com; "
                                       f"verify the origin content."})
        else:
            findings.append({"code": "NON_OSS_ORIGIN", "severity": "info",
                             "detail": f"Origin '{content}' is not an OSS "
                                       f"bucket endpoint (Type={src_type}); "
                                       f"the private-bucket authorization "
                                       f"check is not applicable to this "
                                       f"origin."})
        _is_oss = (src_type == "oss" or content.endswith(".aliyuncs.com"))
        _check_host_header(domain, content, host_cfg, findings,
                           is_oss_origin=_is_oss)
        return check

    bucket, endpoint = parsed["bucket"], parsed["endpoint"]
    check["bucket"] = bucket
    check["endpoint"] = endpoint
    ep_kind = classify_oss_endpoint(endpoint)
    check["endpoint_kind"] = ep_kind
    log(f"\n[Step 3] OSS cross-check of origin bucket '{bucket}' "
        f"(oss2 GetBucketInfo @ {endpoint})")

    # Special endpoint forms (official: access-oss-via-bucket-domain-name):
    if ep_kind == "internal":
        findings.append({"code": "ORIGIN_INTERNAL_ENDPOINT", "severity": "high",
                         "detail": f"Origin '{content}' uses the OSS INTERNAL "
                                   f"endpoint ({endpoint}). Internal endpoints "
                                   f"are only reachable from Alibaba Cloud "
                                   f"internal networks in the SAME region "
                                   f"(e.g. ECS); public CDN edge nodes cannot "
                                   f"route to them, so back-to-origin through "
                                   f"this origin fails (timeout / connection "
                                   f"errors)."})
        recommendations.append(
            f"Change the CDN origin content of '{domain}' from the internal "
            f"endpoint to the bucket's public endpoint "
            f"({endpoint.replace('-internal', '')}) or, for cross-region "
            f"optimization, the transfer-acceleration endpoint "
            f"(<bucket>.oss-accelerate.aliyuncs.com).")
    elif ep_kind == "accelerate":
        findings.append({"code": "ORIGIN_ACCELERATE_ENDPOINT", "severity": "info",
                         "detail": f"Origin '{content}' uses the OSS "
                                   f"transfer-acceleration endpoint. This is "
                                   f"an official 'CDN + transfer acceleration' "
                                   f"dual-acceleration architecture "
                                   f"(transfer-acceleration, best practices); "
                                   f"the "
                                   f"region-consistency check does not apply "
                                   f"to this endpoint form. A successful "
                                   f"GetBucketInfo through it also proves "
                                   f"transfer acceleration is enabled on the "
                                   f"bucket."})

    # Origin Host header sanity for OSS origins: the back-to-origin Host must
    # be the bucket's virtual-hosted endpoint host for OSS to route it.
    # is_oss_origin=True: CDN auto-sets the Host to the source station domain
    # for OSS-domain origins (official policy), so ORIGIN_HOST_DEFAULT is not
    # emitted in that case.
    _check_host_header(domain, content, host_cfg, findings,
                       is_oss_origin=True)

    # Port sanity (OSS endpoints serve 80/443; 8080 is not an OSS port)
    if port not in (80, 443):
        findings.append({"code": "ORIGIN_PORT_SUSPECT", "severity": "warn",
                         "detail": f"Origin port {port} for '{content}': OSS "
                                   f"endpoints serve HTTP(80)/HTTPS(443); a "
                                   f"different port cannot reach OSS and "
                                   f"produces back-to-origin failures."})
        recommendations.append(
            f"Set the origin port of '{content}' to 80 (HTTP) or 443 "
            f"(HTTPS) in the CDN origin settings.")

    try:
        info = _oss_client.get_bucket_info(bucket, f"https://{endpoint}")
        check["oss_bucket_info"] = info
        log(f"  acl={info['acl']} storage_class={info['storage_class']} "
            f"location={info['location']} owner={info['owner_id']}")
        _attribute_bucket(domain, bucket, info, uid, findings,
                          recommendations)
    except _oss_client.OssClientError as e:
        check["oss_error"] = e.to_dict()
        warn(f"oss_{e.category}", str(e), e.hint)
        if e.category == "permission":
            findings.append({"code": "ORIGIN_BUCKET_NOT_READABLE",
                             "severity": "warn",
                             "detail": f"GetBucketInfo on origin bucket "
                                       f"'{bucket}' was denied (403): the "
                                       f"bucket is not readable by this "
                                       f"caller -- typically a cross-account "
                                       f"origin. The back-to-origin "
                                       f"authorization must then be verified "
                                       f"from the bucket owner side "
                                       f"(see origin-auth-playbook)."})
        elif e.category == "not_found":
            findings.append({"code": "ORIGIN_BUCKET_MISSING",
                             "severity": "high",
                             "detail": f"Origin bucket '{bucket}' does not "
                                       f"exist (NoSuchBucket); CDN "
                                       f"back-to-origin to it fails with "
                                       f"404/403."})
            recommendations.append(
                f"Verify the origin content of '{domain}': bucket "
                f"'{bucket}' was not found. Correct the origin address in "
                f"the CDN origin settings.")
    return check


def _check_host_header(domain: str, origin_content: str,
                       host_cfg: Dict[str, Any],
                       findings: List[Dict[str, str]],
                       is_oss_origin: bool = False) -> None:
    """Compare set_req_host_header with the origin content.

    Official behavior (help.aliyun.com/zh/cdn/user-guide/configure-the-default-origin-host,
    section '示例三：源站类型为OSS域名', L79):
      - Origin type = OSS domain -> CDN AUTOMATICALLY enables the default
        origin-HOST feature and sets the domain type to 'source station
        domain'. The back-to-origin Host equals the OSS bucket endpoint
        (<bucket>.oss-<region>.aliyuncs.com). No user configuration is
        needed and ORIGIN_HOST_DEFAULT must NOT be emitted.
      - Origin type = domain / IP -> the feature is OFF by default; the
        back-to-origin Host falls back to the accelerated domain, which
        OSS cannot route (403/404). ORIGIN_HOST_DEFAULT IS emitted.
    """
    if not host_cfg.get("configured"):
        if is_oss_origin:
            # Official: OSS-domain origins have the origin HOST auto-set to
            # the source station domain by CDN. This is CORRECT behavior.
            findings.append({"code": "ORIGIN_HOST_AUTO_OK", "severity": "info",
                             "detail": f"No explicit set_req_host_header for "
                                       f"'{domain}': for an OSS-domain origin "
                                       f"CDN automatically sets the back-to-origin "
                                       f"Host to the source station domain "
                                       f"('{origin_content}') per official policy "
                                       f"(configure-the-default-origin-host, "
                                       f"示例三). No action needed."})
            return
        # Non-OSS origin (domain / IP): default Host = accelerated domain;
        # OSS cannot route that, so this is a real finding.
        findings.append({"code": "ORIGIN_HOST_DEFAULT", "severity": "warn",
                         "detail": f"No set_req_host_header configured for "
                                   f"'{domain}': CDN sends the accelerated "
                                   f"domain as the back-to-origin Host. For "
                                   f"origin '{origin_content}' the Host must "
                                   f"equal the origin endpoint host (or a "
                                   f"custom domain bound to that bucket), "
                                   f"otherwise OSS cannot route the request "
                                   f"and returns 403/404."})
        return
    host = (host_cfg.get("origin_host") or "").strip().lower()
    if host and host != origin_content.lower():
        findings.append({"code": "ORIGIN_HOST_MISMATCH", "severity": "high",
                         "detail": f"Back-to-origin Host "
                                   f"(set_req_host_header='{host}') differs "
                                   f"from the origin content "
                                   f"'{origin_content}'. For OSS origins the "
                                   f"Host must equal "
                                   f"<bucket>.oss-<region>.aliyuncs.com, "
                                   f"otherwise OSS returns 403/404."})


def _attribute_bucket(domain: str, bucket: str, info: Dict[str, Any],
                      uid: str, findings: List[Dict[str, str]],
                      recommendations: List[str]) -> None:
    """Attribute the back-to-origin 403 risk from the measured bucket facts:
    ACL, owner (same vs cross account), region consistency."""
    acl = (info.get("acl") or "").lower()
    owner = str(info.get("owner_id") or "")
    if acl == "private":
        if uid and owner and owner != uid:
            findings.append({"code": "PRIVATE_ORIGIN_CROSS_ACCOUNT",
                             "severity": "high",
                             "detail": f"Origin bucket '{bucket}' is private "
                                       f"and owned by another account "
                                       f"({owner}); CDN back-to-origin from "
                                       f"account {uid} requires an explicit "
                                       f"cross-account origin authorization."})
            recommendations.append(
                f"Ask the bucket owner to authorize CDN back-to-origin for "
                f"account {uid} (bucket policy granting the CDN service "
                f"read, or private-bucket origin authorization) -- see "
                f"references/origin-auth-playbook.md.")
        else:
            findings.append({"code": "PRIVATE_ORIGIN_AUTH_REQUIRED",
                             "severity": "high",
                             "detail": f"Origin bucket '{bucket}' is private "
                                       f"(same account {owner or uid}). CDN "
                                       f"back-to-origin returns 403 unless a "
                                       f"private-bucket origin authorization "
                                       f"is in place; this script cannot "
                                       f"read that authorization state, so "
                                       f"verify it in the CDN console / "
                                       f"bucket policy."})
            recommendations.append(
                f"Enable or verify the private-bucket back-to-origin "
                f"authorization for '{bucket}' (CDN console one-click "
                f"authorization, bucket policy, or STS origin auth) -- see "
                f"references/origin-auth-playbook.md.")
    elif acl in ("public-read", "public-read-write"):
        findings.append({"code": "PUBLIC_ORIGIN_NO_AUTH_NEEDED",
                         "severity": "info",
                         "detail": f"Origin bucket '{bucket}' ACL is "
                                   f"'{acl}': no origin authorization is "
                                   f"required; a back-to-origin 403 would "
                                   f"point to origin Host/port or bucket "
                                   f"policy deny rules instead."})
    # Region consistency: bucket location vs the endpoint region in the host.
    # Only meaningful for public region endpoints (oss-<region>.aliyuncs.com):
    #   * accelerate endpoints carry no region -- comparing 'oss-accelerate'
    #     against the bucket location produced a FALSE ORIGIN_REGION_MISMATCH
    #     (B-class defect fixed; official dual-acceleration architecture).
    #   * internal endpoints are already attributed by ORIGIN_INTERNAL_ENDPOINT;
    #     the '-internal' suffix would also poison the region string compare.
    endpoint = info.get("extranet_endpoint") or ""
    if classify_oss_endpoint(endpoint) != "public":
        return
    location = (info.get("location") or "").lower()
    region_from_host = endpoint.replace(".aliyuncs.com", "")
    if location and region_from_host and location != region_from_host:
        findings.append({"code": "ORIGIN_REGION_MISMATCH", "severity": "high",
                         "detail": f"Origin host uses region "
                                   f"'{region_from_host}' but bucket "
                                   f"'{bucket}' actually lives in "
                                   f"'{location}'; back-to-origin must use "
                                   f"the bucket's own region endpoint."})
        recommendations.append(
            f"Change the CDN origin content to "
            f"{bucket}.{location}.aliyuncs.com (the bucket's own region).")


def _check_bypass(user_origin_host: str, sources: List[Dict[str, Any]],
                  findings: List[Dict[str, str]],
                  recommendations: List[str], log) -> None:
    """Detect client traffic bypassing CDN: the user-reported origin host is
    compared with the CDN-configured origins (measured fields only)."""
    uhost = user_origin_host.strip().lower()
    log(f"\n[Step 4] Bypass check: user-reported origin host '{uhost}'")
    configured = {(s.get("content") or "").strip().lower() for s in sources}
    if parse_oss_origin_host(uhost):
        if uhost not in configured:
            findings.append({"code": "DIRECT_OSS_ACCESS", "severity": "high",
                             "detail": f"The reported host '{uhost}' is an "
                                       f"OSS bucket endpoint and is NOT the "
                                       f"CDN-configured origin set "
                                       f"{sorted(configured) or '(empty)'}: "
                                       f"requests addressed to this host go "
                                       f"directly to OSS and bypass the CDN "
                                       f"accelerated domain entirely."})
            recommendations.append(
                "Point the application/website at the CDN accelerated "
                "domain instead of the OSS endpoint host, and verify the "
                "domain DNS CNAME resolves to the CDN CNAME -- see "
                "references/bypass-detection.md.")
        else:
            findings.append({"code": "DIRECT_OSS_HOST_MATCHES_ORIGIN",
                             "severity": "info",
                             "detail": f"'{uhost}' equals a CDN-configured "
                                       f"origin; if traffic still bypasses "
                                       f"CDN, check the DNS CNAME record of "
                                       f"the accelerated domain and whether "
                                       f"clients hardcode the OSS host."})
    else:
        if uhost not in configured:
            findings.append({"code": "ORIGIN_HOST_MISMATCH",
                             "severity": "warn",
                             "detail": f"User-reported origin host '{uhost}' "
                                       f"does not match any CDN-configured "
                                       f"origin {sorted(configured) or '(empty)'}: "
                                       f"the traffic target and the CDN "
                                       f"origin configuration diverge."})


def _compose_next_action(findings: List[Dict[str, str]],
                         degraded: bool,
                         has_oss_origin: bool = True) -> str:
    codes = [f["code"] for f in findings]
    if "DOMAIN_NOT_FOUND" in codes:
        return ("Verify the accelerated domain name and the owning account "
                "UID, then re-run this diagnosis")
    if "DOMAIN_NOT_ONLINE" in codes:
        return ("Re-enable the stopped CDN domain or confirm its expected "
                "state in the CDN console")
    if "DIRECT_OSS_ACCESS" in codes:
        return ("Point the traffic at the CDN accelerated domain instead "
                "of the OSS endpoint host; verify the CNAME record -- see "
                "references/bypass-detection.md")
    if "PRIVATE_ORIGIN_AUTH_REQUIRED" in codes or \
            "PRIVATE_ORIGIN_CROSS_ACCOUNT" in codes:
        return ("Verify/enable the private-bucket back-to-origin "
                "authorization per references/origin-auth-playbook.md "
                "(manual guidance only -- this skill never changes config)")
    if "ORIGIN_HOST_MISMATCH" in codes or "ORIGIN_HOST_DEFAULT" in codes:
        # F-4 fix: branch the wording on the origin type -- the OSS bucket
        # endpoint form only applies when the origin actually is an OSS
        # bucket; for NON_OSS_ORIGIN domains it is contextually wrong.
        if has_oss_origin:
            return ("Align the back-to-origin Host (set_req_host_header) "
                    "with <bucket>.oss-<region>.aliyuncs.com -- manual "
                    "guidance only")
        return ("Align the back-to-origin Host (set_req_host_header) with "
                "the configured origin content (the origin server / "
                "third-party domain); this origin is NOT an OSS bucket, "
                "so no OSS bucket endpoint form applies and the "
                "private-bucket authorization check is not needed -- "
                "manual guidance only")
    if degraded:
        return ("Review the recorded [WARN] errors, fix the permission or "
                "input gap, then re-run")
    return ("Configuration is consistent; if the 403 persists, capture the "
            "CDN back-to-origin request/response for deeper analysis")


# F-4 inline boundary assertions: NEXT_ACTION wording must branch on the
# origin type (OSS origin keeps the bucket-endpoint form; non-OSS origin
# must not mention it).
_host_findings = [{"code": "ORIGIN_HOST_DEFAULT", "severity": "warn"}]
assert "<bucket>.oss-" in _compose_next_action(_host_findings, False, has_oss_origin=True)  # normal: OSS origin
_nonoss_findings = [{"code": "NON_OSS_ORIGIN", "severity": "info"},
                    {"code": "ORIGIN_HOST_DEFAULT", "severity": "warn"}]
_na_nonoss = _compose_next_action(_nonoss_findings, False, has_oss_origin=False)
assert "<bucket>" not in _na_nonoss and "origin content" in _na_nonoss  # normal: non-OSS origin
assert _compose_next_action([{"code": "DOMAIN_NOT_FOUND", "severity": "high"}], True, has_oss_origin=True).startswith("Verify the accelerated domain")  # boundary: not-found precedence unaffected
assert "consistent" in _compose_next_action([], False, has_oss_origin=False)  # boundary: no findings, no OSS origin

# B-1 inline boundary assertions: _check_host_header must NOT emit
# ORIGIN_HOST_DEFAULT for OSS-domain origins (official auto-sets Host to
# source station domain); MUST emit it for non-OSS origins.
_f: List[Dict[str, str]] = []
_check_host_header("example.com", "bkt.oss-cn-hangzhou.aliyuncs.com",
                   {"configured": False}, _f, is_oss_origin=True)
assert any(x["code"] == "ORIGIN_HOST_AUTO_OK" for x in _f), \
    "B-1: OSS origin with no set_req_host_header must emit ORIGIN_HOST_AUTO_OK"
assert not any(x["code"] == "ORIGIN_HOST_DEFAULT" for x in _f), \
    "B-1: OSS origin must NOT emit ORIGIN_HOST_DEFAULT (false positive)"
_f2: List[Dict[str, str]] = []
_check_host_header("example.com", "origin.example.org",
                   {"configured": False}, _f2, is_oss_origin=False)
assert any(x["code"] == "ORIGIN_HOST_DEFAULT" for x in _f2), \
    "B-1: non-OSS origin with no set_req_host_header must emit ORIGIN_HOST_DEFAULT"
_f3: List[Dict[str, str]] = []
_check_host_header("example.com", "bkt.oss-cn-hangzhou.aliyuncs.com",
                   {"configured": True, "origin_host": "wrong.example.com"},
                   _f3, is_oss_origin=True)
assert any(x["code"] == "ORIGIN_HOST_MISMATCH" for x in _f3), \
    "B-1 boundary: explicit mismatch must still emit ORIGIN_HOST_MISMATCH"

# B-class fix inline assertions: endpoint classification and the region
# compare skip for special endpoint forms (false ORIGIN_REGION_MISMATCH on
# oss-accelerate origins; poisoned compare on -internal origins).
assert classify_oss_endpoint("oss-accelerate.aliyuncs.com") == "accelerate"       # normal
assert classify_oss_endpoint("oss-accelerate-overseas.aliyuncs.com") == "accelerate"  # normal
assert classify_oss_endpoint("oss-cn-beijing-internal.aliyuncs.com") == "internal"    # normal
assert classify_oss_endpoint("oss-cn-beijing.aliyuncs.com") == "public"           # boundary: plain region
assert classify_oss_endpoint("") == "public" and classify_oss_endpoint(None) == "public"  # invalid input: safe default
assert classify_oss_endpoint("OSS-Accelerate.Aliyuncs.COM") == "accelerate"       # boundary: case-insensitive
_fa: List[Dict[str, str]] = []
_attribute_bucket("example.com", "bkt",
                  {"acl": "public-read", "owner_id": "1",
                   "location": "oss-cn-beijing",
                   "extranet_endpoint": "oss-accelerate.aliyuncs.com"},
                  "1", _fa, [])
assert not any(x["code"] == "ORIGIN_REGION_MISMATCH" for x in _fa), \
    "accelerate endpoint must NOT trigger ORIGIN_REGION_MISMATCH (false positive)"
_fi: List[Dict[str, str]] = []
_attribute_bucket("example.com", "bkt",
                  {"acl": "public-read", "owner_id": "1",
                   "location": "oss-cn-beijing",
                   "extranet_endpoint": "oss-cn-beijing-internal.aliyuncs.com"},
                  "1", _fi, [])
assert not any(x["code"] == "ORIGIN_REGION_MISMATCH" for x in _fi), \
    "internal endpoint must NOT trigger ORIGIN_REGION_MISMATCH (suffix-poisoned compare)"
_fr: List[Dict[str, str]] = []
_attribute_bucket("example.com", "bkt",
                  {"acl": "public-read", "owner_id": "1",
                   "location": "oss-cn-beijing",
                   "extranet_endpoint": "oss-cn-hangzhou.aliyuncs.com"},
                  "1", _fr, [])
assert any(x["code"] == "ORIGIN_REGION_MISMATCH" for x in _fr), \
    "boundary: genuine public-endpoint region mismatch must still be detected"


# ---------------------------------------------------------------------------
# Official-doc verification hook (runtime doc lookup, batch-3 integration)
# ---------------------------------------------------------------------------

_CUSTOMER_QUESTION = ""


def _doc_verification(status: str):
    """Step B: verify the customer's original wording against official OSS
    docs. This skill carries no embedded-knowledge Step A, so Step A is
    always "unmatched" and the lookup runs whenever --question is present
    (integration spec 2.2 condition 1). Skipped when --question is absent
    (no-arg regression unchanged). Returns the constant four-key dict from
    _doc_lookup; never raises and never blocks the main diagnosis."""
    q = _CUSTOMER_QUESTION.strip()
    if not q:
        return None
    return _doc_lookup.lookup_config_topic(q)


assert _doc_verification("OK") is None  # invalid: no --question -> unchanged
_CUSTOMER_QUESTION = "how to configure it?"
assert _doc_lookup.is_consult_question(_CUSTOMER_QUESTION) is True  # signal
_CUSTOMER_QUESTION = ""


def _finalize(domain: str, user_origin_host: Optional[str], uid: str,
              findings: List[Dict[str, str]],
              recommendations: List[str], errors: List[Dict[str, Any]],
              evidence: Dict[str, Any], degraded: bool,
              next_action: str) -> Dict[str, Any]:
    return {
        "skill": _SKILL_NAME,
        "domain": domain,
        "user_origin_host": user_origin_host,
        "uid": uid,
        "status": "DEGRADED" if degraded else "OK",
        "findings": findings,
        "recommendations": recommendations,
        "errors": errors,
        "evidence": evidence,
        "next_action": next_action,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_text(result: Dict[str, Any]) -> None:
    print()
    print("=" * 70)
    print("CDN back-to-origin (OSS) configuration diagnosis")
    print("=" * 70)
    print(f"Accelerated domain : {result['domain']}")
    print(f"Caller UID         : {result['uid'] or '(not derived)'}")
    if result.get("user_origin_host"):
        print(f"User-reported host : {result['user_origin_host']}")
    print("-" * 70)
    for f in result["findings"]:
        print(f"[{f['severity'].upper()}] {f['code']}")
        print(f"    {f['detail']}")
    if result["recommendations"]:
        print("-" * 70)
        print("Recommendations (manual guidance only -- read-only skill):")
        for i, r in enumerate(result["recommendations"], start=1):
            print(f"  {i}. {r}")
    if result["errors"]:
        print("-" * 70)
        print("Recorded errors (degraded steps):")
        for e in result["errors"]:
            print(f"  - [{e['category']}] {e['message']}")
            if e.get("hint"):
                print(f"      hint: {e['hint']}")
    dv = result.get("doc_verification")
    if dv:
        print("-" * 70)
        if dv.get("matched"):
            print("Doc verification (official OSS docs, llms-index):")
            for doc in dv.get("docs", []):
                print(f"  - {doc['title']}: {doc['url']}")
        elif (dv.get("note") or "").startswith("DEGRADED"):
            print("Doc verification: DEGRADED (offline) -- conclusions are "
                  "based on embedded knowledge only.")
        else:
            print("Doc verification: no matching official doc entry.")
    print("=" * 70)
    print(f"STATUS: {result['status']}")
    print(f"NEXT_ACTION: {result['next_action']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CDN back-to-origin (OSS) configuration diagnosis "
                    "(read-only: domain state, origin host/port, private "
                    "bucket authorization attribution, bypass detection)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Positive branch: verify a live OSS back-to-origin configuration
  python3 origin_config_diagnosis.py --domain test234.pier39.cn

  # Bypass branch: user traffic addressed directly to an OSS endpoint host
  python3 origin_config_diagnosis.py --domain d.example.com \\
      --user-origin-host b.oss-cn-shanghai.aliyuncs.com

  # JSON output for agents
  python3 origin_config_diagnosis.py --domain d.example.com --json
        """,
    )
    parser.add_argument("--domain", default="",
                            required=False,
                        help="Accelerated domain to diagnose (required)")
    parser.add_argument("--user-origin-host", default=None,
                        help="Origin host the user's traffic is addressed "
                             "to (bypass detection), e.g. "
                             "<bucket>.oss-<region>.aliyuncs.com")
    parser.add_argument("--uid", default=None,
                        help="Target customer UID (informational; the caller "
                             "UID is always derived via STS "
                             "GetCallerIdentity)")
    parser.add_argument("--json", action="store_true",
                        help="JSON output (auto-silences progress)")
    parser.add_argument("--quiet", action="store_true",
                        help="Text mode: suppress progress (final report "
                             "only)")
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
            "skill": "alibabacloud-oss-cdn-origin-config-diagnosis",
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

    # Missing-domain guard: without the accelerated domain there is nothing to
    # check, and a bare exit 2 leaves the customer without a next step.
    if not (args.domain or "").strip():
        _doms = []
        try:
            _doms = list(cdn_describe_user_domains())[:30]
        except Exception as e:
            print(f"[WARN] CDN domain listing degraded: {e}", file=sys.stderr)
        _na = ("Ask the user for the accelerated domain name that fronts the "
               "OSS bucket; cdn_domains lists domains visible to the current "
               "credential.")
        if not _doms:
            _na += (" No CDN domain is listable with the current credential: "
                    "ask for the exact domain name.")
        _rep = {"skill": "alibabacloud-oss-cdn-origin-config-diagnosis",
                "domain": "", "cdn_domains": _doms, "errors": [],
                "status": "FAIL", "next_action": _na}
        print(json.dumps(_rep, indent=2, ensure_ascii=False))
        print(f"STATUS: {_rep['status']}")
        print(f"NEXT_ACTION: {_na}")
        sys.exit(1)
    global _CUSTOMER_QUESTION
    _CUSTOMER_QUESTION = args.question or ""

    domain = args.domain.strip().lower()
    if not re.match(r"^[a-z0-9._-]{3,253}$", domain):
        print("[FAIL] Error: --domain is not a plausible domain name",
              file=sys.stderr)
        sys.exit(1)

    if shutil.which("aliyun") is None:
        print("[FAIL] Error: aliyun CLI not found on PATH; CDN diagnosis "
              "requires it (`aliyun configure` first)", file=sys.stderr)
        sys.exit(1)

    verbose = not (args.json or args.quiet)

    # Caller UID derivation (degraded with [WARN] on failure -- never fatal)
    uid = _oss_client.resolve_uid()
    if args.uid:
        if uid and args.uid != uid:
            print(f"[WARN] provided --uid {args.uid} differs from caller "
                  f"UID {uid}; diagnosis runs with the caller credential",
                  file=sys.stderr)
        uid = uid or args.uid
    if args.uid:
        print(f"Target UID (informational): {args.uid}", file=sys.stderr)

    result = diagnose(domain, args.user_origin_host, uid, verbose=verbose)

    dv = _doc_verification(result["status"])
    if dv is not None:
        result["doc_verification"] = dv

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        # Contract lines stay on stdout in --json mode as well, matching the
        # sibling OSS skills: JSON report first, then the grep-able lines.
        print(f"\nSTATUS: {result['status']}")
        print(f"NEXT_ACTION: {result['next_action']}")
    else:
        print_text(result)
    # F-2 fix: exit-code contract unified with the sibling OSS skills --
    # OK and DEGRADED both exit 0 ("a diagnosis conclusion was produced
    # successfully"); exit 1 is reserved for FAIL (bad input / missing
    # CLI, already handled above). Documented in SKILL.md "Error
    # Handling"; upstream automation must NOT treat DEGRADED as failure.
    sys.exit(0 if result["status"] in ("OK", "DEGRADED") else 1)


if __name__ == "__main__":
    main()
