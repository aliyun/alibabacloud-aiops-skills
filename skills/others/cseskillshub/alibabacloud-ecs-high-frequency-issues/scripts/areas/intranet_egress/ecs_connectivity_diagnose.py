#!/usr/bin/env python3
"""
ecs_connectivity_diagnose.py -- Entry script for ECS intranet / egress
======================================================================
connectivity diagnosis (direction-aware boundary attribution).

SECURITY:
  * Every cloud query performed here is a NON-MUTATING Describe/Get call
    routed through the shared CLI layer (_cli.py). This script never creates,
    changes, deletes, attaches, detaches, reboots or otherwise alters a cloud
    resource, and it never executes anything inside a customer instance.
  * Credential material is never read, printed or passed explicitly: the
    aliyun CLI default credential chain resolves authentication.
  * In-guest state (host firewall, listener bind address, guest routes, DNS,
    proxy settings, live probe results, request arrival in service logs)
    cannot be observed through any cloud API. This script therefore PRINTS a
    checklist of state-inspection commands for the CUSTOMER to run inside the
    instance and paste back as plain text. The skill never executes anything
    inside the instance: guest_command_gate.py validates those inspection
    commands locally, with no cloud call, and the customer runs them by hand.
  * Invoke only after the confirmation step described in SKILL.md, and only
    against the resources the user named.

Decision steps (see references/intranet-egress__diagnosis-decision-tree.md):
  D0  input gate        direction + target + instance locator must be present
  D1  asset ownership   sts identity + DescribeInstances (account / not found)
  D2  direction split   ingress / egress / internal (entry category NOT trusted)
  D3  cloud-side reads  security-group rules both directions (the rules that
                        are actually in effect right now), VSwitch CIDRs,
                        route tables, NAT gateways, SNAT coverage
  D4  target geography  mainland vs overseas target routing decision
                        (cross-border branch; no live link claims)
  D5  guest path        manual checklist output (never executed here)
  D6  attribution       who owns the next step + handoff (application layer,
                        client-local, platform-side-invisible, change requests)

Output: human report (default) or --json machine output; always ends with the
STATUS / VERDICT / ATTRIBUTION / NEXT_ACTION contract lines.

Exit codes:
  0  conclusion produced (STATUS OK or DEGRADED)
  1  no usable conclusion (STATUS FAIL: missing input, or every query failed)
  2  credential/identity chain unusable, or argparse usage error

Usage example:
  python3 scripts/areas/intranet_egress/ecs_connectivity_diagnose.py \\
    --region-id cn-shenzhen --instance-id i-example001 --direction egress \\
    --target https://acme-v02.api.letsencrypt.org/directory \\
    --error-text "curl: (28) Operation timed out after 10000 milliseconds"
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
    DOMESTIC_ALTERNATIVES,
    ERROR_STRING_CLASSES,
    GUEST_CHECKS_LINUX,
    GUEST_CHECKS_WINDOWS,
    HANDOFF_SKILLS,
    OVERSEAS_TARGET_HINTS,
    is_mainland_region,
)

_REGION_RE = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
_INSTANCE_ID_RE = re.compile(r"^i-[A-Za-z0-9-]{4,40}$")


# ---------------------------------------------------------------------------
# Small pure helpers (inline boundary assertions at the bottom of the file)
# ---------------------------------------------------------------------------

def _is_ip(text: Optional[str]) -> bool:
    if not text:
        return False
    try:
        ipaddress.ip_address(str(text).strip())
        return True
    except ValueError:
        return False


def _is_private(text: Optional[str]) -> bool:
    if not _is_ip(text):
        return False
    return ipaddress.ip_address(str(text).strip()).is_private


def _norm_port(port_range: Any, want: Optional[int]) -> tuple:
    """Normalize an ECS rule PortRange ("80/80", "-1/-1", "1/65535").

    An any-port range (-1/-1) collapses to the wanted port when one is given,
    so a wildcard rule can be compared directly; with no wanted port it spans
    every port.
    """
    try:
        lo_s, hi_s = (port_range or "-1/-1").split("/", 1)
        lo, hi = int(lo_s), int(hi_s)
    except (ValueError, AttributeError, TypeError):
        lo, hi = -1, -1
    if lo == -1 or hi == -1:
        return (want, want) if want else (1, 65535)
    return (lo, hi)


def _port_match(port_range: Any, want: Optional[int]) -> bool:
    if want is None:  # protocol-level query (e.g. icmp): any port
        return True
    lo, hi = _norm_port(port_range, want)
    return lo <= want <= hi


def _proto_match(rule_proto: Any, want: str) -> bool:
    rp = str(rule_proto or "").lower()
    return rp in {str(want or "").lower(), "-1", "all"}


def _cidr_contains(cidr: str, ip: Optional[str]) -> bool:
    """True when cidr is the any-address range, or ip falls inside cidr."""
    c = (cidr or "").strip()
    if not ip:
        return False
    if c in ("0.0.0.0/0", "::/0"):
        return True
    try:
        return ipaddress.ip_address(str(ip).strip()) in \
            ipaddress.ip_network(c, strict=False)
    except ValueError:
        return False


def _match_rule(rule: dict, direction: str, proto: str, port: Optional[int],
                remote_ip: Optional[str]) -> str:
    """Classify one security-group rule against a probe: match/maybe/no.

    "maybe" = protocol and port match, but the rule pins a specific remote
    CIDR while the concrete remote IP is unknown. Such rules are surfaced as
    candidates and never drive the verdict.
    """
    if (rule.get("Direction") or "").lower() != direction:
        return "no"
    if not _proto_match(rule.get("IpProtocol", ""), proto):
        return "no"
    if not _port_match(rule.get("PortRange", ""), port):
        return "no"
    remote_key = "DestCidrIp" if direction == "egress" else "SourceCidrIp"
    remote = (rule.get(remote_key) or "").strip()
    if not remote or remote in ("0.0.0.0/0", "::/0"):
        return "match"
    if remote_ip and _cidr_contains(remote, remote_ip):
        return "match"
    if not remote_ip:
        return "maybe"
    return "no"


def _rule_text(rule: dict) -> str:
    remote = (rule.get("DestCidrIp") or rule.get("SourceCidrIp")
              or "0.0.0.0/0")
    desc = str(rule.get("Description") or "")
    desc = f" desc={desc!r}" if desc else ""
    return (f"{rule.get('Direction', '?')} {rule.get('Policy', '?')} "
            f"proto={rule.get('IpProtocol', '?')} "
            f"port={rule.get('PortRange', '?')} remote={remote} "
            f"prio={rule.get('Priority', '?')}{desc}")


def _rule_sort_key(rule: dict) -> tuple:
    try:
        prio = int(rule.get("Priority") or 1)
    except (TypeError, ValueError):
        prio = 1
    # A lower priority number wins; on equal priority an explicit Drop is
    # evaluated before Accept, matching the first-match evaluation model.
    return (prio, 0 if (rule.get("Policy") or "").lower() == "drop" else 1)


def _eval_sg(rules: list, direction: str, proto: str, port: Optional[int],
             remote_ip: Optional[str]) -> dict:
    """Evaluate the first-match verdict for one direction of one group."""
    exact, maybe = [], []
    for rule in rules:
        kind = _match_rule(rule, direction, proto, port, remote_ip)
        if kind == "match":
            exact.append(rule)
        elif kind == "maybe":
            maybe.append(rule)
    ordered = sorted(exact, key=_rule_sort_key)
    if ordered:
        verdict = str(ordered[0].get("Policy") or "?")
        matched = _rule_text(ordered[0])
    else:
        # A normal-type group denies inbound unless a rule matches and allows
        # outbound unless a rule matches. Enterprise-type groups differ in
        # both directions, which is why the group type is surfaced too.
        verdict = "default-deny" if direction == "ingress" else "default-allow"
        matched = None
    return {
        "direction": direction,
        "verdict": verdict,
        "matched_rule": matched,
        "candidate_rules": [_rule_text(r) for r in maybe][:10],
    }


def _icmp_allowed(rules: list, direction: str) -> bool:
    for rule in rules:
        if (rule.get("Direction") or "").lower() != direction:
            continue
        if (rule.get("Policy") or "").lower() != "accept":
            continue
        if _proto_match(rule.get("IpProtocol", ""), "icmp"):
            return True
    return False


def _full_deny_rules(rules: list, direction: str) -> list:
    """All-protocol / all-port Drop rules spanning the whole remote space.

    The classic "an AI-generated blanket deny-all rule killed outbound" shape;
    a priority-1 all-Drop rule also shadows every other rule in that direction.
    """
    hits = []
    for rule in rules:
        if (rule.get("Direction") or "").lower() != direction:
            continue
        if (rule.get("Policy") or "").lower() != "drop":
            continue
        if not _proto_match(rule.get("IpProtocol", ""), "all"):
            continue
        if not _port_match(rule.get("PortRange", ""), None):
            continue
        remote_key = "DestCidrIp" if direction == "egress" else "SourceCidrIp"
        remote = (rule.get(remote_key) or "").strip()
        if remote in ("", "0.0.0.0/0", "::/0"):
            hits.append(_rule_text(rule))
    return hits


def snat_covers(entries: list, vswitch_id: str, own_cidr: Optional[str]) -> bool:
    """True when some SNAT entry includes this instance in its source scope."""
    for e in entries:
        if vswitch_id and str(e.get("SourceVSwitchId") or "") == vswitch_id:
            return True
        cidr = str(e.get("SourceCIDR") or "").strip()
        if cidr and own_cidr and _cidr_contains(cidr, own_cidr):
            return True
    return False


def classify_error(text: Optional[str]) -> Optional[str]:
    """Map a raw customer error string to an evidence class (never a cause)."""
    if not text:
        return None
    low = str(text).lower()
    for klass, markers in ERROR_STRING_CLASSES:
        if any(m in low for m in markers):
            return klass
    return "unrecognized"


def target_location(target: Optional[str], ip: Optional[str],
                    declared: Optional[str]) -> tuple:
    """Return (location, basis) with location in mainland|overseas|unknown."""
    if declared and declared != "unknown":
        return declared, "declared by the customer or operator"
    host = (target or ip or "").strip().lower()
    for hint in OVERSEAS_TARGET_HINTS:
        if hint in host:
            return "overseas", f"known-overseas endpoint hint: {hint}"
    if _is_private(ip):
        return "unknown", "private address range; location not derivable"
    return "unknown", "no endpoint hint matched; ask for the resolved IP"


def guest_checklist(direction: str, os_type: str, port: Optional[int],
                    target: Optional[str]) -> list:
    """Pick the in-guest state-inspection checklist for the customer."""
    src = GUEST_CHECKS_WINDOWS if os_type == "windows" else GUEST_CHECKS_LINUX
    if direction == "egress":
        keys = ["routes-dns-proxy", "guest-firewall", "live-probes-egress"]
    elif direction == "ingress":
        keys = ["listeners", "guest-firewall", "reach-arrival"]
    else:
        keys = ["listeners", "guest-firewall", "routes-dns-proxy"]
    out = []
    for key in keys:
        for line in src[key]:
            line = (line.replace("<PORT>", str(port) if port else "<PORT>")
                        .replace("<TARGET_URL>", target or "<TARGET_URL>")
                        .replace("<TARGET_IP>", target or "<TARGET_IP>"))
            out.append({"group": key, "command": line})
    return out


# ---------------------------------------------------------------------------
# Degraded-query wrapper
# ---------------------------------------------------------------------------

_PERMISSION_HINTS = ("nopermission", "implicitdeny", "accessdenied",
                     "not authorized", "unauthorized", "invalidaccesskeyid",
                     "signaturedoesnotmatch")


def _query(name: str, fn, errors: list) -> Any:
    """Run one cloud query; on failure log [WARN|DEGRADE] and record it.

    A failing query never aborts the whole diagnosis: the missing evidence is
    declared in the report and the run degrades to STATUS: DEGRADED.
    """
    try:
        return fn()
    except _cli.CliError as e:
        low = f"{e.code} {e}".lower()
        if any(h in low for h in _PERMISSION_HINTS):
            category = "permission"
        elif any(h in low for h in ("invalidparameter", "missingparameter",
                                    "notfound", "invalidinstanceid",
                                    "nosuch")):
            category = "parameter"
        else:
            category = "internal"
        print(f"[WARN|DEGRADE] {name}: {e}", file=sys.stderr)
        errors.append({
            "query": name,
            "category": category,
            "code": e.code or "",
            "detail": str(e)[:300],
        })
        return None


# ---------------------------------------------------------------------------
# Main diagnosis
# ---------------------------------------------------------------------------

def collect_missing(args: argparse.Namespace) -> list:
    """D0 gate: return ONLY the inputs that are missing or malformed."""
    missing = []
    if not args.region_id:
        missing.append("region-id (the region of the instance under "
                       "diagnosis; every query is region-scoped)")
    elif not _REGION_RE.match(args.region_id):
        missing.append(f"region-id {args.region_id!r} is not a valid region id")
    if not (args.instance_id or args.private_ip or args.public_ip):
        missing.append("instance locator (instance ID, private IP or public "
                       "IP)")
    if args.instance_id and not _INSTANCE_ID_RE.match(args.instance_id):
        missing.append(f"instance-id {args.instance_id!r} should look like "
                       "i-<alphanumeric>")
    for value, label in ((args.private_ip, "private-ip"),
                         (args.public_ip, "public-ip"),
                         (args.target_ip, "target-ip"),
                         (args.peer_ip, "peer-ip"),
                         (args.client_ip, "client-ip")):
        if value and not _is_ip(value):
            missing.append(f"{label} {value!r} is not a valid IP address")
    if args.port is not None and not (1 <= args.port <= 65535):
        missing.append("port must be between 1 and 65535")
    if not args.direction:
        missing.append("direction: egress (instance -> outside), ingress "
                       "(outside -> instance port) or internal (instance "
                       "<-> instance)")
    elif args.direction == "egress" and not (args.target or args.target_ip):
        missing.append("target (the domain or URL the instance cannot reach)")
    elif args.direction == "ingress" and args.port is None:
        missing.append("port that the outside client cannot connect to")
    elif args.direction == "internal" and not (args.peer_instance_id
                                               or args.peer_ip):
        missing.append("peer instance ID or peer IP for the mutual-access "
                       "check")
    return missing


def run(args: argparse.Namespace) -> tuple:
    """Execute the diagnosis. Returns (report dict, status, exit code)."""
    errors: list = []
    findings: list = []
    auto_filled: dict = {}
    warnings: list = []
    # Set when the cloud-side evidence alone explains the failure.
    config_block = False

    missing = collect_missing(args)
    if missing:
        return ({
            "missing_input": missing,
            "verdict": "NEED-INPUT",
            "attribution": "undetermined",
            "ask_user": ("Ask the customer for exactly these missing items; "
                         "never guess them."),
        }, "FAIL", 1)

    # ---- D1 identity + instance locator -----------------------------
    identity = _query("sts GetCallerIdentity",
                      lambda: _cli.call("sts", "GetCallerIdentity", {},
                                        region=args.region_id),
                      errors)
    account_uid = str((identity or {}).get("AccountId") or "")
    if not account_uid:
        print("[ERROR] caller identity unavailable, so there is no account "
              "baseline for the ownership check. Repair the CLI default "
              "credential chain (`aliyun sts get-caller-identity`); never pass key "
              "material to this skill.", file=sys.stderr)
        return ({"error": "credential chain unavailable",
                 "verdict": "UNDETERMINED",
                 "attribution": "undetermined"}, "FAIL", 2)

    def _find_instance():
        params: dict = {"RegionId": args.region_id}
        if args.instance_id:
            params["InstanceIds"] = json.dumps([args.instance_id])
        elif args.private_ip:
            params["PrivateIpAddresses"] = args.private_ip
        elif args.public_ip:
            params["PublicIpAddresses"] = args.public_ip
        items = _cli.paginate("ecs", "DescribeInstances", params,
                              ["Instances", "Instance"],
                              total_path=["TotalCount"], region=args.region_id)
        return items[0] if items else None

    inst = _query("ecs DescribeInstances (target)", _find_instance, errors)
    if inst is None and errors:
        return ({"account_uid": account_uid, "errors": errors,
                 "verdict": "UNDETERMINED",
                 "attribution": "undetermined",
                 "conclusion": "the queries failed before any evidence could "
                               "be read"}, "FAIL", 1)
    if not inst:
        # Ownership split -- the top mis-routing cause seen in tickets.
        return ({
            "account_uid": account_uid,
            "instance": None,
            "attribution": "ownership",
            "verdict": "OUT-OF-SCOPE",
            "handoff_target": "the owning account, or the customer's own "
                              "network team",
            "findings": [
                f"No ECS instance matched the locator in region "
                f"{args.region_id} under account {account_uid}."],
            "conclusion": (
                "The address is NOT an ECS instance of the CURRENT account. "
                "Either it belongs to another Alibaba Cloud account (re-open "
                "the case with that account's credential: this skill cannot "
                "read cross-account resources) or it is not an Alibaba Cloud "
                "asset at all (customer IDC, another provider, office "
                "network) -- diagnose locally there instead."),
            "next_steps": [
                "Ask the customer who owns the machine and where it actually "
                "runs.",
                "If Alibaba Cloud but another account: have the owning "
                "account run this diagnosis.",
                "If not Alibaba Cloud: hand off to the customer's own network "
                "and host-firewall check (references/intranet-egress__handoff-matrix.md)."],
            "errors": errors,
        }, "OK", 0)

    region = str(inst.get("RegionId") or args.region_id)
    auto_filled["region (taken from the located instance)"] = region
    cloud_state = str(inst.get("Status") or "Unknown")
    os_type = str(inst.get("OSType") or "unknown").lower()
    vpc_attrs = inst.get("VpcAttributes") or {}
    vpc_id = str(vpc_attrs.get("VpcId") or "")
    vswitch_id = str(vpc_attrs.get("VSwitchId") or "")
    private_ips = ((vpc_attrs.get("PrivateIpAddress") or {})
                   .get("IpAddress") or [])
    eip = str((inst.get("EipAddress") or {}).get("IpAddress") or "")
    public_ips = ((inst.get("PublicIpAddress") or {}).get("IpAddress") or [])
    pub_ips = list(public_ips) + ([eip] if eip else [])
    sg_ids = [str(x) for x in ((inst.get("SecurityGroupIds") or {})
                               .get("SecurityGroupId") or [])]
    bw_out = inst.get("InternetMaxBandwidthOut")
    has_public = bool(pub_ips)
    mainland = is_mainland_region(region)

    instance_facts = {
        "instance_id": inst.get("InstanceId"),
        "instance_name": inst.get("InstanceName"),
        "status": cloud_state,
        "region": region,
        "region_class": "mainland" if mainland else "overseas",
        "os_type": os_type,
        "network_type": inst.get("InstanceNetworkType"),
        "vpc_id": vpc_id,
        "vswitch_id": vswitch_id,
        "private_ips": private_ips,
        "public_ips": pub_ips,
        "security_groups": sg_ids,
        "security_group_types": [
            str(x) for x in ((inst.get("SecurityGroupTypes") or {})
                             .get("SecurityGroupType") or [])],
        "internet_max_bandwidth_out": bw_out,
    }
    if cloud_state != "Running":
        config_block = True
        findings.append(
            f"Instance state is {cloud_state}, not Running: no network path "
            "can work while the instance is stopped or transitioning. Resolve "
            "the instance state first "
            f"({HANDOFF_SKILLS['instance-state']}).")

    # ---- D2 direction + target normalization ------------------------
    direction = args.direction
    target_host = args.target or args.target_ip or args.peer_ip or ""
    err_class = classify_error(args.error_text)
    location, loc_basis = target_location(
        args.target, args.target_ip or args.peer_ip, args.target_location)
    remote_ip = args.client_ip if direction == "ingress" else (
        args.target_ip or (args.peer_ip if _is_ip(args.peer_ip) else None))
    proto = (args.protocol or "tcp").lower()

    # ---- D3 cloud-side reads ----------------------------------------
    sg_results = []
    for sg_id in sg_ids[:5]:
        rules = _query(
            f"ecs DescribeSecurityGroupAttribute {sg_id}",
            lambda sg=sg_id: _cli.paginate(
                "ecs", "DescribeSecurityGroupAttribute",
                {"RegionId": region, "SecurityGroupId": sg},
                ["Permissions", "Permission"], mode="token", region=region),
            errors) or []
        entry: dict = {"security_group_id": sg_id, "rule_count": len(rules)}
        if direction == "egress":
            entry["egress_probe"] = _eval_sg(rules, "egress", proto,
                                             args.port, remote_ip)
            entry["egress_full_deny_rules"] = _full_deny_rules(rules, "egress")
        else:
            entry["ingress_probe"] = _eval_sg(rules, "ingress", proto,
                                              args.port, remote_ip)
            entry["ingress_full_deny_rules"] = _full_deny_rules(rules,
                                                                "ingress")
        # ICMP matters in every direction: "ping fails" is the most common
        # red herring on both sides of a connection.
        entry["ingress_icmp_accept"] = _icmp_allowed(rules, "ingress")
        entry["egress_icmp_accept"] = _icmp_allowed(rules, "egress")
        sg_results.append(entry)

    vswitches, route_tables, nat_gateways, snat_entries = [], [], [], []
    if vpc_id:
        vswitches = _query(
            "vpc DescribeVSwitches",
            lambda: _cli.paginate("vpc", "DescribeVSwitches",
                                  {"RegionId": region, "VpcId": vpc_id},
                                  ["VSwitches", "VSwitch"],
                                  total_path=["TotalCount"], region=region),
            errors) or []
        route_tables = _query(
            "vpc DescribeRouteTableList",
            lambda: _cli.paginate("vpc", "DescribeRouteTableList",
                                  {"RegionId": region, "VpcId": vpc_id},
                                  ["RouterTableList", "RouterTableListType"],
                                  total_path=["TotalCount"], region=region),
            errors) or []
        nat_gateways = _query(
            "vpc DescribeNatGateways",
            lambda: _cli.paginate("vpc", "DescribeNatGateways",
                                  {"RegionId": region, "VpcId": vpc_id},
                                  ["NatGateways", "NatGateway"],
                                  total_path=["TotalCount"], region=region),
            errors) or []
        for nat in [n for n in nat_gateways
                    if str(n.get("Status") or "").lower() == "available"][:2]:
            entries = _query(
                f"vpc DescribeSnatTableEntries {nat.get('NatGatewayId')}",
                lambda nid=nat.get("NatGatewayId"): _cli.paginate(
                    "vpc", "DescribeSnatTableEntries",
                    {"RegionId": region, "NatGatewayId": nid},
                    ["SnatTableEntries", "SnatTableEntry"],
                    total_path=["TotalCount"], region=region),
                errors) or []
            snat_entries.extend(entries)
    else:
        warnings.append(
            "The located instance reports no VpcId, so the VPC-side queries "
            "(VSwitch, route table, NAT, SNAT) were skipped and the cloud "
            "egress path is only partly verified.")

    # ---- cloud-path findings ----------------------------------------
    nat_available = [n for n in nat_gateways
                     if str(n.get("Status") or "").lower() == "available"]
    own_cidr = private_ips[0] if private_ips else None
    has_snat = snat_covers(snat_entries, vswitch_id, own_cidr)
    vswitch_cidrs = {str(v.get("VSwitchId")): str(v.get("CidrBlock"))
                     for v in vswitches if v.get("VSwitchId")}

    if direction == "egress":
        if not has_public and not nat_available:
            config_block = True
            findings.append(
                "The instance has no public IP/EIP and the VPC has no "
                "Available NAT gateway: outbound internet traffic has no "
                "cloud-side egress path at all. Creating a NAT gateway or "
                "associating an EIP is a change and billing decision made by "
                "the resource owner in the console; this skill never does it.")
        elif not has_public and nat_available and not has_snat:
            config_block = True
            findings.append(
                f"A NAT gateway exists but no SNAT entry covers VSwitch "
                f"{vswitch_id} or the instance address {own_cidr}: egress "
                "through NAT will fail for this instance.")
        elif has_public and bw_out == 0 and not eip:
            config_block = True
            findings.append(
                "The instance has a fixed public address but its outbound "
                "bandwidth is 0 Mbps, so no traffic can leave even though the "
                "address exists. Verify the bandwidth specification in the "
                "console.")
        for sg in sg_results:
            deny = sg.get("egress_full_deny_rules") or []
            probe = sg.get("egress_probe") or {}
            if deny:
                config_block = True
                findings.append(
                    f"Security group {sg['security_group_id']} contains "
                    f"ALL-protocol DROP rule(s): {deny}. That is the shape of "
                    "a copied or AI-generated blanket deny-out rule; the "
                    "customer should remove it in the console (this skill "
                    "never edits rules).")
            elif str(probe.get("verdict", "")).lower() == "drop":
                config_block = True
                findings.append(
                    f"The outbound probe hits an explicit Drop rule in "
                    f"{sg['security_group_id']}: {probe.get('matched_rule')}")
        if not config_block:
            findings.append(
                "Cloud-side egress configuration shows no blocking finding. "
                "A normal-type group allows outbound by default while an "
                "enterprise-type group does not, so confirm the group type in "
                "the console before concluding the cloud side is clean.")
    elif direction == "ingress":
        allow = [sg for sg in sg_results
                 if str((sg.get("ingress_probe") or {}).get("verdict", "")
                        ).lower() == "accept"]
        drop = [sg for sg in sg_results
                if str((sg.get("ingress_probe") or {}).get("verdict", "")
                       ).lower() == "drop"]
        if drop:
            config_block = True
            findings.append(
                "The inbound probe hits an explicit Drop rule: "
                + "; ".join(str((sg.get("ingress_probe") or {}).get(
                    "matched_rule")) for sg in drop))
        elif not allow and sg_results:
            config_block = True
            findings.append(
                "No security-group INGRESS rule accepts the probed "
                "protocol/port"
                + (f" from {remote_ip}" if remote_ip else "")
                + "; unmatched inbound traffic is dropped silently. That "
                "explains a SYN that never answers (a timeout), but NOT an "
                "immediate connection reset.")
        if not has_public and not eip:
            config_block = True
            findings.append(
                "The instance has no public IP/EIP, so an outside client "
                "cannot reach it directly at all. Port forwarding or an EIP "
                "are console change decisions for the resource owner.")
        if allow and err_class == "timeout" and location == "overseas" \
                and not mainland:
            findings.append(
                "Ingress rules accept the traffic, so the next question is "
                "where the client sits: clients on the Chinese mainland "
                "reaching an instance in an overseas region cross carrier "
                "international exits, and timeouts there commonly originate "
                "OUTSIDE the cloud.")
        if err_class == "timeout" and sg_results and not any(
                sg.get("ingress_icmp_accept") for sg in sg_results):
            findings.append(
                "ICMP is accepted by no group, so a failed ping is EXPECTED "
                "and proves nothing about TCP reachability. Judge the actual "
                "port probe instead -- this single point reverses a frequent "
                "misdiagnosis.")
    else:  # internal
        same_vpc = True
        if args.peer_instance_id:
            def _find_peer():
                items = _cli.paginate(
                    "ecs", "DescribeInstances",
                    {"RegionId": region,
                     "InstanceIds": json.dumps([args.peer_instance_id])},
                    ["Instances", "Instance"], total_path=["TotalCount"],
                    region=region)
                return items[0] if items else None
            peer = _query("ecs DescribeInstances (peer)", _find_peer, errors)
            if not peer:
                config_block = False
                findings.append(
                    f"Peer instance {args.peer_instance_id} was not found in "
                    f"region {region} under this account. A cross-region or "
                    "cross-account peer cannot be diagnosed from here, and "
                    "cross-VPC or cross-region interconnect design belongs to "
                    f"{HANDOFF_SKILLS['general-network']}.")
                same_vpc = False
            else:
                peer_vpc = str(((peer.get("VpcAttributes") or {})
                                .get("VpcId") or ""))
                same_vpc = bool(vpc_id) and peer_vpc == vpc_id
                if not same_vpc:
                    config_block = True
                    findings.append(
                        f"The two instances sit in DIFFERENT VPCs "
                        f"({vpc_id} vs {peer_vpc}): plain private addresses "
                        "cannot route between VPCs. Interconnect product "
                        f"selection belongs to "
                        f"{HANDOFF_SKILLS['general-network']}, not to this "
                        "skill.")
        if args.peer_ip and not _is_private(args.peer_ip):
            findings.append(
                f"Peer {args.peer_ip} is not a private address: this is an "
                "internet path, re-run with --direction egress.")
        elif args.peer_ip and vswitch_cidrs:
            peer_in_vpc = any(_cidr_contains(cidr, args.peer_ip)
                              for cidr in vswitch_cidrs.values())
            if not peer_in_vpc:
                config_block = True
                findings.append(
                    f"Peer {args.peer_ip} falls outside every VSwitch CIDR of "
                    f"VPC {vpc_id} ({sorted(vswitch_cidrs.values())}): either "
                    "the peer sits in another network, or a guest-side route "
                    "and policy-route check is required.")
        allow_ingress = any(str((sg.get("ingress_probe") or {}).get(
            "verdict", "")).lower() == "accept" for sg in sg_results)
        if same_vpc and sg_results and not allow_ingress:
            config_block = True
            findings.append(
                "Same VPC, but no ingress rule accepts the probed "
                "protocol/port from the peer address or peer group, so "
                "private traffic is dropped by the security group. Authorize "
                "the peer CIDR or the peer group in the console (a change "
                "decision of the resource owner).")
        if route_tables:
            findings.append(
                f"VPC {vpc_id} has {len(route_tables)} route table(s); the "
                "per-entry next-hop detail is not exposed by this query, so "
                "the guest-side 'ip route show' and 'ip rule show' items in "
                "the manual checklist are what close that gap. With more than "
                "one network interface, asymmetric return-path routing is a "
                "known cause of 'can send, cannot receive'.")
        findings.append(
            f"VSwitch CIDR map: {json.dumps(vswitch_cidrs, sort_keys=True)}")

    # ---- D4 target geography branch ---------------------------------
    cross_border = location == "overseas" and (
        (mainland and direction == "egress")
        or (not mainland and direction == "ingress"))
    cross_basis = None
    if direction == "egress" and mainland and location == "unknown" \
            and err_class in (None, "timeout"):
        warnings.append(
            "Target location is unknown. Use the checklist item that resolves "
            "the name to read the real IP, or pass --target-location, before "
            "attributing anything to the link.")
    if cross_border:
        cross_basis = (f"instance region {region} (mainland={mainland}) vs "
                       f"target '{target_host}' ({loc_basis})")

    # ---- attribution + verdict --------------------------------------
    attribution = "undetermined"
    verdict = "UNDETERMINED"
    handoff = None
    handoff_target = None
    next_steps: list = []

    if config_block:
        attribution = "cloud-config"
        verdict = "RESOLVED-POINTED"
        next_steps.append(
            "Have the resource owner correct the pointed configuration item in "
            "the ECS/VPC console. This skill never edits security groups, "
            "routes, SNAT entries, EIPs or addresses; re-run it afterwards to "
            "verify the change took effect.")
    elif direction == "egress" and cross_border:
        attribution = "external-link"
        verdict = "RESOLVED-POINTED"
        findings.append("Cross-border branch selected: "
                        + (cross_basis or "no basis computed"))
        next_steps.extend([
            "Explain the boundary: mainland-to-overseas traffic (or the "
            "reverse) crosses carrier international exits, so timeouts there "
            "are typically NOT an instance fault. Reaching a domestic "
            "endpoint is the fastest way to demonstrate the asymmetry.",
            "Offer options for the customer to evaluate: a domestic "
            "mirror/endpoint, a relay instance in a nearby region, or an "
            "acceleration product for endpoints the customer owns. Each is a "
            "console change with its own billing -- see "
            "references/intranet-egress__cross-border-and-blockage.md.",
            "Hard boundary: acceleration cannot front a closed third-party "
            "SaaS whose server endpoints the customer does not control (GitHub "
            "or GitLab SaaS, for example). Never promise otherwise.",
        ])
    elif err_class == "reset" and direction == "ingress":
        attribution = "external-carrier"
        verdict = "NEED-HUMAN"
        next_steps.extend([
            "Collect the client's egress public IP and carrier region -- the "
            "customer opens http://cip.cc from the FAILING client machine, not "
            "from the instance -- plus a screenshot of the error that includes "
            "the address bar.",
            "Compare reachability from another province or carrier. A reset "
            "seen only from one region across several carriers points at "
            "regional carrier-level blocking; the cloud can neither confirm "
            "nor lift that, and the customer contacts the carrier.",
        ])
        warnings.append(
            "A reset is produced by SOME endpoint or middlebox, so the packet "
            "arrives somewhere. Do not name a specific blocker without the "
            "regional comparison evidence above.")
    elif err_class == "refused" or "403" in (args.error_text or "") \
            or "502" in (args.error_text or ""):
        attribution = "application-layer"
        verdict = "OUT-OF-SCOPE"
        handoff = ("the connection was actively rejected or answered with an "
                   "HTTP status, so it reached the instance. Refusal semantics "
                   "and status codes are application-layer topics (service "
                   "bind, virtual host, file permissions, missing index file) "
                   "and sit outside this skill")
        handoff_target = "the application / web service owner"
    elif err_class == "proxy-path":
        attribution = "guest-config"
        verdict = "NEED-HUMAN"
        next_steps.append(
            "A proxy error code only says the browser's proxy path failed. "
            "Have the customer confirm the guest and browser proxy settings "
            "from the checklist (env | grep -i proxy; netsh winhttp show "
            "proxy). Make no root-cause claim without that output.")
    elif not errors and sg_results:
        attribution = "guest-config-or-external"
        verdict = "UNDETERMINED"
        next_steps.append(
            "The cloud-side evidence is clean so far, so the deciding "
            "evidence now lives INSIDE the instance: host firewall state, "
            "listener bind address, in-guest probe results, and whether the "
            "request appears in the service log. Send the checklist below to "
            "the customer and continue interpretation from the pasted plain "
            "text.")
    if direction == "ingress" and err_class == "timeout" and not config_block:
        handoff_target = handoff_target or (
            "a support ticket, for platform-side states with no query entry")
        next_steps.append(
            "If everything above checks out yet reachability still fails from "
            "many places: platform-side states such as anti-DDoS blackhole or "
            "cleaning status, and underlying host incidents, have no public "
            "query entry point. Escalate to a support ticket WITH the "
            "evidence bundle this report produced "
            "(references/intranet-egress__handoff-matrix.md).")

    report = {
        "account_uid": account_uid,
        "instance": instance_facts,
        "probe": {
            "direction": direction,
            "target": target_host or None,
            "port": args.port,
            "protocol": proto,
            "remote_ip": remote_ip,
            "target_location": location,
            "location_basis": loc_basis,
            "error_class": err_class,
            "error_text": args.error_text or None,
            "client_location": args.client_location or None,
        },
        "security_groups": sg_results,
        "vpc": {
            "vswitches": [
                {"id": v.get("VSwitchId"), "cidr": v.get("CidrBlock"),
                 "zone": v.get("ZoneId")} for v in vswitches],
            "route_tables": [
                {"id": t.get("RouteTableId"), "type": t.get("RouteTableType"),
                 "router": t.get("RouterType")} for t in route_tables],
            "nat_gateways": [
                {"id": n.get("NatGatewayId"), "status": n.get("Status"),
                 "type": n.get("NatType")} for n in nat_gateways],
            "snat_entries": [
                {"id": e.get("SnatEntryId"),
                 "vswitch": e.get("SourceVSwitchId"),
                 "cidr": e.get("SourceCIDR"), "snat_ip": e.get("SnatIp"),
                 "status": e.get("Status")} for e in snat_entries],
        },
        "findings": findings,
        "next_steps": next_steps,
        "attribution": attribution,
        "verdict": verdict,
        "handoff": handoff,
        "handoff_target": handoff_target,
        "guest_checklist_manual": guest_checklist(direction, os_type,
                                                 args.port,
                                                 target_host or None),
        "guest_checklist_note": (
            "Automatic in-guest execution is CLOSED by default: these "
            "commands are printed for the customer to run inside the instance "
            "and paste back as plain text (never screenshots, never "
            "credentials)."),
        "domestic_alternatives": (
            DOMESTIC_ALTERNATIVES
            if (cross_border or (mainland and location == "unknown"))
            else []),
        "auto_filled": auto_filled,
        "warnings": warnings,
        "errors": errors,
    }
    status = "DEGRADED" if errors else "OK"
    return (report, status, 0)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render(report: dict) -> str:
    """Render the machine report as the customer-facing text report."""
    lines = []
    lines.append("=" * 68)
    lines.append("ECS CONNECTIVITY DIAGNOSIS REPORT (intranet / egress)")
    lines.append("=" * 68)
    lines.append("Account UID (auto-derived via sts get-caller-identity): "
                 f"{report.get('account_uid')}")
    inst = report.get("instance")
    if inst:
        lines.append(
            f"Instance        : {inst.get('instance_id')} | state "
            f"{inst.get('status')} | region {inst.get('region')} "
            f"({inst.get('region_class')}) | OS {inst.get('os_type')}")
        lines.append(
            f"Network         : vpc={inst.get('vpc_id')} "
            f"vswitch={inst.get('vswitch_id')} "
            f"private={','.join(inst.get('private_ips') or []) or '-'} "
            f"public={','.join(inst.get('public_ips') or []) or '-'}")
        lines.append(
            "Security groups : "
            f"{', '.join(inst.get('security_groups') or [])}")
    probe = report.get("probe") or {}
    if probe:
        lines.append(
            f"Probe           : direction={probe.get('direction')} "
            f"target={probe.get('target') or '-'} "
            f"port={probe.get('port') or '-'} proto={probe.get('protocol')} "
            f"target-location={probe.get('target_location')} "
            f"error-class={probe.get('error_class') or '-'}")
    for sg in report.get("security_groups") or []:
        lines.append(f"\nSecurity group {sg.get('security_group_id')} "
                     f"({sg.get('rule_count')} rule(s) read back)")
        for key in ("ingress_probe", "egress_probe"):
            p = sg.get(key)
            if p:
                lines.append(f"  {key:15s} : verdict={p.get('verdict')} "
                             f"rule={p.get('matched_rule') or '-'}")
                for cand in p.get("candidate_rules") or []:
                    lines.append(f"    candidate (remote CIDR pinned): {cand}")
        for key in ("ingress_full_deny_rules", "egress_full_deny_rules"):
            for hit in sg.get(key) or []:
                lines.append(f"  BLANKET DROP    : {hit}")
    vpc = report.get("vpc")
    if vpc:
        lines.append("\nVPC path")
        lines.append(f"  VSwitches    : {vpc.get('vswitches')}")
        lines.append(f"  Route tables : {vpc.get('route_tables')}")
        lines.append(f"  NAT gateways : {vpc.get('nat_gateways')}")
        lines.append(f"  SNAT entries : {vpc.get('snat_entries')}")
    if report.get("findings"):
        lines.append("\nFindings")
        for f in report["findings"]:
            lines.append(f"  - {f}")
    if report.get("missing_input"):
        lines.append("\nMissing input (ask the customer for EXACTLY these)")
        for m in report["missing_input"]:
            lines.append(f"  - {m}")
    if report.get("guest_checklist_manual"):
        lines.append("\nIn-guest checks for the CUSTOMER to run (paste back "
                     "plain text; never share credentials)")
        for item in report["guest_checklist_manual"]:
            lines.append(f"  [{item['group']}] $ {item['command']}")
    if report.get("domestic_alternatives"):
        lines.append("\nOptions the customer may evaluate for a cross-border "
                     "path (console change decisions, billed per the provider "
                     "catalog; this skill executes none)")
        for d in report["domestic_alternatives"]:
            lines.append(f"  - {d}")
    if report.get("handoff"):
        lines.append(f"\nHandoff: {report['handoff']}")
    if report.get("handoff_target"):
        lines.append(f"Handoff target: {report['handoff_target']}")
    if report.get("next_steps"):
        lines.append("\nNext steps")
        for i, s in enumerate(report["next_steps"], 1):
            lines.append(f"  {i}. {s}")
    lines.append("\n## Degradation log")
    if report.get("errors"):
        for e in report["errors"]:
            lines.append(f"  - query {e['query']}: category={e['category']} "
                         f"code={e['code'] or '-'} ({e['detail'][:120]})")
    else:
        lines.append("  - none")
    if report.get("warnings"):
        lines.append("\nWarnings")
        for w in report["warnings"]:
            lines.append(f"  - {w}")
    if report.get("conclusion"):
        lines.append(f"\nConclusion: {report['conclusion']}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ecs_connectivity_diagnose.py",
        description=("Direction-aware ECS connectivity diagnosis "
                     "(non-mutating cloud queries plus a manual in-guest "
                     "checklist)"),
    )
    p.add_argument("--region-id", required=True,
                   help="region of the instance under diagnosis, e.g. "
                        "cn-hangzhou")
    loc = p.add_argument_group("instance locator (at least one)")
    loc.add_argument("--instance-id", help="ECS instance ID (i-...)")
    loc.add_argument("--private-ip", help="instance private IP, as locator")
    loc.add_argument("--public-ip", help="instance public IP or EIP, as "
                                         "locator")
    p.add_argument("--direction", choices=["egress", "ingress", "internal"],
                   help="fault direction: egress=instance to outside, "
                        "ingress=outside to instance port, "
                        "internal=instance to instance")
    p.add_argument("--target", help="domain or URL reported as failing")
    p.add_argument("--target-ip", help="resolved IP of the target, if known")
    p.add_argument("--peer-instance-id", help="peer instance ID for "
                                              "--direction internal")
    p.add_argument("--peer-ip", help="peer private IP for "
                                     "--direction internal")
    p.add_argument("--client-ip", help="public IP of the outside client for "
                                       "--direction ingress; lets a rule "
                                       "match pin a specific CIDR")
    p.add_argument("--port", type=int, help="target port (required for the "
                                            "ingress and internal probes)")
    p.add_argument("--protocol", choices=["tcp", "udp", "icmp"],
                   help="probe protocol; defaults to tcp")
    p.add_argument("--target-location", choices=["mainland", "overseas",
                                                 "unknown"],
                   help="where the target endpoint sits (customer-declared or "
                        "operator-verified)")
    p.add_argument("--client-location", help="client province/city and "
                                             "carrier, used by the reset and "
                                             "regional analysis")
    p.add_argument("--error-text", help="raw customer error string, mapped to "
                                        "an evidence class")
    p.add_argument("--json", action="store_true", help="emit machine JSON")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    _cli.check_cli_available()

    report, status, code = run(args)

    if args.json:
        report["status"] = status
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    else:
        print(render(report))
    print(f"\nSTATUS: {status}")
    print(f"VERDICT: {report.get('verdict', 'UNDETERMINED')}")
    print(f"ATTRIBUTION: {report.get('attribution', 'undetermined')}")
    na = (report.get("next_steps") or report.get("ask_user")
          or report.get("conclusion")
          or ["read references/intranet-egress__diagnosis-decision-tree.md"])
    print(f"NEXT_ACTION: {str(na[0])[:200]}")
    sys.exit(code)


# ---------------------------------------------------------------------------
# Inline boundary assertions for the pure decision functions (normal,
# boundary and invalid inputs). Executed at import time.
# ---------------------------------------------------------------------------
assert _is_ip("10.0.0.1") and not _is_ip("example.com") and not _is_ip(None)
assert _is_private("192.168.1.7") and not _is_private("8.8.8.8")
assert not _is_private(None)
assert _norm_port("-1/-1", 443) == (443, 443)
assert _norm_port("80/80", 22) == (80, 80)
assert _norm_port("bogus", 22) == (22, 22)   # invalid range falls back to -1/-1 (any), then collapses to `want`
assert _norm_port(None, None) == (1, 65535)
assert _port_match("443/443", 443) and not _port_match("443/443", 80)
assert _port_match("-1/-1", 22) and _port_match("1/1024", 80)
assert _port_match("1/65535", None)
assert _proto_match("-1", "tcp") and _proto_match("tcp", "tcp")
assert not _proto_match("udp", "tcp")
assert not _proto_match("", "tcp")
assert _cidr_contains("0.0.0.0/0", "8.8.8.8")
assert _cidr_contains("10.0.0.0/8", "10.1.2.3")
assert not _cidr_contains("10.0.0.0/8", "192.168.1.1")
assert not _cidr_contains("10.0.0.0/8", None)
assert not _cidr_contains("", "8.8.8.8")
_drop_all = {
    "Direction": "egress", "Policy": "Drop", "IpProtocol": "-1",
    "PortRange": "-1/-1", "DestCidrIp": "0.0.0.0/0", "Priority": "1",
}
_accept_443 = {
    "Direction": "ingress", "Policy": "Accept", "IpProtocol": "tcp",
    "PortRange": "443/443", "SourceCidrIp": "0.0.0.0/0", "Priority": "1",
}
assert _eval_sg([_drop_all], "egress", "tcp", 443, "1.2.3.4")["verdict"] \
    == "Drop"
assert _eval_sg([], "ingress", "tcp", 443, None)["verdict"] == "default-deny"
assert _eval_sg([], "egress", "tcp", 443, None)["verdict"] == "default-allow"
assert _eval_sg([_accept_443], "ingress", "tcp", 443, None)["verdict"] \
    == "Accept"
assert _eval_sg([_accept_443], "ingress", "tcp", 443, None)["matched_rule"]
assert _eval_sg([_drop_all], "egress", "tcp", 443, "1.2.3.4")["matched_rule"]
# A pinned CIDR with an unknown remote IP is a candidate, never a verdict.
_pinned = dict(_accept_443, SourceCidrIp="203.0.113.0/24")
_maybe = _eval_sg([_pinned], "ingress", "tcp", 443, None)
assert _maybe["verdict"] == "default-deny" and _maybe["candidate_rules"]
assert _eval_sg([_pinned], "ingress", "tcp", 443, "203.0.113.9")["verdict"] \
    == "Accept"
assert _eval_sg([_pinned], "ingress", "tcp", 443, "198.51.100.9")["verdict"] \
    == "default-deny"
assert _full_deny_rules([_drop_all], "egress")
assert not _full_deny_rules([_accept_443], "ingress")
assert not _full_deny_rules([], "egress")
assert _icmp_allowed([{"Direction": "ingress", "Policy": "Accept",
                       "IpProtocol": "-1", "PortRange": "-1/-1",
                       "SourceCidrIp": "0.0.0.0/0", "Priority": "2"}],
                     "ingress")
assert not _icmp_allowed([_accept_443], "ingress")
assert not snat_covers([], "vsw-abc", "10.0.0.5")
assert snat_covers([{"SourceVSwitchId": "vsw-abc"}], "vsw-abc", None)
assert snat_covers([{"SourceCIDR": "10.0.1.0/24"}], "vsw-zzz", "10.0.1.9")
assert not snat_covers([{"SourceCIDR": "10.0.1.0/24"}], "vsw-zzz", "10.9.9.9")
assert not snat_covers([{}], "vsw-abc", "10.0.0.5")
assert classify_error("dial tcp 8.8.8.8:22: i/o timeout") == "timeout"
assert classify_error("curl: (28) Operation timed out after 10000 ms") \
    == "timeout"
assert classify_error("ERR_CONNECTION_RESET") == "reset"
assert classify_error("this site can't be reached err_timed_out") == "reset"
assert classify_error("err_proxy_connection_failed") == "proxy-path"
assert classify_error("Connection refused") == "refused"
assert classify_error("HTTP 403 returned by the origin") == "unrecognized"
assert classify_error("something else entirely") == "unrecognized"
assert classify_error(None) is None
assert target_location("https://github.com/x", None, None)[0] == "overseas"
assert target_location(None, "10.0.0.1", "mainland")[0] == "mainland"
assert target_location(None, None, None)[0] == "unknown"
assert target_location(None, "10.0.0.1", None)[1].startswith("private")
_egl = guest_checklist("egress", "linux", 443, "example.org")
assert len(_egl) >= 5
assert all("<PORT>" not in i["command"] for i in _egl)
assert guest_checklist("ingress", "windows", 3389, None)
assert guest_checklist("internal", "linux", None, None)


if __name__ == "__main__":
    main()
