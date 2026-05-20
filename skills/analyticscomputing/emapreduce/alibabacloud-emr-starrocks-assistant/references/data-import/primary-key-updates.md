# Primary Key Table Update Modes Guide

## Table of Contents

1. [Overview](#overview)
2. [UPSERT Mode](#upsert-mode)
3. [DELETE Mode](#delete-mode)
4. [Partial Column Update](#partial-column-update)
5. [Conditional Update](#conditional-update)
6. [Update Configuration per Ingestion Method](#update-configuration-per-ingestion-method)
7. [Best Practices](#best-practices)

---

## Overview

StarRocks Primary Key tables support row-level updates and deletes during ingestion, suitable for CDC sync, dimension table updates, real-time data corrections, and similar scenarios.

**Supported operations:**
- **UPSERT**: update if exists, insert if not (default behavior)
- **DELETE**: delete rows by primary key
- **Partial column update**: update only the specified columns; the rest remain unchanged
- **Conditional update**: update only when a condition is met

**Supported ingestion methods:**
- Stream Load
- Broker Load
- Routine Load
- Flink Connector / Kafka Connector

**Methods that do not support update operations:**
- Spark Load
- INSERT INTO (implemented via SQL semantics, not the `__op` mechanism)

---

## UPSERT Mode

UPSERT is the default ingestion behavior for Primary Key tables — no extra configuration is required.

**How it works:**
- Ingested data is matched against existing rows by primary key
- Primary key exists -> update the entire row
- Primary key does not exist -> insert a new row

**Stream Load example:**

```bash
# UPSERT by default; no extra parameters needed
curl --location-trusted -u root: \
    -H "label:upsert_20240101" \
    -H "column_separator:," \
    -T /data/user_updates.csv \
    http://fe_host:8030/api/mydb/user_table/_stream_load
```

---

## DELETE Mode

Use the `__op` field to mark a delete operation. `__op = 0` means UPSERT, `__op = 1` means DELETE.

### Option 1: data contains an __op column

**CSV data:**
```
1,Alice,30,0
2,Bob,25,1
3,Charlie,35,0
```

**Stream Load:**

```bash
curl --location-trusted -u root: \
    -H "label:upsert_delete_20240101" \
    -H "column_separator:," \
    -H "columns:id, name, age, __op" \
    -T /data/cdc_data.csv \
    http://fe_host:8030/api/mydb/user_table/_stream_load
```

### Option 2: the entire batch is DELETE

```bash
# The whole batch is deletes; specify via Header
curl --location-trusted -u root: \
    -H "label:delete_batch" \
    -H "column_separator:," \
    -H "columns:id, name, age" \
    -H "__op:1" \
    -T /data/delete_keys.csv \
    http://fe_host:8030/api/mydb/user_table/_stream_load
```

### DELETE with JSON Format

```json
// JSON data contains the __op field directly
[
    {"id": 1, "name": "Alice", "age": 30, "__op": 0},
    {"id": 2, "__op": 1}
]
```

```bash
curl --location-trusted -u root: \
    -H "format:json" \
    -H "strip_outer_array:true" \
    -H "columns:id, name, age, __op" \
    -T /data/cdc_data.json \
    http://fe_host:8030/api/mydb/user_table/_stream_load
```

---

## Partial Column Update

Update only the specified columns; columns not specified keep their original values. Suited for scenarios where different data sources update different columns.

### Row Mode (default, v3.0+)

Suitable when only a few columns are being updated. During ingestion, the original row is read, merged with the new values, and written.

**Stream Load:**

```bash
# Update only the age column; other columns unchanged
curl --location-trusted -u root: \
    -H "label:partial_update_age" \
    -H "column_separator:," \
    -H "partial_update:true" \
    -H "columns:id, age" \
    -T /data/age_updates.csv \
    http://fe_host:8030/api/mydb/user_table/_stream_load
```

**Note:** the data must contain all primary key columns.

**Routine Load:**

```sql
CREATE ROUTINE LOAD mydb.partial_update_job ON user_table
COLUMNS (id, score)
PROPERTIES (
    "partial_update" = "true",
    "desired_concurrent_number" = "3"
)
FROM KAFKA (...);
```

### Column Mode (v3.1+)

Suitable when the table has many columns but only a few need to be updated. Incremental column data is appended directly and merged during compaction.

**Stream Load:**

```bash
curl --location-trusted -u root: \
    -H "label:column_mode_update" \
    -H "column_separator:," \
    -H "partial_update:true" \
    -H "partial_update_mode:column" \
    -H "columns:id, score" \
    -T /data/score_updates.csv \
    http://fe_host:8030/api/mydb/user_table/_stream_load
```

### Row Mode vs Column Mode

| Dimension | Row mode | Column mode |
|------|---------|------------|
| Write overhead | Higher (requires reading the original row) | Lower (direct append) |
| Read performance | No impact | Slight impact before compaction |
| Suitable column count | Fewer table columns | Many table columns, few updated |
| Version requirement | v3.0+ | v3.1+ |
| Special restrictions | None | Not supported on Aggregate tables |

---

## Conditional Update

Performs the update only when a condition is met — useful for guaranteeing data ordering (only allow updates from newer data).

**Stream Load:**

```bash
# Update only when the ingested data's update_time > the existing row's update_time
curl --location-trusted -u root: \
    -H "label:conditional_update" \
    -H "column_separator:," \
    -H "merge_condition:update_time" \
    -H "columns:id, name, score, update_time" \
    -T /data/updates.csv \
    http://fe_host:8030/api/mydb/user_table/_stream_load
```

**How it works:**
- `merge_condition` specifies a column name
- During ingestion, compare new vs. old values: update only when new > old
- Rows that do not satisfy the condition are skipped (not counted as error rows)

**Routine Load:**

```sql
CREATE ROUTINE LOAD mydb.conditional_load ON user_table
COLUMNS (id, name, score, update_time)
PROPERTIES (
    "merge_condition" = "update_time"
)
FROM KAFKA (...);
```

**Typical scenarios:**
- CDC data arrives out of order; use `update_time` to ensure only the latest version is written
- Multiple sources writing to the same table; use a version number to prevent old data from overwriting new

---

## Update Configuration per Ingestion Method

### Stream Load

| Feature | Parameter (HTTP Header) |
|------|-------------------|
| UPSERT | Default; no configuration |
| DELETE (whole batch) | `__op: 1` |
| DELETE (mixed) | `columns: ..., __op` |
| Partial column update | `partial_update: true` + `columns: primary key, updated columns` |
| Column mode | `partial_update: true` + `partial_update_mode: column` |
| Conditional update | `merge_condition: column name` |

### Broker Load

```sql
LOAD LABEL mydb.broker_upsert
(
    DATA INFILE("oss://bucket/data.csv")
    INTO TABLE pk_table
    COLUMNS TERMINATED BY ","
    (id, name, age, __op)
)
WITH BROKER (...)
PROPERTIES ("partial_update" = "true");  -- Partial column update is set in PROPERTIES
```

### Routine Load

```sql
CREATE ROUTINE LOAD mydb.pk_update ON pk_table
COLUMNS (id, name, age, __op)
PROPERTIES (
    "partial_update" = "true",           -- Partial column update
    "merge_condition" = "update_time"    -- Conditional update
)
FROM KAFKA (...);
```

### Flink Connector

```sql
-- Flink SQL: automatically handles INSERT/UPDATE/DELETE events
-- Primary Key table + Flink CDC -> automatic UPSERT/DELETE
CREATE TABLE sr_sink (
    id BIGINT,
    name STRING,
    PRIMARY KEY (id) NOT ENFORCED
) WITH (
    'connector' = 'starrocks',
    ...
    'sink.properties.partial_update' = 'true',      -- Partial column update
    'sink.properties.merge_condition' = 'update_ts'  -- Conditional update
);
```

---

## Best Practices

### UPSERT / DELETE Scenarios

| Scenario | Recommended configuration |
|------|---------|
| CDC full-column sync | Default UPSERT; `columns` includes `__op` |
| CDC partial column sync | `partial_update = true` + only pass the changed columns |
| Full refresh of a dimension table | INSERT OVERWRITE or default UPSERT |
| Guarantee ordering | `merge_condition` on a time/version column |
| Bulk delete | `__op: 1` or DELETE SQL |

### Performance Caveats

- **Partial column update (Row mode)** requires reading back the original row; write performance is 30~50% lower than full-column UPSERT
- **Partial column update (Column mode)** writes are fast but compaction load increases
- **Conditional update** requires reading the original row for comparison; slight impact on write performance
- **DELETE operations** in Primary Key tables are tombstones; they are truly purged during compaction
- Primary Key table write performance is roughly 50~70% of Duplicate Key tables (because of primary-key index maintenance)

### Patterns to Avoid

| Anti-pattern | Consequence | Correct approach |
|--------|------|---------|
| Using `__op` on a non-Primary Key table | No effect, ignored | Confirm the target table uses the Primary Key table model |
| Partial column update without the primary key | Ingestion fails | `columns` must include all primary key columns |
| High-frequency small-batch DELETE | Version buildup | Batch the deletes, or use `DELETE FROM table WHERE ...` |
| Out-of-order data without `merge_condition` | Old data overwrites new | Set `merge_condition` to ensure ordering |
| `partial_update=true` set with the intent of enabling DELETE handling | DELETEs are still ignored — `partial_update` controls partial-column UPSERT, not DELETE | Remove `partial_update=true` unless you actually want partial-column UPSERT; DELETE is signaled exclusively via `__op` (column or batch header). Flag the misconfiguration even though the config parses cleanly. |
