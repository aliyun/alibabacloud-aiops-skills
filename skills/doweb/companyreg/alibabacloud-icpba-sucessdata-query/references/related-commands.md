# Related Commands for ICP Filing Success Query

## CLI Commands

Currently, the direct CLI command for querying ICP filing success data is not available in the standard Aliyun CLI plugin. This skill uses the Python Common SDK as an alternative.

### Future CLI Command (when available)

```bash
aliyun beian query-success-icp-data --caller skill
```

**Expected Parameters**:
- `--caller`: Caller identifier (fixed value: "skill")

**Expected Output**: JSON response containing filing success data

## Python Common SDK Methods

### Import Statements

```python
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
import json
```

### Create OpenAPI Client

```python
def create_client() -> OpenApiClient:
    """
    Create an OpenAPI client with credential authentication.
    """
    credential = CredentialClient()

    config = open_api_models.Config(
        credential=credential,
        endpoint='companyreg.aliyuncs.com',
        region_id='cn-hangzhou'
    )

    return OpenApiClient(config)
```

### Query ICP Filing Success Data

```python
def query_success_icp_data(caller: str = 'skill') -> dict:
    """
    Query ICP filing success data.

    Args:
        caller: Caller identifier (fixed value: 'skill')

    Returns:
        dict: Filing success data response
    """
    client = create_client()

    params = open_api_models.Params(
        action='QuerySuccessIcpData',
        version='2026-04-23',
        protocol='HTTPS',
        method='POST',
        auth_type='AK',
        style='RPC',
        pathname='/',
        req_body_type='formData',
        body_type='json'
    )

    queries = {
        'Caller': caller
    }

    request = open_api_models.OpenApiRequest(
        query=queries
    )

    runtime = util_models.RuntimeOptions()

    response = client.call_api(params, request, runtime)
    return response.get('body', {})
```

## API Information

| Field | Value |
|-------|-------|
| **Product** | Companyreg (Beian operations) |
| **API Action** | QuerySuccessIcpData |
| **API Version** | 2026-04-23 |
| **Protocol** | HTTPS |
| **Method** | POST |
| **Style** | RPC |
| **Endpoint** | companyreg.aliyuncs.com |

## Request Parameters

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| Caller | String | Yes | Caller identifier | `skill` |

## Response Structure

```json
{
  "RequestId": "string",
  "Success": boolean,
  "BaSuccessDataWithRiskList": [
    {
      "IcpNumber": "string",
      "OrganizersName": "string",
      "OrganizersNature": "string",
      "ResponsiblePersonName": "string",
      "WebsiteList": [
        {
          "SiteRecordNum": "string",
          "DomainList": ["string"],
          "SiteName": "string",
          "ResponsiblePersonName": "string"
        }
      ],
      "AppList": [
        {
          "AppRecordNum": "string",
          "DomainList": ["string"],
          "AppName": "string",
          "ResponsiblePersonName": "string"
        }
      ],
      "RiskList": [
        {
          "DeadLine": "string",
          "RiskDetailList": [
            {
              "RiskSource": "string",
              "rectifySuggest": ["string"]
            }
          ]
        }
      ]
    }
  ]
}
```

## Response Fields

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| RequestId | String | Unique request identifier |
| Success | Boolean | Whether the request was successful |
| BaSuccessDataWithRiskList | Array | List of filing success data records |

### BaSuccessDataWithRiskList Object

| Field | Type | Description |
|-------|------|-------------|
| IcpNumber | String | ICP filing number (备案号) |
| OrganizersName | String | Entity name (主体名称) |
| OrganizersNature | String | Entity type (主体性质): 企业/个人 |
| ResponsiblePersonName | String | Responsible person name (负责人) |
| WebsiteList | Array | List of websites under this filing |
| AppList | Array | List of APPs under this filing |
| RiskList | Array | List of risks associated with this filing |

### WebsiteList Object

| Field | Type | Description |
|-------|------|-------------|
| SiteRecordNum | String | Website filing number (网站备案号) |
| DomainList | Array[String] | List of domain names |
| SiteName | String | Website name |
| ResponsiblePersonName | String | Website responsible person |

### AppList Object

| Field | Type | Description |
|-------|------|-------------|
| AppRecordNum | String | APP filing number (APP备案号) |
| DomainList | Array[String] | List of domain names |
| AppName | String | APP name |
| ResponsiblePersonName | String | APP responsible person |

### RiskList Object

| Field | Type | Description |
|-------|------|-------------|
| DeadLine | String | Risk rectification deadline |
| RiskDetailList | Array | List of risk details |

### RiskDetailList Object

| Field | Type | Description |
|-------|------|-------------|
| RiskSource | String | Source of the risk |
| rectifySuggest | Array[String] | List of rectification suggestions (may contain HTML) |

## Related RAM Commands

### List User Policies

```bash
aliyun ram list-policies-for-user --user-name <username>
```

### Create Custom Policy

```bash
aliyun ram create-policy \
  --policy-name IcpFilingQueryPolicy \
  --policy-document file://policy.json
```

### Attach Policy to User

```bash
aliyun ram attach-policy-to-user \
  --policy-type Custom \
  --policy-name IcpFilingQueryPolicy \
  --user-name <username>
```

## Usage Examples

### Basic Query

```python
from query_icp_filing import query_success_icp_data
import json

# Query filing data
result = query_success_icp_data(caller='skill')

# Print formatted result
print(json.dumps(result, indent=2, ensure_ascii=False))
```

### Query and Filter Risks

```python
result = query_success_icp_data(caller='skill')

if result.get('Success'):
    for ba_data in result.get('BaSuccessDataWithRiskList', []):
        risks = ba_data.get('RiskList', [])
        if risks:
            print(f"⚠️ Filing {ba_data.get('IcpNumber')} has {len(risks)} risks:")
            for risk in risks:
                print(f"  Deadline: {risk.get('DeadLine')}")
```

### Extract All Domains

```python
result = query_success_icp_data(caller='skill')

all_domains = []
if result.get('Success'):
    for ba_data in result.get('BaSuccessDataWithRiskList', []):
        # Website domains
        for site in ba_data.get('WebsiteList', []):
            all_domains.extend(site.get('DomainList', []))
        # APP domains
        for app in ba_data.get('AppList', []):
            all_domains.extend(app.get('DomainList', []))

print(f"Total domains: {len(all_domains)}")
print(all_domains)
```

## Error Handling

### Common Errors

| Error Code | Description | Solution |
|------------|-------------|----------|
| InvalidAccessKeyId.NotFound | Access Key ID not found | Verify credentials configuration |
| Forbidden.RAM | Insufficient permissions | Check RAM policies |
| InvalidParameter | Invalid parameter value | Verify parameter format |
| InternalError | Internal service error | Retry or contact support |

### Error Handling Pattern

```python
try:
    result = query_success_icp_data(caller='skill')
    if not result.get('Success'):
        print("Query failed")
except Exception as e:
    error_msg = str(e)
    if 'InvalidAccessKeyId' in error_msg:
        print("Credential error: Check your Access Key configuration")
    elif 'Forbidden' in error_msg:
        print("Permission error: Check RAM policies")
    else:
        print(f"Error: {error_msg}")
```

## Additional Resources

- [Alibaba Cloud OpenAPI Portal](https://next.api.aliyun.com/)
- [Python Common SDK Documentation](https://www.alibabacloud.com/help/sdk/python-sdk)
- [API Error Codes](https://www.alibabacloud.com/help/doc-detail/error-codes)
