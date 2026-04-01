# KMS Secret Management RAM Permission Policies

This document lists the RAM permissions required for using KMS secret management features.

## Permission Overview

### Secret Management Permission List

| API Action | Permission Description | Resource Format |
|------------|----------------------|-----------------|
| kms:CreateSecret | Create secret | `acs:kms:*:*:secret/*` |
| kms:DeleteSecret | Delete secret | `acs:kms:*:*:secret/${SecretName}` |
| kms:UpdateSecret | Update secret metadata | `acs:kms:*:*:secret/${SecretName}` |
| kms:DescribeSecret | Query secret metadata | `acs:kms:*:*:secret/${SecretName}` |
| kms:ListSecrets | List secrets | `acs:kms:*:*:secret/*` |
| kms:GetSecretValue | Get secret value | `acs:kms:*:*:secret/${SecretName}` |
| kms:PutSecretValue | Store secret value | `acs:kms:*:*:secret/${SecretName}` |
| kms:ListSecretVersionIds | List secret versions | `acs:kms:*:*:secret/${SecretName}` |
| kms:UpdateSecretVersionStage | Update version stage | `acs:kms:*:*:secret/${SecretName}` |
| kms:UpdateSecretRotationPolicy | Update rotation policy | `acs:kms:*:*:secret/${SecretName}` |
| kms:RotateSecret | Rotate secret | `acs:kms:*:*:secret/${SecretName}` |
| kms:RestoreSecret | Restore secret | `acs:kms:*:*:secret/${SecretName}` |
| kms:SetSecretPolicy | Set secret policy | `acs:kms:*:*:secret/${SecretName}` |
| kms:GetSecretPolicy | Query secret policy | `acs:kms:*:*:secret/${SecretName}` |
| kms:ListKmsInstances | Query KMS instance list | `acs:kms:*:*:*` |
| kms:ListKeys | Query key list | `acs:kms:*:*:key/*` |
| kms:CreateKey | Create key | `acs:kms:*:*:*` |

---

## Recommended Permission Policies

### 1. Full Secret Management Permissions (Read-Write)

For users or applications requiring full secret management capabilities.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kms:CreateSecret",
        "kms:DeleteSecret",
        "kms:UpdateSecret",
        "kms:DescribeSecret",
        "kms:ListSecrets",
        "kms:GetSecretValue",
        "kms:PutSecretValue",
        "kms:ListSecretVersionIds",
        "kms:UpdateSecretVersionStage",
        "kms:UpdateSecretRotationPolicy",
        "kms:RotateSecret",
        "kms:RestoreSecret",
        "kms:SetSecretPolicy",
        "kms:GetSecretPolicy",
        "kms:ListKmsInstances",
        "kms:ListKeys",
        "kms:CreateKey"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2. Read-Only Secret Management Permissions

For users or applications only needing to query secret information.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kms:DescribeSecret",
        "kms:ListSecrets",
        "kms:GetSecretValue",
        "kms:ListSecretVersionIds",
        "kms:GetSecretPolicy",
        "kms:ListKmsInstances",
        "kms:ListKeys"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. Secret Create and Update Permissions (No Delete)

For users needing to create and update secrets but not delete them.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kms:CreateSecret",
        "kms:UpdateSecret",
        "kms:DescribeSecret",
        "kms:ListSecrets",
        "kms:GetSecretValue",
        "kms:PutSecretValue",
        "kms:ListSecretVersionIds",
        "kms:UpdateSecretVersionStage",
        "kms:UpdateSecretRotationPolicy",
        "kms:RotateSecret"
      ],
      "Resource": "*"
    }
  ]
}
```

### 4. Specified Secret Access Permissions

Restrict access to secrets with specific name prefixes.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kms:DescribeSecret",
        "kms:GetSecretValue",
        "kms:ListSecretVersionIds"
      ],
      "Resource": "acs:kms:*:*:secret/prod-*"
    },
    {
      "Effect": "Allow",
      "Action": "kms:ListSecrets",
      "Resource": "*"
    }
  ]
}
```

### 5. Application Minimum Permissions (GetSecretValue Only)

For application runtime scenarios retrieving secrets.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kms:GetSecretValue"
      ],
      "Resource": "acs:kms:*:*:secret/${SecretName}"
    }
  ]
}
```

---

## Additional Permissions for Managed Credentials

### RDS Managed Credentials

When using RDS managed credentials, additional RDS permissions are required:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:ResetAccountPassword",
        "rds:DescribeAccounts",
        "rds:DescribeDBInstanceAttribute"
      ],
      "Resource": "*"
    }
  ]
}
```

### RAM Managed Credentials

When using RAM managed credentials, additional RAM permissions are required:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ram:CreateAccessKey",
        "ram:DeleteAccessKey",
        "ram:ListAccessKeys",
        "ram:GetUser"
      ],
      "Resource": "*"
    }
  ]
}
```

### ECS Managed Credentials

When using ECS managed credentials, additional ECS permissions are required:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:ModifyInstanceAttribute",
        "ecs:DescribeInstances"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## System Policies

Alibaba Cloud provides the following system policies related to KMS:

| System Policy Name | Description |
|-------------------|-------------|
| AliyunKMSFullAccess | Full KMS permissions, includes all KMS operations |
| AliyunKMSReadOnlyAccess | KMS read-only permissions, includes query operations only |
| AliyunKMSSecretAdminAccess | Secret administrator permissions |

### Using System Policies

```bash
# Grant full KMS permissions to RAM user
aliyun ram AttachPolicyToUser \
  --PolicyType System \
  --PolicyName AliyunKMSFullAccess \
  --UserName <username>
```

---

## Best Practices

1. **Principle of Least Privilege**: Only grant necessary permissions, avoid using `*` wildcards
2. **Resource Restrictions**: Limit accessible secret scope through resource ARN
3. **Separate Read-Write Permissions**: Applications typically only need `GetSecretValue` permission
4. **Audit Logging**: Enable ActionTrail to record secret access logs
5. **Regular Review**: Periodically review and clean up unnecessary permissions

---

## Reference Links

- [KMS Authorize RAM Users](https://help.aliyun.com/zh/kms/key-management-service/security-and-compliance/authorization-information)
- [RAM Permission Policy Syntax](https://help.aliyun.com/zh/kms/key-management-service/security-and-compliance/sample-custom-permission-policies)
- [KMS API Reference](https://help.aliyun.com/zh/kms/key-management-service/developer-reference/api-kms-2016-01-20-overview)
