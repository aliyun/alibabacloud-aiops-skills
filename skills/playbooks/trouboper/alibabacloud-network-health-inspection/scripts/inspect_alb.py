"""
inspect_alb.py - 阿里云应用型负载均衡（ALB）巡检

查询 ALB 实例信息和云监控数据，评估 QPS、HTTP 状态码和连接数水位。
所有 API 调用均为只读查询操作，不涉及任何写操作。

巡检指标说明:
  - LoadBalancerQPS: 每秒请求数（QPS），ALB 实例处理的 HTTP/HTTPS 请求速率
  - LoadBalancerHTTPCode2XX: 2XX 状态码数（个/秒），正常响应
  - LoadBalancerHTTPCode4XX: 4XX 状态码数（个/秒），客户端错误
  - LoadBalancerHTTPCode5XX: 5XX 状态码数（个/秒），服务端错误
  - LoadBalancerActiveConnection: 活跃连接数
  - LoadBalancerNewConnection: 新建连接数（个/秒）
  - LoadBalancerProcessedBytes: 处理字节数（bytes/s）

ALB 说明:
  - ALB 使用 ROA 风格 API（alb ListLoadBalancers）
  - 云监控 dimension key 为 loadBalancerId（不是 instanceId）
  - 如果云监控无数据，可能是 ALB 未配置监听或无流量

用法:
    python3 inspect_alb.py --regions cn-hangzhou,cn-shanghai --days 3
    python3 inspect_alb.py --regions cn-hangzhou --instance-ids alb-xxx --days 7
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inspect_common import (
    call_with_retry, query_metrics_batch,
    assess_risk, CN_REGIONS, format_standard_output,
)

# ALB 云监控指标（namespace: acs_alb）
# 注意: dimension key 是 loadBalancerId，不是 instanceId
ALB_METRICS = [
    "LoadBalancerQPS",               # QPS
    "LoadBalancerHTTPCode2XX",       # 2XX 状态码数 (个/秒)
    "LoadBalancerHTTPCode4XX",       # 4XX 状态码数 (个/秒)
    "LoadBalancerHTTPCode5XX",       # 5XX 状态码数 (个/秒)
    "LoadBalancerActiveConnection",  # 活跃连接数
    "LoadBalancerNewConnection",     # 新建连接数 (个/秒)
    "LoadBalancerProcessedBytes",    # 处理字节数 (bytes/s)
]

NAMESPACE = "acs_alb"


def list_alb_instances(region: str, instance_ids: list = None) -> list:
    """查询指定 Region 的 ALB 实例列表（只读操作）。
    ALB 使用 ROA 风格 API，分页使用 MaxResults + NextToken。
    """
    all_instances = []
    next_token = None

    while True:
        params = {"MaxResults": "50"}
        if next_token:
            params["NextToken"] = next_token

        result = call_with_retry("alb", "ListLoadBalancers", params, region)
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
                "business_status": lb.get("LoadBalancerBusinessStatus", ""),
                "address_type": lb.get("AddressType", ""),
                "vpc_id": lb.get("VpcId", ""),
                "dns_name": lb.get("DNSName", ""),
                "edition": lb.get("LoadBalancerEdition", ""),
                "creation_time": lb.get("CreateTime", ""),
                "address_allocated_mode": lb.get("AddressAllocatedMode", ""),
            })

        next_token = result.get("NextToken")
        if not next_token:
            break

    return all_instances


def inspect_instance(instance: dict, days: int, period: int) -> dict:
    """对单个 ALB 实例进行巡检（只读操作）。"""
    instance_id = instance["instance_id"]

    # ALB 的 CMS dimension key 是 loadBalancerId
    metrics_result = query_metrics_batch(
        NAMESPACE, ALB_METRICS, instance_id, days, period,
        dim_key="loadBalancerId"
    )
    metrics = metrics_result.get("metrics", {})

    qps_summary = metrics.get("LoadBalancerQPS", {}).get("summary")
    http2xx_summary = metrics.get("LoadBalancerHTTPCode2XX", {}).get("summary")
    http4xx_summary = metrics.get("LoadBalancerHTTPCode4XX", {}).get("summary")
    http5xx_summary = metrics.get("LoadBalancerHTTPCode5XX", {}).get("summary")
    active_conn_summary = metrics.get("LoadBalancerActiveConnection", {}).get("summary")
    new_conn_summary = metrics.get("LoadBalancerNewConnection", {}).get("summary")
    bytes_summary = metrics.get("LoadBalancerProcessedBytes", {}).get("summary")

    qps_peak = qps_summary["max"] if qps_summary else 0
    qps_avg = qps_summary["avg"] if qps_summary else 0
    http2xx_peak = http2xx_summary["max"] if http2xx_summary else 0
    http4xx_peak = http4xx_summary["max"] if http4xx_summary else 0
    http5xx_peak = http5xx_summary["max"] if http5xx_summary else 0
    active_conn_peak = active_conn_summary["max"] if active_conn_summary else 0
    new_conn_peak = new_conn_summary["max"] if new_conn_summary else 0
    bytes_peak = bytes_summary["max"] if bytes_summary else 0

    # 5XX 错误率评估
    # 注意: CMS 返回的 HTTP 状态码指标是每秒请求数（个/秒），可能是很小的浮点数
    # 当总请求数峰值 < 1 个/秒时，认为基本无流量，不计算错误率（避免误判）
    total_requests_peak = http2xx_peak + http4xx_peak + http5xx_peak
    if total_requests_peak >= 1:
        error_5xx_pct = round(http5xx_peak / total_requests_peak * 100, 2)
    else:
        error_5xx_pct = 0

    # 风险评估: 5XX 错误率 > 5% 为严重，> 1% 为告警
    if error_5xx_pct > 5:
        risk_level = "critical"
    elif error_5xx_pct > 1:
        risk_level = "warning"
    else:
        risk_level = "ok"

    # 运行状态异常强制升级为严重（Active / Provisioning 以外的状态）
    alb_status = instance.get("status", "")
    if alb_status and alb_status not in ("Active", "Provisioning"):
        risk_level = "critical"

    # 业务状态异常（如欠费锁定、残留锁定等）强制升级为严重
    biz_status = instance.get("business_status", "")
    if biz_status and biz_status not in ("Normal", ""):
        risk_level = "critical"

    instance["metrics"] = {
        "qps_peak": qps_peak,
        "qps_avg": round(qps_avg, 0),
        "http_2xx_peak": http2xx_peak,
        "http_4xx_peak": http4xx_peak,
        "http_5xx_peak": http5xx_peak,
        "error_5xx_pct": error_5xx_pct,
        "active_conn_peak": active_conn_peak,
        "new_conn_peak": new_conn_peak,
        "processed_bytes_peak": bytes_peak,
        "status_abnormal": alb_status not in ("Active", "Provisioning", ""),
        "biz_status_abnormal": biz_status not in ("Normal", ""),
    }
    instance["risk_level"] = risk_level
    instance["time_range"] = metrics_result.get("time_range", {})

    return instance


def main():
    parser = argparse.ArgumentParser(description="阿里云应用型负载均衡（ALB）巡检（只读操作）")
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
        instances = list_alb_instances(region, instance_ids)
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

    output = format_standard_output("alb", "应用型负载均衡", args.days, regions, inspected, errors)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
