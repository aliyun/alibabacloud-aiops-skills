# Acceptance Criteria — DataWorks Data Governance Tag Management

**Scenario**: DataWorks data asset tag management  
**Purpose**: Skill testing acceptance criteria — confirms correct and incorrect implementation patterns

---

## Correct SDK Code Patterns

### 1. Import Patterns

#### ✅ CORRECT
```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient  # Required for GET queries
```

#### ❌ INCORRECT
```python
import alibabacloud_dataworks_public20200518  # Do not use product-specific SDK
import aliyunsdkcore                          # Do not use legacy SDK
```

---

### 2. Authentication

#### ✅ CORRECT — Use CredentialClient; never hardcode AK/SK
```python
credential = CredentialClient()
config = open_api_models.Config(credential=credential)
config.endpoint = 'dataworks.cn-hangzhou.aliyuncs.com'
client = OpenApiClient(config)
```

#### ❌ INCORRECT — Hardcoded credentials
```python
config = open_api_models.Config(
    access_key_id='LTAI5t...',     # FORBIDDEN — never hardcode
    access_key_secret='xxxxx'      # FORBIDDEN — never hardcode
)
```

---

### 3. API Style Configuration

#### ✅ CORRECT — ROA style (Body parameters)
```python
params = open_api_models.Params(
    action='CreateDataAssetTag',
    version='2024-05-18',
    protocol='HTTPS',
    method='POST',
    auth_type='AK',
    style='ROA',                           # DataWorks Data Governance APIs use ROA style
    pathname='/api/v1/data-governance/tags',
    req_body_type='json',
    body_type='json'
)
request = open_api_models.OpenApiRequest(body={'Key': 'k1'})
```

#### ❌ INCORRECT — Misusing RPC style
```python
params = open_api_models.Params(
    style='RPC',
    pathname='/',                           # RPC path — not applicable to DataWorks Data Governance APIs
)
```

---

### 4. GET Request (ListDataAssetTags / ListDataAssets)

#### ✅ CORRECT — Use OpenApiUtilClient.query() for query parameters
```python
queries = {'PageNumber': 1, 'PageSize': 10, 'Key': 'test'}
request = open_api_models.OpenApiRequest(
    query=OpenApiUtilClient.query(queries)
)
```

#### ✅ CORRECT — ListDataAssets with JSON-serialized Tags and Ids
```python
import json
queries = {
    'Type': 'Table',
    'Tags': json.dumps([{"Key": "k1", "Value": "v1"}]),  # Must be JSON string
    'Ids': json.dumps(["maxcompute-table.a123.test"]),    # Must be JSON string
    'PageNumber': 1,
    'PageSize': 10
}
request = open_api_models.OpenApiRequest(
    query=OpenApiUtilClient.query(queries)
)
```

#### ❌ INCORRECT — Placing query parameters in the body
```python
request = open_api_models.OpenApiRequest(
    body={'PageNumber': 1, 'PageSize': 10}  # GET requests must not put pagination params in body
)
```

#### ❌ INCORRECT — Passing Tags/Ids as Python objects without JSON serialization
```python
queries = {
    'Type': 'Table',
    'Tags': [{"Key": "k1", "Value": "v1"}],  # Must be json.dumps(...)
}
```

---

### 5. Batch Operation Limits

#### ✅ CORRECT — Respect the limits
```python
# Tags max 20, DataAssetIds max 100
assert len(tags) <= 20, "Tags exceed the limit of 20"
assert len(data_asset_ids) <= 100, "DataAssetIds exceed the limit of 100"
tag_data_assets(client, tags=tags[:20], data_asset_ids=data_asset_ids[:100], ...)
```

#### ❌ INCORRECT — Ignoring limits
```python
tag_data_assets(client, tags=all_tags, data_asset_ids=all_ids, ...)  # May exceed limits
```

---

### 6. Forbidden API — DeleteDataAssetTag

#### ❌ FORBIDDEN — Do not call DeleteDataAssetTag under any circumstances
```python
# This API is strictly prohibited in this skill.
# Do not implement, suggest, or invoke DeleteDataAssetTag.
delete_data_asset_tag(client, key='k1')              # FORBIDDEN
delete_data_asset_tag(client, key='k1', values=['v1'])  # FORBIDDEN
```

If a user requests deletion of a tag key or tag value, respond that this operation is outside
the scope of this skill and must be handled through other authorized channels.

---

### 7. Task-Type Assets — Required Parameters

#### ✅ CORRECT — Provide project_id and env_type for Task assets
```python
tag_data_assets(
    client,
    tags=[{"Key": "k1", "Value": "v1"}],
    data_asset_ids=["task-id-xxx"],
    data_asset_type="ACS::DataWorks::Task",
    project_id=131011,   # Required for Task type
    env_type="Prod"      # Required when project_id is set
)
```

#### ❌ INCORRECT — Missing project_id for Task type
```python
tag_data_assets(
    client,
    tags=[{"Key": "k1", "Value": "v1"}],
    data_asset_ids=["task-id-xxx"],
    data_asset_type="ACS::DataWorks::Task"
    # Missing project_id and env_type — will cause an API error
)
```

---

### 8. Response Handling

#### ✅ CORRECT — Check both statusCode and Data field
```python
body = response.get('body', {})
if response.get('statusCode') == 200 and body.get('Data') == True:
    print("Operation succeeded")
else:
    raise Exception(f"Failed: Code={body.get('Code')}, Message={body.get('Message')}")
```

#### ❌ INCORRECT — Ignoring the response
```python
response = client.call_api(params, request, runtime)
print("done")  # Never skip response validation
```
