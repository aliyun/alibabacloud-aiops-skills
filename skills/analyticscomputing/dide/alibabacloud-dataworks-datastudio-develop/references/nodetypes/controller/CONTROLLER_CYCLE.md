# Loop Node (CONTROLLER_CYCLE)

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no `script.content` required)
- Extension: `.do-while.json` (legacy UI-facing config; empty in real samples. The authoritative config lives in the `do-while` field of `*.spec.json`.)

The loop node implements a **do-while** construct. It is a lightweight container that carries only the loop-level options (`maxIterations`, `parallelism`). The actual loop body is **not nested** inside the container — instead, the start marker ([`CONTROLLER_CYCLE_START`](./CONTROLLER_CYCLE_START.md)), the body task nodes, and the end marker ([`CONTROLLER_CYCLE_END`](./CONTROLLER_CYCLE_END.md)) are authored as **sibling top-level nodes**, wired together by internal `output`-based dependencies (standard `${projectIdentifier}.<node_name>` edges). The container node itself hangs off the project root (or any upstream producer) like a normal task node.

## Typical Topology

```
project_root
     |
     v
 CONTROLLER_CYCLE  (e.g. "dowhile1" — holds do-while options, is the external face of the loop)

 (siblings, inside the same spec or the same workflow, wired by standard output edges)

 CONTROLLER_CYCLE_START  ("cycle_start")
        |
        v
 body task A  ("shell1_in_dowhile1")      body task B  ("select1_in_dowhile1")
        \                                   /
         \                                 /
          ----> CONTROLLER_CYCLE_END  <----
                     ("cycle_end")
```

At runtime, the scheduler repeatedly executes `CYCLE_START` -> body tasks -> `CYCLE_END`. After each `CYCLE_END` run the engine decides whether to start another iteration; the loop exits once the termination condition is met or `maxIterations` is reached.

## Schema

### `do-while` field

The container holds the loop-level options in a top-level `do-while` field on the node object (sibling to `script`, `inputs`, `outputs`). Observed fields in real samples:

```json
"do-while": {
  "maxIterations": 128,
  "parallelism": 0
}
```

| Sub-field | Type | Required | Description |
|-----------|------|----------|-------------|
| `maxIterations` | number | yes | Maximum number of iterations. The loop is forcibly terminated once this count is reached. Observed default in UI-generated samples is `128`. |
| `parallelism` | number | yes | Concurrency option. Observed value in real samples is `0` (serial execution — the next iteration only starts after the previous one completes). Parallel loop execution is not supported today. |

> **Note.** The real sample does **not** embed a loop-continuation expression (`while`, `condition`, etc.) anywhere in the container spec. Termination for this sample relies on `maxIterations` and on whatever logic is encoded inside `CYCLE_END`. If you need a code-driven termination check, place that logic on the `CYCLE_END` node — see [`CONTROLLER_CYCLE_END.md`](./CONTROLLER_CYCLE_END.md).

### `script`

| Field | Value |
|-------|-------|
| `script.runtime.command` | `CONTROLLER_CYCLE` |
| `script.runtime.cu` | Small allocation (e.g. `"0.25"`) — the container performs no computation of its own. |
| `script.content` | **Omit.** The container carries no user code. |
| `script.parameters` | Optional. Use only if the container needs to receive an upstream assignment-node output as a loop input — see "Consuming an assignment-node result" below. |

### `trigger`

The container carries the normal scheduling trigger (`type`, `cron`, `cycleType`, `startTime`, `endTime`, `timezone`). The start/body/end sibling nodes inherit their schedule from the container and should not define independent triggers that contradict the container.

### `outputs`

The container is the external face of the loop. It declares:

- `outputs.nodeOutputs[]` — at least one output that downstream nodes outside the loop can depend on. Declare a fully-qualified `data` output (`${projectIdentifier}.<loop_name>`).
- Upstream producers (e.g. the project root, or an assignment node) are declared via `spec.dependencies[].depends[]` on the container.

## Dependency Wiring

### External wiring (container -> outside world)

Upstream and downstream nodes outside the loop interact only with the **container** node, exactly like a normal task node. They do **not** reference `CYCLE_START`, `CYCLE_END`, or the body tasks directly.

```json
"dependencies": [
  {
    "nodeId": "dowhile1",
    "depends": [
      { "type": "Normal", "output": "${projectIdentifier}_root", "sourceType": "Manual" }
    ]
  }
]
```

### Internal wiring (start -> body -> end)

Inside the loop, dependencies use the standard `output`-based form:

- Each body task depends on `CYCLE_START` via `{ "type": "Normal", "output": "${projectIdentifier}.cycle_start" }`.
- `CYCLE_END` depends on **every** body task (the last nodes in the body DAG) via `{ "type": "Normal", "output": "${projectIdentifier}.<body_task>" }`.
- `CYCLE_START` has no internal `dependencies` entry of its own.

Body tasks do not declare external inputs — the internal edge is carried purely by the `output`-based dependency list.

### Consuming an assignment-node result

To iterate over a result set produced by an upstream assignment node, declare a `Normal` dependency on the assignment node's output under the container's `spec.dependencies[].depends[]`. The body tasks can then read the dataset via the built-in `${dag.input}` variable family (see "Built-in iteration variables" below). You must also declare an `input`-typed parameter on the container so the assignment output is bound under the name you reference in `${dag.<name>}`.

## Built-in iteration variables

Body tasks (shell, SQL, Python, etc.) can reference the following built-ins inside their code/parameters. They are provided by the scheduler on each iteration:

| Variable | Description |
|----------|-------------|
| `${dag.loopTimes}` | Current iteration count. First iteration is `1`, second is `2`, etc. |
| `${dag.offset}` | Zero-based iteration index. First iteration is `0`, second is `1`, etc. |
| `${dag.input}` | Dataset passed in from an upstream assignment node, bound to the container input name `input`. For a different input name `foo`, use `${dag.foo}`. |
| `${dag.input[${dag.offset}]}` | The current iteration's row when iterating over `${dag.input}`. |
| `${dag.input.length}` | Number of rows in `${dag.input}`. Commonly used to drive the termination check. |

These names are taken verbatim from the real `shell1_in_dowhile1.sh` body sample.

## OpenAPI creation pattern (container + internal nodes)

When creating a do-while loop via OpenAPI, the container and its internal nodes must be created **separately** because the container is a first-class node with its own `Id`, and the internal nodes live inside it:

1. **Create the container** — call `create-node` (or the workflow-level equivalent) to create the `CONTROLLER_CYCLE` container node. This returns the container's `Id`.
2. **Create internal nodes with `container-id`** — call `create-node` for each internal node (`CONTROLLER_CYCLE_START`, body tasks, `CONTROLLER_CYCLE_END`), specifying `container-id = <container Id>` to declare that they belong inside the container. Without `container-id`, the internal nodes will be created as top-level workflow nodes and the loop will not function.

This is the same containment mechanism used by workflows: a workflow is a container whose inner nodes are created with `container-id` pointing to the workflow's `Id`. The do-while container and the foreach container (`CONTROLLER_TRAVERSE`) follow the same pattern.

> **Important**: the FlowSpec `*.spec.json` authored locally lists the start/body/end as peer nodes (siblings at the same `spec.nodes[]` level). This is a local authoring convenience — when submitted via OpenAPI, the adapter must split them into separate `create-node` calls with the correct `container-id`.

## Other Requirements

| Requirement | Detail |
|-------------|--------|
| `script.runtime.command` | Must be `CONTROLLER_CYCLE`. |
| `script.content` | Omit on the container. |
| Start / end markers | Exactly one `CONTROLLER_CYCLE_START` and one `CONTROLLER_CYCLE_END` must accompany every `CONTROLLER_CYCLE`, as sibling nodes. See [`CONTROLLER_CYCLE_START.md`](./CONTROLLER_CYCLE_START.md) and [`CONTROLLER_CYCLE_END.md`](./CONTROLLER_CYCLE_END.md). |
| Body-task dependencies | Use standard `output`-based dependencies (`{ "type": "Normal", "output": "${projectIdentifier}.<node_name>" }`). |
| Iteration limit | `do-while.maxIterations` hard-caps the loop. The observed default is `128`. |
| Parallelism | `do-while.parallelism` is `0` in real samples; parallel loop execution is not supported. |
| Internal branches | If the body contains a branch node, it must be paired with a merge node. |
| Product version | DataWorks Standard Edition or above. |

## Full Example

The container node for a loop named `dowhile1`. The sibling `cycle_start`, `shell1_in_dowhile1`, `select1_in_dowhile1`, and `cycle_end` nodes are shown in their own docs; this spec shows only the container.

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "dowhile1",
        "recurrence": "Normal",
        "script": {
          "runtime": {
            "command": "CONTROLLER_CYCLE",
            "cu": "0.25"
          }
        },
        "trigger": {
          "type": "Scheduler",
          "cron": "00 19 00 * * ?",
          "cycleType": "Daily",
          "startTime": "1970-01-01 00:00:00",
          "endTime": "9999-01-01 00:00:00",
          "timezone": "Asia/Shanghai",
          "delaySeconds": 0
        },
        "runtimeResource": {
          "resourceGroup": "${spec.runtimeResource.resourceGroup}"
        },
        "outputs": {
          "nodeOutputs": [
            {
              "sourceType": "System",
              "data": "${projectIdentifier}.dowhile1",
              "refTableName": "dowhile1"
            }
          ]
        },
        "do-while": {
          "maxIterations": 128,
          "parallelism": 0
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "dowhile1",
        "depends": [
          { "type": "Normal", "output": "${projectIdentifier}_root", "sourceType": "Manual" }
        ]
      }
    ]
  }
}
```

## Authoring Checklist

Before submitting a loop container, verify:

- [ ] `script.runtime.command` is `CONTROLLER_CYCLE`.
- [ ] `script.content` is **omitted** on the container.
- [ ] Top-level `do-while` object is present with `maxIterations` and `parallelism`.
- [ ] Exactly one `CONTROLLER_CYCLE_START` and one `CONTROLLER_CYCLE_END` sibling node exist alongside the container.
- [ ] Every body task has a dependency on `CYCLE_START` via `{ "type": "Normal", "output": "${projectIdentifier}.cycle_start" }`.
- [ ] `CYCLE_END` has a dependency on **every** terminal body task via `{ "type": "Normal", "output": "${projectIdentifier}.<body>" }`.
- [ ] External upstream/downstream wiring targets the **container** node only, never the start/end/body nodes.
- [ ] When submitting via OpenAPI: create the container first, then create each internal node (`CYCLE_START`, body tasks, `CYCLE_END`) with `container-id` set to the container's `Id`. Without `container-id`, the internal nodes will not be associated with the loop.
- [ ] The container's `outputs.nodeOutputs[]` exposes the loop to the rest of the flow (at minimum a `${projectIdentifier}.<loop_name>` entry).
- [ ] If the loop consumes an assignment-node result set, the assignment output is declared in the container's `spec.dependencies[].depends[]` and the body tasks reference it as `${dag.<input_name>}`.
