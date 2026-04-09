# Acceptance Criteria: alibabacloud-elasticsearch-network-manage

**Scenario**: Elasticsearch Instance Network Management
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — verify product name exists

✅ **CORRECT**: `elasticsearch`

```bash
aliyun elasticsearch trigger-network
```

❌ **INCORRECT**: `es`, `elastic`, `Elasticsearch`

```bash
# Incorrect examples
aliyun es trigger-network           # Wrong product name
aliyun elastic trigger-network      # Wrong product name
aliyun Elasticsearch trigger-network # Case error
```

---

## 2. Command — verify action exists under the product

### TriggerNetwork

✅ **CORRECT**:
```bash
aliyun elasticsearch trigger-network --instance-id es-cn-xxx --vpc-id vpc-xxx --vswitch-id vsw-xxx
```

❌ **INCORRECT**:
```bash
aliyun elasticsearch TriggerNetwork --instance-id es-cn-xxx      # Should use lowercase hyphen format
aliyun elasticsearch trigger-networks --instance-id es-cn-xxx    # Plural form is wrong
aliyun elasticsearch triggerNetwork --instance-id es-cn-xxx      # Camel case is wrong
```

### EnableKibanaPvlNetwork

✅ **CORRECT**:
```bash
aliyun elasticsearch enable-kibana-pvl-network --instance-id es-cn-xxx
```

❌ **INCORRECT**:
```bash
aliyun elasticsearch EnableKibanaPvlNetwork --instance-id es-cn-xxx  # Should use lowercase hyphen
aliyun elasticsearch enable-kibana-pvl --instance-id es-cn-xxx       # Incomplete command
```

### DisableKibanaPvlNetwork

✅ **CORRECT**:
```bash
aliyun elasticsearch disable-kibana-pvl-network --instance-id es-cn-xxx
```

❌ **INCORRECT**:
```bash
aliyun elasticsearch DisableKibanaPvlNetwork --instance-id es-cn-xxx  # Should use lowercase hyphen
aliyun elasticsearch close-kibana-pvl --instance-id es-cn-xxx         # Wrong verb
```

### UpdateKibanaPvlNetwork

✅ **CORRECT**:
```bash
aliyun elasticsearch update-kibana-pvl-network --instance-id es-cn-xxx --pvl-id es-cn-xxx-kibana-internal-internal --body '{"securityGroups": ["sg-xxx"]}'
```

❌ **INCORRECT**:
```bash
aliyun elasticsearch UpdateKibanaPvlNetwork --instance-id es-cn-xxx   # Should use lowercase hyphen
aliyun elasticsearch update-kibana-pvl --instance-id es-cn-xxx         # Incomplete command
```

### ModifyWhiteIps

✅ **CORRECT**:
```bash
aliyun elasticsearch modify-white-ips --instance-id es-cn-xxx --body '{...}'
```

❌ **INCORRECT**:
```bash
aliyun elasticsearch ModifyWhiteIps --instance-id es-cn-xxx      # Should use lowercase hyphen
aliyun elasticsearch modify-white-ip --instance-id es-cn-xxx     # Singular form is wrong
aliyun elasticsearch update-white-ips --instance-id es-cn-xxx    # Wrong verb
```

### OpenHttps

✅ **CORRECT**:
```bash
aliyun elasticsearch open-https --instance-id es-cn-xxx
```

❌ **INCORRECT**:
```bash
aliyun elasticsearch OpenHttps --instance-id es-cn-xxx      # Should use lowercase hyphen
aliyun elasticsearch enable-https --instance-id es-cn-xxx   # Wrong verb
```

### CloseHttps

✅ **CORRECT**:
```bash
aliyun elasticsearch close-https --instance-id es-cn-xxx
```

❌ **INCORRECT**:
```bash
aliyun elasticsearch CloseHttps --instance-id es-cn-xxx      # Should use lowercase hyphen
aliyun elasticsearch disable-https --instance-id es-cn-xxx   # Wrong verb
```

### DescribeInstance

✅ **CORRECT**:
```bash
aliyun elasticsearch describe-instance --instance-id es-cn-xxx
```

❌ **INCORRECT**:
```bash
aliyun elasticsearch DescribeInstance --instance-id es-cn-xxx  # Should use lowercase hyphen
aliyun elasticsearch get-instance --instance-id es-cn-xxx      # Wrong verb
```

---

## 3. Parameters — verify each parameter name exists for the command

### --instance-id

✅ **CORRECT**:
```bash
aliyun elasticsearch trigger-network --instance-id es-cn-xxx --vpc-id vpc-xxx --vswitch-id vsw-xxx
```

❌ **INCORRECT**:
```bash
aliyun elasticsearch trigger-network --InstanceId es-cn-xxx    # Camel case is wrong
aliyun elasticsearch trigger-network --instanceId es-cn-xxx    # Lower camel case is wrong
aliyun elasticsearch trigger-network --id es-cn-xxx            # Wrong parameter name
```

### --vpc-id

✅ **CORRECT**:
```bash
aliyun elasticsearch trigger-network --vpc-id vpc-xxxxxx
```

❌ **INCORRECT**:
```bash
aliyun elasticsearch trigger-network --vpcId vpc-xxxxxx        # Camel case is wrong
aliyun elasticsearch trigger-network --vpc vpc-xxxxxx          # Wrong parameter name
```

### --vswitch-id

✅ **CORRECT**:
```bash
aliyun elasticsearch trigger-network --vswitch-id vsw-xxxxxx
```

❌ **INCORRECT**:
```bash
aliyun elasticsearch trigger-network --vswitchId vsw-xxxxxx    # Camel case is wrong
aliyun elasticsearch trigger-network --vsw-id vsw-xxxxxx       # Wrong parameter name
```

### --pvl-id

✅ **CORRECT**:
```bash
aliyun elasticsearch update-kibana-pvl-network --pvl-id es-cn-xxx-kibana-internal-internal
```

❌ **INCORRECT**:
```bash
aliyun elasticsearch update-kibana-pvl-network --pvlId es-cn-xxx-kibana-internal-internal   # Camel case is wrong
aliyun elasticsearch update-kibana-pvl-network --pvl es-cn-xxx-kibana-internal-internal      # Wrong parameter name
```

### --white-ip-type

✅ **CORRECT**:
```bash
aliyun elasticsearch modify-white-ips --white-ip-type PRIVATE_ES
```

❌ **INCORRECT**:
```bash
aliyun elasticsearch modify-white-ips --whiteIpType PRIVATE_ES     # Camel case is wrong
aliyun elasticsearch modify-white-ips --ip-type PRIVATE_ES         # Wrong parameter name
```

### --body (RequestBody)

✅ **CORRECT**:
```bash
aliyun elasticsearch modify-white-ips \
  --instance-id es-cn-xxx \
  --body '{"whiteIpGroup": [{"groupName": "default", "ips": ["192.168.0.0/16"]}]}'
```

❌ **INCORRECT**:
```bash
# JSON format error
aliyun elasticsearch modify-white-ips --instance-id es-cn-xxx \
  --body {whiteIpGroup: [{groupName: default}]}  # Missing quotes and correct format
```

### --resource-group-id

✅ **CORRECT**:
```bash
aliyun elasticsearch trigger-network --resource-group-id rg-xxxxxx
```

❌ **INCORRECT**:
```bash
aliyun elasticsearch trigger-network --resourceGroupId rg-xxxxxx   # Camel case is wrong
aliyun elasticsearch trigger-network --rg-id rg-xxxxxx             # Wrong parameter name
```

---

## 4. --user-agent flag present

✅ **CORRECT** — Every command must include `--user-agent AlibabaCloud-Agent-Skills`:
```bash
aliyun elasticsearch trigger-network --instance-id es-cn-xxx --vpc-id vpc-xxx --vswitch-id vsw-xxx --user-agent AlibabaCloud-Agent-Skills
aliyun elasticsearch enable-kibana-pvl-network --instance-id es-cn-xxx --user-agent AlibabaCloud-Agent-Skills
aliyun elasticsearch modify-white-ips --instance-id es-cn-xxx --body '{...}' --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT** — Missing user-agent:
```bash
aliyun elasticsearch trigger-network --instance-id es-cn-xxx --vpc-id vpc-xxx --vswitch-id vsw-xxx  # Missing --user-agent
```

---

## 5. Architecture Type Check

✅ **CORRECT** — Check architecture type before executing TriggerNetwork for Kibana private network:
```bash
# Check instance architecture type
arch_type=$(aliyun elasticsearch describe-instance --instance-id es-cn-xxx --user-agent AlibabaCloud-Agent-Skills | jq -r '.Result.archType')

if [ "$arch_type" == "public" ] && [ "$node_type" == "KIBANA" ] && [ "$network_type" == "PRIVATE" ]; then
  echo "Cloud-native instance does not support TriggerNetwork for Kibana private network"
  exit 1
fi

# Execute TriggerNetwork
aliyun elasticsearch trigger-network --instance-id es-cn-xxx --body '{"nodeType":"WORKER","networkType":"PUBLIC","actionType":"OPEN"}' --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT** — Execute without checking architecture type:
```bash
# Error: Did not check archType
aliyun elasticsearch trigger-network --instance-id es-cn-xxx --body '{"nodeType":"WORKER","networkType":"PUBLIC","actionType":"OPEN"}' --user-agent AlibabaCloud-Agent-Skills
```

---

# Correct Common SDK Code Patterns (if applicable)

## 1. Import Patterns

✅ **CORRECT**:
```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
import alibabacloud_tea_openapi.models as open_api_models
```

❌ **INCORRECT**:
```python
# Wrong import path
from aliyunsdkcore.client import AcsClient  # Legacy SDK
from alibabacloud_elasticsearch import Client  # Product-specific SDK not applicable for ROA style API
```

## 2. Authentication — must use CredentialClient, never hardcode AK/SK

✅ **CORRECT**:
```python
from alibabacloud_credentials.client import Client as CredentialClient

credential = CredentialClient()
config = open_api_models.Config(
    credential=credential,
    endpoint="elasticsearch.cn-hangzhou.aliyuncs.com"
)
client = OpenApiClient(config)
```

❌ **INCORRECT**:
```python
# Hardcoded credentials - strictly forbidden!
config = open_api_models.Config(
    access_key_id="LTAI4xxx",
    access_key_secret="xxx"
)

# Reading from environment variables directly - not recommended
import os
config = open_api_models.Config(
    access_key_id=os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID"),
    access_key_secret=os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
)
```

## 3. Client Initialization

✅ **CORRECT**:
```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
import alibabacloud_tea_openapi.models as open_api_models

credential = CredentialClient()
config = open_api_models.Config(
    credential=credential,
    endpoint="elasticsearch.cn-hangzhou.aliyuncs.com"
)
client = OpenApiClient(config)
```

## 4. API Call Pattern (ROA Style)

Elasticsearch API uses ROA style, which differs from RPC style:

✅ **CORRECT**:
```python
import alibabacloud_tea_openapi.models as open_api_models
from alibabacloud_tea_util.models import RuntimeOptions

# Construct ROA request
params = open_api_models.Params(
    action="TriggerNetwork",
    version="2017-06-13",
    protocol="HTTPS",
    method="POST",
    auth_type="AK",
    style="ROA",
    pathname=f"/openapi/instances/{instance_id}/actions/network-trigger",
    req_body_type="json",
    body_type="json"
)

request = open_api_models.OpenApiRequest()
runtime = RuntimeOptions()

response = client.call_api(params, request, runtime)
```

---

# Error Handling Patterns

## Correct Error Handling

✅ **CORRECT**:
```python
from Tea.exceptions import TeaException

try:
    response = client.call_api(params, request, runtime)
except TeaException as e:
    print(f"Error Code: {e.code}")
    print(f"Error Message: {e.message}")
    print(f"Request ID: {e.data.get('RequestId', 'N/A')}")
```

❌ **INCORRECT**:
```python
# Not handling exceptions
response = client.call_api(params, request, runtime)

# Exception catch too broad
try:
    response = client.call_api(params, request, runtime)
except:  # Catching all exceptions
    pass
```

---

# Summary Checklist

- [ ] CLI commands use lowercase hyphen format (e.g., `trigger-network`, not `TriggerNetwork`)
- [ ] Product name uses `elasticsearch`
- [ ] Parameter names use lowercase hyphen format (e.g., `--instance-id`, not `--InstanceId`)
- [ ] Every command includes `--user-agent AlibabaCloud-Agent-Skills`
- [ ] JSON parameters use correct format and quotes
- [ ] Check archType field before executing TriggerNetwork
- [ ] SDK uses CredentialClient for authentication, no hardcoded credentials
- [ ] SDK uses ROA style to call Elasticsearch API
- [ ] Properly handle API call exceptions
