# EMR Spark SQL（EMR_SPARK_SQL）

## Overview

- Compute engine: `EMR`
- Content format: sql
- Extension: `.sql`
- Data source type: `emr`
- Code: 229
- Description: Run Spark SQL queries on EMR clusters

Execute SQL statements on the Spark SQL engine of EMR clusters through DataWorks scheduling, suitable for data processing and analysis scenarios using Spark SQL. Spark SQL is compatible with Hive SQL syntax while providing richer built-in functions and better performance.

## Prerequisites

- An EMR cluster has been created and added as a DataWorks compute resource
- The DataWorks resource group has network connectivity with the EMR cluster
- EMR cluster has Spark service installed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_emr_spark_sql",
        "script": {
          "path": "example_emr_spark_sql",
          "runtime": {
            "command": "EMR_SPARK_SQL"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Reference

- [EMR Spark SQL Node](https://help.aliyun.com/zh/dataworks/user-guide/emr-spark-sql-node)
