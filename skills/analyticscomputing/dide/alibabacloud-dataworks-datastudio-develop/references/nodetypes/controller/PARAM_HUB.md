# Parameter Hub Node（PARAM_HUB）

## Overview

- Compute engine: `GENERAL`
- `script.content`: none (the parameter hub node carries no executable code)
- `script.language`: none
- Authoritative extension: `.param-hub.json` (sidecar file carrying the node's parameter definitions)

The parameter hub node (参数中心 / 参数集线器) is a logical control node that centrally declares a set of variables and publishes them to direct downstream nodes. It does not perform any computation; its sole purpose is to act as a named container of variables that downstream nodes can consume by name.

Typical use cases:

- **Centralized parameter management** — declare a bundle of constants and scheduling variables in one place and reuse them across multiple downstream tasks.
- **Upstream-parameter fan-out / relay** — receive an output variable from an upstream assignment node and re-publish it under a stable name so multiple direct downstream nodes can each consume it without each wiring up their own `referenceVariable` to the original assignment node.

## Variable Types

A parameter hub node declares its variables under **two** places that must stay in sync:

1. `script["param-hub"].variables[]` — the authoritative definition list (the legacy sidecar `.param-hub.json` carries the same shape).
2. `outputs.variables[]` — the scheduler-facing declaration that downstream nodes actually bind to. Each entry mirrors the corresponding `param-hub.variables[]` entry and additionally carries a `referenceVariable` and a `node` referencing the parameter hub node itself by name.

Each variable has a `type`, which is one of:

| `type` | Meaning | `value` semantics |
|--------|---------|-------------------|
| `Constant` | A fixed literal value. | Raw string literal the parameter evaluates to at runtime (e.g. `"1111"`, `"prod"`). |
| `System` | A scheduling / system variable. | System expression such as `$yyyymmdd`, `$bizdate`, etc.; evaluated by the scheduler at runtime. |
| `PassThrough` | Re-exposes a variable produced by an upstream node (typically a `CONTROLLER_ASSIGNMENT` node's `outputs` variable) under a name local to this parameter hub. | A pass-through value identifier; the `referenceVariable` sub-field points at the upstream node that supplies it. |

All three types share:

- `artifactType: "Variable"`
- `scope: "NodeContext"`
- `name` — the name downstream nodes use when binding (via `inputName`) to this variable.

## Schema

### `script["param-hub"].variables[]`

This is the canonical definition list. One entry per variable the hub publishes.

```json
"param-hub": {
  "variables": [
    {
      "name": "const1",
      "scope": "NodeContext",
      "type": "Constant",
      "value": "1111",
      "description": "111"
    },
    {
      "name": "sysvar1",
      "scope": "NodeContext",
      "type": "System",
      "value": "$yyyymmdd",
      "description": "var"
    },
    {
      "name": "passthroughvar1",
      "scope": "NodeContext",
      "type": "PassThrough",
      "value": "8592858772760529423:outputs",
      "description": "inputvar1",
      "referenceVariable": {
        "name": "outputs",
        "scope": "NodeContext",
        "type": "NodeOutput",
        "node": {
          "name": "assignment1"
        }
      }
    }
  ]
}
```

| Sub-field | Required | Description |
|-----------|----------|-------------|
| `name` | yes | Local variable name. Downstream nodes bind to this name. Must be unique within the parameter hub. |
| `scope` | yes | Always `NodeContext`. |
| `type` | yes | `Constant`, `System`, or `PassThrough`. |
| `value` | yes | For `Constant`: the literal. For `System`: the system expression (e.g. `$yyyymmdd`). For `PassThrough`: an internal pass-through identifier of the form `<upstream-id>:<upstream-var-name>`. |
| `description` | optional | Human-readable description shown in the UI. |
| `referenceVariable` | required for `PassThrough` only | Points at the upstream variable being re-published. `name`/`scope`/`type` mirror the upstream node's `outputs.variables[]` entry (e.g. `name: "outputs"`, `type: "NodeOutput"` when relaying from an assignment node), and `node.name` identifies the upstream node within the workflow. |

### `outputs.variables[]` mirror

Each `param-hub.variables[]` entry must also appear under `outputs.variables[]` so the scheduler publishes it as a bindable output. The outputs mirror carries two extra fields that are not in the sidecar:

- `node.name` — the parameter hub node's own `name`, declaring that the variable belongs to this node.
- `referenceVariable` — for `Constant` and `System` types this is **self-referential** (points back at the parameter hub itself, with `node.refTableName` equal to the hub's own `refTableName`). For `PassThrough` type this points at the **upstream source node** that actually produces the value.

```json
"outputs": {
  "nodeOutputs": [
    {
      "data": "${projectIdentifier}.my_param_hub",
      "refTableName": "my_param_hub"
    }
  ],
  "variables": [
    {
      "name": "const1",
      "scope": "NodeContext",
      "type": "Constant",
      "value": "1111",
      "node": { "name": "my_param_hub" },
      "referenceVariable": {
        "name": "const1",
        "scope": "NodeContext",
        "type": "Constant",
        "value": "1111",
        "node": {
          "name": "my_param_hub",
          "refTableName": "my_param_hub"
        }
      }
    },
    {
      "name": "sysvar1",
      "scope": "NodeContext",
      "type": "System",
      "value": "$yyyymmdd",
      "node": { "name": "my_param_hub" },
      "referenceVariable": {
        "name": "sysvar1",
        "scope": "NodeContext",
        "type": "System",
        "value": "$yyyymmdd",
        "node": {
          "name": "my_param_hub",
          "refTableName": "my_param_hub"
        }
      }
    },
    {
      "name": "passthroughvar1",
      "scope": "NodeContext",
      "type": "PassThrough",
      "value": "8592858772760529423:outputs",
      "node": { "name": "my_param_hub" },
      "referenceVariable": {
        "name": "outputs",
        "scope": "NodeContext",
        "type": "NodeOutput",
        "value": "8592858772760529423:outputs",
        "node": { "name": "assignment1" }
      }
    }
  ]
}
```

### `script` block

```json
"script": {
  "runtime": {
    "command": "PARAM_HUB",
    "cu": "0.25"
  }
}
```

The parameter hub node has no `script.content`, no `script.language`, and no `datasource`. `script.runtime.command` must be `PARAM_HUB`; a small `cu` allocation (e.g. `"0.25"`) is sufficient because the node performs no computation.

## Downstream Consumption

A direct downstream node binds to a parameter hub variable via `inputs.variables[]`, giving it a local access name through `inputName`:

```json
"inputs": {
  "variables": [
    {
      "name": "const1",
      "scope": "NodeContext",
      "type": "Constant",
      "value": "1111",
      "inputName": "const_val",
      "referenceVariable": {
        "name": "const1",
        "scope": "NodeContext",
        "type": "Constant",
        "value": "1111",
        "node": {
          "name": "my_param_hub",
          "refTableName": "my_param_hub"
        }
      }
    }
  ]
}
```

- `name`/`scope`/`type`/`value` must match the parameter hub's `outputs.variables[]` entry for the variable being consumed.
- `inputName` is the local alias the downstream node's code references via `${inputName}`.
- `referenceVariable.node` identifies the parameter hub by `name` (and optionally `refTableName`). **Do not** place parameter hub variables into `script.parameters` — that field is reserved for node-local scheduling parameters; context variables published by a parameter hub must be received via `inputs.variables[]`.

Parameter hub variables can only be consumed by **direct downstream** nodes; cross-level (grand-child) consumption is not supported. This matches the assignment node rule.

## Dependency Wiring

The parameter hub participates in the normal dependency graph:

- **Upstream → parameter hub** — if the hub has a `PassThrough` variable, the upstream node that supplies it (typically an assignment node) must be declared as a real dependency under `dependencies[].depends`. Declare a second `Normal` dependency on `${projectIdentifier}_root` (or the upstream of your choice) if the hub has no upstream variable source.
- **Parameter hub → downstream** — each downstream node that consumes a variable from the hub must depend on the hub's own output `${projectIdentifier}.<param_hub_node_name>` via `dependencies[].depends`.

## Other Requirements

| Requirement | Detail |
|-------------|--------|
| `script.runtime.command` | Must be `PARAM_HUB`. |
| `script.runtime.cu` | Small allocation (e.g. `"0.25"`) is sufficient. |
| `script.content` | Omit. Do not set to `"{}"`. |
| `script.language` | Omit. |
| `datasource` | Not required (the hub performs no computation). |
| Pass level | Variables can only be consumed by direct downstream nodes. |
| Definition dual-write | Every variable must appear **both** in `script["param-hub"].variables[]` and in `outputs.variables[]`. |

## Full Example

A parameter hub `my_param_hub` that publishes three variables — a constant, a system date variable, and a pass-through of an upstream assignment node's `outputs` variable:

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "my_param_hub",
        "recurrence": "Normal",
        "script": {
          "runtime": {
            "command": "PARAM_HUB",
            "cu": "0.25"
          }
        },
        "trigger": {
          "type": "Scheduler",
          "cron": "00 21 00 * * ?",
          "cycleType": "Daily",
          "startTime": "1970-01-01 00:00:00",
          "endTime": "9999-01-01 00:00:00",
          "timezone": "Asia/Shanghai"
        },
        "runtimeResource": {
          "resourceGroup": "${spec.runtimeResource.resourceGroup}"
        },
        "outputs": {
          "nodeOutputs": [
            {
              "data": "${projectIdentifier}.my_param_hub",
              "refTableName": "my_param_hub"
            }
          ],
          "variables": [
            {
              "name": "const1",
              "scope": "NodeContext",
              "type": "Constant",
              "value": "1111",
              "node": { "name": "my_param_hub" },
              "referenceVariable": {
                "name": "const1",
                "scope": "NodeContext",
                "type": "Constant",
                "value": "1111",
                "node": {
                  "name": "my_param_hub",
                  "refTableName": "my_param_hub"
                }
              }
            },
            {
              "name": "sysvar1",
              "scope": "NodeContext",
              "type": "System",
              "value": "$yyyymmdd",
              "node": { "name": "my_param_hub" },
              "referenceVariable": {
                "name": "sysvar1",
                "scope": "NodeContext",
                "type": "System",
                "value": "$yyyymmdd",
                "node": {
                  "name": "my_param_hub",
                  "refTableName": "my_param_hub"
                }
              }
            },
            {
              "name": "passthroughvar1",
              "scope": "NodeContext",
              "type": "PassThrough",
              "value": "8592858772760529423:outputs",
              "node": { "name": "my_param_hub" },
              "referenceVariable": {
                "name": "outputs",
                "scope": "NodeContext",
                "type": "NodeOutput",
                "value": "8592858772760529423:outputs",
                "node": { "name": "upstream_assign" }
              }
            }
          ]
        },
        "param-hub": {
          "variables": [
            {
              "name": "const1",
              "scope": "NodeContext",
              "type": "Constant",
              "value": "1111",
              "description": "a constant literal"
            },
            {
              "name": "sysvar1",
              "scope": "NodeContext",
              "type": "System",
              "value": "$yyyymmdd",
              "description": "scheduling date variable"
            },
            {
              "name": "passthroughvar1",
              "scope": "NodeContext",
              "type": "PassThrough",
              "value": "8592858772760529423:outputs",
              "description": "relay of upstream assignment output",
              "referenceVariable": {
                "name": "outputs",
                "scope": "NodeContext",
                "type": "NodeOutput",
                "node": { "name": "upstream_assign" }
              }
            }
          ]
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "my_param_hub",
        "depends": [
          {
            "type": "Normal",
            "output": "${projectIdentifier}.upstream_assign",
            "sourceType": "Manual"
          },
          {
            "type": "Normal",
            "output": "${projectIdentifier}_root",
            "sourceType": "Manual"
          }
        ]
      }
    ]
  }
}
```

## Legacy `.param-hub.json` Sidecar

The parameter hub node has a legacy sidecar file `<node_name>.param-hub.json` that mirrors the `script["param-hub"].variables[]` list (the same array, without the enclosing `"param-hub"` key):

```json
{
  "variables": [
    {
      "name": "const1",
      "type": "Constant",
      "scope": "NodeContext",
      "description": "111",
      "value": "1111"
    },
    {
      "name": "sysvar1",
      "type": "System",
      "scope": "NodeContext",
      "description": "var",
      "value": "$yyyymmdd"
    },
    {
      "name": "passthroughvar1",
      "type": "PassThrough",
      "scope": "NodeContext",
      "description": "inputvar1",
      "referenceVariable": {
        "name": "outputs",
        "type": "NodeOutput",
        "scope": "NodeContext",
        "node": {
          "nodeName": "upstream_assign",
          "projectIdentifier": "${projectIdentifier}"
        }
      }
    }
  ]
}
```

The sidecar is UI-facing; the authoritative configuration lives under `script["param-hub"]` in `*.spec.json`. Both must stay in sync.

## Authoring Checklist

Before submitting a parameter hub node, verify:

- [ ] `script.runtime.command` is `PARAM_HUB`.
- [ ] `script.content`, `script.language`, and `datasource` are **omitted**.
- [ ] Every variable is declared **both** in `script["param-hub"].variables[]` and in `outputs.variables[]`, with matching `name`/`scope`/`type`/`value`.
- [ ] Each `outputs.variables[]` entry carries a `node.name` matching the parameter hub node itself, and a `referenceVariable` whose `node` is self-referential for `Constant` / `System` types, or points at the upstream source node for `PassThrough` type.
- [ ] Each `PassThrough` variable has a matching upstream declared under `inputs.variables[]` (consuming from the upstream assignment node) and a `Normal` dependency on that upstream under `dependencies[].depends`.
- [ ] Downstream nodes consume parameter hub variables via `inputs.variables[]` with `inputName`, **not** via `script.parameters`.
- [ ] Downstream nodes depend on `${projectIdentifier}.<param_hub_node_name>` under `dependencies[].depends`.
- [ ] The legacy `<node_name>.param-hub.json` sidecar matches `script["param-hub"].variables[]`.
