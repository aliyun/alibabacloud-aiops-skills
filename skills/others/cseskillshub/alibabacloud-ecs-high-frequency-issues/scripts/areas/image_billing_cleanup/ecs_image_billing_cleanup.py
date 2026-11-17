#!/usr/bin/env python3
"""
ecs_image_billing_cleanup.py -- single entry point for image billing & cleanup
==============================================================================
Answers the three questions this scenario is about, from evidence rather than
memory:

  faq              what is actually charged (image vs snapshot vs block storage
                   vs outbound traffic), deletion rules, export limits. Pure
                   offline knowledge, no cloud call.
  unblock-check    why unsubscription or the subscription-to-pay-as-you-go
                   conversion is refused for one instance, plus the fixed
                   unblock chain (ecs:DescribeInstances, DescribeImages).
  inventory        image / snapshot cleanup candidates for one region: which
                   image is referenced by which instance, which is a leftover,
                   what the deletion order is (ecs:DescribeInstances,
                   DescribeImages).
  guest-check      deliver ONE approved, non-mutating inspection command inside
                   the instance when the decision needs real used space
                   (ecs:DescribeInvocations, gated RunCommand dispatch).
  snapshot-backup  create the ONE backup snapshot that must exist before any
                   cleanup or space-releasing decision, gated (ecs:DescribeDisks,
                   gated CreateSnapshot dispatch).
  scope            print this skill's action whitelist, gates and deletion
                   ordering without calling anything.

Permission model (RO+G)
-----------------------
The inventory actions above run automatically. The two gated operations --
RunCommand and CreateSnapshot (real RAM names assembled at render time) --
are refused unless the caller passes
--confirm, which the agent may only do after telling the customer what will
run, its blast radius and whether it is reversible, and getting approval for
that one action. Anything destructive (image or snapshot removal, operating
system replacement, unsubscription, refund) is never invoked: this script prints
console steps for the customer instead. Commands outside GUEST_INSPECTION_COMMANDS
cannot be delivered at all -- the payload is selected from the whitelist by key,
never composed from user text.

Every answer is data-driven or comes from the knowledge embedded in
_constants.py; nothing is invented from memory. Empty or failed queries are
reported as limitations. Each run ends with:

    STATUS: OK | DEGRADED | FAIL
    NEXT_ACTION: <one concrete next step>

Usage:
  python3 ecs_image_billing_cleanup.py faq --topic image-vs-snapshot-billing
  python3 ecs_image_billing_cleanup.py scope
  python3 ecs_image_billing_cleanup.py unblock-check --region cn-hangzhou \
      --instance-id i-xxxx
  python3 ecs_image_billing_cleanup.py inventory --region cn-hangzhou
  python3 ecs_image_billing_cleanup.py snapshot-backup --region cn-hangzhou \
      --disk-id d-xxxx --confirm
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import base64
import binascii
import json
import os
import sys
import time

import _cli
from _constants import (
    ALLOWED_ACTIONS,
    CONSOLE_MESSAGE_BRANCHES,
    DEFAULT_TIMEOUT,
    DELETION_ORDER,
    DISKS_ITEMS_PATH,
    FAQ_TOPICS,
    GUEST_INSPECTION_COMMANDS,
    IMAGES_ITEMS_PATH,
    IMAGE_OWNER_LABELS,
    IMAGE_SOURCE_QUERIES,
    INSTANCES_ITEMS_PATH,
    POLL_BUDGET_SECONDS,
    POLL_INTERVAL_SECONDS,
    RAM_ACTION_CREATE_SNAPSHOT,
    RAM_ACTION_RUN_COMMAND,
    SKILL_NAME,
    SNAPSHOT_QUERY_LIMITATION,
    UNSAFE_PATH_CHARS,
    UNBLOCK_CHAIN_STEPS,
    VERDICT_NOTES,
)

# Image statuses that mean "this object exists and is usable for a decision".
# Anything else is reported verbatim instead of being guessed at.
SETTLED_IMAGE_STATUSES = ("Available", "Waiting", "Deprecated")
# Invocation statuses that mean "still in flight" while polling.
ACTIVE_INVOCATION_STATUSES = ("", "Pending", "Running", "Stopping")
# RunCommand delivery budget, in seconds (service-side limit is separate).
GUEST_COMMAND_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Report container
# ---------------------------------------------------------------------------

class Report:
    """Human lines + machine payload + the final STATUS / NEXT_ACTION."""

    def __init__(self, mode: str, region: str = ""):
        self.mode = mode
        self.region = region
        self.title = f"{SKILL_NAME} :: {mode}"
        self.body: list[str] = []
        self.payload: dict = {}
        self.warnings: list[str] = []
        self.status = "OK"
        self.next_action = ""
        self.summary = ""
        self.as_json = False

    def add(self, text: str = "") -> None:
        self.body.append(text)

    def section(self, text: str) -> None:
        self.body.append("")
        self.body.append(text)
        self.body.append("-" * len(text))

    def warn(self, text: str) -> None:
        """Record a limitation: it degrades the run and stays visible."""
        self.warnings.append(text)
        print(f"[WARN] {text}", file=sys.stderr)
        if self.status == "OK":
            self.status = "DEGRADED"

    def fail(self, text: str) -> None:
        self.warnings.append(text)
        print(f"[WARN] {text}", file=sys.stderr)
        self.status = "FAIL"

    def finish(self, as_json: bool) -> None:
        self.as_json = as_json
        envelope = {
            "skill": SKILL_NAME,
            "mode": self.mode,
            "region": self.region or None,
            "session_id": _cli.session_id(),
            "user_agent": _cli.user_agent(),
            "status": self.status,
            "summary": self.summary,
            "warnings": self.warnings,
            "next_action": self.next_action,
        }
        envelope.update(self.payload)
        self.payload = envelope
        if as_json:
            print(json.dumps(self.payload, indent=2, ensure_ascii=False))
            return
        print("=" * 72)
        print(f" {self.title}" + (f"  [{self.region}]" if self.region else ""))
        print("=" * 72)
        for line in self.body:
            print(line)
        if self.warnings:
            self.section("Limitations of this run")
            for text in self.warnings:
                print(f"  - {text}")
        if self.summary:
            self.section("Summary")
            print(_wrap(self.summary))
        print()

    def emit_status(self) -> None:
        """Contract lines for the agent; already JSON fields in --json mode."""
        if getattr(self, "as_json", False):
            return
        print(f"STATUS: {self.status}")
        print(f"NEXT_ACTION: {self.next_action or 'none'}")


def _wrap(text: str, width: int = 72) -> str:
    """Indent long prose so the report stays readable."""
    out = []
    line = "  "
    for word in str(text).split():
        if len(line) + len(word) > width:
            out.append(line)
            line = "  "
        line += word + " "
    out.append(line.rstrip())
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Cloud inventory helpers (all go through _cli, so the whitelist applies)
# ---------------------------------------------------------------------------

def fetch_instances(report: Report, region: str, profile: str | None,
                    instance_ids: list[str] | None = None,
                    critical: bool = True) -> list[dict]:
    params: dict = {}
    if instance_ids:
        params["InstanceIds"] = json.dumps(instance_ids)
    try:
        return _cli.paginate_paged(
            "ecs", "DescribeInstances", params, INSTANCES_ITEMS_PATH,
            region=region, profile=profile)
    except _cli.CliError as e:
        if critical:
            report.fail(f"DescribeInstances failed: {e}")
        else:
            report.warn(f"DescribeInstances failed: {e}")
        return []


def fetch_images(report: Report, region: str, profile: str | None,
                 alias: str | None = None,
                 image_id: str | None = None,
                 critical: bool = True) -> list[dict]:
    params: dict = {}
    if alias:
        params["ImageOwnerAlias"] = alias
    if image_id:
        params["ImageId"] = image_id
    what = f"image_id={image_id}" if image_id else f"source={alias}"
    try:
        return _cli.paginate_paged(
            "ecs", "DescribeImages", params, IMAGES_ITEMS_PATH,
            region=region, profile=profile)
    except _cli.CliError as e:
        message = f"DescribeImages ({what}) failed: {e}"
        if critical:
            report.fail(message)
        else:
            report.warn(message)
        return []


def fetch_disk(report: Report, region: str, profile: str | None,
               disk_id: str) -> dict | None:
    try:
        # DescribeDisks filters by the JSON-array DiskIds parameter; a bare
        # DiskId parameter is rejected by the API contract, verified against
        # the live CLI.
        rows = _cli.paginate_paged(
            "ecs", "DescribeDisks", {"DiskIds": json.dumps([disk_id])},
            DISKS_ITEMS_PATH,
            region=region, profile=profile)
    except _cli.CliError as e:
        report.fail(f"DescribeDisks failed: {e}")
        return None
    return rows[0] if rows else None


def image_of(report: Report, region: str, profile: str | None,
             image_id: str, critical: bool = True) -> dict | None:
    if not image_id:
        return None
    rows = fetch_images(report, region, profile, image_id=image_id,
                        critical=critical)
    return rows[0] if rows else None


def build_image_usage(instances: list[dict]) -> dict[str, list[dict]]:
    """Map ImageId -> the instances currently booted from it."""
    usage: dict[str, list[dict]] = {}
    for inst in instances:
        img = str(inst.get("ImageId") or "")
        if img:
            usage.setdefault(img, []).append(inst)
    return usage


def image_snapshots(image: dict) -> list[str]:
    """Snapshot ids the image is built from, when the response reports them.

    DescribeImages does not always carry them; when absent the caller must say
    so instead of guessing (see SNAPSHOT_QUERY_LIMITATION).
    """
    mappings = image.get("DiskDeviceMappings")
    if isinstance(mappings, dict):
        rows = mappings.get("DiskDeviceMapping") or []
    elif isinstance(mappings, list):
        rows = mappings
    else:
        rows = []
    if isinstance(rows, dict):
        rows = [rows]
    out = []
    for row in rows:
        snap = str((row or {}).get("SnapshotId") or "").strip()
        if snap:
            out.append(snap)
    return out


def classify_image(image: dict, usage: dict[str, list[dict]]) -> str:
    """Return the cleanup-verdict key for one image."""
    owner = str(image.get("ImageOwnerAlias") or "").strip().lower()
    if not owner:
        owner = "self" if image.get("IsSelf") else "unknown"
    status = str(image.get("Status") or "").strip()
    image_id = str(image.get("ImageId") or "")

    if owner == "system":
        return "PUBLIC_IMAGE_KEEP"
    if status == "Creating":
        return "CREATING_WAIT"
    if status == "CreateFailed":
        return "CREATE_FAILED_CANDIDATE"
    if status and status not in SETTLED_IMAGE_STATUSES:
        return "ABNORMAL_STATE_REVIEW"
    if owner == "marketplace":
        return "MARKETPLACE_REVIEW"
    if owner == "others":
        return "SHARED_NOT_OWNED"
    if usage.get(image_id):
        return "IN_USE_BY_INSTANCE"
    return "CLEANUP_CANDIDATE"


def owner_label(image: dict) -> str:
    owner = str(image.get("ImageOwnerAlias") or "").strip().lower()
    return IMAGE_OWNER_LABELS.get(owner, f"unknown source ({owner or 'n/a'})")


def match_console_message(text: str) -> dict | None:
    """First branch whose English console wording appears in the quote."""
    low = (text or "").lower()
    if not low:
        return None
    for branch in CONSOLE_MESSAGE_BRANCHES:
        for needle in branch["match"]:
            if needle in low:
                return branch
    return None


def print_unblock_chain(report: Report) -> None:
    report.section("Fixed unblock chain (customer-executed steps (console or the equivalent OpenAPI), in order)")
    for step in UNBLOCK_CHAIN_STEPS:
        report.add(_wrap(step))
        report.add("")


# ---------------------------------------------------------------------------
# Gate notification (shared by the two gated actions)
# ---------------------------------------------------------------------------

def gate_plan(report: Report, action: str, what: str, impact: str,
              reversible: str, rerun: str) -> None:
    """Refuse to act until the customer approves this specific action."""
    report.title += "  (planned, not executed)"
    report.section("Approval required before this action runs")
    report.add(f"  Cloud action      : {action}")
    report.add(_wrap("What it does      : " + what))
    report.add(_wrap("Blast radius      : " + impact))
    report.add(_wrap("Reversibility     : " + reversible))
    report.add("")
    report.add(_wrap(
        "Nothing has been changed. Tell the customer exactly the three lines "
        "above, and only if they approve, re-run the same command with "
        f"--confirm. Approval covers this one action: {rerun}"))
    report.summary = (
        f"{action} was prepared but not executed because no approval was "
        f"captured for it.")
    report.status = "DEGRADED"
    report.next_action = (
        f"Ask the customer to approve {action} as described above; on approval "
        f"re-run with --confirm. {rerun}")


# ---------------------------------------------------------------------------
# mode: scope
# ---------------------------------------------------------------------------

def mode_scope(args: argparse.Namespace, report: Report) -> None:
    report.title = f"{SKILL_NAME} :: supported scope"
    report.section("Actions this skill may invoke")
    for (product, action), kind in sorted(ALLOWED_ACTIONS.items()):
        label = "automatic inventory" if kind == "auto" else \
            "gated: needs approval for this action"
        report.add(f"  {product}:{action:<24} {label}")
    report.section("Guest inspection command whitelist (one per approval)")
    for key, spec in sorted(GUEST_INSPECTION_COMMANDS.items()):
        report.add(f"  {key} [{spec['os_type']}] {spec['command']}")
        report.add(_wrap("      answers: " + spec["answers"]))
    report.section("Never executed here (customer-executed only: console or the equivalent OpenAPI; this skill never performs them)")
    report.add(_wrap(
        "Removing images or snapshots, replacing the operating system, "
        "unsubscription, release, renewal, refund, voucher or compensation "
        "requests, and any command outside the whitelist above."))
    report.section("Deletion ordering")
    for note in DELETION_ORDER:
        report.add(_wrap("- " + note))
    report.summary = (
        "Scope printed from the built-in whitelist; no cloud call was made.")
    report.next_action = (
        "Pick the mode that matches the customer's question: unblock-check for "
        "a refused unsubscription or conversion, inventory for cleanup "
        "decisions, faq for billing wording, guest-check or snapshot-backup "
        "only after approval.")


# ---------------------------------------------------------------------------
# mode: faq
# ---------------------------------------------------------------------------

def mode_faq(args: argparse.Namespace, report: Report) -> None:
    report.title = f"{SKILL_NAME} :: billing fact card"
    topics = args.topic
    if not topics:
        report.section("Available topics")
        for key in sorted(FAQ_TOPICS):
            report.add(f"  {key}")
            report.add(_wrap("      " + FAQ_TOPICS[key]["question"]))
        report.summary = ("Topic index. A topic was not selected, so no answer "
                          "text was printed.")
        report.next_action = (
            "Re-run with --topic <one key above>; add several keys to answer a "
            "multi-part question in one run.")
        return

    for key in topics:
        topic = FAQ_TOPICS.get(key)
        if not topic:
            report.warn(f"unknown topic '{key}'; it is not part of the "
                        "built-in knowledge, so nothing was answered for it")
            continue
        report.section(f"{key}")
        report.add(_wrap("Q: " + topic["question"]))
        report.add("")
        report.add(_wrap("A: " + topic["answer"]))
        if topic["sources"]:
            report.add("")
            report.add("  Official references:")
            for url in topic["sources"]:
                report.add(f"    {url}")
        else:
            report.add("")
            report.add(_wrap(
                "  No official document backs this entry in this skill; it is "
                "scope guidance only, so verify it in the console or with "
                "human support before repeating it to the customer."))
    known = [t for t in topics if t in FAQ_TOPICS]
    report.payload["topics"] = known
    report.summary = (
        f"Answered {len(known)} of {len(topics)} requested topic(s) from the "
        "built-in knowledge; prices are deliberately not quoted, only the "
        "billing formula and the official references.")
    if not known:
        report.status = "FAIL"
        report.next_action = "Re-run with a valid --topic key (see the index)."
        return
    if args.region:
        report.next_action = (
            f"Attach this wording to the customer's own objects: run inventory "
            f"--region {args.region}, or unblock-check --region {args.region} "
            "--instance-id <id>.")
    else:
        report.next_action = (
            "Offer to run inventory (cleanup candidates) or unblock-check (one "
            "instance) with --region so the answer names the customer's real "
            "images.")


# ---------------------------------------------------------------------------
# mode: unblock-check
# ---------------------------------------------------------------------------

def mode_unblock_check(args: argparse.Namespace, report: Report) -> None:
    region, profile = args.region, args.profile
    report.title = f"{SKILL_NAME} :: unblock check  [{region}]"

    branch = None
    if args.message_branch:
        branch = next((b for b in CONSOLE_MESSAGE_BRANCHES
                       if b["branch"] == args.message_branch), None)
        if branch is None:
            report.fail(f"unknown console-message branch {args.message_branch}")
            report.next_action = "Choose --message-branch from the listed keys."
            return
    elif args.message:
        branch = match_console_message(args.message)

    instances = fetch_instances(report, region, profile, [args.instance_id])
    if not instances:
        report.fail(f"instance {args.instance_id} was not found in {region}")
        report.next_action = (
            f"Confirm the region for {args.instance_id} (the console filters by "
            "region) and re-run with the right --region; if the instance is "
            "already released, use inventory to look for its leftover images "
            "and snapshots instead.")
        return

    inst = instances[0]
    image_id = str(inst.get("ImageId") or "")
    image = image_of(report, region, profile, image_id)

    report.section("Evidence (from ECS OpenAPI)")
    report.add(f"  Instance        : {inst.get('InstanceId')}  "
               f"name={inst.get('InstanceName') or 'n/a'}")
    report.add(f"  State           : {inst.get('Status') or 'n/a'}")
    report.add(f"  Billing method  : {inst.get('InstanceChargeType') or 'n/a'}")
    report.add(f"  Image           : {image_id or 'not reported'}")
    if image:
        report.add(f"  Image source    : "
                   f"{str(image.get('ImageOwnerAlias') or 'n/a')} "
                   f"({owner_label(image)})")
        report.add(f"  Image status    : {image.get('Status') or 'n/a'}")
        report.add(f"  Image OS / size : {image.get('OSType') or 'n/a'} / "
                   f"{image.get('Size') or 'n/a'} GiB")
        snaps = image_snapshots(image)
        snap_text = (", ".join(snaps) if snaps
                     else "not reported by DescribeImages")
        report.add(f"  Snapshots behind it : {snap_text}")
        if not snaps:
            report.add(_wrap("    " + SNAPSHOT_QUERY_LIMITATION))
    else:
        missing = image_id or "the image id reported on the instance"
        report.warn(f"DescribeImages returned no record for {missing}; the "
                    "image source could not be confirmed from the API")

    if branch:
        report.section("Console message the customer quoted")
        report.add(f"  Branch : {branch['branch']}  ->  {branch['action']}")
        report.add(_wrap("  Meaning: " + branch["meaning"]))
    elif args.message:
        report.section("Console message the customer quoted")
        report.add(_wrap(
            f"  Not matched by the built-in routing table: \"{args.message}\""))
        report.add(_wrap(
            "  This is handled as an unmatched refusal reason: the image chain "
            "below is printed as the most likely path, and the exact wording "
            "should be quoted back to support if it does not fit."))
        report.warn("the quoted console text did not match any known branch; "
                    "the conclusion below rests on the image source only")

    source = str((image or {}).get("ImageOwnerAlias") or "").lower()
    blocked = bool(source) and source != "system"

    report.section("Verdict")
    if not image:
        report.add(_wrap(
            "Inconclusive: the image record is missing, so the blocking "
            "question cannot be answered from the API. Ask the customer for the "
            "image id shown in the console, or check the instance detail page."))
    elif source == "system":
        report.add(_wrap(
            "The instance already runs a free public image, so the image is NOT "
            "the reason the operation was refused. Look elsewhere: the billing "
            "method, the instance state, an attached EIP or bandwidth plan, or "
            "an order-level restriction. If the refusal text still mentions an "
            "image, hand the exact quote to human support."))
    elif blocked:
        report.add(_wrap(
            f"The instance is associated with a {source} image "
            f"({owner_label(image)}). Unsubscription and the "
            "subscription-to-pay-as-you-go conversion both require a free "
            "public image, so this association is the blocker and the chain "
            "below applies."))
    if str(inst.get("InstanceChargeType")) == "PostPaid":
        report.add(_wrap(
            "Note: this instance is already pay-as-you-go. Pay-as-you-go "
            "instances are released, not unsubscribed, and releasing one does "
            "not delete its custom images or snapshots."))

    if blocked or branch:
        print_unblock_chain(report)
        report.add(_wrap(
            "Backup alternative: instead of creating the step-1 snapshot by "
            "hand, run mode snapshot-backup with --disk-id once the customer "
            "approves that action."))

    report.summary = (
        f"Instance {args.instance_id} in {region} runs image "
        f"{image_id or 'unknown'} from source {source or 'unknown'}; "
        + ("the image association is what blocks the operation."
           if blocked else
           "the image is not what blocks the operation."))
    report.payload |= {
        "instance": {k: inst.get(k) for k in
                     ("InstanceId", "InstanceName", "Status",
                      "InstanceChargeType", "ImageId", "OSType")},
        "image": {k: image.get(k) for k in
                  ("ImageId", "ImageName", "Status", "ImageOwnerAlias",
                   "OSType", "Size", "Platform") if image and k in image}
        if image else None,
        "snapshots": image_snapshots(image) if image else [],
        "message_branch": branch["branch"] if branch else None,
        "blocked_by_image": blocked,
    }
    if blocked:
        report.next_action = (
            "Walk the customer through the printed chain: approve a backup "
            "snapshot (console, or snapshot-backup mode with --confirm), then "
            "replace the operating system with a free public image in the "
            "console, then retry the unsubscription or conversion; handle any "
            "bound EIP separately.")
    elif source == "system":
        report.next_action = (
            "Route the refusal to its real cause: check the billing method and "
            "attached EIP or bandwidth plan, and quote the exact console text "
            "to human support if it still points at the image.")
    else:
        report.next_action = (
            "Ask the customer for the image id shown in the console and re-run "
            "once DescribeImages can resolve it.")


# ---------------------------------------------------------------------------
# mode: inventory
# ---------------------------------------------------------------------------

def _validate_new_tmp_path(path: str) -> str:
    """Accept only a brand-new file inside the system temporary directory."""
    roots = [os.path.realpath(r) for r in ("/tmp", "/private/tmp")
             if os.path.isdir(r)]
    extra = os.environ.get("TMPDIR")
    if extra and os.path.isdir(os.path.realpath(extra)):
        roots.append(os.path.realpath(extra))
    real = os.path.realpath(path)
    if not any(real.startswith(root + os.sep) for root in roots):
        raise ValueError("the destination must sit inside the system "
                         "temporary directory")
    if os.path.exists(real):
        raise ValueError("the destination already exists; refusing to "
                         "overwrite any existing file")
    return real


def mode_inventory(args: argparse.Namespace, report: Report) -> None:
    region, profile = args.region, args.profile
    report.title = f"{SKILL_NAME} :: image & snapshot inventory  [{region}]"

    instances = fetch_instances(report, region, profile)
    usage = build_image_usage(instances)

    images: list[dict] = []
    seen: set[str] = set()
    for alias in IMAGE_SOURCE_QUERIES:
        # Non-critical per source: one refused source must not sink the whole
        # inventory, and an empty account is a legitimate empty result.
        for row in fetch_images(report, region, profile, alias=alias,
                                critical=False):
            key = str(row.get("ImageId") or json.dumps(row, sort_keys=True))
            if key not in seen:
                seen.add(key)
                images.append(row)

    if not images:
        report.warn("no custom, shared or marketplace image was returned for "
                    f"{region}; the account may have none in this region")

    counts: dict[str, int] = {}
    rows_out: list[dict] = []
    report.section("Images that can produce or stop producing charges")
    report.add("  ImageId            Source      Status       Size  "
               "Referenced by                 Verdict")
    for image in sorted(images, key=lambda i: str(i.get("ImageId") or "")):
        verdict = classify_image(image, usage)
        counts[verdict] = counts.get(verdict, 0) + 1
        image_id = str(image.get("ImageId") or "n/a")
        holders = usage.get(image_id, [])
        holder_text = ", ".join(str(h.get("InstanceId") or "?")
                               for h in holders[:4]) or "no instance"
        if len(holders) > 4:
            holder_text += f" (+{len(holders) - 4} more)"
        report.add(f"  {image_id:<19} "
                   f"{str(image.get('ImageOwnerAlias') or 'n/a'):<10} "
                   f"{str(image.get('Status') or 'n/a'):<11} "
                   f"{str(image.get('Size') or '-'):<6} "
                   f"{holder_text:<28} {verdict}")
        snaps = image_snapshots(image)
        rows_out.append({
            "image_id": image_id,
            "image_name": image.get("ImageName"),
            "source": image.get("ImageOwnerAlias"),
            "status": image.get("Status"),
            "size_gib": image.get("Size"),
            "os_type": image.get("OSType"),
            "creation_time": image.get("CreationTime"),
            "snapshots": snaps,
            "referenced_by": [str(h.get("InstanceId") or "") for h in holders],
            "verdict": verdict,
            "note": VERDICT_NOTES.get(verdict, ""),
        })
        if snaps:
            report.add(f"      snapshots: {', '.join(snaps)}")
        else:
            report.add("      snapshots: not reported here -> "
                       "see the console snapshots page")

    report.section("What each verdict means")
    for verdict in sorted(counts):
        report.add(f"  {verdict}  (x{counts[verdict]})")
        report.add(_wrap(VERDICT_NOTES.get(verdict, "no built-in note")))
        report.add("")

    report.section("Deletion ordering (manual, irreversible)")
    for note in DELETION_ORDER:
        report.add(_wrap("- " + note))

    report.section("Snapshot-level limits of this inventory")
    report.add(_wrap(SNAPSHOT_QUERY_LIMITATION))
    report.add(_wrap(
        "Fees are not read from any billing API by this skill. Open the bill "
        "details and filter by billing item to confirm what any of these "
        "objects costs: "
        "https://billing-cost.console.aliyun.com/finance/expense-report"))

    candidates = [r for r in rows_out
                  if r["verdict"] in ("CLEANUP_CANDIDATE",
                                      "CREATE_FAILED_CANDIDATE")]
    if args.save_list:
        if not args.confirm:
            gate_plan(
                report, "local file write",
                f"write the {len(candidates)} cleanup candidates of {region} to "
                f"a brand-new file {args.save_list}",
                "a new file in the system temporary directory only; no existing "
                "file is touched, no cloud object changes",
                "fully reversible: delete the file locally",
                "or drop --save-list and read the list on screen")
            return
        try:
            dest = _validate_new_tmp_path(args.save_list)
            with open(dest, "w", encoding="utf-8") as handle:
                json.dump({"region": region, "candidates": candidates},
                          handle, indent=2, ensure_ascii=False)
        except (ValueError, OSError) as e:
            report.fail(f"candidate list was not written: {e}")
            report.next_action = (
                "Pass --save-list with a new file path inside the system "
                "temporary directory, and keep --confirm with it.")
            return
        report.add("")
        report.add(f"  Candidate list written to: {dest}")

    released_only = [r for r in rows_out if not r["referenced_by"]]
    report.summary = (
        f"{len(images)} image object(s) in {region} across "
        f"{len(instances)} instance(s); {counts.get('CLEANUP_CANDIDATE', 0)} "
        f"cleanup candidate(s), {counts.get('IN_USE_BY_INSTANCE', 0)} still "
        f"referenced by an instance, {len(released_only)} referenced by none. "
        "Nothing was deleted.")
    report.payload |= {
        "instance_count": len(instances),
        "image_count": len(images),
        "verdict_counts": counts,
        "images": rows_out,
        "candidates": candidates,
        "list_file": args.save_list if args.confirm and candidates else None,
    }
    report.next_action = (
        "Work through references/image-billing-cleanup__cleanup-checklist.md with the customer: "
        "confirm each candidate is unwanted, back up what matters, then delete "
        "image first and snapshots after it in the console; repeat this "
        "inventory for every other region the customer has used.")


# ---------------------------------------------------------------------------
# mode: guest-check
# ---------------------------------------------------------------------------

def _decode_output(value: str) -> str:
    """DescribeInvocations may return the command output base64-encoded."""
    if not value:
        return ""
    try:
        return base64.b64decode(value, validate=True).decode(
            "utf-8", errors="replace")
    except (binascii.Error, ValueError):
        return value


def _invocation_row(body: dict) -> dict | None:
    invocations = (body.get("Invocations") or {}).get("Invocation") or []
    if isinstance(invocations, dict):
        invocations = [invocations]
    for invocation in invocations:
        inv = invocation if isinstance(invocation, dict) else {}
        inner = inv.get("InvokeInstances") or {}
        rows = inner.get("InvokeInstance") if isinstance(inner, dict) else None
        rows = rows or []
        if isinstance(rows, dict):
            rows = [rows]
        for row in rows:
            merged = dict(row) if isinstance(row, dict) else {}
            merged.setdefault("InvokeStatus",
                              inv.get("InvocationStatus"))
            return merged
    return None


def mode_guest_check(args: argparse.Namespace, report: Report) -> None:
    region, profile = args.region, args.profile
    report.title = f"{SKILL_NAME} :: guest inspection  [{region}]"

    spec = GUEST_INSPECTION_COMMANDS.get(args.command)
    if spec is None:
        report.fail(f"command key '{args.command}' is not on the whitelist")
        report.next_action = (
            "Choose --command from: "
            + ", ".join(sorted(GUEST_INSPECTION_COMMANDS)))
        return

    command = spec["command"]
    if spec.get("path_argument"):
        path = args.path or ""
        bad = sorted(set(path) & UNSAFE_PATH_CHARS)
        if not path.startswith("/") or bad:
            report.fail(
                f"the path {path!r} was rejected; it must start with / and "
                f"contain none of {''.join(sorted(UNSAFE_PATH_CHARS))}")
            report.next_action = (
                f"Re-run with --path /absolute/simple/path (no shell "
                f"metacharacters) for --command {args.command}.")
            return
        command = command.format(path=path)

    instances = fetch_instances(report, region, profile, [args.instance_id])
    if not instances:
        report.fail(f"instance {args.instance_id} was not found in {region}")
        report.next_action = (
            f"Verify the region of {args.instance_id} and re-run with the right "
            "--region.")
        return
    inst = instances[0]
    os_type = str(inst.get("OSType") or "").strip().lower()
    if not os_type:
        image = image_of(report, region, profile,
                         str(inst.get("ImageId") or ""))
        os_type = str((image or {}).get("OSType") or "").strip().lower()
    if os_type and os_type != spec["os_type"]:
        report.fail(f"command '{args.command}' is a {spec['os_type']} command "
                    f"but this instance reports {os_type}")
        matching = sorted(k for k, v in GUEST_INSPECTION_COMMANDS.items()
                          if v["os_type"] == os_type)
        if matching:
            example = ("disk-usage" if os_type == "linux"
                       else "windows-volume-usage")
            report.next_action = (
                f"Re-run with one of the whitelist keys for {os_type} "
                f"({', '.join(matching)}); a typical choice is --command "
                f"{example}.")
        else:
            report.next_action = (
                f"No whitelisted command covers os type {os_type}; ask the "
                "customer to run the inspection manually in Workbench and "
                "paste the output.")
        return

    report.section("Planned action")
    report.add(f"  Instance : {inst.get('InstanceId')} "
               f"({inst.get('Status') or 'state n/a'}, "
               f"os {os_type or 'n/a'})")
    report.add(f"  Command  : {command}")
    report.add(_wrap("  Purpose  : " + spec["answers"]))
    report.add(_wrap("  Effect   : " + spec["reversible"]))

    if not args.confirm:
        gate_plan(
            report, RAM_ACTION_RUN_COMMAND,
            f"deliver the single command `{command}` to {args.instance_id} "
            "through Cloud Assistant and read its printed output",
            f"one instance, one non-mutating command; it needs the Cloud "
            f"Assistant agent to be reachable inside {args.instance_id}",
            spec["reversible"],
            "or ask the customer to run it themselves in Workbench and paste "
            "the output")
        return

    content = base64.b64encode(command.encode("utf-8")).decode("ascii")
    try:
        body = _cli.call("ecs", "RunCommand", {
            "RegionId": region,
            "Type": spec["script_type"],
            "Name": f"{SKILL_NAME}-{args.command}",
            "CommandContent": content,
            "ContentEncoding": "Base64",
            "Timeout": GUEST_COMMAND_TIMEOUT,
            "InstanceId.1": args.instance_id,
        }, region=region, profile=profile)
    except _cli.CliError as e:
        report.fail(f"RunCommand was not accepted: {e}")
        report.next_action = (
            "If this is a permission error, grant " + RAM_ACTION_RUN_COMMAND +
            " per "
            "references/ram-policies.md; if Cloud Assistant is unreachable "
            "inside the instance, ask the customer to run the command in "
            "Workbench and paste the output instead.")
        return

    invoke_id = str(body.get("InvokeId") or "")
    if not invoke_id:
        report.fail("RunCommand returned no InvokeId; the outcome is unknown")
        report.next_action = (
            "Check the instance detail page for the delivery result before "
            "retrying, so the same command is not delivered twice.")
        return

    report.add("")
    report.add(f"  InvokeId: {invoke_id}")

    row, terminal = _poll_invocation(report, region, profile, invoke_id)
    report.section("Command output")
    if row is None:
        report.add(_wrap(
            "No per-instance result was available yet. Report this honestly "
            "instead of guessing at the used space."))
    else:
        report.add(f"  Status: {terminal or 'unknown'}")
        output = _decode_output(str(row.get("Output") or ""))
        report.add(output.rstrip() if output.strip() else
                   "  (no output returned)")
        status_text = str(row.get("InvocationStatus") or terminal or "")
        if status_text not in ("", "Finished", "Success"):
            report.warn(f"the invocation ended in state '{status_text}'; treat "
                        "the output above as incomplete")

    report.summary = (
        f"Delivered one approved inspection command ({args.command}) to "
        f"{args.instance_id}; the used-space reading above is guest-side "
        "reality, which no cloud inventory action can report.")
    report.payload |= {
        "invoke_id": invoke_id,
        "command": command,
        "invocation": row,
    }
    if row is not None and terminal in ("Finished", "Success"):
        report.next_action = (
            "Read the numbers together with the cloud-side inventory and state "
            "which backup is needed before any cleanup decision.")
    else:
        report.next_action = (
            f"Read the result later with mode invocation-result --region "
            f"{region} --invoke-id {invoke_id}, or have the customer run the "
            "command in Workbench and paste the output.")


def _poll_invocation(report: Report, region: str, profile: str | None,
                     invoke_id: str) -> tuple[dict | None, str]:
    """Poll one delivered command until it settles or the budget runs out."""
    deadline = time.monotonic() + POLL_BUDGET_SECONDS
    last: dict | None = None
    last_status = ""
    while True:
        try:
            body = _cli.call("ecs", "DescribeInvocations", {
                "RegionId": region,
                "InvokeId": invoke_id,
                "IncludeOutput": True,
                "ContentEncoding": "PlainText",
            }, region=region, profile=profile, timeout=DEFAULT_TIMEOUT)
        except _cli.CliError as e:
            report.warn(f"DescribeInvocations failed while reading the result: "
                        f"{e}")
            return last, last_status
        row = _invocation_row(body)
        if row:
            last = row
            last_status = str(row.get("InvocationStatus")
                              or row.get("InvokeStatus") or "")
            if last_status not in ACTIVE_INVOCATION_STATUSES:
                return row, last_status
        if time.monotonic() >= deadline:
            report.warn(f"the invocation had not settled within "
                        f"{POLL_BUDGET_SECONDS}s; the InvokeId is reported so "
                        f"the result can be read later")
            return last, last_status or "Pending"
        time.sleep(POLL_INTERVAL_SECONDS)


def mode_invocation_result(args: argparse.Namespace, report: Report) -> None:
    """Read the outcome of an already-approved command (no new action)."""
    region, profile = args.region, args.profile
    report.title = f"{SKILL_NAME} :: invocation result  [{region}]"
    try:
        body = _cli.call("ecs", "DescribeInvocations", {
            "RegionId": region,
            "InvokeId": args.invoke_id,
            "IncludeOutput": True,
            "ContentEncoding": "PlainText",
        }, region=region, profile=profile)
    except _cli.CliError as e:
        report.fail(f"DescribeInvocations failed: {e}")
        report.next_action = (
            "Grant ecs:DescribeInvocations per references/ram-policies.md, or "
            "read the invocation result in the Cloud Assistant console page.")
        return
    row = _invocation_row(body)
    report.section(f"Invocation {args.invoke_id}")
    if not row:
        report.add(_wrap(
            "No invocation matched this InvokeId in this region. Nothing was "
            "invented about its output."))
        report.status = "DEGRADED"
        report.next_action = (
            "Confirm the region that delivered the command and re-run with that "
            "--region.")
        return
    status = str(row.get("InvocationStatus") or row.get("InvokeStatus") or "n/a")
    report.add(f"  Status: {status}")
    output = _decode_output(str(row.get("Output") or ""))
    report.add(output.rstrip() if output.strip() else "  (no output returned)")
    report.summary = f"Read invocation {args.invoke_id}: status {status}."
    report.payload |= {"invoke_id": args.invoke_id, "invocation": row,
                      "output": output}
    if status in ("Finished", "Success"):
        report.next_action = ("Use the output together with the cloud-side "
                              "inventory in the cleanup decision.")
    else:
        report.next_action = ("If the status is not terminal, wait for Cloud "
                              "Assistant or fall back to a manual run in "
                              "Workbench.")


# ---------------------------------------------------------------------------
# mode: snapshot-backup
# ---------------------------------------------------------------------------

def mode_snapshot_backup(args: argparse.Namespace, report: Report) -> None:
    region, profile = args.region, args.profile
    report.title = f"{SKILL_NAME} :: backup snapshot  [{region}]"

    disk = fetch_disk(report, region, profile, args.disk_id)
    if disk is None:
        report.fail(f"disk {args.disk_id} was not found in {region}")
        report.next_action = (
            f"Confirm the region and the disk id (ECS console -> Storage -> "
            f"Disks) and re-run; disk ids are region-scoped.")
        return

    report.section("Target disk (from ECS OpenAPI)")
    report.add(f"  Disk        : {disk.get('DiskId')}  "
               f"{disk.get('DiskName') or 'no name'}")
    report.add(f"  Type        : {disk.get('Type') or 'n/a'}")
    report.add(f"  Size        : {disk.get('Size') or 'n/a'} GiB")
    report.add(f"  State       : {disk.get('Status') or 'n/a'}")
    report.add(f"  Attached to : {disk.get('InstanceId') or 'not attached'}")
    if args.instance_id and disk.get("InstanceId") and \
            str(disk.get("InstanceId")) != args.instance_id:
        report.warn(f"this disk is attached to {disk.get('InstanceId')}, not to "
                    f"{args.instance_id}")

    name = args.snapshot_name or f"{SKILL_NAME}-pre-cleanup"
    report.section("Planned action")
    report.add(f"  Cloud action : {RAM_ACTION_CREATE_SNAPSHOT} on {args.disk_id}")
    report.add(_wrap(f"  Snapshot name: {name}"))
    report.add(_wrap(
        "  What it does : starts one snapshot of this single disk; the disk "
        "content is not modified in any way"))
    report.add(_wrap(
        "  Effect       : creates a billable snapshot in this account. "
        "Snapshot storage is charged by capacity x duration with no free "
        "quota, and only the customer can delete it later, in the console, "
        "irreversibly"))

    if not args.confirm:
        gate_plan(
            report, RAM_ACTION_CREATE_SNAPSHOT,
            f"create one snapshot named {name} of disk {args.disk_id} "
            f"({disk.get('Size')} GiB) in {region}",
            f"adds a snapshot to the account, which starts or continues a "
            f"storage charge of roughly the used data size of {args.disk_id}; "
            f"no disk, image or instance content is changed",
            "the snapshot object can be kept or deleted later by the customer "
            "in the console; deletion is irreversible",
            "or let the customer create the same snapshot in the console")
        return

    try:
        body = _cli.call("ecs", "CreateSnapshot", {
            "RegionId": region,
            "DiskId": args.disk_id,
            "SnapshotName": name,
        }, region=region, profile=profile)
    except _cli.CliError as e:
        report.fail(f"CreateSnapshot was not accepted: {e}")
        report.next_action = (
            "If this is a permission error, grant " + RAM_ACTION_CREATE_SNAPSHOT +
            " per "
            "references/ram-policies.md; if the disk is still initializing or "
            "another snapshot is in progress, wait and retry, or create the "
            "snapshot in the console.")
        return

    snapshot_id = str(body.get("SnapshotId") or "")
    report.section("Result")
    report.add(f"  SnapshotId: {snapshot_id or 'not returned'}")
    report.add(_wrap(
        "The snapshot is being created asynchronously. Wait until it shows "
        "as accomplished in the console before replacing the operating system "
        "or deleting anything."))
    report.add(_wrap(
        "Follow-up charges: this snapshot is billed storage. Delete it in the "
        "console when it is no longer needed; deletion is irreversible."))
    report.summary = (
        f"Requested snapshot {snapshot_id or '(id not returned)'} for disk "
        f"{args.disk_id} in {region} after the customer approved that action.")
    report.payload |= {"snapshot_id": snapshot_id, "disk": {
        k: disk.get(k) for k in
        ("DiskId", "DiskName", "Type", "Size", "Status", "InstanceId")}}
    report.next_action = (
        f"Track snapshot {snapshot_id or args.disk_id} to completion, then "
        "continue with the printed unblock chain or the cleanup checklist.")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _common(parents: list[argparse.ArgumentParser]) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False, parents=parents)
    p.add_argument("--profile", default=None,
                   help="aliyun CLI credential profile name")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    return p


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecs_image_billing_cleanup.py",
        description=(
            "ECS image & snapshot billing and cleanup analysis: charges, "
            "cleanup candidates, and unsubscription or conversion blocked by a "
            "paid image"),
    )
    empty = _common([])
    region_parent = _common([])
    region_parent.add_argument("--region", required=True,
                               help="RegionId, e.g. cn-hangzhou")
    opt_region = _common([])
    opt_region.add_argument("--region", default=None,
                            help="optional RegionId; only used to suggest the "
                                 "next cloud-side step")
    sub = parser.add_subparsers(dest="mode", required=True)

    p = sub.add_parser("scope", parents=[empty],
                       help="print the action whitelist, gates and limits")
    p.set_defaults(func=mode_scope, needs_cli=False)

    p = sub.add_parser("faq", parents=[opt_region],
                       help="billing, deletion and export fact card")
    p.add_argument("--topic", action="append",
                   help="topic key; repeat for several questions")
    p.set_defaults(func=mode_faq, needs_cli=False)

    p = sub.add_parser("unblock-check", parents=[region_parent],
                       help="why unsubscription or conversion is refused")
    p.add_argument("--instance-id", required=True)
    p.add_argument("--message", default=None,
                   help="console refusal text quoted by the customer")
    p.add_argument("--message-branch", default=None,
                   choices=[b["branch"] for b in CONSOLE_MESSAGE_BRANCHES],
                   help="use when the customer's text is not English: pick the "
                        "branch that matches its meaning")
    p.set_defaults(func=mode_unblock_check, needs_cli=True)

    p = sub.add_parser("inventory", parents=[region_parent],
                       help="image and snapshot cleanup candidates")
    p.add_argument("--save-list", default=None, metavar="NEW_FILE",
                   help="write the candidate list to a new file in the system "
                        "temporary directory (gated, needs --confirm)")
    p.add_argument("--confirm", action="store_true",
                   help="the customer approved this specific action")
    p.set_defaults(func=mode_inventory, needs_cli=True)

    p = sub.add_parser("guest-check", parents=[region_parent],
                       help="deliver one approved inspection command")
    p.add_argument("--instance-id", required=True)
    p.add_argument("--command", required=True,
                   choices=sorted(GUEST_INSPECTION_COMMANDS),
                   help="whitelist key; the command text itself cannot be "
                        "supplied")
    p.add_argument("--path", default=None,
                   help="absolute path for --command path-size")
    p.add_argument("--confirm", action="store_true",
                   help="the customer approved this specific command")
    p.set_defaults(func=mode_guest_check, needs_cli=True)

    p = sub.add_parser("invocation-result", parents=[region_parent],
                       help="read the output of an already delivered command")
    p.add_argument("--invoke-id", required=True)
    p.set_defaults(func=mode_invocation_result, needs_cli=True)

    p = sub.add_parser("snapshot-backup", parents=[region_parent],
                       help="create the approved pre-cleanup backup snapshot")
    p.add_argument("--disk-id", required=True)
    p.add_argument("--instance-id", default=None,
                   help="optional cross-check of the attachment")
    p.add_argument("--snapshot-name", default=None)
    p.add_argument("--confirm", action="store_true",
                   help="the customer approved this specific snapshot")
    p.set_defaults(func=mode_snapshot_backup, needs_cli=True)

    return parser


# ---------------------------------------------------------------------------
# Offline entry lock (--selftest): the whole cleanup-verdict decision tree and
# every tolerant field-shape reader are pinned here so a future edit that flips
# a branch, loosens a path guard, or reorders precedence fails immediately --
# before the code ever speaks to a real ticket. Pure functions only; no CLI,
# no credentials, no network.
# ---------------------------------------------------------------------------

def _run_selftest() -> int:
    checks = 0

    def ok(cond, label):
        nonlocal checks
        assert cond, f"selftest failed: {label}"
        checks += 1

    # --- build_image_usage: group by ImageId, skip instances without one ---
    usage = build_image_usage([
        {"ImageId": "m-1", "InstanceId": "i-a"},
        {"ImageId": "m-1", "InstanceId": "i-b"},
        {"ImageId": "m-2", "InstanceId": "i-c"},
        {"InstanceId": "i-d"},
        {"ImageId": "", "InstanceId": "i-e"},
    ])
    ok(sorted(usage) == ["m-1", "m-2"], "build_image_usage keys")
    ok([x["InstanceId"] for x in usage["m-1"]] == ["i-a", "i-b"],
       "build_image_usage groups preserve order")
    ok(build_image_usage([]) == {}, "build_image_usage empty")

    # --- image_snapshots: dict-wrapped, bare list, single dict, missing ---
    ok(image_snapshots({"DiskDeviceMappings": {"DiskDeviceMapping": [
        {"SnapshotId": "s-1"}, {"SnapshotId": "s-2"}]}}) == ["s-1", "s-2"],
       "image_snapshots dict-wrapped list")
    ok(image_snapshots({"DiskDeviceMappings": [{"SnapshotId": "s-a"}]})
       == ["s-a"], "image_snapshots bare list")
    ok(image_snapshots({"DiskDeviceMappings": {"DiskDeviceMapping":
        {"SnapshotId": "s-single"}}}) == ["s-single"],
       "image_snapshots single dict row")
    ok(image_snapshots({"DiskDeviceMappings": {"DiskDeviceMapping": [
        {"SnapshotId": ""}, {"SnapshotId": "  "}, {"SnapshotId": "s-keep"}]}})
       == ["s-keep"], "image_snapshots drops blank ids")
    ok(image_snapshots({}) == [], "image_snapshots missing mappings")
    ok(image_snapshots({"DiskDeviceMappings": "garbage"}) == [],
       "image_snapshots non-container")

    # --- classify_image: full decision tree + precedence ---
    ok(classify_image({"ImageOwnerAlias": "system", "ImageId": "x",
        "Status": "Creating"}, {}) == "PUBLIC_IMAGE_KEEP",
       "classify_image system beats Creating (precedence)")
    ok(classify_image({"ImageOwnerAlias": "self", "ImageId": "x",
        "Status": "Creating"}, {}) == "CREATING_WAIT", "classify_image creating")
    ok(classify_image({"ImageOwnerAlias": "self", "ImageId": "x",
        "Status": "CreateFailed"}, {}) == "CREATE_FAILED_CANDIDATE",
       "classify_image create_failed")
    ok(classify_image({"ImageOwnerAlias": "self", "ImageId": "x",
        "Status": "Deprecating"}, {}) == "ABNORMAL_STATE_REVIEW",
       "classify_image unsettled status -> review")
    ok(classify_image({"ImageOwnerAlias": "self", "ImageId": "x",
        "Status": "Deprecated"}, {}) == "CLEANUP_CANDIDATE",
       "classify_image Deprecated is settled")
    ok(classify_image({"ImageOwnerAlias": "marketplace", "ImageId": "x",
        "Status": "Available"}, {}) == "MARKETPLACE_REVIEW",
       "classify_image marketplace")
    ok(classify_image({"ImageOwnerAlias": "others", "ImageId": "x",
        "Status": "Available"}, {}) == "SHARED_NOT_OWNED",
       "classify_image others/shared")
    ok(classify_image({"ImageOwnerAlias": "self", "ImageId": "m-inuse",
        "Status": "Available"}, {"m-inuse": [{"InstanceId": "i-1"}]})
       == "IN_USE_BY_INSTANCE", "classify_image in use")
    ok(classify_image({"ImageOwnerAlias": "self", "ImageId": "m-free",
        "Status": "Available"}, {"m-other": [{"InstanceId": "i-1"}]})
       == "CLEANUP_CANDIDATE", "classify_image unused despite other usage")
    ok(classify_image({"IsSelf": True, "ImageId": "x",
        "Status": "Available"}, {}) == "CLEANUP_CANDIDATE",
       "classify_image IsSelf fallback -> self")
    ok(classify_image({"ImageId": "x", "Status": "Available"}, {})
       == "CLEANUP_CANDIDATE", "classify_image no owner -> unknown path")
    ok(classify_image({"ImageOwnerAlias": "Public-Read", "ImageId": "x",
        "Status": "Available"}, {}) == "CLEANUP_CANDIDATE",
       "classify_image owner is case-folded")

    # --- owner_label: known, unknown, blank ---
    ok(owner_label({"ImageOwnerAlias": "self"})
       == IMAGE_OWNER_LABELS["self"], "owner_label known")
    ok("weird" in owner_label({"ImageOwnerAlias": "weird"}),
       "owner_label unknown echoes value")
    ok("n/a" in owner_label({}), "owner_label blank")

    # --- match_console_message: case-insensitive, first hit, miss, empty ---
    branch = match_console_message(
        "控制台提示 Please REPLACE With A Public Image first")
    ok(branch and branch["branch"] == "REPLACE_PUBLIC_IMAGE_FIRST",
       "match_console_message case-insensitive substring")
    ok(match_console_message("totally unrelated wording") is None,
       "match_console_message no hit")
    ok(match_console_message("") is None and match_console_message(None)
       is None, "match_console_message empty/None")

    # --- _validate_new_tmp_path: fresh temp ok, existing rejected, outside
    #     tmp rejected, traversal rejected ---
    import tempfile
    base = os.path.realpath(tempfile.gettempdir())
    fresh = os.path.join(base, "ecs_img_cleanup_selftest_new")
    while os.path.exists(fresh):
        fresh += "x"
    try:
        ok(os.path.realpath(_validate_new_tmp_path(fresh)) == fresh,
           "validate_tmp_path accepts fresh file")
        with open(fresh, "w") as fh:
            fh.write("x")
        try:
            _validate_new_tmp_path(fresh)
            ok(False, "validate_tmp_path must reject existing file")
        except ValueError:
            ok(True, "validate_tmp_path rejects existing file")
        finally:
            os.remove(fresh)
        try:
            _validate_new_tmp_path(os.path.realpath(__file__))
            ok(False, "validate_tmp_path must reject path outside tmp")
        except ValueError:
            ok(True, "validate_tmp_path rejects path outside tmp")
    except AssertionError:
        raise

    # --- _decode_output: empty, valid base64, non-base64 passthrough ---
    ok(_decode_output("") == "", "decode_output empty")
    ok(_decode_output(base64.b64encode(b"hello world").decode())
       == "hello world", "decode_output valid base64")
    ok(_decode_output("not base64 !!!") == "not base64 !!!",
       "decode_output invalid passthrough")

    # --- _invocation_row: nested list, single dict, missing, empty ---
    row = _invocation_row({"Invocations": {"Invocation": [{
        "InvocationStatus": "Success", "InvokeInstances": {"InvokeInstance": [
            {"InstanceId": "i-1", "Output": "z"}]}}]}})
    ok(row and row["InvokeStatus"] == "Success" and row["Output"] == "z",
       "invocation_row nested list")
    row2 = _invocation_row({"Invocations": {"Invocation": {
        "InvocationStatus": "Running", "InvokeInstances": {"InvokeInstance":
            {"InstanceId": "i-2"}}}}})
    ok(row2 and row2["InvokeStatus"] == "Running" and row2["InstanceId"]
       == "i-2", "invocation_row single-dict rows")
    ok(_invocation_row({}) is None and _invocation_row(
        {"Invocations": {}}) is None, "invocation_row empty")

    print(f"[OK] ecs_image_billing_cleanup self-test passed: {checks} checks")
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if "--selftest" in argv:
        return _run_selftest()
    args = build_parser().parse_args(argv)
    mode = args.mode
    report = Report(mode, getattr(args, "region", "") or "")
    if getattr(args, "needs_cli", False):
        _cli.check_cli_available()
        account = _cli.resolve_account_id(
            region=getattr(args, "region", "") or "",
            profile=getattr(args, "profile", None))
        if not account:
            report.warn("the account identity could not be resolved; the "
                        "report states which account it assumed only if this "
                        "succeeds -- run scripts/areas/image_billing_cleanup/sts_token.py")
        else:
            report.payload["account_uid"] = account
            report.add(f"Account UID (from STS GetCallerIdentity): {account}")
    args.func(args, report)
    report.finish(bool(getattr(args, "json", False)))
    report.emit_status()
    return 0 if report.status in ("OK", "DEGRADED") else 1


if __name__ == "__main__":
    sys.exit(main())
