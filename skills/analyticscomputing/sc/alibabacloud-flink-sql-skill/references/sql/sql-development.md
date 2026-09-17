# Flink SQL Development

## Job Development Flow

```text
Create Job → Write SQL → Deep Check → Debug → Deploy → Start → Operate
```

## Basic SQL Template

```sql
-- 1. Create a Source Table
CREATE TEMPORARY TABLE source_table (
    user_id   BIGINT,
    item_id   BIGINT,
    behavior  VARCHAR,
    ts        TIMESTAMP(3),
    WATERMARK FOR ts AS ts - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic'     = 'user_behavior',
    'properties.bootstrap.servers' = 'kafka-broker1:9092',
    'properties.group.id'          = 'flink-group',
    'format'    = 'json',
    'scan.startup.mode'            = 'latest-offset'
);

-- 2. Create a Sink Table
CREATE TEMPORARY TABLE sink_table (
    window_start    TIMESTAMP(3),
    window_end      TIMESTAMP(3),
    uv              BIGINT,
    pv              BIGINT
) WITH (
    'connector' = 'hologres',
    'dbname'    = 'your_db',
    'tablename' = 'realtime_uv_pv',
    'username'  = '${ak}',      -- Use a variable or Secret
    'password'  = '${sk}'
);

-- 3. Write results
INSERT INTO sink_table
SELECT
    TUMBLE_START(ts, INTERVAL '1' MINUTE)  AS window_start,
    TUMBLE_END(ts, INTERVAL '1' MINUTE)    AS window_end,
    COUNT(DISTINCT user_id)                AS uv,
    COUNT(1)                               AS pv
FROM source_table
WHERE behavior = 'click'
GROUP BY TUMBLE(ts, INTERVAL '1' MINUTE);
```

## CREATE TABLE

### Basic Syntax

```sql
CREATE TEMPORARY TABLE table_name (
    column_name  data_type [NOT NULL] [COMMENT '...'],
    ...
    [WATERMARK FOR event_time_col AS watermark_strategy]
) WITH (
    'connector' = '...',
    'param1'    = 'value1',
    ...
);
```

### Time Attributes

```sql
-- Event Time + Watermark
ts        TIMESTAMP(3),
WATERMARK FOR ts AS ts - INTERVAL '10' SECOND

-- Processing Time (system time)
proc_time AS PROCTIME()
```

### Data Formats

Supported formats include `json`, `csv`, `avro`, `canal-json`, `debezium-json`, `protobuf`, `ogg-json`, and `maxwell-json`.

## INSERT INTO

### Write to One Sink

```sql
INSERT INTO sink_table SELECT ... FROM source_table;
```

### Write to Multiple Sinks (One Source, Multiple Sinks)

```sql
-- Option 1: multiple INSERT statements
INSERT INTO sink_a SELECT ... FROM source;
INSERT INTO sink_b SELECT ... FROM source;

-- Option 2: CTAS + multiple outputs
-- Suitable for writing the same data to different formats or storage systems
```

## Windowed Aggregations

### Tumbling Window

```sql
SELECT
    TUMBLE_START(ts, INTERVAL '5' MINUTE) AS window_start,
    TUMBLE_END(ts, INTERVAL '5' MINUTE)   AS window_end,
    COUNT(DISTINCT user_id)               AS uv
FROM source_table
GROUP BY TUMBLE(ts, INTERVAL '5' MINUTE);
```

### Sliding Window

```sql
SELECT
    HOP_START(ts, INTERVAL '1' MINUTE, INTERVAL '10' MINUTE) AS window_start,
    HOP_END(ts, INTERVAL '1' MINUTE, INTERVAL '10' MINUTE)   AS window_end,
    SUM(amount)                                              AS total_amount
FROM source_table
GROUP BY HOP(ts, INTERVAL '1' MINUTE, INTERVAL '10' MINUTE);
```

### Session Window

```sql
SELECT
    SESSION_START(ts, INTERVAL '30' MINUTE) AS window_start,
    SESSION_END(ts, INTERVAL '30' MINUTE)   AS window_end,
    COUNT(1)                                AS pv
FROM source_table
GROUP BY SESSION(ts, INTERVAL '30' MINUTE);
```

### OVER Window

```sql
SELECT
    user_id,
    amount,
    ts,
    AVG(amount) OVER (
        PARTITION BY user_id
        ORDER BY ts
        RANGE BETWEEN INTERVAL '10' MINUTE PRECEDING AND CURRENT ROW
    ) AS avg_amount_10min
FROM orders;
```

## Dimension-Table Joins

### Lookup Join (Temporal Table Join)

```sql
SELECT
    o.order_id,
    o.amount,
    u.user_name,
    u.vip_level
FROM orders AS o
JOIN users FOR SYSTEM_TIME AS OF o.proc_time AS u
  ON o.user_id = u.id;
```

**Lookup-table cache strategy:**

- `lookup.cache` = `NONE` / `PARTIAL`: use a partial cache to reduce database load.
- `lookup.partial-cached.max-rows` = '10000': maximum cached rows.
- `lookup.cache.ttl` = '1h': cache expiration time.

## CDAS / CTAS (Whole-Database/Sharded-Table Synchronization)

### CTAS (CREATE TABLE AS)

Use CTAS to merge and synchronize sharded MySQL tables:

```sql
CREATE TABLE mysql_sync_table
WITH ('database-name' = 'order_db%', 'table-name' = 'order_.*')
AS TABLE orders;
```

### CDAS (CREATE DATABASE AS)

Use CDAS for whole-database synchronization that automatically discovers and synchronizes every Table in the target Database.

```sql
-- Important: key OPTIONS for MySQL CDC Sources in the same STATEMENT SET must match,
-- especially server-id. When Databases require different server IDs, split them into
-- separate Jobs or STATEMENT SETs.

STATEMENT SET BEGIN;

CREATE TABLE src_db1 WITH (
  'connector' = 'mysql-cdc',
  'hostname' = 'mysql.example.com',
  'port' = '3306',
  'username' = '${username}',
  'password' = '${password}',
  'database-name' = 'biz_db_1',
  'table-name' = '.*',
  'server-id' = '5401-5408'
);

CREATE TABLE src_db2 WITH (
  'connector' = 'mysql-cdc',
  'hostname' = 'mysql.example.com',
  'port' = '3306',
  'username' = '${username}',
  'password' = '${password}',
  'database-name' = 'biz_db_2',
  'table-name' = '.*',
  'server-id' = '5401-5408'
);

END;
```

## User-Defined Functions (UDFs)

### UDF Registration Flow

1. Develop the UDF locally in Java or Python and package it as a JAR.
2. In the console, go to **Resource Management → Upload Dependency**.
3. Go to **Data Management → Functions → Create Function**.
4. Use it directly in SQL: `SELECT my_udf(col1) FROM table;`.

### Built-In Functions

Alibaba Cloud Flink provides built-in Scalar Functions, Aggregate Functions, and Table-Valued Functions:

- String Functions: `SUBSTRING`, `CONCAT`, `TRIM`, `UPPER`, and `LOWER`;
- Mathematical Functions: `ABS`, `ROUND`, `CEIL`, `FLOOR`, and `RAND`;
- Time Functions: `DATE_FORMAT`, `TIMESTAMPADD`, and `CURRENT_TIMESTAMP`;
- JSON Functions: `JSON_VALUE` and `JSON_QUERY`;
- Aggregate Functions: `COUNT`, `SUM`, `AVG`, `MAX`, `MIN`, and `COUNT(DISTINCT x)`.

## Job Debugging

- **Deep Check:** check SQL semantics, network connectivity, and Table metadata, and view SQL optimization suggestions.
- **Debug mode:** simulate Job execution to verify SELECT/INSERT logic. Debug data is not written downstream.
- **Intermediate results:** inspect intermediate computation results in Debug mode.

## Data Synchronization Templates

The console provides templates for common scenarios:

- Kafka → Hologres real-time data warehouse;
- MySQL CDC → Paimon data lake;
- MySQL CDC → ClickHouse query acceleration;
- SLS logs → MaxCompute.

## SQL Scripts

SQL scripts support `CALL`, DDL, DQL, and DML and can be used to:

- Manage Catalog and Table definitions;
- Query data and verify results;
- Inspect execution plans and troubleshoot with `EXPLAIN`;
- Manage Paimon Tables.

## SET Options

```sql
-- Set parallelism
SET 'parallelism.default' = '4';

-- Enable Checkpoints
SET 'execution.checkpointing.interval' = '60s';
SET 'execution.checkpointing.mode' = 'EXACTLY_ONCE';

-- State Backend (Alibaba Cloud Flink uses Gemini by default)
SET 'state.backend.type' = 'rocksdb';

-- Adjust the SQL parsing timeout
SET 'flink.sqlserver.rpc.execution.timeout' = '600s';
```

## Recommended Practices

1. **Avoid excessive temporary Tables:** prefer registered Tables in a Catalog.
2. **Configure caching for dimension-table Joins:** prevent frequent Lookup calls from slowing the primary data path.
3. **Set Watermarks appropriately:** tune the `INTERVAL` to the out-of-order and latency distributions.
4. **Enable incremental Checkpoints for jobs with large State:** reduce storage and I/O load.
5. **Manage sensitive data with variables or Secrets:** avoid plaintext in SQL.
6. **Use Recommend/Stable engine versions:** first verify version labels and the compatibility matrix.

## Official Documentation

- [Develop an SQL Job](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/develop-an-sql-draft)
- [Flink SQL Job Quickstart](https://help.aliyun.com/zh/flink/realtime-flink/getting-started/getting-started-for-a-flink-sql-deployment)
- [Manage UDFs](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/manage-udfs)
- [Manage Metadata](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/manage-catalogs/)
- [SQL Scripts](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/sql-scripts)
- [Job Debugging](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/debug-a-deployment)
- [CDAS](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/create-database-as-statement)
- [CTAS](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/create-table-as-statement)
