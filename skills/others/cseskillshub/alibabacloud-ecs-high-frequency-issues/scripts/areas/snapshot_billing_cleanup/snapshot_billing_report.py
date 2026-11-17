#!/usr/bin/env python3
"""Entry point for ECS snapshot billing attribution and cleanup preparation.

SECURITY NOTES
    * Evidence collection uses the aliyun CLI with actions on the declared
      whitelist only (see references/ram-policies.md). Credentials come solely
      from the default credential chain of the locally configured CLI; this
      script never accepts, reads, stores, echoes or passes key material.
    * Every subprocess call runs as an argument list (no shell), with a
      per-call timeout, and error text is credential-masked before display.
    * The two non-destructive-by-default write dispatches (one snapshot backup
      of a named disk, one whitelisted in-guest reading) run ONLY in their
      gated modes, ONLY after the operator passed --user-confirmed together
      with a --confirmation-scope that names the exact region and target, and
      ONLY after the customer approved the notice this script prints when the
      gate is not yet satisfied. Every destructive operation (removing a
      snapshot, image or policy, detaching or releasing disks, changing files)
      is never dispatched here: it appears as manual guidance only.

Usage examples
    python3 scripts/areas/snapshot_billing_cleanup/snapshot_billing_report.py --region-id cn-hangzhou
    python3 scripts/areas/snapshot_billing_cleanup/snapshot_billing_report.py --region-id cn-hangzhou \
        --region-id cn-beijing --disk-id d-2zeexample9f3b0f6b7f --symptom delete
    python3 scripts/areas/snapshot_billing_cleanup/snapshot_billing_report.py --region-id cn-hangzhou \
        --instance-id i-2zeexample66e477acae --mode guest-probe \
        --guest-command "df -h" --user-confirmed \
        --confirmation-scope "cn-hangzhou i-2zeexample66e477acae df -h approved"
    python3 scripts/areas/snapshot_billing_cleanup/snapshot_billing_report.py --region-id cn-hangzhou \
        --mode prepare-snapshot --disk-id d-2zeexample9f3b0f6b7f \
        --user-confirmed --confirmation-scope "cn-hangzhou d-2zeexample9f3b0f6b7f"
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import base64
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from _cli import (
    CliError,
    _PACKAGE_NAME,
    build_user_agent,
    mask_credentials,
    new_session_id,
    paginate,
    run_cli,
)
from _constants import (
    ACTION_CREATE_SNAPSHOT,
    ACTION_DESCRIBE_DISKS,
    ACTION_DESCRIBE_IMAGES,
    ACTION_DESCRIBE_INSTANCES,
    ACTION_DESCRIBE_INVOCATIONS,
    ACTION_DESCRIBE_SNAPSHOTS,
    ACTION_RUN_COMMAND,
    BANNER,
    BILLING_ITEM_LABEL,
    BLOCKER_ORDER,
    CANDIDATE_FILE_PREFIX,
    CANDIDATE_FILE_RE,
    CAPACITY_LENSES,
    CLI_TIMEOUT_SECONDS,
    CLOUD_ASSISTANT_KIND_LINUX,
    CLOUD_ASSISTANT_KIND_WINDOWS,
    CODE_IMPLICIT_DENY,
    CODE_NO_PERMISSION,
    DEDUCTION_FACTS,
    ERROR_STRING_INSTANCE_STATE,
    FINAL_ANSWER_BANNER,
    GUEST_BLOCKED_TOKENS,
    GUEST_BLOCKED_WORDS,
    GUEST_PATH_COMMANDS,
    GUEST_READINGS_LINUX,
    GUEST_READINGS_WINDOWS,
    HANDOFFS,
    IMAGE_PROBE_PAGE_SIZE,
    LINUX_PATH_RE,
    MAX_PAGES,
    NOT_RETURNED,
    PAGE_SIZE,
    POLL_DEADLINE_SECONDS,
    POLL_INTERVAL_SECONDS,
    PRODUCT_ECS,
    QUOTA_NOTES,
    REGROWTH_SOURCES,
    SKILL_NAME,
    SNAPSHOT_FIRST_RULE,
    SNAPSHOT_STORAGE_FACTS,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
    USAGE_BLOCKING_STATES,
    WINDOWS_PATH_RE,
)
from sts_token import (
    fetch_caller_identity,
    identity_guidance_lines,
    uid_traceability_label,
)

EXIT_BY_STATUS = {STATUS_OK: 0, STATUS_DEGRADED: 1, STATUS_FAIL: 2}
MAX_REGIONS_PER_RUN = 20
MAX_USAGE_PROBES = 20
INVOCATION_TERMINAL = (
    "Finished", "Success", "Failed", "Stopped", "Timeout", "PartialFailed",
    "Error", "Canceled", "Cancelled",
)
SNAPSHOT_NAME_RE = r"^[A-Za-z][A-Za-z0-9:_.-]{1,127}$"


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def field(item: Dict[str, Any], key: str) -> str:
    """Return one API field verbatim, or the declared missing marker."""
    value = (item or {}).get(key)
    if value in (None, ""):
        return NOT_RETURNED
    return str(value)


def to_int(value: Any) -> Optional[int]:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _unwrap_list(payload: Dict[str, Any], outer: str, inner: str) -> List[Dict[str, Any]]:
    container = (payload or {}).get(outer) or {}
    items = container.get(inner) if isinstance(container, dict) else container
    if isinstance(items, dict):
        items = [items]
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def _notice(text: str) -> str:
    lines = ["", "USER CONFIRMATION REQUIRED (nothing has been executed):",
             "-" * 64]
    lines.extend("  {0}".format(line) for line in text.strip().splitlines())
    lines.append("-" * 64)
    lines.append('  Re-run the same command adding --user-confirmed and')
    lines.append('  --confirmation-scope "<region> <target> <action> approved"')
    lines.append('  ONLY AFTER the customer explicitly approved the notice.')
    return "\n".join(lines)


def _scope_confirms(scope_text: str, required_items: Sequence[str]) -> bool:
    lowered = (scope_text or "").lower()
    return all(str(item).lower() in lowered for item in required_items)


# --------------------------------------------------------------------------- #
# Guest reading validation (class B whitelist, enforced before any dispatch)
# --------------------------------------------------------------------------- #
def validate_guest_request(
    reading: Optional[str], guest_path: Optional[str]
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return ``(command_text, script_type, refusal_reason)``.

    Accepts exactly one whitelisted, information-only guest reading per call.
    Anything chained, redirected, quoted or destructive is refused with the
    reason stated; the caller must relay that refusal and stop.
    """
    if not reading or not reading.strip():
        return None, None, "no --guest-command given; name exactly one whitelisted reading"
    cleaned = re.sub(r"\s+", " ", reading.strip())
    if len(cleaned) > 120:
        return None, None, "guest reading rejected: too long"
    for token in GUEST_BLOCKED_TOKENS:
        if token in cleaned:
            return None, None, (
                "guest reading rejected: character sequence {0!r} is outside the "
                "low-risk whitelist (no chaining, redirection, quoting or globs)"
            ).format(token)
    known = list(GUEST_READINGS_LINUX) + list(GUEST_READINGS_WINDOWS)
    matched = None
    for entry in known:
        if cleaned == entry or cleaned == entry + " " + (guest_path or ""):
            matched = entry
            break
    if matched is None:
        return None, None, (
            "guest reading {0!r} is not on the whitelist; permitted: {1}"
        ).format(cleaned, ", ".join(known))
    for word in matched.lower().split(" "):
        bare = word.lstrip("-+")
        if bare in GUEST_BLOCKED_WORDS:
            return None, None, "guest reading rejected: verb {0!r} is destructive".format(word)
    script_type = (
        CLOUD_ASSISTANT_KIND_WINDOWS
        if matched in GUEST_READINGS_WINDOWS
        else CLOUD_ASSISTANT_KIND_LINUX
    )
    command_text = matched
    if matched in GUEST_PATH_COMMANDS:
        if not guest_path:
            return None, None, (
                "the reading {0!r} needs an explicit --guest-path (absolute "
                "Linux path or Windows drive path)".format(matched)
            )
        path = guest_path.strip()
        pattern = WINDOWS_PATH_RE if script_type == CLOUD_ASSISTANT_KIND_WINDOWS else LINUX_PATH_RE
        if not re.match(pattern, path):
            return None, None, "guest path {0!r} rejected: not a simple, safe path".format(path)
        command_text = matched + " " + path
    elif guest_path:
        return None, None, "this whitelist entry takes no path argument"
    return command_text, script_type, None


# --------------------------------------------------------------------------- #
# Argument handling
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="snapshot_billing_report.py",
        description=(
            "ECS snapshot billing attribution and cleanup preparation. Gathers "
            "account evidence, explains capacity lenses, finds deletion "
            "blockers, and prints manual guidance; destructive steps stay with "
            "a human and gated writes need explicit user confirmation."
        ),
    )
    parser.add_argument(
        "--region-id", dest="region_ids", action="append", default=None,
        help="Alibaba Cloud region id, e.g. cn-hangzhou. Repeat for a "
             "multi-region sweep; never guessed, required outside --check-auth-only.",
    )
    parser.add_argument("--instance-id", dest="instance_id", default=None,
                        help="Optional ECS instance id to narrow evidence.")
    parser.add_argument("--disk-id", dest="disk_id", default=None,
                        help="Optional cloud disk id to narrow evidence.")
    parser.add_argument("--snapshot-id", dest="snapshot_id", default=None,
                        help="Optional snapshot id to analyze one entry.")
    parser.add_argument("--scope", dest="scope",
                        choices=("auto", "region", "instance", "disk"),
                        default="auto",
                        help="Evidence scope. auto derives from --instance-id / --disk-id.")
    parser.add_argument("--billing-cycle", dest="billing_cycle", default=None,
                        help="Optional billing month (YYYY-MM) used only as a "
                             "human cross-check label; no billing API is called.")
    parser.add_argument("--symptom", dest="symptom",
                        choices=("billing", "delete", "size-gap", "quota",
                                 "concepts", "unknown"),
                        default="unknown",
                        help="Customer-visible symptom routing hint.")
    parser.add_argument("--mode", dest="mode",
                        choices=("report", "guest-probe", "prepare-snapshot"),
                        default="report",
                        help="report: evidence sweep only. guest-probe / "
                             "prepare-snapshot: confirmation-gated dispatch.")
    parser.add_argument("--guest-command", dest="guest_command", default=None,
                        help="One whitelisted guest reading, e.g. 'df -h'.")
    parser.add_argument("--guest-path", dest="guest_path", default=None,
                        help="Path argument for a path-taking guest reading.")
    parser.add_argument("--user-confirmed", dest="user_confirmed",
                        action="store_true",
                        help="Set ONLY after the customer approved the notice: "
                             "authorizes exactly this one gated action.")
    parser.add_argument("--confirmation-scope", dest="confirmation_scope",
                        default=None,
                        help="Text naming the exact region and target the "
                             "customer approved; must cover this run's scope.")
    parser.add_argument("--snapshot-name", dest="snapshot_name", default=None,
                        help="Optional name for the gated pre-cleanup backup.")
    parser.add_argument("--write-list-file", dest="write_list_file", default=None,
                        help="New /tmp JSON file for the delete/keep candidate "
                             "lists (requires --user-confirmed; never overwrites).")
    parser.add_argument("--max-pages", dest="max_pages", type=int, default=MAX_PAGES,
                        help="Ceiling on paging requests per list action (default 10).")
    parser.add_argument("--timeout", dest="timeout", type=int,
                        default=CLI_TIMEOUT_SECONDS,
                        help="Per-call CLI timeout in seconds (default 30).")
    parser.add_argument("--poll-deadline-seconds", dest="poll_deadline", type=int,
                        default=POLL_DEADLINE_SECONDS,
                        help="Bound on waiting for one guest reading result.")
    parser.add_argument("--output", dest="output", choices=("text", "json"),
                        default="text", help="Report rendering (default text).")
    parser.add_argument("--check-auth-only", dest="check_auth_only",
                        action="store_true", help="Only verify caller identity and exit.")
    parser.add_argument("--verbose", dest="verbose", action="store_true",
                        help="Show extra detail.")
    return parser


def resolve_regions(raw: Optional[List[str]], warnings: List[str]) -> List[str]:
    regions: List[str] = []
    for item in raw or []:
        value = str(item).strip()
        if value and value not in regions:
            regions.append(value)
    if len(regions) > MAX_REGIONS_PER_RUN:
        warnings.append(
            "region sweep capped at {0} regions for this run".format(MAX_REGIONS_PER_RUN)
        )
        regions = regions[:MAX_REGIONS_PER_RUN]
    return regions


def validate(args: argparse.Namespace) -> List[str]:
    problems: List[str] = []
    if args.check_auth_only:
        return problems
    if not args.region_ids:
        problems.append(
            "--region-id is required; snapshots and disks are regional, billing "
            "is per region, and the region is never guessed."
        )
    if args.max_pages < 1:
        problems.append("--max-pages must be >= 1.")
    if args.timeout < 1:
        problems.append("--timeout must be >= 1 second.")
    if args.poll_deadline < 1:
        problems.append("--poll-deadline-seconds must be >= 1.")
    if args.mode == "guest-probe":
        if not args.instance_id:
            problems.append("guest-probe mode needs --instance-id of the target instance.")
        if not args.guest_command:
            problems.append("guest-probe mode needs --guest-command (one whitelist entry).")
    if args.mode == "prepare-snapshot":
        if not args.disk_id:
            problems.append("prepare-snapshot mode needs --disk-id of the disk to back up.")
        if args.snapshot_name and not re.match(SNAPSHOT_NAME_RE, args.snapshot_name):
            problems.append(
                "--snapshot-name must start with a letter and use only letters, "
                "digits, ':', '_', '.' or '-' (max 128)."
            )
    return problems


# --------------------------------------------------------------------------- #
# Evidence collection (report mode)
# --------------------------------------------------------------------------- #
def collect_region(
    region: str,
    args: argparse.Namespace,
    session_id: str,
    warnings: List[str],
    errors: List[Dict[str, str]],
    timeout: int,
    max_pages: int,
) -> Dict[str, Any]:
    """Collect snapshots, disks, instances and self-owned images for one region."""
    evidence: Dict[str, Any] = {
        "region": region, "snapshots": [], "disks": [], "instances": [],
        "images": [], "paging_truncated": False, "failed": False,
    }
    snap_params: Dict[str, Any] = {"RegionId": region}
    if args.snapshot_id:
        snap_params["SnapshotIds"] = json.dumps([args.snapshot_id])
    if args.disk_id:
        snap_params["DiskId"] = args.disk_id
    if args.instance_id and (args.scope == "instance" or args.scope == "auto"):
        snap_params["InstanceId"] = args.instance_id
    try:
        snapshots, snap_walk = paginate(
            PRODUCT_ECS, ACTION_DESCRIBE_SNAPSHOTS, snap_params, "Snapshot",
            session_id=session_id, page_size=PAGE_SIZE, max_pages=max_pages,
            warnings=warnings, nested_keys=("Snapshots",), timeout=timeout,
        )
        evidence["snapshots"] = snapshots
        evidence["paging_truncated"] = snap_walk == "truncated"
    except CliError as exc:
        errors.append({"region": region, "stage": "snapshots",
                       "code": exc.code, "message": exc.message})
        evidence["failed"] = True
        return evidence

    try:
        disks, _ = paginate(
            PRODUCT_ECS, ACTION_DESCRIBE_DISKS, {"RegionId": region}, "Disk",
            session_id=session_id, page_size=PAGE_SIZE, max_pages=max_pages,
            warnings=warnings, nested_keys=("Disks",), timeout=timeout,
        )
        evidence["disks"] = disks
    except CliError as exc:
        evidence["disks_unavailable"] = True
        warnings.append("disk listing unavailable in {0}: {1}".format(region, exc.message))

    try:
        instances, _ = paginate(
            PRODUCT_ECS, ACTION_DESCRIBE_INSTANCES, {"RegionId": region}, "Instance",
            session_id=session_id, page_size=PAGE_SIZE, max_pages=max_pages,
            warnings=warnings, nested_keys=("Instances",), timeout=timeout,
        )
        evidence["instances"] = instances
    except CliError as exc:
        warnings.append("instance listing unavailable in {0}: {1}".format(region, exc.message))

    try:
        images, _ = paginate(
            PRODUCT_ECS, ACTION_DESCRIBE_IMAGES,
            {"RegionId": region, "ImageOwnerAlias": "self"}, "Image",
            session_id=session_id, page_size=PAGE_SIZE, max_pages=max_pages,
            warnings=warnings, nested_keys=("Images",), timeout=timeout,
        )
        evidence["images"] = images
    except CliError as exc:
        warnings.append("custom image listing unavailable in {0}: {1}".format(region, exc.message))

    evidence["usage_probe_images"] = probe_image_references(
        region, evidence["snapshots"], evidence["images"], session_id, warnings, timeout
    )
    return evidence


def _image_snapshot_refs(image: Dict[str, Any]) -> List[str]:
    refs: List[str] = []
    mappings = (image or {}).get("DiskDeviceMappings") or {}
    items = mappings.get("DiskDeviceMapping") if isinstance(mappings, dict) else None
    if isinstance(items, dict):
        items = [items]
    for item in items or []:
        if isinstance(item, dict) and item.get("SourceSnapshotId"):
            refs.append(str(item.get("SourceSnapshotId")))
    return refs


def probe_image_references(
    region: str,
    snapshots: List[Dict[str, Any]],
    images: List[Dict[str, Any]],
    session_id: str,
    warnings: List[str],
    timeout: int,
) -> Dict[str, List[str]]:
    """Map snapshot id -> referencing custom image ids for this region."""
    mapping: Dict[str, List[str]] = {}
    for image in images:
        image_id = str(image.get("ImageId") or "")
        if not image_id:
            continue
        for snap_id in _image_snapshot_refs(image):
            mapping.setdefault(snap_id, [])
            if image_id not in mapping[snap_id]:
                mapping[snap_id].append(image_id)

    pending = [
        snap for snap in snapshots
        if str(snap.get("Usage") or "").lower() in ("image", "image_disk")
        and str(snap.get("SnapshotId") or "") not in mapping
    ]
    if len(pending) > MAX_USAGE_PROBES:
        warnings.append(
            "image-reference probe capped at {0} snapshots in {1}; remaining "
            "entries rely on the Usage field only".format(MAX_USAGE_PROBES, region)
        )
    for snap in pending[:MAX_USAGE_PROBES]:
        snap_id = str(snap.get("SnapshotId") or "")
        if not snap_id:
            continue
        try:
            payload = run_cli(
                PRODUCT_ECS, ACTION_DESCRIBE_IMAGES,
                {"RegionId": region, "SnapshotId": snap_id,
                 "PageSize": IMAGE_PROBE_PAGE_SIZE, "PageNumber": 1},
                session_id=session_id, timeout=timeout, warnings=warnings,
            )
        except CliError as exc:
            warnings.append(
                "image-reference probe failed for {0} in {1}: {2}".format(
                    snap_id, region, exc.message
                )
            )
            mapping[snap_id] = ["unconfirmed: use the Related Images column in the console"]
            continue
        found = []
        for image in _unwrap_list(payload, "Images", "Image"):
            image_id = str(image.get("ImageId") or "")
            if image_id:
                found.append(image_id)
        mapping[snap_id] = found if found else ["unconfirmed: use the Related Images column in the console"]
    return mapping
# --------------------------------------------------------------------------- #
# Findings: the decision tree applied to collected evidence
# --------------------------------------------------------------------------- #
def analyze(evidence: List[Dict[str, Any]], symptom: str) -> Dict[str, Any]:
    """Build the per-region summary, chain view, blockers and regrowth flags."""
    findings: Dict[str, Any] = {
        "per_region": [], "chains": [], "blockers": [], "orphaned": [],
        "auto_regions": [], "permanent_candidates": 0, "total_snapshots": 0,
        "total_size_at_creation": 0, "all_failed": bool(evidence),
        "truncated": False,
    }
    chains: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for region_evidence in evidence:
        region = str(region_evidence.get("region") or NOT_RETURNED)
        if not region_evidence.get("failed"):
            findings["all_failed"] = False
            findings["truncated"] = findings["truncated"] or bool(
                region_evidence.get("paging_truncated")
            )
        if region_evidence.get("failed"):
            findings["per_region"].append({
                "region": region, "status": "evidence unavailable",
            })
            continue
        snapshots = region_evidence["snapshots"]
        disks = region_evidence["disks"]
        instances = region_evidence["instances"]
        images = region_evidence["images"]
        disk_ids = {str(disk.get("DiskId") or "") for disk in disks}
        disks_known = not region_evidence.get("disks_unavailable")
        usage_probe = region_evidence.get("usage_probe_images") or {}
        auto_count = 0
        size_sum = 0
        for snap in snapshots:
            findings["total_snapshots"] += 1
            snap_id = str(snap.get("SnapshotId") or NOT_RETURNED)
            snap_name = str(snap.get("SnapshotName") or "")
            disk_id = str(snap.get("SourceDiskId") or NOT_RETURNED)
            key = (region, disk_id)
            chain = chains.setdefault(key, {
                "region": region, "disk": disk_id, "entries": 0, "auto": 0,
                "oldest": "", "newest": "", "size_at_creation": 0,
            })
            chain["entries"] += 1
            created = str(snap.get("CreationTime") or "")
            if created:
                chain["oldest"] = min(chain["oldest"], created) if chain["oldest"] else created
                chain["newest"] = max(chain["newest"], created) if chain["newest"] else created
            snap_size = to_int(snap.get("SourceDiskSize"))
            if snap_size:
                size_sum += snap_size
                chain["size_at_creation"] += snap_size
            if str(snap.get("SnapshotType") or "").lower() == "auto":
                auto_count += 1
                chain["auto"] += 1
                retention = to_int(snap.get("RetentionDays"))
                if snap.get("RetentionDays") in (None, "") or retention is None:
                    findings["permanent_candidates"] += 1
            usage = str(snap.get("Usage") or "none").lower()
            if usage in USAGE_BLOCKING_STATES:
                findings["blockers"].append({
                    "region": region, "snapshot": snap_id, "name": snap_name,
                    "usage": usage,
                    "images": ", ".join(usage_probe.get(snap_id) or []) or NOT_RETURNED,
                })
            if (
                disks_known and disk_id != NOT_RETURNED
                and disk_ids and disk_id not in disk_ids
            ):
                findings["orphaned"].append({
                    "region": region, "snapshot": snap_id, "missing_disk": disk_id,
                })
        if auto_count:
            findings["auto_regions"].append({"region": region, "auto_snapshots": auto_count})
        findings["total_size_at_creation"] += size_sum
        findings["per_region"].append({
            "region": region, "status": "collected",
            "snapshots": len(snapshots), "auto_snapshots": auto_count,
            "size_at_creation_gib": size_sum,
            "disks": len(disks), "instances": len(instances),
            "custom_images": len(images),
        })
    findings["chains"] = sorted(
        chains.values(), key=lambda row: (-row["entries"], row["region"], row["disk"])
    )
    findings["no_snapshots_anywhere"] = (
        findings["total_snapshots"] == 0 and not findings["all_failed"]
    )
    findings["top_chains_by_count"] = findings["chains"][:5]
    findings["symptom"] = symptom
    return findings


def decide_next_action(args: argparse.Namespace, findings: Dict[str, Any]) -> str:
    if findings.get("all_failed"):
        return (
            "fix the reported access or parameter problem (see the [WARN] lines "
            "and references/ram-policies.md), then re-run the same command"
        )
    if findings.get("no_snapshots_anywhere"):
        return (
            "hand the operator the no-snapshot proof section: confirm the "
            "billing account, then enumerate the remaining regions or the ECS "
            "overview page which lists every region holding snapshots"
        )
    if findings.get("blockers"):
        return (
            "walk the manual unblocking order in "
            "references/snapshot-billing-cleanup__snapshot-dependency-and-deletion.md with the operator; "
            "this skill never performs the removal itself"
        )
    if findings.get("auto_regions"):
        return (
            "before deleting, verify the automatic snapshot policy behind the "
            "auto-type entries in the console (manual step), or the capacity "
            "will regrow; then hand over the delete/keep list"
        )
    if args.symptom in ("size-gap", "unknown"):
        return (
            "compare the three capacity lenses; to add the guest column, run "
            "guest-probe mode after explicit user confirmation, or ask the "
            "operator to paste df -h output (documented degraded path)"
        )
    return "relay the report sections and their document anchors to the customer"


# --------------------------------------------------------------------------- #
# Confirmation-gated dispatches
# --------------------------------------------------------------------------- #
def _decode_output(raw: str) -> str:
    if not raw:
        return ""
    try:
        return base64.b64decode(raw, validate=True).decode("utf-8", "replace")
    except Exception:
        return raw


def guest_notice(region: str, instance_id: str, command_text: str) -> str:
    return (
        "Action: execute ONE information-only guest reading on the customer "
        "instance through Cloud Assistant.\n"
        "Command: {0}\n"
        "Scope: instance {1} in region {2}.\n"
        "Effect: reports file-system or volume data; does not modify, move or "
        "delete anything inside the guest; nothing is changed, so the reading "
        "is safe by construction.\n"
        "The command was validated against the low-risk whitelist; chained or "
        "destructive input is rejected before dispatch.".format(
            command_text, instance_id, region
        )
    )


def snapshot_notice(region: str, disk_id: str, name: str) -> str:
    return (
        "Action: create ONE snapshot backup of a single cloud disk (the "
        "pre-cleanup safety net of the snapshot-first rule).\n"
        "Disk: {0} in region {1}.\n"
        "Name: {2}\n"
        "Effect: adds a new snapshot entry; the new entry itself bills per "
        "capacity afterwards, so remove it via the console once the manual "
        "cleanup is verified (manual step). Existing data is untouched; the "
        "backup is reversible by deleting the new snapshot itself.".format(
            disk_id, region, name or NOT_RETURNED)
    )


def run_guest_probe(args: argparse.Namespace, session_id: str, warnings: List[str]) -> int:
    region = args.region_ids[0]
    command_text, script_type, refusal = validate_guest_request(
        args.guest_command, args.guest_path
    )
    print("\n== Gated guest reading (mode: guest-probe) ==")
    if refusal:
        print("[WARN] whitelist refusal: {0}".format(refusal))
        print("STATUS: {0}".format(STATUS_FAIL))
        print("NEXT_ACTION: pick exactly one whitelisted entry listed in "
              "references/snapshot-billing-cleanup__guest-diagnostics.md and re-run")
        return EXIT_BY_STATUS[STATUS_FAIL]
    if not (args.user_confirmed and _scope_confirms(
        args.confirmation_scope,
        [region, args.instance_id, command_text.split(" ")[0]],
    )):
        print(_notice(guest_notice(region, args.instance_id, command_text)))
        print("STATUS: {0}".format(STATUS_DEGRADED))
        print("NEXT_ACTION: present the notice above to the customer; if they "
              "approve, re-run the identical command with --user-confirmed and "
              "a --confirmation-scope naming region, instance and command")
        return EXIT_BY_STATUS[STATUS_DEGRADED]
    print("Executing the confirmed gated reading once (dispatch, then fetch result).")
    try:
        payload = run_cli(
            PRODUCT_ECS, ACTION_RUN_COMMAND,
            {
                "RegionId": region,
                "Type": script_type,
                "CommandContent": command_text,
                "Name": "snapshot-billing-diag-{0}".format(session_id[:8]),
                "Description": "information-only reading via " + SKILL_NAME,
                "Timeout": "60",
                "InstanceId.1": args.instance_id,
            },
            session_id=session_id, timeout=args.timeout, warnings=warnings,
        )
    except CliError as exc:
        print("[WARN] dispatch failed: {0}".format(exc.message))
        _print_guest_fallback()
        print("STATUS: {0}".format(STATUS_DEGRADED))
        print("NEXT_ACTION: ask the operator to run the reading inside the "
              "instance manually and paste its output (documented degraded path)")
        return EXIT_BY_STATUS[STATUS_DEGRADED]
    invoke_id = str(payload.get("InvokeId") or "")
    if not invoke_id:
        print("[WARN] dispatch returned no invocation id; the reading may still "
              "be running; fetch results later or use the manual fallback")
        _print_guest_fallback()
        print("STATUS: {0}".format(STATUS_DEGRADED))
        print("NEXT_ACTION: re-check the invocation or take the operator-paste "
              "fallback; do not claim a reading that was not returned")
        return EXIT_BY_STATUS[STATUS_DEGRADED]
    result = _wait_for_invocation(region, invoke_id, args, session_id, warnings)
    print("Invocation: {0}  status: {1}".format(invoke_id, result.get("status", NOT_RETURNED)))
    output = mask_credentials(str(result.get("output") or ""))
    if len(output) > 4000:
        output = output[:4000] + "\n... truncated ..."
    print("Guest reading output ({0}):".format(command_text))
    print(output if output.strip() else "(no output returned yet)")
    print("\nReminder: guest output shows the file-system lens only; it is "
          "never the billed chain capacity nor the provisioned disk size "
          "(references/snapshot-billing-cleanup__snapshot-billing-decision-tree.md).")
    final_status = STATUS_OK if output.strip() else STATUS_DEGRADED
    print("STATUS: {0}".format(final_status))
    print("NEXT_ACTION: put this reading into the three-lens comparison table "
          "of the report mode")
    return EXIT_BY_STATUS[final_status]


def _print_guest_fallback() -> None:
    print("Manual fallback: ask the customer to run and paste, inside the "
          "instance: df -h (Linux) or Get-Volume (Windows), plus "
          "du -x --max-depth=1 / for the top-level breakdown.")


def _wait_for_invocation(
    region: str, invoke_id: str, args: argparse.Namespace,
    session_id: str, warnings: List[str]
) -> Dict[str, Any]:
    waited = 0
    while waited < args.poll_deadline:
        try:
            payload = run_cli(
                PRODUCT_ECS, ACTION_DESCRIBE_INVOCATIONS,
                {"RegionId": region, "InvokeId": invoke_id,
                 "ContentEncoding": "PlainText", "IncludeOutput": "true"},
                session_id=session_id, timeout=args.timeout, warnings=warnings,
            )
        except CliError as exc:
            warnings.append("invocation fetch failed: {0}".format(exc.message))
            return {"status": NOT_RETURNED, "output": ""}
        for invocation in _unwrap_list(payload, "Invocations", "Invocation"):
            status = str(invocation.get("InvokeStatus") or "")
            for inst in _unwrap_list(invocation, "InvokeInstances", "InvokeInstance"):
                inst_status = str(inst.get("InvocationStatus") or "")
                if inst_status in INVOCATION_TERMINAL or status in INVOCATION_TERMINAL:
                    return {
                        "status": inst_status or status or NOT_RETURNED,
                        "output": _decode_output(str(inst.get("Output") or "")),
                    }
        time.sleep(POLL_INTERVAL_SECONDS)  # noqa: timeout
        waited += POLL_INTERVAL_SECONDS
    return {"status": "still running at deadline", "output": ""}


def run_prepare_snapshot(args: argparse.Namespace, session_id: str,
                         warnings: List[str]) -> int:
    region = args.region_ids[0]
    print("\n== Gated pre-cleanup backup (mode: prepare-snapshot) ==")
    if not (args.user_confirmed and _scope_confirms(
        args.confirmation_scope, [region, args.disk_id]
    )):
        print(_notice(snapshot_notice(region, args.disk_id, args.snapshot_name or "")))
        print("STATUS: {0}".format(STATUS_DEGRADED))
        print("NEXT_ACTION: present the notice above to the customer; if they "
              "approve, re-run the identical command with --user-confirmed and "
              "a --confirmation-scope naming region and disk")
        return EXIT_BY_STATUS[STATUS_DEGRADED]
    params: Dict[str, Any] = {
        "RegionId": region,
        "DiskId": args.disk_id,
        "Description": "pre-cleanup backup via {0}".format(SKILL_NAME),
    }
    if args.snapshot_name:
        params["SnapshotName"] = args.snapshot_name
    try:
        payload = run_cli(
            PRODUCT_ECS, ACTION_CREATE_SNAPSHOT, params,
            session_id=session_id, timeout=args.timeout, warnings=warnings,
        )
    except CliError as exc:
        print("[WARN] backup dispatch failed: {0}".format(exc.message))
        if ERROR_STRING_INSTANCE_STATE.lower() in exc.message.lower():
            print("The write was refused because the attached instance is in a "
                  "transitional state ({0}). Stopping here per the error "
                  "discipline: no retry, no path change.".format(
                      ERROR_STRING_INSTANCE_STATE))
            print("NEXT_ACTION: hand off to the instance-state diagnosis path "
                  "(references/snapshot-billing-cleanup__handoffs.md); the snapshot side waits until the "
                  "instance settles")
            return EXIT_BY_STATUS[STATUS_FAIL]
        print("STATUS: {0}".format(STATUS_FAIL))
        print("NEXT_ACTION: resolve the reported error (permissions per "
              "references/ram-policies.md, parameters per the usage of this "
              "script) and re-run; do not proceed to any cleanup without the backup")
        return EXIT_BY_STATUS[STATUS_FAIL]
    new_snapshot = str(payload.get("SnapshotId") or NOT_RETURNED)
    print("Backup snapshot created: {0} on disk {1} ({2}).".format(
        new_snapshot, args.disk_id, region))
    print(SNAPSHOT_FIRST_RULE)
    print("The follow-up in-guest cleanup itself stays a human, operator-"
          "approved action (area:disk-expand-diagnosis guidance).")
    final_status = STATUS_OK if new_snapshot != NOT_RETURNED else STATUS_DEGRADED
    print("STATUS: {0}".format(final_status))
    print("NEXT_ACTION: hand the operator the cleanup steps; verify the "
          "snapshot reaches the accomplished state before any file removal")
    return EXIT_BY_STATUS[final_status]


# --------------------------------------------------------------------------- #
# Candidate list artifact (optional, gated, never overwrites)
# --------------------------------------------------------------------------- #
def write_candidate_file(
    args: argparse.Namespace, findings: Dict[str, Any], session_id: str,
    warnings: List[str]
) -> None:
    path = args.write_list_file
    if not path:
        return
    print("\n== Candidate list file ==")
    if not re.match(CANDIDATE_FILE_RE, path):
        warnings.append("candidate file rejected: must be a new JSON file named "
                        "{0}<name>.json".format(CANDIDATE_FILE_PREFIX))
        print("[WARN] candidate file rejected: bad path (see references/"
              "snapshot-dependency-and-deletion.md templates)")
        return
    if not args.user_confirmed:
        print(_notice(
            "Action: write ONE new JSON file with the delete/keep candidate "
            "lists to {0}.\nEffect: creates a new file under /tmp; no existing "
            "file is touched; no cloud resource changes.".format(path)))
        warnings.append("candidate file skipped: confirmation gate not satisfied")
        return
    if os.path.exists(path):
        warnings.append("candidate file skipped: refusing to overwrite an existing file")
        print("[WARN] refusing to overwrite {0}".format(path))
        return
    payload_obj = {
        "skill": SKILL_NAME, "session_id": session_id,
        "billing_item_label": BILLING_ITEM_LABEL,
        "chain_candidates": list(findings["chains"]),
        "blocked_by_images": findings["blockers"],
        "warning": "Listing as a candidate is NOT permission to delete: verify "
                   "each row, honor the manual unblocking order, and remove "
                   "entries in the console region by region.",
    }
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload_obj, handle, indent=2, ensure_ascii=True)
        os.chmod(path, 0o600)
        print("Candidate list written: {0}".format(path))
    except OSError as exc:
        warnings.append("candidate file write failed: {0}".format(mask_credentials(exc)))
        print("[WARN] candidate file write failed; the lists remain in the report body")


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _rows_to_text(
    title: str, headers: Sequence[str], rows: Sequence[Sequence[Any]]
) -> List[str]:
    lines = ["", "== {0} ==".format(title)]
    if not rows:
        lines.append("  (no records)")
        return lines
    lines.append("  " + " | ".join(headers))
    for row in rows:
        lines.append("  " + " | ".join(str(cell) for cell in row))
    return lines


def render_text(ctx: Dict[str, Any]) -> str:
    findings = ctx["findings"]
    lines: List[str] = [BANNER]
    lines.append("Account label: {0}".format(ctx["account_label"]))
    lines.append("Billing item label on invoices: {0}".format(BILLING_ITEM_LABEL))
    if ctx.get("billing_cycle"):
        lines.append("Billing cycle noted for human cross-check: {0} (no "
                     "billing API is called by this skill)".format(
                         ctx["billing_cycle"]))
    lines.append("")
    lines.append("== Collected parameters ==")
    for key, value in sorted(ctx["collected"].items()):
        lines.append("  {0}: {1}".format(key, value))
    lines.append("")
    lines.append("== Capacity lenses (never mix these three) ==")
    for lens_key, lens_text in CAPACITY_LENSES:
        lines.append("  [{0}] {1}".format(lens_key, lens_text))
    region_rows = [
        (row.get("region"), row.get("status"),
         row.get("snapshots", NOT_RETURNED), row.get("auto_snapshots", NOT_RETURNED),
         row.get("size_at_creation_gib", NOT_RETURNED),
         row.get("custom_images", NOT_RETURNED))
        for row in findings["per_region"]
    ]
    lines.extend(_rows_to_text(
        "Per-region evidence (the size column sums recorded source-disk sizes "
        "at creation: a proxy, NOT the billed chain capacity)",
        ("region", "status", "entries", "auto", "disk-size-sum-GiB", "images"),
        region_rows,
    ))
    chain_rows = [
        (row["region"], row["disk"], row["entries"], row["auto"],
         row["oldest"] or NOT_RETURNED, row["newest"] or NOT_RETURNED)
        for row in findings["chains"]
    ]
    lines.extend(_rows_to_text(
        "Per-disk snapshot chains (the console chain view is the billed authority)",
        ("region", "disk", "entries", "auto", "oldest", "newest"), chain_rows,
    ))
    blocker_rows = [
        (row["region"], row["snapshot"], row["usage"], row["images"])
        for row in findings["blockers"]
    ]
    lines.extend(_rows_to_text(
        "Deletion blockers (referenced snapshots; follow the manual unblocking order)",
        ("region", "snapshot", "usage", "referencing-images"), blocker_rows,
    ))
    if blocker_rows:
        lines.append("  Manual unblocking order (human steps, never executed here):")
        lines.extend("    {0}".format(step) for step in BLOCKER_ORDER)
    orphan_rows = [
        (row["region"], row["snapshot"], row["missing_disk"])
        for row in findings["orphaned"]
    ]
    lines.extend(_rows_to_text(
        "Snapshots whose source disk is no longer listed in the region (the "
        "disk may be released; per the billing facts the snapshots keep "
        "charging until a human removes them)",
        ("region", "snapshot", "source-disk-not-listed"), orphan_rows,
    ))
    lines.append("")
    lines.append("== Regrowth and quota assessment ==")
    if findings["auto_regions"]:
        for row in findings["auto_regions"]:
            lines.append(
                "  region {0}: {1} auto-type snapshot entries -> an automatic "
                "policy or an external job is the generating source; verify "
                "the policy (existence, disk attachment, retention) in the "
                "console BEFORE deleting, otherwise capacity regrows".format(
                    row["region"], row["auto_snapshots"]))
    else:
        lines.append(
            "  no auto-type entries found in the collected regions; a "
            "'deleted but charging again' case now points to another region, "
            "an external job or settlement lag ({0})".format(
                ", ".join(REGROWTH_SOURCES)))
    if findings["permanent_candidates"]:
        lines.append("  {0} auto-type entries did not return a retention value: "
                     "treat them as permanent-retention until the policy page "
                     "proves otherwise".format(findings["permanent_candidates"]))
    if findings["top_chains_by_count"]:
        top = findings["top_chains_by_count"][0]
        lines.append("  largest chain: {0} entries on {1}/{2}".format(
            top["entries"], top["region"], top["disk"]))
    if findings["no_snapshots_anywhere"]:
        lines.append("")
        lines.append("== No-snapshot proof ==")
        lines.append(
            "  Under the CURRENT credential (see the account label above) the "
            "enumerated regions contain zero snapshot entries. A bill line "
            "naming {0} then means: another region still holds snapshots "
            "(enumerate the remaining regions, or check the ECS overview page "
            "that lists every region holding snapshot capacity), or the "
            "invoice belongs to a different account. Do not conclude "
            "'nothing to pay' from this run alone.".format(BILLING_ITEM_LABEL))
    lines.append("")
    lines.append("== Fact anchors ==")
    for fact in SNAPSHOT_STORAGE_FACTS.values():
        lines.append("  - {0}".format(fact))
    if ctx["args_symptom"] in ("billing", "quota", "concepts", "unknown"):
        lines.append("")
        lines.append("== Deduction facts "
                     "(references/snapshot-billing-cleanup__resource-package-deduction.md) ==")
        for fact in DEDUCTION_FACTS:
            lines.append("  - {0}".format(fact))
    lines.append("")
    lines.append("== Quota notes ==")
    for note in QUOTA_NOTES:
        lines.append("  - {0}".format(note))
    if findings["blockers"] or ctx["args_symptom"] == "concepts":
        lines.append("")
        lines.append("A custom image is built ON TOP of snapshots: creating "
                     "one adds snapshot entries automatically, and removing "
                     "the image without its linked snapshots leaves the "
                     "capacity billing behind.")
    lines.append("")
    lines.append("== Out-of-scope routing (references/snapshot-billing-cleanup__handoffs.md) ==")
    for trigger, target in HANDOFFS:
        lines.append("  - {0} -> {1}".format(trigger, target))
    lines.append("")
    lines.append(
        "Report rules honored: only values the API returned are quoted; "
        "missing fields render as '{0}'; every auto-filled parameter is "
        "declared above; removal steps stay manual with the operator; and no "
        "price estimate or quotation is offered (the official billing document "
        "and the price calculator entry are the only price sources).".format(
            NOT_RETURNED))
    return "\n".join(lines)


def render_json(ctx: Dict[str, Any]) -> str:
    payload = {
        "skill": SKILL_NAME,
        "session_id": ctx["session_id"],
        "account_label": ctx["account_label"],
        "billing_item_label": BILLING_ITEM_LABEL,
        "collected_parameters": ctx["collected"],
        "findings": ctx["findings"],
        "warnings": ctx["warnings"],
        "errors": ctx["errors"],
        "status": ctx["status"],
        "next_action": ctx["next_action"],
    }
    return json.dumps(payload, indent=2, ensure_ascii=True, default=str)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def _run_selftest() -> int:
    """Offline regression locks for the pure decision cores that produce the
    customer-facing cleanup plan: field/to-int parsing, the defensive list unwrap,
    region de-dup and capping, the per-region aggregation in analyze() (totals,
    per-disk chains, usage blockers, orphans, permanent-auto flags) and the
    priority order of decide_next_action()/validate()/validate_guest_request().
    Every expected value was read off the live functions first. No cloud call.
    Returns 0 when all hold."""
    rc = 0

    def expect(name, cond):
        nonlocal rc
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            rc = 1

    # parsing helpers: verbatim-or-marker (a numeric 0 is NOT treated as missing),
    # int coercion (junk / None / float-string all become None), list unwrap.
    expect("field: verbatim, missing marker, and 0 preserved",
           field({"a": "x"}, "a") == "x" and field({}, "a") == NOT_RETURNED
           and field({"a": 0}, "a") == "0")
    expect("to_int: parses ints+whitespace, junk/None/float -> None",
           to_int("5") == 5 and to_int(" 7 ") == 7 and to_int("x") is None
           and to_int(None) is None and to_int("12.5") is None)
    expect("unwrap_list: filters dict list, absent container -> []",
           _unwrap_list({"S": {"I": [{"i": 1}, "junk", {"i": 2}]}}, "S", "I") == [{"i": 1}, {"i": 2}]
           and _unwrap_list({}, "S", "I") == [])
    expect("scope_confirms: every required token present (case-insensitive) or False",
           _scope_confirms("cn-hangzhou disk-1 DELETE approved", ["cn-hangzhou", "delete"]) is True
           and _scope_confirms("partial", ["a", "b"]) is False)

    # resolve_regions: strip + de-dup + drop empty, cap at MAX_REGIONS_PER_RUN.
    w: List[str] = []
    expect("resolve_regions: dedup, strip, skip empty",
           resolve_regions(["cn-h", " cn-h ", "cn-bj", ""], w) == ["cn-h", "cn-bj"] and w == [])
    w2: List[str] = []
    capped = resolve_regions(["r%d" % i for i in range(MAX_REGIONS_PER_RUN + 3)], w2)
    expect("resolve_regions: caps at MAX_REGIONS_PER_RUN with a warning",
           len(capped) == MAX_REGIONS_PER_RUN and bool(w2))

    # analyze: one region with an auto snapshot that never expires, a snapshot
    # blocked by image usage, and a snapshot whose source disk is gone.
    evidence = [{"region": "cn-hangzhou", "failed": False, "paging_truncated": False,
                 "snapshots": [
                     {"SnapshotId": "s-1", "SourceDiskId": "d-1", "SourceDiskSize": 40,
                      "SnapshotType": "auto", "RetentionDays": "",
                      "CreationTime": "2026-01-01T00:00:00Z", "Usage": "none"},
                     {"SnapshotId": "s-2", "SourceDiskId": "d-1", "SourceDiskSize": 60,
                      "SnapshotType": "user", "CreationTime": "2026-02-01T00:00:00Z", "Usage": "image"},
                     {"SnapshotId": "s-3", "SourceDiskId": "d-gone", "SourceDiskSize": 10,
                      "SnapshotType": "user", "CreationTime": "2026-03-01T00:00:00Z", "Usage": "none"},
                 ],
                 "disks": [{"DiskId": "d-1"}], "disks_unavailable": False,
                 "instances": [], "images": [], "usage_probe_images": {"s-2": ["m-abc"]}}]
    a = analyze(evidence, "size-gap")
    expect("analyze: totals count every snapshot and sum size at creation",
           a["total_snapshots"] == 3 and a["total_size_at_creation"] == 110)
    expect("analyze: auto snapshot without RetentionDays is a permanent candidate",
           a["permanent_candidates"] == 1
           and a["auto_regions"] == [{"region": "cn-hangzhou", "auto_snapshots": 1}])
    expect("analyze: image-usage snapshot becomes a blocker carrying its image",
           len(a["blockers"]) == 1 and a["blockers"][0]["snapshot"] == "s-2"
           and a["blockers"][0]["images"] == "m-abc")
    expect("analyze: snapshot whose source disk is gone is orphaned",
           [o["snapshot"] for o in a["orphaned"]] == ["s-3"])
    d1 = next(c for c in a["chains"] if c["disk"] == "d-1")
    expect("analyze: per-disk chain has 2 entries, oldest..newest and summed size",
           d1["entries"] == 2 and d1["auto"] == 1
           and d1["oldest"] == "2026-01-01T00:00:00Z" and d1["newest"] == "2026-02-01T00:00:00Z"
           and d1["size_at_creation"] == 100)
    expect("analyze: healthy collection -> not all_failed and not no_snapshots",
           a["all_failed"] is False and a["no_snapshots_anywhere"] is False)

    # decide_next_action: strict priority all_failed > no_snapshots > blockers >
    # auto-regrowth > size-gap lens > generic relay.
    def ns(symptom="x"):
        return argparse.Namespace(symptom=symptom)
    expect("decide: all_failed outranks everything (fix access first)",
           "fix the reported" in decide_next_action(ns(), {"all_failed": True, "blockers": [1]}))
    expect("decide: no_snapshots needs the proof section",
           "no-snapshot proof" in decide_next_action(ns(), {"all_failed": False, "no_snapshots_anywhere": True}))
    expect("decide: blockers precede the regrowth warning",
           "unblocking" in decide_next_action(ns(), {"all_failed": False, "no_snapshots_anywhere": False,
                                                     "blockers": [1], "auto_regions": [1]}))
    expect("decide: auto-regrowth precedes the size-gap lens",
           "regrow" in decide_next_action(ns("size-gap"), {"all_failed": False, "no_snapshots_anywhere": False,
                                                           "blockers": [], "auto_regions": [1]}))
    expect("decide: size-gap lens, then generic relay as the floor",
           "capacity" in decide_next_action(ns("size-gap"), {"all_failed": False, "no_snapshots_anywhere": False,
                                                             "blockers": [], "auto_regions": []})
           and "relay the report" in decide_next_action(ns("other"), {"all_failed": False,
                                                                      "no_snapshots_anywhere": False,
                                                                      "blockers": [], "auto_regions": []}))

    # validate: region always required, auth-only short-circuits, modes demand targets.
    def vns(**kw):
        base = dict(check_auth_only=False, region_ids=None, max_pages=10, timeout=30,
                    poll_deadline=60, mode="report", instance_id=None, guest_command=None,
                    disk_id=None, snapshot_name=None)
        base.update(kw)
        return argparse.Namespace(**base)
    expect("validate: missing region is an error; auth-only has none",
           any("region-id is required" in p for p in validate(vns()))
           and validate(vns(check_auth_only=True)) == [])
    expect("validate: guest-probe mode needs instance id and a command",
           len(validate(vns(region_ids=["cn-h"], mode="guest-probe"))) == 2)

    # validate_guest_request: one whitelisted reading accepted, chaining/unknown refused.
    ok_cmd, ok_type, ok_reason = validate_guest_request("df -h", None)
    expect("guest gate: whitelisted 'df -h' accepted as a shell reading",
           ok_cmd == "df -h" and ok_type is not None and ok_reason is None)
    expect("guest gate: chained command and unknown verb are refused",
           validate_guest_request("df -h && rm -rf /", None)[0] is None
           and validate_guest_request("reboot", None)[0] is None)
    return rc


def main(argv: Optional[Sequence[str]] = None) -> int:
    if "--selftest" in (argv if argv is not None else sys.argv):
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    session_id = new_session_id()
    warnings: List[str] = []
    errors: List[Dict[str, str]] = []

    # One name for one deliverable: the User-Agent already carries the package
    # name, and a banner naming the retired single skill split attribution.
    print(FINAL_ANSWER_BANNER.format(skill=_PACKAGE_NAME, session_id=session_id))

    identity, identity_error = fetch_caller_identity(session_id, warnings)
    account_label = uid_traceability_label(identity)
    if args.check_auth_only:
        print("Caller identity: {0}".format(account_label))
        if identity_error:
            print("[WARN] identity check failed: {0}".format(identity_error))
            for hint in identity_guidance_lines(identity_error):
                print("  - {0}".format(hint))
            print("STATUS: {0}".format(STATUS_FAIL))
            print("NEXT_ACTION: repair the credential chain with aliyun "
                  "configure, then re-run")
            return EXIT_BY_STATUS[STATUS_FAIL]
        print("STATUS: {0}".format(STATUS_OK))
        print("NEXT_ACTION: run the report mode with one or more --region-id values")
        return EXIT_BY_STATUS[STATUS_OK]

    problems = validate(args)
    if problems:
        for problem in problems:
            print("[ERROR] invalid input: {0}".format(problem))
        print("STATUS: {0}".format(STATUS_FAIL))
        print("NEXT_ACTION: correct the parameters above (the region is never "
              "guessed, and gated modes need their named target) and re-run")
        return EXIT_BY_STATUS[STATUS_FAIL]

    regions = resolve_regions(args.region_ids, warnings)
    if not regions:
        print("[ERROR] no usable --region-id value was supplied.")
        print("STATUS: {0}".format(STATUS_FAIL))
        print("NEXT_ACTION: ask the customer which region(s) hold the snapshots "
              "or enumerate them from the ECS overview page, then re-run")
        return EXIT_BY_STATUS[STATUS_FAIL]
    if args.mode in ("guest-probe", "prepare-snapshot") and len(regions) != 1:
        print("[ERROR] gated modes accept exactly one --region-id.")
        print("STATUS: {0}".format(STATUS_FAIL))
        print("NEXT_ACTION: re-run with the single region that owns the target")
        return EXIT_BY_STATUS[STATUS_FAIL]
    if identity_error:
        for hint in identity_guidance_lines(identity_error):
            print("  - {0}".format(hint))

    if args.mode == "guest-probe":
        rc = run_guest_probe(args, session_id, warnings)
        _emit_warnings(warnings)
        return rc
    if args.mode == "prepare-snapshot":
        rc = run_prepare_snapshot(args, session_id, warnings)
        _emit_warnings(warnings)
        return rc

    evidence: List[Dict[str, Any]] = []
    for region in regions:
        evidence.append(collect_region(
            region, args, session_id, warnings, errors, args.timeout, args.max_pages
        ))
    findings = analyze(evidence, args.symptom)

    status = STATUS_OK
    if findings["all_failed"]:
        status = STATUS_FAIL
    elif errors or findings["truncated"] or identity_error or any(
            not w.startswith("cli notice") for w in warnings):
        status = STATUS_DEGRADED
    next_action = decide_next_action(args, findings)

    collected = {
        "regions": ", ".join(regions),
        "mode": args.mode,
        "scope": args.scope,
        "instance-id": args.instance_id or "not supplied",
        "disk-id": args.disk_id or "not supplied",
        "snapshot-id": args.snapshot_id or "not supplied",
        "billing-cycle": args.billing_cycle or "not supplied (human cross-check only)",
        "page-size": PAGE_SIZE,
        "max-pages": args.max_pages,
        "per-call-timeout-seconds": args.timeout,
        "user-agent": build_user_agent(session_id),
    }
    ctx = {
        "session_id": session_id,
        "account_label": account_label,
        "billing_cycle": args.billing_cycle,
        "collected": collected,
        "findings": findings,
        "warnings": warnings,
        "errors": errors,
        "status": status,
        "next_action": next_action,
        "args_symptom": args.symptom,
    }
    if args.output == "json":
        print(render_json(ctx))
    else:
        print(render_text(ctx))
        if errors:
            print("\n== Collection errors ==")
            for row in errors:
                print("  [{0}] {1} stage={2}: {3}".format(
                    row.get("code"), row.get("region"), row.get("stage"),
                    row.get("message")))
    write_candidate_file(args, findings, session_id, warnings)

    if status == STATUS_DEGRADED:
        for warning in warnings[:12]:
            sys.stderr.write("[WARN] {0}\n".format(warning))
    print("\nSTATUS: {0}".format(status))
    print("NEXT_ACTION: {0}".format(next_action))
    if status != STATUS_DEGRADED:
        _emit_warnings(warnings)
    return EXIT_BY_STATUS[status]


def _emit_warnings(warnings: List[str]) -> None:
    for warning in warnings:
        sys.stderr.write("[WARN] {0}\n".format(warning))


if __name__ == "__main__":
    sys.exit(main())
