# EMR Table（EMR_TABLE）

## Overview

- Compute engine: `EMR`
- Content format: empty (no code)
- Extension: none
- Data source type: `emr`
- Code: 261
- LabelType：TABLE
- Description: Manage Hive tables for EMR clusters in DataWorks

Used in DataWorks to define and manage Hive/SparkSQL table structures on EMR clusters, supporting table creation, modification, and metadata management.

## Prerequisites

- An EMR cluster has been created and added as a DataWorks compute resource
- The DataWorks resource group has network connectivity with the EMR cluster
- EMR cluster has Hive Metastore service installed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_emr_table",
        "script": {
          "path": "example_emr_table",
          "runtime": {
            "command": "EMR_TABLE"
          },
          "content": ""
        }
      }
    ]
  }
}
```
