#!/usr/bin/env python3
"""
ecs_remote_connection_triage.py -- SINGLE ENTRY POINT of the Alibaba Cloud
ECS remote-connection entry triage skill (read-only + manual guidance).

SECURITY
--------
* READ-ONLY: every cloud call is a whitelisted Describe*/GetCallerIdentity
  query executed through `_cli.call()`, which refuses anything outside the
  embedded read-only whitelist BEFORE spawning a subprocess. This script
  never mutates a resource, never runs anything inside an instance, and
  never asks for, receives, stores or tests passwords, keys or AK/SK
  material. Guest-side checks are printed for the CUSTOMER to run and
  paste back.
* Input validation: region ids, instance ids, IPv4/v6 addresses and ports
  are regex/ipaddress validated before they can reach a command argument
  list; the CLI is always spawned with an argument list (never shell=True).
* Output contract: a human report or --json payload, ending with
  `STATUS: OK|DEGRADED|FAIL` + `NEXT_ACTION:` (see SKILL.md Output Contract).

WHAT IT DOES (triage tree S1..S5, all read-only)
------------------------------------------------
S1 identity + asset ownership  -> sts:GetCallerIdentity,
                                  ecs:DescribeInstances (by id, by public
                                  IP, by EIP)
S2 instance state + OS/protocol routing
S3 security-group port & source-CIDR evidence -> ecs:DescribeSecurityGroupAttribute
S4 fallback channels -> ecs:DescribeInstanceVncUrl,
                        ecs:DescribeCloudAssistantStatus
S5 saturation pre-screen -> cms:DescribeMetricLast (latest cpu_total)
plus: customer error-string matching against the embedded signature
catalog, intrusion-suspicion detection (identify + hand off), and a final
single verdict with manual-only next steps.

Usage:
  python3 ecs_remote_connection_triage.py --region-id cn-hangzhou \
      (--instance-id i-... | --public-ip 1.2.3.4) [--egress-ip ...] \
      [--port N] [--protocol auto|ssh|rdp] [--client-tool xshell] \
      [--error-text "..."] [--console-ok] [--intrusion-suspect] \
      [--skip-metrics] [--json]
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import ipaddress
import json
import re
import sys
from typing import Any, Optional

import _cli
from _constants import (
    API_VERSIONS,
    CMS_METRICS_DEFAULT,
    CMS_NAMESPACE,
    CPU_SATURATION_PCT,
    DEFAULT_TIMEOUT,
    ECS_PRODUCT,
    ERROR_SIGNATURES,
    GUEST_SELFCHECK_COMMANDS,
    HANDOFFS,
    HARDENING_CHECKLIST,
    INTRUSION_PATTERNS,
    LOCAL_SELFCHECK_COMMANDS,
    MAX_SG_GROUPS,
    OS_PROTOCOL,
    RDP_DEFAULT_PORT,
    RISK_NOTICES,
    SSH_DEFAULT_PORT,
    SSH_PORTS_HINT,
    TOOL_PROTOCOL_HINTS,
    VERDICTS,
)

_REGION_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_INSTANCE_ID_RE = re.compile(r"^i-[a-z0-9-]{6,64}$")


# ---------------------------------------------------------------------------
# Pure helpers (boundary-asserted below): validation + decision logic
# ---------------------------------------------------------------------------

def note_gap(gaps: list, step: str, err: BaseException) -> None:
    """Record a degradation: stderr [WARN] line + structured gap entry."""
    code = getattr(err, "code", "") or type(err).__name__
    msg = str(err)
    gaps.append({"step": step, "code": code, "message": msg[:300]})
    print(f"[WARN] {step} failed: {code}: {msg[:300]}", file=sys.stderr)


def valid_region(value: str) -> bool:
    return bool(_REGION_RE.match(value or ""))


def valid_instance_id(value: str) -> bool:
    return bool(_INSTANCE_ID_RE.match(value or ""))


def valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def valid_port(value: int) -> bool:
    return 1 <= value <= 65535


def port_in_range(port: int, port_range: str) -> bool:
    """Match a target port against an ECS rule PortRange like '22/22',
    '1024/2048', '-1/-1' (all) or '0/65535'."""
    pr = (port_range or "").strip()
    if pr in ("-1/-1", "0/65535", ""):
        return True
    try:
        lo_s, _, hi_s = pr.partition("/")
        lo, hi = int(lo_s), int(hi_s)
    except (ValueError, TypeError):
        return False
    return lo <= port <= hi


def cidr_covers(cidr: str, ip: str) -> bool:
    """True when `ip` falls inside `cidr` (v4/v6 aware); bad input -> False."""
    try:
        if "/" in cidr:
            net = ipaddress.ip_network(cidr, strict=False)
            addr = ipaddress.ip_address(ip)
            return addr.version == net.version and addr in net
        return ipaddress.ip_address(cidr) == ipaddress.ip_address(ip)
    except ValueError:
        return False


def rule_priority(rule: dict) -> int:
    try:
        return int(str(rule.get("Priority") or "99"))
    except (ValueError, TypeError):
        return 99


def match_signatures(text: str) -> list:
    """Return the signature entries whose patterns occur in `text`."""
    low = (text or "").lower()
    if not low:
        return []
    return [sig for sig in ERROR_SIGNATURES
            if any(p.lower() in low for p in sig["patterns"])]


def looks_intrusion(text: str) -> bool:
    low = (text or "").lower()
    return any(p.lower() in low for p in INTRUSION_PATTERNS)


def pick_verdict(facts: dict) -> str:
    """Single decision leaf from collected facts; pure and order-fixed.

    Order follows the triage tree: intrusion > ownership > state > protocol
    mismatch > security group > public path > saturation > error-string
    branches > overdue pattern > insufficient.
    """
    if facts.get("intrusion"):
        return "SECURITY_SUSPECT"
    if facts.get("instance_found") is False:
        # A lookup that ERRORED (permissions/credentials) is not the same as
        # a clean empty result: only the latter proves "not this asset".
        return "INSUFFICIENT" if facts.get("lookup_failed") else "OUT_OF_SCOPE_IP"
    if facts.get("instance_running") is False:
        return "INSTANCE_NOT_RUNNING"
    if facts.get("protocol_mismatch"):
        return "PROTOCOL_MISMATCH"
    if facts.get("sg_port_closed"):
        return "SG_PORT_CLOSED"
    if facts.get("sg_source_mismatch"):
        return "SG_SOURCE_MISMATCH"
    if facts.get("no_public_path"):
        return "NO_PUBLIC_PATH"
    if facts.get("saturated"):
        return "SATURATION_HANG"
    sig_ids = facts.get("signature_ids") or ()
    if "credential" in sig_ids or "pam" in sig_ids:
        return "CREDENTIAL"
    if ("tool-local" in sig_ids or "keepalive" in sig_ids
            or "host-key" in sig_ids):
        return "TOOL_LOCAL"
    if ("resource-limit" in sig_ids or "sshd-config" in sig_ids
            or "file-permission" in sig_ids):
        return "GUEST_LIKELY"
    if facts.get("console_ok") and facts.get("cloud_path_open"):
        return "OVERDUE_PATTERN"
    if "refused-or-service" in sig_ids or "silent-drop" in sig_ids:
        return "GUEST_LIKELY" if facts.get("cloud_path_open") else "INSUFFICIENT"
    if facts.get("cloud_path_open") and facts.get("instance_running"):
        return "GUEST_LIKELY"
    return "INSUFFICIENT"


# Inline boundary assertions for the pure helpers (normal / boundary /
# invalid inputs) -- a broken guard would silently change verdicts.
assert port_in_range(22, "22/22") and port_in_range(10022, "10022/10022")
assert port_in_range(80, "0/65535") and port_in_range(80, "-1/-1")
assert not port_in_range(22, "23/65535") and not port_in_range(22, "junk")
assert cidr_covers("218.207.140.109/32", "218.207.140.109")
assert not cidr_covers("218.207.140.109/32", "58.19.1.99")
assert cidr_covers("0.0.0.0/0", "8.8.8.8")
assert not cidr_covers("bad-cidr", "8.8.8.8")
assert not cidr_covers("10.0.0.0/8", "fe80::1")
assert rule_priority({"Priority": "1"}) == 1 and rule_priority({}) == 99
assert rule_priority({"Priority": "abc"}) == 99
assert not valid_region("CN_Hangzhou") and valid_region("cn-hangzhou")
assert not valid_instance_id("i-bad id!") and valid_instance_id("i-bp1abcdefg2")
assert not valid_ip("300.1.1.1") and valid_ip("101.37.35.34")
assert not valid_port(0) and not valid_port(70000) and valid_port(10022)
assert match_signatures(
    "Could not connect to 39.108.190.9 (port 22): Connection failed"
)[0]["id"] == "protocol-mismatch"
assert match_signatures("SSH connection timed out")[0]["id"] == "silent-drop"
assert match_signatures("") == []
assert looks_intrusion("we were attacked, a stranger ip logged in")
assert not looks_intrusion("simple timeout")
assert pick_verdict({"instance_found": False, "lookup_failed": False}) == \
    "OUT_OF_SCOPE_IP"
assert pick_verdict({"instance_found": False, "lookup_failed": True}) == \
    "INSUFFICIENT"
assert pick_verdict({"instance_found": True, "instance_running": False}) == \
    "INSTANCE_NOT_RUNNING"
assert pick_verdict({"instance_found": True, "instance_running": True,
                     "sg_port_closed": True}) == "SG_PORT_CLOSED"
assert pick_verdict({"instance_found": True, "instance_running": True,
                     "sg_source_mismatch": True}) == "SG_SOURCE_MISMATCH"
assert pick_verdict({"intrusion": True, "instance_found": False}) == \
    "SECURITY_SUSPECT"
assert pick_verdict({}) == "INSUFFICIENT"

# ---------------------------------------------------------------------------
# Evidence collectors (each degrades independently, recording a [WARN])
# ---------------------------------------------------------------------------


def resolve_instance(region: str, instance_id: Optional[str],
                     public_ip: Optional[str], profile: Optional[str],
                     gaps: list, timeout: int = DEFAULT_TIMEOUT) -> tuple:
    """Locate the instance by id, then by public IP, then by EIP (all the
    same read-only DescribeInstances action). Returns (instance | None,
    lookup_failed): lookup_failed is True only when EVERY query errored."""
    attempts = []
    if instance_id:
        attempts.append(("by-instance-id",
                         {"InstanceIds": json.dumps([instance_id])}))
    if public_ip:
        attempts.append(("by-public-ip", {"PublicIpAddresses": public_ip}))
        attempts.append(("by-eip", {"EipAddresses": public_ip}))
    if not attempts:
        return None, True
    calls_failed = 0
    for label, params in attempts:
        params = dict(params)
        params["RegionId"] = region
        try:
            body = _cli.call(ECS_PRODUCT, "DescribeInstances", params,
                             region=region, profile=profile, timeout=timeout)
        except _cli.CliError as e:
            calls_failed += 1
            note_gap(gaps, f"DescribeInstances {label}", e)
            continue
        items = _cli.dig(body, "Instances", "Instance") or []
        if items:
            return items[0], False
    return None, calls_failed == len(attempts)


def security_group_evidence(region: str, groups: list, port: int,
                            protocol: str, egress_ip: Optional[str],
                            profile: Optional[str], gaps: list,
                            timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Enumerate ingress rules matching the target port on every bound
    security group (first-match semantics: ascending Priority, Drop before
    Accept at equal priority)."""
    result = {"checked": [], "accept_rules": [], "drop_hit": False,
              "covers_egress": None}
    proto_wanted = "tcp"
    for sg_id in groups[:MAX_SG_GROUPS]:
        try:
            body = _cli.call(ECS_PRODUCT, "DescribeSecurityGroupAttribute",
                             {"RegionId": region, "SecurityGroupId": sg_id},
                             region=region, profile=profile, timeout=timeout)
        except _cli.CliError as e:
            note_gap(gaps, f"DescribeSecurityGroupAttribute {sg_id}", e)
            continue
        result["checked"].append(sg_id)
        rules = _cli.dig(body, "Permissions", "Permission") or []
        ordered = sorted(rules, key=lambda r: (rule_priority(r),
                                               0 if str(r.get("Policy", ""))
                                               .lower() == "drop" else 1))
        for rule in ordered:
            direction = str(rule.get("Direction") or "").lower()
            if direction and direction != "ingress":
                continue
            rproto = str(rule.get("IpProtocol") or "").lower()
            if rproto not in (proto_wanted, "all", "-1"):
                continue
            if not port_in_range(port, str(rule.get("PortRange") or "")):
                continue
            entry = {
                "sg": sg_id,
                "policy": str(rule.get("Policy") or "?"),
                "priority": str(rule.get("Priority") or "?"),
                "port_range": str(rule.get("PortRange") or "?"),
                "protocol": rproto,
                "source": str(rule.get("SourceCidrIp")
                              or rule.get("Ipv6CidrIp")
                              or rule.get("SourceGroupId") or "-"),
            }
            if entry["policy"].lower() == "accept":
                result["accept_rules"].append(entry)
            else:
                result["drop_hit"] = True
    if egress_ip and result["accept_rules"]:
        result["covers_egress"] = any(
            cidr_covers(r["source"], egress_ip)
            for r in result["accept_rules"])
    return result


def vnc_link(region: str, instance_id: str, profile: Optional[str],
             gaps: list, timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
    try:
        body = _cli.call(ECS_PRODUCT, "DescribeInstanceVncUrl",
                         {"RegionId": region, "InstanceId": instance_id},
                         region=region, profile=profile, timeout=timeout)
        return str(_cli.dig(body, "VncUrl") or "") or None
    except _cli.CliError as e:
        note_gap(gaps, "DescribeInstanceVncUrl", e)
        return None


def cloud_assistant_state(region: str, instance_id: str,
                          profile: Optional[str], gaps: list,
                          timeout: int = DEFAULT_TIMEOUT) -> str:
    try:
        body = _cli.call(ECS_PRODUCT, "DescribeCloudAssistantStatus",
                         {"RegionId": region, "InstanceId.1": instance_id},
                         region=region, profile=profile, timeout=timeout)
        items = _cli.dig(body, "InstanceCloudAssistantStatusSet",
                         "InstanceCloudAssistantStatus") or []
        for item in items:
            if str(item.get("InstanceId") or "") not in ("", instance_id):
                continue
            status = str(item.get("CloudAssistantStatus", "")).lower()
            return "online" if status == "true" else "offline"
        return "unknown"
    except _cli.CliError as e:
        note_gap(gaps, "DescribeCloudAssistantStatus", e)
        return "unknown"


def latest_cpu_percent(region: str, instance_id: str, profile: Optional[str],
                       gaps: list,
                       timeout: int = DEFAULT_TIMEOUT) -> Optional[float]:
    """Latest value of the default verified metric set (cpu_total only);
    None on any gap. Metric names beyond the verified set are never
    invented (see _constants.CMS_METRICS_DEFAULT)."""
    values = []
    for metric in CMS_METRICS_DEFAULT:
        params = {
            "Namespace": CMS_NAMESPACE,
            "MetricName": metric,
            "Dimensions": json.dumps([{"instanceId": instance_id}]),
        }
        try:
            body = _cli.call("cms", "DescribeMetricLast", params,
                             region=region, profile=profile, timeout=timeout)
        except _cli.CliError as e:
            note_gap(gaps, f"DescribeMetricLast {metric}", e)
            continue
        raw = _cli.dig(body, "Datapoints")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                raw = None
        if not isinstance(raw, list) or not raw:
            continue
        try:
            latest = max(raw, key=lambda d: int(d.get("timestamp") or 0))
        except (TypeError, ValueError):
            continue
        for key in ("Average", "Maximum"):
            try:
                values.append(float(latest.get(key)))
                break
            except (TypeError, ValueError):
                continue
    return max(values) if values else None


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def render_sections(data: dict) -> list:
    """Build the ordered human-readable evidence/guidance sections."""
    lines = []
    facts = data["facts"]
    inst = data["instance"] or {}
    lines.append("-- Evidence --")
    lines.append(f"1. Asset ownership : account uid {data['uid'] or 'N/A'} | "
                 f"target {data.get('queried_id', 'N/A')} in {data['region']} "
                 f"| resolved instance: {facts.get('instance_found')}")
    lines.append(f"2. Instance state  : {inst.get('Status', 'N/A')} | "
                 f"OS type: {inst.get('OSType', 'N/A')} "
                 f"({inst.get('OSName', 'N/A')})")
    pub = _cli.dig(inst, "PublicIpAddress", "IpAddress") or []
    eip = _cli.dig(inst, "EipAddress", "IpAddress") or ""
    lines.append(f"3. Public path     : public IP {', '.join(pub) or 'none'} "
                 f"| EIP {eip or 'none'} | bandwidth charge type "
                 f"{inst.get('InternetChargeType', 'N/A')}")
    lines.append(f"4. Protocol routing: {data['protocol']} on port "
                 f"{data['port']} ({data['port_source']}); {SSH_PORTS_HINT}")
    sg = data["sg"]
    if sg["checked"]:
        lines.append(f"5. Security group  : checked {', '.join(sg['checked'])}")
        if sg["accept_rules"]:
            for r in sg["accept_rules"]:
                lines.append(f"     allow {r['protocol']} {r['port_range']} "
                             f"from {r['source']} (sg {r['sg']}, "
                             f"prio {r['priority']})")
        else:
            lines.append("     NO ingress allow rule covers the target port")
        if sg["covers_egress"] is True:
            lines.append("     customer egress IP IS covered by an allow rule")
        elif sg["covers_egress"] is False:
            lines.append("     customer egress IP is NOT covered by any "
                         "allow rule")
    else:
        lines.append("5. Security group  : N/A (not collected)")
    lines.append(f"6. VNC fallback    : {data['vnc'] or 'N/A'}")
    lines.append(f"7. Cloud Assistant : {data['ca_state']} "
                 "(offline means Workbench/session channels are unavailable; "
                 "use VNC)")
    cpu = data["cpu"]
    sat = " (saturation signal)" if facts.get("saturated") else ""
    cpu_txt = f"{cpu:.1f}%" if cpu is not None else "N/A"
    lines.append(f"8. Monitoring      : latest cpu_total = {cpu_txt}{sat}")
    if data["signatures"]:
        lines.append("-- Error signature match --")
        for sig in data["signatures"]:
            lines.append(f"  [{sig['id']}] {sig['branch']}")
    lines.append("-- First diagnosis --")
    v = VERDICTS[data["verdict"]]
    lines.append(f"VERDICT: {data['verdict']} - {v[0]}")
    lines.append(f"  {v[1]}")
    lines.append("-- Next actions (manual only; this skill changes nothing) --")
    lines.append(f"  {v[2]}")
    for sig in data["signatures"]:
        lines.append(f"  [{sig['id']}] {sig['guidance']}")
    if data["verdict"] in ("GUEST_LIKELY", "INSUFFICIENT", "TOOL_LOCAL"):
        lines.append("  Customer-run checks (run inside your own VNC/"
                     "Workbench session or on your own computer, then paste "
                     "the results back):")
        for cmd, look in LOCAL_SELFCHECK_COMMANDS:
            lines.append(f"    [local] {cmd}  ->  {look}")
        for cmd, look in GUEST_SELFCHECK_COMMANDS:
            lines.append(f"    [guest] {cmd}  ->  {look}")
    if data["verdict"] == "TOOL_LOCAL":
        lines.append("  Keepalive template for idle drops: server-side "
                     "ClientAliveInterval 60 / ClientAliveCountMax 10 (the "
                     "customer restarts the SSH service afterwards for it "
                     "to take effect), client-side ServerAliveInterval 60 / "
                     "ServerAliveCountMax 10, and check the idle timeout of "
                     "any intermediate NAT/firewall.")
    for key in sorted(data["notices"]):
        lines.append(f"  Notice [{key}]: {RISK_NOTICES[key]}")
    if data["handoffs"]:
        lines.append("-- Handoff --")
        for area in data["handoffs"]:
            target, why = HANDOFFS[area]
            lines.append(f"  {why} -> {target}")
    if data["verdict"] == "SECURITY_SUSPECT":
        lines.append("  Hardening checklist (manual, in order): "
                     + "; ".join(HARDENING_CHECKLIST))
    if data["gaps"]:
        lines.append("-- Graceful degradation log --")
        for g in data["gaps"]:
            lines.append(f"  [WARN] {g['step']}: {g['code']}: {g['message']}")
    return lines


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ecs_remote_connection_triage.py",
        description=("Read-only triage entry for ECS remote-connection "
                     "failures (protocol unspecified). Never changes any "
                     "resource; guest checks are guidance for the customer "
                     "to run."),
    )
    p.add_argument("--region-id", required=True,
                   help="Alibaba Cloud region id, e.g. cn-hangzhou")
    p.add_argument("--instance-id", default=None,
                   help="ECS instance id (i-...). One of --instance-id/--public-ip.")
    p.add_argument("--public-ip", default=None,
                   help="Public IP / EIP to resolve (when only an IP is known)")
    p.add_argument("--egress-ip", default=None,
                   help="Customer local egress public IP (curl cip.cc)")
    p.add_argument("--port", type=int, default=None,
                   help="Target port; defaults from OS type (22/3389)")
    p.add_argument("--protocol", choices=("auto", "ssh", "rdp"), default="auto")
    p.add_argument("--client-tool", default=None,
                   help="Client tool name (xshell/winscp/putty/...)")
    p.add_argument("--error-text", default=None,
                   help="Error string quoted by the customer")
    p.add_argument("--console-ok", action="store_true",
                   help="Customer confirmed console/VNC login works (decisive "
                        "fork signal)")
    p.add_argument("--intrusion-suspect", action="store_true",
                   help="Customer suspects an attack or an unknown login; "
                        "forces the security handoff route regardless of the "
                        "language of --error-text")
    p.add_argument("--skip-metrics", action="store_true",
                   help="Skip the CloudMonitor saturation pre-screen")
    p.add_argument("--json", action="store_true", help="Machine-readable output")
    p.add_argument("--profile", default=None,
                   help="Optional aliyun CLI credential profile name")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                   help=f"Per-call CLI timeout seconds (default {DEFAULT_TIMEOUT})")
    return p


def main(argv: Optional[list] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    gaps: list = []

    if not valid_region(args.region_id):
        print(f"[ERROR] invalid region id: {args.region_id!r}", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: re-run with a valid --region-id (e.g. cn-hangzhou)")
        return 1
    if not args.instance_id and not args.public_ip:
        print("[ERROR] one of --instance-id / --public-ip is required",
              file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: ask the customer for the instance id or the "
              "public IP plus the region, then re-run")
        return 1
    if args.instance_id and not valid_instance_id(args.instance_id):
        print(f"[ERROR] invalid instance id: {args.instance_id!r}",
              file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: confirm the exact i-... instance id with the "
              "customer (and its region), then re-run")
        return 1
    if args.public_ip and not valid_ip(args.public_ip):
        print(f"[ERROR] invalid IP address: {args.public_ip!r}", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: confirm the public IP / EIP quoted by the "
              "customer, then re-run")
        return 1
    if args.egress_ip and not valid_ip(args.egress_ip):
        note_gap(gaps, "egress-ip validation",
                 ValueError(f"discarded invalid --egress-ip {args.egress_ip!r}"))
        args.egress_ip = None
    if args.port is not None and not valid_port(args.port):
        print("[ERROR] --port must be 1..65535", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: re-run with a valid --port")
        return 1

    _cli.check_cli_available()

    # -- S1 identity --------------------------------------------------------
    uid = ""
    try:
        uid = _cli.get_caller_identity(profile=args.profile,
                                       timeout=args.timeout)["uid"]
    except _cli.CliError as e:
        note_gap(gaps, "GetCallerIdentity", e)

    # -- S1 asset ownership / instance resolution ----------------------------
    inst, lookup_failed = resolve_instance(args.region_id, args.instance_id,
                                           args.public_ip, args.profile, gaps,
                                           timeout=args.timeout)
    facts: dict[str, Any] = {
        "instance_found": inst is not None,
        "lookup_failed": lookup_failed,
        "intrusion": bool(args.intrusion_suspect) or looks_intrusion(
            args.error_text or ""),
        "signature_ids": tuple(s["id"] for s in
                               match_signatures(args.error_text or "")),
        "console_ok": bool(args.console_ok),
    }
    signatures = match_signatures(args.error_text or "")

    if inst is None:
        data = {
            "region": args.region_id, "uid": uid,
            "queried_id": args.instance_id or args.public_ip,
            "instance": {}, "protocol": "N/A", "port": args.port or "N/A",
            "port_source": "N/A",
            "sg": {"checked": [], "accept_rules": [], "covers_egress": None},
            "vnc": None, "ca_state": "skipped", "cpu": None,
            "signatures": signatures,
            "facts": facts, "notices": set(), "handoffs": [], "gaps": gaps,
        }
        data["verdict"] = pick_verdict(facts)
        if facts["instance_found"] is False and lookup_failed:
            data["verdict"] = "INSUFFICIENT"
        return emit(data, args, failed=True)

    instance_id = str(inst.get("InstanceId") or args.instance_id or "")
    status = str(inst.get("Status") or "")
    os_type = str(inst.get("OSType") or "").lower()
    running = status == "Running"
    facts["instance_running"] = running

    # -- S2 protocol routing --------------------------------------------------
    default_proto = OS_PROTOCOL.get(os_type, ("SSH", SSH_DEFAULT_PORT))[0]
    protocol = default_proto if args.protocol == "auto" else args.protocol.upper()
    port = args.port if args.port else (
        SSH_DEFAULT_PORT if protocol == "SSH" else RDP_DEFAULT_PORT)
    port_source = "customer-specified" if args.port else \
        f"auto-defaulted from OS type ({os_type or 'unknown'})"
    tool = (args.client_tool or "").strip().lower()
    tool_proto = TOOL_PROTOCOL_HINTS.get(tool)
    facts["protocol_mismatch"] = bool(
        running and tool_proto and os_type and tool_proto != protocol)

    # -- S3 security group evidence ---------------------------------------------
    groups = _cli.dig(inst, "SecurityGroupIds", "SecurityGroupId") or []
    pub = _cli.dig(inst, "PublicIpAddress", "IpAddress") or []
    eip = str(_cli.dig(inst, "EipAddress", "IpAddress") or "")
    facts["no_public_path"] = running and not pub and not eip
    sg = {"checked": [], "accept_rules": [], "covers_egress": None}
    if running and groups:
        sg = security_group_evidence(args.region_id, groups, port, protocol,
                                     args.egress_ip, args.profile, gaps,
                                     timeout=args.timeout)
    if sg["accept_rules"]:
        if sg["covers_egress"] is False:
            facts["sg_source_mismatch"] = True
        else:
            facts["cloud_path_open"] = True
    elif sg["checked"]:
        facts["sg_port_closed"] = True

    # -- S4 channels ------------------------------------------------------------
    vnc = vnc_link(args.region_id, instance_id, args.profile,
                   gaps, timeout=args.timeout) if running else None
    ca_state = cloud_assistant_state(args.region_id, instance_id,
                                     args.profile, gaps,
                                     timeout=args.timeout)

    # -- S5 saturation pre-screen -------------------------------------------------
    cpu = None
    facts["saturated"] = False
    if running and not args.skip_metrics:
        cpu = latest_cpu_percent(args.region_id, instance_id, args.profile,
                                 gaps, timeout=args.timeout)
        facts["saturated"] = cpu is not None and cpu >= CPU_SATURATION_PCT

    verdict = pick_verdict(facts)
    notices = set()
    if verdict in ("SATURATION_HANG", "INSTANCE_NOT_RUNNING"):
        notices.update(("restart", "stopping", "snapshot"))
    if verdict == "GUEST_LIKELY":
        notices.update(("stopping",))
    if verdict == "CREDENTIAL":
        notices.add("credential")
    if verdict == "OVERDUE_PATTERN":
        notices.add("bandwidth")
    handoffs = []
    if verdict == "SATURATION_HANG":
        handoffs.append("disk-io")
    if verdict == "INSTANCE_NOT_RUNNING" and status == "Stopping":
        handoffs.append("instance-state")
    if verdict == "SECURITY_SUSPECT":
        handoffs.append("security")
    if verdict == "GUEST_LIKELY" and any(
            kw in (args.error_text or "").lower()
            for kw in ("inode", "disk full", "no space")):
        handoffs.append("disk-capacity")

    data = {
        "region": args.region_id, "uid": uid,
        "queried_id": args.instance_id or args.public_ip,
        "instance": inst, "protocol": protocol, "port": port,
        "port_source": port_source, "sg": sg, "vnc": vnc,
        "ca_state": ca_state, "cpu": cpu, "signatures": signatures,
        "facts": facts, "verdict": verdict, "notices": notices,
        "handoffs": handoffs, "gaps": gaps,
    }
    return emit(data, args, failed=False)


def emit(data: dict, args: Any, failed: bool) -> int:
    """Print the report (human or --json) plus the STATUS/NEXT_ACTION lines.

    STATUS rules (contract, SKILL.md 'Available Scripts'):
      OK       - full evidence, no gaps
      DEGRADED - a conclusion was produced but one or more evidence calls
                 failed (recorded in the degradation log / gaps list)
      FAIL     - nothing usable at all (identity AND instance evidence
                 both unavailable)
    """
    if failed and not data["uid"]:
        status = "FAIL"
    elif data["gaps"] or not data["uid"]:
        status = "DEGRADED"
    else:
        status = "OK"
    verdict = data["verdict"]
    next_action = VERDICTS[verdict][2]
    summary = (
        f"Collected read-only evidence for remote-connection triage of "
        f"{data.get('queried_id', 'N/A')} in {data['region']} "
        f"(account uid {data['uid'] or 'N/A'}); protocol {data['protocol']} "
        f"port {data['port']}; verdict {verdict}.")

    if args.json:
        payload = {
            "summary": summary,
            "status": status,
            "next_action": next_action,
            "api_versions": API_VERSIONS,
            "verdict": verdict,
            "verdict_detail": VERDICTS[verdict],
            "region": data["region"],
            "uid": data["uid"] or None,
            "instance": {
                "instance_id": _cli.dig(data["instance"], "InstanceId"),
                "status": _cli.dig(data["instance"], "Status"),
                "os_type": _cli.dig(data["instance"], "OSType"),
                "public_ips": _cli.dig(data["instance"], "PublicIpAddress",
                                       "IpAddress"),
                "eip": _cli.dig(data["instance"], "EipAddress", "IpAddress"),
                "security_group_ids": _cli.dig(data["instance"],
                                               "SecurityGroupIds",
                                               "SecurityGroupId"),
            } if data["instance"] else None,
            "routing": {"protocol": data["protocol"], "port": data["port"],
                        "port_source": data["port_source"]},
            "security_group": data["sg"],
            "vnc_url": data["vnc"],
            "cloud_assistant": data["ca_state"],
            "cpu_latest_percent": data["cpu"],
            "matched_signatures": [s["id"] for s in data["signatures"]],
            "notices": sorted(data["notices"]),
            "handoffs": data["handoffs"],
            "degradations": data["gaps"],
            "guidance_guest_checks": [
                {"command": c, "look_for": l}
                for c, l in GUEST_SELFCHECK_COMMANDS],
        }
        print(json.dumps(payload, indent=2, default=str))
    else:
        print("=" * 62)
        print(" ECS REMOTE CONNECTION TRIAGE REPORT (read-only)")
        print("=" * 62)
        print(summary)
        for line in render_sections(data):
            print(line)
    print(f"\nSTATUS: {status}")
    print(f"NEXT_ACTION: {next_action}")
    return 0 if status in ("OK", "DEGRADED") else 1


if __name__ == "__main__":
    sys.exit(main())
