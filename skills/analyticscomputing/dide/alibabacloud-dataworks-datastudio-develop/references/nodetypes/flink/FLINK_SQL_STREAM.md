# Flink Streaming SQL（FLINK_SQL_STREAM）

## Overview

- Compute engine: `FLINK`
- Content format: sql
- Extension: `.json`
- Data source type: `flink`
- Code: 2012
- Description: Flink streaming SQL node, the recommended real-time computation node type

The Flink streaming SQL node is used in DataWorks to develop and schedule Flink real-time computation tasks. Through standard Flink SQL syntax, you can define streaming data sources (Source), data targets (Sink), and data processing logic to achieve real-time data ingestion, transformation, and writing. This node type is the recommended approach for real-time stream computation in DataWorks, and has superseded the legacy BLINK_SQL.

## Prerequisites

- Alibaba Cloud Realtime Compute Flink edition has been activated and a Flink workspace has been created
- A Flink compute engine instance has been bound in the DataWorks workspace
- RAM users must have **Developer** or **Workspace Admin** role permissions

## Core Features

### SQL Syntax

Flink streaming SQL follows the standard Flink SQL syntax. A typical task consists of three parts:

1. **CREATE TABLE (Source)**: Define the source table, such as Kafka, DataHub, SLS, etc.
2. **CREATE TABLE (Sink)**: Define the target table, such as Hologres, MaxCompute, Kafka, etc.
3. **INSERT INTO ... SELECT**: Define the data transformation and write logic

```sql
-- Define source table (Kafka)
CREATE TABLE source_table (
  user_id BIGINT,
  item_id BIGINT,
  behavior STRING,
  ts TIMESTAMP(3),
  WATERMARK FOR ts AS ts - INTERVAL '5' SECOND
) WITH (
  'connector' = 'kafka',
  'topic' = 'user_behavior',
  'properties.bootstrap.servers' = 'localhost:9092',
  'format' = 'json'
);

-- Define target table (Hologres)
CREATE TABLE sink_table (
  window_start TIMESTAMP(3),
  window_end TIMESTAMP(3),
  item_id BIGINT,
  pv_cnt BIGINT
) WITH (
  'connector' = 'hologres',
  'dbname' = 'my_db',
  'tablename' = 'item_pv',
  'username' = '${ak}',
  'password' = '${sk}'
);

-- Data processing and write
INSERT INTO sink_table
SELECT
  TUMBLE_START(ts, INTERVAL '1' MINUTE) AS window_start,
  TUMBLE_END(ts, INTERVAL '1' MINUTE) AS window_end,
  item_id,
  COUNT(*) AS pv_cnt
FROM source_table
GROUP BY TUMBLE(ts, INTERVAL '1' MINUTE), item_id;
```

### Scheduling Parameters

Supports defining dynamic parameters using `${variable_name}`, which can be assigned values in the scheduling configuration.

## Restrictions

- Once started, streaming tasks run continuously until manually stopped or an exception occurs
- Although the content is in SQL format, it is actually stored as JSON configuration in DataWorks (extension `.json`)
- The corresponding Flink compute resource and resource group must be selected in the run configuration

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_flink_sql_stream",
        "script": {
          "path": "example_flink_sql_stream",
          "runtime": {
            "command": "FLINK_SQL_STREAM"
          },
          "content": "-- Flink Stream SQL\nSELECT 1;"
        }
      }
    ]
  }
}
```

## Related Documentation

- [Flink Streaming SQL Node](https://help.aliyun.com/zh/dataworks/user-guide/flink-sql-streaming-node)
