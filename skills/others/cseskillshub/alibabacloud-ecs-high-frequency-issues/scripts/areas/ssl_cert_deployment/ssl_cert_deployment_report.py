#!/usr/bin/env python3
"""Entry point for ECS SSL certificate application and deployment triage.

SECURITY NOTES
    * Evidence collection uses the aliyun CLI with actions on the declared
      whitelist only (see references/ram-policies.md). Credentials come
      solely from the default credential chain of the locally configured CLI;
      this script never accepts, reads, stores, echoes or passes key
      material.
    * Every subprocess call runs as an argument list (never a shell string),
      with a per-call timeout, and error text is credential-masked before
      display (both enforced in scripts/areas/ssl_cert_deployment/_cli.py).
    * The two confirmation-gated dispatches (ONE whitelisted information-only
      guest reading, and ONE pre-change backup snapshot of a named disk) run
      ONLY after the operator passed --user-confirmed together with a
      --confirmation-scope that names the exact region and target. The
      customer must have approved the notice this script prints while the
      gate is unsatisfied.
    * Every destructive or service-affecting operation (restarting or
      reloading nginx / IIS / containers, editing web-server or redirect
      configuration, changing security group or firewall rules, removing or
      replacing certificate files, deleting snapshots) is NEVER dispatched
      here: it appears as manual guidance only.

Usage examples
    python3 scripts/areas/ssl_cert_deployment/ssl_cert_deployment_report.py --region-id cn-hangzhou \
        --instance-id i-2zeexample66e477acae --domain www.example.com \
        --symptom deploy-not-effective --web-server nginx
    python3 scripts/areas/ssl_cert_deployment/ssl_cert_deployment_report.py --region-id cn-beijing \
        --public-ip 8.138.45.192 --domain jjskovo.top --symptom apply-fail
    python3 scripts/areas/ssl_cert_deployment/ssl_cert_deployment_report.py --region-id cn-hangzhou \
        --instance-id i-2zeexample66e477acae --mode guest-probe \
        --guest-command "stat" --guest-path "/opt/cert/example.pem" \
        --user-confirmed --confirmation-scope \
        "cn-hangzhou i-2zeexample66e477acae stat approved"
    python3 scripts/areas/ssl_cert_deployment/ssl_cert_deployment_report.py --region-id cn-hangzhou \
        --mode snapshot-backup --disk-id d-2zeexample9f3b0f6b7f \
        --user-confirmed --confirmation-scope \
        "cn-hangzhou d-2zeexample9f3b0f6b7f snapshot approved"
    python3 scripts/areas/ssl_cert_deployment/ssl_cert_deployment_report.py --mode checklist \
        --web-server iis --guest-os windows
    python3 scripts/areas/ssl_cert_deployment/ssl_cert_deployment_report.py --mode faq \
        --faq-topic dv-phone
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import base64
import json
import re
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from _cli import (
    CliError,
    _PACKAGE_NAME,
    build_user_agent,
    mask_credentials,
    new_session_id,
    paginate,
    run_cli,
)
from _constants import (
    ACME_ENDPOINTS,
    ACTION_CREATE_SNAPSHOT,
    ACTION_DESCRIBE_INSTANCES,
    ACTION_DESCRIBE_INSTANCE_STATUS,
    ACTION_DESCRIBE_INVOCATIONS,
    ACTION_LIST_USER_CERTIFICATE_ORDER,
    ACTION_RUN_COMMAND,
    APPLY_FAIL_BRANCHES,
    BANNER,
    CAS_API_VERSION,
    CAS_DOMAIN_FIELDS,
    CAS_EXPIRY_FIELDS,
    CAS_ISSUE_FIELDS,
    CAS_MAX_PAGES,
    CAS_ORDER_SCOPES,
    CAS_ORDER_TYPE_CERT,
    CAS_PAGE_SIZE,
    CAS_STATUS_MEANINGS,
    CERT_BODY_BRANCHES,
    CLOUDFLARE_LE_CIDR,
    CLI_TIMEOUT_SECONDS,
    CLOUD_ASSISTANT_KIND_LINUX,
    CODE_API_ERROR,
    CODE_CLI_UNAVAILABLE,
    CODE_IMPLICIT_DENY,
    CODE_INVALID_CREDENTIAL,
    CODE_NO_PERMISSION,
    DEPLOY_BRANCHES,
    DNS_PROVIDER_ENDPOINTS,
    EGRESS_PROBE_NOTE,
    ERROR_CODE_GUIDE,
    ECS_API_VERSION,
    EVIDENCE_SURFACE,
    EXIT_BY_STATUS,
    FINAL_ANSWER_BANNER,
    GUEST_BLOCKED_TOKENS,
    GUEST_BLOCKED_WORDS,
    GUEST_READINGS_LINUX,
    GUEST_WINDOWS,
    HANDOFFS,
    HTTPS_BRANCHES,
    LINUX_PATH_RE,
    MAX_PAGES,
    MISCONCEPTIONS,
    NOT_RETURNED,
    NOT_VERIFIED_NOTE,
    PAGE_SIZE,
    POLL_DEADLINE_SECONDS,
    POLL_INTERVAL_SECONDS,
    PRODUCT_CAS,
    PRODUCT_ECS,
    PRODUCT_FAQ_TOPICS,
    PRODUCT_RULES_BRANCHES,
    PRODUCT_RULES_CONFIDENCE,
    SKILL_NAME,
    SNAPSHOT_FIRST_RULE,
    SNAPSHOT_NOTICE,
    SUGGESTED_EGRESS_COMMANDS,
    SYMP_SYMPTOMS,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
    TRIAGE_TREE_INTRO,
    WEB_SERVERS,
    WEB_SERVER_CHECKLISTS,
    is_mainland_region,
)
from _https_probe import (
    probe_https,
    resolve_domain,
    resolve_domain_public,
    summarize_endpoint_ip,
)
from sts_token import (
    fetch_caller_identity,
    identity_guidance_lines,
    uid_traceability_label,
)

INVOCATION_TERMINAL = (
    "Finished", "Success", "Failed", "Stopped", "Timeout", "PartialFailed",
    "Error", "Canceled", "Cancelled",
)
SNAPSHOT_NAME_RE = r"^[A-Za-z][A-Za-z0-9:_.-]{1,127}$"
GUEST_COMMAND_TIMEOUT = 30


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def field(item: Dict[str, Any], key: str) -> str:
    """Return one API field verbatim, or the declared missing marker."""
    value = (item or {}).get(key)
    if value in (None, ""):
        return NOT_RETURNED
    return str(value)


def _unwrap_list(payload: Dict[str, Any], outer: str, inner: str) -> List[Dict[str, Any]]:
    container = (payload or {}).get(outer) or {}
    items = container.get(inner) if isinstance(container, dict) else container
    if isinstance(items, dict):
        items = [items]
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def _notice(title: str, body: str) -> str:
    lines = ["", "USER CONFIRMATION REQUIRED (nothing has been executed): {0}".format(title),
             "-" * 70]
    lines.extend("  {0}".format(line) for line in body.strip().splitlines())
    lines.append("-" * 70)
    lines.append("  Re-run the same command adding --user-confirmed and")
    lines.append('  --confirmation-scope "<region> <target> <action> approved"')
    lines.append("  ONLY AFTER the customer explicitly approved this notice.")
    return "\n".join(lines)


def _scope_confirms(scope_text: str, required_items: Sequence[str]) -> bool:
    lowered = (scope_text or "").lower()
    return all(str(item).lower() in lowered for item in required_items)


# --------------------------------------------------------------------------- #
# Guest reading validation (approved whitelist, enforced before any dispatch)
# --------------------------------------------------------------------------- #
def validate_guest_request(
    reading: Optional[str], guest_path: Optional[str]
) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(command_line, refusal_reason)`` for one requested reading."""
    if not reading:
        return None, "no --guest-command given; the approved readings are: {0}".format(
            ", ".join(GUEST_READINGS_LINUX))
    command = reading.strip()
    if command not in GUEST_READINGS_LINUX:
        return None, (
            "the requested reading is outside the whitelist approved for this "
            "skill tier. Until the certificate-tier whitelist extension is "
            "signed off, openssl, curl, ss, netstat, firewall queries and "
            "nginx -t are printed as a manual checklist (references/"
            "guest-diagnostics-runbook.md), never dispatched. Approved "
            "readings: {0}".format(", ".join(GUEST_READINGS_LINUX)))
    if not guest_path:
        return None, "the approved readings all take one certificate path via --guest-path"
    path = guest_path.strip()
    if not re.match(LINUX_PATH_RE, path):
        return None, "the path did not pass the conservative character whitelist"
    request = "{0} {1}".format(command, path)
    for token in GUEST_BLOCKED_TOKENS:
        if token in request:
            return None, "the request contains a blocked token and was refused"
    for word in re.split(r"\s+", request):
        if word.lower() in GUEST_BLOCKED_WORDS:
            return None, "the request contains a blocked word and was refused"
    return request, None


# --------------------------------------------------------------------------- #
# Cloud instance evidence
# --------------------------------------------------------------------------- #
def fetch_instance_context(
    region: str,
    instance_id: Optional[str],
    public_ip: Optional[str],
    session_id: str,
    warnings: List[str],
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Return ``(instances, error_code)`` from the instance list query."""
    params: Dict[str, Any] = {"RegionId": region}
    if instance_id:
        params["InstanceIds"] = json.dumps([instance_id])
    elif public_ip:
        params["PublicIpAddresses"] = public_ip
    try:
        items, _page_state = paginate(
            PRODUCT_ECS, ACTION_DESCRIBE_INSTANCES, params, "Instance",
            session_id, PAGE_SIZE, MAX_PAGES, warnings,
            nested_keys=("Instances",),
        )
    except CliError as exc:
        return [], exc.code
    return items, None


def fetch_instance_status(
    region: str,
    instance_id: Optional[str],
    session_id: str,
    warnings: List[str],
) -> str:
    """Best-effort lifecycle state for the named instance ("" when absent)."""
    if not instance_id:
        return ""
    params: Dict[str, Any] = {"RegionId": region}
    params["InstanceId.1"] = instance_id
    try:
        items, _ = paginate(
            PRODUCT_ECS, ACTION_DESCRIBE_INSTANCE_STATUS, params, "InstanceStatus",
            session_id, PAGE_SIZE, MAX_PAGES, warnings,
            nested_keys=("InstanceStatuses",),
        )
    except CliError as exc:
        warnings.append("instance status query degraded: {0}".format(exc.code))
        return ""
    for item in items:
        if str(item.get("InstanceId", "")) == instance_id:
            return str(item.get("Status", "") or "")
    return ""


def instance_public_addresses(instance: Dict[str, Any]) -> List[str]:
    addresses: List[str] = []
    container = (instance or {}).get("PublicIpAddress") or {}
    raw = container.get("IpAddress") if isinstance(container, dict) else None
    if isinstance(raw, list):
        addresses.extend(str(a) for a in raw if a)
    elif raw:
        addresses.append(str(raw))
    eip = (instance or {}).get("EipAddress") or {}
    if isinstance(eip, dict) and eip.get("IpAddress"):
        addresses.append(str(eip["IpAddress"]))
    return sorted(set(addresses))


def instance_is_windows(instance: Dict[str, Any]) -> bool:
    text = "{0} {1}".format(
        (instance or {}).get("OSType", ""), (instance or {}).get("OSName", ""))
    return "windows" in text.lower()


# --------------------------------------------------------------------------- #
# Certificate inventory (read-only CAS query)
# --------------------------------------------------------------------------- #
def _first_present(item: Dict[str, Any], keys: Sequence[str]) -> str:
    """Return the first non-empty value among ``keys``, or the missing marker."""
    for key in keys:
        value = (item or {}).get(key)
        if value not in (None, ""):
            return str(value)
    return NOT_RETURNED


def _epoch_to_date(value: Any) -> str:
    """Render an epoch-millisecond or ISO timestamp without inventing a date."""
    if value in (None, ""):
        return NOT_RETURNED
    text = str(value).strip()
    try:
        stamp = int(float(text))
    except (TypeError, ValueError):
        return text
    if stamp <= 0:
        return NOT_RETURNED
    if stamp > 10 ** 11:            # milliseconds
        stamp = stamp / 1000.0
    try:
        return time.strftime("%Y-%m-%d", time.gmtime(stamp)) + " (UTC)"
    except (OverflowError, OSError, ValueError):
        return text


def _first_time(item: Dict[str, Any], keys: Sequence[str]) -> str:
    """Render the first timestamp-shaped field present in ``item``."""
    for key in keys:
        value = (item or {}).get(key)
        if value not in (None, ""):
            return _epoch_to_date(value)
    return NOT_RETURNED


# Inline boundary assertions for the two renderers above: a missing field, an
# epoch-in-milliseconds value, an ISO string and garbage all stay honest.
assert _epoch_to_date(1730352206000) == "2024-10-31 (UTC)", _epoch_to_date(1730352206000)
assert _epoch_to_date("2025-01-02T03:04:05Z") == "2025-01-02T03:04:05Z"
assert _epoch_to_date(None) == NOT_RETURNED and _epoch_to_date(0) == NOT_RETURNED
assert _epoch_to_date("not-a-date") == "not-a-date"
assert _first_present({"Domain": ""}, CAS_DOMAIN_FIELDS) == NOT_RETURNED
assert _first_present({"Domain": "a.example.com"}, CAS_DOMAIN_FIELDS) == "a.example.com"
assert _first_time({}, CAS_EXPIRY_FIELDS) == NOT_RETURNED


def fetch_certificate_inventory(
    session_id: str,
    warnings: List[str],
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Read the certificate/order inventory with cas ListUserCertificateOrder.

    Two read-only scopes are walked, because they answer different questions:
    ``CERT`` returns the issued and uploaded certificates (status plus validity
    window where the product returns it) and ``CPACK`` returns the certificate
    orders still in the pipeline. Returns ``(rows, error_code)``; an empty list
    is a valid finding and every failure is reported as "not verified".
    """
    rows: List[Dict[str, Any]] = []
    for scope in CAS_ORDER_SCOPES:
        page = 1
        seen_in_scope = 0
        while page <= CAS_MAX_PAGES:
            try:
                payload = run_cli(
                    PRODUCT_CAS, ACTION_LIST_USER_CERTIFICATE_ORDER,
                    {"CurrentPage": page, "ShowSize": CAS_PAGE_SIZE,
                     "OrderType": scope},
                    session_id=session_id, warnings=warnings)
            except CliError as exc:
                return rows, exc.code
            batch = [row for row in (payload.get("CertificateOrderList") or [])
                     if isinstance(row, dict)]
            for row in batch:
                row.setdefault("_Scope", scope)
            rows.extend(batch)
            seen_in_scope += len(batch)
            try:
                total = int(payload.get("TotalCount") or 0)
            except (TypeError, ValueError):
                total = 0
            if len(batch) < CAS_PAGE_SIZE or (total and seen_in_scope >= total):
                break
            page += 1
        else:
            if warnings is not None:
                warnings.append(
                    "stopped paging cas ListUserCertificateOrder ({0}) after "
                    "{1} pages".format(scope, CAS_MAX_PAGES))
    return rows, None


def render_certificate_inventory(
    lines: List[str], rows: List[Dict[str, Any]], error_code: Optional[str]
) -> None:
    """Render the read-only certificate inventory, or mark it NOT VERIFIED."""
    lines.append("certificate inventory (read-only cas ListUserCertificateOrder, "
                 "OrderType={0}, api version {1}):".format(
                     "/".join(CAS_ORDER_SCOPES), CAS_API_VERSION))
    if error_code:
        lines.append("  NOT VERIFIED this run: the certificate read returned "
                     "{0}; do not state the account's certificate list, quota "
                     "or validity dates from this run - read them in the SSL "
                     "certificates console instead.".format(error_code))
        return
    if not rows:
        lines.append("  no issued, uploaded or pending certificate order is "
                     "visible to this credential in the certificate service "
                     "account scope (an empty list is a valid finding, not an "
                     "error).")
        return
    for row in rows:
        status = _first_present(row, ("Status",))
        meaning = CAS_STATUS_MEANINGS.get(status.strip().lower(), "")
        parts = [
            "scope {0}".format(row.get("_Scope") or CAS_ORDER_TYPE_CERT),
            "domain {0}".format(_first_present(row, CAS_DOMAIN_FIELDS)),
            "status {0}{1}".format(status, " ({0})".format(meaning) if meaning else ""),
            "cert type {0}".format(_first_present(row, ("CertType",))),
            "product {0}".format(_first_present(row, ("ProductName",))),
            "order {0}".format(_first_present(row, ("OrderId", "AliyunOrderId"))),
            "issued {0}".format(_first_time(row, CAS_ISSUE_FIELDS)),
            "expires {0}".format(_first_time(row, CAS_EXPIRY_FIELDS)),
        ]
        lines.append("  - " + " | ".join(parts))


# --------------------------------------------------------------------------- #
# Outside-in verification (public resolver + real browser-grade handshake)
# --------------------------------------------------------------------------- #
def verify_domain(
    domain: str,
    expected_addresses: Sequence[str],
    port_note: int,
) -> Dict[str, Any]:
    """Resolve and handshake one domain; compare with the instance addresses.

    When the system resolver and public DoH disagree, both views are probed:
    the local one may be a proxy or split-horizon answer, while the public
    one is what a visitor sees. The public probe connects to the public IP
    but keeps SNI and certificate-name checks on the customer domain.
    """
    dns = resolve_domain(domain)
    probe = probe_https(domain, port=port_note)
    public_dns = resolve_domain_public(domain)
    resolved = [a for a in dns.get("addresses", []) if a]
    public_resolved = [a for a in public_dns.get("addresses", []) if a]
    drift = "n/a"
    if expected_addresses and resolved:
        drift = "consistent" if set(resolved) & set(expected_addresses) else "MISMATCH"
    public_drift = "n/a"
    if expected_addresses and public_resolved:
        public_drift = ("consistent"
                        if set(public_resolved) & set(expected_addresses)
                        else "MISMATCH")
    result: Dict[str, Any] = {
        "domain": domain,
        "dns": dns,
        "tls": probe,
        "public_dns": public_dns,
        "resolution_drift": drift,
        "public_resolution_drift": public_drift,
    }
    if public_resolved and set(public_resolved) != set(resolved):
        result["resolver_view_mismatch"] = True
        for address in public_resolved[:2]:
            public_probe = probe_https(domain, port=port_note, address=address)
            result["public_tls"] = public_probe
            if public_probe.get("verdict") not in (
                    "connect-timeout", "blocked", "dns-failed"):
                break
    return result


def _tls_view(tls: Dict[str, Any]) -> List[str]:
    parts = ["TLS {0}".format(tls.get("verdict", ""))]
    if tls.get("error_code"):
        parts.append("maps to {0}".format(tls["error_code"]))
    if tls.get("subject"):
        parts.append("subject {0}".format(tls["subject"]))
    if tls.get("san_dns"):
        parts.append("SAN {0}".format(", ".join(tls["san_dns"][:8])))
    if tls.get("issuer"):
        parts.append("issuer {0}".format(tls["issuer"]))
    if tls.get("not_after"):
        parts.append("valid until {0}".format(tls["not_after"]))
    if tls.get("days_left") is not None:
        parts.append("days left {0}".format(tls["days_left"]))
    if tls.get("fingerprint_sha256"):
        parts.append("fingerprint {0}".format(tls["fingerprint_sha256"][:16]))
    if tls.get("certificate_verified") is False:
        parts.append("served certificate rejected by verification")
    return parts


def domain_line(result: Dict[str, Any]) -> str:
    parts = [
        "domain {0}".format(result["domain"]),
        "DNS {0} ({1})".format(
            result["dns"].get("verdict", ""),
            ", ".join(result["dns"].get("addresses", [])) or "no answer",
        ),
    ]
    parts.extend(_tls_view(result["tls"]))
    parts.append("resolution vs instance: {0}".format(result["resolution_drift"]))
    line = " | ".join(parts)
    public_tls = result.get("public_tls")
    if public_tls:
        public_dns = result.get("public_dns") or {}
        view = ["public view", "DNS {0} ({1})".format(
            public_dns.get("verdict", ""),
            ", ".join(public_dns.get("addresses", [])) or "no answer")]
        view.extend(_tls_view(public_tls))
        view.append("resolution vs instance: {0}".format(
            result.get("public_resolution_drift", "n/a")))
        line += "\n  " + " | ".join(view)
    return line


# --------------------------------------------------------------------------- #
# Branch renderers
# --------------------------------------------------------------------------- #
def render_branch_table(lines: List[str], heading: str, branches: Sequence[Sequence[str]]) -> None:
    lines.append(heading)
    for index, (condition, finding, action) in enumerate(branches, 1):
        lines.append("  {0}. WHEN {1}".format(index, condition))
        lines.append("     FINDING: {0}".format(finding))
        lines.append("     NEXT: {0}".format(action))


def render_error_code_guide(lines: List[str], wanted: Sequence[str]) -> None:
    quoted = set(wanted)
    guide = [row for row in ERROR_CODE_GUIDE if row[0] in quoted]
    if not guide:
        return
    lines.append("Quoted error strings from the customer's own text, interpreted:")
    for code, reading, action in guide:
        lines.append("  - {0}".format(code))
        lines.append("    reading: {0}".format(reading))
        lines.append("    action:  {0}".format(action))


def render_checklist(lines: List[str], web_server: Optional[str], guest_os: str) -> None:
    lines.append("Manual deployment checklist (customer-executed; this skill "
                 "never edits or reloads anything):")
    servers = [web_server] if web_server else list(WEB_SERVERS)
    for server in servers:
        steps = WEB_SERVER_CHECKLISTS.get(server)
        if not steps:
            continue
        lines.append("  [{0}]".format(server))
        lines.extend("    {0}".format(step) for step in steps)
    lines.append("Suggested information-only probe commands for the customer to run")
    lines.append("and paste back ({0}):".format(guest_os))
    for command in SUGGESTED_EGRESS_COMMANDS.get(guest_os, ()):
        lines.append("  $ {0}".format(command))
    lines.append("  note: {0}".format(EGRESS_PROBE_NOTE))


# --------------------------------------------------------------------------- #
# Gated dispatch modes
# --------------------------------------------------------------------------- #
def run_guest_probe(args: argparse.Namespace, session_id: str) -> Tuple[List[str], str, str]:
    """ONE confirmed, whitelisted, information-only guest reading."""
    lines: List[str] = []
    warnings: List[str] = []
    instances, error_code = fetch_instance_context(
        args.region_id, args.instance_id, args.public_ip, session_id, warnings)
    if error_code or not instances:
        lines.append("instance context unavailable: {0}".format(error_code or "no match"))
        return lines, STATUS_FAIL, "fix the instance selector and re-run"
    instance = instances[0]
    if instance_is_windows(instance):
        lines.append(
            "refused: no Windows guest reading is on the approved whitelist "
            "yet for this tier. Use the printed Windows checklist instead "
            "(references/ssl-cert-deployment__guest-diagnostics-runbook.md).")
        return lines, STATUS_FAIL, "route to the manual Windows checklist"
    request, refusal = validate_guest_request(args.guest_command, args.guest_path)
    if refusal:
        lines.append("refused: {0}".format(refusal))
        return lines, STATUS_FAIL, "adjust the request inside the whitelist or route to the manual checklist"
    target = args.instance_id or field(instance, "InstanceId")
    if not (args.user_confirmed and _scope_confirms(
            args.confirmation_scope, [args.region_id, target,
                                      args.guest_command or ""])):
        lines.append(_notice(
            "one guest reading",
            "will dispatch ONE command to instance {0} in {1} through Cloud "
            "Assistant:\n"
            "  {2}\n"
            "nature: information-only (file metadata / listing / line count); "
            "no file contents are printed, nothing is written, nothing is "
            "restarted.\n"
            "reversible: yes trivially - a query leaves no state behind.\n"
            "one approval covers exactly this one command.".format(
                target, args.region_id, request)))
        return lines, STATUS_DEGRADED, "get the customer's explicit approval, then re-run with --user-confirmed and --confirmation-scope"
    lines.append("confirmed dispatch: {0} -> {1} ({2})".format(request, target, args.region_id))
    try:
        payload = run_cli(
            PRODUCT_ECS, ACTION_RUN_COMMAND,
            {
                "RegionId": args.region_id,
                "Type": CLOUD_ASSISTANT_KIND_LINUX,
                "CommandContent": request,
                "InstanceId.1": target,
                "Name": "ssl-skill-inspect",
                "Description": "one whitelisted information-only reading",
                "Timeout": GUEST_COMMAND_TIMEOUT,
            },
            session_id=session_id, warnings=warnings)
    except CliError as exc:
        lines.append("dispatch failed: {0}".format(exc))
        status = STATUS_DEGRADED if exc.code in (CODE_NO_PERMISSION, CODE_IMPLICIT_DENY, CODE_API_ERROR, CODE_CLI_UNAVAILABLE) else STATUS_FAIL
        return lines, status, "check the assistant agent status and the granted actions in references/ram-policies.md"
    invoke_id = str(payload.get("InvokeId", "") or "")
    if not invoke_id:
        lines.append("no invoke id returned; cannot read the result")
        return lines, STATUS_DEGRADED, "verify the assistant accepted the command in the console"
    lines.append("invoke id: {0}".format(invoke_id))
    result = wait_for_invocation(args.region_id, invoke_id, target, session_id, warnings)
    if result is None:
        lines.append("the invocation did not settle within {0}s; the raw "
                     "invoke id is above and can be re-read later".format(POLL_DEADLINE_SECONDS))
        return lines, STATUS_DEGRADED, "re-read the invocation later or ask the customer to run the command"
    status = result.get("InvocationStatus") or result.get("InvokeRecordStatus") or ""
    output = _decode_output(result.get("Output"))
    lines.append("guest reading finished with status {0}".format(status or NOT_RETURNED))
    if output:
        lines.append("---- guest output (information-only) ----")
        lines.extend(mask_credentials(output).splitlines())
    if warnings:
        lines.append("degradation log: " + "; ".join(warnings))
    return lines, STATUS_OK, "interpret the pasted metadata against references/ssl-cert-deployment__guest-diagnostics-runbook.md"


def wait_for_invocation(
    region: str,
    invoke_id: str,
    instance_id: str,
    session_id: str,
    warnings: List[str],
) -> Optional[Dict[str, Any]]:
    """Poll the invocation table until the target instance settles."""
    deadline = time.time() + POLL_DEADLINE_SECONDS
    while time.time() < deadline:
        try:
            payload = run_cli(
                PRODUCT_ECS, ACTION_DESCRIBE_INVOCATIONS,
                {
                    "RegionId": region,
                    "InvokeId": invoke_id,
                    "IncludeOutput": "true",
                    "ContentEncoding": "Base64",
                },
                session_id=session_id,
                timeout=CLI_TIMEOUT_SECONDS, warnings=warnings)
        except CliError as exc:
            warnings.append("invocation read degraded: {0}".format(exc.code))
            return None
        for invocation in _unwrap_list(payload, "Invocations", "Invocation"):
            for record in _unwrap_list(invocation, "InvokeInstances", "InvokeInstance"):
                if str(record.get("InstanceId", "")) not in ("", instance_id):
                    continue
                state = str(record.get("InvocationStatus") or
                            record.get("InvokeRecordStatus") or "")
                if state in INVOCATION_TERMINAL:
                    return record
        time.sleep(POLL_INTERVAL_SECONDS)
    return None


def _decode_output(raw: Any) -> str:
    if not raw:
        return ""
    text = str(raw)
    try:
        decoded = base64.b64decode(text, validate=False)
        return decoded.decode("utf-8", "replace")
    except Exception:
        return text


def run_snapshot_backup(args: argparse.Namespace, session_id: str) -> Tuple[List[str], str, str]:
    """ONE confirmed backup snapshot of one named disk."""
    lines: List[str] = []
    warnings: List[str] = []
    if not args.disk_id:
        lines.append("--disk-id is mandatory for the backup: the snapshot "
                     "action takes exactly one disk (verified required "
                     "parameter).")
        return lines, STATUS_FAIL, "re-run with --disk-id d-... for the disk the customer is about to change"
    if not (args.user_confirmed and _scope_confirms(
            args.confirmation_scope, [args.region_id, args.disk_id])):
        lines.append(_notice(
            "pre-change snapshot",
            "will create ONE snapshot of disk {0} in {1}.\n"
            "{2}\n"
            "reversible: the snapshot can be deleted at any time afterwards; "
            "the disk itself is not touched.\n"
            "one approval covers exactly this one disk.".format(
                args.disk_id, args.region_id, SNAPSHOT_NOTICE)))
        return lines, STATUS_DEGRADED, "get the customer's explicit approval, then re-run with --user-confirmed and --confirmation-scope"
    name = args.snapshot_name or "ssl-skill-prechange-{0}".format(int(time.time()))
    if not re.match(SNAPSHOT_NAME_RE, name):
        lines.append("the snapshot name did not pass validation")
        return lines, STATUS_FAIL, "re-run with a simple ASCII snapshot name"
    lines.append("confirmed dispatch: one backup snapshot of {0}".format(args.disk_id))
    try:
        payload = run_cli(
            PRODUCT_ECS, ACTION_CREATE_SNAPSHOT,
            {
                "RegionId": args.region_id,
                "DiskId": args.disk_id,
                "SnapshotName": name,
                "Description": "backup before a customer-run certificate change",
            },
            session_id=session_id, warnings=warnings)
    except CliError as exc:
        lines.append("backup dispatch failed: {0}".format(exc))
        return lines, STATUS_DEGRADED, "verify the granted actions in references/ram-policies.md or create the snapshot in the console"
    lines.append("snapshot accepted: {0}".format(field(payload, "SnapshotId")))
    lines.append("the customer can watch progress in the console snapshot list; "
                 "continue with the manual certificate change only after it "
                 "reaches 100 percent.")
    lines.append("after the change succeeds, delete temporary snapshots in the "
                 "console to stop the billing (manual step, link above).")
    if warnings:
        lines.append("degradation log: " + "; ".join(warnings))
    return lines, STATUS_OK, "hand the customer the change steps from references/ssl-cert-deployment__nginx-iis-deploy-checklist.md"


# --------------------------------------------------------------------------- #
# Offline modes
# --------------------------------------------------------------------------- #
def run_faq(args: argparse.Namespace) -> Tuple[List[str], str, str]:
    lines: List[str] = []
    topics = [args.faq_topic] if args.faq_topic else sorted(PRODUCT_FAQ_TOPICS)
    for topic in topics:
        entry = PRODUCT_FAQ_TOPICS.get(str(topic))
        if not entry:
            lines.append("unknown topic {0!r}; available: {1}".format(
                topic, ", ".join(sorted(PRODUCT_FAQ_TOPICS))))
            return lines, STATUS_FAIL, "pick one of the listed topics"
        lines.append("Q&A topic: {0}".format(topic))
        for row in entry:
            lines.append("  - {0}".format(row))
        lines.append("  {0}".format(PRODUCT_RULES_CONFIDENCE))
    return lines, STATUS_OK, "relay the answer verbatim and add the confidence tag"


def run_checklist(args: argparse.Namespace) -> Tuple[List[str], str, str]:
    lines: List[str] = []
    guest_os = args.guest_os if args.guest_os in SUGGESTED_EGRESS_COMMANDS else "linux"
    render_checklist(lines, args.web_server, guest_os)
    lines.append("")
    render_branch_table(lines, "Deployment-effectiveness branches (what the "
                        "served certificate names mean):", DEPLOY_BRANCHES)
    lines.append("")
    render_branch_table(lines, "Egress triage branches (what the paste-back means):",
                        APPLY_FAIL_BRANCHES)
    return lines, STATUS_OK, "wait for the customer to paste the readings back"


# --------------------------------------------------------------------------- #
# Main report mode
# --------------------------------------------------------------------------- #
def run_report(args: argparse.Namespace, session_id: str) -> Tuple[List[str], str, str, List[str]]:
    lines: List[str] = []
    warnings: List[str] = []
    identity, identity_error = fetch_caller_identity(session_id, warnings)
    lines.append("identity: {0}".format(uid_traceability_label(identity)))
    if identity_error:
        lines.extend("  {0}".format(t) for t in identity_guidance_lines(identity_error))

    selector_given = bool(args.instance_id or args.public_ip)
    if not selector_given and not args.domain:
        lines.append("no instance selector given: neither an instance id nor "
                     "a public ip.")
        return lines, STATUS_FAIL, "ask the customer for the ECS instance id or the public IP plus the region id", warnings

    if selector_given:
        instances, error_code = fetch_instance_context(
            args.region_id, args.instance_id, args.public_ip, session_id, warnings)
    else:
        instances, error_code = [], ""
        lines.append("no instance selector given - continuing with the "
                     "outside-in TLS view for {0} (cloud and guest evidence "
                     "are missing).".format(", ".join(args.domain)))
        warnings.append("no instance selector given; cloud and guest evidence are missing")
    instance = None
    addresses: List[str] = []
    status_state = ""
    if error_code:
        if not args.domain:
            lines.append("instance lookup failed: {0}".format(error_code))
            next_action = "check the granted actions in references/ram-policies.md and the region id"
            return lines, STATUS_DEGRADED, next_action, warnings
        lines.append("instance lookup failed: {0} - continuing with the "
                     "outside-in TLS view for {1} (no cloud instance context)."
                     .format(error_code, ", ".join(args.domain)))
        warnings.append("cloud instance context unavailable: {0}".format(error_code))
    elif not instances:
        if not args.domain:
            lines.append("no instance matched in region {0}: the id or address may "
                         "belong to another region or another account (cross-account "
                         "setups appear in real tickets, e.g. ticket T-6A73F6B0)."
                         .format(args.region_id))
            return lines, STATUS_FAIL, "confirm the region and the account, then re-run", warnings
        if selector_given:
            lines.append("no instance matched in region {0} for the given selector - "
                         "continuing with the outside-in TLS view for {1} (the selector "
                         "may belong to another region or account)."
                         .format(args.region_id, ", ".join(args.domain)))
            warnings.append("no matching instance for the given selector")
    else:
        instance = instances[0]

    mainland = is_mainland_region(args.region_id)
    if instance:
        instance_id = field(instance, "InstanceId")
        addresses = instance_public_addresses(instance)
        windows = instance_is_windows(instance)
        status_state = fetch_instance_status(
            args.region_id, instance_id, session_id, warnings)
        lines.append("instance {0} in {1} ({2})".format(
            instance_id, args.region_id, field(instance, "InstanceName")))
        lines.append("  lifecycle state: {0} (api version {1})".format(
            status_state or field(instance, "Status"), ECS_API_VERSION))
        lines.append("  guest kind: {0}".format("windows" if windows else "linux"))
        lines.append("  public addresses: {0}".format(", ".join(addresses) or NOT_RETURNED))
    else:
        windows = False
        lines.append("instance context: not available this run (outside-in TLS "
                     "view only; cloud and guest evidence are missing).")
    lines.append("  network lens: {0}".format(
        "region inside mainland China (cross-border paths apply)" if mainland
        else "region outside the mainland backbone (cross-border wording does NOT apply)"))

    domains = list(args.domain or [])
    inventory_rows, inventory_error = fetch_certificate_inventory(
        session_id, warnings)
    if inventory_error:
        warnings.append(
            "cas {0} degraded: {1}; the certificate inventory is marked NOT "
            "VERIFIED for this run".format(
                ACTION_LIST_USER_CERTIFICATE_ORDER, inventory_error))
    render_certificate_inventory(lines, inventory_rows, inventory_error)

    domain_results: List[Dict[str, Any]] = []
    if domains:
        lines.append("outside-in HTTPS view (verification left fully ON, so the "
                     "verdict equals what a visitor's browser shows):")
        for domain in domains:
            result = verify_domain(domain, addresses, args.tls_port)
            domain_results.append(result)
            lines.append("  {0}".format(domain_line(result)))
            if result.get("resolver_view_mismatch"):
                lines.append("      note: the local resolver answer differs from "
                             "public DNS; the public view is what a visitor sees "
                             "(a local proxy can answer for the domain).")
            detail = result["tls"].get("detail")
            if detail:
                lines.append("      detail: {0}".format(detail))
    else:
        lines.append("no --domain given: the certificate and resolution checks "
                     "are skipped; ask the customer which host name the browser "
                     "visits.")

    quoted_codes: List[str] = []
    for result in domain_results:
        for key in ("tls", "public_tls"):
            code = (result.get(key) or {}).get("error_code")
            if code and str(code) not in quoted_codes:
                quoted_codes.append(str(code))
    quoted_codes.extend(args.quoted_error or [])
    if quoted_codes:
        lines.append("")
        render_error_code_guide(lines, quoted_codes)

    if args.symptom == "apply-fail" or "deadline" in " ".join(args.quoted_error or []).lower():
        lines.append("")
        lines.append("ACME endpoint ownership (DNS answer versus the Cloudflare edge range "
                     "{0}):".format(CLOUDFLARE_LE_CIDR))
        for endpoint in list(ACME_ENDPOINTS) + list(DNS_PROVIDER_ENDPOINTS):
            summary = summarize_endpoint_ip(endpoint, CLOUDFLARE_LE_CIDR)
            verdict = "overseas edge address" if summary.get("in_cidr") else (
                "domestic or other address" if summary.get("addresses") else
                "not resolvable from here")
            lines.append("  {0}: {1} -> {2}".format(
                endpoint, ", ".join(summary.get("addresses", [])) or "none", verdict))
        lines.append("  mainland-region-plus-overseas-edge means the "
                     "cross-border branch: this is not a platform block.")

    lines.append("")
    lines.append(TRIAGE_TREE_INTRO)
    symptom = args.symptom
    if symptom == "apply-fail":
        render_branch_table(lines, "Egress / issuance branches:", APPLY_FAIL_BRANCHES)
    elif symptom == "deploy-not-effective":
        render_branch_table(lines, "Deployment-effectiveness branches:", DEPLOY_BRANCHES)
    elif symptom == "cert-invalid":
        render_branch_table(lines, "Certificate-body branches:", CERT_BODY_BRANCHES)
    elif symptom == "https-unreachable":
        render_branch_table(lines, "HTTPS-reachability branches:", HTTPS_BRANCHES)
    elif symptom == "product-rules":
        render_branch_table(lines, "Product-rule branches:", PRODUCT_RULES_BRANCHES)
        lines.append("  {0}".format(PRODUCT_RULES_CONFIDENCE))
    else:
        render_branch_table(lines, "All branches (state the customer's exact symptom to narrow):",
                            APPLY_FAIL_BRANCHES)
        render_branch_table(lines, "", DEPLOY_BRANCHES)
        render_branch_table(lines, "", CERT_BODY_BRANCHES)
        render_branch_table(lines, "", HTTPS_BRANCHES)

    lines.append("")
    lines.append("Common misconceptions to correct in the reply (support wording):")
    for claim, correction in MISCONCEPTIONS:
        lines.append("  - claim: {0}".format(claim))
        lines.append("    correction: {0}".format(correction))

    if args.web_server or symptom in ("deploy-not-effective", "cert-invalid", "apply-fail"):
        lines.append("")
        render_checklist(lines, args.web_server, "windows" if windows else "linux")

    lines.append("")
    lines.append("Before any guided server-side change: {0}".format(SNAPSHOT_FIRST_RULE))
    lines.append(SNAPSHOT_NOTICE)
    lines.append("")
    lines.append("Out-of-scope signals (recognize, then hand off; never diagnose here):")
    for signal, target in HANDOFFS:
        lines.append("  - {0} -> {1}".format(signal, target))
    lines.append("")
    lines.append("Evidence surface of this run (what is machine-read and what is "
                 "deliberately customer-read):")
    for topic, surface in EVIDENCE_SURFACE:
        lines.append("  - {0}: {1}".format(topic, surface))
    lines.append("Capability limits of this run: {0}".format(NOT_VERIFIED_NOTE))

    status = STATUS_OK
    next_action = "relay the branches whose WHEN matched, with the pasted readings"
    if identity_error:
        status = STATUS_DEGRADED
        next_action = "repair the credential chain (aliyun sts get-caller-identity), then re-run for the account label"
    if instance is None:
        status = STATUS_DEGRADED
        next_action = ("relay the outside-in TLS verdict; ask for an instance id "
                       "that the current identity can read to add cloud and guest evidence")
    if domain_results and any(r["tls"].get("verdict") == "blocked" for r in domain_results):
        status = STATUS_DEGRADED
        next_action = "the probe host egress is restricted: ask the customer to run the printed manual checks instead"
    return lines, status, next_action, warnings


# --------------------------------------------------------------------------- #
# Argument surface
# --------------------------------------------------------------------------- #
def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ssl_cert_deployment_report.py",
        description="ECS SSL certificate application and deployment triage "
                    "(single entry point; see SKILL.md)",
    )
    parser.add_argument("--region-id", default=None,
                        help="ECS region id, mandatory for cloud evidence modes")
    parser.add_argument("--instance-id", default=None)
    parser.add_argument("--public-ip", default=None,
                        help="instance public address, when the id is unknown")
    parser.add_argument("--domain", action="append", default=None,
                        help="repeatable: host name(s) to verify from outside")
    parser.add_argument("--symptom", default="auto", choices=["auto"] + list(SYMP_SYMPTOMS))
    parser.add_argument("--web-server", default=None, choices=list(WEB_SERVERS))
    parser.add_argument("--guest-os", default="auto",
                        choices=["auto", "linux", GUEST_WINDOWS])
    parser.add_argument("--mode", default="report",
                        choices=["report", "guest-probe", "snapshot-backup",
                                 "checklist", "faq"])
    parser.add_argument("--faq-topic", default=None,
                        choices=sorted(PRODUCT_FAQ_TOPICS))
    parser.add_argument("--guest-command", default=None,
                        help="one approved information-only reading, e.g. stat")
    parser.add_argument("--guest-path", default=None,
                        help="certificate or key file path for the reading")
    parser.add_argument("--disk-id", default=None,
                        help="target disk for the gated backup snapshot")
    parser.add_argument("--snapshot-name", default=None)
    parser.add_argument("--quoted-error", action="append", default=None,
                        help="customer-quoted error string or code to interpret")
    parser.add_argument("--tls-port", type=int, default=443)
    parser.add_argument("--user-confirmed", action="store_true",
                        help="set ONLY after the customer approved the notice")
    parser.add_argument("--confirmation-scope", default="",
                        help='must name this run\'s region, target and action, e.g. "cn-hangzhou i-abc stat approved"')
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--check-auth-only", action="store_true")
    args = parser.parse_args(argv)
    if args.tls_port < 1 or args.tls_port > 65535:
        parser.error("--tls-port must be between 1 and 65535")
    return args


def _region_required(args: argparse.Namespace) -> bool:
    return args.mode in ("report", "guest-probe", "snapshot-backup")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    session_id = new_session_id()
    lines: List[str] = []
    warnings: List[str] = []
    status = STATUS_OK
    next_action = ""

    if args.check_auth_only:
        warnings_log: List[str] = []
        identity, identity_error = fetch_caller_identity(session_id, warnings_log)
        lines.append("identity: {0}".format(uid_traceability_label(identity)))
        lines.append("user-agent sample: {0}".format(build_user_agent(session_id)))
        if identity_error:
            lines.extend("  {0}".format(t) for t in identity_guidance_lines(identity_error))
            status, next_action = STATUS_FAIL, "verify the CLI default credential chain with aliyun sts get-caller-identity"
        else:
            status, next_action = STATUS_OK, "credential chain proven; run the report mode"
        warnings = warnings_log
    elif args.mode == "faq":
        lines, status, next_action = run_faq(args)
    elif args.mode == "checklist":
        lines, status, next_action = run_checklist(args)
    elif _region_required(args) and not args.region_id:
        lines.append("a region id is required for this mode and is never guessed.")
        status, next_action = STATUS_FAIL, "ask the customer which region the instance lives in"
    elif args.mode == "guest-probe":
        lines, status, next_action = run_guest_probe(args, session_id)
    elif args.mode == "snapshot-backup":
        lines, status, next_action = run_snapshot_backup(args, session_id)
    else:
        lines, status, next_action, warnings = run_report(args, session_id)

    body = "\n".join(lines)

    # One name for one deliverable: the User-Agent already carries the package
    # name, and a banner naming the retired single skill split attribution.
    banner = FINAL_ANSWER_BANNER.format(skill=_PACKAGE_NAME, session_id=session_id)
    report = "{0}\n{1}\n{2}\n\nSTATUS: {3}\nNEXT_ACTION: {4}\n".format(
        banner, BANNER, body, status, next_action)

    if args.as_json:
        payload = {
            "skill": SKILL_NAME,
            "session_id": session_id,
            "user_agent": build_user_agent(session_id),
            "mode": args.mode,
            "status": status,
            "next_action": next_action,
            "lines": lines,
            "warnings": warnings,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(report)
    for warning in warnings:
        print("[WARN] {0}".format(mask_credentials(warning)), file=sys.stderr)
    return EXIT_BY_STATUS.get(status, 2)


if __name__ == "__main__":
    sys.exit(main())
