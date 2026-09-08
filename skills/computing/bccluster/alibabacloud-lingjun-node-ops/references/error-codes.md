# Error Codes

Archived per call surface; each entry records: error code / trigger scenario / retryable or not / remedy.

---

## Common gateway layer

| Code | Meaning | Retry | Remedy |
|---|---|---|---|
| `InvalidAccessKeyId.NotFound` | AK does not exist | [FAIL] | HITL: have the user reconfigure `aliyun configure` |
| `SignatureDoesNotMatch` | wrong SK | [FAIL] | same as above |
| `Forbidden.RAM` | current account lacks the Action permission | [FAIL] | route to `alibabacloud-ram-permission-diagnose` |
| `NoPermission` | no RAM permission on the resource dimension | [FAIL] | same as above |
| `Throttling` / `Throttling.User` | throttled | [OK] 60s | automatic via safe_aliyun |
| `ServiceUnavailable` / `InternalError` | transient server-side | [OK] 2/4/8s | automatic via safe_aliyun |
| `RequestTimeout` | gateway timeout | [OK] | same as above |
| `InvalidRegionId.NotFound` | endpoint does not match region | [FAIL] | fix the endpoint, see [endpoint-routing.md](endpoint-routing.md) |

---

## eflo-controller business codes

### F1 / F2 / F3 Power

| Code | Meaning | Retry | Remedy |
|---|---|---|---|
| `InvalidNodeStatus` | node state incompatible with the operation (e.g. stop an already-Stopped node) | [FAIL] | pre-check `OperatingState` |
| `OperationConflict` | another mutating task on the same node | [FAIL] | HITL choose parallel / wait |
| `NodeNotFound` / `Node.NotFound` | NodeId does not exist or is cross-cluster | [FAIL] | redo via `list-cluster-nodes` |
| `InvalidImageId.NotFound` | F3 reimage image does not exist | [FAIL] | redo via `list-images` HITL |
| `InvalidLoginPassword` | F3 reimage password violates rules | [FAIL] | 8-30 chars, >=3 of: upper / lower / digit / special |

### F5 Node Spec Change

> The value of `--node-type` is one of the 9 NodeType enum values (cpfs/ebs/balanced x single-tenant/multi-tenant/zeroLeni), **NOT a MachineType**; see node-spec-change.md.

| Code / message | Meaning | Retry | Remedy |
|---|---|---|---|
| `The node_type xxx is not supported.` / `The specified parameter xxx is not valid.` | `--node-type` outside the 9-value enum (common: a MachineType was passed) | [FAIL] | re-pick from the NodeType enum |
| `The node_ids are not in the same group.` | multiple node groups mixed in one call | [FAIL] | split per node group and resubmit |
| `RESOURCE_INSUFFICIENT` (per node) | node's current disk / ENI / dense-ENI count exceeds the target type's quota | [FAIL] | report per node and HITL decide |
| vdpu / whitelist rejection (`These nodes are not support change node type`) | cluster vdpu <= 1.6.0 or node not in ChangeNodeTypeWhiteList | [FAIL] | explain, no retry |
| transition matrix disallows | cross single-tenant/multi-tenant or cross zeroLeni variant conversion | [FAIL] | explain the matrix constraint, do not submit |

### F6 Repair

| Code | Meaning | Retry | Remedy |
|---|---|---|---|
| `InvalidIssueCategory` | `--issue-category` value outside the enum | [FAIL] | see [api-parameters.md F6](api-parameters.md) |
| `InvalidTimeRange` | `start-time >= end-time` | [FAIL] | HITL re-elicit |
| `OperationNotApprovable` | `approve-operation` has no matching pending proposal | [FAIL] | contact the service side to confirm the notification |

### F7 Run-Command

| Code | Meaning | Retry | Remedy |
|---|---|---|---|
| `InvocationDuplicated` | `ClientToken` reused with different parameters | [FAIL] | must use a fresh UUID |
| `NodeNotInCloudAssistant` | cloud-assistant not installed on the node | [FAIL] | install the cloud-assistant agent on the node side |
| `InvalidCommandContent` | script encoding error / length >16KB | [FAIL] | fix and resubmit |

### F8 Node Group

| Code | Meaning | Retry | Remedy |
|---|---|---|---|
| `MissingParameter.NewNodeGroupName` | doc-hallucination | [FAIL] | back-fill from `describe-node-group.NodeGroupName` |
| `NodeGroupNotEmpty` | deleting a non-empty group (this Skill does not delete) | - | - |
| `CrossClusterMoveForbidden` | F8.2 cross-cluster migration | [FAIL] | abort immediately; tell the user to use the shrink+extend combination |

### F9 Tag / RG

| Code | Meaning | Retry | Remedy |
|---|---|---|---|
| `InvalidResourceType` | ResourceType misspelled | [FAIL] | strictly `node` / `cluster` / `Hypernode` |
| `TagKeyDuplicate` | same Key with multiple Values on one resource | [FAIL] | untag first, then tag |
| `ResourceGroupId.NotFound` | rgid does not exist | [FAIL] | redo via `resourcemanager list-resource-groups` |

---

## bssopenapi (F4 renewal)

| Code | Meaning | Retry | Remedy |
|---|---|---|---|
| `Failure to check order` | any of `ProductCode` / `ProductType` / `RenewPeriod` invalid | [FAIL] | strictly `bccluster` / `bccluster_eflocomputing_public_cn` / `[1..9, 12, 24, 36]` |
| `NotApplicable.AccountBalance` | insufficient balance | [FAIL] | HITL: user tops up then manually retries; no auto-retry |
| `InstanceNotFound` | wrong InstanceId (not e01-cn-xxx) | [FAIL] | redo via `list-cluster-nodes` |
| `RenewPeriodNotApplicable` | RenewPeriod not supported by this commodity | [FAIL] | HITL re-elicit |
| `OrderInProcess` | a previous order on the same instance is unfinished | [OK] 30s | wait then retry once; on further failure escalate to HITL |

---

## Async task layer

| TaskState | Meaning | Remedy |
|---|---|---|
| `Pending` | queued | keep polling every 30s |
| `Running` | executing | keep polling every 30s |
| `execution_success` | terminal success | run Verification |
| `execution_fail` | terminal failure | report the error immediately and attach the full `describe-task` JSON |
| `Cancelled` | user cancelled | report [paused] Not Executed |

---

## InvocationStatus (F7)

| Status | Meaning | Remedy |
|---|---|---|
| `Pending` / `Scheduled` / `Running` / `Stopping` | intermediate | keep polling every 10-30s |
| `Success` | succeeded | fetch output into the report |
| `Failed` | failed | fetch ErrorInfo + ExitCode |
| `PartialFailed` | some nodes failed | must break down InvokeNodes[*] per node |
| `Stopped` | user stopped intentionally | report [paused] |
| `Timeout` | user script timed out | report a warning; do not treat as failure |
