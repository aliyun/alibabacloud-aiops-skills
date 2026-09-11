"""
Custom domain address book plugin
GroupTypes: domain
"""
from .base import AddressBookPlugin


def _parse_address_list(item):
    """Parse the address list"""
    address_list = item.get("AddressList", [])
    if address_list:
        return "\n".join(address_list)
    return ""


class CustomDomainPlugin(AddressBookPlugin):
    name = "自定义域名"
    order = 6
    group_types = ["domain"]
    sheet_name = "自定义域名地址簿"
    
    columns = [
        ("地址簿名称", lambda item: item.get("GroupName", "")),
        ("域名",       _parse_address_list),
        ("描述",       lambda item: item.get("Description", "")),
        ("引用次数",   lambda item: item.get("ReferenceCount", 0)),
        ("地址数量",   lambda item: item.get("AddressListCount", 0)),
    ]
    
    col_widths = [30, 50, 30, 12, 12]

    # ==================== Restore configuration ====================
    restore_api = "AddAddressBook"
    name_column = "地址簿名称"
    uid_column = "GroupUuid"

    @property
    def restore_column_mapping(self):
        return {
            "地址簿名称": "GroupName",
            "描述": "Description",
            "域名": "AddressList",
        }

    @property
    def restore_value_transforms(self):
        def transform_address_list(value):
            """Domain list: newline separated -> comma separated"""
            if value and str(value).strip():
                domains = [d.strip() for d in str(value).split("\n") if d.strip()]
                return ",".join(domains)
            return ""

        return {
            "AddressList": transform_address_list,
        }

    @property
    def restore_static_params(self):
        return {
            "GroupType": "domain",
        }
