---
name: alibabacloud-rds-mysql-inspection
description: |
  Batch health inspection for Alibaba Cloud RDS MySQL instances. Supports single, multiple, or all-instance global scan with configurable time window (default 7 days, max 30). Outputs one HTML report per instance plus a summary HTML. Dimensions: instance basics, resource utilization (CPU/memory/disk/IOPS/connections), CloudMonitor alert history, top 20 space-consuming tables (DAS), slow log statistics (DAS), kernel-version / expiration checks. Cluster instances auto-detected; per-node metrics and slow logs.
  Triggers: RDS inspection, RDS health check, RDS MySQL inspection, Alibaba Cloud RDS inspection, batch/global/multi-instance inspection, slow log analysis, space analysis, RDS 巡检, 阿里云 RDS 巡检, 数据库巡检, 批量巡检, 慢日志分析, 表空间分析.
---

# Alibaba Cloud RDS MySQL Instance Inspection Skill

This skill performs batch health inspections of Alibaba Cloud RDS MySQL instances. It supports three modes — single instance, multiple instances, and global batch — with a configurable time window (default 7 days, up to 30 days), and produces standardized HTML inspection reports.

## Usage

**You do not need to run any command manually.** Simply describe the request in natural language.

### Example Prompts

**Example 1: Single instance**
- EN: `Inspect RDS instance rm-bp1xxxxxx`
- ZH: `帮我巡检下 RDS 实例 rm-bp1xxxxxx`

**Example 2: Multiple instances with a custom time window**
- EN: `Inspect rm-bp1xxx and rm-bp1yyy for the past 14 days`
- ZH: `巡检 rm-bp1xxx 和 rm-bp1yyy 这两个实例，看最近 14 天的情况`

**Example 3: Global inspection**
- EN: `Run a health inspection on all RDS MySQL instances and produce a summary report`
- ZH: `帮我对所有 RDS MySQL 实例做一次健康巡检，输出汇总报告`

**Example 4: Limit by region**
- EN: `Inspect all RDS MySQL instances in cn-hangzhou and cn-shanghai`
- ZH: `巡检 cn-hangzhou 和 cn-shanghai 两个 region 的所有 RDS MySQL 实例`

### What the AI Does Automatically

1. Recognizes the user intent (single / multiple / global) and extracts the time-window parameters.
2. Calls `rds describe-regions` to obtain the list of available regions (filters out `ClosedDown`).
3. Concurrently scans every region for RDS MySQL instances (region ID is carried automatically — the user does not need to specify it).
4. Concurrently retrieves attributes, monitoring, alerts, slow logs, and space data for each target instance.
5. Automatically detects cluster instances and collects per-node data.
6. Emits one HTML report per instance plus a summary HTML report, including a health-score ranking and optimization suggestions.

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

## [MUST] CLI User-Agent and AI-Mode Mandatory Rules

> **[MUST] CLI User-Agent** — Every `aliyun` CLI invocation made by this skill must include:
> `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-rds-mysql-inspection`
>
> The `call_cli()` wrapper in `scripts/inspect.py` injects this UA automatically, so it does not need to be repeated on each command.

> **[MUST] Enable AI-Mode** — AI-mode must be enabled before any Agent Skill execution.
> Run the following before invoking any CLI command:
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-rds-mysql-inspection"
> ```

> **[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response (regardless of success, failure, exception, user cancellation, or session end), AI-mode must be disabled. AI-mode is reserved for active Agent Skill executions and must not remain enabled once the skill stops running.
> ```bash
> aliyun configure ai-mode disable
> ```

---

## Required RAM Permissions

This skill uses read-only RDS / CMS / DAS APIs. The full custom-policy JSON, per-action purpose table, and system-policy alternatives are declared in [references/ram-policies.md](references/ram-policies.md). Attach that policy to the executing RAM identity before running the skill.

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
| `--all` | — | flag | Globally inspect every RDS MySQL instance | off |
| `--days` | `-d` | int | Time-window length in days (1-30) | 7 |
| `--start-time` | — | YYYY-MM-DD | Start date (mutually exclusive with `--days`) | none |
| `--end-time` | — | YYYY-MM-DD | End date (must be supplied together with `--start-time`) | none |
| `--output` | `-o` | path | Output directory | `./rds-inspection-reports/<ts>/` |
| `--profile` | `-p` | string | Aliyun CLI profile name | default profile |
| `--regions` | — | string | Limit the scan to specific regions (comma-separated) | all |
| `--concurrency` | `-c` | int | Per-instance inspection concurrency | 3 |
| `--region-concurrency` | — | int | Region scan concurrency | 3 |
| `--skip-space` | — | flag | Skip the DAS space analysis (saves 30-150 s per instance) | off |

**Validation rules (enforced automatically by the script):**
- Exactly one of `-i` or `--all` is required.
- `--days` must be between 1 and 30; values outside this range raise an error.
- `--start-time` and `--end-time` must be supplied together, with a span of <= 30 days.

---

## Core Workflow

### Phase 1: Fetch the Available Region List

```bash
aliyun rds describe-regions --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rds-mysql-inspection
```

Extract `RegionId` from the returned `Regions.RDSRegion[]` and drop any region whose `Status` contains `closed`.

### Phase 2: Concurrently Scan RDS MySQL Instances Across Regions

For each region, call:
```bash
aliyun rds describe-db-instances --region <RegionId> \
  --engine MySQL --page-size 100 --page-number <N> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rds-mysql-inspection
```

Paginate based on `TotalRecordCount` until all records are retrieved. Merge into a complete `[{instanceId, regionId, ...}]` list.

### Phase 3: Filter Target Instances

- `--all`: every instance.
- `-i id1,id2`: filter from the full list (the region ID for each instance is carried automatically; the user does not need to specify it).

Unmatched instance IDs produce a warning but do not abort the overall workflow.

### Phase 4: Instance Attribute Query (default concurrency 3)

```bash
aliyun rds describe-db-instance-attribute --region <RegionId> \
  --db-instance-id <InstanceId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rds-mysql-inspection
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
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rds-mysql-inspection
```

Paginate via `NextToken` until all data points are retrieved.

#### 5.2 CMS Alert History (`cms describe-alert-log-list`)

```bash
aliyun cms describe-alert-log-list \
  --namespace acs_rds_dashboard --product rds \
  --search-key <DBInstanceId> \
  --start-time <ms> --end-time <ms> \
  --page-size 100 --page-number <N>
```

Page through all results. Sort by alert severity in descending order: CRITICAL / P0 / P1 > WARN / P2 > INFO / P3 / P4.

#### 5.3 DAS Slow Log Statistics (`das describe-slow-log-statistic`)

```bash
aliyun das describe-slow-log-statistic \
  --instance-id <DBInstanceId> \
  --start <ms> --end <ms> \
  --order-by <Count|QueryTime> \
  [--node-id <NodeId>] \
  --endpoint das.cn-shanghai.aliyuncs.com
```

**Notes:**
- The DAS endpoint is fixed at `das.cn-shanghai.aliyuncs.com` (DAS is centrally deployed).
- Cluster instances must pass `--node-id` (use the Master node).
- Run the query twice — once ordered by `Count` and once by `QueryTime`.

#### 5.4 DAS Space Analysis — Top 20

```bash
# Trigger the task
aliyun das create-storage-analysis-task \
  --instance-id <DBInstanceId> \
  --endpoint das.cn-shanghai.aliyuncs.com

# Poll for results
aliyun das get-storage-analysis-result \
  --instance-id <DBInstanceId> --task-id <TaskId> \
  --endpoint das.cn-shanghai.aliyuncs.com
```

Poll every 5 seconds, with a 180-second cap. Take the top 20 tables from `StorageAnalysisResult.TableStats`.

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
2. **Resource utilization (past N days)** — A table with average / peak / status color per metric, plus five ECharts line charts (linked via `dataZoom`); one line per node for clusters.
3. **Top 20 space-consuming tables** — Sorted from DAS `TableStats`. Columns: database / table / total space / data / index / fragmentation / row count.
4. **Slow log statistics (past N days)** — Two tables: top by Count and top by QueryTime.
5. **Alert history (past N days)** — Table sorted by severity, capped at 200 rows.

### Phase 8: Summary HTML Rendering (8 Sections)

Outputs `summary.html`, with anchor navigation plus the following eight sections:

1. **Inspection overview** — KPI cards (total / region count / cluster count / global health score / health distribution / alerting instance count) plus four pie / bar charts (category / status / health / per region).
2. **Health score ranking** — Top 20 least-healthy instances, each row linking to the corresponding single-instance report.
3. **Alerting instance statistics** — KPI cards + a severity-distribution bar chart + the top 20 instances by alert count.
4. **Resource utilization Top lists** — Five top-20 tables (CPU / memory / disk / IOPS / connections), sorted by peak value.
5. **Slow log Top lists** — Top instances by slow log count, by total execution time, and by single-statement maximum execution time (aggregated across instances).
6. **Space analysis** — Top instances by used space, top 20 single tables (aggregated across instances), and tables with the highest fragmentation rate.
7. **Version and expiration** — Instances with kernel upgrades available, expiring within 30 days, and expiring within 90 days.
8. **Inspection conclusion** — KPI cards (global health score + instance counts in the healthy / needs-attention / critical categories) plus an aggregated issue list (grouped by issue type: high CPU / high memory / tight space / many slow logs / many alerts / outdated kernel / approaching expiration — each row lists the affected instance IDs).

---

## Report Output Structure

```
./rds-inspection-reports/<timestamp>/
├── summary.html                  # Aggregated inspection report (8 sections)
└── instances/
    ├── rm-bp1xxx.html            # Per-instance report (5 sections)
    ├── rm-bp1yyy.html
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
| DAS slow log | `--instance-id` only | Must also pass `--node-id` (use the Master node) |
| HTML metric charts | Single line | One line per node |
| Cluster-level aggregation | N/A | CPU / memory peak = max of all node peaks |

The cluster node list is obtained from the `DBClusterNodes` field returned by `rds describe-db-instance-attribute`.

---

## Performance Estimates

| Scenario | Estimated Duration |
|----------|--------------------|
| Single instance (with space analysis) | 60-200 seconds |
| Single instance (`--skip-space`) | 10-30 seconds |
| 10 instances at concurrency 3 | 5-15 minutes |
| 50 instances with `--all` | 30-90 minutes |

**Tips for faster runs:**
- For large batches, use `--skip-space`; DAS space analysis costs 30-150 seconds per instance.
- When the target instances' regions are known, use `--regions cn-hangzhou,...` to skip other regions.
- Increase `-c` for higher concurrency (be aware that the CMS API has a default 20 QPS limit; <= 5 is recommended).

---

## Safety Rules

**This is a read-only inspection skill.**
- Mutating operations (DDL / DML, instance configuration changes) are strictly forbidden.
- Only inspection results and optimization suggestions are produced.
- The single non-read CLI call used by this skill is `das create-storage-analysis-task`, which schedules a side analysis task and does not modify any instance data; all other invocations are pure read operations.
- Any mutating operation must be confirmed and executed manually by the user outside of the conversation.

---

## References

- `scripts/inspect.py` — Main inspection script (CLI + collection + rendering).
- `references/ram-policies.md` — Full RAM permission reference (custom policy JSON + action purposes).
- Alibaba Cloud RDS API: https://help.aliyun.com/zh/rds/developer-reference/
- Alibaba Cloud CMS API: https://help.aliyun.com/zh/cms/cloudmonitor-1-0/developer-reference/
- Alibaba Cloud DAS API: https://help.aliyun.com/zh/das/developer-reference/
