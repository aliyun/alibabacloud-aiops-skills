# RAM Policies for SQL Linting Skill

Required RAM permissions for the `alibabacloud-polardb-mysql-sql-lint` skill.

## Minimal RAM Policy

This policy grants the minimum permissions required for SQL linting and DAS diagnostics:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "hdm:DescribeInstanceDasPro",
        "hdm:CreateRequestDiagnosis",
        "hdm:GetRequestDiagnosisResult"
      ],
      "Resource": "*"
    }
  ]
}
```

## Policy Explanation

| Action | Purpose | Required For |
|--------|---------|--------------|
| `hdm:DescribeInstanceDasPro` | Query whether DAS Enterprise Edition (V1/V2) is enabled for the instance | Instance pre-check |
| `hdm:CreateRequestDiagnosis` | Create SQL diagnosis task | DAS SQL diagnosis |
| `hdm:GetRequestDiagnosisResult` | Retrieve diagnosis result | DAS SQL diagnosis |

## Extended RAM Policy (Recommended)

For comprehensive diagnostics including instance metadata and slow log analysis:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "hdm:DescribeInstanceDasPro",
        "hdm:ListInstances",
        "hdm:CreateStorageAnalysisTask",
        "hdm:GetStorageAnalysisTask",
        "hdm:CreateDiagnosisTask",
        "hdm:GetDiagnosisTask",
        "hdm:DescribeSlowLogRecords",
        "hdm:DescribeSlowLogSummary",
        "hdm:ExecuteScript"
      ],
      "Resource": "*"
    }
  ]
}
```

## Additional Actions Explained

| Action | Purpose |
|--------|---------|
| `hdm:ListInstances` | List available instances |
| `hdm:DescribeSlowLogRecords` | Analyze slow query logs |
| `hdm:DescribeSlowLogSummary` | Get slow query statistics |
| `hdm:ExecuteScript` | Execute diagnostic scripts (read-only) |

## How to Create RAM Policy

### Step 1: Create Custom Policy

1. Log on to the [RAM Console](https://ram.console.aliyun.com)
2. Navigate to **Permissions** > **Policies**
3. Click **Create Policy**
4. Select **JSON** tab
5. Paste the policy JSON above
6. Click **Continue to Edit Basic Information**
7. Enter policy name: `AliyunDASSQLLintAccess`
8. Click **OK**

### Step 2: Attach Policy to RAM User/Role

1. Navigate to **Identities** > **Users** (or **Roles**)
2. Click the target user/role
3. Go to **Permissions** tab
4. Click **Add Permissions**
5. Search for `AliyunDASSQLLintAccess`
6. Click **OK**

## Using with Alibaba Cloud CLI

Configure CLI with RAM user credentials:

```bash
# Configure CLI
aliyun configure set \
  --profile sql-lint \
  --mode AK \
  --access-key-id YOUR_ACCESS_KEY_ID \
  --access-key-secret YOUR_ACCESS_KEY_SECRET \
  --region cn-shanghai

# Verify configuration
aliyun das describe-instance-das-pro --instance-id pc-xxxxx --endpoint das.cn-shanghai.aliyuncs.com
```

## Using with Environment Variables

```bash
# Set environment variables
export ALIBABACLOUD_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
export ALIBABACLOUD_ACCESS_KEY_SECRET=YOUR_ACCESS_KEY_SECRET

# Run SQL linting
python3 scripts/sql_lint.py \
  --instance-id pc-xxxxx \
  --sql-file migration.sql \
  --region cn-shanghai
```

## Security Best Practices

1. **Least Privilege**: Use minimal RAM policy in production
2. **Temporary Credentials**: Use STS tokens for short-lived access
3. **RAM Roles**: Prefer roles over long-term AccessKeys
4. **Audit Logs**: Monitor RAM policy usage in ActionTrail
5. **Rotate Keys**: Regularly rotate AccessKey secrets

## Troubleshooting

### Error: Access Denied

```
Error: You are not authorized to do this action.
```

**Solution:**
1. Verify RAM policy is attached to user/role
2. Check policy syntax and actions
3. Wait 1-2 minutes for policy to take effect

### Error: Instance Not Found

```
Error: Instance not found: pc-xxxxx
```

**Solution:**
1. Verify instance ID is correct
2. Ensure instance is connected to DAS
3. Check instance is in the specified region

### Error: DAS Not Enabled

```
Error: DAS service is not enabled for this instance
```

**Solution:**
1. Enable DAS for the instance in DAS Console
2. Verify instance state is "Normal Access"
3. Wait 5 minutes for DAS to initialize

## Related Documentation

- [RAM Policy Documentation](https://www.alibabacloud.com/help/en/ram/latest)
- [DAS API Reference](https://www.alibabacloud.com/help/en/das/latest)
- [STS Temporary Credentials](https://www.alibabacloud.com/help/en/ram/latest/use-sts-for-temporary-access)
