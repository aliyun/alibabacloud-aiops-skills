# Cross-cycle Dependency Check Node (DEPENDENT)

## Overview

- Compute engine: `GENERAL`
- Content format: JSON (inlined into `script.content`)
- Extension: `.json`

The Dependent node (依赖检查节点 / 跨周期依赖检查) waits for one or more **target upstream nodes' scheduled instances** to reach a satisfied state before letting its own downstream flow continue. Unlike a normal in-workflow dependency (`spec.dependencies[].depends`), which wires a direct edge between two nodes that run in the same cycle of the same workflow, a Dependent node **polls for the instance of a different node in a specific (often previous) cycle** and succeeds once that instance's status meets the configured rule.

Typical scenarios:

- A downstream flow should run only after a specific upstream job **in another workflow** has completed its own cycle.
- A daily-cycle flow must wait for the **previous day's** instance of another daily job before continuing.
- Multiple cross-workflow dependencies must be combined with `AND` / `OR` logic before the downstream branch is allowed to proceed.

## How it differs from normal dependencies

| | Normal `spec.dependencies[].depends` | `DEPENDENT` node |
|---|---|---|
| Scope | Same workflow, same cycle | Any node (in this or another workflow), any cycle selector |
| Wiring | Static edge in FlowSpec | Runtime check against a target node's scheduled instance |
| Cycle offset | Always the current cycle | Configurable (same day, previous day, same/previous hour, …) |
| Polling | N/A — instant edge | Polls at a configurable interval up to a max wait window |
| Status logic | Binary: upstream ran → I run | Rule set evaluates upstream instance status over a time window |

If the two nodes live in the same workflow **and** the same cycle, prefer the regular `spec.dependencies[].depends`. Use `DEPENDENT` only when you actually need cross-workflow or cross-cycle waiting.

See also [`CHECK.md`](./CHECK.md), [`CHECK_NODE.md`](./CHECK_NODE.md), and [`FTP_CHECK.md`](./FTP_CHECK.md) for **resource availability** check nodes (waiting for a partition, a file, etc.) — they solve a different problem from `DEPENDENT`, which waits for an **upstream node instance's status**.

## Schema

A Dependent node has no custom `spec.xxx` block. All of its configuration lives as a JSON document inside `script.content`.

### `script.runtime`

```json
"script": {
  "runtime": {
    "command": "DEPENDENT",
    "cu": "0.25"
  },
  "content": "<inlined JSON, see below>"
}
```

| Field | Description |
|-------|-------------|
| `command` | Must be `DEPENDENT`. |
| `cu` | A small allocation (e.g. `"0.25"`) is sufficient; the node only performs polling. |

### `script.content` JSON

```json
{
  "checkInterval": 1,
  "maxCheckMinutes": 60,
  "relation": "AND",
  "dependGroups": [
    {
      "relation": "AND",
      "items": [
        {
          "checkName": "check_item_1",
          "input": "<target_node_identifier>",
          "cycle": "DAY",
          "rules": [
            { "rule": "prevDays", "offset": 0 }
          ]
        },
        {
          "checkName": "check_item_2",
          "input": "<target_node_identifier>",
          "cycle": "DAY",
          "rules": [
            { "rule": "prevDays", "offset": 0 }
          ]
        }
      ]
    }
  ]
}
```

Top-level fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `checkInterval` | integer | yes | Polling interval in minutes. How often the node re-queries the target instance's status. |
| `maxCheckMinutes` | integer | yes | Maximum total wait window in minutes. If the target instance is still not satisfied after this window, the Dependent node fails. |
| `relation` | `AND` \| `OR` | yes | Top-level combinator across `dependGroups[]`. |
| `dependGroups` | array | yes | One or more groups of check items. Each group is itself a boolean combination of items; `dependGroups[].relation` sets the combinator **within** the group, and the top-level `relation` combines groups. |

### `dependGroups[].items[]`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `checkName` | string | yes | Human-readable name of this check item (shown in the UI and the run log). |
| `input` | string | yes | Identifier of the target upstream node whose instance is being waited on. In the real samples this is the target node's internal identifier (a numeric-looking string); the exact form depends on how the node is registered in your environment. |
| `cycle` | string | yes | Cycle granularity of the target node — for example `DAY` for a daily-cycle target, or a finer granularity for an hourly target. Must match the target node's own `cycleType`. |
| `rules[]` | array | yes | One or more rules defining **which cycle** of the target to wait for and what counts as "satisfied". |

### `dependGroups[].items[].rules[]`

Each rule selects a cycle of the target node relative to the current instance of the Dependent node.

| Field | Description |
|-------|-------------|
| `rule` | Cycle-selector name. In the real sample the value observed is `prevDays` — "a previous-day instance of the target". Other values exist for finer granularities (e.g. previous hours); pick the one that matches the target's cycle. |
| `offset` | Integer offset from the current cycle. `0` means the **same cycle** as the current instance (today for a daily cycle); `1` means one cycle earlier (yesterday); and so on. Use a positive number to look further back. |

**Status assertion**: the node is considered satisfied for a given check item once the selected target instance reaches a **success** terminal state. A failed target instance does not satisfy the wait. If multiple rules or items are combined, the combinator (`AND`/`OR`) on the enclosing group / top-level `relation` determines the overall outcome. The node keeps polling at `checkInterval` until either the combined expression becomes true or `maxCheckMinutes` is exceeded.

### Dependency wiring

A Dependent node is wired into the workflow with the **same** FlowSpec dependency edges as any other node — the cross-cycle wait is an in-node behavior, not a replacement for `spec.dependencies[].depends`. Typically the Dependent node sits as (or near) the root of its workflow: upstream is the workflow root, and downstream business nodes depend on the Dependent node's own output.

```json
"outputs": { "nodeOutputs": [ { "sourceType": "System", "data": "${projectIdentifier}.my_depend_check", "refTableName": "my_depend_check" } ] }
```

## Full example

A daily-cycle Dependent node `my_depend_check` that waits for two target nodes' **same-day** instances to finish successfully, combined with `AND`.

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "my_depend_check",
        "recurrence": "Normal",
        "script": {
          "path": "my_depend_check",
          "runtime": {
            "command": "DEPENDENT",
            "cu": "0.25"
          },
          "content": "{\n  \"checkInterval\": 1,\n  \"maxCheckMinutes\": 60,\n  \"relation\": \"AND\",\n  \"dependGroups\": [\n    {\n      \"relation\": \"AND\",\n      \"items\": [\n        { \"checkName\": \"check_item_1\", \"input\": \"<target_node_identifier_1>\", \"cycle\": \"DAY\", \"rules\": [ { \"rule\": \"prevDays\", \"offset\": 0 } ] },\n        { \"checkName\": \"check_item_2\", \"input\": \"<target_node_identifier_2>\", \"cycle\": \"DAY\", \"rules\": [ { \"rule\": \"prevDays\", \"offset\": 0 } ] }\n      ]\n    }\n  ]\n}"
        },
        "trigger": {
          "type": "Scheduler",
          "cron": "00 00 00 * * ?",
          "cycleType": "Daily",
          "timezone": "Asia/Shanghai"
        },
        "outputs": { "nodeOutputs": [ { "sourceType": "System", "data": "${projectIdentifier}.my_depend_check", "refTableName": "my_depend_check" } ] }
      }
    ],
    "dependencies": [
      {
        "nodeId": "my_depend_check",
        "depends": [
          { "type": "Normal", "output": "${projectIdentifier}_root" }
        ]
      }
    ]
  }
}
```

## Authoring checklist

Before submitting a Dependent node, verify:

- [ ] `script.runtime.command` is `DEPENDENT`.
- [ ] `script.content` is the full JSON document (stringified) containing `checkInterval`, `maxCheckMinutes`, `relation`, and `dependGroups[]`.
- [ ] Every `dependGroups[].items[].input` points to a valid **target** node identifier. Do not embed a node *name* where an identifier is expected.
- [ ] Every `items[].cycle` matches the target node's actual cycle granularity.
- [ ] `checkInterval` is small enough to catch a target finishing quickly, but not so small it wastes scheduling resources.
- [ ] `maxCheckMinutes` is large enough to cover the expected arrival window of the target instance, including upstream delays.
- [ ] Cycle offsets (`rules[].offset`) are computed relative to the current Dependent instance's cycle — `0` = same cycle, `1` = previous cycle, etc.
- [ ] If the target node lives in the **same workflow and the same cycle**, prefer a normal `spec.dependencies[].depends` edge over a Dependent node.
- [ ] The Dependent node has an explicit downstream output declared in `outputs.nodeOutputs[]`, and downstream business nodes depend on it.
