# EMR Impala SQL（EMR_IMPALA）

## Overview

- Compute engine: `EMR`
- Content format: sql
- Extension: `.sql`
- Data source type: `emr`
- Code: 260
- Description: Run Impala SQL queries on EMR clusters

Execute SQL statements on the Impala engine of EMR clusters through DataWorks scheduling, suitable for scenarios requiring low-latency interactive analysis. Impala is a massively parallel processing SQL engine based on in-memory computing, providing sub-second query responses.

## Prerequisites

- An EMR cluster has been created and added as a DataWorks compute resource
- The DataWorks resource group has network connectivity with the EMR cluster
- EMR cluster has Impala service installed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_emr_impala",
        "script": {
          "path": "example_emr_impala",
          "runtime": {
            "command": "EMR_IMPALA"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Reference

- [EMR Impala Node](https://help.aliyun.com/zh/dataworks/user-guide/emr-impala-node)
