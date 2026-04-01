# Acceptance Criteria: MaxCompute Project Management

**Scenario**: MaxCompute Project Management
**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Command Patterns

### 1. Product — Verify product name exists

#### ✅ CORRECT
```bash
aliyun maxcompute create-project
aliyun maxcompute get-project
aliyun maxcompute list-projects
aliyun maxcompute delete-project
```

#### ❌ INCORRECT
```bash
# Wrong product name
aliyun odps create-project
aliyun mc create-project

# Wrong command format (using API name directly)
aliyun maxcompute CreateProject
```

### 2. Command — Verify action exists under the product

#### ✅ CORRECT
```bash
# Plugin mode format (lowercase with hyphens)
aliyun maxcompute create-project
aliyun maxcompute get-project
aliyun maxcompute list-projects
aliyun maxcompute delete-project
```

#### ❌ INCORRECT
```bash
# Traditional API format (PascalCase) - NOT ALLOWED
aliyun maxcompute CreateProject
aliyun maxcompute GetProject
aliyun maxcompute ListProjects

# Wrong action names
aliyun maxcompute new-project
aliyun maxcompute query-project
```

### 3. Parameters — Verify each parameter name exists for the command

#### ✅ CORRECT - create-project
```bash
aliyun maxcompute create-project \
  --body '{"name":"my_project","defaultQuota":"os_PayAsYouGoQuota","productType":"payasyougo"}' \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT - create-project
```bash
# Wrong: using query parameters instead of body
aliyun maxcompute create-project \
  --project-name my_project \
  --quota-name os_PayAsYouGoQuota

# Wrong: missing --body for POST request
aliyun maxcompute create-project \
  --name my_project
```

#### ✅ CORRECT - get-project
```bash
aliyun maxcompute get-project \
  --project-name my_project \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT - get-project
```bash
# Wrong parameter name
aliyun maxcompute get-project --name my_project
aliyun maxcompute get-project --ProjectName my_project
```

#### ✅ CORRECT - list-projects
```bash
aliyun maxcompute list-projects \
  --quota-nick-name os_PayAsYouGoQuota \
  --max-item 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT - list-projects
```bash
# Wrong parameter names
aliyun maxcompute list-projects --quota os_PayAsYouGoQuota
aliyun maxcompute list-projects --pageSize 10
```

### 4. User-Agent Flag — MUST be present in every command

#### ✅ CORRECT
```bash
aliyun maxcompute get-project --project-name my_project --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# Missing user-agent flag
aliyun maxcompute get-project --project-name my_project
```

---

## Correct Request Body Patterns

### CreateProject Body

#### ✅ CORRECT
```json
{
  "name": "my_project",
  "defaultQuota": "os_PayAsYouGoQuota",
  "productType": "payasyougo"
}
```

```json
{
  "name": "my_project",
  "defaultQuota": "my_quota",
  "productType": "subscription",
  "properties": {
    "typeSystem": "2"
  }
}
```

#### ❌ INCORRECT
```json
// Wrong: using camelCase for name field
{
  "projectName": "my_project"
}

// Wrong: invalid productType value
{
  "name": "my_project",
  "productType": "free"
}

// Wrong: typeSystem should be string, not integer
{
  "name": "my_project",
  "properties": {
    "typeSystem": 2
  }
}
```

---

## Correct Common SDK Code Patterns (if applicable)

### 1. Import Patterns

#### ✅ CORRECT
```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient
```

#### ❌ INCORRECT
```python
# Wrong: using deprecated SDK
from aliyunsdkcore.client import AcsClient
from aliyunsdkmaxcompute.request.v20220104 import CreateProjectRequest

# Wrong: importing non-existent modules
from alibabacloud_maxcompute import MaxComputeClient
```

### 2. Authentication — Must use CredentialClient

#### ✅ CORRECT
```python
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models

credential = CredentialClient()
config = open_api_models.Config(credential=credential)
config.endpoint = 'maxcompute.cn-hangzhou.aliyuncs.com'
```

#### ❌ INCORRECT
```python
# Wrong: hardcoding credentials
config = open_api_models.Config(
    access_key_id='LTAI***',
    access_key_secret='***'
)

# Wrong: using environment variables directly
import os
config = open_api_models.Config(
    access_key_id=os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'],
    access_key_secret=os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET']
)
```

### 3. API Style — ROA vs RPC

#### ✅ CORRECT - MaxCompute uses ROA style
```python
params = open_api_models.Params(
    action='CreateProject',
    version='2022-01-04',
    protocol='HTTPS',
    method='POST',
    auth_type='AK',
    style='ROA',  # MaxCompute uses ROA style
    pathname='/api/v1/projects',
    req_body_type='json',
    body_type='json'
)
```

#### ❌ INCORRECT
```python
# Wrong: using RPC style for MaxCompute
params = open_api_models.Params(
    action='CreateProject',
    version='2022-01-04',
    style='RPC',  # Wrong style
    pathname='/'
)
```

---

## Parameter Value Constraints

| Parameter | Constraint | Example Valid | Example Invalid |
|-----------|------------|---------------|-----------------|
| `name` | 3-28 chars, lowercase, numbers, underscores | `my_project_1` | `My-Project`, `ab` |
| `productType` | Enum: `payasyougo`, `subscription` | `payasyougo` | `free`, `trial` |
| `typeSystem` | Enum: `1` (Hive), `2` (MaxCompute) | `"2"` | `3`, `"3"` |
| `maxItem` | Positive integer | `10` | `-1`, `0` |

---

## Error Handling Patterns

### Expected Error Responses

| Error Code | When | Correct Handling |
|------------|------|------------------|
| `ProjectAlreadyExist` | Creating duplicate project | Use different name or check existence first |
| `ProjectNotFound` | Querying non-existent project | Verify project name, check region |
| `InvalidProjectName` | Invalid project name format | Follow naming constraints |
| `NoPermission` | Missing RAM permissions | Check and update RAM policy |

---

## Checklist

Before using this skill:

- [ ] `aliyun version` shows >= 3.3.1
- [ ] `aliyun configure list` shows valid profile
- [ ] Required RAM permissions are granted
- [ ] All CLI commands use plugin mode (lowercase with hyphens)
- [ ] All CLI commands include `--user-agent AlibabaCloud-Agent-Skills`
- [ ] Request body uses correct JSON structure
- [ ] Parameter values match documented constraints
