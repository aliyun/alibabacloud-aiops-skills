"""Port book plugin - GroupTypes: port"""
from .base import AddressBookPlugin


class PortPlugin(AddressBookPlugin):
    name = "端口"
    order = 7
    group_types = ["port"]
    sheet_name = "端口簿"
    columns = [
        ("端口簿名称", lambda item: item.get("GroupName", "")),
        ("端口",       lambda item: "\n".join(item.get("AddressList", []))),
        ("描述",       lambda item: item.get("Description", "")),
        ("引用次数",   lambda item: item.get("ReferenceCount", 0)),
        ("端口数量",   lambda item: item.get("AddressListCount", 0)),
    ]
    col_widths = [25, 40, 30, 12, 12]

    # ==================== Restore configuration ====================
    restore_api = "AddAddressBook"
    name_column = "端口簿名称"
    uid_column = "GroupUuid"

    @property
    def restore_column_mapping(self):
        return {
            "端口簿名称": "GroupName",
            "描述": "Description",
            "端口": "AddressList",
        }

    @property
    def restore_value_transforms(self):
        def transform_address_list(value):
            """Port list: newline separated -> comma separated"""
            if value and str(value).strip():
                ports = [p.strip() for p in str(value).split("\n") if p.strip()]
                return ",".join(ports)
            return ""

        return {
            "AddressList": transform_address_list,
        }

    @property
    def restore_static_params(self):
        return {
            "GroupType": "port",
        }
