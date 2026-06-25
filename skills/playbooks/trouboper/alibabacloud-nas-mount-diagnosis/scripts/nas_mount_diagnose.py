#!/usr/bin/env python3
"""
NAS Mount Failure Diagnosis Script
Automatically checks NAS file system, mount targets, permission groups, security groups, etc. via Alibaba Cloud OpenAPI.
Usage: python3 nas_mount_diagnose.py --file-system-id <fs-id> --region <region> [--ecs-instance-id <i-xxx>]
"""

import argparse
import json
import subprocess
import sys


def log(msg):
    """Output diagnostic messages to stderr"""
    print(msg, file=sys.stderr)


def run_aliyun_cli(service, action, params, region):
    """Execute aliyun CLI command and return parsed JSON result"""
    cmd = ["aliyun", service, action]
    # ECS and VPC plugin mode uses --biz-region-id, NAS uses --region
    if service in ("ecs", "vpc"):
        cmd.extend(["--biz-region-id", region])
    else:
        cmd.extend(["--region", region])
    for k, v in params.items():
        cmd.extend([f"--{k}", str(v)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None, result.stderr.strip()
        return json.loads(result.stdout), None
    except FileNotFoundError:
        return None, "aliyun CLI not installed, please install first: https://help.aliyun.com/document_detail/139508.html"
    except subprocess.TimeoutExpired:
        return None, "aliyun CLI execution timed out"
    except json.JSONDecodeError:
        return None, f"Failed to parse response: {result.stdout}"


def check_file_system(fs_id, region):
    """Check file system basic information"""
    log(f"[1/7] Checking file system {fs_id} ...")

    data, err = run_aliyun_cli("nas", "describe-file-systems", {"file-system-id": fs_id}, region)
    if err:
        log(f"  Query failed: {err}")
        return None, {"check": "file_system", "status": "error", "message": err}

    file_systems = data.get("FileSystems", {}).get("FileSystem", [])
    if not file_systems:
        msg = f"File system {fs_id} not found, please verify the ID and Region"
        log(f"  {msg}")
        return None, {"check": "file_system", "status": "fail", "message": msg}

    fs = file_systems[0]
    result = {
        "check": "file_system",
        "status": "pass" if fs.get("Status") == "Running" else "fail",
        "file_system_id": fs_id,
        "file_system_type": fs.get("FileSystemType", "unknown"),
        "protocol_type": fs.get("ProtocolType", "unknown"),
        "fs_status": fs.get("Status", "unknown"),
    }
    log(f"  type={result['file_system_type']}, protocol={result['protocol_type']}, status={result['fs_status']}")
    return fs, result


def check_mount_targets(fs_id, region):
    """Check mount target information"""
    log(f"[2/7] Checking mount targets ...")

    data, err = run_aliyun_cli("nas", "describe-mount-targets", {"file-system-id": fs_id}, region)
    if err:
        log(f"  Query failed: {err}")
        return [], {"check": "mount_targets", "status": "error", "message": err}

    mount_targets = data.get("MountTargets", {}).get("MountTarget", [])
    if not mount_targets:
        msg = f"File system {fs_id} has no mount targets"
        log(f"  {msg}")
        return [], {"check": "mount_targets", "status": "fail", "message": msg}

    targets_info = []
    all_active = True
    for mt in mount_targets:
        status = mt.get("Status", "")
        if status != "Active":
            all_active = False
        targets_info.append({
            "domain": mt.get("MountTargetDomain", ""),
            "status": status,
            "vpc_id": mt.get("VpcId", ""),
            "vsw_id": mt.get("VswId", ""),
            "access_group": mt.get("AccessGroup", ""),
            "network_type": mt.get("NetworkType", ""),
        })
        log(f"  mount_target={targets_info[-1]['domain']}, status={status}, VPC={targets_info[-1]['vpc_id']}")

    result = {
        "check": "mount_targets",
        "status": "pass" if all_active else "fail",
        "targets": targets_info,
    }
    return mount_targets, result


def check_access_rules(access_group_name, region, file_system_type="standard"):
    """Check permission group rules"""
    fs_type_label = "extreme" if file_system_type == "extreme" else "general-purpose"
    log(f"[3/7] Checking permission group {access_group_name} (type={fs_type_label}) ...")

    params = {"access-group-name": access_group_name, "file-system-type": file_system_type}
    data, err = run_aliyun_cli("nas", "describe-access-rules", params, region)
    if err:
        log(f"  Query failed: {err}")
        return [], {"check": "access_rules", "status": "error", "access_group": access_group_name, "message": err}

    rules = data.get("AccessRules", {}).get("AccessRule", [])
    if not rules:
        msg = f"Permission group {access_group_name} has no rules configured"
        log(f"  {msg}")
        return [], {"check": "access_rules", "status": "fail", "access_group": access_group_name, "message": msg}

    rules_info = []
    for rule in rules:
        rules_info.append({
            "source_cidr": rule.get("SourceCidrIp", ""),
            "rw_access": rule.get("RWAccess", ""),
            "user_access": rule.get("UserAccess", ""),
            "priority": rule.get("Priority", ""),
        })
    log(f"  {len(rules)} rule(s) found")

    result = {
        "check": "access_rules",
        "status": "pass",
        "access_group": access_group_name,
        "rules": rules_info,
    }
    return rules, result


def check_ecs_instance(instance_id, region):
    """Check ECS instance information"""
    log(f"[4/7] Checking ECS instance {instance_id} ...")

    data, err = run_aliyun_cli("ecs", "describe-instances",
                               {"instance-ids": json.dumps([instance_id])}, region)
    if err:
        log(f"  Query failed: {err}")
        return None, {"check": "ecs_instance", "status": "error", "message": err}

    instances = data.get("Instances", {}).get("Instance", [])
    if not instances:
        msg = f"ECS instance {instance_id} not found"
        log(f"  {msg}")
        return None, {"check": "ecs_instance", "status": "fail", "message": msg}

    inst = instances[0]
    vpc_id = inst.get("VpcAttributes", {}).get("VpcId", "")
    private_ips = inst.get("VpcAttributes", {}).get("PrivateIpAddress", {}).get("IpAddress", [])
    sg_ids = inst.get("SecurityGroupIds", {}).get("SecurityGroupId", [])
    status = inst.get("Status", "")

    result = {
        "check": "ecs_instance",
        "status": "pass" if status == "Running" else "fail",
        "instance_id": instance_id,
        "ecs_status": status,
        "os_type": inst.get("OSType", ""),
        "os_name": inst.get("OSName", ""),
        "vpc_id": vpc_id,
        "private_ips": private_ips,
        "security_group_ids": sg_ids,
    }
    log(f"  status={status}, VPC={vpc_id}, IP={','.join(private_ips)}, security_groups={','.join(sg_ids)}")
    return inst, result


def check_security_group(sg_id, region, protocol_type):
    """Check if security group rules allow NAS ports"""
    log(f"[5/7] Checking security group {sg_id} ...")

    # Query security group type first
    sg_type = "normal"
    sg_data, sg_err = run_aliyun_cli("ecs", "describe-security-groups",
                                      {"security-group-id": sg_id}, region)
    if not sg_err:
        sg_list = sg_data.get("SecurityGroups", {}).get("SecurityGroup", [])
        if sg_list:
            sg_type = sg_list[0].get("SecurityGroupType", "normal")

    sg_type_label = "normal" if sg_type == "normal" else "enterprise"
    log(f"  Security group type: {sg_type_label}")

    data, err = run_aliyun_cli("ecs", "describe-security-group-attribute",
                               {"security-group-id": sg_id, "direction": "egress"}, region)
    if err:
        log(f"  Query failed: {err}")
        return {"check": "security_group", "security_group_id": sg_id, "status": "error", "message": err}

    # Determine required ports based on protocol type
    if protocol_type.upper() == "NFS":
        required_ports = [2049, 111]
    else:
        required_ports = [445]

    permissions = data.get("Permissions", {}).get("Permission", [])
    egress_rules = [p for p in permissions if p.get("Direction") == "egress"]

    port_results = []
    overall_pass = True

    for port in required_ports:
        port_blocked = False
        for rule in egress_rules:
            if rule.get("Policy") != "Drop":
                continue
            port_range = rule.get("PortRange", "")
            try:
                parts = port_range.split("/")
                if port_range == "-1/-1" or (len(parts) == 2 and int(parts[0]) <= port <= int(parts[1])):
                    port_blocked = True
                    break
            except (ValueError, IndexError):
                continue

        if port_blocked:
            port_results.append({"port": port, "status": "blocked", "reason": "explicit deny rule"})
            overall_pass = False
            log(f"  Port {port}: blocked by explicit deny rule")
            continue

        port_explicitly_allowed = False
        for rule in egress_rules:
            if rule.get("Policy") != "Accept":
                continue
            port_range = rule.get("PortRange", "")
            try:
                if port_range == "-1/-1":
                    port_explicitly_allowed = True
                    break
                parts = port_range.split("/")
                if len(parts) == 2 and int(parts[0]) <= port <= int(parts[1]):
                    port_explicitly_allowed = True
                    break
            except (ValueError, IndexError):
                continue

        if port_explicitly_allowed:
            port_results.append({"port": port, "status": "allowed", "reason": "explicit allow rule"})
            log(f"  Port {port}: explicitly allowed")
        elif sg_type == "normal":
            port_results.append({"port": port, "status": "allowed", "reason": "normal security group allows all egress by default"})
            log(f"  Port {port}: allowed by normal security group default")
        else:
            port_results.append({"port": port, "status": "blocked", "reason": "enterprise security group requires explicit egress allow rule"})
            overall_pass = False
            log(f"  Port {port}: not allowed by enterprise security group")

    return {
        "check": "security_group",
        "security_group_id": sg_id,
        "security_group_type": sg_type,
        "security_group_type_label": sg_type_label,
        "status": "pass" if overall_pass else "fail",
        "ports": port_results,
    }


def check_vpc_consistency(mount_target, ecs_instance, protocol_type):
    """Check VPC consistency. Output warning with connectivity check commands when VPCs differ"""
    log(f"[6/7] Checking VPC consistency ...")

    mt_vpc = mount_target.get("VpcId", "")
    mt_domain = mount_target.get("MountTargetDomain", "")
    ecs_vpc = ecs_instance.get("VpcAttributes", {}).get("VpcId", "")

    consistent = mt_vpc == ecs_vpc
    log(f"  mount_target_VPC={mt_vpc}, ECS_VPC={ecs_vpc}, consistent={'yes' if consistent else 'no'}")

    # NFS port 2049, SMB port 445
    port = 445 if protocol_type.upper() == "SMB" else 2049

    result = {
        "check": "vpc_consistency",
        "mount_target_vpc": mt_vpc,
        "ecs_vpc": ecs_vpc,
    }

    if consistent:
        result["status"] = "pass"
    else:
        result["status"] = "warning"
        result["message"] = (
            f"VPC mismatch (ECS: {ecs_vpc}, mount target: {mt_vpc}). "
            "If network connectivity is established via CEN or other means, mounting is still possible. "
            "Run the following commands on the ECS to verify connectivity:"
        )
        result["connectivity_check"] = [
            f"ping -c 3 {mt_domain}" if mt_domain else "ping -c 3 <mount-target-domain>",
            f"nc -zv {mt_domain} {port}" if mt_domain else f"nc -zv <mount-target-domain> {port}",
        ]
        log(f"  VPC mismatch, recommend checking connectivity from ECS to mount target {mt_domain} (ping + port {port})")

    return result


def check_ip_in_access_rules(ecs_instance, access_rules):
    """Check if ECS IP is authorized in permission group rules"""
    log(f"[7/7] Checking ECS IP authorization ...")

    private_ips = ecs_instance.get("VpcAttributes", {}).get("PrivateIpAddress", {}).get("IpAddress", [])
    if not private_ips:
        return {"check": "ip_authorization", "status": "warning", "message": "Failed to get ECS private IP"}

    ip_results = []
    overall_pass = True

    for ip in private_ips:
        ip_authorized = False
        matched_rule = None
        for rule in access_rules:
            source_cidr = rule.get("SourceCidrIp", "")
            if source_cidr in ("0.0.0.0/0", "0.0.0.0"):
                ip_authorized = True
                matched_rule = source_cidr
                break
            if source_cidr == ip or source_cidr == f"{ip}/32":
                ip_authorized = True
                matched_rule = source_cidr
                break
            if "/" in source_cidr:
                try:
                    import ipaddress
                    if ipaddress.ip_address(ip) in ipaddress.ip_network(source_cidr, strict=False):
                        ip_authorized = True
                        matched_rule = source_cidr
                        break
                except (ValueError, ImportError):
                    pass

        if ip_authorized:
            ip_results.append({"ip": ip, "status": "authorized", "matched_rule": matched_rule})
            log(f"  IP {ip}: authorized (matched rule {matched_rule})")
        else:
            ip_results.append({"ip": ip, "status": "unauthorized"})
            overall_pass = False
            log(f"  IP {ip}: unauthorized")

    return {
        "check": "ip_authorization",
        "status": "pass" if overall_pass else "fail",
        "ips": ip_results,
    }


def check_extreme_mount_path(fs_type, mount_path):
    """Check Extreme NAS mount path.
    Extreme NAS path mapping: / is equivalent to /share (root directory), /subdir is equivalent to /share/subdir.
    Manual mount does not auto-create subdirectories; non-existent subdirectory reports access denied.
    """
    if fs_type != "extreme":
        return None

    log("[Extra check] Extreme NAS mount path validation ...")

    if mount_path is None:
        log("  --mount-path not provided, skipping path check")
        return {
            "check": "extreme_mount_path",
            "status": "warning",
            "message": "Mount path parameter not provided. Note: For Extreme NAS, :/ and :/share are equivalent, both point to root directory",
        }

    # Check if root directory: / and /share are equivalent
    is_root = mount_path in ("/", "/share")
    # Check if subdirectory
    is_subdir = (not is_root) and (
        mount_path.startswith("/share/") or
        (mount_path.startswith("/") and mount_path != "/")
    )

    if is_root:
        log(f"  Path {mount_path} is Extreme NAS root directory (/ and /share are equivalent)")
        return {
            "check": "extreme_mount_path",
            "status": "pass",
            "mount_path": mount_path,
        }

    if is_subdir:
        log(f"  Path {mount_path} is a subdirectory. Note: manual mount does not auto-create subdirectories")
        return {
            "check": "extreme_mount_path",
            "status": "warning",
            "mount_path": mount_path,
            "message": (
                f"Mounting subdirectory '{mount_path}': Extreme NAS does not auto-create subdirectories during manual mount. "
                "If the subdirectory does not exist, it will report access denied. "
                "Please mount root directory (:/ or :/share) first, mkdir the subdirectory, then remount"
            ),
        }

    log(f"  Path {mount_path} has unusual format")
    return {
        "check": "extreme_mount_path",
        "status": "warning",
        "mount_path": mount_path,
        "message": f"Path '{mount_path}' has an unusual format. Extreme NAS recommends :/ or :/share (root), or :/share/<subdirectory>",
    }


def main():
    parser = argparse.ArgumentParser(
        description="NAS Mount Failure Diagnosis Tool - Automatically checks configuration via Alibaba Cloud OpenAPI",
        epilog="Example: python3 nas_mount_diagnose.py --file-system-id 0a1b2c --region cn-hangzhou --ecs-instance-id i-bp1xxx",
    )
    parser.add_argument("--file-system-id", required=True, help="NAS file system ID")
    parser.add_argument("--region", required=True, help="Region ID, e.g. cn-hangzhou")
    parser.add_argument("--ecs-instance-id", help="ECS instance ID (optional, enables deeper checks)")
    parser.add_argument("--mount-path", help="Mount path (optional, e.g. / or /share/subdir, for Extreme NAS path validation)")
    parser.add_argument("--protocol", choices=["NFS", "SMB"], help="Protocol type (optional, auto-detected)")

    args = parser.parse_args()

    log("=" * 50)
    log("  NAS Mount Failure Diagnosis")
    log("=" * 50)

    report = {
        "file_system_id": args.file_system_id,
        "region": args.region,
        "ecs_instance_id": args.ecs_instance_id,
        "checks": [],
    }

    # 1. Check file system
    fs, fs_result = check_file_system(args.file_system_id, args.region)
    report["checks"].append(fs_result)
    if not fs:
        report["overall_status"] = "error"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(1)

    protocol = args.protocol or fs.get("ProtocolType", "NFS")
    report["protocol_type"] = protocol
    fs_type = fs.get("FileSystemType", "unknown")

    # Extreme NAS mount path check
    path_result = check_extreme_mount_path(fs_type, args.mount_path)
    if path_result:
        report["checks"].append(path_result)

    # 2. Check mount targets
    mount_targets, mt_result = check_mount_targets(args.file_system_id, args.region)
    report["checks"].append(mt_result)

    # 3. Check permission group rules (by file system type: standard/extreme)
    access_rules = []
    for mt in mount_targets:
        access_group = mt.get("AccessGroup", "")
        if access_group:
            rules, ar_result = check_access_rules(access_group, args.region, fs_type)
            report["checks"].append(ar_result)
            access_rules.extend(rules)

    # 4-7. If ECS instance ID is provided, perform deeper checks
    if args.ecs_instance_id:
        ecs, ecs_result = check_ecs_instance(args.ecs_instance_id, args.region)
        report["checks"].append(ecs_result)

        if ecs and mount_targets:
            # Check security groups
            sg_ids = ecs.get("SecurityGroupIds", {}).get("SecurityGroupId", [])
            for sg_id in sg_ids:
                sg_result = check_security_group(sg_id, args.region, protocol)
                report["checks"].append(sg_result)

            # Check VPC consistency
            vpc_result = check_vpc_consistency(mount_targets[0], ecs, protocol)
            report["checks"].append(vpc_result)

            # Check IP authorization
            if access_rules:
                ip_result = check_ip_in_access_rules(ecs, access_rules)
                report["checks"].append(ip_result)

    # Aggregate status
    failed_checks = [c for c in report["checks"] if c.get("status") in ("fail", "error")]
    if failed_checks:
        report["overall_status"] = "fail"
        report["failed_checks"] = [c["check"] for c in failed_checks]
    else:
        report["overall_status"] = "pass"

    log(f"\nDiagnosis complete, overall status: {report['overall_status']}")

    # Structured JSON output to stdout
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
