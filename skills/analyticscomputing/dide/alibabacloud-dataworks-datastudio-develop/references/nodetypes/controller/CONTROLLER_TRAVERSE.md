# Traverse Node (CONTROLLER_TRAVERSE)

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no `script.content` required)
- Extension: `.for-each.json` (legacy UI-facing config; in modern samples this file is empty — the authoritative configuration lives in the `for-each` field of `*.spec.json`)

The traverse node is a container control node that implements **for-each** semantics: it iterates over a collection produced by an upstream assignment node and re-runs an inner sub-graph (its *loop body*) once per element. The collection is bound through a node-context `Variable` parameter, not through `script.content`. Unlike the do-while `CONTROLLER_CYCLE`, the iteration count is **driven by the collection length** — there is no user-written stop condition.

Each traverse container is paired with two auto-generated boundary markers:

- [`CONTROLLER_TRAVERSE_START`](./CONTROLLER_TRAVERSE_START.md) — entry marker for the loop body
- [`CONTROLLER_TRAVERSE_END`](./CONTROLLER_TRAVERSE_END.md) — exit marker for the loop body

Every body task lives between these two markers.

## Usage Pattern

```
            upstream (e.g. assignment1, emits a Variable "outputs" holding the collection)
                       |
                       v
            +---------------------------+
            |  CONTROLLER_TRAVERSE      |   <-- container; binds the collection via
            |  (my_foreach)             |       script.parameters[loopDataArray]
            +---------------------------+
                       |  (contains)
              +--------+---------+
              |                  |
              v                  v
   CONTROLLER_TRAVERSE_START     |
              |                  |
              v                  |
      body task(s)                (e.g. shell_in_foreach)
              |
              v
    CONTROLLER_TRAVERSE_END
```

- The **container** (`CONTROLLER_TRAVERSE`) is the node the rest of the workflow depends on. External upstreams and downstreams attach to the container, not to the inner boundary markers.
- The **start** and **end** markers sit inside the container and define where the loop body begins and ends. They are lightweight — no code, no parameters.
- **Body tasks** depend on the start marker (directly or transitively). Any body task can run inside the loop.

## Schema

### `script.runtime`

| Field | Value |
|-------|-------|
| `command` | `CONTROLLER_TRAVERSE` |
| `cu` | Small allocation (e.g. `"0.25"`). The container does no computation. |

### `script.content`

**Omit.** The traverse container carries no code.

### `script.parameters[]` — bind the collection

The collection to iterate over is bound by declaring a single `Variable` parameter named **`loopDataArray`** whose `referenceVariable` points to the upstream assignment node's output variable. This is the only supported way to feed a traverse container.

```json
"script": {
  "runtime": { "command": "CONTROLLER_TRAVERSE", "cu": "0.25" },
  "parameters": [
    {
      "artifactType": "Variable",
      "name": "loopDataArray",
      "scope": "NodeContext",
      "type": "NodeOutput",
      "value": "${outputs}",
      "referenceVariable": {
        "artifactType": "Variable",
        "name": "outputs",
        "scope": "NodeContext",
        "type": "NodeOutput",
        "value": "${outputs}",
        "node": {
          "name": "assignment1"
        }
      }
    }
  ]
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Must be `loopDataArray`. This is the well-known name the traverse runtime reads to obtain the collection. |
| `scope` | yes | `NodeContext`. |
| `type` | yes | `NodeOutput` — the value is forwarded from an upstream node context. |
| `value` | yes | `${outputs}` — a textual placeholder; the actual value comes from `referenceVariable`. |
| `referenceVariable.name` | yes | The name of the variable exposed by the upstream assignment node (typically `outputs`). |
| `referenceVariable.node.name` | yes | The `name` of the upstream assignment node that produced the collection. |

The same variable must also be mirrored under `inputs.variables[]` with `inputName: "loopDataArray"` so the scheduler records the context edge.

### `for-each` — runtime limits

The container also carries a top-level `for-each` object with just two fields:

```json
"for-each": {
  "maxIterations": 128,
  "parallelism": 0
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `maxIterations` | number | `128` | Upper bound on the number of iterations. If the collection is longer than this, the excess elements are not processed. |
| `parallelism` | number | `0` | `0` = serial (iterations run one after another). A positive value requests concurrent iteration execution. |

Note: unlike the do-while `CONTROLLER_CYCLE`, there is **no `while` expression** — the iteration count is always the collection length, capped by `maxIterations`.

### Built-in runtime variables (available inside body tasks)

Body tasks reference the current iteration through `${dag.*}` placeholders, substituted at run time:

| Placeholder | Description |
|-------------|-------------|
| `${dag.loopDataArray}` | The full collection forwarded from the upstream assignment node (2-D array). |
| `${dag.foreach.current}` | The current row as a comma-joined string. |
| `${dag.foreach.current[n]}` | The n-th column of the current row. |
| `${dag.loopDataArray[i][j]}` | Direct index into the full result set (row `i`, column `j`). |
| `${dag.offset}` | Zero-based index of the current iteration. |
| `${dag.loopTimes}` | One-based count of the current iteration. |

These placeholders are resolved by the scheduler before the body task's code runs; body tasks do **not** need to declare them in `script.parameters[]`.

## Dependency Wiring

### Upstream (assignment) -> traverse container

Two things must be wired:

1. A standard scheduler dependency on the assignment node under the container's `dependencies[].depends[]`.
2. A node-context `variables[]` entry under the container's `inputs` that forwards the assignment node's `outputs` variable into the container under `inputName: "loopDataArray"`.

```json
```

### Container -> boundary markers and body tasks (containment)

Start / end markers and body tasks are authored as **peer nodes** (sibling files in the source tree) and linked to the container through the adapter's containment mechanism — there is no `foreach.nodes[]` sub-array inside the container spec. Inside the container:

- **Body tasks depend on `CONTROLLER_TRAVERSE_START`** via an ordinary `Normal` dependency on the start marker's `output` (`${projectIdentifier}.<start_name>`). This is how the body participates in the iteration.
- **`CONTROLLER_TRAVERSE_END`** has no explicit dependencies in its own spec — the runtime attaches it after the final body task automatically.
- Start and end markers do not declare upstream dependencies; they are wired in by the runtime.

### Traverse container -> downstream

Downstream nodes outside the container depend on the container's own output (the entry in `outputs.nodeOutputs[]` whose `data` equals `${projectIdentifier}.<container_name>`), not on the end marker and not on any body task output.

## OpenAPI creation pattern (container + internal nodes)

When creating a foreach loop via OpenAPI, the container and its internal nodes must be created **separately** because the container is a first-class node with its own `Id`, and the internal nodes live inside it:

1. **Create the container** — call `create-node` (or the workflow-level equivalent) to create the `CONTROLLER_TRAVERSE` container node. This returns the container's `Id`.
2. **Create internal nodes with `container-id`** — call `create-node` for each internal node (`CONTROLLER_TRAVERSE_START`, body tasks, `CONTROLLER_TRAVERSE_END`), specifying `container-id = <container Id>` to declare that they belong inside the container. Without `container-id`, the internal nodes will be created as top-level workflow nodes and the foreach will not function.

This is the same containment mechanism used by workflows and the do-while container (`CONTROLLER_CYCLE`): internal nodes are created with `container-id` pointing to their container's `Id`.

> **Important**: the FlowSpec `*.spec.json` authored locally lists the start/body/end as peer nodes (siblings at the same `spec.nodes[]` level). This is a local authoring convenience — when submitted via OpenAPI, the adapter must split them into separate `create-node` calls with the correct `container-id`.

## Other Requirements

| Requirement | Detail |
|-------------|--------|
| `script.runtime.command` | `CONTROLLER_TRAVERSE`. |
| `script.content` | Omit. |
| `script.parameters[]` | Must contain exactly one `Variable` entry named `loopDataArray` that references the upstream assignment node. |
| `inputs.variables[]` | Must mirror `loopDataArray` with `inputName: "loopDataArray"` and point at the same upstream node. |
| `for-each.maxIterations` | Default `128`. Adjustable up to the product cap (commonly `1024`). |
| `for-each.parallelism` | Default `0` (serial). A positive value requests concurrent iteration. |
| Boundary markers | Exactly one `CONTROLLER_TRAVERSE_START` and one `CONTROLLER_TRAVERSE_END` must live inside the container. |
| Internal branching | If a branch node is used inside the body, every branch must converge at a merge node before reaching `CONTROLLER_TRAVERSE_END`. |
| Test method | Cannot be run ad-hoc in Data Studio; must be published and exercised from the Operations Center (like all container nodes). |

Contrast with [`CONTROLLER_CYCLE`](./CONTROLLER_CYCLE.md) (do-while): `CONTROLLER_CYCLE` uses a user-written `while` expression and does not require an upstream assignment node; `CONTROLLER_TRAVERSE` is always length-driven by a collection bound through `loopDataArray`.

## Full Example

A traverse container `my_foreach` that iterates over the collection emitted by an upstream assignment node `assignment1`. One shell body task `shell_in_foreach` prints the current row.

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
          "runtime": { "command": "CONTROLLER_TRAVERSE", "cu": "0.25" },
          "parameters": [
            {
              "artifactType": "Variable",
              "name": "loopDataArray",
              "scope": "NodeContext",
              "type": "NodeOutput",
              "value": "${outputs}",
              "referenceVariable": {
                "artifactType": "Variable",
                "name": "outputs",
                "scope": "NodeContext",
                "type": "NodeOutput",
                "value": "${outputs}",
                "node": { "name": "assignment1" }
              }
            }
          ]
        },
        "outputs": {
          "nodeOutputs": [
            { "sourceType": "System", "data": "${projectIdentifier}.my_foreach", "refTableName": "my_foreach" }
          ]
        },
        "for-each": {
          "maxIterations": 128,
          "parallelism": 0
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "my_foreach",
        "depends": [
          { "type": "Normal", "output": "${projectIdentifier}.assignment1", "sourceType": "Manual" },
          { "type": "Normal", "output": "${projectIdentifier}_root", "sourceType": "Manual" }
        ]
      }
    ]
  }
}
```

A body shell task referencing the built-in variables:

```bash
# current row as a comma-joined string
echo ${dag.foreach.current}
# n-th column of the current row
echo ${dag.foreach.current[n]}
# direct index into the full collection
echo ${dag.loopDataArray[i][j]}
# full collection forwarded from the upstream assignment node
echo ${dag.loopDataArray}
# zero-based iteration offset
echo ${dag.offset}
# one-based iteration count
echo ${dag.loopTimes}
```

## Authoring Checklist

Before submitting a traverse container, verify:

- [ ] `script.runtime.command` is `CONTROLLER_TRAVERSE`.
- [ ] `script.content` is **omitted** (not `""`, not `"{}"`).
- [ ] `script.parameters[]` contains exactly one `Variable` entry named `loopDataArray`, whose `referenceVariable.node.name` points at an upstream assignment node.
- [ ] `inputs.variables[]` mirrors the same binding with `inputName: "loopDataArray"`.
- [ ] `dependencies[].depends[]` declares the scheduler edge to that assignment node.
- [ ] The top-level `for-each` object is present with `maxIterations` and `parallelism`.
- [ ] Exactly one [`CONTROLLER_TRAVERSE_START`](./CONTROLLER_TRAVERSE_START.md) and one [`CONTROLLER_TRAVERSE_END`](./CONTROLLER_TRAVERSE_END.md) sit inside the container.
- [ ] Every body task depends (directly or transitively) on the start marker.
- [ ] Downstream nodes outside the container depend on the container's own `${projectIdentifier}.<container_name>` output, not on body tasks or the end marker.
- [ ] When submitting via OpenAPI: create the container first, then create each internal node (`TRAVERSE_START`, body tasks, `TRAVERSE_END`) with `container-id` set to the container's `Id`. Without `container-id`, the internal nodes will not be associated with the loop.
- [ ] Body tasks use `${dag.foreach.current}`, `${dag.loopDataArray}`, `${dag.offset}`, `${dag.loopTimes}` without declaring them in their own `script.parameters[]`.
