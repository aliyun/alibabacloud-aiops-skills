---
name: lhm-report-download
version: 1.0.0
description: Triggers and downloads an LHM data validation report and returns the OSS download link.
---

# lhm-report-download

Triggers report generation for a specified LHM data validation batch, polls the report generation status, and returns the OSS download link when complete.

## Steps

1. Parse the command-line arguments (batch-id, region, timeout-sec, interval-sec, etc.).
2. Call `build_client_from_config()` to build the LHM client (the network layer goes through the aliyun CLI, read from data_validation_config.yaml, with CLI arguments taking precedence).
3. Call `download_report()`: first confirm the batch has completed, then trigger report generation, poll the report status, and finally download and return the OSS URL.
4. Redirect `sys.stdout` to capture the log prints inside the common functions and avoid polluting stdout.
5. Output `{"ok": true, "oss_url": "..."}` to stdout; on any exception output JSON to stderr and exit(1).

## Pitfalls

- The batch must have finished executing (exec_status=4), otherwise `download_report()` raises an exception.
- Report generation can take a long time; the default is `--timeout-sec 300` seconds. Increase it for batch checks on large tables.
- `--batch-id` is a required argument; missing it triggers an argparse error.
- Credentials are resolved through the default credential chain (environment variables / RAM Role / `~/.alibabacloud/credentials`); the script never accepts AK/SK as command-line arguments.
- The common functions use `print` internally for logs; the script captures them via `io.StringIO` and writes them to stderr, so stdout contains only the final JSON.

## Verification

- For a valid batch, stdout should output something like:

  ```json
  {"ok": true, "oss_url": "https://xxx.oss-cn-hangzhou.aliyuncs.com/xxx.xlsx"}
  ```

- Running `python -m py_compile atomic-skills/lhm-report-download/scripts/run.py` produces no syntax errors.

## Input/Output Examples

```bash
python atomic-skills/lhm-report-download/scripts/run.py \
  --batch-id 67890 \
  --region hangzhou \
  --timeout-sec 300 \
  --interval-sec 3
```

Successful output:

```json
{"ok": true, "oss_url": "https://xxx.oss-cn-hangzhou.aliyuncs.com/xxx.xlsx"}
```
