# Lifecycle Result Reporting Templates

Read when you need a consistent report for an ordinary query/check, high-risk confirmation, SQL/Draft validation, creation, update, deployment, start, restart, stop, deletion, Git synchronization, diagnosis, failure, or unconfirmed result. These templates govern reporting only. They do not change the authorization boundaries in [execution-protocol.md](execution-protocol.md) or replace the read-back evidence required by [verification.md](verification.md).

## Usage Rules

- Preserve the template's field names, order, and required fields; do not replace it with free-form output. Omit only content explicitly marked optional or not applicable, and write “unconfirmed” for unknown items.
- Write explanatory field values in the user's language; keep command names, identifiers, and original error codes unchanged.
- Include only facts proven by CLI output, OpenAPI output, logs, or read-back results. Write “unconfirmed” when evidence is absent; do not guess a state, ID, ticket, or cause.
- The target must contain the real `workspace`, `namespace`, resource name, and ID required by the operation. Omit fields that do not apply.
- Redact commands, errors, and artifacts. Do not output AccessKey IDs, AccessKey secrets, tokens, passwords, or sensitive SQL variable values.
- When the current request contains valid advance confirmation, verify that the real target and strategy remain within its scope, skip the “Before High-Risk Operation” template, and invoke the CLI directly with `--confirm`. Otherwise, show the complete command and wait for confirmation first.
- A task may combine templates. For example, a restart without valid advance confirmation first uses “Before High-Risk Operation”; after confirmation, stop, start, and read back the Job, then use “Start / Restart Completed.”

## Ordinary Query or Check Completed

```text
Completed: <query/check action>
Target: <workspace/namespace/resource name and ID>
Result: <actual queried object or field, including its count, state, or key fields; explain any difference from the user's wording>
Evidence: <command, request ID, or response summary>
Next step: <optional; omit when none>
```

## Before High-Risk Operation

Use for `stop_*`, `delete_*`, a restart/deployment flow that includes a stop, and destructive `execute_sql` statements such as `DROP` or `TRUNCATE` when there is no valid advance confirmation.

```text
High-risk operation awaiting confirmation: <stop/delete/restart/destructive SQL>
Target: <workspace/namespace/resource name, Deployment ID, Job ID, and so on>
Current state: <read-back state; write “unconfirmed” if unavailable>
Impact: <processing interruption, state impact, resource deletion, or downstream impact>
Strategy: <stop/restore/Savepoint strategy or deletion consequence>
Command after confirmation: <complete redacted command; include --confirm when actually invoking it>
After you explicitly confirm the target, impact, and strategy above, I will execute it.
```

## High-Risk Operation Completed

```text
Completed: <stop/delete action>
Target: <workspace/namespace/resource name and ID>
Result: <terminal stop state, confirmed absence, or another state change>
Verification: <get_*/list_* read-back command and key evidence>
State retained: <Savepoint ID, state, and path; do not claim retention without evidence>
Risk handling: Obtained second confirmation/valid advance confirmation for the target above and followed the confirmed strategy
Next step: <monitor, restore, clean up, or no action required>
```

Include `State retained` only when the stop strategy involves a Savepoint. Omit it for ordinary deletion or a stateless stop.

## SQL or Draft Validation Completed

```text
Completed: <quick SQL validation/in-depth Draft validation>
Target: <workspace/namespace/Draft ID>
Result: <passed/failed/still running>
Evidence: <validation command, ticket ID, terminal state, and key diagnostics>
Conclusion: <cloud validation passed/validation failed/unconfirmed; for review by inspection only, write “static review”>
Next step: <modify SQL, continue polling, deploy, or no action required>
```

If the validation command succeeds but the SQL/Draft fails validation, still use this template to record platform diagnostics. If the CLI or OpenAPI call itself fails, use “Operation Failed or Result Unconfirmed.”

## Creation, Update, or Deployment Completed

```text
Completed: <create/update/deploy Draft, Deployment, or supporting resource>
Target: <workspace/namespace/resource name and ID>
Result: <Draft ID, Deployment ID, ticket ID, state, and so on>
Change: <summary of SQL, execution mode, engine version, deployment target, or resource configuration>
Verification: <validation/deployment terminal state and get_*/list_* read-back evidence>
Git: <not applicable/disabled/synchronized/no changes/synchronization failed; on success include commit, branch, and actual artifacts; on failure include the error>
Next step: <start, continue observing, or no action required>
```

Do not report “deployment completed” before an asynchronous ticket reaches a successful terminal state. Use the failure template instead, or explicitly report “still running/unconfirmed” and provide the next query command.

## Start / Restart Completed

```text
Completed: <start/restart action>
Target: <workspace/namespace/resource name and Deployment ID>
Job: <Job ID, expected state, and read-back state>
Restore: <restore strategy and Savepoint ID; for a stateless start write “stateless”>
Verification: <get_job command, state, request ID, and other evidence>
Checkpoint: <include only when requested, required by the flow, or already queried; list completed/failed/in-progress facts>
Conclusion: <start succeeded/restart succeeded/request accepted but runtime state unconfirmed/failed>
Next step: <continue polling, diagnose Checkpoints/startup, or no action required>
```

Determine success from the Job-state read-back rules in [verification.md](verification.md). Do not automatically apply another skill's “first completed Checkpoint” condition to every streaming or batch job. Report “start succeeded” or “restart succeeded” only after read-back reaches the expected runtime state. With only a start response and no Job read-back, report “start request accepted; runtime state unconfirmed.” When the task separately requires Checkpoint validation, report actual Checkpoint evidence; `RUNNING` does not satisfy that item.

## Diagnosis Result

```text
Completed: Diagnosis
Target: <workspace/namespace/Deployment ID/Job ID>
Evidence: <Job state, startup logs, events, platform diagnosis, Checkpoints, and Flink REST summary>
Confirmed facts: <phenomena directly proven by APIs, Metrics, or logs>
Assessment: <most likely cause; label anything not directly proven as “hypothesis”>
Impact: <effect on Sources, operators, Sinks, state, or data freshness>
Recommended actions: <safe actions and verification methods in priority order>
```

A diagnosis request is read-only. Unless the user separately requests and authorizes it, do not claim in the diagnosis report that a configuration was changed or a Job was restarted or stopped.

## Git Synchronization

Use for manual synchronization and for automatic synchronization after directly creating, updating, or deleting a Deployment.

```text
Git synchronization: <automatic/manual>
Target: <workspace/namespace/all Deployments or specified resource name and ID>
Platform result: <creation/update/deletion result; omit for a purely manual synchronization>
State: <succeeded/no changes/failed>
Commit: <commit ID, commit message, and branch; write “no new commit” when none>
Artifacts: <actual repository paths; for deletion, the removed directory>
Push: <remote updated/content already consistent, no push required/push failed/unconfirmed>
Next step: <CR, retry after repairing Git, roll back, or no action required>
```

If automatic synchronization fails, preserve `Platform result` according to platform read-back evidence. Do not describe the entire operation as a platform failure or claim that the platform rolled back. Use this template to state “platform mutation succeeded; Git synchronization failed” and provide a safe retry.

## Operation Failed or Result Unconfirmed

```text
Failed stage: <configuration check/validation/deployment/start/Checkpoint/stop/delete/read-back/Git synchronization>
Target: <workspace/namespace/resource name and ID>
Error: <operation, error code, key message, request ID>
Evidence: <command, ticket/state, and key response summary>
Completed: <steps already confirmed by evidence>
Not executed: <dependent steps skipped because of the failure>
Next step: <one safe query or recovery command that can be run directly>
```

Use this template for timeouts, asynchronous tickets that have not reached a terminal state, and read-back results that differ from expectations. In those cases, title it “Result Unconfirmed” and do not describe the outcome as either a successful or failed terminal state.
