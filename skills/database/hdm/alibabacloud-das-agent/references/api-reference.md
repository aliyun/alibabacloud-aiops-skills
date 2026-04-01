# DAS Agent API Reference

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ALIBABA_CLOUD_DAS_AGENT_ID` | Yes | DAS Agent ID (alias: `AGENT_ID`) |

Credentials are resolved through the Alibaba Cloud Credentials default provider chain. That means the script no longer reads `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` directly, but those variables can still be one valid source if your runtime configures the default chain that way.

## API Endpoint

- **URL**: `https://das.cn-shanghai.aliyuncs.com/`
- **Method**: POST
- **Action**: `Chat`
- **Signature**: ACS3-HMAC-SHA256 ([Alibaba Cloud API Signature Documentation](https://help.aliyun.com/document_detail/185337.htm))
- **Credential Source**: Alibaba Cloud Credentials default provider chain ([官方文档](https://help.aliyun.com/zh/sdk/developer-reference/v2-manage-python-access-credentials))
- **STS Support**: if the resolved credential includes a security token, the request adds `x-acs-security-token`

## Request Body

```
Format=JSON
SecureTransport=true
Message=<URL-encoded JSON: {"id":"uuid","role":"user","content":[{"type":"text","text":"..."}]}>
SourceTlsVersion=TLSv1.2
AcceptLanguage=zh-CN
AgentId=<agent_id>
SessionId=<uuid>
```

## SSE Event Types

The API returns a Server-Sent Events stream. Each line starts with `data:` followed by a JSON object with a `Type` field:

| Type | Key Fields | Description |
|------|-----------|-------------|
| `TEXT_MESSAGE_START` | `MessageId`, `Role` | New message begins. `Role` is `assistant` or `tool`. |
| `TEXT_MESSAGE_CONTENT` | `MessageId`, `Delta` | Incremental text chunk for the current message. |
| `TEXT_MESSAGE_END` | `MessageId` | Current message is complete. |
| `TOOL_CALL_START` | `ToolCallId`, `Name` | DAS Agent is invoking an internal tool. |
| `TOOL_CALL_ARGS` | `ToolCallId`, `Delta` | Streaming tool call arguments. |
| `TOOL_CALL_RESULT` | `ToolCallId`, `Delta`/`Result`/`Content` | Tool execution result (may arrive via different fields). |
| `TOOL_CALL_CHUNK` | `ToolCallId`, `Chunk` | Chunked tool result for large outputs. |
| `TOOL_CALL_END` | `ToolCallId`, `Result` | Tool call is complete. |
| `ACTIVITY_DELTA` | — | Heartbeat / thinking indicator. |
| `CUSTOM` | `Name`, `Value` | Custom events. `Name=error` carries `Value.Code` and `Value.Message`. |
| `RUN_STARTED` | — | Agent run begins. |
| `RUN_FINISHED` | — | Agent run ends. |

The stream ends with `data:[DONE]`.

## JSON Output Schema

When using `--json` mode, the script emits one JSON object per line to **stdout** (JSONL). All output goes to stdout — no stderr.

Two output modes are available:

| Mode | Flag | Description |
|------|------|-------------|
| CLI (Default) | *(none)* | Real-time streaming: text streamed as received, tool calls displayed with progress |
| JSON | `--json` | JSONL: one JSON object per line, machine-readable |

JSON mode event types:

```jsonl
{"type": "session", "session_id": "a1b2c3d4-..."}
{"type": "message", "role": "assistant", "content": "Diagnostic results..."}
{"type": "tool_call", "tool": "das_api", "status": "started"}
{"type": "tool_output", "tool": "das_api", "content": "API execution successful. Response: ..."}
{"type": "tool_result", "tool": "das_api", "args": "{\"command\":\"execute\",...}"}
{"type": "progress", "message": "HTTP error: 500"}
{"type": "error", "code": "-1810006", "message": "agent not associated with any instance"}
```

| type | Fields | Description |
|------|--------|-------------|
| `session` | `session_id` | Server-assigned session ID (always first event). Reuse this ID for multi-turn conversations. |
| `message` | `role`, `content` | Assistant response text |
| `tool_call` | `tool`, `status` | Tool invocation started |
| `tool_output` | `tool`, `content` | Raw API response data (may be truncated if >5000 chars) |
| `tool_result` | `tool`, `args` | Tool completion with arguments used |
| `progress` | `message` | Progress/status information |
| `error` | `code`, `message` | Error event |
