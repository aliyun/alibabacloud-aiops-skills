---
name: alibabacloud-sas-log-to-oss
description: |
  Alicloud Service Scenario-Based Skill. Use for automating SLS (Log Service) log export to OSS (Object Storage) for cold storage archival.
  Triggers: "SLS", "OSS", "log export", "log shipping", "cold storage", "log archive", "Security Center log backup", "list LogStore", "view LogStore", "create export task", "delete export task", "stop export task", "start export task", "manage export task", "cleanup export task", "force delete export", "日志导出", "日志投递", "冷存储", "日志归档", "创建导出", "删除导出", "停掉导出", "暂停导出", "关闭导出", "停用导出", "终止导出", "启动导出", "查看导出", "列出导出", "清理导出".
---

# SLS Log Export to OSS

Automate exporting Alibaba Cloud SLS (Log Service) logs to OSS (Object Storage) for hot-to-cold storage transition. Applicable to Security Center log backup, log archiving, cold data storage, and similar scenarios.

## Architecture

SLS Project + LogStore + OSS Bucket + RAM Role (AliyunLogDefaultRole) + SLS OSS Export Task

---

## 1. Installation

### Aliyun CLI

**Pre-check: Aliyun CLI >= 3.3.3 required**
> [MUST] Verify: `aliyun version` — must be >= 3.3.3.
> - **First install or major upgrade:** `/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"`
> - **Routine update (CLI >= 3.3.5):** `aliyun upgrade` — prefer this built-in self-update over re-running the install script.
> - See [references/cli-installation-guide.md](references/cli-installation-guide.md) for full installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

### Python SDK

```bash
pip install -r scripts/requirements.txt
# or: pip install alibabacloud_sls20201230==5.14.0 alibabacloud_credentials==1.0.10
```

---

## 2. Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ALIBABA_CLOUD_ACCESS_KEY_ID` | Yes | AccessKey ID (auto-read by CredentialClient) |
| `ALIBABA_CLOUD_ACCESS_KEY_SECRET` | Yes | AccessKey Secret (auto-read by CredentialClient) |
| `ALIBABA_CLOUD_ACCOUNT_ID` | Yes | 12-digit Alibaba Cloud account ID, used to construct RAM role ARN |

`ALIBABA_CLOUD_ACCOUNT_ID` is used to construct the RAM role ARN in the format:
`acs:ram::<account-id>:role/aliyunlogdefaultrole`

---

## 3. Authentication

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

This skill uses `CredentialClient` to automatically load credentials from environment variables or configuration files — no hardcoded AK/SK in code. `ALIBABA_CLOUD_ACCOUNT_ID` must be set separately for RAM role ARN construction.

---

## 4. RAM Policy

SLS APIs and corresponding RAM permissions used by this skill:

| Product | RAM Action | Description |
|---------|-----------|-------------|
| SLS | `sls:ListLogStores` | List LogStores |
| SLS | `sls:CreateOSSExport` | Create OSS export task |
| SLS | `sls:ListOSSExports` | List export tasks |
| SLS | `sls:GetOSSExport` | Get export task details |
| SLS | `sls:UpdateOSSExport` | Update export task |
| SLS | `sls:StartOSSExport` | Start export task |
| SLS | `sls:StopOSSExport` | Stop export task |
| SLS | `sls:DeleteOSSExport` | Delete export task |

> **[MUST] Error Handling and Human-In-The-Loop (HITL):** When any command or API call fails, identify the error type and follow the corresponding handling process. For ALL error types listed below, you MUST immediately stop further execution, output the exact error message received, and respond with the standardized error message format. Do NOT attempt to retry, rephrase the command, or proceed to the next step. Report the error to the user with remediation guidance — the user will decide next steps.
>
> **Error Identification and Handling Rules:**
>
> | Error Type | Error Codes / Keywords | Handling Process |
> |------------|----------------------|------------------|
> | **Permission** | `401`, `403`, `Forbidden`, `AccessDenied`, `Forbidden.RAM`, `Unauthorized`, `does not belong` | 1. Read [references/ram-policies.md](references/ram-policies.md) for required permissions\n2. Use `ram-permission-diagnose` skill to guide the user\n3. Output: "Operation failed — insufficient RAM permissions. Please grant the required permissions and retry."\n4. **Report the error to the user with remediation guidance** |
> | **Parameter** | `400`, `InvalidParameter`, `MissingParameter`, `invalid` | 1. List the specific invalid/missing parameters from the error message\n2. Output: "Operation failed — parameter error: [details]. Please verify the parameters and retry."\n3. **Report the error to the user with remediation guidance** |
> | **Throttling** | `503`, `Throttling`, `flow control`, `rate limit` | 1. Output: "Operation failed — request throttled. Please wait a moment and retry later."\n2. **Report the error to the user with remediation guidance** — do NOT auto-retry |
> | **Conflict** | `409`, `JobAlreadyExist`, `already exist`, `conflict` | See [Section 7 Step 2: Idempotency Handling](#step-2-create-export-task-single-logstore) |
> | **System** | `500`, `InternalError`, `ServiceUnavailable` | 1. Output: "Operation failed — server error. Please retry later or contact Alibaba Cloud support."\n2. **Report the error to the user with remediation guidance** |
>
> **Standardized Error Message Format (MUST use for all unrecoverable errors):**
> ```
> Operation failed — requires human intervention: [error reason].
> Please verify permissions/parameters and retry.
> ```
> Your error report MUST contain the exact phrase `Operation failed — requires human intervention:` — do NOT substitute alternative phrasing such as "I cannot proceed", "Please check", or "Error occurred".
>
> **[MUST] Error Transparency:** When a command or API call fails, capture and print the complete original error — including the HTTP status code, error code (e.g., `Forbidden.RAM`, `InvalidParameter`, `Throttling.User`), and the raw error message from stderr/stdout — BEFORE giving remediation guidance. Example: `Error: HTTP 403 | Code: Forbidden.RAM | Message: User is not authorized to perform sls:CreateOSSExport`. Never swallow, paraphrase-only, or truncate the original error text.
>
> **[CRITICAL] Do NOT refuse to help:** When an error occurs, NEVER use refusal phrases such as "无法帮您", "我无法完成", "无法继续", "帮不了", "I cannot help", or "I am unable to help". Instead, explain the specific error, its cause, and the exact steps the user should take to resolve it, then hand the decision back to the user.
>
> **[CRITICAL] No Auto-Retry:** If a command fails with any error code listed in the table above, you MUST immediately STOP execution. Do NOT retry the same command, do NOT modify parameters and retry, do NOT read reference files to "fix" the error and re-execute, and do NOT proceed to the next workflow step. Output the exact error message and the standardized HITL response. Re-executing a failed command without explicit user approval is a violation. (Exception: the `JobAlreadyExist` idempotency verification in Section 7 Step 2 is a read-only `get-export` check, not a retry.)

---

## 5. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.
>
> **Confirmation Rules:**
> 1. If the user has already provided all required parameters (project, logstore, bucket, name, etc.) in their message, you MAY proceed directly without additional confirmation.
> 2. If any required parameter is missing or ambiguous, you MUST call `ask_user_question` to obtain the missing parameter before execution.
> 3. If `ask_user_question` returns empty or fails, use the parameters from the user's original message. Do NOT proceed with inferred or default values for missing required parameters.
> 4. For optional parameters not specified by the user, use the defaults listed in the table below.

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `--project` | Required | SLS Project name | - |
| `--bucket` | Required (create/batch) | OSS Bucket name | - |
| `--logstore` | Required (create-export) | Source LogStore name | - |
| `--name` | Required (create/get/stop/start/delete) | Export task name | - |
| `--endpoint` | Optional | SLS API endpoint | `cn-hangzhou.log.aliyuncs.com` |
| `--oss-endpoint` | Optional | OSS internal endpoint | `https://oss-cn-hangzhou-internal.aliyuncs.com` |
| `--role-name` | Optional | RAM role name | `aliyunlogdefaultrole` |
| `--prefix` | Optional | OSS file prefix | `sls-export/` |
| `--suffix` | Optional | OSS file suffix | `.json` |
| `--content-type` | Optional | Storage format: json/csv/parquet/orc | `json` |
| `--compression` | Optional | Compression: snappy/gzip/zstd/none | `snappy` |
| `--buffer-interval` | Optional | Buffer interval, seconds (300-900) | `300` |
| `--buffer-size` | Optional | Buffer size, MB (5-256) | `256` |
| `--from-time` | Optional | Start time: 1=from first log, or Unix timestamp | `1` |
| `--to-time` | Optional | End time: 0=run forever, or Unix timestamp | `0` |
| `--path-format` | Optional | OSS partition format | `%Y/%m/%d/%H/%M` |
| `--timezone` | Optional | Timezone | `+0800` |

---

## 6. Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) ONCE for the entire session by running:

```bash
SKILL_SESSION_ID=$(python3 -c 'import secrets; print(secrets.token_hex(16))')
```

If `python3` is unavailable, use: `SKILL_SESSION_ID=$(openssl rand -hex 16)`.
Do NOT use `xxd` (not available in all environments). The value MUST be exactly 32 lowercase hex characters (`secrets.token_hex(16)` and `openssl rand -hex 16` both produce exactly 32) — do NOT concatenate or repeat the value. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-log-to-oss/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun ecs describe-instances --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-log-to-oss/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

**Script / Terraform execution:** When running Python SDK scripts or Terraform commands or bash scripts, inject the session-id via inline environment variable so the code can read it at runtime:

```bash
# Python SDK script
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py list-logstores --project <your-sls-project>

# Terraform
SKILL_SESSION_ID={session-id} terraform apply
```

Scripts and Terraform configs should read `SKILL_SESSION_ID` from the environment (default to empty string if absent). See `references/how-to-implement-by-common-sdk.md` for SDK patterns.

---

## 7. Core Workflow

> **[CRITICAL] EXECUTION METHOD PRIORITY (applies to EVERY step below):**
> 1. **ALWAYS** use `python3 scripts/sls_oss_export.py <subcommand>` as the **PRIMARY** execution method for all SLS OSS export operations.
> 2. **User-specified tooling exception**: If the user explicitly asks to use the aliyun CLI, follow the user's request — use the aliyun CLI in **plugin mode** with lowercase-hyphenated subcommands (`list-log-stores`, `create-oss-export`, `list-oss-exports`, `get-oss-export`, `start-oss-export`, `stop-oss-export`, `delete-oss-export`) and include `--user-agent` per Section 6. **CLI precondition**: BEFORE the first aliyun sls call, run `aliyun configure set --auto-plugin-install true && aliyun plugin update` once to enable plugin-mode subcommands — without the sls plugin, lowercase-hyphenated subcommands fail with "not a valid api".
> 3. **Fallback**: Only fall back to the aliyun CLI on your own if the Python script cannot run (e.g., missing dependencies that cannot be installed). State the fallback reason before switching.
> 4. **NEVER** use PascalCase API names as CLI subcommands (e.g., `CreateOSSExport`, `ListOSSExports`, `GetOSSExport`) under any circumstance. Violating this rule will cause workflow failure.

> **Note**: Parameters such as `<your-sls-project>` must be provided by the user. Confirm the Parameter Confirmation section before execution.

### Step 1: List LogStores

View the log stores to export:

```bash
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py list-logstores \
  --project <your-sls-project>
```

### Step 2: Create Export Task (Single LogStore)

```bash
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py create-export \
  --project <your-sls-project> \
  --logstore <logstore-name> \
  --name export-<logstore-name>-to-oss \
  --bucket <your-oss-bucket>
```

**[MUST] Create-First (no existence pre-check):** When the user asks to create an export task, attempt `create-export` directly — do NOT pre-check task existence with `list-exports`/`get-export` and do NOT skip the create call because a task with the same name might already exist. Rely on the idempotency handling below to resolve `JobAlreadyExist`.

**[MUST] Idempotency Handling:** If `create-export` returns `JobAlreadyExist` (HTTP 400), do NOT treat it as a failure. Instead:
1. Run `get-export` to verify the existing task configuration matches the expected values (project, logstore, bucket, name)
2. If configuration matches and status is `RUNNING`, treat the task as successfully created and continue
3. If configuration does not match or status is abnormal (e.g., `STOPPING`, `FAILED`, `UNKNOWN`), **DO NOT wait, retry, or auto-fix**. Immediately report the exact status and configuration discrepancy to the user with remediation guidance.
4. Do NOT block the workflow on `JobAlreadyExist` when the existing task is valid (status `RUNNING` and configuration matches)

### Step 3: Batch Create (All LogStores)

```bash
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py batch-create \
  --project <your-sls-project> \
  --bucket <your-oss-bucket> \
  --prefix sls-export/
```

Export only specified LogStores:

```bash
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py batch-create \
  --project <your-sls-project> \
  --bucket <your-oss-bucket> \
  --logstores logstore1,logstore2,logstore3
```

### Step 4: Verify Export Tasks

```bash
# List all export tasks
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py list-exports \
  --project <your-sls-project>

# View details of a specific task
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py get-export \
  --project <your-sls-project> \
  --name export-<logstore-name>-to-oss
```

### Step 5: Manage Export Tasks

```bash
# Stop a task
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py stop-export \
  --project <your-sls-project> --name <task-name>

# Start a stopped task
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py start-export \
  --project <your-sls-project> --name <task-name>

# Delete a task
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py delete-export \
  --project <your-sls-project> --name <task-name>
```

> **[MUST] Execute User-Requested Operations:** Even if `get-export` returns 404 (task not found), if the user explicitly requests to start, stop, or delete a task, you MUST still attempt the corresponding `start-export`/`stop-export`/`delete-export` command. Let the API return the final status — do not preemptively skip the operation based on a prior query failure.
>
> **[MUST] Desired-State Idempotency:** If a start/stop/delete call returns 404 (not found) or 400 invalid-state (e.g., stopping an already `STOPPED` task), verify the current state via `get-export` or `list-exports`:
> - If the resource is already in the desired end-state (e.g., already deleted, already `STOPPED` for a stop request, already `RUNNING` for a start request), treat the operation as **SUCCESS** and report: "Operation completed — target is already in the expected state." Do NOT treat it as a failure and do NOT retry.
> - Otherwise, follow the error handling rules in Section 4.

### Export Task Naming Rules

Batch-created tasks follow the naming pattern: `export-<logstore-name>-to-oss`

- Only lowercase letters, digits, hyphens (-), and underscores (_) are allowed
- Must start and end with a lowercase letter or digit
- Length must be 2-64 characters
- Must be unique within the same Project

---

## 8. Success Verification Method

For detailed verification steps, see [references/verification-method.md](references/verification-method.md).

**Quick verification**: After creating an export task, confirm the task status is `RUNNING`:

```bash
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py list-exports \
  --project <your-sls-project>
```

**[MUST] Data Integrity Rules:**
1. **Never modify API output**: Do NOT alter, rename, or transliterate any field values returned by the API or script (e.g., LogStore names, Bucket names, task names, status values). Always output original values verbatim. Copy values programmatically (e.g., via JSON parsing or shell pipes) instead of retyping them by hand — manual retyping introduces typos (e.g., `RUNING` instead of `RUNNING`) or wrongly "corrected" names.
2. **Post-operation verification**: After executing `delete-export` or `create-export`, you MUST run `list-exports` or `get-export` to verify the operation took effect. If the verification result contradicts the operation result (e.g., task still shows `RUNNING` after deletion), report the discrepancy to the user.
3. **Accurate counting**: When summarizing or counting results (e.g., task distribution by Bucket, number of tasks), you MUST parse the raw API or script output line by line and count exact occurrences. Do NOT use words like "approximately", "about", "~", "约", or round numbers. If the output is truncated or incomplete, explicitly state "Output truncated — exact count unavailable" and request the user to rerun the command with pagination or full output enabled.

---

## 9. Cleanup

### Stop All Export Tasks

```bash
# List all tasks first
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py list-exports \
  --project <your-sls-project>

# Stop each task
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py stop-export \
  --project <your-sls-project> --name <task-name>
```

### Delete Export Tasks

```bash
SKILL_SESSION_ID={session-id} python3 scripts/sls_oss_export.py delete-export \
  --project <your-sls-project> --name <task-name> --force
```

> **Note**: Deleting an export task does not delete data already exported to OSS. To clean up OSS data, use the OSS console or the `ossutil` tool.

---

## 10. Command Tables

For the complete list of CLI/script commands, see [references/related-commands.md](references/related-commands.md).

---

## 11. Best Practices

1. **Same-region delivery**: The SLS Project and OSS Bucket must be in the same region, otherwise the export task creation will fail.
2. **WORM policy**: The target OSS Bucket must not have WORM (compliance retention) policy enabled.
3. **Buffer configuration**: Control delivery frequency via `--buffer-interval` (300-900 seconds) and `--buffer-size` (5-256 MB). Each Shard independently determines delivery frequency based on buffer size and time thresholds.
4. **CSV/Parquet/ORC formats**: When using these formats, specify field names via `--columns` (comma-separated). Parquet/ORC fields default to type `string`.
5. **Batch creation**: During batch creation, existing export tasks are automatically skipped — no duplicates are created.
6. **Single-task idempotency**: When `create-export` returns `JobAlreadyExist`, verify the existing task via `get-export`. If the configuration matches and status is `RUNNING`, treat it as success — do not block the workflow.
7. **Status confirmation**: After creation, confirm task status is `RUNNING` via `list-exports`.
8. **Partition format**: For compatibility with Hive/MaxCompute and other big data platforms, use `key=value` format partition paths.
9. **RAM role**: When using the default role `aliyunlogdefaultrole`, ensure the role has been properly granted read/write permissions for both SLS and OSS.
10. **Data integrity**: Never modify API-returned field values. Always perform post-operation verification after create/delete operations.

---

## 12. Reference Links

| Reference | Contents |
|-----------|----------|
| [references/reference.md](references/reference.md) | SLS OSS Export API detailed reference |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policy document |
| [references/verification-method.md](references/verification-method.md) | Success verification method |
| [references/related-commands.md](references/related-commands.md) | Complete command list |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation guide |
| [references/aliyun-help-create-sls-export-oss-task.md](references/aliyun-help-create-sls-export-oss-task.md) | Official Alibaba Cloud SLS OSS export help doc |
| [references/aliyun-help-oss-bucket.md](references/aliyun-help-oss-bucket.md) | Official Alibaba Cloud OSS Bucket help doc |
