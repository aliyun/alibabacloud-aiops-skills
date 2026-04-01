# Merge Node（CONTROLLER_JOIN）

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no code)
- Extension: `.join.json`

The merge node is a logical control node used to consolidate the run status of upstream nodes, solving dependency mounting and run triggering issues downstream of branch nodes.

**Typical scenario**: Branch node C defines two mutually exclusive branches C1 and C2 that write data to the same table. Downstream node B cannot directly depend on C1 and C2 (unselected branches will cause B to empty-run). A merge node J must first consolidate the two branches, then let B depend on J.

```
Branch Node C
├── C1 (executed when condition is met)
└── C2 (executed when condition is not met)
       ↘  ↙
    Merge Node J
         ↓
    Downstream Node B
```

## Merge Conditions

| Logic | Description |
|------|------|
| AND | All branches must be in terminal state and all must satisfy the configured run status for the merge node to be marked as success |
| OR | All branches must be in terminal state; if any branch satisfies the configured run status, the merge node is marked as success |

**Node run status options**:
- Success: Node ran successfully
- Failure: Node ran and failed
- Branch not run: Empty-run status when a node is not selected (only applies when the upstream is a branch node)

## Configuration

Merging is achieved through dual-writing dependencies via `inputs.nodeOutputs` + `flow.depends`.

```json
{
  "recurrence": "Normal",
  "name": "join_node",
  "script": {
    "path": "join_node",
    "runtime": { "command": "CONTROLLER_JOIN" },
    "content": ""
  },
  "inputs": {
    "nodeOutputs": [
      { "data": "branch_a_output" },
      { "data": "branch_b_output" }
    ]
  }
}
```

Also declare dependencies in `flow.depends`:

```json
{
  "nodeId": "join_node",
  "depends": [
    { "nodeId": "branch_a", "type": "Normal" },
    { "nodeId": "branch_b", "type": "Normal" }
  ]
}
```

### Field Description

| Configuration | Description |
|--------|------|
| `script.content` | Must be an empty string `""`; cannot be `"{}"` |
| `inputs.nodeOutputs` | List all upstream branch outputs that need to be merged |
| `flow.depends` | Keep consistent with `inputs.nodeOutputs`, dual-write dependencies |

## Full Example

Used with branch nodes to merge two branches:

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "recurrence": "Normal",
        "name": "join_node",
        "script": {
          "path": "join_node",
          "runtime": { "command": "CONTROLLER_JOIN" },
          "content": ""
        },
        "inputs": {
          "nodeOutputs": [
            { "data": "${projectIdentifier}.branch_a", "artifactType": "NodeOutput" },
            { "data": "${projectIdentifier}.branch_b", "artifactType": "NodeOutput" }
          ]
        },
        "outputs": {
          "nodeOutputs": [
            { "data": "${projectIdentifier}.join_node", "artifactType": "NodeOutput" }
          ]
        }
      }
    ],
    "flow": [
      {
        "nodeId": "join_node",
        "depends": [
          { "nodeId": "branch_a", "type": "Normal" },
          { "nodeId": "branch_b", "type": "Normal" }
        ]
      }
    ]
  }
}
```

## Restrictions

| Restriction | Details |
|--------|------|
| Version requirement | DataWorks Standard Edition or above |
| Execution result | Currently only supports setting to success status |
| Node type | Logical control node; does not perform computation |
