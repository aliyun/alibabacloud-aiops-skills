# EMR Kyuubi SQL（EMR_KYUUBI）

## Overview

- Compute engine: `EMR`
- Content format: sql
- Extension: `.sql`
- Data source type: `emr`
- Code: 268
- Description: Run SQL queries via Kyuubi on EMR clusters

Execute SQL statements on the Kyuubi service of EMR clusters through DataWorks scheduling. Kyuubi is a distributed multi-tenant Thrift/JDBC/ODBC service gateway that supports multiple backend engines such as Spark, Flink, Trino, etc., suitable for scenarios requiring a unified SQL entry point to access multiple compute engines.

## Prerequisites

- An EMR cluster has been created and added as a DataWorks compute resource
- The DataWorks resource group has network connectivity with the EMR cluster
- EMR cluster has Kyuubi service installed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_emr_kyuubi",
        "script": {
          "path": "example_emr_kyuubi",
          "runtime": {
            "command": "EMR_KYUUBI"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Reference

- [EMR Kyuubi Node](https://help.aliyun.com/zh/dataworks/user-guide/emr-kyuubi-node)
