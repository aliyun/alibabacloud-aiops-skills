# API Parameters Reference

> Full OpenAPI documentation: <https://api.aliyun.com/api/eflo-controller/2022-12-15>

This file lists the measured parameters (aliyun 3.3.10) of the 10+ CLIs this skill uses.

---

## #1 list-clusters (read-only)

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `--region` + `--endpoint` | string | [PASS] | endpoint-routing same-value hard rule |
| `--max-results` | int | [ ] | Default 20, max 100 |
| `--next-token` | string | [ ] | Pagination token, passed back verbatim |
| `--resource-group-id` | string | [ ] | |
| `--tags` | list | [ ] | |

Returns: `Clusters[].{ClusterId,ClusterName,ClusterType,ClusterDescription,Status,VpcId,...}` + `NextToken`.

---

## #2 describe-cluster (read-only)

| Parameter | Type | Required |
|---|---|---|
| `--region` + `--endpoint` | string | [PASS] |
| `--cluster-id` | string | [PASS] |

Returns: `{ClusterId,ClusterName,ClusterType,Components,NodeCount,...,TaskId,OperatingState}`. A non-empty `TaskId` means the cluster currently has an in-progress change task (unrelated to diagnostic tasks).

---

## #3 list-cluster-nodes (read-only)

| Parameter | Type | Required |
|---|---|---|
| `--region` + `--endpoint` | string | [PASS] |
| `--cluster-id` | string | [PASS] |
| `--node-group-id` | string | [ ] |
| `--operating-states` | list | [ ] |
| `--max-results` | int | [ ] |
| `--next-token` | string | [ ] |

Returns: `Nodes[].{NodeId,Hostname,MachineType,OperatingState,NodeGroupId,NodeGroupName,Zone,HpnZone,...}` + `NextToken`.

---

## #4 list-cluster-hyper-nodes (read-only)

Parameters same as #3, but for cluster-scoped hyper nodes: returns `HyperNodes[].{HyperNodeId,Hostname,MachineType,OperatingState,...}`.

---

## #5 describe-node (read-only)

| Parameter | Type | Required |
|---|---|---|
| `--region` + `--endpoint` | string | [PASS] |
| `--node-id` | string | [PASS] |

Returns: `{NodeId,Hostname,MachineType,OperatingState,Disks[],NetworkCards[],ImageId,Sn,ZoneId,HpnZone,...}`.

---

## #6 describe-hyper-node (read-only)

| Parameter | Type | Required |
|---|---|---|
| `--region` + `--endpoint` | string | [PASS] |
| `--hyper-node-id` | string | [PASS] |

Returns: `{HyperNodeId,Hostname,MachineType,OperatingState,SubNodes[],...}`.

---

## #7 create-diagnostic-task (mutating, submit diagnosis)

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `--region` + `--endpoint` | string | [PASS] | |
| `--cluster-id` | string | [PASS] | Target cluster |
| `--diagnostic-type` | string | [PASS] | Enums (retested 2026-08-19): `BasicCheck` / `NodeHardwareCheck` / `CheckByAiJobLogs`; `NetConfigCheck`/`NetRuntimeCheck` were deprecated on 2026-08-19 (product-side unsupported, the skill no longer submits them); the old values `NetDiag`/`ServerDiag` no longer exist |
| `--node-ids` | list | [ ]* | Two-layer format (probe-measured 2026-08-19): at the OpenAPI layer `NodeIds` is a string array (official example `["mock-sn-200101"]`); at the CLI layer the array is encoded as space-separated `--node-ids v1 v2 v3`; passing an array literal directly is **forbidden** (both JSON/Python styles get word-split / the brackets pollute the node IDs). Required for `BasicCheck`/`NodeHardwareCheck`; optional for `CheckByAiJobLogs` when AiJobLogInfo already contains NodeId |
| `--ai-job-log-info` | object | [ ]* | Required only for `CheckByAiJobLogs`; structure: `{StartTime,EndTime,AiJobLogs[{NodeId,AiInstance,Logs[]}]}` |

Returns: `{RequestId, DiagnosticId}`. `DiagnosticId` is the sole handle for subsequent polling.

**Structured `--ai-job-log-info`**: the CLI passes JSON as a single string via `--ai-job-log-info '<JSON>'`; `StartTime`/`EndTime` must be ISO8601 with timezone, e.g. `2026-05-16T08:00:00+0800`.

---

## #8 describe-diagnostic-result (read-only, polling)

| Parameter | Type | Required |
|---|---|---|
| `--region` + `--endpoint` | string | [PASS] |
| `--diagnostic-id` | string | [PASS] |

Returns (typical fields):

```json
{
  "RequestId": "...",
  "DiagnosticId": "...",
  "ClusterId": "...",
  "ClusterName": "...",
  "DiagnosticType": "BasicCheck",
  "ResourceIds": ["e01-cn-..."],
  "ServerName": "...",
  "Status": "Finished",
  "StartTime": "2026-05-16T08:00:00Z",
  "FinishedTime": "2026-05-16T08:14:32Z",
  "DiagnosticResults": [
    {"NodeId": "e01-cn-xxx", "CheckItem": "ib0_link", "Status": "Success", "ErrorMessage": ""}
  ]
}
```

> [WARN] Under different `DiagnosticType`s / cluster versions, the status field name may be `Status` or `DiagnosticState`, and the terminal-state strings may be `Finished` / `Success` / `Failed`. The Agent **must not** hardcode specific terminal strings; terminal detection must use "not in {InProgress, Running, Pending, Diagnosing}".

---

## #9 list-diagnostic-results (read-only)

| Parameter | Type | Required |
|---|---|---|
| `--region` + `--endpoint` | string | [PASS] |
| `--diag-type` | string | [PASS] | **Server-side required** (measured 2026-08-16: missing -> `field required`). The enum **splits** from the write endpoint #7: the read endpoint only accepts the old enums `NetDiag` / `ServerDiag` / `BasicCheck` (measured working); new enums are rejected |
| `--max-results` | int | [ ] | Default 20, max 100 |
| `--next-token` | string | [ ] | |
| `--resource-group-id` | string | [ ] | |

> [WARN] **CLI truth 1 (measured, 2026-05 cn-wulanchabu)**: `--diag-type` is **required**. When omitted the server returns:
>
> ```
> InternalError 400: parameter check failed, 1 validation error for ListDiagnosticResultsArguments
> ```
>
> The OpenAPI docs mark it as an optional filter, but the gateway actually enforces it. When the Agent wants to list all historical diagnostics, it must iterate over every enum the region actually supports, calling once per enum, then merge the results.
>
> [WARN] **CLI truth 2 (measured, 2026-08-16 holographic account)**: `--diag-type` is server-side required, and an **enum split** exists (the server-side API migration is not yet complete):
>
> | Endpoint | Accepted enums | Measured result |
> |---|---|---|
> | Write `create-diagnostic-task` | `BasicCheck`/`NodeHardwareCheck`/`CheckByAiJobLogs` (`NetConfigCheck`/`NetRuntimeCheck` deprecated 2026-08-19, no longer submitted) | [PASS]; old enums `NetDiag`/`ServerDiag` fail with `value is not a valid enumeration member` |
> | Read `list-diagnostic-results` | `NetDiag`/`ServerDiag`/`BasicCheck` | [PASS]; new enums fail with `Invalid parameter DiagType<enum-name>` |
>
> ```
> InternalError 400: Invalid parameter DiagType<enum-name>
> ```
>
> When querying historical diagnostics the Agent must use the old enums (`NetDiag`/`ServerDiag`/`BasicCheck`), calling once per enum and merging the results; when submitting it must use the new enums. Behavior in other regions may differ; upon hitting this error the Agent should tell the user "this endpoint does not accept enum X (enum split)" rather than treating it as a transient bug.
>
> [WARN] Note: the CLI flag is named `--diag-type`, which is **inconsistent** with `create-diagnostic-task`'s `--diagnostic-type` - this is a CLI legacy artifact; do not mix them up.

Returns: `{RequestId, NextToken, DiagnosticResults[{DiagnosticId,DiagnosticType,Status,ClusterId,...}]}`.

---

## #10 list-syslogs (read-only)

| Parameter | Type | Required |
|---|---|---|
| `--region` + `--endpoint` | string | [PASS] |
| `--node-id` | string | [PASS] (CLI marks it `(required)`) |
| `--from-time` | int | [PASS] epoch-seconds integer (server measured 2026-08-20: passing ISO8601 fails with `value is not a valid integer`) |
| `--to-time` | int | [PASS] epoch-seconds integer (same as above) |
| `--query` | string | [ ] SLS syntax, joined with `OR` (e.g. `error OR fail OR panic`; the pipe form fails with a parse error) |
| `--reverse` | bool | [ ] Default false |
| `--next-token` | string | [ ] |

---

## #11 reboot-nodes (mutating, repair)

| Parameter | Type | Required |
|---|---|---|
| `--region` + `--endpoint` | string | [PASS] |
| `--cluster-id` | string | [PASS] |
| `--nodes` | list | [PASS] Space-separated `NodeId`s |
| `--ignore-failed-node-tasks` | bool | [ ] Default false |

---

## #12 reimage-nodes (mutating, destructive)

| Parameter | Type | Required |
|---|---|---|
| `--region` + `--endpoint` | string | [PASS] |
| `--cluster-id` | string | [PASS] |
| `--nodes` | structured list | [PASS] `Hostname=h ImageId=i LoginPassword=p NodeId=n` per item |
| `--user-data` | string | [ ] |
| `--ignore-failed-node-tasks` | bool | [ ] |

> [WARN] `--nodes` is a **structured** list, **not** a string list; CLI form: `--nodes Hostname=a ImageId=b LoginPassword=c NodeId=d --nodes Hostname=e ...`. `Hostname` / `ImageId` / `LoginPassword` are all `forbidden_inference`.

---

## #13 stop-nodes (mutating, reversible)

| Parameter | Type | Required |
|---|---|---|
| `--region` + `--endpoint` | string | [PASS] |
| `--nodes` | list | [PASS] |
| `--ignore-failed-node-tasks` | bool | [ ] |

> [WARN] **No `--cluster-id`**. Forcing it in triggers `unknown flag`.

---

## #14 report-node-status (mutating, fault reporting)

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `--region` + `--endpoint` | string | [PASS] | |
| `--node-id` | string | [PASS] | **Single NodeId per call** (not a list) |
| `--diagnosis-type` | string | [PASS] | Two reserved enums `QUICK` / `COMPREHENSIVE`, but only `COMPREHENSIVE` is accepted today; `QUICK` is reserved and rejected (400 "Only COMPREHENSIVE diagnosis type is supported") |
| `--description` | string | [PASS] | The user's real fault description; `forbidden_inference` |

> Replaces the legacy PAI-only `report-nodes-status` (`--nodes` / `--reason` / `--issue-category` / `--start-time`), which must no longer be used. Preconditions: node state must be `Using`; daily quota (default 10% of account machines); duplicate account+node report rejected. Response carries `ReportId` (i-<12 digits>) + `RequestId` synchronously; the report appears immediately in `list-fault-reports` with `Status=Processing`; the node transitions to `PreparationForDiagnosingClusterNode`. See [mutating-schemas/report-node-status.yaml](mutating-schemas/report-node-status.yaml).

---

## #15 list-fault-reports (read-only, fault-report list)

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `--region` + `--endpoint` | string | [PASS] | |
| `--nodes` | list | [ ] | Filter by node, `--nodes <nid1> <nid2>` |
| `--status` | string | [ ] | Fault-report status enums: `Processing` / `DiagnosisTerminating` / `DiagnosisTerminated` / `DiagnosisPassed` / `FaultConfirmed` / `FaultFinish` |
| `--max-results` | int | [ ] | Items per page |
| `--next-token` | string | [ ] | Pagination token; non-empty must be exhausted |

> Returned fields: `Reports[]` (`ReportId` / `NodeId` / `Status` / `CreateTime` / `FinishTime` / `Description` / `DiagnosisType`, measured 2026-08-23) + `NextToken` + `RequestId`. In zh sessions `Status` is translated via `_lj_fault_state_t`.

---

## #16 describe-fault-report (read-only, fault-report detail)

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `--region` + `--endpoint` | string | [PASS] | |
| `--report-id` | string | [PASS] | Report ID, shaped like `i-997086804007`; must come from a measured list-fault-reports return or be user-provided |

> Returned fields (measured): `ReportId` / `Status` / `CreateTime` / `FinishTime` / `Description` / `DiagnosisType` / `ErrorMessage` (may be empty) + `RequestId`. Note: `NodeId` is **not** returned; the node dimension requires cross-referencing list-fault-reports.

---

## #17 stop-node-diagnostic (mutating, terminate fault-report diagnosis)

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `--region` + `--endpoint` | string | [PASS] | |
| `--report-id` | string | [PASS] | `forbidden_inference`; must be measured in the same session or explicitly user-provided |

> [WARN] No `--node-id` / `--cluster-id` flags. Takes effect synchronously and returns a `RequestId`; before submission `describe-fault-report` must measure `Status  in {Processing, DiagnosisTerminating}`; terminal states refuse submission. Full confirmation table / validation rules: see [mutating-schemas/stop-node-diagnostic.yaml](mutating-schemas/stop-node-diagnostic.yaml); flow: see [fault-report-tracking.md](fault-report-tracking.md).

---

## DiagnosticType applicability guide

| Type | Inspection dimensions | Average duration | Typical use case |
|---|---|---|---|
| `BasicCheck` | kernel dmesg / driver / runtime / containers | 5-15 min | OOM, kernel panic, driver mismatch |
| `NodeHardwareCheck` | GPU/HBM ECC, NVLink, PCIe, disk SMART, NIC | 20-45 min | GPU XID, HBM errors, abnormal disk IO |
| `CheckByAiJobLogs` | Parses the user's AI job logs (NCCL/Megatron etc.) | 10-30 min (depends on log volume) | "My job trained abnormally - can the logs show at which step it broke?" |

> `NetConfigCheck` / `NetRuntimeCheck` (network configuration / runtime diagnostics) were deprecated on 2026-08-19 and are no longer submitted; historical records (including the old value `NetDiag`) can still be rendered normally per the read-endpoint enums.
