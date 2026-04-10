# Acceptance Criteria: alibabacloud-elasticsearch-instance-manage

**Scenario**: Elasticsearch Instance Management
**Purpose**: Skill testing acceptance criteria

## Table of Contents

- [Correct CLI Command Patterns](#correct-cli-command-patterns)
- [Correct Common SDK Code Patterns (if applicable)](#correct-common-sdk-code-patterns-if-applicable)
- [Response Validation Criteria](#response-validation-criteria)
- [Security Criteria](#security-criteria)
- [References](#references)

---

## Correct CLI Command Patterns

### 1. Product — verify product name exists

#### ✅ CORRECT
```bash
aliyun elasticsearch create-instance ...
aliyun elasticsearch describe-instance ...
aliyun elasticsearch list-instance ...
aliyun elasticsearch restart-instance ...
aliyun elasticsearch update-instance ...
```

#### ❌ INCORRECT
```bash
aliyun es create-instance ...              # Wrong: product name is "elasticsearch" not "es"
aliyun Elasticsearch create-instance ...   # Wrong: product name must be lowercase
aliyun elastic create-instance ...         # Wrong: incomplete product name
```

---

### 2. Command — verify action exists under the product

#### ✅ CORRECT
```bash
aliyun elasticsearch create-instance      # Use kebab-case
aliyun elasticsearch describe-instance    # Use kebab-case
aliyun elasticsearch list-instance        # Use kebab-case
aliyun elasticsearch restart-instance     # Use kebab-case
aliyun elasticsearch update-instance      # Use kebab-case
```

#### ❌ INCORRECT
```bash
aliyun elasticsearch CreateInstance       # Wrong: use kebab-case, not PascalCase
aliyun elasticsearch createInstance       # Wrong: use kebab-case, not camelCase
aliyun elasticsearch create_instance      # Wrong: use kebab-case, not snake_case
aliyun elasticsearch createinstance       # Wrong: words must be separated by hyphens
```

---

### 3. Parameters — verify each parameter name exists for the command

#### ✅ CORRECT - create-instance
```bash
aliyun elasticsearch create-instance \
  --region cn-hangzhou \
  --es-admin-password "YourPassword123!" \
  --es-version "7.10_with_X-Pack" \
  --node-amount 2 \
  --network-config 'vpcId=vpc-xxx vswitchId=vsw-xxx vsArea=cn-hangzhou-i type=vpc' \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT - create-instance
```bash
aliyun elasticsearch create-instance \
  --password "xxx"           # Wrong: should be --es-admin-password
  --version "7.10"           # Wrong: should be --es-version
  --nodeAmount 2             # Wrong: should be --node-amount (kebab-case)
  --networkConfig '{...}'    # Wrong: should be --network-config (kebab-case)
```

#### ✅ CORRECT - describe-instance
```bash
aliyun elasticsearch describe-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT - describe-instance
```bash
aliyun elasticsearch describe-instance \
  --instanceId es-cn-xxx****   # Wrong: should be --instance-id (kebab-case)
  --InstanceId es-cn-xxx****   # Wrong: should be --instance-id (kebab-case, lowercase)
```

#### ✅ CORRECT - list-instance
```bash
aliyun elasticsearch list-instance \
  --region cn-hangzhou \
  --page 1 \
  --size 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT - list-instance
```bash
aliyun elasticsearch list-instance \
  --pageNumber 1   # Wrong: should be --page
  --pageSize 10    # Wrong: should be --size
```

#### ✅ CORRECT - restart-instance
```bash
aliyun elasticsearch restart-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --force true \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT - restart-instance
```bash
aliyun elasticsearch restart-instance \
  --instanceId es-cn-xxx****   # Wrong: should be --instance-id
  --Force true                  # Wrong: should be --force (lowercase)
```

#### ✅ CORRECT - list-all-node
```bash
aliyun elasticsearch list-all-node \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --user-agent AlibabaCloud-Agent-Skills

# With extended parameter
aliyun elasticsearch list-all-node \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --extended false \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT - list-all-node
```bash
aliyun elasticsearch list-all-node \
  --instanceId es-cn-xxx****   # Wrong: should be --instance-id
  --Extended true               # Wrong: should be --extended (lowercase)

aliyun elasticsearch listAllNode \
  --instance-id es-cn-xxx****   # Wrong: command should be list-all-node (kebab-case)
```

#### ✅ CORRECT - update-instance
```bash
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $(uuidgen) \
  --body '{"nodeSpec":{"spec":"elasticsearch.sn2ne.xlarge.new"}}' \
  --user-agent AlibabaCloud-Agent-Skills

# Downgrade with orderActionType
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $(uuidgen) \
  --order-action-type downgrade \
  --body '{"nodeSpec":{"spec":"elasticsearch.sn2ne.large.new"}}' \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT - update-instance
```bash
aliyun elasticsearch update-instance \
  --instanceId es-cn-xxx****   # Wrong: should be --instance-id (kebab-case)

aliyun elasticsearch update-instance \
  --body '{"nodeSpec":{"spec":"elasticsearch.sn2ne.xlarge.new"},"warmNodeConfiguration":{"amount":3}}'   # Wrong: cannot change multiple node types in one call

aliyun elasticsearch update-instance \
  --order-action-type downgrade \
  --body '{"nodeAmount":2}'   # Wrong: cannot reduce node count via UpdateInstance, use ShrinkNode
```

---

### 4. User-Agent — every command must include user-agent

#### ✅ CORRECT
```bash
aliyun elasticsearch list-instance \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
aliyun elasticsearch list-instance \
  --region cn-hangzhou
  # Missing: --user-agent AlibabaCloud-Agent-Skills
```

---

### 5. Parameter Values — verify format requirements

#### ✅ CORRECT - network-config format
```bash
# Format 1: key=value pairs
--network-config 'vpcId=vpc-xxx vswitchId=vsw-xxx vsArea=cn-hangzhou-i type=vpc'

# Format 2: JSON string
--network-config '{"vpcId":"vpc-xxx","vswitchId":"vsw-xxx","vsArea":"cn-hangzhou-i","type":"vpc"}'
```

#### ❌ INCORRECT - network-config format
```bash
# Wrong: missing required fields
--network-config 'vpcId=vpc-xxx'

# Wrong: incorrect field names
--network-config 'vpc_id=vpc-xxx vswitch_id=vsw-xxx'
```

#### ✅ CORRECT - es-version format
```bash
--es-version "7.10_with_X-Pack"
--es-version "8.5.1_with_X-Pack"
--es-version "6.7_with_X-Pack"
```

#### ❌ INCORRECT - es-version format
```bash
--es-version "7.10"           # Wrong: missing "_with_X-Pack"
--es-version "7.10-X-Pack"    # Wrong: incorrect format
```

#### ✅ CORRECT - payment-type values
```bash
--payment-type postpaid    # Pay-as-you-go
--payment-type prepaid     # Subscription
```

#### ❌ INCORRECT - payment-type values
```bash
--payment-type PayAsYouGo       # Wrong: should be "postpaid"
--payment-type Subscription     # Wrong: should be "prepaid"
```

---

## Correct Common SDK Code Patterns (if applicable)

### 1. Import Patterns

#### ✅ CORRECT
```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_util import models as util_models
```

#### ❌ INCORRECT
```python
from aliyunsdkcore.client import AcsClient           # Wrong: old SDK
from aliyunsdkelasticsearch.request import ...        # Wrong: product-specific SDK not recommended
```

### 2. Authentication — must use CredentialClient, never hardcode AK/SK

#### ✅ CORRECT
```python
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models

# Use CredentialClient for automatic credential management
credential = CredentialClient()
config = open_api_models.Config(credential=credential)
config.endpoint = "elasticsearch.cn-hangzhou.aliyuncs.com"
```

#### ❌ INCORRECT
```python
# NEVER hardcode credentials
config = open_api_models.Config(
    access_key_id="LTAI5tXXXXXX",          # FORBIDDEN
    access_key_secret="8dXXXXXXXXXX"       # FORBIDDEN
)
```

### 3. Client Initialization

#### ✅ CORRECT
```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient

credential = CredentialClient()
config = open_api_models.Config(credential=credential)
config.endpoint = "elasticsearch.cn-hangzhou.aliyuncs.com"
client = OpenApiClient(config)
```

---

## Response Validation Criteria

### create-instance Response
✅ Must contain:
- `RequestId` (string)
- `Result.instanceId` (string matching pattern `es-cn-*`)

### describe-instance Response
✅ Must contain:
- `RequestId` (string)
- `Result.instanceId` (string)
- `Result.status` (string: active|activating|inactive|invalid)
- `Result.esVersion` (string)

### list-instance Response
✅ Must contain:
- `RequestId` (string)
- `Headers.X-Total-Count` (integer)
- `Result` (array of instance objects)

### restart-instance Response
✅ Must contain:
- `RequestId` (string)
- `Result.instanceId` (string)

### update-instance Response
✅ Must contain:
- `RequestId` (string)
- `Result.instanceId` (string)
- `Result.status` (string, expected `activating` after successful update)

---

## Security Criteria

### ✅ CORRECT Security Practices
1. Use `aliyun configure list` to verify credentials (never echo AK/SK)
2. Use CredentialClient for SDK authentication
3. Use environment variables for sensitive data
4. Include `--user-agent AlibabaCloud-Agent-Skills` in all commands

### ❌ INCORRECT Security Practices
1. Hardcoding access keys in code or commands
2. Printing or echoing credential values
3. Using `aliyun configure set` with literal credential values in automated scripts

---

## References

- [Elasticsearch CLI Help](aliyun elasticsearch --help)
- [Alibaba Cloud CLI Documentation](https://help.aliyun.com/zh/cli/)
- [Elasticsearch API Reference](https://next.api.aliyun.com/product/elasticsearch)
