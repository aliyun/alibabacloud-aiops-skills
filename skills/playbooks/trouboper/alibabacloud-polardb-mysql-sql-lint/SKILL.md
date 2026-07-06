---
name: alibabacloud-polardb-mysql-sql-lint
description: >
  Pre-release SQL assessment and optimization for PolarDB MySQL.
  Combines 28+ static lint rules with Alibaba Cloud DAS dynamic diagnosis.
  Detects full table scans, missing indexes, dangerous UPDATE/DELETE 
  without WHERE, schema design issues, naming violations, and provides 
  index recommendations with cost estimation.
  Triggers when users ask to review SQL statements, assess SQL quality,
  optimize queries before deployment, validate DDL changes, check for
  SQL injection risks, analyze execution plans, or get DAS-based
  optimization suggestions for PolarDB MySQL instances.
---
# Alibaba Cloud PolarDB MySQL SQL Linting Skill

Pre-release SQL assessment and optimization recommendations by combining static SQL lint rules with Alibaba Cloud DAS SQL diagnostics.

> **Execution Efficiency:** Execute the workflow directly based on this SKILL.md. Do NOT pre-read `references/` files before starting — only read them when explicitly needed for troubleshooting or detailed format specs.

## Prerequisites

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

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

### Required Environment

- **Python Version:** 3.8+
- **CLI Tools:** aliyun-cli (configured with credentials)
- **Environment Variables:** `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`

## Observability Initialization (MUST run before any command)

```bash
if [ -z "$ALICLOUD_SKILL_SESSION_ID" ]; then
  export ALICLOUD_SKILL_SESSION_ID="$(cat /proc/sys/kernel/random/uuid 2>/dev/null | tr -d '-' || uuidgen | tr -d '-' | tr 'A-F' 'a-f')"
fi
export ALICLOUD_SKILL_INVOCATION_ID="$(cat /proc/sys/kernel/random/uuid 2>/dev/null | tr -d '-' | head -c 16 || uuidgen | tr -d '-' | tr 'A-F' 'a-f' | head -c 16)"
export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-polardb-mysql-sql-lint/s-${ALICLOUD_SKILL_SESSION_ID}/i-${ALICLOUD_SKILL_INVOCATION_ID}"
export ALIBABA_CLOUD_OTEL_TRACEPARENT="00-${ALICLOUD_SKILL_SESSION_ID}-${ALICLOUD_SKILL_INVOCATION_ID}-01"
export ALIBABA_CLOUD_OTEL_BAGGAGE="skill=alibabacloud-polardb-mysql-sql-lint,source=agent-skills"
```

Do not skip, alter formats, override `--user-agent` per command, or place PII in baggage.

## AI-Mode Lifecycle

At the **start** of the Core Workflow (before any CLI invocation):
**[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
Run the following commands before any CLI invocation:
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-polardb-mysql-sql-lint"
```
**[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
```bash
aliyun configure ai-mode disable
```

**[MUST] CLI User-Agent** — All `aliyun` API commands must carry User-Agent:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardb-mysql-sql-lint`

UA is auto-injected via the Observability `ALIBABA_CLOUD_USER_AGENT` env var and AI-mode `set-user-agent` — do NOT manually add `--user-agent` per command (the env var handles it). Local commands (`aliyun configure`, `aliyun version`, `aliyun plugin`) do not support `--user-agent` and must not have it added.

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., Instance ID, Database Name, Region, SQL Statement)
> MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| SQL Statement | Required | SQL to diagnose | — |
| Instance ID | Optional | PolarDB MySQL instance ID (e.g., `pc-xxxxxxxxx`). Omit for static-only mode. | — |
| Database Name | Optional | Target database name. Required when Instance ID is provided. | mysql |
| Region | Optional | Instance region | cn-shanghai |

## RAM Permissions

**Custom Policy JSON:**
```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "hdm:DescribeInstanceDasPro",
        "hdm:CreateRequestDiagnosis",
        "hdm:GetRequestDiagnosisResult"
      ],
      "Resource": "*"
    }
  ]
}
```

**Note:** DAS endpoint is fixed to `das.cn-shanghai.aliyuncs.com` regardless of instance region.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

See [references/ram-policies.md](references/ram-policies.md) for detailed RAM policy documentation.

## Core Workflow

### Two Modes

| Mode | When | What you get |
|------|------|-------------|
| **Static-only** | No instance ID, or instance ID invalid | 28+ static lint rules (instant, no API call) |
| **Full diagnosis** | Valid instance ID + database name | Static lint + DAS execution plan + index recommendations |

### Mode 1: Static-Only (no instance ID required)

```bash
python3 scripts/sql_lint.py --sql "YOUR_SQL"
```

Use this when the user just wants a quick SQL review without providing instance details. All 28+ static rules run instantly with no network calls.

### Mode 2: Full Diagnosis (instance ID + database)

```bash
# Step 0: Validate Instance (catches invalid/fake IDs early)
aliyun das describe-instance-das-pro \
  --endpoint das.cn-shanghai.aliyuncs.com \
  --instance-id pc-xxx
# Only fall back to static-only if API returns error (non-200 Code).
# Code=200 means instance is valid and reachable — ALWAYS proceed to Step 1 regardless of Data value.

# Step 1: Static Linting + DAS Diagnosis (all in one)
python3 scripts/sql_lint.py \
  --instance-id pc-xxx --database db_name \
  --sql "YOUR_SQL" --region cn-shanghai

# Step 2: Separate DAS Diagnosis (if needed for more detail)
aliyun das create-request-diagnosis \
  --endpoint das.cn-shanghai.aliyuncs.com \
  --instance-id pc-xxx --database db_name --sql "YOUR_SQL"

# Step 3: Get DAS result (wait 5s)
sleep 5
aliyun das get-request-diagnosis-result \
  --endpoint das.cn-shanghai.aliyuncs.com \
  --instance-id pc-xxx --message-id <task-id-from-step-2>
```

> **Instance Validation**: `sql_lint.py` auto-validates when `--instance-id` is provided (format regex + `describe-instance-das-pro`). Only falls back to static-only if the API returns an error (non-200 Code or network failure). `Code=200` means the instance is valid — always proceed with DAS diagnosis regardless of `Data` value. DAS may not return optimization suggestions for small datasets, and that is normal.
> **No instance ID?** That's fine — just omit `--instance-id` and the script outputs static lint results only.

### Safety Rules

- ❌ **NEVER** connect to database for metadata queries
- ❌ **NEVER** execute `COUNT(*)` on unknown tables
- ❌ **NEVER** fetch table structure (DAS API has no such interface)
- ✅ **ALWAYS** use static linting + DAS diagnosis only
- ✅ **ALWAYS** use `--message-id` (NOT `--task-id`) for getting results

### Multi-Statement SQL

When the user provides multiple SQL statements (separated by `;`), pass all statements together in a single `--sql` argument. The script automatically:
1. Splits statements and runs static lint rules on each one individually
2. Detects RULE-061 (mergeable ALTER TABLE statements) across the batch
3. Runs batch DAS diagnosis — creates all tasks in parallel, waits once (15s), then retrieves all results

```bash
# Multi-statement example
python3 scripts/sql_lint.py \
  --instance-id pc-xxx --database db_name \
  --sql "SELECT * FROM users WHERE status = 1; UPDATE orders SET total = 0 WHERE id > 100"
```

Do NOT split statements and run the script multiple times — one invocation handles everything.

### DAS Response Fields

When DAS diagnosis succeeds, the result includes:
- `estimateCost`: CPU, I/O, rows estimation
- `improvement`: Optimization potential multiplier
- `indexAdvices`: Recommended indexes with DDL
- `tuningAdvices`: SQL rewrite recommendations
- `primaryTag`: Diagnosis category (e.g., `LARGE_TABLE`, `PLAN_COST_VERY_SMALL`)

### Key Parameters

- `--instance-id`: PolarDB MySQL instance ID (e.g., `pc-xxxxxxxxx`)
- `--database`: Database name where the table exists
- `--sql`: SQL statement to diagnose
- `--message-id`: Task ID from `create-request-diagnosis` (NOT `--task-id`)

## Troubleshooting

If DAS diagnosis returns errors (MetadataException, timeout, etc.), report the error and present static lint results only. Do NOT guess recommendations.

**Common issues:**
- **RDS MySQL instances (rm-\*)** may not support full DAS diagnostics
- **DAS timeout**: Ensure instance is connected to DAS and state is "Normal Access"
- **Permission denied**: See [references/ram-policies.md](references/ram-policies.md) for required permissions

See [references/implementation-notes.md](references/implementation-notes.md) for detailed technical notes if needed.

