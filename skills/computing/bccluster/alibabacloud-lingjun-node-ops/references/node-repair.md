# Node Repair (F6) - report-node-status + approve-operation

Two sub-features that together cover the user-facing portion of the Lingjun maintenance lifecycle.

## F6.1 `report-node-status` - declare a fault

Tell the Lingjun service that a node has an issue; the platform immediately creates a fault report (`Status=Processing`, visible via `list-fault-reports`) and spawns the internal repair/deep-diagnosis workflow. This is the general-user fault-reporting API (`ReportNodeStatus`) — it **replaces** the legacy PAI-only `report-nodes-status` (`ReportNodesStatus`, with `--nodes` / `--reason` / `--issue-category`), which must no longer be used.

### CLI

```bash
safe_aliyun aliyun eflo-controller report-node-status \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --node-id <NodeId> \
  --diagnosis-type COMPREHENSIVE \
  --description <free-text written by the user>
```

### Parameters

| Flag | Required | Notes |
|---|---|---|
| `--node-id` | [OK] | single `NodeId` per call (NOT a list) |
| `--diagnosis-type` | [OK] | closed enum: two reserved values `QUICK` / `COMPREHENSIVE`, only `COMPREHENSIVE` accepted today (`QUICK` -> 400 "Only COMPREHENSIVE diagnosis type is supported") |
| `--description` | [OK] | the real fault description written by the user — `forbidden_inference`, LLM composing/splicing is a V3 self-violation |

### Behaviour (backend-verified 2026-08-31)

- **Sync** call. Response carries `ReportId` (format `i-<12 digits>`) + `RequestId`.
- A fault-report row is created immediately with `Status=Processing` — it is instantly visible via `list-fault-reports` / `describe-fault-report`.
- The node leaves `Using` (transitions to the diagnosing-preparation state); a repair task is spawned server-side.
- HyperNode membership is handled server-side (child-node state + hyper-node reflection).

### Preconditions & rejection reasons

| Check | Failure |
|---|---|
| Node exists under the account | 404 `InvalidNodeId.NotFound` |
| Node state is `Using` | 400 "Node status is X, expected Using" |
| Daily quota: today's reports must stay under the account quota (default 10% of account machines) | 400 "daily fault report quota exceeded" |
| No unresolved duplicate report for the same account + node | 400 "Duplicate fault report..." |

### Example

```bash
safe_aliyun aliyun eflo-controller report-node-status \
  --endpoint eflo-controller.cn-wulanchabu.aliyuncs.com --region cn-wulanchabu \
  --node-id e01-cn-aaa \
  --diagnosis-type COMPREHENSIVE \
  --description 'GPU 0 ECC error spike, dmesg attached separately'
```

---

## F6.2 `approve-operation` - approve a pending maintenance proposal

When the Lingjun service plans a maintenance window (disk swap, NIC swap, scheduled reboot for firmware), it raises a proposal that needs explicit user approval. Each proposal is identified by `(NodeId, OperationType)`.

### CLI

```bash
safe_aliyun aliyun eflo-controller approve-operation \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --node-id <NodeId> \
  --operation-type <type-from-notification>
```

### Parameters

| Flag | Required | Notes |
|---|---|---|
| `--node-id` | [OK] | single `NodeId` per call |
| `--operation-type` | [OK] | closed enum — see the table below; pick via HITL guided by the node's measured pending state |

### `OperationType` enum (server-side dispatch, re-verified against backend source 2026-08-31)

| OperationType | Meaning | Precondition (measured node state) |
|---|---|---|
| `RepairMachine` | Approve the repair window and start the repair task (DPU-mode nodes first attempt a standby replacement; on success it returns directly) | The node must have a real fault window (otherwise the server rejects: no real fault on the node, operation forbidden). Node state must be `ClusterNodeRepairPendingApproval` |
| `RebootMachine` | Approve the reboot window and start the reboot task | The node must have a real fault window. Node state must be `ClusterNodeRebootPendingApproval` |
| `UpgradeMachine` | Approve the upgrade window (mainly for hyper-node upgrade scenarios; does **not** require a real fault window) | Node state must be `ClusterNodeUpgradePendingApproval` (otherwise the server rejects: wrong state, upgrade cannot be approved) |
| `TerminateWindow` | Cancel the window: revert the node from a pending-approval state back to `Using` (false alarm / self-recovery) | **Internal-only** (`ApproveOperationInner`). Forbidden through this public CLI |

> **Validation pitfall**: `OperationType` is declared as a bare string — the server performs **no enum validation**; a value outside the four above does not yield an "invalid enum" error but falls into the default dispatch branch and fails with a confusing error. Only the first three values may ever be submitted.

### Behaviour

- **Sync** call. Response body contains `RequestId`.
- The maintenance operation proceeds asynchronously; the user is notified again when the operation completes.

### Hard rule - HITL three-way picker over the closed enum

`--operation-type` must be picked via a three-way HITL (`RepairMachine` / `RebootMachine` / `UpgradeMachine`) guided by the node's measured pending state from `describe-node`; the user selects explicitly. `TerminateWindow` must **never** be offered or submitted (internal-only). Free-text guessing (`reboot` / `replace-disk` / `maintenance` / any value outside the enum) remains a V3 self-violation — the enum table above is the sole source of truth.

### Workflow

1. The user asks to approve a pending proposal (or pastes a maintenance notification).
2. Agent measures the node's pending state via `describe-node` (`ClusterNodeRepairPendingApproval` / `ClusterNodeRebootPendingApproval` / `ClusterNodeUpgradePendingApproval`) and presents the matching three-way picker; the user selects explicitly.
3. Confirmation table + the closing prompt (see `render.confirm_prompt` in `lib/core/i18n.sh`) in one message; user replies the confirmation word (see `render.confirm_word` in `lib/core/i18n.sh`).
4. Submit -> record `RequestId`.
5. Verification: re-query `describe-node` after the planned window; rely on platform notifications for completion confirmation (no public CLI to query the proposal status directly).
