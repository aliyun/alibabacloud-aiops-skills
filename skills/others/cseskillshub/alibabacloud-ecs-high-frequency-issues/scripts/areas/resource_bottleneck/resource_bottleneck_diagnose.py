#!/usr/bin/env python3
"""ECS resource-bottleneck diagnosis entry point (CPU / memory / load / frozen).

WHAT THIS SKILL IS
    A symptom-first diagnosis chain for ECS instances that lag, freeze, or run
    with CPU / memory / load pinned: it joins instance-spec facts, disk
    inventory, CloudMonitor metric series and (behind a confirmation gate) one
    whitelisted in-guest inspection command, then renders an evidence-bound
    report with rule IDs, statistics calibers and explicit handoffs.

WHAT IT MAY CALL (complete whitelist; anything else is prohibited by design)
    ecs DescribeInstances / DescribeInstanceAttribute / DescribeDisks /
        DescribeInvocations      -> control-plane records (Describe/Get style)
    ecs RunCommand               -> THE ONLY gated side-effecting call: sends
        exactly ONE command that fullmatches the in-guest inspection whitelist
        (top / ps / free / vmstat / uptime / sar / iostat / atop -r replay /
        Get-Process / Get-Counter ...) and only after the customer's approval
        for this run is quoted on the command line. What runs in the guest
        inspects state and changes nothing; the dispatch itself is a write-flavored
        call, which is why this skill makes no observation-only claim about itself.
    cms DescribeMetricLast / DescribeMetricList -> monitoring series
    sts GetCallerIdentity        -> credential-chain proof + account label

WHAT IT NEVER DOES
    No resource changes of any kind (no attribute edits, no snapshots, no
    deletions, no restarts, no stop/start, no resizing, no refunds, no security
    rules). Fixing actions -- snapshot before reboot, reboot at low peak, swap
    or virtual-memory setup, parameter tuning, IP blocking -- are emitted as
    manual guidance only. No credential handling: the default CLI chain is the
    only source, and all output is credential-masked.

Usage examples
    python3 scripts/areas/resource_bottleneck/resource_bottleneck_diagnose.py --region-id cn-hangzhou \
        --instance-id i-bp1example0001 --symptom lag --hours 6
    python3 scripts/areas/resource_bottleneck/resource_bottleneck_diagnose.py --region-id cn-shenzhen \
        --instance-id i-wz9example0002 --symptom memory \
        --start-time "2026-08-26T08:00:00Z" --end-time "2026-08-26T09:30:00Z"
    python3 scripts/areas/resource_bottleneck/resource_bottleneck_diagnose.py --region-id cn-hangzhou \
        --instance-id i-bp1example0001 --guest-command "top -bn1" \
        --confirmation "customer replied: yes, run top -bn1 now"
    python3 scripts/areas/resource_bottleneck/resource_bottleneck_diagnose.py --check-auth-only
    python3 scripts/areas/resource_bottleneck/resource_bottleneck_diagnose.py --self-test
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

import cms_metrics
import guest_evidence
from _cli import (
    CliError,
    build_user_agent,
    mask_credentials,
    new_session_id,
    paginate,
    run_cli,
)
from _constants import (
    ACTION_DESCRIBE_INSTANCE_ATTRIBUTE,
    ACTION_DESCRIBE_INSTANCES,
    ACTION_DESCRIBE_DISKS,
    API_WHITELIST_ACTIONS,
    ARM_FAMILY_PATTERN,
    BURSTABLE_FAMILY_PATTERN,
    BURSTABLE_PATTERN,
    CLI_TIMEOUT_SECONDS,
    CMS_API_VERSION,
    CO_PEAK_PROXIMITY_RATIO,
    CODE_IMPLICIT_DENY,
    CODE_NO_PERMISSION,
    DEFAULT_PERIOD_SECONDS,
    ECS_API_VERSION,
    GAPS_DECLARED,
    MAX_OUTPUT_SNIPPET_LINES,
    MAX_REPORT_WARNINGS,
    METRICS_EVIDENCED,
    OUTPUT_SNIPPET_MARKER,
    PAGE_SIZE,
    PRODUCT_ECS,
    RAM_ACTION_NAMES,
    RULES,
    RUN_TYPE_BY_OS,
    SATURATION_CPU_PCT,
    SATURATION_MEM_PCT,
    SKILL_NAME,
    SMALL_SPEC_MEM_MIB,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
    STS_API_VERSION,
    TINY_SPEC_MEM_MIB,
    WINDOW_HOURS_DEFAULT,
    WINDOW_HOURS_MAX,
    WINDOW_HOURS_MIN,
)
from sts_token import fetch_caller_identity, uid_traceability_label

EXIT_BY_STATUS = {STATUS_OK: 0, STATUS_DEGRADED: 1, STATUS_FAIL: 2}

INSTANCE_ID_PATTERN = re.compile(r"^i-[A-Za-z0-9-]{3,64}$")
REGION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$")
ISO_Z_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

# Area / unit / caliber per evidenced metric. Caliber text is printed next to
# every reading because ticket T-46B31B3D (mean vs peak) and T-6F5DD9E4 (host
# view vs guest cpu_total) show the metric NAME alone causes disputes.
METRIC_PROFILE = {
    "CPUUtilization": {
        "area": "compute", "unit": "%",
        "caliber": "host-view period average; ARM instances add a fixed "
                   "virtualization overhead here (rule R7)",
    },
    "memory_usedutilization": {
        "area": "memory", "unit": "%",
        "caliber": "OS-level metric, requires the CloudMonitor agent in the guest",
    },
    "DiskReadBPS": {
        "area": "disk-io", "unit": "Byte/s",
        "caliber": "OS-level read throughput; requires the CloudMonitor agent",
    },
    "DiskWriteBPS": {
        "area": "disk-io", "unit": "Byte/s",
        "caliber": "OS-level write throughput; requires the CloudMonitor agent",
    },
    "IntranetInRate": {
        "area": "network(intranet)", "unit": "bit/s",
        "caliber": "intranet inbound rate; public-bandwidth metrics are an "
                   "open gap, see the gaps section",
    },
}

# Heuristics used to call a reading "high". Working values only: they are
# printed verbatim so every conclusion is re-checkable, and the pending
# ratification of official thresholds is declared in the report.
DISK_ELEVATED_OF_PEAK = 0.85

GUIDANCE_HEADER = (
    "Manual steps below are operator-executed. This skill dispatches nothing "
    "besides the gated whitelisted inspection command and never applies a fix."
)


# --------------------------------------------------------------------------- #
# Argument handling
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resource_bottleneck_diagnose.py",
        description=(
            "ECS resource-bottleneck diagnosis: joins instance specs, disk "
            "inventory, CloudMonitor series and gated in-guest inspection "
            "readings into an evidence-bound report. Fix actions are manual "
            "guidance only."
        ),
    )
    parser.add_argument("--region-id", dest="region_id", default=None,
                        help="Region id of the instance, e.g. cn-hangzhou "
                             "(required for any scoped run; never guessed).")
    parser.add_argument("--instance-id", dest="instance_id", default=None,
                        help="Target ECS instance id, e.g. i-bp1....")
    parser.add_argument("--symptom", dest="symptom",
                        choices=("auto", "lag", "cpu", "memory", "load", "oom",
                                 "atop", "report-review"),
                        default="auto",
                        help="Customer-visible symptom hint for the triage area.")
    parser.add_argument("--hours", dest="hours", type=int,
                        default=WINDOW_HOURS_DEFAULT,
                        help="Look-back window for the metric series, in hours "
                             "(default {0}, range {1}-{2}).".format(
                                 WINDOW_HOURS_DEFAULT, WINDOW_HOURS_MIN,
                                 WINDOW_HOURS_MAX))
    parser.add_argument("--start-time", dest="start_time", default=None,
                        help="Explicit window start, ISO-8601 UTC (YYYY-MM-DDThh:mm:ssZ). "
                             "Overrides --hours together with --end-time.")
    parser.add_argument("--end-time", dest="end_time", default=None,
                        help="Explicit window end, ISO-8601 UTC. Overrides --hours "
                             "together with --start-time.")
    parser.add_argument("--guest-command", dest="guest_command", default=None,
                        help="ONE whitelisted in-guest inspection command "
                             "(e.g. 'top -bn1'). Requires --confirmation.")
    parser.add_argument("--confirmation", dest="confirmation", default=None,
                        help="Verbatim quote of the customer's approval of THIS "
                             "command for THIS run; placeholder answers are rejected.")
    parser.add_argument("--os-type", dest="os_type", default=None,
                        choices=(None, "linux", "windows"),
                        help="Override guest OS family for whitelist selection; "
                             "default derives it from DescribeInstances.")
    parser.add_argument("--report-file", dest="report_file", default=None,
                        help="Write the full JSON report to a NEW file at this "
                             "path (create-only; existing paths are rejected).")
    parser.add_argument("--timeout", dest="timeout", type=int,
                        default=CLI_TIMEOUT_SECONDS,
                        help="Per-call CLI timeout in seconds (default {0}).".format(
                            CLI_TIMEOUT_SECONDS))
    parser.add_argument("--max-pages", dest="max_pages", type=int, default=10,
                        help="Ceiling on paging requests per list action (default 10).")
    parser.add_argument("--output", dest="output", choices=("text", "json"),
                        default="text", help="Report rendering (default text).")
    parser.add_argument("--check-auth-only", dest="check_auth_only",
                        action="store_true", help="Only verify caller identity and exit.")
    parser.add_argument("--self-test", dest="self_test", action="store_true",
                        help="Run offline boundary assertions and exit.")
    parser.add_argument("--verbose", dest="verbose", action="store_true",
                        help="Include raw metric samples and full rule catalog.")
    return parser


def validate(args: argparse.Namespace) -> List[str]:
    problems: List[str] = []
    if args.self_test or args.check_auth_only:
        return problems
    if not args.region_id:
        problems.append(
            "--region-id is required: ECS resources are regional and the "
            "region is never guessed.")
    elif not REGION_PATTERN.match(args.region_id):
        problems.append("--region-id does not look like a region id.")
    if not args.instance_id:
        problems.append(
            "--instance-id is required: without the target instance no evidence "
            "scope exists (ask the customer for the instance id or public ip first).")
    elif not INSTANCE_ID_PATTERN.match(args.instance_id):
        problems.append("--instance-id does not match the i-... form.")
    if not (WINDOW_HOURS_MIN <= args.hours <= WINDOW_HOURS_MAX):
        problems.append("--hours must be between {0} and {1}.".format(
            WINDOW_HOURS_MIN, WINDOW_HOURS_MAX))
    for name in ("start_time", "end_time"):
        value = getattr(args, name)
        if value and not ISO_Z_PATTERN.match(value):
            problems.append("--{0} must be ISO-8601 UTC like 2026-08-26T08:00:00Z.".format(
                name.replace("_", "-")))
    if bool(args.start_time) != bool(args.end_time):
        problems.append("--start-time and --end-time must be given together.")
    if args.timeout < 1:
        problems.append("--timeout must be >= 1 second.")
    return problems


def resolve_window(args: argparse.Namespace) -> Dict[str, str]:
    if args.start_time and args.end_time:
        return {"StartTime": args.start_time, "EndTime": args.end_time,
                "source": "explicit-customer-window"}
    window = cms_metrics.metric_window(args.hours)
    window["source"] = "auto-default-last-{0}h".format(args.hours)
    return window


# --------------------------------------------------------------------------- #
# Evidence collection
# --------------------------------------------------------------------------- #
def collect_instance(
    args: argparse.Namespace, session_id: str,
    warnings: List[str], errors: List[Dict[str, str]],
) -> Dict[str, Any]:
    """DescribeInstances scoped to the one target instance id."""
    record: Dict[str, Any] = {"found": False, "data": {}, "state": "failed"}
    try:
        payload = run_cli(
            PRODUCT_ECS, ACTION_DESCRIBE_INSTANCES,
            params={
                "RegionId": args.region_id,
                "InstanceIds": json.dumps([args.instance_id], separators=(",", ":")),
                "PageSize": 100, "PageNumber": 1,
            },
            session_id=session_id, timeout=args.timeout, warnings=warnings,
        )
    except CliError as exc:
        errors.append({"action": ACTION_DESCRIBE_INSTANCES, "detail": str(exc)})
        return record
    items = ((payload.get("Instances") or {}).get("Instance")) or []
    for item in items:
        if isinstance(item, dict) and str(item.get("InstanceId")) == args.instance_id:
            record["found"] = True
            record["data"] = item
            record["state"] = "ok"
            return record
    record["state"] = "not-found"
    if payload.get("RequestId"):
        record["request_id"] = str(payload["RequestId"])
    return record


def collect_attribute(
    args: argparse.Namespace, session_id: str,
    warnings: List[str], errors: List[Dict[str, str]],
) -> Dict[str, Any]:
    """DescribeInstanceAttribute: the spec cross-check (vCPU / memory of record)."""
    try:
        payload = run_cli(
            PRODUCT_ECS, ACTION_DESCRIBE_INSTANCE_ATTRIBUTE,
            params={"InstanceId": args.instance_id},
            session_id=session_id, timeout=args.timeout, warnings=warnings,
        )
    except CliError as exc:
        errors.append({"action": ACTION_DESCRIBE_INSTANCE_ATTRIBUTE, "detail": str(exc)})
        return {}
    return payload if isinstance(payload, dict) else {}


def collect_disks(
    args: argparse.Namespace, session_id: str,
    warnings: List[str], errors: List[Dict[str, str]],
) -> Tuple[List[Dict[str, Any]], str]:
    try:
        items, state = paginate(
            PRODUCT_ECS, ACTION_DESCRIBE_DISKS,
            {"RegionId": args.region_id, "InstanceId": args.instance_id},
            "Disk",
            session_id=session_id, page_size=PAGE_SIZE, max_pages=args.max_pages,
            warnings=warnings, nested_keys=("Disks", "Disk"), timeout=args.timeout,
        )
    except CliError as exc:
        errors.append({"action": ACTION_DESCRIBE_DISKS, "detail": str(exc)})
        return [], "failed"
    return items, state


def collect_metrics(
    instance_id: str, window: Dict[str, str], session_id: str, timeout: int,
    warnings: List[str], errors: List[Dict[str, str]],
) -> Dict[str, Dict[str, Any]]:
    """Latest + series per evidenced metric. Missing == recorded, never assumed."""
    evidence: Dict[str, Dict[str, Any]] = {}
    for metric in METRICS_EVIDENCED:
        last = cms_metrics.fetch_metric_last(
            instance_id, metric, session_id, timeout, warnings=warnings)
        series = cms_metrics.fetch_metric_series(
            instance_id, metric, window, session_id, timeout, warnings=warnings)
        entry: Dict[str, Any] = {
            "last": cms_metrics.point_value((last.get("points") or [{}])[0])
            if last.get("points") else None,
            "stats": series.get("stats") or {},
            "points": series.get("points") or [],
            "missing": (not last.get("points")) and (not series.get("stats")),
        }
        detail = last.get("error") or series.get("error")
        if detail:
            entry["error"] = str(detail)
            errors.append({"action": "DescribeMetricLast/List:{0}".format(metric),
                           "detail": str(detail)})
        evidence[metric] = entry
    return evidence


# --------------------------------------------------------------------------- #
# Rule engine (pure, self-tested)
# --------------------------------------------------------------------------- #
def instance_areas(evidence: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Condense the metric evidence into the booleans the rules consume."""
    areas: Dict[str, Any] = {}
    cpu = evidence.get("CPUUtilization", {})
    mem = evidence.get("memory_usedutilization", {})
    dread = evidence.get("DiskReadBPS", {})
    dwrite = evidence.get("DiskWriteBPS", {})
    # A metric that is wholly absent from the evidence (empty entry) is a data
    # gap too, not "present with data": only an existing entry carries the
    # upstream "missing" flag. Per references/resource-bottleneck__diagnosis-rules.md, an absent
    # reading must apply R6 and withhold the conclusion, never imply any_data.
    areas["cpu_missing"] = (not cpu) or bool(cpu.get("missing"))
    areas["mem_missing"] = (not mem) or bool(mem.get("missing"))
    areas["disk_missing"] = ((not dread) or bool(dread.get("missing"))) and \
        ((not dwrite) or bool(dwrite.get("missing")))
    areas["cpu_high"] = float((cpu.get("stats") or {}).get("mx") or 0) >= SATURATION_CPU_PCT
    areas["mem_high"] = float((mem.get("stats") or {}).get("avg") or 0) >= SATURATION_MEM_PCT
    disk_peak = max(
        float((dread.get("stats") or {}).get("mx") or 0),
        float((dwrite.get("stats") or {}).get("mx") or 0))
    disk_avg = max(
        float((dread.get("stats") or {}).get("avg") or 0),
        float((dwrite.get("stats") or {}).get("avg") or 0))
    areas["disk_peak"] = disk_peak
    areas["disk_elevated"] = disk_peak > 0 and disk_avg >= disk_peak * DISK_ELEVATED_OF_PEAK
    areas["any_data"] = not (areas["cpu_missing"] and areas["mem_missing"] and areas["disk_missing"])
    return areas


def co_peak(evidence: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """First timestamp where CPU and either disk-BPS series are jointly near peak."""
    cpu = evidence.get("CPUUtilization", {})
    for metric in ("DiskReadBPS", "DiskWriteBPS"):
        other = evidence.get(metric, {})
        hit = cms_metrics.find_co_peaks(
            cpu.get("stats") or {}, cpu.get("points") or [],
            other.get("stats") or {}, other.get("points") or [],
            ratio=CO_PEAK_PROXIMITY_RATIO)
        if hit:
            hit["metric"] = metric
            hit["timestamp_iso"] = cms_metrics.iso_from_ms(hit.get("timestamp_ms"))
            return hit
    return None


def evaluate(
    args: argparse.Namespace,
    instance: Dict[str, Any],
    attribute: Dict[str, Any],
    disks: List[Dict[str, Any]],
    evidence: Dict[str, Dict[str, Any]],
    guest: Optional[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Apply rules R1-R9. Every finding cites the reading that supports it."""
    findings: List[Dict[str, str]] = []
    areas = instance_areas(evidence)
    guest_flags = guest_signal_flags(guest)

    def stat(metric: str, key: str) -> str:
        value = (evidence.get(metric) or {}).get("stats", {}).get(key)
        return "not returned" if value is None else str(value)

    def iso_peak(metric: str) -> str:
        return cms_metrics.iso_from_ms(
            (evidence.get(metric) or {}).get("stats", {}).get("peak_ts_ms"))

    # R8 first: without instance facts nothing else is trustworthy.
    if not instance.get("found"):
        findings.append({
            "id": "R8", "level": "high", "rule": "R8",
            "text": "Instance {0} was not returned by DescribeInstances in region {1}: "
                    "the id/region pair is wrong, the instance is in another account, "
                    "or it is not an ECS instance at all. No assumption made; nothing "
                    "else was judged.".format(args.instance_id, args.region_id),
        })
        return findings

    # Spec priors (small instance / burstable / ARM) come with every conclusion.
    memory_mib = _as_int(instance["data"].get("Memory")) or _as_int(attribute.get("Memory"))
    cpu_count = _as_int(instance["data"].get("Cpu")) or _as_int(attribute.get("Cpu"))
    instance_type = str(instance["data"].get("InstanceType") or attribute.get("InstanceType") or "")
    family = str(instance["data"].get("InstanceTypeFamily") or "")
    if memory_mib and memory_mib <= TINY_SPEC_MEM_MIB:
        findings.append({
            "id": "P1", "level": "high", "rule": "prior",
            "text": "Spec prior: {0} vCPU / {1} MiB is a tiny instance. On such "
                    "sizes ordinary service startup consumes most of the memory "
                    "(tickets T-B8B16499 / T-D25A9845); percentage and absolute "
                    "value must be read together.".format(cpu_count or "not returned", memory_mib),
        })
    elif memory_mib and memory_mib <= SMALL_SPEC_MEM_MIB:
        findings.append({
            "id": "P2", "level": "info", "rule": "prior",
            "text": "Spec prior: {0} MiB total memory is a small instance; the "
                    "memory-exhaustion chain (R1) is statistically likely whenever "
                    "the memory area reads high.".format(memory_mib),
        })
    if BURSTABLE_PATTERN.match(instance_type) or BURSTABLE_FAMILY_PATTERN.match(family):
        findings.append({
            "id": "P3", "level": "info", "rule": "prior",
            "text": "Spec prior: instance type {0} is a burstable t-series: a 100% CPU reading "
                    "means the burst window is spending credits (baseline is a "
                    "small fixed percentage; sustained 100% after credit exhaustion "
                    "in unconstrained mode bills surplus credits). No official "
                    "credit-balance reading is available to this skill, so this is "
                    "the caliber note, not a measurement (ticket T-408C886A).".format(
                        instance_type or "not returned"),
        })
    if ARM_FAMILY_PATTERN.search(instance_type) or ARM_FAMILY_PATTERN.search(family):
        findings.append({
            "id": "R7", "level": "info", "rule": "R7",
            "text": "Instance type {0} is on an ARM (Yitian) family: the console "
                    "host-view CPU includes a fixed virtualization overhead, so the "
                    "guest-internal cpu_total reading is lower and is the correct "
                    "business/alerting caliber. Qualitative only (ticket T-6F5DD9E4; "
                    "no official document located - evidence level: ticket-stated).".format(
                        instance_type or "not returned"),
        })
    status = str(instance["data"].get("Status") or "")
    if status and status.lower() != "running":
        findings.append({
            "id": "R8b", "level": "warn", "rule": "R8",
            "text": "Instance status from the control plane is {0}, not Running: "
                    "boot / lifecycle issues belong to the instance-state "
                    "diagnosis tier, not to resource-bottleneck analysis.".format(status),
        })

    # R1: the dominant chain (memory -> paging/kswapd0 -> IO -> freeze).
    if areas["mem_high"] and (guest_flags["kswapd"] or areas["disk_elevated"] or areas["cpu_high"]):
        findings.append({
            "id": "R1", "level": "high", "rule": "R1",
            "text": "Memory-driven chain suspected: memory avg {0}% (mx {1}%) with "
                    "cpu mx {2}% at {3} and disk BPS mx {4} B/s at {5}{6}. This is the "
                    "most frequent freeze pattern in this tier's tickets: the visible "
                    "symptom is lag/CPU but the root area is memory.".format(
                        stat("memory_usedutilization", "avg"),
                        stat("memory_usedutilization", "mx"),
                        stat("CPUUtilization", "mx"), iso_peak("CPUUtilization"),
                        "{0:.0f}".format(areas["disk_peak"]), iso_peak("DiskWriteBPS"),
                        " plus in-guest kswapd/OOM evidence" if guest_flags["kswapd"] or
                        guest_flags["oom"] else ""),
        })
    elif areas["mem_high"]:
        findings.append({
            "id": "R1b", "level": "high", "rule": "R1",
            "text": "Memory usage avg {0}% (mx {1}%) over the window: the memory area "
                    "is the primary suspect even though paging/IO corroboration is "
                    "not visible from the cloud side yet.".format(
                        stat("memory_usedutilization", "avg"),
                        stat("memory_usedutilization", "mx")),
        })

    # R2: compute saturation with the other areas calm.
    if areas["cpu_high"] and not areas["mem_high"]:
        findings.append({
            "id": "R2", "level": "high", "rule": "R2",
            "text": "Compute saturation: CPU mx {0}% (avg {1}%, peak at {2}) while "
                    "memory avg is {3}%. Attribution needs in-guest process evidence: "
                    "the cloud side cannot name the eating process (rule R2); run the "
                    "gated inspection (top -bn1 or ps aux --sort=-%cpu | head -n 10).".format(
                        stat("CPUUtilization", "mx"), stat("CPUUtilization", "avg"),
                        iso_peak("CPUUtilization"),
                        stat("memory_usedutilization", "avg")),
        })

    # R3: load caliber split.
    if args.symptom == "load" and not areas["cpu_high"]:
        findings.append({
            "id": "R3", "level": "info", "rule": "R3",
            "text": "Load complaint without a high CPU reading: the CloudMonitor load "
                    "metric name is unratified, so this run answers from the CPU area "
                    "only (mx {0}%). High load with idle CPU usually means D-state / "
                    "IO wait: confirm in-guest with vmstat 1 3 (b column) and iostat -x "
                    "1 3, then hand off on rule R4 if IO-bound.".format(
                        stat("CPUUtilization", "mx")),
        })

    # R4: co-saturation of CPU and disk BPS -> operation correlation time point.
    peak = co_peak(evidence)
    if peak:
        findings.append({
            "id": "R4", "level": "high", "rule": "R4",
            "text": "Joint spike detected: CPU and {0} are both within {1:.0f}% of their "
                    "window peaks at {2} (caliber: CloudMonitor period max). Use that "
                    "timestamp for the operation-correlation question (what was "
                    "installed/restarted/backfilled then?), and confirm the disk area "
                    "against the {3} attached disk(s) from DescribeDisks before any "
                    "IO ceiling is claimed.".format(
                        peak["metric"],
                        (1.0 - CO_PEAK_PROXIMITY_RATIO) * 100.0,
                        peak["timestamp_iso"], len(disks)),
        })

    # R5: negative conclusion -- legitimate, useful output.
    if areas["any_data"] and not any((areas["cpu_high"], areas["mem_high"], areas["disk_elevated"])) \
            and not peak and not any(guest_flags.values()):
        findings.append({
            "id": "R5", "level": "ok", "rule": "R5",
            "text": "Negative finding on the evidenced areas: over the window "
                    "cpu mx {0}% / mem avg {1}% / disk mx {2} B/s show no resource "
                    "side bottleneck. 'Not the resources' is a valid conclusion: "
                    "continue at the application, public-network or security area "
                    "per the handoff matrix (tickets T-4C13A2DB / T-F5D78C4B).".format(
                        stat("CPUUtilization", "mx"),
                        stat("memory_usedutilization", "avg"),
                        "{0:.0f}".format(areas["disk_peak"])),
        })

    # R6: explicit evidence gaps (metric missing / agent missing).
    missing_areas = []
    if areas["mem_missing"]:
        missing_areas.append("memory_usedutilization (OS metric needs the "
                            "CloudMonitor agent; its absence usually means the agent "
                            "is not installed)")
    if areas["cpu_missing"]:
        missing_areas.append("CPUUtilization")
    if areas["disk_missing"]:
        missing_areas.append("DiskReadBPS/DiskWriteBPS")
    for metric in missing_areas:
        findings.append({
            "id": "R6", "level": "warn", "rule": "R6",
            "text": "Evidence gap on {0}: no readings returned for the window. "
                    "Statements that would need this area are withheld rather than "
                    "estimated.".format(metric),
        })
    for gap in GAPS_DECLARED:
        if args.verbose:
            findings.append({"id": "R6g", "level": "info", "rule": "R6",
                             "text": "Open metric gap: {0}".format(gap)})

    # Guest-side overrides / confirmations.
    if guest_flags["blocked"]:
        findings.append({
            "id": "R4b", "level": "info", "rule": "R4",
            "text": "In-guest evidence shows a blocked/hung task: that process is a "
                    "victim of I/O stall, not the culprit (ticket T-BF2F77A0); judge "
                    "the IO area first.",
        })
    if guest_flags["oom"]:
        findings.append({
            "id": "R1c", "level": "high", "rule": "R1",
            "text": "In-guest OOM killer trace present: memory exhaustion already "
                    "reached process-kill level; state this as confirmed, not "
                    "suspected.",
        })
    return findings


def guest_signal_flags(guest: Optional[Dict[str, Any]]) -> Dict[str, bool]:
    """Pure condenser: which in-guest markers were seen in the capture."""
    flags = {"kswapd": False, "oom": False, "blocked": False}
    if not guest:
        return flags
    lowered = (guest.get("output") or "").lower()
    flags["kswapd"] = "kswapd" in lowered
    flags["oom"] = "out of memory" in lowered or "oom-killer" in lowered or "oom_kill" in lowered
    flags["blocked"] = "blocked for more than" in lowered
    return flags


def _as_int(value: Any) -> Optional[int]:
    try:
        if value in (None, ""):
            return None
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _text(record: Dict[str, Any], key: str) -> str:
    value = (record or {}).get(key)
    return "not returned" if value in (None, "") else str(value)


# --------------------------------------------------------------------------- #
# Manual guidance (what a human does next; never executed by this skill)
# --------------------------------------------------------------------------- #
def guidance_lines(findings: List[Dict[str, str]], areas: Dict[str, Any]) -> List[str]:
    rules = {item["rule"] for item in findings}
    lines: List[str] = [GUIDANCE_HEADER]
    if "R1" in " ".join(rules) or "R1b" in rules or "R1c" in rules or "R2" in rules:
        lines.append(
            "1. Snapshot first, then act (manual, customer-approved): in the ECS "
            "console create a snapshot of each disk before any reboot; snapshots "
            "are billed per usage until deleted, and a snapshot is usable for "
            "rollback once its progress passes the first percent.")
        lines.append(
            "2. If the instance is frozen, rebooting recovers it but is a manual "
            "step with three risks stated to the customer: business interruption "
            "(do it at low peak), unwritten in-memory data is lost (stop "
            "databases/caches cleanly first if reachable), and create the backup "
            "snapshot beforehand. This skill never restarts anything.")
    if "R1" in rules or "R1b" in rules or "R1c" in rules:
        lines.append(
            "3. Memory chain follow-up (manual): add swap / virtual memory per the "
            "official guides (Linux swap, or Windows virtual memory with its "
            "documented side effect of slower memory IO), tune the top memory "
            "consumer's own limits (e.g. a database buffer pool sized to the "
            "instance), and treat a small-spec instance as undersized by evidence, "
            "not by guesswork. None of these is executed by this skill.")
    if "R2" in rules:
        lines.append(
            "4. Compute saturation follow-up: attribute to a process with the gated "
            "inspection, ask the business whether the process and its volume are "
            "expected (normal load on a small spec vs anomaly vs external traffic), "
            "and only then choose optimize / restrict / resize -- all human calls.")
    if "R4" in rules or "R4b" in rules:
        lines.append(
            "5. IO / joint-spike follow-up: run the operation-correlation question "
            "at the detected timestamp, keep the IO ceiling question inside the "
            "disk-io diagnosis tier (this skill does not compute disk ceilings), "
            "and remember a blocked/hung process is a victim, not the culprit.")
    if "R5" in rules or areas.get("any_data"):
        lines.append(
            "6. Evidence for next time (manual, strongly advised): install the "
            "CloudMonitor agent and atop on the instance now, so a future freeze "
            "is reconstructible from atop -r history instead of guesswork. This is "
            "the closing step of nearly every ticket in this tier.")
    lines.append(
        "7. Never hand this skill a login password or key material: it neither "
        "asks nor stores them; credentials stay inside the default CLI chain of "
        "the machine running these scripts.")
    return lines


def boundary_lines() -> List[str]:
    return [
        "Out of scope for this skill (identify and hand off, never execute): "
        "disk IO ceiling and storage-backend questions -> disk-io diagnosis tier; "
        "capacity / inode -> disk-expand tier; boot and lifecycle -> instance-state "
        "tier; public bandwidth, DNS, ICP and TLS resets -> network tier; attacks, "
        "malicious processes, WAF -> security tier; spec change, refund, pricing -> "
        "billing/commercial humans; application tuning -> the owner's engineers.",
        "This skill performs no cloud change of its own: its single side-effecting "
        "capability (Cloud Assistant dispatch of one whitelisted inspection "
        "command, after quoted customer approval) is fully logged and reversible "
        "in the sense that nothing it can dispatch alters state.",
        "Handoff sentence template: 'Resource-side evidence collected and "
        "time-stamped; the remaining action (<name it>) is a human operation "
        "through the console with the stated risks, <here or in the adjacent "
        "tier>. '",
    ]


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def metric_table(evidence: Dict[str, Dict[str, Any]]) -> List[str]:
    lines = ["  metric | area | latest | avg | max | peak at | samples | caliber"]
    for metric in METRICS_EVIDENCED:
        entry = evidence.get(metric) or {}
        stats = entry.get("stats") or {}
        profile = METRIC_PROFILE.get(metric, {})

        def fmt(value: Any) -> str:
            return "-" if value is None else str(value)

        lines.append("  {0} | {1} | {2} | {3} | {4} | {5} | {6} | {7}".format(
            metric,
            profile.get("area", "?"),
            fmt(entry.get("last")) + (" " + profile.get("unit", "") if entry.get("last") is not None else ""),
            fmt(stats.get("avg")), fmt(stats.get("mx")),
            cms_metrics.iso_from_ms(stats.get("peak_ts_ms")),
            fmt(stats.get("count")),
            profile.get("caliber", ""),
        ))
        if entry.get("missing"):
            lines.append("      (no data returned for {0} in the window - "
                         "recorded as evidence gap)".format(metric))
    return lines


def disk_table(disks: List[Dict[str, Any]]) -> List[str]:
    if not disks:
        return ["  (no disk records returned for this instance)"]
    lines = ["  DiskId | Type | Category | Status | Size(GiB) | Device"]
    for disk in disks:
        lines.append("  {0} | {1} | {2} | {3} | {4} | {5}".format(
            _text(disk, "DiskId"), _text(disk, "Type"), _text(disk, "Category"),
            _text(disk, "Status"), _text(disk, "Size"), _text(disk, "Device")))
    return lines


def guest_block(guest: Optional[Dict[str, Any]]) -> List[str]:
    if not guest:
        return []
    lines = ["--- Gated in-guest evidence ---"]
    lines.append("  command  : {0}".format(mask_credentials(guest.get("command", ""))))
    lines.append("  status   : {0}".format(guest.get("status", "unknown")))
    if guest.get("reject_reason"):
        lines.append("  rejected : {0}".format(guest["reject_reason"]))
    if guest.get("error"):
        lines.append("  error    : {0}".format(guest["error"]))
    if guest.get("error_info"):
        lines.append("  guest err: {0}".format(guest["error_info"]))
    output = guest.get("output") or ""
    if output:
        body = output.splitlines()
        shown = body[:MAX_OUTPUT_SNIPPET_LINES]
        lines.append("  output (credential-masked{0}):".format(
            ", snippet of {0} lines".format(len(body)) if len(body) > MAX_OUTPUT_SNIPPET_LINES else ""))
        for line in shown:
            lines.append("    {0}".format(line[:160]))
        if len(body) > MAX_OUTPUT_SNIPPET_LINES:
            lines.append("    {0}".format(OUTPUT_SNIPPET_MARKER))
        for item in guest.get("findings", []):
            lines.append("  [{0}] {1}".format(item["id"], item["text"]))
    return lines


def determine_status(
    errors: List[Dict[str, str]], warnings: List[str],
    instance: Dict[str, Any], areas: Dict[str, Any],
    guest: Optional[Dict[str, Any]], identity_error: Optional[str],
) -> str:
    if not instance.get("found"):
        return STATUS_FAIL
    if errors and not areas.get("any_data"):
        return STATUS_FAIL
    if errors or warnings or identity_error or not areas.get("any_data"):
        return STATUS_DEGRADED
    if guest and guest.get("status") in ("rejected", "dispatch-failed", "readback-failed"):
        return STATUS_DEGRADED
    return STATUS_OK


def next_action_for(
    status: str, errors: List[Dict[str, str]],
    findings: List[Dict[str, str]], guest: Optional[Dict[str, Any]],
) -> str:
    joined = " ".join(item["detail"] for item in errors)
    if status == STATUS_FAIL:
        if CODE_NO_PERMISSION in joined or CODE_IMPLICIT_DENY in joined:
            return ("An administrator must grant every action listed in "
                    "references/ram-policies.md ({0}); then re-run this exact "
                    "command.".format(", ".join(RAM_ACTION_NAMES)))
        return ("Fix the input scope first: confirm the region + instance id pair "
                "with the customer (DescribeInstances returned nothing usable), "
                "then re-run. Do not proceed on assumed facts.")
    rules = " ".join(item["rule"] for item in findings)
    if guest and guest.get("status") == "rejected":
        return ("Ask the customer to approve the exact inspection command after "
                "seeing it (command, target instance, inspect-only nature, "
                "reversibility), then re-run once with their reply quoted in "
                "--confirmation. Never rephrase the command to dodge the gate.")
    if "R8" in rules:
        return ("Resolve the instance identity question first (region, account, "
                "cloud provider) and re-run; the customer's memory of an ip or id "
                "is not evidence (ticket T-3EA06F17).")
    if "R1" in rules or "R1b" in rules or "R2" in rules:
        return ("Deliver the report, then the manual guidance block; optionally "
                "offer the gated in-guest inspection (one whitelisted command, "
                "quoted customer approval) to pin the process-level evidence.")
    if "R5" in rules:
        return ("Send the negative finding plus the handoff matrix: continue at "
                "the application/public-network/security area, and have the "
                "customer pre-install CloudMonitor agent + atop for reproducibility.")
    return ("Collect the missing evidence area: install/repair the CloudMonitor "
            "agent (manual) or run the gated in-guest inspection, then re-run the "
            "analysis; report only what returned data supports.")


def render_text(report: Dict[str, Any]) -> str:
    out: List[str] = []
    out.append("=" * 78)
    out.append("ECS resource-bottleneck diagnosis (CPU / memory / load / freeze)")
    out.append("=" * 78)
    out.append("Skill        : {0}".format(report["skill_name"]))
    out.append("Session      : {0}".format(report["session_id"]))
    out.append("User-Agent   : {0}".format(report["user_agent"]))
    out.append("Scope        : region={0} instance={1} symptom={2}".format(
        report["region_id"] or "not supplied",
        report["instance_id"] or "not supplied",
        report["symptom"]))
    out.append("Account      : {0} (identity api version {1})".format(
        report["uid_label"], report["identity_api_version"]))
    out.append("API surface  : {0}".format(", ".join(API_WHITELIST_ACTIONS)))
    out.append("RAM actions  : {0}".format(", ".join(RAM_ACTION_NAMES)))
    out.append("Declared ver : ecs={0} cms={1} sts={2}".format(
        ECS_API_VERSION, CMS_API_VERSION, STS_API_VERSION))

    out.append("")
    out.append("--- Collected parameters (all declared; auto-fills marked) ---")
    for key, value in report["declared_params"].items():
        out.append("  {0} = {1}".format(key, value))

    out.append("")
    out.append("--- Instance profile (state {0}) ---".format(
        report["instance_state"]))
    out.extend(report["instance_rows"])

    out.append("")
    out.append("--- Attached disks ({0} record(s), paging {1}) ---".format(
        report["disk_count"], report["disk_paging"]))
    out.extend(report["disk_rows"])

    out.append("")
    out.append("--- CloudMonitor evidence (window {0} .. {1}, period {2}s; "
               "mean AND max always shown; heuristics: cpu mx>={3}% / mem avg>={4}% "
               "pending official threshold ratification) ---".format(
                   report["window"].get("StartTime") or "not read",
                   report["window"].get("EndTime") or "not read",
                   DEFAULT_PERIOD_SECONDS, int(SATURATION_CPU_PCT),
                   int(SATURATION_MEM_PCT)))
    out.extend(report["metric_rows"])

    out.append("")
    out.append("--- Rule findings (each cites its readings) ---")
    if not report["findings"]:
        out.append("  (no finding derived; evidence insufficient rather than assumed)")
    for item in report["findings"]:
        out.append("  [{0}][{1}][{2}] {3}".format(
            item["id"], item["level"], item["rule"], item["text"]))

    out.extend(guest_block(report.get("guest")))

    if report["guidance"]:
        out.append("")
        out.append("--- Manual guidance (operator-executed; never run by this skill) ---")
        for line in report["guidance"]:
            out.append("  {0}".format(line))

    out.append("")
    out.append("--- Scope boundary and handoff ---")
    for line in report["boundary"]:
        out.append("  {0}".format(line))

    if report["warnings"]:
        out.append("")
        out.append("--- Warnings ({0} shown) ---".format(
            min(len(report["warnings"]), MAX_REPORT_WARNINGS)))
        for line in report["warnings"][:MAX_REPORT_WARNINGS]:
            out.append("  [WARN] {0}".format(line))

    if report["errors"]:
        out.append("")
        out.append("--- Failed calls (recorded, not hidden) ---")
        for item in report["errors"][:MAX_REPORT_WARNINGS]:
            out.append("  {0} -> {1}".format(item["action"], item["detail"]))

    out.append("")
    out.append("STATUS: {0}".format(report["STATUS"]))
    out.append("NEXT_ACTION: {0}".format(report["NEXT_ACTION"]))
    out.append("")
    out.append("References: references/resource-bottleneck__diagnosis-rules.md (R1-R9), "
               "references/resource-bottleneck__metric-catalog.md (calibers & gaps), "
               "references/resource-bottleneck__guest-commands.md (whitelist & gate), "
               "references/resource-bottleneck__log-signatures.md (R9 quoted strings), "
               "references/resource-bottleneck__human-actions.md, references/resource-bottleneck__escalation-map.md, "
               "references/resource-bottleneck__evidence-and-privacy.md, references/ram-policies.md")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Report assembly
# --------------------------------------------------------------------------- #
def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    session_id = new_session_id()
    warnings: List[str] = []
    errors: List[Dict[str, str]] = []
    identity, identity_error = guest_identity_lookup(session_id, warnings)

    report: Dict[str, Any] = {
        "skill_name": SKILL_NAME,
        "session_id": session_id,
        "user_agent": build_user_agent(session_id),
        "region_id": args.region_id,
        "instance_id": args.instance_id,
        "symptom": args.symptom,
        "uid_label": uid_label_of(identity),
        "identity_api_version": identity.get("api_version") or "not returned",
        "declared_params": {},
        "instance_state": "not started",
        "instance_rows": [],
        "disk_rows": [],
        "disk_count": 0,
        "disk_paging": "not started",
        "window": {},
        "metric_rows": [],
        "findings": [],
        "guest": None,
        "guidance": [],
        "boundary": boundary_lines(),
        "warnings": warnings,
        "errors": errors,
    }

    if args.check_auth_only:
        report["STATUS"] = STATUS_OK if identity_error is None else STATUS_FAIL
        report["NEXT_ACTION"] = (
            "Credential chain works; run the diagnosis with --region-id and --instance-id."
            if identity_error is None
            else "Run `aliyun sts get-caller-identity` to restore the default credential chain; "
                 "never share key material with the assistant.")
        return report

    problems = validate(args)
    if problems:
        report["declared_params"] = {"validated": "rejected"}
        report["findings"] = [{
            "id": "V1", "level": "high", "rule": "R8",
            "text": "Input rejected: {0}".format(" ".join(problems))}]
        report["STATUS"] = STATUS_FAIL
        report["NEXT_ACTION"] = "Ask the customer for the missing input: {0}".format(
            " ".join(problems))
        return report

    window = resolve_window(args)
    report["window"] = window
    report["declared_params"] = {
        "region-id": args.region_id,
        "instance-id": args.instance_id,
        "symptom": args.symptom,
        "window": "{0} .. {1} ({2})".format(
            window["StartTime"], window["EndTime"], window["source"]),
        "period-seconds": DEFAULT_PERIOD_SECONDS,
        "per-call-timeout-seconds": args.timeout,
        "page-size": PAGE_SIZE,
        "max-pages": args.max_pages,
        "guest-command": mask_credentials(args.guest_command)
                         if args.guest_command else "not requested",
        "customer-approval-quoted": "yes" if args.confirmation else "no",
    }

    instance = collect_instance(args, session_id, warnings, errors)
    report["instance_state"] = instance.get("state", "failed")
    attribute = {}
    if instance.get("found"):
        attribute = collect_attribute(args, session_id, warnings, errors)
    report["instance_rows"] = instance_rows(instance, attribute)

    disks, paging = ([], "skipped")
    if instance.get("found"):
        disks, paging = collect_disks(args, session_id, warnings, errors)
    report["disk_rows"] = disk_table(disks)
    report["disk_count"] = len(disks)
    report["disk_paging"] = paging

    evidence: Dict[str, Dict[str, Any]] = {}
    if instance.get("found"):
        evidence = collect_metrics(args.instance_id, window, session_id,
                                  args.timeout, warnings, errors)
    report["metric_rows"] = metric_table(evidence)

    guest: Optional[Dict[str, Any]] = None
    if args.guest_command:
        os_type = args.os_type or guess_os_type(instance)
        guest = guest_evidence.collect_guest_evidence(
            args.region_id, args.instance_id, args.guest_command, os_type,
            args.confirmation, session_id, args.timeout, warnings)
        guest["findings"] = guest_evidence.parse_guest_findings(
            guest.get("output") or "",
            cpu_count=_as_int((instance.get("data") or {}).get("Cpu")))
        report["guest"] = guest

    findings = evaluate(args, instance, attribute, disks, evidence, guest)
    report["findings"] = findings
    report["guidance"] = guidance_lines(findings, instance_areas(evidence))
    report["STATUS"] = determine_status(errors, warnings, instance, areas_of(evidence),
                                        guest, identity_error)
    report["NEXT_ACTION"] = next_action_for(report["STATUS"], errors, findings, guest)
    if identity_error:
        warnings.append("caller identity lookup returned {0}; account label "
                        "reported as unavailable instead of assumed".format(identity_error))
    if args.report_file:
        report["report_file_state"] = write_report_file(args.report_file, report)
    return report


def areas_of(evidence: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    return instance_areas(evidence)


def uid_label_of(identity: Dict[str, Any]) -> str:
    try:
        from sts_token import uid_traceability_label
        return uid_traceability_label(identity)
    except Exception:  # pragma: no cover - defensive
        return "account:unavailable"


def guest_identity_lookup(session_id: str, warnings: List[str]) -> Tuple[Dict[str, Any], Optional[str]]:
    from sts_token import fetch_caller_identity
    return fetch_caller_identity(session_id, warnings=warnings)


def instance_rows(instance: Dict[str, Any], attribute: Dict[str, Any]) -> List[str]:
    if not instance.get("found"):
        return ["  (instance record not returned; nothing derived from it)"]
    data = instance.get("data") or {}
    lines = []
    for key in ("InstanceId", "InstanceName", "Status", "InstanceType",
                "InstanceTypeFamily", "Cpu", "Memory", "OSType", "OsName",
                "ZoneId", "InstanceNetworkType"):
        lines.append("  {0} = {1}".format(key, _text(data, key)))
    lines.append("  attribute-cpu/memory cross-check = {0} / {1} MiB "
                 "(DescribeInstanceAttribute)".format(
                     _text(attribute, "Cpu"), _text(attribute, "Memory")))
    return lines


def guess_os_type(instance: Dict[str, Any]) -> str:
    os_type = str((instance.get("data") or {}).get("OSType") or "").lower()
    return "windows" if "windows" in os_type else "linux"


def write_report_file(path: str, report: Dict[str, Any]) -> str:
    """Create-only dump of the JSON report (never overwrites; no deletions)."""
    try:
        with open(path, "x") as handle:
            json.dump({key: value for key, value in report.items()
                       if key != "guest"}, handle, ensure_ascii=False, indent=2,
                      default=str)
            handle.write("\n")
        return "written"
    except FileExistsError:
        return "rejected (file exists; this skill never overwrites)"
    except OSError as exc:
        return "failed ({0})".format(mask_credentials(exc))


# --------------------------------------------------------------------------- #
# Offline self-test (pure functions; no network, no cloud)
# --------------------------------------------------------------------------- #
def _self_test() -> int:
    cms_metrics._self_test()
    guest_evidence._self_test()

    # validate(): normal / boundary / rejected inputs
    parser = build_parser()
    ok = parser.parse_args(["--region-id", "cn-hangzhou", "--instance-id", "i-bp1abc123"])
    assert validate(ok) == []
    bad = parser.parse_args(["--region-id", "CN_HANGZHOU!!", "--instance-id", "not-an-id"])
    assert len(validate(bad)) >= 2
    empty = parser.parse_args([])
    assert len(validate(empty)) == 2
    hours = parser.parse_args(["--region-id", "cn-hangzhou", "--instance-id", "i-abc123",
                               "--hours", "900"])
    assert any("--hours" in problem for problem in validate(hours))

    # window resolution
    window = resolve_window(ok)
    assert window["source"].startswith("auto-default") and window["EndTime"].endswith("Z")

    # rule engine on synthetic evidence
    def metric_entry(avg: float, mx: float, missing: bool = False) -> Dict[str, Any]:
        points = [{"timestamp": 1000, "Average": avg, "Maximum": mx},
                  {"timestamp": 2000, "Average": avg, "Maximum": mx}]
        return {"last": avg, "stats": ({} if missing else {"avg": avg, "mx": mx,
                "peak_ts_ms": 2000, "count": 2}), "points": ([] if missing else points),
                "missing": missing}

    fake_args = parser.parse_args(["--region-id", "cn-hangzhou",
                                   "--instance-id", "i-bp1abc123", "--symptom", "memory"])
    fake_instance = {"found": True, "data": {"Memory": 2048, "Cpu": 2,
                                             "InstanceType": "ecs.t5-c1m2.xlarge",
                                             "Status": "Running"}}
    mem_chain = {"CPUUtilization": metric_entry(95, 100),
                 "memory_usedutilization": metric_entry(97, 99),
                 "DiskReadBPS": metric_entry(9_000_000, 11_000_000),
                 "DiskWriteBPS": metric_entry(8_000_000, 10_000_000),
                 "IntranetInRate": metric_entry(1000, 2000)}
    rules = {item["rule"] for item in evaluate(fake_args, fake_instance, {}, [],
                                               mem_chain, None)}
    assert "R1" in rules and "R6" not in rules

    negative = {"CPUUtilization": metric_entry(5, 9),
                "memory_usedutilization": metric_entry(40, 45),
                "DiskReadBPS": metric_entry(1024, 4096),
                "DiskWriteBPS": metric_entry(512, 2048),
                "IntranetInRate": metric_entry(100, 200)}
    rules = {item["rule"] for item in evaluate(fake_args, fake_instance, {}, [],
                                               negative, None)}
    assert "R5" in rules and "R1" not in rules and "R2" not in rules

    gap_case = {metric: metric_entry(0, 0, missing=True) for metric in METRICS_EVIDENCED}
    rules = {item["rule"] for item in evaluate(fake_args, fake_instance, {}, [],
                                               gap_case, None)}
    assert "R6" in rules and "R5" not in rules

    not_found = evaluate(fake_args, {"found": False}, {}, [], negative, None)
    assert not_found and not_found[0]["rule"] == "R8"

    # areas condenser boundary values
    assert instance_areas({})["cpu_high"] is False
    assert instance_areas({})["any_data"] is False
    assert instance_areas(mem_chain)["cpu_high"] is True
    assert instance_areas(mem_chain)["mem_high"] is True
    assert guest_signal_flags(None) == {"kswapd": False, "oom": False, "blocked": False}
    assert guest_signal_flags({"output": "Out of Memory: Killed process 9 (java)"})["oom"]
    assert guest_signal_flags({"output": "garbage"}) == {"kswapd": False, "oom": False,
                                                         "blocked": False}
    assert co_peak({"CPUUtilization": {"stats": {"mx": 100}, "points": [
        {"timestamp": 7, "Average": 99}]}, "DiskReadBPS": {"stats": {"mx": 9e6},
        "points": [{"timestamp": 7, "Average": 8.9e6}]}, "DiskWriteBPS": {}})["timestamp_ms"] == 7
    assert co_peak({}) is None
    assert determine_status([], [], {"found": False}, {}, None, None) == STATUS_FAIL
    assert determine_status([], [], {"found": True}, {"any_data": False}, None, None) \
        == STATUS_DEGRADED
    assert determine_status([], [], {"found": True}, {"any_data": True}, None, None) \
        == STATUS_OK
    assert guess_os_type({"data": {"OSType": "windows"}}) == "windows"
    assert guess_os_type({}) == "linux"
    assert _text({"Cpu": 2}, "Cpu") == "2" and _text({}, "Cpu") == "not returned"
    print("resource_bottleneck_diagnose self-test passed")
    return 0


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    try:
        report = build_report(args)
    except CliError as exc:
        sys.stderr.write("[WARN] {0}\n".format(mask_credentials(exc)))
        print("STATUS: {0}".format(STATUS_FAIL))
        print("NEXT_ACTION: Re-check the region and instance id, restore CLI "
              "access, then re-run the same command; do not improvise cloud calls.")
        return EXIT_BY_STATUS[STATUS_FAIL]
    except Exception as exc:  # pragma: no cover - last-resort guard, never fabricate
        sys.stderr.write("[WARN] unexpected failure: {0}\n".format(mask_credentials(exc)))
        print("STATUS: {0}".format(STATUS_FAIL))
        print("NEXT_ACTION: Report this run to the skill owner using the session "
              "id; do not attempt manual cloud changes.")
        return EXIT_BY_STATUS[STATUS_FAIL]

    if args.output == "json":
        printable = dict(report)
        printable["guidance_source"] = "references/resource-bottleneck__human-actions.md"
        print(json.dumps(printable, ensure_ascii=False, indent=2, sort_keys=True,
                         default=str))
    else:
        print(render_text(report))
    if args.report_file:
        sys.stderr.write("[info] report-file state: {0}\n".format(
            report.get("report_file_state", "not written")))
    return EXIT_BY_STATUS.get(report["STATUS"], EXIT_BY_STATUS[STATUS_DEGRADED])


if __name__ == "__main__":
    sys.exit(main())
