---
name: alibabacloud-agentloop-evaluation
description: Orchestrate AgentLoop evaluation workflows through the Aliyun CLI plugin with safe previews, saved evaluator and evaluator-skill management, one-shot sample tests, trace or dataset batch runs, polling, and result inspection. Analyze evaluation quality and low-score cases from SLS. Use for natural-language requests to create or update evaluators or evaluator skills, launch or monitor evaluation tasks, inspect evaluation results, diagnose low scores, troubleshoot evaluation API calls, and simplify AgentLoop evaluation commands.
---

# Alibaba Cloud AgentLoop Evaluation

## Scenario Description

Orchestrate AgentLoop evaluation workflows through the Aliyun CLI plugin (`aliyun-cli-agentloop`). The skill converts a compact JSON specification into the required AgentLoop API sequence: discover evaluators, create/update saved evaluators, create one-shot or batch evaluation tasks, poll runs, and analyze results from SLS.

**Architecture**: `Aliyun CLI >= 3.3.3 + aliyun-cli-agentloop 0.7.0 + aliyun-cli-sls plugin + AgentLoop API (2026-05-20) + SLS evaluation_detail Logstore`

Use the bundled wrapper to convert a compact JSON specification into the required AgentLoop API sequence. Default to a dry-run; send mutations only with `--execute`.

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**
> [MUST] Verify: `aliyun version` — must be >= 3.3.3.
> - **First install or major upgrade:** Download, review, then execute the [setup script](references/cli-installation-guide.md#first-time-install-or-major-upgrade). Avoid `curl | bash` piping.
> - **Routine update (CLI >= 3.3.5):** `aliyun upgrade` — prefer this built-in self-update over re-running the install script.
> - See [references/cli-installation-guide.md](references/cli-installation-guide.md) for full installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

Verify the AgentLoop plugin:

```bash
aliyun plugin show --name aliyun-cli-agentloop
aliyun agentloop version
```

For result analysis, also install the SLS plugin:

```bash
aliyun plugin install --name aliyun-cli-sls
```

## Script Dependencies

The bundled Python scripts in `scripts/` use **only the Python 3.8+ standard library** — no external packages are required. See [scripts/requirements.txt](scripts/requirements.txt) for the full declaration.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SKILL_DIR` | yes | Absolute path to this skill directory (containing `SKILL.md`) |
| `ALIBABA_CLOUD_PROFILE` | no | Scope the workflow to a named CLI profile without switching the default |
| `SKILL_SESSION_ID` | no | 32-char hex session ID for observability; injected by the agent at runtime |

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## RAM Policy

This skill requires AgentLoop and SLS permissions. See [references/ram-policies.md](references/ram-policies.md) for the full permission list.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., AgentSpace name, Region, evaluator names,
> task names, dataset names, time windows, thresholds, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter Name | Required/Optional | Description | Default Value |
|---|---|---|---|
| `agent_space` | Required | Target AgentSpace name | — |
| `region` | Optional | Aliyun endpoint-selection region | — |
| `task.name` | Optional | Evaluation task name | Auto-generated |
| `task.mode` | Optional | `oneshot` or `batch` | Inferred from data_filter |
| `task.data_type` | Optional | `trace` or `dataset` | `trace` |
| `data_filter.max_records` | Required (batch) | Maximum records to evaluate | — |
| `window.start` | Required (batch) | Backfill start time (timezone-bearing ISO-8601) | — |
| `window.end` | Required (batch) | Backfill end time (timezone-bearing ISO-8601) | — |
| `threshold` | Optional | Low-score threshold for analysis | `0.5` |
| `max_cases` | Optional | Maximum low-score cases to return | `50` |

## Mutation Confirmation Protocol

> **CRITICAL: All cloud mutation operations require explicit user confirmation before execution.**
>
> This skill can create, modify, and delete cloud resources. To prevent unintended
> changes, every mutation MUST follow the three-step protocol below. No exceptions.

### Mutation operations requiring confirmation

The following operations alter cloud resources and MUST NOT be executed without
explicit user approval:

| Operation | CLI/API | Risk |
|-----------|---------|------|
| Create evaluator | `create-evaluator` | Creates a persistent saved evaluator |
| Update evaluator | `update-evaluator` | Modifies an existing evaluator's config/version |
| Create evaluation task | `create-evaluation-task` | Launches a potentially costly evaluation run |
| Execute evaluation task | `run --execute` | Sends the actual mutation request to the cloud |
| Continuous evaluation | `continuous.enabled=true` | Incurs ongoing compute costs until stopped |
| Unbounded batch run | `--allow-unbounded` | Evaluates all matching records with no record cap |
| Delete task | `delete-evaluation-task` | Irreversible resource deletion |
| Delete evaluator | `delete-evaluator` | Irreversible resource deletion |
| Terminate task | `update-evaluation-task --status Terminated` | Stops a running evaluation |

### Three-step confirmation protocol

1. **Preview (dry-run)** — Always run without `--execute` first. Show the user
   the exact commands and JSON payloads that will be sent to the cloud API.

   ```bash
   python3 "$SKILL_DIR/scripts/agentloop_eval.py" run --spec /path/to/evaluation.json
   ```

2. **Confirm** — Present the rendered preview to the user and explicitly ask for
   approval. Quote the key parameters (AgentSpace, evaluator names, task name,
   data scope, estimated records, cost implications). Wait for a clear
   affirmative response before proceeding.

   > Do NOT assume that running `run` without `--execute` implies intent to
   > execute. Do NOT proceed to execution based on silence or ambiguity.

3. **Execute** — Only after receiving explicit confirmation, add `--execute` and
   any required override flags (`--allow-unbounded`, `--allow-continuous`):

   ```bash
   python3 "$SKILL_DIR/scripts/agentloop_eval.py" run \
     --spec /path/to/evaluation.json --execute
   ```

### Read-only operations (no confirmation needed)

`doctor`, `discover`, `status`, and `analyze` (result analysis) are read-only
and do not require the confirmation protocol.

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-agentloop-evaluation/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun agentloop list-evaluators --agent-space my-space --user-agent AlibabaCloud-Agent-Skills/alibabacloud-agentloop-evaluation/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

**Script execution:** The bundled Python wrapper automatically reads `SKILL_SESSION_ID` from the environment and injects `--user-agent` into every cloud API command. Inject the session-id via inline environment variable:

```bash
SKILL_SESSION_ID={session-id} python3 "$SKILL_DIR/scripts/agentloop_eval.py" run --spec evaluation.json --execute
SKILL_SESSION_ID={session-id} python3 "$SKILL_DIR/scripts/analyze_evaluation_results.py" --agent-space <space> ...
```

## Core Workflow

### Select the workflow

- Use a one-shot task with `dataFilter.provided` to test an evaluator against one supplied sample.
- Use a batch trace task with a bounded time window and `maxRecords` to evaluate observed traces.
- Use a batch dataset task for an existing AgentLoop dataset. Start from [references/examples/batch-dataset-example.json](references/examples/batch-dataset-example.json) and map evaluator variables directly to dataset columns.
- Use result analysis to inspect evaluation quality and low-score cases from the fixed `evaluation_detail` SLS Logstore.
- Use `discover` or `status` for read-only inspection.
- Add `evaluator_actions` only when the user asks to create or update saved evaluators. Preserve the requested `AGENT`, `LLM`, or `CODE` type and its type-specific configuration.
- Use the raw evaluator-skill commands in [references/api-map.md](references/api-map.md) when the user asks to manage skill files. Preview create and update operations; require explicit permission before deletion.

Read [references/spec-format.md](references/spec-format.md) whenever composing or changing a workflow specification. Read [references/api-map.md](references/api-map.md) when extending the flow, diagnosing a failed command, or when the installed plugin version differs from the documented version. Read [references/result-analysis.md](references/result-analysis.md) whenever analyzing evaluation results or low-score cases.

### Run the workflow

1. Resolve the skill location from the absolute path of this `SKILL.md`. Prefer the path supplied by the host environment for the loaded skill. Do not assume a platform-specific skill home. Set the path once and verify that the bundled wrapper exists:

   ```bash
   export SKILL_DIR="/absolute/path/to/alibabacloud-agentloop-evaluation"
   test -f "$SKILL_DIR/scripts/agentloop_eval.py"
   ```

   When multiple Aliyun CLI profiles exist, scope the workflow without switching the default profile:

   ```bash
   export ALIBABA_CLOUD_PROFILE=<profile-name>
   ```

2. Check the local CLI and plugin. Add `--agent-space` to verify cloud authentication and access with a read-only request:

   ```bash
   python3 "$SKILL_DIR/scripts/agentloop_eval.py" doctor --agent-space <space>
   ```

3. Discover saved evaluators, current built-in evaluator names, and tasks before inventing names or relying on an old built-in alias:

   ```bash
   python3 "$SKILL_DIR/scripts/agentloop_eval.py" discover \
     --agent-space <space> --all-pages
   ```

   Task discovery defaults to the service's default channel. Add `--channel <channel>` to inspect another channel. One-shot tasks are not returned by the list API; retain their task IDs.

4. Create a spec from the nearest example, filling only required fields. Never put AccessKeys, bearer tokens, or other credentials in the spec.

5. Preview the evaluator and task requests. This invokes the plugin's `--cli-dry-run` and does not send the AgentLoop mutation request. The CLI may still resolve or refresh credentials:

   ```bash
   python3 "$SKILL_DIR/scripts/agentloop_eval.py" run --spec /path/to/evaluation.json
   ```

   If the specification enables continuous evaluation, add `--allow-continuous` only after the user explicitly accepts the ongoing cost. Use the flag for both preview and execution.

6. Inspect the rendered preview. Present the key parameters (AgentSpace, evaluator names, task name, data scope, estimated records, cost implications) to the user and obtain explicit confirmation before proceeding. Only add `--execute` after the user approves the preview — even if the user initially requested execution, the preview must be shown and confirmed first:

   ```bash
   python3 "$SKILL_DIR/scripts/agentloop_eval.py" run \
     --spec /path/to/evaluation.json \
     --execute \
     --output /path/to/evaluation-result.json
   ```

   Execution verifies the AgentSpace, applies explicit evaluator create/update actions, verifies custom evaluator references, creates the task, polls its run, and writes the final raw responses. Use `--no-wait` only when asynchronous handoff is desired.

7. Resume monitoring an existing task when needed:

   ```bash
   python3 "$SKILL_DIR/scripts/agentloop_eval.py" status \
     --agent-space <space> --task-id <task-id> --wait
   ```

### Analyze evaluation results

Use the read-only analyzer after a run completes or when the user asks why evaluation quality is low. Preview the exact SLS queries first:

```bash
python3 "$SKILL_DIR/scripts/analyze_evaluation_results.py" \
  --agent-space <space> \
  --region <region> \
  --from <timezone-bearing-ISO-or-epoch> \
  --to <timezone-bearing-ISO-or-epoch> \
  --task-id <task-id> \
  --preview
```

Then run the bounded analysis when the user has asked for result analysis:

```bash
python3 "$SKILL_DIR/scripts/analyze_evaluation_results.py" \
  --agent-space <space> \
  --region <region> \
  --from <timezone-bearing-ISO-or-epoch> \
  --to <timezone-bearing-ISO-or-epoch> \
  --task-id <task-id> \
  --threshold 0.5 \
  --max-cases 50 \
  --output /path/to/evaluation-analysis.json
```

Narrow by `--run-id` or `--evaluator-name` when available. The analyzer resolves the SLS project from the AgentSpace, queries only `evaluation_detail`, and returns overview metrics, evaluator-level breakdowns, and low-score case evidence.

Raw input, output, evaluation process, and custom outputs are omitted by default. Add `--include-content` only when exact customer content is necessary and explicitly authorized.

## Success Verification Method

See [references/verification-method.md](references/verification-method.md) for step-by-step verification commands covering CLI checks, discovery, preview, execution, result analysis, and unit tests.

## Cleanup

This skill does not automate delete, cancel, or terminate operations. To clean up resources manually after use:

> **Note:** These are raw `aliyun` CLI commands and must include `--user-agent` for observability. Replace `{session-id}` with the current `SKILL_SESSION_ID`.

1. **Terminate a running task** (explicit user authorization required):
   ```bash
   aliyun agentloop update-evaluation-task --agent-space <space> --task-id <task-id> --status Terminated --user-agent AlibabaCloud-Agent-Skills/alibabacloud-agentloop-evaluation/{session-id}
   ```

2. **Delete a task** (explicit user authorization required):
   ```bash
   aliyun agentloop delete-evaluation-task --agent-space <space> --task-id <task-id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-agentloop-evaluation/{session-id}
   ```

3. **Delete a saved evaluator** (explicit user authorization required):
   ```bash
   aliyun agentloop delete-evaluator --agent-space <space> --name <evaluator-name> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-agentloop-evaluation/{session-id}
   ```

> **Warning:** These are destructive operations. Always require explicit user permission before execution. One-shot task and run records are automatically cleaned by the backend after 24 hours.

## Best Practices

- Require a timezone-bearing ISO-8601 window or epoch milliseconds for batch backfills.
- Require `dataFilter.maxRecords` for batch tasks unless the user explicitly accepts an unbounded run and `--allow-unbounded` is supplied.
- Keep `continuous.enabled` false unless the user explicitly requests continuous evaluation and understands the ongoing cost; the wrapper requires `--allow-continuous` when it is enabled.
- Preserve unique evaluator identities within a task. Use `evaluatorRef` for saved evaluators and `name` for inline evaluators.
- Create saved evaluators only with an exact supported type: `AGENT`, `LLM`, or `CODE`. Never silently change the requested type.
- Treat evaluator version updates, evaluator-skill create/update operations, task creation, and continuous evaluation as cloud mutations. Preview them first.
- Keep result analysis read-only and time-bounded. Query only `evaluation_detail`, cap low-score cases at 200, and omit raw customer content unless `--include-content` is explicitly authorized.
- Do not automate delete, cancel, or terminate operations. Use the raw CLI only after explicit user authorization.
- Report the task ID, run ID, final status, and output file. Include raw service errors without exposing local credential files.

## Refresh compatibility

If `doctor` reports a plugin or API version different from the Architecture line above, inspect these before execution and adjust only the affected mappings:

```bash
aliyun agentloop create-evaluator --help
aliyun agentloop create-evaluator-skill --help
aliyun agentloop create-evaluation-task --help
aliyun agentloop get-evaluation-task --help
aliyun agentloop list-evaluation-runs --help
aliyun agentloop get-evaluation-run --help
```

## Reference Links

| Reference | Contents |
|-----------|----------|
| [references/spec-format.md](references/spec-format.md) | Workflow specification format and field reference |
| [references/api-map.md](references/api-map.md) | AgentLoop evaluation API map and CLI command reference |
| [references/result-analysis.md](references/result-analysis.md) | Evaluation result analysis workflow and score bands |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Alibaba Cloud CLI installation and plugin setup guide |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission list and sample policy |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Correct/incorrect CLI and spec patterns |
| [references/verification-method.md](references/verification-method.md) | Step-by-step verification commands |
| [references/related-commands.md](references/related-commands.md) | All CLI commands used by this skill |
