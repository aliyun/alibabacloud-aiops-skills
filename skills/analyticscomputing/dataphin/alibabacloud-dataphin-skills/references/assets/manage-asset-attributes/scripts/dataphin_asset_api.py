#!/usr/bin/env python3
"""dataphin_asset_api.py — Dataphin 资产属性/上架 OpenAPI 调用封装。

不依赖阿里云 SDK，用 requests 手写 HMAC-SHA1 签名，独立部署自签证书可直连。

【实测确认的调用契约（POC 独立部署，V6.3）】
  Version : 2023-06-30（2020-08-30 报 Unknown API）
  Method  : POST，RPC 风格，路径 /
  形态    : 业务参数参与签名 + 平铺放 JSON body；OpTenantId / OpUserId 留 query
  ★ 业务参数放 query 会触发网关 502「AddFieldOperator is not applicable to JsonNull」

  | Action                       | 包裹参数名        | 内部字段大小写 |
  |------------------------------|-------------------|----------------|
  | GetAssetTypeAttributeCodes   | 无（平铺 assetType）| camelCase     |
  | UpdateAssetAttributes        | UpdateCommand     | camelCase      |
  | SubmitAssetsOnShelve         | SubmitCommand     | camelCase      |
  | GetAssetAttributes           | QueryCommand      | camelCase      |
  响应字段统一 PascalCase。

凭证与环境（环境变量，脚本不打印其值）：
  DATAPHIN_AK / DATAPHIN_SK        AccessKey ID / Secret
  DATAPHIN_ENDPOINT                如 dataphin-openapi.poc.lydaas.com
  DATAPHIN_ENDPOINT_IP             可选，独立部署无 DNS 时直连 IP（Host 头仍用域名）
  DATAPHIN_TENANT_ID               OpTenantId
  DATAPHIN_USER_ID                 OpUserId（可选）
  SKILL_SESSION_ID                 必填，继承父层 32 字符小写 hex session-id
"""
import base64
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
import urllib.parse
import uuid
from datetime import datetime, timezone

# Shared helper resolves the installed suite manifest independently of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from skill_user_agent import build_user_agent

try:
    import requests
    import urllib3
except ImportError:
    sys.stderr.write("缺少依赖，请先安装：pip3 install requests\n")
    sys.exit(2)

API_VERSION = "2023-06-30"
BATCH_LIMIT = 50

# 资产类型枚举（实测全部支持；PRD 仅列 3 种且把 BIZ_INDEX 误写为 BIZ_METRIC）
ASSET_TYPES = ["TABLE", "COLUMN", "INDEX", "BIZ_INDEX", "API", "PAGE"]

# 单值语义的 InputMode：传多值会让该资产的**所有**属性都不写入（资产级原子）
SINGLE_VALUE_INPUT_MODES = ("DROPDOWN_SINGLE", "CUSTOM_INPUT", "HYPERLINK")

# 声明 EditableIn 非空（看起来可写）但实测通过 UpdateAssetAttributes **写不进去**的属性：
# 账号名与 user_id 都返回 Success=true 却回读为 []，属性接口对它无效。
# 实测证据（business_owner_id）：
#   写 "SuperAdmin"  → Success=true / FailCount=0，回读 []
#   写 "300006218"（真实 user_id） → 同样 Success=true，回读仍 []
#   改走 UpdateBizMetric --biz-owner-name "SuperAdmin" → BizOwnerName 落库成功，
#   但属性接口侧 business_owner_id 依旧为 [] —— 两套字段不互通。
# value = 替代路径提示，precheck 命中时原样告知用户。
WRITE_INEFFECTIVE_ATTRIBUTES = {
    "business_owner_id": "业务指标的业务负责人请改用 UpdateBizMetric 的 "
                         "--biz-owner-name（填**账号用户名**如 SuperAdmin，不是 user_id）；"
                         "注意该接口是覆盖语义，须先 GetBizMetricByName 回读现值完整回填",
}

# 疑似用户语义的**自定义文本**属性关键词。这类实测不做用户校验（填什么都存得进去），
# 因此只告警不拦截 —— 但填错不会有任何信号，会静静变成脏数据。
# ★ 仅适用于 EnumSourceType 非 SYSTEM_REFERENCE 的属性：SYSTEM_REFERENCE(USER)
#   类实测 **会** 校验 id 存在性（填不存在的 id 静默丢弃），且有专门的值格式
#   warning，不能再套用本启发式文案，否则会同时给出两条相互矛盾的提示。
_USER_SEMANTIC_HINTS = ("owner", "负责人", "用户", "专员")

# 实测为「引用型」但元数据把自己伪装成自由文本的属性。
# 这类属性的 GetAssetTypeAttributeCodes 返回是 InputMode=CUSTOM_INPUT +
# EnumSourceType=MANUAL + SystemReferenceType=null（即看上去就是个文本框），
# 但后端实际会做存在性校验并**静默过滤掉查不到的值**，回读就没了。
# 因为元数据认不出来，precheck 无法自动推导，只能靠这张实测清单兜底提醒。
# value = 向用户索要值时必须转述的取值来源说明。
REFERENCE_LIKE_ATTRIBUTES = {
    "shelve_tags": "标签必须从 Dataphin「标签管理」列表里**已存在的标签**中选，"
                   "不能自编新标签；未登记的标签会被静默丢弃（返回成功但回读为空）。"
                   "另：实测为**单值**语义，传多个会让整条资产写入失败",
    "shelve_directory_ids": "需填**合法的目录 ID**（数字），可从资产目录界面 URL "
                            "或已挂在目标目录下的参照资产反查；填错静默丢弃，"
                            "填非数字直接报 InternalError；实测为**单值**语义",
}

# 上架必填项 ↔ 属性编码映射（实测）；None 表示无对应属性编码、OpenAPI 无法设置。
# ⚠ 本表不保证穷尽：缺失项清单由后端按资产/租户配置动态给出，实测除下列两项外
# 还出现过「数据探查报告」。未登记的项一律按「无法通过 API 修复」处理。
ON_SHELVE_REQUIRED = {
    "归属目录": "shelve_directory_ids",
    "可见范围": None,
    "数据探查报告": None,
}


class DataphinApiError(Exception):
    pass


class AssetApiClient(object):
    def __init__(self, verify_ssl=False):
        self.ak = os.environ.get("DATAPHIN_AK")
        self.sk = os.environ.get("DATAPHIN_SK")
        self.endpoint = os.environ.get("DATAPHIN_ENDPOINT")
        self.endpoint_ip = os.environ.get("DATAPHIN_ENDPOINT_IP")
        self.tenant_id = os.environ.get("DATAPHIN_TENANT_ID")
        self.user_id = os.environ.get("DATAPHIN_USER_ID")
        missing = [n for n, v in [
            ("DATAPHIN_AK", self.ak), ("DATAPHIN_SK", self.sk),
            ("DATAPHIN_ENDPOINT", self.endpoint),
            ("DATAPHIN_TENANT_ID", self.tenant_id)] if not v]
        if missing:
            raise DataphinApiError("缺少必要环境变量：" + " / ".join(missing))
        self.verify_ssl = verify_ssl
        if not verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.user_agent = build_user_agent()

    @staticmethod
    def _pe(s):
        return urllib.parse.quote(str(s), safe="~")

    def _sign(self, params, method="POST"):
        canonical = "&".join(
            self._pe(k) + "=" + self._pe(v) for k, v in sorted(params.items()))
        sts = method + "&" + self._pe("/") + "&" + self._pe(canonical)
        return base64.b64encode(hmac.new(
            (self.sk + "&").encode("utf-8"), sts.encode("utf-8"),
            hashlib.sha1).digest()).decode("utf-8")

    def call(self, action, biz_params):
        """biz_params 参与签名并平铺放 JSON body；公共参数留 query"""
        params = {
            "Action": action,
            "Version": API_VERSION,
            "Format": "JSON",
            "AccessKeyId": self.ak,
            "SignatureMethod": "HMAC-SHA1",
            "SignatureVersion": "1.0",
            "SignatureNonce": str(uuid.uuid4()),
            "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "OpTenantId": self.tenant_id,
        }
        if self.user_id:
            params["OpUserId"] = self.user_id
        params.update(biz_params)
        signature = self._sign(params)

        query = {k: v for k, v in params.items() if k not in biz_params}
        query["Signature"] = signature
        host = self.endpoint_ip or self.endpoint
        try:
            resp = requests.post(
                "https://" + host + "/?" + urllib.parse.urlencode(query),
                data=json.dumps(biz_params, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json",
                         "Host": self.endpoint,
                         "User-Agent": self.user_agent},
                verify=self.verify_ssl, timeout=60)
        except requests.exceptions.RequestException as e:
            # 网络/DNS/TLS/超时类异常统一转成 DataphinApiError，避免抛 traceback
            # 被上层误判为「业务失败」（退出码语义会串）
            hint = ""
            if isinstance(e, requests.exceptions.ConnectionError):
                hint = ("；若为独立部署且域名无 DNS 解析，请设置 "
                        "DATAPHIN_ENDPOINT_IP 直连（Host 头仍用域名）")
            elif isinstance(e, requests.exceptions.Timeout):
                hint = "；请求超时 60s，可稍后重试或缩小批量"
            raise DataphinApiError("%s 网络请求失败（%s）：%s%s" % (
                action, type(e).__name__, e, hint))
        try:
            body = resp.json()
        except ValueError:
            raise DataphinApiError("响应非 JSON（HTTP %s）：%s"
                                   % (resp.status_code, resp.text[:300]))
        if body.get("Code") != "OK":
            raise DataphinApiError("%s 失败 Code=%s Message=%s RequestId=%s" % (
                action, body.get("Code"), body.get("Message"),
                body.get("RequestId")))
        return body

    # ---------- Step 1：查属性定义 ----------
    def get_attribute_codes(self, asset_type):
        """返回属性定义扁平数组（无包裹参数，assetType 平铺）"""
        if asset_type not in ASSET_TYPES:
            raise DataphinApiError("assetType 非法：%s，可选 %s"
                                   % (asset_type, ASSET_TYPES))
        return self.call("GetAssetTypeAttributeCodes",
                         {"assetType": asset_type}).get("Data") or []

    # ---------- 回读属性值 ----------
    def get_attributes(self, guid_list, attribute_codes=None):
        """返回 {guid: {attributeCode: [values]}}；仅返回可编辑属性"""
        if len(guid_list) > BATCH_LIMIT:
            raise DataphinApiError("guidList 超过 %d 条上限" % BATCH_LIMIT)
        q = {"guidList": guid_list}
        if attribute_codes:
            q["attributeCodeList"] = attribute_codes
        body = self.call("GetAssetAttributes",
                         {"QueryCommand": json.dumps(q, ensure_ascii=False)})
        out = {}
        for item in (body.get("Data") or {}).get("AssetAttributeList") or []:
            out[item.get("Guid")] = {
                a.get("AttributeCode"): a.get("Values") or []
                for a in item.get("AttributeList") or []}
        return out

    # ---------- Step 2：覆盖写属性值 ----------
    def update_attributes(self, updates):
        """updates: [{guid, assetType, attributes: {code: [values]}}]
        返回 Data: {TotalCount, SuccessCount, FailCount, ResultList[]}"""
        if len(updates) > BATCH_LIMIT:
            raise DataphinApiError(
                "单次最多 %d 个资产，请分片提交" % BATCH_LIMIT)
        cmd = {"assetAttributeUpdateList": [{
            "guid": u["guid"],
            "assetType": u["assetType"],
            "attributeList": [{"attributeCode": c, "values": v}
                              for c, v in u["attributes"].items()],
        } for u in updates]}
        return self.call("UpdateAssetAttributes", {
            "UpdateCommand": json.dumps(cmd, ensure_ascii=False)}).get("Data")

    # ---------- Step 3：提交上架 ----------
    def submit_on_shelve(self, guid_list):
        """SubmitCommand 只接受 guidList，不支持传归属目录/可见范围。
        失败为逐条失败（HTTP 200 + Code=OK + FailCount>0），无副作用，
        因此可直接用本方法做上架预检：成功即上架完成，失败则回缺失项。"""
        if len(guid_list) > BATCH_LIMIT:
            raise DataphinApiError("guidList 超过 %d 条上限" % BATCH_LIMIT)
        return self.call("SubmitAssetsOnShelve", {
            "SubmitCommand": json.dumps({"guidList": guid_list},
                                        ensure_ascii=False)}).get("Data")


def parse_missing_fields(error_message):
    """从上架失败文案解析缺失项清单。
    实测文案：'资产信息未完善，请完善以下信息：归属目录,可见范围'
    非「信息未完善」类失败（如'当前资产不存在'）返回 []。"""
    if not error_message or "请完善以下信息" not in error_message:
        return []
    tail = error_message.split("请完善以下信息", 1)[1].lstrip("：: ")
    return [x.strip() for x in tail.replace("，", ",").split(",") if x.strip()]


def precheck_attributes(client, asset_type, attrs):
    """写入前按属性定义做本地校验，返回 (violations, warnings)。

    写入是**资产级原子**的（任一属性非法则该资产所有属性都不写入），
    因此本地先拦一遍比让服务端整条拒绝更划算。
    attrs: {attributeCode: [values]}
    """
    defs = {d.get("AttributeCode"): d
            for d in client.get_attribute_codes(asset_type)}
    violations, warnings = [], []
    for code, values in attrs.items():
        d = defs.get(code)
        if d is None:
            violations.append("%s：assetType=%s 下不存在该属性编码"
                              % (code, asset_type))
            continue
        if not d.get("EditableIn"):
            violations.append("%s：EditableIn 为空，该属性不可通过 API 写入" % code)
            continue
        mode = d.get("InputMode")
        if not values:
            if mode != "DROPDOWN_MULTI":
                warnings.append(
                    "%s：InputMode=%s 非多选，传空数组清空属于未定义行为，"
                    "可能返回成功但值不变；如需置空请改为覆盖新值或到界面操作"
                    % (code, mode))
            continue
        if mode in SINGLE_VALUE_INPUT_MODES and len(values) > 1:
            violations.append(
                "%s：InputMode=%s 为单值语义，却传了 %d 个值"
                "（会导致该资产的所有属性都不写入）" % (code, mode, len(values)))
        enum = d.get("EnumValues")
        if enum:
            allowed = [e.get("Value") for e in enum]
            for v in values:
                if v not in allowed:
                    violations.append("%s：值 %r 不在枚举内，可选 %s"
                                      % (code, v, allowed))
        elif d.get("EnumSourceType") == "SYSTEM_REFERENCE":
            ref = d.get("SystemReferenceType")
            if ref == "USER":
                # 实测：值不是裸用户名/裸 user_id，而是序列化用户对象；
                # 属性定义只说 ValueType=STRING，完全不提示这个结构。
                warnings.append(
                    "%s：EnumSourceType=SYSTEM_REFERENCE(USER)，值必须是序列化"
                    "用户对象字符串 {\"id\":\"<user_id>\",\"name\":\"<账号名>\","
                    "\"nameCn\":\"<显示名>\"}（三字段缺一报 InternalError，外层"
                    "不要再套数组）；id 必须是真实 user_id，否则静默丢弃 —— "
                    "写后必看 silentlyDropped" % code)
            else:
                warnings.append(
                    "%s：EnumSourceType=SYSTEM_REFERENCE(%s)，取值须为系统内已存在"
                    "的引用值，且可能要求特定的值结构（USER 类实测需传对象）；"
                    "非法值会被静默丢弃 —— 写后必看 silentlyDropped"
                    % (code, ref))
        # 实测「声明可写但写不进去」的属性：直接拦下并给出替代路径，
        # 否则会拿到 Success=true 的假成功，只有回读才发现值没落库。
        name = d.get("AttributeName") or ""
        if code in WRITE_INEFFECTIVE_ATTRIBUTES:
            violations.append(
                "%s（%s）：该属性虽标注可写，但实测通过 UpdateAssetAttributes "
                "写入无效（账号名与 user_id 均返回成功却回读为空）。%s"
                % (code, name, WRITE_INEFFECTIVE_ATTRIBUTES[code]))
        elif (d.get("AttributeSource") == "CUSTOM"
              # SYSTEM_REFERENCE 类已在上方给过更准确的 warning（且它确实会校验
              # id 存在性），这里不能再说「不做校验」，否则两条提示相互矛盾。
              and d.get("EnumSourceType") != "SYSTEM_REFERENCE"
              and any(k in (code + name).lower()
                      for k in _USER_SEMANTIC_HINTS)):
            warnings.append(
                "%s（%s）：疑似用户语义的自定义属性，实测**不做**用户存在性校验，"
                "填错也会写入且无任何报错（脏数据）；建议填 user_id，"
                "可到 Dataphin「成员管理」页面查询" % (code, name))
        # 元数据伪装成自由文本的引用型属性：实测清单兜底提醒取值来源，
        # 否则用户会当成普通文本自编值，写完被静默丢弃而不自知。
        if code in REFERENCE_LIKE_ATTRIBUTES and values:
            warnings.append("%s（%s）：%s"
                            % (code, name, REFERENCE_LIKE_ATTRIBUTES[code]))
        max_len = d.get("MaxLength")
        if max_len:
            for v in values:
                if len(str(v)) > max_len:
                    violations.append("%s：值长度 %d 超过 MaxLength=%d"
                                      % (code, len(str(v)), max_len))
    return violations, warnings


def diff_written(client, guid_list, expected):
    """写后批量回读校验，返回 {guid: {code: {expected, actual}}}。
    必须做——实测部分属性会「返回成功但值被静默丢弃」（见 SKILL.md 常见坑）。"""
    actual_all = client.get_attributes(guid_list, list(expected.keys()))
    dropped = {}
    for guid in guid_list:
        actual = actual_all.get(guid, {})
        diff = {c: {"expected": v, "actual": actual.get(c, [])}
                for c, v in expected.items() if actual.get(c, []) != v}
        if diff:
            dropped[guid] = diff
    return dropped
