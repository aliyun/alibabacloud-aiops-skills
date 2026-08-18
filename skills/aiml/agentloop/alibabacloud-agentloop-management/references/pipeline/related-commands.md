# Pipeline CLI Commands

These commands were verified against `aliyun-cli-agentloop` 0.7.4 and AgentLoop API `2026-05-20`. Check installed help before execution because later plugin versions may change the contract.

## Contents

- [Command Index](#command-index)
- [Core JSON Shapes](#core-json-shapes)
- [Preview Template](#preview-template)
- [Create Template](#create-template)
- [Manual Run Template](#manual-run-template)
- [Update and Reuse](#update-and-reuse)

```bash
aliyun version
aliyun plugin show --name agentloop
aliyun agentloop <subcommand> --help
```

Every cloud request must also carry the confirmed `--profile`, `--region`, and the session-scoped `--user-agent` required by the root Skill.

## Command Index

| Command | Purpose | Important inputs and safety boundary |
| --- | --- | --- |
| `create-pipeline` | Create a Pipeline. | AgentSpace, name, source, nodes, sink, execute policy, optional client token. `runOnce` may create a run immediately. |
| `get-pipeline` | Read one complete Pipeline. | AgentSpace and exact Pipeline name. Use before update, reuse, or lifecycle mutation. |
| `list-pipelines` | Discover Pipelines. | Optional name/schedule/status filters, pagination token and page size. |
| `update-pipeline` | Replace supplied configuration parts. | Source, nodes, sink, and execute policy are composite objects; a supplied object is a whole replacement. Dry-run the complete intended definition. |
| `delete-pipeline` | Delete one Pipeline resource. | Destructive; exact readback and explicit authorization required. Does not imply Dataset cleanup. |
| `preview-pipeline` | Execute source and node processing without a Dataset sink. | AgentSpace, source, nodes, bounded from/to. No sink parameter. Avoid echoing sensitive rows. |
| `run-pipeline` | Start a manual run. | Pipeline name, bounded from/to, optional business output. No client token and no sink override. Inspect existing runs first. |
| `list-pipeline-runs` | List/filter runs. | Pipeline name or filters, pagination, status, trigger type, and time range as exposed by current help. |
| `get-pipeline-run` | Read authoritative run status/details. | AgentSpace, Pipeline name, and run ID. |
| `get-pipeline-stats` | Read Pipeline statistics. | Pipeline and time/granularity inputs; granularity includes Hour, Day, Week, or Month. |
| `cancel-pipeline-run` | Cancel a run. | Only a `Pending` run is eligible; resolve exact run first. |
| `pause-pipeline` | Pause scheduled execution. | Disruptive; read exact status and obtain authorization. |
| `resume-pipeline` | Resume a paused Pipeline. | Confirm schedule and next-run implications first. |
| `terminate-pipeline` | Terminate Pipeline execution/lifecycle. | Destructive or disruptive; exact readback and explicit authorization required. |

Run states exposed by the CLI include `Pending`, `Running`, `Succeeded`, `Failed`, and `Cancelled`. Trigger types include `Manual`, `Scheduled`, and `RunOnce`. Do not normalize case in request filters without checking help.

## Core JSON Shapes

### Source

```json
{
  "type": "logstore",
  "logstore": {
    "project": "<sls_project>",
    "logstore": "<logstore>",
    "query": "<bounded_source_query>"
  }
}
```

### Nodes

```json
{
  "nodes": [
    {
      "id": "select-fields",
      "type": "project",
      "parameters": {
        "input": "input",
        "output": "output",
        "question": "input",
        "trace_id": "trace_id"
      }
    }
  ]
}
```

### Sink

```json
{
  "type": "dataset",
  "dataset": {
    "agentSpace": "<agent_space>",
    "dataset": "<dataset_name>"
  }
}
```

### Execute policy

Run once over an explicitly bounded source window:

```json
{
  "mode": "runOnce",
  "runOnce": {
    "fromTime": 1785900000,
    "toTime": 1785903600
  }
}
```

For a schedule, inspect current `create-pipeline --help` and confirm `scheduled.fromTime` and `scheduled.interval`; do not infer units or defaults.

## Preview Template

```bash
aliyun agentloop preview-pipeline \
  --agent-space <agent_space> \
  --from-time <from_unix_seconds> \
  --to-time <to_unix_seconds> \
  --source '<source_json>' \
  --pipeline '<nodes_json>'
```

There is deliberately no `--sink`. Use a narrow time window and synthetic/redacted output handling.

## Create Template

```bash
aliyun agentloop create-pipeline \
  --agent-space <agent_space> \
  --pipeline-name <versioned_pipeline_name> \
  --description '<description>' \
  --source '<source_json>' \
  --pipeline '<nodes_json>' \
  --sink '<sink_json>' \
  --execute-policy '<execute_policy_json>' \
  --client-token <stable_uuid> \
  --cli-dry-run
```

Inspect the dry-run body, remove `--cli-dry-run`, and execute only after the source, sink, policy, and field contract are accepted. Immediately follow creation with:

```bash
aliyun agentloop get-pipeline \
  --agent-space <agent_space> \
  --pipeline-name <pipeline_name>

aliyun agentloop list-pipeline-runs \
  --agent-space <agent_space> \
  --pipeline-name <pipeline_name>
```

Do not decide that a manual run is needed from the create response or one immediate empty run list. Poll runs over a bounded observation window; a timeout remains ambiguous.

## Manual Run Template

Use this for a workflow explicitly intended to run manually. Do not use it as the automatic fallback for a newly created `runOnce` Pipeline whose asynchronous run state is absent or ambiguous:

```bash
aliyun agentloop run-pipeline \
  --agent-space <agent_space> \
  --pipeline-name <pipeline_name> \
  --from-time <from_unix_seconds> \
  --to-time <to_unix_seconds> \
  --biz-output '{"dataset":true,"inline":false}'
```

`run-pipeline` cannot change the stored sink and has no client token. Never use it as the way to point an old Pipeline at a new Dataset or as a race-prone fallback after `runOnce` creation.

## Update and Reuse

Before update or clone:

1. `get-pipeline` the exact source resource.
2. Save the complete public source, node, sink, and execute-policy values in memory for the current operation; do not log secrets or raw data.
3. Change only the intended value in the complete copied object.
4. Dry-run the update or create request.
5. Read back the full definition and verify the sink before execution.

Use a new name and `create-pipeline` for retargeting to a new Dataset. Use `update-pipeline` only when in-place replacement is explicitly intended and safe.
