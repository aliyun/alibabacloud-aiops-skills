#!/usr/bin/env python3
"""
lookup_console_resource.py -- single evidence entry point (read-only)
=====================================================================
SECURITY: This skill is strictly READ-ONLY. This script calls ONLY the
whitelisted read actions DescribeInstances / DescribeInstanceStatus /
DescribeAvailableResource (product ecs) and GetCallerIdentity (product sts),
via the shared CLI layer; no other API is reachable from it. It never runs
anything inside a guest OS, never changes cloud resources, and never touches
key material (default credential chain only).

What it answers:
  * FIND (default): an instance (or name/IP) is missing from the console ->
    sweep DescribeInstances region by region and report exactly where it
    exists, with its control-plane status, charge type and lock state.
  * STATUS: cross-check DescribeInstanceStatus against DescribeInstances for
    the found ids, and against the status the customer sees (--console-claims).
  * AVAILABILITY (--availability): is a region/resource visible to this
    account on the buy side (DescribeAvailableResource), for "the region is
    not selectable" tickets.

Contract: plain-text sections + closing `STATUS: OK|DEGRADED|FAIL` and
`NEXT_ACTION: ...` lines (JSON with --json). Exit 0 = OK/DEGRADED, 1 = FAIL.
Per-region failures are logged `[WARN]` and the sweep continues.

Usage examples:
    python3 scripts/areas/console_resource_lookup/lookup_console_resource.py --instance-ids i-xxx,i-yyy
    python3 scripts/areas/console_resource_lookup/lookup_console_resource.py --instance-name web-01 \
        --region-hint cn-shenzhen
    python3 scripts/areas/console_resource_lookup/lookup_console_resource.py --public-ip 203.0.113.10
    python3 scripts/areas/console_resource_lookup/lookup_console_resource.py --availability \
        --availability-region cn-beijing --destination-resource InstanceType
"""

from __future__ import annotations

import argparse
import json
import sys

import _cli
from _cli import CliError
from _constants import (
    AVAILABILITY_NOTE,
    CHARGE_TYPE_NOTE,
    CLI_TIMEOUT,
    DEFAULT_SWEEP_REGIONS,
    DESTINATION_RESOURCES,
    ECS_PRODUCT,
    ENTRY_MAP,
    INSTANCE_STATUS_MEANING,
    INTAKE_QUESTIONS,
    LOCK_REASON_MEANING,
    MAX_INSTANCE_IDS,
    MAX_PAGES,
    MAX_SWEEP_REGIONS,
    NOT_FOUND_FOLLOWUPS,
    PAGE_SIZE,
    SKILL_NAME,
    STATUS_SYNC_NOTE,
)

_STATUS_CODES = ("nopermission", "invalidaccesskey", "signaturedoesnotmatch",
                 "implicitdeny", "unauthorized")


def _split_csv(value):
    return [p.strip() for p in (value or "").split(",") if p.strip()]


def _instance_list(body):
    insts = body.get("Instances")
    if isinstance(insts, dict):
        inner = insts.get("Instance")
        return inner if isinstance(inner, list) else []
    return []


def _dig_words(inst, key):
    """PublicIpAddresses/InnerIpAddress shapes: {"X": ["1.2.3.4"]}."""
    node = inst.get(key)
    if isinstance(node, dict):
        for value in node.values():
            if isinstance(value, list) and value:
                return ", ".join(str(v) for v in value)
    if isinstance(node, list) and node:
        return ", ".join(str(v) for v in node)
    return str(node or "")


def _lock_reasons(inst):
    locks = inst.get("OperationLocks")
    out = []
    if isinstance(locks, dict):
        for item in locks.get("LockReason") or []:
            if isinstance(item, dict):
                out.append(str(item.get("LockReason", "")))
            else:
                out.append(str(item))
    return [reason for reason in out if reason]


def _slim(inst, region):
    """Project one instance record onto the fields this skill reports."""
    eip = inst.get("EipAddress")
    eip_ip = str(eip.get("IpAddress") or "") if isinstance(eip, dict) else ""
    return {
        "region_id": region,
        "instance_id": str(inst.get("InstanceId", "")),
        "instance_name": str(inst.get("InstanceName", "")),
        "status": str(inst.get("Status", "")),
        "charge_type": str(inst.get("InstanceChargeType", "")),
        "instance_type": str(inst.get("InstanceType", "")),
        "public_ips": _dig_words(inst, "PublicIpAddresses"),
        "eip": eip_ip,
        "inner_ips": _dig_words(inst, "InnerIpAddress"),
        "resource_group_id": str(inst.get("ResourceGroupId", "")),
        "vpc_id": str(inst.get("VpcAttributes", {}).get("VpcId", "")
                      if isinstance(inst.get("VpcAttributes"), dict) else ""),
        "creation_time": str(inst.get("CreationTime", "")),
        "expired_time": str(inst.get("ExpiredTime", "")),
        "lock_reasons": _lock_reasons(inst),
    }


def _is_permission_error(code):
    low = (code or "").lower()
    return any(marker in low for marker in _STATUS_CODES)


def find_regions(regions, params, errors, fatal):
    """Sweep DescribeInstances over `regions`; return (hits, fatal_stop)."""
    hits = []
    for region in regions:
        page = 1
        while page <= MAX_PAGES:
            call_params = dict(params)
            call_params["RegionId"] = region
            call_params["PageSize"] = PAGE_SIZE
            call_params["PageNumber"] = page
            try:
                body = _cli.call(ECS_PRODUCT, "DescribeInstances",
                                 call_params, region=region,
                                 timeout=CLI_TIMEOUT)
            except CliError as err:
                errors.append({"region": region, "code": err.code,
                               "message": str(err)[:200]})
                if _is_permission_error(err.code):
                    fatal.append(
                        "credential lacks the read permission (see "
                        "references/ram-policies.md); the remaining regions "
                        "were not queried")
                    return hits, True
                break
            found = _instance_list(body)
            for inst in found:
                hits.append(_slim(inst, region))
            if len(found) < PAGE_SIZE:
                break
            page += 1
    return hits, False


def status_crosscheck(region_ids, instance_ids, errors):
    """DescribeInstanceStatus in the hit regions for the given ids."""
    reading = {}
    ids = instance_ids[:MAX_INSTANCE_IDS]
    for region in region_ids:
        params = {"RegionId": region, "PageSize": PAGE_SIZE}
        for offset, inst_id in enumerate(ids, start=1):
            params[f"InstanceId.{offset}"] = inst_id
        try:
            body = _cli.call(ECS_PRODUCT, "DescribeInstanceStatus", params,
                             region=region, timeout=CLI_TIMEOUT)
        except CliError as err:
            errors.append({"region": region, "action": "DescribeInstanceStatus",
                           "code": err.code, "message": str(err)[:200]})
            continue
        node = body.get("InstanceStatuses")
        items = []
        if isinstance(node, dict):
            inner = node.get("InstanceStatus")
            items = inner if isinstance(inner, list) else []
        for item in items:
            if isinstance(item, dict):
                reading[str(item.get("InstanceId", ""))] = {
                    "region_id": region,
                    "status": str(item.get("Status", "")),
                }
    return reading


def run_availability(args, errors):
    params = {
        "RegionId": args.availability_region,
        "DestinationResource": args.destination_resource,
        "InstanceChargeType": args.instance_charge_type,
        "InstanceType": args.instance_type,
        "ZoneId": args.zone_id,
        "ResourceType": args.resource_type,
    }
    try:
        body = _cli.call(ECS_PRODUCT, "DescribeAvailableResource", params,
                         region=args.availability_region, timeout=CLI_TIMEOUT)
    except CliError as err:
        errors.append({"region": args.availability_region,
                       "action": "DescribeAvailableResource",
                       "code": err.code, "message": str(err)[:200]})
        return None
    zones = []
    node = body.get("AvailableZones")
    items = node.get("AvailableZone") if isinstance(node, dict) else []
    for zone in items or []:
        if not isinstance(zone, dict):
            continue
        supported = []
        for res in (zone.get("AvailableResources", {}) or {}).get(
                "AvailableResource", []) or []:
            for sup in (res.get("SupportedResources", {}) or {}).get(
                    "SupportedResource", []) or []:
                if isinstance(sup, dict):
                    supported.append(
                        f"{sup.get('Value', '?')}:{sup.get('Status', '?')}")
        zones.append({"zone_id": str(zone.get("ZoneId", "")),
                      "status": str(zone.get("Status", "")),
                      "category": str(zone.get("StatusCategory", "")),
                      "supported": supported})
    return zones


def _compare_claim(claims, statuses):
    low = (claims or "").lower()
    matched = [sid for sid, st in statuses.items()
               if st.lower() in low or low in st.lower()]
    return matched


def main():
    parser = argparse.ArgumentParser(
        description="Read-only cross-region lookup and status cross-check "
                    "for ECS resources missing from the console.")
    parser.add_argument("--instance-ids", default="",
                        help="comma separated i-... ids")
    parser.add_argument("--instance-name", default="",
                        help="exact instance name filter")
    parser.add_argument("--public-ip", default="",
                        help="public IP address filter")
    parser.add_argument("--private-ip", default="",
                        help="private/intranet IP address filter")
    parser.add_argument("--resource-group-id", default="",
                        help="restrict the query to one resource group")
    parser.add_argument("--regions", default="",
                        help="comma separated region ids REPLACING the "
                             "default sweep list")
    parser.add_argument("--region-hint", default="",
                        help="comma separated regions queried FIRST")
    parser.add_argument("--status", default="",
                        help="instance status filter (e.g. Running) for a no-locator "
                             "listing; enables the bounded auto-attempt instead of a "
                             "hard failure")
    parser.add_argument("--all-regions", action="store_true",
                        help="with --status and no locator, sweep the default region "
                             "list instead of a single region")
    parser.add_argument("--console-claims", default="",
                        help="the status text the customer sees in the "
                             "console, for the display cross-check")
    parser.add_argument("--no-status-check", action="store_true",
                        help="skip the DescribeInstanceStatus cross-check")
    parser.add_argument("--availability", action="store_true",
                        help="run the buy-side availability mode instead")
    parser.add_argument("--availability-region", default="",
                        help="region for --availability (required with it)")
    parser.add_argument("--destination-resource", default="InstanceType",
                        help="availability destination resource: one of "
                             + "/".join(DESTINATION_RESOURCES))
    parser.add_argument("--instance-charge-type", default="",
                        help="optional PrePaid/PostPaid filter for "
                             "--availability")
    parser.add_argument("--instance-type", default="",
                        help="optional spec filter for --availability")
    parser.add_argument("--zone-id", default="",
                        help="optional zone filter for --availability")
    parser.add_argument("--resource-type", default="",
                        help="optional ResourceType filter for "
                             "--availability")
    parser.add_argument("--profile", default=None,
                        help="optional aliyun CLI profile name")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable output")
    args = parser.parse_args()
    _cli.check_cli_available()

    account_id = _cli.resolve_account_id(profile=args.profile)
    errors = []
    result = {
        "skill": SKILL_NAME,
        "account_id": account_id or "unresolved",
        "mode": "availability" if args.availability else "find",
        "regions_queried": [],
        "hits": [],
        "status_crosscheck": {},
        "console_claims_note": "",
        "availability": None,
        "errors": errors,
    }

    if args.availability:
        if not args.availability_region:
            _finish(result, args.json, "FAIL",
                    "ask for the target region of the availability check; "
                    "never guess a region id", vars(args))
            return 1
        zones = run_availability(args, errors)
        result["availability"] = zones or []
        result["regions_queried"] = [args.availability_region]
        if zones is None:
            _finish(result, args.json, "FAIL",
                    "the availability query failed; report the error code "
                    "and retry once the permission is fixed", vars(args))
            return 1
        status = "DEGRADED" if errors else "OK"
        if zones:
            action = ("the account CAN see sellable resources there; if the "
                      "buy page still hides the region, that is an "
                      "eligibility/UI question -- show the purchasable-"
                      "region page from the entry map and involve sales")
        else:
            action = ("no sellable resource visible for this account in that "
                      "region+filter; distinguish account eligibility "
                      "(real-name/overdue) from a genuinely closed sale -- "
                      "customized or campaign supply is sales-owned")
        _finish(result, args.json, status, action, vars(args))
        return 0

    ids = _split_csv(args.instance_ids)
    params = {}
    if ids:
        params["InstanceIds"] = json.dumps(ids)
    if args.instance_name:
        params["InstanceName"] = args.instance_name
    if args.public_ip:
        params["PublicIpAddresses"] = args.public_ip
    if args.private_ip:
        params["PrivateIpAddresses"] = args.private_ip
    if args.resource_group_id:
        params["ResourceGroupId"] = args.resource_group_id
    if not params:
        if not args.status:
            _finish(result, args.json, "FAIL",
                    "no locator given; rerun with --status Running for a labelled "
                    "one-region listing, or --status Running --all-regions for the "
                    "account-wide sweep; otherwise ask the customer the intake "
                    "questions (resource type, id/name/IP, region seen, account, "
                    "device)", vars(args))
            return 1
        # Bounded auto-attempt (P1-2): a "list my instances" question has no locator to
        # give, so a hard stop leaves the customer with nothing. One region by default,
        # the full sweep only on an explicit flag, and the scope is stated in the report.
        if args.all_regions:
            auto_regions = list(DEFAULT_SWEEP_REGIONS)[:MAX_SWEEP_REGIONS]
            result["scope_note"] = (
                "no locator given, so this is a status listing (%s) across %d regions; "
                "instances in regions outside the built-in list are not covered"
                % (args.status, len(auto_regions)))
        else:
            region = (args.region_hint.split(",")[0].strip() or DEFAULT_SWEEP_REGIONS[0])
            auto_regions = [region]
            result["scope_note"] = (
                "no locator given, so this is a status listing (%s) in ONE region only: "
                "%s; rerun with --all-regions for the account-wide sweep"
                % (args.status, region))
        params = {"Status": args.status}
    else:
        auto_regions = None

    if auto_regions is not None:
        regions = auto_regions
    else:
        overrides = _split_csv(args.regions)
        if overrides:
            regions = overrides[:MAX_SWEEP_REGIONS]
        else:
            regions = list(DEFAULT_SWEEP_REGIONS)
        hints = _split_csv(args.region_hint)
        regions = hints + [r for r in regions if r not in hints]
    result["regions_queried"] = regions

    fatal = []
    hits, stopped = find_regions(regions, params, errors, fatal)
    result["hits"] = hits
    if auto_regions is not None:
        # Quote-able listing rows: a count alone cannot be checked by the customer.
        result["listing"] = [
            {"instance_id": h.get("instance_id"), "name": h.get("instance_name"),
             "status": h.get("status"), "region": h.get("region_id")}
            for h in hits
        ]
    if fatal:
        result["fatal"] = fatal

    if hits and not args.no_status_check:
        hit_regions = sorted({h["region_id"] for h in hits})
        hit_ids = [h["instance_id"] for h in hits]
        result["status_crosscheck"] = status_crosscheck(
            hit_regions, hit_ids, errors)

    if hits and args.console_claims:
        statuses = {h["instance_id"]: h["status"] for h in hits}
        matched = _compare_claim(args.console_claims, statuses)
        result["console_claims_note"] = (
            f"customer-reported console text {args.console_claims!r} matches "
            f"the queried status of {len(matched)}/{len(statuses)} found "
            f"instances; a mismatch means the customer is looking at another "
            f"region/account view, a stale page, or a second-layer (in-OS) "
            f"reading rather than a wrong cloud state"
        )

    status = "OK"
    if stopped or any("DescribeInstanceStatus" in str(e.get("action", ""))
                      for e in errors):
        status = "DEGRADED"
    if errors and status == "OK":
        status = "DEGRADED"
    if stopped:
        status = "FAIL" if not hits else "DEGRADED"

    if hits:
        found_regions = sorted({h["region_id"] for h in hits})
        if auto_regions is not None:
            # The scope note already carries the widening hint (single region vs sweep).
            action = ("listed %d instance(s), scope: %s; quote the rows above instead of a "
                      "bare count" % (len(hits), result.get("scope_note", "stated above")))
        else:
            action = ("resource EXISTS in " + ", ".join(found_regions) +
                      "; tell the customer to switch the console region "
                      "switcher (deep link in the entry map) and, if the list "
                      "is still empty, clear any resource-group filter")
    else:
        if auto_regions is not None:
            action = ("no instance with that status was listed, but the scope was limited "
                      "(see the listing scope line); rerun with --all-regions before telling "
                      "the customer nothing exists")
        else:
            action = ("not found in any queried region; put the not-found "
                      "follow-up questions to the customer (account, product, "
                      "expiry lifecycle) before anything else")
    _finish(result, args.json, status, action, vars(args))
    return 0


def _finish(result, as_json, status, next_action, _args_vars):
    result["status"] = status
    result["next_action"] = next_action
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        _print_contract(status, next_action)
        return
    _render(result, status, next_action)


def _print_contract(status, next_action):
    print(f"STATUS: {status}")
    print(f"NEXT_ACTION: {next_action}")


def _render(result, status, next_action):
    line = "=" * 72
    print(line)
    print(" ECS console resource lookup -- READ-ONLY evidence report")
    print(line)
    print(f"Account of current credential : {result['account_id']}")
    print("Scope statement                 : every result reflects ONLY the "
          "account the current credential belongs to.")
    print(f"Mode                            : {result['mode']}")

    if result["mode"] == "availability":
        print(f"Regions queried                 : "
              f"{', '.join(result['regions_queried'])}")
        zones = result.get("availability") or []
        print(f"\nAvailability evidence ({len(zones)} zone rows)")
        for zone in zones:
            supported = ", ".join(zone["supported"][:10])
            print(f"  {zone['zone_id']} status={zone['status']} "
                  f"category={zone['category']} {supported}")
        print(f"\nNote: {AVAILABILITY_NOTE}")
    else:
        print(f"Regions queried                 : "
              f"{len(result['regions_queried'])} ({', '.join(result['regions_queried'][:8])}"
              f"{', ...' if len(result['regions_queried']) > 8 else ''})")
        if result.get("scope_note"):
            print(f"Listing scope                   : {result['scope_note']}")
        hits = result["hits"]
        print(f"\nFound instances ({len(hits)})")
        for h in hits:
            print(f"  [{h['region_id']}] {h['instance_id']}  "
                  f"name={h['instance_name'] or '-'}  status={h['status']}")
            print(f"      charge={h['charge_type']}  type={h['instance_type']}"
                  f"  public={h['public_ips'] or h['eip'] or '-'}  "
                  f"inner={h['inner_ips'] or '-'}")
            print(f"      resource-group={h['resource_group_id'] or '-'}  "
                  f"vpc={h['vpc_id'] or '-'}  created={h['creation_time'] or '-'}"
                  f"  expired={h['expired_time'] or '-'}")
            if h["lock_reasons"]:
                for reason in h["lock_reasons"]:
                    meaning = LOCK_REASON_MEANING.get(
                        reason, "undocumented lock value (echoed raw)")
                    print(f"      LOCK {reason}: {meaning}")
            if h["charge_type"] in CHARGE_TYPE_NOTE:
                print(f"      charge gating note: "
                      f"{CHARGE_TYPE_NOTE[h['charge_type']]}")
        cross = result.get("status_crosscheck") or {}
        if cross:
            print("\nStatus cross-check (DescribeInstances vs "
                  "DescribeInstanceStatus)")
            for h in hits:
                api2 = cross.get(h["instance_id"], {})
                same = "match" if api2.get("status") == h["status"] else \
                    "MISMATCH"
                print(f"  {h['instance_id']}: {h['status']} vs "
                      f"{api2.get('status', 'n/a')} -> {same}")
                if h["status"] in INSTANCE_STATUS_MEANING:
                    print(f"      meaning: "
                          f"{INSTANCE_STATUS_MEANING[h['status']]}")
        if result.get("console_claims_note"):
            print(f"\nConsole display cross-check: "
                  f"{result['console_claims_note']}")
        print(f"\nQuery errors ({len([e for e in result['errors']])})")
        for err in result["errors"]:
            act = err.get("action", "DescribeInstances")
            print(f"  [WARN] {err.get('region', '?')} {act}: "
                  f"{err.get('code') or 'no-code'} {err['message'][:120]}")
        if not hits:
            print("\nNot-found follow-ups (ask these to the customer)")
            for q in NOT_FOUND_FOLLOWUPS:
                print(f"  - {q}")
        for note in result.get("fatal", []):
            print(f"\nSTOP: {note}")

    print(f"\nInterpretation: {STATUS_SYNC_NOTE}")
    print(f"Console deep link: {ENTRY_MAP['ecs-instance-list']['url']}")
    print("\nIntake questions (when the request lacks a locator)")
    for q in INTAKE_QUESTIONS:
        print(f"  - {q}")
    print(f"\nSTATUS: {status}")
    print(f"NEXT_ACTION: {next_action}")


if __name__ == "__main__":
    sys.exit(main())
