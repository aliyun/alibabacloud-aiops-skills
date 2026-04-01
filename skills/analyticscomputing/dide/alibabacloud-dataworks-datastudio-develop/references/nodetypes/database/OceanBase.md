# OceanBase（OceanBase）

## Overview

- Compute engine: `DATABASE`
- Content format: sql
- Extension: `.sql`
- Data source type: `oceanbase`
- Description: Execute SQL statements against OceanBase database

Used to directly execute SQL queries and data processing against OceanBase distributed database to execute SQL queries and data processing. The corresponding data source type must be registered in the workspace beforehand.

## Prerequisites

- The data source type has been added to the DataWorks workspace OceanBase type data source
- The data source connectivity test has passed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_oceanbase",
        "script": {
          "path": "example_oceanbase",
          "runtime": {
            "command": "OceanBase"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Restrictions

- SQL syntax must comply with OceanBase database specifications (compatible with MySQL or Oracle mode)
- Mixing DDL and DML statements in a single node is not supported (separate execution recommended)
- Execution timeout is limited by the data source configuration
