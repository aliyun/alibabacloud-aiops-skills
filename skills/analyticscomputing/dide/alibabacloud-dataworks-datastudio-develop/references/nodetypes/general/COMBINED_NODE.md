# Combined Node (COMBINED_NODE)

## Overview

- Compute engine: `GENERAL`
- Content format: json
- Extension: `.json`
- Description: Combined node that encapsulates multiple logical steps into a single schedulable node unit

The Combined node is used to encapsulate multiple ordered processing steps within a single node, executing them sequentially in order. It is suitable for scenarios where multiple related operations need to be scheduled and managed as a whole, simplifying the workflow structure.

## Content Structure

`script.content` is the JSON configuration for the internal steps of the combined node.

## Restrictions

- Internal steps of the combined node are executed serially in order.
- If any internal step fails, the entire combined node is marked as failed.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_combined_node",
        "script": {
          "path": "example_combined_node",
          "runtime": {
            "command": "COMBINED_NODE"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```

## Reference

- [Combined Node](https://help.aliyun.com/zh/dataworks/user-guide/combined-node)
