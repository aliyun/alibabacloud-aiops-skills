---
name: alibabacloud-ebs-usage-summary
description: |
  Analyze Alibaba Cloud block storage (EBS) disk performance and fleet composition. Use it to locate performance bottlenecks (saturated IOPS or bandwidth), compare disks, instances, or availability zones to decide where to tune or resize, review disk count and capacity by category / region / billing type to inform capacity and cost decisions, check disk event history, and reach the right console dashboard for deeper drill-down.
  Triggers: "EBS monitoring", "disk metrics", "cloud disk performance", "IOPS analysis", "BPS analysis", "disk monitoring data", "export disk monitoring data", "export monitoring data", "metric aggregation", "resource overview", "EBS Lens", "CloudLens for EBS", "disk usage report", "capacity distribution", "event overview", "monitoring dashboard", "EBS dashboard", "storage dashboard", "disk monitoring dashboard", "storage health", "block storage insights", "disk observability", "disk inventory summary", "telemetry console", "block storage analytics".
---

# Alibaba Cloud EBS Disk Monitoring, Metric Analysis and Resource Overview

This skill enables you to:
1. **Answer disk performance questions** — how busy a disk is, whether it is hitting its IOPS/bandwidth ceiling, how it trends over time, and how it compares with other disks, instances, or availability zones (via `aliyun ebs describe-metric-data`).
2. **Answer fleet composition questions** — how many disks and how much capacity the account holds, how that splits across disk categories, regions, and billing types (both absolute and as percentages), and what disk events occurred (via `aliyun ebs get-report` / `aliyun ebs list-reports`, the same data set behind the EBS Lens Resource Overview console page).
3. **Point users at the right dashboard** — console URLs for CloudMonitor and CloudLens for EBS, optionally with a quick text summary so the user knows what to look at before clicking through.

## Scenario Description

### A. Disk Performance Metrics

Monitor and analyze cloud disk performance to track read/write IOPS and bandwidth (BPS), see how they trend over time, compare disks against each other, aggregate by disk type / instance / availability zone, and pinpoint bottlenecks and tuning opportunities.

### B. Resource Overview Reports (CloudLens for EBS)

Retrieve aggregated resource reports covering: overall disk usage, disk count and capacity broken down by category (`cloud_essd`, `cloud_essd_entry`, `cloud_auto`, `local_ssd_pro`…), by region, and by billing (pay) type — each available as absolute values and as percentage shares — plus a disk event summary with event counts by event name and by region.

> **[MUST] Scope limit — do not over-promise.** The 14 report cards this API returns are listed in [references/related-commands.md · Report Card Titles](references/related-commands.md). Encryption coverage, ESSD AutoPL adoption/burst usage, async replication pair count, dedicated block storage cluster count, and over-provisioned-disk detection are **not** among them. If the user asks for those, say the resource overview report does not expose them and point to the ECS console instead of inventing a figure.

### C. Monitoring Dashboard Quick View

Point the user at the right console dashboard — **CloudMonitor** for real-time metrics and alarm rules, **CloudLens for EBS** for resource overview, disk health analysis, and optimization recommendations — optionally with a quick text summary of the latest report, then guide them into the deeper scenarios (1–8).

**Architecture**: EBS Monitoring Service + Cloud Monitor + CloudLens for EBS + EBS Disks (System/Data Disks)

> **[MUST · PRODUCT CONSTRAINT] All metric data MUST be queried through `aliyun ebs describe-metric-data`.**
>
> - **FORBIDDEN**: `aliyun cms ...` (CloudMonitor, e.g. `DescribeMetricList`), `aliyun ecs ...`, or any other product as a substitute for retrieving disk metric values. They expose different metric names and dimensions and do **not** satisfy this skill's contract.
> - Resource overview data MUST come from the `ebs` product commands (`aliyun ebs get-report` / `aliyun ebs list-reports`) — never from CloudMonitor.
> - `aliyun ecs describe-disks` is permitted for **one purpose only**: resolving a disk reference to a disk ID — either filtering by a given disk name, or listing a region's disks when the user supplied no identifier (see the Pre-Step under Scenario 5). It must never be used to fetch metric values.
> - The CloudMonitor references in this document (including Scenario 9) denote **console navigation URLs for humans only** — they are *not* an API path. Providing a CloudMonitor console link is expected; calling a `cms` API is a workflow failure.

**Supported Metrics**: `disk_read_iops` / `disk_write_iops` (read/write IOPS), `disk_read_bps` / `disk_write_bps` (read/write bandwidth in bytes per second), `disk_iops_percent` / `disk_bps_percent` (IOPS and bandwidth utilization percentage — the two to use for saturation questions), `disk_read_block_size` / `disk_write_block_size` (average block size).

**Aggregation Capabilities**:
- **Time Dimension**: SUM, COUNT, AVG, MAX, MIN over time periods
- **Cross-Disk Dimension**: Aggregate metrics across multiple disks by SUM, AVG, COUNT, MAX, MIN
- **Grouping**: Group by DiskId, DeviceType, DeviceCategory, EcsInstanceId, or Availability Zone

**Supported Reports** (Resource Overview):

Each report card is a `Datas[]` element identified by `Title` (e.g. `disk_count_percent_by_category`) and wrapping a nested `Data[]` array; every `Data[]` entry is one series with `Labels` (a JSON **object**, e.g. `{"category": "cloud_essd"}`) and `DataPoints` (a `{unix_seconds: value}` map at daily granularity). The 14 available cards cover overall usage, plus disk count and capacity by category / region / pay type (absolute and percentage), plus event summary and event counts. Enumerate the account's real titles with `--cli-query "Datas[].Title"` rather than hard-coding card names — see [references/related-commands.md](references/related-commands.md) for the full title list, verified payload shape, and parsing recipes.

---

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**

> Run `aliyun version` to verify >= 3.3.3. If it is missing or too old, prefer a package manager (`brew install aliyun-cli`); otherwise follow `references/cli-installation-guide.md`, which installs into a user-writable directory.
>
> **[MUST] Installation safety:** never stream a remote script directly into a shell interpreter (that leaves no opportunity to inspect what will run) — download it, let the user review it, then run the local copy. Installing changes the user's machine, so **ask for confirmation first**, and never run privilege-elevating commands on the user's behalf.

**Pre-check: Aliyun CLI plugin update required**

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

---

## Prerequisites

> **[MUST] CloudLens for EBS must be enabled before using the Resource Overview feature.**
>
> 1. Log in to the [ECS Console](https://ecs.console.aliyun.com/) and open **Data Insights (EBS Lens) > Resource Overview** from the left-hand navigation.
> 2. If CloudLens for EBS has not been enabled, click the **Enable Now** button on that page.
> 3. After enabling, resource overview data takes approximately **10 minutes** to prepare. During this period, `get-report` will return an empty `Datas` array — this is NOT an error.
> 4. The region passed to the resource overview commands MUST be a region where CloudLens for EBS is enabled.
>
> Reference: [Introduction to Block Storage Data Insights](https://help.aliyun.com/zh/ecs/user-guide/what-is-a-piece-of-data-is-stored-insight/)

---

## Authentication

This skill relies on the Alibaba Cloud default credential chain. No explicit credential configuration is required within the skill session.

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

---

## RAM Policy

This skill requires the following Alibaba Cloud RAM permissions. See `references/ram-policies.md` for the complete permission policy.

**Required API Permissions** (POP action identifiers — the CLI itself is always invoked in plugin mode). All four are **read-only query actions**:
- `ebs:DescribeMetricData` — query disk monitoring metrics (`aliyun ebs describe-metric-data`)
- `ebs:GetReport` — retrieve a CloudLens for EBS resource overview report (`aliyun ebs get-report`)
- `ebs:ListReports` — list historical CloudLens for EBS resource overview reports (`aliyun ebs list-reports`)
- `ecs:DescribeDisks` — resolve a disk name to a disk ID, or list a region's disks when no identifier was given (`aliyun ecs describe-disks`; see the Scenario 5 Pre-Step — never used to fetch metric values)

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Parameter Confirmation

> **[MUST · MANDATORY GATE] Before executing any `aliyun ebs ...` command, output a parameter checklist** listing every user-customizable parameter you are about to use — including documented defaults, which must never be applied silently. Skipping the checklist is a workflow failure.
>
> Then choose one of two branches:
>
> - **Branch A — Interactive Confirmation** (default): ask the user to confirm or modify the checklist and **WAIT for an explicit reply** before any CLI command. Required when a parameter is missing/ambiguous, when the query is wide-scope (> 30 days or a whole region unfiltered), or when re-entering after a failure.
> - **Branch B — Unattended Auto-Proceed**: print the checklist as a notification and proceed without waiting. Allowed only when the input is fully specified, the user explicitly asked for auto-run, or no follow-up reply is possible (automated evaluation / CI).
>
> When branches conflict, **Branch A wins**.
>
> **[MUST] Ambiguity clarification is never skippable.** If a required parameter is missing or ambiguous, you MUST ask an explicit, separate, user-facing question that names each missing parameter, states the value you would assume and why, and invites correction — even in unattended runs (there, ask, then proceed on the stated assumptions and repeat the open questions in the final answer). Jumping straight to "parameters auto-locked" when a required parameter was never supplied is FORBIDDEN.
>
> **Full rule set — branch triggers B1-B3 / A1-A3, conflict carve-outs, and clarification phrasing: [references/parameter-confirmation.md](references/parameter-confirmation.md). Read it whenever the branch choice is not obvious.**

### Required and Optional Parameters

> **[MUST · plugin mode]** Every `aliyun ebs` command runs in **plugin mode**: lowercase-hyphenated command name and lowercase-hyphenated flags. Never use a PascalCase action name or PascalCase flags — the only PascalCase values that remain are **JSON payload keys** inside `--dimensions` (e.g. `DiskId`) and the POP action identifiers in `related_apis.yaml` / RAM policies.
>
> **The region flag is `--biz-region-id`, not `--region-id`** — the bare `--region` is a reserved CLI global flag for endpoint overrides. Treat `aliyun ebs <command> --help` as the authority over this document; if a command is rejected as unknown, the local plugin is stale — run `aliyun plugin update` and retry the same form.

| Command | Required | Key optional flags |
|---------|----------|--------------------|
| `describe-metric-data` | `--metric-name`, `--biz-region-id` | `--start-time` / `--end-time` (ISO 8601 UTC), `--period` (5/10/60/300/600/3600, default 5), `--dimensions` (JSON filter), `--aggre-ops` (`*_OVER_TIME`), `--aggre-over-line-ops` (`NON`/`SUM`/`AVG`/`COUNT`/`MAX`/`MIN`), `--group-by-labels` |
| `get-report` | `--biz-region-id` | `--report-type` (`present` default / `history`), `--app-name` (default `default`), `--report-id` (**required** when type is `history`) |
| `list-reports` | `--biz-region-id` (pass explicitly) | `--page-size` (10) / `--page-number` (1), `--app-id`, `--max-results` / `--next-token` |

Full parameter semantics, valid values, time-range limits per period, and response formats: [references/related-commands.md](references/related-commands.md).

---

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session, and use it wherever `<session-id>` appears below.

**Rule: every `aliyun` CLI command that calls a cloud API MUST include this flag** (local utility commands — `configure`, `plugin`, `version` — do not support it and are excluded):

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

Do not skip, alter the format, or omit it on any API invocation. The flag is accepted by the `ebs` plugin commands even though `--help` does not list it among the global flags (verified with `--cli-dry-run` on CLI 3.4.7). Use `--cli-dry-run` to inspect any command's assembled request without calling the API.

---

## Core Workflow

> **[MUST · ENTRY GATE]** The first step of every scenario below is the Parameter Confirmation gate: output the checklist, then either wait for confirmation (Branch A) or proceed with it as a notification (Branch B). The `# Confirm with user: ...` comment inside each Scenario is only a *reminder* of this gate — the gate itself is the explicit checklist output.
>
> **[MUST · RE-ENTRY GATE]** Any **2 consecutive** command failures (timeout, non-zero exit, gateway 5xx) MUST trigger the **Hard Stop** procedure in `references/error-handling.md §1` and re-enter the gate on Branch A — a 3rd silent retry without a user-facing Hard Stop message is a workflow failure.

### Placeholders in the Scenario Templates

> **[MUST] The commands below are templates, not literal commands.** Every `<...>` token is a value you derive per run — never send a placeholder, or a value copied from this document, to the API.
>
> - `<region-id>` — from the user's request; if absent, the CLI default profile region, which must be named in the clarification question
> - `<disk-id>` / `<instance-id>` — from the user's request, or resolved via the Scenario 5 Pre-Step (`describe-disks` returns both `DiskId` and `InstanceId`)
> - `<start-time>` / `<end-time>` — ISO 8601 UTC (`yyyy-MM-ddTHH:mm:ssZ`); compute relative windows ("last hour") from the current UTC time
> - `<period>` — the smallest granularity whose time-range limit covers the window
> - `<report-id>` — `HistoryReports[].ReportId` from a `list-reports` response (Scenario 7)
> - `<session-id>` — the session ID generated in `## Observability`
>
> The metric name, aggregation, and grouping in each template are likewise examples — substitute what the user actually asked for. Full placeholder table and per-period time-range limits: [references/related-commands.md](references/related-commands.md).

### Scenario 1: Query Single Disk Metrics

Query a per-disk metric (here read IOPS) for one disk over a bounded window:

```bash
# Confirm with user: region, disk ID, metric name, time range
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --start-time <start-time> \
  --end-time <end-time> \
  --period <period> \
  --dimensions "{\"DiskId\": [\"<disk-id>\"]}" \
  --biz-region-id <region-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

**Expected Output**: `TotalCount`, plus one `DataList[]` entry per matched series carrying `Labels` (the dimension values) and `Datapoints` (a JSON string mapping Unix seconds to metric values), and a `RequestId`. See [references/related-commands.md · Response Format](references/related-commands.md) for a full sample payload.

### Scenario 2: Query Multiple Disks with Aggregation

Aggregate a metric across a set of disks selected by dimension (here average write bandwidth over all data disks):

```bash
# Confirm with user: region, metric name, device type, aggregation method
aliyun ebs describe-metric-data \
  --metric-name disk_write_bps \
  --start-time <start-time> \
  --end-time <end-time> \
  --period <period> \
  --dimensions "{\"DeviceType\": [\"data\"]}" \
  --aggre-ops AVG_OVER_TIME \
  --aggre-over-line-ops AVG \
  --biz-region-id <region-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

> Swap `DeviceType` for any other dimension the user scoped the question to (`DiskId`, `DeviceCategory`, `EcsInstanceId`, `Azone`), and choose `--aggre-over-line-ops` to match the question: `AVG` for typical load, `MAX` for worst case, `SUM` for total throughput.

### Scenario 3: Group Metrics by Disk Category

Break a metric down by one label instead of collapsing it (here peak IOPS utilization per disk category):

```bash
# Confirm with user: region, metric name, grouping dimension
aliyun ebs describe-metric-data \
  --metric-name disk_iops_percent \
  --start-time <start-time> \
  --end-time <end-time> \
  --period <period> \
  --aggre-ops MAX_OVER_TIME \
  --group-by-labels DeviceCategory \
  --biz-region-id <region-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

### Scenario 4: Compare Performance Across Availability Zones

Same grouping mechanism applied to `Azone` to compare zones:

```bash
# Confirm with user: region, metric name, grouping by Azone
aliyun ebs describe-metric-data \
  --metric-name disk_bps_percent \
  --start-time <start-time> \
  --end-time <end-time> \
  --period <period> \
  --aggre-ops AVG_OVER_TIME \
  --aggre-over-line-ops AVG \
  --group-by-labels Azone \
  --biz-region-id <region-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

### Scenario 5: Multi-Dimension Filtering

Combine dimensions when the user scopes the question to specific disks **and** specific instances. Dimension values are AND-ed across keys and OR-ed within a key's array:

```bash
# Confirm with user: region, disk IDs, instance ID
aliyun ebs describe-metric-data \
  --metric-name disk_read_bps \
  --start-time <start-time> \
  --end-time <end-time> \
  --period <period> \
  --dimensions "{\"DiskId\": [\"<disk-id-1>\", \"<disk-id-2>\"], \"EcsInstanceId\": [\"<instance-id>\"]}" \
  --aggre-ops AVG_OVER_TIME \
  --biz-region-id <region-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

#### Pre-Step: Resolving a Disk Name to a Disk ID

`describe-metric-data` only accepts **disk IDs** in `--dimensions`, never disk names. When the user supplies a disk *name*, resolve it first via ECS:

```bash
# ECS disk queries also run in plugin mode — flags are lowercase-hyphenated
aliyun ecs describe-disks \
  --biz-region-id <region-id> \
  --disk-name <disk-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

> **[MUST]** Use `--biz-region-id` and `--disk-name`; any other casing or naming for these flags fails with `unknown flag`.
> Extract `Disks.Disk[].DiskId` from the response, then pass that ID into `--dimensions "{\"DiskId\": [\"<resolved-disk-id>\"]}"`.
> If the name matches zero disks, STOP and tell the user — do not guess or substitute a different disk. If it matches multiple, list them and ask which one (see the Ambiguity Clarification rule).

### Scenario 6: Get Latest Resource Overview Report (CloudLens for EBS)

Fetch the most recent weekly resource overview — same data as the EBS Lens Resource Overview console page.

```bash
# Confirm with user: region, report type, application name
aliyun ebs get-report \
  --biz-region-id <region-id> \
  --report-type present \
  --app-name default \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

Each `Datas[]` element is one console card, identified by `Title` and wrapping a nested `Data[]` array of series; each series has a `Labels` object naming its dimension value and a `DataPoints` map keyed by Unix seconds. To render the overview: iterate `Datas[]`, read `Title` to know which card you are on, then walk `Data[]`. **Series are sparse and end on different days** — quote each series' own newest point for "current value per label", but group by timestamp before adding series together, otherwise a percentage card will not total 100. Verified titles include `disk_count_percent_by_category` and `disk_size_percent_by_region`; enumerate the rest with `--cli-query "Datas[].Title"` instead of assuming.

### Scenario 7: List Historical Resource Overview Reports

List previously generated weekly reports (used to obtain a report ID for Scenario 8).

```bash
# Confirm with user: region, page size, page number
aliyun ebs list-reports \
  --biz-region-id <region-id> \
  --page-size 10 \
  --page-number 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

The response contains `HistoryReports[]` with `ReportId`, `ReportTime`, `SubscribePeriod`, and `ReportName` for each historical report. Substitute the page size / page number the user asked for.

### Scenario 8: Get a Specific Historical Resource Overview Report

Retrieve a specific historical report by its ID (obtained from Scenario 7 — never invented):

```bash
# Confirm with user: region, report ID
aliyun ebs get-report \
  --biz-region-id <region-id> \
  --report-type history \
  --report-id <report-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

The response shape is identical to Scenario 6.

### Scenario 9: Monitoring Dashboard Quick View

Provide the user with direct links to the EBS monitoring dashboards and an optional quick summary.

**Step 1 — Present console dashboard URLs:**

| Dashboard | URL | Description |
|-----------|-----|-------------|
| **CloudMonitor — EBS Monitoring** | `https://cloudmonitor.console.aliyun.com/` → navigate to **Product Monitoring > Block Storage** | Real-time monitoring metrics, alarm rules, and event monitoring for EBS disks |
| **ECS Console — EBS Lens Resource Overview** | `https://ecs.console.aliyun.com/` → navigate to **Data Insights (EBS Lens) > Resource Overview** | Resource overview report: disk count/capacity by category, region, and billing type, plus event overview. The console also surfaces figures the API does not return (e.g. encryption and AutoPL ratios) — send the user here for those |
| **ECS Console — EBS Lens Disk Analysis** | `https://ecs.console.aliyun.com/` → navigate to **Data Insights (EBS Lens) > Disk Analysis** | Per-disk performance analysis, health status, and optimization recommendations |

> **Note:** Console menu labels are localized to the console language, and URLs may vary by Alibaba Cloud region and account type. If a URL does not load, guide the user to navigate manually from the ECS or CloudMonitor console home page.

**Step 2 — (Optional) Retrieve a quick text summary:**

If the user wants a programmatic summary in addition to the dashboard links, retrieve the latest resource overview report by following **Scenario 6** (`get-report` with `--report-type present`). Present the key highlights:
- Overall disk usage (`total_disk_usage`)
- Disk count and capacity by category and by region
- Billing-type split (`disk_count_by_pay_type`)
- Event summary and event counts

**Step 3 — Guide to deeper analysis:**

Offer the user to drill deeper by referencing other scenarios:
- *"To query specific disk metrics (IOPS, BPS), see Scenarios 1–5."*
- *"To browse historical resource overview reports, see Scenarios 7–8."*

---

## Success Verification Method

After each call, verify: (1) `RequestId` is present; (2) `DataList` (or `Datas` for resource overview) contains the expected entries; (3) `Datapoints` timestamps fall inside the requested window; (4) values are in range (e.g. percentage metrics 0-100); (5) the `Warnings` array is empty or reviewed. Two audits are mandatory before delivering an answer:

- **[MUST] Cross-Check Report vs Raw Data — Business-Level Consistency Audit.** Before delivering any report, recompute every quantitative claim (counts, category breakdowns, aggregations, time alignment) against the raw API payload. Discrepancy = do NOT publish. See `references/verification-method.md · Cross-Check Audit` for the detailed checklist.
- **[MUST] Retry Discipline Audit — Mechanical Trace Check.** FAIL the run if the trace contains >= 3 consecutive `describe-metric-data` calls without the Hard Stop sentinel between call #2 and call #3. See `references/verification-method.md` for the full rule set.

---

## Cleanup

This skill only queries monitoring data and does not create any resources. No cleanup is required.

---

## Error Handling

> **[MUST · MANDATORY GATE] Error Handling is a HARD BLOCKER, not a suggestion.**
>
> Apply this section whenever a CLI invocation returns a non-zero exit, a timeout, or an API error code. **Silently retrying with mutated parameters is FORBIDDEN.** Every parameter change must be either driven by the rules below or re-confirmed with the user via the Parameter Confirmation gate.

### Quick Reference

| Error Category | Key Rule |
|----------------|----------|
| **CLI/API Timeout** | Max 2 retries with progressive backoff (reduce window + increase period). 3rd retry = **Hard Stop**. See `references/error-handling.md §1`. |
| **Time-Range Errors** | STOP. Surface error verbatim. Propose valid window. Wait for user approval. See `references/error-handling.md §2`. |
| **Permission Errors** | Follow RAM Policy → Permission Failure Handling flow. See `references/error-handling.md §3`. |
| **Throttling** | Wait 5s, retry once. If still throttled, surface to user. |
| **Resource Not Found** | Stop. Ask user to verify resource ID. Do not strip or guess. |
| **Empty Data** | Inform user; suggest widening filter. Do not retry blindly. |
| **Resource Overview / Parameter Errors** | See `references/error-handling.md §5` and the Troubleshooting Quick Reference in `references/related-commands.md` for the full error code tables (`InvalidParameter.MetricName`, `Period exceeds time range limit`, empty `Datas`, `MissingParameter: ReportId`, stale-plugin errors, etc.). |

For detailed error codes, retry tables, and the Hard Stop template, see [references/error-handling.md](references/error-handling.md).

---

## Best Practices

1. **Match period to window**: smaller periods (5s, 10s) for short-term drill-down, larger (300s, 3600s) for trends — always within the period's time-range limit (e.g. 5s supports max 12 hours).
2. **Filter before you aggregate**: `--dimensions` filters cut data volume and query time; use array values to batch multiple disks into one call instead of looping.
3. **Pick aggregation by intent**: AVG for typical load, MAX for peak/bottleneck detection, SUM for totals, COUNT for coverage.
4. **Group by the dimension that answers the question**: `DeviceCategory` to compare disk types, `Azone` for zone comparison, `EcsInstanceId` to attribute load to workloads.
5. **Treat timestamps as UTC+0** (ISO 8601) when converting to the user's local time in the final answer.
6. **Review `Warnings` and rate limits**: warnings may signal incomplete data; wide windows or many disks can hit API rate limits.

---

## Reference Links

| Reference File | Description |
|---------------|-------------|
| [references/ram-policies.md](references/ram-policies.md) | Complete RAM permission policy for EBS monitoring APIs |
| [references/related-commands.md](references/related-commands.md) | All EBS CLI commands, response formats, report card titles, troubleshooting table, and advanced usage (`--cli-query` / `jq` parsing) |
| [references/parameter-confirmation.md](references/parameter-confirmation.md) | Full Parameter Confirmation rule set: branch triggers B1-B3 / A1-A3, conflict resolution, clarification-question requirements |
| [references/verification-method.md](references/verification-method.md) | Detailed verification steps and commands |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Test patterns and acceptance criteria |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Alibaba Cloud CLI installation guide |
| [references/error-handling.md](references/error-handling.md) | Detailed error handling reference (timeout retry table, time-range errors, API error codes) |
