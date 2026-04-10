# Acceptance Criteria - ADBPG Knowledge Base Management

**Scenario**: ADBPG Knowledge Base Management Skill  
**Purpose**: Skill testing acceptance criteria

## Table of Contents

- [1. CLI Command Pattern Verification](#1-cli-command-pattern-verification)
- [2. Python SDK Code Pattern Verification](#2-python-sdk-code-pattern-verification)
- [3. Workflow Verification](#3-workflow-verification)
- [4. Parameter Verification](#4-parameter-verification)
- [5. Security Checks](#5-security-checks)
- [6. Error Handling Checks](#6-error-handling-checks)
- [Checklist](#checklist)

---

## 1. CLI Command Pattern Verification

### 1.1 Product Name Verification

#### ✅ CORRECT
```bash
aliyun gpdb describe-regions
aliyun gpdb init-vector-database
aliyun gpdb create-document-collection
```

#### ❌ INCORRECT
```bash
# Wrong: Product name should be gpdb, not adbpg
aliyun adbpg describe-regions

# Wrong: Product name should be lowercase
aliyun GPDB describe-regions
```

### 1.2 Command Format Verification (Plugin Mode)

#### ✅ CORRECT - Plugin mode (lowercase with hyphens)
```bash
aliyun gpdb describe-regions
aliyun gpdb init-vector-database
aliyun gpdb create-namespace
aliyun gpdb create-document-collection
aliyun gpdb upload-document-async
aliyun gpdb query-content
```

#### ❌ INCORRECT - Traditional API mode (CamelCase)
```bash
# Wrong: Should use plugin mode with lowercase hyphens
aliyun gpdb DescribeRegions
aliyun gpdb InitVectorDatabase
aliyun gpdb CreateNamespace
aliyun gpdb CreateDocumentCollection
```

### 1.3 Parameter Name Format Verification

#### ✅ CORRECT - Lowercase with hyphens
```bash
aliyun gpdb create-document-collection \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin \
  --manager-account-password 'pass' \
  --collection my_kb \
  --embedding-model text-embedding-v4 \
  --dimension 1024
```

#### ❌ INCORRECT - CamelCase parameter names
```bash
# Wrong: Parameter names should be lowercase with hyphens
aliyun gpdb create-document-collection \
  --RegionId cn-hangzhou \
  --DBInstanceId gp-xxxxx \
  --ManagerAccount admin
```

### 1.4 User-Agent Must Be Present

#### ✅ CORRECT
```bash
aliyun gpdb describe-regions --user-agent AlibabaCloud-Agent-Skills
aliyun gpdb query-content --content "test" --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# Wrong: Missing --user-agent parameter
aliyun gpdb describe-regions
aliyun gpdb query-content --content "test"
```

---

## 2. Python SDK Code Pattern Verification

### 2.1 Import Paths

#### ✅ CORRECT
```python
from alibabacloud_gpdb20160503.client import Client
from alibabacloud_gpdb20160503 import models
from alibabacloud_tea_openapi.models import Config
from alibabacloud_tea_util.models import RuntimeOptions
```

#### ❌ INCORRECT
```python
# Wrong: Incorrect package name
from alibabacloud_gpdb.client import Client
from alibabacloud_adbpg.client import Client

# Wrong: Incorrect version number
from alibabacloud_gpdb20200101.client import Client
```

### 2.2 Credential Reading Method

#### ✅ CORRECT - Default credential chain (SDK)
```python
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_gpdb20160503.client import Client
from alibabacloud_tea_openapi.models import Config

client = Client(Config(
    credential=CredentialClient(),
    region_id='cn-hangzhou',
    endpoint='gpdb.aliyuncs.com',
    connect_timeout=10000,
    read_timeout=10000,
    user_agent='AlibabaCloud-Agent-Skills',
))
```

Do **not** parse `~/.aliyun/config.json` or pass raw `access_key_id` / `access_key_secret` from files in skill code; rely on `CredentialClient()` default resolution.

#### ❌ INCORRECT - Hardcoded credentials
```python
# Wrong: Never hardcode AK/SK
client = Client(Config(
    access_key_id='LTAI5tXXXXXXXXXX',
    access_key_secret='8dXXXXXXXXXXXXXXXXXXXX',
))
```

### 2.3 Local File Upload

#### ✅ CORRECT - Packaged script (recommended)

Use [scripts/upload_document_local.py](../scripts/upload_document_local.py): default credential chain, `user_agent='AlibabaCloud-Agent-Skills'`, and HTTP timeouts on `Config`.

#### ✅ CORRECT - Use Advance method (inline pattern)
```python
with open(file_path, 'rb') as f:
    request = models.UploadDocumentAsyncAdvanceRequest(
        region_id='cn-hangzhou',
        dbinstance_id='gp-xxxxx',
        namespace='ns_my_kb',
        namespace_password='<namespace-password>',
        collection='my_kb',
        file_name=os.path.basename(file_path),
        file_url_object=f,  # Pass file stream
        document_loader_name='ADBPGLoader',
    )
    response = client.upload_document_async_advance(request, RuntimeOptions())
```

#### ❌ INCORRECT - Regular upload method doesn't support local files
```python
# Wrong: Regular upload_document_async doesn't support local file streams
request = models.UploadDocumentAsyncRequest(
    file_url_object=f,  # This parameter doesn't exist in regular request
)
```

---

## 3. Workflow Verification

### 3.1 Knowledge Base Creation Order

#### ✅ CORRECT - Correct order
```
1. InitVectorDatabase (re-run may error if already initialized; handle per SKILL pre-checks)
2. CreateNamespace (MUST be before CreateDocumentCollection)
3. CreateDocumentCollection
```

#### ❌ INCORRECT - Wrong order
```
# Wrong: Creating Collection before Namespace will fail
1. CreateDocumentCollection
2. CreateNamespace
# Error: role "knowledgebasepub" does not exist
```

### 3.2 Namespace Rules

#### ✅ CORRECT
```bash
# Namespace name: ns_{collection}
--namespace ns_my_knowledge_base
--namespace ns_product_docs
```

#### ❌ INCORRECT
```bash
# Wrong: public namespace is forbidden
--namespace public

# Wrong: Namespace should have ns_ prefix
--namespace my_knowledge_base
```

---

## 4. Parameter Verification

### 4.1 Required Parameter Check

#### Create Knowledge Base Required Parameters

| Parameter | Required |
|-----------|----------|
| biz-region-id | ✅ |
| db-instance-id | ✅ |
| manager-account | ✅ |
| manager-account-password | ✅ |
| collection | ✅ |
| embedding-model | ✅ |
| dimension | ✅ |

#### Upload Document Required Parameters

| Parameter | Required |
|-----------|----------|
| biz-region-id | ✅ |
| db-instance-id | ✅ |
| namespace-password | ✅ |
| collection | ✅ |
| file-name | ✅ |
| file-url | ✅ |

### 4.2 Parameter Value Formats

#### ✅ CORRECT
```bash
# Instance ID format
--db-instance-id gp-bp1234567890

# Vector dimension (number)
--dimension 1024

# JSON format parameters
--entity-types '["Person","Organization"]'
--model-params '{"Model":"qwen-max","Messages":[...]}'
```

#### ❌ INCORRECT
```bash
# Wrong: Instance ID format error
--db-instance-id bp1234567890

# Wrong: Dimension is not a number
--dimension "1024"

# Wrong: JSON format error
--entity-types [Person,Organization]
```

---

## 5. Security Checks

### 5.1 Credential Security

#### ✅ CORRECT
```bash
# Only check credential status, don't output sensitive values
aliyun configure list
```

#### ❌ INCORRECT
```bash
# Wrong: Never output AK/SK values
echo $ALIBABA_CLOUD_ACCESS_KEY_ID
cat ~/.aliyun/config.json | grep access_key

# Wrong: Never pass AK directly in command line
aliyun configure set --access-key-id LTAI5tXXX --access-key-secret 8dXXX
```

### 5.2 Sensitive Information Prompts

#### ✅ CORRECT
- Prompt user "Password will be used for subsequent operations, please keep it safe"
- Don't display password in plaintext in logs or output

#### ❌ INCORRECT
- Display password in plaintext in output
- Write password to files or logs

---

## 6. Error Handling Checks

### 6.1 Common Error Responses

| Error | Correct Handling |
|-------|-----------------|
| Instance.NotSupportVector | Prompt user to upgrade instance or enable vector engine |
| role "knowledgebasepub" does not exist | Prompt to execute CreateNamespace first |
| Collection.NotFound | Prompt to check if knowledge base name is correct |
| Namespace.PasswordInvalid | Prompt to check namespace password |

### 6.2 Retry Strategy

#### ✅ CORRECT
- Auto-poll upload progress after uploading document, query every 5-10 seconds
- Maximum 30 polls (about 5 minutes)

#### ❌ INCORRECT
- Don't poll upload progress, user can't know if upload completed
- Poll interval too short (< 3 seconds), may trigger rate limiting

---

## Checklist

- [ ] CLI commands use plugin mode (lowercase with hyphens)
- [ ] All CLI commands include `--user-agent AlibabaCloud-Agent-Skills`
- [ ] Python SDK uses correct import paths
- [ ] Python SDK uses `CredentialClient()` default chain (no `~/.aliyun/config.json` parsing in skill code)
- [ ] Python SDK `Config` sets `user_agent='AlibabaCloud-Agent-Skills'` and reasonable `connect_timeout` / `read_timeout`
- [ ] Local file upload uses [scripts/upload_document_local.py](../scripts/upload_document_local.py) or equivalent pattern
- [ ] No hardcoded AK/SK
- [ ] Knowledge base creation follows correct order
- [ ] Namespace name uses `ns_` prefix
- [ ] public namespace is forbidden
- [ ] Sensitive information not output in plaintext
