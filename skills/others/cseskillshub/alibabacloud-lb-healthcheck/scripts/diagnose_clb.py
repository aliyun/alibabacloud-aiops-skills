#!/usr/bin/env python3
"""
diagnose_clb.py -- CLB (Classic Load Balancer) health-check diagnosis
=======================================================================
Collects listeners, forwarding rules, server groups, backend servers and
health-check probe status for a CLB instance, then renders a structured JSON
or Markdown report.

APIs used (all read-only, invoked via the aliyun CLI in plugin mode):
    slb describe-load-balancer-attribute              (listeners + default backends + VpcId)
    slb describe-load-balancer-tcp-listener-attribute (per TCP listener)
    slb describe-load-balancer-udp-listener-attribute (per UDP listener)
    slb describe-load-balancer-http-listener-attribute(per HTTP listener)
    slb describe-load-balancer-https-listener-attribute(per HTTPS listener)
    slb describe-rules                                (forwarding rules per listener)
    slb describe-rule-attribute                       (per rule)
    slb describe-vserver-group-attribute              (vServer group + backends)
    slb describe-master-slave-server-group-attribute  (master-slave group + backends)
    slb describe-health-status                        (backend probe status per listener)

Workflow:
    1. DescribeLoadBalancerAttribute: parse the listener list from
       ListenerPortsAndProtocol (tolerating the legacy misspelled key
       'ListenerPortsAndProtocal') plus instance-level default backend
       servers and VpcId.
    2. Optional protocol/port filtering before any further API loop.
    3. Per listener: query listener attributes (health-check config),
       forwarding rules and DescribeHealthStatus (403 degrades to an
       '_unauthorized' marker instead of aborting).
    4. Resolve every referenced server group (vServer vs master-slave) and
       merge probe results into backend server records.
    5. Render JSON or Markdown. A Graceful Degradation Log is always
       appended at the end of the report.

Auth: relies entirely on the aliyun CLI default credential chain. This
script contains zero credential code and is strictly read-only.

Usage:
    python3 diagnose_clb.py --region cn-hangzhou --load-balancer-id lb-xxx
    python3 diagnose_clb.py --load-balancer-id lb-xxx --format json
    python3 diagnose_clb.py --load-balancer-id lb-xxx --listener-protocols HTTP,HTTPS
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
    is_unauthorized,
    resolve_region,
    set_warn_stdout,
)

PRODUCT = "slb"
TIMEOUT = 60


# ---------------------------------------------------------------------------
# API wrappers
# ---------------------------------------------------------------------------

def describe_load_balancer_attribute(region: str, lb_id: str) -> dict:
    """Instance detail: listener list, default backend servers, VpcId."""
    return call(PRODUCT, "describe-load-balancer-attribute",
                {"LoadBalancerId": lb_id}, region=region, timeout=TIMEOUT)


def list_listeners(region: str, lb_id: str) -> tuple:
    """Parse all listeners of the instance from DescribeLoadBalancerAttribute.

    Some credentials lack DescribeLoadBalancerListeners permission, so the
    listener list is parsed from the ListenerPortsAndProtocol structure.
    Both the current key and the legacy misspelled key
    ('ListenerPortsAndProtocal') are tolerated.
    Returns (listeners, default_backend_servers, vpc_id).
    """
    result = describe_load_balancer_attribute(region, lb_id)
    seen = set()
    listeners = []
    for key in ("ListenerPortsAndProtocol", "ListenerPortsAndProtocal"):
        lp = result.get(key, {})
        if not isinstance(lp, dict):
            continue
        for item in lp.get("ListenerPortAndProtocol", []):
            protocol = (item.get("ListenerProtocol") or "").upper()
            port = item.get("ListenerPort")
            if not protocol or port is None:
                continue
            lid = f"{protocol}_{port}"
            if lid in seen:
                continue
            seen.add(lid)
            listeners.append({
                "LoadBalancerId": lb_id,
                "ListenerProtocol": protocol,
                "ListenerPort": port,
                "ListenerId": lid,
            })
    default_backend_servers = (result.get("BackendServers") or {}).get("BackendServer", []) or []
    vpc_id = result.get("VpcId", "") or ""
    return listeners, default_backend_servers, vpc_id


def get_listener_attribute(region: str, listener: dict) -> dict:
    """Query listener detail attributes (including health-check config)."""
    protocol = listener.get("ListenerProtocol", "").upper()
    command_map = {
        "TCP": "describe-load-balancer-tcp-listener-attribute",
        "UDP": "describe-load-balancer-udp-listener-attribute",
        "HTTP": "describe-load-balancer-http-listener-attribute",
        "HTTPS": "describe-load-balancer-https-listener-attribute",
    }
    command = command_map.get(protocol)
    if not command:
        return {}
    return call(PRODUCT, command, {
        "LoadBalancerId": listener["LoadBalancerId"],
        "ListenerPort": listener["ListenerPort"],
    }, region=region, timeout=TIMEOUT)


def list_rules(region: str, listener: dict) -> list:
    """Query all forwarding rules of a (HTTP/HTTPS) listener.

    ListenerProtocol is passed explicitly: it is required when multiple
    protocols share the same port (per the describe-rules plugin help).
    """
    result = call(PRODUCT, "describe-rules", {
        "LoadBalancerId": listener["LoadBalancerId"],
        "ListenerPort": listener["ListenerPort"],
        "ListenerProtocol": listener.get("ListenerProtocol", ""),
        "BizRegionId": region,
    }, region=region, timeout=TIMEOUT)
    return (result.get("Rules") or {}).get("Rule", []) or []


def get_rule_attribute(region: str, rule_id: str) -> dict:
    """Query the detail of one forwarding rule."""
    return call(PRODUCT, "describe-rule-attribute", {
        "RuleId": rule_id,
        "BizRegionId": region,
    }, region=region, timeout=TIMEOUT)


def describe_vserver_group(region: str, vserver_group_id: str) -> dict:
    """Query vServer group attributes and backend servers."""
    return call(PRODUCT, "describe-vserver-group-attribute", {
        "VServerGroupId": vserver_group_id,
        "BizRegionId": region,
    }, region=region, timeout=TIMEOUT)


def describe_master_slave_server_group(region: str, group_id: str) -> dict:
    """Query master-slave server group attributes and backend servers."""
    return call(PRODUCT, "describe-master-slave-server-group-attribute", {
        "MasterSlaveServerGroupId": group_id,
        "BizRegionId": region,
    }, region=region, timeout=TIMEOUT)


def describe_health_status(region: str, listener: dict) -> dict:
    """Query backend probe status of the listener's default server group.

    Permission denial (403 / Forbidden) degrades to an '_unauthorized'
    marker instead of aborting the whole diagnosis.
    """
    try:
        return call(PRODUCT, "describe-health-status", {
            "LoadBalancerId": listener["LoadBalancerId"],
            "ListenerPort": listener["ListenerPort"],
        }, region=region, timeout=TIMEOUT)
    except CliError as e:
        if is_unauthorized(e):
            return {"_unauthorized": True, "error": str(e)}
        raise


def extract_vserver_group_ids(listeners: list, rules: list) -> list:
    """Collect all server group ids referenced by listeners and rules."""
    ids = []
    for listener in listeners:
        gid = listener.get("VServerGroupId")
        if gid:
            ids.append(gid)
    for rule in rules:
        gid = rule.get("VServerGroupId")
        if gid:
            ids.append(gid)
    return ids


def _filter_listeners(listeners: list, protocols, ports) -> list:
    """Filter listeners by protocol/port before entering the API loops."""
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
    """Build the complete CLB health-check diagnosis report.

    Every per-entity API failure is recorded into the corresponding result
    entry (an 'error' field) and into the shared ERROR_LOG; the overall
    diagnosis never aborts on a single step failure.
    """
    listeners, default_backend_servers, vpc_id = list_listeners(region, load_balancer_id)
    listeners = _filter_listeners(listeners, listener_protocols, listener_ports)

    listener_attributes = {}
    listener_rules = {}
    rule_attributes = {}
    health_status = {}
    all_rules = []

    for listener in listeners:
        lid = listener.get("ListenerId") or \
            f"{listener['ListenerProtocol']}_{listener['ListenerPort']}"
        listener["ListenerId"] = lid

        try:
            attr = get_listener_attribute(region, listener)
        except CliError as e:
            attr = {"error": str(e)}
        listener_attributes[lid] = attr

        # Write back the server group referenced by the listener attributes.
        vsgid = attr.get("VServerGroupId", "")
        mssgid = attr.get("MasterSlaveServerGroupId", "")
        if vsgid:
            listener["VServerGroupId"] = vsgid
            listener["ServerGroupType"] = "VServer Group"
        elif mssgid:
            listener["VServerGroupId"] = mssgid
            listener["ServerGroupType"] = "Master-Slave Server Group"
        else:
            listener["VServerGroupId"] = ""
            listener["ServerGroupType"] = "Default Server Group"

        # Forwarding rules only exist on HTTP/HTTPS listeners; skip L4.
        rules = []
        if listener.get("ListenerProtocol") in ("HTTP", "HTTPS"):
            try:
                rules = list_rules(region, listener)
            except CliError as e:
                rules = []
                listener["RulesError"] = str(e)
        listener_rules[lid] = rules
        all_rules.extend(rules)

        try:
            health_status[lid] = describe_health_status(region, listener)
        except CliError as e:
            health_status[lid] = {"error": str(e)}

        for rule in rules:
            rid = rule.get("RuleId")
            if not rid:
                continue
            try:
                rule_attributes[rid] = get_rule_attribute(region, rid)
            except CliError as e:
                rule_attributes[rid] = {"error": str(e)}

    # Aggregate server groups (vServer groups vs master-slave groups).
    vserver_group_ids = extract_vserver_group_ids(listeners, all_rules)
    master_slave_group_ids = set()
    for listener in listeners:
        if listener.get("ServerGroupType") == "Master-Slave Server Group":
            gid = listener.get("VServerGroupId")
            if gid:
                master_slave_group_ids.add(gid)

    vserver_groups = {}
    servers_by_group = {}
    for gid in set(vserver_group_ids):
        try:
            if gid in master_slave_group_ids:
                vsg = describe_master_slave_server_group(region, gid)
                vserver_groups[gid] = vsg
                servers = (vsg.get("MasterSlaveBackendServers") or {}).get(
                    "MasterSlaveBackendServer", []) or []
            else:
                vsg = describe_vserver_group(region, gid)
                vserver_groups[gid] = vsg
                servers = (vsg.get("BackendServers") or {}).get("BackendServer", []) or []
            servers_by_group[gid] = servers
        except CliError as e:
            vserver_groups[gid] = {"error": str(e)}
            servers_by_group[gid] = []

    # Merge DescribeHealthStatus probe results into backend server records.
    for listener in listeners:
        lid = listener["ListenerId"]
        hs = health_status.get(lid, {})
        if hs.get("_unauthorized") or hs.get("error"):
            continue
        related_gids = set()
        gid = listener.get("VServerGroupId")
        if gid:
            related_gids.add(gid)
        for rule in listener_rules.get(lid, []):
            rgid = rule.get("VServerGroupId")
            if rgid:
                related_gids.add(rgid)
        is_default_listener = listener.get("ServerGroupType") == "Default Server Group"
        for svr in (hs.get("BackendServers") or {}).get("BackendServer", []) or []:
            matched = False
            for g in related_gids:
                for bs in servers_by_group.get(g, []):
                    if bs.get("ServerId") == svr.get("ServerId") and \
                            bs.get("Port") == svr.get("Port"):
                        bs["Status"] = svr.get("ServerHealthStatus")
                        matched = True
            # Default server group: backends have no Port field; match by id.
            if not matched and is_default_listener:
                for bs in default_backend_servers:
                    if bs.get("ServerId") == svr.get("ServerId"):
                        bs["Status"] = svr.get("ServerHealthStatus")
                        break

    # Server group ownership: {gid: {listener_id: [rule_id, ...]}}
    server_group_ownership = {}
    for listener in listeners:
        lid = listener["ListenerId"]
        gid = listener.get("VServerGroupId")
        if gid:
            server_group_ownership.setdefault(gid, {}).setdefault(lid, [])
    for listener in listeners:
        lid = listener["ListenerId"]
        for rule in listener_rules.get(lid, []):
            gid = rule.get("VServerGroupId")
            rid = rule.get("RuleId")
            if gid and rid:
                server_group_ownership.setdefault(gid, {}).setdefault(lid, []) \
                    .append(rid)

    return {
        "LoadBalancerId": load_balancer_id,
        "RegionId": region,
        "ProductType": "CLB",
        "VpcId": vpc_id,
        "Listeners": listeners,
        "ListenerAttributes": listener_attributes,
        "ListenerRules": listener_rules,
        "RuleAttributes": rule_attributes,
        "HealthStatus": health_status,
        "VServerGroups": vserver_groups,
        "ServersByGroup": servers_by_group,
        "ServerGroupOwnership": server_group_ownership,
        "DefaultBackendServers": default_backend_servers,
        "Errors": list(ERROR_LOG),
    }


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
    listener_attributes = report["ListenerAttributes"]
    listener_rules = report["ListenerRules"]
    rule_attributes = report["RuleAttributes"]
    health_status = report["HealthStatus"]
    vserver_groups = report["VServerGroups"]
    servers_by_group = report["ServersByGroup"]
    default_backend_servers = report.get("DefaultBackendServers", [])

    def translate_health_status(status: str) -> str:
        """CLB DescribeHealthStatus returns only normal/abnormal; an empty
        value means the backend was not probed (health check disabled or no
        probe result yet)."""
        mapping = {
            "normal": "Normal (health check passed)",
            "abnormal": "Abnormal (health check failed)",
        }
        if not status or status == "-":
            return "Status not available"
        return mapping.get(status, status)

    def hc_cells(attr: dict) -> list:
        enabled = "Yes" if attr.get("HealthCheck") == "on" else "No"
        port = attr.get("HealthCheckConnectPort", 0)
        port_str = f"{port} (backend port)" if port == 0 else str(port)
        codes = attr.get("HealthCheckHttpCode", "-")
        if isinstance(codes, list):
            codes = ",".join(codes)
        return [
            enabled,
            str(attr.get("HealthCheckType", "-")),
            str(attr.get("HealthCheckURI", "-")),
            port_str,
            str(attr.get("HealthCheckInterval", "-")),
            str(attr.get("HealthCheckTimeout", "-")),
            str(attr.get("HealthyThreshold", "-")),
            str(attr.get("UnhealthyThreshold", "-")),
            str(attr.get("HealthCheckMethod", "-")),
            codes or "-",
        ]

    # 1. Instance information
    lb_vpc_id = report.get("VpcId", "") or "-"
    lines.append("## Instance Information")
    lines.append("")
    lines.append("| Item | Value |")
    lines.append("|------|-------|")
    lines.append(f"| Instance ID | {lb_id} |")
    lines.append("| Product Type | CLB (Classic Load Balancer) |")
    lines.append(f"| RegionId | {region} |")
    lines.append(f"| VpcId | {lb_vpc_id} |")
    lines.append("| Health-check probe source CIDR | 100.64.0.0/10 (fixed CLB probe range; no vSwitch lookup needed) |")
    lines.append("")

    # 2. Listener <-> server group association
    lines.append("## Listener and Server Group Association")
    lines.append("")
    lines.append("| Listener ID | Protocol | Port | Scope | Related Object | Server Group ID | Server Group Type | Backend Count |")
    lines.append("|-------------|----------|------|-------|----------------|-----------------|-------------------|---------------|")
    assoc_rows = []
    for l in listeners:
        lid = l["ListenerId"]
        protocol = l["ListenerProtocol"]
        port = l["ListenerPort"]
        sgid = l.get("VServerGroupId", "")
        sg_type = l.get("ServerGroupType", "Default Server Group")
        if sgid:
            count = len(servers_by_group.get(sgid, []))
            assoc_rows.append((lid, protocol, str(port), "Listener", "-", sgid, sg_type, str(count)))
        else:
            count = len(default_backend_servers)
            assoc_rows.append((lid, protocol, str(port), "Listener", "-",
                               "Default Server Group", "Default Server Group", str(count)))
        for rule in listener_rules.get(lid, []):
            rsgid = rule.get("VServerGroupId", "")
            if rsgid:
                count = len(servers_by_group.get(rsgid, []))
                assoc_rows.append((lid, protocol, str(port), "Rule",
                                   rule["RuleId"], rsgid, "VServer Group", str(count)))
    listener_order = {l["ListenerId"]: idx for idx, l in enumerate(listeners)}
    assoc_rows.sort(key=lambda r: (listener_order[r[0]], 0 if r[3] == "Listener" else 1, r[4]))
    for row in assoc_rows:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # 3. Health check configuration (listener / rule effective config)
    lines.append("## Health Check Configuration")
    lines.append("")
    lines.append("| Target / Server Group ID | Config Source | Source ID | Listener | Default Server Group | Health Check Enabled | Protocol | Path | Port | Interval(s) | Timeout(s) | Healthy Threshold | Unhealthy Threshold | HTTP Method | Normal Status Codes |")
    lines.append("|--------------------------|---------------|-----------|----------|----------------------|----------------------|----------|------|------|-------------|------------|-------------------|---------------------|-------------|---------------------|")

    all_hc_rows = []

    def effective_rule_config(listener_attr: dict, rule_attr: dict):
        """When a rule configures its own health check it takes precedence;
        otherwise the rule inherits the listener configuration."""
        if rule_attr.get("HealthCheck") in ("on", "off"):
            eff = dict(listener_attr)
            for key in ("HealthCheck", "HealthCheckType", "HealthCheckURI",
                        "HealthCheckConnectPort", "HealthCheckInterval",
                        "HealthCheckTimeout", "HealthyThreshold",
                        "UnhealthyThreshold", "HealthCheckMethod",
                        "HealthCheckHttpCode"):
                val = rule_attr.get(key)
                if val is not None and val != "":
                    eff[key] = val
            return eff, "Rule"
        return listener_attr, "Rule (inherited from listener)"

    for gid in sorted(vserver_groups.keys()):
        for listener in listeners:
            if listener.get("VServerGroupId") == gid:
                attr = listener_attributes.get(listener["ListenerId"], {})
                all_hc_rows.append([gid, "Listener", listener["ListenerId"],
                                    listener["ListenerId"], "Yes"] + hc_cells(attr))
        for listener in listeners:
            lattr = listener_attributes.get(listener["ListenerId"], {})
            for rule in listener_rules.get(listener["ListenerId"], []):
                if rule.get("VServerGroupId") == gid:
                    rattr = rule_attributes.get(rule["RuleId"], {})
                    eff, source_label = effective_rule_config(lattr, rattr)
                    all_hc_rows.append([gid, source_label, rule["RuleId"],
                                        listener["ListenerId"], "-"] + hc_cells(eff))

    # Default-server-group listeners are merged into the same table.
    for listener in listeners:
        if listener.get("ServerGroupType") == "Default Server Group":
            lid = listener["ListenerId"]
            attr = listener_attributes.get(lid, {})
            all_hc_rows.append(["Default Server Group", "Listener", lid, lid,
                                "Yes"] + hc_cells(attr))

    all_hc_rows.sort(key=lambda r: (listener_order.get(r[3], 999),
                                    0 if r[1] == "Listener" else 1, r[2]))
    for row in all_hc_rows:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # 4. Backend servers and health-check probes
    lines.append("## Backend Servers and Health Check Probes")
    lines.append("")
    lines.append("| Listener ID | Related Rule | Server Group ID | Server Group Type | Server ID | IP | Port | Type | Weight | Probe Status | Status Description |")
    lines.append("|-------------|--------------|-----------------|-------------------|-----------|----|------|------|--------|--------------|--------------------|")

    for listener in listeners:
        lid = listener["ListenerId"]
        sgid = listener.get("VServerGroupId", "")
        sg_type_listener = listener.get("ServerGroupType", "")
        attr = listener_attributes.get(lid, {})
        backend_port_default = attr.get("BackendServerPort")

        hs = health_status.get(lid, {})
        hs_unauth = hs.get("_unauthorized")
        hs_error = hs.get("error")
        probe_map = {}
        if not hs_unauth and not hs_error:
            for svr in hs.get("BackendServers", {}).get("BackendServer", []):
                probe_map[(svr.get("ServerId"), svr.get("Port"))] = \
                    svr.get("ServerHealthStatus", "")

        blocks = []
        if sgid:
            blocks.append((sgid, "-", sg_type_listener,
                           servers_by_group.get(sgid, []), None))
        elif sg_type_listener == "Default Server Group":
            blocks.append(("Default Server Group", "-", "Default Server Group",
                           default_backend_servers, backend_port_default))

        for rule in listener_rules.get(lid, []):
            rgid = rule.get("VServerGroupId", "")
            if rgid:
                blocks.append((rgid, rule["RuleId"], "VServer Group",
                               servers_by_group.get(rgid, []), None))

        first_row_of_listener = True
        matched_pairs = set()

        def status_cells(shs_value: str) -> tuple:
            if hs_unauth:
                return ("-", "Credential lacks DescribeHealthStatus permission")
            if hs_error:
                return ("-", "DescribeHealthStatus failed (see degradation log)")
            if not shs_value:
                return ("-", "Status not available")
            label = "Normal" if shs_value == "normal" else \
                ("Abnormal" if shs_value == "abnormal" else "-")
            return (label, translate_health_status(shs_value))

        for gid_label, rule_display, gtype, servers, port_override in blocks:
            if not servers:
                display_lid = lid if first_row_of_listener else ""
                lines.append(
                    f"| {display_lid} | {rule_display} | {gid_label} | {gtype} | - | - | - | - | - | - | No backend servers |"
                )
                first_row_of_listener = False
                continue
            for idx, s in enumerate(servers):
                sid = s.get("ServerId", "-")
                sport_raw = s.get("Port")
                if gid_label == "Default Server Group" and port_override not in (None, "", 0):
                    sport = port_override
                else:
                    sport = sport_raw
                sport_display = sport if sport not in (None, "", 0) else "-"
                if gid_label == "Default Server Group":
                    shs_value = next(
                        (v for (msid, _mport), v in probe_map.items() if msid == sid),
                        "",
                    )
                    for key in list(probe_map.keys()):
                        if key[0] == sid:
                            matched_pairs.add(key)
                            break
                else:
                    shs_value = probe_map.get((sid, sport_raw), "")
                    if (sid, sport_raw) in probe_map:
                        matched_pairs.add((sid, sport_raw))

                status_label, status_desc = status_cells(shs_value)
                display_lid = lid if first_row_of_listener else ""
                display_gid = gid_label if idx == 0 else ""
                display_rule = rule_display if idx == 0 else ""
                display_gtype = gtype if idx == 0 else ""
                lines.append(
                    f"| {display_lid} | {display_rule} | {display_gid} | {display_gtype} | {sid} | "
                    f"{s.get('ServerIp', '-')} | {sport_display} | {s.get('Type', '-')} | "
                    f"{s.get('Weight', '-')} | {status_label} | {status_desc} |"
                )
                first_row_of_listener = False

        # Defensive: probe results without a matching configuration row.
        for (msid, mport), shs_value in probe_map.items():
            if (msid, mport) in matched_pairs:
                continue
            status_label, status_desc = status_cells(shs_value)
            display_lid = lid if first_row_of_listener else ""
            lines.append(
                f"| {display_lid} | - | (unmatched) | - | {msid} | - | {mport if mport else '-'} | - | - | "
                f"{status_label} | {status_desc} |"
            )
            first_row_of_listener = False

        if first_row_of_listener:
            lines.append(f"| {lid} | - | - | - | - | - | - | - | - | - | This listener has no server group or backend |")

    lines.append("")
    lines.extend(_degradation_log_lines())
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="CLB (Classic Load Balancer) health-check configuration diagnosis")
    parser.add_argument("--region", default="",
                        help="RegionId, e.g. cn-hangzhou. Falls back to env vars "
                             "(ALIBABA_CLOUD_REGION_ID etc.), then to the current "
                             "profile in ~/.aliyun/config.json.")
    parser.add_argument("--load-balancer-id", required=True, help="CLB instance ID (lb-xxx)")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown",
                        help="Output format, default markdown")
    parser.add_argument("--output", default="-",
                        help="Output file path, default stdout")
    parser.add_argument("--listener-protocols", default="",
                        help="Filter listeners by protocol, comma separated "
                             "(e.g. HTTP,HTTPS or TCP,UDP). Empty = no filter.")
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
            "ProductType": "CLB",
            "error": str(e),
            "Listeners": [], "ListenerAttributes": {}, "ListenerRules": {},
            "RuleAttributes": {}, "HealthStatus": {}, "VServerGroups": {},
            "ServersByGroup": {}, "ServerGroupOwnership": {},
            "DefaultBackendServers": [], "Errors": list(ERROR_LOG),
            "Fatal": True,
        }

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
