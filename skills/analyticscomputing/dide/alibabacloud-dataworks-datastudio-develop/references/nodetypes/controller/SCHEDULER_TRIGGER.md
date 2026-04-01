# Trigger Node（SCHEDULER_TRIGGER）

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no code)
- Extension: `.json`
- Description: HTTP trigger node, no code

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_scheduler_trigger",
        "script": {
          "path": "example_scheduler_trigger",
          "runtime": {
            "command": "SCHEDULER_TRIGGER"
          },
          "content": ""
        }
      }
    ]
  }
}
```
