# Data Merge（DD_MERGE）

## Overview

- Code: `222`
- Compute engine: `DI`
- Content format: json
- Extension: `.json`
- LabelType: `DATA_PROCESS`
- Description: Data merge task

DD_MERGE is used to merge data from multiple data sources or datasets into a unified dataset. The content is a JSON configuration object that defines the sources, targets, and merge rules.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_dd_merge",
        "script": {
          "path": "example_dd_merge",
          "runtime": {
            "command": "DD_MERGE"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```
