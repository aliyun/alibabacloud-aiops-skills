#!/usr/bin/env python3
"""
Alibaba Cloud Elasticsearch instance health check.

Concurrently collects instance status, CloudMonitor metrics, system events, and key logs,
applies Elasticsearch health-event rules (20260318 baseline), and prints a structured report
(findings + evidence + remediation).

Each Finding carries:
  event_code  — e.g. HealthCheck.ClusterUnhealthy
  reason_code — e.g. Cluster.StatusRed
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Shared helpers (time utilities) from _common
from _common import now_ms, ago_ms, ms_to_str, parse_utc

# Control-plane + CMS data collection via aliyun CLI
from openapi_cli_collect import (
    METRIC_DEFINITIONS,
    normalize_datapoints,
    fetch_instance_status_info,
    fetch_metrics_batch,
    fetch_events,
    fetch_log_items,
)


# ---------------------------------------------------------------------------
# Thresholds (ES health-event rules baseline 20260318)
# ---------------------------------------------------------------------------

THRESHOLDS = {
    # Cluster health (rules #1–3)
    "cluster_red":              2,      # ClusterStatus == 2 → Cluster.StatusRed (P0)
    "cluster_yellow":           1,      # ClusterStatus == 1 → Cluster.StatusYellow (P1)
    # CPU (rules #12–13: P0=70%, P1=60%; rule #11 peak: P0=95%, P1=80%)
    "cpu_sustained_critical":   70.0,   # avg CPU > 70% → CPU.PersistUsageHigh (P0)
    "cpu_sustained_warning":    60.0,   # avg CPU > 60% → CPU.PersistUsageHigh (P1)
    "cpu_peak_critical":        95.0,   # max CPU ≥ 95% → CPU.PeakUsageHigh (P0)
    "cpu_peak_warning":         80.0,   # max CPU ≥ 80% → CPU.PeakUsageHigh (P1)
    # Heap (rules #8–9: warning 75% P1, critical 85% P0)
    "heap_critical_avg":        85.0,   # avg heap > 85% → JVMMemory.OldGenUsageCritical (P0)
    "heap_warning_avg":         75.0,   # avg heap > 75% → JVMMemory.OldGenUsageHigh (P1)
    # Disk utilization (rules #13–14)
    "disk_critical_max":        85.0,   # max disk > 85% → Disk.UsageCritical (P0)
    "disk_warning_max":         75.0,   # max disk > 75% → Disk.UsageHigh (P1)
    # Disk IO (rule #19: IO util > 90% P0)
    "disk_io_max":              90.0,   # max IO util > 90% → Disk.IOPerformancePoor (P0)
    # Old GC rate (rule #22: >1/min → P1)
    "old_gc_rate_per_min":      1.0,    # max GC count per sample > 1 → JVMMemory.GCRateTooHigh (P1)
    # GC time ratio (rule #18: >10% wall time → P0)
    "gc_time_ratio":            0.10,   # avg GC duration / 60000ms > 10% → JVMMemory.GCTimeRatioTooHigh (P0)
    # CPU imbalance CV (rule #40) + absolute baseline (Bug-New-01)
    "load_imbalance_cv":        0.3,    # CV > 0.3 → Balancing.NodeCPUUnbalanced (P1)
    "load_imbalance_min_cpu":   10.0,   # require max node avg CPU > 10% before CV check (idle-cluster guard)
    # Disk / memory imbalance
    "disk_imbalance_cv":        0.3,    # CV > 0.3 → Balancing.NodeDiskUnbalanced
    "disk_imbalance_warning":   75.0,   # max node > 75% → P1
    "disk_imbalance_critical":  85.0,   # max node > 85% → P0
    "memory_imbalance_cv":      0.3,    # CV > 0.3 → Balancing.NodeMemoryUnbalanced
    "memory_imbalance_min":     75.0,   # fire only if max heap > 75%
    # Management-plane duration
    "activating_stuck_min":     30,     # activating longer than N min → stuck (P0)
    "event_stuck_min":          60,     # Executing event longer than N min → stuck (P1)
}

PRIORITY_ICON = {"P0": "🔴", "P1": "🟡", "P2": "🔵"}
PRIORITY_LABEL = {"P0": "Critical", "P1": "Warning", "P2": "Info"}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """One diagnostic finding."""
    event_code: str         # e.g. HealthCheck.ClusterUnhealthy
    reason_code: str        # e.g. Cluster.StatusRed
    name: str
    priority: str           # P0 / P1 / P2
    category: str
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    remediation: List[str] = field(default_factory=list)

    @property
    def code(self) -> str:
        """Backward compatible alias for event_code."""
        return self.event_code


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def _cv(values: List[float]) -> float:
    """Coefficient of variation std/mean."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    if mean == 0:
        return 0.0
    std = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5
    return std / mean


def _summarize(datapoints: List[Dict], metric_name: str) -> Dict[str, Dict]:
    """
    Group by node/cluster; compute avg / max / min / latest.
    Uses normalize_datapoints + METRIC_DEFINITIONS.
    Returns {group_key: {"avg", "max", "min", "latest", "points"}}.
    """
    meta = METRIC_DEFINITIONS.get(metric_name, {
        "group_field": "nodeIP",
        "value_field": "Average",
    })
    grouped = normalize_datapoints(datapoints, meta)
    result: Dict[str, Dict] = {}
    for key, points in grouped.items():
        valid_pts = [p for p in points if p["value"] is not None]
        if not valid_pts:
            continue
        vals = [p["value"] for p in valid_pts]
        # latest: newest sample by timestamp (current state), not window max
        latest_pt = max(valid_pts, key=lambda p: p.get("timestamp", 0))
        result[key] = {
            "avg":    sum(vals) / len(vals),
            "max":    max(vals),
            "min":    min(vals),
            "latest": latest_pt["value"],
            "points": valid_pts,  # raw points for time-series CV
        }
    return result


def _compute_timeseries_cv(summary: Dict[str, Dict]) -> Dict[str, Any]:
    """
    Time-series load imbalance: CV across nodes per timestamp, track peak window.

    Returns:
        cv_avg, cv_max, peak_cv, peak_time, peak_values
    """
    if len(summary) < 2:
        return {"cv_avg": 0.0, "cv_max": 0.0, "peak_cv": 0.0, "peak_time": 0, "peak_values": {}}
    
    # CV from per-node avg and per-node max series
    avg_vals = [s["avg"] for s in summary.values()]
    max_vals = [s["max"] for s in summary.values()]
    cv_avg = _cv(avg_vals)
    cv_max = _cv(max_vals)
    
    # Per-timestamp cross-node CV; track worst imbalance bucket
    all_timestamps = set()
    for s in summary.values():
        for pt in s.get("points", []):
            all_timestamps.add(pt.get("timestamp", 0))
    
    peak_cv = cv_avg
    peak_time = 0
    peak_values = {}
    
    for ts in sorted(all_timestamps):
        ts_values = {}
        for node, s in summary.items():
            for pt in s.get("points", []):
                if pt.get("timestamp") == ts and pt["value"] is not None:
                    ts_values[node] = pt["value"]
                    break
        
        if len(ts_values) >= 2:
            vals = list(ts_values.values())
            ts_cv = _cv(vals)
            if ts_cv > peak_cv:
                peak_cv = ts_cv
                peak_time = ts
                peak_values = ts_values
    
    return {
        "cv_avg": cv_avg,
        "cv_max": cv_max,
        "peak_cv": peak_cv,
        "peak_time": peak_time,
        "peak_values": peak_values,
    }


# Metrics subset for diagnosis (from METRIC_DEFINITIONS)
_DIAG_METRICS = [
    "ClusterStatus",
    "ClusterDisconnectedNodeCount",
    "ClusterNodeCount",
    "ClusterShardCount",
    "ClusterQueryQPS",
    "ClusterIndexQPS",
    "NodeCPUUtilization",
    "NodeHeapMemoryUtilization",
    "NodeDiskUtilization",
    "NodeFreeStorageSpace",
    "NodeLoad_1m",
    "NodeStatsDataDiskUtil",
    "JVMGCOldCollectionCount",
    "JVMGCOldCollectionDuration",
]


def _cms_period_for_window(window_min: int) -> str:
    """
    CMS sampling period from window length:
    - window ≤ 30 min → period 60s (finer; ~30 min retention for 60s series)
    - window > 30 min → period 300s (31-day retention; avoids empty CMS at 60s boundary)

    Bug-New-02: window=60 could align begin_ms outside 60s retention → empty datapoints.
    """
    return "60" if window_min <= 30 else "300"


def _get_cluster_setting(raw_settings: Dict, *keys: str) -> Optional[str]:
    """Walk transient → persistent → defaults; return first string leaf at *keys."""
    for section in ("transient", "persistent", "defaults"):
        node = raw_settings.get(section, {})
        for k in keys:
            node = node.get(k, {}) if isinstance(node, dict) else None
            if node is None:
                break
        if node and isinstance(node, str):
            return node
    return None


def _compute_security_score(findings: List[Finding]):
    """
    Overall health grade from finding severities.

    Returns (grade, icon, description):
      A — Healthy: no issues
      B — Stable: P2 hints only
      C — Warning: P1 present, respond within ~30 minutes
      D — Critical: P0 present, immediate action

    Rule: any P0 → D; P1 without P0 → C; P2 only → B; none → A.
    """
    p0 = [f for f in findings if f.priority == "P0"]
    p1 = [f for f in findings if f.priority == "P1"]
    p2 = [f for f in findings if f.priority == "P2"]

    if p0:
        return "D", "🔴", f"Critical — {len(p0)} P0 finding(s) require immediate action"
    if p1:
        return "C", "🟡", f"Warning — {len(p1)} P1 finding(s); respond within ~30 minutes"
    if p2:
        return "B", "🔵", f"Stable — {len(p2)} P2 informational finding(s) (no runtime risk)"
    return "A", "✅", "Healthy — no findings; instance appears normal"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

# Characters rejected in ES user/password (command-injection hardening for curl args)
_DANGEROUS_CHARS = set('`$(){}[]|;&<>\n\r')

def _validate_endpoint_consistency(
    endpoint: str,
    instance_id: Optional[str],
) -> Optional[str]:
    """
    Endpoint vs instance_id consistency (Bug-07).

    For *.aliyuncs.com public endpoints, require instance_id substring in URL
    to avoid optional ES checks hitting the wrong cluster.

    Returns:
        None — proceed
        "skip" — mismatch; warning printed; caller should skip optional checks
        "info" — private endpoint; informational message only
    """
    if not instance_id:
        return None
    
    is_aliyun_public = "aliyuncs.com" in endpoint
    instance_in_endpoint = instance_id.lower() in endpoint.lower()
    
    if is_aliyun_public and not instance_in_endpoint:
        print(
            f"⚠️  [ES config check] Endpoint mismatch (Bug-07):\n"
            f"   ES_ENDPOINT={endpoint}\n"
            f"   Does not contain diagnosed instance_id={instance_id}; endpoint may belong to another instance.\n"
            f"   Skipping optional config checks (circuit breakers / watermarks / thread pools) to avoid cross-instance false positives.\n"
            f"   Fix: export ES_ENDPOINT=\"http://<{instance_id}-endpoint>:9200\"",
            file=sys.stderr,
        )
        return "skip"
    elif not is_aliyun_public and not instance_in_endpoint:
        # Private IP/hostname — cannot infer ownership automatically
        print(
            f"ℹ️  [ES config check] Using private endpoint {endpoint} (not *.aliyuncs.com).\n"
            f"   Confirm this endpoint belongs to instance {instance_id}; otherwise results may reflect another cluster.",
            file=sys.stderr,
        )
        return "info"
    
    return None


def _validate_credentials_safe(username: str, password: str) -> bool:
    """
    Reject username/password if they contain characters unsafe for curl argv.

    Returns:
        True if safe to pass to curl -u; False if unsafe (message printed).
    """
    if any(c in _DANGEROUS_CHARS for c in password) or any(c in _DANGEROUS_CHARS for c in username):
        print(
            f"⚠️  [ES config check] Username/password contain unsafe characters; skipping Elasticsearch API collection.\n"
            f"   Do not use these in credentials: ` $ ( ) {{ }} [ ] | ; & < > newlines",
            file=sys.stderr,
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Data fetch / transform
# ---------------------------------------------------------------------------

def _fetch_error_logs(
    instance_id: str,
    region_id: str,
    begin_ms: int,
    end_ms: int,
    profile: Optional[str] = None,
) -> List[Dict]:
    """Fetch error/warning logs; normalize fields for rule engine."""
    try:
        raw_items = fetch_log_items(
            instance_id, region_id,
            log_type="INSTANCELOG",
            begin_ms=begin_ms,
            end_ms=end_ms,
            query="Exception OR OutOfMemory OR OOM OR ERROR",
            profile=profile,
        )
        logs = []
        for d in raw_items:
            cc = d.get("contentCollection") or {}
            if not isinstance(cc, dict):
                cc = {}
            logs.append({
                "level":   cc.get("level", ""),
                "host":    cc.get("host", d.get("host", "")),
                "time":    cc.get("time", ""),
                "content": (cc.get("content", "") or "")[:300],
            })
        return logs
    except Exception:
        return []


def _load_json_bundle(inline_json: Optional[str], json_file: Optional[str]) -> Dict[str, Any]:
    """Load injected diagnostic bundle from CLI args."""
    if inline_json:
        obj = json.loads(inline_json)
        return obj if isinstance(obj, dict) else {}
    if json_file:
        with open(json_file, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    return {}


# ---------------------------------------------------------------------------
# Rules — CMS / management metrics
# ---------------------------------------------------------------------------

def _check_instance_status(info: Dict) -> List[Finding]:
    findings = []
    if not info or "_error" in info:
        return findings

    status = info.get("status", "")
    updated_at_str = info.get("updated_at", "")

    if status == "activating" and updated_at_str:
        updated_at = parse_utc(updated_at_str)
        if updated_at:
            elapsed_min = (datetime.now(timezone.utc) - updated_at).total_seconds() / 60
            if elapsed_min > THRESHOLDS["activating_stuck_min"]:
                findings.append(Finding(
                    event_code="ManagementPlane.ActivatingStuck",
                    reason_code="ManagementPlane.ActivatingStuck",
                    name="Activating change stuck too long",
                    priority="P0",
                    category="Management plane",
                    description=(
                        f"Instance has stayed in activating for {int(elapsed_min)} minute(s) "
                        f"(last updated: {updated_at_str}); control-plane workflow may be stuck."
                    ),
                    evidence={
                        "current_status": status,
                        "last_updated_at": updated_at_str,
                        "elapsed_minutes": int(elapsed_min),
                    },
                    remediation=[
                        "In the console or CMS, check for system events stuck in Executing",
                        "If no legitimate in-flight change, trigger a harmless update (e.g. description) to refresh state",
                        "Contact Alibaba Cloud support if the workflow remains stuck",
                    ],
                ))
    elif status == "inactive":
        findings.append(Finding(
            event_code="ManagementPlane.InstanceInactive",
            reason_code="ManagementPlane.InstanceInactive",
            name="Instance frozen (inactive)",
            priority="P0",
            category="Management plane",
            description="Instance is inactive (frozen), often due to billing or manual freeze; service unavailable.",
            evidence={"current_status": status},
            remediation=[
                "Verify account balance and payment status",
                "After payment, contact support to unfreeze if needed",
            ],
        ))
    elif status == "invalid":
        findings.append(Finding(
            event_code="ManagementPlane.InstanceInvalid",
            reason_code="ManagementPlane.InstanceInvalid",
            name="Instance invalid",
            priority="P0",
            category="Management plane",
            description="Instance is invalid; service unavailable.",
            evidence={"current_status": status},
            remediation=["Contact Alibaba Cloud support to determine cause and remediation"],
        ))
    return findings


def _check_cluster_health(metrics: Dict[str, List[Dict]]) -> List[Finding]:
    findings = []

    # --- Cluster health (CMS ClusterStatus) ---
    cluster_status_dps = metrics.get("ClusterStatus", [])
    if cluster_status_dps:
        summary = _summarize(cluster_status_dps, "ClusterStatus")
        for cid, stat in summary.items():
            # Use latest sample, not max, so stale Red in the window does not override current state
            current_status = stat["latest"]
            if current_status >= THRESHOLDS["cluster_red"]:
                findings.append(Finding(
                    event_code="HealthCheck.ClusterUnhealthy",
                    reason_code="Cluster.StatusRed",
                    name="Cluster status Red",
                    priority="P0",
                    category="Cluster health",
                    description="Cluster is Red: at least one primary shard is unassigned; some data is unavailable.",
                    evidence={
                        "cluster_status_latest": f"{int(current_status)} (Red)",
                        "cluster_status_window_max": f"{int(stat['max'])}",
                        "sample_point_count": len(cluster_status_dps),
                    },
                    remediation=[
                        "GET _cat/indices?v&health=red          # list red indices",
                        "GET _cat/shards?v&h=index,shard,prirep,state,node,unassigned.reason  # shard state",
                        "GET _cluster/allocation/explain        # unassigned reason",
                        "Fix root cause: offline node → recover; disk full → free space / expand; bad settings → correct",
                    ],
                ))
            elif current_status >= THRESHOLDS["cluster_yellow"]:
                findings.append(Finding(
                    event_code="HealthCheck.ClusterUnhealthy",
                    reason_code="Cluster.StatusYellow",
                    name="Cluster status Yellow",
                    priority="P1",
                    category="Cluster health",
                    description="Cluster is Yellow: all primaries assigned but at least one replica is unassigned.",
                    evidence={
                        "cluster_status_latest": f"{int(current_status)} (Yellow)",
                        "cluster_status_window_max": f"{int(stat['max'])}",
                    },
                    remediation=[
                        "GET _cat/shards?v&h=index,shard,prirep,state,unassigned.reason | grep UNASSIGNED",
                        "GET _cluster/allocation/explain        # replica allocation reason",
                        "If disk pressure: delete cold data or expand capacity",
                        "If relocation in progress: wait for completion",
                    ],
                ))

    # --- Disconnected nodes ---
    disconn_dps = metrics.get("ClusterDisconnectedNodeCount", [])
    if disconn_dps:
        summary = _summarize(disconn_dps, "ClusterDisconnectedNodeCount")
        for _, stat in summary.items():
            if stat["max"] > 0:
                findings.append(Finding(
                    event_code="HealthCheck.ClusterUnhealthy",
                    reason_code="Node.Disconnected",
                    name="Node disconnected or failed",
                    priority="P0",
                    category="Cluster health",
                    description=f"Up to {int(stat['max'])} node(s) disconnected from the cluster; data on those nodes may be unavailable.",
                    evidence={
                        "max_disconnected_nodes": int(stat["max"]),
                        "avg_disconnected_nodes": round(stat["avg"], 2),
                    },
                    remediation=[
                        "GET _cat/nodes?v                       # which nodes are missing",
                        "Check ES logs on offline nodes: OutOfMemoryError / JVM crash / Connection refused",
                        "OOM → more heap or query tuning; network → fix connectivity; high CPU → reduce load",
                        "After restart: GET _cat/recovery?v&active_only=true",
                    ],
                ))
    return findings


def _check_cpu(metrics: Dict[str, List[Dict]]) -> List[Finding]:
    findings = []
    dps = metrics.get("NodeCPUUtilization", [])
    if not dps:
        return findings

    summary = _summarize(dps, "NodeCPUUtilization")

    # P0: avg > 70%; P1: 60% < avg <= 70% (rules #12–13)
    critical  = [(n, s) for n, s in summary.items() if s["avg"] > THRESHOLDS["cpu_sustained_critical"]]
    warning   = [(n, s) for n, s in summary.items()
                 if THRESHOLDS["cpu_sustained_warning"] < s["avg"] <= THRESHOLDS["cpu_sustained_critical"]]
    # Peak: sustained avg not high (<= 60%) but spike high — >=95% P0, >=80% P1 (rule #11 extension)
    peak_critical = [(n, s) for n, s in summary.items()
                     if s["max"] >= THRESHOLDS["cpu_peak_critical"] and
                     s["avg"] <= THRESHOLDS["cpu_sustained_warning"]]
    peak_warning  = [(n, s) for n, s in summary.items()
                     if THRESHOLDS["cpu_peak_warning"] <= s["max"] < THRESHOLDS["cpu_peak_critical"] and
                     s["avg"] <= THRESHOLDS["cpu_sustained_warning"]]

    if critical:
        findings.append(Finding(
            event_code="HealthCheck.CPULoadHigh",
            reason_code="CPU.PersistUsageHigh",
            name="Sustained high CPU (critical)",
            priority="P0",
            category="Resource metrics",
            description=(
                f"Node CPU average exceeds {THRESHOLDS['cpu_sustained_critical']}%; "
                f"severe bottleneck — high risk of node loss or cascading failure."
            ),
            evidence={
                "affected_nodes": [
                    f"{n}  avg={s['avg']:.1f}%  max={s['max']:.1f}%"
                    for n, s in critical
                ]
            },
            remediation=[
                "GET _nodes/hot_threads                 # hot threads",
                "GET _tasks?detailed=true&actions=*search*  # find/cancel heavy searches",
                "Throttle clients: lower QPS or pause bulk ingest temporarily",
                "Tune slow queries: filters, avoid deep pagination, reduce wildcard/fuzzy",
                "Scale out: add data nodes or upgrade instance class if urgent",
            ],
        ))
    elif warning:
        findings.append(Finding(
            event_code="HealthCheck.CPULoadHigh",
            reason_code="CPU.PersistUsageHigh",
            name="Sustained high CPU (warning)",
            priority="P1",
            category="Resource metrics",
            description=(
                f"Node CPU average exceeds {THRESHOLDS['cpu_sustained_warning']}%; "
                f"elevated load — watch for slow queries or write backlog."
            ),
            evidence={
                "affected_nodes": [
                    f"{n}  avg={s['avg']:.1f}%  max={s['max']:.1f}%"
                    for n, s in warning
                ]
            },
            remediation=[
                "GET _nodes/hot_threads                 # CPU consumers",
                "GET _tasks?detailed=true               # in-flight tasks",
                "Tune slow queries: deep pagination, wildcard, large aggs",
                "Consider more nodes or larger nodes if sustained",
            ],
        ))
    elif peak_critical:
        findings.append(Finding(
            event_code="HealthCheck.CPULoadHigh",
            reason_code="CPU.PeakUsageHigh",
            name="CPU spike critical",
            priority="P0",
            category="Resource metrics",
            description=(
                f"Node CPU peak ≥ {THRESHOLDS['cpu_peak_critical']}%; "
                f"very high risk of heartbeat timeouts and nodes leaving the cluster."
            ),
            evidence={
                "affected_nodes": [
                    f"{n}  max={s['max']:.1f}%  avg={s['avg']:.1f}%"
                    for n, s in peak_critical
                ]
            },
            remediation=[
                "Cancel heavy tasks: GET _tasks?detailed=true&actions=*search*",
                "GET _nodes/hot_threads                 # identify CPU consumers",
                "Temporarily reduce client concurrency",
                "Tune heavy queries: BKD ranges, large aggs, complex scripts",
                "Scale out or upgrade nodes if spikes recur",
            ],
        ))
    elif peak_warning:
        findings.append(Finding(
            event_code="HealthCheck.CPULoadHigh",
            reason_code="CPU.PeakUsageHigh",
            name="CPU spike warning",
            priority="P1",
            category="Resource metrics",
            description=(
                f"Node CPU peak in {THRESHOLDS['cpu_peak_warning']}–{THRESHOLDS['cpu_peak_critical']}%; "
                f"not sustained high load, but spikes indicate heavy queries or ingest bursts "
                f"that may become sustained if ignored."
            ),
            evidence={
                "affected_nodes": [
                    f"{n}  max={s['max']:.1f}%  avg={s['avg']:.1f}%"
                    for n, s in peak_warning
                ]
            },
            remediation=[
                "GET _nodes/hot_threads                 # CPU consumers",
                "GET _tasks?detailed=true               # in-flight tasks",
                "Tune heavy queries: large aggs, deep pagination, BKD-heavy patterns",
                "Consider more nodes or larger nodes if spikes recur",
            ],
        ))

    # Load imbalance (rule #40) — time-series CV
    cv_stats = _compute_timeseries_cv(summary)
    cv_avg = cv_stats["cv_avg"]
    cv_max = cv_stats["cv_max"]
    peak_cv = cv_stats["peak_cv"]
    peak_time = cv_stats["peak_time"]
    peak_values = cv_stats["peak_values"]
    
    avg_vals = [s["avg"] for s in summary.values()]
    max_vals = [s["max"] for s in summary.values()]
    max_avg_cpu = max(avg_vals) if avg_vals else 0.0
    
    # Use max of peak / window CV so a short spike is not averaged away
    effective_cv = max(cv_avg, cv_max, peak_cv)
    
    # Absolute CPU floor: skip CV when cluster is idle (idle-cluster CV false positive guard)
    if (effective_cv > THRESHOLDS["load_imbalance_cv"]
            and len(avg_vals) >= 2
            and max_avg_cpu > THRESHOLDS["load_imbalance_min_cpu"]):
        
        evidence = {
            "cv_avg_full_window": round(cv_avg, 3),
            "cv_max_full_window": round(cv_max, 3),
            "cv_peak_window": round(peak_cv, 3),
            "max_node_cpu_avg_pct": f"{max(avg_vals):.1f}%",
            "min_node_cpu_avg_pct": f"{min(avg_vals):.1f}%",
            "max_node_cpu_max_pct": f"{max(max_vals):.1f}%",
            "avg_spread_pct": f"{max(avg_vals) - min(avg_vals):.1f}%",
            "node_count": len(avg_vals),
        }
        
        if peak_cv > cv_avg and peak_time and peak_values:
            evidence["peak_time_local"] = ms_to_str(peak_time)
            evidence["peak_window_cpu_by_node"] = [
                f"{node}: {val:.1f}%" for node, val in sorted(peak_values.items(), key=lambda x: -x[1])
            ]
        
        desc_suffix = ""
        if peak_cv > cv_avg * 1.2:
            desc_suffix = (
                f" Note: peak-window CV={peak_cv:.2f} is much higher than average — inspect that time range."
            )
        
        findings.append(Finding(
            event_code="HealthCheck.LoadUnbalanced",
            reason_code="Balancing.NodeCPUUnbalanced",
            name="Uneven CPU load across nodes",
            priority="P1",
            category="Capacity planning",
            description=(
                f"Cross-node CPU coefficient of variation CV={effective_cv:.2f} "
                f"(threshold {THRESHOLDS['load_imbalance_cv']}); "
                f"max avg {max(avg_vals):.1f}%, min avg {min(avg_vals):.1f}%. "
                f"Common causes: uneven shard counts, hot shards, missing coordinating nodes.{desc_suffix}"
            ),
            evidence=evidence,
            remediation=[
                "# Step 1 — shard balance (common root cause)",
                "GET _cat/nodes?v&h=name,ip,cpu,heap.percent,disk.used_percent,shards",
                "GET _cat/allocation?v",
                "",
                "# Step 2 — hot indices / large shards",
                "GET _cat/shards?v&s=store:desc&h=index,shard,prirep,store,node",
                "GET _cat/indices?v&s=store.size:desc&h=index,pri,rep,store.size",
                "",
                "# Step 3 — rebalance",
                "POST _cluster/reroute { \"commands\": [{\"move\": {\"index\": \"hot_index\", \"shard\": 0, \"from_node\": \"node_busy\", \"to_node\": \"node_idle\"}}] }",
                "",
                "# Longer term",
                "Add coordinating-only nodes, ILM for tiering, tune routing where applicable",
            ],
        ))
    return findings


def _check_memory(metrics: Dict[str, List[Dict]]) -> List[Finding]:
    findings = []
    dps = metrics.get("NodeHeapMemoryUtilization", [])
    if not dps:
        return findings

    summary = _summarize(dps, "NodeHeapMemoryUtilization")
    # rule #9: P0 critical=85%; rule #8: P1 warning=75%
    critical = [(n, s) for n, s in summary.items() if s["avg"] > THRESHOLDS["heap_critical_avg"]]
    warning  = [(n, s) for n, s in summary.items()
                if THRESHOLDS["heap_warning_avg"] < s["avg"] <= THRESHOLDS["heap_critical_avg"]]

    if critical:
        findings.append(Finding(
            event_code="HealthCheck.JVMMemoryPressure",
            reason_code="JVMMemory.OldGenUsageCritical",
            name="Heap usage critical (OOM risk)",
            priority="P0",
            category="Resource metrics",
            description=(
                f"Node heap utilization avg exceeds {THRESHOLDS['heap_critical_avg']}%; "
                f"OutOfMemoryError risk is high."
            ),
            evidence={
                "affected_nodes": [
                    f"{n}  avg={s['avg']:.1f}%  max={s['max']:.1f}%"
                    for n, s in critical
                ]
            },
            remediation=[
                "POST _cache/clear                      # clear caches",
                "GET _tasks?detailed=true&actions=*search*  # find heavy tasks",
                "POST _tasks/<task_id>/_cancel           # cancel large tasks",
                "Restart affected nodes off-peak if required (brief disruption)",
                "Longer term: larger heap / node class; avoid huge result sets",
            ],
        ))
    elif warning:
        findings.append(Finding(
            event_code="HealthCheck.JVMMemoryPressure",
            reason_code="JVMMemory.OldGenUsageHigh",
            name="Heap usage warning",
            priority="P1",
            category="Resource metrics",
            description=(
                f"Node heap utilization avg exceeds {THRESHOLDS['heap_warning_avg']}%; "
                f"OOM risk and frequent Full GC are possible."
            ),
            evidence={
                "affected_nodes": [
                    f"{n}  avg={s['avg']:.1f}%  max={s['max']:.1f}%"
                    for n, s in warning
                ]
            },
            remediation=[
                "GET _nodes/stats/jvm?filter_path=nodes.*.jvm.mem",
                "POST _cache/clear",
                "POST /index_name/_cache/clear?fielddata=true  # fielddata cache",
                "Tune queries: smaller pages, less fielddata, shallower aggs",
                "Consider larger nodes if sustained",
            ],
        ))

    # GC time ratio (rule #18: P0 when GC time > 10% of wall clock per sample window)
    gc_dur_dps = metrics.get("JVMGCOldCollectionDuration", [])
    if gc_dur_dps:
        dur_summary = _summarize(gc_dur_dps, "JVMGCOldCollectionDuration")
        # JVMGCOldCollectionDuration: GC ms per sample bucket; ratio = avg_ms / 60000
        gc_ratio_nodes = [
            (n, s, s["avg"] / 60000.0)
            for n, s in dur_summary.items()
            if s["avg"] / 60000.0 > THRESHOLDS["gc_time_ratio"]
        ]
        if gc_ratio_nodes:
            findings.append(Finding(
                event_code="HealthCheck.JVMMemoryPressure",
                reason_code="JVMMemory.GCTimeRatioTooHigh",
                name="GC time ratio too high",
                priority="P0",
                category="Resource metrics",
                description=(
                    f"Old GC time exceeds {THRESHOLDS['gc_time_ratio'] * 100:.0f}% of wall time; "
                    f"pauses hurt search and indexing latency."
                ),
                evidence={
                    "affected_nodes": [
                        f"{n}  avg_gc_ms={s['avg']:.0f}/min  ratio={ratio * 100:.1f}%"
                        for n, s, ratio in gc_ratio_nodes
                    ]
                },
                remediation=[
                    "GET _nodes/stats/jvm",
                    "POST _cache/clear            # relieve heap pressure",
                    "Inspect large fielddata / request cache usage",
                    "Tune GC / heap only after confirming collector + pause profile "
                    "(see jvm.gc.collectors in _nodes/stats/jvm or node GC logs; do not assume G1 vs CMS from version alone)",
                    "Reduce heavy aggs / large allocations",
                ],
            ))

    # Old GC frequency (rule #22: P1, >1 per minute)
    gc_cnt_dps = metrics.get("JVMGCOldCollectionCount", [])
    if gc_cnt_dps:
        gc_summary = _summarize(gc_cnt_dps, "JVMGCOldCollectionCount")
        gc_nodes = [(n, s) for n, s in gc_summary.items()
                    if s["max"] > THRESHOLDS["old_gc_rate_per_min"]]
        if gc_nodes:
            findings.append(Finding(
                event_code="HealthCheck.JVMMemoryPressure",
                reason_code="JVMMemory.GCRateTooHigh",
                name="Old GC too frequent",
                priority="P1",
                category="Resource metrics",
                description=(
                    f"Old GC rate exceeds {THRESHOLDS['old_gc_rate_per_min']:.0f}/minute; "
                    f"heap pressure may increase search/index latency."
                ),
                evidence={
                    "affected_nodes": [
                        f"{n}  max_gc={s['max']:.1f}/min  avg_gc={s['avg']:.1f}/min"
                        for n, s in gc_nodes
                    ]
                },
                remediation=[
                    "GET _nodes/stats/jvm",
                    "Check fielddata and deep aggregations on heap",
                    "Tune queries to reduce memory churn",
                    "Tune GC / heap or upgrade nodes if sustained (confirm collector via jvm stats or GC logs, not version guesswork)",
                ],
            ))
    return findings


def _check_disk(metrics: Dict[str, List[Dict]]) -> List[Finding]:
    findings = []
    dps = metrics.get("NodeDiskUtilization", [])
    if not dps:
        return findings

    summary = _summarize(dps, "NodeDiskUtilization")
    # rule #14: P0 critical=85%; rule #13: P1 warning=75%
    critical = [(n, s) for n, s in summary.items() if s["max"] > THRESHOLDS["disk_critical_max"]]
    warning  = [(n, s) for n, s in summary.items()
                if THRESHOLDS["disk_warning_max"] < s["max"] <= THRESHOLDS["disk_critical_max"]]

    if critical:
        findings.append(Finding(
            event_code="HealthCheck.DiskUsageHigh",
            reason_code="Disk.UsageCritical",
            name="Disk usage critical",
            priority="P0",
            category="Resource metrics",
            description=(
                f"Node disk usage exceeds {THRESHOLDS['disk_critical_max']}%; "
                f"near ES flood-stage (~95%) writes may fail."
            ),
            evidence={
                "affected_nodes": [
                    f"{n}  max={s['max']:.1f}%  avg={s['avg']:.1f}%"
                    for n, s in critical
                ]
            },
            remediation=[
                "GET _cat/allocation?v",
                "GET _cat/indices?v&s=store.size:desc   # largest indices",
                "DELETE /old_index                      # drop cold indices if safe",
                "PUT _all/_settings {\"index.blocks.read_only_allow_delete\": null}  # clear read-only if set",
                "Expand disk capacity in console if needed",
            ],
        ))
    elif warning:
        findings.append(Finding(
            event_code="HealthCheck.DiskUsageHigh",
            reason_code="Disk.UsageHigh",
            name="Disk usage warning",
            priority="P1",
            category="Resource metrics",
            description=(
                f"Node disk usage exceeds {THRESHOLDS['disk_warning_max']}%; "
                f"free space before flood-stage read-only (~95%)."
            ),
            evidence={
                "affected_nodes": [
                    f"{n}  max={s['max']:.1f}%"
                    for n, s in warning
                ]
            },
            remediation=[
                "GET _cat/indices?v&s=store.size:desc",
                "Delete or archive cold data (e.g. OSS)",
                "Use ILM to expire old indices",
                "Plan disk expansion if growth continues",
            ],
        ))

    # Disk IO utilization (rule #19: P0 when IO util > 90%)
    io_dps = metrics.get("NodeStatsDataDiskUtil", [])
    if io_dps:
        io_summary = _summarize(io_dps, "NodeStatsDataDiskUtil")
        io_nodes = [(n, s) for n, s in io_summary.items()
                    if s["max"] > THRESHOLDS["disk_io_max"]]
        if io_nodes:
            findings.append(Finding(
                event_code="HealthCheck.DiskIOBottleneck",
                reason_code="Disk.IOPerformancePoor",
                name="Disk IO utilization too high",
                priority="P0",
                category="Resource metrics",
                description=(
                    f"Disk IO utilization exceeds {THRESHOLDS['disk_io_max']}%; "
                    f"higher IO latency can cause heartbeat loss or node drop-out."
                ),
                evidence={
                    "affected_nodes": [
                        f"{n}  max_io={s['max']:.1f}%  avg_io={s['avg']:.1f}%"
                        for n, s in io_nodes
                    ]
                },
                remediation=[
                    "Lower ingest pressure: fewer concurrent bulks, larger bulk batches",
                    "Raise refresh_interval (e.g. 30s) to cut refresh cost",
                    "PUT _cluster/settings {\"indices.merge.scheduler.max_thread_count\": 1}",
                    "Longer term: faster disk tier (ESSD PL1/PL2)",
                ],
            ))
    return findings


def _check_resource_imbalance(metrics: Dict[str, List[Dict]]) -> List[Finding]:
    """
    Detect uneven disk and heap utilization across nodes (CV-based).

    Complements CPU imbalance in _check_cpu. See references/sop-node-load-imbalance.md.
    """
    findings = []
    
    # --- Disk utilization imbalance ---
    disk_dps = metrics.get("NodeDiskUtilization", [])
    if disk_dps:
        disk_summary = _summarize(disk_dps, "NodeDiskUtilization")
        if len(disk_summary) >= 2:
            cv_stats = _compute_timeseries_cv(disk_summary)
            cv_avg = cv_stats["cv_avg"]
            cv_max = cv_stats["cv_max"]
            peak_cv = cv_stats["peak_cv"]
            effective_cv = max(cv_avg, cv_max, peak_cv)
            
            avg_vals = [s["avg"] for s in disk_summary.values()]
            max_vals = [s["max"] for s in disk_summary.values()]
            max_disk = max(max_vals)  # use max utilization for severity
            min_disk = min(avg_vals)
            
            if effective_cv > THRESHOLDS["disk_imbalance_cv"]:
                if max_disk > THRESHOLDS["disk_imbalance_critical"]:
                    priority = "P0"
                    desc_suffix = "Hot node above critical watermark — read-only / flood risk."
                elif max_disk > THRESHOLDS["disk_imbalance_warning"]:
                    priority = "P1"
                    desc_suffix = "Hot node disk high — rebalance shards soon."
                else:
                    priority = "P2"
                    desc_suffix = "CV high but absolute disk OK — plan rebalance."
                
                findings.append(Finding(
                    event_code="HealthCheck.LoadUnbalanced",
                    reason_code="Balancing.NodeDiskUnbalanced",
                    name="Uneven disk usage across nodes",
                    priority=priority,
                    category="Capacity planning",
                    description=(
                        f"Cross-node disk utilization CV={effective_cv:.2f} "
                        f"(threshold {THRESHOLDS['disk_imbalance_cv']}); "
                        f"max {max_disk:.1f}%, min {min_disk:.1f}%. "
                        f"Common causes: uneven shard counts / large shards on few nodes. {desc_suffix}"
                    ),
                    evidence={
                        "cv_avg_full_window": round(cv_avg, 3),
                        "cv_max_full_window": round(cv_max, 3),
                        "cv_peak_window": round(peak_cv, 3),
                        "max_node_disk_pct": f"{max_disk:.1f}%",
                        "min_node_disk_avg_pct": f"{min_disk:.1f}%",
                        "spread_pct": f"{max_disk - min_disk:.1f}%",
                        "node_count": len(avg_vals),
                        "top_nodes": [
                            f"{n}  avg={s['avg']:.1f}%  max={s['max']:.1f}%"
                            for n, s in sorted(disk_summary.items(), key=lambda x: -x[1]["max"])
                        ][:5],
                    },
                    remediation=[
                        "# Step 1 — shard balance",
                        "GET _cat/nodes?v&h=name,ip,disk.used_percent,shards",
                        "GET _cat/allocation?v",
                        "",
                        "# Step 2 — move large shards",
                        "GET _cat/shards?v&s=store:desc&h=index,shard,prirep,store,node",
                        "POST _cluster/reroute { \"commands\": [{\"move\": {...}}] }",
                        "",
                        "# Longer term",
                        "Tune disk watermarks for earlier relocation; ILM for retention",
                    ],
                ))
    
    # --- Heap utilization imbalance ---
    heap_dps = metrics.get("NodeHeapMemoryUtilization", [])
    if heap_dps:
        heap_summary = _summarize(heap_dps, "NodeHeapMemoryUtilization")
        if len(heap_summary) >= 2:
            cv_stats = _compute_timeseries_cv(heap_summary)
            cv_avg = cv_stats["cv_avg"]
            cv_max = cv_stats["cv_max"]
            peak_cv = cv_stats["peak_cv"]
            effective_cv = max(cv_avg, cv_max, peak_cv)
            
            avg_vals = [s["avg"] for s in heap_summary.values()]
            max_vals = [s["max"] for s in heap_summary.values()]
            max_heap = max(max_vals)
            min_heap = min(avg_vals)
            
            if (effective_cv > THRESHOLDS["memory_imbalance_cv"]
                    and max_heap > THRESHOLDS["memory_imbalance_min"]):
                findings.append(Finding(
                    event_code="HealthCheck.LoadUnbalanced",
                    reason_code="Balancing.NodeMemoryUnbalanced",
                    name="Uneven heap usage across nodes",
                    priority="P1",
                    category="Capacity planning",
                    description=(
                        f"Cross-node heap utilization CV={effective_cv:.2f} "
                        f"(threshold {THRESHOLDS['memory_imbalance_cv']}); "
                        f"max {max_heap:.1f}%, min {min_heap:.1f}%. "
                        f"Common causes: uneven shards, fielddata skew, hot caches."
                    ),
                    evidence={
                        "cv_avg_full_window": round(cv_avg, 3),
                        "cv_max_full_window": round(cv_max, 3),
                        "cv_peak_window": round(peak_cv, 3),
                        "max_node_heap_pct": f"{max_heap:.1f}%",
                        "min_node_heap_avg_pct": f"{min_heap:.1f}%",
                        "spread_pct": f"{max_heap - min_heap:.1f}%",
                        "node_count": len(avg_vals),
                        "top_nodes": [
                            f"{n}  avg={s['avg']:.1f}%  max={s['max']:.1f}%"
                            for n, s in sorted(heap_summary.items(), key=lambda x: -x[1]["max"])
                        ][:5],
                    },
                    remediation=[
                        "# Step 1 — shard balance",
                        "GET _cat/nodes?v&h=name,ip,heap.percent,shards",
                        "",
                        "# Step 2 — fielddata",
                        "GET _cat/fielddata?v&s=size:desc",
                        "GET _nodes/stats/indices?filter_path=nodes.*.indices.fielddata",
                        "",
                        "# Step 3 — rebalance / query tuning",
                        "Avoid huge text field aggs; reroute shards if needed",
                        "POST _cluster/reroute { \"commands\": [{\"move\": {...}}] }",
                    ],
                ))
    
    return findings


def _check_metrics_sparse(metrics: Dict[str, List[Dict]], window_min: int, period: str) -> None:
    """
    Warn on stderr when CMS datapoints are much sparser than expected.

    Sparse if ClusterStatus / NodeCPUUtilization point count < 20% of expected minimum.
    """
    key_metrics = ["ClusterStatus", "NodeCPUUtilization"]
    expected_min = max(1, window_min // (int(period) // 60))
    threshold   = max(1, int(expected_min * 0.2))

    sparse = [
        m for m in key_metrics
        if len(metrics.get(m, [])) < threshold
    ]
    if sparse:
        print(
            f"\n⚠️  [CMS] Sparse datapoints for key metrics: {sparse}\n"
            f"   Possible causes:\n"
            f"   1. Retention / granularity window shorter than {window_min} minutes (try --window 30)\n"
            f"   2. Fault injection just started; wait ≥5 minutes for CMS to populate\n"
            f"   3. Wrong instance ID or region — CMS returned no data\n"
            f"   Conclusions may be incomplete; interpret with care.",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Rules — events / logs
# ---------------------------------------------------------------------------

def _check_events(events: List[Dict]) -> List[Finding]:
    findings = []
    now_utc = datetime.now(timezone.utc)
    stuck = []
    for e in events:
        if e.get("event_status") == "Executing":
            start_dt = parse_utc(e.get("start_time", ""))
            if start_dt:
                elapsed = (now_utc - start_dt).total_seconds() / 60
                if elapsed > THRESHOLDS["event_stuck_min"]:
                    stuck.append({
                        "event_name": e.get("name", ""),
                        "reason": e.get("reason", ""),
                        "start_time": e.get("start_time", ""),
                        "elapsed_minutes": int(elapsed),
                    })
    if stuck:
        findings.append(Finding(
            event_code="ManagementPlane.EventStuck",
            reason_code="ManagementPlane.EventStuck",
            name="Change event stuck in Executing",
            priority="P1",
            category="Management plane",
            description=(
                f"{len(stuck)} system event(s) stayed Executing longer than "
                f"{THRESHOLDS['event_stuck_min']} minutes; change may be stuck."
            ),
            evidence={"stuck_events": stuck},
            remediation=[
                "Check change progress in the Alibaba Cloud console",
                "If truly stuck, contact support with event IDs",
                "Also verify data-node health — node faults often block changes",
            ],
        ))
    return findings


def _check_logs(logs: List[Dict]) -> List[Finding]:
    findings = []
    oom = [l for l in logs if "OutOfMemoryError" in l.get("content", "") or
           ("OOM" in l.get("content", "") and "ERROR" in l.get("content", "").upper())]
    if oom:
        sample = oom[0]
        findings.append(Finding(
            event_code="HealthCheck.JVMMemoryPressure",
            reason_code="JVMMemory.OOM",
            name="Node OutOfMemoryError",
            priority="P0",
            category="Resource metrics",
            description="Logs show OutOfMemoryError; node likely ran out of heap and may have restarted.",
            evidence={
                "oom_log_lines": len(oom),
                "affected_host": sample.get("host", "-"),
                "log_time": sample.get("time", "-"),
                "log_excerpt": sample.get("content", "")[:150],
            },
            remediation=[
                "Restart affected nodes after confirming recovery path",
                "GET _nodes/stats/jvm",
                "Analyze heap dumps if captured",
                "Increase heap / node size; reduce query memory footprint",
            ],
        ))

    # UnavailableShardsException in logs (often alongside Red)
    shard_errs = [l for l in logs if "UnavailableShardsException" in l.get("content", "")]
    if shard_errs and not oom:
        sample = shard_errs[0]
        # Extract index name from log line (supports [[idx][0]] style)
        m = re.search(r"\[+([^\]\[]+)\]\[0\] primary shard is not active", sample.get("content", ""))
        idx_name = m.group(1) if m else "unknown"

        # System indices (.monitoring-*, .security-*, .kibana*, …) → P2 informational:
        # usually a side-effect of resource pressure, not primary business data loss.
        _SYS_PREFIXES = (".monitoring-", ".security-", ".kibana",  # .kibana-* / .kibana_
                         ".apm-", ".fleet-", ".async-search", ".ds-ilm", ".watches")
        is_system_idx = any(idx_name.startswith(p) for p in _SYS_PREFIXES)

        findings.append(Finding(
            event_code="HealthCheck.ClusterUnhealthy",
            reason_code="Cluster.UnavailableShards",
            name=(
                "System index shard unavailable (informational)"
                if is_system_idx else
                "Primary shard unavailable"
            ),
            priority="P2" if is_system_idx else "P0",
            category="Informational" if is_system_idx else "Cluster health",
            description=(
                f"UnavailableShardsException in logs (index: {idx_name})."
                + (
                    " System / stack index — unassigned shards often follow CPU or heap pressure; "
                    "fix resource pressure first."
                    if is_system_idx else
                    " Primary shard inactive — reads/writes to this index will time out."
                )
            ),
            evidence={
                "matching_log_lines": len(shard_errs),
                "sample_index": idx_name,
                "is_system_index": "yes" if is_system_idx else "no",
                "affected_host": sample.get("host", "-"),
                "log_excerpt": sample.get("content", "")[:150],
            },
            remediation=(
                [
                    "Usually no direct fix on the system index — relieve CPU/heap pressure first",
                    "Optional cleanup: DELETE .monitoring-es-7-* (expired monitoring)",
                    "To disable: xpack.monitoring in kibana.yml (product-specific)",
                ]
                if is_system_idx else
                [
                    "GET _cat/shards?v&h=index,shard,prirep,state,unassigned.reason",
                    "GET _cluster/allocation/explain",
                    "Apply allocation explain guidance (disk, settings, node availability)",
                ]
            ),
        ))
    return findings


# ---------------------------------------------------------------------------
# Rules — optional ES API (cluster settings / _cat / thread pool)
# ---------------------------------------------------------------------------

def _check_fielddata_breaker(raw_settings: Dict) -> List[Finding]:
    """Fielddata circuit breaker limit vs recommended 40%."""
    findings: List[Finding] = []
    fd_limit = _get_cluster_setting(raw_settings, "indices", "breaker", "fielddata", "limit")
    if not fd_limit or "%" not in fd_limit:
        return findings
    try:
        pct = float(fd_limit.rstrip("%"))
    except ValueError:
        return findings
    if pct < 40.0:
        findings.append(Finding(
            event_code="HealthCheck.JVMMemoryPressure",
            reason_code="JVMMemory.BreakerLimitConfigLow",
            name="Fielddata breaker limit too low",
            priority="P2",
            category="Configuration",
            description=(
                f"indices.breaker.fielddata.limit = {fd_limit}, below the 40% recommendation. "
                f"Even when tripped=0, text-field aggregations can easily hit CircuitBreakingException."
            ),
            evidence={
                "configured_value": fd_limit,
                "recommended": "40% (Elasticsearch default)",
                "risk": "Low traffic hides the issue until a spike trips the breaker",
            },
            remediation=[
                'PUT _cluster/settings { "persistent": { "indices.breaker.fielddata.limit": "40%" } }',
                "Before changing: GET _nodes/stats/indices/fielddata?fields=*",
            ],
        ))
    return findings



def _parse_watermark_to_bytes(value: str) -> Optional[int]:
    """Parse disk watermark to bytes. Percentages return None; supports e.g. 500gb, 19605mb, 1000000b."""
    if not value:
        return None
    value = value.strip().lower()
    if "%" in value:
        return None  # percentage watermarks are handled separately
    multipliers = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4, "pb": 1024**5}
    for suffix, mult in sorted(multipliers.items(), key=lambda x: -len(x[0])):
        if value.endswith(suffix):
            try:
                return int(float(value[:-len(suffix)]) * mult)
            except ValueError:
                return None
    # Bare integer → bytes
    try:
        return int(value)
    except ValueError:
        return None


def _check_disk_watermark_config(
    raw_settings: Dict,
    metrics: Optional[Dict[str, List[Dict]]] = None,
    curl_fn=None,
) -> List[Finding]:
    """Disk watermark settings: absolute-byte mode, breach vs CMS, too-low / too-high %."""
    findings: List[Finding] = []
    wm_low = _get_cluster_setting(raw_settings, "cluster", "routing", "allocation", "disk", "watermark", "low")
    wm_flood = _get_cluster_setting(raw_settings, "cluster", "routing", "allocation", "disk", "watermark", "flood_stage")
    if not wm_low:
        return findings

    # --- Branch A: absolute-byte watermarks (e.g. transient "19605mb") ---
    flood_bytes = _parse_watermark_to_bytes(wm_flood) if wm_flood else None
    low_bytes = _parse_watermark_to_bytes(wm_low)

    if low_bytes is not None:
        disk_avail_bytes_list: list = []  # [(node_name, avail_bytes)]
        if curl_fn:
            try:
                alloc_data = curl_fn("/_cat/allocation?format=json&bytes=b")
                for row in (alloc_data or []):
                    node = row.get("node", "unknown")
                    avail = int(row.get("disk.avail", 0))
                    disk_avail_bytes_list.append((node, avail))
            except Exception:
                pass

        if flood_bytes is not None and disk_avail_bytes_list:
            flood_breached = [(n, avail) for n, avail in disk_avail_bytes_list if avail < flood_bytes]
            flood_margin = [(n, avail) for n, avail in disk_avail_bytes_list
                           if avail >= flood_bytes and (avail - flood_bytes) < 500 * 1024 * 1024]

            if flood_breached:
                findings.append(Finding(
                    event_code="HealthCheck.DiskUsageHigh",
                    reason_code="Disk.WatermarkAbsoluteFloodBreached",
                    name="Free disk below absolute flood_stage (indices read-only)",
                    priority="P0",
                    category="Configuration",
                    description=(
                        f"flood_stage is an absolute value {wm_flood} (~{flood_bytes / 1024**2:.0f} MB); "
                        f"these nodes are below it — indices should be read_only_allow_delete."
                    ),
                    evidence={
                        "flood_stage_setting": wm_flood,
                        "flood_stage_bytes": flood_bytes,
                        "breached_nodes": [
                            f"{n}: free {avail / 1024**2:.0f}MB < threshold {flood_bytes / 1024**2:.0f}MB"
                            for n, avail in flood_breached
                        ],
                        "setting_layer": (
                            "transient"
                            if raw_settings.get("transient", {}).get("cluster", {}).get("routing", {}).get("allocation", {}).get("disk", {}).get("watermark")
                            else "persistent"
                        ),
                    },
                    remediation=[
                        'Reset watermarks: PUT _cluster/settings { "transient": { "cluster.routing.allocation.disk.watermark.low": null, '
                        '"cluster.routing.allocation.disk.watermark.high": null, '
                        '"cluster.routing.allocation.disk.watermark.flood_stage": null } }',
                        'Clear read-only: PUT _all/_settings { "index.blocks.read_only_allow_delete": null }',
                        "Find who set transient watermarks (scripts / runbooks / drills)",
                    ],
                ))
            elif flood_margin:
                findings.append(Finding(
                    event_code="HealthCheck.DiskUsageHigh",
                    reason_code="Disk.WatermarkAbsoluteFloodMarginLow",
                    name="Free disk margin above absolute flood_stage is tiny",
                    priority="P1",
                    category="Configuration",
                    description=(
                        f"flood_stage absolute {wm_flood} (~{flood_bytes / 1024**2:.0f} MB); "
                        f"these nodes are barely above it — read-only may return quickly."
                    ),
                    evidence={
                        "flood_stage_setting": wm_flood,
                        "at_risk_nodes": [
                            f"{n}: free {avail / 1024**2:.0f}MB, margin {(avail - flood_bytes) / 1024**2:.0f}MB"
                            for n, avail in flood_margin
                        ],
                    },
                    remediation=[
                        "GET _cluster/settings?include_defaults=true&filter_path=**.watermark",
                        'If mis-set: PUT _cluster/settings { "transient": { "cluster.routing.allocation.disk.watermark.low": null, '
                        '"cluster.routing.allocation.disk.watermark.high": null, '
                        '"cluster.routing.allocation.disk.watermark.flood_stage": null } }',
                    ],
                ))

        is_transient = bool(raw_settings.get("transient", {}).get("cluster", {}).get("routing", {}).get("allocation", {}).get("disk", {}).get("watermark"))
        findings.append(Finding(
            event_code="HealthCheck.ConfigurationRisk",
            reason_code="Disk.WatermarkAbsoluteValue",
            name="Disk watermarks use absolute bytes (non-default)",
            priority="P1",
            category="Configuration",
            description=(
                f"Disk watermarks are absolute bytes (low={wm_low}, flood_stage={wm_flood or 'not set'}), "
                f"not percentage mode. Absolute values do not scale when disks grow and are easy to misconfigure."
            ),
            evidence={
                "low": wm_low,
                "flood_stage": wm_flood or "n/a",
                "setting_layer": "transient" if is_transient else "persistent_or_defaults",
                "risk": "Does not auto-adjust after disk expansion; can block writes while disk looks healthy",
            },
            remediation=[
                'Revert to percentage defaults: PUT _cluster/settings { "transient": { "cluster.routing.allocation.disk.watermark.low": null, '
                '"cluster.routing.allocation.disk.watermark.high": null, '
                '"cluster.routing.allocation.disk.watermark.flood_stage": null } }',
                "Trace the source of absolute-byte watermarks (scripts / ops / fault injection)",
            ],
        ))
        return findings

    # --- Branch B: percentage watermarks ---
    if "%" not in wm_low:
        return findings
    try:
        pct = float(wm_low.rstrip("%"))
    except ValueError:
        return findings

    if metrics:
        disk_summary = _summarize(metrics.get("NodeDiskUtilization", []), "NodeDiskUtilization")
        breached = [(node, stat["max"]) for node, stat in disk_summary.items() if stat["max"] > pct]
        if breached:
            findings.append(Finding(
                event_code="HealthCheck.DiskUsageHigh",
                reason_code="Disk.WatermarkBreached",
                name="Disk usage above configured watermark.low",
                priority="P1",
                category="Configuration",
                description=(
                    f"cluster.routing.allocation.disk.watermark.low = {wm_low}, "
                    f"but node disk utilization max exceeds it — relocations should be active or imminent."
                ),
                evidence={
                    "configured_watermark_low": wm_low,
                    "breached_nodes_max_pct": [f"{n}  {v:.1f}%" for n, v in breached],
                },
                remediation=[
                    "Free disk: delete old indices/snapshots or expand capacity",
                    "GET _cat/shards?v                       # relocations in flight?",
                    "GET _cluster/settings",
                    'If low was mis-tuned: PUT _cluster/settings { "persistent": { "cluster.routing.allocation.disk.watermark.low": "85%" } }',
                ],
            ))

    if pct < 5.0:
        findings.append(Finding(
            event_code="HealthCheck.DiskUsageHigh",
            reason_code="Disk.WatermarkConfigLow",
            name="Disk watermark.low extremely low (write-block risk)",
            priority="P1",
            category="Configuration",
            description=(
                f"cluster.routing.allocation.disk.watermark.low = {wm_low}, far below a sane floor (~5%). "
                f"Normal ingest will cross it quickly and hit flood-stage write blocks."
            ),
            evidence={
                "configured_low": wm_low,
                "recommended_low": "85% (Elasticsearch default)",
                "risk": "Tiny headroom before read-only / flood-stage",
            },
            remediation=[
                'PUT _cluster/settings { "persistent": { "cluster.routing.allocation.disk.watermark.low": "85%", '
                '"cluster.routing.allocation.disk.watermark.high": "90%", '
                '"cluster.routing.allocation.disk.watermark.flood_stage": "95%" } }',
                'If writes blocked: PUT index_name/_settings { "index.blocks.read_only_allow_delete": null }',
            ],
        ))

    if pct > 90.0:
        findings.append(Finding(
            event_code="HealthCheck.DiskUsageHigh",
            reason_code="Disk.WatermarkConfigHigh",
            name="Disk watermark.low too high (relocations start late)",
            priority="P2",
            category="Configuration",
            description=(
                f"cluster.routing.allocation.disk.watermark.low = {wm_low}, above the ~85% recommendation. "
                f"Shards relocate only at very high utilization — little time to react."
            ),
            evidence={
                "configured_low": wm_low,
                "recommended_low": "85% (Elasticsearch default)",
                "risk": "With high=95%, only ~5% between low and high triggers",
            },
            remediation=[
                'PUT _cluster/settings { "persistent": { "cluster.routing.allocation.disk.watermark.low": "85%" } }',
                "Also review watermark.high (~90%) and flood_stage (~95%)",
            ],
        ))
    return findings



def _check_index_readonly_blocks(curl_fn) -> List[Finding]:
    """Detect indices blocked with read_only_allow_delete."""
    findings: List[Finding] = []
    try:
        settings_raw = curl_fn("/_all/_settings?filter_path=*.settings.index.blocks")
        if not settings_raw:
            return findings
        readonly_indices = []
        for idx_name, idx_settings in settings_raw.items():
            blocks = idx_settings.get("settings", {}).get("index", {}).get("blocks", {})
            if str(blocks.get("read_only_allow_delete", "")).lower() == "true":
                readonly_indices.append(idx_name)
        if readonly_indices:
            biz_indices = [i for i in readonly_indices if not i.startswith(".")]
            sys_indices = [i for i in readonly_indices if i.startswith(".")]
            findings.append(Finding(
                event_code="HealthCheck.DiskUsageHigh",
                reason_code="Disk.IndexReadOnly",
                name="Indices read-only (read_only_allow_delete)",
                priority="P0",
                category="Configuration",
                description=(
                    f"{len(readonly_indices)} index(es) have read_only_allow_delete; writes are rejected. "
                    f"Usually from disk flood_stage; on ES 7.x blocks do not auto-clear after disk recovers."
                ),
                evidence={
                    "readonly_index_count": len(readonly_indices),
                    "business_indices_sample": biz_indices[:10] if biz_indices else "(none)",
                    "system_indices_sample": sys_indices[:10] if sys_indices else "(none)",
                },
                remediation=[
                    'PUT _all/_settings { "index.blocks.read_only_allow_delete": null }',
                    "GET _cat/allocation?v                    # confirm free disk",
                    "GET _cluster/settings?include_defaults=true&filter_path=**.watermark",
                    "On ES 7.x you must clear read-only manually after fixing disk",
                ],
            ))
    except Exception as e:
        print(f"⚠️  [ES config check] Index read-only block check failed: {e}", file=__import__('sys').stderr)
    return findings


def _check_zero_replicas(curl_fn) -> List[Finding]:
    """Detect business indices with number_of_replicas=0."""
    findings: List[Finding] = []
    try:
        indices_raw = curl_fn("/_cat/indices?h=index,rep&format=json")
        zero_rep = [
            i["index"] for i in (indices_raw or [])
            if str(i.get("rep", "1")) == "0" and not i.get("index", "").startswith(".")
        ]
        if zero_rep:
            findings.append(Finding(
                event_code="HealthCheck.ClusterUnhealthy",
                reason_code="Index.ZeroReplicas",
                name="Business indices have zero replicas",
                priority="P2",
                category="Configuration",
                description=(
                    f"{len(zero_rep)} non-system index(es) have number_of_replicas=0; "
                    f"a single node loss makes that index unavailable."
                ),
                evidence={"zero_replica_index_count": len(zero_rep), "sample_indices": zero_rep[:5]},
                remediation=[
                    'PUT /index_name/_settings { "number_of_replicas": 1 }',
                    "Repeat per index (or use index patterns carefully)",
                    "Ignore if intentionally cost-optimized",
                ],
            ))
    except Exception as e:
        print(f"⚠️  [ES config check] Failed to read index replica settings: {e}", file=sys.stderr)
    return findings


def _check_thread_pool_rejected(curl_fn) -> List[Finding]:
    """Detect thread_pool rejected counters > 0."""
    findings: List[Finding] = []
    _MONITORED_POOLS = {
        "search": ("ThreadPool.SearchRejected", "search"),
        "write": ("ThreadPool.WriteRejected", "write"),
        "bulk": ("ThreadPool.WriteRejected", "bulk"),
    }
    try:
        raw_tp = curl_fn("/_nodes/stats/thread_pool")
        nodes_tp = raw_tp.get("nodes", {})
        pool_rejected: Dict[str, Dict[str, int]] = {}
        pool_completed: Dict[str, Dict[str, int]] = {}
        for _nid, _ninfo in nodes_tp.items():
            _nname = _ninfo.get("name", _nid)
            for _pool, (_rcode, _label) in _MONITORED_POOLS.items():
                _tp = _ninfo.get("thread_pool", {}).get(_pool, {})
                _rej = _tp.get("rejected", 0)
                _comp = _tp.get("completed", 0)
                if _rej > 0:
                    pool_rejected.setdefault(_pool, {})[_nname] = _rej
                    pool_completed.setdefault(_pool, {})[_nname] = _comp

        merged: Dict[str, Dict] = {}
        for _pool, _by_node in pool_rejected.items():
            _rcode, _label = _MONITORED_POOLS[_pool]
            entry = merged.setdefault(
                _rcode,
                {"label": _label, "by_node": {}, "total": 0, "completed_by_node": {}, "completed_total": 0},
            )
            for _n, _c in _by_node.items():
                entry["by_node"][_n] = entry["by_node"].get(_n, 0) + _c
                entry["total"] += _c
                _c_done = pool_completed.get(_pool, {}).get(_n, 0)
                entry["completed_by_node"][_n] = entry["completed_by_node"].get(_n, 0) + _c_done
                entry["completed_total"] += _c_done

        for _rcode, _info in merged.items():
            findings.append(Finding(
                event_code="HealthCheck.ThreadPoolSaturation",
                reason_code=_rcode,
                name=f"{_info['label']} thread pool rejected requests",
                priority="P1",
                category="Resource metrics",
                description=(
                    f"The {_info['label']} thread pool rejected {_info['total']} request(s) "
                    f"since last restart (cumulative); backlog exceeded pool capacity. "
                    f"CMS/catalog P0 for this class usually requires sustained reject rate plus traffic "
                    f"(see health-events-catalog); use engine evidence with CMS to grade severity."
                ),
                evidence={
                    "total_rejected": _info["total"],
                    "completed_total": _info["completed_total"],
                    "completed_by_node": _info["completed_by_node"],
                    "rejections_by_node": _info["by_node"],
                    "note": "rejected counters are cumulative since node restart; correlate with logs and traffic",
                },
                remediation=[
                    f"Reduce concurrency or QPS for {_info['label']} workloads",
                    "Inspect hot threads: GET /_nodes/hot_threads",
                    "Inspect queue depth: GET /_nodes/stats/thread_pool (queue field)",
                    "Longer term: scale out or add data nodes",
                ],
            ))
    except Exception as e:
        msg = str(e)
        if "-u" in msg or "elastic:" in msg:
            msg = "(error details omitted to avoid leaking credentials in logs)"
        print(f"⚠️  [ES config check] Failed to read thread pool stats: {msg}", file=sys.stderr)
    return findings


def _check_cluster_config_optional(
    metrics: Optional[Dict[str, List[Dict]]] = None,
    instance_id: Optional[str] = None,
    *,
    connect_timeout: float = 5.0,
    read_timeout: float = 10.0,
) -> List[Finding]:
    """
    Optional Elasticsearch API checks when ES_ENDPOINT and ES_PASSWORD are set.

    Preconditions (skip all checks, return []):
      - Endpoint vs instance_id consistency (Bug-07)
      - Safe credentials (no shell metacharacters in user/password)

    Checks (REST probes, not only CMS alerts):
      1. JVMMemory.BreakerLimitConfigLow — fielddata breaker < 40%
      2. Disk.WatermarkBreached — disk % above configured watermark.low vs CMS
      3. Disk.WatermarkConfigLow — watermark.low < 5%
      4. Disk.WatermarkConfigHigh — watermark.low > 90%
      5. Index.ZeroReplicas — business indices with replicas=0
      6. ThreadPool.SearchRejected — pool rejected > 0 (P1 snapshot; catalog P0 is rate+sustained).
         ThreadPool.WriteRejected — P1 unless JVMMemory.GCTimeRatioTooHigh also fires → promoted to P0 (ingest+GC co-headline).

    Args:
        metrics: CMS bundle including NodeDiskUtilization for % watermark breach; None skips breach.
        instance_id: Instance under diagnosis for endpoint consistency.
        connect_timeout: Passed to curl ``--connect-timeout`` (TCP connect phase).
        read_timeout: Transfer budget after connect; curl ``-m`` is set to ``connect_timeout + read_timeout``
            (total operation ceiling, same spirit as prior fixed 15s default when defaults 5+10).

    Returns:
        List of Finding objects for configuration issues.
    """
    import os

    endpoint = os.environ.get("ES_ENDPOINT", "").strip()
    password  = os.environ.get("ES_PASSWORD",  "").strip()
    if not endpoint or not password:
        return []

    endpoint_check = _validate_endpoint_consistency(endpoint, instance_id)
    if endpoint_check == "skip":
        return []

    username = os.environ.get("ES_USERNAME", "elastic").strip() or "elastic"
    endpoint_url = endpoint if endpoint.startswith(("http://", "https://")) else f"http://{endpoint}"

    if not _validate_credentials_safe(username, password):
        return []

    ct = float(connect_timeout)
    rt = float(read_timeout)
    max_time = ct + rt
    subprocess_timeout = max_time + 5.0
    _ct_s, _mt_s = f"{ct:g}", f"{max_time:g}"

    def _curl_json(path: str, method: str = "GET", body: Optional[str] = None) -> Dict[str, Any]:
        """
        Call Elasticsearch HTTP API via curl argv list (not shell=True).

        Credentials are pre-validated for unsafe characters; argv list avoids shell injection.
        """
        import json as _json
        import subprocess as _subprocess

        # argv list — no shell interpretation
        cmd = [
            "curl", "-sS",
            "--connect-timeout", _ct_s,
            "-m", _mt_s,
            "-u", f"{username}:{password}",
            "-X", method.upper(),
            f"{endpoint_url}{path}",
        ]
        if body is not None:
            cmd += ["-H", "Content-Type: application/json", "-d", body]
        try:
            proc = _subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=subprocess_timeout
            )
        except _subprocess.TimeoutExpired:
            # Do not propagate TimeoutExpired — str(e) includes argv and leaks -u credentials.
            raise RuntimeError(
                f"request timed out (curl budget connect+read={max_time}s, subprocess cap={subprocess_timeout}s)"
            ) from None
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "").strip())
        txt = (proc.stdout or "").strip()
        if not txt:
            return {}
        return _json.loads(txt)

    cluster_status: Optional[str] = None  # green/yellow/red
    thread_pool_has_rejected = False  # reserved for future use

    try:
        health_resp = _curl_json("/_cluster/health")
        cluster_status = health_resp.get("status", "").lower()
    except Exception as e:
        msg = str(e)
        if "-u" in msg or "elastic:" in msg:
            msg = "(request failed; details omitted to avoid leaking credentials in logs)"
        print(
            f"⚠️  [ES config check] Cannot reach Elasticsearch at {endpoint_url}: {msg}\n"
            f"   Skipping optional config checks (circuit breakers / watermarks / zero-replica).",
            file=sys.stderr,
        )
        return []

    findings: List[Finding] = []

    try:
        raw_settings = _curl_json("/_cluster/settings?include_defaults=true")
        findings.extend(_check_fielddata_breaker(raw_settings))
        findings.extend(_check_disk_watermark_config(raw_settings, metrics, curl_fn=_curl_json))
    except Exception as e:
        print(f"⚠️  [ES config check] Failed to read circuit breaker / watermark settings: {e}", file=sys.stderr)

    findings.extend(_check_zero_replicas(_curl_json))

    findings.extend(_check_index_readonly_blocks(_curl_json))

    findings.extend(_check_thread_pool_rejected(_curl_json))

    return findings


# ---------------------------------------------------------------------------
# Rule engine — merge & order
# ---------------------------------------------------------------------------

def _promote_write_rejected_if_old_gc_wallclock_p0(findings: List[Finding]) -> None:
    """
    When Old GC wall-clock share fires as P0 (JVMMemory.GCTimeRatioTooHigh), promote
    engine ThreadPool.WriteRejected from P1 → P0 so severity bands can match ingest+GC
    dual-P0 narratives. Co-occurrence is not causation — confirm with hot_threads / _tasks.
    """
    codes = {f.reason_code for f in findings}
    if "JVMMemory.GCTimeRatioTooHigh" not in codes:
        return
    extra = (
        " Co-occurs with JVMMemory.GCTimeRatioTooHigh (Old GC wall-clock share, P0): "
        "use dual P0 headlines or chain write/bulk overload → merges / heap → Old GC → CPU spikes — "
        "not a GC-tuning-only narrative. "
        "Co-occurrence does not prove ingest caused GC — confirm with hot_threads / _tasks."
    )
    for i, f in enumerate(findings):
        if f.reason_code != "ThreadPool.WriteRejected" or f.priority != "P1":
            continue
        findings[i] = Finding(
            event_code=f.event_code,
            reason_code=f.reason_code,
            name=f.name,
            priority="P0",
            category=f.category,
            description=f.description + extra,
            evidence=f.evidence,
            remediation=f.remediation,
        )


def _finding_sort_key(f: Finding) -> tuple:
    """Priority first; within the same priority, thread-pool saturation before JVM memory (write/search narrative before GC-only)."""
    pri = {"P0": 0, "P1": 1, "P2": 2}.get(f.priority, 9)
    if f.reason_code in ("ThreadPool.WriteRejected", "ThreadPool.SearchRejected"):
        band = 0
    elif f.reason_code.startswith("JVMMemory."):
        band = 1
    else:
        band = 2
    return (pri, band, f.reason_code)


def _apply_rules(
    status_info: Dict,
    metrics: Dict[str, List[Dict]],
    events: List[Dict],
    logs: List[Dict],
    instance_id: Optional[str] = None,
    *,
    es_curl_connect_timeout: float = 5.0,
    es_curl_read_timeout: float = 10.0,
) -> List[Finding]:
    findings: List[Finding] = []
    findings += _check_instance_status(status_info)
    findings += _check_cluster_health(metrics)
    findings += _check_cpu(metrics)
    findings += _check_memory(metrics)
    findings += _check_disk(metrics)
    findings += _check_resource_imbalance(metrics)
    findings += _check_events(events)
    findings += _check_logs(logs)
    findings += _check_cluster_config_optional(
        metrics,
        instance_id=instance_id,
        connect_timeout=es_curl_connect_timeout,
        read_timeout=es_curl_read_timeout,
    )

    seen: set = set()
    deduped = []
    for f in findings:
        if f.reason_code not in seen:
            seen.add(f.reason_code)
            deduped.append(f)

    _promote_write_rejected_if_old_gc_wallclock_p0(deduped)

    deduped.sort(key=_finding_sort_key)
    return deduped


def _must_engine_footer_lines(findings: List[Finding]) -> List[str]:
    """
    Deduped engine REST paths for SKILL.md section 5 (MUST table) rows implied by findings.
    Does not replace running curl — reminds the operator/agent after environment reachability checks.
    """
    codes = {f.reason_code for f in findings}
    out: List[str] = []

    def add(path: str) -> None:
        if path not in out:
            out.append(path)

    if codes & {"Cluster.StatusRed", "Cluster.StatusYellow"}:
        add("POST /_cluster/allocation/explain  {}")
        add("GET /_cat/shards?v&h=index,shard,prirep,state,node,unassigned.reason")

    if codes & {"ThreadPool.SearchRejected", "ThreadPool.WriteRejected"}:
        add("GET /_nodes/hot_threads?threads=3")

    if codes & {"CPU.PersistUsageHigh", "CPU.PeakUsageHigh"}:
        add("GET /_nodes/hot_threads?threads=3")
        add("GET /_tasks?detailed=true&actions=*search*")

    if codes & {
        "JVMMemory.OldGenUsageCritical",
        "JVMMemory.OldGenUsageHigh",
        "JVMMemory.GCTimeRatioTooHigh",
        "JVMMemory.GCRateTooHigh",
        "JVMMemory.OOM",
    }:
        add("GET /_nodes/stats/breaker?pretty")

    if "JVMMemory.BreakerLimitConfigLow" in codes:
        add("GET /_cluster/settings?include_defaults=true  # transient + persistent: indices.breaker.*")
        add("GET /_nodes/stats/breaker?pretty")

    if codes & {
        "Balancing.NodeCPUUnbalanced",
        "Balancing.NodeDiskUnbalanced",
        "Balancing.NodeMemoryUnbalanced",
    }:
        add("GET /_cat/shards?v&h=index,shard,prirep,state,node,docs,store")
        add("GET /_cat/allocation?v")

    if codes & {
        "Disk.IndexReadOnly",
        "Disk.WatermarkBreached",
        "Disk.WatermarkAbsoluteFloodBreached",
        "Disk.WatermarkAbsoluteFloodMarginLow",
        "Disk.WatermarkAbsoluteValue",
    }:
        add("GET /_cluster/settings?include_defaults=true&filter_path=**.watermark")
        add("GET /_all/_settings?filter_path=*.settings.index.blocks")

    return out


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _print_report(
    instance_id: str,
    status_info: Dict,
    findings: List[Finding],
    metrics: Dict[str, List[Dict]],
    begin_ms: int,
    end_ms: int,
):
    W = 82
    print(f"\n{'═' * W}")
    print(f"  Elasticsearch instance health report")
    print(f"{'═' * W}")
    print(f"  Instance ID     : {instance_id}")
    if status_info and "_error" not in status_info:
        status = status_info.get("status", "-")
        from_v = {
            "active":     "active (running)",
            "activating": "activating (change in progress)",
            "inactive":   "inactive (frozen)",
            "invalid":    "invalid (unavailable)",
        }
        print(f"  Instance name   : {status_info.get('name', '-')}")
        print(f"  Control status  : {from_v.get(status, status)}")
        print(f"  ES version      : {status_info.get('es_version', '-')}")
        print(f"  Node count      : {status_info.get('node_count', '-')}")
        print(f"  Last updated    : {status_info.get('updated_at', '-')}")
    print(f"  Analysis window : {ms_to_str(begin_ms)} ~ {ms_to_str(end_ms)}")
    print(f"  Report time     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ── Summary ──
    print(f"\n{'─' * W}")
    if not findings:
        print(f"  ✅ No findings — instance appears healthy.")
    else:
        p0 = [f for f in findings if f.priority == "P0"]
        p1 = [f for f in findings if f.priority == "P1"]
        p2 = [f for f in findings if f.priority == "P2"]
        print(f"  📊 {len(findings)} finding(s):  "
              f"🔴 P0×{len(p0)}  🟡 P1×{len(p1)}  🔵 P2×{len(p2)}")

    # ── Findings ──
    for i, f in enumerate(findings, 1):
        icon = PRIORITY_ICON.get(f.priority, "⚪")
        print(f"\n{'─' * W}")
        print(f"  [{i}] {icon} {f.priority} | {f.category} | {f.name}")
        print(f"      Event code  : {f.event_code}")
        print(f"      Reason code : {f.reason_code}")
        print(f"      Description : {f.description}")

        if f.evidence:
            print(f"      Evidence    :")
            for k, v in f.evidence.items():
                if isinstance(v, list):
                    for item in v:
                        print(f"        - {item}")
                else:
                    print(f"        {k}: {v}")


        if f.remediation:
            print(f"      Remediation :")
            for r in f.remediation:
                print(f"        • {r}")

    must_paths = _must_engine_footer_lines(findings)
    if must_paths:
        print(f"\n{'─' * W}")
        print(
            "  Engine API checklist (SKILL.md sections 5–7); run after ES endpoint is reachable:"
        )
        for p in must_paths:
            print(f"    • {p}")
        print(f"{'─' * W}")

    # Read-heavy path: do not let GC/CPU findings imply search pool was ruled out.
    # Skip when write-path rejection is present — bulk/write-primary diagnosis should follow
    # sop-write-performance §2, not a search-pool headline.
    # See references/sop-query-thread-pool.md (Report narrative: search pool vs GC / CPU headlines).
    rc = {f.reason_code for f in findings}
    if (
        "ThreadPool.SearchRejected" not in rc
        and "ThreadPool.WriteRejected" not in rc
        and (
            "JVMMemory.GCTimeRatioTooHigh" in rc
            or "JVMMemory.GCRateTooHigh" in rc
            or "CPU.PeakUsageHigh" in rc
            or "CPU.PersistUsageHigh" in rc
        )
    ):
        print(f"\n{'─' * W}")
        print("  Narrative note (read-heavy / search-pool overload):")
        print("    ThreadPool.SearchRejected was not in this run's findings. If query load may")
        print("    exceed search pool capacity, verify GET /_nodes/stats/thread_pool")
        print("    (search.rejected / queue) on a stable path; GC/CPU may be co-stress.")
        print("    See references/sop-query-thread-pool.md (Report narrative: search pool vs GC / CPU headlines).")
        print(f"{'─' * W}")

    # ── Health grade ──
    print(f"\n{'─' * W}")
    grade, grade_icon, grade_desc = _compute_security_score(findings)
    print(f"  Health grade    {grade_icon} {grade} — {grade_desc}")
    print(f"{'─' * W}")

    # ── Metric summary ──
    print(f"\n{'═' * W}")
    print(f"  Key metrics (avg / max / min in window)")
    print(f"{'─' * W}")

    DISPLAY_METRICS = [
        ("ClusterStatus",                "Cluster health (CMS)      "),
        ("ClusterDisconnectedNodeCount", "Disconnected nodes      "),
        ("NodeCPUUtilization",           "Node CPU (%)            "),
        ("NodeHeapMemoryUtilization",    "Node heap (%)           "),
        ("NodeDiskUtilization",          "Node disk (%)           "),
        ("NodeStatsDataDiskUtil",        "Node disk IO util (%)   "),
        ("NodeLoad_1m",                  "Node load_1m            "),
        ("JVMGCOldCollectionCount",      "Old GC count            "),
        ("JVMGCOldCollectionDuration",   "Old GC duration (ms)    "),
    ]

    STATUS_MAP = {0: "Green", 1: "Yellow", 2: "Red"}

    for metric_name, label in DISPLAY_METRICS:
        dps = metrics.get(metric_name, [])
        if not dps:
            continue
        summary = _summarize(dps, metric_name)
        print(f"\n  {label}")
        for node, stat in summary.items():
            avg_v = stat["avg"]
            if metric_name == "ClusterStatus":
                val_str = f"avg={STATUS_MAP.get(int(round(avg_v)), str(int(round(avg_v))))}  max={STATUS_MAP.get(int(round(stat['max'])), str(int(round(stat['max']))))}"
            else:
                val_str = f"avg={avg_v:.2f}  max={stat['max']:.2f}  min={stat['min']:.2f}"
            print(f"    {node:<50} {val_str}")

    print(f"\n{'═' * W}")
    print(f"  Check complete")
    print(f"{'═' * W}\n")


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def check(
    instance_id: str,
    region_id: str,
    window_min: int = 60,
    profile: Optional[str] = None,
    data_source: str = "auto",
    input_bundle: Optional[Dict[str, Any]] = None,
    *,
    connect_timeout: float = 5.0,
    read_timeout: float = 10.0,
):
    end_ms   = now_ms()
    begin_ms = ago_ms(window_min)

    period = _cms_period_for_window(window_min)

    print(f"\n🔍 Health check: {instance_id} (region: {region_id})")
    print(f"   Window: {ms_to_str(begin_ms)} ~ {ms_to_str(end_ms)} (last {window_min} minutes)")
    print(f"   CMS period: {period}s ({int(period)//60} minute(s) bucket)")
    print(f"   Data source: {data_source}")
    if profile:
        print(f"   CLI profile: {profile}")
    print(f"   Collecting status / metrics / events / logs...\n")

    bundle = input_bundle or {}
    injected_status = bundle.get("status_info")
    injected_metrics = bundle.get("metrics")
    injected_events = bundle.get("events")
    injected_logs = bundle.get("logs")

    use_input_only = data_source == "input"
    use_cli_only = data_source == "cli"

    if isinstance(injected_status, dict) and not use_cli_only:
        status_info = injected_status
    elif use_input_only:
        status_info = {}
    else:
        status_info = fetch_instance_status_info(instance_id, region_id, profile=profile)

    if isinstance(injected_metrics, dict) and not use_cli_only:
        metrics = injected_metrics
    elif use_input_only:
        metrics = {}
    else:
        metrics = fetch_metrics_batch(
            instance_id, region_id, _DIAG_METRICS, begin_ms, end_ms, period, profile=profile
        )

    if isinstance(injected_events, list) and not use_cli_only:
        events = injected_events
    elif use_input_only:
        events = []
    else:
        events = fetch_events(instance_id, region_id, begin_ms, end_ms, profile=profile)

    if isinstance(injected_logs, list) and not use_cli_only:
        logs = injected_logs
    elif use_input_only:
        logs = []
    else:
        logs = _fetch_error_logs(instance_id, region_id, begin_ms, end_ms, profile=profile)

    if data_source != "input":
        _check_metrics_sparse(metrics, window_min, period)

    findings = _apply_rules(
        status_info,
        metrics,
        events,
        logs,
        instance_id=instance_id,
        es_curl_connect_timeout=connect_timeout,
        es_curl_read_timeout=read_timeout,
    )
    _print_report(instance_id, status_info, findings, metrics, begin_ms, end_ms)


def main():
    parser = argparse.ArgumentParser(
        description="Alibaba Cloud Elasticsearch instance health check (rules baseline 20260318).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Coverage (event / reason codes):

  Control plane   ManagementPlane.ActivatingStuck   Long-running activating
                  ManagementPlane.EventStuck        System event stuck Executing
                  ManagementPlane.InstanceInactive  Instance frozen
                  ManagementPlane.InstanceInvalid   Instance invalid

  Cluster         HealthCheck.ClusterUnhealthy
                    Cluster.StatusRed             Cluster Red (P0)
                    Cluster.StatusYellow          Cluster Yellow (P1)
                    Node.Disconnected             Node disconnected (P0)
                    Cluster.UnavailableShards     Primary unavailable [logs] (P0)

  CPU / load      HealthCheck.CPULoadHigh
                    CPU.PersistUsageHigh          Sustained CPU high >70% (P0) / >60% (P1)
                    CPU.PeakUsageHigh             CPU peak >95% (P0) / 80–94% (P1)
                  HealthCheck.LoadUnbalanced
                    Balancing.NodeCPUUnbalanced   CPU imbalance CV>0.3 (P1)
                    Balancing.NodeDiskUnbalanced  Disk imbalance CV>0.3 (P0/P1/P2)
                    Balancing.NodeMemoryUnbalanced Memory imbalance CV>0.3 (P1)

  JVM / GC        HealthCheck.JVMMemoryPressure
                    JVMMemory.OldGenUsageCritical Heap >85% (P0)
                    JVMMemory.OldGenUsageHigh     Heap >75% (P1)
                    JVMMemory.GCTimeRatioTooHigh  GC time ratio >10% (P0)
                    JVMMemory.GCRateTooHigh       Old GC >1/min (P1)
                    JVMMemory.OOM                 OutOfMemoryError in logs (P0)

  Disk            HealthCheck.DiskUsageHigh
                    Disk.UsageCritical            Disk >85% (P0)
                    Disk.UsageHigh                Disk >75% (P1)
                  HealthCheck.DiskIOBottleneck
                    Disk.IOPerformancePoor        Disk IO util >90% (P0)

Examples:
  python3 check_es_instance_health.py -i es-cn-xxx -r cn-hangzhou
  python3 check_es_instance_health.py -i es-cn-xxx -r cn-hangzhou --window 120
  python3 check_es_instance_health.py -i es-cn-xxx -r cn-hangzhou --profile prod
  python3 check_es_instance_health.py -i es-cn-xxx -r cn-hangzhou --connect-timeout 3 --read-timeout 10
  python3 check_es_instance_health.py -i es-cn-xxx -r cn-hangzhou --data-source input --input-json-file /tmp/diag.json

Credentials:
  Prefer `aliyun configure` profiles; pass --profile when needed.
        """,
    )
    parser.add_argument("--instance-id", "-i", required=True, help="Elasticsearch instance ID")
    parser.add_argument("--region-id", "-r", required=True, help="Region ID, e.g. cn-hangzhou")
    parser.add_argument(
        "--window", "-w", type=int, default=60,
        help=(
            "Analysis window in minutes (default 60). "
            "For window ≤30 minutes, CMS period=60s; for >30 minutes, period=300s "
            "(avoids empty CMS responses at 60s retention boundaries)."
        ),
    )
    parser.add_argument("--profile", default=None, help="Aliyun CLI profile name (default profile if omitted)")
    parser.add_argument(
        "--data-source",
        choices=["auto", "cli", "input"],
        default="auto",
        help="auto: use injected bundle first, then CLI; cli: CLI only; input: injected bundle only",
    )
    parser.add_argument("--input-json", default=None, help="Injected diagnostic JSON string")
    parser.add_argument("--input-json-file", default=None, help="Path to injected diagnostic JSON file")
    parser.add_argument(
        "--connect-timeout",
        type=float,
        default=5.0,
        metavar="SEC",
        help=(
            "Elasticsearch engine probes (optional curl to ES_*): max seconds for TCP connect "
            "(curl --connect-timeout). Default 5."
        ),
    )
    parser.add_argument(
        "--read-timeout",
        type=float,
        default=10.0,
        metavar="SEC",
        help=(
            "Elasticsearch engine probes: transfer time budget in seconds; curl -m uses "
            "connect-timeout + read-timeout (total operation ceiling). Default 10 (15s total with defaults)."
        ),
    )
    args = parser.parse_args()
    if args.connect_timeout <= 0 or args.read_timeout <= 0:
        parser.error("--connect-timeout and --read-timeout must be positive")
    input_bundle = _load_json_bundle(args.input_json, args.input_json_file)
    check(
        args.instance_id,
        args.region_id,
        args.window,
        profile=args.profile,
        data_source=args.data_source,
        input_bundle=input_bundle,
        connect_timeout=args.connect_timeout,
        read_timeout=args.read_timeout,
    )


if __name__ == "__main__":
    main()


