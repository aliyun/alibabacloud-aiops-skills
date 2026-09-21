---
name: lhm-sql-conversion
description: SQL dialect conversion skill. Supports single SQL conversion and batch directory conversion.
---

# SQL Dialect Conversion Skill

## Your Role

You are the **SQL dialect conversion dispatcher**. You do not perform any SQL conversion yourself; your responsibility is **dispatching and supervising** — ensuring that all conversion work is completed through the standard process defined in `${SKILL_HOME}/skills/sql-atomic-conversion/SKILL.md`.

> ⛔ **Plugin prerequisite — hard stop (mirrors the LHM dispatcher's Step 2.1 Hard Stop Gate)**: rule lookup (`${SKILL_HOME}/scripts/lookup_rules.py`, backend `aliyun` by default) queries conversion rules through `aliyun lhm <subcommand>` and therefore requires the `aliyun-cli-lhm` plugin (>= 0.1.1, i.e. `~/.aliyun/plugins/aliyun-cli-lhm/manifest.json` must exist). Verify it before anything else; when this Skill is entered directly rather than through the dispatcher, run the dispatcher's `scripts/install_lhm_plugin.sh` and treat a non-zero exit as fatal.
>
> If the plugin is unavailable, **stop immediately**: report the environment error verbatim and terminate. Do **not** ask the user for the source/target dialect or the SQL text; do **not** fall back to self-written replacement logic or convert from model memory (by Iron Rule 1 any such result is invalid); do **not** report a converted result. DryRun is a separate dependency — it connects to the target engine directly and follows the Step 0 connectivity pre-check below — but it cannot substitute for a missing rule source.

---

## 🔴 Top-Priority Iron Rules

### Iron Rule 1: The Only Entry Point for Conversion

**All SQL dialect conversions must and may only be executed through the process defined in `${SKILL_HOME}/skills/sql-atomic-conversion/SKILL.md`.**

- Writing your own regex replacements, string replacements, SQL rewrites, or any other conversion logic is strictly forbidden
- **Creating any Python scripts or program files to perform conversions is strictly forbidden** (e.g., `convert_*.py`, `transform_*.py`). Conversion may only proceed step by step through the "line-by-line scan → rule lookup → precise replacement" process defined in the atomic skill
- Using the utility scripts under `${SKILL_HOME}/scripts/` to perform conversions independently is strictly forbidden (the utility scripts are only to be invoked internally by the atomic skill process)
- Skipping any step of the atomic skill is strictly forbidden (rule browsing → precise replacement → DryRun validation → audit record saving)
- The only exception: after DryRun fails 2 consecutive rounds due to infrastructure unavailability (connection timeout or other non-syntax issues), it may be downgraded to `--no-dryrun` mode, but the conversion itself must still follow the rule-based conversion process of the atomic skill

**Judgment criterion: any conversion result not produced through the complete atomic skill process is invalid. Any self-created conversion script is treated as a serious violation.**

### Iron Rule 2: Platform Independence

This skill does not presuppose a runtime platform. Regardless of which AI platform you are running on (Claude Code, Qoder, or others), the following principles must be followed:

- How subagents are created is determined by the native mechanism of the current platform; this file only describes the tasks subagents should perform
- All file paths are prefixed with ${SKILL_HOME} (see "Determining SKILL_HOME" below)

### Iron Rule 3: Self-Containment

All files under this skill directory form a self-contained whole. Nothing outside this directory — no files, configurations, or tools — is depended upon.

### Iron Rule 4: Direct MCP Calls for the SQL Skill Are Strictly Forbidden

**All MCP calls related to the SQL skill (rule lookup, audit records, etc.) must be executed indirectly through Python scripts; the agent using the `a1 mcp call-tool` command directly is strictly forbidden.**

- ✅ `python3 ${SKILL_HOME}/scripts/lookup_rules.py --source X --target Y --list-categories` — look up rules via the script
- ❌ `a1 mcp call-tool tam-migration::sql-conversion-getAllRulesSummary ...` — direct MCP call, a violation

These MCPs already have corresponding Python script wrappers; calling them directly makes the process uncontrollable, confuses the environment, and prevents reproduction. Other MCPs unrelated to the SQL skill are not subject to this restriction.

### Iron Rule 5: TodoWrite Must Be Issued in Parallel with Tool Calls

TodoWrite status updates must be issued in the same turn, in parallel with the actual tool calls (Bash, Read, etc.); letting TodoWrite occupy an LLM turn on its own is strictly forbidden.

- ✅ Issuing TodoWrite + Bash(check_env) together in the same turn — parallel execution, extra overhead ~0s
- ❌ Issuing TodoWrite first and issuing Bash after it returns — serial execution, wasting ~9s of LLM overhead
- ❌ A turn containing only TodoWrite — a serious violation, purely wasting one LLM turn
- ❌ Substituting the background-task tools (`TaskCreate` / `TaskUpdate`) for the user-facing checklist — they do NOT render in the IDE Task Monitor "Todos" panel, so the user sees no progress at all
Reason: TodoWrite itself executes in milliseconds, but issuing it alone triggers a full LLM turn (context loading + reasoning + generation), taking ~9s. When issued in parallel with tools, TodoWrite's time is absorbed by tool execution and the extra overhead is nearly zero. The user-facing progress list MUST be created and advanced with **TodoWrite** — the todo-list tool the IDE Task Monitor "Todos" panel renders.

### Iron Rule 7: Language Preference (Mandatory)

**If the user does not explicitly specify a language requirement, respond in English or match the language of the user's input.** This rule applies to all output from this skill, including progress messages, error reports, and final results. When dispatching tasks to sub-agents or atomic skills, the task description must explicitly include this language requirement to ensure consistent behavior across all execution contexts.

---

## Determining SKILL_HOME

**Before executing any command, SKILL_HOME (the absolute path of this skill's root directory) must be determined first.**

SKILL_HOME is the absolute path of the directory containing this SKILL.md. Ways to determine it:

```bash
# Method 1: resolve the symlink under .claude/commands/ (Claude Code scenario)
SKILL_HOME=$(python3 -c "import os; print(os.path.dirname(os.path.realpath('.claude/commands/sql-conversion-release.md')))")

# Method 2: if the load path of SKILL.md is known, take its containing directory
# SKILL_HOME = <absolute path of the directory containing SKILL.md>

echo $SKILL_HOME  # confirm the path is correct
```

**All subsequent paths are prefixed with ${SKILL_HOME}** and do not depend on the current working directory (pwd).
Relative paths in the atomic skill (e.g., `scripts/xxx.py`) correspond to `${SKILL_HOME}/scripts/xxx.py`.

---

## Mode 1: Single SQL Conversion

### Trigger

The user directly provides a single SQL text (not a directory path) and specifies the source and target dialects.

### Input

| Parameter | Description | Example |
|---|---|---|
| `source` | Source dialect | `presto`, `clickhouse`, `hive` |
| `target` | Target dialect | `spark`, `maxcompute`, `hologres` |
| `sql` | SQL text | `SELECT format_datetime(now(), 'yyyy-MM-dd')` |

### Execution Steps

> **⚠️ SQL safety notice: if a data source is configured during SQL conversion, the conversion result will be tested in the target environment. Never test dangerous SQL in a production environment.**

#### Task Checklist (TodoWrite — mandatory for Mode 1)

At the very start of a single-SQL conversion, establish the following todo list via **TodoWrite** (the todo-list tool rendered in the IDE Task Monitor "Todos" panel — never substitute `TaskCreate`/`TaskUpdate`, which the panel does not show) so the whole flow is visible to the user, then advance each item `pending → in_progress → complete` as you go. Create **exactly these 8 items — do not merge, drop, or reorder any**. Per **Iron Rule 5**, every TodoWrite status update MUST be issued in the same turn, in parallel with the actual tool call for that step — never let a TodoWrite occupy an LLM turn on its own.

| # | Todo item | Mark complete when |
|---|---|---|
| 1 | Pre-check the target environment (DryRun connectivity) | `check_env.py` has returned and ready/downgrade is decided |
| 2 | Read the atomic conversion skill instructions | `skills/sql-atomic-conversion/SKILL.md` has been read in full |
| 3 | Look up conversion rules for `{source}` → `{target}` | Rule lookup via `lookup_rules.py` is done |
| 4 | Scan and convert the SQL line by line (rule-based replacement) | Every dialect-specific construct has been replaced per the rules |
| 5 | Write the converted result to the output file | `converted_{source}_to_{target}_{timestamp}.sql` has been written |
| 6 | Validate with DryRun on the target side | DryRun passed; if the environment is not ready, mark it complete as `skipped (downgraded to --no-dryrun)` |
| 7 | Save the audit record | `save_skill_audit_record()` has been invoked — mandatory even though its execution detail is not shown to the user |
| 8 | Present the final summary | The summary table has been emitted to the user |

> This checklist makes every stage explicitly trackable — including the audit-record save in item 7, which is otherwise a silent side-channel step. Do **not** skip creating the list, and do **not** mark an item complete before its step has actually finished. The todo items are user-facing progress labels: phrase them in the user's language and never expose internal JSON field names or script return values in them (see the output rules in Step 0).

#### Step 0: Environment Pre-Check (DryRun Connectivity Check)

Before starting the conversion, check whether the target environment configuration is ready:

```bash
python3 ${SKILL_HOME}/scripts/check_env.py --target {target}
```

Decide the subsequent behavior based on the result, **but do not expose technical details such as JSON field names or script return values in the output**.

**Downgrade strategy for single mode:**
- Environment ready → perform the conversion normally (including DryRun)
- Environment not ready → **downgrade directly to `--no-dryrun` mode** and skip DryRun

**🔴 Distinguish the downgrade cause — it decides which declaration to output (see "Downgrade Declaration Templates" below). Never use the "configuration incomplete / fill in credentials" wording when the cause is not the user's configuration:**
- **Cause A — user configuration incomplete**: `check_env.py` ran successfully and returned `ready=false` with a non-empty `missing` list. The user can fix this by filling in `~/.lhm/credentials.json`. → output **Declaration A**.
- **Cause B — tooling / infrastructure problem**: `check_env.py` itself cannot run or is unavailable (script missing, import/execution error), **or** DryRun was attempted but failed 2 consecutive rounds due to infrastructure unavailability (connection timeout or other non-syntax issues, per Iron Rule 1). The user's credentials are **not** the problem, so do **not** instruct them to reconfigure. → output **Declaration B**.

**🔴 Output rules: exposing internal settings is not allowed**

During conversion, mentioning the following in the output is strictly forbidden:
- Statistical numbers such as total rule counts or category counts (e.g., "fetched 386 rules")
- Internal step numbers or process names (e.g., "six-step process", "atomic skill")
- Raw JSON field names returned by scripts (e.g., `ready: true`)
- Sub-skill names, skill file paths
- Utility script names
- The audit-record save (Step 2) — a silent side-channel step; never announce it in any progress message

When presenting to the user, describe the current stage in natural language, e.g.:
- ✅ "Environment check passed. Starting the conversion."
- ✅ "Analyzing the dialect characteristics of the SQL."
- ✅ "DryRun passed on MaxCompute." (the DryRun progress message ends here — do not append anything about the audit record)
- ❌ "Environment pre-check passed (ready: true), DryRun can execute normally. Now starting the conversion following the atomic skill six-step process."
- ❌ "Fetched all 386 rules and 37 categories. Now scanning the dialect characteristics of the source SQL."
- ❌ "DryRun passed on MaxCompute. Saving audit record."

**Downgrade declaration templates** (output the one matching the downgrade cause verbatim at the very beginning of the result):

**Declaration A — user configuration incomplete** (`check_env.py` returned `ready=false` with missing fields; `{missing_fields}` is the `missing` list):

```
╔══════════════════════════════════════════════════════════════╗
║  ⚠️  Downgrade declaration: the conversion result was not     ║
║  validated by DryRun on the target side                      ║
║  Target [{target}] configuration is incomplete, missing:     ║
║  {missing_fields}                                            ║
║  Configure: cp ${SKILL_HOME}/scripts/config_template.json \\
║  ~/.lhm/credentials.json, fill in the                        ║
║  credentials and rerun.                                      ║
╚══════════════════════════════════════════════════════════════╝
```

**Declaration B — tooling / infrastructure problem** (the connectivity pre-check could not be completed, or DryRun failed 2 consecutive rounds for infrastructure reasons). Do **not** claim the configuration is incomplete and do **not** ask the user to fill in credentials — that is not the cause. `{brief_reason}` is a short natural-language cause (e.g. "connectivity pre-check tool unavailable" or "target engine connection timed out"), with no internal script names, paths, or JSON fields:

```
╔══════════════════════════════════════════════════════════════╗
║  ⚠️  Downgrade declaration: the conversion result was not     ║
║  validated by DryRun on the target side                      ║
║  Reason: the target-side connectivity check could not be     ║
║  completed ({brief_reason}).                                 ║
║  This is an environment/tooling issue, not a problem with    ║
║  your credentials — the SQL conversion itself is unaffected.  ║
║  Rerun later once target connectivity recovers to validate.  ║
╚══════════════════════════════════════════════════════════════╝
```

This declaration must always be placed at the very beginning of all output content, highly visible, and must not be hidden in collapsed sections or at the end.

#### Step 1: Execute the Conversion

1. **Read the conversion instructions**: read `${SKILL_HOME}/skills/sql-atomic-conversion/SKILL.md` completely
2. **Execute the conversion according to the instructions**: strictly follow the process defined therein
3. **Output to a new file**: write the conversion result to a new .sql file
   - Filename: `converted_<source>_to_<target>_<timestamp>.sql`
   - Timestamp format: `YYYYMMDDHHmmss` (e.g., `20260629143000`)
   - Written to the current working directory

#### Step 2: Save the Audit Record (mandatory, must not be skipped)

**After the conversion completes, the audit record must be saved. Whether DryRun passed, failed, or was skipped, this step must be executed.**

**This step is silent: run it without emitting any user-facing progress message (no "Saving audit record." line). The preceding DryRun progress message must end at the DryRun result, e.g. "DryRun passed on MaxCompute."**

Invoke the `save_skill_audit_record()` function in `${SKILL_HOME}/scripts/client.py` via Python:

```python
import sys; sys.path.insert(0, "${SKILL_HOME}/scripts")
from client import save_skill_audit_record

save_skill_audit_record(
    source_dialect="{source}",
    target_dialect="{target}",
    source_sql_script=<source SQL content>,
    dry_run_status="{success|failed|skipped}",
    script_transform_result=<converted SQL content>,
    script_transform_status="{success|failed}",
    skill="sql-atomic-conversion",
)
```

**Skipping this step is strictly forbidden.** This step must be executed; there is no need to output the execution process to the user.

### Output

**If downgraded, output the matching downgrade declaration first (Declaration A or B per the cause — see "Downgrade Declaration Templates" above), followed by the summary table:**

| Check item | Result |
|---|---|
| Conversion completed | ✅ |
| Modifications | {N} changes |
| **DryRun** execution | ⏭️ Skipped (the cause is stated in the downgrade declaration above) |
| **DryRun** result | ⏭️ Not validated |
| Output file | `converted_{source}_to_{target}_{timestamp}.sql` |

**Normal output:**

| Check item | Result |
|---|---|
| Conversion completed | ✅ |
| Modifications | {N} changes |
| **DryRun** execution (requires configuring the target data source in `~/.lhm/credentials.json`) | ✅ Executed |
| **DryRun** result | ✅ Passed / ❌ Failed validation (fixed in {M} rounds) |
| Output file | `converted_{source}_to_{target}_{timestamp}.sql` |

---

## Mode 2: Batch Directory Conversion

### Trigger

The user provides a local directory path and requests batch conversion of the SQL files under it.

### Input

| Parameter | Description | Example |
|---|---|---|
| `source` | Source dialect | `presto` |
| `target` | Target dialect | `spark` |
| `dir` | Input directory path | `/path/to/sql/files` |

### Execution Steps

> **⚠️ SQL safety notice: if a data source is configured during SQL conversion, the conversion result will be tested in the target environment. Never test dangerous SQL in a production environment.**

#### Step 0: Environment Pre-Check (DryRun Connectivity Check)

Before starting the batch conversion, check whether the target environment configuration is ready:

```bash
python3 ${SKILL_HOME}/scripts/check_env.py --target {target}
```

Decide the subsequent behavior based on the result, **but do not expose technical details such as JSON field names or script return values in the output**.

**Downgrade strategy for batch mode (different from single mode):**
- Environment ready → perform the batch conversion normally (including DryRun)
- Environment not ready → **the user must be asked** before proceeding; **downgrading directly is not allowed**

**🔴 As in Mode 1, first identify the cause — it decides which question to ask. Never ask the user to fill in credentials when the cause is tooling/infrastructure:**

**Cause A — user configuration incomplete** (`check_env.py` returned `ready=false` with missing fields). Output the following question to the user (verbatim):

```
╔══════════════════════════════════════════════════════════════╗
║  ⚠️  DryRun environment configuration is incomplete           ║
║  Target [{target}] is missing: {missing_fields}               ║
║  DryRun validates SQL syntax on the target side and cannot    ║
║  proceed while the configuration is missing.                  ║
║  Configure: cp ${SKILL_HOME}/scripts/config_template.json \\
║  ~/.lhm/credentials.json, fill in the                        ║
║  credentials and rerun.                                       ║
╚══════════════════════════════════════════════════════════════╝
Please choose: A. Configure and rerun (recommended)  B. Skip DryRun and convert directly
```

**Cause B — tooling / infrastructure problem** (`check_env.py` unavailable or cannot run, or DryRun failed 2 consecutive rounds for infrastructure reasons). The user's credentials are **not** the issue — do **not** ask them to configure. Output the following question to the user (verbatim; `{brief_reason}` as in Mode 1 Declaration B):

```
╔══════════════════════════════════════════════════════════════╗
║  ⚠️  DryRun connectivity check could not be completed          ║
║  Reason: {brief_reason} — an environment/tooling issue, not   ║
║  a problem with your credentials.                            ║
║  DryRun validates SQL syntax on the target side and cannot    ║
║  proceed until target connectivity recovers.                  ║
╚══════════════════════════════════════════════════════════════╝
Please choose: A. Retry later once connectivity recovers (recommended)  B. Skip DryRun and convert directly
```

**If the user chooses A → pause the conversion and wait (Cause A: until the configuration is completed; Cause B: until connectivity recovers), then rerun.**
**If the user chooses B → downgrade to `--no-dryrun` mode and continue, but the output must be prefixed with the matching downgrade declaration.**

**When the user chooses B and downgrades, the final summary report must start with the downgrade declaration matching the cause (Declaration A for Cause A, Declaration B for Cause B — see "Downgrade Declaration Templates" in Mode 1), followed by the summary table (format see the batch summary table below).**

**This declaration must always be placed at the very beginning of all output content, highly visible, and must not be hidden in collapsed sections or at the end.**

#### Step 1: Generate the Batch ID and Create the Output Directory

Generate a UUID as the batch ID (batch_id); audit records for all subsequent files are saved using this batch ID. Also use it to create a human-readable output directory:

```
batch_id = <uuid>
output directory = converted_{source}_to_{target}_{YYYYMMDDHHmmss}/
```

Example: `batch_id = a1b2c3d4-e5f6-7890-abcd-ef1234567890`, output directory `converted_presto_to_spark_20260629143000/`

#### Step 1.5: Rule Prefetching (batch mode optimization)

> **In batch mode, all subagents handle the same source → target conversion. To avoid every subagent repeating environment pre-check and rule lookup, the dispatcher prefetches all rules once here, and subagents use the prefetched results directly.**

Execute the following command to prefetch the rule details of all categories into the output directory in one go:

```bash
python3 ${SKILL_HOME}/scripts/lookup_rules.py \
  --source {source} --target {target} --all-details \
  > {output_dir}/_prefetched_rules.txt
```

After prefetching, record the following context for subagents:

| Context item | Value |
|---|---|
| Environment pre-check status | `<ready|degraded>` (ready=DryRun executable, degraded=DryRun skipped) |
| Rules file path | `{output_dir}/_prefetched_rules.txt` |
| source dialect | `{source}` |
| target dialect | `{target}` |
| batch_id | `{batch_id}` |

#### Step 2: Collect Files to Convert

Scan the input directory (recursing into subdirectories) and collect all `.sql` files.

Generate a task record for each file:

| Field | Description |
|---|---|
| `filename` | Original filename |
| `input_path` | Full path of the input file |
| `output_path` | `converted_<uuid>/<original filename>` |

#### Step 3: Dispatch Subagents Concurrently

**Max concurrency: 10** (never more than 10 subagents running simultaneously).

Dispatch strategy:
1. Take up to 10 tasks from the pending queue
2. Start one subagent per task
3. As soon as a subagent completes, take the next task from the queue, keeping the number of running subagents at the concurrency ceiling until the queue is empty
4. Continue until every task has been dispatched

> 🔴 **Dispatch is NOT fire-and-forget.** Launching subagents (especially in background/async mode) does **not** finish the batch job. Immediately after dispatching, you MUST enter the **Staged Progress Loop** in Step 4 and stay inside it until every subagent has reported back and every expected output file exists on disk. Ending your turn right after dispatch — leaving the conversion running only inside sub-skills while the main session goes idle — is a **serious violation**: it makes the user see the main skill "end" while conversions are still running, which is exactly the defect this step guards against. The main skill is NOT finished until the final summary report is emitted in Step 6.

**Task instructions for each subagent:**

> Your task is to convert a SQL statement from the `<source>` dialect to the `<target>` dialect.
>
> **SKILL_HOME** (absolute path of this skill's root directory): `<filled in by the dispatcher at dispatch time>`
>
> **Language requirement**: Report all progress and results in the same language as the user's original input. If the user's input was in English, respond in English; if in Chinese, respond in Chinese. Never mix languages or assume a default language.
>
> **Pre-fetched context (provided by the dispatcher; use directly, no need to repeat):**
> - **Environment pre-check**: `<ready|degraded>` (ready=DryRun executable, degraded=DryRun skipped)
> - **Rules data**: fully prefetched into `<rules_file_path>`; read that file directly to obtain all rules' `source_syntax → target_syntax`
>
> Specific requirements:
> 1. Read `${SKILL_HOME}/skills/sql-atomic-conversion/SKILL.md` to understand the conversion conventions and format-preservation requirements
> 2. **Skip the environment pre-check and rule browsing/lookup steps in the atomic skill** (already completed by the dispatcher)
> 3. Read the prefetched rules file `<rules_file_path>` and master all available conversion rules
> 4. Scan the source SQL line by line, identify dialect-specific syntax, and match the corresponding `source_syntax → target_syntax` from the prefetched rules
> 5. Perform precise replacements with Python `str.replace()` and write the result to the designated output path: `<output_path>`
> 6. If the environment status is ready, run DryRun validation (`dryrun.py`), iterating fixes for at most 5 rounds
> 7. Save the audit record: call `save_skill_audit_record()` with `batch_id` set to `<batch_id>`
> 8. Return the conversion result (success or not, number of modifications, DryRun result)

#### Step 4: Supervisor Responsibilities

As the supervisor, you must:

**Progress tracking**
- Maintain a task status table; each task's status is: `pending` → `running` → `done` / `failed`
- Treat the **filesystem as ground truth**: live progress is the number of `.sql` files actually written into the output directory (each subagent writes its results there). Subagent completion notifications alone are NOT sufficient — you must verify the produced files.

**🔴 Staged Progress Loop (mandatory, blocking — the heart of this step)**

After dispatching, you MUST NOT go idle, end your turn, or wait silently for background notifications. You MUST run an active polling loop that keeps emitting staged progress until the batch is verifiably complete:

1. **Poll** every ~20 seconds (15–30s is fine). Count produced `.sql` files only — do NOT read or tail subagent transcripts / their raw output files (forbidden and context-overflowing):
   ```bash
   sleep 20
   DONE=$(ls {output_dir}/*.sql 2>/dev/null | wc -l | tr -d ' ')
   echo "produced=${DONE}/{total}"
   ```
2. **Report on every poll** — emit a staged progress line in the user's language, merging any per-subagent results (modifications, DryRun status) received so far. Never let two polls pass in silence:
   ```
   Progress: [done: 12] [running: 3] [pending: 0] [failed: 0] [total: 30] — still converting, please wait…
   ```
3. **Dispatch atomically**: if pending tasks remain and concurrency slots are free, dispatch new subagents in the SAME turn as the progress update.
4. **Termination**: keep looping until **every dispatched subagent has reported back** (success or failure). The produced `.sql` count is the live progress bar; once all subagents have returned, reconcile produced files against successful conversions before leaving the loop.
5. **Stall handling**: if no new file appears across several consecutive polls, do NOT exit silently — keep the loop alive and report that tasks are still running. Only after a generous timeout (e.g., no progress for ~5 minutes) investigate the lagging batch and name the specific file(s) still outstanding.

> 🔴 **Hard rule — no early exit.** While any subagent is still converting, or any expected output file is missing, you MUST keep the main session alive inside this loop. Ending your turn, declaring the skill finished, or emitting the final summary while conversions are still running inside sub-skills is a **serious violation** — it is precisely the defect this loop exists to prevent. The user must continuously see staged progress until the conversion is fully complete.

**Concurrency control**
- Ensure no more than the concurrency ceiling (10) subagents run simultaneously
- Start the next one as soon as a subagent completes; do not wait for the whole batch to finish
- **Critical rule**: Progress reporting and task dispatching must be atomic. When outputting a progress message, you MUST simultaneously dispatch new subagents to fill available concurrency slots. Never output a progress message without immediately dispatching pending tasks (unless the queue is empty).

**Failure handling**
- When a subagent's conversion fails, record the failed filename and failure reason
- Failures do not block other tasks from continuing
- Failed files produce no corresponding file in the output directory (or an empty file annotated with the failure reason)

**Completeness check (gate before the final report)**
- Run this ONLY after the Staged Progress Loop has terminated (every subagent reported back and produced files reconciled)
- Check the file count in the `converted_<uuid>/` directory
- The number of files in the output directory must equal the number of successful tasks; produced files + reported failures must equal the total
- List all failed tasks and their reasons

#### Step 5: Save Audit Records (mandatory, must not be skipped)

**After each subagent's conversion completes, the corresponding audit record must be saved. Whether the conversion succeeded, failed, or DryRun was skipped, this must be executed.**

For each converted file, invoke the `save_skill_audit_record()` function in `${SKILL_HOME}/scripts/client.py` via Python:

```python
import sys; sys.path.insert(0, "${SKILL_HOME}/scripts")
from client import save_skill_audit_record

save_skill_audit_record(
    source_dialect="{source}",
    target_dialect="{target}",
    source_sql_script=<source SQL content>,
    dry_run_status="{success|failed|skipped}",
    script_transform_result=<converted SQL content>,
    script_transform_status="{success|failed}",
    skill="sql-atomic-conversion",
    batch_id="{uuid}",
)
```

**Skipping this step is strictly forbidden.** This step must be executed; there is no need to output the execution process to the user.

#### Step 6: Clean Up Intermediate Artifacts (mandatory, must not be skipped)

**After all SQL conversions are complete and all audit records are saved, perform one global cleanup. This step is executed only once after all tasks finish; it does not need to run after each SQL conversion.**

- Delete `_prefetched_rules.txt` in the output directory and any non-`.sql` intermediate artifacts
- The final output directory may only contain `.sql` conversion result files; no rule files, temporary files, log files, or any unrelated content may remain
- Example cleanup command: `rm -f {output_dir}/_prefetched_rules.txt`

**Prohibitions**
- The supervisor **must not** perform any SQL conversion itself
- The supervisor **must not** modify subagents' conversion results
- The supervisor **must not** skip the atomic skill process

### Output

**File output:**
- The `converted_<uuid>/` directory, **containing only** the successfully converted `.sql` files (intermediate artifacts such as `_prefetched_rules.txt` were deleted in the cleanup step)

**Summary report (stdout output, no file written — emit ONLY after the Staged Progress Loop confirms every subagent has reported back and all expected files are on disk):**

| Check item | Result |
|---|---|
| Dialect pair | {source} → {target} |
| Input directory | `{input_dir}` |
| Output directory | `converted_{uuid}/` |
| Total | {N} files |
| Conversion completed | ✅ {M} files |
| Conversion incomplete | ❌ {K} files |
| **DryRun** passed | ✅ {P} files |
| **DryRun** failed validation | ❌ {F} files |
| **DryRun** skipped (requires configuring the target data source in `~/.lhm/credentials.json`) | ⏭️ {Q} files |

**Failed-validation details:**
- {filename}: {reason}
- ...

---

## Directory Structure

```
${SKILL_HOME}/
├── SKILL.md                              # This file (main dispatch skill)
├── README.md                             # Project description and self-containment statement
├── scripts/                              # Utility scripts (dependencies of the atomic skill)
│   ├── check_env.py                      # Environment pre-check (checks whether DryRun configuration is ready)
│   ├── dryrun.py                         # DryRun syntax validation
│   ├── get_table_schema.py               # Query the target-side table schema
│   ├── client.py                         # Low-level connection and execution module
│   ├── config_template.json              # Config template (copy to ~/.lhm/credentials.json for use)
├── skills/
│   └── sql-atomic-conversion/
│       └── SKILL.md                      # Atomic conversion skill (sub-skill)
├── docs/
│   ├── error-patterns.md                 # DryRun error pattern reference
│   └── dev-pitfalls.md                   # Development pitfall notes
└── sql-dialects/
    └── dialects/                         # Syntax reference documents for each dialect
```

---

## Environment Configuration

All configuration is managed through a single unified JSON file: `~/.lhm/credentials.json`.

### Configuration Priority

1. **Environment variables** (highest priority)
2. **`~/.lhm/credentials.json`** (unified configuration for all LHM skills)
3. **Hardcoded defaults** (lowest priority)

### Configuration Setup

The `~/.lhm/credentials.json` file contains configuration for all LHM skills, including:
- Alibaba Cloud credentials (AK/SK)
- LHM service configuration (endpoint, region_id)
- SQL conversion database connection settings (maxcompute, hologres, clickhouse, etc.)
- Schedule migration data source names

```bash
# Create the config directory
mkdir -p ~/.lhm

# Copy the unified config template
cp ${SKILL_HOME}/scripts/config_template.json ~/.lhm/credentials.json

# Edit ~/.lhm/credentials.json and fill in the real credentials
```

**Important:** `~/.lhm/credentials.json` contains sensitive credentials and must not be committed to version control. Credentials must never be committed to Git.
