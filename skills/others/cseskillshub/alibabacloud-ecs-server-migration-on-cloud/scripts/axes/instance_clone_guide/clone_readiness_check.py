#!/usr/bin/env python3
"""
clone_readiness_check.py -- read-only instance fact verification for ECS
instance cloning (the ONLY API-calling entry script of this skill).

SECURITY: READ-ONLY. This script issues exactly two ECS reads, both on the
skill's API whitelist enforced by _cli.py:
    aliyun ecs describe-instances       (PascalCase metadata mode)
    aliyun ecs describe-instance-status  (PascalCase metadata mode)
plus one STS identity check. It never calls any mutating API, never runs
anything inside a customer instance, and never handles credentials explicitly
(the aliyun CLI default credential chain authenticates every call).

Purpose (from the confirmed tier design):
  * collect the instance facts a clone plan needs (status, zone, type, image,
    IPs, security groups) for the CURRENT credential's account and the ONE
    given region;
  * loss-prevention verification: a console page can report a clone as
    failed while the instances were actually created (real ticket: 25
    duplicated instances). Before the customer retries anything, this
    script answers "does the target instance exist HERE, and how many
    instances does this region have right now".

Output contract: human-readable report by default, `--json` for machines;
every run ends with `STATUS: OK|DEGRADED|FAIL` and `NEXT_ACTION: ...`.
An instance that is NOT FOUND is a VALID finding, never a reason to write
anything. Exit codes: 0 = OK/DEGRADED, 1 = FAIL (every evidence call failed).

Usage:
  python3 clone_readiness_check.py --region-id cn-hangzhou
  python3 clone_readiness_check.py --region-id cn-hangzhou \
      --instance-ids i-source01,i-target02
  python3 clone_readiness_check.py --region-id cn-hangzhou \
      --instance-name my-clone-target --json
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Optional

import _cli
from _constants import (
    DATA_BOUNDARY_NOTES,
    DEFAULT_TIMEOUT,
    STATUS_BATCH_LIMIT,
    TABLE_ROW_LIMIT,
)

_MISSING = "not reported"
_TABLE_COLS = ("instance_id", "instance_name", "status", "zone_id",
               "instance_type", "image_id")
_TABLE_WIDTHS = (14, 18, 10, 14, 20, 24)


def parse_instance_ids(raw: Optional[str]) -> list[str]:
    """Parse a comma-separated instance-ID list; drop blanks, dedupe, keep
    order. Pure function with inline boundary assertions."""
    if not raw:
        return []
    out: list[str] = []
    for part in raw.split(","):
        token = part.strip()
        if token and token not in out:
            out.append(token)
    return out


assert parse_instance_ids("i-a, i-b ,,i-a") == ["i-a", "i-b"]
assert parse_instance_ids(None) == []
assert parse_instance_ids("") == []


def _dig_list(instance: dict, *path: str) -> list:
    """Defensively dig a nested wrapped-list field (ECS response shape
    Item: {..., "IpAddress": [..]}). Absent or malformed -> []."""
    node: Any = instance
    for key in path:
        if not isinstance(node, dict):
            return []
        node = node.get(key)
    return node if isinstance(node, list) else []


def _dig_str(instance: dict, *path: str) -> str:
    """Defensively dig a nested scalar field; tolerate a wrapped list by
    taking its first string element; anything else -> ''."""
    node: Any = instance
    for key in path:
        if not isinstance(node, dict):
            return ""
        node = node.get(key)
    if isinstance(node, str):
        return node
    if isinstance(node, list) and node and isinstance(node[0], str):
        return node[0]
    return ""


def summarize_instance(inst: dict) -> dict:
    """Project one DescribeInstances item onto the report fields.

    Pure function; never invents values -- absent fields become
    'not reported'. Inline boundary assertions below cover a normal item,
    an item with optional fields missing, and an empty item.
    """
    vpc = inst.get("VpcAttributes") if isinstance(
        inst.get("VpcAttributes"), dict) else {}
    private_ips = _dig_list(inst, "VpcAttributes", "PrivateIpAddress",
                            "IpAddress") or \
        _dig_list(inst, "InnerIpAddress", "IpAddress")
    public_ips = _dig_list(inst, "PublicIpAddress", "IpAddress")
    eip = _dig_str(inst, "EipAddress", "IpAddress")
    sgs = _dig_list(inst, "SecurityGroupIds", "SecurityGroupId")
    return {
        "instance_id": str(inst.get("InstanceId") or _MISSING),
        "instance_name": str(inst.get("InstanceName") or _MISSING),
        "status": str(inst.get("Status") or _MISSING),
        "zone_id": str(inst.get("ZoneId") or _MISSING),
        "instance_type": str(inst.get("InstanceType") or _MISSING),
        "image_id": str(inst.get("ImageId") or _MISSING),
        "charge_type": str(inst.get("InstanceChargeType") or _MISSING),
        "network_type": str(inst.get("InstanceNetworkType") or _MISSING),
        "vpc_id": str(vpc.get("VpcId") or _MISSING),
        "v_switch_id": str(vpc.get("VSwitchId") or _MISSING),
        "private_ips": [str(x) for x in private_ips] or [_MISSING],
        "public_ips": ([str(x) for x in public_ips]
                       if public_ips else ([eip] if eip else [_MISSING])),
        "security_group_ids": [str(x) for x in sgs] or [_MISSING],
    }


_TEST_NORMAL = summarize_instance({
    "InstanceId": "i-test0001", "InstanceName": "clone-src",
    "Status": "Running", "ZoneId": "cn-hangzhou-j", "InstanceType": "ecs.g6",
    "ImageId": "m-test0001",
    "PublicIpAddress": {"IpAddress": ["47.0.0.1"]},
    "VpcAttributes": {"PrivateIpAddress": {"IpAddress": ["10.0.0.2"]},
                      "VpcId": "vpc-t", "VSwitchId": "vsw-t"},
    "SecurityGroupIds": {"SecurityGroupId": ["sg-t"]},
})
assert _TEST_NORMAL["instance_id"] == "i-test0001"
assert _TEST_NORMAL["public_ips"] == ["47.0.0.1"]
assert _TEST_NORMAL["private_ips"] == ["10.0.0.2"]
_TEST_PARTIAL = summarize_instance({"InstanceId": "i-p", "Status": "Stopped"})
assert _TEST_PARTIAL["image_id"] == _MISSING
assert _TEST_PARTIAL["public_ips"] == [_MISSING]
assert summarize_instance({})["instance_id"] == _MISSING


def fetch_instances(region: str, instance_name: Optional[str],
                    profile: Optional[str]) -> list[dict]:
    """Page through DescribeInstances for the region, optionally narrowed
    by the exact InstanceName filter the customer provides."""
    params: dict[str, Any] = {"RegionId": region}
    if instance_name:
        params["InstanceName"] = _cli.esc("instance-name", instance_name)
    items = _cli.paginate_next_token(
        "ecs", "DescribeInstances", params, region=region, profile=profile,
        items_path=["Instances", "Instance"],
        token_resp_path=["NextToken"],
    )
    return [i for i in items if isinstance(i, dict)]


def fetch_statuses(region: str, instance_ids: list[str],
                   profile: Optional[str]) -> dict[str, str]:
    """Confirm runtime status via DescribeInstanceStatus (InstanceId.N batch
    form, chunked at the documented batch limit)."""
    statuses: dict[str, str] = {}
    ids = [i for i in instance_ids if i][:STATUS_BATCH_LIMIT * 4]
    for start in range(0, len(ids), STATUS_BATCH_LIMIT):
        chunk = ids[start:start + STATUS_BATCH_LIMIT]
        params: dict[str, Any] = {"RegionId": region}
        for idx, iid in enumerate(chunk, 1):
            params[f"InstanceId.{idx}"] = _cli.esc("instance-id", iid)
        body = _cli.call("ecs", "DescribeInstanceStatus", params,
                         region=region, profile=profile,
                         timeout=DEFAULT_TIMEOUT)
        rows = body.get("InstanceStatuses")
        if isinstance(rows, dict):
            rows = rows.get("InstanceStatus")
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict) and row.get("InstanceId"):
                    statuses[str(row["InstanceId"])] = str(
                        row.get("Status") or _MISSING)
    return statuses


def build_verdict(requested: list[str], found: dict[str, dict],
                  total_in_region: int,
                  name_filtered: bool = False) -> list[str]:
    """Compose the guidance verdict lines strictly from real data."""
    lines: list[str] = []
    for iid in requested:
        if iid in found:
            info = found[iid]
            lines.append(f"{iid}: EXISTS in this account/region "
                         f"(status {info['status']}).")
            if info["status"] == "Running":
                lines.append(f"  note: cloning does NOT require stopping "
                             f"{iid}; data written during capture is not "
                             f"included in the image (consistency point).")
            elif info["status"] == "Stopped":
                lines.append(f"  note: {iid} is stopped; starting it is a "
                             f"customer console action, never this skill's.")
        else:
            lines.append(
                f"{iid}: NOT FOUND in this account/region. Not-found is a "
                f"valid result -- do not react by creating anything, and do "
                f"not assume the console 'clone failed' page was wrong. "
                f"Re-check the account and the region selector first.")
    if name_filtered:
        # An InstanceName filter narrows the server-side response, so this run
        # never saw the whole region: reporting it as an inventory count would
        # understate duplicates that already exist.
        lines.append(
            f"Instances matching the name filter: {total_in_region} "
            f"(NOT the region inventory - the InstanceName filter was applied "
            f"server-side, so the full regional count was not observed this "
            f"run; re-run without --instance-name for the duplicate-count "
            f"check).")
    else:
        lines.append(
            f"Region inventory count seen by this credential: "
            f"{total_in_region} instance(s). After a reported clone FAILURE, "
            f"compare this count with expectations BEFORE any retry: resources "
            f"may exist despite the failure page (real duplicate-creation "
            f"incident on record).")
    return lines


def render_human(uid: str, region: str, requested: list[str],
                 rows: list[dict], statuses: dict[str, str],
                 errors: list[str], name_filtered: bool = False) -> None:
    by_id = {r["instance_id"]: r for r in rows}
    found = {iid: by_id[iid] for iid in requested if iid in by_id}
    shown_rows = list(found.values()) if requested else rows

    print("=" * 74)
    print(" ECS clone readiness - read-only instance facts")
    print("=" * 74)
    print(f" Region                          : {region}")
    print(f" Account UID (this credential)   : {uid or 'unresolved (degraded)'}")
    print(f" {'Instances matching name filter':32s}: {len(rows)}"
          if name_filtered else
          f" {'Instances visible in region':32s}: {len(rows)}")
    if requested:
        print("-" * 74)
        print(" Requested instance verdicts")
        for line in build_verdict(requested, found, len(rows), name_filtered):
            print("  " + line)
    print("-" * 74)
    print(" Instance table")
    print("  " + " | ".join(c.ljust(w) for c, w in
                            zip(_TABLE_COLS, _TABLE_WIDTHS)))
    for info in shown_rows[:TABLE_ROW_LIMIT]:
        print("  " + " | ".join(
            str(info.get(c, _MISSING))[:w].ljust(w)
            for c, w in zip(_TABLE_COLS, _TABLE_WIDTHS)))
    if len(shown_rows) > TABLE_ROW_LIMIT:
        print(f"  ... {len(shown_rows) - TABLE_ROW_LIMIT} more row(s) "
              f"truncated in table view; --json carries all")
    if shown_rows:
        print("-" * 74)
        print(" Detail lines")
        for info in shown_rows[:TABLE_ROW_LIMIT]:
            iid = info["instance_id"]
            print(f"  {iid}  name={info['instance_name']} "
                  f"status={statuses.get(iid, info['status'])} "
                  f"type={info['instance_type']} image={info['image_id']}")
            print(f"      private={','.join(info['private_ips'])} "
                  f"public={','.join(info['public_ips'])}")
            print(f"      security_groups={','.join(info['security_group_ids'])} "
                  f"vpc={info['vpc_id']} vswitch={info['v_switch_id']}")
    if errors:
        print("-" * 74)
        print(" Graceful Degradation Log")
        for err in errors:
            print(f"  [WARN|DEGRADE] {err}")
    print("-" * 74)
    print(" Data boundary (always restate with the findings)")
    for note in DATA_BOUNDARY_NOTES:
        print(f"  - {note}")
    print(" NOTE: whether the source image is a marketplace image is NOT "
          "derivable from these reads; it is a customer console self-check "
          "item before any export discussion.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only instance fact verification for ECS clone "
                    "planning and loss-prevention checks (single region, "
                    "current credential's account only).",
    )
    parser.add_argument("--region-id", required=True,
                        help="Alibaba Cloud region ID, e.g. cn-hangzhou "
                             "(required: every read-only query is scoped to "
                             "one region)")
    parser.add_argument("--instance-ids", default=None,
                        help="Comma-separated instance IDs to verify "
                             "(source and/or clone targets)")
    parser.add_argument("--instance-name", default=None,
                        help="Exact InstanceName filter (as the customer "
                             "reads it in the console)")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    try:
        region = _cli.esc("region-id", args.region_id.strip())
    except _cli.CliError as e:
        msg = str(e)
        print(f"[ERROR] {msg}", file=sys.stderr)
        bad_region_action = ("ask the customer for the exact region shown in "
                             "the console region selector (e.g. cn-hangzhou "
                             "format)")
        if args.json:
            print(json.dumps({"status": "FAIL", "error": msg,
                              "next_action": bad_region_action}, indent=2))
            print("STATUS: FAIL", file=sys.stderr)
            print(f"NEXT_ACTION: {bad_region_action}", file=sys.stderr)
        else:
            print("STATUS: FAIL")
            print(f"NEXT_ACTION: {bad_region_action}")
        sys.exit(1)

    requested = parse_instance_ids(args.instance_ids)
    # InstanceName is a server-side filter, so a name-filtered run reports a
    # subset, never the regional inventory.
    name_filtered = bool(args.instance_name)
    errors: list[str] = []

    _cli.check_cli_available()

    uid = _cli.resolve_account_id(region=region, profile=args.profile)
    if not uid:
        errors.append("sts get-caller-identity failed or returned no UID; "
                      "the account-scope label is degraded, instance reads "
                      "continue.")

    try:
        raw_items = fetch_instances(region, args.instance_name, args.profile)
    except _cli.CliError as e:
        msg = str(e)
        print(f"[WARN] DescribeInstances failed: {msg}", file=sys.stderr)
        fail_action = ("report this failure verbatim (NoPermission or "
                       "ImplicitDeny -> grant the read-only actions listed "
                       "in references/ram-policies.md; a value the script "
                       "rejected as invalid -> correct that input, nothing "
                       "was sent and this is not a permission problem; "
                       "invalid region -> "
                       "confirm the region with the customer). Do NOT "
                       "hand-write aliyun CLI replacements and do NOT fall "
                       "back to any other tool.")
        if args.json:
            print(json.dumps({"region_id": region, "status": "FAIL",
                              "error": msg, "next_action": fail_action},
                             indent=2))
            print("STATUS: FAIL", file=sys.stderr)
            print(f"NEXT_ACTION: {fail_action}", file=sys.stderr)
        else:
            print("STATUS: FAIL")
            print(f"NEXT_ACTION: {fail_action}")
        sys.exit(1)

    rows = [summarize_instance(i) for i in raw_items]
    by_id = {r["instance_id"]: r for r in rows}
    found_ids = [iid for iid in requested if iid in by_id]
    missing_ids = [iid for iid in requested if iid not in by_id]

    statuses: dict[str, str] = {}
    try:
        ids_for_status = requested or [r["instance_id"] for r in rows]
        if len([i for i in ids_for_status if i]) > STATUS_BATCH_LIMIT * 4:
            errors.append(
                f"DescribeInstanceStatus covered only the first "
                f"{STATUS_BATCH_LIMIT * 4} of {len(ids_for_status)} instance "
                f"IDs; the runtime status of the remainder is unconfirmed "
                f"this run.")
        statuses = fetch_statuses(region, ids_for_status, args.profile)
    except _cli.CliError as e:
        statuses = {}
        errors.append(f"DescribeInstanceStatus failed ({e}); runtime-status "
                      "confirmation degraded to the DescribeInstances "
                      "status field.")

    status = "DEGRADED" if errors else "OK"
    verdicts = build_verdict(requested,
                             {iid: by_id[iid] for iid in found_ids},
                             len(rows), name_filtered)

    if requested and missing_ids and not found_ids:
        next_action = (
            "requested instance(s) are NOT visible to this credential/region: "
            "re-check region and account with the customer BEFORE concluding; "
            "missing is a valid finding -- never create or retry anything "
            "from this skill"
        )
    else:
        next_action = (
            "use these facts with scripts/clone_guidance.py --plan to pick "
            "the clone path, then --checklist after the customer performs it"
        )

    if args.json:
        by_id_found = {iid: by_id[iid] for iid in found_ids}
        print(json.dumps({
            "region_id": region,
            "account_uid": uid or None,
            "requested_instance_ids": requested,
            "found": [by_id_found[i] for i in found_ids],
            "missing": missing_ids,
            "instance_count_in_region": len(rows),
            "instance_count_scope": ("InstanceName-filtered subset; the full "
                                      "regional count was not observed"
                                      if name_filtered else
                                      "all instances visible in this region "
                                      "for this credential"),
            "instances": rows[:TABLE_ROW_LIMIT],
            "status_confirmed": statuses,
            "verdict_lines": verdicts,
            "errors": errors,
            "data_boundary_notes": DATA_BOUNDARY_NOTES,
            "status": status,
            "next_action": next_action,
        }, indent=2))
        # Keep stdout pure JSON: the contract lines go to stderr in --json mode.
        print(f"STATUS: {status}", file=sys.stderr)
        print(f"NEXT_ACTION: {next_action}", file=sys.stderr)
    else:
        render_human(uid, region, requested, rows, statuses, errors,
                     name_filtered=name_filtered)
        print(f"\nSTATUS: {status}")
        print(f"NEXT_ACTION: {next_action}")
    sys.exit(0)


if __name__ == "__main__":
    main()
