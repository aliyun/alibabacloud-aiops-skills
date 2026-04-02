# Acceptance Criteria: alibabacloud-hologres-instance-manage

**Scenario**: Hologres Instance Management
**Purpose**: Skill testing acceptance criteria for listing and querying Hologres instances

---

## Correct CLI Command Patterns

### 1. Product — Verify product name exists

✅ **CORRECT**
```bash
aliyun hologram ...
```

❌ **INCORRECT**
```bash
aliyun hologres ...      # Wrong product name
aliyun Hologram ...      # Case sensitivity may matter
aliyun holo ...          # Abbreviated name not valid
```

### 2. Command — Verify ROA-style path syntax

✅ **CORRECT**
```bash
# ListInstances - POST with path, timeout and user-agent
aliyun hologram POST /api/v1/instances --header "Content-Type=application/json" --body '{}' --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills

# GetInstance - GET with path parameter, timeout and user-agent
aliyun hologram GET /api/v1/instances/hgprecn-cn-i7m2v08uu00a --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT**
```bash
# Wrong: Using RPC-style action name
aliyun hologram ListInstances

# Wrong: Missing HTTP method
aliyun hologram /api/v1/instances

# Wrong: Wrong HTTP method
aliyun hologram GET /api/v1/instances  # ListInstances requires POST
```

### 3. Parameters — Verify parameter format

✅ **CORRECT**
```bash
# Header parameter format
--header "Content-Type=application/json"

# Body as JSON string
--body '{"resourceGroupId":"rg-xxx"}'

# Tags as JSON array
--body '{"tag":[{"key":"env","value":"prod"}]}'
```

❌ **INCORRECT**
```bash
# Wrong: Missing quotes around header value
--header Content-Type=application/json

# Wrong: Invalid JSON in body
--body {resourceGroupId:rg-xxx}

# Wrong: Incorrect tag structure
--body '{"tag":{"key":"env","value":"prod"}}'  # Should be array
```

### 4. User-Agent and Timeout — Verify required flags

✅ **CORRECT**
```bash
aliyun hologram POST /api/v1/instances ... --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT**
```bash
# Wrong: Missing user-agent
aliyun hologram POST /api/v1/instances ...

# Wrong: Missing timeout
aliyun hologram POST /api/v1/instances ... --user-agent AlibabaCloud-Agent-Skills

# Wrong: Wrong flag name
aliyun hologram POST /api/v1/instances ... --useragent AlibabaCloud-Agent-Skills
```

---

## Correct Python Common SDK Patterns (if applicable)

### 1. Import Patterns

✅ **CORRECT**
```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
```

❌ **INCORRECT**
```python
# Wrong: Old SDK imports
from aliyunsdkcore.client import AcsClient
from aliyunsdkhologram.request.v20220601.ListInstancesRequest import ListInstancesRequest

# Wrong: Missing credentials import
from alibabacloud_tea_openapi.client import Client as OpenApiClient
# Missing: from alibabacloud_credentials.client import Client as CredentialClient
```

### 2. Authentication — Must use CredentialClient

✅ **CORRECT**
```python
credential = CredentialClient()
config = open_api_models.Config(credential=credential)
config.endpoint = 'hologram.cn-hangzhou.aliyuncs.com'
client = OpenApiClient(config)
```

❌ **INCORRECT**
```python
# Wrong: Hardcoding credentials
config = open_api_models.Config()
config.access_key_id = 'LTAI5tXXXXXX'          # NEVER do this
config.access_key_secret = '8dXXXXXXXXXX'      # NEVER do this

# Wrong: Using environment variables directly in code
import os
config.access_key_id = os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID']  # Use CredentialClient instead
```

### 3. ROA Style API Configuration

✅ **CORRECT**
```python
# ListInstances - ROA POST
params = open_api_models.Params(
    action='ListInstances',
    version='2022-06-01',
    protocol='HTTPS',
    method='POST',
    auth_type='AK',
    style='ROA',
    pathname='/api/v1/instances',
    req_body_type='json',
    body_type='json'
)

# Request with body (ROA style)
body = {'resourceGroupId': 'rg-xxx'}
request = open_api_models.OpenApiRequest(body=body)
```

❌ **INCORRECT**
```python
# Wrong: Using RPC style for ROA API
params = open_api_models.Params(
    action='ListInstances',
    version='2022-06-01',
    style='RPC',          # Should be 'ROA'
    pathname='/',         # Should be '/api/v1/instances'
)

# Wrong: Using query instead of body for ROA POST
request = open_api_models.OpenApiRequest(
    query=OpenApiUtilClient.query(queries)  # Should use body for ROA
)
```

### 4. GetInstance Path Parameter

✅ **CORRECT**
```python
# GetInstance - ROA GET with path parameter
instance_id = 'hgprecn-cn-i7m2v08uu00a'
params = open_api_models.Params(
    action='GetInstance',
    version='2022-06-01',
    protocol='HTTPS',
    method='GET',
    auth_type='AK',
    style='ROA',
    pathname=f'/api/v1/instances/{instance_id}',  # Path parameter in URL
    req_body_type='json',
    body_type='json'
)
```

❌ **INCORRECT**
```python
# Wrong: Putting instanceId in query parameters
params = open_api_models.Params(
    pathname='/api/v1/instances',  # Missing instance ID in path
)
queries = {'instanceId': instance_id}  # Wrong location
```

---

## Request/Response Validation

### ListInstances Request

✅ **CORRECT Request Body**
```json
{}
```

```json
{
  "resourceGroupId": "rg-acfmvscak73zmby"
}
```

```json
{
  "tag": [
    {"key": "env", "value": "production"}
  ]
}
```

❌ **INCORRECT Request Body**
```json
{
  "tags": [{"key": "env", "value": "prod"}]  // Wrong: 'tags' instead of 'tag'
}
```

### ListInstances Response Validation

✅ **Valid Response**
```json
{
  "RequestId": "D1303CD4-AA70-5998-8025-F55B22C50840",
  "InstanceList": [...],
  "Success": "true",
  "HttpStatusCode": "200"
}
```

### GetInstance Response Validation

✅ **Valid Response**
```json
{
  "RequestId": "865A02C2-B374-5DD4-9B34-0CA15DA1AEBD",
  "Instance": {
    "InstanceId": "hgpostcn-cn-tl32s6cgw00b",
    "InstanceStatus": "Running",
    ...
  },
  "Success": true,
  "HttpStatusCode": "200"
}
```

---

## Error Handling Patterns

### Permission Error

✅ **CORRECT Handling**
```bash
# Check for permission error and provide guidance
RESPONSE=$(aliyun hologram POST /api/v1/instances ...)
if echo "$RESPONSE" | grep -q "NoPermission"; then
  echo "Permission denied. Please grant hologram:ListInstances permission."
  echo "See references/ram-policies.md for required permissions."
fi
```

### Instance Not Found

✅ **CORRECT Handling**
```bash
# Validate instance exists before detailed operations
RESPONSE=$(aliyun hologram GET /api/v1/instances/$INSTANCE_ID ...)
if echo "$RESPONSE" | grep -q "InstanceNotFound"; then
  echo "Instance $INSTANCE_ID not found. Use ListInstances to get valid IDs."
fi
```

---

## Checklist

Before considering this skill complete, verify:

- [ ] All CLI commands use `aliyun hologram` (correct product name)
- [ ] ListInstances uses `POST /api/v1/instances`
- [ ] GetInstance uses `GET /api/v1/instances/{instanceId}`
- [ ] All commands include `--user-agent AlibabaCloud-Agent-Skills`
- [ ] All commands include `--read-timeout 4`
- [ ] POST requests include `--header "Content-Type=application/json"`
- [ ] Request bodies are valid JSON
- [ ] Tags use array format: `[{"key":"...","value":"..."}]`
- [ ] Python SDK uses `CredentialClient()` for authentication
- [ ] Python SDK uses `style='ROA'` for these APIs
- [ ] Error handling covers NoPermission and InstanceNotFound cases
