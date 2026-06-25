# RAM Permissions Reference

This document describes the RAM permissions required by the `alibabacloud-rds-postgresql-inspection` skill.

---

## Custom Policy JSON

Attach the following policy to the executing RAM identity:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBInstances",
        "rds:DescribeDBInstanceAttribute",
        "rds:DescribeDBInstancePerformance",
        "rds:DescribeSlowLogRecords"
      ],
      "Resource": "acs:rds:*:*:dbinstance/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:DescribeMetricList",
        "cms:DescribeAlertLogList"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Action Purpose Table

| Action | Purpose |
|--------|---------|
| `rds:DescribeDBInstances` | Discover RDS PostgreSQL instances across regions |
| `rds:DescribeDBInstanceAttribute` | Retrieve instance attributes (category, class, storage, zones, VPC, status, etc.) |
| `rds:DescribeDBInstancePerformance` | Collect performance metrics (CPU, memory, IOPS, connections, space, long transactions, QPS/TPS, swell time, replication delay) |
| `rds:DescribeSlowLogRecords` | Retrieve slow log records (TOP 20) |
| `cms:DescribeMetricList` | Query CloudMonitor time-series metrics for resource utilization |
| `cms:DescribeAlertLogList` | Query CloudMonitor alert history |

---

## System Policy Alternatives

If you prefer to use system policies instead of custom policies, attach the following:

| System Policy | Coverage |
|---------------|----------|
| `AliyunRDSReadOnlyAccess` | Covers all `rds:Describe*` actions |
| `AliyunCloudMonitorReadOnlyAccess` | Covers all `cms:Describe*` actions |

---

## Notes

- This skill is **read-only**. No mutating operations are performed.
- The only non-read CLI call is `das create-storage-analysis-task` (if DAS space analysis is enabled), which schedules a side analysis task and does not modify instance data.
- All API calls include the User-Agent `AlibabaCloud-Agent-Skills/alibabacloud-rds-postgresql-inspection` for audit tracking.
