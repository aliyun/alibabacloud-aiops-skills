# Error Codes Reference (eflo-controller OpenAPI)

> **Evidence-level statement**: All error codes below were obtained by directly reading and cross-checking the source code of the `eflo-controller-v1` project; each OpenAPI went through at least 3 rounds of source-code review. No reliance on external documentation or historical design drafts.
>
> **Scope**: This document **covers only the `Version=2022-12-15` (a.k.a. 1215)** eflo-controller implementation. Differences and compatibility logic of the 0706 (2022-07-06) and 0425 (2024-04-25) versions are out of scope.
>
> The 13 core eflo-controller OpenAPIs covered (product: eflo):
> - Cluster: `ListClusters` / `DescribeCluster` / `ExtendCluster` / `ShrinkCluster`
> - Nodes/hyper nodes inside a cluster: `ListClusterNodes`
> - Node: `DescribeNode` / `DeleteNode`
> - Node group: `ListNodeGroups` / `CreateNodeGroup` / `UpdateNodeGroup` / `ChangeNodeGroup`
> - Machine type / image: `ListMachineTypes` / `ListImages`
> - Task: `DescribeTask`

> **Note on ErrorMessage translations**: Some server-side error messages are emitted in Chinese by the source code; this document shows English renderings (rows affected are annotated "emitted in Chinese by the source code"). Match real responses by ErrorCode + HTTP status, not by message wording.

---

## 1. Per-OpenAPI Error Code Lists

Under each section heading, the `Source:` line points to the implementation file; each error entry lists **trigger condition / HTTP / ErrorCode / ErrorMessage (verbatim from code) / fixability & auto-completion suggestion**.

Fixability classification criteria:

- **Auto-fixable**: the client can infer or generate the required parameter from context (previous API responses, cluster/node-group metadata, session history) without changing user intent — auto-fill / dedupe / batch-split / substitute and retry to continue.
- **Not fixable**: involves resource-state conflicts, quota/permission limits, deprecated/incompatible resources, user-intent gaps, uniqueness conflicts (semantics cannot be auto-decided), or internal dependency failures — requires human decision or changing the resource state before retrying.

### 1.1 `ListClusters`

Source: `src/modules/cluster_manager/api/app/cluster.py` → `list_cluster(args)` (L579)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Fixability & auto-completion |
|---|---|---|---|---|
| Pydantic validation failure (`Tags` count > 20, duplicate keys, invalid length, etc.) | 400 | — (framework-level ValueError) | `parameter validation failed: <pydantic error>` (*original zh* = "parameter validation failed") | Not fixable: `Tags` is user-semantic data; deduping/truncating may break the original intent |
| `NextToken` missing/expired in Redis (`paging.py:37` raise) | 417 | `UnsatisfiedExpect` | `The request not satisfied expect Redis error: next_token_key [{token}] non-existent` | Auto-fixable: discard the stale `NextToken` and retry from the first page (without `NextToken`) |
| The paging cache for `IdListKey` is missing in Redis (`paging.py:44` raise) | 417 | `UnsatisfiedExpect` | `The request not satisfied expect Redis error: id_list_key [{key}] non-existent` | Auto-fixable: discard the stale `NextToken` and restart from the first page |
| `query_resource_group_id_map` call to the underlying TAG service failed (`cluster.py:955` raise) | 417 | `UnsatisfiedExpect` | `The request not satisfied expect query resource group info failed` | Not fixable: upstream TAG service anomaly; short retry or manual investigation |
| Other unknown exceptions (fallback) | 500 | `InternalError` | `Internal error.` | Not fixable: depends on underlying services; manual intervention required |

On success: HTTP 200, Body: `{"Clusters": [...], "NextToken": "...", "RequestId": ...}`.

- When `AccountId == "0"`, an empty `Clusters` is **returned directly** (no query is triggered), HTTP 200.
- Note: the `except CustomException` branch only fills in `ErrorMessage` and does not overwrite `ErrorCode` (current code behavior).

### 1.2 `DescribeCluster`

Source: `src/modules/cluster_manager/api/app/cluster.py` → `describe_cluster(args)` (L411)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Fixability & auto-completion |
|---|---|---|---|---|
| Pydantic validation failure (`ClusterId` missing / wrong type, etc.) | 400 | — | `parameter validation failed: <pydantic error>` (*original zh*) | Auto-fixable: if `ClusterId` is missing, call `ListClusters` to get the target cluster ID (or reuse the most recently used `ClusterId` in the session) |
| Cluster does not exist (by `ClusterId`) | **404** | `RESOURCE_NOT_FOUND` | `cluster instance {ClusterId} resource does not exist.` | Not fixable: the user-provided resource identifier is wrong; manual re-selection needed |
| `query_resource_group_id_map` call to the underlying TAG service failed (`cluster.py:955` raise; only hit on the 1215/0425 branches) | 417 | `UnsatisfiedExpect` | `The request not satisfied expect query resource group info failed` | Not fixable: upstream TAG service anomaly; short retry or manual investigation |
| Other unknown exceptions (fallback) | 500 | `InternalError` | `Internal error.` | Not fixable: depends on underlying services; manual intervention required |

On success: HTTP 200, Body: `{ResourceGroupId, CreateTime, NodeCount, NodeGroupCount, UpdateTime, ClusterDescription, OperatingState, Components, ClusterId, ClusterName, TaskId, ClusterType, VpdId, VpcId, Networks, HpnZone, EnvId, EnvName, ComputingIpVersion, OpenEniJumboFrame, VSwitchId, SecurityGroupId, IsUnderlay, RequestId}`.

### 1.3 `ListClusterNodes`

Source: `src/modules/transaction_manager/api/app/cluster.py` → `cluster_node_group_node(args)` (L3861)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Fixability & auto-completion |
|---|---|---|---|---|
| Pydantic validation failure (empty `ClusterId`, `Tags` > 20, etc.) | 400 | — | `parameter validation failed: <pydantic error>` (*original zh*) | Missing `ClusterId` is auto-fixable: call `ListClusters` to get the target cluster ID; non-compliant `Tags` is not fixable |
| Cluster does not exist | **404** | `RESOURCE_NOT_FOUND` | `cluster instance {ClusterId} resource does not exist.` | Not fixable: the user-provided resource identifier is wrong |
| Other unknown exceptions (fallback) | 500 | `InternalError` | `Internal error.` | Not fixable: depends on underlying services; manual intervention required |

On success: HTTP 200, Body: `{"Nodes": [...], "NextToken": "...", "RequestId": ...}`.

### 1.4 `DescribeNode`

Source: `src/modules/transaction_manager/api/app/node_mgt.py` → `describe_node(args)` (L1758)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Fixability & auto-completion |
|---|---|---|---|---|
| Pydantic validation failure (missing `NodeId`, etc.) | 400 | — | `parameter validation failed: <pydantic error>` (*original zh*) | Auto-fixable: if the session already has a `ClusterId`, call `ListClusterNodes` to get the target `NodeId` |
| Node does not exist (lookup of `NmNode` by `AccountId + NodeId` failed) | **404** | `RESOURCE_NOT_FOUND` | `internal error` (the code rewrites the message to `"internal error"`, not the resource name) | Not fixable: the user-provided `NodeId` is wrong |
| Upstream TAG service throttling in `query_resource_group_id_map` (`public_common/resource_group.py:112` raise) | 500 | `InternalDependencyError.RequestLimitExceeded` | `The maximum request rate permitted by the internal dependency service has been exceeded. Please try again later.` | Auto-fixable: retry with exponential backoff (initial 1s, max 3–5 attempts recommended) |
| Other ServerException from the upstream TAG service in `query_resource_group_id_map` (`public_common/resource_group.py:113` raise) | 500 | `InternalDependencyError` | `The internal dependency service occurs an error temporarily. Please try again later.` | Auto-fixable: short retry; escalate to manual investigation if it keeps failing |
| Other unknown exceptions (fallback) | 500 | — | `internal error` | Not fixable: depends on underlying services; manual intervention required |

On success: HTTP 200, Body contains `NodeId, MachineType, ImageId, ImageName, OperatingState, CreateTime, ExpiredTime, Sn, ZoneId, NodeGroupId, NodeGroupName, FileSystemMountEnabled, Hostname, Networks, HpnZone, TaskId, CommodityCode, RequestId`, etc.

### 1.5 `DeleteNode`

Source: `src/modules/transaction_manager/api/app/delete_node.py` → `delete_nodes(args)` (L46)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Fixability & auto-completion |
|---|---|---|---|---|
| Pydantic validation failure (missing `NodeId`) | 400 | — | `parameter validation failed: <pydantic error>` (*original zh*) | Auto-fixable: based on user intent, call `ListClusterNodes` to get the `NodeId` of the node to release |
| Not pay-as-you-go (`commodity_code` not in the allowed list) | **403** | `ChargeTypeViolation` | `The operation is not permitted due to charge type of the instance.` | Not fixable: subscription nodes cannot be released via this API; the unsubscribe flow is required |
| Node state machine disallows the `ReleasePostpaidService` action (Running/Using, etc.) | **403** | `IncorrectNodeStatus` | `The current status of the resource does not support this operation.` | Not fixable: the node must first be detached/stopped from workloads; the resource state cannot be changed automatically |
| Node does not exist (and it is not an idempotent re-entry on an already-Releasing node) | **404** | `InvalidNodeId.NotFound` | `Node [{NodeId}] does not exist` | Not fixable: `NodeId` is wrong or already released |
| Other unknown exceptions (physical machine / machine-type / image query failure, task creation failure, etc.) | 500 | `InternalError` | `Internal error` | Not fixable: depends on underlying services; manual intervention required |

**Idempotency semantics**: if the node is already `Releasing` (account_id prefix changed to `system-`), `delete_nodes` returns directly:

```
HTTP 200
{"HttpCode": 200, "success": true, "RequestId": ...}
```

On success (non-idempotent path): HTTP 200, Body contains only `RequestId` — **note: the DeleteNode success response does NOT return a TaskId** (the source code only logs it and does not put it into the result).

### 1.6 `ExtendCluster`

Source: `src/modules/transaction_manager/api/app/expansion.py`
- Main function `extend_cluster(args)` (scaling with existing nodes)
- Paid expansion `extend_cluster_and_pay_node(args)` (purchasing new nodes)
- Preflight checks `check_extend_cluster` / `check_extend_cluster_and_pay_node`
- Entry parameter model `ExtendArguments`, with root_validators doing combined validation of version / node group / password, etc.

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Fixability & auto-completion |
|---|---|---|---|---|
| Pydantic validation: `ClusterId` required | 400 | — | `parameter validation failed: <pydantic error>` (*original zh*) | Auto-fixable: call `ListClusters` to pick the target cluster `ClusterId` for expansion |
| Pydantic validation: group expansion allows only a single group | 400 | — | `parameter validation failed: Group expansion only supports a single group.` (*original zh* prefix) | Not fixable: user-intent conflict; split into multiple expansions |
| Pydantic validation: `SavingsPlanId` conflicts with `ChargeType` | 400 | — | `parameter validation failed: SavingsPlanId {xxx} is not allowed to be used with ChargeType {yyy}` (*original zh* prefix) | Not fixable: the billing model is a user decision |
| Pydantic validation: invalid password format (8-30 chars, upper/lower/digits/special) | 400 | — | `parameter validation failed: <pydantic error>` (*original zh*) | Not fixable: the password is a user credential; it cannot be auto-generated/replaced |
| Pydantic validation: `NodeGroupId` does not exist | 400 | — | `parameter validation failed: NodeGroupId {xxx} is not exist` (*original zh* prefix) | Not fixable: `NodeGroupId` reflects the expansion-target intent; a random substitute cannot be chosen |
| Pydantic validation: node group has no password/key pair to inherit | 400 | — | `parameter validation failed: The node group does not have a password/key pair to inherit.` (*original zh* prefix) | Not fixable: the user must explicitly provide a password or key pair |
| Pydantic validation: missing required items such as `NodeGroup.Az/NodeGroupName/MachineType` | 400 | — | `parameter validation failed: <pydantic error>` (*original zh*) | Auto-fixable: if expanding an existing group, call `ListNodeGroups` to look up the `NodeGroupId` and fill `Az/NodeGroupName/MachineType`; if creating a new group, call `DescribeCluster` to get the cluster's available `Az` |
| Cluster/env/group/host does not exist | 400 | — | `cluster/env/host group/host does not exist` family | Not fixable: resource identifier is wrong |
| Cluster state is not Running (e.g. Extending/Cutting) | 400 | — | `The cluster is not in Running state, not allowed to extend.` | Not fixable: wait for the previous task to finish; can combine with `DescribeTask` polling, then manual retry |
| Cluster type does not support expansion | 400 | — | `Unsupported cluster type {xxx}` | Not fixable: cluster type is an inherent attribute |
| VPC switch not allowed | 400 | — | `vpc not allowed to switch` family | Not fixable: VPC is an inherent attribute of the cluster |
| MachineType / AZ / HpnZone inconsistent with the existing node group | 400 | — | specific "MachineType/Az/HpnZone not same" wording | Auto-fixable: call `ListNodeGroups` to get the group's existing `MachineType/Az/HpnZone` and align |
| No permission to use the image | 400 | `InvalidParameter` | `The specified parameter {ImageId} is not valid.` | Not fixable: image permission is controlled at the account level |
| Image deprecated | 400 | `DeprecatedImage` | `Image {ImageId} is deprecated.` | Auto-fixable: call `ListImages` to pick a non-deprecated image with the same `Platform/Architecture` and substitute `ImageId` |
| Key pair does not exist | 400 | — | `Key pair not found` | Not fixable: the key pair is a user credential |
| `VpcId / VSwitchId` missing (when required) | 400 | `InvalidParameter` | `The specified parameter {name} is not valid.` | Auto-fixable: call `DescribeCluster` to get the cluster's `VpcId/VSwitchId` |
| `Nodes/HyperNodes` missing | 400 | `MissingParameter` | `{name} is mandatory for this action.` | Not fixable: the expansion scale is user intent |
| `local/cloud disk image` mismatch, virtualization does not support DataDisk, task_id generation failure | **417** | `UnsatisfiedExpect` | `The request not satisfied expect {detail}` | Not fixable: disk/virtualization are machine-type–image combination constraints |
| Node/hyper-node state machine disallows expansion (`StateMachineException`) | **417** | `UnsatisfiedExpect` | `The status of the hypernode or node does not meet the condition of {action}` | Not fixable: wait for the state machine transition; it cannot be changed automatically |
| Other unknown exceptions (fallback) | 500 | — | `Internal error` | Not fixable: depends on underlying services; manual intervention required |

> Errors in the Pydantic validation phase are triggered by `ValueError`s raised from `ExtendArguments` validators / root_validators; errors in the action execution phase are raised from internal branches of `check_extend_cluster` / `extend_cluster`.

On success: HTTP 200, Body: `{"TaskId": "<task-id>", "RequestId": ...}` (same structure for both existing-node expansion `extend_cluster` and new-purchase expansion `extend_cluster_and_pay_node`).

### 1.7 `ShrinkCluster`

Source: `src/modules/transaction_manager/api/app/shrink.py` → `shrink_cluster(args)` (L94)

| Trigger condition (code location) | HTTP | ErrorCode | ErrorMessage | Fixability & auto-completion |
|---|---|---|---|---|
| Pydantic validation failure | 400 | — | `parameter validation failed: <pydantic error>` (*original zh*) | Missing `ClusterId/NodeGroupId` is auto-fixable (call `ListClusters` / `ListNodeGroups` to fill); other fields are not fixable |
| Cluster does not exist (L184-L187) | 400 | — | `Cluster instance {ClusterId} does not exist` | Not fixable: resource identifier is wrong |
| Current number of shrinking ACK nodes exceeds the limit (L177-L183) | 400 | — | `The current number of shrinking nodes exceeds the limit {RELEASE_ACK_NODES_SIZE}` | Not fixable: wait for concurrent shrinks to finish; quota-related |
| Node group does not exist (L232) | 400 | — | `Host group {NodeGroupId} does not exist` | Not fixable: resource identifier is wrong |
| Both `Nodes` and `HyperNodes` are empty (L247-L250) | 400 | — | `Host/Hypernode does not exist` family | Not fixable: the shrink targets are user intent |
| The node group contains tray nodes (L330) | 400 | — | `Tray node ids not allowed in Nodes` | Auto-fixable: call `ListClusterNodes` to identify tray nodes, remove them and retry |
| Unexpected parent task count (L342-L345) | 400 | — | `Unexpected parent task count` | Not fixable: task metadata anomaly; manual investigation needed |
| `IgnoreFailedNodes=False` and failed nodes exist (L352) | 400 | — | `IgnoreFailedNodes is False` | Not fixable: whether to ignore failed nodes is a user decision; it must not be auto-flipped to True |
| The previous shrink task is still running (L356-L359) | 400 | — | `task is still running` | Auto-fixable: poll the previous task with `DescribeTask` and retry after it completes |
| Unexpected subtask count (L378) | 400 | — | `Unexpected subtask count` | Not fixable: task metadata anomaly |
| Node/hyper-node machine state disallows shrink (L420-L425) | 400 | — | `machine state {state} not allowed to shrink` | Not fixable: wait for the state machine transition |
| `task_meta` missing or `task_id` generation failure (L569-L577) | **417** | `UnsatisfiedExpect` | `The request not satisfied expect {detail}` | Not fixable: internal task generation failed |
| `IntegrityError` (task DB write failure, L683-L685) | **417** | `IntegrityError` | exception message passed through | Not fixable: DB conflict; manual intervention required |
| `StateMachineException` (L692-L694) | **417** | — | `The status of the hypernode or node does not meet the condition of {action}` | Not fixable: wait for the state machine transition |
| Other unknown exceptions (L700-L705) | 500 | — | `Internal error` | Not fixable: depends on underlying services; manual intervention required |

On success: HTTP 200, Body: `{"TaskId": "<task-id>", "RequestId": ...}`.

### 1.8 `ListNodeGroups`

Source: `src/modules/transaction_manager/api/app/node_group.py` → `list_node_groups(args)` (L78)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Fixability & auto-completion |
|---|---|---|---|---|
| Pydantic validation failure (`ClusterId` type, etc.) | 400 | — | `parameter validation failed: <pydantic error>` (*original zh*) | Not fixable: type errors are caller SDK/code issues |
| `POP_PARAMS_CHECK_SUPPLEMENT_SWITCH=ON` and `ClusterId` empty (`node_group.py:107` raises `CustomException`) | 400 | `MissingParameter` | `ClusterId is mandatory for this action.` | Auto-fixable: call `ListClusters` to pick the target cluster and fill `ClusterId` |
| `POP_PARAMS_CHECK_SUPPLEMENT_SWITCH=ON` and the cluster for `ClusterId` does not exist (`node_group.py:112` raises `CustomException`) | 400 | `InvalidParameter` | `The specified parameter ClusterId is not valid.` | Not fixable: resource identifier is wrong |
| The cluster referenced by a group cannot be found in the cluster table (`node_group.py:125` raises `CustomException`) | 400 | `InvalidParameter` | `The specified parameter Cluster id on the group {ids}, It cannot be found in the cluster table is not valid.` | Not fixable: data inconsistency; backend investigation needed |
| Other unknown exceptions (fallback) | 500 | — | `Internal error` | Not fixable: depends on underlying services; manual intervention required |

Note: the 3 `CustomException` branches above exhaust all `raise CustomException` locations inside `list_node_groups`; `get_custom_image_obj` (L141-L151) is swallowed by `try/except Exception` and never re-raised, hence no other `CustomException` entries in the table.

On success: HTTP 200, Body: `{"Groups": [...], "RequestId": ...}`.

### 1.9 `CreateNodeGroup`

Source: `src/modules/transaction_manager/api/app/node_group.py` → `create_node_group(args)` (L350)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Fixability & auto-completion |
|---|---|---|---|---|
| Pydantic validation failure | 400 | — | `parameter validation failed: <pydantic error>` (*original zh*) | Not fixable: Pydantic failures are mostly parameter type/format errors; fix the SDK/calling code |
| Missing `NodeGroup.Az` | 400 | `MissingParameter` | `NodeGroup.Az is mandatory for this action.` | Auto-fixable: call `DescribeCluster` to get the cluster's available `Az`, or reference an existing group's `Az` via `ListNodeGroups` |
| Missing `NodeGroup.NodeGroupName` | 400 | `MissingParameter` | `NodeGroup.NodeGroupName is mandatory for this action.` | Auto-fixable: generate a default `NodeGroupName` with the `<ClusterName>-ng-<timestamp>` template |
| ClusterId does not exist | 400 | `InvalidParameter` | `The specified parameter ClusterId is not valid.` | Not fixable: resource identifier is wrong |
| No permission to use the private image/machine type | 400 | `InvalidParameter` | `Have no permission to use private image/machine type {name}` | Not fixable: permission depends on account-level authorization |
| No permission to use the image | 400 | `InvalidParameter` | `image {ImageId} does not have permission to use` | Not fixable: image permission is authorized at the account level |
| `MachineType` not found | 400 | — | `MachineType {name} cannot be found` | Not fixable: machine-type choice is user intent; auto-substitution would change the spec |
| Network pattern mismatch | 400 | — | `network pattern don't match` | Not fixable: network architecture vs machine type is an inherent constraint |
| Machine type does not support jumbo frame | 400 | — | `Machine type {mt} does not support jumbo frame` | Not fixable: the capability is determined by the machine type |
| `ImageId` does not exist | 400 | — | `image id {ImageId} cannot be found` | Not fixable: image choice is user intent |
| Image does not support Cloud Assistant | 400 | — | `image {ImageId} does not support CloudAssistant` | Auto-fixable: call `ListImages` to pick a Cloud-Assistant-capable `ImageId` with the same platform/architecture |
| Cluster type does not support node groups (`PermissionError`) | **403** | `PermissionError` | `cluster type {type} not allowed to create node group` | Not fixable: cluster type is an inherent attribute |
| Underlay-cluster node groups must specify `RamRoleName` | **417** | `UnsatisfiedExpect` | `The request not satisfied expect RamRoleName` | Not fixable: RAM Role binding is a user security decision; it must not be auto-specified |
| Non-cloud-disk node group validations failed | **417** | `UnsatisfiedExpect` | `The request not satisfied expect {detail}` | Not fixable: disk/machine-type constraint 417 |
| `NodeGroupName` uniqueness conflict | **417** | `IntegrityError` | `{raw DB exception message}` | Auto-fixable: append a timestamp/short-hash suffix to the original `NodeGroupName` and retry |
| Dedicated image/machine type count mismatch (internal data anomaly) | 500 | — | `inner error: private image/machine type count mismatch` | Not fixable: internal data anomaly; backend investigation needed |
| Failed to query network mode | 500 | — | `Failed to query network mode` | Not fixable: dependency service failure |
| Key pair does not exist | 500 | — | `key pair {name} not found` | Not fixable: the key pair is a user credential |
| ACK / Serverless software instance does not exist | 500 | — | `Software/software instance does not exist` | Not fixable: underlying instance missing; backend investigation needed |
| Other unknown exceptions (fallback) | 500 | — | `Internal error` | Not fixable: depends on underlying services; manual intervention required |

On success: HTTP 200, Body: `{"NodeGroupId": "ng-xxxxxx", "RequestId": ...}`.

### 1.10 `UpdateNodeGroup`

Source: `src/modules/cluster_manager/api/app/node_group.py` → `update_node_group(args)` (L395)

| Trigger condition (code location) | HTTP | ErrorCode | ErrorMessage | Fixability & auto-completion |
|---|---|---|---|---|
| Pydantic validation failure | 400 | — | `parameter validation failed: <pydantic error>` (*original zh*) | Missing `NodeGroupId` is auto-fixable (fill via `ListNodeGroups`); other format/type errors are not fixable |
| `NodeGroupId` does not exist (L406-L409) | 400 | — | `Group instance [{NodeGroupId}] does not exist` | Not fixable: resource identifier is wrong |
| Target image invalid (L429-L430) | 400 | `InvalidParameter` | `The specified parameter {ImageId} is not valid.` | Not fixable: image choice is user intent; auto-substitution would change the environment |
| No permission to use the image (L432-L434) | 400 | `InvalidParameter` | `image {ImageId} does not have permission to use` | Not fixable: image permission is authorized at the account level |
| Key pair does not exist (L447-L449, ValueError) | 400 | — | `Key pair {name} does not exist` | Not fixable: the key pair is a user credential |
| Target image deprecated (L490-L493) | 400 | `DeprecatedImage` | `Image {ImageId} is deprecated.` | Auto-fixable: call `ListImages` to pick a non-deprecated image with the same platform/architecture |
| `enable_node_group_file_system_mount` path: cluster does not exist | 400 | `InvalidParameter` | `The specified parameter ClusterId is not valid.` | Not fixable: resource identifier is wrong |
| `enable_node_group_file_system_mount` path: not DPU and not net_arch 7.0 | 400 | — | `only DPU machine types with network architecture 7.0 may initiate the mount-supplement operation` (emitted in Chinese by the source code) | Not fixable: cluster attributes do not satisfy the requirement |
| `enable_node_group_file_system_mount` path: dedicated bare cluster unsupported (`ARGS_TYPE_SUPPORT_ERROR`) | 400 | — | `The cluster type {type} does not allowed.` | Not fixable: cluster type unsupported |
| `enable_node_group_file_system_mount` path: host state update failed | 400 | — | `The host update failed` | Not fixable: underlying update failed |
| Key pair check failed (L443-L446) | **417** | `UnsatisfiedExpect` | `The request not satisfied expect check key pair failed` | Not fixable: the user must confirm the key pair status |
| `FileSystemMountEnabled` cannot be disabled (L502-L508) | **417** | `UnsatisfiedExpect` | `The request not satisfied expect FileSystemMountEnabled are not supported to be closed` | Not fixable: once mount is enabled it cannot be disabled |
| FileSystemMount API not opened to the current user (L513-L518) | **417** | `UnsatisfiedExpect` | `The request not satisfied expect This api is not open to current user` | Not fixable: allowlist-controlled |
| `NewNodeGroupName` uniqueness conflict (L532-L535) | **417** | `IntegrityError` | `{raw DB exception message}` | Auto-fixable: append a timestamp/short-hash suffix to the original `NewNodeGroupName` and retry |
| `enable_node_group_file_system_mount` path: cluster already has CPFS mounted | **417** | `UnsatisfiedExpect` | `The request not satisfied expect CPFS` | Not fixable: a mount already exists |
| `enable_node_group_file_system_mount` path: image does not support Cloud Assistant | **417** | `UnsatisfiedExpect` | `The request not satisfied expect custom_msg` (Images does not support assistant cloud.) | Auto-fixable: call `ListImages` to pick a Cloud-Assistant-capable `ImageId` with the same platform |
| `enable_node_group_file_system_mount` path: node state mismatch | **417** | `UnsatisfiedExpect` | `node {ids} state does not qualify; required states are [Using, ...]` (emitted in Chinese by the source code) | Not fixable: wait for the state machine transition |
| Other unknown exceptions (fallback, L555-L557) | 500 | — | `Internal error {exception}` | Not fixable: depends on underlying services; manual intervention required |

On success (synchronous change, e.g. description update): HTTP 200, Body: `{"RequestId": ...}`.
On success (asynchronous change, e.g. KeyPairName/LoginPassword/FileSystemMount): HTTP 200, Body: `{"TaskId": "<task-id>", "RequestId": ...}`.

### 1.11 `ChangeNodeGroup`

Source: `src/modules/transaction_manager/api/app/node_change_group.py` → `change_nodegroup(args_obj)` (L530)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Fixability & auto-completion |
|---|---|---|---|---|
| Pydantic validation failure | 400 | — | `parameter validation failed: <pydantic error>` (*original zh*) | Not fixable: Pydantic failures are mostly parameter type/format errors |
| `Nodes` count > 500 (L530-L555) | 400 | — | `The number of nodes cannot exceed 500.` | Auto-fixable: split `Nodes` into batches of `≤500` and call sequentially |
| RAM Role inconsistent | 400 | — | `RAM Role not consistent` | Not fixable: source/target group RAM Role conflict; manual alignment needed |
| `target_node_group_id` empty | 400 | — | `target_node_group_id is empty` | Not fixable: the migration target is user intent |
| `node_ids` empty | 400 | — | `node_ids cannot be empty` | Not fixable: the migration targets are user intent |
| `node_ids` contains duplicates | 400 | — | `node_ids not unique` | Auto-fixable: dedupe `node_ids` and retry |
| Node/hyper node does not exist | 400 | — | `nodes may not exist: {ids}` | Not fixable: the user-provided `node_ids` are wrong |
| Input contains tray nodes | 400 | — | `tray node id not valid: {ids}` | Auto-fixable: call `ListClusterNodes` to identify and remove tray nodes, then retry |
| Source nodes span multiple groups | 400 | — | `source nodes must be in one group` | Not fixable: the user must split into multiple calls |
| Source or target group does not exist | 400 | — | `group does not exist` | Not fixable: resource identifier is wrong |
| Source/target groups not in the same cluster | 400 | — | `not in same cluster` | Not fixable: the API does not support cross-cluster migration |
| Source/target group machine types differ | 400 | — | `not in same machine type` | Not fixable: machine-type constraint |
| Source/target group disk types differ | 400 | — | `not in same disk type` | Not fixable: disk-type constraint |
| `file_mount_enabled` differs | 400 | — | `file_mount not same` | Not fixable: mount-attribute constraint |
| `Serverless` / `ExclusiveDpuServerlessCluster` unsupported | 400 | — | `cluster type {type} not supported` | Not fixable: cluster type unsupported |
| `netarch 7.0` unsupported (CustomException) | 400 | `InvalidParameter` | `The specified parameter netarch is not valid.` | Not fixable: network-architecture constraint |
| Node not in Using state | 400 | — | `Node not in Using state` | Not fixable: the node must be put into Using state first |
| Hyper node not in Using state | 400 | — | `Hypernode not in Using state` | Not fixable: the hyper node must be put into Using state first |
| ACK nodes require Cloud Assistant support | 400 | — | `ACK node requires cloud assistant support` | Not fixable: image capability constraint |
| ACK cluster shrinking-node count exceeds the limit | 400 | — | `ACK shrinking nodes exceeds limit` | Not fixable: wait for concurrent shrinks to finish; quota-related |
| Node/hyper-node state machine disallows (`StateMachineException`) | **417** | `UnsatisfiedExpect` | `The status of the hypernode or node does not meet the condition of {action}` | Not fixable: wait for the state machine transition |
| Other unknown exceptions (fallback) | 500 | — | `Internal error` | Not fixable: depends on underlying services; manual intervention required |

On success: HTTP 200, Body: `{"TaskId": "<task-id>", "RequestId": ...}`.

### 1.12 `ListMachineTypes`

Source: `src/modules/transaction_manager/api/app/private_cluster.py` → `private_list_machine_type(args_obj)` (L72)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Fixability & auto-completion |
|---|---|---|---|---|
| Pydantic validation failure | 400 | — | `parameter validation failed: <pydantic error>` (*original zh*) | Not fixable: Pydantic failures are mostly parameter type/format errors |
| Other unknown exceptions (fallback) | 500 | — | `Internal error` | Not fixable: depends on underlying services; manual intervention required |

**No business-level error branches**; normal business failures all go through the generic 500 fallback. On success: HTTP 200, Body: `{"MachineTypes": [...], "RequestId": ...}`.

### 1.13 `ListImages`

Source: `src/modules/transaction_manager/api/app/private_cluster.py` → `private_list_system_image(args_obj)` (L370)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Fixability & auto-completion |
|---|---|---|---|---|
| Pydantic validation failure (`Platform`/`Architecture` split error) | 400 | — | `parameter validation failed: <pydantic error>` (*original zh*) | Not fixable: `Platform`/`Architecture` must be passed by the user per the spec |
| Other unknown exceptions (fallback) | 500 | — | `Internal error` | Not fixable: depends on underlying services; manual intervention required |

**No business-level error branches**. On success: HTTP 200, Body: `{"Images": [...], "RequestId": ...}`.

### 1.14 `DescribeTask`

Source: `src/modules/task_manager/api/service/describe_task.py` → `Describe_task(action_params, ...)` (L161)

Note: the entry of `task_manager` (`common/views.py`) differs from `transaction_manager`; `DescribeTask` returns a `{"ErrorCodeInfo": {...}}` structure produced by `make_error_code_body`, unpacked by the upper-layer view according to the POP version.

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Fixability & auto-completion |
|---|---|---|---|---|
| Other business exceptions (L278-L286) | **200** | `""` (empty string) | `str(e)` (raw exception text); note ErrorCodeInfo.HttpStatusCode=200 is the current code behavior | Not fixable: internal exception; check `ErrorCodeInfo.Success=False` and investigate manually |
| Missing `TaskId` (`params_check` decorator) | **400** | `MissingParameter` | `TaskId is mandatory for this action.` | Auto-fixable: extract `TaskId` from the preceding `ExtendCluster/ShrinkCluster/ChangeNodeGroup/UpdateNodeGroup/DeleteNode` response |
| Parameter type error / JSON parse error / DB error | **400** | `InvalidParameter` | `The specified parameter {paramName} is not valid.` | Not fixable: the parameter block format is wrong; fix the calling code |
| Task does not exist | **400** | `Resource.NotFound` | `The task {TaskId} is not found.` (from `RESOURCE_NOT_FOUND_MESSAGE` % ("task", task_id)) | Not fixable: `TaskId` is wrong or the task has been GC'd |

On success: HTTP 200, Body: `{TaskType, TaskState, CreateTime, UpdateTime, Message, Steps, NodeIds, ClusterName, ClusterId, (Fault,) RequestId}`.

---

## 2. Cross-API Common Error Code Mapping

Aggregated by HTTP status code for easy classification in front-ends/scripts:

### 2.1 HTTP 400 — Request parameter errors

| ErrorCode | Typical source | Description |
|---|---|---|
| `MissingParameter` | Triggered by any CustomException | Required parameter missing |
| `InvalidParameter` | Triggered by any CustomException | Invalid parameter value / no resource permission |
| `Resource.NotFound` | `CustomException(..., RESOURCE_NOT_FOUND)` branches or DescribeTask | Resource (cluster/node/node group/task) does not exist (business layer) |
| `DeprecatedImage` | ExtendCluster / UpdateNodeGroup | Image deprecated |
| `CustomImageError` | Extend/Create/UpdateNodeGroup | Custom image anomaly |
| `IpReserveFailed` | Internal branch of Extend | VPC IP reservation failed |
| `ExceedLimit` | Internal branch of Extend | Spec limit exceeded |
| `DpuMissingIpAllocationPolicy` | Internal branch of Extend | DPU missing IP allocation policy |
| `InvalidNodeId.NotFound` | DeleteNode | Node does not exist (fixed-string error code) |
| `ChargeTypeViolation` | DeleteNode | Non-pay-as-you-go nodes cannot be released |
| `IncorrectNodeStatus` | DeleteNode | Node state does not allow release |
| (empty) "The group [xxx] does not exist" (400) | DeleteNodeGroup | Group does not exist or does not belong to this cluster (verified 2026-08-19) |
| (empty) "There is only one group in the cluster, which cannot be deleted" (400) | DeleteNodeGroup | Last-group protection: the cluster's last group cannot be deleted (verified 2026-08-19) |
| (empty) `parameter validation failed` (emitted in Chinese by the source code) | Pydantic validation of all eflo APIs | Body contains only `ErrorMessage` |

### 2.2 HTTP 403 — Forbidden by permission/business constraints

| ErrorCode | Typical source |
|---|---|
| `PermissionError` | CreateNodeGroup (cluster type does not match node group) |
| `ObjectNotExists` | A few branches return "not found" as a permission failure |
| `ChargeTypeViolation` | DeleteNode |
| `IncorrectNodeStatus` | DeleteNode |
| `InvalidAccount.PermissionDenied` | Gateway layer (api_router); DeleteNodeGroup also returns this code when `--cluster-id` is missing ("Field arguments error", verified 2026-08-19) |

### 2.3 HTTP 404 — Resource does not exist (framework layer)

| ErrorCode | Typical source |
|---|---|
| `RESOURCE_NOT_FOUND` (from `public_common/error_code.py`) | ListClusters / DescribeCluster / ListClusterNodes |
| `RESOURCE_NOT_FOUND` (from the http=404 ObjectDoesNotExist early-exit branch in `public_common/exception/custom_exceptions.py`) | DescribeNode, DeleteNode node-not-found |
| `InvalidAccount.NotFound` | Gateway layer (api_router) |

> The business-layer `CustomException(..., RESOURCE_NOT_FOUND)` maps to **HTTP 400**, which must be distinguished from the framework-layer `ErrorInfo` 404.

### 2.4 HTTP 410 — Insufficient quota

| ErrorCode | Typical source |
|---|---|
| `InsufficientQuota` | ExtendCluster new-purchase phase |

### 2.5 HTTP 417 — Business expectation not satisfied

| ErrorCode | Typical source |
|---|---|
| `UnsatisfiedExpect` | State machine of Extend/Shrink/Change/Create/UpdateNodeGroup, image/disk incompatibility, allowlist limits, etc. |
| `IntegrityError` | NodeGroupName uniqueness conflict in Create/UpdateNodeGroup, task DB write conflict |

**Special case**: `StateMachineException` (`inner_state_machine` in `public_common/common.py`) is also caught by each action and returned as `UnsatisfiedExpect`, with fixed wording:

```
The status of the hypernode or node does not meet the condition of {action}
```

### 2.6 HTTP 500 — Internal errors

| ErrorCode | Typical source |
|---|---|
| `InternalError` | The `except Exception` fallback of all actions |
| `InternalDependencyError` (`DEPENDENCY_ERROR`) | Underlying dependency services (ECS/VPC/underlay network) failed |

The HTTP 500 `ErrorMessage` is usually `Internal error` or `Internal error {exception}`; some actions return `internal error` (lowercase, e.g. DescribeNode).

---

## 3. Idempotency and Retry Notes

Per the source-code implementation, the following APIs have explicit idempotency/re-entry handling:

### 3.1 `DeleteNode` (naturally idempotent)

- Source: `delete_node.py` L98-L110
- If the node has already entered the `Releasing` state (its `account_id` prefix changed to `system-`), a second call returns HTTP 200 directly: `{"HttpCode": 200, "success": true, "RequestId": ...}`.
- If the node does not exist (and is not `Releasing`), HTTP 404 `InvalidNodeId.NotFound` is returned.

### 3.2 `ExtendCluster` / `ShrinkCluster` / `ChangeNodeGroup` (async tasks are queryable)

- All three APIs return a `TaskId`; **the business side should use `ClientToken` or match on `TaskId` for idempotency control**. The source code has no built-in ClientToken dedupe — repeated calls create duplicate tasks.
- The node/hyper-node state machine (`inner_state_machine`) returns 417 on a second attempt, preventing concurrent operations on the same resource.

### 3.3 `CreateNodeGroup` / `UpdateNodeGroup`

- `NodeGroupName` is a unique key; duplicate creation returns HTTP 417 `IntegrityError`.
- Updating key pair / password / file-system mount creates an async task; repeated calls likewise create duplicate tasks — **callers must implement idempotency themselves**.

### 3.4 Read APIs (`List*` / `Describe*`)

- Read APIs are side-effect-free and safe to retry.
- `DescribeTask` returns `TaskState` for polling; the internal-exception branch at L278-L286 returns HTTP 200 + `ErrorCodeInfo.Success=False` — **callers must check `ErrorCodeInfo`, not just the HTTP 200 status**.

---

## 4. Version Notes

This document **targets only the `Version=2022-12-15` (1215) version**.

- Request header: `x-acs-eflo-pop-version: 2022-12-15`
- Required parameters uniformly use `ClusterId` (instead of `EnvName + ClusterName`).
- Response structure: business data is flattened directly under the root object, plus `NextToken` / `HttpCode` / `RequestId` (not wrapped in a `Data` field).
- Error responses: uniformly generated by `entry_view`, structured as `{HttpCode, ErrorCode, ErrorMessage}`, returned with `status=http_status_code`.

Differences and compatibility logic of other versions (0706 / 0425) are out of scope; to adapt other versions, consult the `eflo-controller-v1` source code directly.
