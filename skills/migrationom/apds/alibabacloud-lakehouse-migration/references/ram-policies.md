# RAM Policy Declaration

This skill is the unified dispatcher of Alibaba Cloud Lakehouse Migration Center (LHM). The sub-skills it routes to call LHM services via the aliyun CLI (`aliyun-cli-lhm` plugin) and the `alibabacloud_lhm` SDK. This document declares the RAM permissions required by those cloud service calls.

## Credential Resolution

Credentials must be resolved through the default credential chain. Hardcoding or explicitly passing AccessKey ID/Secret in code or skill output is strictly prohibited. Resolution order:

1. Environment variables: `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET`
2. Credentials file: `~/.alibabacloud/credentials`
3. Configured aliyun CLI profile (`aliyun configure`)
4. Instance RAM role (when running on Alibaba Cloud compute resources such as ECS)

Grant the RAM policies below to the identity actually resolved by the default credential chain (RAM user, RAM role, or instance role).

## Permissions Required by Each Sub-Skill

### 1. Data Validation (`lhm-data-validation-skill`)

| LHM Action | Purpose |
|------------|---------|
| `lhm:GetDataCheckTaskList` | List existing validation tasks |
| `lhm:AddDataCheckTask` | Create a validation task |
| `lhm:UpdateDataCheckTask` | Update / rerun a validation task |
| `lhm:AddDataCheckConfig` | Attach validation configuration to a task |
| `lhm:ExecDataCheckSaveTask` | Save and submit a validation task |
| `lhm:GetDataCheckTaskConfig` | Read task configuration |
| `lhm:ListDataCheckTaskHistory` | Query task execution history |
| `lhm:GetDataCheckReportOverview` | Get the validation report overview |
| `lhm:GetDataCheckEngineRelation` | Query engine binding relations |
| `lhm:ListMetaDataComponentEngine` | List supported engines |
| `lhm:GetLhmDWResourceGroupStatus` | Check resource group binding status |
| `lhm:GetLhmAgentStatus` | Check LHM Agent status |

### 2. Big-Data Workflow Migration (`lhm-bigdata-workflow-migration-skill`)

Environment check (`lhm-sch-env`):

| LHM Action | Purpose |
|------------|---------|
| `lhm:GetDataCheckTaskList` | Environment pre-check |
| `lhm:GetLhmDWResourceGroupStatus` | Validate resource group binding |
| `lhm:GetLhmAgentStatus` | Validate Agent availability |

Data source management (`lhm-sch-ds`):

| LHM Action | Purpose |
|------------|---------|
| `lhm:ListMetaDataComponentPage` | List existing data sources |
| `lhm:ExecMetaDataComponentName` | Check data source name availability |
| `lhm:AddMetaDataComponent` | Create a data source |
| `lhm:ExecWorkflowConnectivity` | Test data source connectivity |
| `lhm:GetMetaOssTempKey` | Obtain OSS temporary credentials for uploading workflow artifacts |

Migration deployment (`lhm-sch-deploy`):

| LHM Action | Purpose |
|------------|---------|
| `lhm:GetBwmMigrationWorkflowSubmitStart` | Submit a migration workflow |
| `lhm:GetBwmMigrationSubmitInstanceList` | List submission instances |
| `lhm:GetBwmMigrationTaskWriterResultPackage` | Get the migration result package |
| `lhm:GetBwmMigrationTaskWriterWorkflowList` | List migrated workflows |

Workflow exploration and conversion (`lhm-sch-read-exec`):

| LHM Action | Purpose |
|------------|---------|
| `lhm:PostInnerReader` | Read source workflow definitions |
| `lhm:GetInnerReadAsyncResult` | Poll asynchronous read results |
| `lhm:PostInnerConvert` | Convert workflow definitions |
| `lhm:GetInnerConvertAsyncResult` | Poll asynchronous conversion results |

> Note: `lhm:GetMetaOssTempKey` returns server-issued OSS temporary credentials for uploading workflow artifacts, so this flow normally does not require granting additional `oss:*` RAM permissions.

### 3. SQL Conversion (`lhm-sql-conversion`)

This sub-skill does not call the LHM OpenAPI directly. SQL DryRun validation connects to the target database directly via each data source's connection configuration, or goes through a configured MCP service. No LHM RAM authorization is required.

## Policy Examples

### Least-privilege policy: Data Validation

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lhm:GetDataCheckTaskList",
        "lhm:AddDataCheckTask",
        "lhm:UpdateDataCheckTask",
        "lhm:AddDataCheckConfig",
        "lhm:ExecDataCheckSaveTask",
        "lhm:GetDataCheckTaskConfig",
        "lhm:ListDataCheckTaskHistory",
        "lhm:GetDataCheckReportOverview",
        "lhm:GetDataCheckEngineRelation",
        "lhm:ListMetaDataComponentEngine",
        "lhm:GetLhmDWResourceGroupStatus",
        "lhm:GetLhmAgentStatus"
      ],
      "Resource": "*"
    }
  ]
}
```

### Least-privilege policy: Workflow Migration

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lhm:GetDataCheckTaskList",
        "lhm:GetLhmDWResourceGroupStatus",
        "lhm:GetLhmAgentStatus",
        "lhm:ListMetaDataComponentPage",
        "lhm:ExecMetaDataComponentName",
        "lhm:AddMetaDataComponent",
        "lhm:ExecWorkflowConnectivity",
        "lhm:GetMetaOssTempKey",
        "lhm:GetBwmMigrationWorkflowSubmitStart",
        "lhm:GetBwmMigrationSubmitInstanceList",
        "lhm:GetBwmMigrationTaskWriterResultPackage",
        "lhm:GetBwmMigrationTaskWriterWorkflowList",
        "lhm:PostInnerReader",
        "lhm:GetInnerReadAsyncResult",
        "lhm:PostInnerConvert",
        "lhm:GetInnerConvertAsyncResult"
      ],
      "Resource": "*"
    }
  ]
}
```

### Merged policy (full dispatcher scope)

When the same identity needs to serve all routed sub-skills, simply merge the `Action` lists of the two policies above into a single statement.

## Security Notes

- Follow the least-privilege principle: grant only the policy corresponding to the sub-skills actually used
- Prefer RAM roles and STS temporary credentials over long-lived AccessKeys
- Never print, log, or echo plaintext AccessKey Secret values in skill output
