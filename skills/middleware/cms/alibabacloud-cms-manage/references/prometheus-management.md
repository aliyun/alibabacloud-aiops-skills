# Prometheus Management

> This file builds on [SKILL.md](../SKILL.md) — region / workspace confirmation, write confirmation, pagination, and error handling are not repeated. Flag lists and body envelopes come from `aliyun cms2 prometheus <subcommand> --help` (once per subcommand per session). **This file is the authority** for aggregation-view create gates and for `--region` on the commands in the table below: generic help says pass `controlRegionId`; this module does not.

Use this module to create a Prometheus aggregation view (`prometheus view`), diagnose an existing one, or delete a view.

Prometheus instances are **not** CloudResource objects. Never `entity query --source CloudResource` to fetch them.

## Commands

Read `--help` before first use. The From-help column is CLI flag and body shapes; the `--region` column is this file's override.

| Need | Command | From help | `--region` here |
|------|---------|-----------|-----------------|
| Business-location catalog | `meta regions` | Items: `name`, `showName`, `controlRegionId` | (none) |
| Workspace `regionId` | `workspace get --workspace` | Response includes `regionId` | Confirmed region |
| Child instance details (batch; region unknown) | `prometheus instance list` | `--prometheus-ids`, `--prometheus-instance-name` (partial match), `--version`, `--member-account-id`, `--next-token` / `--max-results`. Omit `--workspace` in this workflow. Do not pass `--version` | Each `meta regions` `name` |
| Child instance details (one id; `regionId` already known) | `prometheus instance get --prometheus-id` | Instance name, workspace, storage, status, endpoints. Use in diagnose, or whenever `regionId` is already known. Create still uses `instance list` — the child's region is not known yet | Instance `regionId` |
| Resolve view id | `prometheus view list` | `--prometheus-ids` (by id), `--prometheus-view-name` (partial match), `--workspace`, `--next-token` / `--max-results` | Workspace `regionId` |
| Create view | `prometheus view create --body` | Schema `required`: `prometheusViewName`, `version`, `prometheusInstances[]` (`prometheusInstanceId`, `regionId`, `userId`). Returns `prometheusViewId`. Also send `workspace` (schema field; this workflow always includes it) | Workspace `regionId` |
| Read view | `prometheus view get --prometheus-id` | Name, workspace, associated instances, status | Workspace `regionId` |
| Delete view | `prometheus view delete --prometheus-id` | Deletes one view by id. Returns success without a body; confirm with `view get` | Workspace `regionId` |
| Recent samples | `metric promql series` | `--prometheus-id` (instance or view id), `--match`, `--start`, `--end` | Instance `regionId` |

`controlRegionId` is **not** a `--region` value in this module. Use it only to compare control-plane regions in [Hard checks](#hard-checks).

## `meta regions`

```bash
aliyun cms2 meta regions -o json
```

Lists business locations available to the current account. Each item:

| Field | Meaning | Relation |
|-------|---------|----------|
| `name` | Business location ID (e.g. `cn-hangzhou`, `cn-shanghai`, `cn-qingdao-acdr-ut-1`) | Same vocabulary as workspace `regionId` and instance `regionId`. This module uses every `name` as `--region` on `instance list`. |
| `showName` | Display name | Human-facing only. Never a `--region` or body field. |
| `controlRegionId` | CMS / ARMS / SLS control-plane region | Many `name`s can share one `controlRegionId` (e.g. `cn-hangzhou` and `cn-shanghai` both map to `cn-hangzhou`). For dedicated / exclusive business locations, `name` may differ from `controlRegionId`. Generic CLI help says pass this as `--region`; **this module does not.** Use it only to test whether two `name` / `regionId` values sit on the same control plane. |

Load the catalog once per task. Build `name → controlRegionId`. Unknown `name` (workspace or instance `regionId` not in the catalog) → stop; do not guess.

---

## Create Prometheus Aggregation View

### Scope

Trigger when the user asks to create a Prometheus aggregation view / Prometheus view (聚合视图), or to combine several Prometheus instances into one queryable view.

**Out-of-scope**: diagnosing an existing view ([below](#diagnose-prometheus-aggregation-view)); deleting a view ([below](#delete-prometheus-aggregation-view)); creating a Prometheus *instance*; PromQL against the new view; **V1** views. If the user asks for V1, stop and say only V2 is supported.

### Input

| Parameter | Required | How to obtain |
|-----------|----------|---------------|
| Workspace | Yes | [Workspace Confirmation Gate](../SKILL.md#workspace-confirmation-gate-hard-requirement). |
| View region | No (use workspace `regionId`) | The view's region **is** the workspace's `regionId`. After `workspace get`, use that `regionId` on `view create` / `view get` / `view delete`. Do not pick another region for the view. |
| `prometheusViewName` | Yes | Ask if omitted. If the user asked for a new view and an exact name already exists, stop and ask — do not reuse that view and do not rename on your own. |
| `version` | Always `"V2"` | Body field. Schema may list `V1`; do not send it. |
| Child instances | Yes (≥1) | User identifies each child by **id** or **instance name**. Optional per child: `userId`. Omit `userId`, or set it to the current account (runtime context), for same-account list; a different `userId` adds `--member-account-id` (resource-directory proxy on `instance list --help`). |

`prometheusInstanceId` in the create body is the id from `instance list`, **not** an ACK cluster id (`view create --help`). Resolve names before create.

### 1. Workspace `regionId`

```bash
aliyun cms2 workspace get --workspace <workspace> --region <confirmed-region> -o json
```

Read `regionId`. That value is `--region` on `view create` / `view get` / `view delete`. If it differs from the confirmed region, stop — do not substitute.

### 2. Load `meta regions`

Run `meta regions` once per [meta regions](#meta-regions). Keep every `name` for the `instance list` loop. Use the `name → controlRegionId` map only in [Hard checks](#hard-checks). If workspace `regionId` is not a catalog `name`, stop.

### 3. Fetch every named child instance

Current account comes from runtime context (credentials / session). Do not parse `userId` or `regionId` from a workspace name, and do not ask for the current account.

Parse `-o json` by field name: `userId`, `regionId`, `version`, `status`, the id (`prometheusInstanceId` or `prometheusId`), and the instance name (`prometheusInstanceName` / `instanceName` / `name`). Use `userId` from that list row. Never invent those fields, reuse another instance's `userId`, or reuse the view workspace UID (`view create --help`).

**Same account** (`userId` omitted or equals current). **Cross-account** (named `userId` ≠ current): the same loop, plus `--member-account-id <userId>`, grouped by that `userId`. Credentials must belong to the management account (`instance list --help`). If the resource-directory proxy is unsupported → ask the user to switch credentials; do not retry as current-account list.

Identify each child the way the user did. Mix is allowed: split ids and names; do not put `--prometheus-ids` and `--prometheus-instance-name` on the same call.

**By id:** one batched `instance list --prometheus-ids` per catalog `name`.

```bash
aliyun cms2 prometheus instance list \
  --prometheus-ids <id1>,<id2>,... \
  --region <name> \
  --max-results 100 \
  -o json
```

**By instance name:** `instance list --prometheus-instance-name` (one user-supplied name per call; the flag is a single string, not a comma list). `--help` says partial match — keep only **exact** name matches after list ([SKILL.md](../SKILL.md) name-to-ID). Zero exact hits under the current `name` → continue the loop. Only after every `name` has been queried with no exact match is it not-found. More than one exact hit → report the rows and ask; never pick a partial or near match.

```bash
aliyun cms2 prometheus instance list \
  --prometheus-instance-name <instance-name> \
  --region <name> \
  --max-results 100 \
  -o json
```

Shared for both:

- One call per `meta regions` `name` as `--region`. Do not pass `controlRegionId`, do not skip a `name`, and do not collapse the loop (instances in another business location would be missed).
- **Do not pass `--version`.** A `V1` row must stay visible so the version hard check can run.
- **Do not pass `--workspace`.**
- Paginate (`--next-token`). Union rows. A child found under any `name` counts. Only after every `name` has been queried is a missing id or exact name a not-found (you may stop remaining `name`s once every requested child has a row).

### Hard checks

Every named instance, in order. First failure **stops** — do not create a partial view.

| Check | Failure |
|-------|---------|
| Id or exact instance name absent from the completed list, or the query was rejected | Instance `<id or name>` was not found. Do not substitute a partial or near match. |
| `status` ≠ `Running` | Instance `<id>` is not `Running` (report the observed status). |
| `version` ≠ `V2` (including missing) | Only V2 views are supported; instance `<id>` is not `V2` (report the observed version). |
| Instance `regionId` and workspace `regionId` map to different `controlRegionId`s | Report exactly `不允许跨区聚合prometheus实例`, plus the id and both `regionId`s. Do not report `controlRegionId` to the user. |

The last check is the `meta regions` map, not a string compare of `regionId`s (`cn-hangzhou` and `cn-shanghai` may share a `controlRegionId`). A `regionId` missing from the catalog is a mismatch.

### Create

Write confirmation per [SKILL.md](../SKILL.md#global-conventions): workspace, view name, `V2`, every instance (`prometheusInstanceId`, `userId`, `regionId`, `status`, `version`). Wait for a clear affirmative.

Compose `--body` from `--show-schema` / `--show-example-body`. Schema `required`: `prometheusViewName`, `version`, `prometheusInstances[]` (each item: `prometheusInstanceId`, `regionId`, `userId`). Also send `workspace` (schema field; required by this workflow and the Workspace Confirmation Gate — not listed in schema `required[]`). Validate with `jq`. Fill from the fetch, not from example placeholder ids.

```bash
aliyun cms2 prometheus view create --region <workspace-regionId> --body @./view.json -o json < /dev/null
```

```json
{
  "prometheusViewName": "<name>",
  "version": "V2",
  "workspace": "<workspace>",
  "prometheusInstances": [
    {
      "prometheusInstanceId": "<id>",
      "regionId": "<instance-regionId>",
      "userId": "<instance-userId>"
    }
  ]
}
```

Create returns `prometheusViewId`. Do not invent a view id.

### Verify

```bash
aliyun cms2 prometheus view get --prometheus-id <prometheusViewId> --region <workspace-regionId> -o json
```

Report `status` (and name, id, workspace, associated instances). If the first get misses the new view, wait briefly and retry 2–3 times. Persistent failure is `QueryFailed` — not `Running`.

---

## Delete Prometheus Aggregation View

Trigger when the user asks to delete, remove, or tear down a Prometheus aggregation view, including one this task just created. Write confirmation per [SKILL.md](../SKILL.md#global-conventions). `--region` is the workspace `regionId`, same as `view get` — not `controlRegionId`.

```bash
aliyun cms2 prometheus view delete --prometheus-id <prometheusViewId> --region <workspace-regionId> -o json < /dev/null
```

Delete only that view — never another existing view. Then `view get` the same id with the same `--region`. Persistent not-found / HTTP 404 is success. If the first get still finds it, wait briefly and retry 2–3 times before reporting failure.

---

## Diagnose Prometheus Aggregation View

Use this workflow to run a full health check on a Prometheus aggregation view, verifying each sub-instance, its underlying storage, and recent data ingestion, then emit a structured diagnostic report.

### Scope

Trigger when the user asks to diagnose, health-check, or troubleshoot a Prometheus aggregation view. The user may identify it by **id** or by **name**.

### Input

| Parameter | Required | How to obtain |
|-----------|----------|---------------|
| Workspace | Yes | [Workspace Confirmation Gate](../SKILL.md#workspace-confirmation-gate-hard-requirement). Then `workspace get` for `regionId` — that value is `--region` on `view list` / `view get`. |
| View | Yes | User-stated **id**: use it; do not re-ask. User-stated **name**: resolve with `view list` (below). |

**By id:** `prometheus view get --prometheus-id <view-id> --region <workspace-regionId>`. Do not re-ask. `view list --prometheus-ids` is not required.

**By name:** `prometheus view list --prometheus-view-name <name> --workspace <workspace> --region <workspace-regionId>`. The flag is a partial match — keep only **exact** name matches ([SKILL.md](../SKILL.md) name-to-ID). Zero exact hits → not found. More than one exact hit → report the rows and ask. Do not put `--prometheus-ids` and `--prometheus-view-name` on the same call.

### Check items

1. View basics via `prometheus view get --prometheus-id <view-id> --region <workspace-regionId>`: name, ID, status, associated instances. Parse child ids / `regionId` / `userId` by field name.

2. Sub-instance info: name, ID, home region, status, storage fields.
   - When the view already returned a child's `regionId`: `prometheus instance get --prometheus-id <id> --region <instance-regionId> -o json` (skip the catalog loop for that child).
   - Otherwise batch with `prometheus instance list --prometheus-ids` as in [Fetch every named child instance](#3-fetch-every-named-child-instance) (still do not pass `--version`).

3. Underlying SLS Project / MetricStore: read those fields by name from the `instance get` (or list) JSON. Do not call `aliyun sls`. Absent keys → `Unknown`. Ignore `isMoved2MetricStore` and `basicMetricQueryLimit` on every sub-instance; both are internal and have no diagnostic meaning.

4. Data in the last 5 minutes — query each **child** id, not the view:

```bash
aliyun cms2 metric promql series \
  --prometheus-id <child-id> \
  --match 'up' \
  --start <now-minus-5m> \
  --end <now> \
  --region <instance-regionId> \
  -o json
```

Non-empty series → yes. Empty series → no (warning). Query failure → `QueryFailed`. This workflow uses `up` as the ingestion signal; do not invent another PromQL expression.

### Report sections

Produce the report with these sections, in order:

- Aggregation view summary
- Sub-instance status table: name, ID, region, status, SLS Project, MetricStore, data in last 5 minutes (yes/no)
- Overall conclusion: health assessment + anomaly summary + suggested actions

### Anomaly rules

- Sub-instance status not `Running` → anomaly.
- SLS Project / MetricStore missing or in abnormal status → anomaly.
- No data ingested in the last 5 minutes → warning.

Distinguish `Ready`, `NotReady`, `Unknown`, `QueryFailed`, and partial results. Do not treat a query failure as health or absence.
