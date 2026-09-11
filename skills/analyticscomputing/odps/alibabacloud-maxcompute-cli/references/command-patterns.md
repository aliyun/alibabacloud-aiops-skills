> Loaded on demand — selected command patterns and JSON response paths. Skip unless the agent needs details not covered by SKILL.md.

# `aliyun maxc` command patterns

Runtime `aliyun maxc <command> --help` output is authoritative for available
commands and flags. This file contains common patterns. For safety and recovery
rules, see [red-lines.md](red-lines.md). For workflow guidance, see
[../SKILL.md](../SKILL.md).

The command fragments below omit the repeated User-Agent option for readability.
Before executing any fragment that calls a cloud API, append
`--user-agent "$MAXC_AGENT_UA"` with the session value from SKILL.md. Local help,
`agent context`, `agent manifest`, `session show`, and `cache status` may omit it.

Apply SKILL.md's command-plan rule before using any pattern below. An explicit
“only run” plan or any no-execution boundary overrides this preflight; do not
execute commands that the user did not list.

## Preflight

Use these first when the environment or command surface is unclear:

```bash
aliyun version
aliyun maxc --help
aliyun maxc query --help
aliyun maxc auth whoami --json
```

If `aliyun` or `aliyun maxc` is missing, read [setup-install.md](setup-install.md) before proceeding.

## Authentication and session

```bash
aliyun maxc auth whoami --json
# Preferred interactive public-cloud authentication
aliyun maxc auth login --oauth --json
MAXCOMPUTE_ENDPOINT="<endpoint>" MAXCOMPUTE_PROJECT="<project>" aliyun maxc auth login --oauth --project "<project>" --json
# Reconfigure a verified saved access-key/STS provider (not OAuth/external)
MAXCOMPUTE_ENDPOINT="<endpoint>" MAXCOMPUTE_PROJECT="<project>" aliyun maxc auth login --project "<project>" --json
# Reconfigure direct OAuth without losing refresh state
MAXCOMPUTE_ENDPOINT="<endpoint>" MAXCOMPUTE_PROJECT="<project>" aliyun maxc auth login --oauth --project "<project>" --json
# Force project selection for direct OAuth when runtime help lists --reselect
aliyun maxc auth login --oauth --reselect --json
# Approved non-interactive helper
MAXCOMPUTE_ENDPOINT="<endpoint>" MAXCOMPUTE_PROJECT="<project>" aliyun maxc auth login-external --process-command "<user-approved-credential-helper>" --project "<project>" --json
aliyun maxc auth can-i --table your_table --operation SELECT --json
aliyun maxc session show --json
aliyun maxc session set --project your_project --schema your_schema --json
```

The Alibaba Cloud CLI root reserves `--endpoint` and consumes it before the
MaxC extension parser. Pass a verified MaxCompute endpoint through the child
environment as shown above; do not place `--endpoint` after `maxc`. These context values are not credentials, but still avoid printing or
enumerating unrelated environment variables.

### Optional fallback when direct OAuth is unavailable

If an unsupported older runtime lacks direct OAuth, prefer a user-approved
update. Use an Alibaba Cloud CLI OAuth profile only when that runtime must
remain in use.

```bash
# Inspect existing profile names without exposing secret values
aliyun configure list

# Create a profile only when the user chooses this fallback
aliyun configure --mode OAuth --profile "<profile>"

# Verify one selected profile without changing the Alibaba Cloud CLI default
aliyun --profile "<profile>" maxc auth whoami --json

# Persist injected credentials only when this runtime must remain in use
MAXCOMPUTE_ENDPOINT="<endpoint>" MAXCOMPUTE_PROJECT="<project>" aliyun --profile "<profile>" maxc auth login --from-env --project "<project>" --json
```

`session set`, `session show`, and `session unset` are local-only commands. They
read or mutate defaults without loading the backend, so their success does not
prove that the identity can access the project. Project-local cwd configs can
shadow the global defaults, and `session set` warns when they do. Verify remote
access afterward with `auth whoami` or a scoped metadata command.

`session unset` clears both `default_project` and `default_schema`; use it only
when the user explicitly wants both defaults removed. It is not a schema-only
undo command.

On a bundled runtime without direct OAuth, the Alibaba Cloud CLI root consumes
`--profile` and injects the selected profile's current credentials into the
child process.
Combining that root flag with `auth login --from-env` persists only the current
credentials; it does not create a durable profile link. Rerun the bootstrap
after expiry or upgrade to direct OAuth.

When no explicit MaxCompute provider is active, a selected Alibaba Cloud CLI
profile can be inspected or used for a one-off command. Verify the returned
principal, for example:

```bash
aliyun --profile "<profile>" maxc auth whoami --json
aliyun --profile "<profile>" maxc meta list-tables --json
```

An explicit MaxCompute credential provider suppresses profile-injected
credentials for ordinary commands. Confirm `data.identity.identity_source`, the
reported principal, token-expiry information when present, and warnings before
accessing data.

Never put credentials in command arguments or hand-edit credential files.

Do not use plain `auth login` to edit a direct-OAuth or external provider: it
can replace that provider and discard refresh configuration. Re-run the matching
provider-specific login, or use `session set` when only the default project or
schema changes and the endpoint remains valid.

## Metadata and data discovery

```bash
aliyun maxc meta list-tables --json
aliyun maxc meta list-tables --schema my_schema --json
aliyun maxc meta list-tables --project other_project --json
aliyun maxc meta describe your_table --json
aliyun maxc meta search "keyword" --json
aliyun maxc meta search-columns "user_id" --json
aliyun maxc meta partitions your_table --json
aliyun maxc meta latest-partition your_table --json
aliyun maxc meta freshness your_table --json
aliyun maxc meta list-projects --json
aliyun maxc meta list-schemas --project your_project --json
aliyun maxc data sample your_table --rows 5 --partition ds=2026-03-20 --columns id,ds --json
aliyun maxc data profile your_table --partition ds=2026-03-20 --json
aliyun maxc data download your_table --output ./out.csv --partition ds=2026-03-20 --columns id,name --limit 1000 --json
```

- Table-scoped metadata, data, and semantic commands accept `--project` for one-off cross-project access without switching session. `meta list-projects` does not.
- Most meta commands support `--schema` to override the session default.
- `meta search` uses catalog search when available and falls back to targeted substring matching when needed.

### Metadata cache

```bash
aliyun maxc cache status --project your_project --schema your_schema --json
aliyun maxc cache build --project your_project --schema your_schema --json
aliyun maxc cache build --project your_project --schema your_schema --async --json
aliyun maxc cache build-status --project your_project --build-id "<build-id>" --json
aliyun maxc cache clear --project your_project --schema your_schema --dry-run --json
aliyun maxc cache clear --project your_project --schema your_schema --force --json
```

`cache build` refreshes local metadata from the selected remote context.
`cache clear` deletes local cached metadata: resolve the project and optional
schema, preview with `--dry-run`, and use `--force` only when that exact local
deletion is requested or confirmed. Treat build IDs as opaque.

### CSV upload and download

`data upload` and `data download` move CSV/TSV between local files and an
existing table through the MaxCompute Tunnel API. Missing partitions are not
created unless the caller explicitly supplies `--create-partition`.

`data upload` is a write operation. Resolve the exact project, table, complete
partition specification, whether a missing target partition may be created,
source file, and append or overwrite mode before every upload. The user's
request can provide that authorization; ask only for missing choices. Treat
`--overwrite` as destructive and name the scope that will be replaced.

Rules:

- **Leading `SET` options are execution context, not authorization.**
  Project-security, access-control, and masking parameters are blocked. A
  forced mutation accepts only audited statement-local execution hints.

- **Target table must already exist before upload.** No auto-create. If it is
  missing, stop and report `NOT_FOUND`; an upload request is not authorization
  to create a table. If the user separately authorizes the exact table DDL,
  project, schema, target, and effect, execute that one supported `CREATE TABLE`
  statement with `--force`, re-describe the table, and only then retry upload.
- **Partitioned table requires `--partition`.** Spec must list every partition key with no extras (e.g. `ds=20260509,hh=12` — not `ds=20260509` alone, not `wrong=1`). Wrong keys → `VALIDATION_ERROR` up front, no Tunnel session opened.
- **Missing partitions are not created by default.** After explicit authorization, `--create-partition` lets Tunnel create the exact partition named by `--partition`. This metadata mutation happens before row commit, so a later upload failure can leave the new partition present but empty. `--create-partition` without `--partition` is rejected.
- **Use `--dry-run` before the write** when the file-to-table mapping has not yet been validated. It validates the table schema, complete CSV row widths, mapped primitive values, and partition intent without opening an upload session, creating a partition, or writing rows. It still does not prove that a later remote commit will succeed.
- **Default semantics is append.** Pass `--overwrite` for INSERT-OVERWRITE-style replacement of the partition (or whole non-partitioned table). Without `--overwrite`, rows are added.
- **Fail-fast on bad rows.** The CLI validates the complete file before opening a Tunnel upload session. Row parse failures therefore write no rows. The error envelope's `error.context` gives `line` and `column`; an explicitly created partition is a separate metadata side effect as described above.
- **Primitive types only** (bigint/int/smallint/tinyint/double/float/decimal/boolean/string/varchar/char/date/datetime/timestamp). `array`/`map`/`struct` columns → `VALIDATION_ERROR` before opening the session. Those types require a separately authorized SQL write workflow.
- **CSV defaults**: `,` delimiter, header row required (use `--no-header` for ordinal mapping), `\N` as NULL on upload / empty cell as NULL on download (override with `--null-marker`). UTF-8 encoding only.
- **Download requires `--partition` for partitioned tables**, same as upload. Use `--limit N` to cap rows; `data.truncated=true` plus a warning surface in the envelope when the limit was hit. Existing local output files are rejected unless `--overwrite` is explicitly supplied.
- **`data sample` is still preferred for inline JSON inspection** of a few rows. Use `data download` only when you need a CSV file on disk.

Examples after the write scope is confirmed:

```bash
# Validate the confirmed file and target without writing rows
aliyun maxc data upload my_part_table --file ./rows.csv --partition ds=20260509 --dry-run --json

# Append a CSV to a confirmed non-partitioned table
aliyun maxc data upload my_table --file ./rows.csv --json

# Overwrite one explicitly confirmed partition
aliyun maxc data upload my_part_table --file ./rows.csv --partition ds=20260509 --overwrite --json

# Create one verified missing partition, then upload (explicit metadata side effect)
aliyun maxc data upload my_part_table --file ./rows.csv --partition ds=20260509 --create-partition --json

# TSV upload
aliyun maxc data upload my_table --file ./rows.tsv --delimiter $'\t' --json

# Download a column subset, capped at 10000 rows
aliyun maxc data download my_part_table --output ./out.csv --partition ds=20260509 --columns id,name --limit 10000 --json

# Replace an existing local file only with explicit authorization
aliyun maxc data download my_part_table --output ./out.csv --partition ds=20260509 --overwrite --json
```
## Query and jobs

Query syntax:

```bash
aliyun maxc query "SELECT 1 AS one" --json
aliyun maxc query cost "SELECT 1 AS one" --json
aliyun maxc query explain "SELECT 1 AS one" --json
```

### Offline, MCQA, and MaxQA

Use the execution mode that matches the user's intent:

| Mode | Command | Notes |
|---|---|---|
| Offline SQL | `aliyun maxc query "SELECT 1" --json` | Default mode; async jobs use plain instance IDs |
| MCQA v1 | `aliyun maxc query "SELECT 1" --mcqa --json` | No quota required; async jobs may return `<instance-id>@<subquery-id>` |
| MaxQA / MCQA v2 | `aliyun maxc query "SELECT 1" --maxqa --quota "<verified-quota-name>" --json` | Requires `--quota` (or config `mcqa.quota_name`); async jobs use plain instance IDs |

If config already enables MCQA by default, `aliyun maxc query ... --no-mcqa --json` forces the command back to offline mode.

With SET options (parsed and passed as hints to MaxCompute):

```bash
aliyun maxc query "SET odps.sql.type.system.odps2=true; SELECT CAST(id AS INT) FROM schema.table LIMIT 10" --json
```

Legacy-compatible syntax still works:

```bash
aliyun maxc query "SELECT 1 AS one" --mode cost --json
```

The command is `query`, not `sql`. There is no `aliyun maxc sql` command.

For an exact DDL/DML statement the user has explicitly requested, first verify
the project, namespace, target, and effect, then submit only that statement:

```bash
aliyun maxc query "CREATE TABLE schema.table_name (id BIGINT)" --project project_name --user-agent "$MAXC_AGENT_UA" --force --json
```

Do not add `--force` merely because the unforced command returned
`WRITE_OPERATION_REQUIRES_FORCE`. For `DROP`, `PURGE`, overwrite, and other
destructive effects, state the exact scope and irreversibility before running
the authorized command.

### Wait and timeout

```bash
# Default: wait up to 10 seconds, auto-promote to async if not done
aliyun maxc query "SELECT 1 AS one" --json

# Submit and return immediately (get job_id without waiting)
aliyun maxc query "SELECT 1 AS one" --wait 0 --json

# Wait up to 60 seconds before promoting
aliyun maxc query "SELECT 1 AS one" --wait 60 --json
```

Interactive variants use the same `--wait` behavior:

```bash
# MCQA v1 submit-now / wait-later
aliyun maxc query "SELECT 1 AS one" --mcqa --wait 0 --json

# MaxQA / MCQA v2 submit-now / wait-later
aliyun maxc query "SELECT 1 AS one" --maxqa --quota "<verified-quota-name>" --wait 0 --json
```

- `query --wait N`: polls for up to N seconds. If the job finishes within N seconds, returns the result. Otherwise auto-promotes to async and returns `status=pending` with a `job_id`.
- `query --wait 0`: submits and returns immediately with `status=pending` and `job_id`.
- `job wait <id> --timeout N`: waits up to N seconds for completion. Returns `status=pending` if timeout reached.
- Default `--wait` for `query` is 10 seconds. Default `--timeout` for `job wait` is 300 seconds.

Async pattern for long queries:

```bash
# Step 1: submit
aliyun maxc query "SELECT id, ds FROM target_project.my_table WHERE ds = '20260418'" --project execution_project --wait 0 --json
# Returns: { "status": "pending", "metadata": { "job_id": "<job_id>" } }

# Step 2: extract metadata.job_id and wait
aliyun maxc job wait <job_id> --json
# If still pending, retry with longer timeout:
aliyun maxc job wait <job_id> --timeout 600 --json
```

When a successful `job wait` envelope already contains `data.result`, consume
that result directly. Call `job result` only when the completed wait lacks the
requested result, another page is needed, or output must be written separately.

MCQA-specific notes:

- Offline and MaxQA / MCQA v2 async jobs keep a plain job ID such as `2026042011_abc123`.
- MCQA v1 async jobs may return a composite job ID such as `20260629075035248geajxtct4xx1@1`.
- Treat the returned job ID as opaque and pass it back unchanged to `job status`, `job wait`, `job result`, or `job diagnose`.

### Cost control and pagination

```bash
# Estimate cost before running
aliyun maxc query cost "SELECT id FROM <qualified-table> WHERE <verified-partition-filter>" --json

# Auto-abort if estimated cost exceeds threshold (in CU)
aliyun maxc query "SELECT id FROM <qualified-table> WHERE <verified-partition-filter>" --cost-check "<confirmed-threshold-cu>" --json

# Dry-run: validate and estimate without executing the SQL
aliyun maxc query "SELECT id FROM <qualified-table> WHERE <verified-partition-filter>" --dry-run --json

# Pagination
aliyun maxc query "SELECT id, name FROM <qualified-table> WHERE <verified-partition-filter>" --page-size 20 --json
aliyun maxc query "SELECT id, name FROM <qualified-table> WHERE <verified-partition-filter>" --page-size 20 --cursor "<next-cursor>" --json
aliyun maxc query "SELECT id, name FROM <qualified-table> WHERE <verified-partition-filter>" --max-rows <confirmed-page-size> --output "<new-output-path>" --json
```

Query, `job result`, and `data download` output paths reject an existing local
file unless `--overwrite` is explicitly supplied. Check the resolved path
first; use a new path or obtain authorization to replace that exact file. Each
command performs this check before remote result fetching or transfer, writes
through a same-directory temporary file, and updates the destination only after
success.

Query `--output` writes only the rows in the current envelope; it does not
change the default `--max-rows 100` or automatically collect later pages. Check
`data.pagination.has_more` and `data.pagination.next_cursor`. For complete
table or partition export within the Tunnel limits, prefer `data download`; for
an arbitrary multi-page query, combine pages into distinct or otherwise safely
managed outputs without overwriting earlier pages.

`agent context --json` includes `data.context.cost_threshold_cu` and
`data.context.allowed_operations`; respect these guardrails.

### Async jobs

```bash
aliyun maxc job submit "SELECT id FROM <qualified-table> WHERE <verified-partition-filter>" --json
aliyun maxc job status <job_id> --json
aliyun maxc job wait <job_id> --json
aliyun maxc job wait <job_id> --timeout 600 --json
aliyun maxc job wait <job_id> --stream
aliyun maxc job result <job_id> --json
aliyun maxc job result <job_id> --max-rows 50 --cursor "<cursor>" --json
aliyun maxc job diagnose <job_id> --json
aliyun maxc job cancel <job_id> --json
aliyun maxc job list --json
aliyun maxc job list --limit 50 --json
```

Use `job wait --stream` only when you want NDJSON events instead of the normal JSON envelope.

Plain successful `job wait` can already return `data.result`; do not issue a
redundant `job result` call when that envelope satisfies the request.

Before `job cancel`, verify the project and job ID with `job status`. Cancel only
the job the user identified or a job submitted in the current workflow. Ask for
confirmation only when the user's request has not already authorized the cancel.

## Multi-project access

Table-scoped metadata, data, and semantic commands accept `--project` for one-off cross-project access without switching session; `meta list-projects` is the exception:

```bash
# Target verified as 2-tier
aliyun maxc meta list-tables --project other_project --json
aliyun maxc data sample my_table --project other_project --json
aliyun maxc meta describe my_table --project other_project --json

# Target verified as 3-tier
aliyun maxc meta list-tables --project other_project --schema verified_schema --json
aliyun maxc meta describe verified_schema.my_table --project other_project --json
aliyun maxc data sample verified_schema.my_table --project other_project --json
```

Use `session set --project` only when the user wants that project to become the
persistent default for later commands:

```bash
aliyun maxc session set --project other_project --json
aliyun maxc session set --project other_project --schema my_schema --json
aliyun maxc session show --json
```

When writing SQL that references another project, use the verified `project.table` or `project.schema.table` form and follow SKILL.md's namespace rule under Safe operating rules.

## Namespace modes

Some MaxCompute projects use a three-level namespace
(`project.schema.table`); others use a two-level namespace (`project.table`).
Run `aliyun maxc meta list-schemas --json` and inspect the returned namespace
metadata or a specific unsupported-namespace error. A successful response proves
that the project supports three-level namespaces, even when the returned schema
list is empty. Treat the project as two-level only when the failure explicitly
states that it does not use the 3-tier namespace model. Permission, network, and
unfamiliar failures leave the namespace model unresolved; do not guess an
identifier shape from them.

For 3-tier projects:

```bash
aliyun maxc meta list-schemas --json
aliyun maxc meta list-schemas --project other_project --json

# List tables in a specific schema (one-shot vs sticky)
aliyun maxc meta list-tables --schema california_schools --json
aliyun maxc session set --schema california_schools --json

# Search within a schema
aliyun maxc meta search school --schema california_schools --json
aliyun maxc meta search-columns county --schema california_schools --json

# Describe (use schema.table format)
aliyun maxc meta describe california_schools.frpm --json

```

When `--schema` is given, it overrides `session set --schema`. Without either,
use a schema returned by metadata only when the CLI resolves it as the active
schema. If a 3-tier project has no resolved active schema, pass a verified
`--schema`; do not fall back to a bare table name.

## Semantic metadata

Semantic metadata enriches tables with business context for NL2SQL and agent
discovery. Build it from traceable sources such as table and column comments,
documented metric definitions, or information supplied by the user. Mark any
inference explicitly. Before `meta semantic set`, show the proposed content and
confirm the local cache mutation unless the user's original request already
authorizes that exact change. Missing semantic metadata is not, by itself,
authorization to generate or save it.

```bash
aliyun maxc meta semantic list-missing --json

# After the user confirms the source text and local cache mutation
aliyun maxc meta semantic set my_table \
  --desc "<source-grounded table description>" \
  --use-cases "<user-confirmed use case>" \
  --sample-questions "<user-confirmed sample question>" \
  --json

aliyun maxc meta semantic get my_table --json

# Verify in describe output (semantic section appears when metadata exists)
aliyun maxc meta describe my_table --json
```

## Agent context

```bash
# Show environment context (auth, backend, capabilities)
aliyun maxc agent context --json
```

`agent context` is local-only and reports configuration, guardrail, and
capability summaries without loading a provider or checking the network.
`network_checked=false`, `auth_status=incomplete`, or
`backend_reachable=null` therefore leaves remote readiness unverified; none of
these values proves that the identity or backend is invalid. Use `auth whoami
--json` for verified remote identity and MaxCompute context, and do not
reauthenticate from `agent context` alone.

## JSON contract

Most `--json` commands return an envelope shaped like:

- `version`
- `command`
- `status`
- normalized `data`
- `metadata`
- `error`
- `agent_hints`

Important normalized `data` shapes:

| Command | Path |
|---------|------|
| `query` / completed `job wait` / completed `job result` | `data.result` and `data.pagination` |
| unfinished `job wait` / `job result` | `data.job` and the command-specific job state |
| `query cost` / `query explain` | `data.analysis` |
| `auth whoami` | `data.identity` and optional `data.auth_options` |
| `auth can-i` | `data.authorization` |
| `meta describe` | `data.table` |
| `meta search` / `meta search-columns` | `data.search.matches` |
| `meta partitions` | `data.table` and `data.partitions` |
| `meta latest-partition` | `data.partition` |
| `meta freshness` | `data.freshness` |
| `data sample` | `data.sample` |
| `data profile` | `data.profile` |
| `data upload` | top-level `data` (rows_written, applied_partition, blocks, overwrite, ...) |
| `data download` | top-level `data` (rows_written, output_path, columns, truncated, ...) |
| `job status` / `job cancel` | `data.job` |
| `job diagnose` | `data.diagnosis` |
| `agent context` | `data.context` |

`session *` uses a native top-level `data` payload without an extra wrapper in
the documented command contract. Inspect the runtime envelope before relying on
individual fields.

The envelope's top-level `status` is `success`, `pending`, or `failure`. Job and
cache lifecycle states stay in their documented nested `data` fields or stream
events; do not confuse them with the envelope status, and stop on an unknown
top-level value.

`agent_hints` can include (fields are omitted when empty):

- `actions`: authoritative structured actions. Check each action's `id`,
  `executable`, `agent_allowed`, `confirmation_required`, `effect`, and
  placeholders before considering execution.
- `action_ids`: IDs of every structured action in the envelope.
- `next_actions`: compatibility command strings limited to actions that are
  executable, agent-allowed, and confirmation-free. Do not treat this list as
  more authoritative than `actions`.
- `warnings`: actionable alerts (partition auto-selection, truncation, and
  similar conditions). Inspect them even when `status=success`.
- `insights`: contextual notes about the result.

Resolve action placeholders only from verified user input or command output.
For public cloud, normalize a bare `maxc` prefix to `aliyun maxc`, preserve
quoting, add the session User-Agent for cloud calls, and never replay a
confirmation-gated write automatically.

See [json-output-format.md](json-output-format.md) for end-to-end envelope examples.

## Error handling patterns

For the full error code → recovery table, see [red-lines.md](red-lines.md) §Error Code → Recovery.

### Checking error responses

```bash
aliyun maxc query "SELECT id FROM missing_table" --json
```

Parse the returned JSON with the caller's structured-output support. Check `status` first; on failure, inspect `error.code` and `error.suggestion` before constructing a new command.

### Common error → recovery flows

```bash
# NOT_FOUND → search for the correct name
aliyun maxc meta search "partial_name" --json

# PERMISSION_DENIED → confirm the effective identity/project and exact object operation
aliyun maxc auth can-i --table your_table --operation SELECT --json

# JOB_TIMEOUT → check status and continue waiting
aliyun maxc job status <job_id> --json
aliyun maxc job wait <job_id> --timeout 600 --json

# EXECUTION_FAILED → diagnose the job
aliyun maxc job diagnose <job_id> --json

# BACKEND_CONNECTION_ERROR → inspect local context; retry remotely only after endpoint, network, or service state changes
aliyun maxc agent context --json
```

## Gotchas

- `auth whoami` performs a remote security `whoami` probe when config exists.
- `query cost` and `query explain` cannot be combined with execution-only flags such as `--wait`, `--dry-run`, `--cursor`, `--output`, or `--output-format`. They only support `table` or `json` output.
- After `meta list-projects`, use one-off `--project` arguments by default. Use `session set --project ... --json` only for a user-requested persistent default.
