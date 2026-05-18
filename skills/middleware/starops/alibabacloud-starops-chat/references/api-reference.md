# STAROps Agent API Reference

This skill uses STAROps OpenAPI version `2026-04-28` with ACS3-HMAC-SHA256 signing.

## Authentication

Requests are signed with Alibaba Cloud Credentials default-chain credentials. The Python script builds the ACS3 canonical request, signs it with `ACS3-HMAC-SHA256`, and sends HTTPS requests directly.

The default endpoint is derived from the region:

```text
starops.<region>.aliyuncs.com
```

Override with `STAROPS_AGENT_ENDPOINT` when a different endpoint is required.

## CreateThread

```http
POST /digitalEmployee/{name}/thread
```

Body:

```json
{
  "title": "short question title",
  "idempotencyKey": "uuid",
  "variables": {
    "workspace": "workspace-name",
    "region": "cn-beijing",
    "project": "optional-project"
  },
  "attributes": {
    "source": "alibabacloud-starops-chat"
  }
}
```

Expected response field:

```json
{
  "threadId": "thread-id"
}
```

## CreateChat

```http
POST /chat
```

Body:

```json
{
  "action": "create",
  "digitalEmployeeName": "employee-name",
  "threadId": "thread-id",
  "messages": [
    {
      "messageId": "uuid",
      "role": "user",
      "contents": [
        {
          "type": "text",
          "value": "user question"
        }
      ]
    }
  ],
  "variables": {
    "workspace": "workspace-name",
    "region": "cn-beijing"
  }
}
```

The response is an SSE stream whose `data:` payloads contain STAROps `messages`. The script stops when the stream emits a `done` message or a `task_finished` event, and it always closes the streaming HTTP response before exiting.

## Output Modes

JSONL mode emits structured records:

```jsonl
{"type":"thread","thread_id":"thread-id","starops_url":"https://starops.console.aliyun.com/chat?threadId=thread-id&assistantId=apsara-ops"}
{"type":"message","role":"assistant","content":"answer"}
{"type":"done","thread_id":"thread-id","status":"completed"}
```

Pipe mode emits:

```text
THREAD: thread-id
STAROPS_URL: https://starops.console.aliyun.com/chat?threadId=thread-id&assistantId=apsara-ops
=== STAROPS ANSWER BEGIN ===
answer
=== STAROPS ANSWER END ===
```

The console URL uses the same digital employee ID as `assistantId`.

Pipe mode writes progress to stderr, including tool status lines such as:

```text
[tool:started] query_metrics
[tool:running] generate_diagnosis_report
[tool:done] query_metrics
```

`generate_diagnosis_report` text chunks are also mirrored to stderr for live visibility and included in the final stdout answer block.
