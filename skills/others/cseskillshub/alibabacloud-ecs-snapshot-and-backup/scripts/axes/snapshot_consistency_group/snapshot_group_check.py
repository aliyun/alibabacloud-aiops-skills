#!/usr/bin/env python3
"""
snapshot_group_check.py -- single entry point for the
alibabacloud-ecs-snapshot-consistency-group skill.
===================================================
SECURITY / PERMISSION MODEL: this tool is strictly READ-ONLY. It only issues
Describe* reads through the shared `_cli.call()` choke point, and a runtime
whitelist (`_ensure_read_only`) aborts the call if any action outside that
whitelist is requested. It never changes a cloud resource, never runs
anything inside a customer instance, and takes credentials from the aliyun
CLI default credential chain only.

Modes
-----
  precheck  Read-only facts behind "can I create a snapshot consistency group
            here, and why doesn't my automatic snapshot policy keep several
            disks consistent?" -- environment element (customer-declared),
            region element, per-disk category / size / count facts, and each
            disk's own automatic snapshot policy binding.
  verify    Read-only re-check after the customer acted: per-disk snapshot
            records and their completion state, whether a usable
            pre-rollback backup exists, and the instance run/stop state.
  rules     Offline capability-boundary answers distilled from this tier's
            support tickets and the official documentation (no API call),
            selected by keyword match on --question or exactly by --topic.

Output contract
---------------
A human-readable report is printed by default; `--json` prints the same
evidence structure as JSON. Both end with:

    STATUS: OK|DEGRADED|FAIL
    NEXT_ACTION: <one concrete next step>

STATUS is OK when every requested read succeeded, DEGRADED when at least one
read failed but usable evidence remains (a [WARN] line names each failed
read), and FAIL when the run has no usable result at all. Every report prints
the knowledge-verification date, because the capability wording embedded in
this skill is version-sensitive.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import _cli
from _constants import (
    ALLOWED_ECS_ACTIONS,
    DEFAULT_TIMEOUT,
    DISK_CATEGORY_NOTES,
    ECS_API_VERSION,
    ECS_PRODUCT,
    ENVIRONMENT_NOTES,
    HANDOFF_MAP,
    KNOWLEDGE_VERIFIED_DATE,
    MAX_TIMEOUT,
    MIN_TIMEOUT,
    RULES_TOPICS,
    SKILL_NAME,
    SNAPSHOT_DETAIL_LIMIT,
)

# The STS identity read is allowed on top of the ECS read whitelist.
ALLOWED_ACTIONS = tuple(ALLOWED_ECS_ACTIONS) + ("GetCallerIdentity",)

# DescribeSnapshots Status values that decide completion. The support wording
# is "100% upload progress is the real completion", which in the API is the
# point where Status stops being `progressing` and becomes `accomplished`.
STATUS_ACCOMPLISHED = "accomplished"
STATUS_PROGRESSING = "progressing"
STATUS_FAILED = "failed"

# Instance state relevant to the rollback precondition.
INSTANCE_STOPPED = "Stopped"

RAM_REFERENCE = "references/ram-policies.md"


# ---------------------------------------------------------------------------
# Read-only whitelist guard (structural enforcement of the prohibition)
# ---------------------------------------------------------------------------

def _ensure_read_only(product: str, action: str) -> None:
    """Raise unless (product, action) is on the read-only whitelist."""
    if action not in ALLOWED_ACTIONS or product != ECS_PRODUCT:
        if not (product == "sts" and action == "GetCallerIdentity"):
            raise RuntimeError(
                "blocked request outside the read-only whitelist: "
                f"{product} {action}"
            )


def _read_pages(report: "Report", action: str, params: dict, container: str,
                key: str, args: argparse.Namespace) -> List[dict]:
    """One paginated read; returns [] after recording a limitation on error."""
    _ensure_read_only(ECS_PRODUCT, action)
    try:
        items = _cli.paginate_rpc(ECS_PRODUCT, action, params, container, key,
                                  args.region_id, args.profile,
                                  timeout=args.timeout)
    except _cli.CliError as err:
        handle_cli_error(report, action, params, err)
        return []
    return items


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="snapshot_group_check.py",
        description=(
            "Read-only Alibaba Cloud ECS snapshot consistency group "
            "precheck, verification and capability-boundary answers"
        ),
        epilog=(
            "This tool never performs any change on a cloud resource. "
            "Authentication uses the aliyun CLI default credential chain; "
            "never pass key material on the command line."
        ),
    )
    parser.add_argument("--mode", required=True,
                        choices=("precheck", "verify", "rules"),
                        help="precheck=creation feasibility facts, "
                             "verify=post-creation or post-rollback status, "
                             "rules=capability-boundary answers")
    parser.add_argument("--region-id", default=None,
                        help="required by precheck/verify, e.g. cn-hangzhou; "
                             "ECS snapshot and disk facts are region-isolated")
    parser.add_argument("--instance-id", default=None,
                        help="ECS instance id, e.g. i-c0o0abc1234567")
    parser.add_argument("--disk-ids", default=None,
                        help="comma-separated disk ids, e.g. d-aaa,d-bbb")
    parser.add_argument("--environment", default="unknown",
                        choices=("public", "gov", "dedicated", "unknown"),
                        help="customer-declared environment; the read-only "
                             "APIs cannot determine it")
    parser.add_argument("--question", default=None,
                        help="customer wording, used to select rule answers "
                             "and to detect handoff topics")
    parser.add_argument("--topic", default=None, choices=sorted(RULES_TOPICS),
                        help="answer exactly one rule topic instead of "
                             "keyword matching")
    parser.add_argument("--window-hours", type=int, default=24,
                        help="verify mode: hours of history to describe when "
                             "looking for a fresh pre-rollback backup "
                             "(default 24)")
    parser.add_argument("--profile", default=None,
                        help="optional aliyun CLI credential profile name")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"per-call timeout in seconds, "
                             f"{MIN_TIMEOUT}-{MAX_TIMEOUT}, default "
                             f"{DEFAULT_TIMEOUT}")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit JSON instead of the human report")
    return parser


# ---------------------------------------------------------------------------
# Report accumulator
# ---------------------------------------------------------------------------

class Report:
    """Evidence, findings, limitations and errors collected in one run."""

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.uid = ""
        self.session = ""
        self.evidence: List[Dict[str, Any]] = []
        self.findings: List[str] = []
        self.limitations: List[str] = []
        self.errors: List[Dict[str, str]] = []
        self.warnings: List[str] = []
        self.rule_answers: List[Dict[str, Any]] = []
        self.handoffs: List[Dict[str, str]] = []
        self.actions: List[str] = []
        self.degraded = False
        self.fatal = False

    def record(self, action: str, params: Dict[str, Any], observation: str,
               fields: Optional[List[str]] = None) -> None:
        """Append one real API read to the evidence chain."""
        self.evidence.append({
            "product": ECS_PRODUCT,
            "apiVersion": ECS_API_VERSION,
            "api": action,
            "params": {k: v for k, v in params.items() if v is not None},
            "observation": observation,
            "fieldsObserved": fields or [],
        })

    def finding(self, text: str) -> None:
        self.findings.append(text)

    def limitation(self, text: str) -> None:
        if text not in self.limitations:
            self.limitations.append(text)

    def warn(self, text: str) -> None:
        self.warnings.append(text)
        print(f"[WARN] {text}", file=sys.stderr)

    def error(self, code: str, text: str, action: str = "") -> None:
        entry = {"code": code, "message": text}
        if action:
            entry["missingAction"] = action
        self.errors.append(entry)
        print(f"[WARN] {code}: {text}", file=sys.stderr)

    def next_action(self, text: str) -> None:
        if text not in self.actions:
            self.actions.append(text)

    def used_actions(self) -> List[str]:
        return sorted({item["api"] for item in self.evidence})

    @property
    def status(self) -> str:
        if self.fatal:
            return "FAIL"
        if self.mode == "rules":
            if not self.rule_answers:
                return "FAIL"
            return "DEGRADED" if self.errors or self.degraded else "OK"
        if not self.evidence:
            return "FAIL"
        return "DEGRADED" if (self.degraded or self.errors) else "OK"

    @property
    def next(self) -> str:
        if self.actions:
            return self.actions[0]
        if self.mode == "rules":
            return ("run --mode precheck with the customer's region and "
                    "instance or disk scope to add the cloud-side facts")
        return ("no further read-only check is required for this question; "
                "the customer performs the documented console steps and this "
                "tool can then re-verify them read-only")


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def validate_args(args: argparse.Namespace, report: Report) -> None:
    """Mark the run fatal on unusable input (never guesses a value)."""
    if not MIN_TIMEOUT <= args.timeout <= MAX_TIMEOUT:
        report.fatal = True
        report.error("InvalidParameterValue",
                     f"--timeout must be between {MIN_TIMEOUT} and "
                     f"{MAX_TIMEOUT} seconds (got {args.timeout})")
        return
    if args.window_hours <= 0:
        report.fatal = True
        report.error("InvalidParameterValue",
                     "--window-hours must be a positive number of hours "
                     f"(got {args.window_hours})")
        return
    if args.mode in ("precheck", "verify"):
        if not args.region_id:
            report.fatal = True
            report.error(
                "MissingParameter",
                "--region-id is required for mode precheck and verify. ECS "
                "snapshot and disk facts are isolated per region, so guessing "
                "a region can turn an existing resource into a false 'not "
                "found'. Ask the customer which region the console shows.")
            return
        if not args.instance_id and not args.disk_ids:
            report.fatal = True
            report.error(
                "MissingParameter",
                "provide --instance-id or --disk-ids so the reads stay scoped "
                "to the resources the customer asked about; an unscoped "
                "account-wide scan is not run by this skill.")
            return
    if args.mode == "rules" and not (args.question or args.topic):
        report.fatal = True
        report.error(
            "MissingParameter",
            "mode rules needs --question (the customer's own wording) or "
            "--topic; one of: " + ", ".join(sorted(RULES_TOPICS)))


# ---------------------------------------------------------------------------
# Permission-failure handling
# ---------------------------------------------------------------------------

_PERMISSION_MARKERS = (
    "nopermission", "implicitdeny", "accessdenied", "notauthorized",
    "unauthorized", "no permission", "access denied", "not authorized",
)


def _looks_like_permission_failure(err: _cli.CliError) -> bool:
    haystack = f"{err.code} {err.stderr}".lower()
    return any(marker in haystack for marker in _PERMISSION_MARKERS)


def handle_cli_error(report: Report, action: str, params: dict,
                     err: _cli.CliError) -> None:
    """Degrade one failed read into a [WARN] plus a limitation, and for an
    authorization failure also name the single missing RAM action with a
    minimal policy the administrator can attach."""
    report.degraded = True
    if _looks_like_permission_failure(err):
        ram_action = f"{ECS_PRODUCT}:{action}"
        minimal_policy = {
            "Version": "1",
            "Statement": [{
                "Effect": "Allow",
                "Action": [ram_action],
                "Resource": "*",
            }],
        }
        report.error(
            code=err.code or "NoPermission",
            text=(f"{action} was denied with NoPermission or ImplicitDeny. "
                  f"The credential is missing exactly one read action: "
                  f"{ram_action}. Minimal policy to attach: "
                  f"{json.dumps(minimal_policy)}"),
            action=ram_action)
        report.limitation(
            f"That cloud fact is unavailable because the credential is not "
            f"granted {ram_action} (NoPermission or ImplicitDeny); the answer "
            f"for that element falls back to the documented rule wording.")
        report.next_action(
            f"have the account administrator grant the read-only action "
            f"{ram_action} (see {RAM_REFERENCE}), then re-run this exact "
            f"command unchanged")
        return

    code = err.code or "CliCallFailed"
    scope = ", ".join(f"{k}={v}" for k, v in params.items() if v is not None)
    scope_text = scope or "no parameters"
    report.error(code=code,
                 text=f"{action} did not complete with [{scope_text}]: "
                      f"{str(err)[:300]}")
    report.limitation(
        f"That cloud fact is unavailable ({code}); the answer for that "
        f"element degrades to the documented rule wording only.")
    if "regionid" in code.lower():
        report.next_action(
            "confirm the exact --region-id with the customer, because ECS "
            "resources are region-isolated, then re-run")
    else:
        report.next_action(
            f"resolve the {code} condition reported above, then re-run this "
            f"read once; nothing is retried automatically here")


# ---------------------------------------------------------------------------
# Caller identity (traceability label only)
# ---------------------------------------------------------------------------

def attach_identity(report: Report, args: argparse.Namespace) -> None:
    """Resolve the account UID behind the active credential; never fatal."""
    report.session = _cli.session_id()
    try:
        _ensure_read_only("sts", "GetCallerIdentity")
        body = _cli.call("sts", "GetCallerIdentity", {}, profile=args.profile,
                         timeout=args.timeout)
        report.uid = str(body.get("AccountId", "") or "")
    except (_cli.CliError, RuntimeError) as err:
        report.degraded = True
        report.warn(f"caller identity unavailable: {err}")
        report.limitation(
            "The account UID could not be resolved, so this evidence cannot "
            "be labelled with the account that was queried. The rule answers "
            "and the region-scoped reads are unaffected.")


# ---------------------------------------------------------------------------
# precheck mode
# ---------------------------------------------------------------------------

def disk_category_facts(disks: List[dict]) -> Tuple[List[dict], List[str],
                                                   List[str], List[str]]:
    """Classify disks with the embedded category table.

    Returns (rows, essd_ids, non_essd_ids, unknown_ids). A category missing
    from the table stays unknown instead of being guessed.
    """
    rows: List[dict] = []
    essd_ids: List[str] = []
    non_essd_ids: List[str] = []
    unknown_ids: List[str] = []
    for disk in disks:
        disk_id = str(disk.get("DiskId", "") or "")
        raw_category = str(disk.get("Category", "") or "")
        note = DISK_CATEGORY_NOTES.get(raw_category)
        if note is None:
            label = raw_category or "not returned by the API"
            is_essd: Optional[bool] = None
            unknown_ids.append(disk_id)
        else:
            label, is_essd = note
            if is_essd:
                essd_ids.append(disk_id)
            else:
                non_essd_ids.append(disk_id)
        rows.append({
            "diskId": disk_id,
            "categoryRaw": raw_category,
            "categoryLabel": label,
            "essdFamily": is_essd,
            "type": str(disk.get("DiskType", "") or ""),
            "sizeGiB": disk.get("Size"),
            "status": str(disk.get("Status", "") or ""),
            "policyOn": disk.get("EnableAutomatedSnapshotPolicy"),
            "autoSnapshotPolicyId": str(
                disk.get("AutoSnapshotPolicyId", "") or ""),
        })
    return rows, essd_ids, non_essd_ids, unknown_ids


def run_precheck(report: Report, args: argparse.Namespace) -> None:
    """Collect the read-only facts that decide a group-creation question."""
    disk_ids = [d.strip() for d in (args.disk_ids or "").split(",")
                if d.strip()]

    instances: List[dict] = []
    if args.instance_id:
        inst_params = {"RegionId": args.region_id,
                       "InstanceIds": json.dumps([args.instance_id])}
        instances = _read_pages(report, "DescribeInstances", inst_params,
                                "Instances", "Instance", args)
        if instances:
            inst = instances[0]
            report.record("DescribeInstances", inst_params,
                          f"1 instance returned: Status="
                          f"{inst.get('Status', 'not returned')}, "
                          f"InstanceType="
                          f"{inst.get('InstanceType', 'not returned')}",
                          ["Status", "InstanceType", "InstanceNetworkType"])
            report.finding(
                f"Instance {args.instance_id} exists in region "
                f"{args.region_id} with Status="
                f"{inst.get('Status', 'not returned')} and type "
                f"{inst.get('InstanceType', 'not returned')}.")
        elif not report.degraded:
            report.record("DescribeInstances", inst_params,
                          "query succeeded but returned no instance for this "
                          "region", [])
            report.finding(
                f"No instance {args.instance_id} was returned in region "
                f"{args.region_id}. ECS resources are region-isolated, so "
                f"confirm the console region before concluding the instance "
                f"is absent.")
            report.next_action(
                f"confirm which region instance {args.instance_id} lives in, "
                f"then re-run with the corrected --region-id")

    disk_params: Dict[str, Any] = {"RegionId": args.region_id}
    if args.instance_id:
        disk_params["InstanceId"] = args.instance_id
    elif disk_ids:
        disk_params["DiskIds"] = json.dumps(disk_ids)
    disks: List[dict] = []
    if args.instance_id or disk_ids:
        disks = _read_pages(report, "DescribeDisks", dict(disk_params),
                            "Disks", "Disk", args)

    if disks:
        report.record("DescribeDisks", disk_params,
                      f"{len(disks)} disk(s) returned",
                      ["DiskId", "Category", "DiskType", "Size", "Status",
                       "EnableAutomatedSnapshotPolicy",
                       "AutoSnapshotPolicyId"])

    rows, essd_ids, non_essd_ids, unknown_ids = disk_category_facts(disks)
    for row in rows:
        family = ("yes" if row["essdFamily"] else
                  ("no" if row["essdFamily"] is False else "unknown"))
        policy = (f"its own automatic snapshot policy "
                  f"{row['autoSnapshotPolicyId'] or '(id not returned)'}"
                  if (row["policyOn"] or row["autoSnapshotPolicyId"]) else
                  "no automatic snapshot policy enabled")
        size = row["sizeGiB"] if row["sizeGiB"] is not None else "?"
        report.finding(
            f"Disk {row['diskId']} ({row['type'] or 'type not returned'}, "
            f"{size} GiB, category={row['categoryRaw'] or 'not returned'} "
            f"-> {row['categoryLabel']}; ESSD family: {family}) is "
            f"{row['status'] or 'state not returned'} and carries {policy}.")

    if rows:
        if non_essd_ids:
            report.finding(
                "Disk(s) " + ", ".join(non_essd_ids) + " are outside the ESSD "
                "family. The documented group wording targets multiple ESSD "
                "cloud disks, so those disks are reported as a fact and the "
                "customer must check the current supported-category list for "
                "them; this skill does not assert a support verdict that the "
                "documentation does not state.")
        if unknown_ids:
            report.limitation(
                "No disk category was returned for " + ", ".join(unknown_ids)
                + ", so the category element cannot be judged for that disk.")
        if len(essd_ids) >= 2:
            report.finding(
                str(len(essd_ids)) + " disk(s) are in the ESSD family ("
                + ", ".join(essd_ids) + "), so the disk-category element is "
                "satisfied for a multi-disk group covering those disks.")
        if len(rows) == 1:
            report.finding(
                "Only one disk is in scope, so there is no multi-disk "
                "consistency requirement here.")
            add_handoff(report, 1)

        per_disk_policy = [r for r in rows if r["autoSnapshotPolicyId"]]
        if len(per_disk_policy) >= 2:
            report.finding(
                "These " + str(len(per_disk_policy)) + " disks each carry an "
                "independent automatic snapshot policy binding ("
                + ", ".join(f"{r['diskId']}={r['autoSnapshotPolicyId']}"
                            for r in per_disk_policy) + "). A policy is "
                "evaluated per disk, so binding the same policy to several "
                "disks does NOT yield one shared point in time; only a "
                "manually created snapshot consistency group does.")

        report.next_action(
            "hand the customer the creation steps in "
            "references/precheck-checklist.md for the disk list above; the "
            "customer creates the group in the console, then re-run this tool "
            "with --mode verify")
    else:
        report.limitation(
            "No disk facts were collected, so the precheck degrades to the "
            "documented rule wording plus the customer-declared environment.")
        report.next_action(
            "re-run with a --disk-ids list copied from the customer's console "
            "view of that instance, in the same region")

    report.finding(
        "Environment element (customer-declared): "
        + ENVIRONMENT_NOTES[args.environment] + ".")
    if args.environment != "public":
        report.limitation(
            "The environment type is not exposed by any whitelisted read "
            "operation, so it was taken from the customer's own statement and "
            "is the sole basis for the support-scope element of this answer.")

    report.limitation(
        "Snapshot consistency group objects cannot be queried with the read "
        "operations verified for this skill, so group membership is inferred "
        "from per-disk snapshot records and their CreationTime values; the "
        "customer confirms the group entry itself in the console.")

    attach_rule_answers(report, args, ("support-scope",
                                       "auto-policy-vs-group",
                                       "group-basics"))


# ---------------------------------------------------------------------------
# verify mode
# ---------------------------------------------------------------------------

def snapshot_state_verdict(status: str, progress: Any) -> str:
    """Map Status plus progress onto the documented completion criterion."""
    normalized = (status or "").strip().lower()
    progress_text = "" if progress is None else str(progress).strip()
    suffix = f", Progress={progress_text}" if progress_text else ""
    if normalized == STATUS_ACCOMPLISHED:
        return "complete (Status=accomplished" + suffix + ")"
    if normalized == STATUS_PROGRESSING:
        return ("NOT complete - still uploading to OSS" + suffix
                + "; the snapshot is only usable once the upload reaches 100%")
    if normalized == STATUS_FAILED:
        return "FAILED (Status=failed" + suffix + ") - not usable"
    return ("unrecognised state (Status="
            + (status or "not returned") + suffix
            + ") - treat as not confirmed complete")


def _minute_key(raw: Any) -> str:
    """Normalise an ECS CreationTime to minute precision.

    Values look like 2026-07-31T09:15Z (some API versions add seconds). The
    first 16 characters are always YYYY-MM-DDTHH:MM, which compares correctly
    as plain text.
    """
    return str(raw or "").strip()[:16]


def fresh_backup_finding(report: Report, snapshots: List[dict],
                         args: argparse.Namespace) -> None:
    """Judge whether a usable pre-rollback backup exists in this scope.

    A rollback overwrites the current state, so the documented precondition is
    a fresh snapshot of that state taken before stopping. Only records that
    reached Status=accomplished count as usable.
    """
    if not snapshots:
        return
    accomplished = [s for s in snapshots
                    if str(s.get("Status", "")).strip().lower()
                    == STATUS_ACCOMPLISHED]
    report.finding(
        str(len(accomplished)) + " of " + str(len(snapshots))
        + " returned snapshot record(s) reached Status=accomplished, so only "
          "those are usable as a rollback source or as a pre-rollback backup.")
    if not accomplished:
        report.finding(
            "No accomplished snapshot exists in this scope, so nothing here "
            "could serve as a pre-rollback backup.")
        report.next_action(
            "tell the customer to take a fresh snapshot of the current state "
            "in the console and wait for Status=accomplished before any "
            "rollback; this skill never takes it for them")
        return

    cutoff = (datetime.now(timezone.utc)
              - timedelta(hours=args.window_hours)).strftime("%Y-%m-%dT%H:%M")
    recent: List[str] = []
    unparseable = 0
    for snap in accomplished:
        key = _minute_key(snap.get("CreationTime"))
        if len(key) < 16:
            unparseable += 1
            continue
        if key >= cutoff:
            recent.append(str(snap.get("SnapshotId", "?")) + " at " + key)
    if unparseable:
        report.limitation(
            str(unparseable) + " accomplished record(s) carried a CreationTime "
            "this tool could not parse, so they were left out of the "
            "freshness judgement rather than guessed at.")
    window_text = str(args.window_hours)
    if recent:
        report.finding(
            str(len(recent)) + " accomplished snapshot(s) were created within "
            + "the last " + window_text + " hour(s) (UTC cutoff " + cutoff
            + "): " + ", ".join(recent[:SNAPSHOT_DETAIL_LIMIT])
            + ". One of these can undo the rollback if the newest data "
              "matters.")
    else:
        report.finding(
            "No accomplished snapshot was created within the last "
            + window_text + " hour(s) (UTC cutoff " + cutoff
            + "), so no recent pre-rollback backup is visible in this scope.")
        report.next_action(
            "before rolling back, tell the customer to take a fresh snapshot "
            "of the current state and wait for Status=accomplished; this "
            "skill never takes it for them")
    report.limitation(
        "The freshness window is a judgement aid, not a claim about which "
        "snapshot the customer means to roll back to; raise --window-hours "
        "when the intended backup is older than " + window_text + " hours.")


def run_verify(report: Report, args: argparse.Namespace) -> None:
    """Re-check snapshot and instance facts after the customer acted."""
    disk_ids = [d.strip() for d in (args.disk_ids or "").split(",")
                if d.strip()]

    snap_params: Dict[str, Any] = {"RegionId": args.region_id}
    if args.instance_id:
        snap_params["InstanceId"] = args.instance_id
    elif len(disk_ids) == 1:
        snap_params["DiskId"] = disk_ids[0]
    snapshots = _read_pages(report, "DescribeSnapshots", dict(snap_params),
                            "Snapshots", "Snapshot", args)

    newest_by_disk: Dict[str, str] = {}
    if snapshots:
        report.record("DescribeSnapshots", snap_params,
                      f"{len(snapshots)} snapshot record(s) returned",
                      ["SnapshotId", "SnapshotName", "Status", "Progress",
                       "CreationTime", "SourceDiskId", "SourceDiskType",
                       "Category", "Usage"])
        shown = 0
        for snap in snapshots:
            if shown >= SNAPSHOT_DETAIL_LIMIT:
                report.finding(
                    f"... {len(snapshots) - shown} further snapshot record(s) "
                    f"left out of this report by the "
                    f"{SNAPSHOT_DETAIL_LIMIT}-row display cap.")
                break
            shown += 1
            report.finding(
                f"Snapshot {snap.get('SnapshotId', '?')} on source disk "
                f"{snap.get('SourceDiskId', '?')} "
                f"({snap.get('SourceDiskType', '?')} disk, "
                f"category={snap.get('Category', '?')}, created "
                f"{snap.get('CreationTime', '?')}, name="
                f"{snap.get('SnapshotName') or '(unnamed)'}): "
                + snapshot_state_verdict(str(snap.get("Status", "") or ""),
                                         snap.get("Progress")))
            src = str(snap.get("SourceDiskId", "") or "")
            created = str(snap.get("CreationTime", "") or "")
            if src and created and created > newest_by_disk.get(src, ""):
                newest_by_disk[src] = created

        if len(newest_by_disk) >= 2:
            distinct = sorted(set(newest_by_disk.values()))
            if len(distinct) == 1:
                report.finding(
                    "The newest snapshots of " + str(len(newest_by_disk))
                    + " distinct source disks share CreationTime "
                    + distinct[0] + ", which is the observable signature of "
                      "one consistency-group operation covering those disks.")
            else:
                pairs = ", ".join(f"{d}={t}" for d, t in
                                  sorted(newest_by_disk.items())[:10])
                report.finding(
                    "The newest snapshots of " + str(len(newest_by_disk))
                    + " distinct source disks carry " + str(len(distinct))
                    + " different CreationTime values (" + pairs
                    + "), so this set is NOT point-in-time consistent. "
                      "Independent per-disk snapshots, including ones produced "
                      "by the same automatic snapshot policy, never share a "
                      "single time point.")
                report.next_action(
                    "tell the customer that a consistent set needs a manually "
                    "created snapshot consistency group, then run --mode "
                    "precheck for the disk list")
            report.limitation(
                "Snapshots are matched to a group by comparing per-disk "
                "records and CreationTime values; no verified read operation "
                "returns the group object, so confirm the group entry in the "
                "console.")
    elif not report.degraded:
        report.record("DescribeSnapshots", snap_params,
                      "query succeeded with zero snapshot records in this "
                      "region", [])
        if args.instance_id:
            scope_label = f"instance {args.instance_id}"
        elif disk_ids:
            scope_label = f"disk {disk_ids[0]}"
        else:
            scope_label = "the requested scope"
        report.finding(
            f"Region {args.region_id} has no snapshot record for "
            f"{scope_label}. Snapshots are region-isolated, so confirm the "
            f"region before concluding that nothing was created.")
        report.next_action(
            "confirm the console region with the customer; if the region is "
            "right, no snapshot record exists in this account scope, so the "
            "creation the customer described did not complete")

    fresh_backup_finding(report, snapshots, args)

    if args.instance_id:
        inst_params = {"RegionId": args.region_id,
                       "InstanceIds": json.dumps([args.instance_id])}
        instances = _read_pages(report, "DescribeInstances", inst_params,
                                "Instances", "Instance", args)
        if instances:
            state = str(instances[0].get("Status", "") or "")
            report.record("DescribeInstances", inst_params,
                          f"Status={state or 'not returned'}", ["Status"])
            if state == INSTANCE_STOPPED:
                report.finding(
                    f"Instance {args.instance_id} is Stopped, which satisfies "
                    f"the documented stop-before-rollback precondition.")
            elif state:
                report.finding(
                    f"Instance {args.instance_id} is {state}, not Stopped. "
                    f"Rolling back disks with a consistency group requires the "
                    f"instance to be stopped first, and a fresh snapshot of "
                    f"the current state should be taken before stopping so the "
                    f"newest data stays recoverable.")
                report.next_action(
                    "tell the customer to take a fresh snapshot of the current "
                    "state, then stop the instance and perform the rollback in "
                    "the console; this skill never stops an instance and "
                    "never performs a rollback")
            else:
                report.limitation(
                    "DescribeInstances returned no Status value, so the "
                    "stop-before-rollback precondition is unverified.")

    report.finding(
        "This is a read-only re-check of facts. The consistency-group "
        "creation and the rollback itself are performed by the customer in "
        "the console, so this tool never concludes that a change was made on "
        "the customer's behalf.")
    if disk_ids:
        report.finding("Requested disk scope: " + ", ".join(disk_ids)
                       + "; per-disk records are listed above.")

    attach_rule_answers(report, args, ("completion-criteria",
                                       "rollback-prerequisites"))


# ---------------------------------------------------------------------------
# rules mode and rule selection
# ---------------------------------------------------------------------------

def score_topic(question: str, topic: dict) -> int:
    """Count embedded keywords of one rule topic found in the wording."""
    lowered = question.lower()
    return sum(1 for keyword in topic["keywords"] if keyword in lowered)


def select_topics(report: Report, args: argparse.Namespace,
                  defaults: Tuple[str, ...]) -> List[str]:
    """Resolve which rule topics to answer: --topic, then --question keyword
    scoring, then the mode defaults. Never invents a topic."""
    if args.topic:
        return [args.topic]
    if args.question:
        scored = sorted(((score_topic(args.question, RULES_TOPICS[name]), name)
                         for name in RULES_TOPICS), reverse=True)
        hits = [name for score, _ in scored if score > 0][:3]
        if hits:
            return hits
        report.limitation(
            "The customer wording matched no embedded rule topic, so this "
            "answer falls back to the mode's default topics instead of "
            "asserting a conclusion the skill has no evidence for.")
    return list(defaults)


def format_rule_answer(name: str, topic: dict) -> Dict[str, Any]:
    return {
        "topic": name,
        "question": topic["question"],
        "answer": topic["answer"],
        "sources": list(topic["sources"]),
        "confidence": topic["confidence"],
    }


# Customer-wording markers that mean "this belongs to a neighbouring area".
_HANDOFF_TRIGGERS = (
    (0, ("fee", "billing", "cost", "charged", "package", "resource plan",
         "discount", "invoice", "deduct")),
    (1, ("single disk", "one disk only", "cross-region replication",
         "copy the snapshot to another region", "automatic snapshot policy "
         "for one disk")),
    (2, ("help me roll back", "please roll back", "roll it back for me",
         "delete the group", "create it for me", "run the script for us")),
    (3, ("fstab", "mount", "mount point", "cannot see the disk after",
         "partition", "no such device")),
    (4, ("entry is missing", "cannot find the menu", "no button",
         "not visible in the console", "option is gone")),
    (5, ("commercial", "call me back", "callback", "coupon", "sales")),
)


def add_handoff(report: Report, index: int) -> None:
    entry = HANDOFF_MAP[index]
    summary = {"area": entry["area"], "response": entry["response"]}
    if summary not in report.handoffs:
        report.handoffs.append(summary)


def detect_handoff(report: Report, question: Optional[str]) -> None:
    """Recognise neighbouring-area topics from the customer's own words; the
    diagnosis itself is never performed here."""
    if not question:
        return
    lowered = question.lower()
    for index, markers in _HANDOFF_TRIGGERS:
        if any(marker in lowered for marker in markers):
            add_handoff(report, index)


def attach_rule_answers(report: Report, args: argparse.Namespace,
                        defaults: Tuple[str, ...]) -> None:
    for name in select_topics(report, args, defaults):
        report.rule_answers.append(format_rule_answer(name, RULES_TOPICS[name]))
    detect_handoff(report, args.question)


def run_rules(report: Report, args: argparse.Namespace) -> None:
    """Offline capability-boundary answers; no cloud call is made."""
    attach_rule_answers(report, args, ("group-basics",))
    if not report.rule_answers:
        report.fatal = True
        report.error("NoMatchingTopic",
                     "no rule topic matched the request, and there is no "
                     "evidence in this skill to answer it. Report the gap "
                     "instead of guessing.")
        return
    for answer in report.rule_answers:
        report.finding(
            f"[rule:{answer['topic']}] {answer['answer']}")
    report.limitation(
        "Rules mode answers from embedded official-document wording verified "
        + KNOWLEDGE_VERIFIED_DATE + " plus support-ticket evidence. No cloud "
        "resource was queried and nothing was changed. Branches labelled LOW "
        "CONFIDENCE must be relayed with that label.")
    report.next_action(
        "run --mode precheck with the customer's region and instance or disk "
        "scope to add the cloud-side facts behind the rule answer")


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def summarise(report: Report) -> str:
    """Plain-language checked / found / next-step sentence."""
    checked = {
        "precheck": "the instance, disk and environment facts that decide "
                    "whether a snapshot consistency group applies",
        "verify": "the snapshot records, their completion state and the "
                  "instance state behind the create-or-rollback question",
        "rules": "the capability-boundary rules for snapshot consistency "
                 "groups from the embedded official documentation wording",
    }[report.mode]
    found = (f"{len(report.findings)} evidence-based finding(s) and "
             f"{len(report.rule_answers)} documented rule answer(s)")
    if report.limitations:
        found += (f", plus {len(report.limitations)} limitation(s) on what "
                  f"read-only APIs cannot determine")
    return (f"Checked {checked}. Reported {found}. "
            f"Next step: {report.next}.")


def build_payload(report: Report, args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "skill": SKILL_NAME,
        "mode": report.mode,
        "knowledgeVerifiedOn": KNOWLEDGE_VERIFIED_DATE,
        "session": report.session,
        "inputs": {
            "regionId": args.region_id,
            "instanceId": args.instance_id,
            "diskIds": [d.strip() for d in (args.disk_ids or "").split(",")
                        if d.strip()],
            "environment": args.environment,
        },
        "accountUid": report.uid or None,
        "scopeNote": ("reads cover the current credential's account and the "
                      "given region only; cross-account and in-guest state "
                      "are out of reach"),
        "summary": summarise(report),
        "findings": report.findings,
        "ruleAnswers": report.rule_answers,
        "handoffs": report.handoffs,
        "evidence": report.evidence,
        "limitations": report.limitations,
        "permissions": {
            "readOnly": True,
            "actionsUsed": report.used_actions(),
            "reference": RAM_REFERENCE,
        },
        "errors": report.errors,
        "warnings": report.warnings,
        "status": report.status,
        "nextAction": report.next,
    }


def render_json(report: Report, args: argparse.Namespace) -> None:
    payload = build_payload(report, args)
    print(json.dumps(payload, indent=2))
    print(f"\nSTATUS: {payload['status']}")
    print(f"NEXT_ACTION: {payload['nextAction']}")


def render_text(report: Report, args: argparse.Namespace) -> None:
    bar = "=" * 78
    print(bar)
    print(f"ECS snapshot consistency group -- {report.mode} (read-only)")
    print(bar)
    print(f"  Region            : {args.region_id or 'n/a (rules mode)'}")
    print(f"  Instance / Disks  : {args.instance_id or '-'} / "
          f"{args.disk_ids or '-'}")
    print(f"  Environment       : {args.environment} (customer-declared)")
    print(f"  Account UID       : {report.uid or 'not resolved'}")
    print(f"  Session           : {report.session}")
    print(f"  Knowledge dated   : {KNOWLEDGE_VERIFIED_DATE}")
    print(bar)

    print("\nSummary\n-------")
    print(summarise(report))

    print("\nFindings\n--------")
    if report.findings:
        for line in report.findings:
            print(f"  * {line}")
    else:
        print("  (no finding available; see Limitations)")

    if report.rule_answers:
        print("\nDocumented rule answers\n---------------------")
        for answer in report.rule_answers:
            print(f"  [{answer['topic']}] confidence: {answer['confidence']}")
            print(f"  Q: {answer['question']}")
            print(f"  A: {answer['answer']}")
            for source in answer["sources"]:
                print(f"     source: {source}")
            print()

    if report.handoffs:
        print("Handoff - outside this skill's scope\n-------------------------------")
        for entry in report.handoffs:
            print(f"  - {entry['area']}")
            print(f"    {entry['response']}")
        print()

    print("Evidence - API reads performed\n------------------------------")
    if report.evidence:
        for item in report.evidence:
            params = ", ".join(f"{k}={v}" for k, v in item["params"].items())
            print(f"  - {item['product']}:{item['apiVersion']} "
                  f"{item['api']} [{params or 'no extra params'}]")
            print(f"    observed: {item['observation']}")
            if item["fieldsObserved"]:
                print(f"    fields:   {', '.join(item['fieldsObserved'])}")
    else:
        print("  (no API read performed)")

    print("\nRAM actions used\n--------------")
    used = ", ".join(report.used_actions()) or "none"
    print(f"  read-only: {used}")
    print(f"  full list and the minimal policy: {RAM_REFERENCE}")

    print("\nLimitations\n-----------")
    if report.limitations:
        for line in report.limitations:
            print(f"  ! {line}")
    else:
        print("  (none)")

    if report.errors:
        print("\nErrors\n------")
        for err in report.errors:
            print(f"  - {err['code']}: {err['message']}")

    print(f"\nSTATUS: {report.status}")
    print(f"NEXT_ACTION: {report.next}")


def render(report: Report, args: argparse.Namespace) -> None:
    if args.as_json:
        render_json(report, args)
    else:
        render_text(report, args)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def _run_selftest() -> int:
    """Offline boundary locks for the read-only gate and the pure classifiers.

    ``_ensure_read_only`` is the safety gate backing this skill's read-only
    claim: it must block every write action and any non-ECS product while
    allowing the whitelisted Describe* reads and the STS identity call. A wrong
    allow here would let the skill mutate customer state. ``disk_category_facts``
    decides ESSD-family membership (which gates crash-consistent group
    applicability) and must never guess an unknown category. ``snapshot_state_verdict``,
    ``_minute_key`` and ``score_topic`` are pure helpers. No cloud, no credentials.
    """
    rc = 0

    def expect(name, cond):
        nonlocal rc
        if cond:
            print("PASS {0}".format(name))
        else:
            print("FAIL {0}".format(name))
            rc = 1

    def ro_ok(product, action):
        try:
            _ensure_read_only(product, action)
            return True
        except RuntimeError:
            return False

    # --- _ensure_read_only: the read-only boundary
    expect("ro_allowed_describe", ro_ok("ecs", "DescribeDisks"))
    expect("ro_sts_identity_ok", ro_ok("sts", "GetCallerIdentity"))
    expect("ro_blocks_write_action", not ro_ok("ecs", "CreateSnapshot"))
    expect("ro_blocks_delete_action", not ro_ok("ecs", "DeleteDisk"))
    expect("ro_blocks_wrong_product", not ro_ok("oss", "DescribeDisks"))
    expect("ro_blocks_unknown_action", not ro_ok("ecs", "NotARealAction"))
    # universal invariant: every whitelisted action passes under the ecs product
    expect("ro_every_allowed_action_passes",
           all(ro_ok("ecs", a) for a in ALLOWED_ACTIONS))

    # --- snapshot_state_verdict: each documented state + unrecognised default
    expect("sv_accomplished", snapshot_state_verdict("accomplished", "100%").startswith("complete"))
    expect("sv_progressing_not_complete", "NOT complete" in snapshot_state_verdict("progressing", "45%"))
    expect("sv_failed", snapshot_state_verdict("failed", None).startswith("FAILED"))
    expect("sv_unrecognised_treat_unconfirmed",
           "not confirmed complete" in snapshot_state_verdict("bogus", "10"))
    expect("sv_case_and_space_tolerant",
           snapshot_state_verdict("  Accomplished  ", None).startswith("complete"))

    # --- _minute_key: normalise CreationTime to first 16 chars, None-safe
    expect("mk_with_seconds", _minute_key("2026-07-31T09:15:33Z") == "2026-07-31T09:15")
    expect("mk_no_seconds", _minute_key("2026-07-31T09:15Z") == "2026-07-31T09:15")
    expect("mk_none_empty", _minute_key(None) == "" and _minute_key("") == "")

    # --- disk_category_facts: ESSD-family split, unknown never guessed
    essd_cat = next(c for c, (_l, is_essd) in DISK_CATEGORY_NOTES.items() if is_essd)
    plain_cat = next(c for c, (_l, is_essd) in DISK_CATEGORY_NOTES.items() if not is_essd)
    rows, essd, non, unk = disk_category_facts([
        {"DiskId": "d-e", "Category": essd_cat},
        {"DiskId": "d-p", "Category": plain_cat},
        {"DiskId": "d-u", "Category": "totally-made-up"},
        {"DiskId": "d-blank", "Category": ""},
    ])
    expect("dcf_essd_split", essd == ["d-e"] and non == ["d-p"])
    expect("dcf_unknown_not_guessed", unk == ["d-u", "d-blank"])
    expect("dcf_essd_flag_none_for_unknown",
           next(r["essdFamily"] for r in rows if r["diskId"] == "d-u") is None)

    # --- score_topic: keyword hit count, case-insensitive, no false hits
    topic = {"keywords": ["rollback", "revert"]}
    expect("st_counts_hits", score_topic("need to ROLLBACK and revert", topic) == 2)
    expect("st_no_match_zero", score_topic("unrelated wording", topic) == 0)

    print("SELFTEST: {0}".format("PASS" if rc == 0 else "FAIL"))
    return rc


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _run_selftest()
    args = build_parser().parse_args(argv)
    report = Report(args.mode)
    validate_args(args, report)

    if not report.fatal and args.mode in ("precheck", "verify"):
        _cli.check_cli_available()
        attach_identity(report, args)
        try:
            if args.mode == "precheck":
                run_precheck(report, args)
            else:
                run_verify(report, args)
        except _cli.CliError as err:
            handle_cli_error(report, "DescribeSnapshots", {}, err)
        except RuntimeError as err:
            report.degraded = True
            report.error("ReadOnlyBoundary", str(err))
            print("[WARN] a request outside the read-only whitelist was "
                  "blocked; no change was and will be made", file=sys.stderr)
    elif not report.fatal:
        try:
            run_rules(report, args)
        except RuntimeError as err:
            report.error("ReadOnlyBoundary", str(err))

    render(report, args)
    return 0 if report.status in ("OK", "DEGRADED") else 1


if __name__ == "__main__":
    sys.exit(main())
