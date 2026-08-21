#!/usr/bin/env python3
"""
query_deep_scan.py  (dual-backend edition)
==========================================
C-enhancement: SAS-only deep entry-vector scan. Runs AFTER mining is confirmed
to narrow down the most likely intrusion entry, using additional read-only
Security Center APIs (no new product, no extra permission family beyond
yundun-aegis):

  - DescribeCheckWarningSummary  -- baseline / weak-config risks (weak passwords,
                                    unauthorized Redis/Docker, risky config)
  - DescribeGroupedVul           -- vulnerabilities grouped by type (fast view of
                                    which vuln class most likely enabled entry)
  - DescribeExposedStatistics    -- exposure-surface summary counts

All READ-ONLY. Failures degrade gracefully (captured, never fatal).

AUTHENTICATION: handled by the active backend (see _cli.py).

Usage:
    python query_deep_scan.py
    python query_deep_scan.py --region cn-hangzhou --format json
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
        description="SAS-only deep entry-vector scan (baseline + grouped vuln + exposure stats)"
    )
    p.add_argument("--region", default="cn-hangzhou", help="Alibaba Cloud region")
    p.add_argument("--profile", default=None, help="aliyun CLI profile (optional)")
    p.add_argument("--max-items", type=int, default=30,
                   help="Max baseline warnings to keep (default 30)")
    p.add_argument("--format", choices=["json", "text"], default="text")
    p.add_argument("--output", help="Output file path (default: stdout)")
    return p.parse_args()


def _g(d: Any, *keys: str, default: Any = "") -> Any:
    """Case-tolerant nested-dict field getter."""
    if not isinstance(d, dict):
        return default
    lower = {str(k).lower(): v for k, v in d.items()}
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
        lk = k.lower()
        if lk in lower and lower[lk] not in (None, ""):
            return lower[lk]
    return default


def _first_list(body: dict, *keys: str) -> list:
    """Return the first present list under any of `keys`, else the first list
    value found anywhere in the top-level body (schema-tolerant)."""
    for k in keys:
        v = _g(body, k, default=None)
        if isinstance(v, list):
            return v
    for v in body.values():
        if isinstance(v, list):
            return v
    return []


# ---------------------------------------------------------------------------
# C.1  Baseline / weak-config risks
# ---------------------------------------------------------------------------

def query_check_warnings(region: str, profile: Optional[str], max_items: int) -> dict[str, Any]:
    """SAS DescribeCheckWarningSummary -- baseline weak-config risk summary.

    Weak passwords, unauthorized Redis/Docker/Hadoop, and risky OS/app config are
    the most common cryptominer entry vectors, so surfacing them focuses the
    entry-vector hypothesis.
    """
    params = {"CurrentPage": 1, "PageSize": 20}
    try:
        items = _cli.paginate_page(
            "sas", "DescribeCheckWarningSummary", params,
            region=region, profile=profile, items_key="WarningSummarys", page_size=20,
        )
    except _cli.CliError as e:
        return {"error": str(e), "count": 0, "items": []}
    out = []
    for w in items[:max_items]:
        out.append({
            "name": _g(w, "CheckWarningName", "Item", "Name"),
            "level": _g(w, "RiskLevel", "Level"),
            "type": _g(w, "TypeName", "Type", "CheckType"),
            "affectedCount": _g(w, "AffectCount", "InstanceCount", "Count", default=0),
        })
    return {"count": len(items), "items": out}


# ---------------------------------------------------------------------------
# C.2  Grouped vulnerabilities (entry-vector classes)
# ---------------------------------------------------------------------------

def query_grouped_vul(region: str, profile: Optional[str]) -> dict[str, Any]:
    """SAS DescribeGroupedVul -- vulnerabilities grouped by type/necessity.

    A quick class-level view (cve/sys/cms/app/emg) of which vulnerability family
    most likely served as the intrusion entry, complementing Step 4's flat list.
    """
    results: dict[str, Any] = {"groups": [], "errors": []}
    for vtype in ("cve", "app", "cms"):
        params = {"Type": vtype, "CurrentPage": 1, "PageSize": 20, "Dealed": "n"}
        try:
            body = _cli.call("sas", "DescribeGroupedVul", params, region=region, profile=profile)
        except _cli.CliError as e:
            results["errors"].append(f"{vtype}: {e}")
            continue
        for g in _first_list(body, "GroupedVulItems", "GroupedVuls", "Vuls"):
            results["groups"].append({
                "type": vtype,
                "name": _g(g, "AliasName", "Name", "GroupName"),
                "necessity": _g(g, "Necessity"),
                "count": _g(g, "Count", "Total", "Num", default=0),
            })
    results["groups"].sort(key=lambda x: x.get("count", 0) or 0, reverse=True)
    return results


# ---------------------------------------------------------------------------
# C.3  Exposure-surface statistics
# ---------------------------------------------------------------------------

def query_exposed_statistics(region: str, profile: Optional[str]) -> dict[str, Any]:
    """SAS DescribeExposedStatistics -- one-shot exposure-surface summary."""
    try:
        body = _cli.call("sas", "DescribeExposedStatistics", {}, region=region, profile=profile)
    except _cli.CliError as e:
        return {"error": str(e)}
    stat = _g(body, "ExposedStatistics", "ExposedStatisticsResponse", default=body)
    return {
        "exposedInstanceCount": _g(stat, "ExposedInstanceCount", "ExposedInstanceCnt", default=0),
        "exposedPortCount": _g(stat, "ExposedPortCount", "ExposedPortCnt", default=0),
        "exposedComponentCount": _g(stat, "ExposedComponentCount", "ExposedComponentCnt", default=0),
        "gatewayAssetCount": _g(stat, "GatewayAssetCount", default=0),
    }


def collect(region: str, profile: Optional[str], max_items: int = 30) -> dict[str, Any]:
    """Aggregate the three SAS-only deep-scan signals."""
    baseline = query_check_warnings(region, profile, max_items)
    grouped_vul = query_grouped_vul(region, profile)
    exposed_stat = query_exposed_statistics(region, profile)
    errors: list[str] = []
    if baseline.get("error"):
        errors.append(f"checkWarnings: {baseline['error']}")
    errors.extend(f"groupedVul {e}" for e in grouped_vul.get("errors", []))
    if exposed_stat.get("error"):
        errors.append(f"exposedStatistics: {exposed_stat['error']}")
    return {
        "baseline": baseline,
        "groupedVul": grouped_vul.get("groups", []),
        "exposedStatistics": exposed_stat,
        "errors": errors,
    }


def format_text(deep: dict[str, Any]) -> str:
    lines = ["SAS Deep Entry-Vector Scan", "=" * 60, ""]
    b = deep.get("baseline", {})
    lines.append(f"Baseline weak-config risks: {b.get('count', 0)}")
    for w in b.get("items", [])[:15]:
        lines.append(f"  - [{w.get('level') or 'N/A'}] {w.get('name') or 'N/A'} "
                     f"(type={w.get('type') or 'N/A'}, affected={w.get('affectedCount')})")
    lines.append("")
    gv = deep.get("groupedVul", [])
    lines.append(f"Grouped vulnerabilities (unfixed): {len(gv)} group(s)")
    for g in gv[:15]:
        lines.append(f"  - [{g.get('type')}/{g.get('necessity') or '-'}] "
                     f"{g.get('name') or 'N/A'} x{g.get('count')}")
    lines.append("")
    es = deep.get("exposedStatistics", {})
    if es.get("error"):
        lines.append(f"Exposure statistics: ERROR — {es['error']}")
    else:
        lines.append(f"Exposure statistics: instances={es.get('exposedInstanceCount', 0)}, "
                     f"ports={es.get('exposedPortCount', 0)}, "
                     f"components={es.get('exposedComponentCount', 0)}")
    if deep.get("errors"):
        lines.append("")
        for e in deep["errors"]:
            lines.append(f"  warning: {e}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    _cli.check_cli_available()
    deep = collect(args.region, args.profile, args.max_items)

    if args.format == "json":
        output = _cli.mask_text(json.dumps(_cli.mask_obj(deep), indent=2, ensure_ascii=False))
    else:
        output = _cli.mask_text(format_text(deep))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Saved to {args.output}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
