# ClickHouse SQL（CLICK_SQL）

## Overview

- Compute engine: `CLICKHOUSE`
- Content format: sql
- Extension: `.sql`
- Data source type: `clickhouse`
- Description: Execute SQL statements against ClickHouse database

Used to directly execute SQL queries and data processing against ClickHouse columnar storage database to execute SQL queries and data processing. The corresponding data source type must be registered in the workspace beforehand.

> Note: The compute engine for ClickHouse nodes is `CLICKHOUSE`, which differs from the `DATABASE` engine used by other database-type nodes.

## Prerequisites

- The data source type has been added to the DataWorks workspace ClickHouse type data source
- The data source connectivity test has passed
- A ClickHouse cluster has been provisioned and network connectivity is confirmed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_click_sql",
        "script": {
          "path": "example_click_sql",
          "runtime": {
            "command": "CLICK_SQL"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Supported SQL Operations

- **DDL**: CREATE TABLE, DROP TABLE, ALTER TABLE, CREATE VIEW, etc.
- **DML**: INSERT INTO, SELECT ... INTO, etc.
- **Queries**: SELECT (supports JOIN, subqueries, aggregate functions, window functions, etc.)
- **ClickHouse-specific syntax**: MergeTree family engine table creation, MATERIALIZED VIEW, partition operations, etc.

## Restrictions

- SQL syntax must comply with ClickHouse SQL specifications
- ClickHouse does not support standard UPDATE and DELETE statements; use ALTER TABLE ... UPDATE/DELETE (Mutation operations) instead
- Only one SQL statement can be executed at a time
- Execution timeout is limited by the data source configuration
- ClickHouse has limited transaction support; pay attention to data consistency

## Reference

- [ClickHouse SQL Node Documentation](https://help.aliyun.com/zh/dataworks/user-guide/clickhouse-sql-node)
