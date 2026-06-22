"""
inspect_ga.py - 阿里云全球加速（GA）巡检

查询全球加速实例信息和云监控数据，评估带宽使用情况。
所有 API 调用均为只读查询操作，不涉及任何写操作。

巡检指标说明:
  - GaInBps: 入方向带宽（bits/s），流入加速实例的网络带宽
  - GaOutBps: 出方向带宽（bits/s），流出加速实例的网络带宽
  - GaInPps: 入方向包速率（packets/s）
  - GaOutPps: 出方向包速率（packets/s）

GA 说明:
  - 全球加速（Global Accelerator）利用阿里云全球网络优化国际访问质量
  - 每个 GA 实例有带宽上限，超过上限将触发限速

用法:
    python3 inspect_ga.py --days 3
    python3 inspect_ga.py --instance-ids ga-xxx,ga-yyy --days 7
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inspect_common import (
    call_with_retry, query_metrics_batch,
    assess_risk, bits_to_mbps, format_standard_output,
)

# GA 云监控指标（namespace: acs_global_acceleration）
GA_METRICS = [
    "GaInBps",    # 入方向带宽 (bits/s)
    "GaOutBps",   # 出方向带宽 (bits/s)
    "GaInPps",    # 入方向包速率 (packets/s)
    "GaOutPps",   # 出方向包速率 (packets/s)
]

NAMESPACE = "acs_global_acceleration"


def list_ga_instances(instance_ids: list = None) -> list:
    """查询全球加速实例列表（GA 为全局资源）（只读操作）。"""
    params = {"PageSize": "50"}
    all_instances = []
    page = 1

    while True:
        params["PageNumber"] = str(page)
        result = call_with_retry("ga", "ListAccelerators", params, "cn-hangzhou")
        if "error" in result:
            return [{"error": result["error"], "region": "global"}]

        accelerators = result.get("Accelerators", [])
        if not accelerators:
            break

        for ga in accelerators:
            ga_id = ga.get("AcceleratorId", "")
            if instance_ids and ga_id not in instance_ids:
                continue

            # 提取带宽信息
            basic_bw = ga.get("BasicBandwidthPackage", {})
            cross_bw = ga.get("CrossDomainBandwidthPackage", {})

            all_instances.append({
                "instance_id": ga_id,
                "instance_name": ga.get("Name", ""),
                "region": "global",
                "state": ga.get("State", ""),
                "bandwidth": int(basic_bw.get("Bandwidth", 0)),
                "basic_bandwidth_package": basic_bw.get("InstanceId", ""),
                "cross_domain_bandwidth": int(cross_bw.get("Bandwidth", 0)) if cross_bw else 0,
                "cen_id": ga.get("CenId", ""),
                "creation_time": ga.get("CreateTime", ""),
                "spec": ga.get("Spec", ""),
            })

        total = result.get("TotalCount", 0)
        if page * 50 >= total:
            break
        page += 1

    return all_instances


def inspect_instance(instance: dict, days: int, period: int) -> dict:
    """对单个 GA 实例进行巡检（只读操作）。"""
    instance_id = instance["instance_id"]

    metrics_result = query_metrics_batch(NAMESPACE, GA_METRICS, instance_id, days, period)
    metrics = metrics_result.get("metrics", {})

    in_summary = metrics.get("GaInBps", {}).get("summary")
    out_summary = metrics.get("GaOutBps", {}).get("summary")
    in_pps_summary = metrics.get("GaInPps", {}).get("summary")
    out_pps_summary = metrics.get("GaOutPps", {}).get("summary")

    rx_peak_mbps = bits_to_mbps(in_summary["max"]) if in_summary else 0
    tx_peak_mbps = bits_to_mbps(out_summary["max"]) if out_summary else 0
    rx_avg_mbps = bits_to_mbps(in_summary["avg"]) if in_summary else 0
    tx_avg_mbps = bits_to_mbps(out_summary["avg"]) if out_summary else 0

    bandwidth_limit = instance.get("bandwidth", 0)
    peak_pct = round(max(tx_peak_mbps, rx_peak_mbps) / bandwidth_limit * 100, 2) if bandwidth_limit > 0 else 0

    # 状态评估
    state = instance.get("state", "")
    if state not in ("active", "Active", ""):
        risk_level = "critical"
    else:
        risk_level = assess_risk(peak_pct, False)

    instance["metrics"] = {
        "tx_peak_mbps": tx_peak_mbps,
        "rx_peak_mbps": rx_peak_mbps,
        "tx_avg_mbps": tx_avg_mbps,
        "rx_avg_mbps": rx_avg_mbps,
        "in_pps_peak": in_pps_summary["max"] if in_pps_summary else 0,
        "out_pps_peak": out_pps_summary["max"] if out_pps_summary else 0,
        "peak_utilization_pct": peak_pct,
    }
    instance["risk_level"] = risk_level
    instance["time_range"] = metrics_result.get("time_range", {})

    return instance


def main():
    parser = argparse.ArgumentParser(description="阿里云全球加速（GA）巡检（只读操作）")
    parser.add_argument("--instance-ids", default="",
                        help="GA 实例 ID 列表，逗号分隔（默认巡检全部）")
    parser.add_argument("--days", type=int, required=True,
                        help="巡检天数（必须指定）")
    parser.add_argument("--period", type=int, required=True,
                        help="监控数据聚合粒度（秒），如 60/300/900")
    args = parser.parse_args()

    instance_ids = [i.strip() for i in args.instance_ids.split(",") if i.strip()] if args.instance_ids else None

    all_instances = []
    errors = []

    instances = list_ga_instances(instance_ids)
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

    output = format_standard_output("global_accelerator", "全球加速", args.days, ["global"], inspected, errors)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
