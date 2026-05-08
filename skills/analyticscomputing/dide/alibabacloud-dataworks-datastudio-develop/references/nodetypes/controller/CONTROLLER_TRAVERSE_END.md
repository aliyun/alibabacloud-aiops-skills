# Traverse End Node (CONTROLLER_TRAVERSE_END)

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no code, no `script.content`)
- Extension: `.for-each-end` (an empty marker file)

`CONTROLLER_TRAVERSE_END` is the **exit marker** of a [`CONTROLLER_TRAVERSE`](./CONTROLLER_TRAVERSE.md) (for-each) container. It has no business logic and, unlike the do-while [`CONTROLLER_CYCLE_END`](./CONTROLLER_CYCLE_END.md), it carries **no loop-continuation code** — a for-each loop always runs exactly as many iterations as the bound collection contains, so no stop condition is needed. Its sole purpose is to anchor "the end of one iteration": once all body tasks of an iteration have reached it, the runtime either starts the next iteration or exits the loop.

One traverse container contains **exactly one** end marker and **exactly one** [`CONTROLLER_TRAVERSE_START`](./CONTROLLER_TRAVERSE_START.md).

## Usage Pattern

```
   CONTROLLER_TRAVERSE container
   +--------------------------------------------+
   |  CONTROLLER_TRAVERSE_START                 |
   |         |                                  |
   |         v                                  |
   |  body task(s)                              |
   |         |                                  |
   |         v                                  |
   |  CONTROLLER_TRAVERSE_END (this node)       |
   +--------------------------------------------+
```

## Schema

### `script.runtime`

| Field | Value |
|-------|-------|
| `engine` | `General` |
| `command` | `CONTROLLER_TRAVERSE_END` |

### `script.content`

**Omit.** The end marker carries no code. The companion extension file `<name>.for-each-end` is an empty placeholder.

There is **no `while` expression and no stop-condition code** — that is the key difference from [`CONTROLLER_CYCLE_END`](./CONTROLLER_CYCLE_END.md).

### `script.parameters[]`

Not used. Do not declare parameters on the end marker.

### `inputs` / `outputs`

- `inputs` is an empty object `{}`. The end marker does not declare explicit upstream dependencies in its own spec — the runtime wires it to the final body task(s) inside the container automatically.
- `outputs.nodeOutputs[]` contains a single entry with `data: "${projectIdentifier}.<end_name>"`.

## Dependency Wiring

### End marker itself

The end marker's `inputs` is empty and it does not appear in any `dependencies[]` entry in its own spec. Its position "after all body tasks" is enforced by the container's containment semantics, not by user-authored edges. Do **not** manually add body tasks to the end marker's `dependencies[]`.

### Branching inside the body

If a branch node ([`CONTROLLER_BRANCH`](./CONTROLLER_BRANCH.md)) is used inside the loop body, every branch arm must converge at a [`CONTROLLER_JOIN`](./CONTROLLER_JOIN.md) merge node **before** the iteration reaches `CONTROLLER_TRAVERSE_END`. Letting an unselected branch arm propagate *not run* all the way to the end marker can skip the end-of-iteration handoff.

## Other Requirements

| Requirement | Detail |
|-------------|--------|
| `script.runtime.command` | `CONTROLLER_TRAVERSE_END`. |
| `script.runtime.engine` | `General`. |
| `script.content` | Omit. No stop-condition code (that is `CONTROLLER_CYCLE_END`'s job, not this node's). |
| `script.parameters[]` | Omit. |
| Cardinality | Exactly one per `CONTROLLER_TRAVERSE` container. |
| Editability | The marker is auto-generated and cannot be deleted or replaced with a task node. |
| Extension file | `<name>.for-each-end`, empty. |

## Full Example

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "recurrence": "Normal",
        "name": "traverse_end",
        "script": {
          "runtime": {
            "engine": "General",
            "command": "CONTROLLER_TRAVERSE_END"
          }
        },
        "inputs": {},
        "outputs": {
          "nodeOutputs": [
            {
              "sourceType": "System",
              "data": "${projectIdentifier}.traverse_end",
              "refTableName": "traverse_end"
            }
          ]
        }
      }
    ]
  }
}
```

## Authoring Checklist

- [ ] `script.runtime.command` is `CONTROLLER_TRAVERSE_END` and `script.runtime.engine` is `General`.
- [ ] `script.content` and `script.parameters` are **omitted** — no stop-condition code on the end marker.
- [ ] `inputs` is an empty object `{}` and there is no `dependencies[]` entry naming this marker as its owner.
- [ ] `outputs.nodeOutputs[]` contains a single entry with `data: "${projectIdentifier}.<end_name>"`.
- [ ] The node lives inside a [`CONTROLLER_TRAVERSE`](./CONTROLLER_TRAVERSE.md) container and is the **only** end marker in that container.
- [ ] If the body contains a [`CONTROLLER_BRANCH`](./CONTROLLER_BRANCH.md), every arm converges at a [`CONTROLLER_JOIN`](./CONTROLLER_JOIN.md) before reaching this marker.
