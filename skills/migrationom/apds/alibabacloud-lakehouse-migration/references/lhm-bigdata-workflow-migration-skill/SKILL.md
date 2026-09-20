---
name: lhm-sch-workflowmigration
description: |
  User-facing entry Skill for LHM schedule migration (workflow migration). Provides three capabilities:
  (1) Query skill capabilities — output the skill introduction document;
  (2) Create data source — recognize "建数据源/创建数据源" (create data source) instructions and route to lhm-sch-ds
  to complete data source creation, name validation, metadata upload, and connectivity testing;
  (3) Schedule migration — complete a migration instruction end-to-end: config validation → environment
  initialization (lhm-sch-env) → data source existence check (lhm-sch-ds) → workflow exploration & conversion
  (lhm-sch-read-exec) → deployment & upload to DataWorks (lhm-sch-deploy).

  Triggers: asking what this skill can do / introducing capabilities; instructions such as
  "建数据源 / 创建（新增、添加）一个 XX 类型的数据源" (create a data source of type XX);
  or migration instructions such as "把 <源数据源> 迁移到 <目标数据源>" (migrate <source> to <target>),
  in natural language or the -source/-tag/-exStr/-dir parameter form, as well as any request mentioning
  migrating scheduler systems such as DolphinScheduler / Airflow to DataWorks.

  Do not trigger for: SQL conversion (sql-trans), DDL migration (ddl-trans), data validation (DataCheck),
  or other non-schedule-migration tasks.
---

# LHM Schedule Migration User Entry

This Skill is the **user-facing master Playbook**. It does not call APIs directly; it recognizes user intent, routes to the execution sub-skills under the `skill` directory, and handles state hand-off between stages and communication with the user.

> 🧭 **STEP 0 — Mandatory Scope Classification Gate (run this BEFORE any tool call, any todo/plan item, and any environment setup).** Read the user's message once and freeze the scope using the "Capability Selection Rule" below. State the decision explicitly to yourself before doing anything else, e.g. *"Scope: Capability 2 only — the migration mention is generic (no data source name), so Capability 3 is NOT actionable."* This classification is the very first step of the run; nothing — not the plugin gate, not `setup_session.sh`, not a todo list — happens before it.
>
> **Hard gate — Capability 3 (schedule migration) is actionable ONLY if the message names at least one concrete data source** ("migrate X to Y", "migrate X", or the `-source X` / `-tag Y` parameter form). When Capability 3 is **not** actionable, you MUST NOT, at any point in the whole run:
> - create any Capability 3 / migration todo, plan item, or "remaining migration work" tracker;
> - run `setup_session.sh` in the stage-less (`all`) form, or install `lhm-sch-read-exec` / `lhm-sch-deploy` — a data-source-only run uses `--stage ds` (see Capability 2);
> - ask for, mention, or collect source/target data source names, SQL dialect conversion expressions, or config-file paths;
> - bundle migration parameters into the same clarification question as data-source parameters;
> - append any "to continue with the (scheduled task) migration, I still need …" trailer, offer a fillable migration config template, or list exploration/conversion/deployment as pending work in the final message.
>
> A generic migration mention — e.g. "perform scheduled task migration in this lakehouse migration", "help me with the workflow migration" — is **background context, never a task and never a parameter-collection target**. Treating it as actionable is the single most common defect in this playbook and is exactly what causes the run to fail to terminate after a successful data-source creation. Once the scope is frozen here it must never be widened afterwards.

> ⛔ **Plugin prerequisite — hard stop (mirrors the LHM dispatcher's Step 2.1 Hard Stop Gate)**: every execution sub-skill below (`lhm-sch-ds`, `lhm-sch-env`, `lhm-sch-read-exec`, `lhm-sch-deploy`) reaches the service through `aliyun lhm <command>`, which requires the `aliyun-cli-lhm` plugin (>= 0.1.1, i.e. `~/.aliyun/plugins/aliyun-cli-lhm/manifest.json` must exist). Verify it before anything else; when this Skill is entered directly rather than through the dispatcher, run the dispatcher's `scripts/install_lhm_plugin.sh` and treat a non-zero exit as fatal.
>
> If the plugin is unavailable, **stop immediately**: report the environment error verbatim and terminate. Do **not** ask the user for the data source name, type, or any other business parameter; do **not** run `uv tool install`, `lhm-sch-ds`, or any other command in this playbook; do **not** fabricate a result. A CLI that installs successfully still cannot reach the service — it shells out to `aliyun lhm` through its `aliyun_cli.py` layer — so a successful install is never proof that the flow can proceed.

## Path Convention (SKILL_HOME)

`SKILL_HOME` is the absolute path of the directory containing this SKILL.md. Determine it before executing any command:

```bash
# SKILL_HOME = <absolute path of the directory containing this SKILL.md>
echo $SKILL_HOME  # confirm the path is correct before any command
```

- Every path of the form `skill/...` in this file is relative to `${SKILL_HOME}`; expand it to `${SKILL_HOME}/skill/...` before execution. Never rely on the current working directory (pwd).
- The sub-skills under `skill` are **not registered as invokable skills** by the discovery mechanism; load them by file path only, and when delegating to a sub-agent, pass the fully resolved absolute paths.

It provides three capabilities:

| Capability | Trigger | Action |
|------------|---------|--------|
| Capability 1: Query skill capabilities | User asks "what can this skill do / introduce its capabilities" | Output the content of [docs/introduction.md](docs/introduction.md) |
| Capability 2: Create data source | Instructions to create a data source (see trigger phrases below; the Chinese trigger phrases are declared in the frontmatter description) | Route to [skill/lhm-sch-ds/SKILL.md](skill/lhm-sch-ds/SKILL.md) to complete data source creation |
| Capability 3: Schedule migration | A migration instruction (see trigger phrases below) | Config validation → environment initialization → data source existence check → exploration & conversion → deployment & upload |

## Capability Selection Rule (Mandatory)

A single user message can mention more than one capability. Classify the request **once, before any tool call**, by the executable instructions it actually carries — not by the topics it mentions. The scope decided here is frozen for the whole run and must never be widened afterwards.

### Actionability test

| Capability | Actionable when | NOT actionable when |
|------------|-----------------|---------------------|
| Capability 2 (create data source) | The message carries a create/add-data-source instruction — a bare "create a data source" counts; its missing parameters are collected with **one** clarification question | The message only mentions data sources in passing without any create/add intent |
| Capability 3 (schedule migration) | The message carries a migration instruction that names **at least one concrete data source**: "migrate X to Y", "migrate X", or the `-source X` / `-tag Y` parameter form | Migration is mentioned only **generically**, with no data source name at all — e.g. "perform scheduled task migration in this lakehouse migration", "help me with the workflow migration". A generic mention is background context: it is **not** a task to execute, and **not** a task to collect parameters for |

### Decision table

| Create-data-source instruction | Actionable migration instruction | What to run | What to ask |
|---|---|---|---|
| Present | Absent | **Capability 2 only** → report → **END** | Only the missing data source parameters. **Never** ask for source/target data source names, never mention outstanding migration work |
| Present | Present | Capability 2 first, then Capability 3 using the names already extracted from the instruction | Only parameters genuinely missing from the migration instruction (e.g. the target when only the source was named) |
| Absent | Present | Capability 3, Steps 1-5 | Only the missing migration parameters |
| Absent | Absent | Nothing yet — no cloud call, no CLI install | One focused question asking the user to state either the migration instruction (source/target) or the data source to create |

### Hard constraints

1. **Scope is frozen at classification time.** When Capability 3 is not actionable, do not create a Capability 3 plan item / todo, do not install `lhm-sch-read-exec` or `lhm-sch-deploy`, and do not track "remaining migration work".
2. **One question, one capability.** A clarification question may only ask for parameters belonging to the capability currently being executed. Bundling data-source-creation parameters and migration parameters into the same question is forbidden.
3. **No deferred-parameter bookkeeping.** Never report the run as "blocked on migration parameters" when migration is not actionable, and never hand the user a fillable migration template as a suggested next step.
4. **Capability 2 is terminal.** Once the data source is created — or the user-requested connectivity test finishes — the run is over. See "Termination" under Capability 2.

## Capability 1: Query Skill Capabilities

When the user asks about this skill's capabilities, use cases, or introduction:

1. Read [docs/introduction.md](docs/introduction.md) and **output the document content to the user verbatim** — do not rewrite or excerpt it.
2. If the document does not exist or is empty, tell the user that the introduction document is not yet available, and briefly provide example trigger phrases for Capability 2 and Capability 3.

This capability does not execute any scripts and does not enter the migration flow.

## Capability 2: Create Data Source

### Trigger Phrases

Recognize the semantics of create / add a data source (the Chinese trigger phrases are declared in the frontmatter description). Examples:

```
Example 1 (short instruction):
  建数据源

Example 2 (natural language + full parameters):
  创建一个 DolphinScheduler类型版本是1.3.9的数据源，名字叫 test_TC_RE_6，
  host 是 http://10.0.0.1:12345，token 是 abc123，项目是 proj1
  (Create a DolphinScheduler data source of version 1.3.9 named test_TC_RE_6,
  host is http://10.0.0.1:12345, token is abc123, project is proj1)
```

Parameters that may be carried by the instruction: data source type (dsType), version (dsVersion), name (dsName), host/endpoint, token, project, local metadata file path (source file, optional), etc.

### Handling: Delegate to lhm-sch-ds

Once the trigger semantics match, **pass the user instruction verbatim to [skill/lhm-sch-ds/SKILL.md](skill/lhm-sch-ds/SKILL.md)**, which completes the full orchestration: parameter extraction & validation → query same-name data sources (check) → name uniqueness validation (check-name) → metadata file upload (upload, if any) → creation (create) → optional connectivity test (test-conn).

- This entry does not parse, rewrite, or complete any data source parameters; when parameters are missing or validation fails, lhm-sch-ds follows up with the user via AskUserQuestion per its SKILL.md rules — **guessing is forbidden**.
- lhm-sch-ds depends on the session environment prepared by lhm-sch-env; if an environment-class error is reported during execution (missing credentials, command not found), follow [skill/lhm-sch-env/SKILL.md](skill/lhm-sch-env/SKILL.md) to guide the user to initialize the environment and retry. During this process, **never fill in secrets on behalf of the user, and never echo secret values**.
- **Environment scope for a data-source-only run**: when Capability 3 is not actionable (see the Capability Selection Rule), prepare the session with the data-source stage only, so that just `lhm-sch-env` + `lhm-sch-ds` are installed and the migration source/target names are not required:

  ```bash
  bash ${SKILL_HOME}/skill/lhm-sch-env/scripts/setup_session.sh --stage ds --auto-install
  ```

  Do **not** run the stage-less (`all`) form in this case: it installs the exploration/deployment CLIs and demands `source_data_source_name` / `target_data_source_name`, which a create-data-source request legitimately does not have.
- User-facing output follows the "User-Facing Output General Rules" below and the output rules of lhm-sch-ds: only show natural-language progress (e.g., "Validating the data source name...", "✓ Data source created successfully"); never expose command lines, JSON, `ds_id`, or other internal information.
- **Termination (mandatory)**: the connectivity test (`test-conn`) is run **only** when the user explicitly requested it in the instruction — never ask proactively. Once creation succeeds (report "✓ Data source created successfully"), or the requested connectivity test finishes, this capability is **complete**: report the final result and **end**. Do **not** loop back, do **not** ask any further follow-up question, and do **not** keep the session waiting.

  The final message must contain the creation result and nothing else. Explicitly forbidden in it:
  - any "to continue with the scheduled task migration, I still need ..." trailer, or any other prompt for source/target data source names, SQL dialect conversion expressions, or config file paths;
  - offering a fillable migration config template as a next step;
  - listing exploration / conversion / deployment as "not executed" or "pending" work;
  - asking whether to test connectivity, deploy, or proceed further.

  This holds **even when the original request also mentioned migration generically**: a generic mention is not an actionable migration instruction, so there is no migration work left to report and no migration parameter left to collect.

**Relationship to Capability 3 — one narrow exception**: this capability is independent of the schedule migration flow. The **only** situation in which the flow re-enters Capability 3 after a creation is when Capability 3 was **already running** with source/target names **already extracted from the user's instruction**, and its Step 3 or Step 4 reported "data source does not exist"; then return to Step 3 and retry. In every other case creation completes the run — do not re-enter Capability 3, do not ask for source/target names, and do not report outstanding migration work.

## Capability 3: Schedule Migration

### Trigger Phrases and Parameter Extraction

Three forms of migration instructions are supported:

```
Example 1 (natural language):
  把 test_TC_RE_1 迁移到 dw_test_fengling_0318 配置文件路径 xxxx.json
  (Migrate test_TC_RE_1 to dw_test_fengling_0318, config file path xxxx.json)

Example 2 (natural language + SQL dialect conversion):
  把数据源 test_TC_RE_5a 迁移到 dw_test_fengling_0318 数据源 将DWSSQL转到HOLOGRES_SQL 配置文件 xxx.json
  (Migrate data source test_TC_RE_5a to data source dw_test_fengling_0318, converting DWSSQL to HOLOGRES_SQL, config file xxx.json)

Example 3 (parameter form):
  -source test_TC_RE_5a -tag dw_test_fengling_0318 -exStr 将DWSSQL转到HOLOGRES_SQL -dir xxx.json
```

Extract four parameters from the instruction:

| Parameter | Natural-language source | Parameter-form source | Required |
|-----------|-------------------------|-----------------------|----------|
| Source data source name | X in "migrate (data source) X to ..." | `-source` | Yes |
| Target data source name | Y in "... migrate to Y (data source)" | `-tag` | Yes |
| SQL dialect conversion expression | "convert A to B" (e.g., convert DWSSQL to HOLOGRES_SQL) | `-exStr` | No |
| Config file path | "config file (path) xxx.json" | `-dir` | No |

**Extraction rules:**
- This step is reached **only** when the migration instruction is actionable per the Capability Selection Rule (at least one concrete data source name is present). A generic migration mention with no data source name never reaches here — it must not be turned into a parameter-collection question.
- When the natural-language form is used, the **source data source** and **target data source** names must first be extracted accurately; all subsequent steps use the extracted names.
- If any required parameter is missing or cannot be clearly identified → follow up via AskUserQuestion; **guessing is forbidden**. The question asks **only** for the missing migration parameter(s) — never bundle in data-source-creation parameters, and never re-ask for a name the user has already given.
- The SQL dialect conversion expression is optional; do not proactively ask about it when the user has not mentioned it.

### Step 1 — Config File Validation (Python script)

If a config file path is provided, write the source/target data source names extracted from the trigger phrase into the config file's `source_data_source_name` / `target_data_source_name` fields (**only these two fields may be modified**; all other fields such as `endpoint` and `region_id` must not be touched), then invoke the validation script to check for missing fields:

```bash
python3 ${SKILL_HOME}/skill/lhm-sch-env/scripts/session_writer.py --check-only --from <config file path>
```

If no config file path is provided, skip this step and proceed directly to Step 2. The session configuration will be created with default values, and the source/target data source names will be set from the trigger phrase.

The following **business config** fields are mandatory and must be written into the config file: `source_data_source_name` / `target_data_source_name`. Placeholders and template example values are treated as unfilled. Credential fields must NOT be in the config file; credentials are resolved through the default credential chain (environment variables, RAM Role, or `~/.alibabacloud/credentials`).

> **Note**: `endpoint` and `region_id` are read from the `lhm` section of the config file (`lhm.endpoint` / `lhm.region_id`) and attached to **every** `aliyun lhm` call as the fixed parameters `--endpoint` / `--region`. When they are absent from the config file, the CLIs fall back to the environment variables (`LHM_ENDPOINT` / `REGION_ID`) and then to built-in defaults; explicit CLI arguments (`--endpoint` / `--region`) always take the highest precedence.

- **Exit code 0** → validation passed; proceed to Step 2.
- **Exit code 1** → read the `blockers` list from the output JSON, translate the missing fields into natural language and inform the user (e.g., "The config file is missing source_data_source_name / target_data_source_name"), and ask the user to complete them before rerunning this step.
- Interaction constraint: **never fill in secrets on behalf of the user, and never echo secret values**.

### Step 2 — Environment Initialization and Config Transcription (delegate to lhm-sch-env)

After validation passes (or if no config file was provided), initialize the CLI environment and transcribe the session configuration. Follow the execution details in [skill/lhm-sch-env/SKILL.md](skill/lhm-sch-env/SKILL.md):

```bash
# If config file path is provided:
bash ${SKILL_HOME}/skill/lhm-sch-env/scripts/setup_session.sh --from <config file path> --auto-install

# If no config file path is provided:
bash ${SKILL_HOME}/skill/lhm-sch-env/scripts/setup_session.sh --auto-install
```

This script installs the lhm-sch-* CLIs, validates the configuration, and transcribes it into a temporary configuration for the current session (each session creates a dedicated directory `/tmp/lhm-sch-session-<uid>/s-<timestamp>-<random>/session.json`, containing the back-filled source/target data source names); sub-skill CLIs locate and load it automatically via a pointer file.

- **Exit code 0** → session ready; echo a single-line summary, then proceed to Step 3; no further validation in later stages.
- **Exit code 1** → read the reported blockers, guide the user to complete them, and rerun this script.

The session is prepared only once within a session; rerun this step only when a business command actually reports an environment-class error (expired credentials, user changed the configuration).

### Step 3 — Validate Data Source Existence (lhm-sch-ds CLI)

After the session is ready, invoke the `check` command provided by [skill/lhm-sch-ds/SKILL.md](skill/lhm-sch-ds/SKILL.md) for the **source data source** and **target data source** respectively, to confirm each is registered and unique in LHM:

```bash
lhm-sch-ds check --ds-name <data source name> --category-type WORKFLOW
```

**Invocation conventions:**
- `--ds-name`: use the source/target data source names extracted from the trigger phrase; execute once for each;
- `--ds-type`: **do not pass**; the CLI sends dsType as an empty string `""` by default and does not filter by type;
- `--category-type`: **fixed value `WORKFLOW`**.

**Result judgment** (per the status-code contract of lhm-sch-ds):

| Result | Judgment | Agent action |
|--------|----------|--------------|
| `match` with exactly one entry in `matches` | Data source OK | Continue checking the next one; both pass → proceed to Step 4 |
| `empty` (no match found) | Data source has a problem | Tell the user the data source does not exist; guide them to create it via Capability 2, then rerun this step |
| `match` with multiple entries | Data source has a problem | List the same-name data sources in natural language and ask the user to investigate until uniqueness is confirmed, then rerun this step |
| `failed` | API error | Translate the reason into natural language, inform the user, and abort the flow |

- **Only when both the source and target data sources pass validation can the flow proceed to Step 4**; if either has a problem, do not continue.
- On the user side, only show "Checking whether the data sources exist..." and the conclusion; never expose command lines, JSON, `status` values, or internal IDs.

### Step 4 — Workflow Exploration and Conversion (delegate to lhm-sch-read-exec)

Pass the migration instruction to [skill/lhm-sch-read-exec/SKILL.md](skill/lhm-sch-read-exec/SKILL.md), which completes exploration (read) and conversion (convert) of the scheduled jobs. **Passing rules:**

- If the user input is in the **Example 1 / Example 2** form → **remove the config-file expression and pass it verbatim**;
- If the user input is in the **Example 3** parameter form → first transcribe it into the natural-language form of Example 1/2 and then pass it (`-source` → "migrate data source X", `-tag` → "to data source Y", `-exStr` → append the dialect conversion expression), likewise without the config-file expression.

```
Transcription result of Example 3:
  把数据源 test_TC_RE_5a 迁移到 dw_test_fengling_0318 数据源 将DWSSQL转到HOLOGRES_SQL
```

- The environment was readied in Step 2 and the data sources were validated in Step 3, so that skill performs no further environment validation.
- The specific exploration/conversion commands, status-code branches, polling rules, and result rendering are all governed by its SKILL.md.
- After a successful conversion, the CLI automatically writes `task_id` into `output/readexec.json` and the session config's `migration.convert_task_id`, and extracts the conversion result package into `output/ds-cli/result/`.
- If it still returns "data source does not exist" → tell the user the data source must be created first (via Capability 2, delegated to [skill/lhm-sch-ds/SKILL.md](skill/lhm-sch-ds/SKILL.md)), and retry from Step 3 after creation completes.

### Step 5 — Deployment & Upload (delegate to lhm-sch-deploy)

After the conversion completes and the conversion summary has been reported to the user, **deploy only after user confirmation** (deployment is a write operation and requires explicit human confirmation). Follow the execution details in [skill/lhm-sch-deploy/SKILL.md](skill/lhm-sch-deploy/SKILL.md):

```bash
lhm-sch-deploy
```

- `task_id` does not need to be passed explicitly: the CLI reads it automatically from the session config's `migration.convert_task_id`; when unavailable, it resolves in the order: explicitly provided by user > `output/readexec.json` > ask the user.
- It automatically completes trigger → polling → result retrieval → report generation, and presents the deployment result summary to the user.
- After an interruption, use `--skip-start` to resume polling.

### State Hand-off and Wrap-up

**Inter-stage state (tracked internally by the Agent; internal IDs are never shown to the user):**

| State | Produced by | Consumed by |
|-------|-------------|-------------|
| Source/target data source names | Extracted from trigger phrase → back-filled into the config file in Step 1 → session config `migration.*` | Step 3, Step 4 |
| `task_id` | Successful conversion in Step 4 (automatically written to `output/readexec.json` + session config) | Step 5 |

After the entire migration completes, remind the user to clean up the session configuration (it lives in the system temp directory and holds no credentials):

```bash
bash ${SKILL_HOME}/skill/lhm-sch-env/scripts/setup_session.sh --cleanup
```

### Final Summary (mandatory output)

After the migration flow ends (including session cleanup), a **Migration Result Summary** in table form **must** be output to the user. The data comes respectively from the exploration result and conversion result of Step 4 and the deployment result of Step 5. Render it with the following fixed template (fill `-` for unavailable metrics; if a stage was not executed or failed, annotate it truthfully — never omit the entire table). The summary may be delivered in the user's language:

```markdown
## Migration Result Summary

**Migration link**: `<source data source>` → `<target data source>` | **Environment**: <staging/production + region>

### 1. Exploration Result Data

| Metric | Value |
|--------|-------|
| Source data source | <source data source name> |
| Workflow count | <workflow_count> |
| Node count | <node_count> |
| Script count | <script_count> |
| Node type distribution | <type1: n | type2: n | ...> |
| Exploration result | ✅ Complete / ❌ Failed (reason) |

### 2. Conversion Result Data

| Metric | Value |
|--------|-------|
| Conversion direction | <source> → <target> |
| SQL dialect conversion | <dialect mapping / none (not specified)> |
| Workflow count | <total_workflows> |
| Total node count | <total_nodes> |
| Successful nodes | <success_nodes> |
| Failed nodes | <failed_nodes> |
| Downgraded nodes | <downgrade count> |
| Success rate | <percentage> |
| Export package | `<conversion result package path>` |
| Conversion result | ✅ All successful / ⚠️ Partially successful / ❌ Failed |

### 3. Submission & Upload Data

| Metric | Value |
|--------|-------|
| Deployment status | ✅ All successful / ⚠️ Partially successful / ❌ Failed |
| Completion time | <deployment completion time> |
| Total workflows | <n> (successful <n> | failed <n>) |
| Total nodes | <n> |
| Result directory | `<output/deploy/result/<timestamp>/>` |
| Detailed report | `<deploy_report.md path>` |

**Deployed workflow details**:

| Workflow name | Status | Node count |
|---------------|--------|------------|
| <workflow 1> | ✅ Successful | <n> |
| <workflow 2> | ✅ Successful | <n> |

### Conclusion

| Stage | Result | Key data |
|-------|--------|----------|
| ① Exploration | ✅ Complete | <n> workflows / <n> nodes / <n> scripts |
| ② Conversion | ✅ All successful | <n>/<n> nodes successful, <n> failed, <n> downgraded |
| ③ Submission & upload | ✅ All successful | <n>/<n> workflows deployed successfully, <n> nodes in total |
```

Rendering constraints:

- Follow the "User-Facing Output General Rules": the summary **must not** contain internal IDs such as `task_id`, `instance_id`, or `request_id`, and must never echo any credential information.
- If the user has not confirmed deployment (the flow stopped at Step 4), keep only the deployment status row in the "Submission & Upload Data" table, annotated as "Not executed (user did not confirm)", and annotate the corresponding row in the conclusion table accordingly.
- End the summary with a one-sentence statement of the overall result and session config cleanup status (e.g., "This end-to-end migration was fully successful; the session config has been cleaned up.").


## User-Facing Output General Rules

Every sub-skill defines strict "user-facing output rules"; this entry follows them as well:

- The user sees **natural-language progress narration** (e.g., "Validating configuration...", "Still converting, please wait..."); never expose raw command lines, JSON output, `status` values, `err_code`, `request_id`, exit codes, or internal IDs.
- On failure, translate the reason into **actionable guidance** (e.g., "The data source does not exist; it must be created first"); technical details stay in internal logs only.
- Every decision point that requires user judgment (missing-parameter follow-up, config completion, whether to deploy, etc.) must be explicitly asked via AskUserQuestion; never make decisions on behalf of the user. **This applies only to decision points inside the scope frozen by the Capability Selection Rule** — a parameter belonging to a capability that was never triggered is not a decision point, so it must not be asked about.
- **A completed run ends with its result, not with a question.** When the triggered capability has finished, the final message reports the outcome and stops; it does not advertise work that was out of scope, and it does not invite the user to supply parameters for a capability that was never triggered.
