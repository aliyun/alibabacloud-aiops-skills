# Alibaba Cloud Realtime Compute for Apache Flink — SQL Development Reference

## Job Development Workflow Overview

```
Create Job → Write SQL → Deep Inspection → Debug → Deploy → Start → O&M
```

## Basic SQL Template

```sql
-- 1. Create source table (Source)
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

-- 2. Create sink table (Sink)
CREATE TEMPORARY TABLE sink_table (
    window_start    TIMESTAMP(3),
    window_end      TIMESTAMP(3),
    uv              BIGINT,
    pv              BIGINT
) WITH (
    'connector' = 'hologres',
    'dbname'    = 'your_db',
    'tablename' = 'realtime_uv_pv',
    'username'  = '${ak}',      -- Recommend using variables/secrets management
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
-- Event time + watermark
ts        TIMESTAMP(3),
WATERMARK FOR ts AS ts - INTERVAL '10' SECOND

-- Processing time (system time)
proc_time AS PROCTIME()
```

### Data Formats

Supported: `json`, `csv`, `avro`, `canal-json`, `debezium-json`, `protobuf`, `ogg-json`, `maxwell-json`, etc.

## INSERT INTO

### Single Sink Write

```sql
INSERT INTO sink_table SELECT ... FROM source_table;
```

### Multi-Sink Write (One Source, Multiple Sinks)

```sql
-- Option 1: Multiple INSERT statements
INSERT INTO sink_a SELECT ... FROM source;
INSERT INTO sink_b SELECT ... FROM source;

-- Option 2: CTAS + multi-output
-- Suitable for scenarios that require writing the same data to different formats/stores
```

## Window Aggregation

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

## Dimension Table JOIN

### Lookup JOIN (Temporal Table Association)

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

**Lookup Table Caching Strategies**:
- `lookup.cache` = `NONE` / `PARTIAL` — Partial caching to reduce database pressure
- `lookup.partial-cached.max-rows` = '10000' — Maximum cached rows
- `lookup.cache.ttl` = '1h' — Cache expiration time

## CDAS / CTAS (Full-Database / Sharded-Table Sync)

### CTAS (Create Table As Statement)

Used to sync merged data from MySQL sharded databases and tables:

```sql
CREATE TABLE mysql_sync_table
WITH ('database-name' = 'order_db%', 'table-name' = 'order_.*')
AS TABLE orders;
```

### CDAS (Create Database As Statement)

Full-database sync; automatically discovers and syncs all tables in the target database.

```sql
-- Note: Within the same STATEMENT SET, key OPTIONS for MySQL CDC sources must be consistent (especially server-id)
-- If different databases require different server-ids, split them into separate jobs or separate STATEMENT SETs.

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

## User-Defined Functions (UDF)

### UDF Registration Process

1. Develop UDF locally (Java/Python), package as JAR
2. Console → **Resource Management** → **Upload Dependencies**
3. Console → **Data Management** → **Functions** → **New Function**
4. Use directly in SQL: `SELECT my_udf(col1) FROM table;`

### Built-In Functions

Cloud Flink includes a rich set of scalar, aggregate, and table-valued functions:
- String functions: `SUBSTRING`, `CONCAT`, `TRIM`, `UPPER`, `LOWER`
- Math functions: `ABS`, `ROUND`, `CEIL`, `FLOOR`, `RAND`
- Time functions: `DATE_FORMAT`, `TIMESTAMPADD`, `CURRENT_TIMESTAMP`
- JSON functions: `JSON_VALUE`, `JSON_QUERY`
- Aggregate functions: `COUNT`, `SUM`, `AVG`, `MAX`, `MIN`, `COUNT(DISTINCT x)`

## Job Debugging

- **Deep Inspection**: Checks SQL semantics, network connectivity, table metadata; view SQL optimization recommendations
- **Debug Mode**: Simulates job execution to verify SELECT/INSERT logic correctness; debug data is not written downstream
- **Intermediate Result Display**: View intermediate computation results in debug mode

## Data Sync Templates

The console provides pre-built templates (click the template button to use), covering:
- Kafka → Hologres real-time data warehouse
- MySQL CDC → Paimon data lake
- MySQL CDC → ClickHouse query acceleration
- SLS Logs → Big Data Computing Service

## Query Scripts

Supports `CALL`, DDL, DQL, DML syntax, which can be used for:
- Managing Catalog and table definitions
- Data queries and result verification
- `EXPLAIN` to view execution plans for troubleshooting
- Managing Paimon tables

## SET Parameter Configuration

```sql
-- Set parallelism
SET 'parallelism.default' = '4';

-- Enable Checkpoint
SET 'execution.checkpointing.interval' = '60s';
SET 'execution.checkpointing.mode' = 'EXACTLY_ONCE';

-- State backend (Cloud Flink uses Gemini by default)
SET 'state.backend.type' = 'rocksdb';

-- Adjust SQL parsing timeout
SET 'flink.sqlserver.rpc.execution.timeout' = '600s';
```

## Best Practices

1. **Avoid excessive temporary tables**: Use formally registered tables from the Catalog
2. **Add caching to dimension table JOINs**: Prevent high-frequency lookup queries from slowing down the main pipeline
3. **Set watermarks appropriately**: Adjust `INTERVAL` based on data latency experience
4. **Enable incremental checkpoints for large-state jobs**: Reduce storage and I/O pressure
5. **Manage sensitive information with variables/secrets**: Avoid plaintext in SQL
6. **Use recommended/stable engine versions**: Check version labels `Recommend` / `Stable`

## Official Documentation Links

- [SQL Job Development](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/develop-an-sql-draft)
- [Flink SQL Job Quick Start](https://help.aliyun.com/zh/flink/realtime-flink/getting-started/getting-started-for-a-flink-sql-deployment)
- [Managing User-Defined Functions](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/manage-udfs)
- [Managing Metadata](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/manage-catalogs/)
- [Query Scripts](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/sql-scripts)
- [Job Debugging](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/debug-a-deployment)
- [CDAS](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/create-database-as-statement)
- [CTAS](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/create-table-as-statement)
