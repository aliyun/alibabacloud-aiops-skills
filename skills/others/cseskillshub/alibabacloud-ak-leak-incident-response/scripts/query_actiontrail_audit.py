#!/usr/bin/env python3
"""
query_actiontrail_audit.py  (dual-backend edition)
==================================================
Query ActionTrail event logs via the LookupEvents API, routed through the
dual-backend layer in `_cli.py` (aliyun CLI preferred, V3-signed HTTPS fallback).
Supports per-service dangerous-operation audit and sub-account tracing.

AUTHENTICATION:
    Handled by the active backend (see _cli.py): aliyun CLI profile
    (~/.aliyun/config.json) or, on HTTP fallback, env AK/SK / config.json.

Usage:
    python query_actiontrail_audit.py --account <UID>
    python query_actiontrail_audit.py --account <UID> --service Ram
    python query_actiontrail_audit.py --account <UID> --source-ip <IP> --days 1
    python query_actiontrail_audit.py --account <UID> --ak <AK> --days 1
    python query_actiontrail_audit.py --account <UID> --user oss --days 30
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

DANGEROUS_SERVICES = _constants.DANGEROUS_SERVICES
HIGH_RISK_EVENTS = _constants.HIGH_RISK_EVENTS


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Query ActionTrail events via dual-backend LookupEvents")
    p.add_argument("--account", required=True, help="Alibaba Cloud UID")
    p.add_argument("--region", default="cn-shanghai", help="Alibaba Cloud region (default: cn-shanghai)")
    p.add_argument("--profile", default=None, help="aliyun CLI profile name (optional)")
    p.add_argument("--service", default=",".join(DANGEROUS_SERVICES),
                   help="Comma-separated services (ignored when --source-ip/--ak/--user is used)")
    p.add_argument("--source-ip", help="Filter events by source IP address")
    p.add_argument("--ak", help="Filter events by AccessKey ID (EventAccessKeyId)")
    p.add_argument("--user", help="Filter events by sub-account executor name (User filter). "
                   "Mandatory for Step 4a chain tracing.")
    p.add_argument("--days", type=int, default=30, help="Lookback days (max 90)")
    p.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
    p.add_argument("--output", help="Output file path (default: stdout)")
    return p.parse_args()


def classify_event(event_name: str, service: str) -> str:
    """Classify event risk level using substring matching."""
    high_risk = HIGH_RISK_EVENTS.get(service, [])
    if any(pattern in event_name for pattern in high_risk):
        return "HIGH"
    if any(kw in event_name for kw in ("Modify", "Update", "Delete", "Remove", "Stop", "Release")):
        return "MEDIUM"
    return "LOW"


def lookup_events(
    start_time: str,
    end_time: str,
    region: str = "cn-shanghai",
    profile: Optional[str] = None,
    service: Optional[str] = None,
    source_ip: Optional[str] = None,
    ak: Optional[str] = None,
    user: Optional[str] = None,
) -> list[dict]:
    """Query ActionTrail LookupEvents via the dual-backend layer with NextToken pagination.

    Filter priority (mutually exclusive, first match wins):
      1. source_ip -> SourceIpAddress
      2. ak        -> EventAccessKeyId
      3. user      -> User (only working sub-account filter)
      4. service   -> ServiceName
      5. (none)    -> no filter (ALL events)
    """
    params: dict[str, Any] = {
        "StartTime": start_time,
        "EndTime": end_time,
        "MaxResults": 50,
    }
    if source_ip:
        params["LookupAttribute.1.Key"] = "SourceIpAddress"
        params["LookupAttribute.1.Value"] = source_ip
    elif ak:
        params["LookupAttribute.1.Key"] = "EventAccessKeyId"
        params["LookupAttribute.1.Value"] = ak
    elif user:
        params["LookupAttribute.1.Key"] = "User"
        params["LookupAttribute.1.Value"] = user
    elif service:
        params["LookupAttribute.1.Key"] = "ServiceName"
        params["LookupAttribute.1.Value"] = service

    raw = _cli.paginate_next_token(
        "actiontrail", "LookupEvents", params,
        region=region, profile=profile, items_key="Events",
    )
    return [_event_to_dict(e) for e in raw]


def _event_to_dict(evt: Any) -> dict:
    """Normalize an ActionTrail event (CLI returns events as dicts)."""
    if not isinstance(evt, dict):
        evt = {}
    user_identity = evt.get("userIdentity") or {}
    if not isinstance(user_identity, dict):
        user_identity = {}
    return {
        "eventId": evt.get("eventId", "N/A"),
        "eventName": evt.get("eventName", "Unknown"),
        "eventTime": evt.get("eventTime", "N/A"),
        "eventSource": evt.get("eventSource", ""),
        "sourceIpAddress": evt.get("sourceIpAddress", "N/A"),
        "userAgent": evt.get("userAgent", "N/A"),
        "userIdentity": user_identity,
        "userName": user_identity.get("userName") or "N/A",
        "accessKeyId": evt.get("accessKeyId") or user_identity.get("accessKeyId", "N/A"),
        "requestParameters": evt.get("requestParameters") or {},
        "responseElements": evt.get("responseElements") or {},
        "errorCode": evt.get("errorCode") or "",
        "errorMessage": evt.get("errorMessage") or "",
        "serviceName": evt.get("serviceName", ""),
        "eventRW": evt.get("eventRW", ""),
    }


def process_events(raw_events: list[dict], service: str) -> list[dict]:
    """Process raw events into structured records with risk classification."""
    processed = []
    for evt in raw_events:
        event_name = evt.get("eventName", "Unknown")
        risk = classify_event(event_name, service)
        error_code = evt.get("errorCode", "")
        error_message = evt.get("errorMessage", "")
        success = not bool(error_code)
        processed.append({
            "eventId": evt.get("eventId", "N/A"),
            "eventName": event_name,
            "eventTime": evt.get("eventTime", "N/A"),
            "eventSource": evt.get("eventSource", ""),
            "sourceIPAddress": evt.get("sourceIpAddress", "N/A"),
            "userAgent": evt.get("userAgent", "N/A"),
            "userName": evt.get("userName", "N/A"),
            "accessKeyId": evt.get("accessKeyId", "N/A"),
            "requestParameters": evt.get("requestParameters", {}),
            "responseElements": evt.get("responseElements", {}),
            "riskLevel": risk,
            "service": service,
            "success": success,
            "errorCode": error_code,
            "errorMessage": error_message,
        })
    return processed


def main() -> int:
    args = parse_args()
    _cli.check_cli_available()

    region, profile = args.region, args.profile
    days = min(max(args.days, 1), 90)
    start_time, end_time = _cli.get_time_window(days)

    results = []
    if args.source_ip:
        processed = process_events(
            lookup_events(start_time, end_time, region, profile, source_ip=args.source_ip), "SourceIp")
        results.append(_summarize(f"SourceIp:{args.source_ip}", processed))
    elif args.ak:
        processed = process_events(
            lookup_events(start_time, end_time, region, profile, ak=args.ak), "AK")
        results.append(_summarize(f"AK:{args.ak}", processed))
    elif args.user:
        processed = process_events(
            lookup_events(start_time, end_time, region, profile, user=args.user), "User")
        results.append(_summarize(f"User:{args.user}", processed))
    else:
        services = [s.strip() for s in args.service.split(",") if s.strip()]
        for svc in services:
            try:
                processed = process_events(
                    lookup_events(start_time, end_time, region, profile, service=svc), svc)
                results.append(_summarize(svc, processed))
            except _cli.CliError as e:
                results.append({"service": svc, "error": str(e),
                                "event_count": 0, "high_risk_count": 0, "events": []})

    total_events = sum(r["event_count"] for r in results)
    total_high = sum(r["high_risk_count"] for r in results)
    total_failed = sum(1 for r in results for e in r["events"] if not e.get("success", True))

    if args.format == "json":
        output = json.dumps({
            "account": args.account,
            "time_window": {"start": start_time, "end": end_time},
            "total_events": total_events,
            "total_high_risk": total_high,
            "total_failed": total_failed,
            "results": results,
        }, indent=2, ensure_ascii=False)
    else:
        lines = [
            "ActionTrail Audit Results",
            f"Account: {args.account}",
            f"Time Window: {start_time} ~ {end_time}",
        ]
        if args.source_ip:
            lines.append(f"Source IP: {args.source_ip}")
        elif args.ak:
            lines.append(f"AK Filter: {args.ak}")
        elif args.user:
            lines.append(f"User Filter: {args.user}")
        else:
            lines.append(f"Services Queried: {len([s for s in args.service.split(',') if s.strip()])}")
        lines.extend([
            f"Total Events: {total_events}",
            f"High Risk Events: {total_high}",
            f"Failed Events: {total_failed} (AK disabled/permission denied/etc.)",
            "",
        ])
        for r in results:
            lines.append(f"[{r['service']}] {r['event_count']} events ({r['high_risk_count']} high-risk)")
            if "error" in r:
                lines.append(f"  ERROR: {r['error']}")
            for ev in r["events"][:10]:
                status = "OK" if ev.get("success", True) else f"FAIL: {ev.get('errorCode', 'FAIL')}"
                lines.append(
                    f"  {ev['eventTime']} | {ev['riskLevel']} | {ev['eventName']} | "
                    f"{ev['sourceIPAddress']} | {status}"
                )
        output = "\n".join(lines)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Saved to {args.output}")
    else:
        print(output)
    return 0


def _summarize(label: str, processed: list[dict]) -> dict:
    return {
        "service": label,
        "event_count": len(processed),
        "high_risk_count": sum(1 for e in processed if e["riskLevel"] == "HIGH"),
        "events": processed,
    }


if __name__ == "__main__":
    sys.exit(main())
