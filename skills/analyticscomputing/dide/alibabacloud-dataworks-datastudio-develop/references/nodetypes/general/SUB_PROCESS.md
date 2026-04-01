# Sub-workflow Container (SUB_PROCESS)

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no code)
- Extension: none
- Description: Sub-workflow container node for nesting and referencing another workflow within a workflow

The Sub-workflow container (also known as inner node) is used to embed a complete workflow as a sub-process within the current workflow. Sub-workflows enable modular management and reuse of processes, breaking down complex scheduling logic into multiple maintainable sub-processes.

## Restrictions

- The sub-workflow container itself does not contain script content; `script.content` is empty.
- Nodes within the sub-workflow are independently scheduled and executed according to their own dependency relationships.
- The sub-workflow must be created and published before it can be referenced.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_sub_process",
        "script": {
          "path": "example_sub_process",
          "runtime": {
            "command": "SUB_PROCESS"
          },
          "content": ""
        }
      }
    ]
  }
}
```

## Reference

- [Inner Node](https://help.aliyun.com/zh/dataworks/user-guide/inner-node)
