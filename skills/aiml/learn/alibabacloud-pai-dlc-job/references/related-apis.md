# PAI-DLC API & CLI Reference

> **Single source of truth** for everything `aliyun pai-dlc <cmd> --help` and
> `aliyun aiworkspace <cmd> --help` do **not** tell you: command index across
> products, cross-product field contracts, status lifecycle, red lines,
> Constraints semantics, error catalog, forbidden patterns.
>
> For parameter-level details (flags, types, defaults, enums) — always run
> `--help` on the subcommand. This document never duplicates `--help` output.
>
> Every API-invoking call MUST include
> `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job`. Client-side
> helpers (`version` / `configure` / `plugin` / `--help`) do not invoke remote
> APIs and do not need the flag.

---

## 1. Command Index

### 1.1 Client-Side Helpers (no API call)

| CLI Command | Purpose |
|-------------|---------|
| `aliyun version` | Verify CLI ≥ 3.3.1 |
| `aliyun configure list` | Inspect profiles (never echoes AK/SK) |
| `aliyun configure set --auto-plugin-install true` | Enable auto plugin install |
| `aliyun plugin list` / `install --names ...` / `update --name ...` | Plugin management |
| `aliyun pai-dlc --help` / `aliyun aiworkspace --help` | Probe plugin presence |
| `aliyun pai-dlc <subcommand> --help` | Authoritative parameter reference |

### 1.2 PAI-DLC Job APIs (`pai-dlc` plugin, API 2020-12-03)

| CLI | Action | One-liner |
|-----|--------|-----------|
| `create-job` | CreateJob | Submit a distributed training job |
| `list-jobs` | ListJobs | List jobs with `--status` / `--workspace-id` filters |
| `get-job` | GetJob | Full job detail (use `--need-detail` for advanced fields) |
| `update-job` | UpdateJob | Mutate priority / accessibility / description / job-specs |
| `stop-job` | StopJob | Stop a `Running` / `Queuing` job (high-risk) |
| `get-pod-logs` | GetPodLogs | Container logs (always cap with `--max-lines`) |
| `get-pod-events` | GetPodEvents | Pod-level Kubernetes events |
| `get-job-events` | GetJobEvents | Job-level system events |
| `get-job-metrics` | GetJobMetrics | GPU / memory / network metrics |
| `list-job-sanity-check-results` / `get-job-sanity-check-result` | SanityCheck | GPU health-check results |
| `list-ecs-specs` | ListEcsSpecs | Discover available ECS / Lingjun machine types |
| `get-web-terminal` | GetWebTerminal | Web Terminal URL (Pod must be alive) |
| `get-token` | GetToken | Read-only sharing token for jobs / TensorBoards |

### 1.3 PAI-DLC TensorBoard APIs (`pai-dlc` plugin)

| CLI | Action | One-liner |
|-----|--------|-----------|
| `create-tensorboard` | CreateTensorboard | From a job (`--job-id`) **or** dataset (`--data-sources`) — mutually exclusive |
| `get-tensorboard` / `list-tensorboards` | Get/List | Single instance / list with filters |
| `start-tensorboard` / `stop-tensorboard` | Lifecycle | Start a stopped instance / stop a running one |
| `update-tensorboard` | UpdateTensorboard | Mutate `accessibility` / `max-running-time-minutes` / `priority` / `workspace-id` |
| `get-tensorboard-shared-url` | Shared URL | Time-limited shareable link |
| `delete-tensorboard` | Delete | Permanent removal |
| `get-dashboard` / `get-ray-dashboard` | Dashboards | URL non-empty only for `RayJob` |

### 1.4 PAI-DLC JobTemplate APIs (`pai-dlc` plugin ≥ 0.3.1)

| CLI | Action | One-liner |
|-----|--------|-----------|
| `create-job-template` | CreateJobTemplate | First version is `Version=1`, `DefaultVersion=1` |
| `get-job-template` | GetJobTemplate | Add `--biz-version all` for full history |
| `list-job-templates` | ListJobTemplates | Per-workspace catalog |
| `update-job-template` | UpdateJobTemplate | Metadata-only OR new content version |
| `set-job-template-default-version` | SetDefaultVersion | Switch which version `create-job --template-id` uses |
| `delete-job-template` | DeleteJobTemplate | Blocked while any job still references the template |

### 1.5 AIWorkSpace Resource Discovery (`aiworkspace` plugin, API 2021-02-04)

| CLI | Returns | Maps to CreateJob field |
|-----|---------|-------------------------|
| `list-workspaces` | `Workspaces[].WorkspaceId` | `--workspace-id` |
| `list-image-labels` | label `Key=Value` pairs | input for `list-images --labels` |
| `list-images` / `get-image` | `Images[].ImageUri` | `--job-specs[].Image` |
| `list-datasets` / `get-dataset` | `Datasets[].DatasetId` | `--data-sources[].DataSourceId` |
| `list-code-sources` / `get-code-source` | `CodeSources[].CodeSourceId` | `--code-source.CodeSourceId` |

> **Quota (`--resource-id`)** is user-supplied — there is no CLI discovery
> command for QuotaId.

---

## 2. Cross-Product Field Mapping (CreateJob ← AIWorkSpace)

Authoritative mapping from `create-job` fields back to their AIWorkSpace
discovery API. `--help` cannot point you across products.

| CreateJob field | Source API | Source field |
|-----------------|------------|--------------|
| `--workspace-id` | `aiworkspace list-workspaces` | `Workspaces[].WorkspaceId` |
| `--job-specs[].Image` | `aiworkspace list-images` | `Images[].ImageUri` (verbatim) |
| `--data-sources[].DataSourceId` | `aiworkspace list-datasets` | `Datasets[].DatasetId` |
| `--code-source.CodeSourceId` | `aiworkspace list-code-sources` | `CodeSources[].CodeSourceId` |
| `--resource-id` | (manual) | User-provided QuotaId |

**Recommended discovery order:** `list-workspaces` → `list-image-labels` →
`list-images` → `list-datasets` → `list-code-sources` → fill into `create-job`.

---

## 3. Job Status Lifecycle

```
Creating → Queuing → (Bidding) → EnvPreparing → SanityChecking
        → Running → (Restarting) → Stopping → Succeeded / Failed / Stopped
```

- `Bidding` only appears for Spot jobs.
- `SanityChecking` only appears when `Settings.EnableSanityCheck=true`.
- `Restarting` is a transient state during fault recovery.

> The full enum (14 values, e.g. including `SucceededReserving` /
> `FailedReserving`) is documented by `aliyun pai-dlc list-jobs --help` under
> `--status`. The diagram above shows the **operational flow**, not an
> exhaustive enum.

---

## 4. CreateJob — Red Lines

> ⚠ **Red Line 1: `EcsSpec` ⇄ `ResourceConfig`** — mutually exclusive within
> a single TaskSpec. Use `EcsSpec` for public pay-as-you-go; `ResourceConfig`
> (with CPU/Memory/GPU/GPUType) for dedicated quota (and pair with
> `--resource-id`).

> ⚠ **Red Line 2: Image URI source** — `--job-specs[].Image` MUST be a verbatim
> `ImageUri` from `aiworkspace list-images`. Never invent, rewrite, or
> substitute `Name` / `ImageId`.

> ⚠ **Red Line 3: No ROA fallback** — if a plugin subcommand is unavailable,
> install/upgrade the plugin (`aliyun plugin install --names ...` /
> `aliyun plugin update --name ...`). Never construct generic ROA calls
> (`--pathPattern` / `--method GET|POST|PUT|DELETE`).

> ⚠ **Red Line 4: `--workspace-id` is always required** — `--help` marks it
> optional, but the server silently falls back to the user's default
> workspace. Always confirm with the user.

---

## 5. Constraints Format (JobTemplate)

When passing `--constraints` to `create-job-template` / `update-job-template`,
the value is a **JSON string with bash-escaped quotes**:

```bash
CONSTRAINTS='{\"JobSpecs[0].Image\":\"locked\",\"UserCommand\":\"required\"}'
```

The double-escaping (`\"`) is required because the value is parsed first by
the shell and then by JSON.

| Constraint value | Behavior at `create-job` time |
|------------------|-------------------------------|
| `locked` | Field is fixed; `create-job` arguments for this field are ignored. |
| `overridable` | Default. `create-job` arguments override the template value. |
| `required` | `create-job` MUST supply this field if the template doesn't. |

**JSONPath grammar:** dot-separated paths without a `$.` prefix
(e.g. `JobSpecs[0].Image`, `UserCommand`, `DataSources[0].MountPath`).

> **`update-job-template` rule** (per `--help`): `--constraints` cannot be
> passed alone — it must accompany `--content`. Each `--content` push creates
> a new version; pair with `--set-as-default true` to promote it.

---

## 6. Common Errors

| Code | Trigger | Fix |
|------|---------|-----|
| `NotFound` | Wrong `JobId` / `TemplateId` / `TensorboardId` | Re-run the corresponding `list-*` command to confirm |
| `InvalidParameter` | Format / type / enum violation | Re-check with `--help`; for `--content`, validate JSON |
| `InvalidParameter.Content` | `Content` not valid JSON or missing `JobType` / `JobSpecs` | Test with `create-job --cli-dry-run` |
| `InvalidParameter.Constraints` | Invalid value or submitted without `Content` | Use `locked` / `overridable` / `required` only; pair with `--content` |
| `NotFound.JobTemplate` | TemplateId does not exist | Confirm via `list-job-templates` |
| `NotFound.JobTemplateVersion` | Non-existent version number | Use `get-job-template --biz-version all` |
| `Forbidden.RAM` | Missing `pai:*` / `paidlc:*JobTemplate*` / `paiimage:*` etc. | See [ram-policies.md](ram-policies.md) |
| `Throttling` | Rate limit | Reduce request frequency; add backoff |
| `ServiceUnavailable` | Transient | Retry with exponential backoff |

---

## 7. Forbidden Patterns

- ❌ `--pathPattern` / `--method GET|POST|PUT|DELETE` (ROA generic fallback) —
  install/upgrade the proper plugin instead.
- ❌ `aliyun pai-dlc list-images` / `list-workspaces` / `list-datasets` /
  `list-code-sources` — these subcommands belong to **`aiworkspace`**,
  not `pai-dlc`.
- ❌ `aliyun aiworkspace create-job-template` / `list-job-templates` — these
  belong to **`pai-dlc`**, not `aiworkspace`.
- ❌ Reading or printing `ALIBABA_CLOUD_ACCESS_KEY_ID` / `_SECRET`; running
  `aliyun configure set` with literal credential values.
