"""
inspect_cbwp.py - 阿里云共享带宽包巡检

查询共享带宽包实例信息和云监控数据，评估带宽利用率和限速丢包情况。
所有 API 调用均为只读查询操作，不涉及任何写操作。

巡检指标说明:
  - bwp_tx_rate: 出方向带宽（bits/s），共享带宽包流出的网络带宽
  - bwp_rx_rate: 入方向带宽（bits/s），共享带宽包流入的网络带宽
  - out_rate_percent: 出方向利用率（%），带宽使用占比
  - ratelimit_drop_speed: 限速丢包速率（packets/s），因带宽上限导致的丢包

注意: 共享带宽包的指标名是 bwp_tx_rate/bwp_rx_rate，不是 net_tx.rate/net_rx.rate。

用法:
    python3 inspect_cbwp.py --regions cn-hangzhou,cn-shanghai --days 3
    python3 inspect_cbwp.py --regions cn-hangzhou --instance-ids cbwp-xxx --days 7
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

# 共享带宽包云监控指标（namespace: acs_bandwidth_package）
# 注意: 指标名是 bwp_tx_rate/bwp_rx_rate，不是 net_tx.rate/net_rx.rate
CBWP_METRICS = [
    "bwp_tx_rate",          # 出方向带宽 (bits/s)
    "bwp_rx_rate",          # 入方向带宽 (bits/s)
    "out_rate_percent",     # 出方向利用率 (%)
    "ratelimit_drop_speed", # 限速丢包 (packets/s)
]

NAMESPACE = "acs_bandwidth_package"


def list_cbwp_instances(region: str, instance_ids: list = None) -> list:
    """查询指定 Region 的共享带宽包实例列表（只读操作）。"""
    params = {"PageSize": "50"}
    all_instances = []
    page = 1

    while True:
        params["PageNumber"] = str(page)
        result = call_with_retry("vpc", "DescribeCommonBandwidthPackages", params, region)
        if "error" in result:
            return [{"error": result["error"], "region": region}]

        packages = result.get("CommonBandwidthPackages", {}).get("CommonBandwidthPackage", [])
        if not packages:
            break

        for pkg in packages:
            pkg_id = pkg.get("BandwidthPackageId", "")
            if instance_ids and pkg_id not in instance_ids:
                continue
            all_instances.append({
                "instance_id": pkg_id,
                "instance_name": pkg.get("Name", ""),
                "region": region,
                "bandwidth_limit": int(pkg.get("Bandwidth", 0)),
                "status": pkg.get("Status", ""),
                "isp": pkg.get("ISP", ""),
                "business_status": pkg.get("BusinessStatus", ""),
                "creation_time": pkg.get("CreationTime", ""),
                "ip_count": len(pkg.get("PublicIpAddresses", {}).get("PublicIpAddresse", [])),
            })

        total = result.get("TotalCount", 0)
        if page * 50 >= total:
            break
        page += 1

    return all_instances


def inspect_instance(instance: dict, days: int, period: int) -> dict:
    """对单个共享带宽包实例进行巡检（只读操作）。"""
    instance_id = instance["instance_id"]

    metrics_result = query_metrics_batch(NAMESPACE, CBWP_METRICS, instance_id, days, period)
    metrics = metrics_result.get("metrics", {})

    # 提取关键指标
    tx_summary = metrics.get("bwp_tx_rate", {}).get("summary")
    rx_summary = metrics.get("bwp_rx_rate", {}).get("summary")
    pct_summary = metrics.get("out_rate_percent", {}).get("summary")
    drop_summary = metrics.get("ratelimit_drop_speed", {}).get("summary")

    bandwidth_limit = instance.get("bandwidth_limit", 0)

    tx_peak_mbps = bits_to_mbps(tx_summary["max"]) if tx_summary else 0
    rx_peak_mbps = bits_to_mbps(rx_summary["max"]) if rx_summary else 0
    tx_avg_mbps = bits_to_mbps(tx_summary["avg"]) if tx_summary else 0
    rx_avg_mbps = bits_to_mbps(rx_summary["avg"]) if rx_summary else 0
    tx_p95_mbps = bits_to_mbps(tx_summary["p95"]) if tx_summary else 0
    rx_p95_mbps = bits_to_mbps(rx_summary["p95"]) if rx_summary else 0

    # 利用率计算：优先使用云监控直接提供的利用率
    if pct_summary:
        tx_peak_pct = pct_summary["max"]
        tx_avg_pct = pct_summary["avg"]
    elif bandwidth_limit > 0:
        tx_peak_pct = round(tx_peak_mbps / bandwidth_limit * 100, 2)
        tx_avg_pct = round(tx_avg_mbps / bandwidth_limit * 100, 2)
    else:
        tx_peak_pct = 0
        tx_avg_pct = 0

    rx_peak_pct = round(rx_peak_mbps / bandwidth_limit * 100, 2) if bandwidth_limit > 0 else 0

    has_drops = (drop_summary or {}).get("max", 0) > 0
    drop_max_pps = (drop_summary or {}).get("max", 0)

    risk_level = assess_risk(max(tx_peak_pct, rx_peak_pct), has_drops)

    instance["metrics"] = {
        "tx_peak_mbps": tx_peak_mbps,
        "rx_peak_mbps": rx_peak_mbps,
        "tx_avg_mbps": tx_avg_mbps,
        "rx_avg_mbps": rx_avg_mbps,
        "tx_p95_mbps": tx_p95_mbps,
        "rx_p95_mbps": rx_p95_mbps,
        "tx_peak_pct": tx_peak_pct,
        "tx_avg_pct": tx_avg_pct,
        "rx_peak_pct": rx_peak_pct,
        "has_ratelimit_drops": has_drops,
        "drop_max_pps": drop_max_pps,
    }
    instance["risk_level"] = risk_level
    instance["time_range"] = metrics_result.get("time_range", {})

    return instance


def main():
    parser = argparse.ArgumentParser(description="阿里云共享带宽包巡检（只读操作）")
    parser.add_argument("--regions", default=",".join(CN_REGIONS),
                        help="Region 列表，逗号分隔（默认全部中国大陆 Region）")
    parser.add_argument("--instance-ids", default="",
                        help="实例 ID 列表，逗号分隔（默认巡检全部）")
    parser.add_argument("--days", type=int, required=True,
                        help="巡检天数（必须指定）")
    parser.add_argument("--period", type=int, required=True,
                        help="监控数据聚合粒度（秒），如 60/300/900")
    args = parser.parse_args()

    regions = [r.strip() for r in args.regions.split(",") if r.strip()]
    instance_ids = [i.strip() for i in args.instance_ids.split(",") if i.strip()] if args.instance_ids else None

    all_instances = []
    errors = []

    for region in regions:
        instances = list_cbwp_instances(region, instance_ids)
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

    output = format_standard_output("common_bandwidth_package", "共享带宽包", args.days, regions, inspected, errors)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
