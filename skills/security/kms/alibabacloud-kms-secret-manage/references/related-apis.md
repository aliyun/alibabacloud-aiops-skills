# KMS Secret Management Related API List

This document lists all APIs related to Alibaba Cloud KMS secret management and their CLI commands.

## Secret Management API Overview

| Product | CLI Command | API Action | Description | CLI Supported |
|---------|-------------|------------|-------------|---------------|
| KMS | `aliyun kms CreateSecret` | CreateSecret | Create secret and store initial version | ✅ Supported |
| KMS | `aliyun kms DeleteSecret` | DeleteSecret | Delete secret object | ✅ Supported |
| KMS | `aliyun kms UpdateSecret` | UpdateSecret | Update secret metadata | ✅ Supported |
| KMS | `aliyun kms DescribeSecret` | DescribeSecret | Query secret metadata | ✅ Supported |
| KMS | `aliyun kms ListSecrets` | ListSecrets | Query all secrets created by current user in current region | ✅ Supported |
| KMS | `aliyun kms GetSecretValue` | GetSecretValue | Get secret value | ✅ Supported |
| KMS | `aliyun kms PutSecretValue` | PutSecretValue | Store a new version of secret value | ✅ Supported |
| KMS | `aliyun kms ListSecretVersionIds` | ListSecretVersionIds | Query all version information of secret | ✅ Supported |
| KMS | `aliyun kms UpdateSecretVersionStage` | UpdateSecretVersionStage | Update secret version stage | ✅ Supported |
| KMS | `aliyun kms UpdateSecretRotationPolicy` | UpdateSecretRotationPolicy | Update dynamic secret rotation policy | ✅ Supported |
| KMS | `aliyun kms RotateSecret` | RotateSecret | Actively rotate dynamic secret | ✅ Supported |
| KMS | `aliyun kms RestoreSecret` | RestoreSecret | Restore deleted secret | ✅ Supported |
| KMS | `aliyun kms SetSecretPolicy` | SetSecretPolicy | Set secret policy (KMS instance only) | ✅ Supported |
| KMS | `aliyun kms GetSecretPolicy` | GetSecretPolicy | Query secret policy (KMS instance only) | ✅ Supported |

## Auxiliary Query API Overview

| Product | CLI Command | API Action | Description | CLI Supported |
|---------|-------------|------------|-------------|---------------|
| KMS | `aliyun kms ListKmsInstances` | ListKmsInstances | Query KMS instance list | ✅ Supported |
| KMS | `aliyun kms ListKeys` | ListKeys | Query key list (supports filtering by type and instance) | ✅ Supported |
| KMS | `aliyun kms CreateKey` | CreateKey | Create key (auto-create when no AES256 key exists) | ✅ Supported |

---

## Detailed API Parameter Description

### 1. CreateSecret - Create Secret

Create a secret and store its initial version.

**CLI Command Format:**
```bash
aliyun kms CreateSecret \
  --SecretName <secret-name> \
  --SecretData <secret-value> \
  --VersionId <version-id> \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --SecretName | String | Secret name |
| --SecretData | String | Secret value, will be encrypted storage |
| --VersionId | String | Initial version ID |

**Optional Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --SecretType | String | Secret type: Generic (generic), Rds (RDS managed), RAMCredentials (RAM managed), ECS (ECS managed) |
| --SecretDataType | String | Secret value type: text (default), binary |
| --Description | String | Secret description |
| --EncryptionKeyId | String | Encryption key ID |
| --EnableAutomaticRotation | Boolean | Whether to enable automatic rotation |
| --RotationInterval | String | Rotation interval, e.g., 7d, 168h |
| --ExtendedConfig | String | Extended configuration (JSON format) |
| --Tags | String | Tags (JSON format) |
| --DKMSInstanceId | String | KMS instance ID |
| --Policy | String | Secret policy |

---

### 2. DeleteSecret - Delete Secret

Delete secret object, supports setting recovery window or force deletion.

**CLI Command Format:**
```bash
aliyun kms DeleteSecret \
  --SecretName <secret-name> \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --SecretName | String | Secret name |

**Optional Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --ForceDeleteWithoutRecovery | String | Whether to force delete (true/false), cannot recover after force delete |
| --RecoveryWindowInDays | String | Recovery window (days), default 30 days |

---

### 3. UpdateSecret - Update Secret Metadata

Update secret description or extended configuration.

**CLI Command Format:**
```bash
aliyun kms UpdateSecret \
  --SecretName <secret-name> \
  --Description <new-description> \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --SecretName | String | Secret name |

**Optional Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --Description | String | Secret description |
| --ExtendedConfig.CustomData | String | Custom data in extended configuration |

---

### 4. DescribeSecret - Query Secret Metadata

Query secret metadata information.

**CLI Command Format:**
```bash
aliyun kms DescribeSecret \
  --SecretName <secret-name> \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --SecretName | String | Secret name |

**Optional Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --FetchTags | String | Whether to return resource tags (true/false) |

---

### 5. ListSecrets - Query Secret List

Query all secrets created by current user in current region, supports pagination and filtering.

**CLI Command Format:**
```bash
aliyun kms ListSecrets \
  --PageNumber <page-number> \
  --PageSize <page-size> \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Pagination Parameters:**
| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| --PageNumber | Integer | No | Current page number, range: greater than 0 | 1 |
| --PageSize | Integer | No | Number of results per page, range: 1-100 | 10 |
| --FetchTags | String | No | Whether to return tags (true/false) | false |
| --Filters | String | No | Filter conditions (JSON format) | None |

**Filters Parameter Details:**

Filters is a JSON array composed of Key-Values pairs, supporting the following Key values:

| Key | Description | Values Example |
|-----|-------------|----------------|
| SecretName | Secret name | ["secret1", "secret2"] |
| Description | Secret description | ["Database password"] |
| SecretType | Secret type | ["Generic", "Rds", "RAMCredentials", "ECS", "Redis", "PolarDB"] |
| TagKey | Tag key | ["env", "project"] |
| TagValue | Tag value | ["prod", "test"] |
| DKMSInstanceId | KMS instance ID | ["kst-xxx"] |
| Creator | Creator | ["user1"] |

> **Note**: Multiple Values within the same Key are **OR** relationship.
> Example: `[{"Key":"SecretName","Values":["sec1","sec2"]}]` means SecretName=sec1 OR SecretName=sec2

**Pagination Information in Response:**
| Field | Type | Description |
|-------|------|-------------|
| TotalCount | Integer | Total number of secrets |
| PageNumber | Integer | Current page number |
| PageSize | Integer | Number per page |
| SecretList.Secret | Array | Secret list |

**Example 1 - Basic Pagination Query:**
```bash
# Query page 1, 20 items per page
aliyun kms ListSecrets \
  --PageNumber 1 \
  --PageSize 20 \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**Example 2 - Pagination Query with Tags:**
```bash
aliyun kms ListSecrets \
  --PageNumber 1 \
  --PageSize 20 \
  --FetchTags true \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**Example 3 - Filter by Secret Type:**
```bash
aliyun kms ListSecrets \
  --Filters '[{"Key":"SecretType","Values":["Rds","ECS"]}]' \
  --PageNumber 1 \
  --PageSize 50 \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**Example 4 - Filter by KMS Instance:**
```bash
aliyun kms ListSecrets \
  --Filters '[{"Key":"DKMSInstanceId","Values":["kst-hzz65f176a0ogplgqobxt"]}]' \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**Example 5 - Filter by Secret Name:**
```bash
aliyun kms ListSecrets \
  --Filters '[{"Key":"SecretName","Values":["prod-db","prod-api"]}]' \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

**Response Example:**
```json
{
  "PageNumber": 1,
  "PageSize": 20,
  "RequestId": "6a6287a0-ff34-4780-a790-fdfca900557f",
  "TotalCount": 55,
  "SecretList": {
    "Secret": [
      {
        "SecretName": "secret001",
        "SecretType": "Generic",
        "CreateTime": "2024-07-17T07:59:05Z",
        "UpdateTime": "2024-07-17T07:59:05Z"
      }
    ]
  }
}
```

> **Tip**: If filtering resources by tags exceeds 4000, please use the `ListResourceTags` interface for querying.

---

### 6. GetSecretValue - Get Secret Value

Get the actual value of a secret.

**CLI Command Format:**
```bash
aliyun kms GetSecretValue \
  --SecretName <secret-name> \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --SecretName | String | Secret name |

**Optional Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --VersionId | String | Version ID |
| --VersionStage | String | Version stage label (ACSCurrent/ACSPrevious), default ACSCurrent |
| --FetchExtendedConfig | Boolean | Whether to get extended configuration |

---

### 7. PutSecretValue - Store New Version Secret Value

Store a new version of secret value for a secret.

**CLI Command Format:**
```bash
aliyun kms PutSecretValue \
  --SecretName <secret-name> \
  --SecretData <new-secret-value> \
  --VersionId <new-version-id> \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --SecretName | String | Secret name |
| --SecretData | String | New secret value |
| --VersionId | String | New version ID (must be unique) |

**Optional Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --SecretDataType | String | Secret value type: text (default), binary |
| --VersionStages | String | Version labels |

---

### 8. ListSecretVersionIds - Query Secret Version List

Query all version information of a secret.

**CLI Command Format:**
```bash
aliyun kms ListSecretVersionIds \
  --SecretName <secret-name> \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --SecretName | String | Secret name |

**Optional Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --PageNumber | Integer | Page number |
| --PageSize | Integer | Number per page |
| --IncludeDeprecated | String | Whether to include deprecated versions (true/false) |

---

### 9. UpdateSecretVersionStage - Update Version Stage

Update secret version stage label.

**CLI Command Format:**
```bash
aliyun kms UpdateSecretVersionStage \
  --SecretName <secret-name> \
  --VersionStage <stage-label> \
  --MoveToVersion <target-version-id> \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --SecretName | String | Secret name |
| --VersionStage | String | Stage label (ACSCurrent/ACSPrevious/Custom) |

**Optional Parameters (at least one required):**
| Parameter | Type | Description |
|-----------|------|-------------|
| --MoveToVersion | String | Target version to move label to |
| --RemoveFromVersion | String | Remove label from specified version |

---

### 10. UpdateSecretRotationPolicy - Update Rotation Policy

Update secret rotation policy.

**CLI Command Format:**
```bash
aliyun kms UpdateSecretRotationPolicy \
  --SecretName <secret-name> \
  --EnableAutomaticRotation true \
  --RotationInterval 7d \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --SecretName | String | Secret name |
| --EnableAutomaticRotation | Boolean | Whether to enable automatic rotation |

**Optional Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --RotationInterval | String | Rotation interval (6 hours to 365 days), e.g., 7d, 168h |

---

### 11. RotateSecret - Manual Secret Rotation

Immediately execute secret rotation.

**CLI Command Format:**
```bash
aliyun kms RotateSecret \
  --SecretName <secret-name> \
  --VersionId <new-version-id> \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --SecretName | String | Secret name |
| --VersionId | String | New version ID after rotation |

---

### 12. RestoreSecret - Restore Deleted Secret

Restore a secret in deletion waiting period.

**CLI Command Format:**
```bash
aliyun kms RestoreSecret \
  --SecretName <secret-name> \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --SecretName | String | Secret name to restore |

---

### 13. SetSecretPolicy - Set Secret Policy

Set secret policy for secrets in KMS instances.

**CLI Command Format:**
```bash
aliyun kms SetSecretPolicy \
  --SecretName <secret-name> \
  --Policy '<policy-JSON>' \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --SecretName | String | Secret name |
| --Policy | String | Policy content (JSON format) |

**Optional Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --PolicyName | String | Policy name |

> **Note**: SetSecretPolicy and GetSecretPolicy only apply to secrets in KMS instances, not supported in shared KMS.

---

### 15. GetSecretPolicy - Query Secret Policy

Query the secret policy of a specified secret.

**CLI Command Format:**
```bash
aliyun kms GetSecretPolicy \
  --SecretName <secret-name> \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --SecretName | String | Secret name |

**Optional Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| --PolicyName | String | Policy name |

---

## Auxiliary Query API Parameter Description

### 16. ListKmsInstances - Query KMS Instance List

Query the list of KMS instances under current account. Used to automatically obtain DKMSInstanceId when creating secrets.

**CLI Command Format:**
```bash
aliyun kms ListKmsInstances \
  --PageNumber 1 \
  --PageSize 10 \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**
| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| --PageNumber | Integer | No | Current page number | 1 |
| --PageSize | Integer | No | Number per page (1-100) | 20 |

**Response:**
| Field | Description |
|-------|-------------|
| KmsInstances.KmsInstance[].KmsInstanceId | KMS instance ID |
| KmsInstances.KmsInstance[].KmsInstanceArn | KMS instance ARN |
| TotalCount | Total number of instances |

**Response Example:**
```json
{
  "KmsInstances": {
    "KmsInstance": [
      {
        "KmsInstanceId": "kst-hzz68c22f94iwd4k7v0jf",
        "KmsInstanceArn": "acs:kms:cn-hangzhou:120708975881****:keystore/kst-hzz68c22f94iwd4k7v0jf"
      }
    ]
  },
  "TotalCount": 1
}
```

---

### 17. ListKeys - Query Key List

Query the key list in current region, supports filtering by key type and KMS instance. Used to automatically obtain EncryptionKeyId when creating secrets.

**CLI Command Format:**
```bash
aliyun kms ListKeys \
  --Filters '[{"Key":"KeySpec","Values":["Aliyun_AES_256"]},{"Key":"DKMSInstanceId","Values":["<KMS-instance-ID>"]}]' \
  --PageNumber 1 \
  --PageSize 10 \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**
| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| --PageNumber | Integer | No | Current page number | 1 |
| --PageSize | Integer | No | Number per page (1-100) | 10 |
| --Filters | String | No | Filter conditions (JSON format) | None |

**Filters Supported Key Values:**
| Key | Description | Values Example |
|-----|-------------|----------------|
| KeySpec | Key type | ["Aliyun_AES_256", "Aliyun_SM4", "RSA_2048"] |
| KeyState | Key state | ["Enabled", "Disabled"] |
| KeyUsage | Key usage | ["ENCRYPT/DECRYPT", "SIGN/VERIFY"] |
| DKMSInstanceId | KMS instance ID | ["kst-xxx"] |
| CreatorType | Creator type | ["User", "Service"] |
| ProtectionLevel | Protection level | ["SOFTWARE", "HSM"] |

**Response:**
| Field | Description |
|-------|-------------|
| Keys.Key[].KeyId | Key ID |
| Keys.Key[].KeyArn | Key ARN |
| TotalCount | Total number of keys |

**Response Example:**
```json
{
  "Keys": {
    "Key": [
      {
        "KeyId": "key-hzz68d1fd85qslv95ilz4",
        "KeyArn": "acs:kms:cn-hangzhou:123456:key/key-hzz68d1fd85qslv95ilz4"
      }
    ]
  },
  "TotalCount": 1
}
```

---

### 18. CreateKey - Create Key

Create a key. When ListKeys query returns no AES256 key, automatically create one for secret encryption.

**CLI Command Format:**
```bash
aliyun kms CreateKey \
  --KeySpec Aliyun_AES_256 \
  --KeyUsage ENCRYPT/DECRYPT \
  --DKMSInstanceId "<KMS-instance-ID>" \
  --Description "Secret management encryption key" \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**
| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| --KeySpec | String | No | Key specification | Aliyun_AES_256 |
| --KeyUsage | String | No | Key usage | ENCRYPT/DECRYPT |
| --DKMSInstanceId | String | No | KMS instance ID (required when creating key for instance) | None |
| --Description | String | No | Key description | None |
| --Origin | String | No | Key material source: Aliyun_KMS / EXTERNAL | Aliyun_KMS |
| --EnableAutomaticRotation | Boolean | No | Whether to enable automatic rotation | false |
| --RotationInterval | String | No | Rotation interval, e.g., 365d | None |

**Response:**
| Field | Description |
|-------|-------------|
| KeyMetadata.KeyId | Created key ID |
| KeyMetadata.KeySpec | Key specification |
| KeyMetadata.KeyState | Key state |
| KeyMetadata.DKMSInstanceId | KMS instance ID |

**Response Example:**
```json
{
  "KeyMetadata": {
    "KeyId": "key-hzz62f1cb66fa42qo****",
    "KeySpec": "Aliyun_AES_256",
    "KeyUsage": "ENCRYPT/DECRYPT",
    "KeyState": "Enabled",
    "DKMSInstanceId": "kst-hzz68c22f94iwd4k7v0jf",
    "CreationDate": "2024-03-25T10:00:00Z",
    "Creator": "154035569884****",
    "Description": "Secret management encryption key",
    "Origin": "Aliyun_KMS",
    "ProtectionLevel": "SOFTWARE"
  }
}
```

---

## Secret Type Description

### 1. Generic (Generic Secret)

Used to store sensitive information in any format, such as API keys, database passwords, certificates, etc.

### 2. Rds (RDS Managed Secret)

Manage ApsaraDB RDS database account passwords, supports automatic rotation.

**SecretData Format:**
```json
{"Accounts":[{"AccountName":"user1","AccountPassword":"password123"}]}
```

**ExtendedConfig Format:**
```json
{
  "SecretSubType": "SingleUser",
  "DBInstanceId": "rm-xxxxxxxx",
  "CustomData": {}
}
```

### 3. RAMCredentials (RAM Managed Secret)

Manage RAM user AccessKeys, supports automatic rotation.

**SecretData Format:**
```json
{"AccessKeys":[{"AccessKeyId":"LTAI5xxx","AccessKeySecret":"xxx"}]}
```

**ExtendedConfig Format:**
```json
{
  "SecretSubType": "RamUserAccessKey",
  "UserName": "ram-user-name",
  "CustomData": {}
}
```

### 4. ECS (ECS Managed Secret)

Manage ECS instance login credentials (password or SSH key), supports automatic rotation.

**Password Mode SecretData Format:**
```json
{"UserName":"root","Password":"password123"}
```

**SSH Key Mode SecretData Format:**
```json
{"UserName":"root","PublicKey":"ssh-rsa xxx","PrivateKey":"-----BEGIN RSA PRIVATE KEY-----\nxxx\n-----END RSA PRIVATE KEY-----"}
```

**ExtendedConfig Format:**
```json
{
  "SecretSubType": "Password",
  "RegionId": "cn-hangzhou",
  "InstanceId": "i-xxxxxxxx",
  "CustomData": {}
}
```

---

## Limitations

| Feature | Limitation | Description |
|---------|------------|-------------|
| SetSecretPolicy/GetSecretPolicy | KMS instance only | Shared KMS does not support secret policy |
| Managed credential auto rotation | Requires configuration | Rds/RAMCredentials/ECS types require correct ExtendedConfig |
| Secret name | Unique and immutable | Cannot modify secret name after creation |
| Version ID | Unique | Version ID cannot be duplicated within the same secret |
