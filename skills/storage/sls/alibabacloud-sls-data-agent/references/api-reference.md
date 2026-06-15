# SLS DataAgent API Reference

This skill calls the SLS DataAgent (StarOps) OpenAPI with **ACS3-HMAC-SHA256** signing.

- **Endpoint**: defaults to `starops.cn-beijing.aliyuncs.com`; override with `SLS_DATA_AGENT_ENDPOINT`
  (e.g. another region: `starops.<region>.aliyuncs.com`).
- **API version**: `2026-04-28` (sent as the `x-acs-version` header).
- **Scope**: SLS **project**.

> The request/response shapes below describe what the script actually sends. Confirm the action
> names / API version match your backend if you point `SLS_DATA_AGENT_ENDPOINT` elsewhere.

## Authentication & common headers

Requests are signed with Alibaba Cloud Credentials default-chain credentials. The script builds the
ACS3 canonical request, signs it with `ACS3-HMAC-SHA256`, and sends HTTPS requests directly.

Every request carries these headers (signed except `Authorization` itself):

```text
host:                  <endpoint>
content-type:          application/json; charset=utf-8
x-acs-action:          CreateThread | CreateChat
x-acs-version:         2026-04-28
x-acs-date:            <ISO8601 UTC>
x-acs-signature-nonce: <uuid>
x-acs-content-sha256:  <sha256(body)>
x-acs-security-token:  <STS token>      # only when using STS credentials
Authorization:         ACS3-HMAC-SHA256 Credential=<AK>,SignedHeaders=...,Signature=...
```

## CreateThread

```http
POST /digitalEmployee/{name}/thread
```

`{name}` is the digital employee (agentId); defaults to `apsara-ops` (override with `--digital-employee`).

Body:

```json
{
  "title": "short question title",
  "idempotencyKey": "<sha256(employee|project|title)>",
  "variables": {
    "project": "ai-data-poc",
    "region": "cn-beijing",
    "skill": "sop"
  },
  "attributes": {
    "source": "sls-data-agent-skill"
  }
}
```

Expected response field:

```json
{ "threadId": "thread-id" }
```

## CreateChat

```http
POST /chat
```

Body:

```json
{
  "action": "create",
  "digitalEmployeeName": "apsara-ops",
  "threadId": "thread-id",
  "messages": [
    {
      "messageId": "uuid",
      "role": "user",
      "contents": [ { "type": "text", "value": "<message value, see below>" } ]
    }
  ],
  "variables": {
    "project": "ai-data-poc",
    "region": "cn-beijing",
    "skill": "sop"
  }
}
```

### Message value (`--skill` injection)

```text
<code vibeops_object type="vibeops-skill"><skill id="skills.builtin.sls.sls-sql-generation"/></code> <code vibeops_object type="logstore"><logstore name="ai_data_ot" project="ai-data-poc" region="cn-beijing" /></code> top 5 services by error log count in the last 1 hour
```

The response is an SSE stream whose `data:` payloads contain `messages`. The script stops when the
stream emits a `done` message or a `task_finished` event, and always closes the streaming HTTP
response before exiting.

## Output modes

JSONL mode emits structured records (the `data_agent_url` field is included only when a console URL
is configured — defaults to `https://starops.console.aliyun.com/chat`, override with
`SLS_DATA_AGENT_CONSOLE_URL`):

```jsonl
{"type":"thread","thread_id":"thread-id","data_agent_url":"https://starops.console.aliyun.com/chat?threadId=thread-id&assistantId=apsara-ops"}
{"type":"message","role":"assistant","content":"answer"}
{"type":"done","thread_id":"thread-id","status":"completed"}
```

Pipe mode emits:

```text
THREAD: thread-id
DATA_AGENT_URL: https://starops.console.aliyun.com/chat?threadId=thread-id&assistantId=apsara-ops
=== DATA AGENT ANSWER BEGIN ===
answer
=== DATA AGENT ANSWER END ===
```

Pipe mode writes progress to stderr, including tool-status lines such as:

```text
[tool:started] query_data
[tool:running] generate_report
[tool:done] query_data
```
