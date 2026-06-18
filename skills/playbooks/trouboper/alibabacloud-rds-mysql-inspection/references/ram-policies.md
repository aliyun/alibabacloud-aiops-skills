# RAM Permissions

This skill uses **read-only** APIs only. The single DAS `CreateStorageAnalysisTask` call creates a side analysis task and does **not** mutate any instance state; it is whitelisted by the `PreToolUse` hook.

---

## Minimum Custom Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:DescribeRegions",
        "rds:DescribeDBInstances",
        "rds:DescribeDBInstanceAttribute"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:DescribeMetricList",
        "cms:DescribeAlertLogList"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "das:DescribeSlowLogStatistic",
        "das:CreateStorageAnalysisTask",
        "das:GetStorageAnalysisResult"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Permission Purpose

| Action                              | Service | Purpose                                                                                  |
| ----------------------------------- | ------- | ---------------------------------------------------------------------------------------- |
| `rds:DescribeRegions`               | RDS     | List available regions.                                                                  |
| `rds:DescribeDBInstances`           | RDS     | List RDS MySQL instances per region.                                                     |
| `rds:DescribeDBInstanceAttribute`   | RDS     | Retrieve detailed instance attributes (Category, node list, kernel version, etc.).      |
| `cms:DescribeMetricList`            | CMS     | Pull time-series data for the five core metrics (CPU / memory / disk / IOPS / connections). |
| `cms:DescribeAlertLogList`          | CMS     | Pull alert history.                                                                      |
| `das:DescribeSlowLogStatistic`      | DAS     | Pull slow log statistics.                                                                |
| `das:CreateStorageAnalysisTask`     | DAS     | Trigger a space analysis task (side task; does not modify instance state).               |
| `das:GetStorageAnalysisResult`      | DAS     | Retrieve space analysis results.                                                         |

---

## System Policy Alternatives (broader scope, easier to attach)

If you prefer to attach AliCloud system policies instead of a custom policy:

- `AliyunRDSReadOnlyAccess` — covers `rds:Describe*`.
- `AliyunCloudMonitorReadOnlyAccess` — covers `cms:Describe*`.
- DAS does **not** have an official read-only system policy that covers the `CreateStorageAnalysisTask` write action. Use the custom policy block above for DAS, or attach `AliyunDASFullAccess` (broader than needed).

---

## Notes

- All actions are scoped at `Resource: "*"`. Narrow this with instance-ARN constraints when applying in production.
- The skill never reads, prints, or persists `AccessKeyId` / `AccessKeySecret`. Credentials must be configured via `aliyun configure` outside the conversation.
- A `PreToolUse` hook (`scripts/check-write-operation.sh`) intercepts any aliyun CLI invocation whose Action prefix matches a write verb (`Create*`, `Delete*`, `Modify*`, `Update*`, etc.) and requires user confirmation. `CreateStorageAnalysisTask` is explicitly whitelisted.
