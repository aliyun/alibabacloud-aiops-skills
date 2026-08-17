# Success Verification Methods

After each write operation completes, use query tools to read back the target resource and assert key fields to determine whether the operation actually took effect.

## General Verification Patterns

| Write Operation (CLI / MCP) | Read-back Tool (CLI / MCP) | Verification Fields |
|-----------------------------|---------------------------|---------------------|
| `flow-create-pipeline` (MCP: `create_pipeline_from_description`) | `flow-get-pipeline` (MCP: `get_pipeline`) or `flow-list-pipelines --pipeline-name` | `id` exists, `name` matches. Note: `flow-create-pipeline` prints only a bare integer pipeline ID on success — treat that as success, not as malformed output |
| `flow-update-pipeline` (MCP: `update_pipeline`) | `flow-get-pipeline` (MCP: `get_pipeline`) | Changed fields match input parameters |
| `flow-create-pipeline-run` (MCP: `create_pipeline_run`) | `flow-get-latest-pipeline-run` (MCP: `get_latest_pipeline_run`) | `status ∈ {INIT, RUNNING, SUCCESS}`, not `FAIL/CANCELED` |
| `flow-execute-pipeline-job-run` (MCP: `execute_pipeline_job_run`) | `flow-get-pipeline-job-run-log` (MCP: `get_pipeline_job_run_log`) | Log contains latest output |
| `codeup-create-branch` (MCP: `create_branch`) | `codeup-get-branch` (MCP: `get_branch`) | Target `name` exists, `commit.id` matches source branch or is a new commit |
| `codeup-delete-branch` (MCP: `delete_branch`) | `codeup-list-branches` (MCP: `list_branches`) | Target branch is not in the returned list |
| `codeup-create-file` / `codeup-update-file` (MCP: `create_file` / `update_file`) | `codeup-get-file-blobs` (MCP: `get_file_blobs`) | Content matches expected value |
| `codeup-create-change-request` (MCP: `create_change_request`) | `codeup-get-change-request` (MCP: `get_change_request`) | `state == OPENED`, `sourceBranch/targetBranch` match |
| `codeup-create-change-request-comment` (MCP: `create_change_request_comment`) | `codeup-list-merge-request-comments` (MCP: `list_change_request_comments`) | New comment appears in the list. Prerequisite: fetch the patchset biz id via `codeup-list-change-request-patch-sets` — `--patchset-biz-id`, `--draft` and `--resolved` are all required, and omitting any of them fails client-side before the request is sent |
| `projex-create-sprint` (MCP: `create_sprint`) | `projex-get-sprint` (MCP: `get_sprint`) | Date range and name match |
| `projex-update-sprint` (MCP: `update_sprint`) | `projex-get-sprint` (MCP: `get_sprint`) | Changed fields have taken effect |
| `projex-create-workitem` (MCP: `create_work_item`) | `projex-get-workitem` (MCP: `get_work_item`) | `subject` matches, `workitemTypeId` is correct |
| `projex-update-workitem` (MCP: `update_work_item`) | `projex-get-workitem` (MCP: `get_work_item`) | Changed fields have taken effect |
| `projex-create-version` (MCP: `create_version`) | `projex-list-versions` (MCP: `list_versions`) | New version appears |
| `test-hub-create-testcase` (MCP: `create_testcase`) | `test-hub-get-testcase` (MCP: `get_testcase`) | Test case title and directory match. Note the flag inversion on the CLI: `--id` is the **test case** and the library goes in `--test-repo-id` (the create command uses `--id` for the library) |
| `test-hub-update-test-result` (MCP: `update_test_result`) | `test-hub-get-test-result-list` (MCP: `get_test_result_list`) | The `result` for the specified case has been updated |
| `app-stack-create-application` (MCP: `create_application`) | `app-stack-get-application` (MCP: `get_application`) | Application exists, basic attributes match |
| `app-stack-create-app-orchestration` (MCP: `create_app_orchestration`) | `app-stack-get-app-orchestration` (MCP: `get_app_orchestration`) | Orchestration exists, content matches |
| `app-stack-create-change-request` (MCP: `create_appstack_change_request`) | `app-stack-list-change-request-executions` (MCP: `list_appstack_change_request_executions`) | Change order execution record appears |
| `app-stack-execute-change-request-release-stage` (MCP: `execute_app_release_stage`) | `app-stack-list-app-release-stage-runs` (MCP: `list_app_release_stage_runs`) | New run exists, `status != FAIL` |

## Pipeline Run Verification Flow

```
1) flow-create-pipeline-run (MCP: create_pipeline_run) → obtain pipelineRunId
2) Poll flow-get-pipeline-run (MCP: get_pipeline_run) or flow-get-latest-pipeline-run (MCP: get_latest_pipeline_run)
   - Once every 10s, up to 20 times (approximately 3 minutes)
   - status = RUNNING → continue
   - status = SUCCESS → pass
   - status = FAIL/CANCELED → call flow-get-pipeline-job-run-log (MCP: get_pipeline_job_run_log) to extract failure reason
3) Output summary: duration, failed jobs, key log segments
```

## Strict Verification for Delete Operations

After deletion, must use `list_*` or `get_*` to read back:
- `get_*` returns 404 → confirm deletion succeeded
- Still returns data → report failure and investigate

## Error Read-back Example

Investigating a failed pipeline run:

```
# CLI: flow-list-pipeline-runs / MCP: list_pipeline_runs
runs = list_pipeline_runs(pipelineId, status=FAIL, perPage=1)
# CLI: flow-get-pipeline-run / MCP: get_pipeline_run
run = get_pipeline_run(pipelineId, runs[0].id)
for job in run.failedJobs:
    # CLI: flow-get-pipeline-job-run-log / MCP: get_pipeline_job_run_log
    log = get_pipeline_job_run_log(pipelineId, runs[0].id, job.id)
    output summary
```

## Idempotency & Retries

- For `create_*`: if it returns `409 Conflict/Duplicate`, switch to `get_*`/`list_*` to confirm the resource already exists
- For `update_*`: first `get_*` to retrieve the current version/fields, merge, then submit to avoid overwriting
- For `delete_*`: if it returns 404, treat as idempotent success
- Network/5xx: retry up to 3 times with exponential backoff of 1/2/4 seconds

## Known API Limitations

The following fields may not match the written value when read back, which are known limitations of the Yunxiao platform. **Skip blocking validation for these fields** and annotate them as "Platform Limitation" in the final report. Do not trigger degradation or retries because of these:

| Operation (CLI / MCP) | Affected Field | Behavior |
|----------------------|---------------|----------|
| `projex-create-workitem` (MCP: `create_work_item`) with `sprintId` | Sprint association | `projex-get-workitem` (MCP: `get_work_item`) read-back may show the sprint field as empty, but the association actually exists |
| `test-hub-create-testcase` (MCP: `create_testcase`) with `priority` | Priority | Read-back is **shape-shifted, not lost**: the write payload is a map (`{"tc.priority": "<option id>"}`) while `test-hub-get-testcase` (MCP: `get_testcase`) returns an *array* of field descriptors (`[{"fieldId":"tc.priority","values":[{"displayValue":"P1",...}]}]`). Priority does persist — assert on `values[].displayValue` instead of expecting the map back |
| `test-hub-create-testcase` (MCP: `create_testcase`) with `testSteps` | Steps / expected result | Also shape-shifted: written as `content[{step, expected}]`, returned as `stepContent` / `expectedResult` RICHTEXT strings with `content: null`. Do **not** feed the read-back shape into a subsequent create — a payload lacking `content[]` fails with `500 unknown exception` |

## Final Report Format

When reporting to the user, include:
1. CLI command or MCP tool name executed + key parameters
2. Core IDs returned (pipelineRunId / workItemId, etc.)
3. Fields that passed verification
4. Direct links (if the tool returns a web URL)
