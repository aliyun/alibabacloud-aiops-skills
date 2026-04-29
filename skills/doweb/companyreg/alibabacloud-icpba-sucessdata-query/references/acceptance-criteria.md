# Acceptance Criteria: alibabacloud-icpba-sucessdata-query

**Scenario**: ICP Filing Success Data Query
**Purpose**: Skill testing acceptance criteria

---

## Correct Python Common SDK Code Patterns

Since the CLI command is not yet available, this skill uses Python Common SDK exclusively.

### 1. Import Patterns

#### ✅ CORRECT

```python
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
```

**Why**: These are the correct import paths for Alibaba Cloud Python Common SDK.

#### ❌ INCORRECT

```python
# Don't use old SDK imports
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

# Don't use wrong module names
from alibabacloud_openapi import Client
from tea_openapi import models
```

**Why**:
- Old SDK (`aliyunsdkcore`) is deprecated
- Wrong module names will cause ImportError

---

### 2. Authentication — Must Use CredentialClient

#### ✅ CORRECT

```python
from alibabacloud_credentials.client import Client as CredentialClient

credential = CredentialClient()
config = open_api_models.Config(
    credential=credential,
    endpoint='companyreg.aliyuncs.com'
)
```

**Why**: `CredentialClient` automatically discovers credentials from multiple sources (env vars, config file, ECS role).

#### ❌ INCORRECT

```python
# Never hardcode credentials
config = open_api_models.Config(
    access_key_id='LTAI...',
    access_key_secret='xxxxx...'
)

# Don't manually construct credentials
credential = {
    'accessKeyId': 'LTAI...',
    'accessKeySecret': 'xxxxx...'
}
```

**Why**:
- Security risk (credentials in code)
- Violates best practices
- Will fail skill validation

---

### 3. Client Configuration — Correct Endpoint

#### ✅ CORRECT

```python
config = open_api_models.Config(
    credential=credential,
    endpoint='companyreg.aliyuncs.com',  # Correct endpoint
    region_id='cn-hangzhou'               # Valid region
)

client = OpenApiClient(config)
```

**Why**: This is the correct endpoint for the Beian API operations.

#### ❌ INCORRECT

```python
# Wrong endpoint
config = open_api_models.Config(
    credential=credential,
    endpoint='beian.aliyuncs.com',  # Wrong endpoint
)

# Missing endpoint
config = open_api_models.Config(
    credential=credential,
    region_id='cn-hangzhou'
)
```

**Why**:
- `beian.aliyuncs.com` doesn't exist
- Endpoint must be explicitly set to `companyreg.aliyuncs.com`

---

### 4. API Parameters — Correct Structure

#### ✅ CORRECT

```python
params = open_api_models.Params(
    action='QuerySuccessIcpData',  # Correct action name
    version='2026-04-23',           # Correct API version
    protocol='HTTPS',
    method='POST',
    auth_type='AK',
    style='RPC',
    pathname='/',
    req_body_type='formData',
    body_type='json'
)
```

**Why**: All fields are correctly set according to API specification.

#### ❌ INCORRECT

```python
# Wrong action name
params = open_api_models.Params(
    action='QueryIcpData',  # Missing 'Success' in name
    version='2026-04-23',
)

# Wrong version
params = open_api_models.Params(
    action='QuerySuccessIcpData',
    version='2021-01-01',  # Wrong version
)

# Wrong protocol/method
params = open_api_models.Params(
    action='QuerySuccessIcpData',
    version='2026-04-23',
    protocol='HTTP',   # Should be HTTPS
    method='GET',      # Should be POST
)
```

**Why**:
- Wrong action name will return "API not found"
- Wrong version will fail
- Wrong protocol/method won't match API specification

---

### 5. Request Parameters — Required Fields

#### ✅ CORRECT

```python
queries = {
    'Caller': 'skill'  # Required parameter with correct value
}

request = open_api_models.OpenApiRequest(
    query=queries
)
```

**Why**: `Caller` is a required parameter and must be set to 'skill'.

#### ❌ INCORRECT

```python
# Missing required parameter
queries = {}
request = open_api_models.OpenApiRequest(
    query=queries
)

# Wrong parameter name
queries = {
    'CallerId': 'skill'  # Wrong field name
}

# Wrong parameter value
queries = {
    'Caller': 'user'  # Should be 'skill'
}

# Wrong parameter type
queries = {
    'Caller': None  # Should be string 'skill'
}
```

**Why**:
- API will return "MissingParameter" error
- Wrong field name won't be recognized
- Parameter must be exactly 'skill'

---

### 6. Runtime Options — Proper Configuration

#### ✅ CORRECT

```python
runtime = util_models.RuntimeOptions()
response = client.call_api(params, request, runtime)
```

**Why**: `RuntimeOptions` from `util_models` is the correct class.

#### ❌ INCORRECT

```python
# Wrong import
from alibabacloud_tea_openapi import models as util_models
runtime = util_models.RuntimeOptions()

# Missing runtime parameter
response = client.call_api(params, request)

# Wrong runtime type
runtime = {}
response = client.call_api(params, request, runtime)
```

**Why**:
- Wrong import will cause AttributeError
- API call requires runtime parameter
- Runtime must be RuntimeOptions instance

---

### 7. Response Handling — Proper Access

#### ✅ CORRECT

```python
response = client.call_api(params, request, runtime)
body = response.get('body', {})

if body.get('Success'):
    ba_list = body.get('BaSuccessDataWithRiskList', [])
    for ba_data in ba_list:
        icp_number = ba_data.get('IcpNumber')
```

**Why**: Safe access with `.get()` method prevents KeyError.

#### ❌ INCORRECT

```python
# Direct access without checking
response = client.call_api(params, request, runtime)
body = response['body']  # May raise KeyError
ba_list = body['BaSuccessDataWithRiskList']

# Not checking Success field
ba_list = body.get('BaSuccessDataWithRiskList', [])
for ba_data in ba_list:  # May iterate over empty/invalid data
    icp_number = ba_data['IcpNumber']  # May raise KeyError
```

**Why**:
- Response might not have 'body' if error occurs
- Should check 'Success' field before processing
- Direct dictionary access can raise KeyError

---

### 8. Error Handling — Comprehensive Patterns

#### ✅ CORRECT

```python
from Tea.exceptions import TeaException

try:
    response = client.call_api(params, request, runtime)
    body = response.get('body', {})
    return body
except TeaException as e:
    print(f"API Error: {e.code} - {e.message}")
    raise
except Exception as e:
    print(f"Unexpected error: {str(e)}")
    raise
```

**Why**: Proper exception handling with specific error types.

#### ❌ INCORRECT

```python
# Bare except clause
try:
    response = client.call_api(params, request, runtime)
    return response['body']
except:  # Too broad
    print("Error occurred")
    return None

# Ignoring errors
try:
    response = client.call_api(params, request, runtime)
    return response['body']
except Exception:
    pass  # Silent failure
```

**Why**:
- Bare except catches everything including system exits
- Silent failures hide important errors
- Should distinguish between API errors and other errors

---

### 9. Response Structure Validation

#### ✅ CORRECT

```python
result = query_success_icp_data(caller='skill')

# Validate top-level structure
assert 'Success' in result
assert 'BaSuccessDataWithRiskList' in result

if result['Success']:
    # Validate data structure
    for ba_data in result.get('BaSuccessDataWithRiskList', []):
        assert 'IcpNumber' in ba_data
        assert 'OrganizersName' in ba_data
        assert 'WebsiteList' in ba_data
        assert 'AppList' in ba_data
        assert 'RiskList' in ba_data
```

**Why**: Validates response structure before processing.

#### ❌ INCORRECT

```python
result = query_success_icp_data(caller='skill')

# No validation
ba_list = result['BaSuccessDataWithRiskList']
first_icp = ba_list[0]['IcpNumber']  # May fail if empty or missing

# Incorrect field names
for ba_data in ba_list:
    icp = ba_data['ICP_Number']  # Wrong field name (should be IcpNumber)
    websites = ba_data['Websites']  # Wrong field name (should be WebsiteList)
```

**Why**:
- No validation can lead to runtime errors
- Field names are case-sensitive and must match exactly

---

### 10. Data Extraction Patterns

#### ✅ CORRECT

```python
# Safe extraction with defaults
def extract_website_info(response: dict) -> list:
    websites = []

    if not response.get('Success'):
        return websites

    for ba_data in response.get('BaSuccessDataWithRiskList', []):
        for site in ba_data.get('WebsiteList', []):
            website = {
                'site_name': site.get('SiteName', ''),
                'domains': site.get('DomainList', []),
                'responsible_person': site.get('ResponsiblePersonName', '')
            }
            websites.append(website)

    return websites
```

**Why**: Safe extraction with default values prevents errors.

#### ❌ INCORRECT

```python
# Unsafe extraction
def extract_website_info(response):
    websites = []

    for ba_data in response['BaSuccessDataWithRiskList']:
        for site in ba_data['WebsiteList']:
            website = {
                'site_name': site['SiteName'],
                'domains': site['DomainList'],
            }
            websites.append(website)

    return websites
```

**Why**:
- No check for Success field
- Direct dictionary access can raise KeyError
- No default values for missing fields

---

## API Response Field Names

### ✅ CORRECT Field Names

```python
# Top-level fields
response['Success']
response['RequestId']
response['BaSuccessDataWithRiskList']

# Entity fields
ba_data['IcpNumber']
ba_data['OrganizersName']
ba_data['OrganizersNature']
ba_data['ResponsiblePersonName']

# Website fields
site['SiteRecordNum']
site['SiteName']
site['DomainList']
site['ResponsiblePersonName']

# APP fields
app['AppRecordNum']
app['AppName']
app['DomainList']
app['ResponsiblePersonName']

# Risk fields
risk['DeadLine']
risk['RiskDetailList']
detail['RiskSource']
detail['rectifySuggest']  # Note: lowercase 'rectify'
```

### ❌ INCORRECT Field Names

```python
# Wrong capitalization or spelling
response['success']              # Should be 'Success'
response['request_id']           # Should be 'RequestId'
ba_data['ICP_Number']           # Should be 'IcpNumber'
ba_data['OrganizationName']     # Should be 'OrganizersName'
site['SiteRecord']              # Should be 'SiteRecordNum'
site['Domains']                 # Should be 'DomainList'
risk['Deadline']                # Should be 'DeadLine'
detail['RectifySuggest']        # Should be 'rectifySuggest'
```

---

## Common Anti-Patterns to Avoid

### ❌ 1. Hardcoding Credentials

```python
# NEVER do this
access_key_id = 'LTAI...'
access_key_secret = 'xxxxx...'
```

### ❌ 2. Using Synchronous Code in Async Context

```python
# If using async, use proper async patterns
async def query():
    result = query_success_icp_data()  # Blocking call in async function
```

### ❌ 3. Not Handling Empty Arrays

```python
# Assuming arrays are not empty
websites = ba_data['WebsiteList']
first_website = websites[0]  # May fail if empty
```

### ❌ 4. Ignoring Risk Information

```python
# Not checking for risks
for ba_data in result['BaSuccessDataWithRiskList']:
    print(ba_data['IcpNumber'])
    # Missing: Check ba_data['RiskList']
```

### ❌ 5. Not Setting User-Agent

```python
# Missing user-agent for tracking
config = open_api_models.Config(
    credential=credential,
    endpoint='companyreg.aliyuncs.com'
    # Missing: user_agent='ICP-Filing-Query-Skill/1.0'
)
```

---

## Testing Checklist

- [ ] Can import all required modules
- [ ] CredentialClient initializes without error
- [ ] OpenApiClient configuration is correct
- [ ] API parameters match specification
- [ ] Request parameters include 'Caller': 'skill'
- [ ] Response has 'Success' field
- [ ] Response has 'BaSuccessDataWithRiskList' field
- [ ] Can extract entity information
- [ ] Can extract website information
- [ ] Can extract APP information (if present)
- [ ] Can extract risk information (if present)
- [ ] Error handling works for authentication errors
- [ ] Error handling works for permission errors
- [ ] Error handling works for network errors
- [ ] No hardcoded credentials in code
- [ ] All field names match API specification exactly

---

## Example Test Script

```python
#!/usr/bin/env python3
"""
Acceptance test for ICP Filing Success Query skill
"""

def test_imports():
    """Test all imports work correctly"""
    try:
        from alibabacloud_credentials.client import Client as CredentialClient
        from alibabacloud_tea_openapi.client import Client as OpenApiClient
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_tea_util import models as util_models
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_client_creation():
    """Test client can be created"""
    try:
        from alibabacloud_credentials.client import Client as CredentialClient
        from alibabacloud_tea_openapi.client import Client as OpenApiClient
        from alibabacloud_tea_openapi import models as open_api_models

        credential = CredentialClient()
        config = open_api_models.Config(
            credential=credential,
            endpoint='companyreg.aliyuncs.com',
            region_id='cn-hangzhou'
        )
        client = OpenApiClient(config)
        print("✓ Client created successfully")
        return True
    except Exception as e:
        print(f"✗ Client creation failed: {e}")
        return False

def test_response_structure():
    """Test response has correct structure"""
    # Mock response for testing
    mock_response = {
        'Success': True,
        'RequestId': 'test-request-id',
        'BaSuccessDataWithRiskList': [
            {
                'IcpNumber': '测ICP备12345678号',
                'OrganizersName': '测试公司',
                'OrganizersNature': '企业',
                'ResponsiblePersonName': '张三',
                'WebsiteList': [],
                'AppList': [],
                'RiskList': []
            }
        ]
    }

    try:
        assert 'Success' in mock_response
        assert 'BaSuccessDataWithRiskList' in mock_response
        ba_list = mock_response['BaSuccessDataWithRiskList']
        assert len(ba_list) > 0
        ba_data = ba_list[0]
        assert 'IcpNumber' in ba_data
        assert 'OrganizersName' in ba_data
        assert 'WebsiteList' in ba_data
        assert 'AppList' in ba_data
        assert 'RiskList' in ba_data
        print("✓ Response structure validation passed")
        return True
    except AssertionError as e:
        print(f"✗ Response structure validation failed: {e}")
        return False

if __name__ == '__main__':
    print("Running Acceptance Tests...\n")

    tests = [
        test_imports,
        test_client_creation,
        test_response_structure
    ]

    results = [test() for test in tests]

    print(f"\nResults: {sum(results)}/{len(results)} tests passed")
```

---

## Related Documentation

- Common SDK Usage: references/common-sdk-usage.md
- Error Handling: references/error-handling.md
- Verification Method: references/verification-method.md
