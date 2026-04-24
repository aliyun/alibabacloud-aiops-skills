# Related APIs - SLS Query & Analysis

This document is an API / CLI reference for the SLS query/analysis skill. It covers two
read-only endpoints: `GetLogsV2` (run a query or SQL/SPL analysis) and `GetIndex` (inspect
the index configuration of a Logstore). For usage patterns and worked examples, see the
other docs in this skill.

## Command List

| CLI Command | API Action | Description | Documentation |
|-------------|------------|-------------|---------------|
| `aliyun sls get-logs-v2` | GetLogsV2 | Run a query / SQL / SPL statement against a Logstore and return log rows or aggregated results | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getlogsv2) |
| `aliyun sls get-index` | GetIndex | Read the current index configuration of a Logstore (full-text index, field indexes, JSON keys, TTL, log-reduce) | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getindex) |

> **Deprecated — do not use**: `GetLogs` (`aliyun sls get-logs`). Use `GetLogsV2` instead.

---

## GetLogsV2

`POST /logstores/{logstore}/logs` — invoke via `aliyun sls get-logs-v2`.

### Input — Required

| Parameter | Type | CLI Flag | Description |
|-----------|------|----------|-------------|
| Project | string | `--project` | Project name. |
| Logstore | string | `--logstore` | Logstore name. |
| From | integer | `--from` | Start time, Unix timestamp in **seconds**. Inclusive. |
| To | integer | `--to` | End time, Unix timestamp in **seconds**. Exclusive. `from == to` is rejected. |

### Input — Optional

| Parameter | Type | CLI Flag | Description |
|-----------|------|----------|-------------|
| Query | string | `--query` | Query or query + SQL/SPL statement. Omit or use `*` to match all logs. |
| Topic | string | `--topic` | Log topic filter. Default empty. |
| Line | integer | `--line` | Max rows per response, `0–100`, default `100`. Query-mode only (ignored when SQL is present; use `LIMIT` instead). |
| Offset | integer | `--offset` | Starting row for pagination, default `0`. Query-mode only. |
| Reverse | boolean | `--reverse` | `true` = newest first, `false` (default) = oldest first. Query-mode only; in SQL mode use `ORDER BY`. |
| PowerSQL | boolean | `--power-sql` | Enable Dedicated SQL. Default `false`. Equivalent to prepending `set session parallel_sql=true;` to the SQL. |
| Session | string | `--session` | Session hints, e.g. `mode=scan` to force SPL / scan mode. |
| Forward | boolean | `--forward` | Scan / phrase-query paging direction. Default `false`. |
| IsAccurate | boolean | `--is-accurate` | Enable nanosecond-level ordering. |
| Accept-Encoding | string | `--accept-encoding` | Wire compression format (`lz4` / `gzip`). Affects only transport, not the decoded result; the CLI handles decompression automatically. You normally do not need to set this. |

### Output

| Field | Meaning |
|-------|---------|
| `meta.progress` | `Complete` or `Incomplete`. **Always check**: `Incomplete` means the result is partial and the same request should be retried until it returns `Complete`. |
| `meta.count` | Number of rows returned in this response. |
| `data` | Array of `{ key: value }` objects — one log row per entry. `__time__` is seconds. |

---

## GetIndex

`GET /logstores/{logstore}/index` — invoke via `aliyun sls get-index`.

### Input — Required

| Parameter | Type | CLI Flag | Description |
|-----------|------|----------|-------------|
| Project | string | `--project` | Project name. |
| Logstore | string | `--logstore` | Logstore name. |

### Output

| Field | Meaning |
|-------|---------|
| `ttl` | Index TTL in days. |
| `max_text_len` | Max indexed field length (64–16384 bytes, default 2048). |
| `index_mode` | Index type, typically `v2`. |
| `line` | Full-text index configuration (`chn`, `caseSensitive`, `token`, `include_keys`, `exclude_keys`). Absence means full-text index is disabled. |
| `keys` | Field-index map: key = field name, value = `IndexKey` with `type` (`text` / `long` / `double` / `json`), `chn`, `caseSensitive`, `token`, `alias`, `doc_value` (enables SQL statistics), `json_keys` (for nested JSON fields). |
| `log_reduce` | Whether log clustering (LogReduce) is enabled. |
| `log_reduce_white_list` / `log_reduce_black_list` | Fields included/excluded from clustering. |
| `lastModifyTime` | Last index modification time (Unix seconds). |
| `storage` | Storage type, fixed to `pg`. |

## Common Errors

| HTTP Status | ErrorCode | Meaning |
|-------------|-----------|---------|
| 404 | `ProjectNotExist` | Project name is wrong or in a different region. |
| 404 | `LogStoreNotExist` | Logstore name is wrong. |
| 404 | `IndexConfigNotExist` | No index configured on this Logstore — any query/SQL will fail. |
| 500 | `InternalServerError` | Retry with backoff. |

---

## Reference Documentation

| Document | Description |
|----------|-------------|
| [GetLogsV2 API](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getlogsv2) | Official API reference for the query/analysis endpoint |
| [GetIndex API](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getindex) | Official API reference for reading index configuration |
| [Query syntax overview](https://help.aliyun.com/document_detail/43772.html) | Index query language (full-text, field filter, boolean operators) |
| [SQL analytics overview](https://help.aliyun.com/document_detail/53608.html) | SLS SQL grammar, functions, and pagination |
| [SPL overview](https://help.aliyun.com/zh/sls/user-guide/spl-overview) | Scan Processing Language for row-level transforms and scan queries |
| [General API error codes](https://help.aliyun.com/document_detail/29013.html) | Shared SLS error-code table |
| [Aliyun CLI — SLS plugin](https://github.com/aliyun/aliyun-cli) | CLI source and release notes |
