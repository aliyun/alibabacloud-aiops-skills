# Blink Streaming SQL（BLINK_SQL）

## Overview

- Compute engine: `FLINK`
- Content format: sql
- Extension: `.json`
- Data source type: `flink`
- Code: 2010
- Description: Blink streaming SQL (legacy), superseded by FLINK_SQL_STREAM

> **Note**: BLINK_SQL is a legacy node type. It is recommended to use [FLINK_SQL_STREAM](./FLINK_SQL_STREAM.md) instead. Do not use this node type for new projects.

The Blink streaming SQL node is an early real-time streaming computation node based on the Alibaba Cloud Blink engine. Blink is an Alibaba Cloud internal fork of Apache Flink, which was later unified and upgraded to the Flink edition for Alibaba Cloud's real-time computing service. This node type is retained only for compatibility with existing tasks.

## Prerequisites

- Alibaba Cloud Realtime Compute service (Blink version) has been activated
- Blink project association has been configured in the DataWorks workspace

## Core Features

### SQL Syntax

Blink SQL syntax is largely consistent with Flink SQL, supporting DDL (CREATE TABLE), DML (INSERT INTO), and other operations. However, some syntax details and connector configurations differ from the newer Flink SQL version.

```sql
-- Blink SQL example
CREATE TABLE source_table (
  id BIGINT,
  name VARCHAR,
  ts TIMESTAMP,
  WATERMARK FOR ts AS withOffset(ts, 1000)
) WITH (
  type = 'kafka',
  topic = 'my_topic'
);

CREATE TABLE sink_table (
  id BIGINT,
  name VARCHAR
) WITH (
  type = 'rds'
);

INSERT INTO sink_table
SELECT id, name FROM source_table;
```

## Migration Recommendation

It is recommended to migrate existing BLINK_SQL tasks to FLINK_SQL_STREAM. The main changes are:

- Connector declaration: change `type = 'xxx'` to `'connector' = 'xxx'`
- WATERMARK syntax adjustments
- Some built-in function name changes

## Restrictions

- Legacy node type; newer DataWorks versions may no longer support creation
- Depends on the legacy Blink engine runtime environment

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_blink_sql",
        "script": {
          "path": "example_blink_sql",
          "runtime": {
            "command": "BLINK_STREAM_SQL"
          },
          "content": "-- Blink SQL\nSELECT 1;"
        }
      }
    ]
  }
}
```
