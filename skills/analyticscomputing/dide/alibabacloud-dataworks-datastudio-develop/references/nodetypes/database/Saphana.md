# SAP HANA（Saphana）

## Overview

- Compute engine: `DATABASE`
- Content format: sql
- Extension: `.sql`
- Data source type: `saphana`
- Description: Execute SQL statements against SAP HANA database

Used to directly execute SQL queries and data processing against SAP HANA in-memory database to execute SQL queries and data processing. The corresponding data source type must be registered in the workspace beforehand.

## Prerequisites

- The data source type has been added to the DataWorks workspace SAP HANA type data source
- The data source connectivity test has passed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_saphana",
        "script": {
          "path": "example_saphana",
          "runtime": {
            "command": "Saphana"
          },
          "content": "SELECT 1 FROM DUMMY;"
        }
      }
    ]
  }
}
```

## Restrictions

- SQL syntax must comply with SAP HANA SQL specifications
- SAP HANA uses the `DUMMY` table instead of the `DUAL` table used in other databases (e.g., `SELECT 1 FROM DUMMY`)
- Mixing DDL and DML statements in a single node is not supported (separate execution recommended)
- Execution timeout is limited by the data source configuration
