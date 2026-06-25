---
name: alibabacloud-polardb-mysql-inspection
description: |
  Health inspection for Alibaba Cloud PolarDB MySQL instances, generating visual HTML reports.
  Supports five inspection dimensions:
  1. Resource Monitoring — CPU, memory, IOPS, connections usage trends (including Proxy nodes)
  2. Space Analysis — Top 20 table space usage, auto-increment primary key usage
  3. Slow Query Log — Slow SQL statistics and analysis
  4. Session Diagnostics — Current active connections and session status
  5. Alert History — CloudMonitor alert records
  Supports single-instance, multi-instance, and full-account inspection modes.
  Trigger keywords: PolarDB inspection, instance health check, database inspection report,
  CPU/memory/IOPS usage, disk space analysis, table space usage, largest tables,
  top table space, slow query statistics, slow SQL analysis, alert records,
  alert history, connection monitoring, active sessions, database performance check.
---

## HARD RULES (violation = immediate failure)

> **Core Rule: All inspections MUST be executed via `python3 scripts/health-inspect.py`.**
> The script encapsulates all correct API calls internally. The AI MUST NOT call `aliyun` CLI directly to collect inspection data.

1. **Do NOT call aliyun CLI to collect data**: All inspection data (performance monitoring, space analysis, slow logs, etc.) must be obtained through `health-inspect.py`. The AI must not bypass the script by running `aliyun polardb`, `aliyun cms`, `aliyun das`, etc. The only aliyun commands allowed for direct AI invocation are: `aliyun configure list` (check credentials), `aliyun version` (check version), `aliyun configure set` (set configuration), `aliyun plugin` (plugin management)
2. **Do NOT use CloudMonitor (cms) `describe-metric-list` / `describe-metric-data`**: Performance monitoring data is obtained by the script via PolarDB native APIs (`describe-db-cluster-performance`, `describe-db-node-performance`, `describe-db-proxy-performance`). **NEVER** use `aliyun cms describe-metric-list` as a substitute
3. **Do NOT connect to the database directly**: Do not install mysql/mariadb clients, do not connect to database instances in any way, do not execute any SQL statements (including `SELECT ... FROM information_schema`)
4. **Do NOT perform write operations**: Do not call `reset-account-password`, `create-account`, `modify-db-cluster*` or any other APIs that modify instance state
5. **Report errors on API failure**: If the script fails at any step, mark it as "retrieval failed" in the report. **Do NOT** attempt to obtain data through alternative methods

---

## How to Use This Skill

### Usage

**You do not need to run any scripts manually!** This is an AI Agent skill — simply describe your needs in natural language.

### Example Conversations

**Example 1: Single instance inspection**
```
Inspect PolarDB instance pc-bp167736gfqyn483x
```

**Example 2: Multi-instance inspection**
```
Inspect instances pc-bp167736gfqyn483x and pc-bp10yty6665u3u6a5
```

**Example 3: Full account inspection (all instances)**
```
Inspect all PolarDB MySQL instances in my account
```

**Example 4: Specify Region**
```
Inspect PolarDB instance pc-bp167736gfqyn483x in cn-hangzhou region
```

**Example 5: Resource usage only**
```
Show CPU and memory usage for pc-bp167736gfqyn483x
```
Maps to `--item resource`

**Example 6: Slow logs only**
```
Analyze recent slow logs for pc-bp167736gfqyn483x
```
Maps to `--item slowlog`

**Example 7: Combined inspection items**
```
Show slow logs and alert history for pc-bp167736gfqyn483x
```
Maps to `--item slowlog --item alert`

**Example 8: Batch + specific items**
```
Show CPU usage for all instances in the last 3 days
```
Maps to `--all --days 3 --item resource`

### AI Behavior Rules (MUST follow)

1. **Must use the script for inspection**: All inspection operations can **only** be done via `python3 scripts/health-inspect.py`. The AI's role is: identify user intent -> assemble correct script parameters -> execute script -> present report to user. **Do NOT call `aliyun` CLI directly to collect any inspection data**
2. **Inspection mode selection**: Choose the correct execution mode based on user intent; do not manually split into multiple single-instance runs
   - User says "all instances" / "full account" -> use `--all`
   - User specifies multiple instance IDs -> pass multiple IDs: `health-inspect pc-xxx pc-yyy`
   - User specifies a single instance -> single-instance mode: `health-inspect pc-xxx`
3. **Inspection item selection**: Map user's focus areas to `--item` parameters
   - User mentions "CPU" / "memory" / "resource usage" / "connections" / "IOPS" -> `--item resource`
   - User mentions "space" / "disk" / "table size" / "auto-increment" -> `--item space`
   - User mentions "slow log" / "slow query" / "slow SQL" -> `--item slowlog`
   - User mentions "session" / "connection" / "active sessions" -> `--item session`
   - User mentions "alert" / "alarm" / "warning" -> `--item alert`
   - User mentions multiple areas -> combine multiple `--item` (e.g., `--item resource --item slowlog`)
   - User does not specify (e.g., "run inspection" / "full check") -> do not add `--item`, default to full inspection
4. **Unified output**: Multi-instance (>=2) reports go to a single directory with an index page (index.html) + individual detail reports; single-instance outputs a single file
5. **Do not manually list instances then run one by one**: The script's `--all` has built-in instance discovery. The AI does not need to call `describe-db-clusters` first
6. **On script failure**: If the script reports an error at any step, relay the error message to the user. **Do NOT** call aliyun CLI to try alternative data retrieval methods
7. **Do NOT ask follow-up questions after report output**: This skill is inspection-only. Once the report is generated, the task is complete. Do NOT append questions like "Need further analysis?", "Shall I investigate deeper?", or any similar follow-up prompts

### AI Execution Flow (follow this order strictly)

1. Identify user intent, select correct inspection mode and parameters
2. Execute `python3 scripts/health-inspect.py <params>` — one command completes all data collection
3. The script automatically handles: Region discovery, PolarDB API calls for performance data, DAS API for space analysis, slow log queries, report generation
4. Present the generated report file path to the user
5. Answer follow-up questions based on report content

---

# Alibaba Cloud PolarDB MySQL Instance Health Inspection Skill

This skill performs comprehensive health inspection of PolarDB MySQL instances and generates standardized reports.

**Inspection Dimensions:**
1. **Instance Information** — Database type, version, spec, max connections, storage type
2. **Resource Usage** — CPU/memory/space/IOPS/connections average and peak values
3. **Space Usage Details** — Top 20 table space statistics
4. **Slow Log Statistics** — Slow query SQL analysis

**Architecture:** PolarDB MySQL + Aliyun CLI + DAS API + CloudMonitor

---

## Prerequisites

**Runtime Environment:**
- Python >= 3.7
- Aliyun CLI >= 3.3.3
- OS: Linux / macOS / Windows

**Required CLI Tools:**
- aliyun CLI >= 3.3.3 (with valid credentials configured)
- No mysql client needed (this skill completes all inspection via API, no direct database connection required)

**Python Dependencies:**
```bash
# Uses only Python standard library: subprocess, json, os, sys, datetime
# All Alibaba Cloud API calls are made through aliyun CLI
```

**Installation Verification:**
> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> Then [MUST] run `aliyun plugin update` to ensure that any existing plugins on your local machine are always up-to-date.

**[MUST] CLI User-Agent** — User-Agent is handled automatically by AI-mode (see below). Do **NOT** manually pass `--user-agent` to any `aliyun` command.
> **Note:** `health-inspect.py` already appends user-agent internally. Do **NOT** pass `--user-agent` when running the script. For direct `aliyun` CLI commands (`aliyun configure list`, `aliyun version`, `aliyun plugin`, etc.), do **NOT** add `--user-agent` either — these local commands do not support it and will fail with `invalid flag`. The AI-mode `set-user-agent` (configured in Observability Initialization below) automatically injects the user-agent into all API calls.

## Observability Initialization (MUST run before any command)

```bash
if [ -z "$ALICLOUD_SKILL_SESSION_ID" ]; then
  export ALICLOUD_SKILL_SESSION_ID="$(cat /proc/sys/kernel/random/uuid 2>/dev/null | tr -d '-' || uuidgen | tr -d '-' | tr 'A-F' 'a-f')"
fi
export ALICLOUD_SKILL_INVOCATION_ID="$(cat /proc/sys/kernel/random/uuid 2>/dev/null | tr -d '-' | head -c 16 || uuidgen | tr -d '-' | tr 'A-F' 'a-f' | head -c 16)"
export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-polardb-mysql-inspection/s-${ALICLOUD_SKILL_SESSION_ID}/i-${ALICLOUD_SKILL_INVOCATION_ID}"
export ALIBABA_CLOUD_OTEL_TRACEPARENT="00-${ALICLOUD_SKILL_SESSION_ID}-${ALICLOUD_SKILL_INVOCATION_ID}-01"
export ALIBABA_CLOUD_OTEL_BAGGAGE="skill=alibabacloud-polardb-mysql-inspection,source=agent-skills"
```

Do not skip, alter formats, override `--user-agent` per command, or place PII in baggage.

**[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
Run the following commands before any CLI invocation:
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-polardb-mysql-inspection"
```

**[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
```bash
aliyun configure ai-mode disable
```

---

## Required RAM Permissions

This skill uses read-only APIs only. No write permissions are required.
For the full permission policy and descriptions, see `references/ram-policies.md`.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile.
>
> **If no valid profile exists, STOP here.**
> Guide the user to configure credentials outside of this session.

---

## Parameter Reference

| Parameter | Required/Optional | Description | Default |
|-----------|------------------|-------------|---------|
| DBClusterId | Required (omit with `--all`) | PolarDB cluster ID (pc-xxx), supports multiple | User must provide |
| RegionId | Optional | Instance region (auto-discovered if not provided) | Auto-discover |
| Days | Optional | Inspection time range (days) | 7 |
| Item | Optional | Specify inspection items (multiple allowed); omit for full inspection | Full |
| Profile | Optional | aliyun CLI profile name | Default profile |
| Output | Optional | Report output directory or file path | ~/Downloads/ |

**Item values:**

| item | Inspection Content |
|------|-------------------|
| `resource` | CPU/memory/IOPS/connections + Proxy monitoring trends |
| `space` | Space usage Top 20 + auto-increment primary key usage |
| `slowlog` | Slow log statistics |
| `session` | Current session information |
| `alert` | Alert history |

---

## Core Workflow

### Recommended: Use the Automated Script (one-command inspection)

```bash
python3 scripts/health-inspect.py <CLUSTER_ID> [options]
```

**CLI Arguments:**

| Argument | Short | Description |
|----------|-------|-------------|
| `CLUSTER_ID` | (positional) | PolarDB cluster ID, supports multiple; omit with `--all` |
| `--all` | | Inspect all PolarDB MySQL instances in the current account |
| `--region` | `-r` | Specify Region (auto-discovers if not specified) |
| `--days` | `-d` | Inspection time range (days), default 7 |
| `--item` | | Specify inspection item (can be used multiple times); omit for full. Options: resource, space, slowlog, session, alert |
| `--profile` | `-p` | Specify aliyun CLI profile name |
| `--output` | `-o` | Specify report output directory or file path |
| `--format` | `-f` | Report format: html (default), markdown, text |

**Examples:**
```bash
# Single instance (auto-discover Region)
python3 scripts/health-inspect.py pc-bp167736gfqyn483x

# Multi-instance
python3 scripts/health-inspect.py pc-bp167736gfqyn483x pc-bp10yty6665u3u6a5

# All instances in account
python3 scripts/health-inspect.py --all

# All instances in specific Region
python3 scripts/health-inspect.py --all --region cn-hangzhou

# Custom time range (last 3 days)
python3 scripts/health-inspect.py --all --days 3

# Custom time range (last 30 days)
python3 scripts/health-inspect.py pc-bp167736gfqyn483x --days 30

# Resource usage only (CPU/memory/IOPS/connections)
python3 scripts/health-inspect.py pc-bp167736gfqyn483x --item resource

# Slow logs and alerts only
python3 scripts/health-inspect.py pc-bp167736gfqyn483x --item slowlog --item alert

# Batch + specific items
python3 scripts/health-inspect.py --all --item resource --item slowlog

# Custom output directory
python3 scripts/health-inspect.py --all -o /tmp/polardb_report

# Full parameters
python3 scripts/health-inspect.py pc-bp167736gfqyn483x -p myprofile -r cn-hangzhou -d 14 -o ./report
```

The script completes all inspection steps automatically. For multi-instance runs, reports are output to a single directory with a summary page (index.html).

---

> For manual step-by-step API call details, see `references/manual-workflow.md` (only use when the script is unavailable).

---

> For report output format templates (text + HTML/ECharts layout specs), see `references/report-format.md` (only reference when adjusting report styles).

---

## Security Rules

**This skill is read-only:**
- Do not execute any modification operations (DDL/DML)
- Only provide analysis results and optimization suggestions
- All modification operations must be manually confirmed and executed by the user

---

## Reference Documents and Scripts

- `scripts/health-inspect.py` — One-command inspection main script
- `scripts/find-instance-region.py` — Auto-discover instance Region
- `scripts/check-write-operation.sh` — Write operation detection hook
- `references/manual-workflow.md` — Manual step-by-step API call details
- `references/report-format.md` — Inspection report output format specification (text + HTML/ECharts)
