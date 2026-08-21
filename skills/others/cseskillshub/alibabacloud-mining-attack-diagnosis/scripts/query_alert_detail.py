#!/usr/bin/env python3
"""
query_alert_detail.py  (dual-backend edition)
=============================================
Step 2 of the mining-attack detection SOP: fetch full alert detail from
Security Center (SAS) and extract Indicators of Compromise (IOCs) — malicious
process names/paths, mining-pool IPs/domains, sample hashes, persistence hints.

Routed through the dual-backend layer in `_cli.py`. READ-ONLY: no handling /
mutating calls.

Data sources:
  - SAS DescribeAlarmEventDetail  -- detail by UniqueInfo (aggregated alarm)
  - SAS DescribeSuspEventDetail   -- detail by SuspEventId (raw event)

AUTHENTICATION: handled by the active backend (see _cli.py).

Usage:
    python query_alert_detail.py --unique-info <UNIQUE_INFO>
    python query_alert_detail.py --event-id <SUSP_EVENT_ID> --format json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cli
import _constants

# IOC extraction patterns.
_IPV4_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
_MD5_RE = re.compile(r"\b[a-fA-F0-9]{32}\b")
_SHA256_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")
_DOMAIN_RE = re.compile(r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b")

# Private / non-routable IPs are not treated as mining-pool IOCs.
_PRIVATE_IP_PREFIXES = ("10.", "192.168.", "127.", "0.", "169.254.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fetch SAS alert detail and extract mining IOCs via dual-backend"
    )
    p.add_argument("--unique-info", help="UniqueInfo of an aggregated alarm (DescribeAlarmEventDetail)")
    p.add_argument("--event-id", help="SuspEventId of a raw event (DescribeSuspEventDetail)")
    p.add_argument("--region", default="cn-hangzhou", help="Alibaba Cloud region (default: cn-hangzhou)")
    p.add_argument("--profile", default=None, help="aliyun CLI profile name (optional)")
    p.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
    p.add_argument("--output", help="Output file path (default: stdout)")
    return p.parse_args()


def _is_public_ip(ip: str) -> bool:
    if any(ip.startswith(p) for p in _PRIVATE_IP_PREFIXES):
        return False
    if ip.startswith("172."):
        try:
            second = int(ip.split(".")[1])
            if 16 <= second <= 31:
                return False
        except (IndexError, ValueError):
            pass
    return True


def _walk_strings(obj: Any) -> list[str]:
    """Collect all string leaves from a nested dict/list structure."""
    out: list[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(_walk_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_walk_strings(v))
    return out


def extract_iocs(detail: dict) -> dict[str, Any]:
    """Extract IOCs from an SAS alert detail structure (best-effort)."""
    strings = _walk_strings(detail)
    blob = "\n".join(strings)

    ips = sorted({ip for ip in _IPV4_RE.findall(blob) if _is_public_ip(ip)})
    md5s = sorted(set(_MD5_RE.findall(blob)))
    sha256s = sorted(set(_SHA256_RE.findall(blob)))

    # Domains: drop pure-numeric matches (already caught as IPs) and obvious
    # Alibaba/aliyun infrastructure domains.
    domains = sorted({
        d for d in _DOMAIN_RE.findall(blob)
        if not _IPV4_RE.fullmatch(d)
        and "aliyun" not in d.lower()
        and "aliyuncs" not in d.lower()
    })

    # Process / command indicators: pick strings that look like paths or
    # command lines and contain a mining keyword, plus explicit key hints.
    proc_indicators: list[str] = []
    for s in strings:
        low = s.lower()
        looks_like_proc = ("/" in s or "\\" in s or " -o " in low or "cmd" in low or "proc" in low)
        if _constants.is_mining_text(s) and (looks_like_proc or len(s) < 200):
            proc_indicators.append(s.strip())
    proc_indicators = sorted(set(proc_indicators))[:20]

    return {
        "miningPoolIps": ips[:50],
        "domains": domains[:50],
        "sampleMd5": md5s[:50],
        "sampleSha256": sha256s[:50],
        "processIndicators": proc_indicators,
        "matchedKeywords": _constants.matched_mining_keywords(blob),
    }


def get_alarm_detail(region: str, profile: Optional[str], unique_info: str) -> dict[str, Any]:
    try:
        body = _cli.call("sas", "DescribeAlarmEventDetail",
                         {"AlarmUniqueInfo": unique_info, "From": "sas", "Lang": "zh"},
                         region=region, profile=profile)
        return {"detail": body, "iocs": extract_iocs(body)}
    except _cli.CliError as e:
        return {"error": str(e)}


def get_susp_detail(region: str, profile: Optional[str], event_id: str) -> dict[str, Any]:
    try:
        body = _cli.call("sas", "DescribeSuspEventDetail",
                         {"SuspiciousEventId": event_id, "From": "sas", "Lang": "zh"},
                         region=region, profile=profile)
        return {"detail": body, "iocs": extract_iocs(body)}
    except _cli.CliError as e:
        return {"error": str(e)}


def format_text(result: dict[str, Any]) -> str:
    lines = ["Mining Alert Detail & IOC Extraction", "=" * 60, ""]
    if result.get("error"):
        lines.append(f"ERROR: {result['error']}")
        return "\n".join(lines)
    iocs = result.get("iocs", {})
    lines.append("--- Extracted IOCs ---")
    lines.append(f"  Mining-pool IPs : {', '.join(iocs.get('miningPoolIps', [])) or '(none)'}")
    lines.append(f"  Domains         : {', '.join(iocs.get('domains', [])) or '(none)'}")
    lines.append(f"  Sample MD5      : {', '.join(iocs.get('sampleMd5', [])) or '(none)'}")
    lines.append(f"  Sample SHA256   : {', '.join(iocs.get('sampleSha256', [])) or '(none)'}")
    lines.append(f"  Keywords        : {', '.join(iocs.get('matchedKeywords', [])) or '(none)'}")
    procs = iocs.get("processIndicators", [])
    lines.append("  Process / command indicators:")
    if procs:
        for pth in procs:
            lines.append(f"    - {pth}")
    else:
        lines.append("    (none)")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    if not args.unique_info and not args.event_id:
        print("Error: provide --unique-info or --event-id", file=sys.stderr)
        return 2
    _cli.check_cli_available()

    region, profile = args.region, args.profile
    if args.unique_info:
        print(f"[STEP 2] DescribeAlarmEventDetail UniqueInfo={args.unique_info}", file=sys.stderr)
        result = get_alarm_detail(region, profile, args.unique_info)
    else:
        print(f"[STEP 2] DescribeSuspEventDetail SuspEventId={args.event_id}", file=sys.stderr)
        result = get_susp_detail(region, profile, args.event_id)

    if args.format == "json":
        output = json.dumps(_cli.mask_obj(result), indent=2, ensure_ascii=False)
    else:
        output = format_text(result)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Saved to {args.output}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
