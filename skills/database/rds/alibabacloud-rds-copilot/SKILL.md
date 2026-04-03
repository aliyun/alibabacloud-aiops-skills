---
name: alibabacloud-rds-copilot
description: |
  Alibaba Cloud RDS Copilot intelligent operations assistant skill. Used for RDS-related intelligent Q&A, SQL optimization, instance operations, and troubleshooting.
  Calls RdsAi OpenAPI through Alibaba Cloud CLI to get real-time RDS Copilot responses.
  Triggers: "RDS Copilot", "RDS Assistant", "SQL optimization", "RDS troubleshooting", "RDS operations", "database diagnosis"
---

# Alibaba Cloud RDS Copilot Intelligent Operations Assistant

This skill serves as an **intelligent agent for Alibaba Cloud RDS Copilot** in conversations, helping users with RDS-related intelligent Q&A, SQL optimization, instance operations, and troubleshooting.

## Scenario Description

**Architecture**: `Alibaba Cloud CLI + RdsAi OpenAPI`

Main features:
- **Understand user's natural language requests** (Chinese or English), identify if related to RDS Copilot
- **Directly call Alibaba Cloud CLI** to execute `aliyun rdsai chat-messages` command for real-time RDS Copilot queries
- When receiving results or user-pasted error messages, **further explain, diagnose, and provide recommendations**

---

## Installation

> **Pre-check: Alibaba Cloud CLI must be installed**
>
> This skill uses Alibaba Cloud CLI to call RdsAi OpenAPI. You need to install and configure Alibaba Cloud CLI first.

### macOS Installation

```bash
# Option 1: Install via Homebrew (recommended)
brew install aliyun-cli

# Option 2: Install via PKG package
curl -O https://aliyuncli.alicdn.com/aliyun-cli-latest.pkg
sudo installer -pkg aliyun-cli-latest.pkg -target /

# Option 3: Install via one-click script
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"
```

### Linux Installation

```bash
# Install via one-click script
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"

# Or download TGZ package for manual installation
curl https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz -o aliyun-cli.tgz
tar xzvf aliyun-cli.tgz
sudo mv aliyun /usr/local/bin/
```

### Verify Installation

```bash
aliyun version
```

---

## Credential Configuration

### Option 1: Interactive Configuration (Recommended)

```bash
aliyun configure --profile rdsai
```

Follow the prompts to enter:
- **Access Key Id**: Your AccessKey ID
- **Access Key Secret**: Your AccessKey Secret
- **Default Region Id**: cn-hangzhou (or other regions)

### Option 2: Non-interactive Configuration

```bash
aliyun configure set \
  --profile rdsai \
  --mode AK \
  --access-key-id <yourAccessKeyID> \
  --access-key-secret <yourAccessKeySecret> \
  --region cn-hangzhou
```

---

## Command Format

### Basic Command Structure

```bash
aliyun rdsai chat-messages \
  --query '<query content>' \
  --inputs RegionId=<region ID> Language=<language> Timezone=<timezone> [CustomAgentId=<custom agent ID>] \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills' \
  [--conversation-id '<conversation ID>']
```

### Parameter Description

> **IMPORTANT: Parameter Confirmation** — Before executing any command,
> Determine user intent: SQL writing/optimization, SQL diagnosis, instance parameter tuning, troubleshooting, performance analysis, query instance list, etc.
> Collect necessary parameters (use default values if not specified).

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `--query` | Required | User query content | - |
| `--inputs RegionId=` | Optional | Alibaba Cloud region ID | `cn-hangzhou` |
| `--inputs Language=` | Optional | Language | `zh-CN` |
| `--inputs Timezone=` | Optional | Timezone | `Asia/Shanghai` |
| `--inputs CustomAgentId=` | Optional | Custom Agent ID | None |
| `--event-mode` | Optional | Event mode | `separate` |
| `--endpoint` | Required | API endpoint | `rdsai.aliyuncs.com` |
| `--conversation-id` | Optional | Conversation ID for multi-turn dialogue | None |
| `--region` | Optional | Region for API call | Credential default region |
| `--profile` | Optional | Specify credential profile name | Default profile |
| `--user-agent` | Required | Custom User-Agent | `AlibabaCloud-Agent-Skills` |

---

## RAM Permissions

This skill requires the following RAM permissions. See [references/ram-policies.md](references/ram-policies.md) for details.

| Permission | Description |
|------------|-------------|
| `rdsai:ChatMessages` | Call RDS AI Assistant API |

---

## Core Workflow

### 1. Confirm Task Type and Parameters

Determine user intent: SQL writing/optimization, SQL diagnosis, instance parameter tuning, troubleshooting, performance analysis, query instance list, etc.

Collect necessary parameters (use default values if not specified):

- `RegionId`: Region ID (default `cn-hangzhou`)
- `Language`: Language (default `zh-CN`)
- `Timezone`: Timezone (default `Asia/Shanghai`)
- `CustomAgentId`: Custom Agent ID (optional)
- `--conversation-id`: Conversation ID for multi-turn dialogue (optional)

### 2. Construct Command and Call CLI

```bash
# Basic query
aliyun rdsai chat-messages \
  --query 'List RDS MySQL instances in Hangzhou region' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'

# Troubleshooting example
aliyun rdsai chat-messages \
  --query 'RDS instance rm-bp1xxx connection timeout, error Too many connections, please help troubleshoot. Instance is in Hangzhou region.' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'

# Query with Beijing region
aliyun rdsai chat-messages \
  --query 'Optimize this SQL: SELECT * FROM users WHERE name LIKE "%test%"' \
  --inputs RegionId=cn-beijing Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'

# Multi-turn dialogue (using ConversationId from previous response)
aliyun rdsai chat-messages \
  --query 'Continue analyzing the above issue' \
  --conversation-id '<ConversationId from previous response>' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'

# Using custom Agent
aliyun rdsai chat-messages \
  --query 'Analyze database performance' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai CustomAgentId=your-custom-agent-id \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'
```

### 3. Parse Results and Follow-up Processing

- Explain RDS Copilot's response to the user in natural language
- If the response contains SQL or operational steps, assess risks and warn:
  - Avoid executing high-risk statements directly in production (e.g., large table `DELETE` / `UPDATE` / schema changes)
  - Recommend validating in test environment or adding backup/condition restrictions
- If continuing the conversation, record the `ConversationId` from the response for the next query

---

## Output Format

Alibaba Cloud CLI returns JSON format responses (streaming multiple JSON events):

```json
{"data":{"ConversationId":"8227be22-xxxx-xxxx-xxxx-xxxxxxxxxxxx","Event":"workflow_started","MessageId":"a79c881c-xxxx-xxxx-xxxx-xxxxxxxxxxxx",...}}
{"data":{"Answer":"<partial answer content>","Event":"message",...}}
{"data":{"Event":"workflow_finished",...}}
```

Key fields:
- `ConversationId`: Conversation ID (for multi-turn dialogue)
- `Answer`: AI assistant's response content
- `Event`: Event type (workflow_started, message, workflow_finished)

---

## Success Verification

1. **CLI installation successful**: `aliyun version` shows version number
2. **Credential configured correctly**: `aliyun configure list` shows configured credentials
3. **API call successful**: Response contains `ConversationId` and `Answer` in JSON format
4. **Response content valid**: Answer is relevant to the query content

See [references/verification-method.md](references/verification-method.md) for detailed verification steps.

---

## Cleanup

This skill only performs read-only query operations, does not create any cloud resources, no cleanup required.

---

## API and Command List

See [references/related-apis.md](references/related-apis.md) for details.

| Product | API Action | CLI Command | Description |
|---------|------------|-------------|-------------|
| RdsAi | ChatMessages | `aliyun rdsai chat-messages` | RDS AI Assistant dialogue API |

---

## Best Practices

1. **Use multi-turn dialogue**: For complex issues, use `--conversation-id` for context-aware multi-turn conversations
2. **Specify correct region**: Set `RegionId` parameter based on the RDS instance's region
3. **Be cautious in production**: SQL recommendations from RDS Copilot should be validated in test environment first
4. **Save conversation ID**: Save the returned `ConversationId` if you need to follow up or continue analysis
5. **Use configuration file**: Recommend using `aliyun configure` to configure credentials, avoid exposing sensitive information in command line
6. **Use --profile**: You can configure multiple credential profiles and switch between accounts using `--profile`

---

## Reference Links

| Reference Document | Description |
|--------------------|-------------|
| [Alibaba Cloud CLI Documentation](https://help.aliyun.com/zh/cli/) | Alibaba Cloud CLI User Guide |
| [references/related-apis.md](references/related-apis.md) | API and Command List |
| [references/ram-policies.md](references/ram-policies.md) | RAM Policy Configuration |
| [references/verification-method.md](references/verification-method.md) | Verification Methods |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance Criteria |
