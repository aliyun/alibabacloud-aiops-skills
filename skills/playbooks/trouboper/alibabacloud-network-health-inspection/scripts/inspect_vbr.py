"""
inspect_vbr.py - 阿里云 VBR（虚拟边界路由器）巡检

查询 VBR 实例信息和云监控数据，评估带宽水位和健康检查状态。
所有 API 调用均为只读查询操作，不涉及任何写操作。

巡检指标说明:
  - RateInFromIDCToVpc: IDC→VPC 入方向带宽（bits/s），从 IDC 流入阿里云 VPC 的带宽
  - RateOutFromVpcToIDC: VPC→IDC 出方向带宽（bits/s），从阿里云 VPC 流出到 IDC 的带宽
  - VbrHealthyCheckLatency: 健康检查延迟（微秒），需除以 1000 转为毫秒
  - VbrHealthyCheckLossRate: 健康检查丢包率（%），已为百分比值
  - PkgsDropInFromIDCToVpc: IDC→VPC 丢包数（packets/s）
  - PkgsDropOutFromVpcToIDC: VPC→IDC 丢包数（packets/s）

重要提示:
  - VBR 的 CMS namespace 是 acs_physical_connection，不是 acs_express_connect
  - VbrHealthyCheckLatency 单位是微秒(us)，需要除以1000转换为毫秒(ms)
  - VbrHealthyCheckLossRate 返回值已经是百分比，不需要再乘以100

VBR 风险评估标准:
  - 健康检查丢包率 > 5% 或延迟 > 100ms: 严重
  - 健康检查丢包率 > 1% 或延迟 > 50ms: 告警
  - 状态非 Active: 严重

用法:
    python3 inspect_vbr.py --regions cn-hangzhou,cn-shanghai --days 3
    python3 inspect_vbr.py --regions cn-hangzhou --instance-ids vbr-xxx --days 7
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inspect_common import (
    call_with_retry, query_metrics_batch,
    bits_to_mbps, CN_REGIONS, format_standard_output,
)

# VBR 云监控指标（namespace: acs_physical_connection，不是 acs_express_connect）
VBR_METRICS = [
    "RateInFromIDCToVpc",         # IDC→VPC 入方向带宽 (bits/s)
    "RateOutFromVpcToIDC",        # VPC→IDC 出方向带宽 (bits/s)
    "VbrHealthyCheckLatency",     # 健康检查延迟 (微秒 us)
    "VbrHealthyCheckLossRate",    # 健康检查丢包率 (% 已为百分比)
    "PkgsDropInFromIDCToVpc",     # IDC→VPC 丢包数 (packets/s)
    "PkgsDropOutFromVpcToIDC",    # VPC→IDC 丢包数 (packets/s)
]

NAMESPACE = "acs_physical_connection"


def list_vbr_instances(region: str, instance_ids: list = None) -> list:
    """查询指定 Region 的 VBR 实例列表（只读操作）。"""
    params = {"PageSize": "50"}
    all_instances = []
    page = 1

    while True:
        params["PageNumber"] = str(page)
        result = call_with_retry("vpc", "DescribeVirtualBorderRouters", params, region)
        if "error" in result:
            return [{"error": result["error"], "region": region}]

        vbrs = result.get("VirtualBorderRouterSet", {}).get("VirtualBorderRouterType", [])
        if not vbrs:
            break

        for vbr in vbrs:
            vbr_id = vbr.get("VbrId", "")
            if instance_ids and vbr_id not in instance_ids:
                continue
            all_instances.append({
                "instance_id": vbr_id,
                "instance_name": vbr.get("Name", ""),
                "region": region,
                "status": vbr.get("Status", ""),
                "physical_connection_id": vbr.get("PhysicalConnectionId", ""),
                "vlan_id": vbr.get("VlanId", ""),
                "local_gateway_ip": vbr.get("LocalGatewayIp", ""),
                "peer_gateway_ip": vbr.get("PeerGatewayIp", ""),
                "peering_subnet_mask": vbr.get("PeeringSubnetMask", ""),
                "creation_time": vbr.get("CreationTime", ""),
                "physical_connection_owner_uid": vbr.get("PhysicalConnectionOwnerUid", ""),
                "physical_connection_status": vbr.get("PhysicalConnectionStatus", ""),
                "physical_connection_business_status": vbr.get("PhysicalConnectionBusinessStatus", ""),
            })

        total = result.get("TotalCount", 0)
        if page * 50 >= total:
            break
        page += 1

    return all_instances


def assess_vbr_risk(tx_peak_pct: float, rx_peak_pct: float,
                    loss_rate: float, latency_ms: float,
                    has_drops: bool) -> str:
    """VBR 专用风险评估。"""
    # 健康检查维度
    if loss_rate > 5 or latency_ms > 100:
        return "critical"
    if loss_rate > 1 or latency_ms > 50:
        return "warning"

    # 带宽维度
    peak_pct = max(tx_peak_pct, rx_peak_pct)
    if has_drops or peak_pct >= 90:
        return "critical"
    if peak_pct >= 70:
        return "warning"

    return "ok"


def inspect_instance(instance: dict, days: int, period: int) -> dict:
    """对单个 VBR 实例进行巡检（只读操作）。"""
    instance_id = instance["instance_id"]

    metrics_result = query_metrics_batch(NAMESPACE, VBR_METRICS, instance_id, days, period)
    metrics = metrics_result.get("metrics", {})

    in_summary = metrics.get("RateInFromIDCToVpc", {}).get("summary")
    out_summary = metrics.get("RateOutFromVpcToIDC", {}).get("summary")
    latency_summary = metrics.get("VbrHealthyCheckLatency", {}).get("summary")
    loss_summary = metrics.get("VbrHealthyCheckLossRate", {}).get("summary")
    drop_in_summary = metrics.get("PkgsDropInFromIDCToVpc", {}).get("summary")
    drop_out_summary = metrics.get("PkgsDropOutFromVpcToIDC", {}).get("summary")

    rx_peak_mbps = bits_to_mbps(in_summary["max"]) if in_summary else 0
    tx_peak_mbps = bits_to_mbps(out_summary["max"]) if out_summary else 0
    rx_avg_mbps = bits_to_mbps(in_summary["avg"]) if in_summary else 0
    tx_avg_mbps = bits_to_mbps(out_summary["avg"]) if out_summary else 0
    rx_p95_mbps = bits_to_mbps(in_summary["p95"]) if in_summary else 0
    tx_p95_mbps = bits_to_mbps(out_summary["p95"]) if out_summary else 0

    # 健康检查时延：单位是微秒(us)，转换为毫秒(ms)
    latency_peak = round(latency_summary["max"] / 1000, 2) if latency_summary else 0
    latency_avg = round(latency_summary["avg"] / 1000, 2) if latency_summary else 0
    # 健康检查丢包率：API 返回值已为百分比
    loss_peak = round(loss_summary["max"], 2) if loss_summary else 0
    loss_avg = round(loss_summary["avg"], 2) if loss_summary else 0

    # 丢包数 (packets/s)
    drop_in_peak = drop_in_summary["max"] if drop_in_summary else 0
    drop_out_peak = drop_out_summary["max"] if drop_out_summary else 0
    has_drops = (drop_in_peak > 0 or drop_out_peak > 0)

    # VBR 带宽上限取决于关联的物理专线，此处仅展示绝对值
    tx_peak_pct = 0
    rx_peak_pct = 0

    risk_level = assess_vbr_risk(tx_peak_pct, rx_peak_pct, loss_peak, latency_peak, has_drops)

    # VBR 状态非 active 时强制 critical
    if instance.get("status", "").lower() not in ("active", ""):
        risk_level = "critical"

    instance["metrics"] = {
        "tx_peak_mbps": tx_peak_mbps,
        "rx_peak_mbps": rx_peak_mbps,
        "tx_avg_mbps": tx_avg_mbps,
        "rx_avg_mbps": rx_avg_mbps,
        "tx_p95_mbps": tx_p95_mbps,
        "rx_p95_mbps": rx_p95_mbps,
        "health_check_latency_peak_ms": latency_peak,
        "health_check_latency_avg_ms": latency_avg,
        "health_check_loss_peak_pct": loss_peak,
        "health_check_loss_avg_pct": loss_avg,
        "drop_in_peak_pps": drop_in_peak,
        "drop_out_peak_pps": drop_out_peak,
    }
    instance["risk_level"] = risk_level
    instance["time_range"] = metrics_result.get("time_range", {})

    return instance


def main():
    parser = argparse.ArgumentParser(description="阿里云 VBR 巡检（只读操作）")
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
        instances = list_vbr_instances(region, instance_ids)
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

    output = format_standard_output("virtual_border_router", "VBR", args.days, regions, inspected, errors)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
