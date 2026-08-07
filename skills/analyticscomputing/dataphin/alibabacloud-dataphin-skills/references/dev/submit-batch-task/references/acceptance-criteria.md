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

### 4. 多时点 cron 用 `|` 分隔
- 分钟相同：`--cron-expression "0 45 8,20 * * ?"`（08:45、20:45）
- 分钟不同：`--cron-expression "0 23 1 * * ?|0 33 19 * * ?"`（01:23、19:33），用 `|` 分隔多条 cron，`CustomScheduleConfig` 留空
- ❌ 笛卡尔积 `"0 23,33 1,19 * * ?"` 会产生 4 个时点

### 5. submit 后必须 publish 才上线
- `submit-batch-task` 返回 `NodeId`/`SubmitId` 后节点未进运维区，必须再 `publish-object-list --submit-id-list <SubmitId>` 发布
- 完整链路：`create-batch-task`(--env DEV) → `submit-batch-task` → `publish-object-list`

### 6. 上游 SourceNodeId 用 output name（任务名）
- 根节点上游：`SourceNodeId=virtual_root_node_xxx`、`SourceNodeOutputName=virtual_root_node_xxx`
- 真实任务节点上游：`SourceNodeId=<上游任务名>`（=其 output name），如 `shell_a`；**不用物理 `n_xxx` NodeId**
- `--up-stream-list` 传单对象：`'{"NodeType":"PHYSICAL","SourceNodeId":"shell_a","SourceNodeOutputName":"shell_a","PeriodDiff":0}'`

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/project ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ `--up-stream-list` 传 `"[{...}]"`（带外层数组）→ 报 `Expected BEGIN_OBJECT but was BEGIN_ARRAY`；应传单对象 `"{\"NodeType\":...}"`
- ❌ 多时点用笛卡尔积 cron `0 23,33 1,19 * * ?`
- ❌ `submit-batch-task` 成功后不 `publish`，直接 `get-physical-node` → 报 `DPN.OP.NodeNotExist`
- ❌ `SourceNodeId` 传物理 `n_xxx` NodeId → 报 `DPN.DataProcess.NodeUpstreamNotExist`；应传上游 output name（任务名）
