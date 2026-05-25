---
name: alibabacloud-pai-dlc-job
description: |
  Alibaba Cloud PAI-DLC (Deep Learning Containers) job management skill.
  Covers: distributed training job CRUD, JobTemplate (versioned reusable
  configs), TensorBoard lifecycle (create / start / stop / update / share),
  Ray & generic Dashboards, plus monitoring (logs / events / metrics) and
  GPU sanity check.
  Triggers: "DLC", "PAI-DLC", "JobTemplate", "create-job-template",
  "list-job-templates", "set-job-template-default-version",
  "create-tensorboard", "list-tensorboards", "start-tensorboard",
  "stop-tensorboard", "update-tensorboard", "get-tensorboard-shared-url",
  "get-dashboard", "get-ray-dashboard".
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

> **Network timeout & retry (rule `--help` doesn't enforce):** `aliyun` CLI
> defaults to 10s connect / 10s read with no retry. For long-running flows
> (large list, slow region) explicitly raise via global flags
> `--connect-timeout 15 --read-timeout 30 --retry-count 2`. Never rely on the
> default for user-confirmed high-risk calls (`stop-job` / `delete-*`).

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

> **Authoritative parameter reference is `aliyun pai-dlc <cmd> --help`** (必读
> before every call). This skill only documents what `--help` does **not** tell
> you: cross-field rules, cross-product dependencies, hidden behaviors, business
> labels, and reject patterns. Whenever a rule below contradicts `--help`, the
> reason is stated inline.
>
> **Confirm before call:** all user-customizable values (region, names, CIDR,
> specs, etc.) MUST be confirmed with the user — never assume defaults.

### Hard rules that override `--help`

| Rule | Why this skill overrides `--help` |
|------|-----------------------------------|
| `--workspace-id` is **always required** | `--help` marks it optional, but server silently falls back to the user's **default workspace** if omitted → job often lands in the wrong workspace. Always confirm with user. |
| `--job-specs[].Image` MUST be a verbatim `ImageUri` from `aiworkspace list-images` | Cross-product contract; `--help` only describes the field type. See §7.6 red line. |
| `--data-sources[].DataSourceId` from `aiworkspace list-datasets`; `--code-source.CodeSourceId` from `list-code-sources` | Cross-product discovery; `--help` cannot point you to the source product. |
| `--resource-id` (QuotaId) is **manually supplied** | No CLI discovery step. |

### Cross-field mutual exclusion (`--help` cannot catch these)

- `EcsSpec` ⇄ `ResourceConfig` — within a single TaskSpec, pick exactly one.
- `Uri` ⇄ `DataSourceId` — within `--data-sources[]`.
- `Uri` ⇄ `CodeSourceId` — within `--code-source`.

### `--job-type` — Worker `Type` hints per framework

`--help` lists the 9 legal enum values verbatim. What `--help` doesn't tell you
is which `JobSpecs[].Type` roles each framework expects:

| `--job-type` | Valid `JobSpecs[].Type` roles |
|---|---|
| `TFJob` | `Chief` / `PS` / `Worker` / `Evaluator` / `GraphLearn` |
| `PyTorchJob` | `Worker` (+ optional `Master`, auto-promoted) |
| `MPIJob` | `Worker` + `Master` |
| `XGBoostJob` / `OneFlowJob` / `ElasticBatchJob` | `Worker` + optional `Master` |
| `RayJob` | `Worker` (required for `get-dashboard` / `get-ray-dashboard`) |
| `SlurmJob` / `DataJuicerJob` | framework-specific roles |

> **Case-sensitive, no aliases.** `tensorflow`, `pytorch`, `tf-job`, `Pytorch`,
> `PYTORCH_JOB`, `Custom`, `CustomJob` — all rejected.
>
> **No `Custom` enum.** For single-container custom workloads, map to
> `PyTorchJob` (most permissive role set).
>
> **Locked after create:** `JobType` cannot be changed via `update-job`. With
> `--template-id`, the template's `JobType` wins.

Full field reference: see [references/related-apis.md](references/related-apis.md).

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

> **All commands below require `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job`** (omitted in snippets for brevity — see Installation Requirements).

### 7.2 Create Training Job

Minimal single-node PyTorch job (public pay-as-you-go) parameter combination:

```bash
aliyun pai-dlc create-job --region <region> --workspace-id <ws-id> \
  --display-name "my-pytorch-training" --job-type PyTorchJob \
  --job-specs '[{"Type":"Worker","PodCount":1,"Image":"<ImageUri>","EcsSpec":"ecs.gn6i-c4g1.xlarge"}]' \
  --user-command 'python train.py'
```

Multi-node / Spot / RDMA / data mounting — use `create-job --help`.

### 7.3 List / Get Job

Use `--cli-query` to project specific fields (essential for log/event flows):

```bash
aliyun pai-dlc list-jobs --region <region> --status Running
aliyun pai-dlc get-job  --region <region> --job-id <id>
aliyun pai-dlc get-job  --region <region> --job-id <id> --cli-query "Pods[0].PodId"
```

### 7.4 Logs, Events, and Metrics

> **Always cap return size:** `--max-lines 100` (logs), `--max-events-num 50` (events).

Get `PodId` first, then query logs/events/metrics:

```bash
POD_ID=$(aliyun pai-dlc get-job --region <r> --job-id <id> --cli-query "Pods[0].PodId")
aliyun pai-dlc get-pod-logs    --region <r> --job-id <id> --pod-id $POD_ID --max-lines 100
aliyun pai-dlc get-pod-events  --region <r> --job-id <id> --pod-id $POD_ID --max-events-num 20
aliyun pai-dlc get-job-events  --region <r> --job-id <id> --max-events-num 50
aliyun pai-dlc get-job-metrics --region <r> --job-id <id> --metric-type GpuCoreUsage
```

> `--metric-type` 8 valid enum values + default time window: see
> `aliyun pai-dlc get-job-metrics --help`.

**Diagnosis order:** `get-job` (status) → `get-job-events` → `get-pod-logs` → `get-pod-events`.

### 7.5 Compute Health Check

```bash
aliyun pai-dlc list-job-sanity-check-results --region <r> --job-id <id>
aliyun pai-dlc get-job-sanity-check-result   --region <r> --job-id <id> --sanity-check-number 1
```

### 7.6 Pre-Create Resource Discovery (AIWorkSpace)

**Discovery flow:** `list-workspaces` → `list-image-labels` →
`list-images` → `list-datasets` → `list-code-sources` → `pai-dlc create-job`.

> **Quota (`--resource-id`):** user-supplied. No CLI discovery step.

```bash
aliyun aiworkspace list-workspaces     --region <r>                        # → --workspace-id
aliyun aiworkspace list-image-labels   --region <r>                        # → valid label Key=Value pairs
aliyun aiworkspace list-images         --region <r> --labels "K1=V1,K2=V2" # → --job-specs[].Image (use ImageUri verbatim)
aliyun aiworkspace list-datasets       --region <r> --workspace-id <ws>    # → DataSources[].DataSourceId
aliyun aiworkspace list-code-sources   --region <r> --workspace-id <ws>    # → CodeSource.CodeSourceId
```

> **Labels rules** (not in `--help`): comma-separated `Key=Value` pairs, no
> JSON / no spaces. Values MUST come from `list-image-labels` — never invent.
> Do **not** pass `--workspace-id` to `list-images` (official images are global).
>
> **RED LINE:** `--job-specs[].Image` MUST be a verbatim `ImageUri` (not
> `Name` / `ImageId`).
>
> **No ROA fallback** (also applies to §7.7): if a plugin subcommand is
> missing, install/upgrade the plugin — never use `--pathPattern` /
> `--method GET|POST|PUT|DELETE`.

Field-mapping, full parameters, and error codes: see
[references/related-apis.md](references/related-apis.md) and
[references/verification-method.md](references/verification-method.md).

### 7.7 JobTemplate Management (Reusable Templates)

JobTemplate stores a `CreateJob` configuration (`JobSpecs`, `UserCommand`,
`DataSources`, etc.) as a versioned, reusable template. Six subcommands under
`aliyun pai-dlc` (full params: each subcommand's `--help`):
`create-job-template` / `get-job-template` / `list-job-templates` /
`update-job-template` / `set-job-template-default-version` /
`delete-job-template`. Launch a Job from a template via
`aliyun pai-dlc create-job --template-id <id>`.

> **Rules `--help` doesn't (clearly) tell you:**
>
> - **`--constraints` must be bash-escaped JSON**, e.g.
>   `--constraints '{\"JobSpecs[0].Image\":\"locked\",\"UserCommand\":\"locked\"}'`.
>   Constraint values ∈ `locked` / `overridable` / `required` (semantics in
>   [references/job-template-management.md](references/job-template-management.md)).
> - **`update-job-template`: `--constraints` cannot be passed alone** — `--help`
>   states it "must be specified with `Content` and cannot be updated on its own".
>   Each `--content` push creates a new version; pair `--set-as-default true` to
>   promote it.
> - **`get-job-template --biz-version all`** returns every version (omit → default
>   version only). Useful for auditing version history.
> - **`delete-job-template` is blocked when the template is referenced by any
>   job** (per `--help` description). Clean up referencing jobs first, or use a
>   never-referenced template for delete tests.
> - **`Content` is a JSON string** (OpenAPI contract, `--help` confirms). Server
>   stores it verbatim; `get-job-template` returns `Versions[0].Content` as a
>   JSON string with outer quotes — to inspect inner fields, parse with `jq`.
>   `create-job --template-id` consumes it directly, no manual parsing needed.
> - **`list-job-templates --sort-by`** — `--help` doesn't list the enum; default
>   `GmtCreateTime` is safe, other field names are not publicly documented.

For full CRUD workflow, Constraints semantics, and JSONPath rules, see
[references/job-template-management.md](references/job-template-management.md).

### 7.8 Job Lifecycle Management (Stop / Update / Web Terminal)

Stop is a **high-risk** operation. Before proceeding, query status with
`get-job`, present the result to the user, and require explicit confirmation.

> **Rules `--help` doesn't tell you (`update-job` silent-no-op family):**
>
> - **Stop Job** applies only when status is `Running` or `Queuing`.
> - **`update-job --priority`** takes effect **only** when (a) the job uses
>   **quota resources** (`--resource-id`) AND (b) is still in submission
>   phase — `Creating` or `Queuing`. Change is applied asynchronously, typically
>   in 10–60 seconds. Public pay-as-you-go (`EcsSpec`) jobs and jobs past the
>   submission phase (`EnvPreparing` / `Running` / …) receive `200 OK` but the
>   priority is **silently NOT applied** — always pre-check status with `get-job`.
> - **`update-job --accessibility`** takes effect immediately in any status.
> - **`update-job` does NOT expose `--display-name`** (`--help` lists only
>   `--job-id`, `--accessibility`, `--description`, `--job-specs`, `--priority`).
>   To rename a job, recreate it.

For the full pre-check + confirmation + execution templates, plus the
`update-job` low-risk path and `get-web-terminal` / `get-token` sharing
commands, see [references/job-management.md](references/job-management.md).

### 7.9 Ecs Spec Discovery

Discover available instance types; the returned `EcsSpec` value goes
verbatim into `--job-specs[].EcsSpec`.

```bash
aliyun pai-dlc list-ecs-specs --region <r> --accelerator-type GPU --resource-type ECS --page-size 20
# Lingjun dedicated: --quota-id <id> (whitelisted users only)
```

> **`--sort-by` enum (per `--help`):** `CPU` / `GPU` / `Memory` /
> `GmtCreateTime` — note **upper-case** `CPU` / `GPU`. Lowercase or arbitrary
> field names → `BadRequest`. Fallback: omit `--sort-by`, sort client-side
> with `jq -r '.EcsSpecs | sort_by(-.AcceleratorNumber)'`.

### 7.10 Tensorboard Management

TensorBoard visualizes training metrics. 8 subcommands under `aliyun pai-dlc`
(`create-tensorboard`, `list-tensorboards`, `get-tensorboard`,
`start-tensorboard`, `stop-tensorboard`, `update-tensorboard`,
`get-tensorboard-shared-url`, `delete-tensorboard`).

> **Rules `--help` doesn't tell you:**
>
> - **`--job-id` ⇄ `--data-sources`** in `create-tensorboard` — mutually exclusive.
> - **`--data-sources` vs `--tensorboard-data-sources`** in `create-tensorboard`:
>   - `--data-sources [{DataSourceId, MountPath}]` mounts an **existing**
>     workspace dataset. **`Uri` silently ignored** even if passed.
>   - `--tensorboard-data-sources [{SourceType, Uri}]` is for raw
>     `Uri` (OSS / NAS / CPFS) without a pre-registered dataset.
>   - Pick the parameter that matches your input; never stuff `Uri` into
>     `--data-sources`.
> - **`update-tensorboard` does NOT expose `--display-name`** (`--help` lists
>   only `--tensorboard-id` / `--accessibility` / `--max-running-time-minutes`
>   / `--priority` / `--workspace-id`). To rename, recreate.

```bash
# From a job (most common)
aliyun pai-dlc create-tensorboard --region <r> --job-id <id> --display-name "my-tb"
# From a dataset summary path
aliyun pai-dlc create-tensorboard --region <r> \
  --data-sources '[{"DataSourceId":"<id>","MountPath":"/mnt/logs"}]' \
  --summary-path /mnt/logs --display-name "dataset-tb"
```

Full parameters / lifecycle: see
[references/related-apis.md](references/related-apis.md) §1.3.

### 7.11 Dashboard & Ray Dashboard

`get-dashboard` / `get-ray-dashboard` return a URL **only for `RayJob`**;
other job types return empty.

```bash
aliyun pai-dlc get-dashboard     --region <r> --job-id <id>
aliyun pai-dlc get-ray-dashboard --region <r> --job-id <id> --is-shared true --token <t>
```

For shared access, obtain `<t>` via `get-token --target-type job` first.

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

The full command index (5 categories × ~40 commands, with plugin
attribution) is consolidated in
[references/related-apis.md](references/related-apis.md) §1.

## Best Practices

> Items below are **decision rules** and **operational habits** — not parameter
> values (those live in `--help`).

1. **Job naming** — use meaningful, sortable names: `project-model-date`
   (e.g. `resnet50-imagenet-20260320`). Recreate (not `update-job`) is the
   only way to rename.
2. **Resource sizing** — pick GPU type / count by model & dataset size. Verify
   availability with `list-ecs-specs --accelerator-type GPU` **before** picking
   `EcsSpec` (see §7.9).
3. **Diagnose early** — follow the order `get-job` → `get-job-events` →
   `get-pod-logs` → `get-pod-events`. Cap responses (`--max-lines 100`,
   `--max-events-num 50`) to keep agent context lean.
4. **Priority adjustment** — prefer setting `--priority` at `create-job` time.
   Post-creation `update-job --priority` only works for quota jobs in
   `Creating` / `Queuing` phase (§7.8); otherwise it silently no-ops.
5. **Cost control** — use `--job-max-running-time-minutes` as an auto-stop guard
   for every long-running experiment. Spot via `SpotSpec` reduces cost at the
   risk of preemption.
6. **Health check** — enable `Settings.EnableSanityCheck: true` for GPU
   training to catch faulty devices before training starts.
7. **Resource cleanup** — `stop-job` on completed jobs to free quota; clean up
   TensorBoards via `delete-tensorboard` once analysis is done.
8. **Template reuse** — capture standardized pipelines as JobTemplates. Mark
   `Image` / `DataSources` as `locked` and `UserCommand` / `Envs` as
   `overridable` so consumers focus on business parameters via
   `create-job --template-id` (§7.7).
9. **TensorBoard wiring** — prefer `create-tensorboard --job-id` (auto-discovers
   summary path). Use `--tensorboard-data-sources` only when pointing at a raw
   `Uri` outside any workspace dataset (§7.10).
10. **Idempotency on writes** — PAI-DLC `create-*` APIs do **NOT** expose
    `--client-token` (verified via `aliyun pai-dlc create-job --help`). Network
    retries can therefore create duplicate Jobs / Templates / TensorBoards.
    Mitigation: before re-issuing a failed `create-*`, run `list-jobs
    --display-name <name>` (or `list-job-templates --workspace-id <ws>`) to
    detect a half-committed prior attempt.

## Reference Links

| Reference Document | Description |
|--------------------|-------------|
| [references/related-apis.md](references/related-apis.md) | Command index, cross-product field map, lifecycle, red lines, error catalog |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policy details |
| [references/verification-method.md](references/verification-method.md) | End-to-end verification scripts |
| [references/job-management.md](references/job-management.md) | High-risk Stop/Delete/Update flow + Web Terminal |
| [references/job-template-management.md](references/job-template-management.md) | JobTemplate CRUD + Constraints + version management |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Skill testing acceptance criteria |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
