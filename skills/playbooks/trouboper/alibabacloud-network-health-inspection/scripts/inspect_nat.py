"""
inspect_nat.py - 阿里云 NAT 网关巡检

查询 NAT 网关（增强型）实例信息和云监控数据，评估带宽和连接数水位。
所有 API 调用均为只读查询操作，不涉及任何写操作。

巡检指标说明:
  - BWRateInFromOutside: 从公网入方向带宽（bits/s），公网流入 NAT 网关的带宽
  - BWRateOutToOutside: 到公网出方向带宽（bits/s），NAT 网关流出到公网的带宽
  - BWRateInFromInside: 从内网入方向带宽（bits/s），VPC 内流入 NAT 网关的带宽
  - BWRateOutToInside: 到内网出方向带宽（bits/s），NAT 网关流出到 VPC 的带宽
  - SnatConnection: SNAT 并发连接数，当前活跃的 SNAT 连接总数
  - SessionLimitDropRate: 并发连接限速丢包（packets/s），因 SNAT 连接数达到规格上限导致的丢包
  - PPSRateInFromOutside: 从公网入方向包速率（packets/s）
  - PPSRateOutToOutside: 到公网出方向包速率（packets/s）

NAT 网关规格对应上限:
  - Small:    SNAT连接数 10万，带宽 1Gbps
  - Medium:   SNAT连接数 50万，带宽 5Gbps
  - Large:    SNAT连接数 200万，带宽 10Gbps
  - XLarge.1: SNAT连接数 500万，带宽 20Gbps

注意: 并发连接丢包指标是 SessionLimitDropRate，不是 SessionLimitDropConnection。

用法:
    python3 inspect_nat.py --regions cn-hangzhou,cn-shanghai --days 3
    python3 inspect_nat.py --regions cn-hangzhou --instance-ids ngw-xxx --days 7
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

# NAT 网关云监控指标（namespace: acs_nat_gateway）
NAT_METRICS = [
    "BWRateInFromOutside",       # 从公网入方向带宽 (bits/s)
    "BWRateOutToOutside",        # 到公网出方向带宽 (bits/s)
    "BWRateInFromInside",        # 从内网入方向带宽 (bits/s)
    "BWRateOutToInside",         # 到内网出方向带宽 (bits/s)
    "SnatConnection",            # SNAT 并发连接数
    "SessionLimitDropRate",      # 并发连接限速丢包 (packets/s)
    "PPSRateInFromOutside",      # 从公网入方向包速 (packets/s)
    "PPSRateOutToOutside",       # 到公网出方向包速 (packets/s)
]

NAMESPACE = "acs_nat_gateway"

# NAT 网关规格对应的 SNAT 连接数上限和带宽上限（增强型）
NAT_SPEC_LIMITS = {
    "Small":    {"snat_connections": 100000,  "bandwidth_mbps": 1000},
    "Medium":   {"snat_connections": 500000,  "bandwidth_mbps": 5000},
    "Large":    {"snat_connections": 2000000, "bandwidth_mbps": 10000},
    "XLarge.1": {"snat_connections": 5000000, "bandwidth_mbps": 20000},
}


def list_nat_instances(region: str, instance_ids: list = None) -> list:
    """查询指定 Region 的 NAT 网关实例列表（只读操作）。"""
    params = {"PageSize": "50"}
    all_instances = []
    page = 1

    while True:
        params["PageNumber"] = str(page)
        result = call_with_retry("vpc", "DescribeNatGateways", params, region)
        if "error" in result:
            return [{"error": result["error"], "region": region}]

        gateways = result.get("NatGateways", {}).get("NatGateway", [])
        if not gateways:
            break

        for gw in gateways:
            gw_id = gw.get("NatGatewayId", "")
            if instance_ids and gw_id not in instance_ids:
                continue
            spec = gw.get("Spec", gw.get("NatType", ""))
            nat_type = gw.get("NatType", "")
            all_instances.append({
                "instance_id": gw_id,
                "instance_name": gw.get("Name", ""),
                "region": region,
                "spec": spec,
                "nat_type": nat_type,
                "status": gw.get("Status", ""),
                "business_status": gw.get("BusinessStatus", ""),
                "vpc_id": gw.get("VpcId", ""),
                "creation_time": gw.get("CreationTime", ""),
                "internet_charge_type": gw.get("InternetChargeType", ""),
            })

        total = result.get("TotalCount", 0)
        if page * 50 >= total:
            break
        page += 1

    return all_instances


def inspect_instance(instance: dict, days: int, period: int) -> dict:
    """对单个 NAT 网关实例进行巡检（只读操作）。"""
    instance_id = instance["instance_id"]

    metrics_result = query_metrics_batch(NAMESPACE, NAT_METRICS, instance_id, days, period)
    metrics = metrics_result.get("metrics", {})

    # 提取关键指标
    tx_out_summary = metrics.get("BWRateOutToOutside", {}).get("summary")
    rx_in_summary = metrics.get("BWRateInFromOutside", {}).get("summary")
    snat_summary = metrics.get("SnatConnection", {}).get("summary")
    drop_summary = metrics.get("SessionLimitDropRate", {}).get("summary")

    tx_peak_mbps = bits_to_mbps(tx_out_summary["max"]) if tx_out_summary else 0
    rx_peak_mbps = bits_to_mbps(rx_in_summary["max"]) if rx_in_summary else 0
    tx_avg_mbps = bits_to_mbps(tx_out_summary["avg"]) if tx_out_summary else 0
    rx_avg_mbps = bits_to_mbps(rx_in_summary["avg"]) if rx_in_summary else 0
    tx_p95_mbps = bits_to_mbps(tx_out_summary["p95"]) if tx_out_summary else 0

    snat_peak = snat_summary["max"] if snat_summary else 0
    snat_avg = snat_summary["avg"] if snat_summary else 0

    has_session_drop = (drop_summary or {}).get("max", 0) > 0
    drop_max = (drop_summary or {}).get("max", 0)

    # 规格上限评估
    spec = instance.get("spec", "")
    spec_limits = NAT_SPEC_LIMITS.get(spec, {})
    snat_limit = spec_limits.get("snat_connections", 0)
    bw_limit = spec_limits.get("bandwidth_mbps", 0)

    snat_pct = round(snat_peak / snat_limit * 100, 2) if snat_limit > 0 else 0
    bw_pct = round(max(tx_peak_mbps, rx_peak_mbps) / bw_limit * 100, 2) if bw_limit > 0 else 0

    risk_level = assess_risk(max(bw_pct, snat_pct), has_session_drop)

    instance["metrics"] = {
        "tx_peak_mbps": tx_peak_mbps,
        "rx_peak_mbps": rx_peak_mbps,
        "tx_avg_mbps": tx_avg_mbps,
        "rx_avg_mbps": rx_avg_mbps,
        "tx_p95_mbps": tx_p95_mbps,
        "snat_connections_peak": snat_peak,
        "snat_connections_avg": round(snat_avg, 0),
        "snat_pct": snat_pct,
        "bw_pct": bw_pct,
        "has_session_drop": has_session_drop,
        "session_drop_max_pps": drop_max,
        "snat_limit": snat_limit,
        "bw_limit_mbps": bw_limit,
    }
    instance["risk_level"] = risk_level
    instance["time_range"] = metrics_result.get("time_range", {})

    return instance


def main():
    parser = argparse.ArgumentParser(description="阿里云 NAT 网关巡检（只读操作）")
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
        instances = list_nat_instances(region, instance_ids)
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

    output = format_standard_output("nat_gateway", "NAT网关", args.days, regions, inspected, errors)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
