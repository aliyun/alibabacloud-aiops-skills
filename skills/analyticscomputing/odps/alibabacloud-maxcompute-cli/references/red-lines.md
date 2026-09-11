> Load on demand after an error or before retrying a failed command.

# Safety boundaries and recovery

Use `aliyun maxc` for MaxCompute data-plane operations. Apply the safety and recovery rules below when handling credentials, persistent changes, writes, query cost, and command failures.

## Safety and execution rules

| # | Rule | Why |
|---|---|---|
| 1 | Add `--json` to machine-driven commands and parse the envelope | Plain output is optimized for human reading |
| 2 | Resolve table, schema, project, endpoint, partition, and enum values before using them | The valid identifiers depend on the active MaxCompute context |
| 3 | Obtain explicit user confirmation before installing or upgrading Alibaba Cloud CLI | Installation changes the user's environment |
| 4 | When `auth whoami` reports an authenticated identity, verify the effective principal, project, and object permission before changing authentication | An object-level permission failure is not necessarily an authentication failure |
| 5 | For a partitioned table, verify partition columns and any unknown partition value before querying | Partition names, formats, and semantics vary by table |
| 6 | Use the identifier shape returned by metadata discovery | Two-tier and three-tier projects require different qualification; cross-project SQL includes the project |
| 7 | Do not log, echo, or include credentials in output | Credentials remain sensitive in error and diagnostic contexts |
| 8 | Read `error.suggestion` before retrying a failed command | The envelope contains case-specific recovery guidance |
| 9 | Prefer direct OAuth on current supported releases; if runtime help conflicts with this contract, upgrade or use an explicitly approved identity source | Authentication must not require credentials in chat or command arguments |
| 10 | Use runtime help and actual command output when they differ from static examples | The CLI command contract can evolve |
| 11 | Execute DDL/DML only when the user explicitly authorizes the exact statement, target, and effect; use `--force` one statement at a time | The write gate checks every executable operation and rejects mixed statements even with `--force`, but it is still a safety aid rather than authorization. `data upload` is separate and also requires authorization. |
| 12 | Inspect `agent_hints.warnings` before reporting success | Warnings can report cache staleness, cost alerts, or semantic gaps |
| 13 | Treat leading `SET` hints as part of the SQL execution context | Never use project-security, access-control, or masking parameters through `query`; forced writes accept only audited statement-local hints. |

## Common mistakes

| Mistake | Correct approach |
|---------|------------------|
| Assuming every project has a schema layer | Detect two-tier versus three-tier mode; use the identifier returned by `meta` commands |
| Guessing an uncertain column filter value | Inspect actual values with `data sample` or `SELECT DISTINCT` |
| Using `aliyun maxc sql ...` | Use `aliyun maxc query ...` |
| Treating `WRITE_OPERATION_REQUIRES_FORCE` as permission to write | Obtain an explicit user request, verify the exact statement and target, then use `--force` for that one statement only |
| Treating `DROP` or `PURGE` like a reversible retry | Name the exact target and irreversible effect before running the separately authorized statement once |
| Passing credentials directly to `auth login` | Use runtime-supported direct OAuth or an approved existing identity source; never place credential values in command arguments |
| Assuming `aliyun --profile <name> maxc ...` overrides or durably refreshes the effective identity | The Alibaba Cloud CLI root injects the selected profile's current credentials, but an explicit provider under `~/.maxc` can suppress them; verify the principal, identity source, expiry information, and warnings with `auth whoami --json` |
| Hand-editing credential or MaxCompute context files | Use the matching provider-specific login command, or `session set` when only an authorized default project/schema change is needed |
| Inventing endpoints | Use an endpoint supplied by the user, returned by the CLI, or present in the verified effective configuration |
| Using `job wait --stream` and expecting one JSON envelope | `--stream` emits NDJSON; use `job wait --json` for one envelope |
| Running an unknown or potentially large scan without a cost check | Use `query cost` or `--cost-check N`, then adjust columns and partition filters as needed |
| Ignoring `agent_hints.warnings` | Include relevant cache, cost, and semantic warnings in the decision or response |
| Assuming `meta describe` data is live | Check `metadata.source` and warnings when freshness matters |
| Deriving a project by adding or removing `_dev` or `_prod` | Use a discovered or user-provided project name |
| Querying a partitioned table with an unknown partition model | Inspect the table and partition metadata before constructing the filter |
| Substituting an accessible project or table after the requested target fails | Keep the requested target; ask before changing it, even when another object looks similar |
| Using invented credentials, resource identifiers, rows, command output, query results, or mock state as evidence for a real-data request | Stop on the missing prerequisite and report what must be supplied or provisioned; create local input only from user-provided or otherwise verified content |
| Reading `~/.aliyun/config.json`, `~/.maxc/config.yaml`, or secret-bearing environment variables | Use supported identity and session inspection commands, which return sanitized summaries |
| Reporting a failed operation as zero rows or a successful transfer | Treat the envelope state as authoritative; report row counts and paths only from a successful result, and verify downloaded output exists |

## Recovery anti-patterns

| Anti-pattern | Why it fails | Use this approach |
|--------------|--------------|-------------------|
| Iterating every project, schema, and table without a scoped request | It can be slow, rate-limited, and unnecessarily broad | Start with the user-named project or a targeted metadata search; ask for a material missing choice |
| Retrying a failed command without inspecting its envelope | The retry can repeat a validation, permission, or SQL error | Read `error.code` and `error.suggestion`, change the relevant input, then retry |
| `SELECT *` on an unknown table | It can scan unnecessary columns and increase cost | Inspect the schema, select the required columns, and apply an appropriate limit or partition filter |
| Generating SQL from an unverified schema | The query can use nonexistent or ambiguous columns | Run `meta describe` when the required columns are not already verified |
| Continuing after a prerequisite metadata, partition, permission, or local-file check fails | Downstream commands would use unverified inputs and can target the wrong data | Stop the dependent workflow, report the sanitized failure, and request or discover only the missing input within the named scope |
| Broadly enumerating guessed projects, regions, endpoints, schemas, or tables after a scoped failure | It can cross the user's intended boundary and still does not prove the requested target | Follow recovery actions that remain within the named scope; if scoped discovery still cannot resolve the target, stop and ask for the material missing choice |
| Running redundant queries | It increases compute, latency, and result-reconciliation work | Reuse verified metadata and results when they satisfy the next step |
| Executing `next_actions[]` or `actions[]` as an unchecked script | A hint can be a template, disallowed for agents, or require confirmation | Prefer structured `actions[]`; check `executable`, `agent_allowed`, `confirmation_required`, and `effect`, then resolve placeholders from verified context |

## Error code to recovery

When `status=failure`, inspect `error.code` and follow the case-specific `error.suggestion` before retrying.

| `error.code` | Meaning | Recovery |
|--------------|---------|----------|
| `VALIDATION_ERROR` | Invalid input or missing required arguments | Fix the arguments and retry |
| `NOT_FOUND` | Table, job, or resource does not exist | Check the name with `meta search` or `job list` |
| `SCHEMA_NOT_FOUND` | Schema does not exist | Check `error.context.did_you_mean` and `error.context.available_schemas`; list schemas with `meta list-schemas --json` |
| `TABLE_NOT_FOUND` | Table does not exist in the schema | Check `error.context.did_you_mean` and `error.context.available_tables`; search with `meta search <name> --json` |
| `COLUMN_NOT_FOUND` | Column reference does not exist | Check `error.context.available_columns`; run `meta describe <table> --json` |
| `WRITE_OPERATION_REQUIRES_FORCE` | The client-side write gate detected SQL DDL or DML | This error is not authorization. If the user explicitly requested that exact write, recheck its statement, target, and effect, then retry once with `--force`; otherwise stop. This code does not apply to Tunnel-based `data upload`. |
| `CSV_PARSE_ERROR` | A CSV cell could not be parsed against the column type during `data upload` | Use `error.context.line` and `error.context.column` to locate and report the cell. Modify the source CSV only when the user requests that edit. Inspect `error.context.remote_commit_state` when present; do not claim a commit outcome beyond the envelope. |
| `UPLOAD_COMMIT_OUTCOME_UNKNOWN` | The process was interrupted or the backend failed after the Tunnel commit request began, so remote visibility cannot be proven | **Do not retry the upload.** Verify the exact target table or partition first; retrying append can duplicate rows, while retrying overwrite can replace a result that already committed successfully. This error is non-recoverable and exits with code 130. |
| `PERMISSION_DENIED` | The effective identity cannot perform the requested operation | Verify the principal, project, object name, and operation with `auth whoami` and `auth can-i` |
| `SQL_ERROR` | SQL syntax or execution error | Fix the SQL; use `query explain` when validation is needed |
| `COST_LIMIT_EXCEEDED` | Cost exceeds the `--cost-check` threshold | Add partition filters, reduce columns, or ask the user before raising the threshold |
| `BACKEND_CONNECTION_ERROR` | The backend is unreachable | Check the local endpoint, network, and service status; retry once only after the failing condition changes |
| `JOB_TIMEOUT` | The job did not finish within `--timeout` | Check with `job status <id>`; continue waiting with an appropriate timeout when requested |
| `QUOTA_EXCEEDED` | The project quota limit was reached | Wait and retry when appropriate, or ask the user or project administrator to choose an authorized quota when the choice changes capacity or cost |
| `EXECUTION_FAILED` | The backend job failed | Run `job diagnose <id> --json` when a job ID is available |
| `FEATURE_UNAVAILABLE` | The current backend does not expose the feature | Check `agent context --json` and report the supported boundary |
| `INTERNAL_ERROR` | The CLI or backend returned an unexpected failure | Report the sanitized relevant envelope fields and request ID; check the CLI version before retrying |

## Symptom-based troubleshooting

When the symptom does not map to a clear `error.code`:

| Symptom | Possible cause | Recovery |
|---------|----------------|----------|
| `list-tables` returns empty although the user expects tables | Candidate causes include wrong project/schema, permissions or catalog visibility, cache state, or a genuinely empty namespace | Verify the effective project and schema, inspect warnings/source metadata, and check access before concluding that no tables exist |
| `search` returns no matches | Candidate causes include keyword mismatch, search-source coverage, permissions, or wrong project/schema | Verify the context and search source, then try a broader targeted keyword |
| `cache build` reports 0 tables | Candidate causes include wrong project/schema, permissions, or an empty namespace | Verify the selected context and access before rebuilding |
| `describe` fails with `NOT_FOUND` | The name, namespace, permission, or catalog view can be wrong | Use targeted metadata discovery only within the user-named scope; do not switch project, schema, or table without confirmation |
| Commands hang or time out | Candidate causes include an OAuth callback or project picker awaiting input, network/endpoint failure, or backend delay | Inspect current stderr and interactive state first; then verify the effective endpoint and connectivity |
| `whoami` shows the wrong project | A session, file, or environment override is active | Inspect `session show --json` and `config_sources`; change persistent state only with user authorization |
| `whoami` shows `identity_source=mixed` | More than one identity source is active | Verify the effective principal and inspect source summaries without printing secrets |

If recovery is not possible, report the CLI version, masked effective principal,
active project when it is safe and relevant, request ID, and only the sanitized
envelope fields needed to explain the failure. Remove credentials, tokens, SQL
literals, row data, and sensitive local paths.
