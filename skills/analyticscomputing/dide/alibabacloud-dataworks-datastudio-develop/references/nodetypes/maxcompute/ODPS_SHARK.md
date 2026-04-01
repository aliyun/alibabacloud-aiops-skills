# MaxCompute Shark（ODPS_SHARK）

## Overview

- Compute engine: `ODPS`
- Content format: json
- Extension: `.mc.shark.json`
- Code: 223
- Data source type: `odps`
- Description: MaxCompute Shark configuration

The MaxCompute Shark node is used to configure and run Shark jobs. Shark is an early Hive-compatible query engine, and this node type is mainly retained for compatibility with existing tasks.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource

## Content Structure

```json
{
  "type": "JSON configuration object"
}
```

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_odps_shark",
        "script": {
          "path": "example_odps_shark",
          "runtime": {
            "command": "ODPS_SHARK"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```
