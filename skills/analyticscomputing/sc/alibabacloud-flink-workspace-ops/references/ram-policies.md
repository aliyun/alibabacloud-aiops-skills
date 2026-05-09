# RAM Policies for Flink Console Operations

Alibaba Cloud RAM (Resource Access Management) permissions required by
`scripts/flink_ververica_ops.py`.

> Note: For OpenAPI 2022-07-18 (Ververica), official action names use the
> `stream:*` namespace.

---

## Required Permissions

The following actions cover all implemented commands in this skill:

### W1: SQL Development
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

### W2: Job Operations
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
- `stream:FlinkApiProxy` - flink_api_proxy

### W3: Session Clusters
- `stream:CreateSessionCluster` - create_session_cluster
- `stream:UpdateSessionCluster` - update_session_cluster
- `stream:DeleteSessionCluster` - delete_session_cluster
- `stream:GetSessionCluster` - get_session_cluster
- `stream:ListSessionClusters` - list_session_clusters
- `stream:StartSessionCluster` - start_session_cluster
- `stream:StopSessionCluster` - stop_session_cluster

### W4: Dev Resources
- `stream:GetCatalogs` - get_catalogs
- `stream:GetDatabases` - get_databases
- `stream:GetTables` - get_tables
- `stream:ExecuteSqlStatement` - execute_sql
- `stream:ListEngineVersionMetadata` - list_engine_versions

### W5: Workspace Administration
- `stream:CreateMember` - create_member
- `stream:UpdateMember` - update_member
- `stream:DeleteMember` - delete_member
- `stream:GetMember` - get_member
- `stream:ListMembers` - list_members
- `stream:CreateVariable` - create_variable
- `stream:UpdateVariable` - update_variable
- `stream:DeleteVariable` - delete_variable
- `stream:ListVariables` - list_variables
- `stream:CreateDeploymentTargetV2` - create_deployment_target
- `stream:UpdateDeploymentTargetV2` - update_deployment_target
- `stream:DeleteDeploymentTarget` - delete_deployment_target
- `stream:ListDeploymentTargets` - list_deployment_targets

---

## Minimum Permission Policy

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
        "stream:GetCatalogs",
        "stream:GetDatabases",
        "stream:GetTables",
        "stream:ExecuteSqlStatement",
        "stream:ListEngineVersionMetadata",
        "stream:CreateMember",
        "stream:UpdateMember",
        "stream:DeleteMember",
        "stream:GetMember",
        "stream:ListMembers",
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

## Permission Breakdown by Workflow

### W1: SQL Development

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

### W2: Job Operations

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

### W3: Session Clusters

| API Action | RAM Action |
|------------|------------|
| `CreateSessionCluster` | `stream:CreateSessionCluster` |
| `UpdateSessionCluster` | `stream:UpdateSessionCluster` |
| `DeleteSessionCluster` | `stream:DeleteSessionCluster` |
| `GetSessionCluster` | `stream:GetSessionCluster` |
| `ListSessionClusters` | `stream:ListSessionClusters` |
| `StartSessionCluster` | `stream:StartSessionCluster` |
| `StopSessionCluster` | `stream:StopSessionCluster` |

### W4: Dev Resources

| API Action | RAM Action |
|------------|------------|
| `GetCatalogs` | `stream:GetCatalogs` |
| `GetDatabases` | `stream:GetDatabases` |
| `GetTables` | `stream:GetTables` |
| `ExecuteSqlStatement` | `stream:ExecuteSqlStatement` |
| `ListEngineVersionMetadata` | `stream:ListEngineVersionMetadata` |

### W5: Workspace Administration

| API Action | RAM Action |
|------------|------------|
| `CreateMember` | `stream:CreateMember` |
| `UpdateMember` | `stream:UpdateMember` |
| `DeleteMember` | `stream:DeleteMember` |
| `GetMember` | `stream:GetMember` |
| `ListMembers` | `stream:ListMembers` |
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

Use resource-level constraints when possible:

- Workspace: `acs:stream:{regionId}:{accountId}:workspace/{workspaceId}`
- Namespace: `acs:stream:{regionId}:{accountId}:workspace/{workspaceId}/namespace/{namespace}`
- Deployment: `acs:stream:{regionId}:{accountId}:workspace/{workspaceId}/namespace/{namespace}/deployment/{deploymentId}`

Example policy for one specific workspace:

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

Alibaba Cloud currently provides these common system policies:

- `AliyunStreamFullAccess`
- `AliyunStreamReadOnlyAccess`

If your organization requires least privilege, prefer custom policy with
explicit `stream:*` actions shown above.

---

## Troubleshooting

### CLI Plugin Mode (MANDATORY)

When checking RAM permissions with `aliyun` CLI, always use plugin-mode command names (lowercase-hyphenated). Never use PascalCase API names directly in CLI commands.

```bash
aliyun ram list-policies-for-user --user-name <user_name>
aliyun ram list-access-keys --user-name <user_name>
```

### Error: `Forbidden.RAM`

1. Verify attached policies in the [RAM Console](https://ram.console.aliyun.com/) → Users → Permissions tab.
2. Attach a policy that includes required `stream:*` actions.
3. Retry the operation.

### Error: `InvalidAccessKeyId.NotFound`

1. Verify AccessKey in the [RAM Console](https://ram.console.aliyun.com/) → Users → AccessKey Management tab.
2. Rotate/recreate AccessKey and update local config.

### Error: `NoPermission`

1. Ensure the RAM user has the required actions for the specific workflow.
2. Check if resource-level permissions are restricting access.
3. Use `*` resource for testing, then narrow down to specific ARNs.

---

## References

- [OpenAPI RAM actions](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-ram)
- [OpenAPI overview](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-overview)
- [RAM Console](https://ram.console.aliyun.com/)
