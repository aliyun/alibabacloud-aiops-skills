# Availability checks

Check only the model/resource scope supplied by the user or context, under the confirmed CLI profile, region and endpoint. Reuse sufficient checks from the same task and identity; do not probe unrelated models to resolve a missing target.

## Source Model

For a known Project/Logstore, run:

```bash
python3 scripts/semantic-model/model_qa.py source-model readiness \
  --region "<region>" --project "<project>" --logstore "<logstore>"
```

Require `available: true`; a successful command exit alone is insufficient. `reason` explains an unavailable result, and `recommendation`, when present, is only a possible follow-up. For Project-only scope, require `aliyun sls source-model status` to confirm generation completion and `source-model query` to read definitions successfully. Use the same profile, region and endpoint for both reads.

## Context Model

Use `aliyun sls context-model query` for the selected model with this small definition probe:

```text
.umodel | where kind in ('log_set', 'runbook_set', 'metric_set') | project kind | limit 1
```

For model-query probes, require exit code 0, `responseStatus.result=Success`, `responseStatus.level=Info` and a valid, nonempty semantic row. Treat empty, failed or unfinished checks as unavailable/unconfirmed. Model metadata or CLI command availability alone does not confirm readable definitions.

## Result handling

| Result | Next step |
| --- | --- |
| Available | Read [the guide](guide.md). Skip troubleshooting; validate task-specific definition coverage during use. |
| Unavailable/unconfirmed; semantic models are optional | Continue the original task with independently verified definitions. Do not load the guide or troubleshooting, or issue a separate availability report. |
| Unavailable/unconfirmed; semantic models are required | Report the reason or request missing model information, then read [troubleshooting](troubleshooting.md) as needed. |

Treat semantic models as required when the user requires them or the task cannot proceed without them. Do not automatically create or regenerate models.
