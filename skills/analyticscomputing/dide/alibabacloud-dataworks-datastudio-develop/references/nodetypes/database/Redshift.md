# Amazon Redshift（Redshift）

## Overview

- Compute engine: `DATABASE`
- Content format: sql
- Extension: `.sql`
- Data source type: `redshift`
- Description: Execute SQL statements against Amazon Redshift data warehouse

Used to directly execute SQL queries and data processing against Amazon Redshift cloud data warehouse. The corresponding data source type must be registered in the workspace beforehand.

## Prerequisites

- The data source type has been added to the DataWorks workspace Redshift type data source
- The data source connectivity test has passed
- Network connectivity is confirmed (the Redshift cluster must be accessible from DataWorks)

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_redshift",
        "script": {
          "path": "example_redshift",
          "runtime": {
            "command": "Redshift"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Restrictions

- SQL syntax must comply with Amazon Redshift database specifications(based on PostgreSQL)
- Mixing DDL and DML statements in a single node is not supported (separate execution recommended)
- Execution timeout is limited by the data source configuration
