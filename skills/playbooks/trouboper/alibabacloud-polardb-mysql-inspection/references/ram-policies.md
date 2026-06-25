# RAM Permissions: alibabacloud-polardb-mysql-inspection

This skill uses read-only APIs only. No write permissions are required.

## Minimum Permission Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "polardb:DescribeDBClusters",
        "polardb:DescribeDBClusterAttribute",
        "polardb:DescribeDBClusterVersion",
        "polardb:DescribeDBClusterPerformance",
        "polardb:DescribeDBNodePerformance",
        "polardb:DescribeDBProxyPerformance",
        "polardb:DescribeDBNodes",
        "polardb:DescribeDBClusterParameters",
        "polardb:DescribeDasConfig",
        "polardb:DescribeSlowLogs",
        "polardb:DescribeSlowLogRecords"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "das:CreateStorageAnalysisTask",
        "das:GetStorageAnalysisResult",
        "das:GetAutoIncrementUsageStatistic",
        "das:GetMySQLAllSessionAsync"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:DescribeAlertLogList",
        "cms:DescribeMetricRuleList"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Descriptions

| Permission | Purpose |
|------------|---------|
| `polardb:DescribeDBClusters` | List PolarDB clusters (for auto-discovering instance Region) |
| `polardb:DescribeDBClusterAttribute` | Query cluster basic info (version, spec, max connections, etc.) |
| `polardb:DescribeDBClusterVersion` | Query kernel version info (minor version, latest available, Proxy version) |
| `polardb:DescribeDBClusterPerformance` | Query cluster-level performance metrics (CPU, memory, IOPS, connections) |
| `polardb:DescribeDBNodePerformance` | Query node-level performance metrics |
| `polardb:DescribeDBProxyPerformance` | Query Proxy performance metrics (CPU, session routing) |
| `polardb:DescribeDBNodes` | Query cluster node information |
| `polardb:DescribeDBClusterParameters` | Query cluster parameter configuration |
| `polardb:DescribeDasConfig` | Query DAS service configuration status |
| `polardb:DescribeSlowLogs` | Query slow log statistics |
| `polardb:DescribeSlowLogRecords` | Query slow log detail records |
| `das:CreateStorageAnalysisTask` | Create storage analysis task |
| `das:GetStorageAnalysisResult` | Get storage analysis results (table space Top 20) |
| `das:GetAutoIncrementUsageStatistic` | Get auto-increment primary key usage statistics |
| `das:GetMySQLAllSessionAsync` | Async retrieval of current session information |
| `cms:DescribeAlertLogList` | Query CloudMonitor alert history records |
| `cms:DescribeMetricRuleList` | Query CloudMonitor alert rule configuration |
