# 验证方法

本文档描述各 API 调用的成功标志和常见错误处理。

## 成功标志

### 集群管理
- `DescribeDBClusters`：返回 `TotalCount` 字段，`Items` 数组包含集群列表
- `DescribeDBClusterAttribute`：返回 `Items` 数组，`Items[0].DBClusterId` 与传入一致
- `DescribeDBClusterSpaceSummary`：返回 `TotalSize`、`HotData`、`ColdData` 等字段

### 性能监控
- `DescribeDBClusterPerformance`：返回 `PerformanceItems` 数组，包含 `MetricName`、`Points` 字段

### SQL 诊断
- `DescribeBadSqlDetection`：返回 `Items` 数组，`TotalCount > 0` 表示检测到 BadSQL
- `DescribeSQLPatterns`：返回 `Items` 数组，包含 `PatternId`、`SQLPattern`、`QueryCount` 等字段
- `DescribeDiagnosisRecords`：返回 `Items` 数组，包含 `ProcessId`、`SQL`、`Status` 等字段

### 表诊断
- `DescribeAvailableAdvices`：返回 `TotalCount` 和 `Items`，包含 `SchemaName`、`TableName` 等字段
- `DescribeInclinedTables`：返回 `TotalCount`，`TotalCount > 0` 表示存在倾斜表
- `DescribeExcessivePrimaryKeys` / `DescribeOversizeNonPartitionTableInfos` / `DescribeTablePartitionDiagnose`：返回有效 JSON 数据

## 常见错误码

| 错误码 | 含义 | 解决方案 |
|--------|------|----------|
| `InvalidDBClusterId.NotFound` | 集群 ID 不存在 | 调用 `DescribeDBClusters` 获取正确集群 ID |
| `InvalidAdviceDate` | 日期格式错误 | 使用 `yyyyMMdd` 格式（如 `20260322`），且建议 T-1 或更早 |
| `Forbidden.RAM` | 权限不足 | 使用 `ram-permission-diagnose` skill 引导用户申请权限 |
| `InvalidAccessKeyId.NotFound` | AK 不存在 | 运行 `aliyun configure list` 检查凭证状态 |
| `SignatureDoesNotMatch` | AK Secret 错误 | 在本会话外重新配置凭证 |
| `InvalidSecurityToken.Expired` | STS Token 过期 | 重新获取临时凭证 |

## 集群 ID 验证规则

若用户给出的集群 ID 在 API 返回中不存在（错误码 `InvalidDBClusterId.NotFound`），不得中止任务，应：
1. 调用 `DescribeDBClusters` 列出该地域实际存在的集群
2. 引导用户确认正确的集群 ID 后继续执行