# MaxCompute File Resource（ODPS_FILE）

## Overview

- Compute engine: `ODPS`
- Content format: empty (no code)
- Extension: `.json`
- Code: 15
- Data source type: `odps`
- Label type: RESOURCE
- Description: MaxCompute file resource

The file resource node is used to upload text files, configuration files, etc. to a MaxCompute project for use by SQL nodes, MapReduce jobs, etc. Resources must be published after upload before they can be used by other nodes.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource

## Usage Notes

- Resources must be published before they can be referenced by other nodes
- Commonly used to upload configuration files, dictionary files, etc.
- Can be referenced in SQL nodes via the `add file` command

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_odps_file",
        "script": {
          "path": "example_odps_file",
          "runtime": {
            "command": "ODPS_FILE"
          },
          "content": ""
        }
      }
    ]
  }
}
```
