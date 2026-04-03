# Acceptance Criteria: alibabacloud-rds-copilot

**Scenario**: RDS Copilot Intelligent Operations Assistant
**Purpose**: Skill Test Acceptance Criteria

---

## 1. Environment Configuration Verification

### ✅ CORRECT - Using Alibaba Cloud CLI to Configure Credentials

```bash
# Correct: Use aliyun configure to configure credentials (relies on default credential chain)
aliyun configure --profile rdsai
```

### ❌ INCORRECT - Hardcoded Credentials

```bash
# Wrong: Explicitly setting AK/SK environment variables
export ALIBABA_CLOUD_ACCESS_KEY_ID="LTAI5txxxxxxxxxx"  # Do not set explicitly
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="xxxxxxxxxxxxxxxx"  # Do not set explicitly
```

---

## 2. CLI Command Verification

### ✅ CORRECT - Using Alibaba Cloud CLI

```bash
# Correct: Use aliyun CLI to call RDS AI API
aliyun rdsai chat-messages \
  --query 'List RDS instances' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'
```

### ❌ INCORRECT - Missing Required Parameters

```bash
# Wrong: Missing endpoint or user-agent
aliyun rdsai chat-messages \
  --query 'List RDS instances'
```

---

## 3. CLI Command Format Verification

### ✅ CORRECT - Contains Required Parameters

```bash
aliyun rdsai chat-messages \
  --query 'List RDS instances' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'
```

### ❌ INCORRECT - Wrong Endpoint

```bash
# Wrong: Using incorrect endpoint
aliyun rdsai chat-messages \
  --endpoint rds.aliyuncs.com  # Should be rdsai.aliyuncs.com
```

---

## 4. Multi-turn Dialogue Verification

### ✅ CORRECT - Using conversation_id

```bash
# First turn
aliyun rdsai chat-messages \
  --query 'Analyze this SQL performance' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'
# Output: ConversationId: conv-xxxx-xxxx

# Second turn (using conversation ID from first turn)
aliyun rdsai chat-messages \
  --query 'Continue optimization' \
  --conversation-id 'conv-xxxx-xxxx' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'
```

---

## 5. Error Handling Verification

### ✅ CORRECT - Check Credential Configuration

```bash
# Check if CLI credentials are configured
aliyun configure list
```

### ✅ CORRECT - Error Output to stderr

```bash
# If credentials are not configured, CLI will output error message
aliyun rdsai chat-messages --query 'Test' ... 2>&1 | grep -i error
```

---

## 6. User-Agent Verification

### ✅ CORRECT - User-Agent Configured

```bash
# Correct: Include --user-agent parameter
aliyun rdsai chat-messages \
  --query 'Test' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills'
```

### ❌ INCORRECT - Missing User-Agent

```bash
# Wrong: Missing --user-agent parameter
aliyun rdsai chat-messages \
  --query 'Test' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com
```

---

## Acceptance Checklist

- [ ] Alibaba Cloud CLI installed (`aliyun version`)
- [ ] CLI credentials configured (`aliyun configure list`)
- [ ] Basic query successful (`aliyun rdsai chat-messages --query 'Test' ...`)
- [ ] Streaming output works correctly
- [ ] Multi-turn dialogue works (`--conversation-id`)
- [ ] User-Agent configured (`--user-agent 'AlibabaCloud-Agent-Skills'`)
- [ ] Error messages output to stderr
- [ ] Response content output to stdout
