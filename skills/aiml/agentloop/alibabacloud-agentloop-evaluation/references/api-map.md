# AgentLoop evaluation API map

This map is based on `aliyun-cli-agentloop 0.7.0` and AgentLoop API `2026-05-20`. Confirm changed commands with their local `--help` before use.

## Workflow order

1. Verify the AgentSpace with `get-agent-space`.
2. Reuse, create, or update saved evaluators and manage evaluator skills when requested.
3. Validate custom evaluator references with `get-evaluator`.
4. Create an evaluation task. Task creation starts the asynchronous evaluation.
5. Poll `get-evaluation-task` and `list-evaluation-runs`.
6. Fetch the selected run with `get-evaluation-run`.

## Evaluator commands

| Command | Purpose | Important flags |
|---|---|---|
| `list-evaluators` | Discover saved evaluators | `--agent-space`, `--source`, `--type`, `--name`, `--max-results`, `--next-token` |
| `get-evaluator` | Validate a custom reference or inspect a version | `--agent-space`, `--name`, optional `--biz-version` |
| `create-evaluator` | Create a saved evaluator and first version | `--agent-space`, `--name`, `--type`, `--metric-name`, `--biz-version`, optional `--config` |
| `update-evaluator` | Change metadata or add a version | `--agent-space`, `--name`, optional `--biz-version`, `--config` |
| `delete-evaluator` | Delete a saved evaluator version or the whole evaluator | `--agent-space`, `--name`, optional `--biz-version`; omitting the version deletes the whole evaluator; require explicit permission |
| `list-evaluator-skills` | List skills attached to an evaluator | `--agent-space`, `--name` |
| `get-evaluator-skill` | Inspect one evaluator skill | `--agent-space`, `--name`, `--skill-name` |
| `create-evaluator-skill` | Create an evaluator skill | `--agent-space`, `--name`, `--skill-name`, `--files`; preview before mutation |
| `update-evaluator-skill` | Update evaluator-skill metadata or files | `--agent-space`, `--name`, `--skill-name`, optional `--files`; preview before mutation |
| `delete-evaluator-skill` | Delete an evaluator skill | `--agent-space`, `--name`, `--skill-name`; require explicit permission |

The API and workflow wrapper accept saved-evaluator types `LLM`, `AGENT`, and `CODE`. Preserve the requested type and provide its type-specific configuration. A saved custom evaluator uses its name as `evaluatorRef`; a built-in evaluator uses a `Builtin.*` reference. In one task, each reference or inline name must be unique.

Query built-ins explicitly with `list-evaluators --source builtin`. Do not assume aliases are stable. In the tested API revision, the correctness evaluator is `Builtin.agent_correctness`, not `Builtin.correctness`, and its required variables are `input`, `output`, and `expected_output`.

## Task commands

| Command | Purpose | Important flags |
|---|---|---|
| `create-evaluation-task` | Create and start an evaluation | `--agent-space`, `--task-name`, `--task-mode`, `--data-type`, `--data-filter`, `--evaluators`, `--run-strategies`, `--config` |
| `list-evaluation-tasks` | Discover tasks | Optional `--agent-space`, `--channel`, `--status`, `--task-mode`, `--data-type`, `--task-name`, `--max-results`, `--next-token` |
| `get-evaluation-task` | Inspect task state and last run | `--agent-space`, `--task-id` |
| `update-evaluation-task` | Update task fields or terminate a task | `--agent-space`, `--task-id`, optional `--config`, `--data-filter`, `--evaluators`, `--run-strategies`, `--status`, `--tags`; the only user-settable status is currently `Terminated` |
| `delete-evaluation-task` | Delete a task | `--agent-space`, `--task-id`; never automate without explicit permission |

In `aliyun-cli-agentloop 0.7.0`, terminate a task with `update-evaluation-task --status Terminated`. The CLI exposes neither `cancel-evaluation-task` nor `terminate-evaluation-task` as a separate command, and its help does not expose a task-level `Cancelled` transition. Treat task termination as destructive and require explicit permission.

### One-shot evaluation

Use `taskMode=oneshot`, place one sample object under `dataFilter.provided`, and reference one or more existing evaluators. This is the shortest path for evaluator testing.

One-shot creation returns an `eval-temp-*` task ID. These temporary tasks can be fetched with `get-evaluation-task` and produce normal runs and evaluation-detail records, but the tested service excludes them from `list-evaluation-tasks` even when `--task-mode oneshot` is passed. Preserve the returned task ID. The fetched task may show `dataFilter: null` because the inline `provided` sample is not retained in task metadata. The inspected backend cleans temporary task and run records after 24 hours by default; deployment configuration may differ.

### Batch evaluation

Use `taskMode=batch`, a bounded `dataFilter.maxRecords`, and a backfill window in epoch milliseconds. For trace data, the service fills the SLS project and `storeName=logstore-tracing`; set `config.dataScope=trace` for trace-level evaluation.

For dataset data, set `dataType=dataset` and identify the existing dataset with `config.datasetName` or `config.storeName`. The service normalizes `datasetName` to `storeName`; `config.project` is not required. Treat `dataFilter.query` as an SQL condition without `WHERE`, and map evaluator variables directly to dataset columns.

`runStrategies.backfill.startTime` and `endTime` are epoch milliseconds. `continuous.enabled=true` creates ongoing work; the wrapper requires `--allow-continuous`, which must be supplied only after explicit ongoing-cost approval.

## Run commands

| Command | Purpose | Important flags |
|---|---|---|
| `list-evaluation-runs` | List runs for a task | `--agent-space`, `--task-id`, optional `--status`, `--run-type`, `--max-results`, `--next-token` |
| `get-evaluation-run` | Get run details and results | `--agent-space`, `--task-id`, `--run-id` |
| `update-evaluation-run` | Update a run | Inspect local help and require explicit intent before mutation |
| `delete-evaluation-run` | Delete a run | Require explicit permission |

The wrapper recognizes common terminal states such as `Completed`, `Succeeded`, `Failed`, `Cancelled`, and `Terminated`, but always preserves and reports the raw response because deployments may add statuses.

## Result analysis commands

Result analysis is read-only and uses the SLS CLI plugin separately from the AgentLoop plugin.

| Command | Purpose | Important flags |
|---|---|---|
| `agentloop get-agent-space` | Resolve the AgentSpace's SLS project | `--agent-space`; read `slsProject` from the response |
| `sls get-logs-v2` | Query the fixed `evaluation_detail` Logstore | `--project`, `--logstore`, `--from`, `--to`, `--query`, `--line` |

The analyzer issues three bounded SQL queries: an overview, an evaluator breakdown, and low-score case details. SLS `from` and `to` are epoch seconds and form a half-open interval `[from, to)`. The low-score response line limit follows `--max-cases` up to 200. Raw customer content is omitted unless `--include-content` is explicitly supplied.

The SLS plugin is a separate dependency. Check it with `aliyun plugin show --name aliyun-cli-sls`. If it is absent, request approval before installing it. Use the active Aliyun CLI profile; never request or embed raw credentials.

## Global CLI controls

- `--cli-dry-run`: render the request without sending the AgentLoop operation; the CLI may still resolve or refresh credentials.
- `--region`: override endpoint selection region.
- `--endpoint`: override the service endpoint.
- `--log-level DEBUG`: collect request diagnostics without reading credential files.
- `--cli-query '<JMESPath>'`: filter response output after the request succeeds.
