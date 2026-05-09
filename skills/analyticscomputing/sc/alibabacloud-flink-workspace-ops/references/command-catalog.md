# Command Catalog

Full command inventory for uncommon or detailed command lookup.

## CLI Entry

```bash
python scripts/flink_ververica_ops.py <subcommand> [args...]
```

## Common Arguments

```bash
-w, --workspace <id>
-n, --namespace <name>
-r, --region_id <region>
-o, --output json|table|text
```

## W1: SQL Development and Deployment

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

### Validation and Deploy
- `validate_sql`
- `validate_draft`
- `get_validate_result`
- `deploy_draft`
- `get_deploy_result`

Notes:
- `validate_draft` and `deploy_draft` are async.
- Poll with `get_validate_result` and `get_deploy_result`.

## W2: Job Operations

### Deployment
- `create_deployment`
- `update_deployment`
- `get_deployment`
- `list_deployments`
- `delete_deployment`
- `search_by_name`
- `search_by_label`
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

### Savepoints
- `create_savepoint`
- `get_savepoint`
- `delete_savepoint`
- `list_savepoints`

### Auxiliary
- `generate_resource_plan`
- `get_resource_plan_result`
- `get_lineage`
- `flink_api_proxy`

Notes:
- `start_job` uses `--restore_strategy` (`LATEST` or `NONE`) in relevant flows.
- `generate_resource_plan` is async.

## W3: Session Clusters

- `create_session_cluster`
- `update_session_cluster`
- `delete_session_cluster`
- `get_session_cluster`
- `list_session_clusters`
- `start_session_cluster`
- `stop_session_cluster`

## W4: Dev Resources

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

### Engine
- `list_engine_versions`

## W5: Workspace Administration

### Members
- `create_member`
- `update_member`
- `delete_member`
- `get_member`
- `list_members`

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

- Read commands: run directly.
- Mutating commands: explicit user approval + `--confirm`.
- Destructive commands (`delete_*`): explicit delete confirmation + `--confirm`.

## Playbooks (Procedural Flows)

For multi-step execution flows, return to the `Resources` section in `SKILL.md` and load the required playbook on demand.
