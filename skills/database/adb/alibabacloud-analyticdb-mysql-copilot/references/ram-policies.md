# RAM Policy - ADB MySQL 运维诊断助手

本文件列出 `alibabacloud-analyticdb-mysql-copilot` Skill 所需的所有 RAM 权限。

## 权限列表

### 集群管理权限

| API 名称 | 权限 Action | 说明 |
|----------|-------------|------|
| `DescribeDBClusters` | `adb:DescribeDBClusters` | 查询地域内 ADB MySQL 集群列表 |
| `DescribeDBClusterAttribute` | `adb:DescribeDBClusterAttribute` | 查询集群详细属性 |
| `DescribeDBClusterSpaceSummary` | `adb:DescribeDBClusterSpaceSummary` | 查询存储空间概览 |

### 性能监控权限

| API 名称 | 权限 Action | 说明 |
|----------|-------------|------|
| `DescribeDBClusterPerformance` | `adb:DescribeDBClusterPerformance` | 查询性能指标 |

### SQL 诊断权限

| API 名称 | 权限 Action | 说明 |
|----------|-------------|------|
| `DescribeDiagnosisRecords` | `adb:DescribeDiagnosisRecords` | 查询 SQL 诊断记录 |
| `DescribeBadSqlDetection` | `adb:DescribeBadSqlDetection` | 检测 BadSQL |
| `DescribeSQLPatterns` | `adb:DescribeSQLPatterns` | 查询 SQL Pattern 统计 |
| `DescribeDiagnosisSqlInfo` | `adb:DescribeDiagnosisSqlInfo` | 查询 SQL 执行详情 |

### 表诊断权限

| API 名称 | 权限 Action | 说明 |
|----------|-------------|------|
| `DescribeTableStatistics` | `adb:DescribeTableStatistics` | 查询表级统计信息 |
| `DescribeAvailableAdvices` | `adb:DescribeAvailableAdvices` | 获取优化建议 |
| `DescribeExcessivePrimaryKeys` | `adb:DescribeExcessivePrimaryKeys` | 检测主键过多的表 |
| `DescribeOversizeNonPartitionTableInfos` | `adb:DescribeOversizeNonPartitionTableInfos` | 检测超大未分区表 |
| `DescribeTablePartitionDiagnose` | `adb:DescribeTablePartitionDiagnose` | 分区表问题诊断 |
| `DescribeInclinedTables` | `adb:DescribeInclinedTables` | 检测数据倾斜表 |

## 最小权限策略模板

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "adb:DescribeDBClusters",
        "adb:DescribeDBClusterAttribute",
        "adb:DescribeDBClusterSpaceSummary",
        "adb:DescribeDBClusterPerformance",
        "adb:DescribeDiagnosisRecords",
        "adb:DescribeBadSqlDetection",
        "adb:DescribeSQLPatterns",
        "adb:DescribeDiagnosisSqlInfo",
        "adb:DescribeTableStatistics",
        "adb:DescribeAvailableAdvices",
        "adb:DescribeExcessivePrimaryKeys",
        "adb:DescribeOversizeNonPartitionTableInfos",
        "adb:DescribeTablePartitionDiagnose",
        "adb:DescribeInclinedTables"
      ],
      "Resource": "*"
    }
  ]
}
```

## 系统策略推荐

如需快速配置，可使用以下阿里云系统策略：

| 策略名称 | 说明 |
|----------|------|
| `AliyunADBFullAccess` | ADB MySQL 完全访问权限（包含所有读写操作） |
| `AliyunADBReadOnlyAccess` | ADB MySQL 只读访问权限（适合诊断场景） |

> **安全建议**：对于运维诊断场景，推荐使用 `AliyunADBReadOnlyAccess` 只读策略，满足所有诊断 API 的权限需求，同时避免误操作风险。