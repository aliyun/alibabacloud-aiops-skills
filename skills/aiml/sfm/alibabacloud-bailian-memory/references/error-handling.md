# Error Handling Reference

## Error Response Format

All API errors return a JSON body:

```json
{
  "code": "ErrorCode",
  "message": "Human-readable error description",
  "request_id": "unique-request-identifier"
}
```

## Common Error Codes

| HTTP Status | Error Code | Description | Resolution |
|-------------|-----------|-------------|------------|
| 400 | `InvalidParameter` | Invalid parameter value or format | Check parameter types and constraints |
| 400 | `MissingParameter` | Required parameter not provided | Add the required parameter |
| 400 | `MutuallyExclusiveParams` | `project_id`/`project_ids` both provided (messages mode) | Provide only one of them |
| 400 | `InvalidParameter` (profile update) | `attributes` empty or missing `attribute_id` | Provide a non-empty list; get attribute IDs via get_user_profile |
| 401 | `InvalidApiKey` | API key is invalid or not configured | Verify `DASHSCOPE_API_KEY` env var |
| 403 | `Forbidden` | Insufficient permissions / service not activated | Check Bailian console activation and permissions |
| 404 | `NotFound` | Resource does not exist | Verify resource IDs (`memory_node_id`, `event_id`, `profile_schema_id`); check `project_id` was not passed as `memory_library_id` |
| 429 | `TooManyRequests` | Rate limit exceeded | Reduce request frequency; implement backoff |
| 500 | `InternalError` | Internal server error | Retry with exponential backoff |
| 502 | `BadGateway` | Gateway error | Retry with exponential backoff |
| 503 | `ServiceUnavailable` | Service temporarily unavailable | Retry after delay |

## Retry Strategy

The `memory_client.py` implements automatic retry with exponential backoff for transient errors:

- **Retryable status codes:** 429, 500, 502, 503
- **Max retries:** 3
- **Backoff:** 1s → 2s → 4s (exponential)
- **Non-retryable errors:** 400, 401, 403, 404 — fail immediately with clear error message

## Error Handling in Scripts

All helper scripts follow this pattern:

```python
try:
    client = MemoryClient()
    result = client.some_method(...)
    print(json.dumps(result, indent=2))
except MemoryApiError as e:
    print(f"API Error: {e}", file=sys.stderr)
    sys.exit(1)
except RuntimeError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
```

## Troubleshooting Guide

### Authentication Failures (401)

1. API key retrieval is automated via `scripts/api_key.py`. Check the script's error output for specific guidance.
2. Ensure one of the following is configured:
   - Alibaba Cloud CLI config (`~/.aliyun/config.json` with `dashscope.api_key`)
   - Environment variable `DASHSCOPE_API_KEY`
   - Alibaba Cloud CLI with ModelStudio plugin (for auto-creation)
3. Obtain a valid key from [Bailian Console](https://bailian.console.aliyun.com/)

### Resource Not Found (404)

1. Verify `memory_node_id` exists by listing memories or `get_memory_node.py`
2. Verify `event_id` comes from an `add_memory_messages.py`/`add_memory_content.py` response of the same workspace
3. Verify `profile_schema_id` exists in the Bailian console
4. Check `memory_library_id` is correct (or omit for default library); do not pass a `project_id` in its place

### Async Event Handling

Async writes (add_memory_messages / add_memory_content) are **fire-and-forget** by
default — do not poll `get_event.py` unless the user asks for confirmation or a
later step depends on extraction completion.

- `PENDING`: extraction still running — if confirmation was requested, wait a few
  seconds and re-query (at most 5 times), then report the pending state as-is
- `FAILED`: the record carries a `detail` field (`errorCode: errorMessage`) —
  report it to the user; do NOT silently retry the add
- Event queries never return extracted contents — use `list_memories.py` or
  `search_memory.py` to see results

### Rate Limiting (429)

1. SearchMemory: max 300 QPM — reduce search frequency
2. All endpoints combined: max 3000 QPM
3. The client auto-retries with backoff; for bulk operations, add delays between calls

### Content Too Long

- `custom_content`: max 512 characters
- `user_id`: max 64 characters
- `memory_library_id`: max 32 characters
- `messages`: max 50 conversation records per call
