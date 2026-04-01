# MaxCompute Quota Management - RAM Policies

## Overview

This document lists the required RAM (Resource Access Management) permissions for MaxCompute Quota management operations.

## API to Permission Mapping

| API Action | RAM Permission          | Description | Availability |
|------------|-------------------------|-------------|--------------|
| CreateQuota | `odps:CreateQuota`      | Create quota resources | ✅ Available |
| GetQuota | `odps:GetQuota`   | Query quota details | ⚠️ Deprecated |
| QueryQuota | `odps:QueryQuota` | Query quota details | ✅ Recommended |
| ListQuotas | `odps:ListQuotas` | List all quotas | ✅ Available |
| DeleteQuota | N/A                     | Delete quota resources | ❌ **No API** |

> **Note**: Delete Quota permission is not applicable as there is no DeleteQuota API. Quota deletion must be performed through the Console.

## Recommended Policy

### Full Quota Management Policy

This policy grants all permissions needed for quota management:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:CreateQuota",
        "odps:GetQuota",
        "odps:QueryQuota",
        "odps:ListQuotas"
      ],
      "Resource": "*"
    }
  ]
}
```

### Read-Only Quota Policy

For users who only need to view quota information:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:GetQuota",
        "odps:QueryQuota",
        "odps:ListQuotas"
      ],
      "Resource": "*"
    }
  ]
}
```

### Minimal Create Quota Policy

For users who need to create quotas:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:CreateQuota",
        "odps:QueryQuota",
        "odps:ListQuotas"
      ],
      "Resource": "*"
    }
  ]
}
```

## How to Attach Policy

### Via Alibaba Cloud Console

1. Log in to the [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Identities** > **Users**
3. Select the target user
4. Click **Add Permissions**
5. Select or create custom policy with above permissions
6. Confirm and save

### Via Aliyun CLI

```bash
# Create custom policy
aliyun ram create-policy \
  --policy-name MaxComputeQuotaManagement \
  --policy-document '{
    "Version": "1",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "odps:CreateQuota",
          "odps:QueryQuota",
          "odps:ListQuotas"
        ],
        "Resource": "*"
      }
    ]
  }' \
  --user-agent AlibabaCloud-Agent-Skills

# Attach policy to user
aliyun ram attach-policy-to-user \
  --policy-name MaxComputeQuotaManagement \
  --policy-type Custom \
  --user-name <your-username> \
  --user-agent AlibabaCloud-Agent-Skills
```

## System Policies

Alternatively, you can use the following system policies:

| Policy Name | Description |
|-------------|-------------|
| `AliyunMaxComputeFullAccess` | Full access to MaxCompute resources |
| `AliyunMaxComputeReadOnlyAccess` | Read-only access to MaxCompute resources |

## Notes

1. **Principle of Least Privilege**: Grant only the minimum permissions required for the task
2. **Resource Scope**: Consider limiting `Resource` to specific regions or quota IDs if needed
3. **Billing Permissions**: Creating subscription quotas may require additional billing permissions
4. **Audit Trail**: Enable ActionTrail for auditing quota management operations
5. **Delete Operations**: Since there is no DeleteQuota API, no delete permission is needed for API access
