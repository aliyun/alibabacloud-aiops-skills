#!/usr/bin/env python3
"""Entry point: layered diagnosis of ECS console connection channels.

Covers the VNC / management-terminal rescue path and the browser web
terminals (Workbench, session manager): which layer breaks - instance
state, cloud configuration, the channel itself, the guest system, or the
customer-side path.

SECURITY:
  * Query calls (Describe*/Get*) run automatically.
  * ONE gated action exists: dispatching a single whitelisted NON-MUTATING
    inspection command into the guest. It is reached only through the
    `guest-probe` subcommand after the tell-then-confirm gate
    (--user-confirmed plus --approval-quote); the whitelist is frozen in
    _constants.py and every other command is refused.
  * Nothing destructive is ever executed: instance start/stop/reboot, disk
    detach/repair, password reset execution, service or firewall changes,
    fsck and cleanups stay human-only guidance.
  * No credential of any kind is accepted, read, printed or stored here;
    the aliyun CLI default chain resolves authentication.

Subcommands:
  check-auth    credential preflight (identity + UID label)
  diagnose      full layered evidence chain and verdicts
  guest-probe   ONE whitelisted non-mutating guest command (confirmation gate)
  explain       interpret customer-pasted terminal / channel output offline

Every run ends with `STATUS: OK | DEGRADED | FAIL` plus `NEXT_ACTION:`.
Exit codes: 0 = usable conclusion (OK or DEGRADED), 1 = no usable
conclusion, 2 = usage error.
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

from _cli import (
    CliError,
    call_cms,
    call_ecs,
    call_sts,
    new_session_id,
    redact,
)
from _constants import (
    AUTO_GUEST_COMMANDS_LINUX,
    AUTO_GUEST_COMMANDS_WINDOWS,
    AUTO_GUEST_COMMAND_FAMILIES,
    CA_STATUS_ONLINE,
    CMS_METRICS,
    CMS_NAMESPACE_ECS,
    CMS_PERIOD_SECONDS,
    CPU_HIGH_PCT,
    DOC_LINKS,
    DRIVE_ARG_PATTERN,
    ERROR_PATTERNS,
    FS_FULL_PCT,
    GATED_DISPATCH_ACTION,
    GUEST_COMMAND_TIMEOUT_SECONDS,
    HANDOFF_SKILLS,
    HEARTBEAT_FRESH_MINUTES,
    INTERMEDIATE_STATES,
    INVOCATION_POLL_BUDGET_SECONDS,
    INVOCATION_POLL_INTERVAL_SECONDS,
    INVOCATION_TERMINAL_STATUSES,
    LOAD_PER_VCPU_MIN,
    LAYERS,
    MEM_HIGH_PCT,
    NON_RUNNING_STATES,
    PATH_ARG_PATTERN,
    REFUSED_PATH_FRAGMENTS,
    REFUSED_SHELL_TOKENS,
    RUN_TYPE_LINUX,
    RUN_TYPE_WINDOWS,
    SKILL_NAME,
    VERDICT_ALL_GREEN,
    VERDICT_BOOT_FAULT,
    VERDICT_ENTRY_GUIDE,
    VERDICT_GRANT_DEPENDENCE,
    VERDICT_HEALTH_EVENT,
    VERDICT_LOCAL_PATH,
    VERDICT_LOGIN_POLICY,
    VERDICT_NOT_RUNNING,
    VERDICT_PORT_TRIAD,
    VERDICT_SATURATION_HANG,
    VERDICT_SESSION_CHANNEL_LIMIT,
    VERDICT_THIRD_PARTY_NETWORK,
    VERDICT_POWER_TRANSITION,
)

UTC_STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
INSTANCE_ID = re.compile(r"^i-[a-z0-9-]{4,64}$")
REGION_ID = re.compile(r"^[a-z][a-z0-9-]{2,30}$")

CHANNEL_CHOICES = ("vnc", "workbench", "session-manager", "one-click",
                   "ssh-client", "browser-app", "unknown")
SYMPTOM_CHOICES = (
    "cannot-open",            # the console channel page itself fails
    "black-screen",           # opens to black / frozen frame
    "stuck-at-boot",          # boot / loading screen, never reaches login
    "no-password-prompt",     # user typed, Enter, no password box appears
    "login-rejected",         # credentials refused on every channel
    "reset-password-ineffective",
    "blocked",                # web terminal reports interception
    "timeout",                # connection establishment times out
    "refused",                # Connection refused style failure
    "session-drop",           # terminal drops and kills running tasks
    "garbled-or-laggy",       # wrong characters / severe lag in terminal
    "entry-question",         # how do I reach the channel at all
    "unknown",
)


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


def match_error_patterns(error_text):
    """Return the canonical pattern keys present in the normalized English
    error wording supplied by the agent."""
    lowered = (error_text or "").lower()
    hits = []
    for key, needle in ERROR_PATTERNS.items():
        if needle.lower() in lowered:
            hits.append(key)
    return hits


def heartbeat_age_minutes(stamp):
    """Minutes since a Cloud Assistant heartbeat stamp; None if unparsable."""
    when = parse_utc(stamp)
    if when is None:
        return None
    delta = (now_utc() - when).total_seconds() / 60.0
    if delta < 0:
        return 0.0
    return delta


# Inline boundary assertions for the pure helpers (normal / boundary /
# invalid inputs), executed at import time.
assert heartbeat_age_minutes("2020-01-01T00:00:00Z") > 0
assert heartbeat_age_minutes("garbage") is None
assert heartbeat_age_minutes(None) is None
assert "connection_refused" in match_error_patterns(
    "ssh: connect to host 1.2.3.4 port 22: Connection refused")
assert match_error_patterns("") == []
assert sorted(match_error_patterns(
    "InvalidDependence.GrantAccess, Connection refused")) == \
    ["connection_refused", "grant_access_dependence"]


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
        "os_type": (inst.get("OSType") or "").lower() or None,
        "os_name": inst.get("OSName"),
        "cpu": inst.get("Cpu"),
        "memory_mib": inst.get("Memory"),
        "vpc_id": (inst.get("VpcAttributes") or {}).get("VpcId"),
        "internet_ips": (inst.get("PublicIpAddress") or {}).get(
            "IpAddress") or [],
        "eip": (inst.get("EipAddress") or {}).get("IpAddress") or None,
        "inner_ips": (inst.get("VpcAttributes") or {}).get(
            "PrivateIpAddress", {}).get("IpAddress") or [],
        "security_group_ids": (inst.get("SecurityGroupIds") or {}).get(
            "SecurityGroupId") or [],
        "instance_charge_type": inst.get("InstanceChargeType"),
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
    if not rows:
        return
    row = rows[0]
    events = []
    for ev in ((row.get("ScheduledSystemEventSet") or {}).get(
            "ScheduledSystemEventType") or []):
        events.append({
            "event_id": ev.get("EventId"),
            "type": (ev.get("EventType") or {}).get("Name"),
            "status": (ev.get("EventCycleStatus") or {}).get("Name"),
            "not_before": ev.get("NotBefore"),
            "published": ev.get("EventPublishTime"),
        })
    store["health"] = {
        "health_status": (row.get("HealthStatus") or {}).get("Name"),
        "instance_status": (row.get("Status") or {}).get("Name"),
        "scheduled_events": events,
    }


def fetch_cloud_assistant(store, sid, region, instance_id, profile):
    body = fetch(store, "DescribeCloudAssistantStatus", lambda: call_ecs(
        "DescribeCloudAssistantStatus", {"InstanceId.1": instance_id},
        sid, region, profile=profile))
    if not body:
        return
    rows = (body.get("InstanceCloudAssistantStatusSet") or {}).get(
        "InstanceCloudAssistantStatus") or []
    if not rows:
        return
    row = rows[0]
    online = row.get("CloudAssistantStatus") == CA_STATUS_ONLINE
    heartbeat = row.get("LastHeartbeatTime")
    age = heartbeat_age_minutes(heartbeat)
    store["cloud_assistant"] = {
        "installed": online,
        "version": row.get("CloudAssistantVersion"),
        "os_type": (row.get("OSType") or "").lower() or None,
        "last_heartbeat": heartbeat,
        "heartbeat_age_minutes": (None if age is None else round(age, 1)),
        "heartbeat_fresh": (age is not None
                            and age <= HEARTBEAT_FRESH_MINUTES),
    }


def fetch_invocation_history(store, sid, region, instance_id, profile):
    """Recent Cloud Assistant executions. History only, never live usage:
    it shows whether and when commands last ran inside the guest."""
    body = fetch(store, "DescribeInvocations(history)", lambda: call_ecs(
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
        history.append({
            "command_name": row.get("CommandName"),
            "command_type": row.get("CommandType"),
            "invocation_status": (instances[0].get("InvocationStatus")
                                  if instances else None),
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
                "Period": CMS_PERIOD_SECONDS,
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
# Verdict engine (pure function over the collected evidence + facts)
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


def saturation_evidence(store):
    """Evidence lines when CloudMonitor readings show resource saturation
    (the ticket-proven 'system hang' signature that kills every channel at
    once)."""
    lines = []
    mem = metric_value(store, "memory_usedutilization")
    cpu = metric_value(store, "CPUUtilization")
    load = metric_value(store, "load_1m")
    vcpu = (store.get("instance") or {}).get("cpu") or 0
    if mem is not None and mem >= MEM_HIGH_PCT:
        lines.append("memory_usedutilization={0}%".format(mem))
    if cpu is not None and cpu >= CPU_HIGH_PCT:
        lines.append("CPUUtilization={0}%".format(cpu))
    if load is not None and vcpu and load >= LOAD_PER_VCPU_MIN * float(vcpu):
        lines.append("load_1m={0} against {1} vCPU".format(load, vcpu))
    return lines


def classify(store, facts):
    """Return verdict dicts ordered by precedence across the five layers."""
    verdicts = []
    inst = store.get("instance") or {}
    status = inst.get("status")
    health = store.get("health") or {}
    ca = store.get("cloud_assistant") or {}
    agent_online = bool(ca.get("installed")) and bool(ca.get("heartbeat_fresh"))
    agent_unknown = "cloud_assistant" not in store
    saturation = saturation_evidence(store)
    patterns = facts["patterns"]
    symptom = facts["symptom"]
    active_events = [e for e in (health.get("scheduled_events") or [])
                     if e.get("status") in
                     ("Scheduled", "Executing", "Inquiring")]

    # L2: the tier's quotable dependence error code short-circuits first.
    if "grant_access_dependence" in patterns:
        verdicts.append({
            "code": VERDICT_GRANT_DEPENDENCE,
            "layer": "L2",
            "confidence": "high",
            "evidence": ["customer error matches "
                         + ERROR_PATTERNS["grant_access_dependence"]],
            "note": ("the operation is blocked by a Workbench-created "
                     "reverse-access grant chain on the VPC, not by the "
                     "instance; releasing that chain is a human console "
                     "action - see references/console-channel-diagnosis__error-codes.md"),
        })

    # L1: power state decides whether any console channel can attach.
    if status in NON_RUNNING_STATES or status in INTERMEDIATE_STATES:
        if status in INTERMEDIATE_STATES:
            verdicts.append({
                "code": VERDICT_POWER_TRANSITION,
                "layer": "L1",
                "confidence": "high",
                "evidence": ["instance Status={0}".format(status)],
                "note": ("the instance is mid start/stop; a console channel "
                         "reporting 'the current state of the resource does "
                         "not support this operation' here is a lifecycle "
                         "state, not a channel fault; if it stays stuck, "
                         "hand off to {0}".format(
                             HANDOFF_SKILLS["instance_state"])),
            })
        else:
            verdicts.append({
                "code": VERDICT_NOT_RUNNING,
                "layer": "L1",
                "confidence": "high",
                "evidence": ["instance Status={0}".format(status)],
                "note": ("VNC / web terminal sessions attach only to a "
                         "Running instance; a Stopped (or Pending) instance "
                         "explains every channel failure at once. Starting "
                         "it is a human console action; if login was the "
                         "goal, the reset-password-then-restart order "
                         "matters (references/console-channel-diagnosis__channel-matrix.md)"),
            })
    elif status == "Running":
        # L1 health / platform events.
        if health.get("health_status") not in (None, "Ok") or active_events:
            verdicts.append({
                "code": VERDICT_HEALTH_EVENT,
                "layer": "L1",
                "confidence": "medium",
                "evidence": (
                    ["health_status={0}".format(health.get("health_status"))]
                    if health.get("health_status") not in (None, "Ok") else []
                ) + ["scheduled event {0} ({1}, {2})".format(
                    e.get("type"), e.get("status"), e.get("not_before"))
                    for e in active_events[:5]],
                "note": ("a platform-recorded health issue or pending "
                         "system event precedes channel symptoms; read the "
                         "event type first, then continue layering"),
            })

        # L4: hang vs boot fault.
        hang_symptoms = ("no-password-prompt", "blocked", "timeout",
                         "cannot-open")
        boot_symptoms = ("black-screen", "stuck-at-boot")
        if saturation:
            verdicts.append({
                "code": VERDICT_SATURATION_HANG,
                "layer": "L4",
                "confidence": "high" if len(saturation) >= 2 else "medium",
                "evidence": saturation + [
                    "cloud_assistant_online={0}".format(agent_online)],
                "note": ("resource saturation explains simultaneous failure "
                         "of VNC, Workbench and SSH (the classic 'login "
                         "prompt never answers' / 'web terminal blocked' "
                         "pattern). Recovery (snapshot, then restart from "
                         "the console) is a human action; process-level "
                         "attribution needs atop AFTER the incident "
                         "reproduces"),
            })
        if symptom in boot_symptoms or "state_unsupported" in patterns:
            verdicts.append({
                "code": VERDICT_BOOT_FAULT,
                "layer": "L4",
                "confidence": "medium" if not agent_online else "low",
                "evidence": ["symptom={0}".format(symptom),
                             "error patterns={0}".format(patterns or "none"),
                             "cloud_assistant_online={0}".format(
                                 agent_online)],
                "note": ("the channel reaches the screen but the guest "
                         "never completes boot or never responds to login: "
                         "that is an operating-system boot / system-file "
                         "fault, not a channel fault - hand off to {0} with "
                         "the evidence list (references/console-channel-diagnosis__handoff-playbook.md)"
                         .format(HANDOFF_SKILLS["os_fault"])),
            })
        if (not agent_online and not agent_unknown and not saturation
                and symptom in hang_symptoms and not facts["alt_channel_works"]):
            verdicts.append({
                "code": VERDICT_SATURATION_HANG,
                "layer": "L4",
                "confidence": "low",
                "evidence": [
                    "cloud assistant agent is not reporting online while "
                    "the instance is Running",
                    "symptom={0}".format(symptom)],
                "note": ("internal channel unreachable with the instance "
                         "Running usually means the guest is hung or its "
                         "boot is incomplete; confirm via VNC screenshot, "
                         "then treat as hang (metrics showed no saturation) "
                         "or boot fault"),
            })

        # L4: login-policy family (password refused everywhere).
        if symptom in ("login-rejected", "reset-password-ineffective") or \
                "too_many_auth_failures" in patterns or \
                ("incorrect_login" in patterns
                 and symptom == "login-rejected"):
            verdicts.append({
                "code": VERDICT_LOGIN_POLICY,
                "layer": "L4",
                "confidence": "medium" if agent_online else "low",
                "evidence": ["symptom={0}".format(symptom),
                             "error patterns={0}".format(patterns or "none")],
                "note": ("credentials refused on every channel despite a "
                         "Running instance: check the reset-then-restart "
                         "sequence first (an offline password reset only "
                         "takes effect after a restart), then suspect an "
                         "in-guest lockout policy; PAM / lockout state is "
                         "NOT auto-inspectable - ask the customer to paste "
                         "output into explain"),
            })

        # L4: third-party network stack inside the guest.
        if facts["third_party_network"] and (
                symptom in ("timeout", "cannot-open", "refused")
                or "socket_timeout" in patterns):
            verdicts.append({
                "code": VERDICT_THIRD_PARTY_NETWORK,
                "layer": "L4",
                "confidence": "medium",
                "evidence": [
                    "customer reports third-party tunnel software "
                    "(e.g. Tailscale-class) installed in the guest",
                    "symptom={0}".format(symptom),
                    "cloud_assistant_online={0}".format(agent_online)],
                "note": ("internal Alibaba Cloud service segments reached by "
                         "the web terminal can be rejected by the "
                         "software's netfilter rules while public traffic "
                         "still works; disabling those rules is a "
                         "configuration change the customer performs "
                         "manually, with its own side effects "
                         "(references/console-channel-diagnosis__error-codes.md)"),
            })

        # L2/L5: refused + port triage.
        if symptom == "refused" or "connection_refused" in patterns or \
                facts["service_port"]:
            verdicts.append({
                "code": VERDICT_PORT_TRIAD,
                "layer": "L2",
                "confidence": "medium",
                "evidence": (
                    ["symptom={0}".format(symptom),
                     "error patterns={0}".format(patterns or "none")]
                    + (["service port supplied: {0}".format(
                        facts["service_port"])]
                       if facts["service_port"] else [])),
                "note": ("'Connection refused' means a reachable host "
                         "answered with no listener on that port: check "
                         "(1) the application's real port, (2) security-"
                         "group ingress rules for it, (3) the in-guest "
                         "listener and its address family. One-click web "
                         "terminal connect only uses port 22, so a "
                         "non-default ssh port breaks exactly that channel"),
            })

    # L5: another console channel works while the customer's own path fails.
    if status == "Running" and facts["local_channel_fails"] and (
            facts["alt_channel_works"] or agent_online):
        verdicts.append({
            "code": VERDICT_LOCAL_PATH,
            "layer": "L5",
            "confidence": "high" if agent_online else "medium",
            "evidence": [
                "internal channel reachable: "
                "workbench/console path works={0}, cloud assistant "
                "online={1}".format(facts["alt_channel_works"],
                                     agent_online),
                "customer-side connection failing meanwhile=True"],
            "note": ("the server answers on the internal channel and not on "
                     "the customer's own path: the fault is local egress "
                     "(IP blocklists, security software, carrier route, "
                     "cross-border latency). Web-terminal access uses "
                     "Alibaba Cloud's internal path, so 'Workbench works "
                     "but my ssh does not' points AT THE CUSTOMER SIDE, not "
                     "at the instance (references/console-channel-diagnosis__diagnosis-playbook.md)"),
        })

    # L3: session-channel behaviour limits.
    if facts["session_drop"] or symptom in ("session-drop",
                                            "garbled-or-laggy"):
        verdicts.append({
            "code": VERDICT_SESSION_CHANNEL_LIMIT,
            "layer": "L3",
            "confidence": "high",
            "evidence": ["symptom={0}".format(symptom),
                         "session_drop_flag={0}".format(facts["session_drop"])],
            "note": ("a browser terminal session is fragile by design: "
                     "disconnect is NOT a server reboot, and foreground "
                     "processes die with the session. Run long tasks under "
                     "nohup/screen; garbled input is a browser / input-"
                     "method limitation of VNC - switch channel "
                     "(references/console-channel-diagnosis__channel-matrix.md)"),
        })

    # L0: pure entry/usage question.
    if symptom == "entry-question" and status == "Running":
        verdicts.append({
            "code": VERDICT_ENTRY_GUIDE,
            "layer": "L0",
            "confidence": "high",
            "evidence": ["symptom=entry-question"],
            "note": ("no fault found; the request is channel entry and "
                     "usage - answer from references/console-channel-diagnosis__channel-matrix.md "
                     "(console > remote connection, per-method fallback "
                     "table)"),
        })

    # Baseline: everything green.
    if status == "Running" and agent_online and not saturation \
            and health.get("health_status") in (None, "Ok") \
            and not verdicts:
        verdicts.append({
            "code": VERDICT_ALL_GREEN,
            "layer": "L1-L4",
            "confidence": "medium",
            "evidence": ["Status=Running",
                         "cloud_assistant_online=true",
                         "no saturation in {0} metric(s)".format(
                             len(CMS_METRICS))],
            "note": ("the cloud side shows no fault on this instance; the "
                     "failure is on the exact screen the customer is "
                     "standing at - capture the verbatim error text and a "
                     "screenshot, re-run with --error-text / --symptom, or "
                     "route by references/console-channel-diagnosis__channel-matrix.md fallbacks"),
        })
    return verdicts


# Inline boundary assertions for the pure verdict helpers: saturation math
# must fire at the threshold, stay quiet below it, and tolerate missing
# datapoints.
_store_sat = {
    "instance": {"cpu": 2, "status": "Running"},
    "metrics": {
        "CPUUtilization": {"result": {"value": "97.5"}},
        "memory_usedutilization": {"result": None},
        "load_1m": {"result": {"value": 9.0}},
    },
}
assert saturation_evidence(_store_sat) == [
    "CPUUtilization=97.5%", "load_1m=9.0 against 2 vCPU"]
assert saturation_evidence({"instance": {"cpu": 2}, "metrics": {}}) == []
assert metric_value({}, "CPUUtilization") is None


# ---------------------------------------------------------------------------
# Guest command validation (frozen whitelist, fail closed)
# ---------------------------------------------------------------------------

def validate_guest_command(raw, os_type):
    """Return the exact whitelisted command string or raise ValueError."""
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
                "into explain instead".format(fragment))
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
        "references/console-channel-diagnosis__guest-inspection-whitelist.md for the approved set and "
        "the manual path for everything else")


# Inline boundary assertions for the whitelist gate: exact command, refused
# composition, refused path fragment, family with argument, unknown command.
assert validate_guest_command("df -h", "linux") == "df -h"
assert validate_guest_command("ls -la /", "linux") == "ls -la /"
assert validate_guest_command("Get-Volume", "windows") == "Get-Volume"
for _bad, _why in (
        ("df -h; rm -rf /", "composition"),
        ("cat /etc/ssh/sshd_config", "ssh fragment"),
        ("uptime", "not whitelisted"),
        ("ss -lntp", "not whitelisted"),
):
    try:
        validate_guest_command(_bad, "linux")
    except ValueError:
        pass
    else:
        raise AssertionError("whitelist accepted {0!r} ({1})".format(
            _bad, _why))


def probe_gate_inputs(args):
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
# Subcommand: check-auth
# ---------------------------------------------------------------------------

def run_check_auth(args):
    sid = new_session_id()
    try:
        body = call_sts(sid, profile=args.profile)
    except CliError as err:
        print("[WARN] credential preflight failed: {0}".format(err),
              file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: have the operator repair the aliyun CLI default "
              "credential chain (aliyun sts get-caller-identity in their own session); "
              "never paste credentials into this conversation")
        return 1
    print("session_id: {0}".format(sid))
    account = str(body.get("AccountId") or "")
    arn = str(body.get("Arn") or "")
    # The caller account id and its ARN are internal identifiers; the last four
    # digits let the customer confirm which account answered, nothing more.
    print("account_id: {0}".format(
        "****" + account[-4:] if account else "not reported"))
    print("identity_type: {0}".format(body.get("IdentityType")))
    print("arn: {0}".format(
        re.sub(r"(?<!\d)\d{16}(?!\d)", lambda m: "****" + m.group(0)[-4:], arn)
        or "not reported"))
    print("STATUS: OK")
    print("NEXT_ACTION: run diagnose with --region-id and --instance-id")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: diagnose
# ---------------------------------------------------------------------------

def collect_facts(args):
    return {
        "channel": args.channel,
        "symptom": args.symptom,
        "error_text": (args.error_text or "").strip(),
        "patterns": match_error_patterns(args.error_text),
        "service_port": args.service_port,
        "alt_channel_works": bool(args.alt_channel_works),
        "local_channel_fails": bool(args.local_channel_fails),
        "third_party_network": bool(args.third_party_network),
        "session_drop": bool(args.session_drop),
    }


def run_diagnose(args):
    sid = new_session_id()
    store = {"errors": [], "required_failed": False}
    if not REGION_ID.match(args.region_id):
        print("[GATE] --region-id must look like cn-hangzhou", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: confirm the instance's region with the customer")
        return 1
    if not INSTANCE_ID.match(args.instance_id):
        print("[GATE] --instance-id must be an i-... identifier",
              file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: ask for the instance id (console > instances)")
        return 1

    facts = collect_facts(args)

    try:
        identity = call_sts(sid, profile=args.profile)
    except CliError as err:
        print("[WARN] identity step failed: {0}".format(err), file=sys.stderr)
        store["errors"].append({"step": "GetCallerIdentity",
                                "code": err.code, "message": str(err)[:200],
                                "category": "permission"
                                if err.is_auth_denied else "api"})
        identity = {}
    account_id = str(identity.get("AccountId", "") or "")
    caller_type = str(identity.get("IdentityType", "") or "")

    fetch_instance(store, sid, args.region_id, args.instance_id,
                   args.profile)
    if store.get("required_failed"):
        render_fail(store, sid, account_id, args)
        return 1
    fetch_full_status(store, sid, args.region_id, args.instance_id,
                      args.profile)
    fetch_cloud_assistant(store, sid, args.region_id, args.instance_id,
                          args.profile)
    fetch_invocation_history(store, sid, args.region_id, args.instance_id,
                             args.profile)
    fetch_metrics(store, sid, args.region_id, args.instance_id, args.profile)

    verdicts = classify(store, facts)
    next_actions = suggest_next_actions(store, facts, verdicts)
    if args.json:
        print(json.dumps({
            "session_id": sid, "account_id": account_id,
            "identity_type": caller_type, "region": args.region_id,
            "instance": store.get("instance"),
            "health": store.get("health"),
            "cloud_assistant": store.get("cloud_assistant"),
            "invocation_history": store.get("invocation_history"),
            "metrics": store.get("metrics"),
            "metric_source": {"namespace": CMS_NAMESPACE_ECS,
                              "period_seconds": CMS_PERIOD_SECONDS},
            "facts": facts, "verdicts": verdicts,
            "next_actions": next_actions, "errors": store["errors"],
            "status": degrade_status(store),
        }, indent=2, ensure_ascii=False))
        emit_status(store)
        return 0 if not store.get("required_failed") else 1
    render_report(sid, account_id, caller_type, args, store, facts, verdicts,
                  next_actions)
    emit_status(store)
    return 0 if not store.get("required_failed") else 1


def degrade_status(store):
    return "DEGRADED" if store.get("errors") else "OK"


def emit_status(store):
    status = degrade_status(store)
    print("STATUS: {0}".format(status))
    if store.get("errors") and status == "DEGRADED":
        print("NEXT_ACTION: the layered verdicts above were produced with "
              "the degraded legs explicitly marked; rerun failed steps after "
              "fixing permissions, or collect the missing readings from the "
              "customer via explain")


def render_fail(store, sid, account_id, args):
    print("=" * 72)
    print("ECS console-channel diagnosis | session {0}".format(sid))
    print("=" * 72)
    print("[FAIL] no usable conclusion: the target instance could not be "
          "verified in region {0} under account {1}.".format(
              args.region_id, account_id or "(unresolved)"))
    render_errors(store)
    print("STATUS: FAIL")
    print("NEXT_ACTION: confirm the region and instance id with the "
          "customer (console > instances > region switch); never guess a "
          "different id")


def section(title):
    print("\n" + title)
    print("-" * len(title))


def render_report(sid, account_id, caller_type, args, store, facts, verdicts,
                  next_actions):
    inst = store.get("instance") or {}
    ca = store.get("cloud_assistant") or {}
    health = store.get("health") or {}
    print("=" * 72)
    print("ECS console-channel diagnosis  (skill: {0})".format(SKILL_NAME))
    print("session_id: {0}".format(sid))
    print("=" * 72)

    section("Inputs and provenance")
    print("region: {0} (user-provided)".format(args.region_id))
    print("instance: {0} (user-provided)".format(args.instance_id))
    print("account UID: {0} (auto-derived via sts get-caller-identity; "
          "traceability label only)".format(account_id or "unresolved"))
    if caller_type:
        print("caller identity type: {0}{1}".format(
            caller_type,
            " - a RAM sub-user: consider Workbench/ECS authorization for "
            "CLI login failures before suspecting the password"
            if caller_type.lower() in ("ram-user", "sub", "subuser") else ""))
    print("reported channel: {0}; symptom: {1}".format(
        facts["channel"], facts["symptom"]))
    if facts["error_text"]:
        print("error wording (normalized English): {0}".format(
            redact(facts["error_text"])[:200]))
    print("error pattern matches: {0}".format(
        ", ".join(facts["patterns"]) or "none"))

    for layer_id, layer_name, what in LAYERS:
        section("Layer {0} - {1}".format(layer_id, layer_name))
        if layer_id == "L1":
            print("power state: {0}".format(inst.get("status")))
            print("instance type: {0}; OS: {1} ({2})".format(
                inst.get("instance_type"), inst.get("os_type"),
                inst.get("os_name")))
            print("health status: {0}".format(
                health.get("health_status") or "not returned"))
            for ev in (health.get("scheduled_events") or [])[:5]:
                print("scheduled event: {0} status={1} not_before={2}".format(
                    ev.get("type"), ev.get("status"), ev.get("not_before")))
        elif layer_id == "L2":
            ips = inst.get("internet_ips") or []
            print("public IP: {0}".format(
                ", ".join(i for i in ips if i) or
                ((inst.get("eip") or "none") + " (EIP)"
                 if inst.get("eip") else "none attached")))
            print("private IP: {0}".format(
                ", ".join(inst.get("inner_ips") or []) or "not returned"))
            print("security groups bound: {0}".format(
                ", ".join(inst.get("security_group_ids") or []) or
                "not returned"))
            print("security-group RULE detail is outside this skill's "
                  "verified action set: the customer checks ingress rules "
                  "for the service port in the console (guidance only)")
        elif layer_id == "L3":
            if ca:
                print("cloud assistant agent: {0} (version {1}; OS "
                      "reported {2})".format(
                          "online" if ca.get("installed") else "not online",
                          ca.get("version"), ca.get("os_type")))
                print("last heartbeat: {0} (age {1} min; fresh={2})".format(
                    ca.get("last_heartbeat"),
                    ca.get("heartbeat_age_minutes"),
                    ca.get("heartbeat_fresh")))
            else:
                print("cloud assistant status: not available "
                      "(see degradation log)")
            hist = store.get("invocation_history") or []
            print("recent in-guest command history: {0} record(s)".format(
                len(hist)))
            for row in hist[:3]:
                print("  - {0} ({1}) status={2} fired={3}".format(
                    row.get("command_name"), row.get("command_type"),
                    row.get("invocation_status"), row.get("fired_time")))
            print("history is past execution records, never live readings; "
                  "VNC / Workbench session establishment stays a human "
                  "console step")
        elif layer_id == "L4":
            print("CloudMonitor source: namespace {0}, aggregation period "
                  "{1}s (auto-filled, not customer-provided)".format(
                      CMS_NAMESPACE_ECS, CMS_PERIOD_SECONDS))
            any_reading = False
            for metric, entry in (store.get("metrics") or {}).items():
                result = entry.get("result")
                if isinstance(result, dict):
                    any_reading = True
                    print("{0}: {1} at {2} - {3}".format(
                        metric, result.get("value"),
                        result.get("timestamp_utc"), entry["meaning"]))
                else:
                    print("{0}: no datapoint - {1}".format(
                        metric, entry["meaning"]))
            if not any_reading:
                print("(no CloudMonitor datapoint returned: a fresh "
                      "instance, or guest-OS metrics need the CloudMonitor "
                      "agent installed inside the instance)")
            sat = saturation_evidence(store)
            print("saturation flags: {0}".format(", ".join(sat) or "none"))
        elif layer_id == "L5":
            print("customer-side facts collected: alt console channel works="
                  "{0}; customer-local path fails={1}; third-party tunnel "
                  "software={2}; session-drop incidents={3}".format(
                      facts["alt_channel_works"],
                      facts["local_channel_fails"],
                      facts["third_party_network"],
                      facts["session_drop"]))
            print("the customer's own network cannot be probed from the "
                  "cloud side: local steps are listed under Next actions")

    section("Verdicts (layered, ordered by precedence)")
    if not verdicts:
        print("no layered verdict could be drawn from the current evidence")
    for v in verdicts:
        print("\n[{0}] layer {1} confidence {2}".format(
            v["code"], v["layer"], v["confidence"]))
        for line in v["evidence"]:
            print("  evidence: {0}".format(line))
        print("  reading: {0}".format(v["note"]))

    section("Next actions (manual guidance unless marked gated)")
    for line in next_actions:
        print(" - {0}".format(line))
    hints = permission_hint(store)
    for line in hints:
        print(" - {0}".format(line))

    render_errors(store)


SNAPSHOT_LINE = ("before ANY restart, stop, disk detach/attach or offline "
                 "repair the customer performs: create a snapshot of the "
                 "affected disks first in the console (snapshots bill by "
                 "stored capacity; creation and deletion stay human "
                 "actions - this skill never creates them)")


def suggest_next_actions(store, facts, verdicts):
    actions = []
    codes = [v["code"] for v in verdicts]
    inst = store.get("instance") or {}
    ca = store.get("cloud_assistant") or {}

    if VERDICT_GRANT_DEPENDENCE in codes:
        actions.append(
            "explain the reverse-access grant chain meaning, then have the "
            "customer release the Workbench grant in the console before "
            "retrying the VPC change (references/console-channel-diagnosis__error-codes.md; no "
            "verified official deep link ships in this package - state "
            "that honestly and route to support if the console path is "
            "unclear)")
    if VERDICT_NOT_RUNNING in codes:
        actions.append(
            "tell the customer the instance is {0}: start it from the "
            "console (human action) - no console channel can attach "
            "meanwhile".format(inst.get("status")))
    if VERDICT_POWER_TRANSITION in codes:
        actions.append(
            "wait for the transition; if it stays stuck, hand off to {0} "
            "with this report".format(HANDOFF_SKILLS["instance_state"]))
    if VERDICT_SATURATION_HANG in codes:
        actions.append(SNAPSHOT_LINE)
        actions.append(
            "recovery restart is a human console action; afterwards "
            "install atop to catch the next incident ("
            + DOC_LINKS["atop"] + ")")
        if ca.get("installed"):
            actions.append(
                "optionally gather one gated in-guest reading now (guest-"
                "probe 'df -h' after tell-then-confirm) as corroborating "
                "capacity evidence")
    if VERDICT_BOOT_FAULT in codes:
        actions.append(
            "hand off to {0} (guest OS boot/system-file fault); the "
            "handoff text template with the evidence checklist is in "
            "references/console-channel-diagnosis__handoff-playbook.md".format(
                HANDOFF_SKILLS["os_fault"]))
        actions.append(SNAPSHOT_LINE)
    if VERDICT_LOGIN_POLICY in codes:
        actions.append(
            "walk the reset-password (customer console action, see "
            + DOC_LINKS["reset-password"] + ") then RESTART ordering; if "
            "still refused on every channel, suspect the in-guest lockout "
            "policy - ask the customer to paste login/account output into "
            "explain; disk-attach password repair is human-only")
    if VERDICT_PORT_TRIAD in codes:
        actions.append(
            "run the port triad: application's real port vs the port being "
            "accessed; security-group ingress rule for it (console self-"
            "check); in-guest listener and address family via a customer-"
            "run 'ss -lntp' pasted into explain")
    if VERDICT_LOCAL_PATH in codes:
        actions.append(
            "give the customer-side test ladder: telnet to the service "
            "port from the local machine, mtr path analysis ("
            + DOC_LINKS["mtr"] + "), retry over a phone hotspot, disable "
            "local security software, check ISP/cross-border latency; for "
            "cloud-side interception suspicions, review the security-"
            "whitelist console path")
    if VERDICT_THIRD_PARTY_NETWORK in codes:
        actions.append(
            "ask the customer to review the tunnel software's firewall "
            "mode manually (its netfilter rules can reject Alibaba Cloud "
            "service segments); changing it is a customer configuration "
            "action with its own side effects - warn about them, never "
            "execute it here")
    if VERDICT_SESSION_CHANNEL_LIMIT in codes:
        actions.append(
            "explain session fragility and set long tasks under nohup / "
            "screen (" + DOC_LINKS["keep-process-running"] + "); switch "
            "VNC input problems to a native SSH or Workbench password "
            "session per references/console-channel-diagnosis__channel-matrix.md")
    if VERDICT_ENTRY_GUIDE in codes:
        actions.append(
            "answer from the method matrix: console > the instance > "
            "remote connection, then pick the channel per "
            "references/console-channel-diagnosis__channel-matrix.md (VNC needs no guest network, "
            "Workbench password login survives a non-22 ssh port, etc.)")
    if VERDICT_ALL_GREEN in codes:
        actions.append(
            "capture the exact failing screen: verbatim error text and a "
            "screenshot; rerun diagnose with --error-text/--symptom filled")
    if facts["symptom"] == "unknown" and not facts["error_text"]:
        actions.append(
            "ask the customer the three opening questions first: instance id "
            "+ region? OS family? which screen / what exact error (screenshot "
            "welcome)?")
    if not ca or not ca.get("installed"):
        actions.append(
            "the agent being unreachable removes one evidence leg: fall "
            "back to asking the customer to paste the readings so we can "
            "interpret them here")
    return dedupe(actions)


def dedupe(items):
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def render_errors(store):
    errors = store.get("errors") or []
    section("Graceful degradation log")
    if not errors:
        print("no degraded step in this run")
    for err in errors:
        print("[WARN] step={step} code={code} message={message}".format(
            **err), file=sys.stderr)
        print("- step {0}: {1} ({2})".format(
            err.get("step"), err.get("code"), err.get("category")))


# ---------------------------------------------------------------------------
# Subcommand: guest-probe (gated)
# ---------------------------------------------------------------------------

def run_guest_probe(args):
    sid = new_session_id()
    store = {"errors": [], "required_failed": False}

    problems = probe_gate_inputs(args)
    if not REGION_ID.match(args.region_id):
        problems.append("--region-id must look like cn-hangzhou")
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
        "DescribeCloudAssistantStatus", {"InstanceId.1": args.instance_id},
        sid, args.region_id, profile=args.profile))
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
        return 0
    if not installed:
        print("[WARN] Cloud Assistant agent is not reporting online; the "
              "guest channel is unavailable - this also means the hang may "
              "be deeper than the web terminal alone")
        print("STATUS: DEGRADED")
        print("NEXT_ACTION: have the customer run the whitelisted command "
              "inside the instance (console session or SSH) and paste the "
              "output back into scripts/areas/console_channel_diagnosis/console_channel_diagnosis.py explain")
        return 0

    try:
        command = validate_guest_command(args.command, os_type)
    except ValueError as bad:
        print("[GATE] refused: {0}".format(bad))
        print("STATUS: FAIL")
        print("NEXT_ACTION: pick a command from "
              "references/console-channel-diagnosis__guest-inspection-whitelist.md or guide the "
              "customer to run it manually and paste the output to explain")
        return 1

    print("dispatching exactly one whitelisted non-mutating command: "
          "{0!r} on instance {1} (approval recorded as the operator's "
          "quote; this acknowledgement covers THIS call only)".format(
              command, args.instance_id))
    run_type = RUN_TYPE_LINUX if os_type == "linux" else RUN_TYPE_WINDOWS
    # The command goes out in plain text: no encoding parameter is part of
    # this tier's verified surface. Invocation Output is Base64 and decoded
    # at read-back. A rejected request degrades; it is never retried with an
    # invented parameter.
    body = fetch(store, "gated dispatch", lambda: call_ecs(
        GATED_DISPATCH_ACTION, {
            "Type": run_type,
            "CommandContent": command,
            "Name": "{0}-probe".format(SKILL_NAME)[:128],
            "Description": "single whitelisted inspection command",
            "Timeout": GUEST_COMMAND_TIMEOUT_SECONDS,
            "InstanceId.1": args.instance_id,
        }, sid, args.region_id, write=True, profile=args.profile))
    invoke_id = (body or {}).get("InvokeId")
    if not invoke_id:
        print("STATUS: DEGRADED")
        print("NEXT_ACTION: the dispatch failed (see degradation log); "
              "fall back to manual customer readings via explain")
        render_errors(store)
        return 0

    print("invoke_id: {0}".format(invoke_id))
    deadline = time.monotonic() + INVOCATION_POLL_BUDGET_SECONDS
    output = None
    status = None
    exit_code = None
    while time.monotonic() < deadline:
        time.sleep(INVOCATION_POLL_INTERVAL_SECONDS)
        poll = fetch(store, "DescribeInvocations(poll)", lambda: call_ecs(
            "DescribeInvocations", {
                "InvokeId": invoke_id,
                "InstanceId": args.instance_id,
                "IncludeOutput": True,
            }, sid, args.region_id, profile=args.profile))
        if not poll:
            continue
        rows = (poll.get("Invocations") or {}).get("Invocation") or []
        instances = ((rows[0].get("InvokeInstances") or {}).get(
            "InvokeInstance") or [] if rows else [])
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
        print("NEXT_ACTION: interpret the reading against the layered "
              "verdicts; any follow-up command needs its own tell-then-"
              "confirm cycle")
        return 0
    print("STATUS: DEGRADED")
    print("NEXT_ACTION: no output within the polling budget; ask the "
          "customer to run the command and paste it into explain")
    render_errors(store)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: explain (offline text interpretation, zero cloud calls)
# ---------------------------------------------------------------------------

# Each rule: (name, pattern list, verdict line, next-action line). Patterns
# match case-insensitively on customer-pasted text. Every claim is a
# reading of what the customer themselves pasted - never a cloud fact.
EXPLAIN_RULES = (
    ("df-full", (r"\b100%", r"use% *[9][5-9]"),
     "a filesystem reports near-or-at 100% capacity: after-login failures "
     "and blocked web-terminal services are commonly caused by a full disk, "
     "which is a capacity matter, not a channel fault",
     "hand off to {0} for the capacity path; channel-side recovery is only "
     "'log in and read'".format(HANDOFF_SKILLS["disk_capacity"])),
    ("sshd-listen-v6-only", (r"\[::\]:\d+",),
     "the pasted listener list shows an IPv6 wildcard line; if the same "
     "port has no IPv4 (0.0.0.0) line, connections arriving over IPv4 are "
     "refused even though the service is up",
     "compare with 0.0.0.0 lines in the same paste; fixing the listener is "
     "a guest configuration change the customer performs"),
    ("no-listener", (r"connection refused",),
     "'Connection refused' means the host answered and nothing listens on "
     "that port: the network path is NOT the problem",
     "run the port triad (real application port / security-group ingress / "
     "in-guest listener) from references/console-channel-diagnosis__error-codes.md"),
    ("route-or-timeout", (r"no route to host", r"timed out", r"operation "
                          r"timed out"),
     "the path, not the port: packets never got answered - local network, "
     "intermediate carrier, or an ingress rule dropping traffic",
     "customer-side ladder: telnet / hotspot / mtr ("
     + DOC_LINKS["mtr"] + "); security-group ingress self-check"),
    ("state-unsupported", (r"current state of the resource does not support"
                           r"|state.*not support this operation",),
     "the console refuses because the INSTANCE state (stopping, redeploying, "
     "or not yet Running) does not allow the operation - the channel itself "
     "is not broken",
     "re-read power state with diagnose; stuck transitions hand off to {0}"
     .format(HANDOFF_SKILLS["instance_state"])),
    ("lockout-signals", (r"account locked|too many authentication failures|"
                         r"authentication failure",),
     "repeated-failure / lockout wording: an in-guest login-attempt policy "
     "may be locking the account regardless of password correctness",
     "reset-then-restart ordering first; lockout state is not "
     "auto-inspectable - keep it in the manual lane"),
    ("boot-fault-signals", (r"emergency mode|fsck|kernel panic|not "
                            r"syncing|failed to mount|cannot open/"
                            r"root|initramfs|cloud-init.*fail",),
     "boot-sequence wording: the guest never finished starting, so no "
     "channel can reach a login - this is an OS-fault area",
     "hand off to {0} with the paste and the layered report".format(
         HANDOFF_SKILLS["os_fault"])),
    ("third-party-tunnel", (r"tailscale|wireguard|openvpn|netfilter",),
     "third-party tunnel software appears in the paste; its firewall mode "
     "can reject Alibaba Cloud service segments and break internal-channel "
     "logins while public traffic survives",
     "configuration review is the customer's manual action with side "
     "effects; never toggle it from here"),
    ("oom-signals", (r"out of memory|oom-killer|cannot allocate",),
     "memory-exhaustion wording: consistent with the 'every channel hangs "
     "at once' pattern",
     "saturation verdict lane: snapshot, human restart, then atop for the "
     "next occurrence"),
    ("pam-or-lib", (r"libc|no such file or directory.*/bin|"
                    r"error while loading shared libraries",),
     "system-library / core-directory wording: the guest's binaries or "
     "libraries are damaged - beyond any channel layer",
     "hand off to {0}; note the missing-directory listing (ls -la on the "
     "root) in the evidence list".format(HANDOFF_SKILLS["os_fault"])),
)


def explain_text(text):
    """Return (hint lines, action lines) for pasted customer output.
    Pure function over the supplied text; never invents content."""
    hints, actions = [], []
    lowered = (text or "").lower()
    if not lowered.strip():
        return hints, actions
    for name, patterns, verdict, action in EXPLAIN_RULES:
        for pat in patterns:
            if re.search(pat, lowered):
                hints.append("[{0}] {1}".format(name, verdict))
                actions.append(action)
                break
    # df numeric usage needs its own look (percent columns are noisy).
    m = re.search(r"(\d{2,3})%", lowered)
    if m and int(m.group(1)) >= FS_FULL_PCT and "df-full" not in \
            "".join(hints):
        hints.append("[df-usage] the pasted reading carries {0}% "
                     "utilization".format(m.group(1)))
    return hints, dedupe(actions)


# Inline boundary assertions for explain_text: hit, miss and empty inputs.
assert explain_text("df: /dev/vda1 100% used")[0][0].startswith("[df-full]")
assert explain_text("ssh: connect: Connection refused")[0][0].startswith(
    "[no-listener]")
assert explain_text("hello world") == ([], [])
assert explain_text("") == ([], [])


def run_explain(args):
    if args.paste == "-":
        text = sys.stdin.read()
    else:
        try:
            with open(args.paste, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            print("[ERROR] cannot read pasted text: {0}".format(exc),
                  file=sys.stderr)
            print("STATUS: FAIL")
            print("NEXT_ACTION: pass the text on stdin: "
                  "scripts/areas/console_channel_diagnosis/console_channel_diagnosis.py explain --paste -")
            return 1
    hints, actions = explain_text(text)
    print("=" * 72)
    print("Offline interpretation of pasted output (no cloud calls)")
    print("=" * 72)
    if not hints:
        print("no known channel-layer pattern matched the pasted text")
        print("NEXT_ACTION: ask for the verbatim error line or a VNC "
              "screenshot description; text interpretation stays honest")
        print("STATUS: OK")
        return 0
    for line in hints:
        print("- " + line)
    print("\nSuggested routing:")
    for line in actions:
        print("- " + line)
    print("STATUS: OK")
    print("NEXT_ACTION: fold these readings into the layered report; they "
          "are readings OF the customer's paste, not cloud evidence")
    return 0


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="console_channel_diagnosis.py",
        description="Layered diagnosis of ECS console connection channels "
                    "(VNC / management terminal / Workbench / session "
                    "manager).")
    sub = parser.add_subparsers(dest="cmd")
    sub.required = True

    p_auth = sub.add_parser("check-auth", help="credential preflight")
    p_auth.add_argument("--profile")
    p_auth.set_defaults(func=run_check_auth)

    p_diag = sub.add_parser(
        "diagnose", help="full layered evidence chain")
    p_diag.add_argument("--region-id", required=True)
    p_diag.add_argument("--instance-id", required=True)
    p_diag.add_argument("--channel", choices=CHANNEL_CHOICES,
                        default="unknown",
                        help="the console channel the customer tried")
    p_diag.add_argument("--symptom", choices=SYMPTOM_CHOICES,
                        default="unknown",
                        help="what the customer's screen actually does")
    p_diag.add_argument("--error-text", default="",
                        help="verbatim error wording, normalized to English")
    p_diag.add_argument("--service-port", type=int, default=None,
                        help="the application/ssh port in question")
    p_diag.add_argument("--alt-channel-works", action="store_true",
                        help="another console channel still works")
    p_diag.add_argument("--local-channel-fails", action="store_true",
                        help="the customer's own ssh/RDP path fails meanwhile")
    p_diag.add_argument("--third-party-network", action="store_true",
                        help="tunnel software (Tailscale-class) reported in "
                             "the guest")
    p_diag.add_argument("--session-drop", action="store_true",
                        help="terminal disconnects kill running tasks")
    p_diag.add_argument("--profile")
    p_diag.add_argument("--json", action="store_true")
    p_diag.set_defaults(func=run_diagnose)

    p_probe = sub.add_parser(
        "guest-probe", help="ONE whitelisted non-mutating guest command "
                            "(confirmation gate)")
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

    p_expl = sub.add_parser(
        "explain", help="interpret pasted customer/channel output offline")
    p_expl.add_argument("--paste", default="-",
                        help="path to a text file, or - for stdin")
    p_expl.set_defaults(func=run_explain)
    return parser


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


# ---------------------------------------------------------------------------
# Offline regression lock (no cloud, no subprocess): run with
#   python3 scripts/areas/console_channel_diagnosis/console_channel_diagnosis.py --selftest
# Locks the layered verdict engine: a wrong verdict sends the customer to the
# wrong handoff (blaming a channel that is fine, or missing a real hang). The
# load-bearing invariant pinned here is fail-closed on a MISSING cloud-assistant
# reading -- an unknown agent status must never be reported as "not reporting
# online" to justify a hang verdict (fixed this round).
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

    def codes(store, f):
        return [v["code"] for v in classify(store, f)]

    def facts(**kw):
        base = {"channel": "", "symptom": "", "error_text": "", "patterns": [],
                "service_port": None, "alt_channel_works": False,
                "local_channel_fails": False, "third_party_network": False,
                "session_drop": False}
        base.update(kw)
        return base

    # --- parse_utc / heartbeat_age_minutes ---------------------------------
    expect("utc_ok", parse_utc("2026-02-10T10:00:00Z")
           is not None)
    expect("utc_reject_naive", parse_utc("2026-02-10 10:00") is None)
    expect("utc_reject_garbage", parse_utc("x") is None
           and parse_utc("") is None and parse_utc(None) is None)
    expect("hb_future_zero",
           heartbeat_age_minutes("2999-01-01T00:00:00Z") == 0.0)
    expect("hb_past_positive",
           heartbeat_age_minutes("2000-01-01T00:00:00Z") > 0)
    expect("hb_unparsable_none", heartbeat_age_minutes("nope") is None)

    # --- match_error_patterns ----------------------------------------------
    expect("pat_refused", "connection_refused" in match_error_patterns(
        "ssh: connect to host 1.2.3.4 port 22: Connection refused"))
    expect("pat_none_empty", match_error_patterns("") == [])
    expect("pat_multi", sorted(match_error_patterns(
        "InvalidDependence.GrantAccess, Connection refused"))
        == ["connection_refused", "grant_access_dependence"])

    # --- metric_value / saturation_evidence --------------------------------
    st = {"metrics": {"CPUUtilization": {"result": {"value": "97.5"}}}}
    expect("mv_str_cast", metric_value(st, "CPUUtilization") == 97.5)
    expect("mv_absent_none", metric_value({}, "CPUUtilization") is None)
    expect("mv_null_result_none",
           metric_value({"metrics": {"X": {"result": None}}}, "X") is None)
    sat = {"instance": {"cpu": 2},
           "metrics": {"CPUUtilization": {"result": {"value": 90.0}},
                       "memory_usedutilization": {"result": {"value": 89.9}},
                       "load_1m": {"result": {"value": 4.0}}}}
    expect("sat_cpu_at_threshold",
           "CPUUtilization=90.0%" in saturation_evidence(sat))
    expect("sat_mem_below_quiet",
           not any("memory" in x for x in saturation_evidence(sat)))
    expect("sat_load_2x_vcpu", any("load_1m" in x for x in saturation_evidence(sat)))
    expect("sat_no_metrics_quiet",
           saturation_evidence({"instance": {"cpu": 2}, "metrics": {}}) == [])
    # thresholds must stay quiet JUST below the line, both directions
    below = {"instance": {"cpu": 2},
             "metrics": {"CPUUtilization": {"result": {"value": 89.9}},
                         "load_1m": {"result": {"value": 3.0}}}}
    expect("sat_just_below_quiet", saturation_evidence(below) == [])

    # --- classify precedence ------------------------------------------------
    running_ca_off = {"instance": {"status": "Running", "cpu": 2},
                      "cloud_assistant": {"installed": True, "heartbeat_fresh": False},
                      "health": {}}
    expect("cls_stopped_not_running",
           codes({"instance": {"status": "Stopped"}, "health": {}},
                 facts(symptom="cannot-open")) == [VERDICT_NOT_RUNNING])
    expect("cls_stopping_power",
           codes({"instance": {"status": "Stopping"}, "health": {}},
                 facts()) == [VERDICT_POWER_TRANSITION])
    expect("cls_grant_shortcircuit",
           codes({"instance": {"status": "Running", "cpu": 2},
                  "cloud_assistant": {"installed": True, "heartbeat_fresh": True},
                  "health": {}},
                 facts(patterns=["grant_access_dependence"]))
           == [VERDICT_GRANT_DEPENDENCE])
    # anti-regression (this round's fix): an UNKNOWN agent (cloud_assistant key
    # absent because the query failed / no row) must NOT be turned into a hang
    # verdict claiming the agent "is not reporting online".
    store_unknown = {"instance": {"status": "Running", "cpu": 2}, "health": {}}
    expect("invariant_unknown_agent_never_hang",
           VERDICT_SATURATION_HANG not in
           codes(store_unknown, facts(symptom="blocked")))
    # a KNOWN-offline agent with a hang symptom still yields the hang verdict
    expect("known_offline_agent_hang",
           VERDICT_SATURATION_HANG in
           codes(running_ca_off, facts(symptom="blocked")))
    expect("cls_saturation_high",
           any(v["code"] == VERDICT_SATURATION_HANG and v["confidence"] == "high"
               for v in classify(
                   {"instance": {"status": "Running", "cpu": 2},
                    "metrics": {"CPUUtilization": {"result": {"value": 99}},
                                "memory_usedutilization": {"result": {"value": 95}}},
                    "cloud_assistant": {"installed": True, "heartbeat_fresh": False},
                    "health": {}}, facts(symptom="blocked"))))
    expect("cls_local_path",
           VERDICT_LOCAL_PATH in codes(
               {"instance": {"status": "Running", "cpu": 2},
                "cloud_assistant": {"installed": True, "heartbeat_fresh": True},
                "health": {"health_status": "Ok", "scheduled_events": []}},
               facts(local_channel_fails=True, alt_channel_works=True)))
    expect("cls_session_drop",
           VERDICT_SESSION_CHANNEL_LIMIT in codes(
               {"instance": {"status": "Running", "cpu": 2},
                "cloud_assistant": {"installed": True, "heartbeat_fresh": True},
                "health": {}}, facts(session_drop=True)))
    expect("cls_entry_guide",
           codes({"instance": {"status": "Running", "cpu": 2},
                  "cloud_assistant": {"installed": True, "heartbeat_fresh": True},
                  "health": {}},
                 facts(symptom="entry-question")) == [VERDICT_ENTRY_GUIDE])
    expect("cls_all_green",
           codes({"instance": {"status": "Running", "cpu": 2},
                  "cloud_assistant": {"installed": True, "heartbeat_fresh": True},
                  "health": {"health_status": "Ok", "scheduled_events": []}},
                 facts()) == [VERDICT_ALL_GREEN])

    # --- validate_guest_command (frozen whitelist, fail closed) --------------
    expect("vgc_exact", validate_guest_command("df -h", "linux") == "df -h")
    expect("vgc_family_path",
           validate_guest_command("ls -la /var/log", "linux") == "ls -la /var/log")
    for bad, why in (("df -h; rm -rf /", "composition"),
                     ("cat /etc/ssh/sshd_config", "ssh-fragment"),
                     ("uptime", "not-listed"),
                     ("", "empty")):
        try:
            validate_guest_command(bad, "linux")
            expect("vgc_refuse_" + why, False)
        except ValueError:
            expect("vgc_refuse_" + why, True)
    expect("vgc_windows", validate_guest_command("Get-Volume", "windows")
           == "Get-Volume")

    # --- dedupe --------------------------------------------------------------
    expect("dedupe_order", dedupe(["b", "a", "b", "c", "a"]) == ["b", "a", "c"])
    expect("dedupe_empty", dedupe([]) == [])

    print(f"--selftest: {len(checked)} checks, "
          f"{'ALL PASS' if rc == 0 else 'FAILURES PRESENT'}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
