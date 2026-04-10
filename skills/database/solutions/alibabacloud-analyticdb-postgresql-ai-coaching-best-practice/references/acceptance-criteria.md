# Acceptance Criteria: AI Coaching Best Practice

**Scenario**: AI Coaching 最佳实践 - Supabase 陪练平台 + ADBPG 知识库 RAG 驱动陪练系统
**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Command Patterns

### 1. Product Subcommand - verify `gpdb` exists

#### ✅ CORRECT
```bash
aliyun gpdb CreateDBInstance --region cn-hangzhou ...
aliyun gpdb DescribeDBInstances --region cn-hangzhou ...
aliyun gpdb ChatWithKnowledgeBase --region cn-hangzhou ...
```

#### ❌ INCORRECT
```bash
aliyun gpdb Createdbinstance --region cn-hangzhou ...  # Wrong case
aliyun gpdb create-db-instance --region cn-hangzhou ...  # Wrong format
aliyun adbpg CreateDBInstance --region cn-hangzhou ...  # Wrong product name
```

### 2. Action Subcommand - verify action exists under `gpdb`

#### ✅ CORRECT
```bash
aliyun gpdb CreateSupabaseProject --region cn-hangzhou ...
aliyun gpdb InitVectorDatabase --region cn-hangzhou ...
aliyun gpdb CreateNamespace --region cn-hangzhou ...
aliyun gpdb CreateDocumentCollection --region cn-hangzhou ...
aliyun gpdb UploadDocumentAsync --region cn-hangzhou ...
aliyun gpdb ChatWithKnowledgeBase --region cn-hangzhou ...
```

#### ❌ INCORRECT
```bash
aliyun gpdb create-supabase-project --region cn-hangzhou ...  # Wrong case (should be PascalCase)
aliyun gpdb CreateSupabase --region cn-hangzhou ...  # Wrong action name
aliyun gpdb InitVectorDB --region cn-hangzhou ...  # Wrong abbreviation
aliyun gpdb CreateCollection --region cn-hangzhou ...  # Missing Document prefix
```

### 3. Parameters - verify each parameter name exists

#### ✅ CORRECT
```bash
aliyun gpdb CreateDBInstance \
  --RegionId cn-hangzhou \
  --ZoneId cn-hangzhou-j \
  --Engine gpdb \
  --EngineVersion "7.0" \
  --DBInstanceMode StorageElastic \
  --InstanceSpec "4C32G" \
  --DBInstanceCategory HighAvailability \
  --VectorConfigurationStatus enabled \
  --SegStorageType cloud_essd \
  --SegNodeNum 4 \
  --StorageSize 50 \
  --VPCId vpc-xxxxx \
  --VSwitchId vsw-xxxxx \
  --PayType Postpaid
```

#### ❌ INCORRECT
```bash
aliyun gpdb CreateDBInstance \
  --region cn-hangzhou \  # Wrong case (should be --RegionId)
  --zone cn-hangzhou-j \  # Wrong parameter name (should be --ZoneId)
  --engine-version "7.0" \  # Wrong parameter name (should be --EngineVersion)
  --instance-type "4C32G" \  # Wrong parameter name (should be --InstanceSpec)
  --vpc vpc-xxxxx \  # Wrong parameter name (should be --VPCId)
  --vswitch vsw-xxxxx \  # Wrong parameter name (should be --VSwitchId)
```

### 4. Enum Values - verify values fall within allowed range

#### ✅ CORRECT
```bash
# DBInstanceMode values
--DBInstanceMode StorageElastic
--DBInstanceMode Serverless

# DBInstanceCategory values
--DBInstanceCategory HighAvailability
--DBInstanceCategory Basic

# PayType values
--PayType Postpaid
--PayType Prepaid

# VectorConfigurationStatus values
--VectorConfigurationStatus enabled
--VectorConfigurationStatus disabled
```

#### ❌ INCORRECT
```bash
--DBInstanceMode elastic-storage  # Invalid enum value
--DBInstanceCategory ha  # Invalid abbreviation
--PayType pay-as-you-go  # Wrong format (should be Postpaid)
--VectorConfigurationStatus true  # Not a valid enum value
```

### 5. Parameter Value Formats - verify format matches spec

#### ✅ CORRECT
```bash
# RegionId format
--RegionId cn-hangzhou
--RegionId cn-shanghai
--RegionId cn-beijing

# ZoneId format
--ZoneId cn-hangzhou-j
--ZoneId cn-shanghai-f

# InstanceSpec format
--InstanceSpec "4C32G"
--InstanceSpec "8C64G"
--InstanceSpec "16C128G"

# StorageSize (integer, GB)
--StorageSize 50
--StorageSize 100

# SecurityIPList (CIDR or IP, comma-separated)
--SecurityIPList "192.168.1.0/24,10.0.0.1"

# JSON parameters
--ModelParams '{
  "Model": "qwen-max",
  "Messages": [
    {"Role": "system", "Content": "You are a helpful coaching assistant."},
    {"Role": "user", "Content": "Hello"}
  ]
}'

--KnowledgeParams '{
  "SourceCollection": [{
    "Collection": "coaching_knowledge",
    "Namespace": "ns_coaching",
    "NamespacePassword": "NsPass123!",
    "TopK": 5
  }]
}'
```

#### ❌ INCORRECT
```bash
--RegionId hangzhou  # Missing country prefix
--ZoneId cn-hangzhou  # Missing zone suffix (-j, -f, etc.)
--InstanceSpec "4vCPU 32GB"  # Wrong format
--StorageSize "50GB"  # Should be integer only
--SecurityIPList "192.168.1"  # Incomplete IP/CIDR
--ModelParams "Model=qwen-max"  # Should be JSON object
```

### 6. User-Agent Flag - MUST be present

#### ✅ CORRECT
```bash
aliyun gpdb DescribeDBInstances --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun gpdb CreateDBInstance --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills ...
aliyun vpc describe-vpcs --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun vpc create-nat-gateway --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills ...
```

#### ❌ INCORRECT
```bash
aliyun gpdb DescribeDBInstances --region cn-hangzhou  # Missing --user-agent
aliyun gpdb CreateDBInstance --region cn-hangzhou ...  # Missing --user-agent
aliyun vpc create-nat-gateway --biz-region-id cn-hangzhou ...  # Missing --user-agent
```

### 7. Database Account Commands - correct parameter usage

#### ✅ CORRECT
```bash
# describe-accounts: only --db-instance-id required
aliyun gpdb describe-accounts --db-instance-id gp-xxxxx --user-agent AlibabaCloud-Agent-Skills

# create-account: use --region (not --biz-region-id), --account-type defaults to Super
aliyun gpdb create-account --db-instance-id gp-xxxxx --region cn-hangzhou --account-name ai_coaching_01 --account-password 'Coach3Acc#2x9K' --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# Wrong: using --biz-region-id (not supported by describe-accounts)
aliyun gpdb describe-accounts --biz-region-id cn-hangzhou --db-instance-id gp-xxxxx

# Wrong: using --biz-region-id (not supported by create-account, use --region)
aliyun gpdb create-account --biz-region-id cn-hangzhou --db-instance-id gp-xxxxx --account-name admin_user --account-password 'Pass123!'

# Wrong: missing --user-agent
aliyun gpdb create-account --db-instance-id gp-xxxxx --account-name admin_user --account-password 'Pass123!'
```

### 8. NAT Gateway & EIP Commands - correct VPC plugin mode format

#### ✅ CORRECT
```bash
# Check NAT Gateways
aliyun vpc describe-nat-gateways --biz-region-id cn-hangzhou --vpc-id vpc-xxxxx --user-agent AlibabaCloud-Agent-Skills

# Get VSwitch CIDR
aliyun vpc describe-vswitch-attributes --biz-region-id cn-hangzhou --vswitch-id vsw-xxxxx --user-agent AlibabaCloud-Agent-Skills

# Create Enhanced NAT Gateway
aliyun vpc create-nat-gateway --biz-region-id cn-hangzhou --vpc-id vpc-xxxxx --vswitch-id vsw-xxxxx --nat-type Enhanced --user-agent AlibabaCloud-Agent-Skills

# Query EIP addresses
aliyun vpc describe-eip-addresses --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

# Allocate new EIP
aliyun vpc allocate-eip-address --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

# Bind EIP to NAT Gateway (--instance-type Nat)
aliyun vpc associate-eip-address --biz-region-id cn-hangzhou --allocation-id eip-xxxxx --instance-id ngw-xxxxx --instance-type Nat --user-agent AlibabaCloud-Agent-Skills

# Create SNAT entry (--source-cidr for CIDR)
aliyun vpc create-snat-entry --biz-region-id cn-hangzhou --snat-table-id stb-xxxxx --source-cidr "172.16.0.0/20" --snat-ip "47.xx.xx.xx" --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# Wrong: using --region instead of --biz-region-id
aliyun vpc describe-nat-gateways --region cn-hangzhou --vpc-id vpc-xxxxx

# Wrong: missing --nat-type Enhanced
aliyun vpc create-nat-gateway --biz-region-id cn-hangzhou --vpc-id vpc-xxxxx

# Wrong: missing --instance-type Nat when binding EIP to NAT
aliyun vpc associate-eip-address --biz-region-id cn-hangzhou --allocation-id eip-xxxxx --instance-id ngw-xxxxx

# Wrong: using --source-vswitch-id without --snat-ip (SNAT IP is required for public NAT)
aliyun vpc create-snat-entry --biz-region-id cn-hangzhou --snat-table-id stb-xxxxx --source-vswitch-id vsw-xxxxx
```

---

## Correct Common SDK Code Patterns (if applicable)

### 1. Import Patterns

#### ✅ CORRECT
```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_gpdb20160503.client import Client as GpdbClient
from alibabacloud_tea_openapi import models as open_api_models
```

#### ❌ INCORRECT
```python
from aliyun import gpdb  # Wrong SDK structure
import alibabacloud  # Too generic
from alibabacloud.gpdb import Client  # Wrong import path
```

### 2. Authentication - must use CredentialClient, never hardcode AK/SK

#### ✅ CORRECT
```python
credential = CredentialClient()
config = open_api_models.Config(credential=credential)
client = GpdbClient(config)
```

#### ❌ INCORRECT
```python
# NEVER hardcode credentials
access_key_id = "LTAI5tXXXXXXXX"
access_key_secret = "8dXXXXXXXXXXXXXXXXXXXXXXXX"
config = open_api_models.Config(
    access_key_id=access_key_id,
    access_key_secret=access_key_secret
)
```

### 3. Client Initialization

#### ✅ CORRECT
```python
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_gpdb20160503.client import Client as GpdbClient
from alibabacloud_tea_openapi import models as open_api_models

# Create credential client (uses environment variables or default credentials)
credential = CredentialClient()

# Create config
config = open_api_models.Config(
    credential=credential,
    region_id="cn-hangzhou",
    endpoint="gpdb.cn-hangzhou.aliyuncs.com"
)

# Create client
client = GpdbClient(config)
```

#### ❌ INCORRECT
```python
# Missing credential client
config = open_api_models.Config(
    access_key_id="xxx",  # Hardcoded
    access_key_secret="xxx"  # Hardcoded
)
client = GpdbClient(config)
```

### 4. Async Patterns

#### ✅ CORRECT
```python
import asyncio
from alibabacloud_gpdb20160503 import models

async def upload_document():
    request = models.UploadDocumentAsyncRequest(
        dbinstance_id="gp-xxxxx",
        namespace="ns_coaching",
        collection="coaching_knowledge",
        file_name="domain_knowledge.pdf",
        file_url="https://example.com/knowledge.pdf"
    )
    response = await client.upload_document_async(request)
    return response.body
```

#### ❌ INCORRECT
```python
# Using sync method for async operation
def upload_document():
    request = models.UploadDocumentAsyncRequest(...)
    response = client.upload_document(request)  # Wrong method
```

### 5. Common Anti-Patterns

#### ❌ INCORRECT - Reading/Printing Credentials
```bash
# NEVER do this in skill or scripts
echo $ALIBABA_CLOUD_ACCESS_KEY_ID
echo "Your key is: $ALIBABA_CLOUD_ACCESS_KEY_SECRET"
cat ~/.aliyun/config.json
```

#### ✅ CORRECT
```bash
# Only check credential status
aliyun configure list
```

#### ❌ INCORRECT - Skipping Verification
```bash
# Don't skip credential verification
aliyun gpdb CreateDBInstance ...  # Without checking if credentials exist
```

#### ✅ CORRECT
```bash
# Always verify credentials first
aliyun configure list
# Check for valid profile before proceeding
aliyun gpdb DescribeDBInstances --region cn-hangzhou  # Test connectivity
```

---

## Parameter Confirmation Patterns

### ✅ CORRECT - Confirm Before Execution
```
Before proceeding, I need to confirm the following parameters:

| Parameter | Value | Description |
|-----------|-------|-------------|
| RegionId | cn-hangzhou | Region where resources will be created |
| InstanceSpec | 4C32G | ADBPG instance specification |
| StorageSize | 50 GB | Initial storage size |
| VPCId | vpc-xxxxx | VPC for network isolation |
| VSwitchId | vsw-xxxxx | VSwitch for subnet |

Please confirm these values or provide alternatives.
```

### ❌ INCORRECT - Assuming Values
```bash
# Never assume user-specific parameters without confirmation
aliyun gpdb CreateDBInstance \
  --RegionId cn-hangzhou \  # Assumed default
  --InstanceSpec "4C32G" \  # Assumed default
  --VPCId vpc-xxxxx \  # Assumed without asking
  ...
```

---

## Verification Checklist

Before marking skill execution as complete:

- [ ] All `aliyun` commands include `--user-agent AlibabaCloud-Agent-Skills`
- [ ] Credential verification performed before any CLI invocation
- [ ] All user-customizable parameters confirmed with user
- [ ] No hardcoded credentials in any output
- [ ] Instance/Resource status verified after creation
