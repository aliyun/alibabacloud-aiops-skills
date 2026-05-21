# PAI-DLC RAM Permission Policies

## Permission Overview

The following RAM permissions are required to use PAI-DLC service. Please ensure RAM users or roles have been granted the appropriate permissions.

## Minimum Permission Policy (Read-Only)

Query job information, logs, and monitoring data only:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pai:ListJobs",
        "pai:GetJob",
        "pai:GetPodLogs",
        "pai:GetPodEvents",
        "pai:GetJobEvents",
        "pai:GetJobMetrics",
        "pai:ListEcsSpecs",
        "pai:GetJobSanityCheckResult",
        "pai:ListJobSanityCheckResults",
        "paiworkspace:ListWorkspaces",
        "paiimage:ListImages",
        "paiimage:GetImage",
        "paidataset:ListDatasets",
        "paidataset:GetDataset",
        "paicodesource:ListCodeSources",
        "paicodesource:GetCodeSource"
      ],
      "Resource": "*"
    }
  ]
}
```

> Note: The last 7 Actions above belong to the **AIWorkSpace** product (product name `PAIWorkspace`). The RAM sub-account MUST also be granted the corresponding authorizations in order to query the WorkspaceId / ImageUri / DatasetId / CodeSourceId required for DLC job creation. The QuotaId (`--resource-id`) is manually provided by the user. Without authorization, `aliyun aiworkspace list-*` returns `Forbidden.RAM`.

## Standard Permission Policy (Read-Write)

Complete job management permissions:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pai:CreateJob",
        "pai:ListJobs",
        "pai:GetJob",
        "pai:GetPodLogs",
        "pai:GetPodEvents",
        "pai:GetJobEvents",
        "pai:GetJobMetrics",
        "pai:ListEcsSpecs",
        "pai:GetWebTerminal",
        "pai:GetToken",
        "pai:UpdateJob",
        "pai:StopJob",
        "pai:GetJobSanityCheckResult",
        "pai:ListJobSanityCheckResults",
        "paidlc:CreateJobTemplate",
        "paidlc:GetJobTemplate",
        "paidlc:ListJobTemplates",
        "paidlc:UpdateJobTemplate",
        "paidlc:SetJobTemplateDefaultVersion",
        "paidlc:CreateTensorboard",
        "paidlc:GetTensorboard",
        "paidlc:ListTensorboards",
        "paidlc:StartTensorboard",
        "paidlc:StopTensorboard",
        "paidlc:UpdateTensorboard",
        "paidlc:GetTensorboardSharedUrl",
        "paidlc:GetDashboard",
        "paidlc:GetRayDashboard",
        "paiworkspace:ListWorkspaces",
        "paiimage:ListImages",
        "paiimage:GetImage",
        "paidataset:ListDatasets",
        "paidataset:GetDataset",
        "paicodesource:ListCodeSources",
        "paicodesource:GetCodeSource"
      ],
      "Resource": "*"
    }
  ]
}
```

> Notes:
> - The middle 5 `paidlc:*JobTemplate*` Actions belong to the **PAI-DLC** product, used by the 5 CLI subcommands `aliyun pai-dlc create-job-template / list-job-templates / ...` (provided by plugin >= 0.3.1). For view-only template access (without creation), only `paidlc:GetJobTemplate` and `paidlc:ListJobTemplates` need to be granted.
> - The last 7 Actions belong to the **AIWorkSpace** product. They are required for the resource discovery (`list-workspaces` / `list-images` / `list-datasets` / `list-code-sources`) performed before invoking `aliyun pai-dlc create-job`, and MUST be granted to the RAM sub-account together with the `pai:*` Actions above. `--resource-id` (QuotaId) is manually provided by the user.

## Full Permission Policy (Administrator)

Complete permissions including workspace and resource group management:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pai:CreateJob",
        "pai:ListJobs",
        "pai:GetJob",
        "pai:GetPodLogs",
        "pai:GetPodEvents",
        "pai:GetJobEvents",
        "pai:GetJobMetrics",
        "pai:ListEcsSpecs",
        "pai:GetWebTerminal",
        "pai:GetToken",
        "pai:UpdateJob",
        "pai:StopJob",
        "pai:GetJobSanityCheckResult",
        "pai:ListJobSanityCheckResults",
        "paiworkspace:ListWorkspaces",
        "paiimage:ListImages",
        "paiimage:GetImage",
        "paidataset:ListDatasets",
        "paidataset:GetDataset",
        "paicodesource:ListCodeSources",
        "paidlc:CreateJobTemplate",
        "paidlc:GetJobTemplate",
        "paidlc:ListJobTemplates",
        "paidlc:UpdateJobTemplate",
        "paidlc:SetJobTemplateDefaultVersion",
        "paidlc:CreateTensorboard",
        "paidlc:GetTensorboard",
        "paidlc:ListTensorboards",
        "paidlc:StartTensorboard",
        "paidlc:StopTensorboard",
        "paidlc:UpdateTensorboard",
        "paidlc:GetTensorboardSharedUrl",
        "paidlc:GetDashboard",
        "paidlc:GetRayDashboard",
        "paicodesource:GetCodeSource"
      ],
      "Resource": "*"
    }
  ]
}
```

> Note: The `pai:ListImages` / `pai:ListDataSources` / `pai:GetDataSource` listed in earlier versions are **NOT correct Action names**. According to the AIWorkSpace OpenAPI metadata `systemTags.ramAction.action`, the following should be used instead:
>
> - `paiimage:ListImages` (also includes `paiimage:GetImage`)
> - `paidataset:ListDatasets` (also includes `paidataset:GetDataset`)
> - `paicodesource:ListCodeSources` (also includes `paicodesource:GetCodeSource`)
>
> All of the above Actions belong to the **AIWorkSpace** product (product name `PAIWorkspace`). The RAM sub-account MUST be granted the corresponding authorizations; granting only `pai:*` is insufficient to invoke `aliyun aiworkspace list-*` / `get-*`. The `pai:GetQuota` / `pai:ListResourceGroups` / `pai:GetResourceGroup` listed in earlier versions do not appear among the 7 resource discovery APIs covered by this task and are therefore not appended to the policy here.

## Permissions by Operation Category

### Job Creation Related

| Operation | Permission Action | Description |
|-----------|-------------------|-------------|
| Create Training Job | `pai:CreateJob` | Create DLC training job |
| List Machine Specs | `pai:ListEcsSpecs` | Query available ECS instance specifications |

### Job Query Related

| Operation | Permission Action | Description |
|-----------|-------------------|-------------|
| List Jobs | `pai:ListJobs` | Get job list with pagination and filtering |
| Get Job Details | `pai:GetJob` | Get detailed information of a single job |
| Get Pod Logs | `pai:GetPodLogs` | Get log output of job nodes |
| Get Pod Events | `pai:GetPodEvents` | Get system events of job nodes |
| Get Job Events | `pai:GetJobEvents` | Get job-level system events |
| Get Monitoring Metrics | `pai:GetJobMetrics` | Get CPU/GPU/memory usage metrics |

### Job Management Related

| Operation | Permission Action | Description |
|-----------|-------------------|-------------|
| Update Job | `pai:UpdateJob` | Update job configuration, such as priority |
| Stop Job | `pai:StopJob` | Stop running job |

### JobTemplate Related (plugin >= 0.3.1)

| Operation | Permission Action | Description |
|-----------|-------------------|-------------|
| Create Template | `paidlc:CreateJobTemplate` | Create a job template (auto-creates version 1) |
| Get Template | `paidlc:GetJobTemplate` | Read template metadata + version content |
| List Templates | `paidlc:ListJobTemplates` | List templates within a workspace |
| Update Template | `paidlc:UpdateJobTemplate` | Update metadata, or create a new version (with `Content`+`Constraints`) |
| Set Default Version | `paidlc:SetJobTemplateDefaultVersion` | Switch default version |

### Health Check Related

| Operation | Permission Action | Description |
|-----------|-------------------|-------------|
| Get Check Result | `pai:GetJobSanityCheckResult` | Get specific compute health check result |
| List Check Results | `pai:ListJobSanityCheckResults` | Get list of all compute health check results |

### Access and Sharing Related

| Operation | Permission Action | Description |
|-----------|-------------------|-------------|
| Get Web Terminal | `pai:GetWebTerminal` | Get container Web terminal access link |
| Get Sharing Token | `pai:GetToken` | Get job sharing token |

### TensorBoard Related

| Operation | Permission Action | Description |
|-----------|-------------------|-------------|
| Create TensorBoard | `paidlc:CreateTensorboard` | Launch a TensorBoard instance |
| Get TensorBoard | `paidlc:GetTensorboard` | Get TensorBoard instance detail |
| List TensorBoards | `paidlc:ListTensorboards` | List TensorBoard instances |
| Start TensorBoard | `paidlc:StartTensorboard` | Start a stopped instance |
| Stop TensorBoard | `paidlc:StopTensorboard` | Stop a running instance |
| Update TensorBoard | `paidlc:UpdateTensorboard` | Update instance config |
| Get Shared URL | `paidlc:GetTensorboardSharedUrl` | Generate shareable link |

### Dashboard Related

| Operation | Permission Action | Description |
|-----------|-------------------|-------------|
| Get Dashboard | `paidlc:GetDashboard` | Get DLC job dashboard URL |
| Get Ray Dashboard | `paidlc:GetRayDashboard` | Get Ray dashboard URL |

## Resource-Level Authorization

To restrict permissions to specific workspace:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pai:CreateJob",
        "pai:ListJobs",
        "pai:GetJob",
        "pai:UpdateJob",
        "pai:StopJob"
      ],
      "Resource": [
        "acs:pai:*:*:workspace/<workspace-id>",
        "acs:pai:*:*:workspace/<workspace-id>/*"
      ]
    }
  ]
}
```

## Permission Check Commands

Use the following commands to check current user permissions:

```bash
# Check current configuration
aliyun configure list

# Test job list permission
aliyun pai-dlc list-jobs --region cn-hangzhou --page-size 1 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# If Forbidden.RAM error is returned, insufficient permissions
```

## Common Errors

| Error Code | Description | Solution |
|------------|-------------|----------|
| `Forbidden.RAM` | Insufficient RAM permissions | Contact administrator to add corresponding permissions |
| `Forbidden.AccessDenied` | No access to this resource | Check resource-level authorization configuration |
| `InvalidAccessKeyId.NotFound` | AccessKey does not exist | Check if AccessKey is correct |
| `SignatureDoesNotMatch` | Signature mismatch | Check if AccessKeySecret is correct |

## Best Practices

1. **Principle of Least Privilege** — Only grant permissions users actually need
2. **Use RAM Roles** — For tasks running on ECS instances, use ECS RAM Role instead of AK/SK
3. **Regular Auditing** — Regularly check and clean up unnecessary permissions
4. **Separate Read-Only and Read-Write** — Assign read-only policies to users who only need to view
5. **Resource Isolation** — Use resource-level authorization to isolate tasks of different projects

## Reference Links

- [PAI RAM Permission Documentation](https://help.aliyun.com/zh/pai/user-guide/create-a-ram-user)
- [RAM Policy Syntax](https://help.aliyun.com/zh/ram/user-guide/policy-syntax-and-structure)
- [RAM Best Practices](https://help.aliyun.com/zh/ram/user-guide/ram-best-practices)

---

## Permissions by Operation Category (Resource Discovery)

The following table covers only the 7 AIWorkSpace resource discovery APIs (QuotaId (`--resource-id`) is manually provided by the user):

| Operation | CLI Subcommand | RAM Action | Product | Lookup Purpose |
|---|---|---|---|---|
| List Workspaces | `aliyun aiworkspace list-workspaces` | `paiworkspace:ListWorkspaces` | AIWorkSpace | Obtain `--workspace-id` |
| List Images | `aliyun aiworkspace list-images` | `paiimage:ListImages` | AIWorkSpace | Obtain candidates for `WorkerSpec.Image` |
| Get Image Details | `aliyun aiworkspace get-image` | `paiimage:GetImage` | AIWorkSpace | Look up `ImageUri` |
| List Datasets | `aliyun aiworkspace list-datasets` | `paidataset:ListDatasets` | AIWorkSpace | Obtain `DataSources[].DataSourceId` |
| Get Dataset Details | `aliyun aiworkspace get-dataset` | `paidataset:GetDataset` | AIWorkSpace | Look up `Uri` / `SourceType` |
| List Code Sources | `aliyun aiworkspace list-code-sources` | `paicodesource:ListCodeSources` | AIWorkSpace | Obtain `CodeSource.CodeSourceId` |
| Get Code Source Details | `aliyun aiworkspace get-code-source` | `paicodesource:GetCodeSource` | AIWorkSpace | Look up `Uri` / `CodeBranch` / `CodeCommit` |

**Authorization Tip**: These 7 Actions and PAI-DLC's `pai:*` Actions belong to different products, and both groups MUST appear simultaneously in the RAM sub-account policy. Do NOT abbreviate them as `aiworkspace:*`.
