---
name: alibabacloud-polardb-ai-assistant
description: |
  Alibaba Cloud PolarDB Database AI Assistant. For PolarDB MySQL/PostgreSQL cluster management, instance inspection, performance diagnostics, parameter explanation and change assessment, SQL/log analysis, backup, security audit, HA/DR, event analysis, and other PolarDB O&M operations.
  Use when user questions involve PolarDB, cluster IDs starting with pc-, PolarDB kernel/proxy versions, parameters, primary-standby switchover, IMCI columnar storage, or PolarDB console operations. This Skill is PolarDB-only.
---

# PolarDB Database AI Assistant

This Skill focuses on **Alibaba Cloud PolarDB MySQL/PostgreSQL database** intelligent O&M. It invokes the Yaochi Agent v2 backend through the `get-yao-chi-agent` API and the aliyun CLI DAS plugin.

**Architecture**: `Codex Skill` -> `scripts/call_yaochi_agent.sh` -> `Aliyun CLI` -> `DAS Plugin (Signature V3)` -> `get-yao-chi-agent API` -> `Yaochi Agent v2` -> `PolarDB Skill/MCP/DAS/RAG capabilities`

**Scope**: PolarDB only. Do not use this Skill for non-PolarDB product O&M requests unless the user's request is explicitly about PolarDB integration or comparison.

### Supported Capabilities

| Capability | Description |
|------------|-------------|
| Instance query and filtering | Natural-language filtering for PolarDB clusters by ID, engine, version, status, pay type, zone, architecture, tags, name, creation window, or expiration window |
| Instance status inspection | Runtime status, node health, version, lock/migration state, endpoint state, pay type, and expiration checks |
| Cluster resource inspection | CPU, memory, connections, IOPS, storage, Serverless PCU behavior, capacity pressure, and trend analysis |
| Connection and session inspection | Connection usage, active sessions, idle transaction risk, connection trend, and connection pool suggestions |
| Proxy performance inspection | Proxy CPU, QPS, connection stability, response time, endpoint/routing information, and read/write split signal checks |
| Backup inspection | Backup policy, backup records, backup task status, log backup/PITR capability, and backup success/failure risk |
| Security inspection | Whitelist, public exposure risk, SSL/TDE, account security posture, and SQL audit configuration |
| High availability and disaster recovery | Multi-zone/HA posture, hot standby state, GDN/migration signals, HA switch records, and DR readiness |
| Log diagnostics | Error log and slow log volume, pattern analysis, and operational recommendations |
| Serverless inspection | PCU min/max configuration, scaling behavior, auto-pause posture, and workload-resource fit |
| Parameter explanation | PolarDB MySQL/PostgreSQL parameter meaning, defaults, risk, best practices, and restart/effective-scope notes |
| Parameter change assessment | Parameter modification log explanation, multi-parameter impact assessment, and change-risk suggestions |
| IMCI parameter explanation | PolarDB MySQL IMCI columnar index parameter explanation and usage guidance |
| Kernel and proxy version diagnostics | DB kernel/proxy version gap analysis, release-note based risk assessment, high-risk fixed bug checks, and upgrade suggestions |
| HA switchover and event analysis | HA switchover root cause, related performance/log evidence, event impact, and follow-up mitigation |
| Storage diagnostics | Storage composition, growth trend, abnormal usage, cold data/archive signals, and cleanup or capacity advice |
| SQL performance diagnostics | Slow SQL, execution plan, lock/blocking, and index optimization diagnostics when supported by backend and permissions |

### Backend Execution Model

The local Skill does not call PolarDB MCP tools directly. It sends a natural-language query to Yaochi Agent v2. The backend is responsible for:

1. Matching a PolarDB scenario Skill first when the request is an O&M, inspection, diagnosis, parameter, or event scenario.
2. Calling PolarDB MCP/OpenAPI tools for real cluster, metric, log, backup, security, or data-plane evidence.
3. Using DAS intelligent diagnosis for performance, slow SQL, lock, index, and auto-increment ID issues when applicable.
4. Falling back to PolarDB documentation/RAG only when structured tools cannot answer the question.

When answering users, treat the backend output as the source of truth. Do not invent cluster status, metrics, logs, risk levels, or document links that are not present in the response.

## Observability

**[MUST] User-Agent template** — Every Alibaba Cloud CLI, SDK, or Terraform invocation made by this Skill must use:
`AlibabaCloud-Agent-Skills/alibabacloud-polardb-ai-assistant/{session-id}`

**[MUST] Session-id rule** — Generate one observability session ID at the start of each Skill execution session, reuse the same value across all Alibaba Cloud CLI, SDK, and Terraform calls in that session, and do not regenerate it for retries or multi-step workflows. The session ID must be a 32-character lowercase hexadecimal string.

```bash
export ALIBABACLOUD_AGENT_SKILL_SESSION_ID="${ALIBABACLOUD_AGENT_SKILL_SESSION_ID:-$(openssl rand -hex 16)}"
```

**[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardb-ai-assistant/${ALIBABACLOUD_AGENT_SKILL_SESSION_ID}`

## Installation

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> download the installer, review it, then run it locally to update,
> or see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
> Then **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> Then **[MUST]** run `aliyun plugin update` to ensure that any existing plugins on your local machine are always up-to-date.

```bash
# Install aliyun CLI after reviewing the downloaded installer
curl -fsSL https://aliyuncli.alicdn.com/setup.sh -o /tmp/aliyun-cli-setup.sh
less /tmp/aliyun-cli-setup.sh
bash /tmp/aliyun-cli-setup.sh
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
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Diagnose lock blocking and index risks for PolarDB PostgreSQL cluster pc-xxx"

# Parameter tuning
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "How to tune innodb_buffer_pool_size for cluster pc-xxx"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Explain loose_polar_log_bin parameter"
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Compare parameters between pc-xxx and pc-yyy"

# Primary-standby switchover diagnostics
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Analyze recent primary-standby switchover cause for cluster pc-xxx"

# Connection and session
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "How to troubleshoot high connection count in cluster pc-xxx"

# Backup recovery
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Show backup status of cluster pc-xxx"

# Inspection
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Generate a health inspection report for cluster pc-xxx"

# Multi-turn conversation (use session ID from previous response)
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Continue analysis" --session-id "<session-id>"

# Specify profile
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List clusters" --profile myprofile

# Read from stdin
echo "List clusters" | bash $SKILL_DIR/scripts/call_yaochi_agent.sh -
```

### Error Handling

If `call_yaochi_agent.sh` fails, do not summarize it as only `Error: SDKError`.
Surface the structured error block from stderr to the user, especially:

```text
[YaoChi Agent Error]
ErrorCode: <aliyun error code>
ErrorMessage: <full error description>
AuthAction: <required RAM action, when returned>
RequestId: <request id, when returned>
Suggestion: <specific fix>
Reference: <local skill reference>
Troubleshooting: <Aliyun troubleshooting link>
```

For permission errors such as `Forbidden.RAM`, check `AuthAction` first and guide
the user to grant that RAM action or the policies in
[references/ram-policies.md](references/ram-policies.md). For credential,
throttling, timeout, or plugin errors, use the `Suggestion` and
[references/verification-method.md](references/verification-method.md) to give
the next concrete fix.

`Throttling.UserConcurrentLimit` means the account has exceeded the Yaochi Agent
concurrent request limit. Current production verification shows at most 2
concurrent sessions per account; wait for an existing request to finish before
retrying.

### Response Requirements

For diagnosis and inspection questions, keep the answer evidence-driven:

1. Start with the conclusion and current risk level.
2. Cite concrete evidence from the backend response, such as metric values, log counts, backup records, version numbers, or returned status fields.
3. Give at most the highest-impact next actions first. Distinguish immediate actions from follow-up observation.
4. For missing data or permission failures, explain what could not be verified and surface the structured error or missing-permission guidance.
5. Do not expose internal tool names, absolute local file paths, hidden system groups, credentials, or raw implementation details unless they are necessary for user remediation.

For high-risk or change-related requests:

- Parameter changes, restarts, failovers, whitelist changes, backup recovery, and configuration changes require explicit risk explanation and user confirmation.
- Always state whether a parameter change requires restart or has immediate effect when that evidence is available.
- Backup and recovery guidance must remind the user to verify recovery point, data consistency, and business impact before action.

### Example Questions

| Scenario | Example Question |
|----------|------------------|
| Cluster Management | List nodes and endpoints of cluster pc-xxx |
| Instance Query | List PolarDB MySQL 8.0 prepaid clusters in Beijing |
| Health Inspection | Generate a health inspection report for cluster pc-xxx |
| Performance Diagnostics | Troubleshoot high CPU usage in cluster pc-xxx |
| Slow SQL Analysis | Show slow SQL in cluster pc-xxx in the last hour |
| Parameter Tuning | What does loose_polar_log_bin parameter mean |
| Parameter Change | Explain parameter changes of pc-xxx in the last 3 days |
| Parameter Comparison | Compare parameter differences between pc-xxx and pc-yyy |
| IMCI Parameters | How to configure IMCI related parameters for cluster pc-xxx |
| HA Switchover | Analyze recent primary-standby switchover cause for cluster pc-xxx |
| Backup Recovery | When was the latest backup of cluster pc-xxx |
| Storage Optimization | What to do if storage usage of cluster pc-xxx grows too fast |
| Connection Troubleshooting | Cluster pc-xxx connections are full |
| Security Audit | Check security configuration of cluster pc-xxx |
| Version Risk | Analyze DB kernel and proxy version risk for pc-xxx |
| Event Analysis | Analyze PolarDB event impact for pc-xxx |

## Success Verification

See [references/verification-method.md](references/verification-method.md)

## Cleanup

This Skill focuses on **query and diagnostics** capabilities, does not create any resources, no cleanup required.

The following operations are NOT within the scope of this Skill:
- Directly create/delete PolarDB clusters
- Directly change instance specifications or parameters
- Directly modify whitelist, security, backup, or HA configuration

The Skill may explain these operations, assess risk, and guide the user through the required checks, but it must not claim that a change was executed unless the backend response explicitly confirms it.

## API and Command Tables

See [references/related-apis.md](references/related-apis.md)

## Best Practices

1. **PolarDB-only scope**: Use this Skill for PolarDB MySQL/PostgreSQL. Do not route non-PolarDB product O&M requests here.
2. **Cluster ID Format**: PolarDB cluster IDs typically start with `pc-`; include the full cluster ID in queries when available.
3. **Region Specification**: Explicitly specify region in natural language queries (e.g., "Hangzhou region", "Beijing region") to improve query accuracy. If region is unknown, ask or let the backend infer it from the instance when supported.
4. **Evidence First**: For O&M, inspection, and diagnosis answers, rely on backend-returned tool evidence. Do not infer exact metrics, version risk, or backup state without data.
5. **Multi-turn Conversation**: Use `--session-id` for complex diagnostic scenarios to maintain context continuity.
6. **Concurrency Limit**: Maximum 2 concurrent sessions per account, avoid initiating multiple parallel calls.
7. **High-risk Operations**: For parameter changes, failover, recovery, or security changes, explain risk and require user confirmation before any action path.
8. **Throttling Handling**: If encountering `Throttling.UserConcurrentLimit` error, wait for previous query to complete and retry.
9. **Credential Security**: Use `aliyun configure` to manage credentials, never hardcode AK/SK in scripts.

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and configuration guide |
| [references/related-apis.md](references/related-apis.md) | Related API and CLI command list |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policy list |
| [references/verification-method.md](references/verification-method.md) | Success verification methods |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria |
