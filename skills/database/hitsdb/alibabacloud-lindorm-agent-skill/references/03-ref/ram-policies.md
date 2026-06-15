# RAM Permission Policy List

All APIs involved in this Skill and their corresponding RAM permission requirements.

> **Policy name description**: The official Lindorm system policies are `AliyunLindormReadOnlyAccess` for read-only access, `AliyunLindormFullAccess` for full access, and `AliyunLindormDevelopAccess` for developer access.

## Lindorm API Permissions

| API Action | Permission Policy | Description |
|------------|---------|------|
| `DescribeRegions` | `AliyunLindormReadOnlyAccess` | Query region list |
| `GetLindormInstanceList` | `AliyunLindormReadOnlyAccess` | Query instance list |
| `GetLindormInstance` | `AliyunLindormReadOnlyAccess` | Query instance details |
| `GetLindormV2InstanceDetails` | `AliyunLindormReadOnlyAccess` | Query V2 instance details |
| `GetLindormInstanceEngineList` | `AliyunLindormReadOnlyAccess` | Query instance engine list |
| `GetLindormFsUsedDetail` | `AliyunLindormReadOnlyAccess` | Query storage details, V1 |
| `GetLindormV2StorageUsage` | `AliyunLindormReadOnlyAccess` | Query storage details, V2 |
| `GetInstanceIpWhiteList` | `AliyunLindormReadOnlyAccess` | Query IP whitelist |

## CloudMonitor API Permissions

| API Action | Permission Policy | Description |
|------------|---------|------|
| `DescribeMetricMetaList` | `AliyunCloudMonitorReadOnlyAccess` | Query monitoring metric list |
| `DescribeMetricLast` | `AliyunCloudMonitorReadOnlyAccess` | Query latest monitoring data |
| `DescribeMetricData` | `AliyunCloudMonitorReadOnlyAccess` | Query historical monitoring data |

## System Permission Policies

### Read-Only Permissions, Recommended

> This Skill is used for read-only operation scenarios and requires only the following permissions.

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "hitsdb:DescribeRegions",
        "hitsdb:GetLindormInstanceList",
        "hitsdb:GetLindormInstance",
        "hitsdb:GetLindormV2InstanceDetails",
        "hitsdb:GetLindormInstanceEngineList",
        "hitsdb:GetLindormFsUsedDetail",
        "hitsdb:GetLindormV2StorageUsage",
        "hitsdb:GetInstanceIpWhiteList"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:DescribeMetricMetaList",
        "cms:DescribeMetricLast",
        "cms:DescribeMetricData"
      ],
      "Resource": "*"
    }
  ],
  "Version": "1"
}
```

> ℹ️ **About write operation permissions**: This Skill does not execute any write operations. If the user truly needs write operations such as creating, modifying, or deleting instances, grant the official system policy `AliyunLindormFullAccess` directly.

## Permission Configuration Steps

### Configure Through the RAM Console

1. Log on to the [RAM Console](https://ram.console.aliyun.com/).
2. Create a RAM user or use an existing user.
3. On the user details page, click "Add Permissions".
4. Select permission policies:
   - Read-only: `AliyunLindormReadOnlyAccess` + `AliyunCloudMonitorReadOnlyAccess`
   - Full access: `AliyunLindormFullAccess`
5. Confirm authorization.

### Configure Through CLI

```bash
# Create a RAM user.
aliyun ram create-user --user-name lindorm-operator

# Add read-only permissions.
aliyun ram attach-policy-to-user \
  --user-name lindorm-operator \
  --policy-name AliyunLindormReadOnlyAccess \
  --policy-type System

aliyun ram attach-policy-to-user \
  --user-name lindorm-operator \
  --policy-name AliyunCloudMonitorReadOnlyAccess \
  --policy-type System
```

## Permission Verification

Run the following commands to verify whether permissions are configured correctly:

```bash
# Test Lindorm permissions.
aliyun hitsdb get-lindorm-instance-list --region cn-shanghai

# Test CloudMonitor permissions.
aliyun cms describe-metric-meta-list --namespace acs_lindorm
```

If the `Forbidden.RAM` error is returned, permissions are insufficient and must be added by following the preceding steps.

## Handling Flow for Insufficient Permissions

1. Check current user permissions: View the user authorization policies in the RAM Console.
2. Confirm required permissions: Refer to the API permission list above.
3. Apply for permissions: Contact the primary account administrator to add the corresponding permission policies.
4. Verify permissions: Run the test commands again to confirm that the permissions have taken effect.