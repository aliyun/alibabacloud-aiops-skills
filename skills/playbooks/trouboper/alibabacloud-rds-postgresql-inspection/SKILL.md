---
name: alibabacloud-rds-postgresql-inspection
description: Batch health inspection for Alibaba Cloud RDS PostgreSQL instances. Supports single, multiple, or all-instance global scan with configurable time window (default 7 days, max 30). Outputs one HTML report per instance plus a summary HTML. Dimensions include instance basics, resource utilization (CPU/memory/disk/IOPS/connections), CloudMonitor alert history, slow log TOP 20, long transactions, table bloat, QPS/TPS, replication delay. Cluster instances auto-detected with per-node metrics. Triggers on RDS inspection, RDS health check, RDS PostgreSQL inspection, Alibaba Cloud RDS inspection, batch or global multi-instance inspection, slow log analysis, space analysis, PostgreSQL inspection, long transaction, table bloat, replication delay. Chinese triggers: "巡检 RDS PostgreSQL"、"RDS PostgreSQL 巡检"、"RDS 健康巡检"、"RDS 健康检查"、"阿里云 RDS 巡检"、"批量巡检"、"全局巡检"、"所有实例巡检"、"实例巡检"、"慢日志分析"、"长事务"、"表膨胀"、"复制延迟"、"健康评分"、"汇总报告"。
---

# Alibaba Cloud RDS PostgreSQL Instance Inspection Skill

This skill performs batch health inspections of Alibaba Cloud RDS PostgreSQL instances. It supports three modes — single instance, multiple instances, and global batch — with a configurable time window (default 7 days, up to 30 days), and produces standardized HTML inspection reports.

## ⚡ TL;DR — Run ONE command, do NOT improvise

> **The ONLY correct way to fulfil any inspection request is to execute `scripts/inspect.py`.**
> The agent MUST NOT fabricate a markdown summary, MUST NOT chain `aliyun rds describe-*` calls in the conversation, and MUST NOT write any `*.md` / `*_health_report.md` file as the deliverable. The script writes the required HTML files (`instances/<id>.html` per instance, plus `summary.html` in global mode) by itself.

```bash
# Global / batch / 全部 / 所有 / 全局 (the failed eval scenario):
SKILL_SESSION_ID={session-id} python3 scripts/inspect.py --all --days 7

# Single or multiple instances:
SKILL_SESSION_ID={session-id} python3 scripts/inspect.py -i pgm-xxx[,pgm-yyy] --days 7
```

Deliverables produced by the script (the eval asserts on these exact paths):
- `outputs/instances/<DBInstanceId>.html` — one per instance, **5 sections**.
- `outputs/summary.html` — only in `--all` mode, **8 chapters**, with health-score ranking sorted ascending and clickable links to each `instances/<id>.html`.
- ❌ NEVER write `rds_postgresql_health_report.md`, `health_summary.json`, `instances.csv` or any `.md` / `.json` / `.csv` file into `outputs/` as the report.

## Usage

**You do not need to run any command manually.** Simply describe the request in natural language.

### Example Prompts

**Example 1: Single instance**
- `Inspect RDS PostgreSQL instance pgm-bp1xxxxxx`

**Example 2: Multiple instances with a custom time window**
- `Inspect pgm-bp1xxx and pgm-bp1yyy for the past 14 days`

**Example 3: Global inspection**
- `Run a health inspection on all RDS PostgreSQL instances and produce a summary report`

**Example 4: Limit by region**
- `Inspect all RDS PostgreSQL instances in cn-hangzhou and cn-shanghai`

### What the AI Does Automatically

1. Recognizes the user intent (single / multiple / global) and extracts the time-window parameters.
2. Calls `rds describe-regions` to obtain the list of available regions (filters out `ClosedDown`).
3. Concurrently scans every region for RDS PostgreSQL instances (region ID is carried automatically — the user does not need to specify it).
4. Concurrently retrieves attributes, monitoring, alerts, and slow logs for each target instance.
5. Emits one HTML report per instance plus a summary HTML report, including a health-score ranking and optimization suggestions.

---

## [MUST] Execution Mode — Always Run the Script, Never Hand-craft CLI

**This skill is a one-shot script-driven tool. The agent MUST execute `scripts/inspect.py` end-to-end and MUST NOT improvise a sequence of `aliyun` CLI calls in place of the script.** The script is the only place that correctly implements Phase 1 (DescribeRegions) → Phase 2 (cross-region DescribeDBInstances) → Phase 3-7 collection + rendering.

### Intent → Command mapping (MUST follow exactly)

| User intent (any of the trigger keywords) | MUST run | MUST NOT do |
|------|------|------|
| `全部` / `所有` / `全局` / `批量` / `--all` / "all instances" / "global inspection" / "every RDS PostgreSQL" | `SKILL_SESSION_ID={session-id} python3 scripts/inspect.py --all [--days N]` | ❌ Calling `aliyun rds describe-db-instances` directly without iterating regions; ❌ relying on the default profile region only; ❌ skipping `describe-regions` |
| One or more instance IDs (`pgm-xxx` / `pgm-yyy`) | `SKILL_SESSION_ID={session-id} python3 scripts/inspect.py -i pgm-xxx[,pgm-yyy] [--days N]` | ❌ Asking the user for the region; ❌ hard-coding `cn-hangzhou` |
| Specific regions (e.g. "inspect all in cn-hangzhou and cn-shanghai") | `SKILL_SESSION_ID={session-id} python3 scripts/inspect.py --all --regions cn-hangzhou,cn-shanghai` | ❌ Skipping `--regions` and manually iterating regions with CLI |

### [MUST] Hard rules — apply to **ALL** modes (single / multiple / global)

These rules are NOT only for global mode. The single-instance and multi-instance modes have failed evals for the **exact same root cause**: the agent stitched a chain of `aliyun` CLI calls in the conversation, hit a timeout, and produced an empty `outputs/` directory with no HTML report. Treat the rules below as universal:

1. **MUST execute `python3 scripts/inspect.py` exactly once with the appropriate flags.** Do NOT replace it with a sequence of `aliyun rds describe-*` / `aliyun cms describe-*` calls in the conversation. The script is the only path that produces the required HTML report (5 chapters per instance + summary).
2. **MUST pass `--all`** for `全部` / `所有` / `全局` / `批量` / all / global / every. Without `--all` the script will refuse to enter global scan mode.
3. **MUST pass `-i <id1>[,<id2>...]`** for specific instance IDs. The agent MUST NOT ask the user for region; the script auto-locates region via `DescribeDBInstances`.
4. **MUST let the script handle Phase 1 (DescribeRegions) and Phase 2 (cross-region DescribeDBInstances) internally.** The agent MUST NOT replace these phases with manual single-region CLI calls.
5. **MUST NOT** hard-code, default to a single region, **OR cherry-pick a hand-curated subset of regions**. The script iterates **every** region returned by `DescribeRegions` (excluding `ClosedDown`) — typically 50+ regions. Picking only the "common" ones (e.g. `cn-hangzhou / cn-shanghai / cn-beijing / cn-shenzhen / cn-hongkong`) means missing instances in `cn-qingdao`, `cn-zhangjiakou`, `cn-chengdu`, `ap-southeast-*`, `us-east-*`, etc., and the global-scan assertion will fail.
6. **MUST produce HTML output**:
   - Single / multiple instance mode → each instance gets `instances/<DBInstanceId>.html` with **5 sections**: Instance Basics / Resource Utilization / Slow Log TOP 20 / Alert History / Performance Sub-metrics.
   - Global mode → additionally produces `summary.html` (8 chapters).
7. **MUST keep the time window consistent across data sources.** The script computes a single `start_ms` / `end_ms` from `--days` (default 7) and reuses it for monitoring (CMS) / alert history / slow logs / RDS performance API. Manual CLI stitching breaks this consistency and fails the time-window-consistency assertion.
8. **MUST NOT spend Step 0 budget on raw data collection.** A typical 7-day full inspection touches dozens of CLI invocations — stitching them sequentially in the conversation will be terminated/timed out before HTML rendering. The script uses concurrent execution (default `-c 3`) to fit the budget.
9. **MUST NOT fabricate any hand-written deliverable.** The deliverable is HTML rendered by the script, NOT Markdown / JSON / CSV stitched together by the agent. Specifically forbidden filenames observed in failed evals: `rds_postgresql_health_report.md`, `health_summary.json`, `instances.csv`, `*_report.md`, `summary.md`. The agent MUST NOT write `*.md` / `*.json` / `*.csv` files into `outputs/` as the inspection result. The script renders `outputs/instances/<id>.html` and `outputs/summary.html` directly; the agent's job is to run the script and surface those HTML files.
10. **MUST NOT redesign the report sections.** The script writes verbatim chapter / section titles — the agent MUST NOT reorder, rename, drop, merge, or invent any of them.

    **`summary.html` MUST contain exactly these 8 chapters (in this order):**
    1. Inspection Overview
    2. Health Score Ranking
    3. Alert Instance Statistics
    4. Resource Utilization Top
    5. Slow Log Top
    6. Version & Expiration
    7. Inspection Conclusion
    8. Optimization Suggestions

    **`instances/<id>.html` MUST contain exactly these 5 sections (in this order):**
    1. Instance Basics
    2. Resource Utilization
    3. Slow Log TOP 20
    4. Alert History
    5. Performance Sub-metrics

    **Forbidden self-invented chapters** — any subjective/narrative sections not matching the above whitelist (e.g. assessment, limitations, prioritized actions) will fail evals. If you find yourself composing them, STOP and run the script instead.

### Anti-patterns (guaranteed eval failures)

| Pattern | Root cause | Result |
|---------|-----------|--------|
| A: stitching `aliyun` CLI calls manually | Sequential calls exhaust time budget | Empty `outputs/`, no HTML |
| B: no `describe-regions`, only default region | Misses instances in other regions | Global-scan assertion fails |
| B': cherry-picking 5 "common" regions | Misses 45+ regions | Same as B |
| C: writing `.md`/`.json`/`.csv` deliverables | Script output is HTML only | Wrong file type/structure |

### Correct patterns

```bash
# Single instance, last 7 days (default):
SKILL_SESSION_ID={session-id} python3 scripts/inspect.py -i pgm-bp19l6h44g401c7s --days 7

# Multiple instances, custom window:
SKILL_SESSION_ID={session-id} python3 scripts/inspect.py -i pgm-xxx,pgm-yyy --days 14

# Global scan across every non-closed region:
SKILL_SESSION_ID={session-id} python3 scripts/inspect.py --all --days 7

# Global scan limited to specific regions:
SKILL_SESSION_ID={session-id} python3 scripts/inspect.py --all --regions cn-hangzhou,cn-shanghai --days 7
```

The script computes one `start_ms` / `end_ms` shared across all data sources, runs concurrent collection, and writes HTML reports.

---

## Prerequisites

### Runtime

- **Python**: 3.7+ (standard library only)
- **OS**: Linux / macOS / Windows
- **Aliyun CLI**: >= 3.3.3, configured with valid credentials

### Installation Checks

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify the version is >= 3.3.3. If the CLI is missing or outdated,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install or upgrade,
> or follow https://help.aliyun.com/zh/cli/ for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] Run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] Run `aliyun plugin update` to ensure all locally installed plugins are up to date.

```bash
aliyun version
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

### Python Dependencies

Only Python standard library modules are used (`subprocess`, `json`, `argparse`, `concurrent.futures`, `datetime`); `pip install` is not required.

---

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once
for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**

Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag
and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-rds-postgresql-inspection/{session-id}
```

**Script execution:**

```bash
SKILL_SESSION_ID={session-id} python3 scripts/inspect.py
```

---

## Required RAM Permissions

This skill uses read-only RDS / CMS APIs. The full custom-policy JSON, per-action purpose table, and system-policy alternatives are declared in [references/ram-policies.md](references/ram-policies.md). Attach that policy to the executing RAM identity before running the skill.

> **[MUST] Permission Failure Handling:**
> If you encounter permission errors (e.g., `Forbidden.RAM`, `NoPermission`, `403`):
> 1. Read `references/ram-policies.md` for the required permissions
> 2. Use `ram-permission-diagnose` skill to diagnose the missing permissions
> 3. Pause and wait for the user to grant the required permissions before retrying

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
>
> Inspect the output and confirm a valid profile exists. If no credentials are configured, guide the user to configure them outside of the conversation:
> ```bash
> aliyun configure
> ```

---

## CLI Argument Reference

```bash
python3 scripts/inspect.py [options]
```

| Argument | Short | Type | Description | Default |
|----------|-------|------|-------------|---------|
| `--instance-ids` | `-i` | string | Instance ID (repeatable, or comma-separated in a single value) | none |
| `--all` | — | flag | Globally inspect every RDS PostgreSQL instance | off |
| `--days` | `-d` | int | Time-window length in days (1-30) | 7 |
| `--start-time` | — | YYYY-MM-DD | Start date (mutually exclusive with `--days`) | none |
| `--end-time` | — | YYYY-MM-DD | End date (must be supplied together with `--start-time`) | none |
| `--output` | `-o` | path | Output directory | `./rds-pg-inspection-reports/<ts>/` |
| `--profile` | `-p` | string | Aliyun CLI profile name | default profile |
| `--regions` | — | string | Limit the scan to specific regions (comma-separated) | all |
| `--concurrency` | `-c` | int | Per-instance inspection concurrency | 3 |
| `--region-concurrency` | — | int | Region scan concurrency | 3 |

**Validation rules (enforced automatically by the script):**
- Exactly one of `-i` or `--all` is required.
- `--days` must be between 1 and 30; values outside this range raise an error.
- `--start-time` and `--end-time` must be supplied together, with a span of <= 30 days.

---

## Core Workflow

> **The phases below describe what `scripts/inspect.py` performs internally.** The agent's job is to launch the script with the right flags (see the Execution Mode section above), NOT to re-implement these phases by stitching `aliyun` CLI calls together. Phase 1 and Phase 2 in particular are MANDATORY for global / batch mode and MUST NOT be skipped.

### Phase 1: Fetch the Available Region List **[MUST, executed by the script]**

```bash
aliyun rds describe-regions --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rds-postgresql-inspection/{session-id}
```

Extract `RegionId` from the returned `Regions.RDSRegion[]` and drop any region whose `Status` contains `closed`.

> **[MUST]** Skipping this step in global / batch mode is a hard failure — the scan will be silently limited to the default profile region and miss instances in every other region.

### Phase 2: Concurrently Scan RDS PostgreSQL Instances Across Regions **[MUST, executed by the script]**

For **every** region returned by Phase 1 (or the explicit `--regions` whitelist), call:
```bash
aliyun rds describe-db-instances --region <RegionId> \
  --engine PostgreSQL --page-size 100 --page-number <N> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rds-postgresql-inspection/{session-id}
```

Paginate based on `TotalRecordCount` until all records are retrieved. Merge into a complete `[{instanceId, regionId, ...}]` list.

> **[MUST]** A single `DescribeDBInstances` call without iterating regions is **NOT** a valid global scan and will fail the global-coverage assertion.

### Phase 3: Filter Target Instances

- `--all`: every instance.
- `-i id1,id2`: filter from the full list (the region ID for each instance is carried automatically; the user does not need to specify it).

Unmatched instance IDs produce a warning but do not abort the overall workflow.

### Phase 4: Instance Attribute Query (default concurrency 3)

```bash
aliyun rds describe-db-instance-attribute --region <RegionId> \
  --db-instance-id <InstanceId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rds-postgresql-inspection/{session-id}
```

Extract the key fields: `Category` (determines whether the instance is a cluster), `DBClusterNodes` (cluster node list), `MaxConnections`, `MaxIOPS`, `MaxIOMBPS`, `CurrentKernelVersion`, `LatestKernelVersion`, `ExpireTime`, etc.

### Phase 5: Per-Instance Inspection (default concurrency 3)

Within each instance, the following collection steps run sequentially.

#### 5.1 CMS Metric Collection (`cms describe-metric-list`)

Five core metrics. The MetricName and Dimensions depend on whether the instance is a cluster.

**Cluster instances** (`Category=cluster`, queried per node):
| MetricName | Meaning |
|------------|---------|
| `Cluster_CpuUsage` | CPU utilization |
| `Cluster_MemoryUsage` | Memory utilization |
| `Cluster_DiskUsage` | Disk utilization |
| `Cluster_IOPSUsage` | IOPS utilization |
| `Cluster_ConnectionUsage` | Connection utilization |

Dimensions: `[{"instanceId":"<DBInstanceId>","nodeId":"<NodeId>"}]`

**Non-cluster instances:**
| MetricName | Meaning |
|------------|---------|
| `CpuUsage` / `MemoryUsage` / `DiskUsage` / `IOPSUsage` / `ConnectionUsage` | Same as above |

Dimensions: `[{"instanceId":"<DBInstanceId>"}]`

Invocation template:
```bash
aliyun cms describe-metric-list \
  --namespace acs_rds_dashboard \
  --metric-name <MetricName> \
  --period 60 \
  --start-time <StartMillis> --end-time <EndMillis> \
  --dimensions '<JSON>' \
  --length 2000 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rds-postgresql-inspection/{session-id}
```

Paginate via `NextToken` until all data points are retrieved.

#### 5.2 RDS Performance Metrics (`rds describe-db-instance-performance`)

PostgreSQL-specific performance metrics with sub-metrics:

| MetricName | Sub-metrics |
|------------|-------------|
| `MemoryUsage` | Memory utilization details |
| `CpuUsage` | CPU utilization details |
| `PgSQL_IOPS` | IOPS breakdown (read/write) |
| `PolarDBConnections` | Connection breakdown (active/idle) |
| `PgSQL_SpaceUsage` | Space utilization details |
| `PolarDBLocalDiskUsage` | Local disk usage |
| `PolarDBLongTransaction` | Long transaction details |
| `PolarDBQPSTPS` | QPS/TPS metrics |
| `PolarDBSwellTime` | Swell time metrics |
| `PolarDBReplication` | Replication delay |

```bash
aliyun rds describe-db-instance-performance \
  --region <RegionId> \
  --db-instance-id <InstanceId> \
  --key <MetricName> \
  --start-time <YYYY-MM-DD> --end-time <YYYY-MM-DD> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rds-postgresql-inspection/{session-id}
```

#### 5.3 CMS Alert History (`cms describe-alert-log-list`)

```bash
aliyun cms describe-alert-log-list \
  --namespace acs_rds_dashboard --product rds \
  --search-key <DBInstanceId> \
  --start-time <ms> --end-time <ms> \
  --page-size 100 --page-number <N>
```

Page through all results. Sort by alert severity in descending order: CRITICAL / P0 / P1 > WARN / P2 > INFO / P3 / P4.

#### 5.4 Slow Log Records (`rds describe-slow-log-records`)

```bash
aliyun rds describe-slow-log-records \
  --region <RegionId> \
  --db-instance-id <InstanceId> \
  --start-time <YYYY-MM-DD> --end-time <YYYY-MM-DD> \
  --page-size 100 --page-number <N> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rds-postgresql-inspection/{session-id}
```

Retrieve TOP 20 slow log records sorted by execution time.

**Important — 24-hour API limit:** `DescribeSlowLogRecords` only allows the
`StartTime`/`EndTime` interval to span at most 24 hours per call. To keep the
slow-log statistics window aligned with the monitoring data and alert history
window (e.g. 7 days), you MUST split the requested window into ≤24-hour
chunks, call this API once per chunk, then aggregate the results, sort by
execution time, and take the global TOP 20 across the full window.

### Phase 6: Health Score Calculation

Each instance is scored 0-100. Deductions:
- CPU / memory / IOPS / connection peak > 80%: -10; > 60%: -5
- Disk > 85%: -15; > 70%: -5
- Total slow log entries > 1000: -8; > 100: -3
- Critical / severe alerts: -10
- Kernel version not on the latest release: -3
- Expiring within 30 days: -5
- Instance is in Lock state: -8

### Phase 7: Single-Instance HTML Rendering (5 Sections)

Each instance produces `instances/<DBInstanceId>.html` containing the following sections:

1. **Instance basics** — DBInstanceId / Engine + Version / Category (with a `(cluster)` tag) / Class / Storage / MaxConnections / MaxIOPS / MaxIOMBPS / primary and secondary zones / VPC + VSwitch / status / pay type / Lock / maintenance window / creation + expiration / current + latest kernel / cluster node list (for clusters).
2. **Resource utilization (past N days)** — A table with average / peak / status color per metric, plus five ECharts line charts (linked via `dataZoom`); one line per node for clusters. PostgreSQL-specific sub-metrics are displayed for each metric.
3. **Slow log TOP 20** — Sorted by execution time. Columns: execution time / query time / lock time / rows examined / rows sent / SQL text.
4. **Alert history (past N days)** — Table sorted by severity, capped at 200 rows.
5. **Performance metrics with sub-metrics** — Detailed breakdown of PostgreSQL-specific metrics (long transactions, table bloat, QPS/TPS, replication delay, etc.).

### Phase 8: Summary HTML Rendering (8 Sections)

Outputs `summary.html`, with anchor navigation plus the following eight sections:

1. **Inspection overview** — KPI cards (total / region count / cluster count / global health score / health distribution / alerting instance count) plus four pie / bar charts (category / status / health / per region).
2. **Health score ranking** — Top 20 least-healthy instances, each row linking to the corresponding single-instance report.
3. **Alerting instance statistics** — KPI cards + a severity-distribution bar chart + the top 20 instances by alert count.
4. **Resource utilization Top lists** — Five top-20 tables (CPU / memory / disk / IOPS / connections), sorted by peak value.
5. **Slow log Top lists** — Top instances by slow log count, by total execution time, and by single-statement maximum execution time (aggregated across instances).
6. **Version and expiration** — Instances with kernel upgrades available, expiring within 30 days, and expiring within 90 days.
7. **Inspection conclusion** — KPI cards (global health score + instance counts in the healthy / needs-attention / critical categories) plus an aggregated issue list (grouped by issue type: high CPU / high memory / tight space / many slow logs / many alerts / outdated kernel / approaching expiration — each row lists the affected instance IDs).
8. **Optimization suggestions** — Prioritized recommendations derived from the aggregated issue list (e.g. raise spec for chronic high CPU/memory, expand storage for tight space, schedule kernel minor upgrade for outdated versions, renew approaching-expiration instances).

> Note: The script does NOT emit a standalone "Performance metrics summary" chapter at the summary level. PostgreSQL-specific metrics (long transactions / table bloat / QPS / TPS / replication delay) are reported per instance under `instances/<id>.html` § 5 (`Performance Sub-metrics`); summary.html aggregates them indirectly through resource Top lists, slow log Top lists and the issue list in the Inspection Conclusion chapter.

---

## Report Output Structure

```
./rds-pg-inspection-reports/<timestamp>/
├── summary.html                  # Aggregated inspection report (8 sections)
└── instances/
    ├── pgm-bp1xxx.html           # Per-instance report (5 sections)
    ├── pgm-bp1yyy.html
    └── ...
```

In the summary report, every instance ID is a hyperlink that opens the corresponding per-instance report in a new tab.

---

## Status Thresholds

| Metric | Normal | Warning | Critical |
|--------|--------|---------|----------|
| CPU utilization | < 60% | 60-80% | > 80% |
| Memory utilization | < 60% | 60-80% | > 80% |
| Disk utilization | < 70% | 70-85% | > 85% |
| IOPS utilization | < 60% | 60-80% | > 80% |
| Connection utilization | < 60% | 60-80% | > 80% |
| Overall health score | >= 80 | 60-79 | < 60 |

---

## Cluster vs Non-Cluster Handling

| Dimension | Non-cluster instance | Cluster instance (`Category=cluster`) |
|-----------|----------------------|----------------------------------------|
| CMS MetricName | No prefix (`CpuUsage`, etc.) | Prefixed with `Cluster_` |
| CMS Dimensions | `{"instanceId":"<id>"}` | `{"instanceId":"<id>","nodeId":"<nid>"}`, queried per node |
| HTML metric charts | Single line | One line per node |
| Cluster-level aggregation | N/A | CPU / memory peak = max of all node peaks |

The cluster node list is obtained from the `DBClusterNodes` field returned by `rds describe-db-instance-attribute`.

---

## Performance Estimates

| Scenario | Estimated Duration |
|----------|--------------------|
| Single instance | 30-120 seconds |
| 10 instances at concurrency 3 | 5-15 minutes |
| 50 instances with `--all` | 30-90 minutes |

**Tips for faster runs:**
- When the target instances' regions are known, use `--regions cn-hangzhou,...` to skip other regions.
- Increase `-c` for higher concurrency (be aware that the CMS API has a default 20 QPS limit; <= 5 is recommended).

---

## Safety Rules

**This is a read-only inspection skill.**
- Mutating operations (DDL / DML, instance configuration changes) are strictly forbidden.
- Only inspection results and optimization suggestions are produced.
- Any mutating operation must be confirmed and executed manually by the user outside of the conversation.
- **Do NOT ask follow-up questions after report output.** This skill is a one-shot report generation tool; once the report is delivered, the task is complete.

---

## References

- `scripts/inspect.py` — Main inspection script (CLI + collection + rendering).
- `references/ram-policies.md` — Full RAM permission reference (custom policy JSON + action purposes).
- Alibaba Cloud RDS API: https://help.aliyun.com/zh/rds/developer-reference/
- Alibaba Cloud CMS API: https://help.aliyun.com/zh/cms/cloudmonitor-1-0/developer-reference/
