"""Implementation detail."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from net_common import _call_with_retry, cidr_contains, cidr_prefix_len




def describe_vpn_gateways(vpc_id: str = None, region: str = None) -> dict:
    """Implementation detail."""
    params = {"PageSize": "50"}
    if vpc_id:
        params["VpcId"] = vpc_id

    result = _call_with_retry("vpc", "describe-vpn-gateways", params, region)
    if "error" in result:
        return result

    gateways = result.get("VpnGateways", {}).get("VpnGateway", [])

    summary = []
    for gw in gateways:
        summary.append({
            "VpnGatewayId": gw.get("VpnGatewayId"),
            "Name": gw.get("Name", ""),
            "VpcId": gw.get("VpcId", ""),
            "Status": gw.get("Status", ""),
            "BusinessStatus": gw.get("BusinessStatus", ""),
            "InternetIp": gw.get("InternetIp", ""),
            "Spec": gw.get("Spec", ""),
            "IpsecVpn": gw.get("IpsecVpn", ""),
            "SslVpn": gw.get("SslVpn", ""),
        })

    return {"vpn_gateways": summary, "total": len(summary)}


def describe_vpn_connections(vpn_gateway_id: str = None, region: str = None) -> dict:
    """Implementation detail."""
    params = {"PageSize": "50"}
    if vpn_gateway_id:
        params["VpnGatewayId"] = vpn_gateway_id

    result = _call_with_retry("vpc", "describe-vpn-connections", params, region)
    if "error" in result:
        return result

    connections = result.get("VpnConnections", {}).get("VpnConnection", [])

    summary = []
    for conn in connections:
        ike_config = conn.get("IkeConfig", {})
        ipsec_config = conn.get("IpsecConfig", {})
        vco_health = conn.get("VcoHealthCheck", {})


        local_subnet = conn.get("LocalSubnet", "")
        remote_subnet = conn.get("RemoteSubnet", "")


        tunnel_options = []
        tunnel_status_list = []
        tunnel_specs = conn.get("TunnelOptionsSpecification", {}).get("TunnelOptions", [])
        for tun in tunnel_specs:
            tun_ike = tun.get("TunnelIkeConfig", {})
            tun_ipsec = tun.get("TunnelIpsecConfig", {})
            tun_bgp = tun.get("TunnelBgpConfig", {})

            tunnel_info = {
                "TunnelId": tun.get("TunnelId", ""),
                "Role": tun.get("Role", ""),          # master / slave
                "State": tun.get("State", ""),        # active / inactive
                "Status": tun.get("Status", ""),      # ipsec_sa_established / ike_sa_not_established / ...
                "InternetIp": tun.get("InternetIp", ""),
                "CustomerGatewayId": tun.get("CustomerGatewayId", ""),
                "ZoneNo": tun.get("ZoneNo", ""),
                "EnableDpd": tun.get("EnableDpd", False),
                "EnableNatTraversal": tun.get("EnableNatTraversal", False),
                "TunnelIkeConfig": {
                    "IkeVersion": tun_ike.get("IkeVersion", ""),
                    "IkeMode": tun_ike.get("IkeMode", ""),
                    "IkeAuthAlg": tun_ike.get("IkeAuthAlg", ""),
                    "IkeEncAlg": tun_ike.get("IkeEncAlg", ""),
                    "IkePfs": tun_ike.get("IkePfs", ""),
                    "IkeLifetime": tun_ike.get("IkeLifetime", ""),
                    "LocalId": tun_ike.get("LocalId", ""),
                    "RemoteId": tun_ike.get("RemoteId", ""),
                    "Psk": tun_ike.get("Psk", ""),
                },
                "TunnelIpsecConfig": {
                    "IpsecAuthAlg": tun_ipsec.get("IpsecAuthAlg", ""),
                    "IpsecEncAlg": tun_ipsec.get("IpsecEncAlg", ""),
                    "IpsecPfs": tun_ipsec.get("IpsecPfs", ""),
                    "IpsecLifetime": tun_ipsec.get("IpsecLifetime", ""),
                },
                "TunnelBgpConfig": tun_bgp,
            }
            tunnel_options.append(tunnel_info)


            is_up = tun.get("State") == "active" and tun.get("Status") == "ipsec_sa_established"
            tunnel_status_list.append({
                "TunnelId": tun.get("TunnelId", ""),
                "Role": tun.get("Role", ""),
                "State": tun.get("State", ""),
                "Status": tun.get("Status", ""),
                "is_up": is_up,
            })

        summary.append({
            "VpnConnectionId": conn.get("VpnConnectionId"),
            "Name": conn.get("Name", ""),
            "VpnGatewayId": conn.get("VpnGatewayId", ""),
            "CustomerGatewayId": conn.get("CustomerGatewayId", ""),
            "State": conn.get("State", ""),
            "LocalSubnet": local_subnet,
            "RemoteSubnet": remote_subnet,
            "IkeConfig": {
                "IkeVersion": ike_config.get("IkeVersion", ""),
                "IkeMode": ike_config.get("IkeMode", ""),
                "IkeAuthAlg": ike_config.get("IkeAuthAlg", ""),
                "IkeEncAlg": ike_config.get("IkeEncAlg", ""),
                "IkeLifetime": ike_config.get("IkeLifetime", ""),
                "LocalId": ike_config.get("LocalId", ""),
                "RemoteId": ike_config.get("RemoteId", ""),
            },
            "IpsecConfig": {
                "IpsecAuthAlg": ipsec_config.get("IpsecAuthAlg", ""),
                "IpsecEncAlg": ipsec_config.get("IpsecEncAlg", ""),
                "IpsecLifetime": ipsec_config.get("IpsecLifetime", ""),
                "IpsecPfs": ipsec_config.get("IpsecPfs", ""),
            },
            "HealthCheck": {
                "Enable": vco_health.get("Enable", ""),
                "Sip": vco_health.get("Sip", ""),
                "Dip": vco_health.get("Dip", ""),
                "Status": vco_health.get("Status", ""),
            },
            "EffectImmediately": conn.get("EffectImmediately", False),
            "EnableNatTraversal": conn.get("EnableNatTraversal", False),
            "EnableDpd": conn.get("EnableDpd", False),
            "TunnelDetails": tunnel_options,
            "TunnelStatusSummary": tunnel_status_list,
        })

    return {"vpn_connections": summary, "total": len(summary)}


def check_vpn_for_vpc(vpc_id: str, region: str = None) -> dict:
    """Implementation detail."""

    gw_result = describe_vpn_gateways(vpc_id=vpc_id, region=region)
    if "error" in gw_result:
        return gw_result

    gateways = gw_result.get("vpn_gateways", [])
    if not gateways:
        return {
            "found": False,
            "details": f"VPC {vpc_id} 未关联 VPN 网关",
        }


    all_connections = []
    connection_errors = []
    for gw in gateways:
        gw_id = gw["VpnGatewayId"]
        conn_result = describe_vpn_connections(vpn_gateway_id=gw_id, region=region)
        if "error" not in conn_result:
            connections = conn_result.get("vpn_connections", [])
            all_connections.extend(connections)
        else:
            connection_errors.append({
                "VpnGatewayId": gw_id,
                "error": conn_result["error"],
            })


    total_up = 0
    total_down = 0
    tunnel_summary = []
    for conn in all_connections:
        for tun in conn.get("TunnelStatusSummary", []):
            tunnel_summary.append(tun)
            if tun.get("is_up"):
                total_up += 1
            else:
                total_down += 1

    return {
        "found": True,
        "vpn_gateways": gateways,
        "vpn_connections": all_connections,
        "connection_errors": connection_errors,
        "tunnel_summary": tunnel_summary,
        "active_count": total_up,
        "down_count": total_down,
        "details": f"找到 {len(gateways)} 个 VPN 网关, "
                   f"{len(tunnel_summary)} 条隧道 "
                   f"(活跃: {total_up}, 断开: {total_down})",
    }




def describe_virtual_border_routers(region: str = None) -> dict:
    """Implementation detail."""
    params = {"PageSize": "50"}

    result = _call_with_retry("vpc", "describe-virtual-border-routers", params, region)
    if "error" in result:
        return result

    vbrs = result.get("VirtualBorderRouterSet", {}).get("VirtualBorderRouterType", [])

    summary = []
    for vbr in vbrs:
        summary.append({
            "VbrId": vbr.get("VbrId"),
            "Name": vbr.get("Name", ""),
            "Status": vbr.get("Status", ""),
            "PhysicalConnectionId": vbr.get("PhysicalConnectionId", ""),
            "PhysicalConnectionStatus": vbr.get("PhysicalConnectionStatus", ""),
            "PhysicalConnectionBusinessStatus": vbr.get("PhysicalConnectionBusinessStatus", ""),
            "VlanId": vbr.get("VlanId", ""),
            "LocalGatewayIp": vbr.get("LocalGatewayIp", ""),
            "PeerGatewayIp": vbr.get("PeerGatewayIp", ""),
            "PeeringSubnetMask": vbr.get("PeeringSubnetMask", ""),
            "VpcId": vbr.get("VpcId", ""),
            "CircuitCode": vbr.get("CircuitCode", ""),
            "LocalIpv6GatewayIp": vbr.get("LocalIpv6GatewayIp", ""),
            "PeerIpv6GatewayIp": vbr.get("PeerIpv6GatewayIp", ""),
            "EnableIpv6": vbr.get("EnableIpv6", False),
            "RouteTableId": vbr.get("RouteTableId", ""),
            "VlanInterfaceId": vbr.get("VlanInterfaceId", ""),
        })

    return {"vbrs": summary, "total": len(summary)}


def describe_vbr_bgp(vbr_id: str, region: str = None) -> dict:
    """Query BGP groups and peers associated with one VBR."""
    groups_result = _call_with_retry(
        "vpc", "describe-bgp-groups", {"RouterId": vbr_id, "PageSize": "50"}, region,
    )
    peers_result = _call_with_retry(
        "vpc", "describe-bgp-peers", {"RouterId": vbr_id, "PageSize": "50"}, region,
    )
    groups = groups_result.get("BgpGroups", {}).get("BgpGroup", [])
    peers = peers_result.get("BgpPeers", {}).get("BgpPeer", [])
    issues = []
    if "error" in groups_result:
        issues.append(f"BGP group query failed: {groups_result['error']}")
    if "error" in peers_result:
        issues.append(f"BGP peer query failed: {peers_result['error']}")
    for peer in peers:
        status = peer.get("Status", "")
        if status and status.lower() not in {"established", "active"}:
            issues.append(
                f"BGP peer {peer.get('BgpPeerId', peer.get('PeerIpAddress', ''))} "
                f"state is {status}"
            )
    return {"groups": groups, "peers": peers, "issues": issues}


def describe_vbr_routes(route_table_id: str, dst_ip: str = "",
                        region: str = None) -> dict:
    """Return VBR route entries and the longest-prefix match for an IP."""
    result = _call_with_retry(
        "vpc", "describe-route-entry-list",
        {"RouteTableId": route_table_id, "MaxResult": "100"}, region,
    )
    if "error" in result:
        return result

    entries = result.get("RouteEntrys", {})
    if isinstance(entries, dict):
        entries = entries.get("RouteEntry", [])

    summary = []
    for entry in entries:
        next_hops = entry.get("NextHops", {}).get("NextHop", [])
        summary.append({
            "RouteEntryId": entry.get("RouteEntryId", ""),
            "DestinationCidrBlock": entry.get("DestinationCidrBlock", ""),
            "Status": entry.get("Status", ""),
            "Type": entry.get("Type", ""),
            "NextHops": [{
                "NextHopId": hop.get("NextHopId", ""),
                "NextHopType": hop.get("NextHopType", ""),
            } for hop in next_hops],
        })

    matched = []
    if dst_ip:
        matched = [entry for entry in summary
                   if cidr_contains(entry.get("DestinationCidrBlock", ""), dst_ip)]
        matched.sort(
            key=lambda entry: cidr_prefix_len(entry.get("DestinationCidrBlock", "")),
            reverse=True,
        )
    return {
        "route_table_id": route_table_id,
        "route_entries": summary,
        "total": len(summary),
        "destination_ip": dst_ip,
        "matched_route": matched[0] if matched else None,
    }


def check_vbr_for_vpc(vpc_id: str = "", vbr_id: str = "", dst_ip: str = "",
                      region: str = None) -> dict:
    """Implementation detail."""
    vbr_result = describe_virtual_border_routers(region=region)
    if "error" in vbr_result:
        return vbr_result



    vbrs = vbr_result.get("vbrs", [])
    if vbr_id:
        vbrs = [vbr for vbr in vbrs if vbr.get("VbrId") == vbr_id]
    elif vpc_id:
        vbrs = [vbr for vbr in vbrs if vbr.get("VpcId") == vpc_id]

    active = [v for v in vbrs if v.get("Status") == "active"]
    inactive = [v for v in vbrs if v.get("Status") != "active"]


    issues = []
    for vbr in vbrs:
        if vbr.get("Status") != "active":
            issues.append(f"VBR {vbr['VbrId']} 状态异常: {vbr['Status']}")
        pc_status = vbr.get("PhysicalConnectionStatus", "")
        if pc_status and pc_status != "Enabled":
            issues.append(f"VBR {vbr['VbrId']} 物理连接状态异常: {pc_status}")
        pc_biz = vbr.get("PhysicalConnectionBusinessStatus", "")
        if pc_biz and pc_biz != "Normal":
            issues.append(f"VBR {vbr['VbrId']} 物理连接业务状态异常: {pc_biz}")

    bgp = describe_vbr_bgp(vbr_id, region) if vbr_id else {
        "groups": [], "peers": [], "issues": []
    }
    issues.extend(bgp.get("issues", []))

    route_checks = []
    for vbr in vbrs:
        route_table_id = vbr.get("RouteTableId", "")
        if not route_table_id:
            issues.append(f"VBR {vbr['VbrId']} 未返回路由表 ID")
            continue
        route_check = describe_vbr_routes(route_table_id, dst_ip, region)
        route_checks.append(route_check)
        if "error" in route_check:
            issues.append(f"VBR {vbr['VbrId']} 路由查询失败: {route_check['error']}")
        elif dst_ip and not route_check.get("matched_route"):
            issues.append(f"VBR {vbr['VbrId']} 路由表缺少到 {dst_ip} 的路由")

    return {
        "found": len(vbrs) > 0,
        "vbrs": vbrs,
        "active_count": len(active),
        "inactive_count": len(inactive),
        "issues": issues,
        "bgp_groups": bgp.get("groups", []),
        "bgp_peers": bgp.get("peers", []),
        "route_checks": route_checks,
        "details": f"找到 {len(vbrs)} 个 VBR "
                   f"(活跃: {len(active)}, 异常: {len(inactive)})",
    }




def main():
    import argparse

    parser = argparse.ArgumentParser(description="VPN Gateway / Express Connect 诊断")
    sub = parser.add_subparsers(dest="action")


    p = sub.add_parser("vpn-gateways", help="查询 VPN 网关")
    p.add_argument("--vpc-id", help="VPC ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("vpn-connections", help="查询 VPN 连接（隧道）")
    p.add_argument("--vpn-gateway-id", help="VPN 网关 ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("vpn", help="检查 VPC 关联的 VPN 网关和隧道")
    p.add_argument("--vpc-id", required=True, help="VPC ID")
    p.add_argument("--region", help="地域")

    # VBR
    p = sub.add_parser("vbr", help="查询 VBR（虚拟边界路由器）")
    p.add_argument("--vpc-id", help="VPC ID（用于关联过滤）")
    p.add_argument("--vbr-id", help="VBR ID（精确过滤）")
    p.add_argument("--dst-ip", help="目标 IP（用于 VBR 路由最长前缀匹配）")
    p.add_argument("--region", help="地域")

    args = parser.parse_args()

    if args.action == "vpn-gateways":
        result = describe_vpn_gateways(vpc_id=args.vpc_id, region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "vpn-connections":
        result = describe_vpn_connections(vpn_gateway_id=args.vpn_gateway_id,
                                           region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "vpn":
        result = check_vpn_for_vpc(args.vpc_id, region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "vbr":
        result = check_vbr_for_vpc(
            args.vpc_id, args.vbr_id, args.dst_ip, region=args.region,
        )
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
