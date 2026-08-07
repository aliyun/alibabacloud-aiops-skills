# 验收标准

## 本 skill 验收项

- [ ] `get-pipeline-by-id` 能按 `--pipeline-id` / `--file-id` / `--node-id` 三种方式定位任务并回读完整配置
- [ ] 修改前已将回读配置落盘为回滚基线（`current-*.json`）
- [ ] 执行前 HITL 确认信息包含变更 diff（哪些字段改、哪些原样回传）
- [ ] `update-pipeline` 全量回写返回 `Code: OK` / `Success: true`
- [ ] 回写后 `get-pipeline-by-id` 反查：目标字段已变更，未改字段未丢失
- [ ] 仅保存草稿场景使用 `--submit false` 且未进入调度

## 正确模式

### 1. 产品名正确
- 使用 `dataphin-public` 而非旧 `dataphin` 二进制

### 2. 命令格式正确
- 插件模式：`aliyun dataphin-public <verb-resource> [flags]`
- 不使用传统 API 格式 `aliyun dataphin-public RunInstances`

### 3. 参数确认
- 所有用户自定义参数执行前需用户确认
- 不硬编码 tenant-id / project-id / 资源名等

### 4. 全量回写纪律
- 修改前必须 `get-pipeline-by-id` 回读
- `--pipeline-config` / `--schedule-config` 未改动也完整回传

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/project ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ 跳过回读直接凭记忆拼 `--pipeline-config` 回写（导致配置丢失）
- ❌ 未经用户确认直接提交写操作
