# Serverless Spark SQL (SERVERLESS_SPARK_SQL)

## Overview

- Compute engine: `EMR`
- Content format: sql
- Extension: `.sql`
- Data source type: `emr`
- Code: 2101
- Description: Serverless Spark SQL node, distributed SQL queries based on EMR Serverless Spark

By creating a Serverless Spark SQL node, you can process structured data using the distributed SQL query engine based on EMR Serverless Spark compute resources, improving job execution efficiency. This node does not require managing cluster infrastructure and uses the Spark SQL engine to execute queries on demand.

## Prerequisites

- An EMR Serverless Spark compute resource has been bound, Ensure the resource group has network connectivity with the compute resource
- Only Serverless resource groups are supported for running this task type
- RAM users must have **Developer** or **Workspace Admin** role permissions (can be ignored for primary accounts)

## Core Features

### SQL Syntax

Supports the full `catalog.database.tablename` syntax. If the `catalog` parameter is omitted, the system uses the cluster's default Catalog; if `catalog.database` is omitted, the default database of the default Catalog is used.

```sql
-- Basic query
SELECT * FROM <catalog.database.tablename>;

-- Create table (using scheduling parameters)
CREATE TABLE IF NOT EXISTS userinfo_new_${var}(
  ip STRING COMMENT 'IP address',
  uid STRING COMMENT 'User ID'
) PARTITIONED BY (dt STRING);

-- Data query and aggregation
SELECT dt, COUNT(DISTINCT uid) AS uv
FROM user_log
WHERE dt = '${bizdate}'
GROUP BY dt;
```

### Scheduling Parameters

Define dynamic variables using `${variable_name}` syntax, with values assigned in the scheduling configuration. Supports scheduling parameter expressions such as `${yyyymmdd}` for dynamic parameter passing.

### Advanced Parameters

| Parameter | Description | Default value |
|------|------|--------|
| `FLOW_SKIP_SQL_ANALYZE` | `true` executes multiple SQL statements at once; `false` executes them one by one | `false` |
| `DATAWORKS_SESSION_DISABLE` | `true` submits to the queue for execution; `false` executes via SQL Compute | `false` |
| `SERVERLESS_RELEASE_VERSION` | Specifies the Spark engine version | Cluster default version |
| `SERVERLESS_QUEUE_NAME` | Specifies the resource queue for task submission | Default queue |
| `SERVERLESS_SQL_COMPUTE` | Specifies the SQL session | Cluster default session |

## Restrictions

- SQL statements must not exceed **130KB**
- Only Serverless resource groups are supported for execution

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_serverless_spark_sql",
        "script": {
          "path": "example_serverless_spark_sql",
          "runtime": {
            "command": "SERVERLESS_SPARK_SQL"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Related Documentation

- [Serverless Spark SQL Node](https://help.aliyun.com/zh/dataworks/user-guide/serverless-spark-sql-node)
