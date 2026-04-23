---
name: alibabacloud-tair-ai-assistant
description: |
  Alibaba Cloud Tair (Redis OSS-Compatible) Database AI Assistant. For Tair/Redis instance management, performance diagnostics, memory analysis, hotspot key detection, latency troubleshooting, parameter tuning, connection session analysis.
  Use when user questions involve Tair, Redis, instance IDs starting with r-, memory analysis, hotspot keys, eviction policy, big key detection, etc.
---

# Tair Database AI Assistant

This Skill focuses on **Alibaba Cloud Tair (Redis OSS-Compatible) database** intelligent O&M, invoking the get-yao-chi-agent API through the aliyun CLI DAS plugin for diagnostics and analysis.

**Architecture**: `Aliyun CLI` → `DAS Plugin (Signature V3)` → `get-yao-chi-agent API` → Tair Intelligent Diagnostics

### Supported Capabilities

| Capability | Description |
|------------|-------------|
| Instance List Query | List and filter Tair/Redis instances by region, type, status |
| Memory Usage Analysis | Memory consumption breakdown, fragmentation ratio, eviction statistics |
| Hotspot Key Detection | Hot key identification, access frequency analysis, cache optimization |
| Big Key Analysis | Large key detection, memory distribution analysis, optimization suggestions |
| Latency Diagnostics | Command latency analysis, slow command detection, network latency troubleshooting |
| Slow Log Analysis | Slow command log query, high-latency operation identification |
| Parameter Tuning | Instance parameter explanation, configuration suggestions, performance impact analysis |
| Connection Session Analysis | Connection count monitoring, client session troubleshooting, connection pool optimization |
| Backup Status Check | Backup completion verification, retention policy, recovery point in time |
| Performance Monitoring | QPS/TPS/hit rate/bandwidth and other core metrics analysis |
| Expiring Instance Query | Subscription instance expiration reminder |
| Security Configuration Audit | Whitelist, SSL/TLS, password policy, security audit |
| Storage Optimization | Data structure optimization, TTL strategy, memory efficiency improvement |
| Proxy Diagnostics | Proxy layer performance analysis, connection routing, bandwidth bottleneck detection |

## Installation

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
> Then **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

```bash
# Install aliyun CLI
curl -fsSL https://aliyuncli.alicdn.com/install.sh | bash
aliyun version  # Verify >= 3.3.1

# Enable automatic plugin installation
aliyun configure set --auto-plugin-install true

# Install DAS plugin (get-yao-chi-agent requires plugin for Signature V3 support)
aliyun plugin install --names aliyun-cli-das

# Update all installed plugins to latest version
aliyun plugin update

# Install jq (for JSON response parsing)
# macOS:
brew install jq
# Ubuntu/Debian:
# sudo apt-get install jq
```

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `query` | Required | Natural language query content (including region, instance info) | - |
| `--session-id` | Optional | Session ID for multi-turn conversation | - |
| `--profile` | Optional | aliyun CLI profile name | default |

## Authentication

This Skill relies on the **aliyun CLI default credential chain** for authentication — no explicit AK/SK handling is required in the Skill workflow.

The CLI automatically resolves credentials in the following priority order:
1. `--profile` flag on the command line
2. `ALIBABA_CLOUD_PROFILE` environment variable
3. `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` environment variables
4. Configuration file `~/.aliyun/config.json` (current profile)
5. ECS Instance RAM Role (if running on ECS)

For credential setup and configuration modes (OAuth, AK, StsToken, RamRoleArn, EcsRamRole, etc.), see [references/cli-installation-guide.md](references/cli-installation-guide.md).

## RAM Policy

See [references/ram-policies.md](references/ram-policies.md)

## Core Workflow

All intelligent O&M operations are invoked through `scripts/call_yaochi_agent.sh`, which wraps `aliyun das get-yao-chi-agent` (DAS plugin kebab-case command, supports Signature V3) with streaming response parsing.

**Before executing any CLI command, AI-Mode must be enabled; after workflow ends, it must be disabled:**

```bash
# [MUST] Enable AI-Mode before executing CLI commands
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-tair-ai-assistant"
```

```bash
# Instance management
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List Tair instances in Hangzhou region"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Show detailed configuration of instance r-xxx"

# Performance diagnostics
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Analyze instance r-xxx performance in the last hour"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Show slow commands of instance r-xxx"

# Memory analysis
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Analyze memory usage of instance r-xxx"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Detect big keys in instance r-xxx"

# Hotspot key detection
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Find hotspot keys in instance r-xxx"

# Parameter tuning
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "How to tune maxmemory-policy for instance r-xxx"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Explain hz parameter"

# Connection and session
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "How to troubleshoot high connection count in instance r-xxx"

# Backup recovery
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Show backup status of instance r-xxx"

# Multi-turn conversation (use session ID from previous response)
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Continue analysis" --session-id "<session-id>"

# Specify profile
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List instances" --profile myprofile

# Read from stdin
echo "List instances" | bash $SKILL_DIR/scripts/call_yaochi_agent.sh -
```

```bash
# [MUST] Disable AI-Mode after workflow ends
aliyun configure ai-mode disable
```

### Example Questions

| Scenario | Example Question |
|----------|------------------|
| Instance Management | List Tair instances in Beijing region |
| Performance Diagnostics | How to troubleshoot high CPU usage in instance r-xxx |
| Slow Log Analysis | Show slow commands in instance r-xxx in the last hour |
| Memory Analysis | Analyze memory fragmentation of instance r-xxx |
| Big Key Detection | Detect big keys in instance r-xxx and suggest optimization |
| Hotspot Key | Find hotspot keys in instance r-xxx |
| Parameter Tuning | What does maxmemory-policy parameter mean |
| Master-Replica | How to handle high replication delay in instance r-xxx |
| Backup Recovery | When was the latest backup of instance r-xxx |
| Connection Troubleshooting | Instance r-xxx connections are full |
| Security Audit | Check security configuration of instance r-xxx |

## Success Verification

See [references/verification-method.md](references/verification-method.md)

## Cleanup

This Skill focuses on **query and diagnostics** capabilities, does not create any resources, no cleanup required.

The following operations are NOT within the scope of this Skill:
- Create/delete Tair instances
- Change instance specifications
- Purchase/renew instances

## API and Command Tables

See [references/related-apis.md](references/related-apis.md)

## Best Practices

1. **Instance ID Format**: Tair/Redis instance IDs typically start with `r-`, include the full instance ID in queries
2. **Region Specification**: Explicitly specify region in natural language queries (e.g., "Hangzhou region", "Beijing region") to improve query accuracy
3. **Multi-turn Conversation**: Use `--session-id` for complex diagnostic scenarios to maintain context continuity
4. **Concurrency Limit**: Maximum 2 concurrent sessions per account, avoid initiating multiple parallel calls
5. **High-risk Operations**: For operations involving parameter changes, master-replica switchover, always remind users to verify in test environment first
6. **Throttling Handling**: If encountering `Throttling.UserConcurrentLimit` error, wait for previous query to complete and retry
7. **Credential Security**: Use `aliyun configure` to manage credentials, never hardcode AK/SK in scripts

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and configuration guide |
| [references/related-apis.md](references/related-apis.md) | Related API and CLI command list |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policy list |
| [references/verification-method.md](references/verification-method.md) | Success verification methods |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria |
