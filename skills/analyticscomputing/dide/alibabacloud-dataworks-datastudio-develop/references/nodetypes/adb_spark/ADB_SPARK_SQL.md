# ADB Spark SQL (ADB_SPARK_SQL)

## Overview

- Compute engine: `ADB_SPARK`
- Content format: sql
- Extension: `.adb.spark.sql`
- Data source type: `adb_spark`
- Description: AnalyticDB Spark SQL query task

The ADB Spark SQL node is used to develop and schedule AnalyticDB Spark SQL tasks in DataWorks. Through this node, you can directly write SQL statements to query and analyze data in AnalyticDB, and incorporate them into the DataWorks periodic scheduling system for orchestration with other types of data development tasks. This node is suitable for data analysis and computation, periodic batch data processing, and cross-system data integration scenarios.

## Configuration

The node requires the following runtime properties to be configured:

| Parameter | Description |
|-----------|-------------|
| Compute Resource | Select the bound AnalyticDB for Spark compute resource |
| ADB Compute Resource Group | Interactive-type resource group (Spark engine) configured in the AnalyticDB cluster |
| Resource Group | DataWorks resource group that has passed the connectivity test |
| Compute CU | Use the default value; generally no modification needed |

The SQL editing area supports using `${variable_name}` syntax to define dynamic parameters (e.g., `$[yyyymmdd]` for date processing), external library references, internal table creation, OSS storage integration, and Parquet compression format settings.

## Prerequisites

- An AnalyticDB for MySQL cluster (Enterprise Edition, Lakehouse Edition, or Basic Edition) has been created in the same region as the DataWorks workspace, with an Interactive-type resource group (Spark engine) configured.
- The DataWorks workspace has enabled the new Data Studio (Data Development).
- The DataWorks resource group and the AnalyticDB cluster are in the same VPC, and the IP whitelist has been configured.
- The AnalyticDB cluster has been added as a compute resource (type: AnalyticDB for Spark) to the workspace and has passed the resource group connectivity test.
- If using OSS storage, ensure OSS and the cluster are in the same region.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_adb_spark_sql",
        "script": {
          "path": "example_adb_spark_sql",
          "runtime": {
            "command": "ADB Spark SQL"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Restrictions

- Only workspaces with the new Data Studio (Data Development) enabled are supported.
- The AnalyticDB cluster must have an Interactive-type resource group (Spark engine) configured; otherwise, Spark SQL tasks cannot be executed.
- Debug runs require first configuring compute resources, ADB compute resource group, resource group, and compute CU runtime properties.

## Reference

- [ADB Spark SQL Node - Alibaba Cloud Documentation](https://help.aliyun.com/zh/dataworks/user-guide/adb-spark-sql-node)
