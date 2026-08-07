# 验收标准

## 正确模式

### 1. 产品名与命令格式正确
- 使用 `dataphin-public` 而非旧 `dataphin` 二进制
- 插件模式：`aliyun dataphin-public <verb-resource> [flags]`（kebab-case）
- 不使用传统 API 格式 `aliyun dataphin-public GetStandard`
- 查询列表用复数命令 `list-standards`，非 `list-standard`

### 2. 参数确认与 HITL
- 所有用户自定义参数执行前需用户确认
- 写操作（create / update / publish / offline / delete）执行前必须 HITL 二次确认
- 不硬编码 tenant-id / standard-id / 标准集 ID 等
- 19 位大整数 ID 一律字符串传参（引号包住）

### 3. 必填参数完整
- `list-standards` 必带 `--standard-stage`（DEV/PROD）
- `update-standard` 必带 `--standard-id` + `--standard-status`
- `publish-standard` / `offline-standard` 必带 `--comment`

### 4. 端到端校验三步法
- 同步响应 `Code: OK` / 返回 StandardId
- `list-standards` / `get-standard` 反查命中
- 发布后 PROD 阶段状态为 `ACTIVE` 表示生效

### 5. Observability
- 所有调用 API 的 `aliyun` 命令携带 `--user-agent AlibabaCloud-Agent-Skills/manage-data-standard/{session-id}`
- session-id 继承父 skill，不重新生成

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/standard ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ `list-standards` 漏传 `--standard-stage`
- ❌ delete-standard 未经确认直接执行（不可回滚）
