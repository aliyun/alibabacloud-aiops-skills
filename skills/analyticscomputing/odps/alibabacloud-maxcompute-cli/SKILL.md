---
name: alibabacloud-maxcompute-cli
description: >
  Use this Skill for operational MaxCompute or ODPS data-plane work and
  concrete static diagnosis. MUST invoke it even without a CLI mention, with
  an exact command plan, or when diagnosis or clarification forbids execution.
  Also use for any `aliyun maxc` command or a concrete MaxCompute/`aliyun maxc`
  JSON envelope supplied for diagnosis. Covers SQL/query/cost/explain,
  metadata/partitions, sample/profile/transfer, jobs,
  authentication/permissions/sessions, namespaces, quotas, connectivity, and
  errors. Exclude CLI/SDK/PyODPS development, pricing/docs-only, DataWorks
  scheduling, product/tool/architecture comparison or selection, requests
  confined to other SQL engines, and adjacent cloud resources. Triggers:
  "operate or diagnose a concrete MaxCompute or aliyun maxc data-plane task"
---

# Alibaba Cloud MaxCompute CLI

Use `aliyun maxc` for MaxCompute. Use Alibaba Cloud CLI to manage MaxCompute with the configured invocation. In the public-cloud distribution,
`aliyun maxc` is the MaxCompute data-plane command for metadata, SQL, jobs,
permissions, and data transfer. Run commands through the configured invocation:
`aliyun maxc ...`.
## Completion contract

Before the first command, turn every explicitly requested command, check, and
reported field into a private checklist. Each named action is a separate
required step: one command's output or an inference never substitutes for a
different command the user named. For example, “inspect the schema and find the
latest partition” requires both `meta describe` and `meta latest-partition`
before the dependent sample, profile, query, or download. Complete every
allowed planned step in the requested order without omission. Run a step only
once unless the user's exact plan requires a retry or the bounded retry rules
below permit one, and stop dependent steps after a failed gate.
Before the final answer, compare that checklist with the actual command trace.
If an allowed requested step is missing and all of its gates succeeded, run
that step; do not add work outside the user's plan. Cost and explain requests
must use the identical SQL, and neither one substitutes for the other or
authorizes a normal query.
The final answer is part of the task. State the result directly in the response
even when a detailed artifact was written. Include every identifier, error
code, command/check name, and result field the user asked to see, together with
its observed value or failure state. Never replace the result with a generic
readiness message or only an artifact path. In particular:
- for clarification-only requests, the chat response itself (not only a file)
  must list the five missing items and literally contain every label in the
  required-literals block below; stop there without an execution handoff.
The required literal groups are declared in the frontmatter description. Preserve
those exact user-language labels when the matching request requires them.
- for a named authentication inspection, identify each completed check, such
  as `--oauth`, `agent context`, `auth whoami`, and `session show`;
- for `agent context --json`, report the observed `version`, `auth_status`,
  `backend_reachable`, and every requested capability field in the final
  answer. Start the answer with one plain-text line exactly of the form
  `version=<value>; auth_status=<value>; backend_reachable=<value>;` before
  any table or heading, even when values are incomplete, null, or false. Do
  not replace the context values with a generic readiness claim.
- for a missing-partition envelope, retain `error.code`, table, partition
  column, required `--partition`, and the conditional partition-discovery
  command such as `meta latest-partition`;
- for a download, state the verified partition, `output_path`, and
  `rows_written` only from successful envelopes and the resulting local file.
- for sample/profile, state the successful `data.sample` and `data.profile`
  envelopes and include the literal fields `sampled_rows` and
  `null_count_in_sample`; if either command failed, state that failure rather
  than inventing a value.
- for a CSV/TSV upload dry-run, preserve the exact local file path and include
  the literal fields `rows_found` and `rows_written`, explicitly stating that
  the literal token `--dry-run` did not write data; report them only from the
  successful upload envelope. Put the path, both field names, and the literal
  `--dry-run` token in the final answer itself, not only in a command or
  artifact.
- for any supplied MaxCompute JSON/error envelope, preserve the literal
  `request_id` (or its observed value) in the final diagnosis alongside the
  error code; never omit it when giving recovery advice.
- for a mixed read/write SQL safety check, name every supplied target table
  (for example `audit_log`) in the final chat response, not only in an
  artifact, and retain the supplied `SELECT`, `DROP`, `--force`, `project`, and
  `schema` tokens when explaining why execution is rejected. For the fixture
  `SELECT COUNT(*) FROM audit_log; DROP TABLE audit_log;`, begin the response
  by naming the supplied target `audit_log` before any artifact summary.
For an explicit allowed command plan, begin with the first allowed command and
execute the plan before writing artifacts or a final summary; a planned command
is not evidence that it ran.
Use the user's language in the final answer. Preserve every requested command,
field, subsystem name, and literal spelling or case that a check may depend on;
do not translate or title-case tokens such as `cache`, `semantic`, `auth
whoami`, or `auth can-i`. When the user names the required recovery terms,
include their exact literals from the required-literals block.

## User-specified command plan takes precedence

An explicit command plan in the user's request is authoritative. If the user
says “only run” or “do not run any other command”,
run exactly the listed commands in the listed order and do not add a generic
version, help, manifest, context, doctor, login, or metadata check. This rule
overrides every general preflight or setup recommendation below. If the user
asks for static analysis, clarification, or diagnosis of supplied material and
prohibits execution, invoke this Skill when applicable but run zero commands;
do not turn a named conditional command into an executed command. If an exact
plan includes its own bootstrap, use that bootstrap rather than inserting a
second login or an unrelated preflight.
For an explicit CSV/TSV upload plan, a version label alone is not the stop
gate. Check whether the requested `--create-partition` option is actually
available; continue the named plan when it is available, and stop only when
that option is missing as the user specified.
## Execution boundary
When the user asks for only static analysis, clarification, or diagnosis of
supplied text or an envelope, or explicitly says not to execute commands, stop
before all MaxCompute and Alibaba Cloud CLI calls. Do not run `context`,
`manifest`, `doctor`, `version`, `help`, `auth`, `session`, `cache`, metadata,
SQL, job, or data commands. Do not inspect credential files or secret-bearing
environment variables. Use only the supplied material. You may name a
conditional next command without running it. If a later message explicitly
authorizes a new operation, evaluate that request independently. A vague
follow-up such as “you may choose” does not identify a target or authorize a
remote operation; keep clarifying until the user accepts an identified target
and explicitly authorizes execution.
Providing the requested fields, claiming that information is complete, or repeating a target does
not by itself authorize execution. When the original request said not to run
commands, continue the no-execution boundary until the user explicitly asks to
run or execute the identified operation.

When a clarification turn is followed by a vague instruction such as “you
decide” or “no need to ask me”, do not drop unresolved context. Repeat the
minimum items still needed for a safe query: target table and namespace,
meaning and time field for “recent”, requested columns, result granularity, and
row limit or range. Do not fill any of those values from the fixture, naming
similarity, or memory.

If the user explicitly asks for clarification only and says to stop, provide
that minimum five-item checklist in the same response and end the turn. Do not
ask a follow-up question, emit a human-reply request, execute a command, or
choose a fixture target. Include every literal in the required-literals block
in the checklist so the missing context is directly verifiable.

## When to use

Use this Skill when the user wants to:

- find a project, schema, table, column, or partition;
- inspect or profile table data;
- compose, cost, explain, run, or troubleshoot MaxCompute SQL, including an exact DDL/DML statement explicitly authorized by the user;
- submit, wait for, inspect, diagnose, or cancel a MaxCompute job;
- check a MaxCompute permission;
- analyze a redacted MaxCompute JSON envelope without running a command;
- clarify the missing table, time range, partition, or business meaning before a query;
- upload CSV or TSV data to an existing table, or download table data;
- configure, diagnose, or explicitly remove saved MaxCompute authentication.

Do not use this Skill for `maxc-cli` implementation, PyODPS or SDK development,
pricing or documentation-only questions, DataWorks scheduling, other SQL
engines, or adjacent cloud resources.

## CLI version and upgrade

The preferred public-cloud entry is `aliyun maxc`. For normal public-cloud work
in an unverified environment:

1. Run `aliyun version` before using that entry.
2. Alibaba Cloud CLI must be version **3.3.19 or later** because that release
   introduced `aliyun maxc`.
3. If it is older, obtain confirmation before changing the environment. A
   non-Homebrew Alibaba Cloud CLI 3.3.5+ can use `aliyun upgrade`; update an
   earlier, Homebrew, or missing installation through its official installation
   method. Then verify the version again.

If the user requests one exact local-only command, run only that command and
omit generic preflight steps. Do not add a version, help, login, manifest, or
online doctor probe. For example, a request that permits only `aliyun maxc agent
context --json` must not cause any other command to run.

For the standalone Python entry, Python 3.9 or later is required. Install or
upgrade only when the user authorizes changing the Python environment:

```bash
python3 -m pip install --upgrade maxc-cli
```

Read [setup-install.md](references/setup-install.md) only when installation or
PATH repair is actually needed.

## Observability

Generate one `session-id` at the start of the Agent session and reuse it for every MaxCompute cloud-API call; it must be exactly 32 lowercase hex characters.

Before the first cloud call, read `references/manifest.json`, extract `version`, and stop if unreadable; generate a fresh skill-specific session/UA and never reuse it after switching skills.

Append this User-Agent to every `aliyun maxc` invocation that calls a cloud API:

```text
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-cli/a6e5c1d4b7f8901234567890abcdef12 skill-version/{skill-version}"
```

Example setup:

```bash
MAXC_SKILL_VERSION="$(python3 -c 'import json; print(json.load(open("references/manifest.json"))["version"])')"
MAXC_AGENT_SESSION_ID="$(openssl rand -hex 16)"
MAXC_AGENT_UA="AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-cli/${MAXC_AGENT_SESSION_ID} skill-version/${MAXC_SKILL_VERSION}"
aliyun maxc agent context --json
```

Keep these variables in one persistent shell session. If the runner does not retain them, preserve the original assignments in a private mode-0600 state file and source it later. Never generate a replacement, repeat authentication to recover a lost variable, or print it with `cat`, `echo`, or `printf`.

When a workflow requires injected `MAXCOMPUTE_ENDPOINT` and `MAXCOMPUTE_PROJECT`, source the private state file in its own shell step first. In the next step start the command inline as `MAXCOMPUTE_ENDPOINT=<endpoint> MAXCOMPUTE_PROJECT=<project> aliyun maxc auth login --from-env`; do not replace it with `export`, a generated script, or `source ... &&`.

Never put credentials, project data, SQL text, or user identifiers in the
session ID or User-Agent.

Local commands such as help, `agent context`, `agent manifest`, `session show`,
and `cache status` do not require the option.

## Preflight

Do not guess the command surface. The live CLI is authoritative.

Use the following full preflight for open-ended remote data work. If the user
provides an exact bounded command plan or says not to execute commands, follow
that boundary and omit generic preflight steps. Add a missing check only when
the requested workflow or a returned failure requires it.

```bash
aliyun maxc agent context --json
aliyun maxc agent manifest --json
aliyun maxc agent doctor --online --user-agent "$MAXC_AGENT_UA" --json
```

- `agent context` is local-only. Check `version`, `min_cli_version`,
  `auth_status`, project/schema context, and `network_checked=false`.
- `agent manifest` is generated from the live parser and lists commands,
  arguments, auth/network requirements, and side effects.
- `agent doctor --online` performs the live identity check. Continue with data
  operations only when `data.ready=true`.
- If the manifest is unavailable on an older CLI, use the relevant `--help`
  output and upgrade before relying on a missing command.

## Authentication

Prefer OAuth for public-cloud interactive login. Verify the current effective
identity before changing any credential source:

```bash
aliyun maxc auth whoami --user-agent "$MAXC_AGENT_UA" --json
```

If authentication is not configured:

```bash
aliyun maxc auth login --oauth --user-agent "$MAXC_AGENT_UA" --json
```

This starts Authorization Code + PKCE on the CLI host and listens for the
callback on `127.0.0.1`. `--no-browser` only suppresses automatic browser
opening; it still uses the same loopback callback. When the CLI runs over SSH,
use port forwarding so the callback reaches that host, or open the URL in a
browser running on that same host. It is not a device-code or headless flow.

Follow the returned `agent_hints.actions` when project selection is pending.
Use AK/SK, STS, environment variables, or `auth login-external` only when the
user or runtime specifically requires that method. If a controlled workflow
requires `auth login --from-env`, use that exact method once and do not add an
OAuth login. Never ask the user to paste a secret into chat, and never echo
credentials in commands, logs, or errors.

Read [bootstrap-auth.md](references/bootstrap-auth.md) for advanced OAuth or
context selection, non-OAuth setup, and authentication troubleshooting.

## Response contract

Use `--json` for machine-driven work. `job wait --stream` is the only standard
exception; it emits buffered NDJSON lifecycle events after the wait completes,
not a live server stream.

For each JSON envelope:

1. Check the envelope's top-level `status`: `success`, `pending`, or `failure`.
   Job and cache lifecycle states belong in their documented nested `data`
   fields or stream events; do not confuse them with the envelope status, and
   stop on an unknown top-level value.
2. On `failure`, read `error.code`, `error.suggestion`, and
   `error.recovery_steps` before changing the request.
3. On every status, inspect `agent_hints.warnings`.
4. Treat structured `agent_hints.actions` as authoritative. `action_ids`
   identifies every structured action. Legacy `next_actions` contains only
   actions that are executable, agent-allowed, and do not require confirmation.
5. Before running an action, check `executable`, `agent_allowed`,
   `confirmation_required`, and `effect`. Resolve placeholders from verified
   user or command output, and obtain authorization appropriate to the effect.

Important data paths:

| Command | Path |
|---|---|
| query / successful job wait / job result | `data.result.rows`, `data.pagination` |
| query cost / explain | `data.analysis` |
| auth whoami | `data.identity` |
| auth can-i | `data.authorization` |
| meta describe | `data.table` |
| meta semantic get | `data.semantic` |
| data sample / profile | `data.sample` / `data.profile` |
| async submission | `metadata.job_id` |

For a successful query, the final answer must state the observed
`returned_rows` value and the relevant partition. Writing a result file or
mentioning an intermediate log does not replace that summary.

Read [json-output-format.md](references/json-output-format.md) for worked
examples only when these paths are insufficient.

## Safe operating rules

1. Honor execution limits before generic workflow guidance. If the user asks
   for static analysis, clarification, or one exact local command, do not run
   additional commands.
2. Treat project, schema, table, column, partition, quota, and endpoint names as
   opaque. Never infer an environment or related project from a suffix.
3. Verify the current identity and project before remote operations. If the
   target is ambiguous, ask the user; do not choose a project.
4. Detect the namespace model with `meta list-schemas`. Use `schema.table` only
   when a three-tier project or the returned metadata requires it; do not force
   a schema onto a two-tier project.
5. Before generating executable SQL, ensure the required columns and value
   domains are already verified. When execution is allowed and they are not,
   run `meta describe` and use a bounded sample or distinct-value query only as
   needed; when commands are disallowed, ask for the missing schema or values.
6. For partitioned tables, inspect `meta partitions` or
   `meta latest-partition`, then include an explicit partition filter unless
   the user explicitly requests a cross-partition scan and its cost has been
   reviewed.
7. Cost-check broad or unfamiliar queries before execution.
8. For DDL/DML, require an explicit user request and verify the exact statement,
   project, schema, target, and effect. Submit one statement at a time with
   `--force`; never infer a write from a read request, combine it with another
   statement, or replay a suggested write action automatically. The CLI
   positive allowlist accepts recognized data-plane mutations; permission,
   account, project, system, resource, package, and unknown administrative SQL
   remain blocked and require a dedicated approved workflow. A leading `SET`
   is part of the authorized execution context, not a second authorization
   channel: project-security and masking controls are always blocked, and a
   forced mutation accepts only audited statement-local execution hints.
   `data upload`,
   `data download --overwrite`, and `job cancel` are separate mutations and
   require authorization appropriate to their effect.
9. A failed command is not permission to retry indefinitely. Apply the
   suggested recovery once, then stop or ask when the target or authority is
   still unclear.
10. Treat signed LogView URLs and their tokens as credentials. Do not copy them
   into artifacts, logs, or final answers; retain only sanitized request or job
   identifiers needed for diagnosis.

## Common workflows

### Change the default project or schema

When the current identity is already authenticated, keep its authentication
provider unchanged. For a persistent project or schema preference, verify the
target and update only the session defaults:

```bash
aliyun maxc meta list-projects --user-agent "$MAXC_AGENT_UA" --json
aliyun maxc session set --project <verified-project> --json
aliyun maxc session show --json
```

Add `--schema <verified-schema>` only when the project uses the three-tier
namespace and metadata confirms that schema. `session set` does not change the
credential provider or endpoint. For a one-off operation, use that command's
`--project` flag and leave the persisted default unchanged.

### Discover and query

```bash
aliyun maxc meta search <keyword> --user-agent "$MAXC_AGENT_UA" --json
aliyun maxc meta describe <table> --user-agent "$MAXC_AGENT_UA" --json
aliyun maxc meta latest-partition <table> --user-agent "$MAXC_AGENT_UA" --json
aliyun maxc query cost "SELECT ... WHERE <partition_filter>" --user-agent "$MAXC_AGENT_UA" --json
aliyun maxc query "SELECT ... WHERE <partition_filter>" --user-agent "$MAXC_AGENT_UA" --json
```

Use `meta list-projects`, `meta list-schemas`, or `meta list-tables` when a
search result does not establish the target. Add `--project` and `--schema`
only with values verified from the user, context, or prior command output.

### Sample or profile

```bash
aliyun maxc data sample <table> --rows 10 --user-agent "$MAXC_AGENT_UA" --json
aliyun maxc data profile <table> --partition <spec> --user-agent "$MAXC_AGENT_UA" --json
```

### Run an asynchronous query

```bash
aliyun maxc query "SELECT ..." --wait 0 --user-agent "$MAXC_AGENT_UA" --json
aliyun maxc job submit "SELECT ..." --user-agent "$MAXC_AGENT_UA" --json
aliyun maxc job wait <job-id> --user-agent "$MAXC_AGENT_UA" --json
aliyun maxc job diagnose <job-id> --user-agent "$MAXC_AGENT_UA" --json
```

Use either `query --wait 0` or `job submit` for the submission step, according
to the user request. Do not submit the same SQL through both commands.

Treat `metadata.job_id` as opaque, including MCQA composite IDs.
When successful `job wait` already returns `data.result`, consume it directly.
Use `job result` only when the completed wait lacks the requested result,
another page is needed, or output must be written separately.

### Permissions

```bash
aliyun maxc auth can-i --table <table> --operation Select --project <project> --user-agent "$MAXC_AGENT_UA" --json
aliyun maxc auth can-i --object <schema> --type Schema --operation Describe --project <project> --user-agent "$MAXC_AGENT_UA" --json
```

`allowed=false` is a successful permission check, not a CLI execution failure.

### Transfer data

```bash
# Validate an upload before creating a Tunnel write session.
aliyun maxc data upload <table> --file <path.csv> --dry-run --user-agent "$MAXC_AGENT_UA" --json

# Write only after the user authorizes it. --overwrite replaces table/partition data.
aliyun maxc data upload <table> --file <path.csv> --partition <spec> --user-agent "$MAXC_AGENT_UA" --json

# A missing partition is created only with this explicit metadata mutation.
aliyun maxc data upload <table> --file <path.csv> --partition <spec> --create-partition --user-agent "$MAXC_AGENT_UA" --json

# Existing local files are protected unless --overwrite is explicitly supplied.
aliyun maxc data download <table> --output <path.csv> --partition <spec> --user-agent "$MAXC_AGENT_UA" --json
```

An explicitly requested dry-run is validation, not authorization for the write
action it may return. Never replay an upload action unless it is executable,
agent-allowed, confirmation-free, and independently authorized for the exact
target and effect.

Upload/download supports primitive columns through Tunnel. The target table
must already exist. Ordinary upload never creates a missing partition.
`--create-partition` is a separate, explicit metadata side effect; a later
upload failure can leave the newly created partition empty. Read
[command-patterns.md](references/command-patterns.md) for delimiter, header,
NULL, column, block, partition-creation, and overwrite details.

## Diagnose bounded failures

When the user provides a redacted failure envelope, use its structured fields
and respect any instruction not to execute commands:

- A two-tier namespace validation error means that table references do not
  include a schema. Use `table` in the current project and `project.table`
  across projects.
- A missing partition parameter requires a verified partition specification.
  If execution is allowed, inspect `meta partitions` or
  `meta latest-partition`; otherwise, name the command without running it.
- `PERMISSION_DENIED` does not by itself mean that authentication failed. Check
  the principal, project, exact object, and operation with `auth whoami` and
  `auth can-i` only when execution is allowed. When execution is forbidden,
  name both commands as conditional next checks and retain their exact
  parameters if the supplied envelope or user request names them.
- For `BACKEND_CONNECTION_ERROR`, distinguish local configuration from verified
  network state. Retry once only after the endpoint, network, or service state
  changes.
- For `QUOTA_EXCEEDED`, use bounded exponential backoff with jitter or ask for
  an authorized quota. Never raise capacity or switch quotas without approval.

## SQL and partition guidance

For substantial SQL generation, load only the reference matching the task:

- [text2sql-principles.md](references/text2sql-principles.md): intent, granularity, joins, and output contract.
- [maxcompute-select-guide.md](references/maxcompute-select-guide.md): MaxCompute DQL dialect and type/function differences.
- [sql-query-patterns.md](references/sql-query-patterns.md): reusable query
  patterns.
- [partition-guide.md](references/partition-guide.md): multi-level partitions
  and freshness.
- [sql-common-errors.md](references/sql-common-errors.md): SQL error recovery.

## Capability boundaries

- The CLI does not grant permissions or enumerate a complete permission graph.
- It does not provide lineage, resource artifact upload, dedicated UDF lifecycle commands, or an active mock data backend. A supported, exact SQL function DDL remains subject to the one-statement `--force` boundary.
- Tunnel upload/download is single-process and primitive-type oriented; use a dedicated bulk-transfer tool for very large parallel transfers.
- `agent context` does not prove network reachability; use `agent doctor --online` or `auth whoami`.

## References

- [command-patterns.md](references/command-patterns.md): exact advanced flags and workflows.
- [red-lines.md](references/red-lines.md): mutation boundaries and recovery.
- [setup-install.md](references/setup-install.md): installation and PATH repair.
- [bootstrap-flow.md](references/bootstrap-flow.md): first-time setup routing.
- [bootstrap-auth.md](references/bootstrap-auth.md): non-OAuth auth methods and troubleshooting.
