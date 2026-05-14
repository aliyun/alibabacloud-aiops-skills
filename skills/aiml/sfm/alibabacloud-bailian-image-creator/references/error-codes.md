# DashScope Error Code Reference

## Common Error Codes

### Authentication Related

| Error Code | Description | Solution |
|-----------|-------------|----------|
| `InvalidApiKey` | API Key is invalid | Check if API Key is correct, confirm region matches |
| `Unauthorized` | Not authorized | Confirm API Key is set and valid |
| `AccessDenied` | Access denied | Check account permissions and quota |

### Request Related

| Error Code | Description | Solution |
|-----------|-------------|----------|
| `InvalidParameter` | Invalid parameter | Check parameter format and value range |
| `MissingParameter` | Missing required parameter | Add the missing parameter |
| `InvalidImageURL` | Image URL is invalid | Check if the URL is accessible |
| `ImageSizeExceeded` | Image size exceeded | Compress the image or reduce resolution |

### Resource Related

| Error Code | Description | Solution |
|-----------|-------------|----------|
| `QuotaExceeded` | Quota exceeded | Wait for quota reset or upgrade account |
| `ConcurrentRequestExceeded` | Concurrent request limit exceeded | Reduce request frequency |
| `ModelNotFound` | Model not found | Check if model name is correct |

### Service Related

| Error Code | Description | Solution |
|-----------|-------------|----------|
| `InternalError` | Internal error | Retry later |
| `ServiceUnavailable` | Service unavailable | Check service status, retry later |
| `Timeout` | Request timeout | Increase timeout or retry |

---

## Error Handling Best Practices

### 1. Basic Error Handling

```python
if response.status_code == 200:
    # Handle success response
    print(json.dumps(response, ensure_ascii=False))
else:
    print(f"HTTP status code: {response.status_code}")
    print(f"Error code: {response.code}")
    print(f"Error message: {response.message}")
    print("Reference: https://help.aliyun.com/zh/model-studio/developer-reference/error-code")
```

### 2. Retry Mechanism

```python
import time

def call_with_retry(func, max_retries=3):
    for i in range(max_retries):
        try:
            result = func()
            if result.status_code == 200:
                return result
            elif result.code in ['InternalError', 'ServiceUnavailable', 'Timeout']:
                print(f"Retry {i+1}/{max_retries}")
                time.sleep(2 ** i)  # Exponential backoff
                continue
            else:
                return result
        except Exception as e:
            print(f"Exception: {e}")
            if i == max_retries - 1:
                raise
            time.sleep(2 ** i)
```

### 3. Quota Management

```python
# Check quota status
def check_quota(response):
    if response.code == 'QuotaExceeded':
        print("Quota exhausted. Please wait for reset or upgrade your account")
        # Can log or send notifications
        return False
    return True
```

---

## Debugging Tips

1. **Enable verbose logging**: Set `dashscope` log level to DEBUG
2. **Check request parameters**: Print complete request parameters for validation
3. **Test with simple requests**: First test API connectivity with minimal parameters
4. **Check official documentation**: https://help.aliyun.com/zh/model-studio/developer-reference/error-code

---

## Getting Help

- **Error Code Documentation**: https://help.aliyun.com/zh/model-studio/developer-reference/error-code
- **API Documentation**: https://help.aliyun.com/zh/model-studio/developer-reference
- **Technical Support**: Submit issues via Alibaba Cloud ticket system
