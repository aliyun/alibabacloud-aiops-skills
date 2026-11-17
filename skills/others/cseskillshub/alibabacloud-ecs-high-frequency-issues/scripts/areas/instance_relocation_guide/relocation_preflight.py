#!/usr/bin/env python3
"""Single entry point for the ECS instance relocation guide.

The agent runs this script; it never assembles cloud calls by hand. Four
read-only sub-commands are available:

* ``doctor``     confirm the credential chain and echo the API allowlist
* ``inventory``  read the facts of the instances that would be relocated
* ``stock``      check destination capacity for an instance type
* ``assess``     evidence plus constraints, path, checklists and hand-offs

Every report ends with the ``STATUS`` / ``NEXT_ACTION`` contract. Nothing in
this script changes a resource.
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _cli
from _constants import (
    BLIND_SPOTS,
    CALL_TIMEOUT_SECONDS,
    CROSS_ACCOUNT_BRANCHES,
    CUTOVER_CHECKLIST,
    DOCS,
    ECS_API_VERSION,
    ECS_PRODUCT,
    ERROR_BRANCHES,
    HANDOFFS,
    MAX_PAGES,
    PAGE_SIZE,
    PRE_FLIGHT_CHECKLIST,
    READ_API_ALLOWLIST,
    SCENARIO_CONSTRAINTS,
    SNAPSHOT_FIRST_NOTICE,
    STS_API_VERSION,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
)

import sts_token

WARNINGS = []
CALLS = []


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _warn(message):
    WARNINGS.append(str(message))
    _cli.warn(message)


def _title(text):
    print("\n== {0} ==".format(text))


def _bullet(text, indent="  "):
    print("{0}- {1}".format(indent, text))


def _numbered(items, indent="  "):
    for index, item in enumerate(items, 1):
        print("{0}{1}. {2}".format(indent, index, item))


def _doc(key, label=None):
    url = DOCS.get(key, "")
    return "{0}: {1}".format(label or key, url)


def _record_call(action):
    """Remember an action that was actually attempted, for the report footer."""
    if action not in CALLS:
        CALLS.append(action)


def _split_csv(value):
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _unwrap(payload, *path):
    """Walk a nested payload, tolerating both wrapped and flat shapes."""
    node = payload
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
        if isinstance(node, dict) and len(node) == 1:
            inner = list(node.values())[0]
            if isinstance(inner, list):
                node = inner
    if node is None:
        return None
    if isinstance(node, dict) and len(node) == 1:
        inner = list(node.values())[0]
        if isinstance(inner, list):
            return inner
    return node


def _finish(status, next_action):
    """Print the output contract."""
    _title("RESULT")
    print("STATUS: {0}".format(status))
    print("NEXT_ACTION: {0}".format(next_action))
    if WARNINGS:
        print("DEGRADATION_REASON:")
        for item in WARNINGS:
            _bullet(item)
    print("CALLS_MADE: {0}".format(", ".join(CALLS) if CALLS else "none"))
    print("SESSION_ID: {0}".format(getattr(_finish, "session_id", "-")))
    return 0 if status == STATUS_OK else 1


# --------------------------------------------------------------------------- #
# read-only queries
# --------------------------------------------------------------------------- #

def describe_instances(region, instance_ids, session_id, timeout):
    """Return instance rows for a region, paginating with NextToken."""
    rows = []
    token = None
    for _ in range(MAX_PAGES):
        params = {
            "RegionId": region,
            "MaxResults": PAGE_SIZE,
        }
        if instance_ids:
            params["InstanceIds"] = json.dumps(instance_ids)
        if token:
            params["NextToken"] = token
        _record_call("ecs:DescribeInstances")
        payload = _cli.call_or_warn(
            ECS_PRODUCT, "DescribeInstances", params,
            session_id=session_id, timeout=timeout)
        if payload is None:
            return rows, False
        page = _unwrap(payload, "Instances") or []
        if not isinstance(page, list):
            page = [page]
        rows.extend(page)
        token = payload.get("NextToken") if isinstance(payload, dict) else None
        if not token or not page:
            break
    return rows, True


def describe_status(region, instance_ids, session_id, timeout):
    params = {"RegionId": region, "PageSize": PAGE_SIZE}
    for index, instance_id in enumerate(instance_ids[:PAGE_SIZE], 1):
        params["InstanceId.{0}".format(index)] = instance_id
    _record_call("ecs:DescribeInstanceStatus")
    payload = _cli.call_or_warn(
        ECS_PRODUCT, "DescribeInstanceStatus", params,
        session_id=session_id, timeout=timeout)
    if payload is None:
        return {}
    entries = _unwrap(payload, "InstanceStatuses") or []
    mapping = {}
    for entry in entries if isinstance(entries, list) else [entries]:
        if isinstance(entry, dict) and entry.get("InstanceId"):
            mapping[entry["InstanceId"]] = entry.get("Status", "Unknown")
    return mapping


def describe_available(params, session_id, timeout):
    _record_call("ecs:DescribeAvailableResource")
    return _cli.call_or_warn(
        ECS_PRODUCT, "DescribeAvailableResource", params,
        session_id=session_id, timeout=timeout)


def interpret_availability(payload):
    """Extract zone/status pairs without assuming one fixed payload shape.

    Returns ``(entries, interpreted)`` where ``entries`` is a list of dicts with
    ``zone``, ``resource``, ``value`` and ``status`` keys, and ``interpreted``
    says whether anything recognisable was found.
    """
    entries = []

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        zone = node.get("ZoneId")
        status = node.get("Status") or node.get("StatusCategory")
        resource = node.get("Type") or node.get("DestinationResource")
        value = node.get("Value") or node.get("InstanceType")
        if zone or status or value:
            entries.append({
                "zone": zone or "-",
                "resource": resource or "-",
                "value": value or "-",
                "status": status or "Unknown",
            })
        for child in node.values():
            if isinstance(child, (dict, list)):
                walk(child)

    walk(payload or {})
    useful = [item for item in entries if item["status"] != "Unknown"]
    return useful or entries, bool(useful)


# --------------------------------------------------------------------------- #
# report blocks
# --------------------------------------------------------------------------- #

def print_inventory(rows, status_map, region):
    _title("READ-ONLY EVIDENCE / instances in {0}".format(region))
    if not rows:
        _bullet("no instance returned by the read-only query")
        return
    for row in rows:
        instance_id = row.get("InstanceId", "-")
        print("  {0}  ({1})".format(instance_id, row.get("InstanceName", "unnamed")))
        _bullet("region / zone: {0} / {1}".format(
            row.get("RegionId", "-"), row.get("ZoneId", "-")), indent="    ")
        _bullet("instance type: {0} (family {1})".format(
            row.get("InstanceType", "-"), row.get("InstanceTypeFamily", "-")),
            indent="    ")
        _bullet("charge: {0}, expired: {1}".format(
            row.get("InstanceChargeType", "-"), row.get("ExpiredTime", "-")),
            indent="    ")
        _bullet("image: {0}".format(row.get("ImageId", "-")), indent="    ")
        _bullet("status: {0}".format(
            status_map.get(instance_id, row.get("Status", "-"))), indent="    ")
        vpc = row.get("VpcAttributes") or {}
        private_ips = (vpc.get("PrivateIpAddress") or {}).get("IpAddress") or []
        public_ips = (row.get("PublicIpAddress") or {}).get("IpAddress") or []
        eip = (row.get("EipAddress") or {}).get("IpAddress", "")
        _bullet("private address: {0}".format(", ".join(private_ips) or "-"),
                indent="    ")
        _bullet("public address: {0}{1}".format(
            ", ".join(public_ips) or "-",
            " (elastic: {0})".format(eip) if eip else ""), indent="    ")
        groups = (row.get("SecurityGroupIds") or {}).get("SecurityGroupId") or []
        if groups:
            _bullet("security groups: {0}".format(", ".join(groups)), indent="    ")


def print_availability(entries, interpreted, target_zone):
    _title("READ-ONLY EVIDENCE / destination capacity")
    if not entries:
        _bullet("the capacity query returned nothing usable")
        return
    if not interpreted:
        _bullet("payload shape could not be interpreted; re-run with --raw")
    for item in entries[:40]:
        _bullet("zone={0} resource={1} value={2} status={3}".format(
            item["zone"], item["resource"], item["value"], item["status"]))
    if target_zone:
        hits = [item for item in entries if item["zone"] == target_zone]
        if hits:
            _bullet("target zone {0}: {1}".format(
                target_zone, ", ".join(sorted(set(h["status"] for h in hits)))))
        else:
            _bullet("target zone {0} does not appear in the returned capacity "
                    "list".format(target_zone))


def derive_scenarios(args, rows):
    """Decide which constraint sets apply, from flags and evidence."""
    scenarios = []
    if args.retirement_notice:
        scenarios.append("platform-retirement")
    if args.target_account:
        scenarios.append("cross-account")
    if args.target_region and args.target_region != args.source_region:
        scenarios.append("cross-region")
    if args.os_change:
        scenarios.append("os-change")
    zone_changed = False
    if args.target_zone:
        for row in rows:
            if row.get("ZoneId") and row.get("ZoneId") != args.target_zone:
                zone_changed = True
                break
    if zone_changed or args.cross_zone:
        scenarios.append("cross-zone")
    if not scenarios:
        scenarios.append("cross-zone")
    return scenarios


def print_constraints(scenarios):
    _title("CONSTRAINTS THAT DECIDE THIS MOVE")
    for scenario in scenarios:
        constraints = SCENARIO_CONSTRAINTS.get(scenario, ())
        if not constraints:
            continue
        print("  [{0}]".format(scenario))
        for item in constraints:
            print("    * ({0}) {1}".format(item["provenance"], item["text"]))
            for doc_key in item.get("docs", ()):
                _bullet(_doc(doc_key), indent="      ")


def print_cross_account_branches():
    """Route table for another account: transfer, rebuild, or rebuild-only."""
    _title("ANOTHER ACCOUNT / WHICH ROUTE APPLIES")
    for index, branch in enumerate(CROSS_ACCOUNT_BRANCHES, 1):
        print("  Route {0}: {1}".format(index, branch["when"]))
        _bullet("route: {0}".format(branch["route"]), indent="    ")
        for label, key in (("before starting", "before"),
                           ("result", "result"),
                           ("trade-off", "tradeoffs")):
            for item in branch.get(key, ()):
                _bullet("{0}: {1}".format(label, item), indent="    ")
        for doc_key in branch.get("docs", ()):
            _bullet(_doc(doc_key), indent="    ")


def print_path(scenarios):
    _title("MANUAL PATH (guidance only, nothing is executed here)")
    print("  " + SNAPSHOT_FIRST_NOTICE)
    if "cross-account" in scenarios:
        print_cross_account_branches()
    if "cross-region" in scenarios or "cross-account" in scenarios:
        if "cross-account" in scenarios:
            print("  The numbered chain below is route 2 (rebuild). A route-1 "
                  "ownership transfer does not use it.")
        _numbered([
            "Back up first: take a snapshot of the system disk and of every data "
            "disk on the source instance.",
            "Image the system disk. " + _doc("custom_image_from_snapshot"),
            "Replicate the image to the destination region; snapshot "
            "replication is billed on its own. " + _doc("copy_image"),
            "For another account taking the rebuild route, the sharing hop comes "
            "next; a route-1 ownership transfer needs none of this. " +
            _doc("share_custom_image") + " | " + _doc("share_snapshot"),
            "Rebuild the data disks from their snapshots in the destination. " +
            _doc("create_disk_from_snapshot"),
            "Then build the target: a fresh instance from the image (" +
            _doc("create_instance_by_custom_image") + ") or an operating-system "
            "replacement on the instance that already exists there (" +
            _doc("replace_operating_system") + "), which clears that system disk.",
        ])
    if "cross-zone" in scenarios:
        _numbered([
            "Confirm capacity for the instance type in the destination zone "
            "(the stock pre-flight above). Guidance: " +
            _doc("change_types_across_zones"),
            "Check the resources that must move with the instance: data disks, "
            "elastic network interfaces and their vSwitches.",
            "Clear private-address references in route tables, remote-session "
            "records and data-sync tasks; powering the instance off does not "
            "clear them.",
            "Submit the change request, then pay the relocation order; an "
            "unpaid order never executes.",
            "Rebuild data disks from snapshots in the destination zone, or "
            "transfer files over the network. " + _doc("regional_essd_disks"),
            "Expect the private address to change and re-plan the network design.",
        ])
    if "platform-retirement" in scenarios:
        _numbered([
            "Read the retirement notice you received and record its cut-over "
            "date; this skill does not maintain a retirement calendar.",
            "Plan a self-service move now: the platform will not relocate the "
            "instance for you. " + _doc("migration_due_to_underlying_upgrade"),
            "Any retained period is best effort: service levels stop being "
            "guaranteed and the instance can disappear at any time.",
            "Send commercial questions (time transfer, refunds, compensation) "
            "to manual review; no amount is promised here. " +
            _doc("refund_rules"),
        ])
    if "os-change" in scenarios:
        _numbered([
            "Choose one route: step-by-step operating-system migration (" +
            _doc("migrate_operating_system") + ") or back up and replace the "
            "operating system (" + _doc("replace_operating_system") + ").",
            "Windows Server cannot be upgraded across more than one major "
            "version in place.",
            "Both routes need the snapshot taken first; the replacement clears "
            "the system disk.",
        ])


def print_checklists():
    _title("PRE-FLIGHT LIST")
    _numbered(list(PRE_FLIGHT_CHECKLIST))
    _title("CUT-OVER LIST")
    _numbered(list(CUTOVER_CHECKLIST))


def print_errors():
    _title("ERROR WORDING YOU MAY SEE")
    for branch in ERROR_BRANCHES:
        print("  \"{0}\"  ({1})".format(branch["phrase"], branch["provenance"]))
        _bullet(branch["meaning"], indent="    ")
        for action in branch["actions"]:
            _bullet(action, indent="    ")


def print_handoffs():
    _title("OUT OF SCOPE / HAND-OFF")
    for item in HANDOFFS:
        _bullet("{0} -> {1}".format(item["symptom"], item["target"]))


def print_blind_spots():
    _title("WHAT A CLOUD READ CANNOT TELL YOU")
    for item in BLIND_SPOTS:
        _bullet(item)


# --------------------------------------------------------------------------- #
# sub-commands
# --------------------------------------------------------------------------- #

def cmd_doctor(args):
    status = STATUS_OK
    next_action = ("Proceed with 'assess' for the instances you plan to "
                   "relocate.")
    _title("CREDENTIAL CHECK")
    caller = sts_token.get_caller_identity(args.session_id)
    if caller is None:
        _bullet("the credential check failed; see the warning above")
        _bullet("verify the caller with `aliyun sts get-caller-identity` on the default "
                "credential chain; never supply a key or token in chat")
        status = STATUS_FAIL
        next_action = ("Ask the customer to configure local CLI credentials, "
                       "then re-run 'doctor'.")
    else:
        _bullet("account id: {0}".format(caller.get("account_id", "-")))
        _bullet("identity arn: {0}".format(caller.get("arn", "-")))
    _title("API ALLOWLIST (read-only, exhaustive)")
    for action in READ_API_ALLOWLIST:
        _bullet(action)
    print("  ECS api version {0} / STS api version {1}".format(
        ECS_API_VERSION, STS_API_VERSION))
    return _finish(status, next_action)


def cmd_inventory(args):
    status = STATUS_OK
    rows, ok = describe_instances(args.source_region,
                                  _split_csv(args.instance_ids),
                                  args.session_id, args.timeout)
    if not ok:
        status = STATUS_DEGRADED
    ids = [row.get("InstanceId") for row in rows if row.get("InstanceId")]
    status_map = {}
    if ids:
        status_map = describe_status(args.source_region, ids, args.session_id,
                                     args.timeout)
        if not status_map:
            status = STATUS_DEGRADED
    print_inventory(rows, status_map, args.source_region)
    if args.raw:
        _title("RAW PAYLOADS")
        print(json.dumps({"instances": rows, "status": status_map}, indent=2))
    if not rows:
        return _finish(
            STATUS_DEGRADED,
            "Confirm the region and instance ids with the customer; the "
            "read-only query returned no instance.")
    return _finish(
        status,
        "Check destination capacity for this instance type before scheduling "
        "the move.")


def cmd_stock(args):
    status = STATUS_OK
    targets = _split_csv(args.target_zone) or [""]
    params_base = {
        "RegionId": args.target_region or args.source_region,
        "DestinationResource": args.destination_resource,
    }
    if args.instance_type:
        params_base["InstanceType"] = args.instance_type
    if args.charge_type:
        params_base["InstanceChargeType"] = args.charge_type
    all_entries = []
    interpreted_any = False
    raw_payloads = []
    for zone in targets:
        params = dict(params_base)
        if zone:
            params["ZoneId"] = zone
        payload = describe_available(params, args.session_id, args.timeout)
        if payload is None:
            status = STATUS_DEGRADED
            continue
        raw_payloads.append(payload)
        entries, interpreted = interpret_availability(payload)
        all_entries.extend(entries)
        interpreted_any = interpreted_any or interpreted
    print_availability(all_entries, interpreted_any, targets[0] if targets else "")
    if args.raw:
        _title("RAW PAYLOADS")
        print(json.dumps(raw_payloads, indent=2))
    return _finish(
        status,
        "Pick a zone reported as available, then run 'assess' with it as "
        "--target-zone.")


def cmd_assess(args):
    ids = _split_csv(args.instance_ids)
    rows, ok = describe_instances(args.source_region, ids, args.session_id,
                                  args.timeout)
    status = STATUS_OK if ok and rows else STATUS_DEGRADED
    existing = [row.get("InstanceId") for row in rows if row.get("InstanceId")]
    status_map = describe_status(args.source_region, existing, args.session_id,
                                 args.timeout) if existing else {}
    if existing and not status_map:
        status = STATUS_DEGRADED
    print_inventory(rows, status_map, args.source_region)

    entries, interpreted, capacity_status = [], False, None
    if args.target_zone or args.target_region:
        params = {
            "RegionId": args.target_region or args.source_region,
            "DestinationResource": args.destination_resource,
        }
        if args.target_zone:
            params["ZoneId"] = args.target_zone
        if args.instance_type:
            params["InstanceType"] = args.instance_type
        if args.charge_type:
            params["InstanceChargeType"] = args.charge_type
        payload = describe_available(params, args.session_id, args.timeout)
        if payload is None:
            status = STATUS_DEGRADED
            capacity_status = "unavailable to query"
        else:
            entries, interpreted = interpret_availability(payload)
            print_availability(entries, interpreted, args.target_zone)
            capacity_status = "queried"
            if args.raw:
                _title("RAW PAYLOADS")
                print(json.dumps(payload, indent=2))

    scenarios = derive_scenarios(args, rows)
    print("  scenario(s): {0}".format(", ".join(scenarios)))
    _title("DECLARED ASSUMPTIONS")
    _bullet("source region taken from --source-region: {0}".format(args.source_region))
    _bullet("destination resource type assumed to be {0}".format(
        args.destination_resource))
    _bullet("capacity result is a point-in-time read and can change")
    _bullet("instance disk capacity is not returned by the read-only instance "
            "query; read disk sizes in the block storage console")
    if not ids:
        _bullet("no --instance-ids given, so the inventory is the whole "
                "region page set")
    print_constraints(scenarios)
    print_path(scenarios)
    print_checklists()
    print_errors()
    print_blind_spots()
    print_handoffs()

    next_action = ("Take the snapshots listed in the pre-flight list in the "
                   "console, confirm them, then follow the manual path for the "
                   "'{0}' scenario.".format(scenarios[0]))
    if capacity_status == "unavailable to query":
        next_action = ("Re-run 'stock' for the destination zone after fixing "
                       "the query, and confirm capacity in the console.")
    return _finish(status, next_action)


# --------------------------------------------------------------------------- #
# argument parsing
# --------------------------------------------------------------------------- #

def build_parser():
    parser = argparse.ArgumentParser(
        prog="relocation_preflight.py",
        description=("Read-only pre-flight and planning guidance for "
                     "relocating ECS instances across zones, regions and "
                     "accounts. Executes read queries only."))
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--session-id", dest="session_id", default=None,
                        help="reuse a 32 hex session id across runs")
    common.add_argument("--timeout", type=int, default=CALL_TIMEOUT_SECONDS,
                        help="per-call timeout in seconds")
    common.add_argument("--raw", action="store_true",
                        help="print the untouched payloads after the report")

    sub = parser.add_subparsers(dest="command")

    p_doctor = sub.add_parser("doctor", parents=[common],
                             help="check credentials and echo the allowlist")
    p_doctor.set_defaults(func=cmd_doctor)

    p_inv = sub.add_parser("inventory", parents=[common],
                          help="read the facts of the source instances")
    p_inv.add_argument("--source-region", required=True)
    p_inv.add_argument("--instance-ids", default="",
                       help="comma separated instance ids")
    p_inv.set_defaults(func=cmd_inventory)

    p_stock = sub.add_parser("stock", parents=[common],
                            help="check destination capacity")
    p_stock.add_argument("--source-region", required=True)
    p_stock.add_argument("--target-region", default="")
    p_stock.add_argument("--target-zone", default="",
                         help="comma separated candidate zones")
    p_stock.add_argument("--instance-type", default="")
    p_stock.add_argument("--charge-type", default="",
                         choices=["", "PrePaid", "PostPaid"])
    p_stock.add_argument("--destination-resource", default="InstanceType",
                         help="value accepted by the API for "
                              "DestinationResource; defaults to InstanceType")
    p_stock.set_defaults(func=cmd_stock)

    p_assess = sub.add_parser("assess", parents=[common],
                             help="full pre-flight report and manual path")
    p_assess.add_argument("--source-region", required=True)
    p_assess.add_argument("--instance-ids", default="")
    p_assess.add_argument("--target-region", default="")
    p_assess.add_argument("--target-zone", default="")
    p_assess.add_argument("--target-account", default="",
                          help="destination account id, when moving to it")
    p_assess.add_argument("--instance-type", default="")
    p_assess.add_argument("--charge-type", default="",
                          choices=["", "PrePaid", "PostPaid"])
    p_assess.add_argument("--destination-resource", default="InstanceType",
                          help="value accepted by the API for "
                               "DestinationResource; defaults to InstanceType")
    p_assess.add_argument("--cross-zone", action="store_true",
                          help="force the cross-zone guidance set")
    p_assess.add_argument("--os-change", action="store_true",
                          help="include operating-system change constraints")
    p_assess.add_argument("--retirement-notice", action="store_true",
                          help="a zone or region retirement notice applies")
    p_assess.set_defaults(func=cmd_assess)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 2
    args.session_id = args.session_id or _cli.new_session_id()
    _finish.session_id = args.session_id
    print("# {0}".format(_cli.user_agent(args.session_id)))
    try:
        return args.func(args)
    except _cli.CliError as exc:
        _warn("unhandled CLI failure -> {0}".format(exc))
        return _finish(STATUS_FAIL,
                       "Fix the reported failure, then re-run 'doctor'.")


if __name__ == "__main__":
    sys.exit(main())
