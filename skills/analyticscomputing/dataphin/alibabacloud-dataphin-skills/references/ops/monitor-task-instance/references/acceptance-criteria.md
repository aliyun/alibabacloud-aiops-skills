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

### 4. bizdate 使用 T-1
- 查询今日实例使用 `--min-biz-date $(date -v-1d +%Y%m%d) --max-biz-date $(date -v-1d +%Y%m%d)`
- 不直接用今天日期作为 bizdate

### 5. 返回字段路径正确
- 节点名：`.PageResult.Data[].NodeInfo.Name`
- 实例 ID：`.PageResult.Data[].Id`
- 状态：`.PageResult.Data[].StatusList`

### 6. WAIT_SCHEDULE 诊断顺序
- 先检查 `DueTime` 是否已到
- 再检查 `SchedulePaused` / `BlockType` / `WaitReason`
- `DueTime` 未到且无阻塞信息 → 正常等待

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/project/instance ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ 用今天日期直接作为 `bizdate`
- ❌ 看到 `WAIT_SCHEDULE` 不检查 `DueTime` 直接判定异常
- ❌ `list-instances` 不传 `--page` / `--page-size`
