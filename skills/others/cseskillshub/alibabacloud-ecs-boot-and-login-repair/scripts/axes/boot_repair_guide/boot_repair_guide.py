#!/usr/bin/env python3
"""Entry point for alibabacloud-ecs-boot-repair-guide.

The agent runs this script and nothing else: it is the only place that reaches the
cloud, and the only place the triage tables are applied.

    python3 scripts/boot_repair_guide.py profile       --region-id cn-hangzhou --instance-id i-xxx
    python3 scripts/boot_repair_guide.py classify      --region-id cn-hangzhou --instance-id i-xxx \
                                                       --text "start job is running for dev-vdb1"
    python3 scripts/boot_repair_guide.py preflight     --region-id cn-hangzhou --instance-id i-xxx \
                                                       --rescue-instance-id i-yyy --snapshot-progress 100
    python3 scripts/boot_repair_guide.py rescue-stock   --region-id cn-hangzhou --zone-id cn-hangzhou-h
    python3 scripts/boot_repair_guide.py evidence-plan --branch fstab-mount
    python3 scripts/boot_repair_guide.py fstab-compare  --fstab-file fstab.txt --blkid-file blkid.txt
    python3 scripts/boot_repair_guide.py handoff       --text "rdp times out but vnc shows the desktop"

Every subcommand ends with the machine-readable ``STATUS`` and ``NEXT_ACTION`` pair that
the report must relay unchanged. ``--json`` emits the same content as one object.
"""

import argparse
import json
import os
import re
import sys
import textwrap

import _cli
import _constants as C

# Reported releases that have passed their general-support window in the common cases.
# This is an attention flag to be confirmed against the published lifecycle policy,
# never a conclusion in itself.
LIFECYCLE_ATTENTION = (
    "windows server 2003", "windows server 2008", "windows server 2012",
    "centos 6", "centos 7", "debian 8", "debian 9", "debian 10",
    "ubuntu 14.04", "ubuntu 16.04", "ubuntu 18.04", "suse linux enterprise server 11",
    "opensuse 42", "redhat 5", "redhat 6",
)

# Families whose per-instance storage ceiling is shared by all attached disks.
BURSTABLE_FAMILIES = ("ecs.t5", "ecs.t6", "ecs.s6", "ecs.e4", "ecs.xn4")

# Device-token prefixes that are well-formed in column one of a mount table.
KNOWN_DEVICE_TOKENS = ("uuid=", "label=", "partuuid=", "partlabel=", "/dev/", "/")
PSEUDO_FILESYSTEMS = ("proc", "sysfs", "devtmpfs", "tmpfs", "devpts", "securityfs",
                      "cgroup", "cgroup2", "pstore", "debugfs", "mqueue", "hugetlbfs",
                      "fusectl", "configfs", "ramfs", "binfmt_misc", "autofs", "overlay")

CRITICAL_MOUNTS = {"/": "root", "/boot": "boot", "/boot/efi": "EFI system partition",
                   "/efi": "EFI system partition", "[swap]": "swap"}


# ---------------------------------------------------------------------------
# output helpers
# ---------------------------------------------------------------------------
def _wrap(text, indent="        ", width=100):
    return textwrap.fill(str(text), width=width, initial_indent=indent,
                         subsequent_indent=indent).strip()


class Report(object):
    """Accumulates sections, then renders text or JSON with the result tail."""

    def __init__(self, session_id, as_json=False):
        self.session_id = session_id
        self.as_json = as_json
        self.sections = []
        self.gaps = []
        self.calls = []
        self.status = C.STATUS_OK
        self.next_action = "none"
        self.meta = {}

    def section(self, title, lines=()):
        self.sections.append((title, [str(x) for x in lines if x is not None]))

    def gap(self, text):
        self.gaps.append(text)
        if self.status == C.STATUS_OK:
            self.status = C.STATUS_DEGRADED

    def note_call(self, action, params, outcome):
        self.calls.append({"action": action, "declared_params": params, "outcome": outcome})

    def degrade(self):
        if self.status == C.STATUS_OK:
            self.status = C.STATUS_DEGRADED

    def fail(self):
        self.status = C.STATUS_FAIL

    def render(self):
        if self.as_json:
            payload = {
                "skill": C.SKILL_NAME, "session_id": self.session_id,
                "user_agent": _cli.user_agent(self.session_id), "meta": self.meta,
                "sections": [{"title": t, "lines": v} for t, v in self.sections],
                "cloud_calls": self.calls, "evidence_gaps": self.gaps,
                "status": self.status, "next_action": self.next_action,
            }
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return
        print("# alibabacloud-ecs-boot-repair-guide")
        print("session_id: {0}".format(self.session_id))
        print("user_agent: {0}".format(_cli.user_agent(self.session_id)))
        print("scope: boot-failure triage and manual repair guidance; no cloud resource is changed")
        for title, lines in self.sections:
            print("\n## {0}".format(title))
            for line in lines:
                print(_wrap(line, indent="  ", width=104))
        if self.calls:
            print("\n## Cloud calls made (declared parameters, for audit)")
            for call in self.calls:
                print("  - {0} {1} -> {2}".format(call["action"],
                                                  json.dumps(call["declared_params"], ensure_ascii=False),
                                                  call["outcome"]))
        if self.gaps:
            print("\n## Evidence gaps")
            for gap in self.gaps:
                print(_wrap(gap, indent="  - ", width=104))
        print("\nSTATUS: {0}".format(self.status))
        print("NEXT_ACTION: {0}".format(self.next_action))


def warn(message):
    sys.stderr.write(_cli.mask_credentials(message).rstrip() + "\n")


# ---------------------------------------------------------------------------
# ECS payload access
# ---------------------------------------------------------------------------
def _unwrap(payload, *path):
    node = payload
    for key in path:
        if not isinstance(node, dict):
            return []
        node = node.get(key)
    if node is None:
        return []
    if isinstance(node, dict):
        # {"Instance": [...]} versus {"Instance": {...} } both reduce to a list.
        return [node]
    return node if isinstance(node, list) else []


def describe_instances(report, region_id, instance_ids, session_id, device_attribute=True):
    params = {"RegionId": region_id, "PageSize": 50}
    if instance_ids:
        params["InstanceIds"] = list(instance_ids)
    if device_attribute:
        # Asks the service to include the device-attachment availability attribute.
        params["AdditionalAttributes.1"] = "DeviceAvailable"
    payload, error = _cli.call_soft("DescribeInstances", params=params, session_id=session_id,
                                    warn=warn)
    if error is not None:
        report.note_call("DescribeInstances", params, "failed: {0}".format(error.code))
        report.gap("DescribeInstances unavailable ({0}); instance profile, reported operating "
                   "system, zone, and lifecycle state are unknown and must come from the "
                   "customer.".format(error.code))
        if error.is_permission_denied:
            report.gap("The identity lacks ecs:DescribeInstances; see references/ram-policies.md "
                       "for the minimal policy entry.")
        return []
    report.note_call("DescribeInstances", params, "ok")
    return _unwrap(payload, "Instances", "Instance")


def describe_status(report, region_id, instance_ids, session_id):
    params = {"RegionId": region_id, "PageSize": 50}
    for index, instance_id in enumerate(instance_ids[:50], start=1):
        params["InstanceId.{0}".format(index)] = instance_id
    payload, error = _cli.call_soft("DescribeInstanceStatus", params=params,
                                    session_id=session_id)
    if error is not None:
        report.note_call("DescribeInstanceStatus", params, "failed: {0}".format(error.code))
        report.gap("DescribeInstanceStatus unavailable ({0}); the stop or run state has to be "
                   "confirmed by the customer from the console.".format(error.code))
        return {}
    report.note_call("DescribeInstanceStatus", params, "ok")
    statuses = {}
    for item in _unwrap(payload, "InstanceStatuses", "InstanceStatus"):
        statuses[item.get("InstanceId")] = item.get("Status")
    return statuses


def describe_disks(report, region_id, instance_id, session_id):
    """List the disks attached to one instance (read-only DescribeDisks)."""
    params = {"RegionId": region_id, "InstanceId": instance_id, "PageSize": 100}
    payload, error = _cli.call_soft("DescribeDisks", params=params, session_id=session_id)
    if error is not None:
        report.note_call("DescribeDisks", params, "failed: {0}".format(error.code))
        report.gap("DescribeDisks unavailable ({0}); the system disk and its rollback options "
                   "have to be confirmed by the customer from the console.".format(error.code))
        return []
    report.note_call("DescribeDisks", params, "ok")
    return _unwrap(payload, "Disks", "Disk")


def describe_snapshots(report, region_id, disk_id, session_id):
    """List snapshots created from one disk (read-only DescribeSnapshots)."""
    params = {"RegionId": region_id, "DiskId": disk_id, "PageSize": 100}
    payload, error = _cli.call_soft("DescribeSnapshots", params=params, session_id=session_id)
    if error is not None:
        report.note_call("DescribeSnapshots", params, "failed: {0}".format(error.code))
        report.gap("DescribeSnapshots unavailable ({0}); whether a rollback point exists is "
                   "unknown and must be stated by the customer.".format(error.code))
        return None
    report.note_call("DescribeSnapshots", params, "ok")
    return _unwrap(payload, "Snapshots", "Snapshot")


def summarize_recovery_points(report, region_id, instance_id, session_id):
    """Query the system disk and its snapshots; return (lines, usable_snapshot_or_None).

    usable is the newest accomplished snapshot dict, or None when every rollback candidate is
    absent or still progressing. A None return paired with an API error is signalled by the
    gap the describe_* helpers already recorded, so callers can tell 'no snapshot' apart from
    'cannot see snapshots'.
    """
    disks = describe_disks(report, region_id, instance_id, session_id)
    if not disks:
        return (["  recovery points: not resolvable from this account/region."], None)
    system = [d for d in disks if str(d.get("Type", "")).lower() == "system"] or \
        [d for d in disks if d.get("DiskId")] or []
    lines = []
    usable = None
    for disk in system[:1]:
        disk_id = disk.get("DiskId", "n/a")
        lines.append("  system disk: {0} ({1}, {2} GB, status {3})".format(
            disk_id, disk.get("Category", "n/a"), disk.get("Size", "n/a"),
            disk.get("Status", "n/a")))
        snaps = describe_snapshots(report, region_id, disk_id, session_id)
        if snaps is None:
            lines.append("  snapshots: could not be queried; treat the rollback point as "
                         "unconfirmed and ask the customer.")
            return (lines, None)
        done = [s for s in snaps if str(s.get("Status", "")).lower() == "accomplished"]
        done.sort(key=lambda s: s.get("CreationTime", ""), reverse=True)
        if not done:
            lines.append("  snapshots on this disk: {0} total, none accomplished. No rollback "
                         "point exists; guide repair toward a non-destructive path or create a "
                         "snapshot first (a customer change).".format(len(snaps)))
            return (lines, None)
        usable = done[0]
        lines.append("  rollback point available: newest accomplished snapshot {0} created {1} "
                     "(usage {2}); {3} accomplished snapshot(s) in total.".format(
                         usable.get("SnapshotId", "n/a"), usable.get("CreationTime", "n/a"),
                         usable.get("Usage", "n/a"), len(done)))
        progressing = [s for s in snaps
                       if str(s.get("Status", "")).lower() != "accomplished"]
        if progressing:
            lines.append("  note: {0} snapshot(s) still progressing or failed were not counted "
                         "as rollback points.".format(len(progressing)))
    return (lines, usable)


def _private_ip(instance):
    vpc = instance.get("VpcAttributes") or {}
    ips = vpc.get("PrivateIpAddress") or {}
    values = _unwrap(ips, "IpAddress") or (ips if isinstance(ips, list) else [])
    return ", ".join(str(v) for v in values) if values else "n/a"


def _public_ip(instance):
    pip = _unwrap(instance.get("PublicIpAddress") or {}, "IpAddress") or []
    if pip:
        return ", ".join(str(v) for v in pip)
    eip = (instance.get("EipAddress") or {}).get("IpAddress")
    return eip or "n/a"


def _lifecycle_flag(instance):
    blob = " ".join(str(instance.get(k) or "") for k in ("OSName", "OSType", "ImageId")).lower()
    hits = [name for name in LIFECYCLE_ATTENTION if name in blob]
    return hits


def _burstable_flag(instance):
    family = str(instance.get("InstanceTypeFamily") or "").lower()
    return family if any(family.startswith(b) for b in BURSTABLE_FAMILIES) else ""


# ---------------------------------------------------------------------------
# pattern matching
# ---------------------------------------------------------------------------
def match_branches(text):
    """Return pattern entries whose evidence appears in the supplied screen text."""
    if not text:
        return []
    haystack = text.lower()
    scored = []
    for entry in C.ERROR_PATTERNS:
        hits = [p for p in entry["patterns"] if p in haystack]
        if hits:
            scored.append((len(hits), entry, hits))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored


def _branch_card(branch_id, hits=None):
    branch = C.BRANCHES.get(branch_id, C.BRANCHES["unknown"])
    lines = ["branch: {0} ({1})".format(branch_id, branch["label"]),
             "layer: {0}".format(branch["layer"]),
             "gate: {0}".format(branch["gate"])]
    if hits:
        lines.append("matched screen text: {0}".format(", ".join(sorted(set(hits)))))
    return lines, branch


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------
def cmd_profile(args):
    report = Report(args.session_id, as_json=args.json)
    ids = list(args.instance_id or [])
    report.meta["region_id"] = args.region_id
    report.meta["instance_ids"] = ids
    instances = describe_instances(report, args.region_id, ids, args.session_id)
    statuses = describe_status(report, args.region_id, ids or [i.get("InstanceId") for i in instances
                                                              if i.get("InstanceId")],
                               args.session_id)
    if not instances:
        report.fail()
        report.section("Result", ["No instance record was returned. Confirm the region id and the "
                                  "instance id; a wrong region returns an empty set rather than an "
                                  "error."])
        report.next_action = "Customer confirms the region and instance identifier, then re-runs " \
                             "profile."
        report.render()
        return 2

    found_ids = [i.get("InstanceId") for i in instances if i.get("InstanceId")]
    blocks = []
    for instance in instances:
        instance_id = instance.get("InstanceId", "n/a")
        status = instance.get("Status") or statuses.get(instance_id) or "unknown"
        blocks.append("instance_id: {0}   zone: {1}   status: {2}".format(
            instance_id, instance.get("ZoneId", "n/a"), status))
        blocks.append("  reported os: {0} (family: {1})".format(instance.get("OSName", "n/a"),
                                                               instance.get("OSType", "n/a")))
        blocks.append("  image_id: {0}   instance_type: {1}   family: {2}".format(
            instance.get("ImageId", "n/a"), instance.get("InstanceType", "n/a"),
            instance.get("InstanceTypeFamily", "n/a")))
        blocks.append("  private ip: {0}   public ip: {1}".format(_private_ip(instance),
                                                                 _public_ip(instance)))
        blocks.append("  billing: {0}   created: {1}   key pair bound: {2}".format(
            instance.get("InstanceChargeType", "n/a"), instance.get("CreationTime", "n/a"),
            "yes" if instance.get("KeyPairName") else "no"))
        blocks.append("  device attachment available: {0}".format(
            instance.get("DeviceAvailable", "not reported")))
        burstable = _burstable_flag(instance)
        if burstable:
            blocks.append("  flag burstable-family storage ceiling: {0} caps IOPS and throughput per "
                          "instance, shared by every attached disk".format(burstable))
        lifecycle = _lifecycle_flag(instance)
        if lifecycle:
            blocks.append("  flag end-of-support candidate: {0}. Confirm against the published "
                          "lifecycle policy before attributing a boot failure to a missing "
                          "update.".format(", ".join(lifecycle)))
        if str(status).lower() == "running":
            blocks.append("  note: a Running status means the instance is started; it does not mean "
                          "the guest operating system reached logon. The screen text decides "
                          "that.")
    if ids:
        missing = [i for i in ids if i not in found_ids]
        if missing:
            blocks.append("not returned by the query (wrong region, released, or outside this "
                          "account): {0}".format(", ".join(missing)))
            report.gap("{0} of {1} requested instance ids were absent from the response.".format(
                len(missing), len(ids)))

    if args.check_invocations:
        blocks.append("")
        blocks.append("Cloud Assistant history (does the guest ever execute a command after the "
                      "failure?):")
        for instance_id in found_ids[:10]:
            blocks.extend(_invocation_summary(report, args.region_id, instance_id, args.session_id))

    recovery_lines = []
    if found_ids:
        recovery_lines, _usable = summarize_recovery_points(
            report, args.region_id, found_ids[0], args.session_id)

    report.section("Instance profile", blocks)
    report.section("Recovery points (system disk and snapshots)",
                   recovery_lines or ["  not queried (no instance returned)."])
    report.section("Interpretation", [
        "This is the environment picture used by every later step. Nothing here proves a boot "
        "failure; run classify with the screen text for that.",
        "Instance fields come from DescribeInstances and DescribeInstanceStatus; the system disk "
        "and its accomplished snapshots come from DescribeDisks and DescribeSnapshots. Partition "
        "layout, boot loader contents, and update history remain invisible to these actions.",
    ])
    report.next_action = "Run classify with the transcribed console screen text, then preflight " \
                         "before any offline repair step."
    if report.status == C.STATUS_DEGRADED:
        report.next_action = "Supply the missing profile fields from the console, then re-run " \
                             "classify."
    report.render()
    return 0


def _invocation_summary(report, region_id, instance_id, session_id):
    params = {"RegionId": region_id, "InstanceId": instance_id, "PageSize": 10,
              "IncludeOutput": False}
    payload, error = _cli.call_soft("DescribeInvocations", params=params, session_id=session_id)
    if error is not None:
        report.note_call("DescribeInvocations", params, "failed: {0}".format(error.code))
        return ["  {0}: history unavailable ({1})".format(instance_id, error.code)]
    report.note_call("DescribeInvocations", params, "ok")
    lines = []
    for item in _unwrap(payload, "Invocations", "Invocation")[:10]:
        lines.append("  {0}: command={1} status={2} created={3}".format(
            instance_id, item.get("CommandName") or item.get("CommandId") or "n/a",
            item.get("InvocationStatus") or item.get("InvokeStatus") or "n/a",
            item.get("CreateTime") or "n/a"))
    if not lines:
        return ["  {0}: no Cloud Assistant invocation records returned; that is not evidence about "
                "the boot state, only about command history.".format(instance_id)]
    lines.append("  reading: a record that finished after the failure time indicates the guest "
                 "reached a state where the agent ran, which argues against a boot failure; the "
                 "customer's screen text still decides.")
    return lines


def cmd_classify(args):
    report = Report(args.session_id, as_json=args.json)
    text = args.text or ""
    report.meta["region_id"] = args.region_id
    report.meta["instance_ids"] = list(args.instance_id or [])
    report.meta["screen_text_bytes"] = len(text.encode("utf-8"))

    instances, statuses = [], {}
    if args.region_id and args.instance_id:
        instances = describe_instances(report, args.region_id, list(args.instance_id),
                                       args.session_id)
        statuses = describe_status(report, args.region_id, list(args.instance_id), args.session_id)
    elif not args.no_cloud:
        report.gap("No region or instance id supplied, so the step-0 gate rests on the transcribed "
                   "screen text alone. Provide --region-id and --instance-id to also check the "
                   "reported lifecycle state and image.")

    scored = match_branches(text)
    gate_lines = []
    os_reported_running = any((i.get("Status") or statuses.get(i.get("InstanceId"))) == "Running"
                              for i in instances)
    confirmed = {i.get("InstanceId"): (i.get("Status") or statuses.get(i.get("InstanceId")))
                 for i in instances}
    if confirmed:
        gate_lines.append("reported instance states: {0}".format(
            "; ".join("{0}={1}".format(k, v or "unknown") for k, v in sorted(confirmed.items()))))
    if os_reported_running:
        gate_lines.append("The service reports the instance Running. That is the machine state, not "
                          "a statement about the guest: a kernel that never reaches logon still "
                          "reports Running. Only the screen text settles whether the system came up.")

    top_branch = None
    branch_lines = []
    if not scored:
        top_branch = "unknown"
        branch_lines, branch = _branch_card("unknown")
        branch_lines = []
        gate_lines.append("No catalogued boot-time, capacity, state, connection, or security string "
                          "was found in the supplied text.")
        report.gap("The screen text is empty or contains no recognised string. Classification is "
                   "withheld rather than guessed; ask for a verbatim transcription of the console "
                   "screen, including identifiers and the two lines before any prompt.")
    else:
        branch_lines = []
        for score, entry, hits in scored[:4]:
            cid, card = _branch_card(entry["branch"], hits)
            branch_lines.extend(cid)
            branch_lines.append("  supports: {0}".format(entry["proves"]))
            branch_lines.append("  does NOT support: {0}".format(entry["not_proves"]))
            branch_lines.append("  still needed: {0}".format("; ".join(entry["evidence"])))
            branch_lines.append("  detail: {0}".format(C.BRANCHES[entry["branch"]]["reference"]))
            if top_branch is None:
                top_branch, branch = entry["branch"], card
        gate_lines.append("Strongest match: {0} ({1})".format(
            top_branch, C.BRANCHES[top_branch]["label"]))

    report.section("Step 0 gate: is this a boot failure?", gate_lines or ["No cloud state was "
                                                                        "available to check."])

    if branch_lines:
        report.section("Candidate branches (ranked)", branch_lines)

    if top_branch and C.BRANCHES[top_branch]["gate"] == "handoff":
        target = C.BRANCHES[top_branch].get("target_skill", "the owning flow")
        report.section("Routing", ["The evidence points away from the boot path. Hand this to {0} "
                                   "and pass the collected profile and screen text along with it, so "
                                   "the customer does not restate them.".format(target),
                                   "Wording: references/handoff-map.md"])
        report.next_action = "Route to {0}; state the artifact that justifies the route.".format(target)
    elif top_branch and top_branch != "unknown":
        steps = C.MANUAL_GUIDANCE.get(top_branch, ())
        report.section("Manual repair ladder (customer-executed)",
                       ["{0}. {1}".format(i + 1, s) for i, s in enumerate(steps)] or
                       ["No ladder recorded for this branch; report the gap."])
        report.section("Non-mutating evidence to collect first",
                       ["Run evidence-plan --branch {0} for the command list the customer pastes "
                        "back.".format(top_branch)])
        report.next_action = "Confirm the snapshot gate (a usable snapshot at 100 percent) and the " \
                             "approved stop window, then walk the ladder with the customer; every " \
                             "step above is performed by them, not by this skill."
    else:
        report.section("Next evidence", [
            "Ask for, in this order: the verbatim console screen text; the console diagnostic "
            "verdict if one has been run; the time of the last start attempt and the change that "
            "preceded it; whether a snapshot exists and its progress; whether the instance can be "
            "stopped.",
            "Do not name a root cause from the customer's attribution alone.",
        ])
        report.next_action = "Collect the screen text and snapshot state, then re-run classify."

    report.section("Standing constraints", [
        "This skill issues no change: no stop, restart, snapshot, disk operation, boot-loader "
        "rewrite, or mount-table edit is performed on its authority.",
        "The boot loader, the EFI system partition, /etc/fstab, the update history, and any crash "
        "dump live inside the guest or the offline volume; the cloud actions used here cannot see "
        "them, so those conclusions always rest on customer-supplied artifacts.",
    ])
    report.render()
    return 0 if top_branch and top_branch != "unknown" else 3


def cmd_preflight(args):
    report = Report(args.session_id, as_json=args.json)
    ids = [args.instance_id] + (["%s" % args.rescue_instance_id] if args.rescue_instance_id else [])
    report.meta["instance_ids"] = ids
    instances = describe_instances(report, args.region_id, ids, args.session_id)
    statuses = describe_status(report, args.region_id, ids, args.session_id)
    by_id = {i.get("InstanceId"): i for i in instances}

    target = by_id.get(args.instance_id)
    checks = []
    if target is None:
        report.fail()
        report.section("Preflight", ["The instance id was not returned by DescribeInstances; "
                                    "confirm the region and the id."])
        report.next_action = "Correct the region or instance identifier and re-run preflight."
        report.render()
        return 2

    status = target.get("Status") or statuses.get(args.instance_id) or "unknown"
    checks.append("[{0}] instance stop state: {1}. A repair or pre-install environment disk can only "
                  "be attached while the instance is stopped; if a graceful stop is impossible, the "
                  "alternative is a hard power transition, which is itself a way to leave a volume "
                  "needing a consistency pass.".format(
                      "PASS" if str(status).lower() == "stopped" else "BLOCK", status))

    snapshot = args.snapshot_progress
    if snapshot is None:
        rp_lines, usable = summarize_recovery_points(
            report, args.region_id, args.instance_id, args.session_id)
        if usable is not None:
            checks.append("[PASS] rollback point queried from the account: newest accomplished "
                          "snapshot {0} (created {1}). Record its id and creation time in the "
                          "change note; new snapshots bill and expire on their retention "
                          "rule.".format(usable.get("SnapshotId", "n/a"),
                                          usable.get("CreationTime", "n/a")))
        elif rp_lines and any("could not be queried" in ln for ln in rp_lines):
            checks.append("[ASK] snapshot state could not be queried (see gaps); the completion "
                          "figure has to come from the customer's console, and a snapshot below "
                          "100 percent is not a rollback point.")
            report.degrade()
        else:
            checks.append("[BLOCK] no accomplished snapshot was found on the system disk, so no "
                          "rollback point exists yet. Nothing that can destroy data should be "
                          "started until a snapshot completes (a customer change).")
            report.degrade()
    elif snapshot >= 100:
        checks.append("[PASS] snapshot completion reported at {0} percent. Record the snapshot "
                      "identifier and its creation time in the change note, and remember that new "
                      "snapshots bill and expire on their retention rule.".format(snapshot))
    else:
        checks.append("[BLOCK] snapshot reported at {0} percent, so no usable rollback point "
                      "exists yet. Nothing that can destroy data should be started until it "
                      "completes.".format(snapshot))
        report.degrade()

    checks.append("[{0}] stop window approved by the customer: {1}. The window has to cover the "
                  "stop, the attach, the inspection or repair, and a test boot.".format(
                      "PASS" if args.downtime_approved else "ASK",
                      "yes" if args.downtime_approved else "not stated"))
    checks.append("[{0}] guest credential usable for the repair path: {1}. Re-attaching a system "
                  "disk can require setting a logon password or binding a key first, and some "
                  "custom images only support the offline reset flow.".format(
                      "PASS" if args.credential_ready else "ASK",
                      "confirmed" if args.credential_ready else "not stated"))

    burstable = _burstable_flag(target)
    if burstable:
        checks.append("[INFO] {0} is a burstable family: disk IOPS and throughput are capped per "
                      "instance and shared by all attached disks. Attaching a repair or rescue "
                      "disk can exceed that ceiling and fail in a way that reads like a permission "
                      "problem.".format(burstable))

    device_available = target.get("DeviceAvailable")
    if device_available is not None:
        checks.append("[INFO] device attachment availability reported as {0}. This says whether the "
                      "instance supports the attachment slot; it does not say whether the "
                      "attachment is permitted while running, which is never assumed "
                      "here.".format(device_available))

    if args.rescue_instance_id:
        rescue = by_id.get(args.rescue_instance_id)
        if rescue is None:
            checks.append("[ASK] the rescue instance id was not returned; confirm its region and id.")
            report.degrade()
        else:
            same_zone = rescue.get("ZoneId") == target.get("ZoneId")
            checks.append("[{0}] rescue host zone: {1} versus the impaired instance's {2}. Block "
                          "storage is zonal, so a mismatch shows up as a missing resource rather "
                          "than a permission error.".format(
                              "PASS" if same_zone else "BLOCK", rescue.get("ZoneId"),
                              target.get("ZoneId")))
            if not same_zone:
                report.degrade()

    report.section("Offline repair channel preflight", checks)
    report.section("What preflight cannot establish", [
        "Whether the repair environment attaches on the first attempt; it sometimes does not, and "
        "then the case stops being self-service.",
        "Snapshot retention and cost, which are set by the customer's policy; the existence of an "
        "accomplished snapshot is now queried, but its monetary cost is not.",
        "Anything inside the guest or inside the offline volume.",
    ])
    blocking = any(line.startswith("[BLOCK]") for line in checks)
    asking = any(line.startswith("[ASK]") for line in checks)
    if blocking:
        report.next_action = "Resolve the blocked items (stop state, completed snapshot, zone " \
                             "match) before any change guidance is issued."
    elif asking:
        report.next_action = "Ask the customer for the missing confirmations; do not start an " \
                             "offline repair on assumptions."
    else:
        report.next_action = "Prerequisites are met: walk the customer through the repair " \
                             "environment and the ladder in the branch's reference file, restating " \
                             "the impact and the reversibility of each step."
    report.render()
    return 0


def cmd_rescue_stock(args):
    report = Report(args.session_id, as_json=args.json)
    # DescribeAvailableResource has no "Instance" destination; the resource
    # axis for instance-type capacity is "InstanceType" (sending "Instance"
    # is rejected with Invalid.DestinationResource whether or not a specific
    # InstanceType filter is supplied).
    params = {"RegionId": args.region_id, "DestinationResource": "InstanceType",
              "InstanceChargeType": "PostPaid"}
    if args.zone_id:
        params["ZoneId"] = args.zone_id
    if args.instance_type:
        params["InstanceType"] = args.instance_type
    if args.network_category:
        params["NetworkCategory"] = args.network_category
    payload, error = _cli.call_soft("DescribeAvailableResource", params=params,
                                    session_id=args.session_id)
    if error is not None:
        report.note_call("DescribeAvailableResource", params, "failed: {0}".format(error.code))
        report.fail()
        report.section("Result", ["The availability query failed: {0}".format(error.message)])
        report.next_action = "Retry with a narrower zone, or ask the customer to check the purchase " \
                             "page for the temporary instance."
        report.render()
        return 2
    report.note_call("DescribeAvailableResource", params, "ok")
    zones = []
    for zone in _unwrap(payload, "AvailableZones", "AvailableZone"):
        zones.append("{0}: {1}".format(zone.get("ZoneId", "n/a"), zone.get("StatusCategory")
                                       or zone.get("Status") or "status not reported"))
        for res in _unwrap(zone.get("AvailableResources"), "AvailableResource"):
            for support in _unwrap(res.get("SupportedResources"), "SupportedResource")[:5]:
                zones.append("    {0} {1}: {2}".format(res.get("Type", "n/a"),
                                                       support.get("Value", "n/a"),
                                                       support.get("Status", "n/a")))
    report.section("Temporary pay-as-you-go capacity for the rescue host",
                   zones or ["The response carried no zone or resource entries; that is an empty "
                             "result, not a statement that nothing exists."])
    report.section("Reading this result", [
        "The zone must match the impaired instance's zone, because a disk built from a snapshot can "
        "only be attached in the same zone.",
        "Prefer a type with a storage ceiling above the copy workload's need; entry-level burstable "
        "types share one small cap across all disks.",
        "The purchase, the attachment, and the release are all the customer's actions, and the "
        "temporary instance bills while it exists.",
    ])
    report.next_action = "Customer buys the temporary instance in the matching zone and attaches the " \
                         "snapshot-built disks there."
    report.render()
    return 0


def cmd_evidence_plan(args):
    report = Report(args.session_id, as_json=args.json)
    branch = args.branch
    plan = C.EVIDENCE_PLANS.get(branch)
    if not plan:
        report.fail()
        report.section("Result", ["No evidence plan for branch '{0}'. Known branches: {1}".format(
            branch, ", ".join(sorted(C.EVIDENCE_PLANS)))])
        report.next_action = "Run classify to pick a branch, then re-run evidence-plan."
        report.render()
        return 2

    families = [args.os_family] if args.os_family != "auto" else [
        fam for fam in ("linux", "windows") if plan.get(fam)]
    lines = ["The commands below are run by the customer, one at a time, in the guest console, an "
             "existing remote session, or a mounted repair environment. This release does not "
             "dispatch commands into the instance, and each command is a query that changes "
             "nothing.",
             "Paste the full output back, including headers; the identifiers and device names are "
             "the parts that decide the branch."]
    for family in families:
        for step in plan.get(family, ()):
            lines.append("[{0}] {1}".format(family, step["cmd"]))
            lines.append("      why: {0}   nature: {1}".format(step["why"], step["kind"]))
    if not any(plan.get(f) for f in families):
        lines.append("No read-only plan recorded for this branch and operating-system family; the "
                     "evidence has to come from the screen text and the console diagnosis.")
        report.degrade()
    report.section("Evidence plan for {0}".format(branch), lines)
    report.section("Handling the pasted output", [
        "Compare recorded identifiers against what exists before concluding anything about the "
        "volume; see references/fstab-and-devices.md for the mount-table branch.",
        "Never run a repair command copied from another machine or report against a device name "
        "that has not been confirmed on this one; the virtio and NVMe naming families differ by "
        "instance type, not by preference.",
        "If the customer declines to collect any item, mark the dependent conclusion as unsupported "
        "and report the gap.",
    ])
    report.next_action = "Customer runs the listed queries and pastes the output; then re-run " \
                         "classify or fstab-compare with it."
    report.render()
    return 0


# ---------------------------------------------------------------------------
# mount table comparison
# ---------------------------------------------------------------------------
def _read_blob(file_path, inline):
    if inline:
        return inline
    if file_path:
        if not os.path.isfile(file_path):
            return None
        with open(file_path, "r", errors="replace") as handle:
            return handle.read()
    return None


def parse_blkid(text):
    """Index the real devices, their identifiers, and their filesystem types."""
    by_uuid, by_label, by_partuuid, devices, fstype_of = {}, {}, {}, {}, {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        device, _, rest = line.partition(":")
        device = device.strip()
        if not device.startswith("/"):
            continue
        attrs = dict(re.findall(r'([A-Za-z_]+)="([^"]*)"', rest))
        devices[device] = attrs
        if attrs.get("UUID"):
            by_uuid[attrs["UUID"].lower()] = device
        if attrs.get("LABEL"):
            by_label[attrs["LABEL"].lower()] = device
        if attrs.get("PARTUUID"):
            by_partuuid[attrs["PARTUUID"].lower()] = device
        if attrs.get("TYPE"):
            fstype_of[device] = attrs["TYPE"]
    return by_uuid, by_label, by_partuuid, devices, fstype_of


def classify_mount_entry(fields, index, blkid_index):
    by_uuid, by_label, by_partuuid, devices, fstype_of = blkid_index
    device_token = fields[0]
    mount_point = fields[1] if len(fields) > 1 else ""
    fstype = fields[2] if len(fields) > 2 else ""
    options = fields[3].lower() if len(fields) > 3 else ""
    pass_field = fields[5] if len(fields) > 5 else ""
    lowered = device_token.lower()
    verdicts = []

    role = CRITICAL_MOUNTS.get(mount_point.lower())
    if role:
        verdicts.append("critical mount point ({0}): do not comment this line out to get past "
                        "emergency mode".format(role))
    else:
        verdicts.append("data-disk entry: the only safe candidate for a temporary unblock")

    resolved = None
    if lowered.startswith("uuid="):
        resolved = by_uuid.get(lowered.split("=", 1)[1].lower())
        kind = "by-uuid"
    elif lowered.startswith("label="):
        resolved = by_label.get(lowered.split("=", 1)[1].lower())
        kind = "by-label"
    elif lowered.startswith("partuuid="):
        resolved = by_partuuid.get(lowered.split("=", 1)[1].lower())
        kind = "by-partuuid"
    elif lowered.startswith("/dev/"):
        kind = "by-device-name"
        resolved = device_token if device_token in devices else None
        if not resolved and devices:
            listed = list(devices)
            entry_virtio = bool(re.match(r"/dev/vd[a-z]", device_token))
            entry_nvme = device_token.startswith("/dev/nvme")
            listed_virtio = any(d.startswith("/dev/vd") for d in listed)
            listed_nvme = any(d.startswith("/dev/nvme") for d in listed)
            if entry_virtio and listed_nvme and not listed_virtio:
                verdicts.append("the entry uses virtio-style naming while this instance only exposes "
                                "NVMe-style names; the same volume can be present under a different "
                                "name, so confirm it with the listing instead of assuming the "
                                "volume is gone")
            elif entry_nvme and listed_virtio and not listed_nvme:
                verdicts.append("the entry uses NVMe-style naming while this instance only exposes "
                                "virtio-style names; confirm the volume's real name from the "
                                "listing before acting on any repair command")
    else:
        kind = "token"
        if lowered in PSEUDO_FILESYSTEMS or lowered.split("=", 1)[0] in PSEUDO_FILESYSTEMS:
            resolved = device_token
        else:
            verdicts.append("column one is not a recognised device form, a persistent identifier, or "
                            "a known pseudo filesystem: {0}".format(device_token))
            verdicts.append("check for stray leading characters introduced by a previous edit, which "
                            "is a real and observed cause of a system that will not come up")

    if kind == "by-device-name" and not resolved:
        verdicts.append("device not present in the listing; on an instance restored from an image "
                        "this is usually an entry inherited for a data disk the restore never "
                        "carried")
    elif resolved:
        verdicts.append("resolves to {0}".format(resolved))
        actual_type = fstype_of.get(resolved)
        if actual_type and fstype and fstype.lower() not in ("swap", actual_type.lower()):
            verdicts.append("filesystem type recorded as {0} but the device reports {1}; the "
                            "mismatch is what makes the startup check reject the volume".format(
                                fstype, actual_type))

    if "nofail" in options:
        verdicts.append("carries a non-blocking option, so this entry alone would not stop the "
                        "boot; look elsewhere for the failing line")
    if "auto" in options and "noauto" not in options:
        verdicts.append("marked for automatic mounting at startup")
    if "errors=remount-ro" in options:
        verdicts.append("mount options protect the volume by remounting it read-only on recorded "
                        "errors; a read-only root here explains a system that starts but cannot "
                        "serve writes")
    if pass_field and pass_field not in ("0", ""):
        verdicts.append("an integrity check is scheduled for this entry at boot (pass field {0}); a "
                       "wrong type or identifier turns that into a startup failure".format(pass_field))

    return {
        "line": index,
        "device": device_token,
        "mount_point": mount_point,
        "fstype": fstype,
        "verdicts": verdicts,
        "resolvable": bool(resolved),
        "critical": bool(role),
    }


def cmd_fstab_compare(args):
    report = Report(args.session_id, as_json=args.json)
    fstab_text = _read_blob(args.fstab_file, args.fstab_text)
    blkid_text = _read_blob(args.blkid_file, args.blkid_text)
    if fstab_text is None:
        report.fail()
        report.section("Result", ["No mount table was supplied. Provide --fstab-file or "
                                  "--fstab-text with the verbatim contents the customer pasted."])
        report.next_action = "Ask the customer for the file contents and the device listing, then " \
                             "re-run fstab-compare."
        report.render()
        return 2
    if blkid_text is None:
        report.gap("No device listing was supplied, so entries can be checked for syntax and for "
                   "critical mount points but cannot be resolved against real devices.")
        report.degrade()

    blkid_index = parse_blkid(blkid_text)
    lines, candidates, critical_failures = [], [], []
    for index, raw in enumerate(fstab_text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            lines.append("line {0}: commented out -> {1}".format(index, stripped[:80]))
            continue
        fields = stripped.split()
        if len(fields) < 3:
            lines.append("line {0}: too few fields ({1}); this alone can make the file "
                         "unparseable".format(index, len(fields)))
            candidates.append((index, fields[:2], "malformed"))
            continue
        result = classify_mount_entry(fields, index, blkid_index)
        lines.append("line {0}: {1} -> {2} ({3})".format(index, result["device"],
                                                         result["mount_point"] or "n/a",
                                                         result["fstype"] or "n/a"))
        for verdict in result["verdicts"]:
            lines.append("      - {0}".format(verdict))
        if not result["resolvable"]:
            (critical_failures if result["critical"] else candidates).append(
                (index, result["device"], result["mount_point"]))

    report.section("Per-entry verdicts", lines or ["The file had no usable entries."])
    summary = []
    if candidates:
        summary.append("Boot-blocking candidates, in the order they should be considered: " +
                       "; ".join("line {0} ({1})".format(i, d) for i, d, _ in candidates))
        summary.append("Commenting out a data-disk entry is a temporary unblock performed by the "
                       "customer, and it must be recorded as such: the volume stays unmounted until "
                       "the entry is restored with an identifier that exists.")
    else:
        summary.append("Every non-critical entry resolved or looked well formed; if the system still "
                       "drops to emergency mode, the failing unit is named in the lines above the "
                       "prompt and may not be in this file at all.")
    if critical_failures:
        summary.append("CRITICAL: entries that cannot be resolved and are not safe to comment out: " +
                       "; ".join("line {0} ({1} -> {2})".format(i, d, m)
                                 for i, d, m in critical_failures))
        summary.append("A missing root, boot, or EFI partition entry means the boot path has to be "
                       "rebuilt rather than the line deleted; see "
                       "references/grub-efi-repair-guidance.md.")
    summary.append("Prefer persistent identifiers over device names: names depend on attachment "
                   "order and on the storage driver family of the instance type, which is why an "
                   "entry survives a reboot and dies at the next restore.")
    report.section("Summary", summary)
    report.next_action = "Customer corrects the named line themselves, then validates the edited " \
                         "file before the next reboot and reports which claim they hold."
    report.render()
    return 0


def cmd_handoff(args):
    report = Report(args.session_id, as_json=args.json)
    scored = match_branches(args.text or "")
    handoffs = [(s, e, h) for s, e, h in scored
                if C.BRANCHES[e["branch"]]["gate"] == "handoff"]
    lines = []
    if not handoffs:
        report.degrade()
        lines.append("No handoff rule matched the supplied text, and no in-scope branch was claimed "
                     "either. Do not route on a hunch: state what is missing.")
    for score, entry, hits in handoffs[:3]:
        branch = C.BRANCHES[entry["branch"]]
        lines.extend([
            "target: {0}".format(branch.get("target_skill", "the owning flow")),
            "reason from the evidence: {0}".format(entry["proves"]),
            "matched text: {0}".format(", ".join(sorted(set(hits)))),
            "what to hand over: the instance profile, the screen text, and the read-only output "
            "already collected, so the customer does not repeat them.",
            "phrasing: state what the evidence shows, then why it places the problem on another "
            "axis, then what to invoke next (references/handoff-map.md).",
            "",
        ])
    in_scope = [(s, e) for s, e, _ in scored if C.BRANCHES[e["branch"]]["gate"] == "in-scope"]
    if in_scope and handoffs:
        lines.append("Note: {0} also matched, which is a boot-path signal. If the system genuinely "
                     "will not come up, this skill keeps the case; if it is up, the handoff "
                     "above wins.".format(in_scope[0][1]["branch"]))
    report.section("Routing decision", lines)
    report.next_action = "Emit the handoff wording, or continue in this skill if the boot failure " \
                         "is confirmed."
    report.render()
    return 0


# ---------------------------------------------------------------------------
# argument parsing
# ---------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="boot_repair_guide.py",
        description="ECS boot-failure triage and manual repair guidance. Query-only cloud "
                    "surface; every change is performed by the customer.")
    parser.add_argument("--json", action="store_true", help="emit one JSON object instead of text")
    sub = parser.add_subparsers(dest="command")
    sub.required = True

    def add_common(target, region=True):
        if region:
            target.add_argument("--region-id", required=True, help="region of the instance")
        target.add_argument("--session-id", default=None,
                            help="reuse a session id when correlating several runs")

    p = sub.add_parser("profile", help="environment picture from the query surface")
    add_common(p)
    p.add_argument("--instance-id", action="append", required=True,
                   help="one or more instance ids")
    p.add_argument("--check-invocations", action="store_true",
                   help="also read Cloud Assistant history for each instance")
    p.set_defaults(func=cmd_profile)

    c = sub.add_parser("classify", help="step-0 gate plus branch ranking")
    c.add_argument("--region-id", default=None)
    c.add_argument("--instance-id", action="append", default=[])
    c.add_argument("--text", default="", help="verbatim console or VNC screen transcription")
    c.add_argument("--no-cloud", action="store_true",
                   help="classify from the screen text alone")
    c.add_argument("--session-id", default=None)
    c.set_defaults(func=cmd_classify)

    f = sub.add_parser("preflight", help="offline repair channel prerequisites")
    add_common(f)
    f.add_argument("--instance-id", required=True)
    f.add_argument("--rescue-instance-id", default=None)
    f.add_argument("--snapshot-progress", type=int, default=None,
                   help="customer-stated completion percentage of the newest usable snapshot")
    f.add_argument("--downtime-approved", action="store_true")
    f.add_argument("--credential-ready", action="store_true")
    f.set_defaults(func=cmd_preflight)

    s = sub.add_parser("rescue-stock", help="capacity check for the temporary rescue instance")
    add_common(s)
    s.add_argument("--zone-id", default=None)
    s.add_argument("--instance-type", default=None)
    s.add_argument("--network-category", default=None)
    s.set_defaults(func=cmd_rescue_stock)

    e = sub.add_parser("evidence-plan", help="the read-only queries the customer runs and pastes")
    e.add_argument("--branch", required=True, choices=sorted(C.EVIDENCE_PLANS))
    e.add_argument("--os-family", default="auto", choices=("auto", "linux", "windows"))
    e.add_argument("--session-id", default=None)
    e.set_defaults(func=cmd_evidence_plan)

    m = sub.add_parser("fstab-compare", help="compare a mount table against the real devices")
    m.add_argument("--fstab-file", default=None)
    m.add_argument("--fstab-text", default=None)
    m.add_argument("--blkid-file", default=None)
    m.add_argument("--blkid-text", default=None)
    m.add_argument("--session-id", default=None)
    m.set_defaults(func=cmd_fstab_compare)

    h = sub.add_parser("handoff", help="route a symptom that is not a boot failure")
    h.add_argument("--text", required=True)
    h.add_argument("--session-id", default=None)
    h.set_defaults(func=cmd_handoff)
    return parser


def _run_selftest():
    """Offline regression lock over the pure judgement core of this skill.

    Every expectation was recorded from the real behaviour of this file before
    it was pinned (probe round R73). Nothing here reaches the network: the
    cmd_* integrations use --no-cloud / no device listing and their stdout is
    captured so it does not pollute the selftest report.
    """
    import contextlib
    import io

    checks = {"n": 0, "fail": 0}

    def check(name, got, want):
        checks["n"] += 1
        if got != want:
            checks["fail"] += 1
            print("FAIL %s: got %r want %r" % (name, got, want))
        else:
            print("ok   %s" % name)

    def has(name, blob, needle):
        check(name, needle in blob, True)

    def _capture(fn, *a):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = fn(*a)
        return rc, buf.getvalue()

    # ---- _unwrap ------------------------------------------------------------
    check("uw_list", _unwrap({"a": {"b": [1, 2]}}, "a", "b"), [1, 2])
    check("uw_dict", _unwrap({"a": {"b": {"c": 1}}}, "a", "b"), [{"c": 1}])
    check("uw_missing", _unwrap({"a": {}}, "a", "b"), [])
    check("uw_none", _unwrap({"a": None}, "a"), [])
    check("uw_nondict_node", _unwrap("scalar", "a"), [])
    check("uw_scalar_leaf", _unwrap({"a": "x"}, "a"), [])

    # ---- parse_blkid --------------------------------------------------------
    blk = ("/dev/vda1: UUID=\"ABCD-1234\" TYPE=\"ext4\" PARTUUID=\"aa-1\" LABEL=\"rootlbl\"\n"
           "notadevice: UUID=\"zzz\"\n"
           "\n"
           "/dev/nvme0n1p1: UUID=\"ffff\" TYPE=\"xfs\"\n")
    by_uuid, by_label, by_partuuid, devices, fstype_of = parse_blkid(blk)
    check("pb_uuid_lower", by_uuid.get("abcd-1234"), "/dev/vda1")
    check("pb_label", by_label.get("rootlbl"), "/dev/vda1")
    check("pb_partuuid", by_partuuid.get("aa-1"), "/dev/vda1")
    check("pb_skips_nondev", sorted(devices), ["/dev/nvme0n1p1", "/dev/vda1"])
    check("pb_fstype", fstype_of.get("/dev/nvme0n1p1"), "xfs")
    check("pb_empty", parse_blkid(""), ({}, {}, {}, {}, {}))

    # ---- classify_mount_entry ----------------------------------------------
    idx = parse_blkid(blk)
    r_root = classify_mount_entry(["UUID=abcd-1234", "/", "ext4", "errors=remount-ro", "0", "1"],
                                  1, idx)
    check("cme_root_critical", r_root["critical"], True)
    check("cme_root_resolves", r_root["resolvable"], True)
    has("cme_root_text", " ".join(r_root["verdicts"]), "critical mount point (root)")
    has("cme_remount", " ".join(r_root["verdicts"]), "remounting it read-only")
    has("cme_pass", " ".join(r_root["verdicts"]), "pass field 1")

    r_label = classify_mount_entry(["LABEL=rootlbl", "/data", "ext4", "defaults", "0", "0"],
                                   2, idx)
    check("cme_label_resolves", r_label["resolvable"], True)
    has("cme_label_dev", " ".join(r_label["verdicts"]), "resolves to /dev/vda1")
    check("cme_label_no_mismatch", any("mismatch" in v for v in r_label["verdicts"]), False)

    r_mm = classify_mount_entry(["UUID=ffff", "/mnt", "ext4", "defaults", "0", "0"], 3, idx)
    has("cme_fstype_mismatch", " ".join(r_mm["verdicts"]), "the device reports xfs")

    r_swap = classify_mount_entry(["UUID=abcd-1234", "none", "swap", "defaults", "0", "0"],
                                  4, idx)
    check("cme_swap_no_mismatch", any("mismatch" in v for v in r_swap["verdicts"]), False)

    r_dn = classify_mount_entry(["/dev/vda1", "/x", "ext4", "defaults", "0", "0"], 5, idx)
    check("cme_device_present", r_dn["resolvable"], True)

    r_pu = classify_mount_entry(["PARTUUID=aa-1", "/y", "ext4", "defaults", "0", "0"], 6, idx)
    check("cme_partuuid_resolves", r_pu["resolvable"], True)

    r_proc = classify_mount_entry(["proc", "/proc", "proc", "defaults", "0", "0"], 7, idx)
    check("cme_pseudo_ok", r_proc["resolvable"], True)
    check("cme_pseudo_not_critical", r_proc["critical"], False)

    r_bad = classify_mount_entry(["weirdtoken", "/d", "ext4", "defaults", "0", "0"], 8, idx)
    check("cme_bad_token", r_bad["resolvable"], False)
    has("cme_bad_text", " ".join(r_bad["verdicts"]), "not a recognised device form")

    r_nofail = classify_mount_entry(["UUID=ffff", "/data", "xfs", "defaults,nofail", "0", "2"],
                                    9, idx)
    has("cme_nofail", " ".join(r_nofail["verdicts"]), "non-blocking option")

    # virtio entry against an all-NVMe listing -> naming-drift warning
    idx_nvme = parse_blkid("/dev/nvme1n1: UUID=\"n1\" TYPE=\"ext4\"\n")
    r_virt = classify_mount_entry(["/dev/vdb1", "/mnt", "ext4", "defaults", "0", "0"],
                                  10, idx_nvme)
    has("cme_virtio_vs_nvme", " ".join(r_virt["verdicts"]), "virtio-style naming")
    check("cme_virtio_unresolved", r_virt["resolvable"], False)
    # NVMe entry against an all-virtio listing -> reverse warning
    idx_virt = parse_blkid("/dev/vda1: UUID=\"v1\" TYPE=\"ext4\"\n")
    r_nvme = classify_mount_entry(["/dev/nvme0n1p1", "/mnt", "ext4", "defaults", "0", "0"],
                                  11, idx_virt)
    has("cme_nvme_vs_virtio", " ".join(r_nvme["verdicts"]), "NVMe-style naming")

    # ---- match_branches ----------------------------------------------------
    check("mb_empty", match_branches(""), [])
    check("mb_negative", match_branches("zzqq xxvv nothing-matches-here"), [])
    multi = next((e for e in C.ERROR_PATTERNS if len(e["patterns"]) >= 2), None)
    if multi is not None:
        scored = match_branches(" ".join(multi["patterns"][:2]))
        check("mb_top_branch", scored[0][1]["branch"], multi["branch"])
        check("mb_top_score", scored[0][0], 2)
    else:  # pragma: no cover - data guard, would signal a catalog regression
        check("mb_multi_present", False, True)

    # ---- helpers -----------------------------------------------------------
    check("lf_eol", _lifecycle_flag({"OSName": "CentOS 7.9 64-bit"}), ["centos 7"])
    check("lf_supported", _lifecycle_flag({"OSName": "Ubuntu 22.04 64-bit"}), [])
    check("bf_burst", _burstable_flag({"InstanceTypeFamily": "ecs.t6"}), "ecs.t6")
    check("bf_general", _burstable_flag({"InstanceTypeFamily": "ecs.g7"}), "")
    check("pip_multi", _private_ip({"VpcAttributes": {"PrivateIpAddress": {"IpAddress": ["10.0.0.5"]}}}),
          "10.0.0.5")
    check("pip_none", _private_ip({}), "n/a")
    check("pub_normal", _public_ip({"PublicIpAddress": {"IpAddress": ["47.1.1.1"]}}), "47.1.1.1")
    check("pub_eip", _public_ip({"EipAddress": {"IpAddress": "47.2.2.2"}}), "47.2.2.2")
    check("pub_none", _public_ip({}), "n/a")

    # ---- Report status transitions -----------------------------------------
    rep = Report("0" * 32)
    check("rep_ok_init", rep.status, C.STATUS_OK)
    rep.degrade()
    check("rep_degraded", rep.status, C.STATUS_DEGRADED)
    rep.fail()
    check("rep_fail", rep.status, C.STATUS_FAIL)

    fstab_text = ("UUID=missing-uuid / ext4 defaults 0 1\n"
                  "UUID=also-missing /data xfs defaults 0 2\n")

    def fa(fname=None, ftext=None, bname=None, btext=None, js=False):
        return argparse.Namespace(fstab_file=fname, fstab_text=ftext,
                                  blkid_file=bname, blkid_text=btext,
                                  session_id="0" * 32, json=js)

    rc, out = _capture(cmd_fstab_compare, fa(ftext=fstab_text))
    check("fstab_rc", rc, 0)
    has("fstab_critical_root", out, "CRITICAL:")
    has("fstab_status", out, "STATUS: DEGRADED")

    rc, out = _capture(cmd_fstab_compare, fa())
    check("fstab_no_input_rc", rc, 2)
    has("fstab_no_input_status", out, "STATUS: FAIL")

    def ca(text, js=False):
        return argparse.Namespace(region_id=None, instance_id=[], text=text,
                                  no_cloud=True, session_id="0" * 32, json=js)

    rc, out = _capture(cmd_classify, ca(""))
    check("classify_unknown_rc", rc, 3)
    has("classify_degraded", out, "STATUS: DEGRADED")
    if multi is not None:
        rc, out = _capture(cmd_classify, ca(" ".join(multi["patterns"][:2])))
        check("classify_match_rc", rc, 0)
        has("classify_branch", out, multi["branch"])

    # --json emit must be valid JSON carrying the result tail
    rc, out = _capture(cmd_fstab_compare, fa(ftext=fstab_text, js=True))
    try:
        payload = json.loads(out)
        check("fstab_json_status", payload["status"], C.STATUS_DEGRADED)
    except ValueError:
        check("fstab_json_parses", out[:40], "valid json")

    print("SELFTEST: %d checks, %d failures" % (checks["n"], checks["fail"]))
    return 0 if checks["fail"] == 0 else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--selftest":
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "session_id", None):
        args.session_id = _cli.new_session_id()
    if not re.fullmatch(r"[0-9a-f]{32}", args.session_id or ""):
        parser.exit(2, "session id must be the 32 hex characters echoed by a previous run\n")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
