#!/usr/bin/env python3
"""
query_intrusion_trace.py  (dual-backend edition)
================================================
B-enhancement: trace post-intrusion operations via ActionTrail LookupEvents to
understand how a miner may have been deployed or spread — command execution
(RunCommand), instance scale-out (RunInstances), credential/persistence abuse
(CreateAccessKey/CreateUser), and security-group egress opening. READ-ONLY.

Data source:
  - actiontrail LookupEvents  (2020-07-06)

Note: ActionTrail is account/AK-scoped, not per-instance. This surfaces the
account-wide high-risk operation chain within the window; correlate the source
IP / actor with the mining-affected assets from the SAS steps.

AUTHENTICATION: handled by the active backend (see _cli.py).

Usage:
    python query_intrusion_trace.py --days 7
    python query_intrusion_trace.py --days 3 --source-ip 1.2.3.4 --format json
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

HIGH_RISK_TRACE_EVENTS = set(_constants.HIGH_RISK_TRACE_EVENTS)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Trace post-intrusion operations via ActionTrail LookupEvents (dual-backend)"
    )
    p.add_argument("--days", type=int, default=7, help="Lookback days (max 90, default: 7)")
    p.add_argument("--source-ip", help="Filter events by source IP address (optional)")
    p.add_argument("--region", default="cn-hangzhou", help="Alibaba Cloud region")
    p.add_argument("--profile", default=None, help="aliyun CLI profile (optional)")
    p.add_argument("--all", action="store_true",
                   help="Return all events, not just the high-risk mining-relevant ones")
    p.add_argument("--format", choices=["json", "text"], default="text")
    p.add_argument("--output", help="Output file path (default: stdout)")
    return p.parse_args()


def _event_to_dict(evt: Any) -> dict:
    if not isinstance(evt, dict):
        return {}
    ui = evt.get("userIdentity") or {}
    if not isinstance(ui, dict):
        ui = {}
    return {
        "eventName": evt.get("eventName", "Unknown"),
        "eventTime": evt.get("eventTime", "N/A"),
        "eventSource": evt.get("eventSource", ""),
        "sourceIpAddress": evt.get("sourceIpAddress", "N/A"),
        "userAgent": evt.get("userAgent", "N/A"),
        "userName": ui.get("userName") or "N/A",
        "accessKeyId": evt.get("accessKeyId") or ui.get("accessKeyId", "N/A"),
        "errorCode": evt.get("errorCode") or "",
    }


def trace(days: int, source_ip: Optional[str], only_high_risk: bool,
          region: str, profile: Optional[str]) -> dict[str, Any]:
    days = min(max(days, 1), 90)
    start_time, end_time = _cli.get_time_window(days)
    params: dict[str, Any] = {"StartTime": start_time, "EndTime": end_time, "MaxResults": 50}
    if source_ip:
        params["LookupAttribute.1.Key"] = "SourceIpAddress"
        params["LookupAttribute.1.Value"] = source_ip
    try:
        raw = _cli.paginate_next_token(
            "actiontrail", "LookupEvents", params,
            region=region, profile=profile, items_key="Events",
        )
    except _cli.CliError as e:
        return {"error": str(e), "events": [], "total": 0, "window": {"start": start_time, "end": end_time}}

    events = [_event_to_dict(e) for e in raw]
    if only_high_risk:
        events = [e for e in events if e["eventName"] in HIGH_RISK_TRACE_EVENTS]
    events.sort(key=lambda e: e.get("eventTime", ""))
    return {
        "window": {"start": start_time, "end": end_time},
        "total": len(events),
        "successful": sum(1 for e in events if not e["errorCode"]),
        "events": events,
        "sourceIps": sorted({e["sourceIpAddress"] for e in events
                             if e["sourceIpAddress"] not in ("N/A", "", "-")}),
    }


def format_text(result: dict[str, Any]) -> str:
    lines = ["ActionTrail Post-Intrusion Operation Trace", "=" * 60, ""]
    if result.get("error"):
        lines.append(f"ERROR: {result['error']}")
        return "\n".join(lines)
    w = result["window"]
    lines.append(f"Window: {w['start']} ~ {w['end']}")
    lines.append(f"High-risk operations: {result['total']} ({result['successful']} succeeded)")
    ips = result.get("sourceIps", [])
    if ips:
        lines.append(f"Source IPs: {', '.join(ips)}")
    lines.append("")
    for e in result["events"][:50]:
        status = "OK" if not e["errorCode"] else f"FAIL:{e['errorCode']}"
        lines.append(
            f"  {e['eventTime']} | {e['eventName']} | {e['eventSource']} | "
            f"ip={e['sourceIpAddress']} | user={e['userName']} | {status}"
        )
    if not result["events"]:
        lines.append("  (no high-risk operations found in window)")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    _cli.check_cli_available()
    result = trace(args.days, args.source_ip, not args.all, args.region, args.profile)

    if args.format == "json":
        output = _cli.mask_text(json.dumps(_cli.mask_obj(result), indent=2, ensure_ascii=False))
    else:
        output = _cli.mask_text(format_text(result))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Saved to {args.output}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
