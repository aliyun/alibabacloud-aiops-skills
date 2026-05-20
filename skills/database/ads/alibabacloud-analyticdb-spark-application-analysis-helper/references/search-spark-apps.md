# Search Spark Applications Guide

Convert natural language descriptions into `aliyun adb list-spark-apps` CLI commands to query ADB Spark application lists, then format results as tables for display.

---

## 1. Cluster Discovery (When DBClusterId Not Specified)

When the user does not provide a `--db-cluster-id`, the Agent must first discover available clusters before proceeding with the search flow.

### 1.1 Trigger Condition

The Agent must initiate cluster discovery when:
- The user's request does not include a `--db-cluster-id` or `DBClusterId`
- The user asks about Spark applications without specifying which cluster

### 1.2 Prerequisite: biz-region-id

`--biz-region-id` is a required parameter for `describe-db-clusters`. If the user has not provided a region:
- Ask the user to specify a region (e.g., `cn-hangzhou`, `cn-shanghai`, `cn-beijing`)
- Common region IDs: `cn-hangzhou`, `cn-shanghai`, `cn-beijing`, `cn-shenzhen`, `ap-southeast-1`

### 1.3 Retrieve Cluster List

Use the `describe-db-clusters` command (plugin mode) to list available clusters:

```bash
aliyun adb describe-db-clusters \
  --api-version 2021-12-01 \
  --biz-region-id cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper
```

**Available Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--biz-region-id` | String | Yes | Region ID (e.g., `cn-beijing`, `cn-hangzhou`) |
| `--db-cluster-status` | String | No | Filter by status: `Running`, `Creating`, `Deleting`, etc. Recommended: use `Running` to skip non-active clusters |
| `--db-cluster-ids` | String | No | Cluster ID filter; returns all clusters if omitted |
| `--page-number` | Integer | No | Page number, starting from 1 (default: 1) |

**Pagination**: The response contains `TotalCount` and `PageNumber` fields. Each page returns a fixed 30 records (server default); `--page-size` is **NOT supported** — passing any value triggers an `InvalidPageSize.Malformed` server error. To navigate beyond the first 30 clusters, increment `--page-number` only.

> **⚠️ Important — Remaining Differences Between `describe-db-clusters` and Spark Commands**: Both commands now use plugin mode with kebab-case parameters and require `--api-version 2021-12-01`. However, a few differences remain:
>
> | | `describe-db-clusters` | Spark commands e.g. `list-spark-apps` |
> |---|---|---|
> | Parameter naming | kebab-case (e.g., `--biz-region-id`, `--db-cluster-status`) | kebab-case (e.g., `--db-cluster-id`, `--page-number`) |
> | `--api-version` | **MUST** include `--api-version 2021-12-01` | **MUST** include `--api-version 2021-12-01` |
> | Region parameter | `--biz-region-id` | `--region` (NOT `--region-id` or `--biz-region-id`) |
> | `--page-size` | **NOT supported** (fixed 30 per page; `InvalidPageSize.Malformed` error if set) | Supported: default 10, options 50, 100 |

The response contains `Items.DBCluster[]`, where each element includes:

| Field | Description |
|-------|-------------|
| `DBClusterId` | Cluster identifier (e.g., `amv-bp1xxxxxxxxx****`) |
| `DBClusterDescription` | Human-readable cluster description |
| `DBClusterStatus` | Cluster status (e.g., `Running`, `Creating`, `Deleting`) |
| `RegionId` | Region where the cluster resides |

### 1.4 Display Cluster List for Selection

Present the cluster list as a table and let the user select a target cluster:

```
| # | DBClusterId | DBClusterDescription | DBClusterStatus |
|---|-------------|----------------------|-----------------|
| 1 | amv-bp1xxxxxxxxx**** | Production Analytics Cluster | Running |
| 2 | amv-bp1yyyyyyyyy**** | Dev Test Cluster | Running |
| 3 | amv-bp1zzzzzzzzz**** | Staging Cluster | Creating |
```

Ask the user to:
- Select a cluster by number (e.g., "1" or "2")
- Or choose to **search across all clusters**

### 1.5 Search All Clusters Option

If the user chooses to search across all clusters:

1. **Warn about time cost**: Remind the user that searching across all clusters sequentially will take significantly longer than a single-cluster search.
2. **Get user confirmation**: Only proceed after the user explicitly confirms.
3. **Iterate over Running clusters**: Use `--db-cluster-status Running` to directly filter for active clusters, then for each returned cluster, execute the normal search flow (`list-spark-apps`):

```bash
aliyun adb describe-db-clusters \
  --api-version 2021-12-01 \
  --biz-region-id cn-hangzhou \
  --db-cluster-status Running \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper
```

This avoids fetching non-active clusters (e.g., `Creating`, `Deleting`) and reduces the result set to only clusters that can run Spark applications.
4. **Merge and display results**: Combine results from all clusters into a single table with an additional `ClusterId` column to distinguish the source:

```
| ClusterId | AppId | AppName | State | SubmittedTime | Duration | ResourceGroup |
|-----------|-------|---------|-------|---------------|----------|---------------|
| amv-bp1xxxxxxxxx**** | s202401011200xx1234ab000**** | etl_daily_job | [❌ FAILED] | 2024-01-15 10:00:00 | 15m 32s | default |
| amv-bp1yyyyyyyyy**** | s202401011300xx5678cd000**** | sync_orders | [✅ SUCCEEDED] | 2024-01-15 11:00:00 | 5m 10s | spark_rg |
```

### 1.6 Flow Diagram

```
User request (no ClusterId)
  → Ask biz-region-id (if not provided)
  → describe-db-clusters
  → Display cluster list
  → User selects one cluster / "all clusters"
  → If single: proceed with normal search flow
  → If all: warn about time cost → confirm → iterate all Running clusters → merge results
```

---

## 2. Natural Language Intent Recognition

The Agent must extract the following filter dimensions from user descriptions and map them to `--filters` JSON fields:

| Dimension | Natural Language Example | filters Field | Value Mapping |
|-----------|-------------------------|---------------|---------------|
| Application State | "failed jobs", "running", "succeeded" | `AppStates` | Array, e.g., `["FAILED"]`, `["RUNNING"]` |
| Time Range | "last hour", "yesterday", "last Friday to this Monday" | `SubmittedTimeRange` / `TerminatedTimeRange` | `{ "Min": <ms>, "Max": <ms> }` |
| Application Name | "ETL-related jobs" | `AppNameRegex` | Regex string, e.g., `"etl.*"` |
| Resource Group | "jobs in default resource group" | `ResourceGroupName` | String, e.g., `"default"` |
| Application ID | "the job app-xxx" | `AppId` | Exact match string |

### 2.1 Application State Mapping

Supported state values (the `AppStates` array may contain multiple):

| State Value | Meaning | Common Natural Language |
|-------------|---------|------------------------|
| `SUBMITTED` | Submitted | "just submitted", "queued" |
| `STARTING` | Starting | "starting up", "launching" |
| `RUNNING` | Running | "running", "in progress" |
| `SUCCEEDED` | Succeeded | "successful", "completed normally" |
| `FAILED` | Failed | "failed", "errored out", "crashed" |
| `KILLED` | Killed | "killed", "terminated" |
| `COMPLETED` | Completed | "finished" (includes both succeeded and failed) |

**Examples**:
- "Show failed and killed jobs" → `"AppStates": ["FAILED", "KILLED"]`
- "Currently running tasks" → `"AppStates": ["RUNNING"]`

### 2.2 Time Range Mapping

Time ranges are converted to millisecond timestamps and placed in `SubmittedTimeRange` (by submission time) or `TerminatedTimeRange` (by termination time):

| Natural Language | Conversion Logic |
|-----------------|-----------------|
| "last N hours" | `Min = now - N * 3600 * 1000`, `Max = now` |
| "yesterday" | `Min = yesterday 00:00:00`, `Max = yesterday 23:59:59.999` |
| "last Friday to this Monday" | `Min = last Friday 00:00:00`, `Max = this Monday 23:59:59.999` |
| "last 30 minutes" | `Min = now - 30 * 60 * 1000`, `Max = now` |

> **Note**: All timestamps use millisecond-precision Unix timestamps (e.g., `1776407317233`).

### 2.3 Application Name Mapping

`AppNameRegex` uses regex pattern matching. The Agent must convert user descriptions into reasonable regex patterns:

| Natural Language | AppNameRegex Value |
|-----------------|-------------------|
| "ETL-related jobs" | `"etl.*"` or `".*etl.*"` |
| "name contains daily" | `".*daily.*"` |
| "starts with sync" | `"sync.*"` |

### 2.4 Resource Group Mapping

`ResourceGroupName` performs exact match on resource group name:

| Natural Language | ResourceGroupName Value |
|-----------------|------------------------|
| "jobs in default resource group" | `"default"` |
| "spark_rg resource group" | `"spark_rg"` |

### 2.5 Application ID Mapping

`AppId` performs exact match on application ID. Use this when the user mentions a specific job ID:

| Natural Language | AppId Value |
|-----------------|------------|
| "the job app-xxx" | `"app-xxx"` |
| "the application s202401011200xx1234ab000****" | `"s202401011200xx1234ab000****"` |

---

## 3. Parameter Construction Flow

The `--filters` parameter requires a JSON string. **The Agent MUST use [scripts/search_filter_generator.py](../scripts/search_filter_generator.py) to generate this JSON.** Hand-rolling the JSON (manual concatenation, inline `json.dumps`, ad-hoc Python snippets) is **forbidden** because it has repeatedly resulted in dropped filter dimensions — e.g., `AppStates` or `ResourceGroupName` silently omitted even when the user explicitly mentioned them in natural language.

### 3.1 Flow Overview

```
User natural language
  → Agent extracts ALL filter dimensions mentioned (see §2)
  → Agent runs scripts/search_filter_generator.py with one flag per dimension
  → Agent prints the generated JSON and verifies every mentioned dimension is a key
  → Agent embeds the verified JSON into the list-spark-apps CLI invocation
```

### 3.2 [MANDATORY] Filter Dimension Completeness Self-Check

Before invoking `list-spark-apps`, run through this checklist. If the user mentioned a dimension in any form (English, Chinese, regex, ID), it MUST be encoded into the generated JSON. Silent omission is a defect even when the resulting rows happen to look correct (which can happen when server-side data is homogeneous — see the cautionary tale at the end of this section).

| # | Dimension | Filters JSON Key | Generator flag | Trigger phrases (examples, not exhaustive) |
|---|---|---|---|---|
| 1 | Time range | `SubmittedTimeRange` / `TerminatedTimeRange` | `--last-hours`, `--last-minutes`, `--yesterday`, `--start-date`/`--end-date`, `--time-type` | "last hour", "yesterday", "this week", "from X to Y", "近1小时", "昨天" |
| 2 | Application state | `AppStates` | `--app-states` | "failed", "running", "succeeded", "killed", "失败", "运行中", "已完成" |
| 3 | Application name pattern | `AppNameRegex` | `--app-name-regex` | "ETL jobs", "name contains", "starts with", "名称包含", "ETL相关" |
| 4 | Resource group | `ResourceGroupName` | `--resource-group-name` | "in default RG", "spark_rg jobs", "serverless资源组", "默认资源组" |
| 5 | Specific application ID | `AppId` | `--app-id` | "the job s2026...", "AppId xxx" |

**Self-check protocol**:

1. Re-read the user's prompt and **list every filter dimension they mentioned**, in your reasoning trace.
2. Build the corresponding `python scripts/search_filter_generator.py ...` command with one flag per mentioned dimension.
3. Run the script and **print the generated JSON**.
4. **Verify, dimension by dimension**, that every mentioned dimension appears as a key in the JSON. If any is missing, regenerate before proceeding.
5. Only after the JSON is verified complete, embed it in the `aliyun adb list-spark-apps` invocation alongside `--user-agent` and `--api-version`.

> **Cautionary tale**: A request like *"yesterday's failed daily_etl jobs in serverless resource group"* contains FOUR dimensions (time, state, name regex, resource group). A `--filters` value carrying only `SubmittedTimeRange` and `AppNameRegex` is incomplete. If the cluster happens to contain only failed serverless jobs that day, the returned rows will look correct — but the filter is wrong and will silently mislead users on a different dataset, on a different day, or in a different cluster.

### 3.3 Generator Usage

The project provides [scripts/search_filter_generator.py](../scripts/search_filter_generator.py), which generates a usable JSON string directly via command-line arguments:

```bash
# Generate filters JSON for failed jobs in the last 1 hour
python scripts/search_filter_generator.py \
  --app-states FAILED \
  --last-hours 1

# Generate filters JSON with time range, app name regex, and resource group
python scripts/search_filter_generator.py \
  --app-states FAILED RUNNING \
  --last-hours 24 \
  --app-name-regex "etl.*" \
  --resource-group-name "default"

# Generate filters JSON for failed jobs that terminated yesterday
python scripts/search_filter_generator.py \
  --app-states FAILED \
  --yesterday \
  --time-type terminated

# Generate filters JSON for a specific AppId
python scripts/search_filter_generator.py \
  --app-id s202401011200xx1234ab000****

# Generate filters JSON with custom date range
python scripts/search_filter_generator.py \
  --app-states FAILED \
  --start-date 2024-01-01 \
  --end-date 2024-01-31
```

The script outputs a compact JSON string (no extra whitespace) that can be directly used as the value of the `--filters` parameter. Add `--pretty` flag for human-readable output.

**Supported arguments**:

| Argument | Description |
|----------|-------------|
| `--app-states` | One or more states: SUBMITTED, STARTING, RUNNING, SUCCEEDED, FAILED, KILLED, COMPLETED |
| `--last-hours N` | Look back N hours from now |
| `--last-minutes N` | Look back N minutes from now |
| `--yesterday` | Set time range to yesterday |
| `--start-date YYYY-MM-DD` | Start date (inclusive) |
| `--end-date YYYY-MM-DD` | End date (inclusive) |
| `--time-type` | `submitted` (default) or `terminated` — which time range field to populate |
| `--app-name-regex` | Regex pattern for application name matching |
| `--resource-group-name` | Exact resource group name |
| `--app-id` | Exact application ID |
| `--pretty` | Pretty-print JSON output |

### 3.4 Output Format

The script outputs a compact single-line JSON string by default — pass it directly as the value of `--filters`, wrapped in single quotes to avoid shell escaping issues. Example:

```
{"SubmittedTimeRange":{"Min":1776403717233,"Max":1776407317233},"AppStates":["FAILED"],"AppNameRegex":"etl.*","ResourceGroupName":"default"}
```

Add `--pretty` only for human inspection during the self-check; do NOT pass pretty-printed output to the CLI.

> **Why hand-written JSON is forbidden**: Embedding `json.dumps` snippets or string-concatenation in the agent's reasoning trace bypasses the structured `--app-states`, `--resource-group-name`, etc. flags, which are the very mechanism that forces dimension completeness. The script is the choke point — every requested dimension corresponds to exactly one flag, so missing flags are visible at the command line before the API is called.

---

## 4. CLI Invocation Examples

All examples use plugin mode (kebab-case parameters). Every command **MUST** include `--api-version 2021-12-01` (the CLI defaults to the outdated 2019-03-15 version, which causes command failures). Every command **must** include the `--user-agent` parameter.

### 4.1 Basic Query (Cluster ID Only)

```bash
aliyun adb list-spark-apps \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --region cn-hangzhou \
  --api-version 2021-12-01 \
  --page-number 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper
```

### 4.2 Query with State Filter

```bash
# Query failed applications
aliyun adb list-spark-apps \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --region cn-hangzhou \
  --api-version 2021-12-01 \
  --page-number 1 \
  --page-size 50 \
  --filters '{"AppStates":["FAILED"]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper

# Query running and starting applications
aliyun adb list-spark-apps \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --region cn-hangzhou \
  --api-version 2021-12-01 \
  --page-number 1 \
  --filters '{"AppStates":["RUNNING","STARTING"]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper
```

### 4.3 Query with Time Range

```bash
# Query applications submitted in the last 1 hour (timestamps generated by Python script)
aliyun adb list-spark-apps \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --region cn-hangzhou \
  --api-version 2021-12-01 \
  --page-number 1 \
  --page-size 50 \
  --filters '{"SubmittedTimeRange":{"Min":1776403717233,"Max":1776407317233}}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper

# Query failed applications that terminated yesterday
aliyun adb list-spark-apps \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --region cn-hangzhou \
  --api-version 2021-12-01 \
  --page-number 1 \
  --page-size 50 \
  --filters '{"TerminatedTimeRange":{"Min":1776310400000,"Max":1776396799999},"AppStates":["FAILED"]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper
```

### 4.4 Combined Conditions Query

```bash
# Query failed jobs in the last 24 hours, in default resource group, with name matching etl.*
aliyun adb list-spark-apps \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --region cn-hangzhou \
  --api-version 2021-12-01 \
  --page-number 1 \
  --page-size 50 \
  --filters '{"SubmittedTimeRange":{"Min":1776321117233,"Max":1776407317233},"AppStates":["FAILED"],"AppNameRegex":"etl.*","ResourceGroupName":"default"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper

# Query a specific AppId
aliyun adb list-spark-apps \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --region cn-hangzhou \
  --api-version 2021-12-01 \
  --page-number 1 \
  --filters '{"AppId":"s202401011200xx1234ab000****"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper
```

### 4.5 Query by Resource Group

```bash
aliyun adb list-spark-apps \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --region cn-hangzhou \
  --api-version 2021-12-01 \
  --page-number 1 \
  --resource-group-name default \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper
```

---

## 5. Result Display Format

After the CLI returns JSON, extract key fields from `Data.AppInfoList[]` and format them as a standard table.

### 5.1 Standard Table Format

| AppId | AppName | State | SubmittedTime | Duration | ResourceGroup |
|-------|---------|-------|---------------|----------|---------------|

### 5.2 Field Extraction and Conversion Rules

| Table Field | JSON Path | Conversion Rule |
|-------------|-----------|-----------------|
| AppId | `AppId` | Display as-is |
| AppName | `AppName` | Display as-is |
| State | `State` | Display as-is, optionally with state badge (see table below) |
| SubmittedTime | `Detail.SubmittedTimeInMillis` | Millisecond timestamp → `YYYY-MM-DD HH:MM:SS` |
| Duration | `Detail.DurationInMillis` | Milliseconds → human-readable format |
| ResourceGroup | `Detail.ResourceGroupName` | Display as-is |

### 5.3 State Badges

| State | Badge |
|-------|-------|
| SUBMITTED | `[⏳ SUBMITTED]` |
| STARTING | `[🔄 STARTING]` |
| RUNNING | `[▶️ RUNNING]` |
| SUCCEEDED | `[✅ SUCCEEDED]` |
| FAILED | `[❌ FAILED]` |
| KILLED | `[⛔ KILLED]` |
| COMPLETED | `[✔️ COMPLETED]` |

### 5.4 Duration Conversion Example

Convert `Detail.DurationInMillis` (milliseconds) to human-readable format:

```
3661500 ms → "1h 1m 1s"
   90000 ms → "1m 30s"
    5000 ms → "5s"
```

Conversion logic (Python):

```python
def format_duration(ms):
    if ms is None or ms <= 0:
        return "-"
    seconds = ms // 1000
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)
```

### 5.5 Timestamp Conversion Example

Convert `Detail.SubmittedTimeInMillis` (millisecond timestamp) to readable format:

```python
import datetime

def format_timestamp(ms):
    if ms is None or ms <= 0:
        return "-"
    dt = datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S")
```

### 5.6 Display Example

```
| AppId | AppName | State | SubmittedTime | Duration | ResourceGroup |
|-------|---------|-------|---------------|----------|---------------|
| s202401011200xx1234ab000**** | etl_daily_job | [❌ FAILED] | 2024-01-15 10:00:00 | 15m 32s | default |
| s202401011300xx5678cd000**** | sync_orders | [✅ SUCCEEDED] | 2024-01-15 11:00:00 | 5m 10s | spark_rg |
| s202401011400xx9012ef000**** | etl_hourly | [▶️ RUNNING] | 2024-01-15 12:00:00 | 3m 5s | default |
```

---

## 6. Pagination Handling

`list-spark-apps` returns paginated results. Correct pagination logic is required.

### 6.1 Pagination Parameters

| Parameter | Description |
|-----------|-------------|
| `--page-number` | Page number, starting from `1` |
| `--page-size` | Records per page, default `10`, options `50` or `100` |

### 6.2 Detecting the Last Page

Compare the number of items in `Data.AppInfoList` with `--page-size`:

- **Returned count < page-size**: Last page reached
- **Returned count = page-size**: More pages may exist, continue querying

Alternatively, use `Data.TotalCount` to calculate total pages: `total_pages = ceil(TotalCount / PageSize)`

### 6.3 Pagination Query Flow

1. First query: `--page-number 1 --page-size 50`
2. Check the number of items in the returned `AppInfoList`:
   - If < 50, this is the last page; stop querying
   - If = 50, continue to the next page
3. Increment `--page-number` and repeat step 2
4. Merge all page results and format the combined output

### 6.4 Querying All Results

When the user requests "all" applications or the result set is large, query page by page until the last page:

```bash
# Page 1
aliyun adb list-spark-apps \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --region cn-hangzhou \
  --api-version 2021-12-01 \
  --page-number 1 \
  --page-size 100 \
  --filters '{"AppStates":["FAILED"]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper

# If 100 items returned, query page 2
aliyun adb list-spark-apps \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --region cn-hangzhou \
  --api-version 2021-12-01 \
  --page-number 2 \
  --page-size 100 \
  --filters '{"AppStates":["FAILED"]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper

# Continue until returned count < 100
```

> **Note**: When paginating, keep the same `--filters` condition across all pages to avoid inconsistent results.
