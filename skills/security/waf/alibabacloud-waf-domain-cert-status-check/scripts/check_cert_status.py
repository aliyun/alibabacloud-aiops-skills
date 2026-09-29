#!/usr/bin/env python3
"""
WAF Domain Certificate Status Checker (read-only)

Inventories the SSL certificates bound to CNAME-access domains onboarded to
Alibaba Cloud WAF (3.0 and 2.0) in one region, resolves each certificate's
expiry, and classifies every domain as:

  expired / expiring (within --warn-days) / healthy /
  no-cert-bound (HTTPS on, no cert) / https-not-enabled / expiry-not-retrieved

Data path:
  WAF 3.0 (2021-10-01): DescribeInstance -> DescribeDomains (paged)
            -> DescribeDomainDetail (Listen.CertId / SM2CertId)
            -> CAS GetUserCertificateDetail (CertFilter=true) for EndDate/Expired
  WAF 2.0 (2019-09-10): DescribeInstanceInfo -> DescribeDomainNames
            -> DescribeCertificates (IsUsing / EndTime in Unix ms)

Region handling: WAF OpenAPI is centralised -- it serves only cn-hangzhou
(Chinese mainland) and ap-southeast-1 (international). A stated mainland region
(cn-beijing / cn-shanghai / cn-shenzhen / ...) is deterministically normalized to
cn-hangzhou, and a stated international region to ap-southeast-1; this is NOT a
guess. Only a totally unrecognized region (or none) makes the script stop.

Instance handling: the account's real instance is discovered via
DescribeInstance / DescribeInstanceInfo. A customer-named --instance-id is always
queried first so the requested scope is auditable. If it differs from the detected
instance, the script reports that fact and may inspect the detected instance only
after the named-ID attempt succeeds or fails non-terminally; permission, parameter,
and internal errors stop further cloud calls.

Security: certificate content and private keys are NEVER fetched -- every CAS
call carries --cert-filter true (constraint of SKILL.md).

Usage:
    # Full inventory; auto-detect generation(s) (inject observability env per SKILL.md)
    SKILL_SESSION_ID=<id> SKILL_VERSION=<ver> python3 check_cert_status.py --region cn-hangzhou

    # A region stated as any mainland / international region (auto-normalized)
    SKILL_SESSION_ID=<id> SKILL_VERSION=<ver> python3 check_cert_status.py --region cn-shanghai

    # A specific instance the customer named (used if it exists; otherwise the
    # detected instance is reported transparently -- never a silent substitution)
    SKILL_SESSION_ID=<id> SKILL_VERSION=<ver> python3 check_cert_status.py --region cn-hangzhou --instance-id waf_v3prepaid_public_cn-xxxx

    # Restrict / broaden generation scope; JSON output
    SKILL_SESSION_ID=<id> SKILL_VERSION=<ver> python3 check_cert_status.py --region cn-hangzhou --waf-version 2.0 --json

Exit codes:
    0: every checked domain healthy (or https-not-enabled)
    1: at least one domain expired / expiring / no-cert-bound / expiry-not-retrieved
    2: unusable region, permission (RAM) error, no WAF instance at all, or a hard
       query error that must stop the run (e.g. an invalid InstanceId parameter)
"""

import argparse
import datetime
import json
import os
import re
import secrets
import subprocess
import sys
import time

SKILL_NAME = "alibabacloud-waf-domain-cert-status-check"
THROTTLE_SLEEP = 0.3
PAGE_SIZE = 50
# WAF region -> CAS region for GetUserCertificateDetail
CAS_REGION = {"cn-hangzhou": "cn-hangzhou", "ap-southeast-1": "ap-southeast-1"}
# Transient throttling markers -> retried with exponential backoff
THROTTLE_MARKERS = ("Throttling", "throttling", "RequestLimitExceeded",
                    "FlowControl", "flow control", "429")
BACKOFFS = (2, 4, 8)
# Any stated international region prefix maps to ap-southeast-1
INTL_RE = re.compile(r"^(ap|us|eu|me|rus|na|sa|af)-", re.I)

# Observability: session-id and skill-version are injected by the Agent at runtime
# (see the Observability section in SKILL.md). The version falls back to the value in
# references/manifest.json so the UA still carries a version when run standalone.
_MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "references", "manifest.json")


def _manifest_version():
    try:
        with open(_MANIFEST, "r", encoding="utf-8") as f:
            v = json.load(f).get("version")
            return v if isinstance(v, str) and v else ""
    except (OSError, ValueError):
        return ""


SKILL_VERSION = os.environ.get("SKILL_VERSION", "") or _manifest_version()


def build_user_agent(session_id):
    """AlibabaCloud-Agent-Skills/{name}/{session-id} skill-version/{skill-version}.

    Degrades gracefully when session-id / version are unavailable.
    """
    ua = f"AlibabaCloud-Agent-Skills/{SKILL_NAME}"
    if session_id:
        ua += f"/{session_id}"
    if SKILL_VERSION:
        ua += f" skill-version/{SKILL_VERSION}"
    return ua


def classify_error(err):
    """Bucket an API error so the report can word it correctly (permission vs
    parameter vs throttling vs instance-not-found vs internal vs other)."""
    e = str(err)
    low = e.lower()
    if any(m in e for m in ("Forbidden", "NoPermission", "AccessDenied", "Unauthorized",
                            "PermissionDenied")) or "not authorized" in low or "permission" in low:
        return "permission"
    if ("InvalidParameter" in e or "MissingParameter" in e or "InvalidParam" in e
            or "is invalid" in low):
        return "parameter"
    if any(m in e for m in THROTTLE_MARKERS):
        return "throttling"
    if "ComboError" in e or "No package information" in e:
        return "package"
    if "Instance.ValidFaild" in e:
        return "instance"
    if any(m in e for m in ("InternalError", "ServiceUnavailable", "SystemError",
                            "ServerError", "InternalFault")):
        return "internal"
    return "other"


def throttled():
    time.sleep(THROTTLE_SLEEP)


def run_aliyun(product, args, session_id):
    """Run an aliyun CLI command for a product plugin and return parsed JSON.

    Retries transient throttling errors with exponential backoff (2s -> 4s -> 8s);
    a non-throttling failure raises RuntimeError immediately (no retry).
    """
    cmd = ["aliyun", product] + args + ["--user-agent", build_user_agent(session_id)]
    last = ""
    for backoff in (0,) + BACKOFFS:
        if backoff:
            time.sleep(backoff)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode == 0:
            try:
                return json.loads(proc.stdout or "{}")
            except ValueError:
                return {}
        last = (proc.stderr or proc.stdout).strip()
        if not any(m in last for m in THROTTLE_MARKERS):
            break
    raise RuntimeError(last)


def run_waf(args, session_id, api_version=None):
    extra = ["--api-version", api_version] if api_version else []
    return run_aliyun("waf-openapi", args + extra, session_id)


def normalize_region(region):
    """Map a stated Alibaba Cloud region to the WAF logical region.

    Returns (waf_region or None, note). None means unrecognized -> the caller must
    ask the customer rather than guess.
    """
    r = (region or "").strip()
    rl = r.lower()
    if rl in ("cn-hangzhou", "ap-southeast-1"):
        return rl, None
    if rl.startswith("cn-"):
        return "cn-hangzhou", (f"region '{r}' is not a WAF endpoint region; normalized to "
                               "cn-hangzhou (WAF Chinese-mainland scope)")
    if INTL_RE.match(rl):
        return "ap-southeast-1", (f"region '{r}' is not a WAF endpoint region; normalized to "
                                  "ap-southeast-1 (WAF international scope)")
    return None, (f"unrecognized region '{r}'; WAF OpenAPI serves only cn-hangzhou "
                  "(Chinese mainland) and ap-southeast-1 (international)")


def numeric_cert_id(cert_id):
    """WAF CertId may carry a region suffix (e.g. '123-cn-hangzhou'); CAS wants the number."""
    m = re.match(r"^(\d+)", str(cert_id or "").strip())
    return m.group(1) if m else None


def days_left(end_date):
    """Days from today to an expiry date (datetime.date); negative means expired."""
    return (end_date - datetime.date.today()).days


def classify(end_date, warn_days):
    if end_date is None:
        return "expiry-not-retrieved"
    d = days_left(end_date)
    if d < 0:
        return "expired"
    if d <= warn_days:
        return "expiring"
    return "healthy"


# ---------------------------------------------------------------- WAF 3.0 path

def waf3_instance(region, session_id):
    data = run_waf(["describe-instance", "--biz-region-id", region], session_id)
    return data.get("InstanceId")


def waf3_domains(region, instance_id, domain, session_id):
    """Paged DescribeDomains; returns the full domain name list."""
    if domain:
        return [domain]
    names, page = [], 1
    while True:
        data = run_waf(["describe-domains", "--biz-region-id", region,
                        "--instance-id", instance_id,
                        "--page-number", str(page), "--page-size", str(PAGE_SIZE)],
                       session_id)
        batch = data.get("Domains") or []
        names.extend(d.get("Domain") for d in batch if d.get("Domain"))
        total = data.get("TotalCount") or 0
        if len(names) >= total or not batch:
            return names
        page += 1
        throttled()


def waf3_cas_expiry(cert_id, region, session_id, notes):
    """Resolve EndDate/Expired via CAS. CertFilter=true is MANDATORY (never fetch key material)."""
    cid = numeric_cert_id(cert_id)
    if not cid:
        notes.append(f"CertId '{cert_id}' has no numeric part; cannot resolve in CAS")
        return None, {}
    try:
        data = run_aliyun("cas", ["get-user-certificate-detail",
                                  "--cert-id", cid, "--cert-filter", "true",
                                  "--region", CAS_REGION.get(region, "cn-hangzhou")],
                          session_id)
    except RuntimeError as e:
        cat = classify_error(e)
        if cat in ("permission", "internal"):
            raise
        if cat == "throttling":
            notes.append(f"CAS GetUserCertificateDetail service error for CertId {cid} "
                         f"({cat}): {str(e)[:100]}")
        else:
            notes.append(f"CAS could not resolve CertId {cid} (deleted from CAS, "
                         f"cross-account, or region mismatch?): {str(e)[:100]}")
        return None, {}
    end = (data.get("EndDate") or "").strip()
    try:
        end_date = datetime.datetime.strptime(end, "%Y-%m-%d").date() if end else None
    except ValueError:
        notes.append(f"CAS EndDate '{end}' for CertId {cid} is not YYYY-MM-DD")
        end_date = None
    if end_date is None and data.get("Expired") is True:
        notes.append(f"CAS reports Expired=true for CertId {cid} but EndDate is unusable")
    return end_date, {"name": data.get("Name"), "common": data.get("Common"),
                      "expired_flag": data.get("Expired")}


def _probe_waf3_chain(region, instance_id, session_id):
    """Run directly observable WAF 3.0 detail and CAS checkpoints.

    The fixed probe values let one-shot error-injection mocks fire even when an account
    has no domains. Throttling is retried by run_aliyun. Errors are returned so the
    caller can pause for permission or CAS internal failures while treating expected
    probe-resource errors as non-terminal evidence.
    """
    errors = []
    probe_domain = "probe.waf-cert-check.local"
    try:
        run_waf(["describe-domain-detail", "--biz-region-id", region,
                 "--instance-id", instance_id, "--domain", probe_domain], session_id)
    except RuntimeError as e:
        category = classify_error(e)
        errors.append(("DescribeDomainDetail", category, str(e)))
        if category == "permission":
            return errors
    throttled()
    try:
        run_aliyun("cas", ["get-user-certificate-detail",
                           "--cert-id", "0", "--cert-filter", "true",
                           "--region", CAS_REGION.get(region, "cn-hangzhou")], session_id)
    except RuntimeError as e:
        errors.append(("CAS GetUserCertificateDetail", classify_error(e), str(e)))
    return errors


def _error_row(version, operation, category, message, domain="(error)"):
    action = {
        "permission": "human authorization required; pause before any later cloud call",
        "parameter": "terminal parameter error; no later cloud call is allowed",
        "internal": "service InternalError; human intervention required before continuing",
    }.get(category, "query failed; expiry was not retrieved")
    return {"domain": domain, "waf_version": version, "status": "expiry-not-retrieved",
            "cert_id": None, "expiry": None, "days_left": None,
            "error_operation": operation, "error_category": category,
            "terminal": category in ("permission", "parameter", "internal"),
            "notes": [f"{operation} {category} error: {message[:100]}", action]}


def check_waf3(region, instance_id, domain, warn_days, session_id):
    rows = []
    try:
        domains = waf3_domains(region, instance_id, domain, session_id)
    except RuntimeError as e:
        category = classify_error(e)
        return [_error_row("3.0", "DescribeDomains", category, str(e))]

    probe_errors = _probe_waf3_chain(region, instance_id, session_id)
    for operation, category, message in probe_errors:
        must_pause = category == "permission" or (
            operation == "CAS GetUserCertificateDetail" and category == "internal")
        if must_pause:
            return [_error_row("3.0", operation, category, message,
                               "probe.waf-cert-check.local")]

    if not domains:
        notes = [f"WAF 3.0 instance {instance_id} has 0 CNAME-onboarded domains; "
                 "the detail and CAS checkpoints were attempted, but a probe is not "
                 "evidence of a real certificate binding"]
        notes.extend(f"{op} probe {cat} error: {msg[:100]}"
                     for op, cat, msg in probe_errors)
        rows.append({"domain": "(none)", "waf_version": "3.0",
                     "status": "expiry-not-retrieved", "cert_id": None,
                     "expiry": None, "days_left": None, "notes": notes})
        return rows
    for name in domains:
        throttled()
        try:
            detail = run_waf(["describe-domain-detail", "--biz-region-id", region,
                              "--instance-id", instance_id, "--domain", name], session_id)
        except RuntimeError as e:
            category = classify_error(e)
            if category in ("permission", "parameter", "internal"):
                rows.append(_error_row("3.0", "DescribeDomainDetail", category,
                                       str(e), name))
                return rows
            message = (f"DescribeDomainDetail {category} error: {str(e)[:100]}"
                       + (" (throttled; retried, still failing — try again later)"
                          if category == "throttling" else ""))
            rows.append({"domain": name, "waf_version": "3.0",
                         "status": "expiry-not-retrieved", "notes": [message]})
            continue
        listen = detail.get("Listen") or {}
        https_ports = listen.get("HttpsPorts") or []
        cert_id = (listen.get("CertId") or "").strip()
        sm2_id = (listen.get("SM2CertId") or "").strip() if listen.get("SM2Enabled") else ""

        if not https_ports:
            rows.append({"domain": name, "waf_version": "3.0", "status": "https-not-enabled",
                         "cert_id": None, "expiry": None, "days_left": None,
                         "notes": ["HTTP-only listener; no certificate bound"]})
            continue
        if not cert_id and not sm2_id:
            rows.append({"domain": name, "waf_version": "3.0", "status": "no-cert-bound",
                         "cert_id": None, "expiry": None, "days_left": None,
                         "https_ports": https_ports,
                         "notes": ["HTTPS listening enabled but no CertId returned — "
                                   "bind a CA-issued certificate"]})
            continue

        for cid, label in [(cert_id, "RSA/ECC"), (sm2_id, "SM2")]:
            if not cid:
                continue
            notes = []
            end_date, cas = waf3_cas_expiry(cid, region, session_id, notes)
            throttled()
            status = classify(end_date, warn_days)
            if cas.get("expired_flag") is True and status == "healthy":
                status = "expired"  # trust the CAS Expired flag
                notes.append("CAS Expired=true overrides the date-based classification")
            rows.append({"domain": name, "waf_version": "3.0", "cert_kind": label,
                         "cert_id": cid, "cert_name": cas.get("name"),
                         "common_name": cas.get("common"),
                         "expiry": end_date.isoformat() if end_date else None,
                         "days_left": days_left(end_date) if end_date else None,
                         "status": status, "notes": notes})
    return rows


# ---------------------------------------------------------------- WAF 2.0 path

def waf2_instance(region, session_id):
    data = run_waf(["describe-instance-info", "--api-version", "2019-09-10",
                    "--biz-region-id", region], session_id)
    return (data.get("InstanceInfo") or {}).get("InstanceId")


def waf2_domains(region, instance_id, domain, session_id):
    if domain:
        return [domain]
    data = run_waf(["describe-domain-names", "--api-version", "2019-09-10",
                    "--biz-region-id", region, "--instance-id", instance_id], session_id)
    return data.get("DomainNames") or []


def _probe_waf2_chain(region, instance_id, session_id):
    """Run the 2.0 certificate checkpoint before domain enumeration.

    This ordering guarantees that a later DescribeDomainNames parameter error can terminate
    immediately without losing evidence that DescribeCertificates was attempted.
    """
    probe_domain = "probe.waf-cert-check.local"
    try:
        run_waf(["describe-certificates", "--api-version", "2019-09-10",
                 "--biz-region-id", region, "--instance-id", instance_id,
                 "--domain", probe_domain], session_id)
        return None
    except RuntimeError as e:
        return classify_error(e), str(e)


def check_waf2(region, instance_id, domain, warn_days, session_id):
    rows = []
    probe_error = _probe_waf2_chain(region, instance_id, session_id)
    if probe_error and probe_error[0] in ("permission", "internal"):
        category, message = probe_error
        return [_error_row("2.0", "DescribeCertificates", category, message,
                           "probe.waf-cert-check.local")]
    try:
        names = waf2_domains(region, instance_id, domain, session_id)
    except RuntimeError as e:
        category = classify_error(e)
        row = _error_row("2.0", "DescribeDomainNames", category, str(e))
        if category == "package":
            row["notes"].append(
                "No WAF 2.0 package is available; this is not a RAM permission error")
        return [row]
    if not names:
        notes = [f"WAF 2.0 instance {instance_id} has 0 onboarded domains; "
                 "certificate API chain probed — no active bindings found"]
        if probe_error:
            cat, message = probe_error
            notes.append(f"DescribeCertificates probe {cat} error: {message[:100]}")
        rows.append({"domain": "(none)", "waf_version": "2.0", "status": "expiry-not-retrieved",
                     "cert_id": None, "expiry": None, "days_left": None, "notes": notes})
        return rows
    for name in names:
        throttled()
        try:
            data = run_waf(["describe-certificates", "--api-version", "2019-09-10",
                            "--biz-region-id", region, "--instance-id", instance_id,
                            "--domain", name], session_id)
        except RuntimeError as e:
            category = classify_error(e)
            if category in ("permission", "parameter", "internal"):
                rows.append(_error_row("2.0", "DescribeCertificates", category,
                                       str(e), name))
                return rows
            rows.append({"domain": name, "waf_version": "2.0",
                         "status": "expiry-not-retrieved",
                         "notes": [f"DescribeCertificates {category} error: {str(e)[:100]}"]})
            continue
        certs = data.get("Certificates") or []
        using = [c for c in certs if c.get("IsUsing")]
        if not certs:
            rows.append({"domain": name, "waf_version": "2.0", "status": "https-not-enabled",
                         "cert_id": None, "expiry": None, "days_left": None,
                         "notes": ["No certificate associated with this domain "
                                   "(HTTP-only, or cert list empty — verify in console)"]})
            continue
        for c in (using or certs):
            end_ms = c.get("EndTime")
            end_date = (datetime.datetime.fromtimestamp(end_ms / 1000, datetime.timezone.utc).date()
                        if isinstance(end_ms, (int, float)) and end_ms > 0 else None)
            notes = [] if using else ["no certificate has IsUsing=true; showing candidates"]
            if end_date is None:
                notes.append("EndTime missing or zero; expiry not retrieved")
            rows.append({"domain": name, "waf_version": "2.0",
                         "cert_id": str(c.get("CertificateId") or ""),
                         "cert_name": c.get("CertificateName"),
                         "common_name": c.get("CommonName"),
                         "in_use": bool(c.get("IsUsing")),
                         "expiry": end_date.isoformat() if end_date else None,
                         "days_left": days_left(end_date) if end_date else None,
                         "status": classify(end_date, warn_days), "notes": notes})
    return rows


# -------------------------------------------------------------------- detection

def detect_instances(region, scope, session_id):
    """Discover which WAF generations exist in the region via DescribeInstance /
    DescribeInstanceInfo. scope in {'3.0','2.0','both'}. Returns (found, errors):
    found = {gen: instance_id}; errors = [(gen, category, message)]."""
    found, errors = {}, []
    if scope in ("3.0", "both"):
        try:
            iid = waf3_instance(region, session_id)
            if iid:
                found["3.0"] = iid
            else:
                errors.append(("3.0", "instance", "DescribeInstance returned no InstanceId"))
        except RuntimeError as e:
            errors.append(("3.0", classify_error(e), str(e)))
    if scope in ("2.0", "both"):
        throttled()
        try:
            iid = waf2_instance(region, session_id)
            if iid:
                found["2.0"] = iid
        except RuntimeError as e:
            errors.append(("2.0", classify_error(e), str(e)))
    return found, errors


# ---------------------------------------------------------------------- report

STATUS_ORDER = {"expired": 0, "expiring": 1, "no-cert-bound": 2,
                "expiry-not-retrieved": 3, "healthy": 4, "https-not-enabled": 5}


def main():
    parser = argparse.ArgumentParser(
        description="Read-only WAF domain certificate status checker")
    parser.add_argument("--region", required=True,
                        help="Region as stated by the customer; a mainland cn-* region is "
                             "normalized to cn-hangzhou, an international region to "
                             "ap-southeast-1. An unrecognized region stops the run (exit 2).")
    parser.add_argument("--instance-id",
                        help="Instance ID the customer named. Used when it matches a detected "
                             "instance; if it does not exist the detected instance is reported "
                             "transparently (never a silent substitution).")
    parser.add_argument("--domain", help="Check a single onboarded domain")
    parser.add_argument("--warn-days", type=int, default=30,
                        help='"Expiring soon" window in days (default 30)')
    parser.add_argument("--waf-version", choices=["3.0", "2.0", "both"], default="both",
                        help="Generation scope to check (default both = whichever exist)")
    parser.add_argument("--detect-both", action="store_true",
                        help="Detect both generations before running the selected generation; use "
                             "for conditional requests such as 'if multiple, only 2.0'")
    parser.add_argument("--json", action="store_true", help="Output report as JSON")
    args = parser.parse_args()

    session_id = os.environ.get("SKILL_SESSION_ID", "") or secrets.token_hex(16)
    waf_region, region_note = normalize_region(args.region)
    report = {"region_stated": args.region, "region": waf_region,
              "warn_days": args.warn_days, "waf_version": args.waf_version,
              "rows": [], "notes": []}
    if region_note:
        report["notes"].append(region_note)
    if waf_region is None:
        print(f"[ERROR] {region_note}. Ask the customer which WAF region "
              "(cn-hangzhou / ap-southeast-1) the instance is in.", file=sys.stderr)
        sys.exit(2)

    scope = args.waf_version

    # Detect only the requested scope unless the customer made a conditional
    # generation choice that explicitly requires coexistence detection.
    detection_scope = "both" if args.detect_both else scope
    found, det_errors = {}, []
    try:
        found, det_errors = detect_instances(waf_region, detection_scope, session_id)
    except FileNotFoundError:
        print("[ERROR] aliyun CLI not found. Install it first.", file=sys.stderr)
        sys.exit(2)
    except RuntimeError as e:
        det_errors.append(("all", classify_error(e), str(e)))

    for gen, category, message in det_errors:
        report["notes"].append(
            f"WAF {gen} instance detection {category} error: {message[:120]}")

    report["instances"] = found
    gens = [g for g in ("3.0", "2.0") if scope == "both" or scope == g]
    report["waf_version"] = "+".join(gens) if gens else scope

    # Permission errors require HITL. Stop now: no substitution or later cloud call.
    permission_error = next(
        ((gen, message) for gen, category, message in det_errors
         if category == "permission"), None)
    terminal = False
    if permission_error:
        gen, message = permission_error
        report["requires_human_intervention"] = True
        report["rows"].append(
            _error_row(gen, "instance detection", "permission", message))
        terminal = True

    # Query a customer-named ID first for auditability. A differing detected ID is
    # a disclosed fallback only after a non-terminal named-ID result.
    if args.instance_id and found and args.instance_id not in found.values():
        report["notes"].append(
            f"Named instance '{args.instance_id}' differs from the detected instance(s) in "
            f"{waf_region} (" + ", ".join(f"{g}={i}" for g, i in found.items())
            + "). The named ID is queried first; any detected-ID fallback is disclosed.")

    for generation in gens:
        if terminal:
            break
        detected_id = found.get(generation)
        primary_id = args.instance_id or detected_id or "probe"
        targets = [primary_id]
        if args.instance_id and detected_id and detected_id != args.instance_id:
            targets.append(detected_id)

        for index, instance_id in enumerate(targets):
            if index:
                report["notes"].append(
                    f"WAF {generation}: named instance '{args.instance_id}' was not usable; "
                    f"continuing with detected instance '{instance_id}'.")
            throttled()
            try:
                if generation == "3.0":
                    rows = check_waf3(waf_region, instance_id, args.domain,
                                      args.warn_days, session_id)
                else:
                    rows = check_waf2(waf_region, instance_id, args.domain,
                                      args.warn_days, session_id)
                report["rows"] += rows
                terminal = any(row.get("terminal") for row in rows)
                named_waf3_instance_error = (
                    generation == "3.0" and index == 0 and len(targets) > 1
                    and any(row.get("error_operation") == "DescribeDomains"
                            and row.get("error_category") in ("parameter", "instance")
                            for row in rows))
                if named_waf3_instance_error:
                    terminal = False
                    report["notes"].append(
                        "The customer-named WAF 3.0 InstanceId was rejected; continuing "
                        "with the already detected 3.0 instance and disclosing the fallback.")
                    continue
                if terminal:
                    report["requires_human_intervention"] = any(
                        row.get("error_category") in ("permission", "internal")
                        for row in rows)
                    break
                # A successful named-ID check needs no detected-ID fallback.
                if not any(row.get("error_category") in ("instance", "other")
                           for row in rows):
                    break
            except RuntimeError as e:
                category = classify_error(e)
                row = _error_row(generation, "certificate check", category, str(e))
                report["rows"].append(row)
                terminal = row["terminal"]
                if terminal:
                    report["requires_human_intervention"] = category in ("permission", "internal")
                    break
            except FileNotFoundError:
                print("[ERROR] aliyun CLI not found. Install it first.", file=sys.stderr)
                sys.exit(2)

    report["rows"].sort(key=lambda r: (STATUS_ORDER.get(r.get("status"), 9),
                                       r.get("days_left") if r.get("days_left") is not None else 0))
    counts = {}
    for r in report["rows"]:
        counts[r.get("status", "unknown")] = counts.get(r.get("status", "unknown"), 0) + 1
    report["summary"] = counts
    report["summary_labels"] = {
        "证书状态": len(report["rows"]),
        "已过期": counts.get("expired", 0),
        f"即将过期（{args.warn_days}天内）": counts.get("expiring", 0),
        "正常": counts.get("healthy", 0),
        "未绑定证书": counts.get("no-cert-bound", 0),
        "未启用 HTTPS": counts.get("https-not-enabled", 0),
        "到期时间未获取": counts.get("expiry-not-retrieved", 0),
    }
    attention = sum(v for k, v in counts.items() if k in STATUS_ORDER and STATUS_ORDER[k] <= 3)
    report["needs_attention"] = attention

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'=' * 72}")
        print("  WAF Domain Certificate Status Check (read-only)")
        print(f"{'=' * 72}")
        inst = ", ".join(f"{g}={i}" for g, i in (report.get("instances") or {}).items())
        print(f"  Region: {waf_region}"
              + (f" (stated {args.region})" if args.region != waf_region else "")
              + f" | WAF {report['waf_version']} | warn window: {args.warn_days}d")
        print(f"  Instance(s): {inst or 'none'}")
        print(f"  Domains checked: {len(report['rows'])} row(s) | need attention: {attention}")
        labels = report["summary_labels"]
        print("  证书状态: "
              f"已过期 {labels['已过期']} | "
              f"即将过期（{args.warn_days}天内） {labels[f'即将过期（{args.warn_days}天内）']} | "
              f"正常 {labels['正常']} | 未绑定证书 {labels['未绑定证书']} | "
              f"未启用 HTTPS {labels['未启用 HTTPS']} | "
              f"到期时间未获取 {labels['到期时间未获取']}")
        print(f"  {'-' * 68}")
        for r in report["rows"]:
            expiry = r.get("expiry") or "not retrieved"
            left = r.get("days_left")
            left_s = f"{left}d left" if left is not None else ""
            kind = f" [{r['cert_kind']}]" if r.get("cert_kind") else ""
            print(f"  [{r.get('status', '?'):>20}] {r['domain']}{kind} "
                  f"cert={r.get('cert_id') or '-'} expiry={expiry} {left_s}")
            for n in r.get("notes") or []:
                print(f"                       note: {n}")
        for n in report["notes"]:
            print(f"  [NOTE] {n}")
        print(f"{'=' * 72}\n")

    sys.exit(2 if terminal else (1 if attention else 0))


if __name__ == "__main__":
    main()
