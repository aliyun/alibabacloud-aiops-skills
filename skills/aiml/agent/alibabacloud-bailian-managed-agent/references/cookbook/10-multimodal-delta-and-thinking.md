# 10 · Image questions and Delta / Thinking integration

Scenario: a user submits an image to a business service, which passes it to MA. The frontend receives incremental answers and can show a thinking indicator while waiting.

**Test scope**: 2026-09-18, cn-beijing. Image `file_id` input correctly identified a synthetic red image with `qwen3.8-max` and `qwen3.7-plus`. Delta and reasoning were verified with `qwen3.8-max`. Video input was not tested.

## Run the complete example

See [09](09-working-memory-and-web-research.md#run-the-example) for dependencies and authentication. Run from the repository root:

```bash
/tmp/ma-cookbook-env/bin/python scripts/cookbook_smoke.py \
  --execute --bl-config "$HOME/.bailian/config.json" \
  --scenarios image delta --output /tmp/ma-image-delta-check
```

In [cookbook_smoke.py](../../scripts/cookbook_smoke.py), `image_test` generates a red PNG without user data, uploads it, waits for review, then sends it. `delta_test` subscribes to real SSE and asserts that concatenated deltas equal the final answer. The script cleans up its own temporary resources.

## Image input: use the verified file_id path

1. Upload a PNG with multipart `POST /files`; save its File ID.
2. Poll `GET /files/{id}` with a deadline until `available`; stop on rejection.
3. Send this to a new Session:

```json
{
  "input": [{
    "type": "message",
    "role": "user",
    "content": [
      {"type": "text", "text": "Identify the dominant color. Answer just the color name."},
      {"type": "image", "file_id": "<available_image_file_id>"}
    ]
  }]
}
```

4. Check the assistant's answer and terminal state. Expect `Red`; HTTP 200 or `end_turn` alone is insufficient.

**Current limitation (user-confirmed, 2026-09-18)**: MA does not currently support Base64 `image_data` input. The earlier official claim of support for `image_data` + `media_type` was incorrect. In tests, POST accepted synthetic PNG data and history retained the image block, but both models reported no image. Uploaded `file_id` inputs worked. The max trials used 32×32 Base64 images versus 64×64 file uploads; the plus comparison used the exact same 64×64 PNG for both carriers, and only `file_id` worked. The user confirmed the unsupported status and documentation error, resolving the earlier uncertainty about the cause. Use `file_id` now rather than repeating Base64 attempts. Documentation may be corrected later; retest if support is subsequently announced. This limitation does not mean multimodal events are unavailable. See [product status](../product/status.md).

`type: "image"` supplies model vision input. `type: "file"` with `file_id` and `filename` materializes a file for tool access; these serve different purposes.

## Delta: subscribe before sending

Use this subscription path and repeated query parameter:

```text
GET /sessions/{id}/events/stream?event_deltas[]=message&event_deltas[]=reasoning
Accept: text/event-stream
```

Confirm SSE is established before POSTing input through another request. SSE does not replay history; sending first can miss a fast completion or immediate error.

| Frame | Handling |
| --- | --- |
| `event_start` | Record `event.id` and `event.type`; allocate an answer or reasoning slot |
| `event_delta` | Aggregate `delta.content.text` by `event_id` and `delta.index`; one block may have multiple fragments |
| Full `message` / `reasoning` | Validate or replace the event's content; **do not append it again** |
| `session_status` | Read status and `stop_reason` from `content[].data`; `end_turn` means normal completion |
| `error` | Read top-level `error.code` / `error.message`; retain the Session ID for recovery |

Minimal aggregation core (the script includes SSE parsing, connection ordering, and deadlines):

```python
buffers = {}
# For each event_delta:
delta = event["delta"]
key = (event["event_id"], delta["index"])
content = delta.get("content", {})
if content.get("type") == "text":
    buffers[key] = buffers.get(key, "") + content.get("text", "")
```

`delta.index` identifies a **content block**, not a unique fragment. All 23 fragments in the first test concatenated to the final message. Deduplicating fragments by `(event_id, index)` would discard everything after the first fragment in a block. After disconnecting, rebuild from full historical messages keyed by event ID; do not resend the original business input.

Thinking uses `reasoning` events. This test received reasoning start and final frames; not every reasoning event is guaranteed to contain nonempty delta text. Show a thinking indicator rather than treating missing reasoning deltas as failure.

SDK 1.27.3 `events.stream()` has no `event_deltas` parameter. Use REST SSE with the query parameters above when deltas are needed; do not invent an SDK argument.

## Sources

- [Send events: multimodal content blocks](https://docs.agent.bailian.aliyun.com/zh/api/managed-agents/session/send-event.md)
- [SSE: Delta frames and reasoning behavior](https://docs.agent.bailian.aliyun.com/zh/api/managed-agents/session/stream-events.md)
