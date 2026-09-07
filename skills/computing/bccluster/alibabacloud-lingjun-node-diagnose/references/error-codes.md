# Error Codes

> This file summarizes common ErrorCodes in the `eflo:` domain with handling suggestions. Full official docs: <https://help.aliyun.com/document_detail/eflo-controller-error-codes>.

---

## General

| ErrorCode | HTTP | Meaning | Handling |
|---|---|---|---|
| `InvalidAccessKeyId.NotFound` | 4xx | AK does not exist / has been revoked | Blacklist, no retry |
| `SignatureDoesNotMatch` | 4xx | Wrong AK Secret or clock skew | Blacklist |
| `NoPermission` | 403 | RAM missing the action | Blacklist; complete per [ram-policies.md](ram-policies.md) |
| `Forbidden.RAM` | 403 | Sub-account explicitly Denied | Blacklist |
| `InvalidParameter` | 400 | Bad parameter format / enum out of range | Blacklist; re-pick via HITL |
| `MissingParameter` | 400 | Missing required field | Blacklist; complete via HITL (`forbidden_inference` fields must be typed by the user) |
| `Throttling.User` / `Throttling.Api` | 429 | Throttled | Whitelist; retry after a fixed 60s |
| `ServiceUnavailable` / `InternalError` | 5xx | Transient backend error | Whitelist with exponential backoff; exception: see "Known issues" below - specific signatures are not retried |

---

## Known issues (server-side truth; do not misclassify as transient)

### KI-1 create-diagnostic-task reports "These nodes do not exist" although the nodes really exist

- **Signature**: `InternalError` + Message `{'[<NodeId>]'} These nodes do not exist. please verify.`, while `describe-node` / `list-cluster-nodes` confirm the nodes really exist in that cluster.
- **Root cause**: the diagnostic service's node registry is out of sync with the cluster-control metadata (server-side defect, not a caller issue). Whether the NodeIds format is correct can be judged from the echo: `{'[a b]'}` without inner quotes = normal; quoted fragments = format contamination (see api-parameters.md #7 two-layer format).
- **Cross-region reproduction evidence**: cn-wulanchabu `i118208181786688932661` (2026-08-16/19); me-east-1 `i116273451787040153722` node `e01-cn-bbj4x54m004` (2026-08-19, RequestId `01A01A57-B4AE-347E-A4AA-757EFAAE5382`).
- **Handling**: this signature is a **deterministic** failure; retrying is useless (the exception to the `InternalError` whitelist) -> do not retry; guide the user to file a ticket with the RequestId attached.

---

## Resource NotFound

| ErrorCode | Meaning | Handling |
|---|---|---|
| `Cluster.NotFound` / `ClusterNotFound` | ClusterId does not exist / has been deleted | Re-pick via HITL from `list-clusters` |
| `Node.NotFound` / `NodeNotFound` | NodeId does not exist | Re-pick via HITL from `list-cluster-nodes` |
| `HyperNode.NotFound` | HyperNodeId does not exist | Re-pick via HITL from `list-cluster-hyper-nodes` |
| `DiagnosticNotFound` / `Diagnostic.NotFound` | DiagnosticId does not exist / has expired | Check for cross-account / cross-Region calls; re-query `list-diagnostic-results` via HITL |
| `Image.NotFound` | The ImageId for reimage does not exist | Re-pick via HITL from `list-images` |

---

## State conflict

| ErrorCode | Meaning | Handling |
|---|---|---|
| `OperationConflict` | An in-progress task exists on the node / cluster | HITL two-way pick: wait / cancel and reschedule |
| `NodeStateNotMatch` | The node state does not allow this operation (e.g., stop-nodes on a Stopped node) | Re-evaluate via HITL |
| `NodeNotInCluster` | This NodeId does not belong to this ClusterId | Re-pick cluster + node via HITL |
| `DiagnosticInProgress` | The same node already has an InProgress diagnostic | HITL: reuse the existing DiagnosticId or cancel and re-submit |

---

## Diagnostic terminal business failures

When `describe-diagnostic-result` reaches terminal `Status=Failed` / `Status=Fail`, common `ErrorCode`s:

| ErrorCode | Meaning | Default suggestion |
|---|---|---|
| `Diag.AgentTimeout` | The on-node diagnostic agent timed out | Recommend `reboot-nodes` to wake the node, then re-diagnose |
| `Diag.HardwareECC` | GPU/HBM ECC count exceeds the threshold | Recommend `report-node-status --diagnosis-type COMPREHENSIVE` with the ECC evidence in `--description` |
| `Diag.NICDown` | One or more RoCE ports link down | Recommend trying `reboot-nodes` first; if not recovered -> `report-node-status` with the NIC details in `--description` |
| `Diag.DriverMismatch` | NVIDIA / RDMA driver version mismatches the image | Recommend `reimage-nodes` to switch to a verified image |
| `Diag.NCCLHang` | NCCL collective hang | Recommend `reboot-nodes` |

> The mapping above is only a default suggestion; the final repair action must be explicitly chosen by the user in HITL.

---

## Repair CLI business failures

| ErrorCode | Action | Meaning | Handling |
|---|---|---|---|
| `Reboot.Failed` | reboot-nodes | The reboot request was rejected by the node (management channel abnormal) | Escalate to `report-node-status` |
| `Reimage.ImageIncompatible` | reimage-nodes | ImageId incompatible with the node machine type | Re-pick via HITL from `list-images` (filter by MachineType) |
| `ReportStatus.DescriptionTooLong` | report-node-status | Description field too long | Truncate and resend |
| `Stop.AlreadyStopped` | stop-nodes | The node is already Stopped | [PASS] Treat as success and skip |
