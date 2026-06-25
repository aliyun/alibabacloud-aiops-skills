# RAM Permissions: alibabacloud-mongodb-health-inspect

This skill uses read-only APIs only. No write permissions are required.

## Minimum Permission Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dds:DescribeDBInstances",
        "dds:DescribeDBInstanceAttribute",
        "dds:DescribeDBInstancePerformance",
        "dds:DescribeSlowLogRecords"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "das:CreateStorageAnalysisTask",
        "das:GetStorageAnalysisResult",
        "das:GetMongoDBCurrentOp"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:DescribeAlertHistoryList",
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
| `dds:DescribeDBInstances` | List DDS instances (for `--all` auto-discovery) |
| `dds:DescribeDBInstanceAttribute` | Query instance basic info (architecture, version, node list, specs) |
| `dds:DescribeDBInstancePerformance` | Query performance monitoring data (CPU/memory/IOPS/connections/network/Opcounters) |
| `dds:DescribeSlowLogRecords` | Query slow log detail records |
| `das:CreateStorageAnalysisTask` | Create storage analysis task for collection space analysis |
| `das:GetStorageAnalysisResult` | Get storage analysis results (collection space Top 20) |
| `das:GetMongoDBCurrentOp` | Get per-node current session snapshots |
| `cms:DescribeAlertHistoryList` | Query CloudMonitor alert history events |
| `cms:DescribeMetricRuleList` | Query CloudMonitor alert rule configuration |
