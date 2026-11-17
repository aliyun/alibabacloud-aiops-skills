#!/usr/bin/env python3
"""
ecs_smtp_block_diagnosis.py -- Entry script: layer attribution for ECS SMTP /
port-25 mail failures
============================================================================
SECURITY (RO+G permission model):
  * Cloud calls are routed through scripts/areas/smtp_block_diagnosis/_cli.py, which enforces the
    ALLOWED_ACTIONS whitelist: ecs DescribeInstances, ecs
    DescribeInstanceStatus, ecs DescribeInvocations, ecs
    DescribeSecurityGroupAttribute (egress mail-port rules), sts
    GetCallerIdentity,
    plus exactly ONE write-property action, ecs RunCommand. RunCommand is
    used only to dispatch a fixed inspection-only template from GUEST_PROBES
    into the customer's own Linux instance, and only after the caller passes
    --user-confirmation with the exact PROBE_CONFIRMATION_TOKEN proving the
    user approved that single command after seeing the disclosure.
  * Never automated: security-group or firewall edits, service restarts,
    applying or removing rules, submitting the port-25 unblock application,
    opening or configuring a mail product, and any destructive action. Such
    requests are answered with manual steps plus a risk note.
  * Credentials are resolved exclusively by the aliyun CLI default
    credential chain; this script never accepts or prints keys or tokens.
  * Free-form commands can never reach an instance: the script accepts a
    PROBE ID, never command text, and re-validates the rendered template
    (host regex, port integers, prohibited verbs, redirect targets) before
    dispatch. With no --execute-probe the script is fully non-mutating and
    in-guest evidence comes from the manual readings checklist pasted back
    via --port-result / --listener-25.

Attribution layers (see SKILL.md 'Orchestration' and references/):
  platform outbound TCP-25 block | customer config (security group egress /
  guest firewall) | guest listener / container mapping | unblock-application
  eligibility | peer mail-server application layer | cross-border link |
  not attributed (insufficient evidence -> DEGRADED with readings list).

Usage:
  python3 ecs_smtp_block_diagnosis.py --region-id cn-hangzhou \
      (--instance-id i-xxx | --public-ip-address 47.0.0.1) \
      [--direction send|receive|apply] [--target-host HOST] [--target-port N] \
      [--port-result PORT=STATE ...] [--error-text "..."] \
      [--listener-25 yes|no|unknown] [--container-mapped yes|no|unknown] \
      [--customer-text "..."] [--include-invocations] [--json] [--profile P]

  # optional, confirmation-gated in-guest inspection (one probe per run):
  ... [--execute-probe port-probe|listener|firewall|path-info] \
      --user-confirmation I-APPROVE-INSPECTION-ONLY-COMMAND \
      [--probe-host HOST] [--probe-port N ...]

Output contract: human report (default) or full JSON (--json), always ending
with `STATUS: OK|DEGRADED|FAIL` and `NEXT_ACTION: ...`.
Exit codes: 0 = OK or DEGRADED (usable conclusion), 1 = FAIL (missing input /
instance not found / credential failure / probe dispatch error), 2 = argparse
usage error only. A missing confirmation token is NOT an error: dispatch is
skipped, the disclosure is printed, and the run continues as DEGRADED with
the manual readings.
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import base64
import ipaddress
import json
import re
import sys
import time
from typing import Any, Optional

import _cli
from _constants import (
    API_VERSIONS,
    BASELINE_PORTS,
    CLI_TIMEOUT,
    DOC_LINKS,
    DOMESTIC_PROVIDER_HINTS,
    ERROR_SIGNATURES,
    EXTRA_OVERSEAS_REGIONS,
    GUEST_PROBES,
    GUIDANCE_BLOCKS,
    HANDOFF_RULES,
    LAYER_APPLY_ELIGIBILITY,
    LAYER_CROSS_BORDER,
    LAYER_CUSTOMER_CONFIG,
    LAYER_NOT_ATTRIBUTED,
    LAYER_PEER_APPLICATION,
    LAYER_PLATFORM_BLOCK,
    LAYER_UNLISTENING,
    MAX_INVOCATIONS,
    OVERSEAS_REGION_PREFIXES,
    POLICY_STATEMENTS,
    PORT_STATES,
    PROBE_CONFIRMATION_TOKEN,
    PROBE_DEFAULT_PORTS,
    PROBE_MAX_PORTS,
    PROBE_MAX_WAIT_SECONDS,
    PROBE_OUTPUT_MAX_CHARS,
    PROBE_POLL_INTERVAL_SECONDS,
    PROBE_RUN_TIMEOUT_SECONDS,
    PROBE_TERMINAL_STATUSES,
    READINGS,
    SKILL_NAME,
    STATUS_DEGRADED,
    STATUS_OK,
    render_probe_template,
)

# ---------------------------------------------------------------------------
# Input validation types (strict: regex + range, no shell interpolation ever)
# ---------------------------------------------------------------------------

_REGION_RE = re.compile(r"^[a-z][a-z0-9-]{3,30}$")
_INSTANCE_ID_RE = re.compile(r"^i-[a-z0-9]{6,40}$")


def _region_type(value: str) -> str:
    if not _REGION_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"invalid --region-id '{value}': expected e.g. cn-hangzhou")
    return value


def _instance_id_type(value: str) -> str:
    if not _INSTANCE_ID_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"invalid --instance-id '{value}': expected i-xxxx form")
    return value


def _ip_type(value: str) -> str:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid IP address '{value}'")
    return value


# A probe target reaches the instance only as a substituted token inside a
# whitelisted template, so its character set is closed: hostnames and IP
# literals. The regex structurally excludes whitespace, quotes, slashes,
# semicolons, backticks, $, parentheses and every other shell metacharacter.
PROBE_HOST_RE = re.compile(
    r"^(?=.{1,253}$)[A-Za-z0-9]([A-Za-z0-9.:-]*[A-Za-z0-9])?$")


def _probe_host_type(value: str) -> str:
    if not PROBE_HOST_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"invalid --probe-host '{value}': expected a hostname or a bare "
            "IPv4/IPv6 literal with no other characters")
    return value


def _probe_port_type(value: str) -> int:
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid --probe-port '{value}': must be an integer")
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(
            f"invalid --probe-port '{value}': out of range 1-65535")
    return port


def _probe_id_type(value: str) -> str:
    if value not in GUEST_PROBES:
        raise argparse.ArgumentTypeError(
            f"invalid --execute-probe '{value}': must be one of "
            + ", ".join(sorted(GUEST_PROBES)))
    return value


assert _probe_host_type("smtp.qiye.aliyun.com") == "smtp.qiye.aliyun.com"
assert _probe_host_type("47.102.1.2")
assert _probe_host_type("2408:866c:541:2130::4")
for _bad_host in ("smtp.example.com; rm -rf /", "a`id`b", "$(reboot)",
                  "host|nc evil 1", "ex.com > /tmp/x", "-lead", "trail-",
                  "quote'd", "a b"):
    try:
        _probe_host_type(_bad_host)
        raise AssertionError(f"probe host accepted: {_bad_host!r}")
    except argparse.ArgumentTypeError:
        pass  # expected
assert not PROBE_HOST_RE.match("")
assert _probe_port_type("465") == 465
for _bad_port in ("0", "65536", "abc", "25.5"):
    try:
        _probe_port_type(_bad_port)
        raise AssertionError(f"probe port accepted: {_bad_port!r}")
    except argparse.ArgumentTypeError:
        pass  # expected
assert _probe_id_type("port-probe") == "port-probe"
try:
    _probe_id_type("rm-the-firewall")
    raise AssertionError("unknown probe id accepted")
except argparse.ArgumentTypeError:
    pass  # expected


def parse_port_result(value: str) -> tuple[int, str]:
    """Parse 'PORT=STATE' for --port-result. Pure function; raises
    argparse.ArgumentTypeError (a ValueError subclass) on bad input."""
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            f"invalid --port-result '{value}': expected PORT=STATE")
    port_part, _, state = value.partition("=")
    state = state.strip().lower()
    try:
        port = int(port_part.strip())
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid --port-result '{value}': port must be an integer")
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(
            f"invalid --port-result '{value}': port out of range 1-65535")
    if state not in PORT_STATES:
        raise argparse.ArgumentTypeError(
            f"invalid --port-result '{value}': state must be one of "
            + ", ".join(PORT_STATES))
    return port, state


def is_ipv6_literal(host: str) -> bool:
    """True when the target host is a bare IPv6 literal."""
    if not host or ":" not in host:
        return False
    try:
        return ipaddress.ip_address(host).version == 6
    except ValueError:
        return False


assert parse_port_result("25=timeout") == (25, "timeout")
assert parse_port_result("443=connected-closed") == (443, "connected-closed")
for _bad in ("25", "0=timeout", "99999=ok", "25=banned", "abc=timeout"):
    try:
        parse_port_result(_bad)
        raise AssertionError(f"parse_port_result accepted garbage: {_bad}")
    except argparse.ArgumentTypeError:
        pass  # expected
assert is_ipv6_literal("2408:866c:541:2130::4")
assert not is_ipv6_literal("smtp.example.com")
assert not is_ipv6_literal("")


def match_signatures(text: str) -> list[dict]:
    """Return the ERROR_SIGNATURES entries whose regex matches `text`.
    Pure function over embedded knowledge -- no model memory involved."""
    if not text:
        return []
    hits = []
    for sig in ERROR_SIGNATURES:
        if re.search(sig["regex"], text, re.I):
            hits.append(sig)
    return hits


assert [s["id"] for s in match_signatures(
    "550 Bad HELO - Host impersonating domain name [example.com]")] == ["550-bad-helo"]
assert any(s["id"] == "ip-usage-permission" for s in match_signatures(
    "The system reported: no permission to use this IP address"))
assert match_signatures("telnet: Connection timed out") == []


# ---------------------------------------------------------------------------
# Cloud evidence helpers (defensive parsing: missing keys never crash)
# ---------------------------------------------------------------------------

def _dig(obj: Any, *keys: str) -> Any:
    node = obj
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _as_list(node: Any) -> list:
    if node is None:
        return []
    if isinstance(node, list):
        return node
    return [node]


def describe_instance(region: str, instance_id: Optional[str],
                      public_ip: Optional[str], profile: Optional[str],
                      actions: list[dict]) -> tuple[Optional[dict], str]:
    """Locate the instance via DescribeInstances.

    Returns (instance_dict_or_None, failure_note). A public IPv4 is looked
    up first as a fixed public IP, then as an EIP (both filter parameters
    exist on this action; the empty-result case must try both). `failure_note`
    is non-empty only when the QUERY itself errored (permission / CLI
    failure), distinguishing that from a clean 'no such instance'.
    """
    if instance_id:
        attempts = [("InstanceIds", json.dumps([instance_id]))]
    else:
        attempts = [("PublicIpAddresses", public_ip),
                    ("EipAddresses", public_ip)]
    last_error = ""
    had_response = False
    for key, value in attempts:
        params = {"RegionId": region, key: value, "PageSize": 50}
        how = f"{key} filter {value}"
        try:
            body = _cli.call("ecs", "DescribeInstances", params,
                             region=region, profile=profile)
        except _cli.CliError as e:
            actions.append({"action": "ecs DescribeInstances", "how": how,
                            "result": f"failed: {e}"})
            print(f"[WARN] DescribeInstances {key} filter failed: {e}",
                  file=sys.stderr)
            last_error = str(e)
            continue
        had_response = True
        actions.append({"action": "ecs DescribeInstances", "how": how,
                        "result": "ok"})
        instances = _as_list(_dig(body, "Instances", "Instance"))
        if instances:
            return instances[0], ""
    # A clean empty answer is 'not found', not a query failure: only report
    # failure_note when NO attempt ever returned.
    failure_note = "" if had_response else last_error
    return None, failure_note


def describe_status(region: str, instance_id: str, profile: Optional[str],
                    actions: list[dict]) -> Optional[str]:
    try:
        body = _cli.call("ecs", "DescribeInstanceStatus",
                         {"RegionId": region, "InstanceId.1": instance_id},
                         region=region, profile=profile)
        actions.append({"action": "ecs DescribeInstanceStatus",
                        "how": f"InstanceId.1 {instance_id}",
                        "result": "ok"})
        for item in _as_list(_dig(body, "InstanceStatuses",
                                  "InstanceStatus")):
            if isinstance(item, dict):
                return str(item.get("Status") or "")
    except _cli.CliError as e:
        actions.append({"action": "ecs DescribeInstanceStatus",
                        "how": f"InstanceId.1 {instance_id}",
                        "result": f"failed: {e}"})
        print(f"[WARN] DescribeInstanceStatus failed: {e}", file=sys.stderr)
    return None


def describe_invocations(region: str, instance_id: str,
                         profile: Optional[str],
                         actions: list[dict]) -> list[dict]:
    """Recent Cloud Assistant invocation RECORDS (execution history only; the
    read-back of this skill's own gated probe uses `fetch_probe_result`
    below)."""
    try:
        body = _cli.call("ecs", "DescribeInvocations",
                         {"RegionId": region, "InstanceId": instance_id,
                          "MaxResults": MAX_INVOCATIONS},
                         region=region, profile=profile)
        actions.append({"action": "ecs DescribeInvocations",
                        "how": f"recent invocations for {instance_id}",
                        "result": "ok"})
        out = []
        for item in _as_list(_dig(body, "Invocations", "Invocation")):
            if isinstance(item, dict):
                out.append({
                    "invoke_id": str(item.get("InvokeId") or ""),
                    "command_name": str(item.get("CommandName") or ""),
                    "status": str(item.get("InvokeStatus") or ""),
                    "creation_time": str(item.get("CreationTime") or ""),
                })
        return out
    except _cli.CliError as e:
        actions.append({"action": "ecs DescribeInvocations",
                        "how": f"recent invocations for {instance_id}",
                        "result": f"failed: {e}"})
        print(f"[WARN] DescribeInvocations failed: {e}", file=sys.stderr)
        return []


def describe_egress_rules(region: str, sg_ids: list, profile: Optional[str],
                          actions: list[dict]) -> tuple[list, int]:
    """Read the egress rules of every attached security group.

    Returns (rules, ok_reads). ok_reads == 0 means the rule read itself failed
    (permission / API), which must stay distinguishable from "read succeeded
    and there is no rule": the first is an evidence gap, the second is proof
    that this layer is not the blocker.
    """
    rules: list = []
    ok_reads = 0
    for sg in (sg_ids or [])[:5]:
        try:
            body = _cli.call("ecs", "DescribeSecurityGroupAttribute",
                             {"RegionId": region, "SecurityGroupId": sg,
                              "Direction": "egress"},
                             region=region, profile=profile)
        except _cli.CliError as e:
            actions.append({"action": "ecs DescribeSecurityGroupAttribute",
                            "how": f"{sg} / egress", "result": f"failed: {e}"})
            print(f"[WARN] DescribeSecurityGroupAttribute {sg} failed: {e}",
                  file=sys.stderr)
            continue
        ok_reads += 1
        actions.append({"action": "ecs DescribeSecurityGroupAttribute",
                        "how": f"{sg} / egress", "result": "ok"})
        for rule in _as_list(_dig(body, "Permissions", "Permission")):
            if isinstance(rule, dict):
                rule = dict(rule)
                rule["_sg"] = sg
                rule["_direction"] = "egress"
                rules.append(rule)
    return rules, ok_reads


# ---------------------------------------------------------------------------
# Confirmation-gated in-guest inspection (the RO+G probe channel)
#
# prepare_probe() is pure: it renders and re-validates one whitelisted
# template and decides the gate. Only collect_probe() reaches the network,
# and only when the gate is open. Nothing here accepts command text.
# ---------------------------------------------------------------------------

# Which manual-checklist reading each probe replaces (for report wording).
PROBE_READING_MAP = {
    "port-probe": "port-matrix",
    "listener": "listener",
    "firewall": "local-firewall",
    "path-info": "",
}

_PROBE_LINE_RE = re.compile(
    r"^PORT\s+(\d{1,5})\s+(TCP-[A-Z][A-Z-]*)", re.M)

# Guest-side verdict -> the same vocabulary --port-result accepts.
_PROBE_STATE_BY_TOKEN = {
    "TCP-OPEN": "connected",
    "TCP-TIMEOUT": "timeout",
    "TCP-REFUSED": "refused",
}

_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")


def _probe_requires_host(probe_id: str) -> bool:
    return "__HOST__" in GUEST_PROBES[probe_id]["template"]


def resolve_probe_ports(args: argparse.Namespace) -> tuple:
    """Ports for the port-probe: explicit flags, else --target-port, else the
    default mail+control set; de-duplicated and capped at PROBE_MAX_PORTS."""
    ports = list(args.probe_ports or [])
    if not ports:
        if args.target_port:
            ports = [args.target_port]
        else:
            ports = list(PROBE_DEFAULT_PORTS)
    seen: set = set()
    uniq = [p for p in ports if not (p in seen or seen.add(p))]
    if len(uniq) > PROBE_MAX_PORTS:
        print(f"[WARN] --probe-port list trimmed to the first "
              f"{PROBE_MAX_PORTS} ports", file=sys.stderr)
    return tuple(uniq[:PROBE_MAX_PORTS])


def prepare_probe(args: argparse.Namespace) -> dict:
    """Render + validate one probe and apply the confirmation gate.

    Returns the probe record; `gate` is 'DISPATCH-APPROVED' only when
    --user-confirmation equals PROBE_CONFIRMATION_TOKEN exactly. This
    function performs no I/O, so the disclosure can always be printed --
    including when the gate is closed.
    """
    probe_id = args.execute_probe
    meta = GUEST_PROBES[probe_id]
    host = args.probe_host or ""
    if _probe_requires_host(probe_id) and not host:
        raise ValueError(
            f"probe {probe_id!r} needs a validated --probe-host "
            f"({meta['requires']}); refusing to dispatch a command with an "
            "empty target")
    ports = resolve_probe_ports(args) if probe_id == "port-probe" else ()
    command = render_probe_template(probe_id, host=host, ports=ports)
    approved = (args.user_confirmation or "") == PROBE_CONFIRMATION_TOKEN
    return {
        "probe_id": probe_id,
        "title": meta["title"],
        "command_type": meta["command_type"],
        "replaces_reading": PROBE_READING_MAP.get(probe_id, ""),
        "reads": meta["reads"],
        "why": meta["why"],
        "disclosure": meta["disclosure"],
        "reversible": meta["reversible"],
        "host": host,
        "ports": list(ports),
        "timeout_seconds": PROBE_RUN_TIMEOUT_SECONDS,
        "command": command,
        "gate": "DISPATCH-APPROVED" if approved else "HELD-no-confirmation",
        "status": "not-dispatched" if not approved else "dispatching",
        "invoke_id": "",
        "exit_code": "",
        "output": "",
        "output_truncated": False,
        "derived_port_states": {},
        "derived_listener_25": "unknown",
        "error": "",
    }


def _decode_output(value: str) -> str:
    """Decode a Cloud Assistant Output field.

    With IncludeOutput=true the API returns base64. A multi-line value is
    already plain text, so decoding is attempted only for a single unbroken
    base64-shaped token, and its result is accepted only when printable --
    an undecodable or binary-looking answer is returned verbatim instead of
    being silently mangled.
    """
    text = (value or "").strip()
    if not text or "\n" in text or " " in text:
        return text
    if not _BASE64_RE.match(text) or len(text) % 4:
        return text
    try:
        raw = base64.b64decode(text, validate=True)
    except ValueError:
        return text
    decoded = raw.decode("utf-8", "replace")
    if any(ord(ch) < 9 for ch in decoded):
        return text
    return decoded


def dispatch_probe(region: str, instance_id: str, probe: dict,
                   profile: Optional[str], actions: list[dict]) -> str:
    """Send the already-validated template via ecs RunCommand.

    Returns the InvokeId, or raises _cli.CliError (the caller degrades).
    The command content is exactly what prepare_probe rendered and what the
    user approved -- no substitution happens after the gate.
    """
    params = {
        "RegionId": region,
        "Type": probe["command_type"],
        "Name": f"{SKILL_NAME}-{probe['probe_id']}",
        "CommandContent": probe["command"],
        "Description": probe["title"],
        "InstanceId.1": instance_id,
        "Timeout": PROBE_RUN_TIMEOUT_SECONDS,
    }
    try:
        body = _cli.call("ecs", "RunCommand", params, region=region,
                         profile=profile, timeout=CLI_TIMEOUT)
    except _cli.CliError as e:
        actions.append({"action": "ecs RunCommand",
                        "how": f"{probe['probe_id']} on {instance_id}",
                        "result": f"failed: {e}"})
        raise
    invoke_id = str(body.get("InvokeId") or "")
    actions.append({"action": "ecs RunCommand",
                    "how": f"{probe['probe_id']} on {instance_id}",
                    "result": f"ok InvokeId={invoke_id or 'missing'}"})
    return invoke_id


def fetch_probe_result(region: str, invoke_id: str, instance_id: str,
                       profile: Optional[str],
                       actions: list[dict]) -> dict:
    """Poll DescribeInvocations(IncludeOutput=true) for one dispatched probe.

    Bounded twice over: PROBE_MAX_WAIT_SECONDS total and CLI_TIMEOUT per
    call. Never raises -- an API failure is reported in `error` so the run
    still returns a diagnosis.
    """
    result = {"status": "", "exit_code": "", "output": "", "error": ""}
    deadline = time.monotonic() + PROBE_MAX_WAIT_SECONDS
    attempts = 0
    while True:
        attempts += 1
        try:
            body = _cli.call("ecs", "DescribeInvocations",
                             {"RegionId": region, "InvokeId": invoke_id,
                              "InstanceId": instance_id,
                              "IncludeOutput": True, "MaxResults": 10},
                             region=region, profile=profile)
        except _cli.CliError as e:
            actions.append({"action": "ecs DescribeInvocations",
                            "how": f"probe output read-back ({attempts} polls)",
                            "result": f"failed: {e}"})
            result["error"] = f"output read-back failed: {e}"
            return result

        invocation = None
        for item in _as_list(_dig(body, "Invocations", "Invocation")):
            if isinstance(item, dict):
                invocation = item
                break
        if invocation is None:
            result["error"] = "no invocation record found for the InvokeId"
            actions.append({"action": "ecs DescribeInvocations",
                            "how": f"probe output read-back "
                                   f"({attempts} polls)",
                            "result": "empty"})
            return result

        guest = None
        for item in _as_list(_dig(invocation, "InvokeInstances",
                                  "InvokeInstance")):
            if isinstance(item, dict) and str(
                    item.get("InstanceId") or "") in ("", instance_id):
                guest = item
                break
        status = str((guest or {}).get("InvocationStatus")
                     or invocation.get("InvokeStatus") or "")
        result["status"] = status
        if status in PROBE_TERMINAL_STATUSES:
            raw_exit = (guest or {}).get("ExitCode")
            result["exit_code"] = "" if raw_exit is None else str(raw_exit)
            result["output"] = _decode_output(
                str((guest or {}).get("Output") or ""))
            if status not in ("Success", "Finished"):
                result["error"] = str(
                    (guest or {}).get("ErrorInfo")
                    or (guest or {}).get("ErrorDesc")
                    or f"guest execution ended as {status}")
            actions.append({"action": "ecs DescribeInvocations",
                            "how": f"probe output read-back "
                                   f"({attempts} polls)",
                            "result": f"ok status={status}"})
            return result
        if time.monotonic() >= deadline:
            result["error"] = (f"probe did not finish within "
                               f"{PROBE_MAX_WAIT_SECONDS}s (last status "
                               f"{status or 'unknown'}); read-back is "
                               f"partial")
            actions.append({"action": "ecs DescribeInvocations",
                            "how": f"probe output read-back "
                                   f"({attempts} polls)",
                            "result": "window elapsed"})
            return result
        time.sleep(PROBE_POLL_INTERVAL_SECONDS)


def parse_probe_readings(probe_id: str, output: str) -> tuple[dict, str]:
    """Derive attribution inputs from probe output.

    Returns ({port: state}, listener_25). Anything the templates did not
    print stays absent/'unknown' -- derived values are never invented.
    """
    states: dict[int, str] = {}
    for match in _PROBE_LINE_RE.finditer(output or ""):
        port = int(match.group(1))
        token = match.group(2)
        state = _PROBE_STATE_BY_TOKEN.get(token)
        if state and 1 <= port <= 65535:
            states[port] = state
    listener_25 = "unknown"
    if probe_id == "listener" and output:
        section = output.split("== mail-port listeners ==", 1)
        if len(section) == 2:
            body = section[1].split("==", 1)[0]
            if re.search(r":25[\s/]", body):
                listener_25 = "yes"
            elif "NONE" in body:
                listener_25 = "no"
    return states, listener_25


def collect_probe(region: str, instance_id: str, args: argparse.Namespace,
                  profile: Optional[str],
                  actions: list[dict]) -> dict:
    """Run the probe channel end to end, honouring the gate."""
    probe = prepare_probe(args)
    if probe["gate"] != "DISPATCH-APPROVED":
        return probe
    try:
        invoke_id = dispatch_probe(region, instance_id, probe, profile,
                                   actions)
    except _cli.CliError as e:
        probe["status"] = "dispatch-failed"
        probe["error"] = str(e)
        return probe
    probe["invoke_id"] = invoke_id
    if not invoke_id:
        probe["status"] = "dispatch-failed"
        probe["error"] = "RunCommand returned no InvokeId"
        return probe
    result = fetch_probe_result(region, invoke_id, instance_id, profile,
                                actions)
    probe["status"] = result["status"] or "unknown"
    probe["exit_code"] = result["exit_code"]
    probe["error"] = result["error"]
    output = result["output"]
    if len(output) > PROBE_OUTPUT_MAX_CHARS:
        output = output[:PROBE_OUTPUT_MAX_CHARS]
        probe["output_truncated"] = True
    probe["output"] = output
    states, listener_25 = parse_probe_readings(probe["probe_id"], output)
    probe["derived_port_states"] = {str(k): v for k, v in states.items()}
    probe["derived_listener_25"] = listener_25
    probe["derived_states"] = states
    return probe


def probe_report_view(probe: dict) -> dict:
    """Serializable view of one probe record (drops the internal int-keyed
    derived state map, which is merged into the attribution input instead)."""
    return {k: v for k, v in probe.items() if k != "derived_states"}


# Boundary tests: the gate must hold closed without the exact token, and the
# parser must map guest verdicts onto the engine's own vocabulary.
_args_stub = argparse.Namespace(execute_probe="port-probe", probe_host="smtp.x.com",
                                probe_ports=[25, 465], target_port=None,
                                user_confirmation="")
_held = prepare_probe(_args_stub)
assert _held["gate"] == "HELD-no-confirmation"
assert _held["status"] == "not-dispatched"
# The host reaches the guest as a shell-variable assignment, never inline in
# the redirection, so that is the substitution these tests pin down.
assert 'HOST="smtp.x.com"' in _held["command"]
assert 'PORTS="25 465"' in _held["command"]
assert "__HOST__" not in _held["command"] and "__PORTS__" not in _held["command"]
assert _held["ports"] == [25, 465]
_args_stub.user_confirmation = PROBE_CONFIRMATION_TOKEN
assert prepare_probe(_args_stub)["gate"] == "DISPATCH-APPROVED"
_args_stub.user_confirmation = PROBE_CONFIRMATION_TOKEN.lower()
assert prepare_probe(_args_stub)["gate"] == "HELD-no-confirmation"
try:
    prepare_probe(argparse.Namespace(execute_probe="path-info",
                                     probe_host="", probe_ports=[],
                                     target_port=None,
                                     user_confirmation=PROBE_CONFIRMATION_TOKEN))
    raise AssertionError("host-less probe prepared")
except ValueError:
    pass  # expected
assert prepare_probe(argparse.Namespace(
    execute_probe="firewall", probe_host="", probe_ports=[],
    target_port=None, user_confirmation=""))["gate"] == "HELD-no-confirmation"
assert resolve_probe_ports(argparse.Namespace(
    probe_ports=[], target_port=None)) == tuple(PROBE_DEFAULT_PORTS)
assert resolve_probe_ports(argparse.Namespace(
    probe_ports=[], target_port=465)) == (465,)
assert len(resolve_probe_ports(argparse.Namespace(
    probe_ports=list(range(1, 40)), target_port=None))) == PROBE_MAX_PORTS
_states, _l25 = parse_probe_readings(
    "port-probe", "PORT 25 TCP-TIMEOUT\nPORT 465 TCP-OPEN\nPROBE COMPLETE")
assert _states == {25: "timeout", 465: "connected"} and _l25 == "unknown"
assert parse_probe_readings("port-probe", "PORT 25 TCP-BOGUS")[0] == {}
assert parse_probe_readings("listener", "x")[1] == "unknown"
assert parse_probe_readings(
    "listener", "== mail-port listeners ==\nNONE\n== container")[1] == "no"
assert parse_probe_readings(
    "listener", "== mail-port listeners ==\ntcp 0 0 0.0.0.0:25 0.0.0.0:*\n"
    "== container")[1] == "yes"
assert _decode_output("") == ""
assert _decode_output(
    "PORT 25 TCP-OPEN\nPORT 465 TCP-OPEN\n").startswith("PORT 25")
assert _decode_output(base64.b64encode(
    b"PROBE firewall COMPLETE").decode()) == "PROBE firewall COMPLETE"
assert _decode_output("not!!base64") == "not!!base64"


def extract_facts(inst: dict, status_api: Optional[str]) -> dict:
    """Reduce one raw DescribeInstances item to the facts this skill needs."""
    public_ips = [str(x) for x in _as_list(
        _dig(inst, "PublicIpAddress", "IpAddress"))]
    eip = str(_dig(inst, "EipAddress", "IpAddress") or "")
    inner = [str(x) for x in _as_list(
        _dig(inst, "VpcAttributes", "PrivateIpAddress", "IpAddress"))]
    if not inner:
        inner = [str(x) for x in _as_list(_dig(inst, "InnerIpAddress",
                                               "IpAddress"))]
    sgs = [str(x) for x in _as_list(
        _dig(inst, "SecurityGroupIds", "SecurityGroupId"))]
    net_type = str(inst.get("InstanceNetworkType") or "")
    ipv6_visible = "unknown"
    raw_ipv6 = inst.get("Ipv6Address") or _dig(inst, "Ipv6Sets", "Ipv6Set")
    if raw_ipv6:
        ipv6_visible = "yes"
    elif "Ipv6Sets" in inst or "Ipv6Address" in inst:
        ipv6_visible = "no"
    return {
        "instance_id": str(inst.get("InstanceId") or ""),
        "instance_name": str(inst.get("InstanceName") or ""),
        "region_id": str(inst.get("RegionId") or ""),
        "status": str(inst.get("Status") or ""),
        "status_api": status_api or "",
        "instance_network_type": net_type,
        "public_ips": public_ips,
        "eip": eip,
        "inner_ips": inner,
        "security_group_ids": sgs,
        "internet_max_bandwidth_out": inst.get("InternetMaxBandwidthOut"),
        "instance_charge_type": str(inst.get("InstanceChargeType") or ""),
        "ipv6_visible_via_api": ipv6_visible,
    }


def ip_form_verdict(facts: dict) -> tuple[str, str]:
    """Public-IP form used for the unblock-eligibility pre-check
    (evidence: ticket T-384967AE -- the application must reference a
    VPC-mode public IP)."""
    net = facts["instance_network_type"]
    if net == "vpc" and facts["public_ips"]:
        return ("vpc-fixed-public-ipv4",
                "Instance is in a VPC with a fixed public IPv4 -- eligible "
                "IP form for a port-25 unblock application (final decision "
                "stays with the reviewer).")
    if net == "vpc" and facts["eip"]:
        return ("vpc-eip",
                "Instance uses an EIP. Reference the associated public "
                "IPv4 in the application; if the console still reports an IP "
                "usage-permission error, verify the EIP binding state.")
    if facts["public_ips"] and net == "classic":
        return ("classic-network-public-ip",
                "Public IP on the CLASSIC network: past evidence shows the "
                "unblock application requires a VPC-mode public IP "
                "(ticket T-384967AE) -- expect rejection; confirm the "
                "current policy before applying.")
    if not facts["public_ips"] and not facts["eip"]:
        return ("none",
                "No public IPv4 (fixed or EIP) visible on the instance -- "
                "sending via port 25 would first need a public egress path, "
                "and there is no IP to declare in an application.")
    return ("unknown", "Public-IP form not conclusive from the API fields.")


def _facts(**kw):
    base = {"instance_network_type": "vpc", "public_ips": [], "eip": None}
    base.update(kw)
    return base


MAIL_PORTS = (25, 465, 587)


def _port_range_covers(port: int, port_range: Any) -> bool:
    """True when an ECS PortRange ('25/25', '-1/-1', '1/65535') covers port."""
    try:
        lo, hi = (int(x) for x in str(port_range).replace(" ", "").split("/", 1))
    except (TypeError, ValueError):
        return False
    if lo == -1 and hi == -1:
        return True
    return lo <= port <= hi


def security_group_egress_verdict(rules: list) -> dict:
    """What the attached security groups' EGRESS rules say about the mail ports.

    2026-10-21 scene evidence: the SMTP area printed "rule review is manual --
    no verified rule-read API in this tier" while DescribeSecurityGroupAttribute
    was already whitelisted, so an egress-block scene got no branch-specific
    read. The read is now done and reduced here; policy values are compared
    case-insensitively and non-TCP / ingress rules are ignored.
    """
    denied: list = []
    allowed: list = []
    for rule in rules or []:
        if not isinstance(rule, dict):
            continue
        direction = str(rule.get("_direction") or rule.get("Direction")
                        or "egress").lower()
        if direction != "egress":
            continue
        proto = str(rule.get("IpProtocol") or "").lower()
        if proto not in ("tcp", "all", "-1"):
            continue
        ports = [p for p in MAIL_PORTS
                 if _port_range_covers(p, rule.get("PortRange"))]
        if not ports:
            continue
        item = {"sg": str(rule.get("_sg") or rule.get("SecurityGroupId") or ""),
                "policy": str(rule.get("Policy") or "").lower(),
                "ports": ports,
                "dest": str(rule.get("DestCidrIp")
                            or rule.get("SourceCidrIp") or ""),
                "port_range": str(rule.get("PortRange") or "")}
        if item["policy"] == "drop":
            denied.append(item)
        elif item["policy"] == "accept":
            allowed.append(item)
    return {"denied_ports": sorted({p for d in denied for p in d["ports"]}),
            "allowed_ports": sorted({p for a in allowed for p in a["ports"]}),
            "deny_rules": denied, "allow_rules": allowed}


# Boundary assertions: a flipped match here would either blame the security
# group for a port it does not cover or miss a real deny-all rule.
assert _port_range_covers(25, "25/25") and not _port_range_covers(465, "25/25")
assert _port_range_covers(587, "-1/-1") and _port_range_covers(465, "1/65535")
assert not _port_range_covers(25, "") and not _port_range_covers(25, "bad")
_e = security_group_egress_verdict([
    {"IpProtocol": "tcp", "PortRange": "25/25", "Policy": "Drop",
     "DestCidrIp": "0.0.0.0/0", "_direction": "egress", "_sg": "sg-1"},
    {"IpProtocol": "tcp", "PortRange": "465/587", "Policy": "Accept"},
    {"IpProtocol": "udp", "PortRange": "-1/-1", "Policy": "Drop"},
    {"IpProtocol": "tcp", "PortRange": "-1/-1", "Policy": "Drop",
     "Direction": "ingress"},
])
assert _e["denied_ports"] == [25], _e
assert _e["allowed_ports"] == [465, 587], _e
assert security_group_egress_verdict([])["denied_ports"] == []
assert security_group_egress_verdict(None)["allowed_ports"] == []


# Boundary assertions for the unblock-application IP-form verdict (each branch
# drives a different application instruction, so a flipped guard misdirects the
# customer's port-25 request).
assert ip_form_verdict(_facts(public_ips=["1.2.3.4"]))[0] == "vpc-fixed-public-ipv4"
assert ip_form_verdict(_facts(eip="4.3.2.1"))[0] == "vpc-eip"
assert ip_form_verdict(_facts(instance_network_type="classic",
                               public_ips=["1.1.1.1"]))[0] == "classic-network-public-ip"
assert ip_form_verdict(_facts())[0] == "none"   # VPC, no public ip, no eip
# classic + EIP-only (no fixed public ip) is neither of the named forms: it must
# fall through to "unknown", not be silently guessed as a usable application IP.
assert ip_form_verdict(_facts(instance_network_type="classic",
                              eip="5.5.5.5"))[0] == "unknown"
# an unrecognised network type carrying a public ip must NOT be mislabelled as
# the classic form -- only net == "classic" may claim classic-network-public-ip.
assert ip_form_verdict(_facts(instance_network_type="hybrid",
                              public_ips=["9.9.9.9"]))[0] == "unknown"


# ---------------------------------------------------------------------------
# Attribution engine (pure function over collected evidence)
# ---------------------------------------------------------------------------

def is_overseas_region(region_id: str) -> bool:
    return (region_id.startswith(OVERSEAS_REGION_PREFIXES)
            or region_id in EXTRA_OVERSEAS_REGIONS)


assert is_overseas_region("eu-west-1") and not is_overseas_region("cn-hangzhou")
assert is_overseas_region("cn-hongkong")


def target_is_domestic_provider(host: str) -> bool:
    host = (host or "").lower()
    return any(frag in host for frag in DOMESTIC_PROVIDER_HINTS)


assert target_is_domestic_provider("MX.QQ.com") is True    # case-insensitive
assert target_is_domestic_provider("smtp.gmail.com") is False
assert target_is_domestic_provider("") is False


def attribute_layer(direction: str, facts: Optional[dict], states: dict,
                    sigs: list, target_host: str, identity_type: str,
                    listener_25: str, container_mapped: str,
                    egress: Optional[dict] = None) -> dict:
    """Route the evidence through the decision tree of SKILL.md
    'Orchestration'. Returns layer/confidence/reasons/guidance/status.

    `egress` is the reduced DescribeSecurityGroupAttribute result; None means
    the layer was never read (no SG id, or the read failed), which stays an
    evidence gap rather than being reported as "not the blocker".
    """
    reasons: list[str] = []
    guidance: list[str] = []
    handoffs: list[str] = []
    notes: list[str] = []
    status = STATUS_OK
    layer = LAYER_NOT_ATTRIBUTED
    confidence = "low"

    sig_ids = [s["id"] for s in sigs]
    peer_sigs = [s for s in sigs if s["layer"] == LAYER_PEER_APPLICATION]
    ipv6_target = is_ipv6_literal(target_host)
    port25 = states.get(25)
    secure_open = any(states.get(p) in ("connected", "connected-closed",
                                        "banner-error") for p in (465, 587))
    secure_blocked = all(states.get(p) == "timeout" for p in (465, 587)) \
        if 465 in states and 587 in states else (
            states.get(465) == "timeout" or states.get(587) == "timeout") \
        if (465 in states or 587 in states) else False
    baseline_fail = any(states.get(p) == "timeout" for p in BASELINE_PORTS)

    if direction == "apply":
        layer = LAYER_APPLY_ELIGIBILITY
        guidance.append("eligibility")
        if "ip-usage-permission" in sig_ids:
            confidence = "high"
            reasons.append(
                "Reported application error matches the IP "
                "usage-permission signature (ticket T-384967AE: resolved by "
                "referencing the VPC public IP).")
        if facts:
            form, why = ip_form_verdict(facts)
            reasons.append(f"Public-IP pre-check: {form} -- {why}")
            confidence = "high" if "ip-usage-permission" in sig_ids else "medium"
        if ipv6_target:
            reasons.append("Target/IPv6: "
                           + POLICY_STATEMENTS["ipv6-25"]["text"])
        if identity_type == "SubUser":
            reasons.append(
                "Caller is a RAM sub-account: if it cannot view the block "
                "state or submit the application, that is an authorization "
                "gap, not a mail-port problem (ticket T-F418FAF1 pattern).")
            handoffs.append("ram-subaccount")
        if not facts:
            status = STATUS_DEGRADED
            reasons.append("Instance facts unavailable -- eligibility "
                           "answered from policy text only.")
        return _finish(layer, confidence, reasons, guidance, handoffs, notes,
                       status)

    if direction == "receive":
        guidance.append("receive-inbound")
        if listener_25 == "no" or container_mapped == "no":
            layer, confidence = LAYER_UNLISTENING, "high"
            reasons.append(
                "Customer-supplied listener fact: nothing on TCP 25 at the "
                "host interface (container port possibly unmapped -- "
                "ticket T-065FBFCF pattern).")
        elif port25 == "refused":
            layer, confidence = LAYER_UNLISTENING, "medium"
            reasons.append("Inbound 25 test was REFUSED: path reachable but "
                           "no service listening on the host.")
        else:
            layer = LAYER_NOT_ATTRIBUTED
            confidence = "low"
            status = STATUS_DEGRADED
            reasons.append(
                "Receive-side needs the three guest readings (listener, "
                "firewall, external port test); platform INBOUND-25 policy "
                "is UNCONFIRMED in current evidence -- see "
                "POLICY_STATEMENTS['inbound-25'] (verify before promising).")
        return _finish(layer, confidence, reasons, guidance, handoffs, notes,
                       status)

    # --- send direction -----------------------------------------------------
    # Security-group egress is read from the cloud, so the branch that used to
    # be "manual rule review" now has decisive evidence in both directions.
    egress_denied = (egress or {}).get("denied_ports") or []
    if egress is not None:
        if not egress_denied:
            notes.append(
                "Security-group EGRESS rules read: no DROP rule covers TCP "
                "25/465/587, so the attached groups are not blocking mail "
                "ports (rule precedence aside).")
        elif port25 in (None, "timeout"):
            hit = [p for p in egress_denied
                   if p == 25 or (p in (465, 587) and secure_blocked)]
            if hit:
                rules = [r for r in egress.get("deny_rules", [])
                         if set(r["ports"]) & set(hit)]
                detail = "; ".join(
                    "sg=%s %s policy=drop range=%s dest=%s"
                    % (r["sg"] or "?", r["ports"], r["port_range"],
                       r["dest"] or "?") for r in rules[:3])
                layer, confidence = LAYER_CUSTOMER_CONFIG, "high"
                reasons.append(
                    "Security-group EGRESS has a DROP rule covering mail "
                    f"port(s) {hit}: {detail or 'deny rule returned'} -- the "
                    "cloud-side rule blocks the connection before the guest "
                    "is reached.")
                guidance.append("customer-config")
                return _finish(layer, confidence, reasons, guidance, handoffs,
                               notes, status)

    if "illegal-address" in sig_ids:
        layer = "customer-code-or-mail-product-layer"
        confidence = "high"
        reasons.append("AddressException/Illegal address is a client-side "
                       "code or product issue, not a network block.")
        guidance.append("peer-application")
        notes.append("Relay the 'illegal-address' signature guidance from "
                     "references/smtp-block-diagnosis__smtp-error-signatures.md.")
        return _finish(layer, confidence, reasons, guidance, handoffs, notes,
                       status)

    if ipv6_target and port25 in (None, "timeout"):
        layer = LAYER_APPLY_ELIGIBILITY
        confidence = "high"
        reasons.append("Target is an IPv6 literal: "
                       + POLICY_STATEMENTS["ipv6-25"]["text"]
                       + " (ticket T-F418FAF1)")
        guidance.append("eligibility")
        guidance.append("platform-block")
        return _finish(layer, confidence, reasons, guidance, handoffs, notes,
                       status)

    if peer_sigs and (port25 not in ("timeout", "refused") or secure_open):
        # SMTP conversation-level replies exist AND the path is proven
        # reachable (or 25 is not the failing port): peer application layer.
        layer = LAYER_PEER_APPLICATION
        confidence = "high" if secure_open else "medium"
        for s in peer_sigs:
            reasons.append(f"Signature '{s['id']}': {s['headline']} "
                           f"[source: {s['source']}]")
        reasons.append("A 4xx/5xx SMTP reply or banner proves the TCP "
                       "session was established -- this is NOT the platform "
                       "port-25 block (ticket T-BFFFC987 pattern).")
        guidance.append("peer-application")
        if is_overseas_region(facts["region_id"] if facts else "") and \
                target_is_domestic_provider(target_host):
            handoffs.append("cross-border")
            notes.append("Overseas-region instance toward a domestic "
                         "provider: consider the cross-border-link "
                         "explanation (ticket T-8E8AD7A5).")
        return _finish(layer, confidence, reasons, guidance, handoffs, notes,
                       status)

    if port25 == "timeout":
        if secure_open:
            layer, confidence = LAYER_PLATFORM_BLOCK, "high"
            reasons.append(
                "Port matrix: 25 times out while 465/587 (or the 80/443 "
                "control) succeed -- the exact platform outbound-25 "
                "signature (POLICY_STATEMENTS['outbound-25-default']).")
            guidance.append("platform-block")
        elif secure_blocked and not baseline_fail:
            layer, confidence = LAYER_CUSTOMER_CONFIG, "high"
            reasons.append(
                "Port matrix: 465 AND 587 also time out while 80/443 pass "
                "-- the platform does not restrict 465/587, so this is the "
                "customer layer: security-group EGRESS rules or the guest "
                "firewall (ticket T-897D4DEA pattern).")
            guidance.append("customer-config")
        elif secure_blocked and baseline_fail:
            layer, confidence = LAYER_CUSTOMER_CONFIG, "medium"
            reasons.append(
                "Every tested port times out including the 80/443 controls "
                "-- broader egress problem (route/NAT/firewall), not the "
                "25 policy alone.")
            guidance.append("customer-config")
            handoffs.append("non-mail-port")
        else:
            layer, confidence = LAYER_PLATFORM_BLOCK, "medium"
            status = STATUS_DEGRADED
            reasons.append(
                "25 times out; no 465/587/443 control reading supplied -- "
                "platform block is the most frequent cause but confirm with "
                "the control ports (request the readings).")
            guidance.append("platform-block")
            guidance.append("degraded")
        if facts and ip_form_verdict(facts)[0] in ("none",
                                                   "classic-network-public-ip"):
            notes.append("IP-form note for any unblock application: "
                         + ip_form_verdict(facts)[1])
        return _finish(layer, confidence, reasons, guidance, handoffs, notes,
                       status)

    if port25 == "refused":
        layer, confidence = LAYER_PEER_APPLICATION, "medium"
        reasons.append("Egress reached the remote end (RST came back): the "
                       "provider itself refused the session -- contact the "
                       "receiving provider; not a platform block.")
        guidance.append("peer-application")
        return _finish(layer, confidence, reasons, guidance, handoffs, notes,
                       status)

    if port25 in ("connected", "connected-closed", "banner-error"):
        layer, confidence = LAYER_PEER_APPLICATION, "medium"
        reasons.append("TCP 25 is REACHABLE from this instance -- the "
                       "failure (if any) is application/provider side. A "
                       "connected-then-closed result still counts as "
                       "reachable (ticket T-8E8AD7A5: connect != deliver).")
        guidance.append("peer-application")
        guidance.append("unresolved")
        status = STATUS_DEGRADED
        notes.append("Paste the SMTP banner + first client command + reply "
                     "(--error-text) for a precise signature verdict.")
        return _finish(layer, confidence, reasons, guidance, handoffs, notes,
                       status)

    # No port evidence at all -> degrade to the readings checklist.
    layer = LAYER_NOT_ATTRIBUTED
    confidence = "low"
    status = STATUS_DEGRADED
    reasons.append("No in-guest readings available (none passed, no probe "
                   "dispatched): cloud-side facts alone cannot separate the "
                   "platform 25 policy from a customer security-group/"
                   "firewall issue or a provider rejection.")
    guidance.append("degraded")
    guidance.append("guest-gate")
    if sigs:
        guidance.append("peer-application")
        for s in sigs:
            reasons.append(f"Signature '{s['id']}': {s['headline']}")
    return _finish(layer, confidence, reasons, guidance, handoffs, notes,
                   status)


def _finish(layer: str, confidence: str, reasons: list, guidance: list,
            handoffs: list, notes: list, status: str) -> dict:
    # De-duplicate while preserving order.
    seen: set = set()
    uniq_guidance = [g for g in guidance if not (g in seen or seen.add(g))]
    seen = set()
    uniq_handoffs = [h for h in handoffs if not (h in seen or seen.add(h))]
    return {"layer": layer, "confidence": confidence, "reasons": reasons,
            "guidance_keys": uniq_guidance, "handoff_ids": uniq_handoffs,
            "notes": notes, "status": status}


# --- boundary tests for the attribution engine (pure-function discipline) --
_no_facts = None
_v = attribute_layer("send", _no_facts, {25: "timeout", 465: "connected",
                                         443: "connected"}, [], "", "SubUser",
                     "unknown", "unknown")
assert _v["layer"] == LAYER_PLATFORM_BLOCK and _v["confidence"] == "high"
_v = attribute_layer("send", _no_facts, {25: "timeout", 465: "timeout",
                                         587: "timeout", 443: "connected"},
                     [], "", "SubUser", "unknown", "unknown")
assert _v["layer"] == LAYER_CUSTOMER_CONFIG
_v = attribute_layer("send", _no_facts, {}, match_signatures(
    "550 Bad HELO - Host impersonating domain name [x.com]"),
    "smtp.example.com", "", "unknown", "unknown")
assert _v["layer"] == LAYER_PEER_APPLICATION
_v = attribute_layer("send", _no_facts, {}, [], "", "", "unknown", "unknown")
assert _v["status"] == STATUS_DEGRADED and _v["layer"] == LAYER_NOT_ATTRIBUTED
_v = attribute_layer("receive", _no_facts, {}, [], "", "", "no", "unknown")
assert _v["layer"] == LAYER_UNLISTENING and _v["status"] == STATUS_OK
# -- security-group EGRESS read: decisive only when it actually covers a tested port
_deny25 = {"denied_ports": [25], "allowed_ports": [],
           "deny_rules": [{"sg": "sg-1", "policy": "drop", "ports": [25],
                           "dest": "0.0.0.0/0", "port_range": "25/25"}],
           "allow_rules": []}
_v = attribute_layer("send", _no_facts, {25: "timeout"}, [], "", "",
                     "unknown", "unknown", egress=_deny25)
assert _v["layer"] == LAYER_CUSTOMER_CONFIG and _v["confidence"] == "high", _v
assert any("sg-1" in r for r in _v["reasons"]), _v
# a DROP that covers only 465/587 cannot explain a port-25 timeout while both
# secure ports still connect -- it must not be promoted to the cause
_deny_secure = {"denied_ports": [465, 587], "allowed_ports": [],
                "deny_rules": [{"sg": "sg-1", "policy": "drop",
                                "ports": [465, 587], "dest": "",
                                "port_range": "465/587"}],
                "allow_rules": []}
_v = attribute_layer("send", _no_facts, {25: "timeout", 465: "connected",
                                         587: "connected"}, [], "", "",
                     "unknown", "unknown", egress=_deny_secure)
assert _v["layer"] != LAYER_CUSTOMER_CONFIG, _v
# egress read but no DROP: say so instead of leaving the rule layer unmentioned
_v = attribute_layer("send", _no_facts, {25: "timeout"}, [], "", "",
                     "unknown", "unknown",
                     egress=security_group_egress_verdict([]))
assert any("not blocking mail ports" in n for n in _v["notes"]), _v


# ---------------------------------------------------------------------------
# Handoff matching over the customer's own words
# ---------------------------------------------------------------------------

def detect_handoffs(texts: list[str], verdict: dict) -> list[dict]:
    blob = " ".join(t for t in texts if t)
    hits = []
    for rule in HANDOFF_RULES:
        if rule["id"] in verdict.get("handoff_ids", []) or (
                blob and re.search(rule["match"], blob, re.I)):
            hits.append({"id": rule["id"], "target": rule["target"],
                         "sentence": rule["sentence"]})
    # engine-requested handoffs (e.g. cross-border) without regex hit:
    for rid in verdict.get("handoff_ids", []):
        if not any(h["id"] == rid for h in hits):
            rule = next((r for r in HANDOFF_RULES if r["id"] == rid), None)
            if rule:
                hits.append({"id": rule["id"], "target": rule["target"],
                             "sentence": rule["sentence"]})
    return hits


# detect_handoffs: lock both feeding mechanisms (engine-requested ids and
# regex hits), the no-duplicate invariant, and the output shape.
_h = detect_handoffs(["nothing matches here"], {"handoff_ids": ["non-mail-port"]})
assert [x["id"] for x in _h] == ["non-mail-port"], _h
assert all({"id", "target", "sentence"} <= set(x) for x in _h)
# an id requested by the engine AND matched by regex must appear exactly once
_h2 = detect_handoffs(["some text"], {"handoff_ids": ["non-mail-port", "non-mail-port"]})
assert [x["id"] for x in _h2] == ["non-mail-port"], _h2
assert detect_handoffs(["plain wording"], {}) == []
assert detect_handoffs([], {"handoff_ids": []}) == []


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_readings() -> list[str]:
    lines = []
    for r in READINGS:
        lines.append(f"[{r['id']}] {r['title']}")
        lines.append(f"    why: {r['why']}")
        for c in r["commands"]:
            lines.append(f"    run: {c}")
        lines.append(f"    report: {r['report_back']}")
        lines.append(f"    note: {r['note']}")
    return lines


def build_report(args: argparse.Namespace, identity: dict, actions: list,
                 facts: Optional[dict], status_api: Optional[str],
                 invocations: list, verdict: dict, errors: list,
                 probe: Optional[dict] = None,
                 states: Optional[dict] = None,
                 egress: Optional[dict] = None) -> dict:
    layer = verdict["layer"]
    guidance = []
    for key in verdict["guidance_keys"]:
        guidance.append({"block": key,
                         "steps": list(GUIDANCE_BLOCKS.get(key, ()))})
    docs = {k: {"title": v["title"], "url": v["url"]}
            for k, v in DOC_LINKS.items()}
    auto_filled = []
    if getattr(args, "direction_defaulted", False):
        auto_filled.append("--direction defaulted to 'send' (not passed)")
    if identity.get("account_id") and not args.uid:
        auto_filled.append(f"UID auto-derived via STS GetCallerIdentity: "
                           f"{identity['account_id']}")
    merged_states = states if states is not None else _states_from(args)
    return {
        "skill": SKILL_NAME,
        "api_versions": dict(API_VERSIONS),
        "target": {"region_id": args.region_id,
                   "instance_id": args.instance_id,
                   "public_ip_address": args.public_ip_address,
                   "direction": args.direction,
                   "target_host": args.target_host,
                   "target_port": args.target_port},
        "caller": identity,
        "auto_filled": auto_filled,
        "actions_executed": actions,
        "instance_facts": facts,
        "security_group_egress": egress,
        "status_from_api": status_api or "",
        "invocation_records": invocations,
        "guest_readings": {str(k): v for k, v in sorted(merged_states.items())},
        "guest_probe": probe_report_view(probe) if probe else None,
        "matched_signatures": [s["id"] for s in match_signatures(
            args.error_text or "")],
        "verdict": {
            "layer": layer,
            "confidence": verdict["confidence"],
            "reasons": verdict["reasons"],
        },
        "manual_guidance": guidance,
        "policy_statements_quoted": {
            k: {"text": POLICY_STATEMENTS[k]["text"],
                "source": POLICY_STATEMENTS[k]["source"]}
            for k in ("outbound-25-default", "apply-flow", "agreement-scope",
                      "secure-ports-open")},
        "readings_requested": list(READINGS) if verdict["status"]
        == STATUS_DEGRADED else [],
        "handoffs": detect_handoffs(
            [args.error_text or "", args.customer_text or "",
             args.target_host or ""], verdict),
        "notes": verdict["notes"],
        "reference_docs": docs,
        "errors": errors,
        "limitations": [
            "The port-25 unblock application itself is a human console + "
            "review process; this skill never submits, tracks, or promises "
            "it.",
            "No public API exists to query an instance's unblock "
            "application history or review state; the customer checks their "
            "console and the notification email.",
            "In-guest state is collected solely through the "
            "confirmation-gated probe channel: Linux guests, one whitelisted "
            "inspection template per approved run, and the Cloud Assistant "
            "agent must be online. Windows guests stay on the manual "
            "readings checklist. Security-group EGRESS rules of the attached "
            "groups are read and reduced to the mail ports (25/465/587) only; "
            "ingress rules and non-mail ports are out of scope, and a failed "
            "rule read leaves the rule layer UNKNOWN rather than cleared.",
            "Packet-level and cross-border link analysis are out of scope "
            "and get handed off.",
        ],
        "status": verdict["status"],
        "next_action": "",
    }


def _states_from(args: argparse.Namespace) -> dict:
    states: dict[int, str] = {}
    for value in args.port_results or []:
        port, state = value
        states[port] = state
    return states


def render_probe(probe: dict) -> list[str]:
    """Render one probe record: gate state, the four disclosure parts, the
    exact command text, the result and what was derived from it."""
    lines = [f"[{probe['probe_id']}] {probe['title']}"]
    lines.append(f"    gate        : {probe['gate']}")
    lines.append(f"    status      : {probe['status']}"
                 + (f"  (InvokeId {probe['invoke_id']})"
                    if probe["invoke_id"] else ""))
    if probe["exit_code"] != "":
        lines.append(f"    exit code   : {probe['exit_code']}")
    lines.append(f"    what it does: {probe['disclosure']}")
    lines.append(f"    reversible  : {probe['reversible']}")
    lines.append(f"    duration    : guest command Timeout "
                 f"{probe['timeout_seconds']}s; output read-back window "
                 f"{PROBE_MAX_WAIT_SECONDS}s")
    lines.append(f"    replaces    : manual reading "
                 f"'{probe['replaces_reading'] or 'n/a'}'")
    if probe["error"]:
        lines.append(f"    error       : {probe['error']}")
    lines.append("    command (exactly what "
                 + ("ran" if probe["gate"] == "DISPATCH-APPROVED" else "would")
                 + "):")
    for line in probe["command"].rstrip("\n").splitlines():
        lines.append("      | " + line)
    if probe["output"]:
        lines.append("    output"
                     + (" (truncated)" if probe["output_truncated"] else "")
                     + ":")
        for line in probe["output"].rstrip("\n").splitlines():
            lines.append("      > " + line)
    if probe["derived_port_states"]:
        lines.append(f"    derived     : port states "
                     f"{probe['derived_port_states']}")
    if probe["derived_listener_25"] != "unknown":
        lines.append(f"    derived     : listener on 25 = "
                     f"{probe['derived_listener_25']}")
    return lines


def render_text(report: dict) -> str:
    out: list[str] = []
    w = out.append
    w("=" * 72)
    w(" ECS MAIL / PORT-25 DIAGNOSIS  (" + report["target"]["region_id"] + ")")
    w("=" * 72)
    t = report["target"]
    w(f"Target        : {t['instance_id'] or t['public_ip_address']} "
      f"(direction={t['direction']}"
      + (f", mail target {t['target_host']}:{t['target_port']}"
         if t["target_host"] else "") + ")")
    c = report["caller"]
    w(f"Caller        : UID {c.get('account_id') or 'n/a'} "
      f"[identity: {c.get('identity_type') or 'n/a'}] (auto-derived, "
      f"STS GetCallerIdentity)")
    if report["auto_filled"]:
        w("Auto-filled   : " + "; ".join(report["auto_filled"]))

    w("")
    w("[1] Cloud evidence (read queries plus any approved gated dispatch)")
    inst = report["instance_facts"]
    if inst:
        w(f"  instance      : {inst['instance_id']} name={inst['instance_name']}"
          f" status={inst['status']}")
        if report["status_from_api"]:
            w(f"  status (API)  : {report['status_from_api']} "
              f"(DescribeInstanceStatus)")
        w(f"  network       : {inst['instance_network_type'] or 'n/a'} "
          f"public IPv4={', '.join(inst['public_ips']) or '-'} "
          f"EIP={inst['eip'] or '-'} bandwidthOut="
          f"{inst['internet_max_bandwidth_out']}")
        form, why = (ip_form_verdict(inst) if inst else ("unknown", ""))
        w(f"  IP form       : {form} -- {why}")
        w(f"  security grps : {', '.join(inst['security_group_ids']) or 'n/a'}")
        eg = report.get("security_group_egress")
        if eg is not None:
            total_rules = len(eg.get("allow_rules", [])) + len(eg.get("deny_rules", []))
            if eg.get("denied_ports"):
                w(f"  SG egress     : DROP covers TCP port(s) "
                  f"{eg['denied_ports']} ({total_rules} mail-port rule(s) "
                  f"read from the attached groups)")
            else:
                w(f"  SG egress     : {total_rules} mail-port rule(s) read; "
                  f"no DROP covers TCP 25/465/587 (egress not the blocker)")
    for a in report["actions_executed"]:
        w(f"  call          : {a['action']} [{a['how']}] -> {a['result']}")
    for inv in report["invocation_records"]:
        w(f"  invocation    : {inv['invoke_id']} {inv['command_name']} "
          f"status={inv['status']} at {inv['creation_time']}")

    if report.get("guest_probe"):
        w("")
        w("[2] Gated in-guest inspection (one approved inspection-only "
          "command)")
        for line in render_probe(report["guest_probe"]):
            w("  " + line)

    w("")
    w("[3] Layer attribution")
    v = report["verdict"]
    w(f"  VERDICT       : {v['layer']} (confidence: {v['confidence']})")
    for r in v["reasons"]:
        w(f"    reason: {r}")
    if report["guest_readings"]:
        w(f"  port readings : {report['guest_readings']}")
    if report["matched_signatures"]:
        w(f"  signatures    : {', '.join(report['matched_signatures'])}")
    for n in report["notes"]:
        w(f"  note          : {n}")

    w("")
    w("[4] Policy statements quoted (unified wording)")
    for k, ps in report["policy_statements_quoted"].items():
        w(f"  {k}: {ps['text']} [source: {ps['source']}]")

    w("")
    w("[5] Manual guidance (this skill never applies changes or submits "
      "applications)")
    for block in report["manual_guidance"]:
        w(f"  ({block['block']})")
        for step in block["steps"]:
            w(f"    - {step}")

    if report["readings_requested"]:
        w("")
        w("[6] Readings still missing -- prefer the confirmation-gated probe "
          "above; otherwise ask the customer to run these inspection-only "
          "commands in their own session")
        for line in render_readings():
            w("  " + line)

    if report["handoffs"]:
        w("")
        w("[7] Out-of-scope signals -> handoff (routing only)")
        for h in report["handoffs"]:
            w(f"  -> {h['target']}: {h['sentence']}")

    if report["errors"]:
        w("")
        w("[8] Degrade log")
        for e in report["errors"]:
            w(f"  [WARN] {e}")

    w("")
    w("[9] Not covered / limitations")
    for lim in report["limitations"]:
        w(f"  - {lim}")

    w("")
    w("Summary")
    w("-------")
    probe = report.get("guest_probe")
    w(f"What was checked: cloud facts ({len(report['actions_executed'])} "
      f"API call(s)) + "
      + (f"1 gated guest probe ({probe['probe_id']}, "
         f"{probe['status']}) + " if probe else "")
      + f"{len(report['guest_readings'])} guest port reading(s) + "
      f"{len(report['matched_signatures'])} error signature(s).")
    w(f"Key finding    : {v['layer']} (confidence {v['confidence']}).")
    w(f"STATUS: {report['status']}")
    w(f"NEXT_ACTION: {report['next_action']}")
    return "\n".join(out)


def compute_next_action(report: dict, args: argparse.Namespace) -> str:
    layer = report["verdict"]["layer"]
    status = report["status"]
    probe = report.get("guest_probe")
    if status == STATUS_DEGRADED and layer == LAYER_NOT_ATTRIBUTED:
        if probe and probe["gate"] != "DISPATCH-APPROVED":
            return ("relay the [2] disclosure to the user and, only after "
                    "they approve, re-run with --user-confirmation "
                    f"{PROBE_CONFIRMATION_TOKEN} to dispatch the "
                    f"{probe['probe_id']} inspection")
        if not probe:
            return ("offer the confirmation-gated port-probe (show the "
                    "GUEST_PROBES disclosure, then re-run with "
                    "--execute-probe port-probe --user-confirmation "
                    f"{PROBE_CONFIRMATION_TOKEN}); if the probe channel is "
                    "unusable or declined, collect the [6] readings manually "
                    "and re-run with --port-result values")
        return ("collect the [6] readings from the customer (port matrix, "
                "listener, local firewall), then re-run with --port-result "
                "values")
    if layer == LAYER_PLATFORM_BLOCK:
        return ("confirm the customer's use case against the Port-25 Usage "
                "Service Agreement, then relay the 465/587 relay path and "
                "the console application guidance (manual only)")
    if layer == LAYER_CUSTOMER_CONFIG:
        return ("walk the customer through the security-group egress and "
                "local-firewall self-check, retest one change at a time")
    if layer == LAYER_PEER_APPLICATION:
        return ("relay the matched SMTP signature guidance from "
                "references/smtp-block-diagnosis__smtp-error-signatures.md and route identity/"
                "throttling questions to the receiving mail provider")
    if layer == LAYER_UNLISTENING:
        return "guide the customer to publish the mail service on the host (listener/container mapping)"
    if layer == LAYER_APPLY_ELIGIBILITY:
        return "relay the eligibility pre-check result and the manual application path (console + ~1 business day review)"
    if layer == LAYER_CROSS_BORDER:
        return "hand off to the cross-border link diagnosis flow"
    return "gather the missing evidence or hand the material list to human support"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ecs_smtp_block_diagnosis.py",
        description=("Attribute ECS mail (SMTP/port 25) failures across the "
                     "platform block, customer config, guest listener, "
                     "application eligibility and peer-server layers. "
                     "Non-mutating cloud queries, plus an optional "
                     "confirmation-gated inspection-only command channel "
                     "(--execute-probe)."),
    )
    p.add_argument("--region-id", required=True, type=_region_type,
                   help="Instance region, e.g. cn-hangzhou")
    idg = p.add_mutually_exclusive_group(required=True)
    idg.add_argument("--instance-id", type=_instance_id_type,
                     help="ECS instance id (i-...)")
    idg.add_argument("--public-ip-address", type=_ip_type,
                     help="Instance public IPv4 to look up")
    p.add_argument("--direction", choices=("send", "receive", "apply"),
                   default=None,
                   help="Symptom area: cannot send / cannot receive / "
                        "unblock application blocked (default: send)")
    p.add_argument("--target-host", default="",
                   help="Destination SMTP/MX host or IP under test")
    p.add_argument("--target-port", type=int, default=None,
                   help="Destination port under test (1-65535)")
    p.add_argument("--port-result", dest="port_results", action="append",
                   type=parse_port_result, metavar="PORT=STATE",
                   help=("Customer-supplied TCP test result; repeatable. "
                         f"States: {', '.join(PORT_STATES)}"))
    p.add_argument("--error-text", default="",
                   help="Customer-visible SMTP/console error text to match "
                        "against the embedded signatures")
    p.add_argument("--customer-text", default="",
                   help="Customer's own symptom wording (used for "
                        "out-of-scope handoff detection)")
    p.add_argument("--listener-25", choices=("yes", "no", "unknown"),
                   default="unknown",
                   help="From the customer's ss/netstat reading: is anything "
                        "listening on 0.0.0.0:25 on the host")
    p.add_argument("--container-mapped", choices=("yes", "no", "unknown"),
                   default="unknown",
                   help="Is the mail service port published from the "
                        "container to the host")
    p.add_argument("--include-invocations", action="store_true",
                   help="Attach recent Cloud Assistant invocation records "
                        "for the instance (history reconcile only)")
    p.add_argument("--execute-probe", choices=tuple(sorted(GUEST_PROBES)),
                   type=_probe_id_type, default=None,
                   help="Confirmation-gated in-guest inspection: dispatch "
                        "ONE fixed inspection-only command template "
                        "(Cloud Assistant RunCommand). Without this flag the "
                        "whole run is non-mutating. Requires "
                        "--user-confirmation; without that token nothing is "
                        "dispatched and the disclosure is printed instead.")
    p.add_argument("--user-confirmation", default="",
                   help=(f"Exact token proving the user approved THIS single "
                         f"inspection command after seeing the disclosure: "
                         f"{PROBE_CONFIRMATION_TOKEN}"))
    p.add_argument("--probe-host", default=None, type=_probe_host_type,
                   help="Target hostname or bare IP literal for probes that "
                        "need one (port-probe, path-info)")
    p.add_argument("--probe-port", dest="probe_ports", action="append",
                   type=_probe_port_type, metavar="N",
                   help=f"Port tested by port-probe; repeatable up to "
                        f"{PROBE_MAX_PORTS} (default: "
                        f"{', '.join(str(p) for p in PROBE_DEFAULT_PORTS)})")
    p.add_argument("--uid", default=None,
                   help="Optional expected account UID (consistency label)")
    p.add_argument("--profile", default=None,
                   help="Optional aliyun CLI credential profile name")
    p.add_argument("--json", action="store_true", help="JSON output")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    args.direction_defaulted = args.direction is None
    if args.direction is None:
        args.direction = "send"
    if args.target_port is not None and not 1 <= args.target_port <= 65535:
        print("Missing or invalid parameter: --target-port must be "
              "1-65535. Aborting diagnostic workflow.", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: re-run with a valid --target-port")
        return 1

    actions: list[dict] = []
    errors: list[str] = []

    _cli.check_cli_available()

    # Step 1: identity (credential sanity + UID traceability label).
    identity = _cli.resolve_account_id(region=args.region_id,
                                       profile=args.profile)
    actions.append({"action": "sts GetCallerIdentity",
                    "how": "default credential chain",
                    "result": "ok" if identity["account_id"] else "failed"})
    if not identity["account_id"]:
        print("[ERROR] The default credential chain could not be resolved "
              "(sts get-caller-identity failed). Run `aliyun sts get-caller-identity`; "
              "never pass access keys to this script.", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: configure the aliyun CLI default credential "
              "chain (aliyun sts get-caller-identity), then re-run")
        return 1
    if args.uid and args.uid != identity["account_id"]:
        errors.append(f"provided --uid {args.uid} differs from caller "
                      f"{identity['account_id']}; results reflect the "
                      f"caller's account only")
        print(f"[WARN] {errors[-1]}", file=sys.stderr)

    # Step 2: locate the instance.
    inst, failure_note = describe_instance(args.region_id, args.instance_id,
                                           args.public_ip_address,
                                           args.profile, actions)
    if inst is None:
        reason = failure_note
        fatal = bool(reason)
        if fatal and ("NoPermission" in reason or "ImplicitDeny" in reason):
            print("[ERROR] ecs DescribeInstances was denied (NoPermission / "
                  "ImplicitDeny): grant the read actions listed in "
                  "references/ram-policies.md to this principal, then "
                  "re-run.", file=sys.stderr)
        if fatal:
            print(f"[ERROR] instance query failed: {reason}", file=sys.stderr)
        else:
            print("[ERROR] no ECS instance found for the given "
                  f"{'instance id' if args.instance_id else 'public IP'} in "
                  f"{args.region_id}: verify the region, id, and that the "
                  f"address is currently associated with this account.",
                  file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: correct the region/id/IP (or fix the missing "
              "read permission per references/ram-policies.md), then re-run")
        return 1

    facts = extract_facts(inst, None)

    # Step 3: lifecycle status cross-check (degrades on failure).
    status_api = None
    if facts["instance_id"]:
        status_api = describe_status(args.region_id, facts["instance_id"],
                                     args.profile, actions)
        facts["status_api"] = status_api or ""
    if status_api and status_api != "Running":
        errors.append(f"instance status is {status_api}, not Running -- "
                      f"mail services cannot respond while stopped")

    # Step 3b: read the attached security groups' egress rules (read-side
    # only). The SMTP scene "security-group egress blocks mail" needs this
    # branch-specific read; a failed read stays an evidence gap.
    egress: Optional[dict] = None
    if facts["security_group_ids"]:
        _rules, _ok = describe_egress_rules(args.region_id,
                                            facts["security_group_ids"],
                                            args.profile, actions)
        if _ok:
            egress = security_group_egress_verdict(_rules)
        else:
            errors.append("security-group egress rules could not be read; "
                          "treat the security-group layer as UNKNOWN")

    # Step 4: optional Cloud Assistant invocation history (read-side only).
    invocations: list[dict] = []
    if args.include_invocations and facts["instance_id"]:
        invocations = describe_invocations(args.region_id,
                                           facts["instance_id"],
                                           args.profile, actions)

    # Step 5: optional confirmation-gated in-guest inspection.
    probe: Optional[dict] = None
    if args.execute_probe:
        if status_api and status_api != "Running":
            print("[ERROR] the instance is not Running, so a probe cannot "
                  "execute; fix the lifecycle state first (or use the manual "
                  "readings checklist).", file=sys.stderr)
            print("STATUS: FAIL")
            print("NEXT_ACTION: start the instance or drop --execute-probe "
                  "and collect the readings manually")
            return 1
        try:
            probe = collect_probe(args.region_id, facts["instance_id"], args,
                                  args.profile, actions)
        except ValueError as e:
            print(f"[ERROR] unusable probe request: {e}", file=sys.stderr)
            print("STATUS: FAIL")
            print("NEXT_ACTION: correct --probe-host / --probe-port (or run "
                  "without --execute-probe and use the manual readings)")
            return 1
        if probe["gate"] != "DISPATCH-APPROVED":
            print("[WARN] probe NOT dispatched: no valid --user-confirmation "
                  "token. Show the disclosure to the user and re-run with the "
                  "token only after they approve.", file=sys.stderr)
        elif probe["error"]:
            errors.append(f"probe {probe['probe_id']}: {probe['error']}")
            print(f"[WARN] probe degraded: {probe['error']}", file=sys.stderr)

    # Step 6: attribution (manual readings win over derived ones).
    states = _states_from(args)
    listener_25 = args.listener_25
    if probe and probe.get("derived_states"):
        for port, state in probe["derived_states"].items():
            if port in states and states[port] != state:
                errors.append(f"probe reported port {port} as {state} but "
                              f"--port-result said {states[port]}; using the "
                              f"value you passed")
                continue
            states.setdefault(port, state)
    if probe and probe.get("derived_listener_25") != "unknown" \
            and listener_25 == "unknown":
        listener_25 = probe["derived_listener_25"]
    if args.target_port and args.target_port not in states and \
            args.target_host:
        errors.append("--target-port supplied without a matching "
                      "--port-result reading")
    sigs = match_signatures(args.error_text or "")
    verdict = attribute_layer(args.direction, facts, states, sigs,
                              args.target_host,
                              identity["identity_type"],
                              listener_25, args.container_mapped,
                              egress=egress)
    if probe:
        verdict["guidance_keys"] = _with_guest_gate(verdict["guidance_keys"],
                                                    probe)

    # Step 7: report.
    report = build_report(args, identity, actions, facts, status_api,
                          invocations, verdict, errors, probe, states,
                          egress=egress)
    report["next_action"] = compute_next_action(report, args)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_text(report))
    return 0


def _with_guest_gate(guidance_keys: list, probe: dict) -> list:
    """A probe that was requested but not dispatched always surfaces its own
    gate block, so the disclosure reaches the user either way."""
    keys = list(guidance_keys)
    if probe["gate"] != "DISPATCH-APPROVED" and "guest-gate" not in keys:
        keys.append("guest-gate")
    return keys


if __name__ == "__main__":
    sys.exit(main())
