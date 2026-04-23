# Related APIs

## DAS (Database Autonomy Service) - Core API

| Product | CLI Command | API Action | Description |
|---------|------------|------------|-------------|
| DAS | `aliyun das GetYaoChiAgent --Query "<query>" --Source "tair-console" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills` | GetYaoChiAgent | YaoChi Intelligent Diagnostic Agent (SSE streaming response) |
| DAS | `aliyun das GetDasAgentSSE --Query "<query>" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills` | GetDasAgentSSE | DAS Agent SSE interface |

## GetYaoChiAgent API Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--Query` | String | Yes | Natural language query content |
| `--Source` | String | No | Call source identifier, recommended to set as `tair-console` |
| `--SessionId` | String | No | Session ID for multi-turn conversation context preservation |
| `--ExtraInfo` | String | No | Extra information |

## GetDasAgentSSE API Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--Query` | String | Yes | Natural language query content |
| `--AgentId` | String | No | Agent ID |
| `--InstanceId` | String | No | Database instance ID |
| `--SessionId` | String | No | Session ID for multi-turn conversation context preservation |

## SSE Response Format

GetYaoChiAgent returns SSE (Server-Sent Events) streaming response in the following format:

```
data: {"Content":"Response text chunk 1","SessionId":"sess-xxx","ReasoningContent":""}
data: {"Content":"Response text chunk 2","SessionId":"sess-xxx","ReasoningContent":""}
...
data: [DONE]
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `Content` | String | Text content of current chunk |
| `SessionId` | String | Session ID for multi-turn conversation |
| `ReasoningContent` | String | Reasoning process content (for debugging) |

## API Endpoint

| Environment | Endpoint |
|-------------|----------|
| Production | `das.cn-shanghai.aliyuncs.com` |

> Note: GetYaoChiAgent API uses `das.cn-shanghai.aliyuncs.com` endpoint uniformly, regardless of the region where the user's Tair instance is located.
