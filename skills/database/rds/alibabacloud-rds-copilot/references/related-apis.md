# Related APIs - RDS Copilot

## API List

| Product | API Version | API Action | CLI Command | Description |
|---------|-------------|------------|-------------|-------------|
| RdsAi | 2025-05-07 | ChatMessages | `aliyun rdsai chat-messages` | RDS AI Assistant dialogue API |
| RdsAi | 2025-05-07 | GetChatModel | `aliyun rdsai get-chat-model` | Auxiliary: query models available for ChatMessages |

## API Details

### ChatMessages

- **Product**: rdsai
- **API Version**: 2025-05-07
- **Endpoint**: rdsai.aliyuncs.com
- **CLI Command**: `aliyun rdsai chat-messages`
- **Description**: Call RDS AI Assistant for dialogue, returns streaming response

**CLI Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--query` | String | Yes | User query content |
| `--inputs` | Key=Value | No | Input parameters, multiple parameters separated by space |
| `--event-mode` | String | No | Event mode, options: `separate` |
| `--conversation-id` | String | No | Conversation ID for multi-turn dialogue |
| `--endpoint` | String | Yes | API endpoint: `rdsai.aliyuncs.com` |
| `--user-agent` | String | Yes | Custom User-Agent: `AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}` |

**--inputs Supported Parameters**:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `RegionId` | Region ID | `cn-hangzhou` |
| `Language` | Language | `zh-CN` |
| `Timezone` | Timezone | `Asia/Shanghai` |
| `CustomAgentId` | Custom Agent ID | None |
| `EnableThinking` | Deep thinking mode switch: `true` (enabled) or `false` (disabled) | None |
| `ThinkEffort` | Thinking depth: `default` (auto), `high` (deeper reasoning), `low` (faster responses) | None |
| `ModelId` | Model ID for the response model. The supported list is dynamic: query it via `aliyun rdsai get-chat-model` (see GetChatModel below) and verify EVERY user-specified model ID before use (including well-known ones such as `qwen3.8-max`) | None |

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| ConversationId | String | Conversation ID |
| MessageId | String | Message ID |
| Answer | String | AI assistant's response content |
| Event | String | Event type |

### GetChatModel

- **Product**: rdsai
- **API Version**: 2025-05-07
- **Endpoint**: rdsai.aliyuncs.com
- **CLI Command**: `aliyun rdsai get-chat-model`
- **Description**: Auxiliary API that queries the models available for ChatMessages. Supports GET/POST over HTTPS and takes no input parameters. Not part of the main call flow — ChatMessages works without calling it.
- **Usage**: Invoke only when the user explicitly sets a `ModelId` (to verify it is supported), asks which models are available, or checks a model's supported `ThinkEffort` values; calls that omit `ModelId` need no lookup.

**CLI Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--endpoint` | String | Yes | API endpoint: `rdsai.aliyuncs.com` |
| `--user-agent` | String | Yes | Custom User-Agent: `AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}` |

**Response Fields** (top-level `Data` array):

| Field | Type | Description |
|-------|------|-------------|
| ModelId | String | Model ID accepted by the `ModelId` input of ChatMessages |
| Default | Boolean | Whether this is the default model used when `ModelId` is omitted |
| ThinkingLevels | Array of String | Supported `ThinkEffort` values for this model |
| Features | Array of String | Model capabilities, e.g. `text`, `vision` |
| ContextWindow | Integer | Model context window size |

**Response Example** (truncated — the actual list is dynamic and must come from the live response):

```json
{
  "Data": [
    {
      "Features": ["text", "vision"],
      "ContextWindow": 1000000,
      "Default": true,
      "ModelId": "qwen3.8-max",
      "ThinkingLevels": ["default", "low", "high"]
    },
    {
      "Features": ["text"],
      "ContextWindow": 1000000,
      "Default": false,
      "ModelId": "glm-5.2",
      "ThinkingLevels": ["default", "low", "high"]
    }
  ]
}
```

## Alibaba Cloud CLI Usage Examples

### Basic Query

```bash
aliyun rdsai chat-messages \
  --query 'List RDS instances' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

### Troubleshooting

```bash
aliyun rdsai chat-messages \
  --query 'RDS instance rm-bp1pjojb0k8vi8p6j suddenly had connection timeout this morning, logs keep showing ERROR 1040 (HY000): Too many connections, users cannot access the system. Please help troubleshoot and provide solutions. Instance is in Hangzhou region.' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

### Query Specific Region

```bash
aliyun rdsai chat-messages \
  --query 'List MySQL instances in Beijing region' \
  --inputs RegionId=cn-beijing Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

### Multi-turn Dialogue

```bash
# First turn
aliyun rdsai chat-messages \
  --query 'Analyze SELECT * FROM users WHERE id = 1' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'

# Second turn (using ConversationId from previous response)
aliyun rdsai chat-messages \
  --query 'How to optimize this SQL' \
  --conversation-id '8227be22-5c94-4f6d-9b9e-a5f639a3740c' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

### Using Custom Agent

```bash
aliyun rdsai chat-messages \
  --query 'Analyze database performance' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai CustomAgentId=your-custom-agent-id \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

### Using Deep Thinking Mode

Optional `--inputs` parameters `EnableThinking`, `ThinkEffort`, and `ModelId` control the deep thinking mode, thinking depth, and response model:

```bash
aliyun rdsai chat-messages \
  --query 'Diagnose slow SQL on the instance and provide an optimization plan. Instance is in Hangzhou region.' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai EnableThinking=true ThinkEffort=high ModelId=qwen3.8-max \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

To use a different supported model, change only the `ModelId` value (verify every user-specified model ID via `get-chat-model` first, including well-known ones such as `qwen3.8-max`):

```bash
aliyun rdsai chat-messages \
  --query 'Analyze database performance' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai ModelId=<model ID from get-chat-model> \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

**Model availability is dynamic**: do not hardcode a model list. `get-chat-model` is an auxiliary check, but calling it **before** `chat-messages` is mandatory when a model ID is explicitly set (any model ID, including well-known ones such as `qwen3.8-max`), when the user asks which models are available, or when deep thinking / a specific thinking depth is requested; calls that omit `ModelId` need no lookup:

```bash
aliyun rdsai get-chat-model \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

**Default model**: the entry with `Default=true` in the GetChatModel response is the model used when `ModelId` is omitted.

**Forward compatibility**: `ModelId` is passed through to the API as-is. New model IDs appear in the GetChatModel response automatically once the API supports them — verify the new ID with `get-chat-model`, then pass it in the call; no skill configuration or code change is required.

### Using Specific Credential Profile

```bash
aliyun rdsai chat-messages \
  --query 'Query instance information' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}' \
  --profile rdsai
```

## Response Example

```json
{"data":{"ConversationId":"8227be22-5c94-4f6d-9b9e-a5f639a3740c","CreatedAt":1775143912,"Event":"workflow_started","MessageId":"a79c881c-0c3e-525d-b9fd-97829880d"}}
{"data":{"Answer":"Based on your description, the RDS instance has exceeded the connection limit...","Event":"message"}}
{"data":{"Event":"workflow_finished"}}
```

## Error Codes

| HTTP Status | Error Code | Description | Handling |
|-------------|------------|-------------|----------|
| 451 | `ContentModeration` | The request contains non-compliant content | Ask the user to rephrase the query |
| 400 | `InvalidParameter` | One or more parameters are invalid | Check `--inputs` values (e.g. `EnableThinking`, `ThinkEffort`, `ModelId`), fix them, then retry. If an unsupported `ModelId` is the cause, run `aliyun rdsai get-chat-model` to fetch the current supported models and guide the user to pick one, or contact technical support |
| 400 | `InvalidOrder` | No valid RDS AI Assistant Professional Edition order found | Guide the user to activate Professional Edition, then retry the failed call |
| 404 | `UserNotFound` | The user does not exist | Verify the CLI credential configuration and the account |
| 429 | `TooManyRequests` | The maximum concurrent request threshold is exceeded | Wait before retrying, or suggest purchasing an AI capacity pack to raise the concurrency limit |
| 429 | `MoQuotaExceeded` | The MO token quota of the routed Standard instance is exhausted and the request is rate limited | Wait for quota recovery, or suggest purchasing a capacity pack |

## CLI Command Line Options

| Option | Description |
|--------|-------------|
| `--endpoint` | Specify API endpoint, set to `rdsai.aliyuncs.com` |
| `--user-agent` | Specify User-Agent, set to `AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}` |
| `--profile` | Specify credential profile name |
| `--region` | Specify region for API call |
| `--quiet` | Suppress normal output |

## Reference Links

| Document | Description |
|----------|-------------|
| [Alibaba Cloud CLI Documentation](https://help.aliyun.com/zh/cli/) | CLI installation and usage guide |
| [Command Line Options](https://help.aliyun.com/zh/cli/command-line-options) | CLI command line options reference |
| [Parameter Format](https://help.aliyun.com/zh/cli/parameter-format-overview) | CLI parameter format requirements |
| [Configure Credentials](https://help.aliyun.com/zh/cli/configure-credentials) | CLI credential configuration methods |
