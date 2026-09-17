# Lifecycle Verification

Read after any creation, update, deployment, start, stop, or deletion. An API success response means only that the request was accepted; independent evidence must confirm the actual resource state.

The commands below omit common scope arguments, which come from `assets/flink-sql-manager.json`, environment variables, or `-w/-n/-r`.

## General Rules

1. Record real resource IDs, ticket IDs, Job IDs, and request IDs from mutation responses.
2. Poll asynchronous operations with the dedicated result command; do not infer success after a fixed sleep.
3. On read-back, verify the ID, name, namespace, state, and key fields changed by the operation.
4. A timeout is neither success nor a failed terminal state. Report “still running/unconfirmed” and preserve the next query command.
5. If read-back differs from expectations, stop dependent steps and resolve the consistency issue first.

## Git Synchronization

1. Read back the platform resource according to its section below, then inspect the returned `git_sync` result.
2. For `changed: true`, verify the target branch, commit, actual artifacts, and push. Local files or a local commit alone do not prove that the remote was updated. For deletion, verify that the directory was removed.
3. `changed: false` means the content already matches and no new commit or push is needed; it is not a failure. For a manual full synchronization, also verify the actual number of synchronized resources.
4. On Git failure, retain the successful platform fact and retry manually after repairing the repository or credentials.

## SQL and Draft Validation

Quick validation:

```bash
python3 scripts/flink_sql_manager.py validate_sql --statement '<complete-sql>'
```

In-depth Draft validation is asynchronous:

```bash
python3 scripts/flink_sql_manager.py validate_draft --draft_id <draft-id>
python3 scripts/flink_sql_manager.py get_validate_result --ticket_id <ticket-id>
```

Proceed to deployment only after the result explicitly succeeds with no blocking diagnostics. Reviewing SQL by inspection does not replace platform validation.

## Draft Creation and Update

```bash
python3 scripts/flink_sql_manager.py get_draft --draft_id <draft-id>
```

Verify the Draft name, SQL summary, execution mode, engine version, and update time. Preserve a before/after baseline to avoid deploying the wrong version later.

## Draft Deployment

```bash
python3 scripts/flink_sql_manager.py deploy_draft \
  --draft_id <draft-id> --deployment_target <target> --confirm
python3 scripts/flink_sql_manager.py get_deploy_result --ticket_id <ticket-id>
python3 scripts/flink_sql_manager.py get_deployment --deployment_id <deployment-id>
```

Verify that the deployment ticket reaches a successful terminal state and that the Deployment points to the expected Draft/version and deployment target. Never start after a failed ticket.

## Starting a Job

```bash
python3 scripts/flink_sql_manager.py get_job \
  --deployment_id <deployment-id> --job_id <job-id>
```

The start result must confirm that:

- The Job reached the expected runtime state.
- The Job did not enter `FAILED`, `CANCELED/CANCELLED`, or another failed terminal state.

## Stopping a Job

Record the current Job state before stopping it. After obtaining explicit confirmation, including valid advance confirmation, execute the stop and read back the Job:

```bash
python3 scripts/flink_sql_manager.py stop_job \
  --deployment_id <deployment-id> --job_id <job-id> \
  --stop_strategy <strategy> --confirm
python3 scripts/flink_sql_manager.py get_job \
  --deployment_id <deployment-id> --job_id <job-id>
```

Confirm the terminal stop state reported by the platform. When state retention was requested, query the corresponding Savepoint. Do not claim that state was retained without Savepoint evidence.

## Savepoints

```bash
python3 scripts/flink_sql_manager.py get_savepoint --savepoint_id <savepoint-id>
python3 scripts/flink_sql_manager.py list_savepoints --deployment_id <deployment-id>
```

Verify the state, path, creation time, and owning Deployment. An accepted Create Savepoint request does not mean the snapshot completed.

## Session Clusters

```bash
python3 scripts/flink_sql_manager.py get_session_cluster --cluster_name <cluster-name>
python3 scripts/flink_sql_manager.py list_session_clusters
```

After creation or update, verify the resource configuration. After start or stop, poll the state. After deletion, confirm that neither the list nor the get result shows the target. A Session Cluster is only a shared SQL development/test execution environment; do not expand it into general Workspace management.

## Catalogs, Tables, Variables, and Extension Resources

```bash
python3 scripts/flink_sql_manager.py get_catalogs --catalog_name <catalog>
python3 scripts/flink_sql_manager.py get_databases \
  --catalog_name <catalog> --database_name <database>
python3 scripts/flink_sql_manager.py get_tables \
  --catalog_name <catalog> --database_name <database> --table_name <table>
python3 scripts/flink_sql_manager.py list_variables
python3 scripts/flink_sql_manager.py list_connectors
python3 scripts/flink_sql_manager.py get_udf_artifacts
python3 scripts/flink_sql_manager.py list_deploy_targets
```

Read back each target with its list/get command after a mutation. Before deleting a variable, Connector, UDF, or Deployment Target, verify that no Draft or Deployment references it. Revalidate affected SQL after successful deletion.

## Failure Reporting

Use the “Operation Failed or Result Unconfirmed” template in [output-schemas.md](output-schemas.md), preserving the command, state, ticket/request ID, and key error. An asynchronous timeout or read-back mismatch is “unconfirmed”; do not classify it as a successful or failed terminal state.
