---
name: alibabacloud-lakehouse-migration
version: 1.0.0
description: Unified dispatch entry point for the LHM (Lakehouse Migration Center) skill, coordinating the three core capabilities of SQL conversion, data validation, and big-data workflow migration. Use when the user raises a lakehouse migration requirement, such as SQL dialect conversion (e.g., "presto to spark", "hive to maxcompute", "转换 SQL", "SQL 转换", "方言转换"), pre/post-migration data validation / data consistency comparison ("数据校验", "数据比对", "一致性检查", "跑校验", "数据量校验", "指标校验"), migration of scheduled workflows such as DataWorks/DolphinScheduler/Airflow ("工作流迁移", "调度任务迁移", "建数据源", "创建数据源", "把 X 迁移到 Y"), or when the user is unsure which sub-skill to use or needs cross-skill collaboration.
---

# LHM Lakehouse Migration Unified Dispatcher

This skill is the unified entry point for the three core skills of Alibaba Cloud Lakehouse Migration Center (LHM). It analyzes user intent and intelligently routes requests to the corresponding sub-skill for execution.

## Supported Sub-Skills

| Skill | Description | Trigger Scenario |
|-------|-------------|------------------|
| **SQL Conversion** | Converts SQL from a source dialect to a target analytics-engine dialect | User provides SQL text or a directory and specifies source/target dialects |
| **Data Validation** | Validates data consistency across heterogeneous data sources | User needs to compare data before/after migration or verify data integrity |
| **Big-Data Workflow Migration** | Migrates scheduled jobs, environment configurations, and deployment execution | User needs to migrate DataWorks/MaxCompute or similar workflows |

> All three sub-skills are peer-level packages that live alongside this dispatcher in the same monorepo. In a monorepo deployment they are accessed by **absolute file path** under `${SKILL_HOME}`; when installed as independent Skill packages they can also be invoked by **skill name**. The Agent must try both approaches (path first, then name) before concluding a sub-skill is unavailable.
>
> ⚠️ **Discovery boundary**: skill discovery registers only the top-level SKILL.md of each installed package. Files nested inside a package (e.g., `skill/lhm-sch-*/SKILL.md`, `skills/sql-atomic-conversion/SKILL.md`, `atomic-skills/lhm-*/SKILL.md`) are **NOT registered as invokable skills** — they can only be loaded by file path from within their parent package. Never route to them with "Invoke skill: ..."; route to them by absolute file path resolved from the parent package's `SKILL_HOME`.

## Path Resolution (SKILL_HOME)

`${SKILL_HOME}` appears throughout this file. It is **not** a pre-set environment variable — the Agent must resolve it before running any command. `SKILL_HOME` is the absolute path of the directory containing this SKILL.md:

```bash
# If the load path of this SKILL.md is known, take its containing directory:
# SKILL_HOME = <absolute path of the directory containing this SKILL.md>
echo $SKILL_HOME  # confirm the path is correct before any command
```

All subsequent `${SKILL_HOME}/...` paths must be expanded to this absolute path before execution; never leave the literal `${SKILL_HOME}` token in a shell command.

**Sub-skill location**: all three sub-skill packages reside under the `subSkill/` subdirectory within `SKILL_HOME`. The canonical path for a sub-skill's SKILL.md is:
```
${SKILL_HOME}/subSkill/<sub-skill-dir>/SKILL.md
```
For example:
- SQL Conversion: `${SKILL_HOME}/subSkill/lhm-sql-conversion/SKILL.md`
- Data Validation: `${SKILL_HOME}/subSkill/lhm-data-validation-skill/SKILL.md`
- Workflow Migration: `${SKILL_HOME}/subSkill/lhm-bigdata-workflow-migration-skill/SKILL.md`

**Sub-agent dispatch rule**: when delegating a task to a sub-agent (Task/subagent mechanism of the current platform), the task description must contain **fully resolved absolute paths** — expand every `${SKILL_HOME}` before dispatching. A sub-agent runs in an independent context and cannot resolve this variable on its own.

## Intent Recognition and Routing Rules

### 1. SQL Conversion Skill (`lhm-sql-conversion`)

**Trigger keywords**:
- "convert SQL", "SQL conversion", "dialect conversion" (the Chinese equivalents are declared in the frontmatter description)
- "presto to spark", "hive to maxcompute", "clickhouse to hologres"
- SQL text provided together with source/target parameters
- A directory path containing .sql files

**Routing action**:
```
Invoke skill: lhm-sql-conversion
```

**Typical user inputs**:
- "Convert this presto SQL to spark format"
- "Batch-convert all hive SQL under /path/to/sqls to maxcompute"
- "Convert SELECT format_datetime(now(), 'yyyy-MM-dd') to spark"

---

### 2. Data Validation Skill (`lhm-data-validation-skill`)

**Trigger keywords**:
- "data validation", "data comparison", "consistency check"
- "run validation", "verify data", "check data"
- "count check", "metric check", "content check"
- Mentions of the `alibabacloud_lhm` SDK, ds_id, or batch_id

**Routing action**:
```
Invoke skill: lhm-data-validation-skill
```

**Typical user inputs**:
- "Run the count check between source MySQL and target MaxCompute"
- "View the result report of the last validation"
- "Rerun the failed validation tasks"
- "Diagnose why these two tables have inconsistent data"

---

### 3. Big-Data Workflow Migration Skill (`lhm-bigdata-workflow-migration-skill`)

This skill provides three core capabilities:

| Capability | Trigger | Action |
|------------|---------|--------|
| **Query skill capabilities** | User asks "what can this skill do / introduce its capabilities" | Output the content of `docs/introduction.md` |
| **Create data source** | Instructions such as "create a data source of type XX ..." | Route to `skill/lhm-sch-ds/SKILL.md` to complete data source creation |
| **Schedule migration** | A migration instruction (e.g., "migrate X to Y") | Config validation → environment initialization → data source validation → exploration & conversion → deployment & upload |

**Trigger keywords**:
- "workflow migration", "scheduled job migration", "DataWorks migration"
- "create a data source", "add a data source"
- "migrate <source data source> to <target data source>"
- Mentions of migrating DolphinScheduler / Airflow or other schedulers to DataWorks
- Mentions of `lhm-sch-ds`, `lhm-sch-env`, `lhm-sch-deploy`, or `lhm-sch-read-exec`

**Do not trigger** for SQL conversion, DDL migration, data validation, or other non-schedule-migration tasks.

**Routing action**:
```
Invoke skill: lhm-sch-workflowmigration
```

> This skill is registered by the `name` field in its frontmatter, `lhm-sch-workflowmigration`, which **differs from its package directory name** `lhm-bigdata-workflow-migration-skill`. Always invoke it by the frontmatter name; if invocation by name fails while the directory exists, load `<package-dir>/SKILL.md` by absolute path as the fallback.

This skill is a user-facing master playbook that automatically routes to its internal sub-skills based on user intent:
- Capability 1 (query) → directly output the introduction document
- Capability 2 (create data source) → delegate to `skill/lhm-sch-ds/SKILL.md`
- Capability 3 (schedule migration) → invoke the sub-skills sequentially in Steps 1-5

> ⚠️ **Mixed-intent requests**: a single user message can mention both data source creation and migration (e.g. "perform scheduled task migration ... and help me create a data source"). The dispatcher does **not** resolve this itself — it routes to the workflow-migration playbook, whose **Capability Selection Rule** decides which capabilities are actually actionable. A migration is actionable only when the message names at least one concrete data source; a generic migration mention with no data source name is background context, not a task and not a parameter-collection target. Do not pre-plan migration steps for a request that only carries a create-data-source instruction.

**Typical user inputs**:
- "Create a DolphinScheduler data source named test_ds"
- "Migrate test_TC_RE_1 to dw_test_fengling_0318 with config file path xxxx.json"
- "Migrate data source test_TC_RE_5a to the dw_test_fengling_0318 data source, converting DWSSQL to HOLOGRES_SQL, config file xxx.json"
- "-source test_TC_RE_5a -tag dw_test_fengling_0318 -exStr DWSSQL-to-HOLOGRES_SQL -dir xxx.json"

---

## Execution Flow

The dispatcher follows a linear, six-step execution flow. Each step must complete successfully before proceeding to the next.

### Global Language Rule (Mandatory)

**All output from this dispatcher and all sub-agents must match the language of the user's original input.** If the user's input is in English, all progress messages, status updates, error reports, and final results must be in English. If the user's input is in Chinese, respond in Chinese. Never mix languages or assume a default language based on the session environment. This rule applies to:
- Environment initialization status messages
- Session ID generation confirmations
- Config dispatch notifications
- Sub-skill loading confirmations
- Progress tracking outputs
- Error messages and warnings
- Final result summaries

When dispatching tasks to sub-agents, the task description must explicitly include this language requirement.

### Step 1: Intent Recognition

Analyze the user input and match it against the trigger keywords and scenarios defined in the "Intent Recognition and Routing Rules" section above. Determine which sub-skill should handle the request.

Classify by the **executable instructions** the message carries, not by every topic it mentions. When one message maps to several capabilities of the same sub-skill, route to that sub-skill once and let its own selection rule decide the scope; never widen the scope later in the run, and never collect parameters for a capability that was not triggered.

**Do NOT pre-plan the sub-skill's internal steps as todos at this stage.** In particular, for a mixed-intent message that carries only a create-data-source instruction plus a *generic* migration mention (no concrete data source name), you MUST NOT create any "migration flow" / "scheduled task migration" todo or plan item. The workflow-migration playbook's own Capability Selection Rule (its STEP 0 gate) decides the scope, and a generic migration mention is not actionable. Creating a migration todo here anchors the entire run on migration and is the root cause of the playbook failing to terminate after a successful data-source creation — it ends up asking for source/target names that were never part of an actionable task.

**If the intent is unclear**, ask the user to confirm:

```
It looks like you may need one of the following services:
1. SQL dialect conversion
2. Data consistency validation
3. Big-data workflow migration

Please confirm your requirement, or provide more details so I can route accurately.
```

Once the target sub-skill is identified, proceed to Step 2.

### Step 2: Environment Initialization

Prepare the runtime environment before executing any cloud service calls. This step includes two sub-steps that must both succeed.

#### 2.1 Aliyun CLI & LHM Plugin Initialization

Use the unified initialization script to ensure both the `aliyun` CLI and the `lhm` plugin are properly installed and meet version requirements. The `lhm` plugin is public, so the script installs it straight from the public plugin index (`aliyun plugin install --names lhm`) and automatically falls back to an offline package provisioned by the runtime environment when the index is unreachable, then validates the resulting version.

```bash
bash ${SKILL_HOME}/scripts/install_lhm_plugin.sh
INIT_STATUS=$?
echo "INIT_STATUS=${INIT_STATUS}"
if [ ${INIT_STATUS} -ne 0 ]; then
  echo "LHM_INIT_GATE=FAIL"
  echo "[FATAL] Environment initialization failed (exit code ${INIT_STATUS}). Terminating the skill run at Step 2.1; see the Hard Stop Gate below."
else
  echo "LHM_INIT_GATE=PASS"
fi
exit ${INIT_STATUS}
```

Capture the script's exit code and treat ANY non-zero value as a gate failure — see the **Hard Stop Gate** below.

> ⚠️ **Decide PASS/FAIL from the marker line, never from the tool's reported exit code.** The snippet above ends with `exit ${INIT_STATUS}`, so the reported code is faithful. If you wrap it for logging (e.g. `... > init.log 2>&1; echo "exit=$?" | tee -a init.log`), the trailing `echo`/`tee` becomes the last command and the reported exit code collapses to `0` even though the script failed. A masked failure code is the most common reason this gate gets skipped. Read `LHM_INIT_GATE=` / `INIT_STATUS=` from stdout and treat those as the only authoritative signal.

The script performs the following automatically:
1. Checks if `aliyun` CLI is installed; if not, prints installation instructions and exits
2. **Always** installs/updates the `lhm` plugin from the public plugin index — an already-installed plugin is *never* skipped, so every run picks up the latest published version instead of staying on a stale one
3. Falls back to an offline package provisioned **outside** the skill package if the public index is unreachable (lookup order below)
4. Validates the resulting installation against the minimum version (>= 0.1.1)
5. If **both** the online and the offline path fail but a locally installed version >= 0.1.1 already exists, keeps that version, prints a warning, and still exits `0` — a network-restricted yet functional environment must not be reported as broken

To force offline installation directly (skip online attempt):
```bash
bash ${SKILL_HOME}/scripts/install_lhm_plugin.sh --offline
```

> ⚠️ **Offline packages are NOT distributed inside the skill package** — the package carries no binaries. The runtime environment (image, install pipeline, or evaluation platform) must provision `aliyun-cli-lhm-<platform>.tar.gz` (>= 0.1.1) at one of the following locations, which the script searches in this order:
>
> | Priority | Location | Purpose |
> |----------|----------|---------|
> | 1 | `$LHM_PLUGIN_PACKAGE` | explicit full path to the package file |
> | 2 | `$LHM_PLUGIN_DIR/<platform-package>` | explicit directory |
> | 3 | `/eval/data/<platform-package>` | evaluation-environment provisioning directory — same convention as the `/eval/data/credentials.json` fallback in Step 4 |
> | 4 | `${SKILL_HOME}/vendor/<platform-package>` | deployment-provisioned directory |
>
> `<platform-package>` is resolved from `uname`: `aliyun-cli-lhm-darwin-amd64.tar.gz`, `-darwin-arm64.tar.gz`, `-linux-amd64.tar.gz`, or `-linux-arm64.tar.gz`. If the plugin is pre-installed in the image (`~/.aliyun/plugins/aliyun-cli-lhm/manifest.json` exists with version >= 0.1.1), provisioning a package is optional: the script still attempts an update, and when that update cannot reach any source it keeps the pre-installed version and exits `0`.
>
> When the public plugin index is unreachable, no package is provisioned, **and** no usable local version (>= 0.1.1) exists, the script exits non-zero and the run terminates at the Hard Stop Gate below. **This is the intended behaviour** — an environment without the plugin genuinely cannot serve any LHM request, so the skill reports the environment failure instead of pretending to work.

##### ⛔ Hard Stop Gate (Mandatory Interruption)

This initialization is a **blocking gate for the entire skill run**. The `lhm` plugin is the only network path to every LHM API, so without it no sub-skill can do anything except fail. `install_lhm_plugin.sh` signals every failure by exiting non-zero. If ANY of the following conditions holds, the whole skill MUST stop immediately:

1. **`aliyun` CLI is not installed** — neither `aliyun_real` nor `aliyun` is found on PATH
2. **The `lhm` plugin is not installed and cannot be installed** — the public plugin index fails, no offline package is provisioned in any of the four lookup locations, and no locally installed version >= 0.1.1 exists
3. **Installation or post-install validation fails** — the plugin manifest is missing after install, or the installed version is below `0.1.1`

**On a gate failure you MUST do exactly this, and nothing else:**

1. Report the script's error output to the user **verbatim** (in the user's language), including its printed installation instructions and the offline-package lookup locations it searched
2. State that the run terminated at Step 2.1, and list the steps that were therefore **not** executed
3. Stop — issue no further tool call of any kind

**What the gate forbids.** These are not hypothetical; every one of them has been observed in a real run that ignored the gate:

- Continuing to Step 2.2 or any later step (credential check, session ID, config dispatch)
- Reading or loading any sub-skill `SKILL.md`, playbook, template, or reference document
- **Asking the user for business parameters** — data source name/type, source/target dialect, SQL text, table names, config file path, sampling rate. A clarification question is *not* a harmless step: the user answers it, the flow then dies at the first cloud call, and the entire round trip is wasted. While the environment is broken, collect nothing and ask nothing
- Installing or running any sub-skill CLI (`uv tool install`, `pip install`, `lhm-sch-ds`, `lhm-sch-env`, `lhm-sch-deploy`, `lhm-sch-read-exec`, the data-validation scripts, `lookup_rules.py`). **A successful CLI install is never proof that the cloud path works** — every one of them shells out to `aliyun lhm` through its `aliyun_cli.py` layer and fails at the first call. Never tell the user that the flow "proceeds through the self-contained CLI"
- Any `aliyun` / `aliyun_real` `lhm ...` command, and any cloud resource create/modify/delete
- Reporting any count, status, comparison, or conversion result that would have come from a cloud call — never fabricate, estimate, or infer it
- **Self-recovery attempts**: no repeated online retries, no filesystem-wide search for an offline package, no hand-rolled `aliyun plugin install` variants, no SDK fallback, no "alternative install path". At most one immediate retry with `--offline`; if that also fails, the gate is confirmed — report and stop

Resume only after the environment is fixed and the script exits with status `0`.

> This gate binds the dispatcher and, transitively, every sub-skill: since all cloud calls flow through the `aliyun` CLI + `lhm` plugin, a failed initialization renders the entire skill inoperable and must halt it end-to-end. Halting before collecting parameters is deliberate — it tells the user the truth on the first turn instead of after a wasted round trip.

#### 2.2 Credential Check

Verify that Alibaba Cloud credentials are available through the default credential chain. Check in the following order:

1. **Environment variables**: `ALIBABA_CLOUD_ACCESS_KEY_ID` and `ALIBABA_CLOUD_ACCESS_KEY_SECRET`
2. **Credentials file**: `~/.alibabacloud/credentials` exists and contains valid profile
3. **ECS RAM Role**: running on an ECS instance with a bound RAM role (metadata service available)

```bash
echo "AK=${ALIBABA_CLOUD_ACCESS_KEY_ID:+SET}" && echo "SK=${ALIBABA_CLOUD_ACCESS_KEY_SECRET:+SET}"
test -f ~/.alibabacloud/credentials && echo "Credentials file: EXISTS" || echo "Credentials file: NOT FOUND"
```

**If no credentials are detected**, guide the user to configure them using ONE of the following methods (present in the user's language):

```
No Alibaba Cloud credentials detected. Please configure credentials using one of the following methods:

1. (Recommended for production) Bind a RAM Role to your ECS/ACK/FC instance — no manual configuration needed
2. Set environment variables:
     export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-ak>
     export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-sk>
3. Run `aliyun configure` to interactively set up credentials
4. Create ~/.alibabacloud/credentials manually

⚠️ Never put credentials in config files or pass them as command-line arguments.
See: https://help.aliyun.com/document_detail/378657.html
```

**Do not proceed until credentials are confirmed available.** The sub-skills rely on the default credential chain and will fail with authentication errors if credentials are missing.

> **Note**: This check only verifies credential *availability*; it does not validate credential *correctness*. Invalid credentials will be caught by the sub-skill's API calls with clear error messages.

### Step 3: Session ID Generation (Mandatory — never skip, never defer)

Generate a session-scoped identifier for observability. This is a **required step of the linear execution flow**: before loading any sub-skill in Step 5 you MUST actually run the command below and export `LHM_SESSION_ID` into the environment. Do not skip it, do not fold it silently into another step, and do not rely on the sub-skills to generate it for you — the full-chain User-Agent audit described in the "Observability" section only works when the dispatcher sets this value first. **Generate it only once per session** and reuse it for all cloud service calls:

```bash
export LHM_SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4().hex)")
echo "Session ID: $LHM_SESSION_ID"
```

This ID is used in the UA header (`AlibabaCloud-Agent-Skills/alibabacloud-lakehouse-migration/{version}/{session-id}`) for all subsequent cloud service calls (see "Observability" section). Sub-skill scripts read `LHM_SESSION_ID` from the environment; their built-in per-process random fallback is a last-resort safety net for standalone sub-skill use only — it is **not** a substitute for the dispatcher exporting `LHM_SESSION_ID` here, and depending on it breaks full-chain traceability. A Step 3 without an actual `export LHM_SESSION_ID=...` is incomplete: proceed to Step 5 only after it has run.

### Step 4: Config Dispatch

Prepare the configuration file expected by the target sub-skill.

**Dependency declaration**: the config dispatch script depends on `pyyaml`. Install it before first use:

```bash
pip install -r ${SKILL_HOME}/scripts/requirements.txt
```

**Config file resolution order (with evaluation-environment fallback)**:

The canonical config location is the user home directory `~/.lhm/credentials.json`. However, in the dynamic evaluation (sandbox) environment the config file may not be provisionable into the user home directory, so a fallback location `/eval/data/credentials.json` is also supported. Resolve the config in the following order:

1. `~/.lhm/credentials.json` — the standard user-directory location (highest priority)
2. `/eval/data/credentials.json` — the evaluation-environment config directory (fallback)

If the file is NOT found in the user home directory but IS found in the evaluation config directory, copy it once to the standard user-directory location, so that every sub-skill (which reads `~/.lhm/credentials.json`) picks it up automatically:

```bash
USER_CFG="$HOME/.lhm/credentials.json"
EVAL_CFG="/eval/data/credentials.json"

if [ -f "$USER_CFG" ]; then
  echo "Config found in user directory: $USER_CFG"
elif [ -f "$EVAL_CFG" ]; then
  mkdir -p "$HOME/.lhm"
  cp "$EVAL_CFG" "$USER_CFG"
  echo "Config not found in user directory; copied from evaluation config: $EVAL_CFG -> $USER_CFG"
else
  echo "No config file found in either the user directory ($USER_CFG) or the evaluation directory ($EVAL_CFG)"
fi
```

> ⚠️ Copy only when the user-directory file is absent — never overwrite an existing `~/.lhm/credentials.json`. Do not print the file contents (it may contain plaintext secrets).

**Configuration Management**:

All LHM skills read their **business configuration** from `~/.lhm/credentials.json`. This unified configuration file contains:
- LHM service configuration (`lhm.endpoint`, `lhm.region_id`) — these two values are attached to **every** `aliyun lhm` call as the fixed parameters `--endpoint` / `--region`
- SQL conversion database connection settings (maxcompute, hologres, clickhouse, etc.)
- Schedule migration data source names

> **Alibaba Cloud API credentials are NOT stored in or read from this file.** Authentication for every `aliyun lhm` call is resolved through the default credential chain verified in Step 2.2 (environment variables / `~/.alibabacloud/credentials` / RAM Role). The per-database login fields inside the SQL-conversion profiles belong to the DryRun database connection only and are never used to authenticate LHM API calls. Therefore the schedule-migration and data-validation flows must **never** look for cloud credentials in this file, **never** treat their absence as a blocker, and **never** prompt the user for cloud credentials — if the default credential chain is unavailable, Step 2.2 already handles it before any sub-skill is loaded.

Each sub-skill reads the relevant sections from this file automatically. No manual configuration dispatch is needed.

⚠️ **Security constraints**:
- Never fill any credential or secret field programmatically
- Never overwrite fields that already have values
- Never echo plaintext secrets in any output

**If the config file does not exist in either location**, each sub-skill falls back to the environment variables (`LHM_ENDPOINT` / `REGION_ID`) or built-in defaults for the `--endpoint` / `--region` fixed parameters (fully backward compatible); cloud credentials always come from the default credential chain regardless.

### Step 5: Load and Execute Sub-Skill

Based on the routing decision from Step 1, **read the sub-skill's SKILL.md file directly** and follow its instructions to execute the task.

**⚠️ Critical**: Do NOT attempt to invoke the sub-skill by name or through any skill invocation mechanism. The sub-skill is NOT a registered invokable skill — it is a document that you must read and execute yourself. Always use file reading (e.g., `read_file`) to load the sub-skill's SKILL.md at the absolute path:

```
${SKILL_HOME}/subSkill/<sub-skill-dir>/SKILL.md
```

For example:
- SQL Conversion: `${SKILL_HOME}/subSkill/lhm-sql-conversion/SKILL.md`
- Data Validation: `${SKILL_HOME}/subSkill/lhm-data-validation-skill/SKILL.md`
- Workflow Migration: `${SKILL_HOME}/subSkill/lhm-bigdata-workflow-migration-skill/SKILL.md`

**Loading constraints**:
- **File-read only**: always load by absolute file path. Never attempt invocation by skill name.
- If the file does not exist, inform the user that the sub-skill package files are missing and need to be deployed.
- Second-level sub-skills inside a package are also loaded only by absolute file path from within their parent skill's flow.
- When delegating to a sub-agent, resolve all `${SKILL_HOME}`-prefixed paths to absolute paths first.

Execute according to the flow defined in the sub-skill's SKILL.md, including pre-checks, core business logic, result output, and audit records.

> **Interaction with the Step 2.1 Hard Stop Gate**: this step is reached **only after** the gate has passed. If `install_lhm_plugin.sh` exited non-zero, the run already terminated at Step 2.1 — do not load any sub-skill document, do not ask the user for parameters, and do not install or run any sub-skill CLI.

### Step 6: Return Results

Present the sub-skill's execution results in a user-friendly way. Avoid exposing internal technical details unless the user explicitly requests debugging information. Pass error messages from sub-skills through as-is; do not rewrap them.

**A finished sub-skill run finishes the dispatcher run.** Once the routed sub-skill reaches its own terminal state (for example, a data source has been created), report that result and stop. Do not append a follow-up question, a "next step" suggestion, a fillable template, or a list of unexecuted work belonging to a capability that Step 1 did not classify as actionable — that reopens a scope which was deliberately frozen and forces the user into a pointless round trip.

---

## Notes

1. **Do not implement business logic yourself**: this dispatcher only handles routing; all business logic is implemented by the sub-skills
2. **Keep sub-skills independent**: each sub-skill can be used standalone; the dispatcher is merely a convenience entry point
3. **Error pass-through**: pass error messages returned by sub-skills through to the user as-is; do not rewrap them
4. **Audit records**: each sub-skill saves its own audit records; the dispatcher does not duplicate them
5. **Dependency installation**: before running any config dispatch, ensure the dependencies declared in `scripts/requirements.txt` are installed
6. **Environment gate is absolute**: a non-zero exit from `scripts/install_lhm_plugin.sh` terminates the whole run at Step 2.1 — no later step, no sub-skill document loading, no clarification question, no CLI installation, no cloud call, and no self-recovery attempt. Report the script's error verbatim and stop.
7. **Language preference (mandatory for all agents)**: if the user does not explicitly specify a language requirement, respond in English or match the language of the user's input. **This rule applies to the main agent, all sub-agents, and any parallel task executions.** When dispatching tasks to sub-agents (via Task/subagent mechanism), the task description must explicitly include this language requirement to ensure consistent behavior across all execution contexts.

## Observability

This skill orchestrates calls to Alibaba Cloud LHM services. All cloud service calls must carry a unified UA identifier so the server side can track them.

### session-id rules

- At the start of each session, generate a 32-character hexadecimal random ID as the `session-id`. **Generate it only once per session**, and reuse it for all cloud service calls within the session:

```bash
python3 -c "import uuid; print(uuid.uuid4().hex)"
```

- Immediately after generation, export it as an environment variable so that every sub-skill subprocess (CLI wrappers and SDK clients) reuses the same ID:

```bash
export LHM_SESSION_ID=<generated-32-char-hex>
```

The dispatcher MUST have exported `LHM_SESSION_ID` in Step 3 before any sub-skill runs; the sub-skill scripts then read it from the environment when constructing their UA. The per-process random fallback inside those scripts only fires when the variable is genuinely unset (e.g., a sub-skill invoked standalone, outside the dispatcher) so the UA is never missing — it is **not** a license for the dispatcher to skip Step 3, and skipping it breaks the full-chain audit.

### skill-version rules (read from references/manifest.json)

The UA is **version-derived**: it must embed the skill version, which is read from the top-level `version` field of [`references/manifest.json`](references/manifest.json) — a non-empty string. This file MUST be read **before the first cloud call** so every `aliyun lhm` / SDK request carries the correct version segment.

```bash
SKILL_VERSION=$(python3 -c "import json,os; print(json.load(open(os.path.join('${SKILL_HOME}','references','manifest.json')))['version'])")
echo "Skill version: $SKILL_VERSION"
```

- The `version` in `references/manifest.json` is the authoritative source for the UA version segment and is kept in sync with the frontmatter `version`.
- Read it once per session and reuse the value for all cloud service calls.

### UA template declaration

When calling cloud services via the aliyun CLI / SDK, attach the following UA identifier (placeholder form):

```
--user-agent AlibabaCloud-Agent-Skills/{SKILL_NAME}/{version}/{session-id}
```

- `{SKILL_NAME}`: replace with the `name` field of this skill's frontmatter, i.e. `alibabacloud-lakehouse-migration`
- `{version}`: replace with the `version` field read from `references/manifest.json` (see the rule above), i.e. `1.0.0`
- `{session-id}`: replace with the 32-character hexadecimal ID generated by the rule above

Example:

```bash
aliyun lhm <command> --endpoint <lhm.endpoint> --region <lhm.region_id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-lakehouse-migration/1.0.0/0af1c3e6b2d94a7f8c1e2b3d4a5f6071
```

> Besides the UA, every `aliyun lhm` call also carries the fixed connection parameters `--endpoint` / `--region`, whose values are read from the `lhm` section of `~/.lhm/credentials.json` (`lhm.endpoint` / `lhm.region_id`, see Step 4); the environment variables `LHM_ENDPOINT` / `REGION_ID` and built-in defaults are only fallbacks, and explicit CLI arguments take the highest precedence. The sub-skill CLI wrappers attach them automatically.

> ⚠️ **Sandbox Environment Compatibility**: In the evaluation system's sandbox environment, the `aliyun` CLI may be wrapped as a proxy, and actual calls require using `aliyun_real`. Before executing any `aliyun` command, check whether `aliyun_real` exists:
> ```bash
> if command -v aliyun_real >/dev/null 2>&1; then
>   ALIYUN_CMD="aliyun_real"
> else
>   ALIYUN_CMD="aliyun"
> fi
> # Use ${ALIYUN_CMD} instead of aliyun below
> ${ALIYUN_CMD} lhm <command> ...
> ```
> The `aliyun_cli.py` Python module already includes this detection logic (via the `find_aliyun_binary()` function), but manual handling is required when invoking directly through Bash.

When calling cloud services through an Alibaba Cloud SDK, set the same UA identifier via the `user_agent` field of the SDK `Config` object (e.g., `alibabacloud_tea_openapi.models.Config(user_agent=...)`), using the same `AlibabaCloud-Agent-Skills/{SKILL_NAME}/{version}/{session-id}` form with each sub-skill's own `{SKILL_NAME}` and the `{version}` read from `references/manifest.json`. All sub-skill SDK clients and CLI wrappers in this repository already attach the session-id automatically based on `LHM_SESSION_ID`.

Each sub-skill that the request is routed to reuses the same `session-id` when making its own cloud service calls, ensuring full-chain traceability.

## Permissions

This skill is classified in the AIOps domain because it orchestrates Alibaba Cloud service calls. The RAM permission declarations required by the routed sub-skills are in [references/ram-policies.md](references/ram-policies.md). Credentials must be resolved through the default credential chain, as described in that document.

## Skill Package Layout

This dispatcher and the three sub-skills are **independent Skill packages**. In this monorepo, the dispatcher resides at the repository root (`SKILL_HOME`), while all sub-skill packages are organized under the `subSkill/` subdirectory:

```
<repo-root>/                                      # = ${SKILL_HOME} of this dispatcher
├── SKILL.md                                      # This dispatcher (unified entry point)
├── references/manifest.json                      # Skill manifest (authoritative `version` for the UA)
├── references/ram-policies.md                    # RAM permission declarations
├── scripts/                                      # Utility scripts, dependency declaration
│   ├── install_lhm_plugin.sh
│   └── requirements.txt
└── subSkill/                                     # Sub-skill packages directory
    ├── lhm-sql-conversion/                       # SQL conversion skill (registered name: lhm-sql-conversion)
    │   └── skills/sql-atomic-conversion/         # Nested — NOT discoverable by name; load via file path
    ├── lhm-data-validation-skill/                # Data validation skill (registered name: lhm-data-validation-skill)
    │   └── atomic-skills/lhm-*/                  # Nested — NOT discoverable by name; load via file path
    └── lhm-bigdata-workflow-migration-skill/     # Workflow migration skill (registered name: lhm-sch-workflowmigration)
        └── skill/lhm-sch-{ds,env,deploy,read-exec}/  # Nested — NOT discoverable by name; load via file path
```

Routing prerequisite: the three sub-skills must be accessible to the Agent via `${SKILL_HOME}/subSkill/<sub-skill-dir>/SKILL.md` path. Read this file directly and follow its instructions. Never attempt invocation by skill name. Never implement sub-skill business logic yourself.

## When to use

- The user raises a lakehouse migration requirement but is unsure which skill to use
- The user needs cross-skill collaboration (e.g., convert SQL first, then validate data)
- As a unified entry point to simplify user interaction

## When NOT to use

- The user has explicitly specified a concrete skill to use (jump directly to that sub-skill)
- General questions unrelated to lakehouse migration
