#!/usr/bin/env python3
"""
OpenAPI data collection via Aliyun CLI (shared by check_es_instance_health.py).

Design goals:
- Do not rely on OPENAPI_* env vars; prefer `aliyun configure` profiles.
- Preserve response shapes compatible with legacy get_es_instance_*.py scripts so rules do not regress.
"""

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


NAMESPACE = "acs_elasticsearch"

# Metric definitions required for health diagnosis (field names aligned with legacy collectors)
METRIC_DEFINITIONS: Dict[str, Dict[str, str]] = {
    "ClusterStatus": {"group_field": "clusterId", "value_field": "Value"},
    "ClusterDisconnectedNodeCount": {"group_field": "clusterId", "value_field": "Maximum"},
    "ClusterNodeCount": {"group_field": "clusterId", "value_field": "Maximum"},
    "ClusterShardCount": {"group_field": "clusterId", "value_field": "Maximum"},
    "ClusterQueryQPS": {"group_field": "clusterId", "value_field": "Average"},
    "ClusterIndexQPS": {"group_field": "clusterId", "value_field": "Average"},
    "NodeCPUUtilization": {"group_field": "nodeIP", "value_field": "Average"},
    "NodeHeapMemoryUtilization": {"group_field": "nodeIP", "value_field": "Average"},
    "NodeDiskUtilization": {"group_field": "nodeIP", "value_field": "Average"},
    "NodeFreeStorageSpace": {"group_field": "nodeIP", "value_field": "Minimum"},
    "NodeLoad_1m": {"group_field": "nodeIP", "value_field": "Average"},
    "NodeStatsDataDiskUtil": {"group_field": "nodeIP", "value_field": "Maximum"},
    "JVMGCOldCollectionCount": {"group_field": "nodeIP", "value_field": "Maximum"},
    "JVMGCOldCollectionDuration": {"group_field": "nodeIP", "value_field": "Maximum"},
}


def _run_aliyun_json(
    product: str,
    action: str,
    params: Dict[str, Any],
    region_id: Optional[str] = None,
    profile: Optional[str] = None,
    timeout_sec: int = 30,
) -> Dict[str, Any]:
    """
    Invoke Aliyun CLI and parse JSON.

    Raises RuntimeError on failure; callers may degrade.

    Security: subprocess.run uses argv list mode (no shell=True). Arguments are passed
    as discrete list elements and are not interpreted by a shell. Values are validated
    to reject characters that could be abused for injection.
    """
    env = os.environ.copy()
    if not env.get("ALIBABA_CLOUD_USER_AGENT"):
        env["ALIBABA_CLOUD_USER_AGENT"] = "AlibabaCloud-Agent-Skills"

    _DANGEROUS_CHARS = set('`$()|;&<>\n\r')
    _JSON_LITERAL_PARAM_KEYS = frozenset({"Dimensions"})

    def _is_safe(val: str) -> bool:
        return not any(c in _DANGEROUS_CHARS for c in str(val))

    for k, v in params.items():
        if v is None:
            continue
        if k in _JSON_LITERAL_PARAM_KEYS:
            continue
        if not _is_safe(str(v)):
            raise RuntimeError(
                f"aliyun {product} {action}: parameter {k!r} contains unsafe characters; refused"
            )

    cmd: List[str] = ["aliyun"]
    if profile:
        if not _is_safe(profile):
            raise RuntimeError("profile name contains unsafe characters")
        cmd += ["--profile", profile]
    cmd += [product, action]
    if region_id:
        if not _is_safe(region_id):
            raise RuntimeError("region_id contains unsafe characters")
        cmd += ["--region", region_id]

    for k, v in params.items():
        if v is None:
            continue
        cmd += [f"--{k}", str(v)]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_sec,
        env=env,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(f"aliyun {product} {action} failed: {stderr or proc.stdout.strip()}")
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"aliyun {product} {action} returned non-JSON: {e}")


def normalize_datapoints(datapoints: List[Dict], metric_def: Dict[str, str]) -> Dict[str, List[Dict]]:
    """Group CMS datapoints by group_field and normalize value/timestamp fields."""
    group_field = metric_def.get("group_field", "nodeIP")
    value_field = metric_def.get("value_field", "Average")

    grouped: Dict[str, List[Dict]] = {}
    for dp in datapoints or []:
        key = dp.get(group_field) or dp.get("nodeIP") or dp.get("clusterId") or "UNKNOWN"
        value = dp.get(value_field)
        if value is None:
            value = dp.get("Value", dp.get("Average", dp.get("Maximum", dp.get("Minimum"))))
        ts = dp.get("timestamp", dp.get("Timestamp", 0))
        try:
            value = float(value) if value is not None else None
        except (TypeError, ValueError):
            value = None
        grouped.setdefault(str(key), []).append({"timestamp": int(ts or 0), "value": value, "raw": dp})
    return grouped


def fetch_instance_status_info(instance_id: str, region_id: str, profile: Optional[str] = None) -> Dict[str, Any]:
    """Replacement for get_es_instance_status.fetch_instance_status_info."""
    try:
        data = _run_aliyun_json(
            "elasticsearch",
            "DescribeInstance",
            {"InstanceId": instance_id},
            region_id=region_id,
            profile=profile,
            timeout_sec=30,
        )
        r = data.get("Result", {})
        return {
            "name": r.get("description", "-"),
            "status": r.get("status", "-"),
            "es_version": r.get("esVersion", "-"),
            "updated_at": r.get("updatedAt", "") or "",
            "created_at": r.get("createdAt", "") or "",
            "node_count": r.get("nodeAmount", 0) or 0,
            "protocol": r.get("protocol", "-"),
        }
    except Exception as e:
        return {"_error": str(e)}


def fetch_instance_detail(instance_id: str, region_id: str, profile: Optional[str] = None) -> Dict[str, Any]:
    """Full DescribeInstance payload (clusterTasks, etc.) — replaces get_es_instance_detail.py."""
    return _run_aliyun_json(
        "elasticsearch",
        "DescribeInstance",
        {"InstanceId": instance_id},
        region_id=region_id,
        profile=profile,
        timeout_sec=30,
    ).get("Result", {})


def _fetch_metric_points(
    instance_id: str,
    region_id: str,
    metric_name: str,
    begin_ms: int,
    end_ms: int,
    period: str,
    profile: Optional[str] = None,
) -> List[Dict]:
    """Fetch one metric with DescribeMetricList pagination (NextToken)."""
    points: List[Dict] = []
    next_token: Optional[str] = None
    max_pages = 20

    # CMS DescribeMetricList expects millisecond timestamps
    start_ms = str(int(begin_ms))
    end_ms_str = str(int(end_ms))

    for _ in range(max_pages):
        params = {
            "Namespace": NAMESPACE,
            "MetricName": metric_name,
            "Dimensions": json.dumps([{"clusterId": instance_id}], ensure_ascii=False),
            "StartTime": start_ms,
            "EndTime": end_ms_str,
            "Period": period,
            "Length": 1440,
            "NextToken": next_token,
        }
        resp = _run_aliyun_json("cms", "DescribeMetricList", params, region_id=region_id, profile=profile)
        raw = resp.get("Datapoints", "[]")
        batch = json.loads(raw) if isinstance(raw, str) else (raw or [])
        if isinstance(batch, list):
            points.extend(batch)
        next_token = resp.get("NextToken")
        if not next_token:
            break
    return points


def fetch_metrics_batch(
    instance_id: str,
    region_id: str,
    metric_names: List[str],
    begin_ms: int,
    end_ms: int,
    period: str = "300",
    profile: Optional[str] = None,
) -> Dict[str, List[Dict]]:
    """Replacement for get_es_instance_metrics.fetch_metrics_batch."""
    result: Dict[str, List[Dict]] = {}
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(metric_names)))) as ex:
        fut_map = {
            ex.submit(
                _fetch_metric_points,
                instance_id,
                region_id,
                m,
                begin_ms,
                end_ms,
                period,
                profile,
            ): m
            for m in metric_names
        }
        for fut in as_completed(fut_map):
            m = fut_map[fut]
            try:
                result[m] = fut.result()
            except Exception:
                result[m] = []
    return result


def fetch_events(
    instance_id: str,
    region_id: str,
    begin_ms: int,
    end_ms: int,
    profile: Optional[str] = None,
) -> List[Dict]:
    """Replacement for get_es_instance_events.fetch_events — list of normalized dicts."""
    events: List[Dict] = []
    page = 1
    page_size = 100
    start_ms = str(int(begin_ms))
    end_ms_str = str(int(end_ms))

    while True:
        resp = _run_aliyun_json(
            "cms",
            "DescribeSystemEventAttribute",
            {
                "Product": "elasticsearch",
                "SearchKeywords": instance_id,
                "StartTime": start_ms,
                "EndTime": end_ms_str,
                "PageNumber": page,
                "PageSize": page_size,
            },
            region_id=region_id,
            profile=profile,
        )
        wrapper = (resp.get("SystemEvents") or {}).get("SystemEvent") or []
        if not wrapper:
            break

        for e in wrapper:
            content_raw = e.get("Content")
            content = {}
            if isinstance(content_raw, str):
                try:
                    content = json.loads(content_raw)
                except json.JSONDecodeError:
                    content = {}
            events.append(
                {
                    "name": e.get("Name", ""),
                    "time_ms": int(e.get("Time", 0) or 0),
                    "level": e.get("Level", ""),
                    "event_status": content.get("eventStatus", ""),
                    "reason": content.get("reasonCode", content.get("reason", "")),
                    "start_time": content.get("executeStartTime", ""),
                    "finish_time": content.get("executeFinishTime", ""),
                }
            )

        if len(wrapper) < page_size:
            break
        page += 1

    events.sort(key=lambda x: x.get("time_ms", 0), reverse=True)
    return events


def fetch_log_items(
    instance_id: str,
    region_id: str,
    log_type: str = "INSTANCELOG",
    begin_ms: Optional[int] = None,
    end_ms: Optional[int] = None,
    query: str = "*",
    size: int = 50,
    profile: Optional[str] = None,
) -> List[Dict]:
    """Replacement for get_es_instance_log.fetch_log_items."""
    now = datetime.now()
    if begin_ms is None:
        begin_ms = int((now - timedelta(minutes=10)).timestamp() * 1000)
    if end_ms is None:
        end_ms = int(now.timestamp() * 1000)

    resp = _run_aliyun_json(
        "elasticsearch",
        "ListSearchLog",
        {
            "InstanceId": instance_id,
            "type": log_type,
            "query": query or "*",
            "beginTime": int(begin_ms),
            "endTime": int(end_ms),
            "page": 1,
            "size": max(1, min(int(size), 50)),
        },
        region_id=region_id,
        profile=profile,
    )
    return resp.get("Result") or []
