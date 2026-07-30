"""Implementation detail."""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from net_common import CheckResult, cidr_contains




def analyze_step1(data_dir: str) -> dict:
    """Implementation detail."""
    checks = []


    instances_file = Path(data_dir) / "instances.json"
    instances = _load_json(instances_file).get("instances", [])

    if not instances:
        checks.append(_check("实例查询", "error", "未查询到实例信息", suggestion="检查实例 ID 是否正确、Region 是否匹配"))
        return _step_output(checks)

    for inst in instances:
        inst_id = inst.get("InstanceId", "")
        status = inst.get("Status", "")
        net_type = inst.get("InstanceNetworkType", "")


        if status != "Running":
            checks.append(_check(
                f"实例状态 ({inst_id})", "critical",
                f"实例 {inst_id} 状态为 {status}，非 Running",
                suggestion="启动实例后重试",
            ))
        else:
            checks.append(_check(f"实例状态 ({inst_id})", "ok", f"实例 {inst_id} 运行中"))


        if net_type == "classic":
            checks.append(_check(
                f"网络类型 ({inst_id})", "critical",
                f"实例 {inst_id} 为经典网络，本工具仅支持 VPC 网络",
                suggestion="请将实例迁移到 VPC 网络",
            ))
        elif net_type == "vpc":
            vpc_id = inst.get("VpcId", "")
            vsw_id = inst.get("VSwitchId", "")
            checks.append(_check(
                f"网络类型 ({inst_id})", "ok",
                f"VPC: {vpc_id}, VSwitch: {vsw_id}",
            ))


    if len(instances) >= 2:
        vpcs = set(inst.get("VpcId", "") for inst in instances)
        if len(vpcs) == 1:
            scenario = "same_vpc"
            checks.append(_check("场景判定", "ok", f"同 VPC 实例互访 (VPC: {vpcs.pop()})"))
        else:
            scenario = "cross_vpc"
            checks.append(_check("场景判定", "ok", f"跨 VPC 实例互访 (VPCs: {', '.join(vpcs)})"))
    else:
        scenario = "unknown"
        checks.append(_check("场景判定", "warning", "仅提供单端信息，无法完整判定场景"))

    result = _step_output(checks)
    result["scenario"] = scenario
    result["instances"] = instances
    return result


def analyze_step2(data_dir: str, protocol: str = "", port: int = 0,
                   src_ip: str = "", dst_ip: str = "") -> dict:
    """Implementation detail."""
    checks = []

    sg_rules_file = Path(data_dir) / "sg_rules.json"
    sg_data = _load_json(sg_rules_file)

    if not sg_data or "error" in sg_data:
        checks.append(_check("安全组查询", "error", sg_data.get("error", "安全组数据为空")))
        return _step_output(checks)

    if sg_data.get("status") == "unavailable":
        checks.append(_check(
            "安全组查询", "warning", sg_data.get("details", "未能解析安全组 ID"),
            suggestion="确认当前凭证可查询目标 ECS/ENI；保留脚本降级结果并继续其他独立检查",
        ))
        return _step_output(checks)

    sg_check_file = Path(data_dir) / "sg_check.json"
    sg_check = _load_json(sg_check_file)

    if sg_check:
        check_results = []
        direction_names = {
            "source_egress": "源端出方向",
            "dest_ingress": "目的端入方向",
            "dest_egress": "目的端出方向（回包）",
            "source_ingress": "源端入方向（回包）",
        }
        if any(name in sg_check for name in direction_names):
            for key, direction_name in direction_names.items():
                for sg_id, result in sg_check.get(key, {}).items():
                    check_results.append((sg_id, result, direction_name))
        else:
            check_results = [
                (sg_id, result, "") for sg_id, result in sg_check.items()
                if isinstance(result, dict)
            ]

        for sg_id, result, explicit_direction in check_results:
            if "error" in result:
                checks.append(_check(f"安全组 {sg_id}", "error", result["error"]))
                continue

            verdict = result.get("verdict", "")
            details = result.get("details", "")
            sg_type = result.get("sg_type", "normal")
            direction = explicit_direction or (
                "出方向" if "egress" in details.lower() or "出" in details else "入方向")

            if verdict == "deny":
                checks.append(_check(
                    f"安全组{direction} ({sg_id})", "critical", details,
                    suggestion=_sg_fix_suggestion(direction, protocol, port, src_ip, dst_ip, sg_type),
                ))
            elif verdict == "allow":
                checks.append(_check(f"安全组{direction} ({sg_id})", "ok", details))
            else:
                checks.append(_check(f"安全组{direction} ({sg_id})", "warning", details))


            if verdict == "allow" and sg_type == "enterprise":
                checks.append(_check(
                    f"安全组{direction}回程提醒 ({sg_id})", "warning",
                    f"企业安全组为无状态，{direction}已放行，但回程流量需在反方向显式配置放行规则",
                    suggestion="在该企业安全组的反方向添加回程放行规则（临时端口范围 1024-65535）",
                ))
    else:

        for sg_id, rules in sg_data.items():
            if "error" in rules:
                checks.append(_check(f"安全组 {sg_id}", "error", rules["error"]))
            else:
                sg_type = rules.get("sg_type", "normal")
                ic = rules.get("ingress_count", 0)
                ec = rules.get("egress_count", 0)
                type_label = "企业安全组/无状态" if sg_type == "enterprise" else "普通安全组/有状态"
                summary = f"[{type_label}] 入站规则 {ic} 条，出站规则 {ec} 条（未指定协议/端口，无法精确匹配）"

                if sg_type == "enterprise" and ec == 0:
                    checks.append(_check(
                        f"安全组 {sg_id}", "critical",
                        f"[企业安全组/无状态] 无任何出站规则，所有出站流量将被拒绝（企业安全组无默认出站放行）",
                        suggestion="在企业安全组添加出方向放行规则（企业安全组为无状态，还需为回程流量添加反方向规则）",
                    ))
                else:
                    checks.append(_check(
                        f"安全组 {sg_id}", "warning", summary,
                        suggestion="提供协议和端口信息以进行精确规则匹配",
                    ))

    return _step_output(checks)


def analyze_step3(data_dir: str, src_ip: str = "", dst_ip: str = "") -> dict:
    """Implementation detail."""
    checks = []

    route_check_file = Path(data_dir) / "route_check.json"
    route_data = _load_json(route_check_file)

    if not route_data:

        routes_file = Path(data_dir) / "routes.json"
        routes = _load_json(routes_file)
        if routes:
            for table in routes.get("route_tables", []):
                tid = table.get("RouteTableId", "")
                entries = table.get("route_entries", [])
                checks.append(_check(
                    f"路由表 {tid}", "ok",
                    f"共 {len(entries)} 条路由条目",
                ))
        else:
            checks.append(_check("路由表查询", "error", "路由表数据为空"))
        return _step_output(checks)

    for label, data in route_data.items():
        if not isinstance(data, dict):
            continue
        if "error" in data:
            checks.append(_check(f"路由查找 ({label})", "error", data["error"]))
            continue

        matched = data.get("matched", False)
        details = data.get("details", "")

        if not matched:
            checks.append(_check(
                f"路由查找 ({label})", "critical", details,
                suggestion=_route_fix_suggestion("", is_missing=True),
            ))
        else:
            is_active = data.get("is_active", True)
            origin = data.get("origin", "")
            if not is_active:
                checks.append(_check(
                    f"路由查找 ({label})", "critical",
                    f"{details}（路由状态异常）",
                    suggestion=_route_fix_suggestion(origin, is_missing=False),
                ))
            else:
                checks.append(_check(f"路由查找 ({label})", "ok", details))

    return _step_output(checks)


def analyze_step4(data_dir: str, protocol: str = "", port: int = 0,
                   src_ip: str = "", dst_ip: str = "") -> dict:
    """Implementation detail."""
    checks = []

    acl_check_file = Path(data_dir) / "acl_check.json"
    acl_data = _load_json(acl_check_file)

    if not acl_data:
        checks.append(_check("网络 ACL", "ok", "未查询到绑定的网络 ACL，不阻断"))
    else:
        for label, data in acl_data.items():
            if "error" in data:
                checks.append(_check(f"网络 ACL ({label})", "error", data["error"]))
                continue

            verdict = data.get("verdict", "allow")
            details = data.get("details", "")

            if verdict == "deny":
                checks.append(_check(
                    f"网络 ACL ({label})", "critical", details,
                    suggestion="修改网络 ACL 规则以允许所需流量",
                ))
            else:
                checks.append(_check(f"网络 ACL ({label})", "ok", details))

    tr_data = _load_json(Path(data_dir) / "tr_check.json")
    tr_types = {
        tr_data.get(side, {}).get("TransitRouterType", "").lower()
        for side in ("source_tr", "destination_tr")
    }
    if "basic" in tr_types:
        checks.append(_check(
            "基础版 TR Zone VSwitch 网络 ACL",
            "ok",
            "基础版 TR 无 ZoneMappings，TR zone VSwitch NACL 检查不适用；已检查两端业务 VSwitch 的网络 ACL。",
        ))

    return _step_output(checks)


def analyze_step5(data_dir: str, scenario: str = "") -> dict:
    """Implementation detail."""
    checks = []

    # Peering
    peering_file = Path(data_dir) / "peering.json"
    peering_data = _load_json(peering_file)
    if peering_data:
        if peering_data.get("found"):
            if peering_data.get("is_active"):
                checks.append(_check("VPC 对等连接", "ok", peering_data.get("details", "")))
            else:
                checks.append(_check(
                    "VPC 对等连接", "critical",
                    peering_data.get("details", ""),
                    suggestion="检查对等连接状态，如为待接受状态请在对端 VPC 接受连接",
                ))
        elif "error" not in peering_data:
            checks.append(_check("VPC 对等连接", "warning", peering_data.get("details", "未找到对等连接")))

    # CEN
    cen_file = Path(data_dir) / "cen.json"
    cen_data = _load_json(cen_file)
    if cen_data:
        if cen_data.get("found"):
            cen_status = cen_data.get("cen_status", "")
            src_attach = cen_data.get("source_attachment", {})
            dst_attach = cen_data.get("destination_attachment", {})
            src_status = src_attach.get("Status", "") if src_attach else "未挂载"
            dst_status = dst_attach.get("Status", "") if dst_attach else "未挂载"

            if src_status == "Attached" and dst_status == "Attached":
                checks.append(_check("CEN 连接", "ok", cen_data.get("details", "")))
            else:
                checks.append(_check(
                    "CEN 连接", "critical",
                    f"CEN 挂载状态异常: 源={src_status}, 目的={dst_status}",
                    suggestion="确认两端 VPC 均已成功挂载到 CEN",
                ))
        elif "error" not in cen_data:
            checks.append(_check("CEN 连接", "warning", cen_data.get("details", "未找到关联 CEN")))


    tr_route_file = Path(data_dir) / "tr_route_check.json"
    tr_route_data = _load_json(tr_route_file)
    if tr_route_data:
        matched = tr_route_data.get("matched", False)
        details = tr_route_data.get("details", "")
        has_conflict = tr_route_data.get("conflict", False)
        rejected_routes = tr_route_data.get("rejected_routes", [])


        if rejected_routes:
            for r in rejected_routes:
                r_cidr = r.get("DestinationCidrBlock", "")
                r_origin = r.get("OriginResourceId", "")
                r_origin_type = r.get("OriginResourceType", "")
                r_nexthop = r.get("NextHopId", "")
                conflict_detail = (
                    f"路由 {r_cidr} (来源: {r_origin_type} {r_origin}, "
                    f"下一跳: {r_nexthop}) 因前缀冲突被 Rejected"
                )

                active_route = tr_route_data.get("route")
                if active_route and active_route.get("DestinationCidrBlock") == r_cidr:
                    winner_origin = active_route.get("OriginResourceId", "")
                    winner_nexthop = active_route.get("NextHopId", "")
                    conflict_detail += (
                        f"。当前生效路由指向 {winner_nexthop} "
                        f"(来源: {active_route.get('OriginResourceType', '')} {winner_origin})"
                    )
                checks.append(_check(
                    "TR 路由冲突", "critical",
                    conflict_detail,
                    suggestion=(
                        f"存在跨地域/跨 VPC 同前缀路由冲突。修复方案: "
                        f"1) 消除网段冲突（调整一端 VSwitch CIDR）；"
                        f"2) 使用 CEN 路由策略 Deny 不需要的传播源；"
                        f"3) 添加静态路由覆盖（静态优先于传播路由）"
                    ),
                ))

            if matched:

                checks.append(_check("TR 路由匹配", "warning",
                                      tr_route_data.get("conflict_details", details),
                                      suggestion="当前 Active 路由可能不是预期的下一跳，请确认是否需要调整"))
            else:

                checks.append(_check("TR 路由匹配", "critical",
                                      details or "目标网段路由因前缀冲突全部被 Rejected，无 Active 路由可用",
                                      suggestion="需要消除路由冲突或添加静态路由覆盖"))


        elif not matched:
            dst_ip = tr_route_data.get("dst_ip", "")
            suggestion = _tr_route_missing_suggestion(data_dir, dst_ip)
            checks.append(_check(
                "TR 路由匹配", "critical",
                details or f"TR 路由表中缺少到 {dst_ip} 的路由",
                suggestion=suggestion,
            ))
        else:
            is_active = tr_route_data.get("is_active", True)
            if not is_active:
                checks.append(_check(
                    "TR 路由匹配", "critical",
                    f"{details}（路由状态异常）",
                    suggestion="检查 TR 路由条目状态和对应的 VPC 连接是否正常",
                ))
            else:
                checks.append(_check("TR 路由匹配", "ok", details))


    tr_assoc_file = Path(data_dir) / "tr_associations.json"
    tr_assoc_data = _load_json(tr_assoc_file)
    if tr_assoc_data:
        if tr_assoc_data.get("error"):
            checks.append(_check("TR 路由表关联", "warning",
                                  f"关联查询失败: {tr_assoc_data['error']}"))
        elif tr_assoc_data.get("fallback"):
            checks.append(_check("TR 路由表关联", "warning",
                                  tr_assoc_data.get("details", "未找到关联路由表，已回退"),
                                  suggestion="检查源端 VPC 连接的路由表关联配置"))
        else:
            assoc_status = tr_assoc_data.get("association_status", "")
            if assoc_status == "Active":
                rt_type = tr_assoc_data.get("route_table_type", "")
                rt_id = tr_assoc_data.get("route_table_id", "")
                checks.append(_check("TR 路由表关联", "ok",
                                      f"源端关联路由表: {rt_id} (类型: {rt_type})"))
            else:
                checks.append(_check("TR 路由表关联", "critical",
                                      f"关联状态异常: {assoc_status}",
                                      suggestion="检查源端 VPC 连接与 TR 路由表的关联配置"))


    tr_prop_file = Path(data_dir) / "tr_propagations.json"
    tr_prop_data = _load_json(tr_prop_file)
    if tr_prop_data:
        propagated = tr_prop_data.get("propagated", False)
        if propagated:
            prop_status = tr_prop_data.get("propagation_status", "")
            if prop_status == "Active":
                checks.append(_check("TR 路由学习", "ok", tr_prop_data.get("details", "")))
            else:
                checks.append(_check("TR 路由学习", "warning",
                                      f"传播状态: {prop_status}",
                                      suggestion="等待路由学习生效或检查路由学习配置"))
        else:
            checks.append(_check("TR 路由学习", "critical",
                                  tr_prop_data.get("details", "目的端未向源端关联路由表配置路由学习"),
                                  suggestion="在 CEN 控制台为目的 VPC 连接配置路由学习（Propagation）到源端关联的 TR 路由表"))


    route_maps_file = Path(data_dir) / "route_maps.json"
    route_maps_data = _load_json(route_maps_file)
    if route_maps_data:
        blocked = route_maps_data.get("blocked", False)
        if blocked:
            blocking_maps = route_maps_data.get("blocking_maps", [])
            for rm in blocking_maps:
                rm_id = rm.get("RouteMapId", "")
                priority = rm.get("Priority", "")
                desc = rm.get("Description", "")
                dst_cidrs = rm.get("DestinationCidrBlocks", [])
                detail = (
                    f"路由策略 {rm_id} (优先级: {priority}) Deny"
                    f" 目的网段 {', '.join(dst_cidrs)}"
                )
                if desc:
                    detail += f" ({desc})"
                checks.append(_check(
                    "CEN 路由策略", "critical", detail,
                    suggestion=f"检查 CEN 路由策略，移除或修改拒绝规则 {rm_id}",
                ))
        else:
            total = route_maps_data.get("total_maps", 0)
            if total > 0:
                checks.append(_check("CEN 路由策略", "ok",
                                      f"存在 {total} 条路由策略，未匹配到拦截目的网段的 Deny 规则"))

    # VPN
    vpn_file = Path(data_dir) / "vpn.json"
    vpn_data = _load_json(vpn_file)
    if vpn_data and vpn_data.get("found"):
        vpn_connections = vpn_data.get("vpn_connections", [])
        for error in vpn_data.get("connection_errors", []):
            checks.append(_check(
                f"VPN 连接查询 ({error.get('VpnGatewayId', '')})", "warning",
                f"VPN 连接查询权限不足或失败: {error.get('error', '')}",
                suggestion="补充 DescribeVpnConnections 只读权限；同时保留并报告已获取的网关和路由检查结果",
            ))
        if not vpn_connections:
            checks.append(_check(
                "VPN IPsec 连接", "critical",
                "VPN 网关未查询到任何 IPsec 连接，或连接查询因权限不足无法确认；当前没有可验证的活动隧道",
                suggestion="确认 VPN 网关已创建 IPsec 连接；若连接已存在，请补充 DescribeVpnConnections 只读权限",
            ))
        for conn in vpn_connections:
            conn_id = conn.get("VpnConnectionId", "")
            local_subnet = conn.get("LocalSubnet", "")
            remote_subnet = conn.get("RemoteSubnet", "")
            for tun in conn.get("TunnelStatusSummary", []):
                tun_id = tun.get("TunnelId", "")
                role = tun.get("Role", "")
                label = f"{conn_id}/{tun_id}" if tun_id else conn_id
                if role:
                    label += f" ({role})"
                if tun.get("is_up"):
                    checks.append(_check(
                        f"VPN 隧道 ({label})", "ok",
                        f"隧道状态正常, 本端子网: {local_subnet}, 对端子网: {remote_subnet}",
                    ))
                else:
                    checks.append(_check(
                        f"VPN 隧道 ({label})", "critical",
                        f"隧道状态: State={tun.get('State', '')}, Status={tun.get('Status', '')}",
                        suggestion="检查 IKE/IPsec 配置: 预共享密钥、IKE 版本、加密算法是否两端一致",
                    ))

    # VBR
    vbr_file = Path(data_dir) / "vbr.json"
    vbr_data = _load_json(vbr_file)
    if vbr_data and vbr_data.get("found"):
        for issue in vbr_data.get("issues", []):
            suggestion = "联系阿里云技术支持检查物理连接"
            if "路由" in issue:
                suggestion = "检查 VBR 路由表、BGP 路由发布和 RouterInterface 下一跳配置"
            checks.append(_check("VBR 状态", "critical", issue,
                                  suggestion=suggestion))
        if not vbr_data.get("issues"):
            checks.append(_check("VBR 状态", "ok", vbr_data.get("details", "")))
        vbr_cen_data = _load_json(Path(data_dir) / "cen.json")
        if not vbr_cen_data.get("found") and not (
                Path(data_dir) / "vbr_route_sync.json").exists():
            checks.append(_check(
                "VBR CEN 路由同步检查", "skipped",
                "如果 VBR 不是 CEN 子实例，跳过此步骤",
            ))

    if not checks:
        checks.append(_check("跨网络连接", "skipped", "未检测到跨网络连接组件（同 VPC 场景或数据缺失）"))

    return _step_output(checks)


def analyze_step_nat(data_dir: str, src_ip: str = "", dst_ip: str = "",
                      protocol: str = "", port: int = 0) -> dict:
    """Implementation detail."""
    checks = []

    nat_file = Path(data_dir) / "nat_check.json"
    nat_data = _load_json(nat_file)

    if not nat_data or not nat_data.get("found"):
        if nat_data and nat_data.get("error"):
            checks.append(_check("NAT 网关查询", "error", nat_data["error"]))
        else:
            checks.append(_check("NAT 网关", "ok", "未发现关联的 NAT 网关"))
        return _step_output(checks)


    for gw in nat_data.get("nat_gateways", []):
        gw_id = gw.get("NatGatewayId", "")
        gw_status = gw.get("Status", "")
        nat_type = gw.get("NatType", "")
        net_type = gw.get("NetworkType", "")

        if gw_status != "Available":
            checks.append(_check(
                f"NAT 网关状态 ({gw_id})", "critical",
                f"NAT 网关 {gw_id} 状态为 {gw_status}，非 Available",
                suggestion="检查 NAT 网关是否已过期或欠费",
            ))
        else:
            checks.append(_check(
                f"NAT 网关状态 ({gw_id})", "ok",
                f"NAT 网关 {gw_id} 状态正常 (类型: {nat_type}, 网络: {net_type})",
            ))


    dnat_rules = nat_data.get("dnat_rules", [])
    matched_dnat = None

    if dst_ip and dnat_rules:
        for rule in dnat_rules:
            ext_ip = rule.get("ExternalIp", "")
            ext_port = rule.get("ExternalPort", "")
            rule_proto = rule.get("IpProtocol", "").upper()

            internal_ip = rule.get("InternalIp", "")
            internal_port = rule.get("InternalPort", "")
            ip_match = dst_ip in (ext_ip, internal_ip)
            port_match = (not port or ext_port == "any" or internal_port == "any" or
                         str(port) in (str(ext_port), str(internal_port)))
            proto_match = (not protocol or rule_proto == "ANY" or
                          rule_proto == protocol.upper())

            if ip_match and port_match and proto_match:
                matched_dnat = rule
                checks.append(_check(
                    f"DNAT 规则匹配", "ok",
                    f"DNAT: {ext_ip}:{ext_port}/{rule_proto} → "
                    f"{rule.get('InternalIp', '')}:{rule.get('InternalPort', '')} "
                    f"(NAT: {rule.get('NatGatewayId', '')})",
                ))
                break

        if not matched_dnat:
            port_str = f":{port}" if port else ""
            proto_str = f"/{protocol}" if protocol else ""
            checks.append(_check(
                "DNAT 规则匹配", "critical",
                f"未找到匹配 {dst_ip}{port_str}{proto_str} 的 DNAT 规则",
                suggestion="检查 NAT 网关的 DNAT 端口转发规则配置",
            ))


    snat_rules = nat_data.get("snat_rules", [])
    if src_ip and snat_rules:
        snat_matched = False
        for rule in snat_rules:
            src_cidr = rule.get("SourceCIDR", "")
            if src_cidr and cidr_contains(src_cidr, src_ip):
                snat_matched = True
                checks.append(_check(
                    "SNAT 规则匹配", "ok",
                    f"SNAT: {src_cidr} → {rule.get('SnatIp', '')} "
                    f"(NAT: {rule.get('NatGatewayId', '')})",
                ))
                break

        if not snat_matched and not matched_dnat:

            checks.append(_check(
                "SNAT 规则匹配", "warning",
                f"未找到覆盖 {src_ip} 的 SNAT 规则",
                suggestion="如需源端主动出方向 NAT，请配置 SNAT 规则",
            ))


    if matched_dnat and src_ip:
        _check_dnat_asymmetric_routing(
            checks, data_dir, matched_dnat, src_ip,
        )

    return _step_output(checks)


def _check_dnat_asymmetric_routing(checks: list, data_dir: str,
                                     dnat_rule: dict, client_ip: str):
    """Implementation detail."""
    nat_gw_id = dnat_rule.get("NatGatewayId", "")
    internal_ip = dnat_rule.get("InternalIp", "")


    route_check_file = Path(data_dir) / "route_check.json"
    route_data = _load_json(route_check_file)

    if not route_data:
        checks.append(_check(
            "DNAT 回程路由", "warning",
            "无路由检查数据，无法验证 DNAT 回程路径是否对称",
            suggestion="执行路由诊断（Step 3）后重新运行 NAT 分析",
        ))
        return




    return_route = None
    return_label = ""

    for label, data in route_data.items():
        if "error" in data or not data.get("matched"):
            continue
        route = data.get("route", {})
        dest_cidr = route.get("DestinationCidrBlock", "")

        if dest_cidr and cidr_contains(dest_cidr, client_ip):
            nexthops = route.get("NextHops", [])
            for nh in nexthops:
                nh_type = nh.get("NextHopType", "")
                nh_id = nh.get("NextHopId", "")

                if nh_type == "NatGateway" and nh_id == nat_gw_id:
                    continue
                if nh_type != "NatGateway":
                    return_route = data
                    return_label = label
                    break
            if return_route:
                break

    if return_route:
        route_info = return_route.get("route", {})
        dest_cidr = route_info.get("DestinationCidrBlock", "")
        origin = return_route.get("origin", "")
        nexthops = route_info.get("NextHops", [])
        nh_desc = ", ".join(
            f"{nh['NextHopType']}({nh['NextHopId']})" for nh in nexthops
        ) if nexthops else "unknown"

        origin_label = f"（Origin={origin}）" if origin else ""

        if origin == "CEN":
            suggestion = (
                f"CEN 传播路由 {dest_cidr} 覆盖了指向 NAT 网关的路由，导致回程流量绕过 NAT 网关。"
                f"建议: 1) 添加更明细的静态路由（如将客户端网段拆分为 /25 或添加 /32 主机路由）"
                f"指向 NAT 网关 {nat_gw_id}; "
                f"2) 在 CEN 路由策略中对该网段添加 Deny 规则阻止路由学习到此 VPC"
            )
        else:
            suggestion = (
                f"回程路由 {dest_cidr} 指向 {nh_desc} 而非 NAT 网关 {nat_gw_id}，"
                f"导致非对称路由。建议修改该路由的下一跳为 NAT 网关"
            )

        checks.append(_check(
            "DNAT 非对称路由", "critical",
            f"后端 ECS 到客户端 {client_ip} 的回程路由匹配 {dest_cidr} → {nh_desc} "
            f"{origin_label}，未经过 NAT 网关 {nat_gw_id}，存在非对称路由",
            suggestion=suggestion,
        ))
    else:

        found_symmetric = False
        for label, data in route_data.items():
            if "error" in data or not data.get("matched"):
                continue
            route = data.get("route", {})
            dest_cidr = route.get("DestinationCidrBlock", "")
            if dest_cidr and cidr_contains(dest_cidr, client_ip):
                nexthops = route.get("NextHops", [])
                for nh in nexthops:
                    if nh.get("NextHopType") == "NatGateway":
                        found_symmetric = True
                        break
            if found_symmetric:
                break

        if found_symmetric:
            checks.append(_check(
                "DNAT 回程路由", "ok",
                f"后端 ECS 到客户端 {client_ip} 的回程路由经过 NAT 网关，路径对称",
            ))




def analyze_all(data_dir: str) -> dict:
    """Implementation detail."""
    all_checks = []
    root_causes = []
    recommendations = []

    input_data = _load_json(Path(data_dir) / "input.json")
    ips = input_data.get("ips", [])
    protocol = input_data.get("protocol", "")
    port = input_data.get("port", 0)
    src_ip = ips[0] if ips else ""
    dst_ip = ips[1] if len(ips) > 1 else ""

    generators = {
        "step1.json": (("instances.json",), lambda: analyze_step1(data_dir)),
        "step2.json": (("sg_rules.json", "sg_check.json"), lambda: analyze_step2(
            data_dir, protocol, port, src_ip, dst_ip)),
        "step3.json": (("routes.json", "route_check.json"), lambda: analyze_step3(
            data_dir, src_ip, dst_ip)),
        "step4.json": (("acls.json", "acl_check.json"), lambda: analyze_step4(
            data_dir, protocol, port, src_ip, dst_ip)),
        "step5.json": ((), lambda: analyze_step5(data_dir)),
        "step_nat.json": (("nat_check.json",), lambda: analyze_step_nat(
            data_dir, src_ip, dst_ip, protocol, port)),
    }
    cross_network_files = (
        "peering.json", "cen.json", "vpn.json", "vbr.json",
        "tr_check.json", "tr_route_check.json", "vbr_route_sync.json",
    )

    for step_file, (source_files, generator) in generators.items():
        step_path = Path(data_dir) / step_file
        step_data = _load_json(step_path)
        source_exists = any((Path(data_dir) / name).exists()
                            for name in source_files)
        if step_file == "step5.json":
            source_exists = any((Path(data_dir) / name).exists()
                                for name in cross_network_files)
        if source_exists and not isinstance(step_data.get("checks"), list):
            step_data = generator()
            try:
                step_path.write_text(
                    json.dumps(step_data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            except OSError:
                pass
        if step_data:
            for check in step_data.get("checks", []):
                all_checks.append(check)

    raw_input = input_data.get("raw", "")
    regions = set(re.findall(
        r"(?<![a-z0-9])(cn-[a-z]+-?\d*|us-[a-z]+-\d|eu-[a-z]+-\d|ap-[a-z]+-\d)(?![a-z0-9])",
        raw_input,
    ))
    if input_data.get("cen_ids") and len(regions) > 1:
        all_checks.append(_check(
            "跨地域 CEN 中继限制", "ok",
            "跨地域 CEN 路由不支持通过中间地域中继，源端与目的端必须存在直接的路由学习或 Attachment 配置。",
        ))

    tr_data = _load_json(Path(data_dir) / "tr_check.json")
    tr_types = {
        tr_data.get(side, {}).get("TransitRouterType", "").lower()
        for side in ("source_tr", "destination_tr")
    }
    if "basic" in tr_types and not any(
            "TR zone VSwitch NACL 检查不适用" in check.get("summary", "")
            for check in all_checks):
        all_checks.append(_check(
            "基础版 TR Zone VSwitch 网络 ACL",
            "ok",
            "基础版 TR 无 ZoneMappings，TR zone VSwitch NACL 检查不适用；已检查两端业务 VSwitch 的网络 ACL。",
        ))

    vpn_data = _load_json(Path(data_dir) / "vpn.json")
    routes_data = _load_json(Path(data_dir) / "routes.json")
    if vpn_data.get("found") and routes_data:
        target_cidrs = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}\b", raw_input)
        route_entries = [
            entry
            for table in routes_data.get("route_tables", [])
            for entry in table.get("route_entries", [])
        ]
        for target_cidr in target_cidrs:
            target_ip = target_cidr.split("/", 1)[0]
            if not any(cidr_contains(entry.get("DestinationCidrBlock", ""), target_ip)
                       for entry in route_entries):
                all_checks.append(_check(
                    "VPN IDC 目标路由", "critical",
                    f"VPC 路由表缺少到 IDC 网段 {target_cidr} 的路由",
                    suggestion=f"添加到 {target_cidr}、下一跳指向 VPN 网关或相关 VPN 连接的路由",
                ))

    if not all_checks:
        all_checks.append(_check(
            "综合分析输入", "error",
            "未找到可分析的标准步骤数据；诊断结果不完整",
            suggestion="重新运行对应的 skill 脚本和 net_analyze.py stepN 命令",
        ))


    for check in all_checks:
        status = check.get("status", "")
        if status == "critical":
            root_causes.append(check["summary"])
            if check.get("suggestion"):
                recommendations.append(check["suggestion"])
        elif status == "warning" and check.get("suggestion"):
            recommendations.append(check["suggestion"])


    statuses = [c.get("status", "") for c in all_checks]
    if "critical" in statuses:
        severity = "critical"
    elif "warning" in statuses:
        severity = "warning"
    elif "error" in statuses:
        severity = "warning"
    else:
        severity = "normal"


    if root_causes:
        conclusion = f"发现 {len(root_causes)} 个问题: " + "; ".join(root_causes[:3])
        if len(root_causes) > 3:
            conclusion += f" 等（共 {len(root_causes)} 个）"
    elif severity == "normal":
        conclusion = "未发现明显的网络配置异常"
    else:
        conclusion = "存在一些需要关注的配置项，请查看详细检查结果"


    seen = set()
    unique_recs = []
    for r in recommendations:
        if r not in seen:
            seen.add(r)
            unique_recs.append(r)


    check_table = []
    for check in all_checks:
        check_table.append({
            "item": check["name"],
            "status": check["status"],
            "summary": check["summary"],
            "suggestion": check.get("suggestion", ""),
        })

    return {
        "conclusion": conclusion,
        "severity": severity,
        "root_causes": root_causes,
        "check_table": check_table,
        "recommendations": unique_recs,
        "total_checks": len(all_checks),
        "critical_count": statuses.count("critical"),
        "warning_count": statuses.count("warning"),
        "ok_count": statuses.count("ok"),
    }




def _load_json(filepath) -> dict:
    """Implementation detail."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _check(name: str, status: str, summary: str,
           details: str = None, suggestion: str = None) -> dict:
    """Implementation detail."""
    result = {"name": name, "status": status, "summary": summary}
    if details:
        result["details"] = details
    if suggestion:
        result["suggestion"] = suggestion
    return result


def _step_output(checks: list) -> dict:
    """Implementation detail."""
    statuses = [c["status"] for c in checks]
    if "critical" in statuses:
        severity = "critical"
    elif "warning" in statuses:
        severity = "warning"
    elif "error" in statuses:
        severity = "warning"
    else:
        severity = "normal"
    return {"checks": checks, "severity": severity}


def _route_fix_suggestion(origin: str, is_missing: bool = True) -> str:
    """Implementation detail."""
    if is_missing:
        return "添加路由条目指向正确的下一跳"

    if origin == "CEN":
        return (
            "该路由由 CEN 动态传播（Origin=CEN），不能直接在 VPC 路由表中删除或修改。"
            "可选方案: 1) 添加更明细的静态路由（如 /25 拆分或 /32 主机路由）覆盖 CEN 路由; "
            "2) 在 CEN 路由策略中配置 Deny 规则调整路由学习"
        )
    elif origin == "Custom":
        return "该路由为手动添加的自定义路由（Origin=Custom），可直接修改其下一跳或删除后重新创建"
    elif origin == "System":
        return "该路由为系统自动创建（Origin=System），不可修改"
    else:
        return "检查下一跳资源是否存在且状态正常"


def _tr_route_missing_suggestion(data_dir: str, dst_ip: str) -> str:
    """Implementation detail."""

    route_maps_data = _load_json(Path(data_dir) / "route_maps.json")
    if route_maps_data and route_maps_data.get("blocked"):
        blocking = route_maps_data.get("blocking_maps", [])
        if blocking:
            rm_ids = ", ".join(rm.get("RouteMapId", "") for rm in blocking[:3])
            return (
                f"CEN 路由策略（{rm_ids}）Deny 了包含 {dst_ip} 的网段路由传入 TR，"
                "请在 CEN 控制台检查并修改或删除对应的 Deny 路由策略"
            )


    tr_prop_data = _load_json(Path(data_dir) / "tr_propagations.json")
    if tr_prop_data:
        if not tr_prop_data.get("propagated"):
            return (
                "目的端 VPC 连接未向源端关联的 TR 路由表配置路由学习（Propagation），"
                "请在 CEN 控制台为目的 VPC 连接添加到源端关联路由表的路由学习"
            )


    tr_assoc_data = _load_json(Path(data_dir) / "tr_associations.json")
    if tr_assoc_data and tr_assoc_data.get("fallback"):
        return (
            "源端 VPC 连接未关联到任何 TR 路由表（关联转发未配置），"
            "请在 CEN 控制台为源端 VPC 连接配置路由表关联"
        )


    return (
        f"TR 路由表中缺少到 {dst_ip} 的路由。请检查: "
        "1) 目的 VPC 是否已开启自动发布路由到 TR；"
        "2) 目的 VPC 中是否存在包含该 IP 的子网路由"
    )


def _sg_fix_suggestion(direction: str, protocol: str, port: int,
                        src_ip: str, dst_ip: str, sg_type: str = "normal") -> str:
    """Implementation detail."""
    proto = protocol or "TCP"
    if direction == "出方向":
        target_ip = dst_ip or "目的 IP"
        port_str = str(port) if port else "目标端口"
        base = f"在源实例安全组添加出方向规则: 协议={proto}, 端口={port_str}, 目的={target_ip}/32 或相应 CIDR"
    else:
        target_ip = src_ip or "源 IP"
        port_str = str(port) if port else "监听端口"
        base = f"在目的实例安全组添加入方向规则: 协议={proto}, 端口={port_str}, 源={target_ip}/32 或相应 CIDR"
    if sg_type == "enterprise":
        base += "（注意：企业安全组为无状态，还需在反方向添加回程放行规则，端口范围建议 1024-65535）"
    return base




def main():
    import argparse

    parser = argparse.ArgumentParser(description="内网连通性诊断分析引擎")
    sub = parser.add_subparsers(dest="action")

    p = sub.add_parser("step1", help="分析实例和 VPC 信息")
    p.add_argument("--dir", required=True, help="数据目录")

    p = sub.add_parser("step2", help="分析安全组规则")
    p.add_argument("--dir", required=True, help="数据目录")
    p.add_argument("--protocol", default="", help="协议")
    p.add_argument("--port", type=int, default=0, help="端口")
    p.add_argument("--src-ip", default="", help="源 IP")
    p.add_argument("--dst-ip", default="", help="目的 IP")

    p = sub.add_parser("step3", help="分析路由表")
    p.add_argument("--dir", required=True, help="数据目录")
    p.add_argument("--src-ip", default="", help="源 IP")
    p.add_argument("--dst-ip", default="", help="目的 IP")

    p = sub.add_parser("step4", help="分析网络 ACL")
    p.add_argument("--dir", required=True, help="数据目录")
    p.add_argument("--protocol", default="", help="协议")
    p.add_argument("--port", type=int, default=0, help="端口")
    p.add_argument("--src-ip", default="", help="源 IP")
    p.add_argument("--dst-ip", default="", help="目的 IP")

    p = sub.add_parser("step5", help="分析跨网络连接")
    p.add_argument("--dir", required=True, help="数据目录")
    p.add_argument("--scenario", default="", help="场景类型")

    p = sub.add_parser("step-nat", help="分析 NAT 网关（含 DNAT 非对称路由检测）")
    p.add_argument("--dir", required=True, help="数据目录")
    p.add_argument("--src-ip", default="", help="源（客户端）IP")
    p.add_argument("--dst-ip", default="", help="目的（DNAT ExternalIp）IP")
    p.add_argument("--protocol", default="", help="协议")
    p.add_argument("--port", type=int, default=0, help="端口")

    p = sub.add_parser("all", help="综合分析")
    p.add_argument("--dir", required=True, help="数据目录")

    args = parser.parse_args()

    if args.action == "step1":
        result = analyze_step1(args.dir)
    elif args.action == "step2":
        result = analyze_step2(args.dir, args.protocol, args.port, args.src_ip, args.dst_ip)
    elif args.action == "step3":
        result = analyze_step3(args.dir, args.src_ip, args.dst_ip)
    elif args.action == "step4":
        result = analyze_step4(args.dir, args.protocol, args.port, args.src_ip, args.dst_ip)
    elif args.action == "step5":
        result = analyze_step5(args.dir, args.scenario)
    elif args.action == "step-nat":
        result = analyze_step_nat(args.dir, args.src_ip, args.dst_ip,
                                   args.protocol, args.port)
    elif args.action == "all":
        result = analyze_all(args.dir)
    else:
        parser.print_help()
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(json.dumps({"error": "用户中断"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(json.dumps({"error": f"未处理的异常: {type(e).__name__}: {e}"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
