# Parameter Node（PARAM_HUB）

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no code)
- Extension: `.param-hub.json`

The parameter node is a virtual node that does not perform data computation. It is used to centrally manage parameters; downstream nodes obtain required parameters by depending on the parameter node.

**Use cases**:
- Cross-node parameter passing: When multiple downstream nodes need upstream output parameters, the parameter node serves as a unified relay
- Parameter management: Centrally manage constant and variable parameters; downstream nodes can obtain them by simply adding a dependency

## Parameter Types

| Type | Description | Value |
|------|------|------|
| Constant | Fixed value parameter | Custom fixed value |
| Variable | Scheduling variable parameter | Scheduling parameter expression (e.g., time variable) |
| Pass-through variable | Passes upstream node output parameters | Binds to upstream node output parameters |

## Parameter Passing Rules

- Task nodes referencing the parameter node **must be direct downstream nodes of the parameter node**
- Downstream nodes bind the parameter node's output parameters in their scheduling parameters
- In the downstream node script, reference parameter values via `${parameter_name}`

## Configuration Method

### Defining Parameters in the Parameter Node

Define output parameters via `outputs.variables`:

```json
{
  "name": "my_param_hub",
  "script": {
    "path": "my_param_hub",
    "runtime": { "command": "PARAM_HUB" },
    "content": ""
  },
  "outputs": {
    "variables": [
      {
        "artifactType": "Variable",
        "name": "bizdate",
        "scope": "NodeContext",
        "type": "Constant",
        "value": "20260101"
      },
      {
        "artifactType": "Variable",
        "name": "env",
        "scope": "NodeContext",
        "type": "Constant",
        "value": "prod"
      }
    ],
    "nodeOutputs": [
      { "data": "${projectIdentifier}.my_param_hub", "artifactType": "NodeOutput" }
    ]
  }
}
```

### Downstream Node Parameter Reference

Downstream nodes bind to the parameter node's output via `inputs.variables`:

```json
{
  "name": "downstream_node",
  "script": {
    "path": "downstream_node",
    "runtime": { "command": "ODPS_SQL" },
    "content": "SELECT * FROM my_table WHERE dt='${bizdate}' AND env='${env}';",
    "parameters": [
      {
        "artifactType": "Variable",
        "name": "bizdate",
        "scope": "NodeContext",
        "type": "NodeOutput",
        "value": "${bizdate}",
        "node": { "output": "${projectIdentifier}.my_param_hub" }
      },
      {
        "artifactType": "Variable",
        "name": "env",
        "scope": "NodeContext",
        "type": "NodeOutput",
        "value": "${env}",
        "node": { "output": "${projectIdentifier}.my_param_hub" }
      }
    ]
  },
  "inputs": {
    "variables": [
      {
        "artifactType": "Variable",
        "name": "bizdate",
        "scope": "NodeContext",
        "type": "NodeOutput",
        "value": "${bizdate}",
        "node": { "output": "${projectIdentifier}.my_param_hub" }
      },
      {
        "artifactType": "Variable",
        "name": "env",
        "scope": "NodeContext",
        "type": "NodeOutput",
        "value": "${env}",
        "node": { "output": "${projectIdentifier}.my_param_hub" }
      }
    ],
    "nodeOutputs": [
      { "data": "${projectIdentifier}.my_param_hub", "artifactType": "NodeOutput" }
    ]
  }
}
```

## Restrictions

| Restriction | Details |
|--------|------|
| Pass level | Can only pass to direct downstream nodes |
| Node type | Virtual node; does not perform computation |

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_param_hub",
        "script": {
          "path": "example_param_hub",
          "runtime": {
            "command": "PARAM_HUB"
          },
          "content": ""
        }
      }
    ]
  }
}
```
