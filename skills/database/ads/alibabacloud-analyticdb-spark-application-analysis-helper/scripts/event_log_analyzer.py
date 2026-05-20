#!/usr/bin/env python3
"""
Spark Event Log Analyzer

Parse Spark Event Log (JSON Lines format) from stdin, extract Stage/Task level
metrics, and perform data skew quantification, abnormal task detection, shuffle
spill detection, and small file risk detection.

Only Python standard library is required (json, sys, argparse, statistics, math,
collections).

Usage examples:
  # Basic analysis with text output
  aliyun ossutil cat <event-log-path> -e <endpoint> | \
      python3 scripts/event_log_analyzer.py
  
  # JSON output with custom thresholds
  aliyun ossutil cat <event-log-path> -e <endpoint> | \
      python3 scripts/event_log_analyzer.py \
          --output-format json \
          --skew-threshold 8 \
          --duration-threshold 5 \
          --small-file-size-mb 5
  
  # Show top 20 abnormal tasks
  aliyun ossutil cat <event-log-path> -e <endpoint> | \
      python3 scripts/event_log_analyzer.py --top-n 20
"""

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def safe_get(d, *keys, default=0):
    """Safely retrieve a nested key from a dict.

    Args:
        d: Dictionary to traverse.
        *keys: Sequence of keys to follow.
        default: Value returned if any key is missing.

    Returns:
        The nested value or *default*.
    """
    current = d
    for k in keys:
        if not isinstance(current, dict) or k not in current:
            return default
        current = current[k]
    return current


def percentile(sorted_data, p):
    """Compute the *p*-th percentile of a sorted list.

    Uses linear interpolation (same method as numpy's default).

    Args:
        sorted_data: List of numeric values **already sorted** in ascending order.
        p: Percentile in [0, 100].

    Returns:
        The interpolated percentile value.
    """
    if not sorted_data:
        return 0
    n = len(sorted_data)
    if n == 1:
        return sorted_data[0]
    rank = (p / 100.0) * (n - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return sorted_data[lower]
    frac = rank - lower
    return sorted_data[lower] * (1 - frac) + sorted_data[upper] * frac


def compute_stats(values):
    """Compute descriptive statistics for a list of numeric values.

    Args:
        values: List of int/float values.

    Returns:
        dict with keys: min, median, max, p95, stddev.
        stddev is 0.0 for lists with fewer than 2 elements.
    """
    if not values:
        return {"min": 0, "median": 0, "max": 0, "p95": 0, "stddev": 0.0}
    sorted_vals = sorted(values)
    med = statistics.median(sorted_vals)
    p95_val = percentile(sorted_vals, 95)
    if len(sorted_vals) >= 2:
        sd = statistics.stdev(sorted_vals)
    else:
        sd = 0.0
    return {
        "min": sorted_vals[0],
        "median": med,
        "max": sorted_vals[-1],
        "p95": p95_val,
        "stddev": sd,
    }


def compute_simple_stats(values):
    """Compute min/median/max for a list of numeric values.

    Args:
        values: List of int/float values.

    Returns:
        dict with keys: min, median, max.
    """
    if not values:
        return {"min": 0, "median": 0, "max": 0}
    sorted_vals = sorted(values)
    return {
        "min": sorted_vals[0],
        "median": statistics.median(sorted_vals),
        "max": sorted_vals[-1],
    }


def compute_skew_ratio(max_val, median_val, mean_val):
    """Compute skew ratio = max / median.

    When median is 0, falls back to max / (mean + 1) to avoid division by zero.

    Args:
        max_val: Maximum value.
        median_val: Median value.
        mean_val: Mean value.

    Returns:
        Float skew ratio.
    """
    if median_val > 0:
        return max_val / median_val
    if (mean_val + 1) > 0:
        return max_val / (mean_val + 1)
    return 0.0


DURATION_SEVERE_MIN_MS = 5 * 60 * 1000  # 5 minutes


def classify_skew(duration_ratio, shuffle_read_ratio, shuffle_read_max, skew_threshold, duration_max=0):
    """Classify the overall skew level of a stage.

    Args:
        duration_ratio: Duration skew ratio (max / median).
        shuffle_read_ratio: Shuffle read skew ratio (max / median).
        shuffle_read_max: Maximum shuffle read bytes in the stage.
        skew_threshold: Threshold for moderate skew detection.
        duration_max: Maximum task duration in milliseconds in the stage.

    Returns:
        One of "severe", "moderate", or "none".
    """
    # Severe: duration ratio > 10 AND max duration > 5min, or shuffle read ratio > 10 with significant data volume
    duration_severe = duration_ratio > 10 and duration_max > DURATION_SEVERE_MIN_MS
    shuffle_severe = shuffle_read_ratio > 10 and shuffle_read_max > 100 * 1024 * 1024

    if duration_severe or shuffle_severe:
        return "severe"

    # Moderate: either ratio exceeds the configured threshold
    if duration_ratio > skew_threshold or shuffle_read_ratio > skew_threshold:
        return "moderate"

    return "none"


def format_bytes(num_bytes):
    """Format a byte count as a human-readable string.

    Args:
        num_bytes: Number of bytes.

    Returns:
        Human-readable string (e.g., '1.5 GiB', '200.0 MiB').
    """
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 ** 2:
        return f"{num_bytes / 1024:.1f} KiB"
    elif num_bytes < 1024 ** 3:
        return f"{num_bytes / 1024 ** 2:.1f} MiB"
    elif num_bytes < 1024 ** 4:
        return f"{num_bytes / 1024 ** 3:.1f} GiB"
    else:
        return f"{num_bytes / 1024 ** 4:.1f} TiB"


def format_duration(ms):
    """Format a duration in milliseconds to a human-readable string.

    Args:
        ms: Duration in milliseconds.

    Returns:
        Formatted string (e.g., '1m 30s', '45.2s').
    """
    if ms < 1000:
        return f"{ms}ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}m {secs:.0f}s"
    hours = int(minutes // 60)
    mins = minutes % 60
    return f"{hours}h {mins}m"


# ---------------------------------------------------------------------------
# Event parsing
# ---------------------------------------------------------------------------


def parse_events(lines):
    """Parse JSON Lines from an iterable and categorize Spark events.

    Handles SparkListenerStageSubmitted, SparkListenerStageCompleted,
    SparkListenerTaskEnd, SparkListenerApplicationStart, and
    SparkListenerApplicationEnd events.  Invalid JSON lines are skipped
    with a warning to stderr.

    Spark Event Logs may be incomplete due to rolling behaviour.  This
    parser therefore collects as many event types as possible so that
    downstream analysis can infer missing information.

    Args:
        lines: Iterable of string lines (JSON Lines).

    Returns:
        Tuple of (stage_completed_events, stage_submitted_events,
        task_events, app_events):
        - stage_completed_events: dict mapping stage_id -> stage info dict
        - stage_submitted_events: dict mapping stage_id -> stage info dict
        - task_events: dict mapping stage_id -> list of task metric dicts
        - app_events: dict with 'app_start' and 'app_end' keys
    """
    stage_completed_events = {}
    stage_submitted_events = {}
    task_events = defaultdict(list)
    app_events = {"app_start": None, "app_end": None}

    for line_no, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            print(f"[WARN] Skipping invalid JSON at line {line_no}", file=sys.stderr)
            continue

        event_type = event.get("Event", "")

        if event_type == "SparkListenerStageSubmitted":
            info = event.get("Stage Info", {})
            stage_id = info.get("Stage ID")
            if stage_id is None:
                continue
            # Keep the first submitted event per stage (avoid overwriting
            # with retried stage submissions).
            if stage_id not in stage_submitted_events:
                stage_submitted_events[stage_id] = {
                    "stage_id": stage_id,
                    "stage_name": info.get("Stage Name", "unknown"),
                    "num_tasks": info.get("Number of Tasks", 0),
                    "submission_time": info.get("Submission Time"),
                }

        elif event_type == "SparkListenerStageCompleted":
            info = event.get("Stage Info", {})
            stage_id = info.get("Stage ID")
            if stage_id is None:
                continue
            stage_completed_events[stage_id] = {
                "stage_id": stage_id,
                "stage_name": info.get("Stage Name", "unknown"),
                "num_tasks": info.get("Number of Tasks", 0),
                "submission_time": info.get("Submission Time"),
                "completion_time": info.get("Completion Time"),
            }

        elif event_type == "SparkListenerTaskEnd":
            stage_id = event.get("Stage ID")
            if stage_id is None:
                continue
            task_info = event.get("Task Info", {})
            metrics = event.get("Task Metrics", {})

            # Task duration uses Executor Run Time (ms)
            duration = safe_get(metrics, "Executor Run Time", default=0)

            # Shuffle Read = Remote Bytes Read + Local Bytes Read
            shuffle_read = (
                safe_get(metrics, "Shuffle Read Metrics", "Remote Bytes Read", default=0)
                + safe_get(metrics, "Shuffle Read Metrics", "Local Bytes Read", default=0)
            )
            shuffle_write = safe_get(
                metrics, "Shuffle Write Metrics", "Shuffle Bytes Written", default=0
            )
            input_bytes = safe_get(metrics, "Input Metrics", "Bytes Read", default=0)
            output_bytes = safe_get(metrics, "Output Metrics", "Bytes Written", default=0)
            memory_spill = safe_get(metrics, "Memory Bytes Spilled", default=0)
            disk_spill = safe_get(metrics, "Disk Bytes Spilled", default=0)
            gc_time = safe_get(metrics, "JVM GC Time", default=0)

            task_record = {
                "stage_id": stage_id,
                "task_id": task_info.get("Task ID"),
                "task_attempt": task_info.get("Attempt", 0),
                "executor_id": str(task_info.get("Executor ID", "")),
                "launch_time": task_info.get("Launch Time"),
                "finish_time": task_info.get("Finish Time"),
                "duration_ms": duration,
                "shuffle_read_bytes": shuffle_read,
                "shuffle_write_bytes": shuffle_write,
                "input_bytes": input_bytes,
                "output_bytes": output_bytes,
                "memory_bytes_spilled": memory_spill,
                "disk_bytes_spilled": disk_spill,
                "gc_time_ms": gc_time,
            }
            task_events[stage_id].append(task_record)

        elif event_type == "SparkListenerApplicationStart":
            app_events["app_start"] = {
                "app_name": event.get("App Name", ""),
                "app_id": event.get("App ID", ""),
                "timestamp": event.get("Timestamp"),
            }

        elif event_type == "SparkListenerApplicationEnd":
            app_events["app_end"] = {
                "timestamp": event.get("Timestamp"),
            }

    return stage_completed_events, stage_submitted_events, task_events, app_events


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


def analyze(stage_completed_events, stage_submitted_events, task_events, app_events, args):
    """Run all analyses on parsed events.

    Gracefully handles incomplete event logs (missing StageCompleted,
    missing submission/completion times, partial task data) by inferring
    information from available events.

    Performs: stage-level aggregation, task statistics, skew quantification,
    abnormal task detection, shuffle spill detection, and small file risk
    detection.

    Args:
        stage_completed_events: Dict from parse_events (stage_id -> stage info).
        stage_submitted_events: Dict from parse_events (stage_id -> stage info).
        task_events: Dict from parse_events (stage_id -> list of task dicts).
        app_events: Dict from parse_events with app_start and app_end.
        args: Parsed CLI arguments with skew_threshold, duration_threshold,
              small_file_size_mb, and top_n.

    Returns:
        Complete analysis result dict with keys: summary, stages,
        skewed_stages, abnormal_tasks, spill_stages, small_file_risk.
    """
    skew_threshold = args.skew_threshold
    duration_threshold = args.duration_threshold
    small_file_size_mb = args.small_file_size_mb
    top_n = args.top_n

    all_stage_ids = sorted(
        set(
            list(stage_completed_events.keys())
            + list(stage_submitted_events.keys())
            + list(task_events.keys())
        )
    )
    stages_result = []
    skewed_stages = []
    abnormal_tasks = []
    spill_stages = []
    small_file_risk = []

    total_tasks = 0
    completeness_notes = []
    stages_missing_completed = 0
    stages_missing_times = 0

    for sid in all_stage_ids:
        sc_info = stage_completed_events.get(sid, {})
        ss_info = stage_submitted_events.get(sid, {})
        tasks = task_events.get(sid, [])
        total_tasks += len(tasks)

        # --- Determine stage-level info (with fallbacks) ---
        # Prefer StageCompleted > StageSubmitted > inferred from TaskEnd
        has_stage_completed = bool(sc_info)
        has_stage_submitted = bool(ss_info)

        if has_stage_completed:
            stage_name = sc_info.get("stage_name", "unknown")
            num_tasks_declared = sc_info.get("num_tasks", len(tasks))
            submission_time = sc_info.get("submission_time")
            completion_time = sc_info.get("completion_time")
        elif has_stage_submitted:
            stage_name = ss_info.get("stage_name", "unknown")
            num_tasks_declared = ss_info.get("num_tasks", len(tasks))
            submission_time = ss_info.get("submission_time")
            completion_time = None
        else:
            # No StageCompleted or StageSubmitted — infer from TaskEnd events
            stage_name = "unknown (inferred from tasks)"
            num_tasks_declared = len(tasks)
            submission_time = None
            completion_time = None
            if tasks:
                completeness_notes.append(
                    f"Stage {sid}: no StageCompleted/StageSubmitted event found; "
                    f"stage info inferred from {len(tasks)} TaskEnd events"
                )

        if not has_stage_completed and tasks:
            stages_missing_completed += 1

        # Use actual task count as floor for declared tasks
        num_tasks = max(num_tasks_declared, len(tasks))

        # --- Derive stage duration ---
        # Priority: StageCompleted times > task launch/finish times > 0
        if submission_time is not None and completion_time is not None:
            duration_ms = completion_time - submission_time
        elif tasks:
            # Derive from task launch/finish times
            launch_times = [t["launch_time"] for t in tasks if t.get("launch_time") is not None]
            finish_times = [t["finish_time"] for t in tasks if t.get("finish_time") is not None]
            if launch_times and finish_times:
                inferred_start = min(launch_times)
                inferred_end = max(finish_times)
                duration_ms = inferred_end - inferred_start
                submission_time = inferred_start
                completion_time = inferred_end
                stages_missing_times += 1
                completeness_notes.append(
                    f"Stage {sid}: submission/completion time inferred from "
                    f"task launch/finish times"
                )
            else:
                duration_ms = 0
                stages_missing_times += 1
                completeness_notes.append(
                    f"Stage {sid}: unable to determine stage duration "
                    f"(no stage times and incomplete task timestamps)"
                )
        else:
            duration_ms = 0

        # --- Task sampling rate ---
        actual_tasks = len(tasks)
        if num_tasks_declared > 0:
            task_sampling_rate = round(actual_tasks / num_tasks_declared, 2)
        else:
            task_sampling_rate = 1.0 if actual_tasks > 0 else 0.0

        # --- Task-level value lists ---
        durations = [t["duration_ms"] for t in tasks]
        shuffle_reads = [t["shuffle_read_bytes"] for t in tasks]
        shuffle_writes = [t["shuffle_write_bytes"] for t in tasks]
        input_vals = [t["input_bytes"] for t in tasks]
        output_vals = [t["output_bytes"] for t in tasks]
        gc_times = [t["gc_time_ms"] for t in tasks]
        disk_spills = [t["disk_bytes_spilled"] for t in tasks]
        memory_spills = [t["memory_bytes_spilled"] for t in tasks]

        # --- Task-level statistics ---
        task_duration_stats = compute_stats(durations)
        shuffle_read_stats = compute_simple_stats(shuffle_reads)
        shuffle_write_stats = compute_simple_stats(shuffle_writes)
        input_bytes_stats = compute_simple_stats(input_vals)
        output_bytes_stats = compute_simple_stats(output_vals)
        gc_time_stats = compute_simple_stats(gc_times)

        total_disk_spill = sum(disk_spills)
        total_memory_spill = sum(memory_spills)

        # --- Data skew quantification ---
        duration_med = task_duration_stats["median"]
        duration_max = task_duration_stats["max"]
        duration_mean = statistics.mean(durations) if durations else 0

        shuffle_read_med = shuffle_read_stats["median"]
        shuffle_read_max = shuffle_read_stats["max"]
        shuffle_read_mean = statistics.mean(shuffle_reads) if shuffle_reads else 0

        duration_skew_ratio = compute_skew_ratio(duration_max, duration_med, duration_mean)
        shuffle_read_skew_ratio = compute_skew_ratio(
            shuffle_read_max, shuffle_read_med, shuffle_read_mean
        )

        # Classify overall skew level for this stage
        skew_level = classify_skew(
            duration_skew_ratio, shuffle_read_skew_ratio, shuffle_read_max, skew_threshold,
            duration_max=duration_max
        )

        stage_record = {
            "stage_id": sid,
            "stage_name": stage_name,
            "num_tasks": num_tasks,
            "num_tasks_declared": num_tasks_declared,
            "actual_tasks": actual_tasks,
            "task_sampling_rate": task_sampling_rate,
            "duration_ms": duration_ms,
            "duration_source": "stage_event" if (submission_time is not None and completion_time is not None and has_stage_completed) else "inferred_from_tasks" if tasks else "unknown",
            "has_stage_completed_event": has_stage_completed,
            "task_duration_stats": task_duration_stats,
            "shuffle_read_stats": shuffle_read_stats,
            "shuffle_write_stats": shuffle_write_stats,
            "input_bytes_stats": input_bytes_stats,
            "output_bytes_stats": output_bytes_stats,
            "gc_time_stats": gc_time_stats,
            "total_disk_spill": total_disk_spill,
            "total_memory_spill": total_memory_spill,
            "skew_level": skew_level,
            "duration_skew_ratio": round(duration_skew_ratio, 2),
            "shuffle_read_skew_ratio": round(shuffle_read_skew_ratio, 2),
        }
        stages_result.append(stage_record)

        # --- Skewed stage detail ---
        if skew_level != "none":
            if skew_level == "severe":
                recommendation = (
                    "Severe data skew detected. Consider: salting keys, "
                    "broadcast join (if one side is small), or enabling AQE "
                    "(spark.sql.adaptive.enabled=true)."
                )
            else:
                recommendation = (
                    "Moderate data skew detected. Consider: increasing "
                    "shuffle partitions, enabling AQE, or inspecting key "
                    "distribution."
                )
            skewed_stages.append({
                "stage_id": sid,
                "skew_level": skew_level,
                "duration_skew_ratio": round(duration_skew_ratio, 2),
                "shuffle_read_skew_ratio": round(shuffle_read_skew_ratio, 2),
                "recommendation": recommendation,
            })

        # --- Abnormal task detection ---
        for t in tasks:
            reasons = []
            if duration_med > 0 and t["duration_ms"] > duration_med * duration_threshold:
                reasons.append("duration_skew")
            if shuffle_read_med > 0 and t["shuffle_read_bytes"] > shuffle_read_med * skew_threshold:
                reasons.append("shuffle_read_skew")

            if reasons:
                abnormal_tasks.append({
                    "stage_id": sid,
                    "task_id": t["task_id"],
                    "task_attempt": t["task_attempt"],
                    "duration_ms": t["duration_ms"],
                    "duration_ratio": round(
                        t["duration_ms"] / duration_med, 2
                    ) if duration_med > 0 else 0.0,
                    "shuffle_read_bytes": t["shuffle_read_bytes"],
                    "shuffle_read_ratio": round(
                        t["shuffle_read_bytes"] / shuffle_read_med, 2
                    ) if shuffle_read_med > 0 else 0.0,
                    "gc_time_ms": t["gc_time_ms"],
                    "executor_id": t["executor_id"],
                    "reason": ", ".join(reasons),
                })

        # --- Shuffle spill detection ---
        if total_disk_spill > 0:
            if total_disk_spill > 1024 ** 3:
                severity = "critical"
                rec = (
                    "Heavy shuffle spill detected. Increase spark.executor.memory "
                    "or spark.sql.shuffle.partitions."
                )
            elif total_disk_spill > 100 * 1024 * 1024:
                severity = "warning"
                rec = (
                    "Moderate shuffle spill detected. Consider increasing "
                    "spark.executor.memory or spark.sql.shuffle.partitions."
                )
            else:
                severity = "info"
                rec = "Minor shuffle spill detected. Monitor for increase."
            spill_stages.append({
                "stage_id": sid,
                "disk_spill_bytes": total_disk_spill,
                "memory_spill_bytes": total_memory_spill,
                "severity": severity,
                "recommendation": rec,
            })

        # --- Small file detection ---
        output_tasks = [t for t in tasks if t["output_bytes"] > 0]
        if output_tasks:
            num_output_tasks = len(output_tasks)
            avg_output_bytes = sum(t["output_bytes"] for t in output_tasks) / num_output_tasks
            if (
                num_output_tasks > 100
                and avg_output_bytes < small_file_size_mb * 1024 * 1024
            ):
                small_file_risk.append({
                    "stage_id": sid,
                    "num_output_tasks": num_output_tasks,
                    "avg_output_bytes": int(avg_output_bytes),
                    "recommendation": (
                        f"Small file risk: {num_output_tasks} tasks writing avg "
                        f"{avg_output_bytes / 1024 / 1024:.1f} MB each. "
                        f"Use .coalesce(N) or .repartition(N) before write."
                    ),
                })

    # Sort abnormal tasks by duration descending, then take top N
    abnormal_tasks.sort(key=lambda x: x["duration_ms"], reverse=True)
    abnormal_tasks = abnormal_tasks[:top_n]

    # --- Build completeness info ---
    is_partial = (
        stages_missing_completed > 0
        or stages_missing_times > 0
        or app_events["app_start"] is None
        or app_events["app_end"] is None
    )

    data_completeness = {
        "is_partial": is_partial,
        "stages_missing_completed_event": stages_missing_completed,
        "stages_missing_time_info": stages_missing_times,
        "app_start_found": app_events["app_start"] is not None,
        "app_end_found": app_events["app_end"] is not None,
    }
    if is_partial:
        data_completeness["notes"] = completeness_notes

    # Summary
    total_duration_ms = sum(s.get("duration_ms", 0) for s in stages_result)

    summary = {
        "total_stages": len(stages_result),
        "total_tasks": total_tasks,
        "total_duration_ms": total_duration_ms,
        "skewed_stage_count": len(skewed_stages),
        "spill_stage_count": len(spill_stages),
        "small_file_risk_count": len(small_file_risk),
        "abnormal_task_count": len(abnormal_tasks),
        "data_completeness": data_completeness,
    }
    if is_partial:
        summary["partial_event_log_detected"] = True

    # Add app-level info when available
    if app_events["app_start"] is not None:
        summary["app_name"] = app_events["app_start"].get("app_name", "")
        summary["app_id"] = app_events["app_start"].get("app_id", "")
    if app_events["app_start"] is not None and app_events["app_end"] is not None:
        start_ts = app_events["app_start"].get("timestamp")
        end_ts = app_events["app_end"].get("timestamp")
        if start_ts is not None and end_ts is not None:
            summary["app_duration_ms"] = end_ts - start_ts

    return {
        "summary": summary,
        "stages": stages_result,
        "skewed_stages": skewed_stages,
        "abnormal_tasks": abnormal_tasks,
        "spill_stages": spill_stages,
        "small_file_risk": small_file_risk,
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def output_text(result):
    """Print the analysis result in human-readable text format.

    Args:
        result: Analysis result dict from analyze().
    """
    summary = result["summary"]
    print("=" * 72)
    print("  Spark Event Log Analysis Report")
    print("=" * 72)
    print()

    # Application-level info (if available)
    if summary.get("app_name"):
        print(f"  Application:       {summary['app_name']}")
    if summary.get("app_id"):
        print(f"  App ID:            {summary['app_id']}")
    if summary.get("app_duration_ms"):
        print(f"  App Duration:      {format_duration(summary['app_duration_ms'])}")

    print(f"  Total Stages:        {summary['total_stages']}")
    print(f"  Total Tasks:         {summary['total_tasks']}")
    print(f"  Total Duration:      {format_duration(summary['total_duration_ms'])}")
    print(f"  Skewed Stages:       {summary['skewed_stage_count']}")
    print(f"  Spill Stages:        {summary['spill_stage_count']}")
    print(f"  Small File Risk:     {summary['small_file_risk_count']}")
    print(f"  Abnormal Tasks:      {summary['abnormal_task_count']}")

    # Data completeness warning
    completeness = summary.get("data_completeness", {})
    if completeness.get("is_partial"):
        print()
        print("  *** PARTIAL EVENT LOG DETECTED ***")
        if not completeness.get("app_start_found"):
            print("  - ApplicationStart event not found")
        if not completeness.get("app_end_found"):
            print("  - ApplicationEnd event not found")
        if completeness.get("stages_missing_completed_event", 0) > 0:
            print(f"  - {completeness['stages_missing_completed_event']} stage(s) missing StageCompleted event")
        if completeness.get("stages_missing_time_info", 0) > 0:
            print(f"  - {completeness['stages_missing_time_info']} stage(s) with inferred duration")
        for note in completeness.get("notes", []):
            print(f"  - {note}")
        print("  (Analysis proceeds on available data; results may be incomplete)")

    print()

    # Stage summary table
    stages = result["stages"]
    if stages:
        print("-" * 72)
        print("  Stage Metrics Summary")
        print("-" * 72)
        header = (
            f"{'Stage':>6}  {'Name':<30} {'Tasks':>6} "
            f"{'Duration':>12} {'Skew':>8} {'Level':>8}"
        )
        print(f"  {header}")
        print(f"  {'-' * 68}")
        for s in stages:
            name = s["stage_name"]
            if len(name) > 28:
                name = name[:25] + "..."
            dur = format_duration(s["duration_ms"])
            skew = s["duration_skew_ratio"]
            level = s["skew_level"]
            print(
                f"  {s['stage_id']:>6}  {name:<30} {s['num_tasks']:>6} "
                f"{dur:>12} {skew:>7.1f}x {level:>8}"
            )
        print()

        # Per-stage detail
        for s in stages:
            print("-" * 72)
            print(f"  Stage {s['stage_id']}: {s['stage_name']}")
            print(
                f"    Tasks: {s['num_tasks']}  |  "
                f"Duration: {format_duration(s['duration_ms'])}"
                + (f" (inferred from task times)" if s.get("duration_source") == "inferred_from_tasks" else "")
            )
            # Sampling rate annotation
            sampling_rate = s.get("task_sampling_rate", 1.0)
            if sampling_rate < 1.0:
                print(
                    f"    Task Sampling:  {s.get('actual_tasks', '?')}/{s.get('num_tasks_declared', '?')} "
                    f"({sampling_rate:.0%})  [PARTIAL DATA]"
                )
            if not s.get("has_stage_completed_event", True):
                print("    [!] No StageCompleted event for this stage")
            ds = s["task_duration_stats"]
            print(
                f"    Task Duration:  min={format_duration(ds['min'])}  "
                f"median={format_duration(ds['median'])}  "
                f"max={format_duration(ds['max'])}  "
                f"p95={format_duration(ds['p95'])}  "
                f"stddev={ds['stddev']:.0f}ms"
            )
            sr = s["shuffle_read_stats"]
            print(
                f"    Shuffle Read:   min={format_bytes(sr['min'])}  "
                f"median={format_bytes(sr['median'])}  "
                f"max={format_bytes(sr['max'])}"
            )
            sw = s["shuffle_write_stats"]
            print(
                f"    Shuffle Write:  min={format_bytes(sw['min'])}  "
                f"median={format_bytes(sw['median'])}  "
                f"max={format_bytes(sw['max'])}"
            )
            ib = s["input_bytes_stats"]
            print(
                f"    Input Bytes:    min={format_bytes(ib['min'])}  "
                f"median={format_bytes(ib['median'])}  "
                f"max={format_bytes(ib['max'])}"
            )
            ob = s["output_bytes_stats"]
            print(
                f"    Output Bytes:   min={format_bytes(ob['min'])}  "
                f"median={format_bytes(ob['median'])}  "
                f"max={format_bytes(ob['max'])}"
            )
            gc = s["gc_time_stats"]
            print(
                f"    GC Time:        min={format_duration(gc['min'])}  "
                f"median={format_duration(gc['median'])}  "
                f"max={format_duration(gc['max'])}"
            )
            print(
                f"    Disk Spill:     {format_bytes(s['total_disk_spill'])}  |  "
                f"Memory Spill: {format_bytes(s['total_memory_spill'])}"
            )
            print(
                f"    Skew Level:     {s['skew_level']}  "
                f"(duration: {s['duration_skew_ratio']}x, "
                f"shuffle_read: {s['shuffle_read_skew_ratio']}x)"
            )
            print()

    # Skewed stages
    if result["skewed_stages"]:
        print("=" * 72)
        print("  Data Skew Detection")
        print("=" * 72)
        for sk in result["skewed_stages"]:
            print(f"  Stage {sk['stage_id']}  [{sk['skew_level'].upper()}]")
            print(f"    Duration skew ratio:     {sk['duration_skew_ratio']}x")
            print(f"    Shuffle read skew ratio: {sk['shuffle_read_skew_ratio']}x")
            print(f"    Recommendation: {sk['recommendation']}")
            print()

    # Abnormal tasks
    if result["abnormal_tasks"]:
        print("=" * 72)
        print(f"  Abnormal Tasks (Top {len(result['abnormal_tasks'])})")
        print("=" * 72)
        for at in result["abnormal_tasks"]:
            print(
                f"  Stage {at['stage_id']} | Task {at['task_id']} "
                f"(attempt {at['task_attempt']}) on executor {at['executor_id']}"
            )
            print(
                f"    Duration:     {format_duration(at['duration_ms'])}  "
                f"({at['duration_ratio']}x median)"
            )
            print(
                f"    Shuffle Read: {format_bytes(at['shuffle_read_bytes'])}  "
                f"({at['shuffle_read_ratio']}x median)"
            )
            print(f"    GC Time:      {format_duration(at['gc_time_ms'])}")
            print(f"    Reason:       {at['reason']}")
            print()

    # Spill stages
    if result["spill_stages"]:
        print("=" * 72)
        print("  Shuffle Spill Detection")
        print("=" * 72)
        for sp in result["spill_stages"]:
            print(f"  Stage {sp['stage_id']}  [{sp['severity'].upper()}]")
            print(f"    Disk Spill:   {format_bytes(sp['disk_spill_bytes'])}")
            print(f"    Memory Spill: {format_bytes(sp['memory_spill_bytes'])}")
            print(f"    Recommendation: {sp['recommendation']}")
            print()

    # Small file risk
    if result["small_file_risk"]:
        print("=" * 72)
        print("  Small File Risk Detection")
        print("=" * 72)
        for sf in result["small_file_risk"]:
            print(f"  Stage {sf['stage_id']}")
            print(f"    Output Tasks: {sf['num_output_tasks']}")
            print(f"    Avg Output:   {format_bytes(sf['avg_output_bytes'])}")
            print(f"    Recommendation: {sf['recommendation']}")
            print()

    # Healthy message when no anomalies found
    if (
        not result["skewed_stages"]
        and not result["abnormal_tasks"]
        and not result["spill_stages"]
        and not result["small_file_risk"]
    ):
        print("=" * 72)
        print("  No anomalies detected. Application looks healthy.")
        print("=" * 72)


def output_json(result):
    """Print the analysis result as JSON.

    Args:
        result: Analysis result dict from analyze().
    """
    print(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    """Entry point: parse arguments, read stdin, run analysis, output results."""
    parser = argparse.ArgumentParser(
        description=(
            "Analyze Spark Event Log from stdin (JSON Lines format). "
            "Detect data skew, abnormal tasks, shuffle spill, and small file risk."
        ),
        epilog=(
            "Typical usage: aliyun ossutil cat <path> -e <endpoint> | "
            "python3 %(prog)s [options]"
        ),
    )
    parser.add_argument(
        "--skew-threshold",
        type=float,
        default=5,
        help="Skew ratio threshold for moderate skew detection (default: 5)",
    )
    parser.add_argument(
        "--duration-threshold",
        type=float,
        default=5,
        help="Duration multiplier threshold for abnormal task detection (default: 5)",
    )
    parser.add_argument(
        "--small-file-size-mb",
        type=float,
        default=10,
        help="Average output size threshold in MB for small file risk (default: 10)",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of top abnormal tasks to display (default: 10)",
    )

    args = parser.parse_args()

    # Read from stdin
    if sys.stdin.isatty():
        print(
            "[ERROR] No input on stdin. Pipe Spark Event Log content to this script.",
            file=sys.stderr,
        )
        print(
            f"  Example: aliyun ossutil cat <path> -e <endpoint> | "
            f"python3 {parser.prog}",
            file=sys.stderr,
        )
        sys.exit(1)

    lines = sys.stdin.readlines()
    if not lines:
        print(
            "[ERROR] Empty input. No Spark Event Log data received.",
            file=sys.stderr,
        )
        sys.exit(1)

    stage_completed_events, stage_submitted_events, task_events, app_events = parse_events(lines)

    if not stage_completed_events and not stage_submitted_events and not task_events:
        print(
            "[ERROR] No recognizable Spark events found in input.",
            file=sys.stderr,
        )
        sys.exit(1)

    result = analyze(stage_completed_events, stage_submitted_events, task_events, app_events, args)

    if args.output_format == "json":
        output_json(result)
    else:
        output_text(result)


if __name__ == "__main__":
    main()
