#!/usr/bin/env python3
"""
ecs_start_stop_diagnosis.py -- single entry point of the skill
================================================================
SECURITY / EXECUTION MODEL (enforced in code, not only in prose):

* Layer 1 -- automatic cloud evidence queries: Describe*/Get* actions only
  (identity, instance state machine, health + system events, disk
  inventory, snapshot inventory, CloudMonitor readings).
* Layer 2 -- gated in-guest check: dispatches EXACTLY ONE command from the
  frozen whitelist in _constants.GUEST_COMMANDS through the ECS Cloud
  Assistant. Runs only when the operator passed --confirmed AFTER telling
  the customer the exact command, its scope and that it changes nothing.
  Confirmation is valid for this single run only.
* Layer 3 -- gated snapshot creation: the single low-risk reversible write
  (snapshot-first discipline). Runs only with --confirmed after the
  customer accepted the billing notice.
* Anything outside ALLOWED_ACTIONS -- in particular every instance state
  transition (start / stop / reboot / force variants) and every destructive
  operation -- can never leave this host: the shared CLI layer refuses it.
  Such operations appear in the report as customer-executed only (console or the equivalent OpenAPI).

Credentials come exclusively from the aliyun CLI default credential chain;
this script never reads, prints or passes AK/SK/token values.

Output contract: human-readable report (default) or --json; every run ends
with `STATUS: OK|DEGRADED|FAIL` and `NEXT_ACTION: ...`.
Exit codes: 0 = OK/DEGRADED conclusion produced; 1 = FAIL (missing input,
unmet confirmation gate, or credentials unusable); 2 = argparse usage error.

Usage examples:
  python3 scripts/areas/instance_start_stop_anomaly/ecs_start_stop_diagnosis.py \
      --region-id cn-hangzhou --instance-id i-2zexxxxxxxxxxxxxxx
  python3 scripts/areas/instance_start_stop_anomaly/ecs_start_stop_diagnosis.py \
      --region-id cn-hangzhou --instance-id i-2zexxxxxxxxxxxxxxx \
      --operation-time "2026-08-12 16:01" --symptom "stuck in stopping 20 min"
  python3 scripts/areas/instance_start_stop_anomaly/ecs_start_stop_diagnosis.py \
      --region-id cn-hangzhou --instance-id i-2zexxxxxxxxxxxxxxx \
      --guest-check findmnt --confirmed
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone

import _cli
from _constants import (
    BOUNDARY_MESSAGE,
    CMS_METRICS,
    CMS_NAMESPACE,
    DOC_LINKS,
    ECONOMICAL_MODE_NOTE,
    EXPECTED_DWELL_MINUTES,
    FALLBACK_READINGS,
    GUEST_ARG_RE,
    GUEST_ARG_WIN_RE,
    GUEST_COMMANDS,
    HANDOFF_TARGETS,
    INVOCATION_POLL_INTERVAL_SECONDS,
    INVOCATION_POLL_MAX,
    MAX_EXPECTED_DWELL_MINUTES,
    MIDDLE_STATES,
    NEVER_CALLED_ACTIONS,
    PAGE_SIZE,
    REBOOT_RISK_NOTICE,
    ROLLBACK_MANUAL_NOTICE,
    SNAPSHOT_BILLING_NOTICE,
    STOP_DWELL_NOTICE,
    SYMPTOM_ANCHORS,
)

REGION_RE = re.compile(r"^[a-z][a-z0-9-]{2,29}$")
INSTANCE_RE = re.compile(r"^i-[a-z0-9]{6,32}$")
DISK_RE = re.compile(r"^d-[a-z0-9]{6,32}$")

_TERMINAL_INVOCATION_STATES = {"Finished", "Failed", "Stopped", "Timeout",
                               "PartialFailed", "Error", "Success"}

# Boot-path readings the customer can paste when the guest cannot be reached
# at all (indices into FALLBACK_READINGS; whitelist gaps are deliberate).
BOOT_PASTE_KEYS = ("mount table the guest will apply at next boot",
                   "failed boot units",
                   "previous boot error log",
                   "block devices as the guest sees them")


# ---------------------------------------------------------------------------
# Report scaffold
# ---------------------------------------------------------------------------

class Report:
    """Collects sections, the degradation log and the final contract lines."""

    def __init__(self) -> None:
        self.sections = []          # [[title], [line, ...]] pairs
        self.degradations = []      # [(step, detail)]
        self.findings = []          # short conclusion sentences
        self.status = "OK"
        self.next_action = ""
        self.fail_reason = ""
        self._current = None

    def section(self, title: str) -> None:
        entry = [title, []]
        self.sections.append(entry)
        self._current = entry

    def line(self, text: str = "") -> None:
        if self._current is None:
            self.section("(untitled)")
        self._current[1].append(text)

    def finding(self, text: str) -> None:
        self.findings.append(text)

    def degrade(self, step: str, detail: str, hint: str = "") -> None:
        """EXECUTION RULE FOR ERRORS: never abort silently."""
        if self.status == "OK":
            self.status = "DEGRADED"
        masked = _cli.mask_credentials(detail or "")
        self.degradations.append((step, masked))
        line = "[WARN|DEGRADE] %s: %s" % (step, masked)
        if hint:
            line += " -- next: %s" % hint
        print(line, file=sys.stderr)

    def permission_gap(self, step: str, detail: str) -> None:
        """Denials name the missing action with the approved wording."""
        self.degrade(step, detail,
                     "the identity is missing the RAM action named in this "
                     "line; grant it per references/ram-policies.md "
                     "(NoPermission / ImplicitDeny wording only)")

    def render(self) -> str:
        out = []
        for title, lines in self.sections:
            out.append("== %s ==" % title)
            out.extend(lines)
            out.append("")
        if self.degradations:
            out.append("== Graceful degradation log ==")
            for step, detail in self.degradations:
                out.append("  - %s: %s" % (step, detail))
            out.append("")
        out.append("STATUS: %s" % self.status)
        out.append("NEXT_ACTION: %s" % self.next_action)
        return "\n".join(out)

    def to_json(self) -> dict:
        return {
            "status": self.status,
            "next_action": self.next_action,
            "fail_reason": self.fail_reason,
            "findings": list(self.findings),
            "degradations": [{"step": s, "detail": d}
                             for s, d in self.degradations],
            "sections": [{"title": t, "lines": l} for t, l in self.sections],
            "session_id": _cli.session_id(),
        }


# ---------------------------------------------------------------------------
# Pure decision functions (boundary-asserted at the bottom of this module)
# ---------------------------------------------------------------------------

def classify_dwell(elapsed_minutes, status):
    """Map an intermediate-state dwell time onto the evidence window.

    Bands: no-intermediate-state | unknown-elapsed | within-normal |
    within-ceiling | exceeded.
    """
    if status not in MIDDLE_STATES:
        return {"band": "no-intermediate-state", "ceiling": None}
    if elapsed_minutes is None:
        return {"band": "unknown-elapsed",
                "ceiling": MAX_EXPECTED_DWELL_MINUTES}
    if elapsed_minutes <= EXPECTED_DWELL_MINUTES[1]:
        return {"band": "within-normal",
                "ceiling": MAX_EXPECTED_DWELL_MINUTES,
                "remaining_max": max(
                    0.0, MAX_EXPECTED_DWELL_MINUTES - elapsed_minutes)}
    if elapsed_minutes <= MAX_EXPECTED_DWELL_MINUTES:
        return {"band": "within-ceiling",
                "ceiling": MAX_EXPECTED_DWELL_MINUTES,
                "remaining_max": max(
                    0.0, MAX_EXPECTED_DWELL_MINUTES - elapsed_minutes)}
    return {"band": "exceeded",
            "over_minutes": elapsed_minutes - MAX_EXPECTED_DWELL_MINUTES}


def parse_iso_time(text):
    """Parse an operation timestamp; naive input is read as UTC and flagged.

    Returns (datetime|None, assumed_utc: bool).
    """
    raw = (text or "").strip()
    if not raw:
        return None, False
    iso = raw.replace("T", " ")
    if iso.endswith("Z") or iso.endswith("z"):
        iso = iso[:-1] + "+00:00"
    assumed_utc = False
    dt = None
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(iso, fmt)
                break
            except ValueError:
                continue
    if dt is None:
        return None, False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        assumed_utc = True
    return dt, assumed_utc


def elapsed_minutes_since(dt, now=None):
    """Whole minutes from `dt` to now (clamped at 0)."""
    if dt is None:
        return None
    now = now or datetime.now(timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 60.0)


def match_symptoms(text):
    """OCR-tolerant anchor matching over the raw customer wording (any
    language). Returns anchor entries hit -- one ticket routinely spans
    instance-level AND guest-level symptoms."""
    hay = (text or "").lower()
    hits = []
    if not hay:
        return hits
    for entry in SYMPTOM_ANCHORS:
        for anchor in entry["anchors"]:
            if anchor.lower() in hay:
                hits.append(entry)
                break
    return hits


def findmnt_device_mounts(output):
    """Extract {target: device} pairs for real /dev/* mounts from a findmnt
    reading. Tolerates tree-prefix glyphs on sub-mount lines."""
    mounts = {}
    for line in (output or "").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        target = parts[0]
        if "/" in target:
            target = target[target.index("/"):]
        if target.startswith("/") and parts[1].startswith("/dev/"):
            mounts[target] = parts[1]
    return mounts


def _device_family(device):
    """/dev/vdb1 -> /dev/vdb (partition-tolerant comparison key)."""
    return device.rstrip("0123456789")


def crosscheck_mounts(disks, guest_mounts, expected_mount):
    """Cloud-side disk inventory <-> guest mount view (C4).

    Wording stays at candidate level: the boot-time mount table itself is
    not auto-readable, so conclusions are phrased as candidates.
    """
    notes = []
    data_disks = [d for d in disks if d.get("Type") == "data"]
    if guest_mounts is None:
        if data_disks:
            notes.append(
                "cloud side shows %d data disk(s) attached; the guest mount "
                "view is missing -- run the gated 'findmnt' reading (or ask "
                "the customer to paste one) to complete the cross-check"
                % len(data_disks))
        return notes
    mounted_families = {_device_family(dev) for dev in guest_mounts.values()}
    unmounted = []
    for disk in data_disks:
        device = disk.get("Device") or ""
        if device and _device_family(device) not in mounted_families:
            unmounted.append("%s (%s, %s)" % (disk.get("DiskId"), device,
                                              disk.get("Status")))
    if unmounted:
        notes.append(
            "attached in the cloud but NOT visible in the guest mount table: "
            "%s -- classic post-reboot mount-failure pattern (missing or "
            "wrong entry in the boot-time mount table)" % ", ".join(unmounted))
    if expected_mount and expected_mount not in guest_mounts:
        notes.append(
            "expected mount point '%s' is absent from the guest mount view "
            "-- compare with the customer's mount-table reading"
            % expected_mount)
    if not data_disks:
        stale = {t: d for t, d in guest_mounts.items()
                 if t != "/" and not t.startswith("/boot")}
        if stale:
            notes.append(
                "cloud side shows only the system disk, yet the guest mounts "
                "%s -- a boot-time mount entry for a disk that no longer "
                "exists can hang the boot or drop it into emergency mode "
                "(candidate mount-table conflict)" % stale)
    return notes


def snapshot_by_disk(snapshots):
    """Newest USABLE snapshot per disk (pending ones cannot roll back)."""
    per = {}
    for snap in snapshots:
        disk = snap.get("SourceDiskId") or "?"
        item = per.setdefault(disk, {"total": 0, "available": 0,
                                     "latest_time": "", "latest_id": ""})
        item["total"] += 1
        if str(snap.get("Status") or "").lower() == "accomplished":
            item["available"] += 1
            created = str(snap.get("CreationTime") or "")
            if created >= item["latest_time"]:
                item["latest_time"] = created
                item["latest_id"] = str(snap.get("SnapshotId") or "")
    return per


def latest_datapoint_summary(datapoints):
    """Reduce CMS datapoints (already parsed to a list) to one evidence
    dict, or None when there is no usable value."""
    values = []
    for point in datapoints or []:
        if not isinstance(point, dict):
            continue
        for key in ("Average", "Maximum", "Value"):
            if point.get(key) is not None:
                try:
                    values.append(float(point[key]))
                except (TypeError, ValueError):
                    pass
                break
    if not values:
        return None
    return {"max": max(values), "avg": sum(values) / len(values),
            "points": len(values)}


def boot_evidence_checklist():
    """Fallback evidence lines for unreachable guests (customer-paste / VNC)."
    """
    lines = []
    for item in FALLBACK_READINGS:
        if item["topic"] in BOOT_PASTE_KEYS:
            lines.append("  - %s -> %s" % (item["topic"],
                                           item["customer_command"]))
    return lines


# ---------------------------------------------------------------------------
# Cloud evidence steps (Layer 1)
# ---------------------------------------------------------------------------

def _query_error(report, step, err):
    """Record one failed query on its own line without aborting the run."""
    if err.is_permission_error:
        report.permission_gap(step, str(err))
    else:
        report.degrade(step, str(err),
                       "this evidence area is unavailable; continue and "
                       "state the gap in the report")


def fetch_instance(report, args):
    """DescribeInstances with an explicit id or a locator filter; returns
    the matched instance dict or None (candidates fill the report)."""
    params = {"RegionId": args.region_id,
              "PageSize": str(PAGE_SIZE), "PageNumber": "1"}
    if args.instance_id:
        params["InstanceIds"] = json.dumps([args.instance_id])
    elif args.private_ip:
        params["PrivateIpAddresses"] = args.private_ip
    elif args.public_ip:
        params["PublicIpAddresses"] = args.public_ip
    elif args.instance_name:
        params["InstanceName"] = args.instance_name
    try:
        body = _cli.call("ecs", "DescribeInstances", params,
                         region=args.region_id, profile=args.profile,
                         timeout=args.cli_timeout)
    except _cli.CliError as e:
        _query_error(report, "DescribeInstances", e)
        return None
    instances = _cli.as_list(_cli.dig(body, ["Instances"]))
    if not instances:
        return None
    if len(instances) > 1 and not args.instance_id:
        report.line("locator matched %d instances -- re-run with one "
                    "--instance-id:" % len(instances))
        for inst in instances[:10]:
            report.line("   %s  %-10s %s" % (inst.get("InstanceId"),
                                             inst.get("Status"),
                                             inst.get("InstanceName") or "-"))
        return None
    return instances[0]


def fetch_full_status(report, args, instance_id):
    try:
        body = _cli.call("ecs", "DescribeInstancesFullStatus",
                         {"RegionId": args.region_id,
                          "InstanceId.1": instance_id,
                          "PageSize": "10"},
                         region=args.region_id, profile=args.profile,
                         timeout=args.cli_timeout)
    except _cli.CliError as e:
        _query_error(report, "DescribeInstancesFullStatus", e)
        return []
    return _cli.as_list(_cli.dig(body, ["InstanceFullStatusSets"]))


def fetch_history_events(report, args, instance_id):
    try:
        body = _cli.call("ecs", "DescribeInstanceHistoryEvents",
                         {"RegionId": args.region_id,
                          "InstanceId": instance_id,
                          "PageSize": "20", "PageNumber": "1"},
                         region=args.region_id, profile=args.profile,
                         timeout=args.cli_timeout)
    except _cli.CliError as e:
        _query_error(report, "DescribeInstanceHistoryEvents", e)
        return []
    return _cli.as_list(_cli.dig(body, ["InstanceSystemEventSet"]))


def fetch_disks(report, args, instance_id):
    try:
        body = _cli.call("ecs", "DescribeDisks",
                         {"RegionId": args.region_id,
                          "InstanceId": instance_id,
                          "PageSize": "100"},
                         region=args.region_id, profile=args.profile,
                         timeout=args.cli_timeout)
    except _cli.CliError as e:
        _query_error(report, "DescribeDisks", e)
        return []
    return _cli.as_list(_cli.dig(body, ["Disks"]))


def fetch_snapshots(report, args, instance_id):
    try:
        body = _cli.call("ecs", "DescribeSnapshots",
                         {"RegionId": args.region_id,
                          "InstanceId": instance_id,
                          "PageSize": "50"},
                         region=args.region_id, profile=args.profile,
                         timeout=args.cli_timeout)
    except _cli.CliError as e:
        _query_error(report, "DescribeSnapshots", e)
        return []
    return _cli.as_list(_cli.dig(body, ["Snapshots"]))


def fetch_cms(report, args, instance_id):
    """Read the metric set independently: one failure never blocks the rest.
    The metric list is the batch's reading plan (open verification item);
    anything unverified degrades without poisoning the conclusion."""
    out = {}
    for metric, purpose, agent_needed in CMS_METRICS:
        params = {
            "Namespace": CMS_NAMESPACE,
            "MetricName": metric,
            "Dimensions": [{"instanceId": instance_id}],
            "Period": "60",
            "Length": "10",
        }
        step = "DescribeMetricLast %s" % metric
        try:
            body = _cli.call("cms", "DescribeMetricLast", params,
                             region=args.region_id, profile=args.profile,
                             timeout=args.cli_timeout)
        except _cli.CliError as e:
            _query_error(report, step, e)
            continue
        raw = body.get("Datapoints")
        points = []
        if isinstance(raw, str) and raw.strip():
            try:
                points = json.loads(raw)
            except json.JSONDecodeError:
                report.degrade(step, "Datapoints payload was not JSON",
                               "metric pending live verification")
                continue
        elif isinstance(raw, list):
            points = raw
        summary = latest_datapoint_summary(points)
        out[metric] = {"purpose": purpose, "summary": summary,
                       "agent_required": bool(agent_needed)}
        if summary is None:
            report.degrade(
                step, "no datapoint returned",
                "guest-agent metric (memory area) needs the CloudMonitor "
                "agent installed in the instance" if agent_needed
                else "check the console CloudMonitor page instead")
    return out


# ---------------------------------------------------------------------------
# Gated operations (Layers 2 and 3)
# ---------------------------------------------------------------------------

def guest_disclosure(spec, arg, instance_id):
    command = spec["command"] + ((" " + arg) if arg else "")
    return [
        "Gated in-guest check about to run (needs the customer's approval):",
        "  instance : %s" % (instance_id or "(resolve the locator first)"),
        "  command  : %s" % command,
        "  effect   : read-back only -- the command enumerates state and",
        "             changes nothing on the instance",
        "  channel  : ECS Cloud Assistant (the dispatch itself is an",
        "             auditable write-class API call)",
        "  scope    : this ONE command, this ONE time",
    ]


def run_guest_check(report, args, instance_id):
    """Dispatch one whitelisted non-mutating command and read its output
    back through the invocation history. Unavailability degrades to the
    customer-paste / VNC path."""
    pool = GUEST_COMMANDS.get(args.os_type) or {}
    spec = pool.get(args.guest_check)
    report.section("7. Gated in-guest evidence (single whitelisted command)")
    if spec is None:
        report.status = "FAIL"
        report.fail_reason = ("guest check key '%s' is not on the whitelist"
                              % args.guest_check)
        report.line("refused: not on the whitelist. Valid %s keys: %s"
                    % (args.os_type, ", ".join(sorted(pool))))
        report.line("Anything outside the whitelist is executed by the "
                    "customer over VNC/SSH and pasted back -- see "
                    "references/instance-start-stop-anomaly__guest-evidence-commands.md")
        return None
    arg = (args.guest_arg or "").strip()
    if spec.get("arg"):
        if not arg:
            report.status = "FAIL"
            report.fail_reason = "this guest check requires --guest-arg <path>"
            return None
        probe = GUEST_ARG_WIN_RE if args.os_type == "windows" else GUEST_ARG_RE
        if not probe.match(arg):
            report.status = "FAIL"
            report.fail_reason = ("--guest-arg rejected: the path must be "
                                  "absolute and free of shell "
                                  "metacharacters")
            return None
    command = spec["command"] + ((" " + arg) if arg else "")
    for ln in guest_disclosure(spec, arg, instance_id):
        report.line(ln)
    report.line("gate: operator passed --confirmed for this one command")
    params = {
        "RegionId": args.region_id,
        "Type": spec["type"],
        "Name": "ecs-start-stop-anomaly-guest-check",
        "Description": "one non-mutating whitelisted reading (skill "
                       "area:instance-start-stop-anomaly)",
        "CommandContent": command,
        "InstanceId.1": instance_id,
        "Timeout": "60",
    }
    try:
        body = _cli.call("ecs", "RunCommand", params,
                         region=args.region_id, profile=args.profile,
                         timeout=args.cli_timeout)
    except _cli.CliError as e:
        if e.is_permission_error:
            report.degrade("in-guest dispatch", str(e),
                           "grant the gated dispatch action on this instance "
                           "or fall back to a customer-paste reading "
                           "(references/ram-policies.md)")
        else:
            report.degrade("in-guest dispatch", str(e),
                           "Cloud Assistant likely unreachable (agent "
                           "offline / guest not booted) -- use the VNC "
                           "evidence checklist instead")
        return None
    invoke_id = str(body.get("InvokeId") or "")
    if not invoke_id:
        report.degrade("in-guest dispatch",
                       "dispatch accepted but returned no invoke id",
                       "read back with the invocation history query later")
        return None
    report.line("invoke id: %s" % invoke_id)
    output, state = poll_invocation(report, args, invoke_id)
    report.line("final invocation state: %s" % (state or "unknown"))
    if output:
        excerpt = output.splitlines()
        for ln in excerpt[:60]:
            report.line("  | " + ln)
        if len(excerpt) > 60:
            report.line("  | ... (%d more lines; the full reading stays in "
                        "the invocation history)" % (len(excerpt) - 60))
    else:
        report.degrade("in-guest read-back", "no output captured",
                       "fallback: ask the customer to run the reading over "
                       "VNC/SSH and paste it (see "
                       "references/instance-start-stop-anomaly__guest-evidence-commands.md)")
    return output


def poll_invocation(report, args, invoke_id):
    """Poll the invocation history until terminal or the budget runs out."""
    last_state = ""
    for _round in range(INVOCATION_POLL_MAX):
        try:
            body = _cli.call("ecs", "DescribeInvocations",
                             {"RegionId": args.region_id,
                              "InvokeId": invoke_id,
                              "IncludeOutput": "true"},
                             region=args.region_id, profile=args.profile,
                             timeout=args.cli_timeout)
        except _cli.CliError as e:
            _query_error(report, "in-guest read-back", e)
            return "", last_state
        invs = _cli.as_list(_cli.dig(body, ["Invocations"]))
        inst_rows = []
        for inv in invs:
            inst_rows = _cli.as_list(_cli.dig(inv, ["InvokeInstances"]))
            if inst_rows:
                break
        if not inst_rows:
            time.sleep(INVOCATION_POLL_INTERVAL_SECONDS)
            continue
        row = inst_rows[0]
        last_state = str(row.get("InvocationStatus")
                         or row.get("InvokeStatus") or "")
        if last_state in _TERMINAL_INVOCATION_STATES:
            return _cli.decode_guest_output(str(row.get("Output") or "")), \
                last_state
        time.sleep(INVOCATION_POLL_INTERVAL_SECONDS)
    report.degrade("in-guest read-back",
                   "invocation did not settle within the poll budget "
                   "(last state: %s)" % (last_state or "unknown"),
                   "Cloud Assistant may be offline while the guest boots; "
                   "read the history later or use the VNC path")
    return "", last_state


def run_snapshot(report, args, instance_id):
    """Gated snapshot-first write (the only low-risk reversible action)."""
    report.section("7b. Gated snapshot-first write")
    if not DISK_RE.match(args.disk_id or ""):
        report.status = "FAIL"
        report.fail_reason = ("--create-snapshot needs a valid --disk-id "
                              "(d-...) chosen from the disk inventory")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report.line("disk : %s (instance %s)" % (args.disk_id, instance_id))
    report.line("name : pre-recovery-%s" % stamp)
    report.line("gate : operator passed --confirmed after relaying the "
                "billing note below")
    report.line("note : %s" % SNAPSHOT_BILLING_NOTICE)
    params = {
        "RegionId": args.region_id,
        "DiskId": args.disk_id,
        "SnapshotName": "pre-recovery-%s" % stamp,
        "Description": "snapshot-first backup created before a manual "
                       "recovery step (skill alibabacloud-ecs-"
                       "high-frequency-issues)",
    }
    try:
        body = _cli.call("ecs", "CreateSnapshot", params,
                         region=args.region_id, profile=args.profile,
                         timeout=args.cli_timeout)
    except _cli.CliError as e:
        if e.is_permission_error:
            report.degrade("snapshot-first write", str(e),
                           "grant the gated snapshot action on this disk -- "
                           "see references/ram-policies.md")
        else:
            report.degrade("snapshot-first write", str(e),
                           "the customer can create the same snapshot in the "
                           "console before proceeding")
        return
    report.line("snapshot id: %s (progress: %s)"
                % (body.get("SnapshotId", "(none returned)"),
                   body.get("Status", "progressing")))
    report.line("keep the snapshot until the incident is closed, then delete "
                "it from the console (billing).")
    report.finding("snapshot-first backup established before recovery work")


# ---------------------------------------------------------------------------
# Interpretation blocks
# ---------------------------------------------------------------------------

def dwell_guidance(report, dwell):
    band = dwell["band"]
    if band in ("within-normal", "within-ceiling"):
        report.line("verdict : inside the expected transition window -- "
                    "normal flow, not a stuck machine")
        report.line(STOP_DWELL_NOTICE)
        report.line("next    : wait; re-check at the %d-minute ceiling "
                    "(remaining <= %.0f min)."
                    % (MAX_EXPECTED_DWELL_MINUTES,
                       dwell.get("remaining_max", 0.0)))
        report.line("if it must come back faster next time: the console "
                    "offers a forced stop/reboot choice BEFORE the "
                    "operation; once Stopping begins nothing -- including "
                    "support -- can intervene. Forcing skips the OS flush, "
                    "so snapshot first (%s)." % DOC_LINKS["create-snapshot"])
        report.finding("dwell inside the expected window")
    elif band == "exceeded":
        report.line("verdict : dwell exceeded the %d-minute ceiling -- "
                    "treat as a real anomaly and escalate WITH evidence "
                    "(over by ~%.0f min)"
                    % (MAX_EXPECTED_DWELL_MINUTES,
                       dwell.get("over_minutes", 0.0)))
        report.line("the platform-event and resource-pressure sections above "
                    "are the escalation package; attach them to a support "
                    "ticket.")
        report.line("this skill never forces an instance state; a forced "
                    "stop/reboot stays a manual console decision -- relay "
                    "the risk notice first:")
        for ln in REBOOT_RISK_NOTICE:
            report.line("  " + ln)
        report.finding("dwell beyond the ceiling: escalate with evidence")
    elif band == "unknown-elapsed":
        report.line("verdict : intermediate state; dwell time NOT provided "
                    "-- the wait window cannot be bounded yet.")
        report.line("next    : ask when the operation was issued, then "
                    "re-run with --operation-time or --elapsed-minutes.")
        report.finding("dwell unknown: obtain the operation timestamp")
    else:
        report.line("verdict : the instance is not in an intermediate state "
                    "at query time.")


def recent_change_guidance(report, change):
    table = {
        "resize": ["spec changes take effect only after an instance restart; "
                   "expect one deliberate Stopping/Starting cycle "
                   "(%s)" % DOC_LINKS["spec-change-overview"]],
        "security-group": ["boot-stage failures after a security-group edit "
                           "can involve the metadata-service dependency "
                           "(anchor: 100.100.100.200 / Network is "
                           "unreachable) -- see "
                           "references/instance-start-stop-anomaly__boot-failure-root-causes.md",
                           "port reachability itself belongs to the "
                           "connection skills"],
        "package-upgrade": ["guest library/system upgrades that break login "
                            "or boot are OS-tier repairs; this skill stops "
                            "at naming the candidate"],
        "snapshot-rollback": ["a rollback recently overwrote the disk -- if "
                              "the system now fails to boot, verify the "
                              "rolled-back point and whether newer "
                              "snapshots exist before touching anything",
                              ROLLBACK_MANUAL_NOTICE],
        "os-replace": ["changing the OS releases the old system disk; data "
                       "and installed software on it are permanently gone "
                       "(%s)" % DOC_LINKS["os-replace"]],
        "password-reset-offline": ["an OFFLINE password reset requires a "
                                   "reboot to apply -- the following stop/"
                                   "start is expected, not a new failure "
                                   "(%s)" % DOC_LINKS["credential-management"]],
    }
    lines = table.get(change or "none", [])
    if not lines:
        return
    report.section("Recent-change notes")
    for ln in lines:
        report.line("  - %s" % ln)


def handoff_lines(report, hits):
    """Emit handoff/declaration routing for recognized signatures."""
    hand = [h for h in hits if h["action"] == "handoff"]
    unsup = [h for h in hits if h["action"] == "declare-unsupported"]
    if not hand and not unsup:
        return
    report.section("Handoff signals recognized (routed, not solved here)")
    for entry in unsup:
        report.line("  - %s -- declare unsupported and point at the owning "
                    "product" % entry["family"])
    for entry in hand:
        target = HANDOFF_TARGETS.get(entry.get("target", ""), {})
        skill = target.get("skill") or "the account/security support flow"
        report.line("  - [%s] %s" % (entry["id"], entry["family"]))
        report.line("    route to: %s" % skill)
        for ev in target.get("evidence_to_attach", []):
            report.line("      attach: %s" % ev)
        report.line("      note  : %s" % entry["note"])


def candidate_lines(report, hits):
    keep = [h for h in hits if h["action"] == "investigate"]
    if not keep:
        return
    report.section("Candidate causes from customer wording (anchors)")
    for entry in keep:
        report.line("  - [%s] %s" % (entry["id"], entry["family"]))
        report.line("    %s" % entry["note"])


def running_branch(report, hits):
    report.line(BOUNDARY_MESSAGE)
    needs_handoff = [h for h in hits if h["action"] == "handoff"]
    if not needs_handoff:
        report.line("no explicit handoff anchor was supplied -- collect the "
                    "customer's exact error text and classify it with "
                    "references/instance-start-stop-anomaly__handoff-map.md")
    report.line("exception kept here: if data or disk content vanished AFTER "
                "a reboot, the mount cross-check (section 5) decides first "
                "-- that root cause belongs to the start/stop tier, not the "
                "OS tier.")
    report.finding("instance-level state machine is healthy; route the "
                   "guest-side symptom per the handoff map")


def stopped_branch(report, lock_reasons, stopped_mode):
    report.line("The instance is Stopped while the customer reports it will "
                "not come up -- the exact console error text is the "
                "discriminator; run the boot-failure decision tree in "
                "references/instance-start-stop-anomaly__boot-failure-root-causes.md.")
    if lock_reasons:
        report.line("  an operation lock is present -- resolution belongs "
                    "to the owning account (billing/security), and boot "
                    "diagnosis is meaningless while locked")
    if stopped_mode == "NoCharged":
        report.line("  " + ECONOMICAL_MODE_NOTE)
    report.line("  a start attempt in the console is a manual customer "
                "step: %s" % DOC_LINKS["start-instance"])
    report.line("  before that manual step, relay the risk notice:")
    for ln in REBOOT_RISK_NOTICE:
        report.line("    %s" % ln)
    report.line("  evidence the customer can paste (whitelist gaps):")
    for ln in boot_evidence_checklist():
        report.line(ln)


# ---------------------------------------------------------------------------
# Next-action computation (pure over already-collected facts)
# ---------------------------------------------------------------------------

def compute_next_action(status, dwell, hits, lock_reasons, mounts):
    hand = [h for h in hits if h["action"] == "handoff"]
    if status in MIDDLE_STATES:
        if dwell["band"] in ("within-normal", "within-ceiling"):
            return ("Wait until the %d-minute ceiling with the customer, "
                    "then re-run this script. No forced state change is "
                    "possible or permitted from this skill."
                    % MAX_EXPECTED_DWELL_MINUTES)
        if dwell["band"] == "exceeded":
            return ("Escalate via a support ticket attaching sections 2-6 "
                    "as the evidence package; forced stop/reboot remains a "
                    "manual console decision after the risk notice is "
                    "relayed.")
        return ("Obtain the operation timestamp from the customer and "
                "re-run with --operation-time or --elapsed-minutes.")
    if status == "Stopped":
        if lock_reasons:
            return ("Resolve the operation lock with the owning account "
                    "first, then re-run.")
        return ("Follow the boot-failure decision tree; before any manual "
                "recovery step offer the gated snapshot-first write, and "
                "collect the mount-table reading per the paste checklist.")
    if status == "Running":
        if hand or mounts is not None:
            return ("Hand off with the collected evidence package per "
                    "references/instance-start-stop-anomaly__handoff-map.md.")
        return ("Instance-level start/stop is healthy: confirm exactly what "
                "fails inside the guest, run the gated mount cross-check if "
                "data vanished after a reboot, then route via "
                "references/instance-start-stop-anomaly__handoff-map.md.")
    return ("Re-run once the instance leaves the unknown state, or supply a "
            "clearer locator.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ecs_start_stop_diagnosis.py",
        description="ECS instance start/stop state anomaly diagnosis "
                    "(cloud evidence queries + confirmation-gated guest "
                    "read-back + gated snapshot-first write)")
    p.add_argument("--region-id", required=True,
                   help="ECS region id, e.g. cn-hangzhou (never guessed)")
    loc = p.add_mutually_exclusive_group()
    loc.add_argument("--instance-id", help="target instance id (i-...)")
    loc.add_argument("--private-ip", help="private IP locator")
    loc.add_argument("--public-ip", help="public IP locator")
    loc.add_argument("--instance-name", help="instance name locator")
    p.add_argument("--operation-time", metavar="TIMESTAMP",
                   help="when the customer issued the start/stop/reboot "
                        "(ISO 8601; naive values are read as UTC)")
    p.add_argument("--elapsed-minutes", type=float,
                   help="minutes since the operation, if already stated")
    p.add_argument("--symptom", default="",
                   help="verbatim customer wording (free text, any "
                        "language; anchors are OCR-tolerant)")
    p.add_argument("--recent-change",
                   choices=("resize", "security-group", "package-upgrade",
                            "snapshot-rollback", "os-replace",
                            "password-reset-offline", "none"),
                   default=None,
                   help="the change that preceded the anomaly, if known")
    p.add_argument("--expected-mount", default="",
                   help="mount point the customer expects to see (e.g. "
                        "/mnt) for the disk/mount cross-check")
    p.add_argument("--os-type", choices=("linux", "windows"),
                   default="linux")
    p.add_argument("--guest-check",
                   help="key of ONE whitelisted non-mutating guest command "
                        "(linux: findmnt, df-h, df-i, stat, ls-by-uuid; "
                        "windows: get-volume, get-psdrive, get-childitem)")
    p.add_argument("--guest-arg", default="",
                   help="single absolute path argument for the guest "
                        "commands that require one")
    p.add_argument("--create-snapshot", action="store_true",
                   help="request the gated snapshot-first write for "
                        "--disk-id")
    p.add_argument("--disk-id",
                   help="disk id (d-...) for the snapshot write")
    p.add_argument("--confirmed", action="store_true",
                   help="the customer approved THIS run's gated operation "
                        "after the disclosure (one time only)")
    p.add_argument("--profile", default=None,
                   help="optional aliyun CLI profile name")
    p.add_argument("--cli-timeout", type=int, default=60,
                   help="per-call CLI timeout in seconds (default 60)")
    p.add_argument("--json", action="store_true", help="JSON output")
    return p


def validate_args(args, report):
    if not REGION_RE.match(args.region_id or ""):
        report.status = "FAIL"
        report.fail_reason = ("--region-id '%s' is not a valid region id "
                              "(e.g. cn-hangzhou); ask the customer, never "
                              "guess" % (args.region_id,))
        return False
    if args.instance_id and not INSTANCE_RE.match(args.instance_id):
        report.status = "FAIL"
        report.fail_reason = ("--instance-id '%s' does not look like an ECS "
                              "instance id" % args.instance_id)
        return False
    if not (args.instance_id or args.private_ip or args.public_ip
            or args.instance_name):
        report.status = "FAIL"
        report.fail_reason = "no target locator supplied"
        return False
    if args.cli_timeout is not None and args.cli_timeout <= 0:
        report.status = "FAIL"
        report.fail_reason = "--cli-timeout must be positive"
        return False
    return True


def _emit(report, args) -> None:
    if args.json:
        payload = report.to_json()
        payload["request"] = {
            "region_id": args.region_id,
            "instance_id": args.instance_id,
            "operation_time": args.operation_time,
            "recent_change": args.recent_change,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(report.render())


def main() -> None:
    _self_test()
    args = build_parser().parse_args()
    report = Report()
    _cli.check_cli_available()

    if not validate_args(args, report):
        report.next_action = ("Ask the customer for the missing/invalid "
                              "input (region id and one locator); do not "
                              "guess values.")
        _emit(report, args)
        sys.exit(1)

    # ---- confirmation gate first: no gated op without --confirmed ----
    gated = []
    if args.guest_check:
        gated.append("in-guest command '%s'" % args.guest_check)
    if args.create_snapshot:
        gated.append("snapshot creation on disk %s" % (args.disk_id or "?"))
    if gated and not args.confirmed:
        report.section("Confirmation gate (nothing was executed)")
        report.line("Requested gated operations: %s" % "; ".join(gated))
        if args.guest_check:
            pool = GUEST_COMMANDS.get(args.os_type) or {}
            spec = pool.get(args.guest_check)
            if spec:
                for ln in guest_disclosure(spec,
                                           (args.guest_arg or "").strip(),
                                           args.instance_id):
                    report.line("  " + ln)
            else:
                report.line("  key '%s' is not on the whitelist -- it would "
                            "be refused even with --confirmed"
                            % args.guest_check)
        if args.create_snapshot:
            report.line("  snapshot-first write: creates a pay-as-you-go "
                        "snapshot of disk %s; reversible by deleting it "
                        "afterwards." % (args.disk_id or "(unknown disk)"))
            report.line("  %s" % SNAPSHOT_BILLING_NOTICE)
        report.line("Never-executed actions (customer-executed only: console or the equivalent OpenAPI; this skill never performs them): "
                    "%s." % ", ".join(NEVER_CALLED_ACTIONS))
        report.status = "FAIL"
        report.fail_reason = ("gated operation requested without "
                              "--confirmed; relay the disclosure first")
        report.next_action = ("Tell the customer exactly what will run, its "
                              "scope and its reversibility, obtain an "
                              "explicit yes, then re-run the same command "
                              "with --confirmed.")
        _emit(report, args)
        sys.exit(1)
    if gated and args.confirmed and not args.instance_id:
        report.status = "FAIL"
        report.fail_reason = ("gated operations require an explicit "
                              "--instance-id; a locator match is not a "
                              "confirmed scope")
        report.next_action = ("Re-run with the single --instance-id the "
                              "customer confirmed.")
        _emit(report, args)
        sys.exit(1)

    # ---- S0 identity pre-check ----
    report.section("1. Identity and scope")
    try:
        identity = _cli.call("sts", "GetCallerIdentity", {},
                             region=args.region_id, profile=args.profile,
                             timeout=args.cli_timeout)
    except _cli.CliError as e:
        report.fail_reason = "credentials unusable: %s" % e
        report.status = "FAIL"
        report.line("identity pre-check failed: %s" % e)
        report.next_action = ("Fix the CLI default credential chain "
                              "(aliyun sts get-caller-identity); never request AK/SK "
                              "from the customer.")
        _emit(report, args)
        sys.exit(1)
    uid = str(identity.get("AccountId") or "")
    if uid:
        report.line("account uid (auto-derived, traceability label only): %s"
                    % uid)
    else:
        report.degrade("identity pre-check",
                       "GetCallerIdentity returned no AccountId",
                       "results still cover only the current credential's "
                       "account")
    report.line("region: %s   session-id: %s"
                % (args.region_id, _cli.session_id()))

    # ---- S1 state machine (C1) ----
    report.section("2. Instance state machine")
    instance = fetch_instance(report, args)
    if instance is None:
        report.status = "FAIL"
        report.fail_reason = report.fail_reason or \
            "instance not found for the supplied locator/region"
        report.line("not found in %s -- wrong region, a released instance, "
                    "or it belongs to another account "
                    "(release semantics: %s)"
                    % (args.region_id, DOC_LINKS["release-instance"]))
        report.next_action = ("Confirm the region and the exact instance id "
                              "with the customer (or the owning account); "
                              "re-run once corrected.")
        _emit(report, args)
        sys.exit(1)

    instance_id = str(instance.get("InstanceId") or args.instance_id or "")
    status = str(instance.get("Status") or "Unknown")
    report.line("instance : %s  (%s)"
                % (instance_id, instance.get("InstanceName") or "-"))
    report.line("status   : %s" % status)
    report.line("type     : %s / charge %s / network %s"
                % (instance.get("InstanceType", "?"),
                   instance.get("InstanceChargeType", "?"),
                   instance.get("InstanceNetworkType", "?")))
    stopped_mode = str(instance.get("StoppedMode") or "")
    if stopped_mode:
        report.line("stop mode: %s%s"
                    % (stopped_mode,
                       " (economical mode)" if stopped_mode == "NoCharged"
                       else ""))
    locks = _cli.as_list(_cli.dig(instance, ["OperationLocks"]))
    lock_reasons = sorted({str(r.get("LockReason")) for r in locks
                           if isinstance(r, dict) and r.get("LockReason")})
    if lock_reasons:
        report.line("operation locks: %s -- a locked instance cannot be "
                    "started/stopped by ANYONE until the lock reason "
                    "(billing / security / recycling) is resolved with the "
                    "owning account" % ", ".join(lock_reasons))
    report.line("lifecycle: Running -> Stopping -> Starting -> Running is "
                "the normal path (references/instance-start-stop-anomaly__instance-state-machine.md)")

    dwell = {"band": "no-intermediate-state"}
    if status in MIDDLE_STATES:
        elapsed = args.elapsed_minutes
        if elapsed is None and args.operation_time:
            dt, assumed_utc = parse_iso_time(args.operation_time)
            if dt is None:
                report.degrade("operation-time parsing",
                               "could not parse '%s'" % args.operation_time,
                               "pass ISO 8601 or use --elapsed-minutes")
            else:
                elapsed = elapsed_minutes_since(dt)
                report.line("dwell since operation: %.1f min%s"
                            % (elapsed,
                               " (naive input read as UTC)"
                               if assumed_utc else ""))
        dwell = classify_dwell(elapsed, status)
        report.line("dwell band: %s" % dwell["band"])

    # ---- S2 platform health / events (C2) ----
    report.section("3. Platform-side health and system events")
    full_statuses = fetch_full_status(report, args, instance_id)
    if full_statuses:
        for fs in full_statuses[:5]:
            if not isinstance(fs, dict):
                continue
            report.line("  health=%s  instance-status=%s"
                        % (_cli.dig(fs, ["HealthStatus", "Name"], "?"),
                           _cli.dig(fs, ["Status", "Name"], "?")))
            for ev in _cli.as_list(_cli.dig(fs, ["InstanceEventTypeSet"])):
                if isinstance(ev, dict):
                    report.line("    scheduled event: %s / %s (%s)"
                                % (ev.get("Name", "?"), ev.get("Code", "?"),
                                   ev.get("NotBefore")
                                   or ev.get("EventFinishTime") or "-"))
    elif not any(s == "DescribeInstancesFullStatus"
                 for s, _ in report.degradations):
        report.line("  no full-status record returned (empty is valid)")
    history = fetch_history_events(report, args, instance_id)
    if history:
        report.line("  recent system events:")
        for ev in history[:10]:
            if isinstance(ev, dict):
                report.line("    - %s [%s] published %s"
                            % (_cli.dig(ev, ["EventType", "Name"], "?"),
                               _cli.dig(ev, ["EventCycleStatus", "Name"], "?"),
                               ev.get("EventPublishTime", "-")))
    elif not any(s == "DescribeInstanceHistoryEvents"
                 for s, _ in report.degradations):
        report.line("  no platform system events recorded -- the transition "
                    "is not explained by a platform maintenance event")
    if lock_reasons:
        report.line("  lock present: platform-side constraint identified "
                    "(escalate to the owning account, not boot diagnosis)")

    # ---- S3 resource pressure (C3) ----
    report.section("4. Resource pressure readings (CloudMonitor)")
    cms = fetch_cms(report, args, instance_id)
    if cms:
        for metric in sorted(cms):
            info = cms[metric]
            summ = info["summary"]
            if summ:
                report.line("  %-24s avg %.1f max %.1f over %d pts (%s)"
                            % (metric, summ["avg"], summ["max"],
                               summ["points"], info["purpose"]))
            else:
                report.line("  %-24s no datapoint (%s)"
                            % (metric, info["purpose"]))
    else:
        report.line("  every metric area degraded -- state the gap: memory "
                    "readings require the CloudMonitor guest agent, which "
                    "may simply be absent")
    saturation = [m for m, i in (cms or {}).items()
                  if i["summary"] and i["summary"]["max"] >= 95.0]
    if saturation:
        report.line("  near-saturation readings on %s -- a hung guest "
                    "elongates stop AND boot (candidate: resource "
                    "exhaustion)" % ", ".join(saturation))
        report.finding("resource pressure observed on %s"
                       % ", ".join(saturation))

    # ---- S4 disks / mounts (C4) ----
    report.section("5. Disk inventory (cloud side)")
    disks = fetch_disks(report, args, instance_id)
    disk_rows = [d for d in disks if isinstance(d, dict)]
    for disk in disk_rows:
        report.line("  %-24s %-7s %-9s %-8s %sGB %s"
                    % (disk.get("DiskId", "?"), disk.get("Type", "?"),
                       disk.get("Status", "?"), disk.get("Category", "?"),
                       disk.get("Size", "?"), disk.get("Device", "")))
    if not disk_rows and not any(s == "DescribeDisks"
                                 for s, _ in report.degradations):
        report.line("  no disk records returned -- for a boot-broken "
                    "instance verify the system disk exists at all")
    mounts = None
    mount_notes = crosscheck_mounts(disk_rows, mounts,
                                    args.expected_mount.strip())
    if mount_notes:
        report.line("  mount cross-check:")
        for note in mount_notes:
            report.line("   ! %s" % note)

    # ---- S4b recovery points (C5) ----
    report.section("6. Recovery points (snapshot inventory)")
    snapshots = fetch_snapshots(report, args, instance_id)
    per_disk = snapshot_by_disk([s for s in snapshots
                                 if isinstance(s, dict)])
    if per_disk:
        for disk in sorted(per_disk):
            info = per_disk[disk]
            report.line("  disk %s: %d snapshot(s), %d usable, newest "
                        "usable %s (%s)"
                        % (disk, info["total"], info["available"],
                           info["latest_time"] or "-",
                           info["latest_id"] or "-"))
        report.line("  rule: any rollback / re-initialization the customer "
                    "performs must be PRECEDED by a fresh snapshot of the "
                    "CURRENT state (gated --create-snapshot here).")
        report.line("  rollback is executed by the customer in the console "
                    "only: %s" % DOC_LINKS["rollback-disk"])
        report.line("  %s" % ROLLBACK_MANUAL_NOTICE)
    else:
        report.line("  no snapshots visible for this instance -- recovery "
                    "options shrink to image re-deploy paths; state this "
                    "plainly and create a snapshot NOW (gated) before any "
                    "manual change")

    # ---- S5 gated guest evidence / S6 gated snapshot write ----
    hits = match_symptoms(args.symptom)
    if args.guest_check:
        guest_output = run_guest_check(report, args, instance_id)
        if guest_output and args.guest_check == "findmnt":
            mounts = findmnt_device_mounts(guest_output)
            fresh = crosscheck_mounts(disk_rows, mounts,
                                      args.expected_mount.strip())
            if fresh:
                report.line("  mount cross-check (now with guest evidence):")
                for note in fresh:
                    report.line("   ! %s" % note)
                    report.finding("mount cross-check: %s" % note)
    if args.create_snapshot:
        run_snapshot(report, args, instance_id)

    # ---- S7 triage and conclusion ----
    report.section("8. State-machine verdict")
    if status in MIDDLE_STATES:
        dwell_guidance(report, dwell)
    elif status == "Running":
        report.line("The instance is Running with the platform facts above; "
                    "the start/stop state machine itself is NOT broken -- "
                    "the reported failure lives above the hypervisor layer.")
        running_branch(report, hits)
    elif status == "Stopped":
        stopped_branch(report, lock_reasons, stopped_mode)
    else:
        report.line("status '%s' is not one of the ECS lifecycle states; "
                    "re-run to refresh or check region correctness" % status)
    candidate_lines(report, hits)
    handoff_lines(report, hits)
    recent_change_guidance(report, args.recent_change)
    if "fstab-mount" in [h["id"] for h in hits] and mounts is None:
        report.line("required evidence still missing for the mount-table "
                    "candidate: a customer-paste mount-table reading "
                    "and/or the gated findmnt check -- see "
                    "references/instance-start-stop-anomaly__guest-evidence-commands.md")

    # ---- final contract ----
    report.next_action = compute_next_action(status, dwell, hits,
                                             lock_reasons, mounts)
    _emit(report, args)
    sys.exit(1 if report.status == "FAIL" else 0)


# ---------------------------------------------------------------------------
# Inline boundary assertions for the pure functions (normal / boundary /
# invalid inputs). Executed at the start of every run -- a broken decision
# function must never speak to a real ticket.
# ---------------------------------------------------------------------------

def _self_test() -> None:
    assert classify_dwell(7, "Stopping")["band"] == "within-normal"
    assert classify_dwell(10, "Starting")["band"] == "within-normal"
    assert classify_dwell(12.5, "Stopping")["band"] == "within-ceiling"
    assert classify_dwell(15, "Stopping")["band"] == "within-ceiling"
    assert classify_dwell(15.1, "Stopping")["band"] == "exceeded"
    assert classify_dwell(None, "Stopping")["band"] == "unknown-elapsed"
    assert classify_dwell(30, "Running")["band"] == "no-intermediate-state"
    assert classify_dwell(3, "Stopping")["remaining_max"] == 12

    dt, assumed = parse_iso_time("2026-08-12 16:01")
    assert dt is not None and assumed is True
    dt2, assumed2 = parse_iso_time("2026-08-12T16:01:00+08:00")
    assert dt2 is not None and assumed2 is False
    assert parse_iso_time("garbage")[0] is None
    assert parse_iso_time("")[0] is None
    assert elapsed_minutes_since(None) is None

    hits = match_symptoms("页面一直显示 停止中，无法关机")
    assert any(h["id"] == "force-stop-request" for h in hits)
    hits = match_symptoms("console says An operating system wasn't found")
    assert any(h["id"] == "boot-disk-damage" for h in hits)
    # OCR-tolerant variants must still match
    hits = match_symptoms("Calling http://100.100.100.200/2016-01-01/"
                          "meta-data/instance-id failed: Netuork is "
                          "unreachable [Errno 101]")
    assert any(h["id"] == "cloudinit-meta" for h in hits), hits
    hits = match_symptoms("nginx: bind() to 0.0.0.0:8080 failed "
                          "(98: Address already in use)")
    assert any(h["action"] == "handoff" for h in hits)
    assert match_symptoms("") == []

    sample = ("TARGET  SOURCE      FSTYPE OPTIONS\n"
              "/       /dev/vda1   ext4   rw,relatime\n"
              "\u251c\u2500/sys  sysfs       sysfs  rw\n")
    mounts = findmnt_device_mounts(sample)
    assert mounts == {"/": "/dev/vda1"}
    assert findmnt_device_mounts("") == {}

    disks = [{"Type": "data", "DiskId": "d-test01", "Device": "/dev/vdb",
              "Status": "In_use"},
             {"Type": "system", "DiskId": "d-test02", "Device": "/dev/vda",
              "Status": "In_use"}]
    notes = crosscheck_mounts(disks, mounts, "")
    assert any("NOT visible" in n for n in notes), notes
    notes2 = crosscheck_mounts(
        [{"Type": "data", "DiskId": "d-x", "Device": "/dev/vdb",
          "Status": "In_use"}],
        {"/": "/dev/vda1", "/backup": "/dev/vdb1"}, "")
    assert notes2 == [], notes2
    assert any("guest mount view is missing" in n
               for n in crosscheck_mounts(disks, None, ""))
    stale = crosscheck_mounts([{"Type": "system", "Device": "/dev/vda"}],
                              {"/": "/dev/vda1", "/mnt": "/dev/vdc1"}, "")
    assert any("only the system disk" in s for s in stale), stale

    snap = snapshot_by_disk([
        {"SourceDiskId": "d-a", "Status": "accomplished",
         "CreationTime": "2026-08-01T00:00:00Z", "SnapshotId": "s-1"},
        {"SourceDiskId": "d-a", "Status": "progressing",
         "CreationTime": "2026-08-02T00:00:00Z", "SnapshotId": "s-2"}])
    assert snap["d-a"]["available"] == 1
    assert snap["d-a"]["latest_id"] == "s-1"

    assert GUEST_ARG_RE.match("/mnt/data")
    assert not GUEST_ARG_RE.match("/; rm -rf")
    assert not GUEST_ARG_RE.match("relative/path")
    assert GUEST_ARG_WIN_RE.match("C:\\Users\\Public")
    assert not GUEST_ARG_WIN_RE.match("C:\\Windows; del")

    assert latest_datapoint_summary(
        [{"Average": 1.5}, {"Maximum": 2.5}])["max"] == 2.5
    assert latest_datapoint_summary([]) is None
    assert latest_datapoint_summary([{"Average": "x"}]) is None

    assert REGION_RE.match("cn-hangzhou")
    assert not REGION_RE.match("CN-HANGZHOU")
    assert INSTANCE_RE.match("i-2ze0000000000abcdef")
    assert not INSTANCE_RE.match("i-bp1")
    assert DISK_RE.match("d-2ze0000000000abcdef")
    assert not DISK_RE.match("disk-a")

    assert len(boot_evidence_checklist()) >= 3


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        try:
            _self_test()
            print("selftest: all inline assertions passed")
            sys.exit(0)
        except AssertionError as exc:
            print(f"FAIL: {exc}")
            sys.exit(1)
    main()
