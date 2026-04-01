# RAM Policies

## Permission Requirements

The following RAM permissions are required to execute this skill:

| Permission Name | API | Description |
|-----------------|-----|-------------|
| `yundun-sas:DescribeSuspEvents` | DescribeSuspEvents | Query security alert list |
| `yundun-sas:DescribeSecurityEventOperations` | DescribeSecurityEventOperations | Query available handling operations for alerts |
| `yundun-sas:HandleSecurityEvents` | HandleSecurityEvents | Execute alert handling operations |
| `yundun-sas:DescribeSecurityEventOperationStatus` | DescribeSecurityEventOperationStatus | Query handling status |

---

## Complete Permission Policies

### Read-Only Permissions (Query Alerts Only)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-sas:DescribeSuspEvents",
        "yundun-sas:DescribeSecurityEventOperations",
        "yundun-sas:DescribeSecurityEventOperationStatus"
      ],
      "Resource": "*"
    }
  ]
}
```

### Full Permissions (Query + Handle Alerts)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-sas:DescribeSuspEvents",
        "yundun-sas:DescribeSecurityEventOperations",
        "yundun-sas:HandleSecurityEvents",
        "yundun-sas:DescribeSecurityEventOperationStatus"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## System Policies

If you prefer not to create custom policies, you can use the following system policies:

| Policy Name | Description | Permission Scope |
|-------------|-------------|------------------|
| `AliyunYundunSASFullAccess` | Cloud Security Center full access | Includes all SAS operation permissions |
| `AliyunYundunSASReadOnlyAccess` | Cloud Security Center read-only access | Query only, no handling permissions |

**Recommendation:** Following the principle of least privilege, it is recommended to use the custom policies above rather than full access permissions.

---

## Permission Verification

Verify whether the current user has the required permissions:

```bash
# Test query permission
aliyun sas DescribeSuspEvents --PageSize 1 --user-agent AlibabaCloud-Agent-Skills

# If "NoPermission" error is returned, it indicates missing permissions
```

---

## Common Permission Errors

| Error Code | Description | Solution |
|------------|-------------|----------|
| `NoPermission` | No permission to perform this operation | Contact the main account administrator to grant permissions |
| `Forbidden.RAM` | Insufficient RAM permissions | Check RAM policy configuration |
| `InvalidAccessKeyId.NotFound` | Invalid AccessKey | Check credential configuration |

---

## Authorization Steps

1. Log in to [RAM Console](https://ram.console.aliyun.com/)
2. Create a custom policy or select a system policy
3. Attach the policy to the target user/role
4. Verify permissions are effective

---

## Important Notes

1. **Version Limitation**: Some handling operations (e.g., `kill_and_quara`) require Cloud Security Center Advanced Edition or higher
2. **Resource Limitation**: Some operations may be restricted by resource ownership, only able to handle alerts for assets under the current account
3. **Audit Logging**: All handling operations are recorded in the operation audit logs
