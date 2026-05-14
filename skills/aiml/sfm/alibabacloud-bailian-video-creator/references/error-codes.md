# DashScope API Error Codes

## HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Request successful |
| 400 | Invalid request parameters |
| 401 | Authentication failed (invalid API Key) |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
| 503 | Service temporarily unavailable |

## Business Error Codes

### Authentication Related

| Error Code | Description | Solution |
|-----------|-------------|----------|
| InvalidApiKey | API Key is invalid | Check if API Key is correct |
| ExpiredApiKey | API Key has expired | Obtain a new API Key |
| Unauthorized | Unauthorized access | Check Authorization header in request |

### Parameter Related

| Error Code | Description | Solution |
|-----------|-------------|----------|
| InvalidParameter | Parameter format error | Check parameter types and formats |
| MissingParameter | Required parameter missing | Add the missing parameter |
| InvalidVideoFormat | Video format not supported | Use MP4 format |
| VideoTooLarge | Video file too large | Compress video to ≤50MB |
| VideoTooLong | Video duration exceeds limit | Trim video to ≤5 seconds |

### Task Related

| Error Code | Description | Solution |
|-----------|-------------|----------|
| TaskNotFound | Task does not exist | Check if task_id is correct |
| TaskFailed | Task execution failed | Check error details, retry |
| TaskCancelled | Task was cancelled | Create a new task |
| TaskTimeout | Task timed out | Check input content, retry |

### Resource Related

| Error Code | Description | Solution |
|-----------|-------------|----------|
| InsufficientQuota | Insufficient quota | Purchase more quota |
| RateLimitExceeded | Request rate limit exceeded | Reduce request frequency |
| ConcurrentLimitExceeded | Concurrent limit exceeded | Reduce concurrent requests |

## Video Generation Specific Errors

### Text-to-Video

| Error Code | Description | Solution |
|-----------|-------------|----------|
| InvalidPrompt | Prompt format error | Check multi-shot format |
| PromptTooLong | Prompt too long | Simplify the prompt |
| InvalidShotType | Invalid shot type | Use "multi" or "single" |
| InvalidDuration | Invalid duration parameter | Set to 5-15 seconds |

### Video Editing

| Error Code | Description | Solution |
|-----------|-------------|----------|
| InvalidControlCondition | Invalid control condition | Use posebodyface/posebody/depth/scribble |
| InvalidMaskType | Invalid mask type | Use tracking or fixed |
| MaskImageNotFound | Mask image not found | Check mask_image_url |
| InvalidExpandRatio | Invalid expansion ratio | Set to 0.0-1.0 |

## Error Handling Example

```python
from http import HTTPStatus
from dashscope import VideoSynthesis

rsp = VideoSynthesis.async_call(
    api_key=api_key,
    model="wan2.6-t2v",
    prompt="Description text"
)

if rsp.status_code == HTTPStatus.OK:
    print("Task created successfully")
elif rsp.status_code == 401:
    print("Authentication failed, please check API Key")
elif rsp.status_code == 400:
    print(f"Parameter error: {rsp.code} - {rsp.message}")
elif rsp.status_code == 429:
    print("Rate limit exceeded, please retry later")
else:
    print(f"Request failed: {rsp.status_code}")
```

## Task Status Polling Error Handling

```python
def poll_result(task_id, api_key):
    while True:
        rsp = VideoSynthesis.wait(task_id, api_key=api_key)

        if rsp.status_code != HTTPStatus.OK:
            print(f"Query failed: {rsp.code} - {rsp.message}")
            break

        status = rsp.output.task_status

        if status == "SUCCEEDED":
            return rsp.output.video_url
        elif status == "FAILED":
            print(f"Task failed: {rsp.output.message}")
            break
        elif status == "CANCELLED":
            print("Task cancelled")
            break

        time.sleep(15)
```

## FAQ

### Q: Task stuck in PENDING status?
A: Server may be busy. Wait or retry later.

### Q: Video generation failed with "InvalidPrompt"?
A: Check multi-shot prompt format. Ensure correct format:
```
Shot 1 [0-2s] Description...
```

### Q: Video editing result not ideal?
A: Try adjusting `control_condition` and `strength` parameters.

### Q: How to get detailed error information?
A: Check the `message` field in the response, or view console logs.
