# EMR Presto SQL（EMR_PRESTO）

## Overview

- Compute engine: `EMR`
- Content format: sql
- Extension: `.sql`
- Data source type: `emr`
- Code: 259
- Description: Run Presto SQL queries on EMR clusters

Execute SQL statements on the Presto engine of EMR clusters through DataWorks scheduling, suitable for scenarios requiring interactive analysis and cross-data-source federated queries. Presto is a distributed SQL query engine that excels at low-latency ad-hoc queries.

## Prerequisites

- An EMR cluster has been created and added as a DataWorks compute resource
- The DataWorks resource group has network connectivity with the EMR cluster
- EMR cluster has Presto service installed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_emr_presto",
        "script": {
          "path": "example_emr_presto",
          "runtime": {
            "command": "EMR_PRESTO"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Reference

- [EMR Presto Node](https://help.aliyun.com/zh/dataworks/user-guide/emr-presto-node)
