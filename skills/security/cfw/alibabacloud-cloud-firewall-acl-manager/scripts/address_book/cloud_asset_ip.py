"""Cloud asset IP address book plugin"""
import json
from .base import AddressBookPlugin


# Fixed cloud asset type values per GroupType
CLOUD_ASSET_TYPE_MAP = {
    "asset": "公网资产",
    "assetIpv6": "公网资产IPv6",
    "ackNamespace": "ACK集群命名空间",
    "ackLabel": "ACK集群容器组标签",
    "tag": "ECS公网标签",
    "tagPrivate": "ECS私网标签",
}

# IP type per GroupType
IP_TYPE_MAP = {
    "asset": "IPv4",
    "assetIpv6": "IPv6",
    "ackNamespace": "IPv4",
    "ackLabel": "IPv4",
    "tag": "IPv4",
    "tagPrivate": "IPv4",
}


def _get_account(item):
    """Asset account: asset/assetIpv6 take AssetMemberUids, return the all-accounts marker when empty; other types are empty"""
    gt = item.get("GroupType", "")
    if gt in ("asset", "assetIpv6"):
        uids = item.get("AssetMemberUids", [])
        if uids:
            return ", ".join(str(uid) for uid in uids)
        return "全部账号"
    return ""


def _get_ip_type(item):
    """IP type: returns a fixed value based on GroupType"""
    return IP_TYPE_MAP.get(item.get("GroupType", ""), "")


def _get_address_list(item):
    """IP addresses"""
    return "\n".join(item.get("AddressList", []))


def _get_cloud_asset_type(item):
    """Cloud asset type: returns a fixed value based on GroupType"""
    return CLOUD_ASSET_TYPE_MAP.get(item.get("GroupType", ""), "")


def _get_asset_property(item):
    """Asset property: takes different fields based on GroupType"""
    gt = item.get("GroupType", "")
    if gt in ("asset", "assetIpv6"):
        # AssetRegionResourceTypes - extract enabled resource types from ResourceType
        regions = item.get("AssetRegionResourceTypes", [])
        if not regions:
            return ""
        all_enabled = set()
        for region_item in regions:
            resource_types = region_item.get("ResourceType", {})
            ipv4 = resource_types.get("Ipv4", {})
            ipv6 = resource_types.get("Ipv6", {})
            for k, v in ipv4.items():
                if v:
                    all_enabled.add(k)
            for k, v in ipv6.items():
                if v:
                    all_enabled.add(k)
        return ", ".join(sorted(all_enabled)) if all_enabled else ""
    elif gt == "ackNamespace":
        # AckNamespaces
        namespaces = item.get("AckNamespaces", [])
        return ", ".join(namespaces) if namespaces else ""
    elif gt == "ackLabel":
        # AckLabels
        labels = item.get("AckLabels", [])
        if not labels:
            return ""
        parts = [f"{l.get('Key', '')}={l.get('Value', '')}" for l in labels]
        return ", ".join(parts)
    elif gt in ("tag", "tagPrivate"):
        # TagList
        tag_list = item.get("TagList", [])
        if not tag_list:
            return ""
        parts = [f"{t.get('TagKey', '')}={t.get('TagValue', '')}" for t in tag_list]
        return ", ".join(parts)
    return ""


def _get_addresses(item):
    """Address book details"""
    addresses = item.get("Addresses", [])
    if not addresses:
        return ""
    parts = []
    for a in addresses:
        note = a.get("Note", "")
        val = a.get("Address", "")
        parts.append(f"{val} ({note})" if note else val)
    return "\n".join(parts)


def _get_ack_connector(item):
    """ACK sync node name"""
    gt = item.get("GroupType", "")
    if gt in ("ackNamespace", "ackLabel"):
        return item.get("AckClusterConnectorName", "")
    return ""


def _get_ack_connector_id(item):
    """ACK sync node ID"""
    gt = item.get("GroupType", "")
    if gt in ("ackNamespace", "ackLabel"):
        return item.get("AckClusterConnectorId", "")
    return ""


def _get_tag_relation(item):
    """Multi-tag relation"""
    gt = item.get("GroupType", "")
    if gt in ("tag", "tagPrivate"):
        return item.get("TagRelation", "")
    return ""


class CloudAssetIPPlugin(AddressBookPlugin):
    name = "云资产IP"
    order = 5
    group_types = ["asset", "assetIpv6", "ackNamespace", "ackLabel", "tag", "tagPrivate"]
    sheet_name = "云资产IP地址簿"
    columns = [
        ("地址簿名称",     lambda item: item.get("GroupName", "")),
        ("资产账号",       _get_account),
        ("IP类型",         _get_ip_type),
        ("云资产类型",     _get_cloud_asset_type),
        ("资产属性",       _get_asset_property),
        ("描述",           lambda item: item.get("Description", "")),
        ("引用次数",       lambda item: item.get("ReferenceCount", 0)),
        ("地址数量",       lambda item: item.get("AddressListCount", 0)),
        ("ACK同步节点",    _get_ack_connector),
        ("ACK同步节点ID",  _get_ack_connector_id),
        ("多标签关系",     _get_tag_relation),
    ]
    col_widths = [25, 20, 10, 20, 40, 25, 12, 12, 25, 30, 12]

    # ==================== Restore configuration ====================
    restore_api = "AddAddressBook"
    name_column = "地址簿名称"
    uid_column = "GroupUuid"

    # Reverse mapping from cloud asset type to GroupType
    ASSET_TYPE_REVERSE_MAP = {
        "公网资产": "asset",
        "公网资产IPv6": "assetIpv6",
        "ECS公网标签": "tag",
        "ECS私网标签": "tagPrivate",
        "ACK集群容器组标签": "ackLabel",
        "ACK集群命名空间": "ackNamespace",
    }

    def restore(self, ak, sk, region, call_api_fn, excel_file, security_token=None):
        """Cloud asset IP address book restore (overrides base class to handle complex nested parameters)"""
        import pandas as pd

        endpoint = f"cloudfw.{region}.aliyuncs.com"

        # Skip if the sheet does not exist (categories with no data at backup time have no sheet)
        if self.sheet_name not in pd.ExcelFile(excel_file).sheet_names:
            print(f"  [{self.name}] no sheet '{self.sheet_name}' in the backup file, skipping (no data at backup time)")
            return (0, 0, 0, 0)

        df = pd.read_excel(excel_file, sheet_name=self.sheet_name)
        print(f"  [{self.name}] loaded {len(df)} records")

        if '恢复状态' not in df.columns:
            df['恢复状态'] = '待恢复'
        else:
            df['恢复状态'] = df['恢复状态'].astype(str).replace('nan', '待恢复')

        success_count = 0
        fail_count = 0
        skip_count = 0
        exist_count = 0

        indices = list(range(len(df) - 1, -1, -1))

        for idx in indices:
            row = df.iloc[idx]
            record_name = str(row.get("地址簿名称", f"record{idx+1}"))
            asset_type = str(row.get("云资产类型", ""))

            # Only restore public-network assets and public-network IPv6 assets
            if asset_type not in self.ASSET_TYPE_REVERSE_MAP:
                skip_count += 1
                continue

            # Skip if already restored successfully
            current_status = df.at[df.index[idx], '恢复状态']
            if current_status == '成功':
                skip_count += 1
                continue

            # Build API parameters
            group_type = self.ASSET_TYPE_REVERSE_MAP[asset_type]
            ip_type = str(row.get("IP类型", ""))
            description = str(row.get("描述", ""))
            account_str = str(row.get("资产账号", ""))
            asset_property_str = str(row.get("资产属性", ""))

            api_params = {
                "GroupName": record_name,
                "GroupType": group_type,
                "Description": description if description != "nan" else "",
            }

            if group_type in ("asset", "assetIpv6"):
                # ===== Public-network asset / public-network IPv6 asset =====
                # AssetMemberUids: multiple accounts use a JSON list; the all-accounts marker passes an empty list
                if account_str and account_str != "nan" and account_str != "全部账号":
                    uids = [int(uid.strip()) for uid in account_str.split(",") if uid.strip()]
                    api_params["AssetMemberUids"] = json.dumps(uids)
                else:
                    api_params["AssetMemberUids"] = json.dumps([])

                # AssetRegionResourceTypes: JSON string
                resource_type = {}
                if asset_property_str and asset_property_str != "nan":
                    resource_names = [r.strip() for r in asset_property_str.split(",") if r.strip()]
                    ip_key = "Ipv4" if ip_type == "IPv4" else "Ipv6"
                    resource_type[ip_key] = {name: True for name in resource_names}

                asset_region = [{"AssetRegionId": "all", "ResourceType": resource_type}]
                api_params["AssetRegionResourceTypes"] = json.dumps(asset_region)

            elif group_type in ("tag", "tagPrivate"):
                # ===== ECS public-network tag / ECS private-network tag =====
                # TagList: flattened format TagList.1.TagKey, TagList.1.TagValue
                tag_idx = 1
                if asset_property_str and asset_property_str != "nan":
                    for tag_str in asset_property_str.split(","):
                        tag_str = tag_str.strip()
                        if "=" in tag_str:
                            key, value = tag_str.split("=", 1)
                            api_params[f"TagList.{tag_idx}.TagKey"] = key.strip()
                            api_params[f"TagList.{tag_idx}.TagValue"] = value.strip()
                            tag_idx += 1

                # AutoAddTagEcs: default value 1
                api_params["AutoAddTagEcs"] = "1"

                # TagRelation: multi-tag relation
                tag_relation = str(row.get("多标签关系", ""))
                if tag_relation and tag_relation != "nan":
                    api_params["TagRelation"] = tag_relation

            elif group_type == "ackNamespace":
                # ===== ACK cluster namespace =====
                # AckClusterConnectorId
                connector_id = str(row.get("ACK同步节点ID", ""))
                if connector_id and connector_id != "nan":
                    api_params["AckClusterConnectorId"] = connector_id

                # AckNamespaces: flattened format AckNamespaces.1, AckNamespaces.2
                ns_idx = 1
                if asset_property_str and asset_property_str != "nan":
                    for ns in asset_property_str.split(","):
                        ns = ns.strip()
                        if ns:
                            api_params[f"AckNamespaces.{ns_idx}"] = ns
                            ns_idx += 1

            elif group_type == "ackLabel":
                # ===== ACK cluster pod label =====
                # AckClusterConnectorId
                connector_id = str(row.get("ACK同步节点ID", ""))
                if connector_id and connector_id != "nan":
                    api_params["AckClusterConnectorId"] = connector_id

                # AckLabels: flattened format AckLabels.1.Key, AckLabels.1.Value
                label_idx = 1
                if asset_property_str and asset_property_str != "nan":
                    for label_str in asset_property_str.split(","):
                        label_str = label_str.strip()
                        if "=" in label_str:
                            key, value = label_str.split("=", 1)
                            api_params[f"AckLabels.{label_idx}.Key"] = key.strip()
                            api_params[f"AckLabels.{label_idx}.Value"] = value.strip()
                            label_idx += 1

            print(f"  [{self.name}] [{idx+1}] restoring: {record_name}")
            print(f"    GroupType: {group_type}, IP type: {ip_type}")
            print(f"    Asset property: {asset_property_str}")

            try:
                result = call_api_fn(ak, sk, endpoint, self.restore_api, api_params, security_token)

                if self.uid_column in result and result[self.uid_column]:
                    print(f"    [OK] success, {self.uid_column}: {result[self.uid_column]}")
                    df.at[df.index[idx], '恢复状态'] = '成功'
                    success_count += 1
                else:
                    code = result.get("Code", "")
                    message = result.get("Message", "")
                    if "ErrorAddressGroupExist" in code or "already exists" in message.lower() or "Duplicates" in code:
                        print(f"    [WARN] already exists")
                        df.at[df.index[idx], '恢复状态'] = '已存在'
                        exist_count += 1
                    else:
                        print(f"    [FAIL] failed: {code} - {message}")
                        df.at[df.index[idx], '恢复状态'] = '失败'
                        fail_count += 1

            except Exception as e:
                error_str = str(e)
                if "ErrorAddressGroupExist" in error_str or "already exist" in error_str.lower() or "Duplicates" in error_str:
                    print(f"    [WARN] already exists")
                    df.at[df.index[idx], '恢复状态'] = '已存在'
                    exist_count += 1
                else:
                    print(f"    [FAIL] exception: {error_str[:200]}")
                    df.at[df.index[idx], '恢复状态'] = '失败'
                    fail_count += 1

        # Update the restore status in Excel
        import openpyxl
        wb = openpyxl.load_workbook(excel_file)
        ws = wb[self.sheet_name]
        header_row = [cell.value for cell in ws[1]]
        if '恢复状态' in header_row:
            status_col_idx = header_row.index('恢复状态') + 1
        else:
            status_col_idx = ws.max_column + 1
            ws.cell(row=1, column=status_col_idx, value='恢复状态')

        for i, (_, row) in enumerate(df.iterrows()):
            ws.cell(row=i + 2, column=status_col_idx, value=row.get('恢复状态', '待恢复'))

        wb.save(excel_file)

        print(f"  [{self.name}] restore finished: success {success_count}, fail {fail_count}, skip {skip_count}, existing {exist_count}")
        return (success_count, fail_count, skip_count, exist_count)
