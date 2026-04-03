# Related APIs - RDS Copilot

## API List

| Product | API Version | API Action | CLI Command | Description |
|---------|-------------|------------|-------------|-------------|
| RdsAi | 2025-05-07 | ChatMessages | `aliyun rdsai chat-messages` | RDS AI Assistant dialogue API |

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
| `--user-agent` | String | Yes | Custom User-Agent: `AlibabaCloud-Agent-Skills` |

**--inputs Supported Parameters**:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `RegionId` | Region ID | `cn-hangzhou` |
| `Language` | Language | `zh-CN` |
| `Timezone` | Timezone | `Asia/Shanghai` |
| `CustomAgentId` | Custom Agent ID | None |

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| ConversationId | String | Conversation ID |
| MessageId | String | Message ID |
| Answer | String | AI assistant's response content |
| Event | String | Event type |

## Alibaba Cloud CLI Usage Examples

### Basic Query

```bash
aliyun rdsai chat-messages \
  --query 'List RDS instances' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'
```

### Troubleshooting

```bash
aliyun rdsai chat-messages \
  --query 'RDS instance rm-bp1pjojb0k8vi8p6j suddenly had connection timeout this morning, logs keep showing ERROR 1040 (HY000): Too many connections, users cannot access the system. Please help troubleshoot and provide solutions. Instance is in Hangzhou region.' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'
```

### Query Specific Region

```bash
aliyun rdsai chat-messages \
  --query 'List MySQL instances in Beijing region' \
  --inputs RegionId=cn-beijing Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'
```

### Multi-turn Dialogue

```bash
# First turn
aliyun rdsai chat-messages \
  --query 'Analyze SELECT * FROM users WHERE id = 1' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'

# Second turn (using ConversationId from previous response)
aliyun rdsai chat-messages \
  --query 'How to optimize this SQL' \
  --conversation-id '8227be22-5c94-4f6d-9b9e-a5f639a3740c' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'
```

### Using Custom Agent

```bash
aliyun rdsai chat-messages \
  --query 'Analyze database performance' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai CustomAgentId=your-custom-agent-id \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'
```

### Using Specific Credential Profile

```bash
aliyun rdsai chat-messages \
  --query 'Query instance information' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills' \
  --profile rdsai
```

## Response Example

```json
{"data":{"ConversationId":"8227be22-5c94-4f6d-9b9e-a5f639a3740c","CreatedAt":1775143912,"Event":"workflow_started","MessageId":"a79c881c-0c3e-525d-b9fd-97829880d"}}
{"data":{"Answer":"Based on your description, the RDS instance has exceeded the connection limit...","Event":"message"}}
{"data":{"Event":"workflow_finished"}}
```

## CLI Command Line Options

| Option | Description |
|--------|-------------|
| `--endpoint` | Specify API endpoint, set to `rdsai.aliyuncs.com` |
| `--user-agent` | Specify User-Agent, set to `AlibabaCloud-Agent-Skills` |
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
