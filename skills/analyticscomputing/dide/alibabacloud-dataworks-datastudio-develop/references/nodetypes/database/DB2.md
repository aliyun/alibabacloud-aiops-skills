# IBM DB2（DB2）

## Overview

- Compute engine: `DATABASE`
- Content format: sql
- Extension: `.sql`
- Data source type: `db2`
- Description: Execute SQL statements against IBM DB2 database

Used to directly execute SQL queries and data processing against IBM DB2 database to execute SQL queries and data processing. The corresponding data source type must be registered in the workspace beforehand.

## Prerequisites

- The data source type has been added to the DataWorks workspace DB2 type data source
- The data source connectivity test has passed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_db2",
        "script": {
          "path": "example_db2",
          "runtime": {
            "command": "DB2"
          },
          "content": "SELECT 1 FROM SYSIBM.SYSDUMMY1;"
        }
      }
    ]
  }
}
```

## Restrictions

- SQL syntax must comply with IBM DB2 database specifications
- DB2 uses the `SYSIBM.SYSDUMMY1` table instead of the `DUAL` table used in other databases (e.g., `SELECT 1 FROM SYSIBM.SYSDUMMY1`)
- Mixing DDL and DML statements in a single node is not supported (separate execution recommended)
- Execution timeout is limited by the data source configuration
