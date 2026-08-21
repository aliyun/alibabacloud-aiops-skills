#!/usr/bin/env python3
"""
query_mining_alerts.py  (dual-backend edition)
==============================================
Step 1 of the mining-attack detection SOP: query Security Center (SAS) for
mining (cryptojacking) alerts, routed through the dual-backend layer in
`_cli.py` (aliyun CLI preferred, V3-signed HTTPS fallback; no Python SDKs).

Data source (all READ-ONLY -- this script performs no handling / write calls):
  SAS DescribeSuspEvents -- security alert events (un-aggregated)

Mining alerts are recognized by matching event name / type / description
against the mining indicator keyword set in `_constants.py`.

AUTHENTICATION:
    Handled by the active backend (see _cli.py): aliyun CLI profile
    (~/.aliyun/config.json) or, on HTTP fallback, env AK/SK / config.json.

Usage:
    python query_mining_alerts.py --account <UID>
    python query_mining_alerts.py --account <UID> --days 7 --dealed N
    python query_mining_alerts.py --source susp --format json
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
        description="Query Security Center (SAS) for mining alerts via dual-backend"
    )
    p.add_argument("--account", default=None,
                   help="Alibaba Cloud UID (optional; auto-derived via STS if omitted)")
    p.add_argument("--region", default="cn-hangzhou",
                   help="Alibaba Cloud region (default: cn-hangzhou)")
    p.add_argument("--profile", default=None, help="aliyun CLI profile name (optional)")
    p.add_argument("--days", type=int, default=30, help="Lookback days (default: 30)")
    p.add_argument("--dealed", choices=["Y", "N", "all"], default="all",
                   help="Filter by handled status: Y=handled, N=pending, all (default)")
    p.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
    p.add_argument("--output", help="Output file path (default: stdout)")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Field extraction helpers (SAS responses vary; stay defensive)
# ---------------------------------------------------------------------------

def _g(d: dict, *keys: str, default: str = "") -> str:
    """Return the first present, non-empty value among keys (case-tolerant)."""
    if not isinstance(d, dict):
        return default
    lower = {str(k).lower(): v for k, v in d.items()}
    for k in keys:
        v = lower.get(k.lower())
        if v not in (None, ""):
            return v
    return default


def _normalize_alert(raw: dict, source: str) -> dict:
    """Normalize an SAS alarm/susp record into a common shape."""
    name = _g(raw, "AlarmEventName", "AlarmEventNameDisplay", "EventName", "Name")
    etype = _g(raw, "AlarmEventType", "AlarmEventTypeDisplay", "EventType", "Type")
    desc = _g(raw, "Desc", "Description", "EventSubType")
    level = _g(raw, "Level", "AlarmLevel", "SecurityEventLevel")
    dealed = _g(raw, "Dealed", "EventStatus", default="")
    return {
        "source": source,
        "alarmEventName": name,
        "alarmEventType": etype,
        "description": desc,
        "level": level,
        "dealed": dealed,
        "lastTime": _g(raw, "LastTime", "LastTimeStamp", "GmtLast"),
        "occurrenceTime": _g(raw, "OccurrenceTime", "StartTime", "GmtOccurrenceTime"),
        "instanceName": _g(raw, "InstanceName", "AssetName"),
        "internetIp": _g(raw, "InternetIp", "PublicIp"),
        "intranetIp": _g(raw, "IntranetIp", "PrivateIp"),
        "uuid": _g(raw, "Uuid", "InstanceId"),
        "uniqueInfo": _g(raw, "AlarmUniqueInfo", "UniqueInfo"),
        "eventId": _g(raw, "SecurityEventIds", "Id", "EventId", "SuspEventId"),
        "dataSource": _g(raw, "DataSource"),
        "matchedKeywords": _constants.matched_mining_keywords(name, etype, desc),
        "levelRank": _constants.level_rank(level),
    }


def query_susp_events(region: str, profile: Optional[str], dealed: str) -> tuple[list[dict], list[dict]]:
    """SAS DescribeSuspEvents -- security alert events.

    Returns (all_alerts, mining_alerts): the full normalized alert list plus
    the subset matching mining keywords. Callers may use all_alerts as a
    fallback probe for the detail APIs when no mining alert exists.
    """
    params: dict[str, Any] = {"Lang": "zh"}
    if dealed in ("Y", "N"):
        params["Dealed"] = dealed
    raw = _cli.paginate_page(
        "sas", "DescribeSuspEvents", params,
        region=region, profile=profile, items_key="SuspEvents", page_size=20,
    )
    all_alerts = [_normalize_alert(r, "susp") for r in raw if isinstance(r, dict)]
    mining = [a for a in all_alerts
              if _constants.is_mining_text(a["alarmEventName"], a["alarmEventType"], a["description"])]
    return all_alerts, mining


def collect_alerts(region: str, profile: Optional[str], dealed: str) -> dict[str, Any]:
    result: dict[str, Any] = {"mining_alerts": [], "all_alerts": [], "errors": []}
    try:
        all_alerts, mining = query_susp_events(region, profile, dealed)
        result["all_alerts"] = all_alerts
        result["mining_alerts"].extend(mining)
    except _cli.CliError as e:
        result["errors"].append(f"DescribeSuspEvents: {e}")

    # De-duplicate by (name, uuid, eventId), keep highest-severity ordering.
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for a in sorted(result["mining_alerts"], key=lambda x: x["levelRank"], reverse=True):
        key = (a["alarmEventName"], a["uuid"], a["eventId"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(a)
    result["mining_alerts"] = deduped
    result["total"] = len(deduped)
    result["affected_assets"] = sorted({a["uuid"] for a in deduped if a["uuid"]})
    return result


def format_text(result: dict[str, Any]) -> str:
    lines = ["Mining Alert Detection (Security Center)", "=" * 60, ""]
    if result.get("errors"):
        lines.append("--- Warnings ---")
        for e in result["errors"]:
            lines.append(f"  ! {e}")
        lines.append("")
    total = result.get("total", 0)
    lines.append(f"Mining alerts found: {total}")
    lines.append(f"Affected assets: {len(result.get('affected_assets', []))}")
    lines.append("")
    if total == 0:
        lines.append("No mining alerts detected in Security Center for the given window.")
        return "\n".join(lines)
    for a in result["mining_alerts"]:
        lines.append(
            f"[{a['level'] or 'N/A'}] {a['alarmEventName']} ({a['alarmEventType']})"
        )
        lines.append(
            f"    asset={a['instanceName'] or 'N/A'} "
            f"ip={a['internetIp'] or a['intranetIp'] or 'N/A'} "
            f"uuid={_cli.mask_sensitive(a['uuid']) or 'N/A'}"
        )
        lines.append(
            f"    dealed={a['dealed'] or 'N/A'} lastTime={a['lastTime'] or 'N/A'} "
            f"keywords={','.join(a['matchedKeywords']) or '-'}"
        )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    _cli.check_cli_available()

    region, profile = args.region, args.profile
    if not args.account:
        args.account = _cli.resolve_account_id(region, profile) or "N/A"
        print(f"[INFO] UID (display only): {_cli.mask_sensitive(args.account)}", file=sys.stderr)

    print("[STEP 1] Querying Security Center for mining alerts...", file=sys.stderr)
    result = collect_alerts(region, profile, args.dealed)
    print(f"[STEP 1] {result.get('total', 0)} mining alert(s) found.", file=sys.stderr)

    if args.format == "json":
        output = _cli.mask_text(
            json.dumps(_cli.mask_obj(result), indent=2, ensure_ascii=False),
            extra=[args.account],
        )
    else:
        output = _cli.mask_text(format_text(result), extra=[args.account])

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Saved to {args.output}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
