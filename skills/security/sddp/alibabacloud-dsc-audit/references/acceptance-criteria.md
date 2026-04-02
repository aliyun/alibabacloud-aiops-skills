# Acceptance Criteria: alibabacloud-dsc-audit

**Scenario**: Data Security Center Security Risk Event Query and Handling
**Purpose**: Skill test acceptance criteria

---

## Correct Common SDK Code Patterns

### 1. Import Pattern

#### ✅ CORRECT

```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient  # Required for RPC style
```

#### ❌ INCORRECT

```python
# Error: Using legacy SDK
from aliyunsdkcore.client import AcsClient
from aliyunsdksddp.request.v20190103 import DescribeRiskRulesRequest

# Error: Missing OpenApiUtilClient (required for RPC style)
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
# Missing OpenApiUtilClient
```

### 2. Authentication Pattern

#### ✅ CORRECT

```python
# Use CredentialClient, do not hardcode AK/SK
credential = CredentialClient()
config = open_api_models.Config(credential=credential)
config.endpoint = 'sddp.cn-zhangjiakou.aliyuncs.com'
client = OpenApiClient(config)
```

#### ❌ INCORRECT

```python
# Error: Hardcoded AK/SK
config = open_api_models.Config(
    access_key_id='LTAI5tXXXXXXXX',
    access_key_secret='8dXXXXXXXXXXXXXXXXXXXXXXXX'
)

# Error: Using string instead of CredentialClient
config = open_api_models.Config(credential='my-credential')
```

### 3. API Parameter Configuration (RPC Style)

#### ✅ CORRECT

```python
params = open_api_models.Params(
    action='DescribeRiskRules',
    version='2019-01-03',
    protocol='HTTPS',
    method='POST',
    auth_type='AK',
    style='RPC',
    pathname='/',           # Fixed as '/' for RPC style
    req_body_type='json',
    body_type='json'
)
```

#### ❌ INCORRECT

```python
# Error: RPC style using custom pathname
params = open_api_models.Params(
    action='DescribeRiskRules',
    version='2019-01-03',
    style='RPC',
    pathname='/risk/rules',  # RPC style should be '/'
)

# Error: Using ROA style
params = open_api_models.Params(
    action='DescribeRiskRules',
    version='2019-01-03',
    style='ROA',  # Should be RPC
)
```

### 4. Request Building (RPC Style)

#### ✅ CORRECT

```python
# RPC style uses query parameters, must use OpenApiUtilClient.query()
queries = {
    'CurrentPage': 1,
    'PageSize': 10,
    'HandleStatus': 'UNPROCESSED'
}
request = open_api_models.OpenApiRequest(
    query=OpenApiUtilClient.query(queries)
)
```

#### ❌ INCORRECT

```python
# Error: RPC style using body parameters
request = open_api_models.OpenApiRequest(
    body={'CurrentPage': 1, 'PageSize': 10}
)

# Error: Not using OpenApiUtilClient.query()
request = open_api_models.OpenApiRequest(
    query={'CurrentPage': 1, 'PageSize': 10}
)
```

### 5. Complex Parameter Handling (Flat Mode)

#### ✅ CORRECT

```python
# Use flat mode for complex objects
queries = {
    'RiskId': 75110196,
    'HandleInfoList.1.HandleType': 'Manual',
    'HandleInfoList.1.HandleContent': json.dumps({
        'HandleMethod': 0,
        'HandleDetail': 'Handling description'
    })
}
```

#### ❌ INCORRECT

```python
# Error: Directly passing nested objects
queries = {
    'RiskId': 75110196,
    'HandleInfoList': [
        {
            'HandleType': 'Manual',
            'HandleContent': {
                'HandleMethod': 0,
                'HandleDetail': 'Handling description'
            }
        }
    ]
}
```

### 6. API Call

#### ✅ CORRECT

```python
runtime = util_models.RuntimeOptions()
response = client.call_api(params, request, runtime)

# Check response
status_code = response.get('statusCode')
body = response.get('body')

if status_code == 200:
    items = body.get('Items', [])
```

#### ❌ INCORRECT

```python
# Error: Missing runtime options
response = client.call_api(params, request)

# Error: Not checking status code
body = response.get('body')
items = body['Items']  # May throw KeyError
```

---

## Service Configuration Validation

### ✅ CORRECT

| Configuration | Correct Value |
|---------------|---------------|
| Product Code | Sddp |
| Endpoint | sddp.cn-zhangjiakou.aliyuncs.com |
| API Version | 2019-01-03 |
| API Style | RPC |

### ❌ INCORRECT

| Error Case | Description |
|------------|-------------|
| Wrong endpoint | Using `sddp.aliyuncs.com` instead of `sddp.cn-zhangjiakou.aliyuncs.com` |
| Wrong version | Using incorrect version number |
| Wrong style | Using ROA instead of RPC |

---

## API Restriction Validation

### ✅ CORRECT

This skill **only** uses the following two APIs:
- `DescribeRiskRules` - Query security risk events
- `PreHandleAuditRisk` - Handle security risk events

### ❌ INCORRECT

Calling other unauthorized APIs:
- `DescribeDataAssets`
- `DescribeRules`
- Any other Data Security Center APIs

---

## Pagination Query Validation

### ✅ CORRECT

```python
def fetch_all_risk_rules():
    all_items = []
    current_page = 1
    
    while True:
        response = describe_risk_rules(current_page)
        body = response.get('body', {})
        items = body.get('Items', [])
        all_items.extend(items)
        
        total_count = body.get('TotalCount', 0)
        if current_page * page_size >= total_count:
            break
        
        current_page += 1
    
    return all_items
```

### ❌ INCORRECT

```python
# Error: Only fetching first page, ignoring subsequent pages
def fetch_risk_rules():
    response = describe_risk_rules(current_page=1)
    return response.get('body', {}).get('Items', [])
```

---

## Required Field Validation

### Query Results Must Include RiskId

#### ✅ CORRECT

```python
for item in items:
    risk_id = item.get('RiskId')  # Must display
    print(f"Risk ID: {risk_id}")    # Required for handling
```

#### ❌ INCORRECT

```python
# Error: Not displaying RiskId
for item in items:
    print(f"Rule Name: {item.get('RuleName')}")
    # Missing RiskId, user cannot perform handling operations
```
