# Blink Batch SQL（BLINK_BATCH_SQL）

## Overview

- Compute engine: `FLINK`
- Content format: sql
- Extension: `.json`
- Data source type: `flink`
- Code: 2020
- Description: Blink batch SQL (legacy), superseded by FLINK_SQL_BATCH

> **Note**: BLINK_BATCH_SQL is a legacy node type. It is recommended to use [FLINK_SQL_BATCH](./FLINK_SQL_BATCH.md) instead. Do not use this node type for new projects.

The Blink batch SQL node is an early batch SQL node based on the Alibaba Cloud Blink engine. Unlike BLINK_SQL (streaming), this node processes bounded datasets and executes in batch processing mode. The Blink engine has been unified and upgraded to the Flink edition, and this node type is retained only for compatibility with existing tasks.

## Prerequisites

- Alibaba Cloud Realtime Compute service (Blink version) has been activated
- Blink project association has been configured in the DataWorks workspace

## Core Features

### SQL Syntax

Blink batch SQL syntax is used for batch processing of bounded datasets, supporting standard SELECT, JOIN, GROUP BY, and other operations.

```sql
-- Blink Batch SQL example
CREATE TABLE batch_input (
  user_id BIGINT,
  item_id BIGINT,
  action VARCHAR
) WITH (
  type = 'odps',
  tableName = 'user_behavior',
  partition = 'ds=20231001'
);

CREATE TABLE batch_output (
  user_id BIGINT,
  action_count BIGINT
) WITH (
  type = 'odps',
  tableName = 'user_action_summary',
  partition = 'ds=20231001'
);

INSERT INTO batch_output
SELECT user_id, COUNT(*) AS action_count
FROM batch_input
GROUP BY user_id;
```

## Migration Recommendation

It is recommended to migrate existing BLINK_BATCH_SQL tasks to FLINK_SQL_BATCH. The main changes are:

- Connector declaration: change `type = 'xxx'` to `'connector' = 'xxx'`
- Compatibility adjustments for some data types and built-in functions

## Restrictions

- Legacy node type; newer DataWorks versions may no longer support creation
- Depends on the legacy Blink engine runtime environment
- Batch tasks automatically end after processing completes

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_blink_batch_sql",
        "script": {
          "path": "example_blink_batch_sql",
          "runtime": {
            "command": "BLINK_BATCH_SQL"
          },
          "content": "-- Blink Batch SQL\nSELECT 1;"
        }
      }
    ]
  }
}
```
