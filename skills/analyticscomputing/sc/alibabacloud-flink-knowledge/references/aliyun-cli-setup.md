# aliyun CLI Configuration Reference

This document declares the complete configuration requirements and SQL syntax hard guard rules when this Skill invokes `aliyun` CLI to call Alibaba Cloud services.

## aliyun CLI Configuration Requirements

When this skill invokes `aliyun` CLI, the agent MUST complete the following 4 configuration declarations **before** executing any business command. Each declaration is required independently.

### 1. Plugin Update Declaration
Before executing `aliyun` commands, confirm that the plugin version matches the runtime. Update with the following command:
```bash
aliyun plugin update
```

### 2. User-Agent Declaration (Per-Command)
Every business API command MUST carry a `--user-agent` flag with the session-scoped identifier:
```bash
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-flink-knowledge/{session-id}"
```
Where `{session-id}` is a 32-character lowercase hexadecimal string generated once per session at skill load time. Do NOT use `aliyun configure ai-mode` commands — apply `--user-agent` directly on each business command.

### 3. System Commands
System commands (`configure`, `plugin`, `version`) do NOT carry `--user-agent`. Only business API commands do.

### 4. Post-Execution Cleanup
No session state cleanup is required. Each command is self-contained with its own `--user-agent` flag.

### Configuration Summary
- **User-Agent**: `AlibabaCloud-Agent-Skills/alibabacloud-flink-knowledge/{session-id}` applied to every business command for platform observability
- **Plugin Policy**: The agent should call `aliyun plugin update` in the first session to ensure the plugin is up to date
- **Plugin Mode Mandatory Requirement**: All `aliyun` CLI commands **must** use plugin mode (lowercase-hyphen format, e.g. `list-regions`, `describe-vpcs`). PascalCase format (e.g. `ListRegions`, `DescribeVpcs`) is **prohibited**

---

## G3-Gated SQL Syntax Hard Guards

### STATE TTL syntax discipline (G3)
In Flink SQL DDL, the inline `STATE ttl INTERVAL` syntax is **prohibited** (not officially supported in DDL; high model hallucination rate). All state TTL declarations must be specified via the WITH clause, for example:
```
WITH ('state.ttl' = '24 h')
```
Violating this syntax rule will trigger a G3 block; inline STATE TTL syntax must not be output.

### Checkpoint/Savepoint restore boundary guidance
When restoring from a Checkpoint/Savepoint and adding new operators, the following two cases must be distinguished:
1. **Stateless operators** — Appending stateless operators at the end of a job is generally safe and can be restored directly.
2. **Stateful operators** — Adding stateful operators to a job causes state mapping inconsistency; `allowNonRestoredState=true` must be explicitly configured during restoration, otherwise restoration will fail.

Vague statements (such as "adding a new operator at the end always allows restoration") are prohibited. The above distinction must be clearly stated with the corresponding restoration strategy.

**`allowNonRestoredState` is a job startup parameter, not a SQL session parameter**: `allowNonRestoredState` is a CLI/console configuration at Flink job startup (e.g. `flink run -DallowNonRestoredState=true` or console startup parameter), not a SQL SET statement. Any SQL `SET` syntax for configuring `allowNonRestoredState` is prohibited — such syntax is invalid in Flink SQL and will be silently ignored.
