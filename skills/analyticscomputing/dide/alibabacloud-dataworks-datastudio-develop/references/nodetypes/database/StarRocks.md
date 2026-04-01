# StarRocks（StarRocks）

## Overview

- Compute engine: `DATABASE`
- Content format: sql
- Extension: `.sql`
- Data source type: `starrocks`
- Description: Execute SQL statements against StarRocks database

Used to directly execute SQL queries and data processing against StarRocks real-time analytical database to execute SQL queries and data processing. The corresponding data source type must be registered in the workspace beforehand.

## Prerequisites

- The data source type has been added to the DataWorks workspace StarRocks type data source
- The data source connectivity test has passed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_starrocks",
        "script": {
          "path": "example_starrocks",
          "runtime": {
            "command": "StarRocks"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Restrictions

- SQL syntax must comply with StarRocks database specifications（MySQL-protocol compatible)
- Mixing DDL and DML statements in a single node is not supported (separate execution recommended)
- Execution timeout is limited by the data source configuration
