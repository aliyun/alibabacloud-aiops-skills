"""Implementation detail."""

import json
import sys
import os


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from net_common import _call_with_retry, cidr_contains




def describe_instances(instance_ids: list = None, private_ips: list = None,
                       vpc_id: str = None, region: str = None) -> dict:
    """Implementation detail."""
    params = {"PageSize": "100"}
    if instance_ids:
        params["InstanceIds"] = json.dumps(instance_ids)
    if vpc_id:
        params["VpcId"] = vpc_id

    result = _call_with_retry("ecs", "describe-instances", params, region)
    if "error" in result:
        return result

    instances = result.get("Instances", {}).get("Instance", [])


    if private_ips:
        filtered = []
        for inst in instances:
            inst_ips = set()

            vpc_attrs = inst.get("VpcAttributes", {})
            for ip in vpc_attrs.get("PrivateIpAddress", {}).get("IpAddress", []):
                inst_ips.add(ip)

            for eni in inst.get("NetworkInterfaces", {}).get("NetworkInterface", []):
                for ip_set in eni.get("PrivateIpSets", {}).get("PrivateIpSet", []):
                    inst_ips.add(ip_set.get("PrivateIpAddress", ""))
            if inst_ips & set(private_ips):
                filtered.append(inst)
        instances = filtered


    summary = []
    for inst in instances:
        vpc_attrs = inst.get("VpcAttributes", {})
        private_ips_list = vpc_attrs.get("PrivateIpAddress", {}).get("IpAddress", [])
        sg_ids = [sg for sg in inst.get("SecurityGroupIds", {}).get("SecurityGroupId", [])]
        summary.append({
            "InstanceId": inst.get("InstanceId"),
            "InstanceName": inst.get("InstanceName", ""),
            "Status": inst.get("Status"),
            "VpcId": vpc_attrs.get("VpcId", ""),
            "VSwitchId": vpc_attrs.get("VSwitchId", ""),
            "PrivateIpAddress": private_ips_list,
            "SecurityGroupIds": sg_ids,
            "InstanceNetworkType": inst.get("InstanceNetworkType", ""),
            "RegionId": inst.get("RegionId", ""),
            "ZoneId": inst.get("ZoneId", ""),
        })

    return {"instances": summary, "total": len(summary)}


def _find_instance_by_ip_in_region(ip: str, region: str) -> dict:
    """Implementation detail."""
    def _extract_ips(vpc_attrs):
        """Implementation detail."""
        ips = set()

        primary = vpc_attrs.get("PrivateIpAddress", "")
        if isinstance(primary, str) and primary:
            ips.add(primary)
        elif isinstance(primary, dict):
            for addr in primary.get("IpAddress", []):
                if addr:
                    ips.add(addr)

        for ip_set in vpc_attrs.get("PrivateIpSets", {}).get("PrivateIpSet", []):
            sec_ip = ip_set.get("PrivateIpAddress", "")
            if sec_ip:
                ips.add(sec_ip)
        return ips


    inst_params = {
        "PageSize": "100",
    }
    inst_result = _call_with_retry("ecs", "describe-instances", inst_params, region)
    if "error" not in inst_result:
        instances = inst_result.get("Instances", {}).get("Instance", [])
        for inst in instances:
            vpc_attrs = inst.get("VpcAttributes", {})
            all_ips = _extract_ips(vpc_attrs)
            if ip in all_ips:
                sg_ids = inst.get("SecurityGroupIds", {}).get("SecurityGroupId", [])
                return {
                    "found": True,
                    "region": region,
                    "instance_id": inst.get("InstanceId", ""),
                    "vpc_id": vpc_attrs.get("VpcId", ""),
                    "vswitch_id": vpc_attrs.get("VSwitchId", ""),
                    "security_groups": sg_ids,
                    "source": "instances",
                }



    fallback_params = {"PageSize": "1", "Status": "Running"}
    fallback_result = _call_with_retry("ecs", "describe-instances", fallback_params, region)
    vpc_id = None
    if "error" not in fallback_result:
        fallback_instances = fallback_result.get("Instances", {}).get("Instance", [])
        if fallback_instances:
            vpc_id = fallback_instances[0].get("VpcAttributes", {}).get("VpcId", "")

    if vpc_id:
        eni_params = {
            "PageSize": "100",
            "VpcId": vpc_id,
            "PrivateIpAddress.1": ip,
        }
        eni_result = _call_with_retry("ecs", "describe-network-interfaces", eni_params, region)
        if "error" not in eni_result:
            enis = eni_result.get("NetworkInterfaceSets", {}).get("NetworkInterfaceSet", [])
            if enis:
                eni = enis[0]
                return {
                    "found": True,
                    "region": region,
                    "instance_id": eni.get("InstanceId", ""),
                    "vpc_id": eni.get("VpcId", ""),
                    "vswitch_id": eni.get("VSwitchId", ""),
                    "security_groups": eni.get("SecurityGroupIds", {}).get("SecurityGroupId", []),
                    "source": "eni",
                }

    return {"found": False, "ip": ip}


def find_instance_by_ip(ip: str, region: str = None) -> dict:
    """Resolve a private IP, using a bounded region search when unspecified."""
    regions = [region] if region else [
        "cn-hangzhou", "cn-shanghai", "cn-beijing", "cn-shenzhen", "cn-chengdu",
    ]
    errors = []
    for candidate in regions:
        result = _find_instance_by_ip_in_region(ip, candidate)
        if result.get("found"):
            return result
        if result.get("error"):
            errors.append({"region": candidate, "error": result["error"]})
    response = {"found": False, "ip": ip, "searched_regions": regions}
    if errors:
        response["errors"] = errors
    return response




def describe_network_interfaces(instance_ids: list = None, vpc_id: str = None,
                                 region: str = None) -> dict:
    """Implementation detail."""
    params = {"PageSize": "100"}
    if instance_ids and len(instance_ids) == 1:
        params["InstanceId"] = instance_ids[0]
    if vpc_id:
        params["VpcId"] = vpc_id

    result = _call_with_retry("ecs", "describe-network-interfaces", params, region)
    if "error" in result:
        return result

    enis = result.get("NetworkInterfaceSets", {}).get("NetworkInterfaceSet", [])


    if instance_ids and len(instance_ids) > 1:
        id_set = set(instance_ids)
        enis = [e for e in enis if e.get("InstanceId", "") in id_set]

    summary = []
    for eni in enis:
        private_ips = []
        for ip_set in eni.get("PrivateIpSets", {}).get("PrivateIpSet", []):
            private_ips.append(ip_set.get("PrivateIpAddress", ""))
        summary.append({
            "NetworkInterfaceId": eni.get("NetworkInterfaceId"),
            "InstanceId": eni.get("InstanceId", ""),
            "VpcId": eni.get("VpcId", ""),
            "VSwitchId": eni.get("VSwitchId", ""),
            "PrivateIpAddresses": private_ips,
            "SecurityGroupIds": eni.get("SecurityGroupIds", {}).get("SecurityGroupId", []),
            "Status": eni.get("Status", ""),
            "Type": eni.get("Type", ""),
        })

    return {"enis": summary, "total": len(summary)}




def _get_security_group_type(sg_id: str, region: str = None) -> str:
    """Implementation detail."""
    params = {"SecurityGroupId": sg_id}
    result = _call_with_retry("ecs", "describe-security-groups", params, region)
    if "error" in result:
        return "normal"
    groups = result.get("SecurityGroups", {}).get("SecurityGroup", [])
    if groups:
        return groups[0].get("SecurityGroupType", "normal")
    return "normal"


def describe_security_group_attribute(sg_id: str, direction: str = "all",
                                      region: str = None) -> dict:
    """Implementation detail."""
    params = {"SecurityGroupId": sg_id}
    if direction != "all":
        params["Direction"] = direction

    result = _call_with_retry("ecs", "describe-security-group-attribute", params, region)
    if "error" in result:
        return result



    sg_type = _get_security_group_type(sg_id, region)

    permissions = result.get("Permissions", {}).get("Permission", [])
    ingress_rules = []
    egress_rules = []

    for rule in permissions:
        rule_info = {
            "IpProtocol": rule.get("IpProtocol", "").upper(),
            "PortRange": rule.get("PortRange", ""),
            "SourceCidrIp": rule.get("SourceCidrIp", ""),
            "SourceGroupId": rule.get("SourceGroupId", ""),
            "DestCidrIp": rule.get("DestCidrIp", ""),
            "DestGroupId": rule.get("DestGroupId", ""),
            "Policy": rule.get("Policy", "Accept"),
            "Priority": rule.get("Priority", 1),
            "Direction": rule.get("Direction", ""),
            "Description": rule.get("Description", ""),
            "NicType": rule.get("NicType", ""),
        }
        if rule.get("Direction") == "ingress":
            ingress_rules.append(rule_info)
        elif rule.get("Direction") == "egress":
            egress_rules.append(rule_info)

    return {
        "sg_id": sg_id,
        "sg_name": result.get("SecurityGroupName", ""),
        "vpc_id": result.get("VpcId", ""),
        "sg_type": sg_type,
        "ingress_rules": sorted(ingress_rules, key=lambda r: r["Priority"]),
        "egress_rules": sorted(egress_rules, key=lambda r: r["Priority"]),
        "ingress_count": len(ingress_rules),
        "egress_count": len(egress_rules),
    }


def get_all_sg_rules(sg_ids: list, region: str = None) -> dict:
    """Implementation detail."""
    results = {}
    for sg_id in sg_ids:
        results[sg_id] = describe_security_group_attribute(sg_id, region=region)
    return results


def resolve_security_group_ids(instance_ids: list, region: str = None) -> dict:
    """Resolve security groups from instances, falling back to ENIs."""
    ids = []
    instances = describe_instances(instance_ids=instance_ids, region=region)
    for instance in instances.get("instances", []):
        ids.extend(instance.get("SecurityGroupIds", []))

    if not ids:
        enis = describe_network_interfaces(instance_ids=instance_ids, region=region)
        for eni in enis.get("enis", []):
            ids.extend(eni.get("SecurityGroupIds", []))

    return {
        "security_group_ids": list(dict.fromkeys(filter(None, ids))),
        "instance_ids": instance_ids,
    }


def four_direction_sg_check(source_instance_ids: list, dest_instance_ids: list,
                            source_ip: str, dest_ip: str, protocol: str = "",
                            port: int = 0, region: str = None) -> dict:
    """Run forward and return security-group checks in one deterministic call."""
    source = resolve_security_group_ids(source_instance_ids, region)
    dest = resolve_security_group_ids(dest_instance_ids, region)
    source_sgs = source["security_group_ids"]
    dest_sgs = dest["security_group_ids"]

    def run(sg_ids, direction, ip, check_port):
        results = {}
        for sg_id in sg_ids:
            rules = describe_security_group_attribute(sg_id, region=region)
            results[sg_id] = (rules if "error" in rules else
                              check_security_group_rules(
                                  rules, direction, ip, protocol, check_port))
        return results

    return {
        "source_security_group_ids": source_sgs,
        "destination_security_group_ids": dest_sgs,
        "source_egress": run(source_sgs, "egress", dest_ip, port),
        "dest_ingress": run(dest_sgs, "ingress", source_ip, port),
        "dest_egress": run(dest_sgs, "egress", source_ip, 0),
        "source_ingress": run(source_sgs, "ingress", dest_ip, 0),
        "four_direction_check_complete": bool(source_sgs and dest_sgs),
    }




def _port_in_range(port: int, port_range: str) -> bool:
    """Implementation detail."""
    if not port_range or port_range == "-1/-1":
        return True
    try:
        parts = port_range.split("/")
        low = int(parts[0])
        high = int(parts[1])
        return low <= port <= high
    except (ValueError, IndexError):
        return False


def _protocol_matches(rule_proto: str, target_proto: str) -> bool:
    """Implementation detail."""
    rule_proto = rule_proto.upper()
    target_proto = target_proto.upper()
    if rule_proto == "ALL" or target_proto == "ALL" or not target_proto:
        return True
    return rule_proto == target_proto


def check_security_group_rules(sg_rules: dict, direction: str,
                                ip: str, protocol: str = "",
                                port: int = 0) -> dict:
    """Implementation detail."""
    rules = sg_rules.get(f"{direction}_rules", [])
    sg_type = sg_rules.get("sg_type", "normal")

    if not rules:

        if sg_type == "normal" and direction == "egress":
            return {
                "verdict": "allow",
                "matched_rule": None,
                "checked_rules": 0,
                "sg_type": sg_type,
                "details": f"安全组 {sg_rules.get('sg_id', '')} 无显式出站规则，普通安全组默认允许所有出站流量",
            }
        return {
            "verdict": "deny",
            "matched_rule": None,
            "checked_rules": 0,
            "sg_type": sg_type,
            "details": f"安全组 {sg_rules.get('sg_id', '')} 无{direction}规则，"
                       + ("企业安全组默认拒绝所有流量（含出站）" if sg_type == "enterprise"
                          else "默认拒绝"),
        }

    for rule in rules:

        if not _protocol_matches(rule["IpProtocol"], protocol):
            continue


        if protocol.upper() != "ICMP" and port > 0:
            if not _port_in_range(port, rule["PortRange"]):
                continue


        if direction == "ingress":
            cidr = rule["SourceCidrIp"]
            group_id = rule["SourceGroupId"]
        else:
            cidr = rule["DestCidrIp"]
            group_id = rule["DestGroupId"]


        if group_id and not cidr:
            continue

        if cidr and ip:
            if not cidr_contains(cidr, ip):
                continue


        return {
            "verdict": "allow" if rule["Policy"] == "Accept" else "deny",
            "matched_rule": rule,
            "checked_rules": len(rules),
            "sg_type": sg_type,
            "details": f"匹配规则: {rule['IpProtocol']} {rule['PortRange']} "
                       f"{'源' if direction == 'ingress' else '目的'}: {cidr or group_id} "
                       f"策略: {rule['Policy']} 优先级: {rule['Priority']}",
        }


    proto_str = protocol or "ALL"
    port_str = f":{port}" if port else ""

    if sg_type == "normal" and direction == "egress":
        return {
            "verdict": "allow",
            "matched_rule": None,
            "checked_rules": len(rules),
            "sg_type": sg_type,
            "details": f"无匹配显式出站规则，普通安全组默认允许所有出站流量",
        }
    return {
        "verdict": "deny",
        "matched_rule": None,
        "checked_rules": len(rules),
        "sg_type": sg_type,
        "details": f"无匹配规则: {proto_str}{port_str} IP={ip}，"
                   + ("企业安全组默认拒绝所有未匹配流量（含出站）" if sg_type == "enterprise"
                      else "VPC 安全组默认拒绝所有未匹配流量"),
    }




def main():
    import argparse

    parser = argparse.ArgumentParser(description="ECS 实例与安全组诊断")
    sub = parser.add_subparsers(dest="action")


    p = sub.add_parser("instances", help="查询 ECS 实例")
    p.add_argument("--instance-ids", help="实例 ID，逗号分隔")
    p.add_argument("--ips", help="私网 IP，逗号分隔")
    p.add_argument("--vpc-id", help="VPC ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("enis", help="查询弹性网卡")
    p.add_argument("--instance-ids", help="实例 ID，逗号分隔")
    p.add_argument("--vpc-id", help="VPC ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("sg-rules", help="查询安全组规则")
    p.add_argument("--sg-ids", help="安全组 ID，逗号分隔")
    p.add_argument("--instance-ids", help="自动解析安全组的实例 ID，逗号分隔")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("sg-check", help="检查安全组规则匹配")
    p.add_argument("--sg-ids", help="安全组 ID，逗号分隔")
    p.add_argument("--instance-ids", help="自动解析安全组的实例 ID，逗号分隔")
    p.add_argument("--direction", required=True, choices=["ingress", "egress"])
    p.add_argument("--ip", required=True, help="源/目的 IP")
    p.add_argument("--protocol", default="", help="协议")
    p.add_argument("--port", type=int, default=0, help="端口")
    p.add_argument("--region", help="地域")

    p = sub.add_parser("sg-four-direction-check", help="一次检查企业安全组四个方向")
    p.add_argument("--source-instance-ids", required=True, help="源实例 ID，逗号分隔")
    p.add_argument("--dest-instance-ids", required=True, help="目的实例 ID，逗号分隔")
    p.add_argument("--source-ip", required=True)
    p.add_argument("--dest-ip", required=True)
    p.add_argument("--protocol", default="")
    p.add_argument("--port", type=int, default=0)
    p.add_argument("--region", help="地域")


    p = sub.add_parser("find-by-ip", help="通过私网 IP 反查实例")
    p.add_argument("--ip", required=True, help="私网 IP")
    p.add_argument("--region", help="地域")

    args = parser.parse_args()

    if args.action == "instances":
        ids = args.instance_ids.split(",") if args.instance_ids else None
        ips = args.ips.split(",") if args.ips else None
        result = describe_instances(instance_ids=ids, private_ips=ips,
                                    vpc_id=args.vpc_id, region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "enis":
        ids = args.instance_ids.split(",") if args.instance_ids else None
        result = describe_network_interfaces(instance_ids=ids,
                                              vpc_id=args.vpc_id, region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "sg-rules":
        sg_ids = args.sg_ids.split(",") if args.sg_ids else []
        requested_instance_ids = args.instance_ids.split(",") if args.instance_ids else []
        if args.instance_ids:
            resolved = resolve_security_group_ids(requested_instance_ids, args.region)
            sg_ids.extend(resolved["security_group_ids"])
        if not sg_ids:
            result = {
                "security_groups": {}, "total": 0, "status": "unavailable",
                "instance_ids": requested_instance_ids,
                "details": "实例或 ENI 查询未返回安全组 ID；保留此结构化降级结果并继续独立检查，禁止改用直接 aliyun CLI。",
            }
        else:
            result = get_all_sg_rules(list(dict.fromkeys(sg_ids)), region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "sg-check":
        sg_ids = args.sg_ids.split(",") if args.sg_ids else []
        requested_instance_ids = args.instance_ids.split(",") if args.instance_ids else []
        if args.instance_ids:
            resolved = resolve_security_group_ids(requested_instance_ids, args.region)
            sg_ids.extend(resolved["security_group_ids"])
        if not sg_ids:
            print(json.dumps({
                "status": "unavailable", "instance_ids": requested_instance_ids,
                "details": "实例或 ENI 查询未返回安全组 ID；无法执行规则匹配，禁止改用直接 aliyun CLI。",
            }, ensure_ascii=False, indent=2))
            return
        results = {}
        for sg_id in sg_ids:
            sg_data = describe_security_group_attribute(sg_id, region=args.region)
            if "error" in sg_data:
                results[sg_id] = sg_data
            else:
                results[sg_id] = check_security_group_rules(
                    sg_data, args.direction, args.ip, args.protocol, args.port
                )
        print(json.dumps(results, ensure_ascii=False, indent=2))

    elif args.action == "sg-four-direction-check":
        result = four_direction_sg_check(
            args.source_instance_ids.split(","),
            args.dest_instance_ids.split(","),
            args.source_ip, args.dest_ip, args.protocol, args.port, args.region,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "find-by-ip":
        result = find_instance_by_ip(args.ip, region=args.region)
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
