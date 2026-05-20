# Materialized Views

## Table of Contents

1. [Sync MV vs Async MV](#sync-mv-vs-async-mv)
2. [Sync Materialized Views (Rollup)](#sync-materialized-views-rollup)
3. [Async Materialized Views](#async-materialized-views)
4. [Query Rewrite](#query-rewrite)
5. [MV Operations and Management](#mv-operations-and-management)
6. [Common Pitfalls and Limitations](#common-pitfalls-and-limitations)

---

## Sync MV vs Async MV

| Feature | Sync MV (Rollup) | Async MV |
|------|---------------------|-------------|
| Data consistency | Strong consistency (real-time sync with base table) | Eventual consistency (per refresh strategy) |
| Supported table count | Single table only | Supports multi-table JOIN |
| External table support | Not supported | Supported (Hive/Iceberg, etc.) |
| Aggregate functions | SUM, MIN, MAX, COUNT, BITMAP_UNION, HLL_UNION | All aggregate functions |
| JOIN | Not supported | Supported |
| Window functions | Not supported | Supported |
| Refresh method | Automatic real-time sync | Manual / scheduled / triggered |
| Creation syntax | `CREATE MATERIALIZED VIEW ... AS SELECT` | `CREATE MATERIALIZED VIEW ... REFRESH ... AS SELECT` |
| Use case | Single-table pre-aggregation (PV/UV/SUM) | Multi-table JOIN, complex query acceleration |
| Version requirement | All versions | v2.4+ (v3.0+ recommended) |

**Decision guide:**
- Single-table simple aggregation + strong consistency required -> Sync MV
- Multi-table JOIN / complex query / latency acceptable -> Async MV
- External table data acceleration -> Async MV

---

## Sync Materialized Views (Rollup)

### Creation Syntax

```sql
-- Create a sync MV for a Duplicate Key table
CREATE MATERIALIZED VIEW mv_daily_sales
AS
SELECT
    dt,
    product_id,
    SUM(quantity) AS total_quantity,
    SUM(amount) AS total_amount,
    COUNT(*) AS order_count
FROM order_detail
GROUP BY dt, product_id;
```

### Supported Aggregate Functions

| Aggregate function | Notes |
|---------|------|
| `SUM` | Sum |
| `MIN` | Minimum |
| `MAX` | Maximum |
| `COUNT` | Count |
| `BITMAP_UNION` | BITMAP aggregation (for exact deduplication) |
| `HLL_UNION` | HLL aggregation (for approximate deduplication) |
| `PERCENTILE_UNION` | Percentile aggregation |

### Automatic Query Rewrite

Sync MV rewrite is fully automatic and transparent:

```sql
-- Original query -> optimizer automatically rewrites to read from the MV
SELECT dt, SUM(amount) FROM order_detail
WHERE dt = '2024-01-15'
GROUP BY dt;
-- Actual execution: reads from mv_daily_sales rather than scanning the base table

-- Use EXPLAIN to verify whether the MV was hit
EXPLAIN SELECT dt, SUM(amount) FROM order_detail
WHERE dt = '2024-01-15' GROUP BY dt;
-- Check whether the output contains rollup: mv_daily_sales
```

---

## Async Materialized Views

### Creation Syntax

```sql
-- Basic syntax
CREATE MATERIALIZED VIEW mv_name
[COMMENT 'description']
[PARTITION BY partition_expr]
[DISTRIBUTED BY HASH(column) [BUCKETS N]]
[REFRESH refresh_strategy]
[PROPERTIES ("key"="value", ...)]
AS
SELECT ...;
```

### Refresh Strategies

```sql
-- 1. Manual refresh (default)
CREATE MATERIALIZED VIEW mv_report
REFRESH MANUAL
AS SELECT ...;
-- Trigger manually: REFRESH MATERIALIZED VIEW mv_report;

-- 2. Scheduled refresh
CREATE MATERIALIZED VIEW mv_report
REFRESH ASYNC EVERY (INTERVAL 1 HOUR)
AS SELECT ...;

-- 3. Partition-based scheduled refresh (incremental refresh)
CREATE MATERIALIZED VIEW mv_report
PARTITION BY dt
REFRESH ASYNC EVERY (INTERVAL 1 HOUR)
AS
SELECT dt, region, SUM(amount)
FROM orders
GROUP BY dt, region;
-- Only refreshes partitions whose data has changed

-- 4. Set refresh time range (only refresh the most recent N partitions)
CREATE MATERIALIZED VIEW mv_report
PARTITION BY dt
REFRESH ASYNC EVERY (INTERVAL 1 HOUR)
PROPERTIES (
    "partition_refresh_number" = "3"  -- refresh at most 3 partitions per run
)
AS SELECT ...;
```

### Multi-Table JOIN MV

```sql
-- Wide-table materialized view: fact table JOINed with dimension tables
CREATE MATERIALIZED VIEW mv_order_wide
PARTITION BY dt
DISTRIBUTED BY HASH(order_id) BUCKETS 16
REFRESH ASYNC EVERY (INTERVAL 30 MINUTE)
AS
SELECT
    o.dt,
    o.order_id,
    o.user_id,
    o.amount,
    u.name AS user_name,
    u.region,
    p.product_name,
    p.category
FROM orders o
JOIN users u ON o.user_id = u.user_id
JOIN products p ON o.product_id = p.product_id;
```

### External Table MV (Data Lake Acceleration)

```sql
-- Accelerate Hive table data
CREATE MATERIALIZED VIEW mv_hive_summary
PARTITION BY dt
REFRESH ASYNC EVERY (INTERVAL 1 HOUR)
AS
SELECT dt, region, SUM(revenue) AS total_revenue
FROM hive_catalog.db.sales_table
GROUP BY dt, region;

-- Accelerate Iceberg table data
CREATE MATERIALIZED VIEW mv_iceberg_agg
REFRESH ASYNC EVERY (INTERVAL 2 HOUR)
AS
SELECT event_date, COUNT(*) AS event_count
FROM iceberg_catalog.db.events
GROUP BY event_date;
```

---

## Query Rewrite

### Conditions for Rewrite

For an async MV, Query Rewrite requires:

| Condition | Notes |
|------|------|
| MV is Active | In `SHOW MATERIALIZED VIEWS`, is_active = true |
| Data freshness | Some staleness is allowed by default; configurable via `query_rewrite_consistency` |
| Query is coverable | The query's tables, columns, aggregates, and JOINs can be covered by the MV |
| Rewrite switch is on | `enable_materialized_view_rewrite = true` (default on) |

### Rewrite Modes

```sql
-- 1. Default: rewrite only when MV data is fresh
SET materialized_view_rewrite_mode = 'default';

-- 2. Force rewrite: rewrite even if MV data may be stale (trade consistency for performance)
SET materialized_view_rewrite_mode = 'force';

-- 3. Disable rewrite
SET materialized_view_rewrite_mode = 'disable';
```

### Verifying Rewrite

```sql
-- Use EXPLAIN to check
EXPLAIN SELECT region, SUM(amount)
FROM orders
WHERE dt >= '2024-01-01'
GROUP BY region;

-- Check whether the output contains the MV name
-- If rewrite takes effect, you will see something like:
-- TABLE: mv_order_summary
-- instead of the original table name
```

### Common Reasons for Rewrite Failure

| Reason | Resolution |
|------|---------|
| Query contains columns not in the MV | Add the corresponding columns to the MV definition |
| Aggregate function in the query not supported by the MV | Adjust the MV definition or the SQL |
| Query's WHERE range exceeds the MV's partitions | Extend the MV's partition range |
| MV is inactive | Check refresh status, fix issues, then `ALTER MATERIALIZED VIEW mv_name ACTIVE` |
| Query uses non-deterministic functions | Avoid `now()`, `random()`, etc. in queries |

---

## MV Operations and Management

### View MV Status

```sql
-- List all materialized views
SHOW MATERIALIZED VIEWS;

-- View details
SHOW MATERIALIZED VIEWS LIKE 'mv_name';

-- Show the CREATE statement
SHOW CREATE MATERIALIZED VIEW mv_name;

-- View refresh history
SELECT * FROM information_schema.task_runs
WHERE task_name LIKE '%mv_name%'
ORDER BY create_time DESC
LIMIT 10;
```

### Manual Refresh

```sql
-- Full refresh
REFRESH MATERIALIZED VIEW mv_name;

-- Refresh specified partitions
REFRESH MATERIALIZED VIEW mv_name
PARTITION START('2024-01-01') END('2024-01-02');

-- Force refresh (even if no data changed)
REFRESH MATERIALIZED VIEW mv_name FORCE;

-- Wait synchronously for refresh to complete
REFRESH MATERIALIZED VIEW mv_name WITH SYNC MODE;
```

### Modifying an MV

```sql
-- Change the refresh strategy
ALTER MATERIALIZED VIEW mv_name
REFRESH ASYNC EVERY (INTERVAL 2 HOUR);

-- Change properties
ALTER MATERIALIZED VIEW mv_name
SET ("partition_refresh_number" = "5");

-- Pause/resume refresh
ALTER MATERIALIZED VIEW mv_name INACTIVE;   -- pause
ALTER MATERIALIZED VIEW mv_name ACTIVE;     -- resume

-- Drop
DROP MATERIALIZED VIEW mv_name;
-- For a sync MV, use:
DROP MATERIALIZED VIEW mv_name ON table_name;
```

---

## Common Pitfalls and Limitations

| Pitfall | Notes | Resolution |
|------|------|---------|
| MV definition contains `now()` | Refresh results are unstable | Use a business time column instead |
| MV partition key inconsistent with the base table | Cannot refresh incrementally; only full refresh | The MV's partition key must map to the base table's partition column |
| External-table MV cannot detect data changes | Always full refresh | Set a reasonable refresh interval |
| Too many MVs cause refresh resource contention | Refresh tasks queue and time out | Limit MV count; stagger refresh times |
| Refresh failure causes data staleness | Query Rewrite falls back to the base table | Monitor refresh status; set alerts |
| Base table schema change for a multi-table JOIN MV | MV becomes inactive | Rebuild the MV |
| MV query rewrite produces results different from the original query | Data staleness or incomplete MV coverage | Validate MV data; verify rewrite logic |

### MV Design Recommendations

1. **Design by query frequency:** Prioritize MVs for high-frequency queries; low-frequency queries aren't worth it.
2. **Limit MV count:** Recommend no more than 5 MVs per base table.
3. **Partition alignment:** Keep MV partition granularity equal to or coarser than the base table (day -> month).
4. **Monitor refreshes:** Periodically verify refresh success and acceptable latency.
5. **Reserve extra columns:** Include a few extra dimension columns in the MV to cover more query patterns.
