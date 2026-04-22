# `GetIssues` - aggregated error list

Aliyun CLI command: `aliyun emas-appmonitor get-issues`
API version: `2019-06-11` · Action: `GetIssues` · Method: `POST` RPC

Queries the **aggregated Issue list** under a given `AppKey + Os + BizModule + TimeRange` combination. Each record represents a distinct error cluster (identified by `DigestHash`) and can be sorted by error count / error rate / affected device count / affected device rate.

## Parameters

| CLI flag | Required | Type | Description |
| --- | --- | --- | --- |
| `--app-key` | Yes | int64 | Application AppKey, 10 digits or more |
| `--biz-module` | Yes | string | `crash` / `anr` / `lag` / `custom` / `memory_leak` / `memory_alloc` (the CLI `--help` only lists some of the 6; this Skill has verified that the rest **are forwarded as-is**; see `biz-module-reference.md`) |
| `--time-range` | Yes | object | `StartTime=<ms> EndTime=<ms> Granularity=<int> GranularityUnit=<MINUTE\|HOUR\|DAY>`; see "TimeRange" below |
| `--os` | Recommended | string | `android` / `iphoneos` / `harmony`. *Strongly recommended*; otherwise aggregation buckets from different platforms are mixed |
| `--filter` | No | object | Filter condition as a JSON string; see `filter-reference.md` |
| `--name` | No | string | Fuzzy search by `Name` |
| `--order-by` | No | string | `ErrorCount` / `ErrorRate` / `ErrorDeviceCount` / `ErrorDeviceRate` |
| `--order-type` | No | string | `asc` / `desc`, default `desc` |
| `--page-index` | No | int | Default 1 |
| `--page-size` | No | int | Server default; 10~50 recommended |
| `--status` | No | int | `1=NEW` / `2=OPEN` / `3=CLOSE` / `4=FIXED` |

### TimeRange wire format

In the OpenAPI, `TimeRange` is declared as `style: "flat"` - the CLI **flattens** the sub-fields into `Key=Value` form, separated by spaces, and the whole block is the value of `--time-range`:

```bash
--time-range StartTime=1775000000000 EndTime=1776000000000 Granularity=1 GranularityUnit=HOUR
```

- `StartTime` / `EndTime`: Unix millisecond timestamps (`int64`)
- `Granularity` + `GranularityUnit`: reference window for computing "growth rate"
- `GranularityUnit` values: `MINUTE` / `HOUR` / `DAY`

**Pitfall (observed by this Skill)**: in some prod environments, the combination `Granularity=60 GranularityUnit=MINUTE` can be rejected by the backend (returns `Code:200, Message:"unknown error"`). **Recommended forms**:
- Day level: `Granularity=1 GranularityUnit=DAY`
- Hour level: `Granularity=1 GranularityUnit=HOUR`

## `--cli-dry-run` example

Verify the request body format (does not send the real request):

```bash
aliyun emas-appmonitor get-issues \
  --app-key 12345678 \
  --os iphoneos \
  --biz-module crash \
  --time-range StartTime=1776000000000 EndTime=1776086400000 Granularity=1 GranularityUnit=HOUR \
  --page-index 1 --page-size 10 \
  --cli-dry-run
```

The dry-run prints a `Body` JSON in which `AppKey` / `BizModule` / `Os` are top-level fields, `TimeRange` is a nested object, and `Filter` (if provided) is **the entire JSON string** (the value at the `Filter` key is a string, not an object).

## Response structure

Top-level fields (consistent across all emas-appmonitor APIs):

| Field | Type | Description |
| --- | --- | --- |
| `Success` | boolean | Whether the business logic succeeded |
| `ErrorCode` | int32 | 0 means normal; non-zero see `Message` |
| `Message` | string | Error description; `"SUCCESS"` on success |
| `RequestId` | string | POP request ID; include this when reporting issues |
| `Model` | object | Business data, see below |

`Model` fields:

| Field | Type | Description |
| --- | --- | --- |
| `Total` | int64 | Total number of Issues matched (not the count on this page) |
| `PageNum` | int32 | Current page number |
| `PageSize` | int32 | Current page size |
| `Pages` | int32 | Total pages |
| `Items` | array | Each element is one Issue; see the table below |

`Model.Items[*]` fields:

| Field | Type | Description |
| --- | --- | --- |
| `DigestHash` | string | Unique Issue ID (Base36, fixed length 13). Use it as-is when calling `get-issue` / `get-errors` / `get-error` |
| `Name` | string | Issue title (usually truncated from the first few stack frames) |
| `Status` | int32 | `1=NEW` / `2=OPEN` / `3=CLOSE` / `4=FIXED` |
| `FirstVersion` | string | App version when the Issue first appeared |
| `ErrorCount` | int32 | Error count within the time window |
| `ErrorRate` | double | Error rate (errors / app launches) |
| `ErrorDeviceCount` | int32 | Affected device count |
| `ErrorDeviceRate` | double | Affected device rate |
| `AffectedUserCount` | int32 | Affected user count |
| `Stack` | string | Truncated stack (for reporting) |
| `Type` / `Reason` | string | crash: `EXC_BAD_ACCESS...` / `KERN_PROTECTION_FAILURE`; custom: business errorCode |
| `LagCost` | int64 | Only valid for lag; lag duration (ms) |
| `AllocSizePct90 / Pct70 / Pct50 / Max` | int64 | Only valid for memory_alloc; in-cluster allocation size percentiles |
| `EventTime` | string | Latest event time |
| `Tags` | array<string> | Manual tags |

## Key JMESPath expressions

Commonly used inside `--cli-query` (note the TitleCase keys, mapped from `backendName` in `.cspec`):

| Purpose | JMESPath |
| --- | --- |
| Core fields for N items on the current page | `Model.Items[*].{dh:DigestHash,name:Name,ec:ErrorCount,er:ErrorRate,edc:ErrorDeviceCount,status:Status}` |
| Digest hash list only | `Model.Items[*].DigestHash` |
| Just the total | `Model.Total` |
| Filter rows with `ErrorCount > 10` | `Model.Items[?ErrorCount > \`10\`].{dh:DigestHash,ec:ErrorCount}` |

## Typical sorting strategies

**By error rate** (the primary metric, traffic-normalized):

```bash
aliyun emas-appmonitor get-issues --app-key ... --biz-module crash --time-range ... \
  --order-by ErrorRate --order-type desc --page-size 5 \
  --cli-query "Model.Items[*].{dh:DigestHash,name:Name,er:ErrorRate,ec:ErrorCount}"
```

**By absolute error count** (useful for high-DAU apps to surface high-frequency Issues):

```bash
aliyun emas-appmonitor get-issues --app-key ... --biz-module lag --time-range ... \
  --order-by ErrorCount --order-type desc --page-size 5
```

## Common business errors

| HTTP | `ErrorCode` | Meaning | Action |
| --- | --- | --- | --- |
| 400 | `InvalidAppId` | AppKey does not exist or cannot be parsed | Confirm the AppKey; do not use leading zeros |
| 400 | `InvalidParameters` | Some parameter is invalid (commonly: invalid `Granularity` combination, `TimeRange.StartTime > EndTime`) | Check timestamp unit and granularity combination |
| 400 | `InvalidRequest` | Request structure is invalid | Verify body field names |
| 403 | `Forbidden.NoRAMPermission` | RAM lacks `emasha:ViewIssues` | See `ram-policies.md` |
| 403 | `Forbidden.NoPermission` | Account does not own this AppKey | Find the AppKey owner account |
| 406 | `UnexpectedAppStatus` | App status is abnormal (overdue / disabled, etc.) | Activate the corresponding sub-service in the console (crash / apm / tlog) |
| 500 | `InternalError` | Backend error | Retry; report with `RequestId` |

## Pitfalls & tips

- **`--page-size 1` triggers `unknown error`**: this Skill has verified that the backend returns `Code: 200, Message: "unknown error"` for certain biz_modules when `PageSize=1`. **The minimum recommended is `--page-size 2`**; commonly use `--page-size 10`.
- **The list API does not filter by `DigestHash`**: to fetch one known Issue by hash, use `get-issue`.
- **Top N merging**: the 6 `BizModule`s for the same `AppKey + Os` are not exposed in a single API. This Skill's `list_top_issues.sh` parallel-invokes `get-issues` 6 times and merges / sorts with `jq`.
- **The denominator of `ErrorRate`** is the number of launches that day (computed by backend OLAP); low-traffic apps amplify noise. Always look at `ErrorCount` alongside.
- **`Status` field**: `CLOSE` / `FIXED` also appear in the response; to see only active issues, pass `--status 1` or `--status 2`, or filter client-side with JMESPath.
- **Pagination**: for a full scan, use `--pager` to let the CLI merge pages automatically; for big AppKeys, sample with `--page-size 10` first.
