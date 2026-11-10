# Waiting for an agent request

Use `scripts/agent_job.py` when an execution tool would kill a long blocking call. Python 3 is required for this local wrapper. It calls the existing guarded helper, preserves the platform environment and records actual status; it has no independent cloud API or confirmation path.

## Start exactly once

Save the non-secret query in a file under this task's action-log directory. Initialize `SKILL_SESSION_ID` and `SKILL_VERSION` from the Skill as usual, exporting or injecting them into the start command. Choose a **new absolute job directory** under that action-log directory. The directory must not exist; an existing job is never relaunched.

```bash
SKILL_SESSION_ID="$SKILL_SESSION_ID" SKILL_VERSION="$SKILL_VERSION" \
python3 "$SKILL_ROOT/scripts/agent_job.py" start \
  --job-dir "$JOB_DIR" --query-file "$QUERY_FILE" --prepare -- \
  --source "$SOURCE" --extra-info '{"mode":"readonly"}'
```

`--prepare` runs the existing standard preparation once before the query. Use it when local dependency preparation is authorized, including unattended evaluations with authorized setup. If software changes are prohibited, complete a successful check-only probe separately and omit `--prepare`. Setup logs are saved to `setup.stdout` and `setup.stderr`; a setup failure stops before the query. Never unset mock flags or alter credentials.

For a related continuation, append `--session-id "$RETURNED_SESSION_ID"` after the source options. Use only the server SessionID returned by the earlier request and the same product source. Keep each query file unchanged until its job finishes.

For an explicitly approved operation, pass the exact operation options after `--` instead of readonly metadata: `--source`, `--confirm approve`, `--expect-tool`, and the complete concrete `--expect-args`. The query file contains only its short task label. All approval, allowlist and single-operation checks remain in `call_apsaradb_agent.sh`; the job tool does not create an approval or restart a failed operation.

A successful `start` only proves that a local worker was launched, not that a query or write succeeded.

## Wait on that same job

```bash
python3 "$SKILL_ROOT/scripts/agent_job.py" wait --job-dir "$JOB_DIR" --seconds 30
```

This is one bounded foreground observation, not another request. It waits at most 30 seconds and returns a small JSON status. Use a tool deadline longer than this wait. The supported interval is 0–55 seconds. When `state` remains `running`, invoke **wait on the same directory** again. Do not add separate sleep commands, background Monitor tools, custom polling loops or another start command.

Do not finalize the parent task while the job remains running merely because it has waited a long time, stdout is empty, or admission was previously throttled. A later accepted request can still be streaming. Retry exhaustion is established by the helper's actual terminal status, not a guessed deadline or retry count. If the enclosing execution budget itself ends, record the job as incomplete; never call it successful or empty.

- `state=finished` includes the actual helper `exit_code` and timestamps.
- `request_succeeded=true` additionally requires exit 0, a nonempty answer and a valid returned SessionID. Inspect the business result; this flag does not verify a resource postcondition.
- `state=interrupted` means the worker disappeared without terminal status. It is incomplete; never automatically relaunch it, especially for an operation.
- A failed helper remains failed even if stdout contains partial content or a SessionID. The log files remain available as evidence.

## Read the completed result and finish

```bash
python3 "$SKILL_ROOT/scripts/agent_job.py" result --job-dir "$JOB_DIR"
```

`result` also accepts `--seconds 30` for a bounded wait before reading. It uses the same 0–55 second limit and observes the existing job only. If the job is still running, it reports that no completed result is available; keep waiting on the same directory.

`result` emits the complete answer and helper stderr only after a successful finished request; otherwise it returns a failure and the recorded status. Raw `stdout`, `stderr`, `request.json` and `status.json` remain under the job directory. Use the job timestamps to distinguish this attempt from old artifacts.

An operation still requires a **new independent readonly verification job** for the exact approved resource and value. If execution failed or is uncertain, verify readonly and report the uncertainty, without replaying the write.

After the requested evidence is obtained, produce the final business answer and end the parent task. Do not leave background waiting tools or add unrelated memory/file-management work. The child helper's success does not by itself complete the parent task.
