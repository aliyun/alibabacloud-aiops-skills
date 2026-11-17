#!/usr/bin/env python3
"""CloudMonitor metric access and statistics for the resource-bottleneck skill.

Two call shapes are used, both Describe/Get-style reads of the cms product:

    * DescribeMetricLast  -> the latest single reading ("is it pegged right now")
    * DescribeMetricList  -> a time series over an explicit window ("stayed high")

All aggregation happens here as pure, unit-testable functions over whatever the
API returned, so the report never depends on model arithmetic. A missing series
is surfaced as an evidence gap; it is never replaced with an assumed value.

The response envelope (a JSON-array string under ``Datapoints``) follows the
CloudMonitor contract as recorded in the tier's requirements document; the
metric NAME list lives in _constants and contains only names evidenced by the
tier's ticket corpus.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from _cli import CliError, run_cli
from _constants import (
    ACTION_DESCRIBE_METRIC_LAST,
    ACTION_DESCRIBE_METRIC_LIST,
    CMS_NAMESPACE_ECS,
    DEFAULT_PERIOD_SECONDS,
    METRIC_PAGE_SIZE,
    PRODUCT_CMS,
)


def _dimensions(instance_id: str) -> str:
    """Render the Dimensions filter the cms metric queries expect."""
    return json.dumps([{"instanceId": instance_id}], separators=(",", ":"))


def metric_window(hours: int) -> Dict[str, str]:
    """Return an explicit UTC start/end window as ISO-8601 without offset."""
    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = datetime.fromtimestamp(end.timestamp() - hours * 3600, tz=timezone.utc)
    start = start.replace(microsecond=0)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return {"StartTime": start.strftime(fmt), "EndTime": end.strftime(fmt)}


def fetch_metric_last(
    instance_id: str, metric_name: str, session_id: str,
    timeout: int, warnings: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Latest reading of one metric; failures degrade to a typed result."""
    try:
        payload = run_cli(
            PRODUCT_CMS, ACTION_DESCRIBE_METRIC_LAST,
            params={
                "Namespace": CMS_NAMESPACE_ECS,
                "MetricName": metric_name,
                "Dimensions": _dimensions(instance_id),
            },
            session_id=session_id, timeout=timeout, warnings=warnings,
        )
    except CliError as exc:
        return {"metric": metric_name, "error": str(exc), "points": [], "empty": True}
    points = parse_datapoints(payload)
    return {"metric": metric_name, "points": points, "empty": not points}


def fetch_metric_series(
    instance_id: str, metric_name: str, window: Dict[str, str], session_id: str,
    timeout: int, warnings: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Time series of one metric over ``window``; failures degrade, never guess."""
    try:
        payload = run_cli(
            PRODUCT_CMS, ACTION_DESCRIBE_METRIC_LIST,
            params={
                "Namespace": CMS_NAMESPACE_ECS,
                "MetricName": metric_name,
                "Dimensions": _dimensions(instance_id),
                "StartTime": window.get("StartTime"),
                "EndTime": window.get("EndTime"),
                "Period": DEFAULT_PERIOD_SECONDS,
                "Length": METRIC_PAGE_SIZE,
            },
            session_id=session_id, timeout=timeout, warnings=warnings,
        )
    except CliError as exc:
        return {"metric": metric_name, "error": str(exc), "stats": {}, "points": []}
    points = parse_datapoints(payload)
    return {
        "metric": metric_name,
        "stats": summarize_points(points),
        "points": points,
        "count": len(points),
    }


def parse_datapoints(payload: Any) -> List[Dict[str, Any]]:
    """Decode the Datapoints field, which is a JSON-array *string* or a list."""
    if not isinstance(payload, dict):
        return []
    raw = payload.get("Datapoints")
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        try:
            raw = json.loads(raw)
        except ValueError:
            return []
    if isinstance(raw, list):
        return [point for point in raw if isinstance(point, dict)]
    return []


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def point_value(point: Dict[str, Any]) -> Optional[float]:
    """Prefer Average, fall back to Maximum/Minimum, else nothing (never 0)."""
    for key in ("Average", "Maximum", "Minimum", "value", "Value"):
        number = _as_float(point.get(key))
        if number is not None:
            return number
    return None


def point_maximum(point: Dict[str, Any]) -> Optional[float]:
    number = _as_float(point.get("Maximum"))
    if number is None:
        number = point_value(point)
    return number


def point_timestamp_ms(point: Dict[str, Any]) -> Optional[int]:
    number = _as_float(point.get("timestamp"))
    if number is None:
        return None
    return int(number)


def summarize_points(points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Average and peak over the window with their timestamp.

    Mean and max are always reported together, in one record, because tickets
    T-46B31B3D and T-3941829E show the two calibers leading customer and
    engineer to opposite conclusions when only one is quoted.
    """
    values: List[float] = []
    maxima: List[float] = []
    peak_value: Optional[float] = None
    peak_ts: Optional[int] = None
    first_ts: Optional[int] = None
    last_ts: Optional[int] = None
    for point in points:
        value = point_value(point)
        if value is None:
            continue
        values.append(value)
        ts = point_timestamp_ms(point)
        if ts is not None:
            first_ts = ts if first_ts is None else min(first_ts, ts)
            last_ts = ts if last_ts is None else max(last_ts, ts)
        maximum = point_maximum(point)
        if maximum is not None:
            maxima.append(maximum)
            if peak_value is None or maximum > peak_value:
                peak_value = maximum
                peak_ts = ts
    if not values:
        return {}
    return {
        "count": len(values),
        "avg": round(sum(values) / len(values), 2),
        "mx": round(max(maxima) if maxima else max(values), 2),
        "peak_ts_ms": peak_ts,
        "first_ts_ms": first_ts,
        "last_ts_ms": last_ts,
    }


def iso_from_ms(millis: Optional[int]) -> str:
    """UTC rendering of a millisecond timestamp; ``not returned`` when absent."""
    if millis is None:
        return "not returned"
    try:
        return datetime.fromtimestamp(millis / 1000.0, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    except (OverflowError, OSError, ValueError):
        return "not returned"


def find_co_peaks(
    cpu_stats: Dict[str, Any],
    cpu_points: List[Dict[str, Any]],
    other_stats: Dict[str, Any],
    other_points: List[Dict[str, Any]],
    ratio: float,
) -> Optional[Dict[str, Any]]:
    """Timestamp where the CPU series and another series are both near peak.

    Used for the co-saturation detection behind rules R1 and R4 (ticket
    T-1BBB1704: CPU and disk BPS spiking in the same minute). Returns None
    when either side has no data — the absence is reported, not inferred.
    """
    if not cpu_points or not other_points:
        return None
    cpu_peak = (cpu_stats or {}).get("mx")
    other_peak = (other_stats or {}).get("mx")
    if not cpu_peak or not other_peak:
        return None
    cpu_floor = float(cpu_peak) * ratio
    other_floor = float(other_peak) * ratio
    other_high_ts = set()
    for point in other_points:
        ts = point_timestamp_ms(point)
        value = point_value(point)
        if ts is not None and value is not None and value >= other_floor:
            other_high_ts.add(ts)
    best: Optional[Dict[str, Any]] = None
    for point in cpu_points:
        ts = point_timestamp_ms(point)
        value = point_value(point)
        if ts is None or value is None or ts not in other_high_ts:
            continue
        if value >= cpu_floor:
            best = {"timestamp_ms": ts, "cpu_value": value}
            break
    return best


# --- inline boundary assertions for the pure functions (dev-time check) -------
def _self_test() -> None:
    """Boundary checks for the parsing/aggregation helpers (no network)."""
    assert parse_datapoints({"Datapoints": '[]'}) == []
    assert parse_datapoints({"Datapoints": ""}) == []
    assert parse_datapoints({"Datapoints": "not json"}) == []
    assert parse_datapoints("junk") == []
    assert parse_datapoints({"Datapoints": '[{"timestamp":1,"Average":2.5}, 3]'}) == [
        {"timestamp": 1, "Average": 2.5}
    ]
    assert point_value({"Average": 0.0}) == 0.0
    assert point_value({"Maximum": 7}) == 7.0
    assert point_value({}) is None
    assert summarize_points([]) == {}
    stats = summarize_points([
        {"timestamp": 1000, "Average": 10, "Maximum": 20},
        {"timestamp": 2000, "Average": 30, "Maximum": 40},
    ])
    assert stats["avg"] == 20.0 and stats["mx"] == 40.0 and stats["count"] == 2
    assert stats["peak_ts_ms"] == 2000
    assert iso_from_ms(None) == "not returned"
    assert iso_from_ms(0).endswith("Z")
    window = metric_window(6)
    assert window["StartTime"].endswith("Z") and window["EndTime"].endswith("Z")
    assert window["StartTime"] < window["EndTime"]
    co = find_co_peaks(
        {"mx": 100.0}, [{"timestamp": 5, "Average": 95}],
        {"mx": 50.0}, [{"timestamp": 5, "Average": 48}], 0.85,
    )
    assert co is not None and co["timestamp_ms"] == 5
    assert find_co_peaks({}, [], {"mx": 1}, [{"timestamp": 1, "Average": 1}], 0.85) is None


if __name__ == "__main__":  # pragma: no cover - dev-time check
    _self_test()
    print("cms_metrics self-test passed")
