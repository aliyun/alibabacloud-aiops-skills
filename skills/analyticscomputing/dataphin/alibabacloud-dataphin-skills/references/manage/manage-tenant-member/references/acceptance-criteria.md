# 验收标准

## 正确模式

### 1. 产品名正确
- 使用 `dataphin-public` 而非旧 `dataphin` 二进制

### 2. 命令格式正确
- 插件模式：`aliyun dataphin-public <verb-resource> [flags]`
- 不使用传统 API 格式 `aliyun dataphin-public RunInstances`

### 3. 参数确认
- 所有用户自定义参数执行前需用户确认
- 不硬编码 tenant-id / user-id / 资源名等

### 4. user-list 格式正确
- 每个用户传一个 JSON 对象字符串：`--user-list '{"Id":"xxx"}'`
- 多用户传多个参数：`--user-list '{"Id":"xxx"}' '{"Id":"yyy"}'`
- **不能传 JSON 数组** `'[{"Id":"xxx"}]'`

### 5. update / remove 参数名正确
- 更新角色用 `--member-list '{"UserId":"xxx","RoleList":[...]}'`，**不是** `--user-id` / `--role-list`
- 移除成员用 `--source-id '<user-id>'`，**不是** `--user-id`

### 6. 分页参数完整
- `list-addable-users` / `list-tenant-members` 必须同时传 `--page` 和 `--page-size`

### 7. 独立部署连接正确
- 使用带正确 `--endpoint` 的 profile，避免打到公共云报 `InvalidAccessKeyId.NotFound`
- 自签证书环境用 `DATAPHIN_INSECURE=true`（或 `--insecure` 放命令末尾）

### 8. 权限确认
- 操作前确认调用者具备 SuperAdmin 或系统管理员角色
- 权限不足时停止并引导用户通过 `ram-permission-diagnose` 申请

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/user ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ `--user-list` 传 JSON 数组
- ❌ update/remove 误用 `--user-id` / `--role-list`（应为 `--member-list` / `--source-id`）
- ❌ `list-addable-users` / `list-tenant-members` 缺少分页参数
- ❌ 静默添加/移除/更新租户成员
