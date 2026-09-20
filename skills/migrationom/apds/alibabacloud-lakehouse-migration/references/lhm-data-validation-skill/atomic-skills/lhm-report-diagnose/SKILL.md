---
name: lhm-report-diagnose
version: 1.0.0
description: Diagnoses the failed tables and fields in an LHM data validation batch and outputs structured diagnosis results.
---

# lhm-report-diagnose

Diagnoses the details of failed tables and fields in a specified LHM data validation batch. Supports two output forms: grouped by field or a flat list.

## Steps

1. Read the command-line arguments: batch ID, output grouping mode, and region.
2. Before execution, run `lhm-common check --profile data-validation` first to confirm the preconditions are met.
3. Call `build_client_from_config()` to build the LHM client (the network layer goes through the aliyun CLI, read from data_validation_config.yaml, with CLI arguments taking precedence).
4. Redirect `sys.stdout` to `io.StringIO`, call `diagnose_failed()` to obtain the diagnosis results, then restore stdout.
5. Output JSON: `{"ok": true, "diagnosis": [...] or {...}}`.

## Pitfalls

- **Not redirecting stdout pollutes the JSON**: although `diagnose_failed()` does not print directly, stdout must be redirected to strictly guarantee that external systems can parse the output.
- **Confusing batch_id with task_id**: the diagnosis interface must use `batch_id`; do not pass `task_id`.
- **Credentials**: resolved through the default credential chain (environment variables / RAM Role / `~/.alibabacloud/credentials`); the script never accepts AK/SK as command-line arguments.
- **Semantics of group_by_field**: defaults to `False`, returning a flat list; when set to `True`, results are grouped by table → field, which is convenient for aggregating and viewing differences.

## Verification

- `python -m py_compile atomic-skills/lhm-report-diagnose/scripts/run.py` passes.
- After running the script, stdout is valid JSON and contains JSON content only.
- When credentials are missing or the `batch_id` does not exist, stderr outputs `{"ok": false, "error": "..."}` and exit(1).

## Input/Output Examples

```bash
python atomic-skills/lhm-report-diagnose/scripts/run.py \
  --batch-id 12345 \
  --region hangzhou
```

Output (flat list):

```json
{
  "ok": true,
  "diagnosis": [
    {
      "table": "src_db.orders",
      "type": "STEP",
      "detail": {
        "src_count": 1000,
        "dst_count": 999,
        "is_consistent": 0
      }
    }
  ]
}
```

Grouped by field:

```bash
python atomic-skills/lhm-report-diagnose/scripts/run.py \
  --batch-id 12345 \
  --group-by-field \
  --region hangzhou
```

Output:

```json
{
  "ok": true,
  "diagnosis": {
    "src_db.orders": {
      "summary": {"total": 1, "pass": 0, "fail": 1},
      "steps": [...],
      "columns": {
        "amount": {"pass": 0, "fail": 1, "metrics": [...]}
      }
    }
  }
}
```
