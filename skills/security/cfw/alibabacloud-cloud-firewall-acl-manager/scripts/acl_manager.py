#!/usr/bin/env python3
"""ACL policy management engine - query/analysis + single-point changes

Read-only subcommands (zero risk):
  hit     Hit analysis: sort by hit count, identify zero-hit policies
  dup     Duplicate rule detection: duplicate policies with identical signatures
  shadow  Shadow rule detection: policies fully covered by a preceding broader rule that will never be hit
  audit   Compliance inspection: check high-risk allow patterns and output the inspection report

Write subcommands (Plan-First two-phase confirmation):
  add     Add a single policy (--boundary internet/nat/vpc, --dry-run only shows the plan)
  switch  Enable/disable a single policy (Release switch, three boundaries)

Boundary note: this module does not provide delete/cleanup capability; please clean up policies manually in the console.
"""
import argparse
import ipaddress
import json
import os
import sys
from datetime import datetime

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import BackupEngine, call_api, load_default_credentials  # noqa: E402
from acl_policy import get_plugins  # noqa: E402

# High-risk port list (value format: service name | brief risk description)
# Source: security practice references such as the cnblogs article "Common High-Risk Ports" (cnblogs.com/yjiejie/p/18405794);
# common ports like 53(DNS), 80/443/8080 are deliberately excluded to avoid false positives on system default rules / normal web traffic.
HIGH_RISK_PORTS = {
    # ---- Remote management services ----
    "20": "FTP data port | anonymous upload/download, sniffing",
    "21": "FTP | anonymous access, brute force, sniffing, historical RCE vulnerabilities",
    "22": "SSH | brute force, v1 MITM, tunnel forwarding / intranet proxy",
    "23": "Telnet | plaintext transmission, brute force, weak passwords",
    "69": "TFTP | no authentication, sensitive config files can be downloaded",
    "512": "Linux rexec | unauthenticated remote execution, brute force",
    "513": "Linux rlogin | unauthenticated remote login, brute force",
    "514": "Linux rsh/syslog | unauthenticated remote command execution",
    "873": "Rsync | anonymous access, unauthorized file upload/download",
    "3389": "RDP remote desktop | brute force, Shift backdoor, MS12-020 vulnerability",
    "5900": "VNC | weak password brute force, plaintext sniffing",
    "5901": "VNC | weak password brute force, plaintext sniffing",
    "5902": "VNC | weak password brute force, plaintext sniffing",
    # ---- LAN / infrastructure services ----
    "111": "NFS portmap | privilege escalation via misconfigured permissions",
    "2049": "NFS file sharing | privilege escalation via misconfigured permissions",
    "135": "RPC port mapper | information leakage, worm exploitation",
    "137": "NetBIOS name service | information leakage, SMB-family vulnerability exploitation",
    "138": "NetBIOS datagram | information leakage, SMB-family vulnerability exploitation",
    "139": "NetBIOS session | brute force, MS08-067/MS17-010 remote execution",
    "445": "SMB file sharing | brute force, EternalBlue (MS17-010) and other remote execution",
    "161": "SNMP | default community string brute force, intranet information gathering",
    "389": "LDAP | injection, anonymous access, weak passwords",
    # ---- Mail services (plaintext protocols) ----
    "25": "SMTP | mail spoofing, user enumeration (switch to SMTPS recommended)",
    "110": "POP3 | brute force, plaintext sniffing (switch to POP3S recommended)",
    "143": "IMAP | brute force, plaintext sniffing (switch to IMAPS recommended)",
    # ---- Databases ----
    "1433": "SQLServer | injection, privilege escalation, sa weak password brute force",
    "1521": "Oracle | TNS brute force, injection, shell escalation",
    "3306": "MySQL | injection, privilege escalation, brute force",
    "5000": "Sybase/DB2 | brute force, injection",
    "5432": "PostgreSQL | brute force, injection, weak passwords",
    "5984": "CouchDB | unauthorized arbitrary command execution",
    "6379": "Redis | unauthorized access, weak password brute force",
    "11211": "Memcached | unauthorized access, reflection amplification attacks",
    "27017": "MongoDB | brute force, unauthorized access",
    "27018": "MongoDB (shard) | brute force, unauthorized access",
    # ---- Middleware / DevOps components ----
    "2181": "ZooKeeper | unauthorized access",
    "2375": "Docker API | unauthorized takeover of containers and even the host",
    "3690": "SVN | source code leakage, unauthorized access",
    "4848": "GlassFish admin console | weak passwords",
    "7001": "WebLogic | Java deserialization, weak passwords",
    "7002": "WebLogic (SSL) | Java deserialization, weak passwords",
    "8069": "Zabbix | remote execution, SQL injection",
    "9080": "WebSphere | Java deserialization, weak passwords",
    "9081": "WebSphere | Java deserialization, weak passwords",
    "9090": "WebSphere admin console | Java deserialization, weak passwords",
    "9200": "Elasticsearch | unauthorized remote execution",
    "9300": "Elasticsearch (cluster) | unauthorized remote execution",
    "50030": "Hadoop | unauthorized access",
    "50070": "Hadoop | unauthorized access",
}


def _load_credentials(args):
    """Rely on the default credential chain (aliyun CLI config); explicit AK/SK is not accepted"""
    ak, sk, token = load_default_credentials()
    return ak, sk, token


def _fmt_time(ts):
    if not ts:
        return "never"
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
    except Exception:
        return str(ts)


# ==================== Data fetching ====================

def fetch_internet(engine):
    """Fetch all policies of the internet boundary (IPv4 in/out directions), keeping Order and hit fields"""
    items = []
    for direction in ("in", "out"):
        page = 1
        while True:
            data = call_api(engine.ak, engine.sk, engine.endpoint, "DescribeControlPolicy", {
                "Direction": direction, "CurrentPage": str(page), "PageSize": "50", "Lang": "zh",
            }, engine.security_token)
            batch = data.get("Policys", [])
            for it in batch:
                it["_direction"] = direction
                it["_boundary"] = "互联网边界"
                it["_scope"] = "互联网边界"
            items.extend(batch)
            if not batch or len(items) >= int(data.get("TotalCount", 0)):
                break
            page += 1
    return items


def fetch_all_boundaries(engine):
    """Merged fetch across three boundaries: internet uses the native API (keeps hit fields), NAT/VPC reuse plugins"""
    rows = fetch_internet(engine)
    for name in ("NAT边界", "VPC边界"):
        plugin = get_plugins([name])[0]
        for it in engine.fetch(plugin):
            it["_boundary"] = name
            # Scope: NAT per gateway, VPC per policy group (hit analysis only has data for internet)
            scope = it.get("NatGatewayId") or it.get("MemberUid") or it.get("VpcFirewallId") or name
            it["_scope"] = str(scope)
            rows.append(it)
    return rows


def _row_label(row):
    """Human-readable policy identifier"""
    name = row.get("AclName") or row.get("策略名称") or "(unnamed)"
    return f"{name} [{row.get('_boundary', '?')}/{row.get('_direction', '')}]"


def _row_scope(row):
    return (row.get("_boundary"), row.get("_scope"), row.get("_direction") or row.get("方向"))


# ==================== Read-only: hit analysis ====================

def cmd_hit(args, engine):
    rows = fetch_internet(engine)  # Hit statistics are only provided by the internet boundary API
    rows.sort(key=lambda r: int(r.get("HitTimes", 0) or 0))
    zero = [r for r in rows if not int(r.get("HitTimes", 0) or 0)]

    print(f"\nInternet boundary has {len(rows)} policies in total, {len(zero)} with zero hits\n")
    print(f"{'Hits':>12} | {'Last Hit':<12} | {'Action':<6} | Policy")
    print("-" * 90)
    for r in rows[:args.top]:
        print(f"{int(r.get('HitTimes', 0) or 0):>12} | {_fmt_time(r.get('HitLastTime')):<12} | "
              f"{r.get('AclAction', ''):<6} | {_row_label(r)} (UUID: {r.get('AclUuid', '')})")
    if zero:
        print(f"\n[WARN] {len(zero)} zero-hit policies (evaluate manually and clean up in the console; this tool does not provide deletion):")
        for r in zero:
            print(f"    - {_row_label(r)} (UUID: {r.get('AclUuid', '')}, action: {r.get('AclAction')})")


# ==================== Read-only: duplicate rule detection ====================

def _dup_signature(row):
    """Duplicate detection signature: excludes volatile fields such as priority/UUID/hits"""
    keys = ["_boundary", "_scope", "_direction", "AclAction", "Source", "SourceType",
            "Destination", "DestinationType", "Proto", "DestPort", "DestPortType",
            "DestPortGroup", "Release", "IpVersion"]
    vals = []
    for k in keys:
        v = row.get(k, "")
        if k == "_direction" and not v:
            v = row.get("方向", "")
        vals.append(str(v or "").strip())
    return tuple(vals)


def cmd_dup(args, engine):
    rows = fetch_all_boundaries(engine)
    groups = {}
    for r in rows:
        groups.setdefault(_dup_signature(r), []).append(r)

    dups = {sig: group for sig, group in groups.items() if len(group) > 1}
    dup_rows = sum(len(g) for g in dups.values())
    print(f"\nChecked {len(rows)} policies, found {len(dups)} duplicate groups involving {dup_rows} policies\n")
    for sig, group in dups.items():
        print(f"  Duplicate group ({len(group)} items): {_row_label(group[0])} | source={group[0].get('Source')} "
              f"dest={group[0].get('Destination')} proto={group[0].get('Proto')} port={group[0].get('DestPort')}")
        for r in group:
            print(f"      - UUID: {r.get('AclUuid', r.get('策略名称', '?'))} priority: {r.get('Order', r.get('优先级', '?'))}")
    if not dups:
        print("  [OK] no duplicate policies found")


# ==================== Read-only: shadow rule detection ====================

def _parse_nets(value, vtype):
    """Parse an address value into a set of networks; only the net type is parseable, others (group/location) return None meaning undecidable"""
    if vtype != "net" or not value:
        return None
    nets = []
    for part in str(value).split(","):
        part = part.strip()
        if not part:
            continue
        try:
            nets.append(ipaddress.ip_network(part, strict=False))
        except ValueError:
            return None
    return nets


def _covers_addr(outer_val, outer_type, inner_val, inner_type):
    """Whether outer fully covers inner (only decidable for the net type)"""
    if outer_type == inner_type and str(outer_val) == str(inner_val):
        return True
    o = _parse_nets(outer_val, outer_type)
    i = _parse_nets(inner_val, inner_type)
    if o is None or i is None:
        return None  # Undecidable (address book/domain etc.)
    return all(any(in_net.subnet_of(out_net) for out_net in o) for in_net in i)


def _parse_port_range(p):
    try:
        a, b = str(p).split("/")
        return int(a), int(b)
    except Exception:
        return None


def _covers_port(outer, inner):
    if str(outer) == "0/0":
        return True
    if str(outer) == str(inner):
        return True
    o, i = _parse_port_range(outer), _parse_port_range(inner)
    if o is None or i is None:
        return None
    return o[0] <= i[0] and i[1] <= o[1]


def _covers_proto(outer, inner):
    return str(outer).upper() == "ANY" or str(outer).upper() == str(inner).upper()


def _covered_by(outer, inner):
    """Determine whether outer (earlier) fully covers inner (later)"""
    checks = [
        _covers_addr(outer.get("Source"), outer.get("SourceType"), inner.get("Source"), inner.get("SourceType")),
        _covers_addr(outer.get("Destination"), outer.get("DestinationType"),
                     inner.get("Destination"), inner.get("DestinationType")),
        _covers_proto(outer.get("Proto", "ANY"), inner.get("Proto", "ANY")),
        _covers_port(outer.get("DestPort", "0/0"), inner.get("DestPort", "0/0")),
    ]
    if any(c is False for c in checks):
        return False
    if any(c is None for c in checks):
        return None  # Some dimension is undecidable
    return True


def cmd_shadow(args, engine):
    rows = fetch_internet(engine)
    # Group by scope (direction) and sort by priority ascending: earlier rules match first
    groups = {}
    for r in rows:
        groups.setdefault(r.get("_direction"), []).append(r)

    found = []
    unknown = []
    for direction, items in groups.items():
        items.sort(key=lambda r: int(r.get("Order", 9999)))
        for idx, inner in enumerate(items):
            for outer in items[:idx]:
                cov = _covered_by(outer, inner)
                if cov is True:
                    found.append((inner, outer))
                    break
                if cov is None and not any(f[0] is inner for f in found):
                    unknown.append((inner, outer))

    print(f"\nShadow rule detection (internet boundary, judged by priority order within the same direction)\n")
    if found:
        print(f"[WARN] {len(found)} policies confirmed to be fully covered (these policies will never be hit):")
        for inner, outer in found:
            diff = "actions differ, verify intent carefully!" if inner.get("AclAction") != outer.get("AclAction") else "same action, pure redundancy"
            print(f"    - {_row_label(inner)} (priority {inner.get('Order')}, UUID: {inner.get('AclUuid')})")
            print(f"        covered by: {_row_label(outer)} (priority {outer.get('Order')}) - {diff}")
    else:
        print("  [OK] no confirmed shadow policies found")
    if unknown:
        print(f"\n[INFO] {len(unknown)} more policies cannot be auto-judged for coverage due to address book/domain types; manual review recommended")


# ==================== Read-only: compliance inspection ====================

def cmd_audit(args, engine):
    rows = fetch_internet(engine)
    findings = []

    for r in rows:
        direction = r.get("_direction")
        action = r.get("AclAction", "")
        source = str(r.get("Source", ""))
        destination = str(r.get("Destination", ""))
        dest_type = r.get("DestinationType", "")
        port = str(r.get("DestPort", ""))
        # Disabled policies are not effective and are excluded from risk judgment (Release field is the string 'true'/'false')
        if str(r.get("Release", "true")).lower() != "true":
            continue
        label = f"{_row_label(r)} (UUID: {r.get('AclUuid')}, priority {r.get('Order')})"

        if action == "accept":
            if direction == "in":
                # Check 1: allow all networks + all ports (inbound)
                full_open = source in ("0.0.0.0/0", "::/0") and port in ("0/0", "") and dest_type == "net"
                if full_open:
                    findings.append(("HIGH", "allow all networks + all ports", label))
                # Check 2: allow high-risk ports (inbound, all-network source)
                high_risk_hit = False
                for part in port.replace("-", "/").split(","):
                    base = part.split("/")[0].strip()
                    if base in HIGH_RISK_PORTS and source in ("0.0.0.0/0", "::/0"):
                        findings.append(("HIGH", f"high-risk port {base} ({HIGH_RISK_PORTS[base]}) allowed from all-network source", label))
                        high_risk_hit = True
                        break
                # Check 3: allow all-network source (general reminder; skip if Check 1/2 already matched)
                if not full_open and not high_risk_hit and source in ("0.0.0.0/0", "::/0"):
                    findings.append(("MEDIUM", "allow all-network source", label))
            else:
                # Check 2: allow high-risk ports (outbound, all-network destination)
                high_risk_hit = False
                for part in port.replace("-", "/").split(","):
                    base = part.split("/")[0].strip()
                    if base in HIGH_RISK_PORTS and destination in ("0.0.0.0/0", "::/0") and dest_type == "net":
                        findings.append(("HIGH", f"high-risk port {base} ({HIGH_RISK_PORTS[base]}) allowed to all-network destination (outbound)", label))
                        high_risk_hit = True
                        break
                # Check 3: allow all-network destination (outbound general reminder)
                if not high_risk_hit and destination in ("0.0.0.0/0", "::/0") and dest_type == "net":
                    findings.append(("MEDIUM", "allow all-network destination (outbound)", label))
        # Check 4: observe-mode policies
        if action == "log":
            findings.append(("INFO", "observe-mode policy (log only, no blocking)", label))

    print(f"\nCompliance inspection report - internet boundary in/out directions ({len(rows)} policies in total)")
    print(f"Inspection time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    if not findings:
        print("  [OK] no high-risk patterns found")
        return
    for level in ("HIGH", "MEDIUM", "INFO"):
        items = [f for f in findings if f[0] == level]
        if items:
            print(f"[{level}] {len(items)} item(s)")
            for _, desc, label in items:
                print(f"    - {desc}: {label}")
            print()
    print("Note: this tool only outputs inspection conclusions; handle remediation (adjust/disable/cleanup) manually in the console or use the switch subcommand to disable.")


# ==================== Write: boundary metadata for three boundaries ====================

BOUNDARY_LABEL = {"internet": "Internet boundary", "nat": "NAT boundary", "vpc": "VPC boundary"}


def _validate_scope(args):
    """Validate that the boundary and scope parameters match, and return the scope display name"""
    if args.boundary == "nat":
        if not getattr(args, "nat_gateway_id", None):
            print("[FAIL] NAT boundary requires --nat-gateway-id")
            sys.exit(1)
        args.direction = "out"  # NAT boundary only supports the outbound direction
        return f"NAT gateway {args.nat_gateway_id}"
    if args.boundary == "vpc":
        if not getattr(args, "vpc_firewall_id", None):
            print("[FAIL] VPC boundary requires --vpc-firewall-id (policy group ID; obtain it from _AclGroupId in dup output or from the backup Excel)")
            sys.exit(1)
        return f"policy group {args.vpc_firewall_id}"
    if not getattr(args, "direction", None):
        print("[FAIL] Internet boundary requires --direction in/out")
        sys.exit(1)
    return ""


def _query_policy(engine, boundary, acl_uuid, scope_id, direction=None):
    """Query a single policy by UUID (server-side AclUuid filter, falling back to full scan when not matched)"""
    if boundary == "nat":
        api, base = "DescribeNatFirewallControlPolicy", {"NatGatewayId": scope_id, "Direction": "out"}
    elif boundary == "vpc":
        api, base = "DescribeVpcFirewallControlPolicy", {"VpcFirewallId": scope_id}
    else:
        api, base = "DescribeControlPolicy", {"Direction": direction}

    params = dict(base)
    params.update({"AclUuid": acl_uuid, "CurrentPage": "1", "PageSize": "50", "Lang": "zh"})
    data = call_api(engine.ak, engine.sk, engine.endpoint, api, params, engine.security_token)
    matched = [p for p in data.get("Policys", []) if p.get("AclUuid") == acl_uuid]
    if matched:
        return matched[0]

    # Fallback: full pagination scan (in case the server ignores the AclUuid filter parameter)
    page = 1
    items = []
    while True:
        params = dict(base)
        params.update({"CurrentPage": str(page), "PageSize": "50", "Lang": "zh"})
        data = call_api(engine.ak, engine.sk, engine.endpoint, api, params, engine.security_token)
        batch = data.get("Policys", [])
        items.extend(batch)
        if not batch or len(items) >= int(data.get("TotalCount", 0)):
            break
        page += 1
    for p in items:
        if p.get("AclUuid") == acl_uuid:
            return p
    return None


# ==================== Write: Plan-First confirmation framework ====================

def _confirm(args, plan_lines):
    """Plan-First two-phase: show the plan -> interactive confirmation (--yes required for non-interactive use)"""
    print("\n" + "=" * 60)
    print("Change plan")
    print("=" * 60)
    for line in plan_lines:
        print(f"  {line}")
    print("=" * 60)

    if getattr(args, "dry_run", False):
        print("\n[INFO] dry-run mode: plan shown only, no changes will be executed")
        return False
    if getattr(args, "yes", False):
        print("\n[INFO] --yes specified, executing directly")
        return True
    if sys.stdin.isatty():
        return input("\nConfirm execution? (y/n)").strip().lower() == "y"
    print("\n[FAIL] --yes not specified in a non-interactive environment, aborted. Add --yes and rerun after confirming the plan")
    return False


# ==================== Write: add a single policy ====================

ACTION_MAP = {"放行": "accept", "拒绝": "drop", "观察": "log"}


def cmd_add(args, engine):
    action = ACTION_MAP.get(args.acl_action, args.acl_action)
    scope = _validate_scope(args)

    params = {
        "AclAction": action,
        "SourceType": args.source_type,
        "Source": args.source,
        "DestinationType": args.dest_type,
        "Destination": args.destination,
        "Proto": args.proto.upper(),
        "DestPortType": "port",
        "DestPort": args.port,
        "NewOrder": "-1",
        "Release": "true",
        "Description": args.description or "",
        "ApplicationNameList.1": args.application or "ANY",
    }
    if args.boundary == "internet":
        api = "AddControlPolicy"
        params.update({"Direction": args.direction, "AclName": args.name})
    elif args.boundary == "nat":
        api = "CreateNatFirewallControlPolicy"
        params.update({"NatGatewayId": args.nat_gateway_id, "Direction": "out"})
    else:
        api = "CreateVpcFirewallControlPolicy"
        params["VpcFirewallId"] = args.vpc_firewall_id

    boundary_desc = f"{BOUNDARY_LABEL[args.boundary]} ({args.region})"
    if scope:
        boundary_desc += f" | {scope}"
    if args.boundary != "nat":  # NAT has no policy name field; identified by description
        boundary_desc += f" | direction: {args.direction}" if args.boundary == "internet" else ""
    plan = [f"Boundary: {boundary_desc}",
            f"Policy identifier: {args.name if args.boundary == 'internet' else '(NAT/VPC has no name field, see description)'}",
            f"Description: {args.description or '(empty)'}",
            f"Action: {args.acl_action} ({action})",
            f"Source: {args.source} ({args.source_type})", f"Destination: {args.destination} ({args.dest_type})",
            f"Protocol/port: {args.proto}/{args.port}", f"Insert position: end of list (NewOrder=-1)",
            f"Enabled state: enabled", "", "[WARN] New policies are inserted at the end; adjust the order in the console if higher priority is needed"]
    if not _confirm(args, plan):
        return

    result = call_api(engine.ak, engine.sk, engine.endpoint, api, params, engine.security_token)
    acl_uuid = result.get("AclUuid")
    if not acl_uuid:
        print(f"[FAIL] creation failed: {result.get('Code')} - {result.get('Message')}")
        sys.exit(1)
    print(f"[OK] created successfully, AclUuid: {acl_uuid}")

    # Post-write verification
    p = _query_policy(engine, args.boundary, acl_uuid,
                      args.nat_gateway_id if args.boundary == "nat" else args.vpc_firewall_id,
                      args.direction if args.boundary == "internet" else None)
    if p:
        print(f"[OK] post-write verification passed: priority {p.get('Order')}, enabled {p.get('Release')}, action {p.get('AclAction')}")
    else:
        print("[WARN] new policy not found in post-write verification, please check in the console")


# ==================== Write: enable/disable ====================

def cmd_switch(args, engine):
    release = "true" if args.enable else "false"
    op = "enable" if args.enable else "disable"
    scope = _validate_scope(args)
    scope_id = args.nat_gateway_id if args.boundary == "nat" else args.vpc_firewall_id

    # Check current state first
    p = _query_policy(engine, args.boundary, args.acl_uuid, scope_id,
                      args.direction if args.boundary == "internet" else None)
    if not p:
        scope_hint = f", scope {scope}" if scope else ""
        print(f"[FAIL] policy {args.acl_uuid} not found ({BOUNDARY_LABEL[args.boundary]}{scope_hint})")
        sys.exit(1)
    current = str(p.get("Release", "")).lower() == "true"
    if current == args.enable:
        print(f"[INFO] policy is already {'enabled' if current else 'disabled'}, no change needed")
        return

    boundary_desc = f"{BOUNDARY_LABEL[args.boundary]}"
    if scope:
        boundary_desc += f" | {scope}"
    if args.boundary == "internet":
        boundary_desc += f" | direction: {args.direction}"
    plan = [f"Boundary: {boundary_desc}",
            f"Policy: {p.get('AclName') or p.get('Description') or '(unnamed)'} (UUID: {args.acl_uuid})",
            f"Operation: {'enabled' if current else 'disabled'} -> {op}",
            f"Impact: {'this policy starts matching traffic' if args.enable else 'this policy stops matching traffic, please evaluate the traffic destination'}"]
    if not _confirm(args, plan):
        return

    modify_params = {"AclUuid": args.acl_uuid, "Release": release}
    if args.boundary == "nat":
        modify_api = "ModifyNatFirewallControlPolicy"
        modify_params.update({"NatGatewayId": args.nat_gateway_id, "Direction": "out"})
    elif args.boundary == "vpc":
        modify_api = "ModifyVpcFirewallControlPolicy"
        modify_params["VpcFirewallId"] = args.vpc_firewall_id
    else:
        modify_api = "ModifyControlPolicy"
    result = call_api(engine.ak, engine.sk, engine.endpoint, modify_api,
                      modify_params, engine.security_token)
    if result.get("Code"):
        print(f"[FAIL] {op} failed: {result.get('Code')} - {result.get('Message')}")
        sys.exit(1)
    print(f"[OK] {op} request submitted")

    # Post-write verification
    vp = _query_policy(engine, args.boundary, args.acl_uuid, scope_id,
                       args.direction if args.boundary == "internet" else None)
    if vp and str(vp.get("Release", "")).lower() == release:
        print(f"[OK] post-write verification passed: policy has been {op}d")
    else:
        print("[WARN] post-write verification did not confirm the state change, please check in the console")


# ==================== Entry point ====================

def main():
    parser = argparse.ArgumentParser(description="ACL policy management engine (query/analyze/add/switch, no deletion provided)")
    parser.add_argument("--region", default="cn-hangzhou", help="Region (default cn-hangzhou)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("hit", help="Hit analysis (zero-hit identification)")
    p.add_argument("--top", type=int, default=20, help="Show the N least-hit policies (default 20)")

    sub.add_parser("dup", help="Duplicate rule detection (three boundaries)")
    sub.add_parser("shadow", help="Shadow rule detection (internet boundary)")
    sub.add_parser("audit", help="Compliance inspection (high-risk allow patterns)")

    p = sub.add_parser("add", help="Add a single policy (three boundaries, selected via --boundary)")
    # --boundary/--proto/--port are deliberately required with no defaults:
    # they must come from explicit user confirmation, never from silent
    # script defaults (see SKILL.md "Clarify before writing").
    p.add_argument("--boundary", required=True, choices=["internet", "nat", "vpc"],
                   help="Boundary type (required; must come from user confirmation, no default)")
    p.add_argument("--nat-gateway-id", help="NAT gateway ID (required when boundary=nat)")
    p.add_argument("--vpc-firewall-id", help="VPC policy group ID (required when boundary=vpc)")
    p.add_argument("--direction", help="Direction in/out (required for internet boundary; NAT is fixed to out and needs no value)")
    p.add_argument("--name", required=True, help="Policy name (internet boundary; used as description prefix reference for NAT/VPC)")
    p.add_argument("--acl-action", required=True,
                   choices=["accept", "drop", "log", "放行", "拒绝", "观察"], help="Action")
    p.add_argument("--source", required=True, help="Source address")
    p.add_argument("--source-type", default="net", choices=["net", "group", "location"], help="Source type")
    p.add_argument("--destination", required=True, help="Destination address")
    p.add_argument("--dest-type", default="net", choices=["net", "group", "domain", "location"], help="Destination type")
    p.add_argument("--proto", required=True, help="Protocol TCP/UDP/ICMP/ANY (required; must come from user confirmation, no default)")
    p.add_argument("--port", required=True, help="Port such as 80/80 or 0/0 (required; must come from user confirmation, no default)")
    p.add_argument("--application", help="Application name (default ANY)")
    p.add_argument("--description", help="Description")
    p.add_argument("--dry-run", action="store_true", help="Only show the plan without executing")
    p.add_argument("--yes", action="store_true", help="Skip confirmation and execute directly")

    p = sub.add_parser("switch", help="Enable/disable a single policy (three boundaries, selected via --boundary)")
    p.add_argument("--boundary", default="internet", choices=["internet", "nat", "vpc"],
                   help="Boundary type (default internet)")
    p.add_argument("--nat-gateway-id", help="NAT gateway ID (required when boundary=nat)")
    p.add_argument("--vpc-firewall-id", help="VPC policy group ID (required when boundary=vpc)")
    p.add_argument("--acl-uuid", required=True, help="Policy UUID")
    p.add_argument("--direction", help="Direction in/out (required for internet boundary)")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--enable", action="store_true", help="Enable the policy")
    group.add_argument("--disable", action="store_true", help="Disable the policy")
    p.add_argument("--dry-run", action="store_true", help="Only show the plan without executing")
    p.add_argument("--yes", action="store_true", help="Skip confirmation and execute directly")

    args = parser.parse_args()
    ak, sk, token = _load_credentials(args)
    engine = BackupEngine(ak, sk, args.region, security_token=token)

    handlers = {"hit": cmd_hit, "dup": cmd_dup, "shadow": cmd_shadow,
                "audit": cmd_audit, "add": cmd_add, "switch": cmd_switch}
    handlers[args.command](args, engine)


if __name__ == "__main__":
    main()
