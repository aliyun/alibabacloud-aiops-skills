# Loop Node（CONTROLLER_CYCLE）

## Overview

- Compute engine: `GENERAL`
- Content format: json
- Extension: `.do-while.json`

The loop node implements do-while loop logic: execute the loop body first, then determine whether to continue. It can be used standalone or combined with assignment nodes to iterate over result sets.

## Node Structure

```
do-while wrapper (CONTROLLER_CYCLE)
├── Start Node (CONTROLLER_CYCLE_START, auto-generated, cannot be deleted)
├── Loop body business nodes (multiple can be added, custom arrangement)
└── End Node (CONTROLLER_CYCLE_END, auto-generated, determines whether to continue looping)
```

- Start node: Marks the beginning of the loop; has no business function
- Loop body: Multiple child nodes can be added and executed by dependency
- End node: Executes evaluation code; returns True to continue, False to exit

**Execution flow**: Start -> Execute loop body by dependencies -> End evaluates -> If True, return to Start; if False, exit

## Loop Condition

The end node uses code to determine whether to continue looping:

```python
# Control loop 5 times
if ${dag.loopTimes} < 5:
    print True
else:
    print False
```

- Returns `True`: Continue to the next loop iteration
- Returns `False`: Exit the loop

When iterating over a dataset with an assignment node:

```python
# Iterate by dataset length
if ${dag.loopTimes} <= ${dag.input.length}:
    print True
else:
    print False
```

## Built-in Variables

| Variable | Description | Example |
|------|------|------|
| `${dag.loopTimes}` | Current loop count (starting from 1) | 1st time = 1, 2nd time = 2 |
| `${dag.offset}` | Offset (starting from 0) | 1st time = 0, 2nd time = 1 |
| `${dag.input}` | Dataset passed by assignment node | Array format |
| `${dag.input[${dag.offset}]}` | Data row for the current loop | Indexed by offset |
| `${dag.input.length}` | Dataset length | Total record count |

## Configuration

### script.content Field

Stores loop control configuration in JSON format:

| Field | Type | Default | Description |
|------|------|--------|------|
| `maxIterations` | number | 128 | Maximum iterations; exceeding this will cause an error |
| `parallelism` | number | 0 | Concurrency not supported; must be serial (next cycle starts only after the previous one completes) |

### dowhile Field

| Field | Type | Description |
|------|------|------|
| `dowhile.nodes` | array | List of child nodes within the loop body |
| `dowhile.flow` | array | Dependency relationships of child nodes within the loop body |
| `dowhile.while` | string/object | Loop continuation condition |

## Full Example

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "recurrence": "Normal",
        "name": "my_loop",
        "script": {
          "path": "my_loop",
          "runtime": { "command": "CONTROLLER_CYCLE" },
          "content": "{\"maxIterations\":128,\"parallelism\":0}"
        },
        "dowhile": {
          "nodes": [
            {
              "name": "loop_task",
              "script": {
                "path": "my_loop/loop_task",
                "runtime": { "command": "DIDE_SHELL" },
                "content": "echo \"loop iteration: ${dag.loopTimes}, offset: ${dag.offset}\""
              }
            }
          ],
          "flow": [
            {
              "nodeId": "loop_task",
              "depends": []
            }
          ],
          "while": "${dag.loopTimes} < 5"
        },
        "outputs": {
          "nodeOutputs": [
            { "data": "${projectIdentifier}.my_loop", "artifactType": "NodeOutput" }
          ]
        }
      }
    ],
    "flow": [
      {
        "nodeId": "my_loop",
        "depends": [
          { "type": "Normal", "output": "${projectIdentifier}_root" }
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
| Maximum iterations | 128; exceeding this will cause an error |
| Concurrency | Concurrent execution not supported; serial only |
| Test method | Cannot be tested directly in Data Studio; must be published and executed in the Operations Center |
| Internal branches | When using branch nodes, merge nodes must also be used |
| End node code | Comments are not supported |
| With assignment node | When backfilling data, both the assignment node and loop node must be selected; otherwise, the passed values cannot be retrieved |
