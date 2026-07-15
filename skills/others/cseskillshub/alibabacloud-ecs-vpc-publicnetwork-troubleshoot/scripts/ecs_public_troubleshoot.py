#!/usr/bin/env python3
"""
ECS Public Network Connectivity Automated Detection Script (Scenario 1)
Covers Branch A (Direct Public IP) and Branch B (NAT Gateway)

SECURITY: This script issues READ-ONLY Alibaba Cloud API queries only
(Describe*/Get* actions). It never creates, modifies, deletes, or restarts any
resource. It MUST only be invoked after the user has confirmed the diagnostic
scope per SKILL.md's "User Confirmation" policy, and only against the single
resource the user specified.

Usage:
  python3 ecs_public_troubleshoot.py \
    --region-id cn-beijing \
    --instance-id i-xxx

Output: Structured JSON containing all detection item results for rendering the information table
"""

import argparse
import json
import os
import subprocess
import concurrent.futures
import ipaddress
import sys
import uuid

try:
    from aliyunsdkcore.client import AcsClient
    from aliyunsdkcore.request import CommonRequest
    from aliyunsdkcore.auth.credentials import StsTokenCredential
except ImportError:
    print("[ERROR] Missing aliyunsdkcore, please run: pip install -r scripts/requirements.txt", file=sys.stderr)
    sys.exit(1)

# Silence benign "Exception ignored in AcsClient.__del__" noise the SDK emits
# when a client fails to initialize (partial object lacks a 'session' attribute).
_orig_acs_del = getattr(AcsClient, "__del__", None)
if _orig_acs_del is not None:
    def _quiet_acs_del(self, _orig=_orig_acs_del):
        try:
            _orig(self)
        except Exception:
            pass
    AcsClient.__del__ = _quiet_acs_del

# ============================================================
# Observability: Skill UA + session-id
# ============================================================
SKILL_NAME = "alibabacloud-ecs-vpc-publicnetwork-troubleshoot"
SKILL_VERSION = "0.1.0"
# API timeout defaults (seconds)
DEFAULT_CONNECT_TIMEOUT = 10
DEFAULT_READ_TIMEOUT = 30


def _get_or_create_session_id():
    """Get or create Skill session ID (shared within one troubleshooting session)"""
    sid = os.environ.get("SKILL_SESSION_ID")
    if not sid:
        sid = uuid.uuid4().hex
        os.environ["SKILL_SESSION_ID"] = sid
    return sid


SESSION_ID = _get_or_create_session_id()
print(f"[SESSION] session-id={SESSION_ID}", file=sys.stderr)


def _setup_ua(client):
    """Inject User-Agent with session-id into AcsClient for observability tracing"""
    try:
        client.append_user_agent(
            "AlibabaCloud-Agent-Skills",
            f"{SKILL_NAME}/{SESSION_ID}",
        )
    except Exception:
        # Ignore if older SDK does not support append_user_agent; UA will still be passed to subprocesses via env var
        pass
    # Also pass unified UA to subprocesses (aliyun CLI) via environment variable
    os.environ["ALIBABACLOUD_USER_AGENT"] = (
        f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{SESSION_ID}"
    )
    return client


def call_api(client, product, version, action, params=None, region_id=None,
             connect_timeout=DEFAULT_CONNECT_TIMEOUT, read_timeout=DEFAULT_READ_TIMEOUT):
    """Generic Alibaba Cloud OpenAPI call wrapper (CommonRequest, with built-in timeout protection)"""
    req = CommonRequest()
    req.set_accept_format("json")
    req.set_domain(f"{product}.aliyuncs.com")
    req.set_method("POST")
    req.set_protocol_type("https")
    req.set_version(version)
    req.set_action_name(action)
    # Enforce timeout to prevent hanging
    try:
        req.set_connect_timeout(connect_timeout)
        req.set_read_timeout(read_timeout)
    except AttributeError:
        pass
    if region_id:
        req.add_query_param("RegionId", region_id)
    if params:
        for k, v in params.items():
            req.add_query_param(k, v)
    resp = client.do_action_with_exception(req)
    return json.loads(resp)


def call_cli(product, action, region_id, extra_params=None):
    """Call API via aliyun CLI (for DDoS/CFW interfaces where SDK version is uncertain)"""
    cmd = [
        "aliyun", product, action,
        "--region", region_id,
    ]
    if extra_params:
        for k, v in extra_params.items():
            cmd.extend([f"--{k}", str(v)])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {"_error": result.stderr.strip()}
    except Exception as e:
        return {"_error": str(e)}


def query_ecs_info(client, region_id, instance_id):
    """Step 3: Query ECS basic info and determine Branch A/B"""
    data = call_api(client, "ecs", "2014-05-26", "DescribeInstances", {
        "InstanceIds": json.dumps([instance_id]),
        "RegionId": region_id,
    }, region_id)
    instances = data.get("Instances", {}).get("Instance", [])
    if not instances:
        raise ValueError(f"Instance {instance_id} not found")
    inst = instances[0]
    public_ips = inst.get("PublicIpAddress", {}).get("IpAddress", [])
    eip = inst.get("EipAddress", {}) or {}
    eip_ip = eip.get("IpAddress") if eip else None
    has_public = bool(public_ips or eip_ip)
    return {
        "instance_id": inst["InstanceId"],
        "instance_name": inst.get("InstanceName", ""),
        "private_ip": inst.get("VpcAttributes", {}).get("PrivateIpAddress", {}).get("IpAddress", [None])[0],
        "public_ip": public_ips[0] if public_ips else None,
        "eip_ip": eip_ip,
        "internet_charge_type": inst.get("InternetChargeType", ""),
        "security_groups": inst.get("SecurityGroupIds", {}).get("SecurityGroupId", []),
        "vswitch_id": inst.get("VpcAttributes", {}).get("VSwitchId"),
        "vpc_id": inst.get("VpcAttributes", {}).get("VpcId"),
        "zone_id": inst.get("ZoneId", ""),
        "has_public_ip": has_public,
        "branch": "A" if has_public else "B",
    }


def query_account(client, region_id):
    """Step 4: Check account UID and overdue status"""
    try:
        uid_data = call_api(client, "sts", "2015-04-01", "GetCallerIdentity", region_id=region_id)
        # Use CLI to call bssopenapi to avoid SDK DNS resolution issues
        balance_data = call_cli("bssopenapi", "query-account-balance", region_id)
        if "_error" in balance_data:
            raise RuntimeError(balance_data["_error"])
        available = float(balance_data.get("Data", {}).get("AvailableAmount", 0))
        return {
            "uid": uid_data.get("AccountId", ""),
            "available_amount": available,
            "is_owed": available < 0,
            "status": "abnormal" if available < 0 else "normal",
            "error": None,
        }
    except Exception as e:
        return {"uid": "", "available_amount": 0, "is_owed": False, "status": "normal", "error": str(e)}


def query_security_group(client, region_id, sg_ids):
    """Step 5: Check ECS security group rules (return raw data, status determined by caller based on branch)"""
    try:
        has_icmp = False
        has_egress_drop = False
        for sg_id in sg_ids:
            data = call_api(client, "ecs", "2014-05-26", "DescribeSecurityGroupAttribute", {
                "SecurityGroupId": sg_id,
                "RegionId": region_id,
            }, region_id)
            for perm in data.get("Permissions", {}).get("Permission", []):
                if perm.get("Direction") == "ingress":
                    proto = perm.get("IpProtocol", "").upper()
                    src = perm.get("SourceCidrIp", "")
                    policy = perm.get("Policy", "")
                    if policy == "Accept" and src == "0.0.0.0/0" and (proto == "ICMP" or proto == "ALL"):
                        has_icmp = True
                elif perm.get("Direction") == "egress":
                    if perm.get("Policy") == "Drop":
                        has_egress_drop = True
        return {
            "sg_ids": sg_ids,
            "has_icmp_0_0_0_0": has_icmp,
            "has_egress_drop": has_egress_drop,
            "status": "normal",  # Placeholder, recalculated by main() based on branch
            "error": None,
        }
    except Exception as e:
        return {"sg_ids": sg_ids, "has_icmp_0_0_0_0": False, "has_egress_drop": False, "status": "abnormal", "error": str(e)}


def query_vswitch(client, region_id, vswitch_id):
    """Step 6: Check VSwitch network ACL"""
    try:
        data = call_api(client, "vpc", "2016-04-28", "DescribeVSwitchAttributes", {
            "VSwitchId": vswitch_id,
            "RegionId": region_id,
        }, region_id)
        acl_id = data.get("NetworkAclId", "")
        cidr = data.get("CidrBlock", "")
        route_table_id = data.get("RouteTable", {}).get("RouteTableId", "")
        return {
            "vswitch_id": vswitch_id,
            "cidr_block": cidr,
            "network_acl_id": acl_id,
            "has_acl": bool(acl_id),
            "route_table_id": route_table_id,
            "status": "abnormal" if acl_id else "normal",
            "error": None,
        }
    except Exception as e:
        return {"vswitch_id": vswitch_id, "cidr_block": "", "network_acl_id": "", "has_acl": False, "route_table_id": "", "status": "normal", "error": str(e)}


def query_vpc(client, region_id, vpc_id):
    """Step 7: Check VPC IPv4 gateway and route configuration"""
    try:
        data = call_api(client, "vpc", "2016-04-28", "DescribeVpcAttribute", {
            "VpcId": vpc_id,
            "RegionId": region_id,
        }, region_id)
        support_ipv4 = data.get("SupportIpv4Gateway", False)
        ipv4_gateway_id = data.get("Ipv4GatewayId", "")
        return {
            "vpc_id": vpc_id,
            "support_ipv4_gateway": support_ipv4,
            "ipv4_gateway_id": ipv4_gateway_id,
            "status": "abnormal" if support_ipv4 else "normal",
            "error": None,
        }
    except Exception as e:
        return {"vpc_id": vpc_id, "support_ipv4_gateway": False, "ipv4_gateway_id": "", "status": "normal", "error": str(e)}


def query_route_table(client, region_id, route_table_id):
    """Check route table 0.0.0.0/0 route"""
    try:
        data = call_api(client, "vpc", "2016-04-28", "DescribeRouteEntryList", {
            "RouteTableId": route_table_id,
            "RegionId": region_id,
        }, region_id)
        entries = data.get("RouteEntrys", {}).get("RouteEntry", [])
        for entry in entries:
            if entry.get("DestinationCidrBlock") == "0.0.0.0/0":
                next_hop_type = entry.get("NextHops", {}).get("NextHop", [{}])[0].get("NextHopType", "")
                next_hop_id = entry.get("NextHops", {}).get("NextHop", [{}])[0].get("NextHopId", "")
                return {
                    "has_0_0_0_0": True,
                    "next_hop_type": next_hop_type,
                    "next_hop_id": next_hop_id,
                    "status": "normal" if next_hop_type in ("Ipv4Gateway", "NatGateway") else "abnormal",
                    "error": None,
                }
        return {"has_0_0_0_0": False, "next_hop_type": "", "next_hop_id": "", "status": "abnormal", "error": None}
    except Exception as e:
        return {"has_0_0_0_0": False, "next_hop_type": "", "next_hop_id": "", "status": "abnormal", "error": str(e)}


def query_ddos(region_id, ip, instance_type="ecs"):
    """Check DDoS blackhole status (CLI call)"""
    data = call_cli("antiddos-public", "describe-instance-ip-address", region_id, {
        "ddos-region-id": region_id,
        "instance-type": instance_type,
        "instance-ip": ip,
    })
    if "_error" in data:
        return {"ip_status": "unknown", "status": "normal", "error": data["_error"]}
    inst_list = data.get("InstanceList", [])
    if inst_list:
        ip_configs = inst_list[0].get("IpAddressConfig", [])
        if ip_configs:
            ip_status = ip_configs[0].get("IpStatus", "")
            return {"ip_status": ip_status, "status": "normal" if ip_status == "normal" else "abnormal", "error": None}
    return {"ip_status": "unknown", "status": "normal", "error": "DDoS status not found"}


def query_cfw(region_id, ip):
    """Check Cloud Firewall (CFW) traffic diversion (CLI call)"""
    data = call_cli("cloudfw", "describe-asset-list", region_id, {
        "current-page": "1",
        "page-size": "1",
        "search-item": ip,
    })
    if "_error" in data:
        return {"has_cfw": False, "status": "normal", "error": data["_error"]}
    # Handle both list (empty result) and dict (non-empty result) return formats for Assets
    assets_data = data.get("Assets", {})
    if isinstance(assets_data, list):
        has_cfw = len(assets_data) > 0
    else:
        assets = assets_data.get("Asset", [])
        has_cfw = len(assets) > 0
    return {"has_cfw": has_cfw, "status": "abnormal" if has_cfw else "normal", "error": None}


# ==================== Branch B Functions ====================

def query_nat_gateways(client, region_id, vpc_id):
    """Step 9B: Check if NAT gateway exists"""
    try:
        data = call_api(client, "vpc", "2016-04-28", "DescribeNatGateways", {
            "VpcId": vpc_id,
            "RegionId": region_id,
        }, region_id)
        nats = data.get("NatGateways", {}).get("NatGateway", [])
        if not nats:
            return {"has_nat": False, "nat_gateway_id": "", "snat_table_id": "", "network_type": "", "status": "abnormal", "error": None}
        nat = nats[0]
        net_type = nat.get("NetworkType", "")
        snat_table_ids = nat.get("SnatTableIds", {}).get("SnatTableId", [])
        snat_table_id = snat_table_ids[0] if snat_table_ids else ""
        if net_type != "internet":
            return {"has_nat": False, "nat_gateway_id": nat.get("NatGatewayId", ""), "snat_table_id": "", "network_type": net_type, "status": "abnormal", "error": None}
        return {
            "has_nat": True,
            "nat_gateway_id": nat.get("NatGatewayId", ""),
            "snat_table_id": snat_table_id,
            "network_type": net_type,
            "status": "normal",
            "error": None,
        }
    except Exception as e:
        return {"has_nat": False, "nat_gateway_id": "", "snat_table_id": "", "network_type": "", "status": "abnormal", "error": str(e)}


def query_snat_entries(client, region_id, snat_table_id, vswitch_cidr):
    """Step 10B: Check NAT gateway SNAT entries"""
    try:
        data = call_api(client, "vpc", "2016-04-28", "DescribeSnatTableEntries", {
            "SnatTableId": snat_table_id,
            "RegionId": region_id,
        }, region_id)
        entries = data.get("SnatTableEntries", {}).get("SnatTableEntry", [])
        if not entries:
            return {"has_snat": False, "matched_snat": None, "status": "abnormal", "error": None}
        matched = None
        for entry in entries:
            source_cidr = entry.get("SourceCIDR", "")
            if _cidr_contains(source_cidr, vswitch_cidr):
                matched = entry
                break
        if matched:
            return {
                "has_snat": True,
                "matched_snat": {
                    "source_cidr": matched.get("SourceCIDR", ""),
                    "snat_ip": matched.get("SnatIp", ""),
                },
                "status": "normal",
                "error": None,
            }
        return {"has_snat": False, "matched_snat": None, "status": "abnormal", "error": None}
    except Exception as e:
        return {"has_snat": False, "matched_snat": None, "status": "abnormal", "error": str(e)}


def _cidr_contains(parent, child):
    """Check if parent CIDR contains child CIDR (supports exact match and containment)"""
    try:
        if parent == child:
            return True
        parent_net = ipaddress.ip_network(parent, strict=False)
        child_net = ipaddress.ip_network(child, strict=False)
        return parent_net.supernet_of(child_net)
    except Exception:
        return False


# ==================== Main Flow ====================

def run_branch_a(client, region_id, ecs_info):
    """Branch A: Direct public IP mode subsequent steps (8A-9A)"""
    target_ip = ecs_info["public_ip"] or ecs_info["eip_ip"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        f_ddos = ex.submit(query_ddos, region_id, target_ip, "ecs")
        f_cfw = ex.submit(query_cfw, region_id, target_ip)
        ddos = f_ddos.result()
        cfw = f_cfw.result()
    return {"ddos": ddos, "cfw": cfw}


def run_branch_b(client, region_id, ecs_info, vswitch_info):
    """Branch B: NAT gateway mode subsequent steps (8B-12B)"""
    # Round 1: Parallel check route table + NAT gateway
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        f_route = ex.submit(query_route_table, client, region_id, vswitch_info["route_table_id"])
        f_nat = ex.submit(query_nat_gateways, client, region_id, ecs_info["vpc_id"])
        route_info = f_route.result()
        nat_info = f_nat.result()

    # Round 2: SNAT check (depends on NAT gateway result)
    snat_info = {"has_snat": False, "matched_snat": None, "status": "abnormal", "error": None}
    if nat_info["has_nat"] and nat_info["snat_table_id"]:
        snat_info = query_snat_entries(client, region_id, nat_info["snat_table_id"], vswitch_info["cidr_block"])

    # Round 3: DDoS + CFW (depends on SNAT IP)
    ddos = {"ip_status": "unknown", "status": "normal", "error": "No SNAT IP"}
    cfw = {"has_cfw": False, "status": "normal", "error": "No SNAT IP"}
    snat_ip = (snat_info.get("matched_snat") or {}).get("snat_ip", "")
    if snat_ip:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            f_ddos = ex.submit(query_ddos, region_id, snat_ip, "eip")
            f_cfw = ex.submit(query_cfw, region_id, snat_ip)
            ddos = f_ddos.result()
            cfw = f_cfw.result()

    return {
        "route_table": route_info,
        "nat_gateway": nat_info,
        "snat": snat_info,
        "ddos": ddos,
        "cfw": cfw,
    }


def _load_cached_creds():
    """Read credentials from sts_create.py local cache (.sts_cache.json).

    Returns the credential dict for last_active_uid, or None if unavailable.
    This lets business scripts consume credentials without requiring the
    caller to export plaintext AK/SK/token on the command line.
    """
    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".sts_cache.json")
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    creds = raw.get("credentials", {}) or {}
    uid = raw.get("last_active_uid")
    entry = creds.get(str(uid)) if uid else None
    if not entry and creds:
        entry = next(iter(creds.values()), None)
    return entry or None


def _make_client(region_id):
    """Build AcsClient honoring the SDK default credential chain.

    Reads Alibaba Cloud credentials from environment variables when
    ALIBABA_CLOUD_ACCESS_KEY_ID is set (ALIBABA_CLOUD_SECURITY_TOKEN is
    optional and used for STS temporary credentials). Falls back to a
    default-chain AcsClient otherwise, so that credentials files, CLI
    config, or instance metadata can still be picked up.
    """
    ak = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
    sk = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
    token = os.environ.get("ALIBABA_CLOUD_SECURITY_TOKEN")
    # Fall back to sts_create.py local cache when env vars are absent,
    # avoiding the need to export plaintext credentials on the command line.
    if not (ak and sk):
        cached = _load_cached_creds()
        if cached:
            ak = cached.get("access_key_id")
            sk = cached.get("access_key_secret")
            token = cached.get("security_token")
    if ak and sk:
        if token:
            # AcsClient has no set_security_token method; STS tokens must be
            # injected via a StsTokenCredential (aliyun-python-sdk-core).
            client = AcsClient(region_id=region_id,
                               credential=StsTokenCredential(ak, sk, token))
        else:
            client = AcsClient(ak, sk, region_id)
        return client
    return AcsClient(region_id=region_id)


def main():
    parser = argparse.ArgumentParser(description="ECS Public Network Connectivity Automated Detection")
    parser.add_argument("--region-id", required=True, help="Region ID, e.g. cn-beijing")
    parser.add_argument("--instance-id", required=True, help="ECS Instance ID")
    parser.add_argument("--uid", default=None, help="Optional: Provide UID directly, skip GetCallerIdentity query")
    parser.add_argument("--available-amount", type=float, default=None, help="Optional: Provide account balance directly, skip BSS query (requires --uid)")
    args = parser.parse_args()

    client = _make_client(args.region_id)
    _setup_ua(client)

    # Step 3: Query ECS basic info
    ecs_info = query_ecs_info(client, args.region_id, args.instance_id)

    # Step 4: Account info (if uid and balance provided in step 1, reuse directly and skip API call)
    if args.uid is not None and args.available_amount is not None:
        account_info = {
            "uid": str(args.uid),
            "available_amount": args.available_amount,
            "is_owed": args.available_amount < 0,
            "status": "abnormal" if args.available_amount < 0 else "normal",
            "error": None,
        }
    else:
        account_info = query_account(client, args.region_id)
        if args.uid:
            account_info["uid"] = str(args.uid)

    # Supplement: If instance has no public IP but has EIP bound, query EIP billing mode
    eip_charge_error = None
    if ecs_info["public_ip"] is None and ecs_info["eip_ip"]:
        eip_data = call_cli("vpc", "describe-eip-addresses", args.region_id, {
            "region-id": args.region_id,
            "eip-address": ecs_info["eip_ip"],
        })
        if "_error" not in eip_data:
            eip_list = eip_data.get("EipAddresses", {}).get("EipAddress", [])
            if eip_list:
                ecs_info["internet_charge_type"] = eip_list[0].get("InternetChargeType", "")
            else:
                eip_charge_error = f"EIP {ecs_info['eip_ip']} info not found"
        else:
            eip_charge_error = f"EIP billing mode query failed: {eip_data['_error']}"

    # Billing mode status: mark as abnormal when overdue and pay-by-traffic
    charge_type_status = "normal"
    if account_info["is_owed"] and ecs_info.get("internet_charge_type") == "PayByTraffic":
        charge_type_status = "abnormal"
    ecs_info["internet_charge_type_status"] = charge_type_status

    # Steps 5-7: Parallel execution (security group, VSwitch, VPC)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        f_sg = ex.submit(query_security_group, client, args.region_id, ecs_info["security_groups"])
        f_vsw = ex.submit(query_vswitch, client, args.region_id, ecs_info["vswitch_id"])
        f_vpc = ex.submit(query_vpc, client, args.region_id, ecs_info["vpc_id"])
        sg_info = f_sg.result()
        vswitch_info = f_vsw.result()
        vpc_info = f_vpc.result()

    # Branch determination and execute subsequent steps
    if ecs_info["branch"] == "A":
        branch_result = run_branch_a(
            client, args.region_id, ecs_info
        )
    else:
        branch_result = run_branch_b(
            client, args.region_id, ecs_info, vswitch_info
        )

    # Recalculate security group status based on branch: Branch A checks inbound ICMP allow, Branch B checks egress Drop rules
    if ecs_info["branch"] == "A":
        sg_info["status"] = "normal" if sg_info["has_icmp_0_0_0_0"] else "abnormal"
    else:
        sg_info["status"] = "normal" if not sg_info["has_egress_drop"] else "abnormal"

    # Step 7 route table check (Branch A IPv4 gateway route)
    route_info = None
    if vpc_info["support_ipv4_gateway"] and vswitch_info["route_table_id"]:
        route_info = query_route_table(client, args.region_id, vswitch_info["route_table_id"])

    # Branch A secondary determination: IPv4 gateway enabled and route table correctly points to IPv4 gateway, overall normal
    if ecs_info["branch"] == "A" and vpc_info["support_ipv4_gateway"] and route_info:
        if route_info.get("next_hop_type") == "Ipv4Gateway":
            vpc_info["status"] = "normal"

    result = {
        "scenario": "ecs_public",
        "branch": ecs_info["branch"],
        "ecs": ecs_info,
        "account": account_info,
        "security_group": sg_info,
        "vswitch": vswitch_info,
        "vpc": vpc_info,
        "route_table": route_info,
        "branch_result": branch_result,
        "errors": [],
    }

    # Collect errors
    if eip_charge_error:
        result["errors"].append(eip_charge_error)
    for section in [account_info, sg_info, vswitch_info, vpc_info]:
        if section.get("error"):
            result["errors"].append(section["error"])
    if route_info and route_info.get("error"):
        result["errors"].append(route_info["error"])

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
