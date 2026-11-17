#!/usr/bin/env python3
"""Entry point for the ECS bandwidth change and billing-mode guide.

Single CLI entry for this skill. It reads the live public bandwidth, the bandwidth
billing mode, the public IP shape and the instance state through the query API
whitelist, compares them with what the customer expected, and prints the guided
console path that matches the case. It never sends a mutating call.

  python3 scripts/areas/bandwidth_modify_guide/bandwidth_modify_guide.py --region-id cn-hangzhou --instance-id i-xxxx
  python3 scripts/areas/bandwidth_modify_guide/bandwidth_modify_guide.py --region-id us-west-1 --intent ip-swap --with-eip

Exit codes: 0 evidence collected (OK or DEGRADED), 2 unusable (FAIL), 4 bad arguments.
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import sys

from _cli import CliError, call, dig, new_session_id, redact, warn
from _constants import (
    BANDWIDTH_BY_BANDWIDTH,
    BANDWIDTH_BY_TRAFFIC,
    CHARGE_POSTPAID,
    CHARGE_PREPAID,
    DEFAULT_PAGE_SIZE,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    INSTANCE_IDS_BATCH,
    INTENTS,
    INBOUND_TRACKING_THRESHOLD_MBITPS,
    MAX_PAGES,
    MAX_TIMEOUT_SECONDS,
    PRODUCT_ECS,
    PRODUCT_VPC,
    RAM_ACTIONS,
    SKILL_NAME,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
)
from sts_token import preflight, uid_tag

DOC_LINKS = {
    "config_change_overview":
        "https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-configuration-changes.md",
    "renewal_change":
        "https://help.aliyun.com/zh/ecs/user-guide/renewal-change",
    "temporary_upgrade":
        "https://help.aliyun.com/zh/ecs/user-guide/temporary-upgrade-bandwidth-on-a-daily-basis"
        "#title-jcy-ddl-31o",
    "billing_mode_convert":
        "https://help.aliyun.com/zh/ecs/user-guide/change-the-billing-method-for-network-usage-1",
    "billing_best_practices":
        "https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-ecs-billing-methods.md",
    "convert_ip_to_eip": "https://help.aliyun.com/document_detail/61290.html",
    "unbind_eip": "https://help.aliyun.com/document_detail/65204.html",
    "apply_eip": "https://help.aliyun.com/document_detail/65203.html",
    "bind_eip": "https://help.aliyun.com/document_detail/72125.html",
    "snapshot_billing": "https://help.aliyun.com/zh/ecs/product-overview/snapshots-1",
}

CONSOLE_LINKS = {
    "ecs_instances": "https://ecs.console.aliyun.com/server/region",
    "vpc_eips": "https://vpc.console.aliyun.com/eip/{region-id}/eips",
    "oos_bandwidth": "https://oos.console.aliyun.com/{region-id}/maintenance/bandwidth",
    "price_configurator": "https://www.aliyun.com/price/cpq/",
    "campaign_99": "https://www.aliyun.com/daily-act/ecs/99program",
}

# Guidance blocks. Held as constants because scripts/ carries no data file.
GUIDANCE = {
    "survey": [
        "Report the live values per instance, then ask which area the customer wants: the "
        "bandwidth value, the bandwidth billing mode, or the public IP.",
        "Bandwidth-only adjustments do not need an instance restart; a CPU or memory resize does. "
        "Never mix the two answers.",
    ],
    "resize": [
        "Increase or decrease the value: console instance list, choose the instance, open the "
        "bandwidth change entry, set the target value, read the fee shown on the confirmation "
        "page, submit. %s" % CONSOLE_LINKS["ecs_instances"],
        "A subscription instance that is already at its term limit uses the renewal-with-change "
        "path instead: %s" % DOC_LINKS["renewal_change"],
        "Published entry point for the whole topic: %s" % DOC_LINKS["config_change_overview"],
        "A lower value cannot be rolled back afterwards; restoring it is a new change with its "
        "own price difference.",
        "The change page enforces whatever bandwidth floor applies to this shape and region; read "
        "it from the page instead of promising a specific minimum.",
    ],
    "not-effective": [
        "Compare the live value printed above with the value the customer ordered. A paid order "
        "and an effective configuration are different facts.",
        "If the live value already matches the target, the change took effect: a bandwidth-only "
        "change needs no restart, so ask what the application is measuring and where.",
        "If the live value still differs, this is an order-processing question, not a "
        "configuration question. Escalate a ticket carrying order id, instance id, region, "
        "expected value, the live value above, and the time of the order.",
        "If the customer actually changed CPU or memory rather than bandwidth, that change needs an "
        "instance restart; advise an off-peak window, stopping the application so buffered writes "
        "reach the disk, and a snapshot first. Snapshots are billed: %s"
        % DOC_LINKS["snapshot_billing"],
        "If the customer also wants a different public IP, that part is not covered by a "
        "bandwidth change at all: run --intent ip-swap.",
    ],
    "billing-convert": [
        "Two independent dimensions: the instance charge type (subscription or pay-as-you-go) and "
        "the bandwidth billing mode (fixed bandwidth or pay-by-traffic). A subscription covers the "
        "instance, the system disk and the image licence; pay-by-traffic bandwidth is billed "
        "afterwards. %s" % DOC_LINKS["billing_best_practices"],
        "Conversion entry: %s" % DOC_LINKS["billing_mode_convert"],
        "Fee preview method, which is the only reliable one: open the conversion page, select the "
        "target mode, read the estimated refund or charge shown there, and do not confirm. Nobody "
        "can compute an account-level figure from outside the billing page.",
        "Before converting, say plainly that a campaign or discounted order may be refunded at "
        "zero, and that switching back to fixed bandwidth later may cost more than the original.",
    ],
    "ip-swap": [
        "A fixed public IP cannot be edited in place. Run the five-step EIP path in "
        "references/bandwidth-modify-guide__eip-swap-runbook.md, in this order: bandwidth billing mode conversion, "
        "convert the fixed IP to an EIP, unbind, apply a new EIP, bind it.",
        "Step documents: %s | %s | %s | %s" % (DOC_LINKS["billing_mode_convert"],
                                               DOC_LINKS["convert_ip_to_eip"],
                                               DOC_LINKS["unbind_eip"],
                                               DOC_LINKS["apply_eip"]),
        "Binding step: %s" % DOC_LINKS["bind_eip"],
        "Three caveats to state up front: an EIP cannot be turned back into a fixed public IP; an "
        "EIP carries its own configuration fee on top of bandwidth; the old EIP keeps billing "
        "until it is released in the VPC console.",
        "Closing check: release the old EIP in the region's EIP list (%s), then re-run with "
        "--with-eip and confirm the old address is gone and the new one is bound to the instance."
        % CONSOLE_LINKS["vpc_eips"],
    ],
    "temp-upgrade": [
        "Periodic short peaks are the temporary upgrade case, not a permanent one: instance list, "
        "bandwidth change entry, temporary upgrade, set value and window, pay, effective at once. "
        "%s" % CONSOLE_LINKS["ecs_instances"],
        "Repeating schedule: the bandwidth maintenance task in OOS. %s" % CONSOLE_LINKS["oos_bandwidth"],
        "Rules and billing: %s" % DOC_LINKS["temporary_upgrade"],
        "Do not assert the minimum or maximum window from memory; the official page and the "
        "console selector are the authority for the case. See references/bandwidth-modify-guide__evidence-gaps.md.",
        "Inbound follows outbound: below %d Mbit/s purchased outbound the inbound ceiling is "
        "%d Mbit/s; at or above it, inbound equals the purchased outbound value."
        % (INBOUND_TRACKING_THRESHOLD_MBITPS, INBOUND_TRACKING_THRESHOLD_MBITPS),
        "Temporary upgrade applies to subscription instances on fixed bandwidth; the live charge "
        "type and billing mode above decide whether this path exists at all.",
    ],
    "cost-rule": [
        "Explainable rules: each resource item is billed on its own; discounts are not inherited "
        "across a configuration change; leaving a campaign price is permanent once the "
        "configuration changes; a downgrade cannot be revoked, so reversing it pays a difference; "
        "a five-day unconditional refund does not return a spent coupon.",
        "Never a number. Use the console preview, the configurator %s, or a commercial "
        "follow-up with the usual one-business-day callback for bundled renewals and campaign "
        "pricing." % CONSOLE_LINKS["price_configurator"],
        "Campaign pages cover fixed configurations only, which is why an out-of-campaign or "
        "overseas selection goes to commercial: %s" % CONSOLE_LINKS["campaign_99"],
    ],
    "triage": [
        "Slow access is not automatically a bandwidth question. Read the configured value, then "
        "ask which peak window hurts and whether the console monitoring chart reaches it.",
        "If bandwidth is nowhere near the configured value and the symptom is packet loss, ping "
        "timeout or a cross-border path, this leaves the tier: hand off with the facts attached "
        "per references/bandwidth-modify-guide__handoff-matrix.md.",
        "Requests to change disk size, to boot or stop an instance, or to buy something new are "
        "different tiers; hand off rather than answer.",
    ],
}

NEXT_ACTIONS = {
    "survey": "Ask the customer which of the three areas to work on, then rerun with --intent.",
    "resize": "Guide the console bandwidth change; read the fee on the confirmation page.",
    "not-effective": "Escalate a ticket with order id, instance id, expected and live values.",
    "billing-convert": "Walk the customer to the conversion page and read the preview, no submit.",
    "ip-swap": "Run the five-step EIP path, then re-check with --with-eip.",
    "temp-upgrade": "Confirm the peak reading, then guide the temporary upgrade or the OOS task.",
    "cost-rule": "State the rules, then point to the preview page or commercial follow-up.",
    "triage": "Either confirm saturation or hand off with the verified facts.",
}

EIP_PATH_STEPS = [
    "1. Convert the bandwidth billing mode from fixed bandwidth to pay-by-traffic.",
    "2. Convert the fixed public IP of the instance into an EIP.",
    "3. Unbind that EIP from the instance.",
    "4. Apply for a new EIP.",
    "5. Bind the new EIP to the instance, then release the old one when it is no longer needed.",
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="bandwidth_modify_guide.py",
        description="Query-and-guide ECS public bandwidth changes, billing-mode conversion, "
                    "temporary upgrade and the public IP replacement path.",
    )
    parser.add_argument("--region-id", required=True,
                        help="region that owns the instance; never guessed")
    parser.add_argument("--instance-id", action="append", default=[],
                        dest="instance_ids", help="instance id, repeatable; omit to survey")
    parser.add_argument("--intent", choices=INTENTS, default="survey",
                        help="which guidance block to print")
    parser.add_argument("--with-eip", action="store_true", dest="with_eip",
                        help="also query EIP records for the matched instances")
    parser.add_argument("--check-stock", dest="check_stock", metavar="INSTANCE_TYPE",
                        default=None, help="look up sellability before a resize")
    parser.add_argument("--expected-bandwidth", dest="expected_bandwidth", type=int, default=None,
                        metavar="MBITPS", help="value the customer ordered, to test effectiveness")
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE, dest="page_size")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS,
                        help="per-call CLI timeout in seconds (max %d)" % MAX_TIMEOUT_SECONDS)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES,
                        help="backoff retries on transient failures")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit the evidence payload as JSON")
    return parser.parse_args(argv)


def _note(notes, severity, item, reason):
    notes.append({"severity": severity, "item": item, "reason": redact(reason)})


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_list(payload, *path):
    found = dig(payload, *path)
    if isinstance(found, list):
        return found
    if isinstance(found, dict) and found:
        first = sorted(found.values(), key=lambda v: not isinstance(v, list))
        for candidate in first:
            if isinstance(candidate, list):
                return candidate
    return []


def fetch_instances(region, instance_ids, args, session_id, notes):
    """Pages through DescribeInstances; empty list on no match, notes on failure."""
    collected = []
    page = 1
    total = None
    page_cap = 1 if instance_ids else MAX_PAGES
    while page <= page_cap:
        params = {"RegionId": region, "PageNumber": page, "PageSize": args.page_size}
        if instance_ids and page == 1:
            params["InstanceIds"] = json.dumps(list(instance_ids))
        try:
            payload = call(PRODUCT_ECS, "DescribeInstances", params,
                           session_id=session_id, timeout=args.timeout, retries=args.retries)
        except CliError as exc:
            _note(notes, "hard", "ecs:DescribeInstances", _describe(exc, params))
            warn("DescribeInstances failed: %s" % exc)
            return collected, 0
        if not isinstance(payload, dict):
            _note(notes, "hard", "ecs:DescribeInstances", "unexpected response shape")
            return collected, 0
        collected.extend(_first_list(payload, "Instances", "Instance"))
        total = _as_int(dig(payload, "TotalCount"))
        if total is None or len(collected) >= total:
            break
        page += 1
    if instance_ids:
        wanted = set(instance_ids)
        found = set(item.get("InstanceId") for item in collected if item.get("InstanceId"))
        missing = sorted(wanted - found)
        if missing:
            _note(notes, "soft", "requested instance ids",
                  "not returned by DescribeInstances in %s: %s" % (region, ", ".join(missing)))
    return collected, total or 0


def fetch_status_map(region, instance_ids, args, session_id, notes):
    """DescribeInstanceStatus, batched; used to cross-check the reported state."""
    status_map = {}
    ids = [i for i in instance_ids if i][:INSTANCE_IDS_BATCH * MAX_PAGES]
    if not ids:
        return status_map
    for start in range(0, len(ids), INSTANCE_IDS_BATCH):
        params = {"RegionId": region,
                  "InstanceId": list(ids[start:start + INSTANCE_IDS_BATCH]),
                  "PageNumber": 1, "PageSize": DEFAULT_PAGE_SIZE}
        try:
            payload = call(PRODUCT_ECS, "DescribeInstanceStatus", params,
                           session_id=session_id, timeout=args.timeout, retries=args.retries)
        except CliError as exc:
            _note(notes, "soft", "ecs:DescribeInstanceStatus", _describe(exc, params))
            warn("DescribeInstanceStatus failed: %s" % exc)
            continue
        for item in _first_list(payload, "InstanceStatuses", "InstanceStatus"):
            if item.get("InstanceId"):
                status_map[item["InstanceId"]] = item.get("Status")
    return status_map


def fetch_eips(region, args, session_id, notes):
    try:
        payload = call(PRODUCT_VPC, "DescribeEipAddresses",
                       {"RegionId": region, "PageNumber": 1, "PageSize": DEFAULT_PAGE_SIZE},
                       session_id=session_id, timeout=args.timeout, retries=args.retries)
    except CliError as exc:
        _note(notes, "hard", "vpc:DescribeEipAddresses", _describe(exc, {"RegionId": region}))
        warn("DescribeEipAddresses failed: %s" % exc)
        return []
    return _first_list(payload, "EipAddresses", "EipAddress")


def fetch_stock(region, instance_type, charge_type, zone_id, args, session_id, notes):
    params = {"RegionId": region, "DestinationResource": "InstanceType",
              "InstanceChargeType": charge_type or CHARGE_PREPAID}
    if zone_id:
        params["ZoneId"] = zone_id
    if instance_type:
        params["InstanceType"] = instance_type
    try:
        payload = call(PRODUCT_ECS, "DescribeAvailableResource", params,
                       session_id=session_id, timeout=args.timeout, retries=args.retries)
    except CliError as exc:
        _note(notes, "soft", "ecs:DescribeAvailableResource", _describe(exc, params))
        warn("DescribeAvailableResource failed: %s" % exc)
        return None
    available = []
    for zone in _first_list(payload, "AvailableZones", "AvailableZone"):
        for region_res in _first_list(zone, "AvailableResources", "AvailableResource"):
            for resource in _first_list(region_res, "SupportedResources", "SupportedResource"):
                available.append({
                    "zone_id": zone.get("ZoneId"),
                    "status": resource.get("Status"),
                    "value": resource.get("Value") or resource.get("SupportedResource"),
                })
    if not available:
        _note(notes, "soft", "sellability lookup",
              "no availability entries returned for %s" % instance_type)
    return available


def _describe(exc, params):
    declared = ", ".join("%s=%s" % (k, redact(str(v))) for k, v in sorted(params.items()))
    return "%s (%s) | declared params: %s" % (exc.code, redact(exc.message), declared)


def summarize(instance, status_map, eips):
    """Facts for one instance, taken only from fields the response actually carried."""
    instance_id = instance.get("InstanceId") or "unknown"
    outbound = _as_int(instance.get("InternetMaxBandwidthOut"))
    inbound = _as_int(instance.get("InternetMaxBandwidthIn"))
    fixed_ips = [ip for ip in _first_list(instance, "PublicIpAddress", "IpAddress") if ip]
    eip_block = instance.get("EipAddress") or {}
    eip_address = eip_block.get("IpAddress") if isinstance(eip_block, dict) else None
    public_ip = eip_address or (fixed_ips[0] if fixed_ips else None)
    if eip_address:
        ip_shape = "eip"
    elif fixed_ips:
        ip_shape = "fixed-public-ip"
    else:
        ip_shape = "none"
    related_eips = [e for e in eips
                    if e.get("IpAddress") == eip_address
                    or (instance_id and e.get("AssociatedInstanceId") == instance_id)]
    charge = instance.get("InstanceChargeType") or "unknown"
    band_billing = instance.get("InternetChargeType") or "unknown"
    facts = {
        "instance_id": instance_id,
        "instance_name": instance.get("InstanceName"),
        "region_id": instance.get("RegionId"),
        "zone_id": instance.get("ZoneId"),
        "instance_type": instance.get("InstanceType"),
        "instance_network_type": instance.get("InstanceNetworkType"),
        "status_from_describe_instances": instance.get("Status"),
        "status_from_describe_instance_status": status_map.get(instance_id),
        "instance_charge_type": charge,
        "bandwidth_internet_charge_type": band_billing,
        "internet_max_bandwidth_out_mbitps": outbound,
        "internet_max_bandwidth_in_mbitps": inbound,
        "inbound_rule_expected_mbitps": _expected_inbound(outbound),
        "public_ip": public_ip,
        "public_ip_shape": ip_shape,
        "fixed_public_ips": fixed_ips,
        "eip_allocation_id": eip_block.get("AllocationId") if isinstance(eip_block, dict) else None,
        "eip_count_for_instance": len(related_eips),
        "expired_time": instance.get("ExpiredTime"),
        "vpc_attributes_private_ip": dig(instance, "VpcAttributes", "PrivateIpAddress", "IpAddress"),
    }
    facts["checks"] = _checks(facts, charge, band_billing, outbound)
    return facts


def _expected_inbound(outbound):
    if outbound is None:
        return None
    if outbound < INBOUND_TRACKING_THRESHOLD_MBITPS:
        return INBOUND_TRACKING_THRESHOLD_MBITPS
    return outbound


def _checks(facts, charge, band_billing, outbound):
    checks = []
    if charge and charge not in (CHARGE_PREPAID, CHARGE_POSTPAID):
        checks.append("instance charge type %s was not recognised; report it verbatim" % charge)
    if band_billing and band_billing not in (BANDWIDTH_BY_BANDWIDTH, BANDWIDTH_BY_TRAFFIC):
        checks.append("bandwidth billing mode %s was not recognised; report it verbatim"
                      % band_billing)
    if facts["status_from_describe_instances"] and facts["status_from_describe_instance_status"]:
        if facts["status_from_describe_instances"] != facts["status_from_describe_instance_status"]:
            checks.append("the two status reads disagree; quote both")
    if facts["internet_max_bandwidth_in_mbitps"] and facts["inbound_rule_expected_mbitps"]:
        if facts["internet_max_bandwidth_in_mbitps"] != facts["inbound_rule_expected_mbitps"]:
            checks.append("inbound value differs from the published rule; report the live value")
    if outbound == 0:
        checks.append("outbound bandwidth is 0, so the instance has no public bandwidth to adjust")
    if facts["public_ip_shape"] == "fixed-public-ip":
        checks.append("fixed public IP: replacement requires the five-step EIP path")
    return checks


def decide_status(notes, instances_found):
    if any(n["severity"] == "hard" for n in notes) or not instances_found:
        return STATUS_DEGRADED
    return STATUS_OK


def build_report(args, session_id, identity, instances_facts, eips, stock, notes):
    status = decide_status(notes, len(instances_facts))
    report = {
        "skill": SKILL_NAME,
        "session_id": session_id,
        "caller": uid_tag(identity),
        "region_id": args.region_id,
        "intent": args.intent,
        "declared_parameters": {
            "RegionId": args.region_id,
            "InstanceIds": args.instance_ids or None,
            "PageSize": args.page_size,
            "TimeoutSeconds": args.timeout,
            "Retries": args.retries,
            "EipQuery": bool(args.with_eip or args.intent == "ip-swap"),
            "SellabilityLookupFor": args.check_stock,
        },
        "query_surface": list(RAM_ACTIONS),
        "mutation_performed": False,
        "instance_count": len(instances_facts),
        "instances": instances_facts,
        "eip_records": [
            {"allocation_id": e.get("AllocationId"), "ip_address": e.get("IpAddress"),
             "status": e.get("Status"), "bandwidth_mbitps": _as_int(e.get("Bandwidth")),
             "internet_charge_type": e.get("InternetChargeType"),
             "associated_instance_id": e.get("AssociatedInstanceId")}
            for e in eips
        ],
        "sellability": stock,
        "expected_bandwidth_mbitps": args.expected_bandwidth,
        "effectiveness": _effectiveness(instances_facts, args.expected_bandwidth),
        "limitations": _limitations(notes, args),
        "gaps": [n for n in notes],
        "guidance": GUIDANCE.get(args.intent, []),
        "eip_path_steps": EIP_PATH_STEPS if args.intent == "ip-swap" else [],
        "status": status,
        "next_action": NEXT_ACTIONS.get(args.intent, "Report the evidence and ask one question."),
    }
    return report


def _effectiveness(instances_facts, expected):
    if expected is None or not instances_facts:
        return None
    matched = [f["instance_id"] for f in instances_facts
               if f["internet_max_bandwidth_out_mbitps"] == expected]
    differed = [{"instance_id": f["instance_id"],
                 "live_mbitps": f["internet_max_bandwidth_out_mbitps"]}
                for f in instances_facts
                if f["internet_max_bandwidth_out_mbitps"] != expected]
    return {"expected_mbitps": expected, "already_at_target": matched, "differs": differed}


def _limitations(notes, args):
    limits = [
        "Public bandwidth utilisation is not part of the verified query surface of this skill, so "
        "no peak reading is printed; ask the customer for the console bandwidth monitoring chart "
        "of the affected window.",
        "Account level pricing, discount entitlement and refund arithmetic are not exposed; the "
        "console confirmation page is the only source of a figure.",
        "No order, invoice or ticket lookup is available in this package.",
    ]
    if args.intent == "temp-upgrade":
        limits.append("The temporary upgrade duration window is not asserted here; see "
                      "references/bandwidth-modify-guide__evidence-gaps.md.")
    if notes:
        limits.append("%d read(s) did not return usable data; see the gaps list." % len(notes))
    return limits


def render_text(report):
    out = []
    out.append("ECS bandwidth guide | session %s | %s" % (report["session_id"], report["caller"]))
    out.append("region=%s intent=%s instances=%d mutation_performed=%s"
               % (report["region_id"], report["intent"], report["instance_count"],
                  str(report["mutation_performed"]).lower()))
    out.append("")
    out.append("Declared parameters: %s"
              % json.dumps(report["declared_parameters"], sort_keys=True))
    out.append("Query surface: %s" % ", ".join(report["query_surface"]))
    out.append("")
    if not report["instances"]:
        out.append("No instance evidence collected in %s." % report["region_id"])
    for facts in report["instances"]:
        out.append("Instance %s" % facts["instance_id"])
        for key in ("instance_name", "zone_id", "instance_type", "instance_network_type",
                    "status_from_describe_instances", "status_from_describe_instance_status",
                    "instance_charge_type", "bandwidth_internet_charge_type",
                    "internet_max_bandwidth_out_mbitps", "internet_max_bandwidth_in_mbitps",
                    "inbound_rule_expected_mbitps", "public_ip", "public_ip_shape",
                    "eip_allocation_id", "expired_time"):
            out.append("  %-38s %s" % (key, facts.get(key)))
        for line in facts["checks"]:
            out.append("  note: %s" % line)
        out.append("")
    if report["eip_records"]:
        out.append("EIP records in the region: %d" % len(report["eip_records"]))
        for eip in report["eip_records"]:
            out.append("  %s" % json.dumps(eip, sort_keys=True))
        out.append("")
    if report["sellability"] is not None:
        out.append("Sellability entries: %d" % len(report["sellability"]))
        for entry in report["sellability"][:20]:
            out.append("  %s" % json.dumps(entry, sort_keys=True))
        out.append("")
    if report["expected_bandwidth_mbitps"] is not None:
        out.append("Effectiveness check: %s" % json.dumps(report["effectiveness"], sort_keys=True))
        out.append("")
    if report["eip_path_steps"]:
        out.append("Public IP replacement path (customer performs every step):")
        for step in report["eip_path_steps"]:
            out.append("  %s" % step)
        out.append("")
    out.append("Guidance:")
    for line in report["guidance"]:
        out.append("  - %s" % line)
    out.append("")
    out.append("Limitations:")
    for line in report["limitations"]:
        out.append("  - %s" % line)
    if report["gaps"]:
        out.append("")
        out.append("Unverified reads:")
        for gap in report["gaps"]:
            out.append("  - [%s] %s | %s" % (gap["severity"], gap["item"], gap["reason"]))
    out.append("")
    out.append("STATUS: %s" % report["status"])
    out.append("NEXT_ACTION: %s" % report["next_action"])
    return "\n".join(out)


def _run_selftest():
    """Offline regression lock: pure computation core + contract guards."""
    from _cli import dig, build_argv, is_transient_error, is_permission_error, redact
    from _cli import _plugin_action, ACTION_WHITELIST
    results = {"pass": 0, "fail": 0}

    def check(name, got, want):
        if got == want:
            results["pass"] += 1
        else:
            results["fail"] += 1
            print("FAIL {0}: got {1!r} want {2!r}".format(name, got, want))

    # --- _as_int ---
    check("as_int_valid", _as_int("42"), 42)
    check("as_int_none", _as_int(None), None)
    check("as_int_bad", _as_int("abc"), None)
    check("as_int_float_str", _as_int("3.14"), None)
    check("as_int_zero", _as_int(0), 0)

    # --- _first_list ---
    check("fl_list", _first_list({"Instances": {"Instance": [{"a": 1}]}}, "Instances", "Instance"),
          [{"a": 1}])
    check("fl_missing", _first_list({}, "Instances", "Instance"), [])
    check("fl_none", _first_list({"Instances": None}, "Instances", "Instance"), [])

    # --- dig ---
    check("dig_deep", dig({"a": {"b": {"c": 1}}}, "a", "b", "c"), 1)
    check("dig_miss", dig({"a": {}}, "a", "b", "c"), None)
    check("dig_index", dig({"list": [10, 20]}, "list", 1), 20)

    # --- _expected_inbound ---
    check("inbound_none", _expected_inbound(None), None)
    check("inbound_zero", _expected_inbound(0), INBOUND_TRACKING_THRESHOLD_MBITPS)
    check("inbound_below", _expected_inbound(5), INBOUND_TRACKING_THRESHOLD_MBITPS)
    check("inbound_at", _expected_inbound(10), 10)
    check("inbound_above", _expected_inbound(100), 100)

    # --- _checks ---
    base_facts = {
        "status_from_describe_instances": "Running",
        "status_from_describe_instance_status": "Running",
        "internet_max_bandwidth_in_mbitps": 10,
        "inbound_rule_expected_mbitps": 10,
        "public_ip_shape": "eip",
    }
    check("chk_normal", _checks(base_facts, "PostPaid", "PayByTraffic", 5), [])
    check("chk_unknown_charge",
          "not recognised" in " ".join(_checks(base_facts, "Spot", "PayByTraffic", 5)), True)
    check("chk_status_disagree",
          "disagree" in " ".join(_checks(
            dict(base_facts, status_from_describe_instance_status="Stopped"),
            "PostPaid", "PayByTraffic", 5)), True)
    check("chk_outbound_zero",
          "no public bandwidth" in " ".join(_checks(
            dict(base_facts, internet_max_bandwidth_in_mbitps=None,
                 inbound_rule_expected_mbitps=None),
            "PostPaid", "PayByTraffic", 0)), True)
    check("chk_fixed_ip",
          "five-step" in " ".join(_checks(
            dict(base_facts, public_ip_shape="fixed-public-ip"),
            "PostPaid", "PayByTraffic", 5)), True)

    # --- summarize ---
    raw_inst = {"InstanceId": "i-x", "InstanceName": "web", "RegionId": "cn-hangzhou",
                "ZoneId": "cn-hangzhou-k", "Status": "Running", "InstanceType": "ecs.g6.large",
                "InstanceNetworkType": "vpc", "InstanceChargeType": "PostPaid",
                "InternetChargeType": "PayByTraffic", "InternetMaxBandwidthOut": 5,
                "InternetMaxBandwidthIn": 10,
                "PublicIpAddress": {"IpAddress": ["1.2.3.4"]},
                "EipAddress": {"IpAddress": "", "AllocationId": ""},
                "VpcAttributes": {"PrivateIpAddress": {"IpAddress": ["10.0.0.1"]}}}
    f = summarize(raw_inst, {"i-x": "Running"}, [])
    check("sum_id", f["instance_id"], "i-x")
    check("sum_outbound", f["internet_max_bandwidth_out_mbitps"], 5)
    check("sum_inbound_expected", f["inbound_rule_expected_mbitps"], 10)
    check("sum_ip_shape", f["public_ip_shape"], "fixed-public-ip")
    check("sum_public_ip", f["public_ip"], "1.2.3.4")
    check("sum_checks_empty", len(f["checks"]), 1)  # fixed-public-ip note
    check("sum_checks_content", "five-step" in f["checks"][0], True)

    # --- decide_status ---
    check("ds_ok", decide_status([], 1), STATUS_OK)
    check("ds_degraded_no_instances", decide_status([], 0), STATUS_DEGRADED)
    check("ds_degraded_hard_note", decide_status([{"severity": "hard"}], 1), STATUS_DEGRADED)
    check("ds_soft_note", decide_status([{"severity": "soft"}], 1), STATUS_OK)

    # --- _effectiveness ---
    ef = _effectiveness([f], 5)
    check("eff_match", "i-x" in ef["already_at_target"], True)
    check("eff_differ_empty", ef["differs"], [])
    ef2 = _effectiveness([f], 100)
    check("eff_mismatch", any(d["instance_id"] == "i-x" for d in ef2["differs"]), True)
    check("eff_none_expected", _effectiveness([f], None), None)
    check("eff_no_instances", _effectiveness([], 5), None)

    # --- _plugin_action (whitelist bridge) ---
    check("pa_rpc_pascal", _plugin_action(["sts", "GetCallerIdentity"]), "GetCallerIdentity")
    check("pa_hyphen_legacy", _plugin_action(["sts", "get-caller-identity"]), "GetCallerIdentity")

    # --- build_argv ---
    argv = build_argv("ecs", "DescribeInstances", {"RegionId": "cn-hangzhou", "InstanceIds": '["i-1"]'})
    check("ba_basic", argv[:3], ["aliyun", "ecs", "describe-instances"])
    check("ba_has_region", "--biz-region-id" in argv and "cn-hangzhou" in argv, True)
    argv2 = build_argv("ecs", "DescribeInstanceStatus", {"InstanceId": ["i-a", "i-b"]})
    check("ba_list_repeated_values",
          argv2[argv2.index("--instance-id") + 1:argv2.index("--instance-id") + 3], ["i-a", "i-b"])

    # --- redact ---
    check("redact_ak", "***" in redact("AccessKeyId=LTAI5tXXXX"), True)
    check("redact_none", redact(None), "")
    check("redact_json_field", '"SecurityToken": "***"' in redact('{"SecurityToken": "abc"}'), True)

    # --- is_transient / is_permission ---
    check("tr_throttle", is_transient_error("Throttling.User"), True)
    check("tr_timeout", is_transient_error("timed out after 30s"), True)
    check("tr_no_perm", is_transient_error("NoPermission"), False)
    check("perm_no", is_permission_error("NoPermission"), True)
    check("perm_implicit", is_permission_error("ImplicitDeny"), True)
    check("perm_no_tr", is_permission_error("Throttling"), False)

    # --- contract guards ---
    import os
    src = open(__file__, encoding="utf-8").read()
    check("exit_propagated", "raise SystemExit(main())" in src, True)
    check("sts_cmd_in_constants",
          '"get-caller-identity"' in open(
              os.path.join(os.path.dirname(os.path.abspath(__file__)), "_constants.py"),
              encoding="utf-8").read(), True)
    check("readonly_whitelist",
          "DescribeInstances" in str(ACTION_WHITELIST) and
          "StopInstance" not in str(ACTION_WHITELIST), True)
    from _cli import check_action
    try:
        check_action("ecs", "StopInstance")
        check("whitelist_denies_stop", False, True)
    except Exception as exc:
        check("whitelist_denies_stop", "WhitelistViolation" in str(exc), True)

    print("selftest: {0} passed, {1} failed".format(results["pass"], results["fail"]))
    return 1 if results["fail"] else 0


def main(argv=None):
    if argv is None and "--selftest" in sys.argv:
        return _run_selftest()
    args = parse_args(argv)
    args.region_id = args.region_id.strip()
    args.instance_ids = [i.strip() for i in args.instance_ids if i and i.strip()]
    if not args.region_id:
        sys.stderr.write("[FAIL] --region-id must not be empty; it is never guessed.\n")
        return 4
    args.timeout = max(1, min(args.timeout, MAX_TIMEOUT_SECONDS))

    session_id = new_session_id()
    identity, error = preflight(session_id=session_id, timeout=args.timeout)
    if error is not None:
        sys.stdout.write("STATUS: %s\n" % STATUS_FAIL)
        sys.stdout.write("NEXT_ACTION: %s (%s: %s)\n"
                         % (error["remediation"], error["code"], error["message"]))
        sys.stdout.write("session %s\n" % session_id)
        return 2

    notes = []
    raw_instances, _total = fetch_instances(args.region_id, args.instance_ids, args,
                                            session_id, notes)
    ids_to_check = [i.get("InstanceId") for i in raw_instances if i.get("InstanceId")]
    status_map = fetch_status_map(args.region_id, ids_to_check, args, session_id, notes)
    eips = []
    if args.with_eip or args.intent == "ip-swap":
        eips = fetch_eips(args.region_id, args, session_id, notes)
    stock = None
    if args.check_stock:
        first = raw_instances[0] if raw_instances else {}
        stock = fetch_stock(args.region_id, args.check_stock,
                            first.get("InstanceChargeType"), first.get("ZoneId"),
                            args, session_id, notes)

    facts = [summarize(i, status_map, eips) for i in raw_instances]
    report = build_report(args, session_id, identity, facts, eips, stock, notes)
    if args.as_json:
        sys.stdout.write(json.dumps(report, sort_keys=True, indent=2, default=str) + "\n")
    else:
        sys.stdout.write(render_text(report) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
