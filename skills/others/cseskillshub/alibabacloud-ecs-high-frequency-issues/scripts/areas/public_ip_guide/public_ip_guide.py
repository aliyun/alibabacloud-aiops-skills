#!/usr/bin/env python3
"""Single entry point of the public IP / EIP guide.

Collects the address facts with non-mutating queries, then prints the guidance
branch that matches them. The agent runs this file and never assembles CLI
calls by hand.

    python3 scripts/areas/public_ip_guide/public_ip_guide.py --intent change-ip \
        --instance-id i-2ze000000000000000 --region cn-hangzhou

Every intent ends with ``STATUS: OK|DEGRADED|FAIL`` and ``NEXT_ACTION:``. This
script calls no action that changes a resource or a bill: the change steps it
prints are console guidance the customer performs.
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import os
import sys

import sts_token
from _cli import CliError, call, new_session_id
from _constants import (
    ACTION_DESCRIBE_EIP_ADDRESSES,
    ACTION_DESCRIBE_INSTANCES,
    ACTION_DESCRIBE_INSTANCE_STATUS,
    BILLING_MODEL,
    BILLING_TAIL_WARNING,
    COMMON_REGIONS,
    CONSULT_FACTS,
    CONSULT_METHODS,
    COUNTER_EXAMPLES,
    DOC_ASSOCIATE_EIP,
    DOC_CHANGE_BANDWIDTH_BILLING,
    DOC_CONNECT_TO_INSTANCE,
    DOC_CROSS_ACCOUNT_TRANSFER,
    DOC_MANAGE_ENI,
    DOC_MODIFY_EIP_BANDWIDTH,
    DOC_PUBLIC_BANDWIDTH,
    DOC_RELEASE_INSTANCE,
    DOC_SECURITY_GROUP_GUIDE,
    EIP_BANDWIDTH_OPTIONS,
    EIP_CONSOLE_URL,
    FIVE_STEP_FLOW,
    GUEST_SIDE_NOTE,
    HANDOFF_RULES,
    INTENTS,
    INTENT_NEXT_ACTION,
    MAX_SCAN_REGIONS,
    MULTI_IP_RULES,
    PAGE_SIZE,
    PRODUCT_ECS,
    PRODUCT_VPC,
    RELEASED_ADDRESS_RULES,
    RENEW_CONSOLE_URL,
    SKILL_NAME,
    THREE_NOTICES,
    TRANSFER_RULES,
    UNIQUE_ADDRESS_NOTE,
    WRONG_SHORTCUTS,
)

TITLE = "ECS public IP and EIP guide"
NO_HANDLE_HINT = (
    "no resource handle was given, so nothing was queried: pass --instance-id, --public-ip "
    "or --allocation-id together with --region"
)
ADDRESS_TYPE_LABEL = {
    "fixed": "fixed public IP (owned by the instance, billed with it)",
    "eip": "Elastic IP Address (independent resource, billed on its own)",
    "none": "no public address returned",
    "unknown": "not established",
}


# --------------------------------------------------------------------------- #
# report plumbing
# --------------------------------------------------------------------------- #
class Report:
    """Collected output lines, evidence values, and the degradation marks."""

    def __init__(self, session_id):
        self.session_id = session_id
        self.lines = []
        self.evidence = {}
        self.warnings = []
        self.failed = False

    def line(self, text=""):
        self.lines.append(text)

    def section(self, name):
        self.line("")
        self.line("-- {0} --".format(name))

    def bullet(self, text):
        self.line("  {0}".format(text))

    def warn(self, label, error):
        self.warnings.append("{0}: {1}".format(label, error))
        sys.stderr.write("[WARN] {0}: {1}\n".format(label, error))

    def status(self):
        if self.failed:
            return "FAIL"
        return "DEGRADED" if self.warnings else "OK"

    def render(self):
        return "\n".join(self.lines)


def _dig(node, *keys, **kwargs):
    default = kwargs.get("default")
    current = node
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def _as_list(value):
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def _only(**kwargs):
    """Keep the keyword only when it carries a value, so defaults stay untouched."""
    return dict((key, value) for key, value in kwargs.items() if value)


# --------------------------------------------------------------------------- #
# queries
# --------------------------------------------------------------------------- #
def describe_instances(region, session_id, instance_id=None, public_ip=None, timeout=None):
    params = {"RegionId": region, "PageSize": PAGE_SIZE}
    # DescribeInstances takes both of these as JSON array strings, not bare values.
    if instance_id:
        params["InstanceIds"] = [instance_id]
    if public_ip:
        params["PublicIpAddresses"] = [public_ip]
    body = call(PRODUCT_ECS, ACTION_DESCRIBE_INSTANCES, params, session_id=session_id,
                **_only(timeout=timeout))
    rows = _dig(body, "Instances", "Instance", default=[])
    return [_normalise_instance(item) for item in _as_list(rows)]


def describe_instance_status(region, session_id, instance_id, timeout=None):
    body = call(PRODUCT_ECS, ACTION_DESCRIBE_INSTANCE_STATUS,
                {"RegionId": region, "InstanceId.1": instance_id, "PageSize": PAGE_SIZE},
                session_id=session_id, **_only(timeout=timeout))
    rows = _as_list(_dig(body, "InstanceStatuses", "InstanceStatus", default=[]))
    for item in rows:
        if item.get("InstanceId") == instance_id:
            return item.get("Status") or ""
    return rows[0].get("Status", "") if rows else ""


def describe_eips(region, session_id, allocation_id=None, eip_address=None,
                  instance_id=None, status=None, timeout=None):
    params = {"RegionId": region, "PageSize": PAGE_SIZE}
    if allocation_id:
        params["AllocationId"] = allocation_id
    if eip_address:
        params["EipAddress"] = eip_address
    if instance_id:
        params["AssociatedInstanceId"] = instance_id
        params["AssociatedInstanceType"] = "EcsInstance"
    if status:
        params["Status"] = status
    body = call(PRODUCT_VPC, ACTION_DESCRIBE_EIP_ADDRESSES, params, session_id=session_id,
                **_only(timeout=timeout))
    rows = _dig(body, "EipAddresses", "EipAddress", default=[])
    return [_normalise_eip(item) for item in _as_list(rows)]


def _normalise_instance(item):
    return {
        "instance_id": item.get("InstanceId", ""),
        "name": item.get("InstanceName", ""),
        "status": item.get("Status", ""),
        "region_id": item.get("RegionId", ""),
        "zone_id": item.get("ZoneId", ""),
        "network_type": item.get("InstanceNetworkType", ""),
        "instance_charge_type": item.get("InstanceChargeType", ""),
        "internet_charge_type": item.get("InternetChargeType", ""),
        "bandwidth_out": item.get("InternetMaxBandwidthOut", ""),
        "public_ips": [ip for ip in _as_list(_dig(item, "PublicIpAddress", "IpAddress", default=[])) if ip],
        "eip": {
            "ip_address": _dig(item, "EipAddress", "IpAddress", default="") or "",
            "allocation_id": _dig(item, "EipAddress", "AllocationId", default="") or "",
            "bandwidth": _dig(item, "EipAddress", "Bandwidth", default="") or "",
            "internet_charge_type": _dig(item, "EipAddress", "InternetChargeType", default="") or "",
        },
        "inner_ips": [ip for ip in _as_list(_dig(item, "InnerIpAddress", "IpAddress", default=[])) if ip],
        "private_ips": [
            ip for ip in
            _as_list(_dig(item, "VpcAttributes", "PrivateIpAddress", "IpAddress", default=[])) if ip
        ],
        "vpc_id": _dig(item, "VpcAttributes", "VpcId", default="") or "",
        "vswitch_id": _dig(item, "VpcAttributes", "VSwitchId", default="") or "",
    }


def _normalise_eip(item):
    return {
        "allocation_id": item.get("AllocationId", ""),
        "ip_address": item.get("IpAddress", ""),
        "status": item.get("Status", ""),
        "bandwidth": item.get("Bandwidth", ""),
        "internet_charge_type": item.get("InternetChargeType", ""),
        "charge_type": item.get("ChargeType", ""),
        "bound_instance_id": item.get("InstanceId", "") or item.get("AssociatedInstanceId", "") or "",
        "private_ip_address": item.get("PrivateIpAddress", ""),
        "region_id": item.get("RegionId", ""),
        "name": item.get("Name", ""),
    }


def classify(instance):
    """fixed | eip | none, from whichever address fields came back."""
    if not instance:
        return "unknown"
    if instance["eip"]["ip_address"] or instance["eip"]["allocation_id"]:
        return "eip"
    if instance["public_ips"]:
        return "fixed"
    return "none"


# --------------------------------------------------------------------------- #
# collection
# --------------------------------------------------------------------------- #
class Facts:
    """What the guidance branches quote from; never filled in from memory."""

    def __init__(self):
        self.region = ""
        self.region_source = ""
        self.regions_searched = []
        self.instance = None
        self.instance_status = ""
        self.eips = []
        self.unbound_eips = []
        self.identity_tag = "account unknown"
        self.old_address = ""
        self.allocation_id = ""
        self.symptom = ""
        self.timeout = None
        self.missing_region = False
        self.has_handle = False


def region_plan(args):
    if args.region:
        return [args.region]
    if args.scan_regions:
        limit = args.max_regions or MAX_SCAN_REGIONS
        return list(COMMON_REGIONS[:limit])
    return []


def probe(region, args, session_id):
    """Look the handles up in one region and return ``(instance, eips)``.

    Raises :class:`CliError` when a query fails so the caller can degrade.
    """
    instance = None
    eips = []
    if args.instance_id or args.public_ip:
        rows = describe_instances(region, session_id, instance_id=args.instance_id,
                                 public_ip=args.public_ip, timeout=args.timeout)
        instance = rows[0] if rows else None
        if instance and instance["eip"]["allocation_id"]:
            eips = describe_eips(region, session_id,
                                 allocation_id=instance["eip"]["allocation_id"],
                                 timeout=args.timeout)
    if args.allocation_id:
        eips = describe_eips(region, session_id, allocation_id=args.allocation_id,
                             timeout=args.timeout)
        if eips and not instance and eips[0]["bound_instance_id"]:
            rows = describe_instances(region, session_id, instance_id=eips[0]["bound_instance_id"],
                                      timeout=args.timeout)
            instance = rows[0] if rows else None
    return instance, eips


def collect(args, session_id, report):
    facts = Facts()
    try:
        facts.identity_tag = sts_token.get_caller_identity(session_id)["tag"]
    except CliError as error:
        report.warn("identity query", error)

    facts.has_handle = bool(args.instance_id or args.public_ip or args.allocation_id)
    if not facts.has_handle:
        return facts

    regions = region_plan(args)
    if not regions:
        report.failed = True
        facts.missing_region = True
        return facts

    for region in regions:
        try:
            instance, eips = probe(region, args, session_id)
        except CliError as error:
            report.warn("query in " + region, error)
            if error.is_permission or error.is_credential:
                report.failed = True
                break
            continue
        if instance or eips:
            facts.instance, facts.eips = instance, eips
            facts.region = region
            facts.region_source = "provided" if args.region else "located by scanning regions"
            return facts
        if not args.region:
            facts.regions_searched.append(region)

    if args.region:
        facts.region = args.region
        facts.region_source = "provided"
    return facts


def read_operability(report, facts, session_id):
    """Instance status is the pre-change gate: a locked or stopped host blocks the path."""
    if not (facts.region and facts.instance and facts.instance["instance_id"]):
        return
    try:
        facts.instance_status = describe_instance_status(facts.region, session_id,
                                                        facts.instance["instance_id"],
                                                        timeout=facts.timeout)
    except CliError as error:
        report.warn("instance status query", error)


# --------------------------------------------------------------------------- #
# shared blocks
# --------------------------------------------------------------------------- #
def state_section(report, facts):
    report.section("current state")
    report.bullet("{0} | session {1}".format(facts.identity_tag, report.session_id))
    if facts.region:
        report.bullet("region {0} ({1})".format(facts.region, facts.region_source or "provided"))
    if facts.regions_searched:
        report.bullet("scanned without a match ({0}): {1}".format(
            len(facts.regions_searched), ", ".join(facts.regions_searched)))
    if not (facts.instance or facts.eips):
        if facts.missing_region:
            report.bullet("No state was queried: the region was not supplied.")
            return
        report.bullet(NO_HANDLE_HINT if not facts.has_handle else
                      "nothing matched the handle in {0}".format(
                          facts.region or "the searched regions"))
        report.bullet("A wrong region is the most common reason: the same account held addresses "
                      "in cn-zhangjiakou, us-west-1 and cn-wulanchabu in the recorded cases.")
        report.bullet("EIP list of the region: {0}".format(
            EIP_CONSOLE_URL.format(region_id=facts.region or "<region-id>")))
        return
    kind = classify(facts.instance)
    if facts.instance:
        report.bullet("instance {0} status={1} lifecycle={2} network={3}".format(
            facts.instance["instance_id"] or facts.instance["name"] or "-",
            facts.instance_status or facts.instance["status"] or "unknown",
            facts.instance["instance_charge_type"] or "unknown",
            facts.instance["network_type"] or "unknown",
        ))
        report.bullet("address type: {0}".format(ADDRESS_TYPE_LABEL[kind]))
        if facts.instance["public_ips"]:
            report.bullet("public addresses returned: {0}".format(
                ", ".join(facts.instance["public_ips"])))
        if facts.instance["eip"]["ip_address"]:
            report.bullet("bound EIP {0} allocation={1} bandwidth={2} EIP billing={3}".format(
                facts.instance["eip"]["ip_address"],
                facts.instance["eip"]["allocation_id"] or "-",
                facts.instance["eip"]["bandwidth"] or "-",
                facts.instance["eip"]["internet_charge_type"] or "-",
            ))
        report.bullet("instance public bandwidth {0} Mbps, bandwidth billing {1}".format(
            facts.instance["bandwidth_out"] if facts.instance["bandwidth_out"] != "" else "unknown",
            facts.instance["internet_charge_type"] or "unknown",
        ))
        private = facts.instance["private_ips"] or facts.instance["inner_ips"]
        report.bullet("private address inside the instance: {0}".format(", ".join(private) or "none returned"))
    for eip in facts.eips:
        report.bullet("EIP record {0} ip={1} status={2} bandwidth={3} instance charge={4} "
                      "traffic charge={5} bound-to={6}".format(
                          eip["allocation_id"], eip["ip_address"] or "-", eip["status"] or "-",
                          eip["bandwidth"] or "-", eip["charge_type"] or "-",
                          eip["internet_charge_type"] or "-", eip["bound_instance_id"] or "unbound"))
    report.evidence["address_type"] = kind


def human_fallback(report):
    report.section("human boundary")
    report.bullet("Everything that spends money or releases something is clicked by the customer in "
                  "the console, where the estimated fee is shown before confirmation. This guide "
                  "computes no price and runs no change.")
    report.bullet("Console entries: EIP list {0} | renewal page {1}".format(
        EIP_CONSOLE_URL.format(region_id="<region-id>"), RENEW_CONSOLE_URL))


def steps_for(kind):
    """The change path, renumbered: all five steps for a fixed IP, the last three for an EIP."""
    raw = list(FIVE_STEP_FLOW) if kind == "fixed" else list(FIVE_STEP_FLOW[2:])
    total = len(raw)
    built = []
    for index, (title, text, url) in enumerate(raw, start=1):
        label = title.split(" - ", 1)[-1]
        built.append(("step {0}/{1} - {2}".format(index, total, label), text, url))
    return built


# --------------------------------------------------------------------------- #
# intent branches
# --------------------------------------------------------------------------- #
def branch_change_ip(report, facts):
    kind = classify(facts.instance)
    report.section("change decision")
    if kind == "unknown":
        report.bullet("The address type could not be established, so no change path is asserted. "
                      "Ask for the instance id and region, or rerun with --scan-regions.")
        human_fallback(report)
        return
    if kind == "none":
        report.bullet("There is no public address on this instance, so there is nothing to replace "
                      "yet: see the ip-missing branch.")
        human_fallback(report)
        return
    if kind == "fixed":
        report.bullet("A fixed public IP cannot be swapped directly; the supported route goes "
                      "through an EIP.")
    else:
        report.bullet("The address is already an EIP, so no conversion is needed: unbind, allocate, "
                      "bind. Review the bandwidth billing switch first if the instance is on fixed "
                      "bandwidth: " + DOC_CHANGE_BANDWIDTH_BILLING)
    report.section("change path, in order")
    for label, text, url in steps_for(kind):
        report.bullet(label)
        report.bullet("      " + text)
        report.bullet("      doc: " + url)
    report.section("three notices, never omitted")
    for notice in THREE_NOTICES:
        report.bullet(notice)
    report.section("shortcuts that were tried and did not work")
    for item in WRONG_SHORTCUTS:
        report.bullet("- " + item)
    report.section("address uniqueness and the billing tail")
    report.bullet(UNIQUE_ADDRESS_NOTE)
    report.bullet(BILLING_TAIL_WARNING)
    report.bullet("After the customer acts, rerun this entry point with --intent verify.")
    human_fallback(report)


def branch_add_ip(report, facts):
    report.section("multiple address rules")
    for item in MULTI_IP_RULES:
        report.bullet("- " + item)
    report.section("documentation")
    report.bullet("secondary ENI: " + DOC_MANAGE_ENI)
    report.bullet("bind and unbind an EIP: " + DOC_ASSOCIATE_EIP)
    report.bullet("how an instance gets public traffic: " + DOC_PUBLIC_BANDWIDTH)
    report.bullet("which remote method to use: " + DOC_CONNECT_TO_INSTANCE)
    report.bullet("port allowance: " + DOC_SECURITY_GROUP_GUIDE)
    report.section("instance side")
    report.bullet(GUEST_SIDE_NOTE)
    human_fallback(report)


def branch_retain_ip(report, facts):
    report.section("transfer and retention rules")
    for item in TRANSFER_RULES:
        report.bullet("- " + item)
    report.section("what no query can settle")
    report.bullet("Whether two accounts share one enterprise verification subject is registration "
                  "data, not an ECS field, and it cannot be looked up from here.")
    report.section("documentation")
    report.bullet("transfer procedure: " + DOC_CROSS_ACCOUNT_TRANSFER)
    report.bullet("rebind an EIP afterwards: " + DOC_ASSOCIATE_EIP)
    human_fallback(report)


def branch_billing(report, facts):
    report.section("billing caliber")
    for item in BILLING_MODEL + EIP_BANDWIDTH_OPTIONS:
        report.bullet("- " + item)
    report.section("documentation")
    report.bullet("EIP bandwidth and its billing method: " + DOC_MODIFY_EIP_BANDWIDTH)
    report.bullet("public and private bandwidth: " + DOC_PUBLIC_BANDWIDTH)
    human_fallback(report)


def branch_consult(report, facts):
    report.line("RULE-LEAD: [platform_rule] a public address is a cloud-side field (console "
                "list/details or DescribeInstances / DescribeEipAddresses); the guest NIC shows "
                "private addresses only, so a missing address inside the instance is normal")
    report.section("where the public address is shown")
    for name, detail in CONSULT_METHODS:
        report.bullet("{0}: {1}".format(name, detail))
    report.section("facts that are usually misread")
    for item in CONSULT_FACTS:
        report.bullet("- " + item)
    report.bullet("No read was executed: a how-to question is answered from platform rules, so "
                  "there is no UNVERIFIED layer here.")


def branch_ip_missing(report, facts):
    report.section("is the address still there")
    if facts.instance and classify(facts.instance) != "none":
        report.bullet("An address is still assigned, so a missing address is not the cause: move to "
                      "the access area with --intent triage.")
    elif facts.instance:
        report.bullet("The instance exists but returned no public address.")
        report.bullet("Usual causes: the address was converted and then released, public bandwidth "
                      "is 0 Mbps, or the address sits on a secondary interface.")
    else:
        report.bullet("No instance matched the handle, so the address cannot be confirmed from ECS.")
        report.bullet("Check the EIP list of the region: {0}".format(
            EIP_CONSOLE_URL.format(region_id=facts.region or "<region-id>")))
        report.bullet("Purchase history is on the order management page of the billing console.")
    if facts.eips:
        report.bullet("An EIP record was found, so the address still belongs to this account even "
                      "while unbound: bind it again instead of allocating a new one.")
    report.section("released address rules")
    for item in RELEASED_ADDRESS_RULES:
        report.bullet("- " + item)
    report.section("documentation")
    report.bullet("release and release protection: " + DOC_RELEASE_INSTANCE)
    human_fallback(report)


def branch_verify(report, facts, session_id):
    report.section("read-back after the customer acted")
    if facts.instance:
        current = facts.instance["eip"]["ip_address"] or ", ".join(facts.instance["public_ips"]) or "none"
        report.bullet("current address type: {0}".format(classify(facts.instance)))
        report.bullet("current public address: {0}".format(current))
        if facts.instance_status:
            report.bullet("instance status: {0}".format(facts.instance_status))
        if facts.old_address:
            if current == facts.old_address:
                report.bullet("The address is still the old one, so the change has not taken effect.")
            else:
                report.bullet("The address differs from {0}, so the swap took effect.".format(facts.old_address))
    else:
        report.bullet("The instance was not found in {0}; confirm the region before concluding."
                      .format(facts.region or "<unknown region>"))
    if facts.allocation_id:
        report.section("old EIP")
        if facts.eips:
            for eip in facts.eips:
                report.bullet("allocation {0} still exists with status {1}: it is still billed. "
                              "Bind it or have the customer release it."
                              .format(eip["allocation_id"], eip["status"] or "unknown"))
        else:
            report.bullet("Allocation {0} no longer resolves: the old EIP was released and stopped "
                          "billing.".format(facts.allocation_id))
    if facts.region:
        try:
            facts.unbound_eips = describe_eips(facts.region, session_id, status="Available",
                                               timeout=facts.timeout)
        except CliError as error:
            report.warn("unbound EIP query", error)
        report.section("billing tail candidates in this region")
        if facts.unbound_eips:
            for eip in facts.unbound_eips:
                report.bullet("allocated but unbound: {0} ({1})".format(
                    eip["ip_address"] or "-", eip["allocation_id"]))
            report.bullet("A release is final and is confirmed by the customer, never by this skill.")
        else:
            report.bullet("No unbound EIP returned in this region.")
        report.bullet("EIP list: {0}".format(EIP_CONSOLE_URL.format(region_id=facts.region)))


def match_handoff(symptom):
    """Score the handoff table against free text, strongest area first."""
    text = (symptom or "").lower()
    scored = []
    for rank, (area, keywords, target, wording) in enumerate(HANDOFF_RULES):
        hits = sum(1 for word in keywords if word in text)
        if hits:
            scored.append((-hits, rank, area, target, wording))
    scored.sort()
    return [(area, target, wording) for _neg, _rank, area, target, wording in scored]


def branch_triage(report, facts):
    report.section("counter-example gate")
    matches = match_handoff(facts.symptom)
    if not matches:
        report.bullet("No handoff area matched the wording, so the address area is plausible.")
        report.bullet("Before offering a change: " + COUNTER_EXAMPLES[0])
        return
    for area, target, wording in matches:
        report.bullet("area: {0} -> {1}".format(area, target))
        report.bullet("      " + wording)
    report.section("why an address change is the wrong tool here")
    for item in COUNTER_EXAMPLES:
        report.bullet("- " + item)


# --------------------------------------------------------------------------- #
# entry
# --------------------------------------------------------------------------- #
def build_parser():
    parser = argparse.ArgumentParser(
        prog="public_ip_guide.py",
        description="Collect the public IP and EIP state of an ECS instance with non-mutating "
                    "queries, then print the matching guidance branch. Nothing here changes a "
                    "resource or a bill.",
    )
    parser.add_argument("--intent", required=True, choices=INTENTS, help="which branch to run")
    parser.add_argument("--instance-id", help="ECS instance id, i-...")
    parser.add_argument("--public-ip", help="public IP or EIP address, to look the instance up by")
    parser.add_argument("--allocation-id", help="EIP allocation id, eip-...")
    parser.add_argument("--region", help="RegionId of the resource")
    parser.add_argument("--scan-regions", action="store_true",
                        help="locate the resource across the common regions when --region is absent")
    parser.add_argument("--max-regions", type=int, default=0,
                        help="cap for --scan-regions, default {0}".format(MAX_SCAN_REGIONS))
    parser.add_argument("--symptom", default="", help="free-text symptom for the counter-example gate")
    parser.add_argument("--old-address", default="", help="address that should be gone, for verify")
    parser.add_argument("--timeout", type=int, default=0, help="per-call timeout override, seconds")
    parser.add_argument("--json", action="store_true", help="also emit the evidence block as JSON")
    return parser


def run_consult(args):
    """How-to intent: platform rules only, so no identity check and no cloud read."""
    session_id = new_session_id()
    report = Report(session_id)
    report.line("== {0} ==".format(TITLE))
    report.line("skill {0} | intent consult (platform rules, no cloud read)".format(SKILL_NAME))
    branch_consult(report, None)
    next_action = INTENT_NEXT_ACTION["consult"]
    report.line("")
    report.line("STATUS: {0}".format(report.status()))
    report.line("NEXT_ACTION: " + next_action)
    payload = {
        "skill": SKILL_NAME,
        "session_id": session_id,
        "intent": "consult",
        "methods": [{"name": name, "detail": detail} for name, detail in CONSULT_METHODS],
        "facts": list(CONSULT_FACTS),
        "reads_executed": 0,
        "status": report.status(),
        "next_action": next_action,
    }
    if args.json:
        report.line("")
        report.line(json.dumps(payload, indent=2, sort_keys=True))
    print(report.render())
    return 0


def run(args):
    if args.intent == "consult":
        return run_consult(args)
    session_id = new_session_id()
    report = Report(session_id)
    facts = collect(args, session_id, report)
    facts.old_address = args.old_address
    facts.allocation_id = args.allocation_id
    facts.symptom = args.symptom
    facts.timeout = args.timeout

    report.line("== {0} ==".format(TITLE))
    report.line("skill {0} | intent {1}".format(SKILL_NAME, args.intent))
    if facts.missing_region:
        report.bullet("No query ran: the region is required. Pass --region, or rerun with "
                      "--scan-regions to find the resource.")

    if args.intent == "triage" and not (args.instance_id or args.public_ip or args.allocation_id):
        BRANCHES[args.intent](report, facts, session_id)
    else:
        read_operability(report, facts, session_id)
        state_section(report, facts)
        BRANCHES[args.intent](report, facts, session_id)
        if args.symptom and args.intent != "triage":
            matches = match_handoff(args.symptom)
            if matches:
                report.section("counter-example gate on this wording")
                for area, target, wording in matches:
                    report.bullet("area: {0} -> {1}".format(area, target))
                    report.bullet("      " + wording)

    if report.failed and not facts.region:
        next_action = "Provide --region for the resource, or rerun with --scan-regions."
    else:
        next_action = INTENT_NEXT_ACTION[args.intent]
    report.line("")
    report.line("STATUS: {0}".format(report.status()))
    report.line("NEXT_ACTION: " + next_action)

    payload = {
        "skill": SKILL_NAME,
        "session_id": session_id,
        "intent": args.intent,
        "region": facts.region,
        "identity": facts.identity_tag,
        "address_type": classify(facts.instance),
        "instance": facts.instance,
        "eips": facts.eips,
        "unbound_eips": facts.unbound_eips,
        "warnings": report.warnings,
        "status": report.status(),
        "next_action": next_action,
    }
    if args.json:
        report.line("")
        report.line(json.dumps(payload, indent=2, sort_keys=True))
    print(report.render())
    return 1 if report.status() == "FAIL" else 0


BRANCHES = {
    "change-ip": lambda report, facts, session_id: branch_change_ip(report, facts),
    "add-ip": lambda report, facts, session_id: branch_add_ip(report, facts),
    "retain-ip": lambda report, facts, session_id: branch_retain_ip(report, facts),
    "billing": lambda report, facts, session_id: branch_billing(report, facts),
    "ip-missing": lambda report, facts, session_id: branch_ip_missing(report, facts),
    "verify": lambda report, facts, session_id: branch_verify(report, facts, session_id),
    "triage": lambda report, facts, session_id: branch_triage(report, facts),
}


def _run_selftest():
    """Offline regression lock: pure core plus stubbed-call integration.

    Shapes follow the live DescribeInstances/DescribeEipAddresses payloads
    captured against the evaluation role (empty strings, dict-wrapped lists,
    TopLevel TotalCount); no network call is made here.
    """
    import argparse
    import contextlib
    import io

    results = {"pass": 0, "fail": 0}

    def check(name, got, want):
        if got == want:
            results["pass"] += 1
        else:
            results["fail"] += 1
            print("FAIL {0}: got {1!r} want {2!r}".format(name, got, want))

    original_call = globals()["call"]

    class Stub:
        """Records every call and replays canned payloads keyed by action."""

        def __init__(self, routes=None):
            self.log = []
            self.routes = routes or {}

        def __call__(self, product, action, params=None, session_id=None, timeout=None):
            self.log.append((product, action, dict(params or {}), timeout))
            if action in self.routes:
                return self.routes[action]
            raise CliError(product, action, "UnexpectedAction", action)

    # ----- pure helpers -------------------------------------------------- #
    check("dig_found", _dig({"a": {"b": 1}}, "a", "b"), 1)
    check("dig_miss", _dig({"a": {"b": 1}}, "a", "c", default="D"), "D")
    check("dig_none_mid", _dig({"a": None}, "a", "b", default="D"), "D")
    check("dig_nondict", _dig("str", "a", default="D"), "D")
    check("as_list_empty_str", _as_list(""), [])
    check("as_list_none", _as_list(None), [])
    check("as_list_single", _as_list("x"), ["x"])
    check("as_list_passthrough", _as_list([1, 2]), [1, 2])
    check("only_drops_falsy", _only(timeout=None, a=0, b="", c="s"), {"c": "s"})

    # ----- normalisation on live-captured shapes -------------------------- #
    # A real row of the evaluation account: no public IP, EIP block present
    # but every field an empty string.
    bare_row = {
        "InstanceId": "i-bp1example724c8af2a1", "InstanceName": "worker-k8s",
        "Status": "Running", "RegionId": "cn-hangzhou", "ZoneId": "cn-hangzhou-k",
        "InstanceNetworkType": "vpc", "InstanceChargeType": "PostPaid",
        "InternetChargeType": "PayByTraffic", "InternetMaxBandwidthOut": 0,
        "PublicIpAddress": {"IpAddress": []},
        "EipAddress": {"AllocationId": "", "InternetChargeType": "", "IpAddress": ""},
        "InnerIpAddress": {"IpAddress": []},
        "VpcAttributes": {"VpcId": "vpc-1", "VSwitchId": "vsw-1",
                          "PrivateIpAddress": {"IpAddress": ["10.111.214.109"]}},
    }
    n = _normalise_instance(bare_row)
    check("norm_bare_public_ips", n["public_ips"], [])
    check("norm_bare_eip_ip", n["eip"]["ip_address"], "")
    check("norm_bare_eip_alloc", n["eip"]["allocation_id"], "")
    check("norm_bare_private", n["private_ips"], ["10.111.214.109"])
    check("norm_bare_vpc", (n["vpc_id"], n["vswitch_id"]), ("vpc-1", "vsw-1"))
    check("classify_bare", classify(n), "none")

    eip_row = dict(bare_row)
    eip_row["EipAddress"] = {"AllocationId": "eip-bp1abc", "IpAddress": "47.98.1.2",
                              "Bandwidth": "5", "InternetChargeType": "PayByBandwidth"}
    ne = _normalise_instance(eip_row)
    check("classify_eip", classify(ne), "eip")
    check("norm_eip_bandwidth", ne["eip"]["bandwidth"], "5")

    fixed_row = dict(bare_row)
    fixed_row["PublicIpAddress"] = {"IpAddress": ["121.41.1.1"]}
    check("classify_fixed", classify(_normalise_instance(fixed_row)), "fixed")
    # EIP wins over a fixed address when both blocks came back
    both_row = dict(eip_row)
    both_row["PublicIpAddress"] = {"IpAddress": ["121.41.1.1"]}
    check("classify_eip_wins", classify(_normalise_instance(both_row)), "eip")
    check("classify_none_inst", classify(None), "unknown")
    # classify only ever sees _normalise_instance output; an empty raw row must
    # normalise into the "none" shape rather than raise.
    check("classify_empty_raw_row", classify(_normalise_instance({})), "none")

    eip_live = {"AllocationId": "eip-bp1x", "IpAddress": "8.135.1.1", "Status": "InUse",
                "Bandwidth": "100", "InternetChargeType": "PayByTraffic",
                "ChargeType": "PostPaid", "InstanceId": "i-bp1y",
                "PrivateIpAddress": "10.0.0.5", "RegionId": "cn-hangzhou", "Name": ""}
    check("norm_eip_bound", _normalise_eip(eip_live)["bound_instance_id"], "i-bp1y")
    assoc_row = dict(eip_live)
    del assoc_row["InstanceId"]
    assoc_row["AssociatedInstanceId"] = "i-bp1z"
    check("norm_eip_assoc_fallback", _normalise_eip(assoc_row)["bound_instance_id"], "i-bp1z")
    check("norm_eip_unbound", _normalise_eip({"AllocationId": "eip-bp1u"})["bound_instance_id"], "")

    # ----- query wrappers -------------------------------------------------- #
    stub = Stub({"DescribeInstances": {"Instances": {"Instance": [bare_row]}},
                 "DescribeInstanceStatus": {"InstanceStatuses": {"InstanceStatus": [
                     {"InstanceId": "i-bp1example724c8af2a1", "Status": "Running"}]}},
                 "DescribeEipAddresses": {"EipAddresses": {"EipAddress": [eip_live]}}})
    globals()["call"] = stub
    try:
        rows = describe_instances("cn-hangzhou", "s", instance_id="i-bp1example724c8af2a1",
                                  timeout=7)
        check("di_params", stub.log[-1][:2], ("ecs", "DescribeInstances"))
        check("di_instanceids", stub.log[-1][2]["InstanceIds"], ["i-bp1example724c8af2a1"])
        check("di_timeout_forwarded", stub.log[-1][3], 7)
        check("di_rows", [r["instance_id"] for r in rows], ["i-bp1example724c8af2a1"])

        describe_instances("cn-hangzhou", "s", public_ip="1.2.3.4")
        check("di_publicips", stub.log[-1][2]["PublicIpAddresses"], ["1.2.3.4"])
        check("di_no_instanceids", "InstanceIds" in stub.log[-1][2], False)
        describe_instances("cn-hangzhou", "s")
        check("di_no_handle_params",
              ("InstanceIds" in stub.log[-1][2], "PublicIpAddresses" in stub.log[-1][2]),
              (False, False))

        st = describe_instance_status("cn-hangzhou", "s", "i-bp1example724c8af2a1")
        check("dis_status", st, "Running")
        check("dis_param", stub.log[-1][2]["InstanceId.1"], "i-bp1example724c8af2a1")
        stub.routes["DescribeInstanceStatus"] = {"InstanceStatuses": {"InstanceStatus": [
            {"InstanceId": "i-other", "Status": "Stopped"}]}}
        check("dis_fallback_first_row",
              describe_instance_status("cn-hangzhou", "s", "i-missing"), "Stopped")
        stub.routes["DescribeInstanceStatus"] = {"InstanceStatuses": {"InstanceStatus": []}}
        check("dis_empty", describe_instance_status("cn-hangzhou", "s", "i-missing"), "")

        describe_eips("cn-hangzhou", "s", instance_id="i-bp1y")
        check("eip_assoc_params",
              (stub.log[-1][2]["AssociatedInstanceId"], stub.log[-1][2]["AssociatedInstanceType"]),
              ("i-bp1y", "EcsInstance"))
        describe_eips("cn-hangzhou", "s", status="Available")
        check("eip_status_param", stub.log[-1][2]["Status"], "Available")
        describe_eips("cn-hangzhou", "s", allocation_id="eip-bp1x", eip_address="8.135.1.1")
        check("eip_id_params",
              (stub.log[-1][2]["AllocationId"], stub.log[-1][2]["EipAddress"]),
              ("eip-bp1x", "8.135.1.1"))
    finally:
        globals()["call"] = original_call

    # ----- region plan / probe ------------------------------------------- #
    A = argparse.Namespace
    check("rp_region", region_plan(A(region="cn-hangzhou", scan_regions=False, max_regions=0)),
          ["cn-hangzhou"])
    check("rp_scan_default_len",
          len(region_plan(A(region="", scan_regions=True, max_regions=0))), MAX_SCAN_REGIONS)
    check("rp_scan_cap3", region_plan(A(region="", scan_regions=True, max_regions=3)),
          list(COMMON_REGIONS[:3]))
    check("rp_none", region_plan(A(region="", scan_regions=False, max_regions=0)), [])

    stub = Stub({"DescribeInstances": {"Instances": {"Instance": [eip_row]}},
                 "DescribeEipAddresses": {"EipAddresses": {"EipAddress": [eip_live]}}})
    globals()["call"] = stub
    try:
        args = A(instance_id="i-bp1example724c8af2a1", public_ip=None, allocation_id=None,
                 timeout=None)
        inst, eips = probe("cn-hangzhou", args, "s")
        check("probe_inst", inst["instance_id"], "i-bp1example724c8af2a1")
        check("probe_eip_enrich", [e["allocation_id"] for e in eips], ["eip-bp1x"])
        check("probe_enrich_param", stub.log[-1][2].get("AllocationId"), "eip-bp1abc")

        args = A(instance_id=None, public_ip=None, allocation_id="eip-bp1x", timeout=None)
        inst, eips = probe("cn-hangzhou", args, "s")
        check("probe_alloc_only_reverse", inst["instance_id"], "i-bp1example724c8af2a1")

        stub.routes["DescribeEipAddresses"] = {"EipAddresses": {"EipAddress": [
            dict(eip_live, InstanceId="")]}}
        log_before = len(stub.log)
        inst, eips = probe("cn-hangzhou", args, "s")
        check("probe_alloc_unbound_no_inst", inst, None)
        new_actions = [a for _p, a, _x, _t in stub.log[log_before:]]
        check("probe_unbound_skips_ecs", "DescribeInstances" in new_actions, False)
    finally:
        globals()["call"] = original_call

    # ----- guidance core --------------------------------------------------- #
    check("handoff_filing", [m[0] for m in match_handoff("443 rst beian blocked")],
          ["filing interception on port 443"])
    multi = match_handoff("ping timeout packet loss, ssh refused on port 22")
    check("handoff_ranked_by_hits", multi[0][0], "public path quality")
    check("handoff_all_areas", len(multi), 4)
    check("handoff_no_match", match_handoff("hello world"), [])
    check("handoff_empty", match_handoff(""), [])
    check("handoff_casefold",
          [m[0] for m in match_handoff("SSH TIMEOUT on 22")],
          [m[0] for m in match_handoff("ssh timeout on 22")])

    fsteps = steps_for("fixed")
    check("steps_fixed_count", len(fsteps), 5)
    check("steps_fixed_first", fsteps[0][0], "step 1/5 - switch the public bandwidth billing method")
    check("steps_fixed_last", fsteps[-1][0], "step 5/5 - bind the new EIP to the instance")
    esteps = steps_for("eip")
    check("steps_eip_count", len(esteps), 3)
    check("steps_eip_renumbered", [s[0] for s in esteps],
          ["step 1/3 - unbind the EIP", "step 2/3 - allocate a new EIP",
           "step 3/3 - bind the new EIP to the instance"])
    check("steps_urls_present", all(s[2].startswith("https://") for s in fsteps), True)

    # ----- state section rendering ----------------------------------------- #
    def make_facts(**over):
        facts = Facts()
        for key, value in over.items():
            setattr(facts, key, value)
        return facts

    rep = Report("sess1")
    state_section(rep, make_facts(identity_tag="account ****3456", region="cn-hangzhou",
                                  region_source="provided", instance=ne, instance_status="Running",
                                  eips=[_normalise_eip(eip_live)]))
    text = rep.render()
    check("state_shows_account", "account ****3456 | session sess1" in text, True)
    check("state_shows_running", "status=Running" in text, True)
    check("state_eip_label", "address type: Elastic IP Address" in text, True)
    check("state_bound_eip_line", "bound EIP 47.98.1.2 allocation=eip-bp1abc bandwidth=5" in text, True)
    check("state_eip_record", "EIP record eip-bp1x ip=8.135.1.1 status=InUse" in text, True)
    check("state_evidence_kind", rep.evidence.get("address_type"), "eip")

    rep = Report("s2")
    state_section(rep, make_facts())
    check("state_no_handle", NO_HANDLE_HINT.split(",")[0] in rep.render(), True)
    rep = Report("s3")
    state_section(rep, make_facts(has_handle=True, missing_region=True))
    check("state_missing_region", "the region was not supplied" in rep.render(), True)

    # ----- end-to-end runs through run() ------------------------------------ #
    identity = {"AccountId": "1234567890123456", "Arn": "x", "IdentityType": "AssumedRoleUser",
                "PrincipalId": "y"}

    def routes_for(instance_rows, eip_rows_by_call):
        calls = {"DescribeEipAddresses": 0}

        def router(product, action, params, session_id, timeout):
            if action == "GetCallerIdentity" or action == "GetCallerIdentity":
                return identity
            if action == "DescribeInstances":
                return {"Instances": {"Instance": instance_rows}}
            if action == "DescribeInstanceStatus":
                return {"InstanceStatuses": {"InstanceStatus": [
                    {"InstanceId": "i-bp1example724c8af2a1", "Status": "Running"}]}}
            if action == "DescribeEipAddresses":
                rows = eip_rows_by_call[min(calls["DescribeEipAddresses"], len(eip_rows_by_call) - 1)]
                calls["DescribeEipAddresses"] += 1
                return {"EipAddresses": {"EipAddress": rows}}
            raise AssertionError(action)
        return router

    class RoutingStub:
        def __init__(self, router):
            self.log = []
            self.router = router

        def __call__(self, product, action, params=None, session_id=None, timeout=None):
            self.log.append((product, action))
            return self.router(product, action, dict(params or {}), session_id, timeout)

    def routed_run(args, router):
        stub = RoutingStub(router)
        globals()["call"] = stub
        import sts_token as _st
        original_sts = _st.call
        _st.call = stub
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = run(args)
        finally:
            globals()["call"] = original_call
            _st.call = original_sts
        return rc, buf.getvalue(), stub.log

    # verify on the live-shaped bare instance with the old EIP released
    args = A(intent="verify", instance_id="i-bp1example724c8af2a1", public_ip=None,
             allocation_id="eip-bp1old", region="cn-hangzhou", scan_regions=False,
             max_regions=0, symptom="", old_address="47.98.1.2", timeout=None, json=False)
    router = routes_for([bare_row], [[], [], []])
    rc, out, log = routed_run(args, router)
    check("verify_rc_ok", rc, 0)
    check("verify_status_ok", "STATUS: OK" in out, True)
    check("verify_old_released", "eip-bp1old no longer resolves" in out, True)
    check("verify_old_addr_gone", "differs from 47.98.1.2" in out, True)
    check("verify_no_unbound_tail", "No unbound EIP returned in this region." in out, True)
    check("verify_next_action", out.strip().endswith(INTENT_NEXT_ACTION["verify"]), True)

    # verify with the old EIP still allocated and billing-tail candidates
    inuse = dict(eip_live, AllocationId="eip-bp1old", Status="InUse")
    available = dict(eip_live, AllocationId="eip-bp1spare", Status="Available",
                     InstanceId="")
    router = routes_for([bare_row], [[inuse], [available]])
    args = A(intent="verify", instance_id="i-bp1example724c8af2a1", public_ip=None,
             allocation_id="eip-bp1old", region="cn-hangzhou", scan_regions=False,
             max_regions=0, symptom="", old_address="", timeout=None, json=False)
    rc, out, log = routed_run(args, router)
    check("verify_alloc_still_billed", "eip-bp1old still exists with status InUse" in out, True)
    check("verify_billing_tail_listed",
          "allocated but unbound: 8.135.1.1 (eip-bp1spare)" in out, True)
    check("verify_status_ok_with_warnings", "STATUS: OK" in out, True)

    # change-ip on an EIP-bound instance: 3 renumbered steps, notices present
    router = routes_for([eip_row], [[eip_live]])
    args = A(intent="change-ip", instance_id="i-bp1example724c8af2a1", public_ip=None,
             allocation_id=None, region="cn-hangzhou", scan_regions=False, max_regions=0,
             symptom="", old_address="", timeout=None, json=False)
    rc, out, log = routed_run(args, router)
    check("change_eip_rc", rc, 0)
    check("change_eip_decision", "already an EIP, so no conversion is needed" in out, True)
    check("change_eip_steps3", "step 3/3 - bind the new EIP to the instance" in out, True)
    check("change_notices", all(n.split(" - ")[0] in out for n in THREE_NOTICES), True)
    check("change_wrong_shortcuts", len(WRONG_SHORTCUTS), out.count("\n  - "))

    # change-ip on a fixed instance: 5 steps including the billing switch
    router = routes_for([fixed_row], [[]])
    args = A(intent="change-ip", instance_id="i-bp1example724c8af2a1", public_ip=None,
             allocation_id=None, region="cn-hangzhou", scan_regions=False, max_regions=0,
             symptom="", old_address="", timeout=None, json=False)
    rc, out, log = routed_run(args, router)
    check("change_fixed_decision", "cannot be swapped directly" in out, True)
    check("change_fixed_step1", "step 1/5 - switch the public bandwidth billing method" in out, True)

    # change-ip with an unrelated symptom also prints the counter gate
    router = routes_for([eip_row], [[eip_live]])
    args = A(intent="change-ip", instance_id="i-bp1example724c8af2a1", public_ip=None,
             allocation_id=None, region="cn-hangzhou", scan_regions=False, max_regions=0,
             symptom="ping timeout packet loss", old_address="", timeout=None, json=False)
    rc, out, log = routed_run(args, router)
    check("change_symptom_gate", "counter-example gate on this wording" in out, True)
    check("change_symptom_area", "area: public path quality" in out, True)

    # permission failure: FAIL exit with the region guidance, warning logged
    args = A(intent="change-ip", instance_id="i-x", public_ip=None, allocation_id=None,
             region="cn-hangzhou", scan_regions=False, max_regions=0, symptom="",
             old_address="", timeout=None, json=False)
    rc, out, log = routed_run(
        args, lambda p, a, x, s, t: identity if a in (
            "GetCallerIdentity", "GetCallerIdentity") else (_ for _ in ()).throw(
            CliError(p, a, "NoPermission", "denied")))
    check("perm_rc_fail", rc, 1)
    check("perm_status_fail", "STATUS: FAIL" in out, True)
    check("perm_region_shown", "region cn-hangzhou" in out, True)

    # transient error: degrades with a warning but does not fail the run
    rc, out, log = routed_run(
        args, lambda p, a, x, s, t: identity if a in (
            "GetCallerIdentity", "GetCallerIdentity") else (_ for _ in ()).throw(
            CliError(p, a, "ServiceUnavailable", "busy")))
    check("transient_rc", rc, 0)
    check("transient_status_degraded", "STATUS: DEGRADED" in out, True)
    check("transient_next_action", INTENT_NEXT_ACTION["change-ip"] in out, True)

    # missing region: no query, FAIL, explicit guidance
    no_call_log = []

    def no_query(product, action, params, session_id, timeout):
        no_call_log.append(action)
        return identity
    args = A(intent="change-ip", instance_id="i-x", public_ip=None, allocation_id=None,
             region="", scan_regions=False, max_regions=0, symptom="", old_address="",
             timeout=None, json=False)
    rc, out, log = routed_run(args, no_query)
    check("noregion_rc", rc, 1)
    check("noregion_no_resource_query",
          [a for a in no_call_log if a not in ("GetCallerIdentity", "GetCallerIdentity")], [])
    check("noregion_line", "No query ran: the region is required." in out, True)

    # scan-regions: locates on the third region, records the two misses
    seen = []

    def scan_router(product, action, params, session_id, timeout):
        if action in ("GetCallerIdentity", "GetCallerIdentity"):
            return identity
        if action == "DescribeInstances":
            seen.append(params.get("RegionId"))
            hit = [bare_row] if params.get("RegionId") == "cn-beijing" else []
            return {"Instances": {"Instance": hit}}
        return {}
    args = A(intent="ip-missing", instance_id="i-bp1example724c8af2a1", public_ip=None,
             allocation_id=None, region="", scan_regions=True, max_regions=3, symptom="",
             old_address="", timeout=None, json=False)
    rc, out, log = routed_run(args, scan_router)
    check("scan_seen", seen, ["cn-hangzhou", "cn-shanghai", "cn-beijing"])
    check("scan_found_region", "region cn-beijing (located by scanning regions)" in out, True)
    check("scan_misses", "scanned without a match (2): cn-hangzhou, cn-shanghai" in out, True)

    # ip-missing on the live-shaped bare instance
    router = routes_for([bare_row], [[]])
    args = A(intent="ip-missing", instance_id="i-bp1example724c8af2a1", public_ip=None,
             allocation_id=None, region="cn-hangzhou", scan_regions=False, max_regions=0,
             symptom="", old_address="", timeout=None, json=False)
    rc, out, log = routed_run(args, router)
    check("missing_no_addr_line", "returned no public address" in out, True)
    check("missing_rules_block", RELEASED_ADDRESS_RULES[0][:24] in out, True)

    # triage without any handle: no state section, handoff only
    args = A(intent="triage", instance_id=None, public_ip=None, allocation_id=None,
             region="", scan_regions=False, max_regions=0, symptom="ssh refused port 22",
             old_address="", timeout=None, json=False)
    rc, out, log = routed_run(args, no_query)
    check("triage_nohandle_rc", rc, 0)
    check("triage_nohandle_no_state", "-- current state --" in out, False)
    check("triage_nohandle_area", "area: remote login -> area:ssh-connection" in out, True)

    # --json payload shape
    router = routes_for([eip_row], [[eip_live]])
    args = A(intent="verify", instance_id="i-bp1example724c8af2a1", public_ip=None,
             allocation_id=None, region="cn-hangzhou", scan_regions=False, max_regions=0,
             symptom="", old_address="", timeout=None, json=True)
    rc, out, log = routed_run(args, router)
    check("json_valid", out.strip().splitlines()[-1], "}")
    try:
        payload = json.loads(out[out.index("{"): out.rindex("}") + 1])
        check("json_address_type", payload["address_type"], "eip")
        check("json_status", payload["status"], "OK")
        check("json_identity", payload["identity"], "account ****3456")
    except ValueError as error:
        check("json_parses", str(error), "")

    # ----- sts_token helpers ------------------------------------------------ #
    import sts_token
    check("tag_masks_head", sts_token.account_tag("1234567890123456"), "account ****3456")
    check("tag_empty", sts_token.account_tag(""), "account unknown")
    check("tag_short", sts_token.account_tag("12"), "account ****12")
    cred = CliError("sts", "GetCallerIdentity", "InvalidSecurityToken.Expired", "expired")
    check("guidance_credential", "aliyun sts get-caller-identity" in sts_token.guidance_for(cred), True)
    unavail = CliError("sts", "GetCallerIdentity", "CliUnavailable", "missing")
    check("guidance_cli_missing", "install the Alibaba Cloud CLI" in sts_token.guidance_for(unavail), True)

    # ----- contract guards --------------------------------------------------- #
    src = open(__file__, encoding="utf-8").read()
    # Only check the operational code, not the selftest itself which quotes
    # mutating action names in its assertions.
    core_end = src.index("def _run_selftest():")
    src_core = src[:core_end]
    constants_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_constants.py"),
                         encoding="utf-8").read()
    check("sts_uses_rpc_form",
          'ACTION_GET_CALLER_IDENTITY = "GetCallerIdentity"' in constants_src, True)
    check("exit_code_propagated",
          "if __name__ == \"__main__\":\n    #" in src and "sys.exit(main())" in src
          and "\n    main()\n" not in src, True)
    check("no_mutating_actions_in_core", any(
        token in src_core for token in ("AuthorizeSecurityGroup", "AllocateEipAddress",
                                    "AssociateEipAddress", "UnassociateEipAddress",
                                    "ReleaseEipAddress", "ModifyInstanceNetworkSpec",
                                    "ModifyInstanceSpec", "StopInstance", "RebootInstance")), False)

    print("selftest: {0} passed, {1} failed".format(results["pass"], results["fail"]))
    return 1 if results["fail"] else 0


def main(argv=None):
    if argv is None and "--selftest" in sys.argv:
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    args.timeout = args.timeout or None
    return run(args)


if __name__ == "__main__":
    # propagate main()'s documented exit code; dropping it would make the
    # --selftest failure path always exit 0.
    sys.exit(main())
