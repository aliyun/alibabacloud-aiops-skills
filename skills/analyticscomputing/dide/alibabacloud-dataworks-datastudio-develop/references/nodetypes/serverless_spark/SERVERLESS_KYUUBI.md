# Serverless Kyuubi SQL (SERVERLESS_KYUUBI)

## Overview

- Compute engine: `EMR`
- Content format: sql
- Extension: `.sql`
- Data source type: `emr`
- Code: 2103
- Description: Serverless Kyuubi SQL node, based on the Apache Kyuubi multi-tenant SQL gateway

The Serverless Kyuubi SQL node is used to submit Spark SQL queries through the Apache Kyuubi multi-tenant SQL gateway. Kyuubi is a distributed multi-tenant gateway that provides Serverless SQL on Spark capabilities, supporting multiple users sharing Spark engine resources with better resource isolation and session management features.

## Prerequisites

- An EMR Serverless Spark compute resource has been bound, with the Kyuubi service enabled
- Ensure the resource group has network connectivity with the compute resource
- Only Serverless resource groups are supported for running this task type
- RAM users must have **Developer** or **Workspace Admin** role permissions

## Core Features

### SQL Syntax

Kyuubi SQL supports the full Spark SQL syntax, submitted for execution through the Kyuubi gateway:

```sql
-- Data query
SELECT dt, COUNT(DISTINCT user_id) AS uv, COUNT(*) AS pv
FROM user_log
WHERE dt = '${bizdate}'
GROUP BY dt;

-- Create table
CREATE TABLE IF NOT EXISTS dwd_order_detail (
  order_id BIGINT COMMENT 'Order ID',
  user_id BIGINT COMMENT 'User ID',
  amount DECIMAL(10, 2) COMMENT 'Order amount',
  order_time TIMESTAMP COMMENT 'Order time'
) PARTITIONED BY (dt STRING)
STORED AS PARQUET;

-- Data write
INSERT OVERWRITE TABLE dwd_order_detail PARTITION (dt = '${bizdate}')
SELECT order_id, user_id, amount, order_time
FROM ods_order
WHERE dt = '${bizdate}';
```

### Scheduling Parameters

Supports defining dynamic parameters using `${variable_name}` syntax, with values assigned in the scheduling configuration.

### Differences from Serverless Spark SQL

| Feature | Kyuubi SQL | Spark SQL |
|------|-----------|-----------|
| Execution engine | Via Kyuubi gateway | Direct Spark SQL |
| Multi-tenant | Natively supported | Requires additional configuration |
| Session management | Kyuubi session pool | Independent session |
| Resource sharing | Shared Spark engine | Independent engine |
| Applicable scenarios | Multi-user interactive queries | Batch SQL tasks |

### Advantages

- **Multi-tenant isolation**: Supports multiple simultaneous users with mutual isolation
- **Session reuse**: Reuses Spark engines via session pool mechanism, reducing startup time
- **Standard interfaces**: Compatible with JDBC/ODBC standard protocols
- **Resource elasticity**: Based on Serverless architecture, resources are allocated on demand

## Restrictions

- Only Serverless resource groups are supported for execution
- The EMR Serverless Spark cluster must have the Kyuubi service enabled
- SQL syntax is limited by the Spark SQL version

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_serverless_kyuubi",
        "script": {
          "path": "example_serverless_kyuubi",
          "runtime": {
            "command": "SERVERLESS_KYUUBI"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Related Documentation

- [Serverless Kyuubi SQL Node](https://help.aliyun.com/zh/dataworks/user-guide/serverless-kyuubi-node)
