#!/usr/bin/env python3
"""Alibaba Cloud ECS management.

Capabilities:
  - describe_instance_types / describe_instance_type_families  (instance type query)
  - describe_regions / describe_zones / describe_available_resource  (inventory query)
  - describe_price  (pricing)
  - run_instances / describe_instances  (instance creation)
  - create_security_group / authorize_security_group / authorize_security_group_egress
  - describe_images
  - run_command / describe_invocations / describe_invocation_results  (script execution)

All functions use RPC-style API (product=ecs, version=2014-05-26).
"""

from __future__ import annotations

import base64
import sys
import os
import time
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

from common import call_rpc_api, wait_until, pp

PRODUCT = "ecs"
VERSION = "2014-05-26"


def _call(action: str, params: dict | None = None, region: str | None = None) -> dict:
    return call_rpc_api(PRODUCT, VERSION, action, params=params, region=region)


# ---------------------------------------------------------------------------
# Instance type query
# ---------------------------------------------------------------------------

def describe_instance_types(
    instance_type_family: str | None = None,
    instance_types: list[str] | None = None,
    min_cpu: int | None = None,
    max_cpu: int | None = None,
    min_memory: float | None = None,
    max_memory: float | None = None,
    gpu_amount: int | None = None,
    region: str | None = None,
) -> dict:
    """Query ECS instance type specifications.

    Use filters to narrow results (cpu, memory, gpu, family).
    Returns InstanceTypes.InstanceType[].
    """
    params: dict[str, Any] = {}
    if instance_type_family:
        params["InstanceTypeFamily"] = instance_type_family
    if instance_types:
        for i, t in enumerate(instance_types):
            params[f"InstanceTypes.{i+1}"] = t
    if min_cpu is not None:
        params["MinimumCpuCoreCount"] = min_cpu
    if max_cpu is not None:
        params["MaximumCpuCoreCount"] = max_cpu
    if min_memory is not None:
        params["MinimumMemorySize"] = min_memory
    if max_memory is not None:
        params["MaximumMemorySize"] = max_memory
    if gpu_amount is not None:
        params["GPUAmount"] = gpu_amount
    return _call("DescribeInstanceTypes", params, region)


def describe_instance_type_families(
    generation: str | None = None,
    region: str | None = None,
) -> dict:
    """List instance type families (e.g. ecs.g7, ecs.c7)."""
    params: dict[str, Any] = {}
    if generation:
        params["Generation"] = generation
    return _call("DescribeInstanceTypeFamilies", params, region)


def describe_recommend_instance_type(
    cores: int | None = None,
    memory: float | None = None,
    instance_type: str | None = None,
    instance_family_level: str | None = None,
    instance_charge_type: str = "PostPaid",
    spot_strategy: str = "NoSpot",
    priority_strategy: str = "InventoryFirst",
    zone_id: str | None = None,
    system_disk_category: str | None = None,
    max_price: float | None = None,
    scene: str = "CREATE",
    instance_type_family: list[str] | None = None,
    region: str | None = None,
) -> dict:
    """Recommend instance types based on requirements.

    Provide EITHER (cores + memory) OR instance_type, not both.

    Args:
        cores: vCPU count.
        memory: Memory in GiB.
        instance_type: Base instance type to find alternatives for.
        instance_family_level: EntryLevel | EnterpriseLevel | CreditEntryLevel.
        priority_strategy: InventoryFirst | PriceFirst | NewProductFirst.
        max_price: Max hourly price (only for SpotWithPriceLimit).
        scene: CREATE | UPGRADE.
        instance_type_family: Limit to these families, e.g. ["ecs.g7", "ecs.c7"].

    Returns:
        Data.RecommendInstanceType[] with InstanceType, ZoneId, Priority etc.
    """
    params: dict[str, Any] = {
        "NetworkType": "vpc",
        "InstanceChargeType": instance_charge_type,
        "SpotStrategy": spot_strategy,
        "PriorityStrategy": priority_strategy,
        "Scene": scene,
    }
    if cores is not None:
        params["Cores"] = cores
    if memory is not None:
        params["Memory"] = memory
    if instance_type:
        params["InstanceType"] = instance_type
    if instance_family_level:
        params["InstanceFamilyLevel"] = instance_family_level
    if zone_id:
        params["ZoneId"] = zone_id
    if system_disk_category:
        params["SystemDiskCategory"] = system_disk_category
    if max_price is not None:
        params["MaxPrice"] = max_price
    if instance_type_family:
        for i, f in enumerate(instance_type_family):
            params[f"InstanceTypeFamily.{i+1}"] = f
    result = _call("DescribeRecommendInstanceType", params, region)

    for rec in result.get("Data", {}).get("RecommendInstanceType", []):
        inst = rec.get("InstanceType", {})
        mem_mb = inst.get("Memory")
        if isinstance(mem_mb, (int, float)) and mem_mb >= 1024:
            inst["MemoryGB"] = round(mem_mb / 1024, 1)

    return result


# ---------------------------------------------------------------------------
# Inventory query
# ---------------------------------------------------------------------------

def describe_regions(region: str | None = None) -> dict:
    """List all available regions."""
    return _call("DescribeRegions", region=region)


def describe_zones(region: str | None = None) -> dict:
    """List zones in a region."""
    return _call("DescribeZones", region=region)


def describe_available_resource(
    destination_resource: str = "InstanceType",
    zone_id: str | None = None,
    instance_type: str | None = None,
    instance_charge_type: str = "PostPaid",
    io_optimized: str = "optimized",
    region: str | None = None,
) -> dict:
    """Query available resources (instance types, disk types, etc.) by zone.

    destination_resource: InstanceType | SystemDisk | DataDisk | Network
    """
    params: dict[str, Any] = {
        "DestinationResource": destination_resource,
        "InstanceChargeType": instance_charge_type,
        "IoOptimized": io_optimized,
    }
    if zone_id:
        params["ZoneId"] = zone_id
    if instance_type:
        params["InstanceType"] = instance_type
    return _call("DescribeAvailableResource", params, region)


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

def describe_price(
    instance_type: str,
    period: int = 1,
    price_unit: str = "Hour",
    instance_charge_type: str = "PostPaid",
    system_disk_category: str = "cloud_essd",
    system_disk_size: int = 40,
    internet_max_bandwidth_out: int = 0,
    amount: int = 1,
    region: str | None = None,
    zone_id: str | None = None,
) -> dict:
    """Query price for an ECS instance configuration.

    Returns price info including TradePrice, OriginalPrice, DiscountPrice.
    """
    params: dict[str, Any] = {
        "ResourceType": "instance",
        "InstanceType": instance_type,
        "Period": period,
        "PriceUnit": price_unit,
        "InstanceChargeType": instance_charge_type,
        "SystemDisk.Category": system_disk_category,
        "SystemDisk.Size": system_disk_size,
        "InternetMaxBandwidthOut": internet_max_bandwidth_out,
        "Amount": amount,
    }
    if zone_id:
        params["ZoneId"] = zone_id
    return _call("DescribePrice", params, region)


# ---------------------------------------------------------------------------
# Image query
# ---------------------------------------------------------------------------

def describe_images(
    image_name: str | None = None,
    os_type: str | None = None,
    image_family: str | None = None,
    instance_type: str | None = None,
    region: str | None = None,
    page_size: int = 20,
) -> dict:
    """Query available images.

    Common image_family values:
      acs:alibaba_cloud_linux_3_2104_lts_x64, acs:ubuntu_24_04_x64,
      acs:ubuntu_22_04_x64, acs:centos_7_9_x64
    """
    params: dict[str, Any] = {
        "PageSize": page_size,
        "ImageOwnerAlias": "system",
        "Status": "Available",
    }
    if image_name:
        params["ImageName"] = image_name
    if os_type:
        params["OSType"] = os_type
    if image_family:
        params["ImageFamily"] = image_family
    if instance_type:
        params["InstanceType"] = instance_type
    return _call("DescribeImages", params, region)


# ---------------------------------------------------------------------------
# Security groups
# ---------------------------------------------------------------------------

def create_security_group(
    vpc_id: str,
    sg_name: str = "acf-sg",
    description: str = "Created by Alibaba Cloud Compute Provision skill",
    region: str | None = None,
) -> str:
    """Create a security group. Returns SecurityGroupId."""
    params: dict[str, Any] = {
        "VpcId": vpc_id,
        "SecurityGroupName": sg_name,
        "Description": description,
    }
    result = _call("CreateSecurityGroup", params, region)
    sg_id = result.get("SecurityGroupId", "")
    print(f"SecurityGroup created: {sg_id}")
    return sg_id


def authorize_security_group(
    security_group_id: str,
    ip_protocol: str = "tcp",
    port_range: str = "22/22",
    source_cidr_ip: str = "0.0.0.0/0",
    region: str | None = None,
) -> dict:
    """Add an ingress rule to a security group."""
    params: dict[str, Any] = {
        "SecurityGroupId": security_group_id,
        "IpProtocol": ip_protocol,
        "PortRange": port_range,
        "SourceCidrIp": source_cidr_ip,
        "Policy": "Accept",
    }
    return _call("AuthorizeSecurityGroup", params, region)


def authorize_security_group_egress(
    security_group_id: str,
    ip_protocol: str = "all",
    port_range: str = "-1/-1",
    dest_cidr_ip: str = "0.0.0.0/0",
    region: str | None = None,
) -> dict:
    """Add an egress rule to a security group."""
    params: dict[str, Any] = {
        "SecurityGroupId": security_group_id,
        "IpProtocol": ip_protocol,
        "PortRange": port_range,
        "DestCidrIp": dest_cidr_ip,
        "Policy": "Accept",
    }
    return _call("AuthorizeSecurityGroupEgress", params, region)


def setup_security_group(
    vpc_id: str,
    sg_name: str = "acf-sg",
    ingress_rules: list[dict] | None = None,
    region: str | None = None,
) -> str:
    """Create a security group with caller-specified ingress rules + full egress.

    Ingress rules MUST be derived from what the deployed application actually
    needs. Open only the ports the workload requires, and scope the source CIDR
    as tightly as possible. Pass ``None`` or ``[]`` for an internal-only SG
    (no ingress, full egress).

    Args:
        ingress_rules: List of dicts. Each dict accepts:
            - ``port_range``  (str, required): e.g. ``"80/80"``, ``"443/443"``,
              ``"8000/9000"``.
            - ``source_cidr_ip``  (str, default ``"0.0.0.0/0"``): tighten this
              for management ports (SSH/RDP/DB) — e.g. the operator's public
              ``/32`` or an internal CIDR. Only use ``0.0.0.0/0`` for ports
              that genuinely serve the public internet (HTTP/HTTPS).
            - ``ip_protocol``  (str, default ``"tcp"``): ``tcp``/``udp``/``icmp``/``all``.

    Examples:
        # Public web server
        setup_security_group(vpc_id, ingress_rules=[
            {"port_range": "80/80"},
            {"port_range": "443/443"},
        ])

        # Web server + SSH from operator only
        setup_security_group(vpc_id, ingress_rules=[
            {"port_range": "80/80"},
            {"port_range": "443/443"},
            {"port_range": "22/22", "source_cidr_ip": "203.0.113.5/32"},
        ])

        # Internal worker, no ingress
        setup_security_group(vpc_id, ingress_rules=None)

    Returns:
        security_group_id.
    """
    sg_id = create_security_group(vpc_id=vpc_id, sg_name=sg_name, region=region)

    rules = ingress_rules or []
    for rule in rules:
        port_range = rule["port_range"]
        protocol = rule.get("ip_protocol", "tcp")
        source = rule.get("source_cidr_ip", "0.0.0.0/0")
        authorize_security_group(sg_id, protocol, port_range, source, region)

    authorize_security_group_egress(sg_id, "all", "-1/-1", "0.0.0.0/0", region)

    if rules:
        summary = ", ".join(
            f"{r.get('ip_protocol', 'tcp')}/{r['port_range']} from {r.get('source_cidr_ip', '0.0.0.0/0')}"
            for r in rules
        )
        print(f"SecurityGroup {sg_id} configured: ingress=[{summary}] + full egress")
    else:
        print(f"SecurityGroup {sg_id} configured with full egress (no ingress)")
    return sg_id


def delete_security_group(
    security_group_id: str,
    region: str | None = None,
) -> dict:
    """Delete a security group. The SG must have no associated instances."""
    params: dict[str, Any] = {"SecurityGroupId": security_group_id}
    result = _call("DeleteSecurityGroup", params, region)
    print(f"SecurityGroup deleted: {security_group_id}")
    return result


# ---------------------------------------------------------------------------
# Instance creation
# ---------------------------------------------------------------------------

def run_instances(
    instance_type: str,
    vswitch_id: str,
    security_group_id: str,
    image_id: str,
    instance_name: str = "acf-instance",
    system_disk_category: str = "cloud_essd",
    system_disk_size: int = 40,
    internet_max_bandwidth_out: int = 0,
    instance_charge_type: str = "PostPaid",
    amount: int = 1,
    region: str | None = None,
    **extra_params,
) -> dict:
    """Create ECS instance(s) and wait until Running.

    Args:
        internet_max_bandwidth_out: Public network bandwidth in Mbps (0~100).
            0 = no public IP assigned (default).
            >0 = auto-assign public IP with this bandwidth.
            Typical values: 5 (light use), 10-50 (moderate), 100 (heavy).

    Returns RunInstances response with InstanceIdSets.

    Raises:
        ValueError: If UserData is passed. Use run_command() or
            run_command_and_wait() after instance creation instead.
    """
    if "UserData" in extra_params:
        raise ValueError(
            "UserData is not allowed in run_instances(). "
            "Create the instance first, then use run_command() or "
            "run_command_and_wait() to execute scripts on it."
        )

    params: dict[str, Any] = {
        "InstanceType": instance_type,
        "VSwitchId": vswitch_id,
        "SecurityGroupId": security_group_id,
        "ImageId": image_id,
        "InstanceName": instance_name,
        "SystemDisk.Category": system_disk_category,
        "SystemDisk.Size": system_disk_size,
        "InternetMaxBandwidthOut": internet_max_bandwidth_out,
        "InstanceChargeType": instance_charge_type,
        "Amount": amount,
        "InternetChargeType": "PayByTraffic",
    }
    params.update(extra_params)

    result = _call("RunInstances", params, region)
    instance_ids = result.get("InstanceIdSets", {}).get("InstanceIdSet", [])
    print(f"Instances created: {instance_ids}")

    for iid in instance_ids:
        def _check(instance_id=iid):
            info = describe_instances(instance_ids=[instance_id], region=region)
            items = info.get("Instances", {}).get("Instance", [])
            return items[0] if items else {"Status": "Pending"}

        wait_until(_check, {"Running"}, {"Stopped", "Error"}, interval=10, timeout=300)
        print(f"Instance {iid} is Running")

    return result


_FALLBACK_REGIONS = ["cn-hangzhou", "cn-shanghai", "cn-beijing", "cn-shenzhen", "cn-zhangjiakou"]


def find_available_instance_type(
    cores: int = 2,
    memory: float = 4,
    instance_type: str | None = None,
    instance_charge_type: str = "PostPaid",
    system_disk_category: str = "cloud_essd",
    regions: list[str] | None = None,
) -> dict:
    """Find an available instance type with pricing across zones and regions.

    Searches across multiple regions/zones until it finds an instance type
    with stock. Returns the first available option with its pricing info
    so the agent can present cost to the user BEFORE creating anything.

    Args:
        cores: Desired vCPU count (used if instance_type is None).
        memory: Desired memory in GiB (used if instance_type is None).
        instance_type: Explicit instance type to check availability for.
        regions: Regions to try in order. Defaults to _FALLBACK_REGIONS.

    Returns:
        dict with keys: instance_type, region, zone_id, cores, memory,
        price_per_hour, currency. Raise RuntimeError if nothing found.
    """
    candidate_regions = regions or _FALLBACK_REGIONS
    errors: list[str] = []

    for region in candidate_regions:
        print(f"Checking region: {region} ...")

        try:
            recs = describe_recommend_instance_type(
                cores=cores if not instance_type else None,
                memory=memory if not instance_type else None,
                instance_type=instance_type,
                instance_charge_type=instance_charge_type,
                priority_strategy="InventoryFirst",
                system_disk_category=system_disk_category,
                region=region,
            )
        except Exception as e:
            errors.append(f"{region}: {e}")
            continue

        rec_list = recs.get("Data", {}).get("RecommendInstanceType", [])
        if not rec_list:
            errors.append(f"{region}: no instance types available")
            continue

        for rec in rec_list:
            type_info = rec.get("InstanceType", {})
            rec_type = type_info.get("InstanceType", "")
            rec_cores = type_info.get("Cores", cores)
            rec_mem_mb = type_info.get("Memory")
            rec_mem = round(rec_mem_mb / 1024, 1) if isinstance(rec_mem_mb, (int, float)) and rec_mem_mb >= 1024 else rec_mem_mb
            zones = rec.get("Zones", {}).get("zone", [])
            if not zones or not rec_type:
                continue

            zone_id = zones[0].get("ZoneNo", "")
            if not zone_id:
                continue

            try:
                price_info = describe_price(
                    instance_type=rec_type,
                    price_unit="Hour",
                    region=region,
                )
                price_data = price_info.get("PriceInfo", {}).get("Price", {})
                trade_price = price_data.get("TradePrice", 0)
                currency = price_data.get("Currency", "CNY")
            except Exception:
                trade_price = None
                currency = "CNY"

            print(f"  ✅ Found: {rec_type} ({rec_cores}C/{rec_mem}G) in {zone_id}")
            return {
                "instance_type": rec_type,
                "region": region,
                "zone_id": zone_id,
                "cores": rec_cores,
                "memory": rec_mem,
                "price_per_hour": trade_price,
                "currency": currency,
            }

    raise RuntimeError(
        f"No available ECS instance type found after trying {len(candidate_regions)} regions.\n"
        + "\n".join(f"  - {e}" for e in errors)
    )


def create_instance_with_infra(
    instance_type: str,
    zone_id: str,
    image_family: str = "acs:alibaba_cloud_linux_3_2104_lts_x64",
    instance_name: str = "acf-instance",
    system_disk_category: str = "cloud_essd",
    system_disk_size: int = 40,
    internet_max_bandwidth_out: int = 0,
    instance_charge_type: str = "PostPaid",
    region: str | None = None,
    **extra_params,
) -> dict:
    """Create an ECS instance with automatic VPC/VSwitch/SecurityGroup setup.

    Call this AFTER cost confirmation. This function handles all
    infrastructure (VPC, VSwitch, SecurityGroup, Image) automatically.

    Args:
        instance_type: The instance type from find_available_instance_type().
        zone_id: The zone from find_available_instance_type().
        region: The region from find_available_instance_type().

    Returns:
        dict with keys: instance_id, region, zone_id, instance_type,
        vpc_id, vswitch_id, security_group_id, image_id.
    """
    sys.path.insert(0, os.path.dirname(__file__))
    from vpc import ensure_vpc_and_vswitch

    if "UserData" in extra_params:
        raise ValueError(
            "UserData is not allowed. Use run_command() or "
            "run_command_and_wait() after instance creation instead."
        )
    if "image_id" in extra_params or "ImageId" in extra_params:
        raise ValueError(
            "image_id/ImageId should not be passed — it is resolved "
            "internally via image_family. Use the image_family parameter instead."
        )

    vpc_id, vsw_id, vpc_is_new, vsw_is_new = ensure_vpc_and_vswitch(
        zone_id=zone_id, region=region,
    )

    sg_id = create_security_group(vpc_id=vpc_id, region=region)
    authorize_security_group_egress(security_group_id=sg_id, region=region)
    if internet_max_bandwidth_out > 0:
        authorize_security_group(
            security_group_id=sg_id, port_range="22/22", region=region
        )

    imgs = describe_images(
        image_family=image_family, instance_type=instance_type, region=region
    )
    img_list = imgs.get("Images", {}).get("Image", [])
    if not img_list:
        _rollback_infra(sg_id, vsw_id if vsw_is_new else None,
                        vpc_id if vpc_is_new else None, region)
        raise RuntimeError(f"No image found for family={image_family}, type={instance_type}, region={region}")
    img_id = img_list[0]["ImageId"]

    try:
        result = run_instances(
            instance_type=instance_type,
            vswitch_id=vsw_id,
            security_group_id=sg_id,
            image_id=img_id,
            instance_name=instance_name,
            system_disk_category=system_disk_category,
            system_disk_size=system_disk_size,
            internet_max_bandwidth_out=internet_max_bandwidth_out,
            instance_charge_type=instance_charge_type,
            region=region,
            **extra_params,
        )
    except Exception:
        _rollback_infra(sg_id, vsw_id if vsw_is_new else None,
                        vpc_id if vpc_is_new else None, region)
        raise

    iid = result.get("InstanceIdSets", {}).get("InstanceIdSet", [""])[0]
    print(f"✅ Instance created: {iid} ({instance_type} in {zone_id})")
    return {
        "instance_id": iid,
        "region": region,
        "zone_id": zone_id,
        "instance_type": instance_type,
        "vpc_id": vpc_id,
        "vswitch_id": vsw_id,
        "security_group_id": sg_id,
        "image_id": img_id,
        "vpc_is_new": vpc_is_new,
        "vswitch_is_new": vsw_is_new,
    }


def _rollback_infra(
    sg_id: str | None, vsw_id: str | None, vpc_id: str | None, region: str | None
) -> None:
    """Best-effort cleanup of infra created before instance creation failed."""
    print("⚠️ Instance creation failed, rolling back infrastructure ...")
    if sg_id:
        try:
            delete_security_group(sg_id, region=region)
        except Exception as e:
            print(f"  ⚠️ Rollback SG {sg_id}: {e}")
    if vsw_id:
        try:
            from vpc import delete_vswitch
            delete_vswitch(vsw_id, region=region)
        except Exception as e:
            print(f"  ⚠️ Rollback VSwitch {vsw_id}: {e}")
    if vpc_id:
        try:
            from vpc import delete_vpc
            delete_vpc(vpc_id, region=region)
        except Exception as e:
            print(f"  ⚠️ Rollback VPC {vpc_id}: {e}")


def describe_instances(
    instance_ids: list[str] | None = None,
    instance_name: str | None = None,
    status: str | None = None,
    region: str | None = None,
    page_size: int = 50,
) -> dict:
    """Query ECS instances."""
    params: dict[str, Any] = {"PageSize": page_size}
    if instance_ids:
        import json as _json
        params["InstanceIds"] = _json.dumps(instance_ids)
    if instance_name:
        params["InstanceName"] = instance_name
    if status:
        params["Status"] = status
    return _call("DescribeInstances", params, region)


def delete_instances(
    instance_ids: list[str],
    force: bool = True,
    region: str | None = None,
    max_retries: int = 5,
    retry_interval: int = 15,
) -> dict:
    """Release (delete) one or more ECS instances.

    Retries automatically on IncorrectInstanceStatus (e.g. instance still
    initializing after RunInstances). Waits retry_interval seconds between
    attempts, up to max_retries times.
    """
    params: dict[str, Any] = {
        "Force": force,
    }
    for i, iid in enumerate(instance_ids):
        params[f"InstanceId.{i+1}"] = iid

    for attempt in range(1, max_retries + 1):
        try:
            result = _call("DeleteInstances", params, region)
            print(f"Instances released: {instance_ids}")
            return result
        except Exception as e:
            err_str = str(e)
            if "IncorrectInstanceStatus" in err_str and attempt < max_retries:
                print(f"  Instance not ready for release (attempt {attempt}/{max_retries}), "
                      f"retrying in {retry_interval}s...")
                time.sleep(retry_interval)
            else:
                raise


# ---------------------------------------------------------------------------
# Script execution (Cloud Assistant)
# ---------------------------------------------------------------------------

def run_command(
    instance_id: str,
    command_content: str | None = None,
    command_type: str = "RunShellScript",
    timeout: int = 600,
    region: str | None = None,
    script_path: str | None = None,
) -> str:
    """Execute a script on an ECS instance via Cloud Assistant.

    Args:
        instance_id: Target ECS instance.
        command_content: Script content (shell or python). Ignored if script_path is set.
        command_type: RunShellScript | RunPythonScript | RunBatScript | RunPowerShellScript.
        timeout: Command timeout in seconds.
        script_path: Local file path to read script content from.

    Provide either command_content or script_path. script_path takes priority.

    Returns:
        InvokeId for tracking.
    """
    if script_path:
        with open(os.path.expanduser(script_path), "r", encoding="utf-8") as f:
            command_content = f.read()
        print(f"Script loaded from: {script_path} ({len(command_content)} bytes)")
    if not command_content:
        raise ValueError("Either command_content or script_path must be provided")

    encoded = base64.b64encode(command_content.encode("utf-8")).decode("utf-8")
    params: dict[str, Any] = {
        "Type": command_type,
        "CommandContent": encoded,
        "InstanceId.1": instance_id,
        "Timeout": timeout,
        "ContentEncoding": "Base64",
    }
    result = _call("RunCommand", params, region)
    invoke_id = result.get("InvokeId", "")
    print(f"Command submitted, InvokeId: {invoke_id}")
    return invoke_id


def describe_invocations(
    invoke_id: str,
    region: str | None = None,
) -> dict:
    """Query invocation status."""
    params: dict[str, Any] = {"InvokeId": invoke_id}
    return _call("DescribeInvocations", params, region)


def describe_invocation_results(
    invoke_id: str,
    instance_id: str | None = None,
    region: str | None = None,
) -> dict:
    """Get invocation results (stdout/stderr)."""
    params: dict[str, Any] = {"InvokeId": invoke_id}
    if instance_id:
        params["InstanceId"] = instance_id
    return _call("DescribeInvocationResults", params, region)


def run_command_and_wait(
    instance_id: str,
    command_content: str | None = None,
    command_type: str = "RunShellScript",
    timeout: int = 600,
    region: str | None = None,
    script_path: str | None = None,
) -> dict:
    """Execute a script and wait for completion. Returns invocation result.

    Provide either command_content or script_path. script_path takes priority.
    Result includes Output (Base64 encoded), ExitCode, ErrorInfo, etc.
    """
    invoke_id = run_command(instance_id, command_content, command_type, timeout, region, script_path)

    def _check():
        inv = describe_invocations(invoke_id, region)
        items = inv.get("Invocations", {}).get("Invocation", [])
        if not items:
            return {"InvokeStatus": "Pending"}
        status = items[0].get("InvocationStatus", "Pending")
        return {"Status": status}

    wait_until(
        _check,
        target_statuses={"Success", "Finished", "Failed", "PartialFailed", "Stopped"},
        interval=5,
        timeout=timeout + 60,
        status_key="Status",
    )

    result = describe_invocation_results(invoke_id, instance_id, region)
    items = result.get("Invocation", {}).get("InvocationResults", {}).get("InvocationResult", [])
    if items:
        item = items[0]
        output_b64 = item.get("Output", "")
        if output_b64:
            try:
                item["DecodedOutput"] = base64.b64decode(output_b64).decode("utf-8", errors="replace")
            except Exception:
                pass
        print(f"Command exit code: {item.get('ExitCode')}")
        if item.get("DecodedOutput"):
            print(f"Output:\n{item['DecodedOutput']}")
        return item

    return result


def run_command_and_cleanup(
    instance_id: str,
    command_content: str | None = None,
    command_type: str = "RunShellScript",
    timeout: int = 600,
    region: str | None = None,
    script_path: str | None = None,
    security_group_id: str | None = None,
    vpc_id: str | None = None,
    vswitch_id: str | None = None,
    infra: dict | None = None,
) -> dict:
    """Execute a script, wait for completion, then release the instance and infra.

    For one-shot tasks: runs the script, collects output, then cleans up
    the instance + security group (always) and VSwitch + VPC (only if newly
    created, not shared/reused).

    Preferred usage — pass the return value of create_instance_with_infra()
    as ``infra`` and omit the individual ID args:

        infra = create_instance_with_infra(...)
        run_command_and_cleanup(
            instance_id=infra["instance_id"],
            command_content="echo hi",
            region=infra["region"],
            infra=infra,
        )

    When ``infra`` is provided, vpc_id/vswitch_id/security_group_id are
    read from it, and VPC/VSwitch are only deleted if they were freshly
    created (``vpc_is_new`` / ``vswitch_is_new`` flags).

    Returns:
        The command invocation result (same as run_command_and_wait).
    """
    if infra is not None:
        security_group_id = security_group_id or infra.get("security_group_id")
        region = region or infra.get("region")
        if infra.get("vswitch_is_new"):
            vswitch_id = vswitch_id or infra.get("vswitch_id")
        else:
            vswitch_id = None
        if infra.get("vpc_is_new"):
            vpc_id = vpc_id or infra.get("vpc_id")
        else:
            vpc_id = None

    try:
        result = run_command_and_wait(
            instance_id=instance_id,
            command_content=command_content,
            command_type=command_type,
            timeout=timeout,
            region=region,
            script_path=script_path,
        )
    except Exception as e:
        print(f"⚠️ Command failed: {e}")
        result = {"Error": str(e), "ExitCode": -1}

    print(f"\n🧹 Cleaning up resources ...")

    try:
        delete_instances([instance_id], force=True, region=region)
        _wait_instance_deleted(instance_id, region=region)
    except Exception as e:
        print(f"  ⚠️ Failed to delete instance {instance_id}: {e}")

    if security_group_id:
        _retry_cleanup(
            lambda: delete_security_group(security_group_id, region=region),
            f"SecurityGroup {security_group_id}",
        )

    if vswitch_id:
        sys.path.insert(0, os.path.dirname(__file__))
        from vpc import delete_vswitch
        _retry_cleanup(
            lambda: delete_vswitch(vswitch_id, region=region),
            f"VSwitch {vswitch_id}",
        )

    if vpc_id:
        from vpc import delete_vpc
        _retry_cleanup(
            lambda: delete_vpc(vpc_id, region=region),
            f"VPC {vpc_id}",
        )

    print("🧹 Cleanup complete.")
    return result


def _retry_cleanup(
    fn, resource_label: str, max_retries: int = 5, interval: int = 15
) -> None:
    """Retry a cleanup operation, tolerating DependencyViolation delays."""
    for attempt in range(1, max_retries + 1):
        try:
            fn()
            print(f"  {resource_label} deleted.")
            return
        except Exception as e:
            err_str = str(e)
            if "DependencyViolation" in err_str and attempt < max_retries:
                print(f"  {resource_label}: dependency not yet released (attempt {attempt}/{max_retries}), retrying in {interval}s...")
                time.sleep(interval)
            else:
                print(f"  ⚠️ Failed to delete {resource_label}: {e}")
                return


def _wait_instance_deleted(
    instance_id: str, region: str | None = None, timeout: int = 120, interval: int = 5
) -> None:
    """Poll until the instance disappears from DescribeInstances."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        info = describe_instances(instance_ids=[instance_id], region=region)
        items = info.get("Instances", {}).get("Instance", [])
        if not items:
            print(f"  Instance {instance_id} released.")
            return
        status = items[0].get("Status", "")
        print(f"  Instance {instance_id} status: {status}, waiting ...")
        time.sleep(interval)
    print(f"  ⚠️ Timed out waiting for instance {instance_id} to be released.")
