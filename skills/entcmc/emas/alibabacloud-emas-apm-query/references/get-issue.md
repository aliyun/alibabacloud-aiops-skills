# `GetIssue` - aggregated error detail

Aliyun CLI command: `aliyun emas-appmonitor get-issue`
API version: `2019-06-11` · Action: `GetIssue` · Method: `POST` RPC

Queries the aggregated statistics of a **single Issue** (identified by `DigestHash`) within a specified time window, including error rate, affected devices, affected version list, growth rate, summary stack and so on. Used to **drill into each** Top N Issue after `get-issues`.

## Parameters

| CLI flag | Required | Type | Description |
| --- | --- | --- | --- |
| `--app-key` | Yes | int64 | AppKey |
| `--os` | Yes | string | `android` / `iphoneos` / `harmony` (note: `os` is strictly required here) |
| `--biz-module` | Yes | string | Same 6 enum values as `get-issues` |
| `--time-range` | Yes | object | Same as `get-issues`; see below |
| `--digest-hash` | Recommended | string | Base36 (13 chars). *Effectively required*: the backend `getIssueDetail` returns `InvalidParameters` when `digestHash` is empty |
| `--filter` | No | object | Further narrow the filter scope (e.g. a specific `appVersion`) |

### TimeRange

Exactly the same as `get-issues` (`style: "flat"`):

```bash
--time-range StartTime=<ms> EndTime=<ms> Granularity=1 GranularityUnit=HOUR
```

**Same pitfall**: avoid `Granularity=60 GranularityUnit=MINUTE`; use `1 HOUR` or `1 DAY` instead.

## Use cases

1. You already have a `DigestHash` (from `get-issues` / an alert / a console link) and want to view the aggregated metrics of that Issue in **any time window** (the metrics in the `get-issues` list only reflect the window of that page).
2. Compare the `ErrorCount` / `ErrorRate` / `Pages` of the same Issue across two time windows (the `Growth*` fields automatically compare against the previous equal-sized window).
3. Obtain the **affected version list** (`AffectedVersions`) - the list API does not return this field.

## `--cli-dry-run` example

```bash
aliyun emas-appmonitor get-issue \
  --app-key 12345678 \
  --os iphoneos \
  --biz-module crash \
  --time-range StartTime=1776000000000 EndTime=1776086400000 Granularity=1 GranularityUnit=DAY \
  --digest-hash 3JE6F43KCQ1SV \
  --cli-dry-run
```

## Response structure

Top level is the same as `get-issues`: `Success` / `ErrorCode` / `Message` / `RequestId` / `Model`.
`Model` is a single Issue object (not an array); major fields:

| Field | Type | Description |
| --- | --- | --- |
| `DigestHash` | string | Echoes the input |
| `Name` | string | Issue title |
| `Status` | int32 | `1=NEW` / `2=OPEN` / `3=CLOSE` / `4=FIXED` |
| `FirstVersion` | string | First-seen version |
| `AffectedVersions` | array<string> | Affected version list |
| `GmtCreate` | int64 | Issue first-created time (ms) |
| `GmtLatest` | int64 | Most recent occurrence time (ms) |
| `ErrorCount` / `ErrorRate` | int32 / double | Absolute count and ratio within the window |
| `ErrorCountGrowthRate` / `ErrorRateGrowthRate` | double | Growth rate vs the previous equal-sized window |
| `ErrorDeviceCount` / `ErrorDeviceRate` | int32 / double | Affected device count and rate |
| `ErrorDeviceCountGrowthRate` / `ErrorDeviceRateGrowthRate` | double | Growth rate |
| `Stack` | string | Full stack (richer than `get-issues.Items[*].Stack`) |
| `CruxStack` / `KeyLine` | string / int32 | Compressed key stack and key line |
| `Summary` | string | Machine-generated summary |
| `SymbolicStatus` | boolean | Whether already symbolicated (iOS) |
| `Type` / `Reason` | string | Exception type and reason |
| `Tags` | array<string> | User tags |
| `LagCost` | int64 | lag duration (ms) |
| `AllocSizeMax` / `AllocSizePct90` / `Pct70` / `Pct50` / `EventTime` | int64 / string | memory_alloc specific |
| `ErrorLine` / `ErrorColumn` / `ErrorFileName` / `ErrorName` / `ErrorType` | string | h5 / js related (usually not relevant for the 6 modules in this Skill) |

## Key JMESPath expressions

```bash
# Key numbers + stack at once
--cli-query "Model.{status:Status,errorCount:ErrorCount,errorRate:ErrorRate,versions:AffectedVersions,type:Type,reason:Reason,stack:Stack}"

# Only whether it is growing
--cli-query "Model.{ec:ErrorCount,ecGrowth:ErrorCountGrowthRate,er:ErrorRate,erGrowth:ErrorRateGrowthRate}"

# Only the affected versions
--cli-query "Model.AffectedVersions"
```

## Common errors

Mostly same as `get-issues`, additional notes:

- `InvalidParameters` with `Message` mentioning `digestHash` -> `--digest-hash` was not provided, or it was not a 13-char Base36 string.
- `Model` is `null` (`Success=true` but empty `Model`) -> no data for this `DigestHash` within the window; widen the `TimeRange` or switch `biz-module`.

## Tips

- **Pair with `get-errors`**: `get-issue` tells you "what the cluster is"; `get-errors` tells you "which concrete samples exist". `dig_issue.sh` in this Skill runs them in this order by default.
- **Spotting fast-growing Issues**: set `TimeRange` to yesterday's 24h, and `get-issue`'s `ErrorCountGrowthRate` is the "today vs yesterday" growth rate.
- **Symbolication check**: on iOS, when `SymbolicStatus=false` the `Stack` contains many hex addresses; uploading the dSYM is required. You can still use `cruxStack` as an aid.
