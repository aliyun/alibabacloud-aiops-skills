# 相关命令索引（manage-app-and-bindauth）

| 命令 | 用途 | 类型 | 必要性 |
|------|------|------|--------|
| `create-data-service-app` | 创建数据服务应用（需 AppGroupId，非 ProjectId） | 写 | 必须 |
| `get-data-service-app-groups` | 查询应用分组列表（获取 AppGroupId） | 读 | 创建前必须 |
| `get-data-service-app` | 查询应用详情 | 读 | 必须 |
| `list-data-service-apps` | 查询应用列表 | 读 | 可选 |
| `list-data-service-published-apis` | 查询已发布 API 列表（获取待授权 ApiId） | 读 | 可选 |
| `add-data-service-app-member` | 添加应用成员 | 写 | 可选 |
| `grant-data-service-api` | 授权 API 给应用 | 写 | ⚠️ 当前 OpenAPI 暂不支持，改走控制台 |
| `revoke-data-service-api` | 回收 API 授权 | 写 | ⚠️ 当前 OpenAPI 暂不支持，改走控制台 |
| `list-authorized-data-service-api-details` | 查询已授权 API 详情 | 读 | 必须 |
| `reset-data-service-app-secret` | 重置应用密钥 | 写 | 可选 |

## 参数速查

### create-data-service-app
- `--op-tenant-id` (必填): 租户 ID
- `--create-command` (必填): JSON 字符串，结构 `{AppGroupId: integer, AppName: string, AppKey?: string, AppSecret?: string, OwnerIds?: [string], Scenarios?: string}`
  - **⚠️ 用 `AppGroupId`（应用分组 ID，先用 `get-data-service-app-groups` 查），不是 `ProjectId`**；无 `AppDescription` 字段；AppGroupId 为整数不加引号

### get-data-service-app-groups
- `--op-tenant-id` (必填): 租户 ID
- `--project-id` (已废弃): 可不传
  - 响应：分组列表，每项含 `Id`（即 AppGroupId）/ `Name`

### add-data-service-app-member
- `--OpTenantId` (必填): 租户 ID
- `--AddCommand` (必填): JSON 字符串，包含 AppId、UserId

### list-data-service-published-apis
- `--op-tenant-id` (必填): 租户 ID
- `--project-id` (必填): 数据服务项目 ID
- `--list-query` (分页必传): `PageNo` 与 `PageSize` 为必要参数，不传可能返回空列表；可选过滤 `ApiName` / `GroupId`。格式：`--list-query ApiName=xxx GroupId=xxx PageNo=1 PageSize=100`
  - 响应：`PageResult.ApiList[]`（含 `ApiId` / `ApiName` / `GroupName` / `AppCount` / `AppInfoList`）、`PageResult.TotalCount`

### grant-data-service-api
> ⚠️ **当前 OpenAPI 暂不支持（据实测）**：命令存在，但授权所需的字段标识无法通过 OpenAPI 获取，无法构造有效 `GrantCommand`，请改用 Dataphin 控制台授权。以下参数保留供支持后启用。
- `--OpTenantId` (必填): 租户 ID
- `--ProjectId` (必填): 项目 ID（字符串）
- `--GrantCommand` (必填): JSON 字符串，包含 ApiId、AppId、Columns
  - 详见 [grant-api-params.md](./grant-api-params.md)

### list-authorized-data-service-api-details
- `--op-tenant-id` (必填): 租户 ID
- `--list-query` (必填): 对象，结构 `{AppKey: integer, AppKeyStr: string, Page: integer, PageSize: integer}`。格式：`--list-query AppKeyStr=xxx Page=1 PageSize=50`
  - **⚠️ 不是 `--AppId`**；必传字符串形式 `AppKeyStr` + 分页 `Page`/`PageSize`，否则报 `--list-query is required` 或 `appKeyStr 不能为空`
  - 响应：`Result.Data[]`（含 `ApiId` / `ApiName` / `AppId` / `AuthType` / `AuthorizedDevReturnParameters`）

### get-data-service-app
- `--OpTenantId` (必填): 租户 ID
- `--AppId` (必填): 应用 ID（字符串）

### reset-data-service-app-secret
- `--OpTenantId` (必填): 租户 ID
- `--AppId` (必填): 应用 ID（字符串）

### revoke-data-service-api
> ⚠️ **当前 OpenAPI 暂不支持（据实测）**：与授权同因，请改用 Dataphin 控制台回收授权。以下参数保留供支持后启用。
- `--OpTenantId` (必填): 租户 ID
- `--ProjectId` (必填): 项目 ID（字符串）
- `--RevokeCommand` (必填): JSON 字符串，包含 ApiId、AppId
