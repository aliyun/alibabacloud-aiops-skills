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

### 4. list-nodes 参数完整
- SHELL 脚本节点必须同时传 `--node-biz-type SCRIPT --node-sub-biz-type-list SHELL --schedule-type NORMAL`
- SQL 节点传对应子类型，如 `MAX_COMPUTE_SQL` / `HIVE_SQL` 等
- 逻辑表节点传 `--node-biz-type LOGICAL_TABLE`

### 5. node-id-list 格式正确
- 每个节点传一个 JSON 对象字符串：`--node-id-list '{"Id":"n_xxx"}'`
- 多根节点传多个参数：`--node-id-list '{"Id":"n_xxx"}' '{"Id":"n_yyy"}'`
- 逻辑表节点可加 `FieldIdList`：`--node-id-list '{"Id":"n_xxx","FieldIdList":["f_xxx"]}'`

### 6. 海量模式取真正 SupplementId
- 普通模式：`SupplementId = create-node-supplement` 返回的 `SubmitId`
- 海量模式（含 `--contain-all-down-stream true`）：`SubmitId` 是 jobId
- 海量模式必须先调用 `get-operation-submit-status --job-id <SubmitId>`，取 `ExternalBizId` 作为真正 SupplementId，再查 `get-supplement-dagrun`

### 7. contain-all-down-stream 传值
- `--contain-all-down-stream true`（或 `false`）
- 不可裸写 flag

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/project ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ `list-nodes` 缺少 `--node-sub-biz-type-list`
- ❌ `--node-id-list` 传 JSON 数组（如 `'[{"Id":"n_xxx"}]'`）
- ❌ 海量模式下直接用 `SubmitId` 当 SupplementId 查询 dagrun
- ❌ `--contain-all-down-stream` 裸写 flag 或不传 bool 值
