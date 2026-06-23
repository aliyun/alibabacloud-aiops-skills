# Success Verification Methods

After each MCP write operation completes, use query tools to read back the target resource and assert key fields to determine whether the operation actually took effect.

## General Verification Patterns

| Write Operation | Read-back Tool | Verification Fields |
|----------------|----------------|---------------------|
| `create_pipeline_from_description` | `get_pipeline` | `id` exists, `name` matches |
| `update_pipeline` | `get_pipeline` | Changed fields match input parameters |
| `create_pipeline_run` | `get_latest_pipeline_run` | `status ∈ {INIT, RUNNING, SUCCESS}`, not `FAIL/CANCELED` |
| `execute_pipeline_job_run` | `get_pipeline_job_run_log` | Log contains latest output |
| `create_branch` | `get_branch` | Target `name` exists, `commit.id` matches source branch or is a new commit |
| `delete_branch` | `list_branches` | Target branch is not in the returned list |
| `create_file` / `update_file` | `get_file_blobs` | Content matches expected value |
| `create_change_request` | `get_change_request` | `state == OPENED`, `sourceBranch/targetBranch` match |
| `create_change_request_comment` | `list_change_request_comments` | New comment appears in the list |
| `create_sprint` | `get_sprint` | Date range and name match |
| `update_sprint` | `get_sprint` | Changed fields have taken effect |
| `create_work_item` | `get_work_item` | `subject` matches, `workitemTypeId` is correct |
| `update_work_item` | `get_work_item` | Changed fields have taken effect |
| `create_version` | `list_versions` | New version appears |
| `create_testcase` | `get_testcase` | Test case title and directory match |
| `update_test_result` | `get_test_result_list` | The `result` for the specified case has been updated |
| `create_application` | `get_application` | Application exists, basic attributes match |
| `create_app_orchestration` | `get_app_orchestration` | Orchestration exists, content matches |
| `create_appstack_change_request` | `list_appstack_change_request_executions` | Change order execution record appears |
| `execute_app_release_stage` | `list_app_release_stage_runs` | New run exists, `status != FAIL` |

## Pipeline Run Verification Flow

```
1) create_pipeline_run → obtain pipelineRunId
2) Poll get_pipeline_run (or get_latest_pipeline_run)
   - Once every 10s, up to 20 times (approximately 3 minutes)
   - status = RUNNING → continue
   - status = SUCCESS → pass
   - status = FAIL/CANCELED → call get_pipeline_job_run_log to extract failure reason
3) Output summary: duration, failed jobs, key log segments
```

## Strict Verification for Delete Operations

After deletion, must use `list_*` or `get_*` to read back:
- `get_*` returns 404 → confirm deletion succeeded
- Still returns data → report failure and investigate

## Error Read-back Example

Investigating a failed pipeline run:

```
runs = list_pipeline_runs(pipelineId, status=FAIL, perPage=1)
run = get_pipeline_run(pipelineId, runs[0].id)
for job in run.failedJobs:
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

| Operation | Affected Field | Behavior |
|-----------|---------------|----------|
| `create_work_item` with `sprintId` | Sprint association | `get_work_item` read-back may show the sprint field as empty, but the association actually exists |
| `create_testcase` with `priority` | Priority | `get_testcase` read-back may show `customFieldValues` as an empty array, with priority not persisted |

## Final Report Format

When reporting to the user, include:
1. MCP tool name executed + key parameters
2. Core IDs returned (pipelineRunId / workItemId, etc.)
3. Fields that passed verification
4. Direct links (if the tool returns a web URL)
