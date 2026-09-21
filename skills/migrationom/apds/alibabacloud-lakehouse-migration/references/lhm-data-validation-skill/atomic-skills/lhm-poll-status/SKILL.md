---
name: lhm-poll-status
version: 1.0.0
description: Polls the execution status of an LHM data validation task until the task reaches a terminal state or times out.
---

# lhm-poll-status

Polls the execution status of an LHM data validation task until the task reaches a terminal state (STOPPED / FAILED / FINISHED) or the timeout is reached.

## Steps

1. Parse the command-line arguments (task-id, batch-id, region, timeout-sec, interval-sec, etc.).
2. Call `build_client_from_config()` to build the LHM client (the network layer goes through the aliyun CLI, read from data_validation_config.yaml, with CLI arguments taking precedence).
3. Call `poll_exec_status()` to poll the task status; redirect `sys.stdout` to capture the log prints inside the common functions and avoid polluting stdout.
4. If the status reaches a terminal state, output `{"ok": true, "exec_status": <int>, "exec_status_text": "..."}`.
5. If it times out, output `{"ok": false, "exec_status": -1, "reason": "timeout"}` and exit(1).

## Pitfalls

- `--task-id` and `--batch-id` must be provided together; missing either one causes the API query to fail.
- Long-running batch tasks may require increasing `--timeout-sec`; the default of 1800 seconds may not be enough.
- Credential precedence: command-line arguments > data_validation_config.yaml (~/.lhm/data_validation_config.yaml) > environment variables.
- The common functions use `print` internally for polling logs; the script captures them via `io.StringIO` and writes them to stderr, so stdout contains only the final JSON.

## Verification

- For a normally completed batch, stdout should output something like:

  ```json
  {"ok": true, "exec_status": 4, "exec_status_text": "FINISHED"}
  ```

- For the timeout scenario, stderr should output:

  ```json
  {"ok": false, "exec_status": -1, "reason": "timeout"}
  ```

- Running `python -m py_compile atomic-skills/lhm-poll-status/scripts/run.py` produces no syntax errors.

## Input/Output Examples

```bash
python atomic-skills/lhm-poll-status/scripts/run.py \
  --task-id 12345 \
  --batch-id 67890 \
  --region hangzhou \
  --timeout-sec 1800 \
  --interval-sec 5
```

Successful output:

```json
{"ok": true, "exec_status": 4, "exec_status_text": "FINISHED"}
```
