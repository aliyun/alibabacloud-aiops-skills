# Workflow specification

Use JSON so nested evaluator and task parameters do not need shell escaping. Start from `examples/oneshot-example.json`, `examples/batch-trace-example.json`, or `examples/batch-dataset-example.json` in the `examples/` subdirectory.

## Top-level fields

| Field | Required | Meaning |
|---|---:|---|
| `agent_space` | yes | Target AgentSpace name |
| `region` | no | Aliyun endpoint-selection region |
| `endpoint` | no | Explicit AgentLoop service endpoint |
| `evaluator_actions` | no | Explicit saved-evaluator create/update operations |
| `task` | yes | Evaluation task definition |

Do not store credentials in this file. The wrapper uses the active Aliyun CLI profile.

## Evaluator actions

Omit this section when reusing built-in or existing evaluators. Each action is explicit:

```json
{
  "evaluator_actions": [
    {
      "action": "create",
      "name": "answer-correctness",
      "type": "AGENT",
      "metric_name": "correctness",
      "biz_version": "v1",
      "description": "Judge answer correctness",
      "config": {
        "prompt": "Judge {{input}} and {{output}} and return JSON.",
        "variables": ["input", "output"]
      }
    }
  ]
}
```

The workflow wrapper accepts the API-supported saved-evaluator types `AGENT`, `LLM`, and `CODE`. Preserve the user's requested type and provide the corresponding type-specific `config`; never silently substitute another type.

Use `action: update` with `name` and a new `biz_version` to add a version. Use `action: reuse` or omit the action object when no evaluator mutation is needed.

## Task fields

The wrapper accepts readable snake_case and converts known fields to the plugin's camelCase payload.

Only the documented wrapper aliases are converted. The raw `task.config` map is passed through unchanged, so use exact service keys such as `datasetName`, `storeName`, and `dataScope`, not snake_case variants.

| Field | Required | Meaning |
|---|---:|---|
| `name` | no | Task name; generated when absent |
| `mode` | no | `oneshot` for provided samples; otherwise `batch` |
| `data_type` | no | Usually `trace` or `dataset`; defaults to `trace` |
| `data_filter` | yes | `provided` sample or bounded batch query |
| `evaluator_refs` or `evaluators` | yes | Simplified references or raw evaluator objects |
| `config` | batch-dependent | Data-source configuration |
| `window` | batch-dependent | Readable ISO timestamps converted to backfill milliseconds |
| `run_strategies` | advanced | Raw strategy object; mutually exclusive with `window` |
| `channel`, `description`, `tags` | no | Task metadata |

For one-shot runs, always retain the returned `eval-temp-*` task ID. Temporary tasks may not appear in task-list APIs even though their run and evaluation-detail records are present; query them by task ID. In the inspected backend, temporary task and run records are cleaned after 24 hours by default, though deployment configuration may differ. Inspect or export results promptly.

### Dataset batches

For `data_type: dataset`, set `config.datasetName` or `config.storeName` to the existing AgentLoop dataset name. Prefer `datasetName` in specifications for readability; the service normalizes it to `storeName`. Dataset tasks do not require `config.project`.

`data_filter.query` is an optional SQL condition without the `WHERE` keyword, for example `category = 'golden'`. The service combines it with any evaluator-level query, applies `samplingRate`, and appends the `maxRecords` limit. Keep `max_records` and a bounded backfill `window` in normal batch workflows.

Map evaluator variables directly to dataset column names. For a dataset with `input`, `output`, and `expected_output` columns, use those exact names rather than `trace.input` or other trace paths. See `examples/batch-dataset-example.json` for a complete specification.

### Simplified evaluator references

```json
{
  "evaluator_refs": [
    {
      "ref": "Builtin.agent_correctness",
      "result_name": "correctness",
      "result_type": "score",
      "variable_mapping": {
        "input": "input",
        "output": "output",
        "expected_output": "expected_output"
      }
    }
  ]
}
```

`ref` becomes `evaluatorRef`. Omit `version` to use the evaluator's latest version. `variable_mapping` keys are variables declared by the evaluator; values are fields or paths in the evaluation data.

Built-in names and required variables can change between service revisions. Run `discover` and use the returned exact `Builtin.*` name. In API `2026-05-20`, correctness is `Builtin.agent_correctness` and requires `input`, `output`, and `expected_output`.

Use raw `evaluators` for inline evaluators or fields not covered by the simplified form. Inline evaluators must provide `name`, `resultName`, `resultType`, `config`, and `variableMapping`.

### Time window

Prefer timezone-bearing ISO-8601 values:

```json
{
  "window": {
    "start": "2026-07-14T09:00:00+08:00",
    "end": "2026-07-14T10:00:00+08:00"
  }
}
```

Epoch milliseconds are also accepted. Naive timestamps without a timezone are rejected.

## Commands

Preview safely:

```bash
python3 scripts/agentloop_eval.py run --spec evaluation.json
```

Execute and wait:

```bash
python3 scripts/agentloop_eval.py run --spec evaluation.json --execute --output result.json
```

Allow a deliberately unbounded batch only after explicit agreement:

```bash
python3 scripts/agentloop_eval.py run --spec evaluation.json --execute --allow-unbounded
```

Allow continuous evaluation only after explicit ongoing-cost agreement. Pass the flag for preview and execution:

```bash
python3 scripts/agentloop_eval.py run --spec continuous.json --allow-continuous
python3 scripts/agentloop_eval.py run --spec continuous.json --allow-continuous --execute
```
