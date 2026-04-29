# Python Common SDK Usage for ICP Filing Query

## Overview

This document provides detailed guidance on using the Alibaba Cloud Python Common SDK to query ICP filing success data.

## Prerequisites

### Install Dependencies

```bash
pip install -r scripts/requirements.txt
```

### Verify Installation

```python
import alibabacloud_credentials
import alibabacloud_tea_openapi

print(f"Credentials SDK version: {alibabacloud_credentials.__version__}")
print(f"OpenAPI SDK version: {alibabacloud_tea_openapi.__version__}")
```

## Authentication

### Using CredentialClient (Recommended)

The `CredentialClient` automatically discovers credentials from multiple sources:

1. Environment variables (`ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`)
2. Credentials file (`~/.alibabacloud/credentials`)
3. ECS RAM role
4. STS token

```python
from alibabacloud_credentials.client import Client as CredentialClient

# Automatic credential discovery
credential = CredentialClient()
```

### Credential Priority Chain

The credential client searches in this order:

1. **Environment Variables**:
   ```bash
   export ALIBABA_CLOUD_ACCESS_KEY_ID="your-access-key-id"
   export ALIBABA_CLOUD_ACCESS_KEY_SECRET="your-access-key-secret"
   ```

2. **Credentials File** (`~/.alibabacloud/credentials`):
   ```ini
   [default]
   type = access_key
   access_key_id = your-access-key-id
   access_key_secret = your-access-key-secret
   ```

3. **ECS RAM Role** (when running on ECS):
   - No configuration needed
   - Automatically fetches temporary credentials from instance metadata

4. **STS Token**:
   ```bash
   export ALIBABA_CLOUD_ACCESS_KEY_ID="your-access-key-id"
   export ALIBABA_CLOUD_ACCESS_KEY_SECRET="your-access-key-secret"
   export ALIBABA_CLOUD_SECURITY_TOKEN="your-security-token"
   ```

## Creating OpenAPI Client

### Basic Client Configuration

```python
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as open_api_models

def create_client(endpoint: str = 'companyreg.aliyuncs.com',
                  region_id: str = 'cn-hangzhou') -> OpenApiClient:
    """
    Create an OpenAPI client with automatic credential discovery.

    Args:
        endpoint: API endpoint (default: companyreg.aliyuncs.com)
        region_id: Region ID (default: cn-hangzhou)

    Returns:
        OpenApiClient: Configured API client
    """
    # Automatic credential discovery
    credential = CredentialClient()

    # Configure client
    config = open_api_models.Config(
        credential=credential,
        endpoint=endpoint,
        region_id=region_id
    )

    return OpenApiClient(config)
```

### Advanced Client Configuration

For more control over client behavior:

```python
def create_advanced_client(
    endpoint: str = 'companyreg.aliyuncs.com',
    region_id: str = 'cn-hangzhou',
    connect_timeout: int = 5000,
    read_timeout: int = 10000,
    max_idle_conns: int = 50
) -> OpenApiClient:
    """
    Create an OpenAPI client with advanced configuration.
    """
    credential = CredentialClient()

    config = open_api_models.Config(
        credential=credential,
        endpoint=endpoint,
        region_id=region_id,
        connect_timeout=connect_timeout,  # Connection timeout in milliseconds
        read_timeout=read_timeout,        # Read timeout in milliseconds
        max_idle_conns=max_idle_conns,    # Maximum idle connections
        protocol='HTTPS',                 # Force HTTPS
        user_agent='ICP-Filing-Query-Skill/1.0'
    )

    return OpenApiClient(config)
```

## Making API Calls

### Basic API Call Pattern

```python
from alibabacloud_tea_util import models as util_models

def call_api(client: OpenApiClient, action: str, queries: dict) -> dict:
    """
    Generic API call pattern.

    Args:
        client: OpenAPI client
        action: API action name
        queries: Query parameters

    Returns:
        dict: API response body
    """
    # Define API parameters
    params = open_api_models.Params(
        action=action,
        version='2026-04-23',
        protocol='HTTPS',
        method='POST',
        auth_type='AK',
        style='RPC',
        pathname='/',
        req_body_type='formData',
        body_type='json'
    )

    # Create request
    request = open_api_models.OpenApiRequest(
        query=queries
    )

    # Runtime options
    runtime = util_models.RuntimeOptions()

    # Call API
    response = client.call_api(params, request, runtime)

    return response.get('body', {})
```

### QuerySuccessIcpData Implementation

See the complete implementation in `scripts/query_icp_filing.py` and the Core Workflow section of `SKILL.md`.

## Error Handling

### Basic Error Handling

```python
from Tea.exceptions import TeaException

def query_with_error_handling(caller: str = 'skill') -> dict:
    """
    Query with comprehensive error handling.
    """
    try:
        result = query_success_icp_data(caller)
        return result
    except TeaException as e:
        print(f"API Error:")
        print(f"  Code: {e.code}")
        print(f"  Message: {e.message}")
        print(f"  Data: {e.data}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise
```

### Retry Logic

```python
import time

def query_with_retry(caller: str = 'skill', max_retries: int = 3) -> dict:
    """
    Query with automatic retry on failure.

    Args:
        caller: Caller identifier
        max_retries: Maximum number of retry attempts

    Returns:
        dict: API response
    """
    for attempt in range(max_retries):
        try:
            result = query_success_icp_data(caller)
            return result
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"All {max_retries} attempts failed")
                raise
```

## Response Processing

### Parse Entity Information

```python
def extract_entity_info(response: dict) -> list:
    """
    Extract entity information from API response.

    Args:
        response: API response dict

    Returns:
        list: List of entity information dicts
    """
    entities = []

    if not response.get('Success'):
        return entities

    for ba_data in response.get('BaSuccessDataWithRiskList', []):
        entity = {
            'icp_number': ba_data.get('IcpNumber'),
            'name': ba_data.get('OrganizersName'),
            'type': ba_data.get('OrganizersNature'),
            'responsible_person': ba_data.get('ResponsiblePersonName')
        }
        entities.append(entity)

    return entities
```

### Parse Website Information

```python
def extract_website_info(response: dict) -> list:
    """
    Extract website information from API response.

    Args:
        response: API response dict

    Returns:
        list: List of website information dicts
    """
    websites = []

    if not response.get('Success'):
        return websites

    for ba_data in response.get('BaSuccessDataWithRiskList', []):
        icp_number = ba_data.get('IcpNumber')

        for site in ba_data.get('WebsiteList', []):
            website = {
                'icp_number': icp_number,
                'site_record_num': site.get('SiteRecordNum'),
                'site_name': site.get('SiteName'),
                'domains': site.get('DomainList', []),
                'responsible_person': site.get('ResponsiblePersonName')
            }
            websites.append(website)

    return websites
```

### Parse APP Information

```python
def extract_app_info(response: dict) -> list:
    """
    Extract APP information from API response.

    Args:
        response: API response dict

    Returns:
        list: List of APP information dicts
    """
    apps = []

    if not response.get('Success'):
        return apps

    for ba_data in response.get('BaSuccessDataWithRiskList', []):
        icp_number = ba_data.get('IcpNumber')

        for app in ba_data.get('AppList', []):
            app_info = {
                'icp_number': icp_number,
                'app_record_num': app.get('AppRecordNum'),
                'app_name': app.get('AppName'),
                'domains': app.get('DomainList', []),
                'responsible_person': app.get('ResponsiblePersonName')
            }
            apps.append(app_info)

    return apps
```

### Parse Risk Information

```python
def extract_risk_info(response: dict) -> list:
    """
    Extract risk information from API response.

    Args:
        response: API response dict

    Returns:
        list: List of risk information dicts
    """
    risks = []

    if not response.get('Success'):
        return risks

    for ba_data in response.get('BaSuccessDataWithRiskList', []):
        icp_number = ba_data.get('IcpNumber')

        for risk in ba_data.get('RiskList', []):
            for detail in risk.get('RiskDetailList', []):
                risk_info = {
                    'icp_number': icp_number,
                    'deadline': risk.get('DeadLine'),
                    'source': detail.get('RiskSource'),
                    'suggestions': detail.get('rectifySuggest', [])
                }
                risks.append(risk_info)

    return risks
```

## Complete Usage Example

See `scripts/query_icp_filing.py` for a complete working example that includes querying, parsing, and displaying ICP filing data.

## Best Practices

1. **Use CredentialClient**: Always use automatic credential discovery instead of hardcoding
2. **Handle Errors**: Implement comprehensive error handling and retry logic
3. **Parse Responses**: Use helper functions to extract structured data
4. **Timeout Configuration**: Set appropriate timeouts for your use case
5. **Connection Pooling**: Reuse clients when making multiple API calls
6. **Logging**: Add proper logging for debugging and monitoring
7. **Validation**: Validate response structure before accessing nested fields

## Common Issues

### Issue 1: Credential Not Found

**Error**: `No credentials found`

**Solution**: Set credentials using one of the supported methods (environment variables, credentials file, etc.)

### Issue 2: Permission Denied

**Error**: `Forbidden.RAM`

**Solution**: Check RAM policies and ensure the user has `beian:QuerySuccessIcpData` permission

### Issue 3: Endpoint Not Found

**Error**: `Cannot resolve endpoint`

**Solution**: Verify the endpoint URL is correct: `companyreg.aliyuncs.com`

### Issue 4: Timeout

**Error**: `Request timeout`

**Solution**: Increase timeout values or check network connectivity

## Related Documentation

- [Alibaba Cloud Credentials SDK](https://github.com/aliyun/credentials-python)
- [Alibaba Cloud OpenAPI SDK](https://github.com/aliyun/alibabacloud-sdk)
- [API Reference](https://next.api.aliyun.com/)
