#!/usr/bin/env python3
"""
host_intrusion_diagnosis.py -- single entry point of the skill
================================================================
SECURITY / EXECUTION MODEL (enforced in code, not only in prose):

* Layer 1 -- automatic cloud evidence queries: inquiry actions only
  (identity, Security Center alerts / version / asset statistics /
  exposure surface, CloudMonitor CPU, snapshot inventory, Cloud Backup
  restore-job records).
* Layer 2 -- gated in-guest forensics: dispatches EXACTLY ONE command
  from the frozen four-category whitelist in _constants.GUEST_COMMANDS
  (process state / connection state / scheduled tasks / startup items)
  into the guest through Cloud Assistant, and reads the output back.
  Runs only when the operator passed --confirmed AFTER telling the
  customer the exact command, its scope and that it changes nothing.
  Confirmation is valid for this single run only.
* Layer 3 -- gated evidence snapshot: the single low-risk reversible
  write (snapshot-first before any cleanup or handling guidance). Runs
  only with --confirmed after the customer accepted the billing notice.
* Anything outside ALLOWED_ACTIONS -- deleting/quarantining files,
  killing processes, rolling back disks, replacing systems, editing
  security groups, unblock appeals -- can never leave this host: the
  shared CLI layer refuses it. Such operations appear in the report as
  customer-executed only (console or the equivalent OpenAPI).

Credentials come exclusively from the aliyun CLI default credential chain;
this script never reads, prints or passes credential values.

Output contract: human-readable report (default) or --json; every run ends
with `STATUS: OK|DEGRADED|FAIL` and `NEXT_ACTION: ...`.
Exit codes: 0 = OK/DEGRADED conclusion produced; 1 = FAIL (missing input,
unmet confirmation gate, or credentials unusable); 2 = argparse usage error.

Usage examples:
  python3 scripts/areas/host_intrusion_cleanup/host_intrusion_diagnosis.py \
      --region-id cn-hangzhou --instance-id i-2zexxxxxxxxxxxxxxx
  python3 scripts/areas/host_intrusion_cleanup/host_intrusion_diagnosis.py \
      --region-id cn-hangzhou --public-ip 47.120.48.210 \
      --incident-time "2026-08-20 03:10" --symptom "files encrypted"
  python3 scripts/areas/host_intrusion_cleanup/host_intrusion_diagnosis.py \
      --region-id cn-hangzhou --instance-id i-2zexxxxxxxxxxxxxxx \
      --guest-check connections --confirmed
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import _cli
from _constants import (
    ALERT_CATEGORY_ANCHORS,
    BACKUP_RETENTION_NOTICE,
    BRANCH_LABELS,
    CMS_CPU_SUSPECT_PERCENT,
    CMS_METRICS,
    CMS_NAMESPACE,
    DISK_RE,
    ENCRYPTED_STATE_SNAPSHOT_NOTICE,
    ENTRY_VECTOR_HINTS,
    FALLBACK_READINGS,
    GUEST_COMMANDS,
    GUEST_COMMAND_CATEGORIES,
    HANDOFF_TARGETS,
    HARDENING_CHECKLIST,
    HBR_PAGE_SIZE,
    HBR_RESTORE_EDITIONS,
    HBR_RESTORE_TYPE,
    INSTANCE_RE,
    INVOCATION_POLL_INTERVAL_SECONDS,
    INVOCATION_POLL_MAX,
    IPV4_RE,
    MAX_PAGES,
    PAGE_SIZE,
    RECURRENCE_NOTICE,
    REGION_RE,
    RECOVERY_UNCERTAIN_NOTICE,
    ROLLBACK_MANUAL_NOTICE,
    SHARED_RESPONSIBILITY_NOTICE,
    SNAPSHOT_BILLING_NOTICE,
    SNAPSHOT_FIRST_RULE,
    SYMPTOM_ANCHORS,
)

_ISO_Z_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?)\s*Z$",
                       re.IGNORECASE)

_TERMINAL_INVOCATION_STATES = {"Finished", "Failed", "Stopped", "Timeout",
                               "PartialFailed", "Error", "Success"}


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested in _self_test)
# ---------------------------------------------------------------------------

def parse_iso_time(value, now=None):
    """Parse 'YYYY-MM-DD HH:MM[:SS]', optional T separator and trailing Z,
    or a unix timestamp. Returns (datetime, tz_flagged); naive -> UTC + False.
    Raises ValueError on unparseable input (never guesses)."""
    if value is None or not str(value).strip():
        raise ValueError("empty time value")
    raw = str(value).strip()
    if raw.isdigit():
        return datetime.fromtimestamp(int(raw), tz=timezone.utc), True
    tz_flagged = False
    m = _ISO_Z_RE.match(raw)
    if m:
        raw, tz_flagged = m.group(1), True
    dt = None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            break
        except ValueError:
            continue
    if dt is None:
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            raise ValueError(
                "unparseable time %r; use ISO 8601 "
                "(e.g. 2026-08-12 02:30 or 2026-08-12T02:30Z, epoch seconds "
                "also accepted)" % value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        return dt, tz_flagged
    return dt, True


def classify_symptom(text):
    """Map verbatim customer wording to a branch or handoff target.
    Returns (branch, anchor_entry). branch is one of the intrusion branches
    ('ransom', 'miner', 'webshell') or 'handoff'; else (None, None)."""
    low = (text or "").lower()
    for entry in SYMPTOM_ANCHORS:
        for anchor in entry["anchors"]:
            if anchor.lower() in low:
                return entry.get("branch"), entry
    return None, None


def classify_alert(item):
    """Classify one Security Center event into an intrusion branch by its
    name text. Returns (branch, matched_anchor). Never raises."""
    if not isinstance(item, dict):
        return "other", ""
    haystack = " ".join(str(item.get(k) or "") for k in
                        ("Name", "EventName", "AlarmEventName", "Remarks",
                         "Description", "Detail"))
    low = haystack.lower()
    for entry in ALERT_CATEGORY_ANCHORS:
        for anchor in entry["anchors"]:
            if anchor.lower() in low:
                return entry["branch"], anchor
    return "other", ""


def first_of(item, keys, default=""):
    """First present non-empty value among keys (tolerant field mapping:
    Security Center shapes vary across API generations; unknown fields are
    reported as the default, never invented)."""
    for key in keys:
        value = item.get(key) if isinstance(item, dict) else None
        if value not in (None, ""):
            return value
    return default


def alert_targets(item):
    """The identifying strings an alert row carries for host matching."""
    out = set()
    if not isinstance(item, dict):
        return out
    for key in ("InstanceId", "InternetIp", "IntranetIp", "Ip", "Uuid"):
        value = item.get(key)
        if isinstance(value, str) and value:
            out.add(value)
    inner = item.get("Instance")
    if isinstance(inner, dict):
        for key in ("InstanceId", "InternetIp", "IntranetIp"):
            value = inner.get(key)
            if isinstance(value, str) and value:
                out.add(value)
    return out


def alert_matches_target(item, instance_id, public_ip):
    targets = alert_targets(item)
    if instance_id and instance_id in targets:
        return True
    if public_ip and public_ip in targets:
        return True
    return False


def judge_recoverability(snapshots, incident_dt):
    """K4 mechanical verdict for the ransom branch. snapshots is the list of
    DescribeSnapshots records; incident_dt may be None.

    Returns a dict:
      verdict   : 'restorable' | 'no-window' | 'none-found'
      points    : usable snapshots (accomplished, at or before the incident
                  window), newest first
      latest    : per-disk latest accomplished snapshot (inventory context)
    Empty input is valid (an account with no snapshots is the single most
    common ransomware finding in this tier)."""
    usable = [s for s in snapshots if isinstance(s, dict)
              and str(s.get("Status", "")).lower() == "accomplished"]

    def creation(s):
        try:
            dt, _ = parse_iso_time(str(s.get("CreationTime", "")))
            return dt
        except ValueError:
            return None

    with_time = [s for s in usable if creation(s) is not None]
    by_newest = sorted(with_time, key=creation, reverse=True)

    latest_per_disk = {}
    for s in by_newest:
        disk = str(first_of(s, ("SourceDiskId", "DiskId"), "?"))
        latest_per_disk.setdefault(disk, s)

    if not by_newest:
        return {"verdict": "none-found", "points": [],
                "latest": list(latest_per_disk.values())}

    if incident_dt is None:
        return {"verdict": "no-window", "points": [],
                "latest": list(latest_per_disk.values())}

    points = [s for s in by_newest if creation(s) <= incident_dt]
    if points:
        return {"verdict": "restorable", "points": points,
                "latest": list(latest_per_disk.values())}
    return {"verdict": "none-found", "points": [],
            "latest": list(latest_per_disk.values())}


def retention_flags(snapshots, warn_days=7):
    """Flag snapshots whose retention is short enough to destroy the only
    recovery point (the 1-day/24h auto-release trap seen in this tier)."""
    flags = []
    for s in snapshots:
        if not isinstance(s, dict):
            continue
        raw = s.get("RetentionDays")
        try:
            days = int(raw)
        except (TypeError, ValueError):
            continue
        if 0 < days <= warn_days:
            flags.append("snapshot %s auto-releases in %d day(s)"
                         % (s.get("SnapshotId", "?"), days))
    return flags


def summarize_datapoints(raw_datapoints):
    """CloudMonitor returns Datapoints as a JSON string. Parse tolerantly and
    return (count, average_of_Average, maximum_of_Maximum) or None parts."""
    points = None
    if isinstance(raw_datapoints, str) and raw_datapoints.strip():
        try:
            points = json.loads(raw_datapoints)
        except json.JSONDecodeError:
            points = None
    elif isinstance(raw_datapoints, list):
        points = raw_datapoints
    if not isinstance(points, list) or not points:
        return None, None, None
    avgs = [float(p.get("Average")) for p in points
            if isinstance(p, dict) and p.get("Average") is not None]
    maxs = [float(p.get("Maximum")) for p in points
            if isinstance(p, dict) and p.get("Maximum") is not None]
    return (len(points),
            round(sum(avgs) / len(avgs), 1) if avgs else None,
            max(maxs) if maxs else None)


def exposure_port_hints(rows):
    """Surface management-port exposure (22/3389) from Security Center
    exposure records; text hints only, never a firewall conclusion."""
    hints = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        ports = row.get("ExposurePort") or first_of(row, ("Ports",), "")
        for port in re.split(r"[,\s]+", str(ports)):
            if port in ENTRY_VECTOR_HINTS and port not in seen:
                seen.add(port)
                hints.append("port %s: %s" % (port, ENTRY_VECTOR_HINTS[port]))
    return hints


def build_next_actions(branch, recover, cpu_suspect, unresolved,
                       exposure_rows, guest_done, snapshot_done):
    """Deterministic NEXT_ACTION string from collected facts."""
    if branch == "ransom":
        if recover["verdict"] == "restorable":
            return ("Roll back from %s (pre-incident, accomplished) via the "
                    "ECS console; system disk first; this is irreversible and "
                    "manual-only%s. Before rollback create a current-state "
                    "evidence snapshot%s."
                    % (recover["points"][0].get("SnapshotId", "?"),
                       "" if snapshot_done else " (gated --create-evidence-"
                       "snapshot available)",
                       " -- done this run" if snapshot_done else ""))
        if recover["verdict"] == "no-window":
            return ("Ask the customer when encryption was noticed "
                    "(ransom note file time, latest encrypted file mtime), "
                    "then re-run with --incident-time to select the rollback "
                    "point; recovery hinges on a pre-incident snapshot.")
        return ("No pre-incident recovery point exists: platform-side "
                "restore is impossible (do not re-snapshot the encrypted "
                "state expecting recovery); guide to third-party data "
                "recovery services and fix the backup retention policy.")
    if branch == "miner":
        base = ("Process the unresolved Security Center alerts in the "
                "console, verify the entry vulnerability is patched, then "
                "clean persistence.")
        if not guest_done:
            base += (" Run the four gated forensics categories "
                     "(--guest-check processes/connections/cron-tasks/"
                     "startup-items) with --confirmed to locate "
                     "persistence.")
        if cpu_suspect:
            base += " CPU readings corroborate a resource-exhaustion pattern."
        if exposure_rows:
            base += " Tighten the exposed management ports per the checklist."
        if unresolved:
            base += " Recurring alerts mean the hole was never fixed: patch " \
                    "before concluding."
        return base
    if branch == "webshell":
        return ("Restore the site from known-clean code or a pre-defacement "
                "backup, have the developer fix the upload/injection "
                "vulnerability, and use the Security Center console for "
                "quarantine actions (this skill never deletes files).")
    return ("Review the evidence report, then choose the gated forensics or "
            "evidence-snapshot steps if on-host facts are still missing.")


# ---------------------------------------------------------------------------
# Report accumulator
# ---------------------------------------------------------------------------

class Report:
    def __init__(self):
        self.lines = []
        self.degradations = []   # [(source, reason)]
        self.data = {}
        self.blocked = []

    def line(self, text=""):
        self.lines.append(text)

    def degrade(self, source, reason):
        self.degradations.append((source, reason))

    def render(self):
        return "\n".join(self.lines)


def warn_and_degrade(report, source, err):
    line = "[WARN] %s: %s" % (source, err)
    print(line, file=sys.stderr)
    reason = str(err)
    code = getattr(err, "code", "") or ""
    if getattr(err, "is_permission_error", False):
        reason = ("permission denied (%s) -- grant the single missing action "
                  "from references/ram-policies.md (NoPermission / "
                  "ImplicitDeny); no wildcard grant is needed" % (code or
                                                                  "denied"))
    report.degrade(source, reason)


# ---------------------------------------------------------------------------
# Layer 1 -- automatic evidence gathering
# ---------------------------------------------------------------------------

def gather_susp_events(region, profile):
    """DescribeSuspEvents with CurrentPage/PageSize paging."""
    items = []
    for page in range(1, MAX_PAGES + 1):
        body = _cli.call("sas", "DescribeSuspEvents", {
            "From": "sas", "Lang": "en",
            "CurrentPage": str(page), "PageSize": str(PAGE_SIZE),
        }, region=region, profile=profile)
        page_items = _cli.as_list(_cli.pick(body, "SuspEvents"))
        items.extend(page_items)
        total = body.get("TotalCount")
        if total is not None:
            try:
                if len(items) >= int(total):
                    break
            except (TypeError, ValueError):
                pass
        if len(page_items) < PAGE_SIZE:
            break
    return items


def gather_snapshots(region, instance_id, profile):
    """DescribeSnapshots for the instance; returns the raw record list."""
    items = []
    for page in range(1, MAX_PAGES + 1):
        body = _cli.call("ecs", "DescribeSnapshots", {
            "RegionId": region, "InstanceId": instance_id,
            "PageNumber": str(page), "PageSize": str(PAGE_SIZE),
        }, region=region, profile=profile)
        page_items = _cli.as_list(_cli.dig(body, ["Snapshots"]))
        items.extend(page_items)
        total = body.get("TotalCount")
        try:
            if total is None or len(items) >= int(total) \
                    or len(page_items) < PAGE_SIZE:
                break
        except (TypeError, ValueError):
            break
    return items


def gather_exposure(region, instance_id, profile):
    body = _cli.call("sas", "DescribeExposedInstanceList", {
        "InstanceId": instance_id, "CurrentPage": "1",
        "PageSize": str(PAGE_SIZE),
    }, region=region, profile=profile)
    return _cli.as_list(_cli.pick(body, "List", "ExposedInstanceList",
                                  "ExposedInstances"))


def gather_restore_jobs(report, region, profile):
    """DescribeRestoreJobs2 for the ECS file-backup restore type.

    The API documents two vault editions (Edition accepts STANDARD, the
    default, and BASIC), so both are queried independently: one edition being
    empty, denied or unavailable must not hide the other. Failures degrade per
    edition instead of aborting the run."""
    jobs = []
    for edition in HBR_RESTORE_EDITIONS:
        try:
            body = _cli.call("hbr", "DescribeRestoreJobs2", {
                "Edition": edition, "RestoreType": HBR_RESTORE_TYPE,
                "PageNumber": "1", "PageSize": str(HBR_PAGE_SIZE),
            }, region=region, profile=profile)
            rows = _cli.as_list(_cli.pick(body, "RestoreJobs"))
            report.line("  edition %-8s %d restore job(s) on record"
                        % (edition, len(rows)))
            jobs.extend(rows)
        except _cli.CliError as e:
            report.line("  edition %-8s unavailable (%s)" % (edition, e))
            warn_and_degrade(report,
                             "hbr:DescribeRestoreJobs2(%s)" % edition, e)
    return jobs


def _row_carries_ip(row_values, ip):
    """Exact-token match: a record carries the ip only when one of its
    string values, split on list separators, equals it (no substring
    false-positives between neighbouring addresses)."""
    for value in row_values:
        for token in re.split(r"[,\s;]+", value):
            if token == ip:
                return True
    return False


def resolve_instance_from_public_ip(region, public_ip, profile):
    """In-contract mapping of a public IP to an instance id: scan the
    Security Center exposure surface (it carries instance + ip pairs).
    Returns (instance_id|None, candidates, error|None)."""
    rows = []
    for page in range(1, MAX_PAGES + 1):
        body = _cli.call("sas", "DescribeExposedInstanceList", {
            "CurrentPage": str(page), "PageSize": str(PAGE_SIZE),
        }, region=region, profile=profile)
        page_rows = _cli.as_list(_cli.pick(body, "List",
                                           "ExposedInstanceList",
                                           "ExposedInstances"))
        rows.extend(page_rows)
        if len(page_rows) < PAGE_SIZE:
            break
    candidates = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        values = _cli.collect_strings(row)
        if _row_carries_ip(values, public_ip):
            inst = str(first_of(row, ("InstanceId",), ""))
            if inst and inst not in candidates:
                candidates.append(inst)
    if len(candidates) == 1:
        return candidates[0], candidates, None
    if len(candidates) > 1:
        return None, candidates, None
    return None, [], "not-found"


def gather_cpu_readings(report, region, instance_id, profile):
    """CloudMonitor last window per metric; independent failure per metric."""
    readings = []
    dimensions = json.dumps([{"instanceId": instance_id}],
                            separators=(",", ":"))
    for metric_name, meaning, required in CMS_METRICS:
        try:
            body = _cli.call("cms", "DescribeMetricLast", {
                "Namespace": CMS_NAMESPACE, "MetricName": metric_name,
                "Dimensions": dimensions, "Period": "300", "Length": "48",
            }, region=region, profile=profile)
            datapoints = _cli.dig(body, ["Datapoints"])
            count, avg, peak = summarize_datapoints(datapoints)
            readings.append({"metric": metric_name, "meaning": meaning,
                             "points": count, "average": avg, "peak": peak})
            report.line("  %-18s samples=%s avg=%s peak=%s  (%s)"
                        % (metric_name,
                           count if count is not None else "n/a",
                           avg if avg is not None else "n/a",
                           peak if peak is not None else "n/a",
                           meaning))
        except _cli.CliError as e:
            report.line("  %-18s unavailable (%s)" % (metric_name, e))
            warn_and_degrade(report, "cms:DescribeMetricLast(%s)"
                             % metric_name, e)
    return readings


# ---------------------------------------------------------------------------
# Layer 2 -- gated in-guest forensics
# ---------------------------------------------------------------------------

def guest_disclosure(os_type, key):
    entry = GUEST_COMMANDS[os_type][key]
    return (
        "Gated in-guest forensics -- one command, this run only:\n"
        "  command   : %s\n"
        "  category  : %s\n"
        "  target    : %s guest (%s channel)\n"
        "  effect    : reports state only; it changes nothing, deletes "
        "nothing and stops nothing; reversible by definition (no writes)\n"
        "  scope     : exactly one whitelisted %s probe for exactly the "
        "instance named in this invocation\n"
        "  approval  : valid for THIS command at THIS time only; a second "
        "probe needs a second confirmation\n"
        "Relay all five lines to the customer. If they agree, re-invoke "
        "with --confirmed. Commands outside this whitelist (file deletion, "
        "process kill, service control, anything with redirection) are "
        "refused even with --confirmed and become customer-paste "
        "requests." % (entry["command"], entry["category"], os_type,
                       "Cloud Assistant", key))


def run_guest_probe(report, region, instance_id, os_type, key, profile):
    """Dispatch one whitelisted probe and poll for its output."""
    entry = GUEST_COMMANDS[os_type][key]
    command = entry["command"]
    try:
        body = _cli.call("ecs", "RunCommand", {
            "RegionId": region,
            "Type": entry["type"],
            "Name": "ecs-forensics-%s" % key,
            "Description": "single whitelisted %s probe (non-mutating)"
                           % entry["category"],
            "CommandContent": _cli.encode_command(command),
            "ContentEncoding": "Base64",
            "InstanceId.1": instance_id,
            "Timeout": "60",
        }, region=region, profile=profile)
        invoke_id = str(body.get("InvokeId", "") or "")
        if not invoke_id:
            raise _cli.CliError("RunCommand returned no InvokeId")
    except _cli.CliError as e:
        report.line("  dispatch failed: %s" % e)
        warn_and_degrade(report, "ecs:run-command(%s)" % key, e)
        report.line("  substitute: ask the customer to run `%s` in the "
                    "guest (Workbench/VNC/SSH) and paste the output."
                    % command)
        return None

    report.line("  dispatched: invoke-id %s" % invoke_id)
    for attempt in range(INVOCATION_POLL_MAX):
        if attempt:
            time.sleep(INVOCATION_POLL_INTERVAL_SECONDS)
        try:
            inv = _cli.call("ecs", "DescribeInvocations", {
                "RegionId": region, "InvokeId": invoke_id,
                "IncludeOutput": "true",
            }, region=region, profile=profile)
        except _cli.CliError as e:
            report.line("  read-back failed: %s" % e)
            warn_and_degrade(report, "ecs:DescribeInvocations", e)
            return None
        rows = _cli.as_list(_cli.dig(inv, ["Invocations", "Invocation"]))
        inst_rows = []
        for row in rows:
            inst_rows.extend(_cli.as_list(_cli.dig(row, ["InvokeInstances"])))
        for ir in inst_rows:
            if not isinstance(ir, dict):
                continue
            status = str(ir.get("InvocationStatus")
                         or ir.get("Status") or "")
            if status and status not in _TERMINAL_INVOCATION_STATES:
                continue
            output = _cli.decode_guest_output(str(ir.get("Output") or ""))
            trimmed = output[:4000] + ("\n  [...truncated]"
                                       if len(output) > 4000 else "")
            report.line("  category : %s" % entry["category"])
            report.line("  exit     : %s" % first_of(ir, ("ExitCode",), "?"))
            report.line("  read-how : %s" % entry["read_how"])
            report.line("  output   :")
            for line in trimmed.splitlines():
                report.line("    | %s" % line)
            return {"key": key, "command": command, "status": status,
                    "output": trimmed}
        last = rows[-1] if rows and isinstance(rows[-1], dict) else {}
        report.line("  (still %s -- poll %d/%d)"
                    % (first_of(last, ("InvocationStatus", "Status"),
                                "Running"),
                       attempt + 1, INVOCATION_POLL_MAX))
    report.degrade("ecs:run-command(%s)" % key,
                   "guest did not return within the polling window")
    report.line("  timed out waiting for the guest; substitute: customer "
                "runs `%s` and pastes the output." % command)
    return None


# ---------------------------------------------------------------------------
# Layer 3 -- gated evidence snapshot
# ---------------------------------------------------------------------------

def snapshot_disclosure(disk_id, name):
    return (
        "Gated evidence snapshot -- one cloud write, this run only:\n"
        "  action    : CreateSnapshot on disk %s\n"
        "  name      : %s\n"
        "  effect    : adds a recovery point; changes nothing on the disk; "
        "the snapshot can be deleted afterwards (manually, console)\n"
        "  billing   : pay-as-you-go for stored size; delete unneeded "
        "snapshots after the incident to stop charges\n"
        "  why       : snapshot-first is mandatory before any cleanup or "
        "handling guidance in this skill\n"
        "Relay all five lines to the customer. If they agree, re-invoke "
        "with --confirmed." % (disk_id, name))


def create_evidence_snapshot(report, region, disk_id, profile):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    name = "ecs-intrusion-evidence-%s" % stamp
    try:
        # CreateSnapshot has NO RegionId parameter (verified against aliyun
        # CLI 3.4.5 metadata, which accepts DiskId, SnapshotName, Description,
        # RetentionDays, Category, InstantAccess, InstantAccessRetentionDays,
        # ClientToken, ResourceGroupId): the disk id already scopes the call,
        # and the transport layer passes the region through --region.
        body = _cli.call("ecs", "CreateSnapshot", {
            "DiskId": disk_id,
            "SnapshotName": name,
            "Description": "pre-cleanup evidence snapshot taken via the "
                           "host-intrusion skill",
        }, region=region, profile=profile)
        snapshot_id = str(body.get("SnapshotId", "") or "")
        report.line("  snapshot created: %s (name %s, status progressing; "
                    "it becomes usable when accomplished)"
                    % (snapshot_id or "?", name))
        report.line("  %s" % SNAPSHOT_BILLING_NOTICE)
        return {"snapshot_id": snapshot_id, "name": name}
    except _cli.CliError as e:
        report.line("  snapshot creation failed: %s" % e)
        warn_and_degrade(report, "ecs:create-snapshot", e)
        report.line("  substitute: the customer creates the snapshot in the "
                    "ECS console before any cleanup step.")
        return None


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def render_alerts(report, events, instance_id, public_ip):
    """Bucket the Security Center events and print the target-scoped ones."""
    if not events:
        report.line("  no security-center events returned for this identity "
                    "(empty is valid: it scopes to the current account)")
        return {}
    branch_counts = {}
    scoped = []
    for item in events:
        branch, _anchor = classify_alert(item)
        branch_counts[branch] = branch_counts.get(branch, 0) + 1
        if alert_matches_target(item, instance_id, public_ip):
            scoped.append((branch, item))
    report.line("  branch totals (account-scoped): "
                + ", ".join("%s=%d" % (BRANCH_LABELS.get(b, b), n)
                            for b, n in sorted(branch_counts.items())))
    if not scoped:
        report.line("  no events matched the target instance directly; "
                    "check the instance id / public ip if this surprises you")
    name_seen = {}
    for branch, item in scoped[:15]:
        name = str(first_of(item, ("Name", "EventName", "AlarmEventName"),
                            "?"))
        name_seen[name] = name_seen.get(name, 0) + 1
        report.line("  [%s] %s | level=%s | status=%s | last=%s"
                    % (branch, name[:70],
                       first_of(item, ("Level",), "?"),
                       first_of(item, ("Status", "EventStatus", "Dealed"),
                                "?"),
                       first_of(item, ("LastFoundTime", "OccurrenceTime",
                                       "ModifiedAt", "DetectTime"), "?")))
    recurring = [n for n, c in name_seen.items() if c > 1]
    if recurring:
        report.line("  recurring alert names: %s" % ", ".join(recurring[:5]))
        report.line("  %s" % RECURRENCE_NOTICE)
    return {"counts": branch_counts, "recurring": recurring,
            "scoped": len(scoped)}


def render_snapshots(report, snapshots, recover, flags):
    report.line("  snapshot inventory: %d record(s) for this instance"
                % len(snapshots))
    for s in snapshots[:10]:
        report.line("    %s | %s | %s | %s | used-by=%s"
                    % (first_of(s, ("SnapshotId",), "?"),
                       first_of(s, ("Status",), "?"),
                       first_of(s, ("CreationTime",), "?"),
                       first_of(s, ("SourceDiskType", "DiskId"), "?"),
                       first_of(s, ("Usage",), "-")))
    for flag in flags:
        report.line("  [!] %s" % flag)
    verdict = recover["verdict"]
    if verdict == "restorable":
        point = recover["points"][0]
        report.line("  VERDICT: restorable -- %s accomplished at %s predates "
                    "the incident window"
                    % (point.get("SnapshotId", "?"),
                       point.get("CreationTime", "?")))
        report.line("  %s" % ROLLBACK_MANUAL_NOTICE)
    elif verdict == "no-window":
        report.line("  VERDICT: undecided -- accomplished snapshots exist, "
                    "but no incident time window was given; re-run with "
                    "--incident-time to pick the rollback point")
    else:
        report.line("  VERDICT: none usable for pre-incident recovery "
                    "(no accomplished snapshot at or before the window)")
        report.line("  %s" % ENCRYPTED_STATE_SNAPSHOT_NOTICE)
        report.line("  %s" % RECOVERY_UNCERTAIN_NOTICE)
    report.line("  %s" % BACKUP_RETENTION_NOTICE)


def render_exposure(report, rows):
    if not rows:
        report.line("  no exposure records returned (empty is valid; it can "
                    "also mean the Security Center agent is not installed)")
        return
    for row in rows[:10]:
        report.line("    %s | %s | exposed=%s | risk=%s"
                    % (first_of(row, ("InstanceId",), "?"),
                       first_of(row, ("InstanceName", "InternetIp"), "-"),
                       first_of(row, ("ExposedStatus", "ExposureStatus"),
                                "?"),
                       first_of(row, ("VulStatus", "HealthStatus"), "-")))
    for hint in exposure_port_hints(rows):
        report.line("    entry-vector candidate: %s" % hint)
    report.line("  NOTE: per-rule security-group verification is not part "
                "of this skill's verified surface; the exposure list is "
                "the entry-vector evidence, console checks close it out")


def render_hardening(report):
    report.line("  Ticket-proven hardening list (relay all six):")
    for item in HARDENING_CHECKLIST:
        report.line("   %s" % item)


def render_fallback_table(report):
    report.line("  Readings this skill will NOT dispatch (customer-paste "
                "via console/Workbench/VNC):")
    for item in FALLBACK_READINGS:
        report.line("   - %s: `%s`  (%s)"
                    % (item["topic"], item["customer_command"],
                       item["why_not_auto"]))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="host_intrusion_diagnosis.py",
        description="Alibaba Cloud ECS host intrusion triage: Security "
                    "Center alerts, exposure surface, CPU corroboration, "
                    "snapshot/file-backup recoverability, gated in-guest "
                    "forensics and a gated evidence snapshot. Destructive "
                    "cleanup is always manual.",
    )
    loc = parser.add_argument_group("locator (region-id plus exactly one)")
    loc.add_argument("--region-id", default=None,
                     help="Region id, e.g. cn-hangzhou (REQUIRED, never "
                          "guessed)")
    loc.add_argument("--instance-id", default=None,
                     help="Target ECS instance id (i-...)")
    loc.add_argument("--public-ip", default=None,
                     help="Target public IPv4; mapped to an instance id via "
                          "the Security Center exposure surface")

    ctx = parser.add_argument_group("context")
    ctx.add_argument("--incident-time", default=None,
                     help="When the intrusion/encryption was noticed; ISO "
                          "8601 or epoch seconds (drives the recoverability "
                          "verdict)")
    ctx.add_argument("--symptom", default=None,
                     help="Verbatim customer wording (drives triage)")
    ctx.add_argument("--os-type", choices=("linux", "windows"),
                     default="linux", help="Guest OS family (default linux)")
    ctx.add_argument("--domain", default=None,
                     help="Affected website domain (webshell branch "
                          "context; resolution is a customer step)")

    g2 = parser.add_argument_group("gated operations (each needs --confirmed)")
    g2.add_argument("--guest-check", choices=GUEST_COMMAND_CATEGORIES,
                    default=None,
                    help="Dispatch exactly ONE whitelisted forensics "
                         "category into the guest")
    g2.add_argument("--create-evidence-snapshot", action="store_true",
                    help="Create the current-state evidence snapshot (needs "
                         "--disk-id)")
    g2.add_argument("--disk-id", default=None,
                    help="Disk id (d-...) for the evidence snapshot")
    g2.add_argument("--confirmed", action="store_true",
                    help="The customer approved THIS run's gated operation")

    out = parser.add_argument_group("output / transport")
    out.add_argument("--report-file", default=None,
                     help="Also write the report to this NEW local file "
                          "(an existing path is refused)")
    out.add_argument("--json", action="store_true", help="JSON output")
    out.add_argument("--profile", default=None, help="aliyun CLI profile")
    out.add_argument("--cli-timeout", type=int, default=None,
                     help="Override per-call CLI timeout (seconds)")
    return parser.parse_args(argv)


def validate_args(args):
    """Return an error string, or None when the inputs are usable."""
    if not args.region_id or not REGION_RE.match(args.region_id):
        return ("a valid --region-id is required and never guessed "
                "(example: cn-hangzhou)")
    if not args.instance_id and not args.public_ip:
        return "provide exactly one locator: --instance-id or --public-ip"
    if args.instance_id and args.public_ip:
        return "provide exactly one locator: --instance-id or --public-ip"
    if args.instance_id and not INSTANCE_RE.match(args.instance_id):
        return "--instance-id must be an ECS instance id (example: i-bp1exampleea42c2d3cf)"
    if args.public_ip and not IPV4_RE.match(args.public_ip):
        return "--public-ip must be a dotted IPv4 address"
    if args.incident_time:
        try:
            parse_iso_time(args.incident_time)
        except ValueError as e:
            return str(e)
    if args.create_evidence_snapshot:
        if not args.disk_id:
            return ("--create-evidence-snapshot needs --disk-id (list the "
                    "disks in the ECS console if unsure)")
        if not DISK_RE.match(args.disk_id):
            return "--disk-id must be an ECS disk id (example: d-bp1examplec75780a4b3)"
    return None


def _run_selftest():
    """Offline regression lock: pure computation core + contract guards."""
    results = {"pass": 0, "fail": 0}

    def check(name, got, want):
        if got == want:
            results["pass"] += 1
        else:
            results["fail"] += 1
            print("FAIL {0}: got {1!r} want {2!r}".format(name, got, want))

    from datetime import datetime, timezone

    # --- parse_iso_time ---
    dt, tz = parse_iso_time("2026-08-12T02:30:00Z")
    check("pit_z", dt.year, 2026)
    check("pit_z_tzflag", tz, True)
    check("pit_z_utc", dt.tzinfo is not None, True)
    dt2, tz2 = parse_iso_time("2026-08-12 02:30")
    check("pit_naive_hour", dt2.hour, 2)
    check("pit_naive_tzflag", tz2, False)
    dt3, _ = parse_iso_time("1723449600")
    check("pit_epoch", dt3.year, 2024)
    try:
        parse_iso_time("")
        check("pit_empty_raises", False, True)
    except ValueError:
        check("pit_empty_raises", True, True)
    try:
        parse_iso_time(None)
        check("pit_none_raises", False, True)
    except ValueError:
        check("pit_none_raises", True, True)

    # --- classify_symptom ---
    branch, _ = classify_symptom("My server got hit by ransomware")
    check("cs_ransom", branch, "ransom")
    branch2, _ = classify_symptom("there is a miner process using 100% CPU")
    check("cs_miner", branch2, "miner")
    b3, _ = classify_symptom("totally unrelated question about billing")
    check("cs_none", b3, None)

    # --- classify_alert ---
    alert = {"Name": "Webshell Found", "EventName": ""}
    b, a = classify_alert(alert)
    check("ca_webshell", b, "webshell")
    b2, _ = classify_alert({"Name": ""})
    check("ca_empty", b2, "other")
    b3, _ = classify_alert("not a dict")
    check("ca_non_dict", b3, "other")

    # --- first_of ---
    check("fo_first", first_of({"a": 1, "b": 2}, ["a", "b"]), 1)
    check("fo_skip_empty", first_of({"a": "", "b": 2}, ["a", "b"]), 2)
    check("fo_default", first_of({}, ["x", "y"], "N/A"), "N/A")
    check("fo_non_dict", first_of("str", ["a"], "D"), "D")

    # --- alert_targets / alert_matches_target ---
    item = {"InstanceId": "i-abc", "InternetIp": "47.1.1.1", "Instance": {"IntranetIp": "10.0.0.1"}}
    targets = alert_targets(item)
    check("at_has_id", "i-abc" in targets, True)
    check("at_has_pub", "47.1.1.1" in targets, True)
    check("at_has_priv", "10.0.0.1" in targets, True)
    check("amt_id", alert_matches_target(item, "i-abc", ""), True)
    check("amt_ip", alert_matches_target(item, "", "47.1.1.1"), True)
    check("amt_no", alert_matches_target(item, "i-xyz", "8.8.8.8"), False)

    # --- judge_recoverability ---
    incident = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
    v_empty = judge_recoverability([], incident)
    check("jr_none", v_empty["verdict"], "none-found")
    snaps = [
        {"Status": "accomplished", "CreationTime": "2026-08-11T00:00:00Z",
         "SnapshotId": "s-old", "SourceDiskId": "d-1"},
        {"Status": "accomplished", "CreationTime": "2026-08-13T00:00:00Z",
         "SnapshotId": "s-new", "SourceDiskId": "d-1"},
        {"Status": "progressing", "CreationTime": "2026-08-10T00:00:00Z",
         "SnapshotId": "s-prog", "SourceDiskId": "d-1"},
    ]
    v = judge_recoverability(snaps, incident)
    check("jr_restorable", v["verdict"], "restorable")
    check("jr_point_count", len(v["points"]), 1)  # only s-old is before incident
    check("jr_point_id", v["points"][0]["SnapshotId"], "s-old")
    check("jr_latest", len(v["latest"]), 1)  # only d-1, latest accomplished is s-new
    v_nw = judge_recoverability(snaps, None)
    check("jr_no_window", v_nw["verdict"], "no-window")

    # --- retention_flags ---
    flagged = retention_flags([
        {"SnapshotId": "s1", "RetentionDays": 1},
        {"SnapshotId": "s2", "RetentionDays": 30},
        {"SnapshotId": "s3", "RetentionDays": 7},
        {"SnapshotId": "s4", "RetentionDays": 0},
        {"SnapshotId": "s5"},
    ], warn_days=7)
    check("rf_count", len(flagged), 2)  # s1(1 day) and s3(7 days)
    check("rf_has_s1", any("s1" in f for f in flagged), True)
    check("rf_has_s3", any("s3" in f for f in flagged), True)
    check("rf_empty", retention_flags([]), [])

    # --- contract guard ---
    src = open(__file__, encoding="utf-8").read()
    core_end = src.index("def _run_selftest():")
    src_core = src[:core_end]
    check("no_mutating_in_core",
          any(t in src_core for t in ("DeleteSnapshot", "ReInitDisk",
              "ResetDisk", "StopInstance", "DeleteInstance")), False)
    check("exit_propagated", "sys.exit(main())" in src, True)

    print("selftest: {0} passed, {1} failed".format(results["pass"], results["fail"]))
    return 1 if results["fail"] else 0


def main(argv=None):
    if argv is None and "--selftest" in sys.argv:
        return _run_selftest()
    args = parse_args(argv)
    report = Report()

    if args.cli_timeout:
        try:
            _cli.set_call_timeout(args.cli_timeout)
        except _cli.CliError as e:
            print("[ERROR] %s" % e, file=sys.stderr)
            print("STATUS: FAIL")
            print("NEXT_ACTION: Re-run with an integer --cli-timeout "
                  "between 5 and 600 seconds.")
            return 1

    error = validate_args(args)
    if error:
        print("[ERROR] %s" % error, file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: Correct the input and re-run. Ask the customer "
              "for the region and instance locator; never guess them.")
        return 1

    gated = []
    if args.guest_check:
        gated.append(("guest-check " + args.guest_check,
                      lambda: guest_disclosure(
                          args.os_type, args.guest_check)))
    if args.create_evidence_snapshot:
        gated.append(("create-evidence-snapshot",
                      lambda: snapshot_disclosure(
                          args.disk_id,
                          "ecs-intrusion-evidence-<this-run>")))
    if len(gated) > 1:
        print("[ERROR] exactly one gated operation per run: one customer "
              "approval covers one single command or write.",
              file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: Split into two approved runs -- the evidence "
              "snapshot first (snapshot-before-cleanup), then one "
              "forensics probe each with its own confirmation.")
        return 1
    if gated and not args.confirmed:
        print("CONFIRMATION GATE NOT SATISFIED -- nothing was executed.\n")
        for _label, disclosure in gated:
            print(disclosure() + "\n")
        print("Each gated operation needs its own approved re-run; do not "
              "batch two of them behind one confirmation.")
        print("STATUS: FAIL")
        print("NEXT_ACTION: Relay the disclosure line-by-line to the "
              "customer. Re-run with --confirmed only after they approve; "
              "otherwise use the customer-executed steps in the console or the equivalent OpenAPI.")
        return 1

    _cli.check_cli_available()
    session = _cli.session_id()
    now = datetime.now(timezone.utc)

    report.line("=" * 72)
    report.line("ECS HOST INTRUSION TRIAGE")
    report.line("=" * 72)
    report.line("Session-Id : %s" % session)
    report.line("UTC        : %s" % now.strftime("%Y-%m-%d %H:%M:%S"))
    report.line("Region     : %s (given by the caller -- never guessed)"
                % args.region_id)
    report.line("Time note  : times are UTC unless --incident-time carried "
                "an explicit offset")

    # ---- identity pre-check ------------------------------------------------
    account_id = _cli.resolve_account_id(region=args.region_id,
                                         profile=args.profile)
    if account_id:
        report.line("Account    : %s (via STS GetCallerIdentity)"
                    % account_id)
    else:
        print("[ERROR] sts:GetCallerIdentity failed: the CLI has no usable "
              "default credential", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: Repair CLI credentials via `aliyun sts get-caller-identity` "
              "(never pass keys on a command line), then re-run.")
        if args.json:
            print(json.dumps({"status": "FAIL", "session_id": session}))
        else:
            print(report.render())
        return 1

    # ---- locator -----------------------------------------------------------
    instance_id = args.instance_id or ""
    if args.public_ip:
        report.line("")
        report.line("== Locator: mapping public ip %s ==" % args.public_ip)
        try:
            mapped, candidates, why = resolve_instance_from_public_ip(
                args.region_id, args.public_ip, args.profile)
            if mapped:
                instance_id = mapped
                report.line("  mapped to instance %s via the Security Center "
                            "exposure surface" % instance_id)
            elif why == "not-found":
                report.line("  no exposure record carries this ip. The "
                            "instance may not exist in THIS account, sit in "
                            "another region, or be a non-ECS product (cloud "
                            "web hosting has no ECS API surface -- route per "
                            "references/host-intrusion-cleanup__handoff-boundaries.md)")
                if args.json:
                    print(json.dumps({"status": "FAIL", "reason": why,
                                      "session_id": session}))
                else:
                    print(report.render())
                print("STATUS: FAIL")
                print("NEXT_ACTION: Ask the customer for the ECS instance "
                      "id and region, or confirm the product form before "
                      "diagnosis. Do not guess an instance id.")
                return 1
            else:
                report.line("  ambiguous: %d exposed instances carry this ip "
                            "(%s)" % (len(candidates), ", ".join(candidates)))
                if not args.json:
                    print(report.render())
                print("STATUS: FAIL")
                print("NEXT_ACTION: Ask the customer which instance is the "
                      "affected one, then re-run with --instance-id.")
                return 1
        except _cli.CliError as e:
            report.line("  mapping query failed: %s" % e)
            warn_and_degrade(report, "sas:DescribeExposedInstanceList(map)",
                             e)
            if not args.json:
                print(report.render())
            print("STATUS: DEGRADED")
            print("NEXT_ACTION: Re-run with --instance-id (ask the customer "
                  "for it); ip mapping needs the exposure surface.")
            return 1
    report.line("Instance   : %s" % instance_id)

    # ---- triage ------------------------------------------------------------
    report.line("")
    report.line("== Triage ==")
    branch, entry = classify_symptom(args.symptom or "")
    if entry and entry.get("action") == "handoff":
        target = HANDOFF_TARGETS.get(entry["target"], {})
        report.line("  symptom '%s' is outside this tier: %s"
                    % (args.symptom, entry["note"]))
        if target.get("skill"):
            report.line("  hand to %s. Evidence to attach: %s"
                        % (target["skill"],
                           "; ".join(target["evidence_to_attach"])))
        elif target.get("evidence_to_attach"):
            report.line("  evidence to attach: %s"
                        % "; ".join(target["evidence_to_attach"]))
        if target.get("manual_note"):
            report.line("  manual note: %s" % target["manual_note"])
        # The triage lines above ARE the handoff answer: render them before
        # the output-contract lines, otherwise the customer only receives
        # STATUS/NEXT_ACTION and never sees the routing note or the
        # self-service entry it cites.
        if not args.json:
            print(report.render())
        print("STATUS: OK")
        print("NEXT_ACTION: Route per references/host-intrusion-cleanup__handoff-boundaries.md "
              "with the evidence listed above; do not continue the "
              "intrusion flow on a non-intrusion area.")
        return 0
    if branch and branch not in ("other", "entry"):
        report.line("  symptom branch: %s" % BRANCH_LABELS[branch])
    elif args.symptom:
        report.line("  symptom wording did not match any anchor; branches "
                    "will be derived from the alert evidence instead")

    # ---- Layer 1 automatic queries ----------------------------------------
    events, exposure_rows, snapshots = [], [], []
    guest_result = None
    snapshot_result = None
    cpu_readings = []
    restore_jobs = []
    version_config = {}
    field_stats = {}

    report.line("")
    report.line("== Security Center alerts (sas:DescribeSuspEvents) ==")
    try:
        events = gather_susp_events(args.region_id, args.profile)
        alert_summary = render_alerts(report, events, instance_id,
                                      args.public_ip)
    except _cli.CliError as e:
        report.line("  unavailable: %s" % e)
        warn_and_degrade(report, "sas:DescribeSuspEvents", e)
        alert_summary = {}

    report.line("")
    report.line("== Security Center version + asset statistics ==")
    try:
        body = _cli.call("sas", "DescribeVersionConfig", {},
                         region=args.region_id, profile=args.profile)
        version_config = body if isinstance(body, dict) else {}
        for key in ("Version", "PostPayVersion", "PostPayModuleSwitch",
                    "SasVersion", "EnterpriseCapacity"):
            if key in version_config:
                report.line("  %-20s %s" % (key + ":", version_config[key]))
        report.line("  capability note: whether alerts can be auto-handled "
                    "depends on the edition -- see "
                    "references/host-intrusion-cleanup__scenario-runbooks.md; unhandled alerts are "
                    "a console action this skill guides but never performs")
    except _cli.CliError as e:
        report.line("  version config unavailable: %s" % e)
        warn_and_degrade(report, "sas:DescribeVersionConfig", e)
    try:
        body = _cli.call("sas", "DescribeFieldStatistics", {},
                         region=args.region_id, profile=args.profile)
        fields = _cli.dig(body, ["GroupedFields"])
        if isinstance(fields, dict):
            for key in sorted(fields):
                report.line("  %-20s %s" % (key + ":", fields[key]))
        field_stats = fields if isinstance(fields, dict) else {}
    except _cli.CliError as e:
        report.line("  asset statistics unavailable: %s" % e)
        warn_and_degrade(report, "sas:DescribeFieldStatistics", e)

    report.line("")
    report.line("== Entry vector: internet exposure "
                "(sas:DescribeExposedInstanceList) ==")
    try:
        exposure_rows = gather_exposure(args.region_id, instance_id,
                                        args.profile)
        render_exposure(report, exposure_rows)
    except _cli.CliError as e:
        report.line("  unavailable: %s" % e)
        warn_and_degrade(report, "sas:DescribeExposedInstanceList", e)

    report.line("")
    report.line("== Mining corroboration: recent resource readings "
                "(cms:DescribeMetricLast -> cms:QueryMetricLast) ==")
    cpu_readings = gather_cpu_readings(report, args.region_id, instance_id,
                                       args.profile)

    report.line("")
    report.line("== Recoverability inventory (ecs:DescribeSnapshots) ==")
    incident_dt = None
    if args.incident_time:
        incident_dt, flagged = parse_iso_time(args.incident_time)
        if not flagged:
            report.line("  incident time was read as UTC; a local-zone time "
                        "shifts the rollback point -- confirm with the "
                        "customer if the margin matters")
    else:
        report.line("  no --incident-time given: the recoverability verdict "
                    "is inventory-only until the incident window is known")
    try:
        snapshots = gather_snapshots(args.region_id, instance_id,
                                     args.profile)
        recover = judge_recoverability(snapshots, incident_dt)
        flags = retention_flags(snapshots)
        render_snapshots(report, snapshots, recover, flags)
    except _cli.CliError as e:
        report.line("  snapshot inventory unavailable: %s" % e)
        warn_and_degrade(report, "ecs:DescribeSnapshots", e)
        recover = {"verdict": "no-window", "points": [], "latest": []}

    report.line("")
    report.line("== File-backup restore jobs (hbr:DescribeRestoreJobs2) ==")
    # gather_restore_jobs queries both documented vault editions and degrades
    # per edition on its own; it does not raise.
    restore_jobs = gather_restore_jobs(report, args.region_id, args.profile)
    if not restore_jobs:
        report.line("  no ECS file-backup restore jobs on record (empty "
                    "is valid). Reminder: file backup restores "
                    "directories of a running instance; it does not "
                    "replace a system-disk snapshot rollback")
    for job in restore_jobs[:10]:
        report.line("    %s | %s | %s | %s"
                    % (first_of(job, ("JobId",), "?"),
                       first_of(job, ("Status",), "?"),
                       first_of(job, ("CreateTime", "RestoreId"), "-"),
                       first_of(job, ("RestoreType",), "-")))

    # ---- Layer 2 / Layer 3 gated operations --------------------------------
    if args.guest_check:
        report.line("")
        report.line("== Gated in-guest forensics (%s -- confirmed this run) "
                    "== " % args.guest_check)
        guest_result = run_guest_probe(report, args.region_id, instance_id,
                                       args.os_type, args.guest_check,
                                       args.profile)

    if args.create_evidence_snapshot:
        report.line("")
        report.line("== Gated evidence snapshot (confirmed this run) ==")
        report.line("  %s" % SNAPSHOT_FIRST_RULE)
        snapshot_result = create_evidence_snapshot(
            report, args.region_id, args.disk_id, args.profile)

    # ---- guidance -----------------------------------------------------------
    if not branch or branch in ("other", "entry"):
        counts = alert_summary.get("counts", {}) if alert_summary else {}
        branch = max(counts, key=counts.get) if counts else None

    report.line("")
    report.line("== Recommended next actions (manual steps + gates) ==")
    unresolved = bool(alert_summary.get("scoped")) if alert_summary else False
    cpu_suspect = any(r.get("peak") and
                      r["peak"] >= CMS_CPU_SUSPECT_PERCENT
                      for r in cpu_readings)
    next_action = build_next_actions(branch or "other", recover, cpu_suspect,
                                     unresolved, exposure_rows,
                                     guest_result is not None,
                                     snapshot_result is not None)
    report.line("  %s" % next_action)
    report.line("  %s" % SNAPSHOT_FIRST_RULE)
    report.line("  %s" % SHARED_RESPONSIBILITY_NOTICE)
    render_hardening(report)
    render_fallback_table(report)

    # ---- status -------------------------------------------------------------
    status = "OK" if not report.degradations else "DEGRADED"
    report.line("")
    if report.degradations:
        report.line("-- Graceful Degradation Log --")
        for source, reason in report.degradations:
            report.line("  [DEGRADED] %s: %s" % (source, reason))
        report.line("")
    report.line("STATUS: %s" % status)
    report.line("NEXT_ACTION: %s" % next_action)

    if args.json:
        print(json.dumps({
            "session_id": session,
            "region": args.region_id,
            "instance_id": instance_id,
            "account_id_masked": account_id[-4:] and "****" + account_id[-4:],
            "branch": branch,
            "alerts": alert_summary,
            "version_config": {k: version_config.get(k) for k in
                               ("Version", "PostPayVersion")
                               if k in version_config},
            "field_statistics": field_stats,
            "exposure_rows": len(exposure_rows),
            "cpu_readings": cpu_readings,
            "recoverability": recover["verdict"],
            "recovery_points": [s.get("SnapshotId")
                                for s in recover["points"][:5]],
            "restore_jobs": len(restore_jobs),
            "guest_forensics": {"key": args.guest_check,
                                "ok": guest_result is not None}
            if args.guest_check else None,
            "evidence_snapshot": snapshot_result,
            "degradations": [{"source": s, "reason": r}
                             for s, r in report.degradations],
            "status": status,
            "next_action": next_action,
        }, ensure_ascii=False, indent=2))
        # The output contract lines are visible in BOTH modes.
        print("STATUS: %s" % status)
        print("NEXT_ACTION: %s" % next_action)
    else:
        print(report.render())

    if args.report_file:
        write_report_file(args.report_file, report)

    return 0


def write_report_file(path, report):
    """Write the evidence report to a NEW operator-chosen local path. An
    existing file is refused: the report never overwrites anything."""
    if os.path.exists(path):
        print("[WARN] --report-file %s already exists; refusing to "
              "overwrite (the skill only creates new files)" % path,
              file=sys.stderr)
        return
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(report.render() + "\n")
        print("[notice] report written to %s" % path, file=sys.stderr)
    except OSError as e:
        print("[WARN] could not write --report-file: %s" % e,
              file=sys.stderr)


# ---------------------------------------------------------------------------
# Inline self-test of the pure helpers (KB layer 1)
# ---------------------------------------------------------------------------

def _self_test():
    # parse_iso_time: normal / boundary / invalid
    dt, tzf = parse_iso_time("2026-08-12 02:30")
    assert tzf is False and dt.tzinfo is not None
    dt, tzf = parse_iso_time("2026-08-09T14:25:30Z")
    assert tzf is True and dt.month == 8 and dt.day == 9
    dt, _ = parse_iso_time("1500000000")
    assert dt.year > 2000
    for bad in ("", "not-a-time", None):
        try:
            parse_iso_time(bad)
            raise AssertionError("parse_iso_time accepted %r" % bad)
        except ValueError:
            pass

    # classify_symptom
    assert classify_symptom("my server files are encrypted by ransomware")[0] \
        == "ransom"
    assert classify_symptom("服务器中了勒索病毒")[0] == "ransom"
    assert classify_symptom("ECS keeps raising mining alerts")[0] == "miner"
    assert classify_symptom("服务器被挖矿木马入侵")[0] == "miner"
    assert classify_symptom("website redirected to gambling pages")[0] \
        == "webshell"
    assert classify_symptom("网站被挂马了")[0] == "webshell"
    assert classify_symptom("disk is full, no space left")[1]["target"] \
        == "disk-capacity"
    assert classify_symptom("please refund my subscription money")[1] \
        ["target"] == "human-channel"
    assert classify_symptom("hello there") == (None, None)

    # classify_alert
    assert classify_alert({"Name": "Malicious software (trojan) program"}) \
        [0] == "miner"
    assert classify_alert({"Name": "Suspicious mining pool connection"})[0] \
        == "miner"
    assert classify_alert({"Name": "Webshell file detected"})[0] == "webshell"
    assert classify_alert({"Name": "Brute force logon failed"})[0] == "entry"
    assert classify_alert({})[0] == "other"
    assert classify_alert("garbage")[0] == "other"

    # judge_recoverability
    snaps = [
        {"SnapshotId": "s-old", "Status": "accomplished",
         "CreationTime": "2026-08-01T00:00:00Z", "SourceDiskId": "d-a"},
        {"SnapshotId": "s-mid", "Status": "accomplished",
         "CreationTime": "2026-08-15T00:00:00Z", "SourceDiskId": "d-a"},
        {"SnapshotId": "s-prog", "Status": "progressing",
         "CreationTime": "2026-08-20T00:00:00Z", "SourceDiskId": "d-b"},
    ]
    inc = datetime(2026, 8, 20, 3, 0, tzinfo=timezone.utc)
    verdict = judge_recoverability(snaps, inc)
    assert verdict["verdict"] == "restorable"
    assert [s["SnapshotId"] for s in verdict["points"]] == ["s-mid", "s-old"]
    assert judge_recoverability(snaps, None)["verdict"] == "no-window"
    assert judge_recoverability([], inc)["verdict"] == "none-found"
    assert judge_recoverability(snaps, datetime(
        2026, 7, 1, tzinfo=timezone.utc))["verdict"] == "none-found"

    # retention_flags
    flags = retention_flags([{"SnapshotId": "s-x", "RetentionDays": "1"},
                             {"SnapshotId": "s-y", "RetentionDays": 30},
                             {"SnapshotId": "s-z"}])
    assert len(flags) == 1 and "s-x" in flags[0]

    # summarize_datapoints
    raw = json.dumps([{"Average": 90.0, "Maximum": 100.0},
                      {"Average": 80.0, "Maximum": 95.0}])
    count, avg, peak = summarize_datapoints(raw)
    assert count == 2 and avg == 85.0 and peak == 100.0
    assert summarize_datapoints(None)[:2] == (None, None)
    assert summarize_datapoints("not json") == (None, None, None)

    # validate_args
    base = dict(region_id="cn-hangzhou", instance_id="i-abc123456",
                public_ip=None, incident_time=None, symptom=None,
                os_type="linux", domain=None, guest_check=None,
                create_evidence_snapshot=False, disk_id=None,
                confirmed=False, report_file=None, json=False,
                profile=None, cli_timeout=None)
    assert validate_args(argparse.Namespace(**base)) is None
    # missing region
    assert validate_args(argparse.Namespace(**dict(base, region_id=None)))
    # invalid region shape
    assert validate_args(argparse.Namespace(**dict(base, region_id="HZ!")))
    # both locators at once is refused
    assert validate_args(argparse.Namespace(**dict(
        base, public_ip="47.0.0.1")))
    # no locator at all
    assert validate_args(argparse.Namespace(**dict(
        base, instance_id=None, public_ip=None)))
    # invalid instance id
    assert validate_args(argparse.Namespace(**dict(
        base, instance_id="i-bad id")))
    # invalid ip
    assert validate_args(argparse.Namespace(**dict(
        base, instance_id=None, public_ip="not-an-ip")))
    assert validate_args(argparse.Namespace(**dict(
        base, incident_time="bad")))
    assert validate_args(argparse.Namespace(**dict(
        base, create_evidence_snapshot=True, disk_id="nope")))
    assert validate_args(argparse.Namespace(**dict(
        base, create_evidence_snapshot=True, disk_id="d-abc123456"))) is None

    # build_next_actions: every branch / verdict combo yields a string
    for branch in ("ransom", "miner", "webshell", None):
        for verdict in ("restorable", "no-window", "none-found"):
            rec = {"verdict": verdict,
                   "points": [{"SnapshotId": "s-x"}] if verdict ==
                   "restorable" else [], "latest": []}
            out = build_next_actions(branch, rec, True, True, [{}], False,
                                     False)
            assert isinstance(out, str) and out

    # Cloud Backup query constants: only documented values, page size inside
    # the documented 1..99 window.
    assert HBR_RESTORE_TYPE == "ECS_FILE"
    assert HBR_RESTORE_EDITIONS == ("STANDARD", "BASIC")
    assert 1 <= HBR_PAGE_SIZE <= 99

    # The frozen guest whitelist: four categories, both OS families, and no
    # command carrying a side effect (no redirection, pipe, kill or writer).
    for os_type in ("linux", "windows"):
        assert tuple(sorted(GUEST_COMMANDS[os_type])) == \
            tuple(sorted(GUEST_COMMAND_CATEGORIES))
        for key, entry in GUEST_COMMANDS[os_type].items():
            cmd = entry["command"]
            for banned in (">", ">>", "|", "rm ", "mv ", "kill", "systemctl "
                           "stop", "shutdown", "reboot", "dd "):
                assert banned not in cmd, (os_type, key, banned)
            assert entry["category"] and entry["read_how"]

    # Handoff map integrity: every anchor that routes away must resolve to a
    # target, and every target must name either a sibling skill or a manual
    # note -- a dangling route would silently drop the customer.
    for entry in SYMPTOM_ANCHORS:
        if entry.get("action") != "handoff":
            continue
        target = HANDOFF_TARGETS.get(entry["target"])
        assert target is not None, entry["target"]
        assert target.get("skill") or target.get("manual_note"), entry["target"]
        assert target.get("evidence_to_attach"), entry["target"]
    for name, target in HANDOFF_TARGETS.items():
        assert target.get("skill") or target.get("manual_note"), name

    print("[ok] host_intrusion_diagnosis.py self-test passed", file=sys.stderr)


_self_test()


if __name__ == "__main__":
    sys.exit(main())
