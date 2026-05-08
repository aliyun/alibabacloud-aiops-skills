# Merge Node（CONTROLLER_JOIN）

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no `script.content` required)
- Extension: `.join.json` (legacy UI-facing config; the authoritative config lives in `spec.join` of `*.spec.json`)

The merge node is a logical control node used to consolidate the run status of multiple upstream nodes. It solves the dependency-mounting problem for downstream nodes that would otherwise empty-run when an unselected branch is skipped, and it lets you apply explicit status-assertion rules to gate whether flow continues past the merge point.

## When a merge node is needed

A `CONTROLLER_BRANCH` can be used **without** a merge node: the selected arm runs, and tasks on unselected arms are automatically marked *not run* (status `"2"`) with their code never executed. If the different arms terminate independently (write different tables, call different services, etc.) and nothing downstream needs to run regardless of which arm was selected, a merge node is unnecessary.

Insert a `CONTROLLER_JOIN` merge node when either of the following is true:

1. **Rejoin flow after a branch** — a downstream node (or subgraph) must run regardless of which arm was selected. Without the merge node it would empty-run because the unselected arms propagate *not run* through the dependency graph.
2. **Gate flow on branch outcome** — you need to explicitly evaluate the run status of the selected arm's task(s) via `assertion` rules, combine multiple branch outcomes via `logic.expression`, and let the merge node's own success/failure decide whether the flow continues downstream of the merge point.

**Important — what the merge node actually merges**: The entries in `join.branches[]` reference the **outputs of the nodes that sit on each branch arm** — that is, the business nodes (shell, SQL, DI, …) whose upstream is a `CONTROLLER_BRANCH` — **not** the `CONTROLLER_BRANCH` node's own output. In a typical topology each branch arm has one or more real task nodes; the merge node consolidates the outputs of those task nodes (or the last node on each arm), because only those carry the "did this arm actually run" information via their run status.

**Typical scenario**: Branch node C defines two mutually exclusive arms. On each arm sits a task node — T1 on the "condition met" arm, T2 on the "condition not met" arm — and both arms write to the same downstream table. A downstream node B cannot depend on T1 and T2 directly (the task on the unselected arm will be marked *not run* and B will empty-run). Insert a merge node J whose `join.branches[]` references **T1's output and T2's output** (not C's output), with each branch's `assertion.in = ["1","2"]` (accept *success* or *not-run*) combined with `logic = AND`, then let B depend on J — J will succeed regardless of which arm was selected.

```
         Branch Node C
        ╱             ╲
       T1              T2          ← tasks on each arm; these are
    (met arm)    (not-met arm)       what the merge node references
        ╲             ╱
         Merge Node J              ← join.branches[] = [T1.output, T2.output]
              ↓
        Downstream Node B
```

More generally, the upstream referenced by a `join.branches[]` entry can be **any node whose run status carries the outcome of the branch arm** — most commonly the terminal node of the arm, but it can also be a chain of nodes deep inside a longer arm. The only requirement is that the referenced node sits on a branch arm rooted at a `CONTROLLER_BRANCH` so that its *not-run* state correctly reflects "this arm was not selected".

## Schema

A merge node is configured via the `join` field on the node spec. It has two required sub-fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `join.branches` | array | yes | Declarative list of upstream branches to consolidate. Each element gives the branch a **local name** (used in the logic expression), points at the **upstream output** being watched, and defines an **assertion** specifying which run statuses of that upstream count as "this branch satisfied". |
| `join.logic.expression` | string | yes | Boolean expression combining the local branch names using `and` / `or` / `not` / parentheses. The merge node succeeds iff this expression evaluates to true after all upstream branches reach a terminal state. |

### `join.branches[]`

```json
{
  "name": "b_1",
  "output": {
    "data": "${projectIdentifier}.upstream_task_on_branch_arm"
  },
  "assertion": {
    "field": "status",
    "in": ["1", "2"]
  }
}
```

| Sub-field | Description |
|-----------|-------------|
| `name` | Local alias for this branch; must be a valid identifier, referenced from `logic.expression`. Must be unique within the merge node. |
| `output.data` | Fully-qualified upstream output in the form `${projectIdentifier}.<upstream_node_name>`. This points at a **task node sitting on one arm of a `CONTROLLER_BRANCH`** (or any node downstream of such a task on that arm), **not** the `CONTROLLER_BRANCH` node itself. Must also appear in the merge node's `dependencies[].depends` (see below). |
| `assertion.field` | Always `status` (the upstream run status). |
| `assertion.in` | Array of run-status codes that satisfy this branch. |

**Run status codes** (used in `assertion.in`):

| Code | Meaning |
|------|---------|
| `"1"` | Upstream ran successfully |
| `"2"` | Upstream was not run (empty-run; e.g. the upstream is a task sitting on a `CONTROLLER_BRANCH` arm that was not selected) |
| `"3"` | Upstream ran and failed |

The common case for merging the task nodes on mutually-exclusive arms of a `CONTROLLER_BRANCH` is `"in": ["1", "2"]` — accept either a *successful run* or a *not-run* of each upstream task. For any single execution exactly one of the arm tasks will be in status `"1"` (the task on the selected arm) and the others in `"2"` (tasks on the unselected arms), so every branch entry in the merge node satisfies its assertion and the merge node consistently succeeds regardless of which arm was chosen.

### `join.logic.expression`

A boolean expression over the local `name`s declared in `branches[]`. Supported operators:

- `and`, `or`, `not`
- Parentheses for grouping

Examples:

| Expression | Semantics (for a two-branch merge `b_1`, `b_2`) |
|------------|--------------------------------------------------|
| `b_1 and b_2` | Both branches must satisfy their assertion (AND — all-of). This is the standard choice for merging mutually-exclusive `CONTROLLER_BRANCH` outputs when every branch's `assertion.in` accepts both *success* (`"1"`) and *not-run* (`"2"`) — the selected branch evaluates true via `"1"` and the unselected branches evaluate true via `"2"`, so the AND over all of them holds regardless of which branch was selected. |
| `b_1 or b_2` | At least one branch must satisfy its assertion (OR — any-of). Use this for independent parallel upstreams when the merge should succeed as long as any one of them finished in an acceptable state. |
| `(b_1 and b_2) or b_3` | Arbitrary combinators are allowed |

**Selection rule of thumb**:

| Upstream topology | Recommended `logic.expression` | Recommended `assertion.in` |
|-------------------|--------------------------------|----------------------------|
| Task nodes sitting on mutually-exclusive arms of a `CONTROLLER_BRANCH` (the typical scenario) | `b_1 and b_2 and …` | `["1", "2"]` — accept both *success* and *not-run*, so every arm task's assertion holds regardless of which arm was selected |
| Independent parallel upstreams where ALL must finish successfully | `b_1 and b_2 and …` | `["1"]` |
| Independent parallel upstreams where ANY one satisfying is enough | `b_1 or b_2 or …` | topology-dependent |

## Dependency Wiring

`join.branches[].output` only declares the *semantic* mapping between local names and upstream outputs. The scheduler still requires the standard dependency declaration:

- **`dependencies[].depends`** — declare a `Normal` dependency on each upstream node output referenced by `join.branches[].output.data`.

Both (`join.branches` and `dependencies`) must list the same upstream outputs. Missing either one will cause the merge node to fail to trigger or to empty-run.

## Other Requirements

| Requirement | Detail |
|-------------|--------|
| `script.runtime.command` | Must be `CONTROLLER_JOIN`. |
| `script.content` | **Required when submitting via OpenAPI** — see the "`script.content` format (OpenAPI adapter)" section below. When authoring locally the merge node carries no user code, but the OpenAPI adapter requires `script.content` to be populated with a `ControllerJoinCode` JSON string for the merge config to take effect. |
| `script.runtime.cu` | Small allocation (e.g. `"0.25"`) is sufficient; the merge node does not perform computation. |
| `outputs.nodeOutputs` | Must declare the merge node's own output so downstream nodes can depend on it. |
| Execution result | Currently the merge node can only be marked as *success* when the logic expression evaluates to true; it cannot propagate a *failure* status. |
| Product version | DataWorks Standard Edition or above. |

## `script.content` format (OpenAPI adapter)

When creating or updating a merge node via OpenAPI, the `join` field on the spec alone is **not sufficient** — the platform also requires `script.content` to be populated with a JSON string carrying the equivalent merge configuration (called `ControllerJoinCode`). If `script.content` is omitted or empty, the merge rules will not take effect and the node will behave as if no branches were configured.

**Format**: `script.content` must be a JSON string (i.e. the value is a stringified JSON object) with two top-level keys:

```json
{
  "branchList": [
    {
      "node": "${projectIdentifier}.upstream_task_on_arm_1",
      "runStatus": [1, 2],
      "logic": 1
    },
    {
      "node": "${projectIdentifier}.upstream_task_on_arm_2",
      "runStatus": [1, 2],
      "logic": 1
    }
  ],
  "resultStatus": "1"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `branchList` | array | One entry per upstream branch being merged. Must correspond 1:1 with the entries in `join.branches[]` and `inputs.nodeOutputs[]`. |
| `branchList[].node` | string | Fully-qualified upstream output identifier (same value as `join.branches[].output.data` / `inputs.nodeOutputs[].data`). |
| `branchList[].runStatus` | int array | Which upstream run-status codes satisfy this branch: `1` = success, `2` = not-run, `3` = failure. Maps directly to `join.branches[].assertion.in` (same codes, but here as integers instead of strings). |
| `branchList[].logic` | int | Combination mode for this branch: `1` = AND (this branch must satisfy), `2` = OR (this branch optionally satisfies). All entries should use the same value — mixed AND/OR within a single merge is not standard. Maps to the `join.logic.expression` combinator. |
| `resultStatus` | string | The merge node's own result status when the logic evaluates to true. `"1"` = success. |

**Consistency rule**: the `script.content` JSON and the `join` field must encode the **same** merge logic. The caller is responsible for keeping them in sync — on updates, both must be refreshed together. The `join` field is the semantic model read by the UI; `script.content` is what the execution engine actually evaluates at runtime.

**Example**: for a two-branch merge with AND logic accepting both success and not-run:

```json
"script": {
  "runtime": { "command": "CONTROLLER_JOIN", "cu": "0.25" },
  "content": "{\"branchList\":[{\"node\":\"${projectIdentifier}.branch_condition_true_shell\",\"runStatus\":[1,2],\"logic\":1},{\"node\":\"${projectIdentifier}.branch_condition_false_shell\",\"runStatus\":[1,2],\"logic\":1}],\"resultStatus\":\"1\"}"
}
```

## Full Example

Two shell task nodes (`分支条件满足_shell`, `分支条件不满足_shell`) sit on the two mutually-exclusive arms of an upstream `CONTROLLER_BRANCH`. The merge node references **these two shell tasks' outputs** (not the branch node's own output). Each branch entry's assertion accepts both *success* (`"1"`) and *not-run* (`"2"`), and the logic expression ANDs them — so for any single execution the task on the selected arm matches via `"1"` and the task on the unselected arm matches via `"2"`, and the merge node consistently succeeds regardless of which arm was chosen.

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "join_node",
        "recurrence": "Normal",
        "script": {
          "runtime": { "command": "CONTROLLER_JOIN", "cu": "0.25" },
          "content": "{\"branchList\":[{\"node\":\"${projectIdentifier}.branch_condition_true_shell\",\"runStatus\":[1,2],\"logic\":1},{\"node\":\"${projectIdentifier}.branch_condition_false_shell\",\"runStatus\":[1,2],\"logic\":1}],\"resultStatus\":\"1\"}"
        },
        "join": {
          "branches": [
            {
              "name": "b_1",
              "output": {
                "data": "${projectIdentifier}.branch_condition_true_shell"
              },
              "assertion": { "field": "status", "in": ["1", "2"] }
            },
            {
              "name": "b_2",
              "output": {
                "data": "${projectIdentifier}.branch_condition_false_shell"
              },
              "assertion": { "field": "status", "in": ["1", "2"] }
            }
          ],
          "logic": { "expression": "b_1 and b_2" }
        },
        "outputs": {
          "nodeOutputs": [
            { "data": "${projectIdentifier}.join_node", "refTableName": "join_node" }
          ]
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "join_node",
        "depends": [
          { "type": "Normal", "output": "${projectIdentifier}.branch_condition_true_shell" },
          { "type": "Normal", "output": "${projectIdentifier}.branch_condition_false_shell" }
        ]
      }
    ]
  }
}
```

## Authoring Checklist

Before submitting a merge node, verify:

- [ ] `script.runtime.command` is `CONTROLLER_JOIN`.
- [ ] `join.branches[]` has at least two entries, each with a unique `name`.
- [ ] Every `join.branches[].output.data` is also listed in `dependencies[].depends` for this node.
- [ ] Each `join.branches[].output.data` points at a **task node on a branch arm** (or a node downstream of such a task on that arm) — **not** the `CONTROLLER_BRANCH` node itself.
- [ ] `assertion.in` uses the correct run-status codes (`"1"` success, `"2"` not-run, `"3"` failure). For tasks on mutually-exclusive `CONTROLLER_BRANCH` arms use `["1","2"]` so that both the selected-arm task (success) and unselected-arm tasks (not-run) satisfy the assertion.
- [ ] `logic.expression` references exactly the set of names declared in `join.branches[].name`. For tasks on mutually-exclusive `CONTROLLER_BRANCH` arms use `and` (all branches' assertions will hold). Use `or` only for independent parallel upstreams where any-of semantics is desired.
- [ ] `outputs.nodeOutputs` declares the merge node's own output so downstream nodes can depend on it.
- [ ] **`script.content` carries a valid `ControllerJoinCode` JSON string** when submitting via OpenAPI — with `branchList[]` entries matching 1:1 with `join.branches[]`, and `resultStatus: "1"`. The `script.content` and `join` field must encode the same merge logic. Without `script.content`, the merge rules will not take effect at runtime.
