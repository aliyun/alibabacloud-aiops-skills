# RAM Policy - ADB MySQL Operations & Diagnosis Assistant

This file lists all RAM permissions required by the `alibabacloud-analyticdb-mysql-copilot` Skill.

## Permission List

### Cluster Management Permissions

| API Name | Permission Action | Description |
|----------|-------------|------|
| `DescribeDBClusters` | `adb:DescribeDBClusters` | Query ADB MySQL cluster list within a region |
| `DescribeDBClusterAttribute` | `adb:DescribeDBClusterAttribute` | Query cluster detailed attributes |
| `DescribeDBClusterSpaceSummary` | `adb:DescribeDBClusterSpaceSummary` | Query storage space overview |

### Instance Diagnosis Permissions

| API Name | Permission Action | Description |
|----------|-------------|------|
| `DescribeChatMessage` | `adbai:DescribeChatMessage` | Instance kernel diagnosis, including: slow SQL query diagnosis, instance diagnosis, instance write diagnosis, table modeling diagnosis |

## Minimum Permission Policy Template

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
        "adbai:DescribeChatMessage"
      ],
      "Resource": "*"
    }
  ]
}
```

## System Policy Recommendations

For quick configuration, use the following Alibaba Cloud system policies:

| Policy Name | Description |
|----------|------|
| `AliyunADBFullAccess` | ADB MySQL full access permissions (includes all read/write operations) |
| `AliyunADBReadOnlyAccess` | ADB MySQL read-only access permissions (suitable for diagnosis scenarios) |
| `AliyunADBDeveloperAccess` | ADB MySQL developer permissions (for developers, supports diagnosis scenarios) |

> **Security Recommendation**: For operations diagnosis scenarios, we recommend using the `AliyunADBReadOnlyAccess` read-only policy, which meets all diagnosis API permission requirements while avoiding the risk of accidental operations.