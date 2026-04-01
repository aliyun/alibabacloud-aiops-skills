# SelectDB（Selectdb）

## Overview

- Compute engine: `DATABASE`
- Content format: sql
- Extension: `.sql`
- Data source type: `selectdb`
- Description: Execute SQL statements against SelectDB database

Used to directly execute SQL queries and data processing against SelectDB cloud-native real-time data warehouse to execute SQL queries and data processing. The corresponding data source type must be registered in the workspace beforehand.

## Prerequisites

- The data source type has been added to the DataWorks workspace SelectDB type data source
- The data source connectivity test has passed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_selectdb",
        "script": {
          "path": "example_selectdb",
          "runtime": {
            "command": "Selectdb"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Restrictions

- SQL syntax must comply with SelectDB database specifications(based on Apache Doris, MySQL-protocol compatible)
- Mixing DDL and DML statements in a single node is not supported (separate execution recommended)
- Execution timeout is limited by the data source configuration
