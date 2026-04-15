# Acceptance Criteria: OpenSearch App Management

**Scenario**: OpenSearch Instance Management
**Purpose**: Skill test acceptance criteria

> **Terminology**: OpenSearch instance and OpenSearch app group are synonymous.

---

# Correct CLI Command Patterns

## 1. Product — Verify Product Name

✅ **CORRECT**: `opensearch`

```bash
aliyun opensearch --help
```

❌ **INCORRECT**: `open-search`, `OpenSearch`, `os`

---

## 2. Command — Verify Command Exists

### CreateAppGroup

✅ **CORRECT**:
```bash
aliyun opensearch create-app-group --help
```

❌ **INCORRECT**: `aliyun opensearch CreateAppGroup`, `aliyun opensearch create_app_group`

### ListAppGroups

✅ **CORRECT**:
```bash
aliyun opensearch list-app-groups --help
```

❌ **INCORRECT**: `aliyun opensearch ListAppGroups`, `aliyun opensearch list_app_groups`

### DescribeAppGroup

✅ **CORRECT**:
```bash
aliyun opensearch describe-app-group --help
```

❌ **INCORRECT**: `aliyun opensearch DescribeAppGroup`, `aliyun opensearch get-app-group`

---

## 3. Parameters — Verify Parameter Names

### create-app-group Parameters

✅ **CORRECT**:
```bash
# Generate idempotency token
CLIENT_TOKEN=$(uuidgen)

aliyun opensearch create-app-group \
  --client-token "$CLIENT_TOKEN" \
  --body '{
    "name": "my_app",
    "type": "enhanced",
    "chargeType": "POSTPAY",
    "domain": "ecommerce",
    "quota": {
      "docSize": 100,
      "computeResource": 2000,
      "spec": "opensearch.private.common"
    }
  }' \
  --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT** (wrong parameter format):
```bash
# Wrong: Should not use separate parameters, use --body JSON instead
aliyun opensearch create-app-group \
  --name my-app \
  --type standard \
  --charge-type POSTPAY \
  --quota "doc-size=10,compute-resource=20,spec=opensearch.share.common"
```

### Idempotency and Dry-run Parameters

✅ **CORRECT**:
```bash
# Dry-run mode
aliyun opensearch create-app-group \
  --dryRun true \
  --body '{...}' \
  --user-agent AlibabaCloud-Agent-Skills

# Idempotent creation (must generate token first)
CLIENT_TOKEN=$(uuidgen)
aliyun opensearch create-app-group \
  --client-token "$CLIENT_TOKEN" \
  --body '{...}' \
  --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT**:
```bash
# Wrong: dryRun should not be in body
aliyun opensearch create-app-group \
  --body '{"dryRun": true, ...}'

# Wrong: hardcoded token, should use uuidgen
aliyun opensearch create-app-group \
  --client-token "fixed-token-123"

# Wrong: parameter name is incorrect
aliyun opensearch create-app-group \
  --dry-run true    # Should be --dryRun
```

### list-app-groups Parameters

✅ **CORRECT**:
```bash
aliyun opensearch list-app-groups \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT**:
```bash
aliyun opensearch list-app-groups \
  --page 1 \                       # Wrong: should be --page-number
  --limit 10                       # Wrong: should be --page-size
```

### describe-app-group Parameters

✅ **CORRECT**:
```bash
aliyun opensearch describe-app-group \
  --app-group-identity my_instance \
  --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT**:
```bash
aliyun opensearch describe-app-group \
  --name my_instance \             # Wrong: should be --app-group-identity
  --app-name my_instance           # Wrong: should be --app-group-identity
```

---

## 4. Parameter Values — Verify Valid Values

### name Parameter (Instance Name)

Instance name must start with a letter, only lowercase letters, numbers, and underscores (_) allowed, hyphens (-) forbidden, max 30 characters.

✅ **CORRECT**: `my_search_instance`, `video_search`, `product_search_2024`

❌ **INCORRECT**: `my-search-instance` (contains hyphen), `My_Search` (uppercase), `123_search` (starts with number)

### type Parameter

✅ **CORRECT**: `standard` (High-performance), `enhanced` (Industry Algorithm)

❌ **INCORRECT**: `basic`, `advanced`, `enterprise`

### domain Parameter (for enhanced type only)

✅ **CORRECT**: `general` (default), `ecommerce`, `esports`, `community`, `education`

❌ **INCORRECT**: `retail`, `game`, `media`, `ECOMMERCE`

### chargeType Parameter

✅ **CORRECT**: `POSTPAY`, `PREPAY`

❌ **INCORRECT**: `postpay`, `prepay`, `PAY_AS_YOU_GO`, `SUBSCRIPTION`

> **Note**: When chargeType is `PREPAY`, `order` parameter is required

### order Parameter (required for PREPAY)

✅ **CORRECT**:
```bash
# Subscription instance must include order parameter
aliyun opensearch create-app-group \
  --client-token "$CLIENT_TOKEN" \
  --body '{
    "name": "my_prepay_instance",
    "type": "enhanced",
    "chargeType": "PREPAY",
    "quota": {...},
    "order": {
      "duration": 1,
      "pricingCycle": "Year",
      "autoRenew": true
    }
  }'
```

❌ **INCORRECT**:
```bash
# Wrong: Subscription instance missing order parameter
aliyun opensearch create-app-group \
  --body '{
    "chargeType": "PREPAY",
    "quota": {...}
  }'

# Wrong: order missing required fields
aliyun opensearch create-app-group \
  --body '{
    "chargeType": "PREPAY",
    "order": {
      "duration": 1
    }
  }'
```

### spec Parameter

✅ **CORRECT**:
- `opensearch.share.common`
- `opensearch.private.common`
- `opensearch.private.compute`
- `opensearch.private.storage`

❌ **INCORRECT**:
- `opensearch.share.junior`
- `opensearch.share.compute`
- `opensearch.share.storage`
- `share.common`
- `common`

---

## 5. User-Agent Flag — Verify User-Agent

✅ **CORRECT**: Every command includes `--user-agent AlibabaCloud-Agent-Skills`

```bash
aliyun opensearch list-app-groups --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT**: Missing user-agent

```bash
aliyun opensearch list-app-groups
```

---

# Correct Python Common SDK Code Patterns (Fallback)

If CLI is unavailable, Python Common SDK can be used as a fallback.

## 1. Import Patterns

✅ **CORRECT**:
```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
```

❌ **INCORRECT**:
```python
# Wrong: using deprecated SDK
from aliyunsdkcore.client import AcsClient

# Wrong: incorrect module name
from alibabacloud_opensearch import Client
```

## 2. Authentication — Must Use CredentialClient

✅ **CORRECT**:
```python
credential = CredentialClient()
config = open_api_models.Config(credential=credential)
config.endpoint = 'opensearch.cn-hangzhou.aliyuncs.com'
client = OpenApiClient(config)
```

❌ **INCORRECT** (hardcoded credentials):
```python
# FORBIDDEN: hardcoding credentials
config = open_api_models.Config()
config.access_key_id = 'LTAI5txxxxxxxx'
config.access_key_secret = 'xxxxxxxxxxxxxxxx'
```

## 3. API Style — OpenSearch Uses ROA Style

✅ **CORRECT**:
```python
params = open_api_models.Params(
    action='CreateAppGroup',
    version='2017-12-25',
    protocol='HTTPS',
    method='POST',
    auth_type='AK',
    style='ROA',
    pathname='/v4/openapi/app-groups',
    req_body_type='json',
    body_type='json'
)
```

❌ **INCORRECT** (wrong API style):
```python
params = open_api_models.Params(
    style='RPC',                    # Wrong: OpenSearch uses ROA style
    pathname='/',                   # Wrong: ROA requires specific path
)
```

---

# Critical Patterns Checklist

- [ ] All CLI commands use lowercase hyphen format (plugin mode)
- [ ] All commands include `--user-agent AlibabaCloud-Agent-Skills`
- [ ] Parameter names are correct (kebab-case format)
- [ ] Parameter values are within allowed enum range
- [ ] SDK code uses CredentialClient, no hardcoded credentials
- [ ] OpenSearch API uses ROA style with correct pathname
