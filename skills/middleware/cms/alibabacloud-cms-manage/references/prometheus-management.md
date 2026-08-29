# Prometheus Management

> This file builds on [SKILL.md](../SKILL.md) — region / workspace confirmation, write confirmation, pagination, and error handling are not repeated. Flag lists and body envelopes come from `aliyun cms2 prometheus <subcommand> --help` (once per subcommand per session). **This file is the authority** for aggregation-view create gates and for `--region` on each command in this workflow.

Use this module to create a Prometheus aggregation view (`aliyun cms2 prometheus view`), diagnose an existing one, or delete a view.

Prometheus instances are **not** CloudResource objects. Never `aliyun cms2 entity query --source CloudResource` to fetch them.

## `aliyun cms2 meta regions`

`aliyun cms2 meta regions` (item fields from `--help`).
Pass `regionId` as `--region`. Never pass `showName` or `controlRegionId`.
Load once per task. The `regionId → controlRegionId` map is used only in [Hard checks](#hard-checks).
A workspace or instance `regionId` missing from the catalog → stop; do not guess.

---

## Create Prometheus Aggregation View

### Scope

Trigger when the user asks to create a Prometheus aggregation view / Prometheus view (聚合视图), or to combine several Prometheus instances into one queryable view.

**Out-of-scope**: diagnosing an existing view ([below](#diagnose-prometheus-aggregation-view)); deleting a view ([below](#delete-prometheus-aggregation-view)); creating a Prometheus *instance*; PromQL against the new view; **V1** views. If the user asks for V1, stop and say only V2 is supported.

### Input

| Parameter | Required | How to obtain |
|-----------|----------|---------------|
| Workspace | Yes | [Workspace Confirmation Gate](../SKILL.md#workspace-confirmation-gate-hard-requirement). |
| View region | No (use workspace `regionId`) | The `regionId` from `aliyun cms2 workspace get`. Do not pick another region for the view. |
| `prometheusViewName` | Yes | Ask if omitted. If the user asked for a new view and an exact name already exists, stop and ask — do not reuse that view and do not rename on your own. |
| `version` | Always `"V2"` | Body field. Schema may list `V1`; do not send it. |
| Child instances | Yes (≥1) | User identifies each child by **id** or **instance name**. Optional per child: `userId`. Omit `userId`, or set it to the current account (runtime context), for same-account list; a different `userId` adds `--member-account-id` (resource-directory proxy on `aliyun cms2 prometheus instance list --help`). |

`prometheusInstanceId` in the create body is the id from `aliyun cms2 prometheus instance list`, **not** an ACK cluster id (`aliyun cms2 prometheus view create --help`). Resolve names before create.

### 1. Workspace `regionId`

`aliyun cms2 workspace get` (flags from `--help`). Read `regionId`. That value is `--region` on `aliyun cms2 prometheus view create` / `aliyun cms2 prometheus view get` / `aliyun cms2 prometheus view delete`. If it differs from the confirmed region, stop — do not substitute.

### 2. Load `aliyun cms2 meta regions`

Run `aliyun cms2 meta regions` once per [meta regions](#aliyun-cms2-meta-regions). Keep every catalog `regionId` for the `aliyun cms2 prometheus instance list` loop. Use the `regionId → controlRegionId` map only in [Hard checks](#hard-checks).

### 3. Fetch every named child instance

Current account comes from runtime context (credentials / session). Do not parse `userId` or `regionId` from a workspace name, and do not ask for the current account.

Parse `-o json` by field name: `userId`, `regionId`, `version`, `status`, the id (`prometheusInstanceId` or `prometheusId`), and the instance name (`prometheusInstanceName` / `instanceName` / `name`). Use `userId` from that list row: never invent it, never reuse another instance's `userId`, never reuse the view workspace UID (`aliyun cms2 prometheus view create --help`).

**Same account** (`userId` omitted or equals current): run the loop below without `--member-account-id`. **Cross-account** (named `userId` ≠ current): the same loop, plus `--member-account-id <userId>`, grouped by that `userId`. Credentials must belong to the management account (`aliyun cms2 prometheus instance list --help`). If the resource-directory proxy is unsupported → ask the user to switch credentials; do not retry as current-account list.

Identify each child the way the user did. Mix is allowed: split ids and names; do not put `--prometheus-ids` and `--prometheus-instance-name` on the same call.

**By id:** one batched `aliyun cms2 prometheus instance list --prometheus-ids` per catalog `regionId` as `--region` (flags from `--help`).

**By instance name:** `aliyun cms2 prometheus instance list --prometheus-instance-name` (one user-supplied name per call; the flag is a single string, not a comma list; `--region` is the catalog `regionId` in the loop). `--help` says partial match — keep only **exact** name matches after list ([Name-to-ID lookup](../SKILL.md) must match exactly). Zero exact hits under the current catalog `regionId` → continue the loop. Only after every catalog `regionId` has been queried with no exact match is it not-found. More than one exact hit → report the rows and ask; never pick a partial or near match.

Shared for both:

- One call per catalog `regionId` as `--region`. Do not pass `controlRegionId`, do not skip a catalog `regionId`, and do not collapse the loop (instances in another business location would be missed).
- **Do not pass `--version`.** A `V1` row must stay visible so the version hard check can run.
- **Do not pass `--workspace`.**
- Paginate (`--next-token`). Union rows. A child found under any catalog `regionId` counts. A missing id or exact name is not-found only after every catalog `regionId` has been queried; you may stop remaining catalog `regionId`s once every requested child has a row.

### Hard checks

Every named instance, in order. First failure **stops** — do not create a partial view.

| Check | Failure |
|-------|---------|
| Id or exact instance name absent from the completed loop results, or the query was rejected | Instance `<id or name>` was not found. Do not substitute a partial or near match. |
| `status` ≠ `Running` | Instance `<id>` is not `Running` (report the observed status). |
| `version` ≠ `V2` (including missing) | Only V2 views are supported; instance `<id>` is not `V2` (report the observed version). |
| Instance `regionId` and workspace `regionId` map to different `controlRegionId`s | Report exactly `不允许跨区聚合prometheus实例`, plus the id and both `regionId`s. Do not report `controlRegionId` to the user. |

The last check is the `aliyun cms2 meta regions` map, not a string compare of `regionId`s (`cn-hangzhou` and `cn-shanghai` may share a `controlRegionId`). A `regionId` missing from the catalog is a mismatch.

### Create

Write confirmation per [SKILL.md](../SKILL.md#global-conventions): workspace, view name, `V2`, every instance (`prometheusInstanceId`, `userId`, `regionId`, `status`, `version`). Wait for a clear affirmative.

`aliyun cms2 prometheus view create` with `--region` = workspace `regionId` (flags from `--help`).
Compose `--body` from `--show-schema` / `--show-example-body`.
Fill ids from the fetch in this workflow, not from example placeholders.
`workspace` is in schema `required[]` and must be the workspace chosen by the Workspace Confirmation Gate.
`version` is always `"V2"`. Validate with `jq`.

Create returns `prometheusViewId`. Do not invent a view id.

### Verify

`aliyun cms2 prometheus view get` that `prometheusViewId` with `--region` = workspace `regionId` (flags from `--help`). Report `status` (and name, id, workspace, associated instances). If the first get misses the new view, wait briefly and retry 2–3 times. Persistent failure is `QueryFailed` — not `Running`.

---

## Delete Prometheus Aggregation View

Trigger when the user asks to delete, remove, or tear down a Prometheus aggregation view, including one this task just created. Write confirmation per [SKILL.md](../SKILL.md#global-conventions). `--region` is the workspace `regionId`, same as `aliyun cms2 prometheus view get`. When the user gives a name, resolve the id with `aliyun cms2 prometheus view list` as in [Diagnose](#diagnose-prometheus-aggregation-view).

`aliyun cms2 prometheus view delete` that id (flags from `--help`). Delete only that view — never another existing view. Then `aliyun cms2 prometheus view get` the same id with the same `--region`. Persistent not-found / HTTP 404 is success. If the first get still finds it, wait briefly and retry 2–3 times before reporting failure.

---

## Diagnose Prometheus Aggregation View

### Scope

Trigger when the user asks to diagnose, health-check, or troubleshoot a Prometheus aggregation view. The user may identify it by **id** or by **name**. Verify each sub-instance, its underlying storage, and recent data ingestion, then emit a structured diagnostic report.

### Input

| Parameter | Required | How to obtain |
|-----------|----------|---------------|
| Workspace | Yes | [Workspace Confirmation Gate](../SKILL.md#workspace-confirmation-gate-hard-requirement). Then `aliyun cms2 workspace get` for `regionId` — that value is `--region` on `aliyun cms2 prometheus view list` / `aliyun cms2 prometheus view get`. |
| View | Yes | User-stated **id**: `aliyun cms2 prometheus view get` directly. User-stated **name**: resolve with `aliyun cms2 prometheus view list` (below). |

**By id:** `aliyun cms2 prometheus view get --prometheus-id <view-id> --region <workspace-regionId>`. `aliyun cms2 prometheus view list --prometheus-ids` is not required.

**By name:** `aliyun cms2 prometheus view list --prometheus-view-name <name> --workspace <workspace> --region <workspace-regionId>`. The flag is a partial match — keep only **exact** name matches ([Name-to-ID lookup](../SKILL.md) must match exactly). Zero exact hits → not found. More than one exact hit → report the rows and ask. Do not put `--prometheus-ids` and `--prometheus-view-name` on the same call. Then `aliyun cms2 prometheus view get` with the resolved id.

### Check items

1. View basics from the `aliyun cms2 prometheus view get` above: name, ID, status, associated instances. Parse child ids / `regionId` / `userId` by field name.

2. Sub-instance info: name, ID, home region, status, storage fields.
   - When the view already returned a child's `regionId`: `aliyun cms2 prometheus instance get --prometheus-id <id> --region <instance-regionId>` (skip the catalog loop for that child).
   - Otherwise batch with `aliyun cms2 prometheus instance list --prometheus-ids` as in [Fetch every named child instance](#3-fetch-every-named-child-instance) (still do not pass `--version`).

3. Underlying SLS Project / MetricStore: read those fields by name from the `aliyun cms2 prometheus instance get` (or list) JSON. Do not call an SLS CLI. Absent keys → `Unknown`. Ignore `isMoved2MetricStore` and `basicMetricQueryLimit` on every sub-instance; both are internal and have no diagnostic meaning.

4. Data in the last 5 minutes — query each **child** id, not the view: `aliyun cms2 metric promql series --prometheus-id <child-id> --match 'up' --start <rfc3339-or-unix> --end <rfc3339-or-unix>` spanning the last 5 minutes (`--start`/`--end` are required; RFC3339 or unix seconds — `now-5m` is rejected), `--region` = that instance's `regionId`. Non-empty series → yes. Empty series → no (warning). Query failure → `QueryFailed`. This workflow uses `up` as the ingestion signal; do not invent another PromQL expression.

### Report sections

Produce the report with these sections, in order:

- Aggregation view summary
- Sub-instance status table: name, ID, region, status, SLS Project, MetricStore, data in last 5 minutes (yes/no)
- Overall conclusion: health assessment + anomaly summary + suggested actions. Distinguish `Ready`, `NotReady`, `Unknown`, `QueryFailed`, and partial results. Do not treat a query failure as health or absence.

### Anomaly rules

- Sub-instance status not `Running` → anomaly.
- SLS Project / MetricStore missing or in abnormal status → anomaly.
- No data ingested in the last 5 minutes → warning.
