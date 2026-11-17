#!/usr/bin/env python3
"""
image_lifecycle_check.py -- single entry point for the
area:custom-image-lifecycle skill
====================================================================
SECURITY / PERMISSION MODEL (mirrors SKILL.md, Absolute Rules):
  * Group A  non-mutating evidence queries (Describe*/Get*) run
    automatically -- they change nothing on any resource.
  * Group C  the five confirmation-gated image-chain actions (CreateImage,
    CopyImage, ModifyImageSharePermission, ImportImage, ExportImage) are
    dispatched ONLY in plan mode when the caller additionally passes
    --confirm USER-CONFIRMED, which is legal only AFTER the agent has told
    the end user what will run, its impact and its reversibility, and the
    user said yes (one approval covers exactly one operation).
  * Destructive or commercial operations (any delete / cancel / start /
    stop / attach / detach / release / refund path) are NEVER executed;
    they receive manual guidance only.
  * Guest-inspection commands are never dispatched by this script; the
    guest mode prints the whitelist of inspection-only commands and the
    manual path (Workbench / Cloud Assistant with the user's approval).
Credentials always come from the aliyun CLI default credential chain; this
script never reads, prints or transports any AccessKey / Secret / token.

Modes:
  report    F1  image/snapshot/task/share evidence chain (+region sweep)
  capacity  F2  image system-disk size vs target instance disks
  precheck  F3  CreateImage precondition check for a source instance
  plan      F5  confirmation-gated write chain: plan -> gate -> (confirm)
                -> execute -> re-read status
  guest     F6/6.6  inspection-only in-guest command guidance + refusal
                list for non-whitelisted checks

Every run ends with the contract lines:
  STATUS: OK | DEGRADED | FAIL
  NEXT_ACTION: <one concrete instruction>
Exit codes: 0 = OK/DEGRADED, 1 = FAIL or blocked, 2 = argparse usage error.
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import sys
from typing import Any, Optional

import _cli
from _constants import (
    CONFIRM_PHRASE,
    CONSOLE_LINKS,
    DEFAULT_REGION,
    GUEST_COMMANDS,
    GUEST_OUT_OF_SCOPE,
    HELP_LINKS,
    IMAGE_STATUS_NOTES,
    MECHANISM_NOTES,
    REGION_SWEEP,
    STS_PRODUCT,
    WRITE_OPS,
    WINDOWS_CONFIDENCE_NOTE,
)

ECS = "ecs"


# ---------------------------------------------------------------------------
# Evidence collector
# ---------------------------------------------------------------------------

class Collector:
    """Accumulates findings, degradation marks and the final verdict."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.findings: list[str] = []
        self.suggestions: list[str] = []
        self.auto_filled: list[str] = []
        self.payload: dict[str, Any] = {}
        self.hard_fail: Optional[str] = None

    def warn(self, detail: str) -> None:
        """EXECUTION RULE FOR ERRORS: log `[WARN] <Code>: <Message>` to
        stderr and CONTINUE -- never abort the whole diagnosis silently."""
        line = f"[WARN] {detail}"
        print(line, file=sys.stderr)
        self.errors.append(detail)

    def degrade(self) -> str:
        if self.hard_fail:
            return "FAIL"
        return "DEGRADED" if self.errors else "OK"


# ---------------------------------------------------------------------------
# Pure decision functions (unit-testable; boundary asserts run at import)
# ---------------------------------------------------------------------------

def normalize_gb(value: Any) -> Optional[int]:
    """Coerce an API size value (int GB, or strings like "40"/"100 GiB")
    into integer GB; None when absent or unparseable."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    digits = ""
    for ch in text:
        if ch.isdigit():
            digits += ch
        elif digits:
            break
    return int(digits) if digits else None


assert normalize_gb(40) == 40
assert normalize_gb("100 GiB") == 100
assert normalize_gb("60") == 60
assert normalize_gb(None) is None
assert normalize_gb("abc") is None


def judge_capacity(image_sys_gb: Optional[int],
                   target_sys_gb: Optional[int]) -> dict[str, Any]:
    """Hard rule (ticket-confirmed): the target system disk must be >= the
    image's system-disk size. Returns a verdict with the concrete delta."""
    if image_sys_gb is None or target_sys_gb is None:
        return {"verdict": "UNKNOWN",
                "detail": "image or target system-disk size could not be "
                          "read from the API responses; do NOT conclude."}
    if image_sys_gb <= target_sys_gb:
        return {"verdict": "FITS",
                "detail": f"target system disk {target_sys_gb} GB >= image "
                          f"system disk {image_sys_gb} GB (slack "
                          f"{target_sys_gb - image_sys_gb} GB)",
                "delta_gb": target_sys_gb - image_sys_gb}
    return {"verdict": "TOO_SMALL",
            "detail": f"target system disk {target_sys_gb} GB < image "
                      f"system disk {image_sys_gb} GB: the image CANNOT be "
                      f"used here until the target disk grows by at least "
                      f"{image_sys_gb - target_sys_gb} GB",
            "delta_gb": image_sys_gb - target_sys_gb}


assert judge_capacity(40, 60)["verdict"] == "FITS"
assert judge_capacity(100, 60)["verdict"] == "TOO_SMALL"
assert judge_capacity(100, 60)["delta_gb"] == 40
assert judge_capacity(None, 60)["verdict"] == "UNKNOWN"


def judge_create_blockade(status: str, lock_reasons: list[str]) -> dict[str, Any]:
    """CreateImage precondition distilled from tickets: an instance stopped
    by an overdue / security lock (expired) cannot produce a custom image;
    a normally Running or normally Stopped instance can."""
    locks = sorted({r for r in lock_reasons if r})
    if locks:
        return {"can_proceed": False,
                "reason": f"instance carries operation lock(s): "
                          f"{', '.join(locks)}; while locked (e.g. expired "
                          f"for overdue payment) image creation fails with "
                          f"IncorrectInstanceStatus -- renew / clear the "
                          f"lock first"}
    if status in ("Pending", "Starting", "Stopping", "Deleted"):
        return {"can_proceed": False,
                "reason": f"instance is in transitional state {status}; "
                          f"wait for Running or Stopped"}
    return {"can_proceed": True,
            "reason": f"instance state {status or 'unknown'} is not locked; "
                      f"image creation is allowed (the operation will take "
                      f"one snapshot per covered disk automatically)"}


assert judge_create_blockade("Running", [])["can_proceed"] is True
assert judge_create_blockade("Stopped", ["financial"])["can_proceed"] is False
assert judge_create_blockade("Stopping", [])["can_proceed"] is False


def detect_copy_conflict(processing_tasks: list[dict],
                         creating_copies: list[dict]) -> bool:
    """Same-source uniqueness rule (ticket-confirmed): while one copy task
    of the SAME source image is in progress, a second submission fails
    immediately."""
    if processing_tasks or creating_copies:
        return True
    return False


assert detect_copy_conflict([], []) is False
assert detect_copy_conflict([{"TaskId": "t"}], []) is True


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _image_items(body_items: list[dict]) -> list[dict[str, Any]]:
    """Project only fields actually present in the API response items."""
    out = []
    for img in body_items:
        entry: dict[str, Any] = {
            "image_id": img.get("ImageId"),
            "name": img.get("ImageName"),
            "status": img.get("Status"),
            "size_gb": img.get("Size"),
            "os_type": img.get("OSType"),
            "platform": img.get("Platform"),
            "owner_alias": img.get("ImageOwnerAlias"),
            "creation_time": img.get("CreationTime"),
        }
        progress = img.get("Progress")
        if progress:
            entry["progress"] = progress
        if img.get("Tags") and isinstance(img["Tags"], dict):
            entry["tags"] = img["Tags"].get("Tag") or []
        out.append(entry)
    return out


def _status_note(entry: dict[str, Any]) -> str:
    note = IMAGE_STATUS_NOTES.get(str(entry.get("status")), "")
    return f" ({note})" if note else ""


def _unwrap_locks(attrs: dict[str, Any]) -> list[str]:
    locks = attrs.get("OperationLocks") or {}
    if isinstance(locks, dict):
        items = locks.get("OperationLock") or []
    else:
        items = locks or []
    reasons = []
    for item in items:
        if isinstance(item, dict):
            reasons.append(str(item.get("LockReason") or ""))
    return reasons


def _call_checked(col: Collector, product: str, action: str,
                  params: dict[str, Any], region: str,
                  profile: Optional[str]) -> Optional[dict[str, Any]]:
    try:
        return _cli.call(product, action, params, region=region,
                         profile=profile)
    except _cli.CliError as e:
        col.warn(f"{e.code or 'CliError'}: {e}")
        return None


def _pages_checked(col: Collector, product: str, action: str,
                   params: dict[str, Any], items_path: list[str],
                   region: str, profile: Optional[str]) -> list[dict]:
    try:
        return _cli.paginate_pages(product, action, params,
                                   items_path=items_path, region=region,
                                   profile=profile)
    except _cli.CliError as e:
        col.warn(f"{e.code or 'CliError'}: {e}")
        return []


def _identity(col: Collector, profile: Optional[str]) -> str:
    try:
        body = _cli.call(STS_PRODUCT, "GetCallerIdentity", {},
                         profile=profile)
        uid = str(body.get("AccountId") or "")
        col.payload["identity"] = {
            "account_uid": uid,
            "identity_type": body.get("IdentityType"),
            "arn": body.get("Arn"),
        }
        col.findings.append(f"Account view: UID {uid or 'unknown'} "
                            f"({body.get('IdentityType') or 'Unknown'})")
        return uid
    except _cli.CliError as e:
        col.warn(f"{e.code or 'CliError'}: {e}")
        col.findings.append("Identity view unavailable: all conclusions "
                            "below are limited to the current credential "
                            "and may reflect the wrong account view")
        return ""


def _effective_region(args: argparse.Namespace, col: Collector) -> str:
    if args.region:
        return args.region
    col.auto_filled.append(
        f"region auto-filled to {DEFAULT_REGION} (CLI default); declare "
        f"this to the user -- if the resource lives in another region, "
        f"re-run with --region or --all-regions")
    return DEFAULT_REGION


# ---------------------------------------------------------------------------
# mode: report (F1)
# ---------------------------------------------------------------------------

def mode_report(args: argparse.Namespace, col: Collector) -> None:
    region = _effective_region(args, col)
    _identity(col, args.profile)

    col.payload["images"] = _image_items(_pages_checked(
        col, ECS, "DescribeImages",
        {"RegionId": region,
         "ImageOwnerAlias": args.image_owner_alias,
         "ImageId": args.image_id},
        ["Images", "Image"], region, args.profile))

    if args.instance_id:
        attrs = _call_checked(col, ECS, "DescribeInstanceAttribute",
                              {"InstanceId": args.instance_id},
                              region, args.profile)
        if attrs:
            col.payload["instance"] = {
                "instance_id": attrs.get("InstanceId"),
                "status": attrs.get("Status"),
                "region_id": attrs.get("RegionId"),
                "instance_type": attrs.get("InstanceType"),
                "os_type": attrs.get("OSType"),
                "expired_time": attrs.get("ExpiredTime"),
                "operation_locks": _unwrap_locks(attrs),
            }
        col.payload["disks"] = _pages_checked(
            col, ECS, "DescribeDisks",
            {"RegionId": region, "InstanceId": args.instance_id},
            ["Disks", "Disk"], region, args.profile)
        col.payload["snapshots"] = _pages_checked(
            col, ECS, "DescribeSnapshots",
            {"RegionId": region, "InstanceId": args.instance_id},
            ["Snapshots", "Snapshot"], region, args.profile)

    if args.image_id:
        share = _call_checked(
            col, ECS, "DescribeImageSharePermission",
            {"RegionId": region, "ImageId": args.image_id},
            region, args.profile)
        if share:
            accounts = [a for a in
                        ((share.get("Accounts") or {}).get("Account") or [])
                        if isinstance(a, dict)]
            listed = share.get("ShareCount")
            col.payload["share_permission"] = {
                "image_id": args.image_id,
                # counted from the returned account rows; an API-supplied
                # count is echoed only when the response actually carries one
                "shared_account_count": len(accounts) if listed is None
                                        else listed,
                "accounts": [a.get("AliyunId") or a.get("AccountId") or ""
                             for a in accounts],
            }

    tasks = _pages_checked(col, ECS, "DescribeTasks",
                           {"RegionId": region, "TaskStatus": "Processing"},
                           ["TaskSet", "Task"], region, args.profile)
    if not tasks and not any("DescribeTasks" in e for e in col.errors):
        # some deployments reject the TaskStatus filter shape; one retry
        # without it keeps the progress leg alive.
        tasks = _pages_checked(col, ECS, "DescribeTasks",
                               {"RegionId": region},
                               ["TaskSet", "Task"], region, args.profile)
    col.payload["processing_tasks"] = tasks

    if args.all_regions:
        sweep: dict[str, Any] = {}
        for r in REGION_SWEEP:
            if r == region:
                continue
            try:
                body = _cli.call(ECS, "DescribeImages",
                                 {"RegionId": r, "ImageOwnerAlias": "self",
                                  "PageNumber": 1, "PageSize": 10},
                                 region=r, profile=args.profile)
                total = body.get("TotalCount")
                items = ((body.get("Images") or {}).get("Image")) or []
                sweep[r] = {"total": total,
                            "first_image_ids": [i.get("ImageId")
                                                for i in items[:5]]}
            except _cli.CliError as e:
                col.warn(f"{e.code or 'CliError'}: sweep {r}: {e}")
                sweep[r] = {"error": e.code or "CliError"}
        col.payload["region_sweep"] = sweep

    # ---- findings (only from data actually returned) ----
    images = col.payload.get("images") or []
    creating = [i for i in images if str(i.get("status")) == "Creating"]
    failed = [i for i in images
              if str(i.get("status")) in ("Unavailable", "CreateFailed")]
    available = [i for i in images if str(i.get("status")) == "Available"]
    col.findings.append(
        f"Images visible to this account in {region} "
        f"(owner alias '{args.image_owner_alias}'): {len(images)} total, "
        f"{len(available)} Available, {len(creating)} Creating, "
        f"{len(failed)} failed/unavailable")
    for i in creating:
        col.findings.append(
            f"Creating now: {i['image_id']} "
            f"{i.get('name') or ''} progress={i.get('progress', 'n/a')} "
            f"(duration has no SLA: it rides on the regional snapshot "
            f"pipeline)")
    for i in failed[:5]:
        col.findings.append(
            f"Failed / unavailable: {i['image_id']} {_status_note(i)} "
            f"-- check the underlying snapshots and tasks for the failing "
            f"layer")
    snaps = col.payload.get("snapshots") or []
    progressing = [s for s in snaps
                   if str(s.get("Status")) == "Progressing"]
    if snaps:
        col.findings.append(
            f"Snapshots of instance: {len(snaps)}, currently Progressing: "
            f"{len(progressing)} (image creation rides on this pipeline; "
            f"snapshot progress is the authoritative progress signal)")
        for s in progressing[:5]:
            col.findings.append(
                f"  snapshot {s.get('SnapshotId')} progress="
                f"{s.get('Progress', 'n/a')} category={s.get('Category')}")
    for t in (col.payload.get("processing_tasks") or [])[:10]:
        col.findings.append(
            f"Task in progress: {t.get('TaskId')} action="
            f"{t.get('TaskAction')} status={t.get('TaskStatus')} "
            f"created={t.get('CreationTime')}")
    share = col.payload.get("share_permission")
    if share:
        col.findings.append(
            f"Share relation of {share['image_id']}: "
            f"{share['shared_account_count']} account(s) listed as "
            f"{share['accounts'] or '[]'}")
    if not images:
        col.findings.append(
            f"No images matched in region {region}. Before concluding "
            f"'the image does not exist', exclude the two known view "
            f"errors: wrong region selector and wrong account (shared "
            f"images need --image-owner-alias others).")
        col.suggestions.append(
            "Re-run with --all-regions to sweep the account's visible "
            "regions (the 'image disappeared' tickets are frequently a "
            "region-view artifact).")
    col.suggestions.append(
        "For a size decision run --mode capacity; for CreateImage "
        "preconditions run --mode precheck; mechanism wording: "
        + MECHANISM_NOTES["image-needs-snapshot"])


# ---------------------------------------------------------------------------
# mode: capacity (F2)
# ---------------------------------------------------------------------------

def mode_capacity(args: argparse.Namespace, col: Collector) -> None:
    region = _effective_region(args, col)
    if not args.image_id or not args.target_instance_id:
        col.hard_fail = "capacity mode needs --image-id and " \
                        "--target-instance-id"
        return
    _identity(col, args.profile)

    images = _image_items(_pages_checked(
        col, ECS, "DescribeImages",
        {"RegionId": region, "ImageId": args.image_id},
        ["Images", "Image"], region, args.profile))
    if not images:
        col.hard_fail = (
            f"image {args.image_id} not visible in region {region} under "
            f"this account. Either the region/account view is wrong, or "
            f"the image lives in another region: cross-region use of a "
            f"custom image FIRST requires copying the image (plan mode "
            f"--op copy-image) -- replace-OS cannot cross regions.")
        return
    image = images[0]

    attrs = _call_checked(col, ECS, "DescribeInstanceAttribute",
                          {"InstanceId": args.target_instance_id},
                          region, args.profile)
    target_region = (attrs or {}).get("RegionId")
    disks = _pages_checked(
        col, ECS, "DescribeDisks",
        {"RegionId": region, "InstanceId": args.target_instance_id},
        ["Disks", "Disk"], region, args.profile)
    sys_disks = [d for d in disks if str(d.get("Type")) == "SYSTEM"]
    target_sys_gb = None
    if sys_disks:
        target_sys_gb = normalize_gb(sys_disks[0].get("Size"))

    verdict = judge_capacity(normalize_gb(image.get("size_gb")),
                             target_sys_gb)
    col.payload["capacity"] = {
        "image": image,
        "target_instance": {
            "instance_id": args.target_instance_id,
            "status": (attrs or {}).get("Status"),
            "region_id": target_region,
        },
        "target_disks": [
            {"disk_id": d.get("DiskId"), "type": d.get("Type"),
             "size_gb": d.get("Size"), "category": d.get("Category"),
             "status": d.get("Status")}
            for d in disks],
        "verdict": verdict,
    }
    col.findings.append(
        f"Image {image['image_id']} system disk: {image.get('size_gb')} GB "
        f"(status {image.get('status')}); target system disk: "
        f"{target_sys_gb if target_sys_gb is not None else 'n/a'} GB")
    col.findings.append(f"Capacity verdict: {verdict['verdict']} - "
                        + verdict["detail"])
    col.suggestions.append(MECHANISM_NOTES[
        "replace-os-touches-system-disk-only"])
    col.suggestions.append(MECHANISM_NOTES[
        "new-instance-includes-checked-data-disks"])
    col.suggestions.append(
        "If the target is TOO_SMALL: grow the target system disk first "
        "(that purchase-side path and the partition step belong to the "
        "disk-expand area), or create a new instance of sufficient size "
        "from the image. Shrinking a disk is NOT supported: "
        + MECHANISM_NOTES["disk-shrink-unsupported"]
        + f" Reference: {HELP_LINKS['shrink-disk']}")


# ---------------------------------------------------------------------------
# mode: precheck (F3)
# ---------------------------------------------------------------------------

def mode_precheck(args: argparse.Namespace, col: Collector) -> None:
    region = _effective_region(args, col)
    if not args.instance_id and not args.snapshot_id:
        col.hard_fail = ("precheck mode needs --instance-id (image from an "
                         "instance) or --snapshot-id (image from a "
                         "snapshot)")
        return
    _identity(col, args.profile)

    checks: list[dict[str, Any]] = []
    if args.instance_id:
        attrs = _call_checked(col, ECS, "DescribeInstanceAttribute",
                              {"InstanceId": args.instance_id},
                              region, args.profile)
        if not attrs:
            checks.append({"check": "instance visible",
                           "state": "FAIL",
                           "detail": f"instance {args.instance_id} not "
                                     f"found under this account/region "
                                     f"view"})
        else:
            gate = judge_create_blockade(str(attrs.get("Status") or ""),
                                         _unwrap_locks(attrs))
            checks.append({"check": "instance state / locks",
                           "state": "PASS" if gate["can_proceed"] else "FAIL",
                           "detail": f"Status={attrs.get('Status')} "
                                     f"locks={_unwrap_locks(attrs)} "
                                     f"expired_time={attrs.get('ExpiredTime')}"
                                     f" -> {gate['reason']}"})
            disks = _pages_checked(
                col, ECS, "DescribeDisks",
                {"RegionId": region, "InstanceId": args.instance_id},
                ["Disks", "Disk"], region, args.profile)
            sys_gb = next((normalize_gb(d.get("Size")) for d in disks
                           if str(d.get("Type")) == "SYSTEM"), None)
            data = [d for d in disks if str(d.get("Type")) == "DATA"]
            checks.append({"check": "disk inventory (image will cover "
                                    "system disk; data disks included "
                                    "only when selected)",
                           "state": "INFO",
                           "detail": f"system disk {sys_gb} GB; "
                                     f"{len(data)} data disk(s): "
                                     f"{[(d.get('DiskId'), d.get('Size')) for d in data[:6]]}"})
            snaps = _pages_checked(
                col, ECS, "DescribeSnapshots",
                {"RegionId": region, "InstanceId": args.instance_id},
                ["Snapshots", "Snapshot"], region, args.profile)
            checks.append({"check": "existing snapshots (history / quota "
                                    "context)",
                           "state": "INFO",
                           "detail": f"{len(snaps)} snapshot(s) found; "
                                     f"snapshot storage is billed "
                                     f"pay-as-you-go"})
    if args.snapshot_id:
        snaps = _pages_checked(
            col, ECS, "DescribeSnapshots",
            {"RegionId": region, "SnapshotIds": json.dumps(
                [args.snapshot_id])},
            ["Snapshots", "Snapshot"], region, args.profile)
        usable = [s for s in snaps if str(s.get("Status")) == "accomplished"]
        checks.append({"check": "source snapshot state",
                       "state": "PASS" if usable else "FAIL",
                       "detail": f"{len(snaps)} match; accomplished: "
                                 f"{len(usable)}; progress of newest: "
                                 f"{(snaps[0].get('Progress') if snaps else 'n/a')}"})

    col.payload["precheck"] = checks
    for c in checks:
        col.findings.append(f"[{c['state']}] {c['check']}: {c['detail']}")
    blocked = any(c["state"] == "FAIL" for c in checks)
    col.suggestions.append(MECHANISM_NOTES["image-needs-snapshot"])
    col.suggestions.append(MECHANISM_NOTES["auto-backup-myth"])
    if blocked:
        col.suggestions.append(
            "Fix the failing precondition first (renew / wait for state / "
            "correct the view). Once passed, produce the image through the "
            "confirmation gate: --mode plan --op create-image ...")
    else:
        col.suggestions.append(
            "Preconditions look clear. To create the image through the "
            "confirmation gate run: --mode plan --op create-image "
            f"--region {region} --instance-id <id> --image-name <name>")


# ---------------------------------------------------------------------------
# mode: plan (F5, confirmation-gated writes)
# ---------------------------------------------------------------------------

def _params_for(op: str, args: argparse.Namespace,
                col: Collector) -> tuple[dict[str, Any], list[str]]:
    """Assemble the RPC parameter dict; returns (params, missing list)."""
    region = args.region or DEFAULT_REGION
    params: dict[str, Any] = {}
    missing: list[str] = []

    def req(key: str, value: Any) -> None:
        if value in (None, "", []):
            missing.append(key)
        else:
            params[key] = value

    if op == "create-image":
        params["RegionId"] = region
        if not args.instance_id and not args.snapshot_id:
            missing.append("InstanceId or SnapshotId")
        if args.instance_id:
            params["InstanceId"] = args.instance_id
        if args.snapshot_id:
            params["SnapshotId"] = args.snapshot_id
        req("ImageName", args.image_name)
        if args.description:
            params["Description"] = args.description
    elif op == "copy-image":
        params["RegionId"] = region
        req("ImageId", args.image_id)
        req("DestinationRegionId", args.dest_region)
        if args.dest_image_name:
            params["DestinationImageName"] = args.dest_image_name
        elif args.image_id:
            auto = f"{args.image_id}-copy-{args.dest_region or region}"
            params["DestinationImageName"] = auto
            col.auto_filled.append(
                f"DestinationImageName auto-filled to '{auto}'")
        else:
            missing.append("ImageId (for the auto-filled destination name)")
    elif op == "share-image":
        params["RegionId"] = region
        req("ImageId", args.image_id)
        req("AddAccount.n", args.accounts)
        if args.accounts:
            for idx, uid in enumerate(
                    [a.strip() for a in args.accounts.split(",") if a.strip()],
                    start=1):
                params[f"AddAccount.{idx}"] = uid
            params.pop("AddAccount.n", None)
    elif op == "import-image":
        params["RegionId"] = region
        req("ImageName", args.image_name)
        req("OSType", args.ostype)
        req("Platform", args.platform)
        req("DiskDeviceMapping.1.OSSBucket", args.oss_bucket)
        req("DiskDeviceMapping.1.OSSObject", args.oss_object)
        for key, val in (("DiskDeviceMapping.1.Format", args.image_format),
                         ("DiskDeviceMapping.1.DiskImageSize",
                          args.disk_image_size),
                         ("Architecture", args.architecture),
                         ("BootMode", args.boot_mode),
                         ("LicenseType", args.license_type)):
            if val:
                params[key] = val
    elif op == "export-image":
        params["RegionId"] = region
        req("ImageId", args.image_id)
        req("OSSBucket", args.oss_bucket)
        if args.oss_prefix:
            params["OSSPrefix"] = args.oss_prefix
        if args.image_format:
            params["ImageFormat"] = args.image_format
        if args.role_name:
            params["RoleName"] = args.role_name
    if args.dry_run:
        params["DryRun"] = True
    return params, missing


def _preflight(op: str, params: dict[str, Any], region: str,
               args: argparse.Namespace, col: Collector) -> bool:
    """Non-mutating preflight per operation. Returns False when the plan is
    blocked (then nothing may execute even with --confirm)."""
    if op == "create-image" and params.get("InstanceId"):
        attrs = _call_checked(col, ECS, "DescribeInstanceAttribute",
                              {"InstanceId": params["InstanceId"]},
                              region, args.profile)
        if not attrs:
            col.warn("preflight: instance not visible under this account/"
                     "region view; refusing")
            return False
        gate = judge_create_blockade(str(attrs.get("Status") or ""),
                                     _unwrap_locks(attrs))
        if not gate["can_proceed"]:
            col.findings.append(f"PREFLIGHT BLOCKED: {gate['reason']}")
            return False
        col.findings.append(f"PREFLIGHT PASS: {gate['reason']}")
        return True
    if op == "create-image" and params.get("SnapshotId"):
        snaps = _pages_checked(
            col, ECS, "DescribeSnapshots",
            {"RegionId": region,
             "SnapshotIds": json.dumps([params["SnapshotId"]])},
            ["Snapshots", "Snapshot"], region, args.profile)
        if not any(str(s.get("Status")) == "accomplished" for s in snaps):
            col.findings.append(
                "PREFLIGHT BLOCKED: source snapshot not found or not "
                "accomplished yet (progress-based: an image can only be "
                "built on a finished snapshot).")
            return False
        col.findings.append("PREFLIGHT PASS: source snapshot accomplished")
        return True
    if op == "copy-image":
        images = _image_items(_pages_checked(
            col, ECS, "DescribeImages",
            {"RegionId": region, "ImageId": params.get("ImageId")},
            ["Images", "Image"], region, args.profile))
        if not images:
            col.findings.append("PREFLIGHT BLOCKED: source image not "
                                "visible in the source region view")
            return False
        if str(images[0].get("status")) != "Available":
            col.findings.append(
                f"PREFLIGHT BLOCKED: source image status is "
                f"{images[0].get('status')}, copy requires Available")
            return False
        # same-source uniqueness pre-check (turns the post-hoc console
        # error into a pre-submission finding)
        dest = params.get("DestinationRegionId") or ""
        dup = _pages_checked(
            col, ECS, "DescribeImages",
            {"RegionId": dest, "ImageOwnerAlias": "self",
             "ImageName": params.get("DestinationImageName"),
             "Status": "Creating"},
            ["Images", "Image"], dest, args.profile) if dest else []
        tasks = _pages_checked(
            col, ECS, "DescribeTasks", {"RegionId": region},
            ["TaskSet", "Task"], region, args.profile)
        conflict = detect_copy_conflict(
            [t for t in tasks if str(t.get("TaskStatus")) == "Processing"
             and "copy" in str(t.get("TaskAction", "")).lower()], dup)
        if conflict:
            col.findings.append(
                "PREFLIGHT WARNING: an in-progress copy of this image (or "
                "a Creating image with the same destination name) appears "
                "to exist. Only ONE copy task per source image is allowed; "
                "wait for the current one. Note: failed copy tasks may "
                "not show in the console task list at all.")
        else:
            col.findings.append("PREFLIGHT PASS: no conflicting in-progress "
                                "copy visible")
        return True
    if op == "share-image":
        images = _image_items(_pages_checked(
            col, ECS, "DescribeImages",
            {"RegionId": region, "ImageId": params.get("ImageId"),
             "ImageOwnerAlias": "self"},
            ["Images", "Image"], region, args.profile))
        if not images:
            col.findings.append(
                "PREFLIGHT BLOCKED: the image is not owned by this "
                "account (only self-owned custom images can be shared; "
                "marketplace or received images cannot be re-shared).")
            return False
        col.findings.append("PREFLIGHT PASS: self-owned image; sharing is "
                            "region-scoped (receiver uses it in THIS "
                            "region; for another region copy first)")
        return True
    if op == "import-image":
        col.findings.append(
            "PREFLIGHT LIMIT (DEGRADED by design): this skill's API "
            "surface cannot verify the OSS bucket/object contents, nor the "
            "guest boot mode / drivers inside the image file. Before "
            "confirming, ask the customer to verify the object exists in "
            "the region's OSS console and to run the compatibility "
            "precheck list (references/custom-image-lifecycle__root-causes.md, section scenario "
            "174).")
        return True
    if op == "export-image":
        images = _image_items(_pages_checked(
            col, ECS, "DescribeImages",
            {"RegionId": region, "ImageId": params.get("ImageId")},
            ["Images", "Image"], region, args.profile))
        if not images:
            col.findings.append("PREFLIGHT BLOCKED: image not visible in "
                                "this account/region view")
            return False
        entry = images[0]
        if str(entry.get("os_type") or "").lower() == "windows":
            col.findings.append(
                "POLICY BLOCK: " + MECHANISM_NOTES[
                    "windows-export-not-allowed-by-license"])
            return False
        if str(entry.get("owner_alias")) != "self":
            col.findings.append(
                "PREFLIGHT BLOCKED: only self-owned custom images can be "
                "exported")
            return False
        col.findings.append(
            "PREFLIGHT PASS: self-owned non-Windows image. Cost notice: "
            "export writes objects into the OSS bucket (storage + "
            "requests billed under OSS pay-as-you-go).")
        return True
    return True


def mode_plan(args: argparse.Namespace, col: Collector) -> None:
    op = args.op
    if not op or op not in WRITE_OPS:
        col.hard_fail = (f"plan mode needs --op one of: "
                         f"{', '.join(sorted(WRITE_OPS))}")
        return
    meta = WRITE_OPS[op]
    action = meta["action"]
    region = args.region or DEFAULT_REGION
    if not args.region:
        col.auto_filled.append(
            f"region auto-filled to {DEFAULT_REGION}; confirm this is the "
            f"intended source region before asking the user to approve")
    _identity(col, args.profile)

    params, missing = _params_for(op, args, col)
    if missing:
        col.hard_fail = ("missing required parameter(s) for "
                         f"{action}: {', '.join(missing)}")
        return

    col.payload["plan"] = {
        "operation": op,
        "action": action,
        "product": ECS,
        "parameters": params,
        "purpose": meta["purpose"],
        "impact": meta["impact"],
        "reversibility": meta["reversibility"],
    }
    col.findings.append(
        f"PLANNED WRITE: {action} with parameters "
        f"{json.dumps(params, ensure_ascii=False)}")

    if not _preflight(op, params, region, args, col):
        col.hard_fail = (f"preflight refused {action}; fix the named "
                         f"condition and re-plan")
        return

    confirmed = args.confirm == CONFIRM_PHRASE
    if args.confirm and not confirmed:
        col.hard_fail = (f"--confirm value must be exactly "
                         f"'{CONFIRM_PHRASE}'")
        return

    gate_text = (
        "CONFIRMATION GATE (agent must relay ALL of it to the user BEFORE "
        "executing):\n"
        f"  WHAT      : {action} via this skill, parameters "
        f"{json.dumps(params, ensure_ascii=False)}\n"
        f"  PURPOSE   : {meta['purpose']}\n"
        f"  IMPACT    : {meta['impact']}\n"
        f"  REVERSIBLE: {meta['reversibility']}\n"
        "  QUESTION  : 'May I run this now?' -- one approval covers exactly "
        "this one operation; any parameter change requires a new approval.")
    col.payload["gate"] = gate_text

    if not confirmed:
        col.suggestions.append(
            "Nothing has been executed. Present the gate text to the user; "
            f"only after explicit approval re-run with --confirm "
            f"{CONFIRM_PHRASE}.")
        return

    col.findings.append("User confirmation recorded (--confirm passed); "
                        "dispatching the approved action.")
    try:
        body = _cli.call(ECS, action, params, region=region,
                         profile=args.profile)
    except _cli.CliError as e:
        if args.dry_run and e.code.lower().startswith("dryrun"):
            col.findings.append(
                f"DRY-RUN validation succeeded ({e.code}): parameters and "
                f"permissions are accepted; nothing was created.")
            col.payload["execution"] = {"dry_run": "passed",
                                        "code": e.code}
            return
        col.warn(f"{e.code or 'CliError'}: {e}")
        guidance = next((v for k, v in
                         sorted(_ERROR_GUIDANCE_ITEMS())
                         if e.code and k.lower() in e.code.lower()), None)
        if guidance:
            col.suggestions.append(f"{e.code}: {guidance}")
        col.hard_fail = (f"{action} execution failed; no write happened "
                         f"(or it partially applied -- verify with report "
                         f"mode before retrying)")
        return
    col.payload["execution"] = {
        "request_id": body.get("RequestId"),
        "image_id": body.get("ImageId"),
        "task_id": body.get("TaskId"),
    }
    if args.dry_run:
        col.findings.append(
            "DryRun was requested: the API returned without creating "
            "anything; treat this as parameter/permission validation only.")
    col.findings.append(
        f"{action} accepted. RequestId={body.get('RequestId')} "
        f"ImageId={body.get('ImageId') or 'n/a'} "
        f"TaskId={body.get('TaskId') or 'n/a'}")
    col.suggestions.append(
        "Read the result back through the evidence chain: "
        f"--mode report --region {region}"
        + (f" --image-id {body.get('ImageId')}" if body.get("ImageId")
           else "")
        + " (image status/progress, snapshots and tasks).")


def _ERROR_GUIDANCE_ITEMS():
    from _constants import ERROR_GUIDANCE
    return ERROR_GUIDANCE.items()


# ---------------------------------------------------------------------------
# mode: guest (inspection-only in-guest guidance)
# ---------------------------------------------------------------------------

def mode_guest(args: argparse.Namespace, col: Collector) -> None:
    os_name = (args.os or "linux").lower()
    if os_name not in GUEST_COMMANDS:
        col.hard_fail = "--os must be linux or windows in guest mode"
        return
    allowed = GUEST_COMMANDS[os_name]
    selected = [c for c in allowed
                if not args.guest_check or c["check"] in args.guest_check]
    col.payload["guest_plan"] = {
        "os": os_name,
        "inspection_only_commands": selected,
        "never_allowed": [desc + " -> " + route
                          for desc, route in GUEST_OUT_OF_SCOPE],
        "confidence_note": WINDOWS_CONFIDENCE_NOTE if os_name == "windows"
                           else "",
        "rules": [
            "Each command is inspection-only: it lists state and changes "
            "nothing on the disk.",
            "Before dispatching ANY in-guest command the agent must tell "
            "the user what will run, that it is non-mutating, and get a "
            "yes for exactly that one command.",
            "Run them only through a channel the customer's instance "
            "actually exposes (Workbench / Cloud Assistant). This script "
            "never dispatches guest commands itself.",
            "If no such channel is usable (agent offline, no permission): "
            "mark the reading DEGRADED, hand the customer the exact "
            "command lines to paste back, and never invent readings.",
        ],
    }
    for c in selected:
        col.findings.append(f"[{os_name}] {c['cmd']}  <- {c['purpose']}")
    if os_name == "windows":
        col.findings.append(WINDOWS_CONFIDENCE_NOTE)
    col.suggestions.append(
        "Out-of-whitelist guest requests (drivers, grub/boot, sshd "
        "config, anything mutating) are refused: give manual steps via "
        f"VNC {CONSOLE_LINKS['vnc-login']} and the docs in "
        "references/custom-image-lifecycle__console-guides.md instead.")


# ---------------------------------------------------------------------------
# Rendering & CLI
# ---------------------------------------------------------------------------

def render(col: Collector, as_json: bool, status: str,
           next_action: str) -> None:
    if as_json:
        print(json.dumps({
            "status": status,
            "next_action": next_action,
            "findings": col.findings,
            "suggestions": col.suggestions,
            "auto_filled": col.auto_filled,
            "errors": col.errors,
            "data": col.payload,
        }, indent=2, ensure_ascii=False))
        return
    print("=" * 72)
    print("ECS custom image lifecycle - evidence report")
    print("=" * 72)
    if col.auto_filled:
        print("\nAuto-filled parameters (declare these to the user):")
        for a in col.auto_filled:
            print(f"  - {a}")
    if col.payload:
        print("\nCollected evidence (verbatim API-derived fields):")
        print(json.dumps(col.payload, indent=2, ensure_ascii=False))
    if col.findings:
        print("\nFindings:")
        for f in col.findings:
            print(f"  - {f}")
    if col.suggestions:
        print("\nSuggestions (manual guidance; writes only via the "
              "confirmation gate):")
        for s in col.suggestions:
            print(f"  - {s}")
    if col.errors:
        print("\nGraceful degradation log:")
        for e in col.errors:
            print(f"  - [WARN] {e}")
    print("\nSummary")
    print("-------")
    if col.hard_fail:
        print(f"Hard stop: {col.hard_fail}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="image_lifecycle_check.py",
        description="ECS custom-image lifecycle evidence + confirmation-"
                    "gated chain runner (see SKILL.md before use)",
    )
    p.add_argument("--mode", required=True,
                   choices=["report", "capacity", "precheck", "plan",
                            "guest"],
                   help="report=F1 evidence chain; capacity=F2 size check; "
                        "precheck=F3 CreateImage preconditions; plan=F5 "
                        "gated write chain; guest=inspection guidance")
    p.add_argument("--region", default=None,
                   help=f"source region id (default auto-fill: "
                        f"{DEFAULT_REGION}, declared in output)")
    p.add_argument("--all-regions", action="store_true",
                   help="report mode: sweep the common region list to "
                        "rule out a wrong-region view")
    p.add_argument("--instance-id", default=None)
    p.add_argument("--image-id", default=None)
    p.add_argument("--target-instance-id", default=None,
                   help="capacity mode: instance whose disks are compared")
    p.add_argument("--snapshot-id", default=None)
    p.add_argument("--image-owner-alias", default="self",
                   choices=["self", "system", "others", "marketplace"],
                   help="DescribeImages owner filter (custom images: self;"
                        " images shared TO you: others)")
    p.add_argument("--op", default=None,
                   choices=sorted(WRITE_OPS.keys()),
                   help="plan mode: the gated operation to plan/execute")
    p.add_argument("--image-name", default=None)
    p.add_argument("--description", default=None)
    p.add_argument("--dest-region", default=None,
                   help="copy-image: DestinationRegionId")
    p.add_argument("--dest-image-name", default=None)
    p.add_argument("--accounts", default=None,
                   help="share-image: comma-separated receiver account "
                        "ids (AddAccount.n)")
    p.add_argument("--oss-bucket", default=None)
    p.add_argument("--oss-object", default=None)
    p.add_argument("--oss-prefix", default=None)
    p.add_argument("--image-format", default=None)
    p.add_argument("--disk-image-size", default=None)
    p.add_argument("--ostype", default=None, choices=[None, "linux",
                                                      "windows"])
    p.add_argument("--platform", default=None)
    p.add_argument("--architecture", default=None)
    p.add_argument("--boot-mode", default=None)
    p.add_argument("--license-type", default=None)
    p.add_argument("--role-name", default=None)
    p.add_argument("--dry-run", action="store_true",
                   help="plan mode: attach the RPC DryRun parameter "
                        "(validate without creating)")
    p.add_argument("--confirm", default=None,
                   help=f"execution gate: exactly '{CONFIRM_PHRASE}', "
                        f"legal only after the user approved the announced "
                        f"impact")
    p.add_argument("--os", default=None, choices=[None, "linux", "windows"],
                   help="guest mode: which inspection command set")
    p.add_argument("--guest-check", action="append", default=None,
                   choices=["space", "inode", "mount", "data-size",
                            "deleted-open-files", "file-stat"],
                   help="guest mode: limit to specific check(s)")
    p.add_argument("--profile", default=None,
                   help="optional aliyun CLI credential profile name")
    p.add_argument("--json", action="store_true", help="JSON output")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    col = Collector()

    dispatch = {
        "report": mode_report,
        "capacity": mode_capacity,
        "precheck": mode_precheck,
        "plan": mode_plan,
        "guest": mode_guest,
    }
    try:
        _cli.check_cli_available()
        dispatch[args.mode](args, col)
    except _cli.CliError as e:  # belt-and-braces: modes already degrade
        col.warn(f"{e.code or 'CliError'}: {e}")

    if col.hard_fail:
        render(col, args.json, "FAIL",
               f"Resolve: {col.hard_fail}")
        print("\nSTATUS: FAIL")
        print(f"NEXT_ACTION: {col.hard_fail}")
        return 1

    needs_confirm = (args.mode == "plan" and args.confirm is None)
    next_action = (
        "Present the CONFIRMATION GATE text to the user (what runs / "
        "impact / reversibility). Execute ONLY after an explicit yes, by "
        f"re-running this mode with --confirm {CONFIRM_PHRASE}."
        if needs_confirm else
        "Compose the report from the findings above; cite only values "
        "listed here and the handoff table in "
        "references/custom-image-lifecycle__handoff-boundaries.md.")
    status = col.degrade()
    render(col, args.json, status, next_action)
    print(f"\nSTATUS: {status}")
    print(f"NEXT_ACTION: {next_action}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
