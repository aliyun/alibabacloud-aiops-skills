#!/usr/bin/env python3
"""
rollback_readiness.py -- Single entry point: snapshot rollback readiness,
restore-point evidence and confirmation-gated helpers
=====================================================
SECURITY: This script answers ONE question with evidence: can this disk be
rolled back to which snapshot, at what cost in data, and what must happen
first. It renders the rollback itself as MANUAL console steps only -- the
disk-rollback operation is NEVER invoked here (SKILL.md Absolute Rule 1).
State changes exist in exactly two gated modes and nowhere else:

  snapshot-backup  creates one billable snapshot of one named disk
                   (the snapshot-first fallback), only after the caller
                   repeats the confirmation flag;
  guest-check      dispatches exactly ONE command taken verbatim from the
                   frozen non-mutating whitelist in _constants.py, only
                   after the caller repeats the confirmation flag.

Every other mode is a query. Credentials are resolved exclusively by the
aliyun CLI default credential chain; nothing here reads, prints, caches or
forwards keys or tokens. Whitelist enforcement lives in _cli.require_allowed.

Modes:
  assess          eligibility preconditions + candidate restore points +
                  data-loss window + manual rollback steps pointer
  guest-check     gated dispatch of ONE whitelisted non-mutating command,
                  used before/after a rollback to compare what is actually
                  inside the disk (df / findmnt / ls / stat / lsof +L1,
                  Get-Volume / Get-PSDrive / Get-ChildItem)
  snapshot-backup gated pre-rollback fallback snapshot of one disk

Output contract (both text and --json):
  ... evidence sections ...
  STATUS: OK|DEGRADED|FAIL
  NEXT_ACTION: <the single next step>

Exit codes: 0 = OK or DEGRADED (usable conclusion), 1 = FAIL (missing input
or every evidence call failed), 2 = argparse usage error.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import _cli
from _constants import (
    BILLING_NOTICE,
    DEFAULT_TIMEOUT,
    DISK_ID_RE,
    GUEST_COMMAND_WHITELIST,
    INSTANCE_ID_RE,
    POLL_INTERVAL_SECONDS,
    POLL_MAX_ATTEMPTS,
    PROFILE_NAME_RE,
    REGION_ID_RE,
    RISK_STATEMENT,
    RUN_COMMAND_TYPE,
    SENSITIVE_INFO_FOOTNOTE,
    SNAPSHOT_ID_RE,
    SNAPSHOT_PROGRESS_GATE,
    VERDICT_ELIGIBLE,
    VERDICT_NEEDS,
    VERDICT_NO_SNAPSHOT,
    VERDICT_UNKNOWN,
    _GUEST_SHELL_CONTROL,
)

_ECS = "ecs"
_PERMISSION_MARKERS = ("nopermission", "implicitdeny", "accessdenied")


# ---------------------------------------------------------------------------
# Small pure helpers (unit-testable, no model involvement -- KB-04 principle)
# ---------------------------------------------------------------------------

def _matches(pattern: str, value: str) -> bool:
    return bool(re.match(pattern, value or ""))


def _parse_api_time(raw: str) -> datetime | None:
    """Parse the ISO-8601 UTC timestamps the ECS APIs return, e.g.
    '2026-08-27T02:00:00Z'. Returns None when unparseable (never guess)."""
    raw = (raw or "").strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_user_time(raw: str) -> datetime | None:
    """Parse a user-supplied date or datetime as UTC (customer incident
    times are stated in plain dates in tickets)."""
    raw = (raw or "").strip().replace(" ", "T")
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%MZ",
                "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _hours_text(start: datetime, end: datetime) -> str:
    total = (end - start).total_seconds()
    hours = total / 3600.0
    if hours < 0:
        return "n/a (snapshot timestamp is in the future; verify the region clock)"
    if hours < 48:
        return f"{hours:.1f} hours"
    return f"{hours / 24:.1f} days"


def _permission_hint(err: _cli.CliError, product: str, action: str) -> str:
    """Auth-failure wording: name the missing action + minimal policy
    pointer. Literal codes follow the tier vocabulary (NoPermission /
    ImplicitDeny); the other literal spelling is never used here."""
    code = (err.code or "").lower()
    if any(marker in code for marker in _PERMISSION_MARKERS):
        return (
            f"permission gap: the credential lacks the '{action}' action of "
            f"product '{product}' (returned {err.code}). Grant it per the "
            "minimal policy in references/ram-policies.md, then rerun the "
            "same command.")
    return ""


# ---------------------------------------------------------------------------
# Query wrappers: one evidence call each; failures degrade, never abort
# ---------------------------------------------------------------------------

class Evidence:
    """Collects queries, errors and the graceful-degradation log."""

    def __init__(self, region: str, profile: str | None):
        self.region = region
        self.profile = profile
        self.errors: list[dict] = []

    def _note(self, action: str, err: _cli.CliError) -> None:
        hint = _permission_hint(err, _ECS, action)
        self.errors.append({
            "action": action,
            "code": err.code or "Unknown",
            "message": str(err)[:300],
            "hint": hint,
        })
        line = f"[WARN] {_ECS} {action} failed: {err.code or ''}: {str(err)[:200]}"
        if hint:
            line += f"\n[WARN] {hint}"
        print(line, file=sys.stderr)

    def query(self, action: str, params: dict, items_path: list[str],
              label: str = "") -> list[dict]:
        try:
            items = _cli.paginate(_ECS, action, params, items_path,
                                  region=self.region, profile=self.profile)
            return items
        except _cli.CliError as e:
            self._note(action, e)
        return []

    def query_one(self, action: str, params: dict, label: str = "") -> dict:
        try:
            return _cli.call(_ECS, action, params,
                             region=self.region, profile=self.profile,
                             timeout=DEFAULT_TIMEOUT)
        except _cli.CliError as e:
            self._note(action, e)
        return {}


# ---------------------------------------------------------------------------
# assess mode
# ---------------------------------------------------------------------------

def _snapshot_usable(snap: dict, now: datetime) -> tuple[bool, list[str]]:
    """Pure precondition check P2-P4 for one snapshot entry."""
    reasons: list[str] = []
    status = str(snap.get("Status") or "").lower()
    progress = str(snap.get("Progress") or "").strip()
    if status and status != "accomplished":
        reasons.append(f"status={status}")
    if progress and progress != "100%":
        reasons.append(f"progress={progress}")
    if not reasons:
        created = _parse_api_time(str(snap.get("CreationTime") or ""))
        retention = snap.get("RetentionDays")
        if created and isinstance(retention, int) and retention > 0:
            expires = created + timedelta(days=retention)
            if now > expires:
                reasons.append(
                    f"beyond retention ({retention} days, expired "
                    f"{expires.date()})")
    usable = not reasons
    return usable, reasons


def _assess_disk(ev: Evidence, disk: dict, target_snapshot_id: str | None,
                 before: datetime | None, now: datetime,
                 instance_status: str | None = None) -> dict:
    """Build the per-disk verdict from real API entries only."""
    disk_id = str(disk.get("DiskId") or "")
    disk_type = str(disk.get("Type") or "")
    snaps = ev.query(
        "DescribeSnapshots",
        {"RegionId": ev.region, "DiskId": disk_id},
        ["Snapshots", "Snapshot"])

    candidates, excluded = [], []
    for snap in snaps:
        sid = str(snap.get("SnapshotId") or "")
        if target_snapshot_id and sid != target_snapshot_id:
            continue
        usable, reasons = _snapshot_usable(snap, now)
        created = _parse_api_time(str(snap.get("CreationTime") or ""))
        row = {
            "snapshot_id": sid,
            "name": str(snap.get("SnapshotName") or "(unnamed)"),
            "creation_time": str(snap.get("CreationTime") or "n/a"),
            "progress": str(snap.get("Progress") or "n/a"),
            "status": str(snap.get("Status") or "n/a"),
            "retention_days": snap.get("RetentionDays"),
            "source_disk_id": str(snap.get("SourceDiskId") or ""),
            "category": str(snap.get("Category") or "n/a"),
        }
        if usable and str(snap.get("SourceDiskId") or "") != disk_id:
            usable, reasons = False, ["not created from this disk"]
        if usable and before and created and created > before:
            reasons = list(reasons) + [
                "newer than the supplied --before point (excluded from the "
                "clean restore-point shortlist, still listed as candidate)"]
            row["newer_than_before"] = True
        if usable:
            candidates.append(row)
        else:
            row["excluded_reasons"] = reasons
            excluded.append(row)

    newest = None
    if candidates:
        newest = max(
            candidates,
            key=lambda r: _parse_api_time(r["creation_time"])
            or datetime.min.replace(tzinfo=timezone.utc))

    verdict = VERDICT_UNKNOWN
    actions: list[str] = []
    if not snaps and not any(e["action"] == "DescribeSnapshots"
                             for e in ev.errors):
        verdict = VERDICT_NO_SNAPSHOT
    elif candidates:
        needs_stop = (disk_type == "system"
                      and instance_status not in (None, "", "Stopped"))
        verdict = VERDICT_NEEDS if needs_stop else VERDICT_ELIGIBLE
        stop_note = (f" -- current instance state: {instance_status}"
                     if needs_stop else "")
        actions.append("instance must be stopped before the rollback "
                       "(manual step; this skill never stops it)" + stop_note)
    elif snaps:
        verdict = VERDICT_NO_SNAPSHOT
        actions.append("every listed snapshot of this disk failed the "
                       "preconditions (see excluded_snapshots); do NOT "
                       "attempt a rollback against them")

    loss_window = None
    if newest:
        created = _parse_api_time(newest["creation_time"])
        if created:
            loss_window = _hours_text(created, now)

    return {
        "disk_id": disk_id,
        "disk_name": str(disk.get("DiskName") or "(unnamed)"),
        "disk_type": disk_type or "n/a",
        "disk_status": str(disk.get("Status") or "n/a"),
        "size_gib": disk.get("Size"),
        "verdict": verdict,
        "actions_required": actions,
        "candidate_snapshots": candidates,
        "excluded_snapshots": excluded,
        "latest_usable_snapshot": newest,
        "data_loss_window_if_rolled_back_now": loss_window,
    }


def run_assess(args: argparse.Namespace) -> int:
    ev = Evidence(args.region_id, args.profile)
    before = _parse_user_time(args.before) if args.before else None
    if args.before and before is None:
        print("STATUS: FAIL")
        print("NEXT_ACTION: supply --before as YYYY-MM-DD or "
              "YYYY-MM-DDTHH:MM:SS (UTC); the value given could not be parsed")
        return 1
    now = datetime.now(timezone.utc)

    uid = _cli.resolve_account_id(profile=args.profile)

    instances: list[dict] = []
    if args.instance_id:
        instances = ev.query(
            "DescribeInstances",
            {"RegionId": ev.region, "InstanceIds": json.dumps([args.instance_id])},
            ["Instances", "Instance"])
    disks: list[dict] = []
    if args.disk_id:
        disks = ev.query(
            "DescribeDisks",
            {"RegionId": ev.region, "DiskIds": json.dumps([args.disk_id])},
            ["Disks", "Disk"])
    elif args.instance_id:
        disks = ev.query(
            "DescribeDisks",
            {"RegionId": ev.region, "InstanceId": args.instance_id},
            ["Disks", "Disk"])

    inst_status = str(instances[0].get("Status") or "") if instances else None
    per_disk = [_assess_disk(ev, d, args.snapshot_id, before, now, inst_status)
                for d in disks]

    # Cross-check a user-named snapshot against the enumerated disks so the
    # "snapshot belongs to the target disk" precondition holds even when the
    # user only knows the snapshot id.
    orphan_note = None
    if args.snapshot_id and per_disk and not any(
            c["snapshot_id"] == args.snapshot_id
            for d in per_disk for c in d["candidate_snapshots"]):
        orphan_note = (
            f"the named snapshot {args.snapshot_id} is not among the usable "
            "snapshots of the queried disk(s); verify its source disk before "
            "planning any rollback")

    query_failed = bool(ev.errors)
    if not disks and not query_failed:
        status = "FAIL" if not args.disk_id and not args.instance_id else "DEGRADED"
    elif query_failed:
        status = "DEGRADED"
    else:
        status = "OK"

    instance_state = None
    if instances:
        instance_state = {
            "instance_id": str(instances[0].get("InstanceId") or ""),
            "status": str(instances[0].get("Status") or "n/a"),
            "instance_network_type": str(
                instances[0].get("InstanceNetworkType") or "n/a"),
        }
    elif args.instance_id and not any(
            e["action"] == "DescribeInstances" for e in ev.errors):
        instance_state = {
            "instance_id": args.instance_id,
            "status": "NOT_VISIBLE",
            "note": ("the instance is not visible in this region under this "
                     "account: released instances lose their disks and "
                     "snapshots marked for release -- see "
                     "references/recovery-boundaries.md"),
        }

    report = {
        "mode": "assess",
        "region_id": args.region_id,
        "auto_filled": {
            "account_uid": uid or "(unavailable)",
            "uid_source": "sts caller-identity" if uid else "n/a",
            "evaluation_time_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "instance": instance_state,
        "preconditions": [
            {"id": pid, "text": text} for pid, text in _PRECONDITION_TUPLES],
        "per_disk": per_disk,
        "snapshot_id_cross_check": orphan_note,
        "risk_statement": RISK_STATEMENT,
        "progress_gate": SNAPSHOT_PROGRESS_GATE,
        "manual_steps_doc": "references/rollback-entry-steps.md",
        "errors": ev.errors,
    }

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        _render_assess(report)

    eligible = any(d["verdict"] == VERDICT_ELIGIBLE for d in per_disk)
    if status == "FAIL":
        print("STATUS: FAIL")
        print("NEXT_ACTION: provide the target RegionId plus an InstanceId "
              "or DiskId that is visible to the current credential, then "
              "rerun assess")
        return 1
    print(f"STATUS: {status}")
    if eligible or any(d["verdict"] == VERDICT_NEEDS for d in per_disk):
        print("NEXT_ACTION: relay the two risk points and the manual "
              "console steps from references/rollback-entry-steps.md; a "
              "NEEDS_ACTION verdict means the user must stop the instance "
              "first (manual) and assess should then be rerun; before "
              "guiding the rollback, offer the gated snapshot-backup of "
              "the current state (announce scope, impact and billing, "
              "then obtain confirmation)")
    elif any(d["verdict"] == VERDICT_NO_SNAPSHOT for d in per_disk):
        print("NEXT_ACTION: relay the evidence-based not-recoverable "
              "finding from references/recovery-boundaries.md (no usable "
              "snapshot for the target disk) plus the alternative-backup "
              "checklist; never promise platform-side recovery")
    else:
        print("NEXT_ACTION: complete the evidence gaps above (retry the "
              "failed queries or ask the user to confirm region/account), "
              "then rerun assess")
    return 0


_PRECONDITION_TUPLES = [
    ("P1", "target disk exists and is visible in the queried region/account"),
    ("P2", "a candidate snapshot of that exact disk exists (SourceDiskId match)"),
    ("P3", "candidate snapshot progress is 100% (status accomplished)"),
    ("P4", "candidate snapshot is within its retention period"),
    ("P5", "instance state allows rollback (system-disk rollback requires "
           "the instance stopped; stopping itself is a manual action)"),
]


def _render_assess(report: dict) -> None:
    print("=" * 72)
    print(" ECS snapshot rollback readiness assessment")
    print("=" * 72)
    af = report["auto_filled"]
    print(f" Region              : {report['region_id']}")
    print(f" Account UID         : {af['account_uid']} (auto-filled via "
          f"{af['uid_source']}; traceability label only)")
    print(f" Evaluated (UTC)     : {af['evaluation_time_utc']}")
    inst = report["instance"]
    if inst:
        print(f" Instance            : {inst['instance_id']}  state={inst['status']}")
        if inst.get("note"):
            print(f"                       {inst['note']}")
    if not report["per_disk"]:
        print(" Disks               : none visible for the given inputs")
    for d in report["per_disk"]:
        print("-" * 72)
        print(f" Disk {d['disk_id']} [{d['disk_type']}] name={d['disk_name']} "
              f"state={d['disk_status']} size={d['size_gib']}GiB")
        print(f"   VERDICT           : {d['verdict']}")
        for act in d["actions_required"]:
            print(f"   ACTION REQUIRED   : {act}")
        if d["candidate_snapshots"]:
            print(f"   Usable snapshots  : {len(d['candidate_snapshots'])} "
                  "(most recent first)")
            for c in sorted(d["candidate_snapshots"],
                            key=lambda r: r["creation_time"], reverse=True)[:10]:
                extra = " [newer than --before]" if c.get("newer_than_before") else ""
                print(f"     - {c['snapshot_id']} created {c['creation_time']} "
                      f"progress={c['progress']} retention={c['retention_days']}{extra}")
            if d["latest_usable_snapshot"]:
                lu = d["latest_usable_snapshot"]
                print(f"   Data-loss window  : rolling back NOW to "
                      f"{lu['snapshot_id']} permanently loses everything "
                      f"written in the last {d['data_loss_window_if_rolled_back_now']}")
        for c in d["excluded_snapshots"]:
            print(f"   Excluded          : {c['snapshot_id']} "
                  f"({'; '.join(c['excluded_reasons'])})")
    if report["snapshot_id_cross_check"]:
        print("-" * 72)
        print(f" NOTE: {report['snapshot_id_cross_check']}")
    print("-" * 72)
    print(" MANDATORY RISK STATEMENT (relay both points verbatim before any")
    print(" rollback guidance -- the rollback itself is manual, forever):")
    for i, point in enumerate(report["risk_statement"], 1):
        print(f"   {i}. {point}")
    print(f" {report['progress_gate']}")
    print(" Manual console steps: see references/rollback-entry-steps.md")
    if report["errors"]:
        print("-" * 72)
        print(" Graceful degradation log:")
        for e in report["errors"]:
            print(f"   [WARN] ecs {e['action']}: {e['code']}"
                  + (f" -- {e['hint']}" if e["hint"] else ""))
    print(f" Footnote: {SENSITIVE_INFO_FOOTNOTE}")


# ---------------------------------------------------------------------------
# guest-check mode (gated: one whitelisted non-mutating command)
# ---------------------------------------------------------------------------

def check_guest_command(os_type: str, command: str) -> tuple[bool, str]:
    """Pure whitelist validator. Returns (ok, reason)."""
    patterns = GUEST_COMMAND_WHITELIST.get(os_type)
    if patterns is None:
        return False, f"unknown os-type '{os_type}' (expected linux or windows)"
    if not command or not command.strip():
        return False, "empty command"
    if command != command.strip():
        return False, "leading/trailing whitespace is not accepted"
    for ch in _GUEST_SHELL_CONTROL:
        if ch in command:
            return False, ("the command contains a shell control character; "
                           "only single whitelisted statements are accepted")
    for pat in patterns:
        if re.fullmatch(pat, command):
            return True, f"matched whitelisted pattern {pat}"
    return False, ("command is not on the frozen observation whitelist in "
                   "scripts/_constants.py; refused. Never assemble a custom "
                   "command; see references/guest-observation-catalog.md")


def _decode_invocation_output(raw: str) -> str:
    """Cloud Assistant returns the command output as text; decode base64
    when present, otherwise relay verbatim (never invent content)."""
    if not raw:
        return ""
    try:
        decoded = base64.b64decode(raw, validate=True).decode("utf-8", "replace")
        return decoded
    except Exception:
        return raw


def run_guest_check(args: argparse.Namespace) -> int:
    ok, reason = check_guest_command(args.os_type, args.command)
    if not ok:
        print(f"[REFUSED] {reason}", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: pick a command from "
              "references/guest-observation-catalog.md and rerun "
              "guest-check with the exact whitelisted string")
        return 1

    if args.confirm != "yes":
        # Announce-then-confirm gate: without the explicit confirmation flag
        # nothing is dispatched. This is the mandatory pre-execution step.
        print("=" * 72)
        print(" PENDING CONFIRMATION (nothing has been executed)")
        print("=" * 72)
        print(f" Instance   : {args.instance_id} ({args.region_id})")
        print(f" OS family  : {args.os_type}")
        print(f" Command    : {args.command}")
        print(" Nature     : observation-only listing; the command changes "
              "nothing on the disk and writes no data")
        print(" Effect     : one Cloud Assistant invocation record appears "
              "on the instance; its stdout is returned here")
        print(" Reversibility: nothing to reverse (no state change beyond "
              "the invocation record)")
        print(" Approval covers exactly this one command at this one time.")
        print("STATUS: FAIL")
        print("NEXT_ACTION: relay the announcement above to the user; after "
              "they approve this exact command, rerun with --confirm yes")
        return 1

    ev = Evidence(args.region_id, args.profile)
    # Audit trail: the announcement is echoed even on the confirmed path.
    print(f"[GATE] confirmed dispatch: instance {args.instance_id} "
          f"({args.region_id}, {args.os_type}), observation-only command "
          f"'{args.command}'; user approval for this exact command was "
          "relayed by the agent (per-call, non-transferable)")
    status_rows = ev.query(
        "DescribeCloudAssistantStatus",
        {"RegionId": args.region_id, "InstanceId.1": args.instance_id},
        ["InstanceCloudAssistantStatusSet", "InstanceCloudAssistantStatus"])
    ready = None
    for row in status_rows:
        if str(row.get("InstanceId") or "") == args.instance_id:
            ready = str(row.get("CloudAssistantStatus") or "").lower() == "true"
    if ready is None and not any(e["action"] == "DescribeCloudAssistantStatus"
                                 for e in ev.errors):
        ready = False
    if ready is False:
        print("[WARN] Cloud Assistant is not answering on this instance; "
              "the gated command was NOT dispatched", file=sys.stderr)
        print("STATUS: DEGRADED")
        print("NEXT_ACTION: fall back to asking the customer to run the "
              "command manually and paste the output (Workbench console or "
              "VNC); see the degradation branch in "
              "references/guest-observation-catalog.md")
        return 0

    try:
        body = _cli.call(
            _ECS, "RunCommand",
            {
                "RegionId": args.region_id,
                "Type": RUN_COMMAND_TYPE[args.os_type],
                "CommandContent": args.command,
                "Name": "rollback-guide-obs",
                "Description": "observation-only check, confirmation-gated",
                "Timeout": 60,
                "InstanceId.1": args.instance_id,
                # idempotency token for this single logical dispatch
                "ClientToken": uuid.uuid4().hex,
            },
            region=args.region_id, profile=args.profile,
            timeout=DEFAULT_TIMEOUT, retryable=False)
    except _cli.CliError as e:
        hint = _permission_hint(e, _ECS, "RunCommand")
        print(f"[WARN] dispatch failed: {e.code or ''}: {str(e)[:200]}",
              file=sys.stderr)
        if hint:
            print(f"[WARN] {hint}", file=sys.stderr)
        print("STATUS: DEGRADED")
        print("NEXT_ACTION: fall back to the customer-pasted-output path; if "
              "this was a permission gap, grant the action per "
              "references/ram-policies.md and retry once")
        return 0

    invoke_id = str(body.get("InvokeId") or "")
    output, invocation_status = _poll_invocation(ev, invoke_id, args)
    print("=" * 72)
    print(f" Guest observation: {args.instance_id} ({args.os_type})")
    print("=" * 72)
    print(f" Command   : {args.command}")
    print(f" InvokeId  : {invoke_id or 'n/a'}")
    print(f" Invocation: {invocation_status or 'unknown'}")
    print(" Output (verbatim):")
    print(output if output.strip() else "(empty output)")
    if ev.errors:
        print(" Graceful degradation log:")
        for err in ev.errors:
            print(f"   [WARN] ecs {err['action']}: {err['code']}")
    print("\nSTATUS: OK" if output.strip() or invocation_status == "Success"
          else "\nSTATUS: DEGRADED")
    print("NEXT_ACTION: compare these readings against the pre-rollback "
          "snapshot of the same command to judge the rollback effect; "
          "service state (self-start, listeners) is NOT covered by this "
          "whitelist -- output the manual checklist instead")
    return 0


def _poll_invocation(ev: Evidence, invoke_id: str,
                     args: argparse.Namespace) -> tuple[str, str]:
    """Poll DescribeInvocations for the dispatched command's result.
    Returns (output_text, invocation_status)."""
    if not invoke_id:
        return "", "unknown"
    for _ in range(POLL_MAX_ATTEMPTS):
        body = ev.query_one("DescribeInvocations", {
            "RegionId": args.region_id,
            "InvokeId": invoke_id,
            "IncludeOutput": "true",
        })
        invs = _cli_dig(body, ["Invocations", "Invocation"])
        if invs:
            inv = invs[0]
            states = _cli_dig(inv, ["InvokeInstances", "InvokeInstance"])
            state = str(inv.get("InvocationStatus") or "")
            raw = ""
            # Never read a sibling instance's output: an invokeId can carry
            # several InvokeInstance entries, so the entry is matched by the
            # dispatched instance id first and falls back to the
            # invocation-level state only when no entry matches.
            target = str(getattr(args, "instance_id", "") or "")
            chosen = None
            for st in states:
                if str(st.get("InstanceId") or "") == target:
                    chosen = st
                    break
            if chosen is None and len(states) == 1:
                chosen = states[0]
            if chosen is not None:
                state = str(chosen.get("InvocationStatus") or state)
                raw = str(chosen.get("Output") or "")
            if state in ("Running", "Pending", "Scheduled", "Stopping", ""):
                time.sleep(POLL_INTERVAL_SECONDS)
                continue
            return _decode_invocation_output(raw), state
        time.sleep(POLL_INTERVAL_SECONDS)
    return "", "Timeout-waiting-for-result"


def _cli_dig(obj, path):
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return []
        node = node.get(key)
    if isinstance(node, dict):
        node = node.get("Item") if "Item" in node else []
    return node if isinstance(node, list) else []


# ---------------------------------------------------------------------------
# snapshot-backup mode (gated: one billable snapshot, snapshot-first)
# ---------------------------------------------------------------------------

def run_snapshot_backup(args: argparse.Namespace) -> int:
    if args.confirm != "yes":
        print("=" * 72)
        print(" PENDING CONFIRMATION (nothing has been created)")
        print("=" * 72)
        print(f" Disk       : {args.disk_id} ({args.region_id})")
        print(" What runs  : one snapshot of this disk's CURRENT state")
        print(" Impact     : a new billable snapshot appears; "
              + BILLING_NOTICE)
        print(" Reversibility: purely additive -- the disk itself is not "
              "touched; the snapshot can be deleted manually later")
        print(" Approval covers exactly this one snapshot of this one disk.")
        print("STATUS: FAIL")
        print("NEXT_ACTION: relay the announcement above (including the "
              "billing note) to the user; after they approve, rerun with "
              "--confirm yes")
        return 1

    ev = Evidence(args.region_id, args.profile)
    # Audit trail: the announcement is echoed even on the confirmed path.
    print(f"[GATE] confirmed create: one pre-rollback fallback snapshot of "
          f"disk {args.disk_id} in {args.region_id}; billable; additive, the "
          "disk itself is untouched; user approval (with the billing note "
          "relayed) confirmed by the agent (per-call, non-transferable)")
    disks = ev.query("DescribeDisks",
                     {"RegionId": args.region_id,
                      "DiskIds": json.dumps([args.disk_id])},
                     ["Disks", "Disk"])
    if not disks and not any(e["action"] == "DescribeDisks" for e in ev.errors):
        print("STATUS: FAIL")
        print(f"NEXT_ACTION: disk {args.disk_id} is not visible in "
              f"{args.region_id} under this account; verify the region and "
              "disk id, then rerun")
        return 1

    try:
        # Params kept to the api-info-verified minimum for this action:
        # RegionId + DiskId. Single attempt: a duplicated fallback snapshot
        # would double the billing surprise, so transient failures are NOT
        # retried blindly -- the state is verified before any rerun.
        body = _cli.call(
            _ECS, "CreateSnapshot",
            {"RegionId": args.region_id, "DiskId": args.disk_id},
            region=args.region_id, profile=args.profile,
            timeout=DEFAULT_TIMEOUT, retryable=False)
    except _cli.CliError as e:
        hint = _permission_hint(e, _ECS, "CreateSnapshot")
        print(f"[WARN] snapshot creation failed: {e.code or ''}: "
              f"{str(e)[:200]}", file=sys.stderr)
        if hint:
            print(f"[WARN] {hint}", file=sys.stderr)
        print("STATUS: DEGRADED")
        print("NEXT_ACTION: run assess first to see whether the snapshot was "
              "in fact created (a timeout can still have succeeded); rerun "
              "snapshot-backup only if it is absent, and if this was a "
              "permission gap grant the action per references/ram-policies.md; "
              "otherwise create the fallback snapshot manually in the console "
              "before any rollback guidance continues")
        return 0

    snapshot_id = str(body.get("SnapshotId") or "")
    print("=" * 72)
    print(" Pre-rollback fallback snapshot")
    print("=" * 72)
    print(f" Disk        : {args.disk_id}")
    print(f" SnapshotId  : {snapshot_id or 'n/a'}")
    print(f" Billing     : {BILLING_NOTICE}")

    progress = "n/a"
    if snapshot_id:
        progress = _wait_snapshot_progress(ev, snapshot_id)
    print(f" Progress    : {progress}")
    print(" Reminder    : " + SNAPSHOT_PROGRESS_GATE)
    if ev.errors:
        for err in ev.errors:
            print(f"   [WARN] ecs {err['action']}: {err['code']}")
    if progress == "100%":
        print("\nSTATUS: OK")
        print("NEXT_ACTION: the current-state fallback exists at 100%; "
              "continue with the manual rollback steps in "
              "references/rollback-entry-steps.md")
    else:
        print("\nSTATUS: DEGRADED")
        print("NEXT_ACTION: wait for the snapshot to reach 100% (rerun "
              "assess or poll in the console) before guiding any rollback")
    return 0


def _wait_snapshot_progress(ev: Evidence, snapshot_id: str) -> str:
    for _ in range(POLL_MAX_ATTEMPTS):
        snaps = ev.query("DescribeSnapshots",
                         {"RegionId": ev.region,
                          "SnapshotIds": json.dumps([snapshot_id])},
                         ["Snapshots", "Snapshot"])
        for s in snaps:
            if str(s.get("SnapshotId") or "") == snapshot_id:
                progress = str(s.get("Progress") or "").strip()
                status = str(s.get("Status") or "")
                if progress == "100%" or status == "accomplished":
                    return "100%"
        time.sleep(POLL_INTERVAL_SECONDS)
    return "still progressing (poll ceiling reached; verify again in the console)"


# ---------------------------------------------------------------------------
# argparse entry
# ---------------------------------------------------------------------------

def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--region-id", required=True,
                        help="Alibaba Cloud region id, e.g. cn-hangzhou")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return _run_selftest()
    parser = argparse.ArgumentParser(
        prog="rollback_readiness.py",
        description="ECS snapshot rollback readiness, gated observation and "
                    "gated pre-rollback backup (single entry point)")
    sub = parser.add_subparsers(dest="mode", required=True)

    p_assess = sub.add_parser("assess", help="eligibility + evidence (queries only)")
    _common(p_assess)
    p_assess.add_argument("--instance-id", default=None)
    p_assess.add_argument("--disk-id", default=None)
    p_assess.add_argument("--snapshot-id", default=None,
                          help="evaluate one user-named target snapshot")
    p_assess.add_argument("--before", default=None,
                          help="UTC date/datetime; snapshots newer than this "
                               "are flagged for clean-restore-point selection")

    p_guest = sub.add_parser("guest-check",
                             help="gated dispatch of ONE whitelisted "
                                  "non-mutating observation command")
    _common(p_guest)
    p_guest.add_argument("--instance-id", required=True)
    p_guest.add_argument("--command", required=True)
    p_guest.add_argument("--os-type", default="linux", choices=["linux", "windows"])
    p_guest.add_argument("--confirm", default=None,
                         help="must be 'yes' AND only after the user "
                              "approved this exact command (per-call)")

    p_snap = sub.add_parser("snapshot-backup",
                            help="gated creation of one pre-rollback "
                                 "fallback snapshot")
    _common(p_snap)
    p_snap.add_argument("--disk-id", required=True)
    p_snap.add_argument("--confirm", default=None,
                        help="must be 'yes' AND only after the user approved "
                             "this exact disk, billing note relayed (per-call)")

    args = parser.parse_args()

    _cli.check_cli_available()

    if not _matches(REGION_ID_RE, args.region_id):
        print(f"[ERROR] invalid region id: {args.region_id!r}", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: rerun with the exact region id (e.g. cn-hangzhou)")
        return 1
    if args.profile and not _matches(PROFILE_NAME_RE, args.profile):
        print("[ERROR] invalid profile name", file=sys.stderr)
        return 1
    for field, regex, label in (
            ("instance_id", INSTANCE_ID_RE, "instance id"),
            ("disk_id", DISK_ID_RE, "disk id"),
            ("snapshot_id", SNAPSHOT_ID_RE, "snapshot id")):
        value = getattr(args, field, None)
        if value and not _matches(regex, value):
            print(f"[ERROR] invalid {label}: {value!r}", file=sys.stderr)
            print("STATUS: FAIL")
            print(f"NEXT_ACTION: rerun with a well-formed {label}")
            return 1

    if args.mode == "assess":
        return run_assess(args)
    if args.mode == "guest-check":
        return run_guest_check(args)
    return run_snapshot_backup(args)


# ---------------------------------------------------------------------------
# Offline regression lock (no cloud, no subprocess): run with
#   python3 scripts/rollback_readiness.py --selftest
# Protects the rollback-readiness decision core: a wrong verdict or a wrong
# restore point is permanent data loss for the customer. Invariants locked:
#   * every exclusion is evidence-based and fail-closed (a failed query must
#     never be reported as NO_USABLE_SNAPSHOT);
#   * the guest command gate accepts only frozen whitelisted single statements
#     (it fronts one real RunCommand inside the customer's instance);
#   * poll output is matched per instance id -- a sibling instance's output is
#     never relayed as the target's (fixed this round, anti-regression below);
#   * user-supplied --before instants parse without forcing full seconds.
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

    import argparse as _ap
    import base64 as _b64

    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)

    def snap(**kw):
        s = {"SnapshotId": "s-1", "Status": "accomplished", "Progress": "100%",
             "CreationTime": "2026-09-01T02:00:00Z", "SourceDiskId": "d-abc"}
        s.update(kw)
        return s

    class FakeEv:
        region = "cn-hangzhou"

        def __init__(self, snaps=None, errors=None):
            self.snaps = snaps or []
            self.errors = errors or []

        def query(self, action, params, items_path, label=""):
            return self.snaps

    sys_disk = {"DiskId": "d-abc", "Type": "system", "Status": "In_use",
                "Size": 40}
    data_disk = {"DiskId": "d-abc", "Type": "data", "Status": "In_use",
                 "Size": 100}

    # --- time parsing ------------------------------------------------------
    expect("ut_date", _parse_user_time("2026-09-01")
           == datetime(2026, 9, 1, tzinfo=timezone.utc))
    expect("ut_full_secs", _parse_user_time("2026-08-20T10:30:45")
           == datetime(2026, 8, 20, 10, 30, 45, tzinfo=timezone.utc))
    expect("ut_minute_instant", _parse_user_time("2026-08-20T10:30")
           == datetime(2026, 8, 20, 10, 30, tzinfo=timezone.utc))
    expect("ut_space_form", _parse_user_time("2026-08-20 10:30")
           == datetime(2026, 8, 20, 10, 30, tzinfo=timezone.utc))
    expect("ut_junk_none", _parse_user_time("last tuesday") is None)
    expect("api_time_z", _parse_api_time("2026-08-27T02:00:00Z")
           == datetime(2026, 8, 27, 2, tzinfo=timezone.utc))
    expect("api_time_junk_none", _parse_api_time("n/a") is None)
    expect("hours_negative_future", "in the future" in
           _hours_text(now, now - timedelta(hours=3)))
    expect("hours_days_unit", _hours_text(now - timedelta(hours=60), now)
           == "2.5 days")

    # --- _snapshot_usable (P2-P4 preconditions) ----------------------------
    ok, why = _snapshot_usable(snap(), now)
    expect("usable_normal", ok and why == [])
    ok, why = _snapshot_usable(snap(Status="progressing", Progress="45%"), now)
    expect("usable_progressing", not ok
           and "status=progressing" in why and "progress=45%" in why)
    ok, why = _snapshot_usable(
        snap(CreationTime="2026-08-01T00:00:00Z", RetentionDays=7), now)
    expect("usable_retention_expired", not ok
           and any(r.startswith("beyond retention") for r in why))
    ok, why = _snapshot_usable(
        snap(CreationTime="2026-09-20T00:00:00Z", RetentionDays=7), now)
    expect("usable_retention_open", ok)
    ok, why = _snapshot_usable(snap(Progress=""), now)
    expect("usable_blank_progress", ok)  # flash snapshots carry no Progress

    # --- _assess_disk verdicts (fail-closed decision core) -----------------
    r = _assess_disk(FakeEv([snap()]), sys_disk, None, None, now, "Running")
    expect("verdict_system_running_needs", r["verdict"] == VERDICT_NEEDS)
    r = _assess_disk(FakeEv([snap()]), sys_disk, None, None, now, "Stopped")
    expect("verdict_system_stopped_eligible",
           r["verdict"] == VERDICT_ELIGIBLE)
    r = _assess_disk(FakeEv([snap()]), data_disk, None, None, now, "Running")
    expect("verdict_data_running_eligible",
           r["verdict"] == VERDICT_ELIGIBLE)
    r = _assess_disk(FakeEv([]), sys_disk, None, None, now, "Running")
    expect("verdict_no_snapshot", r["verdict"] == VERDICT_NO_SNAPSHOT)
    r = _assess_disk(FakeEv([], errors=[{"action": "DescribeSnapshots",
                                         "code": "Forbidden"}]),
                     sys_disk, None, None, now, "Running")
    expect("verdict_query_fail_is_not_no_snapshot",
           r["verdict"] == VERDICT_UNKNOWN)
    r = _assess_disk(FakeEv([snap(Status="progressing", Progress="10%")]),
                     sys_disk, None, None, now, "Running")
    expect("verdict_all_excluded_warns_do_not",
           r["verdict"] == VERDICT_NO_SNAPSHOT
           and any("do NOT" in a for a in r["actions_required"]))
    r = _assess_disk(FakeEv([snap(SourceDiskId="d-other")]),
                     sys_disk, None, None, now, "Running")
    expect("cross_disk_excluded",
           r["excluded_snapshots"][0]["excluded_reasons"]
           == ["not created from this disk"])
    r = _assess_disk(FakeEv([snap(SnapshotId="s-keep"),
                             snap(SnapshotId="s-skip")]),
                     sys_disk, "s-keep", None, now, "Running")
    expect("target_filter",
           [c["snapshot_id"] for c in r["candidate_snapshots"]] == ["s-keep"])
    r = _assess_disk(FakeEv([snap()]), sys_disk, None,
                     datetime(2026, 8, 1, tzinfo=timezone.utc), now,
                     "Running")
    expect("before_marks_not_excludes",
           r["candidate_snapshots"][0].get("newer_than_before") is True
           and r["verdict"] in (VERDICT_ELIGIBLE, VERDICT_NEEDS))
    r = _assess_disk(FakeEv([snap(SnapshotId="s-old"),
                             snap(SnapshotId="s-new",
                                  CreationTime="2026-09-20T12:00:00Z")]),
                     data_disk, None, None, now, "Running")
    expect("newest_and_loss_window",
           r["latest_usable_snapshot"]["snapshot_id"] == "s-new"
           and r["data_loss_window_if_rolled_back_now"] == "2.0 days")

    # --- check_guest_command (execution gate in front of RunCommand) -------
    for good in ("df -h", "df -hT", "findmnt", "findmnt /data",
                 "ls /srv/app", "stat -f /data", "lsof +L1"):
        expect("gate_accept_" + good.replace(" ", "_").replace("/", ""),
               check_guest_command("linux", good)[0])
    for bad in ("ls /etc; rm -rf /", "rm -rf /tmp", "df -h && reboot",
                 "ls /etc | wc -l", "`id`", "$(id)", "df -h > /tmp/x",
                 " ls /data", "ls  /data", "LS /DATA", ""):
        ok, _ = check_guest_command("linux", bad)
        expect("gate_refuse_" + (bad.strip() or "empty").replace(" ", "_")[:24],
               not ok)
    expect("gate_windows_accept",
           check_guest_command("windows", "Get-Volume")[0])
    expect("gate_windows_backtick",
           not check_guest_command("windows", "Get-Volume`; Invoke-WebRequest")[0])
    expect("gate_unknown_os", not check_guest_command("macos", "df -h")[0])
    # security invariant: nothing accepted carries a shell control character
    inv_ok = True
    for probe in ("df -h", "ls /srv", "findmnt /data", "Get-Volume",
                  "rm -rf /", "a; b", "a && b", "a|b", "a>b", "$(x)", "`x`",
                  "a\nb", "a\\b"):
        for fam in ("linux", "windows"):
            if check_guest_command(fam, probe)[0] \
                    and any(c in probe for c in _GUEST_SHELL_CONTROL):
                inv_ok = False
    expect("invariant_accept_implies_no_control_char", inv_ok)

    # --- _cli_dig / _decode_invocation_output ------------------------------
    expect("dig_nested_list",
           _cli_dig({"Snapshots": {"Snapshot": [{"a": 1}]}},
                    ["Snapshots", "Snapshot"]) == [{"a": 1}])
    expect("dig_missing_empty", _cli_dig({}, ["Snapshots", "Snapshot"]) == [])
    expect("dig_non_list_empty", _cli_dig({"a": {"b": "s"}}, ["a", "b"]) == [])
    expect("decode_b64", _decode_invocation_output(
        _b64.b64encode("Filesystem /dev/vda1".encode()).decode())
        == "Filesystem /dev/vda1")
    expect("decode_verbatim", _decode_invocation_output("plain output")
        == "plain output")
    expect("decode_empty", _decode_invocation_output("") == "")

    # --- _poll_invocation: per-instance output attribution -----------------
    out_wrong = _b64.b64encode(b"output-of-WRONG-instance").decode()
    out_right = _b64.b64encode(b"Filesystem /dev/vda1 40G").decode()

    class PollEv:
        region = "cn-hangzhou"
        errors: list = []

        def __init__(self, body):
            self.body = body

        def query_one(self, action, params, label=""):
            return self.body

    multi = {"Invocations": {"Invocation": [{
        "InvokeId": "t-x", "InvocationStatus": "Success",
        "InvokeInstances": {"InvokeInstance": [
            {"InstanceId": "i-other", "InvocationStatus": "Success",
             "Output": out_wrong},
            {"InstanceId": "i-target", "InvocationStatus": "Success",
             "Output": out_right},
            {"InstanceId": "i-third", "InvocationStatus": "Failed",
             "Output": out_wrong}]}}]}}
    real_sleep = time.sleep
    time.sleep = lambda _s: None
    try:
        text, st = _poll_invocation(
            PollEv(multi), "t-x",
            _ap.Namespace(region_id="cn-hangzhou", instance_id="i-target"))
        expect("poll_reads_the_target_not_the_first",
               text == "Filesystem /dev/vda1 40G")
        single = {"Invocations": {"Invocation": [{
            "InvocationStatus": "Success",
            "InvokeInstances": {"InvokeInstance": [
                {"InstanceId": "i-only", "InvocationStatus": "Success",
                 "Output": out_right}]}}]}}
        text2, _ = _poll_invocation(
            PollEv(single), "t-y",
            _ap.Namespace(region_id="cn-hangzhou", instance_id="i-mismatch"))
        expect("poll_single_entry_fallback", text2 == "Filesystem /dev/vda1 40G")
        text3, st3 = _poll_invocation(
            PollEv(multi), "t-z",
            _ap.Namespace(region_id="cn-hangzhou", instance_id="i-none"))
        expect("poll_no_match_never_relays_sibling_output",
               text3 == "" and st3 == "Success")
        run = {"Invocations": {"Invocation": [{
            "InvocationStatus": "Running",
            "InvokeInstances": {"InvokeInstance": [
                {"InstanceId": "i-target", "InvocationStatus": "Running",
                 "Output": ""}]}}]}}
        text4, st4 = _poll_invocation(
            PollEv(run), "t-w",
            _ap.Namespace(region_id="cn-hangzhou", instance_id="i-target"))
        expect("poll_running_keeps_polling_until_ceiling",
               text4 == "" and st4 == "Timeout-waiting-for-result")
    finally:
        time.sleep = real_sleep

    # --- _permission_hint ---------------------------------------------------
    err_perm = _cli.CliError("denied", code="Forbidden.NoPermission")
    hint = _permission_hint(err_perm, "ecs", "DescribeSnapshots")
    expect("hint_permission_names_action",
           "DescribeSnapshots" in hint and "ram-policies.md" in hint)
    expect("hint_other_error_empty",
           _permission_hint(_cli.CliError("throttled", code="Throttling"),
                            "ecs", "X") == "")

    print(f"--selftest: {len(checked)} checks, "
          f"{'ALL PASS' if rc == 0 else 'FAILURES PRESENT'}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
