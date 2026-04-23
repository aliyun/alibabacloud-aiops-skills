---
name: alibabacloud-polardbx-ai-assistant
description: |
  Alibaba Cloud PolarDB-X Distributed Database AI Assistant. Use for PolarDB-X cluster management,
  topology inspection, performance diagnostics, SQL optimization, data distribution analysis,
  elastic scaling diagnostics, connection/session analysis, security audit, backup/restore,
  parameter tuning, and other O&M operations.
  Triggers: "PolarDB-X", "distributed database", "pxc-", "DN/CN nodes", "data sharding",
  "PolarDB-X diagnostics", "PolarDB-X performance", "PolarDB-X slow SQL", "YaoChi Agent",
  "PolarDB-X topology", "PolarDB-X backup", "PolarDB-X security audit", "PolarDB-X scaling"
---

# PolarDB-X Distributed Database AI Assistant

This skill provides intelligent O&M capabilities for **Alibaba Cloud PolarDB-X distributed database**, powered by the DAS (Database Autonomy Service) `get-yao-chi-agent` API via the aliyun CLI DAS plugin.

**Architecture**: `Aliyun CLI` -> `DAS Plugin (Signature V3)` -> `get-yao-chi-agent API` -> PolarDB-X Intelligent Diagnostics

### Supported Capabilities

| Capability | Description |
|------------|-------------|
| Instance Information | Instance details, cluster configuration, version info |
| Topology Inspection | CN/DN node distribution, shard topology, data node status |
| Storage Information | Disk usage, storage capacity, space growth trends |
| SQL Optimization | Slow SQL analysis, distributed execution plan interpretation, index suggestions, cross-shard query optimization |
| Cluster Performance Monitoring | QPS/TPS/connections/throughput and other core metrics analysis |
| Connection & Session Analysis | Connection count monitoring, session troubleshooting, connection pool optimization |
| Security Audit | Whitelist, SSL, security policy audit |
| Backup Status Check | Backup completeness, retention policy, point-in-time recovery |
| Instance Health Check | Instance health status, running state verification |
| Log Diagnostics | Error log analysis, slow log troubleshooting |
| Data Distribution Analysis | Shard data skew detection, hotspot shard diagnostics |
| Elastic Scaling Diagnostics | Scale-out/in status, data migration progress, node load balancing |
| Parameter Tuning | Kernel parameter interpretation, change impact assessment, configuration recommendations |
| High Availability & DR | HA configuration assessment, disaster recovery architecture diagnostics, primary-standby status |
| Expiring Instance Query | Subscription instance expiration reminders, renewal status |

## Installation

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.

> **Pre-check: Aliyun CLI plugin update required**
> **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> **[MUST]** run `aliyun plugin update` to ensure that any existing plugins on your local machine are always up-to-date.

> **[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
> `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ai-assistant`

> **[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
> Run the following commands before any CLI invocation:
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ai-assistant"
> ```

> **[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
> AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
> ```bash
> aliyun configure ai-mode disable
> ```

```bash
# Install aliyun CLI
curl -fsSL https://aliyuncli.alicdn.com/install.sh | bash
aliyun version  # Verify >= 3.3.3

# Enable automatic plugin installation
aliyun configure set --auto-plugin-install true

# Install DAS plugin (get-yao-chi-agent requires plugin for Signature V3 support)
aliyun plugin install --names aliyun-cli-das

# Install jq (for JSON response parsing)
# macOS:
brew install jq
# Ubuntu/Debian:
# sudo apt-get install jq
```

## Environment Variables

No additional environment variables are required. This skill relies entirely on the aliyun CLI's existing credential configuration.

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

Credentials are managed through aliyun CLI configuration — **no additional AK/SK setup is needed**:

```bash
# Recommended: OAuth mode
aliyun configure --mode OAuth

# Alternative: AK mode (configure outside of agent session)
aliyun configure set \
  --mode AK \
  --access-key-id <your-access-key-id> \
  --access-key-secret <your-access-key-secret> \
  --region cn-hangzhou

# Cross-account access: RamRoleArn mode
aliyun configure set \
  --mode RamRoleArn \
  --access-key-id <your-access-key-id> \
  --access-key-secret <your-access-key-secret> \
  --ram-role-arn acs:ram::<account-id>:role/<role-name> \
  --role-session-name yaochi-agent-session \
  --region cn-hangzhou
```

## RAM Policy

See [references/ram-policies.md](references/ram-policies.md) for the full list of required permissions.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default Value |
|-----------|-------------------|-------------|---------------|
| `query` | Required | Natural language query content (including region, instance info, etc.) | - |
| `--session-id` | Optional | Session ID for multi-turn conversation context | - |
| `--profile` | Optional | aliyun CLI profile name | default |

## Core Workflow

All intelligent O&M operations **MUST** be invoked through `scripts/call_yaochi_agent.sh`, which wraps the `aliyun das get-yao-chi-agent` (DAS plugin kebab-case command, supporting Signature V3) with streaming response parsing.

> **⚠️ CRITICAL RESTRICTION:**
> - **DO NOT** use direct `aliyun polardbx` or `aliyun rds` CLI commands for diagnostics, topology, or security audits.
> - **DO NOT** attempt to query instance details using `DescribeDBInstances` or similar APIs directly.
> - **ONLY** use the DAS plugin command: `aliyun das get-yao-chi-agent` (wrapped by `call_yaochi_agent.sh`).
> - If the script fails, check permissions via `ram-permission-diagnose` skill, **DO NOT** fallback to other product APIs.

```bash
# Cluster Management
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List PolarDB-X instances in Hangzhou region"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Show detailed configuration of instance pxc-xxx"

# Topology Inspection
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Show CN/DN node distribution of instance pxc-xxx"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Show shard topology of instance pxc-xxx"

# Performance Diagnostics
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Analyze performance of instance pxc-xxx in the last hour"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Show slow SQL of instance pxc-xxx"

# SQL Optimization
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Optimize execution plan of this SQL on instance pxc-xxx"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Which cross-shard queries on instance pxc-xxx need optimization"

# Data Distribution
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Check whether data distribution of instance pxc-xxx is even"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Are there any hotspot shards on instance pxc-xxx"

# Elastic Scaling
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Show scale-out status of instance pxc-xxx"

# Parameter Tuning
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "How to tune CONN_POOL_MAX_POOL_SIZE parameter on instance pxc-xxx"

# Connection & Session
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "How to troubleshoot high connection count on instance pxc-xxx"

# Backup & Restore
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Show backup status of instance pxc-xxx"

# Security Audit
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Check security configuration of instance pxc-xxx"

# High Availability & DR
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Show HA configuration of instance pxc-xxx"

# Multi-turn Conversation (use session ID returned from previous call)
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Continue analysis" --session-id "<session-id>"

# Specify profile
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List instances" --profile myprofile

# Read from stdin
echo "List instances" | bash $SKILL_DIR/scripts/call_yaochi_agent.sh -
```

### Typical Query Examples

| Scenario | Example Query |
|----------|---------------|
| Cluster Management | Show node list of instance pxc-xxx |
| Topology | How many CN and DN nodes does instance pxc-xxx have |
| Performance Diagnostics | How to troubleshoot high CPU usage on instance pxc-xxx |
| Slow SQL Analysis | Show slow SQL of instance pxc-xxx in the last hour |
| SQL Optimization | Why is this SELECT statement slow on instance pxc-xxx |
| Data Distribution | Is there data skew in shards of instance pxc-xxx |
| Elastic Scaling | What is the scale-out progress of instance pxc-xxx |
| Parameter Tuning | How to optimize connection pool parameters on instance pxc-xxx |
| Backup & Restore | When was the latest backup of instance pxc-xxx |
| Storage Optimization | What to do about rapid storage growth on instance pxc-xxx |
| Connection Troubleshooting | Instance pxc-xxx connection count is maxed out |
| Security Audit | Check security configuration of instance pxc-xxx |
| High Availability | Is the DR architecture of instance pxc-xxx reasonable |
| Expiration Reminder | Which PolarDB-X instances are about to expire |

## Success Verification

See [references/verification-method.md](references/verification-method.md) for detailed verification steps.

## Cleanup

This skill focuses on **query and diagnostics** capabilities only. It does not create any resources, so no cleanup is needed.

The following operations are **out of scope** for this skill:
- Creating/deleting PolarDB-X instances
- Changing instance specifications
- Purchasing/renewing instances

## Command Tables

See [references/related-apis.md](references/related-apis.md) for the full list of APIs and CLI commands.

## Best Practices

1. **Instance ID Format**: PolarDB-X instance IDs start with `pxc-`. Always include the full instance ID in queries.
2. **Region Specification**: Explicitly specify the region in natural language queries (e.g., "Hangzhou region", "Beijing region") to improve query accuracy.
3. **Multi-turn Conversation**: Use `--session-id` to maintain context continuity in complex diagnostic scenarios.
4. **Concurrency Limit**: Maximum 2 concurrent sessions per account. Avoid launching multiple parallel calls.
5. **Distributed Characteristics**: When troubleshooting issues, distinguish between CN (Compute Node) and DN (Data Node) layers.
6. **Throttling Handling**: If you encounter a `Throttling.UserConcurrentLimit` error, wait for the previous query to complete before retrying.
7. **Credential Security**: Use `aliyun configure` to manage credentials. Never hardcode AK/SK in scripts.

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and configuration guide |
| [references/related-apis.md](references/related-apis.md) | Related APIs and CLI command list |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policy list |
| [references/verification-method.md](references/verification-method.md) | Success verification methods |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria |
