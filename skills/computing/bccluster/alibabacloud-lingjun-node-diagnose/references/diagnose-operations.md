# Diagnose Operations (Core Flows)

> This file is the detailed implementation version of Features 1-7 in SKILL.md. Every command must run as `safe_aliyun aliyun ...`, and every mutating command must go through the `safe_mutate` two-phase commit first.

---

## #f1. Resource Locator

Locate the target Cluster + (Hyper)Node:

1. **HITL obtains the Region** ([endpoint-routing.md Section 2](endpoint-routing.md)).
2. `list-clusters` (paginate to exhaustion) -> the user picks `--cluster-id` from the visible clusters.
3. `list-cluster-nodes` + `list-cluster-hyper-nodes` (both paginated to exhaustion) -> render a unified numbered table:

   | # | Type | NodeId/HyperNodeId | Hostname | MachineType | OperatingState |
   |---|---|---|---|---|---|
   | 1 | Node | e01-cn-... | node-001 | efg1.nvga1 | Using |
   | 2 | HyperNode | hn-cn-... | hn-001 | efg2.... | HealthyUsing |

   > In zh sessions the `OperatingState` column values are rendered in Chinese per the authoritative table [node-state-i18n.md](node-state-i18n.md) (e.g. `Using` renders as its zh literal from that table); en sessions keep English.

4. The user **explicitly** picks a row (auto-select is forbidden).
5. Call `describe-node` / `describe-hyper-node` to fetch `Disks[]` / `NetworkCards[]` and other hardware counters; cache them in fixtures for the Section f5 report to reference later.

---

## #f2. Submit Diagnostic Task

```bash
[locate] → [DiagnosticType three-way choice] → [(if CheckByAiJobLogs) AiJobLogInfo HITL] →
[safe_mutate Phase 1 dump] → [user replies the confirmation word (zh 「确认」 / en "confirm"); Agent submits internally] →
[actual create-diagnostic-task call] → [validate RequestId + DiagnosticId] →
[enter §f3 polling]
```

### DiagnosticType three-way choice wording

```
Please choose the diagnostic type:
  1. Server basic health check (BasicCheck) — kernel/driver/runtime
  2. Hardware health inspection (NodeHardwareCheck) — GPU/HBM/PCIe/disk/NIC
  3. AI Job log diagnosis (CheckByAiJobLogs) — root-cause analysis based on the training logs you provide
```

> In zh sessions this menu is rendered in Chinese; the three English enum names always stay verbatim.

> Network diagnostics `NetConfigCheck` / `NetRuntimeCheck` were deprecated on 2026-08-19 and are no longer offered in the menu; if the user asks for network diagnosis on their own, steer them to BasicCheck (covers driver/runtime) or NodeHardwareCheck (covers NIC hardware).

### CheckByAiJobLogs sub-flow

Collect via HITL, in order:

1. `StartTime` / `EndTime` (ISO8601 with timezone).
2. `AiJobLogs[]`: each item `{NodeId, AiInstance (instance/Pod name), Logs[] (list of log paths)}`.
3. Serialize into a single JSON string and pass to `--ai-job-log-info`.

### Phase 1 output example (en session; zh sessions are isomorphic with labels rendered in Chinese per parameter-confirmation.md and the confirmation word changed to the zh literal defined there)

```text
🛑 About to submit a diagnostic task (mutating); please confirm:

  Region              : cn-hangzhou
  Cluster ID          : <cid>
  Diagnostic Type     : BasicCheck
  Target Nodes (1)    :
    - Type=Node  NodeId=e01-cn-xxx  Hostname=node-001  MachineType=efg1.nvga1
  Full CLI            : aliyun eflo-controller create-diagnostic-task --endpoint ... --region cn-hangzhou --cluster-id <cid> --diagnostic-type BasicCheck --node-ids e01-cn-xxx

APPROVE_TOKEN=ab12cd34  ← Agent-internal audit only; never show to the user
Review the parameters above and reply "confirm" to execute; any other reply cancels.
```

### Diagnosis re-entry check

Before submitting, run `list-diagnostic-results --diag-type <T>` to check whether the same node already has an InProgress diagnosis. If so, HITL offers two choices: a) reuse the existing `DiagnosticId` and enter Section f3; b) force-create a new one (rare; requires an explicit user-stated reason).

---

## #f3. Poll & Wait

Unified across the three DiagnosticTypes (same pattern as node-ops): one round every 10s in the foreground, **each round is an independent Bash call**, and at the end of each round the Agent reports one progress line in the reply body; cramming the loop into a single long-running blocking command is forbidden:

```bash
# First round (already executed automatically inside diagnose_submit):
poll_diagnostic_burst <region> <did> 10 10          # returns after 1 poll; rc=10 means still in progress

# Each subsequent round (independent Bash call, until terminal rc=0/1):
sleep 10 && poll_diagnostic_burst <region> <did> 10 10 <t0>   # t0 keeps the epoch of the first round start; displays cumulative elapsed time
# Each round prints one stdout line: ⏳ [HH:MM:SS] poll #N — diagnostic task <did> status=Running elapsed Xs
# The Agent must forward that line verbatim into the reply body so the user sees live progress
```

Terminal-state detection uses a reverse whitelist (anything other than `InProgress`/`Running`/`Pending`/`Diagnosing` counts as terminal); the blocking `poll_diagnostic` is reserved for tests / non-interactive orchestration.

Once a terminal state is hit, proceed to the Section f5 report.

> [WARN] Never hardcode `Status=Finished` as the only terminal check; different DiagnosticTypes may return different field names/values. The Agent uses the reverse whitelist (anything other than `InProgress`/`Running`/`Pending`/`Diagnosing` counts as terminal).

---

## #f4. List Diagnostic History

```bash
safe_aliyun aliyun eflo-controller list-diagnostic-results \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --diag-type NetDiag [--max-results 100]   # --diag-type is server-side required; the read endpoint only accepts the old enums NetDiag/ServerDiag/BasicCheck (enum split, see api-parameters.md #9)
# Paginate to exhaustion: loop on NextToken
```

Use cases:
- Query the status of a specific DiagnosticId (ID obtained in Section f3 but polling was not finished at the time).
- Review the recent N fault trends (filter by `--diag-type`).
- Find currently InProgress diagnostics (re-entry check).

---

## #f5. Diagnostic Report Template

Fixed 6 sections; every field comes from the real API response. In zh sessions field names / column names are rendered in the Chinese-name-plus-original format per [parameter-confirmation.md Section Parameter-name Chinese mapping table](parameter-confirmation.md), values untranslated; **single exception**: node state (`OperatingState`) is translated per [node-state-i18n.md](node-state-i18n.md) (e.g. `Using` renders as its zh literal from that table). The template below shows the en-session layout:

```markdown
# Lingjun Node Diagnostic Report — <DiagnosticId>

## 1. Summary (Header)
| Field | Value |
|---|---|
| Region | cn-hangzhou |
| Cluster ID (ClusterId) | <cid> |
| Cluster Name (ClusterName) | <name> |
| Diagnostic Task ID (DiagnosticId) | <did> |
| Diagnostic Type (DiagnosticType) | BasicCheck |
| Submit Time (StartTime) | <StartTime from API> |
| Finish Time (FinishedTime) | <FinishedTime from API> |
| Total Duration (Duration) | <delta> |

## 2. Target Identity
| # | Type | NodeId/HyperNodeId | Hostname | MachineType | OperatingState |
|---|---|---|---|---|---|
| 1 | Node | <NodeId> | <Hostname> | <MachineType> | <state> |

## 3. Verdict
**Overall verdict**: PASS / FAIL / WARNING

| CheckItem | Status | ErrorCode | ErrorMessage |
|---|---|---|---|
| ib0_link | Success | - | - |
| nccl_test | Fail | NCCL_ERR_SOCKET | bind: address already in use |

## 4. Per-Item Detail (abnormal items)
### nccl_test ❌
- ErrorMessage: <ErrorMessage>
- Hardware counter snapshot (from describe-node):
  - GPU0 ECC: <value>
  - NIC bond0 RxErrors: <value>

## 5. Supporting Evidence (system log excerpt)
```text
2026-05-16T08:12:34+0800 kernel: NCCL WARN bind: address already in use
...
```

## 6. Recommended Repair Plan
👉 See [Repair Plan](#) for the executable HITL plan.
```

When a field is missing it **must** be rendered as `-` with the language-matched missing-field note (zh literal lives in the report template); fabricating values is **forbidden**.

---

## #f6. Repair Plan Mapping

See [repair-plan-templates.md](repair-plan-templates.md) for details. Verdict -> default recommendation:

| Symptom | Default Action |
|---|---|
| BasicCheck SOFT errors | reboot-nodes |
| BasicCheck severe driver/firmware/kernel degradation (reboot ineffective) | reimage-nodes |
| Hardware fault | report-node-status (`--diagnosis-type COMPREHENSIVE`) |
| Offline maintenance | stop-nodes |
| Permanent removal | escalate to alibabacloud-lingjun-cluster-scaling skill |

Every repair command must go through:

```bash
[Phase 1 dump w/ resource list + impact + reversibility flag] →
[user replies the confirmation word (zh 「确认」 / en "confirm"; the reimage wipe warning is already inside the confirmation table, and the confirmation word counts as acknowledgement)] →
[Agent submits internally, actual CLI issued]
```

---

## #f7. Auxiliary Telemetry

`list-syslogs` time window recommendation: `--from-time = (StartTime - 30min)` ~ `--to-time = (FinishedTime + 5min)` (**epoch-seconds integers**; server measured 2026-08-20 does not accept ISO), with keyword filter `--query 'error OR fail OR panic OR oom OR nccl OR nvidia OR nic OR ib0 OR rdma'` (SLS OR syntax); after paginating to exhaustion, write the most recent 200 lines into report Section 5.

When the window exceeds 24h, HITL must prompt the user that the window is too wide and should be narrowed.

---

## #f8. Fault Report Tracking

The deep-diagnosis tracking closed loop after a fault report (`report-node-status`): `list-fault-reports` / `describe-fault-report` (read-only) + `stop-node-diagnostic` (mutating, two-phase confirmation).

```bash
# Query (filterable by node / status; paginate to exhaustion)
safe_aliyun aliyun eflo-controller list-fault-reports --endpoint eflo-controller.<region>.aliyuncs.com --region <region> [--nodes <nid>] [--status Processing]

# Detail
safe_aliyun aliyun eflo-controller describe-fault-report --endpoint eflo-controller.<region>.aliyuncs.com --region <region> --report-id <rid>

# Terminate (precondition: describe-fault-report measured Status ∈ {Processing, DiagnosisTerminating})
safe_mutate stop-node-diagnostic aliyun eflo-controller stop-node-diagnostic --endpoint eflo-controller.<region>.aliyuncs.com --region <region> --report-id <rid>
```

State machine / translated names / boundary exceptions / Phase 1 example: see [fault-report-tracking.md](fault-report-tracking.md); zh-session state names go through `_lj_fault_state_t` (faultstate.* entries).
