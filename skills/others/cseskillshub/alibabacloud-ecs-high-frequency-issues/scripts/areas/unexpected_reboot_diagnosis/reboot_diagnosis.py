#!/usr/bin/env python3
"""Entry point for area:unexpected-reboot-diagnosis.

Single entry for every capability of this skill. The agent MUST run this
script and MUST NOT assemble aliyun CLI commands by hand.

Subcommands
    check-auth       Credential preflight (GetCallerIdentity, query class).
    diagnose         Full read-only evidence chain for one instance:
                     instance facts, health status, system events,
                     maintenance attributes, disks, instance type capacity,
                     Cloud Assistant readiness, recent invocations and
                     CloudMonitor readings, followed by verdicts.
    guest-probe      Dispatch EXACTLY ONE whitelisted non-mutating command
                     into the guest (write class, confirmation gate).
    create-snapshot  Snapshot-first guard before cleanup or risky handling
                     (write class, confirmation gate, billing disclosed).
    explain          Interpret guest readings the customer pasted (no cloud
                     access at all).

SECURITY
    * Query calls run without per-call confirmation; the two write-class
      subcommands refuse to act unless the gate inputs are present
      (--user-confirmed plus --approval-quote), so the gate does not depend
      on the agent remembering it.
    * The command string for guest-probe is frozen-whitelist validated after
      assembly; shell composition tokens fail closed.
    * Credentials resolve only through the aliyun CLI default chain; this
      script never accepts, reads, stores or prints an AccessKey pair or a
      security token.
    * Every subprocess call carries an explicit timeout; every call carries
      the run's User-Agent session id (see _cli.py).

Exit codes: 0 = OK or DEGRADED conclusion, 1 = no usable conclusion,
2 = usage error.
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import base64
import json
import re
import sys
import time
from datetime import datetime, timezone

from _cli import CliError, call_cms, call_ecs, call_sts, new_session_id
from _constants import (
    AUTO_GUEST_COMMANDS_LINUX,
    AUTO_GUEST_COMMANDS_WINDOWS,
    AUTO_GUEST_COMMAND_FAMILIES,
    CA_STATUS_ONLINE,
    CMS_METRICS,
    CMS_NAMESPACE_ECS,
    DISK_UTIL_CAP_PCT,
    DOC_LINKS,
    DRIVE_ARG_PATTERN,
    EVENT_ALL_STATUSES,
    EVENT_LIFECYCLE_TYPES,
    EVENT_REBOOT_TYPES,
    EVENT_REDEPLOY_TYPES,
    EPHEMERAL_CATEGORYS,
    FS_FULL_PCT,
    GUEST_COMMAND_TIMEOUT_SECONDS,
    HANDOFF_SKILLS,
    INTERMEDIATE_STATES,
    INVOCATION_POLL_BUDGET_SECONDS,
    INVOCATION_POLL_INTERVAL_SECONDS,
    INVOCATION_TERMINAL_STATUSES,
    LOCAL_DISK_CATEGORY_PREFIX,
    MEM_HIGH_PCT,
    CPU_HIGH_PCT,
    PATH_ARG_PATTERN,
    REFUSED_PATH_FRAGMENTS,
    REFUSED_SHELL_TOKENS,
    RUN_TYPE_LINUX,
    RUN_TYPE_WINDOWS,
    SKILL_NAME,
)

UTC_STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
DISK_ID = re.compile(r"^d-[a-z0-9-]{4,64}$")
INSTANCE_ID = re.compile(r"^i-[a-z0-9-]{4,64}$")
REGION_ID = re.compile(r"^[a-z][a-z0-9-]{2,30}$")


# ---------------------------------------------------------------------------
# Small shared helpers
# ---------------------------------------------------------------------------

def now_utc():
    return datetime.now(timezone.utc)


def parse_utc(stamp):
    if not stamp or not UTC_STAMP.match(stamp):
        return None
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc)


def fetch(store, name, fn, required=False):
    """Run one evidence call; degrade on failure, never abort the chain."""
    try:
        return fn()
    except CliError as err:
        store["errors"].append({
            "step": name,
            "code": err.code,
            "message": str(err)[:300],
            "category": "permission" if err.is_auth_denied else "api",
        })
        print("[WARN] {0} failed: {1}: {2}".format(
            name, err.code, str(err.message)[:200]), file=sys.stderr)
        if required:
            store["required_failed"] = True
        return None


def permission_hint(store):
    lines = []
    for err in store["errors"]:
        if err.get("category") == "permission":
            lines.append(
                "permission gap at step '{0}': the RAM policy of the current "
                "identity is missing the action named there; grant the "
                "minimal fragment in references/ram-policies.md "
                "(reported as NoPermission / ImplicitDeny)".format(
                    err["step"]))
    return lines


# ---------------------------------------------------------------------------
# Evidence fetchers (diagnose)
# ---------------------------------------------------------------------------

def fetch_instance(store, sid, region, instance_id, profile):
    body = fetch(store, "DescribeInstances", lambda: call_ecs(
        "DescribeInstances",
        {"InstanceIds": json.dumps([instance_id]), "PageSize": 10},
        sid, region, profile=profile), required=True)
    insts = []
    if body:
        insts = (body.get("Instances") or {}).get("Instance") or []
    if not insts:
        store["required_failed"] = True
        store["errors"].append({
            "step": "DescribeInstances",
            "code": "InstanceNotFoundOrOutOfRegion",
            "message": ("no instance {0} is visible in region {1} under this "
                        "credential".format(instance_id, region)),
            "category": "parameter",
        })
        return None
    inst = insts[0]
    store["instance"] = {
        "instance_id": inst.get("InstanceId"),
        "name": inst.get("InstanceName"),
        "status": inst.get("Status"),
        "instance_type": inst.get("InstanceType"),
        "os_type": inst.get("OSType"),
        "os_name": inst.get("OSName"),
        "cpu": inst.get("Cpu"),
        "memory_gib": inst.get("Memory"),
        "vpc_id": inst.get("VpcAttributes", {}).get("VpcId"),
        "vswitch_id": inst.get("VpcAttributes", {}).get("VSwitchId"),
        "zone_id": inst.get("ZoneId"),
        "internet_ip": inst.get("PublicIpAddress", {}).get("IpAddress") or [],
        "eip": (inst.get("EipAddress") or {}).get("IpAddress") or None,
        "inner_ips": inst.get("VpcAttributes", {}).get(
            "PrivateIpAddress", {}).get("IpAddress") or [],
        "instance_charge_type": inst.get("InstanceChargeType"),
        "security_group_ids": inst.get("SecurityGroupIds", {}).get(
            "IpAddress") or inst.get("SecurityGroupIds", {}).get(
                "SecurityGroupId") or [],
    }
    return store["instance"]


def fetch_full_status(store, sid, region, instance_id, profile):
    body = fetch(store, "DescribeInstancesFullStatus", lambda: call_ecs(
        "DescribeInstancesFullStatus",
        {"InstanceId.1": instance_id, "PageSize": 10},
        sid, region, profile=profile))
    if not body:
        return
    rows = (body.get("InstanceFullStatusSet") or {}).get(
        "InstanceFullStatusType") or []
    if rows:
        row = rows[0]
        store["health"] = {
            "health_status": (row.get("HealthStatus") or {}).get("Name"),
            "instance_status": (row.get("Status") or {}).get("Name"),
            "scheduled_events": (
                row.get("ScheduledSystemEventSet") or {}).get(
                    "ScheduledSystemEventType") or [],
        }


def fetch_history_events(store, sid, region, instance_id, profile,
                         since, until):
    params = {
        "InstanceId": instance_id,
        "MaxResults": 100,
        "EventPublishTime.Start": since,
        "EventPublishTime.End": until,
    }
    for i, status in enumerate(EVENT_ALL_STATUSES, 1):
        params["InstanceEventCycleStatus.{0}".format(i)] = status
    body = fetch(store, "DescribeInstanceHistoryEvents", lambda: call_ecs(
        "DescribeInstanceHistoryEvents", params, sid, region,
        profile=profile))
    if body is None:
        return
    rows = (body.get("InstanceSystemEventSet") or {}).get(
        "InstanceSystemEventType") or []
    events = []
    for row in rows:
        events.append({
            "event_id": row.get("EventId"),
            "type": (row.get("EventType") or {}).get("Name"),
            "cycle_status": (row.get("EventCycleStatus") or {}).get("Name"),
            "published": row.get("EventPublishTime"),
            "finished": row.get("EventFinishTime"),
            "not_before": row.get("NotBefore"),
            "reason": row.get("Reason"),
        })
    store["events"] = events


def fetch_maintenance(store, sid, region, instance_id, profile):
    body = fetch(store, "DescribeInstanceMaintenanceAttributes", lambda: call_ecs(
        "DescribeInstanceMaintenanceAttributes",
        {"InstanceId.1": instance_id}, sid, region, profile=profile))
    if not body:
        return
    rows = (body.get("MaintenanceAttributes") or {}).get(
        "MaintenanceAttribute") or []
    if rows:
        row = rows[0]
        action = row.get("ActionOnMaintenance") or {}
        store["maintenance"] = {
            "value": action.get("Value"),
            "default": action.get("DefaultValue"),
            "supported": (action.get("SupportedValues") or {}).get(
                "SupportedValue") or [],
            "notify": row.get("NotifyOnMaintenance"),
        }


def fetch_disks(store, sid, region, instance_id, profile):
    body = fetch(store, "DescribeDisks", lambda: call_ecs(
        "DescribeDisks", {"InstanceId": instance_id, "PageSize": 50},
        sid, region, profile=profile))
    if body is None:
        return
    disks = []
    for row in (body.get("Disks") or {}).get("Disk") or []:
        disks.append({
            "disk_id": row.get("DiskId"),
            "type": row.get("Type"),
            "category": row.get("Category"),
            "size_gib": row.get("Size"),
            "device": row.get("Device"),
        })
    store["disks"] = disks


def fetch_instance_type(store, sid, region, type_id, profile):
    if not type_id:
        return
    body = fetch(store, "DescribeInstanceTypes", lambda: call_ecs(
        "DescribeInstanceTypes", {"InstanceTypes.1": type_id},
        sid, region, profile=profile))
    if not body:
        return
    rows = (body.get("InstanceTypes") or {}).get("InstanceType") or []
    if rows:
        row = rows[0]
        store["instance_type"] = {
            "id": row.get("InstanceTypeId"),
            "cpu_cores": row.get("CpuCoreCount"),
            "memory_gib": row.get("MemorySize"),
            "local_storage_category": row.get("LocalStorageCategory"),
            "local_storage_amount": row.get("LocalStorageAmount"),
            "bandwidth_rx_kbit": row.get("InstanceBandwidthRx"),
            "bandwidth_tx_kbit": row.get("InstanceBandwidthTx"),
        }


def fetch_cloud_assistant(store, sid, region, instance_id, profile):
    body = fetch(store, "DescribeCloudAssistantStatus", lambda: call_ecs(
        "DescribeCloudAssistantStatus", {"InstanceId.1": instance_id},
        sid, region, profile=profile))
    if not body:
        return
    rows = (body.get("InstanceCloudAssistantStatusSet") or {}).get(
        "InstanceCloudAssistantStatus") or []
    if rows:
        row = rows[0]
        store["cloud_assistant"] = {
            "installed": row.get("CloudAssistantStatus") == CA_STATUS_ONLINE,
            "version": row.get("CloudAssistantVersion"),
            "os_type": row.get("OSType"),
            "last_heartbeat": row.get("LastHeartbeatTime"),
        }


def fetch_invocations(store, sid, region, instance_id, profile):
    body = fetch(store, "DescribeInvocations", lambda: call_ecs(
        "DescribeInvocations",
        {"InstanceId": instance_id, "PageSize": 10},
        sid, region, profile=profile))
    if body is None:
        return
    rows = (body.get("Invocations") or {}).get("Invocation") or []
    history = []
    for row in rows:
        instances = (row.get("InvokeInstances") or {}).get(
            "InvokeInstance") or []
        status = instances[0].get("InvocationStatus") if instances else None
        history.append({
            "command_name": row.get("CommandName"),
            "command_type": row.get("CommandType"),
            "status": status,
            "fired_time": (instances[0].get("StartTime")
                           if instances else None),
        })
    store["invocation_history"] = history


def fetch_metrics(store, sid, region, instance_id, profile):
    readings = {}
    for metric, meaning, agg in CMS_METRICS:
        def one(metric=metric, agg=agg):
            body = call_cms("DescribeMetricLast", {
                "Namespace": CMS_NAMESPACE_ECS,
                "MetricName": metric,
                "Dimensions": json.dumps([{"instanceId": instance_id}]),
                "Period": 300,
            }, sid, region, profile=profile)
            points = body.get("Datapoints") or []
            if isinstance(points, str):
                points = json.loads(points) if points.strip() else []
            points = [p for p in points if isinstance(p, dict)]
            if not points:
                return None
            latest = max(points, key=lambda p: p.get("timestamp") or 0)
            return {
                "value": latest.get(agg, latest.get("Average")),
                "timestamp_utc": datetime.fromtimestamp(
                    (latest.get("timestamp") or 0) / 1000.0,
                    tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        readings[metric] = {
            "meaning": meaning,
            "result": fetch(store, "DescribeMetricLast:" + metric, one),
        }
    store["metrics"] = readings


# ---------------------------------------------------------------------------
# Verdict engine (pure function over the collected evidence)
# ---------------------------------------------------------------------------

def metric_value(store, name):
    entry = (store.get("metrics") or {}).get(name) or {}
    result = entry.get("result")
    if not isinstance(result, dict):
        return None
    value = result.get("value")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classify(store):
    """Return verdict dicts ordered by precedence (A, F, C, B, D, E, H)."""
    verdicts = []
    events = store.get("events") or []
    status = (store.get("instance") or {}).get("status")
    health = (store.get("health") or {}).get("health_status")
    mem = metric_value(store, "memory_usedutilization")
    cpu = metric_value(store, "CPUUtilization")
    load = metric_value(store, "load_1m")
    iops_util = metric_value(store, "DiskReadWriteIOPSUtilization")
    bps_util = metric_value(store, "DiskReadWriteBPSUtilization")
    vcpu = (store.get("instance") or {}).get("cpu") or 0

    reboot_events = [e for e in events if e.get("type") in EVENT_REBOOT_TYPES]
    redeploy_events = [e for e in events if e.get("type") in EVENT_REDEPLOY_TYPES]
    lifecycle_events = [e for e in events
                        if e.get("type") in EVENT_LIFECYCLE_TYPES]
    planned_reboot = [e for e in reboot_events
                      if e.get("type") == "SystemMaintenance.Reboot"]
    crash_reboot = [e for e in reboot_events
                    if e.get("type") in
                    ("InstanceFailure.Reboot", "SystemFailure.Reboot")]
    local_disk = has_local_disk(store)

    if crash_reboot or (reboot_events and not planned_reboot):
        seen_crash = bool(crash_reboot)
        verdicts.append({
            "code": "A_os_crash_event",
            "confidence": "high" if seen_crash else "medium",
            "evidence": ["{0} {1} published {2}".format(
                e.get("event_id"), e.get("type"), e.get("published"))
                for e in reboot_events[:10]],
            "note": ("the platform detected an inside-guest fault "
                     "(OOM, blue screen, hang, kernel panic or serial-log "
                     "storm) and issued a protective reboot; this is a "
                     "symptom record, not the root cause itself"),
        })
    if redeploy_events:
        verdicts.append({
            "code": "F_hardware_redeploy",
            "confidence": "high",
            "evidence": ["{0} {1} status {2} not_before {3}".format(
                e.get("event_id"), e.get("type"), e.get("cycle_status"),
                e.get("not_before")) for e in redeploy_events[:10]],
            "note": ("a hardware-risk or maintenance redeployment event "
                     "exists; if local disks are attached their contents "
                     "will be wiped by the redeploy"),
        })
    caps = []
    if iops_util is not None and iops_util >= DISK_UTIL_CAP_PCT:
        caps.append("DiskReadWriteIOPSUtilization={0}%".format(iops_util))
    if bps_util is not None and bps_util >= DISK_UTIL_CAP_PCT:
        caps.append("DiskReadWriteBPSUtilization={0}%".format(bps_util))
    if caps:
        verdicts.append({
            "code": "C_storage_perf_ceiling",
            "confidence": "medium",
            "evidence": caps,
            "note": ("storage throughput or IOPS is at the instance-spec "
                     "ceiling; that is NOT the same as the disk being full "
                     "or memory being short - verify capacity inside the "
                     "guest with df -h / df -i"),
        })
    exhaustion = []
    if mem is not None and mem >= MEM_HIGH_PCT:
        exhaustion.append("memory_usedutilization={0}%".format(mem))
    if cpu is not None and cpu >= CPU_HIGH_PCT:
        exhaustion.append("CPUUtilization={0}%".format(cpu))
    if load is not None and vcpu and load >= 2 * float(vcpu):
        exhaustion.append("load_1m={0} against {1} vCPU".format(load, vcpu))
    if exhaustion and not crash_reboot:
        verdicts.append({
            "code": "B_resource_exhaustion",
            "confidence": "medium" if mem is not None else "low",
            "evidence": exhaustion,
            "note": ("resource exhaustion pattern; process-level attribution "
                     "needs atop or journal history inside the guest "
                     "(manual, see references/unexpected-reboot-diagnosis__guest-inspection-whitelist.md)"),
        })
    elif exhaustion:
        store["metrics_context"] = exhaustion
    if status in INTERMEDIATE_STATES:
        verdicts.append({
            "code": "D_power_transition_handoff",
            "confidence": "high",
            "evidence": ["instance Status={0}".format(status)],
            "note": ("the instance sits in a start/stop transition, not a "
                     "crash; hand off to {0}".format(
                         HANDOFF_SKILLS["instance_state"])),
        })
    if lifecycle_events or planned_reboot:
        verdicts.append({
            "code": "E_planned_or_login",
            "confidence": "high",
            "evidence": ["{0} {1} status {2}".format(
                e.get("event_id"), e.get("type"), e.get("cycle_status"))
                for e in (lifecycle_events + planned_reboot)[:10]],
            "note": ("planned lifecycle or maintenance activity explains the "
                     "reboot narrative; this is not a fault"),
        })
    if status == "Running" and health in (None, "Ok") and not reboot_events:
        ca = store.get("cloud_assistant") or {}
        fresh = ca.get("last_heartbeat")
        alive = ca.get("installed")
        verdicts.append({
            "code": "H_os_alive_app_layer",
            "confidence": "medium" if alive else "low",
            "evidence": ["Status=Running", "health={0}".format(health),
                         "cloud_assistant_online={0}".format(alive),
                         "last_heartbeat={0}".format(fresh)],
            "note": ("the instance itself is alive; check the application, "
                     "the login path and the security group before calling "
                     "it a crash"),
        })
    return verdicts


def has_local_disk(store):
    type_info = store.get("instance_type") or {}
    category = (type_info.get("local_storage_category") or "").lower()
    amount = type_info.get("local_storage_amount") or 0
    if category.startswith(LOCAL_DISK_CATEGORY_PREFIX) or \
            category in EPHEMERAL_CATEGORYS or (amount or 0) > 0:
        return True
    for disk in store.get("disks") or []:
        disk_category = (disk.get("category") or "").lower()
        if disk_category.startswith(LOCAL_DISK_CATEGORY_PREFIX) or \
                disk_category in EPHEMERAL_CATEGORYS:
            return True
    return False


def recoverability(store):
    local = has_local_disk(store)
    cloud = [d for d in store.get("disks") or []
             if not ((d.get("category") or "").lower().startswith(
                 LOCAL_DISK_CATEGORY_PREFIX))]
    lines = [
        "cloud disks visible: {0}; local disks: {1}".format(
            len(cloud), "yes" if local and not cloud else
            sum(1 for d in store.get("disks") or [] if d not in cloud)),
    ]
    if local:
        lines.append(
            "this instance carries local disks: they cannot be snapshotted; "
            "back up inside the guest (copy to a cloud disk, another "
            "instance on the same vSwitch {0}, or object storage) before "
            "any redeploy or risky handling".format(
                (store.get("instance") or {}).get("vswitch_id")))
    lines.append(
        "snapshot coverage is NOT queried here (no snapshot API is in this "
        "skill's verified surface); check the automatic snapshot policy in "
        "the console before trusting recoverability")
    return lines


# ---------------------------------------------------------------------------
# Guest command validation (whitelist, fail closed)
# ---------------------------------------------------------------------------

def validate_guest_command(raw, os_type):
    """Return the exact command string or raise ValueError with the reason."""
    command = (raw or "").strip()
    if not command:
        raise ValueError("empty command")
    for token in REFUSED_SHELL_TOKENS:
        if token in command:
            raise ValueError(
                "shell composition or quoting token {0!r} is refused; one "
                "plain command per call".format(token))
    lowered = command.lower()
    for fragment in REFUSED_PATH_FRAGMENTS:
        if fragment in lowered:
            raise ValueError(
                "path fragment {0!r} is off the auto-execution whitelist "
                "for this tier; run it manually and paste the output "
                "instead".format(fragment))
    exact = AUTO_GUEST_COMMANDS_LINUX if os_type == "linux" \
        else AUTO_GUEST_COMMANDS_WINDOWS
    if command in exact:
        return command
    for family, spec in AUTO_GUEST_COMMAND_FAMILIES.items():
        if spec["os"] != os_type:
            continue
        prefix = spec["prefix"]
        if command == family and spec["arg_kind"]:
            raise ValueError(
                "{0} requires its target argument".format(prefix))
        if command.startswith(prefix + " "):
            argument = command[len(prefix) + 1:].strip()
            if spec["arg_kind"] == "path":
                if not re.match(PATH_ARG_PATTERN, argument):
                    raise ValueError(
                        "argument must be a single plain absolute path")
            elif spec["arg_kind"] == "drive":
                if not re.match(DRIVE_ARG_PATTERN, argument):
                    raise ValueError("argument must be a drive letter")
            else:
                raise ValueError("unsupported argument kind")
            return "{0} {1}".format(prefix, argument)
    raise ValueError(
        "command is not on the frozen whitelist for this tier; see "
        "references/unexpected-reboot-diagnosis__guest-inspection-whitelist.md for the approved set and "
        "the manual path for everything else")


def snapshot_gate_inputs(args):
    problems = []
    if not args.user_confirmed:
        problems.append(
            "the customer has not been asked for and given an explicit "
            "confirmation (pass --user-confirmed only after that)")
    quote = (args.approval_quote or "").strip()
    if len(quote) < 4:
        problems.append(
            "--approval-quote must carry the verbatim affirmative answer")
    return problems


# ---------------------------------------------------------------------------
# Subcommand: diagnose
# ---------------------------------------------------------------------------

def run_diagnose(args):
    sid = new_session_id()
    store = {"errors": [], "required_failed": False}

    if not REGION_ID.match(args.region_id):
        print("STATUS: FAIL")
        print("NEXT_ACTION: restate --region-id (e.g. cn-hangzhou)")
        return 1
    if not INSTANCE_ID.match(args.instance_id):
        print("STATUS: FAIL")
        print("NEXT_ACTION: restate --instance-id (i-...)")
        return 1
    for flag, value in (("--event-since", args.event_since),
                        ("--event-until", args.event_until)):
        if value and not UTC_STAMP.match(value):
            print("STATUS: FAIL")
            print("NEXT_ACTION: {0} must be UTC ISO format "
                  "YYYY-MM-DDTHH:MM:SSZ".format(flag))
            return 1

    identity = fetch(store, "GetCallerIdentity",
                     lambda: call_sts(sid, profile=args.profile))
    account_id = (identity or {}).get("AccountId", "")

    inst = fetch_instance(store, sid, args.region_id, args.instance_id,
                          args.profile)
    if inst:
        fetch_full_status(store, sid, args.region_id, args.instance_id,
                          args.profile)
        fetch_history_events(store, sid, args.region_id, args.instance_id,
                             args.profile, args.event_since, args.event_until)
        fetch_maintenance(store, sid, args.region_id, args.instance_id,
                          args.profile)
        fetch_disks(store, sid, args.region_id, args.instance_id,
                    args.profile)
        fetch_instance_type(store, sid, args.region_id,
                            inst.get("instance_type"), args.profile)
        fetch_cloud_assistant(store, sid, args.region_id, args.instance_id,
                              args.profile)
        fetch_invocations(store, sid, args.region_id, args.instance_id,
                          args.profile)
        fetch_metrics(store, sid, args.region_id, args.instance_id,
                      args.profile)

    verdicts = classify(store) if inst else []
    store["verdicts"] = verdicts
    next_actions = suggest_next_actions(store)

    if store["required_failed"]:
        status = "FAIL"
        next_line = ("confirm region and instance id with the customer; "
                     "nothing was concluded")
        code = 1
    else:
        status = "DEGRADED" if store["errors"] else "OK"
        next_line = next_actions[0] if next_actions else "present the report"
        code = 0

    if args.json:
        payload = {
            "skill": SKILL_NAME,
            "session_id": sid,
            "account_id": account_id,
            "region_id": args.region_id,
            "instance": store.get("instance"),
            "health": store.get("health"),
            "events": store.get("events"),
            "maintenance": store.get("maintenance"),
            "disks": store.get("disks"),
            "instance_type": store.get("instance_type"),
            "cloud_assistant": store.get("cloud_assistant"),
            "invocation_history": store.get("invocation_history"),
            "metrics": store.get("metrics"),
            "verdicts": verdicts,
            "recoverability": recoverability(store) if inst else [],
            "auto_filled": auto_filled_notes(args),
            "errors": store["errors"],
            "next_actions": next_actions,
            "status": status,
            "next_action": next_line,
        }
        # Pure JSON on stdout; contract lines go to stderr so machine
        # parsing stays valid.
        print("STATUS: {0}".format(status), file=sys.stderr)
        print("NEXT_ACTION: {0}".format(next_line), file=sys.stderr)
        print(json.dumps(payload, indent=2, ensure_ascii=False,
                         default=str))
    else:
        render_report(sid, account_id, args, store, verdicts, next_actions)
        print("STATUS: {0}".format(status))
        print("NEXT_ACTION: " + next_line)
    return code


def auto_filled_notes(args):
    notes = ["event window defaulted to the whole queryable history "
             "(no --event-since/--event-until given)"
             if not (args.event_since or args.event_until) else
             "event window filtered to {0} .. {1}".format(
                 args.event_since or "beginning",
                 args.event_until or "now")]
    notes.append("metric period auto-filled to 300s")
    notes.append("UID label auto-derived via sts get-caller-identity")
    return notes


def suggest_next_actions(store):
    actions = []
    codes = {v["code"] for v in store.get("verdicts") or []}
    events = store.get("events") or []
    if any(e.get("type") in EVENT_REBOOT_TYPES for e in events):
        actions.append(
            "confirm the incident time window with the customer, then "
            "cross-check it against the event publish times")
    if "A_os_crash_event" in codes or "B_resource_exhaustion" in codes:
        actions.append(
            "offer guest-probe df -h / df -i (one command, per-call "
            "confirmation) to rule capacity in or out")
        actions.append(
            "recommend deploying atop and enabling kernel crash dump for "
            "the next occurrence (manual steps in "
            "references/unexpected-reboot-diagnosis__diagnosis-playbook.md)")
    if "C_storage_perf_ceiling" in codes:
        actions.append(
            "explain the spec ceiling versus capacity-full confusion, then "
            "hand sustained IO performance questions to " +
            HANDOFF_SKILLS["disk_io"])
    if "F_hardware_redeploy" in codes:
        actions.append(
            "before any redeploy window: back up local-disk data manually; "
            "redeploy and migration are human actions, never automated here")
    if "D_power_transition_handoff" in codes:
        actions.append("hand off to " + HANDOFF_SKILLS["instance_state"])
    if "H_os_alive_app_layer" in codes:
        actions.append(
            "run the app-layer triad (can the OS be logged into, do ports "
            "listen, are the security group rules correct) before treating "
            "this as an instance crash")
    if store.get("errors"):
        for line in permission_hint(store)[:3]:
            actions.append(line)
    return actions


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def section(title):
    print("\n== {0} ==".format(title))


def render_report(sid, account_id, args, store, verdicts, next_actions):
    print("ECS unexpected reboot diagnosis")
    print("skill: {0}".format(SKILL_NAME))
    print("session_id: {0}".format(sid))
    print("account_id: {0}".format(account_id or "(unresolved)"))
    print("region: {0}   instance: {1}".format(args.region_id,
                                               args.instance_id))

    section("Instance facts")
    inst = store.get("instance")
    if inst:
        for key in ("instance_id", "name", "status", "instance_type",
                    "os_type", "cpu", "memory_gib", "zone_id", "vpc_id",
                    "vswitch_id", "instance_charge_type"):
            print("{0}: {1}".format(key, inst.get(key)))
        print("public_ips: {0}".format(
            inst.get("internet_ip") or "none" ))
        print("eip: {0}".format(inst.get("eip") or "none"))
        print("private_ips: {0}".format(inst.get("inner_ips")))
    else:
        print("(instance not visible)")

    section("Health and power state")
    health = store.get("health")
    if health:
        print("health_status: {0}".format(health.get("health_status")))
        print("instance_status(api): {0}".format(
            health.get("instance_status")))
        if health.get("scheduled_events"):
            for event in health["scheduled_events"][:10]:
                print("scheduled: {0} not_before {1} status {2}".format(
                    (event.get("EventType") or {}).get("Name"),
                    event.get("NotBefore"),
                    (event.get("EventCycleStatus") or {}).get("Name")))
    else:
        print("(unavailable)")

    section("System events")
    events = store.get("events")
    if events is None:
        print("(query failed, see degradation log)")
    elif not events:
        print("no instance system events in the query window")
        print("meaning: an in-guest crash WITHOUT a recorded event points "
              "to resource exhaustion or an app-level fault, not to a "
              "platform-detected reboot")
    else:
        for event in events[:20]:
            print("{published} {type} [{cycle_status}] id={event_id} "
                  "not_before={not_before} reason={reason}".format(**event))

    section("Maintenance attributes (recovery behaviour after a crash)")
    maint = store.get("maintenance")
    if maint:
        print("ActionOnMaintenance: {0} (default {1}, supported {2})".format(
            maint.get("value"), maint.get("default"),
            ", ".join(maint.get("supported") or [])))
        print("NotifyOnMaintenance: {0}".format(maint.get("notify")))
    else:
        print("(unavailable)")

    section("Instance type capacity")
    type_info = store.get("instance_type")
    if type_info:
        print("type: {0}   vCPU: {1}   memory GiB: {2}".format(
            type_info.get("id"), type_info.get("cpu_cores"),
            type_info.get("memory_gib")))
        print("local storage: category={0!r} amount={1}".format(
            type_info.get("local_storage_category"),
            type_info.get("local_storage_amount")))
        print("instance bandwidth Kbit/s: rx={0} tx={1}".format(
            type_info.get("bandwidth_rx_kbit"),
            type_info.get("bandwidth_tx_kbit")))
    else:
        print("(unavailable)")

    section("Disks")
    disks = store.get("disks")
    if disks is None:
        print("(query failed, see degradation log)")
    else:
        for disk in disks:
            print("{disk_id} type={type} category={category} "
                  "size_gib={size_gib} device={device}".format(**disk))
        for line in recoverability(store):
            print("note: " + line)

    section("Cloud Assistant readiness (guest evidence channel)")
    ca = store.get("cloud_assistant")
    if ca:
        print("installed: {0}   version: {1}   os: {2}   heartbeat: "
              "{3}".format(ca.get("installed"), ca.get("version"),
                           ca.get("os_type"), ca.get("last_heartbeat")))
        if not ca.get("installed"):
            print("consequence: guest-probe is unavailable; degraded to "
                  "manual readings (customer runs the whitelisted command "
                  "and pastes the output)")
    else:
        print("(query failed, see degradation log)")

    section("Recent Cloud Assistant invocations (history)")
    history = store.get("invocation_history")
    if history is None:
        print("(query failed)")
    elif not history:
        print("no invocation history for this instance")
    else:
        for row in history[:10]:
            print("{command_name} type={command_type} status={status} "
                  "fired={fired_time}".format(**row))

    section("CloudMonitor latest readings")
    print("note: DescribeMetricLast returns only the LATEST datapoint per "
          "metric; for the incident's past time window open the console "
          "monitoring charts (this limitation is deliberate: the skill "
          "does not assume a historical query API that was not verified)")
    metrics = store.get("metrics") or {}
    for metric, meaning, _agg in CMS_METRICS:
        entry = metrics.get(metric) or {}
        result = entry.get("result")
        if isinstance(result, dict):
            print("{0} ({1}): {2} at {3}".format(
                metric, meaning, result.get("value"),
                result.get("timestamp_utc")))
        else:
            print("{0} ({1}): no datapoint returned".format(metric, meaning))

    section("Verdicts (code / confidence / evidence)")
    if not verdicts:
        print("(no branch matched; ask the customer to restate the exact "
              "symptom and time window)")
    for verdict in verdicts:
        print("- {code} [{confidence}]".format(**verdict))
        for evidence in verdict.get("evidence") or []:
            print("    * {0}".format(evidence))
        if verdict.get("note"):
            print("    note: {0}".format(verdict["note"]))

    if store.get("metrics_context"):
        print("exhaustion readings kept as context: " +
              ", ".join(store["metrics_context"]))

    section("Diagnosability readiness for the next occurrence")
    print("- kernel crash dump (Linux kdump): enable manually so a future "
          "in-guest crash leaves a vmcore: " +
          DOC_LINKS["kernel-crash-dump"])
    print("- atop: deploy manually to keep process-level history "
          "(replay is a manual step in this tier): " + DOC_LINKS["atop"])
    print("- service keepalive after reboots (optional): " +
          DOC_LINKS["service-keepalive"])
    print("- maintenance attributes and notification switch: " +
          DOC_LINKS["maintenance-attrs-console"])

    section("Auto-filled inputs (declared)")
    for note in auto_filled_notes(args):
        print("- " + note)

    section("Graceful degradation log")
    if not store["errors"]:
        print("- none")
    for err in store["errors"]:
        print("- step={step} category={category} code={code} message="
              "{message}".format(**err))

    section("Suggested next actions")
    if not next_actions:
        print("- present the report; await the customer's incident window")
    for action in next_actions:
        print("- " + action)


# ---------------------------------------------------------------------------
# Subcommand: guest-probe (gated)
# ---------------------------------------------------------------------------

def run_guest_probe(args):
    sid = new_session_id()
    store = {"errors": [], "required_failed": False}

    problems = snapshot_gate_inputs(args)
    if not INSTANCE_ID.match(args.instance_id):
        problems.append("--instance-id must be an i-... identifier")
    if problems:
        for problem in problems:
            print("[GATE] " + problem, file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: disclose the exact command, its single target, "
              "its non-mutating nature and reversibility, get an explicit "
              "yes, then rerun with the gate inputs")
        return 1

    ca = fetch(store, "DescribeCloudAssistantStatus", lambda: call_ecs(
        "DescribeCloudAssistantStatus",
        {"InstanceId.1": args.instance_id}, sid, args.region_id,
        profile=args.profile))
    os_type = None
    installed = False
    if ca:
        rows = (ca.get("InstanceCloudAssistantStatusSet") or {}).get(
            "InstanceCloudAssistantStatus") or []
        if rows:
            os_type = (rows[0].get("OSType") or "").lower() or None
            installed = rows[0].get("CloudAssistantStatus") == CA_STATUS_ONLINE
    if args.os_type:
        os_type = args.os_type.lower()
    if not os_type:
        print("[WARN] OS family undetermined; pass --os-type linux|windows")
        print("STATUS: DEGRADED")
        print("NEXT_ACTION: ask the customer for the OS family")
        return 0 if not store.get("required_failed") else 1
    if not installed:
        print("[WARN] Cloud Assistant agent is not reporting online; the "
              "guest channel is unavailable")
        print("STATUS: DEGRADED")
        print("NEXT_ACTION: have the customer run the whitelisted command "
              "inside the instance (console session or SSH) and paste the "
              "output back into scripts/areas/unexpected_reboot_diagnosis/reboot_diagnosis.py explain")
        return 0

    try:
        command = validate_guest_command(args.command, os_type)
    except ValueError as bad:
        print("[GATE] refused: {0}".format(bad))
        print("STATUS: FAIL")
        print("NEXT_ACTION: pick a command from "
              "references/unexpected-reboot-diagnosis__guest-inspection-whitelist.md or guide the "
              "customer to run it manually")
        return 1

    print("dispatching exactly one whitelisted non-mutating command: "
          "{0!r} (approval recorded as the operator's quote, this "
          "acknowledgement covers THIS call only)".format(command))
    run_type = RUN_TYPE_LINUX if os_type == "linux" else RUN_TYPE_WINDOWS
    body = fetch(store, "RunCommand", lambda: call_ecs(
        "RunCommand", {
            "Type": run_type,
            "CommandContent": command,
            "Name": "{0}-probe".format(SKILL_NAME)[:128],
            "Description": "single whitelisted inspection command",
            "Timeout": GUEST_COMMAND_TIMEOUT_SECONDS,
            "InstanceId.1": args.instance_id,
        }, sid, args.region_id, write=True, profile=args.profile))
    if not body or not body.get("InvokeId"):
        print("STATUS: DEGRADED")
        print("NEXT_ACTION: the dispatch failed (see degradation log); "
              "fall back to manual customer readings via explain")
        render_errors(store)
        return 0

    invoke_id = body["InvokeId"]
    print("invoke_id: {0}".format(invoke_id))
    deadline = time.monotonic() + INVOCATION_POLL_BUDGET_SECONDS
    output = None
    status = None
    exit_code = None
    while time.monotonic() < deadline:
        time.sleep(INVOCATION_POLL_INTERVAL_SECONDS)
        poll = fetch(store, "DescribeInvocations", lambda: call_ecs(
            "DescribeInvocations", {
                "InvokeId": invoke_id,
                "InstanceId": args.instance_id,
                "IncludeOutput": True,
            }, sid, args.region_id, profile=args.profile))
        if not poll:
            continue
        rows = (poll.get("Invocations") or {}).get("Invocation") or []
        instances = (rows[0].get("InvokeInstances") or {}).get(
            "InvokeInstance") or [] if rows else []
        if not instances:
            continue
        status = instances[0].get("InvocationStatus")
        exit_code = instances[0].get("ExitCode")
        if status in INVOCATION_TERMINAL_STATUSES:
            encoded = instances[0].get("Output") or ""
            try:
                output = base64.b64decode(encoded).decode(
                    "utf-8", errors="replace")
            except (ValueError, TypeError):
                output = None
            break

    print("invocation_status: {0}   exit_code: {1}".format(status, exit_code))
    if output:
        print("---- guest output (verbatim, non-mutating command) ----")
        print(output.rstrip())
        print("---- end output ----")
        print("STATUS: OK")
        print("NEXT_ACTION: interpret capacity or handle findings against "
              "the event timeline, then continue the report")
        return 0
    print("STATUS: DEGRADED")
    print("NEXT_ACTION: no output within the polling budget; ask the "
          "customer to run the command and paste it into explain")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: create-snapshot (gated)
# ---------------------------------------------------------------------------

def run_create_snapshot(args):
    sid = new_session_id()
    store = {"errors": []}

    problems = snapshot_gate_inputs(args)
    if not DISK_ID.match(args.disk_id):
        problems.append("--disk-id must be a d-... identifier")
    if args.retention_days is not None and not (
            1 <= args.retention_days <= 65536):
        problems.append("--retention-days must be within 1..65536")
    if problems:
        for problem in problems:
            print("[GATE] " + problem, file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: disclose that snapshots bill by stored "
              "capacity, agree retention, obtain explicit confirmation, "
              "then rerun")
        return 1

    check = fetch(store, "DescribeDisks", lambda: call_ecs(
        "DescribeDisks", {"DiskIds": json.dumps([args.disk_id])},
        sid, args.region_id, profile=args.profile))
    disks = ((check or {}).get("Disks") or {}).get("Disk") or []
    if not disks:
        print("STATUS: FAIL")
        print("NEXT_ACTION: verify the disk id and region; nothing was "
              "created")
        render_errors(store)
        return 1
    category = (disks[0].get("Category") or "").lower()
    if category.startswith(LOCAL_DISK_CATEGORY_PREFIX) or \
            category in EPHEMERAL_CATEGORYS:
        print("[GATE] disk {0} is a local disk (category {1}); local disks "
              "cannot be snapshotted. Back the data up inside the guest "
              "instead (cloud disk, another instance on the same vSwitch, "
              "or object storage).".format(args.disk_id, category))
        print("STATUS: FAIL")
        print("NEXT_ACTION: guide the customer through the local-disk "
              "backup path; do not attempt CreateSnapshot")
        return 1

    print("creating ONE snapshot of {0} (reversible: the snapshot adds a "
          "copy and alters no existing data; it bills by stored capacity; "
          "delete it after the change is verified - deletion is a human "
          "decision)".format(args.disk_id))
    params = {
        "DiskId": args.disk_id,
        "SnapshotName": "{0}-guard".format(SKILL_NAME)[:50],
        "Description": "snapshot-first guard before customer-handled "
                       "cleanup or risky operations",
        "RetentionDays": args.retention_days,
    }
    body = fetch(store, "CreateSnapshot", lambda: call_ecs(
        "CreateSnapshot", params, sid, args.region_id, write=True,
        profile=args.profile))
    if body and body.get("SnapshotId"):
        print("snapshot_id: {0}".format(body["SnapshotId"]))
        print("STATUS: OK")
        print("NEXT_ACTION: wait for the snapshot to reach accomplished in "
              "the console before any cleanup guidance proceeds; the "
              "cleanup itself is a human action")
        return 0
    print("STATUS: DEGRADED")
    print("NEXT_ACTION: the snapshot call did not succeed (quota, "
          "permissions or disk state); have the customer create the "
          "snapshot in the console before continuing")
    render_errors(store)
    return 0


def render_errors(store):
    for err in store.get("errors") or []:
        print("[WARN] step={step} code={code} message={message}".format(
            **err), file=sys.stderr)
        if err.get("category") == "permission":
            print("reported as NoPermission / ImplicitDeny; minimal "
                  "fragments: references/ram-policies.md", file=sys.stderr)


# ---------------------------------------------------------------------------
# Subcommand: explain (offline reading interpretation, no cloud access)
# ---------------------------------------------------------------------------

USAGE_PCT = re.compile(r"(\d{1,3})%")


def run_explain(args):
    sid = new_session_id()
    if args.paste == "-":
        text = sys.stdin.read()
    else:
        try:
            with open(args.paste, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as err:
            print("[WARN] cannot read {0}: {1}".format(args.paste, err),
                  file=sys.stderr)
            print("STATUS: FAIL")
            print("NEXT_ACTION: pass the pasted readings via --paste - "
                  "(stdin) or a readable file")
            return 1
    findings = []

    for line in text.splitlines():
        parts = line.split()
        lowered = line.lower()
        if "%IUse" in line or ("Filesystem" in line and "Mounted" in line):
            continue  # df / df -i header row, informational
        if len(parts) >= 6 and (parts[-1].startswith("/") or
                                parts[0].startswith("/dev")):
            for match in USAGE_PCT.finditer(line):
                pct = int(match.group(1))
                if pct >= FS_FULL_PCT:
                    findings.append(
                        "capacity pressure: {0!r} at {1}% (df line)"
                        .format(line.strip(), pct))
                    break
        if "(deleted)" in lowered and len(parts) >= 9:
            findings.append(
                "deleted-but-open handles present (lsof +L1 output): space "
                "is held by processes with the file unlinked; a restart of "
                "the holding service frees it - service restart is a human "
                "action")
        if "insufficient" in lowered or "cannot allocate" in lowered or \
                "no space left" in lowered:
            findings.append(
                "guest error text indicates allocation failure: {0!r}"
                .format(line.strip()[:160]))
        if "oom" in lowered or "killed process" in lowered:
            findings.append(
                "guest error text indicates OOM involvement: {0!r}"
                .format(line.strip()[:160]))

    findings = list(dict.fromkeys(findings))

    print("session_id: {0}".format(sid))
    print("mode: explain (offline; no cloud calls were made)")
    if findings:
        print("findings from the pasted readings:")
        for finding in findings:
            print("- " + finding)
    else:
        print("no threshold-crossing or error pattern found in the pasted "
              "text; check that the pasting includes the df -h / df -i / "
              "lsof +L1 table bodies")
    print("STATUS: OK" if findings or "df" in text.lower() else
          "STATUS: DEGRADED")
    print("NEXT_ACTION: fold these findings into the diagnose report as "
          "guest-side evidence; never retype guest numbers as API values")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: check-auth
# ---------------------------------------------------------------------------

def run_check_auth(args):
    sid = new_session_id()
    try:
        body = call_sts(sid, profile=args.profile)
    except CliError as err:
        print("[WARN] identity check failed: {0}".format(err),
              file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: fix the CLI default credential chain via "
              "aliyun sts get-caller-identity in the operator's own session; never "
              "collect keys in chat")
        return 1
    print("session_id: {0}".format(sid))
    print("account_id: {0}".format(body.get("AccountId", "")))
    print("identity: {0}".format(body.get("Arn", "")))
    print("STATUS: OK")
    print("NEXT_ACTION: run diagnose --region-id <region> --instance-id "
          "<id>")
    return 0


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="reboot_diagnosis.py",
        description="Locate why an ECS instance rebooted or appeared "
                    "crashed; evidence-based, gated writes.")
    sub = parser.add_subparsers(dest="mode", required=True)

    p_auth = sub.add_parser("check-auth", help="credential preflight")
    p_auth.add_argument("--profile")
    p_auth.set_defaults(func=run_check_auth)

    p_diag = sub.add_parser("diagnose", help="full read-only evidence chain")
    p_diag.add_argument("--region-id", required=True)
    p_diag.add_argument("--instance-id", required=True)
    p_diag.add_argument("--event-since", default=None,
                        help="UTC YYYY-MM-DDTHH:MM:SSZ incident window start")
    p_diag.add_argument("--event-until", default=None,
                        help="UTC YYYY-MM-DDTHH:MM:SSZ incident window end")
    p_diag.add_argument("--profile")
    p_diag.add_argument("--json", action="store_true")
    p_diag.set_defaults(func=run_diagnose)

    p_probe = sub.add_parser("guest-probe",
                             help="ONE whitelisted non-mutating guest "
                                  "command (confirmation gate)")
    p_probe.add_argument("--region-id", required=True)
    p_probe.add_argument("--instance-id", required=True)
    p_probe.add_argument("--command", required=True,
                         help="exact whitelisted command line")
    p_probe.add_argument("--os-type", choices=("linux", "windows"),
                         default=None)
    p_probe.add_argument("--user-confirmed", action="store_true")
    p_probe.add_argument("--approval-quote", default="")
    p_probe.add_argument("--profile")
    p_probe.set_defaults(func=run_guest_probe)

    p_snap = sub.add_parser("create-snapshot",
                            help="snapshot-first guard (confirmation gate)")
    p_snap.add_argument("--region-id", required=True)
    p_snap.add_argument("--disk-id", required=True)
    p_snap.add_argument("--retention-days", type=int, default=None)
    p_snap.add_argument("--user-confirmed", action="store_true")
    p_snap.add_argument("--approval-quote", default="")
    p_snap.add_argument("--profile")
    p_snap.set_defaults(func=run_create_snapshot)

    p_expl = sub.add_parser("explain",
                            help="interpret pasted guest readings offline")
    p_expl.add_argument("--paste", default="-")
    p_expl.set_defaults(func=run_explain)

    return parser


def _run_selftest():
    """Offline boundary locks for the pure classification / validation core
    (no cloud calls). Thresholds and precedence each carry a discriminating
    case so a boundary or ordering regression fails an assertion."""
    results = []

    def expect(name, cond):
        results.append(bool(cond))
        print(("PASS " if cond else "FAIL ") + name)
        return cond

    def codes(store):
        return [v["code"] for v in classify(store)]

    def metrics(**vals):
        return {"metrics": {k: {"result": {"value": v}} for k, v in vals.items()}}

    # --- parse_utc: never raises, tolerates junk ---
    pu = parse_utc("2026-09-17T08:30:00Z")
    expect("parse_utc: valid Z -> tz-aware datetime", pu is not None and pu.tzinfo is not None and pu.hour == 8)
    expect("parse_utc: bad/empty/None -> None (never raises)",
           parse_utc("nope") is None and parse_utc("") is None and parse_utc(None) is None)

    # --- classify precedence ---
    crash = {"instance": {"status": "Running", "cpu": 2}, "health": {"health_status": "Ok"},
             "events": [{"type": "InstanceFailure.Reboot", "event_id": "e1"}]}
    expect("classify: crash reboot -> A only", codes(crash) == ["A_os_crash_event"])
    planned = {"instance": {"status": "Running", "cpu": 2},
               "events": [{"type": "SystemMaintenance.Reboot", "event_id": "e2", "cycle_status": "Executed"}]}
    expect("classify: planned reboot -> E not A", codes(planned) == ["E_planned_or_login"])
    redeploy = {"instance": {"status": "Running"},
                "events": [{"type": "SystemMaintenance.Redeploy", "event_id": "e3", "cycle_status": "WillExecute"}]}
    expect("classify: redeploy -> F present", "F_hardware_redeploy" in codes(redeploy))

    # --- classify thresholds (discriminating: at-threshold fires, below does not) ---
    cap = {"instance": {"status": "Running", "cpu": 2}, "health": {"health_status": "Ok"}}
    cap_at = dict(cap); cap_at.update(metrics(DiskReadWriteIOPSUtilization=DISK_UTIL_CAP_PCT))
    expect("classify: disk util at cap -> C", "C_storage_perf_ceiling" in codes(cap_at))
    cap_below = dict(cap); cap_below.update(metrics(DiskReadWriteIOPSUtilization=DISK_UTIL_CAP_PCT - 1))
    expect("classify: disk util below cap -> no C (threshold)", "C_storage_perf_ceiling" not in codes(cap_below))
    mem_at = dict(cap); mem_at.update(metrics(memory_usedutilization=MEM_HIGH_PCT))
    expect("classify: mem at threshold -> B", "B_resource_exhaustion" in codes(mem_at))
    mem_below = dict(cap); mem_below.update(metrics(memory_usedutilization=MEM_HIGH_PCT - 1))
    expect("classify: mem below threshold -> no B (threshold)", "B_resource_exhaustion" not in codes(mem_below))
    crash_mem = dict(crash); crash_mem.update(metrics(memory_usedutilization=99))
    expect("classify: crash event suppresses B (A precedence over B)", codes(crash_mem) == ["A_os_crash_event"])

    # --- classify power transition vs healthy ---
    trans = {"instance": {"status": "Stopping", "cpu": 2}, "health": {"health_status": "Ok"}}
    expect("classify: intermediate power state -> D, not H", codes(trans) == ["D_power_transition_handoff"])
    expect("classify: alive running, no events -> H", codes(cap) == ["H_os_alive_app_layer"])
    expect("classify: empty store -> no verdicts", classify({}) == [])

    # --- has_local_disk / recoverability ---
    local = {"instance_type": {"local_storage_amount": 2}}
    expect("has_local_disk: amount>0 -> True", has_local_disk(local) is True)
    expect("has_local_disk: cloud-only -> False", has_local_disk({"disks": [{"category": "cloud_essd"}]}) is False)
    expect("recoverability: local-disk warning present", any("local disks" in ln for ln in recoverability(local)))

    # --- validate_guest_command (fail-closed whitelist; security gate) ---
    ok_cmd = AUTO_GUEST_COMMANDS_LINUX[0]
    expect("vgc: accepts a whitelisted linux command", validate_guest_command(ok_cmd, "linux") == ok_cmd)
    for bad in ("", "free; reboot", "rm -rf /", "df -h | sh"):
        try:
            validate_guest_command(bad, "linux")
            rejected = False
        except ValueError:
            rejected = True
        expect("vgc rejects %r" % bad, rejected)

    passed = sum(results)
    print("SELFTEST: %s (%d/%d)" % ("PASS" if passed == len(results) else "FAIL", passed, len(results)))
    return 0 if passed == len(results) else 1


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    # Intercept before build_parser()/subcommand-required guard so a bare
    # --selftest runs the pure assertions offline (never shadowed).
    if "--selftest" in argv:
        return _run_selftest()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
