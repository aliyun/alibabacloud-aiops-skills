---
name: lhm-report-summary
version: 1.0.0
description: Gets the overview statistics of an LHM data validation batch.
---

# lhm-report-summary

Gets the overview statistics of a specified LHM data validation batch, including task name, validation template, table-level pass/fail counts, pass rate, difference rate, etc.

## Steps

1. Parse the command-line arguments (batch-id, region, etc.).
2. Call `build_client_from_config()` to build the LHM client (the network layer goes through the aliyun CLI, read from data_validation_config.yaml, with CLI arguments taking precedence).
3. Call `summarize_batch()` to get the batch overview; redirect `sys.stdout` to capture the log prints inside the common functions and avoid polluting stdout.
4. Add `"ok": true` to the returned dict and output the JSON to stdout.
5. On any exception output JSON to stderr and exit(1).

## Pitfalls

- The batch must have finished executing (exec_status=4), otherwise `GetDataCheckReportOverview` may return incomplete data.
- `--batch-id` is a required argument; missing it triggers an argparse error.
- Credentials are resolved through the default credential chain (environment variables / RAM Role / `~/.alibabacloud/credentials`); the script never accepts AK/SK as command-line arguments.
- The common functions may use `print` internally for logs; the script captures them via `io.StringIO` and writes them to stderr, so stdout contains only the final JSON.

## Verification

- For a valid batch, stdout should output something like:

  ```json
  {
    "ok": true,
    "task_name": "逐表数据量校验",
    "template": "MIX",
    "total_tables": 13,
    "pass_tables": 11,
    "fail_tables": 2,
    "pass_rate": "84.62%",
    "column_pass_rate": 0.95,
    "diff_rate": "15.38%",
    "exec_status": 4,
    "check_result": 2
  }
  ```

- Running `python -m py_compile atomic-skills/lhm-report-summary/scripts/run.py` produces no syntax errors.

## Input/Output Examples

```bash
python atomic-skills/lhm-report-summary/scripts/run.py \
  --batch-id 67890 \
  --region hangzhou
```

Successful output:

```json
{"ok": true, "task_name": "逐表数据量校验", "template": "MIX", "total_tables": 13, "pass_tables": 11, "fail_tables": 2, "pass_rate": "84.62%", "column_pass_rate": 0.95, "diff_rate": "15.38%", "exec_status": 4, "check_result": 2}
```
