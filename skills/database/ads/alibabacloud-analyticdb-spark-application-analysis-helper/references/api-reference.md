# API Parameter Quick Reference

All APIs version `2021-12-01`, request method RPC style. CLI invocation **MUST** include `--api-version 2021-12-01`.

> ⚠️ **IMPORTANT: Parameter Naming Difference**
>
> - `describe-db-clusters` (RPC style) uses `--biz-region-id` for region specification
> - All other Spark commands (ROA style: `list-spark-apps`, `get-spark-app-info`, `get-spark-app-log`) use `--region`
>
> Do NOT mix them up. Using `--region` with `describe-db-clusters` will fail silently.

## Table of Contents

- [CLI Invocation Convention](#cli-invocation-convention)
- [Cluster Queries](#cluster-queries): describe-db-clusters
- [Spark Application Queries](#spark-application-queries): ListSparkApps, GetSparkAppInfo, GetSparkAppLog

---

## CLI Invocation Convention

The canonical form for every `aliyun adb` invocation — `--api-version`, the region flag (`--region` for Spark commands or `--biz-region-id` for `describe-db-clusters`), and `--user-agent` are all part of the standard template, not optional decorations. See [SKILL.md → CLI Invocation](../SKILL.md#cli-invocation) for the authoritative version of this template and the hard constraints behind it.

```bash
aliyun adb <action-name> \
  --region <region> \
  --api-version 2021-12-01 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper \
  [--param value ...]
```

- **API version**: `2021-12-01` — MUST be specified explicitly via `--api-version 2021-12-01` on every call. Omitting it falls back to the outdated `2019-03-15` version and causes failures.
- **Region flag**: Spark commands (`list-spark-apps`, `get-spark-app-info`, `get-spark-app-log`) use `--region <region-id>`. The cluster-discovery command `describe-db-clusters` uses `--biz-region-id <region-id>` instead. **Neither command accepts `--region-id`.**
- **Parameter naming**: API CamelCase → CLI lowercase-hyphenated (e.g., `DBClusterId` → `--db-cluster-id`, `AppId` → `--app-id`, `PageNumber` → `--page-number`).
- **User-Agent — HARD CONSTRAINT**: Every `aliyun adb` subcommand MUST carry `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper`. Setting it once via `aliyun configure ai-mode set-user-agent` does NOT exempt subsequent commands; the per-command flag is still required.
- **CLI reference portal**: https://api.aliyun.com/api-tools/cli/adb/2021-12-01

---

## Cluster Queries

### describe-db-clusters — Query ADB Cluster List (Plugin Mode)

**Description**: List AnalyticDB clusters in a specified region. Use this to discover the `DBClusterId` needed for Spark application queries. This command uses **plugin mode** (kebab-case parameters), same as Spark commands.

> **⚠️ MUST** include `--api-version 2021-12-01` on every call. Omitting it will cause the command to fail.

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --biz-region-id | String | Yes | Region ID (e.g., `cn-hangzhou`, `cn-beijing`, `cn-shanghai`) |
| --db-cluster-ids | String | No | Cluster ID filter; returns all clusters in the region if omitted |
| --db-cluster-status | String | No | Cluster status: Preparing, Creating, Running, Deleting, Restoring, ClassChanging |
| --db-cluster-version | String | No | 3.0 (data warehouse), 5.0 (default, includes lakehouse/enterprise/basic), All |
| --page-number | Integer | No | Page number, starting from 1 (default: 1) |
| ~~--page-size~~ | ~~Integer~~ | ~~No~~ | **⚠️ NOT SUPPORTED — server-side bug.** Passing any value causes `InvalidPageSize.Malformed` error. Fixed at 30 records per page. |
| --product-version | String | No | Product version: EnterpriseVersion or BasicVersion |
| --resource-group-id | String | No | Resource group ID |

**Key Response Fields**: `Items.DBCluster[]` (DBClusterId, DBClusterDescription, DBClusterStatus, RegionId, ComputeResource, StorageResource, PayType, CreateTime), `TotalCount`, `PageNumber`

**Key fields for cluster identification**:
- `DBClusterId` — Unique cluster ID (e.g., `amv-bp1xxxxxxxxx****`), required by all Spark app APIs
- `DBClusterDescription` — Human-readable cluster name
- `DBClusterStatus` — Current status (Running, Creating, etc.)
- `ComputeResource` / `StorageResource` — Resource specs (e.g., `16ACU`)

```bash
# List all clusters in a region
aliyun adb describe-db-clusters \
  --api-version 2021-12-01 \
  --biz-region-id cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper

# Filter by cluster status
aliyun adb describe-db-clusters \
  --api-version 2021-12-01 \
  --biz-region-id cn-hangzhou \
  --db-cluster-status Running \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper

# Query a specific cluster
aliyun adb describe-db-clusters \
  --api-version 2021-12-01 \
  --biz-region-id cn-hangzhou \
  --db-cluster-ids amv-bp1xxxxxxxxx**** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper
```

> **Note**: Both `describe-db-clusters` and Spark commands (e.g., `list-spark-apps`) now use plugin mode with kebab-case parameters and require `--api-version 2021-12-01`. The only notable difference is the region parameter: `--biz-region-id` for `describe-db-clusters` vs. `--region` for Spark commands. Additionally, `--page-size` is broken for `describe-db-clusters` (fixed at 30 per page) while Spark commands support it normally.

---

## Spark Application Queries

### ListSparkApps — Query Spark Application List

**Description**: List Spark applications in an ADB cluster, with optional filtering by time range, status, app name, etc.

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| DBClusterId | String | Yes | ADB cluster ID (e.g., `amv-bp1xxxxxxxxx****`) |
| Region | String | Yes | Region ID for API routing (e.g., `cn-beijing`, `cn-hangzhou`). CLI parameter: `--region` |
| ResourceGroupName | String | No | Job resource group name |
| PageNumber | Integer | Yes | Page number, starting from 1 |
| PageSize | Integer | No | Records per page: 10 (default), 50, or 100 |
| Filters | String (JSON) | No | Filter conditions in JSON format (see below) |

**Filters JSON Structure**:

```json
{
  "SubmittedTimeRange": { "Min": <timestamp_ms>, "Max": <timestamp_ms> },
  "TerminatedTimeRange": { "Min": <timestamp_ms>, "Max": <timestamp_ms> },
  "AppStates": ["SUBMITTED", "STARTING", "RUNNING", "SUCCEEDED", "FAILED", "KILLED", "COMPLETED"],
  "AppId": "<exact_app_id>",
  "AppNameRegex": "<regex_pattern>",
  "ResourceGroupName": "<resource_group>"
}
```

> **Note**: `ResourceGroupName` can be specified either as a top-level CLI parameter (`--resource-group-name`) or inside the `--filters` JSON. Both approaches are equivalent; using the top-level parameter is simpler for single-filter queries.

**Key Response Fields**: `Data.AppInfoList[]` (AppId, AppName, State, Priority, Message, Detail), `Data.PageNumber`, `Data.PageSize`, `Data.TotalCount`

**AppInfoList[].Detail fields**: AppType, DBClusterId, Data, DurationInMillis, ExecutionDurationInMillis, ResourceProvisioningDurationInMillis, SubmittedTimeInMillis, StartedTimeInMillis, TerminatedTimeInMillis, LastUpdatedTimeInMillis, LastAttemptId, LogRootPath, ResourceGroupName, WebUiAddress

```bash
# Basic query
aliyun adb list-spark-apps \
  --api-version 2021-12-01 \
  --region cn-hangzhou \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --page-number 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper

# With filters (e.g., failed apps only) — generate the filters JSON via scripts/search_filter_generator.py
aliyun adb list-spark-apps \
  --api-version 2021-12-01 \
  --region cn-hangzhou \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --page-number 1 \
  --page-size 50 \
  --filters '{"AppStates":["FAILED"],"AppNameRegex":"etl.*"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper
```

---

### GetSparkAppInfo — Query Spark Application Details

**Description**: Retrieve detailed information of a specific Spark application, including configuration, execution metrics, and runtime data.

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| AppId | String | Yes | Spark application ID (from ListSparkApps) |
| Region | String | Yes | Region ID (e.g., `cn-beijing`, `cn-hangzhou`) — required for routing |
| DBClusterId | String | No | ADB cluster ID (optional since AppId is globally unique) |

**Key Response Fields**: `Data` (AppId, AppName, State, Priority, Message, AppType, Detail)

**Data.Detail fields**: Data (JSON string of Spark job template), SubmittedTimeInMillis, StartedTimeInMillis, TerminatedTimeInMillis, LastUpdatedTimeInMillis, DurationInMillis, ExecutionDurationInMillis, ResourceProvisioningDurationInMillis, RunningStartTimeInMillis, DBClusterId, ResourceGroupName, WebUiAddress, LogRootPath, EstimateExecutionCpuTimeInSeconds, LastAttemptId

```bash
aliyun adb get-spark-app-info \
  --api-version 2021-12-01 \
  --app-id s202401011200xx1234ab000**** \
  --region cn-beijing \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper
```

---

### GetSparkAppLog — Query Spark Application Log

**Description**: Retrieve log content of a Spark application. Supports pagination and line-count limiting.

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| AppId | String | Yes | Spark application ID (from ListSparkApps) |
| Region | String | No | Region ID for API routing. CLI parameter: `--region`. Recommended for faster routing |
| DBClusterId | String | No | ADB cluster ID |
| LogLength | Long | No | Number of log lines to return, range: 1–500, default: 300 |
| PageNumber | Integer | No | Page number for log pagination |
| PageSize | Integer | No | Lines per page |

**Key Response Fields**: `Data` (LogContent, Message, DBClusterId, LogSize)

- `Data.LogContent` — Log text content (multi-line string)
- `Data.Message` — Warning message (e.g., log file deleted, resource insufficient); empty when no warning
- `Data.LogSize` — Total log size in bytes (0 means no valid log)

```bash
# Get latest 100 lines of log
aliyun adb get-spark-app-log \
  --api-version 2021-12-01 \
  --region cn-beijing \
  --app-id s202401011200xx1234ab000**** \
  --log-length 100 \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper

# Paginated log retrieval
aliyun adb get-spark-app-log \
  --api-version 2021-12-01 \
  --region cn-beijing \
  --app-id s202401011200xx1234ab000**** \
  --page-number 1 \
  --page-size 500 \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper
```

---

## Notes

1. **Timestamps**: All time fields in responses use millisecond-precision Unix timestamps (e.g., `1776407317233`). Convert to human-readable format for display.
2. **Pagination**: `ListSparkApps` returns paginated results. Check `Data.TotalCount` vs `PageNumber * PageSize` to determine if more pages exist.
3. **Log retention**: Application logs are retained for 30 days.
4. **App States**: Valid states include `SUBMITTED`, `STARTING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `KILLED`, `COMPLETED`.
5. **Rate limiting**: Default 100 requests/second per user. On `Throttling.User` error, wait 5–10 seconds before retry.
