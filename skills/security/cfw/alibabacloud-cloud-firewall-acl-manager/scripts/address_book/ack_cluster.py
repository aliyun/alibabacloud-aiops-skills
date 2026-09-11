"""Sync node - ACK cluster address book plugin"""
from .base import AddressBookPlugin


class AckClusterPlugin(AddressBookPlugin):
    """Sync node - ACK cluster plugin"""
    
    name = "同步节点-ACK集群"
    sheet_name = "同步节点-ACK集群"
    order = 2
    group_types = []  # This plugin does not use GroupType
    
    # Use a different API
    api_action = "DescribeAckClusterConnectors"
    page_no_key = "PageNo"
    result_key = "AckClusterConnectors"
    
    columns = [
        ("同步节点实例ID",     lambda item: item.get("ConnectorId", "")),
        ("同步节点名称",       lambda item: item.get("ConnectorName", "")),
        ("ACK集群ID",          lambda item: item.get("ClusterId", "")),
        ("名称",               lambda item: item.get("ClusterName", "")),
        ("ACK集群所属账号",    lambda item: item.get("MemberUid", "")),
        ("专有网络",           lambda item: item.get("VpcId", "")),
        ("地域",               lambda item: item.get("RegionNo", "")),
        ("ACK地址簿",          lambda item: len(item.get("GroupUuids", []))),
        ("主交换机ID",         lambda item: item.get("PrimaryVswitchId", "")),
        ("主交换机IP",         lambda item: item.get("PrimaryVswitchIp", "")),
        ("主交换机可用区",     lambda item: item.get("PrimaryVswitchZoneId", "")),
        ("备用交换机ID",       lambda item: item.get("StandbyVswitchId", "")),
        ("备用交换机IP",       lambda item: item.get("StandbyVswitchIp", "")),
        ("备用交换机可用区",   lambda item: item.get("StandbyVswitchZoneId", "")),
        ("同步周期",           lambda item: item.get("Ttl", "")),
        ("连接器状态",         lambda item: item.get("ConnectorStatus", "")),
        ("健康检查状态",       lambda item: item.get("ConnectorHealthCheckStatus", "")),
        ("不健康原因",         lambda item: item.get("UnhealthyReason", "")),
    ]
    col_widths = [25, 20, 38, 30, 20, 25, 15, 12, 25, 18, 18, 25, 18, 18, 12, 15, 15, 30]
    
    def post_process(self, items: list) -> list:
        """ACK cluster connectors do not need to filter Global=1"""
        return items
    
    # ==================== Restore configuration ====================
    restore_api = "CreateAckClusterConnector"
    name_column = "同步节点名称"
    uid_column = "ConnectorId"
    
    @property
    def restore_column_mapping(self):
        return {
            "同步节点名称": "ConnectorName",
            "ACK集群ID": "ClusterId",
            "ACK集群所属账号": "MemberUid",
            "地域": "RegionNo",
            "主交换机ID": "PrimaryVswitchId",
            "主交换机IP": "PrimaryVswitchIp",
            "备用交换机ID": "StandbyVswitchId",
            "备用交换机IP": "StandbyVswitchIp",
            "同步周期": "Ttl",
        }
    
    @property
    def restore_value_transforms(self):
        return {}
