---
name: alibabacloud-pai-dlc-job
description: |
  Alibaba Cloud PAI-DLC (Deep Learning Containers) job management skill.
  Covers: distributed training job CRUD, monitoring (logs and events), and
  GPU sanity check.
  Triggers: "DLC", "PAI-DLC", "create-job", "list-jobs", "get-job",
  "stop-job", "update-job", "get-pod-logs", "get-job-events",
  "get-pod-events", "list-job-sanity-check-results".
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
aliyun aiworkspace --help >/dev/null 2>&1 || aliyun plugin install --names aliyun-cli-aiworkspace
aliyun plugin update

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
| Update Job | `pai:UpdateJob` |
| Stop Job | `pai:StopJob` |
| AIWorkSpace Resource Discovery | `paiworkspace:ListWorkspaces` / `paiimage:ListImages,GetImage` / `paidataset:ListDatasets,GetDataset` / `paicodesource:ListCodeSources,GetCodeSource` |

> **AIWorkSpace authorization note:** `Image` / `DataSourceId` / `CodeSourceId` /
> `WorkspaceId` field values for `create-job` come from the
> AIWorkSpace resource-discovery APIs. `--resource-id` (QuotaId) is manually provided by the user.
> RAM users MUST hold the corresponding
> AIWorkSpace-namespaced permissions listed above (do not abbreviate as `aiworkspace:*`).

## Parameter Confirmation

> **Authoritative parameter reference is `aliyun pai-dlc <cmd> --help`** (must-read
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
| `RayJob` | `Worker` |
| `SlurmJob` / `DataJuicerJob` | framework-specific roles |

> **Case-sensitive, no aliases.** `tensorflow`, `pytorch`, `tf-job`, `Pytorch`,
> `PYTORCH_JOB`, `Custom`, `CustomJob` — all rejected.
>
> **No `Custom` enum.** For single-container custom workloads, map to
> `PyTorchJob` (most permissive role set).
>
> **Locked after create:** `JobType` cannot be changed via `update-job`.

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
  --user-command 'python train.py' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

Multi-node / Spot / RDMA / data mounting — use `create-job --help`.
Subsequent snippets omit `--user-agent` for brevity — always include it.

### 7.3 List / Get Job

Use `--cli-query` to project specific fields (essential for log/event flows):

```bash
aliyun pai-dlc list-jobs --region <region> --status Running
aliyun pai-dlc get-job  --region <region> --job-id <id>
aliyun pai-dlc get-job  --region <region> --job-id <id> --cli-query "Pods[0].PodId"
```

### 7.4 Logs and Events

> **Always cap return size:** `--max-lines 100` (logs), `--max-events-num 50` (events).

Get `PodId` first, then query logs/events:

```bash
POD_ID=$(aliyun pai-dlc get-job --region <r> --job-id <id> --cli-query "Pods[0].PodId")
aliyun pai-dlc get-pod-logs    --region <r> --job-id <id> --pod-id $POD_ID --max-lines 100
aliyun pai-dlc get-pod-events  --region <r> --job-id <id> --pod-id $POD_ID --max-events-num 20
aliyun pai-dlc get-job-events  --region <r> --job-id <id> --max-events-num 50
```

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
> Do **not** pass `--workspace-id` to `list-images` when discovering **official
> public images** (they are global). Pass `--workspace-id` only when filtering
> **custom / private images** scoped to a specific workspace.
>
> **RED LINE:** `--job-specs[].Image` MUST be a verbatim `ImageUri` (not
> `Name` / `ImageId`).
>

Field-mapping, full parameters, and error codes: see
[references/related-apis.md](references/related-apis.md) and
[references/verification-method.md](references/verification-method.md).

### 7.7 Job Lifecycle Management (Stop / Update / Web Terminal)

Stop is a **high-risk** operation. Before proceeding, query status with
`get-job`, present the result to the user, and require explicit confirmation.

> **Rules `--help` doesn't tell you (`update-job` silent-no-op family):**
>
> - **Stop Job** applies only when status is `Running` or `Queuing`.
> - **`update-job --priority`** takes effect **only** when (a) the job uses
>   **quota resources** (`--resource-id`) AND (b) status is `Creating`,
>   `Queuing`, or `EnvPreparing`. Once the job enters `Running` or later,
>   priority **cannot be modified** — the API returns `200 OK` but the change
>   is **silently NOT applied**. Always pre-check status with `get-job`.
> - **`update-job --accessibility`** takes effect immediately in any status.
> - **`update-job` does NOT expose `--display-name`** (`--help` lists only
>   `--job-id`, `--accessibility`, `--description`, `--job-specs`, `--priority`).
>   To rename a job, recreate it.

For the full pre-check + confirmation + execution templates, plus the
`update-job` low-risk path and `get-web-terminal` / `get-token` sharing
commands, see [references/job-management.md](references/job-management.md).

### 7.8 Ecs Spec Discovery

Discover available instance types; the returned `EcsSpec` value goes
verbatim into `--job-specs[].EcsSpec`.

```bash
aliyun pai-dlc list-ecs-specs --region <r> --accelerator-type GPU --resource-type ECS --page-size 20
# Lingjun dedicated: --quota-id <id> (whitelisted users only)
```

> **`list-ecs-specs` does not support `--sort-by`** — even values shown as
> valid in `--help` (e.g. `CPU` / `GPU` / `Memory` / `GmtCreateTime`) are
> rejected by the server. Always omit `--sort-by` here and sort the JSON
> output client-side with `jq` — e.g.
> `... | jq '.EcsSpecs | sort_by(-.AcceleratorNumber)'`.

## Success Verification Method

For step-by-step end-to-end verification scripts (resource discovery →
CreateJob → log query → cleanup), see
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
   `EcsSpec` (see §7.8).
3. **Diagnose early** — follow the order `get-job` → `get-job-events` →
   `get-pod-logs` → `get-pod-events`. Cap responses (`--max-lines 100`,
   `--max-events-num 50`) to keep agent context lean.
4. **Priority adjustment** — prefer setting `--priority` at `create-job` time.
   Post-creation `update-job --priority` only works for quota jobs in
   `Creating` / `Queuing` / `EnvPreparing` phase (§7.7); once `Running`,
   priority cannot be modified.
5. **Cost control** — use `--job-max-running-time-minutes` as an auto-stop guard
   for every long-running experiment. Spot via `SpotSpec` reduces cost at the
   risk of preemption.
6. **Health check** — enable `Settings.EnableSanityCheck: true` for GPU
   training to catch faulty devices before training starts.
7. **Resource cleanup** — `stop-job` on completed jobs to free quota.
8. **Idempotency on writes** — PAI-DLC `create-*` APIs do **NOT** expose
   `--client-token` (verified via `aliyun pai-dlc create-job --help`). Network
   retries can therefore create duplicate Jobs. Mitigation: before re-issuing
   a failed `create-*`, run `list-jobs --display-name <name>` to detect a
   half-committed prior attempt.

## Reference Links

| Reference Document | Description |
|--------------------|-------------|
| [references/related-apis.md](references/related-apis.md) | Command index, cross-product field map, lifecycle, red lines, error catalog |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policy details |
| [references/verification-method.md](references/verification-method.md) | End-to-end verification scripts |
| [references/job-management.md](references/job-management.md) | High-risk Stop/Delete/Update flow + Web Terminal |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Skill testing acceptance criteria |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
