#!/usr/bin/env python3
"""
ecs_instance_modify.py -- READ-ONLY ECS spec-change & purchase-feasibility entry
================================================================================
SECURITY: strictly READ-ONLY. Only Describe/Get-class ECS APIs plus STS
GetCallerIdentity are ever called (through _cli.call). This script NEVER issues a
mutating API (no ModifyInstancesAttribute / ReplaceSystemDisk / RebootInstance /
RunInstances / CreateInstance and no order placement). Credentials come only from
the aliyun CLI default credential chain; no AK/SK is read, printed or passed.

Capabilities (one tier: "spec change & purchase feasibility"):
  A. spec-change feasibility  (--instance-id [--operation-type Upgrade|Downgrade]
                               [--target-instance-type T]):
       DescribeInstances -> current spec/status/charge type, then
       DescribeResourcesModification -> the target instance types it CAN change to.
  B. stock / purchase feasibility (--check-stock --target-instance-type T
                               --region R [--zone-id Z]):
       DescribeAvailableResource -> whether T is Available or SoldOut in the zone
       (OperationDenied.NoStock guidance).
  C. account quota / limits (--check-quota --region R):
       DescribeAccountAttributes -> account-level attributes/limits + Quotas Center
       guidance for the per-instance-type purchase quota.
  D. "spec change did not take effect" -- capability A re-reads the authoritative
     control-plane InstanceType/Status and explains the restart requirement.

Every cloud call degrades gracefully: on CliError it logs `[WARN] <Code>: <msg>`
to stderr, records the error, and continues. The run ends with
`STATUS: OK|DEGRADED|FAIL` and a `NEXT_ACTION:` line.

Usage:
  python3 ecs_instance_modify.py --instance-id i-bp1xxxx --region cn-hangzhou
  python3 ecs_instance_modify.py --check-stock --target-instance-type ecs.g6.large \
      --region cn-hangzhou --zone-id cn-hangzhou-i
  python3 ecs_instance_modify.py --check-quota --region cn-hangzhou --json
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import sys

import _cli
from _constants import (
    DEFAULT_REGION, DESTINATION_RESOURCE_INSTANCE_TYPE, ERROR_CODES,
    INSTANCE_CHARGE_TYPES, MODIFY_NOT_EFFECTIVE_RULES, OPERATION_TYPE_UPGRADE,
    PURCHASE_FAILURE_RULES, QUOTA_CONSOLE_PATH, STATUS_STOPPED,
)


# --------------------------------------------------------------------------
# Pure helpers (defensive response parsing -- never assume a rigid schema)
# --------------------------------------------------------------------------

def extract_instances(resp):
    """DescribeInstances -> list of instance dicts (tolerant of shapes)."""
    if not isinstance(resp, dict):
        return []
    inst = resp.get("Instances")
    if isinstance(inst, dict):
        lst = inst.get("Instance")
        return lst if isinstance(lst, list) else []
    if isinstance(inst, list):
        return inst
    return []


def collect_value_status(node, acc=None):
    """Recursively collect (Value, Status) pairs from any nested dict/list.

    DescribeResourcesModification and DescribeAvailableResource nest their
    results (AvailableZones -> AvailableResources -> SupportedResources); this
    walker never hard-codes the path, so a shape change degrades to fewer pairs
    instead of a crash.
    """
    if acc is None:
        acc = []
    if isinstance(node, dict):
        if "Value" in node:
            acc.append((str(node.get("Value")), str(node.get("Status", ""))))
        for v in node.values():
            collect_value_status(v, acc)
    elif isinstance(node, list):
        for v in node:
            collect_value_status(v, acc)
    return acc


def collect_account_attributes(node, acc=None):
    """Recursively collect {AttributeName -> [values]} from DescribeAccountAttributes."""
    if acc is None:
        acc = {}
    if isinstance(node, dict):
        name = node.get("AttributeName")
        if name:
            vals = []
            sub = node.get("AttributeValues")
            if isinstance(sub, dict):
                vi = sub.get("ValueItem")
                if isinstance(vi, list):
                    vals = [str(x.get("Value", "")) for x in vi if isinstance(x, dict)]
            acc[str(name)] = vals
        for v in node.values():
            collect_account_attributes(v, acc)
    elif isinstance(node, list):
        for v in node:
            collect_account_attributes(v, acc)
    return acc


def decide_stock(pairs, target):
    """Verdict for capability B from (Value, Status) pairs. Pure."""
    if not pairs:
        return {"verdict": "UNKNOWN",
                "reason": "availability response exposed no recognizable value/status list"}
    matched = [(v, s) for (v, s) in pairs if target and v == target] or pairs
    avail = [v for (v, s) in matched if s.lower() in ("available", "withstock", "")]
    sold = [v for (v, s) in matched if "soldout" in s.lower() or "withoutstock" in s.lower()]
    if sold and not avail:
        return {"verdict": "SOLD_OUT", "error_code": "OperationDenied.NoStock",
                "reason": "target instance type reports no stock in the requested scope"}
    if avail:
        return {"verdict": "AVAILABLE", "reason": "stock reported available",
                "available": avail[:20]}
    return {"verdict": "UNKNOWN", "reason": "status values not conclusive",
            "seen": matched[:20]}


def decide_modify(instances, feasible_pairs, target):
    """Verdict for capability A. Pure."""
    if not instances:
        return {"verdict": "INSTANCE_NOT_FOUND",
                "error_code": "InvalidInstanceId.NotFound",
                "reason": "DescribeInstances returned no instance for the id/region"}
    inst = instances[0]
    cur_type = str(inst.get("InstanceType", ""))
    status = str(inst.get("Status", ""))
    charge = str(inst.get("InstanceChargeType", ""))
    feasible = sorted({v for (v, s) in feasible_pairs
                       if s.lower() in ("available", "withstock", "")})
    out = {
        "current_instance_type": cur_type,
        "status": status,
        "charge_type": charge,
        "charge_type_note": INSTANCE_CHARGE_TYPES.get(charge, ""),
        "feasible_target_count": len(feasible),
        "feasible_targets": feasible[:30],
    }
    if target:
        out["target"] = target
        out["target_feasible"] = target in feasible
    if charge and status and status != STATUS_STOPPED and charge == "PostPaid":
        out["restart_note"] = ("pay-as-you-go instance is %s; most spec changes "
                               "require it to be Stopped first" % status)
    if not feasible:
        out["verdict"] = "NO_FEASIBLE_TARGET"
        out["reason"] = ("no changeable target instance type returned (check "
                         "operation type, instance status, or family limits)")
    else:
        out["verdict"] = "FEASIBLE"
    return out


def decide_status(errors, evidence_ok, missing_input=False):
    """OK / DEGRADED / FAIL from the run evidence. Pure."""
    if missing_input:
        return "FAIL"
    if errors and not evidence_ok:
        return "FAIL"
    if errors:
        return "DEGRADED"
    return "OK" if evidence_ok else "FAIL"


# --- inline boundary assertions (normal / boundary / invalid) -------------
assert extract_instances({"Instances": {"Instance": [{"InstanceId": "i-1"}]}}) == [{"InstanceId": "i-1"}]
assert extract_instances({"Instances": {"Instance": []}}) == []
assert extract_instances({}) == [] and extract_instances(None) == [] and extract_instances("x") == []
assert collect_value_status({"A": {"SupportedResource": [{"Value": "ecs.g6.large", "Status": "Available"}]}}) \
    == [("ecs.g6.large", "Available")]
assert collect_value_status([{"Value": "x", "Status": "SoldOut"}, {"Value": "y"}]) == [("x", "SoldOut"), ("y", "")]
assert collect_value_status({}) == [] and collect_value_status(None) == []
assert decide_stock([("ecs.g6.large", "SoldOut")], "ecs.g6.large")["verdict"] == "SOLD_OUT"
assert decide_stock([("ecs.g6.large", "Available")], "ecs.g6.large")["verdict"] == "AVAILABLE"
assert decide_stock([], "ecs.g6.large")["verdict"] == "UNKNOWN"
_dm = decide_modify([{"InstanceType": "ecs.g6.large", "Status": "Running", "InstanceChargeType": "PostPaid"}],
                    [("ecs.g6.xlarge", "Available")], "ecs.g6.xlarge")
assert _dm["verdict"] == "FEASIBLE" and _dm["target_feasible"] is True and "restart_note" in _dm
assert decide_modify([], [], "")["verdict"] == "INSTANCE_NOT_FOUND"
assert decide_modify([{"InstanceType": "t", "Status": "Running", "InstanceChargeType": "PrePaid"}], [], "")["verdict"] == "NO_FEASIBLE_TARGET"
assert decide_status([], True) == "OK"
assert decide_status(["e"], True) == "DEGRADED"
assert decide_status(["e"], False) == "FAIL"
assert decide_status([], False, missing_input=True) == "FAIL"


# --------------------------------------------------------------------------
# Evidence gathering (each call degrades independently)
# --------------------------------------------------------------------------

def _gather(args, errors):
    """Run the mode-appropriate read-only calls; return (evidence dict, ok flag)."""
    ev = {"mode": None, "uid": _cli.resolve_account_id(region=args.region, profile=args.profile)}
    ok = False

    if args.check_quota:
        ev["mode"] = "quota"
        try:
            resp = _cli.call("ecs", "DescribeAccountAttributes",
                             {"RegionId": args.region}, region=args.region, profile=args.profile)
            ev["account_attributes"] = collect_account_attributes(resp)
            ev["quota_console_path"] = QUOTA_CONSOLE_PATH
            ok = True
        except _cli.CliError as e:
            errors.append("DescribeAccountAttributes: %s" % e)
            print("[WARN] %s: %s" % (e.code or "DescribeAccountAttributes", e), file=sys.stderr)

    elif args.check_stock:
        ev["mode"] = "stock"
        if not args.target_instance_type:
            return ev, False, True  # missing input
        params = {"DestinationResource": DESTINATION_RESOURCE_INSTANCE_TYPE,
                  "RegionId": args.region, "InstanceType": args.target_instance_type}
        if args.zone_id:
            params["ZoneId"] = args.zone_id
        try:
            resp = _cli.call("ecs", "DescribeAvailableResource", params,
                             region=args.region, profile=args.profile)
            pairs = collect_value_status(resp)
            ev["stock"] = decide_stock(pairs, args.target_instance_type)
            ev["target_instance_type"] = args.target_instance_type
            ok = True
        except _cli.CliError as e:
            errors.append("DescribeAvailableResource: %s" % e)
            print("[WARN] %s: %s" % (e.code or "DescribeAvailableResource", e), file=sys.stderr)

    elif args.instance_id:
        ev["mode"] = "modify"
        ev["instance_id"] = args.instance_id
        try:
            resp = _cli.call("ecs", "DescribeInstances",
                             {"RegionId": args.region, "InstanceIds": json.dumps([args.instance_id])},
                             region=args.region, profile=args.profile)
            instances = extract_instances(resp)
        except _cli.CliError as e:
            instances = []
            errors.append("DescribeInstances: %s" % e)
            print("[WARN] %s: %s" % (e.code or "DescribeInstances", e), file=sys.stderr)
        feasible = []
        if instances:
            try:
                mresp = _cli.call("ecs", "DescribeResourcesModification",
                                  {"DestinationResource": DESTINATION_RESOURCE_INSTANCE_TYPE,
                                   "RegionId": args.region, "ResourceId": args.instance_id,
                                   "OperationType": args.operation_type},
                                  region=args.region, profile=args.profile)
                feasible = collect_value_status(mresp)
                ok = True
            except _cli.CliError as e:
                errors.append("DescribeResourcesModification: %s" % e)
                print("[WARN] %s: %s" % (e.code or "DescribeResourcesModification", e), file=sys.stderr)
        ev["modify"] = decide_modify(instances, feasible, args.target_instance_type)
        ev["operation_type"] = args.operation_type
        ev["not_effective_rules"] = MODIFY_NOT_EFFECTIVE_RULES
        if instances:
            ok = True
    else:
        return ev, False, True  # missing input

    return ev, ok, False


def _error_code_hints(errors):
    hints = []
    for code, meta in ERROR_CODES.items():
        if any(code.lower() in e.lower() for e in errors):
            hints.append({"code": code, "meaning": meta["meaning"], "guidance": meta["guidance"]})
    return hints


def main():
    p = argparse.ArgumentParser(
        description="READ-ONLY ECS spec-change / purchase-feasibility diagnosis")
    p.add_argument("--instance-id", default=None, help="target ECS instance id (capability A/D)")
    p.add_argument("--region", default=DEFAULT_REGION, help="region id (default cn-hangzhou)")
    p.add_argument("--zone-id", default=None, help="zone id for the stock check")
    p.add_argument("--operation-type", default=OPERATION_TYPE_UPGRADE,
                   choices=["Upgrade", "Downgrade"], help="spec-change direction")
    p.add_argument("--target-instance-type", default=None,
                   help="desired target instance type (feasibility / stock)")
    p.add_argument("--check-stock", action="store_true", help="capability B: stock / purchase feasibility")
    p.add_argument("--check-quota", action="store_true", help="capability C: account quota / limits")
    p.add_argument("--profile", default=None, help="optional aliyun CLI credential profile")
    p.add_argument("--json", action="store_true", help="JSON output")
    args = p.parse_args()

    _cli.check_cli_available()
    errors = []
    ev, ok, missing_input = _gather(args, errors)
    ev["errors"] = errors
    ev["error_code_hints"] = _error_code_hints(errors)
    if ev["mode"] == "stock" and not args.check_quota:
        ev["purchase_failure_rules"] = PURCHASE_FAILURE_RULES
    status = decide_status(errors, ok, missing_input)

    if missing_input:
        next_action = ("provide --instance-id with --region for a spec-change check, or "
                       "--check-stock --target-instance-type <T> --region <R>, or "
                       "--check-quota --region <R>")
    elif status == "FAIL":
        next_action = ("no usable evidence: verify the credential can read ECS in this "
                       "region and that the instance id / target type are correct")
    else:
        next_action = ("relay the verdict and the read-only guidance; the user performs any "
                       "actual spec change / purchase in the console (this skill never mutates)")

    if args.json:
        print(json.dumps({"status": status, "next_action": next_action, **ev},
                         ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("ECS spec-change / purchase feasibility (READ-ONLY)")
        print("=" * 60)
        print("  mode      : %s" % ev.get("mode"))
        print("  region    : %s" % args.region)
        print("  uid       : %s" % (ev.get("uid") or "(unresolved)"))
        if ev.get("modify"):
            m = ev["modify"]
            print("  instance  : %s" % args.instance_id)
            print("  current   : %s (%s, %s)" % (m.get("current_instance_type"),
                                                 m.get("status"), m.get("charge_type")))
            print("  verdict   : %s (feasible targets: %d)"
                  % (m.get("verdict"), m.get("feasible_target_count", 0)))
            if m.get("target"):
                print("  target    : %s feasible=%s" % (m["target"], m.get("target_feasible")))
        if ev.get("stock"):
            s = ev["stock"]
            print("  target    : %s" % args.target_instance_type)
            print("  verdict   : %s (%s)" % (s.get("verdict"), s.get("reason", "")))
        if ev.get("account_attributes") is not None:
            print("  account attributes returned: %d" % len(ev["account_attributes"]))
            print("  quota path: %s" % QUOTA_CONSOLE_PATH)
        if errors:
            print("\n  degraded calls:")
            for e in errors:
                print("    - %s" % e)
        for h in ev.get("error_code_hints", []):
            print("\n  [%s] %s\n     -> %s" % (h["code"], h["meaning"], h["guidance"]))
        print("\nSummary")
        print("-------")
        print("  Evidence-based, read-only findings only. Any spec change, restart,")
        print("  or purchase is a MANUAL action the user performs in the console;")
        print("  this skill never modifies a resource or places an order.")
    print("\nSTATUS: %s" % status)
    print("NEXT_ACTION: %s" % next_action)
    return 0 if status in ("OK", "DEGRADED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
