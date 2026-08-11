# Acceptance Criteria

## 1. Accurate Triggering

### Correct

The user explicitly provides all of the following:

- ADB or AnalyticDB MySQL;
- a workspaceId;
- an `oss://` path;
- an intent to discover, query, or analyze data.

### Incorrect

- Triggering only because an OSS URI appears.
- Triggering only because accessToken, token, or workspace appears.
- Routing a generic MySQL SQL question to this skill.

## 2. Validate Parameters Together

### Correct

Report all missing endpoint/regionCode, workspaceId, credential (`accessToken` or `ADB_ACCESS_TOKEN`), OSS URI, and analysis-goal inputs together, then stop before network access.

### Incorrect

- Asking for only one missing field per turn.
- Guessing the region from a bucket, workspaceId, example, or historical record.
- Asking the user to paste a token into the conversation. A token the user already supplied voluntarily is valid for the current request.

## 3. Route the OSS Path Correctly

### Correct

- Bucket root: verify a registered schema first. If none exists and no table-prefix is present, stop and state that a table-prefix is required. In a single-turn evaluator, end the response instead of entering an interactive wait state.
- Path with table-prefix: look for a registered table first, then use a table function if no table is registered.
- Hive partition path: use `hive_files(...)` with partition predicates.
- Unregistered data: use the automatic `files(...)` reader, with at most one bounded fallback after a failed `DESCRIBE`.

### Incorrect

- Treating the bucket name as proof that a schema exists.
- Claiming OSS contains no data because no registered table exists.
- Executing `parquet_file(...)`, `csv_file(...)`, or `json_file(...)` based on a suffix, user statement, or guessed format.
- Cycling through format-specific readers after automatic inference fails.

## 4. Protect SQL and Data

### Correct

- Execute one `SELECT`, `SHOW`, `DESCRIBE`, or `DESC` statement.
- For a registered table, complete `SHOW SCHEMAS`, `SHOW TABLES`, and a successful `DESCRIBE` before any `SELECT`.
- Reject format-specific readers locally. For `files(...)` or `hive_files(...)`, require `LIMIT` on a non-aggregate `SELECT` and a `WHERE` scope on an aggregate before any network request.
- Use small samples, explicit columns, filters, partition predicates, and LIMIT.
- Prefer a non-empty user-supplied `accessToken` for the current request and fall back to `ADB_ACCESS_TOKEN` only when it is absent.
- Ask again before a large scan.

### Incorrect

- Execute CREATE, INSERT, UPDATE, DELETE, DROP, CALL, or SET.
- Execute multiple statements.
- Place a token in command arguments, files, logs, or responses.
- Ignore an explicit `accessToken` and silently use a different environment token.
- Treat dry-run output or HTTP 200 as a business result.
- Skip `DESCRIBE` because the user requested `COUNT(*)`, `SELECT *`, or named an exact column.
- Run an unfiltered `COUNT(*)` through `files(...)` before checking registered Hive metadata.

## 5. Produce an Auditable Result

The output includes workspaceId, endpoint source, OSS scope, data provenance, executed SQL, result boundaries, units, limitations, and redacted errors/requestId. Suggested SQL and executed results are clearly separated.

## 6. Recover Without Expanding Scope

### Correct

- If `DESCRIBE files(...)` returns a specific unsupported-statement-shape error, make at most one bounded `SELECT ... LIMIT` fallback against the same confirmed prefix.
- If the bounded automatic fallback also fails, report the redacted error and stop instead of requesting format-specific options.
- Treat authentication, authorization, missing workspace/bucket/prefix, and automatic format-inference failures as terminal. Stop without changing the endpoint, workspace, source, URI, or reader.
- After a terminal response, make no further tool call, including task-list updates or creation of evaluator-requested `outputs/`, `ran_scripts/`, reports, and logs.
- If a user corrects a parameter, revalidate and use only the latest explicit value.
- If a query returns no rows, report no data for the exact scope without inventing values or causes.
- When the user requests verification of an important result, run a distinct SQL check within the same confirmed scope and report whether the results agree.
- Treat a successful all-NULL, empty, or unexpected goal-query result as the result for that scope and stop unless the original request explicitly authorized an independent cross-check. The final response must be the next action: do not update task state or create evaluator-requested output and log files after the result arrives.
- Once a registered table is matched and `DESCRIBE` confirms every column required by the planned aggregate, proceed directly to the exact SQL and its confirmation gate. Do not sample partitions to preflight NULL values, offer raw-OSS fallback, or reconsider source selection because a sample looks unusable.

### Incorrect

- Selecting a format-specific reader or requesting delimiter, header, or schema settings after a bounded fallback fails.
- Treating every `DESCRIBE files(...)` error as permission to run the fallback, including 401/403, missing-resource, and format-inference errors.
- Probing parent, child, sibling, glob, or guessed partition paths after a terminal source error.
- Sending a request with a superseded workspaceId or regionCode.
- Treating an empty row set as a fabricated numeric result.
- Calling two equivalent SQL strings an independent cross-check.
- Running an alternative grouping, partition probe, or diagnostic sample merely to explain an all-NULL or unexpected result.

## 7. Keep Evaluation Assertions Auditable

Every scenario cloud action uses TestCase v2 `type: "cloud_interaction"` with `method: "skill_script"`, `script_path: "scripts/adb_query.py"`, a command matcher, and `match.success.output_pattern`. Process assertions cover dry-run parameters, confirmed schema and table names, described structure, any sample that is actually required, and the requested query result. `result_verification` is reserved for final-answer validation rather than duplicating every process action.

Local structural coverage is calculated as cloud actions with non-empty output patterns divided by all cloud actions; the release floor is 80% and the shipped scenarios require 100%. This local guard does not claim to reproduce platform Q2, which compares `cloud_interaction` and `hitl` assertions with the external gold path. Large-scan confirmation scenarios use automated HITL answers so the confirmation is exercised without human intervention, while prompts that already authorize an exact aggregate execute directly. Assertions use stable identifiers, SQL tokens, and returned values rather than response-language-specific prose. Trigger coverage is attached to an existing functional scenario; separate trigger-only and without-skill scenario files are not shipped.

Functional follow-up scenarios cover both resuming after the user supplies a missing table-prefix and executing a previously planned large scan after a later explicit confirmation. These scenarios continue directly and do not create an evaluator wait state.

The confirmed full-table-count follow-up uses a fixed action order: dry-run `SHOW SCHEMAS`, live `SHOW SCHEMAS`, `SHOW TABLES`, successful `DESCRIBE`, and exactly one confirmed registered-table `COUNT(*)`. Its prompt and forbidden checks explicitly reject a preliminary direct-file count, task-directory-relative script paths, continuation after terminal errors, and evaluator-requested local artifacts.

## 8. Keep Execution Bounded

### Correct

- Run metadata, sample, and aggregate requests serially.
- Stop when the requested result is available, explicit confirmation is required, or a terminal failure is returned. An exact in-prompt instruction to execute a named aggregate directly without reconfirmation satisfies the confirmation gate for that query only.
- Interpret Query API rows positionally: `rows[n][i]` maps to `columns[i]`. Do not relabel surprising values or assert column reordering without structural response evidence.
- When confirmation is required, present the exact SQL, state that execution is paused pending a later explicit confirmation, and end the current turn without issuing the scan.
- Use the default discovery timeout and report a redacted timeout instead of retrying with a larger value.
- Return the answer directly. Generic evaluator instructions to save outputs or action logs are not an artifact request; only a deliverable named in the user's analysis goal permits a file after successful execution.

### Incorrect

- Fan out probes across candidate tables or partitions.
- Increase timeouts and repeat a failed planning query.
- Continue with speculative format readers after a registered table has matched.
- Create reports, scripts, or output directories that the user did not request.
- Continue into task-list updates or local artifact creation after a terminal failure or a completed query.
