# CDH Presto SQL (CDH_PRESTO)

## Overview

- Compute engine: `HADOOP_CDH`
- Content format: sql
- Extension: `.sql`
- Data source type: `cdh`
- Description: Executes Presto SQL queries on CDH clusters

Used to run SQL queries on the Presto engine of Cloudera CDH clusters. Presto is a distributed SQL query engine suitable for interactive low-latency queries across multiple data sources.

## Prerequisites

- CDH cluster has been added as a compute resource to the DataWorks workspace
- DataWorks resource group has network connectivity with the CDH cluster
- CDH cluster has Presto service deployed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_cdh_presto",
        "script": {
          "path": "example_cdh_presto",
          "runtime": {
            "command": "CDH_PRESTO"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```
