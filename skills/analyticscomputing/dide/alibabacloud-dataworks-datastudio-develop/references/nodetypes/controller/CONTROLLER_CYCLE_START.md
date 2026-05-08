# Loop Start Node (CONTROLLER_CYCLE_START)

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no `script.content`, no code file)
- Extension: `.do-while-start` (legacy UI marker file; empty in real samples)

The loop start node is an empty marker that denotes the **beginning of a do-while loop body**. It is always paired with a [`CONTROLLER_CYCLE`](./CONTROLLER_CYCLE.md) container and a [`CONTROLLER_CYCLE_END`](./CONTROLLER_CYCLE_END.md) marker. It carries no user code, no `script.content`, no `script.parameters`, and no data-source binding — its sole purpose is to act as the single entry-point that every body task depends on.

## Role in the loop topology

```
CONTROLLER_CYCLE  (container — external face of the loop)

CONTROLLER_CYCLE_START  <-- this node
        |
        v
 body task A      body task B
        \          /
         v        v
   CONTROLLER_CYCLE_END
```

`CYCLE_START` is a **sibling** of the container, not nested inside it. It is authored as its own top-level node in the spec (or as its own 3-file directory when using the build tool). Inside the loop it has:

- **No incoming dependencies.** The start node's `dependencies` entry is absent — it is the root of the loop-body DAG.
- **No `script.content`.** It carries no user code and the extension file `.do-while-start` is empty.
- **No `datasource`.** Even if the body tasks operate on MaxCompute, the start marker itself does not bind to any data source.

## Schema

### `script`

| Field | Value |
|-------|-------|
| `script.runtime.command` | `CONTROLLER_CYCLE_START` |
| `script.runtime.engine` | `General` (observed in real samples) |
| `script.runtime.cu` | Omit. The start marker performs no computation. (Some real samples omit `cu` entirely on this node.) |
| `script.content` | **Omit.** Do not set to `""` or `"{}"`. |
| `script.parameters` | Omit. |

### `inputs` / `outputs`

- `inputs` is an empty object (`{}`) in real samples.
- `outputs.nodeOutputs[]` contains a single entry with the fully-qualified `data` identifier `${projectIdentifier}.<start_name>`. Body tasks depend on the start node via this `output` (see below).

### Trigger / runtimeResource

The start marker still needs a `runtimeResource.resourceGroup` assignment, matching the rest of the loop. It does not define its own trigger — scheduling is inherited from the container.

## Dependency Wiring

### Incoming: none

The start node has no `dependencies` entry of its own. It is the single root of the loop-body DAG.

### Outgoing: every body task depends on the start node by `output`

```json
// On a body task
"dependencies": [
  {
    "nodeId": "shell1_in_dowhile1",
    "depends": [
      { "type": "Normal", "output": "${projectIdentifier}.cycle_start" }
    ]
  }
]
```

This is the **only** correct way to wire body tasks to the start marker:

- Use a standard **`output`-based** dependency.
- The body task declares only this internal dependency — no external `inputs`-level wiring is needed for this edge.

## Full Example

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "cycle_start",
        "recurrence": "Normal",
        "script": {
          "runtime": {
            "engine": "General",
            "command": "CONTROLLER_CYCLE_START"
          }
        },
        "runtimeResource": {
          "resourceGroup": "${spec.runtimeResource.resourceGroup}"
        },
        "inputs": {},
        "outputs": {
          "nodeOutputs": [
            {
              "sourceType": "System",
              "data": "${projectIdentifier}.cycle_start",
              "refTableName": "cycle_start"
            }
          ]
        }
      }
    ]
  }
}
```

## Authoring Checklist

- [ ] `script.runtime.command` is `CONTROLLER_CYCLE_START`.
- [ ] `script.runtime.engine` is `General`.
- [ ] `script.content`, `script.parameters`, and `datasource` are all **omitted**.
- [ ] `inputs` is an empty object `{}`.
- [ ] `outputs.nodeOutputs[]` contains exactly one entry with `data: "${projectIdentifier}.<start_name>"`.
- [ ] The spec does **not** declare any incoming dependency on this node (no `dependencies` entry naming the start node as its owner).
- [ ] Every loop-body task depends on this node via `{ "type": "Normal", "output": "${projectIdentifier}.cycle_start" }` in its own `dependencies[].depends`.
- [ ] Exactly one `CONTROLLER_CYCLE_START` exists for each [`CONTROLLER_CYCLE`](./CONTROLLER_CYCLE.md) container, and it is paired with exactly one [`CONTROLLER_CYCLE_END`](./CONTROLLER_CYCLE_END.md).
