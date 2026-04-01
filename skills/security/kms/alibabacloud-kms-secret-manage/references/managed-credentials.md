# Managed Credentials Guide

This document details the creation and management of KMS managed credentials.

## Managed Credentials Overview

Managed credentials can automatically manage cloud product credential rotation, supporting the following types:

| Type | Description | Supported Cloud Products |
|------|-------------|-------------------------|
| Rds | RDS Managed Credentials | ApsaraDB RDS |
| RAMCredentials | RAM Managed Credentials | RAM User AccessKey |
| ECS | ECS Managed Credentials | ECS Instance Login Credentials |
| Redis | Redis Managed Credentials | Redis Instances |
| PolarDB | PolarDB Managed Credentials | PolarDB Databases |

---

## RDS Managed Credentials

### Create RDS Managed Credential

```bash
aliyun kms CreateSecret \
  --SecretName "<secret-name>" \
  --SecretType Rds \
  --SecretData '{"Accounts":[{"AccountName":"<db-username>","AccountPassword":"<password>"}]}' \
  --VersionId "v1" \
  --ExtendedConfig '{"SecretSubType":"SingleUser","DBInstanceId":"<RDS-instance-ID>"}' \
  --EnableAutomaticRotation true \
  --RotationInterval 7d \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### SecretData Format

```json
{
  "Accounts": [
    {
      "AccountName": "dbuser",
      "AccountPassword": "<database-password>"
    }
  ]
}
```

### ExtendedConfig Format

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| SecretSubType | String | Yes | Fixed value: SingleUser or DualUser |
| DBInstanceId | String | Yes | RDS Instance ID |
| CustomData | Object | No | Custom data |

```json
{
  "SecretSubType": "SingleUser",
  "DBInstanceId": "rm-xxxxxxxx",
  "CustomData": {}
}
```

### Rotation Mode Description

- **SingleUser**: Single account mode, directly modifies account password during rotation
- **DualUser**: Dual account mode, switches between two accounts during rotation, no business interruption

---

## RAM Managed Credentials

### Create RAM Managed Credential

```bash
aliyun kms CreateSecret \
  --SecretName "<secret-name>" \
  --SecretType RAMCredentials \
  --SecretData '{"AccessKeys":[{"AccessKeyId":"<AK>","AccessKeySecret":"<SK>"}]}' \
  --VersionId "v1" \
  --ExtendedConfig '{"SecretSubType":"RamUserAccessKey","UserName":"<RAM-username>"}' \
  --EnableAutomaticRotation true \
  --RotationInterval 30d \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### SecretData Format

```json
{
  "AccessKeys": [
    {
      "AccessKeyId": "<AccessKeyId>",
      "AccessKeySecret": "<AccessKeySecret>"
    }
  ]
}
```

### ExtendedConfig Format

```json
{
  "SecretSubType": "RamUserAccessKey",
  "UserName": "ram-user-name",
  "CustomData": {}
}
```

---

## ECS Managed Credentials

### Create ECS Managed Credential (Password Mode)

```bash
aliyun kms CreateSecret \
  --SecretName "<secret-name>" \
  --SecretType ECS \
  --SecretData '{"UserName":"root","Password":"<password>"}' \
  --VersionId "v1" \
  --ExtendedConfig '{"SecretSubType":"Password","RegionId":"<region-id>","InstanceId":"<ECS-instance-ID>"}' \
  --EnableAutomaticRotation true \
  --RotationInterval 30d \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Password Mode SecretData Format

```json
{
  "UserName": "root",
  "Password": "<login-password>"
}
```

### SSH Key Mode SecretData Format

```json
{
  "UserName": "root",
  "PublicKey": "<SSH-public-key>",
  "PrivateKey": "<SSH-private-key>"
}
```

### ExtendedConfig Format

```json
{
  "SecretSubType": "Password",
  "RegionId": "cn-hangzhou",
  "InstanceId": "i-xxxxxxxx",
  "CustomData": {}
}
```

---

## Secret Policy (KMS Instance Only)

> **Limitation**: `SetSecretPolicy` and `GetSecretPolicy` APIs **only apply to secrets in KMS instances**, not supported in shared KMS.

### Set Secret Policy

```bash
aliyun kms SetSecretPolicy \
  --SecretName "<secret-name>" \
  --Policy '<policy-JSON>' \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Policy Format Example

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "RAM": ["acs:ram::*:user/app-user"]
      },
      "Action": ["kms:GetSecretValue"],
      "Resource": ["*"]
    }
  ]
}
```

### Query Secret Policy

```bash
aliyun kms GetSecretPolicy \
  --SecretName "<secret-name>" \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Additional RAM Permissions Required for Managed Credentials

When using managed credentials, in addition to KMS permissions, you need to grant permissions for the corresponding cloud products.

### RDS Managed Credential Permissions

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

### RAM Managed Credential Permissions

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

### ECS Managed Credential Permissions

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

## Rotation Policy Configuration

### Enable Automatic Rotation

```bash
aliyun kms UpdateSecretRotationPolicy \
  --SecretName "<secret-name>" \
  --EnableAutomaticRotation true \
  --RotationInterval 7d \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Rotation Interval Description

| Format | Example | Description |
|--------|---------|-------------|
| Days | 7d | Rotate every 7 days |
| Hours | 168h | Rotate every 168 hours |

**Valid Range**: 6 hours ~ 365 days

### Disable Automatic Rotation

```bash
aliyun kms UpdateSecretRotationPolicy \
  --SecretName "<secret-name>" \
  --EnableAutomaticRotation false \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Manual Rotation

```bash
aliyun kms RotateSecret \
  --SecretName "<secret-name>" \
  --VersionId "<new-version-id>" \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Best Practices

1. **Choose appropriate rotation period**: 7-30 days recommended for production
2. **Use dual account mode (RDS)**: Avoid business interruption during rotation
3. **Monitor rotation events**: Monitor rotation results via ActionTrail
4. **Test rotation process**: Verify in test environment before applying to production
5. **Configure alerts**: Set up CloudMonitor alerts for rotation failure events
