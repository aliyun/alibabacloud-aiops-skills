---
name: manage-asset-attributes
description: |-
  查询资产类型下可用的自定义属性定义，并按 GUID 批量覆盖写资产属性值（数据开发工作流回写资产画像的典型场景）。
  当用户场景涉及 资产自定义属性、属性回写、批量更新属性、资产打标、工作流回写画像 时进入。

  触发场景：查某类资产（TABLE/COLUMN）有哪些可填属性；把加工/治理结果批量写回资产属性（覆盖写，支持清空）；任务结束后回写负责人/密级/上架说明等。

  触发词：资产属性、自定义属性、属性回写、批量更新属性、update-asset-attributes、get-asset-type-attribute-codes、AssetAttribute、资产打标。

  关键限制：InputMode（CUSTOM_INPUT/DROPDOWN_SINGLE/DROPDOWN_MULTI/HYPERLINK）决定 Values 校验；写入为覆盖(Upsert)语义，Values=[] 表示清空；单次批量 ≤ 50 条；19 位 ID 必须字符串。
---

# 资产自定义属性管理（查询定义 + 批量覆盖写）

## 1. Scenario Description

围绕 Dataphin 资产目录的「自定义属性」做两件事：

1. **查可用属性定义**（`GetAssetTypeAttributeCodes`）：按资产类型（TABLE / COLUMN）拿到该类型下所有可填属性的编码、输入方式、枚举值、超链接目标、最大长度等元信息 —— 决定后续能写哪些属性、值怎么填。
2. **批量覆盖写属性值**（`UpdateAssetAttributes`）：对一批资产 GUID 一次性写入 / 覆盖 / 清空自定义属性值，返回逐条成功/失败与整体统计。

典型用于**数据开发或治理工作流回写资产画像**：任务跑完后，把「负责人、数据密级、上架说明、外部链接」等结果写回对应表/字段的自定义属性。

**Architecture**：`Dataphin Tenant → Asset(GUID: TABLE/COLUMN) → AssetAttribute(AttributeCode + Values[])`。

> 属性值查询（回读校验）请配合只读子 skill `query-asset-details`（`GetAssetAttributes`）使用。

## 2. Installation

```bash
aliyun plugin install --names aliyun-cli-dataphin-public
```
（详见 [`references/cli-installation-guide.md`](references/cli-installation-guide.md)）

> **命令收录说明**：本组 Action（`GetAssetTypeAttributeCodes` / `UpdateAssetAttributes`）为 V6.3 新增，若当前 `aliyun dataphin-public --help` 未列出对应 kebab-case 命令，说明本地插件版本偏低，请先 `aliyun plugin update`；仍未收录时用 §8 的 OpenAPI SDK 兜底路径调用（API 版本 `2023-06-30`）。

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

## 4. Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, print, or expose AK/SK values in the conversation or logs
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> install/update from https://aliyuncli.alicdn.com (see `references/cli-installation-guide.md` for the OS-specific script).

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## 5. RAM Policy

最小权限策略详见 [`references/ram-policies.md`](references/ram-policies.md)。

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| 参数 | 必填 | 描述 | 默认值 |
|---|---|---|---|
| `OpTenantId` | 是 | 操作租户 ID（19 位 snowflake，**字符串传**） | — |
| `AssetType` | 是（查定义） | 资产类型枚举：`TABLE` / `COLUMN` | — |
| `Guid` | 是（写入） | 资产 GUID，如 `odps.<tenant>.<project>.<table>` | — |
| `AttributeCode` | 是（写入） | 属性编码，来自 `GetAssetTypeAttributeCodes` 返回 | — |
| `Values` | 是（写入） | 属性值数组；`[]` 表示清空该属性 | — |

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-devops` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/manage-asset-attributes/{session-id}
```

> SDK 兜底路径（§8）请把同一字符串设置到 OpenAPI Client 的 `user_agent` 配置项，保持可观测性一致。

## 8. Core Workflow

```bash
OP_TENANT_ID="<19 位租户 ID 字符串>"
SESSION_ID="<inherited from alibabacloud-dataphin-devops>"
UA="AlibabaCloud-Agent-Skills/manage-asset-attributes/$SESSION_ID"
```

### Step 1 · 查可用属性定义（GetAssetTypeAttributeCodes，只读）

CLI（插件收录后）：

```bash
aliyun dataphin-public get-asset-type-attribute-codes \
  --OpTenantId "$OP_TENANT_ID" \
  --AssetType TABLE \
  --user-agent "$UA"
```

返回 `Data` 为属性定义**扁平数组**，每个元素关键字段：

```jsonc
{
  "AttributeCode": "code02",          // 属性编码（写入时用它）
  "AttributeName": "密级",
  "InputMode": "DROPDOWN_SINGLE",     // ★ 类型分支字段
  "EnumSourceType": "MANUAL",         // MANUAL 手工枚举 / SYSTEM_REFERENCE 系统引用
  "EnumValues": [ { "Value": "1", "DisplayName": "秘密" } ],
  "LinkTarget": null,                 // HYPERLINK 时为 CURRENT_PAGE / NEW_PAGE
  "MaxLength": 1000                   // 文本类最大长度（如有）
}
```

### 类型分支：InputMode 决定 Values 怎么填

| InputMode | 含义 | Values 规则 |
|---|---|---|
| `CUSTOM_INPUT` | 自定义文本输入 | 单元素字符串数组，如 `["数仓团队"]` |
| `DROPDOWN_SINGLE` | 下拉单选 | 单元素，取值必须∈ `EnumValues[].Value` |
| `DROPDOWN_MULTI` | 下拉多选 | 多元素，每个∈ `EnumValues[].Value` |
| `HYPERLINK` | 超链接 | 单元素 URL 字符串，跳转行为看 `LinkTarget` |

### Step 2 · 批量覆盖写属性值（UpdateAssetAttributes，⚠ 写操作）

CLI（插件收录后）：

```bash
aliyun dataphin-public update-asset-attributes \
  --OpTenantId "$OP_TENANT_ID" \
  --UpdateCommand '{
    "AssetAttributeUpdateList": [
      {
        "Guid": "odps.<tenant>.<project>.<table>",
        "AssetType": "TABLE",
        "AttributeList": [
          { "AttributeCode": "code02", "Values": ["1"] },
          { "AttributeCode": "shelve_description", "Values": ["已治理，可对外"] }
        ]
      }
    ]
  }' \
  --user-agent "$UA"
```

写入语义（**已在测试环境端到端验证**）：

- **覆盖写(Upsert)**：新值整体替换旧值，不是追加。
- **清空**：`"Values": []` 会把该属性清空。
- **批量部分成功**：`Data.{TotalCount, SuccessCount, FailCount, ResultList[]}`，`ResultList[i].{Success, ErrorCode, ErrorMessage}` 逐条给出结果；单条失败不影响其它条。
- **批量上限**：`AssetAttributeUpdateList` 单次 ≤ 50 条，超限整体 400 拒绝。

### SDK 兜底路径（命令未收录时）

新增 Action 未进本地插件时，用通用 OpenAPI SDK 直调（Python 示例，API 版本 `2023-06-30`，RPC 风格）：

```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as om
from alibabacloud_tea_util import models as um
import json, os

conf = om.Config(
    access_key_id=os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"],
    access_key_secret=os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"],
    endpoint=os.environ["DATAPHIN_OPENAPI_ENDPOINT"],  # 独立部署必填
)
conf.user_agent = "AlibabaCloud-Agent-Skills/manage-asset-attributes/<session-id>"
client = OpenApiClient(conf)

params = om.Params(action="UpdateAssetAttributes", version="2023-06-30",
    protocol="HTTPS", method="POST", auth_type="AK", style="RPC",
    pathname="/", req_body_type="formData", body_type="json")
# 对象/数组参数以 JSON 字符串放入 formData
body = {"UpdateCommand": json.dumps({"AssetAttributeUpdateList": [
    {"Guid": "odps.<tenant>.<project>.<table>", "AssetType": "TABLE",
     "AttributeList": [{"AttributeCode": "code02", "Values": ["1"]}]}
]}, ensure_ascii=False)}
req = om.OpenApiRequest(query={"OpTenantId": "<tenant>"}, body=body)
runtime = um.RuntimeOptions(); runtime.ignore_ssl = True   # 独立部署自签证书
resp = client.call_api(params, req, runtime)["body"]
print(resp)
```

> `GetAssetTypeAttributeCodes` 兜底同理：`AssetType` 放 query，无 body。

### 执行前确认（**写操作必备 / HITL 章节**）

> `UpdateAssetAttributes` 是写操作，调用方执行前必须二次确认：
> - 即将写入的 GUID 清单、AttributeCode 与 Values（脱敏后）
> - 影响范围（哪个租户 / 多少个资产 / 是否含清空 `Values:[]`）
> - 覆盖写不可自动回滚 —— 如需回滚，须先用 `query-asset-details` 读出原值另存
> - 替代方案：先对 1 个 GUID 试写并回读，确认无误再批量

仅当用户明确回复"确认 / yes / 执行"后才发起写命令。

## 9. Success Verification

三步法（详见 [`references/acceptance-criteria.md`](references/acceptance-criteria.md)）：

1. 同步返回 `Success=true` 且 `Data.FailCount=0`（整体成功）。
2. 逐条核对 `Data.ResultList[i].Success=true`（部分成功时定位失败条）。
3. 用 `query-asset-details`（`GetAssetAttributes`）回读被写 GUID，确认 `Values` 与写入一致。

## 10. Cleanup

属性写入无独立资源可删除；如需还原，用 Step 2 把属性覆盖写回原值（原值须在写入前经 `query-asset-details` 读出保存），或 `Values:[]` 清空本次写入的属性。

## 11. Command Tables

详见 [`references/related-commands.md`](references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 大整数 ID（19 位 snowflake）一律字符串传参（参 [`../../../../.qoder/rules/repo-conventions.md`](../../../../.qoder/rules/repo-conventions.md)）。
2. 写操作（update）执行前必须 HITL 二次确认；覆盖写前先读原值以备回滚。
3. 写入前先跑 Step 1 拿到合法 `AttributeCode` 与枚举 `Value`，避免非法值。

### ✗ 平台限制

#### ✗ 批量条数上限
- 限制描述：`UpdateAssetAttributes` 单次 `AssetAttributeUpdateList` ≤ 50 条，超限整体拒绝。
- 替代方案：客户端分片，每片 ≤ 50 条循环提交。

### 常见坑

#### [Agent 自主发现] 写入不存在的 AttributeCode 会静默成功
- 现象：写一个当前资产类型不存在的属性编码时，返回 `Success=true`，`ErrorCode=null`，并不报 `InvalidAttributeCode`。
- 结论：**务必先跑 Step 1 校验 AttributeCode 合法性**，不要依赖服务端拦截；已作为 PRD 偏差反馈研发。

#### [Agent 自主发现] 文本超长未被拦截
- 现象：文本属性即便定义了 `MaxLength`，写入超长文本仍返回 `Success=true`。
- 结论：客户端应在写入前按 `MaxLength` 自校验，避免脏数据；已作为 PRD 偏差反馈研发。

#### [Agent 自主发现] 部分自定义输入属性提示“配置已变更”
- 现象：个别 `CUSTOM_INPUT` 属性写入报 `OperateFailed：配置已变更，无法提交`。
- 结论：该属性定义在后台被改动，需在控制台重新确认属性配置后再写；换用稳定的系统文本属性可绕过。

### Reference Links

- [`references/cli-installation-guide.md`](references/cli-installation-guide.md)
- [`references/ram-policies.md`](references/ram-policies.md)
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md)
- [`references/related-commands.md`](references/related-commands.md)
