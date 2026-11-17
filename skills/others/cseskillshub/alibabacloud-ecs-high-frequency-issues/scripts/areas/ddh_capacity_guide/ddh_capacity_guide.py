#!/usr/bin/env python3
"""
ddh_capacity_guide.py -- single entry point for the ECS DDH / Capacity Guide
============================================================================
SECURITY: This skill is strictly READ-ONLY. It only calls read-only ECS
Describe APIs and STS GetCallerIdentity:

  * ecs DescribeInstances / DescribeInstanceStatus - instance facts
  * ecs DescribeInstanceHistoryEvents             - platform event record
                                                    (type / lifecycle status /
                                                    published / finish time)
  * ecs DescribeDedicatedHosts                    - Dedicated Host usage status
  * ecs DescribeDisks                             - disk inventory per instance
  * ecs DescribeDiskMonitorData                   - cloud-disk IOPS / BPS /
                                                    latency readings
  * sts GetCallerIdentity                         - account provenance label

The full set is enforced by the READ_ONLY_ACTIONS whitelist in `_cli.py`. It
NEVER creates, modifies, deletes, reboots, migrates or otherwise changes any
resource, it never calls RedeployInstance / ModifyInstanceDeployment (those are
described as customer self-service paths only), and it never executes commands
inside a guest. Credentials come exclusively from the aliyun CLI default
credential chain; this script never reads, prints or accepts AK/SK.

What it does (RO_QUERY main area: fetch facts -> apply official rules -> explain
the process and the next step):
  1. Pre-check account/region visibility of the target instance(s).
  2. Classify the instance family as shared / burstable / dedicated.
  3. Read the platform event record of the instance(s) and the Dedicated Host
     status, so a host event is interpreted from real data instead of memory.
  4. Read cloud-disk IOPS / BPS / latency for the storage-ceiling symptom.
  5. Route the customer's symptom to the matching official-rule guidance
     (host reboot / redeploy / disk-maintenance events, CPU contention /
     isolation selection, storage performance ceiling, DDH / capacity
     reservation, account visibility).
  6. Emit an evidence-based report that ends with STATUS / NEXT_ACTION, and on a
     permission failure print the missing read-only action plus the minimal
     policy snippet.

Anything the read-only APIs cannot see (per-process guest I/O, readings outside
the disk-monitor window, whether a host is about to fail) is stated honestly as
a limitation with the customer-side source of truth; the script never
fabricates such data.

Usage:
  python3 ddh_capacity_guide.py --region-id cn-hangzhou \
      --instance-id i-bp1xxxx [--instance-id i-bp2xxxx] \
      [--symptom "instance was rebooted by the underlying host"] [--json]
  python3 ddh_capacity_guide.py --region-id cn-hangzhou \
      --instance-type ecs.e-c1m2.xlarge --symptom "shared CPU contention"
  python3 ddh_capacity_guide.py --region-id cn-hangzhou \
      --instance-id i-bp1xxxx --dedicated-host-id dh-bp1xxxx \
      --symptom "instance is Running but unresponsive, storage ceiling"
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

import _cli
from _constants import (
    ACCOUNT_VISIBILITY_GUIDANCE,
    CAPACITY_RESERVATION_GUIDANCE,
    DDH_GUIDANCE,
    DDH_MAX_RESULTS,
    DDH_STATUS_NOTES,
    DDH_STATUSES,
    EVENT_CYCLE_STATUSES,
    HISTORY_EVENT_MAX_RESULTS,
    HOST_EVENTS,
    HOST_MIGRATION_GUIDANCE,
    ISOLATION_SELECTION_GUIDANCE,
    MAINTENANCE_WINDOW_GUIDANCE,
    MAX_MONITORED_DISKS,
    MAX_PAGES,
    MONITOR_PERIOD_SECONDS,
    MONITOR_WINDOW_MINUTES,
    RAM_ACTION_BY_API,
    SLA_GUIDANCE,
    STORAGE_CEILING_GUIDANCE,
    SYMPTOM_ROUTES,
    classify_instance_family,
)

READ_ONLY_BANNER = "READ-ONLY SKILL - NO RESOURCE WAS CHANGED"


def _expand(values):
    """Flatten a list of possibly comma-separated values into clean tokens."""
    out = []
    for value in values or []:
        for part in str(value).split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out


def _warn(message, errors):
    """Log a degradation trace to stderr AND record it for the report."""
    print("[WARN] " + message, file=sys.stderr)
    errors.append(message)


# ---------------------------------------------------------------------------
# Permission-failure triage (BUG-28: the reference doc promises this output)
# ---------------------------------------------------------------------------
# Markers that identify a RAM / policy denial in an aliyun CLI error. The native
# codes are NoPermission and Forbidden.RAM; ImplicitDeny appears in policy
# evaluation text. Matching is case-insensitive on the code AND the message.
_PERMISSION_MARKERS = (
    "nopermission", "forbidden", "implicitdeny", "unauthorizedoperation",
    "accessdenied", "access denied", "not authorized", "denied by policy",
)


def is_permission_error(exc):
    """True when a CliError looks like a RAM / policy denial. Never raises."""
    code = str(getattr(exc, "code", "") or "")
    haystack = (code + " " + str(exc)).lower()
    return any(marker in haystack for marker in _PERMISSION_MARKERS)


def permission_literal(exc):
    """Return the canonical denial literal for the report (NoPermission/...)."""
    haystack = (str(getattr(exc, "code", "") or "") + " " + str(exc)).lower()
    if "nopermission" in haystack:
        return "NoPermission"
    if "implicitdeny" in haystack:
        return "ImplicitDeny"
    if "unauthorizedoperation" in haystack:
        return "UnauthorizedOperation"
    return "Forbidden"


def is_parameter_error(exc):
    """True when a CliError is a request-parameter rejection. Never raises.

    Verified behaviour: DescribeDedicatedHosts answers
    InvalidParameter.DedicatedHostIds for a host id that does not exist under the
    account, so retrying the same request with another status value would fail
    identically.
    """
    haystack = (str(getattr(exc, "code", "") or "") + " " + str(exc)).lower()
    return "invalidparameter" in haystack


def note_failure(action, exc, errors, permission_gaps):
    """Record one failed read-only call; print NoPermission for policy denials.

    The [WARN] line keeps the existing degradation contract (STATUS is derived
    from `errors` exactly as before); when the failure is a permission denial an
    extra `NoPermission: <ram action>` line is emitted and the gap is recorded so
    the report can print the minimal read-only policy snippet.
    """
    code = getattr(exc, "code", "") or "unknown"
    _warn(action + " failed (" + code + "): " + str(exc), errors)
    if not is_permission_error(exc):
        return
    ram_action = RAM_ACTION_BY_API.get(action, "ecs:" + action)
    literal = code if (code and code != "unknown") else permission_literal(exc)
    if ram_action not in [gap["action"] for gap in permission_gaps]:
        permission_gaps.append({
            "action": ram_action,
            "api": action,
            "error_code": literal,
        })
    print("NoPermission: " + ram_action, file=sys.stderr)


def build_minimal_policy(permission_gaps):
    """Return the minimal read-only policy that clears the recorded gaps."""
    actions = []
    for gap in permission_gaps:
        if gap["action"] not in actions:
            actions.append(gap["action"])
    if not actions:
        return None
    return {
        "Version": "1",
        "Statement": [
            {"Effect": "Allow", "Action": actions, "Resource": "*"},
        ],
    }


def _dig(obj, path):
    """Walk a nested dict along `path`; return None on any miss."""
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _text(value):
    """Best-effort scalar from a CLI field (the CLI renders empty enums as {})."""
    if isinstance(value, dict):
        return str(value.get("Name") or value.get("Code") or "")
    if value is None:
        return ""
    return str(value)


def fetch_instances(region, instance_ids, profile, errors, permission_gaps):
    """Read-only DescribeInstances for the given ids. Returns (instances, ok).

    `ok` is False only when the API call itself failed (permission / network);
    an empty result is a VALID finding (not visible under this account/region),
    so it returns ([], True).
    """
    params = {"RegionId": region}
    if instance_ids:
        params["InstanceIds"] = json.dumps(instance_ids)
    try:
        instances = _cli.paginate_pages(
            "ecs", "DescribeInstances", params, region=region, profile=profile,
            items_path=["Instances", "Instance"],
        )
        return instances, True
    except _cli.CliError as exc:
        note_failure("DescribeInstances", exc, errors, permission_gaps)
        return [], False


def fetch_statuses(region, instance_ids, profile, errors, permission_gaps):
    """Read-only DescribeInstanceStatus cross-check. Returns (statuses, ok)."""
    if not instance_ids:
        return [], True
    params = {"RegionId": region}
    for idx, iid in enumerate(instance_ids, 1):
        params["InstanceId." + str(idx)] = iid
    try:
        statuses = _cli.paginate_pages(
            "ecs", "DescribeInstanceStatus", params, region=region,
            profile=profile, items_path=["InstanceStatuses", "InstanceStatus"],
            # DescribeInstanceStatus caps PageSize at 50 (DescribeInstances
            # allows 100); sending the generic PAGE_SIZE=100 makes the API
            # reject the call with InvalidParameter "PageSize is not valid".
            page_size=50,
        )
        return statuses, True
    except _cli.CliError as exc:
        note_failure("DescribeInstanceStatus", exc, errors, permission_gaps)
        return [], False


# ---------------------------------------------------------------------------
# Platform event record (DescribeInstanceHistoryEvents, read-only)
# ---------------------------------------------------------------------------

def _event_record(instance_id, row):
    """Normalise one InstanceSystemEventType row (only real fields are read)."""
    return {
        "instance_id": instance_id,
        "event_id": _text(row.get("EventId")),
        "event_type": _text(row.get("EventType")),
        "cycle_status": _text(row.get("EventCycleStatus")),
        "impact_level": _text(row.get("ImpactLevel")),
        "publish_time": _text(row.get("EventPublishTime")
                              or row.get("PublishTime")),
        "not_before": _text(row.get("NotBefore")),
        "finish_time": _text(row.get("EventFinishTime")),
        "reason": _text(row.get("Reason")),
    }


def fetch_history_events(region, instance_ids, profile, errors,
                         permission_gaps):
    """Read the platform event record per instance. Returns (events, ok).

    Every documented lifecycle status is sent explicitly, because the API
    otherwise returns finished (non-active) events only and a still-Scheduled
    maintenance event is exactly what the customer is asking about.
    """
    events = []
    ok = True
    for instance_id in instance_ids:
        page = 0
        next_token = ""
        while page < MAX_PAGES:
            params = {
                "RegionId": region,
                "InstanceId": instance_id,
                "MaxResults": HISTORY_EVENT_MAX_RESULTS,
            }
            for idx, status in enumerate(EVENT_CYCLE_STATUSES, 1):
                params["InstanceEventCycleStatus." + str(idx)] = status
            if next_token:
                params["NextToken"] = next_token
            try:
                body = _cli.call("ecs", "DescribeInstanceHistoryEvents", params,
                                 region=region, profile=profile)
            except _cli.CliError as exc:
                note_failure("DescribeInstanceHistoryEvents", exc, errors,
                             permission_gaps)
                ok = False
                break
            rows = _dig(body, ["InstanceSystemEventSet",
                               "InstanceSystemEventType"])
            if not isinstance(rows, list):
                rows = []
            for row in rows:
                if isinstance(row, dict):
                    events.append(_event_record(instance_id, row))
            next_token = _text(body.get("NextToken"))
            page += 1
            if not next_token or not rows:
                break
    return events, ok


# ---------------------------------------------------------------------------
# Dedicated Host status (DescribeDedicatedHosts, read-only)
# ---------------------------------------------------------------------------

def dedicated_host_ids_from_instances(instances):
    """Collect the Dedicated Host ids the instances actually report.

    DescribeInstances returns `DedicatedHostAttribute.DedicatedHostId` (empty
    string for a non-DDH instance), verified on a live response.
    """
    host_ids = []
    for inst in instances:
        host_id = _text(_dig(inst, ["DedicatedHostAttribute",
                                    "DedicatedHostId"]))
        if host_id and host_id not in host_ids:
            host_ids.append(host_id)
    return host_ids


def _host_record(row, queried_status):
    """Normalise one DedicatedHost row (only fields actually present)."""
    return {
        "dedicated_host_id": _text(row.get("DedicatedHostId")),
        "status": _text(row.get("Status")) or queried_status,
        "status_note": DDH_STATUS_NOTES.get(
            _text(row.get("Status")) or queried_status, ""),
        "zone_id": _text(row.get("ZoneId")),
        "host_type": _text(row.get("DedicatedHostType")),
        "host_name": _text(row.get("HostName")),
    }


def fetch_dedicated_hosts(region, host_ids, profile, errors, permission_gaps):
    """Read Dedicated Host usage status. Returns (hosts, ok).

    `Status` on this API is a single-value filter whose default is Available, so
    every documented value is queried explicitly: a host in UnderAssessment /
    PermanentFailure / TempUnavailable / Redeploying never appears otherwise.
    """
    hosts = []
    ok = True
    for status in DDH_STATUSES:
        params = {
            "RegionId": region,
            "MaxResults": DDH_MAX_RESULTS,
            "Status": status,
        }
        if host_ids:
            params["DedicatedHostIds"] = ",".join(host_ids)
        try:
            body = _cli.call("ecs", "DescribeDedicatedHosts", params,
                             region=region, profile=profile)
        except _cli.CliError as exc:
            note_failure("DescribeDedicatedHosts", exc, errors,
                         permission_gaps)
            ok = False
            if is_parameter_error(exc):
                # The request itself is rejected (for example a host id that
                # does not exist here); re-sending it with another status value
                # would fail identically, so stop instead of repeating it.
                break
            continue
        rows = _dig(body, ["DedicatedHosts", "DedicatedHost"])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            record = _host_record(row, status)
            if record["dedicated_host_id"] and record["dedicated_host_id"] in [
                    existing["dedicated_host_id"] for existing in hosts]:
                continue
            hosts.append(record)
    return hosts, ok


# ---------------------------------------------------------------------------
# Cloud-disk I/O readings (DescribeDisks + DescribeDiskMonitorData, read-only)
# ---------------------------------------------------------------------------

def fetch_disks(region, instance_ids, profile, errors, permission_gaps):
    """Read the disk inventory of the instances. Returns (disks, ok)."""
    disks = []
    ok = True
    for instance_id in instance_ids:
        params = {"RegionId": region, "InstanceId": instance_id}
        try:
            rows = _cli.paginate_pages(
                "ecs", "DescribeDisks", params, region=region, profile=profile,
                items_path=["Disks", "Disk"],
            )
        except _cli.CliError as exc:
            note_failure("DescribeDisks", exc, errors, permission_gaps)
            ok = False
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            disk_id = _text(row.get("DiskId"))
            if not disk_id:
                continue
            disks.append({
                "instance_id": instance_id,
                "disk_id": disk_id,
                "type": _text(row.get("Type")),
                "category": _text(row.get("Category")),
                "size_gib": _text(row.get("Size")),
                "status": _text(row.get("Status")),
            })
    return disks, ok


def _utc_minute_now():
    """Current UTC time truncated to the minute (the API's expected grain)."""
    return datetime.now(timezone.utc).replace(second=0, microsecond=0)


def _peak(rows, key):
    """Max integer value of `key` across the samples, or None when absent."""
    values = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            values.append(int(row.get(key)))
        except (TypeError, ValueError):
            continue
    return max(values) if values else None


def _last(row):
    """Return the last sample only if its TimeStamp is present (real field)."""
    if not isinstance(row, dict):
        return {}
    keys = ("TimeStamp", "IOPSTotal", "IOPSRead", "IOPSWrite", "BPSTotal",
            "BPSRead", "BPSWrite", "LatencyRead", "LatencyWrite")
    return {key: row[key] for key in keys if key in row}


def fetch_disk_monitor(region, disks, profile, errors, permission_gaps):
    """Read cloud-disk IOPS / BPS / latency for the recent window. Returns list.

    DescribeDiskMonitorData requires DiskId + StartTime + EndTime and caps
    (EndTime - StartTime) / Period at 400 points. Metrics are quoted exactly as
    returned: no ceiling comparison is invented.
    """
    readings = []
    if not disks:
        return readings
    end = _utc_minute_now()
    start = end - timedelta(minutes=MONITOR_WINDOW_MINUTES)
    time_format = "%Y-%m-%dT%H:%M:%SZ"
    for disk in disks[:MAX_MONITORED_DISKS]:
        params = {
            "RegionId": region,
            "DiskId": disk["disk_id"],
            "StartTime": start.strftime(time_format),
            "EndTime": end.strftime(time_format),
            "Period": str(MONITOR_PERIOD_SECONDS),
        }
        try:
            body = _cli.call("ecs", "DescribeDiskMonitorData", params,
                             region=region, profile=profile)
        except _cli.CliError as exc:
            note_failure("DescribeDiskMonitorData", exc, errors,
                         permission_gaps)
            continue
        rows = _dig(body, ["MonitorData", "DiskMonitorData"])
        if not isinstance(rows, list):
            rows = []
        readings.append({
            "disk_id": disk["disk_id"],
            "instance_id": disk.get("instance_id"),
            "category": disk.get("category"),
            "size_gib": disk.get("size_gib"),
            "window": {
                "start": params["StartTime"],
                "end": params["EndTime"],
                "period_seconds": MONITOR_PERIOD_SECONDS,
            },
            "sample_count": len(rows),
            "peak": {
                "iops_total": _peak(rows, "IOPSTotal"),
                "bps_total": _peak(rows, "BPSTotal"),
                "latency_read_us": _peak(rows, "LatencyRead"),
                "latency_write_us": _peak(rows, "LatencyWrite"),
            },
            "last_sample": _last(rows[-1]) if rows else {},
        })
    return readings


def route_symptom(symptom_text):
    """Return the ordered list of guidance route keys matched by the symptom."""
    text = (symptom_text or "").lower()
    matched = []
    for keywords, route in SYMPTOM_ROUTES:
        if any(kw in text for kw in keywords):
            if route not in matched:
                matched.append(route)
    return matched


def build_guidance(routes, classifications, instance_visible, queried_api):
    """Assemble the rule-based guidance blocks for the matched routes."""
    guidance = []

    if "host_event" in routes:
        for event_name, event in HOST_EVENTS.items():
            guidance.append(event_name + " (" + event["title"] + "): "
                            + event["explanation"])
        guidance.append("SLA claim: " + SLA_GUIDANCE)
        guidance.append("Maintenance window: " + MAINTENANCE_WINDOW_GUIDANCE)
        guidance.append("Host migration: " + HOST_MIGRATION_GUIDANCE)

    if "isolation" in routes or (not routes and classifications):
        guidance.append("Isolation selection: " + ISOLATION_SELECTION_GUIDANCE)

    if "storage_ceiling" in routes:
        guidance.append("Storage performance ceiling: " + STORAGE_CEILING_GUIDANCE)

    if "ddh_capacity" in routes or not routes:
        guidance.append("Dedicated Host (DDH): " + DDH_GUIDANCE)
        guidance.append("Capacity reservation / elasticity assurance: "
                        + CAPACITY_RESERVATION_GUIDANCE)

    if "visibility" in routes or (queried_api and not instance_visible):
        guidance.append("Account / region visibility: "
                        + ACCOUNT_VISIBILITY_GUIDANCE)

    # De-duplicate while preserving order.
    seen = set()
    unique = []
    for item in guidance:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def main():
    parser = argparse.ArgumentParser(
        description="Read-only ECS Dedicated Host (DDH) / capacity reservation "
                    "guide: instance-family isolation classification, host "
                    "event / Dedicated Host status / cloud-disk I/O evidence, "
                    "and capacity selection guidance.",
    )
    parser.add_argument("--region-id", required=True,
                        help="Region of the target instance(s), e.g. "
                             "cn-hangzhou (REQUIRED by the ECS Describe APIs)")
    parser.add_argument("--instance-id", action="append", default=[],
                        help="Target instance id (repeatable or comma-separated)")
    parser.add_argument("--instance-type", action="append", default=[],
                        help="Instance type to classify without an API call, "
                             "e.g. ecs.e-c1m2.xlarge (repeatable / "
                             "comma-separated)")
    parser.add_argument("--dedicated-host-id", action="append", default=[],
                        help="Optional Dedicated Host id (repeatable / "
                             "comma-separated) to read host status for; when "
                             "omitted, the host ids reported by the instances "
                             "are used")
    parser.add_argument("--symptom", default="",
                        help="The customer's own wording, used to route to the "
                             "matching official-rule guidance")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    region = args.region_id.strip()
    instance_ids = _expand(args.instance_id)
    instance_types = _expand(args.instance_type)
    dedicated_host_ids = _expand(args.dedicated_host_id)
    symptom = (args.symptom or "").strip()
    errors = []
    permission_gaps = []

    if not region:
        print("[ERROR] --region-id is required and must be non-empty.",
              file=sys.stderr)
        print("\nSTATUS: FAIL")
        print("NEXT_ACTION: ask the user for the region of the target "
              "instance(s) and re-run")
        sys.exit(1)

    _cli.check_cli_available()

    # Routing is decided BEFORE the evidence queries, because the matched
    # routes select which read-only sources are worth calling (host-event
    # routes -> event record + Dedicated Host status; storage-ceiling route ->
    # cloud-disk I/O readings).
    routes = route_symptom(symptom)

    # --- Identity label (auto-filled, never asked from the user) -------------
    uid = _cli.resolve_account_id(region=region, profile=args.profile)
    auto_filled = []
    if uid:
        auto_filled.append("Account UID auto-derived from the credential via "
                           "sts get-caller-identity: " + uid)
    else:
        auto_filled.append("Account UID could not be derived (identity check "
                           "failed); continuing with the read-only queries")

    # --- Evidence collection (read-only) ------------------------------------
    instances = []
    statuses = []
    events = []
    hosts = []
    disks = []
    io_readings = []
    queried_api = False
    instances_ok = True
    instance_visible = None  # None = not queried; True/False after a query
    host_query_attempted = False

    if instance_ids:
        queried_api = True
        instances, instances_ok = fetch_instances(region, instance_ids,
                                                  args.profile, errors,
                                                  permission_gaps)
        instance_visible = len(instances) > 0
        if instances_ok and not instances:
            _warn("DescribeInstances returned no instance for id(s) "
                  + ", ".join(instance_ids) + " in region " + region
                  + " under the current credential", errors)
        # Status cross-check (adds the running-state fact; degrades silently).
        _statuses, _statuses_ok = fetch_statuses(region, instance_ids,
                                                 args.profile, errors,
                                                 permission_gaps)
        statuses = _statuses

        # Platform event record for the instance(s): the evidence behind a
        # host reboot / redeploy / disk-maintenance notification.
        events, _events_ok = fetch_history_events(region, instance_ids,
                                                  args.profile, errors,
                                                  permission_gaps)

    # Dedicated Host status: queried when a host id is known or the symptom is
    # a host / DDH question. The API default status filter is Available only,
    # so every documented value is read inside the helper.
    target_host_ids = list(dedicated_host_ids)
    for host_id in dedicated_host_ids_from_instances(instances):
        if host_id not in target_host_ids:
            target_host_ids.append(host_id)
    host_query_wanted = bool(target_host_ids) or (
        bool(instance_ids) and ("host_event" in routes
                                or "ddh_capacity" in routes))
    if host_query_wanted:
        host_query_attempted = True
        hosts, _hosts_ok = fetch_dedicated_hosts(region, target_host_ids,
                                                 args.profile, errors,
                                                 permission_gaps)

    # Cloud-disk I/O readings: the evidence behind a "Running but unresponsive
    # at the storage ceiling" symptom.
    if instance_ids and "storage_ceiling" in routes:
        disks, _disks_ok = fetch_disks(region, instance_ids, args.profile,
                                       errors, permission_gaps)
        io_readings = fetch_disk_monitor(region, disks, args.profile, errors,
                                         permission_gaps)

    # --- Classification (pure knowledge; works with or without API data) ----
    classifications = []
    for inst in instances:
        itype = str(inst.get("InstanceType") or "")
        klass, family, note = classify_instance_family(itype)
        classifications.append({
            "instance_id": inst.get("InstanceId"),
            "instance_type": itype,
            "status": inst.get("Status"),
            "zone_id": inst.get("ZoneId"),
            "family": family,
            "class": klass,
            "note": note,
        })
    for itype in instance_types:
        klass, family, note = classify_instance_family(itype)
        classifications.append({
            "instance_id": None,
            "instance_type": itype,
            "status": None,
            "zone_id": None,
            "family": family,
            "class": klass,
            "note": note,
        })

    # --- Routing + guidance --------------------------------------------------
    guidance = build_guidance(routes, classifications, instance_visible,
                              queried_api)
    minimal_policy = build_minimal_policy(permission_gaps)

    limitations = [
        "CONNECTED (read-only): the platform event record of the queried "
        "instance(s) is read with DescribeInstanceHistoryEvents (event type, "
        "lifecycle status, publish / scheduled / finish time) and Dedicated "
        "Host usage status is read with DescribeDedicatedHosts (Available / "
        "UnderAssessment / PermanentFailure - the only three status values the "
        "service accepts; TempUnavailable and Redeploying are documented in the "
        "CLI help but rejected by the live API, so they are never reported as "
        "checked). Cloud-disk IOPS / BPS / latency for the recent window is "
        "read with DescribeDiskMonitorData. These are quoted as returned; no "
        "reading is inferred.",
        "NOT AVAILABLE: per-process guest I/O, guest-internal performance "
        "history, and any reading outside the cloud-disk monitor window. The "
        "source of truth there is the customer's own atop / iostat output or "
        "the CloudMonitor chart in the ECS console, which the customer can "
        "paste or screenshot for interpretation. A missing instance event "
        "record does not prove the host was healthy - it only means no "
        "matching event is visible under this account and region.",
        "NEVER PERFORMED: host migration (RedeployInstance / "
        "ModifyInstanceDeployment), forced reboot, snapshot creation and any "
        "configuration change are customer self-service or console actions "
        "explained by this skill and never executed by it.",
    ]

    suggestions = [
        "Explain the conclusion strictly from the facts above and the official "
        "rules; state the account UID and region that were queried.",
        "When the evidence contains an event record, name the event type and "
        "its lifecycle status, then give the matching official explanation. "
        "When it contains disk I/O readings, quote the measured peak and the "
        "window instead of describing a limit from memory.",
        "For any redeploy / migration / reconfiguration, give the risk notice "
        "and the self-service console steps (or the documented operation name) "
        "for the customer to perform, or hand off to a human support ticket "
        "when the platform must investigate the host itself; never claim an "
        "action was completed.",
        "If the instance was not visible, re-check with the owning account's "
        "credential and the correct region before concluding.",
    ]

    # --- STATUS determination ------------------------------------------------
    if not instance_ids and not instance_types and not symptom:
        status = "FAIL"
        next_action = ("ask the user for the region plus at least one of: "
                       "instance id(s), instance type, or the symptom wording")
    elif queried_api and not instances_ok:
        status = "DEGRADED"
        next_action = ("report the read-only query failure as a limitation, "
                       "relay the rule-based guidance, and - when the failure "
                       "is a permission denial - relay the printed NoPermission "
                       "action plus the minimal read-only policy before asking "
                       "for anything else")
    elif errors:
        status = "DEGRADED"
        next_action = ("relay the findings and the recorded [WARN] degradations, "
                       "then give the rule-based guidance and next steps")
    else:
        status = "OK"
        next_action = ("relay the facts, the event record, the host status, the "
                       "disk I/O readings, the family classification and the "
                       "matched official-rule guidance; declare the auto-filled "
                       "UID and region")

    summary = (
        "Read-only DDH / capacity guide for region " + region + ". "
        + ("Queried " + str(len(instance_ids)) + " instance id(s); "
           + ("found " + str(len(instances)) + " visible."
              if queried_api else "no API query needed."))
        + " Platform events: " + str(len(events)) + ". "
        + ("Dedicated Hosts: " + str(len(hosts)) + " (status values queried: "
           + ", ".join(DDH_STATUSES) + "). " if host_query_attempted else "")
        + ("Cloud-disk I/O series: " + str(len(io_readings)) + ". "
           if io_readings else "")
        + "Classified " + str(len(classifications)) + " instance type(s). "
        + "Matched guidance route(s): "
        + (", ".join(routes) if routes else "general capacity/isolation")
        + ". This skill changed nothing."
    )

    if args.json:
        print(json.dumps({
            "status": status,
            "next_action": next_action,
            "summary": summary,
            "uid": uid,
            "region": region,
            "auto_filled": auto_filled,
            "instances": instances,
            "instance_statuses": statuses,
            "instance_history_events": events,
            "dedicated_hosts": hosts,
            "disks": disks,
            "disk_monitor_readings": io_readings,
            "classifications": classifications,
            "matched_routes": routes,
            "guidance": guidance,
            "limitations": limitations,
            "suggestions": suggestions,
            "permission_gaps": permission_gaps,
            "minimal_readonly_policy": minimal_policy,
            "errors": errors,
        }, indent=2, ensure_ascii=False))
    else:
        print("=" * 72)
        print(READ_ONLY_BANNER)
        print("=" * 72)
        print("\nSummary")
        print("-------")
        print(summary)
        print("\nScope / provenance")
        print("------------------")
        for line in auto_filled:
            print("  - " + line)
        print("  - Region queried: " + region)
        if classifications:
            print("\nInstance-family classification")
            print("------------------------------")
            for item in classifications:
                ident = item["instance_id"] or "(type only)"
                print("  - " + str(ident) + "  " + str(item["instance_type"])
                      + "  -> " + item["class"].upper()
                      + (" [family " + item["family"] + "]" if item["family"]
                         else ""))
                print("      " + item["note"])
                if item["status"]:
                    print("      status: " + str(item["status"]))
        if instance_ids:
            print("\nPlatform event record (DescribeInstanceHistoryEvents, "
                  "read-only)")
            print("-" * 62)
            if events:
                for event in events:
                    print("  - " + str(event["instance_id"]) + "  "
                          + (event["event_type"] or "(type not returned)")
                          + "  [" + (event["cycle_status"] or "status n/a")
                          + "]")
                    for label, key in (
                            ("event_id", "event_id"),
                            ("published", "publish_time"),
                            ("scheduled (NotBefore)", "not_before"),
                            ("finished", "finish_time"),
                            ("reason", "reason")):
                        if event[key]:
                            print("      " + label + ": " + event[key])
                    rule = HOST_EVENTS.get(event["event_type"])
                    if rule:
                        print("      official rule: " + rule["title"])
            else:
                print("  - no platform event record is visible for the queried "
                      "instance(s) under this account and region (this does "
                      "not prove the host was healthy)")
        if host_query_attempted:
            print("\nDedicated Host status (DescribeDedicatedHosts, read-only)")
            print("-" * 56)
            if hosts:
                for host in hosts:
                    print("  - " + (host["dedicated_host_id"] or "(id not "
                          "returned)") + "  " + (host["status"] or "status n/a")
                          + (": " + host["status_note"]
                             if host["status_note"] else ""))
                    details = []
                    for label, key in (("zone", "zone_id"),
                                       ("type", "host_type"),
                                       ("name", "host_name")):
                        if host[key]:
                            details.append(label + "=" + host[key])
                    if details:
                        print("      " + "  ".join(details))
            else:
                print("  - no Dedicated Host is visible in region " + region
                      + " under this account for any queried status ("
                      + ", ".join(DDH_STATUSES) + ")")
            if target_host_ids:
                print("  - host id(s) taken from the instance data / "
                      "--dedicated-host-id: " + ", ".join(target_host_ids))
        if io_readings:
            print("\nCloud-disk I/O readings (DescribeDiskMonitorData, "
                  "read-only)")
            print("-" * 56)
            for reading in io_readings:
                print("  - " + reading["disk_id"]
                      + (" (" + reading["category"] + ", "
                         + reading["size_gib"] + " GiB)"
                         if reading["category"] else "")
                      + "  window " + reading["window"]["start"] + " ~ "
                      + reading["window"]["end"] + " @"
                      + str(reading["window"]["period_seconds"]) + "s")
                peaks = []
                for label, key in (("peak IOPS (total)", "iops_total"),
                                   ("peak BPS (total)", "bps_total"),
                                   ("peak read latency (us)",
                                    "latency_read_us"),
                                   ("peak write latency (us)",
                                    "latency_write_us")):
                    if reading["peak"][key] is not None:
                        peaks.append(label + "=" + str(reading["peak"][key]))
                print("      samples=" + str(reading["sample_count"])
                      + ("  " + "  ".join(peaks) if peaks else
                         "  (no sample returned for this window)"))
        print("\nOfficial-rule guidance")
        print("----------------------")
        for item in guidance:
            print("  - " + item)
        print("\nLimitations (what is connected, unavailable, never done)")
        print("-------------------------------------------------------")
        for item in limitations:
            print("  - " + item)
        print("\nSuggestions (manual guidance only)")
        print("----------------------------------")
        for item in suggestions:
            print("  - " + item)
        if permission_gaps:
            print("\nPermission gaps (read-only actions only)")
            print("----------------------------------------")
            for gap in permission_gaps:
                print("NoPermission: " + gap["action"]
                      + "    (" + gap["api"] + ", error "
                      + str(gap["error_code"]) + ")")
            print("Minimal read-only policy snippet that clears them "
                  "(grant to the caller's RAM user / role):")
            print(json.dumps(minimal_policy, indent=2, ensure_ascii=False))
        if errors:
            print("\nGraceful Degradation Log")
            print("------------------------")
            for item in errors:
                print("  - [WARN] " + item)

    print("\nSTATUS: " + status)
    print("NEXT_ACTION: " + next_action)
    if status == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
