# Tutorial 04: Let the Agent Run Itself Every Morning, Unattended

| Item | Value |
| --- | --- |
| **Goal** | Turn a manually-proven task into a scheduled one: every workday at 9:00 a session spins up automatically and produces results — with run history, pause, and manual catch-up runs |
| **Capabilities involved** | Deployment / schedule (cron) / Agent version pinning / Deployment Run / Session |
| **Difficulty** | Advanced |
| **Prerequisites** | [01-ai-native-quickstart.md](01-ai-native-quickstart.md) done, plus **one complete task already run manually** (the hard requirement in step 1) |
| **Estimated time** | 20-30 minutes |
| **Source** | Official API docs (Deployment) + official Python SDK field tests |

## Scenario

Daily inspections, morning briefs, reconciliation batches — the shared trait is **nobody triggers
them**; they must run themselves on schedule and deliver results to people. That is what Deployment
does: it freezes "Agent + Environment + Vault + initial message + schedule" into one config, and
the server spins up sessions on time.

The hard part of scheduled tasks is not the config — it is that **nobody is watching**. Failed
runs, dirty results, double runs: all must be designed in before going live, or you discover them
a week too late.

## Final artifacts

One `active` Deployment + at least one successful run record + a retrieval loop that queries run
history with idempotency.

## Steps

### 1. Run it manually once first (not skippable)

**Do not create a Deployment before one manual success.** When a scheduled run goes wrong you
cannot watch the process — troubleshooting costs an order of magnitude more than a manual run.
Verify the full chain with a session first:

```bash
bl managed-agent session run --agent <your Agent> --prompt "Summarize yesterday's order data" --output json
```

**How to verify**: the result matches expectations, and `session events --session-id <id> --all`
shows no unexpected tool failures.

Confirm one thing while you are at it: **put the analysis logic in scripts, not all in the prompt**.
Scheduled tasks run deterministic work — the more steps the prompt describes, the more the daily
results fluctuate.

### 2. Find the Agent version to pin

```bash
export CMA_BASE="https://${BAILIAN_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio"

curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s "${CMA_BASE}/agents/agent_xxx" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" | jq '{id, name, version}'
```

Every save of an Agent auto-generates a new version. Omitting `agent.version` takes the latest —
meaning **anyone's single edit to the Agent changes your scheduled task's behavior**, and it
changes while unattended.

**Always pin the version in production.**

### 3. Create the Deployment

```bash
DEPLOYMENT_ID=$(curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "${CMA_BASE}/deployments" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily order summary",
    "agent": {"id": "agent_xxx", "version": 12},
    "environment_id": "env_xxx",
    "schedule": {"type": "cron", "expression": "0 9 * * 1-5", "timezone": "Asia/Shanghai"},
    "initial_events": [
      {"type": "message", "role": "user",
       "content": [{"type": "text", "text": "Summarize yesterday's order data and output the list of anomalous orders"}]}
    ]
  }' | jq -r '.id')
```

Key fields:

| Field | Notes |
| --- | --- |
| `schedule` | **Omitted = manual triggering only** (fine to omit during integration testing); `type` currently only `cron` |
| `schedule.timezone` | **Required**: omitting it gets the creation rejected outright with 400 (`PARAMS_MISSING: schedule.timezone is required`) — there is no "created but running in the wrong timezone"; only a wrong value produces "9 AM becomes midnight" |
| `agent.version` | Omitted = latest; always pin in production |
| `initial_events` | 1-50 entries; the opening message sent on your behalf at each trigger (field-tested boundaries: an empty array 400s with `initial_events is required`; 51 entries 400s with `at most 50`) |
| `vault_ids` / `resources` | Bind external credentials or reference data files here |

**Expected result**: the returned Deployment has `status: active`; the next trigger time is in
`schedule.next_run_at` (**there is no top-level `next_run_at` / `last_run_at` field** —
`jq '.next_run_at'` yields null).
**How to verify**:
```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s "${CMA_BASE}/deployments/${DEPLOYMENT_ID}" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" \
  | jq '{status, next_run_at: .schedule.next_run_at, last_run_at: .schedule.last_run_at}'
```
**Check that `schedule.next_run_at` is the time point you intend** — the value is UTC (Shanghai
9:00 shows as `01:00:00Z`; convert before comparing). A mistyped cron expression surfaces at this
step; no need to wait until tomorrow morning.

### 4. Trigger once manually for integration testing

No need to wait for the schedule:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "${CMA_BASE}/deployments/${DEPLOYMENT_ID}/run" \
  -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" | jq
```

Every trigger (scheduled or manual) produces one Run record and spins up one Session. Right after
triggering, the run's `session_id` is `null` (the session spins up asynchronously) and
`status: "running"`; once done, `status` becomes `succeeded`, and only then do `session_id` and
`finished_at` carry values:

```json
{
  "id": "drun_01M1G1J7JZ1P58VB91S3HYS9EN",
  "status": "succeeded",
  "session_id": "sesn_01M1G1J7KHBP4QE6ZGQB47RPST",
  "trigger_source": "manual",
  "started_at": "2026-09-02T03:10:54.047Z",
  "finished_at": "2026-09-02T03:10:56.834Z"
}
```

Query a single run with `GET /deployment_runs/{run_id}` (note: not
`/deployments/{id}/runs/{run_id}` — that one 404s).

**How to verify**: `GET /deployments/{id}/runs` shows this run; the run object directly carries
`session_id` — open its event stream and confirm the output matches the manual run in step 1.

### 5. Retrieve results, with run_id as the idempotency key

The server spins up sessions on schedule and produces results, but **delivering them to people is
your job**. A background worker periodically pulls run records and processes the unprocessed ones:

```python
def collect_runs(deployment_id, processed_run_ids):
    """Use run_id as the idempotency key to prevent double processing."""
    cursor, seen = None, set()
    while True:
        page = client.deployments.list_runs(deployment_id, limit=50, page=cursor)
        for run in page.data:
            if run.id in processed_run_ids or run.status not in ("succeeded", "failed"):
                continue
            yield client.deployment_runs.retrieve(run.id)
            # Caller durably commits its result and processed_run_ids together after handling.
            # Do not mark a running run as processed; it must be revisited on the next poll.
        cursor = page.next_page
        if not cursor:
            break
        if cursor in seen:
            raise RuntimeError("repeated run page cursor")
        seen.add(cursor)
```

(`client.deployment_runs.retrieve` is exactly `GET /deployment_runs/{id}` underneath; both SDK
methods field-tested working, and `list_runs` list items already carry `session_id` — skip the
retrieve entirely when you don't need details.)

**`run_id` must be persisted as the idempotency key, atomically with the handled result.**
Only process terminal runs (`succeeded` / `failed`); never mark a running run as handled.
For external notifications, use an outbox and a receiver-side idempotency key. Worker restarts, overlapping pulls, and
catch-up runs all make you see the same run twice; without the key you send duplicate
notifications or double-write the business DB.

### 6. Operations: pause, resume, reconfigure

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "${CMA_BASE}/deployments/${DEPLOYMENT_ID}/pause"   -H "Authorization: Bearer ${DASHSCOPE_API_KEY}"
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s -X POST "${CMA_BASE}/deployments/${DEPLOYMENT_ID}/unpause" -H "Authorization: Bearer ${DASHSCOPE_API_KEY}"
```

After `pause`, `status: "paused"` (carrying `paused_reason: {"type": "manual"}`, with
`schedule.next_run_at` nulled to stop scheduling); `unpause` restores `active` and reschedules.

- **Temporary stops use `pause`, not delete-and-recreate** — recreating changes the Deployment ID,
  and the new deployment's `/runs` listing won't show the old runs; but the run records themselves
  are not lost: the workspace-level `GET /deployment_runs` still returns the full history
  (field-tested: including runs of archived deployments), `run_id` is globally unique, and **the
  idempotency key survives recreation** — what you lose is only the convenience of querying
  history per deployment
- Reconfigure with `POST /deployments/{id}`: passed fields replace, omitted fields stay
  (field-tested: updating with only `description` left name / agent / schedule / initial_events /
  environment_id all untouched)
- `POST /deployments/{id}/archive` is a **terminal state**: after archiving, `/run` or updates both
  return 409 `DEPLOYMENT_STATE_CONFLICT: "deployment archived"`. Note archiving **does not change
  the `status` field** (still shows active or paused); detect the archived state by `archived_at`
  being non-null

### 7. Go-live self-check

- [ ] A manual `run` has succeeded at least once, with output matching the manual session
- [ ] `schedule.next_run_at` matches the intended time point (remember UTC conversion); `timezone` explicitly set
- [ ] `agent.version` is pinned
- [ ] `run_id` is persisted and the idempotency logic verified (processing one run twice produces no duplicate results)
- [ ] **Failure alerts are wired**: N consecutive failed runs must notify a human — never rely on someone flipping through records
- [ ] Confirmed no external cron runs the same job (old and new running in parallel is the most common double-trigger cause)
- [ ] Artifact landing is settled: written into `/mnt/session/outputs/` (automatically becoming downloadable artifacts, still downloadable after the session archives); sandbox files outside outputs are recycled with the session

## FAQ

| Symptom | Cause | Fix |
| --- | --- | --- |
| Did not run at the scheduled time | Status is `paused`, or `schedule` was never passed | Check `status`; `unpause` or add the `schedule` |
| Runs at the wrong time | `timezone` value is wrong (omitting it fails creation with 400 outright) | Set `Asia/Shanghai` explicitly; verify with `schedule.next_run_at` (UTC — remember to convert) |
| The same job ran twice | An external cron coexists with the Deployment | Retire the old cron; use `run_id` idempotency as the backstop |
| Results differ from last week | Version not pinned; someone edited the Agent | Pin `agent.version`; diff the `GET /agents/{id}/versions` listing to locate the change |
| Run records exist but no results | Artifacts were not written into `/mnt/session/outputs/` | Require that directory explicitly in the prompt; artifacts enter the Files listing automatically (`GET /files?scope_id=<session_id>`), still downloadable after the session archives |
| Want the run history of an archived deployment | Querying per deployment is inconvenient | The workspace-level `GET /deployment_runs` returns every run (field-tested: including archived deployments'); `run_id` is globally unique |
| Want to revert an archive | Archiving is terminal (re-triggering/updating both 409) | Create a new Deployment; this is exactly why temporary stops should use `pause` |
| A scheduled task has been silently failing for days | No failure alerts | Wire alerts — observability for scheduled tasks must be self-built |

## Going further

- Scheduled tasks needing external service credentials → Vault (the `vault_ids` field); full semantics in [../product/concepts.md](../product/concepts.md)
- Fixed reference data mounted on every run → [03-mount-files.md](03-mount-files.md)
- The sandbox lacks dependencies → [05-environment-packages.md](05-environment-packages.md)
- Full code implementations → [../integration/code-python.md](../integration/code-python.md) Shape C / [../integration/code-java.md](../integration/code-java.md)
