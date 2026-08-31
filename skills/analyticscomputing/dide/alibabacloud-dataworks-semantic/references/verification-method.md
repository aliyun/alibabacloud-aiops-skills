# Verification Method — DataWorks Semantic Analysis

Every command must use `--read-timeout 60 --connect-timeout 10`.

## Public API readiness

Run `--help` only for commands required by the selected workflow. Create/run/result workflows select the applicable commands from `create-semantic-job`, `run-semantic-job`, `list-semantic-job-runs`, and `download-semantic-results`. A stop workflow checks `kill-semantic-job` and `get-semantic-job-detail`, plus `list-semantic-job-runs` only when identifiers must be resolved. A diagnosis workflow checks `get-semantic-job-detail` and `get-semantic-job-log`. Unrelated workflows must not probe stop or diagnostic commands.

Expected: all commands exist and do not require customer-supplied `tenant-id` or `user-id`.

Failure: update the `dataworks-public` plugin once. If a core command remains absent or requires identity parameters outside the public contract, stop and report the capability gap.

## Create verification

1. List every page of semantic jobs and search for the exact requested `Name`.
2. If absent and the user confirmed the full configuration, create once.
3. Require a non-empty returned `Data.Name`; retain returned `Data.ProjectId` and configuration fields.
4. List jobs again and compare the exact name, project, resource group, source, and reference files with the requested definition.

If creation times out, repeat the list and comparison before considering another create. A matching definition proves the first call succeeded. A same-name mismatch is a conflict, not permission to replace it.

## Run verification

1. Submit once by exact `Name`.
2. Require non-empty `Data.JobRunId` and `Data.ExecutorJobId` before reporting acceptance.
3. Preserve the exact returned identifiers. List runs by `JobName` only when identifiers must be resolved or the submission response was lost; do not issue a redundant list call when both IDs were returned.
4. When waiting was requested, poll with a fixed deadline and report timeout without resubmitting.
5. Use `get-semantic-job-detail` with the exact executor and workspace identifiers for final executor state. Parse its `Data.Statuses` array with `scripts/parse_job_detail.py`; never read a guessed singular `Data.Status` field. Executor codes are `1=WAITING`, `2=RUNNING`, `3=FINISH`, `4=ERROR`, and `6=KILLED`.
6. On terminal failure, call `get-semantic-job-log` for the exact `ExecutorJobId` and `ProjectId`, return sanitized diagnostic context with the run identifiers, and stop the workflow. Do not alter the source, delete or recreate the job, submit another run, or continue to result retrieval.

If submission times out, list recent runs and compare identifiers and creation time before considering another run. Never create a second run merely because the response was lost.

## Stop verification

1. Resolve the exact requested run and keep `JobRunId` and `ExecutorJobId` distinct.
2. Query `get-semantic-job-detail` with the exact `ExecutorJobId` and `ProjectId`; if the run is already terminal, report it without issuing a kill.
3. Require an explicit request to stop this cloud run. A request to stop waiting or monitoring is not authorization to stop execution.
4. Call `kill-semantic-job` once with the exact `ExecutorJobId` and `ProjectId`.
5. Treat a successful response as acceptance only. Poll the same executor with a fixed deadline and report success only after it reaches `KILLED`.
6. If the response is lost or the deadline expires, query state and report an unconfirmed outcome instead of automatically repeating the kill.

## Result verification

1. Require the requested run to reach a successful terminal state.
2. Validate the approved output directory with `scripts/download_results.py --validate-only` before requesting any presigned URL. If validation fails, do not call `download-semantic-results`.
3. Create an owner-only temporary response file, then call `download-semantic-results` exactly once with exact `JobName` and `JobRunId`, redirecting stdout directly to that file. Never preview the response in the terminal or agent log.
4. Require every returned item to match that job and run and have an HTTPS public download URL. Use a safe `FileName` when present; otherwise derive only a safe URL path basename.
5. Write only into the validated approved directory without overwriting existing files.
6. Confirm each local file exists, is non-empty, and has the expected name before reporting success.
7. Report missing or partial artifacts explicitly; do not infer that a model exists solely from run submission.

## Common failures

| Signal | Meaning | Action |
|---|---|---|
| command not found | Installed plugin predates the semantic API | Update once, then stop if still absent |
| `Forbidden.RAM` | Missing a released semantic action | Grant only the relevant action from `ram-policies.md` |
| name conflict | A job already uses the requested name | Compare the definition; reuse only if equivalent |
| missing run or executor ID | Submission response is incomplete | Treat as unconfirmed and query runs |
| ambiguous stop target | Job or run identifiers resolve to multiple executors | Ask the user to choose; do not issue a kill |
| stop accepted but still running | Kill is asynchronous | Poll exact executor to `KILLED` or report bounded-wait timeout |
| executor code `3` | The semantic analysis finished successfully | Continue the explicitly requested lifecycle; do not retrieve failure logs or kill the terminal run |
| executor code `4` | The semantic analysis failed | Retrieve logs for the exact executor and project, return sanitized diagnostics, and stop without source changes, deletion, recreation, or another run |
| no artifacts | Results are not ready or the run produced none | Recheck exact run status; do not select another run silently |
| result job/run mismatch | Response does not match the request | Stop and preserve sanitized response context |
| unsafe file name or URL | Artifact cannot be downloaded safely | Skip it and report the rejected item without revealing URL secrets |
| model/version request | Public plugin lacks stable model APIs | Report the public OpenAPI capability boundary |
