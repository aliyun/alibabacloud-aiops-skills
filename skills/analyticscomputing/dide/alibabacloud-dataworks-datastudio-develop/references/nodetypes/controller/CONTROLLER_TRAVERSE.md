# Traverse Node（CONTROLLER_TRAVERSE）

## Overview

- Compute engine: `GENERAL`
- Content format: json
- Extension: `.for-each.json`

The traverse node implements for-each loop logic, automatically iterating over the result set output by the upstream assignment node and repeatedly executing the internal loop body for each element.

**Use case**: Execute the same processing logic for multiple business units, product lines, or configuration items.

## Node Structure

```
Assignment Node (outputs array, e.g., "10,20,30")
    ↓
for-each wrapper (CONTROLLER_TRAVERSE)
├── Start Node (CONTROLLER_TRAVERSE_START, auto-generated)
├── Internal Business Node (actual processing logic)
└── End Node (CONTROLLER_TRAVERSE_END, auto-generated)
```

- Wrapper container: Contains the entire loop workflow
- Start/End nodes: Auto-generated, not editable, only mark loop body boundaries
- Internal business nodes: Execute actual data processing

## Built-in Variables

Internal nodes reference traverse data via the following variables:

| Variable | Description |
|------|------|
| `${dag.loopDataArray}` | The complete result set from the upstream assignment node |
| `${dag.foreach.current}` | The data item currently being processed in the loop |
| `${dag.offset}` | Current loop offset (starting from 0) |
| `${dag.loopTimes}` | Current loop iteration (starting from 1) |
| `${dag.foreach.current[n]}` | The n-th data item in the current data row (2D array) |

## Configuration

### script.content Field

Stores traverse control configuration in JSON format:

| Field | Type | Default | Description |
|------|------|--------|------|
| `maxIterations` | number | 128 | Maximum loop count, adjustable up to 1024 |
| `parallelism` | number | 0 | Parallelism, 0 = serial, maximum 20 (default concurrency 5) |

### foreach Field

| Field | Type | Description |
|------|------|------|
| `foreach.nodes` | array | List of child nodes within the traverse body |
| `foreach.flow` | array | Dependency relationships of child nodes within the traverse body |

## Full Example

Assignment node outputs `"10,20,30"`; the for-each internal Shell node processes each item:

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "recurrence": "Normal",
        "name": "my_foreach",
        "script": {
          "path": "my_foreach",
          "runtime": { "command": "CONTROLLER_TRAVERSE" },
          "content": "{\"maxIterations\":128,\"parallelism\":0}"
        },
        "foreach": {
          "nodes": [
            {
              "name": "inner_task",
              "script": {
                "path": "my_foreach/inner_task",
                "runtime": { "command": "DIDE_SHELL" },
                "content": "echo \"processing item: ${dag.foreach.current}\""
              }
            }
          ],
          "flow": [
            {
              "nodeId": "inner_task",
              "depends": []
            }
          ]
        },
        "outputs": {
          "nodeOutputs": [
            { "data": "${projectIdentifier}.my_foreach", "artifactType": "NodeOutput" }
          ]
        }
      }
    ],
    "flow": [
      {
        "nodeId": "my_foreach",
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
| Maximum iterations | Default 128, maximum 1024 |
| Concurrency | Maximum 20 |
| Test method | Cannot be run directly in Data Studio; must be published and smoke tested in the Operations Center |
| Standalone execution | Standalone smoke testing, backfill, and manual execution are not supported |
| Internal branches | If branch nodes are used, all branches must converge at a merge node before connecting to the end node |
| Re-run behavior | Automatic re-run on failure resumes from the failed node; manual re-run triggers a complete re-run |
