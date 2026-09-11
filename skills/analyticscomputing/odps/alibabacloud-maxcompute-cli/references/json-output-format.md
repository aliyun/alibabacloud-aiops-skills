> Loaded on demand — full envelope spec with worked `jq` examples. Skip unless the agent is parsing a response shape not covered by SKILL.md's key-path list.

# JSON output format

Non-streaming `--json` output is one envelope. The exception is
`job wait --stream --json`, which emits one JSON event per line (NDJSON); parse
those events line by line. Use `jq` or Python to extract fields like `status`,
`data`, `error`, and `agent_hints` from an envelope.

```bash
# Extract query result rows
aliyun maxc query "SELECT ..." --json | jq '.data.result.rows'

# Export as TSV
aliyun maxc query "SELECT ..." --json | jq -r '.data.result.rows[] | [.col1, .col2] | @tsv'
```

Check the envelope's top-level `status` first: `success`, `pending`, or
`failure`. Job and cache lifecycle states stay in their documented nested
`data` fields or stream events; do not confuse them with the envelope status,
and stop on an unknown top-level value. On `failure`, read `error.code`,
`error.suggestion`, and `error.recovery_steps` before retrying. Inspect
`agent_hints.warnings` for every status.

Run public-cloud commands with the `aliyun maxc` prefix. Treat structured
`agent_hints.actions` as authoritative and use `action_ids` to account for all
of them. Before execution, check `executable`, `agent_allowed`,
`confirmation_required`, and `effect`; resolve placeholders from verified
context. `next_actions` is a compatibility list containing only executable,
agent-allowed, confirmation-free commands.

## Query success

`data` is normalized into `result`, `pagination`, and `safety`:

```json
{
  "data": {
    "result": {
      "rows": [{"id": 1, "name": "Alice"}],
      "schema": [
        {"name": "id", "type": "BIGINT", "comment": ""},
        {"name": "name", "type": "STRING", "comment": ""}
      ],
      "row_count": 1,
      "returned_rows": 1
    },
    "pagination": {
      "has_more": false,
      "next_cursor": null
    },
    "safety": {
      "mode": "read_only",
      "force": false,
      "allowed_operations": ["SELECT"],
      "effective_hints": {},
      "policy_decision": "allowed"
    }
  }
}
```

Key paths: `data.result.rows`, `data.result.returned_rows`, `data.result.row_count`, `data.pagination.has_more`, `data.pagination.next_cursor`.

## Query cost and explain

```json
{
  "data": {
    "analysis": {
      "estimated_input_size_bytes": 456789,
      "sql_complexity": "low",
      "tables_used": ["schema.table"]
    },
    "safety": { "mode": "read_only", "policy_decision": "allowed" }
  }
}
```

Key path: `data.analysis` (not `data.result`).

## Query timeout and asynchronous continuation

When `--wait N` is exceeded, `status` is `pending` with a `job_id` in metadata:

```json
{
  "status": "pending",
  "metadata": {
    "job_id": "2026...",
    "project": "my_project",
    "wait_seconds": 10,
    "sql_executed": "SELECT ..."
  },
  "agent_hints": {
    "actions": [
      {
        "id": "job.wait",
        "command": "aliyun maxc --user-agent <user_agent> job wait 2026... --project my_project --json",
        "executable": false,
        "placeholders": { "user_agent": "<user_agent>" },
        "effect": "read",
        "confirmation_required": false,
        "agent_allowed": true
      },
      {
        "id": "job.status",
        "command": "aliyun maxc --user-agent <user_agent> job status 2026... --project my_project --json",
        "executable": false,
        "placeholders": { "user_agent": "<user_agent>" },
        "effect": "read",
        "confirmation_required": false,
        "agent_allowed": true
      },
      {
        "id": "job.result",
        "command": "aliyun maxc --user-agent <user_agent> job result 2026... --project my_project --max-rows 100 --json",
        "executable": false,
        "placeholders": { "user_agent": "<user_agent>" },
        "effect": "read",
        "confirmation_required": false,
        "agent_allowed": true
      }
    ],
    "action_ids": ["job.wait", "job.status", "job.result"],
    "insights": ["Query promoted to async after 10s."]
  }
}
```

Only the action fields needed to illustrate continuation safety are shown above;
the runtime also returns each action's title and argument schema. Resolve the
session User-Agent placeholder before following up. Because these templates are
not yet executable, this envelope does not include legacy `next_actions`.

`job wait` and `job result` expose `data.result` only when a result is ready.
An unfinished job response uses `data.job` and a non-terminal job state; keep
the job ID opaque and continue only as requested.

Successful `job wait` and `job result` responses describe their non-mutating
follow-up in `data.safety`: `scope=result_observation` and
`allowed_operations` contains `JOB_WAIT` or `JOB_RESULT`. This does not mean
the already-submitted SQL was executed again. Reuse `job wait` results instead
of fetching them a second time.

## Authorized DDL or DML with `--force`

DDL/DML is allowed only when the user explicitly requests the exact mutation.
Verify the statement, project, schema, target, and effect; submit one statement
at a time with `--force`. The positive allowlist accepts recognized data-plane
mutations; unknown, procedural, permission, session-control, and administrative
SQL remain blocked even with `--force`. Do not reinterpret
`WRITE_OPERATION_REQUIRES_FORCE` as authorization, combine the write with
another statement, or execute a write action merely because it appears in
`agent_hints.actions`. Tunnel-based `data upload` is a separate write path with
its own authorization boundary.
Leading `SET` options are part of the same authorized execution context.
Project-security and masking controls remain blocked, and forced mutations
accept only audited statement-local execution hints.
On successful query or submission responses, `data.safety.effective_hints`
reports the hints actually sent to MaxCompute. Audited hint values are shown;
an audited key whose value is outside its documented boolean, numeric, or enum
domain is still rendered as `<redacted>`. Values of unknown hints retained for
read-only compatibility are also never echoed.

A successful DDL/DML command can return an empty `data.result`; that is not a
zero-row query. Report the operation and target proved by the envelope, and
retain any returned job ID when the write remains pending.

## Data upload

Tunnel-based bulk load. Before running it, confirm the exact project, table,
partition, local file, and append or overwrite mode. The user's original request
can provide this authorization. `data` is flat (no inner wrapper):

```json
{
  "command": "data upload",
  "status": "success",
  "data": {
    "table": "proj.sch.tbl",
    "applied_partition": "ds=20260509",
    "rows_written": 12345,
    "bytes_read": 2345678,
    "blocks": 2,
    "overwrite": false,
    "warnings": []
  },
  "metadata": { "project": "my_project", "requested_partition": "ds=20260509", "delimiter": ",", "block_size": 10000 },
  "agent_hints": {
    "actions": [
      {
        "id": "data.sample",
        "command": "aliyun maxc --user-agent <user_agent> data sample proj.sch.tbl --partition ds=20260509 --project my_project --json",
        "executable": false,
        "placeholders": { "user_agent": "<user_agent>" },
        "effect": "read",
        "confirmation_required": false,
        "agent_allowed": true
      }
    ],
    "action_ids": ["data.sample"]
  }
}
```

The unresolved User-Agent keeps this cloud follow-up out of `next_actions`.
Resolve it with the existing session value, then verify the exact table and
partition from the successful envelope before deciding whether a sample is
appropriate.

On failure, `error.context` carries `line` (1-based) and `column` (column NAME):

```json
{
  "status": "failure",
  "error": {
    "code": "CSV_PARSE_ERROR",
    "message": "could not parse 'abc' as bigint: invalid literal",
    "context": { "line": 3, "column": "user_id" }
  }
}
```

## Data download

```json
{
  "command": "data download",
  "status": "success",
  "data": {
    "table": "proj.sch.tbl",
    "applied_partition": "ds=20260509",
    "output_path": "/abs/path/out.csv",
    "rows_written": 10000,
    "bytes_written": 4567890,
    "columns": ["col1", "col2"],
    "truncated": true,
    "warnings": ["--limit reached; output may be partial (session has 53210 rows)."]
  }
}
```
