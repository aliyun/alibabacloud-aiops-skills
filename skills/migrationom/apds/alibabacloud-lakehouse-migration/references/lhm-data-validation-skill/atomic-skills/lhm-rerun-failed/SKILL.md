---
name: lhm-rerun-failed
version: 1.0.0
description: Reruns the failed tasks in an LHM data validation batch and returns the new batch ID.
---

# lhm-rerun-failed

For a specified LHM data validation batch, filters by failure type and reruns, returning a new `batch_id`.

## Steps

1. Read the command-line arguments: original batch ID, failure type, and region.
2. Before execution, run `lhm-common check --profile data-validation` first to confirm the preconditions are met.
3. Call `build_client_from_config()` to build the LHM client (the network layer goes through the aliyun CLI, read from data_validation_config.yaml, with CLI arguments taking precedence).
4. Redirect `sys.stdout` to `io.StringIO`, call `rerun_failed()` to get the new batch ID, then restore stdout.
5. Output JSON: `{"ok": true, "new_batch_id": <int>}`.

## Pitfalls

- **stdout polluted by prints**: `rerun_failed()` prints `[一键重跑] 新 batchId=...` internally; stdout must be redirected, otherwise JSON parsing fails.
- **fail_type values**: only 0 (failed only), 1 (failed + not passed), and 2 (failed + terminated) are supported; other values trigger an argparse error.
- **Using task_id instead of batch_id**: the rerun interface requires the original `batch_id`; do not pass `task_id` by mistake.
- **Credentials**: resolved through the default credential chain (environment variables / RAM Role / `~/.alibabacloud/credentials`); the script never accepts AK/SK as command-line arguments.

## Verification

- `python -m py_compile atomic-skills/lhm-rerun-failed/scripts/run.py` passes.
- On success stdout is valid JSON, e.g., `{"ok": true, "new_batch_id": 12346}`.
- On failure stderr outputs `{"ok": false, "error": "..."}` and exit(1).

## Input/Output Examples

```bash
python atomic-skills/lhm-rerun-failed/scripts/run.py \
  --batch-id 12345 \
  --fail-type 1 \
  --region hangzhou
```

Output:

```json
{
  "ok": true,
  "new_batch_id": 12346
}
```

Rerun failures only:

```bash
python atomic-skills/lhm-rerun-failed/scripts/run.py \
  --batch-id 12345 \
  --fail-type 0 \
  --region hangzhou
```
