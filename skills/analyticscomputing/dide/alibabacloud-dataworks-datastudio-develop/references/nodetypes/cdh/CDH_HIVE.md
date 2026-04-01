# CDH Hive SQL (CDH_HIVE)

## Overview

- Compute engine: `HADOOP_CDH`
- Content format: sql
- Extension: `.sql`
- Data source type: `cdh`
- Description: Executes Hive SQL statements on CDH clusters

Used to run SQL queries and data processing tasks on the Hive engine of Cloudera CDH clusters. Suitable for Hive-based ETL data processing, table creation, and data query scenarios.

## Prerequisites

- CDH cluster has been added as a compute resource to the DataWorks workspace
- DataWorks resource group has network connectivity with the CDH cluster
- CDH cluster has Hive service deployed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_cdh_hive",
        "script": {
          "path": "example_cdh_hive",
          "runtime": {
            "command": "CDH_HIVE"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```
