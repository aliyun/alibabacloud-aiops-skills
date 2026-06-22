"""
inspect_physconn.py - 阿里云物理专线巡检

查询物理专线实例基本信息（带宽上限、状态等）。
物理专线本身无云监控指标，流量/丢包通过关联的 VBR 监控查看。
所有 API 调用均为只读查询操作，不涉及任何写操作。

巡检内容:
  - 物理专线实例 ID、名称、带宽上限
  - 接入点、端口类型、运营商信息
  - 实例状态和业务状态
  - 风险评估：仅基于实例状态判定（Enabled + Normal = 正常）

注意: 物理专线的流量监控需通过关联的 VBR 查看（inspect_vbr.py）

用法:
    python3 inspect_physconn.py --regions cn-hangzhou,cn-shanghai
    python3 inspect_physconn.py --regions cn-hangzhou --instance-ids pc-xxx --days 3
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inspect_common import call_with_retry, CN_REGIONS, format_standard_output


def list_physconn_instances(region: str, instance_ids: list = None) -> list:
    """查询指定 Region 的物理专线实例列表（只读操作）。"""
    params = {"PageSize": "50"}
    all_instances = []
    page = 1

    while True:
        params["PageNumber"] = str(page)
        result = call_with_retry("vpc", "DescribePhysicalConnections", params, region)
        if "error" in result:
            return [{"error": result["error"], "region": region}]

        connections = result.get("PhysicalConnectionSet", {}).get("PhysicalConnectionType", [])
        if not connections:
            break

        for conn in connections:
            conn_id = conn.get("PhysicalConnectionId", "")
            if instance_ids and conn_id not in instance_ids:
                continue
            all_instances.append({
                "instance_id": conn_id,
                "instance_name": conn.get("Name", ""),
                "region": region,
                "bandwidth_limit": int(conn.get("Bandwidth", 0)),
                "status": conn.get("Status", ""),
                "business_status": conn.get("BusinessStatus", ""),
                "access_point_id": conn.get("AccessPointId", ""),
                "line_operator": conn.get("LineOperator", ""),
                "port_type": conn.get("PortType", ""),
                "creation_time": conn.get("CreationTime", ""),
                "enabled_time": conn.get("EnabledTime", ""),
                "spec": conn.get("Spec", ""),
                "redundant_physical_connection_id": conn.get("RedundantPhysicalConnectionId", ""),
            })

        total = result.get("TotalCount", 0)
        if page * 50 >= total:
            break
        page += 1

    return all_instances


def inspect_instance(instance: dict) -> dict:
    """对单个物理专线实例进行巡检（只读操作，仅基本信息，不查云监控）。"""
    status = instance.get("status", "")
    biz_status = instance.get("business_status", "")

    # 风险评估：仅基于实例状态
    if status != "Enabled":
        risk_level = "critical"
    elif biz_status != "Normal":
        risk_level = "warning"
    else:
        risk_level = "ok"

    instance["risk_level"] = risk_level
    instance["note"] = "物理专线流量监控请查看关联 VBR 的监控数据"
    return instance


def main():
    parser = argparse.ArgumentParser(description="阿里云物理专线巡检（只读操作）")
    parser.add_argument("--regions", default=",".join(CN_REGIONS),
                        help="Region 列表，逗号分隔（默认全部中国大陆 Region）")
    parser.add_argument("--instance-ids", default="",
                        help="实例 ID 列表，逗号分隔（默认巡检全部）")
    parser.add_argument("--days", type=int, required=True,
                        help="巡检天数（必须指定）")
    args = parser.parse_args()

    regions = [r.strip() for r in args.regions.split(",") if r.strip()]
    instance_ids = [i.strip() for i in args.instance_ids.split(",") if i.strip()] if args.instance_ids else None

    all_instances = []
    errors = []

    for region in regions:
        instances = list_physconn_instances(region, instance_ids)
        for inst in instances:
            if "error" in inst:
                errors.append(inst)
            else:
                all_instances.append(inst)

    inspected = []
    for inst in all_instances:
        try:
            result = inspect_instance(inst)
            inspected.append(result)
        except Exception as e:
            inst["error"] = str(e)
            inst["risk_level"] = "error"
            inspected.append(inst)

    output = format_standard_output("physical_connection", "物理专线", args.days, regions, inspected, errors)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
