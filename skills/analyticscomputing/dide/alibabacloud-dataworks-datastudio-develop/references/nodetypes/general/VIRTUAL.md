# Virtual Node (VIRTUAL)

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no code)
- Extension: `.vi`
- Description: An empty-run node that produces no data; the scheduler returns success directly

The Virtual node is a control-type node. During scheduled execution, the system returns success directly without consuming resources, performing any operations, or blocking downstream execution. It is commonly used in the following scenarios:

- As the orchestration starting node of a workflow, making the data flow path clearer.
- As a consolidated output node for multiple branch nodes.
- When multiple input nodes without dependency relationships need to be scheduled together, a Virtual node can serve as the upstream to manage downstream branches uniformly, and can control the earliest run time of each branch through scheduled timing.

## Prerequisites

- The RAM account must be added to the corresponding workspace with Developer or Workspace Admin role permissions.
- The workspace must have a Serverless resource group bound.

## Restrictions

- The Virtual node has no script content; only scheduling properties need to be configured.
- When the workspace root node is used as an upstream dependency, it is not displayed in the workflow panel and must be viewed in the Operation Center.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_virtual",
        "script": {
          "path": "example_virtual",
          "runtime": {
            "command": "VIRTUAL"
          },
          "content": ""
        }
      }
    ]
  }
}
```

## Reference

- [Virtual Node](https://help.aliyun.com/zh/dataworks/user-guide/virtual-node)
