#!/usr/bin/env python3
"""
disk_dr_inventory.py -- single entry point of the ECS disk replication DR guide
================================================================================
SECURITY: This skill is strictly READ-ONLY. This script only invokes the
whitelisted read-only queries (ECS DescribeInstances / DescribeDisks /
DescribeSnapshots plus the STS identity check) through the shared CLI layer
(_cli.py). It never creates, modifies or deletes any cloud resource, never
runs commands inside customer instances, and never reads, prints or accepts
AccessKey credentials -- authentication is resolved exclusively by the aliyun
CLI default credential chain.

What it produces
----------------
A per-region "disk DR evidence inventory" for the account behind the active
credential: instances (region/zone/status), cloud disks (category, zone,
auto-snapshot flag) and snapshots (existence, type, source disk), plus a DR
findings list, an explicit visibility-scope declaration and the official
guidance doc URLs the Agent may cite. It answers the factual half of questions
like "does my ECS have any disaster recovery", "is any DR or backup running on
my account" and "which of my disks already have zone-level redundancy".
Replication pair / consistency group objects are NOT visible through this
read-only surface; the report says so explicitly instead of guessing.

Output contract (both text and --json modes):
  * every queried region contributes an inventory block or an explicit error
    record; failures degrade with [WARN] on stderr and never abort the run;
  * the run ends with `STATUS: OK|DEGRADED|FAIL` plus a `NEXT_ACTION:` line.

Exit codes: 0 = OK or DEGRADED (a usable report was produced);
1 = FAIL (no usable evidence at all); 2 = usage error (bad arguments).

Usage:
  python3 disk_dr_inventory.py --region-id cn-hangzhou
  python3 disk_dr_inventory.py --region-id cn-hangzhou,cn-shanghai --json
  python3 disk_dr_inventory.py --region-id cn-beijing --instance-id i-2zexxxxxxx
  python3 disk_dr_inventory.py --region-id cn-beijing --disk-id d-2zexxxxxxx
"""

from __future__ import annotations

import argparse
import json
import re
import sys

import _cli
from _constants import (
    API_VERSIONS,
    DISK_CATEGORY_NOTES,
    DISK_ID_RE,
    DOC_URLS,
    INSTANCE_ID_RE,
    MAX_REGIONS,
    PERMISSION_HINT,
    REGION_ID_RE,
    REPLICA_VISIBILITY_NOTE,
    SCOPE_NOT_COVERED,
    SKILL_NAME,
    ZONE_REDUNDANT_DISK_CATEGORIES,
)


# ---------------------------------------------------------------------------
# Input parsing / validation
# ---------------------------------------------------------------------------

def parse_regions(raw: str) -> list:
    """Split and validate a comma-separated region-id list (order preserved,
    duplicates removed). Raises ValueError on any invalid input."""
    regions = [r.strip() for r in raw.split(",") if r.strip()]
    if not regions:
        raise ValueError("no region id given")
    if len(regions) > MAX_REGIONS:
        raise ValueError(
            "too many regions (" + str(len(regions)) + "); pass at most "
            + str(MAX_REGIONS) + " per run")
    for region in regions:
        if not re.match(REGION_ID_RE, region):
            raise ValueError("invalid region id: " + repr(region))
    seen = set()
    ordered = []
    for region in regions:
        if region not in seen:
            seen.add(region)
            ordered.append(region)
    return ordered


# ---------------------------------------------------------------------------
# Read-only evidence collection (one region at a time; failures degrade)
# ---------------------------------------------------------------------------

def fetch_instances(region: str, instance_id, profile) -> list:
    params = {"RegionId": region}
    if instance_id:
        params["InstanceIds"] = json.dumps([instance_id])
    items = _cli.paginate_next_token(
        "ecs", "DescribeInstances", params, region=region, profile=profile,
        items_path=["Instances", "Instance"], token_resp_path=["NextToken"])
    rows = []
    for inst in items:
        if not isinstance(inst, dict):
            continue
        rows.append({
            "instance_id": inst.get("InstanceId"),
            "instance_name": inst.get("InstanceName"),
            "status": inst.get("Status"),
            "zone_id": inst.get("ZoneId"),
            "instance_charge_type": inst.get("InstanceChargeType"),
        })
    return rows


def fetch_disks(region: str, instance_id, disk_id, profile) -> list:
    params = {"RegionId": region}
    if disk_id:
        params["DiskIds"] = json.dumps([disk_id])
    elif instance_id:
        params["InstanceId"] = instance_id
    items = _cli.paginate_next_token(
        "ecs", "DescribeDisks", params, region=region, profile=profile,
        items_path=["Disks", "Disk"], token_resp_path=["NextToken"])
    rows = []
    for disk in items:
        if not isinstance(disk, dict):
            continue
        category = str(disk.get("Category") or "unknown")
        rows.append({
            "disk_id": disk.get("DiskId"),
            "disk_name": disk.get("DiskName"),
            "category": category,
            "category_note": DISK_CATEGORY_NOTES.get(category, ""),
            "disk_type": disk.get("Type"),
            "status": disk.get("Status"),
            "size_gib": disk.get("Size"),
            "zone_id": disk.get("ZoneId"),
            "instance_id": disk.get("InstanceId"),
            "encrypted": disk.get("Encrypted"),
            "multi_attach": disk.get("MultiAttach"),
            "disk_charge_type": disk.get("DiskChargeType"),
            "delete_with_instance": disk.get("DeleteWithInstance"),
            "enable_auto_snapshot": disk.get("EnableAutoSnapshot"),
        })
    return rows


def fetch_snapshots(region: str, instance_id, disk_id, profile) -> list:
    params = {"RegionId": region}
    if disk_id:
        params["DiskId"] = disk_id
    elif instance_id:
        params["InstanceId"] = instance_id
    items = _cli.paginate_next_token(
        "ecs", "DescribeSnapshots", params, region=region, profile=profile,
        items_path=["Snapshots", "Snapshot"], token_resp_path=["NextToken"])
    rows = []
    for snap in items:
        if not isinstance(snap, dict):
            continue
        rows.append({
            "snapshot_id": snap.get("SnapshotId"),
            "snapshot_name": snap.get("SnapshotName"),
            "status": snap.get("Status"),
            # Echoed verbatim: the script never re-interprets enum values.
            "snapshot_type": snap.get("SnapshotType"),
            "usage": snap.get("Usage"),
            "source_disk_id": snap.get("SourceDiskId"),
            "source_disk_type": snap.get("SourceDiskType"),
            "source_disk_size_gib": snap.get("SourceDiskSize"),
            "encrypted": snap.get("Encrypted"),
            "creation_time": snap.get("CreationTime"),
        })
    return rows


def collect_region(region: str, instance_id, disk_id, profile) -> dict:
    """Run the three whitelisted read-only queries for one region.

    Each query failure is recorded (with a permission hint when the error
    looks authorization-related), printed as [WARN] on stderr, and the loop
    continues -- one failed query never aborts the whole inventory.
    """
    block = {
        "region_id": region,
        "instances": [],
        "disks": [],
        "snapshots": [],
        "errors": [],
    }
    fetchers = [
        ("DescribeInstances", "instances",
         lambda: fetch_instances(region, instance_id, profile)),
        ("DescribeDisks", "disks",
         lambda: fetch_disks(region, instance_id, disk_id, profile)),
        ("DescribeSnapshots", "snapshots",
         lambda: fetch_snapshots(region, instance_id, disk_id, profile)),
    ]
    for api_name, slot, fetch in fetchers:
        try:
            block[slot] = fetch()
        except _cli.CliError as exc:
            message = str(exc)
            print("[WARN] " + region + " " + api_name + " failed: " + message,
                  file=sys.stderr)
            error = {
                "region_id": region,
                "api": api_name,
                "code": exc.code or "Unknown",
                "message": message,
            }
            if _cli.is_permission_error(exc):
                error["hint"] = PERMISSION_HINT
            block["errors"].append(error)
    return block


# ---------------------------------------------------------------------------
# Analysis (pure functions over collected data -- no extra API calls)
# ---------------------------------------------------------------------------

def analyze_block(block: dict) -> list:
    """Derive per-region DR findings from the collected inventory rows."""
    region = block["region_id"]
    disks = block["disks"]
    snapshots = block["snapshots"]
    findings = []

    category_counts = {}
    for disk in disks:
        key = str(disk.get("category") or "unknown")
        category_counts[key] = category_counts.get(key, 0) + 1
    zone_redundant = [
        d for d in disks
        if str(d.get("category")) in ZONE_REDUNDANT_DISK_CATEGORIES
    ]
    auto_snapshot_disks = [
        d for d in disks if d.get("enable_auto_snapshot") is True
    ]

    block["analysis"] = {
        "instance_count": len(block["instances"]),
        "disk_count": len(disks),
        "disk_category_counts": category_counts,
        "zone_redundant_disk_ids": [d.get("disk_id") for d in zone_redundant],
        "auto_snapshot_enabled_disk_ids": [
            d.get("disk_id") for d in auto_snapshot_disks
        ],
        "snapshot_count": len(snapshots),
    }

    if block["errors"] and not disks and not snapshots \
            and not block["instances"]:
        findings.append(
            region + ": no evidence could be collected (every query failed); "
            "see the error records -- do NOT conclude 'no DR resources exist' "
            "from failed queries.")
        return findings

    if zone_redundant:
        findings.append(
            region + ": " + str(len(zone_redundant)) + " zone-redundant ESSD "
            "disk(s) found (" + ", ".join(
                str(d.get("disk_id")) for d in zone_redundant_safe(zone_redundant))
            + ") -- these disks replicate data across zones of this region by "
            "platform design (see the regional-essd doc in guidance_docs).")
    elif disks:
        findings.append(
            region + ": " + str(len(disks)) + " disk(s) found, none in a "
            "zone-redundant category -- a zone failure is not absorbed at the "
            "disk layer for these disks.")

    if snapshots:
        findings.append(
            region + ": " + str(len(snapshots)) + " snapshot(s) exist. "
            "Snapshots are stored in the region where they were created and "
            "are NOT copied to other regions automatically; cross-region copy "
            "is a manual customer operation (see references/"
            "dr-capability-boundary.md).")
    else:
        findings.append(
            region + ": no snapshot found for the queried scope -- no "
            "snapshot-based backup evidence in this region.")

    if auto_snapshot_disks:
        findings.append(
            region + ": " + str(len(auto_snapshot_disks)) + " disk(s) have "
            "the automatic-snapshot flag enabled -- an automatic snapshot "
            "policy is applied to them (policy lifecycle belongs to the "
            "snapshot management domain).")

    if not zone_redundant and not snapshots:
        findings.append(
            region + ": no disk-level redundancy and no snapshot backup "
            "evidence for the queried scope. A single ECS instance has no "
            "automatic failover; disk-level DR requires async replication "
            "(replication pair / consistency group) or zone-redundant ESSD -- "
            "see references/dr-capability-boundary.md.")
    return findings


def zone_redundant_safe(disks: list) -> list:
    """Cap the id list echoed inside a findings line (keeps output stable)."""
    return disks[:10]


def compute_status(blocks: list) -> str:
    total_calls = len(blocks) * 3
    failed_calls = sum(len(b["errors"]) for b in blocks)
    if failed_calls == 0:
        return "OK"
    if total_calls and failed_calls >= total_calls:
        return "FAIL"
    return "DEGRADED"


def build_suggestions(status: str) -> list:
    suggestions = [
        "Route the customer's request with references/root-causes.md: group A "
        "(DR capability question) -> answer from references/"
        "dr-capability-boundary.md plus this inventory; group B (charges "
        "suspected from DR/backup) -> relay the evidence list with the scope "
        "declaration and hand off per references/handoff-map.md; group C "
        "(in-guest problems after copying data) -> hand off with the "
        "read-only self-check list in references/self-check-commands.md.",
        "For step-by-step console operations (create a replication pair or "
        "consistency group, run a DR failover, delete a replication pair), "
        "cite ONLY the guidance_docs URLs and add the risk notice, expected "
        "result and post-step verification required by SKILL.md; the customer "
        "executes every such step themselves.",
    ]
    if status == "DEGRADED":
        suggestions.append(
            "Report every degraded query with its error code; for "
            "NoPermission / ImplicitDeny, point to references/ram-policies.md "
            "for the minimal read-only grant, then rerun this script.")
    return suggestions


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_text(report: dict) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("ECS disk replication / DR evidence inventory (read-only)")
    lines.append("=" * 70)
    lines.append("Skill          : " + report["skill"])
    lines.append("Session id     : " + report["session_id"])
    lines.append("Account UID    : " + report["uid"]
                 + ("  (auto-derived via aliyun sts get-caller-identity)"
                    if report["uid"] != "unavailable" else ""))
    lines.append("Regions queried: " + ", ".join(report["regions_queried"]))
    filters = report["filters"]
    lines.append("Filters        : instance_id=" + str(filters["instance_id"] or "-")
                 + ", disk_id=" + str(filters["disk_id"] or "-"))
    lines.append("")
    for block in report["inventory"]:
        region = block["region_id"]
        lines.append("-" * 70)
        lines.append("Region: " + region)
        lines.append("-" * 70)
        lines.append("Instances (" + str(len(block["instances"])) + "):")
        for inst in block["instances"]:
            lines.append("  " + str(inst.get("instance_id"))
                         + "  zone=" + str(inst.get("zone_id"))
                         + "  status=" + str(inst.get("status"))
                         + "  charge=" + str(inst.get("instance_charge_type")))
        lines.append("Disks (" + str(len(block["disks"])) + "):")
        for disk in block["disks"]:
            lines.append("  " + str(disk.get("disk_id"))
                         + "  category=" + str(disk.get("category"))
                         + "  type=" + str(disk.get("disk_type"))
                         + "  size=" + str(disk.get("size_gib")) + "GiB"
                         + "  zone=" + str(disk.get("zone_id"))
                         + "  status=" + str(disk.get("status"))
                         + "  auto_snapshot=" + str(disk.get("enable_auto_snapshot")))
            if disk.get("category_note"):
                lines.append("      note: " + disk["category_note"])
        lines.append("Snapshots (" + str(len(block["snapshots"])) + "):")
        for snap in block["snapshots"]:
            lines.append("  " + str(snap.get("snapshot_id"))
                         + "  type=" + str(snap.get("snapshot_type"))
                         + "  status=" + str(snap.get("status"))
                         + "  source_disk=" + str(snap.get("source_disk_id"))
                         + "  created=" + str(snap.get("creation_time")))
        for error in block["errors"]:
            lines.append("  [WARN] " + error["api"] + " failed: "
                         + error["code"] + ": " + error["message"][:200])
            if error.get("hint"):
                lines.append("         hint: " + error["hint"])
        lines.append("")
    lines.append("DR findings:")
    for finding in report["dr_findings"]:
        lines.append("  * " + finding)
    lines.append("")
    lines.append("Visibility scope declaration:")
    scope = report["scope_declaration"]
    lines.append("  account      : " + scope["account_uid"])
    lines.append("  regions      : " + ", ".join(scope["regions_queried"]))
    lines.append("  evidence from: " + ", ".join(scope["apis_used"]))
    lines.append("  NOT covered  :")
    for item in scope["not_covered"]:
        lines.append("    - " + item)
    lines.append("")
    lines.append("Guidance docs (the only URLs this skill may cite):")
    for key, url in report["guidance_docs"].items():
        lines.append("  " + key + ": " + url)
    lines.append("")
    lines.append("Summary")
    lines.append("-------")
    lines.append(report["summary"])
    lines.append("")
    lines.append("Suggestions:")
    for suggestion in report["suggestions"]:
        lines.append("  * " + suggestion)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Offline regression lock (no cloud, no files, no subprocess): run with
#   python3 scripts/disk_dr_inventory.py --selftest
# Locks the DR-readiness decision core. Two safety invariants matter most:
# (1) when every query failed and nothing was collected the analysis must emit
#     the fail-closed "do NOT conclude no DR resources" line, never a
#     "zone-redundant / snapshot" conclusion; (2) snapshots present must not
#     also be reported as "no snapshot found" (an under-counted backup would
#     wrongly push the customer toward replication they already have).
# ---------------------------------------------------------------------------

def _run_selftest() -> int:
    rc = 0
    checked: list = []

    def expect(name, cond):
        nonlocal rc
        checked.append(name)
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            rc = 1

    def _raises(fn, exc_type):
        try:
            fn()
            return False
        except exc_type:
            return True

    def block(**kw):
        b = {"region_id": "cn-hangzhou", "instances": [], "disks": [],
             "snapshots": [], "errors": []}
        b.update(kw)
        return b

    # --- parse_regions ----------------------------------------------------
    expect("pr_dedup_order",
           parse_regions("cn-hangzhou, cn-shanghai ,cn-hangzhou")
           == ["cn-hangzhou", "cn-shanghai"])
    expect("pr_max_bound_raises",
           _raises(lambda: parse_regions(",".join(["cn-region%d" % i
                          for i in range(MAX_REGIONS + 1)])), ValueError))
    expect("pr_empty_raises", _raises(lambda: parse_regions(""), ValueError))
    expect("pr_invalid_raises", _raises(lambda: parse_regions("bad region!"), ValueError))

    # --- analyze_block: zone-redundant + auto snapshot --------------------
    b = block(
        instances=[{"i": 1}],
        disks=[{"disk_id": "d-1", "category": "cloud_essd", "enable_auto_snapshot": True},
               {"disk_id": "d-2", "category": "cloud_regional_disk_auto",
                "enable_auto_snapshot": False}],
        snapshots=[{"snapshot_id": "s-1"}],
    )
    findings = analyze_block(b)
    joined = "\n".join(findings)
    expect("an_zone_redundant_line", "zone-redundant ESSD" in joined and "d-2" in joined)
    expect("an_no_none_redundant_when_zr", "none in a zone-redundant category" not in joined)
    expect("an_snapshot_present_line", "snapshot(s) exist" in joined)
    expect("an_not_no_snapshot_claim", "no snapshot found" not in joined)
    expect("an_auto_snapshot_line", "automatic-snapshot" in joined)
    expect("an_analysis_ids",
           b["analysis"]["zone_redundant_disk_ids"] == ["d-2"]
           and b["analysis"]["auto_snapshot_enabled_disk_ids"] == ["d-1"]
           and b["analysis"]["snapshot_count"] == 1)

    # --- analyze_block: normal disk, no snapshot, no zr -------------------
    b2 = block(disks=[{"disk_id": "d-9", "category": "cloud_essd",
                       "enable_auto_snapshot": False}])
    f2 = "\n".join(analyze_block(b2))
    expect("an_none_redundant_line", "none in a zone-redundant category" in f2)
    expect("an_no_snapshot_found", "no snapshot found" in f2)
    expect("an_no_dr_conclusion", "no disk-level redundancy and no snapshot" in f2)

    # --- analyze_block: every query failed -> fail-closed, no conclusions -
    b3 = block(errors=[{"api": "DescribeDisks"}], instances=[], disks=[], snapshots=[])
    f3 = analyze_block(b3)
    expect("an_fail_closed_single_line",
           len(f3) == 1 and "do NOT conclude" in f3[0])
    expect("an_fail_closed_no_redundant_claim",
           not any("zone-redundant" in x for x in f3))

    # --- zone_redundant_safe caps at 10 ----------------------------------
    expect("zrs_caps_10",
           len(zone_redundant_safe([{"disk_id": str(i)} for i in range(25)])) == 10)

    # --- compute_status ---------------------------------------------------
    expect("cs_ok", compute_status([block(), block()]) == "OK")
    expect("cs_degraded_partial",
           compute_status([block(errors=[{"a": 1}]), block()]) == "DEGRADED")
    expect("cs_fail_all",
           compute_status([block(errors=[1, 2, 3]), block(errors=[4, 5, 6])]) == "FAIL")
    expect("cs_suggestions_degraded_has_permission_hint",
           any("NoPermission" in s for s in build_suggestions("DEGRADED")))
    expect("cs_suggestions_ok_no_permission_hint",
           not any("NoPermission" in s for s in build_suggestions("OK")))

    print("SELFTEST: {} ({} checks)".format(
        "PASS" if rc == 0 else "FAIL", len(checked)))
    return rc


def main() -> None:
    if "--selftest" in sys.argv[1:]:
        sys.exit(_run_selftest())
    parser = argparse.ArgumentParser(
        description="Read-only per-region inventory of ECS instances, disks "
                    "and snapshots as the evidence base for disk "
                    "replication / DR guidance (no cloud resource is "
                    "modified).")
    parser.add_argument(
        "--region-id", required=True,
        help="Region id to query; several regions can be passed "
             "comma-separated (e.g. cn-hangzhou,cn-shanghai). Results are "
             "per region and are never extrapolated across regions.")
    parser.add_argument(
        "--instance-id", default=None,
        help="Optional instance id filter (i-...)")
    parser.add_argument(
        "--disk-id", default=None,
        help="Optional disk id filter (d-...)")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true",
                        help="Emit the machine-readable report")
    args = parser.parse_args()

    try:
        regions = parse_regions(args.region_id)
    except ValueError as exc:
        parser.error(str(exc))
    if args.instance_id and not re.match(INSTANCE_ID_RE, args.instance_id):
        parser.error("invalid instance id: " + repr(args.instance_id))
    if args.disk_id and not re.match(DISK_ID_RE, args.disk_id):
        parser.error("invalid disk id: " + repr(args.disk_id))

    _cli.check_cli_available()

    uid = _cli.resolve_account_id(profile=args.profile)
    auto_filled = []
    if uid:
        auto_filled.append({
            "parameter": "uid",
            "value": uid,
            "source": "auto-derived via aliyun sts get-caller-identity",
        })
    else:
        uid = "unavailable"

    blocks = [
        collect_region(region, args.instance_id, args.disk_id, args.profile)
        for region in regions
    ]

    findings = []
    for block in blocks:
        findings.extend(analyze_block(block))
    findings.append(REPLICA_VISIBILITY_NOTE)

    status = compute_status(blocks)
    all_errors = [e for b in blocks for e in b["errors"]]

    total_instances = sum(len(b["instances"]) for b in blocks)
    total_disks = sum(len(b["disks"]) for b in blocks)
    total_snapshots = sum(len(b["snapshots"]) for b in blocks)
    summary = (
        "Queried " + str(len(regions)) + " region(s) (" + ", ".join(regions) +
        ") of account " + uid + ": " + str(total_instances) + " instance(s), "
        + str(total_disks) + " disk(s), " + str(total_snapshots) +
        " snapshot(s) collected through read-only queries. " +
        ("All queries succeeded." if status == "OK" else
         str(len(all_errors)) + " query(queries) failed and are recorded as "
         "[WARN] entries; the remaining evidence is still usable."
         if status == "DEGRADED" else
         "Every query failed; no evidence is available -- do NOT draw any "
         "'no DR resources' conclusion from this run.")
    )

    if status == "OK" or status == "DEGRADED":
        next_action = (
            "Relay the inventory and route the request per references/"
            "root-causes.md (group A capability answer / group B evidence "
            "handoff / group C self-check handoff); cite only the "
            "guidance_docs URLs." if status == "OK" else
            "Report the degraded queries with their error codes; for "
            "NoPermission / ImplicitDeny grant the read-only actions in "
            "references/ram-policies.md and rerun this script."
        )
    else:
        next_action = (
            "Check credentials with scripts/sts_token.py (run `aliyun "
            "configure` if the chain is unconfigured), verify the region ids, "
            "grant the read-only actions in references/ram-policies.md when "
            "the errors are NoPermission / ImplicitDeny, then rerun."
        )

    report = {
        "skill": SKILL_NAME,
        "session_id": _cli.session_id(),
        "uid": uid,
        "auto_filled": auto_filled,
        "regions_queried": regions,
        "filters": {"instance_id": args.instance_id, "disk_id": args.disk_id},
        "inventory": blocks,
        "dr_findings": findings,
        "scope_declaration": {
            "account_uid": uid,
            "regions_queried": regions,
            "apis_used": [
                "ecs DescribeInstances (" + API_VERSIONS["ecs"] + ")",
                "ecs DescribeDisks (" + API_VERSIONS["ecs"] + ")",
                "ecs DescribeSnapshots (" + API_VERSIONS["ecs"] + ")",
                "sts get-caller-identity (" + API_VERSIONS["sts"] + ")",
            ],
            "not_covered": SCOPE_NOT_COVERED,
        },
        "guidance_docs": DOC_URLS,
        "errors": all_errors,
        "summary": summary,
        "suggestions": build_suggestions(status),
        "status": status,
        "next_action": next_action,
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_text(report))
    print("")
    print("STATUS: " + status)
    print("NEXT_ACTION: " + next_action)
    sys.exit(0 if status in ("OK", "DEGRADED") else 1)


if __name__ == "__main__":
    main()
