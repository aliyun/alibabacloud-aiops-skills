# AnalyticDB for MySQL（ADB_for_MySQL）

## Overview

- Compute engine: `DATABASE`
- Content format: sql
- Extension: `.sql`
- Data source type: `adb_mysql`
- Description: Execute SQL statements against AnalyticDB for MySQL database

Used to directly execute SQL queries and data processing against AnalyticDB for MySQL（ADB MySQL）cloud-native data warehouse to execute SQL queries and data processing. The corresponding data source type must be registered in the workspace beforehand.

## Prerequisites

- The data source type has been added to the DataWorks workspace AnalyticDB for MySQL type data source
- The data source connectivity test has passed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_adb_for_mysql",
        "script": {
          "path": "example_adb_for_mysql",
          "runtime": {
            "command": "ADB for MySQL"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Restrictions

- SQL syntax must comply with AnalyticDB for MySQL database specifications（MySQL-syntax compatible)
- Mixing DDL and DML statements in a single node is not supported (separate execution recommended)
- Execution timeout is limited by the data source configuration
