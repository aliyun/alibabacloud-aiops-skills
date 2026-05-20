# RAM Permission Description

This Skill calls Alibaba Cloud ADB Spark and related services' OpenAPIs via `aliyun` CLI to perform read-only diagnostic and analysis operations. The following lists the minimum RAM permission set required.

## Required Permission List

### ADB Cluster Query

| Action | Description | Operation Type |
|--------|------|---------|
| `adb:DescribeDBClusters` | List ADB clusters in a region to discover DBClusterId | Read-only |

### ADB Spark Apps

| Action | Description | Operation Type |
|--------|------|---------|
| `adb:ListSparkApps` | Query ADB Spark application list | Read-only |
| `adb:GetSparkAppInfo` | Get meta information of a spark application | Read-only |
| `adb:GetSparkAppLog` | Get tail logs of a Spark application | Read-only |



### Spark Log From OSS

| Action | Description | Operation Type |
|--------|------|---------|
| `oss:GetObject` | Read files from OSS bucket | Read-only |
| `oss:GetBucket` | Read-only access to OSS bucket | Read-only |
| `oss:ListObjects` | List files in OSS bucket | Read-only |


## RAM Policy Example

Below is a RAM custom policy (JSON format) granting all above permissions, can be created in RAM console:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "adb:DescribeDBClusters",
        "adb:ListSparkApps",
        "adb:GetSparkAppInfo",
        "adb:GetSparkAppLog"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetObject",
        "oss:GetBucket",
        "oss:ListObjects"
      ],
      "Resource": "*"
    }
  ]
}
```

## Least Privilege Principle Recommendations

To minimize permission exposure, narrow the OSS `Resource` field to the specific Bucket where Spark logs are stored (e.g. `acs:oss:*:*:<your-bucket-name>` and `acs:oss:*:*:<your-bucket-name>/*`) instead of using the `*` wildcard. This ensures read access is granted only to the required log storage location.

## Troubleshooting Insufficient Permissions

When encountering `Forbidden.RAM` error:

1. Check specific missing Action name in error Message
2. Add corresponding permission for current user/role in RAM console
3. If using STS Token, confirm STS policy also contains required Actions (STS permissions = RAM permissions ∩ STS policy permissions)
4. Re-execute operation to verify permissions take effect