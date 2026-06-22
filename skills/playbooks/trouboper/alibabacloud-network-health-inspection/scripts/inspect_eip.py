"""
inspect_eip.py - 阿里云弹性公网IP（EIP）巡检

查询 EIP 实例信息和云监控数据，评估带宽利用率和限速丢包情况。
所有 API 调用均为只读查询操作，不涉及任何写操作。

巡检指标说明:
  - net_tx.rate: 出方向带宽（bits/s），EIP 流出的网络带宽
  - net_rx.rate: 入方向带宽（bits/s），EIP 流入的网络带宽
  - out_ratelimit_drop_speed: 出方向限速丢包（packets/s），因带宽上限导致的出方向丢包
  - in_ratelimit_drop_speed: 入方向限速丢包（packets/s），因带宽上限导致的入方向丢包

用法:
    python3 inspect_eip.py --regions cn-hangzhou,cn-shanghai --days 3
    python3 inspect_eip.py --regions cn-hangzhou --instance-ids eip-xxx,eip-yyy --days 7
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

# EIP 云监控指标（namespace: acs_vpc_eip）
EIP_METRICS = [
    "net_tx.rate",               # 出方向带宽 (bits/s)
    "net_rx.rate",               # 入方向带宽 (bits/s)
    "out_ratelimit_drop_speed",  # 出方向限速丢包 (packets/s)
    "in_ratelimit_drop_speed",   # 入方向限速丢包 (packets/s)
]

NAMESPACE = "acs_vpc_eip"


def list_eip_instances(region: str, instance_ids: list = None) -> list:
    """查询指定 Region 的 EIP 实例列表（只读操作）。"""
    params = {"PageSize": "50"}
    all_instances = []
    page = 1

    while True:
        params["PageNumber"] = str(page)
        result = call_with_retry("vpc", "DescribeEipAddresses", params, region)
        if "error" in result:
            return [{"error": result["error"], "region": region}]

        eips = result.get("EipAddresses", {}).get("EipAddress", [])
        if not eips:
            break

        for eip in eips:
            eip_id = eip.get("AllocationId", "")
            if instance_ids and eip_id not in instance_ids:
                continue
            all_instances.append({
                "instance_id": eip_id,
                "instance_name": eip.get("Name", ""),
                "ip_address": eip.get("IpAddress", ""),
                "region": region,
                "bandwidth": int(eip.get("Bandwidth", 0)),
                "status": eip.get("Status", ""),
                "internet_charge_type": eip.get("InternetChargeType", ""),
                "isp": eip.get("ISP", ""),
                "bindable_type": eip.get("InstanceType", ""),
                "bindable_id": eip.get("InstanceId", ""),
                "creation_time": eip.get("AllocationTime", ""),
                "business_status": eip.get("BusinessStatus", ""),
                "bandwidth_package_id": eip.get("BandwidthPackageId", ""),
            })

        total = result.get("TotalCount", 0)
        if page * 50 >= total:
            break
        page += 1

    return all_instances


def inspect_instance(instance: dict, days: int, period: int) -> dict:
    """对单个 EIP 实例进行巡检（只读操作）。"""
    instance_id = instance["instance_id"]

    metrics_result = query_metrics_batch(NAMESPACE, EIP_METRICS, instance_id, days, period)
    metrics = metrics_result.get("metrics", {})

    # 提取关键指标
    tx_summary = metrics.get("net_tx.rate", {}).get("summary")
    rx_summary = metrics.get("net_rx.rate", {}).get("summary")
    out_drop_summary = metrics.get("out_ratelimit_drop_speed", {}).get("summary")
    in_drop_summary = metrics.get("in_ratelimit_drop_speed", {}).get("summary")

    bandwidth_limit = instance.get("bandwidth", 0)

    tx_peak_mbps = bits_to_mbps(tx_summary["max"]) if tx_summary else 0
    rx_peak_mbps = bits_to_mbps(rx_summary["max"]) if rx_summary else 0
    tx_avg_mbps = bits_to_mbps(tx_summary["avg"]) if tx_summary else 0
    rx_avg_mbps = bits_to_mbps(rx_summary["avg"]) if rx_summary else 0
    tx_p95_mbps = bits_to_mbps(tx_summary["p95"]) if tx_summary else 0
    rx_p95_mbps = bits_to_mbps(rx_summary["p95"]) if rx_summary else 0

    # 利用率计算
    tx_peak_pct = round(tx_peak_mbps / bandwidth_limit * 100, 2) if bandwidth_limit > 0 else 0
    rx_peak_pct = round(rx_peak_mbps / bandwidth_limit * 100, 2) if bandwidth_limit > 0 else 0

    out_drop_max = (out_drop_summary or {}).get("max", 0)
    in_drop_max = (in_drop_summary or {}).get("max", 0)
    has_drops = out_drop_max > 0 or in_drop_max > 0

    risk_level = assess_risk(max(tx_peak_pct, rx_peak_pct), has_drops)

    instance["metrics"] = {
        "tx_peak_mbps": tx_peak_mbps,
        "rx_peak_mbps": rx_peak_mbps,
        "tx_avg_mbps": tx_avg_mbps,
        "rx_avg_mbps": rx_avg_mbps,
        "tx_p95_mbps": tx_p95_mbps,
        "rx_p95_mbps": rx_p95_mbps,
        "tx_peak_pct": tx_peak_pct,
        "rx_peak_pct": rx_peak_pct,
        "has_drops": has_drops,
        "out_drop_max_pps": out_drop_max,
        "in_drop_max_pps": in_drop_max,
    }
    instance["risk_level"] = risk_level
    instance["time_range"] = metrics_result.get("time_range", {})

    return instance


def main():
    parser = argparse.ArgumentParser(description="阿里云弹性公网IP（EIP）巡检（只读操作）")
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
        instances = list_eip_instances(region, instance_ids)
        for inst in instances:
            if "error" in inst:
                errors.append(inst)
            else:
                all_instances.append(inst)

    # 巡检每个实例
    inspected = []
    for inst in all_instances:
        try:
            result = inspect_instance(inst, args.days, args.period)
            inspected.append(result)
        except Exception as e:
            inst["error"] = str(e)
            inst["risk_level"] = "error"
            inspected.append(inst)

    output = format_standard_output("eip", "弹性公网IP", args.days, regions, inspected, errors)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
