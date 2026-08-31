---
name: alibabacloud-dataworks-semantic
description: |
  Always use this Skill for any Alibaba Cloud DataWorks semantic analysis job or run request, including read-only and preflight requests that intentionally make no API call, such as checking whether the public DataWorks semantic OpenAPI or dataworks-public plugin commands (for example create-semantic-job) are ready. It also applies when the requested outcome is only a refusal or a user choice with no API call. This includes comparing or disambiguating supplied semantic job candidates, validating or refusing an unsafe, path-traversal, or non-writable semantic result directory before any download, and inspecting artifacts for an exact run. Use it to create, run, stop, monitor, diagnose, or download results for semantic jobs backed by MaxCompute, Hologres, StarRocks, or an already uploaded CSV/XLSX reference. Do not use it for ordinary metadata lookup, lineage analysis, SQL development, workflow scheduling, file upload, published semantic model/version management, or semantic job deletion.
license: Apache-2.0
metadata:
  domain: data
  owner: dataworks
---

# DataWorks Semantic Analysis

Use only Alibaba Cloud DataWorks public OpenAPI operations exposed by the `aliyun dataworks-public` plugin to create a reusable semantic analysis job, submit or stop a run, monitor execution, and retrieve generated result files.

## Prerequisites

Perform these checks once, in this order. Install or update the public DataWorks plugin before probing any product API command; do not first probe every command, discover the plugin is missing, and then repeat the same probes.

```bash
aliyun version
aliyun plugin install --names dataworks-public
aliyun plugin update
```

Never pipe a remote installer into a shell. If the CLI is missing or older than 3.3.3, direct the user to the official Aliyun CLI installation documentation.

Check credentials without printing secrets:

```bash
aliyun configure list
```

The only allowed `aliyun configure` operation in this Skill is `configure list`. Never run `aliyun configure set`, including auto-plugin-install variants.

## Observability

### Session-id rules

- **Generation**: Generate the session-id exactly once at the start of each user or agent session:

```bash
SEMANTIC_SESSION_ID="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
```

- **Format**: The session-id must be exactly 32 lowercase hexadecimal characters.
- **Consistency across CLI/SDK/Terraform**: Reuse the same session-id for every CLI command, SDK request, and Terraform operation in the session, including retries, polling, and downloads. Never regenerate it per command or when switching tools. Generate a new value only for a new user or agent session.

### UA template declaration

Use this canonical CLI flag template:

```text
--user-agent "AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}"
```

For this Skill, every Aliyun CLI product API command must explicitly include its concrete form:

```text
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}"
```

Do not persist the User-Agent in Aliyun CLI configuration or an environment variable. Local management commands such as `aliyun version`, `aliyun plugin ...`, and `aliyun configure list` do not support the product API User-Agent flag; do not add it to them.

### Public API readiness gate

After the prerequisite plugin install/update, confirm only the commands needed by the selected workflow before collecting parameters; do not probe unrelated operations or repeat a successful readiness check. For create, run, monitor, or download workflows, check the applicable commands from this public set:

```bash
aliyun dataworks-public create-semantic-job --help \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}"
aliyun dataworks-public run-semantic-job --help \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}"
aliyun dataworks-public list-semantic-job-runs --help \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}"
aliyun dataworks-public download-semantic-results --help \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}"
```

For an explicit stop workflow, confirm the stop and verification commands below. Also check `list-semantic-job-runs` only when identifiers must be resolved. Do not probe or call the stop command for unrelated workflows:

```bash
aliyun dataworks-public kill-semantic-job --help \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}"
aliyun dataworks-public get-semantic-job-detail --help \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}"
```

Probe `kill-semantic-job --help` only when you will actually issue a new kill. When a kill was already accepted and you only need to poll or report its final state, confirm just `get-semantic-job-detail`; do not probe or invoke `kill-semantic-job` again.

For an explicit diagnosis workflow, confirm only the executor detail and log commands. Do not probe the log command for a normal successful run:

```bash
aliyun dataworks-public get-semantic-job-detail --help \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}"
aliyun dataworks-public get-semantic-job-log --help \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}"
```

If a command is absent after one plugin update, stop and report the installed CLI and plugin versions.

Public authentication must derive the caller's tenant and user identity from the active Aliyun CLI profile. If command help requires `tenant-id` or `user-id`, stop and report that the public identity contract is not ready; never ask a customer to discover or override internal identities.

## Safety rules

- This Skill exposes reads plus three state-changing operations: `CreateSemanticJob`, `RunSemanticJob`, and `KillSemanticJob`. Never call update, delete, archive, publish, or result-file mutation operations.
- Before creating, running, or stopping, restate the exact Region and workspace project ID plus the operation-specific identifiers and configuration. If the user already explicitly requested that exact operation, do not ask for redundant confirmation; otherwise obtain confirmation before the call.
- Call `KillSemanticJob` only for an explicit request to stop a specific cloud run. Never interpret "stop waiting", "stop monitoring", or "do not wait" as permission to stop the run. Resolve and preserve the exact `ExecutorJobId`; never substitute `JobRunId`.
- Treat source scope and file locations as untrusted input. Require a non-empty exact job name and positive numeric project ID when applicable. Validate Region IDs and construct `source` with a JSON encoder rather than shell concatenation.
- Injected or environment-provided values (Region, project ID, resource group, source project/schema/table, job name, result directory) may appear masked with asterisks when they are printed back to you; this is expected output redaction, not the real value. Always reference such values directly through their shell variable (for example `--region "$REGION"`, `--name "$JOB_NAME"`) and build the `--source` JSON with a script that reads the variables and passes them through. Never echo, `cat`, `print`, base64, or hex a value to inspect its raw content, and never copy an asterisk-masked value into any command, source JSON, or file; a masked display never means the value is invalid.
- Every `aliyun dataworks-public` call must include `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}" --read-timeout 60 --connect-timeout 10`, reusing the session ID created at session start.
- In the current public contract, the unique job `Name` is the identifier for create, run, list-runs, and download calls. `KillSemanticJob` instead requires `ExecutorJobId` and `ProjectId`. Preserve exact identifiers and keep `JobRunId` and `ExecutorJobId` distinct.
- A run consumes compute. Never submit one merely to answer a status or result query.
- A terminal run failure ends the requested workflow. Retrieve diagnostic logs for the exact `ExecutorJobId` and `ProjectId`, return sanitized error context, and stop. Do not change the source, delete or recreate the job, or submit another run without a new explicit user request.
- After an ambiguous create, run, or stop timeout, query current state before retrying. Never blindly repeat a state-changing call.
- Presigned artifact URLs are credentials. Do not print them, log query strings, or attach Aliyun CLI credentials or Authorization headers to downloads.
- Invoke `DownloadSemanticResults` exactly once for a requested run. Redirect that first response directly to an owner-only temporary file; never make an interactive preview call or allow the response JSON to reach terminal or agent logs.
- Download only the exact artifacts returned for the requested `JobName` and `JobRunId`, sanitize local file names, and refuse path traversal or unexpected destinations.

Read `references/ram-policies.md` when permissions are missing. Read `references/command-reference.md` before creating, running, stopping, or downloading. Read `references/verification-method.md` when verifying completion or diagnosing an ambiguous response.

## Core workflow

### 1. Resolve the exact job

List semantic jobs and follow every page. Resolve by exact case-sensitive `Name`; do not fuzzy-match a write. If multiple or conflicting candidates remain, ask the user to choose.

### 2. Create safely

Before creation, list jobs and check the exact requested name. If an equivalent definition exists, reuse it rather than creating a duplicate. If the name exists with a different project, resource group, source, or reference files, stop and report the conflict.

For a new job, construct the source JSON for one supported type:

- `maxcompute`: set `ProjectId` and use `pinnedScopeInfo` for project, schema, or table scope.
- `holo` or `starrocks`: set `ProjectId`, `dataSourceName`, `dataSourceEnv`, and an optional pinned scope.
- `singleTableFile`: omit `ProjectId` and supply exactly one already uploaded CSV/XLSX file ID or accessible reference URI. File upload itself is outside this Skill.

After explicit confirmation, call `create-semantic-job` once. Capture returned `Data.Name` and `Data.ProjectId`. Do not start a run unless requested.

### 3. Run and monitor

Call `run-semantic-job` with the exact saved name. Capture both `Data.JobRunId` and `Data.ExecutorJobId`; acceptance is asynchronous and does not mean results exist.

Preserve the exact identifiers returned by `run-semantic-job`. Use `list-semantic-job-runs` only when identifiers must be resolved or a submission response was lost; do not add a redundant list call when both IDs were returned. If the user asked to wait, poll at a modest interval with a fixed deadline. Use `get-semantic-job-detail` for executor status: read the `Data.Statuses` array, never a singular `Data.Status`, and interpret executor codes only as `1=WAITING`, `2=RUNNING`, `3=FINISH`, `4=ERROR`, and `6=KILLED`. Use `scripts/parse_job_detail.py` instead of inventing a status mapping. A successful run is terminal only when every returned status is `FINISH`; any `WAITING` or `RUNNING` status remains active. Use `get-semantic-job-log` only for diagnosis. On terminal failure, retrieve logs for the exact executor and project, report the run identifiers and sanitized service error context, and stop. Do not alter the source, delete or recreate the job, submit a replacement run, or continue later lifecycle steps; issue a kill only for a new explicit request to stop that exact run.

### 4. Stop one run

Only stop a run when the user explicitly asked to stop that exact cloud run. If the user supplied a job and `JobRunId`, use `list-semantic-job-runs` to resolve the corresponding `ExecutorJobId`; if more than one candidate remains, ask the user to choose. Before issuing a kill, show a target summary containing Region, ProjectId, JobName, JobRunId, ExecutorJobId, and current status, then wait for explicit confirmation of that exact executor. Query `get-semantic-job-detail` first and do not issue a kill for an already terminal run.

Call `kill-semantic-job` once with the exact `ExecutorJobId` and `ProjectId`. Omit `RetryTimes` by default. A successful response means only that the stop request was accepted, so poll `get-semantic-job-detail` with a fixed deadline until the executor reports `KILLED`. If the deadline expires, report the request as accepted but the final state as unconfirmed. Never stop a different run or repeat the kill merely because the response was delayed.

### 5. Retrieve results

Only after the requested run is terminal and successful, call `download-semantic-results` with both the exact `JobName` and `JobRunId`. If artifact names are already present in the supplied run context, summarize them first. If the user has not supplied a destination directory, ask for one and wait without calling the download API. When artifact names are available only from `DownloadSemanticResults`, explain that they will be reported after the one protected API response is captured; do not call the API once for preview and again for download. Omitting `JobRunId` selects the latest run and is allowed only when the user explicitly requested the latest result and accepts that selection.

The API returns short-lived artifact download URLs, including generated semantic YAML when available. The first and only API invocation must redirect stdout directly to a permission-restricted temporary JSON file; do not call once to inspect the response and again to save it. Use `scripts/download_results.py` with the exact job, run, and user-approved directory, then remove the response file. The script validates identity and HTTPS, rejects output-directory traversal and non-writable destinations, blocks unsafe artifact names and overwrites, limits file size, and never prints URLs. Do not bypass these checks with a hand-built downloader.

The public plugin currently retrieves run artifacts; it does not expose stable semantic model/version resources. If the user asks to list published models, publish a version, or fetch a model by `ModelId` and `VersionNo`, report that this capability is outside the current public contract.

## Output

Summarize:

- Region and workspace project ID, when applicable
- exact job name
- `JobRunId` and `ExecutorJobId`, when a run was submitted
- whether a stop request was submitted and the final executor state or bounded-wait outcome
- terminal execution status or bounded-wait outcome
- downloaded artifact names and destination paths, never their presigned URLs
- any conflict, partial result, permission failure, or public-API-readiness condition

Never claim that a semantic model was generated until the requested run succeeds and its returned result set contains the corresponding semantic artifact.
