# PAI-DLC API and CLI Command Reference

## Complete API List (28 APIs)

| # | Product | CLI Command | API Action | Key Required Params |
|---|---------|-------------|------------|---------------------|
| 1 | PAI-DLC | `aliyun pai-dlc create-job` | CreateJob | `--display-name`, `--job-type`, `--job-specs`, `--user-command` |
| 2 | PAI-DLC | `aliyun pai-dlc list-jobs` | ListJobs | None |
| 3 | PAI-DLC | `aliyun pai-dlc get-job` | GetJob | `--job-id` |
| 4 | PAI-DLC | `aliyun pai-dlc get-pod-logs` | GetPodLogs | `--job-id`, `--pod-id` |
| 5 | PAI-DLC | `aliyun pai-dlc get-pod-events` | GetPodEvents | `--job-id`, `--pod-id` |
| 6 | PAI-DLC | `aliyun pai-dlc get-job-events` | GetJobEvents | `--job-id` |
| 7 | PAI-DLC | `aliyun pai-dlc get-job-metrics` | GetJobMetrics | `--job-id`, `--metric-type` |
| 8 | PAI-DLC | `aliyun pai-dlc list-ecs-specs` | ListEcsSpecs | None |
| 9 | PAI-DLC | `aliyun pai-dlc get-web-terminal` | GetWebTerminal | `--job-id`, `--pod-id` |
| 10 | PAI-DLC | `aliyun pai-dlc get-token` | GetToken | `--target-id`, `--target-type` |
| 11 | PAI-DLC | `aliyun pai-dlc update-job` | UpdateJob | `--job-id` |
| 12 | PAI-DLC | `aliyun pai-dlc stop-job` | StopJob | `--job-id` |
| 13 | PAI-DLC | `aliyun pai-dlc get-job-sanity-check-result` | GetJobSanityCheckResult | `--job-id`, `--sanity-check-number` |
| 14 | PAI-DLC | `aliyun pai-dlc list-job-sanity-check-results` | ListJobSanityCheckResults | `--job-id` |
| 15 | PAI-DLC | `aliyun pai-dlc create-job-template` | CreateJobTemplate | `--template-name`, `--workspace-id`, `--content` |
| 16 | PAI-DLC | `aliyun pai-dlc get-job-template` | GetJobTemplate | `--template-id` |
| 17 | PAI-DLC | `aliyun pai-dlc list-job-templates` | ListJobTemplates | `--workspace-id` |
| 18 | PAI-DLC | `aliyun pai-dlc update-job-template` | UpdateJobTemplate | `--template-id` |
| 19 | PAI-DLC | `aliyun pai-dlc set-job-template-default-version` | SetJobTemplateDefaultVersion | `--template-id`, `--biz-version` |
| 20 | PAI-DLC | `aliyun pai-dlc create-tensorboard` | CreateTensorboard | `--job-id` or `--data-sources` |
| 21 | PAI-DLC | `aliyun pai-dlc get-tensorboard` | GetTensorboard | `--tensorboard-id` |
| 22 | PAI-DLC | `aliyun pai-dlc list-tensorboards` | ListTensorboards | None |
| 23 | PAI-DLC | `aliyun pai-dlc start-tensorboard` | StartTensorboard | `--tensorboard-id` |
| 24 | PAI-DLC | `aliyun pai-dlc stop-tensorboard` | StopTensorboard | `--tensorboard-id` |
| 25 | PAI-DLC | `aliyun pai-dlc update-tensorboard` | UpdateTensorboard | `--tensorboard-id` |
| 26 | PAI-DLC | `aliyun pai-dlc get-tensorboard-shared-url` | GetTensorboardSharedUrl | `--tensorboard-id` |
| 27 | PAI-DLC | `aliyun pai-dlc get-dashboard` | GetDashboard | `--job-id` |
| 28 | PAI-DLC | `aliyun pai-dlc get-ray-dashboard` | GetRayDashboard | `--job-id` |

> For full parameter listings of any command, use `aliyun pai-dlc <command> --help`.
> Every CLI invocation MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job`.

---

## Key API Rules & Red Lines

This section documents non-obvious behaviors, constraints, and red lines that are
**NOT** available via `--help`. For parameter-level details, always use `--help`.

### CreateJob — Critical Rules

> ⚠️ **Red Line 1: EcsSpec vs ResourceConfig** — Mutually exclusive. Use `EcsSpec` for public
> pay-as-you-go resources, `ResourceConfig` (with CPU/Memory/GPU/GPUType) for dedicated
> resource groups. Both must NOT appear in the same TaskSpec.

> ⚠️ **Red Line 2: Image URI Source** — `--job-specs[].Image` MUST come from
> `aliyun aiworkspace list-images`. Never guess or hardcode image URIs.

> ⚠️ **Red Line 3: No ROA Fallback** — If a plugin subcommand is unavailable, install/upgrade
> the plugin first. Never construct generic ROA calls with HTTP method + path template.

**Key TaskSpec fields:** `Type` (Worker/PS/Master/Evaluator/Chief), `Image`, `PodCount`, `EcsSpec` or `ResourceConfig`.

**Before `create-job`, always run resource discovery:**
```bash
aliyun aiworkspace list-workspaces       # → --workspace-id
aliyun aiworkspace list-images            # → --job-specs[].Image
aliyun aiworkspace list-datasets          # → --data-sources[].DataSourceId
aliyun aiworkspace list-code-sources      # → --code-source.CodeSourceId
```

### Job Status Lifecycle

```
Creating → Queuing → (Bidding) → EnvPreparing → SanityChecking
  → Running → (Restarting) → Stopping → Succeeded/Failed/Stopped
```

Bidding only applies to Spot jobs. SanityChecking only appears when health check is enabled.

### ListEcsSpecs — Discover Available Machine Types

`aliyun pai-dlc list-ecs-specs` discovers ECS/Lingjun machine types.

```bash
aliyun pai-dlc list-ecs-specs \
  --accelerator-type GPU \
  --page-size 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

Key filters: `--accelerator-type` (CPU/GPU), `--resource-type` (ECS/Lingjun), `--instance-types` (comma-separated).

### TensorBoard APIs (7 commands)

All under `aliyun pai-dlc {create,get,list,start,stop,update}-tensorboard` + `get-tensorboard-shared-url`.

Key rules:
- **Create**: must provide `--job-id` (attach to existing job) OR `--data-sources` (from dataset), mutually exclusive
- **Shared URL**: `get-tensorboard-shared-url` generates time-limited shareable link (`--expire-time-seconds`, max 604800)

### Dashboard APIs (2 commands)

`aliyun pai-dlc get-dashboard` / `get-ray-dashboard` — both require `--job-id`.
Only return non-empty URLs for `RayJob` type jobs.

### Other APIs (Quick Reference)

| API | CLI Command | Key Note |
|-----|-------------|----------|
| ListJobs | `aliyun pai-dlc list-jobs` | Filter by `--status`, `--workspace-id`, `--job-type` |
| GetJob | `aliyun pai-dlc get-job` | Use `--need-detail` for full info |
| GetPodLogs | `aliyun pai-dlc get-pod-logs` | Requires `--job-id` + `--pod-id` |
| GetPodEvents | `aliyun pai-dlc get-pod-events` | Requires `--job-id` + `--pod-id` |
| GetJobEvents | `aliyun pai-dlc get-job-events` | Default 7-day window |
| GetJobMetrics | `aliyun pai-dlc get-job-metrics` | Requires `--metric-type` (e.g., GpuCoreUsage) |
| GetWebTerminal | `aliyun pai-dlc get-web-terminal` | Returns Web Terminal access URL |
| GetToken | `aliyun pai-dlc get-token` | Generates sharing tokens for job/tensorboard |
| UpdateJob | `aliyun pai-dlc update-job` | Update priority, accessibility, or job-specs |
| StopJob | `aliyun pai-dlc stop-job` | Stop before manipulating job state |
| SanityCheck | `aliyun pai-dlc get-job-sanity-check-result` / `list-job-sanity-check-results` | Requires health check enabled in Settings |

---

## AIWorkSpace APIs — Resource Discovery

These 8 APIs belong to **AIWorkSpace 2021-02-04** (plugin: `aliyun-cli-aiworkspace`).
They provide value sources for DLC `create-job` fields. Always run these before creating a job.

> ⚠️ Do NOT use generic ROA calls (HTTP method + path template). Install the plugin:
> `aliyun plugin install --names aliyun-cli-aiworkspace`

### Image Discovery

| API | CLI | Returns | Maps To |
|-----|-----|---------|---------|
| ListImages | `aliyun aiworkspace list-images --workspace-id <id>` | `Images[].ImageUri` | `--job-specs[].Image` |
| GetImage | `aliyun aiworkspace get-image --image-id <id>` | Image details | Verify ImageUri |

Key `--labels` filters: `system.chipType=GPU`, `system.framework=PyTorch`, `system.officialReleased=true`.
Multiple labels: `--labels system.chipType=GPU,system.framework=PyTorch`.

### Dataset Discovery

| API | CLI | Returns | Maps To |
|-----|-----|---------|---------|
| ListDatasets | `aliyun aiworkspace list-datasets --workspace-id <id>` | `Datasets[].DatasetId` | `--data-sources[].DataSourceId` |
| GetDataset | `aliyun aiworkspace get-dataset --dataset-id <id>` | Dataset Uri | `DataSources[].Uri` |

### CodeSource Discovery

| API | CLI | Returns | Maps To |
|-----|-----|---------|---------|
| ListCodeSources | `aliyun aiworkspace list-code-sources --workspace-id <id>` | `CodeSources[].CodeSourceId` | `--code-source.CodeSourceId` |
| GetCodeSource | `aliyun aiworkspace get-code-source --code-source-id <id>` | Uri, Branch, Commit | CodeSource fields |

### Quota & Workspace Discovery

| API | CLI | Returns | Maps To |
|-----|-----|---------|---------|
| ListWorkspaces | `aliyun aiworkspace list-workspaces` | `Workspaces[].WorkspaceId` | `--workspace-id` |

> **Quota (--resource-id):** User MUST manually provide the QuotaId. No CLI discovery step.

### Field Mapping Summary

| CreateJob Field | Source API | Source Field |
|---|---|---|
| `--job-specs[].Image` | ListImages | `Images[].ImageUri` |
| `--data-sources[].DataSourceId` | ListDatasets | `Datasets[].DatasetId` |
| `--code-source.CodeSourceId` | ListCodeSources | `CodeSources[].CodeSourceId` |
| `--resource-id` | Manual input | User-provided QuotaId |
| `--workspace-id` | ListWorkspaces | `Workspaces[].WorkspaceId` |

**Recommended order:** `list-workspaces` → `list-images` / `list-datasets` / `list-code-sources` → fill into `create-job`. `--resource-id` is manually provided by user.

### AIWorkSpace RAM Permissions

| Action | Use Case |
|---|---|
| `paiimage:ListImages` / `paiimage:GetImage` | Image discovery |
| `paidataset:ListDatasets` / `paidataset:GetDataset` | Dataset discovery |
| `paicodesource:ListCodeSources` / `paicodesource:GetCodeSource` | Code source discovery |
| `paiworkspace:ListWorkspaces` | Workspace discovery |

---

## JobTemplate APIs — Template Management

A JobTemplate saves a complete `CreateJob` configuration as a reusable template with
multi-version management and field constraints (`locked` / `overridable` / `required`).

> **Plugin Requirement:** `aliyun-cli-pai-dlc` >= 0.3.1. Verify with:
> `aliyun pai-dlc create-job-template --help`. If unavailable, run:
> `aliyun plugin update --name aliyun-cli-pai-dlc`.

### Command Summary

| # | CLI Command | Key Required | RAM Permission |
|---|-------------|-------------|----------------|
| B1 | `create-job-template` | `--template-name`, `--workspace-id`, `--content` | `paidlc:CreateJobTemplate` |
| B2 | `get-job-template` | `--template-id` | `paidlc:GetJobTemplate` |
| B3 | `list-job-templates` | `--workspace-id` | `paidlc:ListJobTemplates` |
| B4 | `update-job-template` | `--template-id` | `paidlc:UpdateJobTemplate` |
| B5 | `set-job-template-default-version` | `--template-id`, `--biz-version` | `paidlc:SetJobTemplateDefaultVersion` |

### Constraints Format

When passing `--constraints`, use escaped-quote JSON wrapped in single-quoted shell string:

```bash
CONSTRAINTS='{\"JobSpecs[0].Image\":\"locked\",\"UserCommand\":\"locked\",\"JobType\":\"locked\"}'

aliyun pai-dlc create-job-template \
  --region <region> \
  --workspace-id <workspace-id> \
  --template-name "my-template" \
  --content "$CONTENT" \
  --constraints "$CONSTRAINTS" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

**Constraint types:**

| Type | Behavior on Job Submission |
|---|---|
| `locked` | Field cannot be overridden by `create-job` |
| `overridable` | Field can be overridden by `create-job` |
| `required` | `create-job` MUST provide this field |

**Common path examples** (without `$.` prefix):

- `JobSpecs[0].Image` — lock the image of the first TaskSpec
- `JobSpecs[0].EcsSpec` — allow overriding machine type
- `UserCommand` — required startup command
- `DataSources[0].MountPath` — lock mount path

> ⚠️ Constraints must be submitted together with Content; updating Constraints alone is rejected.

### CreateJobTemplate Example

```bash
CONTENT=$(cat <<'EOF'
{
  "JobType": "PyTorchJob",
  "JobSpecs": [{
    "Type": "Worker",
    "PodCount": 1,
    "Image": "<ImageUri from list-images>",
    "EcsSpec": "ecs.gn6i-c4g1.xlarge"
  }],
  "UserCommand": "python -c 'print(123)'"
}
EOF
)

aliyun pai-dlc create-job-template \
  --region cn-hangzhou \
  --workspace-id <WORKSPACE_ID> \
  --template-name "demo-pytorch-template" \
  --content "$CONTENT" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

### GetJobTemplate — Version Query

```bash
# Default version
aliyun pai-dlc get-job-template \
  --region cn-hangzhou \
  --template-id <TEMPLATE_ID> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# All versions (for diff)
aliyun pai-dlc get-job-template \
  --region cn-hangzhou \
  --template-id <TEMPLATE_ID> \
  --biz-version all \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

### UpdateJobTemplate — Create New Version

```bash
# Metadata only (no new version)
aliyun pai-dlc update-job-template \
  --region cn-hangzhou \
  --template-id <TEMPLATE_ID> \
  --description "Updated description" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# New version with constraints
aliyun pai-dlc update-job-template \
  --region cn-hangzhou \
  --template-id <TEMPLATE_ID> \
  --content "$NEW_CONTENT" \
  --constraints "$CONSTRAINTS" \
  --set-as-default true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

> ⚠️ `--content` + `--constraints` must be provided together or both omitted.
> `--biz-version` is NOT supported in update; use `set-job-template-default-version` to switch versions.

### Connecting JobTemplate with CreateJob

```bash
aliyun pai-dlc create-job \
  --region cn-hangzhou \
  --workspace-id <WORKSPACE_ID> \
  --display-name "demo-from-template" \
  --template-id <TEMPLATE_ID> \
  --user-command 'python train.py --epochs 10' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

The server merges template content with `create-job` parameters: `locked` fields keep template values, `overridable` fields take input parameters, missing `required` fields return error.

### Common JobTemplate Errors

| Error Code | Trigger | Fix |
|---|---|---|
| `InvalidParameter.TemplateName` | Name >1024 chars or empty | Validate length |
| `InvalidParameter.Content` | Not valid JSON or missing required fields | Test with `create-job --cli-dry-run` |
| `InvalidParameter.Constraints` | Invalid constraint type or submitted without Content | Use `locked`/`overridable`/`required` only |
| `NotFound.JobTemplate` | TemplateId doesn't exist | Confirm with `list-job-templates` |
| `NotFound.JobTemplateVersion` | Non-existent version number | Use `get-job-template --biz-version all` |
| `Forbidden.RAM` | Missing `paidlc:*JobTemplate*` permission | See ram-policies.md |
