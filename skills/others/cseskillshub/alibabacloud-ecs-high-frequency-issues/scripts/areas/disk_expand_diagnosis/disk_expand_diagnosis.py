#!/usr/bin/env python3
"""Entry point for ECS cloud disk expansion and partition/filesystem diagnosis.

The agent runs only this script; it never assembles aliyun CLI calls by hand.
Every cloud fact comes from the calls below, every judgement comes from the
tables in ``_constants.py`` or from output the customer pasted in, and every run
ends with a ``STATUS:`` / ``NEXT_ACTION:`` contract.
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import re
import sys

import _constants as C
import sts_token
from _cli import CliError, call_ecs, new_session_id, user_agent_for

_DEVICE_RE = re.compile(r"/dev/(vd[a-z]+|xvd[a-z]+|sd[a-z]+|nvme\d+n\d+)(p?\d+)?\b")
_BARE_DEVICE_RE = re.compile(
    r"\b(vd[a-z]|xvd[a-z]|sd[a-z]|nvme\d+n\d+)(p?[1-9]\d*)?\b"
)
_FSTYPE_RE = re.compile(r"\b(ext[234]|xfs|btrfs|swap|ntfs|fat32|vfat)\b", re.IGNORECASE)
_PERCENT_RE = re.compile(r"^\d{1,3}%$")
_SOURCE_FS_RE = re.compile(r"^(?:/dev/|overlay|tmpfs|devtmpfs|shm)", re.IGNORECASE)
_REAL_FSTYPES = ("ext4", "ext3", "ext2", "xfs", "btrfs")
_BOX_DRAWING = ("\u2514\u2500", "\u251c\u2500", "\u2502")

_AUTO_EXACT_LOWER = frozenset(command.lower() for command in C.AUTO_GUEST_COMMAND_EXACT)
_AUTO_FAMILIES_LOWER = dict(
    (name.lower(), tuple(option.lower() for option in options))
    for name, options in C.AUTO_GUEST_COMMAND_FAMILIES.items()
)


# ---------------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------------
def _first(mapping, *keys, **kwargs):
    default = kwargs.get("default", "UNKNOWN")
    if not isinstance(mapping, dict):
        return default
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return default


def _as_int(value, default=None):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def partition_device(disk_device, suffix):
    """Build the partition node name for both guest device-naming families."""
    if suffix is None:
        return disk_device
    base = disk_device.rsplit("/", 1)[-1]
    cleaned = suffix.lstrip("p")
    if base.startswith(("nvme", "md")):
        return "{0}p{1}".format(disk_device, cleaned)
    return "{0}{1}".format(disk_device, cleaned)


def _has_partition_number(device):
    """True only for a partition node, never for a whole-disk node."""
    base = device.rsplit("/", 1)[-1]
    if base.startswith("nvme"):
        return bool(re.match(r"^nvme\d+n\d+p[1-9]\d*$", base))
    return bool(re.match(r"^(?:vd|xvd|sd)[a-z][1-9]\d*$", base))


def _device_from_token(token):
    """Normalise one device token to ``/dev/<disk>[p]<n>``, or return None."""
    if not token:
        return None
    token = token.strip(":,;")
    if token.startswith("/dev/"):
        match = _DEVICE_RE.search(token)
        if not match:
            return None
        return partition_device("/dev/{0}".format(match.group(1)), match.group(2))
    match = _BARE_DEVICE_RE.fullmatch(token)
    if not match:
        return None
    return partition_device("/dev/{0}".format(match.group(1)), match.group(2))


def _clean_line(line):
    for box in _BOX_DRAWING:
        line = line.replace(box, " ")
    return line


class Run(object):
    """Accumulates findings, limitations and assumptions for one invocation."""

    def __init__(self, session_id):
        self.session_id = session_id
        self.findings = []
        self.guest = {}
        self.signals = []
        self.manual_steps = []
        self.handoffs = []
        self.limits = []
        self.assumptions = []
        self.snapshot_confirmed = None
        self.verdicts = []
        self.status = C.STATUS_OK
        self.next_action = C.NEXT_ACTION_NONE

    def degrade(self, action=None, note=None):
        if self.status == C.STATUS_OK:
            self.status = C.STATUS_DEGRADED
        if action:
            self.next_action = action
        if note:
            self.limits.append(note)

    def fail(self, action, note):
        self.status = C.STATUS_FAILED
        self.next_action = action
        self.limits.append(note)

    def add_verdict(self, verdict):
        if verdict not in self.verdicts:
            self.verdicts.append(verdict)

    @property
    def snapshot_status(self):
        if self.snapshot_confirmed:
            return "CONFIRMED: {0}".format(self.snapshot_confirmed)
        if C.VERDICT_TARGET_NOT_FOUND in self.verdicts:
            # The snapshot precondition guards a change to a known disk. With no
            # disk identified there is nothing to protect yet, so asking the
            # customer for a snapshot here would be about a target this run never
            # found.
            return ("NOT_APPLICABLE - no target disk was identified, so the "
                    "snapshot precondition is not reached yet")
        return (
            "NOT_CONFIRMED - a fresh snapshot of the target disk is a precondition "
            "for every partition or filesystem step below "
            "(see references/disk-expand-diagnosis__snapshot-first.md)"
        )


# ---------------------------------------------------------------------------
# cloud side
# ---------------------------------------------------------------------------
def fetch_disks(region_id, instance_id, disk_id, session_id):
    params = {"RegionId": region_id}
    if disk_id:
        params["DiskIds"] = json.dumps([disk_id])
    elif instance_id:
        params["InstanceId"] = instance_id
    payload = call_ecs("DescribeDisks", params, session_id)
    body = _first(payload, "Disks", default={})
    if isinstance(body, dict):
        body = body.get("Disk") or []
    return body if isinstance(body, list) else []


def fetch_instances(region_id, instance_id, session_id):
    params = {"RegionId": region_id}
    if instance_id:
        params["InstanceIds"] = json.dumps([instance_id])
    payload = call_ecs("DescribeInstances", params, session_id)
    body = _first(payload, "Instances", default={})
    if isinstance(body, dict):
        body = body.get("Instance") or []
    return body if isinstance(body, list) else []


def _region_hint(disks):
    return _first(disks[0], "RegionId") if disks else "UNKNOWN"


# A denial message quotes the action it refused, next to a resource ARN that
# carries the account id and `*:…` sequences. Only the code and the action are
# ever repeated back, so the report can name the grant without transcribing
# the ARN. The `<code>: <action>` shape is also what the shared report layer
# reads, so the answer gains the grant path instead of only the refusal word.
_DENIED_ACTION_RE = re.compile(
    r"[Aa]ction:\s*([a-z][a-z0-9_-]*:[A-Za-z][A-Za-z0-9]*)")


def denied_action(message):
    match = _DENIED_ACTION_RE.search(message or "")
    return match.group(1) if match else None


def denial_phrase(code, action):
    if action:
        return "{0}: {1}".format(code, action)
    return "{0}: the response did not name the action".format(code)


def read_failure_note(read, action, exc):
    """One failed cloud read, reported as a refusal or as a failure."""
    if exc.is_auth_denied:
        return ("{0} was refused ({1}), so what that read would have settled is "
                "unverified; the minimal fragment for the grant is in "
                "references/ram-policies.md.".format(
                    read, denial_phrase(exc.code, action))
                )
    return ("{0} failed ({1}), so the cloud-side classification is unavailable. "
            "When the code is {2}, the missing permission is {3}; see "
            "references/ram-policies.md.".format(
                read, exc.code, C.AUTH_DENIED_CODES[0], action))


def classify_cloud_side(disks, instances, disk_id, instance_id, expected_gib, run):
    """Map cloud facts onto one of the C1 verdicts.

    The distinction that matters most in this tier is "the change never landed"
    versus "it landed and the guest is the missing step". Confusing those two is
    what keeps customers hunting for a resize entry point that correctly no
    longer exists.
    """
    target = None
    if disk_id:
        target = next((d for d in disks if _first(d, "DiskId") == disk_id), None)
        if target is None:
            run.add_verdict(C.VERDICT_TARGET_NOT_FOUND)
            run.findings.append(
                "Disk {0} was not returned for region {1}. A wrong region is the "
                "usual cause, so confirm it before drawing any conclusion.".format(
                    disk_id, _region_hint(disks)
                )
            )
            return None
    elif disks:
        if instance_id:
            target = next(
                (d for d in disks if _first(d, "InstanceId") == instance_id), None
            )
        target = target or disks[0]

    if target is None:
        run.add_verdict(C.VERDICT_TARGET_NOT_FOUND)
        run.findings.append(
            "No disk came back for this region and resource pair, so nothing about "
            "the resize can be confirmed from the cloud side yet."
        )
        return None

    size_gib = _as_int(_first(target, "Size", "Capacity"))
    facts = {
        "disk_id": _first(target, "DiskId"),
        "cloud_size_gib": size_gib,
        "category": _first(target, "Category", "DiskCategory"),
        "disk_type": str(_first(target, "Type", "DiskType")).upper(),
        "status": _first(target, "Status"),
        "attached_instance": _first(target, "InstanceId"),
        "device": _first(target, "Device"),
        "portable": _first(target, "Portable"),
        "auto_snapshot_policy": _first(target, "AutoSnapshotPolicyId"),
        "enable_auto_snapshot": _first(target, "EnableAutoSnapshot"),
        "instance_status": "UNKNOWN",
        "os_family": "UNKNOWN",
    }
    run.findings.append(
        "Cloud side: disk {0} reports {1} GiB (category {2}, type {3}, status {4}, "
        "attached instance {5}, console device {6}).".format(
            facts["disk_id"], facts["cloud_size_gib"], facts["category"],
            facts["disk_type"], facts["status"], facts["attached_instance"],
            facts["device"],
        )
    )
    run.findings.append(
        "Auto snapshot fields on this disk: enable={0} policy={1}. Those say nothing "
        "about whether a manual snapshot exists right now, so they are never treated "
        "as the pre-change backup.".format(
            facts["enable_auto_snapshot"], facts["auto_snapshot_policy"]
        )
    )

    wanted_instance = instance_id or facts["attached_instance"]
    if wanted_instance in (None, "", "UNKNOWN"):
        wanted_instance = None

    instance = None
    if instances and wanted_instance:
        instance = next(
            (i for i in instances if _first(i, "InstanceId") == wanted_instance),
            None,
        )
    if instances and instance is None:
        run.limits.append(
            "DescribeInstances returned {0} instance(s), none of which is the "
            "instance this disk reports as attached, so no operating system family "
            "and no power state was attributed to the disk. Taking one from an "
            "unrelated instance would be worse than reporting the gap: the Linux "
            "versus Windows branch stays undecided until the instance is "
            "confirmed.".format(len(instances))
        )

    if instance is not None:
        state = _first(instance, "Status")
        facts["instance_status"] = state
        facts["os_family"] = str(_first(instance, "OSType", "OSNameEn", "OSName"))
        run.findings.append(
            "Instance {0} reports status {1} and OS family {2}.".format(
                _first(instance, "InstanceId"), state, facts["os_family"]
            )
        )
        if state not in ("Running", "Stopped", "UNKNOWN"):
            run.add_verdict(C.VERDICT_INSTANCE_STATE_BLOCKED)
            run.handoffs.append(
                C.HANDOFFS["area:instance-state-diagnosis"]
            )
            run.findings.append(
                "The instance sits in {0}, an intermediate power state. That has to "
                "settle before any partition work, and startup behaviour is another "
                "tier's problem.".format(state)
            )
        elif state == "Stopped":
            run.findings.append(
                "The instance is stopped, so in-guest commands cannot run right now. "
                "Starting it is a deliberate customer action, not something this "
                "skill performs."
            )

    if facts["disk_type"] == "DATA" and facts["status"] == "Available":
        run.add_verdict(C.VERDICT_SUSPECTED_NEW_DISK)
        run.findings.append(
            "The target data disk is in status Available, meaning created but not "
            "attached. A disk bought alongside the original one, rather than the "
            "original one being extended, looks exactly like this from the inside."
        )
        run.handoffs.append(
            {
                "target": "new data disk attach and initialization (outside this tier)",
                "phrase": (
                    "Attach and initialize the disk first. Formatting a device "
                    "erases it, so this diagnosis never emits a format command; use "
                    "the attach-a-data-disk and Linux initialization documentation, "
                    "and return to resizing only once the disk is attached and "
                    "mounted."
                ),
            }
        )
        return facts

    if expected_gib is None:
        run.degrade(
            C.NEXT_ACTION_ASK_REGION,
            "The expected post-resize size is missing, so the cloud side cannot be "
            "classified as landed or not landed. Ask what size was purchased.",
        )
        run.add_verdict(C.VERDICT_UNKNOWN)
        return facts

    if size_gib is None:
        run.limits.append(
            "The size field was absent from the response, so no numeric comparison "
            "was made instead of assuming a value."
        )
        run.add_verdict(C.VERDICT_UNKNOWN)
        return facts

    if size_gib < expected_gib:
        run.add_verdict(C.VERDICT_CLOUD_NOT_RESIZED)
        run.findings.append(
            "Cloud side is still at {0} GiB against an expected {1} GiB: the "
            "capacity change itself has not landed, so anything inside the operating "
            "system is moot until it does.".format(size_gib, expected_gib)
        )
    else:
        run.add_verdict(C.VERDICT_CLOUD_RESIZED_OS_STUCK)
        run.findings.append(
            "Cloud side already reports {0} GiB against an expected {1} GiB, so the "
            "capacity change has landed. Not finding a resize entry point in the "
            "console is the expected state here, not evidence of a failed order: the "
            "outstanding work is the partition and the filesystem inside the "
            "guest.".format(size_gib, expected_gib)
        )

    if len(disks) > 1:
        run.assumptions.append(
            "{0} disks were visible for this resource and the analysis used {1}. If "
            "that is not the disk you extended, pass --disk-id explicitly.".format(
                len(disks), facts["disk_id"]
            )
        )
    return facts


# ---------------------------------------------------------------------------
# guest side
# ---------------------------------------------------------------------------
def scan_signals(text):
    if not text:
        return []
    lowered = text.lower()
    return [s for s in C.ERROR_SIGNALS if s["pattern"].lower() in lowered]


def parse_guest_readings(text):
    """Extract what the pasted output actually shows, and nothing more.

    Deliberately tolerant of the shapes ``lsblk -f``, ``blkid``, ``df -Th`` and
    ``fdisk -lu`` produce, since that is the material customers paste. Anything
    absent from the text stays absent rather than being inferred.
    """
    readings = {
        "devices": [],
        "filesystems": {},
        "mounts": {},
        "inode_full": False,
        "space_full": False,
        "has_lvm": False,
        "has_logical_partition": False,
        "partition_table": "UNKNOWN",
        "partitions_per_disk": {},
    }
    if not text:
        return readings

    devices = set()
    for line in text.splitlines():
        line = _clean_line(line)
        for token in line.split():
            device = _device_from_token(token)
            if device:
                devices.add(device)
        if "LVM2" in line or "/dev/mapper/" in line or "Linux LVM" in line:
            readings["has_lvm"] = True
        if re.search(r"\bextended\b", line, re.IGNORECASE):
            readings["has_logical_partition"] = True
        if re.search(r"table type:\s*gpt|\bGPT\b", line):
            readings["partition_table"] = "gpt"
        elif readings["partition_table"] == "UNKNOWN" and re.search(r"\bdos\b|MBR", line, re.I):
            readings["partition_table"] = "dos"

        fstype_match = _FSTYPE_RE.search(line)
        if fstype_match:
            for token in line.split():
                device = _device_from_token(token)
                if device:
                    readings["filesystems"].setdefault(
                        device, fstype_match.group(1).lower()
                    )
                    break

    readings["devices"] = sorted(devices)

    # df tables: source device first, mount point last, one percentage column.
    inode_context = "IUse%" in text or "Inodes" in text
    for line in text.splitlines():
        fields = _clean_line(line).split()
        if len(fields) < 4 or not _SOURCE_FS_RE.match(fields[0]):
            continue
        percents = [field for field in fields if _PERCENT_RE.match(field)]
        if not percents:
            continue
        device = _device_from_token(fields[0]) or fields[0]
        readings["mounts"].setdefault(device, fields[-1])
        if int(percents[-1][:-1]) >= 100:
            if inode_context:
                readings["inode_full"] = True
            else:
                readings["space_full"] = True

    per_disk = {}
    for device in devices:
        if not _has_partition_number(device):
            continue
        match = _DEVICE_RE.match(device)
        if match:
            disk = "/dev/{0}".format(match.group(1))
            per_disk[disk] = per_disk.get(disk, 0) + 1
    readings["partitions_per_disk"] = per_disk
    return readings


def detect_fstype(readings, device=None):
    """Filesystem type for the exact device, never a type borrowed from another."""
    filesystems = readings.get("filesystems") or {}
    if device:
        return filesystems.get(device)
    for known, fstype in sorted(filesystems.items()):
        if fstype in _REAL_FSTYPES:
            return fstype
    return None


def detect_target_device(readings, mount=None):
    """Prefer the device behind the requested mount point, else the one on ``/``."""
    filesystems = readings.get("filesystems") or {}
    mounts = readings.get("mounts") or {}
    if mount:
        wanted = mount.rstrip("/") or "/"
        for device, point in mounts.items():
            if (point.rstrip("/") or "/") == wanted and _has_partition_number(device):
                return device
        for device, point in mounts.items():
            if (point.rstrip("/") or "/") == wanted:
                return device
    for device, point in mounts.items():
        if (point.rstrip("/") or "/") == "/" and _has_partition_number(device):
            return device
    for device in sorted(filesystems):
        if _has_partition_number(device):
            return device
    for device in readings.get("devices", []):
        if _has_partition_number(device):
            return device
    return None


def capacity_gap_note(expected_gib):
    """Why the guest number sits below the number on the order."""
    decimal_equivalent = expected_gib * 1.073741824
    return (
        "A guest figure below the purchased {0} GiB is expected until the partition "
        "and the filesystem are grown, and a residual gap afterwards is normal too: "
        "the console counts binary GiB while several tools print decimal GB ({0} GiB "
        "is about {1:.2f} GB), and the filesystem reserves capacity for its own "
        "metadata plus blocks held back for the privileged user. Judge this as units "
        "and overhead, not as capacity that went missing.".format(
            expected_gib, decimal_equivalent
        )
    )


# ---------------------------------------------------------------------------
# plan generation
# ---------------------------------------------------------------------------
def build_linux_steps(target_device, fstype, mountpoint):
    """Emit one partition command plus the matching filesystem command.

    The device form and the filesystem-specific tool are the two places support
    cases show customers failing, so both are written out in full rather than
    left as a placeholder.
    """
    steps = []
    if not target_device:
        steps.append(
            "Establish the layout first. Run lsblk -f and blkid inside the instance "
            "and paste both outputs back: the device form and the filesystem type "
            "decide which command is correct, and this skill will not guess either."
        )
        return steps

    if not _has_partition_number(target_device):
        steps.append(
            "{0} is a whole device or a logical volume, not a numbered partition. "
            "That layout is not automated by this tier: confirm with lsblk -f and let "
            "a human choose the target object, because growing the wrong one is a "
            "data event.".format(target_device)
        )
        return steps

    target_device = _device_from_token(target_device) or target_device
    match = _DEVICE_RE.search(target_device)
    if not match:
        steps.append(
            "Confirm the device name with lsblk -f first: {0} is not a recognisable "
            "/dev/ partition node, and the growpart pairing depends on the exact "
            "disk plus partition form.".format(target_device)
        )
        return steps
    disk_device = "/dev/{0}".format(match.group(1))
    partition_number = (match.group(2) or "").lstrip("p")

    steps.append(
        "Grow the partition: sudo LC_ALL=en_US.UTF-8 growpart {0} {1}  -- note the "
        "single space between the device name and the partition number. Writing them "
        "together is the most common failure at this step.".format(
            disk_device, partition_number
        )
    )

    if fstype in ("ext4", "ext3", "ext2"):
        steps.append("Grow the filesystem: sudo resize2fs {0}".format(target_device))
    elif fstype == "xfs":
        steps.append(
            "Grow the filesystem: sudo xfs_growfs {0}  -- xfs is grown through its "
            "mount point, not its device node, and resize2fs must never be run "
            "against xfs.".format(mountpoint or "<mount point of {0}>".format(target_device))
        )
    elif fstype == "btrfs":
        steps.append(
            "Grow the mounted btrfs filesystem at {0} with its own resize commands; "
            "this skill does not automate btrfs.".format(mountpoint or "<mount point>")
        )
    else:
        steps.append(
            "No filesystem command is emitted, because the filesystem type is "
            "undetermined. Confirm it with blkid or lsblk -f first: ext families take "
            "resize2fs, xfs takes xfs_growfs, and picking by guess wastes a change "
            "window and can look like a new fault."
        )
    steps.append(
        "Verify inside the guest with df -h. On Linux the console disk page and any "
        "Windows-style disk management wording are not the verification step."
    )
    return steps


def build_windows_steps(drive_hint):
    target = drive_hint or "the affected drive letter"
    return [
        "Open Disk Management (diskmgmt.msc), locate {0}, and confirm an Unallocated "
        "block exists immediately to its RIGHT on the SAME disk.".format(target),
        "Only when that block is adjacent: right-click the volume, choose Extend "
        "Volume, and accept the default that consumes all of the unallocated space.",
        "If no unallocated block appears at all, use Action then Rescan Disks before "
        "concluding the space vanished. An older guest sometimes needs an instance "
        "restart to re-enumerate the disk, and that restart is a business decision "
        "this skill neither makes nor executes.",
        "If Extend Volume is greyed out while unallocated space does exist, that "
        "space is either on the left or on another disk, and native tooling stops "
        "there. What remains is third-party partition software, which carries real "
        "data-loss risk, or deleting the blocking volume, which is destructive and "
        "requires first verifying the data on it is disposable. Both are human "
        "operations behind a fresh snapshot.",
        "Cross-disk moves are not possible: capacity cannot be shifted from one cloud "
        "disk to another, and the platform cannot shrink or relocate an existing "
        "partition.",
        "Verify with Get-Volume or a refreshed Disk Management view.",
    ]


# ---------------------------------------------------------------------------
# guest command gate
# ---------------------------------------------------------------------------
def check_command_gate(command, justify=None):
    """Decide whether one guest command may be dispatched automatically."""
    text = " ".join((command or "").split()).strip()
    if not text:
        return False, "No command was supplied."
    for meta in C.SHELL_METACHARACTERS:
        if meta in text:
            return False, (
                "The input contains {0!r}. Anything with shell composition is "
                "refused, so no mutating step can ride along inside a listing "
                "command.".format(meta)
            )
    lowered = text.lower()
    for banned in C.NEVER_AUTO_GUEST_COMMANDS:
        if re.search(r"(?<![\w-])" + re.escape(banned.lower()) + r"\b", lowered):
            return False, (
                "`{0}` changes partition, filesystem or instance state. This skill "
                "documents it as a human step and never executes it.".format(banned)
            )
    for human_only in C.HUMAN_ONLY_GUEST_COMMANDS:
        if lowered == human_only.lower() or lowered.startswith(human_only.lower() + " "):
            return False, (
                "`{0}` is not approved for automated execution in this tier. Run it "
                "yourself inside the instance and paste the output back; the analysis "
                "continues from there.".format(human_only)
            )
    if lowered in _AUTO_EXACT_LOWER:
        return True, "exact non-mutating command on the approved list"
    if lowered.startswith(C.AUTO_FSUTIL_QUERY_PREFIXES):
        return True, "non-mutating fsutil query subcommand"

    argv = text.split()
    program = argv[0]
    allowed_options = _AUTO_FAMILIES_LOWER.get(program.lower())
    if allowed_options is None:
        return False, (
            "`{0}` is outside the approved non-mutating command set for this "
            "skill.".format(program)
        )
    for token in argv[1:]:
        if token.startswith("-") or token.startswith("+"):
            name = token.split("=", 1)[0].lower()
            if name not in allowed_options:
                return False, (
                    "Option `{0}` is not on the approved list for `{1}`.".format(
                        token.split("=", 1)[0], program
                    )
                )
    if program.lower() in ("du", "lsof") and not justify:
        return False, (
            "`{0}` belongs primarily to the disk capacity tier. It is allowed here "
            "only when a space or inode shortage looks like the thing blocking the "
            "resize, then once, followed by a hand-off. Re-run with --justify "
            "recording why it is needed.".format(program)
        )
    return True, "single non-mutating command from the approved set"


def submit_run_command(region_id, instance_id, command, session_id):
    params = {
        "RegionId": region_id,
        "Type": "RunShellScript",
        "CommandContent": command,
        "InstanceId.1": instance_id,
        "Name": "{0}-inspect".format(C.SKILL_NAME),
        "Description": "Non-mutating inspection issued by {0}".format(C.SKILL_NAME),
    }
    return call_ecs("RunCommand", params, session_id, write=True)


# ---------------------------------------------------------------------------
# report rendering
# ---------------------------------------------------------------------------
def render(run, args):
    lines = ["=== ECS DISK EXPAND DIAGNOSIS ==="]
    lines.append("session_id: {0}".format(run.session_id))
    lines.append("user_agent: {0}".format(user_agent_for(run.session_id)))
    if getattr(args, "region_id", None):
        lines.append("region: {0}".format(args.region_id))

    lines.append("")
    lines.append("[Evidence]")
    lines.extend("  - {0}".format(f) for f in (run.findings or ["none collected"]))

    # The signal table describes the pasted text. When nothing was pasted, a
    # section saying "no known error signal string appeared in the input" reports
    # on an input the customer never sent.
    if run.signals or getattr(args, "paste", None):
        lines.append("")
        lines.append("[Matched error signals]")
        if run.signals:
            for signal in run.signals:
                lines.append(
                    "  - {0} (confidence: {1})".format(signal["id"], signal["confidence"])
                )
                lines.append("      meaning: {0}".format(signal["meaning"]))
                lines.append("      handling: {0}".format(signal["disposition"]))
                for cause in signal.get("secondary_causes") or ():
                    lines.append("      also rule out: {0}".format(cause))
        else:
            lines.append("  - no known error signal string appeared in the input")

    lines.append("")
    lines.append("[Verdict]")
    lines.extend("  - {0}".format(v) for v in (run.verdicts or [C.VERDICT_UNKNOWN]))

    lines.append("")
    lines.append("[Snapshot status]")
    lines.append("  - {0}".format(run.snapshot_status))

    if run.manual_steps:
        lines.append("")
        lines.append("[Manual steps, for a human to execute]")
        for index, step in enumerate(run.manual_steps, start=1):
            lines.append("  {0}. {1}".format(index, step))

    if run.handoffs:
        lines.append("")
        lines.append("[Outside this tier: hand off]")
        for handoff in run.handoffs:
            if handoff.get("phrase"):
                lines.append("  - {0}".format(handoff["phrase"]))
                lines.append("    owner: {0}".format(handoff["target"]))
            else:
                lines.append("  - {0}".format(handoff["target"]))

    lines.append("")
    lines.append("[Assumptions and auto-filled inputs]")
    lines.extend("  - {0}".format(a) for a in (run.assumptions or ["none"]))

    lines.append("")
    lines.append("[Confidence and limits]")
    lines.extend("  - {0}".format(l) for l in (run.limits or ["none recorded"]))

    lines.append("")
    lines.append("STATUS: {0}".format(run.status))
    lines.append("NEXT_ACTION: {0}".format(run.next_action))
    return "\n".join(lines)


def to_json(run, args):
    return {
        "session_id": run.session_id,
        "user_agent": user_agent_for(run.session_id),
        "region": getattr(args, "region_id", None),
        "findings": run.findings,
        "signals": [
            {key: signal[key] for key in ("id", "confidence", "verdict", "meaning", "disposition")}
            for signal in run.signals
        ],
        "verdicts": run.verdicts,
        "guest": run.guest,
        "snapshot_status": run.snapshot_status,
        "manual_steps": run.manual_steps,
        "handoffs": run.handoffs,
        "assumptions": run.assumptions,
        "limits": run.limits,
        "STATUS": run.status,
        "NEXT_ACTION": run.next_action,
    }


def emit(run, args):
    if args.json:
        print(json.dumps(to_json(run, args), indent=2, ensure_ascii=False))
    else:
        print(render(run, args))
    if run.status == C.STATUS_OK:
        return 0
    return 2 if run.status == C.STATUS_FAILED else 1


def read_paste(location):
    if not location:
        return ""
    if location == "-":
        return sys.stdin.read()
    with open(location, "r") as handle:
        return handle.read()


# ---------------------------------------------------------------------------
# analysis orchestration
# ---------------------------------------------------------------------------
def analyze_guest_text(run, text):
    run.signals = scan_signals(text)
    run.guest = parse_guest_readings(text)
    readings = run.guest

    if readings.get("devices"):
        run.findings.append(
            "Devices named in the pasted output: {0}".format(
                ", ".join(readings["devices"][:12])
            )
        )
    if readings.get("filesystems"):
        run.findings.append(
            "Filesystems named in the pasted output: {0}".format(
                ", ".join(
                    "{0}={1}".format(device, fstype)
                    for device, fstype in sorted(readings["filesystems"].items())
                )
            )
        )
    if readings.get("mounts"):
        run.findings.append(
            "Mount points named: {0}".format(
                ", ".join(
                    "{0}->{1}".format(device, point)
                    for device, point in sorted(readings["mounts"].items())
                )
            )
        )
    if readings.get("partition_table") != "UNKNOWN":
        run.findings.append(
            "Partition table indicated by the pasted output: {0}".format(
                readings["partition_table"]
            )
        )
    for disk, count in sorted((readings.get("partitions_per_disk") or {}).items()):
        if count >= 4:
            run.findings.append(
                "{0} shows {1} partitions in the pasted output. On an MBR disk four "
                "primary partitions is the ceiling, which is worth stating before "
                "anyone plans another one.".format(disk, count)
            )
    if readings.get("has_lvm"):
        run.add_verdict(C.VERDICT_SPECIAL_LAYOUT)
        run.findings.append("The pasted output shows LVM objects.")
    if readings.get("has_logical_partition"):
        run.add_verdict(C.VERDICT_SPECIAL_LAYOUT)
        run.findings.append("The pasted output shows an extended partition.")
    if readings.get("inode_full"):
        run.add_verdict(C.VERDICT_CAPACITY_OR_INODE_BLOCKED)
        run.handoffs.append(C.HANDOFFS["disk-capacity"])
        run.findings.append(
            "A filesystem in the pasted df -i output sits at 100 percent of its inode "
            "table, which blocks metadata operations including some resize paths."
        )
    if readings.get("space_full"):
        run.add_verdict(C.VERDICT_CAPACITY_OR_INODE_BLOCKED)
        run.handoffs.append(C.HANDOFFS["disk-capacity"])
        run.findings.append(
            "A filesystem in the pasted output sits at 100 percent of its blocks."
        )
    for signal in run.signals:
        if signal["verdict"]:
            run.add_verdict(signal["verdict"])
        handoff_key = signal.get("handoff")
        if handoff_key and handoff_key in C.HANDOFFS:
            run.handoffs.append(C.HANDOFFS[handoff_key])


def record_prerequisites(run):
    """Snapshot-first is a hard precondition for any emitted change guidance."""
    if run.manual_steps and not run.snapshot_confirmed:
        run.degrade(C.NEXT_ACTION_SNAPSHOT_FIRST)


def build_recommendation(run, args, facts):
    os_family = (facts or {}).get("os_family", "UNKNOWN")
    is_windows = args.os_type == "windows" or "windows" in str(os_family).lower()
    if args.os_type == "linux":
        is_windows = False

    blocker_names = {
        C.VERDICT_FS_HEALTH_BLOCKED,
        C.VERDICT_CAPACITY_OR_INODE_BLOCKED,
        C.VERDICT_PARTITION_TABLE_INCONSISTENT,
        C.VERDICT_INSTANCE_STATE_BLOCKED,
        C.VERDICT_PARTITION_LAYER_NOT_ENLARGED,
        C.VERDICT_SPECIAL_LAYOUT,
        C.VERDICT_GUEST_TOOLING_MISSING,
        C.VERDICT_INIT_OR_MOUNT_AREA,
        C.VERDICT_DISK_NOT_ATTACHED,
    }
    blockers = blocker_names & set(run.verdicts)

    if C.VERDICT_CLOUD_NOT_RESIZED in run.verdicts:
        run.manual_steps.append(
            "Complete the cloud-side capacity change first. This skill will not place "
            "that order silently: it bills, and the extra size cannot be given back "
            "afterwards. Only a customer who has restated the exact target size and "
            "accepted the billing consequence may proceed."
        )
        run.manual_steps.append(
            "Console entry point for the disk list: {0}".format(
                C.CONSOLE_LINKS["disk_list"].format(region_id=args.region_id)
            )
        )
        run.degrade(C.NEXT_ACTION_CONFIRM_GATE)
        return

    if C.VERDICT_TARGET_NOT_FOUND in run.verdicts:
        run.degrade(C.NEXT_ACTION_ASK_REGION)
        return

    if C.VERDICT_SUSPECTED_NEW_DISK in run.verdicts:
        run.degrade(C.NEXT_ACTION_STOP_AND_REPORT)
        return

    if is_windows:
        run.manual_steps.extend(build_windows_steps(args.drive_letter or args.mount))
        run.limits.append(
            "NTFS has no equivalent of df -i, so a file-count or metadata exhaustion "
            "conclusion on Windows is inferred rather than measured; state that "
            "confidence limit in the reply."
        )
        if not run.guest:
            run.limits.append(
                "Get-Partition and Get-Disk are not approved for automated execution "
                "in this tier, so where the unallocated block sits has to come from "
                "the customer or a screenshot."
            )
        run.degrade(C.NEXT_ACTION_MANUAL_COMMANDS)
        record_prerequisites(run)
        return

    if C.VERDICT_CAPACITY_OR_INODE_BLOCKED in blockers:
        run.findings.append(
            "The resize cannot complete while usage is pinned at the limit; the "
            "capacity work comes first and belongs to the disk capacity tier."
        )
        run.degrade(C.NEXT_ACTION_STOP_AND_REPORT)
        return

    if C.VERDICT_FS_HEALTH_BLOCKED in blockers:
        run.manual_steps.append(
            "Repair the filesystem before touching size. A human runs the check and "
            "repair with the disk detached or the instance in a controlled state, "
            "after a snapshot. Do not re-run the resize while the health error "
            "stands, and do not read the refusal as a typo in the command."
        )
        run.degrade(C.NEXT_ACTION_STOP_AND_REPORT)
        return

    if C.VERDICT_PARTITION_TABLE_INCONSISTENT in blockers:
        run.manual_steps.append(
            "Escalate for a human engineer: the partition-table metadata disagrees "
            "with the device size, and the published resize walkthroughs do not cover "
            "reconciling it."
        )
        run.degrade(C.NEXT_ACTION_STOP_AND_REPORT)
        return

    if C.VERDICT_INSTANCE_STATE_BLOCKED in blockers:
        run.manual_steps.append(
            "Settle the instance power state and a normal boot first. While the "
            "instance sits between states or drops to a maintenance shell, no "
            "partition or filesystem command is trustworthy, and starting or "
            "rebooting it is a deliberate customer action."
        )
        run.degrade(C.NEXT_ACTION_STOP_AND_REPORT)
        return

    if {C.VERDICT_INIT_OR_MOUNT_AREA, C.VERDICT_DISK_NOT_ATTACHED} & blockers:
        run.manual_steps.append(
            "This is the new-disk area, not a failed resize: the device has to be "
            "attached and initialized before any growth step applies. Follow "
            "{0} and {1}; formatting a device erases it, so this skill stops short "
            "of issuing that command even after a confirmation.".format(
                C.HELP_DOCUMENTS["attach_data_disk"],
                C.HELP_DOCUMENTS["initialize_linux_data_disk"],
            )
        )
        run.degrade(C.NEXT_ACTION_STOP_AND_REPORT)
        return

    if C.VERDICT_GUEST_TOOLING_MISSING in blockers:
        run.manual_steps.append(
            "Install the guest-side resize helper first. Package installation "
            "mutates the instance and stays a customer action; when the install "
            "itself fails on name resolution or an unreachable repository, that is a "
            "separate problem to close before the resize is retried."
        )
        run.degrade(C.NEXT_ACTION_MANUAL_COMMANDS)
        return

    special_layout = bool(
        {C.VERDICT_PARTITION_LAYER_NOT_ENLARGED, C.VERDICT_SPECIAL_LAYOUT} & blockers
    )
    if special_layout:
        run.manual_steps.append(
            "This layout needs its own procedure rather than the generic pairing: an "
            "LVM logical volume, or an extended partition carrying logical "
            "partitions. Follow the matching document listed in "
            "references/disk-expand-diagnosis__linux-expand-paths.md and have a human confirm the exact "
            "target object before writing to it."
        )
        run.degrade(C.NEXT_ACTION_MANUAL_COMMANDS)
        record_prerequisites(run)
        return

    target = args.device or detect_target_device(run.guest, args.mount)
    fstype = args.fstype or detect_fstype(run.guest, target)
    mountpoint = args.mount or (run.guest.get("mounts") or {}).get(target)

    undetermined = not run.verdicts or run.verdicts == [C.VERDICT_UNKNOWN]
    run.manual_steps.extend(build_linux_steps(target, fstype, mountpoint))
    if target:
        run.add_verdict(C.VERDICT_READY_TO_APPLY)
        if undetermined:
            run.degrade(
                C.NEXT_ACTION_ASK_GUEST_READINGS,
                "The commands above stay conditional until the cloud-side size and "
                "the guest layout are both confirmed.",
            )
        else:
            run.degrade(C.NEXT_ACTION_MANUAL_COMMANDS)
    else:
        run.degrade(C.NEXT_ACTION_ASK_GUEST_READINGS)
    record_prerequisites(run)

    if args.expected_size_gib:
        run.limits.append(capacity_gap_note(args.expected_size_gib))


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------
def cmd_check_auth(args):
    run = Run(new_session_id())
    identity, error = sts_token.preflight(run.session_id)
    if error is not None:
        if error.is_auth_denied:
            run.fail(
                C.NEXT_ACTION_GRANT_PERMISSION,
                "Identity preflight was refused ({0}); what this check would have "
                "settled is unverified. references/ram-policies.md carries the "
                "minimal fragment for this check and names the action when the "
                "response does not.".format(
                    denial_phrase(error.code, denied_action(error.message))),
            )
            return emit(run, args)
        run.fail(
            C.NEXT_ACTION_VERIFY_CREDENTIALS,
            "Identity preflight failed: {0}: {1}. Re-authenticate with `aliyun "
            "configure` or the role the environment already provides. Never paste an "
            "AccessKey pair into a conversation, and rotate any key that was ever "
            "shared.".format(error.code, error.message),
        )
        return emit(run, args)
    run.findings.append(
        "identity: {0}".format(json.dumps(sts_token.masked_identity(identity), sort_keys=True))
    )
    run.findings.append("account_label: {0}".format(sts_token.account_label(identity)))
    run.assumptions.append("STS GetCallerIdentity, product sts, version 2015-04-01")
    return emit(run, args)


def cmd_explain(args):
    run = Run(new_session_id())
    run.assumptions.append("guidance-only mode: no cloud API was called")
    try:
        text = read_paste(args.paste)
    except OSError as exc:
        run.fail(C.NEXT_ACTION_STOP_AND_REPORT, "Could not read --paste: {0}".format(exc))
        return emit(run, args)
    if not text.strip():
        run.degrade(
            C.NEXT_ACTION_ASK_GUEST_READINGS,
            "No pasted output was supplied, so there is nothing to interpret.",
        )
        return emit(run, args)
    analyze_guest_text(run, text)
    if not run.signals:
        run.degrade(
            C.NEXT_ACTION_ASK_GUEST_READINGS,
            "No known error signal matched the pasted text. It may be truncated, or "
            "translated by a non-English locale: re-run the failing command with "
            "LC_ALL=en_US.UTF-8 and paste it again.",
        )
    else:
        run.degrade(C.NEXT_ACTION_STOP_AND_REPORT)
    record_prerequisites(run)
    return emit(run, args)


def cmd_diagnose(args):
    run = Run(new_session_id())
    if not args.region_id:
        run.degrade(
            C.NEXT_ACTION_ASK_REGION,
            "Region is required. The API is regional, and sweeping every region to "
            "guess one is deliberately not done: it costs calls and widens the "
            "permission surface. Ask for the region together with the instance or "
            "disk ID.",
        )
        return emit(run, args)
    if not (args.instance_id or args.disk_id):
        run.degrade(
            C.NEXT_ACTION_ASK_REGION,
            "An instance ID or a disk ID is required alongside the region.",
        )
        return emit(run, args)

    identity, identity_error = sts_token.preflight(run.session_id)
    if identity_error is not None:
        run.degrade(
            C.NEXT_ACTION_VERIFY_CREDENTIALS,
            "Identity preflight failed ({0}), so the run continues in guidance-only "
            "mode from whatever text was supplied.".format(identity_error.code),
        )
    else:
        run.findings.append(
            "account_label: {0}".format(sts_token.account_label(identity))
        )

    if args.snapshot_confirmed:
        run.snapshot_confirmed = args.snapshot_confirmed
        run.assumptions.append(
            "the snapshot attestation is a customer statement, not a value this skill "
            "read back from a cloud API"
        )

    disks = []
    instances = []
    facts = None
    if args.skip_cloud_calls:
        run.degrade(
            C.NEXT_ACTION_ASK_GUEST_READINGS,
            "Cloud calls were skipped, so every conclusion below rests on the pasted "
            "text alone and the cloud-side state is unverified.",
        )
        run.assumptions.append("no cloud API was called in this run")
    else:
        try:
            disks = fetch_disks(
                args.region_id, args.instance_id, args.disk_id, run.session_id
            )
            run.assumptions.append(
                "DescribeDisks called with RegionId={0} and {1}".format(
                    args.region_id,
                    "DiskIds={0}".format(args.disk_id) if args.disk_id
                    else "InstanceId={0}".format(args.instance_id),
                )
            )
        except CliError as exc:
            run.degrade(
                C.NEXT_ACTION_GRANT_PERMISSION if exc.is_auth_denied
                else C.NEXT_ACTION_RETRY_LATER,
                read_failure_note("DescribeDisks", "ecs:DescribeDisks", exc),
            )
        resolved_instance = args.instance_id
        if not resolved_instance:
            match = None
            if args.disk_id:
                match = next(
                    (d for d in disks if _first(d, "DiskId") == args.disk_id), None
                )
            elif disks:
                match = disks[0]
            attached = _first(match, "InstanceId", default=None) if match else None
            if attached and attached != "UNKNOWN":
                resolved_instance = attached
                run.assumptions.append(
                    "No instance ID was supplied, so DescribeInstances was scoped to "
                    "{0}, the instance the target disk reports as attached.".format(
                        resolved_instance
                    )
                )

        if resolved_instance:
            try:
                instances = fetch_instances(
                    args.region_id, resolved_instance, run.session_id
                )
                run.assumptions.append(
                    "DescribeInstances called with RegionId={0} and InstanceIds "
                    "[{1}]".format(args.region_id, resolved_instance)
                )
            except CliError as exc:
                run.degrade(
                    C.NEXT_ACTION_GRANT_PERMISSION if exc.is_auth_denied
                    else C.NEXT_ACTION_RETRY_LATER,
                    read_failure_note("DescribeInstances", "ecs:DescribeInstances",
                                      exc),
                )
        elif run.next_action not in (C.NEXT_ACTION_VERIFY_CREDENTIALS,
                                     C.NEXT_ACTION_GRANT_PERMISSION):
            run.degrade(
                C.NEXT_ACTION_ASK_REGION,
                "No instance ID was supplied and no disk in this region reported an "
                "attached instance, so DescribeInstances was not called. Listing "
                "every instance in the region and picking one would attribute an "
                "unrelated machine's operating system and power state to this disk, "
                "so ask for the instance ID to settle the Linux versus Windows "
                "branch.",
            )

        facts = classify_cloud_side(
            disks, instances, args.disk_id, resolved_instance,
            args.expected_size_gib, run,
        )

    text = ""
    if args.paste:
        try:
            text = read_paste(args.paste)
        except OSError as exc:
            run.degrade(
                C.NEXT_ACTION_ASK_GUEST_READINGS,
                "Could not read the pasted file: {0}".format(exc),
            )
    if text.strip():
        analyze_guest_text(run, text)
    elif run.status != C.STATUS_FAILED:
        if C.VERDICT_TARGET_NOT_FOUND in run.verdicts:
            run.degrade(
                C.NEXT_ACTION_ASK_REGION,
                "Guest-side state is unknown, and this run did not identify a target "
                "disk. Readings taken inside a guest cannot say which machine or which "
                "disk this is, so settle the region, the account and the instance the "
                "disk is attached to first. After the target is confirmed, ask the "
                "customer to run and paste back on that machine: df -Th, lsblk -f, "
                "blkid, fdisk -lu, df -i.",
            )
        else:
            run.degrade(
                C.NEXT_ACTION_ASK_GUEST_READINGS,
                "Guest-side state is unknown. Cloud APIs cannot report the partition "
                "table, the filesystem type or the free space inside the guest, and the "
                "device-level listing commands are not approved for automated execution in "
                "this tier. Ask the customer to run and paste back: df -Th, lsblk -f, "
                "blkid, fdisk -lu, df -i.",
            )

    build_recommendation(run, args, facts)
    return emit(run, args)


def cmd_run_command(args):
    run = Run(new_session_id())
    allowed, reason = check_command_gate(args.command, args.justify)
    run.findings.append("requested guest command: {0}".format(args.command))
    if not allowed:
        run.degrade(C.NEXT_ACTION_ASK_GUEST_READINGS, reason)
        run.manual_steps.append(
            "Run this yourself inside the instance and paste the raw output back: "
            "{0}".format(args.command)
        )
        return emit(run, args)

    if not args.confirm:
        run.degrade(
            C.NEXT_ACTION_CONFIRM_GATE,
            "Pre-execution disclosure was not acknowledged. Before this call the "
            "operator must be told: the single command being sent ({0}), that it only "
            "inspects and modifies no data, that it targets instance {1} and nothing "
            "else, and that a failure costs nothing but time. Acknowledgement covers "
            "this one command, not the rest of the session.".format(
                args.command, args.instance_id
            ),
        )
        return emit(run, args)

    try:
        payload = submit_run_command(
            args.region_id, args.instance_id, args.command, run.session_id
        )
        run.findings.append(
            "RunCommand accepted; invoke id: {0}".format(_first(payload, "InvokeId"))
        )
        run.assumptions.append(
            "RunCommand, under the ecs RAM code, is a write-class action used here "
            "purely to carry a non-mutating command; this version does not assert a "
            "result-retrieval API, so submission is reported and no stdout is claimed."
        )
        run.degrade(
            C.NEXT_ACTION_ASK_GUEST_READINGS,
            "Command submitted. Read the output from the Cloud Assistant invocation "
            "result, or have the customer paste it, then continue the diagnosis.",
        )
    except CliError as exc:
        run.fail(
            C.NEXT_ACTION_VERIFY_CREDENTIALS if exc.is_auth_denied
            else C.NEXT_ACTION_RETRY_LATER,
            "RunCommand failed: {0}".format(exc),
        )
    return emit(run, args)


def cmd_create_snapshot(args):
    run = Run(new_session_id())
    if not args.confirm_cost:
        run.degrade(
            C.NEXT_ACTION_CONFIRM_GATE,
            "Snapshot creation bills by stored capacity and retention time. Disclose "
            "that, state plainly that snapshots live in cloud storage and never "
            "consume space on the disk being resized, and remind the customer to "
            "delete old snapshots once the change is verified. The snapshot itself has "
            "to be created by the customer in their own account context.",
        )
        run.manual_steps.append(
            "Snapshot the disk behind {0} from the console disk list: {1}".format(
                args.disk_id,
                C.CONSOLE_LINKS["disk_list"].format(region_id=args.region_id),
            )
        )
        return emit(run, args)

    params = {"DiskId": args.disk_id}
    if args.snapshot_name:
        params["SnapshotName"] = args.snapshot_name
    if args.retention_days:
        params["RetentionDays"] = args.retention_days
    retention_note = (
        str(args.retention_days) if args.retention_days
        else "not set, so it bills until deleted"
    )
    try:
        payload = call_ecs("CreateSnapshot", params, run.session_id, write=True)
        snapshot_id = _first(payload, "SnapshotId")
        run.snapshot_confirmed = snapshot_id
        run.findings.append("snapshot created: {0}".format(snapshot_id))
        run.assumptions.append("RetentionDays: {0}".format(retention_note))
        run.degrade(C.NEXT_ACTION_ASK_GUEST_READINGS)
    except CliError as exc:
        run.fail(
            C.NEXT_ACTION_VERIFY_CREDENTIALS if exc.is_auth_denied
            else C.NEXT_ACTION_RETRY_LATER,
            "CreateSnapshot failed: {0}".format(exc),
        )
    return emit(run, args)


def cmd_resize_disk(args):
    run = Run(new_session_id())
    if not (args.confirm_cost and args.confirm_irreversible):
        run.degrade(
            C.NEXT_ACTION_CONFIRM_GATE,
            "A capacity change is callable only once three things hold: DescribeDisks "
            "really shows the disk below the intended size, the customer accepted the "
            "billing consequence, and the customer restated the exact target size "
            "knowing it cannot be given back. Emit parameterized guidance instead.",
        )
        run.manual_steps.append(
            "Console entry point for the disk list: {0}".format(
                C.CONSOLE_LINKS["disk_list"].format(region_id=args.region_id)
            )
        )
        run.manual_steps.append(
            "Intended target: disk {0}, new size {1} GiB, no resize type declared, "
            "which means the online path.".format(args.disk_id, args.new_size_gib)
        )
        return emit(run, args)

    try:
        call_ecs(
            "ResizeDisk",
            {"DiskId": args.disk_id, "NewSize": args.new_size_gib},
            run.session_id,
            write=True,
        )
        run.findings.append(
            "ResizeDisk accepted for {0} at {1} GiB. Re-read DescribeDisks to confirm "
            "it, then continue with the guest-side partition and filesystem growth: "
            "that is a separate step this order does not perform.".format(
                args.disk_id, args.new_size_gib
            )
        )
        run.degrade(C.NEXT_ACTION_ASK_GUEST_READINGS)
    except CliError as exc:
        run.fail(
            C.NEXT_ACTION_VERIFY_CREDENTIALS if exc.is_auth_denied
            else C.NEXT_ACTION_RETRY_LATER,
            "ResizeDisk failed: {0}".format(exc),
        )
    return emit(run, args)


# ---------------------------------------------------------------------------
# argument plumbing
# ---------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="disk_expand_diagnosis.py",
        description=(
            "Diagnose ECS cloud disk expansion that did not take effect inside the "
            "guest, plus partition and filesystem adjustment failures."
        ),
    )
    sub = parser.add_subparsers(dest="subcommand")

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--region-id", help="e.g. cn-hangzhou")
    shared.add_argument("--json", action="store_true", help="machine-readable output")

    auth = sub.add_parser("check-auth", parents=[shared], help="credential preflight")
    auth.set_defaults(func=cmd_check_auth, json=False, region_id=None)

    explain = sub.add_parser("explain", parents=[shared], help="interpret pasted output")
    explain.add_argument("--paste", required=True,
                         help="file holding pasted guest output, or - for stdin")
    explain.set_defaults(func=cmd_explain, json=False, region_id=None)

    diag = sub.add_parser("diagnose", parents=[shared], help="run the decision tree")
    diag.add_argument("--instance-id")
    diag.add_argument("--disk-id")
    diag.add_argument("--expected-size-gib", type=int)
    diag.add_argument("--os-type", choices=("linux", "windows"))
    diag.add_argument("--mount", help="mount point of the target filesystem")
    diag.add_argument("--drive-letter", help="Windows drive letter, e.g. D:")
    diag.add_argument("--device", help="override the detected guest device, e.g. /dev/vda3")
    diag.add_argument("--fstype", choices=("ext4", "ext3", "ext2", "xfs", "btrfs"))
    diag.add_argument("--paste", help="file with pasted guest output, or - for stdin")
    diag.add_argument("--snapshot-confirmed", help="snapshot id or creation time")
    diag.add_argument("--skip-cloud-calls", action="store_true",
                      help="guidance-only mode, no cloud query attempted")
    diag.set_defaults(func=cmd_diagnose, json=False, region_id=None)

    guest = sub.add_parser("run-command", parents=[shared],
                           help="dispatch ONE approved non-mutating command")
    guest.add_argument("--instance-id", required=True)
    guest.add_argument("--command", required=True)
    guest.add_argument("--confirm", help="acknowledge the pre-execution disclosure")
    guest.add_argument("--justify", help="why a capacity-tier command is needed here")
    guest.set_defaults(func=cmd_run_command, json=False)

    snap = sub.add_parser("create-snapshot", parents=[shared],
                          help="gated pre-change snapshot")
    snap.add_argument("--disk-id", required=True)
    snap.add_argument("--snapshot-name")
    snap.add_argument("--retention-days", type=int)
    snap.add_argument("--confirm-cost", action="store_true")
    snap.set_defaults(func=cmd_create_snapshot, json=False)

    resize = sub.add_parser("resize-disk", parents=[shared],
                            help="gated capacity change order")
    resize.add_argument("--disk-id", required=True)
    resize.add_argument("--new-size-gib", type=int, required=True)
    resize.add_argument("--confirm-cost", action="store_true")
    resize.add_argument("--confirm-irreversible", action="store_true")
    resize.set_defaults(func=cmd_resize_disk, json=False)

    return parser


def _run_selftest():
    """Offline boundary locks for the device-naming and plan-generation core.

    These guard the two places support tickets show customers failing: the
    nvme-vs-virtio partition node spelling, and emitting a filesystem command
    that matches the actual fstype (resize2fs must never target xfs). Pure
    functions only - no cloud or credentials touched.
    """
    rc = 0

    def expect(name, cond):
        nonlocal rc
        print("PASS" if cond else "FAIL", name)
        if not cond:
            rc = 1

    # partition_device: nvme/md take a 'p' separator, virtio/scsi do not.
    expect("pd_nvme", partition_device("/dev/nvme0n1", "1") == "/dev/nvme0n1p1")
    expect("pd_nvme_prepend_p", partition_device("/dev/nvme0n1", "p3") == "/dev/nvme0n1p3")
    expect("pd_md", partition_device("/dev/md0", "2") == "/dev/md0p2")
    expect("pd_virtio", partition_device("/dev/vdb", "1") == "/dev/vdb1")
    expect("pd_scsi", partition_device("/dev/sda", "4") == "/dev/sda4")
    expect("pd_none_suffix", partition_device("/dev/vdb", None) == "/dev/vdb")

    # _has_partition_number: whole-disk nodes are never partitions.
    expect("hpn_nvme_disk_false", _has_partition_number("/dev/nvme0n1") is False)
    expect("hpn_nvme_part_true", _has_partition_number("/dev/nvme0n1p1") is True)
    expect("hpn_vda_false", _has_partition_number("/dev/vda") is False)
    expect("hpn_vda1_true", _has_partition_number("/dev/vda1") is True)
    expect("hpn_xvda1_true", _has_partition_number("/dev/xvda1") is True)
    expect("hpn_sda10_true", _has_partition_number("/dev/sda10") is True)
    expect("hpn_sdb_false", _has_partition_number("/dev/sdb") is False)

    # _device_from_token: bare and /dev forms normalise; junk is rejected.
    expect("dft_dev", _device_from_token("/dev/vdb1") == "/dev/vdb1")
    expect("dft_bare", _device_from_token("vdc2") == "/dev/vdc2")
    expect("dft_xvd", _device_from_token("xvdc3") == "/dev/xvdc3")
    expect("dft_junk_none", _device_from_token("junk") is None)
    expect("dft_empty_none", _device_from_token("") is None)
    expect("dft_punct_none", _device_from_token(":,;") is None)

    # generic helpers.
    expect("as_int_ok", _as_int("42") == 42)
    expect("as_int_none", _as_int("x") is None)
    expect("as_int_default", _as_int("x", 0) == 0)
    expect("first_skips_empty", _first({"a": None, "b": "z"}, "a", "b") == "z")

    # detect_fstype: exact device only, never borrows a type from another node.
    readings = {
        "filesystems": {"/dev/vdb1": "xfs", "/dev/vda1": "ext4"},
        "mounts": {"/dev/vdb1": "/data", "/dev/vda1": "/"},
    }
    expect("dfs_exact", detect_fstype(readings, "/dev/vdb1") == "xfs")
    expect("dfs_unknown_none", detect_fstype(readings, "/dev/vdz9") is None)
    expect("dfs_no_device_first", detect_fstype(readings, None) == "ext4")

    # detect_target_device: mount wins, else falls back to the root partition.
    expect("dtd_mount", detect_target_device(readings, "/data") == "/dev/vdb1")
    expect("dtd_default_root", detect_target_device(readings) == "/dev/vda1")

    # capacity_gap_note: GiB order number plus its decimal GB equivalent.
    gap = capacity_gap_note(100)
    expect("gap_gib", "100 GiB" in gap)
    expect("gap_decimal_gb", "107.37 GB" in gap)

    # build_linux_steps: the command must match the fstype and device family.
    xfs = build_linux_steps("/dev/vdb1", "xfs", "/data")
    expect("bls_xfs_growfs_mount", any("xfs_growfs /data" in s for s in xfs))
    expect("bls_xfs_no_resize2fs", not any("sudo resize2fs" in s for s in xfs))
    expect("bls_growpart_space", any("growpart /dev/vdb 1 " in s for s in xfs))

    ext = build_linux_steps("/dev/vdb1", "ext4", "/data")
    expect("bls_ext_resize2fs_dev", any("resize2fs /dev/vdb1" in s for s in ext))

    nvme = build_linux_steps("/dev/nvme0n1p1", "ext4", "/data")
    expect("bls_nvme_growpart", any("growpart /dev/nvme0n1 1 " in s for s in nvme))
    expect("bls_nvme_fs_psuffix", any("resize2fs /dev/nvme0n1p1" in s for s in nvme))

    whole = build_linux_steps("/dev/vdb", "ext4", "/data")
    expect("bls_whole_refuses", len(whole) == 1 and "whole device" in whole[0])

    none_dev = build_linux_steps(None, "ext4", "/data")
    expect("bls_no_device_layout", len(none_dev) == 1 and "lsblk -f" in none_dev[0])

    unk = build_linux_steps("/dev/vdb1", None, "/data")
    expect("bls_unknown_no_fs_cmd", any("No filesystem command" in s for s in unk))

    btrfs = build_linux_steps("/dev/vdb1", "btrfs", "/data")
    expect("bls_btrfs_not_automated", any("does not automate btrfs" in s for s in btrfs))

    # Error-signal locks (live-verified 2026-10-20 via faultlab F4 injection):
    # the instance-type x disk-category refusal must map to TARGET_DISK_NOT_
    # ATTACHED, match case-insensitively, and never fire on unrelated text.
    expect("sig_category_hit",
           any(s["id"] == "disk-category-not-supported-by-instancetype"
               and s["verdict"] == C.VERDICT_DISK_NOT_ATTACHED
               for s in scan_signals("ERROR: InvalidInstanceType.NotSupportDiskCategory ...")))
    expect("sig_category_case_insensitive",
           scan_signals("invalidinstancetype.notsupportdiskcategory"))
    expect("sig_category_no_false_fire", not scan_signals("resize2fs done, 40G visible"))
    expect("sig_empty_safe", scan_signals("") == [])

    print("SELFTEST:", "PASS" if rc == 0 else "FAIL")
    return rc


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if "--selftest" in argv:
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("STATUS: FAILED\nNEXT_ACTION: STOP_AND_REPORT", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
