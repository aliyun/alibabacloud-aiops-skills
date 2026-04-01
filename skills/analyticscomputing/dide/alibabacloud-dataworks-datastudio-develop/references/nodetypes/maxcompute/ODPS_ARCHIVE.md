# MaxCompute Archive Resource（ODPS_ARCHIVE）

## Overview

- Compute engine: `ODPS`
- Content format: empty (no code)
- Extension: `.json`
- Code: 14
- Data source type: `odps`
- Label type: RESOURCE
- Description: MaxCompute Archive resource

The Archive resource node is used to upload compressed archive files (such as .tar.gz, .zip, etc.) to a MaxCompute project for use by MapReduce jobs, Spark jobs, etc. Resources must be published after upload before they can be used by other nodes.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource

## Usage Notes

- Resources must be published before they can be referenced by other nodes
- Supported archive formats include .tar.gz, .zip, etc.
- Commonly used to upload dependency packages containing multiple files

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_odps_archive",
        "script": {
          "path": "example_odps_archive",
          "runtime": {
            "command": "ODPS_ARCHIVE"
          },
          "content": ""
        }
      }
    ]
  }
}
```
