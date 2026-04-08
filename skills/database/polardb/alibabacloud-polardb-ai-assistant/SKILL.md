---
name: alibabacloud-polardb-ai-assistant
description: |
  Alibaba Cloud PolarDB Database AI Assistant. For PolarDB MySQL/PostgreSQL cluster management, performance diagnostics, parameter tuning, slow SQL analysis, backup recovery, connection session analysis, primary-standby switchover diagnostics, security configuration audit, and other O&M operations.
  Use when user questions involve PolarDB, cluster IDs starting with pc-, kernel parameters, primary-standby switchover, IMCI columnar storage, etc.
---

# PolarDB Database AI Assistant

This Skill focuses on **Alibaba Cloud PolarDB MySQL/PostgreSQL database** intelligent O&M, invoking the get-yao-chi-agent API through the aliyun CLI DAS plugin for diagnostics and analysis.

**Architecture**: `Aliyun CLI` → `DAS Plugin (Signature V3)` → `get-yao-chi-agent API` → PolarDB Intelligent Diagnostics

### Supported Capabilities

| Capability | Description |
|------------|-------------|
| PolarDB Primary-Standby Switchover Analysis | Failover cause investigation, switchover log analysis, unexpected Failover diagnostics |
| PolarDB Kernel Parameter Change Assessment | Impact assessment before parameter modification, change risk analysis |
| PolarDB Kernel Parameter Explanation | Parameter meaning explanation, configuration suggestions, performance impact analysis |
| PolarDB Kernel Parameter Explanation (IMCI) | IMCI columnar engine related parameter explanation |
| PolarDB Kernel Version Proxy Diagnostics | Proxy layer troubleshooting, version compatibility diagnostics |
| PolarDB Kernel Version Instance Diagnostics | Instance layer version issue diagnostics, upgrade suggestions |
| Instance Query Filter | PolarDB instance search and filtering |
| Proxy Performance Monitoring | Proxy layer performance metrics analysis, connection routing diagnostics |
| Serverless Configuration | Serverless instance parameters and elastic scaling configuration |
| SQL Optimization Analysis | Slow SQL analysis, index suggestions, execution plan interpretation |
| Expiring Instance Query | Subscription instance expiration reminder |
| Backup Status Check | Backup completion, retention policy, recovery point in time |
| Storage Usage Diagnostics | Storage consumption analysis, growth trends, space optimization suggestions |
| Security Configuration Audit | Whitelist, SSL, security policy audit |
| Instance Status Check | Instance health status, running status verification |
| Log Diagnostics | Error log analysis, slow log troubleshooting |
| Auto-Increment ID Overflow Detection | Auto-increment ID exhaustion risk detection, primary key overflow warning |
| Connection and Session Analysis | Connection count monitoring, session issue troubleshooting, connection pool optimization |
| Cluster Performance Monitoring | QPS/TPS/connections/throughput and other core metrics analysis |
| High Availability and Disaster Recovery | HA configuration assessment, disaster recovery architecture diagnostics |

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
| `query` | Required | Natural language query content (including region, cluster info) | - |
| `--session-id` | Optional | Session ID for multi-turn conversation | - |
| `--profile` | Optional | aliyun CLI profile name | default |

## Authentication

Credentials use existing aliyun CLI configuration, **no additional AK/SK setup required**:

```bash
# Recommended: OAuth mode
aliyun configure --mode OAuth

# Or: AK mode
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

See [references/ram-policies.md](references/ram-policies.md)

## Core Workflow

All intelligent O&M operations are invoked through `scripts/call_yaochi_agent.sh`, which wraps `aliyun das get-yao-chi-agent` (DAS plugin kebab-case command, supports Signature V3) with streaming response parsing.

```bash
# Cluster management
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List PolarDB clusters in Hangzhou region"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Show detailed configuration of cluster pc-xxx"

# Performance diagnostics
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Analyze cluster pc-xxx performance in the last hour"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Show slow SQL of cluster pc-xxx"

# Parameter tuning
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "How to tune innodb_buffer_pool_size for cluster pc-xxx"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Explain loose_polar_log_bin parameter"

# Primary-standby switchover diagnostics
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Analyze recent primary-standby switchover cause for cluster pc-xxx"

# Connection and session
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "How to troubleshoot high connection count in cluster pc-xxx"

# Backup recovery
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Show backup status of cluster pc-xxx"

# Multi-turn conversation (use session ID from previous response)
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Continue analysis" --session-id "<session-id>"

# Specify profile
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List clusters" --profile myprofile

# Read from stdin
echo "List clusters" | bash $SKILL_DIR/scripts/call_yaochi_agent.sh -
```

### Example Questions

| Scenario | Example Question |
|----------|------------------|
| Cluster Management | List nodes of cluster pc-xxx |
| Performance Diagnostics | How to troubleshoot high CPU usage in cluster pc-xxx |
| Slow SQL Analysis | Show slow SQL in cluster pc-xxx in the last hour |
| Parameter Tuning | What does loose_polar_log_bin parameter mean |
| IMCI Parameters | How to configure IMCI related parameters for cluster pc-xxx |
| Primary-Standby | How to handle high primary-standby delay in cluster pc-xxx |
| Backup Recovery | When was the latest backup of cluster pc-xxx |
| Storage Optimization | What to do if storage usage of cluster pc-xxx grows too fast |
| Connection Troubleshooting | Cluster pc-xxx connections are full |
| Security Audit | Check security configuration of cluster pc-xxx |

## Success Verification

See [references/verification-method.md](references/verification-method.md)

## Cleanup

This Skill focuses on **query and diagnostics** capabilities, does not create any resources, no cleanup required.

The following operations are NOT within the scope of this Skill:
- Create/delete PolarDB clusters
- Change instance specifications
- Purchase/renew instances

## API and Command Tables

See [references/related-apis.md](references/related-apis.md)

## Best Practices

1. **Cluster ID Format**: PolarDB cluster IDs typically start with `pc-`, include the full cluster ID in queries
2. **Region Specification**: Explicitly specify region in natural language queries (e.g., "Hangzhou region", "Beijing region") to improve query accuracy
3. **Multi-turn Conversation**: Use `--session-id` for complex diagnostic scenarios to maintain context continuity
4. **Concurrency Limit**: Maximum 2 concurrent sessions per account, avoid initiating multiple parallel calls
5. **High-risk Operations**: For operations involving parameter changes, primary-standby switchover, always remind users to verify in test environment first
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
