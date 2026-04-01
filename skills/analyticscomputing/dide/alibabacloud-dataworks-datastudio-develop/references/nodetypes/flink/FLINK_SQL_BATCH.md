# Flink Batch SQL（FLINK_SQL_BATCH）

## Overview

- Compute engine: `FLINK`
- Content format: sql
- Extension: `.json`
- Data source type: `flink`
- Code: 2011
- Description: Flink batch SQL node, used for batch SQL computation based on the Flink engine

The Flink batch SQL node is used in DataWorks to develop and schedule batch SQL tasks based on the Flink engine. Unlike streaming SQL, batch SQL processes bounded datasets and is suitable for offline batch computation scenarios. This node type leverages Flink's unified batch-streaming architecture to execute SQL queries in batch processing mode.

## Prerequisites

- Alibaba Cloud Realtime Compute Flink edition has been activated and a Flink workspace has been created
- A Flink compute engine instance has been bound in the DataWorks workspace
- RAM users must have **Developer** or **Workspace Admin** role permissions

## Core Features

### SQL Syntax

Flink batch SQL supports standard Flink SQL batch processing syntax, primarily used for:

- Batch reading and processing of bounded data sources
- Data aggregation, join queries, and other batch analysis operations
- Batch data writes to target tables

```sql
-- Define batch data source
CREATE TABLE batch_source (
  order_id BIGINT,
  user_id BIGINT,
  amount DECIMAL(10, 2),
  order_time TIMESTAMP(3)
) WITH (
  'connector' = 'filesystem',
  'path' = 'oss://my-bucket/orders/',
  'format' = 'parquet'
);

-- Define target table
CREATE TABLE batch_sink (
  user_id BIGINT,
  total_amount DECIMAL(10, 2),
  order_count BIGINT
) WITH (
  'connector' = 'hologres',
  'dbname' = 'my_db',
  'tablename' = 'user_order_summary'
);

-- Batch aggregation processing
INSERT INTO batch_sink
SELECT
  user_id,
  SUM(amount) AS total_amount,
  COUNT(*) AS order_count
FROM batch_source
GROUP BY user_id;
```

### Scheduling Parameters

Supports defining dynamic parameters using `${variable_name}`, which can be assigned values in the scheduling configuration. Time expressions such as `${yyyymmdd}` are also supported.

## Restrictions

- Batch tasks automatically end after data processing completes, suitable for periodic scheduling
- Although the content is in SQL format, it is actually stored as JSON configuration in DataWorks (extension `.json`)
- The corresponding Flink compute resource and resource group must be selected in the run configuration

## Differences from Streaming SQL

| Feature | Batch SQL (FLINK_SQL_BATCH) | Streaming SQL (FLINK_SQL_STREAM) |
|------|---------------------------|---------------------------|
| Dataset type | Bounded dataset | Unbounded data stream |
| Execution method | Automatically ends after processing completes | Runs continuously |
| Applicable scenarios | Offline batch analysis, ETL | Real-time data processing, monitoring |
| Scheduling method | Periodic scheduling | Runs continuously after startup |

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_flink_sql_batch",
        "script": {
          "path": "example_flink_sql_batch",
          "runtime": {
            "command": "FLINK_SQL_BATCH"
          },
          "content": "-- Flink Batch SQL\nSELECT 1;"
        }
      }
    ]
  }
}
```

## Related Documentation

- [Flink Batch SQL Node](https://help.aliyun.com/zh/dataworks/user-guide/flink-sql-batch-node)
