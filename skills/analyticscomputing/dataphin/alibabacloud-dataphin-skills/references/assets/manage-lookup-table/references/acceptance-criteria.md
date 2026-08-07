# 验收标准

## 正确模式

### 1. 产品名与命令格式正确
- 使用 `dataphin-public` 而非旧 `dataphin` 二进制
- 插件模式：`aliyun dataphin-public <verb-resource> [flags]`（kebab-case）
- 不使用传统 API 格式 `aliyun dataphin-public CreateStandardLookupTable`

### 2. 参数确认与 HITL
- 所有用户自定义参数执行前需用户确认
- 写操作（create / update / delete）执行前必须 HITL 二次确认
- 不硬编码 tenant-id / 码表 ID / 目录路径等
- 19 位大整数 ID 一律字符串传参（引号包住）

### 3. 必填参数与码值规范
- `create` 必带 `--standard-lookup-table-name` + `--code`
- `update` 必带 `--id` + `--standard-lookup-table-name` + `--code`
- 码值元素 `Value`/`Name` 必填且 ≤64 字符，`Value` 码表内唯一
- update 前先 `get` 备份全量码值（覆盖语义防丢失）

### 4. 端到端校验
- 同步响应 `Code: OK`，create 返回码表 Id
- `get-standard-lookup-table --nullable false` 反查名称/编码/码值数一致

### 5. Observability
- 所有调用 API 的 `aliyun` 命令携带 `--user-agent AlibabaCloud-Agent-Skills/manage-lookup-table/{session-id}`
- session-id 继承父 skill，不重新生成

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/码表 ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ update 未先 get 备份就整体覆盖码值列表
- ❌ delete-standard-lookup-table 未经确认直接执行（不可回滚）
- ❌ 虚构 `list-standard-lookup-tables` 之类不存在的命令
