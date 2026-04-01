# SQL Component（COMPONENT_SQL）

## Overview

- Compute engine: `ODPS`
- Content format: sql
- Extension: `.sql`
- Code: 1010
- Data source type: `odps`
- Description: SQL component (legacy), supports parameterized SQL

> **Note**: COMPONENT_SQL is the legacy SQL component. It is recommended to use [SQL_COMPONENT](./SQL_COMPONENT.md) (new version) instead.

The SQL component node provides SQL code templates with multiple input and output parameters. It generates result tables by performing filtering, joining, and aggregation operations on data source tables, supporting parameterized SQL reuse.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_component_sql",
        "script": {
          "path": "example_component_sql",
          "runtime": {
            "command": "COMPONENT_SQL"
          },
          "content": "SELECT ${param1} FROM dual;"
        }
      }
    ]
  }
}
```
