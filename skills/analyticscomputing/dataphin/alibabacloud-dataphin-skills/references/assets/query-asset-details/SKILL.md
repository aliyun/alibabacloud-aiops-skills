---
name: query-asset-details
description: |-
  综合查询资产的完整画像：批量读取资产自定义属性值（GetAssetAttributes），并查询单个资产的目录挂载层级链与专题/目录描述（GetCatalogAssetDetails 增强）。纯只读，不含任何写操作。
  当用户场景涉及 资产画像查询、资产属性值查询、目录层级、资产挂在哪个专题、目录路径、资产上下文 时进入。

  触发场景：一次性拿一批资产（GUID）的自定义属性值；查某资产挂在哪个专题/目录、完整层级路径；属性写入后回读校验。

  触发词：资产画像、资产属性查询、get-asset-attributes、目录层级、DirectoryChain、专题、get-catalog-asset-details、资产详情、资产挂载目录。

  关键限制：GetAssetAttributes 单次 GuidList ≤ 50；不传 AttributeCodeList 返回全部属性；GUID 不存在不报错且不返回；DirectoryChain 按 Level 升序、末节点为叶子；19 位 ID 必须字符串。
---

# 资产详情综合查询（属性值 + 目录层级）

## 1. Scenario Description

只读地拼出一个资产的「完整画像」，覆盖两类信息：

1. **自定义属性值**（`GetAssetAttributes`）：按一批 GUID 批量读取资产的自定义属性当前取值，可选按 `AttributeCodeList` 过滤只取关心的属性。
2. **目录层级上下文**（`GetCatalogAssetDetails` 增强）：查单个资产挂载的专题/目录，V6.3 起 `Directories` 扩展返回专题描述、目录描述与**目录层级链 `DirectoryChain`**（从根到叶子的完整路径）。

典型用于**资产盘点、画像展示、属性写入后的回读校验**。本 skill 全部为只读 API，安全无副作用。

**Architecture**：`Dataphin Tenant → Asset(GUID) →（AttributeList[] + Directories[] with DirectoryChain[]）`。

> 属性的**写入**请用子 skill `manage-asset-attributes`（`UpdateAssetAttributes`）。

## 2. Installation

```bash
aliyun plugin install --names aliyun-cli-dataphin-public
```
（详见 [`references/cli-installation-guide.md`](references/cli-installation-guide.md)）

> **命令收录说明**：`GetAssetAttributes` 为 V6.3 新增，`GetCatalogAssetDetails` 为 V6.3 增强出参；若当前 `aliyun dataphin-public --help` 未列出对应 kebab-case 命令，请先 `aliyun plugin update`；仍未收录时用 §8 的 OpenAPI SDK 兜底路径调用（API 版本 `2023-06-30`）。

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
| `GuidList` | 是（查属性值） | 资产 GUID 数组，单次 ≤ 50 | — |
| `AttributeCodeList` | 否 | 属性编码过滤；不传返回全部属性 | 全部 |
| `Guid` | 是（查目录） | 单个资产 GUID | — |
| `IncludeColumns` | 否 | 是否含字段级信息 | false |
| `IncludeDetailedAttributes` | 否 | 是否含明细属性 | false |

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-devops` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/query-asset-details/{session-id}
```

> SDK 兜底路径（§8）请把同一字符串设置到 OpenAPI Client 的 `user_agent` 配置项，保持可观测性一致。

## 8. Core Workflow

```bash
OP_TENANT_ID="<19 位租户 ID 字符串>"
SESSION_ID="<inherited from alibabacloud-dataphin-devops>"
UA="AlibabaCloud-Agent-Skills/query-asset-details/$SESSION_ID"
```

### Step 1 · 批量查资产属性值（GetAssetAttributes，只读）

CLI（插件收录后）：

```bash
aliyun dataphin-public get-asset-attributes \
  --OpTenantId "$OP_TENANT_ID" \
  --QueryCommand '{
    "GuidList": ["odps.<tenant>.<project>.<table>"],
    "AttributeCodeList": ["code02", "shelve_description"]
  }' \
  --user-agent "$UA"
```

返回结构：

```jsonc
{
  "Success": true,
  "Data": {
    "AssetAttributeList": [
      {
        "Guid": "odps.<tenant>.<project>.<table>",
        "AttributeList": [
          { "AttributeCode": "code02", "Values": ["1"] },
          { "AttributeCode": "shelve_description", "Values": ["已治理"] }
        ]
      }
    ]
  }
}
```

要点（**已在测试环境端到端验证**）：

- 不传 `AttributeCodeList` → 返回该资产**全部**自定义属性。
- 传了 `AttributeCodeList` → 只返回指定属性（顺序与传入一致）。
- **GUID 不存在**：`Success=true`，`AssetAttributeList` 中**不含**该资产（不报错）。
- **批量上限**：`GuidList` 单次 ≤ 50，超限整体 400 拒绝。

### Step 2 · 查目录层级链（GetCatalogAssetDetails，只读）

CLI（插件收录后）：

```bash
aliyun dataphin-public get-catalog-asset-details \
  --OpTenantId "$OP_TENANT_ID" \
  --GetCatalogAssetDetailsQuery '{
    "Guid": "odps.<tenant>.<project>.<table>",
    "IncludeColumns": true,
    "IncludeDetailedAttributes": true
  }' \
  --user-agent "$UA"
```

V6.3 起 `Data.Directories[]` 每个挂载项扩展如下：

```jsonc
{
  "TopicId": 113086,
  "TopicName": "专题B",
  "TopicDescription": null,              // 描述为空返回 null
  "DirectoryId": 1130876689044,
  "DirectoryName": "A1",
  "DirectoryDescription": "",            // 描述为空返回 空串
  "DirectoryChain": [                    // ★ 从根到叶子的完整层级链
    { "DirectoryId": 1130876689040, "DirectoryName": "根目录", "Level": 1 },
    { "DirectoryId": 1130876689044, "DirectoryName": "A1",   "Level": 2 }
  ]
}
```

要点（**已在测试环境端到端验证**）：

- `DirectoryChain` 按 `Level` **升序**，**末节点即叶子目录**（其 `DirectoryId` == 外层 `DirectoryId`）。
- 描述字段为空时：`TopicDescription` 返回 `null`，`DirectoryDescription` 返回 `""`（空串），调用方需兼容两种空值。
- 增强字段**无需新增入参**即返回（向后兼容）。
- 一个资产可挂在**多个目录/专题**，`Directories[]` 每项各自携带独立完整层级链。

### SDK 兜底路径（命令未收录时）

新增/增强 Action 未进本地插件时，用通用 OpenAPI SDK 直调（Python 示例，API 版本 `2023-06-30`，RPC 风格）：

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
conf.user_agent = "AlibabaCloud-Agent-Skills/query-asset-details/<session-id>"
client = OpenApiClient(conf)

params = om.Params(action="GetAssetAttributes", version="2023-06-30",
    protocol="HTTPS", method="POST", auth_type="AK", style="RPC",
    pathname="/", req_body_type="formData", body_type="json")
body = {"QueryCommand": json.dumps(
    {"GuidList": ["odps.<tenant>.<project>.<table>"]}, ensure_ascii=False)}
req = om.OpenApiRequest(query={"OpTenantId": "<tenant>"}, body=body)
runtime = um.RuntimeOptions(); runtime.ignore_ssl = True   # 独立部署自签证书
resp = client.call_api(params, req, runtime)["body"]
print(resp)
```

> `GetCatalogAssetDetails` 兜底同理：`action="GetCatalogAssetDetails"`，body 用 `GetCatalogAssetDetailsQuery`。

> 本 skill 全部为只读查询，无写操作、无 HITL 确认要求。

## 9. Success Verification

- `GetAssetAttributes`：`Success=true`；命中资产的 `AttributeList` 含预期编码；不存在 GUID 不在结果中。
- `GetCatalogAssetDetails`：`Success=true`；`Directories[].DirectoryChain` 存在、`Level` 升序、末节点为叶子。
- 详见 [`references/acceptance-criteria.md`](references/acceptance-criteria.md)。

## 10. Cleanup

纯只读查询，无资源产生，无需清理。

## 11. Command Tables

详见 [`references/related-commands.md`](references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 大整数 ID（19 位 snowflake）一律字符串传参（参 [`../../../../.qoder/rules/repo-conventions.md`](../../../../.qoder/rules/repo-conventions.md)）。
2. 只查关心的属性时传 `AttributeCodeList`，减少响应体积。
3. 大批量查询按 50 一片分片调用。

### ✗ 平台限制

#### ✗ 批量条数上限
- 限制描述：`GetAssetAttributes` 单次 `GuidList` ≤ 50，超限整体拒绝。
- 替代方案：客户端分片，每片 ≤ 50 个 GUID 循环查询。

### 常见坑

#### [Agent 自主发现] GUID 不存在不会报错
- 现象：查询不存在的 GUID 时 `Success=true`，只是结果里没有该资产。
- 结论：不能凭 `Success` 判断 GUID 有效性，须核对 `AssetAttributeList` 是否真的返回了目标 GUID。

#### [Agent 自主发现] 空描述有两种空值形态
- 现象：`TopicDescription` 空时为 `null`，`DirectoryDescription` 空时为 `""`。
- 结论：展示层需同时兼容 `null` 与空串，避免误判“字段缺失”。

### Reference Links

- [`references/cli-installation-guide.md`](references/cli-installation-guide.md)
- [`references/ram-policies.md`](references/ram-policies.md)
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md)
- [`references/related-commands.md`](references/related-commands.md)
