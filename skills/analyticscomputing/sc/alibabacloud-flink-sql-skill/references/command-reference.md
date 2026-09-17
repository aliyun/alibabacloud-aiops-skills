# Unified CLI Command Reference

This is the complete command catalog for the unified CLI. See [lifecycle.md](lifecycle.md) for lifecycle ordering. The definitive parameter reference is `python3 scripts/flink_sql_manager.py <command> --help`.

## CLI Entry Point

```bash
python3 scripts/flink_sql_manager.py <command> [args...]
```

## Common Arguments

```bash
-w, --workspace <id>
-n, --namespace <name>
-r, --region_id <region>
-o, --output json|table|text
```

Scope arguments can also come from environment variables or `assets/flink-sql-manager.json`. See [configuration.md](configuration.md) for precedence.

## Configuration Gate

- `config_init`
- `config_doctor`

## Git Synchronization

- `git_init`
- `git_sync`

## SQL Development, Validation, and Deployment

### Folder

- `create_folder`
- `update_folder`
- `delete_folder`
- `get_folder`

### Draft

- `create_draft`
- `update_draft`
- `delete_draft`
- `get_draft`
- `list_drafts`
- `get_draft_lock`

### Validation and Deployment

- `validate_sql`
- `validate_draft`
- `get_validate_result`
- `deploy_draft`
- `get_deploy_result`

Notes:

- `validate_draft` and `deploy_draft` are asynchronous.
- Poll their results with `get_validate_result` and `get_deploy_result`, respectively.

## Deployments and Running Jobs

### Deployment

- `create_deployment`
- `update_deployment`
- `get_deployment`
- `list_deployments`
- `delete_deployment`
- `search_by_name`
- `search_by_label`
- `search_by_ip`
- `get_events`

### Job Lifecycle

- `start_job`
- `stop_job`
- `get_job`
- `list_jobs`
- `delete_job`
- `hot_update_job`
- `get_hot_update_result`
- `get_start_log`
- `diagnose_job`
- `get_checkpoints`

### Savepoint

- `create_savepoint`
- `get_savepoint`
- `delete_savepoint`
- `list_savepoints`

### Supporting Commands

- `generate_resource_plan`
- `get_resource_plan_result`
- `get_lineage`
- `flink_api_proxy`

## Historical Metrics

- `get_metric_dashboard`
- `get_metric_data`

Note: `generate_resource_plan` is asynchronous.

## Session Clusters (SQL Development/Test Execution Environments)

- `create_session_cluster`
- `update_session_cluster`
- `delete_session_cluster`
- `get_session_cluster`
- `list_session_clusters`
- `start_session_cluster`
- `stop_session_cluster`

## SQL Development Resources

### UDF

- `create_udf_artifact`
- `update_udf_artifact`
- `get_udf_artifacts`
- `delete_udf_artifact`
- `register_udf_function`
- `delete_udf_function`

### Custom Connectors

- `list_connectors`
- `register_connector`
- `delete_connector`

### Metadata and SQL

- `get_catalogs`
- `get_databases`
- `get_tables`
- `execute_sql`

### Engines

- `list_engine_versions`

## SQL Runtime Resources

### Variables

- `create_variable`
- `update_variable`
- `delete_variable`
- `list_variables`

### Deployment Targets

- `create_deploy_target`
- `update_deploy_target`
- `delete_deploy_target`
- `list_deploy_targets`

## Safety Baseline

- Run `config_doctor` before a cloud command.
- Read-only commands: execute directly after resolving the target scope.
- Normal mutations: append `--confirm` after the user explicitly requests the operation.
- `stop_*` and `delete_*`: valid advance confirmation in the current request satisfies the gate; otherwise restate the target and impact, wait for confirmation, then append `--confirm`.
- Read back every completed mutation with a read command.

## Complete Flows

Follow [lifecycle.md](lifecycle.md) for multi-step tasks, entering at the user's current stage.
