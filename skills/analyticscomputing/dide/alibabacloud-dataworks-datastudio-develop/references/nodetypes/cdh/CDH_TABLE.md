# CDH Table (CDH_TABLE)

## Overview

- Compute engine: `HADOOP_CDH`
- Content format: empty (no code)
- Extension: none
- Data source type: `cdh`
- Label type: TABLE
- Description: Manages Hive table metadata on CDH clusters

Used to manage table objects (such as Hive tables) on CDH clusters in DataWorks. This node type is for table metadata registration and management and does not contain executable code.

## Prerequisites

- CDH cluster has been added as a compute resource to the DataWorks workspace
- DataWorks resource group has network connectivity with the CDH cluster
- CDH cluster has Hive Metastore service deployed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_cdh_table",
        "script": {
          "path": "example_cdh_table",
          "runtime": {
            "command": "CDH_TABLE"
          },
          "content": ""
        }
      }
    ]
  }
}
```

## Restrictions\n\n- The node content format is empty; table structure is defined through metadata configuration rather than code
