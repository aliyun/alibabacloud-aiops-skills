# API Parameter Inventory

All OpenAPI parameters referenced by this Skill, organized by the 9 Features (required / optional / default / value range). **If any parameter is missing or its value is not in this inventory, HITL must re-ask the user - LLM inference is forbidden.**

---

## F1 / F2 / F3 - Power Operations

### `stop-nodes`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--region` / `--endpoint` | Y | string | see [endpoint-routing.md](endpoint-routing.md) |
| `--nodes <id1> <id2> ...` | Y | string[] | NodeId array, <=100 |
| `--ignore-failed-node-tasks` | N | bool | default `false` |

### `reboot-nodes`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--region` / `--endpoint` | Y | string | |
| `--nodes <id1> <id2> ...` | Y | string[] | NodeId array |
| `--cluster-id` | N | string | recommended; speeds up server-side lookup |
| `--ignore-failed-node-tasks` | N | bool | default `false` |

### `reimage-nodes`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--region` / `--endpoint` | Y | string | |
| `--cluster-id` | N | string | recommended |
| `--nodes Hostname=<h> ImageId=<i> NodeId=<n> [LoginPassword=<pwd>]` | Y | array<object> | per node `Hostname`/`ImageId`/`NodeId` required, `LoginPassword` optional (omit -> keep existing password); `ImageId` and `LoginPassword` are `forbidden_inference` |
| `--user-data` | N | string | Base64 <=16KB |
| `--ignore-failed-node-tasks` | N | bool | default `false` |

---

## F4 - Renew (BssOpenApi)

### `bssopenapi renew-instance`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--instance-id` | Y | string | **= NodeId** (`e01-cn-xxx`) |
| `--product-code` | Y | string | fixed `bccluster` |
| `--product-type` | business-required | string | China site `bccluster_eflocomputing_public_cn`; International site `bccluster_eflocomputing_public_intl` |
| `--renew-period` | Y | int | values `1..9 / 12 / 24 / 36`, unit months; `forbidden_inference` |
| `--client-token` | recommended | UUID | idempotency key, **must keep the same value across retries** |

### `bssopenapi query-orders`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--product-code` | N | string | recommended filter `bccluster` |
| `--order-type` | N | string | `Renew` / `New` / ... |
| `--create-time-start` / `--create-time-end` | N | string | ISO8601 |
| `--page-num` / `--page-size` | N | int | default `1` / `20` |

---

## F5 - Node Spec Change

### `change-node-types`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--region` / `--endpoint` | Y | string | |
| `--node-ids <id1> <id2> ...` | Y | string[] | **<=10 per batch** |
| `--node-type` | Y | string | target NodeType (9-value enum: cpfs/ebs/balanced x single-tenant/multi-tenant/zeroLeni, **NOT a MachineType**); `forbidden_inference` |

### `describe-node-type`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--node-type` | Y | string | e.g. `efg2.C64M512.16ti` |

---

## F6 - Repair

### `report-node-status`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--node-id` | Y | string | single NodeId per call |
| `--diagnosis-type` | Y | enum | two reserved enums `QUICK` / `COMPREHENSIVE`, but only `COMPREHENSIVE` is accepted today (`QUICK` is reserved -> 400 "Only COMPREHENSIVE diagnosis type is supported") |
| `--description` | Y | string | fault description written by the user (`forbidden_inference`) |

Preconditions: node state must be `Using`; daily quota (default 10% of account machines); duplicate account+node report rejected. Response carries `ReportId` (i-<12 digits>) + `RequestId`; the report appears immediately in `list-fault-reports` with `Status=Processing`. Replaces the legacy PAI-only `report-nodes-status`. See `node-repair.md` F6.1

### `approve-operation`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--node-id` | Y | string | |
| `--operation-type` | Y | string | closed enum (public): `RepairMachine` / `RebootMachine` / `UpgradeMachine`; `TerminateWindow` is internal-only and forbidden here. No server-side enum validation — values outside the enum hit the default dispatch branch and fail confusingly. See `node-repair.md` F6.2 |

---

## F7 - Run Command / Send File

### `run-command`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--node-id-list` | Y | string[] | <=50 per batch |
| `--command-content` | Y | string | Bash script; secrets must go through `--enable-parameter` |
| `--client-token` | recommended | UUID | idempotency key |
| `--name` | N | string | <=30 |
| `--working-dir` | N | string | default `/root` |
| `--timeout` | N | int | default `60` seconds, max `86400` |
| `--username` | N | string | default `root` |
| `--content-encoding` | N | enum | `PlainText` (default) / `Base64` |
| `--repeat-mode` | N | enum | `Once` (default) / `Period` / `NextRebootOnly` / `EveryReboot` |
| `--frequency` | Y when `--repeat-mode=Period` | string | Cron expression |
| `--enable-parameter` | N | bool | enables `{{var}}` placeholders |
| `--parameters` | Y when enable-parameter | json | `{"key":"val"}` |

### `describe-invocations`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--invoke-id` | Y | string | |
| `--node-id` | N | string | |
| `--include-output` | recommended | bool | default `false`; set `true` once finished |
| `--content-encoding` | N | enum | `PlainText` (default) / `Base64` |

### `stop-invocation`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--invoke-id` | Y | string | |
| `--node-id-list` | N | string[] | omit -> stop all targets |

---

## F8 - Node Group Update

### `update-node-group`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--node-group-id` | Y | string | |
| `--new-node-group-name` | Y (doc-hallucination: CLI marks Optional but the server requires it) | string | must be passed even when not renaming |
| `--image-id` | N (>=1 business-optional) | string | `forbidden_inference` |
| `--login-password` | N (>=1) | string | sensitive field |
| `--user-data` | N (>=1) | string | Base64 <=16KB |
| `--biz-key-pair-name` | N (>=1) | string | |
| `--biz-ram-role-name` | N (>=1) | string | |
| `--file-system-mount-enabled` | N (>=1) | bool | |
| `--system-disk` | N (>=1) | object | only the single field `PerformanceLevel=<PL>`; Category/Size cannot be changed (dry-run verified: unknown field) |

---

## F9 - Tag & Resource Group

### `tag-resources`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--biz-region-id` | Y | string | == `--region` |
| `--resource-type` | Y | enum | `node` / `cluster` / `Hypernode` |
| `--resource-id` | Y | string[] | <=50 per batch |
| `--tag` | Y | repeated `Key=k Value=v` | >=1 pair |

### `untag-resources`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--biz-region-id` | Y | string | |
| `--resource-type` | Y | enum | |
| `--resource-id` | Y | string[] | |
| `--tag-key` or `--all=true` | Y (mutually exclusive) | string[] / bool | pick exactly one |

### `list-tag-resources`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--biz-region-id` | Y | string | |
| `--resource-type` | Y | enum | |
| `--resource-id` | N | string[] | |
| `--tag` | N | repeated | filter |
| `--max-results` / `--next-token` | N | int / string | pagination |

### `change-resource-group`

| Field | Required | Type | Notes |
|---|---|---|---|
| `--resource-region-id` | Y | string | == `--region` |
| `--resource-type` | Y | enum | `node` / `cluster` / `Hypernode` |
| `--resource-id` | Y | string | |
| `--resource-group-id` | Y | string | `forbidden_inference`; must be HITL-selected from `resourcemanager list-resource-groups` |

---

## Read-only / verification APIs

| API | Required | Purpose |
|---|---|---|
| `list-cluster-nodes` | `--cluster-id` | list regular nodes per cluster |
| `list-cluster-hyper-nodes` | `--cluster-id` | list hyper nodes per cluster |
| `describe-node` | `--node-id` | single-node detail |
| `describe-hyper-node` | `--hyper-node-id` | single hyper-node detail |
| `describe-node-group` | `--node-group-id` | node-group detail |
| `list-node-groups` | `--cluster-id` | list node groups |
| `list-clusters` | (none) | list clusters |
| `list-images` | (none) | list available images |
| `describe-task` | `--task-id` | async task status |

`OperatingState` enum: `Creating` / `Using` / `HealthyUsing` / `Unused` / `Stopped` / `Stopping` / `Starting` / `Rebooting` / `Reimaging` / `Deleting` / `Failed` / `Unknown`.

`TaskState` enum: `Running` / `execution_success` / `execution_fail` / `Cancelled` / `Pending`.

`InvocationStatus` enum (F7): `Pending` / `Scheduled` / `Running` / `Success` / `Failed` / `Stopped` / `Stopping` / `PartialFailed` / `Timeout`.
