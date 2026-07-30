"""Implementation detail."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from net_common import _call_with_retry, cidr_contains, cidr_prefix_len




def describe_vpcs(vpc_ids: list = None, region: str = None) -> dict:
    """Implementation detail."""
    params = {"PageSize": "50"}
    if vpc_ids:

        pass

    all_vpcs = []
    page_number = 1

    while True:
        params["PageNumber"] = str(page_number)
        result = _call_with_retry("vpc", "describe-vpcs", params, region)
        if "error" in result:
            return result

        vpcs = result.get("Vpcs", {}).get("Vpc", [])
        all_vpcs.extend(vpcs)

        total_count = result.get("TotalCount", 0)
        if len(all_vpcs) >= total_count or not vpcs:
            break
        page_number += 1

    if vpc_ids:
        id_set = set(vpc_ids)
        all_vpcs = [v for v in all_vpcs if v.get("VpcId") in id_set]

    summary = []
    for vpc in all_vpcs:
        summary.append({
            "VpcId": vpc.get("VpcId"),
            "VpcName": vpc.get("VpcName", ""),
            "CidrBlock": vpc.get("CidrBlock", ""),
            "SecondaryCidrBlocks": vpc.get("SecondaryCidrBlocks", {}).get("SecondaryCidrBlock", []),
            "Status": vpc.get("Status", ""),
            "RegionId": vpc.get("RegionId", ""),
            "VSwitchIds": vpc.get("VSwitchIds", {}).get("VSwitchId", []),
            "CenStatus": vpc.get("CenStatus", ""),
        })

    return {"vpcs": summary, "total": len(summary)}


def describe_vswitches(vpc_id: str = None, vswitch_ids: list = None,
                        region: str = None) -> dict:
    """Implementation detail."""
    params = {"PageSize": "50"}
    if vpc_id:
        params["VpcId"] = vpc_id
    if vswitch_ids and len(vswitch_ids) == 1:
        params["VSwitchId"] = vswitch_ids[0]

    result = _call_with_retry("vpc", "describe-vswitches", params, region)
    if "error" in result:
        return result

    vswitches = result.get("VSwitches", {}).get("VSwitch", [])

    if vswitch_ids and len(vswitch_ids) > 1:
        id_set = set(vswitch_ids)
        vswitches = [v for v in vswitches if v.get("VSwitchId") in id_set]

    summary = []
    for vsw in vswitches:
        summary.append({
            "VSwitchId": vsw.get("VSwitchId"),
            "VSwitchName": vsw.get("VSwitchName", ""),
            "VpcId": vsw.get("VpcId", ""),
            "CidrBlock": vsw.get("CidrBlock", ""),
            "ZoneId": vsw.get("ZoneId", ""),
            "Status": vsw.get("Status", ""),
            "RouteTableId": vsw.get("RouteTable", {}).get("RouteTableId", ""),
            "NetworkAclId": vsw.get("NetworkAclId", ""),
        })

    return {"vswitches": summary, "total": len(summary)}




def describe_route_table_list(vpc_id: str = None, route_table_id: str = None,
                               region: str = None) -> dict:
    """Implementation detail."""
    params = {"PageSize": "50"}
    if vpc_id:
        params["VpcId"] = vpc_id
    if route_table_id:
        params["RouteTableId"] = route_table_id

    result = _call_with_retry("vpc", "describe-route-table-list", params, region)
    if "error" in result:
        return result

    tables = result.get("RouterTableList", {}).get("RouterTableListType", [])

    summary = []
    for table in tables:
        summary.append({
            "RouteTableId": table.get("RouteTableId"),
            "RouteTableName": table.get("RouteTableName", ""),
            "VpcId": table.get("VpcId", ""),
            "RouteTableType": table.get("RouteTableType", ""),
            "VSwitchIds": table.get("VSwitchIds", {}).get("VSwitchId", []),
            "RouterId": table.get("RouterId", ""),
            "RouterType": table.get("RouterType", ""),
        })

    return {"route_tables": summary, "total": len(summary)}


def describe_route_entry_list(route_table_id: str, region: str = None) -> dict:
    """Implementation detail."""
    params = {
        "RouteTableId": route_table_id,
        "MaxResult": "100",
    }

    all_entries = []
    next_token = None

    while True:
        if next_token:
            params["NextToken"] = next_token

        result = _call_with_retry("vpc", "describe-route-entry-list", params, region)
        if "error" in result:
            return result

        entries = result.get("RouteEntrys", {}).get("RouteEntry", [])
        for entry in entries:
            nexthops = entry.get("NextHops", {}).get("NextHop", [])
            nexthop_info = []
            for nh in nexthops:
                nexthop_info.append({
                    "NextHopId": nh.get("NextHopId", ""),
                    "NextHopType": nh.get("NextHopType", ""),
                    "Enabled": nh.get("Enabled", 1),
                    "Weight": nh.get("Weight", 0),
                })

            all_entries.append({
                "DestinationCidrBlock": entry.get("DestinationCidrBlock", ""),
                "Type": entry.get("Type", ""),  # System / Custom / BGP
                "Origin": entry.get("Origin", ""),
                "Status": entry.get("Status", ""),
                "RouteEntryName": entry.get("RouteEntryName", ""),
                "NextHops": nexthop_info,
                "RouteEntryId": entry.get("RouteEntryId", ""),
            })

        next_token = result.get("NextToken", "")
        if not next_token:
            break

    return {"route_entries": all_entries, "total": len(all_entries), "route_table_id": route_table_id}


def route_lookup(route_entries: list, dst_ip: str) -> dict:
    """Implementation detail."""
    best_match = None
    best_prefix = -1

    for entry in route_entries:
        cidr = entry.get("DestinationCidrBlock", "")
        if not cidr:
            continue
        if cidr_contains(cidr, dst_ip):
            plen = cidr_prefix_len(cidr)
            if plen > best_prefix:
                best_prefix = plen
                best_match = entry

    if best_match:
        nexthops = best_match.get("NextHops", [])
        nh_desc = ", ".join(
            f"{nh['NextHopType']}({nh['NextHopId']})" for nh in nexthops
        ) if nexthops else "Local"

        status = best_match.get("Status", "")
        is_active = status in ("Available", "")
        origin = best_match.get("Origin", "")
        origin_label = f", 来源: {origin}" if origin else ""

        return {
            "matched": True,
            "route": best_match,
            "prefix_len": best_prefix,
            "next_hop_summary": nh_desc,
            "is_active": is_active,
            "origin": origin,
            "details": f"匹配路由: {best_match['DestinationCidrBlock']} → {nh_desc} "
                       f"(类型: {best_match['Type']}, 状态: {status or 'Active'}{origin_label})",
        }

    return {
        "matched": False,
        "route": None,
        "prefix_len": -1,
        "next_hop_summary": "",
        "is_active": False,
        "details": f"未找到到 {dst_ip} 的路由条目",
    }




def describe_network_acls(vpc_id: str = None, network_acl_id: str = None,
                           region: str = None) -> dict:
    """Implementation detail."""
    params = {"PageSize": "50"}
    if vpc_id:
        params["VpcId"] = vpc_id
    if network_acl_id:
        params["NetworkAclId"] = network_acl_id

    result = _call_with_retry("vpc", "describe-network-acls", params, region)
    if "error" in result:
        return result

    acls = result.get("NetworkAcls", {}).get("NetworkAcl", [])

    summary = []
    for acl in acls:
        ingress = acl.get("IngressAclEntries", {}).get("IngressAclEntry", [])
        egress = acl.get("EgressAclEntries", {}).get("EgressAclEntry", [])

        resources = acl.get("Resources", {}).get("Resource", [])
        bound_vswitches = [r.get("ResourceId", "") for r in resources
                          if r.get("ResourceType") == "VSwitch"]

        ingress_rules = []
        for idx, rule in enumerate(ingress, 1):
            ingress_rules.append({
                "EntryType": rule.get("EntryType", ""),
                "NetworkAclEntryName": rule.get("NetworkAclEntryName", ""),
                "Policy": rule.get("Policy", ""),
                "Protocol": rule.get("Protocol", ""),
                "SourceCidrIp": rule.get("SourceCidrIp", ""),
                "Port": rule.get("Port", "-1/-1"),
                "Order": idx,
            })

        egress_rules = []
        for idx, rule in enumerate(egress, 1):
            egress_rules.append({
                "EntryType": rule.get("EntryType", ""),
                "NetworkAclEntryName": rule.get("NetworkAclEntryName", ""),
                "Policy": rule.get("Policy", ""),
                "Protocol": rule.get("Protocol", ""),
                "DestinationCidrIp": rule.get("DestinationCidrIp", ""),
                "Port": rule.get("Port", "-1/-1"),
                "Order": idx,
            })

        summary.append({
            "NetworkAclId": acl.get("NetworkAclId"),
            "NetworkAclName": acl.get("NetworkAclName", ""),
            "VpcId": acl.get("VpcId", ""),
            "Status": acl.get("Status", ""),
            "BoundVSwitches": bound_vswitches,
            "IngressRules": ingress_rules,
            "EgressRules": egress_rules,
        })

    return {"network_acls": summary, "total": len(summary)}


def check_network_acl(acl: dict, direction: str, ip: str,
                       protocol: str = "", port: int = 0) -> dict:
    """Implementation detail."""
    rules = acl.get("IngressRules" if direction == "ingress" else "EgressRules", [])

    if not rules:
        return {
            "verdict": "allow",
            "matched_rule": None,
            "details": f"ACL {acl.get('NetworkAclId', '')} 无{direction}规则，默认允许",
        }

    for rule in rules:

        rule_proto = rule.get("Protocol", "all").upper()
        target_proto = protocol.upper() if protocol else ""
        if rule_proto != "ALL" and target_proto and rule_proto != target_proto:
            continue


        if direction == "ingress":
            cidr = rule.get("SourceCidrIp", "0.0.0.0/0")
        else:
            cidr = rule.get("DestinationCidrIp", "0.0.0.0/0")

        if ip and cidr and not cidr_contains(cidr, ip):
            continue


        port_range = rule.get("Port", "-1/-1")
        if protocol.upper() != "ICMP" and port > 0 and port_range != "-1/-1":
            try:
                parts = port_range.split("/")
                low, high = int(parts[0]), int(parts[1])
                if not (low <= port <= high):
                    continue
            except (ValueError, IndexError):
                pass


        policy = rule.get("Policy", "accept")
        return {
            "verdict": "allow" if policy.lower() == "accept" else "deny",
            "matched_rule": rule,
            "details": f"匹配 ACL 规则: 协议={rule_proto} 端口={port_range} "
                       f"IP={cidr} 策略={policy} 序号={rule.get('Order')}",
        }

    return {
        "verdict": "allow",
        "matched_rule": None,
        "details": "无匹配 ACL 规则，默认允许",
    }




def describe_nat_gateways(vpc_id: str = None, nat_gateway_id: str = None,
                           region: str = None) -> dict:
    """Implementation detail."""
    params = {"PageSize": "50"}
    if vpc_id:
        params["VpcId"] = vpc_id
    if nat_gateway_id:
        params["NatGatewayId"] = nat_gateway_id

    result = _call_with_retry("vpc", "describe-nat-gateways", params, region)
    if "error" in result:
        return result

    gateways = result.get("NatGateways", {}).get("NatGateway", [])

    summary = []
    for gw in gateways:
        summary.append({
            "NatGatewayId": gw.get("NatGatewayId", ""),
            "Name": gw.get("Name", ""),
            "VpcId": gw.get("VpcId", ""),
            "Status": gw.get("Status", ""),
            "NatType": gw.get("NatType", ""),
            "NetworkType": gw.get("NetworkType", ""),
            "VSwitchId": gw.get("NatGatewayPrivateInfo", {}).get("VSwitchId", ""),
            "PrivateIpAddress": gw.get("NatGatewayPrivateInfo", {}).get("PrivateIpAddress", ""),
            "ForwardTableIds": gw.get("ForwardTableIds", {}).get("ForwardTableId", []),
            "SnatTableIds": gw.get("SnatTableIds", {}).get("SnatTableId", []),
        })

    return {"nat_gateways": summary, "total": len(summary)}


def describe_forward_table_entries(forward_table_id: str,
                                    region: str = None) -> dict:
    """Implementation detail."""
    params = {
        "ForwardTableId": forward_table_id,
        "PageSize": "50",
    }

    all_entries = []
    page = 1

    while True:
        params["PageNumber"] = str(page)
        result = _call_with_retry("vpc", "describe-forward-table-entries", params, region)
        if "error" in result:
            return result

        entries = result.get("ForwardTableEntries", {}).get("ForwardTableEntry", [])
        for entry in entries:
            all_entries.append({
                "ForwardEntryId": entry.get("ForwardEntryId", ""),
                "ForwardTableId": entry.get("ForwardTableId", ""),
                "ExternalIp": entry.get("ExternalIp", ""),
                "ExternalPort": entry.get("ExternalPort", ""),
                "InternalIp": entry.get("InternalIp", ""),
                "InternalPort": entry.get("InternalPort", ""),
                "IpProtocol": entry.get("IpProtocol", ""),
                "Status": entry.get("Status", ""),
                "ForwardEntryName": entry.get("ForwardEntryName", ""),
            })

        total = result.get("TotalCount", 0)
        if page * 50 >= total:
            break
        page += 1

    return {"forward_entries": all_entries, "total": len(all_entries)}


def describe_snat_table_entries(snat_table_id: str,
                                 region: str = None) -> dict:
    """Implementation detail."""
    params = {
        "SnatTableId": snat_table_id,
        "PageSize": "50",
    }

    all_entries = []
    page = 1

    while True:
        params["PageNumber"] = str(page)
        result = _call_with_retry("vpc", "describe-snat-table-entries", params, region)
        if "error" in result:
            return result

        entries = result.get("SnatTableEntries", {}).get("SnatTableEntry", [])
        for entry in entries:
            all_entries.append({
                "SnatEntryId": entry.get("SnatEntryId", ""),
                "SnatTableId": entry.get("SnatTableId", ""),
                "SourceCIDR": entry.get("SourceCIDR", ""),
                "SourceVSwitchId": entry.get("SourceVSwitchId", ""),
                "SnatIp": entry.get("SnatIp", ""),
                "Status": entry.get("Status", ""),
                "SnatEntryName": entry.get("SnatEntryName", ""),
            })

        total = result.get("TotalCount", 0)
        if page * 50 >= total:
            break
        page += 1

    return {"snat_entries": all_entries, "total": len(all_entries)}


def check_nat_for_vpc(vpc_id: str, region: str = None) -> dict:
    """Implementation detail."""
    gw_result = describe_nat_gateways(vpc_id=vpc_id, region=region)
    if "error" in gw_result:
        return {"found": False, "error": gw_result["error"],
                "nat_gateways": [], "dnat_rules": [], "snat_rules": [],
                "details": f"NAT 网关查询失败: {gw_result['error']}"}

    gateways = gw_result.get("nat_gateways", [])
    if not gateways:
        return {"found": False, "nat_gateways": [], "dnat_rules": [], "snat_rules": [],
                "details": f"VPC {vpc_id} 未发现 NAT 网关"}

    all_dnat = []
    all_snat = []

    for gw in gateways:
        gw_id = gw.get("NatGatewayId", "")

        for ft_id in gw.get("ForwardTableIds", []):
            ft_result = describe_forward_table_entries(ft_id, region=region)
            if "error" not in ft_result:
                for entry in ft_result.get("forward_entries", []):
                    entry["NatGatewayId"] = gw_id
                    all_dnat.append(entry)

        for st_id in gw.get("SnatTableIds", []):
            st_result = describe_snat_table_entries(st_id, region=region)
            if "error" not in st_result:
                for entry in st_result.get("snat_entries", []):
                    entry["NatGatewayId"] = gw_id
                    all_snat.append(entry)

    details = f"发现 {len(gateways)} 个 NAT 网关, {len(all_dnat)} 条 DNAT 规则, {len(all_snat)} 条 SNAT 规则"

    return {
        "found": True,
        "nat_gateways": gateways,
        "dnat_rules": all_dnat,
        "snat_rules": all_snat,
        "details": details,
    }




def main():
    import argparse

    parser = argparse.ArgumentParser(description="VPC / 路由表 / 网络 ACL 诊断")
    sub = parser.add_subparsers(dest="action")

    # VPC
    p = sub.add_parser("vpcs", help="查询 VPC")
    p.add_argument("--vpc-ids", help="VPC ID，逗号分隔")
    p.add_argument("--region", help="地域")

    # VSwitch
    p = sub.add_parser("vswitches", help="查询交换机")
    p.add_argument("--vpc-id", help="VPC ID")
    p.add_argument("--vswitch-ids", help="交换机 ID，逗号分隔")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("routes", help="查询路由表和路由条目")
    p.add_argument("--vpc-id", help="VPC ID")
    p.add_argument("--route-table-id", help="路由表 ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("route-check", help="路由最长前缀匹配查找")
    p.add_argument("--route-table-id", required=True, help="路由表 ID")
    p.add_argument("--dst-ip", required=True, help="目的 IP")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("acls", help="查询网络 ACL")
    p.add_argument("--vpc-id", help="VPC ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("acl-check", help="网络 ACL 规则评估")
    p.add_argument("--vpc-id", required=True, help="VPC ID")
    p.add_argument("--vswitch-id", required=True, help="交换机 ID")
    p.add_argument("--direction", required=True, choices=["ingress", "egress"])
    p.add_argument("--ip", required=True, help="源/目的 IP")
    p.add_argument("--protocol", default="", help="协议")
    p.add_argument("--port", type=int, default=0, help="端口")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("nat-gateways", help="查询 NAT 网关")
    p.add_argument("--vpc-id", help="VPC ID")
    p.add_argument("--nat-gw-id", help="NAT 网关 ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("dnat-rules", help="查询 DNAT 端口转发规则")
    p.add_argument("--forward-table-id", required=True, help="DNAT 表 ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("snat-rules", help="查询 SNAT 规则")
    p.add_argument("--snat-table-id", required=True, help="SNAT 表 ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("nat-check", help="NAT 网关综合查询（含 DNAT/SNAT 规则）")
    p.add_argument("--vpc-id", required=True, help="VPC ID")
    p.add_argument("--region", help="地域")

    args = parser.parse_args()

    if args.action == "vpcs":
        vpc_ids = args.vpc_ids.split(",") if args.vpc_ids else None
        result = describe_vpcs(vpc_ids=vpc_ids, region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "vswitches":
        vsw_ids = args.vswitch_ids.split(",") if args.vswitch_ids else None
        result = describe_vswitches(vpc_id=args.vpc_id, vswitch_ids=vsw_ids,
                                     region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "routes":

        tables = describe_route_table_list(vpc_id=args.vpc_id,
                                            route_table_id=args.route_table_id,
                                            region=args.region)
        if "error" in tables:
            print(json.dumps(tables, ensure_ascii=False, indent=2))
            return


        output = {"route_tables": []}
        for table in tables.get("route_tables", []):
            tid = table["RouteTableId"]
            entries = describe_route_entry_list(tid, region=args.region)
            table["route_entries"] = entries.get("route_entries", []) if "error" not in entries else []
            if "error" in entries:
                table["error"] = entries["error"]
            output["route_tables"].append(table)

        print(json.dumps(output, ensure_ascii=False, indent=2))

    elif args.action == "route-check":
        entries_result = describe_route_entry_list(args.route_table_id, region=args.region)
        if "error" in entries_result:
            print(json.dumps(entries_result, ensure_ascii=False, indent=2))
            return
        result = route_lookup(entries_result["route_entries"], args.dst_ip)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "acls":
        result = describe_network_acls(vpc_id=args.vpc_id, region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "acl-check":
        acls_result = describe_network_acls(vpc_id=args.vpc_id, region=args.region)
        if "error" in acls_result:
            print(json.dumps(acls_result, ensure_ascii=False, indent=2))
            return


        target_acl = None
        for acl in acls_result.get("network_acls", []):
            if args.vswitch_id in acl.get("BoundVSwitches", []):
                target_acl = acl
                break

        if not target_acl:
            result = {
                "verdict": "allow",
                "details": f"VSwitch {args.vswitch_id} 未绑定网络 ACL，不阻断",
            }
        else:
            result = check_network_acl(
                target_acl, args.direction, args.ip, args.protocol, args.port
            )
            result["acl_id"] = target_acl.get("NetworkAclId", "")

        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "nat-gateways":
        result = describe_nat_gateways(vpc_id=args.vpc_id,
                                        nat_gateway_id=args.nat_gw_id,
                                        region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "dnat-rules":
        result = describe_forward_table_entries(args.forward_table_id,
                                                 region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "snat-rules":
        result = describe_snat_table_entries(args.snat_table_id,
                                              region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "nat-check":
        result = check_nat_for_vpc(args.vpc_id, region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(json.dumps({"error": "用户中断"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(json.dumps({"error": f"未处理的异常: {type(e).__name__}: {e}"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
