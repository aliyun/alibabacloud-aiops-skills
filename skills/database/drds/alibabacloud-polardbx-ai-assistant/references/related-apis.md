# Related APIs

## DAS (Database Autonomy Service) - Core API

| Product | CLI Command | API Action | Description |
|---------|------------|------------|-------------|
| DAS | `aliyun das get-yao-chi-agent --query "<query>" --source "polardbx-console" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills` | GetYaoChiAgent | YaoChi Agent (SSE streaming response) |
| DAS | `aliyun das get-das-agent-sse --Query "<query>" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills` | GetDasAgentSSE | DAS Agent SSE API |

## GetYaoChiAgent API Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--query` | String | Yes | Natural language query content |
| `--source` | String | No | Call source identifier, set to `polardbx-console` |
| `--session-id` | String | No | Session ID for multi-turn conversation context |

## GetDasAgentSSE API Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--Query` | String | Yes | Natural language query content |
| `--AgentId` | String | No | Agent ID |
| `--InstanceId` | String | No | Database instance ID |
| `--SessionId` | String | No | Session ID for multi-turn conversation context |

## SSE Response Format

GetYaoChiAgent returns SSE (Server-Sent Events) streaming response:

```
data: {"Content":"Response text chunk 1","SessionId":"sess-xxx","ReasoningContent":""}
data: {"Content":"Response text chunk 2","SessionId":"sess-xxx","ReasoningContent":""}
...
data: [DONE]
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `Content` | String | Current chunk text content |
| `SessionId` | String | Session ID for multi-turn conversation |
| `ReasoningContent` | String | Reasoning content (for debug) |

## API Endpoint

| Environment | Endpoint |
|-------------|----------|
| Production | `das.cn-shanghai.aliyuncs.com` |

> Note: GetYaoChiAgent API uses `das.cn-shanghai.aliyuncs.com` endpoint uniformly, regardless of the PolarDB-X instance's region.
