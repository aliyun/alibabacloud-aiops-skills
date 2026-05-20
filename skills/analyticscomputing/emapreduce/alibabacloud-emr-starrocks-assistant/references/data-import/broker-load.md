# Broker Load Detailed Guide

## Table of Contents

1. [Overview](#overview)
2. [SQL Syntax](#sql-syntax)
3. [Storage System Configuration](#storage-system-configuration)
4. [Format Parameters](#format-parameters)
5. [Data Transformation](#data-transformation)
6. [Best Practices](#best-practices)
7. [Monitoring and Management](#monitoring-and-management)
8. [Common Issues](#common-issues)

---

## Overview

Broker Load ingests data in batch from HDFS or cloud storage asynchronously. After submission it runs in the background; check progress via `SHOW LOAD`.

**Key characteristics:**
- Asynchronous execution; suitable for large-scale offline ingestion
- Supports CSV, Parquet, and ORC formats (JSON is **not** supported — use `INSERT INTO ... FROM FILES()` instead for JSON in object storage)
- Supports HDFS, S3, OSS, Azure Blob, GCS, MinIO, and other storage backends
- Supports wildcards to match multiple files
- Supports multi-table transactional ingestion
- Supports UPSERT / DELETE on Primary Key tables
- Supports both broker mode (HA/Kerberos) and broker-free mode

---

## SQL Syntax

**Basic syntax:**

```sql
LOAD LABEL <database>.<label>
(
    DATA INFILE("<file_path>")
    [NEGATIVE]
    INTO TABLE <table_name>
    [PARTITION (<partition_list>)]
    [COLUMNS TERMINATED BY "<separator>"]
    [ROWS TERMINATED BY "<row_separator>"]
    [FORMAT AS "CSV|Parquet|ORC"]
    [(column_list)]
    [COLUMNS FROM PATH AS (partition_columns)]
    [SET (column_mapping)]
    [WHERE <predicate>]
)
[WITH BROKER "<broker_name>" (<broker_properties>)]
PROPERTIES (<load_properties>);
```

**Full example — ingest CSV from OSS:**

```sql
LOAD LABEL mydb.oss_load_20240101
(
    DATA INFILE("oss://my-bucket/data/2024/01/01/*.csv")
    INTO TABLE user_behavior
    COLUMNS TERMINATED BY ","
    (user_id, item_id, behavior_type, ts_str)
    SET (event_time = str_to_date(ts_str, '%Y-%m-%d %H:%i:%s'))
    WHERE behavior_type IN ('buy', 'cart')
)
WITH BROKER
(
    "fs.oss.accessKeyId" = "<ak>",
    "fs.oss.accessKeySecret" = "<sk>",
    "fs.oss.endpoint" = "oss-cn-hangzhou-internal.aliyuncs.com"
)
PROPERTIES
(
    "timeout" = "7200",
    "max_filter_ratio" = "0.01"
);
```

**Ingest Parquet from OSS:**

```sql
LOAD LABEL mydb.parquet_load
(
    DATA INFILE("oss://my-bucket/data/dt=2024-01-01/*.parquet")
    INTO TABLE user_behavior
    FORMAT AS "parquet"
    (user_id, item_id, behavior_type, event_time)
    COLUMNS FROM PATH AS (dt)
)
WITH BROKER
(
    "fs.oss.accessKeyId" = "<ak>",
    "fs.oss.accessKeySecret" = "<sk>",
    "fs.oss.endpoint" = "oss-cn-hangzhou-internal.aliyuncs.com"
)
PROPERTIES ("timeout" = "7200");
```

**Multi-table ingestion (atomic within the same batch):**

```sql
LOAD LABEL mydb.multi_table_load
(
    DATA INFILE("oss://bucket/orders/*.csv")
    INTO TABLE orders
    COLUMNS TERMINATED BY ","
    (order_id, user_id, amount, order_time),

    DATA INFILE("oss://bucket/order_items/*.csv")
    INTO TABLE order_items
    COLUMNS TERMINATED BY ","
    (item_id, order_id, product_id, quantity, price)
)
WITH BROKER (...)
PROPERTIES ("timeout" = "7200");
```

---

## Storage System Configuration

### Alibaba Cloud OSS

```sql
WITH BROKER
(
    "fs.oss.accessKeyId" = "<AccessKey ID>",
    "fs.oss.accessKeySecret" = "<AccessKey Secret>",
    "fs.oss.endpoint" = "oss-cn-<region>-internal.aliyuncs.com"
)
```

**Caveats:**
- Use the internal endpoint (`-internal`) to avoid external traffic charges
- Ensure BE nodes can reach OSS over the internal network
- Prefer RAM-role authorization over AK/SK

### AWS S3

```sql
WITH BROKER
(
    "aws.s3.access_key" = "<access_key>",
    "aws.s3.secret_key" = "<secret_key>",
    "aws.s3.region" = "us-west-2"
)
```

### HDFS (broker-free)

```sql
-- Simple HDFS (no HA)
DATA INFILE("hdfs://<namenode>:8020/data/*.csv")
-- No WITH BROKER clause needed

-- HDFS HA
WITH BROKER
(
    "dfs.nameservices" = "my-ha-cluster",
    "dfs.ha.namenodes.my-ha-cluster" = "nn1,nn2",
    "dfs.namenode.rpc-address.my-ha-cluster.nn1" = "nn1_host:8020",
    "dfs.namenode.rpc-address.my-ha-cluster.nn2" = "nn2_host:8020",
    "dfs.client.failover.proxy.provider.my-ha-cluster" =
        "org.apache.hadoop.hdfs.server.namenode.ha.ConfiguredFailoverProxyProvider"
)
```

### Azure Blob Storage

```sql
WITH BROKER
(
    "azure.blob.storage_account" = "<account>",
    "azure.blob.shared_key" = "<key>"
)
-- File path: wasbs://<container>@<account>.blob.core.windows.net/path/
```

### Google Cloud Storage

```sql
WITH BROKER
(
    "gcp.gcs.service_account_email" = "<email>",
    "gcp.gcs.service_account_private_key_id" = "<key_id>",
    "gcp.gcs.service_account_private_key" = "<private_key>"
)
-- File path: gs://<bucket>/path/
```

---

## Format Parameters

### Parquet / ORC

- Automatically maps columns to table fields by name (case-insensitive)
- If column names don't match, use `(column_list)` + `SET` for mapping
- Separator does not need to be specified

```sql
-- Mapping when Parquet column names don't match
DATA INFILE("oss://bucket/data.parquet")
INTO TABLE target_table
FORMAT AS "parquet"
(src_col1, src_col2, src_col3)
SET (
    target_col1 = src_col1,
    target_col2 = CAST(src_col2 AS INT),
    target_col3 = src_col3
)
```

### CSV

| Parameter | Description |
|------|------|
| `COLUMNS TERMINATED BY` | Column separator; supports multi-character |
| `ROWS TERMINATED BY` | Row delimiter |
| `skip_header` | Number of header rows to skip (set in PROPERTIES) |
| `trim_space` | Trim leading/trailing whitespace in fields |
| `enclose` | Field enclosing character |
| `escape` | Escape character |

### JSON (v3.2.3+)

```sql
DATA INFILE("oss://bucket/data.json")
INTO TABLE target_table
FORMAT AS "json"
PROPERTIES (
    "jsonpaths" = '["$.id", "$.name", "$.info.age"]',
    "strip_outer_array" = "true"
)
```

---

## Data Transformation

Similar to Stream Load. Supports:
- Column mapping and renaming
- Expression computation via the SET clause
- Row filtering via the WHERE clause
- Extraction of partition fields from the path via COLUMNS FROM PATH AS
- The NEGATIVE keyword for reverse ingestion (Aggregate table scenarios; used to undo previously ingested data)

---

## Best Practices

### Timeout Settings

| Data volume | Recommended timeout |
|--------|-------------|
| < 10 GB | 3600 (1 hour) |
| 10~100 GB | 7200~14400 (2~4 hours) |
| > 100 GB | Estimate by throughput: `data volume (GB) / throughput (GB/h) × 3600 × 1.5` |

The FE parameter `broker_load_default_timeout_second` controls the default value (default 14400 = 4 hours).

### Concurrency Control
- FE parameter `max_broker_load_job_concurrency` controls the number of Broker Loads that can run simultaneously (default 5)
- Each Broker Load task is split into multiple sub-tasks distributed across BEs
- The BE parameter `pipeline_dop` affects the parallelism of each sub-task

### File Organization
- Use wildcards to match multiple files: `oss://bucket/data/2024/01/*/*.parquet`
- Each file is best at 128 MB ~ 1 GB; files that are too small increase scheduling overhead
- Parquet/ORC outperforms CSV — better compression ratio with columnar storage and automatic column mapping

### Memory Control
- BE parameter `load_process_max_memory_limit_percent` (default 30%) caps total ingestion memory
- Per-task limit via PROPERTIES `"exec_mem_limit"` (default 2 GB)
- Increase `exec_mem_limit` appropriately when ingesting large data volumes

---

## Monitoring and Management

**View ingestion status:**

```sql
-- View recent ingestion tasks
SHOW LOAD FROM mydb ORDER BY CreateTime DESC LIMIT 10;

-- View by label
SHOW LOAD FROM mydb WHERE LABEL = "oss_load_20240101";

-- View running tasks
SHOW LOAD FROM mydb WHERE STATE = "LOADING";
```

**Task state transitions:**
```
PENDING → LOADING → FINISHED / CANCELLED
```

**Cancel a task:**

```sql
CANCEL LOAD FROM mydb WHERE LABEL = "oss_load_20240101";
```

---

## Common Issues

| Issue | Cause | Resolution |
|------|------|---------|
| Task stays PENDING for a long time | Concurrency is maxed out | Wait, or increase `max_broker_load_job_concurrency` |
| CANCELLED due to `timeout` | Large data volume, slow network | Increase the `timeout` parameter |
| `ETL_QUALITY_UNSATISFIED` | Error rows exceed `max_filter_ratio` | `SHOW LOAD` and inspect tracking_url for error details |
| Parquet column mapping fails | Column-name case mismatch | Map explicitly with `(column_list)` |
| `RPC timed out` | write_buffer too large | Reduce `write_buffer_size` or increase `tablet_writer_rpc_timeout_sec` |
| OSS access fails | Endpoint or permission issue | Check that the endpoint uses the internal network and that AK/SK has OSS read permission |
