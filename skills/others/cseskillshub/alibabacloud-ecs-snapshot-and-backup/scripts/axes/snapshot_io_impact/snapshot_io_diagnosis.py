#!/usr/bin/env python3
"""snapshot_io_diagnosis.py - single entry point of the skill.

SECURITY SUMMARY
    * Class 1 (automatic): cloud inspection calls only - the Describe/Get
      actions registered in ``_constants.CLOUD_READ_ACTIONS``. They change
      nothing and run without a per-call gate.
    * Class 2 (gated): exactly ONE inspection command from the frozen
      whitelist, delivered into a Linux guest through the Cloud Assistant
      channel. Delivery is refused unless the caller passes ``--confirm``
      repeating the exact instance id, which stands for the customer having
      seen the disclosure block (target, command, effect, reversibility) and
      approved that one command at this one time. The delivered command only
      prints information; anything outside the whitelist is refused.
    * Class 3 (gated): ONE restore-point snapshot via the registered write
      action, refused unless ``--confirm`` repeats the exact disk id. Snapshots
      are billable; deleting one afterwards is a manual console step this
      script never performs.
    * Everything else is prohibited: this script calls no other action, in no
      other form, and it never accepts, reads, stores or prints key material -
      credentials come from the aliyun CLI default chain only.

USAGE
    python3 scripts/snapshot_io_diagnosis.py diagnose --region-id cn-hangzhou \
        --instance-id i-xxxxxxxx [--window-start 2026-02-10T14:00:00Z] \
        [--window-end 2026-02-10T15:00:00Z] [--symptom "..."] [--json]
    python3 scripts/snapshot_io_diagnosis.py guest-check --region-id cn-hangzhou \
        --instance-id i-xxxxxxxx --command-key disk-usage [--confirm i-xxxxxxxx]
    python3 scripts/snapshot_io_diagnosis.py snapshot-backup --region-id cn-hangzhou \
        --disk-id d-xxxxxxxx [--confirm d-xxxxxxxx]

EXIT CODES
    0  STATUS: OK  or  STATUS: DEGRADED (a usable report was produced)
    1  reserved for internal errors (masked)
    2  STATUS: FAIL (input rejected / no usable evidence) or argparse usage error
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import _cli
from _constants import (
    CATEGORY_PROFILE,
    CLOUD_READ_ACTIONS,
    CMS_LENGTH,
    CMS_METRICS,
    CMS_NAMESPACE_ECS,
    CMS_PERIOD_SECONDS,
    CONSOLE_ENTRIES,
    DEFAULT_SYMPTOM_WINDOW_HOURS,
    DISK_ID_PATTERN,
    GUEST_COMMANDS,
    INSTANCE_ID_PATTERN,
    INVOCATION_POLL_ATTEMPTS,
    INVOCATION_POLL_INTERVAL_SECONDS,
    ISO_UTC_PATTERN,
    LINUX_PATH_PATTERN,
    NEAR_CEILING_RATIO,
    OFFICIAL_DOCS,
    REFUSED_GUEST_TOOLS,
    REGION_ID_PATTERN,
    REJECTED_COMMAND_TOKENS,
    ROOT_CAUSE_TAXONOMY,
    RUN_COMMAND_LINUX_TYPE,
    RUN_COMMAND_TIMEOUT_SECONDS,
    SHELL_METACHARACTERS,
    SNAPSHOT_ID_PATTERN,
    SNAPSHOT_SCAN_DAYS,
    SNAPSHOT_STATUS_PROGRESSING,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
    VERDICT_EVIDENCE_INSUFFICIENT,
    VERDICT_NOT_SNAPSHOT,
    VERDICT_SNAPSHOT_AMPLIFIER,
    VERDICT_SNAPSHOT_CORRELATED,
    WINDOWS_GUEST_CHANNEL_ENABLED,
)

ECS = "ecs"
CMS = "cms"


class InputError(Exception):
    """Rejected input; the run never reaches the network."""


# ---------------------------------------------------------------------------
# Pure helpers (boundary-asserted below)
# ---------------------------------------------------------------------------

def parse_utc(text: str) -> datetime:
    """Parse an ISO-8601 timestamp to UTC. A trailing Z or a naive value is
    read as UTC; an explicit ``+HH:MM``/``-HH:MM`` offset is honoured and
    converted to UTC (never stripped, which would shift the symptom window)."""
    value = (text or "").strip()
    if not re.match(ISO_UTC_PATTERN, value):
        raise InputError("timestamp {0!r} is not ISO-8601 (YYYY-MM-DDTHH:MM[:SS]Z)".format(text))
    if re.search(r"[+-]\d{2}:\d{2}$", value):
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M%z"):
            try:
                return datetime.strptime(value, fmt).astimezone(timezone.utc)
            except ValueError:
                continue
        raise InputError("timestamp {0!r} cannot be parsed".format(text))
    normalized = re.sub(r"Z$", "", value)
    formats = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M")
    for fmt in formats:
        try:
            return datetime.strptime(normalized, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise InputError("timestamp {0!r} cannot be parsed".format(text))


def snapshot_span(snapshot: dict, now: datetime):
    """Return (start, end) of one snapshot task; progressing -> open end."""
    start = _api_time(snapshot.get("StartTime") or snapshot.get("CreationTime")) or now
    status = str(snapshot.get("Status") or "").lower()
    if status == SNAPSHOT_STATUS_PROGRESSING:
        return start, None
    end = _api_time(snapshot.get("EndTime")) or start
    return start, end


def _api_time(text):
    value = (text or "").strip()
    if not value:
        return None
    try:
        return parse_utc(value)
    except InputError:
        return None


def windows_overlap(a_start: datetime, a_end, b_start: datetime, b_end) -> bool:
    """True when [a_start, a_end or b_end] intersects [b_start, b_end or now]."""
    left = a_start
    right = a_end if a_end is not None else b_end
    other_left = b_start
    other_right = b_end if b_end is not None else right
    return left <= other_right and other_left <= right


def datapoint_summary(points: list) -> dict:
    """Summarize CloudMonitor datapoints: count, latest, max, avg (Average/Maximum)."""
    values = []
    latest_value = None
    latest_ts = -1
    for point in points:
        for field in ("Average", "Maximum", "Value"):
            raw = point.get(field)
            if raw is None:
                continue
            try:
                number = float(raw)
            except (TypeError, ValueError):
                continue
            values.append(number)
            timestamp = int(point.get("timestamp") or 0)
            if timestamp >= latest_ts:
                latest_ts, latest_value = timestamp, number
            break
    if not values:
        return {"count": 0, "latest": None, "max": None, "avg": None}
    return {
        "count": len(values),
        "latest": latest_value,
        "max": max(values),
        "avg": sum(values) / len(values),
    }


def ceiling_reference(type_record: dict) -> dict:
    """Collect numeric storage-perf fields from one DescribeInstanceTypes record.

    The scan is deliberately narrow: only an IOPS-named number, or a
    bandwidth-style number explicitly about disks or storage, counts as a
    candidate ceiling. Local-disk inventory fields (amount/quantity/category)
    and network bandwidth fields are excluded so no unrelated number can be
    misread as an I/O ceiling. This package never invents a ceiling number.
    """
    found = {}
    for key, value in (type_record or {}).items():
        lowered = key.lower()
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        if any(ban in lowered for ban in ("amount", "quantity", "category", "count", "number")):
            continue
        if "iops" in lowered:
            found[key] = value
        elif ("disk" in lowered or "storage" in lowered) and ("bps" in lowered or "bandwidth" in lowered):
            found[key] = value
    return found


def classify(overlapping: int, active: int, io_at_ceiling, gaps: list) -> str:
    """Decision tree of the tier, as a testable pure function."""
    if gaps and not overlapping:
        return VERDICT_EVIDENCE_INSUFFICIENT
    if overlapping == 0:
        return VERDICT_NOT_SNAPSHOT
    if io_at_ceiling:
        return VERDICT_SNAPSHOT_AMPLIFIER
    return VERDICT_SNAPSHOT_CORRELATED


def metric_key_matches(metric_name: str, ceiling_key: str) -> bool:
    """Pair a CMS metric with a candidate instance-type ceiling field."""
    metric = metric_name.lower()
    field = ceiling_key.lower()
    if "iops" in metric and "iops" in field:
        return True
    if metric.endswith("bps") and ("bps" in field or "storage" in field):
        return True
    return False


def validate_pattern(value: str, pattern: str, label: str) -> str:
    text = (value or "").strip()
    if not re.match(pattern, text):
        raise InputError("{0} {1!r} does not look like a valid identifier".format(label, value))
    return text


# Inline boundary assertions (normal / boundary / invalid) for the pure logic.
_now = datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc)
_t1 = parse_utc("2026-02-10T10:00:00Z")
_t2 = parse_utc("2026-02-10T11:00Z")
assert _t1 < _t2
# an explicit offset must be converted to UTC, not stripped (18:00+08 == 10:00Z)
assert parse_utc("2026-02-10T18:00:00+08:00") == _t1
assert snapshot_span({"Status": "accomplished", "StartTime": "2026-02-10T10:00:00Z",
                      "EndTime": "2026-02-10T10:30:00Z"}, _now)[1] == parse_utc("2026-02-10T10:30Z")
assert snapshot_span({"Status": "progressing", "CreationTime": "2026-02-10T10:00:00Z"},
                     _now)[1] is None
assert windows_overlap(_t1, _t2, parse_utc("2026-02-10T10:30Z"), _now)
assert not windows_overlap(_t1, _t2, parse_utc("2026-02-10T11:30Z"), _now)
# open-ended task overlap is decided by the other window's bounds
assert windows_overlap(_t1, None, _t2, _now)
assert datapoint_summary([{"timestamp": 1, "Average": "10"}, {"timestamp": 2, "Average": 30}]) == \
    {"count": 2, "latest": 30.0, "max": 30.0, "avg": 20.0}
assert datapoint_summary([])["count"] == 0
assert classify(0, 0, False, []) == VERDICT_NOT_SNAPSHOT
assert classify(2, 1, True, []) == VERDICT_SNAPSHOT_AMPLIFIER
assert classify(1, 0, False, []) == VERDICT_SNAPSHOT_CORRELATED
assert classify(0, 0, None, ["read failed"]) == VERDICT_EVIDENCE_INSUFFICIENT
assert metric_key_matches("DiskWriteBPS", "StorageBandwidth") and \
    not metric_key_matches("DiskReadIOPS", "CpuCoreCount")
assert ceiling_reference({"LocalStorageAmount": 1, "VmIOPS": 110000,
                          "InstanceBandwidthRx": 1024, "CpuCoreCount": 4}) == {"VmIOPS": 110000}
assert ceiling_reference({}) == {}
try:
    parse_utc("10.02.2026")
    raise AssertionError("parse_utc must reject non-ISO input")
except InputError:
    pass


# ---------------------------------------------------------------------------
# Shared report pieces
# ---------------------------------------------------------------------------

def _fmt_time(moment) -> str:
    if not moment:
        return "in progress (open-ended)"
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _print_evidence_source(lines: list) -> None:
    lines.append("")
    lines.append("## Evidence sources")
    lines.append("")
    for product, action in sorted(CLOUD_READ_ACTIONS):
        lines.append("- {0} {1} (API version declared in related_apis.yaml)".format(product, action))


def _print_degradations(lines: list, warnings: list) -> None:
    lines.append("")
    lines.append("## Graceful Degradation Log")
    lines.append("")
    if warnings:
        for item in warnings:
            lines.append("- [DEGRADE] {0}".format(item))
    else:
        lines.append("- none: every planned evidence call returned")


def _handoff_lines(keyword: str = "") -> list:
    from _constants import HANDOFFS
    lines = []
    for symptom, target in HANDOFFS:
        if not keyword or keyword.lower() in symptom.lower():
            lines.append("- {0} -> {1}".format(symptom, target))
    return lines


# ---------------------------------------------------------------------------
# diagnose
# ---------------------------------------------------------------------------

def cmd_diagnose(args) -> int:
    _cli.check_cli_available()
    session_id = _cli.new_session_id()
    warnings: list = []
    report: list = []
    auto_filled: list = []
    now = datetime.now(timezone.utc)

    region_id = validate_pattern(args.region_id, REGION_ID_PATTERN, "region id")
    instance_id = validate_pattern(args.instance_id, INSTANCE_ID_PATTERN, "instance id") \
        if args.instance_id else ""
    disk_id = validate_pattern(args.disk_id, DISK_ID_PATTERN, "disk id") if args.disk_id else ""
    if not instance_id and not disk_id:
        raise InputError("pass --instance-id or --disk-id (never guessed)")

    # Symptom window: default = last N hours, always declared.
    if args.window_end:
        window_end = parse_utc(args.window_end)
    else:
        window_end = now
        auto_filled.append("window-end defaulted to the run time {0}".format(_fmt_time(now)))
    if args.window_start:
        window_start = parse_utc(args.window_start)
    else:
        window_start = window_end - timedelta(hours=DEFAULT_SYMPTOM_WINDOW_HOURS)
        auto_filled.append("window-start defaulted to {0} hours before the window end"
                           .format(DEFAULT_SYMPTOM_WINDOW_HOURS))
    if window_start >= window_end:
        raise InputError("window-start must be earlier than window-end")

    report.append("# ECS snapshot I/O impact diagnosis")
    report.append("")
    report.append("- session-id: {0}".format(session_id))
    report.append("- region: {0}".format(region_id))
    report.append("- symptom window (UTC): {0} .. {1}".format(
        _fmt_time(window_start), _fmt_time(window_end)))
    if args.symptom:
        report.append("- customer symptom wording: {0}".format(
            _cli.mask_credentials(args.symptom)[:200]))

    # Identity label (soft; degrade only).
    account_id, identity_error = _cli.resolve_account_id(session_id=session_id,
                                                         profile=args.profile)
    if identity_error:
        _cli.warn(warnings, "identity label unavailable: {0}".format(identity_error))
    else:
        report.append("- account (auto-derived via the STS identity check): {0}".format(
            account_id or "not returned"))
        auto_filled.append("account id auto-derived from the default credential chain")

    evidence = {"instance": {}, "disks": [], "snapshots": [], "instance_type": {},
                "ceilings": {}, "metrics": {}}

    # Disk-only targeting: resolve the owning instance from the disk record.
    if not instance_id and disk_id:
        payload, error = _cli.call_soft(
            ECS, "DescribeDisks",
            {"RegionId": region_id, "DiskIds": json.dumps([disk_id])},
            session_id=session_id, profile=args.profile, timeout=args.timeout,
            warnings=warnings,
        )
        for disk in _cli.as_list(payload or {}, "Disks", "Disk"):
            attached = disk.get("InstanceId") or ""
            if isinstance(attached, list):
                attached = attached[0] if attached else ""
            if attached:
                instance_id = str(attached)
                break
        if not instance_id:
            print("\n".join(report))
            print("- The disk {0} returned no attached instance in this region, and the "
                  "symptom must be correlated to an instance's snapshot tasks.".format(disk_id))
            print(STATUS_FAIL)
            print("NEXT_ACTION: ask the customer which instance the disk is attached to "
                  "(console disk list shows the attachment), then re-run with --instance-id.")
            return 2
        report.append("- instance resolved from the disk attachment: {0}".format(instance_id))
        auto_filled.append("instance id derived from DescribeDisks attachment of {0}".format(disk_id))

    # Step 1: instance context.
    payload, error = _cli.call_soft(
        ECS, "DescribeInstances",
        {"RegionId": region_id, "InstanceIds": json.dumps([instance_id])},
        session_id=session_id, profile=args.profile, timeout=args.timeout,
        warnings=warnings,
    )
    instances = _cli.as_list(payload or {}, "Instances", "Instance")
    if error or not instances:
        print("\n".join(report))
        print("- instance lookup failed or returned nothing: {0}".format(
            error or "no record for {0} in {1}".format(instance_id, region_id)))
        print(STATUS_FAIL)
        print("NEXT_ACTION: confirm the instance id and region with the customer; this "
              "skill only sees resources of the current credential and region.")
        return 2
    instance = instances[0]
    evidence["instance"] = {
        "InstanceId": instance.get("InstanceId"),
        "Status": instance.get("Status"),
        "InstanceType": instance.get("InstanceType"),
        "ZoneId": instance.get("ZoneId"),
        "InstanceNetworkType": instance.get("InstanceNetworkType"),
    }
    report.append("- instance: {0} (status {1}, type {2}, zone {3})".format(
        instance.get("InstanceId") or "not returned",
        instance.get("Status") or "not returned",
        instance.get("InstanceType") or "not returned",
        instance.get("ZoneId") or "not returned"))
    os_name = str(_cli.dig(instance, "OSName") or _cli.dig(instance, "OSType") or "").lower()

    # Step 2: disks of the instance.
    disk_params = {"RegionId": region_id, "InstanceId": instance_id}
    disks, paging = _cli.paginate(
        ECS, "DescribeDisks", disk_params, "Disks", session_id, warnings,
        profile=args.profile, timeout=args.timeout,
    )
    for disk in disks:
        evidence["disks"].append({
            "DiskId": disk.get("DiskId"),
            "Type": disk.get("Type"),
            "Category": disk.get("Category"),
            "Size": disk.get("Size"),
            "Status": disk.get("Status"),
            "Device": disk.get("Device"),
        })
    report.append("")
    report.append("## Disks of the instance ({0})".format(paging))
    report.append("")
    if evidence["disks"]:
        report.append("| disk | role | category | size (GiB) | status | device |")
        report.append("|---|---|---|---|---|---|")
        for disk in evidence["disks"]:
            report.append("| {DiskId} | {Type} | {Category} | {Size} | {Status} | {Device} |".format(
                **{key: (disk.get(key) if disk.get(key) is not None else "not returned")
                   for key in ("DiskId", "Type", "Category", "Size", "Status", "Device")}))
    else:
        report.append("- no disk rows returned")

    # Step 3: snapshot tasks (the correlation core).
    snap_params = {"RegionId": region_id}
    if disk_id:
        snap_params["DiskId"] = disk_id
    else:
        snap_params["InstanceId"] = instance_id
    snapshots, snap_paging = _cli.paginate(
        ECS, "DescribeSnapshots", snap_params, "Snapshots", session_id, warnings,
        profile=args.profile, timeout=args.timeout,
    )
    scan_floor = now - timedelta(days=SNAPSHOT_SCAN_DAYS)
    overlapping_snaps = []
    for snap in snapshots:
        created = _api_time(snap.get("CreationTime"))
        if created and created < scan_floor:
            continue
        start, end = snapshot_span(snap, now)
        overlaps = windows_overlap(start, end, window_start, window_end)
        record = {
            "SnapshotId": snap.get("SnapshotId"),
            "DiskId": snap.get("SourceDiskId") or snap.get("DiskId") or "not returned",
            "Status": snap.get("Status"),
            "Progress": snap.get("Progress"),
            "CreationTime": snap.get("CreationTime"),
            "StartTime": snap.get("StartTime"),
            "EndTime": snap.get("EndTime"),
            "SnapshotName": snap.get("SnapshotName"),
            "SourceDiskType": snap.get("SourceDiskType"),
            "span": (start, end),
            "overlaps": overlaps,
        }
        evidence["snapshots"].append(record)
        if overlaps:
            overlapping_snaps.append(record)
    active_snaps = [s for s in overlapping_snaps
                    if str(s.get("Status") or "").lower() == SNAPSHOT_STATUS_PROGRESSING]

    report.append("")
    report.append("## Snapshot tasks in the scan range ({0}, last {1} days)".format(
        snap_paging, SNAPSHOT_SCAN_DAYS))
    report.append("")
    if evidence["snapshots"]:
        report.append("| snapshot | source disk | status | progress | start | end | overlaps window |")
        report.append("|---|---|---|---|---|---|---|")
        for snap in evidence["snapshots"]:
            start, end = snap["span"]
            report.append("| {0} | {1} | {2} | {3} | {4} | {5} | {6} |".format(
                snap.get("SnapshotId") or "not returned",
                snap.get("DiskId"), snap.get("Status") or "not returned",
                snap.get("Progress") or "not returned",
                _fmt_time(start), _fmt_time(end) if end else "open",
                "YES" if snap["overlaps"] else "no"))
    else:
        report.append("- no snapshot rows returned for this instance/disk")

    # Step 4: instance-type ceiling fields (generic scan, no invented numbers).
    instance_type = str(instance.get("InstanceType") or "")
    if instance_type:
        payload, error = _cli.call_soft(
            ECS, "DescribeInstanceTypes", {"RegionId": region_id, "InstanceTypes.1": instance_type},
            session_id=session_id, profile=args.profile, timeout=args.timeout,
            warnings=warnings,
        )
        records = _cli.as_list(payload or {}, "InstanceTypes", "InstanceType")
        if records:
            evidence["instance_type"] = {
                key: value for key, value in records[0].items()
                if isinstance(value, (str, int, float, bool))
            }
            evidence["ceilings"] = ceiling_reference(records[0])
    report.append("")
    report.append("## Storage performance context")
    report.append("")
    if evidence["ceilings"]:
        for key, value in sorted(evidence["ceilings"].items()):
            report.append("- instance-type field `{0}` returned by the API: {1}".format(key, value))
    else:
        report.append("- DescribeInstanceTypes returned no numeric storage-ceiling field for "
                      "this instance type; ceilings must be read from the block-storage "
                      "performance page of the console before any numeric statement.")
    for disk in evidence["disks"]:
        profile_note = CATEGORY_PROFILE.get(str(disk.get("Category") or ""), "category not in "
                                            "the built-in table; report it as returned")
        report.append("- disk {0} ({1} GiB): {2}".format(
            disk.get("DiskId"), disk.get("Size"), profile_note))

    # Step 5: CloudMonitor readings inside the symptom window.
    wanted = [m.strip() for m in (args.metrics or "").split(",") if m.strip()] \
        or [name for name, _, _ in CMS_METRICS]
    descriptions = {name: desc for name, desc, _ in CMS_METRICS}
    dims = [{"instanceId": instance_id}]
    if disk_id:
        dims[0]["diskId"] = disk_id
        auto_filled.append("diskId dimension included because --disk-id was given; drop "
                           "--disk-id to fall back to the instance-level series")
    for metric in wanted:
        payload, error = _cli.call_soft(
            CMS, "DescribeMetricLast",
            {"Namespace": args.namespace or CMS_NAMESPACE_ECS, "MetricName": metric,
             "Dimensions": json.dumps(dims), "Period": CMS_PERIOD_SECONDS,
             "Length": CMS_LENGTH,
             "StartTime": _fmt_time(window_start), "EndTime": _fmt_time(window_end)},
            session_id=session_id, profile=args.profile, timeout=args.timeout,
            warnings=warnings,
        )
        if error:
            evidence["metrics"][metric] = {"error": error}
            continue
        points = _cli.parse_datapoints(payload)
        evidence["metrics"][metric] = datapoint_summary(points)
    report.append("")
    report.append("## CloudMonitor readings inside the symptom window")
    report.append("")
    report.append("| metric | points | max | avg | latest |")
    report.append("|---|---|---|---|---|")
    for metric, data in evidence["metrics"].items():
        if "error" in data:
            report.append("| {0} | read failed: {1} | - | - | - |".format(
                metric, _cli.mask_credentials(data["error"])[:120]))
            continue
        report.append("| {0} ({1}) | {2} | {3} | {4:.1f} | {5} |".format(
            metric, descriptions.get(metric, "caller-provided metric"), data["count"],
            data["max"] if data["max"] is not None else float("nan"),
            data["avg"] if data["count"] else float("nan"),
            data["latest"] if data["latest"] is not None else "-")
            if data["count"] else "| {0} | 0 | - | - | - |".format(metric))
    if not any(data.get("count", 0) for data in evidence["metrics"].values() if "error" not in data):
        warnings_note = ("no datapoints came back: either nothing was produced in the window, "
                         "the metric names or dimensions do not match the console series, or "
                         "CloudMonitor is not collecting; the report must not conclude from this alone")
        _cli.warn(warnings, warnings_note)

    # Verdict.
    io_at_ceiling = False
    ratio_notes = []
    for metric, data in evidence["metrics"].items():
        if "error" in data or not data.get("count"):
            continue
        for key, value in evidence["ceilings"].items():
            if metric_key_matches(metric, key) and value:
                ratio = (data["max"] or 0) / float(value)
                ratio_notes.append("{0} peak reached {1:.0f}% of returned field {2}".format(
                    metric, 100 * ratio, key))
                if ratio >= NEAR_CEILING_RATIO:
                    io_at_ceiling = True
    gaps = [w for w in warnings if w.startswith(("degraded call", "identity"))] \
        + ([ "no datapoints in window"] if not any(
            d.get("count", 0) for d in evidence["metrics"].values() if "error" not in d) else [])
    verdict = classify(len(overlapping_snaps), len(active_snaps), io_at_ceiling, gaps)

    report.append("")
    report.append("## Verdict")
    report.append("")
    report.append("- verdict: {0}".format(verdict))
    for code, text in ROOT_CAUSE_TAXONOMY:
        report.append("- branch {0}: {1}".format(code, text))
    if verdict == VERDICT_SNAPSHOT_AMPLIFIER:
        report.append("- matched branches: B1 (see the tree above). " + "; ".join(ratio_notes))
    elif verdict == VERDICT_SNAPSHOT_CORRELATED:
        report.append("- matched branches: B2. Correlation proven, causation not: guest-side "
                      "latency evidence is missing.")
    elif verdict == VERDICT_NOT_SNAPSHOT:
        report.append("- matched branches: B3. No snapshot task overlaps the symptom window.")
    else:
        report.append("- matched branches: B4. The evidence chain has a named gap; see the "
                      "degradation log.")

    report.append("")
    report.append("## Guidance (manual console steps only)")
    report.append("")
    if verdict in (VERDICT_SNAPSHOT_AMPLIFIER, VERDICT_SNAPSHOT_CORRELATED):
        report.append("- Move manual snapshot requests away from the business peak; take them "
                      "when write activity is naturally low.")
        report.append("- Avoid starting snapshots on several disks of one instance at the same "
                      "time; one disk at a time spreads the read pressure.")
        report.append("- Review the auto snapshot policy schedule for this instance: "
                      "{0}. Adjusting the schedule is a console change performed by the "
                      "customer; this skill neither changes it nor promises a numeric "
                      "throttling limit (none is verified in this package).".format(
                          CONSOLE_ENTRIES["auto_snapshot_policy"]))
        report.append("- Before a customer-performed change, an optional restore point can be "
                      "taken with the gated snapshot-backup subcommand (billable; deletion "
                      "afterwards is a manual console step).")
    elif verdict == VERDICT_NOT_SNAPSHOT:
        handoffs = _handoff_lines()
        report.append("- The symptom is not attributable to snapshot activity in this window. "
                      "Route with the hand-off map (references/handoffs.md):")
        for line in handoffs:
            report.append("  {0}".format(line))
    else:
        report.append("- Close the named evidence gap first (ask the customer for the console "
                      "monitoring screenshot, or confirm instance/disk ids) before any "
                      "attribution sentence is shown to the customer.")
    report.append("")
    report.append("Official documentation cited by this package:")
    for title, url in OFFICIAL_DOCS:
        report.append("- {0}: {1}".format(title, url))

    report.append("")
    report.append("## Declared parameters and assumptions")
    report.append("")
    report.append("- region {0} and target {1} were taken from the caller (never guessed)".format(
        region_id, disk_id or instance_id))
    for item in auto_filled:
        report.append("- auto-filled: {0}".format(item))
    report.append("- timestamps are interpreted as UTC; API times are echoed unchanged")
    report.append("- monitoring values come from the CloudMonitor window given; DescribeMetricLast "
                  "reports within the requested StartTime/EndTime only")

    _print_evidence_source(report)
    _print_degradations(report, warnings)
    report.append("")
    report.append("## Limitations (required disclosures)")
    report.append("")
    report.append("- No cloud API measures block-device latency inside the guest; the whitelisted "
                  "inspection commands report capacity and file-handle context only. For a "
                  "latency figure, ask the customer to run an I/O tool themselves and paste it.")
    report.append("- Snapshot concurrency and throttling numbers are NOT promised: this package "
                  "contains no verified official snapshot-performance document.")
    report.append("- Results only cover resources visible to the current credential in "
                  "{0}.".format(region_id))

    status = STATUS_OK
    next_action = ("NEXT_ACTION: relay the verdict and the guidance above to the customer; "
                   "if they want a restore point first, run snapshot-backup with the "
                   "confirmation flow.")
    if verdict == VERDICT_NOT_SNAPSHOT:
        next_action = "NEXT_ACTION: hand off per references/handoffs.md (no snapshot overlap found)."
    if gaps or verdict == VERDICT_EVIDENCE_INSUFFICIENT:
        status = STATUS_DEGRADED
        next_action = ("NEXT_ACTION: state the gaps from the degradation log and ask the "
                       "customer for the missing reading; do not conclude across the gap.")

    if args.json:
        payload_out = {
            "session_id": session_id,
            "region": region_id,
            "instance_id": instance_id,
            "window": {"start": _fmt_time(window_start), "end": _fmt_time(window_end)},
            "evidence": json.loads(json.dumps(evidence, default=str)),
            "verdict": verdict,
            "degradations": warnings,
            "auto_filled": auto_filled,
            "status": status.split(" ", 1)[1],
        }
        print(json.dumps(payload_out, indent=2, ensure_ascii=False))
    else:
        print("\n".join(report))
    print("")
    print(status)
    print(next_action)
    return 0 if status != STATUS_FAIL else 2


# ---------------------------------------------------------------------------
# guest-check (Class 2, confirmation-gated)
# ---------------------------------------------------------------------------

def _whitelist_refusal(command_key: str) -> str:
    """Refusal wording for anything outside the frozen command set."""
    lowered = command_key.strip().lower()
    for tool in REFUSED_GUEST_TOOLS:
        if tool in lowered:
            return ("`{0}` measures live I/O state but is outside this skill's frozen "
                    "command set; it is never dispatched here. Ask the customer to run it "
                    "themselves and paste the output.".format(tool))
    for token in REJECTED_COMMAND_TOKENS:
        if re.search(r"\b{0}\b".format(re.escape(token)), lowered):
            return ("`{0}` carries side effects and is rejected outright; this skill only "
                    "guides manual steps for changes.".format(token))
    return ("command key {0!r} is not on the frozen whitelist in scripts/_constants.py; "
            "only the listed inspection commands may be delivered.".format(command_key))


def _assemble_command(args) -> str:
    entry = GUEST_COMMANDS.get(args.command_key)
    if not entry:
        raise InputError(_whitelist_refusal(args.command_key))
    if entry["os"] == "windows" and not WINDOWS_GUEST_CHANNEL_ENABLED:
        raise InputError("the Windows guest channel is not enabled for this tier; guidance "
                         "stays manual (see references/guest-inspection-commands.md)")
    content = entry["command"]
    if entry["needs_path"]:
        path = (args.path or "").strip()
        if not re.match(LINUX_PATH_PATTERN, path) or ".." in path:
            raise InputError("path {0!r} is required for this command key and must be a plain "
                             "absolute path without traversal".format(args.path))
        content = "{0} {1}".format(content, path)
    else:
        if args.path:
            raise InputError("command key {0!r} takes no path".format(args.command_key))
    for char in SHELL_METACHARACTERS:
        if char in content:
            raise InputError("assembled command rejected for shell metacharacters")
    return content


def cmd_guest_check(args) -> int:
    _cli.check_cli_available()
    session_id = _cli.new_session_id()
    warnings: list = []
    region_id = validate_pattern(args.region_id, REGION_ID_PATTERN, "region id")
    instance_id = validate_pattern(args.instance_id, INSTANCE_ID_PATTERN, "instance id")
    content = _assemble_command(args)

    print("# Confirmation required before any in-guest execution")
    print("")
    print("- Target instance: `{0}` in `{1}`".format(instance_id, region_id))
    print("- Channel: Cloud Assistant command delivery, ONE whitelisted command per call")
    print("- Command that would run: `{0}`".format(content))
    print("- What it returns: {0}".format(GUEST_COMMANDS[args.command_key]["purpose"]))
    print("- State change: none - the command only prints information; nothing is rolled back")
    print("- Tier honesty note: this reading is capacity/file context, NOT a block-device "
          "latency measurement")
    print("- Blast radius: one inspection command inside this single instance")
    print("")

    if not args.confirm or args.confirm.strip() != instance_id:
        print("Nothing has been executed.")
        print(STATUS_DEGRADED)
        print("NEXT_ACTION: show the block above to the customer; after an explicit yes for "
              "this one command, re-run identically with `--confirm {0}`. The confirmation "
              "covers this command only.".format(instance_id))
        return 0

    payload, error = _cli.call_soft(
        ECS, "RunCommand",
        {"RegionId": region_id, "Type": RUN_COMMAND_LINUX_TYPE, "CommandContent": content,
         "InstanceId.1": instance_id, "Timeout": RUN_COMMAND_TIMEOUT_SECONDS},
        session_id=session_id, timeout=args.timeout, profile=args.profile,
        gated=True, warnings=warnings,
    )
    if error:
        print("- Delivery failed: {0}".format(error))
        print("- Usual causes: the Cloud Assistant agent is missing or offline on this "
              "instance, the region does not match, or the caller lacks the delivery "
              "permission (NoPermission / ImplicitDeny).")
        print(STATUS_DEGRADED)
        print("NEXT_ACTION: ask the customer to run `{0}` themselves and paste the output; "
              "never trade an instance password for it.".format(content))
        return 0

    invoke_id = _cli.dig(payload or {}, "InvokeId")
    print("- invocation id: {0}".format(invoke_id or "not returned"))
    output_text = None
    for attempt in range(INVOCATION_POLL_ATTEMPTS):
        time.sleep(INVOCATION_POLL_INTERVAL_SECONDS if attempt else 0)
        payload, error = _cli.call_soft(
            ECS, "DescribeInvocations",
            {"RegionId": region_id, "InvokeId": invoke_id},
            session_id=session_id, timeout=args.timeout, profile=args.profile,
            warnings=warnings,
        )
        if error:
            continue
        invocations = _cli.as_list(payload or {}, "Invocations", "Invocation")
        if invocations:
            inner = _cli.as_list(invocations[0], "InvokeInstances", "InvokeInstance")
            record = inner[0] if inner else invocations[0]
            output_text = _cli.dig(record, "Output")
            status = _cli.dig(record, "InvocationStatus") or "unknown"
            print("- invocation status: {0} (recorded results, poll {1}/{2})".format(
                status, attempt + 1, INVOCATION_POLL_ATTEMPTS))
            if output_text or status in ("Failed", "Timeout", "Stopped", "Aborted"):
                break
    if not output_text:
        print(STATUS_DEGRADED)
        print("NEXT_ACTION: the command was delivered but no output was readable; ask the "
              "customer to paste the result of `{0}` or check that the Cloud Assistant "
              "agent is online.".format(content))
        return 0

    try:
        decoded = base64.b64decode(str(output_text)).decode("utf-8", "replace")
    except (binascii.Error, ValueError):
        decoded = str(output_text)
    print("")
    print("## Command output")
    print("")
    print("```")
    for line in _cli.mask_credentials(decoded).splitlines():
        print(line)
    print("```")
    print("")
    print(STATUS_OK)
    print("NEXT_ACTION: combine this context reading with the diagnose evidence; it does "
          "not measure I/O latency by itself.")
    return 0


# ---------------------------------------------------------------------------
# snapshot-backup (Class 3, confirmation-gated)
# ---------------------------------------------------------------------------

def cmd_snapshot_backup(args) -> int:
    _cli.check_cli_available()
    session_id = _cli.new_session_id()
    warnings: list = []
    region_id = validate_pattern(args.region_id, REGION_ID_PATTERN, "region id")
    disk_id = validate_pattern(args.disk_id, DISK_ID_PATTERN, "disk id")

    print("# Confirmation required before creating a snapshot")
    print("")
    print("- Target disk: `{0}` in `{1}`".format(disk_id, region_id))
    print("- Action: one restore-point snapshot of this single disk")
    print("- Effect: adds a billable snapshot resource; the disk itself is not touched")
    print("- Reversibility: the snapshot can be deleted afterwards IN THE CONSOLE by the "
      "customer; this skill never deletes anything")
    print("- Billing: snapshots are billed for stored size; temporary restore points should "
      "be cleaned up manually after the change")
    print("- This tier performs no cleanup actions; a snapshot here only precedes a "
      "customer-performed change on request")
    print("")

    if not args.confirm or args.confirm.strip() != disk_id:
        print("Nothing has been executed.")
        print(STATUS_DEGRADED)
        print("NEXT_ACTION: show the block above to the customer; after an explicit yes, "
              "re-run identically with `--confirm {0}`. The confirmation covers this one "
              "snapshot only.".format(disk_id))
        return 0

    payload, error = _cli.call_soft(
        ECS, "CreateSnapshot", {"RegionId": region_id, "DiskId": disk_id},
        session_id=session_id, timeout=args.timeout, profile=args.profile,
        gated=True, warnings=warnings,
    )
    if error:
        print("- The snapshot request failed: {0}".format(error))
        print(STATUS_DEGRADED)
        print("NEXT_ACTION: report the exact code; a NoPermission / ImplicitDeny here means "
              "the customer's own credentials lack the write right - stop and hand the "
              "manual console step to the customer instead.")
        return 0

    snapshot_id = str(_cli.dig(payload or {}, "SnapshotId") or "")
    print("- snapshot request accepted: {0}".format(snapshot_id or "id not returned"))
    if snapshot_id and re.match(SNAPSHOT_ID_PATTERN, snapshot_id):
        verify, error = _cli.call_soft(
            ECS, "DescribeSnapshots",
            {"RegionId": region_id, "SnapshotIds": json.dumps([snapshot_id])},
            session_id=session_id, timeout=args.timeout, profile=args.profile,
            warnings=warnings,
        )
        rows = _cli.as_list(verify or {}, "Snapshots", "Snapshot")
        if rows:
            print("- verification read: status {0}, progress {1}".format(
                rows[0].get("Status") or "not returned",
                rows[0].get("Progress") or "not returned"))
        elif error:
            print("- verification read failed: {0}".format(error))
    print("")
    print(STATUS_OK)
    print("NEXT_ACTION: tell the customer the snapshot is progressing; the change itself "
          "stays a manual console step, and removing the restore point afterwards is "
          "manual too (billing pointer: {0}).".format(CONSOLE_ENTRIES["snapshot_list"]))
    return 0


# ---------------------------------------------------------------------------
# Argument wiring
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="snapshot_io_diagnosis.py",
        description="ECS snapshot I/O impact diagnosis: window correlation, IO headroom, "
                    "confirmation-gated guest context reads and restore points.",
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--region-id", required=True, help="Region of the resource (never guessed)")
    common.add_argument("--profile", default=None, help="Optional aliyun CLI profile name")
    common.add_argument("--timeout", type=int, default=30, help="Per-call timeout in seconds")

    p_diag = sub.add_parser("diagnose", parents=[common],
                            help="automatic cloud inspection chain and verdict")
    p_diag.add_argument("--instance-id", default="", help="ECS instance id (i-...)")
    p_diag.add_argument("--disk-id", default="", help="disk id (d-...) to narrow the scan")
    p_diag.add_argument("--window-start", default="", help="symptom window start, ISO-8601 UTC")
    p_diag.add_argument("--window-end", default="", help="symptom window end, ISO-8601 UTC")
    p_diag.add_argument("--symptom", default="", help="customer wording, echoed as evidence")
    p_diag.add_argument("--namespace", default="", help="CloudMonitor namespace override")
    p_diag.add_argument("--metrics", default="",
                        help="comma-separated CloudMonitor metric names (default: the four "
                             "disk read/write BPS/IOPS metrics)")
    p_diag.add_argument("--json", action="store_true", help="structured JSON report")
    p_diag.set_defaults(func=cmd_diagnose)

    p_guest = sub.add_parser("guest-check", parents=[common],
                             help="deliver ONE whitelisted inspection command (gated)")
    p_guest.add_argument("--instance-id", required=True, help="ECS instance id (i-...)")
    p_guest.add_argument("--command-key", required=True,
                         help="key from the frozen whitelist (see references/guest-inspection-commands.md)")
    p_guest.add_argument("--path", default="", help="absolute path for path-taking keys")
    p_guest.add_argument("--confirm", default="",
                         help="must repeat the exact instance id after the customer approved "
                              "this one command")
    p_guest.set_defaults(func=cmd_guest_check)

    p_snap = sub.add_parser("snapshot-backup", parents=[common],
                            help="create ONE restore-point snapshot (gated)")
    p_snap.add_argument("--disk-id", required=True, help="disk id (d-...) to snapshot")
    p_snap.add_argument("--confirm", default="",
                        help="must repeat the exact disk id after the customer approved "
                              "this one snapshot")
    p_snap.set_defaults(func=cmd_snapshot_backup)
    return parser


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _run_selftest()
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except InputError as exc:
        print(_cli.mask_credentials(str(exc)))
        print(STATUS_FAIL)
        print("NEXT_ACTION: fix the input (ids, window, or the refused command) and re-run; "
              "this skill never widens its own whitelist.")
        return 2
    except Exception as exc:  # defensive: never leak a raw traceback or secret
        print("[FAIL] unexpected error: {0}".format(_cli.mask_credentials(exc)))
        print(STATUS_FAIL)
        print("NEXT_ACTION: report the session id above; re-run once, and if it repeats, "
              "escalate with the session id instead of improvising other commands.")
        return 1


# ---------------------------------------------------------------------------
# Offline regression lock (no cloud, no subprocess): run with
#   python3 scripts/snapshot_io_diagnosis.py --selftest
# Locks the attribution decision core: a wrong verdict sends the customer down
# the wrong remediation path (blaming or clearing snapshots wrongly). Invariant
# pinned: an open (progressing) snapshot task overlaps a symptom window exactly
# when it started at or before the window end; the evidence-insufficient branch
# only fires when NO overlap exists; and the ceiling scan never mistakes a
# network-bandwidth or local-disk-count number for a storage ceiling.
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

    def t(h, m=0):
        return datetime(2026, 2, 10, h, m, tzinfo=timezone.utc)

    # --- parse_utc ----------------------------------------------------------
    expect("parse_zulu", parse_utc("2026-02-10T10:00:00Z") == t(10))
    expect("parse_minute", parse_utc("2026-02-10T10:00Z") == t(10))
    expect("parse_offset", parse_utc("2026-02-10T18:00:00+08:00") == t(10))
    for bad in ("10.02.2026", "", "2026-02-10", "yesterday"):
        try:
            parse_utc(bad)
            expect("parse_reject_" + (bad or "empty"), False)
        except InputError:
            expect("parse_reject_" + (bad or "empty"), True)

    # --- _api_time soft version ----------------------------------------------
    expect("api_time_none_on_junk", _api_time("nope") is None
           and _api_time("") is None and _api_time(None) is None)
    expect("api_time_ok", _api_time("2026-02-10T10:00:00Z") == t(10))

    # --- snapshot_span -------------------------------------------------------
    s, e = snapshot_span({"Status": "accomplished",
                          "StartTime": "2026-02-10T10:00:00Z",
                          "EndTime": "2026-02-10T10:30:00Z"}, t(12))
    expect("span_closed", s == t(10) and e == t(10, 30))
    s, e = snapshot_span({"Status": "progressing",
                          "CreationTime": "2026-02-10T10:00:00Z"}, t(12))
    expect("span_open_progressing", s == t(10) and e is None)
    s, e = snapshot_span({"Status": "accomplished"}, t(12))  # no times at all
    expect("span_all_missing_defaults_now", s == t(12) and e == t(12))

    # --- windows_overlap (attribution pivot) --------------------------------
    expect("ov_closed_closed", windows_overlap(t(10), t(11), t(10, 30), t(11, 30)))
    expect("ov_disjoint", not windows_overlap(t(10), t(11), t(12), t(13)))
    expect("ov_touch_boundary", windows_overlap(t(10), t(11), t(11), t(12)))
    # open (progressing) task overlaps iff it started at or before window end
    expect("ov_open_started_after_window",
           not windows_overlap(t(13), None, t(10), t(12)))
    expect("ov_open_running_into_window",
           windows_overlap(t(11), None, t(12), t(13)))
    expect("ov_open_spanning_window",
           windows_overlap(t(10), None, t(11), t(12)))

    # --- datapoint_summary ---------------------------------------------------
    d = datapoint_summary([{"timestamp": 5, "Maximum": 10},
                           {"timestamp": 3, "Average": "8"}, {"Average": "bad"}])
    expect("dp_mixed", d["count"] == 2 and d["latest"] == 10.0
           and d["max"] == 10.0 and abs(d["avg"] - 9.0) < 1e-9)
    expect("dp_empty", datapoint_summary([]) == {"count": 0, "latest": None,
                                                "max": None, "avg": None})

    # --- ceiling_reference (never misread an unrelated number) ---------------
    got = ceiling_reference({"InstanceBandwidthRx": 1024,
                             "LocalStorageAmount": 8, "VmIOPS": 110000,
                             "StorageBandwidth": 2000, "MemorySize": 4096,
                             "CpuCoreCount": 4})
    expect("ceil_iops_and_storage_only",
           got == {"VmIOPS": 110000, "StorageBandwidth": 2000})
    expect("ceil_bool_ignored", ceiling_reference({"Enabled": True, "VmIOPS": 5})
           == {"VmIOPS": 5})
    expect("ceil_empty", ceiling_reference({}) == {} and ceiling_reference(None) == {})

    # --- metric_key_matches --------------------------------------------------
    expect("mkm_iops_iops", metric_key_matches("DiskReadIOPS", "VmIOPS"))
    expect("mkm_bps_storage", metric_key_matches("DiskWriteBPS", "StorageBandwidthMbps"))
    expect("mkm_cross_family_no", not metric_key_matches("DiskWriteBPS", "VmIOPS"))
    expect("mkm_cpu_no", not metric_key_matches("cpu_total", "VmIOPS"))

    # --- classify truth table (verdict priority) -----------------------------
    expect("cls_no_overlap_no_gap", classify(0, 0, False, []) == VERDICT_NOT_SNAPSHOT)
    expect("cls_gap_without_overlap_evidence",
           classify(0, 0, None, ["read failed"]) == VERDICT_EVIDENCE_INSUFFICIENT)
    expect("cls_overlap_beats_gap",
           classify(2, 0, False, ["g"]) == VERDICT_SNAPSHOT_CORRELATED)
    expect("cls_at_ceiling_amplifier",
           classify(1, 1, True, []) == VERDICT_SNAPSHOT_AMPLIFIER)
    expect("cls_overlap_below_ceiling",
           classify(1, 0, False, []) == VERDICT_SNAPSHOT_CORRELATED)
    # invariant: gaps never downgrade a proven overlap to evidence-insufficient
    expect("invariant_overlap_never_evidence_insufficient",
           classify(1, 0, False, ["g"]) != VERDICT_EVIDENCE_INSUFFICIENT
           and classify(3, 2, True, ["g"]) != VERDICT_EVIDENCE_INSUFFICIENT)

    # --- validate_pattern ----------------------------------------------------
    expect("vp_accept", validate_pattern("i-bp1abc", INSTANCE_ID_PATTERN, "id")
           == "i-bp1abc")
    try:
        validate_pattern("i-../etc", INSTANCE_ID_PATTERN, "id")
        expect("vp_reject_traversal", False)
    except InputError:
        expect("vp_reject_traversal", True)

    print(f"--selftest: {len(checked)} checks, "
          f"{'ALL PASS' if rc == 0 else 'FAILURES PRESENT'}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
