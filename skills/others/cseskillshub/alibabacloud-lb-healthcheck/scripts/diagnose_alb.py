#!/usr/bin/env python3
"""
diagnose_alb.py -- ALB (Application Load Balancer) health-check diagnosis
===========================================================================
Collects listeners, forwarding rules, server groups, backend servers and
health-check probe status for an ALB instance, then renders a structured
JSON or Markdown report.

APIs used (all read-only, invoked via the aliyun CLI in plugin mode):
    alb get-load-balancer-attribute   (VpcId, ZoneMappings, probe source IPs)
    vpc describe-vswitches            (vSwitch CIDRs of the ALB zones)
    alb list-listeners                (NextToken pagination, LoadBalancerIds)
    alb list-rules                    (NextToken pagination, ListenerIds)
    alb get-listener-health-status    (IncludeRule=true, includes rule groups)
    alb list-server-groups            (NextToken pagination, ServerGroupIds)
    alb list-server-group-servers     (NextToken pagination, per group)

Workflow:
    1. GetLoadBalancerAttribute: VpcId and ZoneMappings. Health-check probe
       sources are the Local IPs (Ipv4LocalAddresses), NOT the VIP
       (IntranetAddress) -- this pitfall is handled explicitly.
    2. DescribeVSwitches resolves the CIDR of every zone vSwitch
       (best effort; failure does not abort the diagnosis).
    3. ListListeners (paginated), then optional protocol/port filtering.
    4. Per listener: ListRules and GetListenerHealthStatus with
       IncludeRule=true so rule-bound server groups are included.
    5. Aggregate server groups (ListServerGroups + ListServerGroupServers)
       and build the ownership map {group: {listener: [rules]}}.
    6. Render JSON or Markdown. A Graceful Degradation Log is always
       appended at the end of the report.

Auth: relies entirely on the aliyun CLI default credential chain. This
script contains zero credential code and is strictly read-only.

Usage:
    python3 diagnose_alb.py --region cn-hangzhou --load-balancer-id alb-xxx
    python3 diagnose_alb.py --load-balancer-id alb-xxx --format json
    python3 diagnose_alb.py --load-balancer-id alb-xxx --listener-ports 80,443
"""

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _cli import (  # noqa: E402
    ERROR_LOG,
    CliError,
    call,
    check_cli_available,
    paginate_next_token,
    paginate_page,
    resolve_region,
    set_warn_stdout,
)

TIMEOUT = 60


# ---------------------------------------------------------------------------
# API wrappers
# ---------------------------------------------------------------------------

def get_load_balancer_info(region: str, load_balancer_id: str) -> dict:
    """Query ALB instance attributes: VpcId, ZoneMappings (with vSwitchId)
    and the health-check probe source IPs.

    NOTE: the health-check probe sources are the Local IPs
    (Ipv4LocalAddresses), NOT the VIP (IntranetAddress, which is the client
    access address).
    """
    result = call("alb", "get-load-balancer-attribute",
                  {"LoadBalancerId": load_balancer_id},
                  region=region, timeout=TIMEOUT)
    vpc_id = result.get("VpcId", "")
    zone_mappings = result.get("ZoneMappings", [])
    source_ips = []
    for zm in zone_mappings:
        for addr in zm.get("LoadBalancerAddresses", []):
            for local_ip in addr.get("Ipv4LocalAddresses", []):
                if local_ip and local_ip not in source_ips:
                    source_ips.append(local_ip)
    return {
        "VpcId": vpc_id,
        "ZoneMappings": zone_mappings,
        "HealthCheckSourceIPs": source_ips,
    }


def describe_vswitches(region: str, vpc_id: str, vswitch_ids: list) -> dict:
    """Resolve {vswitch_id: cidr_block} via VPC DescribeVSwitches (paginated)."""
    if not vswitch_ids:
        return {}
    all_vsws = paginate_page(
        "vpc", "describe-vswitches",
        {"VpcId": vpc_id},
        region=region,
        items_key="VSwitches.VSwitch",
        page_req_key="PageNumber",
        page_size=50,
        max_pages=20,
        timeout=TIMEOUT,
    )
    result = {}
    wanted = set(vswitch_ids)
    for vsw in all_vsws:
        if vsw.get("VSwitchId") in wanted:
            result[vsw["VSwitchId"]] = vsw.get("CidrBlock", "")
    return result


def list_listeners(region: str, load_balancer_id: str) -> list:
    """Query all listeners of the instance (auto paginated). Filters out
    stale entries that do not belong to this instance."""
    all_listeners = paginate_next_token(
        "alb", "list-listeners",
        {"LoadBalancerIds": [load_balancer_id]},
        region=region,
        items_key="Listeners",
        max_results=100,
        max_pages=50,
        timeout=TIMEOUT,
    )
    return [l for l in all_listeners if l.get("LoadBalancerId") == load_balancer_id]


def list_rules(region: str, listener_id: str) -> list:
    """Query all forwarding rules of a listener (auto paginated)."""
    return paginate_next_token(
        "alb", "list-rules",
        {"ListenerIds": [listener_id]},
        region=region,
        items_key="Rules",
        max_results=100,
        max_pages=50,
        timeout=TIMEOUT,
    )


def get_listener_health_status(region: str, listener_id: str) -> dict:
    """Listener health status INCLUDING rule-bound server groups
    (IncludeRule=true is mandatory for complete coverage)."""
    return call("alb", "get-listener-health-status", {
        "ListenerId": listener_id,
        "IncludeRule": True,
    }, region=region, timeout=TIMEOUT)


def list_server_groups(region: str, server_group_ids: list) -> list:
    """Batch-query server groups by id (auto paginated)."""
    if not server_group_ids:
        return []
    ids = []
    seen = set()
    for gid in server_group_ids:
        if gid and gid not in seen:
            seen.add(gid)
            ids.append(gid)
    # The plugin list parameter accepts at most 20 ids per call.
    all_groups = []
    for i in range(0, len(ids), 20):
        batch = ids[i:i + 20]
        all_groups.extend(paginate_next_token(
            "alb", "list-server-groups",
            {"ServerGroupIds": batch},
            region=region,
            items_key="ServerGroups",
            max_results=100,
            max_pages=20,
            timeout=TIMEOUT,
        ))
    return all_groups


def list_server_group_servers(region: str, server_group_id: str) -> list:
    """Backend servers of one server group (auto paginated)."""
    return paginate_next_token(
        "alb", "list-server-group-servers",
        {"ServerGroupId": server_group_id},
        region=region,
        items_key="Servers",
        max_results=100,
        max_pages=50,
        timeout=TIMEOUT,
    )


def extract_server_group_ids(listeners: list, rules: list) -> list:
    """Collect every server group id referenced by default actions or rules."""
    ids = []
    for listener in listeners:
        for action in listener.get("DefaultActions", []):
            if action.get("Type") == "ForwardGroup":
                cfg = action.get("ForwardGroupConfig", {})
                for t in cfg.get("ServerGroupTuples", []):
                    gid = t.get("ServerGroupId")
                    if gid:
                        ids.append(gid)
    for rule in rules:
        for action in rule.get("RuleActions", []):
            if action.get("Type") == "ForwardGroup":
                cfg = action.get("ForwardGroupConfig", {})
                for t in cfg.get("ServerGroupTuples", []):
                    gid = t.get("ServerGroupId")
                    if gid:
                        ids.append(gid)
    return ids


def get_listener_default_server_group(listener: dict) -> str:
    """Server group id of the listener default ForwardGroup action."""
    for action in listener.get("DefaultActions", []):
        if action.get("Type") == "ForwardGroup":
            cfg = action.get("ForwardGroupConfig", {})
            for t in cfg.get("ServerGroupTuples", []):
                gid = t.get("ServerGroupId")
                if gid:
                    return gid
    return ""


def get_rule_server_group(rule: dict) -> str:
    """Server group id bound to a forwarding rule (ForwardGroup action)."""
    for action in rule.get("RuleActions", []):
        if action.get("Type") == "ForwardGroup":
            cfg = action.get("ForwardGroupConfig", {})
            for t in cfg.get("ServerGroupTuples", []):
                gid = t.get("ServerGroupId")
                if gid:
                    return gid
    return ""


def build_server_group_ownership(listeners: list, listener_rules: dict) -> dict:
    """{server_group_id: {listener_id: [rule_id, ...], ...}}"""
    ownership = {}
    for listener in listeners:
        lid = listener["ListenerId"]
        gid = get_listener_default_server_group(listener)
        if gid:
            ownership.setdefault(gid, {}).setdefault(lid, [])
    for lid, rules in listener_rules.items():
        for rule in rules:
            gid = get_rule_server_group(rule)
            if gid:
                ownership.setdefault(gid, {}).setdefault(lid, []).append(rule["RuleId"])
    return ownership


def _filter_listeners(listeners: list, protocols, ports) -> list:
    if protocols:
        upper_set = {p.upper() for p in protocols}
        listeners = [l for l in listeners
                     if (l.get("ListenerProtocol") or "").upper() in upper_set]
    if ports:
        port_set = {int(p) for p in ports}
        listeners = [l for l in listeners
                     if int(l.get("ListenerPort") or -1) in port_set]
    return listeners


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_diagnosis_report(region: str, load_balancer_id: str,
                           listener_protocols: set = None,
                           listener_ports: set = None) -> dict:
    """Build the complete ALB health-check diagnosis report.

    Every per-entity API failure is recorded into the corresponding result
    entry (an 'error' field) and into the shared ERROR_LOG; the overall
    diagnosis never aborts on a single step failure.
    """
    # Instance info (VpcId + ZoneMappings -> vSwitch CIDRs + probe source IPs)
    lb_info_error = ""
    try:
        lb_info = get_load_balancer_info(region, load_balancer_id)
    except CliError as e:
        lb_info = {"VpcId": "", "ZoneMappings": [], "HealthCheckSourceIPs": []}
        lb_info_error = str(e)
    vpc_id = lb_info.get("VpcId", "")
    zone_mappings = lb_info.get("ZoneMappings", [])
    health_check_source_ips = lb_info.get("HealthCheckSourceIPs", [])
    vswitch_ids = [zm.get("VSwitchId") for zm in zone_mappings if zm.get("VSwitchId")]
    vswitch_cidrs = {}
    if vpc_id and vswitch_ids:
        try:
            vswitch_cidrs = describe_vswitches(region, vpc_id, vswitch_ids)
        except CliError:
            pass  # non-critical path; failure does not affect main diagnosis

    listeners = list_listeners(region, load_balancer_id)
    listeners = _filter_listeners(listeners, listener_protocols, listener_ports)

    listener_rules = {}
    all_rules = []
    for listener in listeners:
        lid = listener["ListenerId"]
        try:
            rules = list_rules(region, lid)
        except CliError as e:
            rules = []
            listener["RulesError"] = str(e)
        listener_rules[lid] = rules
        all_rules.extend(rules)

    health_status = {}
    for listener in listeners:
        lid = listener["ListenerId"]
        try:
            health_status[lid] = get_listener_health_status(region, lid)
        except CliError as e:
            health_status[lid] = {"error": str(e)}

    server_group_ids = extract_server_group_ids(listeners, all_rules)
    try:
        server_groups = list_server_groups(region, server_group_ids)
    except CliError as e:
        # The failure is already recorded in ERROR_LOG by _cli.call.
        server_groups = []
        server_groups_error = str(e)
    else:
        server_groups_error = ""
    server_group_map = {sg["ServerGroupId"]: sg for sg in server_groups
                        if sg.get("ServerGroupId")}

    servers_by_group = {}
    for gid in server_group_map:
        try:
            servers_by_group[gid] = list_server_group_servers(region, gid)
        except CliError as e:
            servers_by_group[gid] = []
            server_group_map[gid]["ServersError"] = str(e)

    server_group_ownership = build_server_group_ownership(listeners, listener_rules)

    report = {
        "LoadBalancerId": load_balancer_id,
        "RegionId": region,
        "ProductType": "ALB",
        "VpcId": vpc_id,
        "ZoneMappings": zone_mappings,
        "VSwitchCIDRs": vswitch_cidrs,
        "HealthCheckSourceIPs": health_check_source_ips,
        "Listeners": listeners,
        "ListenerRules": listener_rules,
        "HealthStatus": health_status,
        "ServerGroups": server_groups,
        "ServersByGroup": servers_by_group,
        "ServerGroupOwnership": server_group_ownership,
        "Errors": list(ERROR_LOG),
    }
    if lb_info_error:
        report["LoadBalancerInfoError"] = lb_info_error
        # First-step fatal failure (instance not found / access denied):
        # the degraded report is still emitted, but the exit code must
        # signal failure so callers do not mistake it for a success.
        report["Fatal"] = True
    if server_groups_error:
        report["ServerGroupsError"] = server_groups_error
    return report


# ---------------------------------------------------------------------------
# Markdown rendering (all English)
# ---------------------------------------------------------------------------

def _degradation_log_lines() -> list:
    lines = ["## Graceful Degradation Log", ""]
    if ERROR_LOG:
        for entry in ERROR_LOG:
            lines.append(f"- {entry}")
    else:
        lines.append("No API errors were encountered")
    lines.append("")
    return lines


def format_markdown_report(report: dict) -> str:
    """Render the diagnosis report as Markdown tables."""
    lines = []
    lb_id = report["LoadBalancerId"]
    region = report["RegionId"]
    listeners = report["Listeners"]
    listener_rules = report["ListenerRules"]
    health_status = report["HealthStatus"]
    server_groups = report["ServerGroups"]
    servers_by_group = report["ServersByGroup"]
    ownership = report["ServerGroupOwnership"]
    sg_map = {sg["ServerGroupId"]: sg for sg in server_groups
              if sg.get("ServerGroupId")}

    health_map = {}
    for lid, hs in health_status.items():
        if not isinstance(hs, dict) or hs.get("error"):
            continue
        for lgs in hs.get("ListenerHealthStatus", []) or []:
            for sgi in lgs.get("ServerGroupInfos", []) or []:
                sgid = sgi.get("ServerGroupId")
                if sgid:
                    health_map[(lid, sgid)] = sgi
        # Server groups bound to forwarding rules (IncludeRule=true).
        for rhs in hs.get("RuleHealthStatus", []) or []:
            for sgi in rhs.get("ServerGroupInfos", []) or []:
                sgid = sgi.get("ServerGroupId")
                if sgid:
                    health_map[(lid, sgid)] = sgi

    listener_meta = {}
    for l in listeners:
        listener_meta[l["ListenerId"]] = (
            l.get("ListenerProtocol", "-"),
            l.get("ListenerPort", "-"),
            get_listener_default_server_group(l),
        )

    def build_owner_str(sgid: str, owner_dict: dict) -> str:
        out = []
        for idx, (lid, rules) in enumerate(owner_dict.items(), start=1):
            proto, port, default_sg = listener_meta.get(lid, ("-", "-", None))
            default_tag = ", default" if default_sg == sgid else ""
            out.append(f"Listener {idx}: {lid} ({proto}:{port}{default_tag})")
            for ridx, rid in enumerate(rules, start=1):
                out.append(f"&nbsp;&nbsp;Rule {ridx}: {rid} ({proto}:{port})")
        return "<br>".join(out) if out else "-"

    # 1. Instance information
    lb_vpc_id = report.get("VpcId", "") or "-"
    lb_vswitch_cidrs = report.get("VSwitchCIDRs", {}) or {}
    lb_source_ips = report.get("HealthCheckSourceIPs", []) or []
    vswitch_display = "<br>".join(
        f"{vsw_id} ({cidr})" for vsw_id, cidr in lb_vswitch_cidrs.items()
    ) or "-"
    source_ip_display = ", ".join(lb_source_ips) if lb_source_ips else "-"

    lines.append("## Instance Information")
    lines.append("")
    lines.append("| Item | Value |")
    lines.append("|------|-------|")
    lines.append(f"| Instance ID | {lb_id} |")
    lines.append("| Product Type | ALB (Application Load Balancer) |")
    lines.append(f"| RegionId | {region} |")
    lines.append(f"| VpcId | {lb_vpc_id} |")
    lines.append(f"| ALB vSwitch / CIDR | {vswitch_display} |")
    lines.append(f"| Health-check probe source IPs | {source_ip_display} |")
    if report.get("LoadBalancerInfoError"):
        lines.append("| Instance Attribute Error | GetLoadBalancerAttribute failed (see degradation log) |")
    lines.append("")

    # 2. Listeners
    lines.append("## Listeners")
    lines.append("")
    lines.append("| Listener ID | Protocol | Port | Default Server Group ID | Rule Count |")
    lines.append("|-------------|----------|------|-------------------------|------------|")
    for l in listeners:
        lid = l["ListenerId"]
        default_sg = get_listener_default_server_group(l)
        lines.append(f"| {lid} | {l['ListenerProtocol']} | {l['ListenerPort']} | {default_sg or '-'} | {len(listener_rules.get(lid, []))} |")
    lines.append("")

    # 3. Server group summary
    lines.append("## Server Group Summary")
    lines.append("")
    lines.append("| Server Group ID | Owned By (Listener / Rule) | Protocol | Backend Count |")
    lines.append("|-----------------|----------------------------|----------|---------------|")
    for sgid in sorted(sg_map.keys()):
        sg = sg_map[sgid]
        protocol = sg.get("Protocol", "-")
        server_count = len(servers_by_group.get(sgid, []))
        owner_str = build_owner_str(sgid, ownership.get(sgid, {}))
        lines.append(f"| {sgid} | {owner_str} | {protocol} | {server_count} |")
    lines.append("")

    # 4. Server group health check configuration
    lines.append("## Server Group Health Check Configuration")
    lines.append("")
    lines.append("| Server Group ID | Health Check Enabled | Protocol | Path | Port | Interval(s) | Timeout(s) | Healthy Threshold | Unhealthy Threshold | HTTP Method | Normal Status Codes |")
    lines.append("|-----------------|----------------------|----------|------|------|-------------|------------|-------------------|---------------------|-------------|---------------------|")
    for sgid in sorted(sg_map.keys()):
        sg = sg_map[sgid]
        hc = sg.get("HealthCheckConfig", {})
        enabled = "Yes" if hc.get("HealthCheckEnabled") else "No"
        protocol = hc.get("HealthCheckProtocol", sg.get("Protocol", "-"))
        path = hc.get("HealthCheckPath", "-")
        port = hc.get("HealthCheckConnectPort", 0)
        port_str = f"{port} (backend port)" if port == 0 else str(port)
        codes = ",".join(hc.get("HealthCheckCodes", []) or hc.get("HealthCheckHttpCodes", []) or [])
        lines.append(
            f"| {sgid} | {enabled} | {protocol} | {path} | {port_str} | "
            f"{hc.get('HealthCheckInterval', '-')} | {hc.get('HealthCheckTimeout', '-')} | "
            f"{hc.get('HealthyThreshold', '-')} | {hc.get('UnhealthyThreshold', '-')} | "
            f"{hc.get('HealthCheckMethod', '-')} | {codes or '-'} |"
        )
    lines.append("")

    # 5. Backend server status (management status, not probe result)
    lines.append("## Backend Server Status")
    lines.append("")
    lines.append("| Server Group ID | Server ID | IP | Port | Type | Weight | Status |")
    lines.append("|-----------------|-----------|----|------|------|--------|--------|")
    mgmt_status_map = {
        "Available": "Available (member of the server group)",
        "Unavailable": "Unavailable (removed or misconfigured)",
        "Initial": "Initializing",
        "Configuring": "Initializing",
        "Removing": "Removing",
    }
    for sgid in sorted(sg_map.keys()):
        servers = servers_by_group.get(sgid, [])
        if not servers:
            lines.append(f"| {sgid} | - | - | - | - | - | No backend servers |")
        else:
            for s in servers:
                raw_status = s.get('Status', '-')
                status_en = mgmt_status_map.get(raw_status, raw_status)
                lines.append(
                    f"| {sgid} | {s.get('ServerId', '-')} | {s.get('ServerIp', '-')} | "
                    f"{s.get('Port', '-')} | {s.get('ServerType', '-')} | {s.get('Weight', '-')} | {status_en} |"
                )
    lines.append("")

    # 6. Health check probe results
    lines.append("## Health Check Probe Results")
    lines.append("")
    lines.append("| Listener | Server Group ID | Source | Server ID | Port | Probe Status | Failure Reason Code |")
    lines.append("|----------|-----------------|--------|-----------|------|--------------|---------------------|")
    for l in listeners:
        lid = l["ListenerId"]
        proto_port = f"{l['ListenerProtocol']}:{l['ListenerPort']}"
        default_sgid = get_listener_default_server_group(l)
        hs = health_status.get(lid, {})
        listener_sg_sources = {}
        if default_sgid:
            listener_sg_sources[default_sgid] = "Default server group"
        for rule in listener_rules.get(lid, []):
            rule_sgid = get_rule_server_group(rule)
            if rule_sgid and rule_sgid not in listener_sg_sources:
                listener_sg_sources[rule_sgid] = "Forwarding rule"
        if isinstance(hs, dict) and hs.get("error"):
            for sgid, source_label in listener_sg_sources.items():
                lines.append(f"| {proto_port} | {sgid} | {source_label} | - | - | - | GetListenerHealthStatus failed (see degradation log) |")
            continue
        for sgid, source_label in listener_sg_sources.items():
            sgi = health_map.get((lid, sgid), {})
            non_normal = sgi.get("NonNormalServers", [])
            servers = servers_by_group.get(sgid, [])
            if not servers:
                lines.append(f"| {proto_port} | {sgid} | {source_label} | - | - | - | No backend servers |")
            elif not non_normal:
                for s in servers:
                    lines.append(
                        f"| {proto_port} | {sgid} | {source_label} | {s.get('ServerId', '-')} | {s.get('Port', '-')} | Normal | - |"
                    )
            else:
                for svr in non_normal:
                    reason = (svr.get("Reason") or {}).get("ReasonCode", "-")
                    lines.append(
                        f"| {proto_port} | {sgid} | {source_label} | {svr.get('ServerId')} | {svr.get('Port')} | Abnormal | {reason} |"
                    )
                non_normal_pairs = {(svr.get("ServerId"), svr.get("Port")) for svr in non_normal}
                normal_servers = [s for s in servers
                                  if (s.get("ServerId"), s.get("Port")) not in non_normal_pairs]
                for s in normal_servers:
                    lines.append(
                        f"| {proto_port} | {sgid} | {source_label} | {s.get('ServerId', '-')} | {s.get('Port', '-')} | Normal | - |"
                    )
    lines.append("")
    lines.extend(_degradation_log_lines())
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ALB (Application Load Balancer) health-check configuration diagnosis")
    parser.add_argument("--region", default="",
                        help="RegionId, e.g. cn-hangzhou. Falls back to env vars "
                             "(ALIBABA_CLOUD_REGION_ID etc.), then to the current "
                             "profile in ~/.aliyun/config.json.")
    parser.add_argument("--load-balancer-id", required=True, help="ALB instance ID (alb-xxx)")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown",
                        help="Output format, default markdown")
    parser.add_argument("--output", default="-",
                        help="Output file path, default stdout")
    parser.add_argument("--listener-protocols", default="",
                        help="Filter listeners by protocol, comma separated "
                             "(e.g. HTTP,HTTPS). Empty = no filter.")
    parser.add_argument("--listener-ports", default="",
                        help="Filter listeners by port, comma separated "
                             "(e.g. 80,443). Empty = no filter.")
    args = parser.parse_args()

    check_cli_available()
    region = resolve_region(args.region)
    set_warn_stdout(args.format != "json")  # keep JSON stdout parseable

    protocols = {p.strip() for p in args.listener_protocols.split(",") if p.strip()} or None
    try:
        ports = {int(p.strip()) for p in args.listener_ports.split(",") if p.strip()} or None
    except ValueError:
        print("[ERROR] --listener-ports must be a comma separated integer list", file=sys.stderr)
        sys.exit(1)

    fatal = False
    try:
        report = build_diagnosis_report(region, args.load_balancer_id,
                                        listener_protocols=protocols,
                                        listener_ports=ports)
    except CliError as e:
        # Fatal first-step failure (e.g. instance not found): still emit a
        # report skeleton with the Graceful Degradation Log.
        fatal = True
        report = {
            "LoadBalancerId": args.load_balancer_id,
            "RegionId": region,
            "ProductType": "ALB",
            "error": str(e),
            "VpcId": "", "ZoneMappings": [], "VSwitchCIDRs": {},
            "HealthCheckSourceIPs": [], "Listeners": [], "ListenerRules": {},
            "HealthStatus": {}, "ServerGroups": [], "ServersByGroup": {},
            "ServerGroupOwnership": {}, "Errors": list(ERROR_LOG),
            "Fatal": True,
        }
    fatal = fatal or bool(report.get("Fatal"))

    if args.format == "markdown":
        output = format_markdown_report(report)
        if report.get("error"):
            output = (f"[ERROR] Diagnosis could not collect instance data: "
                      f"{report['error']}\n\n" + output)
    else:
        output = json.dumps(report, indent=2, ensure_ascii=False)

    if args.output == "-":
        print(output)
    else:
        try:
            parent = os.path.dirname(args.output)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
        except OSError as e:
            print(f"[ERROR] Failed to write report to {args.output}: {e}",
                  file=sys.stderr)
            sys.exit(1)
        print(f"Report saved: {args.output}")

    sys.exit(1 if fatal else 0)


if __name__ == "__main__":
    main()
