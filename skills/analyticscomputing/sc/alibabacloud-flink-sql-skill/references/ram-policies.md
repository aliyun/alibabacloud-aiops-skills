# RAM Policies and Sensitive Information

## SQL Variables and Credentials

- Never write AccessKey IDs, AccessKey secrets, passwords, OAuth tokens, or STS tokens directly in SQL, commands, logs, or conversations.
- Store secrets required by SQL in the platform's variable/secret facility and reference them as `${var_name}`.
- Verify the scope before creating or updating a variable; check Draft and Deployment references before deleting one.
- The CLI uses the Alibaba Cloud SDK default credential chain and the machine's Git credential mechanisms. Local configuration stores only the resource scope and optional repository location, never cloud or Git credentials.

```sql
CREATE TEMPORARY TABLE mysql_source (...) WITH (
  'username' = '${db_user}',
  'password' = '${db_password}'
);
```

## RAM Permissions

The following Alibaba Cloud RAM (Resource Access Management) permissions are required by `scripts/flink_sql_manager.py`.

> Note: Official Ververica OpenAPI 2022-07-18 action names use the `stream:*` namespace.

---

## Required Permissions

These actions cover every command implemented by this skill:

### SQL Development
- `stream:CreateFolder` - create_folder
- `stream:UpdateFolder` - update_folder
- `stream:DeleteFolder` - delete_folder
- `stream:GetFolder` - get_folder
- `stream:CreateDeploymentDraft` - create_draft
- `stream:UpdateDeploymentDraft` - update_draft
- `stream:DeleteDeploymentDraft` - delete_draft
- `stream:GetDeploymentDraft` - get_draft
- `stream:ListDeploymentDrafts` - list_drafts
- `stream:GetDeploymentDraftLock` - get_draft_lock
- `stream:ValidateDeploymentDraftAsync` - validate_draft
- `stream:GetValidateDeploymentDraftResult` - get_validation_result
- `stream:ValidateSqlStatement` - validate_sql
- `stream:DeployDeploymentDraftAsync` - deploy_draft
- `stream:GetDeployDeploymentDraftResult` - get_deploy_result

### Job Operations
- `stream:CreateDeployment` - create_deployment
- `stream:UpdateDeployment` - update_deployment
- `stream:GetDeployment` - get_deployment
- `stream:ListDeployments` - list_deployments
- `stream:DeleteDeployment` - delete_deployment
- `stream:GetDeploymentsByName` - get_deployments_by_name
- `stream:GetDeploymentsByLabel` - get_deployments_by_label
- `stream:GetEvents` - get_events
- `stream:StartJobWithParams` - start_job
- `stream:StopJob` - stop_job
- `stream:GetJob` - get_job
- `stream:ListJobs` - list_jobs
- `stream:DeleteJob` - delete_job
- `stream:HotUpdateJob` - hot_update_job
- `stream:GetHotUpdateJobResult` - get_hot_update_result
- `stream:GetLatestJobStartLog` - get_job_start_log
- `stream:GetJobDiagnosis` - diagnose_job
- `stream:CreateSavepoint` - create_savepoint
- `stream:GetSavepoint` - get_savepoint
- `stream:DeleteSavepoint` - delete_savepoint
- `stream:ListSavepoints` - list_savepoints
- `stream:GenerateResourcePlanWithFlinkConfAsync` - generate_resource_plan
- `stream:GetGenerateResourcePlanResult` - get_resource_plan_result
- `stream:GetLineageInfo` - get_lineage
- `stream:FlinkApiProxy` - flink_api_proxy / get_checkpoints

### Session Cluster
- `stream:CreateSessionCluster` - create_session_cluster
- `stream:UpdateSessionCluster` - update_session_cluster
- `stream:DeleteSessionCluster` - delete_session_cluster
- `stream:GetSessionCluster` - get_session_cluster
- `stream:ListSessionClusters` - list_session_clusters
- `stream:StartSessionCluster` - start_session_cluster
- `stream:StopSessionCluster` - stop_session_cluster

### SQL Development Resources
- `stream:CreateUdfArtifact` - create_udf_artifact
- `stream:UpdateUdfArtifact` - update_udf_artifact
- `stream:GetUdfArtifacts` - get_udf_artifacts
- `stream:DeleteUdfArtifact` - delete_udf_artifact
- `stream:RegisterUdfFunction` - register_udf_function
- `stream:DeleteUdfFunction` - delete_udf_function
- `stream:ListCustomConnectors` - list_connectors
- `stream:RegisterCustomConnector` - register_connector
- `stream:DeleteCustomConnector` - delete_connector
- `stream:GetCatalogs` - get_catalogs
- `stream:GetDatabases` - get_databases
- `stream:GetTables` - get_tables
- `stream:ExecuteSqlStatement` - execute_sql
- `stream:ListEngineVersionMetadata` - list_engine_versions

### SQL Runtime Resources
- `stream:CreateVariable` - create_variable
- `stream:UpdateVariable` - update_variable
- `stream:DeleteVariable` - delete_variable
- `stream:ListVariables` - list_variables
- `stream:CreateDeploymentTargetV2` - create_deployment_target
- `stream:UpdateDeploymentTargetV2` - update_deployment_target
- `stream:DeleteDeploymentTarget` - delete_deployment_target
- `stream:ListDeploymentTargets` - list_deployment_targets

---

## Minimum-Permission Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "stream:CreateFolder",
        "stream:UpdateFolder",
        "stream:DeleteFolder",
        "stream:GetFolder",
        "stream:CreateDeploymentDraft",
        "stream:UpdateDeploymentDraft",
        "stream:DeleteDeploymentDraft",
        "stream:GetDeploymentDraft",
        "stream:ListDeploymentDrafts",
        "stream:GetDeploymentDraftLock",
        "stream:ValidateDeploymentDraftAsync",
        "stream:GetValidateDeploymentDraftResult",
        "stream:ValidateSqlStatement",
        "stream:DeployDeploymentDraftAsync",
        "stream:GetDeployDeploymentDraftResult",
        "stream:CreateDeployment",
        "stream:UpdateDeployment",
        "stream:GetDeployment",
        "stream:ListDeployments",
        "stream:DeleteDeployment",
        "stream:GetDeploymentsByName",
        "stream:GetDeploymentsByLabel",
        "stream:GetEvents",
        "stream:StartJobWithParams",
        "stream:StopJob",
        "stream:GetJob",
        "stream:ListJobs",
        "stream:DeleteJob",
        "stream:HotUpdateJob",
        "stream:GetHotUpdateJobResult",
        "stream:GetLatestJobStartLog",
        "stream:GetJobDiagnosis",
        "stream:CreateSavepoint",
        "stream:GetSavepoint",
        "stream:DeleteSavepoint",
        "stream:ListSavepoints",
        "stream:GenerateResourcePlanWithFlinkConfAsync",
        "stream:GetGenerateResourcePlanResult",
        "stream:GetLineageInfo",
        "stream:FlinkApiProxy",
        "stream:CreateSessionCluster",
        "stream:UpdateSessionCluster",
        "stream:DeleteSessionCluster",
        "stream:GetSessionCluster",
        "stream:ListSessionClusters",
        "stream:StartSessionCluster",
        "stream:StopSessionCluster",
        "stream:CreateUdfArtifact",
        "stream:UpdateUdfArtifact",
        "stream:GetUdfArtifacts",
        "stream:DeleteUdfArtifact",
        "stream:RegisterUdfFunction",
        "stream:DeleteUdfFunction",
        "stream:ListCustomConnectors",
        "stream:RegisterCustomConnector",
        "stream:DeleteCustomConnector",
        "stream:GetCatalogs",
        "stream:GetDatabases",
        "stream:GetTables",
        "stream:ExecuteSqlStatement",
        "stream:ListEngineVersionMetadata",
        "stream:CreateVariable",
        "stream:UpdateVariable",
        "stream:DeleteVariable",
        "stream:ListVariables",
        "stream:CreateDeploymentTargetV2",
        "stream:UpdateDeploymentTargetV2",
        "stream:DeleteDeploymentTarget",
        "stream:ListDeploymentTargets"
      ],
      "Resource": [
        "acs:stream:*:*:workspace/*"
      ]
    }
  ]
}
```

---

## Permissions by Workflow

### SQL Development

| API Action | RAM Action |
|------------|------------|
| `CreateFolder` | `stream:CreateFolder` |
| `UpdateFolder` | `stream:UpdateFolder` |
| `DeleteFolder` | `stream:DeleteFolder` |
| `GetFolder` | `stream:GetFolder` |
| `CreateDeploymentDraft` | `stream:CreateDeploymentDraft` |
| `UpdateDeploymentDraft` | `stream:UpdateDeploymentDraft` |
| `DeleteDeploymentDraft` | `stream:DeleteDeploymentDraft` |
| `GetDeploymentDraft` | `stream:GetDeploymentDraft` |
| `ListDeploymentDrafts` | `stream:ListDeploymentDrafts` |
| `GetDeploymentDraftLock` | `stream:GetDeploymentDraftLock` |
| `ValidateDeploymentDraftAsync` | `stream:ValidateDeploymentDraftAsync` |
| `GetValidateDeploymentDraftResult` | `stream:GetValidateDeploymentDraftResult` |
| `ValidateSqlStatement` | `stream:ValidateSqlStatement` |
| `DeployDeploymentDraftAsync` | `stream:DeployDeploymentDraftAsync` |
| `GetDeployDeploymentDraftResult` | `stream:GetDeployDeploymentDraftResult` |

### Job Operations

| API Action | RAM Action |
|------------|------------|
| `CreateDeployment` | `stream:CreateDeployment` |
| `UpdateDeployment` | `stream:UpdateDeployment` |
| `GetDeployment` | `stream:GetDeployment` |
| `ListDeployments` | `stream:ListDeployments` |
| `DeleteDeployment` | `stream:DeleteDeployment` |
| `GetDeploymentsByName` | `stream:GetDeploymentsByName` |
| `GetDeploymentsByLabel` | `stream:GetDeploymentsByLabel` |
| `GetEvents` | `stream:GetEvents` |
| `StartJobWithParams` | `stream:StartJobWithParams` |
| `StopJob` | `stream:StopJob` |
| `GetJob` | `stream:GetJob` |
| `ListJobs` | `stream:ListJobs` |
| `DeleteJob` | `stream:DeleteJob` |
| `HotUpdateJob` | `stream:HotUpdateJob` |
| `GetHotUpdateJobResult` | `stream:GetHotUpdateJobResult` |
| `GetLatestJobStartLog` | `stream:GetLatestJobStartLog` |
| `GetJobDiagnosis` | `stream:GetJobDiagnosis` |
| `CreateSavepoint` | `stream:CreateSavepoint` |
| `GetSavepoint` | `stream:GetSavepoint` |
| `DeleteSavepoint` | `stream:DeleteSavepoint` |
| `ListSavepoints` | `stream:ListSavepoints` |
| `GenerateResourcePlanWithFlinkConfAsync` | `stream:GenerateResourcePlanWithFlinkConfAsync` |
| `GetGenerateResourcePlanResult` | `stream:GetGenerateResourcePlanResult` |
| `GetLineageInfo` | `stream:GetLineageInfo` |
| `FlinkApiProxy` | `stream:FlinkApiProxy` |

### Session Cluster

| API Action | RAM Action |
|------------|------------|
| `CreateSessionCluster` | `stream:CreateSessionCluster` |
| `UpdateSessionCluster` | `stream:UpdateSessionCluster` |
| `DeleteSessionCluster` | `stream:DeleteSessionCluster` |
| `GetSessionCluster` | `stream:GetSessionCluster` |
| `ListSessionClusters` | `stream:ListSessionClusters` |
| `StartSessionCluster` | `stream:StartSessionCluster` |
| `StopSessionCluster` | `stream:StopSessionCluster` |

### SQL Development Resources

| API Action | RAM Action |
|------------|------------|
| `CreateUdfArtifact` | `stream:CreateUdfArtifact` |
| `UpdateUdfArtifact` | `stream:UpdateUdfArtifact` |
| `GetUdfArtifacts` | `stream:GetUdfArtifacts` |
| `DeleteUdfArtifact` | `stream:DeleteUdfArtifact` |
| `RegisterUdfFunction` | `stream:RegisterUdfFunction` |
| `DeleteUdfFunction` | `stream:DeleteUdfFunction` |
| `ListCustomConnectors` | `stream:ListCustomConnectors` |
| `RegisterCustomConnector` | `stream:RegisterCustomConnector` |
| `DeleteCustomConnector` | `stream:DeleteCustomConnector` |
| `GetCatalogs` | `stream:GetCatalogs` |
| `GetDatabases` | `stream:GetDatabases` |
| `GetTables` | `stream:GetTables` |
| `ExecuteSqlStatement` | `stream:ExecuteSqlStatement` |
| `ListEngineVersionMetadata` | `stream:ListEngineVersionMetadata` |

### SQL Runtime Resources

| API Action | RAM Action |
|------------|------------|
| `CreateVariable` | `stream:CreateVariable` |
| `UpdateVariable` | `stream:UpdateVariable` |
| `DeleteVariable` | `stream:DeleteVariable` |
| `ListVariables` | `stream:ListVariables` |
| `CreateDeploymentTargetV2` | `stream:CreateDeploymentTargetV2` |
| `UpdateDeploymentTargetV2` | `stream:UpdateDeploymentTargetV2` |
| `DeleteDeploymentTarget` | `stream:DeleteDeploymentTarget` |
| `ListDeploymentTargets` | `stream:ListDeploymentTargets` |

---

## Resource ARN Examples

Use resource-level constraints whenever possible:

- Workspace: `acs:stream:{regionId}:{accountId}:workspace/{workspaceId}`
- Namespace: `acs:stream:{regionId}:{accountId}:workspace/{workspaceId}/namespace/{namespace}`
- Deployment: `acs:stream:{regionId}:{accountId}:workspace/{workspaceId}/namespace/{namespace}/deployment/{deploymentId}`

Example policy granting access to one specific Workspace:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "stream:ListDeployments",
        "stream:GetDeployment",
        "stream:StartJobWithParams",
        "stream:StopJob"
      ],
      "Resource": "acs:stream:cn-beijing:123456789012:workspace/w-xxx"
    }
  ]
}
```

---

## Predefined System Policies

Alibaba Cloud currently provides these commonly used system policies:

- `AliyunStreamFullAccess`
- `AliyunStreamReadOnlyAccess`

When the organization requires least privilege, prefer a custom policy that explicitly includes the `stream:*` actions listed above.

---

## Troubleshooting

### Authentication and Scope Check

First run `python3 scripts/flink_sql_manager.py config_doctor`. It reports only whether credentials can be resolved and the provider type; it does not output an AccessKey or token. The user or an administrator must inspect and grant RAM policies in the RAM console.

### Error: `Forbidden.RAM`

1. In the [RAM console](https://ram.console.aliyun.com/), inspect the policies granted under **Users → Permissions**.
2. Grant a policy containing the required `stream:*` actions.
3. Retry the operation.

### Error: `InvalidAccessKeyId.NotFound`

1. Reconfigure OAuth or the default credential chain on the user's machine; never send an AccessKey in the conversation.
2. Run `config_doctor` again. If it still fails, ask the account administrator to inspect the credential state.

### Error: `NoPermission`

1. Verify that the RAM user has the actions required by the current workflow.
2. Check whether resource-level permissions restrict access.
3. A `*` resource can be used temporarily for testing; after validation, restrict it to specific ARNs.

---

## References

- [OpenAPI RAM Actions](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-ram)
- [OpenAPI Overview](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-overview)
- [RAM Console](https://ram.console.aliyun.com/)
