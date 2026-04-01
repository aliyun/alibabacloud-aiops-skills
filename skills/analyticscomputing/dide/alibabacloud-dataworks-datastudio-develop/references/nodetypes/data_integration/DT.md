# DT Data Sync（DT）

## Overview

- Code: `21`
- Compute engine: `DI`
- Content format: json
- Extension: `.json`
- LabelType: `DATA_PROCESS`
- Description: DT Data sync task

DT is a data sync node type in DataWorks Data Integration. The content is a JSON configuration object used to define data transfer tasks.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_dt",
        "script": {
          "path": "example_dt",
          "runtime": {
            "command": "DT"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```
