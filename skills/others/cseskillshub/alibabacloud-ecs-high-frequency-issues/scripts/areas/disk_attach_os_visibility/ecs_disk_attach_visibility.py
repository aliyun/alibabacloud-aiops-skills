#!/usr/bin/env python3
"""Single entry point: where does an ECS disk stop being usable, cloud side or guest side?

Collects the control-plane half of the visibility chain with the four describe actions
this skill is allowed to call, folds in guest readings that scripts/areas/disk_attach_os_visibility/guest_probe.py has
already collected under the customer's confirmation, and prints an evidence-bound report
ending in STATUS and NEXT_ACTION.

Examples:
    python3 scripts/areas/disk_attach_os_visibility/ecs_disk_attach_visibility.py --region-id cn-hangzhou \
        --instance-id i-c00000000000000000
    python3 scripts/areas/disk_attach_os_visibility/ecs_disk_attach_visibility.py --region-id cn-hangzhou \
        --instance-id i-c00000000000000000 --disk-id d-c00000000000000000 \
        --symptom "data disk attached but not visible in the instance" \
        --guest-findings guest-findings.json
    python3 scripts/areas/disk_attach_os_visibility/ecs_disk_attach_visibility.py --help
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

import report_builder as rb
import sts_token
from _cli import CliError, call, mask_secrets, new_session_id, records
from _constants import (
    ALLOWED_ACTIONS,
    AGENT_OFFLINE_LINES,
    CLI_TIMEOUT_SECONDS,
    DESCRIBE_PAGE_SIZE,
    DISK_RULE_DOC_LINKS,
    DISK_RULE_CONCLUSIONS,
    DISK_RULE_CONSENT_LINE,
    DISK_RULE_CONSENT_TOPICS,
    DISK_RULE_TOPIC_DOCS,
    DISK_RULE_TOPICS,
    DISK_RULE_WINDOWS_LINES,
    DISK_RULE_WINDOWS_DOCS,
    DISK_RULE_LINUX_STEP_RE,
    DOC_LINKS,
    ECS_PRODUCT,
    agent_offline_signal,
    FINDING_DISK_ATTACHED_TO_THIS_INSTANCE,
    FINDING_DISK_NOT_ATTACHED,
    FINDING_DISK_NOT_FOUND_IN_REGION,
    FINDING_DISK_ON_OTHER_INSTANCE,
    FINDING_EXPLANATION,
    FINDING_FILESYSTEM_NOT_MOUNTED,
    FINDING_INSTANCE_NOT_FOUND,
    FINDING_INSTANCE_STOPPED,
    FINDING_MOUNTED_AND_READABLE,
    FINDING_NO_FILESYSTEM,
    FINDING_PROBE_NOT_RUN,
    FINDING_PROBE_UNAVAILABLE,
    HANDOFF_ROUTES,
    IN_SCOPE_SYMPTOMS,
    OS_UNKNOWN,
    SKILL_NAME,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
)

GUEST_GATE_TEXT = (
    "The guest half of the chain still needs a confirmation step. Tell the customer which "
    "one inspect-only command is about to run, that it changes nothing, and that they may "
    "run it themselves instead. After they agree, run: "
    "python3 scripts/areas/disk_attach_os_visibility/guest_probe.py --region-id <region> --instance-id <instance> "
    "--os <linux|windows> --command \"lsblk -f\" --confirmed"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=SKILL_NAME,
        description="Diagnose why an attached ECS disk is not visible or usable inside the guest.")
    parser.add_argument("--region-id", help="Region id of the instance. Required: disk and instance ids "
                                            "are region scoped and this skill does not sweep regions.")
    parser.add_argument("--instance-id", help="Instance id the disk is expected on. Required.")
    parser.add_argument("--disk-id", action="append", default=[],
                        help="Specific disk id to judge. Repeat for several. Omit to judge every disk "
                             "attached to the instance.")
    parser.add_argument("--os", choices=("auto", "linux", "windows"), default="auto",
                        help="Guest family. auto reads it from the instance record when that field is "
                             "present; otherwise the guest step is skipped until this is stated.")
    parser.add_argument("--symptom", default="", help="The customer's own words, used for handoff routing "
                                                      "and mount-shadowing detection.")
    parser.add_argument("--guest-findings", help="Path to the JSON produced by scripts/areas/disk_attach_os_visibility/guest_probe.py, or "
                                                 "- to read it from stdin. Omit for a cloud-side-only report.")
    parser.add_argument("--skip-snapshots", action="store_true",
                        help="Do not check whether a recovery point exists for the disks.")
    parser.add_argument("--skip-identity-check", action="store_true",
                        help="Skip the caller identity pre-flight (not recommended).")
    parser.add_argument("--print-only", action="store_true",
                        help="Print the API requests that would be made, then stop.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of markdown.")
    parser.add_argument("--timeout", type=int, default=CLI_TIMEOUT_SECONDS, help="Seconds per API call.")
    return parser


def _require(args: argparse.Namespace) -> Optional[str]:
    missing = [name for name, value in (("--region-id", args.region_id), ("--instance-id", args.instance_id))
               if not value]
    if missing:
        return ("Missing %s. Ask the customer for it; disk and instance ids are only meaningful inside "
                "one region and this skill does not sweep regions on their behalf." % ", ".join(missing))
    return None


def _fetch_instance(session_id: str, region_id: str, instance_id: str,
                    timeout: int) -> Tuple[Dict[str, Any], List[str]]:
    gaps: List[str] = []
    payload = call(ECS_PRODUCT, "DescribeInstances",
                   {"InstanceIds": json.dumps([instance_id]), "PageSize": DESCRIBE_PAGE_SIZE},
                   session_id=session_id, region_id=region_id, timeout=timeout)
    rows = records(payload, ("Instance",))
    if not rows:
        return {}, [FINDING_INSTANCE_NOT_FOUND]
    facts = rb.extract_instance_facts(rows[0])
    if len(rows) > 1:
        gaps.append("The API returned more than one instance record for a single id; the first was used.")
    return facts, gaps


def _fetch_disks(session_id: str, region_id: str, instance_id: str, disk_ids: List[str],
                 timeout: int) -> Tuple[List[Dict[str, Any]], List[str]]:
    gaps: List[str] = []
    payload = call(ECS_PRODUCT, "DescribeDisks",
                   {"InstanceId": instance_id, "PageSize": DESCRIBE_PAGE_SIZE},
                   session_id=session_id, region_id=region_id, timeout=timeout)
    disks = [rb.extract_disk_facts(row) for row in records(payload, ("Disk",))]

    wanted = [disk_id for disk_id in disk_ids if disk_id]
    present = {disk["disk_id"] for disk in disks}
    for disk_id in wanted:
        if disk_id in present:
            continue
        try:
            extra = call(ECS_PRODUCT, "DescribeDisks",
                         {"DiskIds": json.dumps([disk_id]), "PageSize": DESCRIBE_PAGE_SIZE},
                         session_id=session_id, region_id=region_id, timeout=timeout)
        except CliError as error:
            gaps.append("Lookup of %s by disk id failed (%s)." % (disk_id, error.code))
            continue
        rows = [rb.extract_disk_facts(row) for row in records(extra, ("Disk",))]
        if rows:
            disks.extend(rows)
        else:
            disks.append({"disk_id": disk_id, "size_gib": None, "disk_type": "", "category": "",
                          "status": "", "attached_instances": [], "cloud_device": "", "portable": None,
                          "billing": "", "delete_with_instance": None, "serial": "", "multi_attach": "",
                          "raw": {"DiskId": disk_id, "note": FINDING_DISK_NOT_FOUND_IN_REGION}})
    return disks, gaps


def _fetch_snapshot_presence(session_id: str, region_id: str, instance_id: str,
                             timeout: int) -> Tuple[Dict[str, Any], List[str]]:
    gaps: List[str] = []
    payload = call(ECS_PRODUCT, "DescribeSnapshots",
                   {"InstanceId": instance_id, "PageSize": DESCRIBE_PAGE_SIZE},
                   session_id=session_id, region_id=region_id, timeout=timeout)
    rows = records(payload, ("Snapshot",))
    by_disk: Dict[str, int] = {}
    for row in rows:
        disk_id = str(row.get("SourceDiskId") or row.get("DiskId") or "unknown")
        by_disk[disk_id] = by_disk.get(disk_id, 0) + 1
    return {"snapshot_count": len(rows), "by_disk": by_disk}, gaps


def _load_guest(path: str) -> Dict[str, Any]:
    if path == "-":
        raw = sys.stdin.read()
    else:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    try:
        return json.loads(raw)
    except ValueError as error:
        raise CliError("BadGuestFindings", "the guest findings file is not valid JSON (%s)" % error)


def route_handoff(symptom: str) -> List[Tuple[str, str, str]]:
    """Return (destination, reason) for every out-of-scope symptom cluster the words contain."""
    lowered = (symptom or "").lower()
    hits: List[Tuple[str, str, str]] = []
    for markers, destination, reason in HANDOFF_ROUTES:
        matched = [marker for marker in markers if marker in lowered]
        if matched:
            hits.append((",".join(matched), destination, reason))
    return hits


def in_scope(symptom: str) -> bool:
    lowered = (symptom or "").lower()
    return any(marker in lowered for marker in IN_SCOPE_SYMPTOMS)


_FORMAT_VETO_RE = re.compile(
    r"严禁格|禁止格|不要格|不能格|别格|勿格|不许格|不可格|保留数据|数据不能丢|数据很重要")
_FORMAT_VETO_LINE = (
    "Have the customer know this disk carries data they asked to keep: NEVER partition or "
    "format it; mount the existing filesystem read-only and copy the data off first.")
_DF_DU_VETO_RE = re.compile(
    r"看不到|没显示|没有显示|没有用上|没用上|未初始化|显示只有|不显示")


def disk_rule_for(symptom: str) -> Tuple[str, Tuple[str, ...]]:
    """The first topic the customer wording earns; specific topics precede generic ones."""
    lowered = (symptom or "").lower()
    veto = bool(_FORMAT_VETO_RE.search(symptom or ""))
    if agent_offline_signal(symptom):
        return "agent-offline", AGENT_OFFLINE_LINES
    for topic, markers, lines in DISK_RULE_TOPICS:
        if any(marker in lowered for marker in markers):
            if topic == "df-du-mismatch" and _DF_DU_VETO_RE.search(symptom or ""):
                continue
            if veto:
                lines = tuple(
                    _FORMAT_VETO_LINE
                    if "mkfs" in line and "all data will be lost" in line else line
                    for line in lines)
            return topic, lines
    return "", ()


# P1 Chinese in-domain symptom recognition (ledger D160 §30/§38): the matcher was
# English-only, so flagship Chinese in-domain questions were mislabeled out of scope.
assert in_scope("挂载后系统内看不到磁盘")
assert in_scope("如何卸载云盘")
assert in_scope("查看云盘使用容量")
assert not route_handoff("挂载后系统内看不到磁盘")
assert not route_handoff("如何卸载云盘")
assert not route_handoff("查看云盘使用容量")
assert any("disk-expand" in h[1] for h in route_handoff("磁盘扩容后容量没变"))
assert any("instance-state" in h[1] for h in route_handoff("实例无法启动卡在开机"))
assert in_scope("data disk attached but not visible")
assert not in_scope("今天天气不错")


def preview_requests(session_id: str, args: argparse.Namespace) -> None:
    from _cli import build_command
    from _constants import ECS_VERSION, STS_PRODUCT
    print("# Requests this run would make (nothing was sent)")
    for action, params in (
        ("DescribeInstances", {"InstanceIds": json.dumps([args.instance_id])}),
        ("DescribeDisks", {"InstanceId": args.instance_id}),
        ("DescribeSnapshots", {"InstanceId": args.instance_id}),
    ):
        print(" ".join(build_command(ECS_PRODUCT, action, params, session_id, args.region_id)))
    print(" ".join(build_command(STS_PRODUCT, "GetCallerIdentity", {}, session_id)))
    print("# product version: ecs %s" % ECS_VERSION)


def _attached_not_visible(verdicts: List[Dict[str, Any]]) -> bool:
    """True when a disk is attached to this instance but the chain has not reached
    mounted-and-readable (probe missing or an OS-side break). This is the core
    'attached but not visible' scenario that needs OS-side remediation guidance."""
    for verdict in verdicts:
        findings = verdict.get("findings", [])
        if FINDING_DISK_ATTACHED_TO_THIS_INSTANCE in findings \
                and FINDING_MOUNTED_AND_READABLE not in findings:
            return True
    return False


def _new_disk_lead_line(verdicts: List[Dict[str, Any]], os_family: str,
                        guest: Dict[str, Any]) -> Optional[str]:
    """MUST-LEAD for the confirmed Linux new-disk case: attached and enumerated in-guest
    but no filesystem. Names the cause in the report headline instead of leaving it
    unverified. Scoped to Linux and a collected guest reading; nothing is executed."""
    if os_family != "linux" or not guest.get("collected"):
        return None
    for verdict in verdicts:
        findings = verdict.get("findings", [])
        if FINDING_DISK_ATTACHED_TO_THIS_INSTANCE in findings \
                and FINDING_NO_FILESYSTEM in findings:
            return ("MUST-LEAD: [disk-not-initialized] the guest reading shows the attached "
                    "data disk enumerated with no filesystem and no mount -- measured, not "
                    "inferred. A new disk is never auto-initialized by the platform: snapshot "
                    "first, then partition (optional), mkfs, mount, and persist via UUID in "
                    "/etc/fstab.")
    return None


def _placement_lead_line(verdicts: List[Dict[str, Any]]) -> Optional[str]:
    """MUST-LEAD for a placement break the control plane positively reported.

    DescribeDisks returning Available with no owner, or an owner that is not the
    queried instance, is a positive reading of the fault, not an absent one: it
    fully explains why the guest cannot see the disk, so the chain legitimately
    stops at the placement link and the verdict may name it. An attached disk
    whose guest half was never read stays unverified.
    """
    for verdict in verdicts:
        findings = verdict.get("findings", [])
        if FINDING_DISK_NOT_ATTACHED in findings:
            return ("MUST-LEAD: [disk-not-attached] the control plane reports this data disk "
                    "as Available with no instance attached -- measured, not inferred. No "
                    "operating-system action can make it visible until it is attached in the "
                    "console; attach it to this instance in the same zone, then read the guest.")
        if FINDING_DISK_ON_OTHER_INSTANCE in findings:
            return ("MUST-LEAD: [disk-on-other-instance] the control plane reports this data "
                    "disk attached to a different instance -- measured, not inferred. That is "
                    "why this instance cannot see it: detach it from the current owner first, "
                    "then attach it here in the same zone, and snapshot before any move.")
    return None


# The answer budget keeps the first lines of a headed section, so the reading that
# carries the decisive signal must come first. Alphabetical order put `df -h` ahead
# of `lsblk -f`, and a live run shipped the corroborating reading while the decisive
# one was folded away.
_GUEST_READ_ORDER = ("lsblk -f", "lsblk", "df -h")


def _guest_reads_in_decisive_order(raw: Dict[str, str]) -> List[Tuple[str, str]]:
    def rank(command: str) -> Tuple[int, str]:
        lowered = command.strip().lower()
        for index, known in enumerate(_GUEST_READ_ORDER):
            if lowered == known:
                return (index, lowered)
        return (len(_GUEST_READ_ORDER), lowered)
    return sorted(raw.items(), key=lambda item: rank(item[0]))


def _visibility_guidance_lines(os_family: str, guest: Dict[str, Any],
                               devices: Sequence[str] = (),
                               not_initialized: bool = False,
                               unmounted: Sequence[str] = (),
                               uuid_by_device: Optional[Dict[str, str]] = None) -> List[str]:
    """Suggestion-only OS-side remediation guidance for an attached disk that is not
    yet visible. Snapshot-first, consent-gated, console path, OS-family specific.
    Nothing here is executed by the skill."""
    lines: List[str] = []
    if not_initialized and os_family == "linux":
        # The remediation sequence used to live only inside the MUST-LEAD evidence
        # string, which the answer's lead truncates: a live run ended the customer's
        # first line at "snapshot first," and the sequence never reached them. The
        # section budget keeps whole lines from the top, so it leads here instead.
        target = (" on %s" % ", ".join(devices)) if devices else ""
        lines.append(
            "- This disk%s has no partition table and no filesystem, so the OS cannot use "
            "it yet: have the customer snapshot it first, then partition (optional), create "
            "a filesystem with mkfs, mount it at an empty path, and persist a UUID entry "
            "with defaults,nofail in /etc/fstab." % target)
    lines += [
        "- Guidance only: this skill does not partition, format, mount, bring a volume online "
        "or change anything; every in-guest command needs the customer's explicit consent first.",
        "- Console entry point: ECS console -> instance details -> Block Storage tab shows the "
        "disk attached to this instance.",
        "- Before any partition, format or volume change, have the customer create a snapshot "
        "of the disk as a recovery point (a manual decision; snapshots are billed).",
    ]
    if not guest.get("collected"):
        lines.append(
            "- The OS half was not read this run, so the exact break is not yet known. Ask the "
            "customer to run and paste the guest reading (lsblk -f / df -h on Linux, Disk "
            "Management on Windows) to locate it; the standard path below applies once confirmed.")
    if os_family == "windows":
        lines.append(
            "- Have the customer open Disk Management (diskmgmt.msc) and bring the disk Online "
            "if it shows Offline.")
        lines.append(
            "- Have the customer Initialize the disk if Not Initialized (GPT for disks over "
            "2 TiB), then create a New Simple Volume and assign a drive letter.")
    elif os_family == "linux":
        if devices:
            lines.append(
                "- The guest reading already names the device for this disk: %s. Have the "
                "customer confirm it by size before touching it; the name comes from this "
                "run's reading, not from an assumed /dev/vd* or /dev/nvme* pattern."
                % ", ".join(devices))
        elif unmounted:
            uuid = next((value for value in
                         ((uuid_by_device or {}).get(name, "") for name in unmounted)
                         if value), "")
            pin = ("UUID=%s" % uuid) if uuid else "the UUID `blkid` reports"
            lines.append(
                "- The guest reading already shows a filesystem on %s, so it holds data: have "
                "the customer mount it and never run mkfs on it. The missing step is the mount, "
                "not the initialization." % ", ".join(unmounted))
            lines.append(
                "- Have the customer mount %s at an empty path, add it to /etc/fstab as "
                "`%s <path> <fstype> defaults,nofail 0 0`, then run `mount -a` and confirm the "
                "path is listed before rebooting." % (", ".join(unmounted), pin))
        else:
            lines.append(
                "- Ask the customer to run and paste lsblk -f to identify the device (match by "
                "size; mind NVMe vs virtio naming, never assume /dev/vdb).")
        if not_initialized:
            lines.append(
                "- Do not run mkfs on a disk that already holds data: this run read no "
                "filesystem on it, which is why initializing is the path here.")
        elif not unmounted:
            lines.append(
                "- A disk created from a snapshot already has a partition and filesystem: have the "
                "customer skip fdisk/mkfs and mount it directly.")
            lines.append(
                "- Only if it has no partition or filesystem, have the customer partition it "
                "(fdisk/parted) and create a filesystem (mkfs) - destructive if it already holds data.")
        if not unmounted:
            lines.append(
                "- Have the customer mount it at an empty chosen path, then persist a UUID entry "
                "with defaults,nofail in /etc/fstab so a mount failure cannot block boot.")
    else:
        lines.append(
            "- Windows: have the customer open Disk Management -> Online -> Initialize (GPT) -> "
            "New Simple Volume -> assign a drive letter.")
        lines.append(
            "- Linux: ask the customer to run and paste lsblk -f, then partition + mkfs "
            "(destructive if data exists) -> mount -> UUID entry in /etc/fstab.")
    lines += [
        "- Official guidance: %s" % DOC_LINKS["data_disk_guide"],
        "- Keep a mount after reboot (UUID in fstab): %s" % DOC_LINKS["fstab_uuid"],
    ]
    return lines


def build_sections(args: argparse.Namespace, facts: Dict[str, Any], disks: List[Dict[str, Any]],
                   guest: Dict[str, Any], snapshots: Dict[str, Any], os_family: str,
                   verdicts: List[Dict[str, Any]], gaps: List[str],
                   caller_label: str) -> List[Tuple[str, List[str]]]:
    sections: List[Tuple[str, List[str]]] = []

    scope = ["- Region queried: `%s`" % args.region_id,
             "- Instance inspected: `%s`" % args.instance_id,
             "- Caller identity: `%s`" % caller_label,
             "- Instance state returned: `%s`" % (facts.get("status") or "not returned"),
             "- Guest family used for the chain: `%s`" % (os_family or OS_UNKNOWN),
             "- Disks evaluated: `%d`" % len(disks),
             "- Customer wording supplied: `%s`" % ("yes" if args.symptom else "no")]
    if args.disk_id:
        scope.append("- Disk ids named by the customer: %s" % ", ".join("`%s`" % d for d in args.disk_id))
    else:
        scope.append("- No disk id was supplied, so every disk attached to the instance was evaluated.")
    sections.append(("What was checked", scope))

    rule_topic, rule_lines = disk_rule_for(args.symptom)
    if rule_topic:
        windows_lines = (DISK_RULE_WINDOWS_LINES.get(rule_topic, ())
                         if os_family == "windows" else ())
        if windows_lines:
            rule_lines = tuple(
                line for line in rule_lines
                if not re.search(DISK_RULE_LINUX_STEP_RE, line))
        answered = ["- %s" % line for line in rule_lines]
        answered.extend("- %s" % line for line in windows_lines)
        if rule_topic in DISK_RULE_CONSENT_TOPICS:
            answered.append("- %s" % DISK_RULE_CONSENT_LINE)
        doc_key = DISK_RULE_TOPIC_DOCS.get(rule_topic)
        if windows_lines:
            doc_key = DISK_RULE_WINDOWS_DOCS.get(rule_topic) or doc_key
        if doc_key:
            answered.append("- Official guidance: %s"
                            % (DISK_RULE_DOC_LINKS.get(doc_key) or DOC_LINKS.get(doc_key, "")))
        sections.append(("Answer to the asked question (offline rule, no cloud read)", answered))

    if verdicts:
        rows = [(str(v["evidence"].get("disk_id", "")),
                 str(v["evidence"].get("size_gib", "")),
                 ", ".join(v["findings"]) or "no finding",
                 v["explanation"] or "") for v in verdicts]
        sections.append(("Chain verdict per disk", rb.markdown_table(
            ("disk id", "size GiB", "findings", "what that means"), rows)))

    first = verdicts[0] if verdicts else None
    if first:
        chain_lines = rb.markdown_table(
            ("step", "plane / meaning", "state"), rb.chain_table(first))
        first_findings = first.get("findings", [])
        probe_missing = (FINDING_PROBE_NOT_RUN in first_findings
                         or FINDING_PROBE_UNAVAILABLE in first_findings)
        explanation = first["explanation"]
        if not explanation:
            if probe_missing:
                explanation = ("the disk is attached to this instance on the cloud side; the OS "
                               "half has not been read, so visibility inside the guest is not yet "
                               "verified")
            elif FINDING_MOUNTED_AND_READABLE in first_findings:
                explanation = ("the chain is complete; the disk is attached, enumerated, has a "
                               "filesystem and is mounted")
        next_step = first["manual_next_step"]
        if not next_step:
            if FINDING_MOUNTED_AND_READABLE in first_findings:
                next_step = "none; the chain is complete"
            elif probe_missing:
                next_step = ("approve the guest probe (or paste lsblk/df or Disk Management output) "
                             "so the OS half can be checked; the chain is not complete yet")
            else:
                next_step = "see the remediation guidance below"
        chain_lines += [
            "",
            "- Explanation: %s" % (explanation or "nothing to report"),
            "- Manual step for the customer: %s" % next_step,
            "- This skill does not perform that step.",
        ]
        if FINDING_DISK_NOT_ATTACHED in first_findings:
            if os_family == "windows":
                chain_lines.append(
                    "- After attaching, ask the customer to bring the volume Online in Disk "
                    "Management, initialize it if needed, and assign a drive letter so paths can see it.")
            else:
                chain_lines.append(
                    "- After attaching, ask the customer to mount the filesystem at a chosen path "
                    "and persist it with a UUID entry in /etc/fstab so it survives reboot.")
        sections.append(("Where the chain stops", chain_lines))

    snapshot_copy_low = (args.symptom or "").lower()
    if any(marker in snapshot_copy_low for marker in
           ("快照的内容", "从快照", "快照创建", "快照复制", "快照恢复", "快照盘",
            "copy snapshot", "from snapshot", "snapshot-created", "restore from snapshot")):
        sections.append(("Copying snapshot data to a new disk (guidance only)", [
            "- Have the customer confirm the source snapshot is completed (ECS console -> Snapshots).",
            "- Have the customer create a disk from that snapshot in the SAME zone as the target "
            "instance (console -> buy disk -> create from snapshot); a disk only attaches to an "
            "instance in the same zone.",
            "- Have the customer attach the snapshot-created disk to the instance in the console.",
            "- Have the customer mount it directly at an empty path and copy the data -- do NOT "
            "initialize or format it: a snapshot-created disk already carries the source partition "
            "and filesystem, and formatting would destroy the snapshot data.",
            "- Official guidance: %s" % DOC_LINKS["disk_from_snapshot"],
        ]))

    if disks and guest.get("collected"):
        sections.append(("Cloud disk id to guest device map", rb.markdown_table(
            ("disk id", "size GiB", "guest device matched by size", "mount point"),
            rb.device_map_rows(verdicts, guest))))

    if snapshots:
        lines = ["- Snapshots returned for this instance in this region: `%d`" % snapshots["snapshot_count"]]
        for disk_id, count in sorted(snapshots.get("by_disk", {}).items()):
            lines.append("- `%s`: `%d` snapshot record(s)" % (disk_id, count))
        lines.append("- Have the customer create a snapshot before any partitioning, formatting or "
                     "volume change; a snapshot that exists is the recovery point (a manual decision; snapshots are billed).")
        sections.append(("Recovery point before remediation", lines))

    # Scoped to the verdicts that actually read NO filesystem. A live run has a 20G
    # system disk and a 20G data disk on the same instance; aggregating over every
    # verdict pulled the mounted system disk into the initialization target and told
    # the customer to mkfs it. Only the uninitialised disk may be named.
    uninit_devices = sorted({
        name
        for verdict in verdicts
        if FINDING_DISK_ATTACHED_TO_THIS_INSTANCE in verdict.get("findings", [])
        and FINDING_NO_FILESYSTEM in verdict.get("findings", [])
        for name in (verdict.get("evidence", {}).get("size_matched_devices") or [])})
    unmounted_devices = sorted({
        name
        for verdict in verdicts
        if FINDING_DISK_ATTACHED_TO_THIS_INSTANCE in verdict.get("findings", [])
        and FINDING_FILESYSTEM_NOT_MOUNTED in verdict.get("findings", [])
        for name in (verdict.get("evidence", {}).get("size_matched_devices") or [])})
    uuid_by_device = {device["name"]: device.get("uuid", "")
                      for device in guest.get("devices", [])
                      if device.get("name") in unmounted_devices and device.get("uuid")}
    if _attached_not_visible(verdicts):
        symptom_text = (args.symptom or "").lower()
        boot_is_blocked = any(
            marker in symptom_text for marker in
            ("give root password", "emergency mode", "maintenance", "卡在",
             "进不去系统", "启动不了", "无法启动", "无法正常启动", "不能正常启动",
             "启动失败", "起不来"))
        if not boot_is_blocked:
            sections.append(("Making an attached disk visible (guidance only)",
                             _visibility_guidance_lines(
                                 os_family, guest, uninit_devices,
                                 not_initialized=bool(uninit_devices),
                                 unmounted=unmounted_devices,
                                 uuid_by_device=uuid_by_device)))

    if guest.get("raw"):
        if guest.get("source") == "ticket-pasted":
            lines: List[str] = ["Readings supplied with this request (pasted in the "
                                "ticket or recovered from its screenshots); no command "
                                "was dispatched by this run:"]
        else:
            lines: List[str] = ["Collected through Cloud Assistant, one approved command "
                                "at a time:"]
        if not guest.get("collected"):
            lines.append("")
            lines.append("    (no usable rows parsed from the output above)")
        for command, output in _guest_reads_in_decisive_order(guest["raw"]):
            lines.append("")
            lines.append("    $ %s" % command)
            for row in (output or "").splitlines()[:60]:
                lines.append("      %s" % mask_secrets(row))
        sections.append(("Guest readings as returned", lines))

    symptom_low = (args.symptom or "").lower()
    boot_blocked = any(marker in symptom_low for marker in
                       ("give root password", "emergency mode", "maintenance",
                        "卡在", "进不去系统", "启动不了", "无法启动", "无法正常启动",
                        "不能正常启动", "启动失败", "起不来"))
    fstab_mistake = "fstab" in symptom_low and any(
        marker in symptom_low for marker in ("改错", "设置错", "改回", "错误", "写错"))
    if boot_blocked or fstab_mistake:
        sections.append(("Boot blocked by a mount entry (guidance only)", [
            "- Have the customer snapshot the disks first: it is the only recovery point "
            "before editing boot mounts.",
            "- Ask the customer to comment out every non-system-disk entry in /etc/fstab "
            "(including NAS), then reboot to confirm the instance boots again.",
            "- Have the customer restart it themselves only after they confirm a business "
            "window; this skill never restarts it for them.",
            "- Have the customer re-enable the commented entries one at a time, rebooting "
            "after each, to identify the entry that blocks boot.",
            "- Have the customer rewrite the surviving entries with UUID plus defaults,nofail "
            "so a later mount failure cannot block boot; a spec change can rename devices.",
            "- Official guidance: %s" % DOC_LINKS["fstab_uuid"],
        ]))
    if any(marker in symptom_low for marker in ("卸载", "detach", "unmount", "解除挂载")):
        sections.append(("Detaching a data disk (guidance only)", [
            "- Have the customer treat detaching as a two-plane operation: this skill only "
            "guides and never dispatches DetachDisk for them.",
            "- Ask the customer for consent, then have them unmount the filesystem FIRST "
            "(umount on Linux, offline the disk on Windows) so no process still holds it.",
            "- Have the customer detach the data disk in the console afterwards: its status "
            "becomes Available, it can be re-attached later, and detaching does not delete "
            "the disk data.",
            "- Have the customer never detach from the console while the guest still has it "
            "mounted: that risks filesystem corruption. Unmount first, then detach.",
            "- Official guidance: %s" % DOC_LINKS["detach_data_disk"],
        ]))
    if any(marker in symptom_low for marker in
           ("使用容量", "使用量", "已用", "剩余空间", "用了多少", "used space", "disk usage")):
        usage_lines = ["- Have the customer know cloud-side capacity (DescribeDisks.Size) is the "
                       "provisioned disk size, not what the filesystem has used; the two are "
                       "different numbers."]
        for verdict in verdicts:
            size = verdict["evidence"].get("size_gib")
            if size:
                usage_lines.append("- `%s`: cloud capacity `%s` GiB."
                                   % (verdict["evidence"].get("disk_id", ""), size))
        if guest.get("collected"):
            usage_lines.append("- Have the customer read the guest df rows above for "
                               "used/available inside the filesystem; cloud capacity is not "
                               "the same as filesystem used.")
        else:
            usage_lines.append("- Ask the customer to approve the guest df probe to see used "
                               "space: filesystem used/available was not read this run, so only "
                               "cloud capacity is reported.")
        sections.append(("Cloud capacity vs filesystem usage", usage_lines))

    handoff = route_handoff(args.symptom)
    if handoff or not in_scope(args.symptom):
        lines = []
        for matched, destination, reason in handoff:
            lines.append("- Trigger wording seen: `%s` -> %s. %s" % (matched, destination, reason))
        if not handoff:
            lines.append("- No out-of-scope wording was supplied, so no handoff is proposed.")
        lines.append("- Anything that changes placement, partitions, formats, mounts, brings a volume "
                     "online or restarts the instance is guidance only; see references/disk-attach-os-visibility__handoff-boundaries.md.")
        sections.append(("Scope and handoff", lines))

    if gaps:
        sections.append(("Limitations of this run", ["- %s" % gap for gap in gaps]))

    asked = os.environ.get("ECS_CUSTOMER_QUESTION", "") or ""
    if re.search(r"(?i)wwid|wwn|序列号|serial|唯一标识|多重挂载|共享盘", asked):
        sections.append(("Identifying the same disk across instances", [
            "- Ask the customer to run and paste cat /sys/class/block/<device>/wwid "
            "(for example nvme3n1) - on NVMe shared disks this is the stable identifier.",
            "- Ask the customer to run and paste lsblk -o NAME,SIZE,WWN,SERIAL to list every "
            "device with its WWN and serial side by side.",
            "- The name under /dev/disk/by-id and the SERIAL column carry the disk's serial "
            "number, not its WWID; do not match a shared disk by /dev/vdX or by serial alone.",
        ]))
    if re.search(r"(?i)(不影响|影响).{0,8}业务|需要重启|要不要重启|用不用重启|热挂载", asked):
        sections.append(("Attaching a disk without affecting the workload", [
            "- Attaching a data disk is hot-plug: no reboot and no instance stop is needed, "
            "and the running workload is not interrupted.",
            "- Have the customer mount it at an EMPTY directory; mounting over a directory "
            "that already holds data hides that data until it is unmounted.",
            "- Have the customer persist the mount with a UUID entry and defaults,nofail in "
            "/etc/fstab, so a later mount failure cannot block the next boot.",
        ]))

    guest_read = bool(guest.get("collected") or guest.get("raw"))
    if not guest_read and not rule_topic:
        ask = [
            "- Ask the customer to approve one inspect-only reading (it changes nothing) "
            "or paste it: `lsblk -f`, `blkid`, `df -h`, `cat /etc/fstab`; Windows: Disk "
            "Management; plus the error text and RequestId.",
        ]
        sections.append(("What to ask the customer for next", ask))
    docs = ["- Use a disk after attaching it: %s" % DOC_LINKS["data_disk_guide"],
            "- Keep a mount after reboot with a UUID entry: %s" % DOC_LINKS["fstab_uuid"]]
    if guest_read:
        docs.extend([
            "- Attach a data disk: %s" % DOC_LINKS["attach_data_disk"],
            "- Detach a data disk: %s" % DOC_LINKS["detach_data_disk"],
            "- Device names on NVMe instances: %s" % DOC_LINKS["nvme_protocol"],
            "- Per-instance attachment limits: %s" % DOC_LINKS["limitations"]])
    sections.append(("Official guidance", docs))
    return sections


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    session_id = new_session_id()

    missing = _require(args)
    if missing:
        print(json.dumps({"status": "FAIL", "reason": missing, "session_id": session_id,
                          "next_action": "Ask the customer for the region id and the instance id."},
                         indent=2))
        print(STATUS_FAIL)
        print("NEXT_ACTION: collect --region-id and --instance-id from the customer, then rerun.")
        return 2

    if args.print_only:
        preview_requests(session_id, args)
        print(STATUS_OK)
        print("NEXT_ACTION: rerun without --print-only once these requests are approved.")
        return 0

    gaps: List[str] = []
    facts: Dict[str, Any] = {}
    disks: List[Dict[str, Any]] = []
    snapshots: Dict[str, Any] = {}
    guest: Dict[str, Any] = rb.parse_guest_results(None)
    errors: List[str] = []
    caller_label = "not checked"
    used_actions: List[str] = []

    if not args.skip_identity_check:
        used_actions.append("GetCallerIdentity")
        try:
            identity, identity_ok = sts_token.summarise(
                sts_token.fetch_identity(session_id, min(30, args.timeout)))
            caller_label = identity["account_label"] if identity_ok else "unproven"
            if not identity_ok:
                gaps.append("Caller identity could not be proven; the CLI may not be configured.")
        except CliError as error:
            caller_label = "unproven"
            gaps.append("Caller identity check failed (%s)." % error.code)
            if error.is_permission_failure:
                errors.append("GetCallerIdentity was refused with NoPermission or ImplicitDeny. "
                              "references/ram-policies.md holds the minimal policy to request.")

    calls: List[Tuple[str, Any]] = [
        ("DescribeInstances", lambda: _fetch_instance(session_id, args.region_id,
                                                      args.instance_id, args.timeout)),
        ("DescribeDisks", lambda: _fetch_disks(session_id, args.region_id, args.instance_id,
                                               args.disk_id, args.timeout)),
    ]
    if not args.skip_snapshots:
        calls.append(("DescribeSnapshots",
                      lambda: _fetch_snapshot_presence(session_id, args.region_id,
                                                       args.instance_id, args.timeout)))
    for action, invoke in calls:
        if action not in ALLOWED_ACTIONS:
            continue
        used_actions.append(action)
        try:
            value, call_gaps = invoke()
        except CliError as error:
            errors.append("%s failed: %s" % (action, mask_secrets("%s: %s" % (error.code, error.message))))
            if error.is_permission_failure:
                errors.append("%s was refused with NoPermission or ImplicitDeny for this caller. "
                              "references/ram-policies.md holds the minimal policy to request." % action)
            gaps.append("%s returned no usable data." % action)
            continue
        gaps.extend(call_gaps)
        if action == "DescribeInstances":
            facts = value
        elif action == "DescribeDisks":
            disks = value
        else:
            snapshots = value

    if args.guest_findings:
        try:
            guest = rb.parse_guest_results(_load_guest(args.guest_findings))
        except (CliError, OSError) as error:
            guest = rb.parse_guest_results(None)
            guest["gaps"] = [str(getattr(error, "message", error))]
            gaps.append("Guest findings could not be loaded, so the chain stops at the cloud half.")
    else:
        gaps.append("Guest readings were not supplied, so steps 3 to 5 of the chain are unverified.")

    os_family = args.os if args.os != "auto" else rb.os_family_from(facts)
    if facts and str(facts.get("status", "")).lower() not in ("running", ""):
        gaps.append(FINDING_EXPLANATION[FINDING_INSTANCE_STOPPED])

    verdicts: List[Dict[str, Any]] = []
    if disks and FINDING_INSTANCE_NOT_FOUND not in gaps:
        for disk in disks:
            verdicts.append(rb.evaluate_disk(disk, args.instance_id, guest, os_family, args.symptom))
    elif not disks and FINDING_INSTANCE_NOT_FOUND in gaps:
        verdicts.append(rb.evaluate_disk({"disk_id": "", "size_gib": None, "disk_type": "", "category": "",
                                          "status": "", "attached_instances": [], "cloud_device": "",
                                          "portable": None, "billing": "", "delete_with_instance": None,
                                          "serial": "", "multi_attach": "", "raw": {}},
                                         args.instance_id, guest, os_family, args.symptom))

    blocked = [v["blocked_step"] for v in verdicts if v.get("blocked_step")]
    if errors:
        status = STATUS_FAIL
    elif gaps or (guest.get("gaps") and not guest.get("collected")):
        status = STATUS_DEGRADED
    else:
        status = STATUS_OK

    if args.json:
        print(json.dumps({
            "status": status.split(": ", 1)[1],
            "session_id": session_id,
            "caller_identity": caller_label,
            "region_id": args.region_id,
            "instance_id": args.instance_id,
            "os_family": os_family or OS_UNKNOWN,
            "instance": {key: value for key, value in facts.items() if key != "raw"},
            "disks": [{key: value for key, value in disk.items() if key != "raw"} for disk in disks],
            "snapshots": snapshots,
            "verdicts": verdicts,
            "handoff": route_handoff(args.symptom),
            "gaps": gaps,
            "errors": errors,
            "guest_commands": guest.get("commands", []),
            "next_action": ("guest manual steps for the blocked link only" if guest.get("collected")
                            else GUEST_GATE_TEXT),
        }, indent=2, default=str))
        # observability marker belongs on stderr: mixing it into stdout broke strict
        # json.loads for machine consumers (faultlab P2, 2026-10-08)
        print("# session %s | actions used: %s" % (session_id, ", ".join(used_actions) or "none"),
              file=sys.stderr)
        return 0 if status != STATUS_FAIL else 1
    else:
        sections = build_sections(args, facts, disks, guest, snapshots, os_family, verdicts, gaps,
                                  caller_label)
        if errors:
            sections.append(("Platform errors", ["- %s" % error for error in errors]))
        sys.stdout.write(rb.render_markdown(
            "ECS disk attach and OS visibility report", sections))

    new_disk_lead = _new_disk_lead_line(verdicts, os_family, guest) or \
        _placement_lead_line(verdicts)
    if new_disk_lead:
        print(new_disk_lead)

    rule_topic, _rule_lines = disk_rule_for(args.symptom)
    if rule_topic and DISK_RULE_CONCLUSIONS.get(rule_topic):
        print("RULE-LEAD: [platform_rule] %s" % DISK_RULE_CONCLUSIONS[rule_topic])

    for error in errors:
        sys.stderr.write("[WARN] %s\n" % mask_secrets(error))

    print(status)
    if status == STATUS_DEGRADED and not args.guest_findings:
        print("NEXT_ACTION: " + GUEST_GATE_TEXT)
    elif blocked and FINDING_DISK_NOT_FOUND_IN_REGION in blocked:
        print("NEXT_ACTION: confirm the region id with the customer; disk ids do not travel between regions.")
    elif status == STATUS_FAIL:
        print("NEXT_ACTION: fix the reported permission or connectivity problem, then rerun. "
              "Do not ask the customer for an AccessKey pair.")
    elif guest.get("collected"):
        print("NEXT_ACTION: give the customer the manual step for the blocked link only, with the risk "
              "statement and the matching help document. Do not run it for them.")
    else:
        print("NEXT_ACTION: " + GUEST_GATE_TEXT)
    print("# session %s | actions used: %s" % (session_id, ", ".join(used_actions) or "none"))
    return 0 if status != STATUS_FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
