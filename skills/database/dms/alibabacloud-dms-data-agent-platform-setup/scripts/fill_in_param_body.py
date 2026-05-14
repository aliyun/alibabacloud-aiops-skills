import re
from typing import List, Any, Optional, Tuple, Dict
from copy import deepcopy


class void_arg_t:
    def __init__(self):
        pass


DEFAULT_USERNAME = "dify_user"

# 敏感字段名集合，错误消息中对其值进行脱敏
_SENSITIVE_KEYS = {"DbInstancePassword", "KvStorePassword", "VectordbPassword"}

# 字符串参数的正则格式约束：{参数名: (pattern, 说明)}
_STR_FORMAT_RULES: Dict[str, Tuple[str, str]] = {
    "VpcId":            (r"^vpc-[a-z0-9]+$",          "should match ^vpc-[a-z0-9]+$"),
    "VSwitchId":        (r"^vsw-[a-z0-9]+$",          "should match ^vsw-[a-z0-9]+$"),
    "BackupVSwitchId":  (r"^vsw-[a-z0-9]+$",          "should match ^vsw-[a-z0-9]+$"),
    "SecurityGroupId":  (r"^sg-[a-z0-9]+$",           "should match ^sg-[a-z0-9]+$"),
    "WorkspaceId":      (r"^[a-zA-Z0-9_-]{1,64}$",    "alphanumeric/underscore/hyphen, 1-64 chars"),
    "WorkspaceName":    (r"^[a-zA-Z0-9_-]{1,64}$",    "alphanumeric/underscore/hyphen, 1-64 chars"),
    "DbInstanceAccount":(r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$", "starts with letter, alphanumeric/underscore, 1-64 chars"),
    "DbInstancePassword":(r"^.{8,32}$",               "8-32 characters"),
    "KvStoreAccount":   (r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$", "starts with letter, alphanumeric/underscore, 1-64 chars"),
    "KvStorePassword":  (r"^.{8,32}$",                "8-32 characters"),
    "VectordbAccount":  (r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$", "starts with letter, alphanumeric/underscore, 1-64 chars"),
    "VectordbPassword": (r"^.{8,32}$",                "8-32 characters"),
}


class bodyArgItem_t:
    def __init__(
        self,
        name: str,
        val_type: Any,
        default_val: Any,
        allowed_val_list: Optional[List[Any]],
        required: bool,
    ):
        assert isinstance(name, str)
        self.key_name = name
        self.val_type = val_type
        self.val = default_val
        self.allowed_val_list = allowed_val_list
        self.required = required
        self.check_val(strict=False)

    def check_val(self, strict: bool = True):
        if isinstance(self.val, void_arg_t):
            if strict and self.required:
                raise ValueError(f"{self.key_name}: required")
            return
        # 1. 检查类型
        if self.val_type is not Any and not isinstance(self.val, self.val_type):
            # 对敏感字段脱敏，避免密码出现在错误消息中
            display_val = "***" if self.key_name in _SENSITIVE_KEYS else self.val
            raise ValueError(
                f"{self.key_name}: val <{display_val}> type mis-match, expect: {self.val_type}, got: {type(self.val)}"
            )
        # 2. 检查枚举值
        if self.allowed_val_list and self.val not in self.allowed_val_list:
            display_val = "***" if self.key_name in _SENSITIVE_KEYS else self.val
            raise ValueError(
                f"{self.key_name}: val <{display_val}> not in allowed list <{self.allowed_val_list}>"
            )
        # 3. 对字符串参数进行正则格式校验
        if isinstance(self.val, str) and self.key_name in _STR_FORMAT_RULES:
            pattern, description = _STR_FORMAT_RULES[self.key_name]
            if not re.fullmatch(pattern, self.val):
                raise ValueError(
                    f"{self.key_name}: invalid format, {description}"
                )

    def set_val(self, new_val: Any):
        self.val = new_val
        self.check_val()


FULL_PARAM_LIST: Tuple[bodyArgItem_t, ...] = (
    bodyArgItem_t("VpcId", str, void_arg_t(), None, True),
    bodyArgItem_t("VSwitchId", str, void_arg_t(), None, True),
    bodyArgItem_t("BackupVSwitchId", str, void_arg_t(), None, True),
    bodyArgItem_t("SecurityGroupId", str, void_arg_t(), None, True),
    bodyArgItem_t("NatGatewayOption", str, "NoNeed", ("NoNeed", "Enable"), True),
    bodyArgItem_t("ZoneId", str, void_arg_t(), None, True),
    bodyArgItem_t("DataRegion", str, void_arg_t(), None, True),
    bodyArgItem_t("ResourceQuota", str, "12CU", None, True),
    bodyArgItem_t("Replicas", int, 1, None, True),
    bodyArgItem_t(
        "WorkspaceOption",
        str,
        "CreateNewInstance",
        ("UseExistingInstance", "CreateNewInstance"),
        True,
    ),
    bodyArgItem_t("WorkspaceId", str, void_arg_t(), None, False),
    bodyArgItem_t("WorkspaceName", str, void_arg_t(), None, False),
    bodyArgItem_t(
        "DatabaseOption",
        str,
        "CreateNewInstance",
        ("CreateNewInstance", "UseExistingInstance"),
        True,
    ),
    bodyArgItem_t("DbResourceId", int, void_arg_t(), None, False),
    bodyArgItem_t("DbEngineType", str, "PostgreSQL", None, True),
    bodyArgItem_t("DbInstanceClass", str, "pg.n2.2c.1m", None, True),
    bodyArgItem_t("DbEngineVersion", str, "15.0", None, True),
    bodyArgItem_t("DbInstanceCategory", str, "Basic", None, True),
    bodyArgItem_t("DbStorageType", str, "general_essd", None, True),
    bodyArgItem_t("DbStorageSize", str, "60", None, True),
    bodyArgItem_t("DbInstanceAccount", str, DEFAULT_USERNAME, None, True),
    bodyArgItem_t("DbInstancePassword", str, void_arg_t(), None, True),
    bodyArgItem_t(
        "KvStoreOption",
        str,
        "CreateNewInstance",
        ("CreateNewInstance", "UseExistingInstance"),
        True,
    ),
    bodyArgItem_t("KvStoreResourceId", int, void_arg_t(), None, False),
    bodyArgItem_t("KvStoreType", str, "REDIS", None, True),
    bodyArgItem_t("KvStoreInstanceClass", str, "redis.shard.large.ce", None, True),
    bodyArgItem_t("KvStoreEngineVersion", str, "6.0", None, True),
    bodyArgItem_t("KvStoreNodeType", str, "MASTER_SLAVE", None, True),
    bodyArgItem_t("KvStoreAccount", str, DEFAULT_USERNAME, None, True),
    bodyArgItem_t("KvStorePassword", str, void_arg_t(), None, True),
    bodyArgItem_t(
        "VectordbOption",
        str,
        "CreateNewInstance",
        ("CreateNewInstance", "UseExistingInstance"),
        True,
    ),
    bodyArgItem_t("VectordbResourceId", int, void_arg_t(), None, False),
    bodyArgItem_t("VectordbType", str, void_arg_t(), None, False),
    bodyArgItem_t("VectordbCategory", str, "Basic", None, True),
    bodyArgItem_t("VectordbEngineVersion", str, "7.0", None, True),
    bodyArgItem_t("VectordbInstanceSpec", str, "4C16G", None, True),
    bodyArgItem_t("SegNodeNum", int, 2, None, True),
    bodyArgItem_t("VectordbStorageType", str, "cloud_essd", None, True),
    bodyArgItem_t("SegDiskPerformanceLevel", str, "pl1", None, True),
    bodyArgItem_t("VectordbStorageSize", str, "50", None, True),
    bodyArgItem_t("VectordbAccount", str, DEFAULT_USERNAME, None, True),
    bodyArgItem_t("VectordbPassword", str, void_arg_t(), None, True),
    bodyArgItem_t("StorageType", str, "cloud_essd", None, True),
    bodyArgItem_t("PayType", str, "PrePaid", ("PrePaid", "PostPaid"), True),
    bodyArgItem_t("PayPeriodType", str, "Month", ("Month", "Year"), True),
    bodyArgItem_t("PayPeriod", int, 1, None, True),
    bodyArgItem_t("DryRun", bool, True, (True, False), True),
    bodyArgItem_t("MajorVersion", str, "1.13.x", None, True),
    bodyArgItem_t(
        "Edition",
        str,
        "OpenCommunity",
        ("OpenCommunity", "Community", "Enterprise"),
        True,
    ),
    bodyArgItem_t("EnableExtraEndpoint", bool, True, (True, False), True),
    bodyArgItem_t("OnlyIntranet", bool, False, (True, False), True),
)


def fill_in_param_body(customer_input: Dict[str, Any]) -> Dict[str, Any]:
    param_list: List[bodyArgItem_t] = deepcopy(FULL_PARAM_LIST)

    def reset_param_val(key_name: str, val: Any):
        for param in param_list:
            if param.key_name == key_name:
                param.set_val(val)
                return
        raise ValueError(f"unknown param key name: {key_name}")

    for key_name in customer_input:
        reset_param_val(key_name, customer_input[key_name])

    result = {}
    for param in param_list:
        param: bodyArgItem_t
        param.check_val()
        if not isinstance(param.val, void_arg_t):
            result[param.key_name] = param.val
    post_check(result)
    return result


def post_check(param_body: Dict[str, Any]):
    # 1. 新建或使用已有工作空间
    assert "WorkspaceOption" in param_body, "WorkspaceOption is required"
    if param_body["WorkspaceOption"] == "CreateNewInstance":
        assert (
            "WorkspaceName" in param_body
        ), "WorkspaceName wanted when CreateNewInstance"
    else:
        assert (
            "WorkspaceId" in param_body
        ), "WorkspaceId needed when UseExistingInstance"

    # 2. 新建或使用已有数据库实例
    assert "DatabaseOption" in param_body, "DatabaseOption is required"
    if param_body["DatabaseOption"] == "UseExistingInstance":
        assert (
            "DbResourceId" in param_body
        ), "DbResourceId needed when UseExistingInstance"

    # 3. 新建或使用已有 KV 存储实例
    assert "KvStoreOption" in param_body, "KvStoreOption is required"
    if param_body["KvStoreOption"] == "UseExistingInstance":
        assert (
            "KvStoreResourceId" in param_body
        ), "KvStoreResourceId needed when UseExistingInstance"

    # 4. 新建或使用已有向量库实例
    assert "VectordbOption" in param_body, "VectordbOption is required"
    if param_body["VectordbOption"] == "UseExistingInstance":
        assert (
            "VectordbResourceId" in param_body
        ), "VectordbResourceId needed when UseExistingInstance"


if __name__ == "__main__":
    print(f"共有 {len(FULL_PARAM_LIST)} 个参数需要填写")
