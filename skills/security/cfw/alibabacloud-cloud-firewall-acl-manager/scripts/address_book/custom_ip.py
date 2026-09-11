"""Custom IP address book plugin (ip + ipv6 combination)"""
from .base import AddressBookPlugin

TYPE_MAP = {"ip": "IPv4", "ipv6": "IPv6"}
TYPE_REVERSE_MAP = {"IPv4": "ip", "IPv6": "ipv6"}


def _parse_addr(item):
    """Parse the address list into a string"""
    addresses = item.get("Addresses", [])
    if addresses:
        parts = []
        for a in addresses:
            note = a.get("Note", "")
            val = a.get("Address", "")
            parts.append(f"{val} ({note})" if note else val)
        return "\n".join(parts)
    return "\n".join(item.get("AddressList", []))


class CustomIPPlugin(AddressBookPlugin):
    name = "自定义IP"
    order = 4
    group_types = ["ip", "ipv6"]
    sheet_name = "自定义IP地址簿"
    columns = [
        ("地址簿名称", lambda item: item.get("GroupName", "")),
        ("IP类型",     lambda item: TYPE_MAP.get(item.get("GroupType", ""), item.get("GroupType", ""))),
        ("IP地址",     _parse_addr),
        ("描述",       lambda item: item.get("Description", "")),
        ("引用次数",   lambda item: item.get("ReferenceCount", 0)),
        ("地址数量",   lambda item: item.get("AddressListCount", 0)),
    ]
    col_widths = [30, 12, 50, 30, 12, 12]
    # post_process inherits the default implementation (filters Global=1)

    # ==================== Restore configuration ====================
    restore_api = "AddAddressBook"
    name_column = "地址簿名称"
    uid_column = "GroupUuid"

    @property
    def restore_column_mapping(self):
        return {
            "地址簿名称": "GroupName",
            "IP类型": "GroupType",
            "IP地址": "AddressList",
            "描述": "Description",
        }

    @property
    def restore_value_transforms(self):
        return {
            "GroupType": lambda v: TYPE_REVERSE_MAP.get(v, v),
            "AddressList": lambda v: ",".join([line.strip() for line in v.split("\n") if line.strip()]),
        }

