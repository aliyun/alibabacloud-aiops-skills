# Hologres SQL（HOLOGRES_SQL）

## Overview

- Compute engine: `HOLO`
- Content format: sql
- Extension: `.sql`
- Data source type: `hologres`
- Code: 1093
- Description: Hologres SQL node for executing Hologres SQL queries and analysis

Hologres is seamlessly integrated with MaxCompute at the underlying layer. Without migrating data, you can use the Hologres SQL node to directly query and analyze large-scale data in MaxCompute using standard PostgreSQL statements. This node supports Hologres-compatible PostgreSQL syntax and is suitable for data querying and analysis in real-time data warehouse scenarios.

## Prerequisites

- A Hologres compute engine instance has been added on the DataWorks workspace configuration page
- RAM users must have **Developer** or **Workspace Admin** role permissions

## Core Features

### SQL Syntax

Hologres SQL is PostgreSQL-syntax compatible and supports standard DDL and DML operations:

```sql
-- Create table
CREATE TABLE IF NOT EXISTS user_profile (
  user_id BIGINT NOT NULL,
  user_name TEXT,
  age INT,
  city TEXT,
  PRIMARY KEY (user_id)
);

-- Query data (supports scheduling parameters)
SELECT col_1, col_2
FROM your_table_name
WHERE pt > ${pt_num}
LIMIT 500;

-- Joint query with MaxCompute external table
SELECT h.user_id, h.user_name, m.order_amount
FROM user_profile h
JOIN odps_external_table m ON h.user_id = m.user_id
WHERE m.dt = '${bizdate}';
```

### Scheduling Parameters

Supports defining dynamic parameters using `${variable_name}` syntax, with values assigned in the scheduling configuration.

### Steps

1. Write task code in the SQL editing area
2. Select the compute resource and resource group in the run configuration
3. Select the created Hologres data source from the data source dropdown in the toolbar
4. Click Run to execute the task and save the node
5. Configure node scheduling information according to business requirements
6. Publish the node to the production environment

## Restrictions

- Query results display limit: up to 10,000 rows
- Defaults to 200 rows when `LIMIT` is not specified
- Accessing data sources on public network or VPC environments requires using a scheduling resource group that has passed the connectivity test

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_hologres_sql",
        "script": {
          "path": "example_hologres_sql",
          "runtime": {
            "command": "HOLOGRES_SQL"
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
