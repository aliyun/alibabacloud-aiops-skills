# Command Reference

This reference matches Aliyun CLI 3.4.10 with `dataworks-public` plugin 0.7.10. Live `--help` output remains authoritative. If a command is absent or a flag differs, stop instead of guessing.

Before using this reference, reuse the 32-character hexadecimal `SEMANTIC_SESSION_ID` generated once at session start as described in `SKILL.md`. Append these flags to every Aliyun CLI product API command:

```text
--region "$REGION_ID" --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}" --read-timeout 60 --connect-timeout 10
```

## List jobs

```bash
aliyun dataworks-public list-semantic-jobs \
  --region "$REGION_ID" \
  --page-number 1 --page-size 200 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}" \
  --read-timeout 60 --connect-timeout 10
```

Follow all pages before concluding that a name is available. `Name` is unique within the current tenant and is the public identifier used by later calls.

## Create a MaxCompute job

Required customer inputs:

- Region ID
- DataWorks workspace `ProjectId`
- unique exact job name
- semantic runtime `ResourceGroupId`
- MaxCompute project, schema, or table scope
- optional reference file IDs or URIs

Example table-level source JSON:

```json
{
  "type": "maxcompute",
  "domain": "sales",
  "pinnedScopeInfo": [
    {
      "type": "table",
      "project": "project_name",
      "name": "orders"
    }
  ]
}
```

Add `"schema": "schema_name"` for a schema-enabled table. A project-level scope is `{"type":"project","name":"project_name"}`. Build JSON using a JSON encoder and pass it as one `--source` argument.

```bash
aliyun dataworks-public create-semantic-job \
  --region "$REGION_ID" \
  --name "$JOB_NAME" \
  --project-id "$PROJECT_ID" \
  --resource-group-id "$RESOURCE_GROUP_ID" \
  --source "$SOURCE_JSON" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}" \
  --read-timeout 60 --connect-timeout 10
```

For `holo` and `starrocks`, `source` also requires `dataSourceName` and `dataSourceEnv`; pass `ProjectId`. For `singleTableFile`, omit `ProjectId` and pass exactly one existing CSV/XLSX source through either `--reference-file-ids` or `--reference-file-uris`. Uploading a local file is outside this Skill; ask the user for an already uploaded `FileId` or accessible URI.

Never pass internal tenant, user, request-source, account, connection-secret, or AgentWorks-only fields.

## Run and inspect

```bash
aliyun dataworks-public run-semantic-job \
  --region "$REGION_ID" \
  --name "$JOB_NAME" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}" \
  --read-timeout 60 --connect-timeout 10

aliyun dataworks-public list-semantic-job-runs \
  --region "$REGION_ID" \
  --job-name "$JOB_NAME" \
  --page-number 1 --page-size 200 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}" \
  --read-timeout 60 --connect-timeout 10
```

`RunSemanticJob` returns `Data.JobRunId` and `Data.ExecutorJobId`. Never substitute one for the other.

For executor status or sanitized diagnostic logs:

```bash
aliyun dataworks-public get-semantic-job-detail \
  --region "$REGION_ID" \
  --executor-job-id "$EXECUTOR_JOB_ID" \
  --project-id "$PROJECT_ID" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}" \
  --read-timeout 60 --connect-timeout 10

aliyun dataworks-public get-semantic-job-log \
  --region "$REGION_ID" \
  --executor-job-id "$EXECUTOR_JOB_ID" \
  --project-id "$PROJECT_ID" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}" \
  --read-timeout 60 --connect-timeout 10
```

The current log command returns default log segments; it has no paging flags.

`GetSemanticJobDetail` returns executor codes in `Data.Statuses`, which is an array even for one command. There is no documented singular `Data.Status` field. The exact codes are:

| Code | State | Terminal | Successful |
|---:|---|---|---|
| 1 | `WAITING` | no | no |
| 2 | `RUNNING` | no | no |
| 3 | `FINISH` | yes | yes |
| 4 | `ERROR` | yes | no |
| 6 | `KILLED` | yes | no |

Redirect each detail response to a temporary JSON file and use the bundled parser. It emits one aggregate state without printing the response body:

```bash
umask 077
DETAIL_RESPONSE_FILE="$(mktemp)"
trap 'rm -f "$DETAIL_RESPONSE_FILE"' EXIT

aliyun dataworks-public get-semantic-job-detail \
  --region "$REGION_ID" \
  --executor-job-id "$EXECUTOR_JOB_ID" \
  --project-id "$PROJECT_ID" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}" \
  --read-timeout 60 --connect-timeout 10 \
  >"$DETAIL_RESPONSE_FILE"

EXECUTOR_STATE="$(python3 scripts/parse_job_detail.py --response "$DETAIL_RESPONSE_FILE")"

rm -f "$DETAIL_RESPONSE_FILE"
trap - EXIT
```

Do not substitute a guessed status table or parse `Data.Status`. `FINISH` means every returned status is code `3`. `ERROR` or `KILLED` means all entries are terminal and at least one entry has that state. If any entry is `WAITING` or `RUNNING`, the aggregate remains active. An empty, unknown, or malformed status set is not success; stop or continue bounded polling rather than guessing.

## Stop one run

Resolve the exact `ExecutorJobId` from `RunSemanticJob` or `ListSemanticJobRuns` and confirm the workspace `ProjectId`. Query `get-semantic-job-detail` first; do not send a stop request for an already terminal run.

```bash
aliyun dataworks-public kill-semantic-job \
  --region "$REGION_ID" \
  --executor-job-id "$EXECUTOR_JOB_ID" \
  --project-id "$PROJECT_ID" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}" \
  --read-timeout 60 --connect-timeout 10
```

`--retry-times` is optional and should be omitted unless the user explicitly requested a non-negative executor retry count. A successful `KillSemanticJob` response only acknowledges the request. Poll `get-semantic-job-detail` for the same executor and project, parsing `Data.Statuses` with `scripts/parse_job_detail.py`, until it reports the `KILLED` terminal state (executor status code `6`) or a fixed deadline expires. Never substitute `JobRunId`, stop an ambiguous candidate, or automatically repeat the kill after a timeout.

## Retrieve one run's artifacts

Create the response file before the API call and redirect the first and only response directly into it:

```bash
set -euo pipefail
umask 077

python3 scripts/download_results.py \
  --output-dir "$OUTPUT_DIR" \
  --validate-only

RESULT_RESPONSE_FILE="$(mktemp)"
trap 'rm -f "$RESULT_RESPONSE_FILE"' EXIT

aliyun dataworks-public download-semantic-results \
  --region "$REGION_ID" \
  --job-name "$JOB_NAME" \
  --job-run-id "$JOB_RUN_ID" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-semantic/${SEMANTIC_SESSION_ID}" \
  --read-timeout 60 --connect-timeout 10 \
  >"$RESULT_RESPONSE_FILE"

python3 scripts/download_results.py \
  --response "$RESULT_RESPONSE_FILE" \
  --job-name "$JOB_NAME" \
  --job-run-id "$JOB_RUN_ID" \
  --output-dir "$OUTPUT_DIR"

rm -f "$RESULT_RESPONSE_FILE"
trap - EXIT
```

Keep `--job-run-id` for deterministic retrieval. Without it, the service selects the latest run.

Each result contains `JobName`, `JobRunId`, and `DownloadUrl`; some releases may also return `FileName` or `InternalDownloadUrl`. Never run the API interactively to preview these fields. A second invocation creates a fresh set of credentials and needlessly exposes the first response.

Remove the temporary response file after the download. The script prefers only the public `DownloadUrl` and enforces:

1. confirm the response job and run match the request;
2. require HTTPS and a returned Alibaba Cloud artifact URL;
3. prefer `FileName`; when it is absent, derive only the URL path basename, never query parameters, then reject `..`, path separators, empty names, or control characters;
4. validate the output directory before requesting any presigned URL, reject `..` traversal and non-writable destinations, then download to a temporary file under that directory and atomically rename it;
5. set bounded transfer time and size limits and refuse redirects to non-HTTPS destinations;
6. never send Aliyun credentials or an Authorization header with a presigned URL;
7. do not reveal URL query strings in logs or final output.

If a destination file exists, stop and ask before overwriting it.

## Currently unavailable through the public plugin

Plugin 0.7.10 does not expose semantic model, version, version-view, version-file, or run-materialization commands. Do not invent unsupported command names.
