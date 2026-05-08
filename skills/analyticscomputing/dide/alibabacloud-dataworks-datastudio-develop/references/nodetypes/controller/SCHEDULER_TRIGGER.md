# Trigger Node (SCHEDULER_TRIGGER)

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no `script.content` required)
- Extension: `.json`
- Language: `plaintext`

The Trigger node (a.k.a. HTTP Trigger) is a special virtual-style control node that acts as an **inbound entry point** into a DataWorks workflow. It carries no user code and performs no computation of its own. Its purpose is to give external systems a handle to fire the workflow on demand (in addition to the normal scheduled cron firing), so downstream tasks that depend on this node's output run when the trigger is fired.

## Purpose and usage

A Trigger node is used whenever the downstream flow must be kick-started by an **external signal** — for example, a business system that needs to invoke a DataWorks workflow after an upstream event, or an operator who wants to fire the flow without waiting for the next scheduled tick. Typical usage pattern:

1. Place the Trigger node as the root (or one of the roots) of the workflow.
2. Wire downstream business nodes (SQL, shell, DI, …) so that they depend on the Trigger node's output.
3. The Trigger node still has a normal `trigger.cron` / `cycleType`, so the flow **also** runs on its regular schedule. The inbound invocation is an additional, on-demand firing — not a replacement.

Direction of the HTTP call: **inbound only**. The Trigger node does **not** make outgoing HTTP requests to an external service. If you need to call an external HTTP endpoint from within a workflow, use a shell / python task (or an appropriate integration node) instead. The "HTTP" in "HTTP Trigger" refers to the fact that the external system invokes DataWorks over HTTP and DataWorks then fires the trigger node's instance.

## Runtime behavior

These are runtime constraints set by the DataWorks platform itself, not by the FlowSpec — an authoring agent should be aware of them when choosing whether to use a Trigger node:

- **Edition requirement** — Trigger nodes are available on **DataWorks Enterprise Edition or higher** only. On lower editions the node will not be dispatchable.
- **Resource group** — the node **must** be bound to a Serverless scheduling resource group that is already associated with the workspace. There is no default.
- **Instance generation mode** — two options at publish time: `T+1 next day` (instances appear the day after publish) or `immediate post-publish` (instances appear as soon as the node is published). Choose based on whether the external caller needs to fire the workflow on the same day the trigger is published.
- **Preconditions for an inbound fire** — when the external system invokes the trigger, DataWorks will only actually run the instance when **all** of the following are satisfied:
  1. A periodic instance for the current cycle exists in Operation Center (i.e. the trigger has been scheduled into the cycle).
  2. Every upstream / parent dependency has already completed successfully.
  3. The instance's scheduled start time has been reached.
  4. The bound resource group has sufficient capacity.
  5. The node is not frozen (i.e. not paused in Operation Center).
  6. The instance is in the **"awaiting trigger"** state. A succeeded instance **cannot be re-triggered**; to fire the same logical node again you must wait for the next cycle's instance.
- **Inbound trigger signal retention** — an external fire signal is held for at most **24 hours**. If the preconditions above (especially upstream completion) are not all met within 24 hours of the external call, the signal expires and the node will not run. The external caller would then have to re-issue the trigger.
- **No re-trigger after success** — once an instance has finished successfully, further inbound fires against the same instance are ignored.

Because of these constraints, a Trigger node is best used as the workflow root with a permissive schedule so that the "awaiting trigger" window is wide enough for the external caller, and the upstream chain is minimal (ideally only `${projectIdentifier}_root`).

## Schema

A Trigger node has no dedicated `spec.xxx` configuration block — the node is fully described by its standard FlowSpec fields. All trigger-specific behavior comes from two places:

| Where | What it carries |
|-------|-----------------|
| `script.runtime.command` | Must be `SCHEDULER_TRIGGER`. This is what marks the node as a trigger and makes it invocable from outside. |
| `script.language` | `plaintext` (the node carries no real code). |
| `script.content` | Empty / omitted. The Trigger node has no user code. |
| `trigger` | A normal scheduler trigger block (`type: Scheduler`, `cron`, `cycleType`, `timezone`, …). The node still runs on its cron; inbound invocations fire it **in addition** to scheduled runs. |
| `outputs.nodeOutputs[]` | At least one output that downstream nodes depend on. This is the only way downstream tasks "see" that the trigger fired. |

### `script.runtime`

```json
"script": {
  "language": "plaintext",
  "runtime": {
    "command": "SCHEDULER_TRIGGER",
    "cu": "0.25"
  }
}
```

| Field | Description |
|-------|-------------|
| `command` | Must be `SCHEDULER_TRIGGER`. |
| `cu` | A small allocation (e.g. `"0.25"`) is sufficient; the node performs no computation. |

### `trigger`

Even though the node is designed to be fired by external calls, a scheduler trigger block is still required — DataWorks treats it as a normal scheduled node for cycle management, instance generation, and deployment.

```json
"trigger": {
  "type": "Scheduler",
  "cron": "00 01 00 * * ?",
  "cycleType": "Daily",
  "startTime": "1970-01-01 00:00:00",
  "endTime":   "9999-01-01 00:00:00",
  "timezone":  "Asia/Shanghai",
  "delaySeconds": 0
}
```

See [`../../scheduling-guide.md`](../../scheduling-guide.md) for the full set of scheduler fields.

### Dependency wiring

A Trigger node is typically a **root node** of its workflow — its only upstream is the workflow root (`${projectIdentifier}_root`). Downstream business nodes then depend on the Trigger node's own output.

```json
"outputs": {
  "nodeOutputs": [
    { "sourceType": "System", "data": "${projectIdentifier}.my_http_trigger", "refTableName": "my_http_trigger" }
  ]
}
```

Downstream node:

```json
"dependencies": [
  {
    "nodeId": "downstream_task",
    "depends": [
      { "type": "Normal", "output": "${projectIdentifier}.my_http_trigger" }
    ]
  }
]
```

## Full example

A Trigger node `my_http_trigger` that fires daily at 00:01 on its normal schedule and can additionally be fired on demand from an external system. Downstream tasks depend on its output.

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "my_http_trigger",
        "recurrence": "Normal",
        "script": {
          "path": "my_http_trigger",
          "language": "plaintext",
          "runtime": {
            "command": "SCHEDULER_TRIGGER",
            "cu": "0.25"
          }
        },
        "trigger": {
          "type": "Scheduler",
          "cron": "00 01 00 * * ?",
          "cycleType": "Daily",
          "timezone": "Asia/Shanghai"
        },
        "outputs": {
          "nodeOutputs": [
            { "sourceType": "System", "data": "${projectIdentifier}.my_http_trigger", "refTableName": "my_http_trigger" }
          ]
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "my_http_trigger",
        "depends": [
          { "type": "Normal", "output": "${projectIdentifier}_root" }
        ]
      }
    ]
  }
}
```

## Authoring checklist

Before submitting a Trigger node, verify:

- [ ] `script.runtime.command` is `SCHEDULER_TRIGGER`.
- [ ] `script.language` is `plaintext` (or omitted); `script.content` is empty or omitted — the node carries no user code.
- [ ] A normal `trigger` block is present (`type: Scheduler` + `cron` + `cycleType` + `timezone`). The node still runs on its cron; external invocations fire it additionally.
- [ ] The node has at least one entry under `outputs.nodeOutputs[]`; downstream tasks depend on that output.
- [ ] The node is positioned as a workflow root — its only upstream is `${projectIdentifier}_root` — unless you have a deliberate reason for it to sit mid-flow. This also keeps the "awaiting trigger" window wide enough for the external caller within the 24-hour inbound-signal retention.
- [ ] The target workspace is on **DataWorks Enterprise Edition or higher** and has a Serverless scheduling resource group bound — the Trigger node requires both.
- [ ] The upstream chain from the Trigger node is minimal. Remember: the inbound fire signal is held for at most 24 hours, and the node will only run when **all** upstream dependencies have also completed within that window.
- [ ] Do not rely on re-triggering a succeeded instance — a fresh inbound fire against an already-succeeded instance is ignored. For a repeat run, wait for the next cycle's instance.
- [ ] Do not use this node to **make** outgoing HTTP calls from a workflow — the Trigger node is inbound-only.
