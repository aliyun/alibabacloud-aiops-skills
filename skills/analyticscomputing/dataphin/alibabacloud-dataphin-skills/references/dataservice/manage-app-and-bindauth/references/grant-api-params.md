# GrantDataServiceApi 完整参数参考

> ⚠️ **当前 OpenAPI 暂不支持（据实测）**：`grant-data-service-api` 命令存在，但授权所需的字段标识（`Columns` / 字段 ID）无法通过现有 OpenAPI 完整获取，无法构造出有效的 `GrantCommand`，实测无法完成授权。**请通过 Dataphin 控制台完成 API 授权**。下文参数结构保留供 OpenAPI 支持后启用。

## GrantCommand JSON 结构

```json
{
  "ApiId": "1234567890123456789",
  "AppId": "9876543210987654321",
  "Columns": ["user_id", "user_name", "dept_id"]
}
```

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ApiId | String | 是 | 要授权的 API ID（19 位 snowflake ID，字符串格式） |
| AppId | String | 是 | 目标应用 ID（19 位 snowflake ID，字符串格式） |
| Columns | Array\<String\> | 是 | 授权字段列表，指定应用可访问的 API 返回字段 |

## Columns 字段说明

`Columns` 数组指定应用可访问的 API 返回字段：

- 字段名必须与 API 返回参数定义一致
- 仅授权列出的字段，未列出的字段应用无法获取
- 建议按最小权限原则，仅授权业务必需字段

**获取可用字段列表：**

```bash
aliyun dataphin-public get-data-service-api-document \
  --OpTenantId "{OpTenantId}" \
  --ApiId "{ApiId}" \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/manage-app-and-bindauth/{SESSION_ID}"
```

从返回的 `ResponseParameters` 中提取 `ParameterName` 作为可授权字段。

## 命令完整形式

```bash
aliyun dataphin-public grant-data-service-api \
  --OpTenantId "{OpTenantId}" \
  --ProjectId "{ProjectId}" \
  --GrantCommand '{"ApiId": "{ApiId}", "AppId": "{AppId}", "Columns": ["field1", "field2"]}' \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/manage-app-and-bindauth/{SESSION_ID}"
```

## 注意事项

- ApiId 和 AppId 必须为字符串格式（19 位 snowflake ID）
- 授权即时生效，无需额外审批流程
- 同一 API 可授权给多个应用，每次授权独立管理字段范围
- 重复授权同一 API 会更新字段范围（以最新授权为准）

> **注意**：以上参数结构基于文档推断，实际使用时请通过 `aliyun dataphin-public grant-data-service-api --help` 验证最新格式。
