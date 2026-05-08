# Python Script (PYTHON)

## Overview

- Compute engine: `GENERAL`
- Content format: python
- Extension: `.py`
- Description: Run Python 3 scripts on DataWorks scheduling resource groups

The Python node runs a Python 3 source file on a scheduling resource group. It is suitable for data processing, ETL helper logic, calling external APIs, and similar scripting tasks. The source code lives in a `.py` file and is embedded into `script.content` at build time — there is no on-host code path or remote fetch.

## Schema

The Python node shares most of its shape with `DIDE_SHELL`. This section documents only the fields that behave differently or that the sample makes concrete.

### `script` block

| Field | Required | Description |
|-------|----------|-------------|
| `script.language` | yes | `python3`. This pins the interpreter; only Python 3 is supported. |
| `script.runtime.command` | yes | `PYTHON`. Immutable once the node is created. |
| `script.runtime.cu` | optional | CU allocation for the task container, e.g. `"0.5"`. |
| `script.content` | yes | The full `.py` source, embedded inline as a single string. The build step reads the companion `.py` file and injects it here. There is no separate `path`-on-host field. |
| `script.parameters[]` | optional | Arguments passed to the Python process. See "Parameter passing" below. |

### `runtimeResource`

| Field | Description |
|-------|-------------|
| `runtimeResource.resourceGroup` | Identifier of the Serverless scheduling resource group that will run the script. In the sample this is templated as `${spec.runtimeResource.resourceGroup}` and supplied via `dataworks.properties`. |

## Parameter passing

The sample declares a single entry under `script.parameters` using the `NoKvVariableExpression` type:

```json
"parameters": [
  {
    "name": "-",
    "scope": "NodeParameter",
    "type": "NoKvVariableExpression",
    "value": " arrr11 arrr2"
  }
]
```

What this means, based on the sample:

- `type: "NoKvVariableExpression"` declares a **positional argument string** rather than a named `key=value` parameter. The entire `value` is appended to the Python command line and exposed to the script as `sys.argv`.
- `name` is set to `"-"` because there is no variable name to bind — the engine treats the row as a raw argv tail.
- The script reads positional arguments by index. The sample script does exactly this:

  ```python
  import sys
  print("hello, arg1: " + sys.argv[1] + ", arg2: " + sys.argv[2])
  ```

  With `value = " arrr11 arrr2"`, `sys.argv[1]` becomes `arrr11` and `sys.argv[2]` becomes `arrr2`.
- This is the **positional-only** parameter style. Named `${var}` placeholders inside the Python source are **not** substituted by the scheduler for this node type — parameters reach the script exclusively via `sys.argv`.

If you need multiple positional arguments, put them all inside one `value` string separated by whitespace; do not create multiple `NoKvVariableExpression` rows.

## Dependency wiring

Standard input/output wiring, identical to other task nodes:

- `outputs.nodeOutputs[]` declares this node's own outputs. Emit a single row with the fully-qualified `data` identifier `${projectIdentifier}.<node_name>`.
- `spec.dependencies[]` carries the actual scheduling edges using `{ type, output, sourceType }` entries.

## Full example

Based on the real sample (`PythonNode`), with the project name replaced by `${projectIdentifier}`.

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "PythonNode",
        "id": "PythonNode",
        "recurrence": "Normal",
        "instanceMode": "T+1",
        "rerunMode": "Allowed",
        "rerunTimes": 0,
        "rerunInterval": 180000,
        "script": {
          "language": "python3",
          "runtime": {
            "command": "PYTHON",
            "cu": "0.5"
          },
          "parameters": [
            {
              "name": "-",
              "scope": "NodeParameter",
              "type": "NoKvVariableExpression",
              "value": " arrr11 arrr2"
            }
          ]
        },
        "trigger": {
          "type": "Scheduler",
          "cron": "00 27 00 * * ?",
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
              "data": "${projectIdentifier}.PythonNode",
              "refTableName": "PythonNode"
            }
          ]
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "PythonNode",
        "depends": [
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

The companion `PythonNode.py`:

```python
import os
import sys

print("hello, arg1: " + sys.argv[1] + ", arg2: " + sys.argv[2])
```

And `dataworks.properties`:

```
spec.runtimeResource.resourceGroup=Serverless_res_group_xxx
```

## Authoring checklist

- [ ] `script.language` is `python3`.
- [ ] `script.runtime.command` is `PYTHON`.
- [ ] The `.py` source is embedded in `script.content` (inline string), not referenced by an external path.
- [ ] If the script reads `sys.argv`, a single `NoKvVariableExpression` entry is declared under `script.parameters[]`, with `name: "-"` and all positional args packed into one whitespace-separated `value` string.
- [ ] `runtimeResource.resourceGroup` points at a Serverless scheduling resource group.
- [ ] `outputs.nodeOutputs[]` includes a row with `data: "${projectIdentifier}.<node_name>"` so downstream nodes can depend on this node.
- [ ] `spec.dependencies[]` uses `{ type, output, sourceType }` entries.

## Reference

- [Python Node](https://help.aliyun.com/zh/dataworks/user-guide/python-node)
