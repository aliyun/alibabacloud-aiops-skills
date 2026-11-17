#!/usr/bin/env python3
"""Single entry point for cross-border and overseas link quality diagnosis.

Read-only: this script performs only the whitelisted calls listed in READ_SCOPE
below, prints an evidence report, and never mutates anything or runs anything
inside the instance.
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _cli import SESSION_ID, USER_AGENT, mask_secrets, run_cli_quiet, warn  # noqa: E402
from _constants import (  # noqa: E402
    API_VERSIONS,
    BRANCH_BANDWIDTH_LIMIT,
    BRANCH_BORDER_CONGESTION,
    BRANCH_CARRIER_POLICY,
    BRANCH_CROSS_ACCOUNT,
    BRANCH_FORWARDING_FAULT,
    BRANCH_HANDOFF,
    BRANCH_INSUFFICIENT,
    BRANCH_INSTANCE_STATE,
    BRANCH_NOT_CROSS_BORDER,
    BRANCH_REGULATORY_BOUNDARY,
    CONGESTION_EXPLANATION,
    CONGESTION_WAIVER,
    DIRECTIONS,
    DOC_LINKS,
    EVIDENCE_CHECKLIST,
    EVIDENCE_KEYS,
    HANDOFFS,
    IP_DIFFERENCE_STATEMENT,
    LINK_DISCLAIMER,
    MAINLAND_KEYWORDS,
    NEW_IP_STATEMENT,
    NO_GUARANTEE_STATEMENT,
    OVERSEAS_KEYWORDS,
    PAGE_NUMBER,
    PAGE_SIZE,
    RAM_ACTIONS,
    REGION_ALIASES,
    REGION_LABELS,
    RECOVERY_STATEMENT,
    SIDES,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
    SYMPTOMS,
    THIRD_PARTY_RISK_STATEMENT,
)
from sts_token import get_caller_identity, guidance_for, trace_tag  # noqa: E402

READ_SCOPE = (
    ("ecs", "DescribeInstances"),
    ("ecs", "DescribeInstanceStatus"),
    ("ecs", "DescribeAvailableResource"),
    ("vpc", "DescribeEipAddresses"),
    ("sts", "GetCallerIdentity"),
)

FORWARDING_MARKERS = (
    "request-arrives-response-lost",
    "eip-change-no-help",
    "multi-tcp-timeout",
    "last-hop-drop",
    "overseas-users-normal",
)

# Evidence keys that end this diagnosis: either a sibling tier owns the symptom,
# or the cause is outside Alibaba Cloud's network entirely.
OTHER_TIER_RESPONSES = {
    "disk-not-expanded": {"handoff": "disk-expand"},
    "io-slow": {"handoff": "disk-io"},
    "ssh-auth-failure": {"handoff": "ssh"},
    "panel-login-only": {"handoff": "panel"},
    "filing-context": {"handoff": "filing"},
    "intranet-egress-config": {"handoff": "intranet-egress"},
    "attack-traffic": {"handoff": "attack"},
    "transfer-tool-only": {"handoff": "file-transfer"},
    "cdn-bypass-still-slow": {"handoff": "web-access"},
    "fixed-stall-seconds": {"handoff": "web-access"},
    "platform-restriction": {"handoff": "punishment"},
    "change-requested": {"handoff": "manual-change"},
    "third-party-risk-control": {"wording": THIRD_PARTY_RISK_STATEMENT},
}

OPTION_BY_SIDE = {
    "inbound_mainland_users_overseas_server": (
        "If the user base is mainly in Chinese mainland, host the service on a mainland "
        "instance so that user traffic never depends on a cross-border path."
    ),
    "inbound_overseas_users": (
        "If the user base is mainly outside mainland China, keep or move the service to an "
        "overseas region close to those users; users near the instance should see low, "
        "stable latency."
    ),
    "outbound_from_mainland": (
        "For a mainland instance that must reach an overseas endpoint, evaluate Global "
        "Accelerator instead of the best-effort public path: %s"
        % DOC_LINKS["global-accelerator-scenarios"]
    ),
    "outbound_landing_near_users": (
        "Stage the transfer through an endpoint close to the receiving side (an instance or "
        "object storage in the region nearest the user), then fetch it from there, instead "
        "of pushing data across the cross-border path in one hop."
    ),
}

VERDICT_HEADLINE = {
    BRANCH_BORDER_CONGESTION: "Cross-border public path congestion or carrier routing loss",
    BRANCH_FORWARDING_FAULT: "Suspected platform egress, NAT, or return-path fault - escalate",
    BRANCH_CARRIER_POLICY: "Carrier-side policy or local block on this address",
    BRANCH_REGULATORY_BOUNDARY: "Regulatory boundary on cross-border access, not an instance fault",
    BRANCH_BANDWIDTH_LIMIT: "Local bandwidth ceiling, not a cross-border path problem",
    BRANCH_NOT_CROSS_BORDER: "Not a cross-border issue",
    BRANCH_CROSS_ACCOUNT: "Resource not under the queried account",
    BRANCH_INSTANCE_STATE: "Instance state blocks the connection",
    BRANCH_HANDOFF: "Belongs to another tier",
    BRANCH_INSUFFICIENT: "No attribution yet",
}


def build_parser():
    parser = argparse.ArgumentParser(
        prog="cross_border_link_diagnosis.py",
        description=(
            "Read-only cross-border / overseas link quality diagnosis. Collects cloud-side "
            "evidence, applies the attribution rules, prints a report. Performs no mutation "
            "and no guest execution."
        ),
    )
    parser.add_argument("--region-id", help="region id of the resource; never guessed")
    parser.add_argument("--instance-id", help="ECS instance id, e.g. i-exampleid")
    parser.add_argument("--public-ip", help="fixed public IP of the instance")
    parser.add_argument("--eip", help="Elastic IP address bound to the instance")

    parser.add_argument(
        "--direction", choices=DIRECTIONS, default="unknown",
        help="inbound: users reach the server; outbound: the server reaches an external target",
    )
    parser.add_argument(
        "--source-side", choices=SIDES, default="unknown",
        help="where the traffic starts",
    )
    parser.add_argument(
        "--target-side", choices=SIDES, default="unknown",
        help="where the traffic is headed",
    )
    parser.add_argument(
        "--symptom", choices=SYMPTOMS, default="unknown",
    )
    parser.add_argument("--source-location", help="city and carrier of the affected client")
    parser.add_argument("--target-desc", help="external domain / address / port that fails")
    parser.add_argument("--error-string", help="verbatim client-side error, e.g. err_timed_out")
    parser.add_argument("--time-window", help="when it started and how long it lasts")
    parser.add_argument(
        "--user-base", choices=("mainland", "overseas", "mixed", "unknown"),
        default="unknown", help="where the business's users actually are",
    )
    parser.add_argument(
        "--evidence", action="append", default=[], metavar="KEY",
        help="observed fact, repeatable; known keys: %s" % ", ".join(sorted(EVIDENCE_KEYS)),
    )
    parser.add_argument("--mtr-file", help="path to raw MTR text captured by the customer")
    parser.add_argument("--customer-note", action="append", default=[],
                        help="verbatim customer statement worth recording; repeatable")

    parser.add_argument("--check-target-region",
                        help="validate stock in a suggested migration region")
    parser.add_argument("--instance-type", help="instance type used with --check-target-region")
    parser.add_argument("--zone-id", help="zone used with --check-target-region")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--skip-owner-check", action="store_true",
                        help="skip the account identity probe")
    return parser


def normalize_region(value):
    if not value:
        return None
    stripped = value.strip()
    lowered = stripped.lower().replace(" ", "").replace("_", "-")
    if lowered in REGION_LABELS:
        return lowered
    return REGION_ALIASES.get(lowered, stripped)


def validate(args, notes):
    missing = []
    if not args.region_id:
        missing.append("--region-id (the region of the resource; this skill does not guess it)")
    if not (args.instance_id or args.public_ip or args.eip):
        missing.append("one of --instance-id / --public-ip / --eip")
    if args.direction == "unknown":
        missing.append("--direction (inbound or outbound; the fixes are opposite)")
    if args.source_side == "unknown" and args.target_side == "unknown":
        missing.append("--source-side / --target-side (mainland or overseas on each end)")
    if args.symptom == "unknown":
        missing.append("--symptom (slow, timeout, packet-loss, port-blocked, partial-isp)")
    for key in args.evidence:
        if key not in EVIDENCE_KEYS:
            notes.append("unrecognised --evidence key ignored: %s" % key)
    return missing


def label_region(region_id):
    entry = REGION_LABELS.get(region_id)
    if entry:
        return entry["label"], entry["side"]
    if region_id:
        lowered = region_id.lower()
        if lowered.startswith("cn-") and lowered != "cn-hongkong":
            return "%s (mainland-prefixed region, not in the built-in list)" % region_id, "mainland"
    return region_id or "unknown", "unknown"


def side_from_text(text):
    if not text:
        return "unknown"
    lowered = text.lower()
    mainland = any(token in lowered for token in MAINLAND_KEYWORDS)
    overseas = any(token in lowered for token in OVERSEAS_KEYWORDS)
    if mainland and not overseas:
        return "mainland"
    if overseas and not mainland:
        return "overseas"
    return "unknown"


def is_overseas_side(side):
    return side in ("overseas", "overseas_direction")


def ram_action_for(product, action):
    return RAM_ACTIONS.get((product, action), "%s:%s" % (product, action))


def note_auth_gap(ctx, product, action, error):
    ctx["api_failures"].append(str(error))
    warn(str(error))
    if getattr(error, "is_auth", False):
        ctx["gaps"].append(
            "%s was refused (%s). Attach this single action to the operator's policy: %s"
            % (action, error.code, ram_action_for(product, action))
        )
    else:
        ctx["gaps"].append("%s did not return data (%s); fall back to the console page."
                           % (action, error.code))


def resolve_instance(region_id, instance_id, public_ip, eip):
    params = {"RegionId": region_id, "PageNumber": PAGE_NUMBER, "PageSize": PAGE_SIZE}
    if instance_id:
        params["InstanceIds"] = json.dumps([instance_id])
    elif public_ip:
        params["PublicIpAddresses"] = json.dumps([public_ip])
    elif eip:
        params["EipAddresses"] = json.dumps([eip])
    payload, error = run_cli_quiet("ecs", "DescribeInstances", params)
    if error is not None:
        return None, error
    if payload is None:
        return None, None
    instances = (payload.get("Instances") or {}).get("Instance") or []
    return (instances[0] if instances else None), None


def describe_eip(region_id, address, instance_id):
    params = {"RegionId": region_id, "PageNumber": PAGE_NUMBER, "PageSize": PAGE_SIZE}
    if address:
        params["EipAddress"] = address
    elif instance_id:
        params["AssociatedInstanceId"] = instance_id
    payload, error = run_cli_quiet("vpc", "DescribeEipAddresses", params)
    if error is not None:
        return None, error
    if payload is None:
        return None, None
    entries = (payload.get("EipAddresses") or {}).get("EipAddress") or []
    return (entries or None), None


def describe_instance_status(region_id, instance_id):
    payload, error = run_cli_quiet(
        "ecs", "DescribeInstanceStatus",
        {"RegionId": region_id, "InstanceId": [instance_id]},
    )
    if error is not None:
        return None, error
    entries = ((payload or {}).get("InstanceStatuses") or {}).get("InstanceStatus") or []
    for entry in entries:
        if entry.get("InstanceId") == instance_id:
            return entry.get("Status"), None
    return None, None


def describe_availability(region_id, instance_type, zone_id):
    params = {
        "RegionId": region_id,
        "DestinationResource": "InstanceType",
        "InstanceChargeType": "PostPaid",
    }
    if instance_type:
        params["InstanceType"] = instance_type
    if zone_id:
        params["ZoneId"] = zone_id
    return run_cli_quiet("ecs", "DescribeAvailableResource", params)


def read_raw_text(path, limit_lines=400):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except OSError as error:
        return None, "could not read %s (%s)" % (path, mask_secrets(error))
    return lines[:limit_lines], None


def mtr_facts(lines, addresses):
    """Mechanical facts about a raw capture; deliberately not an interpretation."""
    if not lines:
        return ["raw MTR file was empty"]
    hop_rows = [line for line in lines if "%" in line and any(ch.isdigit() for ch in line)]
    text = "\n".join(lines)
    facts = ["raw capture attached: %d rows with a loss column" % len(hop_rows)]
    known = [address for address in addresses if address]
    if known:
        hit = [address for address in known if address in text]
        facts.append(
            "destination address appears in the capture: %s"
            % ("yes (%s)" % ", ".join(hit) if hit
               else "no - the last visible hop is not the destination")
        )
    facts.append(
        "caveat: intermediate hops can rate-limit ICMP, so hop loss is only meaningful "
        "together with the TCP test on the target port"
    )
    return facts


def read_availability(payload, region_id):
    zones = ((payload or {}).get("AvailableZones") or {}).get("AvailableZone") or []
    if not zones:
        return {
            "region": region_id,
            "verdict": "unrecognised-response",
            "detail": "the call succeeded but returned no zone entries; confirm in the console",
        }
    available = [zone.get("ZoneId") for zone in zones if zone.get("Status") == "Available"]
    return {
        "region": region_id,
        "verdict": "available" if available else "unavailable",
        "detail": "zones reporting capacity: %s" % (", ".join([z for z in available if z])
                                                    or "none"),
    }


def gather(args):
    """Run the read-only queries and assemble the diagnosis context."""
    ctx = {
        "evidence": [],
        "gaps": [],
        "notes": [],
        "probes": [],
        "api_failures": [],
        "resource": {},
        "availability": None,
        "owner": None,
        "cross_border": None,
        "far_side": None,
    }
    for key in dict.fromkeys(args.evidence):
        if key in EVIDENCE_KEYS:
            ctx["evidence"].append("[CUSTOMER] %s" % EVIDENCE_KEYS[key])

    if not args.skip_owner_check:
        identity, identity_error = get_caller_identity()
        ctx["owner"] = trace_tag(identity)
        if identity_error is not None:
            ctx["api_failures"].append(str(identity_error))
            ctx["gaps"].append(guidance_for(identity_error))
        else:
            ctx["evidence"].append("[API] queries ran against %s" % ctx["owner"])

    args.region_id = normalize_region(args.region_id)
    region_label, instance_side = label_region(args.region_id)
    ctx["region_label"] = region_label
    ctx["instance_side"] = instance_side

    if not args.region_id or not (args.instance_id or args.public_ip or args.eip):
        ctx["resource"]["resolved"] = False
        return ctx

    instance, instance_error = resolve_instance(
        args.region_id, args.instance_id, args.public_ip, args.eip
    )
    if instance_error is not None:
        note_auth_gap(ctx, "ecs", "DescribeInstances", instance_error)
        ctx["resource"]["resolved"] = False
        return ctx
    if instance is None:
        ctx["resource"]["resolved"] = False
        ctx["evidence"].append(
            "[API] DescribeInstances returned no instance for the supplied id or address in "
            "%s: the resource is not under the queried account and region" % args.region_id
        )
        return ctx

    resource = ctx["resource"]
    resource["resolved"] = True
    resource["instance_id"] = instance.get("InstanceId")
    resource["status"] = instance.get("Status")
    resource["instance_type"] = instance.get("InstanceType")
    resource["zone_id"] = instance.get("ZoneId")
    resource["network_type"] = instance.get("InstanceNetworkType")
    resource["internet_max_bandwidth_out"] = instance.get("InternetMaxBandwidthOut")
    resource["public_ips"] = [
        item.get("IpAddress")
        for item in (instance.get("PublicIpAddresses") or {}).get("IpAddress") or []
    ]
    instance_eip = instance.get("EipAddress") or {}
    resource["eip"] = instance_eip.get("IpAddress") or args.eip
    resource["eip_bandwidth"] = instance_eip.get("Bandwidth")
    resource["security_groups"] = [
        group for group in
        (instance.get("SecurityGroupIds") or {}).get("SecurityGroupId") or []
    ]

    ctx["evidence"].append(
        "[API] instance %s is in %s (%s); that location counts as: %s"
        % (resource["instance_id"], args.region_id, region_label, instance_side)
    )
    ctx["evidence"].append(
        "[API] status=%s, charge type=%s, public outbound bandwidth cap=%s Mbit/s"
        % (instance.get("Status"), instance.get("InstanceChargeType"),
           instance.get("InternetMaxBandwidthOut"))
    )
    if resource["security_groups"]:
        ctx["evidence"].append(
            "[API] attached security groups: %s (rule bodies are not read here; a human "
            "confirms the tested port in the console)" % ", ".join(resource["security_groups"])
        )

    health, status_error = describe_instance_status(args.region_id, resource["instance_id"])
    if status_error is not None:
        note_auth_gap(ctx, "ecs", "DescribeInstanceStatus", status_error)
    else:
        resource["health_status"] = health
        ctx["evidence"].append(
            "[API] DescribeInstanceStatus reports: %s" % (health or "no entry returned")
        )

    entries, eip_error = describe_eip(args.region_id, resource["eip"], resource["instance_id"])
    if eip_error is not None:
        note_auth_gap(ctx, "vpc", "DescribeEipAddresses", eip_error)
    elif entries:
        entry = entries[0]
        resource["eip"] = entry.get("IpAddress") or resource["eip"]
        resource["eip_status"] = entry.get("Status")
        resource["eip_provisioned_bandwidth"] = entry.get("Bandwidth")
        resource["eip_charge_type"] = entry.get("InternetChargeType")
        ctx["evidence"].append(
            "[API] EIP %s status=%s, provisioned bandwidth=%s Mbit/s, metering=%s"
            % (entry.get("IpAddress"), entry.get("Status"), entry.get("Bandwidth"),
               entry.get("InternetChargeType"))
        )
    else:
        ctx["evidence"].append(
            "[API] no EIP allocated in %s for this resource: it is reached through a fixed "
            "public address" % args.region_id
        )

    if args.mtr_file:
        lines, read_error = read_raw_text(args.mtr_file)
        if read_error:
            ctx["gaps"].append("raw MTR evidence missing: %s" % read_error)
        else:
            addresses = [args.public_ip, args.eip, resource.get("eip"), args.target_desc]
            addresses += resource.get("public_ips") or []
            ctx["probes"].append(mtr_facts(lines, addresses))
            ctx["evidence"].append(
                "[CUSTOMER] raw MTR attached from %s (text preserved verbatim, not rewritten)"
                % os.path.basename(args.mtr_file)
            )

    if args.check_target_region:
        payload, avail_error = describe_availability(
            normalize_region(args.check_target_region), args.instance_type, args.zone_id
        )
        target = normalize_region(args.check_target_region)
        if avail_error is not None:
            note_auth_gap(ctx, "ecs", "DescribeAvailableResource", avail_error)
        else:
            ctx["availability"] = read_availability(payload, target)
            ctx["evidence"].append(
                "[API] DescribeAvailableResource for %s: %s"
                % (target, ctx["availability"]["detail"])
            )

    for note in args.customer_note:
        ctx["evidence"].append("[CUSTOMER] verbatim: %s" % note)
    return ctx


def handoff_for(key):
    for entry in HANDOFFS:
        if entry["key"] == key:
            return entry
    return None


def classify_geography(args, ctx):
    """Return True / False / None for 'does this pair cross the border'."""
    instance_side = ctx["instance_side"]
    if instance_side == "unknown":
        return None
    if args.direction == "inbound":
        far_side = args.source_side
    elif args.direction == "outbound":
        far_side = args.target_side
    else:
        far_side = "unknown"
    if far_side == "unknown" and args.source_location:
        far_side = side_from_text(args.source_location)
    if far_side == "unknown" and args.target_desc:
        far_side = side_from_text(args.target_desc)
    ctx["far_side"] = far_side
    if far_side == "unknown":
        return None
    server_overseas = is_overseas_side(instance_side)
    far_overseas = is_overseas_side(far_side)
    if server_overseas == far_overseas:
        return False
    return True


def decide(ctx, args):
    """Return (branch, detail, confidence)."""
    evidence = set(args.evidence)
    resource = ctx["resource"]

    if not resource.get("resolved"):
        if any("not under the queried account" in item for item in ctx["evidence"]):
            return BRANCH_CROSS_ACCOUNT, (
                "the address or id given does not belong to the account used for this query"
            ), "confirmed"
        return BRANCH_INSUFFICIENT, (
            "no cloud-side reading was possible, so no attribution is attempted"
        ), "unknown"

    for key, response in OTHER_TIER_RESPONSES.items():
        if key in evidence:
            if "wording" in response:
                return BRANCH_HANDOFF, response["wording"], "confirmed"
            entry = handoff_for(response["handoff"])
            return BRANCH_HANDOFF, (entry or {}).get("wording", response["handoff"]), "confirmed"

    status = resource.get("status")
    if status and status != "Running":
        entry = handoff_for("instance-state")
        return BRANCH_INSTANCE_STATE, "instance status is %s; %s" % (
            status, (entry or {}).get("wording", "")), "confirmed"

    if "bandwidth-saturated" in evidence:
        entry = handoff_for("bandwidth")
        return BRANCH_BANDWIDTH_LIMIT, (
            "outbound throughput is pinned at the provisioned limit, which is a local "
            "capacity ceiling rather than a path problem; %s"
            % ((entry or {}).get("wording", ""))
        ), "probable"

    cross_border = classify_geography(args, ctx)
    ctx["cross_border"] = cross_border

    if cross_border is False:
        return BRANCH_NOT_CROSS_BORDER, (
            "both endpoints are on the same side of the border, so the cross-border "
            "hypothesis does not apply here"
        ), "confirmed"

    if cross_border is None:
        return BRANCH_INSUFFICIENT, (
            "the geography of the two endpoints is not established, so no attribution is "
            "attempted"
        ), "unknown"

    markers = [marker for marker in FORWARDING_MARKERS if marker in evidence]
    decisive = [marker for marker in markers if marker != "overseas-users-normal"]
    if len(decisive) >= 2:
        return BRANCH_FORWARDING_FAULT, "markers present: %s" % ", ".join(markers), "probable"

    if "mainland-nodes-fail-overseas-ok" in evidence:
        detail = CONGESTION_EXPLANATION
        if "eip-change-no-help" in evidence:
            detail = "%s %s" % (detail, NEW_IP_STATEMENT)
        if "partial-isp-only" in evidence:
            detail = "%s %s" % (detail, IP_DIFFERENCE_STATEMENT)
        return BRANCH_BORDER_CONGESTION, detail, "probable"

    if "server-side-clean" in evidence and "overseas-users-normal" in evidence:
        return BRANCH_BORDER_CONGESTION, CONGESTION_EXPLANATION, "probable"

    if args.direction == "outbound":
        return BRANCH_REGULATORY_BOUNDARY, (
            "a mainland instance is reaching an overseas endpoint, which is a regulated "
            "direction as well as a congested one"
        ), "probable"

    if "partial-isp-only" in evidence:
        return BRANCH_CARRIER_POLICY, (
            "only selected cities or carriers are affected while the rest are clean"
        ), "probable"

    return BRANCH_INSUFFICIENT, (
        "the cross-border path is in scope, but the observed facts do not yet separate "
        "congestion from a forwarding fault"
    ), "unknown"


def build_options(ctx, args, branch):
    options = []
    if branch == BRANCH_BORDER_CONGESTION:
        if args.direction == "outbound":
            options.append(OPTION_BY_SIDE["outbound_from_mainland"])
            options.append(OPTION_BY_SIDE["outbound_landing_near_users"])
        elif args.user_base == "mainland":
            options.append(OPTION_BY_SIDE["inbound_mainland_users_overseas_server"])
            options.append(OPTION_BY_SIDE["outbound_from_mainland"])
        elif args.user_base == "overseas":
            options.append(OPTION_BY_SIDE["inbound_overseas_users"])
        else:
            options.append(
                "Decide by where the users are: a mainland user base points to a mainland "
                "instance, an overseas user base points to an overseas region close to them. "
                "Either way the cross-border hop disappears for most traffic."
            )
    elif branch == BRANCH_FORWARDING_FAULT:
        options.append(
            "Escalate with the pack below: platform egress, NAT mapping, and BGP "
            "announcement are not visible to read-only instance APIs."
        )
    elif branch == BRANCH_CARRIER_POLICY:
        options.append(
            "Report the address and the affected cities to the carrier of the affected "
            "clients and escalate in parallel; a lifted block is confirmed only by a fresh "
            "test from that city."
        )
    elif branch == BRANCH_REGULATORY_BOUNDARY:
        options.append(
            "State the boundary as it is: outbound access from a mainland instance to an "
            "overseas endpoint is regulated and cannot simply be opened on request. The "
            "legitimate routes are an overseas instance near the target, or Global "
            "Accelerator: %s" % DOC_LINKS["global-accelerator-scenarios"]
        )
    elif branch == BRANCH_BANDWIDTH_LIMIT:
        options.append(
            "Compare the peak metering curve against the provisioned limit; if the ceiling "
            "is real, treat it as a capacity decision rather than a link fault."
        )
    if branch in (BRANCH_BORDER_CONGESTION, BRANCH_REGULATORY_BOUNDARY,
                  BRANCH_CARRIER_POLICY, BRANCH_FORWARDING_FAULT):
        options.append(
            "Public dial test from several mainland and several overseas nodes against the "
            "same address and port, repeated after any change: %s" % DOC_LINKS["dial-test"]
        )
        options.append(
            "MTR procedure, bidirectional with raw output preserved: %s"
            % DOC_LINKS["mtr-guide"]
        )
    return options


def escalation_pack(ctx, args):
    resource = ctx["resource"]
    addresses = [value for value in [
        resource.get("eip"), args.eip, args.public_ip
    ] + (resource.get("public_ips") or []) if value]
    return [
        ("Resource", resource.get("instance_id") or "not resolved"),
        ("Region / zone", "%s / %s" % (args.region_id or "-", resource.get("zone_id") or "-")),
        ("Public address", ", ".join(dict.fromkeys(addresses)) or "-"),
        ("Instance status", resource.get("status") or "-"),
        ("EIP status / provisioned bandwidth", "%s / %s Mbit/s" % (
            resource.get("eip_status") or "-",
            resource.get("eip_provisioned_bandwidth") or resource.get("eip_bandwidth") or "-")),
        ("Security groups", ", ".join(resource.get("security_groups") or []) or "-"),
        ("Symptom / direction", "%s / %s" % (args.symptom, args.direction)),
        ("Affected source", args.source_location or "-"),
        ("Affected target", args.target_desc or "-"),
        ("Error text", args.error_string or "-"),
        ("Fault window", args.time_window or "not provided"),
        ("Recorded reproduction", " / ".join(sorted(set(args.evidence))) or "not provided"),
        ("Raw probes", "attached" if args.mtr_file
         else "NOT attached - the reviewer needs raw output, not a summary"),
    ]


def checklist_lines():
    lines = []
    for entry in EVIDENCE_CHECKLIST:
        lines.append("- (%s) %s" % (entry["who"], entry["item"]))
        lines.append("      how: %s" % entry["how"])
        lines.append("      nature: %s" % entry["nature"])
    return lines


def scope_lines():
    lines = []
    for product, action in READ_SCOPE:
        lines.append(
            "- %s %s (version %s, read-only, RAM action %s)"
            % (product, action, API_VERSIONS.get(product, "-"), ram_action_for(product, action))
        )
    return lines


def compute_status(ctx, branch, missing):
    resolved = ctx["resource"].get("resolved")
    if ctx["api_failures"] and not resolved and not ctx["evidence"]:
        return STATUS_FAIL
    if missing or ctx["gaps"] or ctx["api_failures"] or branch == BRANCH_INSUFFICIENT:
        return STATUS_DEGRADED
    if not ctx["evidence"]:
        return STATUS_DEGRADED
    return STATUS_OK


def render(ctx, args, branch, detail, confidence, missing, status):
    out = []
    out.append("STATUS: %s" % status)
    out.append("SESSION: %s" % SESSION_ID)
    out.append("USER_AGENT: %s" % USER_AGENT)
    if ctx.get("owner"):
        out.append("QUERY_TARGET: %s" % ctx["owner"])
    out.append("")
    out.append("== 1. VERDICT ==")
    out.append("headline: %s" % VERDICT_HEADLINE.get(branch, branch))
    out.append("branch: %s" % branch)
    out.append("confidence: %s" % confidence)
    out.append("detail: %s" % detail)
    out.append("geography: instance side=%s, far side=%s, cross-border=%s"
               % (ctx.get("instance_side"), ctx.get("far_side"), ctx.get("cross_border")))
    out.append("")
    out.append("read-only scope used for this run:")
    out.extend(scope_lines())

    out.append("")
    out.append("== 2. EVIDENCE ==")
    out.extend(["- %s" % item for item in ctx["evidence"]] or ["- none collected"])
    if ctx["probes"]:
        out.append("mechanical facts about the attached capture (not an interpretation):")
        for probe in ctx["probes"]:
            out.extend(["  - %s" % line for line in probe])

    out.append("")
    out.append("== 3. GAPS ==")
    gaps = ["required input missing: %s" % item for item in missing] + ctx["gaps"]
    if ctx["api_failures"]:
        gaps.append("read-only query failures: %s" % "; ".join(ctx["api_failures"]))
    gaps.extend(ctx["notes"])
    out.extend(["- %s" % gap for gap in gaps] or ["- none"])

    out.append("")
    out.append("== 4. HOW TO CLOSE THE GAPS ==")
    out.append("every item below is run by the customer or a human engineer, never by this skill")
    out.extend(checklist_lines())

    out.append("")
    out.append("== 5. RECOMMENDED OPTIONS ==")
    if ctx.get("availability"):
        availability = ctx["availability"]
        out.append("- stock check for %s: %s (%s)"
                   % (availability["region"], availability["verdict"], availability["detail"]))
    elif branch in (BRANCH_BORDER_CONGESTION, BRANCH_REGULATORY_BOUNDARY):
        out.append("- before recommending a migration region, validate stock with "
                   "--check-target-region <region-id> --instance-type <type>; not run yet")
    options = build_options(ctx, args, branch)
    out.extend(["- %s" % option for option in options]
               or ["- no option is emitted until the branch is settled"])
    out.append("- the links above are the only permitted reference set for this skill; %s"
               % LINK_DISCLAIMER)

    out.append("")
    out.append("== 6. NOT GUARANTEED ==")
    if branch in (BRANCH_BORDER_CONGESTION, BRANCH_CARRIER_POLICY,
                  BRANCH_REGULATORY_BOUNDARY, BRANCH_FORWARDING_FAULT):
        out.append("- %s" % CONGESTION_WAIVER)
        out.append("- %s" % RECOVERY_STATEMENT)
    out.append("- %s" % NO_GUARANTEE_STATEMENT)
    out.append("- this run changed nothing and executed nothing inside the guest")

    if branch == BRANCH_FORWARDING_FAULT:
        out.append("")
        out.append("== 7. ESCALATION PACK ==")
        out.append("paste this block into the ticket for the network reviewer, with the raw "
                   "output attached")
        out.extend(["- %s: %s" % (label, value) for label, value in escalation_pack(ctx, args)])

    handoff = handoff_text(ctx, args, branch)
    if handoff:
        out.append("")
        out.append("== 8. HANDOFF ==")
        out.append("- %s" % handoff)

    out.append("")
    out.append("NEXT_ACTION: %s" % next_action(ctx, args, branch, status, missing))
    return "\n".join(out)


def handoff_text(ctx, args, branch):
    if branch == BRANCH_HANDOFF:
        return None
    if branch == BRANCH_CROSS_ACCOUNT:
        return (
            "Only resources under the account used for the query can be inspected here. Ask "
            "the owning account to open the request, or rerun authenticated as that account."
        )
    if branch == BRANCH_NOT_CROSS_BORDER:
        entry = handoff_for("web-access")
        return ("The pair does not cross the border; work the symptom at the layer where it "
                "shows: %s" % (entry or {}).get("target", ""))
    if branch == BRANCH_BANDWIDTH_LIMIT:
        return (entry_wording("bandwidth"))
    if branch == BRANCH_INSTANCE_STATE:
        return entry_wording("instance-state")
    return None


def entry_wording(key):
    entry = handoff_for(key)
    return (entry or {}).get("wording", "")


def next_action(ctx, args, branch, status, missing):
    if missing:
        return "collect these inputs in one reply, then rerun: %s" % ", ".join(missing)
    if status == STATUS_FAIL:
        return ("restore read access: have the customer run `aliyun sts get-caller-identity` locally, then "
                "attach the actions listed in references/ram-policies.md")
    if branch == BRANCH_FORWARDING_FAULT:
        return ("send the escalation pack plus raw MTR and dial-test output to a human "
                "network reviewer; stop asking the customer for repeated self-checks")
    if branch == BRANCH_BORDER_CONGESTION:
        return ("send the congestion explanation, the option set matched to where the users "
                "are, and the no-guarantee statement; re-test from multiple nodes once the "
                "customer picks an option")
    if branch == BRANCH_CARRIER_POLICY:
        return "open the carrier report and the human escalation in parallel"
    if branch == BRANCH_INSUFFICIENT:
        return ("collect bidirectional raw MTR and a multi-node dial test before any "
                "attribution is offered")
    if branch in (BRANCH_HANDOFF, BRANCH_NOT_CROSS_BORDER, BRANCH_BANDWIDTH_LIMIT,
                  BRANCH_INSTANCE_STATE, BRANCH_CROSS_ACCOUNT):
        return "hand off with the wording in section 8 and retire the cross-border hypothesis"
    return "review the report with the customer and agree the next test"


def as_json(ctx, args, branch, detail, confidence, missing, status):
    return {
        "status": status,
        "session_id": SESSION_ID,
        "user_agent": USER_AGENT,
        "owner": ctx.get("owner"),
        "region_id": args.region_id,
        "region_label": ctx.get("region_label"),
        "instance_side": ctx.get("instance_side"),
        "far_side": ctx.get("far_side"),
        "cross_border": ctx.get("cross_border"),
        "branch": branch,
        "headline": VERDICT_HEADLINE.get(branch, branch),
        "detail": detail,
        "confidence": confidence,
        "read_only_scope": [
            {
                "product": product,
                "action": action,
                "version": API_VERSIONS.get(product),
                "ram_action": ram_action_for(product, action),
            }
            for product, action in READ_SCOPE
        ],
        "resource": ctx.get("resource"),
        "evidence": ctx.get("evidence"),
        "probe_facts": ctx.get("probes"),
        "gaps": ctx.get("gaps"),
        "missing_inputs": missing,
        "api_failures": ctx.get("api_failures"),
        "options": build_options(ctx, args, branch),
        "availability": ctx.get("availability"),
        "escalation_pack": escalation_pack(ctx, args)
        if branch == BRANCH_FORWARDING_FAULT else None,
        "evidence_checklist": [dict(entry) for entry in EVIDENCE_CHECKLIST],
        "not_guaranteed": [CONGESTION_WAIVER, NO_GUARANTEE_STATEMENT],
        "handoff": handoff_text(ctx, args, branch),
        "next_action": next_action(ctx, args, branch, status, missing),
    }


def _run_selftest():
    """Offline boundary locks for the geography-decision layer.

    ``classify_geography`` decides whether the two endpoints cross the border --
    the single hinge the whole ``decide`` branch selection hangs on -- and must
    return None (never guess) when either side is unknown. ``label_region``
    encodes the mainland/overseas split including the cn-hongkong exception
    (overseas_direction, not mainland) and the ``cn-*`` fallback, and
    ``side_from_text`` must return unknown for ambiguous text naming both sides.
    A wrong verdict routes the customer to the opposite remediation. Pure logic
    only - no cloud, no credentials.
    """
    rc = 0

    def expect(name, cond):
        nonlocal rc
        if cond:
            print("PASS {0}".format(name))
        else:
            print("FAIL {0}".format(name))
            rc = 1

    # --- normalize_region: separators + aliases; unmatched passes through
    expect("nr_underscore_to_dash", normalize_region("cn_hangzhou") == "cn-hangzhou")
    expect("nr_trim", normalize_region("  cn-shanghai  ") == "cn-shanghai")
    expect("nr_alias", normalize_region("hongkong") == "cn-hongkong")
    expect("nr_empty_none", normalize_region("") is None and normalize_region(None) is None)

    # --- label_region: known map, cn-hongkong special, cn-* fallback, unknown
    expect("lr_known_mainland", label_region("cn-hangzhou")[1] == "mainland")
    expect("lr_hongkong_is_overseas_direction", label_region("cn-hongkong")[1] == "overseas_direction")
    expect("lr_overseas_region", label_region("us-west-1")[1] == "overseas")
    expect("lr_cn_prefix_fallback", label_region("cn-somewhere")[1] == "mainland")
    expect("lr_unknown_side", label_region("nowhere-region")[1] == "unknown")
    expect("lr_empty_unknown", label_region("") == ("unknown", "unknown"))

    # --- is_overseas_side: overseas and overseas_direction both count
    expect("ios_overseas", is_overseas_side("overseas") is True)
    expect("ios_overseas_direction", is_overseas_side("overseas_direction") is True)
    expect("ios_mainland_false", is_overseas_side("mainland") is False)
    expect("ios_unknown_false", is_overseas_side("unknown") is False)

    # --- side_from_text: single-side only; ambiguous / empty -> unknown
    expect("sft_mainland", side_from_text("Beijing, mainland China") == "mainland")
    expect("sft_overseas", side_from_text("Singapore") == "overseas")
    expect("sft_ambiguous_unknown", side_from_text("from Shanghai to Singapore") == "unknown")
    expect("sft_empty_unknown", side_from_text("") == "unknown" and side_from_text(None) == "unknown")

    # --- classify_geography: the cross-border hinge (True / False / None)
    class _Args:
        def __init__(self, direction, source_side, target_side, source_location="", target_desc=""):
            self.direction = direction
            self.source_side = source_side
            self.target_side = target_side
            self.source_location = source_location
            self.target_desc = target_desc

    def geo(instance_side, args):
        return classify_geography(args, {"instance_side": instance_side})

    expect("geo_instance_unknown_none",
           geo("unknown", _Args("inbound", "overseas", "unknown")) is None)
    expect("geo_crosses_true",
           geo("mainland", _Args("inbound", "overseas", "unknown")) is True)
    expect("geo_same_side_false",
           geo("mainland", _Args("inbound", "mainland", "unknown")) is False)
    expect("geo_outbound_crosses_true",
           geo("overseas", _Args("outbound", "unknown", "mainland")) is True)
    # overseas_direction (cn-hongkong server) vs a mainland peer still crosses
    expect("geo_hongkong_vs_mainland_crosses",
           geo("overseas_direction", _Args("outbound", "unknown", "mainland")) is True)
    expect("geo_far_unknown_none",
           geo("mainland", _Args("inbound", "unknown", "unknown")) is None)
    # unknown far_side is inferred from free-text source_location
    expect("geo_infers_from_source_location",
           geo("mainland", _Args("inbound", "unknown", "unknown", source_location="Tokyo Japan")) is True)

    print("SELFTEST: {0}".format("PASS" if rc == 0 else "FAIL"))
    return rc


def exit_code_for(status: str) -> int:
    """SKILL.md contract: 0 when a conclusion exists (OK or DEGRADED), 1 on FAIL.

    2026-10-21 scene evidence: a DEGRADED conclusion (resource not under the
    queried account) exited 2, so the agent read it as a usage error, abandoned
    the area and hand-built raw CLI calls until the leg timed out.
    """
    return 0 if status in (STATUS_OK, STATUS_DEGRADED) else 1


assert exit_code_for(STATUS_OK) == 0
assert exit_code_for(STATUS_DEGRADED) == 0
assert exit_code_for(STATUS_FAIL) == 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    notes = []
    missing = validate(args, notes)
    ctx = gather(args)
    ctx["notes"] = notes
    branch, detail, confidence = decide(ctx, args)
    status = compute_status(ctx, branch, missing)
    if args.format == "json":
        payload = as_json(ctx, args, branch, detail, confidence, missing, status)
        text = json.dumps(payload, indent=2, default=str, ensure_ascii=False)
    else:
        text = render(ctx, args, branch, detail, confidence, missing, status)
    print(mask_secrets(text))
    return exit_code_for(status)


if __name__ == "__main__":
    sys.exit(main())
