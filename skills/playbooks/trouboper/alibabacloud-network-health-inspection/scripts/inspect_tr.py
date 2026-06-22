"""
inspect_tr.py - 阿里云转发路由器（Transit Router）巡检

查询 CEN 下的转发路由器及其网络实例连接（VPC/VBR/VPN 连接），评估 TR 连接状态。
所有 API 调用均为只读查询操作，不涉及任何写操作。

TR 说明:
  - 转发路由器（Transit Router）是云企业网 CEN 的核心组件
  - 每个地域部署一个 TR，负责该地域内的网络实例互通
  - TR 连接类型: VPC 连接、VBR 连接、VPN 连接、跨地域连接
  - 同地域 VPC 互通不消耗跨地域带宽包额度
  - TR 流量监控通过关联的 CEN 带宽包和 VBR 监控查看

巡检内容:
  - TR 实例基本信息和状态
  - TR 下的 VPC 连接列表和状态
  - TR 下的 VBR 连接列表和状态
  - TR 路由表数量

用法:
    python3 inspect_tr.py --days 3
    python3 inspect_tr.py --cen-ids cen-xxx --regions cn-hangzhou --days 7
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inspect_common import (
    call_with_retry, CN_REGIONS, format_standard_output,
)


def list_cen_instances() -> list:
    """查询所有 CEN 实例（只读操作）。"""
    params = {"PageSize": "50"}
    cen_ids = []
    page = 1
    while True:
        params["PageNumber"] = str(page)
        result = call_with_retry("cbn", "DescribeCens", params, "cn-hangzhou")
        if "error" in result:
            return []
        cens = result.get("Cens", {}).get("Cen", [])
        if not cens:
            break
        for cen in cens:
            cen_ids.append(cen.get("CenId", ""))
        total = result.get("TotalCount", 0)
        if page * 50 >= total:
            break
        page += 1
    return cen_ids


def list_transit_routers(cen_id: str, region: str = None) -> list:
    """查询指定 CEN 下的转发路由器列表（只读操作）。"""
    params = {"CenId": cen_id}
    if region:
        params["RegionId"] = region
    result = call_with_retry("cbn", "ListTransitRouters", params, "cn-hangzhou")
    if "error" in result:
        return [{"error": result["error"], "cen_id": cen_id}]

    trs = result.get("TransitRouters", [])
    instances = []
    for tr in trs:
        tr_id = tr.get("TransitRouterId", "")
        instances.append({
            "instance_id": tr_id,
            "instance_name": tr.get("TransitRouterName", ""),
            "cen_id": cen_id,
            "region": tr.get("RegionId", ""),
            "status": tr.get("Status", ""),
            "type": tr.get("Type", ""),
            "creation_time": tr.get("CreationTime", ""),
            "ali_uid": tr.get("AliUid", ""),
        })
    return instances


def list_tr_vpc_attachments(tr_id: str, region: str) -> list:
    """查询 TR 的 VPC 连接列表（只读操作）。"""
    params = {"TransitRouterId": tr_id, "MaxResults": "50"}
    result = call_with_retry("cbn", "ListTransitRouterVpcAttachments", params, region)
    if "error" in result:
        return []

    attachments = result.get("TransitRouterAttachments", [])
    return [{
        "attachment_id": a.get("TransitRouterAttachmentId", ""),
        "attachment_name": a.get("TransitRouterAttachmentName", ""),
        "vpc_id": a.get("VpcId", ""),
        "vpc_owner_id": a.get("VpcOwnerId", ""),
        "status": a.get("Status", ""),
    } for a in attachments]


def list_tr_vbr_attachments(tr_id: str, region: str) -> list:
    """查询 TR 的 VBR 连接列表（只读操作）。"""
    params = {"TransitRouterId": tr_id, "MaxResults": "50"}
    result = call_with_retry("cbn", "ListTransitRouterVbrAttachments", params, region)
    if "error" in result:
        return []

    attachments = result.get("TransitRouterAttachments", [])
    return [{
        "attachment_id": a.get("TransitRouterAttachmentId", ""),
        "attachment_name": a.get("TransitRouterAttachmentName", ""),
        "vbr_id": a.get("VbrId", ""),
        "vbr_owner_id": a.get("VbrOwnerId", ""),
        "status": a.get("Status", ""),
    } for a in attachments]


def list_tr_route_tables(tr_id: str, region: str) -> int:
    """查询 TR 路由表数量（只读操作）。"""
    params = {"TransitRouterId": tr_id, "MaxResults": "50"}
    result = call_with_retry("cbn", "ListTransitRouterRouteTables", params, region)
    if "error" in result:
        return 0
    tables = result.get("TransitRouterRouteTables", [])
    return len(tables)


def inspect_instance(instance: dict) -> dict:
    """对单个 TR 实例进行巡检（只读操作）。"""
    tr_id = instance["instance_id"]
    region = instance["region"]

    # 查询 VPC 连接
    vpc_attachments = list_tr_vpc_attachments(tr_id, region)
    # 查询 VBR 连接
    vbr_attachments = list_tr_vbr_attachments(tr_id, region)
    # 查询路由表数量
    route_table_count = list_tr_route_tables(tr_id, region)

    # 检查连接状态
    abnormal_vpc = [a for a in vpc_attachments if a.get("status") != "Attached"]
    abnormal_vbr = [a for a in vbr_attachments if a.get("status") != "Attached"]

    status = instance.get("status", "")
    if status != "Active":
        risk_level = "critical"
    elif abnormal_vpc or abnormal_vbr:
        risk_level = "warning"
    else:
        risk_level = "ok"

    instance["vpc_attachments"] = vpc_attachments
    instance["vbr_attachments"] = vbr_attachments
    instance["route_table_count"] = route_table_count
    instance["risk_level"] = risk_level
    instance["note"] = "TR 流量监控请查看关联 CEN 带宽包和 VBR 的监控数据"

    return instance


def main():
    parser = argparse.ArgumentParser(description="阿里云转发路由器（TR）巡检（只读操作）")
    parser.add_argument("--cen-ids", default="",
                        help="CEN 实例 ID 列表，逗号分隔（默认查询全部 CEN 下的 TR）")
    parser.add_argument("--regions", default="",
                        help="Region 列表，逗号分隔（默认全部 Region）")
    parser.add_argument("--days", type=int, required=True,
                        help="巡检天数（必须指定）")
    args = parser.parse_args()

    cen_ids = [i.strip() for i in args.cen_ids.split(",") if i.strip()] if args.cen_ids else None
    regions_filter = [r.strip() for r in args.regions.split(",") if r.strip()] if args.regions else None

    # 如果没有指定 CEN ID，先查所有 CEN
    if not cen_ids:
        cen_ids = list_cen_instances()

    all_instances = []
    errors = []
    all_regions = set()

    for cen_id in cen_ids:
        trs = list_transit_routers(cen_id)
        for tr in trs:
            if "error" in tr:
                errors.append(tr)
                continue
            tr_region = tr.get("region", "")
            if regions_filter and tr_region not in regions_filter:
                continue
            all_regions.add(tr_region)
            all_instances.append(tr)

    inspected = []
    for inst in all_instances:
        try:
            result = inspect_instance(inst)
            inspected.append(result)
        except Exception as e:
            inst["error"] = str(e)
            inst["risk_level"] = "error"
            inspected.append(inst)

    output = format_standard_output(
        "transit_router", "转发路由器", args.days,
        sorted(all_regions) if all_regions else ["global"], inspected, errors
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
