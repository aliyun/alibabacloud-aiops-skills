# `GetErrors` - sample list

Aliyun CLI command: `aliyun emas-appmonitor get-errors`
API version: `2019-06-11` · Action: `GetErrors` · Method: `POST` RPC

Queries the **sample list** under an Issue (`DigestHash`). **Each record only contains the "sample pointer" quadruple** - `ClientTime` + `Uuid` + `Did` + `DigestHash` - full dimensions / stack / logs must be fetched via `get-error` using these pointers.

## Parameters

| CLI flag | Required | Type | Description |
| --- | --- | --- | --- |
| `--app-key` | Yes | int64 | AppKey |
| `--biz-module` | Yes | string | One of the 6 enum values |
| `--page-index` | Yes | int | Page number (CLI `--help` says required) |
| `--page-size` | Yes | int | Page size (same) |
| `--time-range` | Yes | object | **Only `StartTime` + `EndTime` (ms), no `Granularity`** |
| `--os` | Recommended | string | `android` / `iphoneos` / `harmony`. *Strongly recommended* |
| `--digest-hash` | Recommended | string | *Effectively required*: omitting it pulls samples for the whole AppKey, which is useless for troubleshooting |
| `--filter` | No | object | Further filter samples (common: specific version, device model) |

### TimeRange format

```bash
--time-range StartTime=<ms> EndTime=<ms>
```

> **Important: `--time-range` on `get-errors` does NOT accept `Granularity` / `GranularityUnit`**. Mixing those in causes the CLI to exit with `Error: unknown field: Granularity`.

### `--page-size` pitfall (shared)

Verified by this Skill: **`--page-size 1` triggers backend `unknown error`** (see `get-issues.md`). Minimum recommended `--page-size 2`; commonly `--page-size 10`.

## `--cli-dry-run` example

```bash
aliyun emas-appmonitor get-errors \
  --app-key 12345678 \
  --os iphoneos \
  --biz-module crash \
  --time-range StartTime=1776000000000 EndTime=1776086400000 \
  --digest-hash 3JE6F43KCQ1SV \
  --page-index 1 --page-size 5 \
  --cli-dry-run
```

## Response structure

`Model` fields:

| Field | Type | Description |
| --- | --- | --- |
| `Total` | int64 | Total number of matched samples |
| `PageNum` / `PageSize` / `Pages` | int32 | Pagination |
| `Items` | array | See below (**only 5 fields**) |

### `Model.Items[*]` fields (**only these 5**)

| Field | Type | Description |
| --- | --- | --- |
| `ClientTime` | int64 | Client time of the sample (ms) - required `--client-time` for `get-error` |
| `Did` | string | Device id (plaintext) - optional `--did` for `get-error` |
| `Utdid` | string | UTDID (desensitized device id) |
| `Uuid` | string | Event unique id - optional `--uuid` for `get-error` |
| `DigestHash` | string | DigestHash of the owning Issue - echoes the input |

> **Do NOT** expect `get-errors` to return `AppVersion` / `OsVersion` / `DeviceModel` / `Stack` - those require `get-error`.

## Key JMESPath expressions

```bash
# Extract the client-time + uuid + did triple (used by the next get-error call)
--cli-query "Model.Items[*].{ct:ClientTime,uuid:Uuid,did:Did,utdid:Utdid}"

# Uuid list only
--cli-query "Model.Items[*].Uuid"

# Total count
--cli-query "Model.Total"
```

## Typical usage

**1. Pick 3~5 latest samples**

```bash
aliyun emas-appmonitor get-errors \
  --app-key 335695934 --os iphoneos --biz-module crash \
  --time-range StartTime=$START EndTime=$END \
  --digest-hash $DIGEST \
  --page-index 1 --page-size 5 \
  --cli-query "Model.Items[*].{ct:ClientTime,uuid:Uuid,did:Did}"
```

Pass the returned `ct` + `uuid` + `did` triples to `get-error` to drill into each sample.

**2. Narrow to a specific version / device**

```bash
aliyun emas-appmonitor get-errors \
  --app-key 335695934 --os iphoneos --biz-module crash \
  --time-range StartTime=$START EndTime=$END \
  --digest-hash $DIGEST \
  --filter '{"Key":"appVersion","Operator":"in","Values":["3.5.0"]}' \
  --page-index 1 --page-size 10
```

`Filter.Key` comes from `assets/system-filters/<biz-module>-<platform>.json`. Note that after filtering, `Model.Total` only reflects "samples passing the filter", not the overall Issue ErrorCount.

## Common errors

| Symptom | Meaning | Action |
| --- | --- | --- |
| `Error: unknown field: Granularity` | `--time-range` mixed in Granularity | Remove Granularity / GranularityUnit |
| `Code: 200, Message: "unknown error"` | Common with `--page-size 1` | Increase `--page-size` to >= 2 |
| `Success=true, Items=[], Total=0` | No matches inside the window / filter | Widen `TimeRange`; confirm `biz-module` matches the Issue's module |
| `Forbidden.NoRAMPermission` | Missing `emasha:ViewErrors` | See `ram-policies.md` |

## Tips

- **Keep `--time-range` within 30 days**: backend OLAP retention is limited; 7~14 days is safe.
- **`page-size <= 10`**: Top-N analysis only needs 3~5 representative samples; more slows down overall troubleshooting.
- **Missing any of the triple degrades `get-error` into "fuzzy match"**:
  - `ClientTime` is required
  - `Uuid` is optional but **strongly recommended** (most precise)
  - `Did` is optional
  - `DigestHash` + `BizModule` + `Os` serve as auxiliary filters
