# SSH Remote Execution (SSH)

## Overview

- Compute engine: `GENERAL`
- Content format: shell
- Extension: `.ssh.sh`
- Description: Run a shell script on a remote host over an SSH data-source connection

The SSH node is structurally very similar to `DIDE_SHELL`: the script body is a Bash file embedded into `script.content`. The key difference is **where** the script runs. Instead of executing on the scheduling resource group itself, the scheduler opens an SSH session to a remote host (declared via a data source) and runs the script there. The scheduling resource group only drives the session and collects logs.

Use this node for periodic jobs on ECS or other remote machines reachable over SSH.

## Schema

This section documents only the fields that differ from a plain shell node. Everything else (`trigger`, `inputs`, `outputs`, `dependencies`, `runtimeResource`) follows the standard task-node shape.

### `datasource` block (required — SSH-specific)

The remote host is not a free-form IP/port literal inside the node. It is resolved via a **named data source** of type `ssh`. The data source stores the host, port, credentials, and any SSH-specific options; the node only references it by name.

```json
"datasource": {
  "name": "${spec.datasource.name}",
  "type": "ssh"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `datasource.name` | yes | The identifier of a pre-registered SSH data source in the workspace. The data source must already exist and be reachable from the chosen resource group's network. In the sample this is templated as `${spec.datasource.name}` and supplied from `dataworks.properties` (value `ssh_connect`). |
| `datasource.type` | yes | Must be `"ssh"`. |

There is **no inline `connection` / `host` / `port` / `user` / `privateKey` block** on the node spec — all of that lives on the data source. This is the single most important difference from a `DIDE_SHELL` node.

### `script` block

| Field | Description |
|-------|-------------|
| `script.language` | `shell-script` in the sample (same as a plain shell node). |
| `script.runtime.command` | Must be `SSH`. Immutable once the node is created. |
| `script.runtime.cu` | CU allocation for the driver container on the resource group. The sample uses `"0.25"` — the resource group only drives the SSH session, so a small allocation is sufficient. |
| `script.content` | The full shell source to execute on the remote host, embedded as a string (built from the companion `.ssh.sh` file). |
| `script.parameters[]` | Named parameters made available as shell variables. See "Parameter substitution" below. |

### `runtimeResource`

`runtimeResource.resourceGroup` still points at the **local** Serverless scheduling resource group that will initiate the SSH session. This resource group must have network connectivity to the SSH data source's host.

## Parameter substitution

SSH nodes use **named** parameters that are substituted into `script.content` as `${name}` placeholders before the script is shipped to the remote host. This is different from the Python node's positional `NoKvVariableExpression` style.

From the sample:

```json
"parameters": [
  {
    "artifactType": "Variable",
    "name": "myDate",
    "scope": "NodeParameter",
    "type": "System",
    "value": "$[yyyymmdd]"
  }
]
```

And the companion `sshnode1.ssh.sh`:

```bash
#!/bin/bash
echo ${myDate} >/tmp/sshnode.log
cat /tmp/sshnode.log
```

What this shows:

- `name: "myDate"` is the placeholder key. Any `${myDate}` inside `script.content` is replaced at runtime with the resolved value.
- `type: "System"` combined with a `$[yyyymmdd]` value makes this a **scheduling system variable** — the engine substitutes the current business date formatted as `yyyymmdd` at run time. Other date-format expressions under `$[...]` follow the same rule.
- `scope: "NodeParameter"` scopes the variable to this node.
- Unlike the Python node, you can declare multiple named parameters and reference each one independently inside the script body.

## Dependency wiring

Standard input/output wiring, identical to other task nodes. The sample:

- Consumes the workflow root as `${projectIdentifier}_root` via a `Normal` dependency in `spec.dependencies[]`.
- Publishes its own output as `${projectIdentifier}.sshnode1` under `outputs.nodeOutputs[]`.

## Full example

Based on the real sample (`sshnode1`), with the project name replaced by `${projectIdentifier}`.

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "sshnode1",
        "recurrence": "Normal",
        "instanceMode": "T+1",
        "rerunMode": "Allowed",
        "rerunTimes": 0,
        "rerunInterval": 180000,
        "datasource": {
          "name": "${spec.datasource.name}",
          "type": "ssh"
        },
        "script": {
          "language": "shell-script",
          "runtime": {
            "command": "SSH",
            "cu": "0.25"
          },
          "parameters": [
            {
              "artifactType": "Variable",
              "name": "myDate",
              "scope": "NodeParameter",
              "type": "System",
              "value": "$[yyyymmdd]"
            }
          ]
        },
        "trigger": {
          "type": "Scheduler",
          "cron": "00 20 00 * * ?",
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
              "data": "${projectIdentifier}.sshnode1",
              "refTableName": "sshnode1"
            }
          ]
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "sshnode1",
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

The companion `sshnode1.ssh.sh`:

```bash
#!/bin/bash
echo ${myDate} >/tmp/sshnode.log
cat /tmp/sshnode.log
```

And `dataworks.properties`:

```
spec.runtimeResource.resourceGroup=group_xxx
spec.datasource.name=ssh_connect
```

## Authoring checklist

- [ ] `script.runtime.command` is `SSH`.
- [ ] A top-level `datasource` block is present with `type: "ssh"` and `name` set to a pre-registered SSH data source.
- [ ] No inline host / port / credential fields are added to the node spec — the data source owns all connection details.
- [ ] The shell body is embedded in `script.content` from the companion `.ssh.sh` file.
- [ ] Each `${name}` placeholder in `script.content` is declared in `script.parameters[]` with the appropriate `type` (`System` for scheduling variables like `$[yyyymmdd]`, otherwise a literal or upstream-passthrough type).
- [ ] `runtimeResource.resourceGroup` points at a Serverless scheduling resource group that has network connectivity to the SSH data source's host.
- [ ] `outputs.nodeOutputs[]` includes a row with `data: "${projectIdentifier}.<node_name>"` so downstream nodes can depend on this node.
- [ ] `spec.dependencies[]` uses `{ type, output, sourceType }` entries.

## Reference

- [SSH Node](https://help.aliyun.com/zh/dataworks/user-guide/ssh-node)
