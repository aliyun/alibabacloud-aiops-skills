---
name: alibabacloud-mongodb-health-inspect
description: |
  Run a read-only health inspection on Alibaba Cloud MongoDB (DDS) instances and produce a standardized report. Supports Sharding and ReplicaSet architectures across single-instance, multi-instance, and whole-account scopes.
  Use this skill when the user asks for a MongoDB health check, DDS inspection, resource usage review, slow query analysis, current session snapshot, alert review, or configuration risk assessment.
  Triggers: MongoDB 巡检, MongoDB 健康检查, DDS 巡检, 实例巡检, MongoDB health check, MongoDB inspection, 资源使用率, 慢日志, 慢查询, 当前会话, 报警历史, 配置检查, 风险评估, 数据库健康报告, 性能巡检, 巡检报告.
---

## The ONLY Command You Run

Everything in this skill is done by running **one single command**. You do NOT call any `aliyun` CLI commands yourself. You do NOT generate any report files yourself. You ONLY run this:

```bash
SKILL_SESSION_ID={session-id} bash scripts/run-inspect.sh {INSTANCE_ARGS} {OPTIONS}
```

The script handles ALL of the following internally — you do NOT do any of these yourself:
- Instance discovery (cross-region, both Sharding and ReplicaSet)
- API data collection (DDS, DAS, CMS)
- Report generation (HTML format, with index.html for multi-instance)
- Output to `~/Downloads/` by default

---

## Decision Tree: How to Assemble the Command

### Step 1 — Pick `{INSTANCE_ARGS}` (required)

| User intent | `{INSTANCE_ARGS}` |
|---|---|
| Gives one instance ID | `dds-xxx` |
| Gives multiple instance IDs | `dds-xxx dds-yyy` (space-separated, ONE command) |
| "all instances" / full account scan | `--all` |
| All instances in a specific region | `--all --region cn-hangzhou` |

### Step 2 — Pick `--days` (optional)

| User intent | Option |
|---|---|
| "last 3 days" / recent N days | `--days 3` |
| "last week" / no mention | omit (default: 7) |
| Custom N days | `--days N` |

### Step 3 — Pick `--item` (optional, can repeat)

| User mentions | Option |
|---|---|
| CPU / memory / resource usage / connections / IOPS | `--item resource` |
| slow log / slow query | `--item slowlog` |
| alarm / alert | `--item alert` |
| config check / risk assessment / version / expiry | `--item config` |
| space / disk / collection size | `--item space` |
| session / currentOp | `--item session` |
| Multiple areas | combine: `--item slowlog --item alert` |
| Full inspection / nothing specific | omit (default: all items) |

### Step 4 — Run the command. Done.

Present the report file path from the script output to the user. **Do NOT add any extra content, sections, or summaries.**

---

## Complete Examples

```bash
# User: "inspect instance dds-bp1acbc74a1f9e04"
SKILL_SESSION_ID={session-id} bash scripts/run-inspect.sh dds-bp1acbc74a1f9e04

# User: "inspect dds-xxx and dds-yyy, combined report"
SKILL_SESSION_ID={session-id} bash scripts/run-inspect.sh dds-bp15195cbe597cd4 dds-bp1f4501681c0454

# User: "inspect all instances, last 1 day"
SKILL_SESSION_ID={session-id} bash scripts/run-inspect.sh --all --days 1

# User: "all instances in cn-hangzhou, last 3 days"
SKILL_SESSION_ID={session-id} bash scripts/run-inspect.sh --all --region cn-hangzhou --days 3

# User: "analyze slow logs for dds-xxx"
SKILL_SESSION_ID={session-id} bash scripts/run-inspect.sh dds-bp15195cbe597cd4 --item slowlog

# User: "check CPU and memory for dds-xxx, last 7 days"
SKILL_SESSION_ID={session-id} bash scripts/run-inspect.sh dds-bp1f4501681c0454 --item resource

# User: "check slow logs and alerts for two instances"
SKILL_SESSION_ID={session-id} bash scripts/run-inspect.sh dds-bp1f4501681c0454 dds-m5e14a05531b3dc4 --item slowlog --item alert
```

---

## Forbidden Actions

You MUST NOT do any of the following. Each is an immediate failure:

1. **Call `aliyun` CLI to collect data** — no `aliyun dds`, `aliyun cms`, `aliyun das`, or any API commands. The ONLY allowed `aliyun` commands are: `aliyun configure list`, `aliyun version`, `aliyun configure set`, `aliyun plugin`
2. **Discover instances manually** — no looping through regions with `DescribeDBInstances`. Use `--all`
3. **Split multi-instance into separate runs** — pass all IDs in ONE command
4. **Generate or modify reports** — no creating files, no appending "Instance Overview" / "Optimization Suggestions" / summaries
5. **Pass `-o`** — unless the user explicitly requests a custom output path
6. **Pass `-f markdown` or `-f text`** — unless the user explicitly requests non-HTML format
7. **Connect to the database** — no mongo/mongosh clients
8. **Perform write operations** — no ModifyDBInstanceSpec, CreateDBInstance, etc.
9. **Substitute a different instance** — if the user's instance ID is not found, report the error. Do NOT inspect a different instance instead
10. **Ask follow-up questions after report output** — the task is complete once the report path is presented

---

## Prerequisites

**Runtime:**
- Python >= 3.7
- Aliyun CLI >= 3.3.3
- OS: Linux / macOS / Windows

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> Then [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` in the command template above.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**

Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-health-inspect/{session-id}
```

> **Note:** The script reads `SKILL_SESSION_ID` from environment and appends user-agent internally. Do NOT pass `--user-agent` when running the script.

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **ONLY** use `aliyun configure list` to check credential status
>
> **If no valid profile exists, STOP here.**
> Guide the user to configure credentials outside of this session.

---

## Required RAM Permissions

For the full permission policy and descriptions, see `references/ram-policies.md`.

> **[MUST] Permission Failure Handling:** When the script fails due to permission errors:
> 1. Read `references/ram-policies.md` to get the full list of permissions required
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Security Rules

**This skill is read-only:**
- Do not execute any modification operations (DDL/DML/instance scaling)
- Only provide analysis results and optimization suggestions
- All modification operations must be manually confirmed and executed by the user
