#!/usr/bin/env python3
"""
query_attack_surface.py  (dual-backend edition)
===============================================
Step 4 of the mining-attack detection SOP: assess the attack surface that most
commonly leads to cryptojacking — internet-exposed assets and unpatched
high-risk vulnerabilities — via Security Center (SAS). Correlating these with
the mining-affected assets (from Step 1) helps hypothesize the intrusion entry.

Routed through the dual-backend layer in `_cli.py`. READ-ONLY: no handling /
mutating calls.

Data sources:
  - SAS DescribeExposedInstanceList -- internet-exposed assets (attack surface)
  - SAS DescribeVulList             -- vulnerability records (entry vectors)

AUTHENTICATION: handled by the active backend (see _cli.py).

Usage:
    python query_attack_surface.py --account <UID>
    python query_attack_surface.py --vul-type cve --necessity asap --format json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cli


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Query SAS attack surface (exposed assets + vulns) via dual-backend"
    )
    p.add_argument("--account", default=None,
                   help="Alibaba Cloud UID (optional; auto-derived via STS if omitted)")
    p.add_argument("--region", default="cn-hangzhou", help="Alibaba Cloud region (default: cn-hangzhou)")
    p.add_argument("--profile", default=None, help="aliyun CLI profile name (optional)")
    p.add_argument("--vul-type", default="cve",
                   help="Vulnerability type: cve/sys/cms/app/emg/sca (default: cve)")
    p.add_argument("--necessity", default="asap",
                   help="Vuln fix necessity filter: asap/later/nntf (default: asap)")
    p.add_argument("--scope", choices=["exposed", "vuls", "both"], default="both",
                   help="What to query (default: both)")
    p.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
    p.add_argument("--output", help="Output file path (default: stdout)")
    return p.parse_args()


def _g(d: dict, *keys: str, default: str = "") -> str:
    if not isinstance(d, dict):
        return default
    lower = {str(k).lower(): v for k, v in d.items()}
    for k in keys:
        v = lower.get(k.lower())
        if v not in (None, ""):
            return v
    return default


def query_exposed_instances(region: str, profile: Optional[str]) -> list[dict]:
    """SAS DescribeExposedInstanceList -- internet-exposed assets."""
    raw = _cli.paginate_page(
        "sas", "DescribeExposedInstanceList", {},
        region=region, profile=profile, items_key="ExposedInstances", page_size=20,
    )
    out = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        out.append({
            "instanceId": _g(r, "InstanceId"),
            "instanceName": _g(r, "InstanceName"),
            "internetIp": _g(r, "InternetIp", "ExposureIp"),
            "exposureType": _g(r, "ExposureType", "ExposureTypeList"),
            "exposurePort": _g(r, "ExposurePort", "ExposurePortList"),
            "exposureComponent": _g(r, "ExposureComponent", "ExposureComponentList"),
            "uuid": _g(r, "Uuid", "InstanceId"),
        })
    return out


def query_vul_list(region: str, profile: Optional[str], vul_type: str, necessity: str) -> list[dict]:
    """SAS DescribeVulList -- vulnerability records (entry vectors)."""
    params: dict[str, Any] = {"Type": vul_type, "Lang": "zh"}
    if necessity:
        params["Necessity"] = necessity
    raw = _cli.paginate_page(
        "sas", "DescribeVulList", params,
        region=region, profile=profile, items_key="VulRecords", page_size=20,
    )
    out = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        out.append({
            "aliasName": _g(r, "AliasName", "Name"),
            "name": _g(r, "Name"),
            "necessity": _g(r, "Necessity"),
            "status": _g(r, "Status"),
            "instanceName": _g(r, "InstanceName"),
            "internetIp": _g(r, "InternetIp"),
            "intranetIp": _g(r, "IntranetIp"),
            "uuid": _g(r, "Uuid"),
            "lastTs": _g(r, "LastTs", "GmtLast"),
        })
    return out


def collect(region: str, profile: Optional[str], vul_type: str,
            necessity: str, scope: str) -> dict[str, Any]:
    result: dict[str, Any] = {"exposed_instances": [], "vulnerabilities": [], "errors": []}
    if scope in ("exposed", "both"):
        try:
            result["exposed_instances"] = query_exposed_instances(region, profile)
        except _cli.CliError as e:
            result["errors"].append(f"DescribeExposedInstanceList: {e}")
    if scope in ("vuls", "both"):
        try:
            result["vulnerabilities"] = query_vul_list(region, profile, vul_type, necessity)
        except _cli.CliError as e:
            result["errors"].append(f"DescribeVulList: {e}")
    result["exposed_count"] = len(result["exposed_instances"])
    result["vul_count"] = len(result["vulnerabilities"])
    return result


def format_text(result: dict[str, Any]) -> str:
    lines = ["Attack Surface Assessment (Security Center)", "=" * 60, ""]
    if result.get("errors"):
        lines.append("--- Warnings ---")
        for e in result["errors"]:
            lines.append(f"  ! {e}")
        lines.append("")
    lines.append(f"Internet-exposed assets: {result.get('exposed_count', 0)}")
    for x in result.get("exposed_instances", [])[:30]:
        lines.append(
            f"  - {x['instanceName'] or x['instanceId'] or 'N/A'} "
            f"ip={x['internetIp'] or 'N/A'} port={x['exposurePort'] or 'N/A'} "
            f"component={x['exposureComponent'] or 'N/A'}"
        )
    lines.append("")
    lines.append(f"Unpatched vulnerabilities: {result.get('vul_count', 0)}")
    for v in result.get("vulnerabilities", [])[:30]:
        lines.append(
            f"  - [{v['necessity'] or 'N/A'}] {v['aliasName'] or v['name'] or 'N/A'} "
            f"asset={v['instanceName'] or 'N/A'} status={v['status'] or 'N/A'}"
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    _cli.check_cli_available()

    region, profile = args.region, args.profile
    if not args.account:
        args.account = _cli.resolve_account_id(region, profile) or "N/A"
        print(f"[INFO] UID (display only): {_cli.mask_sensitive(args.account)}", file=sys.stderr)

    print("[STEP 4] Assessing attack surface (exposed assets + vulnerabilities)...", file=sys.stderr)
    result = collect(region, profile, args.vul_type, args.necessity, args.scope)
    print(f"[STEP 4] exposed={result.get('exposed_count', 0)} vuls={result.get('vul_count', 0)}",
          file=sys.stderr)

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
