# 验收标准

## 正确模式

### 1. 产品名与命令格式正确
- 使用 `dataphin-public` 而非旧 `dataphin` 二进制
- 插件模式：`aliyun dataphin-public <verb-resource> [flags]`（kebab-case）
- 不使用传统 API 格式 `aliyun dataphin-public CreateStandardMapping`

### 2. 参数确认与 HITL
- 所有用户自定义参数执行前需用户确认
- 写操作（create / update-to-invalid / delete）执行前必须 HITL 二次确认
- 无效映射冲突策略（SET_INVALID_TO_VALID / KEEP_INVALID_AND_SKIP）必须显式与用户确认，不可静默用默认值
- 不硬编码 tenant-id / standard-id / 资产 GUID
- 19 位大整数 ID 一律字符串传参（引号包住）

### 3. 必填参数完整
- `get-asset-mapping-relations` 必带 `--asset-type`（COLUMN/INDEX）+ `--relation-type`（VALID/INVALID）
- `create-standard-mapping` 必带 `--standard-id` + `--asset-guid-list`
- update/delete 至少提供 `--guid-list` 或 `--belong-guid-list` 之一，单次 ≤1000

### 4. 端到端校验
- `create` 响应 `Data.SuccessCount` 与入参 GUID 数一致、`FailedGuidList` 为空；不为空须逐个报告失败原因
- `get-asset-mapping-relations` / `get-belong-asset-mapping` 反查命中目标标准

### 5. Observability
- 所有调用 API 的 `aliyun` 命令携带 `--user-agent AlibabaCloud-Agent-Skills/manage-standard-mapping/{session-id}`
- session-id 继承父 skill，不重新生成

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/standard/GUID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ 对未发布（非已生效）标准直接建有效映射
- ❌ 未确认冲突策略就用默认 SET_INVALID_TO_VALID 覆盖既有排除决策
- ❌ 虚构「按标准 ID 分页列映射」的 list 命令
