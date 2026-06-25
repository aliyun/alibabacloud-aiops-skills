# RAM Permissions for KVStore Health Inspection

This document describes the minimum RAM permissions required to run the KVStore health inspection tool.

## Required Permissions

The inspection tool requires **read-only** access to the following Alibaba Cloud APIs:

### 1. R-KVStore (Redis) APIs

| API Action | Description |
|------------|-------------|
| `r-kvstore:DescribeInstances` | List Redis instances in an account |
| `r-kvstore:DescribeInstanceAttribute` | Get detailed instance attributes |
| `r-kvstore:DescribeHistoryMonitorValues` | Query historical monitoring metrics |
| `r-kvstore:DescribeLogicInstanceTopology` | Get cluster/readwrite topology information |
| `r-kvstore:DescribeEngineVersion` | Query Redis engine version |
| `r-kvstore:DescribeSlowLogRecords` | Query slow log records |

### 2. DAS (Database Autonomy Service) APIs

| API Action | Description |
|------------|-------------|
| `das:DescribeHotBigKeys` | Analyze hot keys and big keys |
| `das:GetRedisAllSession` | Get real-time session information |

### 3. CloudMonitor (CMS) APIs

| API Action | Description |
|------------|-------------|
| `cms:DescribeAlertLogList` | Query alert history records |
| `cms:DescribeMetricRuleList` | Query alert rule configurations |

## RAM Policy Example

Below is the minimum permission policy required:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "r-kvstore:DescribeInstances",
        "r-kvstore:DescribeInstanceAttribute",
        "r-kvstore:DescribeHistoryMonitorValues",
        "r-kvstore:DescribeLogicInstanceTopology",
        "r-kvstore:DescribeEngineVersion",
        "r-kvstore:DescribeSlowLogRecords"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "das:DescribeHotBigKeys",
        "das:GetRedisAllSession"
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

## Important Notes

1. **Read-Only Access**: The inspection tool only requires read permissions. No write or modification permissions are needed.

2. **Resource Scope**: The policy uses `"Resource": "*"` to allow inspection of all Redis instances in the account. To restrict to specific instances, modify the Resource field:
   ```json
   "Resource": "acs:r-kvstore:*:*:instance/<instance-id>"
   ```

3. **DAS API Region**: The DAS API calls (`DescribeHotBigKeys` and `GetRedisAllSession`) are made to the `cn-shanghai` region endpoint, regardless of where the Redis instance is located.

4. **System Policies**: You can also use the following system policies as alternatives:
   - `AliyunKvstoreReadOnlyAccess` - Provides read-only access to all KVStore resources
   - `AliyunCloudMonitorReadOnlyAccess` - Provides read-only access to CloudMonitor

5. **RAM User vs RAM Role**: 
   - For **RAM Users**: Attach the policy directly to the user
   - For **RAM Roles**: Attach the policy to the role, then assume the role using STS

## Verifying Permissions

To verify that your credentials have the required permissions, generate a session ID and use the **plugin (kebab-case) form** of the CLI with `--user-agent` on every command (do NOT use PascalCase, `ai-mode`, or `ALIBABA_CLOUD_USER_AGENT`):

```bash
# SA-2.11 Observability — generate a session ID and build the UA once
export ALICLOUD_SKILL_SESSION_ID="$(uuidgen | tr -d '-' | tr 'A-F' 'a-f')"
export UA="AlibabaCloud-Agent-Skills/alibabacloud-kvstore-health-inspection/${ALICLOUD_SKILL_SESSION_ID}"

# Test instance listing
aliyun r-kvstore describe-instances \
  --page-size 10 \
  --user-agent "${UA}"

# Test monitoring data access
aliyun r-kvstore describe-history-monitor-values \
  --instance-id <test-instance-id> \
  --monitor-keys CpuUsage \
  --start-time 2026-03-14T00:00:00Z \
  --end-time 2026-03-15T00:00:00Z \
  --interval-for-history 01m \
  --user-agent "${UA}"

# Test DAS API access
aliyun das describe-hot-big-keys \
  --instance-id <test-instance-id> \
  --region cn-shanghai \
  --user-agent "${UA}"

# Test CloudMonitor access
aliyun cms describe-alert-log-list \
  --product "kvstore" \
  --start-time $(($(date +%s) - 86400))000 \
  --end-time $(date +%s)000 \
  --page-size 10 \
  --user-agent "${UA}"
```

## Troubleshooting Permission Errors

If you encounter permission errors:

1. **Forbidden.RAM**: The RAM user/role lacks required permissions
   - Solution: Attach the policy above to the user/role

2. **Forbidden.Access**: The AccessKey is invalid or expired
   - Solution: Check AccessKey status in RAM console

3. **NoPermission.DAS**: DAS service is not activated
   - Solution: Activate DAS in the Alibaba Cloud console

4. **Throttling.User**: Too many API requests
   - Solution: The tool includes automatic retry with exponential backoff. If issues persist, reduce inspection frequency.

## Security Best Practices

1. **Use RAM Users**: Never use the root account AccessKey for inspections
2. **Minimum Privilege**: Use the exact policy above, avoid granting broader permissions
3. **Rotate Keys**: Regularly rotate AccessKey credentials
4. **Audit Logs**: Enable ActionTrail to monitor API access
5. **Temporary Credentials**: For automated inspections, consider using STS temporary credentials with short expiration times
