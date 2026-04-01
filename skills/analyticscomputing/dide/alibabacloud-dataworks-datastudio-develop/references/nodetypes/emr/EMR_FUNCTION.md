# EMR Function（EMR_FUNCTION）

## Overview

- Compute engine: `EMR`
- Content format: empty (no code)
- Extension: none
- Data source type: `emr`
- Code: 262
- LabelType：FUNCTION
- Description: Manage custom functions for EMR clusters in DataWorks

Used to register and manage in DataWorks EMR custom functions (UDF/UDAF/UDTF) on the cluster. Once registered, they can be called directly in Hive SQL, Spark SQL, and other nodes.

## Prerequisites

- An EMR cluster has been created and added as a DataWorks compute resource
- The DataWorks resource group has network connectivity with the EMR cluster
- The JAR resource (EMR_JAR) required by the function has been uploaded

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_emr_function",
        "script": {
          "path": "example_emr_function",
          "runtime": {
            "command": "EMR_FUNCTION"
          },
          "content": ""
        }
      }
    ]
  }
}
```
