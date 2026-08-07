# 验收标准

## 正确模式

### 1. 产品名正确
- 使用 `dataphin-public` 而非旧 `dataphin` 二进制

### 2. 命令格式正确
- 插件模式：`aliyun dataphin-public <verb-resource> [flags]`
- 不使用传统 API 格式 `aliyun dataphin-public RunInstances`

### 3. 参数确认
- 所有用户自定义参数执行前需用户确认
- 不硬编码 tenant-id / project-id / data-source-id 等
- `--operator-type` 未提供时必须主动询问用户
- `--code` 未提供时必须主动询问用户
- DATABASE_SQL 类 `--data-source-id` 和 `--data-source-schema` 未提供时必须主动询问

### 4. OperatorType 使用字符串枚举
- MaxCompute SQL：`MaxCompute_SQL`
- 关系型数据库（MySQL/Oracle/PostgreSQL/SQLServer）：`DATABASE_SQL`

### 5. 必填参数完整
- DATABASE_SQL：必须同时传 `--data-source-id` + `--data-source-schema`
- MaxCompute_SQL：仅需 `--project-id`

### 6. 结果获取正确
- `--sub-task-id` 从 0 开始
- 先查日志确认 `TaskStatus: SUCCESS` 再取结果
- 结果为空时等待 3-10 秒重试

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/project/data-source ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ 使用 `--script` 而不是 `--code`
- ❌ DATABASE_SQL 只传 `--data-source-id` 不传 `--data-source-schema`
- ❌ 用数值枚举代替字符串 OperatorType
- ❌ `--sub-task-id` 从 1 开始
# 验收标准

## 正确模式

### 1. 产品名正确
- 使用 `dataphin-public` 而非旧 `dataphin` 二进制

### 2. 命令格式正确
- 插件模式：`aliyun dataphin-public <verb-resource> [flags]`
- 不使用传统 API 格式 `aliyun dataphin-public RunInstances`

### 3. 参数确认
- 所有用户自定义参数执行前需用户确认
- 不硬编码 tenant-id / project-id / 资源名等

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/project ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
