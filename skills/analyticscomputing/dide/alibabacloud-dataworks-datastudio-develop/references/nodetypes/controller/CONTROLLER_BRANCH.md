# Branch Node（CONTROLLER_BRANCH）

## Overview

The branch node is a controller node that dispatches the workflow to different downstream branches based on condition expressions.Multiple branch conditions are defined via the `branch.branches` array; at runtime, they are matched in order, and the branch whose condition is met gets activated.

## Configuration

Branch conditions are configured via the `branch` field:

```json
{
  "name": "my_branch",
  "script": {
    "path": "my_branch",
    "runtime": { "command": "CONTROLLER_BRANCH" },
    "content": ""
  },
  "branch": {
    "branches": [
      {
        "when": "${status} == 'success'",
        "output": "branch_success_output"
      },
      {
        "when": "${status} == 'failure'",
        "output": "branch_failure_output"
      }
    ]
  }
}
```

### Field Description

| Field | Type | Description |
|------|------|------|
| `branch.branches` | array | List of branch conditions, matched in order |
| `branches[].when` | string | Branch condition expression |
| `branches[].output` | string | Output identifier when the branch condition is met; downstream nodes establish dependencies via this identifier |

### script.content

The branch node's `script.content` is an empty string `""`.

## Full Example

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "recurrence": "Normal",
        "name": "my_branch",
        "script": {
          "path": "my_branch",
          "runtime": { "command": "CONTROLLER_BRANCH" },
          "content": ""
        },
        "branch": {
          "branches": [
            {
              "when": "${status} == 'success'",
              "output": "${projectIdentifier}.my_branch.branch_success"
            },
            {
              "when": "${status} == 'failure'",
              "output": "${projectIdentifier}.my_branch.branch_failure"
            }
          ]
        },
        "outputs": {
          "nodeOutputs": [
            { "data": "${projectIdentifier}.my_branch", "artifactType": "NodeOutput" }
          ]
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "my_branch",
        "depends": [
          { "type": "Normal", "output": "${projectIdentifier}_root" }
        ]
      }
    ]
  }
}
```
