---
name: alibabacloud-kvstore-health-inspection
description: |
  Health inspection for Alibaba Cloud Redis (ApsaraDB for Redis / Tair) instances. Generates HTML reports across 7 dimensions: instance basic info, current sessions, resource usage trends (CPU/memory/connection/bandwidth, last 7 days), big key / hot key analysis, slow log statistics, alert history, and risk-prioritized recommendations. Supports standard / cluster / SplitRW architectures, Tair PENA (persistent memory) and Tair ESSD (disk) types. Single-instance, multi-instance and full-account batch modes are supported. Trigger keywords: Redis inspection, Redis health check, KVStore inspection, Tair inspection, CPU usage, memory usage, connection usage, bandwidth usage, proxy usage, persistent memory, disk usage, slow log, big key, hot key, alert history, instance health report.
---

## HARD RULES (violation = immediate failure)

> **Core Rule: All inspections MUST be executed via `python3 scripts/health-inspect.py`.**
> The script encapsulates all correct API calls internally. The AI MUST NOT call `aliyun` CLI directly to collect inspection data.

1. **Do NOT call aliyun CLI to collect data**: All inspection data must be obtained through `health-inspect.py`. The AI must not bypass the script by running `aliyun r-kvstore` directly. The only aliyun commands allowed for direct AI invocation are: `aliyun configure list` (check credentials), `aliyun version` (check version), `aliyun configure set` (set configuration), `aliyun plugin` (plugin management)
2. **Do NOT use CloudMonitor (cms) APIs**: Performance monitoring data is obtained by the script via R-kvstore `describe-history-monitor-values` API. **NEVER** use `aliyun cms describe-metric-list/describe-metric-data` as a substitute
3. **Do NOT connect to Redis directly**: Do not install redis-cli clients, do not connect to Redis instances in any way, do not execute any Redis commands
4. **Do NOT perform write operations**: Do not call `modify-instance*`, `create-instance*`, `delete-instance*` or any other APIs that modify instance state
5. **Report errors on API failure**: If the script fails at any step, mark it as "retrieval failed" in the report. **Do NOT** attempt to obtain data through alternative methods

---

## How to Use This Skill

### Usage

**You do not need to run any scripts manually!** This is an AI Agent skill — simply describe your needs in natural language.

### Example Conversations

**Example 1: Single instance inspection**
```
Inspect Redis instance r-bp1xxxxxxxxxxxx
```

**Example 2: Multi-instance inspection**
```
Inspect instances r-bp1xxxxxxxxxxxx and r-bp2yyyyyyyyyyyyyy
```

**Example 3: Full account inspection (all instances)**
```
Inspect all Redis instances in my account
```

**Example 4: Specify Region**
```
Inspect Redis instance r-bp1xxxxxxxxxxxx in cn-hangzhou region
```

**Example 5: Resource usage with custom time range**
```
Show resource usage for r-bp1xxxxxxxxxxxx in the last 3 days
```
Maps to `--days 3`

**Example 6: Resource usage only**
```
Show CPU and memory usage for r-bp1xxxxxxxxxxxx
```
Maps to `--item resource`

**Example 7: Slow logs only**
```
Analyze recent slow logs for r-bp1xxxxxxxxxxxx
```
Maps to `--item slowlog`

**Example 8: Big/Hot key analysis**
```
Check for big keys and hot keys in r-bp1xxxxxxxxxxxx
```
Maps to `--item bigkey`

**Example 9: Combined inspection items**
```
Show slow logs and alert history for r-bp1xxxxxxxxxxxx
```
Maps to `--item slowlog --item alert`

**Example 10: Batch + specific items**
```
Show CPU usage for all instances in the last 3 days
```
Maps to `--all --days 3 --item resource`

**Example 11: Specify output format**
```
Generate a Markdown report for r-bp1xxxxxxxxxxxx
```
Maps to `--format markdown`

### AI Behavior Rules (MUST follow)

1. **Must use the script for inspection**: All inspection operations can **only** be done via `python3 scripts/health-inspect.py`. The AI's role is: identify user intent -> assemble correct script parameters -> execute script -> present report to user. **Do NOT call `aliyun` CLI directly to collect any inspection data**
2. **Inspection mode selection**: Choose the correct execution mode based on user intent
   - User says "all instances" / "full account" -> use `--all`
   - User specifies multiple instance IDs -> pass multiple IDs: `health-inspect.py r-xxx r-yyy`
   - User specifies a single instance -> single-instance mode: `health-inspect.py r-xxx`
3. **Inspection item selection**: Map user's focus areas to `--item` parameters
   - User mentions "CPU" / "memory" / "resource usage" / "connections" / "bandwidth" -> `--item resource`
   - User mentions "session" / "connection" / "active connections" / "client IPs" -> `--item session`
   - User mentions "big key" / "hot key" / "large key" / "memory usage by key" -> `--item bigkey`
   - User mentions "slow log" / "slow command" / "latency" -> `--item slowlog`
   - User mentions "alert" / "alarm" / "warning" / "notification" -> `--item alert`
   - User mentions multiple areas -> combine multiple `--item` (e.g., `--item resource --item slowlog`)
   - User does not specify (e.g., "run inspection" / "full check") -> do not add `--item`, default to full inspection
4. **Unified output**: Multi-instance (>=2) reports go to a single directory with an index page (index.html) + individual detail reports; single-instance outputs a single file
5. **Do not manually list instances then run one by one**: The script's `--all` has built-in instance discovery. The AI does not need to call `describe-instances` first
6. **On script failure**: If the script reports an error at any step, relay the error message to the user. **Do NOT** call aliyun CLI to try alternative data retrieval methods
7. **Do NOT ask follow-up questions after report output**: This skill is inspection-only. Once the report is generated, the task is complete. Do NOT append questions like "Need further analysis?" or any similar follow-up prompts

### AI Execution Flow (follow this order strictly)

1. Identify user intent, select correct inspection mode and parameters
2. Execute `python3 scripts/health-inspect.py <params>` — one command completes all data collection
3. The script automatically handles: Region discovery, R-kvstore API calls for performance data, report generation
4. Present the generated report file path to the user
5. Answer follow-up questions based on report content

---

# Alibaba Cloud Redis (KVStore) Instance Health Inspection Skill

This skill performs resource usage health inspection of Redis instances and generates standardized reports.

**Inspection Dimensions (7 Sections):**
1. **Instance Basic Information** — ID, name, version, class, architecture, status
2. **Current Sessions** — Connection usage distribution, node topology
3. **Resource Usage (Last 7 Days)** — CPU, Memory, Connection, Bandwidth with ECharts charts
4. **Big Key / Hot Key** — Cache analysis Top10 big keys and Top10 hot keys
5. **Slow Log Statistics (Last 7 Days)** — Slow command aggregation by type
6. **Alert History (Last 7 Days)** — CloudMonitor (CMS) alert records
7. **Inspection Conclusions & Recommendations** — Risk-prioritized suggestions

**Resource Metrics:**
- CPU Usage, Connection Usage, Memory Usage
- Input/Output Bandwidth Usage
- Proxy metrics (cluster/splitrw only)
- Persistent Memory Usage (Tair only)
- Disk Usage (Tair only)

**Architecture Support:**
- Standard (single-node, master-replica)
- Cluster (cluster edition)
- SplitRW (read-write splitting)

**Instance Type Support:**
- Redis Community Edition
- Tair (DRAM)
- Tair (Persistent Memory, InstanceClass: tair.scm.*)
- Tair (ESSD, InstanceClass: tair.essd.*)

**Architecture:** R-kvstore API (DescribeHistoryMonitorValues) + Aliyun CLI

---

## Prerequisites

**Runtime Environment:**
- Python >= 3.7
- Aliyun CLI >= 3.3.3
- OS: Linux / macOS / Windows

**Required CLI Tools:**
- aliyun CLI >= 3.3.3 (with valid credentials configured)
- No redis-cli needed (this skill completes all inspection via API, no direct Redis connection required)

**Python Dependencies:**
```bash
# Uses only Python standard library: subprocess, json, os, sys, datetime
# All Alibaba Cloud API calls are made through aliyun CLI
```

**Installation Verification:**
> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> see `references/cli-installation-guide.md` for detailed installation instructions,
> or run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> Then [MUST] run `aliyun plugin update` to ensure plugins are up-to-date.

**[MUST] CLI User-Agent** — Every **business API** `aliyun` CLI invocation (e.g. `aliyun r-kvstore …`, `aliyun das …`, `aliyun cms …`) MUST carry the `--user-agent` flag with the full UA template defined in the Observability section below. **System / utility commands MUST NOT carry `--user-agent`** (see the exclusion list in the Observability section). Do **NOT** rely on the deprecated `aliyun configure ai-mode` mechanism or the `ALIBABA_CLOUD_USER_AGENT` environment variable — both have been retired.

## Observability (MUST follow before any aliyun CLI invocation)

This skill emits observability headers via the `--user-agent` flag on **every business API** `aliyun` CLI command. The deprecated `aliyun configure ai-mode enable / disable / set-user-agent` commands and the `ALIBABA_CLOUD_USER_AGENT` env var MUST NOT be used.

**Scope rule (SA-2.11):**
- ✅ **Business API commands** (carry `--user-agent`): `aliyun r-kvstore <action>`, `aliyun das <action>`, `aliyun cms <action>`, etc.
- ❌ **System / utility commands** (MUST NOT carry `--user-agent`): `aliyun configure …` (e.g. `aliyun configure list`, `aliyun configure set`), `aliyun plugin …` (e.g. `aliyun plugin update`, `aliyun plugin install`, `aliyun plugin list`), `aliyun help`, `aliyun version`, `aliyun upgrade`, `aliyun --help`.

### Step 1 — Generate a session ID (once per skill invocation)

```bash
# 32-char lowercase hex without dashes (UUID v4)
export ALICLOUD_SKILL_SESSION_ID="$(uuidgen | tr -d '-' | tr 'A-F' 'a-f')"
```

### Step 2 — UA template (MUST use full format including session-id segment)

```
AlibabaCloud-Agent-Skills/alibabacloud-kvstore-health-inspection/${ALICLOUD_SKILL_SESSION_ID}
```

The `/{session-id}` segment is mandatory — a UA without it will be rejected by SA-2.11 review.

### Step 3 — Pass `--user-agent` on every **business API** aliyun CLI command

Applies only to business product commands (`r-kvstore` / `das` / `cms` / etc.). System commands listed in the scope rule above MUST NOT have `--user-agent` appended.

```bash
# ✅ Business API command — UA REQUIRED
aliyun r-kvstore describe-instances \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-kvstore-health-inspection/${ALICLOUD_SKILL_SESSION_ID}"

# ❌ System / utility commands — UA MUST NOT be passed
aliyun configure list
aliyun plugin update
aliyun version
```

The Python script `scripts/health-inspect.py` automatically injects this UA on every internal **business API** `aliyun` invocation, and never on system commands. When the AI issues direct CLI calls, it MUST append `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-kvstore-health-inspection/${ALICLOUD_SKILL_SESSION_ID}"` to **business API** commands only — and MUST NOT append it to `aliyun configure …`, `aliyun plugin …`, `aliyun help`, `aliyun version`, `aliyun upgrade`, or `aliyun --help`.

Do not skip the UA, alter the format, or omit the `/{session-id}` segment.

---

## Required RAM Permissions

This skill uses read-only APIs only. No write permissions are required.

For the full permission policy and detailed descriptions, see `references/ram-policies.md`.

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
| InstanceId | Required (omit with `--all`) | Redis instance ID (r-xxx), supports multiple | User must provide |
| RegionId | Optional | Instance region (auto-discovered if not provided) | Auto-discover |
| Days | Optional | Inspection time range (days) | 7 |
| Item | Optional | Specify inspection items (multiple allowed); omit for full inspection | Full |
| Profile | Optional | aliyun CLI profile name | Default profile |
| Output | Optional | Report output directory or file path | ~/Downloads/ |
| Format | Optional | Report format: html, markdown, text | html |

**Item values:**

| item | Inspection Content |
|------|-------------------|
| `resource` | CPU/memory/connection/bandwidth usage trends (data nodes + proxy nodes) |
| `session` | Current session information, connection usage, source IP statistics |
| `bigkey` | Big key / hot key analysis (large keys, big keys, hot keys, high traffic keys) |
| `slowlog` | Slow log statistics and command analysis |
| `alert` | Alert rules configuration and alert history |

---

## Core Workflow

### Recommended: Use the Automated Script (one-command inspection)

```bash
python3 scripts/health-inspect.py <INSTANCE_ID> [options]
```

**CLI Arguments:**

| Argument | Short | Description |
|----------|-------|-------------|
| `INSTANCE_ID` | (positional) | Redis instance ID, supports multiple; omit with `--all` |
| `--all` | | Inspect all Redis instances in the current account |
| `--region` | `-r` | Specify Region (auto-discovers if not specified) |
| `--days` | `-d` | Inspection time range (days), default 7 |
| `--item` | | Specify inspection item (can be used multiple times); omit for full. Options: resource, session, bigkey, slowlog, alert |
| `--profile` | `-p` | Specify aliyun CLI profile name |
| `--output` | `-o` | Specify report output directory or file path |
| `--format` | `-f` | Report format: html (default), markdown, text |

**Examples:**
```bash
# Single instance (auto-discover Region)
python3 scripts/health-inspect.py r-bp1xxxxxxxxxxxx

# Multi-instance
python3 scripts/health-inspect.py r-bp1xxxxxxxxxxxx r-bp2yyyyyyyyyyyyyy

# All instances in account
python3 scripts/health-inspect.py --all

# All instances in specific Region
python3 scripts/health-inspect.py --all --region cn-hangzhou

# Custom time range (last 3 days)
python3 scripts/health-inspect.py r-bp1xxxxxxxxxxxx --days 3

# Resource usage only (CPU/memory/connection/bandwidth)
python3 scripts/health-inspect.py r-bp1xxxxxxxxxxxx --item resource

# Big key and hot key analysis only
python3 scripts/health-inspect.py r-bp1xxxxxxxxxxxx --item bigkey

# Slow logs only
python3 scripts/health-inspect.py r-bp1xxxxxxxxxxxx --item slowlog

# Slow logs and alerts only
python3 scripts/health-inspect.py r-bp1xxxxxxxxxxxx --item slowlog --item alert

# Batch + specific items
python3 scripts/health-inspect.py --all --item resource --item slowlog

# Markdown format
python3 scripts/health-inspect.py r-bp1xxxxxxxxxxxx --format markdown

# Custom output directory
python3 scripts/health-inspect.py --all -o /tmp/redis_report

# Full parameters
python3 scripts/health-inspect.py r-bp1xxxxxxxxxxxx -p myprofile -r cn-hangzhou -d 14 -o ./report
```

The script completes all inspection steps automatically. For multi-instance runs, reports are output to a single directory with a summary page (index.html).

**Item Selection Examples:**

When the user specifies particular inspection items, map their intent to `--item` parameters:

```bash
# User says "check CPU and memory" -> resource item
python3 scripts/health-inspect.py r-bp1xxxxxxxxxxxx --item resource

# User says "analyze slow commands" -> slowlog item
python3 scripts/health-inspect.py r-bp1xxxxxxxxxxxx --item slowlog

# User says "find big keys" -> bigkey item
python3 scripts/health-inspect.py r-bp1xxxxxxxxxxxx --item bigkey

# User says "check sessions and connections" -> session item
python3 scripts/health-inspect.py r-bp1xxxxxxxxxxxx --item session

# User says "review alerts" -> alert item
python3 scripts/health-inspect.py r-bp1xxxxxxxxxxxx --item alert

# User specifies multiple items
python3 scripts/health-inspect.py r-bp1xxxxxxxxxxxx --item resource --item bigkey --item slowlog
```

When the user does not specify items, omit the `--item` parameter to run full inspection (all 7 sections).

---

> For manual step-by-step API call details, see `references/manual-workflow.md` (only use when the script is unavailable).

---

> For report output format templates (text + HTML/ECharts layout specs), see `references/report-format.md` (only reference when adjusting report styles).

---

## Reference Documents and Scripts

- `scripts/health-inspect.py` — One-command inspection main script
- `scripts/find-instance-region.py` — Auto-discover instance Region
- `scripts/check-write-operation.sh` — Write operation detection hook
- `config/metrics.json` — Metrics configuration per architecture type
- `references/manual-workflow.md` — Manual step-by-step API call details
- `references/report-format.md` — Inspection report output format specification
- `references/ram-policies.md` — RAM permission policy and setup guide
- `references/cli-installation-guide.md` — Aliyun CLI installation and configuration guide
