# Check Node (CHECK)

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no code)
- Extension: `.json`
- Description: Legacy check node for verifying the availability of target objects

The Check node (legacy) is used to verify whether upstream data or target objects are ready before a workflow runs. Once the check conditions are met, the node returns a success status and triggers downstream task execution. For new tasks, it is recommended to use the new Check node (CHECK_NODE).

## Restrictions

- This node has been replaced by the new CHECK_NODE; it is recommended to use the new version.
- Check logic is configured via parameters; `script.content` is empty.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_check",
        "script": {
          "path": "example_check",
          "runtime": {
            "command": "CHECK"
          },
          "content": ""
        }
      }
    ]
  }
}
```
