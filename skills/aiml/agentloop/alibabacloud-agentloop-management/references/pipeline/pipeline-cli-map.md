# AgentLoop Pipeline CLI map

This reference records the locally verified Pipeline surface of the Alibaba Cloud
CLI plugin. Prefer the installed CLI help and dry-run payload over documentation
examples when field names differ.

## Verified toolchain

- Aliyun CLI: `3.3.23`
- Plugin: `aliyun-cli-agentloop 0.7.4`
- AgentLoop API: `2026-05-20`
- Product command: `aliyun agentloop`

Re-check these values before relying on this map after a plugin update:

```bash
aliyun version
aliyun plugin show --name aliyun-cli-agentloop
aliyun agentloop version
```

## Pipeline commands

| Category | Command | Purpose | Important parameters |
|---|---|---|---|
| Resource | `create-pipeline` | Create a Pipeline | `--agent-space`, `--pipeline-name`, `--source`, `--pipeline`, `--sink`, `--execute-policy`, optional `--client-token`; RunOnce mode also starts one run immediately |
| Resource | `get-pipeline` | Get one Pipeline | `--agent-space`, `--pipeline-name` |
| Resource | `list-pipelines` | List Pipelines | `--agent-space`, optional name, schedule type/status, pagination |
| Resource | `update-pipeline` | Replace supplied configuration blocks | `--agent-space`, `--pipeline-name`; supplied source/pipeline/sink/policy blocks are replaced as a whole |
| Resource | `delete-pipeline` | Delete a Pipeline | `--agent-space`, `--pipeline-name` |
| Schedule | `pause-pipeline` | Pause scheduling | `--agent-space`, `--pipeline-name`, optional `--reason` |
| Schedule | `resume-pipeline` | Resume scheduling | `--agent-space`, `--pipeline-name` |
| Schedule | `terminate-pipeline` | Terminate a Pipeline | `--agent-space`, `--pipeline-name`, optional `--reason` |
| Preview | `preview-pipeline` | Trial-run source and nodes without creating a resource | `--agent-space`, `--source`, `--pipeline`, `--from-time`, `--to-time`; prefer the wrapper `preview` subcommand, which derives `--source` and `--pipeline` from the spec file |
| Run | `run-pipeline` | Trigger a manual run | `--agent-space`, `--pipeline-name`, optional time window and `--biz-output`; a window already covered by a run returns `409 ResourceExist` |
| Run | `cancel-pipeline-run` | Cancel a pending run | `--agent-space`, `--pipeline-name`, `--run-id`; only `Pending` can be cancelled |
| Inspection | `get-pipeline-run` | Get one run | `--agent-space`, `--pipeline-name`, `--run-id` |
| Inspection | `list-pipeline-runs` | List run history | optional time range, status, trigger type, pagination; max 200 |
| Inspection | `get-pipeline-stats` | Get run statistics | optional time range and `Hour`, `Day`, `Week`, or `Month` granularity |

Read-only commands are `get-pipeline`, `list-pipelines`, `get-pipeline-run`,
`list-pipeline-runs`, and `get-pipeline-stats`. Treat every other command as a
cloud mutation or a potentially billable processing action. Although
`preview-pipeline` does not create a Pipeline resource, it reads source data and
executes nodes, so bound its time window and account for AI-node cost.

## CLI request model

The locally verified `create-pipeline` body has four configuration blocks:

```json
{
  "source": {
    "type": "logstore",
    "logstore": {
      "project": "example-project",
      "logstore": "example-logstore",
      "query": "*"
    }
  },
  "pipeline": {
    "nodes": [
      {
        "id": "select-fields",
        "type": "project",
        "parameters": {
          "question": "user_query"
        }
      }
    ]
  },
  "sink": {
    "type": "dataset",
    "dataset": {
      "agentSpace": "example-agent-space",
      "dataset": "example_dataset"
    }
  },
  "executePolicy": {
    "mode": "runOnce",
    "runOnce": {
      "fromTime": 1785312000,
      "toTime": 1785315600
    }
  }
}
```

Important CLI 0.7.4 details:

- Pipeline names must contain 3 to 63 lowercase letters, digits, or hyphens.
- Source type sent to the API is `logstore`.
- Sink type currently exposed by the CLI is `dataset`.
- The CLI uses `sink.dataset.agentSpace`, not the `workspace` spelling shown in
  some product-documentation examples.
- Time windows use Unix seconds, not milliseconds.
- Execute-policy modes sent to the API are `runOnce` and `scheduled`.
- `update-pipeline` replaces each supplied object block as a whole.
- Node IDs must be unique and nodes execute in array order.

Use `--cli-dry-run true` on create, update, lifecycle, and run commands before
sending a mutation. `preview-pipeline` is a service operation that processes a
small sample; it is not the same as CLI dry-run.

## Processing node types

The local Layer 1 Node reference documents 14 ordered node types:

| Category | Node type | Function |
|---|---|---|
| Basic | `project` | Select and rename fields |
| Basic | `extend` | Compute or overwrite fields with expressions |
| Basic | `where` | Filter rows with a boolean expression |
| Basic | `limit` | Limit output rows |
| Assembly | `make-instance` | Aggregate event rows into sample instances |
| Cleaning | `dedup-exact` | Exact text deduplication |
| Cleaning | `dedup-fuzzy` | Near-duplicate text removal |
| Cleaning | `dedup-semantic` | Embedding-based semantic deduplication |
| Features | `embedding` | Generate a vector column |
| Features | `doc-stats` | Generate document statistics |
| Sampling | `semantic-cluster` | Assign semantic cluster IDs |
| Sampling | `sample` | Sample by ratio or count, optionally by group |
| AI | `llm-call` | Invoke an LLM for evaluation, labeling, or synthesis |
| AI | `agentic-call` | Invoke a configured digital employee/agent |

The CLI intentionally models `nodes[].parameters` as a free-form object. It does
not validate or enumerate node-specific keys in `--help`; validate JSON
parameters against `references/pipeline/nodes/`, use `references/pipeline/operators/`
only for SPL-layer semantics and troubleshooting, and preview with
a bounded time window before creation.

When a JSON payload is passed inline on the command line, quote it from a file
(`--pipeline "$(cat nodes.json)"`) rather than as a single-quoted literal. A
shell-mangled payload is reported as `Error: unknown field: {"nodes":`, which
looks like an API field error but is purely local quoting damage. The wrapper is
not affected: it passes each JSON blob as one argv element without a shell.

## Status and filter values

- Pipeline schedule status: `None`, `Active`, `Paused`, `Terminated`
- Schedule type: `RunOnce`, `Scheduled`
- Run status: `Pending`, `Running`, `Succeeded`, `Failed`, `Cancelled`
- Trigger type: `Manual`, `Scheduled`, `RunOnce`
- Statistics granularity: `Hour`, `Day`, `Week`, `Month`

## Output shape notes

- `list-pipeline-runs` returns the run list in the top-level `runs` field. Use
  `--cli-query 'runs'` or a query rooted at `runs[...]`, not `pipelineRuns`.
- The Aliyun CLI may return `null` for a wrong `--cli-query` path instead of an
  error. Treat `null` from a query as a possible query-shape mistake; inspect the
  raw response before concluding that no Pipeline runs exist.

## Documentation compatibility note

The installed CLI plugin and reference files describe the same four-part model,
but examples can use different casing, legacy names, or SPL-layer syntax. Build
top-level requests from the installed CLI schema, build `pipeline.nodes[]` from
`references/pipeline/nodes/`, and use `references/pipeline/operators/` primarily
for SPL semantics and operational troubleshooting.

## Backend template translation

Backend predefined-pipeline templates (for example the `pipeline-api.json` shape
used by internal generators such as `xiaolan-pipeline-gen`) are NOT the CLI
`create-pipeline` payload. Translate these fields before feeding the wrapper:

| Field | Backend template | CLI / this skill spec |
|---|---|---|
| `source.type` | `logstore` | spec accepts `LogStore` or `logstore`; wrapper emits `logstore` |
| source body | `parameters.query` | `logstore.{project,logstore,query}` |
| `where` node param | `condition` | `filter` |
| `executePolicy.mode` | `incremental` + batchSize/timeRange | spec `run_once` / `scheduled`; wrapper emits `runOnce` / `scheduled` |
| `sink` | `type: dataset` with no body | spec `dataset.{agent_space,name}` -> wrapper emits `dataset.{agentSpace,dataset}` |
| time unit | mixed | Unix seconds or timezone ISO-8601; milliseconds rejected |

Node-type notes when porting backend templates:

- There is no `sort` node. For time-ordered aggregation use `make-instance` with
  `join(col, sep, order_by)` or `first(col, order_by)` and an order key such as
  `startTime`; see `references/pipeline/operators/make-instance.md`.
- `ai-gen` is rejected (use `llm-call`); `make-conversation` is rejected.
