#!/usr/bin/env python3
"""Single entry point for ECS migration-to-cloud assessment.

Sub-commands
  whoami               confirm the credential and tag the report with the account
  assess               inventory a source instance and produce a migration verdict
  source-inventory     raw cloud-side readings for the migration source
  target-availability  check whether a target resource is sellable
  guest-probe          run ONE inspection-only command in the guest, after confirmation
  invocation-result    read back the output of a guest probe
  protect-snapshot     create one snapshot before a change, after confirmation
  route                match a symptom or error string against the known causes

The agent calls this script and never assembles aliyun CLI commands by hand.
"""

import argparse
import base64
import io
import json
import re
import sys
import time

import _cli
import sts_token
from _constants import (
    BOUNDARY_STATEMENT,
    COMMAND_METACHARACTERS,
    CONFIRMATION_NOTICE,
    ECS_PRODUCT,
    ERROR_SIGNATURES,
    GUEST_PROBES,
    KNOWN_GUEST_PATHS,
    LINUX_PATH_PATTERN,
    LOCAL_DISK_CATEGORY_PREFIXES,
    MAX_INSTANCE_IDS,
    MAX_INVOCATION_OUTPUT_CHARS,
    MIGRATION_PATHS,
    NVME_INSTANCE_FAMILIES,
    OS_SUPPORT_POSTURE,
    PAGE_SIZE,
    PRECONDITIONS,
    PROBE_POLL_INTERVAL_SECONDS,
    PROBE_WAIT_TIMEOUT_SECONDS,
    READ_TIMEOUT_SECONDS,
    SKILL_NAME,
    SNAPSHOT_NOTICE,
    SYMPTOM_ROUTING,
    WINDOWS_PATH_PATTERN,
    WRITE_TIMEOUT_SECONDS,
)

CONFIRM_TOKEN = "yes"
NONFINAL_INVOCATION_STATES = ("running", "pending", "scheduled", "invoking", "stopping")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
class Report(object):
    """Collects the printed report plus the worst status seen."""

    def __init__(self, title, session_id, uid="unknown"):
        self.lines = []
        self.session_id = session_id
        self.uid = uid
        self.gaps = []
        self.next_actions = []
        self.worst = "OK"
        self.emit("=" * 72)
        self.emit(title)
        self.emit("skill      : {}".format(SKILL_NAME))
        self.emit("session_id : {}".format(session_id))
        self.emit("uid        : {}".format(uid))
        self.emit("=" * 72)

    def emit(self, text=""):
        self.lines.append(str(text))

    def section(self, name):
        self.emit("")
        self.emit("## {}".format(name))

    def item(self, key, value):
        self.emit("  {:<22}: {}".format(key, value))

    def note(self, text):
        self.emit("  - {}".format(text))

    def action(self, text):
        self.next_actions.append(text)

    def gap(self, text):
        self.gaps.append(text)
        if self.worst == "OK":
            self.worst = "DEGRADED"

    def fail(self, text=None):
        self.worst = "FAIL"
        if text:
            self.gap(text)

    def finish(self):
        if self.gaps:
            self.section("Evidence gaps")
            for gap in self.gaps:
                self.note(gap)
        self.section("Verdict")
        self.emit("  {}".format(BOUNDARY_STATEMENT))
        actions = self.next_actions or [
            "Review the evidence list with the customer and agree the migration path before "
            "anything is scheduled."]
        self.emit("")
        self.emit("STATUS: {}".format(self.worst))
        for action in actions:
            self.emit("NEXT_ACTION: {}".format(action))
        print("\n".join(self.lines))


# ---------------------------------------------------------------------------
# Cloud-side queries
# ---------------------------------------------------------------------------
def fetch_instances(report, region_id, instance_ids, session_id):
    params = {"RegionId": region_id, "PageSize": PAGE_SIZE}
    if instance_ids:
        params["InstanceIds"] = json.dumps(instance_ids)
    payload = _cli.describe(ECS_PRODUCT, "DescribeInstances", params=params,
                            session_id=session_id, timeout=READ_TIMEOUT_SECONDS,
                            stream=sys.stderr)
    if payload is None:
        report.gap("DescribeInstances returned nothing for {}{}; the inventory below is "
                   "incomplete.".format(region_id,
                                        " for " + ",".join(instance_ids) if instance_ids else ""))
        return []
    instances = (payload.get("Instances") or {}).get("Instance") or []
    if instance_ids:
        found = {item.get("InstanceId") for item in instances}
        missing = [iid for iid in instance_ids if iid not in found]
        if missing:
            report.gap("Not returned by DescribeInstances (released, in another region, or not "
                       "visible to this account): {}".format(", ".join(missing)))
    return instances


def fetch_status_map(report, region_id, instance_ids, session_id):
    if not instance_ids:
        return {}
    params = {"RegionId": region_id, "PageSize": PAGE_SIZE}
    for index, instance_id in enumerate(instance_ids[:MAX_INSTANCE_IDS], start=1):
        params["InstanceId.{}".format(index)] = instance_id
    payload = _cli.describe(ECS_PRODUCT, "DescribeInstanceStatus", params=params,
                            session_id=session_id, timeout=READ_TIMEOUT_SECONDS,
                            stream=sys.stderr)
    if payload is None:
        report.gap("DescribeInstanceStatus unavailable; run state was not verified.")
        return {}
    statuses = (payload.get("InstanceStatuses") or {}).get("InstanceStatus") or []
    return {item.get("InstanceId"): item.get("Status") for item in statuses}


def fetch_disks(report, region_id, instance_id, session_id):
    params = {"RegionId": region_id, "InstanceId": instance_id, "PageSize": PAGE_SIZE}
    payload = _cli.describe(ECS_PRODUCT, "DescribeDisks", params=params,
                            session_id=session_id, timeout=READ_TIMEOUT_SECONDS,
                            stream=sys.stderr)
    if payload is None:
        report.gap("DescribeDisks unavailable for {}; local-disk and encryption constraints "
                   "were not verified.".format(instance_id))
        return []
    return (payload.get("Disks") or {}).get("Disk") or []


def fetch_assistant_online(report, region_id, instance_id, session_id):
    params = {"RegionId": region_id, "InstanceId.1": instance_id}
    payload = _cli.describe(ECS_PRODUCT, "DescribeCloudAssistantStatus", params=params,
                            session_id=session_id, timeout=READ_TIMEOUT_SECONDS,
                            stream=sys.stderr)
    if payload is None:
        report.gap("DescribeCloudAssistantStatus unavailable; in-guest readings may not be "
                   "possible for {}.".format(instance_id))
        return False
    items = ((payload.get("InstanceCloudAssistantStatusSet") or {})
             .get("InstanceCloudAssistantStatus") or [])
    for item in items:
        if item.get("InstanceId") == instance_id:
            return str(item.get("CloudAssistantStatus", "")).lower() == "true"
    report.gap("{} has no Cloud Assistant record; it is not registered as a managed host."
               .format(instance_id))
    return False


def collect(report, args, session_id, deep):
    """Read the source side once; return [{instance, disks, assistant_online}]."""
    instance_ids = _split_ids(args.instance_id)
    instances = fetch_instances(report, args.region_id, instance_ids, session_id)
    statuses = fetch_status_map(report, args.region_id,
                               [i.get("InstanceId") for i in instances if i.get("InstanceId")],
                               session_id)
    collected = []
    for instance in instances:
        entry = {"instance": instance, "status": statuses.get(instance.get("InstanceId")),
                 "disks": [], "assistant_online": False}
        if deep:
            entry["disks"] = fetch_disks(report, args.region_id, instance.get("InstanceId"),
                                         session_id)
            entry["assistant_online"] = fetch_assistant_online(report, args.region_id,
                                                               instance.get("InstanceId"),
                                                               session_id)
        collected.append(entry)
        _print_instance(report, entry)
    if not instances:
        report.gap("No instance was returned, so nothing could be read from the cloud side.")
    return collected


def _print_instance(report, entry):
    instance = entry["instance"]
    report.emit("")
    report.item("InstanceId", instance.get("InstanceId", ""))
    report.item("Status", entry.get("status") or instance.get("Status", "unknown"))
    report.item("InstanceType", "{} (family {})".format(instance.get("InstanceType", ""),
                                                       instance_family(instance.get("InstanceType"))))
    report.item("OS", instance.get("OSNameEn") or instance.get("OSName") or "unknown")
    report.item("Network", "{} vpc={} vswitch={}".format(
        instance.get("InstanceNetworkType", ""), instance.get("VpcId", ""),
        instance.get("VSwitchId", "")))
    report.item("SecurityGroups", ", ".join(
        ((instance.get("SecurityGroupIds") or {}).get("SecurityGroupId") or [])) or "none")
    public_ips = (instance.get("PublicIpAddress") or {}).get("IpAddress") or []
    eip = (instance.get("EipAddress") or {}).get("IpAddress") or ""
    report.item("Public address", "{}{}".format(
        ", ".join(public_ips) or "none", " (EIP {})".format(eip) if eip else ""))
    report.item("Created / Expired", "{} / {}".format(instance.get("CreationTime", "?"),
                                                     instance.get("ExpiredTime", "?")))


# ---------------------------------------------------------------------------
# Judgement over the readings
# ---------------------------------------------------------------------------
def instance_family(instance_type):
    parts = str(instance_type or "").split(".")
    return parts[1] if len(parts) > 2 else ""


def os_posture(os_name):
    label = (os_name or "").strip().lower()
    for needle, verdict in OS_SUPPORT_POSTURE:
        if needle in label:
            return verdict
    return "no documented screening posture for this release; confirm against the official SMC " \
           "supported-OS list before scheduling"


def match_error(text):
    lowered = (text or "").lower()
    hits = []
    for entry in ERROR_SIGNATURES:
        matched = [sig for sig in entry["signatures"] if sig in lowered]
        if matched:
            hits.append((entry, matched))
    return hits


def match_symptom(text):
    lowered = (text or "").lower()
    hits = []
    for name, needles, guidance in SYMPTOM_ROUTING:
        if any(needle in lowered for needle in needles):
            hits.append((name, guidance))
    return hits


def safe_path(raw, os_type):
    """Accept a bare path only; anything that could chain a second command is refused."""
    if raw is None or raw == "":
        raise ValueError("this probe needs an explicit --path")
    if any(token in raw for token in COMMAND_METACHARACTERS):
        raise ValueError("command metacharacters are not accepted")
    pattern = WINDOWS_PATH_PATTERN if os_type == "windows" else LINUX_PATH_PATTERN
    if not re.match(pattern, raw):
        raise ValueError("not a plain {} path".format(os_type))
    return raw


def local_disk(disk):
    category = str(disk.get("Category") or "").lower()
    return category.startswith(LOCAL_DISK_CATEGORY_PREFIXES)


def encrypted(disk):
    return disk.get("Encrypted") in (True, "true", "True")


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------
def cmd_whoami(args, session_id):
    identity = sts_token.get_caller_identity(session_id=session_id, stream=sys.stderr)
    if identity is None:
        print("STATUS: FAIL")
        print("NEXT_ACTION: run `aliyun configure` with a profile of the account that owns the "
              "migration source, then re-run. Never paste an AccessKey pair or a security "
              "token into the conversation.")
        return 2
    report = Report("Caller identity", session_id, uid=sts_token.account_id(identity))
    report.section("Identity")
    report.item("AccountId", sts_token.account_id(identity) or "unknown")
    report.item("Arn", _cli.mask_secrets(identity.get("Arn", "")))
    report.action("Re-run `assess` with the --region-id that holds the migration source.")
    report.finish()
    return 0


def cmd_source_inventory(args, session_id):
    report = _open_report("Migration source inventory", session_id)
    collect(report, args, session_id, deep=False)
    report.action("Run `assess` for the compatibility, disk, and boot-driver judgement.")
    report.finish()
    return 0 if report.worst == "OK" else 1


def cmd_assess(args, session_id):
    report = _open_report("Migration-to-Alibaba-Cloud assessment", session_id)
    collected = collect(report, args, session_id, deep=True)
    for entry in collected:
        _assess_entry(report, entry, args)
    if not collected:
        _offline_note(report)
    _emit_guidance(report, args)
    report.finish()
    return 0 if report.worst != "FAIL" else 1


def _assess_entry(report, entry, args):
    instance = entry["instance"]
    instance_id = instance.get("InstanceId", "")
    report.section("Assessment of {}".format(instance_id))
    report.item("OS posture", os_posture(instance.get("OSNameEn") or instance.get("OSName")))
    report.note("Screening posture only: the authoritative matrix is the official SMC "
                "supported-OS list, and very old releases need a migration drill.")
    family = instance_family(instance.get("InstanceType"))
    if family in NVME_INSTANCE_FAMILIES:
        report.item("Block device", "family {} boots from NVMe, so the source image must "
                                   "already carry the NVMe driver".format(family))
        report.note("Without the driver the instance stays in `Starting`; device names also "
                    "shift from /dev/vdb to /dev/nvme1n1, so any saved path breaks.")
    for disk in entry["disks"]:
        label = "{} ({} GiB, {})".format(disk.get("DiskId", ""), disk.get("Size", "?"),
                                        disk.get("Category", "unknown"))
        report.item("Disk", label)
        if local_disk(disk):
            report.note("Local disk: data is lost when the instance is stopped or redeployed. "
                        "Back it up before any migration step.")
        if encrypted(disk):
            report.note("Encrypted disk: migration copies the readable data and the target "
                        "disk is created without encryption.")
    if entry["disks"]:
        report.note("Disk sizes above are provisioned sizes. The shrink decision needs the "
                    "in-guest `df -h` reading, which no cloud API returns.")
    report.item("Cloud Assistant", "online" if entry["assistant_online"] else "not confirmed")
    if not entry["assistant_online"]:
        report.note("Ask the customer to run the same inspection command on the source and "
                    "paste the output, or register the host as a managed instance first.")


def _offline_note(report):
    report.section("A source that is not an ECS instance")
    report.note("On-premises, VMware, hyper-converged, physical, and other-cloud sources have "
                "no cloud-side reading at all. Assessment then rests on the facts the customer "
                "states plus their own inspection output.")


def _emit_guidance(report, args):
    report.section("Candidate paths")
    for name, when, link in MIGRATION_PATHS:
        report.emit("  {}".format(name))
        report.emit("    when: {}".format(when))
        report.emit("    doc : {}".format(link))
    if args.shrink:
        report.note("Shrink: the target must stay above the bytes in use, so the smallest "
                    "workable target comes from the `df -h` reading, not from the source size.")
    if args.cross_account:
        report.note("Cross-account: instances cannot be transferred directly. Create a custom "
                    "image, share it in the same region (or copy it first), then re-create the "
                    "instance in the target account.")
    if args.expired_source:
        report.note("Source that can no longer be logged into: whole-server migration is not "
                    "possible. Use an image import, or rebuild the service from a backup.")

    report.section("Preconditions before any migration window")
    for precondition in PRECONDITIONS:
        report.note(precondition)

    report.section("Handled by a human, never by this skill")
    report.note("Quotation, discounts, refunds, compensation, renewal handling, ICP filing, and "
                "machine-room addresses.")
    report.note("Boot-loader rebuild, file-system repair, network re-configuration, service or "
                "instance restart, agent uninstall, snapshot deletion, and partition changes.")
    report.action("Create a snapshot for every disk in scope before any change "
                  "(`protect-snapshot`), then agree the low-peak window.")
    report.action("Tell the customer the public address changes: lower the DNS TTL and rebuild "
                  "the security groups on the target.")


def cmd_target_availability(args, session_id):
    report = Report("Target resource availability", session_id, uid=_cached_uid(session_id))
    params = {"RegionId": args.region_id, "DestinationResource": args.destination_resource}
    for key, value in (("ZoneId", args.zone_id), ("InstanceType", args.instance_type),
                       ("InstanceChargeType", args.instance_charge_type),
                       ("SystemDiskCategory", args.system_disk_category),
                       ("DataDiskCategory", args.data_disk_category),
                       ("IoOptimized", args.io_optimized),
                       ("NetworkCategory", args.network_category)):
        if value:
            params[key] = value
    report.section("DescribeAvailableResource {}".format(args.region_id))
    report.item("parameters", ", ".join("{}={}".format(k, v) for k, v in sorted(params.items())))
    payload = _cli.describe(ECS_PRODUCT, "DescribeAvailableResource", params=params,
                           session_id=session_id, timeout=READ_TIMEOUT_SECONDS,
                           stream=sys.stderr)
    if payload is None:
        report.fail()
        report.action("Re-check the parameters, or read sellability in the console instead.")
    else:
        zones = (payload.get("AvailableZones") or {}).get("AvailableZone") or []
        report.item("zones returned", len(zones))
        for zone in zones:
            report.emit("  {} [{}] {}".format(zone.get("ZoneId", ""), zone.get("Status", ""),
                                             zone.get("StatusCategory", "")))
        if not zones:
            report.gap("Nothing sellable matched: this is exactly the risk for a very old system "
                       "that depends on a retired instance type.")
            report.action("Pick a family that is sellable here and re-check the operating-system "
                          "posture against the official SMC supported-OS list.")
        else:
            report.action("Quote the zone and family back to the customer; purchasing and "
                          "instance-type change stay manual.")
    report.finish()
    return 0 if report.worst == "OK" else 1


def cmd_guest_probe(args, session_id):
    probe = GUEST_PROBES.get(args.probe)
    if probe is None:
        return _refused(args.probe, "not on the inspection-only allow-list")
    if args.os_type != probe["os_type"]:
        return _refused(args.probe, "probe is a {} command, --os-type says {}".format(
            probe["os_type"], args.os_type))
    path = ""
    if probe["needs_path"]:
        try:
            path = safe_path(args.path, probe["os_type"])
        except ValueError as exc:
            return _refused(args.probe, str(exc))
    command = probe["argv"] + (" {}".format(path) if path else "")

    print(CONFIRMATION_NOTICE.format(command=command, instance_id=args.instance_id,
                                     purpose=probe["purpose"]))
    if probe["needs_path"]:
        print("typical targets: {}".format(", ".join(KNOWN_GUEST_PATHS)))
    if args.confirm != CONFIRM_TOKEN:
        print("")
        print("NOT EXECUTED")
        print("STATUS: FAIL")
        print("NEXT_ACTION: state the notice above to the customer, obtain confirmation for "
              "this one command, then re-run with --confirm {}.".format(CONFIRM_TOKEN))
        return 2

    params = {
        "RegionId": args.region_id,
        "Type": probe["command_type"],
        "Name": "{}-{}".format(SKILL_NAME, args.probe),
        "Description": "inspection-only probe issued by {}".format(SKILL_NAME),
        "CommandContent": command,
        "InstanceId.1": args.instance_id,
        "Timeout": 60,
    }
    try:
        payload = _cli.call_cli(ECS_PRODUCT, "run-command", params=params,
                               session_id=session_id, timeout=WRITE_TIMEOUT_SECONDS,
                               stream=sys.stderr)
    except _cli.CliError as exc:
        _report_failure(exc)
        print("STATUS: DEGRADED" if _agent_unavailable(exc) else "STATUS: FAIL")
        print("NEXT_ACTION: if the agent or a permission is missing, ask the customer to run "
              "`{}` on the source and paste the output.".format(command))
        return 1

    invoke_id = payload.get("InvokeId", "")
    report = Report("Guest probe issued", session_id, uid=_cached_uid(session_id))
    report.section("{}".format(command))
    report.item("instance", args.instance_id)
    report.item("InvokeId", invoke_id)
    if args.wait and invoke_id:
        _poll_invocation(report, args.region_id, invoke_id, session_id)
    else:
        report.action("Read the output with `invocation-result --region-id {} --invoke-id {}`."
                      .format(args.region_id, invoke_id or "<InvokeId>"))
    report.finish()
    return 0 if report.worst == "OK" else 1


def _agent_unavailable(exc):
    text = "{} {}".format(exc.code, exc.message).lower()
    markers = ("clientnotrunning", "clientnotonline", "instancenotfound",
               "not online", "cloud assistant", "agent is not running")
    return any(marker in text for marker in markers)


def _poll_invocation(report, region_id, invoke_id, session_id):
    deadline = time.time() + PROBE_WAIT_TIMEOUT_SECONDS
    while time.time() < deadline:
        payload = _cli.describe(ECS_PRODUCT, "DescribeInvocations",
                               params={"RegionId": region_id, "InvokeId": invoke_id,
                                       "IncludeOutput": "true"},
                               session_id=session_id, timeout=READ_TIMEOUT_SECONDS,
                               stream=sys.stderr)
        for invoked in _invoke_instances(payload):
            state = str(invoked.get("InvocationStatus", "")).lower()
            if state and state not in NONFINAL_INVOCATION_STATES:
                report.item("state", state)
                report.emit(_decode_output(invoked.get("Output") or "") or "(no output)")
                report.action("Compare the bytes in use against the intended target disk size; "
                              "the target must stay above the used space.")
                return
        time.sleep(PROBE_POLL_INTERVAL_SECONDS)
    report.gap("The probe reported no final state within {}s; read it later with "
               "`invocation-result`.".format(PROBE_WAIT_TIMEOUT_SECONDS))


def _invoke_instances(payload):
    invocations = ((payload or {}).get("Invocations") or {}).get("Invocation") or []
    out = []
    for invocation in invocations:
        out.extend(((invocation.get("InvokeInstances") or {}).get("InvokeInstance") or []))
    return out


def cmd_invocation_result(args, session_id):
    params = {"RegionId": args.region_id, "IncludeOutput": "true"}
    if args.invoke_id:
        params["InvokeId"] = args.invoke_id
    if args.instance_id:
        params["InstanceId"] = args.instance_id
    payload = _cli.describe(ECS_PRODUCT, "DescribeInvocations", params=params,
                           session_id=session_id, timeout=READ_TIMEOUT_SECONDS,
                           stream=sys.stderr)
    report = Report("Guest probe results", session_id, uid=_cached_uid(session_id))
    if payload is None:
        report.fail()
        report.action("Re-check the region and InvokeId.")
        report.finish()
        return 1
    invocations = (payload.get("Invocations") or {}).get("Invocation") or []
    if not invocations:
        report.gap("No invocation matched: this account has no such command record in this "
                   "region.")
    for invocation in invocations:
        report.section("InvokeId {}".format(invocation.get("InvokeId", "")))
        report.item("command", invocation.get("CommandName", ""))
        # `invocation` is already one record unwrapped from Invocations.Invocation,
        # so its per-instance rows live under InvokeInstances.InvokeInstance here --
        # read them directly rather than re-applying the payload-level helper.
        instances = (invocation.get("InvokeInstances") or {}).get("InvokeInstance") or []
        for invoked in instances:
            report.emit("  {} [{}]".format(invoked.get("InstanceId", ""),
                                          invoked.get("InvocationStatus", "")))
            for line in _decode_output(invoked.get("Output") or "").splitlines():
                report.emit("    {}".format(line))
    report.action("Use the reading to fix the target disk size; repairs such as freeing space "
                  "are carried out by the customer.")
    report.finish()
    return 0 if report.worst == "OK" else 1


def cmd_protect_snapshot(args, session_id):
    print(SNAPSHOT_NOTICE.format(disk_id=args.disk_id, region_id=args.region_id))
    if args.confirm != CONFIRM_TOKEN:
        print("")
        print("NOT EXECUTED")
        print("STATUS: FAIL")
        print("NEXT_ACTION: state the billing impact, obtain confirmation, then re-run with "
              "--confirm {}.".format(CONFIRM_TOKEN))
        return 2
    params = {
        "RegionId": args.region_id,
        "DiskId": args.disk_id,
        "SnapshotName": args.snapshot_name or "before-migration-{}".format(session_id[:8]),
        "Description": "Snapshot before change, issued by {}".format(SKILL_NAME),
    }
    try:
        payload = _cli.call_cli(ECS_PRODUCT, "create-snapshot", params=params,
                               session_id=session_id, timeout=WRITE_TIMEOUT_SECONDS,
                               stream=sys.stderr)
    except _cli.CliError as exc:
        _report_failure(exc)
        print("STATUS: FAIL")
        print("NEXT_ACTION: resolve the reported cause; deleting or rolling back a snapshot "
              "stays a manual decision.")
        return 1
    report = Report("Snapshot created", session_id, uid=_cached_uid(session_id))
    report.item("SnapshotId", payload.get("SnapshotId", ""))
    report.item("disk", args.disk_id)
    report.action("Wait until the snapshot is completed before the migration window; deletion "
                  "is handled manually.")
    report.finish()
    return 0


def cmd_route(args, session_id):
    report = Report("Symptom routing", session_id, uid="not queried (offline match)")
    text = " ".join(args.text)
    report.item("input", text)
    matches = match_symptom(text)
    for name, guidance in matches:
        report.emit("  [outside this skill] {} -> {}".format(name, guidance))
    hits = match_error(text)
    for entry, matched in hits:
        report.emit("  [matched: {}]".format(", ".join(matched)))
        report.emit("    likely cause : {}".format(entry["cause"]))
        report.emit("    next step    : {}".format(entry["next_step"]))
    if not matches and not hits:
        report.gap("No documented signature matched. Collect the exact console message, the "
                   "tail of the client log, and the instance id before judging anything.")
    report.action("Report only causes whose signature is present; the abbreviation alone is not "
                  "evidence.")
    report.finish()
    return 0


# ---------------------------------------------------------------------------
# Small shared helpers
# ---------------------------------------------------------------------------
def _open_report(title, session_id):
    return Report(title, session_id, uid=_cached_uid(session_id))


def _cached_uid(session_id):
    identity = sts_token.get_caller_identity(session_id=session_id, stream=io.StringIO())
    return sts_token.account_id(identity) or "unknown"


def _split_ids(raw):
    if not raw:
        return []
    return [item for item in re.split(r"[,\s]+", raw.strip()) if item][:MAX_INSTANCE_IDS]


def _decode_output(raw_output):
    if not raw_output:
        return ""
    text = raw_output
    try:
        text = base64.b64decode(raw_output).decode("utf-8", "replace")
    except Exception:
        pass
    return _cli.mask_secrets(text)[:MAX_INVOCATION_OUTPUT_CHARS]


def _refused(requested, reason):
    print("STATUS: FAIL")
    print("REFUSED : '{}' is {}".format(requested, reason))
    print("ALLOWED : {}".format(", ".join(sorted(GUEST_PROBES))))
    print("NEXT_ACTION: choose one allow-listed probe, or tell the customer why the requested "
          "command cannot be issued by this skill and hand the step to a human operator.")
    return 2


def _report_failure(exc):
    code = (exc.code or "").lower()
    if any(marker in code for marker in ("nopermission", "implictdeny", "accessdenied")):
        sys.stderr.write("[WARN] {} - this account lacks an action; grant only the action that "
                         "is missing, see references/ram-policies.md\n".format(exc.code))
    else:
        sys.stderr.write("[WARN] {} - {}\n".format(exc.code, _cli.mask_secrets(exc.message)))


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="assess_migration.py",
        description="Assess migration of an on-premises, other-cloud, or ECS source onto "
                    "Alibaba Cloud ECS, and identify Server Migration Center task errors.",
    )
    sub = parser.add_subparsers(dest="command")

    def add_region(sp):
        sp.add_argument("--region-id", required=True,
                        help="region holding the resource, e.g. cn-hangzhou")

    sub.add_parser("whoami", help="verify the credential and print the account"
                   ).set_defaults(func=cmd_whoami)

    inventory = sub.add_parser("source-inventory",
                               help="cloud-side inventory of the migration source")
    add_region(inventory)
    inventory.add_argument("--instance-id", required=True,
                           help="one instance id, or a comma-separated list")
    inventory.set_defaults(func=cmd_source_inventory)

    assess = sub.add_parser("assess", help="produce a migration verdict")
    add_region(assess)
    assess.add_argument("--instance-id", required=True,
                        help="one instance id, or a comma-separated list")
    assess.add_argument("--shrink", action="store_true",
                        help="a smaller target disk is wanted")
    assess.add_argument("--cross-account", action="store_true",
                        help="source and target belong to different accounts")
    assess.add_argument("--expired-source", action="store_true",
                        help="the source can no longer be logged into")
    assess.set_defaults(func=cmd_assess)

    avail = sub.add_parser("target-availability",
                           help="check whether a target resource is sellable")
    add_region(avail)
    avail.add_argument("--destination-resource", required=True,
                       choices=["Zone", "InstanceType", "SystemDisk", "DataDisk", "Network",
                                "IoOptimized", "DedicatedHost"])
    avail.add_argument("--instance-type")
    avail.add_argument("--zone-id")
    avail.add_argument("--instance-charge-type", choices=["PrePaid", "PostPaid"])
    avail.add_argument("--system-disk-category")
    avail.add_argument("--data-disk-category")
    avail.add_argument("--io-optimized", choices=["optimized", "none"])
    avail.add_argument("--network-category", choices=["vpc", "classic"])
    avail.set_defaults(func=cmd_target_availability)

    probe = sub.add_parser("guest-probe",
                           help="run ONE inspection-only command in the guest")
    add_region(probe)
    probe.add_argument("--instance-id", required=True)
    probe.add_argument("--probe", required=True, choices=sorted(GUEST_PROBES))
    probe.add_argument("--os-type", required=True, choices=["linux", "windows"])
    probe.add_argument("--path", help="required for the probes that take a path")
    probe.add_argument("--confirm", default="",
                       help="pass `yes` only after the customer confirmed this one command")
    probe.add_argument("--wait", action="store_true", help="poll until a final state")
    probe.set_defaults(func=cmd_guest_probe)

    result = sub.add_parser("invocation-result", help="read back a guest probe")
    add_region(result)
    result.add_argument("--invoke-id")
    result.add_argument("--instance-id")
    result.set_defaults(func=cmd_invocation_result)

    snap = sub.add_parser("protect-snapshot", help="create one snapshot before a change")
    add_region(snap)
    snap.add_argument("--disk-id", required=True)
    snap.add_argument("--snapshot-name")
    snap.add_argument("--confirm", default="",
                      help="pass `yes` only after the customer accepted the billing impact")
    snap.set_defaults(func=cmd_protect_snapshot)

    route = sub.add_parser("route", help="match a symptom or error string")
    route.add_argument("text", nargs="+")
    route.set_defaults(func=cmd_route)

    return parser


def _run_selftest() -> int:
    """Offline regression lock over the pure assessment core.

    Every expectation was recorded from the real behaviour of this file before
    it was pinned (probe round R75); nothing here reaches the CLI. The
    invocation-result case pins the fixed bug where a payload-level helper was
    re-applied to an already-unwrapped single Invocation record, silently
    dropping every instance row and its output.
    """
    import contextlib

    checks = {"n": 0, "fail": 0}

    def check(name, got, want):
        checks["n"] += 1
        if got != want:
            checks["fail"] += 1
            print("FAIL %s: got %r want %r" % (name, got, want))
        else:
            print("ok   %s" % name)

    def _capture(fn, *a):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = fn(*a)
        return rc, buf.getvalue()

    def _refused_path(raw, ost):
        try:
            safe_path(raw, ost)
            return False
        except ValueError:
            return True

    # ---- instance_family / NVMe routing ------------------------------------
    check("fam_full", instance_family("ecs.g8i.large"), "g8i")
    check("fam_short2", instance_family("g8i.large"), "")
    check("fam_empty", instance_family(""), "")
    check("fam_none", instance_family(None), "")
    check("fam_four_parts", instance_family("ecs.g8i.x.large"), "g8i")
    nvme = next(iter(sorted(NVME_INSTANCE_FAMILIES)))
    check("fam_nvme_member", "g6" in NVME_INSTANCE_FAMILIES, False)
    check("nvme_gate_on", instance_family("ecs.%s.large" % nvme) in NVME_INSTANCE_FAMILIES, True)

    # ---- os_posture ---------------------------------------------------------
    check("os_centos7", os_posture("CentOS 7.9 64-bit"), "generally supported; validate with a migration drill before cutover")
    check("os_rhel4", os_posture("RHEL 4"), "not supported by SMC whole-server migration")
    # DescribeInstances reports this release as "RedHat N.x" (see the sibling
    # os-eol-guide token list); pinning it keeps that row from going dead again.
    check("os_redhat_real_token",
          os_posture("RedHat 4.8 64 bit"), "not supported by SMC whole-server migration")
    check("os_redhat7_real_token",
          os_posture("RedHat 7.9 64 bit"),
          "generally supported; validate with a migration drill before cutover")
    check("os_win2012", os_posture("Windows Server 2012 R2"), "check the SMC supported-OS list before scheduling")
    check("os_unknown", os_posture("Ubuntu 22.04"), os_posture("zzz"))
    check("os_empty", os_posture(None), os_posture(""))
    check("os_default_wording", "no documented screening posture" in os_posture("Ubuntu 22.04"), True)

    # ---- match_error / match_symptom (data-driven) --------------------------
    e0 = ERROR_SIGNATURES[0]
    hits = match_error("boom " + e0["signatures"][0] + " end")
    check("me_first", any(entry is e0 for entry, _m in hits), True)
    check("me_empty", match_error(""), [])
    check("me_negative", match_error("zzqq nothing xxvv"), [])
    # the customer pastes CLI output in any casing; matching must not depend on it
    check("me_case_insensitive", bool(match_error(e0["signatures"][0].upper())), True)
    s0 = SYMPTOM_ROUTING[0]
    hs = match_symptom("customer says " + s0[1][0])
    check("ms_first", (s0[0], s0[2]) in hs, True)
    check("ms_empty", match_symptom(""), [])

    # ---- local_disk / encrypted --------------------------------------------
    check("ld_local", local_disk({"Category": "local_ssd"}), True)
    check("ld_ephemeral", local_disk({"Category": "ephemeral"}), True)
    check("ld_cloud", local_disk({"Category": "cloud_essd"}), False)
    check("ld_missing", local_disk({}), False)
    check("en_true_bool", encrypted({"Encrypted": True}), True)
    check("en_true_str", encrypted({"Encrypted": "true"}), True)
    check("en_false_str", encrypted({"Encrypted": "false"}), False)
    check("en_missing", encrypted({}), False)

    # ---- _split_ids ---------------------------------------------------------
    check("si_commas", _split_ids("i-1,i-2  i-3"), ["i-1", "i-2", "i-3"])
    check("si_empty", _split_ids(""), [])
    check("si_none", _split_ids(None), [])
    check("si_cap", len(_split_ids(",".join("i-%d" % n for n in range(99)))), MAX_INSTANCE_IDS)

    # ---- _decode_output -----------------------------------------------------
    check("do_b64", _decode_output("aGVsbG8gZGYgb3V0cHV0"), "hello df output")
    check("do_empty", _decode_output(""), "")
    # unparsable base64 is passed through rather than crashing or fabricating
    check("do_bad_b64_passthrough", _decode_output("!!!not base64!!!"), "!!!not base64!!!")
    check("do_capped", len(_decode_output("x" * 5000)) <= MAX_INVOCATION_OUTPUT_CHARS, True)

    # ---- safe_path ------------------------------------------------------------
    check("sp_ok", safe_path("/boot/grub2", "linux"), "/boot/grub2")
    check("sp_win", safe_path("C:\\Windows", "windows"), "C:\\Windows")
    for bad, ost, why in (("/a;rm -rf /", "linux", "metachar"), ("/a|b", "linux", "pipe"),
                          ("$(id)", "linux", "subshell"), ("relative/path", "linux", "shape"),
                          ("Windows\\System32", "windows", "win-nodrive"),
                          ("C:\\a|b", "windows", "win-metachar")):
        try:
            safe_path(bad, ost)
            outcome = "accepted"
        except ValueError:
            outcome = "refused"
        check("sp_refuses[%s]" % why, outcome, "refused")
    # `$` in the shape pattern would accept a trailing newline, so the
    # metacharacter guard is the only thing refusing an injected command chain
    check("sp_trailing_newline", _refused_path("/boot/grub\n", "linux"), True)
    try:
        safe_path("", "linux")
        outcome = "accepted"
    except ValueError:
        outcome = "refused"
    check("sp_empty", outcome, "refused")

    # ---- _invoke_instances (payload-level contract) -------------------------
    full = {"Invocations": {"Invocation": [
        {"InvokeInstances": {"InvokeInstance": [{"InstanceId": "i-a"}, {"InstanceId": "i-b"}]}},
        {"InvokeInstances": {"InvokeInstance": [{"InstanceId": "i-c"}]}}]}}
    check("ii_flattens_all", [r["InstanceId"] for r in _invoke_instances(full)],
          ["i-a", "i-b", "i-c"])
    check("ii_none_payload", _invoke_instances(None), [])
    check("ii_single_record_is_empty_by_contract", _invoke_instances({"InvokeId": "t"}), [])

    # ---- cmd_invocation_result: the fixed regression -------------------------
    real_describe = _cli.describe
    real_uid = globals()["_cached_uid"]
    try:
        globals()["_cached_uid"] = lambda sid: "acct-test"
        payload = {"Invocations": {"Invocation": [{
            "InvokeId": "t-abc", "CommandName": "probe-df",
            "InvokeInstances": {"InvokeInstance": [
                {"InstanceId": "i-xyz", "InvocationStatus": "Finished",
                 "Output": "aGVsbG8gZGYgb3V0cHV0"}]}}]}}
        _cli.describe = lambda *a, **k: payload
        ns = argparse.Namespace(region_id="cn-hangzhou", invoke_id="t-abc", instance_id=None)
        rc, out = _capture(cmd_invocation_result, ns, "sess")
        check("ir_rc", rc, 0)
        check("ir_shows_instance", "i-xyz" in out, True)
        check("ir_shows_status", "Finished" in out, True)
        check("ir_shows_decoded_output", "hello df output" in out, True)
        # multi invocation where one has no InvokeInstances at all
        payload2 = {"Invocations": {"Invocation": [
            {"InvokeId": "t-2", "CommandName": "c",
             "InvokeInstances": {"InvokeInstance": [
                 {"InstanceId": "i-a", "InvocationStatus": "Running", "Output": ""},
                 {"InstanceId": "i-b", "InvocationStatus": "Success", "Output": "b2s="}]}},
            {"InvokeId": "t-3", "CommandName": "c2"}]}}
        _cli.describe = lambda *a, **k: payload2
        rc2, out2 = _capture(cmd_invocation_result,
                             argparse.Namespace(region_id="r", invoke_id=None, instance_id=None),
                             "sess")
        check("ir_multi", all(x in out2 for x in ("i-a", "i-b", "t-3")), True)
        check("ir_decodes_second_output", "ok" in out2, True)
        _cli.describe = lambda *a, **k: {"Invocations": {"Invocation": []}}
        rc3, out3 = _capture(cmd_invocation_result,
                             argparse.Namespace(region_id="r", invoke_id="t-9", instance_id=None),
                             "sess")
        check("ir_no_match_rc", rc3, 1)
        check("ir_no_match_degraded", "STATUS: DEGRADED" in out3, True)
        _cli.describe = lambda *a, **k: None
        rc4, out4 = _capture(cmd_invocation_result,
                             argparse.Namespace(region_id="r", invoke_id="t", instance_id=None),
                             "sess")
        check("ir_api_fail", (rc4, "STATUS: FAIL" in out4), (1, True))
    finally:
        _cli.describe = real_describe
        globals()["_cached_uid"] = real_uid

    # ---- Report status accumulation -------------------------------------
    rep_buf = io.StringIO()
    with contextlib.redirect_stdout(rep_buf):
        rep = Report("t", "s")
        check("rep_init", rep.worst, "OK")
        rep.gap("g")
        check("rep_gap", rep.worst, "DEGRADED")
        rep.gap("g2")
        check("rep_gap_idempotent", rep.gaps, ["g", "g2"])
        rep.fail()
        check("rep_fail", rep.worst, "FAIL")

    print("SELFTEST: %d checks, %d failures" % (checks["n"], checks["fail"]))
    return 0 if checks["fail"] == 0 else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--selftest":
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 2
    return args.func(args, _cli.new_session_id())


if __name__ == "__main__":
    sys.exit(main())
