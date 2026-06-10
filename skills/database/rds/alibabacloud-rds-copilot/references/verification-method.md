# Verification Method - RDS Copilot

This document describes how to verify that the RDS Copilot skill is correctly configured and running.

## Prerequisites Verification

### 1. Verify Alibaba Cloud CLI Installation and Version

```bash
command -v aliyun
aliyun version
```

**Expected Result**: Outputs CLI version number, e.g., `3.3.3` (must be >= 3.3.3)

**If not installed**:

```bash
# macOS - Install via Homebrew
brew install aliyun-cli

# macOS/Linux - Install via one-click script
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"
```

**If installed but lower than 3.3.3**:

```bash
# CLI 3.3.5+ non-Homebrew install
aliyun upgrade --yes

# macOS Homebrew install
brew update
brew upgrade aliyun-cli

# Fallback for old 3.0.x CLI versions that do not support plugin commands
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"
```

### 2. Verify RdsAi Plugin Readiness

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin list
aliyun plugin search rdsai
# Run only if the previous checks do not show the rdsai plugin/command.
aliyun plugin install --names rdsai
aliyun rdsai --help
```

**Expected Result**:
- `aliyun plugin` is available. If it is not available, upgrade Alibaba Cloud CLI first.
- The `rdsai` product plugin/command is available before any `aliyun rdsai chat-messages` call.
- These system commands do not use `--user-agent`; User-Agent is only passed on business API commands.

### 3. Verify Credential Configuration

```bash
# View configured credentials list
aliyun configure list
```

**Expected Result**: Outputs configured credential information

**If not configured**:

```bash
# Interactive configuration
aliyun configure --mode AK --profile rdsai

# Or non-interactive configuration
aliyun configure set \
  --profile rdsai \
  --mode AK \
  --access-key-id <yourAccessKeyID> \
  --access-key-secret <yourAccessKeySecret> \
  --region cn-hangzhou
```

Stop here until credentials are configured. Do not run `aliyun rdsai chat-messages` with empty or invalid credentials.

### 4. Verify Observability Session Id

```bash
openssl rand -hex 16
```

**Expected Result**: Generates one 32-character lowercase hex `session-id`, for example `0123456789abcdef0123456789abcdef`.

Use this User-Agent template for every business API call in the same task:

```text
AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}
```

Do not use deprecated global User-Agent configuration mechanisms. Do not add `--user-agent` to system commands such as `aliyun configure`, `aliyun plugin`, `aliyun version`, install commands, or upgrade commands.

## Functionality Verification

### 5. Verify Basic Query Functionality

```bash
aliyun rdsai chat-messages \
  --query 'Hello, please introduce yourself' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

**Expected Result**:
- Returns JSON format response (streaming multiple JSON events)
- Contains `ConversationId` field
- Contains `Answer` field with RDS Copilot's self-introduction
- Contains `Event` field

**Example Output**:
```json
{"data":{"ConversationId":"8227be22-xxxx-xxxx-xxxx-xxxxxxxxxxxx","Event":"workflow_started",...}}
{"data":{"Answer":"I am Alibaba Cloud RDS Copilot, an intelligent assistant designed for database operations...","Event":"message",...}}
{"data":{"Event":"workflow_finished",...}}
```

### 6. Verify Troubleshooting Functionality

```bash
aliyun rdsai chat-messages \
  --query 'RDS instance rm-bp1xxx connection timeout, error Too many connections, please help troubleshoot.' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

**Expected Result**: Returns response with troubleshooting recommendations

### 7. Verify Default Region Behavior

When the user does not specify a region, the agent must still pass `RegionId=cn-hangzhou`:

```bash
aliyun rdsai chat-messages \
  --query 'List RDS instances' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

**Expected Result**: The command uses `cn-hangzhou`; no placeholder region remains in the final command.

### 8. Verify Region-specific Query Functionality

```bash
aliyun rdsai chat-messages \
  --query 'List instances' \
  --inputs RegionId=cn-beijing Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

**Expected Result**: Returns query results related to Beijing region

### 9. Verify Multi-turn Dialogue Functionality

```bash
# First turn
RESULT=$(aliyun rdsai chat-messages \
  --query 'Analyze SELECT * FROM users WHERE id = 1' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}' 2>&1)
echo "$RESULT"

# Extract ConversationId
CONV_ID=$(echo "$RESULT" | grep -oP '"ConversationId":"[^"]+' | head -1 | cut -d'"' -f4)
echo "ConversationId: $CONV_ID"

# Second turn
aliyun rdsai chat-messages \
  --query 'How to optimize this SQL' \
  --conversation-id "$CONV_ID" \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

**Expected Result**: Second turn understands context and provides recommendations related to first turn

## Error Handling Verification

### 10. Verify Missing Credentials Error Handling

```bash
# Use non-existent profile
aliyun rdsai chat-messages \
  --query 'Test' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}' \
  --profile nonexistent
```

**Expected Result**: Outputs error message indicating profile does not exist

Agent handling must stop before retrying the RDS Copilot API repeatedly and should guide:

```bash
aliyun configure --mode AK --profile rdsai
```

If the user asks the agent to configure credentials, request these fields:
- AccessKeyId
- AccessKeySecret
- Optional SecurityToken for temporary credentials
- Profile name, default `rdsai`
- RegionId, default `cn-hangzhou`

## Verification Checklist

| Verification Item | Command | Expected Result |
|-------------------|---------|-----------------|
| CLI Installation | `command -v aliyun && aliyun version` | Shows version >= 3.3.3 |
| RdsAi Plugin | `aliyun plugin search rdsai` / `aliyun rdsai --help` | `rdsai` command is available before ChatMessages |
| Credential Configuration | `aliyun configure list` | Shows a valid configured credential |
| Observability | `openssl rand -hex 16` and per-command `--user-agent` | 32-character hex session-id, UA format includes the session-id |
| Basic Query | `aliyun rdsai chat-messages --query '...' ...` | Returns JSON response |
| Default Region | `--inputs RegionId=cn-hangzhou ...` | Uses cn-hangzhou when the user omits region |
| Region-specific | `aliyun rdsai chat-messages --inputs RegionId=cn-beijing ...` | Correct region |
| Multi-turn Dialogue | `aliyun rdsai chat-messages --conversation-id '...' ...` | Context correlation |

## Common Issues

### Q1: Error "command not found: aliyun"

**Solution**: Install Alibaba Cloud CLI

```bash
brew install aliyun-cli
```

### Q2: Error "InvalidAccessKeyId" or "SignatureDoesNotMatch"

**Solution**: Check if credentials are configured correctly

```bash
aliyun configure --mode AK --profile rdsai
```

### Q3: Error "ServiceUnavailable" or connection timeout

**Solution**: Check network connection, ensure access to `rdsai.aliyuncs.com`

### Q4: How to view complete request and response

**Solution**: Use `--dryrun` option to simulate the call

```bash
aliyun rdsai chat-messages \
  --query 'Test' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}' \
  --dryrun
```

### Q5: Error "No valid order found"

**Solution**: Only handle this as Professional Edition activation guidance when the actual CLI response or user-pasted error contains `No valid order found`. This error means the current call did not find a valid RDS AI Assistant Professional Edition order. Return the Professional Edition activation page directly and ask the user to enable Professional Edition before retrying this failed call.

- Activation page: https://rdsnext.console.aliyun.com/rdsCopilotProfessional/cn-hangzhou
- Operation guide: https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/manage-rds-colipot-professional-edition

The guide describes opening the RDS console, choosing **RDS AI Assistant > Professional Edition**, clicking **Activate Now**, configuring the purchase, and retrying after the Professional Edition instance is available.
