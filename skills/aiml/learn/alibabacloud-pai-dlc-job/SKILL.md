---
name: alibabacloud-pai-dlc-job
description: |
  Alibaba Cloud PAI-DLC (Deep Learning Containers) job management skill.
  Use for creating, managing, and monitoring DLC training jobs
  and managing reusable job templates.
  Triggers: "DLC", "PAI-DLC", "JobTemplate", "create-job-template",
  "list-job-templates", "set-job-template-default-version",
  "create-tensorboard", "list-tensorboards", "get-dashboard".
---

# PAI-DLC Deep Learning Job Management

Manage deep learning training jobs on Alibaba Cloud PAI-DLC (Platform for AI - Deep
Learning Containers) service.

## Scenario Description

PAI-DLC is a distributed training service provided by Alibaba Cloud's AI Platform PAI,
supporting:

- **Job Creation and Execution** — Create distributed training jobs for TensorFlow,
  PyTorch, XGBoost, and other frameworks
- **Job Monitoring** — Get job status, logs, events, and monitoring metrics
- **Compute Health Check** — Check health status of GPU and other compute devices
- **Job Management** — Update and stop jobs
- **Job Templates** — Save reusable `CreateJob` configurations as templates with
  multi-version management and field constraints

**Architecture**: PAI Workspace + DLC Job + Computing Resources (ECS public pay-as-you-go
or Lingjun dedicated quota) + AIWorkSpace catalog (images / datasets / code sources /
quotas / workspaces).

## Installation Requirements

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify version >= 3.3.1. If not installed or version is too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for
> installation instructions.
> Then [Required] run `aliyun configure set --auto-plugin-install true` to enable
> automatic plugin installation.

> **Note on `--user-agent`:** Every API-invoking `aliyun` command in this skill MUST
> include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job`. Client-side helpers
> (`aliyun version`, `aliyun configure ...`, `aliyun plugin ...`,
> `aliyun <product> --help`) do not invoke remote APIs and therefore do not require
> the flag.

```bash
aliyun version
aliyun configure set --auto-plugin-install true
aliyun pai-dlc --help
# JobTemplate (§7.7) requires aliyun-cli-pai-dlc >= 0.3.1.
# If create-job-template --help fails: aliyun plugin update --name aliyun-cli-pai-dlc
aliyun aiworkspace --help >/dev/null 2>&1 || aliyun plugin install --names aliyun-cli-aiworkspace

aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job"
# After session: aliyun configure ai-mode disable
```

## Environment Variables

This skill does not require any custom environment variables. Credentials are handled
by the Alibaba Cloud CLI configuration (see Authentication below). Optionally:

| Variable | Required | Purpose |
|----------|----------|---------|
| `ALIBABA_CLOUD_PROFILE` | Optional | Selects a non-default `aliyun configure` profile |
| `ALIBABA_CLOUD_REGION_ID` | Optional | Default region when `--region` is omitted (still recommended to pass `--region` explicitly) |

Do NOT export `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` from
within this session; configure them outside (`aliyun configure` or shell profile).

## Authentication Configuration

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal
>    or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## RAM Permissions

> **[MUST] Permission Failure Handling:** When any command or API call fails due to
> permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

For detailed permission list, see [references/ram-policies.md](references/ram-policies.md).

**Required Permissions Overview:**

| Operation | Required Permission |
|-----------|---------------------|
| Create Job | `pai:CreateJob` |
| List Jobs | `pai:ListJobs` |
| Get Job Details | `pai:GetJob` |
| Get Pod Logs | `pai:GetPodLogs` |
| Get Job Events | `pai:GetJobEvents` |
| Get Job Metrics | `pai:GetJobMetrics` |
| Update Job | `pai:UpdateJob` |
| Stop Job | `pai:StopJob` |
| Stop Job | `pai:StopJob` |
| Create / Read / Update Job Template | `paidlc:CreateJobTemplate` / `paidlc:GetJobTemplate` / `paidlc:ListJobTemplates` / `paidlc:UpdateJobTemplate` / `paidlc:SetJobTemplateDefaultVersion` |
| AIWorkSpace Resource Discovery | `paiworkspace:ListWorkspaces` / `paiimage:ListImages,GetImage` / `paidataset:ListDatasets,GetDataset` / `paicodesource:ListCodeSources,GetCodeSource` |

> **AIWorkSpace authorization note:** `Image` / `DataSourceId` / `CodeSourceId` /
> `WorkspaceId` field values for `create-job` come from the
> AIWorkSpace resource-discovery APIs. `--resource-id` (QuotaId) is manually provided by the user.
> RAM users MUST hold the corresponding
> AIWorkSpace-namespaced permissions listed above (do not abbreviate as `aiworkspace:*`).

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

### Parameters Requiring User Confirmation

| Parameter | Required | Notes |
|-----------|----------|-------|
| `--region` | Yes | e.g., `cn-hangzhou` |
| `--workspace-id` | Yes | From `aliyun aiworkspace list-workspaces` |
| `--job-type` | Yes | `PyTorchJob`, `TFJob`, `RayJob`, etc. |
| `--display-name` | Yes | Meaningful name (project + model + date) |
| `--job-specs[].Image` | Yes | Verbatim `ImageUri` from `list-images` (see §7.6 red line) |
| `--user-command` | Yes | e.g., `python train.py` |
| `--job-specs[].EcsSpec` | Conditional | Public pay-as-you-go (mutually exclusive with `ResourceConfig`) |
| `--resource-id` + `ResourceConfig` | Conditional | Dedicated quota path (mutually exclusive with `EcsSpec`). User MUST manually provide the QuotaId.|
| `--data-sources` / `--code-source` | Optional | From `list-datasets` / `list-code-sources` |
| `--template-id` | Conditional | When creating Job from JobTemplate |

For all parameters: `aliyun pai-dlc create-job --help`.

**Mutual exclusion summary:**

- `EcsSpec` and `ResourceConfig` are **mutually exclusive** within a single TaskSpec.
- `Uri` and `DataSourceId` within `--data-sources[]` are mutually exclusive.
- `Uri` and `CodeSourceId` within `--code-source` are mutually exclusive.

For full parameter reference: see [references/related-apis.md](references/related-apis.md).

## Core Workflows

### 7.1 Resource Selection Decision Guide

Before calling `create-job`, determine the resource path:

- **Public pay-as-you-go** → Use `EcsSpec` in TaskSpec; do NOT pass `--resource-id`.
  - Use cases: quick start, testing, no dedicated quota.
  - Example: `"EcsSpec": "ecs.gn6i-c4g1.xlarge"`
- **Dedicated quota** (Lingjun / enterprise quota) → Use `ResourceConfig` in TaskSpec
  AND pass `--resource-id <QuotaId>`.
  - Use cases: dedicated resource group, Lingjun smart compute, Spot bidding.
  - Example: `--resource-id quotaXXX` + `"ResourceConfig": {"CPU": "4", "Memory": "8Gi", "GPU": "1"}`

> **EcsSpec and ResourceConfig MUST NOT both appear in the same TaskSpec.**

> **Also required before `create-job`:** `--job-specs[].Image` MUST come from
> `aliyun aiworkspace list-images`; `--data-sources[].DataSourceId` from
> `list-datasets`; `--code-source.CodeSourceId` from `list-code-sources`.
> Full discovery flow → see §7.6.

**Distributed architecture choices:**

| Topology | `JobSpecs` shape |
|---|---|
| Single-node | One `Worker` only |
| TFJob PS-Worker | Both `PS` (CPU) and `Worker` (GPU) roles |
| PyTorch multi-node | One `Worker` with `PodCount > 1` |

Optional flags: `--enable-gang-scheduling true` (all-or-nothing scheduling),
`Settings.EnableRDMA: true` (high-performance network for multi-node GPU),
`Settings.EnableSanityCheck: true` (GPU health verification).

### 7.2 Create Training Job

```bash
# Minimal single-node PyTorch job (public pay-as-you-go)
aliyun pai-dlc create-job \
  --region <region> \
  --workspace-id <workspace-id> \
  --display-name "my-pytorch-training" \
  --job-type PyTorchJob \
  --job-specs '[{
    "Type": "Worker",
    "PodCount": 1,
    "Image": "<ImageUri-from-aiworkspace-list-images>",
    "EcsSpec": "ecs.gn6i-c4g1.xlarge"
  }]' \
  --user-command 'python train.py' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

For multi-node topologies, see §7.1. For Spot, RDMA, data mounting parameters, use `aliyun pai-dlc create-job --help`.

### 7.3 List / Get Job

```bash
# List running jobs (status filter: Creating/Queuing/Running/Succeeded/Failed/Stopped)
aliyun pai-dlc list-jobs \
  --region <region> \
  --status Running \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Get job detail
aliyun pai-dlc get-job \
  --region <region> \
  --job-id <job-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Get a specific PodId (for log/event queries)
aliyun pai-dlc get-job \
  --region <region> \
  --job-id <job-id> \
  --cli-query "Pods[0].PodId" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

### 7.4 Logs, Events, and Metrics

> **IMPORTANT**: Always limit return size: `--max-lines 100` for logs, `--max-events-num 50` for events.

```bash
# Get PodId first, then query logs/events/metrics
POD_ID=$(aliyun pai-dlc get-job --region <region> --job-id <job-id> \
  --cli-query "Pods[0].PodId" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job)

aliyun pai-dlc get-pod-logs --region <region> --job-id <job-id> --pod-id $POD_ID --max-lines 100 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
aliyun pai-dlc get-pod-events --region <region> --job-id <job-id> --pod-id $POD_ID --max-events-num 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
aliyun pai-dlc get-job-events --region <region> --job-id <job-id> --max-events-num 50 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
aliyun pai-dlc get-job-metrics --region <region> --job-id <job-id> --metric-type GpuCoreUsage --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

**Metric types:** `GpuCoreUsage`, `GpuMemoryUsage`, `CpuCoreUsage`, `MemoryUsage`, `NetworkInputRate`, `NetworkOutputRate`, `DiskReadRate`, `DiskWriteRate`.

**Diagnosis order:** `get-job` (status) → `get-job-events` → `get-pod-logs` → `get-pod-events`.

### 7.5 Compute Health Check

```bash
# All sanity check results
aliyun pai-dlc list-job-sanity-check-results \
  --region <region> \
  --job-id <job-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Single sanity check result
aliyun pai-dlc get-job-sanity-check-result \
  --region <region> \
  --job-id <job-id> \
  --sanity-check-number 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

### 7.6 Pre-Create Resource Discovery (AIWorkSpace)

**Discovery flow:** `list-workspaces` → `list-image-labels` →
`list-images` → `list-datasets` → `list-code-sources` → `pai-dlc create-job`.

> **Quota (--resource-id):** User MUST manually provide the QuotaId. No CLI discovery step.

```bash
# Step 1: Pick a workspace (yields --workspace-id)
aliyun aiworkspace list-workspaces \
  --region <region> --page-number 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Step 2: Discover available image labels (MUST run before list-images)
# list-image-labels returns all label Key-Value pairs available in this region.
# Use this to discover valid --labels filters for list-images.
aliyun aiworkspace list-image-labels \
  --region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# How to use list-image-labels results:
# - Extract label Keys (e.g. system.chipType, system.framework, system.cudaVersion)
#   and their available Values to construct --labels filters
# - Multiple labels can be combined with comma: --labels "key1=val1,key2=val2"
# - Labels format: --labels "Key=Value" (single key-value pair), NOT JSON or spaces

# Step 3: Pick an image (yields WorkerSpec.Image / --job-specs[].Image)
# Labels MUST come from list-image-labels output — NEVER guess or invent label values
# NOTE: Do NOT pass --workspace-id to list-images; official images are global
aliyun aiworkspace list-images \
  --region <region> \
  --labels "<Key1=Value1,Key2=Value2>" \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# RED LINE: --job-specs[].Image MUST be a verbatim ImageUri from list-images.
# NEVER invent, rewrite, or copy Name/ImageId instead of ImageUri.

# Step 4: Pick a dataset (yields DataSources[].DataSourceId)
aliyun aiworkspace list-datasets \
  --region <region> --workspace-id <workspace-id> --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Step 5: Pick a code source (yields CodeSource.CodeSourceId)
aliyun aiworkspace list-code-sources \
  --region <region> --workspace-id <workspace-id> --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

> **Red line (also applies in Section 7.7):** Do NOT fall back to ROA generic
> invocations (`--pathPattern` / `--method GET|POST|PUT|DELETE`) when a plugin
> is missing or returns an error. Install/upgrade the plugin instead.

Field-mapping, full parameters, and error codes: see
[references/related-apis.md](references/related-apis.md) and
[references/verification-method.md](references/verification-method.md).

### 7.7 JobTemplate Management (Reusable Templates)

JobTemplate stores a `CreateJob` configuration (`JobSpecs`, `UserCommand`,
`DataSources`, etc.) as a versioned, reusable template. Six subcommands are
exposed by `aliyun-cli-pai-dlc` >= 0.3.1:
`create-job-template`, `get-job-template`, `list-job-templates`,
`update-job-template`, `set-job-template-default-version`. A Job can be launched from a template via
`aliyun pai-dlc create-job --template-id <id>`.

> **Constraints format:** When passing `--constraints`, use escaped-quote JSON:
> `--constraints '{\"JobSpecs[0].Image\":\"locked\",\"UserCommand\":\"locked\"}'`.

For full CRUD workflow, Constraints semantics, JSONPath rules, and pitfalls, see
[references/job-template-management.md](references/job-template-management.md).

### 7.8 Job Lifecycle Management (Stop / Update / Web Terminal)

Stop is a **high-risk** operation. Before proceeding, query status with
`get-job`, present the result to the user, and require explicit confirmation.

- Stop Job: applicable only when status is `Running` or `Queuing`.

For the full pre-check + confirmation + execution templates, plus the
`update-job` low-risk path and `get-web-terminal` / `get-token` sharing
commands, see [references/job-management.md](references/job-management.md).

### 7.9 Ecs Spec Discovery

Discover available instance types before choosing `EcsSpec` in `--job-specs`.
Results from `list-ecs-specs` provide the exact `EcsSpec` value to use.

```bash
# GPU public pay-as-you-go instances
aliyun pai-dlc list-ecs-specs \
  --region <region> \
  --accelerator-type GPU \
  --resource-type ECS \
  --sort-by GPU \
  --order desc \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Lingjun dedicated instances
# Note: --quota-id is only available for whitelisted users
```

Copy the returned `EcsSpec` value verbatim into `--job-specs[].EcsSpec`.
For full parameters see `aliyun pai-dlc list-ecs-specs --help`.

### 7.10 Tensorboard Management

TensorBoard visualizes training metrics. Seven subcommands under `aliyun pai-dlc`:
`create-tensorboard`, `list-tensorboards`, `get-tensorboard`, `start-tensorboard`,
`stop-tensorboard`, `update-tensorboard`, `get-tensorboard-shared-url`.

> `--job-id` and `--data-sources` are mutually exclusive in create.

```bash
# Create from a job (most common)
aliyun pai-dlc create-tensorboard \
  --region <region> \
  --job-id <job-id> \
  --display-name "my-training-tb" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Create from a dataset summary path
aliyun pai-dlc create-tensorboard \
  --region <region> \
  --data-sources '[{"DataSourceId":"<dataset-id>","MountPath":"/mnt/logs"}]' \
  --summary-path /mnt/logs \
  --display-name "dataset-tb" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

For full parameters and lifecycle, see [references/related-apis.md](references/related-apis.md)
TensorBoard section.

### 7.11 Dashboard & Ray Dashboard

Both `get-dashboard` and `get-ray-dashboard` return a URL only for `RayJob` type
jobs. For non-Ray jobs, the response is empty.

```bash
# Generic DLC dashboard (RayJob only)
aliyun pai-dlc get-dashboard \
  --region <region> \
  --job-id <job-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Ray-specific dashboard with optional sharing
aliyun pai-dlc get-ray-dashboard \
  --region <region> \
  --job-id <job-id> \
  --is-shared true \
  --token <sharing-token> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

For shared access, first obtain a token via `get-token --target-type job`,
then pass it to `get-ray-dashboard --token <token> --is-shared true`.

## Success Verification Method

For step-by-step end-to-end verification scripts (resource discovery →
CreateJob → log query → cleanup, plus JobTemplate CRUD verification), see
[references/verification-method.md](references/verification-method.md).

**Quick verification:**

- `get-job` → Status should be `Creating` / `Queuing` / `Running` shortly after
  `create-job` returns.
- `list-jobs --status Running` → Should return the freshly created Job until it
  finishes or is stopped.
- `get-pod-logs` → Should return non-empty log content once the Pod is past
  `EnvPreparing`.

## Command Tables

A flat list of every CLI command used by this skill (Product / Command /
Description) is in [references/related-commands.md](references/related-commands.md).

## Best Practices

1. **Job Naming Convention** — Use meaningful names containing project, model,
   and date, e.g., `resnet50-imagenet-20260320`.
2. **Resource Configuration Optimization** — Choose appropriate GPU type and
   quantity based on model size and dataset size.
3. **Log Monitoring** — Periodically check logs and events to detect failures
   early.
4. **Priority Management** — Set higher priority for critical jobs (1-9, 9 highest).
5. **Cost Control** — Spot instances reduce cost at the risk of preemption; use
   `--job-max-running-time-minutes` as an auto-stop guard for any long-running
   experiment.
6. **Health Check** — Enable `Settings.EnableSanityCheck: true` to verify GPU
   devices before training starts.
7. **Resource Cleanup** — Stop completed jobs promptly to free resource quotas.
8. **Template Reuse** — Capture standardized training pipelines as JobTemplates;
   mark `Image` / `DataSources` as `locked` and `UserCommand` / `Envs` as
   `overridable` so consumers focus on business parameters via
   `create-job --template-id`.
9. **TensorBoard Monitoring** — Attach a TensorBoard instance to training jobs for
   real-time metric visualization.
10. **Ecs Spec Discovery** — Run `list-ecs-specs --accelerator-type GPU` before
    choosing `EcsSpec` to confirm which instance types are available in the region.

## Reference Links

| Reference Document | Description |
|--------------------|-------------|
| [references/related-apis.md](references/related-apis.md) | Complete API and CLI command reference |
| [references/related-commands.md](references/related-commands.md) | Flat list of all CLI commands |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policy details |
| [references/verification-method.md](references/verification-method.md) | End-to-end verification scripts |
| [references/job-management.md](references/job-management.md) | High-risk Stop/Delete/Update flow + Web Terminal |
| [references/job-template-management.md](references/job-template-management.md) | JobTemplate CRUD + Constraints + version management |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Skill testing acceptance criteria |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
