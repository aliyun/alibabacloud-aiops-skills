"""
inspect_nlb.py - 阿里云网络型负载均衡（NLB）巡检

查询 NLB 实例信息和云监控数据，评估流量、连接数水位。
所有 API 调用均为只读查询操作，不涉及任何写操作。

巡检指标说明:
  - LoadBalancerActiveFlowCount: 活跃连接数（Flow），当前正在处理的连接/流总数
  - LoadBalancerNewFlowCount: 新建连接数（Flow/秒），每秒新建立的连接/流数
  - LoadBalancerProcessedDataAmount: 处理数据量（bytes/s）
  - LoadBalancerInBitsRate: 入方向带宽（bits/s）
  - LoadBalancerOutBitsRate: 出方向带宽（bits/s）

NLB 说明:
  - NLB 使用 ROA 风格 API（nlb ListLoadBalancers）
  - 云监控 dimension key 为 loadBalancerId（不是 instanceId）
  - NLB 专注于四层（TCP/UDP）负载均衡，性能更高
  - 如果云监控无数据，可能是 NLB 未配置监听或无流量

用法:
    python3 inspect_nlb.py --regions cn-hangzhou,cn-shanghai --days 3
    python3 inspect_nlb.py --regions cn-hangzhou --instance-ids nlb-xxx --days 7
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

# NLB 云监控指标（namespace: acs_nlb）
# 注意: dimension key 是 loadBalancerId，不是 instanceId
NLB_METRICS = [
    "LoadBalancerActiveFlowCount",       # 活跃连接数
    "LoadBalancerNewFlowCount",          # 新建连接数 (个/秒)
    "LoadBalancerProcessedDataAmount",   # 处理数据量 (bytes/s)
    "LoadBalancerInBitsRate",            # 入方向带宽 (bits/s)
    "LoadBalancerOutBitsRate",           # 出方向带宽 (bits/s)
]

NAMESPACE = "acs_nlb"


def list_nlb_instances(region: str, instance_ids: list = None) -> list:
    """查询指定 Region 的 NLB 实例列表（只读操作）。
    NLB 使用 ROA 风格 API，分页使用 MaxResults + NextToken。
    """
    all_instances = []
    next_token = None

    while True:
        params = {"MaxResults": "50"}
        if next_token:
            params["NextToken"] = next_token

        result = call_with_retry("nlb", "ListLoadBalancers", params, region)
        if "error" in result:
            return [{"error": result["error"], "region": region}]

        lbs = result.get("LoadBalancers", [])
        if not lbs:
            break

        for lb in lbs:
            lb_id = lb.get("LoadBalancerId", "")
            if instance_ids and lb_id not in instance_ids:
                continue
            all_instances.append({
                "instance_id": lb_id,
                "instance_name": lb.get("LoadBalancerName", ""),
                "region": region,
                "status": lb.get("LoadBalancerStatus", ""),
                "address_type": lb.get("AddressType", ""),
                "vpc_id": lb.get("VpcId", ""),
                "dns_name": lb.get("DNSName", ""),
                "cross_zone_enabled": lb.get("CrossZoneEnabled", False),
                "creation_time": lb.get("CreateTime", ""),
                "bandwidth_package_id": lb.get("BandwidthPackageId", ""),
            })

        next_token = result.get("NextToken")
        if not next_token:
            break

    return all_instances


def inspect_instance(instance: dict, days: int, period: int) -> dict:
    """对单个 NLB 实例进行巡检（只读操作）。"""
    instance_id = instance["instance_id"]

    # NLB 的 CMS dimension key 是 loadBalancerId
    metrics_result = query_metrics_batch(
        NAMESPACE, NLB_METRICS, instance_id, days, period,
        dim_key="loadBalancerId"
    )
    metrics = metrics_result.get("metrics", {})

    active_flow_summary = metrics.get("LoadBalancerActiveFlowCount", {}).get("summary")
    new_flow_summary = metrics.get("LoadBalancerNewFlowCount", {}).get("summary")
    data_summary = metrics.get("LoadBalancerProcessedDataAmount", {}).get("summary")
    in_bps_summary = metrics.get("LoadBalancerInBitsRate", {}).get("summary")
    out_bps_summary = metrics.get("LoadBalancerOutBitsRate", {}).get("summary")

    active_flow_peak = active_flow_summary["max"] if active_flow_summary else 0
    active_flow_avg = active_flow_summary["avg"] if active_flow_summary else 0
    new_flow_peak = new_flow_summary["max"] if new_flow_summary else 0
    data_peak = data_summary["max"] if data_summary else 0

    rx_peak_mbps = bits_to_mbps(in_bps_summary["max"]) if in_bps_summary else 0
    tx_peak_mbps = bits_to_mbps(out_bps_summary["max"]) if out_bps_summary else 0
    rx_avg_mbps = bits_to_mbps(in_bps_summary["avg"]) if in_bps_summary else 0
    tx_avg_mbps = bits_to_mbps(out_bps_summary["avg"]) if out_bps_summary else 0

    # NLB 无固定带宽上限（全托管），主要关注丢包和状态
    # 基于实例状态评估
    status = instance.get("status", "")
    if status not in ("Active", "Provisioning", ""):
        risk_level = "critical"
    else:
        risk_level = "ok"

    instance["metrics"] = {
        "tx_peak_mbps": tx_peak_mbps,
        "rx_peak_mbps": rx_peak_mbps,
        "tx_avg_mbps": tx_avg_mbps,
        "rx_avg_mbps": rx_avg_mbps,
        "active_flow_peak": active_flow_peak,
        "active_flow_avg": round(active_flow_avg, 0),
        "new_flow_peak": new_flow_peak,
        "processed_data_peak_bytes": data_peak,
    }
    instance["risk_level"] = risk_level
    instance["time_range"] = metrics_result.get("time_range", {})

    return instance


def main():
    parser = argparse.ArgumentParser(description="阿里云网络型负载均衡（NLB）巡检（只读操作）")
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
        instances = list_nlb_instances(region, instance_ids)
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

    output = format_standard_output("nlb", "网络型负载均衡", args.days, regions, inspected, errors)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
