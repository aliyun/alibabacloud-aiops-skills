# PolarDB-X / DRDS（DRDS）

## Overview

- Compute engine: `DATABASE`
- Content format: sql
- Extension: `.sql`
- Data source type: `drds`
- Description: Execute SQL statements against PolarDB-X (DRDS) database

Used to directly execute SQL queries and data processing against PolarDB-X (formerly DRDS) distributed database. The corresponding data source type must be registered in the workspace beforehand.

## Prerequisites

- The data source type has been added to the DataWorks workspace DRDS type data source
- The data source connectivity test has passed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_drds",
        "script": {
          "path": "example_drds",
          "runtime": {
            "command": "DRDS"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Restrictions

- SQL syntax must comply with PolarDB-X（DRDS）database specifications
- Mixing DDL and DML statements in a single node is not supported (separate execution recommended)
- Execution timeout is limited by the data source configuration
