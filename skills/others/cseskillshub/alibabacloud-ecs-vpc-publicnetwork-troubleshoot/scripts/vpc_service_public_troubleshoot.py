#!/usr/bin/env python3
"""
VPC Cloud Service Public Network Access Automated Detection Script (Scenario 2)

SECURITY: This script issues READ-ONLY Alibaba Cloud API queries only
(Describe*/Get* actions). It never creates, modifies, deletes, or restarts any
resource. It MUST only be invoked after the user has confirmed the diagnostic
scope per SKILL.md's "User Confirmation" policy, and only against the single
resource the user specified.

Usage:
  python3 vpc_service_public_troubleshoot.py \
    --region-id cn-beijing \
    --vswitch-id vsw-xxx

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
DEFAULT_CONNECT_TIMEOUT = 10
DEFAULT_READ_TIMEOUT = 30


def _get_or_create_session_id():
    sid = os.environ.get("SKILL_SESSION_ID")
    if not sid:
        sid = uuid.uuid4().hex
        os.environ["SKILL_SESSION_ID"] = sid
    return sid


SESSION_ID = _get_or_create_session_id()
print(f"[SESSION] session-id={SESSION_ID}", file=sys.stderr)


def _setup_ua(client):
    """Inject User-Agent with session-id into AcsClient"""
    try:
        client.append_user_agent(
            "AlibabaCloud-Agent-Skills",
            f"{SKILL_NAME}/{SESSION_ID}",
        )
    except Exception:
        pass
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


def _cidr_contains(parent, child):
    """Check if parent CIDR contains child CIDR"""
    try:
        if parent == child:
            return True
        parent_net = ipaddress.ip_network(parent, strict=False)
        child_net = ipaddress.ip_network(child, strict=False)
        return parent_net.supernet_of(child_net)
    except Exception:
        return False


# ==================== Scenario 2 Functions ====================

def query_vswitch(client, region_id, vswitch_id):
    """Step 1 & 3: Query VSwitch details (including ACL, CIDR, VPC)"""
    try:
        data = call_api(client, "vpc", "2016-04-28", "DescribeVSwitchAttributes", {
            "VSwitchId": vswitch_id,
            "RegionId": region_id,
        }, region_id)
        acl_id = data.get("NetworkAclId", "")
        cidr = data.get("CidrBlock", "")
        vpc_id = data.get("VpcId", "")
        route_table_id = data.get("RouteTable", {}).get("RouteTableId", "")
        zone_id = data.get("ZoneId", "")
        return {
            "vswitch_id": vswitch_id,
            "cidr_block": cidr,
            "vpc_id": vpc_id,
            "zone_id": zone_id,
            "network_acl_id": acl_id,
            "has_acl": bool(acl_id),
            "route_table_id": route_table_id,
            "status": "abnormal" if acl_id else "normal",
            "error": None,
        }
    except Exception as e:
        return {"vswitch_id": vswitch_id, "cidr_block": "", "vpc_id": "", "zone_id": "", "network_acl_id": "", "has_acl": False, "route_table_id": "", "status": "normal", "error": str(e)}


def query_account(client, region_id):
    """Step 2: Check account UID and overdue status"""
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


def query_ipv4_gateway(vpc_id, region_id):
    """Step 10: Query VPC IPv4 gateway mode via CLI"""
    data = call_cli("vpc", "describe-vpc-attribute", region_id, {
        "vpc-id": vpc_id,
    })
    if "_error" in data:
        return {"support_ipv4_gateway": False, "status": "normal", "error": data["_error"]}
    support = data.get("SupportIpv4Gateway", False)
    return {
        "support_ipv4_gateway": support,
        "status": "abnormal" if support else "normal",
        "error": None,
    }


def query_nat_gateways(client, region_id, vpc_id):
    """Step 4: Check if NAT gateway exists"""
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


def query_route_table(client, region_id, route_table_id):
    """Step 5: Check route table 0.0.0.0/0 route"""
    try:
        data = call_api(client, "vpc", "2016-04-28", "DescribeRouteEntryList", {
            "RouteTableId": route_table_id,
            "RegionId": region_id,
        }, region_id)
        entries = data.get("RouteEntrys", {}).get("RouteEntry", [])
        for entry in entries:
            if entry.get("DestinationCidrBlock") == "0.0.0.0/0":
                next_hops = entry.get("NextHops", {}).get("NextHop", [{}])
                next_hop_type = next_hops[0].get("NextHopType", "") if next_hops else ""
                next_hop_id = next_hops[0].get("NextHopId", "") if next_hops else ""
                return {
                    "has_0_0_0_0": True,
                    "next_hop_type": next_hop_type,
                    "next_hop_id": next_hop_id,
                    "status": "normal" if next_hop_type == "NatGateway" else "abnormal",
                    "error": None,
                }
        return {"has_0_0_0_0": False, "next_hop_type": "", "next_hop_id": "", "status": "abnormal", "error": None}
    except Exception as e:
        return {"has_0_0_0_0": False, "next_hop_type": "", "next_hop_id": "", "status": "abnormal", "error": str(e)}


def query_snat_entries(client, region_id, snat_table_id, vswitch_cidr):
    """Step 6: Check NAT gateway SNAT entries"""
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


def query_eip(client, region_id, eip_address=None, allocation_id=None):
    """Step 7: Check EIP address details"""
    try:
        params = {"RegionId": region_id}
        if eip_address:
            params["EipAddress"] = eip_address
        if allocation_id:
            params["AllocationId"] = allocation_id
        data = call_api(client, "vpc", "2016-04-28", "DescribeEipAddresses", params, region_id)
        eips = data.get("EipAddresses", {}).get("EipAddress", [])
        if not eips:
            return {"has_eip": False, "eip_info": None, "status": "abnormal", "error": "EIP associated with SNAT not found"}
        eip = eips[0]
        return {
            "has_eip": True,
            "eip_info": {
                "ip_address": eip.get("IpAddress", ""),
                "bandwidth": eip.get("Bandwidth", ""),
                "status": eip.get("Status", ""),
                "charge_type": eip.get("ChargeType", ""),
                "instance_id": eip.get("InstanceId", ""),
            },
            "status": "normal",
            "error": None,
        }
    except Exception as e:
        return {"has_eip": False, "eip_info": None, "status": "normal", "error": str(e)}


def query_ddos(region_id, ip, instance_type="eip"):
    """Step 8: Check DDoS blackhole status (CLI call)"""
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
    """Step 9: Check Cloud Firewall (CFW) traffic diversion (CLI call)"""
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
    default-chain AcsClient otherwise.
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


# ==================== Main Flow ====================

def main():
    parser = argparse.ArgumentParser(description="VPC Cloud Service Public Network Access Automated Detection")
    parser.add_argument("--region-id", required=True, help="Region ID, e.g. cn-beijing")
    parser.add_argument("--vswitch-id", required=True, help="VSwitch ID (vsw-xxx)")
    parser.add_argument("--uid", default=None, help="Optional: Provide UID directly")
    args = parser.parse_args()

    client = _make_client(args.region_id)
    _setup_ua(client)

    # Step 1 & 3: Query VSwitch info
    vswitch_info = query_vswitch(client, args.region_id, args.vswitch_id)
    if vswitch_info.get("error"):
        print(json.dumps({"scenario": "vpc_service", "error": f"VSwitch query failed: {vswitch_info['error']}"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    # Step 2 & 4 & 10: Parallel execution (account info + NAT gateway query + IPv4 gateway query)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        f_account = ex.submit(query_account, client, args.region_id)
        f_nat = ex.submit(query_nat_gateways, client, args.region_id, vswitch_info["vpc_id"])
        f_ipv4 = ex.submit(query_ipv4_gateway, vswitch_info["vpc_id"], args.region_id)
        account_info = f_account.result()
        nat_info = f_nat.result()
        ipv4_info = f_ipv4.result()

    if args.uid:
        account_info["uid"] = args.uid

    # Step 5: Query route table (depends on route_table_id from VSwitch info)
    route_info = {"has_0_0_0_0": False, "next_hop_type": "", "next_hop_id": "", "status": "normal", "error": None}
    if vswitch_info["route_table_id"]:
        route_info = query_route_table(client, args.region_id, vswitch_info["route_table_id"])

    # Step 6: Query SNAT entries (depends on NAT gateway result)
    snat_info = {"has_snat": False, "matched_snat": None, "status": "abnormal", "error": "No NAT gateway, cannot configure SNAT"}
    if nat_info["has_nat"] and nat_info["snat_table_id"]:
        snat_info = query_snat_entries(client, args.region_id, nat_info["snat_table_id"], vswitch_info["cidr_block"])

    # Step 7 & 8 & 9: EIP + DDoS + CFW (depends on SNAT IP)
    eip_info = {"has_eip": False, "eip_info": None, "status": "abnormal", "error": "No SNAT IP, cannot query EIP"}
    ddos_info = {"ip_status": "unknown", "status": "normal", "error": "No SNAT IP"}
    cfw_info = {"has_cfw": False, "status": "normal", "error": "No SNAT IP"}

    snat_ip = (snat_info.get("matched_snat") or {}).get("snat_ip", "")
    if snat_ip:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            f_eip = ex.submit(query_eip, client, args.region_id, eip_address=snat_ip)
            f_ddos = ex.submit(query_ddos, args.region_id, snat_ip, "eip")
            f_cfw = ex.submit(query_cfw, args.region_id, snat_ip)
            eip_info = f_eip.result()
            ddos_info = f_ddos.result()
            cfw_info = f_cfw.result()

    result = {
        "scenario": "vpc_service",
        "vswitch": vswitch_info,
        "account": account_info,
        "ipv4_gateway": ipv4_info,
        "nat_gateway": nat_info,
        "route_table": route_info,
        "snat": snat_info,
        "eip": eip_info,
        "ddos": ddos_info,
        "cfw": cfw_info,
        "errors": [],
    }

    for section in [vswitch_info, account_info, ipv4_info, nat_info, route_info, snat_info, eip_info, ddos_info, cfw_info]:
        if section.get("error"):
            result["errors"].append(section["error"])

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
