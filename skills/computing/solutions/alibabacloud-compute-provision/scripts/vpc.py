#!/usr/bin/env python3
"""Alibaba Cloud VPC & VSwitch management.

Capabilities:
  - create_vpc / describe_vpcs
  - create_vswitch / describe_vswitches

All functions use RPC-style API (product=vpc, version=2016-04-28).
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from common import call_rpc_api, wait_until, pp

PRODUCT = "vpc"
VERSION = "2016-04-28"


def _call(action: str, params: dict | None = None, region: str | None = None) -> dict:
    return call_rpc_api(PRODUCT, VERSION, action, params=params, region=region)


# ---------------------------------------------------------------------------
# VPC
# ---------------------------------------------------------------------------

def create_vpc(
    cidr_block: str = "192.168.0.0/16",
    vpc_name: str = "acf-vpc",
    region: str | None = None,
    description: str = "",
) -> dict:
    """Create a VPC and wait until Available.

    Returns the full VPC description dict.
    """
    params: dict = {
        "CidrBlock": cidr_block,
        "VpcName": vpc_name,
    }
    if description:
        params["Description"] = description

    result = _call("CreateVpc", params, region)
    vpc_id = result.get("VpcId", "")
    print(f"VPC created: {vpc_id}")

    def _check():
        vpcs = describe_vpcs(vpc_id=vpc_id, region=region)
        items = vpcs.get("Vpcs", {}).get("Vpc", [])
        return items[0] if items else {"Status": "Pending"}

    info = wait_until(_check, {"Available"}, {"Error"}, interval=5, timeout=120)
    print(f"VPC {vpc_id} is Available")
    return info


def describe_vpcs(
    vpc_id: str | None = None,
    vpc_name: str | None = None,
    region: str | None = None,
    page_size: int = 50,
) -> dict:
    """List VPCs with optional filters."""
    params: dict = {"PageSize": page_size}
    if vpc_id:
        params["VpcId"] = vpc_id
    if vpc_name:
        params["VpcName"] = vpc_name
    return _call("DescribeVpcs", params, region)


# ---------------------------------------------------------------------------
# VSwitch
# ---------------------------------------------------------------------------

def create_vswitch(
    vpc_id: str,
    zone_id: str,
    cidr_block: str = "192.168.0.0/24",
    vswitch_name: str = "acf-vsw",
    region: str | None = None,
    description: str = "",
) -> dict:
    """Create a VSwitch and wait until Available.

    Returns the full VSwitch description dict.
    """
    params: dict = {
        "VpcId": vpc_id,
        "ZoneId": zone_id,
        "CidrBlock": cidr_block,
        "VSwitchName": vswitch_name,
    }
    if description:
        params["Description"] = description

    result = _call("CreateVSwitch", params, region)
    vsw_id = result.get("VSwitchId", "")
    print(f"VSwitch created: {vsw_id}")

    def _check():
        vsws = describe_vswitches(vswitch_id=vsw_id, region=region)
        items = vsws.get("VSwitches", {}).get("VSwitch", [])
        return items[0] if items else {"Status": "Pending"}

    info = wait_until(_check, {"Available"}, {"Error"}, interval=3, timeout=60)
    print(f"VSwitch {vsw_id} is Available")
    return info


def describe_vswitches(
    vpc_id: str | None = None,
    vswitch_id: str | None = None,
    zone_id: str | None = None,
    region: str | None = None,
    page_size: int = 50,
) -> dict:
    """List VSwitches with optional filters."""
    params: dict = {"PageSize": page_size}
    if vpc_id:
        params["VpcId"] = vpc_id
    if vswitch_id:
        params["VSwitchId"] = vswitch_id
    if zone_id:
        params["ZoneId"] = zone_id
    return _call("DescribeVSwitches", params, region)


def delete_vswitch(
    vswitch_id: str,
    region: str | None = None,
) -> dict:
    """Delete a VSwitch. It must have no associated resources."""
    result = _call("DeleteVSwitch", {"VSwitchId": vswitch_id}, region)
    print(f"VSwitch deleted: {vswitch_id}")
    return result


def delete_vpc(
    vpc_id: str,
    region: str | None = None,
) -> dict:
    """Delete a VPC. All VSwitches in it must be deleted first."""
    result = _call("DeleteVpc", {"VpcId": vpc_id}, region)
    print(f"VPC deleted: {vpc_id}")
    return result


# ---------------------------------------------------------------------------
# Convenience: ensure VPC + VSwitch exist
# ---------------------------------------------------------------------------

def _find_available_vsw_cidr(vpc_id: str, vpc_cidr_prefix: str = "192.168", region: str | None = None) -> str:
    """Find an available /24 CIDR within the VPC by checking existing VSwitches.

    Scans 192.168.0.0/24 through 192.168.255.0/24 and returns the first
    subnet not used by any existing VSwitch.
    """
    vsws = describe_vswitches(vpc_id=vpc_id, region=region)
    vsw_items = vsws.get("VSwitches", {}).get("VSwitch", [])
    used_cidrs = {v.get("CidrBlock", "") for v in vsw_items}

    for third_octet in range(256):
        candidate = f"{vpc_cidr_prefix}.{third_octet}.0/24"
        if candidate not in used_cidrs:
            return candidate

    raise RuntimeError(f"No available /24 CIDR in {vpc_cidr_prefix}.0.0/16, all 256 subnets occupied")


def ensure_vpc_and_vswitch(
    zone_id: str,
    vpc_cidr: str = "192.168.0.0/16",
    vsw_cidr: str | None = None,
    vpc_name: str = "acf-vpc",
    vsw_name: str = "acf-vsw",
    region: str | None = None,
) -> tuple[str, str, bool, bool]:
    """Create or reuse a VPC and VSwitch.

    Returns (vpc_id, vswitch_id, vpc_is_new, vswitch_is_new).
    The boolean flags indicate whether the resource was freshly created
    (True) or reused from an existing one (False).

    If vsw_cidr is None (default), auto-detects an available /24 subnet
    within the VPC to avoid CIDR conflicts with existing VSwitches.
    """
    vpc_is_new = False
    vsw_is_new = False

    vpcs = describe_vpcs(vpc_name=vpc_name, region=region)
    items = vpcs.get("Vpcs", {}).get("Vpc", [])
    available = [v for v in items if v.get("Status") == "Available"]

    if available:
        vpc_id = available[0]["VpcId"]
        print(f"Reusing existing VPC: {vpc_id}")
    else:
        vpc_info = create_vpc(cidr_block=vpc_cidr, vpc_name=vpc_name, region=region)
        vpc_id = vpc_info["VpcId"]
        vpc_is_new = True

    vsws = describe_vswitches(vpc_id=vpc_id, zone_id=zone_id, region=region)
    vsw_items = vsws.get("VSwitches", {}).get("VSwitch", [])
    vsw_available = [v for v in vsw_items if v.get("Status") == "Available"]

    if vsw_available:
        vsw_id = vsw_available[0]["VSwitchId"]
        print(f"Reusing existing VSwitch: {vsw_id}")
    else:
        if vsw_cidr is None:
            vpc_prefix = vpc_cidr.rsplit(".", 2)[0]  # "192.168.0.0/16" → "192.168"
            vsw_cidr = _find_available_vsw_cidr(vpc_id, vpc_prefix, region)
            print(f"Auto-detected available CIDR: {vsw_cidr}")

        vsw_info = create_vswitch(
            vpc_id=vpc_id, zone_id=zone_id,
            cidr_block=vsw_cidr, vswitch_name=vsw_name, region=region,
        )
        vsw_id = vsw_info["VSwitchId"]
        vsw_is_new = True

    return vpc_id, vsw_id, vpc_is_new, vsw_is_new
