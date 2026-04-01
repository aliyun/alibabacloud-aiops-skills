# MaxCompute JAR Resource（ODPS_JAR）

## Overview

- Compute engine: `ODPS`
- Content format: empty (no code)
- Extension: `.json`
- Code: 13
- Data source type: `odps`
- Label type: RESOURCE
- Description: MaxCompute JAR resource

The JAR resource node is used to upload Java JAR packages to a MaxCompute project for use by MapReduce jobs, UDF functions, Spark jobs, etc. Resources must be published after upload before they can be used by other nodes.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource

## Usage Notes

- Resources must be published before they can be referenced by other nodes
- Referenced by resource name in ODPS_MR or ODPS_SPARK nodes
- Used as a UDF dependency resource in ODPS_FUNCTION

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_odps_jar",
        "script": {
          "path": "example_odps_jar",
          "runtime": {
            "command": "ODPS_JAR"
          },
          "content": ""
        }
      }
    ]
  }
}
```
