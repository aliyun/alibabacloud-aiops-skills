# Error Handling for ICP Filing Success Query

## Overview

This document describes common errors that may occur when querying ICP filing success data and their solutions.

## Common Error Categories

### 1. Authentication Errors
### 2. Permission Errors
### 3. Parameter Errors
### 4. Network Errors
### 5. Service Errors

---

## 1. Authentication Errors

### Error: InvalidAccessKeyId.NotFound

**Full Error Message**:
```
InvalidAccessKeyId.NotFound: Specified access key is not found.
```

**Cause**: The Access Key ID does not exist or is incorrect.

**Solution**:
1. Verify your Access Key ID is correct
2. Check if the Access Key has been deleted
3. Ensure you're using the correct environment/account
4. Generate a new Access Key if necessary

```bash
# Check current credentials
aliyun configure list

# Reconfigure with correct credentials
aliyun configure
```

---

### Error: InvalidAccessKeySecret

**Full Error Message**:
```
InvalidAccessKeySecret: Specified access key secret is not valid.
```

**Cause**: The Access Key Secret is incorrect.

**Solution**:
1. Verify the Access Key Secret matches the Access Key ID
2. Check for extra spaces or hidden characters
3. Regenerate the Access Key pair if necessary

```python
# Verify credentials programmatically
from alibabacloud_credentials.client import Client as CredentialClient

try:
    credential = CredentialClient()
    # If this succeeds, credentials are found
    print("Credentials loaded successfully")
except Exception as e:
    print(f"Credential error: {e}")
```

---

### Error: SecurityToken.Expired

**Full Error Message**:
```
SecurityToken.Expired: The security token you provided has expired.
```

**Cause**: STS token has expired (common when using temporary credentials).

**Solution**:
1. Refresh your STS token
2. Use long-term Access Keys for development
3. Implement automatic token refresh logic

```python
# For STS token refresh
from alibabacloud_sts20150401.client import Client as StsClient
from alibabacloud_sts20150401 import models as sts_models

def refresh_sts_token():
    # Implement STS token refresh logic
    pass
```

---

## 2. Permission Errors

### Error: Forbidden.RAM

**Full Error Message**:
```
Forbidden.RAM: User not authorized to operate on the specified resource.
```

**Cause**: The current user/role lacks the required RAM permission `beian:QuerySuccessIcpData`.

**Solution**:
1. Check current user's permissions:
   ```bash
   aliyun ram list-policies-for-user --user-name <username>
   ```

2. Grant the required permission (see references/ram-policies.md)

3. Verify the policy is attached:
   ```bash
   aliyun ram get-user-policy \
     --user-name <username> \
     --policy-name IcpFilingQueryPolicy \
     --policy-type Custom
   ```

4. Wait a few minutes for permission changes to propagate

**Prevention**:
- Always verify permissions before deploying to production
- Use RAM policy simulator to test permissions
- Follow principle of least privilege

---

### Error: Forbidden.NoPermission

**Full Error Message**:
```
Forbidden.NoPermission: You are not authorized to do this action.
```

**Cause**: Similar to Forbidden.RAM, indicates missing permissions.

**Solution**:
1. Review required permissions in references/ram-policies.md
2. Use `ram-permission-diagnose` skill for detailed analysis
3. Contact account administrator to grant permissions

---

## 3. Parameter Errors

### Error: InvalidParameter

**Full Error Message**:
```
InvalidParameter: The specified parameter is invalid.
```

**Cause**: One or more parameters have invalid values.

**Solution**:
1. Verify all parameters match the API specification
2. Check parameter types (string, integer, boolean)
3. Ensure required parameters are provided

```python
# Correct parameter usage
def query_success_icp_data(caller: str = 'skill') -> dict:
    # Validate parameter
    if not caller or not isinstance(caller, str):
        raise ValueError("Caller must be a non-empty string")

    queries = {
        'Caller': caller  # Must be 'skill' for this API
    }
    # ... rest of the code
```

**Common Parameter Issues**:
| Parameter | Issue | Solution |
|-----------|-------|----------|
| Caller | Empty or wrong value | Must be 'skill' |
| Caller | Wrong type | Must be string, not int/bool |

---

### Error: MissingParameter

**Full Error Message**:
```
MissingParameter: The required parameter is missing.
```

**Cause**: A required parameter was not provided.

**Solution**:
1. Check API documentation for required parameters
2. Ensure all required parameters are included in the request

```python
# Always include required parameters
queries = {
    'Caller': 'skill'  # Required parameter
}
```

---

## 4. Network Errors

### Error: Connection Timeout

**Full Error Message**:
```
RequestTimeout: Request timeout.
```

**Cause**: Network request took too long to complete.

**Solution**:
1. Check network connectivity
2. Increase timeout values
3. Implement retry logic

```python
from alibabacloud_tea_util import models as util_models

# Increase timeout
runtime = util_models.RuntimeOptions(
    connect_timeout=10000,  # 10 seconds
    read_timeout=30000      # 30 seconds
)

response = client.call_api(params, request, runtime)
```

---

### Error: Connection Refused

**Full Error Message**:
```
ConnectionError: Connection refused.
```

**Cause**: Cannot connect to the API endpoint.

**Solution**:
1. Verify endpoint URL is correct: `companyreg.aliyuncs.com`
2. Check firewall settings
3. Verify network connectivity
4. Ensure you're not blocked by security policies

```python
# Verify endpoint
config = open_api_models.Config(
    credential=credential,
    endpoint='companyreg.aliyuncs.com',  # Verify this
    region_id='cn-hangzhou'
)
```

---

### Error: SSL Certificate Verification Failed

**Full Error Message**:
```
SSLError: Certificate verification failed.
```

**Cause**: SSL certificate cannot be verified.

**Solution**:
1. Update CA certificates on your system
2. Check system time is correct (affects certificate validation)
3. If behind corporate proxy, configure proxy settings

```bash
# Update CA certificates (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install ca-certificates

# macOS
brew install openssl
```

---

## 5. Service Errors

### Error: InternalError

**Full Error Message**:
```
InternalError: An internal error occurred.
```

**Cause**: Server-side error in the Alibaba Cloud service.

**Solution**:
1. Retry the request (often transient errors)
2. Implement exponential backoff
3. Check [Alibaba Cloud Service Status](https://status.alibabacloud.com/)
4. Contact support if error persists

```python
import time

def query_with_exponential_backoff(max_retries=3):
    for attempt in range(max_retries):
        try:
            return query_success_icp_data(caller='skill')
        except Exception as e:
            if 'InternalError' in str(e) and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Internal error, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
```

---

### Error: ServiceUnavailable

**Full Error Message**:
```
ServiceUnavailable: The service is temporarily unavailable.
```

**Cause**: The API service is temporarily unavailable (maintenance, overload, etc.).

**Solution**:
1. Wait and retry after a few minutes
2. Check service status page
3. Implement circuit breaker pattern

```python
import time
from datetime import datetime, timedelta

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open

    def call(self, func, *args, **kwargs):
        if self.state == 'open':
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = 'half-open'
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise

    def on_success(self):
        self.failure_count = 0
        self.state = 'closed'

    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
```

---

### Error: Throttling.User

**Full Error Message**:
```
Throttling.User: Request was denied due to user flow control.
```

**Cause**: Too many requests from your account in a short time period.

**Solution**:
1. Implement rate limiting in your application
2. Add delays between requests
3. Request quota increase if needed

```python
import time
from datetime import datetime

class RateLimiter:
    def __init__(self, max_calls_per_minute=60):
        self.max_calls = max_calls_per_minute
        self.calls = []

    def wait_if_needed(self):
        now = datetime.now()
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls
                      if (now - call_time).seconds < 60]

        if len(self.calls) >= self.max_calls:
            # Wait until oldest call is more than 1 minute old
            sleep_time = 60 - (now - self.calls[0]).seconds
            if sleep_time > 0:
                time.sleep(sleep_time)

        self.calls.append(now)

# Usage
rate_limiter = RateLimiter(max_calls_per_minute=60)

def query_with_rate_limit():
    rate_limiter.wait_if_needed()
    return query_success_icp_data(caller='skill')
```

---

## Error Handling Best Practices

### 1. Comprehensive Try-Catch

```python
from Tea.exceptions import TeaException

def robust_query(caller: str = 'skill') -> dict:
    """
    Query with comprehensive error handling.
    """
    try:
        result = query_success_icp_data(caller)
        return result

    except TeaException as e:
        # Handle API-specific errors
        error_code = getattr(e, 'code', 'Unknown')

        if error_code in ['InvalidAccessKeyId.NotFound', 'InvalidAccessKeySecret']:
            print("Authentication error: Check your credentials")
        elif error_code in ['Forbidden.RAM', 'Forbidden.NoPermission']:
            print("Permission error: Check RAM policies")
        elif error_code == 'InvalidParameter':
            print("Parameter error: Check parameter values")
        elif error_code in ['InternalError', 'ServiceUnavailable']:
            print("Service error: Retry after a few minutes")
        else:
            print(f"API error [{error_code}]: {e.message}")

        raise

    except ConnectionError as e:
        print(f"Network error: {e}")
        raise

    except Exception as e:
        print(f"Unexpected error: {e}")
        raise
```

### 2. Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def query_with_logging(caller: str = 'skill') -> dict:
    """
    Query with detailed logging.
    """
    logger.info(f"Starting ICP filing query with caller: {caller}")

    try:
        result = query_success_icp_data(caller)
        logger.info(f"Query successful, RequestId: {result.get('RequestId')}")
        return result

    except Exception as e:
        logger.error(f"Query failed: {str(e)}", exc_info=True)
        raise
```

### 3. Custom Exception Classes

```python
class ICPFilingQueryError(Exception):
    """Base exception for ICP filing query errors."""
    pass

class AuthenticationError(ICPFilingQueryError):
    """Authentication-related errors."""
    pass

class PermissionError(ICPFilingQueryError):
    """Permission-related errors."""
    pass

class ParameterError(ICPFilingQueryError):
    """Parameter validation errors."""
    pass

def query_with_custom_exceptions(caller: str = 'skill') -> dict:
    """
    Query with custom exception handling.
    """
    try:
        result = query_success_icp_data(caller)
        return result

    except TeaException as e:
        error_code = getattr(e, 'code', 'Unknown')

        if error_code in ['InvalidAccessKeyId.NotFound', 'InvalidAccessKeySecret']:
            raise AuthenticationError(f"Authentication failed: {e.message}")
        elif error_code in ['Forbidden.RAM', 'Forbidden.NoPermission']:
            raise PermissionError(f"Permission denied: {e.message}")
        elif error_code == 'InvalidParameter':
            raise ParameterError(f"Invalid parameter: {e.message}")
        else:
            raise ICPFilingQueryError(f"Query failed: {e.message}")
```

## Error Response Structure

API errors typically have this structure:

```json
{
  "Code": "Forbidden.RAM",
  "Message": "User not authorized to operate on the specified resource.",
  "RequestId": "ABC123-DEF456-GHI789",
  "HostId": "companyreg.aliyuncs.com"
}
```

## Debugging Tips

1. **Enable Debug Logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Print Request Details**:
   ```python
   print(f"Endpoint: {config.endpoint}")
   print(f"Region: {config.region_id}")
   print(f"Parameters: {queries}")
   ```

3. **Check Request ID**:
   Every API response includes a RequestId. Use it when contacting support.

4. **Use API Explorer**:
   Test API calls in [OpenAPI Explorer](https://next.api.aliyun.com/) to isolate issues.

## Related Documentation

- [API Error Codes Reference](https://www.alibabacloud.com/help/doc-detail/error-codes)
- RAM Permission Troubleshooting: references/ram-policies.md
- Common SDK Usage: references/common-sdk-usage.md
