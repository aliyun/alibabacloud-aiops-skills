#!/usr/bin/env python3
"""
idc_address_query.py -- SINGLE read-only entry point for the skill.
===================================================================
Resolves an ECS instance (by instance id) or a public IP to its region,
availability zone, and the public CITY-LEVEL location of that region, then
states the confidentiality boundary. It performs ONLY Describe* / STS read
calls. It NEVER runs any command inside the instance and NEVER invents a
district/street-level data-center address, a facility name or a rack position.

The agent MUST run this entry script; it MUST NOT hand-compose aliyun
commands. Every cloud read flows through scripts/_cli.py (timeout, retry,
credential masking, observability User-Agent).

Output contract: the report ends with a machine-checkable
    STATUS: OK | DEGRADED | FAIL
    NEXT_ACTION: <human guidance or "None">
"""

import argparse
import json
import sys

from _cli import CliError, make_session_id, run_cli
from _constants import (
    CONFIDENTIALITY_NOTICE,
    CROSS_ACCOUNT_NOTICE,
    DATA_SAFETY_REMINDER,
    HANDOFF_RULES,
    INPUT_GUIDANCE,
    MAX_IDS_PER_CALL,
    MAX_PAGES,
    REGION_CITY_MAP,
    RELEASED_INSTANCE_NOTICE,
    SKILL_NAME,
    STATUS_PAGE_SIZE,
    TICKET_GUIDANCE,
    ZONE_STATUS_MEANINGS,
)
from sts_token import caller_uid, get_caller_identity


# ---------------------------------------------------------------------------
# Small response helpers (only reference documented DescribeInstances fields)
# ---------------------------------------------------------------------------

def _public_ips(instance):
    ips = []
    pub = instance.get("PublicIpAddress") or {}
    for ip in pub.get("IpAddress") or []:
        if ip:
            ips.append(ip)
    eip = instance.get("EipAddress") or {}
    if eip.get("IpAddress"):
        ips.append(eip["IpAddress"])
    return ips


def _private_ips(instance):
    ips = []
    inner = instance.get("InnerIpAddress") or {}
    for ip in inner.get("IpAddress") or []:
        if ip:
            ips.append(ip)
    vpc = instance.get("VpcAttributes") or {}
    priv = vpc.get("PrivateIpAddress") or {}
    for ip in priv.get("IpAddress") or []:
        if ip:
            ips.append(ip)
    return ips


def _public_location(region_id):
    """City-level public name for a region, or an honest fallback. Never a
    guessed district/street address."""
    city = REGION_CITY_MAP.get(region_id)
    if city:
        return "%s (public city-level name of region %s)" % (city, region_id)
    return ("%s (this region is not in the embedded public city-level table; "
            "only the raw region id is reported, no location is inferred)"
            % region_id)


# ---------------------------------------------------------------------------
# Read-only ECS queries (paginated)
# ---------------------------------------------------------------------------

def describe_instances(region, base_params, session_id, warnings):
    """Return the list of Instance dicts for one region, following pages."""
    collected = []
    page = 1
    while page <= MAX_PAGES:
        params = dict(base_params)
        params["RegionId"] = region
        params["PageSize"] = 100
        params["PageNumber"] = page
        try:
            body = run_cli("ecs", "DescribeInstances", params=params,
                           region=region, session_id=session_id)
        except CliError as exc:
            warnings.append("DescribeInstances region=%s page=%d -> %s"
                            % (region, page, exc))
            break
        block = body.get("Instances") or {}
        page_items = block.get("Instance") or []
        collected.extend(page_items)
        total = body.get("TotalCount")
        if not page_items:
            break
        if isinstance(total, int) and len(collected) >= total:
            break
        if len(page_items) < 100:
            break
        page += 1
    return collected


def enrich_status(region, instance_ids, session_id, warnings):
    """Call DescribeInstanceStatus to confirm lifecycle status; returns map."""
    status_map = {}
    if not instance_ids:
        return status_map
    params = {"RegionId": region, "PageSize": STATUS_PAGE_SIZE}
    for idx, iid in enumerate(instance_ids[:STATUS_PAGE_SIZE], start=1):
        params["InstanceId.%d" % idx] = iid
    try:
        body = run_cli("ecs", "DescribeInstanceStatus", params=params,
                       region=region, session_id=session_id)
    except CliError as exc:
        warnings.append("DescribeInstanceStatus region=%s -> %s" % (region, exc))
        return status_map
    block = body.get("InstanceStatuses") or {}
    for item in block.get("InstanceStatus") or []:
        if item.get("InstanceId"):
            status_map[item["InstanceId"]] = item.get("Status", "Unknown")
    return status_map


def locate(instance_ids, public_ips, regions, session_id, warnings):
    """Scan regions for the requested ids and IPs. Returns (found, missing_ids,
    missing_ips). Each found entry is (instance_dict, matched_by) where
    matched_by is ('id', value) or ('ip', value)."""
    pending_ids = list(dict.fromkeys(instance_ids))
    pending_ips = list(dict.fromkeys(public_ips))
    found = []

    for region in regions:
        if not pending_ids and not pending_ips:
            break

        if pending_ids:
            params = {"InstanceIds": json.dumps(pending_ids[:MAX_IDS_PER_CALL])}
            items = describe_instances(region, params, session_id, warnings)
            hit = set()
            for inst in items:
                iid = inst.get("InstanceId")
                if iid in pending_ids:
                    found.append((inst, ("id", iid)))
                    hit.add(iid)
            pending_ids = [i for i in pending_ids if i not in hit]

        if pending_ips:
            params = {"PublicIpAddresses": ",".join(pending_ips)}
            items = describe_instances(region, params, session_id, warnings)
            hit = set()
            for inst in items:
                pubs = _public_ips(inst)
                matched = [ip for ip in pubs if ip in pending_ips]
                if matched:
                    found.append((inst, ("ip", ", ".join(matched))))
                    hit.update(matched)
            pending_ips = [ip for ip in pending_ips if ip not in hit]

    return found, pending_ids, pending_ips


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def _print_header(uid, session_id):
    print("==== %s (READ-ONLY) ====" % SKILL_NAME)
    print("Account UID : %s" % uid)
    print("Session     : %s" % session_id)
    print("Scope       : read-only location lookup; no changes were made.")
    print()


def _print_confidentiality():
    print("DISCLOSURE BOUNDARY AND SAFE USE")
    for line in (CONFIDENTIALITY_NOTICE, DATA_SAFETY_REMINDER, TICKET_GUIDANCE):
        print("  - %s" % line)
    print()


def report_location(uid, session_id, found, missing_ids, missing_ips,
                    regions, warnings, show_status):
    _print_header(uid, session_id)

    status_by_region = {}
    if show_status and found:
        grouped = {}
        for inst, _ in found:
            grouped.setdefault(inst.get("RegionId"), []).append(inst.get("InstanceId"))
        for region, ids in grouped.items():
            status_by_region.update(enrich_status(region, ids, session_id, warnings))

    print("RESULT")
    if not found:
        print("  No matching resource found under this account.")
    for inst, matched_by in found:
        iid = inst.get("InstanceId", "unknown")
        region = inst.get("RegionId", "unknown")
        zone = inst.get("ZoneId", "unknown")
        api_status = inst.get("Status", "Unknown")
        live_status = status_by_region.get(iid, api_status) if show_status else api_status
        kind, value = matched_by
        pub = ", ".join(_public_ips(inst)) or "none"
        priv = ", ".join(_private_ips(inst)) or "none"
        print("  [%s=%s]" % (kind, value))
        print("     Instance ID     : %s" % iid)
        print("     Region / Zone   : %s / %s" % (region, zone))
        print("     Status          : %s" % live_status)
        print("     Public location : %s" % _public_location(region))
        print("     Public IPs      : %s" % pub)
        print("     Private IPs     : %s" % priv)
        print()

    if missing_ids or missing_ips:
        print("NOT FOUND UNDER THIS ACCOUNT (searched %d region(s))" % len(regions))
        for iid in missing_ids:
            print("  instance id %s" % iid)
        for ip in missing_ips:
            print("  public IP %s" % ip)
        for line in (CROSS_ACCOUNT_NOTICE.format(uid=uid), RELEASED_INSTANCE_NOTICE):
            print("  - %s" % line)
        print()

    _print_confidentiality()

    if warnings:
        print("DEGRADED CHECKS")
        for w in warnings:
            print("  [WARN] %s" % w)
        print()

    if found and not warnings:
        print("STATUS: OK")
    elif found:
        print("STATUS: DEGRADED")
    elif warnings:
        print("STATUS: DEGRADED")
    else:
        print("STATUS: DEGRADED")

    if found:
        print("NEXT_ACTION: For a district/street-level address, facility name "
              "or rack position, open a support ticket from the owning account; "
              "this tool stays at the city-level public boundary.")
    else:
        print("NEXT_ACTION: Confirm the identifier, or open a support ticket "
              "from the account that owns the resource; if the instance was "
              "released, historical location is not queryable here.")


def report_availability(uid, session_id, region, destination_resource,
                        items, warnings):
    _print_header(uid, session_id)
    print("ZONE AVAILABILITY (public information, read-only)")
    print("  Region              : %s" % region)
    print("  DestinationResource : %s" % destination_resource)
    if not items:
        print("  (no zone rows returned)")
    for z in items:
        zid = z.get("ZoneId", "unknown")
        status = z.get("Status", "unknown")
        category = z.get("StatusCategory", "")
        meaning = ZONE_STATUS_MEANINGS.get(category, "")
        extra = " (%s)" % meaning if meaning else ""
        print("  zone=%s status=%s category=%s%s" % (zid, status, category, extra))
    print()

    if warnings:
        print("DEGRADED CHECKS")
        for w in warnings:
            print("  [WARN] %s" % w)
        print()

    print("STATUS: %s" % ("DEGRADED" if warnings else "OK"))
    print("NEXT_ACTION: Availability and stock are public; physical "
          "data-center addresses remain confidential via the ticket channel.")


def print_handoff():
    print("HANDOFF MATRIX (adjacent requests are routed, never answered here)")
    for rule in HANDOFF_RULES:
        print("  request: %s" % rule["request"])
        print("     route -> %s" % rule["route_to"])
        print("     reply : %s" % rule["sentence"])
    print()


# ---------------------------------------------------------------------------
# Availability mode
# ---------------------------------------------------------------------------

def run_availability(args, session_id, uid):
    warnings = []
    params = {"RegionId": args.region, "DestinationResource": args.destination_resource}
    if args.zone_id:
        params["ZoneId"] = args.zone_id
    try:
        body = run_cli("ecs", "DescribeAvailableResource", params=params,
                       region=args.region, session_id=session_id)
    except CliError as exc:
        warnings.append("DescribeAvailableResource -> %s" % exc)
        body = {}
    block = body.get("AvailableZones") or {}
    items = block.get("AvailableZone") or []
    report_availability(uid, session_id, args.region,
                        args.destination_resource, items, warnings)
    return 0


# ---------------------------------------------------------------------------
# Argument parsing and main flow
# ---------------------------------------------------------------------------

def _split(values):
    out = []
    for raw in values or []:
        for part in str(raw).split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out


def build_parser():
    p = argparse.ArgumentParser(
        prog="idc_address_query.py",
        description="READ-ONLY ECS instance / public-IP location resolver. "
                    "Never returns or invents street-level addresses.")
    p.add_argument("--instance-id", action="append", default=[],
                   help="ECS instance id (i-...); repeatable or comma-separated")
    p.add_argument("--public-ip", action="append", default=[],
                   help="public IP address to resolve; repeatable or comma-separated")
    p.add_argument("--region", help="optional RegionId to narrow the search")
    p.add_argument("--no-status", action="store_true",
                   help="skip the DescribeInstanceStatus confirmation read")
    p.add_argument("--check-availability", action="store_true",
                   help="zone availability mode instead of location lookup")
    p.add_argument("--destination-resource", default="Zone",
                   help="DescribeAvailableResource DestinationResource "
                        "(default Zone lists per-zone availability; "
                        "SystemDisk, DataDisk and Network require additional "
                        "filters and may return Invalid.DestinationResource "
                        "without them)")
    p.add_argument("--zone-id", help="optional ZoneId filter for availability mode")
    p.add_argument("--show-handoff", action="store_true",
                   help="print the handoff matrix and exit")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    session_id = make_session_id()
    warnings = []

    if args.show_handoff:
        print("==== %s (READ-ONLY) ====" % SKILL_NAME)
        print_handoff()
        print("STATUS: OK")
        print("NEXT_ACTION: None")
        return 0

    # Credential preflight -> account uid for the cross-account wording.
    try:
        identity = get_caller_identity(session_id=session_id)
    except CliError as exc:
        sys.stderr.write("[WARN] STS get-caller-identity failed: %s\n" % exc)
        print("==== %s (READ-ONLY) ====" % SKILL_NAME)
        print("AUTH FAILED")
        print("  The read-only calls could not be authorized (NoPermission / "
              "ImplicitDeny) or no credential was resolved.")
        print("  Attach the minimal policy in references/ram-policies.md.")
        print("STATUS: FAIL")
        print("NEXT_ACTION: Configure credentials with 'aliyun configure' "
              "(default credential chain); never supply an access key id or "
              "secret to this tool. Then re-run.")
        return 2

    uid = caller_uid(identity)

    if args.check_availability:
        if not args.region:
            print("==== %s (READ-ONLY) ====" % SKILL_NAME)
            print("INPUT REQUIRED")
            print("  Availability mode needs --region.")
            print("STATUS: FAIL")
            print("NEXT_ACTION: Re-run with --region <region-id> "
                  "(and optionally --destination-resource / --zone-id).")
            return 2
        return run_availability(args, session_id, uid)

    instance_ids = _split(args.instance_id)
    public_ips = _split(args.public_ip)

    if not instance_ids and not public_ips:
        print("==== %s (READ-ONLY) ====" % SKILL_NAME)
        print("INPUT REQUIRED")
        print("  %s" % INPUT_GUIDANCE)
        print("STATUS: FAIL")
        print("NEXT_ACTION: Provide at least one ECS instance id (i-...) or a "
              "public IP, from the account that owns the resource, then re-run.")
        return 2

    regions = [args.region] if args.region else list(REGION_CITY_MAP)
    found, missing_ids, missing_ips = locate(
        instance_ids, public_ips, regions, session_id, warnings)

    report_location(uid, session_id, found, missing_ids, missing_ips,
                    regions, warnings, show_status=not args.no_status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
