"""
inspect_clb.py - 阿里云传统型负载均衡（CLB）巡检

查询 CLB 实例信息和云监控数据，评估流量、连接数和 QPS 水位。
所有 API 调用均为只读查询操作，不涉及任何写操作。

巡检指标说明:
  - InstanceTrafficRX: 入方向流量（bits/s），客户端流入 CLB 的带宽
  - InstanceTrafficTX: 出方向流量（bits/s），CLB 流出到客户端的带宽
  - InstanceActiveConnection: 活跃连接数，当前正在处理的连接总数
  - InstanceNewConnection: 新建连接数（个/秒），每秒新建立的连接数
  - InstanceQps: 每秒查询数（QPS），七层监听的请求处理速率
  - InstanceDropPacketRX: 入方向丢弃包数（packets/s）
  - InstanceDropPacketTX: 出方向丢弃包数（packets/s）

CLB 规格与性能上限相关，不同规格的最大连接数、CPS、QPS 不同。

用法:
    python3 inspect_clb.py --regions cn-hangzhou,cn-shanghai --days 3
    python3 inspect_clb.py --regions cn-hangzhou --instance-ids lb-xxx --days 7
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

# CLB 云监控指标（namespace: acs_slb_dashboard）
CLB_METRICS = [
    "InstanceTrafficRX",          # 入方向流量 (bits/s)
    "InstanceTrafficTX",          # 出方向流量 (bits/s)
    "InstanceActiveConnection",   # 活跃连接数
    "InstanceNewConnection",      # 新建连接数 (个/秒)
    "InstanceQps",                # QPS (七层监听)
    "InstanceDropPacketRX",       # 入方向丢弃包数 (packets/s)
    "InstanceDropPacketTX",       # 出方向丢弃包数 (packets/s)
]

NAMESPACE = "acs_slb_dashboard"


def list_clb_instances(region: str, instance_ids: list = None) -> list:
    """查询指定 Region 的 CLB 实例列表（只读操作）。"""
    params = {"PageSize": "50"}
    all_instances = []
    page = 1

    while True:
        params["PageNumber"] = str(page)
        result = call_with_retry("slb", "DescribeLoadBalancers", params, region)
        if "error" in result:
            return [{"error": result["error"], "region": region}]

        lbs = result.get("LoadBalancers", {}).get("LoadBalancer", [])
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
                "address": lb.get("Address", ""),
                "address_type": lb.get("AddressType", ""),
                "status": lb.get("LoadBalancerStatus", ""),
                "bandwidth": int(lb.get("Bandwidth", -1)),
                "internet_charge_type": lb.get("InternetChargeType", ""),
                "vpc_id": lb.get("VpcId", ""),
                "network_type": lb.get("NetworkType", ""),
                "spec": lb.get("LoadBalancerSpec", ""),
                "creation_time": lb.get("CreateTime", ""),
            })

        total = result.get("TotalCount", 0)
        if page * 50 >= total:
            break
        page += 1

    return all_instances


def inspect_instance(instance: dict, days: int, period: int) -> dict:
    """对单个 CLB 实例进行巡检（只读操作）。"""
    instance_id = instance["instance_id"]

    metrics_result = query_metrics_batch(NAMESPACE, CLB_METRICS, instance_id, days, period)
    metrics = metrics_result.get("metrics", {})

    tx_summary = metrics.get("InstanceTrafficTX", {}).get("summary")
    rx_summary = metrics.get("InstanceTrafficRX", {}).get("summary")
    active_conn_summary = metrics.get("InstanceActiveConnection", {}).get("summary")
    new_conn_summary = metrics.get("InstanceNewConnection", {}).get("summary")
    qps_summary = metrics.get("InstanceQps", {}).get("summary")
    drop_rx_summary = metrics.get("InstanceDropPacketRX", {}).get("summary")
    drop_tx_summary = metrics.get("InstanceDropPacketTX", {}).get("summary")

    tx_peak_mbps = bits_to_mbps(tx_summary["max"]) if tx_summary else 0
    rx_peak_mbps = bits_to_mbps(rx_summary["max"]) if rx_summary else 0
    tx_avg_mbps = bits_to_mbps(tx_summary["avg"]) if tx_summary else 0
    rx_avg_mbps = bits_to_mbps(rx_summary["avg"]) if rx_summary else 0

    active_conn_peak = active_conn_summary["max"] if active_conn_summary else 0
    active_conn_avg = active_conn_summary["avg"] if active_conn_summary else 0
    new_conn_peak = new_conn_summary["max"] if new_conn_summary else 0
    qps_peak = qps_summary["max"] if qps_summary else 0
    qps_avg = qps_summary["avg"] if qps_summary else 0

    drop_rx_max = (drop_rx_summary or {}).get("max", 0)
    drop_tx_max = (drop_tx_summary or {}).get("max", 0)
    has_drops = drop_rx_max > 0 or drop_tx_max > 0

    # 利用率评估（CLB 带宽上限，-1 表示按流量计费无上限）
    bandwidth_limit = instance.get("bandwidth", -1)
    if bandwidth_limit > 0:
        peak_pct = round(max(tx_peak_mbps, rx_peak_mbps) / bandwidth_limit * 100, 2)
    else:
        peak_pct = 0

    risk_level = assess_risk(peak_pct, has_drops)

    instance["metrics"] = {
        "tx_peak_mbps": tx_peak_mbps,
        "rx_peak_mbps": rx_peak_mbps,
        "tx_avg_mbps": tx_avg_mbps,
        "rx_avg_mbps": rx_avg_mbps,
        "active_conn_peak": active_conn_peak,
        "active_conn_avg": round(active_conn_avg, 0),
        "new_conn_peak": new_conn_peak,
        "qps_peak": qps_peak,
        "qps_avg": round(qps_avg, 0),
        "has_drops": has_drops,
        "drop_rx_max_pps": drop_rx_max,
        "drop_tx_max_pps": drop_tx_max,
        "bandwidth_utilization_pct": peak_pct,
    }
    instance["risk_level"] = risk_level
    instance["time_range"] = metrics_result.get("time_range", {})

    return instance


def main():
    parser = argparse.ArgumentParser(description="阿里云传统型负载均衡（CLB）巡检（只读操作）")
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
        instances = list_clb_instances(region, instance_ids)
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

    output = format_standard_output("clb", "传统型负载均衡", args.days, regions, inspected, errors)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
