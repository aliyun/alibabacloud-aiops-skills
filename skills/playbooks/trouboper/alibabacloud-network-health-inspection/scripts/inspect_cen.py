"""
inspect_cen.py - 阿里云云企业网（CEN）巡检

查询 CEN 实例及带宽包信息，评估跨地域带宽使用情况。
所有 API 调用均为只读查询操作，不涉及任何写操作。

巡检指标说明:
  - InterRegionOutBandwidth: 跨地域出方向带宽（bits/s），流出本地域的跨地域带宽
  - InterRegionInBandwidth: 跨地域入方向带宽（bits/s），流入本地域的跨地域带宽

CEN 带宽包说明:
  - CEN 带宽包用于跨地域互通，限制跨地域之间的最大传输带宽
  - 同地域内通过 TR 互通不消耗带宽包额度

用法:
    python3 inspect_cen.py --days 3
    python3 inspect_cen.py --instance-ids cen-xxx,cen-yyy --days 7
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inspect_common import (
    call_with_retry, query_metrics_batch,
    assess_risk, bits_to_mbps, CN_REGIONS, format_standard_output,
)

# CEN 云监控指标（namespace: acs_cen）
# 跨地域带宽指标，dimension 需要 cenId
CEN_METRICS = [
    "InterRegionOutBandwidth",   # 跨地域出方向带宽 (bits/s)
    "InterRegionInBandwidth",    # 跨地域入方向带宽 (bits/s)
]

NAMESPACE = "acs_cen"


def list_cen_instances(instance_ids: list = None) -> list:
    """查询 CEN 实例列表（CEN 为全局资源，不区分 Region）（只读操作）。"""
    params = {"PageSize": "50"}
    all_instances = []
    page = 1

    while True:
        params["PageNumber"] = str(page)
        result = call_with_retry("cbn", "DescribeCens", params, "cn-hangzhou")
        if "error" in result:
            return [{"error": result["error"], "region": "global"}]

        cens = result.get("Cens", {}).get("Cen", [])
        if not cens:
            break

        for cen in cens:
            cen_id = cen.get("CenId", "")
            if instance_ids and cen_id not in instance_ids:
                continue
            all_instances.append({
                "instance_id": cen_id,
                "instance_name": cen.get("Name", ""),
                "region": "global",
                "status": cen.get("Status", ""),
                "description": cen.get("Description", ""),
                "creation_time": cen.get("CreationTime", ""),
                "protection_level": cen.get("ProtectionLevel", ""),
            })

        total = result.get("TotalCount", 0)
        if page * 50 >= total:
            break
        page += 1

    return all_instances


def list_cen_bandwidth_packages(cen_id: str = None) -> list:
    """查询 CEN 带宽包列表（只读操作）。"""
    params = {"PageSize": "50"}
    if cen_id:
        # 使用 Filter 筛选特定 CEN 的带宽包
        params["Filter.1.Key"] = "CenId"
        params["Filter.1.Value.1"] = cen_id
    all_packages = []
    page = 1

    while True:
        params["PageNumber"] = str(page)
        result = call_with_retry("cbn", "DescribeCenBandwidthPackages", params, "cn-hangzhou")
        if "error" in result:
            return [{"error": result["error"]}]

        packages = result.get("CenBandwidthPackages", {}).get("CenBandwidthPackage", [])
        if not packages:
            break

        for pkg in packages:
            all_packages.append({
                "package_id": pkg.get("CenBandwidthPackageId", ""),
                "name": pkg.get("Name", ""),
                "bandwidth_limit": int(pkg.get("Bandwidth", 0)),
                "status": pkg.get("Status", ""),
                "cen_ids": pkg.get("CenIds", {}).get("CenId", []),
                "geographic_region_a": pkg.get("GeographicRegionAId", ""),
                "geographic_region_b": pkg.get("GeographicRegionBId", ""),
                "business_status": pkg.get("BusinessStatus", ""),
                "creation_time": pkg.get("CreationTime", ""),
            })

        total = result.get("TotalCount", 0)
        if page * 50 >= total:
            break
        page += 1

    return all_packages


def inspect_instance(instance: dict, days: int, period: int) -> dict:
    """对单个 CEN 实例进行巡检（只读操作）。"""
    cen_id = instance["instance_id"]

    # 查询关联的带宽包
    bw_packages = list_cen_bandwidth_packages(cen_id)
    bw_packages_clean = [p for p in bw_packages if "error" not in p]

    # 尝试查询 CEN 跨地域带宽指标
    metrics_result = query_metrics_batch(NAMESPACE, CEN_METRICS, cen_id, days, period, dim_key="cenId")
    metrics = metrics_result.get("metrics", {})

    out_summary = metrics.get("InterRegionOutBandwidth", {}).get("summary")
    in_summary = metrics.get("InterRegionInBandwidth", {}).get("summary")

    tx_peak_mbps = bits_to_mbps(out_summary["max"]) if out_summary else 0
    rx_peak_mbps = bits_to_mbps(in_summary["max"]) if in_summary else 0
    tx_avg_mbps = bits_to_mbps(out_summary["avg"]) if out_summary else 0
    rx_avg_mbps = bits_to_mbps(in_summary["avg"]) if in_summary else 0

    # 总带宽上限 = 所有带宽包之和
    total_bw_limit = sum(p.get("bandwidth_limit", 0) for p in bw_packages_clean)
    peak_pct = round(max(tx_peak_mbps, rx_peak_mbps) / total_bw_limit * 100, 2) if total_bw_limit > 0 else 0

    # 状态评估
    status = instance.get("status", "")
    if status not in ("Active", ""):
        risk_level = "critical"
    else:
        risk_level = assess_risk(peak_pct, False)

    instance["metrics"] = {
        "tx_peak_mbps": tx_peak_mbps,
        "rx_peak_mbps": rx_peak_mbps,
        "tx_avg_mbps": tx_avg_mbps,
        "rx_avg_mbps": rx_avg_mbps,
        "total_bw_limit_mbps": total_bw_limit,
        "peak_utilization_pct": peak_pct,
    }
    instance["bandwidth_packages"] = bw_packages_clean
    instance["risk_level"] = risk_level
    instance["time_range"] = metrics_result.get("time_range", {})

    return instance


def main():
    parser = argparse.ArgumentParser(description="阿里云云企业网（CEN）巡检（只读操作）")
    parser.add_argument("--instance-ids", default="",
                        help="CEN 实例 ID 列表，逗号分隔（默认巡检全部）")
    parser.add_argument("--days", type=int, required=True,
                        help="巡检天数（必须指定）")
    parser.add_argument("--period", type=int, required=True,
                        help="监控数据聚合粒度（秒），如 60/300/900")
    args = parser.parse_args()

    instance_ids = [i.strip() for i in args.instance_ids.split(",") if i.strip()] if args.instance_ids else None

    all_instances = []
    errors = []

    instances = list_cen_instances(instance_ids)
    for inst in instances:
        if "error" in inst:
            errors.append(inst)
        else:
            all_instances.append(inst)

    inspected = []
    for inst in all_instances:
        try:
            result = inspect_instance(inst, args.days, args.period)
            inspected.append(result)
        except Exception as e:
            inst["error"] = str(e)
            inst["risk_level"] = "error"
            inspected.append(inst)

    output = format_standard_output("cen", "云企业网", args.days, ["global"], inspected, errors)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
