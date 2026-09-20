---
name: alibabacloud-polardb-mysql-inspection
description: |
  Health inspection for Alibaba Cloud PolarDB MySQL instances, generating visual HTML reports.
  Supports single-instance, multi-instance, and full-account inspection modes.
  Trigger keywords:PolarDB inspection, instance health check, database inspection report,
  CPU/memory/IOPS usage, disk space analysis, table space usage, largest tables,
  top table space, slow query statistics, slow SQL analysis, alert records,
  alert history, connection monitoring, active sessions, database performance check.
---

# Alibaba Cloud PolarDB MySQL Instance Health Inspection

Comprehensive health inspection for PolarDB MySQL instances with visual HTML reports.

**Inspection Dimensions:**
1. Instance Information — Database type, version, spec, storage
2. Resource Usage — CPU/memory/IOPS/connections (cluster + per-node + Proxy)
3. Space Analysis — Top 20 tables, auto-increment primary key usage
4. Slow Query Log — Slow SQL statistics and analysis
5. Session & Alert — Active connections, CloudMonitor alert history

**Architecture:** PolarDB MySQL + Aliyun CLI + DAS API + CloudMonitor → HTML/Markdown/Text Report

---

## How to Use This Skill

**You do not need to run any scripts manually!** This is an AI Agent skill — simply describe your needs in natural language.

### Example Conversations

**Example 1: Single instance inspection**
```
Inspect PolarDB instance pc-bp1715bzkcrateo69
```

**Example 2: Multi-instance inspection**
```
Inspect instances pc-bp1715bzkcrateo69 and pc-bp12n05ogr61b5929
```

**Example 3: Full account inspection (all instances)**
```
Inspect all PolarDB MySQL instances in my account
```

**Example 4: Specify Region**
```
Inspect PolarDB instance pc-bp1715bzkcrateo69 in cn-hangzhou region
```

**Example 5: Resource usage only**
```
Show CPU and memory usage for pc-bp1715bzkcrateo69
```
Maps to `--item resource`

**Example 6: Slow logs only**
```
Analyze recent slow logs for pc-bp1715bzkcrateo69
```
Maps to `--item slowlog`

**Example 7: Combined inspection items**
```
Show slow logs and alert history for pc-bp1715bzkcrateo69
```
Maps to `--item slowlog --item alert`

**Example 8: Batch + specific items**
```
Show CPU usage for all instances in the last 3 days
```
Maps to `--all --days 3 --item resource`

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
> Routine CLI self-update (>= 3.3.5): `aliyun upgrade`

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

## Required RAM Permissions

This skill uses read-only APIs only. No write permissions are required.
For the full permission policy and descriptions, see `references/ram-policies.md`.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance IDs, output paths,
> time ranges, etc.) MUST be confirmed with the user. Do NOT assume or use default
> values without explicit user approval.

---

## Observability (MUST follow for every aliyun command)

Before any cloud API invocation, read `references/manifest.json` from this skill's root and use only its top-level non-empty string `version` as `{skill-version}`. If the file is missing, invalid, or the field is absent/empty/not a string, STOP and report the error. NEVER invent, guess, or reuse a version from another skill.

Bind version and session to the current skill name and skill root. Before this skill's first cloud API invocation in a conversation, generate a fresh random 32-character lowercase hexadecimal session ID. Reuse that session ID for this skill throughout the conversation; each skill MUST use a distinct session ID. NEVER copy one from documentation, examples, another skill, or a previous conversation, and NEVER send the literal `{session-id}` placeholder. When switching skills or returning to this skill, reread this skill's manifest; never cross-skill reuse either value.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

Markdown examples may omit the flag for brevity. The Agent MUST append the exact flag below to every actual execution, including commands generated or extended at runtime; do not repeat UA boilerplate in every example block.

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-polardb-mysql-inspection/{session-id} skill-version/{skill-version}"
```

The entire UA value MUST be double-quoted because it contains a space. Do not skip, alter, or omit it on any `aliyun` API command.

**Script execution:** Inject both scoped values inline:

```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/health-inspect.py
```

Scripts MUST require both values and construct the same UA product.

---

## Core Workflow

### Parameter Reference

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
python3 scripts/health-inspect.py pc-bp1715bzkcrateo69

# Multi-instance
python3 scripts/health-inspect.py pc-bp1715bzkcrateo69 pc-bp12n05ogr61b5929

# All instances in account
python3 scripts/health-inspect.py --all

# All instances in specific Region
python3 scripts/health-inspect.py --all --region cn-hangzhou

# Custom time range (last 3 days)
python3 scripts/health-inspect.py --all --days 3

# Custom time range (last 30 days)
python3 scripts/health-inspect.py pc-bp1715bzkcrateo69 --days 30

# Resource usage only (CPU/memory/IOPS/connections)
python3 scripts/health-inspect.py pc-bp1715bzkcrateo69 --item resource

# Slow logs and alerts only
python3 scripts/health-inspect.py pc-bp1715bzkcrateo69 --item slowlog --item alert

# Batch + specific items
python3 scripts/health-inspect.py --all --item resource --item slowlog

# Custom output directory
python3 scripts/health-inspect.py --all -o /tmp/polardb_report

# Full parameters
python3 scripts/health-inspect.py pc-bp1715bzkcrateo69 -p myprofile -r cn-hangzhou -d 14 -o ./report
```

The script completes all inspection steps automatically. For multi-instance runs, reports are output to a single directory with a summary page (index.html).

> For manual step-by-step API call details, see `references/manual-workflow.md` (only use when the script is unavailable).

> For report output format templates (text + HTML/ECharts layout specs), see `references/report-format.md` (only reference when adjusting report styles).

### Hard Rules (violation = immediate failure)

> **Core Rule: All inspections MUST be executed via `python3 scripts/health-inspect.py`.**
> The script encapsulates all correct API calls internally. The AI MUST NOT call `aliyun` CLI directly to collect inspection data.

1. **Do NOT call aliyun CLI to collect data**: All inspection data (performance monitoring, space analysis, slow logs, etc.) must be obtained through `health-inspect.py`. The AI must not bypass the script by running `aliyun polardb`, `aliyun cms`, `aliyun das`, etc. The only aliyun commands allowed for direct AI invocation are: `aliyun configure list` (check credentials), `aliyun version` (check version), `aliyun configure set` (set configuration), `aliyun plugin` (plugin management)
2. **Do NOT use CloudMonitor (cms) `describe-metric-list` / `describe-metric-data`**: Performance monitoring data is obtained by the script via PolarDB native APIs (`describe-db-cluster-performance`, `describe-db-node-performance`, `describe-db-proxy-performance`). **NEVER** use `aliyun cms describe-metric-list` as a substitute
3. **Do NOT connect to the database directly**: Do not install mysql/mariadb clients, do not connect to database instances in any way, do not execute any SQL statements (including `SELECT ... FROM information_schema`)
4. **Do NOT perform write operations**: Do not call `reset-account-password`, `create-account`, `modify-db-cluster*` or any other APIs that modify instance state
5. **Report errors on API failure**: If the script fails at any step, mark it as "retrieval failed" in the report. **Do NOT** attempt to obtain data through alternative methods

### AI Behavior Rules (MUST follow)

1. **Must use the script for inspection** (see Hard Rule #1): The AI's role is: identify user intent → assemble correct script parameters → execute script → present report to user
2. **Inspection mode selection**: Choose the correct execution mode based on user intent; do not manually split into multiple single-instance runs
   - User says "all instances" / "full account" → use `--all`
   - User specifies multiple instance IDs → pass multiple IDs: `health-inspect pc-xxx pc-yyy`
   - User specifies a single instance → single-instance mode: `health-inspect pc-xxx`
3. **Inspection item selection**: Map user's focus areas to `--item` parameters
   - User mentions "CPU" / "memory" / "resource usage" / "connections" / "IOPS" → `--item resource`
   - User mentions "space" / "disk" / "table size" / "auto-increment" → `--item space`
   - User mentions "slow log" / "slow query" / "slow SQL" → `--item slowlog`
   - User mentions "session" / "connection" / "active sessions" → `--item session`
   - User mentions "alert" / "alarm" / "warning" → `--item alert`
   - User mentions multiple areas → combine multiple `--item` (e.g., `--item resource --item slowlog`)
   - User does not specify (e.g., "run inspection" / "full check") → do not add `--item`, default to full inspection
4. **Unified output**: Multi-instance (>=2) reports go to a single directory with an index page (index.html) + individual detail reports; single-instance outputs a single file
5. **Do not manually list instances then run one by one** (see Hard Rule #1): The script's `--all` has built-in instance discovery
6. **On script failure** (see Hard Rule #5): Relay the error message to the user; do NOT call aliyun CLI to try alternative methods
7. **Do NOT ask follow-up questions after report output**: This skill is inspection-only. Once the report is generated, the task is complete. Do NOT append questions like "Need further analysis?", "Shall I investigate deeper?", or any similar follow-up prompts

### AI Execution Flow (follow this order strictly)

1. Identify user intent, select correct inspection mode and parameters
2. Execute `python3 scripts/health-inspect.py <params>` — one command completes all data collection
3. The script automatically handles: Region discovery, PolarDB API calls for performance data, DAS API for space analysis, slow log queries, report generation
4. Present the generated report file path to the user
5. Answer follow-up questions based on report content

---

## Success Verification

A successful inspection produces:
- Terminal output containing `✅` completion markers for each data collection phase
- A report file path printed as `📄 Report saved: {path}` (single instance) or `📊 Summary report: {path}` (multi-instance)
- Generated HTML/text report file(s) with size > 0

For detailed verification steps including report content checks and error state identification, see [references/verification-method.md](references/verification-method.md).

---

## Security Rules

**This skill is read-only:**
- Do not execute any modification operations (DDL/DML)
- Only provide analysis results and optimization suggestions
- All modification operations must be manually confirmed and executed by the user

---

## Best Practices

1. **Use `--all` for full-account inspection**: Instead of manually collecting instance IDs, use the `--all` flag which has built-in instance discovery across all regions (or a specific region with `--region`).
2. **Adjust `--days` based on the investigation scope**: Default is 7 days. Use shorter ranges (1-3 days) for recent incident analysis; use longer ranges (14-30 days) for trend analysis.
3. **Use `--item` to focus on specific dimensions**: When the user only cares about a specific aspect (e.g., slow queries), specifying `--item slowlog` reduces API calls and speeds up the inspection.
4. **Check CLI version and plugin updates before first run**: Ensure `aliyun version` >= 3.3.3 and run `aliyun plugin update` to avoid stale plugin issues.
5. **Review the HTML report in a browser**: HTML reports include interactive ECharts trend charts. For the best experience, open the report file directly in a web browser.

---

## Reference Documents and Scripts

- `scripts/health-inspect.py` — One-command inspection main script
- `scripts/find-instance-region.py` — Auto-discover instance Region
- `scripts/check-write-operation.sh` — Write operation detection hook
- `references/manifest.json` — Skill name and version metadata
- `references/manual-workflow.md` — Manual step-by-step API call details
- `references/report-format.md` — Inspection report output format specification (text + HTML/ECharts)
- `references/ram-policies.md` — Required RAM permission policy
- `references/acceptance-criteria.md` — Correct/incorrect invocation patterns
- `references/verification-method.md` — Script execution and report content verification
- `references/related-commands.md` — Cloud API and local utility command reference
