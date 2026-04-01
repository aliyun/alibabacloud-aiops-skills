# MaxCompute Extreme Storage（EXTREME_STORAGE）

## Overview

- Compute engine: `ODPS`
- Content format: empty (no code)
- Extension: `.mc.extreme.store.sh`
- Code: 30
- Data source type: `odps`
- Description: Extreme storage node

The extreme storage node is used to manage MaxCompute table storage format conversion, converting table data to the extreme storage format to improve query performance. This node does not require writing code and can be completed through configuration.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_extreme_storage",
        "script": {
          "path": "example_extreme_storage",
          "runtime": {
            "command": "EXTREME_STORAGE"
          },
          "content": ""
        }
      }
    ]
  }
}
```
