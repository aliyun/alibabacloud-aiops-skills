# DashScope Voice API Error Codes Reference

## Common Error Codes

| Error Code | Error Message | Description | Solution |
|------------|---------------|-------------|----------|
| InvalidApiKey | Invalid API-key provided | API Key is invalid | Check if the API Key is correct |
| AccessDenied | Access denied | Access denied | Verify account permissions and service activation status |
| Throttling | Requests throttling triggered | Request throttling triggered | Reduce request frequency or apply for quota increase |
| QuotaExhausted | Quota exhausted | Quota exhausted | Top up balance or wait for quota refresh |
| InternalError | Internal error | Internal error | Retry later; contact support if the issue persists |

## Speech Recognition (ASR) Error Codes

| Error Code | Error Message | Description | Solution |
|------------|---------------|-------------|----------|
| InvalidParameter | Invalid parameter | Invalid parameter | Check request parameter format and value range |
| FileUrlInvalid | File URL is invalid | File URL is invalid | Ensure URL is publicly accessible and correctly formatted |
| FileTooLarge | File size exceeds limit | File too large | Long audio <=2GB, short audio <=10MB |
| FileDurationExceed | Audio duration exceeds limit | Audio duration exceeds limit | Long audio <=12h, short audio <=5min |
| UnsupportedFormat | Unsupported audio format | Unsupported audio format | Use a supported format (mp3, wav, flac, etc.) |
| FileDownloadFailed | Failed to download file | File download failed | Check if URL is accessible |
| EmptyAudio | Audio content is empty | Audio content is empty | Check if the audio file is valid |
| NoSpeechDetected | No speech detected | No speech detected | Check if the audio contains valid speech content |
| TaskNotFound | Task not found | Task does not exist | Check if the task_id is correct |
| TaskExpired | Task has expired | Task has expired | Resubmit the task |

## Speech Synthesis (TTS) Error Codes

| Error Code | Error Message | Description | Solution |
|------------|---------------|-------------|----------|
| InvalidParameter | Invalid parameter | Invalid parameter | Check request parameter format and value range |
| TextTooLong | Text length exceeds limit | Text too long | Single request must not exceed 10,000 characters |
| TextEmpty | Text content is empty | Text is empty | Provide valid text content |
| InvalidVoice | Invalid voice parameter | Invalid voice parameter | Use a valid voice name (e.g. Cherry) |
| InvalidSpeechRate | Invalid speech rate | Invalid speech rate | Speech rate range: 0.5-2.0 |
| InvalidPitch | Invalid pitch value | Invalid pitch value | Pitch range: 0.5-2.0 |
| InvalidVolume | Invalid volume value | Invalid volume value | Volume range: 0-100 |
| InvalidFormat | Invalid output format | Invalid output format | Use wav, mp3, or pcm |
| InvalidSampleRate | Invalid sample rate | Invalid sample rate | Use a supported sample rate (8k-48k) |
| SynthesisFailed | Speech synthesis failed | Synthesis failed | Check text content, retry later |

## HTTP Status Codes

| Status Code | Description | Common Causes |
|-------------|-------------|---------------|
| 200 | Success | Request processed successfully |
| 400 | Bad Request | Parameter format error or missing required parameter |
| 401 | Unauthorized | API Key is invalid or not provided |
| 403 | Forbidden | Insufficient account permissions or service not activated |
| 404 | Not Found | Task ID does not exist or has expired |
| 429 | Too Many Requests | Throttling triggered, reduce request frequency |
| 500 | Server Error | Internal error, retry later |
| 503 | Service Unavailable | Service temporarily unavailable, retry later |

## Task Status

| Status | Description | Recommended Action |
|--------|-------------|-------------------|
| PENDING | Task is waiting | Continue polling |
| RUNNING | Task is running | Continue polling |
| SUCCEEDED | Task succeeded | Retrieve results |
| FAILED | Task failed | Check error message |
| CANCELLED | Task cancelled | Resubmit |

## Common Troubleshooting

### 1. "Invalid API-key provided"
- Check if the API Key was copied correctly
- Verify the environment variable `DASHSCOPE_API_KEY` is set
- Confirm the API Key region matches the request endpoint

### 2. "File URL is invalid"
- Ensure the audio file URL is publicly accessible
- URL must be a complete HTTP/HTTPS address
- Check if the file exists and has not expired

### 3. "Audio duration exceeds limit"
- Short audio (qwen3-asr-flash): <=5 minutes
- Long audio (qwen3-asr-flash-filetrans): <=12 hours
- Use FFmpeg to trim overly long audio

### 4. "No speech detected"
- Check if the audio contains valid speech
- Verify the audio volume is not too low
- Try adjusting the audio with FFmpeg

### 5. "Invalid voice parameter"
- Use a valid voice name, e.g. Cherry, Ethan
- Voice names are case-sensitive
- Refer to the voice list for selection

## Error Retry Strategy

```python
import time
import random

def retry_with_backoff(func, max_retries=3):
    """Retry strategy with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            # Exponential backoff + random jitter
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            print(f"Request failed, retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
```

## Reference Links

- [DashScope Error Code Documentation](https://help.aliyun.com/zh/model-studio/developer-reference/error-code)
- [Speech Recognition API Documentation](https://help.aliyun.com/zh/model-studio/qwen-asr-api-reference)
- [Speech Synthesis API Documentation](https://help.aliyun.com/zh/model-studio/qwen-tts-api-reference)
