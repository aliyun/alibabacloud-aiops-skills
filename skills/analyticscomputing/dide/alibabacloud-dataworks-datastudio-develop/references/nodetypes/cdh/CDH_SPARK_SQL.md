# CDH Spark SQL (CDH_SPARK_SQL)

## Overview

- Compute engine: `HADOOP_CDH`
- Content format: sql
- Extension: `.sql`
- Data source type: `cdh`
- Description: Executes Spark SQL statements on CDH clusters

Used to run SQL queries on the Spark SQL engine of Cloudera CDH clusters. Compared to Hive SQL, Spark SQL typically offers better execution performance, suitable for data processing scenarios requiring higher query efficiency.

## Prerequisites

- CDH cluster has been added as a compute resource to the DataWorks workspace
- DataWorks resource group has network connectivity with the CDH cluster
- CDH cluster has Spark service deployed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_cdh_spark_sql",
        "script": {
          "path": "example_cdh_spark_sql",
          "runtime": {
            "command": "CDH_SPARK_SQL"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```
