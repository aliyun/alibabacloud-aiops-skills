# ADB Presto OSS Table Functions

OSS table functions read files directly without creating tables in Hive Metastore. Their metadata is released after the query.

## Function Selection

| Function | Use case |
|---|---|
| `files(...)` | The format is unknown or a unified reader is preferred. Supports automatic format detection. |
| `hive_files(...)` | The path is confirmed to be a Hive-style `key=value` partition directory. |

Use `files(...)` as the only general direct-file entry point so that the service performs format and schema inference. Use `hive_files(...)` only when the path has a confirmed Hive partition layout. This skill does not execute `parquet_file(...)`, `csv_file(...)`, or `json_file(...)`; if automatic inference fails, stop instead of selecting a reader from an assumed format.

Only a specific unsupported `DESCRIBE files(...)` statement-shape error permits the single bounded `SELECT ... LIMIT 5` fallback below. Authentication or authorization errors, missing workspace/bucket/prefix errors, and `Cannot detect OSS file format` / `no supported files` / `No files found` errors are terminal. Report the redacted error and stop without changing the URI or reader.

## Path Rules

| OSS URI | Meaning |
|---|---|
| `oss://bucket/path/file.parquet` | One object |
| `oss://bucket/path/*.parquet` | Match the current level |
| `oss://bucket/path/**/*.parquet` | Recursively match from the fixed prefix |
| `oss://bucket/path/ds=*/part-*` | Expand partition-like path segments |
| `oss://bucket/path/` | Recursively read visible data files under the directory |

Files and path segments beginning with an underscore or dot are ignored by default. Only `oss://` is supported; S3, HDFS, and OSS-HDFS URIs are not supported.

## Format Discovery and Schema Inference

### Unknown format

```sql
DESCRIBE files(location => 'oss://bucket/path/')
```

If the service cannot `DESCRIBE` a table-function call, make only one bounded fallback:

```sql
SELECT *
FROM files(location => 'oss://bucket/path/')
LIMIT 5
```

Automatic format detection checks the path suffix, listed file suffixes, and a bounded content sample of `.txt` files. Mixed formats under the selected path cause an error. Extensionless objects cannot be detected reliably.

### Automatic schema

```sql
SELECT *
FROM files(
  location => 'oss://bucket/path/*.parquet',
  schema => 'auto'
)
LIMIT 20
```

`schema => 'auto'` performs bounded listing and sampling during planning. Restrict the path first, validate the inferred columns, and keep later queries within that same confirmed prefix and automatic reader.

## Hive Partition Directories

Example layout:

```text
oss://bucket/events/
  ds=2026-07-10/
    hour=12/
      part-000.parquet
```

```sql
SELECT event_id, payload, ds, hour
FROM hive_files(
  location => 'oss://bucket/events/',
  schema => 'auto',
  partition_columns => 'auto'
)
WHERE ds = DATE '2026-07-10'
  AND hour = 12
LIMIT 100
```

Confirm the Hive partition naming convention before using `hive_files(...)`. Add partition predicates as early as possible to avoid listing and scanning unrelated partitions.

## Important Limitations

- All data files under the selected path must resolve to one format.
- Content sniffing samples only a bounded number of `.txt` files; extensionless files are not sniffed.
- Schema inference is sample-based and is not proof of complete data quality.
- A path with many Hive partitions can require expensive directory discovery before split generation. Narrow the prefix first.
- Format-specific readers are intentionally outside this skill's workflow. A failed automatic inference is reported rather than retried with an assumed format.
- A successful table-function query proves only that the files are readable, not that the returned data answers the user's question.
