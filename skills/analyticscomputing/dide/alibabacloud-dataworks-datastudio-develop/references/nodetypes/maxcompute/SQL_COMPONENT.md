# SQL Component (New)（SQL_COMPONENT）

## Overview

- Compute engine: `ODPS`
- Content format: sql
- Extension: `.sql`
- Code: 3010
- Data source type: `odps`
- Description: SQL component (new version), supports parameterized SQL

The SQL component (new version) node provides SQL code templates with multiple input and output parameters. It generates result tables by performing filtering, joining, and aggregation operations on data source tables, helping developers quickly build reusable data processing nodes.

## Prerequisites

- Only supported on DataWorks **Standard Edition or above**
- Development permissions for the workspace are required
- The workspace has been bound to a MaxCompute compute resource

## Core Features

### Parameterized SQL

The component supports defining input parameters using `${parameter_name}`. When referencing the component, the system automatically identifies parameters and requires value assignment.

```sql
-- SQL component example: parameterized query template
SELECT ${columns}
FROM ${source_table}
WHERE dt = '${bizdate}'
  AND ${filter_condition};
```

### Version Management

Supports upgrading component versions through the "Update Code Version" feature. Consumers can choose to use the new version.

## Restrictions

- When accessing public network or VPC data sources, a scheduling resource group that has passed the connectivity test must be used

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_sql_component",
        "script": {
          "path": "example_sql_component",
          "runtime": {
            "command": "SQL_COMPONENT"
          },
          "content": "SELECT ${param1} FROM dual;"
        }
      }
    ]
  }
}
```

## Reference

- [SQL Component Node](https://help.aliyun.com/zh/dataworks/user-guide/sql-component-node)
