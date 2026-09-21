---
name: lhm-sch-read-exec
description: |
  CLI tool and Agent Playbook for LHM schedule migration (schedule reading and conversion).
  Provides both a standalone CLI (`lhm-scheduler`) and an Agent-driven workflow guide.

  Triggers: lhm-scheduler commands, schedule migration tasks, PostInnerReader,
  GetInnerReadAsyncResult, PostInnerConvert, GetInnerConvertAsyncResult,
  or any request interacting with the LHM Inner Scheduler API — even without explicitly mentioning "LHM".
  Conversion-only triggers include "直接转换" (convert directly), "跳过探查" (skip exploration),
  and "只跑转换阶段" (run only the conversion stage).

  Do not trigger for: DataCheck workflows, DDL translation, SQL conversion, or other
  non-schedule-migration tasks.
---

# LHM Scheduler CLI & Agent Playbook

This Skill is **Agent-driven**. The `lhm-sch-read-exec` CLI exposes **stateless single-step commands**: each command makes **exactly one** API call, prints structured JSON status, and exits. There is **no polling loop inside** — the **Agent** is responsible for waiting between polls and re-invoking the poll command based on the returned `status` and exit code. State (such as `task_id`) is passed explicitly via command-line arguments; the CLI itself persists nothing.

## CLI Usage

### Environment Prerequisites

**The environment and credentials have already been prepared by [lhm-sch-env](../lhm-sch-env/SKILL.md) at session start; this skill performs no environment validation whatsoever.**
Simply run the business commands — do not run validation scripts, do not run `validate`, and do not re-confirm credentials or prompt the user about configuration.

> ⛔ **The one exception — the `aliyun-cli-lhm` plugin (hard stop)**: `read-start`, `convert-start`, and every polling command below reach the service through `aliyun lhm <command>`, so the plugin (>= 0.1.1, i.e. `~/.aliyun/plugins/aliyun-cli-lhm/manifest.json` exists) must be present. If it is not, **stop immediately**: report the environment error verbatim and terminate.
>
> Do **not** ask the user to choose a data source, resolve an ambiguity, or supply any conversion parameter — those clarifications are meaningful **only once the plugin is confirmed available**, because without it no `read-start` call can ever return a candidate list to disambiguate. Do **not** run `uv tool install` or `lhm-scheduler`: this CLI shells out to `aliyun lhm`, so a successful install is never proof that the flow can proceed, and never report an exploration or conversion result that did not come from a real call.

Only when a command actually reports an environment-class error (e.g., credentials not found, command not found) should it be handed to [lhm-sch-env](../lhm-sch-env/SKILL.md); when relaying its guidance, **never write secrets on behalf of the user, and never echo secret values**.

### Status Code & Exit Code Contract

Each single-step command outputs a JSON object with a `status` field to **stdout** and exits with an exit code; the Agent branches on them:

| `status` | Exit code | Meaning | Agent action |
|----------|-----------|---------|--------------|
| `started` | `0` | The start step was accepted; the task is running | Proceed to the corresponding `*-poll` step |
| `running` | `3` | Poll step — the task is still in progress | **Wait about 20 seconds, then re-invoke the same poll command** |
| `completed` | `0` | Poll step — the task completed successfully | Proceed to the next step / render results |
| `ambiguous` | `2` | The data source name matched multiple candidates (E610R1002) | Show the `candidates` to the user and rerun start with the exact name |
| `failed` | `2` | Unrecoverable business error | Report `err_code` + `err_message` and abort |
| `failed` (SDK_ServiceUnavailable) | `2` | **API-level transient server fault** (HTTP 503) | **Abort the flow immediately** and tell the user "The LHM service is temporarily unavailable; please retry later or contact operations to check the service status"; do not auto-retry |
| *(config error)* | `1` | Missing credentials / invalid configuration | Fix the environment and retry |

### Commands

#### Single-Step Migration Commands

```bash
# 1. Start exploration (PostInnerReader)
lhm-sch-read-exec read-start --source <SOURCE_DS_NAME>

# 2. Poll exploration results (GetInnerReadAsyncResult) — repeat while exit code is 3
lhm-sch-read-exec read-poll --source <SOURCE_DS_NAME>

# 3. Trigger conversion (PostInnerConvert) — returns task_id
lhm-sch-read-exec convert-start --source <SOURCE_DS_NAME> --target <TARGET_DS_NAME> [--sql-convert-map <JSON_MAP>]

# 4. Poll conversion results (GetInnerConvertAsyncResult) — repeat while exit code is 3
lhm-sch-read-exec convert-poll --task-id <TASK_ID> [--output-format text|json]
```

**Common options** (all commands): `--endpoint URL` / `--region ID` — attached to every `aliyun lhm` call as fixed parameters; they override the values read from the config file's `lhm` section (`lhm.endpoint` / `lhm.region_id`), which in turn fall back to the `LHM_ENDPOINT` / `REGION_ID` environment variables and then built-in defaults.

**`convert-poll --output-format`** (default `json`): when the step is `completed` and `text` is selected, the §5.4-format summary (downloaded from `metadata/convert_statistics.json` inside the result zip) is also printed to **stderr**, while the JSON status goes to stdout.

### Agent Orchestration Flow

The Agent drives the full migration by chaining single-step commands. Polling is the Agent's responsibility:

#### Special Logic: Convert-Only Mode

If the user's semantics clearly indicate **conversion only** (e.g., "convert directly", "skip exploration", "run only the conversion stage"; the Chinese equivalents are declared in the frontmatter description), and the user has provided explicit source and target data source names, the Agent **may skip steps 1 and 2 (the exploration stage)** and start directly from step 3 (`convert-start`).

**Applicability conditions:**
- The user's intent is clearly "convert only" or "skip reading/exploration"
- The user has provided valid `--source` and `--target` parameters
- Exploration results such as workflow/node counts are not needed

**Note:** if the user has not clearly expressed the intent to skip exploration, or if it is necessary to confirm the data sources exist or to fetch schedule metadata, the full four-step flow must be executed.

#### Standard Flow

```
1. read-start --source S
     status=started (exit 0) → go to 2
     status=ambiguous        → have the user choose the exact name, rerun read-start
     status=failed           → abort

2. read-poll --source S
     status=running (exit 3)   → wait about 20 seconds, rerun read-poll (max 20 retries ≈ 6.7 minutes)
     status=completed (exit 0) → record workflow_count / node_count, go to 3
     status=failed             → abort

3. convert-start --source S --target T [--sql-convert-map <JSON_MAP>]
     status=started (exit 0)   → obtain task_id, go to 4
     status=ambiguous/failed   → handle as above

4. convert-poll --task-id <task_id> -o text
     status=running (exit 3)   → wait about 20 seconds, rerun convert-poll (max 20 retries)
     status=completed (exit 0) → render the summary (already emitted with -o text), go to 5
     status=failed             → abort

5. Task results are persisted automatically
     When convert-start succeeds, the CLI automatically writes task_id to <session dir>/output/ds-cli/result/readexec.json in the session temp directory and synchronizes it into the session temp config (convert_task_id); no manual action by the Agent is needed.
```

**Agent polling rules (mandatory; violation means failure):**
- After receiving a `running` (exit 3) result, the Agent **must** emit a user-facing status (e.g., `仍在读取中...` / "Still reading...", `仍在转换中...` / "Still converting..."), wait **20 seconds**, and then **re-invoke the same poll command in a new turn**.
- It is **strictly forbidden** to summarize the task, ask the user whether to continue, or end the flow early after receiving `running`. `running` means the task is in progress — **it is neither an error nor an interruption**.
- Track the retry count in the Agent context; abort after **20 retries** for any poll step.
- **Never** expose raw `err_code` / `request_id` to the user while waiting.
- **Critical constraint**: polling is a necessary part of asynchronous tasks and **must continue until `completed` or `failed` is received**. Stopping polling midway is equivalent to task failure.

### User-Facing Output Rules (must be followed)

The CLI's JSON/status output is the **Agent-internal protocol**. What the user sees must be concise natural-language progress narration — the underlying mechanics must never be exposed.

**Always hide from the user:**
- The raw command lines being executed (e.g., `lhm-sch-read-exec read-poll --source ...`)
- Raw JSON output / `status` field values (`started`, `running`, `completed`, etc.)
- Technical codes: `err_code` (e.g., `E610R1004`, `E610R1016`), `request_id`, exit codes
- SDK / endpoint / region internals and any stack traces

**What to show the user** — only the meaning of the current progress:
- Exploration started → `开始读取调度信息...` ("Reading schedule information...")
- Exploration polling → `仍在探查中，请稍候...` ("Still exploring, please wait...")
- Exploration complete → report the counts in natural language (workflow count / node count / type distribution)
- Conversion started → `开始转换调度...` ("Converting schedules...")
- Conversion polling → `仍在转换中，请稍候...` ("Still converting, please wait...")
- Conversion complete → render per convertResultRenderingDesign.md

**Mapping reference (for Agent-internal use; do not print):**

| Internal signal | What the user should see |
|-----------------|--------------------------|
| `read-start` → `started` | Reading schedule information... |
| `read-poll` → `running` / `E610R1004` | Still exploring, please wait... |
| `read-poll` → `completed` | (directly present workflow count / node count / type distribution) |
| `convert-start` → `started` | Converting schedules... |
| `convert-poll` → `running` / `E610R1016` | Still converting, please wait... |
| `convert-poll` → `completed` | (render the conversion result summary) |
| any step → `failed` (`SDK_ServiceUnavailable`) | The LHM service is temporarily unavailable; please retry later or contact operations to check the service status |

> Failure is the only exception: when `status="failed"` is received, translate the reason into actionable guidance (e.g., "the data source does not exist"), but still **do not** expose raw `err_code` / `request_id` to the user — keep them in internal logs only.

### Examples

```bash
# Start exploration
lhm-sch-read-exec read-start -s ds_dolphin_prod

# Poll until complete (the Agent repeats while the exit code is 3)
lhm-sch-read-exec read-poll -s ds_dolphin_prod

# Trigger conversion; obtain task_id from the JSON output
lhm-sch-read-exec convert-start -s ds_dolphin_prod -t ds_dataworks_prod --sql-convert-map '{"dolphin_sql":"dataworks_sql"}'

# Poll conversion and render the summary on completion
lhm-sch-read-exec convert-poll --task-id 4189652306700009473 -o text
```

### Credential Configuration

The CLI automatically loads the session config transcribed by lhm-sch-env; this skill does not need to care. The session temp directory (abbreviated `<session dir>` below) is a per-session dedicated `/tmp/lhm-sch-session-<uid>/s-<timestamp>-<random>/`, which the CLI locates automatically via the pointer file `current` (or `$LHM_SESSION_FILE`); the session config `session.json` and all result artifacts live under that directory.

---

# Appendix: Low-Level API Reference

The following sections document the four underlying Inner APIs and the error-handling principles. The CLI single-step commands (see "CLI Usage" above) wrap these APIs — this appendix is for understanding what each command does internally and for using the SDK directly when debugging. **The orchestration and polling logic is defined in "Agent Orchestration Flow" above; do not reimplement it as a synchronous loop.**

## Available APIs

The environment and credentials have already been prepared by lhm-sch-env; this skill can use the following four Inner APIs directly:

| API | Method | Purpose | Required parameters |
|-----|--------|---------|---------------------|
| **PostInnerReader** | `client.post_inner_reader()` | Start the schedule exploration task | `data_source_name` |
| **GetInnerReadAsyncResult** | `client.get_inner_read_async_result()` | Fetch exploration results | `data_source_name` |
| **PostInnerConvert** | `client.post_inner_convert()` | Trigger schedule conversion | `src_data_source_name`, `tgt_data_source_name` |
| **GetInnerConvertAsyncResult** | `client.get_inner_convert_async_result()` | Fetch conversion results | `task_id` |

See [api-spec.md](api-spec.md) for the detailed API specification.

## API to CLI Command Mapping

Each Inner API is wrapped by a single-step CLI command. The table below summarizes the request, the success response, and the in-progress error code of each step. The Agent does not call these APIs directly — it invokes the CLI commands and branches on `status` / exit code.

| API | CLI command | Request parameters | On success (`err_code=200`) `body.data` | In-progress error code |
|-----|-------------|--------------------|-----------------------------------------|------------------------|
| **PostInnerReader** | `read-start` | `data_source_name` | (exploration accepted) | — |
| **GetInnerReadAsyncResult** | `read-poll` | `data_source_name` | `{workflowCount, taskNodeCount, scriptCount, nodeTypeCountMap}` | `E610R1004` |
| **PostInnerConvert** | `convert-start` | `src_data_source_name`, `tgt_data_source_name`, `sql_convert_map` (optional) | `task_id` (string) | — |
| **GetInnerConvertAsyncResult** | `convert-poll` | `task_id` | conversion results including `download_url` | `E610R1016` |

**Data source ambiguity (`E610R1002`)**: `read-start` / `convert-start` return `status="ambiguous"` with a `candidates` list parsed from `body.data`. The Agent presents these names to the user via `AskUserQuestion` and reruns the start command with the confirmed exact name.

**Data source does not exist (`E610R1001`)**: returns `status="failed"` with `action_required="create_datasource"` and `suggested_skill="/lhm-sch-ds"`; tell the user "The data source does not exist; please use the /lhm-sch-ds skill to create it. Example: /lhm-sch-ds create a DolphinScheduler-type data source", then abort. The Agent should guide the user to invoke the `/lhm-sch-ds` skill to create the missing data source and then retry.

**Final result rendering**: `convert-poll -o text` downloads the result zip referenced by `download_url`, extracts all files into the session temp directory (`<session dir>/output/ds-cli/result/`, same root as the session config `session.json`), and automatically renders convertResultRenderingDesign.md. The output includes the absolute paths of the extracted files; no manual rendering is needed. In addition, the Agent **must** also download the OSS file referenced by the `oss_download_url` field into the same temp directory (`<session dir>/output/ds-cli/result/`) to ensure the conversion result package is complete and usable.

---

## Error Handling Principles

1. **Never guess parameters**: all data source names and task IDs must come from API responses or explicit user input
2. **Always check the `success` field first**: even when `err_code == 200`, verify `body.success == "true"` (string comparison)
3. **Parse `data` safely**: always wrap `json.loads(body.data)` in try-except; malformed JSON should trigger an abort and log the raw data
4. **Preserve request_id**: include `request_id` in every error message for troubleshooting
5. **User-friendly messages**: translate technical `err_code`s into actionable guidance (see api-spec.md for error code meanings)

## Agent Instructions

When driving the single-step commands (see "Agent Orchestration Flow"):

1. **Pass state via parameters**: explicitly carry `SOURCE_DS_NAME`, `TARGET_DS_NAME`, and the `task_id` from `convert-start` between command invocations — the CLI is stateless
3. **Branch on `status` + exit code**: exit `3` (`running`) → wait about 20 seconds and rerun the same poll command; exit `0` → proceed; exit `2` (`failed`/`ambiguous`) → handle or abort; exit `1` → fix the configuration. **Pay special attention**: if `err_code == "SDK_ServiceUnavailable"`, this is an API-level transient server fault (HTTP 503); **the flow must be interrupted immediately and the user told that the service is unavailable — auto-retrying or treating it as an ordinary business error is strictly forbidden**.
4. **Use AskUserQuestion for ambiguity**: upon receiving `status="ambiguous"`, present the `candidates` and rerun the start command with the confirmed exact name
5. **Respect the polling interval**: keep waiting about 20 seconds between polls; cap each poll step at **20 retries** (≈ 6.7 minutes)
6. **Keep user output friendly**: follow the **"User-Facing Output Rules (must be followed)"** above — never print command lines, raw JSON, `status` values, `err_code`, `request_id`, or exit codes to the user; only show the natural-language meaning of the current step (`仍在读取中...` / "Still reading..." / `仍在转换中...` / "Still converting..." / result summary)
7. **Refer to api-spec.md** for complete field definitions and error code meanings
8. **Handle sql_convert_map from natural language**: when calling `convert-start`, extract the SQL dialect mapping mentioned in the user's request (e.g., convert dolphin sql to dataworks sql) and pass it via `--sql-convert-map`. If the user does not mention SQL dialect conversion, omit this parameter entirely — do not proactively ask or prompt.
9. **Task results are persisted automatically**: when `convert-start` succeeds, the CLI has already written task_id to `<session dir>/output/ds-cli/result/readexec.json` and synchronized it into the session temp config (the `convert_task_id` field of `<session dir>/session.json`); the Agent does not need to create files manually.
10. **Source/target parameter completeness check**: before executing any operation, the **source data source** and **target data source** parameters must both be identified from the user's natural-language input. If either parameter is missing or cannot be clearly identified, the Agent **must immediately ask the user** and may continue only after both parameters have explicit values. Guessing or skipping with incomplete parameters is forbidden.
11. **Strictly limit the responsibility boundary**: this Skill is only responsible for **schedule reading and conversion** (read + convert). When `convert-poll` returns `status="completed"` and the conversion result summary has been rendered, **the task is over**. Proactively invoking other skills (such as `lhm-sch-deploy`, `lhm-sch-pipeline`) or performing any operation beyond read/convert scope is strictly forbidden. If the user later needs deployment or other operations, wait for an explicit new instruction before responding.
12. **Do not search for or modify output paths**: the output directory `<session dir>/output/ds-cli/result/` and the file `readexec.json` are **fixed conventions** (located in the same temp directory as the session config `session.json`) and are managed automatically by the CLI. It is **strictly forbidden** to spawn subtasks or use Grep/Glob to search the codebase in order to "find", "verify", or "update" this path configuration. To read the results, use the absolute paths in the CLI output directly.
