# Fault Report Tracking (Feature 8 flow)

> Applicable APIs: `list-fault-reports` / `describe-fault-report` (read-only) + `stop-node-diagnostic` / `approve-operation` (mutating).
> CLI truth measured on 2026-08-23 in cn-wulanchabu, aliyun 3.3.10 + plugin aliyun-cli-eflo-controller 0.7.4.

---

## 1. Background and trigger scenarios

After `report-node-status` (Feature 6, `--diagnosis-type COMPREHENSIVE`) submits a fault report, the platform immediately creates the fault report (`Status=Processing`) and the node enters **deep diagnosis** (typically 3-5 hours, covering system info / environment / PCIe / CPU / memory / GPU / network performance / high-speed links / logs / local storage). Feature 8 covers the post-report tracking closed loop:

- User asks "how is my fault report progressing / which faults have I reported before" -> `list-fault-reports` + `describe-fault-report`;
- User says "I don't want the diagnosis anymore / stop the fault report / restore the node" -> `stop-node-diagnostic` (mutating);
- User says "the platform raised a repair/reboot/upgrade proposal, approve it" (node measured in a `*PendingApproval` state) -> `approve-operation` (mutating).

## 2. Fault-report state machine

```text
Processing (deep diagnosis in progress)
   ├─ user stops ────────▶ DiagnosisTerminating (terminating, intermediate) ──▶ DiagnosisTerminated (terminated)
   ├─ no fault found ────▶ DiagnosisPassed (diagnosis passed, no fault found)
   └─ fault confirmed ───▶ FaultConfirmed (fault confirmed) ──▶ FaultFinish (fault handling completed)
```

In zh sessions, rendering `Status` must go through `_lj_fault_state_t` (the `faultstate.*` entries in `lib/core/i18n.sh`); en sessions and unlisted states pass through verbatim. **All script/jq decision logic uses the raw English values** (consistent with the OperatingState translation-boundary rule).

**Billing/SLA caliber (informational only, never a billing promise)**: reports ending in `DiagnosisTerminated` / `DiagnosisPassed` do not count toward node unavailable time; a `FaultConfirmed` report counts full unavailable time from the report moment to `FaultFinish`.

## 3. Query flow (read-only)

1. `list-fault-reports [--nodes <nid>] [--status <state>]`; a non-empty `NextToken` must be paginated to exhaustion (same as the skill-wide pagination rule).
2. When the user points at a specific report -> `describe-fault-report --report-id <rid>` to fetch the detail. Note the detail API does **not** return `NodeId`; the node dimension is authoritative from the list API.
3. Render the fault-report table (zh sessions render state names in Chinese per the i18n rules): report ID / node ID / status / report creation time / finish time / description; every field must come from the measured JSON (anti-hallucination red line).

## 4. Termination flow (stop-node-diagnostic, mutating)

1. **Locate**: `list-fault-reports` (or the user directly provides the ReportId) -> obtain `ReportId`. `ReportId` is `forbidden_inference`; fabrication / cross-session reuse is forbidden.
2. **Pre-check**: measure `Status` via `describe-fault-report --report-id <rid>`:
   -  in {`Processing`, `DiagnosisTerminating`} -> stoppable, enter Phase 1;
   -  in {`DiagnosisTerminated`, `DiagnosisPassed`, `FaultConfirmed`, `FaultFinish`} -> terminal, **must not** submit; explain the measured state and its meaning to the user ([PAUSE] Not Executed).
3. **Phase 1** (`safe_mutate stop-node-diagnostic ...`): the confirmation table renders per [mutating-schemas/stop-node-diagnostic.yaml](mutating-schemas/stop-node-diagnostic.yaml) `phase1_dump_fields`, with parameter names rendered per the Chinese mapping table in parameter-confirmation.md in zh sessions, and must include the impact statement:
   - the deep diagnosis stops immediately and **cannot be resumed**;
   - the node becomes available again;
   - diagnosing again requires a fresh fault report (`report-node-status`).
4. **Confirmation**: the user replies with the session-language confirmation word (zh word per parameter-confirmation.md / en "confirm") -> the Agent internally runs `safe_mutate_confirm <hash>`; any other input -> [PAUSE] Not Executed (same V5 red line as Feature 6).
5. **Post-commit verification**: 2xx + `RequestId`, and a `describe-fault-report` re-check shows `Status`  in {`DiagnosisTerminating`, `DiagnosisTerminated`} (`DiagnosisTerminating` is intermediate; a short poll <= 1min is acceptable); auxiliary `describe-node` observation of the node returning to `Using`. See [verification-method.md Section 7](verification-method.md).

## 5. Approval flow (approve-operation, mutating)

When deep diagnosis / platform maintenance raises a pending proposal, the node sits in a `*PendingApproval` state until the user approves:

1. **Pre-check**: `describe-node` measures `OperatingState`  in {`ClusterNodeRepairPendingApproval`, `ClusterNodeRebootPendingApproval`, `ClusterNodeUpgradePendingApproval`}; any other state -> no proposal to approve, terminate the flow with the measured state.
2. **Picker**: present the three-way HITL picker `RepairMachine` / `RebootMachine` / `UpgradeMachine` with the state-matched option highlighted (`RepairMachine` <- Repair, `RebootMachine` <- Reboot, `UpgradeMachine` <- Upgrade). `TerminateWindow` is internal-only and must never be offered.
3. **Phase 1** (`safe_mutate approve-operation ...`): confirmation table per [mutating-schemas/approve-operation.yaml](mutating-schemas/approve-operation.yaml) `phase1_dump_fields` (Region / NodeId / measured pending state / OperationType / full CLI line); zh sessions render parameter names per the Chinese mapping table in parameter-confirmation.md.
4. **Confirmation**: user replies the session-language confirmation word (zh word per parameter-confirmation.md / en "confirm") -> the Agent internally runs `safe_mutate_confirm <hash>`; any other input -> [PAUSE] Not Executed.
5. **Post-commit verification**: 2xx + `RequestId`; `describe-node` re-check shows the node leaving the `*PendingApproval` state (into the repair/reboot/upgrade flow). No public CLI queries the proposal status directly.

## 6. Edge cases and exceptions

| Scenario | Handling |
|---|---|
| `ReportId` does not exist / cross-Region | `NotFound` -> ask the user to confirm the Region (this skill enforces a single-Region lock per session) and the source of the report ID |
| Termination requested on a terminal report | Refuse to submit; show the measured Status (Chinese rendering in zh sessions) and its meaning |
| Node-dimension query ("has this node reported faults?") | Use `list-fault-reports --nodes <nid>`; do not guess via describe-fault-report |
| Node stays away from `Using` for a long time after termination | The fault-report Status is authoritative; node-state migration may lag - tell the truth and suggest a ticket if needed |
| Missing permissions | `eflo:DescribeFaultReport` / `eflo:ListFaultReports` / `eflo:StopNodeDiagnostic` / `eflo:ApproveOperation` - see [ram-policies.md Policy D](ram-policies.md) |

## 7. Phase 1 output example (zh session shown; en sessions are isomorphic with the confirmation prompt changed to reply "confirm")

```bash
🛑 About to issue mutating operation [stop-node-diagnostic]; review the parameters and reply 「确认」 to submit:

| Parameter | Value |
|---|---|
| Region | cn-wulanchabu |
| Report ID | i-997086804007 |
| Node ID | e01-cn-w1b4uz8i204 |
| Current fault status | `深度诊断中 (Processing)` |
| Impact | The deep diagnosis stops immediately and cannot be resumed; the node becomes available again; diagnosing again requires a fresh fault report |
| Full CLI | aliyun eflo-controller stop-node-diagnostic --endpoint eflo-controller.cn-wulanchabu.aliyuncs.com --region cn-wulanchabu --report-id i-997086804007 |

If everything is correct, reply 「确认」 to submit; to modify parameters or cancel, just tell me.
```
