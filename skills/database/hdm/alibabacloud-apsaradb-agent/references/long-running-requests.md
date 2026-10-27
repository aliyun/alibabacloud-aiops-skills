# Waiting for a readonly agent request

Prefer a tool that returns a live process handle and lets you wait on that same handle without killing it when a polling interval ends. Each poll is observation, not a new agent request. Sequential throttle recovery plus a streaming answer may exceed a ten-minute blocking tool limit.

If the tool has no persistent-process facility, the following local recipe starts the existing helper in a separate process session. It does not change cloud APIs, credentials, retry rules, or success criteria. Keep the parent task active and poll until completion; do not leave the job unobserved or return a final business answer while it is still running.

## Start once

Set `SKILL_ROOT` to the installed Skill's absolute directory, `QUERY_FILE` to a saved non-secret query, `SOURCE` to its correct product route, and `JOB_DIR` to a new absolute directory under this task's action-log directory. Keep the required `SKILL_SESSION_ID` and `SKILL_VERSION` exported. The directory must not exist: this guards against accidentally relaunching a previously started job.

```bash
python3 - "$SKILL_ROOT/scripts/call_apsaradb_agent.sh" "$QUERY_FILE" "$JOB_DIR" --source "$SOURCE" <<'PY'
import os
import pathlib
import subprocess
import sys

helper, query, directory, *options = sys.argv[1:]
if not all(pathlib.Path(p).is_absolute() for p in (helper, query, directory)):
    raise SystemExit("Use absolute paths for helper, query, and job directory")
os.umask(0o077)
job = pathlib.Path(directory)
job.mkdir(mode=0o700)
wrapper = '''
set +e
job=$1
shift
bash "$@"
rc=$?
printf '%s\\n' "$rc" > "$job/exit-code.tmp"
mv "$job/exit-code.tmp" "$job/exit-code"
exit "$rc"
'''
with open(query, "rb") as inp, (job / "stdout").open("wb") as out, (job / "stderr").open("wb") as err:
    process = subprocess.Popen(
        ["bash", "-c", wrapper, "_", str(job), helper, "-", *options],
        stdin=inp, stdout=out, stderr=err, start_new_session=True,
    )
(job / "pid").write_text(str(process.pid) + "\n")
print("Started local job:", job, "PID:", process.pid)
PY
```

For a related continuation only, append `--session-id "$RETURNED_SESSION_ID"` to the Python command's arguments before `<<'PY'`. Use only the server SessionID actually returned by the earlier response, preserve the source, and use a new job directory. Never manufacture a SessionID or reuse another product's conversation.

## Poll the same job

Run this check in later tool calls using the same `JOB_DIR`; leave a reasonable interval between checks. Do not run the start command again.

```bash
python3 - "$JOB_DIR" <<'PY'
import os
import pathlib
import sys

job = pathlib.Path(sys.argv[1])
status = job / "exit-code"
if status.exists():
    print("Helper finished; exit code:", int(status.read_text().strip()))
else:
    try:
        os.kill(int((job / "pid").read_text().strip()), 0)
    except ProcessLookupError:
        print("Job disappeared without an exit code: interrupted/incomplete; do not relaunch")
    else:
        print("Still running; wait on this same job")
PY
```

After completion, inspect this job's `stdout` and `stderr`. Exit 0 alone is insufficient: the answer must be complete and a new conversation must return a valid `[SessionID]`. A nonzero exit, missing exit status, partial stream, or readonly violation remains a failed request. Preserve its evidence and follow the Skill's bounded, related continuation rules where applicable. Do not treat a launch or a poll as a successful cloud call, change a failure into an empty result, or start parallel copies to avoid waiting.
