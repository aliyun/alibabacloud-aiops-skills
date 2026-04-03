---
title: PolarDB-X Range Partition Auto-Add Partitions
---

# PolarDB-X Range Partition Auto-Add Partitions

PolarDB-X leverages the TTL mechanism to provide automatic partition pre-creation for Range partitioned tables. Scheduled tasks automatically pre-create future Range partitions, preventing write failures due to insufficient partitions.

**Only applicable to time-type partition columns** (`DATE` / `DATETIME` / `TIMESTAMP`) Range partitioned tables. Auto-add partitions is not supported for integer-type partition columns (integer columns use the `EXPIRE OVER` strategy, which requires expired partitions to be cleaned up before new ones can be added — incompatible with add-only scenarios).

## Core Parameters

### TTL_EXPR (Partition Column)

Specify the partition column associated with auto-add partitions:

```
TTL_EXPR = `partition_column`
```

Only the partition column name needs to be declared; no need to specify `EXPIRE AFTER` or `TIMEZONE`.

### TTL_PART_INTERVAL (Partition Interval)

Define the time interval between adjacent Range partitions:

```
TTL_PART_INTERVAL = INTERVAL(int_value, interval_unit)
```

- `interval_unit` supports only: `DAY` / `MONTH` / `YEAR`.
- If not specified, defaults to monthly: `INTERVAL(1, MONTH)`.

### ARCHIVE_TABLE_PRE_ALLOCATE (Pre-creation Count)

Number of Range partitions pre-created by the scheduled task:

```
ARCHIVE_TABLE_PRE_ALLOCATE = int_number
```

Default values vary by partition interval:

| Partition Interval | Default Pre-creation Count | Description |
|---------|-----------|------|
| YEAR    | 1         | Pre-create 1 year's partitions |
| MONTH   | 2         | Pre-create 2 months' partitions |
| DAY     | 7         | Pre-create 7 days' partitions |

### TTL_CLEANUP (Whether to Clean Up Expired Partitions)

```
TTL_CLEANUP = 'ON' | 'OFF'
```

- `OFF` (recommended): Only pre-create new partitions; do not clean up old partitions. Suitable for add-only scenarios.
- `ON`: Scheduled task automatically drops expired partitions.

### TTL_JOB (Schedule)

No need to specify explicitly; use system defaults. Defaults to starting at 02:00 UTC+8 daily.

## First-Level Range Partition — Monthly Partitions

Applicable to scenarios where the time column is the first-level Range partition key:

```sql
-- 1. Create table: first-level RANGE COLUMNS partition
CREATE TABLE t_order (
  id BIGINT AUTO_INCREMENT,
  user_id BIGINT,
  amount DECIMAL(10,2),
  gmt_created DATETIME NOT NULL,
  PRIMARY KEY (id, gmt_created)
)
PARTITION BY RANGE COLUMNS(`gmt_created`) (
  PARTITION p20250401 VALUES LESS THAN ('2025-04-01'),
  PARTITION p20250501 VALUES LESS THAN ('2025-05-01'),
  PARTITION p20250601 VALUES LESS THAN ('2025-06-01')
);

-- 2. Configure TTL auto-add partitions (monthly, pre-create 2 months)
ALTER TABLE t_order
MODIFY TTL SET
  TTL_ENABLE = 'ON',
  TTL_CLEANUP = 'OFF',
  TTL_EXPR = `gmt_created`,
  TTL_PART_INTERVAL = INTERVAL(1, MONTH),
  ARCHIVE_TYPE = 'PARTITION',
  ARCHIVE_TABLE_PRE_ALLOCATE = 2;

-- 3. Immediately trigger auto-add partitions (WITH TTL_CLEANUP='OFF' forces add-only)
ALTER TABLE t_order CLEANUP EXPIRED DATA WITH TTL_CLEANUP = 'OFF';
```

Notes:

- `TTL_CLEANUP = 'OFF'` ensures partitions are only added, never dropped.
- Step 3 must be executed: the customer's table may only have initial time-range partitions; manually triggering immediately pre-creates missing future partitions without waiting for the next day's scheduled task.
- `WITH TTL_CLEANUP = 'OFF'` forces add-only at the statement level, even if the table's TTL definition has `TTL_CLEANUP = 'ON'`, preventing accidental deletion of old partitions.

## First-Level Range Partition — Daily Partitions

```sql
-- 1. Create table
CREATE TABLE t_log (
  id BIGINT AUTO_INCREMENT,
  log_content TEXT,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (id, created_at)
)
PARTITION BY RANGE COLUMNS(`created_at`) (
  PARTITION p20250601 VALUES LESS THAN ('2025-06-01'),
  PARTITION p20250602 VALUES LESS THAN ('2025-06-02'),
  PARTITION p20250603 VALUES LESS THAN ('2025-06-03')
);

-- 2. Configure TTL auto-add partitions (daily, pre-create 7 days)
ALTER TABLE t_log
MODIFY TTL SET
  TTL_ENABLE = 'ON',
  TTL_CLEANUP = 'OFF',
  TTL_EXPR = `created_at`,
  TTL_PART_INTERVAL = INTERVAL(1, DAY),
  ARCHIVE_TYPE = 'PARTITION',
  ARCHIVE_TABLE_PRE_ALLOCATE = 7;

-- 3. Immediately trigger auto-add partitions
ALTER TABLE t_log CLEANUP EXPIRED DATA WITH TTL_CLEANUP = 'OFF';
```

## Second-Level Range Subpartitions

Applicable to scenarios where the first level uses KEY/HASH for data distribution and the second level uses Range for time-based rolling management:

```sql
-- 1. Create table: KEY first-level + RANGE COLUMNS second-level
CREATE TABLE t_event (
  id BIGINT AUTO_INCREMENT,
  app_id BIGINT,
  payload TEXT,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (id, created_at)
)
PARTITION BY KEY(`id`) PARTITIONS 8
SUBPARTITION BY RANGE COLUMNS(`created_at`) (
  SUBPARTITION sp20250401 VALUES LESS THAN ('2025-04-01'),
  SUBPARTITION sp20250501 VALUES LESS THAN ('2025-05-01'),
  SUBPARTITION sp20250601 VALUES LESS THAN ('2025-06-01')
);

-- 2. Configure TTL auto-add subpartitions (monthly, pre-create 2 months)
ALTER TABLE t_event
MODIFY TTL SET
  TTL_ENABLE = 'ON',
  TTL_CLEANUP = 'OFF',
  TTL_EXPR = `created_at`,
  TTL_PART_INTERVAL = INTERVAL(1, MONTH),
  ARCHIVE_TYPE = 'SUBPARTITION',
  ARCHIVE_TABLE_PRE_ALLOCATE = 2;

-- 3. Immediately trigger auto-add partitions
ALTER TABLE t_event CLEANUP EXPIRED DATA WITH TTL_CLEANUP = 'OFF';
```

Notes:

- `ARCHIVE_TYPE = 'SUBPARTITION'` specifies that the automatically managed partitions are templated second-level Range subpartitions.
- First-level KEY partitions remain unchanged; second-level Range subpartitions roll automatically.

## Managing Auto-Add Partition Configuration

```sql
-- View TTL configuration
SHOW CREATE TABLE t_order;

-- Adjust pre-creation count
ALTER TABLE t_order MODIFY TTL SET ARCHIVE_TABLE_PRE_ALLOCATE = 6;

-- Adjust partition interval
ALTER TABLE t_order MODIFY TTL SET TTL_PART_INTERVAL = INTERVAL(1, DAY);

-- Pause auto-partition task
ALTER TABLE t_order MODIFY TTL SET TTL_ENABLE = 'OFF';

-- Resume auto-partition task
ALTER TABLE t_order MODIFY TTL SET TTL_ENABLE = 'ON';

-- Enable automatic cleanup of expired partitions
ALTER TABLE t_order MODIFY TTL SET TTL_CLEANUP = 'ON';

-- Disable cleanup (add-only, no delete)
ALTER TABLE t_order MODIFY TTL SET TTL_CLEANUP = 'OFF';

-- Manually trigger auto-add partitions (WITH TTL_CLEANUP='OFF' forces add-only)
ALTER TABLE t_order CLEANUP EXPIRED DATA WITH TTL_CLEANUP = 'OFF';

-- Remove TTL definition (if an archive table exists, drop it first)
ALTER TABLE t_order REMOVE TTL;
```

## Limitations

- **Only supports time-type partition columns**: `DATE` / `DATETIME` / `TIMESTAMP`. Integer-type partition columns are not supported (the `EXPIRE OVER` strategy requires old partitions to be cleaned up before adding new ones, conflicting with add-only scenarios).
- Only supports partitioned tables in **AUTO mode databases**.
- Partition-based archiving requires Enterprise Edition version 5.4.20+ (MySQL 5.7 requires `polardb-2.5.0_5.4.20-20250328` or later).
- Tables with partition-based archiving that have JOIN relationships with other tables may experience **JOIN computation pushdown failures** due to partition definition misalignment.
- When `TTL_CLEANUP = 'OFF'`, new partitions are still automatically added, but expired partitions are not dropped.
- After configuration, immediately execute `ALTER TABLE xxx CLEANUP EXPIRED DATA WITH TTL_CLEANUP = 'OFF'` to trigger pre-creation, instead of waiting for the next day's scheduled task. `WITH TTL_CLEANUP = 'OFF'` forces add-only at the statement level.
- Before removing a TTL definition, if an associated archive table exists, it must be dropped first.
