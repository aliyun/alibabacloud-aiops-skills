# MaxCompute Python Resource（ODPS_PYTHON）

## Overview

- Compute engine: `ODPS`
- Content format: empty (no code)
- Extension: `.json`
- Code: 12
- Data source type: `odps`
- Label type: RESOURCE
- Description: MaxCompute Python resource

The Python resource node is used to upload Python script files to a MaxCompute project for use by PyODPS nodes, Python UDFs, or Spark Python jobs. Resources must be published after upload before they can be used by other nodes.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource

## Usage Notes

- Resources must be published before they can be referenced by other nodes
- Can serve as a dependency resource for Python UDFs
- Referenced in PyODPS nodes via the `##@resource_reference{resource_name}` comment

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_odps_python",
        "script": {
          "path": "example_odps_python",
          "runtime": {
            "command": "ODPS_PYTHON"
          },
          "content": ""
        }
      }
    ]
  }
}
```
