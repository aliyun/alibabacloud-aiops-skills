# PAI-DLC API & CLI Reference

> **Single source of truth** for everything `aliyun pai-dlc <cmd> --help` and
> `aliyun aiworkspace <cmd> --help` do **not** tell you: command index across
> products, cross-product field contracts, status lifecycle, red lines,
> error catalog, forbidden patterns.
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
| `list-job-sanity-check-results` / `get-job-sanity-check-result` | SanityCheck | GPU health-check results |
| `list-ecs-specs` | ListEcsSpecs | Discover available ECS / Lingjun machine types |
| `get-web-terminal` | GetWebTerminal | Web Terminal URL (Pod must be alive) |
| `get-token` | GetToken | Read-only sharing token for jobs |

### 1.3 AIWorkSpace Resource Discovery (`aiworkspace` plugin, API 2021-02-04)

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

## 5. Common Errors

| Code | Trigger | Fix |
|------|---------|-----|
| `NotFound` | Wrong `JobId` | Re-run the corresponding `list-*` command to confirm |
| `InvalidParameter` | Format / type / enum violation | Re-check with `--help` |
| `Forbidden.RAM` | Missing `pai:*` / `paiimage:*` etc. | See [ram-policies.md](ram-policies.md) |
| `Throttling` | Rate limit | Reduce request frequency; add backoff |
| `ServiceUnavailable` | Transient | Retry with exponential backoff |

---

## 6. Forbidden Patterns

- ❌ `--pathPattern` / `--method GET|POST|PUT|DELETE` (ROA generic fallback) —
  install/upgrade the proper plugin instead.
- ❌ `aliyun pai-dlc list-images` / `list-workspaces` / `list-datasets` /
  `list-code-sources` — these subcommands belong to **`aiworkspace`**,
  not `pai-dlc`.
- ❌ Reading or printing `ALIBABA_CLOUD_ACCESS_KEY_ID` / `_SECRET`; running
  `aliyun configure set` with literal credential values.
