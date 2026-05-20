# INSERT INTO and Pipe Detailed Guide

## Table of Contents

1. [INSERT INTO Overview](#insert-into-overview)
2. [INSERT INTO VALUES](#insert-into-values)
3. [INSERT INTO SELECT](#insert-into-select)
4. [INSERT INTO SELECT FROM FILES()](#insert-into-select-from-files)
5. [INSERT OVERWRITE](#insert-overwrite)
6. [Pipe Continuous Ingestion](#pipe-continuous-ingestion)
7. [Best Practices](#best-practices)

---

## INSERT INTO Overview

INSERT INTO is the most flexible ingestion method, supporting multiple data sources:
- **VALUES**: write a small number of data rows directly
- **SELECT**: ingest from internal tables, external tables, or materialized views
- **SELECT FROM FILES()**: ingest from cloud-storage files (v3.1+)

Executes synchronously and returns the result immediately.

---

## INSERT INTO VALUES

**Applicable scenarios:** testing, demos, very small data writes.

```sql
INSERT INTO user_table (id, name, age, city)
VALUES
    (1, 'Alice', 30, 'Beijing'),
    (2, 'Bob', 25, 'Shanghai'),
    (3, 'Charlie', 35, 'Hangzhou');
```

**Note:** Do not use INSERT INTO VALUES at high frequency in production — each execution generates a new tablet version, which easily triggers TOO_MANY_VERSION.

---

## INSERT INTO SELECT

**Ingest from an internal table:**

```sql
-- Ingest from a staging table into the target table
INSERT INTO target_table
SELECT * FROM staging_table WHERE dt = '2024-01-01';

-- Ingest the aggregated result of one table into another
INSERT INTO daily_summary (dt, user_count, total_amount)
SELECT
    DATE(event_time) AS dt,
    COUNT(DISTINCT user_id),
    SUM(amount)
FROM order_detail
WHERE event_time >= '2024-01-01'
GROUP BY DATE(event_time);
```

**Ingest from an external table / catalog:**

```sql
-- Ingest from a Hive catalog
INSERT INTO starrocks_table
SELECT * FROM hive_catalog.hive_db.hive_table
WHERE dt = '2024-01-01';

-- Ingest from a JDBC catalog (MySQL)
INSERT INTO starrocks_table
SELECT * FROM jdbc_catalog.mysql_db.mysql_table
WHERE id > 1000;

-- Ingest from an Iceberg catalog
INSERT INTO starrocks_table
SELECT col1, col2, col3 FROM iceberg_catalog.db.iceberg_table;
```

**Memory control:**
- Controlled via the session variable `exec_mem_limit` (default 2GB)
- Increase appropriately for large data volumes: `SET exec_mem_limit = 8589934592;` (8GB)
- `query_timeout` controls the timeout (default 300s); increase for large data volumes

---

## INSERT INTO SELECT FROM FILES()

**v3.1+ feature:** ingest directly from cloud-storage files without creating an external table.

**Basic syntax:**

```sql
INSERT INTO target_table
SELECT * FROM FILES(
    "path" = "oss://bucket/data/2024/01/*.parquet",
    "format" = "parquet",
    "fs.oss.accessKeyId" = "<ak>",
    "fs.oss.accessKeySecret" = "<sk>",
    "fs.oss.endpoint" = "oss-cn-hangzhou-internal.aliyuncs.com"
);
```

**Supported storage systems:**
- Alibaba Cloud OSS: `oss://bucket/path/`
- AWS S3: `s3://bucket/path/`
- HDFS: `hdfs://namenode:port/path/`
- Azure: `wasbs://container@account.blob.core.windows.net/path/`
- GCS: `gs://bucket/path/`
- MinIO: `s3://bucket/path/` (with the endpoint parameter)

**Supported file formats:**
- Parquet (v3.1+)
- ORC (v3.1+)
- CSV (v3.3+)

**Column mapping and transformation:**

```sql
-- Select specific columns and transform them
INSERT INTO target_table (user_id, event_time, amount)
SELECT
    uid,
    CAST(ts AS DATETIME),
    price * quantity
FROM FILES(
    "path" = "oss://bucket/data/*.parquet",
    "format" = "parquet",
    ...
);
```

**Auto table creation (v3.2+):**

```sql
-- Automatically create the table based on the file schema
CREATE TABLE auto_table AS
SELECT * FROM FILES(
    "path" = "oss://bucket/data/sample.parquet",
    "format" = "parquet",
    ...
);
```

**FILES() vs Broker Load comparison:**

| Dimension | FILES() | Broker Load |
|------|---------|-------------|
| Execution mode | Sync | Async |
| Applicable scale | Flexible (don't run too large per batch) | Tens to hundreds of GB |
| SQL flexibility | High (JOIN, aggregation supported) | Simple mapping only |
| Transaction | Single table | Multi-table supported |
| Format support | Parquet/ORC/CSV | Parquet/ORC/CSV/JSON |
| Version requirement | v3.1+ | v2.x+ |

---

## INSERT OVERWRITE

**Atomically replace partition data:** writes into a temporary partition first and atomically swaps on success.

```sql
-- Overwrite a specific partition
INSERT OVERWRITE target_table PARTITION (p20240101)
SELECT * FROM staging_table WHERE dt = '2024-01-01';

-- Auto-inferred partitions (v3.2+)
INSERT OVERWRITE target_table
SELECT * FROM FILES(
    "path" = "oss://bucket/data/dt=2024-01-01/*.parquet",
    "format" = "parquet",
    ...
);
```

**Typical scenarios:**
- Daily full refresh of certain partitions
- T+1 report data refresh
- Data repair (re-ingest a day's data)

---

## Pipe Continuous Ingestion

### Overview

Pipe (v3.2+) is a long-running asynchronous ingestion mechanism that can automatically watch for new files in cloud storage and ingest them. Internally it is implemented using INSERT INTO SELECT FROM FILES().

**Key characteristics:**
- Automatically splits large file sets into smaller batches executed in order
- Supports `AUTO_INGEST=TRUE` for automatic discovery of new files
- Supports Parquet and ORC formats
- Suitable for continuous file ingestion at the 100 GB ~ TB scale

### Creation Syntax

```sql
CREATE PIPE [IF NOT EXISTS] <pipe_name>
PROPERTIES (
    "AUTO_INGEST" = "TRUE",
    "POLL_INTERVAL" = "60",    -- Scan interval in seconds (default 300; lower for frequent file arrivals)
    "BATCH_SIZE" = "1GB",      -- Data volume per batch
    "BATCH_FILES" = "256"      -- Number of files per batch
)
AS INSERT INTO target_table
SELECT * FROM FILES(
    "path" = "oss://bucket/data/incoming/*.parquet",
    "format" = "parquet",
    "fs.oss.accessKeyId" = "<ak>",
    "fs.oss.accessKeySecret" = "<sk>",
    "fs.oss.endpoint" = "oss-cn-hangzhou-internal.aliyuncs.com"
);
```

### File Discovery Mechanism

- **OSS/S3:** detects new/changed files via the file's ETag
- **HDFS:** detects via LastModifiedTime
- With `AUTO_INGEST=TRUE`, Pipe polls continuously; `POLL_INTERVAL` controls the interval
- Files already ingested are not re-ingested (deduplicated by file path + ETag)

### Management and Monitoring

```sql
-- List all pipes
SHOW PIPES;

-- View pipe details
SHOW PIPE mydb.my_pipe;

-- View file ingestion status
SELECT * FROM information_schema.pipe_files
WHERE pipe_name = 'my_pipe';

-- Suspend
SUSPEND PIPE mydb.my_pipe;

-- Resume
RESUME PIPE mydb.my_pipe;

-- Re-ingest a failed file
ALTER PIPE mydb.my_pipe RETRY FILE "oss://bucket/data/failed_file.parquet";

-- Drop
DROP PIPE mydb.my_pipe;
```

### Pipe vs Routine Load Comparison

| Dimension | Pipe | Routine Load |
|------|------|-------------|
| Data source | Files (OSS/S3/HDFS) | Kafka / Pulsar |
| Format | Parquet / ORC | CSV / JSON / Avro |
| Trigger | File arrival | Message arrival |
| Applicable scenarios | Continuous batch file ingestion | Streaming message consumption |
| Version requirement | v3.2+ | v2.x+ |

---

## Best Practices

### INSERT INTO Usage Recommendations

| Scenario | Recommendation |
|------|------|
| Testing/Demo | INSERT INTO VALUES with small data |
| Cross-table ETL | INSERT INTO SELECT with larger `exec_mem_limit` and `query_timeout` |
| Cloud-storage files | INSERT INTO SELECT FROM FILES() (v3.1+) |
| Partition data refresh | INSERT OVERWRITE for atomic replacement |
| High-frequency writes | Don't use INSERT INTO; switch to Stream Load or Routine Load |

### Pipe Usage Recommendations

- **File size:** 128 MB ~ 1 GB per file is optimal
- **BATCH_SIZE:** set based on cluster memory; 512 MB ~ 2 GB is recommended
- **POLL_INTERVAL:** 30~60s when file arrival is frequent, 300~600s when infrequent
- **Error handling:** periodically check `pipe_files` for files with `LOAD_STATE = 'ERROR'` and re-ingest with RETRY FILE
- **Note:** every Pipe batch generates a tablet version; with frequent small files watch out for compaction pressure
