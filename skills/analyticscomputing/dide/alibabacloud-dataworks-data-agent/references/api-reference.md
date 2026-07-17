# DataWorks Data Agent API Reference

API Version: 2024-05-18 | Protocol: JSON-RPC 2.0

All APIs are called via `aliyun dataworks-public <action>` with `--params` and `--user-agent`.

## Scope

This tool covers Agent Session management APIs only (8 APIs).

## Parameter Formats

| Format | Applicable APIs | Example |
|---|---|---|
| JSON string | create-agent-session, prompt-agent-session, list-agent-sessions, load-agent-session | `--params '{"Key": "value"}'` |
| Flat key=value | All others | `--params Key1=val1 Key2=val2``

---

## Session Management

### create-agent-session — Create Session

```bash
aliyun dataworks-public create-agent-session --profile default --region cn-shanghai \
  --params '{"Meta":{"Agent":{"AgentName":"dataworks_data_agent"},"Config":{"SessionSource":"cli"}}}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

**--params (JSON):**

```json
{
  "Meta": {
    "Agent": { "AgentName": "string" },
    "Config": {
      "SessionSource": "string",
      "SessionTags": ["tag1", "tag2"]
    }
  }
}
```

Returns: `JsonRpcResponse.Result.SessionId`

### prompt-agent-session — Send Prompt (SSE Streaming)

```bash
aliyun dataworks-public prompt-agent-session --profile default --region cn-shanghai \
  --params '{"SessionId":"xxx","Prompt":[{"Type":"text","Text":"hello"}]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

**--params (JSON):**

```json
{
  "SessionId": "string",
  "Prompt": [
    {
      "Type": "text",
      "Text": "user message",
      "Name": "filename.csv",
      "Uri": "file:///path/to/file",
      "MimeType": "text/csv"
    }
  ],
  "Meta": { "Context": "string (JSON double-encoded, e.g. \"{\\\"datasetUuid\\\":\\\"xxx\\\"}\")" }
}
```

**SSE Response (JSONL, one per line):**

```jsonl
{"data":{"Jsonrpc":"2.0","Method":"session/update","Params":{"sessionId":"xxx","update":{"content":{"text":"chunk","type":"text"},"sessionUpdate":"agent_message_chunk"}}}}
{"data":{"Jsonrpc":"2.0","Result":{"stopReason":"end_turn"}}}
```

- Text chunk: `Params.update.sessionUpdate == "agent_message_chunk"` → concatenate `content.text`
- End signal: `Result.stopReason == "end_turn"`
- Error: `Error.code` + `Error.message`

### load-agent-session — Load Session History (SSE Streaming)

```bash
aliyun dataworks-public load-agent-session --profile default --region cn-shanghai \
  --params '{"SessionId":"xxx","Meta":{"BeginLogOffset":0,"IsReload":true}}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

**--params (JSON):**

| Parameter | Type | Required | Description |
|---|---|---|---|
| SessionId | string | Yes | Target session ID |
| Meta.BeginLogOffset | int | No | Start loading from this offset (default: 0) |
| Meta.IsReload | bool | No | Force reload from beginning |

**SSE Response (JSONL):**

- Config update: `Params.update.sessionUpdate == "config_option_update"` → read `configOptions`
- History messages: `Params.update.sessionUpdate == "agent_message_chunk"` → concatenate `content.text`
- End signal: `Result.stopReason`
- Non-existent session returns SSE error frame with code 400

### list-agent-sessions — List Sessions

```bash
aliyun dataworks-public list-agent-sessions --profile default --region cn-shanghai \
  --params '{"AgentName":"dataworks_data_agent","MaxResults":10}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

**--params (JSON):**

| Parameter | Type | Required | Description |
|---|---|---|---|
| AgentName | string | **Yes** | Agent name |
| MaxResults | int | No | Page size |
| NextToken | string | No | Pagination cursor |
| SessionTitle | string | No | Filter by title |

Returns: `JsonRpcResponse.Result.AgentSessions[]` — each with `SessionId`, `SessionTitle`, `Meta.SessionSource`, `Meta.SessionStatus`, timestamps

### cancel-agent-session — Cancel Session

```bash
aliyun dataworks-public cancel-agent-session --profile default --region cn-shanghai \
  --params 'SessionId=xxx' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| SessionId | string | Yes | Session ID to cancel |

Returns: `JsonRpcResponse.Result.SessionId`

---

## Artifacts

### list-agent-session-artifacts — List Artifacts

```bash
aliyun dataworks-public list-agent-session-artifacts --profile default --region cn-shanghai \
  --params 'SessionId=xxx MaxResults=50' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

Returns: `JsonRpcResponse.Result.Artifacts[]` — each with `ArtifactName`, `ArtifactPath`, `ArtifactType`

### get-agent-session-artifact-meta — Get Artifact Content

```bash
aliyun dataworks-public get-agent-session-artifact-meta --profile default --region cn-shanghai \
  --params 'SessionId=xxx ArtifactPath=/csv/report.csv' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

Returns: `JsonRpcResponse.Result.ArtifactContent`

---

## Token Usage

### get-agent-session-token-usage

```bash
aliyun dataworks-public get-agent-session-token-usage --profile default --region cn-shanghai \
  --params 'SessionId=xxx' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

Returns: `{PromptTokens, CompletionTokens, CachedTokens, ThoughtsTokens, TotalTokens}`
