# 相关命令索引（create-and-publish-api）

| 命令 | 用途 | 类型 | 必要性 |
|------|------|------|--------|
| `get-data-service-my-projects` | 查询我的数据服务项目 | 读 | 必须 |
| `get-data-service-api-groups` | 查询 API 分组 | 读 | 可选 |
| `create-data-service-api` | 创建数据服务 API | 写 | 必须 |
| `publish-data-service-api` | 发布 API 到生产 | 写 | 必须 |
| `list-data-service-published-apis` | 查询已发布 API 列表 | 读 | 必须 |
| `get-data-service-api-document` | 获取 API 文档 | 读 | 可选 |

## 参数速查

### get-data-service-my-projects
- `--OpTenantId` (必填): 租户 ID

### create-data-service-api
- `--OpTenantId` (必填): 租户 ID
- `--CreateCommand` (必填): JSON 字符串，包含 ProjectId、ApiName、Sql、DataSourceId 等

### publish-data-service-api
- `--OpTenantId` (必填): 租户 ID
- `--ApiId` (必填): API ID（字符串）
- `--ProjectId` (必填): 项目 ID（字符串）
