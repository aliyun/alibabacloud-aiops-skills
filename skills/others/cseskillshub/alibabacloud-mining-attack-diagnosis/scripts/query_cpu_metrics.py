#!/usr/bin/env python3
"""
query_cpu_metrics.py  (dual-backend edition)
============================================
B-enhancement: query CloudMonitor (Cms) for ECS CPU utilization to corroborate
suspected mining. High sustained CPU is a strong signal when combined with SAS
mining alerts. READ-ONLY.

Data source:
  - Cms DescribeMetricList  (Namespace=acs_ecs_dashboard, MetricName=CPUUtilization)

AUTHENTICATION: handled by the active backend (see _cli.py).

Usage:
    python query_cpu_metrics.py --instance-id i-bp1xxx,i-bp2yyy --hours 6
    python query_cpu_metrics.py --instance-id i-bp1xxx --days 1 --threshold 80
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cli
import _constants


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Query CloudMonitor CPU utilization to corroborate mining via dual-backend"
    )
    p.add_argument("--instance-id", required=True,
                   help="Comma-separated ECS instance ID(s) (e.g. i-bp1xxx)")
    p.add_argument("--hours", type=int, default=6, help="Lookback hours (default: 6)")
    p.add_argument("--days", type=int, default=0, help="Lookback days (overrides --hours if >0)")
    p.add_argument("--threshold", type=int, default=_constants.MINING_CPU_THRESHOLD,
                   help=f"CPU%% threshold for mining flag (default: {_constants.MINING_CPU_THRESHOLD})")
    p.add_argument("--region", default="cn-hangzhou", help="Alibaba Cloud region")
    p.add_argument("--profile", default=None, help="aliyun CLI profile (optional)")
    p.add_argument("--format", choices=["json", "text"], default="text")
    p.add_argument("--output", help="Output file path (default: stdout)")
    return p.parse_args()


def query_cpu(instance_id: str, hours: int, threshold: int,
              region: str, profile: Optional[str]) -> dict[str, Any]:
    """Query CPUUtilization for one instance and compute mining-signal metrics."""
    end_ms = _cli.to_millis(0)
    start_ms = _cli.to_millis(0) - hours * 3600 * 1000

    params: dict[str, Any] = {
        "Namespace": "acs_ecs_dashboard",
        "MetricName": "CPUUtilization",
        "Period": "300",  # 5-minute granularity
        "StartTime": str(start_ms),
        "EndTime": str(end_ms),
        "Dimensions": json.dumps([{"instanceId": instance_id}]),
        "Length": "1000",
    }

    all_points: list[dict] = []
    next_token: Optional[str] = None
    for _ in range(50):
        if next_token:
            params["NextToken"] = next_token
        try:
            body = _cli.call("cms", "DescribeMetricList", params, region=region, profile=profile)
        except _cli.CliError as e:
            return {"instanceId": instance_id, "error": str(e)}
        dp_raw = body.get("Datapoints", "")
        if isinstance(dp_raw, str) and dp_raw.strip():
            try:
                points = json.loads(dp_raw)
                if isinstance(points, list):
                    all_points.extend(points)
            except json.JSONDecodeError:
                pass
        next_token = body.get("NextToken")
        if not next_token:
            break

    if not all_points:
        return {"instanceId": instance_id, "datapoints": 0, "avg": 0, "max": 0,
                "threshold": threshold, "highCount": 0, "highRatio": 0,
                "sustainedHighCpu": False, "note": "no datapoints"}

    avgs = [p.get("Average", 0) or 0 for p in all_points]
    maxs = [p.get("Maximum", 0) or 0 for p in all_points]
    total = len(avgs)
    avg_cpu = sum(avgs) / total if total else 0
    max_cpu = max(maxs) if maxs else 0
    high_count = sum(1 for a in avgs if a >= threshold)
    high_ratio = high_count / total if total else 0
    sustained = high_ratio >= 0.5

    return {
        "instanceId": instance_id,
        "datapoints": total,
        "hours": hours,
        "avg": round(avg_cpu, 1),
        "max": round(max_cpu, 1),
        "threshold": threshold,
        "highCount": high_count,
        "highRatio": round(high_ratio, 3),
        "sustainedHighCpu": sustained,
    }


def format_text(results: list[dict]) -> str:
    lines = ["CloudMonitor CPU Corroboration", "=" * 60, ""]
    for r in results:
        if r.get("error"):
            lines.append(f"  {r['instanceId']}: ERROR — {r['error']}")
            continue
        flag = "YES — MINING-CONSISTENT" if r["sustainedHighCpu"] else "no"
        lines.append(
            f"  {r['instanceId']}: avg={r['avg']}% max={r['max']}% "
            f"high(>={r['threshold']}%)={r['highCount']}/{r['datapoints']} "
            f"ratio={r['highRatio']} sustained={flag}"
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    _cli.check_cli_available()

    hours = args.days * 24 if args.days > 0 else args.hours
    instance_ids = [s.strip() for s in args.instance_id.split(",") if s.strip()]
    results = [query_cpu(iid, hours, args.threshold, args.region, args.profile) for iid in instance_ids]

    if args.format == "json":
        output = json.dumps(results, indent=2, ensure_ascii=False)
    else:
        output = format_text(results)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Saved to {args.output}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
