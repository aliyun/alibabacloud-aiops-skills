# Full Flink SQL Lifecycle Workflow

Read when the user wants to complete one or more consecutive steps among SQL solution design, development, validation, deployment, start/stop, changes, performance assessment, and troubleshooting from natural language.

All stages connect through one continuous workflow:

```text
Requirements and data contract → SQL authoring and static review → Configuration check and cloud validation → Draft and Deployment
→ Start and acceptance → Operations and changes → Performance assessment and troubleshooting
```

The user can enter at any stage. After completing the current stage, execute only the later stages required to achieve the goal; do not expand the mutation scope.

## Command Usage Principles

This document describes stage goals, essential ordering, and stopping conditions. Commands mentioned here are recommendations rather than a complete capability catalog. Discover other commands in [command-reference.md](command-reference.md), and obtain exact parameters from `python3 scripts/flink_sql_manager.py <command> --help`.

## 1. Requirements and Data Contract

Define the computation goal and input/output contracts as the basis for development, deployment, and acceptance.

Recommended flow:

1. Confirm Sources, Sinks, schemas, primary keys, data formats, and Connectors.
2. Define streaming/batch mode, time semantics, update semantics, state retention, and recovery requirements.
3. Establish throughput, latency, consistency, fault-tolerance, and data-quality goals.
4. Confirm the target engine version, deployment target, network, permissions, and other constraints.

## 2. SQL Authoring and Static Review

Translate the data contract into complete SQL and check computation semantics, configuration, and version compatibility.

Recommended flow:

1. Enter the applicable topic through [sql/README.md](sql/README.md). Consult official documentation for current options or support scope.
2. Write complete DDL + DML, preserving required `SET` statements, table definitions, and `INSERT INTO` statements, with semicolons between statements.
3. Check Source/Sink types, primary keys, and update semantics. Declare primary keys with `NOT ENFORCED` and meet Connector requirements.
4. Check time fields, Watermarks, and state boundaries and TTLs for Joins, aggregations, and deduplication. Define Watermarks on input tables that require event-time processing.
5. Check required Connector options, authentication variables, network access, formats, startup offsets, and engine compatibility.

Without platform validation evidence, report only a static review and do not claim that cloud validation passed.

## 3. Configuration Check and Cloud Validation

Confirm the target environment, identity, and metadata, then validate the SQL in the actual cloud environment.

Recommended flow:

1. Use `config_doctor` to check the scope and credentials. If missing, initialize with `config_init` and run the check again.
2. Use `get_catalogs`, `get_databases`, and `get_tables` as needed to confirm metadata.
3. Use `validate_sql` to validate the complete SQL.

If `validate_sql` fails, return to stage 2, correct the SQL according to the line/column, type, function, Connector, or permission error returned by the platform, and validate again. Do not deploy after a failed result.

## 4. Draft and Deployment

Maintain editable Drafts and their deployed versions while keeping `Draft → Deployment → Job` consistent.

Recommended flow:

1. Use `create_draft` for a new job. For an existing Draft, read it back with `get_draft` before using `update_draft` as needed.
2. Complete in-depth validation with `validate_draft` and `get_validate_result`.
3. After validation succeeds, deploy with `deploy_draft` and `get_deploy_result`.
4. Read back the Deployment with `get_deployment`; use `git_sync` only when artifacts should be retained.

Continue polling until an asynchronous result reaches a terminal state. Stop on failure and do not enter the start stage.

## 5. Start and Acceptance

Start the job with the required restore behavior and verify its runtime state and the acceptance goals of the current task.

Recommended flow:

1. Use `list_jobs` and `get_job` to check for conflicting instances and establish a baseline.
2. Start the job with `start_job` using the required restore behavior.
3. Obtain the new Job ID from the response or `list_jobs`, then read back its runtime state with `get_job`.
4. Verify output, Checkpoints, or other acceptance goals requested by the user. Enter stage 7 when startup fails, performance misses the target, or the state is abnormal.

A Checkpoint does not replace reading back the current Job state. An acceptance item that was not executed cannot be marked as passed.

## 6. Operations and Changes

Manage running instances, state, and supporting resources while controlling change impact and verifying the final state.

Recommended flow:

1. Read back the applicable Draft, Deployment, Job, or supporting resource, and confirm its state, references, and impact scope.
2. Define the change, state retention, and restore strategy. Confirm stop, delete, restart, and other operations according to the safety gate.
3. To update a running job, update the Draft and validate it again; retain state and stop as needed, deploy, wait for the terminal result, and restore the Job. Do not update only the Deployment and leave a stale Draft behind.
4. For stop-only or delete-only requests, read back the terminal state, resource existence, and required Savepoint evidence after the operation; do not restart automatically.
5. Manage Session Clusters, variables, Catalogs, tables, Connectors, UDFs, and Deployment Targets as needed. Check references before a mutation and verify affected resources afterward.
6. Read back every mutation with the applicable `get_*` or `list_*` command. When Git is configured, synchronize applicable Deployment changes according to [git-sync.md](git-sync.md).

## 7. Performance Assessment and Troubleshooting

Evaluate job behavior, use evidence to identify bottlenecks or failures, and recommend optimization or recovery actions.

Recommended flow:

1. Read [diagnosis/README.md](diagnosis/README.md), then select data queries, performance knowledge, or diagnosis of an actual job based on the user's goal.
2. Follow the entry workflow to confirm the scope, collect evidence, and validate causes. Query only the data required for the current objective.
3. Form the assessment, confirmed facts, and hypotheses requiring validation. Enter the corresponding change stage only when the user asks to implement a recommendation; do not modify the job automatically.
