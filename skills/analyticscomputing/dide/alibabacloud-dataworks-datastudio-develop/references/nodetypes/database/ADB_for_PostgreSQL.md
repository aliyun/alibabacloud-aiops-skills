# AnalyticDB for PostgreSQL（ADB_for_PostgreSQL）

## Overview

- Compute engine: `DATABASE`
- Content format: sql
- Extension: `.sql`
- Data source type: `adb_pg`
- Description: Execute SQL statements against AnalyticDB for PostgreSQL database

Used to directly execute SQL queries and data processing against AnalyticDB for PostgreSQL（ADB PG）cloud-native data warehouse to execute SQL queries and data processing. The corresponding data source type must be registered in the workspace beforehand.

## Prerequisites

- The data source type has been added to the DataWorks workspace AnalyticDB for PostgreSQL type data source
- The data source connectivity test has passed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_adb_for_postgresql",
        "script": {
          "path": "example_adb_for_postgresql",
          "runtime": {
            "command": "ADB for PostgreSQL"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Restrictions

- SQL syntax must comply with AnalyticDB for PostgreSQL database specifications（PostgreSQL-syntax compatible, with Greenplum extension support)
- Mixing DDL and DML statements in a single node is not supported (separate execution recommended)
- Execution timeout is limited by the data source configuration
