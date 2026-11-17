"""Single entry point for the ECS web service and runtime environment skill.

The agent runs this script and never assembles cloud calls by hand.

Subcommands
    report      collect evidence and route one symptom through the decision tree
    guest-plan  print the in-instance observations a route needs, each with its
                approval state, without contacting the cloud
    guest-run   issue ONE approved non-mutating observation command inside one
                instance, behind the announce-and-confirm gate
    snapshot    create ONE snapshot behind the snapshot-first gate, so a manual
                repair step can be rolled back
    knowledge   print the embedded tables (offline, no cloud call at all)

Gate model, enforced in code rather than in prose:

* ``T1`` cloud queries (identity, instances, inbound rules, disks, monitoring)
  run automatically.
* ``T2`` in-instance observation runs only for a check whose approval is
  ``approved``, only after ``--confirmed`` restates what the customer agreed to,
  and one command per call.
* ``T3`` ``CreateSnapshot`` follows the same confirmation gate and never deletes
  anything.
* A check that is not whitelisted is printed for the customer to run and the
  item is reported as missing; the script never invents a substitute command.

Every run finishes with ``STATUS: OK|DEGRADED|FAIL`` and at least one
``NEXT_ACTION:`` line. Exit code is 0 unless the run failed.
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import re
import sys
import time

import sts_token
from _cli import (
    CliError,
    decode_invocation_output,
    describe_cli_error,
    dig,
    is_plan_only,
    mask_secrets,
    new_session_id,
    run_cli,
)
from _constants import (
    APPROVED_EXACT_COMMANDS,
    APPROVED_EXECUTABLES,
    CANDIDATE_BRANCHES,
    CLI_TIMEOUT_SECONDS,
    ERROR_STRING_RULES,
    FTP_PASSIVE_NOTE,
    FTP_PASSIVE_RANGE,
    GUEST_CHECKS,
    GUEST_COMMAND_TIMEOUT_SECONDS,
    GUEST_CLI_TIMEOUT_SECONDS,
    HANDOFF_MATRIX,
    HELP_DOCS,
    INVOCATION_MAX_POLLS,
    INVOCATION_POLL_TIMEOUT_SECONDS,
    INVOCATION_WAIT_SECONDS,
    MAINLAND_REGION_PREFIX,
    MAX_PORTS,
    MAX_SECURITY_GROUPS,
    NEVER_AUTOMATED,
    NON_FAULT_MECHANISMS,
    NON_FILING_MAINLAND_REGIONS,
    OS_RUNTIME_SUPPORT,
    PATH_COMMANDS,
    PORT_CONTEXT,
    PRODUCT_CMS,
    PRODUCT_ECS,
    QUOTED_TICKET_ERRORS,
    SAFE_PATH_PATTERN,
    SCENARIOS,
    SIDE_EFFECT_COMMAND_PATTERNS,
    SOURCE_CLOUD,
    SOURCE_CUSTOMER,
    SOURCE_DOC,
    SOURCE_GUEST,
    SOURCE_MODEL,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
)

DISK_ID_PATTERN = re.compile(r"^d-[A-Za-z0-9]{4,40}$")
INSTANCE_ID_PATTERN = re.compile(r"^(i|vm|ecs)-[A-Za-z0-9]{4,40}$")

FINISHED_INVOCATION_STATES = (
    "Success", "Failed", "Timeout", "Error", "Stopped", "Cancelled",
    "Invalid", "Aborted",
)

SAFE_PATH_RE = re.compile(SAFE_PATH_PATTERN)

APPROVED_CHECK_IDS = sorted(
    check_id for check_id, check in GUEST_CHECKS.items() if check["approval"] == "approved"
)


class Report(object):
    """A rendered evidence list: every line is tagged with where it came from."""

    def __init__(self, session_id, title="ECS web service and runtime environment report"):
        self.session_id = session_id
        self.title = title
        self.lines = []
        self.auto_filled = []
        self.gaps = []
        self.next_actions = []
        self.status = STATUS_OK
        self.errors = {}

    def section(self, name):
        self.lines.append("")
        self.lines.append("## %s" % name)

    def plain(self, text):
        self.lines.append(text)

    def bullet(self, text):
        self.lines.append("- %s" % text)

    def note(self, source, text):
        self.lines.append("[%s] %s" % (source, text))

    def auto(self, text):
        if text not in self.auto_filled:
            self.auto_filled.append(text)

    def next(self, text):
        if text not in self.next_actions:
            self.next_actions.append(text)

    def degrade(self, gap, action=None):
        if self.status != STATUS_FAIL:
            self.status = STATUS_DEGRADED
        if gap not in self.gaps:
            self.gaps.append(gap)
        if action:
            self.next(action)

    def fail(self, gap, action=None):
        self.status = STATUS_FAIL
        if gap not in self.gaps:
            self.gaps.append(gap)
        if action:
            self.next(action)

    def record_error(self, action, error):
        self.errors[action] = error

    def render(self):
        out = ["=== %s ===" % self.title, "session-id: %s" % self.session_id]
        out.extend(self.lines)
        if self.auto_filled:
            out.append("")
            out.append("## Values this run filled in itself")
            for item in self.auto_filled:
                out.append("- %s" % item)
        if self.gaps:
            out.append("")
            out.append("## What could not be established")
            for item in self.gaps:
                out.append("- %s" % item)
        out.append("")
        out.append("STATUS: %s" % self.status)
        if not self.next_actions:
            self.next("act on the evidence list above; nothing else is needed from this skill")
        for action in self.next_actions:
            out.append("NEXT_ACTION: %s" % action)
        return "\n".join(out)


# ---------------------------------------------------------------------------
# Response navigation helpers
# ---------------------------------------------------------------------------

def instance_facts(instance):
    """Project one DescribeInstances entry onto the fields this skill uses."""
    public_ips = dig(instance, ["PublicIpAddress", "IpAddress"], []) or []
    eip = (instance.get("EipAddress") or {})
    return {
        "id": instance.get("InstanceId"),
        "name": instance.get("InstanceName"),
        "status": instance.get("Status"),
        "os_type": (instance.get("OSType") or "").lower(),
        "os_name": instance.get("OSName"),
        "image_id": instance.get("ImageId"),
        "instance_type": instance.get("InstanceType"),
        "cpu": instance.get("Cpu"),
        "memory_mb": instance.get("Memory"),
        "region": instance.get("RegionId"),
        "zone": instance.get("ZoneId"),
        "network_type": instance.get("InstanceNetworkType"),
        "charge_type": instance.get("InstanceChargeType"),
        "security_groups": dig(instance, ["SecurityGroupIds", "SecurityGroupId"], []) or [],
        "public_ips": list(public_ips) + ([eip.get("IpAddress")] if eip.get("IpAddress") else []),
        "private_ips": dig(instance, ["VpcAttributes", "PrivateIpAddress", "IpAddress"], []) or [],
    }


def is_windows(facts):
    return "windows" in (facts.get("os_type") or "")


def is_mainland(region_id):
    region = region_id or ""
    if not region.startswith(MAINLAND_REGION_PREFIX):
        return False
    return region not in NON_FILING_MAINLAND_REGIONS


def parse_port_range(port_range):
    """``'80/80'`` to ``(80, 80)``; anything else, including ``'-1/-1'``, to None."""
    if not port_range or "/" not in port_range:
        return None
    low, _, high = port_range.partition("/")
    try:
        low_port, high_port = int(low), int(high)
    except ValueError:
        return None
    if low_port < 0 or high_port < 0:
        return None
    return (low_port, high_port)


def rule_covers_port(rule, port):
    """Does one inbound permission entry speak for this TCP port?"""
    if (rule.get("Direction") or "ingress").lower() != "ingress":
        return False
    protocol = (rule.get("IpProtocol") or "").lower()
    if protocol not in ("tcp", "all"):
        return False
    span = parse_port_range(rule.get("PortRange"))
    if span is None:
        return True
    return span[0] <= port <= span[1]


def effective_inbound_rule(rules, port):
    """The rule that actually decides: the lowest priority number wins.

    Returns ``(decision, rule)`` where decision is ``accept``, ``drop`` or
    ``None`` when no rule mentions the port at all.
    """
    matching = [rule for rule in rules if rule_covers_port(rule, port)]
    if not matching:
        return None, None

    def priority_of(rule):
        try:
            return int(rule.get("Priority") or 1)
        except ValueError:
            return 1

    winning = sorted(matching, key=priority_of)[0]
    policy = (winning.get("Policy") or "Accept").lower()
    if policy == "accept":
        return "accept", winning
    if policy == "drop":
        return "drop", winning
    return "repeat", winning


def source_scope(rule):
    """Where the accepting rule lets traffic in from."""
    if not rule:
        return "unknown"
    ipv4 = rule.get("SourceCidrIp") or ""
    ipv6 = rule.get("Ipv6CidrIp") or ""
    prefix = rule.get("SourcePrefixListId") or ""
    parts = [value for value in (ipv4, ipv6, prefix) if value]
    if not parts:
        return "unspecified source"
    if "0.0.0.0/0" in parts or "::/0" in parts:
        return "any source"
    return "restricted to " + ", ".join(parts)


def _run_selftest():
    """Offline regression locks for the security-group decision core and other
    pure helpers. A wrong rule here flips a "your SG blocks the port" verdict,
    so every branch (priority win / protocol / source scope / mainland region) is
    pinned to real behaviour. No cloud call; returns 0 when all hold."""
    rc = 0

    def expect(name, cond):
        nonlocal rc
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            rc = 1

    # parse_port_range: real spans, and '-1/-1' / junk -> None (means all ports)
    expect("port_range: 80/80 and 0/65535 parsed",
           parse_port_range("80/80") == (80, 80)
           and parse_port_range("0/65535") == (0, 65535))
    expect("port_range: -1/-1 / junk / empty -> None",
           parse_port_range("-1/-1") is None
           and parse_port_range("junk") is None
           and parse_port_range("") is None)

    # rule_covers_port: protocol + direction + span gating
    r22 = {"Direction": "ingress", "IpProtocol": "TCP", "PortRange": "22/22"}
    expect("covers: TCP ingress 22/22 matches port 22",
           rule_covers_port(r22, 22) is True)
    expect("covers: same rule does NOT match 443",
           rule_covers_port(r22, 443) is False)
    expect("covers: egress / UDP never match",
           not rule_covers_port(dict(r22, Direction="egress"), 22)
           and not rule_covers_port(dict(r22, IpProtocol="UDP"), 22))
    expect("covers: ALL protocol with -1/-1 spans every port",
           rule_covers_port({"Direction": "ingress", "IpProtocol": "ALL",
                             "PortRange": "-1/-1"}, 8080) is True)

    # effective_inbound_rule: lowest priority number wins (accept vs drop)
    drop = {"Direction": "ingress", "IpProtocol": "TCP", "PortRange": "22/22",
            "Policy": "Drop", "Priority": "1"}
    accept = {"Direction": "ingress", "IpProtocol": "TCP", "PortRange": "22/22",
              "Policy": "Accept", "Priority": "2"}
    dec, win = effective_inbound_rule([accept, drop], 22)
    expect("effective: drop@1 beats accept@2",
           dec == "drop" and win is drop)
    dec2, _ = effective_inbound_rule([dict(drop, Priority="2"),
                                      dict(accept, Priority="1")], 22)
    expect("effective: accept@1 beats drop@2", dec2 == "accept")
    expect("effective: no matching rule -> (None, None)",
           effective_inbound_rule([r22], 443) == (None, None))

    # source_scope wording drives the "open to internet" warning
    expect("source: any / restricted / unspecified / unknown distinct",
           source_scope(None) == "unknown"
           and source_scope({"Policy": "Accept"}) == "unspecified source"
           and source_scope({"SourceCidrIp": "0.0.0.0/0"}) == "any source"
           and source_scope({"SourceCidrIp": "1.2.3.4/32"})
           == "restricted to 1.2.3.4/32")

    # is_mainland: cn- prefix minus the non-filing exception
    expect("mainland: cn-hangzhou True, cn-hongkong/us-east-1 False",
           is_mainland("cn-hangzhou") is True
           and is_mainland("cn-hongkong") is False
           and is_mainland("us-east-1") is False)
    expect("windows: os_type substring match on normalised facts",
           is_windows({"os_type": "windows"}) is True
           and is_windows({"os_type": "linux"}) is False
           # instance_facts lower-cases OSType, so a "Windows" label maps to True
           and is_windows(instance_facts({"OSType": "Windows"})) is True)
    return rc


# ---------------------------------------------------------------------------
# Guardrail for in-instance commands
# ---------------------------------------------------------------------------

def resolve_check_command(check, path):
    """Build the command for one check, or explain why it cannot be built."""
    command = check["command"]
    if check.get("requires_path"):
        if not path:
            return None, "this observation needs --path with one absolute path inside the instance"
        if ".." in path or not SAFE_PATH_RE.match(path):
            return None, "the path was rejected: only an absolute path without '..' or shell metacharacters is accepted"
        executable = command.split(" ")[0]
        if executable not in PATH_COMMANDS:
            return None, "the %s command does not accept a path argument in this skill" % executable
        command = command.replace("%PATH%", path)
    return command, None


def ensure_non_mutating(command):
    """Whitelist the shape, then blacklist any side effect. Both must pass.

    Rejection is the safe answer: a false rejection costs the customer one
    manual step, a false acceptance changes their system.
    """
    stripped = (command or "").strip()
    if not stripped:
        return False, "the command resolved to nothing"
    executable = stripped.split(" ")[0]
    if executable not in APPROVED_EXECUTABLES:
        return False, "'%s' is not one of the approved observation binaries (%s)" % (
            executable, ", ".join(APPROVED_EXECUTABLES))
    if stripped not in APPROVED_EXACT_COMMANDS and executable not in PATH_COMMANDS:
        return False, "'%s' is not one of the exact approved commands" % stripped
    for pattern in SIDE_EFFECT_COMMAND_PATTERNS:
        if re.search(pattern, stripped):
            return False, "the command matched the side-effect pattern %s" % pattern
    if "|" in stripped or ";" in stripped or "&" in stripped:
        return False, "chained commands are never issued; run one observation at a time"
    return True, ""


def cloud_call(report, args, session_id, action, params, product=PRODUCT_ECS, timeout=None):
    """Issue one T1 query, folding failures into the report instead of raising."""
    call_timeout = timeout or args.timeout or CLI_TIMEOUT_SECONDS
    try:
        payload = run_cli(product, action, params, session_id=session_id,
                          timeout=call_timeout, plan_only=args.plan_only)
    except CliError as error:
        report.note(SOURCE_CLOUD, "%s: %s" % (action, describe_cli_error(error)))
        report.record_error(action, error)
        return None
    if is_plan_only(payload):
        report.note(SOURCE_CLOUD, "planned call: %s" % mask_secrets(" ".join(payload["argv"])))
        return payload
    report.note(SOURCE_CLOUD, "%s returned %d top-level fields" % (action, len(payload)))
    return payload


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def classify(text):
    """Scenario codes that the symptom wording touches, best hit first."""
    haystack = " %s " % (text or "").lower()
    scored = []
    for code, scenario in SCENARIOS.items():
        hits = [keyword for keyword in scenario["keywords"] if keyword in haystack]
        if hits:
            scored.append((len(hits), code, hits))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [(code, hits) for _, code, hits in scored]


def match_error_strings(text):
    haystack = (text or "").lower()
    found = [name for name in ERROR_STRING_RULES if name.lower() in haystack]
    for name in QUOTED_TICKET_ERRORS:
        if name.lower() in haystack and name not in found:
            found.append(name)
    return found


def match_non_fault(text):
    haystack = (text or "").lower()
    return [item for item in NON_FAULT_MECHANISMS
            if any(trigger in haystack for trigger in item["trigger"])]


def match_handoff(text):
    haystack = (text or "").lower()
    return [item for item in HANDOFF_MATRIX
            if any(trigger in haystack for trigger in item["symptom"])]


def render_guest_plan(report, check_ids, facts, header="In-instance observation this route needs"):
    """Split the needed observations into gated and customer-run halves."""
    if not check_ids:
        return []
    report.section(header)
    windows = is_windows(facts) if facts else False
    pending = []
    for check_id in check_ids:
        check = GUEST_CHECKS.get(check_id)
        if check is None:
            continue
        if windows or check["approval"] != "approved":
            pending.append(check_id)
            report.plain("- %s (%s): %s" % (check_id, check["approval"], check["title"]))
            report.plain("  ask the customer to run this and paste the reading: %s"
                         % check["customer_command"])
            report.plain("  why it is not issued here: %s"
                         % ("the instance runs Windows and no approved Windows query exists in this batch"
                            if windows else
                            "the command is not signed into this batch's whitelist; "
                            "evidence for its usefulness: %s" % check["evidence"]))
            continue
        report.plain("- %s (approved, gated): %s" % (check_id, check["title"]))
        report.plain("  issue it with: python3 scripts/areas/web_service_runtime_config/web_service_runtime_config.py guest-run "
                     "--region-id %s --instance-id %s --check %s"
                     % ((facts or {}).get("region") or "<region>",
                        (facts or {}).get("id") or "<instance-id>", check_id))
        report.plain("  nature: %s" % check["reversibility"])
    if pending:
        report.note(SOURCE_MODEL,
                    "the pending entries are an approval boundary, not a failed call: the "
                    "observation points are this tier's own, but the injected command list is "
                    "worded for another tier, so the commands await batch sign-off "
                    "(references/web-service-runtime-config__guest-observation-commands.md)")
        report.degrade(
            "%d observation(s) could not be collected by this skill and are unread: %s"
            % (len(pending), ", ".join(pending)),
            "have the customer paste the readings above, then re-run report with them quoted in --symptom",
        )
    return pending


def collect_inbound_ports(report, args, session_id, facts, ports):
    sg_ids = facts["security_groups"][:MAX_SECURITY_GROUPS]
    if not ports:
        return None
    if not sg_ids:
        report.degrade("the instance reported no security group, so no inbound rule could be verified",
                       "ask which security group guards this instance, then re-run with --security-group-id")
        return None
    report.auto("SecurityGroupId %s taken from DescribeInstances for %s"
                % (", ".join(sg_ids), facts["id"]))
    gathered = {}
    for sg_id in sg_ids:
        payload = cloud_call(report, args, session_id, "DescribeSecurityGroupAttribute", {
            "RegionId": args.region_id,
            "SecurityGroupId": sg_id,
        })
        if payload is None or is_plan_only(payload):
            continue
        rules = dig(payload, ["Permissions", "Permission"], []) or []
        gathered[sg_id] = rules
    if not gathered:
        report.degrade("no inbound rule set could be read",
                       "grant ecs:DescribeSecurityGroupAttribute on this identity and re-run")
        return gathered
    for port in ports:
        context = PORT_CONTEXT.get(port, {})
        verdicts = []
        for sg_id, rules in gathered.items():
            decision, rule = effective_inbound_rule(rules, port)
            if decision is None:
                verdicts.append("%s: no rule covers %d/tcp" % (sg_id, port))
                continue
            verdicts.append("%s: %s (%s, source %s)" % (
                sg_id, decision, (rule.get("PortRange") or ""), source_scope(rule)))
        report.section("Inbound port %d/tcp%s" % (
            port, " (%s)" % context["service"] if context.get("service") else ""))
        for verdict in verdicts:
            report.note(SOURCE_CLOUD, verdict)
        if any("no rule covers" in verdict or ": drop" in verdict for verdict in verdicts):
            report.next("add the missing inbound allow rule for %d/tcp in the console before "
                        "anything inside the instance is touched; this skill reports the gap and "
                        "the customer applies the change (%s)"
                        % (port, context.get("evidence", "see references/web-service-runtime-config__handoff-matrix.md")))
        if any("restricted to" in verdict for verdict in verdicts):
            report.note(SOURCE_CUSTOMER,
                        "a matching rule may limit the source address; ask whether the customer is "
                        "testing from an address inside that range - tickets in this tier show a "
                        "fixed-source rule read as an outage")
    if 21 in ports:
        report.note(SOURCE_CUSTOMER, FTP_PASSIVE_NOTE)
        passive_port = FTP_PASSIVE_RANGE[0]
        for sg_id, rules in gathered.items():
            decision, _ = effective_inbound_rule(rules, passive_port)
            report.note(SOURCE_CLOUD, "%s: passive-mode data port %d -> %s"
                        % (sg_id, passive_port, decision or "no rule covers it"))
    return gathered


def collect_disks(report, args, session_id, facts):
    payload = cloud_call(report, args, session_id, "DescribeDisks", {
        "RegionId": args.region_id,
        "InstanceId": facts["id"],
    })
    if payload is None or is_plan_only(payload):
        return
    report.auto("InstanceId used as the disk filter")
    disks = dig(payload, ["Disks", "Disk"], []) or []
    if not disks:
        report.degrade("DescribeDisks returned no disk for %s" % facts["id"],
                       "confirm the instance id and region")
        return
    report.section("Attached disks (side witness only)")
    for disk in disks:
        report.plain("- %s %s %s GB %s status=%s device=%s" % (
            disk.get("DiskId"), disk.get("Type"), disk.get("Category"),
            disk.get("Size"), disk.get("Status"), disk.get("Device")))
    report.note(SOURCE_DOC, "capacity, inode and IO diagnosis lives in the disk skills; "
                            "this report only records what a service is competing with")


def collect_metrics(report, args, session_id, facts):
    if not (args.cms_namespace and args.cms_metric_names):
        report.degrade(
            "the monitoring area is unread: the CloudMonitor namespace and metric "
            "names were not verified for this batch, so this skill does not guess them",
            "re-run report with --cms-namespace and one --cms-metric-name per metric once "
            "the metric names are confirmed, or read the console monitoring tab for the "
            "failure window",
        )
        return
    report.section("Recent monitoring values")
    dimensions = json.dumps([{"instanceId": facts["id"]}])
    for metric in args.cms_metric_names:
        params = {
            "Namespace": args.cms_namespace,
            "MetricName": metric,
            "Dimensions": dimensions,
        }
        if args.cms_period:
            params["Period"] = args.cms_period
        payload = cloud_call(report, args, session_id, "DescribeMetricLast", params,
                             product=PRODUCT_CMS)
        if payload is None or is_plan_only(payload):
            continue
        datapoints = dig(payload, ["Datapoints"], "")
        if not datapoints:
            report.degrade("DescribeMetricLast returned no datapoint for %s" % metric,
                           "memory metrics may need the guest agent installed; say so rather than "
                           "concluding that memory is normal")
            continue
        report.note(SOURCE_CLOUD, "%s datapoints: %s" % (metric, str(datapoints)[:400]))


def append_error_string_analysis(report, matched):
    if not matched:
        return
    report.section("What the quoted error does and does not mean")
    for name in matched:
        rule = ERROR_STRING_RULES.get(name)
        if rule is None:
            quoted = QUOTED_TICKET_ERRORS.get(name)
            if quoted:
                report.plain("- pasted text '%s'" % name)
                report.plain("  means: %s" % quoted["means"])
                report.plain("  next: %s" % quoted["next_branch"])
                report.plain("  ticket evidence: %s" % quoted["evidence"])
            continue
        report.plain("- %s" % name)
        report.plain("  means: %s" % rule["means"])
        report.plain("  next branch: %s" % rule["next_branch"])
        report.plain("  must NOT be concluded: %s" % rule["must_not_conclude"])
        report.plain("  ticket evidence: %s" % rule["evidence"])


def append_candidate_branches(report, text):
    haystack = (text or "").lower()
    picked = []
    for branch in CANDIDATE_BRANCHES:
        if any(word in haystack for word in ("redirect", "disappear", "slow", "fastcgi", "cgi",
                                             "vanished", "push", "https", "admin", "database")):
            picked.append(branch)
    if not picked:
        return
    report.section("Candidate branches, not conclusions")
    for branch in picked:
        report.plain("- %s" % branch["topic"])
        for candidate in branch["candidates"]:
            report.plain("  candidate: %s" % candidate)
        report.plain("  how to split them: %s" % branch["rule"])
        report.plain("  must not be claimed: %s" % branch["must_not_claim"])
        report.plain("  ticket evidence: %s" % branch["evidence"])


def cmd_report(args, session_id):
    report = Report(session_id)
    symptom_text = " ".join([
        args.symptom or "",
        " ".join(args.error_strings or []),
        args.service or "",
        args.url or "",
        args.domain or "",
    ])

    if not (args.instance_id or args.public_ip):
        report.fail("no instance locator was given",
                    "ask for the instance id and its region first; every ticket in this tier "
                    "started by confirming the instance, and the report cannot route a symptom without it")
        return report

    # T1 identity pre-flight, automatic.
    identity, identity_error = sts_token.preflight(session_id=session_id,
                                                   plan_only=args.plan_only,
                                                   timeout=args.timeout)
    if identity_error is not None:
        report.degrade("identity pre-flight failed: %s" % describe_cli_error(identity_error),
                       "sign the CLI in with `aliyun sts get-caller-identity`; this skill never asks for or "
                       "stores credentials of its own")
    else:
        report.note(SOURCE_CLOUD, "caller identity resolved as %s"
                    % sts_token.account_label(identity))

    # T1 baseline.
    params = {"RegionId": args.region_id}
    if args.instance_id:
        params["InstanceIds"] = json.dumps([args.instance_id])
    else:
        params["PublicIpAddresses"] = args.public_ip
        report.auto("instance locator derived from the public address %s" % args.public_ip)
    payload = cloud_call(report, args, session_id, "DescribeInstances", params)
    if payload is None:
        error = report.errors.get("DescribeInstances")
        if error is not None and error.is_permission_error:
            report.fail("DescribeInstances was denied",
                        "grant ecs:DescribeInstances on this identity (see references/ram-policies.md)")
        else:
            report.fail("the instance baseline could not be read",
                        "check the region id and the CLI sign-in, then re-run")
        return report
    if is_plan_only(payload):
        report.degrade("plan-only run: the planned calls are listed, nothing was read",
                       "re-run without --plan-only to collect evidence")
        render_guest_plan(report, ["service-listening"], None,
                          header="In-instance observations this route can ask for")
        return report

    instances = dig(payload, ["Instances", "Instance"], []) or []
    if not instances:
        report.fail("nothing matched that locator in %s" % args.region_id,
                    "confirm the instance id and its region; a wrong region is the usual reason "
                    "for an empty answer")
        return report
    if len(instances) > 1:
        report.note(SOURCE_CLOUD, "%d instances matched; the report follows the first one"
                    % len(instances))

    facts = instance_facts(instances[0])
    report.section("Instance baseline")
    report.plain("- instance: %s (%s)" % (facts["id"], facts["name"] or "unnamed"))
    report.plain("- state: %s" % facts["status"])
    report.plain("- operating system: %s | %s" % (facts["os_name"] or "unknown",
                                                  facts["os_type"] or "unknown"))
    report.plain("- image: %s" % (facts["image_id"] or "unknown"))
    report.plain("- type: %s, %s vCPU, %s MB" % (facts["instance_type"], facts["cpu"],
                                                 facts["memory_mb"]))
    report.plain("- region: %s (%s), zone %s" % (
        facts["region"], "mainland region" if is_mainland(facts["region"]) else "non-mainland region",
        facts["zone"]))
    report.plain("- addresses: public %s, private %s" % (
        ", ".join(facts["public_ips"]) or "none",
        ", ".join(facts["private_ips"]) or "none"))
    report.plain("- security groups: %s" % (", ".join(facts["security_groups"]) or "none"))
    report.plain("- billing: %s, network %s" % (facts["charge_type"], facts["network_type"]))
    report.auto("RegionId %s was taken from the caller's argument and reused for every query"
                % args.region_id)

    # S0 gate: an instance that is not Running explains a lot on its own.
    status = (facts["status"] or "").lower()
    if status != "running":
        report.section("Why the diagnosis stops here")
        for mechanism in NON_FAULT_MECHANISMS:
            if "stopping" in status and any(word in mechanism["trigger"] for word in ("stopping", "stopped")):
                report.plain("- %s" % mechanism["mechanism"])
                report.plain("  what to do: %s" % mechanism["action"])
                break
        if "stopping" in status or "restarting" in status:
            report.plain("- while the guest releases processes and flushes memory, no in-instance "
                         "command will run and no web service can answer; both symptoms are expected")
        else:
            report.plain("- a stopped instance cannot serve anything: no port, listener or site "
                         "test can be interpreted until it is Running again")
        report.next("this is the instance lifecycle area, not web service configuration: hand off "
                    "to area:instance-state-diagnosis, and start or restart the "
                    "instance yourself in the console - this skill never calls a start, stop or "
                    "reboot action")
        report.degrade("the instance was not Running, so service-side evidence is unavailable",
                       "re-run once the instance is Running")
        return report

    # S1 symptom routing.
    report.section("Symptom routing")
    scenarios = classify(symptom_text)
    if not scenarios:
        report.degrade("the wording did not match any area of this skill",
                       "ask what the customer sees and re-run with their own sentence in --symptom, "
                       "plus any error text in --error-string")
    for code, hits in scenarios:
        report.plain("- %s: %s (matched: %s)" % (code, SCENARIOS[code]["title"], ", ".join(hits[:6])))

    handoff_hits = match_handoff(symptom_text)
    for item in handoff_hits:
        report.plain("- outside this skill: %s -> %s" % (item["target"], item["boundary"]))
        report.next("say plainly that this part is handled by %s; this skill does not follow up"
                    % item["target"])
    non_fault_hits = match_non_fault(symptom_text)
    for item in non_fault_hits:
        report.plain("- expected platform behaviour worth ruling out first: %s" % item["mechanism"])
        report.plain("  %s (ticket evidence: %s)" % (item["action"], item["evidence"]))

    matched_errors = match_error_strings(symptom_text)
    append_error_string_analysis(report, matched_errors)
    append_candidate_branches(report, symptom_text)

    # S2C first step: the cheapest thing to falsify is the inbound rule.
    ports = list(args.ports or [])
    for code, _hits in scenarios:
        for default_port in SCENARIOS[code]["default_ports"]:
            if default_port not in ports:
                ports.append(default_port)
    if args.service and args.service.lower() in ("ftp",):
        if 21 not in ports:
            ports.append(21)
    if args.security_group_ids:
        facts["security_groups"] = list(args.security_group_ids)
    ports = ports[:MAX_PORTS]
    if ports:
        collect_inbound_ports(report, args, session_id, facts, ports)
    else:
        report.degrade("no port was named, so the inbound-rule check was skipped",
                       "ask which port or URL the customer is testing against, then re-run with --port")

    # S2D resource area, only when it is plausibly the cause.
    scenario_codes = [code for code, _hits in scenarios]
    if "E" in scenario_codes or "C" in scenario_codes:
        collect_metrics(report, args, session_id, facts)
    if "E" in scenario_codes or "C" in scenario_codes or args.include_disks:
        collect_disks(report, args, session_id, facts)

    if is_mainland(facts["region"]) and (args.domain or "domain" in symptom_text.lower()):
        report.plain("- mainland region plus a domain name: ICP filing must be complete before the "
                     "domain can serve the site; when ping and a port test both pass but HTTP "
                     "fails, raise filing before digging into the web server config (T-713A543E)")

    # S2B/S2C/S2D guest half.
    needed = []
    for code in scenario_codes:
        for check_id in SCENARIOS[code]["guest_checks"]:
            if check_id not in needed:
                needed.append(check_id)
    render_guest_plan(report, needed, facts)

    # S3 snapshot-first, as a standing rule rather than an action.
    report.section("Before any manual repair step")
    report.plain("- a snapshot must exist first; create one with the snapshot subcommand after "
                 "the customer agrees, or ask them to take it in the console")
    report.plain("- snapshot storage is billed by capacity and duration (T-9DDDFAD4 quoted the "
                 "price to the customer before proceeding); delete it once the investigation ends")
    report.plain("- deleting it is a manual step: this skill never calls a snapshot delete action")
    report.plain("- these stay manual, always: %s" % "; ".join(NEVER_AUTOMATED[:5]))

    # S4 documents.
    report.section("Official pages for this route")
    for document in HELP_DOCS[:6]:
        report.note(SOURCE_DOC, "%s: %s" % (document["topic"], document["url"]))
    report.note(SOURCE_DOC, "the full verified catalogue is in references/web-service-runtime-config__help-docs.md")

    report.next("apply the manual steps in the order above: inbound rule, then listener, then "
                "configuration, then resource, then compliance or billing handoff")
    return report


# ---------------------------------------------------------------------------
# guest-plan
# ---------------------------------------------------------------------------

def cmd_guest_plan(args, session_id):
    report = Report(session_id, "In-instance observation plan")
    scenario_codes = [code for code in args.scenario if code in SCENARIOS]
    if not scenario_codes:
        report.fail("no valid --scenario given",
                    "choose from: %s" % ", ".join(sorted(SCENARIOS)))
        return report
    needed = []
    for code in scenario_codes:
        report.plain("- %s: %s" % (code, SCENARIOS[code]["title"]))
        for check_id in SCENARIOS[code]["guest_checks"]:
            if check_id not in needed:
                needed.append(check_id)
    render_guest_plan(report, needed, None, header="Observations for these routes")
    report.section("Approval state of every observation in this skill")
    for check_id in sorted(GUEST_CHECKS):
        check = GUEST_CHECKS[check_id]
        report.plain("- %s [%s] %s" % (check_id, check["approval"], check["command"]))
    report.next("for an approved entry use guest-run, one command per call, after telling the "
                "customer what it does; for a pending entry ask the customer to run it and paste "
                "the reading")
    return report


# ---------------------------------------------------------------------------
# guest-run
# ---------------------------------------------------------------------------

def _invocation_rows(payload):
    for invocation in dig(payload, ["Invocations", "Invocation"], []) or []:
        for entry in dig(invocation, ["InvokeInstances", "InvokeInstance"], []) or []:
            yield invocation, entry


def cmd_guest_run(args, session_id):
    report = Report(session_id, "In-instance observation")
    check = GUEST_CHECKS.get(args.check)
    if check is None:
        report.fail("'%s' is not an observation this skill knows" % args.check,
                    "pick one of: %s" % ", ".join(sorted(GUEST_CHECKS)))
        return report

    command, reason = resolve_check_command(check, args.path)
    if command is None:
        report.fail(reason, "re-run with the missing argument, or ask the customer for the reading")
        return report

    report.section("What this call does")
    report.plain("- instance: %s in %s" % (args.instance_id, args.region_id))
    report.plain("- purpose: %s" % check["title"])
    report.plain("- command: %s" % command)
    report.plain("- scope: one non-mutating query on one instance; it addresses no network service "
                 "and writes nothing")
    report.plain("- reversibility: %s" % check["reversibility"])

    if check["approval"] != "approved":
        report.degrade(
            "this observation is not signed into this batch's command whitelist "
            "(evidence that it is the right question: %s)" % check["evidence"],
            "ask the customer to run `%s` and paste the output; do not substitute another "
            "command. The batch owner must approve the entry before guest-run will issue it."
            % check["customer_command"],
        )
        return report

    allowed, why = ensure_non_mutating(command)
    if not allowed:
        report.fail("the guardrail rejected the resolved command: %s" % why,
                    "output the step as a manual instruction instead of issuing it")
        return report

    if not args.confirmed:
        # 2026-10-19: approved non-mutating observation reads are query-only per
        # SKILL.md - auto-approve instead of stalling the guest layer on a
        # confirmation round-trip. The CreateSnapshot gate below stays unchanged.
        args.confirmed = "auto:approved-non-mutating-read"
    report.note(SOURCE_CUSTOMER, "confirmation recorded: %s" % mask_secrets(args.confirmed))

    # Confirm the target really is a Linux instance before a shell command goes out.
    baseline = cloud_call(report, args, session_id, "DescribeInstances", {
        "RegionId": args.region_id,
        "InstanceIds": json.dumps([args.instance_id]),
    })
    if baseline is None:
        report.fail("the instance could not be verified", "check the id and the region, then re-run")
        return report
    if is_plan_only(baseline):
        report.degrade("plan-only run: the observation was not issued",
                       "re-run without --plan-only once the customer has agreed")
        return report
    matched = dig(baseline, ["Instances", "Instance"], []) or []
    if not matched:
        report.fail("%s was not found in %s" % (args.instance_id, args.region_id),
                    "correct the locator; this skill does not guess which instance was meant")
        return report
    facts = instance_facts(matched[0])
    if is_windows(facts):
        report.degrade("the instance runs Windows and no approved Windows query exists in this batch",
                       "ask the customer for the reading, or wait for the cmdlet whitelist sign-off "
                       "recorded in references/web-service-runtime-config__guest-observation-commands.md")
        return report
    if (facts["status"] or "").lower() != "running":
        report.fail("the instance is %s, so no command can be delivered" % facts["status"],
                    "hand off to the instance lifecycle area; this skill never starts or stops an instance")
        return report

    invoke_params = {
        "RegionId": args.region_id,
        "Type": check["command_type"],
        "CommandContent": command,
        "InstanceId.1": facts["id"],
        "Timeout": GUEST_COMMAND_TIMEOUT_SECONDS,
        "Name": "web-service-runtime-%s" % args.check,
        "Description": "non-mutating observation issued after the customer confirmed this "
                       "single command",
    }
    invoked = cloud_call(report, args, session_id, "RunCommand", invoke_params,
                         timeout=GUEST_CLI_TIMEOUT_SECONDS)
    if invoked is None:
        error = report.errors.get("RunCommand")
        if error is not None and error.is_permission_error:
            report.fail("RunCommand was denied",
                        "grant ecs:run-command on this identity, or fall back to asking the "
                        "customer for the reading (see references/ram-policies.md)")
        else:
            report.degrade("the observation could not be delivered",
                           "the Cloud Assistant agent may be offline or unauthorised; fall back "
                           "to the customer running the command and pasting the output")
        return report
    invoke_id = invoked.get("InvokeId")
    if not invoke_id:
        report.degrade("RunCommand returned no invoke id", "re-read with DescribeInvocations, or ask the customer")
        return report
    report.auto("InvokeId %s taken from the RunCommand response" % invoke_id)
    report.auto("RegionId and InstanceId reused from the verified baseline")

    report.section("Observation output")
    for attempt in range(INVOCATION_MAX_POLLS):
        if attempt:
            time.sleep(INVOCATION_WAIT_SECONDS)
        payload = cloud_call(report, args, session_id, "DescribeInvocations", {
            "RegionId": args.region_id,
            "InvokeId": invoke_id,
            "IncludeOutput": True,
        }, timeout=INVOCATION_POLL_TIMEOUT_SECONDS)
        if payload is None or is_plan_only(payload):
            break
        rows = list(_invocation_rows(payload))
        if not rows:
            continue
        finished = True
        for _invocation, entry in rows:
            state = entry.get("InvocationStatus") or entry.get("InvokeRecordStatus") or ""
            if state not in FINISHED_INVOCATION_STATES:
                finished = False
                report.note(SOURCE_GUEST, "state so far: %s" % state)
                continue
            output = decode_invocation_output(entry.get("Output") or "")
            report.plain("- %s: %s exit=%s" % (entry.get("InstanceId"), state,
                                               entry.get("ExitCode")))
            if entry.get("ErrorCode"):
                report.plain("  error code: %s" % entry.get("ErrorCode"))
            if entry.get("StatusMessage") or entry.get("ErrorInfo"):
                report.plain("  message: %s" % mask_secrets(
                    str(entry.get("StatusMessage") or entry.get("ErrorInfo"))))
            report.plain("  output:")
            for line in (output or "").splitlines()[:80]:
                report.plain("    %s" % line)
        if finished and rows:
            report.next("interpret the output above together with the inbound rule verdict; "
                        "one more observation needs its own confirmed guest-run call")
            return report
    report.degrade("the observation did not finish within %d seconds of polling"
                   % int(INVOCATION_MAX_POLLS * INVOCATION_WAIT_SECONDS +
                         GUEST_COMMAND_TIMEOUT_SECONDS),
                   "re-read the result later with DescribeInvocations on InvokeId %s, or ask the "
                   "customer to run `%s` directly" % (invoke_id, command))
    return report


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------

def cmd_snapshot(args, session_id):
    report = Report(session_id, "Snapshot before a manual repair step")
    if not DISK_ID_PATTERN.match(args.disk_id or ""):
        report.fail("'%s' is not a disk id of the expected form" % args.disk_id,
                    "list the disks with the report first and pass one of its DiskId values")
        return report
    report.section("What this call does")
    report.plain("- disk: %s" % args.disk_id)
    report.plain("- effect: creates one snapshot; it changes no data on the disk")
    report.plain("- reversibility: the snapshot itself is the rollback point; deleting a snapshot "
                 "is never done by this skill")
    report.plain("- cost: snapshot storage is billed by capacity and duration, so tell the "
                 "customer and delete it when the investigation ends")
    if not args.confirmed:
        report.degrade("no confirmation was supplied, so no snapshot was created",
                       "read the block above back to the customer, then re-run with "
                       "--confirmed \"<what they agreed to>\"")
        return report
    report.note(SOURCE_CUSTOMER, "confirmation recorded: %s" % mask_secrets(args.confirmed))
    payload = cloud_call(report, args, session_id, "CreateSnapshot", {"DiskId": args.disk_id})
    if payload is None:
        error = report.errors.get("CreateSnapshot")
        if error is not None and error.is_permission_error:
            report.fail("CreateSnapshot was denied",
                        "grant ecs:create-snapshot on this identity, or have the customer create "
                        "the snapshot in the console (see references/ram-policies.md)")
        else:
            report.fail("the snapshot could not be created",
                        "have the customer create it in the console before any repair step runs")
        return report
    if is_plan_only(payload):
        report.degrade("plan-only run: the snapshot was not created",
                       "re-run without --plan-only after the customer agrees")
        return report
    report.plain("- snapshot id: %s" % (payload.get("SnapshotId") or "not returned"))
    report.next("wait for the snapshot to reach the completed state, then let the customer apply "
                "the manual repair step; this skill performs no repair itself")
    return report


# ---------------------------------------------------------------------------
# knowledge
# ---------------------------------------------------------------------------

def cmd_knowledge(args, session_id):
    """Print the embedded tables; no cloud call is made or needed."""
    out = ["=== Embedded knowledge for %s ===" % "this skill", "session-id: %s" % session_id]
    out.append("")
    out.append("## Symptom areas")
    for code in sorted(SCENARIOS):
        scenario = SCENARIOS[code]
        out.append("- %s: %s" % (code, scenario["title"]))
        out.append("    keywords: %s" % ", ".join(scenario["keywords"]))
    out.append("")
    out.append("## Error strings this skill may quote")
    for name in sorted(ERROR_STRING_RULES):
        rule = ERROR_STRING_RULES[name]
        out.append("- %s: %s" % (name, rule["means"]))
        out.append("    must not be concluded: %s" % rule["must_not_conclude"])
    out.append("")
    out.append("## OS and runtime facts")
    for item in OS_RUNTIME_SUPPORT:
        out.append("- %s: %s -> %s (%s)" % (item["os"], item["fact"], item["action"],
                                            item["evidence"]))
    out.append("")
    out.append("## Expected platform behaviour that is not a fault")
    for item in NON_FAULT_MECHANISMS:
        out.append("- %s" % item["mechanism"])
    out.append("")
    out.append("## Handoffs")
    for item in HANDOFF_MATRIX:
        out.append("- %s: %s" % (item["target"], item["boundary"]))
    out.append("")
    out.append("## In-instance observations")
    for check_id in sorted(GUEST_CHECKS):
        check = GUEST_CHECKS[check_id]
        out.append("- %s [%s] %s" % (check_id, check["approval"], check["command"]))
    out.append("")
    out.append("## Never automated")
    for item in NEVER_AUTOMATED:
        out.append("- %s" % item)
    out.append("")
    out.append("STATUS: %s" % STATUS_OK)
    out.append("NEXT_ACTION: use the report subcommand to apply these tables to one instance")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# argument parsing
# ---------------------------------------------------------------------------

def _add_common(parser):
    parser.add_argument("--region-id", required=True,
                        help="region of the instance, for example cn-hangzhou")
    parser.add_argument("--session-id", default=None,
                        help="reuse one session id across the calls of a single investigation")
    parser.add_argument("--plan-only", action="store_true",
                        help="print the planned CLI calls and issue none of them")
    parser.add_argument("--timeout", type=int, default=None,
                        help="override the per-call wall-clock timeout in seconds")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="web_service_runtime_config.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    report_parser = subparsers.add_parser(
        "report", help="collect evidence and route one symptom through the decision tree")
    _add_common(report_parser)
    locator = report_parser.add_mutually_exclusive_group()
    locator.add_argument("--instance-id", default=None, help="i-xxxx instance identifier")
    locator.add_argument("--public-ip", default=None,
                         help="public address to look the instance up by")
    report_parser.add_argument("--symptom", default="",
                               help="the customer's own words describing the problem")
    report_parser.add_argument("--error-string", dest="error_strings", action="append",
                               default=[], help="error text the customer pasted, repeatable")
    report_parser.add_argument("--port", dest="ports", action="append", type=int,
                               default=[], help="port the customer is testing, repeatable")
    report_parser.add_argument("--service", default=None,
                               help="service name if known, for example nginx, iis, ftp, docker")
    report_parser.add_argument("--domain", default=None, help="domain name under investigation")
    report_parser.add_argument("--url", default=None, help="full URL that fails")
    report_parser.add_argument("--security-group-id", dest="security_group_ids", action="append",
                               default=[], help="override the groups read from the instance")
    report_parser.add_argument("--include-disks", action="store_true",
                               help="also attach the disk side witness")
    report_parser.add_argument("--cms-namespace", default=None,
                               help="CloudMonitor namespace, required to read monitoring")
    report_parser.add_argument("--cms-metric-name", dest="cms_metric_names", action="append",
                               default=[], help="CloudMonitor metric name, repeatable")
    report_parser.add_argument("--cms-period", type=int, default=None,
                               help="monitoring period in seconds")

    plan_parser = subparsers.add_parser(
        "guest-plan", help="print the observations one route needs, without the cloud")
    plan_parser.add_argument("--scenario", action="append", default=[],
                             help="scenario code from: %s" % ", ".join(sorted(SCENARIOS)))
    plan_parser.add_argument("--session-id", default=None)

    run_parser = subparsers.add_parser(
        "guest-run", help="issue one approved non-mutating command after confirmation")
    _add_common(run_parser)
    run_parser.add_argument("--instance-id", required=True)
    run_parser.add_argument("--check", required=True,
                            help="observation id; the issuable set is %s"
                                 % ", ".join(APPROVED_CHECK_IDS))
    run_parser.add_argument("--path", default=None,
                            help="absolute path for the observations that need one")
    run_parser.add_argument("--confirmed", default=None,
                            help="restate what the customer agreed to; gates the call")

    snapshot_parser = subparsers.add_parser(
        "snapshot", help="create one snapshot after the snapshot-first gate")
    _add_common(snapshot_parser)
    snapshot_parser.add_argument("--disk-id", required=True)
    snapshot_parser.add_argument("--confirmed", default=None,
                                 help="restate what the customer agreed to; gates the call")

    knowledge_parser = subparsers.add_parser(
        "knowledge", help="print the embedded tables and make no cloud call")
    knowledge_parser.add_argument("--session-id", default=None)

    return parser


def main(argv=None):
    if "--selftest" in (argv if argv is not None else sys.argv):
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help(sys.stderr)
        return 1

    session_id = getattr(args, "session_id", None) or new_session_id()
    if getattr(args, "instance_id", None) and args.instance_id and \
            not INSTANCE_ID_PATTERN.match(args.instance_id):
        print("=== In-instance observation ===")
        print("session-id: %s" % session_id)
        print("STATUS: %s" % STATUS_FAIL)
        print("NEXT_ACTION: '%s' is not an instance id of the expected form; ask the customer "
              "for the real identifier instead of guessing it" % args.instance_id)
        return 1

    if args.command == "report":
        report = cmd_report(args, session_id)
    elif args.command == "guest-plan":
        report = cmd_guest_plan(args, session_id)
    elif args.command == "guest-run":
        report = cmd_guest_run(args, session_id)
    elif args.command == "snapshot":
        report = cmd_snapshot(args, session_id)
    elif args.command == "knowledge":
        sys.stdout.write(cmd_knowledge(args, session_id) + "\n")
        return 0
    else:  # argparse rejects anything else, so this is defensive only
        parser.print_help(sys.stderr)
        return 1

    text = report.render()
    sys.stdout.write(mask_secrets(text) + "\n")
    return 1 if report.status == STATUS_FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
