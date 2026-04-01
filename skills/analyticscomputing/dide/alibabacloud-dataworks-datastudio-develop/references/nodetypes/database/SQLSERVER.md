# SQL Server（SQLSERVER）

## Overview

- Compute engine: `DATABASE`
- Content format: sql
- Extension: `.sql`
- Data source type: `sqlserver`
- Description: Execute SQL statements against SQL Server database

Used to directly execute SQL queries and data processing against SQL Server database to execute SQL queries and data processing. The corresponding data source type must be registered in the workspace beforehand.

## Prerequisites

- The data source type has been added to the DataWorks workspace SQL Server type data source
- The data source connectivity test has passed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_sqlserver",
        "script": {
          "path": "example_sqlserver",
          "runtime": {
            "command": "Sql Server"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Restrictions

- SQL syntax must comply with SQL Server（T-SQL）database specifications
- Mixing DDL and DML statements in a single node is not supported (separate execution recommended)
- Execution timeout is limited by the data source configuration
