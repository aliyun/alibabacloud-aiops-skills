# Lightning SQL（LIGHTNING_SQL）

## Overview

- Compute engine: `ODPS`
- Content format: sql
- Extension: `.sql`
- Code: 61
- Data source type: `odps`
- Description: Lightning SQL query

The Lightning SQL node is used to perform interactive SQL queries through the MaxCompute Lightning service. Lightning provides a PostgreSQL-compatible query interface that supports low-latency interactive analysis on MaxCompute tables.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource
- MaxCompute Lightning service has been activated

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_lightning_sql",
        "script": {
          "path": "example_lightning_sql",
          "runtime": {
            "command": "LIGHTNING_SQL"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```
