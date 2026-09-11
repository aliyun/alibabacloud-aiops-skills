"""Sync node - private DNS address book plugin"""
from .base import AddressBookPlugin


class PrivateDnsPlugin(AddressBookPlugin):
    """Sync node - private DNS plugin
    
    Three API calls:
    1. DescribePrivateDnsEndpointList - get the instance list
    2. DescribePrivateDnsDomainNameList - get the domain name list of each instance
    3. DescribePrivateDnsEndpointDetail - get the zones and vSwitch info of each instance
    """
    
    name = "同步节点-私有DNS"
    sheet_name = "同步节点-私有DNS"
    order = 3
    group_types = []  # GroupType is not used
    
    def custom_fetch(self, ak, sk, endpoint, call_api_fn, page_size=50, security_token=None):
        """Custom data fetching logic: three API calls"""
        all_instances = []
        current_page = 1
        
        # Step 1: get all DNS instances
        while True:
            params = {
                "CurrentPage": current_page,
                "PageSize": page_size,
                "Lang": "zh"
            }
            response = call_api_fn(ak, sk, endpoint, "DescribePrivateDnsEndpointList", params, security_token)
            
            if not response:
                break
            
            instances = response.get("AccessInstanceList", [])
            if not instances:
                break
            
            for instance in instances:
                instance_id = instance.get("AccessInstanceId")
                instance_region = instance.get("RegionNo")
                
                if instance_id and instance_region:
                    # Step 2: get the domain name list
                    domain_params = {
                        "AccessInstanceId": instance_id,
                        "RegionNo": instance_region,
                        "CurrentPage": 1,
                        "PageSize": 50,
                        "Lang": "zh"
                    }
                    domain_response = call_api_fn(
                        ak, sk, endpoint,
                        "DescribePrivateDnsDomainNameList",
                        domain_params, security_token
                    )
                    if domain_response:
                        instance["DomainNameList"] = domain_response.get("DomainNameList", [])
                    else:
                        instance["DomainNameList"] = []
                    
                    # Step 3: get instance details (zones and vSwitch info)
                    detail_params = {
                        "AccessInstanceId": instance_id,
                        "RegionNo": instance_region,
                        "Lang": "zh"
                    }
                    detail_response = call_api_fn(
                        ak, sk, endpoint,
                        "DescribePrivateDnsEndpointDetail",
                        detail_params, security_token
                    )
                    if detail_response:
                        # Extract detail fields and merge them into the instance data
                        instance["EndpointId"] = detail_response.get("EndpointId", "")
                        instance["PrimaryZoneId"] = detail_response.get("PrimaryZoneId", "")
                        instance["StandbyZoneId"] = detail_response.get("StandbyZoneId", "")
                        instance["PrimaryVSwitchId"] = detail_response.get("PrimaryVSwitchId", "")
                        instance["PrimaryVSwitchIp"] = detail_response.get("PrimaryVSwitchIp", "")
                        instance["StandbyVSwitchId"] = detail_response.get("StandbyVSwitchId", "")
                        instance["StandbyVSwitchIp"] = detail_response.get("StandbyVSwitchIp", "")
                    else:
                        instance["EndpointId"] = ""
                        instance["PrimaryZoneId"] = ""
                        instance["StandbyZoneId"] = ""
                        instance["PrimaryVSwitchId"] = ""
                        instance["PrimaryVSwitchIp"] = ""
                        instance["StandbyVSwitchId"] = ""
                        instance["StandbyVSwitchIp"] = ""
                else:
                    instance["DomainNameList"] = []
                    instance["EndpointId"] = ""
                    instance["PrimaryZoneId"] = ""
                    instance["StandbyZoneId"] = ""
                    instance["PrimaryVSwitchId"] = ""
                    instance["PrimaryVSwitchIp"] = ""
                    instance["StandbyVSwitchId"] = ""
                    instance["StandbyVSwitchIp"] = ""
            
            all_instances.extend(instances)
            
            # Check whether there is more data
            total_count = response.get("TotalCount", 0)
            if len(all_instances) >= total_count:
                break
            
            current_page += 1
        
        return all_instances
    
    # DNS type mapping
    DNS_TYPE_MAP = {"Custom": "自建DNS", "PrivateZone": "PrivateZone"}
    # Status mapping
    STATUS_MAP = {"normal": "正常"}

    columns = [
        ("同步节点实例ID",    lambda item: item.get("AccessInstanceId", "")),
        ("同步节点名称",      lambda item: item.get("AccessInstanceName", "")),
        ("VPC ID",            lambda item: item.get("VpcId", "")),
        ("地域",              lambda item: item.get("RegionNo", "")),
        ("私有DNS类型",       lambda item: PrivateDnsPlugin.DNS_TYPE_MAP.get(item.get("PrivateDnsType", ""), item.get("PrivateDnsType", ""))),
        ("DNS服务器-主",      lambda item: item.get("PrimaryDns", "")),
        ("DNS服务器-备",      lambda item: item.get("StandbyDns", "")),
        ("实例状态",          lambda item: PrivateDnsPlugin.STATUS_MAP.get(item.get("Status", ""), item.get("Status", ""))),
        ("应用的防火墙边界",  lambda item: ", ".join(item.get("FirewallType", []))),
        ("所属账号",          lambda item: item.get("MemberUid", "")),
        ("主可用区",          lambda item: item.get("PrimaryZoneId", "")),
        ("主交换机ID",        lambda item: item.get("PrimaryVSwitchId", "")),
        ("主交换机IP",        lambda item: item.get("PrimaryVSwitchIp", "")),
        ("备用可用区",        lambda item: item.get("StandbyZoneId", "")),
        ("备用交换机ID",      lambda item: item.get("StandbyVSwitchId", "")),
        ("备用交换机IP",      lambda item: item.get("StandbyVSwitchIp", "")),
        ("DNS解析协议",       lambda item: item.get("IpProtocol", "")),
        ("DNS解析端口",       lambda item: item.get("Port", "")),
        ("域名列表",          lambda item: "\n".join(item.get("DomainNameList", []))),
        ("域名数量",          lambda item: item.get("DomainNameCount", "")),
    ]
    
    col_widths = [28, 20, 25, 15, 15, 18, 18, 10, 20, 20, 18, 28, 18, 18, 28, 18, 12, 12, 30, 10]

    # ==================== Restore configuration ====================
    restore_api = "CreatePrivateDnsEndpoint"
    name_column = "同步节点名称"
    uid_column = "AccessInstanceId"

    @property
    def restore_column_mapping(self):
        return {
            "同步节点名称": "AccessInstanceName",
            "VPC ID": "VpcId",
            "地域": "RegionNo",
            "私有DNS类型": "PrivateDnsType",
            "DNS服务器-主": "PrimaryDns",
            "DNS服务器-备": "StandbyDns",
            # The owning account (MemberUid) is not sent during restore: the backup records the source account UID,
            # and cross-account restore would inevitably fail with -200154 mismatch; when omitted, the server
            # defaults to the current account, so same-account restore behavior is unchanged.
            "主可用区": "PrimaryZoneId",
            "主交换机ID": "PrimaryVSwitchId",
            "主交换机IP": "PrimaryVSwitchIp",
            "备用可用区": "StandbyZoneId",
            "备用交换机ID": "StandbyVSwitchId",
            "备用交换机IP": "StandbyVSwitchIp",
            "DNS解析协议": "IpProtocol",
            "DNS解析端口": "Port",
            "应用的防火墙边界": "FirewallType",
        }

    @property
    def restore_value_transforms(self):
        def transform_member_uid(value):
            if value and str(value).strip() and str(value).strip() != "(空)":
                return int(value)
            return None

        def transform_port(value):
            if value and str(value).strip() and str(value).strip() != "(空)":
                return int(value)
            return None

        def transform_firewall_type(value):
            if value and str(value).strip() and str(value).strip() != "(空)":
                return [item.strip() for item in str(value).split(",")]
            return None

        def transform_private_dns_type(value):
            type_map = {
                "自建DNS": "Custom",
                "PrivateZone": "PrivateZone"
            }
            return type_map.get(value, value)

        return {
            "MemberUid": transform_member_uid,
            "Port": transform_port,
            "FirewallType": transform_firewall_type,
            "PrivateDnsType": transform_private_dns_type,
        }

    @property
    def restore_skip_params_by_type(self):
        """The PrivateZone type is managed by Alibaba Cloud, so DNS server and vSwitch IP parameters are not needed"""
        return {
            "PrivateDnsType": {
                "PrivateZone": [
                    "PrimaryDns",
                    "StandbyDns",
                    "PrimaryVSwitchIp",
                    "StandbyVSwitchIp",
                    "IpProtocol",
                    "Port",
                ]
            }
        }

    def post_process(self, items):
        """Private DNS does not need to filter Global=1"""
        return items

    def post_restore_record(self, row, result, ak, sk, endpoint, call_api_fn, security_token=None):
        """Add the domain name list after the sync node is created successfully"""
        import pandas as pd

        access_instance_id = result.get("AccessInstanceId", "")
        region_no = str(row.get("地域", ""))
        domain_list_str = row.get("域名列表", "")

        if not access_instance_id or not region_no:
            return

        # Parse the domain name list (newline separated)
        if pd.isna(domain_list_str) or not str(domain_list_str).strip():
            return

        domains = [d.strip() for d in str(domain_list_str).split("\n") if d.strip()]
        domains.reverse()  # Reverse the domain order to keep it consistent with the table display order
        if not domains:
            return

        print(f"    adding {len(domains)} domains...")
        domain_params = {
            "AccessInstanceId": access_instance_id,
            "RegionNo": region_no,
        }
        for i, domain in enumerate(domains, 1):
            domain_params[f"DomainNameList.{i}"] = domain

        domain_result = call_api_fn(ak, sk, endpoint, "AddPrivateDnsDomainName", domain_params, security_token, method="POST")
        code = domain_result.get("Code", "")
        if code:
            print(f"      [FAIL] failed to add domains: {code} - {domain_result.get('Message', '')}")
        else:
            print(f"      [OK] all {len(domains)} domains added successfully")
