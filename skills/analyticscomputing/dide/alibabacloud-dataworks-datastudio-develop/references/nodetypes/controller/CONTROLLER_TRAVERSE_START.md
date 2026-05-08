# Traverse Start Node (CONTROLLER_TRAVERSE_START)

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no code, no `script.content`)
- Extension: `.for-each-start` (an empty marker file)

`CONTROLLER_TRAVERSE_START` is the **entry marker** of a [`CONTROLLER_TRAVERSE`](./CONTROLLER_TRAVERSE.md) (for-each) container. It has no business logic — its sole purpose is to anchor the loop body so that body tasks can attach to "the start of the iteration" through a normal scheduler dependency. It is the traverse counterpart of [`CONTROLLER_CYCLE_START`](./CONTROLLER_CYCLE_START.md).

One traverse container contains **exactly one** start marker and **exactly one** [`CONTROLLER_TRAVERSE_END`](./CONTROLLER_TRAVERSE_END.md).

## Usage Pattern

```
   CONTROLLER_TRAVERSE container
   +--------------------------------------------+
   |  CONTROLLER_TRAVERSE_START (this node)     |
   |         |                                  |
   |         v                                  |
   |  body task(s)                              |
   |         |                                  |
   |         v                                  |
   |  CONTROLLER_TRAVERSE_END                   |
   +--------------------------------------------+
```

Body tasks declare a `Normal` dependency on the start marker's `output` (`${projectIdentifier}.<start_name>`); the runtime re-drives the start marker once per iteration, which in turn re-drives every body task rooted at it.

## Schema

### `script.runtime`

| Field | Value |
|-------|-------|
| `engine` | `General` |
| `command` | `CONTROLLER_TRAVERSE_START` |

### `script.content`

**Omit.** The start marker carries no code. The companion extension file `<name>.for-each-start` is an empty placeholder.

### `script.parameters[]`

Not used. Do not declare parameters on the start marker.

### `inputs` / `outputs`

- `inputs` is an empty object `{}`. The start marker does not declare upstream dependencies of its own — the runtime links it to the container automatically.
- `outputs.nodeOutputs[]` contains a single entry with `data: "${projectIdentifier}.<start_name>"`. Body tasks attach to this output via `dependencies[].depends[]`.

## Dependency Wiring

### Start marker itself

The start marker's own `inputs` is empty and it does not appear as a child of any other node in `dependencies[]`. Its attachment to the enclosing [`CONTROLLER_TRAVERSE`](./CONTROLLER_TRAVERSE.md) container is handled by the adapter's containment mechanism.

### Body tasks -> start marker

Every body task that should run once per iteration depends on the start marker:

```json
"dependencies": [
  {
    "nodeId": "shell_in_foreach",
    "depends": [
      { "type": "Normal", "output": "${projectIdentifier}.traverse_start" }
    ]
  }
]
```

Body tasks that are downstream of other body tasks need only depend on those siblings — they do not also need to depend on the start marker, because the transitive path already reaches it.

## Other Requirements

| Requirement | Detail |
|-------------|--------|
| `script.runtime.command` | `CONTROLLER_TRAVERSE_START`. |
| `script.runtime.engine` | `General`. |
| `script.content` | Omit. |
| `script.parameters[]` | Omit. |
| Cardinality | Exactly one per `CONTROLLER_TRAVERSE` container. |
| Editability | The marker is auto-generated and cannot be deleted or replaced with a task node. |
| Extension file | `<name>.for-each-start`, empty. |

## Full Example

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "recurrence": "Normal",
        "name": "traverse_start",
        "script": {
          "runtime": {
            "engine": "General",
            "command": "CONTROLLER_TRAVERSE_START"
          }
        },
        "inputs": {},
        "outputs": {
          "nodeOutputs": [
            {
              "sourceType": "System",
              "data": "${projectIdentifier}.traverse_start",
              "refTableName": "traverse_start"
            }
          ]
        }
      }
    ]
  }
}
```

## Authoring Checklist

- [ ] `script.runtime.command` is `CONTROLLER_TRAVERSE_START` and `script.runtime.engine` is `General`.
- [ ] `script.content` and `script.parameters` are **omitted**.
- [ ] `inputs` is an empty object `{}`.
- [ ] `outputs.nodeOutputs[]` contains a single entry with `data: "${projectIdentifier}.<start_name>"`.
- [ ] The node lives inside a [`CONTROLLER_TRAVERSE`](./CONTROLLER_TRAVERSE.md) container and is the **only** start marker in that container.
- [ ] At least one body task declares a `Normal` dependency on this marker's `output`.
