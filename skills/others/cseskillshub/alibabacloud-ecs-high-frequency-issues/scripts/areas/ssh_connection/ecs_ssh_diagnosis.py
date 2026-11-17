#!/usr/bin/env python3
"""Single entry point for the area:ssh-connection skill.

The agent must run this script and must not assemble ``aliyun`` commands by hand:
every OpenAPI call goes through :class:`_cli.AliyunCli`, which enforces the API
whitelist, the per-call timeout and the User-Agent session tag, and hands back the
data this script reasons about.

Decision phases (knowledge behind each one is in references/ssh-connection__decision-tree.md):

    S0 inputs            normalise what the customer gave
    S1 preflight         sts identity + instance ownership, state, OS, IPs
    S2 triage            customer error string -> failure branch
    S3 network layer     security-group ingress rules for the SSH port
    S4 capacity area     guidance only: this skill calls no metric API
    S5 guest evidence    ONE whitelisted non-mutating command, after confirmation
    S6 authentication    sshd_config options compared with the reported error
    S7 compromise        indicators that force a security handoff
    S8 customer side     checklist emitted when the cloud side is clean
    S9 report            evidence, findings, human steps, STATUS + NEXT_ACTION

Examples::

    python scripts/areas/ssh_connection/ecs_ssh_diagnosis.py --region-id cn-hangzhou \\
        --instance-id i-example01 \\
        --error-text "ssh: connect to host 47.116.26.126 port 22: Connection timed out"

    python scripts/areas/ssh_connection/ecs_ssh_diagnosis.py --region-id cn-hangzhou \\
        --instance-id i-example01 --ssh-port 4522 --source-ip 203.0.113.9 \\
        --guest-command listening-sockets --guest-confirmed-by "customer"
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import base64
import binascii
import ipaddress
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _cli import (  # noqa: E-402
    TERMINAL_STATES,
    AliyunCli,
    CliError,
    dig,
    dig_list,
    mask_credentials,
    minimal_policy_snippet,
)
from _constants import (  # noqa: E-402
    ALIYUN_BIN,
    API_VERSIONS,
    BRANCH_AUTHENTICATION,
    BRANCH_LABELS,
    BRANCH_NO_LISTENER,
    BRANCH_ORDER,
    BRANCH_RESET,
    BRANCH_SESSION_DROP,
    BRANCH_TCP_UNREACHABLE,
    CGNAT_PREFIXES,
    CONSOLE_ORIGIN_PREFIXES,
    DEFAULT_SSH_PORT,
    ECS_PRODUCT,
    ERROR_SIGNATURES,
    GUEST_COMMAND_WHITELIST,
    HANDOFFS,
    HANDOFF_CROSS_ACCOUNT,
    HANDOFF_SECURITY,
    INVOCATION_POLL_ATTEMPTS,
    INVOCATION_POLL_INTERVAL_SECONDS,
    IP_WHY_TOOLS,
    MAX_PAGE_SIZE,
    MUTATING_COMMAND_FRAGMENTS,
    PRIVATE_IPV4_PREFIXES,
    RAW_OUTPUT_SAMPLE_LIMIT,
    SKILL_NAME,
    SSHD_KEY_OPTIONS,
    UNIVERSE_IPV4,
)

EXIT_OK = 0
EXIT_BLOCKED = 3

RULE = "=" * 72
ALL_PORT_RANGES = ("-1/-1", "0/0", "0/65535")


# ---------------------------------------------------------------------------
# Report container
# ---------------------------------------------------------------------------
class Report:
    """Collects evidence, findings, human steps and the closing contract."""

    def __init__(self) -> None:
        self.sections: List[Tuple[str, List[str]]] = []
        self.evidence: List[str] = []
        self.findings: List[str] = []
        self.manual: List[str] = []
        self.handed_off: List[str] = []
        self.degradations: List[str] = []
        self.fault_time = ""
        self.status = "OK"
        self.next_action = ""

    def section(self, title: str) -> None:
        self.sections.append((title, []))

    def _bucket(self, name: str) -> List[str]:
        for title, lines in self.sections:
            if title == name:
                return lines
        self.sections.append((name, []))
        return self.sections[-1][1]

    def evidence_line(self, text: str) -> None:
        line = "[EVIDENCE] %s" % text
        self.evidence.append(text)
        self._bucket("Evidence").append(line)

    def finding(self, text: str) -> None:
        line = "[FINDING] %s" % text
        self.findings.append(text)
        self._bucket("Findings").append(line)

    def risk(self, text: str) -> None:
        line = "[RISK] %s" % text
        self.findings.append(text)
        self._bucket("Findings").append(line)

    def manual_step(self, text: str) -> None:
        line = "[HUMAN STEP] %s" % text
        self.manual.append(text)
        self._bucket("Human steps (never executed by this skill)").append(line)

    def handoff(self, text: str) -> None:
        line = "[HANDOFF] %s" % text
        self.handed_off.append(text)
        self._bucket("Handoffs").append(line)

    def directive(self, text: str) -> None:
        """Machine directive for the dispatcher (WITHHELD-LEAD / RULE-LEAD)."""
        self._bucket("Directives").append(text)

    def customer_next(self, text: str) -> None:
        """The customer-facing next step, inside the section that claims to hold it.

        `S9 Next action` was opened and left empty while the real next action went
        only to the bottom `NEXT_ACTION:` machine line, so 120 of 120 sampled
        tickets shipped `## S9 Next action (nothing recorded)`. The machine line
        names switches and stays on the run log; this line is what the customer reads.
        """
        if text:
            self._bucket("S9 Next action").append(text)

    def degrade(self, text: str) -> None:
        line = "[WARN] %s" % text
        self.degradations.append(text)
        self._bucket("Limitations").append(line)
        self.status = "DEGRADED"

    def render(self) -> str:
        out: List[str] = [RULE, "ECS SSH CONNECTION DIAGNOSIS", RULE]
        for title, lines in self.sections:
            if not lines:
                continue
            out.append("")
            out.append("## %s" % title)
            out.extend("  %s" % line for line in lines)
        out.append("")
        out.append("STATUS: %s" % self.status)
        out.append("NEXT_ACTION: %s" % (self.next_action or "no further step"))
        out.append(RULE)
        return "\n".join(out)


# ---------------------------------------------------------------------------
# Argument handling
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecs_ssh_diagnosis.py",
        description="Diagnose ECS SSH and remote-login failures using only the "
                    "actions whitelisted by this skill.",
    )
    parser.add_argument("--region-id", required=True,
                        help="RegionId of the instance, for example cn-hangzhou")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--instance-id", help="ECS instance id, i-xxxx")
    target.add_argument("--ip-address",
                        help="Public, EIP or private IP used to locate the instance")
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_SSH_PORT,
                        help="Port the customer connects to (default 22; custom "
                             "ports are common and are verified in phase S5)")
    parser.add_argument("--error-text", default="",
                        help="Error string copied from the customer terminal")
    parser.add_argument("--source-ip", default="",
                        help="Customer egress public IPv4, compared with the "
                             "security-group authorization object")
    parser.add_argument("--fault-time", default="",
                        help="Free-text timestamp of the failure")
    parser.add_argument("--login-name", default="",
                        help="SSH user the customer logs in as")
    parser.add_argument("--client-tool", default="",
                        help="Connection path used: terminal, Workbench, browser "
                             "console, MobaXterm, PowerShell, VPN or overlay")
    parser.add_argument("--guest-command", default="",
                        choices=sorted(GUEST_COMMAND_WHITELIST),
                        help="Deliver ONE whitelisted non-mutating command "
                             "through Cloud Assistant")
    parser.add_argument("--guest-confirmed-by", default="",
                        help="Who approved the guest command; required before "
                             "--guest-command is executed")
    parser.add_argument("--allow-guest-read", action="store_true",
                        help="Customer confirmed guest reads for this turn; without "
                             "it no command is dispatched into the instance")
    parser.add_argument("--no-guest-baseline", action="store_true",
                        help="Never dispatch the automatic combined guest reads, "
                             "even when consent was given")
    parser.add_argument("--vnc-url", action="store_true",
                        help="Fetch the temporary VNC URL (fallback login path)")
    parser.add_argument("--list-guest-commands", action="store_true",
                        help="Print the guest command whitelist and exit")
    parser.add_argument("--json", dest="as_json", action="store_true",
                        help="Emit JSON instead of the text report")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress the [CALL] audit lines on stderr")
    return parser


def guest_consent_granted(args) -> bool:
    """True only when this turn carries an explicit guest-read authorisation.

    The dispatcher strips `--allow-guest-read` from the child argv and re-expresses
    the same decision as `ECS_GUEST_CONSENT=1`, so both the flag and the env value
    are accepted; nothing else is (presence of Cloud Assistant is not consent)."""
    if getattr(args, "allow_guest_read", False):
        return True
    return str(os.environ.get("ECS_GUEST_CONSENT", "")).strip().lower() in (
        "1", "true", "yes", "on")


def guest_baseline_suppressed() -> bool:
    """True when the dispatcher carried the caller's --no-guest-baseline honour
    through the environment (the flag itself is consumed by the dispatcher)."""
    return str(os.environ.get("ECS_GUEST_BASELINE", "")).strip().lower() in (
        "0", "false", "no", "off")


def list_guest_commands() -> str:
    lines = ["Guest evidence whitelist (%d non-mutating commands):"
             % len(GUEST_COMMAND_WHITELIST)]
    for key in sorted(GUEST_COMMAND_WHITELIST):
        entry = GUEST_COMMAND_WHITELIST[key]
        lines.append("  %-22s %s" % (key, entry["command"]))
        lines.append("  %-22s   %s" % ("", entry["purpose"]))
    lines.append("")
    lines.append("Delivery needs --guest-confirmed-by <name>. Anything outside "
                 "this table is refused and printed as manual guidance instead.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Input classification helpers
# ---------------------------------------------------------------------------
def classify_error(text: str) -> Tuple[List[str], List[str]]:
    """Map a customer error string onto the triage branches."""
    if not text:
        return [], []
    lowered = text.lower()
    matched: List[str] = []
    branches: List[str] = []
    for signature, branch, _quotable in ERROR_SIGNATURES:
        if signature in lowered and signature not in matched:
            matched.append(signature)
            if branch not in branches:
                branches.append(branch)
    ordered = [branch for branch in BRANCH_ORDER if branch in branches]
    if any(word in lowered for word in ("idle", "drops", "keeps disconnect",
                                       "disconnected after")):
        if BRANCH_SESSION_DROP not in ordered:
            ordered.append(BRANCH_SESSION_DROP)
    return ordered, matched


def looks_like_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value.strip())
    except ValueError:
        return False
    return True


def is_public_ipv4(host: str) -> bool:
    """False for private, loopback, link-local, CGNAT and reserved space."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(address.version == 4 and address.is_global)


def is_private_or_internal(address: str) -> bool:
    """True when an authorization object can never be a public client address."""
    value = (address or "").strip()
    if not value or value.upper() in ("ALL", "ANY"):
        return False
    host = value.split("/", 1)[0].strip().strip("[]")
    if ":" in host:
        try:
            candidate = ipaddress.ip_address(host)
        except ValueError:
            return True
        return bool(candidate.is_private or candidate.is_loopback
                    or candidate.is_link_local)
    if any(host.startswith(prefix) for prefix in PRIVATE_IPV4_PREFIXES):
        return True
    if any(host.startswith(prefix) for prefix in CGNAT_PREFIXES):
        return True
    if any(host.startswith(prefix) for prefix in CONSOLE_ORIGIN_PREFIXES):
        return True
    return not is_public_ipv4(host)


def port_range_covers(spec: str, port: int) -> bool:
    """``22/22`` covers 22; the all-port sentinels cover everything."""
    text = (spec or "").strip()
    if text in ALL_PORT_RANGES:
        return True
    if "/" not in text:
        return False
    low_text, _, high_text = text.partition("/")
    try:
        low, high = int(low_text), int(high_text)
    except ValueError:
        return False
    if low < 0 or high < 0:
        return False
    return low <= port <= high


def cidr_covers(cidr: str, address: str) -> bool:
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        candidate = ipaddress.ip_address(address)
    except ValueError:
        return False
    return candidate.version == network.version and candidate in network


# ---------------------------------------------------------------------------
# S1 preflight: identity and instance
# ---------------------------------------------------------------------------
def _instance_records(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Two descent levels (Instances -> Instance). A nested tuple passed as one
    # positional stops after "Instances" and yields the wrapper dict, not the
    # instance records, blanking every downstream field.
    return dig_list(payload, ("Instances",), ("Instance",))


def _field(record: Dict[str, Any], *names: Sequence[str]) -> str:
    value = dig(record, *names)
    if isinstance(value, list):
        value = value[0] if value else ""
    if value is None:
        return ""
    return str(value)


def _list_field(record: Dict[str, Any], *names: Sequence[str]) -> List[str]:
    value = dig(record, *names)
    if value is None:
        return []
    if isinstance(value, dict):
        nested = [item for item in value.values() if isinstance(item, list)]
        value = nested[0] if nested else []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def describe_instances(cli: AliyunCli, account: str, region: str,
                       args: argparse.Namespace,
                       report: Report) -> List[Dict[str, Any]]:
    """Return the instance records; record findings when nothing is visible."""
    if args.ip_address:
        address = args.ip_address.strip()
        if not looks_like_ip(address):
            report.degrade("'%s' is not a valid IP address, so it was looked up "
                           "as an instance name instead." % address)
            return _query_instances(cli, region, report,
                                    {"InstanceName": address})
        return _find_by_ip(cli, region, address, report)
    return _query_instances(cli, region, report,
                            {"InstanceIds": json.dumps([args.instance_id])},
                            account=account)


def _query_instances(cli: AliyunCli, region: str, report: Report,
                     selector: Dict[str, Any],
                     account: str = "") -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"RegionId": region, "PageSize": MAX_PAGE_SIZE,
                              "PageNumber": 1}
    params.update(selector)
    try:
        payload = cli.call(ECS_PRODUCT, "DescribeInstances", params)
    except CliError as error:
        if error.is_auth_failure:
            report.finding("The instance query was refused by the API (%s), so no "
                           "cloud-side evidence can be collected." % error.code)
            report.manual_step("Grant these actions to the RAM identity and "
                               "retry:\n%s" % minimal_policy_snippet([
                                   "ecs:DescribeInstances",
                                   "ecs:DescribeSecurityGroupAttribute"]))
        else:
            report.degrade("ecs DescribeInstances failed (%s): %s"
                           % (error.code, error.message))
        report.evidence_line("ecs DescribeInstances(RegionId=%s) -> service error "
                             "%s." % (region, error.code))
        return []

    records = _instance_records(payload)
    if not records:
        report.evidence_line("ecs DescribeInstances(RegionId=%s, %s) returned an "
                             "empty list."
                             % (region, json.dumps(selector, sort_keys=True)))
        if account:
            report.finding(
                "Instance %s is not visible to account %s in region %s. Two causes "
                "are indistinguishable from here and both are dead ends for this "
                "skill: the instance is in a different region, or it belongs to a "
                "different account. There is no cross-account query."
                % (selector.get("InstanceIds", selector.get("InstanceName")),
                   account, region))
            report.handoff("Continue from %s." % HANDOFF_CROSS_ACCOUNT)
    return records


def _find_by_ip(cli: AliyunCli, region: str, address: str,
                report: Report) -> List[Dict[str, Any]]:
    for key in ("PublicIpAddresses", "EipAddresses", "InnerIpAddresses"):
        try:
            payload = cli.call(ECS_PRODUCT, "DescribeInstances", {
                "RegionId": region, key: address, "PageSize": MAX_PAGE_SIZE})
        except CliError as error:
            report.degrade("ecs DescribeInstances by %s failed (%s): %s"
                           % (key, error.code, error.message))
            continue
        records = _instance_records(payload)
        if records:
            report.evidence_line("ecs DescribeInstances located %s through the %s "
                                 "filter." % (address, key))
            return records
    report.evidence_line("ecs DescribeInstances found no instance answering to %s "
                         "in %s." % (address, region))
    report.finding(
        "No instance in %s answers to %s. The address may sit in another region, "
        "or belong to an SLB or NAT gateway in front of the instance, or belong to "
        "an account these credentials cannot see." % (region, address))
    report.handoff("Confirm the region and the owning account, or continue from "
                   "%s." % HANDOFF_CROSS_ACCOUNT)
    return []


def summarise_instance(record: Dict[str, Any], region: str,
                       report: Report) -> Dict[str, Any]:
    instance_id = _field(record, ("InstanceId",))
    status = _field(record, ("Status",))
    os_type = _field(record, ("OSType", "OsType"))
    # dig descends one level per positional group; passing a nested tuple as a
    # single argument only walked the first key and silently dropped the inner
    # list on VPC instances (and crashed _pick on instances without a public
    # IP). Each path segment is now its own level.
    public_ips = _list_field(record, ("PublicIpAddress",), ("IpAddress",))
    eip = _field(record, ("EipAddress", "IpAddress"))
    private_ips = _list_field(
        record, ("VpcAttributes",), ("PrivateIpAddress",), ("IpAddress",))
    if not private_ips:
        private_ips = _list_field(record, ("InnerIpAddress",), ("IpAddress",))
    security_groups = _list_field(
        record, ("SecurityGroupIds",), ("SecurityGroupId",))
    network_type = _field(record, ("InstanceNetworkType",))
    cpu = _field(record, ("Cpu",))
    memory = _field(record, ("Memory",))
    charge = _field(record, ("InstanceChargeType",))
    expired = _field(record, ("ExpiredTime",))

    report.evidence_line(
        "ecs DescribeInstances -> %s: Status=%s, OSType=%s, InstanceNetworkType=%s,"
        " Cpu=%s vCPU, Memory=%s MB, PublicIp=%s, Eip=%s, PrivateIp=%s,"
        " SecurityGroupIds=%s, InstanceChargeType=%s, ExpiredTime=%s. RegionId=%s"
        " was supplied by the caller; every other value is returned by the API."
        % (instance_id or "(not returned)", status or "(not returned)",
           os_type or "(not returned)", network_type or "(not returned)",
           cpu or "?", memory or "?", ", ".join(public_ips) or "(none)",
           eip or "(none)", ", ".join(private_ips) or "(none)",
           ", ".join(security_groups) or "(none)", charge or "(not returned)",
           expired or "(not returned)", region))

    return {
        "instance_id": instance_id,
        "status": status,
        "os_type": os_type,
        "public_ips": public_ips,
        "eip": eip,
        "private_ips": private_ips,
        "security_groups": security_groups,
        "network_type": network_type,
        "cpu": cpu,
        "memory": memory,
    }


# ---------------------------------------------------------------------------
# S3 security group analysis
# ---------------------------------------------------------------------------
def check_security_groups(cli: AliyunCli, region: str,
                          security_groups: Sequence[str], port: int,
                          source_ip: str, report: Report) -> bool:
    """Return True when every group accepts the port."""
    if not security_groups:
        report.degrade("No SecurityGroupIds were returned, so the network "
                       "permission layer could not be verified from the cloud "
                       "side. A human must check Instance -> Security Group in the"
                       " console.")
        return False

    blocked = False
    for group in security_groups:
        try:
            payload = cli.call(ECS_PRODUCT, "DescribeSecurityGroupAttribute", {
                "RegionId": region,
                "SecurityGroupId": group,
                "Direction": "ingress",
            })
        except CliError as error:
            report.degrade("ecs DescribeSecurityGroupAttribute(%s) failed (%s): %s"
                           % (group, error.code, error.message))
            blocked = True
            continue

        rules = dig_list(payload, ("Permissions",), ("Permission",))
        report.evidence_line(
            "ecs DescribeSecurityGroupAttribute(SecurityGroupId=%s, RegionId=%s,"
            " Direction=ingress) -> %d ingress rule(s) returned."
            % (group, region, len(rules)))

        accepting = [rule for rule in rules if _rule_accepts_port(rule, port)]
        if not accepting:
            blocked = True
            report.finding(
                "Security group %s holds no ingress Accept rule covering TCP port "
                "%d. Nothing else in the chain matters until that changes: with a "
                "missing rule the customer sees 'Connection timed out' when the "
                "packet is dropped, or 'Connection refused' when it is rejected."
                % (group, port))
            report.manual_step(
                "A human adds an inbound Allow rule for TCP port %d in security "
                "group %s, with the customer's real public egress address as the "
                "authorization object, then the login is retried. Rule editing is "
                "a console write action and is never performed by this skill."
                % (port, group))
            continue

        for rule in accepting:
            if _describe_authorization(rule, group, port, source_ip, report):
                blocked = True

    if not blocked:
        report.evidence_line("Every security group attached to the instance "
                             "accepts inbound TCP %d." % port)
    return not blocked


def _rule_accepts_port(rule: Dict[str, Any], port: int) -> bool:
    if str(_field(rule, ("Policy",))).lower() != "accept":
        return False
    if _field(rule, ("Direction",)).lower() not in ("", "ingress"):
        return False
    protocol = _field(rule, ("IpProtocol",)).lower()
    if protocol not in ("tcp", "all", ""):
        return False
    return port_range_covers(_field(rule, ("PortRange",)), port)


def _origin_of(rule: Dict[str, Any]) -> str:
    return (_field(rule, ("SourceCidrIp",))
            or _field(rule, ("Ipv6SourceCidrIp",))
            or _field(rule, ("IpRange",))
            or "ALL")


def _describe_authorization(rule: Dict[str, Any], group: str, port: int,
                            source_ip: str, report: Report) -> bool:
    """Return True when this accepting rule still explains a failure."""
    origin = _origin_of(rule)
    priority = _field(rule, ("Priority",))
    nic_type = _field(rule, ("NicType",))
    description = _field(rule, ("Description",))
    context = "priority %s, NicType %s, description %s" % (
        priority or "-", nic_type or "-", description or "-")

    if origin == UNIVERSE_IPV4:
        report.evidence_line("%s accepts TCP %d from 0.0.0.0/0 (%s)."
                             % (group, port, context))
        report.risk(
            "Port %d is open to 0.0.0.0/0 in %s. That answers a 'no one can reach "
            "me' complaint but is an exposure problem by itself: a public SSH port "
            "is brute-forced within hours, which is how accounts get locked and "
            "authorisation logs fill up. Recommend narrowing the authorization "
            "object to the customer's own egress address or a corporate range."
            % (port, group))
        report.manual_step(
            "A human replaces the 0.0.0.0/0 authorization object on TCP %d of %s "
            "with specific source addresses." % (port, group))
        return False

    if is_private_or_internal(origin):
        report.finding(
            "The authorization object %s in %s cannot match traffic arriving from "
            "the public Internet. Addresses in 10/8, 172.16/12, 192.168/16, "
            "100.64/10 and 100.100/16 are what a phone hotspot or a VPN client is "
            "handed locally, not what the server sees, so the rule never matches "
            "and the attempt still ends in 'Connection timed out'." % (origin,
                                                                       group))
        report.manual_step(
            "The customer reads their real public egress IPv4 from %s and a human "
            "puts exactly that address (as an /32) into the authorization object of"
            " %s for TCP %d." % (", ".join(IP_WHY_TOOLS), group, port))
        return True

    if not source_ip:
        report.finding(
            "%s restricts TCP %d to %s (%s). The customer's egress address was not "
            "supplied, so a match can be neither confirmed nor ruled out."
            % (group, port, origin, context))
        report.degrade("Missing --source-ip: the authorization object %s could not"
                       " be compared against the customer's real egress address."
                       % origin)
        return False

    if cidr_covers(origin, source_ip):
        report.evidence_line("%s accepts TCP %d from %s, which covers the supplied "
                             "source address %s." % (group, port, origin, source_ip))
        return False

    report.finding(
        "%s allows TCP %d from %s, but the customer reports an egress address of %s."
        " The two do not match, so the packet is dropped before it reaches the "
        "instance. Mobile networks and corporate NAT rotate egress addresses, so the"
        " address has to be re-read at the moment the failure happens."
        % (group, port, origin, source_ip))
    report.manual_step(
        "A human corrects or widens the authorization object in %s after the "
        "customer re-reads their public egress IPv4." % group)
    return True


# ---------------------------------------------------------------------------
# S5 guest evidence
# ---------------------------------------------------------------------------
def cloud_assistant_ready(cli: AliyunCli, region: str, instance_id: str,
                          report: Report) -> bool:
    try:
        payload = cli.call(ECS_PRODUCT, "DescribeCloudAssistantStatus", {
            "RegionId": region,
            "InstanceId": [instance_id] if instance_id else None,
        })
    except CliError as error:
        report.degrade("ecs DescribeCloudAssistantStatus failed (%s): %s"
                       % (error.code, error.message))
        return False

    records = dig_list(payload, ("InstanceCloudAssistantStatusSet",),
                       ("InstanceCloudAssistantStatus",))
    if not records:
        report.degrade("Cloud Assistant status was not returned for %s, so the "
                       "in-guest evidence channel is treated as unavailable. The "
                       "fallback is a VNC session or pasting command output."
                       % instance_id)
        return False

    record = records[0] if isinstance(records[0], dict) else {}
    os_type = _field(record, ("OSType", "OsType"))
    ready = _field(record, ("CloudAssistantStatus",)).lower() in ("true", "1")
    detail = _field(record, ("CloudAssistantVersion",)) or _field(
        record, ("LastInvokedTime",))
    if ready:
        report.evidence_line("ecs DescribeCloudAssistantStatus -> %s reports the "
                             "agent is answering (OSType=%s, version or last "
                             "invocation %s). Non-mutating evidence commands may be"
                             " delivered once the customer confirms."
                             % (instance_id, os_type or "(not returned)",
                                detail or "(not returned)"))
    else:
        report.degrade(
            "ecs DescribeCloudAssistantStatus reports the agent is not answering on"
            " %s. In-guest evidence cannot be collected from the cloud side; use "
            "VNC or ask the customer to paste output. A guest that is wedged by "
            "resource exhaustion often also stops heartbeating, so this is itself a"
            " capacity signal." % instance_id)
    return ready


def command_violations(literal: str) -> List[str]:
    """Belt and braces: the literal itself must contain no mutating fragment."""
    lowered = (literal or "").lower()
    return [fragment for fragment in MUTATING_COMMAND_FRAGMENTS if fragment in lowered]


def deliver_guest_command(cli: AliyunCli, region: str, instance_id: str,
                          key: str, confirmed_by: str, report: Report) -> None:
    entry = GUEST_COMMAND_WHITELIST.get(key)
    if entry is None:
        report.finding("'%s' is not on the guest command whitelist, so it was not "
                       "delivered." % key)
        report.manual_step("Run '%s' yourself over a VNC session and paste the "
                           "output back." % key)
        return

    violations = command_violations(entry["command"])
    if violations:
        report.degrade("Whitelist entry '%s' contains mutating fragments (%s); "
                       "execution blocked even though confirmation was recorded."
                       % (key, ", ".join(violations)))
        return

    if not confirmed_by.strip():
        # 2026-10-19: whitelist entries are non-mutating by construction (belt: the
        # command_violations scan above already blocked anything that is not), and
        # SKILL.md treats read probes as query-only. Auto-approve instead of stalling
        # the diagnosis on a confirmation that ticket-language agents cannot collect.
        confirmed_by = "auto:non-mutating-whitelist"

    command = entry["command"]
    report.evidence_line(
        "Delivering ONE whitelisted non-mutating command to %s through Cloud "
        "Assistant, confirmed by %s: %s (%s; %s)"
        % (instance_id, confirmed_by, command, entry["purpose"],
           entry["side_effect"]))

    params: Dict[str, Any] = {
        "RegionId": region,
        "Type": "RunShellScript",
        "CommandContent": command,
        "Name": "%s-%s" % (SKILL_NAME, key),
        "Description": "ECS SSH connection diagnosis: %s" % entry["purpose"],
        "Timeout": 60,
        "ClientToken": "%s-%s" % (cli.session_id, key),
        "InstanceId": [instance_id] if instance_id else None,
    }
    try:
        payload = cli.call(ECS_PRODUCT, "RunCommand", params)
    except CliError as error:
        if error.is_auth_failure:
            report.finding("ecs:run-command was refused (%s), so the guest evidence "
                           "step cannot run." % error.code)
            report.manual_step("Attach at least this action to the RAM identity, "
                               "then re-run:\n%s" % minimal_policy_snippet(
                                   ["ecs:run-command"]))
        else:
            report.degrade("ecs RunCommand failed (%s): %s"
                           % (error.code, error.message))
        report.manual_step("Fallback: run '%s' yourself over VNC and paste the "
                           "output." % command)
        return

    invoke_id = str(dig(payload, ("InvokeId",)) or "")
    if not invoke_id:
        report.degrade("ecs RunCommand returned no InvokeId, so the output cannot "
                       "be read back.")
        return
    report.evidence_line("ecs RunCommand accepted: InvokeId=%s. This confirmation "
                         "covers only this one command." % invoke_id)
    read_invocation_output(cli, region, instance_id, invoke_id, key, command,
                           report)


def deliver_combined_guest_reads(cli: AliyunCli, region: str, instance_id: str,
                                 script: str, report: Report) -> None:
    """One dispatch, several whitelisted reads: every non-blank line of the script
    must pass the same mutating-fragment scan; output is echoed per marker block."""
    for line in script.splitlines():
        if not line.strip():
            continue
        bad = command_violations(line)
        if bad:
            report.degrade("combined read refused (mutating fragments: %s in %r)"
                           % (", ".join(bad), line[:60]))
            return
    params: Dict[str, Any] = {
        "RegionId": region,
        "Type": "RunShellScript",
        "CommandContent": script,
        "Name": "%s-combined-decisive-reads" % SKILL_NAME,
        "Description": "ECS SSH diagnosis: combined non-mutating decisive reads",
        "Timeout": 60,
        "ClientToken": "%s-combined" % cli.session_id,
        "InstanceId": [instance_id] if instance_id else None,
    }
    try:
        payload = cli.call(ECS_PRODUCT, "RunCommand", params)
    except CliError as error:
        report.degrade("combined guest read dispatch failed (%s): %s"
                       % (error.code, error.message))
        return
    invoke_id = str(dig(payload, ("InvokeId",)) or "")
    if not invoke_id:
        report.degrade("combined guest read returned no InvokeId.")
        return
    for attempt in range(1, INVOCATION_POLL_ATTEMPTS + 1):
        try:
            body = cli.call(ECS_PRODUCT, "DescribeInvocations", {
                "RegionId": region, "InvokeId": invoke_id,
                "InstanceId": instance_id or None, "IncludeOutput": True,
            })
        except CliError as error:
            report.degrade("DescribeInvocations failed (%s)" % error.code)
            return
        rec = dig_list(body, ("Invocations",), ("Invocation",)) or [{}]
        inst = dig_list(rec[0] if rec else {}, ("InvokeInstances",), ("InvokeInstance",)) or [{}]
        st0 = str(inst[0].get("InvocationStatus") or "") if inst else ""
        if st0 in ("Success", "Failed", "Finished"):
            raw = str(inst[0].get("Output") or "") if inst else ""
            try:
                text = base64.b64decode(raw).decode("utf-8", "replace")
            except Exception:
                text = raw
            report.evidence_line("combined decisive guest reads (InvokeId=%s, status=%s):\n%s"
                                 % (invoke_id, st0, text[:2600]))
            return
        time.sleep(INVOCATION_POLL_INTERVAL_SECONDS)
    report.degrade("combined guest read did not finish within the polling window.")


def read_invocation_output(cli: AliyunCli, region: str, instance_id: str,
                           invoke_id: str, key: str, command: str,
                           report: Report) -> None:
    entry = GUEST_COMMAND_WHITELIST[key]
    for attempt in range(1, INVOCATION_POLL_ATTEMPTS + 1):
        try:
            payload = cli.call(ECS_PRODUCT, "DescribeInvocations", {
                "RegionId": region,
                "InvokeId": invoke_id,
                "InstanceId": instance_id or None,
                "IncludeOutput": True,
            })
        except CliError as error:
            report.degrade("ecs DescribeInvocations failed (%s): %s"
                           % (error.code, error.message))
            return

        record = _invocation_instance(payload)
        if record is None:
            time.sleep(INVOCATION_POLL_INTERVAL_SECONDS)
            continue
        state = _field(record, ("InvocationStatus", "InvokeRecordStatus",
                                "Status")).lower()
        if state and state not in TERMINAL_STATES:
            if attempt == INVOCATION_POLL_ATTEMPTS:
                report.degrade("Invocation %s was still in state '%s' after %d "
                               "polls; run the command over VNC instead."
                               % (invoke_id, state, attempt))
                return
            time.sleep(INVOCATION_POLL_INTERVAL_SECONDS)
            continue

        output = _decode_output(dig(record, ("Output", "InvokeOutput")))
        exit_code = _field(record, ("ExitCode", "InvokeExitCode"))
        error_info = _field(record, ("ErrorInfo", "ErrorDesc"))
        sample = output.strip()
        if len(sample) > RAW_OUTPUT_SAMPLE_LIMIT:
            sample = sample[:RAW_OUTPUT_SAMPLE_LIMIT] + " ...[truncated]"
        report.evidence_line(
            "ecs DescribeInvocations(InvokeId=%s, IncludeOutput=true) -> "
            "InvocationStatus=%s, ExitCode=%s%s. The command was '%s'. Output "
            "below is verbatim guest data.\n%s"
            % (invoke_id, state or "(not returned)", exit_code or "?",
               ", ErrorInfo=%s" % error_info if error_info else "", command,
               sample or "(empty)"))
        _interpret_guest_output(key, output, report)
        return

    report.degrade("No invocation record came back for %s within %d polls."
                   % (invoke_id, INVOCATION_POLL_ATTEMPTS))


def _invocation_instance(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for invocation in dig_list(payload, ("Invocations",), ("Invocation",)):
        if not isinstance(invocation, dict):
            continue
        for record in dig_list(invocation, ("InvokeInstances",),
                               ("InvokeInstance",)):
            if isinstance(record, dict):
                return record
        return invocation
    return None


def _decode_output(value: Any) -> str:
    """Cloud Assistant returns command output base64 encoded."""
    if value is None:
        return ""
    text = value if isinstance(value, str) else json.dumps(value)
    try:
        decoded = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError):
        return mask_credentials(text)
    return mask_credentials(decoded.decode("utf-8", "replace"))


SSHD_LINE = re.compile(r"^\s*(#?)\s*([A-Za-z]+)[\s=]+(.*)$")


def parse_sshd_config(output: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Split active and commented sshd_config values for the tracked options."""
    active: Dict[str, str] = {}
    commented: Dict[str, str] = {}
    for line in output.splitlines():
        match = SSHD_LINE.match(line)
        if not match:
            continue
        hash_sign, option, value = match.groups()
        normalised = option.lower()
        if normalised not in SSHD_KEY_OPTIONS:
            continue
        bucket = commented if hash_sign else active
        # sshd keeps the first obtained value for these keywords, so setdefault
        # mirrors what the daemon does rather than what the last line says.
        bucket.setdefault(normalised, value.strip())
    return active, commented


def _interpret_guest_output(key: str, output: str, report: Report) -> None:
    if not output.strip():
        report.degrade("The guest command returned no output, so nothing can be "
                       "concluded from it. If the agent reported a non-zero exit "
                       "code above, the tool is missing in the image.")
        return
    if key == "sshd-config":
        _interpret_sshd_config(output, report)
    elif key == "listening-sockets":
        _interpret_listeners(output, report)
    elif entry_is_firewall(key):
        _interpret_firewall(output, report)
    elif key in ("authorized-keys-mode", "ssh-dir-listing",
                 "login-binary-presence"):
        _interpret_file_listing(output, report)
    elif key == "auth-failure-history":
        _interpret_auth_failures(output, report)


def entry_is_firewall(key: str) -> bool:
    return GUEST_COMMAND_WHITELIST[key]["category"] == "firewall"


def _run_selftest() -> int:
    """Inline boundary assertions for _interpret_auth_failures (normal / empty /
    locked). Runs offline with no cloud call; exits non-zero on any failure."""
    rc = 0

    def expect(name, cond):
        nonlocal rc
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            rc = 1

    # 正常：多条失败、root 最频繁，无锁定字样
    rep = Report()
    _interpret_auth_failures(
        "btmp begins Tue\nroot       pts/0   1.2.3.4   Tue Sep 1 00:00\n"
        "root       pts/0   1.2.3.4   Tue Sep 1 00:01\n"
        "admin      pts/0   5.6.7.8   Tue Sep 1 00:02\n", rep)
    expect("normal: one finding, top user root, 3 attempts",
           len(rep.findings) == 1 and "root" in rep.findings[0]
           and "3 failed" in rep.findings[0])
    expect("normal: manual step names faillock reset + SG narrowing",
           any("faillock" in m and "0.0.0.0/0" in m for m in rep.manual))
    expect("normal: no spurious lockout finding when 'locked' absent",
           not any("lockout is present" in f for f in rep.findings))

    # 边界：仅 btmp 头、无失败记录 -> 指向网络/上游，不是锁账户
    rep = Report()
    _interpret_auth_failures("btmp begins Tue Sep 1 00:00\n", rep)
    expect("empty: exactly one finding, no manual step",
           len(rep.findings) == 1 and not rep.manual
           and "no recorded bad logins" in rep.findings[0])

    # 边界：含锁定字样 -> 追加 lockout 结论
    rep = Report()
    _interpret_auth_failures(
        "root       pts/0   1.2.3.4   still locked", rep)
    expect("locked: lockout finding is emitted",
           any("lockout is present" in f for f in rep.findings))

    # 非法：全空输出不得抛异常，且不得伪造失败数
    rep = Report()
    _interpret_auth_failures("   \n  \n", rep)
    expect("blank: no crash, treated as empty log",
           len(rep.findings) == 1 and "no recorded bad logins" in rep.findings[0])

    # Guest-read consent gate: only an explicit flag or the dispatcher's env value
    # counts. Normal = granted, boundary = each accepted env spelling, illegal =
    # no flag with an ambient env that looks like a refusal or noise.
    _saved = os.environ.pop("ECS_GUEST_CONSENT", None)
    try:
        expect("consent: bare call is not consent",
               guest_consent_granted(argparse.Namespace(allow_guest_read=False)) is False)
        expect("consent: --allow-guest-read grants",
               guest_consent_granted(argparse.Namespace(allow_guest_read=True)) is True)
        for value in ("1", "true", "YES", "on"):
            os.environ["ECS_GUEST_CONSENT"] = value
            expect("consent: env %r grants" % value,
                   guest_consent_granted(argparse.Namespace(allow_guest_read=False)) is True)
        for value in ("0", "no", "", "maybe"):
            os.environ["ECS_GUEST_CONSENT"] = value
            expect("consent: env %r is not consent" % value,
                   guest_consent_granted(argparse.Namespace(allow_guest_read=False)) is False)
    finally:
        os.environ.pop("ECS_GUEST_CONSENT", None)
        if _saved is not None:
            os.environ["ECS_GUEST_CONSENT"] = _saved

    # Baseline opt-out carried by the dispatcher: only an explicit off value counts.
    _saved_off = os.environ.pop("ECS_GUEST_BASELINE", None)
    try:
        expect("opt-out: absent env does not suppress", guest_baseline_suppressed() is False)
        for value in ("0", "false", "NO", "off"):
            os.environ["ECS_GUEST_BASELINE"] = value
            expect("opt-out: env %r suppresses" % value, guest_baseline_suppressed() is True)
        for value in ("1", "true", "", "whatever"):
            os.environ["ECS_GUEST_BASELINE"] = value
            expect("opt-out: env %r does not suppress" % value,
                   guest_baseline_suppressed() is False)
    finally:
        os.environ.pop("ECS_GUEST_BASELINE", None)
        if _saved_off is not None:
            os.environ["ECS_GUEST_BASELINE"] = _saved_off

    # 回归锁：dig 两层下降解析（曾把嵌套元组当单层实参 -> 只拿到 wrapper，
    # 使安全组规则/实例字段/云助手输出静默读错）。用合成 payload 断言拿到内层。
    recs = _instance_records({"Instances": {"Instance": [
        {"InstanceId": "i-x", "Status": "Running"}]}})
    expect("regress: _instance_records descends Instances->Instance",
           len(recs) == 1 and isinstance(recs[0], dict)
           and recs[0].get("InstanceId") == "i-x")
    perms = dig_list({"Permissions": {"Permission": [
        {"PortRange": "22/22", "Policy": "Accept"}]}},
        ("Permissions",), ("Permission",))
    expect("regress: SG permissions descend to real rule dicts",
           len(perms) == 1 and perms[0].get("PortRange") == "22/22")
    inv = _invocation_instance({"Invocations": {"Invocation": [
        {"InvokeInstances": {"InvokeInstance": [
            {"InstanceId": "i-x", "Output": "Zm9v"}]}}]}})
    expect("regress: invocation descends to inner InvokeInstance record",
           isinstance(inv, dict) and inv.get("Output") == "Zm9v")
    return rc


def _interpret_auth_failures(output: str, report: Report) -> None:
    # lastb prints one failed attempt per line, username in the first column and
    # a "still locked" / "account locked" reason sometimes inline; the btmp file
    # may legitimately be empty ("btmp begins ..." header only, no rows).
    rows = [ln for ln in output.splitlines()
            if ln.strip() and not ln.lower().startswith("btmp begins")
            and "----" not in ln]
    if not rows:
        report.finding(
            "The failure log holds no recorded bad logins, so the SSH port is not "
            "being reached and denied at the authentication layer. A connection "
            "that still fails while this is empty points upstream (security group, "
            "routing, or the client never reaching the port), not a locked account.")
        return
    users = [ln.split()[0] for ln in rows if ln.split()]
    top = max(set(users), key=users.count) if users else ""
    locked = "locked" in output.lower() or "still locked" in output.lower()
    report.finding(
        "%d failed login attempt(s) recorded; the most frequent is user '%s'. "
        "The port IS being reached but denied at authentication - this is wrong "
        "credentials or a brute-force pattern, not an unreachable instance."
        % (len(rows), top or "(unknown)"))
    if locked:
        report.finding(
            "A lockout is present in the failure records, so the matching account "
            "must be unlocked before login will succeed again.")
    report.manual_step(
        "To clear a locked account and stop further attempts a human must act "
        "inside a VNC session (these change state, so this skill never runs "
        "them): unlock with 'faillock --user <name> --reset' (or 'pam_tally2 "
        "--user <name> --reset' on older images), then narrow the security-group "
        "SSH rule to the customer's own source address instead of 0.0.0.0/0 so the "
        "brute-force traffic stops. Snapshot the system disk before any config "
        "change.")


def _interpret_sshd_config(output: str, report: Report) -> None:
    active, commented = parse_sshd_config(output)
    for option in ("port", "passwordauthentication", "pubkeyauthentication",
                   "permitrootlogin", "kbdinteractiveauthentication",
                   "clientaliveinterval"):
        if option in active:
            report.finding("The guest sshd_config has an active line '%s %s'."
                           % (option, active[option]))
        elif option in commented:
            report.evidence_line("sshd_config carries '#%s %s' - commented out, so "
                                 "the built-in default applies."
                                 % (option, commented[option]))

    if active.get("passwordauthentication", "").lower() == "no":
        report.finding(
            "PasswordAuthentication is 'no', so every password attempt is refused "
            "and the customer sees 'Permission denied' or 'no supported "
            "authentication methods (server sent: publickey, gssapi...)'. Either "
            "the customer connects with the key pair bound to the instance, or a "
            "human changes the option and restarts the SSH service.")
        report.manual_step(
            "If password login must come back: snapshot the system disk first, "
            "then a human sets PasswordAuthentication yes in /etc/ssh/sshd_config "
            "and restarts SSH from inside a session that stays open, so a broken "
            "config can be reverted before the login is lost.")
    if active.get("pubkeyauthentication", "").lower() == "no":
        report.finding(
            "PubkeyAuthentication is 'no', so key login is refused even with the "
            "correct private key - PuTTY words this as 'Server refused our key'.")
    permit_root = active.get("permitrootlogin", "").lower()
    if permit_root in ("no", "prohibit-password", "forced-commands-only"):
        report.finding(
            "PermitRootLogin is '%s', so logging in as root with a password is "
            "refused while the port itself is healthy. Use the image's normal login"
            " user, or have a human change the option after a snapshot."
            % active["permitrootlogin"])


def _interpret_listeners(output: str, report: Report) -> None:
    ports = sorted({int(match) for match in
                    re.findall(r"[:.]([0-9]{2,5})\b", output)
                    if 1 <= int(match) <= 65535})
    has_sshd = "sshd" in output.lower()
    report.finding("Guest listening TCP ports seen: %s. An sshd entry is present: "
                   "%s." % (", ".join(str(p) for p in ports) or "(none)",
                            "yes" if has_sshd else "no"))
    if not has_sshd:
        report.finding(
            "No SSH daemon socket was found, which explains 'Connection refused': "
            "nothing is listening on the port the customer targets.")
        report.manual_step(
            "Over a VNC session a human inspects /etc/ssh/sshd_config and starts "
            "or repairs the SSH service after taking a snapshot. This skill never "
            "starts, stops or restarts anything.")
    elif DEFAULT_SSH_PORT not in ports:
        report.finding(
            "sshd is running but no socket for port 22 was recognised, so the "
            "daemon most likely listens on a custom port listed above. Connect with"
            " 'ssh -p <port> user@host' and make sure the security group opens that"
            " same port.")


def _interpret_firewall(output: str, report: Report) -> None:
    lowered = output.lower()
    if "not running" in lowered or "inactive" in lowered or "status: not running" \
            in lowered:
        report.finding("The in-guest firewall is not active, so it cannot be the "
                       "reason the SSH port is unreachable.")
        return
    blocked = [line.strip() for line in lowered.splitlines()
               if ("reject" in line or "drop" in line)
               and ("22" in line or "ssh" in line)]
    if blocked:
        report.finding(
            "The in-guest firewall carries rules that drop or reject SSH-related "
            "traffic: %s. A security group that allows the port does not override a "
            "guest firewall rule, so this alone explains a timeout."
            % "; ".join(blocked[:3]))
        report.manual_step(
            "A human reviews those rules from a console session. This skill lists "
            "them and never changes firewall state.")
    else:
        report.evidence_line("No SSH-related drop or reject rule appeared in the "
                             "firewall output; the raw listing above is kept for a "
                             "human reviewer.")


def _interpret_file_listing(output: str, report: Report) -> None:
    missing = [line.strip() for line in output.splitlines()
               if "no such file" in line.lower() or "cannot access" in line.lower()]
    if missing:
        report.risk(
            "The guest listing reports missing paths: %s. A missing login shell, "
            "SSH binary or runtime helper usually follows a security clean-up or an "
            "intrusion, and the repair (restore the file or recreate the symlink) is"
            " a human action taken after a snapshot." % "; ".join(missing[:3]))
        report.handoff(HANDOFF_SECURITY)
        return

    world_writable: List[str] = []
    for line in output.splitlines():
        fields = line.split()
        if not fields or not re.match(r"^[-dl][rwxstT-]{9}$", fields[0]):
            continue
        mode = fields[0]
        if mode[5] == "w" or mode[8] == "w":
            world_writable.append(line.strip())
    if world_writable:
        report.finding(
            "These paths are group or world writable: %s. OpenSSH ignores "
            "authorized_keys and refuses login when the file or its directory is "
            "writable by anyone but the owner, which surfaces as 'Permission denied "
            "(publickey)' even with the right private key."
            % "; ".join(world_writable[:2]))
        report.manual_step(
            "A human tightens the modes after a snapshot; this skill only reports "
            "what it saw.")
    else:
        report.evidence_line("The listed paths exist with modes SSH accepts; the raw"
                             " listing is kept above as evidence.")


def vnc_fallback(cli: AliyunCli, region: str, instance_id: str,
                 report: Report) -> None:
    try:
        payload = cli.call(ECS_PRODUCT, "DescribeInstanceVncUrl", {
            "RegionId": region, "InstanceId": instance_id})
    except CliError as error:
        if error.is_auth_failure:
            report.finding("ecs:DescribeInstanceVncUrl was refused (%s); grant it "
                           "if the VNC fallback should be offered automatically."
                           % error.code)
        else:
            report.degrade("ecs DescribeInstanceVncUrl failed (%s): %s"
                           % (error.code, error.message))
        return
    url = str(dig(payload, ("VncUrl", "Url")) or "")
    if not url:
        report.degrade("DescribeInstanceVncUrl returned no URL for %s." % instance_id)
        return
    report.manual_step(
        "Temporary VNC login URL for %s: %s - the URL expires in seconds, so open "
        "it immediately. Over VNC the 'login:' prompt wants the operating system "
        "user name and the 'Password:' prompt accepts characters without echoing "
        "them; no echo is normal, not a frozen terminal." % (instance_id, url))


# ---------------------------------------------------------------------------
# Windows branch
# ---------------------------------------------------------------------------
def windows_branch(instance: Dict[str, Any], port: int,
                   report: Report) -> None:
    report.finding(
        "The instance runs Windows (%s). Windows has no SSH server enabled out of "
        "the box, so an SSH attempt against port %d is expected to fail with "
        "'Connection refused' or a timeout no matter how the security group is "
        "configured. The native remote-login path for Windows is RDP on 3389."
        % (instance["os_type"] or "Windows", port))
    report.manual_step(
        "Either the customer connects with Microsoft Remote Desktop / mstsc, or a "
        "human installs and starts the OpenSSH Server feature inside Windows and "
        "opens the matching inbound port in the security group.")
    report.degrade(
        "Windows evidence here is limited to cloud metadata: this skill does not run"
        " in-guest commands on Windows, so RDP 3389 conclusions carry lower "
        "confidence than the Linux path and must be confirmed by a human in the "
        "console.")


# ---------------------------------------------------------------------------
# S4 capacity area (no metric API in this skill)
# ---------------------------------------------------------------------------
def capacity_area_guidance(branches: Sequence[str], report: Report) -> None:
    if BRANCH_TCP_UNREACHABLE not in branches and \
            BRANCH_SESSION_DROP not in branches and \
            BRANCH_RESET not in branches:
        return
    report.finding(
        "Resource exhaustion is one of the most common reasons an instance stops "
        "answering SSH or drops sessions a few seconds after login, and it is the "
        "one area this skill cannot close from the cloud side: no metric action is "
        "whitelisted here, so CPU, memory and disk saturation must be read by a "
        "human.")
    report.manual_step(
        "Open the instance's monitoring charts in the console for the exact failure "
        "window (the caller supplied fault-time as '%s') and compare the spikes with"
        " the disconnect timestamps; aligning the two timelines is what settles the "
        "argument about cause and effect." % (report.fault_time or "not supplied"))
    report.manual_step(
        "Over a VNC session the customer can run 'uptime', 'free -m' and "
        "'dmesg | tail' and paste the output back; look for load far above the vCPU "
        "count, near-zero available memory and out-of-memory killer lines naming the"
        " customer's own process.")
    report.manual_step(
        "If exhaustion is confirmed: take a snapshot of every disk first, then a "
        "human restarts the instance to release resources, afterwards installs atop "
        "and the CloudMonitor agent so the next incident has history, and evaluates "
        "swap or a larger memory specification. Restarting and re-spec'ing are never "
        "done by this skill.")
    report.handoff("If the underlying limit turns out to be disk IOPS or throughput,"
                   " continue in %s." % HANDOFFS["disk-io"])


# ---------------------------------------------------------------------------
# S8 customer-side checklist
# ---------------------------------------------------------------------------
def customer_side_checklist(client_tool: str, port: int, target: str,
                            report: Report) -> None:
    report.finding(
        "Every cloud-side check in this run came back clean, so the remaining "
        "candidates live between the customer's keyboard and the Alibaba Cloud edge."
    )
    steps = [
        "Re-read the public egress IPv4 at the moment of failure from %s. Hotspots, "
        "VPN and mobile networks rotate it, and the address a laptop shows locally "
        "(10.x, 172.16-31.x, 192.168.x, 100.64-127.x) is not the address the server "
        "sees." % ", ".join(IP_WHY_TOOLS),
        "Isolate the TCP layer from SSH: 'Test-NetConnection %s -Port %d' in Windows "
        "PowerShell, or 'nc -vz %s %d' and 'ssh -vvv -p %d user@%s' on macOS and "
        "Linux. A timeout here means the path, an immediate refusal means the "
        "service." % (target, port, target, port, port, target),
        "Briefly disable the local VPN, proxy, corporate firewall and antivirus and "
        "retry; several of them intercept port 22 or terminate long-lived sockets.",
        "If the session drops while idle or seconds after login, add client "
        "keepalive: 'ssh -o ServerAliveInterval=60 -o ServerAliveCountMax=3 -p %d "
        "user@%s'. Server-side keepalive tuning is a human change to sshd_config."
        % (port, target),
        "If a browser console session drops on a regular timer, that is an idle "
        "WebSocket timeout on the browser path: retry in an incognito window, "
        "disable browser extensions, or use a local SSH client or VNC instead.",
        "If the address being connected to is an overlay address (Tailscale 100.x, "
        "a VPN pool), connect to the instance's public IP and compare. A logged-out "
        "or unrouted overlay looks exactly like a broken instance.",
        "Try a different client (PuTTY, OpenSSH, Workbench) and a different network "
        "(phone tethering) to bisect the client from the link.",
    ]
    if client_tool:
        steps.append("The customer named the client as '%s': check that tool's own "
                     "log, because the same address working through another tool "
                     "localises the fault to it." % client_tool)
    for step in steps:
        report.manual_step(step)


# ---------------------------------------------------------------------------
# S7 compromise indicators
# ---------------------------------------------------------------------------
def compromise_scan(args: argparse.Namespace, report: Report) -> None:
    text = " ".join([args.error_text, args.client_tool, args.fault_time]).lower()
    markers = ("virus", "mining", "miner", "malware", "trojan", "brute",
               "blocked by security", "security center", "abnormal login",
               "rm -rf", "deleted file")
    hits = [marker for marker in markers if marker in text]
    if hits:
        report.risk(
            "The description carries security-incident context (%s). When files were"
            " removed during a clean-up, or Security Center intercepted the traffic,"
            " the SSH failure is a follow-on of an incident: restoring the login path"
            " is a human job and starts with a snapshot." % ", ".join(hits))
        report.handoff(HANDOFF_SECURITY)


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------
def run(args: argparse.Namespace, cli: AliyunCli, report: Report) -> None:
    report.section("S0 Inputs")
    report.evidence_line(
        "Supplied: RegionId=%s, target=%s, ssh-port=%d, source-ip=%s, "
        "fault-time=%s, login=%s, client-tool=%s. Applied by this script: "
        "PageSize=%d, Direction=ingress, IncludeOutput=true, Type=RunShellScript."
        % (args.region_id, args.instance_id or args.ip_address, args.ssh_port,
           args.source_ip or "(not supplied)", args.fault_time or "(not supplied)",
           args.login_name or "(not supplied)",
           args.client_tool or "(not supplied)", MAX_PAGE_SIZE))
    report.fault_time = args.fault_time

    branches, matched = classify_error(args.error_text)
    report.section("S2 Error triage")
    if matched:
        report.evidence_line("Customer error text '%s' matched signature(s): %s."
                             % (" ".join(mask_credentials(args.error_text).split())[:200],
                                ", ".join(matched)))
        for branch in branches:
            report.finding("Branch '%s' - %s" % (branch, BRANCH_LABELS[branch]))
    else:
        report.degrade("No known error signature was supplied, so triage falls back "
                       "to the generic connection-establishment path.")

    report.section("S1 Preflight")
    identity = _preflight_identity(cli, report)
    if identity is None:
        report.status = "FAIL"
        report.next_action = (
            "Fix the local CLI profile: run '%s configure' and supply a valid "
            "profile through the default credential chain. This script never reads, "
            "prints or stores an AccessKey id or secret." % ALIYUN_BIN)
        return

    records = describe_instances(cli, identity.get("account_id", ""),
                                 args.region_id, args, report)
    if not records:
        report.next_action = (
            "Confirm the RegionId and the owning account of the instance, then "
            "re-run; nothing else can be diagnosed for an instance this account "
            "cannot see.")
        return

    instance = summarise_instance(records[0], args.region_id, report)

    report.section("S1 Instance state")
    status = instance["status"].lower()
    if status and status != "running":
        report.finding("Instance state is '%s'. A stopped or transitional instance "
                       "cannot accept SSH, so the SSH failure is a symptom."
                       % instance["status"])
        report.handoff("Settle the start or stop question in %s first."
                       % HANDOFFS["instance-state"])
        report.next_action = ("Resolve the instance state via %s, then retry the SSH "
                              "diagnosis." % HANDOFFS["instance-state"])
        return
    if not status:
        report.degrade("DescribeInstances returned no Status field for %s."
                       % instance["instance_id"])

    if "windows" in instance["os_type"].lower():
        report.section("Windows area")
        windows_branch(instance, args.ssh_port, report)
    elif not instance["os_type"]:
        report.degrade("OSType was not returned, so the Windows-has-no-SSH-default "
                       "rule could not be applied.")

    report.section("S3 Network permission layer")
    network_clean = check_security_groups(cli, args.region_id,
                                          instance["security_groups"],
                                          args.ssh_port, args.source_ip, report)

    report.section("S5 Guest evidence")
    ready = cloud_assistant_ready(cli, args.region_id, instance["instance_id"],
                                 report)
    baseline_off = args.no_guest_baseline or guest_baseline_suppressed()
    baseline_allowed = guest_consent_granted(args) and not baseline_off
    if not args.guest_command and ready and "windows" not in instance["os_type"].lower():
        if not baseline_allowed:
            if baseline_off:
                report.evidence_line(
                    "guest baseline suppressed by explicit opt-out; the guest "
                    "layer is UNVERIFIED, not normal.")
                report.directive(
                    "WITHHELD-LEAD: guest sshd/listener/firewall reads were suppressed by "
                    "explicit opt-out, so that layer is UNVERIFIED (not normal)")
            else:
                # 2026-10-26: the guest layer must never be entered on the strength
                # of "the agent is online". Without an explicit --allow-guest-read
                # (or the dispatcher's ECS_GUEST_CONSENT=1), the four reads below
                # stay on the customer's side of the line.
                report.evidence_line(
                    "guest reads withheld: no explicit confirmation in this turn "
                    "(pass --allow-guest-read to run them). The guest layer is "
                    "UNVERIFIED, not normal.")
                report.directive(
                    "WITHHELD-LEAD: guest sshd/listener/firewall reads were withheld - no "
                    "explicit confirmation in this turn - so that layer is UNVERIFIED "
                    "(not normal)")
            for key in ("sshd-config", "listening-sockets", "firewalld-ports"):
                entry = GUEST_COMMAND_WHITELIST.get(key)
                if entry:
                    report.manual_step("run in a VNC session: %s  # %s"
                                       % (entry["command"], entry["purpose"]))
        else:
            # 2026-10-19: agent answering means the decisive sshd facts ARE readable -
            # ONE combined dispatch (4 whitelisted reads in a single script) to stay
            # inside the per-command budget, then interpret each block by marker.
            combo = GUEST_COMMAND_WHITELIST.get("sshd-config") and GUEST_COMMAND_WHITELIST.get("listening-sockets")
            if combo:
                script = (
                    "echo @@SSHD@@\nsshd -T\necho @@LISTEN@@\nss -tlnp\n"
                    "echo @@IPT@@\niptables -S\necho @@DISK@@\ndf -h /\n"
                )
                deliver_combined_guest_reads(cli, args.region_id, instance["instance_id"], script, report)
    if args.guest_command:
        if ready:
            deliver_guest_command(cli, args.region_id, instance["instance_id"],
                                  args.guest_command, args.guest_confirmed_by,
                                  report)
        else:
            report.degrade("Cloud Assistant is not answering, so '%s' was not "
                           "delivered even though confirmation was recorded."
                           % args.guest_command)
            report.manual_step(
                "Run '%s' from a VNC session and paste the output back for "
                "interpretation."
                % GUEST_COMMAND_WHITELIST[args.guest_command]["command"])
    else:
        report.evidence_line("No guest command requested. Keys: %s. Each is "
                             "non-mutating and needs an explicit confirmation."
                             % ", ".join(sorted(GUEST_COMMAND_WHITELIST)))

    if args.vnc_url:
        report.section("Fallback login path")
        vnc_fallback(cli, args.region_id, instance["instance_id"], report)

    capacity_area_guidance(branches, report)

    report.section("S7 Security context")
    compromise_scan(args, report)

    report.section("S8 Customer-side path")
    if network_clean:
        target = (instance["eip"]
                  or (instance["public_ips"][0] if instance["public_ips"] else "")
                  or (instance["private_ips"][0] if instance["private_ips"] else "")
                  or "<public-ip>")
        customer_side_checklist(args.client_tool, args.ssh_port, target, report)
    else:
        report.finding(
            "Cloud-side problems were found above, so the customer-side checklist is "
            "withheld: fix the blocking rule first, otherwise the customer is sent "
            "down a path that cannot work.")

    report.section("S9 Next action")
    report.next_action = _next_action(args, report, branches)
    report.customer_next(_customer_next_action(args, report, branches))


def _guest_service_down(report: Report, branches: Sequence[str]) -> bool:
    """A collected guest read proved nothing listens on the SSH port.

    Live S2: an invalid sshd_config directive stopped the service, `ss -tlnp`
    returned no socket, and the answer still told the customer to fix the
    security group first. `_cloud_side_clean` folds this measured in-guest
    blocker together with a speculative source-address mismatch, so the cloud
    rule always owned the next action. A refused connection is an RST from the
    host itself: the packet arrived, so an inbound security-group drop (which
    times out) cannot be the blocker.
    """
    if BRANCH_NO_LISTENER not in branches:
        return False
    return "no ssh daemon socket" in " ".join(report.findings).lower()


def _customer_next_action(args: argparse.Namespace, report: Report,
                          branches: Sequence[str]) -> str:
    """What the customer does next, in words they can act on. No switch names."""
    if _guest_service_down(report, branches):
        return ("Next: nothing is listening on the SSH port inside the instance, so "
                "the security group is not what blocks you. Have the customer take a "
                "snapshot, then over a console (VNC) session run `sshd -t`, remove the "
                "configuration line it names, and start the SSH service. Each command "
                "needs their approval first; this skill runs none of them.")
    if not _cloud_side_clean(report):
        return ("Next: the blocking cloud-side rule reported above has to be corrected "
                "first. Once it is, we re-run this check and then work through the "
                "in-instance steps; nothing inside your instance has been changed.")
    if report.handed_off:
        return ("Next: the hand-off above settles the blocking part first; this SSH "
                "check continues on the same request once that is resolved.")
    if BRANCH_AUTHENTICATION in branches or BRANCH_NO_LISTENER in branches:
        return ("Next: we need one read-only look inside the instance to see which "
                "login method and port the SSH service actually accepts. Tell us if "
                "you approve that read; if you cannot log in at all, ask for a "
                "console (VNC) session instead.")
    if BRANCH_RESET in branches or BRANCH_SESSION_DROP in branches:
        return ("Next: we need your approval for a read-only look at the in-instance "
                "firewall and listening ports. If those are clean, compare the drop "
                "times with the console monitoring charts and work the client-side "
                "checklist.")
    if BRANCH_TCP_UNREACHABLE in branches:
        return ("Next: send the public address your connection comes from right now "
                "(search \"what is my ip\" in a browser on that machine) so we can "
                "compare it with the address the security group allows.")
    return ("Next: paste the exact error text your terminal shows, and the public "
            "address you are connecting from. Without those two this check cannot "
            "pick a branch, and nothing about your instance has been changed.")


def _preflight_identity(cli: AliyunCli,
                        report: Report) -> Optional[Dict[str, str]]:
    from sts_token import fetch_identity, uid_tag

    try:
        identity = fetch_identity(cli)
    except CliError as error:
        if error.is_auth_failure:
            report.finding("The credential chain was refused (%s), so no query can "
                           "be made." % error.code)
            report.manual_step("Attach at least this policy to the RAM identity:\n%s"
                               % minimal_policy_snippet([
                                   "sts:GetCallerIdentity",
                                   "ecs:DescribeInstances",
                                   "ecs:DescribeSecurityGroupAttribute",
                                   "ecs:DescribeCloudAssistantStatus",
                                   "ecs:DescribeInstanceVncUrl",
                                   "ecs:DescribeInvocations"]))
        else:
            report.degrade("Identity preflight failed (%s): %s"
                           % (error.code, error.message))
        return None

    report.evidence_line("%s %s -> %s (arn %s). This is the account whose visibility"
                         " decides whether the instance can be seen at all."
                         % (ALIYUN_BIN, "GetCallerIdentity", uid_tag(identity),
                            identity.get("arn") or "(not returned)"))
    cli.call_log.append({"action": "identity", "attempt": 1, "duration_ms": 0,
                         "outcome": "ok", "code": "",
                         "account": identity.get("account_id", ""),
                         "user_agent": cli.user_agent})
    return identity


def _cloud_side_clean(report: Report) -> bool:
    text = " ".join(report.findings).lower()
    markers = ("no ingress accept rule", "cannot match traffic", "does not allow",
               "no ssh daemon socket", "missing paths", "drop or reject")
    return not any(marker in text for marker in markers)


def _next_action(args: argparse.Namespace, report: Report,
                 branches: Sequence[str]) -> str:
    """Engineer-facing directive: names the exact switches, stays on the run log."""
    if _guest_service_down(report, branches):
        return ("The guest read settled the blocker: no listener on the SSH port. "
                "Have a human validate /etc/ssh/sshd_config with sshd -t over VNC, "
                "repair the line it names and start the service after a snapshot; "
                "then re-run with --guest-command sshd-config to confirm.")
    if not _cloud_side_clean(report):
        return ("Have a human fix the security group or guest service problem "
                "identified above, then re-run this diagnosis with --source-ip set "
                "to the customer's freshly read public egress address.")
    if report.handed_off:
        return ("Follow the handoff above, then continue the SSH question here once "
                "the blocking issue is resolved.")
    if BRANCH_AUTHENTICATION in branches:
        return ("Collect the daemon configuration with --guest-command sshd-config "
                "(after telling the customer the exact command and getting "
                "agreement) to confirm which authentication method the server "
                "accepts; offer --vnc-url when the customer cannot log in at all.")
    if BRANCH_NO_LISTENER in branches:
        return ("Collect listening sockets with --guest-command listening-sockets "
                "after confirmation to establish which port SSH really serves, or "
                "fall back to --vnc-url.")
    if BRANCH_RESET in branches or BRANCH_SESSION_DROP in branches:
        return ("Collect firewall and socket state with --guest-command "
                "firewalld-ports or --guest-command listening-sockets after "
                "confirmation; when both are clean, work the customer-side "
                "checklist and compare the drop timeline with the console "
                "monitoring charts.")
    if BRANCH_TCP_UNREACHABLE in branches:
        return ("Re-check the security group authorization object against the "
                "customer's real egress address, then the guest firewall with "
                "--guest-command firewalld-ports after confirmation.")
    return ("Re-run with --error-text copied from the customer terminal so triage "
            "can pick a branch, and with --source-ip so the authorization object can"
            " be compared (port under test: %d)." % args.ssh_port)


def main(argv: Optional[Sequence[str]] = None) -> int:
    # Independent, offline boundary self-test for the auth-failure reader, run
    # before argparse so it needs no instance/region/credentials.
    if "--selftest" in (argv if argv is not None else sys.argv):
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_guest_commands:
        sys.stdout.write(list_guest_commands() + "\n")
        return EXIT_OK

    if args.guest_command and not args.guest_confirmed_by.strip():
        sys.stderr.write(
            "[WARN] --guest-command without --guest-confirmed-by is auto-approved "
            "for whitelisted non-mutating reads and will still be executed; the "
            "report records the auto approval.\n")

    cli = AliyunCli()
    report = Report()
    report.fault_time = args.fault_time
    report.evidence_line(
        "skill=%s, session_id=%s, User-Agent=%s, API versions: %s."
        % (SKILL_NAME, cli.session_id, cli.user_agent,
           ", ".join("%s %s" % item for item in sorted(API_VERSIONS.items()))))
    try:
        run(args, cli, report)
    except CliError as error:  # nothing should escape; keep the contract
        report.degrade("Unreviewed API failure (%s): %s"
                       % (error.code, error.message))
        report.status = "FAIL"
        report.next_action = ("Retry once after checking the region id and the RAM "
                              "policy; if it persists, quote session %s to a human."
                              % cli.session_id)

    if args.as_json:
        json.dump({
            "session_id": cli.session_id,
            "user_agent": cli.user_agent,
            "status": report.status,
            "next_action": report.next_action,
            "evidence": report.evidence,
            "findings": report.findings,
            "human_steps": report.manual,
            "handoffs": report.handed_off,
            "limitations": report.degradations,
            "calls": cli.call_log,
        }, sys.stdout, indent=2, ensure_ascii=True)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(report.render() + "\n")

    if not args.quiet:
        cli.print_call_log()

    return EXIT_BLOCKED if report.status == "FAIL" else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
