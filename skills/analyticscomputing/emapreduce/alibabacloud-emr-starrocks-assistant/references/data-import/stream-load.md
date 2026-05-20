# Stream Load Detailed Guide

## Table of Contents

1. [Overview](#overview)
2. [HTTP Syntax](#http-syntax)
3. [Core Parameters](#core-parameters)
4. [CSV Ingestion](#csv-ingestion)
5. [JSON Ingestion](#json-ingestion)
6. [Data Transformation](#data-transformation)
7. [Multi-Table Ingestion](#multi-table-ingestion)
8. [Best Practices](#best-practices)
9. [Common Issues](#common-issues)

---

## Overview

Stream Load pushes a local file or data stream to StarRocks via HTTP PUT and synchronously returns the result. Suitable for batch ingestion of a single file < 10GB.

**Key characteristics:**
- Synchronous operation; success/failure is known immediately
- Supports CSV and JSON formats
- Supports data transformation during ingestion (column mapping, function computation, filtering)
- Supports UPSERT / DELETE on Primary Key tables
- Supports multi-table transactional ingestion (v3.x+)

---

## HTTP Syntax

**Basic syntax:**

```bash
curl --location-trusted -u <user>:<password> \
    -H "label:<label>" \
    -H "column_separator:<sep>" \
    -T <file_path> \
    http://<fe_host>:<fe_http_port>/api/<database>/<table>/_stream_load
```

**Request target:**
- Send to the FE HTTP port (default 8030); the FE redirects to a BE
- You can also send directly to the BE HTTP port (default 8040), skipping the FE redirect
- `--location-trusted` makes curl follow the redirect while carrying the auth info

**Sample response:**

```json
{
    "TxnId": 1003,
    "Label": "my_label_20240101",
    "Status": "Success",
    "Message": "OK",
    "NumberTotalRows": 1000000,
    "NumberFilteredRows": 0,
    "NumberUnselectedRows": 0,
    "LoadBytes": 52943670,
    "LoadTimeMs": 3245
}
```

**Status values:**
- `Success`: ingestion succeeded
- `Publish Timeout`: data was written but publish timed out; it will complete automatically and is treated as success
- `Label Already Exists`: a label with the same name already exists (idempotency safeguard)
- `Fail`: ingestion failed; check `Message` and `ErrorURL`

---

## Core Parameters

Passed via HTTP Header:

| Parameter | Required | Default | Description |
|------|------|--------|------|
| `label` | No | Auto-generated | Ingestion label; duplicates not allowed (idempotency safeguard) |
| `column_separator` | No | `\t` | CSV column separator; supports multi-character (e.g., `\x01`, `||`) |
| `row_delimiter` | No | `\n` | Row delimiter |
| `columns` | No | Auto-mapped | Column mapping and transformation expressions |
| `where` | No | None | Row filter condition |
| `max_filter_ratio` | No | `0` | Allowed ratio of error rows (0~1); exceeding causes the ingestion to fail |
| `partitions` | No | Auto | Target partitions |
| `timeout` | No | 600s | Timeout (seconds) |
| `strict_mode` | No | `false` | Strict mode; whether to filter rows that fail type conversion |
| `timezone` | No | Session timezone | Timezone; affects datetime type conversion |
| `format` | No | `csv` | Data format: `csv` or `json` |
| `jsonpaths` | No | Auto | JSON field extraction paths |
| `strip_outer_array` | No | `false` | Whether the JSON data is wrapped in an outer array |
| `partial_update` | No | `false` | Whether this is a partial column update (Primary Key table) |
| `partial_update_mode` | No | `row` | Partial update mode: `row` (default) / `column` — Stream Load support: **v3.5+** (Broker/Routine Load: v3.1+) |
| `merge_condition` | No | None | Conditional update expression on Primary Key table — Stream Load support: **v3.5+** (Broker/Routine Load: v3.2+) |
| `skip_header` | No | `0` | Number of CSV header rows to skip (v3.0+) |
| `trim_space` | No | `false` | Whether to trim leading/trailing whitespace in CSV fields |
| `enclose` | No | None | CSV field enclosing character (e.g., double quote `"`) |
| `escape` | No | None | CSV escape character |
| `compression` | No | None | File compression format: `gz`, `bz2`, `lz4`, `deflate`, `zstd` |

---

## CSV Ingestion

**Basic CSV ingestion:**

```bash
curl --location-trusted -u root: \
    -H "label:csv_load_20240101" \
    -H "column_separator:," \
    -H "skip_header:1" \
    -T /data/user_data.csv \
    http://fe_host:8030/api/mydb/user_table/_stream_load
```

**Handling special separators:**

```bash
# Hive default separator \x01
-H "column_separator:\x01"

# Multi-character separator
-H "column_separator:||"

# Tab separator (default)
-H "column_separator:\t"
```

**Handling quoted CSV:**

```bash
# CSV fields are wrapped in double quotes and contain commas
# "John","New York, NY","30"
-H "column_separator:," \
-H "enclose:\"" \
-H "escape:\\"
```

**Handling NULL values:**
- NULL is represented as `\N` in CSV (default)
- Custom NULL mapping can be done via the `columns` expression using `if` / `nullif`

**Handling compressed files:**

```bash
curl --location-trusted -u root: \
    -H "label:gz_load" \
    -H "compression:gz" \
    -T /data/user_data.csv.gz \
    http://fe_host:8030/api/mydb/user_table/_stream_load
```

---

## JSON Ingestion

**Basic JSON ingestion:**

```bash
# Single-line JSON (one JSON object per line)
curl --location-trusted -u root: \
    -H "format:json" \
    -H "strip_outer_array:true" \
    -T /data/users.json \
    http://fe_host:8030/api/mydb/user_table/_stream_load
```

**JSON data formats:**

```json
// Format 1: JSON array (requires strip_outer_array:true)
[
    {"id": 1, "name": "Alice", "age": 30},
    {"id": 2, "name": "Bob", "age": 25}
]

// Format 2: NDJSON (one JSON per line; strip_outer_array not required)
{"id": 1, "name": "Alice", "age": 30}
{"id": 2, "name": "Bob", "age": 25}
```

**Precise mapping with jsonpaths:**

```bash
# When JSON field names do not exactly match table column names
-H 'jsonpaths:["$.user_id", "$.user_name", "$.user_age"]' \
-H 'columns:id, name, age'
```

**Extracting nested JSON:**

```bash
# JSON: {"data": {"id": 1, "info": {"name": "Alice"}}}
-H 'jsonpaths:["$.data.id", "$.data.info.name"]' \
-H 'columns:id, name'
```

**Performance caveats for JSON ingestion:**
- JSON parsing is 2-5x slower than CSV
- Prefer CSV for large data volumes
- JSON files should not exceed 1-2 GB
- `streaming_load_max_batch_size_mb` (BE parameter) caps JSON file size

---

## Data Transformation

Stream Load supports lightweight ETL during ingestion via the `columns` parameter.

**Column renaming:**

```bash
# File has 5 columns, table has 3 columns; skip columns 2 and 4
-H "columns:col1, tmp_col2, col3, tmp_col4, col5"
# Columns prefixed with tmp_ that don't exist in the table are automatically ignored
```

**Column computation:**

```bash
# File columns: date_str, amount_cents
# Table columns: dt (DATE), amount (DECIMAL)
-H "columns:date_str, amount_cents, dt=str_to_date(date_str,'%Y%m%d'), amount=amount_cents/100"
```

**Row filtering:**

```bash
# Only ingest rows where age > 18
-H "where:age > 18"
```

**Extracting partition fields from file paths:**

```bash
# File path contains partition info: /data/dt=20240101/region=us/data.csv
-H "columns:col1, col2, col3" \
-H "column_from_path:dt, region"
```

**Common transformation functions:**
- `str_to_date(str, format)` — string to date
- `if(condition, true_val, false_val)` — conditional expression
- `nullif(expr1, expr2)` — returns NULL if values are equal
- `ifnull(expr, default)` — NULL replacement
- `cast(expr AS type)` — type cast
- `substr(str, pos, len)` — substring
- `concat(str1, str2)` — string concatenation
- `now()` — current time

---

## Multi-Table Ingestion

v3.x+ supports ingesting data into multiple tables in a single HTTP request with transactional atomicity.

```bash
curl --location-trusted -u root: \
    -H "label:multi_table_load" \
    -F "table1=@/data/table1.csv;columns:c1,c2,c3" \
    -F "table2=@/data/table2.csv;columns:c1,c2" \
    http://fe_host:8030/api/mydb/_stream_load_multi_table
```

---

## Best Practices

### File Size

| File size | Recommendation |
|---------|------|
| < 100 MB | Ingest directly, no special handling |
| 100 MB ~ 5 GB | Recommended range; highest per-batch efficiency |
| 5 GB ~ 10 GB | Workable; ensure a sufficient timeout |
| > 10 GB | Split the file, or use Broker Load / Pipe |

### Label Management
- Use labels for idempotency: a given label can only be ingested once
- Recommended label format includes date and batch number: `daily_load_20240101_001`
- Label retention is controlled by the FE parameter `label_keep_max_second` (default 3 days)

### Timeout Settings
- Default is 600s (10 minutes); adjust with `-H "timeout:3600"`
- Estimation formula: `timeout ≈ file size (MB) / expected throughput (MB/s) × 2`
- FE parameter `stream_load_default_timeout_second` controls the default value
- FE parameter `max_stream_load_timeout_second` controls the upper bound

### Error Handling
- Set `max_filter_ratio` to 0 for zero tolerance (recommended for production)
- To tolerate some dirty data, set it to 0.01 (1%) or lower
- The `ErrorURL` in the response shows the specific error rows
- Combine with `strict_mode:true` so rows that fail type conversion are filtered (instead of converted to NULL)

### Performance Optimization
- Per-ingestion throughput is typically 50-200 MB/s (depends on BE configuration and network)
- Launching multiple Stream Loads in parallel can boost overall throughput
- CSV is 2-5x faster than JSON; prefer CSV for large data volumes
- Compressed files (gz/lz4) reduce network transfer time but add BE decompression overhead

---

## Common Issues

| Issue | Cause | Resolution |
|------|------|---------|
| `Label Already Exists` | A label with the same name has been used | Use a different label, or wait for `label_keep_max_second` to expire |
| `body exceed max size` | File exceeds the BE limit | Increase `streaming_load_max_mb` (BE parameter, default 100GB) |
| `TabletWriter add batch with unknown id` | Write timeout | Increase `streaming_load_rpc_max_alive_time_sec` (default 1200s) |
| `too many tablet versions` | Ingestion is too frequent | Reduce frequency, batch the data, or tune compaction parameters |
| Ingestion succeeds but data is all NULL | Column separator mismatch | Verify that `column_separator` matches the actual file separator |
| JSON field values are all NULL | Field-name case mismatch | Use `jsonpaths` for precise mapping |
| `close index channel failed` | Compaction backlog | Reduce ingestion frequency, increase compaction threads |
