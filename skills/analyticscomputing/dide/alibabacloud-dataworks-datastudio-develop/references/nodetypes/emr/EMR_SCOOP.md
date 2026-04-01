# EMR Sqoop（EMR_SCOOP）

## Overview

- Compute engine: `EMR`
- Content format: empty (no code)
- Extension: none
- Data source type: `emr`
- Code: 263
- Description: Run Sqoop data migration tasks on EMR clusters

Execute data import and export tasks between relational databases and Hadoop on EMR clusters using the Sqoop tool, suitable for bulk data transfer scenarios between RDBMS and HDFS/Hive.

## Prerequisites

- An EMR cluster has been created and added as a DataWorks compute resource
- The DataWorks resource group has network connectivity with the EMR cluster
- EMR cluster has Sqoop service installed
- The target relational database has network connectivity with the EMR cluster

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_emr_scoop",
        "script": {
          "path": "example_emr_scoop",
          "runtime": {
            "command": "EMR_SCOOP"
          },
          "content": ""
        }
      }
    ]
  }
}
```
