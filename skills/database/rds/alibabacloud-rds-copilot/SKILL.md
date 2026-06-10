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

## Agent Execution Contract

Before calling RDS Copilot, the agent must make the local environment ready by itself whenever command execution is available. Do not ask the user to install CLI or plugins first if the agent can install or upgrade them directly.
If install or upgrade needs network access, sudo, or tool approval, request that approval with the concrete command and continue after approval.

**Hard gate**: Do not execute `aliyun rdsai chat-messages` until all readiness checks pass:

1. Alibaba Cloud CLI exists and `aliyun version` is >= `3.3.3`.
2. Plugin auto-install is enabled and the `rdsai` product plugin/command is available.
3. Alibaba Cloud CLI credentials are configured and the selected profile is valid.

If any gate fails:

- Missing or old CLI: install or upgrade Alibaba Cloud CLI, then re-run `aliyun version`.
- Missing `rdsai` plugin: enable plugin auto-install and install or trigger installation of `rdsai`, then re-check the command.
- Missing/invalid credentials: stop before the RDS Copilot API call and guide the user to configure credentials. If the user asks the agent to configure them, request only the required fields, then configure through `aliyun configure`; never ask the user to paste secrets into environment variables.

**Default region**: If the user does not explicitly provide a region, always use `cn-hangzhou`. Natural language "Hangzhou" maps to `cn-hangzhou`. Keep this default in both `--inputs RegionId=cn-hangzhou` and any credential setup guidance unless the user specifies another region.

---

## Installation

> **Agent preflight: Alibaba Cloud CLI must be installed or installed by the agent**
>
> This skill uses Alibaba Cloud CLI to call RdsAi OpenAPI. The agent must first check whether the CLI is present and usable. If the CLI is missing and command execution is available, install it before asking the user to take manual action.

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `command -v aliyun` and `aliyun version` to verify >= 3.3.3.
> If not installed or version is too low, install or update it before proceeding.
> CLI versions below 3.3.0 do not support the `aliyun plugin` command; upgrade the CLI first instead of running plugin commands repeatedly.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] verify the `rdsai` plugin capability with `aliyun plugin list`, `aliyun plugin search rdsai`, or `aliyun rdsai --help`.
> [MUST] if `rdsai` is not installed, run `aliyun plugin install --names rdsai` and re-check.
> [MUST] run `aliyun plugin update --name rdsai` when the plugin is already installed; if the CLI only supports `aliyun plugin update`, use that and continue.

**[MUST] CLI User-Agent** — Every `aliyun rdsai chat-messages` invocation must include a per-command `--user-agent` value in this format:
`AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}`.
See the Observability section for session-id generation rules. Do not pass `--user-agent` to system commands such as `aliyun configure`, `aliyun plugin`, `aliyun version`, or install/upgrade commands.

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
command -v aliyun
aliyun version
```

---

## Credential Configuration

### Option 1: Interactive Configuration (Recommended)

```bash
aliyun configure --mode AK --profile rdsai
```

Follow the prompts to enter:
- **Access Key Id**: Your AccessKey ID
- **Access Key Secret**: Your AccessKey Secret
- **Default Region Id**: cn-hangzhou unless the user specifies another region

Before asking the user for secrets, explain that the recommended interactive command keeps the secret inside Alibaba Cloud CLI's credential store. Do not print or store the secret in chat history longer than needed.

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
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai [CustomAgentId=<custom agent ID>] \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}' \
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
| `--user-agent` | Required for business API commands | Custom User-Agent | `AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}` |

---

## RAM Permissions

This skill requires the following RAM permissions. See [references/ram-policies.md](references/ram-policies.md) for details.

| Permission | Description |
|------------|-------------|
| `rdsai:ChatMessages` | Call RDS AI Assistant API |

---

## Core Workflow

### 0. Environment Readiness Preflight (Before Calling RDS Copilot)

Run this preflight once at the start of every RDS Copilot task. Do not skip it because the user only asked a simple query.

```bash
# 0.1 Check Alibaba Cloud CLI existence and version
command -v aliyun
aliyun version
```

If `aliyun` is missing, install it by choosing the safest available local method:

```bash
# macOS, when Homebrew is available
brew install aliyun-cli

# macOS/Linux fallback
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"
```

If `aliyun version` is lower than `3.3.3`, upgrade it before running plugin commands:

```bash
# CLI 3.3.5+ non-Homebrew install
aliyun upgrade --yes

# macOS Homebrew install
brew update
brew upgrade aliyun-cli

# Fallback for old CLI versions such as 3.0.x that do not support plugin commands
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"
```

After install or upgrade, re-run `aliyun version`.

```bash
# 0.2 Enable and verify plugin support. These are system commands; do not add --user-agent.
aliyun configure set --auto-plugin-install true
aliyun plugin list
aliyun plugin search rdsai

# Run only if the previous checks do not show the rdsai plugin/command.
aliyun plugin install --names rdsai

# Final capability check. This may also trigger auto-install after auto-plugin-install is enabled.
aliyun rdsai --help
```

If `aliyun plugin` returns an error such as `'plugin' is not a valid command or product`, the CLI is too old. Upgrade the CLI first; do not keep retrying plugin commands.

```bash
# 0.4 Check credentials before the first API call
aliyun configure list
```

Treat these credential states as **not ready**:

- No profile is listed.
- The selected or default profile has empty `Credential`.
- `Valid` is `Invalid` or not shown as valid.
- The command reports `unknown profile`, `InvalidAccessKeyId`, `SignatureDoesNotMatch`, missing AccessKey, expired STS token, or similar authentication errors.

When credentials are not ready, stop before `aliyun rdsai chat-messages` and answer with credential guidance:

```bash
# Recommended interactive setup
aliyun configure --mode AK --profile rdsai

# Non-interactive setup if the user explicitly asks the agent to configure credentials
aliyun configure set \
  --profile rdsai \
  --mode AK \
  --access-key-id <AccessKeyId> \
  --access-key-secret <AccessKeySecret> \
  --region cn-hangzhou
```

If the user wants the agent to configure credentials, ask for:

- Credential mode: default to `AK` unless the user says OAuth, STS, RAM role, EcsRamRole, or another supported mode.
- Profile name: default to `rdsai`.
- AccessKeyId and AccessKeySecret for AK mode, or the mode-specific fields for STS/RAM-role modes.
- STS token if using temporary credentials.
- RegionId: default `cn-hangzhou` if not specified.

Never use `export ALIBABA_CLOUD_ACCESS_KEY_ID=...` or `export ALIBABA_CLOUD_ACCESS_KEY_SECRET=...` as the normal setup path. Use `aliyun configure` so credentials stay in the CLI credential store.

### 1. Confirm Task Type and Parameters

Determine user intent: SQL writing/optimization, SQL diagnosis, instance parameter tuning, troubleshooting, performance analysis, query instance list, etc.

Collect necessary parameters (use default values if not specified):

- `RegionId`: Region ID (default `cn-hangzhou`; use this if omitted)
- `Language`: Language (default `zh-CN`)
- `Timezone`: Timezone (default `Asia/Shanghai`)
- `CustomAgentId`: Custom Agent ID (optional)
- `--conversation-id`: Conversation ID for multi-turn dialogue (optional)

### 2. Construct Command and Call CLI

Only run this step after the environment readiness preflight succeeds. Always include `RegionId`; if the user does not provide a region, use `cn-hangzhou`.
Before the first business API call, generate one session-id using the Observability rules below and reuse it for all `aliyun rdsai chat-messages` calls in this RDS Copilot task.

```bash
# Basic query
aliyun rdsai chat-messages \
  --query 'List RDS MySQL instances in Hangzhou region' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'

# Troubleshooting example
aliyun rdsai chat-messages \
  --query 'RDS instance rm-bp1xxx connection timeout, error Too many connections, please help troubleshoot. Instance is in Hangzhou region.' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'

# Query with Beijing region
aliyun rdsai chat-messages \
  --query 'Optimize this SQL: SELECT * FROM users WHERE name LIKE "%test%"' \
  --inputs RegionId=cn-beijing Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'

# Multi-turn dialogue (using ConversationId from previous response)
aliyun rdsai chat-messages \
  --query 'Continue analyzing the above issue' \
  --conversation-id '<ConversationId from previous response>' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'

# Using custom Agent
aliyun rdsai chat-messages \
  --query 'Analyze database performance' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai CustomAgentId=your-custom-agent-id \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

### 3. Parse Results and Follow-up Processing

- Only when the response or user-pasted error contains `No valid order found`, stop normal result analysis and directly return this guidance to the user:
  - The current call did not find a valid RDS AI Assistant Professional Edition order. Enable RDS AI Assistant Professional Edition for the current Alibaba Cloud account, then retry the failed call.
  - Activation page: https://rdsnext.console.aliyun.com/rdsCopilotProfessional/cn-hangzhou
  - Operation guide: https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/manage-rds-colipot-professional-edition
  - According to the operation guide, create RDS AI Assistant Professional Edition from the RDS console by choosing **RDS AI Assistant > Professional Edition** and clicking **Activate Now**. After activation succeeds, retry the failed call with the enabled account.
- Explain RDS Copilot's response to the user in natural language
- If the response contains SQL or operational steps, assess risks and warn:
  - Avoid executing high-risk statements directly in production (e.g., large table `DELETE` / `UPDATE` / schema changes)
  - Recommend validating in test environment or adding backup/condition restrictions
- If continuing the conversation, record the `ConversationId` from the response for the next query

---

## Observability

Generate one `session-id` per RDS Copilot task/session before the first business API call. The `session-id` must be a 32-character lowercase hexadecimal string, generated once and reused for every `aliyun rdsai chat-messages` command in the same task, including multi-turn follow-ups.

Recommended generation methods:

```bash
openssl rand -hex 16
```

Fallback:

```bash
python3 -c 'import secrets; print(secrets.token_hex(16))'
```

User-Agent template:

```text
AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}
```

Apply this User-Agent only as a per-command `--user-agent` argument on business API commands:

```bash
aliyun rdsai chat-messages \
  --query '<query content>' \
  --inputs RegionId=cn-hangzhou Language=zh-CN Timezone=Asia/Shanghai \
  --event-mode separate \
  --endpoint rdsai.aliyuncs.com \
  --user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'
```

Do not use deprecated global User-Agent configuration mechanisms. Do not add `--user-agent` to system commands such as `aliyun configure`, `aliyun plugin`, `aliyun version`, `command -v aliyun`, install commands, or upgrade commands.

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
3. **Observability configured correctly**: Business API calls include `--user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-rds-copilot/{session-id}'` with a 32-character hex session-id
4. **API call successful**: Response contains `ConversationId` and `Answer` in JSON format
5. **Response content valid**: Answer is relevant to the query content

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
