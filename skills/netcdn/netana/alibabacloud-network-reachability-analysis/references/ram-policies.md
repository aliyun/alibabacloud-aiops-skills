# RAM Policies

## Required Permissions

The following RAM policy grants the minimum permissions needed for NIS reachability analysis and CloudMonitor metric queries.

### NIS Permissions

| Action | Description |
|--------|-------------|
| `nis:CreateAndAnalyzeNetworkPath` | Initiate network reachability analysis tasks |
| `nis:GetNetworkReachableAnalysis` | Query analysis task results |

### CloudMonitor Permissions

| Action | Description |
|--------|-------------|
| `cms:DescribeMetricData` | Query monitoring metrics for resources on the path |

### Recommended RAM Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "nis:CreateAndAnalyzeNetworkPath",
        "nis:GetNetworkReachableAnalysis"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:DescribeMetricData"
      ],
      "Resource": "*"
    }
  ]
}
```

### Notes

- NIS reachability analysis is read-only and does not modify any network resources.
- `DescribeMetricData` shares a monthly free quota of 1,000,000 calls with other CloudMonitor query APIs.
- Per-account rate limit for `DescribeMetricData`: 10 calls/second.
