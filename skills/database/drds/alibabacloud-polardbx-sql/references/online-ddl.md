---
title: PolarDB-X Online DDL and Lock-Free DDL Operations
---

# PolarDB-X Online DDL and Lock-Free DDL Operations

PolarDB-X Distributed Edition has extensively optimized DDL table-locking issues, including MDL lock preemption, MDL dual versioning, and lock-free column type changes. This document explains how to determine if a DDL locks the table, how to execute DDL in a lock-free manner, and long transaction checks before DDL execution.

## EXPLAIN ONLINE_DDL — Determine If DDL Locks the Table

Before executing DDL, use `EXPLAIN ONLINE_DDL` to predict whether the DDL will lock the table, without actually executing the DDL.

**Version requirement**: Instance version >= 5.4.20-20241224.

### Syntax

```sql
EXPLAIN ONLINE_DDL ALTER TABLE ...
```

### Return Fields

| Field | Meaning |
|------|------|
| DDL TYPE | `ONLINE_DDL` (no table lock) or `LOCK_TABLE` (locks table) |
| ALGORITHM | The execution algorithm the DDL will use |

### DDL TYPE and ALGORITHM Reference

| DDL TYPE | ALGORITHM | Description | Business Impact |
|----------|-----------|------|-----------|
| ONLINE_DDL | INSTANT / META_ONLY / DEFAULT | Metadata-only change, completes in seconds | Small |
| ONLINE_DDL | INPLACE / OMC / OSC | No table lock but duration depends on data volume, consumes some disk/IO/CPU resources | Small |
| LOCK_TABLE | COPY | Locks table, table is not writable during execution | Large |

### Examples

```sql
-- Add column: INSTANT, completes in seconds, no table lock
EXPLAIN ONLINE_DDL ALTER TABLE t1 ADD COLUMN d int;
-- Result: DDL TYPE = ONLINE_DDL, ALGORITHM = INSTANT

-- Modify column type: COPY, locks table
EXPLAIN ONLINE_DDL ALTER TABLE t1 MODIFY COLUMN c bigint;
-- Result: DDL TYPE = LOCK_TABLE, ALGORITHM = COPY

-- Add partition: META_ONLY, completes in seconds, no table lock
EXPLAIN ONLINE_DDL ALTER TABLE t1 ADD PARTITION (PARTITION p2 VALUES LESS THAN (2000000));
-- Result: DDL TYPE = ONLINE_DDL, ALGORITHM = META_ONLY
```

## Lock-Free DDL Execution Strategy

Handle based on `EXPLAIN ONLINE_DDL` results:

1. **DDL TYPE = ONLINE_DDL**: Execute the original SQL directly; it won't lock the table.
2. **DDL TYPE = LOCK_TABLE**: Specify `ALGORITHM=OMC` to enable lock-free column type change.

### ALGORITHM=OMC Lock-Free Column Type Change

For ALTER TABLE operations that would lock the table (e.g., modifying column types), specify `ALGORITHM=OMC` in the SQL to avoid table locking:

```sql
-- Original SQL would lock the table
EXPLAIN ONLINE_DDL ALTER TABLE t1 MODIFY COLUMN b text;
-- Result: DDL TYPE = LOCK_TABLE, ALGORITHM = COPY

-- After specifying OMC, no table lock
EXPLAIN ONLINE_DDL ALTER TABLE t1 MODIFY COLUMN b text, ALGORITHM=OMC;
-- Result: DDL TYPE = ONLINE_DDL, ALGORITHM = OMC

-- After confirming lock-free, execute
ALTER TABLE t1 MODIFY COLUMN b text, ALGORITHM=OMC;
```

**Note**: OMC executes slower and consumes more resources; only use it when you need to avoid table locking. Prefer native Online DDL.

## Check Long Transactions Before DDL

Even if the DDL itself doesn't lock the table, **uncommitted long transactions or large queries** on the target table may still cause issues.

### PolarDB-X MDL Optimizations

PolarDB-X has two key optimizations for MDL locks:

1. **Preemptive MDL lock**: Guarantees the DDL can acquire the MDL lock within a deterministic time frame (default 15s), solving the problem of DDL being unable to execute for extended periods.
2. **Dual-version MDL lock**: Introduces a dual-version metadata mechanism where new transactions access new metadata, preventing new transactions from being blocked.

**Side effect**: By default, connections with long transactions or large queries exceeding 15 seconds will be killed. If you have important data sync tasks (DataWorks/DTS/mysqldump, etc.), avoid performing DDL during those task executions.

### Check Long Transactions via POLARDBX_TRX View

Query all transactions with duration exceeding 15 seconds:

```sql
SELECT
    TRX_ID AS 'Transaction ID',
    PROCESS_ID AS 'Connection ID',
    SCHEMA AS 'Database',
    START_TIME AS 'Transaction Start Time',
    ROUND(DURATION_TIME / 1000 / 1000, 3) AS 'Duration (seconds)',
    ROUND(ACTIVE_TIME / 1000 / 1000, 3) AS 'Active Time (seconds)',
    ROUND(IDLE_TIME / 1000 / 1000, 3) AS 'Idle Time (seconds)',
    SQL AS 'Current SQL'
FROM
    INFORMATION_SCHEMA.POLARDBX_TRX
WHERE
    DURATION_TIME > 15 * 1000 * 1000;
```

Field descriptions:
- **Duration**: Total elapsed time from transaction start to now.
- **Active Time**: Total time the database actually spent processing the transaction.
- **Idle Time**: Total time the client was not interacting with the database during the transaction (typically client-side business logic processing time).

### Check Transaction MDL via METADATA_LOCK View

After locating a long transaction, check which tables it holds MDL locks on:

```sql
SELECT
    LOWER(HEX(TRX_ID)) AS 'Transaction ID',
    CONN_ID AS 'Connection ID',
    SUBSTRING_INDEX(SUBSTRING_INDEX(`TABLE`, '#', 1), '.', 1) AS 'Database',
    SUBSTRING_INDEX(SUBSTRING_INDEX(`TABLE`, '#', 1), '.', -1) AS 'Table Name',
    SUBSTRING_INDEX(FRONTEND, '@', 1) AS 'Username',
    SUBSTRING_INDEX(FRONTEND, '@', -1) AS 'Client IP',
    TYPE AS 'MDL Type'
FROM
    INFORMATION_SCHEMA.METADATA_LOCK
WHERE
    `TABLE` NOT LIKE 'tablegroupid%'
    AND LOWER(HEX(TRX_ID)) = '<transaction_id>';
```

### Long Transaction Decision Before DDL

| Long Transaction Situation | Recommended Action |
|-----------|---------|
| Long transaction is unexpected | Investigate business logic, resolve before executing DDL |
| Long transaction is expected and high priority | Postpone DDL to avoid business impact |
| Long transaction is expected but low priority | Can execute DDL, but the DDL process will kill the long transaction connection |

## Recommended DDL Execution Workflow

> **Important**: DDL is a high-risk operation. Before actually executing any DDL statement, you **must present the DDL statement, EXPLAIN ONLINE_DDL results, and long transaction check results to the user and obtain explicit confirmation before execution**. Never execute DDL directly without user confirmation.

```
1. EXPLAIN ONLINE_DDL ALTER TABLE ...
   |
   |-- ONLINE_DDL -> Execute directly
   |-- LOCK_TABLE -> Rewrite with ALGORITHM=OMC and re-EXPLAIN to confirm
   |
2. Check long transactions on the target table (POLARDBX_TRX + METADATA_LOCK)
   |
3. Present all information to the user and obtain explicit confirmation
   |
4. Execute DDL after confirming it's safe
```

## View DDL Execution Progress

For long-running DDL operations (such as OMC, INPLACE, OSC involving data backfill), monitor execution progress in real-time via the `INFORMATION_SCHEMA.DDL_PROGRESS` view:

```sql
SELECT * FROM INFORMATION_SCHEMA.DDL_PROGRESS;
```

| Field | Description |
|------|------|
| JOB_ID | DDL task ID |
| BACKFILL_ID | Data backfill task ID |
| TABLE_SCHEMA | Database name |
| TABLE_NAME | Table name |
| STATE | Current execution state |
| PROGRESS | Execution progress percentage |
| FINISHED_ROWS | Number of completed rows |
| APPROXIMATE_TOTAL_ROWS | Estimated total rows |
| CURRENT_SPEED | Current execution speed (rows/second) |
| AVERAGE_SPEED | Average execution speed (rows/second) |
| CHECK_PROGRESS | Verification progress |
| START_TIME | Start time |
| UPDATE_TIME | Last update time |
| DDL_STMT | DDL statement |

When users execute a long-running DDL and ask about progress, use this view.

## DMS Lock-Free Changes

PolarDB-X's lock-free column type change feature is integrated into DMS (Data Management Service)'s lock-free change module. When using DMS, the system automatically determines whether the DDL has table-locking risks and intelligently selects the optimal execution strategy.

- Entry: DMS Console > Database Development > Data Changes > Lock-Free Changes
- Once enabled, both regular data change orders and lock-free change orders prioritize lock-free execution
- Version requirement: Instance version >= 5.4.20-20241224

## Legacy Version Compatibility

For instance versions below 5.4.20-20241224:

- Refer to the official Online DDL documentation to determine if DDL locks the table.
- For ALTER TABLE types, append `LOCK=NONE` to the statement for testing:
  - Executes normally -> The operation is Online and doesn't lock the table.
  - Returns an error -> The operation doesn't support Online execution and will lock the table.
- It's recommended to verify on a test instance or test table.

## FAQ

**Q: Why isn't OMC the default execution strategy for ALTER TABLE?**

While OMC avoids table locking, it executes slower and consumes more resources. In most scenarios, prefer MySQL-native Online DDL; only choose OMC when you need to avoid table locking.

**Q: How to speed up DDL execution?**

PolarDB-X supports parallel DDL functionality. When hardware resources are idle, you can adjust DDL concurrency to accelerate execution and shorten the change window.
