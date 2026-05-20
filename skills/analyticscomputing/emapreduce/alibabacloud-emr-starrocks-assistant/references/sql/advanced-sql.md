# Advanced SQL Features

## Table of Contents

1. [External Catalog Federated Queries](#external-catalog-federated-queries)
2. [Resource Group Resource Isolation](#resource-group-resource-isolation)
3. [UDF User-Defined Functions](#udf-user-defined-functions)
4. [Generated Columns](#generated-columns)
5. [Dictionary Objects](#dictionary-objects)
6. [AUTO_INCREMENT Columns](#auto_increment-columns)
7. [Execution Plans and EXPLAIN](#execution-plans-and-explain)
8. [Query Cache](#query-cache)
9. [SET_VAR Hint](#set_var-hint)

---

## External Catalog Federated Queries

An External Catalog lets you query external data sources directly without importing the data.

### Supported Catalog Types

| Catalog | Data source | Version |
|---------|--------|---------|
| `hive_catalog` | Hive / HMS | v2.3+ |
| `iceberg_catalog` | Iceberg | v2.4+ |
| `hudi_catalog` | Hudi | v2.4+ |
| `deltalake_catalog` | Delta Lake | v2.5+ |
| `jdbc_catalog` | MySQL / PostgreSQL | v2.3+ |
| `elasticsearch_catalog` | Elasticsearch | v3.1+ |
| `paimon_catalog` | Paimon | v3.1+ |
| `unified_catalog` | Hive + Iceberg + Hudi + Delta Lake | v3.2+ |

### Creation and Use

```sql
-- Create a Hive Catalog
CREATE EXTERNAL CATALOG hive_catalog
PROPERTIES (
    "type" = "hive",
    "hive.metastore.uris" = "thrift://metastore:9083"
);

-- Create an Iceberg Catalog (object storage)
CREATE EXTERNAL CATALOG iceberg_catalog
PROPERTIES (
    "type" = "iceberg",
    "iceberg.catalog.type" = "hive",
    "hive.metastore.uris" = "thrift://metastore:9083"
);

-- Switch Catalog
SET CATALOG hive_catalog;
USE db_name;
SELECT * FROM table_name;

-- Cross-catalog query (three-part naming)
SELECT *
FROM hive_catalog.db_name.table_name
WHERE dt = '2024-01-15';

-- Internal table JOIN external table
SELECT o.*, h.extra_info
FROM default_catalog.db.orders o
JOIN hive_catalog.dw.user_profile h ON o.user_id = h.user_id;
```

### Performance Optimization

```sql
-- 1. Use Data Cache to accelerate repeated queries
SET enable_scan_datacache = true;

-- 2. Create async materialized views for frequently queried external tables
CREATE MATERIALIZED VIEW mv_hive_agg
REFRESH ASYNC EVERY (INTERVAL 1 HOUR)
AS
SELECT dt, region, SUM(amount) AS total
FROM hive_catalog.db.sales
GROUP BY dt, region;

-- 3. Query files directly with the FILES() function
SELECT * FROM FILES(
    "path" = "s3://bucket/data/*.parquet",
    "format" = "parquet",
    "aws.s3.access_key" = "xxx",
    "aws.s3.secret_key" = "xxx"
);
```

---

## Resource Group Resource Isolation

Resource Groups isolate resource usage across business workloads to prevent interference.

### Creating Resource Groups

```sql
-- Create a resource group
CREATE RESOURCE GROUP rg_etl
TO (user='etl_user')                    -- classifier: by user
WITH (
    'cpu_weight' = '20',                -- CPU weight (relative)
    'mem_limit' = '30%',                -- memory upper limit
    'concurrency_limit' = '10',         -- concurrency upper limit
    'big_query_mem_limit' = '10737418240',  -- per-query memory limit (10GB)
    'big_query_scan_rows_limit' = '1000000000'  -- per-query scan rows limit
);

-- Resource group with multiple classifiers
CREATE RESOURCE GROUP rg_online
TO
    (user='app_user'),                  -- by user
    (role='analyst'),                   -- by role
    (query_type IN ('SELECT')),         -- by query type
    (source_ip = '10.0.0.0/24')         -- by source IP
WITH (
    'cpu_weight' = '50',
    'mem_limit' = '50%',
    'concurrency_limit' = '100'
);
```

### Viewing and Management

```sql
-- View resource groups
SHOW RESOURCE GROUPS;

-- View resource group classifiers
SHOW RESOURCE GROUP rg_online;

-- Modify a resource group
ALTER RESOURCE GROUP rg_etl
WITH ('concurrency_limit' = '20');

-- Drop a resource group
DROP RESOURCE GROUP rg_etl;

-- Manually specify the resource group for a query
SET resource_group = 'rg_online';
```

---

## UDF User-Defined Functions

StarRocks supports Java UDFs, including scalar, aggregate, window, and table functions.

### Scalar UDF

```java
// Java implementation
package com.example.udf;

public class MyUpperUDF {
    public String evaluate(String input) {
        if (input == null) return null;
        return input.toUpperCase();
    }
}
```

```sql
-- Register a scalar UDF
CREATE FUNCTION my_upper(VARCHAR)
RETURNS VARCHAR
PROPERTIES (
    "symbol" = "com.example.udf.MyUpperUDF",
    "type" = "StarrocksJar",
    "file" = "http://server/my-udf.jar"
);

-- Use it
SELECT my_upper(name) FROM users;
```

### Aggregate UDF (UDAF)

```sql
-- Register an aggregate UDF
CREATE AGGREGATE FUNCTION my_sum(BIGINT)
RETURNS BIGINT
PROPERTIES (
    "symbol" = "com.example.udf.MySumUDAF",
    "type" = "StarrocksJar",
    "file" = "http://server/my-udf.jar"
);
```

### Table Function (UDTF)

```sql
-- Register a table function
CREATE TABLE FUNCTION my_explode(VARCHAR)
RETURNS TABLE (word VARCHAR)
PROPERTIES (
    "symbol" = "com.example.udf.MyExplodeUDTF",
    "type" = "StarrocksJar",
    "file" = "http://server/my-udf.jar"
);

-- Use it (with LATERAL JOIN)
SELECT t.word
FROM articles, LATERAL my_explode(content) AS t;
```

### UDF Management

```sql
-- View UDFs
SHOW FUNCTIONS;
SHOW GLOBAL FUNCTIONS;

-- Drop a UDF
DROP FUNCTION my_upper(VARCHAR);
DROP GLOBAL FUNCTION my_upper(VARCHAR);
```

---

## Generated Columns

A generated column computes an expression and stores the result at write time, so queries read it directly without runtime computation.

```sql
-- Define generated columns at table creation (v3.1+)
CREATE TABLE orders (
    order_id BIGINT,
    order_time DATETIME,
    amount DECIMAL(10,2),
    discount_rate DOUBLE,
    -- generated columns
    order_date DATE AS DATE(order_time),           -- extract date
    final_amount DECIMAL(10,2) AS amount * (1 - discount_rate),  -- compute discounted price
    order_year INT AS YEAR(order_time)             -- extract year
)
PARTITION BY (order_date)  -- generated column can be a partition column
DISTRIBUTED BY HASH(order_id);
```

**Use cases:**
- Precompute and store compute-heavy expressions
- Extract JSON fields and index them
- Create partition-expression columns (e.g., `DATE(datetime_col)`)

---

## Dictionary Objects

A Dictionary caches dimension-table data in BE memory; the `dict_mapping()` function provides millisecond-level dimension lookups.

```sql
-- 1. Create a Dictionary (CREATE DICTIONARY: v3.3+; dict_mapping() in load expressions: v3.2.5+)
CREATE DICTIONARY user_dict
USING users              -- based on the users table
(
    user_id KEY,          -- lookup key
    user_name VALUE,      -- return value
    region VALUE
);

-- 2. Manual refresh
REFRESH DICTIONARY user_dict;

-- 3. Use it in queries (in place of a JOIN)
SELECT
    order_id,
    amount,
    dict_mapping('user_dict', user_id, 'user_name') AS user_name,
    dict_mapping('user_dict', user_id, 'region') AS region
FROM orders
WHERE dt = '2024-01-15';

-- Performance comparison:
-- dict_mapping: in-memory lookup, no network shuffle
-- JOIN: requires Broadcast or Shuffle; gets slower as the dimension table grows
```

---

## AUTO_INCREMENT Columns

```sql
-- Auto-increment column (v3.1+, Primary Key / Duplicate tables; PK column allowed only on Primary Key tables)
CREATE TABLE events (
    id BIGINT AUTO_INCREMENT,   -- auto-increment primary key
    event_time DATETIME,
    user_id BIGINT,
    event_type VARCHAR(64)
)
PRIMARY KEY (id)
DISTRIBUTED BY HASH(id);

-- During ingestion, omit the auto-increment column; the system generates it
INSERT INTO events (event_time, user_id, event_type)
VALUES ('2024-01-15 10:00:00', 12345, 'click');
```

**Notes:**
- Auto-increment values are globally unique but not necessarily contiguous.
- Bulk ingestion allocates a contiguous range of IDs per batch.
- Suitable for scenarios that need unique identifiers but not strict monotonicity.

---

## Execution Plans and EXPLAIN

### EXPLAIN Commands

```sql
-- Basic execution plan
EXPLAIN SELECT * FROM orders WHERE dt = '2024-01-15';

-- Verbose execution plan (recommended; includes more optimizer info)
EXPLAIN VERBOSE SELECT * FROM orders WHERE dt = '2024-01-15';

-- View cost information
EXPLAIN COSTS SELECT * FROM orders WHERE dt = '2024-01-15';

-- View logical plan
EXPLAIN LOGICAL SELECT * FROM orders WHERE dt = '2024-01-15';
```

### Interpreting Key Information

```
-- Focus on:
-- 1. OlapScanNode:
--    partitions=3/365        <- partition pruning: 3 of 365 partitions scanned
--    tabletRatio=10/30       <- bucket pruning: 10 of 30 tablets scanned
--    cardinality=1000000     <- estimated rows

-- 2. HashJoinNode:
--    join op: INNER JOIN
--    distribution type: BROADCAST  <- JOIN distribution strategy
--    equal join conjunct: ...

-- 3. AggregateNode:
--    aggregate: SUM, COUNT
--    group by: region

-- 4. ExchangeNode:
--    distribution type: SHUFFLE   <- data redistribution
```

---

## Query Cache

```sql
-- Enable Query Cache (v3.0+)
SET enable_query_cache = true;

-- Cache mode
SET query_cache_type = 2;
-- 0: do not use cache
-- 1: use only when execution plans match exactly
-- 2: use when semantics match (recommended)

-- Cache size (BE config)
-- query_cache_capacity = 536870912  -- 512MB
```

**Cache conditions:**
- Identical SQL (or semantically equivalent SQL)
- Underlying data has not changed (DML invalidates the cache)
- Query does not contain non-deterministic functions (such as `now()`, `random()`)

---

## SET_VAR Hint

Temporarily modify session variables for a single SQL statement without affecting other queries.

```sql
-- Syntax: SELECT /*+ SET_VAR(key=value[, ...]) */ ...

-- 1. Adjust parallelism
SELECT /*+ SET_VAR(pipeline_dop=8) */
    region, COUNT(*)
FROM orders
GROUP BY region;

-- 2. Adjust memory limit
SELECT /*+ SET_VAR(query_mem_limit=8589934592) */
    user_id, SUM(amount)
FROM orders
GROUP BY user_id;

-- 3. Force a higher Broadcast Join row limit
SELECT /*+ SET_VAR(broadcast_row_limit=15000000) */
    o.*, p.name
FROM orders o
JOIN products p ON o.product_id = p.product_id;

-- 4. Adjust aggregation stages
SELECT /*+ SET_VAR(new_planner_agg_stage=2) */
    region, COUNT(DISTINCT user_id)
FROM events
GROUP BY region;

-- 5. Disable materialized view rewrite (for debugging)
SELECT /*+ SET_VAR(enable_materialized_view_rewrite=false) */
    region, SUM(amount)
FROM orders
GROUP BY region;

-- 6. Set multiple variables at once
SELECT /*+ SET_VAR(pipeline_dop=4, query_mem_limit=4294967296) */
    ...
```

### Common SET_VAR Parameters

| Parameter | Default | Description |
|------|--------|------|
| `pipeline_dop` | 0 (auto) | Parallelism; 0 = CPU cores / 2 |
| `query_mem_limit` | 0 (unlimited) | Per-query memory limit (bytes) |
| `query_timeout` | 300 | Query timeout (seconds) |
| `broadcast_row_limit` | 10000000 | Broadcast Join row limit |
| `new_planner_agg_stage` | 0 (auto) | Number of aggregation stages |
| `enable_materialized_view_rewrite` | true | Whether to enable MV rewrite |
| `cbo_use_correlated_join_estimate` | true | CBO correlated-join estimation |
| `enable_query_cache` | false | Whether to enable Query Cache |
