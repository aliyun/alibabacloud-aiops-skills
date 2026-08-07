---
name: manage-app-and-bindauth
description: |
  数据服务应用管理与 API 权限绑定。创建应用 → 添加成员 → 为应用授权 API → 验证授权结果 → 获取 AppKey/AppSecret 供后续调用使用。
  触发场景：创建数据服务应用 / API 授权 / 权限绑定 / 应用管理 / 密钥管理。
---

# 数据服务应用管理与 API 权限绑定

## 1. Scenario Description

管理员/开发者通过阿里云 CLI 完成数据服务应用的创建与 API 权限绑定全流程：

**业务流程：**
```
创建应用 → 添加成员（可选）→ 发现已发布 API → 授权 API（字段级）→ 验证授权 → 获取凭证
```

> ⚠️ **当前限制（据实测）**：`授权 API`（步骤 3，`grant-data-service-api`）与 `回收授权`（Cleanup，`revoke-data-service-api`）**当前 OpenAPI 暂不支持**——命令虽存在，但授权所需的字段标识（`Columns` / 字段 ID）无法通过现有 OpenAPI 获取，实测无法构造出有效的授权参数。**请通过 Dataphin 控制台完成 API 授权与回收**；本 Skill 的应用创建、成员、凭证管理不受影响。

**资源拓扑：**
```
数据服务项目
└── 应用（App）
    ├── AppKey / AppSecret（调用凭证）
    ├── 应用成员
    └── 已授权 API
        ├── API 信息
        └── 授权字段（GrantColumns）
```

**前置条件：**
- 数据服务项目已存在，当前用户为项目成员
- 至少一个 API 已发布到生产环境（可由 S1 `create-and-publish-api` 产出）

**与 S1 的衔接：**
- S1 产出 `ApiId`，本 Skill 消费 `ApiId` 完成授权
- 本 Skill 产出 `AppKey` / `AppSecret`，供 S3 `call-data-service-api` 消费

## 2. Installation

**Pre-check: Aliyun CLI >= 3.4.8 required**
> 运行 `aliyun version` 确认版本 >= 3.4.8。未安装或版本过低，请从 https://aliyuncli.alicdn.com 安装/升级（各操作系统一键脚本见 ./references/cli-installation-guide.md）。

**Pre-check: Aliyun CLI plugin update required**
> [MUST] 运行 `aliyun configure set --auto-plugin-install true` 开启插件自动安装。
> [MUST] 运行 `aliyun plugin update` 确保已装插件保持最新。

```bash
# 安装 aliyun CLI（>= 3.4.8）：https://github.com/aliyun/aliyun-cli
# 各操作系统一键安装脚本见 ./references/cli-installation-guide.md

# 开启插件自动安装并更新已装插件
aliyun configure set --auto-plugin-install true
aliyun plugin update

# 安装 dataphin-public 插件
aliyun plugin install --names aliyun-cli-dataphin-public

# 验证
aliyun version            # 需 >= 3.4.8
aliyun dataphin-public --help
```

详见 [CLI 安装指南](./references/cli-installation-guide.md)。

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

## 4. Authentication

### Pre-check: Credentials Required

```bash
# 检查凭证配置
aliyun configure list

# 检查 CLI 版本
aliyun version
# 要求 >= 3.4.8

# 检查插件可用
aliyun dataphin-public --help
```

**凭证不可打印**：任何时候不得将 AccessKey ID/Secret 输出到终端或日志。

## 5. RAM Policy

本 Skill 涉及的最小 RAM 权限：

```json
{
  "Effect": "Allow",
  "Action": [
    "dataphin:CreateDataServiceApp",
    "dataphin:GetDataServiceApp",
    "dataphin:GetDataServiceAppGroups",
    "dataphin:ListDataServiceApps",
    "dataphin:ListDataServicePublishedApis",
    "dataphin:AddDataServiceAppMember",
    "dataphin:GrantDataServiceApi",
    "dataphin:RevokeDataServiceApi",
    "dataphin:ListAuthorizedDataServiceApiDetails",
    "dataphin:ResetDataServiceAppSecret"
  ],
  "Resource": "*"
}
```

### Permission Failure Handling

若遇到权限错误（HTTP 403 或 ErrorCode 含 `Forbidden`/`NoPermission`），请：
1. 确认 RAM 用户已附加上述策略
2. 确认策略中 Resource 范围覆盖目标租户
3. 联系租户管理员授权

详见 [RAM 策略参考](../../ram-policies.md)。

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation**
> 执行前必须确认以下业务参数：

| 参数 | 含义 | 获取方式 | 必填 |
|------|------|---------|------|
| OpTenantId | 租户 ID | profile 或询问用户 | 是 |
| ProjectId | 数据服务项目 ID | 需从控制台页面请求中手动获取（见下方说明） | 是（查已发布 API/应用列表用） |
| AppGroupId | 应用分组 ID（**≠ ProjectId**） | `get-data-service-app-groups` 查询（见步骤 1a） | 创建应用时必填 |
| AppName | 应用名称 | 用户指定 | 是 |
| AppKeyStr | 应用 AppKey（字符串形式） | 创建返回 / `AppInfoList[].AppKeyStr` / `get-data-service-app` | 查已授权时必填 |
| ApiId | 要授权的 API ID | S1 产出或步骤 2b 查询 | 是 |
| GrantColumns | 授权字段列表 | 查询 API 字段后选择 | 是（控制台授权用） |
| UserId | 要添加的成员 ID | 用户提供 | 否 |

**ProjectId 获取说明（重要）：**
> 当前 **无 OpenAPI 可列举数据服务项目**，ProjectId 需从 Dataphin 控制台页面的网络请求中手动获取：
> 1. 打开浏览器 DevTools（F12）→ Network 面板
> 2. 在 Dataphin 控制台进入「数据服务」模块，切换到目标项目
> 3. 观察网络请求中的 `projectId` 参数（通常出现在请求 URL 或 body 中，如 `projectId=126`）
> 4. 将该整数值作为 `--project-id` 传入
>
> ℹ️ 典型值为小整数（如 `126`、`130`），**与 19 位 snowflake ID 不同**。

**ApiId 获取说明：**
> 若由 S1 `create-and-publish-api` 产出，直接传入即可。
> 若需独立获取，可通过步骤 2b `list-data-service-published-apis` 查询项目下已发布 API 列表。

**GrantColumns 获取说明：**
> 授权 API 时需指定允许应用访问的字段列表。可通过 `get-data-service-api-document` 查询 API 返回参数，从中选择需要授权的字段名。
> ⚠️ **实测限制**：授权所需的字段标识无法通过现有 OpenAPI 完整获取，`grant-data-service-api` 当前无法经 OpenAPI 完成授权，请改用控制台（详见步骤 3）。

> **⚠️ 应用定位暗坑**：`list-data-service-apps` 按 `AppName` 找应用时，**同租户可能存在多个同名应用**（列表不返回 AppKey）。若用户给了 AppKey，应**用 AppKey 唯一确定**目标应用（逐个 `get-data-service-app` 取详情核对 `AppKey`），避免授权到错的应用。注意 `get-data-service-app` 返回的 `AppKey` 为**字符串**（如 `"200000326"`）。

## 7. Observability

本子 Skill 的 session-id **继承自父 Skill `alibabacloud-dataphin-skills`**，不重新生成。

所有 CLI 命令携带：
```
--user-agent AlibabaCloud-Agent-Skills/manage-app-and-bindauth/{SESSION_ID}
```

其中 `{SESSION_ID}` 为父 Skill 生成的 32 字符小写十六进制字符串。

## 8. Core Workflow

### 步骤 1：创建数据服务应用

#### 步骤 1a：查询应用分组（获取 AppGroupId）

> **⚠️ 关键概念**：创建应用需要 **应用分组 ID（`AppGroupId`）**，它与 `ProjectId` 是**两个独立概念**——`AppGroupId` 来自 Dataphin 独立的「应用分组」管理体系，**不能用 `ProjectId` 代替**。传错分组 ID（如把 `ProjectId` 当成 `AppGroupId`）服务端**不报错**，但应用会被分到不可见/不存在的分组，在平台分组管理页面找不到。

```bash
aliyun dataphin-public get-data-service-app-groups \
  --op-tenant-id "{OpTenantId}" \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/manage-app-and-bindauth/{SESSION_ID}"
```

> 从返回列表中选择目标分组的 `Id` 作为 `AppGroupId`（如 `509`）。注：该命令的 `--project-id` 参数**已废弃**，可不传；如需新建分组用 `create-data-service-app-group`。

#### 步骤 1b：创建应用

#### HITL 确认（写操作）

执行前确认以下信息：
- 应用名称：`{AppName}`
- 应用分组：`{AppGroupId}`（来自步骤 1a，**非 ProjectId**）
- 影响范围：在目标分组下创建新应用
- 可回滚：创建后可删除

**确认后执行：**

```bash
aliyun dataphin-public create-data-service-app \
  --op-tenant-id "{OpTenantId}" \
  --create-command '{"AppGroupId": {AppGroupId}, "AppName": "{AppName}", "Scenarios": "OPENAPI"}' \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/manage-app-and-bindauth/{SESSION_ID}"
```

> **create-command 结构**：`{AppGroupId: integer, AppName: string, AppKey?: string, AppSecret?: string, OwnerIds?: [string], Scenarios?: string}`。**无 `ProjectId`、无 `AppDescription` 字段**；`AppGroupId` 为整数，直接内嵌不加引号。

**响应处理：**
- 确认 `Code` 为成功
- 提取 `AppId`（字符串格式，19 位 snowflake ID）
- 提取 `AppKey`、`AppSecret`（**仅此一次返回，请务必保存**）

> **重要**：AppSecret 仅在创建时返回一次，后续无法重新获取（除非重置）。请提示用户妥善保存。

### 步骤 2：添加应用成员（可选）

#### HITL 确认（写操作）

执行前确认：
- 目标应用：`{AppName}`（ID: `{AppId}`）
- 要添加的成员：`{UserId}`
- 影响范围：该成员获得应用的访问权限

**确认后执行：**

```bash
aliyun dataphin-public add-data-service-app-member \
  --OpTenantId "{OpTenantId}" \
  --AddCommand '{"AppId": "{AppId}", "UserId": "{UserId}"}' \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/manage-app-and-bindauth/{SESSION_ID}"
```

**响应处理：**
- 确认 `Code` 为成功

### 步骤 2b：查询已发布 API（获取待授权 ApiId）

> 本步骤用于**发现项目中已发布的 API**——若你已有 ApiId（如 S1 `create-and-publish-api` 产出），可跳过。此为**只读**操作，无需 HITL 确认。
>
> **⚠️ 前置约束（必须）**：本步骤要求**用户显式给出数据服务项目 ID（`ProjectId`）**——当前无 OpenAPI 可列举项目，无法自动发现（获取方式见 §6 ProjectId 获取说明）。**若用户未提供 `ProjectId`，必须先向用户索取，不得臆测或使用默认值。**

```bash
aliyun dataphin-public list-data-service-published-apis \
  --op-tenant-id "{OpTenantId}" \
  --project-id "{ProjectId}" \
  --list-query PageNo=1 PageSize=100 \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/manage-app-and-bindauth/{SESSION_ID}"
```

**响应处理：**
- 已发布 API 列表位于 `PageResult.ApiList[]`，总数位于 `PageResult.TotalCount`
- 每个 API 含 `ApiId`（整数）、`ApiName`、`GroupName`、`AppCount`（已授权应用数）、`AppInfoList`（已授权的应用明细）
- 提取目标 `ApiId` 供后续授权使用（步骤 3 在控制台操作时需选中该 API）

> **⚠️ 分页必传**：`--list-query` 中 `PageNo` 与 `PageSize` 为必要参数，不传可能返回空列表（实测暗坑）。建议 `PageSize=100`，若 `TotalCount` 超过页容量再翻页。
> 可选过滤：`--list-query ApiName=xxx GroupId=xxx PageNo=1 PageSize=100`。

### 步骤 3：为应用授权 API（字段级）

> ⚠️ **当前 OpenAPI 暂不支持（据实测）**：`grant-data-service-api` 命令存在，但授权所需的字段标识（`Columns` / 字段 ID）无法通过现有 OpenAPI 查询获取，无法构造出有效的 `GrantCommand`，实测无法完成授权。**请改用 Dataphin 控制台**：进入数据服务项目 → 应用 → API 授权，选择 API 与字段后授权。以下命令保留供 OpenAPI 支持后启用。

#### HITL 确认（写操作）

执行前确认：
- 目标应用：`{AppName}`（ID: `{AppId}`）
- 要授权的 API：`{ApiId}`
- 授权字段：`{GrantColumns}`
- 影响范围：应用获得该 API 指定字段的调用权限

**确认后执行：**

```bash
aliyun dataphin-public grant-data-service-api \
  --OpTenantId "{OpTenantId}" \
  --ProjectId "{ProjectId}" \
  --GrantCommand '{"ApiId": "{ApiId}", "AppId": "{AppId}", "Columns": ["field1", "field2"]}' \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/manage-app-and-bindauth/{SESSION_ID}"
```

完整参数结构见 [GrantDataServiceApi 参数参考](./references/grant-api-params.md)。

**响应处理：**
- 确认 `Code` 为成功
- 授权即时生效，应用可调用该 API

### 步骤 4：验证授权结果

> 说明：授权当前需在控制台完成（见步骤 3）。本步骤用于**反查已授权结果**——无论授权来自控制台还是（未来支持的）OpenAPI，均可用此命令核对。

```bash
aliyun dataphin-public list-authorized-data-service-api-details \
  --op-tenant-id "{OpTenantId}" \
  --list-query AppKeyStr={AppKeyStr} Page=1 PageSize=50 \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/manage-app-and-bindauth/{SESSION_ID}"
```

> **⚠️ 参数更正（据实测）**：本命令**不接受 `--AppId`**，而是用 `--list-query` 对象，结构 `{AppKey: integer, AppKeyStr: string, Page: integer, PageSize: integer}`。必传字符串形式的 **`AppKeyStr`**（如 `200001170-limei_test`，可从步骤 2b 的 `AppInfoList[].AppKeyStr` 或 `get-data-service-app` 取得）与分页 `Page`/`PageSize`；不传会报 `--list-query is required` 或 `appKeyStr 不能为空`。

**响应处理：**
- 已授权明细位于 `Result.Data[]`，含 `ApiId` / `ApiName` / `AppId` / `AuthType` / `AuthorizedDevReturnParameters`（已授权字段，含 `ParameterName` / `IsAuthorized`）

**验证标准：**
- 在返回列表中找到 `ApiId` 对应的记录
- 确认授权字段与 `GrantColumns` 一致
- 确认授权状态为有效

### 步骤 5：获取应用凭证

```bash
aliyun dataphin-public get-data-service-app \
  --OpTenantId "{OpTenantId}" \
  --AppId "{AppId}" \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/manage-app-and-bindauth/{SESSION_ID}"
```

**响应处理：**
- 提取 `AppKey`
- **注意**：此接口不返回 AppSecret，仅返回 AppKey
- 如需重置 AppSecret，参见下方密钥重置说明

> **S3 衔接**：将 `AppId`、`AppKey`、`AppSecret`（步骤 1 已保存）传递给 S3 `call-data-service-api` 使用。

#### 密钥重置（强 HITL 确认）

> ⚠️ **不可回滚操作**：重置后旧 AppSecret 立即失效，所有使用旧密钥的调用将被拒绝。请确保已通知所有相关方。

执行前**必须**确认：
- 目标应用：`{AppName}`（ID: `{AppId}`）
- 已通知所有使用该应用密钥的调用方
- 已做好密钥切换准备

```bash
aliyun dataphin-public reset-data-service-app-secret \
  --OpTenantId "{OpTenantId}" \
  --AppId "{AppId}" \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/manage-app-and-bindauth/{SESSION_ID}"
```

**响应处理：**
- 提取新的 `AppSecret`
- **务必保存新密钥**，旧密钥即刻失效

## 9. Success Verification

采用三步验证法：

1. **同步返回检查**：`create-data-service-app` 返回 Code 为成功，含 AppId / AppKey / AppSecret
2. **反查确认**：`list-authorized-data-service-api-details` 能查到已授权 API 且字段匹配（授权当前经控制台完成，见步骤 3）
3. **凭证获取**：`get-data-service-app` 返回有效 AppKey

```bash
# 查询应用列表确认应用存在
aliyun dataphin-public list-data-service-apps \
  --OpTenantId "{OpTenantId}" \
  --ProjectId "{ProjectId}" \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/manage-app-and-bindauth/{SESSION_ID}"
```

## 10. Cleanup

如需清理本 Skill 创建的资源：

### 回收 API 授权

> ⚠️ **当前 OpenAPI 暂不支持（据实测）**：`revoke-data-service-api` 与授权同因——无法通过 OpenAPI 获取/给出所需字段参数。**请通过 Dataphin 控制台回收授权**。以下命令保留供 OpenAPI 支持后启用。

```bash
aliyun dataphin-public revoke-data-service-api \
  --OpTenantId "{OpTenantId}" \
  --ProjectId "{ProjectId}" \
  --RevokeCommand '{"ApiId": "{ApiId}", "AppId": "{AppId}"}' \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/manage-app-and-bindauth/{SESSION_ID}"
```

### 删除应用

> 注意：当前 OpenAPI 可能不支持直接删除应用。如需清理，请通过 Dataphin 控制台操作。
> 删除前需先回收所有已授权 API。

## 11. Command Tables

| 命令 | 用途 | 类型 |
|------|------|------|
| `create-data-service-app` | 创建应用（需 AppGroupId，非 ProjectId） | 写 |
| `get-data-service-app-groups` | 查询应用分组列表（获取 AppGroupId） | 读 |
| `get-data-service-app` | 查询应用详情 | 读 |
| `list-data-service-apps` | 查询应用列表 | 读 |
| `list-data-service-published-apis` | 查询已发布 API 列表（获取待授权 ApiId） | 读 |
| `add-data-service-app-member` | 添加应用成员 | 写 |
| `grant-data-service-api` | 授权 API 给应用 | 写（⚠️ 当前 OpenAPI 暂不支持，改走控制台） |
| `revoke-data-service-api` | 回收 API 授权 | 写（⚠️ 当前 OpenAPI 暂不支持，改走控制台） |
| `list-authorized-data-service-api-details` | 查询已授权 API 详情（传 AppKeyStr + Page/PageSize） | 读 |
| `reset-data-service-app-secret` | 重置应用密钥 | 写 |

详见 [相关命令索引](./references/related-commands.md)。

## 12. Best Practices

- **应用分组 ≠ 项目（据实测）**：`create-data-service-app` 的 `create-command` 需 `AppGroupId`（应用分组 ID，先用 `get-data-service-app-groups` 查），**不是 `ProjectId`**；传错服务端不报错但应用会落到不可见分组
- **查已授权用 AppKeyStr（据实测）**：`list-authorized-data-service-api-details` 用 `--list-query AppKeyStr=.. Page=1 PageSize=50`，**不是 `--AppId`**；Page/PageSize 必传
- **大整数 ID**：AppId、ApiId、ProjectId 等 19 位 snowflake ID 必须用字符串格式传参
- **密钥安全**：AppSecret 仅在创建/重置时返回一次，务必提示用户保存；不得将密钥输出到日志
- **字段授权**：授权时明确指定 GrantColumns，避免使用 `*` 授权全部字段
- **授权/回收暂走控制台（据实测）**：`grant-data-service-api` / `revoke-data-service-api` 当前 OpenAPI 无法获取所需字段标识、无法给出有效参数，请通过 Dataphin 控制台完成 API 授权与回收；待 OpenAPI 支持后再切回命令行
- **密钥重置**：为不可回滚操作，执行前必须强 HITL 确认并通知所有调用方
- **环境 Endpoint**：
  - 管理面：`dataphin-openapi.<env>.aliyun.com`
  - 数据服务网关：`dataphin-os-gateway.<env>.aliyun.com`
