#!/usr/bin/env python3
"""
query_notification.py  (dual-backend edition)
=============================================
Query AK leak notifications and ban status via the dual-backend layer in
`_cli.py` (aliyun CLI preferred, V3-signed HTTPS fallback; no Python SDKs).

Data sources (all READ-ONLY -- this script performs no write/mutating calls):
  1. Security Center (SAS): DescribeAccesskeyLeakList -- detects leaked AKs
  2. Security Center (SAS): DescribeAccessKeyLeakDetail -- full detail of one leak event
  3. ActionTrail: LookupEvents -- infers ban status from errorCode analysis

Note: the two SAS APIs above are callable with a standard credential
(verified against the live API). DescribeAccesskeyLeakList returns whatever
leaks Security Center has flagged (empty if none); an unknown Id returns
"data not exist", not a permission error.

Remediation is intentionally NOT automated: when a leak is confirmed the
investigation report prints a strong warning telling the operator to disable
the leaked AK, replace it in all running services, and create a new AK. This
skill never disables or modifies any credential.

AUTHENTICATION:
    Handled by the active backend (see _cli.py): aliyun CLI profile
    (~/.aliyun/config.json) or, on HTTP fallback, env AK/SK / config.json.

Usage:
    python query_notification.py --account <UID> --ak <AK>
    python query_notification.py --account <UID> --ak <AK> --days 30
    python query_notification.py --account <UID> --profile myprofile
    python query_notification.py --account <UID> --detail-id <LeakEventId>
"""

import argparse
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cli

BAN_ERROR_CODES = {
    "InvalidAccessKeyId.Inactive",
    "Forbidden.AccessKeyDisabled",
    "Forbidden.AccessKey",
    "InvalidAccessKeyId.NotFound",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Query AK leak notifications via dual-backend (Security Center + ActionTrail)"
    )
    p.add_argument("--account", default=None,
                   help="Alibaba Cloud UID (optional; auto-derived from the credential via STS if omitted)")
    p.add_argument("--ak", help="AccessKey ID to check for leak alerts")
    p.add_argument("--days", type=int, default=30, help="Lookback days (default: 30)")
    p.add_argument("--region", default="cn-shanghai", help="Alibaba Cloud region (default: cn-shanghai)")
    p.add_argument("--profile", default=None, help="aliyun CLI profile name (optional)")
    p.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
    p.add_argument("--output", help="Output file path (default: stdout)")
    p.add_argument("--detail-id", type=int, default=None,
                   help="Fetch full detail for one leak event ID (DescribeAccessKeyLeakDetail)")
    return p.parse_args()


def query_ak_leak_detection(region: str, profile: Any, ak: str = "") -> dict[str, Any]:
    """Security Center DescribeAccesskeyLeakList -- find AK leak events."""
    result = {
        "source": "security_center",
        "alert_detected": False,
        "total_records": 0,
        "records": [],
        "aks_found_in_alert": [],
    }
    try:
        params = {"CurrentPage": 1, "PageSize": 100}
        if ak:
            params["Query"] = f"ak:{ak}"
        body = _cli.call("sas", "DescribeAccesskeyLeakList", params,
                         region=region, profile=profile)
        records = body.get("AccessKeyLeakList") or []
        total = body.get("TotalCount", 0) or 0
        result["total_records"] = total
        result["records"] = [
            {
                "id": r.get("Id", ""),
                "ak": r.get("AccesskeyId", "") or r.get("AccessKeyId", ""),
                "type": r.get("Type", ""),
                "status": r.get("Status", ""),
                "deal_time": r.get("DealTime", ""),
                "gmt_modified": r.get("GmtModified", ""),
                "url": r.get("Url", ""),
                "asset": r.get("Asset", ""),
                "user_type": r.get("UserType", ""),
            }
            for r in records
        ]
        result["alert_detected"] = total > 0
        aks = {r.get("AccesskeyId") or r.get("AccessKeyId") for r in records}
        result["aks_found_in_alert"] = sorted(a for a in aks if a)
    except _cli.CliError as e:
        code = e.code or ""
        if "NoPermission" in code or "Forbidden" in code or "NoPermission" in str(e):
            result["error"] = (
                f"Security Center API access denied (credential lacks "
                f"yundun-aegis:DescribeAccesskeyLeakList): {e}. "
                f"Proceed with user-provided AK instead."
            )
        else:
            result["error"] = str(e)
    return result


def infer_ban_from_actiontrail(
    region: str, profile: Any, ak: str, start_time: str, end_time: str
) -> dict[str, Any]:
    """Infer AK ban status from ActionTrail error codes."""
    result = {
        "ak_ban_inferred": False,
        "ban_error_codes": [],
        "total_events": 0,
        "failed_events": 0,
    }
    if not ak:
        return result
    try:
        events = _cli.paginate_next_token(
            "actiontrail", "LookupEvents",
            {
                "StartTime": start_time,
                "EndTime": end_time,
                "MaxResults": 50,
                "LookupAttribute.1.Key": "EventAccessKeyId",
                "LookupAttribute.1.Value": ak,
            },
            region=region, profile=profile,
        )
        ban_codes = set()
        total = len(events)
        failed = 0
        for evt in events:
            ec = (evt.get("errorCode") if isinstance(evt, dict) else "") or ""
            if ec in BAN_ERROR_CODES:
                failed += 1
                ban_codes.add(ec)
        result["total_events"] = total
        result["failed_events"] = failed
        result["ban_error_codes"] = sorted(ban_codes)
        if total > 0 and failed == total and ban_codes:
            result["ak_ban_inferred"] = True
    except _cli.CliError as e:
        result["error"] = str(e)
    return result


def get_leak_detail(region: str, profile: Any, leak_id: int) -> dict[str, Any]:
    """Security Center DescribeAccessKeyLeakDetail -- full detail of one leak event.

    `leak_id` is the `Id` field from a DescribeAccesskeyLeakList record.
    An unknown id returns "data not exist", not a permission error.
    """
    result: dict[str, Any] = {"id": leak_id}
    try:
        body = _cli.call("sas", "DescribeAccessKeyLeakDetail", {"Id": leak_id},
                         region=region, profile=profile)
        result["detail"] = body
    except _cli.CliError as e:
        result["error"] = str(e)
    return result


def format_text_output(notification: dict[str, Any], ban_info: dict[str, Any],
                       detail: dict[str, Any] = None) -> str:
    lines = ["AK Leak Notification Query Results"]
    lines.append("=" * 60)

    lines.append("")
    lines.append("--- Security Center: AK Leak Detection ---")
    if notification.get("error"):
        lines.append(f"  Status: SKIPPED ({notification['error']})")
    else:
        lines.append(f"  Alert Detected: {'YES' if notification.get('alert_detected') else 'NO'}")
        lines.append(f"  Total Records: {notification.get('total_records', 0)}")
        aks = notification.get("aks_found_in_alert", [])
        if aks:
            lines.append(f"  AKs in Alerts: {', '.join(_cli.mask_sensitive(a) for a in aks)}")
        for rec in notification.get("records", [])[:20]:
            lines.append(f"  - Id: {rec.get('id', 'N/A')} | AK: {_cli.mask_sensitive(rec.get('ak', 'N/A'))} | Type: {rec.get('type', 'N/A')} | "
                         f"Status: {rec.get('status', 'N/A')} | Time: {rec.get('deal_time', 'N/A')}")

    lines.append("")
    lines.append("--- AK Ban Inference (from ActionTrail errorCodes) ---")
    if ban_info.get("error"):
        lines.append(f"  Status: ERROR ({ban_info['error']})")
    else:
        lines.append(f"  AK Ban Inferred: {'YES' if ban_info.get('ak_ban_inferred') else 'NO'}")
        lines.append(f"  Total Events Analyzed: {ban_info.get('total_events', 0)}")
        lines.append(f"  Failed Events (ban codes): {ban_info.get('failed_events', 0)}")
        codes = ban_info.get("ban_error_codes", [])
        if codes:
            lines.append(f"  Ban Error Codes: {', '.join(codes)}")

    if detail is not None:
        lines.append("")
        lines.append("--- Leak Event Detail (DescribeAccessKeyLeakDetail) ---")
        if detail.get("error"):
            lines.append(f"  Id {detail.get('id')}: ERROR ({detail['error']})")
        else:
            d = detail.get("detail", {}) or {}
            lines.append(f"  Id: {detail.get('id')}")
            for k in ("AccessKeyId", "AccesskeyId", "Type", "Status", "Location",
                      "Asset", "GmtCreate", "GmtModified", "Url"):
                if k in d:
                    val = _cli.mask_sensitive(d.get(k)) if "accesskey" in k.lower() else d.get(k)
                    lines.append(f"    {k}: {val}")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    _cli.check_cli_available()

    region, profile = args.region, args.profile
    days = min(max(args.days, 1), 90)
    start_time, end_time = _cli.get_time_window(days)
    if not args.account:
        args.account = _cli.resolve_account_id(region, profile)
        if args.account:
            print(f"[INFO] UID auto-derived from credential: {_cli.mask_sensitive(args.account)}", file=sys.stderr)
        else:
            args.account = "N/A"
            print("[WARN] Could not auto-derive UID (credential lacks STS access); continuing.",
                  file=sys.stderr)
    print(f"[INFO] Account: {_cli.mask_sensitive(args.account)}", file=sys.stderr)
    print(f"[INFO] AK: {_cli.mask_sensitive(args.ak) if args.ak else 'N/A'}", file=sys.stderr)
    print(f"[INFO] Time window: {start_time} ~ {end_time}", file=sys.stderr)

    print("[STEP 1] Querying Security Center for AK leak alerts...", file=sys.stderr)
    notification = query_ak_leak_detection(region, profile, args.ak or "")

    print("[STEP 1] Inferring AK ban status from ActionTrail error codes...", file=sys.stderr)
    ban_info = infer_ban_from_actiontrail(region, profile, args.ak or "", start_time, end_time)

    detail = None
    if args.detail_id is not None:
        print(f"[STEP 1] Fetching leak detail for Id={args.detail_id}...", file=sys.stderr)
        detail = get_leak_detail(region, profile, args.detail_id)

    if args.format == "json":
        payload = {"notification": notification, "ban_inference": ban_info}
        if detail is not None:
            payload["leak_detail"] = detail
        output = _cli.mask_text(
            json.dumps(_cli.mask_obj(payload), indent=2, ensure_ascii=False),
            extra=[args.account, args.ak],
        )
    else:
        output = _cli.mask_text(
            format_text_output(notification, ban_info, detail),
            extra=[args.account, args.ak],
        )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Saved to {args.output}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
