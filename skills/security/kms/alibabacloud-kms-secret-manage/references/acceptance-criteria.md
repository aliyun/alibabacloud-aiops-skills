# Acceptance Criteria: KMS Secret Management Skill

**Scenario**: Alibaba Cloud KMS Secret Management
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product Name - Verify product name exists (`kms` not other spellings)

#### ✅ Correct
```bash
aliyun kms CreateSecret ...
```

#### ❌ Incorrect
```bash
aliyun Kms CreateSecret ...    # Wrong case
aliyun key-management ...      # Wrong product name
```

## 2. API Action Name - Verify action exists under this product

#### ✅ Correct
```bash
aliyun kms CreateSecret
aliyun kms DeleteSecret
aliyun kms GetSecretValue
aliyun kms ListSecrets
```

#### ❌ Incorrect
```bash
aliyun kms create-secret        # Should be PascalCase
aliyun kms CreateCredential     # Wrong action name
```

## 3. Parameter Names - Verify parameters exist for this command

### CreateSecret Parameters

#### ✅ Correct
```bash
aliyun kms CreateSecret \
  --SecretName "my-secret" \
  --SecretData "secret-value" \
  --VersionId "v1" \
  --Description "description" \
  --SecretType "Generic" \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ Incorrect
```bash
aliyun kms CreateSecret \
  --secret-name "my-secret"    # Should be --SecretName
  --secret-data "value"        # Should be --SecretData
```

### GetSecretValue Parameters

#### ✅ Correct
```bash
aliyun kms GetSecretValue \
  --SecretName "my-secret" \
  --VersionId "v1" \
  --VersionStage "ACSCurrent" \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

### DeleteSecret Parameters

#### ✅ Correct
```bash
aliyun kms DeleteSecret \
  --SecretName "my-secret" \
  --ForceDeleteWithoutRecovery "true" \
  --RecoveryWindowInDays "7" \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

## 4. Enum Values - Verify parameter values are within allowed range

### SecretType Enum Values

#### ✅ Correct
```bash
--SecretType "Generic"
--SecretType "Rds"
--SecretType "RAMCredentials"
--SecretType "ECS"
```

#### ❌ Incorrect
```bash
--SecretType "generic"         # Wrong case
--SecretType "Database"        # Invalid enum value
```

### VersionStage Enum Values

#### ✅ Correct
```bash
--VersionStage "ACSCurrent"
--VersionStage "ACSPrevious"
```

### SecretDataType Enum Values

#### ✅ Correct
```bash
--SecretDataType "text"
--SecretDataType "binary"
```

## 5. Parameter Value Formats

### Filters Parameter (JSON array format)

#### ✅ Correct
```bash
--Filters '[{"Key":"SecretName","Values":["test-*"]}]'
```

#### ❌ Incorrect
```bash
--Filters '{"Key":"SecretName","Values":["test-*"]}'  # Should be array
--Filters "SecretName=test-*"                          # Wrong format
```

### ExtendedConfig Parameter (JSON object format)

#### ✅ Correct
```bash
--ExtendedConfig '{"SecretSubType":"SingleUser","DBInstanceId":"rm-xxxxxxxx"}'
```

### RotationInterval Parameter (time format)

#### ✅ Correct
```bash
--RotationInterval "7d"      # 7 days
--RotationInterval "168h"    # 168 hours
--RotationInterval "604800s" # 604800 seconds
```

#### ❌ Incorrect
```bash
--RotationInterval "7 days"  # Wrong format
--RotationInterval "1w"      # Week not supported
```

## 6. Required user-agent flag

#### ✅ Correct - Every command must include user-agent
```bash
aliyun kms CreateSecret \
  --SecretName "test" \
  --SecretData "value" \
  --VersionId "v1" \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ Incorrect - Missing user-agent
```bash
aliyun kms CreateSecret \
  --SecretName "test" \
  --SecretData "value" \
  --VersionId "v1" \
  --region cn-hangzhou
```

---

# Correct Common SDK Code Patterns (if applicable)

## 1. Import Paths

#### ✅ Correct
```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_util import models as util_models
```

#### ❌ Incorrect
```python
from aliyunsdkkms.client import Client       # Old SDK
from alibabacloud_kms import Client          # Wrong package name
```

## 2. Authentication - Must use CredentialClient, never hardcode AK/SK

#### ✅ Correct
```python
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models

credential = CredentialClient()
config = open_api_models.Config(credential=credential)
config.endpoint = 'kms.cn-hangzhou.aliyuncs.com'
```

#### ❌ Incorrect
```python
config = open_api_models.Config(
    access_key_id='LTAI5txxxxxxxx',        # Hardcoded AK
    access_key_secret='xxxxxxxxxx'          # Hardcoded SK
)
```

## 3. Client Initialization

#### ✅ Correct
```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient

client = OpenApiClient(config)
```

## 4. API Call

#### ✅ Correct
```python
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

params = open_api_models.Params(
    action='CreateSecret',
    version='2016-01-20',
    protocol='HTTPS',
    method='POST',
    auth_type='AK',
    style='RPC',
    pathname='/',
    req_body_type='json',
    body_type='json'
)

body = {
    'SecretName': 'my-secret',
    'SecretData': 'secret-value',
    'VersionId': 'v1'
}

runtime = util_models.RuntimeOptions()
request = open_api_models.OpenApiRequest(body=body)

response = client.call_api(params, request, runtime)
```

---

# Common Anti-patterns

## 1. Do not print secret values in output

#### ❌ Incorrect
```bash
echo "Secret value: $(aliyun kms GetSecretValue --SecretName test | jq -r '.SecretData')"
```

## 2. Do not expose secrets in command history

#### ✅ Correct - Read from file
```bash
aliyun kms CreateSecret \
  --SecretName "my-secret" \
  --SecretData "$(cat secret.txt)" \
  --VersionId "v1" \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

## 3. Do not assume default parameters

#### ❌ Incorrect - Missing required parameters
```bash
aliyun kms CreateSecret \
  --SecretName "my-secret" \
  --SecretData "value"
  # Missing --VersionId and --region
```

---

# Test Scenario Checklist

- [ ] CreateSecret can create generic secrets
- [ ] DeleteSecret soft delete with recovery window
- [ ] DeleteSecret force delete without recovery
- [ ] GetSecretValue get current version
- [ ] GetSecretValue get specified version
- [ ] GetSecretValue get ACSPrevious version
- [ ] ListSecrets list all secrets
- [ ] ListSecrets use Filters for filtering
- [ ] PutSecretValue store new version
- [ ] UpdateSecret update description
- [ ] UpdateSecretVersionStage switch version stage
- [ ] UpdateSecretRotationPolicy enable/disable auto rotation
- [ ] RotateSecret manual rotation
- [ ] RestoreSecret restore deleted secret
- [ ] SetSecretPolicy/GetSecretPolicy only work for secrets in KMS instances

---

# API Version and Endpoint

| Configuration | Value |
|--------------|-------|
| API Version | 2016-01-20 |
| Endpoint Format | kms.{regionId}.aliyuncs.com |
| Signature Style | RPC |
| Authentication | AK |
