# Check Node - New (CHECK_NODE)

## Overview

- Compute engine: `GENERAL`
- Content format: empty (`script.content` is omitted)
- Extension: `.json` (legacy UI-facing config; the authoritative config lives in `*.spec.json`)

The new Check node polls a target object and returns success only once a user-defined readiness condition is satisfied. It is intended as a scheduling gate: downstream nodes depend on the check node's output and only run after the check passes. Typical use is waiting for a MaxCompute partition to appear before running downstream SQL.

Compared to the legacy [`CHECK`](./CHECK.md) node, `CHECK_NODE` is the current recommended form. It overlaps with [`FTP_CHECK`](./FTP_CHECK.md) and [`OSS_INSPECT`](./OSS_INSPECT.md), which are single-purpose check nodes for FTP and OSS respectively; `CHECK_NODE` is the unified successor and can target MaxCompute partitions, FTP files, OSS / OSS_HDFS / HDFS files, and Kafka→MaxCompute real-time sync tasks. It is distinct from [`DATA_QUALITY_MONITOR`](./DATA_QUALITY_MONITOR.md), which evaluates *data content* quality rules rather than target-object readiness.

## Prerequisites

- The data source being checked (MaxCompute, FTP, OSS, HDFS, or OSS_HDFS) must already be registered in the project.
- Real-time sync checks are only available for Kafka→MaxCompute tasks that have been published to production.
- DataWorks Professional Edition or above.

## Restrictions

- Only Serverless resource groups are supported for execution.
- A single check node can only check one object; multiple dependencies require multiple nodes.
- Check interval: 1–30 minutes; maximum running duration: 24 hours.
- FTP with `Protocol=SFTP` and key-based authentication is not supported.
- Scheduling resources are occupied continuously while the node polls, until the check completes.
- Available in a limited set of regions (specific cities in East China, North China, South China, Southwest China, and Asia Pacific).

## Schema

The check node spec is unusually thin. The runtime selects its behaviour from two pieces of the node spec:

1. `script.runtime.command` — fixed to `CHECK_NODE`.
2. `datasource` — the node-level datasource block that names the data source to probe.

`script.content` is **omitted** (not `""` and not `"{}"`). The detailed check rule (target table, partition expression, polling interval, stop strategy) is not carried inline in the spec sample observed; it is configured alongside the node and persisted by the platform. When authoring a new check node by cloning an existing one, preserve the companion legacy `.<name>.json` file that accompanies the spec — it carries the human-facing rule configuration.

### `datasource`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Name of the registered data source to probe. Must match an existing data source in the project. |
| `type` | string | yes | Data source type, e.g. `odps` for MaxCompute. Other supported values correspond to the prerequisite list above. |

### `script`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `runtime.command` | string | yes | Must be `CHECK_NODE`. |
| `runtime.cu` | string | optional | Small allocation (e.g. `"0.25"`) is sufficient; the node performs polling only. |
| `content` | — | — | **Omit.** Do not set to `""` or `"{}"`. |

### Legacy UI config (`*.json`) — reference only

The `.json` file that accompanies the spec in exported samples records the UI-facing rule. Observed fields (not exhaustive; the runtime reads these, not the spec):

| Field | Observed value | Meaning |
|-------|----------------|---------|
| `checkType` | `datasource` | Probe mode: check an object in a registered data source. |
| `dataSourceType` | `MaxCompute` | Engine family. |
| `dataSource` | `<project-name>` | Data source name (matches `datasource.name` in the spec). |
| `tableGuid` | `odps.<project>.<table>` | Fully-qualified table identifier. |
| `table` | `<table_name>` | Short table name. |
| `partitions[]` | `[{name, value}]` | Partition key/value pairs; values support scheduling placeholders such as `${bizdate}`. |
| `condition.kind` | `PARTITION_EXISTS` | Readiness rule. `PARTITION_EXISTS` waits for the specified partition to appear. |
| `stopStrategy.kind` | `END_AT_LOOPS` | Termination policy. |
| `stopStrategy.config.intervalInMinute` | `5` | Polling interval in minutes. |

These fields are documented from the observed sample and may evolve; they are not part of the minimal spec contract.

## Full Example

A daily check node `checknode1` that waits for a partition on a MaxCompute table in the data source `${projectIdentifier}`.

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "checknode1",
        "id": "checknode1",
        "recurrence": "Normal",
        "timeout": 0,
        "timeoutUnit": "HOURS",
        "instanceMode": "T+1",
        "rerunMode": "Allowed",
        "datasource": {
          "name": "${spec.datasource.name}",
          "type": "odps"
        },
        "script": {
          "runtime": {
            "command": "CHECK_NODE",
            "cu": "0.25"
          }
        },
        "trigger": {
          "type": "Scheduler",
          "cron": "00 28 00 * * ?",
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
              "sourceType": "System",
              "refTableName": "checknode1"
            },
            {
              "sourceType": "System",
              "data": "${projectIdentifier}.checknode1",
              "refTableName": "checknode1"
            }
          ]
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "checknode1",
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

## Authoring Checklist

Before submitting a CHECK_NODE, verify:

- [ ] `script.runtime.command` is `CHECK_NODE`.
- [ ] `script.content` is **omitted** (not set to `""` or `"{}"`).
- [ ] A node-level `datasource` block with `name` and `type` is present, and the named data source exists in the project.
- [ ] The `runtimeResource.resourceGroup` points to a Serverless resource group.
- [ ] The accompanying `.json` file (if authoring from a template) has a `condition`/`partitions`/`stopStrategy` configuration consistent with the target object; scheduling placeholders such as `${bizdate}` are used instead of hard-coded dates.
- [ ] Downstream nodes depend on this node's output (e.g. `${projectIdentifier}.<check_node_name>`) so they are gated by the check result.
- [ ] Only one target object is being checked per node.

## Reference

- [Check Node](https://help.aliyun.com/zh/dataworks/user-guide/check-node)
