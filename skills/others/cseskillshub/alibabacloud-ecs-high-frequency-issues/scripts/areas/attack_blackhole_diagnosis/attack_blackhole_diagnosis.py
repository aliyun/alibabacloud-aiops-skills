#!/usr/bin/env python3
"""Single entry point for read-only ECS attack / blackhole triage.

The agent runs THIS script and reads its report. It must not assemble its own
OpenAPI calls. Everything here is read-only: instance state, security-group
rules with priority resolution, EIP state and Cloud Assistant invocation
history. Verdicts are evidence-based; anything that cannot be observed from a
verified read-only API is reported as a degradation with the exact console page
the customer should open, never as a guessed conclusion.

Exit codes: 0 report produced (STATUS OK or DEGRADED), 2 credential or API
permission failure (and argparse usage errors), 3 no target instance resolved.
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import ipaddress
import json
import re
import sys

import _cli
from _cli import CliError, USER_AGENT
from _constants import (
    ADMIN_PORTS,
    BILLING_DETAIL_URL,
    BUSINESS_PORTS,
    CONSOLE_SSH_WHITELIST_CIDR,
    DEFAULT_PAGE_SIZE,
    DDOS_CONSOLE_URL,
    DOC_HARDENING_SUMMARY,
    DOC_SAS_FREE_TRIAL,
    DOC_SAS_PAY_AS_YOU_GO,
    DOC_SG_CASES,
    DOC_SG_START,
    DOC_SNAPSHOT_BILLING,
    DOC_SNAPSHOT_CREATE,
    DOC_WINDOWS_HIGH_BANDWIDTH,
    EIP_CONVERSION_STEPS,
    FULL_COVERAGE_CIDRS,
    HIGH_RISK_PORTS,
    MAX_PAGES,
    MAX_RECENT_INVOCATIONS,
    MAX_SECURITY_GROUPS_PER_INSTANCE,
    PENALTY_RELEASE_URL,
    QUOTABLE_ERROR_STRINGS,
    REGION_SWITCH_NOTE,
    SECURITY_CENTER_ALARMS_URL,
    SECURITY_CENTER_LOGIN_URL,
    SECURITY_CENTER_OVERVIEW_URL,
    SECURITY_CENTER_VIRUS_KILL_URL,
    SECURITY_GROUP_CONSOLE_URL,
    SKILL_NAME,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
    VERDICT_EXTERNAL_BLOCK,
    VERDICT_NOT_ATTACK_CONFIG,
    VERDICT_NOT_ATTACK_RESOURCE,
    VERDICT_PLATFORM_BLOCKOUT,
    VERDICT_REAL_DDOS,
    VERDICT_UNDETERMINED,
)
from sts_token import CredentialError, get_caller_identity, provenance_tag


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _dig(payload, *path, **kwargs):
    """Tolerant nested lookup; returns ``default`` on any miss."""
    default = kwargs.get("default")
    node = payload
    for key in path:
        if isinstance(node, dict):
            if key in node:
                node = node[key]
                continue
            lowered = {str(k).lower(): v for k, v in node.items()}
            if str(key).lower() in lowered:
                node = lowered[str(key).lower()]
                continue
        return default
    if node is None or node == {}:
        return default
    return node


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _split_csv(value):
    if not value:
        return []
    return [part.strip() for part in re.split(r"[,\s]+", value) if part.strip()]


def _to_int(value, default=None):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _normalize_protocol(value):
    return (value or "ALL").strip().upper()


def _port_range_matches(port_range, port):
    """ECS PortRange looks like '80/80', '-1/-1', '0/65535', '22/22'.

    '-1/-1' and an empty range mean "every port", so such a rule matches any
    port being evaluated; protocol filtering happens separately.
    """
    text = (port_range or "").strip()
    if not text or text == "-1/-1":
        return True
    if "/" not in text:
        return False
    low, _, high = text.partition("/")
    low_n, high_n = _to_int(low), _to_int(high)
    if low_n is None or high_n is None:
        return False
    if port is None:
        return True
    return low_n <= port <= high_n


def _protocol_matches(rule_protocol, want_protocol):
    rule_protocol = _normalize_protocol(rule_protocol)
    if rule_protocol in ("ALL", ""):
        return True
    return rule_protocol == _normalize_protocol(want_protocol)


def _source_of(rule, direction):
    if direction == "ingress":
        field = (rule.get("SourceCidrIp") or rule.get("Ipv6SourceCidrIp")
                 or _dig(rule, "SourcePrefixListId") or rule.get("SourceGroupId") or "")
    else:
        field = (rule.get("DestCidrIp") or rule.get("Ipv6DestCidrIp")
                 or rule.get("DestPrefixListId") or "")
    return field if isinstance(field, str) else str(field)


def _source_matches(source_field, observed_source):
    """True when the rule's authorisation object covers the observed peer."""
    field = (source_field or "").strip()
    if not field:
        return False
    if field in FULL_COVERAGE_CIDRS:
        return True
    if field.startswith(("sg-", "pml-", "pl-")):
        return None  # group- or prefix-list-based: depends on their members
    if not observed_source:
        return None  # cannot decide without the peer address
    if "," in field:
        return any(_source_matches(part.strip(), observed_source) for part in field.split(","))
    try:
        observed = ipaddress.ip_address(observed_source)
    except ValueError:
        return None
    try:
        if "/" in field:
            return observed in ipaddress.ip_network(field, strict=False)
        return observed == ipaddress.ip_address(field)
    except ValueError:
        return field == observed_source


def _precedence(rule):
    """Lower Priority value wins; a Drop beats an Accept at equal priority."""
    priority = _to_int(rule.get("Priority"), 100)
    policy = (rule.get("Policy") or "").strip().lower()
    return (priority, 0 if policy == "drop" else 1)


def _policy_of(rule):
    policy = (rule.get("Policy") or "").strip().lower()
    if policy in ("drop", "deny", "refuse"):
        return "DROP"
    if policy in ("accept",):
        return "ACCEPT"
    return policy.upper() or "UNKNOWN"


# ---------------------------------------------------------------------------
# API collectors
# ---------------------------------------------------------------------------

def fetch_instance_status(warnings, region_id):
    """Region-wide lightweight status list (fastest Running / stopped split)."""
    statuses = {}
    for page in range(1, MAX_PAGES + 1):
        payload = _cli.run_json("ecs", "DescribeInstanceStatus", {
            "RegionId": region_id,
            "PageNumber": page,
            "PageSize": DEFAULT_PAGE_SIZE,
        }, warn=warnings)
        if not payload:
            break
        rows = _as_list(_dig(payload, "InstanceStatuses", "InstanceStatus", default=[]))
        for row in rows:
            iid = row.get("InstanceId")
            if iid:
                statuses[iid] = (row.get("Status") or "Unknown")
        total = _to_int(_dig(payload, "TotalCount"), 0)
        if len(rows) < DEFAULT_PAGE_SIZE or (total and len(statuses) >= total):
            break
    return statuses


def fetch_instances(warnings, region_id, args):
    """Resolve the target instance(s) from whichever identifier was supplied."""
    params = {"RegionId": region_id, "PageSize": DEFAULT_PAGE_SIZE}
    selector = None
    if args.instance_id:
        params["InstanceIds"] = _split_csv(args.instance_id)
        selector = "instance-id"
    elif args.public_ip:
        params["PublicIpAddresses"] = _split_csv(args.public_ip)
        selector = "public-ip"
    elif args.eip_address:
        params["EipAddresses"] = _split_csv(args.eip_address)
        selector = "eip"
    elif args.private_ip:
        params["PrivateIpAddresses"] = _split_csv(args.private_ip)
        selector = "private-ip"
    else:
        selector = "region-scan"
    payload = _cli.run_json("ecs", "DescribeInstances", params, warn=warnings)
    rows = _as_list(_dig(payload, "Instances", "Instance", default=[]))
    return selector, rows


def fetch_security_group_catalog(warnings, region_id):
    payload = _cli.run_json("ecs", "DescribeSecurityGroups", {
        "RegionId": region_id,
        "PageSize": DEFAULT_PAGE_SIZE,
    }, warn=warnings)
    rows = _as_list(_dig(payload, "SecurityGroups", "SecurityGroup", default=[]))
    return {row.get("SecurityGroupId"): row for row in rows if row.get("SecurityGroupId")}


def fetch_security_group_rules(warnings, region_id, security_group_id):
    payload = _cli.run_json("ecs", "DescribeSecurityGroupAttribute", {
        "RegionId": region_id,
        "SecurityGroupId": security_group_id,
    }, warn=warnings)
    rules = _as_list(_dig(payload, "Permissions", "Permission", default=[]))
    for rule in rules:
        rule["_direction"] = (rule.get("Direction") or "ingress").lower()
    return payload, rules


def fetch_eips(warnings, region_id):
    payload = _cli.run_json("vpc", "DescribeEipAddresses", {
        "RegionId": region_id,
        "PageSize": DEFAULT_PAGE_SIZE,
    }, warn=warnings)
    return _as_list(_dig(payload, "EipAddresses", "EipAddress", default=[]))


def fetch_invocation_history(warnings, region_id, instance_id):
    payload = _cli.run_json("ecs", "DescribeInvocations", {
        "RegionId": region_id,
        "InstanceId": instance_id,
        "PageSize": DEFAULT_PAGE_SIZE,
        "IncludeOutput": False,
    }, warn=warnings)
    rows = _as_list(_dig(payload, "Invocations", "Invocation", default=[]))
    return rows[:MAX_RECENT_INVOCATIONS]


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------

def evaluate_port(rules, direction, protocol, port, observed_source):
    """Resolve the security-group decision for one flow, honouring priority."""
    candidates = [
        rule for rule in rules
        if (rule.get("_direction") or (rule.get("Direction") or "ingress").lower()) == direction
        and _protocol_matches(rule.get("IpProtocol"), protocol)
        and _port_range_matches(rule.get("PortRange"), port)
    ]
    candidates.sort(key=_precedence)
    trace = []
    effective = None
    for rule in candidates:
        source = _source_of(rule, direction)
        match = _source_matches(source, observed_source)
        trace.append({
            "priority": _to_int(rule.get("Priority"), 100),
            "policy": _policy_of(rule),
            "protocol": _normalize_protocol(rule.get("IpProtocol")),
            "port_range": rule.get("PortRange") or "-",
            "authorisation": source or "-",
            "covers_observed_peer": match,
            "description": _cli.mask(rule.get("Description") or "")[:120],
        })
        if effective is None and match is True:
            effective = trace[-1]
    if effective is None and observed_source:
        # No rule covers the observed peer; ingress default is deny, egress
        # default is allow in a normal security group.
        effective = {"priority": None, "policy": "NO-MATCHING-RULE", "authorisation": "-"}
    elif effective is None and trace:
        effective = {"priority": None, "policy": "UNDETERMINED-NEEDS-PEER", "authorisation": "-"}
    return {
        "direction": direction,
        "protocol": protocol,
        "port": port,
        "observed_source": observed_source or None,
        "effective": effective,
        "trace": trace,
    }


def analyse_rules(rules, ports, observed_source):
    """Build per-port evaluations plus the classic rule-conflict findings."""
    findings = []
    evaluations = []
    for port in ports:
        evaluation = evaluate_port(rules, "ingress", "TCP", port, observed_source)
        evaluations.append(evaluation)
        trace = evaluation["trace"]
        drops = [t for t in trace if t["policy"] == "DROP"]
        accepts = [t for t in trace if t["policy"] == "ACCEPT"]
        if drops and accepts:
            top_drop, top_accept = drops[0], accepts[0]
            if top_drop["priority"] <= top_accept["priority"]:
                findings.append({
                    "code": "SG-DENY-SHADOWS-ALLOW",
                    "severity": "high",
                    "detail": ("TCP port {0}: a DROP rule at priority {1} covering {2} is evaluated "
                               "before the ACCEPT rule at priority {3} covering {4}, so traffic is "
                               "blocked by rule precedence. This is a configuration effect, not "
                               "evidence of an attack.").format(
                                   port, top_drop["priority"], top_drop["authorisation"],
                                   top_accept["priority"], top_accept["authorisation"]),
                })
        if not accepts and not drops:
            findings.append({
                "code": "SG-NO-INGRESS-RULE",
                "severity": "high",
                "detail": ("TCP port {0}: no ingress rule exists for this port, so inbound traffic "
                           "to it is dropped by the security group default. The service is reachable "
                           "only after an accept rule is added.").format(port),
            })
        elif not accepts and drops:
            findings.append({
                "code": "SG-ONLY-DENY-RULE",
                "severity": "high",
                "detail": ("TCP port {0}: only DROP rules match this port ({1}); add a scoped accept "
                           "rule or remove the deny rule.").format(port, drops[0]["authorisation"]),
            })
        elif accepts and (evaluation["effective"] or {}).get("policy") == "NO-MATCHING-RULE":
            findings.append({
                "code": "SG-PEER-NOT-AUTHORISED",
                "severity": "high",
                "detail": ("TCP port {0}: accept rules exist but none authorises {1}, so this particular "
                           "client is filtered by the security group while other clients may be served "
                           "normally. That pattern is commonly reported as 'only I cannot open the site' "
                           "and is not an attack.").format(port, observed_source),
            })
    ssh22 = evaluate_port(rules, "ingress", "TCP", 22, None)
    console_allowed = any(
        t["policy"] == "ACCEPT" and t["authorisation"] == CONSOLE_SSH_WHITELIST_CIDR
        for t in ssh22["trace"]
    )
    if ssh22["trace"] and not console_allowed:
        findings.append({
            "code": "SG-CONSOLE-SSH-WHITELIST-MISSING",
            "severity": "medium",
            "detail": ("Port 22 has ingress rules but {0} is not in an accept rule, so browser-based "
                       "and Workbench SSH sessions can fail with a closed connection even while the "
                       "instance and any real attack are unrelated.").format(CONSOLE_SSH_WHITELIST_CIDR),
        })
    exposed = []
    for rule in rules:
        direction = rule.get("_direction") or "ingress"
        if direction != "ingress" or _policy_of(rule) != "ACCEPT":
            continue
        if _source_of(rule, "ingress") not in FULL_COVERAGE_CIDRS:
            continue
        port_range = (rule.get("PortRange") or "").strip()
        if not port_range or port_range == "-1/-1":
            exposed.append("all ports")
            continue
        if not _protocol_matches(rule.get("IpProtocol"), "TCP"):
            continue
        for risky in sorted(set(ADMIN_PORTS + HIGH_RISK_PORTS)):
            if _port_range_matches(port_range, risky):
                exposed.append(risky)
    exposed = sorted(set(str(item) for item in exposed))
    if exposed:
        findings.append({
            "code": "SG-PUBLIC-ADMIN-EXPOSURE",
            "severity": "high",
            "detail": ("These ports are accepted from {0}: {1}. Public administrative and datastore "
                       "ports are the usual entry point for brute force and for a host being abused "
                       "to attack others; narrow the authorisation object to your own office or "
                       "VPN egress address.").format(FULL_COVERAGE_CIDRS[0], ", ".join(str(p) for p in exposed)),
        })
    egress_deny = [
        rule for rule in rules
        if (rule.get("_direction") or "") == "egress" and _policy_of(rule) == "DROP"
    ]
    if egress_deny:
        findings.append({
            "code": "SG-EGRESS-DENY-PRESENT",
            "severity": "info",
            "detail": ("{0} egress DROP rule(s) exist. A customer-side egress deny is different from a "
                       "platform outbound block: platform blocks are announced in an SMS or internal "
                       "message and are lifted only through the penalty-release page.").format(len(egress_deny)),
        })
    return evaluations, findings


def analyse_eips(eips, instance_id, public_ips):
    """Match EIPs to the instance and read bandwidth/state, never mutate them."""
    matched = []
    for eip in eips:
        bound_instance = eip.get("InstanceId") or _dig(eip, "AssociatedInstanceId")
        address = eip.get("IpAddress") or _dig(eip, "EipAddress")
        if bound_instance and bound_instance == instance_id:
            matched.append(eip)
        elif address and address in public_ips:
            matched.append(eip)
    notes = []
    for eip in matched:
        status = eip.get("Status") or "Unknown"
        bandwidth = eip.get("Bandwidth")
        charge = eip.get("InternetChargeType") or eip.get("ChargeType") or "unknown"
        entry = {
            "ip": eip.get("IpAddress"),
            "allocation_id": eip.get("AllocationId"),
            "status": status,
            "bandwidth_mbps": bandwidth,
            "charge_type": charge,
            "bound_instance": eip.get("InstanceId"),
        }
        notes.append(entry)
        if status and status not in ("InUse", "Available"):
            notes.append({
                "warning": ("EIP status '{0}' is not InUse. A suspended or unpaid-by-traffic band can "
                            "stop forwarding public traffic and is frequently mistaken for a blackhole; "
                            "check outstanding balance before any attack hypothesis.").format(status)})
        if str(bandwidth or "0").strip() in ("0", ""):
            notes.append({"warning": "EIP bandwidth reads 0 Mbps, which means no public bandwidth is effective."})
    # R13 A-line F9-eip-conflict (2026-10-21): this function reported only EIPs bound to
    # the instance, so an EIP that exists in the region and is bound to NOTHING was
    # silently dropped and the leg wrote "no EIP" about an address the account really
    # holds. That unbound Available EIP *is* the fault signature of the fixed-public-IP /
    # EIP mutual exclusion - the allocation succeeded, the association could not - so it
    # must be surfaced whenever the instance also carries a fixed public IP.
    if public_ips:
        for eip in eips:
            if eip.get("InstanceId") or _dig(eip, "AssociatedInstanceId"):
                continue
            if str(eip.get("Status") or "") != "Available":
                continue
            notes.append({
                "unbound_eip": {"ip": eip.get("IpAddress"),
                                "allocation_id": eip.get("AllocationId"),
                                "status": eip.get("Status"),
                                "bandwidth_mbps": eip.get("Bandwidth")},
                # The renderer only prints note["warning"] for warning-shaped notes, so the
                # concrete address and allocation id have to be inside that sentence - a
                # report must be able to quote the number, not just the category.
                "warning": ("EIP {0} (allocation {1}) is allocated in this region and bound to no "
                            "instance while this instance still carries a fixed public IP. That "
                            "combination is the mutual-exclusion signature: the address exists but "
                            "cannot be attached until the fixed IP is converted or released, so "
                            "traffic pointed at it silently goes nowhere. Quote this address and its "
                            "allocation id and name the conversion path before any bandwidth or DNS "
                            "hypothesis; and never report this region as 'no EIP' - the read returned "
                            "it.").format(eip.get("IpAddress"), eip.get("AllocationId"))})
    return matched, notes


def analyse_invocations(rows, time_window):
    """Read-only history of Cloud Assistant runs: who touched the instance."""
    summary = []
    for row in rows:
        summary.append({
            "invoke_id": row.get("InvokeId"),
            "command_name": row.get("CommandName") or row.get("Name"),
            "command_type": row.get("CommandType") or row.get("Type"),
            "status": row.get("InvocationStatus") or row.get("InvokeStatus"),
            "created": row.get("CreationTime") or row.get("CreateTime"),
        })
    if time_window:
        for item in summary:
            if item.get("created") and _within(item["created"], time_window):
                item["in_reported_window"] = True
    return summary


def _within(timestamp, window):
    """Loose ISO-8601 substring comparison; never fails the report."""
    if not timestamp:
        return False
    start, _, end = window.partition(",")
    stamp = str(timestamp)
    if start and end:
        return start.strip() <= stamp <= end.strip()
    if start:
        return stamp.startswith(start.strip()[:10])
    return False


def detect_notice_signals(alarm_text, symptom):
    """Classify the text the customer pasted; it is the only window onto
    platform-side outbound blocks and content penalties."""
    blob = " ".join(filter(None, [alarm_text, symptom])).lower()
    signals = []
    if re.search(r"black\s*hole|blackhole|ddos", blob):
        signals.append("mentions-blackhole-or-ddos")
    if re.search(r"scrub|cleaning|mitigation", blob):
        signals.append("mentions-traffic-scrubbing")
    if re.search(r"block(ed)?\s*(the\s*)?server|outbound|blocked .{0,20}port", blob):
        signals.append("mentions-outbound-block")
    if re.search(r"illegal|violation|prohibiti|penalt|url.*shield|shut\s*down", blob):
        signals.append("mentions-content-penalty")
    if re.search(r"port\s*25|smtp", blob):
        signals.append("mentions-port-25")
    if re.search(r"account.{0,20}(frozen|freeze)|unfreez", blob):
        signals.append("mentions-account-freeze")
    if re.search(r"carrier|isp|operator|regulator|cross[- ]?border|overseas", blob):
        signals.append("mentions-carrier-or-regulator")
    if re.search(r"miner|cryptomining|worm|webshell|backdoor|trojan|virus", blob):
        signals.append("mentions-host-compromise")
    return signals


def build_verdict(findings, instance_row, signals):
    """Four-way classification with an explicit confidence and its limits."""
    reasons = []
    if not instance_row:
        return VERDICT_UNDETERMINED, "none", reasons + [
            "No instance row was resolved, so no area can be assessed."]
    status = (instance_row.get("status") or instance_row.get("Status") if instance_row else None) or "Unknown"
    if status not in ("Running",):
        return VERDICT_NOT_ATTACK_RESOURCE, "high", [
            "Instance state read from the control plane is '{0}', not Running, so the outage is on the "
            "instance-lifecycle area. This skill does not decide why it stopped.".format(status)
        ] + reasons
    blocking = [f for f in findings if f["code"] in (
        "SG-DENY-SHADOWS-ALLOW", "SG-NO-INGRESS-RULE", "SG-ONLY-DENY-RULE",
        "SG-PEER-NOT-AUTHORISED", "SG-CONSOLE-SSH-WHITELIST-MISSING")]
    if blocking:
        reasons.append("{0} security-group finding(s) independently explain an unreachable service; "
                       "fix them first and retest before concluding an attack.".format(len(blocking)))
    if "mentions-outbound-block" in signals:
        reasons.append("The pasted notice describes a platform outbound block, which is a penalty for the "
                       "instance attacking others; that is not a DDoS blackhole and has a different path.")
    if "mentions-content-penalty" in signals:
        reasons.append("The pasted notice is a content penalty record, which is released only after the "
                       "reported URL is remediated and the customer applies on the release page.")
    if "mentions-carrier-or-regulator" in signals:
        reasons.append("Symptom wording points at a carrier, regulator or third-party endpoint block, "
                       "which Alibaba Cloud neither imposes nor can lift.")
    if "mentions-blackhole-or-ddos" in signals and not blocking:
        reasons.append("A blackhole cannot be confirmed or refuted from the verified read-only surface; "
                       "the DDoS console event list is the only authoritative source.")
    if reasons:
        if blocking and not any(s in signals for s in ("mentions-outbound-block", "mentions-content-penalty")):
            return VERDICT_NOT_ATTACK_CONFIG, "medium", reasons
        if "mentions-outbound-block" in signals or "mentions-content-penalty" in signals:
            return VERDICT_PLATFORM_BLOCKOUT, "medium", reasons
        if "mentions-carrier-or-regulator" in signals:
            return VERDICT_EXTERNAL_BLOCK, "medium", reasons
        if "mentions-blackhole-or-ddos" in signals:
            return VERDICT_REAL_DDOS, "low", reasons
    return VERDICT_UNDETERMINED, "low", reasons + [
        "The verified read-only evidence does not single out one area; collect the console items listed "
        "as missing evidence before drawing a conclusion."]


def ports_of_interest(args):
    ports = list(BUSINESS_PORTS)
    for extra in _split_csv(args.expected_ports):
        value = _to_int(extra)
        if value and value not in ports:
            ports.append(value)
    blob = " ".join(filter(None, [args.symptom, args.expected_ports, args.error_string])).lower()
    words = {
        "ssh": 22, "rdp": 3389, "http": 80, "https": 443,
        "redis": 6379, "mysql": 3306, "mssql": 1433, "smtp": 25,
    }
    for token, port in words.items():
        if token in blob and port not in ports:
            ports.append(port)
    for match in re.finditer(r"(?:port|:)\s*(\d{2,5})", blob):
        port = _to_int(match.group(1))
        if port and 0 < port < 65536 and port not in ports:
            ports.append(port)
    for match in re.finditer(r"(\d{2,5})/tcp", blob):
        port = _to_int(match.group(1))
        if port and port not in ports:
            ports.append(port)
    return sorted(set(ports))


# ---------------------------------------------------------------------------
# report rendering
# ---------------------------------------------------------------------------

# A region id is a lowercase slug such as ``cn-hangzhou`` or ``ap-southeast-1``.
# Anything else is not substituted into a console URL (it would build a dead
# link), and the customer is told to switch region in the console instead.
_REGION_ID_PATTERN = re.compile(r"^[a-z]{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")


def console_link(template, region_id):
    """Fill the ``{region_id}`` slot of a region-scoped console deep link.

    The console URLs carry the region as a path segment. Pinning one region in
    the constants sent every customer, in every region, to the same empty page;
    the region actually queried has to be substituted here. When the region is
    missing or malformed the region segment is dropped and an explicit
    "switch the region" note travels with the link instead of a silent guess.
    """
    region = (region_id or "").strip()
    if "{region_id}" not in template:
        return template
    if _REGION_ID_PATTERN.match(region):
        return template.format(region_id=region)
    return "{0} ({1})".format(template.replace("/{region_id}", ""), REGION_SWITCH_NOTE)


MANUAL_ONLY_ACTIONS = [
    "Restart or stop the instance, or force-restart a wedged guest OS",
    "Reinstall the system disk, roll a disk back from a snapshot, or delete snapshots",
    "Kill processes, remove or quarantine files, clean webshells or scheduled tasks",
    "Add, edit or delete security-group rules, or detach/attach and re-assign public IPs or EIPs",
    "Change bandwidth billing, purchase EIP / Anti-DDoS / WAF / CDN, or request a refund",
    "Capture packets, or run any command inside the guest operating system",
]


def render_text(report):
    out = []
    add = out.append
    add("=" * 78)
    add("ECS ATTACK / BLACKHOLE TRIAGE  ({0})".format(SKILL_NAME))
    add("=" * 78)
    add("Provenance      : {0} | region {1}".format(report.get("provenance"), report.get("region_id")))
    add("Observability UA: {0}".format(report.get("user_agent")))
    add("Target selector : {0} | instances examined {1}".format(
        report.get("selector"), len(report.get("targets") or [])))
    add("Customer quote  : {0}".format(report.get("error_string") or "-"))
    inputs = report.get("inputs") or {}
    if inputs:
        add("Collected inputs: domain={0} window={1} peer={2}".format(
            inputs.get("domain") or "-", inputs.get("time_window") or "-",
            inputs.get("observed_peer") or "-"))
        add("Ports evaluated : {0}".format(
            ", ".join(str(p) for p in inputs.get("requested_ports") or []) or "-"))
        if inputs.get("symptom"):
            add("Symptom words   : {0}".format(inputs["symptom"])[:200])
        if inputs.get("platform_notice_text"):
            add("Notice text     : {0}".format(inputs["platform_notice_text"])[:200])
    if report.get("notice_signals"):
        add("Notice signals  : {0}".format(", ".join(report["notice_signals"])))
    add("Verdict         : {0} (confidence {1})".format(report.get("verdict"), report.get("confidence")))
    for reason in report.get("verdict_reasons") or []:
        add("   - {0}".format(reason))
    if report.get("forbidden_actions"):
        add("")
        add("CUSTOMER-IMPOSED CONSTRAINTS (highest priority, never proposed by this skill):")
        for item in report["forbidden_actions"]:
            add("   ! {0}".format(item))
    for target in report.get("targets") or []:
        add("")
        add("-" * 78)
        add("Instance {0} | {1} | status={2} | zone={3}".format(
            target.get("instance_id"), target.get("instance_name") or "-",
            target.get("status"), target.get("zone_id") or "-"))
        add("Public IPs {0} | Private IPs {1} | EIP {2}".format(
            ",".join(target.get("public_ips") or []) or "-",
            ",".join(target.get("private_ips") or []) or "-",
            target.get("eip") or "-"))
        add("Internet max bandwidth out: {0} Mbps | charge {1}".format(
            target.get("internet_max_bandwidth_out"), target.get("instance_charge_type")))
        if target.get("security_groups"):
            add("Security groups: {0}".format(", ".join(target["security_groups"])))
        if target.get("egress_denies") is not None:
            add("Customer-side egress DROP rules in effect: {0}".format(target["egress_denies"]))
        for evaluation in target.get("evaluations") or []:
            effective = evaluation.get("effective") or {}
            add("   {0}/{1}:{2} (peer {3}) -> {4}{5}".format(
                evaluation.get("direction"), evaluation.get("protocol"), evaluation.get("port"),
                evaluation.get("observed_source") or "unspecified",
                effective.get("policy") or "UNDETERMINED",
                "" if effective.get("priority") in (None, "") else
                " [priority {0}, authorisation {1}]".format(effective.get("priority"),
                                                            effective.get("authorisation"))))
            for step in evaluation.get("trace") or []:
                add("        priority {priority:>3} {policy:<6} {protocol} {port_range:<12} "
                    "src {authorisation:<18} covers_peer={covers_observed_peer}".format(**step))
        for note in target.get("eip_notes") or []:
            if note.get("warning"):
                add("   [!] {0}".format(note["warning"]))
            else:
                add("   EIP {ip} allocation={allocation_id} status={status} "
                    "bandwidth={bandwidth_mbps} charge={charge_type}".format(**note))
        if target.get("invocations") is not None:
            add("   Cloud Assistant history (last {0} read-only records):".format(
                len(target["invocations"])))
            for item in target["invocations"]:
                add("     {created} | {command_name} | {command_type} | {status}".format(
                    created=item.get("created") or "-",
                    command_name=item.get("command_name") or "-",
                    command_type=item.get("command_type") or "-",
                    status=item.get("status") or "-"))
            if not target["invocations"]:
                add("     none recorded")
        for finding in target.get("findings") or []:
            add("   [{0}] {1}: {2}".format(finding["severity"].upper(), finding["code"], finding["detail"]))
    add("")
    add("=" * 78)
    add("WHAT THIS SKILL COULD NOT OBSERVE (read-only surface has no verified API for these)")
    add("=" * 78)
    for gap in report.get("gaps") or []:
        add("   - {0}".format(gap))
    add("")
    add("=" * 78)
    add("MANUAL-ONLY RECOVERY PATHS (guidance; never executed by this skill)")
    add("=" * 78)
    for path in report.get("manual_paths") or []:
        add("   * {0}".format(path))
    add("")
    add("=" * 78)
    add("NEVER PERFORMED BY THIS SKILL (manual only, with risk disclosure first)")
    add("=" * 78)
    for action in report.get("prohibited_actions") or MANUAL_ONLY_ACTIONS:
        add("   x {0}".format(action))
    add("")
    add("Console / documentation entry points:")
    for link in report.get("links") or []:
        add("   - {0}".format(link))
    add("")
    add("Suggested evidence to collect from inside the guest (run these yourself, read-only,")
    add("and paste the output back; never include account passwords in a ticket chat):")
    for command in report.get("guest_readonly_suggestions") or []:
        add("   $ {0}".format(command))
    add("")
    add("Suggested hardening checklist:")
    for item in report.get("hardening") or []:
        add("   - {0}".format(item))
    add("")
    add("Hand-off:")
    for item in report.get("handoff") or []:
        add("   -> {0}".format(item))
    add("")
    add("=" * 78)
    add("Summary: {0}".format(report.get("summary")))
    add("STATUS: {0}".format(report.get("status")))
    add("NEXT_ACTION: {0}".format(report.get("next_action")))
    add("=" * 78)
    return "\n".join(out)


def build_report(args):
    warnings = []
    report = {
        "skill": SKILL_NAME,
        "region_id": args.region_id,
        "user_agent": USER_AGENT,
        "selector": None,
        "error_string": args.error_string,
        "inputs": {
            "symptom": args.symptom or None,
            "domain": args.domain or None,
            "time_window": args.time_window or None,
            "observed_peer": args.source_ip or None,
            "platform_notice_text": _cli.mask(args.alarm_text or "")[:400] or None,
            "requested_ports": ports_of_interest(args),
        },
        "provenance": "account=unknown",
        "verdict": VERDICT_UNDETERMINED,
        "confidence": "none",
        "verdict_reasons": [],
        "forbidden_actions": [],
        "targets": [],
        "gaps": [],
        "manual_paths": [],
        "links": [],
        "hardening": [],
        "handoff": [],
        "guest_readonly_suggestions": [],
    }

    identity = get_caller_identity()
    report["provenance"] = provenance_tag(identity)

    for item in _split_csv(args.forbidden_actions):
        report["forbidden_actions"].append(item)

    statuses = fetch_instance_status(warnings, args.region_id)
    selector, instances = fetch_instances(warnings, args.region_id, args)
    report["selector"] = selector
    if not instances:
        report["verdict"] = VERDICT_UNDETERMINED
        report["confidence"] = "none"
        report["verdict_reasons"] = ["No target instance could be resolved."]
        report["links"] = [
            "{0} (DDoS protection events for this account, in {1})".format(
                console_link(DDOS_CONSOLE_URL, args.region_id), args.region_id),
            "{0} (security groups of this region)".format(
                console_link(SECURITY_GROUP_CONSOLE_URL, args.region_id)),
        ]
        report["prohibited_actions"] = list(MANUAL_ONLY_ACTIONS)
        report["gaps"] = ["Every read-only check needs a resolvable instance or public IP in this region."]
        report["status"] = STATUS_DEGRADED
        report["summary"] = ("No instance matched the supplied identifiers in {0}; the account checked is "
                            "{1}.".format(args.region_id, report["provenance"]))
        report["next_action"] = ("Re-run with --instance-id or --public-ip belonging to the account reported "
                                 "by the identity check, or correct the region. Never assume the address is "
                                 "in this account: 'not your asset' style replies are often a duplicate "
                                 "request or a wrong-account lookup.")
        report["warnings"] = warnings
        return report

    catalog = fetch_security_group_catalog(warnings, args.region_id)
    eips = fetch_eips(warnings, args.region_id)

    ports = ports_of_interest(args)
    signals = detect_notice_signals(args.alarm_text, args.symptom)
    report["notice_signals"] = signals

    for row in instances[:MAX_SECURITY_GROUPS_PER_INSTANCE]:
        instance_id = row.get("InstanceId")
        if not instance_id:
            continue
        public_ips = _as_list(_dig(row, "PublicIpAddress", "IpAddress", default=[]))
        private_ips = _as_list(_dig(row, "VpcAttributes", "PrivateIpAddress", "IpAddress", default=[]))
        if not private_ips:
            private_ips = _as_list(_dig(row, "InnerIpAddress", "IpAddress", default=[]))
        sg_ids = [s for s in _as_list(_dig(row, "SecurityGroupIds", "SecurityGroupId", default=[])) if s]
        target = {
            "instance_id": instance_id,
            "instance_name": row.get("InstanceName"),
            "status": row.get("Status") or statuses.get(instance_id) or "Unknown",
            "control_plane_status": statuses.get(instance_id),
            "zone_id": row.get("ZoneId"),
            "instance_charge_type": row.get("InstanceChargeType"),
            "internet_max_bandwidth_out": row.get("InternetMaxBandwidthOut"),
            "internet_charge_type": row.get("InternetChargeType"),
            "public_ips": public_ips,
            "private_ips": private_ips,
            "eip": _dig(row, "EipAddress", "IpAddress") or None,
            "security_groups": sg_ids,
            "evaluations": [],
            "findings": [],
            "eip_notes": [],
        }
        rules = []
        for sg_id in sg_ids[:MAX_SECURITY_GROUPS_PER_INSTANCE]:
            _, sg_rules = fetch_security_group_rules(warnings, args.region_id, sg_id)
            if not sg_rules and sg_id in catalog:
                target["findings"].append({
                    "code": "SG-RULES-UNREADABLE",
                    "severity": "medium",
                    "detail": ("No rules could be read for {0}; it may belong to another account or be "
                               "inherited. Confirm ownership in the security-group list.").format(sg_id)})
            for rule in sg_rules:
                rule["_sg"] = sg_id
            rules.extend(sg_rules)
        if len(sg_ids) > 1:
            target["findings"].append({
                "code": "SG-MULTI-GROUP-APPROXIMATION",
                "severity": "info",
                "detail": ("{0} security groups are attached; their rules were merged and ordered by "
                           "priority for the evaluation above. Merging is an approximation of the "
                           "platform's own rule evaluation, so confirm the final decision in the "
                           "console before changing anything.").format(len(sg_ids))})
        evaluations, findings = analyse_rules(rules, ports, args.source_ip)
        target["evaluations"] = evaluations
        target["findings"].extend(findings)
        target["egress_denies"] = len([r for r in rules if (r.get("_direction") or "") == "egress"
                                       and _policy_of(r) == "DROP"])
        matched_eips, eip_notes = analyse_eips(eips, instance_id, public_ips)
        target["eip_notes"] = eip_notes
        target["eip_bound"] = bool(matched_eips)
        if public_ips and not matched_eips:
            target["eip_notes"].append({
                "warning": ("{0} reads as a fixed public IP of the instance, not an associated EIP. Two "
                            "consequences: a proxied defence product pointed at another address is "
                            "silently bypassed, and replacing this address later requires the "
                            "bandwidth-billing change plus the fixed-public-IP-to-EIP conversion.").format(
                                public_ips[0])})
        if args.include_invocations:
            target["invocations"] = analyse_invocations(
                fetch_invocation_history(warnings, args.region_id, instance_id), args.time_window)
        else:
            target["invocations"] = None
        report["targets"].append(target)

    first = report["targets"][0] if report["targets"] else None
    all_findings = [f for t in report["targets"] for f in t["findings"]]
    verdict, confidence, reasons = build_verdict(all_findings, first, signals)
    report["verdict"] = verdict
    report["confidence"] = confidence
    report["verdict_reasons"] = reasons

    # Gaps: capabilities the tier genuinely cannot observe from a verified
    # read-only API. Stated explicitly instead of being inferred.
    report["gaps"] = [
        ("DDoS blackhole / scrubbing events and the mitigation thresholds: no verified read-only action "
         "exists in this skill's surface, so the state is UNCONFIRMED. Open the DDoS protection asset "
         "and event pages and share the event detail."),
        ("Security Center alarm details (virus, worm, webshell, brute force, outbound-attack blocks): not "
         "readable through a verified read-only action here; the absence of an alarm must not be used as "
         "proof, and neither must its presence be used as proof that the platform should clean it."),
        ("Content-penalty records and their release status, 25-port unblocking applications, and account "
         "freezes: console-only, handled by an approval flow this skill cannot see or accelerate."),
        ("Real-time in-guest connections, processes, load and access logs: this skill does not run "
         "commands inside the operating system, so those readings must be taken by the customer."),
        ("Attack source attribution, whether the attack hit a domain or the IP, and any release timer: "
         "not determinable from the platform for DDoS events."),
    ]

    report["links"] = [
        "{0} (DDoS protection: blackhole / scrubbing events, and the downloadable traffic evidence "
        "package under the event details)".format(console_link(DDOS_CONSOLE_URL, args.region_id)),
        "{0} (Security Center alarms)".format(console_link(SECURITY_CENTER_ALARMS_URL, args.region_id)),
        "{0} (Security Center full-disk scan)".format(
            console_link(SECURITY_CENTER_VIRUS_KILL_URL, args.region_id)),
        "{0} (Security Center overview; pay-as-you-go switch, billing is T+1)".format(
            console_link(SECURITY_CENTER_OVERVIEW_URL, args.region_id)),
        "{0} (penalty record list and the self-service 'apply to release the penalty' page)".format(PENALTY_RELEASE_URL),
        "{0} (Security Center sign-in)".format(SECURITY_CENTER_LOGIN_URL),
        "{0} (security groups of this region)".format(console_link(SECURITY_GROUP_CONSOLE_URL, args.region_id)),
        "{0} (per-instance billing detail, to separate attack traffic cost from product cost)".format(BILLING_DETAIL_URL),
        DOC_SG_START,
        DOC_SG_CASES,
        DOC_WINDOWS_HIGH_BANDWIDTH,
        DOC_SNAPSHOT_CREATE,
        DOC_SNAPSHOT_BILLING,
        DOC_HARDENING_SUMMARY,
        DOC_SAS_FREE_TRIAL,
        DOC_SAS_PAY_AS_YOU_GO,
    ]

    report["manual_paths"] = _manual_paths(verdict, signals, first)
    report["prohibited_actions"] = list(MANUAL_ONLY_ACTIONS)
    report["links"].extend(["{0} -> {1}".format(step, url) for step, url in EIP_CONVERSION_STEPS])
    report["hardening"] = [
        "Restrict 22 and 3389 to your own office or VPN egress address instead of {0}; keep only 80/443 "
        "public. Priority matters: a DROP rule with a lower numeric priority overrides every ACCEPT "
        "rule, so prefer a narrow allow-list over per-IP blocks.".format(FULL_COVERAGE_CIDRS[0]),
        "Keep {0} allowed on port 22 if browser-based and Workbench sign-in must keep working.".format(
            CONSOLE_SSH_WHITELIST_CIDR),
        "Use strong unique passwords plus key-based sign-in, and patch the high-severity vulnerabilities "
        "listed in Security Center (take a snapshot before patching).",
        "Set a recurring snapshot policy so a ransomware or compromise incident can be rolled back; "
        "rollback is irreversible for the current disk content, so snapshot the live disk first.",
        "Deploy a load and connection history collector such as atop so a later incident can be read "
        "back in time; without it the on-scene evidence disappears once the box reboots.",
        "Do not rely on a reboot to fix an attack: rebooting a wedged guest OS restores service but "
        "destroys the evidence needed to explain the cause.",
        "Full list of hardening items: {0}".format(DOC_HARDENING_SUMMARY),
    ]
    report["guest_readonly_suggestions"] = [
        "ss -tunap | head -n 100                     # who is connected right now, and which process",
        "netstat -ano | findstr :<PORT>               # Windows: peers and PID for one port",
        "tasklist | findstr <PID>                     # Windows: resolve that PID to a program",
        "lsof -nP -i | grep <PEER_IP>                 # confirm whether a given peer is really served",
        "ps aux --sort=-%cpu | head -n 15             # what is burning CPU",
        "awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -n 20",
    ]
    report["handoff"] = _handoff(verdict, signals, all_findings)

    degraded = bool(warnings) or verdict in (VERDICT_REAL_DDOS, VERDICT_UNDETERMINED)
    report["warnings"] = warnings
    report["status"] = STATUS_DEGRADED if degraded else STATUS_OK
    report["summary"] = _summary(report)
    report["next_action"] = _next_action(report)
    return report


def _manual_paths(verdict, signals, target):
    paths = [
        "Wait for the automatic release: a blackhole lifts on its own once the attack stops, and repeated "
        "attacks extend the window. There is no supported early manual removal, and this skill does not "
        "promise a number of minutes; the DDoS console event detail is the only authoritative timing.",
        "Trim exposure while blocked: pause the DNS record of the affected domain so visitors stop "
        "converging on the blackholed address, and re-point it after release.",
        "Replace the public address if attacks keep landing on it: a fixed public IP cannot be swapped "
        "directly, so the order is: " + " -> ".join(step for step, _ in EIP_CONVERSION_STEPS) + ". "
        "Bandwidth and EIP changes may add cost, so confirm the billing page before acting.",
        "Move to a proxied mitigation product (Anti-DDoS, CDN or WAF) for real protection. Three "
        "separate routes, do not mix them up: (a) buying the product, activating it, onboarding the "
        "domain onto it and switching on the basic protection settings are self-service - start on the "
        "corresponding product page in the Alibaba Cloud console, no specialist has to be involved and "
        "none is needed before protection exists; (b) an Enterprise-edition quote or a solution design "
        "is a pre-sales conversation; (c) tuning complex custom rules (rate-limit thresholds, bot "
        "policies, precise protection policies) is where a ticket gets product-side help.",
        "Before any restart, on-machine assistance or rollback: create snapshots of every disk first "
        "({0}); snapshots bill by capacity ({1}). Deleting them afterwards is also a human step.".format(
            DOC_SNAPSHOT_CREATE, DOC_SNAPSHOT_BILLING),
        "For an incident report or a police report: download the traffic evidence package from the DDoS "
        "console event details. Alibaba Cloud does not file a report on your behalf, does not modify your "
        "application source, and does not decrypt ransomware-encrypted data.",
    ]
    if "mentions-outbound-block" in signals:
        paths.insert(0, (
            "An outbound block announced by SMS means the instance was attacking others and the platform "
            "cut the outbound path. It lifts when the penalty is released; first remediate the abuse "
            "(usually a compromised service or a weak-password database), then apply on the release page."))
    if "mentions-content-penalty" in signals:
        paths.insert(0, (
            "A URL shielded for illegal content is not an attack and is not lifted by paying for a "
            "security product: delete the reported URL, verify it returns 404, then apply to release the "
            "penalty on the self-service page. If the reported file no longer exists, no release is needed."))
    if "mentions-port-25" in signals:
        paths.insert(0, (
            "Port 25 is closed by default on newly purchased instances for anti-spam policy. Apply for "
            "unblocking with a filed domain and the required attachments, or switch to 465/another SMTP "
            "port. Only IPv4 outbound 25 can be released; IPv6 is not supported."))
    if "mentions-account-freeze" in signals:
        paths.insert(0, (
            "A security-related account freeze lifts automatically on the announced date and cannot be "
            "accelerated. Stopping pay-as-you-go instances by hand reduces part of the spend; compute, "
            "memory and disk charges continue."))
    if target and target.get("status") and target["status"] != "Running":
        paths.insert(0, (
            "The instance is not Running, so settle the instance-lifecycle question first through the "
            "instance-state skill; this skill stops here for that area."))
    return paths


def _handoff(verdict, signals, findings):
    handoff = []
    if "mentions-host-compromise" in signals or verdict == VERDICT_PLATFORM_BLOCKOUT:
        handoff.append("Miner, worm, webshell or backdoor cleanup: hand off to "
                       "alibabacloud-mining-attack-diagnosis, Security Center, or a human engineer. This "
                       "skill identifies the area and points at the pages; it never cleans the host.")
    handoff.append("Instance stuck, cannot boot, restart-in-progress: area:instance-state-diagnosis.")
    handoff.append("Disk added but capacity not visible, extend-volume work: area:disk-expand-diagnosis.")
    handoff.append("Slow disk IO or performance below spec: area:resource-bottleneck.")
    handoff.append("Disk full or inode exhaustion: the disk-capacity skill; a full log volume can itself "
                   "make a service refuse connections and look like an attack.")
    handoff.append("Anti-DDoS, WAF or CDN: buying, activating, onboarding the domain and turning on the "
                   "basic protection settings are self-service on the corresponding product page in the "
                   "console, so nothing has to wait for a specialist. Only an Enterprise-edition quote or "
                   "a solution design goes to pre-sales, and only complex custom rule or bot-policy "
                   "tuning needs a ticket.")
    handoff.append("Penalty release is a self-service application on the penalty record page; the review "
                   "conclusion is decided by the platform, so this skill predicts no turnaround and "
                   "promises no fixed number of days. File a ticket only if a rejection needs a human "
                   "re-check.")
    handoff.append("Fee refunds, reductions or compensation, account freezes, filing a police report, and "
                   "appeals to third parties such as messengers or domain registrars: commercial or human "
                   "handling only.")
    if any(f["code"] == "SG-RULES-UNREADABLE" for f in findings):
        handoff.append("Security groups that cannot be read with the current identity: a human with the "
                       "owning account's console should confirm the rule set.")
    return handoff


def _summary(report):
    targets = report.get("targets") or []
    counts = {}
    for target in targets:
        for finding in target["findings"]:
            counts[finding["code"]] = counts.get(finding["code"], 0) + 1
    basis = ", ".join("{0}={1}".format(k, v) for k, v in sorted(counts.items())) or "no rule findings"
    return ("Read-only triage over {0} instance(s) in {1}; verdict {2} (confidence {3}); findings: {4}. "
            "Blackhole and alarm state are console-only and were not asserted.".format(
                len(targets), report.get("region_id"), report.get("verdict"),
                report.get("confidence"), basis))


def _next_action(report):
    verdict = report.get("verdict")
    if report.get("status") == STATUS_FAIL:
        return "Restore the credential chain with 'aliyun sts get-caller-identity' in your own terminal, then re-run."
    if verdict == VERDICT_NOT_ATTACK_CONFIG:
        return ("Apply the listed security-group corrections by hand, retest the service, and only then "
                "resume the attack hypothesis. Do not restart or reinstall anything first.")
    if verdict == VERDICT_NOT_ATTACK_RESOURCE:
        return "Hand off to the instance-state skill; the outage is not an attack area."
    if verdict == VERDICT_PLATFORM_BLOCKOUT:
        return "Remediate the reported abuse or content, then apply on the penalty-release page; provide the evidence list in the report."
    if verdict == VERDICT_EXTERNAL_BLOCK:
        return "Assemble the appeal evidence for the blocking party; Alibaba Cloud cannot lift an external, carrier or regulator block."
    if report.get("status") == STATUS_DEGRADED:
        return ("Open the DDoS protection event page, capture the blackhole or scrubbing event detail and "
                "the asset thresholds, then re-run this triage with those readings pasted in; no release "
                "time can be quoted before that.")
    return "Collect the guest-side readings listed above and re-run the triage with them."


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog=SKILL_NAME,
        description=("Read-only ECS attack / blackhole / blockout triage. Guidance only: this tool "
                     "never changes cloud resources."),
    )
    parser.add_argument("--region-id", required=True,
                        help="Region of the instance, for example cn-hangzhou (echoed back in the report)")
    parser.add_argument("--instance-id", help="Comma-separated i-* instance ids")
    parser.add_argument("--public-ip", help="Fixed public IP to resolve to an instance")
    parser.add_argument("--eip-address", help="Elastic IP address to resolve to an instance")
    parser.add_argument("--private-ip", help="Private IP to resolve to an instance")
    parser.add_argument("--domain", help="Affected domain, recorded for the evidence pack (not resolved)")
    parser.add_argument("--symptom", help="Customer's own words about the outage")
    parser.add_argument("--error-string", default="",
                        help="Verbatim client error; recognised: {0}".format(", ".join(QUOTABLE_ERROR_STRINGS)))
    parser.add_argument("--expected-ports", help="Extra TCP ports to evaluate, comma-separated")
    parser.add_argument("--source-ip", help="Client address whose traffic should be evaluated")
    parser.add_argument("--alarm-text", help="Verbatim platform notice (SMS or internal message) if received")
    parser.add_argument("--time-window", help="Incident window, e.g. 2026-09-17T10:00Z,2026-09-17T14:00Z")
    parser.add_argument("--forbidden-actions",
                        help="Things the customer forbids (e.g. release IP, stop instance, reset disk); "
                             "treated as binding constraints")
    parser.add_argument("--no-invocations", dest="include_invocations", action="store_false", default=True,
                        help="Skip the read-only Cloud Assistant history lookup")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def _run_selftest():
    """Offline boundary locks for the security-group rule-evaluation core.

    The drop/accept precedence, port-range and peer-coverage decisions are what
    tell a customer whether a port is really filtered by the security group (as
    opposed to an actual attack or a blackhole), so an off-by-one range or a
    wrong precedence tie-break would flip a connectivity verdict. Pure functions
    on crafted rules only - no cloud calls, no credentials.
    """
    rc = 0

    def expect(name, cond):
        nonlocal rc
        print("PASS" if cond else "FAIL", name)
        if not cond:
            rc = 1

    # port ranges: inclusive, and the all-port forms.
    expect("pr_all", _port_range_matches("-1/-1", 80) is True)
    expect("pr_empty_all", _port_range_matches("", 80) is True)
    expect("pr_exact", _port_range_matches("80/80", 80) is True)
    expect("pr_exact_miss", _port_range_matches("80/80", 81) is False)
    expect("pr_wide", _port_range_matches("0/65535", 443) is True)
    expect("pr_inclusive_hi", _port_range_matches("1024/2048", 2048) is True)
    expect("pr_above_hi", _port_range_matches("1024/2048", 2049) is False)
    expect("pr_bad", _port_range_matches("bad", 80) is False)
    expect("pr_port_none", _port_range_matches("22/22", None) is True)

    # protocol filter.
    expect("proto_all", _protocol_matches("ALL", "TCP") is True)
    expect("proto_blank_all", _protocol_matches("", "UDP") is True)
    expect("proto_case", _protocol_matches("tcp", "TCP") is True)
    expect("proto_diff", _protocol_matches("TCP", "UDP") is False)
    expect("proto_icmp", _protocol_matches("ICMP", "TCP") is False)

    # source coverage: CIDR, exact ip, group/prefix-list undetermined, comma list.
    expect("src_full", _source_matches("0.0.0.0/0", "1.2.3.4") is True)
    expect("src_in", _source_matches("10.0.0.0/8", "10.1.2.3") is True)
    expect("src_out", _source_matches("10.0.0.0/8", "11.1.1.1") is False)
    expect("src_exact", _source_matches("1.2.3.4", "1.2.3.4") is True)
    expect("src_group_undetermined", _source_matches("sg-abc", "1.2.3.4") is None)
    expect("src_no_peer", _source_matches("1.2.3.4", None) is None)
    expect("src_empty", _source_matches("", "1.2.3.4") is False)
    expect("src_comma", _source_matches("10.0.0.0/8, 11.0.0.0/8", "11.2.2.2") is True)

    # precedence: lower priority number wins, drop before accept at equal priority.
    expect("prec_drop_first", _precedence({"Priority": "1", "Policy": "Drop"})
           < _precedence({"Priority": "1", "Policy": "Accept"}))
    expect("prec_low_num_first", _precedence({"Priority": "1", "Policy": "Accept"})
           < _precedence({"Priority": "2", "Policy": "Accept"}))

    # policy normalisation.
    expect("pol_drop", _policy_of({"Policy": "Drop"}) == "DROP")
    expect("pol_accept", _policy_of({"Policy": "Accept"}) == "ACCEPT")

    # evaluate_port end-to-end decisions.
    shadow = [
        {"Direction": "ingress", "IpProtocol": "TCP", "PortRange": "22/22", "Priority": "1",
         "Policy": "Drop", "SourceCidrIp": "0.0.0.0/0"},
        {"Direction": "ingress", "IpProtocol": "TCP", "PortRange": "22/22", "Priority": "2",
         "Policy": "Accept", "SourceCidrIp": "0.0.0.0/0"},
    ]
    ev = evaluate_port(shadow, "ingress", "TCP", 22, "1.2.3.4")
    expect("ev_drop_shadows_accept", (ev["effective"] or {}).get("policy") == "DROP")
    expect("ev_effective_priority", (ev["effective"] or {}).get("priority") == 1)

    scoped = [{"Direction": "ingress", "IpProtocol": "TCP", "PortRange": "80/80", "Priority": "1",
               "Policy": "Accept", "SourceCidrIp": "192.168.0.0/16"}]
    expect("ev_peer_not_authorised",
           (evaluate_port(scoped, "ingress", "TCP", 80, "8.8.8.8")["effective"] or {}).get("policy")
           == "NO-MATCHING-RULE")
    expect("ev_default_deny_no_rule",
           (evaluate_port([], "ingress", "TCP", 443, "1.2.3.4")["effective"] or {}).get("policy")
           == "NO-MATCHING-RULE")
    group_rule = [{"Direction": "ingress", "IpProtocol": "TCP", "PortRange": "443/443",
                   "Priority": "1", "Policy": "Accept", "SourceCidrIp": "sg-abc"}]
    expect("ev_needs_peer_undetermined",
           (evaluate_port(group_rule, "ingress", "TCP", 443, None)["effective"] or {}).get("policy")
           == "UNDETERMINED-NEEDS-PEER")

    # analyse_rules finding codes.
    _, f_shadow = analyse_rules(shadow, [22], "1.2.3.4")
    expect("ar_deny_shadows", any(x["code"] == "SG-DENY-SHADOWS-ALLOW" for x in f_shadow))
    expect("ar_console_ssh_missing", any(x["code"] == "SG-CONSOLE-SSH-WHITELIST-MISSING" for x in f_shadow))
    _, f_none = analyse_rules([], [80], None)
    expect("ar_no_ingress_rule", any(x["code"] == "SG-NO-INGRESS-RULE" for x in f_none))
    _, f_peer = analyse_rules(scoped, [80], "8.8.8.8")
    expect("ar_peer_not_authorised", any(x["code"] == "SG-PEER-NOT-AUTHORISED" for x in f_peer))
    expose = [{"Direction": "ingress", "IpProtocol": "TCP", "PortRange": "3306/3306", "Priority": "1",
               "Policy": "Accept", "SourceCidrIp": "0.0.0.0/0"}]
    _, f_exp = analyse_rules(expose, [3306], "1.2.3.4")
    expect("ar_public_admin_exposure", any(x["code"] == "SG-PUBLIC-ADMIN-EXPOSURE" for x in f_exp))
    # console whitelist present -> no SSH-whitelist-missing finding for port 22.
    wl = [{"Direction": "ingress", "IpProtocol": "TCP", "PortRange": "22/22", "Priority": "1",
           "Policy": "Accept", "SourceCidrIp": CONSOLE_SSH_WHITELIST_CIDR}]
    _, f_wl = analyse_rules(wl, [22], "1.2.3.4")
    expect("ar_console_whitelisted",
           not any(x["code"] == "SG-CONSOLE-SSH-WHITELIST-MISSING" for x in f_wl))

    # analyse_eips: an unbound Available EIP is a finding, not something to drop.
    eip_bound = [{"IpAddress": "47.0.0.9", "AllocationId": "eip-bound1", "Status": "InUse",
                  "InstanceId": "i-1", "Bandwidth": "5"}]
    m_bound, n_bound = analyse_eips(eip_bound, "i-1", [])
    expect("eips_bound_matched", len(m_bound) == 1 and not any("unbound_eip" in x for x in n_bound))
    eip_unbound = [{"IpAddress": "121.43.255.114", "AllocationId": "eip-x1", "Status": "Available",
                    "Bandwidth": "5"}]
    m_un, n_un = analyse_eips(eip_unbound, "i-1", ["120.26.215.9"])
    expect("eips_unbound_not_matched_to_instance", m_un == [])
    expect("eips_unbound_surfaced", any("unbound_eip" in x for x in n_un))
    expect("eips_unbound_quotes_the_address",
           any((x.get("unbound_eip") or {}).get("ip") == "121.43.255.114"
               and (x.get("unbound_eip") or {}).get("allocation_id") == "eip-x1" for x in n_un))
    # the rendered warning line itself must carry the numbers (the text renderer prints
    # warning-shaped notes verbatim; a category without an address cannot be quoted)
    expect("eips_unbound_warning_carries_numbers",
           any("121.43.255.114" in (x.get("warning") or "") and "eip-x1" in (x.get("warning") or "")
               for x in n_un))
    # bound elsewhere -> not an unbound finding for this instance
    m_other, n_other = analyse_eips([{"IpAddress": "1.2.3.4", "Status": "InUse",
                                      "InstanceId": "i-other"}], "i-1", ["9.9.9.9"])
    expect("eips_bound_elsewhere_ignored", not any("unbound_eip" in x for x in n_other))
    # no public IP on the instance -> nothing to contrast, keep the report quiet
    _, n_quiet = analyse_eips(eip_unbound, "i-1", [])
    expect("eips_unbound_quiet_without_fixed_ip", not any("unbound_eip" in x for x in n_quiet))
    _, n_empty = analyse_eips([], "i-1", ["9.9.9.9"])
    expect("eips_empty_list_safe", isinstance(n_empty, list))

    # console_link: the region actually queried must reach the deep link, and no
    # template may keep a pinned region or leak its placeholder to a customer.
    region_scoped = (DDOS_CONSOLE_URL, SECURITY_CENTER_ALARMS_URL,
                     SECURITY_CENTER_VIRUS_KILL_URL, SECURITY_CENTER_OVERVIEW_URL,
                     SECURITY_GROUP_CONSOLE_URL)
    expect("link_region_substituted",
           console_link(DDOS_CONSOLE_URL, "cn-beijing")
           == "https://yundun.console.aliyun.com/?p=ddos#/asset/ecs/cn-beijing")
    expect("link_no_pinned_hangzhou",
           all("cn-hangzhou" not in console_link(t, "cn-beijing") for t in region_scoped))
    expect("link_no_placeholder_left",
           all("{region_id}" not in console_link(t, "ap-southeast-1") for t in region_scoped))
    expect("link_region_trimmed",
           console_link(SECURITY_GROUP_CONSOLE_URL, "  cn-shanghai ").endswith("/cn-shanghai"))
    expect("link_bad_region_gets_switch_note",
           "switch the region" in console_link(SECURITY_CENTER_ALARMS_URL, "")
           and "{region_id}" not in console_link(SECURITY_CENTER_ALARMS_URL, ""))
    expect("link_bad_region_not_injected",
           "evil" not in console_link(DDOS_CONSOLE_URL, "cn-hangzhou#evil"))
    expect("link_plain_url_untouched",
           console_link(SECURITY_CENTER_LOGIN_URL, "cn-beijing") == SECURITY_CENTER_LOGIN_URL)
    expect("link_pay_as_you_go_style_preserved",
           console_link(SECURITY_CENTER_OVERVIEW_URL, "cn-hongkong")
           .endswith("#/overview/home/cn-hongkong"))

    # Customer-facing routing: mitigation products are self-service to start, so
    # neither the manual paths nor the hand-off may call them specialist work.
    routing = " ".join(_manual_paths(VERDICT_REAL_DDOS, [], None)
                       + _handoff(VERDICT_REAL_DDOS, [], []))
    expect("routing_products_self_service",
           "choosing those products is human work" not in routing
           and "self-service" in routing)
    expect("routing_no_specialist_onboarding",
           "onboarding and rule authoring: a human specialist" not in routing)
    expect("routing_penalty_self_service_applied",
           "self-service application" in routing and "no fixed number of days" in routing)

    print("SELFTEST:", "PASS" if rc == 0 else "FAIL")
    return rc


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if "--selftest" in argv:
        return _run_selftest()
    args = parse_args(argv)
    if args.error_string and args.error_string not in QUOTABLE_ERROR_STRINGS:
        # Unrecognised text is kept as a customer quote only: it is never
        # promoted to an official error code in the report.
        args.error_string = "{0} (customer-reported text, not an official error code)".format(args.error_string)
    try:
        report = build_report(args)
    except CredentialError as exc:
        sys.stderr.write("[WARN] {0}\n".format(exc))
        print("STATUS: {0}".format(STATUS_FAIL))
        print("NEXT_ACTION: Authenticate first: run 'aliyun sts get-caller-identity' yourself. This skill never "
              "collects account passwords or key values.")
        print("DETAIL: {0}".format(exc))
        return 2
    except CliError as exc:
        sys.stderr.write("[WARN] {0}\n".format(_cli.mask(exc)))
        print("STATUS: {0}".format(STATUS_FAIL))
        print("NEXT_ACTION: grant the read-only actions listed below, then re-run.")
        print(_cli.permission_hint([
            "ecs:DescribeInstances", "ecs:DescribeInstanceStatus", "ecs:DescribeSecurityGroups",
            "ecs:DescribeSecurityGroupAttribute", "ecs:DescribeInvocations",
            "vpc:DescribeEipAddresses", "sts:GetCallerIdentity"]))
        return 2
    if args.output == "json":
        print(json.dumps(report, indent=2, default=str))
    else:
        print(render_text(report))
    if args.verbose:
        for warning in report.get("warnings") or []:
            sys.stderr.write("{0}\n".format(_cli.mask(warning)))
    if not report.get("targets"):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
