---
title: PolarDB-X TTL Tables and Cold Data Archiving
---

# PolarDB-X TTL Tables and Cold Data Archiving

TTL (Time-to-Live) tables provide automatic data lifecycle management in PolarDB-X. Define data expiration rules based on time columns, and the system periodically cleans up expired data automatically, with optional archiving of cold data to low-cost storage (OSS).

## TTL Definition

A TTL definition consists of three parts:

### TTL_EXPR (Required)

Defines the data survival time condition:

```
TTL_EXPR = `time_column` EXPIRE AFTER expiration_interval TIMEZONE 'timezone'
```

Supported expiration intervals: `N YEAR` / `N MONTH` / `N DAY`.

### TTL_JOB (Optional)

Defines the cleanup task scheduling plan:

```
TTL_JOB = CRON 'cron_expression' TIMEZONE 'timezone'
```

Defaults to executing daily at 1:00 AM.

### Archive Table (Optional)

Archive table for cold data archiving to OSS. See the cold data archiving documentation for details.

## Creating a TTL Table

```sql
CREATE TABLE t_order (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT,
  amount DECIMAL(10,2),
  gmt_modified DATETIME NOT NULL
) PARTITION BY KEY(id) PARTITIONS 16
TTL = TTL_DEFINITION (
  TTL_EXPR = `gmt_modified` EXPIRE AFTER 3 MONTH TIMEZONE '+08:00'
);
```

With a custom cleanup schedule:

```sql
CREATE TABLE t_log (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  log_content TEXT,
  created_at DATETIME NOT NULL
) PARTITION BY KEY(id) PARTITIONS 8
TTL = TTL_DEFINITION (
  TTL_EXPR = `created_at` EXPIRE AFTER 30 DAY TIMEZONE '+08:00'
  TTL_JOB = CRON '0 0 2 * * ?' TIMEZONE '+08:00'
);
```

## TTL Combined with CCI

CCI (Clustered Columnar Index) can be combined with TTL tables for hot/cold data separation:
- **Hot data**: In the row-store partitioned table, supporting high-performance OLTP operations.
- **Cold data**: Archived to columnar storage (object storage) via CCI, reducing storage costs while retaining analytical query capabilities.

```sql
CREATE TABLE t_order (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT,
  amount DECIMAL(10,2),
  gmt_modified DATETIME NOT NULL,
  CLUSTERED COLUMNAR INDEX cci_user(user_id) PARTITION BY KEY(user_id) PARTITIONS 16
) PARTITION BY KEY(id) PARTITIONS 16
TTL = TTL_DEFINITION (
  TTL_EXPR = `gmt_modified` EXPIRE AFTER 6 MONTH TIMEZONE '+08:00'
);
```

## Managing TTL Definitions

```sql
-- View TTL definition for a table
SHOW CREATE TABLE t_order;

-- Modify TTL expiration time
ALTER TABLE t_order
  MODIFY TTL SET TTL_EXPR = `gmt_modified` EXPIRE AFTER 6 MONTH TIMEZONE '+08:00';

-- Remove TTL definition (if an archive table exists, drop it first)
ALTER TABLE t_order REMOVE TTL;
```

## Limitations

- TTL time columns must be `DATE` / `DATETIME` / `TIMESTAMP` types.
- Before removing a TTL definition, if an associated archive table exists, it must be dropped first.
- TTL cleanup tasks run asynchronously in the background; data is not deleted instantly upon expiration.
