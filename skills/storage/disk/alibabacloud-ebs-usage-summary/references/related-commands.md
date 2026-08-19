# EBS Monitoring CLI Commands Reference

Complete reference for all CLI commands used in the Alibaba Cloud EBS monitoring skill.

## Command Overview

All commands use **plugin mode**: the command name and every flag are lowercase-hyphenated (e.g. `aliyun ebs get-report --biz-region-id cn-hangzhou`).

> **Region flag:** every `ebs` command takes the region as `--biz-region-id`, **not** `--region-id` — the bare `--region` is a reserved CLI global flag for endpoint overrides. Verified against `aliyun ebs get-report --help` (CLI 3.4.7). Treat `aliyun ebs <command> --help` as the authority whenever a flag name is in doubt.

| Command | Underlying API Action | Description |
|---------|----------------------|-------------|
| `aliyun ebs describe-metric-data` | `DescribeMetricData` | Query disk monitoring metrics |
| `aliyun ebs get-report` | `GetReport` | Get CloudLens for EBS resource overview report |
| `aliyun ebs list-reports` | `ListReports` | List historical resource overview reports |

> The API action names in the middle column are POP action identifiers (used in `related_apis.yaml` and RAM policy statements). They are **not** CLI command names — always invoke the lowercase-hyphenated form. A `--cli-dry-run` on `get-report` shows the mapping explicitly: `API Action: GetReport`, `Style: RPC`, with the `--biz-region-id` value sent as `{"RegionId": "<region-id>"}` in the request body.

> **`--user-agent` is accepted** on these commands even though `--help` does not list it among the global flags — verified with `--cli-dry-run` on CLI 3.4.7 (the request was built without an `unknown flag` error). Keep passing it as required by SKILL.md · Observability.

### Placeholder Conventions

Every `<...>` token below is a value you must supply from the user's request or resolve from a prior call:

| Placeholder | How to obtain it |
|-------------|------------------|
| `<region-id>` | From the user's request; otherwise the CLI default profile region (confirm with the user) |
| `<disk-id>` | From the user's request, or resolved from a disk name via `aliyun ecs describe-disks` |
| `<instance-id>` | From the user's request, or the `InstanceId` field returned by `aliyun ecs describe-disks` |
| `<report-id>` | From the `HistoryReports[].ReportId` field of a `list-reports` response |
| `<start-time>` / `<end-time>` | ISO 8601 UTC (`yyyy-MM-ddTHH:mm:ssZ`), derived from the user's requested window |
| `<session-id>` | The 32-char hex session ID generated once per session (see SKILL.md · Observability) |

---

## 1. describe-metric-data (Plugin Mode)

Query disk performance metrics including IOPS, BPS, and bandwidth utilization.

### Syntax

```bash
aliyun ebs describe-metric-data \
  --metric-name <metric> \
  --biz-region-id <region> \
  [--start-time <iso8601>] \
  [--end-time <iso8601>] \
  [--period <seconds>] \
  [--dimensions <json>] \
  [--aggre-ops <method>] \
  [--aggre-over-line-ops <method>] \
  [--group-by-labels <label>] \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

### Parameters

| Parameter | Required | Description | Valid Values |
|-----------|----------|-------------|--------------|
| `--metric-name` | **Yes** | Metric to query | `disk_bps_percent`, `disk_iops_percent`, `disk_read_block_size`, `disk_read_bps`, `disk_read_iops`, `disk_write_block_size`, `disk_write_bps`, `disk_write_iops` |
| `--biz-region-id` | **Yes** | Region ID | e.g., `cn-hangzhou`, `cn-shanghai`, `cn-beijing` |
| `--start-time` | No | Query start time (ISO 8601) | Format: `yyyy-MM-ddTHH:mm:ssZ` |
| `--end-time` | No | Query end time (ISO 8601) | Format: `yyyy-MM-ddTHH:mm:ssZ` |
| `--period` | No | Data granularity in seconds | `5`, `10`, `60`, `300`, `600`, `3600` |
| `--dimensions` | No | JSON filter for dimensions | JSON object with array values |
| `--aggre-ops` | No | Time aggregation method | `AVG_OVER_TIME`, `SUM_OVER_TIME`, `MAX_OVER_TIME`, `MIN_OVER_TIME`, `COUNT_OVER_TIME` |
| `--aggre-over-line-ops` | No | Cross-disk aggregation | `NON`, `SUM`, `AVG`, `COUNT`, `MAX`, `MIN` |
| `--group-by-labels` | No | Group by dimension labels | `DiskId`, `DeviceType`, `DeviceCategory`, `EcsInstanceId`, `Azone` |

### Dimension Filters

The `--dimensions` parameter accepts a JSON object with array values. Keys are AND-ed, values inside one key are OR-ed. Substitute the identifiers resolved for the current request:

```json
{
  "DiskId": ["<disk-id>"],
  "DeviceType": ["data", "system"],
  "DeviceCategory": ["cloud_essd", "cloud_essd_entry"],
  "EcsInstanceId": ["<instance-id>"],
  "Azone": ["<zone-id-1>", "<zone-id-2>"]
}
```

### Time Range Limits by Period

| Period | Max Time Range |
|--------|----------------|
| 5 seconds | 12 hours |
| 10 seconds | 24 hours |
| 60 seconds | 7 days |
| 300 seconds | 30 days |
| 600 seconds | 30 days |
| 3600 seconds | 30 days |

### Response Format

```json
{
  "TotalCount": 1,
  "DataList": [
    {
      "Labels": "{\"DiskId\": \"d-bp1234567890abcde\"}",
      "Datapoints": "{\"1705315200\": 150, \"1705315260\": 148, ...}"
    }
  ],
  "RequestId": "11B55F58-D3A4-4A9B-9596-342420D0****",
  "Warnings": []
}
```

- `TotalCount`: Number of result entries
- `DataList`: Array of metric data points
  - `Labels`: dimension key-value pairs
  - `Datapoints`: timestamp-to-value mapping (Unix seconds)
- `RequestId`: Unique request identifier
- `Warnings`: Array of warning messages (empty if no warnings)

> **Partially verified.** A live call confirmed the top-level keys `DataList`, `TotalCount`, and `RequestId`. The query returned `"DataList": []` with `"TotalCount": 0`, so the **inner types of `Labels` and `Datapoints` are still unconfirmed** — this document shows them as JSON-encoded strings (inherited from earlier revisions), but the sibling `get-report` API turned out to use real objects instead. Before parsing, check which form you actually received:
>
> ```bash
> ... | jq '.DataList[0] | {labels_type: (.Labels | type), datapoints_type: (.Datapoints | type)}'
> ```
>
> If the type is `"string"`, pipe through `fromjson`; if it is `"object"`, use it directly.
>
> An empty `DataList` with a valid `RequestId` is not an error — it means no series matched the filter or window. Inform the user and suggest widening the dimension filter or the time range; do not retry blindly with the same parameters.

---

## 2. get-report (Plugin Mode)

Retrieve CloudLens for EBS resource overview reports.

> **IMPORTANT**: If the command is rejected as an unknown API, the local plugin is stale — run `aliyun plugin update` and retry before considering any alternative invocation form.
>
> Flag list verified against `aliyun ebs get-report --help` (CLI 3.4.7): `--biz-region-id` (required), `--report-type`, `--app-name`, `--report-id`.

### Syntax

```bash
aliyun ebs get-report \
  --biz-region-id <region-id> \
  [--report-type <present|history>] \
  [--app-name <app-name>] \
  [--report-id <report-id>] \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

### Parameters

| Parameter | Required | Description | Valid Values |
|-----------|----------|-------------|--------------|
| `--biz-region-id` | **Yes** | Region ID (must have CloudLens for EBS enabled) | e.g., `cn-hangzhou` |
| `--report-type` | No | Report type to retrieve | `present` (latest), `history` (specific) |
| `--app-name` | No | Application name (only effective when report type is `present`) | Default: `default` |
| `--report-id` | When report type is `history` | Historical report ID | Obtained from `list-reports` |

### Response Format (Latest Report — `--report-type present`)

Verified against a live `aliyun ebs get-report --biz-region-id cn-hangzhou --report-type present` call (CLI 3.4.7). **Each `Datas[]` element carries a `Title` plus a nested `Data[]` array** — the series live one level deeper than a naive reading suggests:

```json
{
  "Datas": [
    {
      "Data": [
        {
          "DataPoints": {
            "1786550400": 1.92,
            "1786636800": 1.79,
            "1786896000": 1.89,
            "1786982400": 2.27
          },
          "Labels": { "category": "local_ssd_pro" }
        },
        {
          "DataPoints": {
            "1786550400": 38.46,
            "1786636800": 41.07,
            "1786723200": 36.17
          },
          "Labels": { "category": "cloud_auto" }
        },
        {
          "DataPoints": {
            "1786550400": 57.69,
            "1786636800": 55.36,
            "1786723200": 61.7
          },
          "Labels": { "category": "cloud_essd" }
        },
        {
          "DataPoints": {
            "1786550400": 1.92,
            "1786636800": 1.79,
            "1786723200": 2.13
          },
          "Labels": { "category": "cloud_essd_entry" }
        }
      ],
      "Title": "disk_count_percent_by_category"
    },
    {
      "Data": [
        {
          "DataPoints": { "1786550400": 21.99, "1786636800": 22.17 },
          "Labels": { "region_id": "cn-chengdu" }
        },
        {
          "DataPoints": { "1786550400": 2.5, "1786636800": 2.52 },
          "Labels": { "region_id": "cn-hangzhou" }
        }
      ],
      "Title": "disk_size_percent_by_region"
    }
  ],
  "RequestId": "01A017F4-2BE0-5BE7-AD7C-11727053396C"
}
```

**Confirmed facts — do not assume otherwise:**

| Aspect | Reality |
|--------|---------|
| Card identity | `Datas[].Title` — a plain string, emitted **after** the `Data` array in each element |
| Series location | `Datas[].Data[]`, **not** `Datas[]` directly |
| `Labels` type | A real **JSON object** (e.g. `{"category": "cloud_essd"}`) — not a JSON-encoded string, so no second parse is needed |
| `Labels` keys | Lowercase snake_case dimension names. Observed: `category` (`cloud_essd`, `cloud_essd_entry`, `cloud_auto`, `local_ssd_pro`) and `region_id` (`cn-hangzhou`, `cn-chengdu`) |
| `DataPoints` keys | **Unix seconds** (10 digits, e.g. `1786550400`), daily granularity (86400 s apart) — not milliseconds |
| Sparse series | Series within one card cover **different timestamp sets** and may end on different days (the `local_ssd_pro` series above stops two days before `cloud_essd`). Group by timestamp before comparing or summing series — never by array position or per-series latest value |
| `RequestId` | Present at the **top level**, emitted after `Datas` |
| `*_percent` cards | Series values **at one shared timestamp** sum to ~100 (verified across all 7 days of `disk_count_percent_by_category`: 99.99-100.01). Summing each series' own latest value instead gives a wrong total |

### Response Format (Historical Report — `--report-type history`)

Same structure as above, with data from the specified historical report.

### Report Card Titles

The complete title list, enumerated from a live report via `--cli-query "Datas[].Title"` (CLI 3.4.7, `cn-hangzhou`) — **14 cards**:

| `Title` | `Labels` key | Description |
|---------|--------------|-------------|
| `total_disk_usage` | not inspected | Overall disk usage summary |
| `disk_count_by_category` | ✅ `category` | Disk count per disk category |
| `disk_count_percent_by_category` | ✅ `category` | Disk count share (%) per category |
| `disk_size_by_category` | ✅ `category` (assumed) | Capacity per category |
| `disk_size_percent_by_category` | ✅ `category` (assumed) | Capacity share (%) per category |
| `disk_count_by_region` | ✅ `region_id` (assumed) | Disk count per region |
| `disk_count_percent_by_region` | ✅ `region_id` (assumed) | Disk count share (%) per region |
| `disk_size_by_region` | ✅ `region_id` (assumed) | Capacity per region |
| `disk_size_percent_by_region` | ✅ `region_id` | Capacity share (%) per region |
| `disk_count_by_pay_type` | not inspected | Disk count per billing type |
| `disk_count_percent_by_pay_type` | not inspected | Disk count share (%) per billing type |
| `event_summary` | not inspected | Disk event summary |
| `disk_event_count_by_event_name` | not inspected | Event count per event type |
| `disk_event_count_by_region` | not inspected | Event count per region |

Only `category` and `region_id` were observed as actual `Labels` keys. For any other card, read `Data[0].Labels | keys` from the response rather than guessing the key from the title.

**Naming patterns** (useful when a new card appears):

- Capacity is always **`size`**, never `capacity`
- Billing type is **`pay_type`**, never `charge_type`
- Most dimensions come in an absolute (`disk_count_by_*` / `disk_size_by_*`) **and** a percentage (`*_percent_by_*`) variant — except `pay_type`, which has count variants only
- Event cards are prefixed `disk_event_count_by_*`, plus a standalone `event_summary`

> **Cards that do NOT exist in the verified payload:** there is no title for encrypted-disk count/ratio, ESSD AutoPL ratio or burst usage, async replication pair count, dedicated block storage cluster count, or over-provisioned disks. Earlier revisions of this document guessed such names (`encrypted_disk_percent`, `essd_autopl_percent`, `dbsc_count`, `disk_spec_exceed_instance_percent`, …) — all were wrong. Do not promise those figures to the user from this API.
>
> The list above is from one account in one region; a card may be absent when the account has no such resources. Always enumerate with `--cli-query "Datas[].Title"` for the target account rather than assuming this list is exhaustive.

---

## 3. list-reports (Plugin Mode)

List historical CloudLens for EBS resource overview reports.

### Syntax

```bash
aliyun ebs list-reports \
  --biz-region-id <region-id> \
  [--page-size <size>] \
  [--page-number <number>] \
  [--app-id <app-id>] \
  [--max-results <count>] \
  [--next-token <token>] \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-usage-summary/<session-id>
```

### Parameters

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `--biz-region-id` | Recommended | Region ID. The help output does not mark it as mandatory (unlike `get-report`), but always pass it explicitly instead of relying on the profile's default region. Call the [supported regions API](https://help.aliyun.com/document_detail/354276.html) to see where CloudLens for EBS is available | N/A |
| `--page-size` | No | Rows per page in page-based pagination (`int`) | 10 |
| `--page-number` | No | Page number in page-based pagination (`int`) | 1 |
| `--app-id` | No | Application ID filter | All apps |
| `--max-results` | No | Max items when using token-based pagination (`int`) | N/A |
| `--next-token` | No | Query token; use the `NextToken` returned by the previous call | N/A |

> Flag list verified against `aliyun ebs list-reports --help` (CLI 3.4.7): `--app-id`, `--max-results`, `--next-token`, `--page-number`, `--page-size`, `--biz-region-id`.

### Response Format

```json
{
  "RequestId": "...",
  "HistoryReports": [
    {
      "ReportId": "rpt-1234567890",
      "ReportTime": "2024-01-15T00:00:00Z",
      "SubscribePeriod": "weekly",
      "ReportName": "EBS Resource Overview - Week 3"
    }
  ],
  "TotalCount": 5,
  "NextToken": "..."
}
```

---

## Advanced Usage

### JMESPath Queries (--cli-query)

Extract specific fields from responses:

```bash
# Extract only disk IDs and IOPS values
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --biz-region-id <region-id> \
  --period 60 \
  --start-time <start-time> \
  --end-time <end-time> \
  --cli-query "DataList[].{DiskId: Labels, IOPS: Datapoints}"

# List every report card title in this account's report
aliyun ebs get-report \
  --biz-region-id <region-id> \
  --report-type present \
  --app-name default \
  --cli-query "Datas[].Title"

# Pull one card by title
aliyun ebs get-report \
  --biz-region-id <region-id> \
  --report-type present \
  --app-name default \
  --cli-query "Datas[?Title=='disk_count_percent_by_category'] | [0].Data"
```

> Filtering on `Title` works, but the series are nested: `Datas[?Title=='...'].DataPoints` returns nothing — you must descend into `.Data[]` first. Start from `--cli-query "Datas[].Title"` to learn which cards this account actually has.

### jq Pipelines

Parse and transform JSON responses:

```bash
# Parse Datapoints from describe-metric-data
# `fromjson` assumes Datapoints is a JSON string — check its type first (see the
# Response Format note above) and drop `fromjson` if it is already an object.
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --biz-region-id <region-id> \
  --period 60 \
  --start-time <start-time> \
  --end-time <end-time> \
  | jq '.DataList[0].Datapoints | fromjson | to_entries[] | {time: (.key | tonumber | strftime("%Y-%m-%d %H:%M:%S")), value: .value}'

# Flatten every get-report series into title/label/date/value rows
# (Labels is a real object and DataPoints keys are Unix seconds)
aliyun ebs get-report \
  --biz-region-id <region-id> \
  --report-type present \
  --app-name default \
  | jq -r '.Datas[] | .Title as $t | .Data[] | .Labels as $l | .DataPoints | to_entries[]
           | [$t, ($l | to_entries[0].value), (.key | tonumber | strftime("%Y-%m-%d")), .value] | @tsv'

# Pull a single card by title
aliyun ebs get-report \
  --biz-region-id <region-id> \
  --report-type present \
  --app-name default \
  | jq '.Datas[] | select(.Title == "disk_count_percent_by_category")'
```

### Inspecting a Report Card

```bash
# 1) Which cards exist, and what does each break down by?
aliyun ebs get-report \
  --biz-region-id <region-id> \
  --report-type present \
  --app-name default \
  | jq -r '.Datas[] | "\(.Title): \(.Data | length) series, labelled by \(.Data[0].Labels | keys | join(","))"'

# 2) Latest value per label for one card
aliyun ebs get-report \
  --biz-region-id <region-id> \
  --report-type present \
  --app-name default \
  | jq '.Datas[] | select(.Title == "<title>") | .Data[]
        | {label: .Labels, latest: (.DataPoints | to_entries | max_by(.key | tonumber) | .value)}'

# 3) Per-day totals for a percentage card (group by timestamp, not by series)
aliyun ebs get-report \
  --biz-region-id <region-id> \
  --report-type present \
  --app-name default \
  | jq -r '.Datas[] | select(.Title == "disk_count_percent_by_category")
           | [.Data[] | .DataPoints | to_entries[]] | group_by(.key)
           | map({date: (.[0].key | tonumber | strftime("%Y-%m-%d")),
                  series: length, total: (map(.value) | add)})[]
           | "\(.date) series=\(.series) total=\(.total)"'
```

> Recipe 2 reports each series' own newest point, which is the right answer for "what is the current value per label" but **not** for cross-series arithmetic — those points can fall on different days. Use recipe 3 whenever you add series together.

---

## Troubleshooting Quick Reference

This table is the single source of truth for command-level errors; SKILL.md links here instead of repeating it.

| Error | Cause | Solution |
|-------|-------|----------|
| `InvalidParameter.MetricName` | Invalid metric name | Use one of the 8 supported metrics listed above |
| `InvalidParameter: Period exceeds time range limit` | Period too small for time range | Check time range limits table above |
| `InvalidStartTime.TooEarly` | Start time beyond retention | Use more recent start time |
| `InvalidEndTime.Malformed` | Invalid time format | Use ISO 8601 format: `yyyy-MM-ddTHH:mm:ssZ` |
| Empty `DataList` | No data in range/filter | Widen filter or check time range |
| Empty `Datas` | CloudLens not enabled or preparing | Wait 10 min after enabling CloudLens |
| `MissingParameter: ReportId` | Report type is `history` without `--report-id` | Call `list-reports` first to get a report ID |
| `NoSuchResource` | Invalid report ID | Verify the ID against a `list-reports` response |
| `InvalidApi.NotFound` / unknown flag | Stale local CLI plugin | Run `aliyun plugin update`, then retry the same lowercase-hyphenated command |

---

## Related Resources

- [Alibaba Cloud CLI Documentation](https://help.aliyun.com/zh/cli/)
- [EBS API Documentation](https://help.aliyun.com/zh/ecs/developer-reference/api-ebs-2021-07-30-overview)
- [CloudLens for EBS](https://help.aliyun.com/zh/ecs/user-guide/what-is-a-piece-of-data-is-stored-insight/)
