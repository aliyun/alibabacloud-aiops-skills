# Hologres Development（HOLOGRES_DEVELOP）

## Overview

- Compute engine: `HOLO`
- Content format: sql
- Extension: `.sql`
- Data source type: `hologres`
- Code: 1091
- Description: Hologres development SQL node for Hologres database development and debugging

The Hologres development node provides a SQL editing and debugging environment for the development phase, allowing you to write and run Hologres SQL directly in DataWorks. It is functionally similar to the HOLOGRES_SQL node, both using PostgreSQL-compatible syntax, and is suitable for table management, data querying, and ETL development in Hologres real-time data warehouses.

## Prerequisites

- A Hologres compute engine instance has been added on the DataWorks workspace configuration page
- RAM users must have **Developer** or **Workspace Admin** role permissions

## Core Features

### SQL Syntax

Supports Hologres-compatible PostgreSQL syntax, including:

- **DDL operations**: Create tables, modify table structures, create indexes, etc.
- **DML operations**: INSERT, UPDATE, DELETE, SELECT
- **External table queries**: Directly query MaxCompute data through external tables

```sql
-- Create columnar storage table
BEGIN;
CREATE TABLE IF NOT EXISTS dwd_user_info (
  user_id BIGINT NOT NULL,
  user_name TEXT,
  gender TEXT,
  register_date DATE,
  PRIMARY KEY (user_id)
);
CALL set_table_property('dwd_user_info', 'orientation', 'column');
CALL set_table_property('dwd_user_info', 'bitmap_columns', 'gender');
COMMIT;

-- Query using scheduling parameters
SELECT user_id, user_name
FROM dwd_user_info
WHERE register_date = '${bizdate}';
```

### Scheduling Parameters

Supports defining dynamic parameters using `${variable_name}` syntax, with values assigned in the scheduling configuration.

### Differences from HOLOGRES_SQL

| Feature | HOLOGRES_DEVELOP | HOLOGRES_SQL |
|------|------------------|-------------|
| Code | 1091 | 1093 |
| Purpose | Development and debugging | Production execution |
| SQL syntax | PostgreSQL compatible | PostgreSQL compatible |

The two are functionally identical; the main difference lies in node classification and intended use case.

## Restrictions

- Query results display limit: up to 10,000 rows
- Defaults to 200 rows when `LIMIT` is not specified

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_hologres_develop",
        "script": {
          "path": "example_hologres_develop",
          "runtime": {
            "command": "HOLOGRES_DEVELOP"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Related Documentation

- [Hologres SQL Node](https://help.aliyun.com/zh/dataworks/user-guide/hologres-sql-node)
