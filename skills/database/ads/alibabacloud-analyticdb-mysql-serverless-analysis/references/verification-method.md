# Verification Method

## Static Checks

```bash
python3 -m py_compile scripts/adb_query.py
python3 -m unittest discover -s tests -v
```

Success criteria:

- Python syntax validation passes.
- All unit tests pass.
- The skill frontmatter contains the correct name.
- Every local file referenced by SKILL.md exists.
- SKILL.md is no longer than 500 lines.
- A non-empty explicit `accessToken` overrides `ADB_ACCESS_TOKEN`, while an absent explicit token falls back to the environment.
- Every cloud action uses TestCase v2 `type: "cloud_interaction"`, `method: "skill_script"`, and the relative `scripts/adb_query.py` path.
- Every cloud action includes a command matcher and `match.success.output_pattern`; local cloud-output assertion coverage is at least 80%, while platform Q2 coverage is calculated independently against the generated gold path.
- Process evidence stays in `expectations`; `result_verification` contains only final-answer checks for the requested analysis outcome.
- Every scenario has a human-readable description, and every dry-run is represented as a Skill-script interaction.
- Registered-table scenarios require a successful `DESCRIBE` before any `SELECT`, while exact aggregate scenarios do not require a process-only sample.
- Format-specific `parquet_file(...)`, `csv_file(...)`, and `json_file(...)` readers are prohibited by the skill and absent from scenario expectations.
- Trigger coverage reuses a functional scenario; the directory contains no separate trigger-only or without-skill scenarios.
- The fallback, independent cross-check, missing-schema, corrected-parameter, and empty-result branches are represented by functional scenarios.
- Follow-up handling is covered when the user supplies a previously missing table-prefix and when the user later confirms an exact large-scan plan.
- Large-scan confirmation scenarios use top-level automated `hitl` answers plus a referenced `expectations[].type: "hitl"` assertion, so they cover the confirmation action without waiting for a human. The explicit follow-up confirmation scenario executes without asking again.
- Generic evaluator requests for `outputs/`, `ran_scripts/`, or action logs do not override the terminal no-more-tools rule.

## Dry Run

A dry run does not require `ADB_ACCESS_TOKEN` and does not access the network:

```bash
env -u ADB_ACCESS_TOKEN SKILL_SESSION_ID={session-id} python3 scripts/adb_query.py \
  --region-code cn-beijing \
  --workspace-id ws-demo \
  --dry-run <<'SQL'
SHOW SCHEMAS FROM hive
SQL
```

Success criteria:

- The URL is `https://serverless.cn-beijing.ads.aliyuncs.com/workspace/ws-demo/v1/query`.
- The JSON request body contains only SQL and does not contain Authorization or a token.
- The output explicitly contains `dryRun: true`.

## Read-Only Boundary

The following commands must fail without a network request:

```bash
SKILL_SESSION_ID={session-id} python3 scripts/adb_query.py \
  --region-code cn-beijing \
  --workspace-id ws-demo \
  --dry-run <<'SQL'
DROP TABLE hive.default.example
SQL
```

```bash
SKILL_SESSION_ID={session-id} python3 scripts/adb_query.py \
  --region-code cn-beijing \
  --workspace-id ws-demo \
  --dry-run <<'SQL'
SHOW SCHEMAS FROM hive; SHOW TABLES FROM hive.default
SQL
```

## Live Request

Run a live request only after the user confirms endpoint/regionCode, workspaceId, OSS path, and analysis goal and either supplies an `accessToken` for this request or configures `ADB_ACCESS_TOKEN`. Start with `SHOW SCHEMAS FROM hive`, then progress through bounded queries.

Do not judge success from HTTP status alone. Confirm that the SQL has no server-side error, the response contains interpretable data, and the data is sufficient to answer the analysis goal.

For failure-path verification, confirm that 401/403, invalid-token, access-denied, missing workspace/bucket/prefix, and automatic format-inference errors end the workflow immediately. The agent must not make another tool call, change paths, sources, endpoints, workspaces, or readers, update a task list, or create evaluator-requested outputs/logs after those terminal responses. Only a specific unsupported `DESCRIBE files(...)` statement-shape error allows one bounded same-prefix fallback.
