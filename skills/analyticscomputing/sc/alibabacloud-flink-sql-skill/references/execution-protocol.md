# Unified Execution Protocol

This document governs how an agent connects SQL design, development, and cloud operations into one lifecycle. The entry point is always:

```bash
python3 scripts/flink_sql_manager.py <command> [args...]
```

## 1. Enter at the Current Stage

First determine whether the user is currently at requirements design, SQL authoring, validation, drafting, deployment, runtime, change, or troubleshooting, then continue through [lifecycle.md](lifecycle.md). SQL references and platform commands are both parts of this workflow.

Read only the references required for the current stage. When the latest version, online support scope, or current Connector options matter, consult official online documentation and state the query date; do not present an offline snapshot as current fact.

## 2. Real-Resource Gate

Run `config_doctor` before any Ververica OpenAPI command. If the scope is incomplete, initialize it according to [configuration.md](configuration.md) and run the check again. For historical Metrics, follow [job-observability.md](diagnosis/job-observability.md) to check the scope and Cookie. When a Draft ID, Deployment ID, or Job ID is missing, obtain it from user-provided information or a read-only listing. Never call an API with placeholders such as `w-xxx`, `d-xxx`, or `j-xxx`.

Automatic Git post-processing follows only an authorized and successful Deployment mutation; it does not authorize the platform mutation. See [git-sync.md](git-sync.md) for details.

Stop immediately at a failed command, explain the error, and use a recovery that matches the error category. Do not execute dependent steps or fabricate IDs, tickets, or states.

## 3. Risk Levels

- Read-only: `list_*`, `get_*`, `search_*`, `diagnose_job`, and `validate_sql`. Execute directly when the scope is clear and the doctor check succeeds.
- Normal mutation: `create_*`, `update_*`, `deploy_*`, `start_*`, `register_*`, `execute_sql`, `git_init`, and `git_sync`. An explicit request to perform the operation is authorization; append `--confirm` to the CLI call. Do not execute when the user asks only for options.
- High risk: `stop_*`, `delete_*`, and any deployment or restart flow that first stops a running job. If the current request explicitly provides advance confirmation and the resolved target and strategy match the confirmed scope, invoke the CLI directly with `--confirm`. Otherwise, use the high-risk confirmation template in [output-schemas.md](output-schemas.md), restate the target, impact, and strategy, and wait for confirmation.

Do not reuse confirmation from another request, resource, or strategy. Stopping a streaming job interrupts processing, and deletion may not be directly recoverable.

## 4. Verification After a Mutation

HTTP 200 alone does not prove acceptance: a response body with `success: false` is a business failure. After a successful API response, read back every mutation with the applicable `get_*` or `list_*` command:

- Asynchronous operations such as Draft validation and deployment: retain the ticket ID and poll the result command until a terminal state.
- Start: read back with `get_job` and confirm the expected runtime state.
- Stop: use `get_job` to confirm `CANCELLED`, `FINISHED`, or the terminal stop state reported by the platform.
- Create, update, and delete: read back the object or list and verify its ID, name, and key fields.
- Deployment mutations with Git synchronization enabled: verify platform and Git results independently according to [verification.md](verification.md); a Git failure does not override the platform result.

## 5. Verifying SQL Conclusions

When designing SQL, check the Source/Sink schemas, primary keys, time attributes, Watermarks, state, and Connector options. After the user provides an accessible workspace, use `validate_sql` for platform syntax and compatibility validation. If no platform validation was run, describe the conclusion as a static review; do not claim that cloud validation passed.

## 6. Reporting Format

Before reporting, read [output-schemas.md](output-schemas.md) for the applicable scenario:

- Use the general query template for ordinary queries.
- Use the before-confirmation and completion templates for high-risk operations.
- Use the dedicated templates for SQL/Draft validation, creation/update/deployment, start/restart, and diagnosis.
- Use the Git template for automatic or manual Git synchronization; for a platform mutation, report the platform and Git results together.
- Use the failure/unconfirmed template when a command fails, an asynchronous result times out, or the state cannot be read back.

Templates organize only facts already obtained; they do not replace read-back verification. Never present an accepted request, partial completion, or unconfirmed state as complete success, and never report success for a capability unsupported by the current CLI.
