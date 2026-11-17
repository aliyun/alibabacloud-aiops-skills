#!/usr/bin/env python3
"""
vpc_connectivity_check.py -- single entry point for the
area:vpc-connectivity-check skill
=============================================
SECURITY: This skill is strictly READ-ONLY. Every cloud query goes through
_cli.call(), which enforces a hard whitelist of read-only actions
(DescribeInstances / DescribeInstanceStatus / DescribeAvailableResource /
DescribeSecurityGroupAttribute / DescribeEipAddresses / GetCallerIdentity),
passes parameters as an argument list (never shell=True), and carries a
per-call timeout. This script never mutates cloud resources, never runs
commands inside a guest OS, and never reads, prints or passes any credential
material -- authentication is resolved by the aliyun CLI default credential
chain.

Modes (--check):
  pair         Same-VPC / vSwitch / security-group binding comparison for two
               instances, the inbound RULE CONTENT of the target instance's
               security groups read back with DescribeSecurityGroupAttribute
               and compared rule by rule (direction, protocol, port range,
               authorization object, policy, priority), optional vSwitch
               CIDR-overlap verdict, optional DescribeAvailableResource context
               for the source zone.
  transfer     Cross-account instance-transfer pre-check: source instance
               region / zone / VPC facts, zone consistency of the target
               vSwitch, zone availability for the instance type, and the
               InvalidDependence.GrantAccess dependency guidance. Pass
               --same-account for a vSwitch move inside one account, where
               the destination VPC must equal the instance's current VPC.
  ip-inventory
               Paginated private-IP inventory of a region, optionally
               filtered by a CIDR range (10.19.0.0/16 style).
  public-path  Public-side context for the "intranet works, internet does
               not" branch: instance status, public IP / EIP presence and
               EIP binding state (DescribeEipAddresses).
  cidr-only    Pure local check: overlap relation between two CIDR blocks
               the customer read from the console (no API call, no guest).

Output contract:
  --json   one machine-consumable JSON document;
  default  human-readable report with the same findings;
  both end with exactly one `STATUS: OK|DEGRADED|FAIL` line and one
  `NEXT_ACTION: ...` line.
Exit codes: 0 = OK or DEGRADED (usable conclusion), 1 = FAIL (no usable
conclusion), 2 = argparse usage error.

Examples:
  python3 vpc_connectivity_check.py --check pair --region-id cn-hangzhou \
      --instance-id-a i-bp1example0b79486034 \
      --instance-id-b i-bp1example80057dc0bd \
      --cidr-a 172.26.0.0/18 --cidr-b 172.26.32.0/20
  python3 vpc_connectivity_check.py --check transfer --region-id cn-hangzhou \
      --instance-id i-bp1example0b79486034 \
      --target-zone-id cn-hangzhou-h
  python3 vpc_connectivity_check.py --check ip-inventory \
      --region-id cn-hangzhou --cidr-filter 10.19.0.0/16
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
    CIDR_VERDICTS,
    DEFAULT_REGION,
    ERROR_DISPOSITIONS,
    GUEST_BOUNDARY_ITEMS,
    HANDOFFS,
    MANUAL_STEPS,
    SG_ACCEPT_POLICIES,
    SG_DROP_POLICIES,
    SG_MISCONCEPTION_FIXES,
    SG_PROTOCOL_ALL,
    SG_RULE_VERDICTS,
    SG_RULE_VERIFY_DIMENSIONS,
    SKILL_NAME,
    TRANSFER_CONSISTENCY_CONDITIONS,
    TRANSFER_EXTRA_NOTES,
)

_ID_RE = re.compile(r"^i-[A-Za-z0-9-]+$")
_REGION_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_VSW_RE = re.compile(r"^vsw-[A-Za-z0-9-]+$")
_SG_RE = re.compile(r"^sg-[A-Za-z0-9-]+$")
_ZONE_RE = re.compile(r"^[a-z][a-z0-9-]*$")

_MODES = ("pair", "transfer", "ip-inventory", "public-path", "cidr-only")

_API_CALLS: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Small tolerant extraction helpers (never fabricate missing fields)
# ---------------------------------------------------------------------------

def _dig(obj: Any, path: list[str]) -> Any:
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _extract_list(body: Any, container: str, item: str) -> list[dict]:
    """Return body[container][item] or body[container] when already a list."""
    if not isinstance(body, dict):
        return []
    node = body.get(container)
    if isinstance(node, dict):
        inner = node.get(item)
        return inner if isinstance(inner, list) else []
    if isinstance(node, list):
        return node
    return []


def _call(product: str, action: str, params: dict[str, Any],
          region: str, profile: Optional[str]) -> dict[str, Any]:
    """Whitelisted CLI call with evidence logging."""
    _API_CALLS.append({"product": product, "action": action,
                       "params": dict(params)})
    return _cli.call(product, action, params, region=region, profile=profile)


def _warn(errors: list[dict[str, str]], api: str, exc: _cli.CliError) -> None:
    entry = {"api": api,
             "code": getattr(exc, "code", "") or "CliError",
             "message": str(exc)[:400]}
    errors.append(entry)
    print(f"[WARN] {api} -> {entry['code']}: {entry['message']}",
          file=sys.stderr)


# ---------------------------------------------------------------------------
# Pure local functions (unit-asserted below)
# ---------------------------------------------------------------------------

def cidr_relation(cidr_a: str, cidr_b: str) -> str:
    """Deterministic overlap relation between two CIDR blocks."""
    a = ipaddress.ip_network(cidr_a, strict=False)
    b = ipaddress.ip_network(cidr_b, strict=False)
    if a.version != b.version:
        return "disjoint"
    if a == b:
        return "identical"
    if a.subnet_of(b):
        return "a-within-b"
    if b.subnet_of(a):
        return "b-within-a"
    return "partial-overlap" if a.overlaps(b) else "disjoint"


def ip_in_cidr(ip: str, cidr: str) -> bool:
    try:
        return ipaddress.ip_address(ip) in ipaddress.ip_network(
            cidr, strict=False)
    except ValueError:
        return False


def sg_intersection(sgs_a: list[str], sgs_b: list[str]) -> list[str]:
    return sorted(set(sgs_a) & set(sgs_b))


def port_in_range(port: int, port_range: str) -> bool:
    """True when ``port`` sits inside an ECS ``start/end`` port range.

    The API expresses "every port" as ``-1/-1`` (and some protocol-level rules
    as a bare ``-1``). An unparsable range is NOT treated as a match: a rule
    this checker cannot read must never be reported as authorizing traffic.
    """
    text = (port_range or "").strip()
    if not text:
        return False
    if text in ("-1/-1", "-1"):
        return True
    start, _, end = text.partition("/")
    try:
        low = int(start)
        high = int(end) if end else low
    except ValueError:
        return False
    if low < 0 or high < 0:
        return True
    if high < low:
        low, high = high, low
    return low <= port <= high


def protocol_matches(rule_protocol: str, wanted: str) -> bool:
    """An ALL rule covers every protocol; anything else must match exactly."""
    rule = (rule_protocol or "").strip().lower()
    if rule in SG_PROTOCOL_ALL:
        return True
    return rule == (wanted or "").strip().lower()


def rule_source_matches(source_cidr: str, source_group: str, source_ip: str) -> bool:
    """True when the rule's authorization object covers the source address.

    A group-to-group authorization (SourceGroupId) is not address-comparable,
    so it never counts as a confirmed match; the caller reports it separately
    instead of guessing its membership.
    """
    if source_group:
        return False
    return bool(source_cidr) and ip_in_cidr(source_ip, source_cidr)


def evaluate_ingress_access(rules: list[dict], source_ip: str, port: Optional[int],
                            protocol: str) -> dict[str, Any]:
    """Compare every inbound rule with one flow and return a verdict dict.

    ``rules`` are raw ``Permissions.Permission`` rows from
    DescribeSecurityGroupAttribute. Nothing is inferred: the returned verdict
    names the concrete rule (raw port range, source, policy, priority) that
    decided it, or says that no rule matched.
    """
    accepts: list[dict] = []
    drops: list[dict] = []
    group_rules: list[dict] = []
    for rule in rules or []:
        if not isinstance(rule, dict):
            continue
        direction = str(rule.get("Direction") or "ingress").strip().lower()
        if direction not in ("ingress", "all"):
            continue
        if not protocol_matches(str(rule.get("IpProtocol") or ""), protocol):
            continue
        if port is not None and not port_in_range(port, str(rule.get("PortRange") or "")):
            continue
        source_cidr = str(rule.get("SourceCidrIp") or "")
        source_group = str(rule.get("SourceGroupId") or "")
        if not rule_source_matches(source_cidr, source_group, source_ip):
            if source_group and port is not None:
                group_rules.append(rule)
            continue
        policy = str(rule.get("Policy") or "").strip().lower()
        try:
            priority = int(rule.get("Priority") or 1)
        except (TypeError, ValueError):
            priority = 1
        entry = {
            "rule_id": str(rule.get("SecurityGroupRuleId") or "N/A"),
            "direction": direction,
            "protocol": str(rule.get("IpProtocol") or "N/A"),
            "port_range": str(rule.get("PortRange") or "N/A"),
            "source": source_cidr or source_group or "N/A",
            "policy": policy or "N/A",
            "priority": priority,
        }
        if policy in SG_ACCEPT_POLICIES:
            accepts.append(entry)
        elif policy in SG_DROP_POLICIES:
            drops.append(entry)

    accepts.sort(key=lambda r: r["priority"])
    drops.sort(key=lambda r: r["priority"])
    allow = accepts[0] if accepts else None
    deny = drops[0] if drops else None
    if port is None:
        verdict = "no-port-given"
    elif deny is not None and (allow is None or deny["priority"] <= allow["priority"]):
        verdict = "shadowed-by-deny"
    elif allow is not None:
        verdict = "allowed"
    else:
        verdict = "no-matching-rule"
    return {
        "verdict": verdict,
        "allow": allow,
        "deny": deny,
        "group_authorized": group_rules[:3],
    }


# Boundary assertions for the pure decision functions (KB layer-1 discipline).
# "a-within-b" means A is contained in B; the /18 below is the CONTAINER, so
# the narrower /20 yields "b-within-a".
assert cidr_relation("172.26.0.0/18", "172.26.32.0/20") == "b-within-a"
assert cidr_relation("172.26.32.0/20", "172.26.0.0/18") == "a-within-b"
assert cidr_relation("10.0.0.0/8", "192.168.0.0/16") == "disjoint"
assert cidr_relation("10.1.0.0/16", "10.0.0.0/8") == "a-within-b"
assert cidr_relation("10.1.0.0/16", "10.1.0.0/16") == "identical"
assert cidr_relation("10.0.0.0/9", "10.128.0.0/9") == "disjoint"
# 192.168.1.0/23 normalizes to 192.168.0.0/23 (a /23 third octet must be
# even), so both inputs are the same network: strict=False makes this
# "identical"; aligned CIDRs never partially overlap.
assert cidr_relation("192.168.0.0/23", "192.168.1.0/23") == "identical"
assert cidr_relation("2001:db8::/32", "10.0.0.0/8") == "disjoint"
# invalid: a malformed CIDR must raise ValueError (the caller validates first).
try:
    cidr_relation("bad-cidr", "10.0.0.0/8")
    raise AssertionError("malformed CIDR must raise ValueError")
except ValueError:
    pass
assert ip_in_cidr("10.19.5.7", "10.19.0.0/16") is True
assert ip_in_cidr("10.20.5.7", "10.19.0.0/16") is False
assert ip_in_cidr("not-an-ip", "10.0.0.0/8") is False
assert sg_intersection(["sg-b", "sg-a"], ["sg-a", "sg-c"]) == ["sg-a"]
assert sg_intersection([], ["sg-a"]) == []

# Security-group rule comparison: normal, boundary and invalid inputs.
assert port_in_range(22, "22/22") is True                  # single-port rule
assert port_in_range(22, "20/30") is True                  # inside the range
assert port_in_range(31, "20/30") is False                 # just outside
assert port_in_range(1, "-1/-1") is True                   # "all ports"
assert port_in_range(25, "30/20") is True                  # reversed bounds tolerated
assert port_in_range(22, "") is False                      # invalid: empty range
assert port_in_range(22, "ssh") is False                   # invalid: non-numeric
assert protocol_matches("all", "tcp") is True              # ALL covers TCP
assert protocol_matches("", "tcp") is True                 # absent protocol = ALL
assert protocol_matches("tcp", "tcp") is True
assert protocol_matches("udp", "tcp") is False
assert rule_source_matches("10.0.0.0/8", "", "10.1.2.3") is True
assert rule_source_matches("10.0.0.0/8", "", "192.168.1.1") is False
assert rule_source_matches("", "sg-other", "10.1.2.3") is False  # group rule: no guess
_allow = {"Direction": "ingress", "IpProtocol": "tcp", "PortRange": "22/22",
          "SourceCidrIp": "10.0.0.0/8", "Policy": "Accept", "Priority": 1,
          "SecurityGroupRuleId": "sgr-a"}
_deny = {"Direction": "ingress", "IpProtocol": "tcp", "PortRange": "0/65535",
         "SourceCidrIp": "0.0.0.0/0", "Policy": "Drop", "Priority": 1,
         "SecurityGroupRuleId": "sgr-d"}
_v = evaluate_ingress_access([_allow], "10.1.2.3", 22, "tcp")
assert _v["verdict"] == "allowed" and _v["allow"]["rule_id"] == "sgr-a", _v
_v = evaluate_ingress_access([_allow, _deny], "10.1.2.3", 22, "tcp")
assert _v["verdict"] == "shadowed-by-deny" and _v["deny"]["rule_id"] == "sgr-d", _v
_v = evaluate_ingress_access([_allow], "192.168.1.1", 22, "tcp")
assert _v["verdict"] == "no-matching-rule", _v
_v = evaluate_ingress_access([_allow], "10.1.2.3", None, "tcp")
assert _v["verdict"] == "no-port-given", _v
_v = evaluate_ingress_access([], "10.1.2.3", 22, "tcp")    # invalid: no rules at all
assert _v["verdict"] == "no-matching-rule" and _v["allow"] is None, _v
_v = evaluate_ingress_access([_deny, dict(_allow, Priority=10)], "10.1.2.3", 22, "tcp")
assert _v["verdict"] == "shadowed-by-deny", _v             # better-priority deny wins


def _valid_cidr(text: str) -> bool:
    try:
        ipaddress.ip_network(text, strict=False)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Fact extraction from Describe* payloads
# ---------------------------------------------------------------------------

def _instance_facts(inst: dict[str, Any]) -> dict[str, Any]:
    return {
        "instance_id": inst.get("InstanceId", "N/A"),
        "instance_name": inst.get("InstanceName", "N/A"),
        "status": inst.get("Status", "N/A"),
        "zone_id": inst.get("ZoneId", "N/A"),
        "vpc_id": _dig(inst, ["VpcAttributes", "VpcId"]) or "N/A",
        "vswitch_id": _dig(inst, ["VpcAttributes", "VSwitchId"]) or "N/A",
        "private_ips": [str(x) for x in
                        (_dig(inst, ["VpcAttributes", "PrivateIpAddress",
                                      "IpAddress"]) or [])],
        "public_ips": [str(x) for x in
                       (_dig(inst, ["PublicIpAddress", "IpAddress"]) or [])],
        "eip": _dig(inst, ["EipAddress", "IpAddress"]) or "",
        "security_groups": [str(x) for x in
                            (_dig(inst, ["SecurityGroupIds",
                                         "SecurityGroupId"]) or [])],
        "instance_type": inst.get("InstanceType", "N/A"),
        "instance_charge_type": inst.get("InstanceChargeType", "N/A"),
        "network_type": inst.get("InstanceNetworkType", "N/A"),
    }


def _fetch_instances(region: str, instance_ids: list[str],
                     profile: Optional[str],
                     errors: list[dict[str, str]]) -> dict[str, dict]:
    params: dict[str, Any] = {"RegionId": region}
    if instance_ids:
        params["InstanceIds"] = json.dumps(instance_ids)
    try:
        items = _cli.paginate_paged(
            "ecs", "DescribeInstances", params,
            ["Instances", "Instance"], region=region, profile=profile)
    except _cli.CliError as e:
        _warn(errors, "ecs DescribeInstances", e)
        return {}
    return {f["instance_id"]: f
            for f in (_instance_facts(it) for it in items)
            if f["instance_id"] != "N/A"}


def _fetch_ingress_rules(region: str, security_group_ids: list[str],
                         profile: Optional[str],
                         errors: list[dict[str, str]]) -> dict[str, Any]:
    """Read the inbound RULE CONTENT of each security group (read-only).

    DescribeSecurityGroupAttribute is a query: it returns direction, protocol,
    port range, authorization object, policy and priority per rule, which is
    exactly what the manual console check used to ask the customer to retype.
    A group whose read fails is reported as unreadable with a [WARN], never
    silently treated as "no rules".
    """
    groups: list[dict[str, Any]] = []
    for sg_id in security_group_ids:
        try:
            body = _call(
                "ecs", "DescribeSecurityGroupAttribute",
                {"RegionId": region, "SecurityGroupId": sg_id,
                 "Direction": "ingress"},
                region, profile)
        except _cli.CliError as e:
            _warn(errors, f"ecs DescribeSecurityGroupAttribute {sg_id}", e)
            groups.append({"security_group_id": sg_id, "read": False,
                           "rules": []})
            continue
        groups.append({
            "security_group_id": sg_id,
            "read": True,
            "rules": [r for r in _extract_list(body, "Permissions", "Permission")
                      if isinstance(r, dict)],
        })
    return {"groups": groups}


def _rule_summary(rule: dict) -> str:
    """One compact, quotable line per rule (raw API values only)."""
    return (f"{rule.get('SecurityGroupRuleId') or 'N/A'} "
            f"{str(rule.get('Direction') or 'N/A')} "
            f"{str(rule.get('IpProtocol') or 'N/A')} "
            f"port {str(rule.get('PortRange') or 'N/A')} "
            f"from {str(rule.get('SourceCidrIp') or rule.get('SourceGroupId') or 'N/A')}"
            f" policy {str(rule.get('Policy') or 'N/A')}"
            f" priority {str(rule.get('Priority') or 'N/A')}")


# ---------------------------------------------------------------------------
# Check modes
# ---------------------------------------------------------------------------

def check_pair(args: argparse.Namespace, uid: str,
               errors: list[dict[str, str]]) -> dict[str, Any]:
    region = args.region_id
    facts = _fetch_instances(region, [args.instance_id_a, args.instance_id_b],
                             args.profile, errors)
    a = facts.get(args.instance_id_a)
    b = facts.get(args.instance_id_b)
    findings: list[dict[str, str]] = []
    missing = [i for i in (args.instance_id_a, args.instance_id_b)
               if i not in facts]
    if missing:
        findings.append({
            "check": "instance-lookup",
            "result": "FAIL",
            "evidence": "not returned by DescribeInstances in "
                        f"{region}: {', '.join(missing)}",
            "meaning": "wrong region, wrong ID, or the instances belong to "
                       "another account than the active credential",
        })
        return {"status": "FAIL",
                "next_action": "confirm RegionId and instance IDs (and the "
                               "owning account), then rerun",
                "findings": findings, "facts": facts,
                "manual_steps": [], "handoffs": {}}

    same_vpc = a["vpc_id"] == b["vpc_id"]
    findings.append({
        "check": "same-vpc",
        "result": "PASS" if same_vpc else "FAIL",
        "evidence": f"{a['instance_id']} vpc={a['vpc_id']}; "
                    f"{b['instance_id']} vpc={b['vpc_id']}",
        "meaning": ("both instances sit in one VPC: private routing is "
                    "expected inside it" if same_vpc else
                    "different VPCs: private IPs are not reachable across "
                    "VPCs without an explicit interconnection (CEN / "
                    "peering + routes), a manual configuration step"),
    })
    same_vsw = a["vswitch_id"] == b["vswitch_id"]
    findings.append({
        "check": "same-vswitch",
        "result": "INFO",
        "evidence": f"{a['instance_id']} vswitch={a['vswitch_id']}; "
                    f"{b['instance_id']} vswitch={b['vswitch_id']}",
        "meaning": ("same vSwitch" if same_vsw else
                    "different vSwitches: legal inside one VPC, but confirm "
                    "their CIDRs do not overlap other ranges (see the "
                    "cidr verdict below or run --check cidr-only)"),
    })
    shared = sg_intersection(a["security_groups"], b["security_groups"])
    findings.append({
        "check": "security-group-bindings",
        "result": "INFO",
        "evidence": f"{a['instance_id']}: {', '.join(a['security_groups'])}; "
                    f"{b['instance_id']}: {', '.join(b['security_groups'])}; "
                    f"shared: {', '.join(shared) if shared else 'none'}",
        "meaning": ("bindings listed; the rule content of every listed group "
                    "is read back below through "
                    "DescribeSecurityGroupAttribute (read-only), so no rule "
                    "has to be retyped from the console"),
    })

    # Inbound RULE CONTENT of the TARGET instance's groups (read-only query).
    # A is the source, B is the instance being accessed, so the allow rule that
    # matters lives on B's security group and authorizes A's private IP.
    target_sgs = [sg for sg in b["security_groups"] if sg != "N/A"]
    source_ip = a["private_ips"][0] if a["private_ips"] else ""
    rule_read = _fetch_ingress_rules(region, target_sgs, args.profile, errors)
    readable = [g for g in rule_read["groups"] if g["read"]]
    unreadable = [g["security_group_id"] for g in rule_read["groups"]
                  if not g["read"]]
    rule_lines: list[str] = []
    for group in rule_read["groups"]:
        rules = group["rules"]
        rule_lines.append(
            f"{group['security_group_id']}: "
            + (f"{len(rules)} inbound rule(s)" if group["read"]
               else "rule content NOT readable this run"))
        for rule in rules[:12]:
            rule_lines.append("  " + _rule_summary(rule))
        if len(rules) > 12:
            rule_lines.append(f"  ... {len(rules) - 12} more rule(s) not listed")
    findings.append({
        "check": "security-group-ingress-rules",
        "result": "INFO" if readable else "SKIPPED",
        "evidence": (" || ".join(rule_lines) if rule_lines
                     else "the target instance is bound to no readable "
                          "security group"),
        "meaning": ("inbound rules of the TARGET instance's security groups, "
                    "read from the API with direction, protocol, port range, "
                    "authorization object, policy and priority"
                    if readable else SG_RULE_VERDICTS["unreadable"]),
    })

    rule_verdict = "unreadable"
    if readable:
        merged = [r for g in readable for r in g["rules"]]
        evaluation = evaluate_ingress_access(
            merged, source_ip, args.port, args.protocol) if source_ip else {
                "verdict": "no-matching-rule", "allow": None, "deny": None,
                "group_authorized": []}
        rule_verdict = evaluation["verdict"]
        decided = evaluation["deny"] if evaluation["deny"] and \
            rule_verdict == "shadowed-by-deny" else evaluation["allow"]
        findings.append({
            "check": "security-group-rule-match",
            "result": {"allowed": "PASS",
                       "shadowed-by-deny": "FAIL",
                       "no-matching-rule": "FAIL"}.get(rule_verdict, "INFO"),
            "evidence": ("flow " + (source_ip or "<source-private-ip>")
                         + (f":{args.port}" if args.port else "")
                         + f"/{args.protocol}; "
                         + ("no security group rule was readable"
                            if not readable else
                            (_rule_summary(decided) if decided
                             else "no rule matched"))),
            "meaning": SG_RULE_VERDICTS.get(rule_verdict,
                                            SG_RULE_VERDICTS["unreadable"]),
        })
        if evaluation["group_authorized"]:
            findings.append({
                "check": "security-group-group-authorization",
                "result": "INFO",
                "evidence": " || ".join(_rule_summary(r)
                                        for r in evaluation["group_authorized"]),
                "meaning": "these rules authorize a SOURCE SECURITY GROUP "
                           "rather than a CIDR: whether A's instance belongs "
                           "to that group is not readable as an address "
                           "match, so confirm the group membership manually",
            })
    if unreadable:
        findings.append({
            "check": "security-group-rule-read",
            "result": "SKIPPED",
            "evidence": "not readable: " + ", ".join(unreadable),
            "meaning": SG_RULE_VERDICTS["unreadable"],
        })

    # Optional vSwitch CIDR inputs (read by the customer from the console).
    cidr_verdict = None
    if args.cidr_a and args.cidr_b:
        rel = cidr_relation(args.cidr_a, args.cidr_b)
        cidr_verdict = CIDR_VERDICTS[rel]
        findings.append({
            "check": "vswitch-cidr-overlap",
            "result": "FAIL" if rel != "disjoint" else "PASS",
            "evidence": f"--cidr-a {args.cidr_a} vs --cidr-b {args.cidr_b}",
            "meaning": cidr_verdict + (
                " overlapping private ranges make return routing ambiguous "
                "-- this is the top root cause for 'intranet ping fails "
                "inside one account'" if rel != "disjoint" else ""),
        })
    else:
        findings.append({
            "check": "vswitch-cidr-overlap",
            "result": "SKIPPED",
            "evidence": "no --cidr-a/--cidr-b given",
            "meaning": "read the two vSwitch IPv4 CIDRs from the VPC "
                       "console and rerun this check (or --check cidr-only) "
                       "to make the overlap verdict deterministic",
        })

    # Live-status cross-check via DescribeInstanceStatus (read-only context).
    try:
        statuses = _call(
            "ecs", "DescribeInstanceStatus",
            {"RegionId": region, "InstanceId.1": args.instance_id_a,
             "InstanceId.2": args.instance_id_b},
            region, args.profile)
        rows = _extract_list(statuses, "InstanceStatuses", "Instance")
        found = {str(r.get("InstanceId")): str(r.get("Status"))
                 for r in rows if isinstance(r, dict)}
        findings.append({
            "check": "instance-live-status",
            "result": "INFO",
            "evidence": "; ".join(f"{k}={v}" for k, v in sorted(found.items()))
                        or "no rows",
            "meaning": "a stopped instance answers nothing on any port",
        })
    except _cli.CliError as e:
        _warn(errors, "ecs DescribeInstanceStatus", e)

    # Zone availability context (best effort; never blocks the verdict).
    try:
        zones = _call(
            "ecs", "DescribeAvailableResource",
            {"RegionId": region, "DestinationResource": "Zone",
             "InstanceChargeType": a["instance_charge_type"]
             if a["instance_charge_type"] in ("PrePaid", "PostPaid")
             else None,
             "NetworkCategory": "vpc"},
            region, args.profile)
        zone_rows = _extract_list(zones, "AvailableZones", "AvailableZone")
        avail = [f"{z.get('ZoneId')}={z.get('Status', 'N/A')}"
                 for z in zone_rows if isinstance(z, dict)]
        findings.append({
            "check": "zone-availability-context",
            "result": "INFO",
            "evidence": "; ".join(avail) or "no zones returned",
            "meaning": "source zone "
                       f"{a['zone_id']} / target zone {b['zone_id']} "
                       "availability context for vSwitch placement",
        })
    except _cli.CliError as e:
        _warn(errors, "ecs DescribeAvailableResource", e)

    manual = list(MANUAL_STEPS["pair"])
    if not readable:
        # The rule read failed, so the console comparison is the fallback and
        # the dimensions below are what the customer must compare by hand.
        for dim in SG_RULE_VERIFY_DIMENSIONS:
            manual.append(f"  inbound rule dimension to verify (rule read "
                          f"failed this run): {dim}")
    if rule_verdict in ("no-matching-rule", "shadowed-by-deny"):
        if args.port:
            # Traffic direction: A is the source, B is the instance being
            # accessed, so the allow rule lives on B's security group and
            # authorizes A's private IP.
            manual.append(
                f"  concrete rule shape: on the TARGET ({b['instance_id']}) "
                f"security group add an inbound allow for {args.protocol} "
                f"port {args.port} with authorization object "
                f"{source_ip or '<source-private-ip>'}/32, then re-run this "
                f"check to confirm the verdict flips to PASS")
        elif b["private_ips"] and a["private_ips"]:
            manual.append(
                f"  rule shape without a given port: on the TARGET "
                f"({b['instance_id']}) security group add an inbound allow "
                f"for the needed protocol/port with authorization object "
                f"{a['private_ips'][0]}/32, then re-run with --port to get "
                f"the rule-level verdict")
    elif rule_verdict == "allowed":
        manual.append(
            "  the cloud-side inbound rule already allows this flow, so the "
            "remaining work is on the guest and the application: check the "
            "OS firewall, the listening address (0.0.0.0 vs 127.0.0.1) and "
            "the service itself")

    findings.append({
        "check": "intranet-whitelist-misconceptions",
        "result": "INFO",
        "evidence": "embedded reference knowledge",
        "meaning": " | ".join(SG_MISCONCEPTION_FIXES),
    })

    status = "DEGRADED" if errors else "OK"
    if not same_vpc:
        next_action = ("interconnect the two VPCs first (manual, "
                       "console/VPC peering), then re-run this check")
    elif cidr_verdict and "OVERLAP" in cidr_verdict:
        next_action = ("resolve the CIDR conflict: create a non-overlapping "
                       "vSwitch in the same VPC and move one instance's "
                       "private IP onto it (same-zone constraint, manual)")
    elif rule_verdict == "allowed":
        next_action = ("the inbound security-group rule already matches this "
                       "flow: continue on the guest side (OS firewall, "
                       "listening address, service) and retest with telnet "
                       "on the actual port")
    elif rule_verdict in ("no-matching-rule", "shadowed-by-deny"):
        next_action = ("add or re-prioritise the inbound allow on the TARGET "
                       "instance's security group in the console (manual), "
                       "then re-run this check to confirm PASS")
    else:
        next_action = ("rerun with --port (and the rule content readable) to "
                       "get the rule-level verdict, or compare the printed "
                       "rule dimensions in the console")
    return {"status": status, "next_action": next_action,
            "findings": findings, "facts": facts,
            "manual_steps": manual,
            "guest_boundary": GUEST_BOUNDARY_ITEMS,
            "handoffs": {}}


def check_transfer(args: argparse.Namespace, uid: str,
                   errors: list[dict[str, str]]) -> dict[str, Any]:
    region = args.region_id
    facts = _fetch_instances(region, [args.instance_id], args.profile, errors)
    inst = facts.get(args.instance_id)
    if inst is None:
        return {"status": "FAIL",
                "next_action": "confirm the source instance ID / region / "
                               "owning account, then rerun",
                "findings": [{"check": "source-instance-lookup",
                              "result": "FAIL",
                              "evidence": f"{args.instance_id} not found in "
                                          f"{region}",
                              "meaning": "DescribeInstances returned no row"}],
                "facts": facts, "manual_steps": [], "handoffs": {}}

    findings = [{
        "check": "source-instance-facts",
        "result": "INFO",
        "evidence": (f"region={region} zone={inst['zone_id']} "
                     f"vpc={inst['vpc_id']} vswitch={inst['vswitch_id']} "
                     f"security-groups={','.join(inst['security_groups'])} "
                     f"type={inst['instance_type']}"),
        "meaning": "region and availability zone are the dimensions the "
                   "target account's resources must match; the VPC ID is "
                   "account-local and does not carry over",
    }]

    if args.target_vpc_id:
        if args.same_account:
            ok = args.target_vpc_id == inst["vpc_id"]
            findings.append({
                "check": "target-vpc-consistency",
                "result": "PASS" if ok else "FAIL",
                "evidence": f"target vpc {args.target_vpc_id} vs instance "
                            f"vpc {inst['vpc_id']}",
                "meaning": "same-account vSwitch change: the destination "
                           "vSwitch must sit inside the instance's current "
                           "VPC" if not ok else
                           "same VPC: the switch-change condition holds",
            })
        else:
            findings.append({
                "check": "target-vpc-consistency",
                "result": "INFO",
                "evidence": f"target vpc {args.target_vpc_id} vs source "
                            f"vpc {inst['vpc_id']} (different accounts)",
                "meaning": "cross-account transfer: each account owns its "
                           "own VPCs, so a different VPC ID is expected and "
                           "is NOT a mismatch. The real rule lives inside "
                           "the TARGET account -- the selected vSwitch and "
                           "security group must share one single target VPC "
                           "-- and that membership is not readable through "
                           "this skill's verified read-only action set, so "
                           "verify it in the target account's VPC console",
            })
    if args.target_zone_id:
        ok = args.target_zone_id == inst["zone_id"]
        findings.append({
            "check": "target-zone-consistency",
            "result": "PASS" if ok else "FAIL",
            "evidence": f"target zone {args.target_zone_id} vs source zone "
                        f"{inst['zone_id']}",
            "meaning": "the target vSwitch must be in the source "
                       "instance's availability zone" if not ok else
                       "zone condition satisfied",
        })
    if args.target_vswitch_id or args.target_security_group_id:
        findings.append({
            "check": "target-resource-identity",
            "result": "INFO",
            "evidence": (f"target vswitch={args.target_vswitch_id or 'N/A'} "
                         f"security-group={args.target_security_group_id or 'N/A'}"),
            "meaning": "created BY the TARGET account itself: an empty "
                       "picker usually means the wrong region or zone, a "
                       "security group and vSwitch that do not share one "
                       "target VPC, or resources built in the wrong account",
        })

    # Zone availability for the instance type (explains 'vSwitch not
    # selectable' when the zone sells nothing of this family).
    try:
        avail = _call(
            "ecs", "DescribeAvailableResource",
            {"RegionId": region, "DestinationResource": "InstanceType",
             "InstanceType": inst["instance_type"],
             "InstanceChargeType": inst["instance_charge_type"]
             if inst["instance_charge_type"] in ("PrePaid", "PostPaid")
             else None},
            region, args.profile)
        rows = _extract_list(avail, "AvailableZones", "AvailableZone")
        zones = [f"{z.get('ZoneId')}={z.get('Status', 'N/A')}"
                 for z in rows if isinstance(z, dict)]
        source_avail = [z for z in zones
                        if z.startswith(f"{inst['zone_id']}=")]
        findings.append({
            "check": "instance-type-zone-availability",
            "result": "INFO",
            "evidence": ("source zone: " + (source_avail[0] if source_avail
                                            else "not listed")
                         + "; region zones: "
                         + ("; ".join(zones) if zones else "none")),
            "meaning": "the target vSwitch must sit in a zone that actually "
                       "serves this instance family (economy families are "
                       "placed randomly -> cover all zones)",
        })
    except _cli.CliError as e:
        _warn(errors, "ecs DescribeAvailableResource", e)

    findings.append({
        "check": "grant-dependency",
        "result": "INFO",
        "evidence": "error string InvalidDependence.GrantAccess",
        "meaning": ERROR_DISPOSITIONS["InvalidDependence.GrantAccess"],
    })

    manual = list(MANUAL_STEPS["transfer"])
    manual += [f"consistency rule: {c}"
               for c in TRANSFER_CONSISTENCY_CONDITIONS]
    manual += [f"note: {n}" for n in TRANSFER_EXTRA_NOTES]

    status = "DEGRADED" if errors else "OK"
    failed = [f_["check"] for f_ in findings
              if f_.get("result") == "FAIL"]
    if failed:
        next_action = ("fix the mismatched dimension(s) "
                       f"[{', '.join(failed)}] on the TARGET account first "
                       "(customer-executed steps above: console or the equivalent OpenAPI), then retry the "
                       "transfer selection")
    else:
        next_action = ("take the source facts above to the target account: "
                       "create the vSwitch/security group in the same "
                       "region and zone, inside one single target VPC, "
                       "cancel any source-account reverse authorization if "
                       "GrantAccess errors appear, then perform the "
                       "transfer manually")
    return {"status": status, "next_action": next_action,
            "findings": findings, "facts": {args.instance_id: inst},
            "manual_steps": manual, "handoffs": {}}


def check_ip_inventory(args: argparse.Namespace, uid: str,
                       errors: list[dict[str, str]]) -> dict[str, Any]:
    params: dict[str, Any] = {"RegionId": args.region_id}
    if args.vpc_id:
        params["VpcId"] = args.vpc_id
    try:
        items = _cli.paginate_paged(
            "ecs", "DescribeInstances", params,
            ["Instances", "Instance"], region=args.region_id,
            profile=args.profile)
    except _cli.CliError as e:
        _warn(errors, "ecs DescribeInstances", e)
        return {"status": "FAIL",
                "next_action": "check the ecs:DescribeInstances permission "
                               "and the region, then rerun",
                "findings": [], "facts": {}, "manual_steps": [],
                "handoffs": {}}

    all_facts = [_instance_facts(it) for it in items]
    rows = all_facts
    if args.cidr_filter:
        rows = [f for f in all_facts
                if any(ip_in_cidr(ip, args.cidr_filter)
                       for ip in f["private_ips"])]
    findings = [{
        "check": "private-ip-inventory",
        "result": "INFO",
        "evidence": (f"{len(rows)} of {len(all_facts)} instances in "
                     f"{args.region_id}"
                     + (f" hold a private IP inside {args.cidr_filter}"
                        if args.cidr_filter else " (no CIDR filter)")),
        "meaning": "primary + secondary private IPs as returned by the API; "
                   "an empty result is a valid finding, not an error",
    }]
    manual = list(MANUAL_STEPS["ip-list"])
    return {"status": "DEGRADED" if errors else "OK",
            "next_action": "present the IP table; for per-OS secondary-IP "
                           "activation inside the guest, follow the manual "
                           "note below",
            "findings": findings,
            "inventory": rows,
            "facts": {r["instance_id"]: r for r in rows},
            "manual_steps": manual, "handoffs": {}}


def check_public_path(args: argparse.Namespace, uid: str,
                      errors: list[dict[str, str]]) -> dict[str, Any]:
    region = args.region_id
    facts = _fetch_instances(region, [args.instance_id], args.profile, errors)
    inst = facts.get(args.instance_id)
    if inst is None:
        return {"status": "FAIL",
                "next_action": "confirm the instance ID / region / owning "
                               "account, then rerun",
                "findings": [{"check": "instance-lookup", "result": "FAIL",
                              "evidence": "no row returned",
                              "meaning": "cannot locate the instance"}],
                "facts": facts, "manual_steps": [], "handoffs": {}}

    try:
        statuses = _call(
            "ecs", "DescribeInstanceStatus",
            {"RegionId": region, "InstanceId.1": args.instance_id},
            region, args.profile)
        rows = _extract_list(statuses, "InstanceStatuses", "Instance")
        live = rows[0].get("Status", "N/A") if rows else "N/A"
    except _cli.CliError as e:
        _warn(errors, "ecs DescribeInstanceStatus", e)
        live = "unavailable"

    eips: list[dict[str, str]] = []
    try:
        eip_body = _call(
            "vpc", "DescribeEipAddresses",
            {"RegionId": region,
             "AssociatedInstanceId": args.instance_id},
            region, args.profile)
        for row in _extract_list(eip_body, "EipAddresses", "EipAddress"):
            if isinstance(row, dict):
                eips.append({
                    "ip": str(row.get("IpAddress", "N/A")),
                    "status": str(row.get("Status", "N/A")),
                    "allocation_id": str(row.get("AllocationId", "N/A")),
                    "bandwidth_mbps": str(row.get("Bandwidth", "N/A")),
                })
    except _cli.CliError as e:
        _warn(errors, "vpc DescribeEipAddresses", e)

    has_public = bool(inst["public_ips"]) or bool(inst["eip"]) or bool(eips)
    bound_in_use = [e_ for e_ in eips if e_["status"] == "InUse"]
    if not has_public:
        verdict = ("the instance holds no public IP and no bound EIP: "
                   "public access is impossible by configuration, this is a "
                   "cloud-side explanation (needs EIP / NAT, manual)")
    elif eips and not bound_in_use:
        verdict = ("an EIP exists for the instance but none is InUse "
                   f"(statuses: {', '.join(e_['status'] for e_ in eips)}): "
                   "the binding state explains the public failure")
    else:
        verdict = ("public path IS configured on the cloud side (status "
                   f"{live}, {len(bound_in_use) or 'classic'} in-use EIP / "
                   "public IP): if the intranet works, the internet-side "
                   "fault is NOT a missing public binding -- check "
                   "security-group inbound rules from the internet and the "
                   "application (HTTPS binding / reverse proxy) manually")
    findings = [{
        "check": "public-path-presence",
        "result": "PASS" if has_public else "FAIL",
        "evidence": (f"public_ips={inst['public_ips'] or 'none'} "
                     f"instance_eip={inst['eip'] or 'none'} "
                     f"eip_records={json.dumps(eips) if eips else 'none'} "
                     f"live_status={live}"),
        "meaning": verdict,
    }]
    manual = list(MANUAL_STEPS["eip-check"])
    handoffs = {}
    if not has_public:
        handoffs["alibabacloud-ecs-vpc-publicnetwork-troubleshoot"] = \
            HANDOFFS["alibabacloud-ecs-vpc-publicnetwork-troubleshoot"]
    return {"status": "DEGRADED" if errors else "OK",
            "next_action": ("relay the verdict; public egress/ingress setup "
                            "and application-layer fixes are manual"),
            "findings": findings, "facts": {args.instance_id: inst},
            "manual_steps": manual, "handoffs": handoffs}


def check_cidr_only(args: argparse.Namespace) -> dict[str, Any]:
    rel = cidr_relation(args.cidr_a, args.cidr_b)
    verdict = CIDR_VERDICTS[rel]
    overlap = rel != "disjoint"
    findings = [{
        "check": "cidr-overlap(local)",
        "result": "FAIL" if overlap else "PASS",
        "evidence": f"{args.cidr_a} vs {args.cidr_b} -> {rel}",
        "meaning": verdict,
    }]
    manual = list(MANUAL_STEPS["cidr"]) if overlap else []
    return {"status": "OK",
            "next_action": ("hand the customer the re-planning steps above"
                            if overlap else
                            "no action; the two ranges cannot conflict"),
            "findings": findings, "facts": {}, "manual_steps": manual,
            "handoffs": {}}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_human(result: dict[str, Any]) -> None:
    print("=" * 72)
    print(f" {SKILL_NAME} -- check: {result['mode']}")
    print("=" * 72)
    if result.get("uid"):
        print(f"Caller UID : {result['uid']} (auto-filled via "
              f"sts get-caller-identity)")
    if result.get("region_id"):
        print(f"Region     : {result['region_id']}")
    facts = result.get("facts") or {}
    if facts:
        print("- instance facts (from DescribeInstances) -")
        for fid, f in facts.items():
            print(f"  {fid}: vpc={f.get('vpc_id')} vswitch="
                  f"{f.get('vswitch_id')} zone={f.get('zone_id')} "
                  f"ips={','.join(f.get('private_ips') or []) or 'N/A'} "
                  f"sgs={','.join(f.get('security_groups') or []) or 'N/A'} "
                  f"status={f.get('status')}")
    inv = result.get("inventory")
    if inv is not None:
        print("- private IP inventory -")
        for r in inv:
            print(f"  {r['instance_id']}  {r['instance_name']}  "
                  f"zone={r['zone_id']} vpc={r['vpc_id']} "
                  f"vswitch={r['vswitch_id']} "
                  f"ips={','.join(r['private_ips']) or 'N/A'}")
        if not inv:
            print("  (no matching instance -- a valid finding)")
    print("- findings -")
    for f_ in result["findings"]:
        print(f"  [{f_['result']:<7}] {f_['check']}")
        print(f"            evidence: {f_['evidence']}")
        print(f"            meaning : {f_['meaning']}")
    if result.get("manual_steps"):
        print("- manual guidance (performed by a human in the console; "
              "this skill changes nothing) -")
        for s in result["manual_steps"]:
            print(f"  * {s}")
    if result.get("guest_boundary"):
        print("- not visible to read-only cloud APIs (customer self-check "
              "or manual support) -")
        for g in result["guest_boundary"]:
            print(f"  * {g}")
    if result.get("handoffs"):
        print("- hand off -")
        for k, v in result["handoffs"].items():
            print(f"  * {k}: {v}")
    if result.get("api_calls"):
        print("- evidence: API calls made -")
        for c in result["api_calls"]:
            print(f"  * {c['product']} {c['action']} "
                  f"{json.dumps(c['params'])}")
    if result.get("errors"):
        print("## Graceful Degradation Log")
        for e in result["errors"]:
            print(f"  [WARN] {e['api']}: {e['code']} -> {e['message'][:200]}")


# ---------------------------------------------------------------------------
# Argument parsing and main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="vpc_connectivity_check.py",
        description="Read-only ECS VPC / vSwitch / security-group "
                    "intranet-configuration checker (manual guidance "
                    "only; changes nothing).",
    )
    p.add_argument("--check", required=True, choices=_MODES,
                   help="which deterministic check to run")
    p.add_argument("--region-id", default=None,
                   help=f"region ID for every cloud-backed mode "
                        f"(required; e.g. {DEFAULT_REGION})")
    p.add_argument("--profile", default=None,
                   help="optional aliyun CLI credential profile name")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument("--instance-id-a", default=None,
                   help="pair mode: first instance ID")
    p.add_argument("--instance-id-b", default=None,
                   help="pair mode: second instance ID (the one being "
                        "accessed)")
    p.add_argument("--instance-id", default=None,
                   help="transfer / public-path mode: instance ID")
    p.add_argument("--cidr-a", default=None, help="CIDR block A (pair / "
                   "cidr-only)")
    p.add_argument("--cidr-b", default=None, help="CIDR block B (pair / "
                   "cidr-only)")
    p.add_argument("--port", type=int, default=None,
                   help="pair mode: target port the customer wants to "
                        "verify (1-65535)")
    p.add_argument("--protocol", default="tcp", choices=("tcp", "udp",
                                                         "icmp", "all"),
                   help="pair mode: protocol for the rule shape hint")
    p.add_argument("--target-zone-id", default=None,
                   help="transfer mode: target vSwitch zone")
    p.add_argument("--target-vpc-id", default=None,
                   help="transfer mode: target vSwitch/security-group VPC")
    p.add_argument("--target-vswitch-id", default=None,
                   help="transfer mode: target vSwitch ID")
    p.add_argument("--target-security-group-id", default=None,
                   help="transfer mode: target security group ID")
    p.add_argument("--same-account", action="store_true",
                   help="transfer mode: the destination resources belong to "
                        "the SAME account (vSwitch change), so the "
                        "destination VPC must equal the instance VPC; "
                        "without this flag the case is a cross-account "
                        "transfer, where VPC IDs legitimately differ")
    p.add_argument("--cidr-filter", default=None,
                   help="ip-inventory mode: keep only instances holding a "
                        "private IP inside this CIDR")
    p.add_argument("--vpc-id", default=None,
                   help="ip-inventory mode: restrict to one VPC")
    return p


def _validate(args: argparse.Namespace) -> list[str]:
    problems: list[str] = []

    def need(value: Optional[str], label: str, pattern: Optional[re.Pattern]
             = None) -> None:
        if not value:
            problems.append(f"{label} is required for --check {args.check}")
        elif pattern and not pattern.match(value):
            problems.append(f"{label}={value!r} has an invalid format")

    if args.check in ("pair", "transfer", "ip-inventory", "public-path"):
        need(args.region_id, "--region-id", _REGION_RE)
    if args.check == "pair":
        need(args.instance_id_a, "--instance-id-a", _ID_RE)
        need(args.instance_id_b, "--instance-id-b", _ID_RE)
    if args.check == "transfer":
        need(args.instance_id, "--instance-id", _ID_RE)
        if args.target_zone_id and not _ZONE_RE.match(args.target_zone_id):
            problems.append("--target-zone-id format invalid")
        if args.target_vpc_id and not _REGION_RE.match(args.target_vpc_id) \
                and not args.target_vpc_id.startswith("vpc-"):
            problems.append("--target-vpc-id format invalid")
        if args.target_vswitch_id and \
                not _VSW_RE.match(args.target_vswitch_id):
            problems.append("--target-vswitch-id format invalid")
        if args.target_security_group_id and \
                not _SG_RE.match(args.target_security_group_id):
            problems.append("--target-security-group-id format invalid")
    if args.check == "public-path":
        need(args.instance_id, "--instance-id", _ID_RE)
    if args.check == "cidr-only":
        need(args.cidr_a, "--cidr-a")
        need(args.cidr_b, "--cidr-b")
    for flag in (args.cidr_a, args.cidr_b, args.cidr_filter):
        if flag and not _valid_cidr(flag):
            problems.append(f"CIDR {flag!r} is not parseable")
    if args.port is not None and not (1 <= args.port <= 65535):
        problems.append("--port must be between 1 and 65535")
    return problems


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)

    problems = _validate(args)
    if problems:
        result = {"mode": args.check, "status": "FAIL",
                  "next_action": "fix the input: "
                                 + "; ".join(problems),
                  "findings": [{"check": "input-validation",
                                "result": "FAIL",
                                "evidence": "; ".join(problems),
                                "meaning": "mandatory parameter gate"}],
                  "facts": {}, "manual_steps": [], "handoffs": {}}
        _finish(args, result)
        return 1

    errors: list[dict[str, str]] = []
    uid = ""
    if args.check != "cidr-only":
        _cli.check_cli_available()
        try:
            body = _call("sts", "GetCallerIdentity", {},
                         args.region_id or DEFAULT_REGION, args.profile)
            uid = str(body.get("AccountId", "") or "")
        except _cli.CliError as e:
            _warn(errors, "sts GetCallerIdentity", e)
        if not uid:
            result = {"mode": args.check, "uid": "",
                      "region_id": args.region_id, "status": "FAIL",
                      "next_action": "configure the aliyun CLI default "
                                     "credential chain (run 'aliyun "
                                     "configure'); never pass AK/SK to "
                                     "this script",
                      "findings": [{"check": "credential-precheck",
                                    "result": "FAIL",
                                    "evidence": "get-caller-identity "
                                                "returned no AccountId",
                                    "meaning": "NoPermission / "
                                               "InvalidCredential / "
                                               "unconfigured chain"}],
                      "facts": {}, "manual_steps": [], "handoffs": {},
                      "errors": errors}
            _finish(args, result)
            return 1

    if args.check == "pair":
        result = check_pair(args, uid, errors)
    elif args.check == "transfer":
        result = check_transfer(args, uid, errors)
    elif args.check == "ip-inventory":
        result = check_ip_inventory(args, uid, errors)
    elif args.check == "public-path":
        result = check_public_path(args, uid, errors)
    else:
        result = check_cidr_only(args)

    result.setdefault("mode", args.check)
    result["uid"] = uid or result.get("uid", "")
    result["region_id"] = args.region_id
    result.setdefault("errors", errors)
    result["api_calls"] = list(_API_CALLS)
    exit_code = 1 if result["status"] == "FAIL" else 0
    _finish(args, result)
    return exit_code


def _finish(args: argparse.Namespace, result: dict[str, Any]) -> None:
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        render_human(result)
    print(f"\nSTATUS: {result['status']}")
    print(f"NEXT_ACTION: {result['next_action']}")


# ---------------------------------------------------------------------------
# Offline regression lock (no cloud, no subprocess): run with
#   python3 scripts/areas/vpc_connectivity_check/vpc_connectivity_check.py --selftest
# Locks the connectivity decision helpers: the CIDR relation classifier (which
# drives whether two ranges are reported as conflicting) plus the response
# diggers used to pull facts out of Describe* payloads. A wrong relation either
# raises a false route-conflict alarm or clears a real overlap, mis-steering
# VPC peering / routing decisions.
# ---------------------------------------------------------------------------

def _run_selftest() -> int:
    rc = 0
    checked: list = []

    def expect(name, cond):
        nonlocal rc
        checked.append(name)
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            rc = 1

    # --- _dig ---------------------------------------------------------------
    expect("dig_deep", _dig({"a": {"b": {"c": 7}}}, ["a", "b", "c"]) == 7)
    expect("dig_nondict_mid", _dig({"a": "str"}, ["a", "b"]) is None)
    expect("dig_none_root", _dig(None, ["a"]) is None)
    expect("dig_missing", _dig({"a": {}}, ["a", "b", "c"]) is None)

    # --- _extract_list ------------------------------------------------------
    expect("ex_dict_of_list",
           _extract_list({"I": {"X": [{"a": 1}]}}, "I", "X") == [{"a": 1}])
    expect("ex_direct_list",
           _extract_list({"I": [{"a": 1}]}, "I", "X") == [{"a": 1}])
    expect("ex_dict_wo_item", _extract_list({"I": {"Y": []}}, "I", "X") == [])
    expect("ex_nondict_body",
           _extract_list("x", "I", "X") == [] and _extract_list(None, "I", "X") == [])

    # --- _valid_cidr --------------------------------------------------------
    expect("vc_ok", _valid_cidr("10.0.0.0/8"))
    expect("vc_bad_octets", not _valid_cidr("10.0.0/8"))
    expect("vc_garbage", not _valid_cidr("bad") and not _valid_cidr(""))

    # --- cidr_relation ------------------------------------------------------
    expect("rel_identical", cidr_relation("10.1.0.0/16", "10.1.0.0/16") == "identical")
    expect("rel_hostbits_normalize",
           cidr_relation("10.0.0.5/24", "10.0.0.0/24") == "identical")
    expect("rel_a_within_b", cidr_relation("10.1.0.0/16", "10.0.0.0/8") == "a-within-b")
    expect("rel_b_within_a", cidr_relation("172.26.0.0/18", "172.26.32.0/20") == "b-within-a")
    expect("rel_disjoint", cidr_relation("10.0.0.0/8", "192.168.0.0/16") == "disjoint")
    expect("rel_adjacent_disjoint",
           cidr_relation("10.0.0.0/9", "10.128.0.0/9") == "disjoint")
    expect("rel_version_mismatch_disjoint",
           cidr_relation("2001:db8::/32", "10.0.0.0/8") == "disjoint")
    try:
        cidr_relation("nope", "10.0.0.0/8")
        expect("rel_malformed_raises", False)
    except ValueError:
        expect("rel_malformed_raises", True)

    # --- ip_in_cidr ---------------------------------------------------------
    expect("ip_in_true", ip_in_cidr("10.19.5.7", "10.19.0.0/16"))
    expect("ip_in_false", not ip_in_cidr("10.20.5.7", "10.19.0.0/16"))
    expect("ip_in_badip_false", not ip_in_cidr("not-an-ip", "10.0.0.0/8"))

    # --- sg_intersection ----------------------------------------------------
    expect("sg_common", sg_intersection(["sg-b", "sg-a"], ["sg-a", "sg-c"]) == ["sg-a"])
    expect("sg_empty_side", sg_intersection([], ["sg-a"]) == [])
    expect("sg_sorted_unique",
           sg_intersection(["sg-2", "sg-1", "sg-2"], ["sg-2", "sg-1"]) == ["sg-1", "sg-2"])

    # --- check_cidr_only verdict mapping (pure) ------------------------------
    import argparse as _ap
    r_id = check_cidr_only(_ap.Namespace(cidr_a="10.0.0.0/8", cidr_b="10.0.0.0/8"))
    expect("cco_identical_is_overlap",
           r_id["findings"][0]["result"] == "FAIL"
           and r_id["findings"][0]["evidence"].endswith("-> identical")
           and r_id["manual_steps"])
    r_dis = check_cidr_only(_ap.Namespace(cidr_a="10.0.0.0/8", cidr_b="192.168.0.0/16"))
    expect("cco_disjoint_is_pass",
           r_dis["findings"][0]["result"] == "PASS" and not r_dis["manual_steps"])
    r_within = check_cidr_only(
        _ap.Namespace(cidr_a="10.1.0.0/16", cidr_b="10.0.0.0/8"))
    expect("cco_within_is_overlap", r_within["findings"][0]["result"] == "FAIL")
    expect("cco_status_ok_no_errors",
           r_id["status"] == "OK" and r_dis["status"] == "OK")

    print(f"--selftest: {len(checked)} checks, "
          f"{'ALL PASS' if rc == 0 else 'FAILURES PRESENT'}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
