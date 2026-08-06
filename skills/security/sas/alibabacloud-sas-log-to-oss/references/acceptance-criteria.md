# Acceptance Criteria: alibabacloud-sas-log-to-oss

**Scenario**: SLS log export to OSS cold storage
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. List LogStores

#### ✅ CORRECT
```bash
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py list-logstores \
  --project my-sls-project
```

#### ❌ INCORRECT
```bash
# Error: missing required --project parameter
python3 scripts/sls_oss_export.py list-logstores

# Error: using old default project name (removed)
python3 scripts/sls_oss_export.py list-logstores --project aliyun-cloudsiem-data-xxx
```

## 2. Create Export Task

#### ✅ CORRECT
```bash
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py create-export \
  --project my-sls-project \
  --logstore my-logstore \
  --name export-my-logstore-to-oss \
  --bucket my-oss-bucket
```

#### ❌ INCORRECT
```bash
# Error: task name contains uppercase (must be lowercase letters, digits, hyphens, underscores)
python3 scripts/sls_oss_export.py create-export \
  --project my-sls-project --logstore my-logstore \
  --name Export-My-LogStore --bucket my-bucket

# Error: missing --bucket parameter
python3 scripts/sls_oss_export.py create-export \
  --project my-sls-project --logstore my-logstore --name export-test
```

## 3. Batch Create

#### ✅ CORRECT
```bash
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py batch-create \
  --project my-sls-project \
  --bucket my-oss-bucket \
  --prefix sls-export/
```

#### ❌ INCORRECT
```bash
# Error: missing --bucket parameter
python3 scripts/sls_oss_export.py batch-create --project my-sls-project
```

# Correct Common SDK Code Patterns

## 1. Import Patterns

#### ✅ CORRECT
```python
from alibabacloud_sls20201230.client import Client
from alibabacloud_sls20201230 import models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_credentials.client import Client as CredentialClient
```

#### ❌ INCORRECT
```python
# Error: using AK/SK directly instead of CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
config = open_api_models.Config(
    access_key_id=ak,        # should not hardcode
    access_key_secret=sk,    # should not hardcode
)
```

## 2. Authentication — must use CredentialClient, never hardcode AK/SK

#### ✅ CORRECT
```python
credential = CredentialClient()
config = open_api_models.Config(
    credential=credential,
    endpoint='cn-hangzhou.log.aliyuncs.com',
    user_agent=_build_user_agent(),
)
client = Client(config)
```

#### ❌ INCORRECT
```python
# Error: hardcoded credentials
config = open_api_models.Config(
    access_key_id='LTAIxxxxxxxx',
    access_key_secret='xxxxxxxxxxxx',
)
```

## 3. Observability — must include user_agent

#### ✅ CORRECT
```python
SKILL_NAME = 'alibabacloud-sas-log-to-oss'
SESSION_ID = os.environ.get('SKILL_SESSION_ID', '')
ua = f'AlibabaCloud-Agent-Skills/{SKILL_NAME}'
if SESSION_ID:
    ua = f'{ua}/{SESSION_ID}'

config = open_api_models.Config(
    credential=credential,
    endpoint=endpoint,
    user_agent=ua,
)
```

#### ❌ INCORRECT
```python
# Error: user_agent not set, cannot be tracked
config = open_api_models.Config(
    credential=credential,
    endpoint=endpoint,
)
```

## 4. Environment Variable Naming

#### ✅ CORRECT
```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-ak>
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-sk>
export ALIBABA_CLOUD_ACCOUNT_ID=<your-account-id>
```

#### ❌ INCORRECT
```bash
# Error: environment variable name missing underscore (CredentialClient cannot recognize)
export ALIBABACLOUD_ACCESS_KEY_ID=<your-ak>
export ALIBABACLOUD_ACCESS_KEY_SECRET=<your-sk>
export ALIBABACLOUD_ACCOUNT_ID=<your-account-id>
```
