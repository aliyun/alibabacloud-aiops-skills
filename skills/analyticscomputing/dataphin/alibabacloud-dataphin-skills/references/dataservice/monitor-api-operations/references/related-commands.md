# 相关命令索引（monitor-api-operations）

| 命令 | 用途 | 类型 | 必要性 |
|------|------|------|--------|
| `get-data-service-api-call-summary` | 查看 API 调用汇总 | 读 | 必须 |
| `get-data-service-api-call-trend` | 分析调用趋势 | 读 | 必须 |
| `list-data-service-api-calls` | 查看调用日志明细 | 读 | 必须 |
| `list-data-service-api-call-statistics` | 调用统计列表 | 读 | 可选 |
| `get-data-service-api-error-impact` | 异常影响汇总 | 读 | 可选 |
| `list-data-service-api-impacts` | 异常调用明细 | 读 | 可选 |

## 参数速查

### get-data-service-api-call-summary
- `--OpTenantId` (必填): 租户 ID
- `--ProjectId` (必填): 项目 ID（字符串）

### get-data-service-api-call-trend
- `--OpTenantId` (必填): 租户 ID
- `--ProjectId` (必填): 项目 ID（字符串）
- `--ApiId` (必填): API ID（字符串）
- `--StartTime` (必填): 查询开始时间
- `--EndTime` (必填): 查询结束时间

### list-data-service-api-calls
- `--OpTenantId` (必填): 租户 ID
- `--ProjectId` (必填): 项目 ID（字符串）
- `--ApiId` (可选): API ID（字符串）；用于按单个 API 过滤，不传则返回项目下全部
- `--StartTime` (必填): 查询开始时间
- `--EndTime` (必填): 查询结束时间
- `--PageNo` (可选): 分页页码（list-* 命令用 PageNo，非 PageNum），默认 1
- `--PageSize` (可选): 每页条数，默认 20

### get-data-service-api-error-impact
- `--OpTenantId` (必填): 租户 ID
- `--ProjectId` (必填): 项目 ID（字符串）
- `--ApiId` (必填): API ID（字符串）
- `--StartTime` (必填): 查询开始时间
- `--EndTime` (必填): 查询结束时间

### list-data-service-api-impacts
- `--OpTenantId` (必填): 租户 ID
- `--ProjectId` (必填): 项目 ID（字符串）
- `--ApiId` (必填): API ID（字符串）
- `--StartTime` (必填): 查询开始时间
- `--EndTime` (必填): 查询结束时间
