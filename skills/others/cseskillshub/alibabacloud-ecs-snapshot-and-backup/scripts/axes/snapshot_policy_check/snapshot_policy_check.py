#!/usr/bin/env python3
"""Single entry point for the ECS snapshot policy check skill.

Every cloud fact in this package comes from here; the agent must run this script
rather than compose CLI calls itself. Sub-commands map to the skill capabilities:

    identity             account provenance tag
    snapshot-status      C1  creation progress / stalled vs queued vs failed
    policy-coverage      C2  disks x policy binding x automatic snapshot evidence
    lifecycle-inventory  C3+C4 copy, archive pre-check, retention and expiry
    invocation-history   C1  Cloud Assistant history behind app-consistent fails
    create-backup        C5  confirmation-gated backup snapshot before a change
    guest-commands       C7  side-effect-free in-instance commands (guided only)
    handoff              C6  symptom outside this skill's scope -> where to go
    check-all            C1+C2+C4 across every region passed in

Ends with the report contract: ``STATUS: OK|DEGRADED|FAIL`` plus ``NEXT_ACTION``.
"""

import argparse
import datetime
import json
import sys
import time

import _cli
import _constants as C
import sts_token


# --------------------------------------------------------------------------
# time helpers
# --------------------------------------------------------------------------

_TIME_FORMATS = ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ", "%Y-%m-%dT%H:%M:%S%z")


def parse_utc(value):
    """Parse an ECS timestamp; return None instead of guessing."""
    if not value:
        return None
    text = str(value).strip()
    for fmt in _TIME_FORMATS:
        try:
            moment = datetime.datetime.strptime(text, fmt)
        except ValueError:
            continue
        if moment.tzinfo is None:
            return moment.replace(tzinfo=datetime.timezone.utc)
        return moment.astimezone(datetime.timezone.utc)
    return None


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def minutes_since(value):
    moment = parse_utc(value) if not isinstance(value, datetime.datetime) else value
    if moment is None:
        return None
    return (now_utc() - moment).total_seconds() / 60.0


def human_minutes(minutes):
    if minutes is None:
        return "unknown"
    if minutes < 90:
        return "{0:.0f} min".format(minutes)
    return "{0:.1f} h".format(minutes / 60.0)


def parse_progress(value):
    """DescribeSnapshots reports progress as a percentage string such as '45%'."""
    if value is None:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if not digits:
        return None
    return max(0, min(100, int(digits)))


def add_days(value, days):
    moment = parse_utc(value)
    if moment is None or days in (None, ""):
        return None
    try:
        return moment + datetime.timedelta(days=int(days))
    except (TypeError, ValueError):
        return None


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ") if moment else "not returned by API"


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------


class Report(object):
    """Accumulates findings, degraded steps and the closing contract lines."""

    def __init__(self, title, as_json=False):
        self.title = title
        self.as_json = as_json
        self.sections = []
        self.assumptions = []
        self.degradations = []
        self.failures = []
        self.next_actions = []
        self.payload = {}

    def section(self, name, lines=None):
        self.sections.append((name, list(lines or [])))

    def assume(self, text):
        self.assumptions.append(text)

    def degrade(self, text):
        self.degradations.append(text)

    def fail(self, text):
        self.failures.append(text)

    def action(self, text):
        if text not in self.next_actions:
            self.next_actions.append(text)

    def status(self):
        if self.failures:
            return C.STATUS_FAIL
        if self.degradations:
            return C.STATUS_DEGRADED
        return C.STATUS_OK

    def render(self):
        if self.as_json:
            body = {
                "skill": C.SKILL_NAME,
                "session_id": _cli.SESSION_ID,
                "title": self.title,
                "status": self.status().replace("STATUS: ", ""),
                "assumptions": self.assumptions,
                "sections": dict(self.sections),
                "degradations": self.degradations,
                "failures": self.failures,
                "next_actions": self.next_actions,
                "data": self.payload,
            }
            return json.dumps(body, indent=2, ensure_ascii=False, sort_keys=True)
        out = [
            "=" * 72,
            "{0}  (skill session {1})".format(self.title, _cli.SESSION_ID),
            "=" * 72,
        ]
        for name, lines in self.sections:
            out.append("\n## {0}".format(name))
            out.extend(lines if lines else ["  (no records returned)"])
        if self.assumptions:
            out.append("\n## Assumptions and auto-filled inputs")
            out.extend(["  - {0}".format(a) for a in self.assumptions])
        if self.degradations:
            out.append("\n## Degraded evidence")
            out.extend(["  - {0}".format(d) for d in self.degradations])
        if self.failures:
            out.append("\n## Blocking failures")
            out.extend(["  - {0}".format(f) for f in self.failures])
        out.append("\n{0}".format(self.status()))
        if self.next_actions:
            out.append("NEXT_ACTION:")
            out.extend(["  1. {0}".format(t) for t in self.next_actions])
        else:
            out.append("NEXT_ACTION: none; the evidence above answers the request.")
        return "\n".join(out)


def row(cols):
    return "  " + " | ".join(str(c) for c in cols)


def summarize(items, limit=15):
    lines = [row(i) for i in items[:limit]]
    if len(items) > limit:
        lines.append(row(["... {0} more, same pattern".format(len(items) - limit)]))
    return lines


# --------------------------------------------------------------------------
# shared API access
# --------------------------------------------------------------------------


def fetch_snapshots(region, **filters):
    params = {"RegionId": region}
    params.update({k: v for k, v in filters.items() if v not in (None, "")})
    return _cli.paginate("DescribeSnapshots", params, "Snapshots.Snapshot")


def fetch_disks(region, instance_id=None, policy_id=None, disk_id=None):
    params = {"RegionId": region}
    if instance_id:
        params["InstanceId"] = instance_id
    if policy_id:
        params["AutoSnapshotPolicyId"] = policy_id
    if disk_id:
        params["DiskIds"] = json.dumps([disk_id])
    return _cli.paginate("DescribeDisks", params, "Disks.Disk")


def fetch_instances(region, instance_id=None):
    params = {"RegionId": region}
    if instance_id:
        params["InstanceIds"] = json.dumps([instance_id])
    return _cli.paginate("DescribeInstances", params, "Instances.Instance")


def field(item, *names):
    """First present key among ``names``; None when the API omitted it."""
    for name in names:
        if isinstance(item, dict) and name in item and item[name] != "":
            return item[name]
    return None


def policy_ids_of(disk):
    """Collect any auto snapshot policy ids the disk response exposes."""
    ids = []
    direct = field(disk, "AutoSnapshotPolicyId")
    if direct:
        ids.append(str(direct))
    associated = disk.get("AssociatedAutoSnapshotPolicy") if isinstance(disk, dict) else None
    if isinstance(associated, dict):
        listed = associated.get("AutoSnapshotPolicyIdList")
        if isinstance(listed, list):
            ids.extend(str(v) for v in listed if v)
    return sorted(set(ids))


def snapshot_sort_key(snap):
    return str(field(snap, "CreationTime") or "")


# --------------------------------------------------------------------------
# C1 snapshot-status
# --------------------------------------------------------------------------


def cmd_snapshot_status(args):
    report = Report("C1 snapshot creation status", args.json)
    report.assume("region(s) queried: {0}".format(", ".join(args.regions)))
    report.assume("look-back window: {0} h".format(args.hours))

    cutoff = now_utc() - datetime.timedelta(hours=args.hours)
    seen = {}
    for region in args.regions:
        try:
            snaps = fetch_snapshots(
                region,
                InstanceId=args.instance_id,
                DiskId=args.disk_id,
                SnapshotIds=args.snapshot_id,
            )
        except _cli.CliError as exc:
            report.fail("DescribeSnapshots in {0}: {1}".format(region, exc))
            report.action(
                "Re-run after the API error clears; no conclusion is drawn without data."
            )
            return report
        for snap in snaps:
            sid = field(snap, "SnapshotId")
            if not sid:
                continue
            created = parse_utc(field(snap, "CreationTime"))
            if created and created < cutoff and not args.snapshot_id:
                continue
            seen[sid] = (region, snap)

    if not seen and not args.snapshot_id:
        report.degrade(
            "No snapshot in the {0} h window. Confirm the region list; this skill "
            "does not enumerate regions on its own.".format(args.hours)
        )
        report.action(
            "Pass every region holding the disk with --regions cn-hangzhou,cn-heyuan,..."
        )
        return report

    in_flight = []  # every snapshot line, whatever its final state
    completed = []
    failed = []
    for sid, (region, snap) in sorted(seen.items(), key=lambda kv: snapshot_sort_key(kv[1][1])):
        status = str(field(snap, "Status") or "unknown")
        progress = parse_progress(field(snap, "Progress"))
        created = field(snap, "CreationTime")
        elapsed = minutes_since(created)
        source_size = field(snap, "SourceDiskSize")
        category = field(snap, "Category", "SnapshotCategory")
        record = {
            "snapshot_id": sid,
            "region": region,
            "status": status,
            "progress_percent": progress,
            "created_utc": created or "not returned by API",
            "age": human_minutes(elapsed),
            "source_disk_id": field(snap, "SourceDiskId"),
            "source_disk_size_gb": source_size,
            "source_disk_type": field(snap, "SourceDiskType"),
            "category": category,
            "retention_days": field(snap, "RetentionDays"),
            "expire_time": field(snap, "ExpireTime"),
            "creation_type": field(snap, "SnapshotType"),
            "snapshot_name": field(snap, "SnapshotName"),
        }
        line = row(
            [
                sid,
                region,
                status,
                "{0}%".format(progress) if progress is not None else "n/a",
                human_minutes(elapsed),
                "{0} GB".format(source_size) if source_size else "n/a",
                field(snap, "SourceDiskId") or "n/a",
            ]
        )
        if status == C.SNAPSHOT_STATUS_FAILED:
            failed.append(record)
            in_flight.append(line + "   <- creation FAILED")
        elif status == C.SNAPSHOT_STATUS_ACCOMPLISHED:
            completed.append(record)
            in_flight.append(line)
        else:
            verdict = classify_progress(progress, elapsed)
            record["verdict"] = verdict
            in_flight.append(line + "   <- " + verdict)
            if verdict.startswith("no observable progress"):
                report.action(
                    "Open a support ticket for {0} quoting snapshot id, instance id "
                    "and creation time; this skill cannot accelerate a queued task.".format(sid)
                )
        report.payload.setdefault("snapshots", []).append(record)

    report.section("Snapshots (id | region | status | progress | age | source size | disk)", in_flight)
    report.section(
        "Completed in window",
        summarize(
            [
                [
                    r["snapshot_id"],
                    r["region"],
                    r["created_utc"],
                    "{0} GB".format(r["source_disk_size_gb"] or "n/a"),
                ]
                for r in completed
            ]
        ),
    )
    if failed:
        report.section(
            "Failed creations - next checks",
            [
                row(
                    [
                        r["snapshot_id"],
                        r["region"],
                        "name may collide or quota reached; see references/error-signals.md",
                    ]
                )
                for r in failed
            ],
        )
        report.degrade("Failure reason code is not returned by DescribeSnapshots.")
        report.action(
            "Read the failure text in the console snapshot list, then compare it with "
            "references/error-signals.md before changing anything."
        )

    if args.polls > 1:
        moved = measure_progress_movement(seen, args)
        report.section(
            "Progress sampled {0} times, {1}s apart".format(args.polls, args.poll_interval),
            moved,
        )

    slow = [r for r in report.payload.get("snapshots", []) if r["status"] == C.SNAPSHOT_STATUS_PROGRESSING]
    if slow:
        report.section(
            "Interpretation",
            [
                "  A percentage that climbs slowly is queueing, not a stuck task: creation "
                "time scales with the data written since the last snapshot and with shared "
                "capacity in the region (evidence: tickets 000ACRF8K2, 000DGRP989).",
                "  Nobody - support included - can accelerate a queued snapshot; the only "
                "lever is creating at an off-peak hour.",
                "  Do not delete a progressing snapshot to 'restart' it: deletion is "
                "irreversible and is performed by the customer in the console.",
                "  See references/snapshot-lifecycle.md for the full decision tree.",
            ],
        )
    return report


def classify_progress(progress, elapsed_minutes):
    if progress is None:
        return "progress value not returned by API; state = {0}".format("unknown")
    if progress >= 100:
        return "finished pending status update"
    if elapsed_minutes is None:
        return "creation time not returned by API"
    if progress == 0 and elapsed_minutes > C.STALLED_PROGRESS_MINUTES:
        return "no observable progress after {0}".format(human_minutes(elapsed_minutes))
    if elapsed_minutes > C.LONG_RUNNING_HOURS * 60:
        return "running over {0} h at {1}% - candidate for a support ticket".format(
            C.LONG_RUNNING_HOURS, progress
        )
    return "in flight at {0}% after {1} - consistent with normal queueing".format(
        progress, human_minutes(elapsed_minutes)
    )


def measure_progress_movement(seen, args):
    """Re-poll so 'stuck' rests on two samples, not on a single glance."""
    last = {}
    for sid, (region, snap) in seen.items():
        last[sid] = (region, parse_progress(field(snap, "Progress")))
    for _ in range(max(0, args.polls - 1)):
        time.sleep(args.poll_interval)
        for sid, (region, _previous) in list(last.items()):
            try:
                snaps = fetch_snapshots(region, SnapshotIds=sid)
            except _cli.CliError:
                continue
            if snaps:
                last[sid] = (region, parse_progress(field(snaps[0], "Progress")))
    lines = [row(["snapshot", "first sample", "later sample", "verdict"])]
    for sid, (region, snap) in seen.items():
        before = parse_progress(field(snap, "Progress"))
        after = last.get(sid, (region, before))[1]
        lines.append(
            row(
                [
                    sid,
                    "{0}%".format(before) if before is not None else "n/a",
                    "{0}%".format(after) if after is not None else "n/a",
                    "unchanged" if before == after else "moving",
                ]
            )
        )
    return lines


# --------------------------------------------------------------------------
# C2 policy-coverage
# --------------------------------------------------------------------------


def cmd_policy_coverage(args):
    report = Report("C2 auto snapshot policy coverage", args.json)
    report.assume("region(s) queried: {0}".format(", ".join(args.regions)))
    report.assume("auto snapshot evidence window: {0} h".format(args.hours))
    if args.policy_id:
        report.assume(
            "binding filter --policy-id {0}: DescribeDisks supports an "
            "AutoSnapshotPolicyId request parameter".format(args.policy_id)
        )
    else:
        report.assume(
            "no policy id supplied; policy names and schedules are not queried in "
            "this version (see references/limitations.md)"
        )

    cutoff = now_utc() - datetime.timedelta(hours=args.hours)
    for region in args.regions:
        try:
            disks = fetch_disks(
                region, instance_id=args.instance_id, policy_id=args.policy_id, disk_id=args.disk_id
            )
        except _cli.CliError as exc:
            report.fail("DescribeDisks in {0}: {1}".format(region, exc))
            return report
        try:
            auto_snaps = fetch_snapshots(region, SnapshotType="auto", InstanceId=args.instance_id)
        except _cli.CliError as exc:
            report.degrade("DescribeSnapshots(auto) in {0}: {1}".format(region, exc))
            auto_snaps = []
        try:
            instances = {
                str(field(inst, "InstanceId")): (
                    str(field(inst, "Status") or "unknown"),
                    str(field(inst, "OSType") or "unknown"),
                )
                for inst in fetch_instances(region, instance_id=args.instance_id)
                if field(inst, "InstanceId")
            }
        except _cli.CliError as exc:
            report.degrade(
                "DescribeInstances in {0}: {1} - coverage table will omit instance state".format(
                    region, exc
                )
            )
            instances = {}

        latest = {}
        for snap in auto_snaps:
            disk_ref = field(snap, "SourceDiskId")
            created = parse_utc(field(snap, "CreationTime"))
            if not disk_ref or created is None or created < cutoff:
                continue
            if disk_ref not in latest or created > parse_utc(latest[disk_ref]):
                latest[disk_ref] = field(snap, "CreationTime")

        bound_rows, gap_rows, unknown_rows = [], [], []
        for disk in disks:
            disk_ref = field(disk, "DiskId")
            if not disk_ref:
                continue
            ids = policy_ids_of(disk)
            attached = str(field(disk, "InstanceId") or "")
            inst_status, inst_os = instances.get(attached, ("not queried", "not queried"))
            entry = {
                "disk_id": disk_ref,
                "region": region,
                "instance_id": attached or "detached",
                "instance_status": inst_status,
                "instance_os": inst_os,
                "type": field(disk, "Type"),
                "size_gb": field(disk, "Size"),
                "category": field(disk, "Category"),
                "status": field(disk, "Status"),
                "policy_ids_reported_by_api": ids,
                "latest_auto_snapshot": latest.get(disk_ref),
            }
            report.payload.setdefault("disks", []).append(entry)
            if latest.get(disk_ref):
                bound_rows.append(
                    row(
                        [
                            disk_ref,
                            entry["instance_id"],
                            field(disk, "Type"),
                            "{0} GB".format(field(disk, "Size")),
                            "auto snapshot " + latest[disk_ref],
                        ]
                    )
                )
            elif ids:
                unknown_rows.append(
                    row(
                        [
                            disk_ref,
                            entry["instance_id"],
                            field(disk, "Type"),
                            "{0} GB".format(field(disk, "Size")),
                            "policy id {0} reported but no auto snapshot in {1} h".format(
                                ",".join(ids), args.hours
                            ),
                        ]
                    )
                )
            else:
                gap_rows.append(
                    row(
                        [
                            disk_ref,
                            "{0} [{1}, {2}]".format(
                                entry["instance_id"], inst_status, inst_os
                            ),
                            field(disk, "Type"),
                            "{0} GB".format(field(disk, "Size")),
                            "no policy id on the disk response, no auto snapshot",
                        ]
                    )
                )

        report.section(
            "Region {0}: disks covered by automatic snapshots".format(region),
            summarize(bound_rows),
        )
        report.section(
            "Region {0}: policy bound but no snapshot in window".format(region),
            summarize(unknown_rows),
        )
        report.section(
            "Region {0}: no automatic snapshot evidence "
            "(disk | instance [status, os] | type | size | finding)".format(region),
            summarize(gap_rows),
        )
        if gap_rows:
            report.action(
                "For each disk above, bind a policy in the console: "
                "{0} -> select the policy -> Apply to disks. Binding is a customer "
                "action; this skill does not change cloud configuration.".format(
                    C.CONSOLE_AUTO_POLICY.format(region_id=region)
                )
            )
        if unknown_rows:
            report.action(
                "Check whether the policy was applied after the day's trigger hour, and "
                "whether the account is in arrears; both suppress creation without an "
                "error. See references/policy-effectiveness.md."
            )
    report.section(
        "Interpretation",
        [
            "  A policy that is created but never applied to a disk triggers nothing "
            "(evidence: tickets 000F4RNG48, 0001FRZPLN).",
            "  Policies generated with the instance, commonly named default_policy, sit "
            "unbound by design and cost nothing until a disk is attached.",
            "  First creation for a disk happens on the policy's next scheduled hour, not "
            "at binding time (evidence: ticket 000GJRTG60).",
        ],
    )
    return report


# --------------------------------------------------------------------------
# C3 + C4 lifecycle-inventory
# --------------------------------------------------------------------------


def cmd_lifecycle_inventory(args):
    report = Report("C3/C4 snapshot lifecycle, copy, archive and retention", args.json)
    report.assume("region(s) queried: {0}".format(", ".join(args.regions)))
    total_gb = 0
    counted = 0
    for region in args.regions:
        try:
            snaps = fetch_snapshots(region, InstanceId=args.instance_id, DiskId=args.disk_id)
        except _cli.CliError as exc:
            report.fail("DescribeSnapshots in {0}: {1}".format(region, exc))
            return report
        rows = []
        for snap in sorted(snaps, key=snapshot_sort_key):
            created = field(snap, "CreationTime")
            retention = field(snap, "RetentionDays")
            expire = field(snap, "ExpireTime")
            category = field(snap, "Category", "SnapshotCategory")
            age_days = None
            created_moment = parse_utc(created)
            if created_moment:
                age_days = (now_utc() - created_moment).days
            size = field(snap, "SourceDiskSize")
            if size:
                try:
                    total_gb += float(size)
                    counted += 1
                except (TypeError, ValueError):
                    pass
            flags = []
            if retention in (None, ""):
                flags.append("retention not set by API -> check whether it is 'delete with disk' or permanent")
            if age_days is not None and age_days < C.ARCHIVE_MIN_STANDARD_DAYS:
                flags.append("{0} d old: a standard snapshot must be kept >= {1} d before archiving".format(
                    age_days, C.ARCHIVE_MIN_STANDARD_DAYS))
            if str(category).lower().startswith("archiv"):
                flags.append("archived: minimum {0} d at the archive layer, early deletion is still billed".format(
                    C.ARCHIVE_MIN_RETENTION_HOURS // 24))
                flags.append("archived snapshots cannot be copied to another region")
            expiry_display = expire
            if not expiry_display and retention not in (None, ""):
                derived = add_days(created, retention)
                if derived:
                    expiry_display = "{0} (derived: creation + retention)".format(iso(derived))
            report_rows_target = expiry_display or "not returned"
            rows.append(
                row(
                    [
                        field(snap, "SnapshotId"),
                        region,
                        category or "standard(not returned)",
                        field(snap, "Status"),
                        (created or "n/a"),
                        "perm" if retention in (None, "") else "{0} d".format(retention),
                        report_rows_target,
                        age_days if age_days is not None else "n/a",
                        "; ".join(flags) or "ok",
                    ]
                )
            )
            report.payload.setdefault("snapshots", []).append(
                {
                    "snapshot_id": field(snap, "SnapshotId"),
                    "region": region,
                    "category": category,
                    "creation_time": created,
                    "retention_days": retention,
                    "expire_time": expire,
                    "source_disk_id": field(snap, "SourceDiskId"),
                    "source_disk_size_gb": size,
                    "flags": flags,
                }
            )
        report.section(
            "Region {0}: id | region | category | status | created | retention | expires | age d | notes".format(
                region
            ),
            summarize(rows, limit=25),
        )

    report.section(
        "Retention and billing view",
        [
            row(["snapshots counted", counted]),
            row(["sum of source disk sizes (GB)", "{0:.0f}".format(total_gb)]),
            row(
                [
                    "NOT the billed amount",
                    "billed capacity is the snapshot chain total: first full snapshot plus the",
                ]
            ),
            row(["", "incremental parts after it, per disk; standard and archived chains bill separately"]),
            row(["reference unit price", "about {0} CNY / GB / month (mainland standard snapshots)".format(
                C.SNAPSHOT_UNIT_PRICE_CNY_PER_GB_MONTH)]),
        ],
    )
    report.degrade(
        "Snapshot chain capacity and copy lineage are not returned by the actions this "
        "version calls; read them from the console snapshot list or supply a policy id."
    )
    report.section(
        "Console entry points for the readings above",
        [
            row([region, C.CONSOLE_SNAPSHOT_LIST.format(region_id=region)])
            for region in args.regions
        ]
        + [
            row(
                [
                    args.regions[0],
                    C.CONSOLE_DISK_LIST.format(region_id=args.regions[0]),
                    "block storage page shows which disks carry a policy (ticket 000ACRK142)",
                ]
            )
        ],
    )
    report.section(
        "Stop-billing checklist (order matters; each step is a customer action)",
        [
            "  1. Unbind and delete automatic snapshot policies, or set their retention shorter.",
            "  2. Delete the automatic snapshots they already produced - the policy is free, "
            "the snapshots are billed.",
            "  3. Delete manually created snapshots; a policy deletion never removes them.",
            "  4. Delete custom images that reference the remaining snapshots.",
            "  5. Remember that snapshots created before an arrears stop continue to bill.",
            "  Evidence: tickets 000AWRLY1J, 000G2RJ8LG, 00069RU80Y, 00094RC1SX.",
        ],
    )
    report.section(
        "Copy, archive and export boundaries",
        [
            "  Copying is triggered per snapshot: two snapshots copied twice, and an automatic",
            "  policy that creates N snapshots per day copies N per day (ticket 0001ZS3DD6).",
            "  A copy bills twice: copy traffic plus standard storage in the destination region.",
            "  Archive pre-check: >= {0} d retained as standard, then >= {1} d at the archive layer".format(
                C.ARCHIVE_MIN_STANDARD_DAYS, C.ARCHIVE_MIN_RETENTION_HOURS // 24),
            "  Snapshots cannot be downloaded directly. Path: snapshot -> custom image ->",
            "  export the image to OSS -> download from OSS. Only some Linux images export;",
            "  encrypted, marketplace and Windows images do not (tickets 0005PR939W, 0009LRB5RD).",
            "  The ExportSnapshot whitelist is closed; InvalidUser.NotInWhiteList is a product",
            "  limit and cannot be opened on request (ticket 000CARSFMA).",
            "  Full detail: references/copy-archive-export.md.",
        ],
    )
    report.action(
        "For any deletion or archival execution, hand the console steps to the customer; "
        "this skill never deletes or archives a snapshot."
    )
    return report


# --------------------------------------------------------------------------
# C1b invocation-history
# --------------------------------------------------------------------------


VSS_SIGNALS = {
    "0x80042304": "VSS_E_UNEXPECTED_PROVIDER_ERROR - the EBS VSS provider is missing or "
    "broken; re-registration and a reboot are customer-side steps",
    "exitcode 12": "script stage failed; for app-consistent snapshots this usually means the "
    "RAM role or the VSS writer chain is incomplete",
    "VssSnapshot": "VSS writer output present - compare writer state in the payload",
    "regsvr32": "manual component registration was already attempted",
}


def cmd_invocation_history(args):
    report = Report("C1b Cloud Assistant invocation history (app-consistent failures)", args.json)
    report.assume("region(s) queried: {0}".format(", ".join(args.regions)))
    if not args.instance_id:
        report.degrade("No --instance-id supplied; results cover every instance in the region.")
    for region in args.regions:
        params = {
            "RegionId": region,
            "InstanceId": args.instance_id,
            "IncludeOutput": True,
            "ContentEncoding": "Base64",
        }
        try:
            invocations = _cli.paginate(
                "DescribeInvocations", params, "Invocations.Invocation"
            )
        except _cli.CliError as exc:
            report.fail("DescribeInvocations in {0}: {1}".format(region, exc))
            report.action(
                "If the response says the Cloud Assistant service is not activated or the "
                "agent is offline, ask the customer to install/start the assistant first; "
                "app-consistent snapshots depend on it."
            )
            return report
        rows = []
        for inv in invocations:
            invoke_id = field(inv, "InvokeId") or field(inv, "InvocationId") or "n/a"
            status = field(inv, "InvokeStatus", "InvocationStatus", "Status") or "unknown"
            command = field(inv, "CommandName") or field(inv, "CommandId") or "n/a"
            exit_codes = sorted(set(str(v) for k, v in _cli.find_keys(inv, {"ExitCode"})))
            outputs = [v for k, v in _cli.find_keys(inv, {"Output"})]
            decoded = " ".join(_cli.decode_maybe_base64(o)[:400] for o in outputs[:2])
            signals = [label for token, label in VSS_SIGNALS.items() if token.lower() in decoded.lower()]
            if "exitcode 12" not in " ".join(signals) and "12" in exit_codes:
                signals.append(VSS_SIGNALS["exitcode 12"])
            rows.append(
                row(
                    [
                        invoke_id,
                        region,
                        command,
                        status,
                        "exit:" + ",".join(exit_codes) if exit_codes else "exit:n/a",
                    ]
                )
            )
            for signal in signals:
                rows.append("      signal -> " + signal)
            report.payload.setdefault("invocations", []).append(
                {
                    "invoke_id": invoke_id,
                    "region": region,
                    "command": command,
                    "status": status,
                    "exit_codes": exit_codes,
                    "signals": signals,
                }
            )
        report.section("Region {0}: invocations".format(region), summarize(rows, limit=30))
    report.section(
        "Repair steps are human-only (this skill never runs them)",
        [
            "  1. Confirm the ESSD disk type and that no multi-attach is enabled - prerequisite.",
            "  2. Create the RAM role the app-consistent flow requires and attach it to the instance.",
            "  3. In the guest: check VSS writers, re-register the EBS VSS provider components, then",
            "     reboot. Re-registration and reboot are outside the allowed command set.",
            "  4. If Security Center quarantined the script, add an exclusion before retrying.",
            "  5. Verify afterwards by re-running: check-all for the new snapshot records.",
            "  Evidence: ticket 000BSRFJZW (truncated log; final closure unconfirmed).",
        ],
    )
    return report


# --------------------------------------------------------------------------
# C5 create-backup (confirmation gated)
# --------------------------------------------------------------------------


def cmd_create_backup(args):
    report = Report("C5 pre-change backup snapshot (confirmation gated)", args.json)
    if "CreateSnapshot" not in C.WRITE_ACTIONS:
        report.fail(
            "Refused: CreateSnapshot is not declared as a gated write action in this "
            "package, so no cloud resource may be created."
        )
        report.action("Do not work around the allowlist; report this to the skill owner.")
        return report
    report.assume("region {0}".format(args.regions[0]))
    region = args.regions[0]
    if not args.disk_id:
        report.fail("Refused: --disk-id is required so the backup target is unambiguous.")
        report.action(
            "Ask the customer which disk must be backed up, then re-run with --disk-id d-..."
        )
        return report
    disk = None
    try:
        disks = fetch_disks(region, disk_id=args.disk_id)
    except _cli.CliError as exc:
        report.fail("DescribeDisks failed: {0}".format(exc))
        return report
    if disks:
        disk = disks[0]
    else:
        report.degrade("DescribeDisks returned no record for {0}".format(args.disk_id))

    notice = [
        "  WHAT WILL RUN   ecs CreateSnapshot with DiskId={0}".format(args.disk_id),
        "  DISK            {0}".format(
            disk and row([
                field(disk, "DiskId"),
                field(disk, "Category"),
                "{0} GB".format(field(disk, "Size")),
                field(disk, "Status"),
                field(disk, "InstanceId") or "detached",
            ]) or "details unavailable"
        ),
        "  SCOPE           only this disk on this account; no guest and no data is touched",
        "  REVERSIBILITY   creating is safe and additive; deleting the result is irreversible",
        "                    and is always done by the customer in the console",
        "  BILLING         snapshots bill by retained capacity every month until deleted;",
        "                    a standard snapshot bills from the moment it completes",
        "  RETENTION       {0}".format(
            "{0} days, then it deletes itself".format(args.retention_days)
            if args.retention_days
            else "not set - the snapshot is kept until deleted, which keeps billing; "
            "consider --retention-days {0} for a pre-change backup".format(
                C.DEFAULT_RETENTION_DAYS
            )
        ),
    ]
    report.section("Pre-execution notice", notice)

    if args.confirm != args.disk_id:
        report.fail(
            "Write action blocked: --confirm must repeat the exact disk id. "
            "Nothing was created."
        )
        report.action(
            "Ask the customer to approve this specific backup, then re-run with "
            "--disk-id {0} --confirm {0}".format(args.disk_id)
        )
        return report

    name = args.snapshot_name or "prechange-{0}".format(now_utc().strftime("%Y%m%d%H%M%S"))
    params = {"DiskId": args.disk_id, "SnapshotName": name}
    if args.retention_days:
        params["RetentionDays"] = args.retention_days
    try:
        payload = _cli.call("CreateSnapshot", params, timeout=C.CLI_TIMEOUT_WRITE_SECONDS)
    except _cli.CliError as exc:
        report.fail("CreateSnapshot failed: {0}".format(exc))
        if exc.code in C.PERMISSION_DENIED_CODES:
            report.action(
                "The identity behind the default credential chain is missing the ECS "
                "snapshot-creation permission (CreateSnapshot under the RAM prefix "
                "ecs); add the exact grant described in references/ram-policies.md "
                "instead of broadening permissions."
            )
        else:
            report.action(
                "Compare the failure code with references/error-signals.md; arrears and "
                "risk-control blocks are account-level and handled in Billing Center."
            )
        return report

    snapshot_id = _cli.dig(payload, "SnapshotId")
    report.payload["created_snapshot_id"] = snapshot_id
    request_id = str(payload.get("RequestId") or "not returned")
    if snapshot_id:
        report.section("Created", [row([snapshot_id, region, name, "request " + request_id])])
    else:
        report.degrade(
            "Response carried no SnapshotId field; verifying against the disk instead."
        )
        report.section(
            "Created", [row(["id not returned", region, name, "request " + request_id])]
        )

    deadline = time.time() + args.wait_seconds
    progress = None
    status = "unknown"
    while time.time() < deadline:
        try:
            snaps = fetch_snapshots(region, DiskId=args.disk_id)
        except _cli.CliError as exc:
            report.degrade("poll failed: {0}".format(exc))
            break
        target = [s for s in snaps if field(s, "SnapshotId") == snapshot_id] or snaps
        if target:
            newest = max(target, key=snapshot_sort_key)
            status = str(field(newest, "Status"))
            progress = parse_progress(field(newest, "Progress"))
            if status in (C.SNAPSHOT_STATUS_ACCOMPLISHED, C.SNAPSHOT_STATUS_FAILED):
                break
        time.sleep(min(15, max(5, args.poll_interval)))
    report.section(
        "Verification",
        [
            row(["status", status, "progress", "{0}%".format(progress) if progress is not None else "n/a"]),
            row(["waited", "{0} s".format(args.wait_seconds)]),
        ],
    )
    if status == C.SNAPSHOT_STATUS_ACCOMPLISHED:
        report.action(
            "Backup is available: proceed with the customer's change, and tell them the "
            "retention that was set ({0}) so billing expectations are clear.".format(
                args.retention_days or "none - it bills until deleted"
            )
        )
    else:
        report.degrade("Snapshot had not accomplished within the wait window.")
        report.action(
            "Re-run snapshot-status for {0} before the change starts; do not roll back or "
            "clean up until it is accomplished.".format(snapshot_id or "disk " + args.disk_id)
        )
    return report


# --------------------------------------------------------------------------
# C7 guest-commands (guided, never dispatched)
# --------------------------------------------------------------------------


def validate_guest_command(candidate):
    """True only for an exact allowlisted, side-effect-free command."""
    if not candidate:
        return False
    text = candidate.strip()
    if any(meta in text for meta in C.COMMAND_META_CHARS):
        return False
    return any(text == allowed or text.startswith(allowed + " ") for allowed in C.GUEST_COMMAND_ALLOWLIST)


def cmd_guest_commands(args):
    report = Report("C7 in-instance inspection commands", args.json)
    allowed, refused = [], []
    for candidate in list(args.candidate or []):
        if validate_guest_command(candidate):
            allowed.append(candidate)
        else:
            refused.append(candidate)
    if allowed or refused:
        report.section(
            "Evaluated requests",
            [row(["ALLOWED", cmd]) for cmd in allowed] + [row(["REFUSED", cmd]) for cmd in refused],
        )
    if refused:
        report.action(
            "Refused: only the fixed allowlist below may run inside the instance. Anything "
            "else is handed to the customer as a manual step."
        )
    report.section(
        "Allowed side-effect-free commands (one at a time, after telling the customer what "
        "it does and that it changes nothing)",
        ["  - {0}".format(cmd) for cmd in C.GUEST_COMMAND_ALLOWLIST],
    )
    report.section(
        "Delivery status in this version",
        [
            "  This package does not dispatch commands into the instance. The execution",
            "  channel and its permission point are not verified yet, so the commands above",
            "  are handed to the customer to run, and their pasted output is the evidence.",
            "  Treat that as the DEGRADED path: report which reading is still missing.",
        ],
    )
    report.degrade("In-instance execution is not wired; guidance only.")
    report.action(
        "Ask the customer to run the listed command(s) and paste the output, then attach it "
        "to the finding - for example heavy writes during the creation window."
    )
    return report


# --------------------------------------------------------------------------
# C6 handoff
# --------------------------------------------------------------------------

HANDOFFS = (
    (
        ("expand", "partition", "filesystem", "resize", "growpart"),
        "Disk expansion after a resize",
        "alibabacloud-ecs-disk-expand-diagnosis",
        "This skill only creates and verifies the prerequisite snapshot; the partition and "
        "file-system extension belongs to the expansion skill.",
    ),
    (
        ("boot", "grub", "cannot start", "start stop", "pending state", "stuck starting"),
        "Instance boot or state transitions",
        "alibabacloud-ecs-instance-state-diagnosis",
        "Instance state diagnosis is a separate axis; rollback is a human console action.",
    ),
    (
        ("iops", "throughput", "latency", "slow disk", "io hang", "bps"),
        "Disk IO performance",
        "alibabacloud-ecs-disk-io-diagnosis",
        "Performance shortfall against the disk specification is a different axis.",
    ),
    (
        ("rollback", "revert", "restore disk"),
        "Snapshot rollback execution",
        "human console steps (no automated owner)",
        "Rollback is irreversible and customer-executed. Offer the pre-change backup here, "
        "then hand over the documented steps.",
    ),
    (
        ("vulnerability", "security center", "agent blocked script", "quarantine"),
        "Security Center remediation",
        "Security Center support",
        "Cross-product; identify and route, do not diagnose.",
    ),
    (
        ("hbr", "cloud backup", "whole machine backup", "backup plan"),
        "ECS whole-instance backup",
        "Cloud Backup (HBR)",
        "HBR plans are snapshot-based but their policy and billing live in Cloud Backup.",
    ),
    (
        ("arrears", "unpaid", "balance", "refund", "resource package", "risk control", "invoice"),
        "Account, arrears, packages and risk control",
        "Billing and Cost Center / account appeal",
        "Commercial and account actions are out of scope; route with the evidence gathered.",
    ),
    (
        ("delete snapshot", "clean capacity", "how much capacity left"),
        "Snapshot deletion and capacity cleanup",
        "alibabacloud-ebs-disk-snapshot-management",
        "Deletion is destructive and never automated here; route for capacity work.",
    ),
)


def cmd_handoff(args):
    report = Report("C6 symptom routing", args.json)
    text = " ".join(args.symptom).lower()
    matched = [entry for keys, entry, target, note in HANDOFFS if any(k in text for k in keys)]
    lines = []
    for keys, entry, target, note in HANDOFFS:
        marker = "MATCH" if entry in matched else "  -  "
        lines.append(row([marker, entry, "->", target]))
        if entry in matched:
            lines.append("        why: {0}".format(note))
            report.action("{0}: {1}".format(entry, note))
    report.section("Boundary table", lines)
    if not matched:
        report.degrade("No boundary keyword matched; the symptom stays inside this skill.")
    report.section(
        "Phrasing rule",
        [
            "  Tell the customer what this skill can and cannot see. Never promise that an",
            "  agent will operate on their behalf, delete a snapshot, or speed up a queue.",
        ],
    )
    return report


# --------------------------------------------------------------------------
# identity + check-all
# --------------------------------------------------------------------------


def cmd_identity(args):
    report = Report("Account identity", args.json)
    label, error = sts_token.identity_label()
    if error:
        report.fail(error)
        report.assume(sts_token.configure_hint())
        report.action(
            "Configure the CLI with `aliyun configure` using the default credential chain, "
            "then re-run. Never paste an AccessKey pair into the conversation."
        )
        return report
    report.section("Caller", [row([label])])
    report.assume("every query below is scoped to this account")
    return report


def cmd_check_all(args):
    report = Report("Snapshot health check across {0} region(s)".format(len(args.regions)), args.json)
    label, error = sts_token.identity_label()
    report.assume("account: {0}".format(label or error))
    report.assume(
        "API versions queried: {0} {1}, {2} {3}".format(
            C.ECS_PRODUCT, C.ECS_VERSION, C.STS_PRODUCT, C.STS_VERSION
        )
    )
    merged_sections = []
    for name, builder in (
        ("C1 snapshot-status", cmd_snapshot_status),
        ("C2 policy-coverage", cmd_policy_coverage),
        ("C4 lifecycle-inventory", cmd_lifecycle_inventory),
    ):
        sub = builder(args)
        sub.title = name
        for section_name, lines in sub.sections:
            merged_sections.append(("{0} / {1}".format(name, section_name), lines))
        report.assumptions.extend(sub.assumptions)
        report.degradations.extend(sub.degradations)
        report.failures.extend(sub.failures)
        for action_text in sub.next_actions:
            report.action(action_text)
        if sub.payload:
            report.payload[name] = sub.payload
    report.sections = merged_sections
    report.section(
        "Scope of this check",
        [
            "  Queries only the allowlisted actions in references/ram-policies.md. No cloud",
            "  configuration is changed. The only write is a confirmation-gated backup.",
            "  See references/limitations.md for what this version cannot determine.",
        ],
    )
    return report


# --------------------------------------------------------------------------
# argparse
# --------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        prog="snapshot_policy_check.py",
        description="Evidence collector for ECS snapshot creation, auto snapshot "
        "policy effectiveness, and copy / archive / export questions.",
    )
    sub = parser.add_subparsers(dest="command")

    def add_common(p):
        p.add_argument(
            "--regions",
            help="comma-separated region ids, required; never defaulted, this version "
            "does not enumerate regions on its own",
        )
        p.add_argument("--instance-id", help="optional ECS instance id")
        p.add_argument("--disk-id", help="optional disk id")
        p.add_argument("--json", action="store_true", help="emit machine-readable output")

    p = sub.add_parser("identity", help="show the calling account tag")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_identity, regions=[], instance_id=None, disk_id=None)

    p = sub.add_parser("snapshot-status", help="C1: progress, age and verdict per snapshot")
    add_common(p)
    p.add_argument("--snapshot-id", help="optional single snapshot id")
    p.add_argument("--hours", type=int, default=72, help="look-back window (default 72)")
    p.add_argument("--polls", type=int, default=1, help="samples to compare progress (1-5)")
    p.add_argument("--poll-interval", type=int, default=30, help="seconds between samples")
    p.set_defaults(func=cmd_snapshot_status)

    p = sub.add_parser("policy-coverage", help="C2: disks x policy binding x automatic snapshots")
    add_common(p)
    p.add_argument("--hours", type=int, default=168, help="auto snapshot evidence window")
    p.add_argument("--policy-id", help="auto snapshot policy id used as a binding filter")
    p.set_defaults(func=cmd_policy_coverage)

    p = sub.add_parser("lifecycle-inventory", help="C3/C4: category, retention, expiry, limits")
    add_common(p)
    p.set_defaults(func=cmd_lifecycle_inventory)

    p = sub.add_parser("invocation-history", help="C1b: Cloud Assistant history and exit codes")
    add_common(p)
    p.set_defaults(func=cmd_invocation_history)

    p = sub.add_parser("create-backup", help="C5: confirmation-gated CreateSnapshot + verify")
    add_common(p)
    p.add_argument("--snapshot-name")
    p.add_argument("--retention-days", type=int)
    p.add_argument("--confirm", help="must repeat --disk-id exactly, after customer approval")
    p.add_argument("--wait-seconds", type=int, default=300)
    p.add_argument("--poll-interval", type=int, default=15, help="seconds between status polls")
    p.set_defaults(func=cmd_create_backup)

    p = sub.add_parser("guest-commands", help="C7: validate and print in-instance commands")
    p.add_argument(
        "--candidate",
        action="append",
        help="command string to validate against the side-effect-free allowlist",
    )
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_guest_commands, regions=[], instance_id=None, disk_id=None, candidate=[])

    p = sub.add_parser("handoff", help="C6: route out-of-scope symptoms")
    p.add_argument("symptom", nargs="+", help="customer wording, e.g. resize partition")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_handoff, regions=[], instance_id=None, disk_id=None)

    p = sub.add_parser("check-all", help="C1+C2+C4 across every region given")
    add_common(p)
    p.add_argument("--hours", type=int, default=72)
    p.add_argument("--snapshot-id")
    p.add_argument("--policy-id")
    p.add_argument("--polls", type=int, default=1)
    p.add_argument("--poll-interval", type=int, default=30)
    p.set_defaults(func=cmd_check_all)

    return parser


def normalise_regions(args, parser):
    if isinstance(args.regions, str):
        regions = [r.strip() for r in args.regions.split(",") if r.strip()]
    else:
        regions = [r.strip() for r in (args.regions or []) if r.strip()]
    if args.command == "create-backup" and len(regions) > 1:
        regions = regions[:1]
    args.regions = regions
    needs_region = args.command not in ("identity", "guest-commands", "handoff")
    if needs_region and not regions:
        parser.error(
            "sub-command '{0}' needs --regions; ask the customer which region holds the "
            "resource instead of assuming one".format(args.command)
        )
    args.polls = max(1, min(5, getattr(args, "polls", 1) or 1))
    args.poll_interval = max(5, min(120, getattr(args, "poll_interval", 30) or 30))
    if getattr(args, "retention_days", None) is not None and args.retention_days <= 0:
        args.retention_days = None
    return args


def _run_selftest():
    """Offline boundary locks for the pure decision/parsing core.

    ``validate_guest_command`` is a fail-closed read-only gate (a wrong "True"
    hands the customer a side-effect command), ``classify_progress`` turns a
    snapshot percentage + age into the single diagnosis line a support engineer
    acts on, and the parse helpers normalise raw ECS fields. A dropped branch
    misleads the responder, so each is pinned here. Pure logic only - no cloud,
    no credentials, no subprocess.
    """
    rc = 0

    def expect(name, cond):
        nonlocal rc
        if cond:
            print("PASS {0}".format(name))
        else:
            print("FAIL {0}".format(name))
            rc = 1

    # --- validate_guest_command: exact allowlist, prefix-bypass & meta blocked
    expect("vgc_exact_df_h", validate_guest_command("df -h") is True)
    expect("vgc_allowlist_with_arg", validate_guest_command("df -h /var") is True)
    expect("vgc_findmnt", validate_guest_command("findmnt") is True)
    expect("vgc_windows", validate_guest_command("Get-Volume") is True)
    expect("vgc_empty_refuse", validate_guest_command("") is False)
    expect("vgc_bare_df_refuse", validate_guest_command("df") is False)
    # discriminating case for the 'allowed + " "' guard: "stat" is allowlisted, so
    # dropping the trailing space would let "statxyz" (a different binary) pass via
    # startswith("stat"); "statxyz" therefore pins the space guard specifically.
    expect("vgc_stat_exact", validate_guest_command("stat") is True)
    expect("vgc_prefix_bypass_refuse", validate_guest_command("statxyz") is False)
    expect("vgc_meta_semicolon_refuse", validate_guest_command("df -h;rm -rf /") is False)
    expect("vgc_meta_andand_refuse", validate_guest_command("df -h && reboot") is False)
    expect("vgc_nonallowlist_refuse", validate_guest_command("rm -rf /") is False)
    # universal invariant: every allowlisted entry must self-accept
    expect("vgc_all_allowlist_self_accept",
           all(validate_guest_command(cmd) for cmd in C.GUEST_COMMAND_ALLOWLIST))

    # --- parse_progress: salvage an int percentage, clamped to [0, 100]
    expect("pp_pct_string", parse_progress("45%") == 45)
    expect("pp_plain", parse_progress("45") == 45)
    expect("pp_zero", parse_progress(0) == 0)
    expect("pp_clamp_high", parse_progress("150") == 100)
    expect("pp_none", parse_progress(None) is None)
    expect("pp_nodigits_none", parse_progress("abc") is None)
    expect("pp_empty_none", parse_progress("") is None)

    # --- human_minutes: <90 shows minutes, else hours
    expect("hm_none", human_minutes(None) == "unknown")
    expect("hm_below_90", human_minutes(89) == "89 min")
    expect("hm_at_90_hours", human_minutes(90) == "1.5 h")

    # --- classify_progress: every decision branch
    expect("cp_none_unknown", "unknown" in classify_progress(None, 10))
    expect("cp_finished", classify_progress(100, 5) == "finished pending status update")
    expect("cp_no_elapsed", classify_progress(50, None) == "creation time not returned by API")
    expect("cp_stalled", "no observable progress" in classify_progress(0, C.STALLED_PROGRESS_MINUTES + 1))
    expect("cp_zero_but_recent_ok", "in flight" in classify_progress(0, C.STALLED_PROGRESS_MINUTES - 1))
    expect("cp_long_running", "support ticket" in classify_progress(5, C.LONG_RUNNING_HOURS * 60 + 60))
    expect("cp_in_flight", "in flight at 50%" in classify_progress(50, 10))

    # --- parse_utc: ISO formats only; anything else returns None (never guesses)
    expect("pu_iso_z", parse_utc("2024-10-10T13:55:36Z") is not None)
    expect("pu_bad_none", parse_utc("garbage") is None)
    expect("pu_empty_none", parse_utc("") is None)
    expect("pu_none_none", parse_utc(None) is None)

    print("SELFTEST: {0}".format("PASS" if rc == 0 else "FAIL"))
    return rc


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--selftest" in argv:
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        print("\n{0}".format(C.STATUS_FAIL))
        print("NEXT_ACTION: choose a sub-command; start with check-all --regions <region ids>")
        return 2
    args = normalise_regions(args, parser)
    try:
        report = args.func(args)
    except _cli.CliError as exc:
        report = Report("fatal", getattr(args, "json", False))
        report.fail(str(exc))
        if exc.code in C.PERMISSION_DENIED_CODES:
            report.action(
                "The identity behind the default credential chain lacks an action listed in "
                "references/ram-policies.md; attach that policy, do not broaden it."
            )
        else:
            report.action("Resolve the API error, then re-run the same sub-command.")
    print(report.render())
    return 0 if report.status() != C.STATUS_FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
