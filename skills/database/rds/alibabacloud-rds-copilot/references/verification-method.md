# Verification Method - RDS Copilot

This document describes how to verify that the RDS Copilot skill is correctly configured and running.

## Prerequisites Verification

### 1. Verify Alibaba Cloud CLI Installation

```bash
aliyun version
```

**Expected Result**: Outputs CLI version number, e.g., `3.0.277`

**If not installed**:

```bash
# macOS - Install via Homebrew
brew install aliyun-cli

# macOS/Linux - Install via one-click script
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"
```

### 2. Verify Credential Configuration

```bash
# View configured credentials list
aliyun configure list
```

**Expected Result**: Outputs configured credential information

**If not configured**:

```bash
# Interactive configuration
aliyun configure --profile rdsai

# Or non-interactive configuration
aliyun configure set \
  --profile rdsai \
  --mode AK \
  --access-key-id <yourAccessKeyID> \
  --access-key-secret <yourAccessKeySecret> \
  --region cn-hangzhou
```

## Functionality Verification

### 3. Verify Basic Query Functionality

```bash
aliyun rdsai chat-messages \
  --query 'Hello, please introduce yourself' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'
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

### 4. Verify Troubleshooting Functionality

```bash
aliyun rdsai chat-messages \
  --query 'RDS instance rm-bp1xxx connection timeout, error Too many connections, please help troubleshoot.' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'
```

**Expected Result**: Returns response with troubleshooting recommendations

### 5. Verify Region-specific Query Functionality

```bash
aliyun rdsai chat-messages \
  --query 'List instances' \
  --inputs RegionId=cn-beijing Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'
```

**Expected Result**: Returns query results related to Beijing region

### 6. Verify Multi-turn Dialogue Functionality

```bash
# First turn
RESULT=$(aliyun rdsai chat-messages \
  --query 'Analyze SELECT * FROM users WHERE id = 1' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills' 2>&1)
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
  --user-agent 'AlibabaCloud-Agent-Skills'
```

**Expected Result**: Second turn understands context and provides recommendations related to first turn

## Error Handling Verification

### 7. Verify Missing Credentials Error Handling

```bash
# Use non-existent profile
aliyun rdsai chat-messages \
  --query 'Test' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills' \
  --profile nonexistent
```

**Expected Result**: Outputs error message indicating profile does not exist

## Verification Checklist

| Verification Item | Command | Expected Result |
|-------------------|---------|-----------------|
| CLI Installation | `aliyun version` | Shows version number |
| Credential Configuration | `aliyun configure list` | Shows configuration info |
| Basic Query | `aliyun rdsai chat-messages --query '...' ...` | Returns JSON response |
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
aliyun configure --profile rdsai
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
  --user-agent 'AlibabaCloud-Agent-Skills' \
  --dryrun
```
