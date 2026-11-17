#!/usr/bin/env python3
"""rdp_diagnose.py -- Single entry point for Windows Remote Desktop (RDP) diagnosis.

Scope (RO+G): cloud-side query reads run automatically; the one write-class
action (the ECS Cloud Assistant command dispatch) is reached only through an
explicit confirmation gate and only to run a SINGLE whitelisted, non-mutating
query command inside the guest. This script never changes any resource: it does
not unlock an account, open a port, authorize a security group, reset a
password, or restart an instance -- those are manual steps it hands off.

Evidence chain, per-run session id, retry / timeout / credential masking all
live in the shared transport layer ``_cli``. The final answer must relay this
script's ``Summary`` block and the ``STATUS`` / ``NEXT_ACTION`` contract verbatim
and cite only values actually returned.

Usage examples (run from the skill directory):

    python3 scripts/areas/windows_rdp/rdp_diagnose.py --region-id cn-hangzhou \
        --instance-id i-2zeexamplea78f35439f --port 3389 \
        --error-string "for security reasons, the remote computer cannot be authenticated"

    python3 scripts/areas/windows_rdp/rdp_diagnose.py --region-id ap-southeast-1 \
        --public-ip 8.219.4.5 --port 3389

    # disclose the exact guest query command WITHOUT running it (no --confirm):
    python3 scripts/areas/windows_rdp/rdp_diagnose.py --region-id cn-hangzhou \
        --instance-id i-2zeexamplea78f35439f --guest-check rdp-listeners

    # dispatch ONE whitelisted non-mutating query after explicit confirmation:
    python3 scripts/areas/windows_rdp/rdp_diagnose.py --region-id cn-hangzhou \
        --instance-id i-2zeexamplea78f35439f --guest-check rdp-listeners \
        --confirm confirm:rdp-listeners

    python3 scripts/areas/windows_rdp/rdp_diagnose.py --check-auth-only
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import base64
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

import _cli
from _cli import CliError, new_session_id, run_cli
from _constants import (
    ACTION_DESCRIBE_CLOUD_ASSISTANT_STATUS,
    ACTION_DESCRIBE_INSTANCES,
    ACTION_DESCRIBE_INSTANCE_VNC_URL,
    ACTION_DESCRIBE_INVOCATIONS,
    ACTION_DESCRIBE_SECURITY_GROUP_ATTRIBUTE,
    ACTION_RUN_COMMAND,
    CLI_GUEST_POLL_TIMEOUT_SECONDS,
    CODE_COMMAND_REFUSED,
    CODE_NOT_CONFIRMED,
    CONSOLE_ENTRIES,
    DEFAULT_RDP_PORT,
    GUEST_QUERY_WHITELIST,
    HANDOFF_MATRIX,
    MAINLAND_CN_REGION_PREFIX,
    OVERSEAS_CN_REGIONS,
    PRODUCT_ECS,
    SNAPSHOT_ADVISORY,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
)
from sts_token import fetch_caller_identity, identity_guidance_lines, uid_traceability_label


# ---------------------------------------------------------------------------
# Small nested-response helpers
# ---------------------------------------------------------------------------
def _dig(node: Any, path: List[str]) -> Any:
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


# ---------------------------------------------------------------------------
# Step 0/2: locate the instance and read its cloud-side facts
# ---------------------------------------------------------------------------
def describe_instance(
    region: str,
    instance_id: Optional[str],
    public_ip: Optional[str],
    session_id: str,
    warnings: List[str],
    errors: List[Dict[str, str]],
) -> Optional[Dict[str, Any]]:
    params: Dict[str, Any] = {"RegionId": region}
    if instance_id:
        params["InstanceIds"] = json.dumps([instance_id])
    elif public_ip:
        params["PublicIpAddresses"] = public_ip
    try:
        payload = run_cli(PRODUCT_ECS, ACTION_DESCRIBE_INSTANCES, params,
                          session_id=session_id, warnings=warnings)
    except CliError as exc:
        errors.append({"step": "DescribeInstances", "code": exc.code, "detail": exc.message})
        return None

    instances = _as_list(_dig(payload, ["Instances", "Instance"]))
    if not instances:
        warnings.append("no instance matched in {0} (checked {1})".format(
            region, instance_id or public_ip))
        return None
    inst = instances[0]
    pub_ips = _as_list(_dig(inst, ["PublicIpAddress", "IpAddress"]))
    eip = inst.get("EipAddress") or {}
    if isinstance(eip, dict) and eip.get("IpAddress"):
        pub_ips.append(eip["IpAddress"])
    sg_ids = _as_list(_dig(inst, ["SecurityGroupIds", "SecurityGroupIds"]))
    return {
        "instance_id": inst.get("InstanceId"),
        "status": inst.get("Status"),
        "os_type": inst.get("OSType"),
        "os_name": inst.get("OSName"),
        "instance_type": inst.get("InstanceType"),
        "memory_gib": _to_gib(inst.get("Memory")),
        "cpu": inst.get("Cpu"),
        "zone_id": inst.get("ZoneId"),
        "region_id": inst.get("RegionId") or region,
        "public_ips": [str(x) for x in pub_ips if x],
        "security_group_ids": [str(x) for x in sg_ids if x],
        "network_type": inst.get("InstanceNetworkType"),
    }


def _to_gib(mib: Any) -> Optional[float]:
    try:
        return round(int(mib) / 1024.0, 1)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Step 2: security group ingress evaluation for the RDP port
# ---------------------------------------------------------------------------
def check_security_group(
    region: str, sg_id: str, port: int,
    session_id: str, warnings: List[str], errors: List[Dict[str, str]],
) -> Dict[str, Any]:
    params = {"RegionId": region, "SecurityGroupId": sg_id, "Direction": "ingress"}
    try:
        payload = run_cli(PRODUCT_ECS, ACTION_DESCRIBE_SECURITY_GROUP_ATTRIBUTE, params,
                          session_id=session_id, warnings=warnings)
    except CliError as exc:
        errors.append({"step": "DescribeSecurityGroupAttribute", "sg": sg_id,
                       "code": exc.code, "detail": exc.message})
        return {"sg_id": sg_id, "evaluated": False}

    rules = _as_list(_dig(payload, ["Permissions", "Permission"]))
    accept_from = []
    open_world = False
    for r in rules:
        if str(r.get("Policy", "")).lower() != "accept":
            continue
        lo, hi = _parse_port_range(r.get("PortRange"))
        proto = str(r.get("IpProtocol", "")).lower()
        if proto not in ("tcp", "all"):
            continue
        if not _range_covers_port((lo, hi), port):
            continue
        src = r.get("SourceCidrIp") or r.get("DestCidrIp") or ""
        accept_from.append(str(src))
        if str(src) in ("0.0.0.0/0", "::/0"):
            open_world = True
    return {
        "sg_id": sg_id,
        "evaluated": True,
        "port": port,
        "allowed": bool(accept_from),
        "accept_sources": accept_from,
        "wide_open_to_internet": open_world,
    }


def _parse_port_range(value: Any) -> Tuple[int, int]:
    text = str(value or "")
    if "/" in text:
        lo, hi = text.split("/", 1)
    else:
        lo = hi = text
    try:
        return int(lo), int(hi)
    except ValueError:
        return -1, -1


def _range_covers_port(bounds: Tuple[int, int], port: int) -> bool:
    lo, hi = bounds
    if lo == -1 or hi == -1:      # all-port / icmp style
        return True
    if lo == 0 and hi == 0:       # "-1/-1" sentinel meaning all ports
        return True
    return lo <= port <= hi


# ---------------------------------------------------------------------------
# Step 3: Cloud Assistant readiness gate
# ---------------------------------------------------------------------------
def check_cloud_assistant(
    region: str, instance_id: str,
    session_id: str, warnings: List[str], errors: List[Dict[str, str]],
) -> Dict[str, Any]:
    params = {"RegionId": region, "InstanceId.1": instance_id}
    try:
        payload = run_cli(PRODUCT_ECS, ACTION_DESCRIBE_CLOUD_ASSISTANT_STATUS, params,
                          session_id=session_id, warnings=warnings)
    except CliError as exc:
        errors.append({"step": "DescribeCloudAssistantStatus", "code": exc.code,
                       "detail": exc.message})
        return {"checked": False, "ready": False}
    items = _as_list(_dig(payload, ["InstanceCloudAssistantStatusSet", "InstanceCloudAssistantStatus"]))
    ready = False
    version = None
    for it in items:
        if str(it.get("CloudAssistantStatus", "")).lower() == "true":
            ready = True
        version = it.get("CloudAssistantVersion") or version
    return {"checked": True, "ready": ready, "agent_version": version}


# ---------------------------------------------------------------------------
# Rescue channel (step 6 bypass)
# ---------------------------------------------------------------------------
def fetch_vnc_url(
    region: str, instance_id: str,
    session_id: str, warnings: List[str], errors: List[Dict[str, str]],
) -> Optional[str]:
    params = {"RegionId": region, "InstanceId": instance_id}
    try:
        payload = run_cli(PRODUCT_ECS, ACTION_DESCRIBE_INSTANCE_VNC_URL, params,
                          session_id=session_id, warnings=warnings)
    except CliError as exc:
        errors.append({"step": "DescribeInstanceVncUrl", "code": exc.code, "detail": exc.message})
        return None
    for value in _iter_strings(payload):
        if "vnc" in value.lower() or value.startswith("http"):
            return value
    return None


def _iter_strings(node: Any):
    if isinstance(node, dict):
        for v in node.values():
            for s in _iter_strings(v):
                yield s
    elif isinstance(node, list):
        for v in node:
            for s in _iter_strings(v):
                yield s
    elif isinstance(node, str):
        yield node


# ---------------------------------------------------------------------------
# Step 4: confirmation-gated in-guest query (the only write-class dispatch)
# ---------------------------------------------------------------------------
def guest_disclosure(name: str, instance_id: str) -> Dict[str, Any]:
    entry = GUEST_QUERY_WHITELIST[name]
    return {
        "guest_check": name,
        "command_type": entry["type"],
        "command": entry["command"],
        "target_instance": instance_id,
        "nature": "non-mutating query: reads service, listener, firewall, account, "
                  "session, registry or log state and changes nothing",
        "reversible": "nothing to reverse; the command does not write",
        "dispatched": False,
    }


def guest_dispatch_and_read(
    region: str, instance_id: str, name: str,
    session_id: str, warnings: List[str], errors: List[Dict[str, str]],
) -> Dict[str, Any]:
    entry = GUEST_QUERY_WHITELIST[name]
    params = {
        "RegionId": region,
        "Type": entry["type"],
        "Name": "rdp-diag-{0}".format(name),
        "Description": "Windows RDP diagnosis: one non-mutating query command",
        "CommandContent": _cli.encode_command_content(entry["command"]),
        "ContentEncoding": "Base64",
        "InstanceId.1": instance_id,
        "Timeout": str(CLI_GUEST_POLL_TIMEOUT_SECONDS),
    }
    try:
        dispatch = run_cli(PRODUCT_ECS, ACTION_RUN_COMMAND, params,
                           session_id=session_id, warnings=warnings)
    except CliError as exc:
        errors.append({"step": "guest dispatch", "code": exc.code, "detail": exc.message})
        return {"guest_check": name, "command": entry["command"], "dispatched": False,
                "invoke_id": None, "result": None}

    invoke_id = dispatch.get("InvokeId")
    output, invocation_status = _poll_invocation(region, instance_id, invoke_id,
                                                 session_id, warnings, errors)
    return {"guest_check": name, "command": entry["command"], "dispatched": True,
            "invoke_id": invoke_id, "invocation_status": invocation_status,
            "output": output}


def _poll_invocation(
    region: str, instance_id: str, invoke_id: Any,
    session_id: str, warnings: List[str], errors: List[Dict[str, str]],
) -> Tuple[Optional[str], Optional[str]]:
    import time
    params = {"RegionId": region, "IncludeOutput": "true"}
    if invoke_id:
        params["InvokeId"] = str(invoke_id)
    else:
        params["InstanceId"] = instance_id
    for attempt in range(3):
        try:
            payload = run_cli(PRODUCT_ECS, ACTION_DESCRIBE_INVOCATIONS, params,
                              session_id=session_id, warnings=warnings,
                              timeout=CLI_GUEST_POLL_TIMEOUT_SECONDS)
        except CliError as exc:
            errors.append({"step": "DescribeInvocations", "code": exc.code, "detail": exc.message})
            return None, None
        invs = _as_list(_dig(payload, ["Invocations", "Invocation"]))
        for inv in invs:
            for ii in _as_list(_dig(inv, ["InvokeInstances", "InvokeInstance"])):
                status = ii.get("InvocationStatus")
                raw = ii.get("Output")
                if raw:
                    return _decode_output(raw), status
                if status in ("Success", "Failed", "Timeout", "Error"):
                    return None, status
        if attempt < 2:
            time.sleep(3)
    return None, "Running"


def _decode_output(raw: str) -> str:
    try:
        return base64.b64decode(raw).decode("utf-8", "replace")
    except Exception:
        return str(raw)


# ---------------------------------------------------------------------------
# Error-text classification
# ---------------------------------------------------------------------------
def classify_error_string(text: Optional[str]) -> List[str]:
    from _constants import ERROR_TAXONOMY
    if not text:
        return []
    lowered = text.lower()
    hits = []
    for key, meta in ERROR_TAXONOMY.items():
        if key.lower() in lowered:
            hits.append(key)
    return hits


def _is_windows(inst: Optional[Dict[str, Any]]) -> Optional[bool]:
    if not inst:
        return None
    os_type = str(inst.get("os_type") or "").lower()
    os_name = str(inst.get("os_name") or "").lower()
    if os_type:
        return os_type.startswith("win")
    if os_name:
        return "windows" in os_name
    return None


def _is_cross_border(region: Optional[str]) -> bool:
    if not region:
        return False
    if region in OVERSEAS_CN_REGIONS:
        return True
    return not region.startswith(MAINLAND_CN_REGION_PREFIX)


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------
def build_report(args: argparse.Namespace, sid: str, account_label: str,
                 inst: Optional[Dict[str, Any]], sgs: List[Dict[str, Any]],
                 ca: Optional[Dict[str, Any]], vnc: Optional[str],
                 guest: Optional[Dict[str, Any]], errors: List[Dict[str, str]],
                 warnings: List[str]) -> Tuple[Dict[str, Any], int]:
    findings: List[str] = []
    handoffs: List[str] = []
    next_action: List[str] = []
    status = STATUS_OK

    port = args.port or DEFAULT_RDP_PORT

    # Step 0: disambiguation
    win = _is_windows(inst)
    if inst is None:
        status = STATUS_DEGRADED
        findings.append("Instance not resolved in {0} from the supplied locator; "
                        "cloud-side facts are incomplete.".format(args.region_id))
        next_action.append("Confirm the instance id / public IP and the region, then re-run.")
    elif win is False:
        findings.append("The target reports a non-Windows OS ({0}); RDP/mstsc does not apply.".format(
            inst.get("os_name") or inst.get("os_type")))
        handoffs.append(HANDOFF_MATRIX[4][1])
        next_action.append("Route to the Linux SSH diagnosis path; do not continue RDP checks.")
        return _finalize(sid, account_label, args, port, inst, sgs, ca, vnc, guest,
                         findings, handoffs, next_action, errors, warnings, STATUS_OK)
    elif win is True:
        findings.append("Target is a Windows instance ({0}), instance type {1}, {2} GiB memory.".format(
            inst.get("os_name") or "Windows", inst.get("instance_type"), inst.get("memory_gib")))

    if inst and str(inst.get("status")) != "Running":
        findings.append("Instance state is {0} (not Running); RDP cannot answer until it is up.".format(
            inst.get("status")))
        handoffs.append(HANDOFF_MATRIX[2][1])

    if inst and not inst.get("public_ips"):
        findings.append("No public IP returned for the instance; verify the customer is dialing the "
                        "correct address or use an internal/Workbench channel.")

    # Cross-border
    if inst and _is_cross_border(inst.get("region_id")):
        findings.append("Instance region {0} is outside mainland China; if the client is in "
                        "mainland China this is a cross-border public path.".format(inst.get("region_id")))
        next_action.append("Confirm from a same-region client; explain cross-border limits; VNC/Workbench "
                           "or a same-region jump host are the mitigations (region migration is manual).")

    # Security group
    if sgs:
        for s in sgs:
            if not s.get("evaluated"):
                continue
            if s.get("allowed"):
                note = "Security group {0} allows TCP {1}.".format(s.get("sg_id"), port)
                if s.get("wide_open_to_internet"):
                    note += (" Source is 0.0.0.0/0 -- this exposes RDP to internet-wide brute "
                             "force, the usual trigger for account lockout.")
                findings.append(note)
            else:
                findings.append("Security group {0} has NO inbound allow for TCP {1}; "
                                "the cloud side blocks the connection.".format(s.get("sg_id"), port))
                next_action.append("Guide the operator to add an exact allow for TCP {0} narrowed to "
                                   "the client public IP (manual, in the console).".format(port))
                status = STATUS_DEGRADED if status == STATUS_OK else status
    else:
        warnings.append("no security group to evaluate")

    # Cloud assistant gate
    if ca and ca.get("checked") and not ca.get("ready"):
        findings.append("Cloud Assistant is not ready on this instance; the in-guest query channel "
                        "is unavailable, so guest-side facts cannot be collected automatically.")
        next_action.append("Ask the customer for the client-side evidence checklist "
                           "(mstsc screenshot, telnet/tracetcp the port, tracert, cip.cc) and, "
                           "if needed, an authorized manual in-guest look.")
        status = STATUS_DEGRADED

    # Error string classification
    hits = classify_error_string(args.error_string)
    from _constants import BRANCH_LABELS, ERROR_TAXONOMY
    for h in hits:
        meta = ERROR_TAXONOMY[h]
        findings.append("Reported error matched '{0}' -> {1} (confidence: {2}). Action: {3}".format(
            h, BRANCH_LABELS.get(meta["branch"], meta["branch"]), meta["confidence"], meta["action"]))

    # Guest check outcome
    if guest is not None:
        if guest.get("refused"):
            status = STATUS_FAIL
        elif not guest.get("dispatched"):
            status = STATUS_DEGRADED

    return _finalize(sid, account_label, args, port, inst, sgs, ca, vnc, guest,
                     findings, handoffs, next_action, errors, warnings, status)


def _finalize(sid, account_label, args, port, inst, sgs, ca, vnc, guest,
              findings, handoffs, next_action, errors, warnings, status) -> Tuple[Dict[str, Any], int]:
    if errors and status == STATUS_OK:
        status = STATUS_DEGRADED
    if not next_action:
        next_action.append("Interpret the layered findings with references/windows-rdp__rdp-layered-checklist.md; "
                           "every repair is a manual step attributed to the operator.")
    report = {
        "skill": "area:windows-rdp",
        "session_id": sid,
        "account": account_label,
        "region_id": args.region_id,
        "target_rdp_port": port,
        "auto_filled": {"port": port == DEFAULT_RDP_PORT and args.port is None},
        "instance": inst,
        "security_groups": sgs,
        "cloud_assistant": ca,
        "vnc_rescue": bool(vnc),
        "guest_check": guest,
        "findings": findings,
        "handoffs": handoffs,
        "snapshot_advisory": SNAPSHOT_ADVISORY if (handoffs or findings) else "",
        "errors": errors,
        "warnings": warnings,
        "status": status,
        "next_action": next_action,
        "customer_next": _customer_next(next_action),
    }
    exit_code = 1 if status == STATUS_FAIL else 0
    return report, exit_code


def _customer_next(next_action: List[str]) -> str:
    """The step the customer can act on, in their words. No switch or file names.

    The engineer-facing `next step` lines say things like `Route to the Linux SSH
    diagnosis path` and `Interpret the layered findings with references/...`.
    Measured on 120 sampled tickets: every answer carried the telemetry block and
    that internal directive, and none carried a customer-facing ask.
    """
    head = next_action[0] if next_action else ""
    if "Route to the Linux SSH" in head:
        return ("Next: this instance runs Linux, so the remote-login path is SSH, not "
                "Remote Desktop. Send the exact error your SSH client shows and we "
                "continue on that path; nothing on the instance has been changed.")
    if head.startswith("Confirm the instance id"):
        return ("Next: send the instance id (or the public address you dial) and its "
                "region, plus the exact address:port you type into Remote Desktop.")
    if "add an exact allow" in head:
        return ("Next: the security group does not allow the Remote Desktop port from "
                "your address. Add an allow rule for that port narrowed to the address "
                "you connect from, then retry; this check never changes a rule for you.")
    if head.startswith("Confirm from a same-region client"):
        return ("Next: try the same login from a client in the same region as the "
                "instance. If that works, the limit is on the cross-border path rather "
                "than on the instance itself.")
    return ("Next: paste the exact text or error code Remote Desktop shows, the "
            "address:port you dial, and whether this login ever worked before. "
            "Nothing on the instance has been changed.")


def render_text(report: Dict[str, Any], vnc: Optional[str]) -> str:
    lines: List[str] = []
    lines.append("=" * 70)
    lines.append("Windows Remote Desktop (RDP) diagnosis")
    lines.append("=" * 70)
    lines.append("session-id      : {0}".format(report["session_id"]))
    lines.append("account         : {0}".format(report["account"]))
    lines.append("region          : {0}".format(report["region_id"]))
    lines.append("target RDP port : {0}".format(report["target_rdp_port"]))
    if report["auto_filled"].get("port"):
        lines.append("                (port auto-defaulted to 3389)")
    inst = report["instance"]
    if inst:
        lines.append("instance        : {0} state={1} os={2} type={3} mem={4}GiB public={5}".format(
            inst.get("instance_id"), inst.get("status"),
            (inst.get("os_type") or "?"), inst.get("instance_type"),
            inst.get("memory_gib"), ",".join(inst.get("public_ips") or []) or "none"))
    for s in report["security_groups"]:
        if s.get("evaluated"):
            lines.append("security group  : {0} allow_tcp_{1}={2} wide_open={3}".format(
                s.get("sg_id"), s.get("port"), s.get("allowed"), s.get("wide_open_to_internet")))
    ca = report["cloud_assistant"]
    if ca and ca.get("checked"):
        lines.append("cloud assistant : ready={0} version={1}".format(ca.get("ready"), ca.get("agent_version")))
    if report["guest_check"] is not None:
        gc = report["guest_check"]
        lines.append("guest check     : {0} dispatched={1}".format(gc.get("guest_check"), gc.get("dispatched")))
        if gc.get("dispatched") and gc.get("output"):
            lines.append("  --- guest output ({0}) ---".format(gc.get("invocation_status")))
            lines.append(_indent(str(gc["output"])))
        elif not gc.get("dispatched"):
            lines.append("  command (NOT run yet):")
            lines.append(_indent(gc.get("command", "")))
            if gc.get("nature"):
                lines.append("  nature     : {0}".format(gc["nature"]))
            if gc.get("confirm_required"):
                lines.append("  confirm    : {0}".format(gc["confirm_required"]))
    if vnc:
        lines.append("vnc rescue url : provided (enter via console; rescue sign-in only)")
    lines.append("-" * 70)
    lines.append("Findings:")
    for f in report["findings"] or ["(no finding produced)"]:
        lines.append("  - {0}".format(f))
    if report["handoffs"]:
        lines.append("Hand-off (out of this skill's RO+G scope):")
        for h in report["handoffs"]:
            lines.append("  -> {0}".format(h))
    if report["snapshot_advisory"]:
        lines.append("Advisory: {0}".format(report["snapshot_advisory"]))
    for e in report["errors"]:
        lines.append("[WARN] {0}".format(e))
    for w in report["warnings"]:
        lines.append("[WARN] {0}".format(w))
    lines.append("-" * 70)
    lines.append("Summary")
    lines.append("  what was checked : cloud-side connection surface"
                 " + in-guest query channel status for the target RDP port")
    for na in report["next_action"]:
        lines.append("  next step        : {0}".format(na))
    lines.append("  {0}".format(report.get("customer_next")
                                or _customer_next(report["next_action"])))
    lines.append("")
    lines.append("STATUS: {0}".format(report["status"]))
    lines.append("NEXT_ACTION: {0}".format(report["next_action"][0] if report["next_action"] else "review findings"))
    return "\n".join(lines)


def _indent(text: str, prefix: str = "    ") -> str:
    return "\n".join(prefix + line for line in text.splitlines())


# ---------------------------------------------------------------------------
# Argument parsing and main
# ---------------------------------------------------------------------------
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Windows Remote Desktop (RDP) diagnosis for Alibaba Cloud ECS (RO+G: query reads "
                    "plus a confirmation-gated, non-mutating in-guest query)")
    parser.add_argument("--region-id", help="Region of the instance (required for a scoped run)")
    parser.add_argument("--instance-id", help="ECS instance id (i-...)")
    parser.add_argument("--public-ip", help="Public IP to locate the instance when no id is given")
    parser.add_argument("--port", type=int, default=None,
                        help="Target RDP port the customer dials (default {0})".format(DEFAULT_RDP_PORT))
    parser.add_argument("--security-group-id", action="append", default=None,
                        help="Explicit security group id (repeatable); default from DescribeInstances")
    parser.add_argument("--error-string", help="Quoted mstsc error text / code from the screenshot")
    parser.add_argument("--vnc", action="store_true", help="Also fetch the VNC rescue URL")
    parser.add_argument("--guest-check", choices=sorted(GUEST_QUERY_WHITELIST.keys()),
                        help="Dispatch ONE whitelisted non-mutating in-guest query (needs --confirm)")
    parser.add_argument("--confirm", help="Exact token 'confirm:<guest-check-name>' to allow the dispatch")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    parser.add_argument("--profile", default=None, help="Optional aliyun CLI credential profile")
    parser.add_argument("--check-auth-only", action="store_true", help="Run only the identity pre-check")
    return parser.parse_args(argv)


def _run_selftest() -> int:
    """Offline regression locks for the pure RDP triage decisions: port-range
    parsing/coverage, cross-border detection, OS classification and error-string
    taxonomy. Each feeds a customer-facing verdict, so behaviour is pinned here
    with no cloud call. Returns 0 when all hold."""
    rc = 0

    def expect(name, cond):
        nonlocal rc
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            rc = 1

    # _parse_port_range + _range_covers_port (RDP 3389 must match, others not)
    expect("port_range: '3389/3389' and bare '3389' -> (3389,3389)",
           _parse_port_range("3389/3389") == (3389, 3389)
           and _parse_port_range("3389") == (3389, 3389))
    expect("port_range: junk -> (-1,-1) treated as all-ports",
           _parse_port_range("abc") == (-1, -1)
           and _range_covers_port((-1, -1), 3389) is True
           and _range_covers_port((0, 0), 3389) is True)
    expect("port_range: 3389 covered by its own range only",
           _range_covers_port((3389, 3389), 3389) is True
           and _range_covers_port((1, 100), 3389) is False)

    # _is_cross_border: mainland prefix vs overseas
    expect("cross_border: cn-hangzhou False, ap-southeast-1 True, empty False",
           _is_cross_border("cn-hangzhou") is False
           and _is_cross_border("ap-southeast-1") is True
           and _is_cross_border("") is False)

    # _is_windows: os_type prefix win, fall back to os_name, None for missing
    expect("is_windows: win os_type True, linux False, None-safe",
           _is_windows({"os_type": "windows"}) is True
           and _is_windows({"os_type": "linux"}) is False
           and _is_windows(None) is None and _is_windows({}) is None)
    expect("is_windows: a resolved instance with no OS read stays unknown",
           _is_windows({"instance_id": "i-bp1abcdefg2"}) is None
           and _is_windows({"os_name": ""}) is None
           and _is_windows({"os_name": "Windows Server 2019"}) is True)

    # classify_error_string: a real taxonomy key is detected in free text
    hits = classify_error_string("mstsc failed with 0xd07 for user x")
    expect("classify: known error code surfaced from text",
           "0xd07" in hits and classify_error_string("") == [])
    return rc


def main(argv: Optional[List[str]] = None) -> int:
    if "--selftest" in (argv if argv is not None else sys.argv):
        return _run_selftest()
    args = parse_args(argv)
    sid = new_session_id()
    warnings: List[str] = []
    errors: List[Dict[str, str]] = []

    identity, id_err = fetch_caller_identity(sid, warnings=warnings)
    account_label = uid_traceability_label(identity)

    if args.check_auth_only:
        rep, code = _auth_only_report(sid, account_label, id_err, warnings)
        _emit(rep, args.output, vnc=None)
        return code

    # Mandatory parameter gate
    if not args.region_id or not (args.instance_id or args.public_ip):
        rep = {
            "skill": "area:windows-rdp", "session_id": sid, "account": account_label,
            "region_id": args.region_id, "target_rdp_port": args.port or DEFAULT_RDP_PORT,
            "auto_filled": {"port": args.port is None}, "instance": None, "security_groups": [],
            "cloud_assistant": None, "vnc_rescue": False, "guest_check": None,
            "findings": ["Missing required input: region-id plus an instance-id or public-ip."],
            "handoffs": [], "snapshot_advisory": "",
            "errors": errors, "warnings": warnings, "status": STATUS_FAIL,
            "next_action": ["Ask for the region and the instance id (or public IP) and the exact ip:port dialed."],
        }
        if id_err:
            rep["next_action"].append("credential/identity: {0}".format(identity_guidance_lines(id_err)[0]))
        _emit(rep, args.output, vnc=None)
        return 1

    inst = describe_instance(args.region_id, args.instance_id, args.public_ip, sid, warnings, errors)

    sg_ids = args.security_group_id or (inst.get("security_group_ids") if inst else []) or []
    port = args.port or DEFAULT_RDP_PORT
    sgs = [check_security_group(args.region_id, sg, port, sid, warnings, errors) for sg in sg_ids]

    ca = None
    guest = None
    vnc = None

    if args.instance_id:
        ca = check_cloud_assistant(args.region_id, args.instance_id, sid, warnings, errors)

    if args.vnc and args.instance_id:
        vnc = fetch_vnc_url(args.region_id, args.instance_id, sid, warnings, errors)

    if args.guest_check:
        guest = _run_guest_check(args, sid, inst, ca, warnings, errors)

    report, code = build_report(args, sid, account_label, inst, sgs, ca, vnc, guest, errors, warnings)
    _emit(report, args.output, vnc=vnc)
    return code


def _run_guest_check(args, sid, inst, ca, warnings, errors) -> Dict[str, Any]:
    name = args.guest_check
    if name not in GUEST_QUERY_WHITELIST:
        # argparse already restricts choices; this is a belt-and-braces guard.
        return {"guest_check": name, "refused": True, "dispatched": False,
                "reason": CODE_COMMAND_REFUSED,
                "detail": "command name is not on the whitelist"}
    if not args.instance_id:
        return {"guest_check": name, "refused": True, "dispatched": False,
                "reason": CODE_MISSING_INSTANCE,
                "detail": "a guest query needs an instance-id (not a bare public IP)"}
    if not (ca and ca.get("ready")):
        disc = guest_disclosure(name, args.instance_id)
        disc.update({"refused": False, "blocked_by": "cloud-assistant-not-ready",
                     "dispatched": False})
        return disc
    expected = "confirm:{0}".format(name)
    if args.confirm != expected:
        disc = guest_disclosure(name, args.instance_id)
        disc.update({"dispatched": False, "confirm_required": expected,
                     "reason": CODE_NOT_CONFIRMED})
        return disc
    return guest_dispatch_and_read(args.region_id, args.instance_id, name, sid, warnings, errors)


CODE_MISSING_INSTANCE = "MissingInstanceId"


def _auth_only_report(sid, account_label, id_err, warnings):
    status = STATUS_FAIL if id_err else STATUS_OK
    return ({
        "skill": "area:windows-rdp", "session_id": sid, "account": account_label,
        "region_id": None, "target_rdp_port": None, "auto_filled": {}, "instance": None,
        "security_groups": [], "cloud_assistant": None, "vnc_rescue": False, "guest_check": None,
        "findings": ["identity pre-check only"], "handoffs": [], "snapshot_advisory": "",
        "errors": [], "warnings": warnings, "status": status,
        "next_action": identity_guidance_lines(id_err),
    }, 1 if id_err else 0)


def _emit(report: Dict[str, Any], output: str, vnc: Optional[str]) -> None:
    if output == "json":
        # Pure, parseable JSON: status / next_action are already fields inside.
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_text(report, vnc))


if __name__ == "__main__":
    sys.exit(main())
