# Acceptance Criteria: alibabacloud-rds-copilot

**Scenario**: RDS Copilot Intelligent Operations Assistant
**Purpose**: Skill Test Acceptance Criteria

---

## 0. Environment Readiness Gate

### ✅ CORRECT - Preflight Before RDS Copilot API Calls

```bash
command -v aliyun
aliyun version
aliyun configure set --auto-plugin-install true
aliyun plugin list
aliyun plugin search rdsai
# Run only if the previous checks do not show the rdsai plugin/command.
aliyun plugin install --names rdsai
aliyun rdsai --help
aliyun configure list
```

Expected handling:
- If Alibaba Cloud CLI is missing or lower than `3.3.3`, install or upgrade it first.
- If `aliyun plugin` is unavailable, treat it as an old CLI and upgrade before plugin operations.
- If the `rdsai` plugin/command is missing, install it or trigger auto-install before calling ChatMessages.
- If CLI credentials are missing or invalid, stop before `aliyun rdsai chat-messages` and guide credential setup.
- If the user does not specify a region, use `cn-hangzhou`.
- System commands in this preflight must not use `--user-agent`; only `aliyun rdsai chat-messages` business API commands use per-command `--user-agent`.

### ❌ INCORRECT - Calling ChatMessages Before Preflight

```bash
# Wrong: skips CLI/plugin/credential readiness checks
aliyun rdsai chat-messages \
  --query 'List RDS instances' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

---

## 1. Environment Configuration Verification

### ✅ CORRECT - Using Alibaba Cloud CLI to Configure Credentials

```bash
# Correct: Use aliyun configure to configure credentials (relies on default credential chain)
aliyun configure --mode AK --profile rdsai
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
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
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
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
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
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
# Output: ConversationId: conv-xxxx-xxxx

# Second turn (using conversation ID from first turn)
aliyun rdsai chat-messages \
  --query 'Continue optimization' \
  --conversation-id 'conv-xxxx-xxxx' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

---

## 5. Error Handling Verification

### ✅ CORRECT - Check Credential Configuration

```bash
# Check if CLI credentials are configured
aliyun configure list
```

Expected handling when no valid credential is configured:
- Do not call `aliyun rdsai chat-messages`.
- Tell the user the CLI credential is not ready.
- Provide `aliyun configure --mode AK --profile rdsai` for interactive setup.
- If the agent is asked to configure credentials, request AccessKeyId, AccessKeySecret, optional SecurityToken/Profile, and RegionId defaulting to `cn-hangzhou`.

### ✅ CORRECT - Error Output to stderr

```bash
# If credentials are not configured, CLI will output error message
aliyun rdsai chat-messages --query 'Test' ... 2>&1 | grep -i error
```

### ✅ CORRECT - No Valid Order Error

```text
No valid order found
```

Expected handling:
- Explain that this failed call did not find a valid RDS AI Assistant Professional Edition order, and the current Alibaba Cloud account needs to enable Professional Edition before retrying this failed call.
- Return the Professional Edition activation page directly: https://rdsnext.console.aliyun.com/rdsCopilotProfessional/cn-hangzhou
- Return the operation guide: https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/manage-rds-colipot-professional-edition

---

## 6. Observability Verification

### ✅ CORRECT - Session User-Agent Format

```text
session-id: 32-character lowercase hex generated once per RDS Copilot task
User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}
```

Expected handling:
- Generate the `session-id` once before the first business API call.
- Reuse the same `session-id` for every `aliyun rdsai chat-messages` command in the same task.
- Do not use deprecated global User-Agent configuration mechanisms.
- Do not add `--user-agent` to system commands such as `aliyun configure`, `aliyun plugin`, `aliyun version`, install commands, or upgrade commands.

### ❌ INCORRECT - Missing Session Id Segment

A User-Agent value that omits the trailing `/{session-id}` segment fails this check.

---

## 7. User-Agent Verification

### ✅ CORRECT - User-Agent Configured

```bash
# Correct: Include --user-agent parameter
aliyun rdsai chat-messages \
  --query 'Test' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
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

- [ ] Alibaba Cloud CLI installed and version >= `3.3.3` (`aliyun version`)
- [ ] `rdsai` plugin/command is available before ChatMessages (`aliyun plugin search rdsai` / `aliyun rdsai --help`)
- [ ] CLI credentials configured and valid (`aliyun configure list`)
- [ ] Missing credentials stop the workflow before API calls and return setup guidance
- [ ] Region defaults to `cn-hangzhou` when omitted
- [ ] Basic query successful (`aliyun rdsai chat-messages --query 'Test' ...`)
- [ ] Streaming output works correctly
- [ ] Multi-turn dialogue works (`--conversation-id`)
- [ ] Observability chapter declares 32-character hex `session-id` generation and UA template `AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}`
- [ ] User-Agent configured only on business API commands (`--user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'`)
- [ ] Error messages output to stderr
- [ ] Response content output to stdout
