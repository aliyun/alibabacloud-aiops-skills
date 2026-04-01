# EMR Trino SQL（EMR_TRINO）

## Overview

- Compute engine: `EMR`
- Content format: sql
- Extension: `.sql`
- Data source type: `emr`
- Code: 267
- Description: Run Trino SQL queries on EMR clusters

Execute SQL statements on the Trino engine of EMR clusters through DataWorks scheduling, suitable for interactive analysis and cross-data-source federated query scenarios. Trino (formerly PrestoSQL) is a high-performance distributed SQL query engine that supports federated queries across multiple data sources.

## Prerequisites

- An EMR cluster has been created and added as a DataWorks compute resource
- The DataWorks resource group has network connectivity with the EMR cluster
- EMR cluster has Trino service installed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_emr_trino",
        "script": {
          "path": "example_emr_trino",
          "runtime": {
            "command": "EMR_TRINO"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Reference

- [EMR Trino Node](https://help.aliyun.com/zh/dataworks/user-guide/emr-trino-node)
