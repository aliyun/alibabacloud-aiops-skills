# Loop End Node (CONTROLLER_CYCLE_END)

## Overview

- Compute engine: `GENERAL`
- Content format: empty in real samples (no `script.content`, no code file)
- Extension: `.do-while-end` (legacy UI marker file; empty in real samples)

The loop end node marks the **end of a do-while loop body**. It is always paired with a [`CONTROLLER_CYCLE`](./CONTROLLER_CYCLE.md) container and a [`CONTROLLER_CYCLE_START`](./CONTROLLER_CYCLE_START.md) marker. Inside the loop body DAG it is the **single sink** — every terminal body task must flow into it.

## Role in the loop topology

```
CONTROLLER_CYCLE  (container — external face of the loop)

CONTROLLER_CYCLE_START
        |
        v
 body task A      body task B
        \          /
         v        v
   CONTROLLER_CYCLE_END  <-- this node
```

`CYCLE_END` is a **sibling** of the container, not nested inside it. It is authored as its own top-level node in the spec (or as its own 3-file directory when using the build tool). On every loop iteration the scheduler runs each body task and, once they have all succeeded, runs `CYCLE_END`. The scheduler then decides whether to start another iteration.

## Schema

### `script`

| Field | Value |
|-------|-------|
| `script.runtime.command` | `CONTROLLER_CYCLE_END` |
| `script.runtime.engine` | `General` (observed in real samples) |
| `script.runtime.cu` | Small allocation (e.g. `"0.25"`). |
| `script.content` | **Omit** in real samples. Do not set to `""` or `"{}"`. |
| `script.language` | Some real samples carry a legacy `"odps-sql"` value here left over from the UI template. It has no runtime effect on this node type and may be left as-is or removed; the authoritative field is `script.runtime.command`. |
| `script.parameters` | Omit. |

### `datasource`

Real samples carry a `datasource` object on the end node even though it executes no SQL:

```json
"datasource": {
  "name": "${spec.datasource.name}",
  "type": "odps"
}
```

This appears to be a UI artifact carried over from the template the end node was originally cloned from. It is benign; keep it if it was already present in the source project to avoid UI churn, but do not invent one if the source sample does not have it.

### `inputs` / `outputs`

- `inputs` is an empty object (`{}`) in real samples — no `nodeOutputs` list.
- `outputs.nodeOutputs[]` contains a single entry with the fully-qualified `data` identifier `${projectIdentifier}.<end_name>`. Nothing outside the loop should depend on this output — external consumers depend on the container node instead (see [`CONTROLLER_CYCLE.md`](./CONTROLLER_CYCLE.md)).

### Trigger / runtimeResource

Same as `CYCLE_START`: inherit scheduling from the container, but still declare `runtimeResource.resourceGroup`.

## Dependency Wiring

### Incoming: depends on every terminal body task by `output`

```json
"dependencies": [
  {
    "nodeId": "cycle_end",
    "depends": [
      { "type": "Normal", "output": "${projectIdentifier}.shell1_in_dowhile1" },
      { "type": "Normal", "output": "${projectIdentifier}.select1_in_dowhile1" }
    ]
  }
]
```

- Use standard **`output`-based** dependencies.
- Wire **every terminal body task** (every leaf of the body DAG) into this list, so the end marker only runs after the whole loop body for this iteration has completed.

### Outgoing: none (inside the loop)

No other node depends on `CYCLE_END`. External downstream consumers depend on the container node, not on the end marker.

## Loop termination

The real sample contains **no explicit loop-continuation expression** on `CYCLE_END` — `script.content` is empty. In that configuration, the loop runs until `do-while.maxIterations` on the container is reached. If you need a code-driven termination check, that logic is authored as code on this node (e.g. a small Python/shell snippet that prints `True` to continue or `False` to exit, referencing `${dag.loopTimes}`, `${dag.input.length}`, etc.). The exact code mechanism is not exercised by the current sample; document it by example only if you have a reference that actually uses it.

## Full Example

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "id": "cycle_end",
        "name": "cycle_end",
        "recurrence": "Normal",
        "datasource": {
          "name": "${spec.datasource.name}",
          "type": "odps"
        },
        "script": {
          "language": "odps-sql",
          "runtime": {
            "engine": "General",
            "command": "CONTROLLER_CYCLE_END",
            "cu": "0.25"
          }
        },
        "runtimeResource": {
          "resourceGroup": "${spec.runtimeResource.resourceGroup}"
        },
        "inputs": {},
        "outputs": {
          "nodeOutputs": [
            {
              "data": "${projectIdentifier}.cycle_end",
              "sourceType": "System",
              "refTableName": "cycle_end"
            }
          ]
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "cycle_end",
        "depends": [
          { "type": "Normal", "output": "${projectIdentifier}.shell1_in_dowhile1" },
          { "type": "Normal", "output": "${projectIdentifier}.select1_in_dowhile1" }
        ]
      }
    ]
  }
}
```

## Authoring Checklist

- [ ] `script.runtime.command` is `CONTROLLER_CYCLE_END`.
- [ ] `script.runtime.engine` is `General`.
- [ ] `script.content` is **omitted** unless you are authoring a code-driven termination check.
- [ ] `inputs` is an empty object `{}`.
- [ ] `outputs.nodeOutputs[]` contains exactly one entry with `data: "${projectIdentifier}.<end_name>"`.
- [ ] `dependencies[]` lists **every** terminal body task as an `output`-based `Normal` dependency.
- [ ] No node outside the loop depends on this end marker — external consumers depend on the [`CONTROLLER_CYCLE`](./CONTROLLER_CYCLE.md) container instead.
- [ ] Exactly one `CONTROLLER_CYCLE_END` exists for each container, paired with exactly one [`CONTROLLER_CYCLE_START`](./CONTROLLER_CYCLE_START.md).
