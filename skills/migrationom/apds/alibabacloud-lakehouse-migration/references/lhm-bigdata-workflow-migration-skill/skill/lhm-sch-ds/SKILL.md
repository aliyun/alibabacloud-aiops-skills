---
name: lhm-sch-ds
description: |
  Agent Playbook for LHM schedule data source management.
  Guides the user through data source creation, validation, OSS file upload, and connectivity testing.

  Triggers: create a data source, add a data source, validate a data source name, upload a metadata
  file, test connectivity, or any request related to LHM schedule data source management.

  Do not trigger for: schedule migration tasks, SQL conversion, DDL translation, or other
  non-data-source-management tasks.
---

# LHM Schedule Data Source CLI & Agent Playbook

This Skill is **Agent-driven**. The `lhm-sch-ds` CLI exposes **stateless single-step commands**: each command makes **exactly one** API call, prints structured JSON status, and exits. There are **no loops inside** — the **Agent** is responsible for orchestrating step order, asking the user for decisions, and performing the OSS file upload (via curl). State (parsed configuration, data source name, new ID) is passed explicitly via command-line arguments; the CLI itself persists nothing.

## Scope and Termination (Mandatory)

This skill covers **data source management only** — querying existing data sources, name validation, metadata upload, creation, and connectivity testing. It never plans, executes, or collects parameters for the schedule migration chain (exploration / conversion / deployment).

- **Terminal states**: `create` succeeded; or the user-requested `test-conn` finished; or an existing data source was selected in Step 4. At a terminal state, report the result and **stop**.
- **Never solicit migration parameters.** Do not ask for a source/target data source name, a SQL dialect conversion expression, or a migration config file path — not as a question, not as a "to continue with the migration ..." trailer on the final message, not as a suggested next step, and not as a fillable template.
- **Never report migration work as pending.** Lines such as "exploration / conversion / deployment not executed" are outside this skill's scope and must not appear in its output.
- **Resumption is the caller's decision, not this skill's.** When reached from the schedule-migration entry playbook, only that playbook decides whether a migration flow resumes — and it does so solely under the narrow exception in its Capability Selection Rule (migration already running, names already extracted, "data source does not exist" reported). A generic mention of migration in the original user request is not a reason to resume one.
- **Session stage**: a data-source-only run prepares its session with `setup_session.sh --stage ds`, which does **not** require the migration source/target data source names. Their absence is expected — never treat it as a blocker, and never turn it into a question for the user.
- **One question, one concern.** A clarification question asked by this skill may only concern data source parameters.

## CLI Usage

### Environment Prerequisites

**The environment and credentials have already been prepared by [lhm-sch-env](../lhm-sch-env/SKILL.md) at session start; this skill performs no environment validation whatsoever.**
Simply run the business commands — do not run validation scripts, do not run `validate`, and do not re-confirm credentials or prompt the user about configuration.

> ⛔ **The one exception — the `aliyun-cli-lhm` plugin (hard stop)**: every command below reaches the service through `aliyun lhm <command>`, so the plugin (>= 0.1.1, i.e. `~/.aliyun/plugins/aliyun-cli-lhm/manifest.json` exists) must be present. If it is not, **stop before Step 0**: report the environment error verbatim and terminate.
>
> In particular, do **not** ask the user for `dsName`, `dsType`, or any other business parameter. The clarification rules further below are mandatory **only once the plugin is confirmed available** — while it is missing, every `check` / `check-name` / `create` / `test-conn` call is guaranteed to fail, so an answer collected now can never be used. Do **not** run `uv tool install` or `lhm-sch-ds` either: this CLI shells out to `aliyun lhm`, so a successful install is never proof that the flow can proceed.

Only when a command actually reports an environment-class error (e.g., credentials not found, command not found) should it be handed to [lhm-sch-env](../lhm-sch-env/SKILL.md); when relaying its guidance, **never write secrets on behalf of the user, and never echo secret values**.

### Command Invocation

All commands are executed via `lhm-sch-ds <command>`.

### Status Code & Exit Code Contract

Each single-step command outputs a JSON object with a `status` field to **stdout** and exits with an exit code; the Agent branches on them:

| `status` | Exit code | Meaning | Agent action |
|----------|-----------|---------|--------------|
| `ok` | `0` | Operation succeeded | Use the payload and proceed to the next step |
| `empty` | `0` | `check` — no same-name data source found | Continue with `check-name` → `create` |
| `match` | `0` | `check` — one or more existing data sources found | Show `matches` to the user and ask which one to use |
| `available` | `0` | `check-name` — the name is available | Continue with upload/create |
| `exists` | `2` | `check-name` — the name is taken or invalid | Have the user provide a new name and rerun `check-name` |
| `failed` | `2` | Unrecoverable business/API error | Report `err_message` and abort |
| *(config error)* | `1` | Missing credentials / invalid config file | Fix the environment and retry |

### Commands

#### Single-Step Data Source Commands

```bash
# 1. Query whether a same-name data source already exists (ListMetaDataComponentPage)
#    --ds-type may be omitted: when omitted, dsType is sent as an empty string "" (no type filtering)
lhm-sch-ds check --ds-name <DS_NAME> [--ds-type <DS_TYPE>] [--category-type WORKFLOW]

# 2. Validate name uniqueness before creation (ExecMetaDataComponentName)
lhm-sch-ds check-name --ds-name <DS_NAME>

# 3. Upload a local metadata file to OSS — only when source-file-path has a value (GetMetaOssTempKey + multipart upload)
lhm-sch-ds upload --file <LOCAL_FILE_PATH>

# 4. Create the data source from the filled-in config JSON file (AddMetaDataComponent)
lhm-sch-ds create --config-file <PATH_TO_FILLED_TEMPLATE.json>

# 5. Test connectivity (ExecWorkflowConnectivity)
lhm-sch-ds test-conn --config-file <PATH_TO_FILLED_TEMPLATE.json> [--ds-id <DS_ID>]
```

**Common options** (all commands): `--endpoint URL` / `--region ID` — attached to every `aliyun lhm` call as fixed parameters; they override the values read from the config file's `lhm` section (`lhm.endpoint` / `lhm.region_id`), which in turn fall back to the `LHM_ENDPOINT` / `REGION_ID` environment variables and then built-in defaults.

**Config file format**: `--config-file` is a filled-in data source template (see `datasourceTemplate`). The CLI reads `dsName`, `categoryType`, `dsType`, `dsConfig`, and `dsStatus`; `_comment` blocks are ignored. `dsConfig` is serialized to a JSON string internally before the API call.

> **File upload is handled by the `upload` command.** It obtains STS credentials internally, generates a unique OSS object name (`{YYYYMMDDHHmmss}_{basename}`), and uploads the file via multipart/form-data. **The local file is never renamed, moved, or modified** — only the OSS object key uses the generated unique name. On success it returns `oss_filename`; the Agent writes that value back into `dsConfig.source-file-path` before calling `create`.
>
> If you need the raw credentials for a manual/curl upload, use the low-level command `lhm-sch-ds oss-key` (see Appendix Step 6 / [API.md — OSS file upload example (curl)](API.md#oss-file-upload-example-curl)).

### Agent Orchestration Flow

The Agent drives the complete data source workflow by chaining single-step commands. Asking the user, uploading files, and rewriting the configuration are all the Agent's responsibilities:

```
0. Extract the data source name, type, and all configuration parameters (dsVersion, endpoint, token, project, etc.) from the user's request;
   if the data source name (dsName) or type (dsType) is missing/ambiguous → first apply the "Clarification rules for required data source creation info"
   (follow up via AskUserQuestion; dsType must be chosen from the enumeration list), then continue after clarification;
   load the matching template based on dsType (see Step 2), auto-fill the parameters, and save as a local JSON config file (see Agent orchestration rules - automatic config file generation);
   if the user provided a source file (local metadata file path), handle it per the source file handling rules.

1. check --ds-name DS_NAME [--ds-type DS_TYPE] (omit --ds-type when no type is specified; dsType is sent as an empty string)
     status=empty (exit 0) → no existing data source, go to 2
     status=match (exit 0) → show `matches`; if the user picks one →
         go to 5 test-conn ONLY if the user explicitly requested it, otherwise END
                             if the user wants to create a new one → go to 2
     status=failed          → abort

2. check-name --ds-name DS_NAME
     status=available (exit 0) → go to 3
     status=exists (exit 2)    → have the user change the name and rerun check-name (loop)
     status=failed             → abort

3. If dsConfig.source-file-path has a value (non-empty):
     a. upload --file <LOCAL_FILE_PATH>   (use the original local path)
            status=ok (exit 0)     → obtain `oss_filename`
            status=failed (exit 2) → report err_message, abort
        (the command obtains STS, generates the unique name, and uploads internally;
         the local file is never renamed/moved/modified)
     b. Rewrite dsConfig.source-file-path in the config file to `oss_filename`
   If source-file-path is empty/absent → skip the upload.

4. create --config-file <PATH>
     status=ok (exit 0)     → obtain ds_id, report "✓ Data source created successfully";
                              if the user explicitly requested a connectivity test → go to 5,
                              otherwise END (creation is the terminal step of this capability —
                              do NOT proactively ask about connectivity)
     status=failed (exit 2) → report err_message, abort

5. test-conn --config-file <PATH> [--ds-id <ds_id>]   (run ONLY when the user explicitly requested it; never ask proactively)
     - If source-file-path originally had a value → skip the connectivity test, END
     status=ok (exit 0)     → "✓ Data source connectivity check passed", END
     status=failed (exit 2) → "✗ Connectivity check failed: {err_message}", END
```

**Agent orchestration rules:**
- **Clarification rules for required data source creation info**:
  - When the user clearly wants to **create a new data source** but has not provided the **data source name (dsName)** or **data source type (dsType)**, the Agent must first clarify with the user via `AskUserQuestion` in Step 0 — **skipping, inventing, or default-filling is forbidden**, and no CLI command may be executed before clarification completes.
  - **Name clarification**: when the name is missing, ask the user directly "Please provide the name of the data source to create" (free-text input).
  - **Type clarification**: when the type is missing, ask the user "Please select the type of the data source to create"; the options **must only** be the following enumeration list (presented as choices):
    `["DolphinScheduler", "DataArtsStudio", "DataWorks", "Azkaban", "Wedata", "EmrWorkflow", "Adf", "Airflow"]`
  - **Type normalization**: if the type provided by the user is an alias, abbreviation, or has inconsistent casing (e.g., `dolphin`, `海豚调度`, `airflow`), the Agent should map it to the canonical value in the enumeration above; if no unique mapping can be determined (e.g., the input is outside the enumeration), the enumeration options must be listed for the user to choose again — guessing is forbidden.
  - When both name and type are missing, they may be asked together in a single `AskUserQuestion` to reduce round trips.
- **Automatic config file generation rules**:
  - When the user mentions creating a data source, the Agent extracts the data source type (dsType) and all configuration parameters (dsName, dsVersion, endpoint, token, project, etc.) from the user's natural-language input in Step 0, loads the corresponding data source template based on dsType (see the template structure reference in Step 1), automatically fills the parameters into the template, and saves it as a local JSON config file. All subsequent CLI commands (`check`, `check-name`, `create`, `test-conn`) use this config file.
  - If the user provided a source file (local metadata file path), the Agent writes that path into the template's `dsConfig.source-file-path` field in Step 0, then handles it via the upload flow in Step 3.
  - If the user mentions "use the previous file", the Agent should look in the earlier session history for a saved data source config file path and reuse that file (including its already-filled fields such as source-file-path), passing it directly as the `--config-file` argument to subsequent CLI commands without regenerating a config file.
- Use `AskUserQuestion` for every user decision: which existing data source to choose, whether to create a new one, and changing the name on a conflict. The connectivity test is **not** a decision to ask about — it runs only when the user explicitly requested it, so never proactively ask "Do you want to test connectivity?".
- Never guess parameters — all names, IDs, and file paths come from API responses, user input, or the parsed config file.
- Track state explicitly between command invocations (`DS_NAME`, parsed configuration, `ds_id`, whether `source-file-path` has a value); the CLI is stateless.
- **Parameter validation rules**: when extracting data source parameter fields from natural language, the corresponding type's template must be loaded first, the descriptions and validation requirements of each field in `_comment` (format, allowed values, URL conventions, etc.) must be read, and each extracted field value must be validated. If validation fails, immediately point out the specific field's problem and the correct format requirements to the user, and continue only after the user corrects it — parameters that fail validation must never be passed to subsequent CLI commands.
- **Data source name change restrictions**: the Agent is strictly forbidden from changing the data source name (`dsName`) provided by the user on its own initiative. Name changes are only allowed in the following two cases:
  1. The user proactively enters a new name;
  2. When `check-name` returns `exists` (the name is taken or invalid), the Agent must explicitly ask the user and provide modification suggestions; **only after the user explicitly confirms or enters a new name** may `dsName` be updated and the flow continue.
  Any name change without user authorization is a violation; the flow must be aborted immediately and the reason explained to the user.

### User-Facing Output Rules (must be followed)

The CLI's JSON/status output is the **Agent-internal protocol**. What the user sees must be concise natural-language narration — the underlying mechanics must never be exposed.

**Always hide from the user:**
- The raw command lines being executed (e.g., `lhm-sch-ds check --ds-name ...`)
- Raw JSON output / `status` field values (`ok`, `empty`, `match`, `available`, `exists`, `failed`)
- Technical codes: `err_code`, `request_id`, exit codes
- **Data source ID (`ds_id`)**: after a successful creation, only report "✓ Data source created successfully"; never expose internal IDs in user-visible output
- OSS credentials: `ak`, `signature`, `security_token`, `policy` — these must never be printed

**What to show the user** — only the meaning of the current progress:
- Querying existing data sources → `正在查询数据源...` ("Querying data sources...")
- Existing data sources found → list names/types in natural language and ask which one to use
- Name validation → `正在校验数据源名称...` ("Validating the data source name..."); on `exists` → `数据源名称已存在或不合法，请修改后重试` ("The data source name already exists or is invalid; please modify and retry")
- Uploading file → `正在上传元数据文件...` ("Uploading the metadata file...")
- Creating data source → `正在创建数据源...` ("Creating the data source..."); on success → `✓ 数据源创建成功` ("✓ Data source created successfully")
- Connectivity test → `正在检测连通性...` ("Testing connectivity..."); result → `✓ 连通性校验成功` / `✗ 连通性校验失败：...` ("✓ Connectivity check passed" / "✗ Connectivity check failed: ...")

**Mapping reference (for Agent-internal use; do not print):**

| Internal signal | What the user should see |
|-----------------|--------------------------|
| `check` → `empty` | (continue the creation flow, no notice needed) |
| `check` → `match` | (list existing data source names/types and ask whether to use one) |
| `check-name` → `available` | (continue, no notice needed) |
| `check-name` → `exists` | The name already exists or is invalid; modify and retry |
| `upload` → `ok` | Uploading metadata file... / upload succeeded |
| `create` → `ok` | ✓ Data source created successfully |
| `test-conn` → `ok` / `failed` | ✓ Connectivity passed / ✗ Connectivity failed: ... |

> Failure is the only exception: when `status="failed"` is received, translate the reason into actionable guidance (e.g., "the data source configuration is incorrect"), but still **do not** expose raw `err_code` / `request_id` to the user — keep them in internal logs only.

### Credential Configuration

The CLI automatically loads the session config transcribed by lhm-sch-env (a per-session dedicated directory `/tmp/lhm-sch-session-<uid>/s-<timestamp>-<random>/session.json`, located via the pointer file `current`); this skill does not need to care.

---

# Appendix: Low-Level Business Logic & API Reference

The following sections document the low-level step-by-step business logic and the five data source APIs. The CLI single-step commands (see "CLI Usage" above) wrap these APIs — this appendix is for understanding what each command does internally and for using the SDK directly when debugging. **The orchestration logic is defined in "Agent Orchestration Flow" above; do not reimplement it as a synchronous script.**

## API Reference

See [API.md](API.md) for all API specification documents. Core APIs and their corresponding CLI commands:

| API | CLI command | Purpose |
|-----|-------------|---------|
| `ListMetaDataComponentPage` | `check` | Query whether a same-name data source exists |
| `ExecMetaDataComponentName` | `check-name` | Validate data source name uniqueness |
| `GetMetaOssTempKey` | `upload` (and `oss-key`) | `upload` obtains credentials + uploads the file; `oss-key` only returns the raw credentials |
| `AddMetaDataComponent` | `create` | Create a new data source |
| `ExecWorkflowConnectivity` | `test-conn` | Test data source connectivity |

---

## Business Logic Workflow (Detailed)

The data source management workflow contains 9 sequential steps. Each step corresponds to one or more CLI commands above; this section details the entry conditions, wrapped API calls, error handling, and exit criteria.

### Step 1: Extract the Data Source Name and Type from Natural Language

**Goal**: identify the name and type of the data source to add from the user's input.

- Parse the user's natural-language request to extract the target data source name (`dsName`) and type (`dsType`).
- If the name is missing or ambiguous, use `AskUserQuestion` to confirm before continuing.
- If the type is missing, ambiguous, or outside the enumeration, use `AskUserQuestion` to have the user choose from the following enumeration:
  `["DolphinScheduler", "DataArtsStudio", "DataWorks", "Azkaban", "Wedata", "EmrWorkflow", "Adf", "Airflow"]`
- See "Agent orchestration rules - Clarification rules for required data source creation info" above for detailed clarification behavior.
- **Output**: validated `DS_NAME` and `DS_TYPE`

---

### Step 2: Load the Matching Data Source Template

**Goal**: find and output the matching template document based on the data source type.

- **⚠️ Searching for template files with tools such as find, grep, or glob is strictly forbidden.** The template documents live in the `datasourceTemplate` subdirectory alongside this SKILL.md; use the List Directory tool directly to list all `.md` files in that directory.
- **File naming convention**: template documents follow the `{dsType}-datasource-template.md` format (e.g., `airflow-datasource-template.md`, `dolphinScheduler-datasource-template.md`). The Agent should find the `.md` document whose filename contains the keyword corresponding to the `dsType` field provided by the user.
- **Output the matched template document content verbatim** to the user, without modification
- If no matching template document is found, prompt the user to check whether the data source type is correct, or to provide the configuration parameters manually

---

### Step 3: User Fills in the Template and Provides the File Path

**Goal**: the user fills in the template fields, saves it as a file, and provides the file path.

- After receiving the template, the user fills in the required fields (`dsName`, `categoryType`, `dsType`, `dsConfig`, etc.)
- The user saves the filled-in template to a local file
- The user provides the file path to the Agent
- **Action**: load and parse the JSON file from the provided path
- **Output**: the parsed configuration object containing `dsName`, `categoryType`, `dsType`, and `dsConfig`

---

### Step 4: Query Existing Data Sources by Name

**Goal**: verify whether a same-name data source already exists.

> **CLI command**: `lhm-sch-ds check --ds-name <DS_NAME> [--ds-type <DS_TYPE>] [--category-type WORKFLOW]`. When `--ds-type` is omitted, dsType is sent as an empty string `""` (no type filtering). Mapping: `empty` → no match (→ Step 5), `match` → with `matches` (ask the user), `failed` → abort. The raw API call below is for SDK-level debugging only.

**API call**:
```python
request = lhm_models.ListMetaDataComponentPageRequest(
    category_type=parsed_config['categoryType'],
    ds_name=parsed_config['dsName'],
    ds_type=parsed_config['dsType']
)
response = client.list_meta_data_component_page(request)
body = response.body
```

**Response handling**:

| Condition | Action | Next step |
|-----------|--------|-----------|
| `body.success == true` and `body.data` is empty | No existing data source found | → Step 5 |
| `body.success == true` and `len(body.data) == 1` | One matching data source found | Ask the user: "Do you want to use this data source?" |
| `body.success == true` and `len(body.data) > 1` | Multiple matching data sources found | Have the user specify which one to use |
| `body.success == false` | API error | Report the error and **abort** |

**Single-match flow**:
- Show the data source type and name
- Ask the user: "Do you want to use this data source?"
  - If **yes**: return the data source name and **end the workflow** — run a connectivity test (→ Step 9) only if the user explicitly requested one; do **not** ask proactively
  - If **no**: → Step 5 (create a new data source)

**Multi-match flow**:
- List the names and types of all matching data sources
- Ask the user: "Is the data source you need in the list?"
  - If **yes**: have the user specify the exact name, then return the data source name and **end the workflow** — run a connectivity test (→ Step 9) only if the user explicitly requested one; do **not** ask proactively
  - If **no**: → Step 5 (create a new data source)

---

### Step 5: Validate Data Source Name Uniqueness

**Goal**: ensure the data source name is unique before creation.

> **CLI command**: `lhm-sch-ds check-name --ds-name <DS_NAME>`. Mapping: `available` → the name is available (→ Step 6), `exists` → taken/invalid (have the user change the name and retry), `failed` → abort. The raw API call below is for SDK-level debugging only.

**API call**:
```python
request = lhm_models.ExecMetaDataComponentNameRequest(ds_name=parsed_config['dsName'])
response = client.exec_meta_data_component_name(request)
body = response.body
```

**Response handling**:

| `body.data` | Meaning | Action |
|-------------|---------|--------|
| `true` | The name already exists or is invalid | Have the user change the name, ↺ retry Step 5 |
| `false` | The name is available | → Step 6 |

**Loop until valid**:
- If `body.data == true`, tell the user: "The data source name already exists or is invalid; please modify and retry"
- Wait for the user to provide a new name
- Update `parsed_config['dsName']` and retry the API call
- Loop until `body.data == false`

---

### Step 6: Upload the File to OSS (if source-file-path has a value)

**Goal**: if the `source-file-path` field is non-empty, upload the metadata file to OSS. Generate a unique filename to prevent overwrites.

> **CLI command**: `lhm-sch-ds upload --file <LOCAL_FILE_PATH>` performs the complete upload — obtaining STS credentials, generating a unique OSS object name, and uploading the file via multipart/form-data. On success it returns `oss_filename`, which the Agent writes back into `source-file-path` before calling `create` (Step 7). The local file is not modified.
>
> For manual/curl uploads, the low-level command `lhm-sch-ds oss-key` returns the raw credentials (`status=ok` with `oss.{ak,policy,signature,security_token,dir,...}` and an `expired` flag); the Python/curl snippets below document that path and are for SDK-level debugging only.

**Condition check**:
- Parse `parsed_config['dsConfig']['source-file-path']`
- If the field is empty or null → skip to Step 8
- If the field has a value → continue with the upload

**Generate a unique filename**:
- Extract the original filename from `source-file-path`
- Generate a timestamp-based unique name: `{YYYYMMDDHHmmss}_{original_filename}`
- Store it as `OSS_FILENAME` for the upload and subsequent steps
```python
import os
from datetime import datetime
original_path = parsed_config['dsConfig']['source-file-path']
original_filename = os.path.basename(original_path)
timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
OSS_FILENAME = f"{timestamp}_{original_filename}"
```

**Obtain OSS credentials**:
```python
request = lhm_models.GetMetaOssTempKeyRequest()
response = client.get_meta_oss_temp_key(request)
body = response.body
```

**Validate credentials**:
- Check that `body.success == true` and `body.data` exists
- Verify `time.time() < body.data.expire` (credentials not expired)
- If expired or invalid → report the error and **abort**

**Upload the file**:
- Construct the curl command following [OSS file upload example (curl)](API.md#oss-file-upload-example-curl)
- Replace the placeholders with the actual values from `body.data`:
  - `key`: `{body.data.dir}{OSS_FILENAME}` (use the generated unique filename)
  - `policy`: `body.data.policy`
  - `OSSAccessKeyId`: `body.data.ak`
  - `signature`: `body.data.signature`
  - `x-oss-security-token`: `body.data.securityToken`
  - `file`: the local file at the **original** `source-file-path` (do not rename or modify the local file)
- Execute the upload via subprocess or an equivalent mechanism
- **Always set explicit network timeouts** on the upload call so a stalled OSS request cannot hang the flow indefinitely: for `curl` use `--connect-timeout 10 --max-time 600`; for a Python `subprocess` use a matching `timeout=` value (e.g. `timeout=600`)
- Verify upload success (HTTP 200/204 response)
- If the upload fails → report the error and **abort**

> ⚠️ **Security constraint**: the local file at `source-file-path` must never be renamed, moved, copied, or modified. Only the OSS object key uses the generated `OSS_FILENAME`. The original local file stays untouched.

---

### Step 7: Update source-file-path to the OSS Filename

**Goal**: set `source-file-path` to the exact filename used in the OSS upload.

**Condition**: execute only when `source-file-path` was non-empty in Step 6.

**Action**:
```python
parsed_config['dsConfig']['source-file-path'] = OSS_FILENAME
```

**Example**:
- Original local path: `/Users/Admin/Downloads/lhm/airflow/data.zip`
- Generated OSS filename: `20260528200109_legao.zip`
- Updated `source-file-path`: `20260528200109_legao.zip`

**Critical**: the value in `source-file-path` must exactly match the `key` suffix used in the OSS upload so the backend can locate the file.

---

### Step 8: Create the Data Source

**Goal**: create the new data source via the API.

> **CLI command**: `lhm-sch-ds create --config-file <PATH>`. The CLI reads `dsName`/`categoryType`/`dsType`/`dsConfig`/`dsStatus` from the file and serializes `dsConfig` to a JSON string internally. Mapping: `ok` → with `ds_id`, `failed` → abort. The raw API call below is for SDK-level debugging only.

**API call**:
```python
import json
request = lhm_models.AddMetaDataComponentRequest(
    ds_name=parsed_config['dsName'],
    category_type=parsed_config['categoryType'],
    ds_type=parsed_config['dsType'],
    ds_config=json.dumps(parsed_config['dsConfig']),  # serialize to a JSON string
    ds_status=parsed_config.get('dsStatus', 0)
)
response = client.add_meta_data_component(request)
body = response.body
```

**Response handling**:

| Condition | Action | Next step |
|-----------|--------|-----------|
| `body.success == true` | Creation succeeded; store `body.data` as `NEW_DS_ID` | **End the workflow** — go to Step 9 only if the user explicitly requested a connectivity test |
| `body.success == false` | Creation failed | Report `body.err_message` and **abort** |

**Critical**: store `NEW_DS_ID` for subsequent operations (such as the connectivity test), but **do not** expose this ID in user-visible output. Output the success message: "✓ Data source created successfully". Unless the user explicitly asked for a connectivity test, this is the **terminal step** — do **not** proactively ask "Do you want to test connectivity?"; the workflow ends here.

---

### Step 9: Optional Connectivity Test

**Goal**: test data source connectivity if the user requests it.

> **CLI command**: `lhm-sch-ds test-conn --config-file <PATH> [--ds-id <DS_ID>]`. The CLI derives `dsVersion` from `dsConfig.dsVersion`. Mapping: `ok` → connectivity passed, `failed` → failed (with `err_message`). The raw API call below is for SDK-level debugging only.

**Entry conditions**:
- Coming from Step 4 (an existing data source was chosen) or Step 8 (a new data source was created)
- The user **explicitly requested** a connectivity test in their instruction. This step is **never** triggered proactively by the Agent — if the user did not ask for a connectivity test, the workflow already ended at Step 4 / Step 8. Do **not** ask "Do you want to test connectivity?".

**Condition check**:
- If `source-file-path` was originally non-empty/non-null → skip the connectivity test and **end the workflow**
- If `source-file-path` is null or absent → continue with the test

**API call**:
```python
request = lhm_models.ExecWorkflowConnectivityRequest(
    ds_name=parsed_config['dsName'],
    ds_config=json.dumps(parsed_config['dsConfig']),
    ds_type=parsed_config['dsType'],
    ds_version=parsed_config['dsConfig']['dsVersion'],
    id=NEW_DS_ID if 'NEW_DS_ID' in locals() else None
)
response = client.exec_workflow_connectivity(request)
body = response.body
```

**Response handling**:

| `body.success` | Action |
|----------------|--------|
| `true` | Output "✓ Data source connectivity check passed" and **end the workflow** |
| `false` | Output "✗ Connectivity check failed: [{body.err_code}] {body.err_message}" and **end the workflow** |

---

## Error Handling Principles

1. **Never guess parameters**: all data source names, IDs, and file paths must come from API responses, user input, or the parsed config file
2. **Always check the `success` field first**: verify `body.success == true` before processing `data`
3. **Parse JSON safely**: wrap `json.loads()` in try-except; malformed JSON should trigger an abort and log the raw data
4. **Preserve request_id**: include `request_id` in every error message for troubleshooting
5. **User-friendly messages**: translate technical errors into actionable guidance
6. **Abort on unknown errors**: never silently ignore unexpected responses or failures
7. **Credential safety**: never log or expose `securityToken`, `ak`, or sensitive configuration values

## Agent Instructions

When executing this workflow:

1. **Validate the environment first** (see the prerequisites section), completing it before Step 1 begins
2. **Maintain state explicitly**: track `DS_NAME`, `parsed_config`, `NEW_DS_ID`, and `source-file-path` state across steps
3. **Use AskUserQuestion for all user decisions**: especially data source selection and name changes (connectivity testing is **not** prompted — it runs only on the user's explicit request)
4. **Log all API calls**: print request parameters and response `request_id` to stderr for debugging
5. **Verify before operating on files**: always verify a file exists before reading/uploading it
6. **Handle OSS credentials carefully**: check the expiration time before use; do not cache them beyond the current session
7. **Strip paths correctly**: use `os.path.basename()` to ensure only the filename remains in `source-file-path`
8. **Refer to API.md** for complete field definitions, response schemas, and curl examples
9. **Template output**: when outputting the template in Step 2, keep the original formatting and comments completely unchanged
