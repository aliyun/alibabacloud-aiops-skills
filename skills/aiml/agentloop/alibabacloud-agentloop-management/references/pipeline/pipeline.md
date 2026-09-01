# AgentLoop Pipeline Skill

> **Domain entry**: this file is the Pipeline-domain playbook dispatched from the router SKILL.md of `alibabacloud-agentloop-management`. All file paths below are relative to the skill root.

## Scenario

Create and inspect AgentLoop Pipelines through the Aliyun CLI plugin
(`aliyun-cli-agentloop`). This domain turns natural-language Pipeline requests
into explicit JSON specs, checks those specs against local references, and uses a
small safety wrapper for guarded creation.

The scope is intentionally narrow:

- Wrapper commands: `doctor`, `preview`, and `create`
- Wrapper cloud calls: `create-pipeline` and `preview-pipeline`, both driven from
  one spec file
- Raw CLI guidance: all read, run, lifecycle, and destructive Pipeline
  operations
- Node references: used for create-spec JSON shape and shallow validation
- Operator references: internal SPL semantics reference for precise node
  understanding. SPL is never surfaced: not in user-facing output, not in
  create-spec JSON, not in `pipeline.nodes[].parameters`

**Architecture**: `Aliyun CLI >= 3.3.3 + aliyun-cli-agentloop 0.7.4 + AgentLoop
API 2026-05-20 + Python 3.8+ standard library`.

## CLI Prerequisites

Pre-check the Aliyun CLI:

```bash
aliyun version
```

The version must be `>= 3.3.3`. For a first install or major upgrade, download
and review the official setup script before executing it. Do not use `curl |
bash`. For routine updates on newer CLI versions, prefer:

```bash
aliyun upgrade
```

Enable plugin installation and update plugins:

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

Verify AgentLoop support:

```bash
aliyun plugin show --name aliyun-cli-agentloop
aliyun agentloop version
aliyun agentloop create-pipeline --help
```

Do not install or upgrade plugins inside this skill unless the user explicitly
approves that environment change.

## Script Dependencies

The bundled wrapper `scripts/pipeline/agentloop_pipeline.py` uses only Python
3.8+ standard library modules. No package installation is required.

## Environment

| Variable | Required | Description |
|---|---:|---|
| `SKILL_DIR` | Recommended | Absolute path to this skill directory (containing `SKILL.md`) |
| `ALIBABA_CLOUD_PROFILE` | Optional | Scope CLI calls to a named profile without changing the default |
| `SKILL_SESSION_ID` | Optional | 32-character lowercase hex session ID for User-Agent observability |

Resolve `SKILL_DIR` from the loaded skill path when available:

```bash
export SKILL_DIR="/absolute/path/to/alibabacloud-agentloop-management"
test -f "$SKILL_DIR/scripts/pipeline/agentloop_pipeline.py"
```

When multiple Aliyun profiles exist, prefer scoping the workflow:

```bash
export ALIBABA_CLOUD_PROFILE=<profile-name>
```

If the user supplies a profile, such as `miniwan`, preserve that exact profile
for source discovery, Pipeline mutation, run inspection, Dataset readback, and
credential checks. Never silently fall back to the default profile. The wrapper
inherits `ALIBABA_CLOUD_PROFILE`; raw CLI commands must carry the same profile
through the supported CLI mechanism.

## Authentication

Credentials are required for cloud API calls.

Security rules:

- Never read credential files.
- Never echo AccessKey, secret, token, authorization, or password values.
- Never ask the user to paste AK/SK into the conversation.
- Never run `aliyun configure set` with literal credential values.
- Use only the CLI's status output to check credential presence.

Check authentication state:

```bash
aliyun configure list
```

If no valid AK, STS, OAuth, or configured profile is present, stop and ask the
user to configure credentials outside this session, then rerun checks.

## RAM Permissions

Pipeline operations use the concrete AgentLoop RAM actions listed in
[references/pipeline/ram-policies.md](ram-policies.md). Do not use a wildcard
action pattern in a policy.

On any permission failure:

1. Capture the API action, denied RAM action, and request ID without exposing
   credentials.
2. Read [references/pipeline/ram-policies.md](ram-policies.md).
3. If `ram-permission-diagnose` is installed, invoke it. Otherwise show the
   missing action and the least-privilege policy template.
4. Pause until the user confirms that permission was granted before retrying.

## Parameter Confirmation

Before executing any cloud API call, confirm all user-specific parameters. Do
not invent defaults for resources, time windows, data scopes, datasets, model
nodes, or lifecycle targets.

| Parameter | Required | Notes |
|---|---:|---|
| AgentSpace | Yes | Target AgentLoop workspace |
| Region | Yes for wrapper create | CLI endpoint region, for example `cn-hangzhou` |
| Pipeline name | Yes | 3-63 lowercase letters, digits, hyphens. No underscores. Dataset names use the opposite rule; see the resource-name table in the router `SKILL.md` |
| Source project/logstore/query | Yes for create/preview/run design | `*` is allowed only after being shown clearly |
| Time window | Required for RunOnce, preview, manual run | Use timezone-bearing ISO-8601 or Unix seconds |
| Sink dataset | Yes for create | Only the dataset sink is supported |
| Execute policy | Yes for create | `run_once` or `scheduled` |
| Scheduled interval | Required for Scheduled | Requires `--allow-scheduled` |
| AI nodes | Optional | Show cost warning for `llm-call` or `agentic-call` |
| Global dedup | Optional | Show global state warning when `global=true` |
| Output contract | Yes for Dataset materialization | Freeze every required raw, derived, and lineage field before preview |

For trace-derived evaluation or experiment data, preserve raw `input`, raw
`output`, and stable lineage beside any derived `question`. A normalized field
is a convenience, not a substitute for source evidence. Read
[references/pipeline/nodes-and-expressions.md](nodes-and-expressions.md) for the
raw-preserving extraction pattern and test cases. Do not print real conversation
bodies during preview or verification; report field presence, counts, hashes,
and redacted samples.

## Observability

Generate one 32-character lowercase hex session ID for the skill session and
reuse it for every command. Use it as `{session-id}`.

Every `aliyun agentloop` cloud API command must include:

```bash
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-management/{session-id}"
```

Local utility commands such as `aliyun version`, `aliyun configure`, and
`aliyun plugin` do not need this flag.

The bundled wrapper injects `--user-agent` into its cloud API commands. To make
the ID stable across wrapper calls, run:

```bash
SKILL_SESSION_ID={session-id} python3 "$SKILL_DIR/scripts/pipeline/agentloop_pipeline.py" create --spec pipeline.json
```

## Confirmation Protocol

Cloud mutations and processing operations must not run silently.

### No confirmation needed

Local and read-only operations:

- `doctor`
- `preview` without `--execute` (stops at CLI dry-run, reads no source data)
- `aliyun version`
- `aliyun configure list`
- `aliyun plugin show`
- `get-pipeline`
- `list-pipelines`
- `get-pipeline-run`
- `list-pipeline-runs`
- `get-pipeline-stats`

### Confirmation required

Processing or mutation operations:

| Operation | Risk |
|---|---|
| `create-pipeline` | Creates persistent Pipeline resource |
| `update-pipeline` | Replaces supplied configuration blocks |
| `preview-pipeline` | Reads source data and executes nodes; can incur AI cost |
| `run-pipeline` | Starts a processing run |
| `pause-pipeline` | Changes schedule lifecycle |
| `resume-pipeline` | Changes schedule lifecycle |
| `terminate-pipeline` | Stops Pipeline permanently or semi-permanently depending on service behavior |
| `cancel-pipeline-run` | Cancels a pending run |
| `delete-pipeline` | Deletes a resource |

### Three-step protocol

1. Preview the exact target, command, payload, data scope, schedule, AI nodes,
   global dedup, destination, and likely cost.
2. Ask for explicit user approval. Silence or "looks ok" in earlier discussion
   is not execution approval.
3. Execute exactly one named operation only after approval.

For wrapper create, always run without `--execute` first:

```bash
python3 "$SKILL_DIR/scripts/pipeline/agentloop_pipeline.py" create --spec /path/to/pipeline.json
```

Only after the user approves, run:

```bash
python3 "$SKILL_DIR/scripts/pipeline/agentloop_pipeline.py" create --spec /path/to/pipeline.json --execute
```

Add `--allow-scheduled` for both preview and execution when the spec uses
Scheduled mode.

## Core Workflow

### 1. Check the environment

Run local checks:

```bash
python3 "$SKILL_DIR/scripts/pipeline/agentloop_pipeline.py" doctor
```

Add `--agent-space` only when the user wants a read-only access check:

```bash
python3 "$SKILL_DIR/scripts/pipeline/agentloop_pipeline.py" doctor --agent-space <space> --region <region>
```

If the plugin/API version differs from this domain's architecture line, inspect
the affected command help before composing payloads.

### 2. Select the workflow

Use wrapper `create` when the user wants to create a Pipeline from a spec.

Use raw CLI when the user wants to:

- list or inspect Pipelines
- inspect runs or stats
- preview processing
- trigger a manual run
- update an existing Pipeline
- pause or resume scheduling
- cancel, terminate, or delete anything

Add wrapper commands only when they combine multiple CLI calls or add
guardrails. Keep simple read-only operations as raw CLI.

### 3. Compose a create spec

Read [references/pipeline/spec-format.md](spec-format.md) before composing or
changing a spec.

For node choice and parameter shape:

1. Read [references/pipeline/nodes/OVERVIEW.md](nodes/OVERVIEW.md) for API node
   JSON examples.
2. Load only selected `references/pipeline/nodes/<node>.md` files for parameter
   names, required fields, defaults, and output columns.
3. Read [references/pipeline/operators/OVERVIEW.md](operators/OVERVIEW.md) or
   selected operator files when the task needs precise SPL-layer semantics or
   implementation behavior. Use them only to understand nodes, never as
   user-facing output or JSON syntax.
4. Use [references/pipeline/trace/ot-ai-collection-spec.md](trace/ot-ai-collection-spec.md)
   only for OT AI trace field mapping.
5. Prefer installed CLI help and dry-run payload casing over documentation
   examples.

For OT-AI trace sources (any LogStore whose spans carry `gen_ai.*` attributes),
you MUST strictly follow
[references/pipeline/trace/ot-ai-trace-recipe.md](trace/ot-ai-trace-recipe.md).
Do not compose the node chain from intuition, do not skip steps, and do not
paste SPL from unrelated examples. The recipe's four-step methodology is
mandatory:

1. Sample raw traces with the aliyun CLI using an existing profile. Prefer the
   installed `alibabacloud-sls-cli-guidance` skill to query SLS. Do not use SLR
   or the SLS SDK.
2. Analyze span-kind distribution, parent/child links, and per-kind `gen_ai.*`
   attributes directly from the sample. Note truncation and NULL rates. Confirm
   the derived understanding with the user before moving on.
3. Derive a target field-mapping table (target column -> type -> source span kind
   -> extraction expression). Compose nodes with the OT-AI SPL recipes
   (per-span-kind CASE WHEN preprocess, nested `json_extract_scalar`,
   multi-source fallback). Use CLI casing throughout; `where` uses `filter`,
   not `condition`.
4. Validate with wrapper `create` dry-run (step 4) and then wrapper `preview`
   (step 5) before any real create. Both are required, not optional.

Deviations from the recipe require explicit user consent recorded in the
conversation and a note in the spec's `description` field.

Supported node types:

`project`, `extend`, `where`, `limit`, `make-instance`, `dedup-exact`,
`dedup-fuzzy`, `dedup-semantic`, `embedding`, `doc-stats`,
`semantic-cluster`, `sample`, `llm-call`, `agentic-call`.

Reject `ai-gen` and recommend `llm-call`. Reject `make-conversation`.

### 4. Preview create

Run the wrapper without `--execute`:

```bash
python3 "$SKILL_DIR/scripts/pipeline/agentloop_pipeline.py" create --spec /path/to/pipeline.json
```

The wrapper validates the JSON, builds the CLI 0.7.4 payload, prints a redacted
summary, and calls `create-pipeline --cli-dry-run true`. It does not create a
Pipeline.

Inspect and summarize these fields for the user:

- AgentSpace and Region
- Pipeline name
- Source project, LogStore, query
- RunOnce window or Scheduled interval
- Node list
- AI-node warning
- global-dedup warning
- sink dataset

### 5. Validate SPL semantics with `preview` (required)

Wrapper dry-run only checks payload shape and casing. It does NOT validate that
the SPL expressions inside each node actually run against the target LogStore.
Between dry-run and real creation, preview the same spec on a bounded time
window to confirm the node chain executes end-to-end and outputs the expected
columns. Skip only for trivial specs already proven on the same LogStore
schema.

Use the wrapper, which reads the same `pipeline.json` and derives `--source` and
`--pipeline` from it:

```bash
python3 "$SKILL_DIR/scripts/pipeline/agentloop_pipeline.py" preview \
  --spec /path/to/pipeline.json \
  --from-time <window-start> \
  --to-time <window-end> \
  --execute
```

`--from-time` and `--to-time` accept Unix seconds or timezone-bearing ISO-8601
and are always required: preview must not silently inherit the spec's RunOnce
window. Without `--execute` the wrapper stops at CLI dry-run and reads no source
data. With `--execute` it performs the real preview, and when the spec contains
an AI node it first requires the Pipeline name on stdin because the run is
billed per row. Add `--allow-scheduled` for a Scheduled spec.

Do not hand-assemble the raw `preview-pipeline` command from the spec. The
wrapper passes each JSON blob as one argv element with no shell involved, which
avoids the quoting failure described under "Preview processing" below.

Before running it:

- Bound the window to a few minutes; a 5-minute window on an active LogStore is
  usually enough to return the default 5 sample rows. The wrapper warns above 15
  minutes.
- Warn on cost: SLS scan bytes plus AI-node cost if the spec contains
  `llm-call` or `agentic-call`.
- Prefer a window that overlaps a recently committed watermark of a related
  Pipeline (from `get-pipeline-stats`) so the window is guaranteed to contain
  data.

`preview` is a confirmation-required operation: it reads real source data and
executes nodes. Follow the three-step protocol.

The wrapper prints a `column_check` verdict comparing the returned `meta.keys`
against the columns declared by the last `project` node. `"ok": false` with a
populated `missing` list means a column never materialized: look for a
misspelled aggregator, a WHERE that dropped every row, or a NULL upstream
extraction. Fix the spec, re-run wrapper dry-run, then preview again before
proceeding. `extra` lists returned columns that the output `project` does not
declare, such as `__time__`, and is informational. The verdict is skipped when
the spec has no `project` node or the response shape is unrecognized; read
`data[]` and `meta.keys` manually in that case.

### 6. Execute create

After explicit approval:

```bash
python3 "$SKILL_DIR/scripts/pipeline/agentloop_pipeline.py" create --spec /path/to/pipeline.json --execute
```

For Scheduled mode:

```bash
python3 "$SKILL_DIR/scripts/pipeline/agentloop_pipeline.py" create --spec /path/to/pipeline.json --allow-scheduled --execute
```

The wrapper requires the Pipeline name to be typed into stdin before the real
create call.

Treat RunOnce creation as write-capable because it may schedule its run
asynchronously. Go straight to step 7 and inspect the stored Pipeline and run
history. Do not call `run-pipeline` again merely because the create response has
`lastRunId` null or one immediate run-list response is empty; poll `list-pipeline-runs` over a bounded observation window. If no run appears before
timeout, mark execution state `ambiguous` and do not use a manual run as the
fallback. A late automatic run and a manual fallback can both write the same
source window, while `run-pipeline` has no client token to prevent duplicate
business rows.

### 7. Inspect results

Use raw read-only CLI:

```bash
aliyun agentloop get-pipeline \
  --agent-space <space> \
  --pipeline-name <name> \
  --region <region> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-management/{session-id}"
```

For runs:

```bash
aliyun agentloop list-pipeline-runs \
  --agent-space <space> \
  --pipeline-name <name> \
  --region <region> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-management/{session-id}"
```

`list-pipeline-runs` returns the run array in the top-level `runs` field. When
using `--cli-query`, query `runs`, not `pipelineRuns`. A wrong JMESPath can
silently return `null`; do not interpret `null` as "no run records" until the raw
response shape has been checked.

When a run appears, monitor it with `get-pipeline-run`; do not call
`run-pipeline` again. A successful run is transport evidence, not Dataset
acceptance. Read back the target Dataset and reconcile the selected source set,
required `input`/`output`/`question` and lineage fields, empty values,
duplicates, transforms, and query truncation. Use
[references/pipeline/verification-method.md](verification-method.md). If the
source oracle or field completeness cannot be checked, report
`insufficient_evidence` instead of declaring the import correct.

## Raw CLI Recipes

### Read-only

List Pipelines:

```bash
aliyun agentloop list-pipelines \
  --agent-space <space> \
  --region <region> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-management/{session-id}"
```

Get one Pipeline:

```bash
aliyun agentloop get-pipeline \
  --agent-space <space> \
  --pipeline-name <name> \
  --region <region> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-management/{session-id}"
```

Get stats:

```bash
aliyun agentloop get-pipeline-stats \
  --agent-space <space> \
  --pipeline-name <name> \
  --region <region> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-management/{session-id}"
```

### Preview processing

Prefer the wrapper `preview` subcommand (Core Workflow step 5). It reuses the
spec file, so `--source` and `--pipeline` never have to be rebuilt by hand. Reach
for the raw command only when there is no spec file, for example when trying a
node chain that has not been written down yet. This is not CLI dry-run.

A wrapper call that times out, or that reports the `aliyun-cli-agentloop` plugin
as missing, is an environment fault rather than a reason to leave the wrapper:
install the plugin and run the same subcommand again. Once a spec file exists the
raw command validates nothing the wrapper has not already validated, and
rebuilding `--source` and `--pipeline` by hand is exactly how the quoting failure
below gets introduced. If the raw command is still unavoidable, split the spec
into its own files first and pass those, never an inline literal:

```bash
python3 - "$SPEC" <<'PY'
import json, sys
spec = json.load(open(sys.argv[1]))
json.dump(spec["source"], open("source.json", "w"))
json.dump(spec["nodes"], open("pipeline-nodes.json", "w"))
PY
```

```bash
aliyun agentloop preview-pipeline \
  --agent-space <space> \
  --source "$(cat source.json)" \
  --pipeline "$(cat pipeline-nodes.json)" \
  --from-time <unix-seconds> \
  --to-time <unix-seconds> \
  --region <region> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-management/{session-id}"
```

Require a bounded time window. Warn before AI nodes.

Pass the two JSON blobs from files as shown above, never as inline single-quoted
literals. Inline JSON containing a quote or an empty-string comparison such as
`!= ''` gets mangled by the shell, and the service then reports a misleading
`Error: unknown field: {"nodes":`. That error names the API but the real cause is
local shell quoting: the payload arrived truncated. If it appears, stop editing
the node parameters and check how the JSON was passed.

### Manual run

Only needed for a Scheduled Pipeline that must process an extra window, or for a
RunOnce Pipeline being re-run over a window it has not covered yet. A newly
created RunOnce Pipeline has already run its configured window, so check
`list-pipeline-runs` before calling this.

Use only with explicit approval and a bounded time window:

```bash
aliyun agentloop run-pipeline \
  --agent-space <space> \
  --pipeline-name <name> \
  --from-time <unix-seconds> \
  --to-time <unix-seconds> \
  --region <region> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-management/{session-id}"
```

`409 ResourceExist: A run already exists` means a run already covers that window.
Treat it as a normal outcome: read the existing run with `list-pipeline-runs` and
`get-pipeline-run` instead of retrying or widening the window silently.

### Lifecycle and destructive operations

Before pause, resume, terminate, cancel, update, or delete:

1. Query the exact target.
2. Show AgentSpace, Pipeline name, run ID if applicable, current status, and
   consequence.
3. Ask for separate explicit confirmation.
4. Execute exactly one raw CLI command.

Examples (each needs the shared `--user-agent` flag before execution):

```bash
aliyun agentloop pause-pipeline --agent-space <space> --pipeline-name <name> --reason '<reason>' --region <region>
aliyun agentloop resume-pipeline --agent-space <space> --pipeline-name <name> --region <region>
aliyun agentloop delete-pipeline --agent-space <space> --pipeline-name <name> --region <region>
```

Never perform bulk destructive operations.

## Node, Operator, and OT AI Guidance

SPL is the service-side implementation language behind Pipeline nodes. This
skill must not output SPL: never show SPL syntax, operator flags, or SPL-layer
concepts in user-facing output, and never paste them into create-spec JSON or
`pipeline.nodes[].parameters`. The user-facing surface is Pipeline Nodes only.

Do not paste SPL syntax directly into the JSON payload. The CLI accepts
`pipeline.nodes[].parameters` objects. Translate only after checking the
Layer 1 node reference and the installed CLI schema.

Reference layers:

- `references/pipeline/nodes/`: API node JSON definitions, including parameter
  expressions, defaults, output columns, and troubleshooting notes. Use this
  first when composing `pipeline.nodes[]`.
- `references/pipeline/operators/`: SPL operator syntax and implementation
  details. Use only to understand node semantics precisely and to troubleshoot
  expressions; never copy into user-facing output or JSON payloads.
- Installed CLI help and dry-run: final authority for command names, casing, and
  top-level request payload fields.

For OT AI trace Pipelines:

1. Decide sample granularity: Span, Trace, Session, Agent turn, or ReAct step.
2. Select candidate fields from
   [references/pipeline/trace/ot-ai-collection-spec.md](trace/ot-ai-collection-spec.md).
3. Confirm the real LogStore schema if the user authorizes inspection.
4. Use `make-instance` when multiple event rows must become one dataset row.
5. Treat prompt, message, tool argument, tool result, input, and output fields as
   sensitive content.

## Verification

After editing this domain or its wrapper, run:

```bash
python3 -m unittest tests.pipeline.test_agentloop_pipeline
python3 -m unittest tests.pipeline.test_skill_contracts
python3 "$SKILL_DIR/scripts/pipeline/agentloop_pipeline.py" doctor
```

If a skill validator (for example `skill-creator`'s `quick_validate.py`) is
available in your environment, run it against `"$SKILL_DIR"` as well.

For compile checks on macOS sandboxed environments, set a local pycache prefix:

```bash
PYTHONPYCACHEPREFIX="$SKILL_DIR/.pycache" python3 -m py_compile "$SKILL_DIR/scripts/pipeline/agentloop_pipeline.py" "$SKILL_DIR/tests/pipeline/test_agentloop_pipeline.py"
```

Remove the local `.pycache` directory after verification.

## Compatibility Refresh

If the AgentLoop plugin changes, inspect:

```bash
aliyun agentloop create-pipeline --help
aliyun agentloop update-pipeline --help
aliyun agentloop preview-pipeline --help
aliyun agentloop run-pipeline --help
aliyun agentloop list-pipeline-runs --help
aliyun agentloop get-pipeline-stats --help
```

Update [references/pipeline/pipeline-cli-map.md](pipeline-cli-map.md),
[references/pipeline/spec-format.md](spec-format.md), and the wrapper field
mapping only for confirmed differences.

## References

| File | Use |
|---|---|
| [references/pipeline/spec-format.md](spec-format.md) | Create-spec JSON schema and examples |
| [references/pipeline/pipeline-cli-map.md](pipeline-cli-map.md) | Verified Pipeline CLI commands and payload model |
| [references/pipeline/ram-policies.md](ram-policies.md) | RAM actions and least-privilege policy templates |
| [references/pipeline/related-commands.md](related-commands.md) | CLI recipes, RunOnce boundaries, and clone-to-new-sink workflow |
| [references/pipeline/nodes-and-expressions.md](nodes-and-expressions.md) | Compact node inventory and raw-preserving question extraction |
| [references/pipeline/verification-method.md](verification-method.md) | Preview, async run-state, and source-to-Dataset reconciliation contract |
| [references/pipeline/nodes/OVERVIEW.md](nodes/OVERVIEW.md) | API node selection, JSON examples, and ordering |
| `references/pipeline/nodes/<node>.md` | Node-specific JSON parameter guidance |
| [references/pipeline/operators/OVERVIEW.md](operators/OVERVIEW.md) | SPL operator map, ordering rules, and data-flow internals (internal reference; do not surface SPL) |
| `references/pipeline/operators/<operator>.md` | Operator-specific SPL syntax and behavior (internal reference; do not surface SPL) |
| [references/pipeline/trace/ot-ai-trace-recipe.md](trace/ot-ai-trace-recipe.md) | OT-AI trace to Dataset methodology and OT-AI expression recipes |
| [references/pipeline/trace/ot-ai-collection-spec.md](trace/ot-ai-collection-spec.md) | OT AI trace field vocabulary for Pipeline source mapping |
