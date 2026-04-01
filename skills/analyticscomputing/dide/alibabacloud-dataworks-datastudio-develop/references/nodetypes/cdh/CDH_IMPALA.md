# CDH Impala SQL (CDH_IMPALA)

## Overview

- Compute engine: `HADOOP_CDH`
- Content format: sql
- Extension: `.sql`
- Data source type: `cdh`
- Description: Executes Impala SQL queries on CDH clusters

Used to run SQL queries on the Impala engine of Cloudera CDH clusters. Impala provides low-latency interactive query capabilities for HDFS and HBase data, suitable for ad-hoc queries and BI analysis scenarios requiring fast response times.

## Prerequisites

- CDH cluster has been added as a compute resource to the DataWorks workspace
- DataWorks resource group has network connectivity with the CDH cluster
- CDH cluster has Impala service deployed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_cdh_impala",
        "script": {
          "path": "example_cdh_impala",
          "runtime": {
            "command": "CDH_IMPALA"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```
