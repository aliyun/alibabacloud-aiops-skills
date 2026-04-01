# Table Merge（TT_MERGE）

## Overview

- Code: `200`
- Compute engine: `DI`
- Content format: json
- Extension: `.json`
- LabelType: `DATA_PROCESS`
- Description: Table merge task

TT_MERGE is used to merge data from multiple tables and write it into a single target table. The content is a JSON configuration object that defines the source tables, target table, and merge strategy.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_tt_merge",
        "script": {
          "path": "example_tt_merge",
          "runtime": {
            "command": "TT_MERGE"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```
