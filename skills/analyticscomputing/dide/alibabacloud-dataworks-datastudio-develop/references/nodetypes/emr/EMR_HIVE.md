# EMR Hive SQL（EMR_HIVE）

## Overview

- Compute engine: `EMR`
- Content format: sql
- Extension: `.sql`
- Data source type: `emr`
- Code: 227
- Description: Run Hive SQL queries on EMR clusters

Execute Hive SQL statements on Alibaba Cloud E-MapReduce clusters through DataWorks scheduling, suitable for Hive-based data warehouse ETL processing, data querying, and analysis scenarios.

## Prerequisites

- An EMR cluster has been created and added as a DataWorks compute resource
- The DataWorks resource group has network connectivity with the EMR cluster
- EMR cluster has Hive service installed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_emr_hive",
        "script": {
          "path": "example_emr_hive",
          "runtime": {
            "command": "EMR_HIVE"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Reference

- [EMR Hive Node](https://help.aliyun.com/zh/dataworks/user-guide/emr-hive-node)
