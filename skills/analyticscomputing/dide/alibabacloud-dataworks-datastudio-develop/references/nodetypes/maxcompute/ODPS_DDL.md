# MaxCompute DDL（ODPS_DDL）

## Overview

- Compute engine: `ODPS`
- Content format: sql
- Extension: `.json`
- Code: 18
- Data source type: `odps`
- Label type: RESOURCE
- Description: MaxCompute DDL statements (CREATE/ALTER/DROP)

The DDL node is used to execute MaxCompute Data Definition Language (DDL) operations, including creating tables, altering table structures, dropping tables, etc. It is suitable for scenarios that require automated table structure management through scheduling.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource

## Core Features

Supports standard MaxCompute DDL statements:

```sql
-- Create table
CREATE TABLE IF NOT EXISTS my_table (
  id     BIGINT,
  name   STRING,
  amount DOUBLE
) PARTITIONED BY (dt STRING)
LIFECYCLE 180;

-- Alter table
ALTER TABLE my_table ADD COLUMNS (city STRING);

-- Drop table
DROP TABLE IF EXISTS temp_table;
```

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_odps_ddl",
        "script": {
          "path": "example_odps_ddl",
          "runtime": {
            "command": "ODPS_DDL"
          },
          "content": "CREATE TABLE IF NOT EXISTS test_table (id BIGINT, name STRING);"
        }
      }
    ]
  }
}
```
