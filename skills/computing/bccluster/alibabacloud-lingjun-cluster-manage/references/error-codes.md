# Error Codes Reference (eflo-controller OpenAPI)

> **Evidence level declaration**: all error codes below were read and verified directly against the `eflo-controller-v1` project source code; every OpenAPI was cross-checked against the source at least 3 times. No external documentation or historical design drafts were relied upon.
>
> **Scope note**: this document **covers only the `Version=2022-12-15` (aka 1215) version** of the eflo-controller implementation. Differences and compatibility logic of the 0706 (2022-07-06) and 0425 (2024-04-25) versions are out of scope.
>
> The 13 covered core eflo-controller OpenAPIs (product eflo):
> - Cluster: `ListClusters` / `DescribeCluster` / `ExtendCluster` / `ShrinkCluster`
> - Nodes / hyper-nodes under a cluster: `ListClusterNodes`
> - Node: `DescribeNode` / `DeleteNode`
> - Node group: `ListNodeGroups` / `CreateNodeGroup` / `UpdateNodeGroup` / `ChangeNodeGroup`
> - Machine type / image: `ListMachineTypes` / `ListImages`
> - Task: `DescribeTask`

---

## 1. Per-OpenAPI Error Code Catalog

Under each section title, `Source:` points to the implementing file. Each error entry lists **trigger condition / HTTP / ErrorCode / ErrorMessage (verbatim from code) / repairability & auto-completion suggestion**.

Repairability classification criteria:

- **Auto-repairable**: the client can, without changing user intent, infer or generate the required parameter from context (previous API responses, cluster / node-group metadata, session history), then continue by auto-filling / deduplicating / batching / substituting and retrying.
- **Not repairable**: involves resource-state conflicts, quota / permission limits, deprecated / incompatible resources, user-intent-class missing values, uniqueness conflicts (semantics cannot be decided automatically), or internal dependency failures — requires human decision or a resource-state change before retry.

### 1.1 `ListClusters`

Source: `src/modules/cluster_manager/api/app/cluster.py` → `list_cluster(args)` (L579)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Repairability & auto-completion suggestion |
|---|---|---|---|---|
| Pydantic validation failure (`Tags` count >20, duplicate Key, illegal length, etc.) | 400 | — (framework-level ValueError) | `参数校验失败: <pydantic 错误>` | Not repairable: `Tags` is user semantic data; dedup / truncation may break the original intent |
| `NextToken` does not exist / expired in Redis (raised at `paging.py:37`) | 417 | `UnsatisfiedExpect` | `The request not satisfied expect Redis error: next_token_key [{token}] non-existent` | Auto-repairable: drop the stale `NextToken` and retry with a first-page request (no `NextToken`) |
| The paging cache for `IdListKey` does not exist in Redis (raised at `paging.py:44`) | 417 | `UnsatisfiedExpect` | `The request not satisfied expect Redis error: id_list_key [{key}] non-existent` | Auto-repairable: drop the stale `NextToken` and restart from the first page |
| `query_resource_group_id_map` call to the underlying TAG service failed (raised at `cluster.py:955`) | 417 | `UnsatisfiedExpect` | `The request not satisfied expect query resource group info failed` | Not repairable: upstream TAG service error; short retry or manual investigation |
| Other unknown exceptions (fallback) | 500 | `InternalError` | `Internal error.` | Not repairable: depends on underlying services, human intervention required |

On success: HTTP 200, Body: `{"Clusters": [...], "NextToken": "...", "RequestId": ...}`.

- When `AccountId == "0"`, an empty `Clusters` is **returned directly** (no query triggered), HTTP 200.
- Note: the `except CustomException` branch only back-fills `ErrorMessage` and does not overwrite `ErrorCode` (current code behavior).

### 1.2 `DescribeCluster`

Source: `src/modules/cluster_manager/api/app/cluster.py` → `describe_cluster(args)` (L411)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Repairability & auto-completion suggestion |
|---|---|---|---|---|
| Pydantic validation failure (`ClusterId` missing / wrong type, etc.) | 400 | — | `参数校验失败: <pydantic 错误>` | Auto-repairable: if `ClusterId` is missing, call `ListClusters` first to fetch the target cluster ID (or reuse the most recently used `ClusterId` in the session) |
| Cluster does not exist (queried by `ClusterId`) | **404** | `RESOURCE_NOT_FOUND` | `cluster instance {ClusterId} resource does not exist.` | Not repairable: the user-supplied resource identifier is wrong; human re-selection required |
| `query_resource_group_id_map` call to the underlying TAG service failed (raised at `cluster.py:955`, only reached on the 1215/0425 branches) | 417 | `UnsatisfiedExpect` | `The request not satisfied expect query resource group info failed` | Not repairable: upstream TAG service error; short retry or manual investigation |
| Other unknown exceptions (fallback) | 500 | `InternalError` | `Internal error.` | Not repairable: depends on underlying services, human intervention required |

On success: HTTP 200, Body: `{ResourceGroupId, CreateTime, NodeCount, NodeGroupCount, UpdateTime, ClusterDescription, OperatingState, Components, ClusterId, ClusterName, TaskId, ClusterType, VpdId, VpcId, Networks, HpnZone, EnvId, EnvName, ComputingIpVersion, OpenEniJumboFrame, VSwitchId, SecurityGroupId, IsUnderlay, RequestId}`.

### 1.3 `ListClusterNodes`

Source: `src/modules/transaction_manager/api/app/cluster.py` → `cluster_node_group_node(args)` (L3861)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Repairability & auto-completion suggestion |
|---|---|---|---|---|
| Pydantic validation failure (`ClusterId` empty, `Tags` >20, etc.) | 400 | — | `参数校验失败: <pydantic 错误>` | Missing `ClusterId` is auto-repairable: call `ListClusters` to fetch the target cluster ID; non-compliant `Tags` is not repairable |
| Cluster does not exist | **404** | `RESOURCE_NOT_FOUND` | `cluster instance {ClusterId} resource does not exist.` | Not repairable: the user-supplied resource identifier is wrong |
| Other unknown exceptions (fallback) | 500 | `InternalError` | `Internal error.` | Not repairable: depends on underlying services, human intervention required |

On success: HTTP 200, Body: `{"Nodes": [...], "NextToken": "...", "RequestId": ...}`.

### 1.4 `DescribeNode`

Source: `src/modules/transaction_manager/api/app/node_mgt.py` → `describe_node(args)` (L1758)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Repairability & auto-completion suggestion |
|---|---|---|---|---|
| Pydantic validation failure (`NodeId` missing, etc.) | 400 | — | `参数校验失败: <pydantic 错误>` | Auto-repairable: if the session already has a `ClusterId`, call `ListClusterNodes` to fetch the target `NodeId` |
| Node does not exist (querying `NmNode` by `AccountId + NodeId` fails) | **404** | `RESOURCE_NOT_FOUND` | `internal error` (code rewrites the message to `"internal error"`, not the resource name) | Not repairable: the user-supplied `NodeId` is wrong |
| Upstream TAG service throttled for `query_resource_group_id_map` (raised at `public_common/resource_group.py:112`) | 500 | `InternalDependencyError.RequestLimitExceeded` | `The maximum request rate permitted by the internal dependency service has been exceeded. Please try again later.` | Auto-repairable: retry with exponential backoff (suggested initial 1s, at most 3–5 attempts) |
| Other ServerException from upstream TAG service for `query_resource_group_id_map` (raised at `public_common/resource_group.py:113`) | 500 | `InternalDependencyError` | `The internal dependency service occurs an error temporarily. Please try again later.` | Auto-repairable: short retry; persistent failure requires manual investigation |
| Other unknown exceptions (fallback) | 500 | — | `internal error` | Not repairable: depends on underlying services, human intervention required |

On success: HTTP 200, Body includes `NodeId, MachineType, ImageId, ImageName, OperatingState, CreateTime, ExpiredTime, Sn, ZoneId, NodeGroupId, NodeGroupName, FileSystemMountEnabled, Hostname, Networks, HpnZone, TaskId, CommodityCode, RequestId`, etc.

### 1.5 `DeleteNode`

Source: `src/modules/transaction_manager/api/app/delete_node.py` → `delete_nodes(args)` (L46)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Repairability & auto-completion suggestion |
|---|---|---|---|---|
| Pydantic validation failure (`NodeId` missing) | 400 | — | `参数校验失败: <pydantic 错误>` | Auto-repairable: based on user intent, call `ListClusterNodes` to fetch the `NodeId` of the node to release |
| Not pay-as-you-go (`commodity_code` not in the allow list) | **403** | `ChargeTypeViolation` | `The operation is not permitted due to charge type of the instance.` | Not repairable: subscription nodes cannot be released via this API; use the unsubscribe flow |
| Node state machine forbids the `ReleasePostpaidService` action (Running/Using, etc.) | **403** | `IncorrectNodeStatus` | `The current status of the resource does not support this operation.` | Not repairable: the node must first be detached / stopped from business; resource state cannot be changed automatically |
| Node does not exist (and not the idempotent fallback for an already-Releasing node) | **404** | `InvalidNodeId.NotFound` | `Node [{NodeId}] does not exist` | Not repairable: `NodeId` is wrong or already released |
| Other unknown exceptions (physical machine / machine type / image query failure, task creation failure, etc.) | 500 | `InternalError` | `Internal error` | Not repairable: depends on underlying services, human intervention required |

**Idempotency semantics**: if the node is already `Releasing` (`account_id` prefixed `system-`), `delete_nodes` returns directly:

```
HTTP 200
{"HttpCode": 200, "success": true, "RequestId": ...}
```

On success (non-idempotent): HTTP 200, Body contains only `RequestId` — **note: the DeleteNode success response does not return a TaskId** (source only logs it, never back-fills it into result).

### 1.6 `ExtendCluster`

Source: `src/modules/transaction_manager/api/app/expansion.py`
- Main function `extend_cluster(args)` (extend with existing nodes)
- Paid extension `extend_cluster_and_pay_node(args)` (newly purchased nodes)
- Pre-checks `check_extend_cluster` / `check_extend_cluster_and_pay_node`
- Entry parameter model `ExtendArguments`, with a root_validator doing joint validation of version / node group / password, etc.

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Repairability & auto-completion suggestion |
|---|---|---|---|---|
| Pydantic validation: `ClusterId` required | 400 | — | `参数校验失败: <pydantic 错误>` | Auto-repairable: call `ListClusters` to select the extension target cluster `ClusterId` |
| Pydantic validation: group extension allows only a single group | 400 | — | `参数校验失败: Group expansion only supports a single group.` | Not repairable: user intent conflict; split into multiple extensions |
| Pydantic validation: `SavingsPlanId` conflicts with `ChargeType` | 400 | — | `参数校验失败: SavingsPlanId {xxx} is not allowed to be used with ChargeType {yyy}` | Not repairable: the billing model is a user decision |
| Pydantic validation: illegal password format (8-30 chars, upper/lower/digit/special) | 400 | — | `参数校验失败: <pydantic 错误>` | Not repairable: the password is user credential material and must not be auto-generated as a substitute |
| Pydantic validation: `NodeGroupId` does not exist | 400 | — | `参数校验失败: NodeGroupId {xxx} is not exist` | Not repairable: `NodeGroupId` encodes the extension target intent; a random substitute is not acceptable |
| Pydantic validation: node group has no inheritable password / key pair | 400 | — | `参数校验失败: The node group does not have a password/key pair to inherit.` | Not repairable: the user must explicitly provide a password or key pair |
| Pydantic validation: required fields such as `NodeGroup.Az/NodeGroupName/MachineType` missing | 400 | — | `参数校验失败: <pydantic 错误>` | Auto-repairable: when extending an existing group, call `ListNodeGroups` to fetch `NodeGroupId` and back-fill `Az/NodeGroupName/MachineType`; when creating a new group, call `DescribeCluster` for the cluster's available `Az` |
| Cluster / environment / group / host does not exist | 400 | — | `cluster/env/host group/host does not exist` family | Not repairable: resource identifier error |
| Cluster state not Running (e.g. Extending/Cutting) | 400 | — | `The cluster is not in Running state, not allowed to extend.` | Not repairable: wait for the preceding task to finish; optionally combine with `DescribeTask` polling then manual retry |
| Cluster type does not support extension | 400 | — | `Unsupported cluster type {xxx}` | Not repairable: cluster type is an intrinsic property |
| VPC switch not allowed | 400 | — | `vpc not allowed to switch` family | Not repairable: VPC is an intrinsic property of the cluster |
| Machine type / AZ / HpnZone inconsistent with existing node groups | 400 | — | Specific "MachineType/Az/HpnZone not same" wording | Auto-repairable: call `ListNodeGroups` to fetch the group's current `MachineType/Az/HpnZone` and align |
| No permission to use the image | 400 | `InvalidParameter` | `The specified parameter {ImageId} is not valid.` | Not repairable: image permission is controlled at account level |
| Image deprecated | 400 | `DeprecatedImage` | `Image {ImageId} is deprecated.` | Auto-repairable: call `ListImages` to pick a non-deprecated image with the same `Platform/Architecture` as a substitute `ImageId` |
| Key pair does not exist | 400 | — | `Key pair not found` | Not repairable: the key pair is user credential material |
| `VpcId / VSwitchId` missing (when required) | 400 | `InvalidParameter` | `The specified parameter {name} is not valid.` | Auto-repairable: call `DescribeCluster` to fetch the cluster's `VpcId/VSwitchId` |
| `Nodes/HyperNodes` missing | 400 | `MissingParameter` | `{name} is mandatory for this action.` | Not repairable: extension scale is user intent |
| `local/cloud disk image` mismatch, virtualization does not support DataDisk, task_id generation failure | **417** | `UnsatisfiedExpect` | `The request not satisfied expect {detail}` | Not repairable: disk / virtualization constraints of the machine-type–image combination |
| Node / hyper-node state machine forbids extension (`StateMachineException`) | **417** | `UnsatisfiedExpect` | `The status of the hypernode or node does not meet the condition of {action}` | Not repairable: must wait for state-machine transitions; cannot be changed automatically |
| Other unknown exceptions (fallback) | 500 | — | `Internal error` | Not repairable: depends on underlying services, human intervention required |

> Pydantic-stage errors are raised as `ValueError` by the `ExtendArguments` validator / root_validator; action-stage errors are raised by internal branches of `check_extend_cluster` / `extend_cluster`.

On success: HTTP 200, Body: `{"TaskId": "<task-id>", "RequestId": ...}` (same structure for both existing-node extension `extend_cluster` and newly-purchased extension `extend_cluster_and_pay_node`).

### 1.7 `ShrinkCluster`

Source: `src/modules/transaction_manager/api/app/shrink.py` → `shrink_cluster(args)` (L94)

| Trigger condition (code location) | HTTP | ErrorCode | ErrorMessage | Repairability & auto-completion suggestion |
|---|---|---|---|---|
| Pydantic validation failure | 400 | — | `参数校验失败: <pydantic 错误>` | Missing `ClusterId/NodeGroupId` is auto-repairable (back-fill via `ListClusters` / `ListNodeGroups`); other fields not repairable |
| Cluster does not exist (L184-L187) | 400 | — | `Cluster instance {ClusterId} does not exist` | Not repairable: resource identifier error |
| ACK cluster shrink node count exceeds the concurrent limit (L177-L183) | 400 | — | `The current number of shrinking nodes exceeds the limit {RELEASE_ACK_NODES_SIZE}` | Not repairable: wait for concurrent shrinks to finish; involves quota |
| Node group does not exist (L232) | 400 | — | `Host group {NodeGroupId} does not exist` | Not repairable: resource identifier error |
| `Nodes` and `HyperNodes` both empty (L247-L250) | 400 | — | `Host/Hypernode does not exist` family wording | Not repairable: shrink targets are user intent |
| Node group contains tray nodes (L330) | 400 | — | `Tray node ids not allowed in Nodes` | Auto-repairable: call `ListClusterNodes` to identify tray nodes, remove them, and retry |
| Unexpected parent task count (L342-L345) | 400 | — | `Unexpected parent tasks count` | Not repairable: task metadata anomaly; manual investigation required |
| `IgnoreFailedNodes=False` with failed nodes present (L352) | 400 | — | `IgnoreFailedNodes is False` | Not repairable: whether to ignore failed nodes is a user decision and must not be auto-flipped to True |
| Previous shrink task still running (L356-L359) | 400 | — | `task is still running` | Auto-repairable: poll the preceding task via `DescribeTask` until completion, then retry |
| Unexpected subtask count (L378) | 400 | — | `Unexpected subtask count` | Not repairable: task metadata anomaly |
| Node / hyper-node machine state forbids shrink (L420-L425) | 400 | — | `machine state {state} not allowed to shrink` | Not repairable: must wait for state-machine transitions |
| `task_meta` missing or `task_id` generation failure (L569-L577) | **417** | `UnsatisfiedExpect` | `The request not satisfied expect {detail}` | Not repairable: internal task generation failure |
| `IntegrityError` (task DB write failure, L683-L685) | **417** | `IntegrityError` | Passthrough exception message | Not repairable: DB conflict; human intervention required |
| `StateMachineException` (L692-L694) | **417** | — | `The status of the hypernode or node does not meet the condition of {action}` | Not repairable: must wait for state-machine transitions |
| Other unknown exceptions (L700-L705) | 500 | — | `Internal error` | Not repairable: depends on underlying services, human intervention required |

On success: HTTP 200, Body: `{"TaskId": "<task-id>", "RequestId": ...}`.



### 1.8 `ListNodeGroups`

Source: `src/modules/transaction_manager/api/app/node_group.py` → `list_node_groups(args)` (L78)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Repairability & auto-completion suggestion |
|---|---|---|---|---|
| Pydantic validation failure (`ClusterId` type, etc.) | 400 | — | `参数校验失败: <pydantic 错误>` | Not repairable: type errors are caller SDK / code issues |
| `POP_PARAMS_CHECK_SUPPLEMENT_SWITCH=ON` and `ClusterId` empty (`node_group.py:107` raises `CustomException`) | 400 | `MissingParameter` | `ClusterId is mandatory for this action.` | Auto-repairable: call `ListClusters` to select the target cluster and back-fill `ClusterId` |
| `POP_PARAMS_CHECK_SUPPLEMENT_SWITCH=ON` and the cluster for `ClusterId` does not exist (`node_group.py:112` raises `CustomException`) | 400 | `InvalidParameter` | `The specified parameter ClusterId is not valid.` | Not repairable: resource identifier error |
| The cluster corresponding to a group cannot be found in the cluster table (`node_group.py:125` raises `CustomException`) | 400 | `InvalidParameter` | `The specified parameter Cluster id on the group {ids}, It cannot be found in the cluster table is not valid.` | Not repairable: data inconsistency; backend investigation required |
| Other unknown exceptions (fallback) | 500 | — | `Internal error` | Not repairable: depends on underlying services, human intervention required |

Note: the 3 `CustomException` branches above exhaust all `raise CustomException` sites inside `list_node_groups`; `get_custom_image_obj` (L141-L151) is swallowed by `try/except Exception` and never re-raised, hence no other `CustomException` entries appear in the table.

On success: HTTP 200, Body: `{"Groups": [...], "RequestId": ...}`.

### 1.9 `CreateNodeGroup`

Source: `src/modules/transaction_manager/api/app/node_group.py` → `create_node_group(args)` (L350)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Repairability & auto-completion suggestion |
|---|---|---|---|---|
| Pydantic validation failure | 400 | — | `参数校验失败: <pydantic 错误>` | Not repairable: Pydantic failures are mostly parameter type / format errors; fix the SDK / calling code |
| `NodeGroup.Az` missing | 400 | `MissingParameter` | `NodeGroup.Az is mandatory for this action.` | Auto-repairable: call `DescribeCluster` for the cluster's available `Az`, or consult `ListNodeGroups` for existing groups' `Az` |
| `NodeGroup.NodeGroupName` missing | 400 | `MissingParameter` | `NodeGroup.NodeGroupName is mandatory for this action.` | Auto-repairable: generate a default `NodeGroupName` from the `<ClusterName>-ng-<timestamp>` template |
| ClusterId does not exist | 400 | `InvalidParameter` | `The specified parameter ClusterId is not valid.` | Not repairable: resource identifier error |
| No permission to use private image / machine type | 400 | `InvalidParameter` | `Have no permission to use private image/machine type {name}` | Not repairable: permission depends on account-level authorization |
| No permission to use the image | 400 | `InvalidParameter` | `image {ImageId} does not have permission to use` | Not repairable: image permission is granted at account level |
| `MachineType` not found | 400 | — | `MachineType {name} cannot be found` | Not repairable: machine-type selection is user intent; auto-substitution would change the spec |
| Network pattern mismatch | 400 | — | `network pattern don't match` | Not repairable: network architecture and machine type are intrinsic constraints |
| Machine type does not support jumbo frame | 400 | — | `Machine type {mt} does not support jumbo frame` | Not repairable: the capability is determined by the machine type |
| `ImageId` does not exist | 400 | — | `image id {ImageId} cannot be found` | Not repairable: image selection is user intent |
| Image does not support Cloud Assistant | 400 | — | `image {ImageId} does not support CloudAssistant` | Auto-repairable: call `ListImages` to pick an image with the same platform / architecture that supports Cloud Assistant |
| Cluster type does not support node groups (`PermissionError`) | **403** | `PermissionError` | `cluster type {type} not allowed to create node group` | Not repairable: cluster type is an intrinsic property |
| Underlay cluster node groups must specify `RamRoleName` | **417** | `UnsatisfiedExpect` | `The request not satisfied expect RamRoleName` | Not repairable: RAM Role binding is a user security decision; must not be auto-specified |
| Non-cloud-disk node group validation failures | **417** | `UnsatisfiedExpect` | `The request not satisfied expect {detail}` | Not repairable: disk / machine-type constraint class 417 |
| `NodeGroupName` uniqueness conflict | **417** | `IntegrityError` | `{raw db exception message}` | Auto-repairable: append a timestamp / short-hash suffix to the original `NodeGroupName` and retry |
| Dedicated image / machine type count mismatch (internal data anomaly) | 500 | — | `inner error: private image/machine type count mismatch` | Not repairable: internal data anomaly; backend investigation required |
| Network mode query failure | 500 | — | `Failed to query network mode` | Not repairable: dependent service failure |
| Key pair does not exist | 500 | — | `key pair {name} not found` | Not repairable: the key pair is user credential material |
| ACK / Serverless software instance does not exist | 500 | — | `Software/software instance does not exist` | Not repairable: underlying instance missing; backend investigation required |
| Other unknown exceptions (fallback) | 500 | — | `Internal error` | Not repairable: depends on underlying services, human intervention required |

On success: HTTP 200, Body: `{"NodeGroupId": "ng-xxxxxx", "RequestId": ...}`.

### 1.10 `UpdateNodeGroup`

Source: `src/modules/cluster_manager/api/app/node_group.py` → `update_node_group(args)` (L395)

| Trigger condition (code location) | HTTP | ErrorCode | ErrorMessage | Repairability & auto-completion suggestion |
|---|---|---|---|---|
| Pydantic validation failure | 400 | — | `参数校验失败: <pydantic 错误>` | Missing `NodeGroupId` is auto-repairable (back-fill via `ListNodeGroups`); other format / type errors not repairable |
| `NodeGroupId` does not exist (L406-L409) | 400 | — | `Group instance [{NodeGroupId}] does not exist` | Not repairable: resource identifier error |
| Target image invalid (L429-L430) | 400 | `InvalidParameter` | `The specified parameter {ImageId} is not valid.` | Not repairable: image selection is user intent; auto-substitution would change the environment |
| No permission to use the image (L432-L434) | 400 | `InvalidParameter` | `image {ImageId} does not have permission to use` | Not repairable: image permission is granted at account level |
| Key pair does not exist (L447-L449, ValueError) | 400 | — | `Key pair {name} does not exist` | Not repairable: the key pair is user credential material |
| Target image deprecated (L490-L493) | 400 | `DeprecatedImage` | `Image {ImageId} is deprecated.` | Auto-repairable: call `ListImages` to pick a non-deprecated image with the same platform / architecture as a substitute `ImageId` |
| `enable_node_group_file_system_mount` path: cluster does not exist | 400 | `InvalidParameter` | `The specified parameter ClusterId is not valid.` | Not repairable: resource identifier error |
| `enable_node_group_file_system_mount` path: neither DPU nor net_arch 7.0 | 400 | — | `只支持DPU机型且网络架构为7.0的集群发起补挂载操作` | Not repairable: cluster attributes not satisfied |
| `enable_node_group_file_system_mount` path: dedicated bare cluster not supported (`ARGS_TYPE_SUPPORT_ERROR`) | 400 | — | `The cluster type {type} does not allowed.` | Not repairable: cluster type not supported |
| `enable_node_group_file_system_mount` path: host state update failed | 400 | — | `The host update failed` | Not repairable: underlying update failure |
| Key pair check failure (L443-L446) | **417** | `UnsatisfiedExpect` | `The request not satisfied expect check key pair failed` | Not repairable: user must confirm key pair status |
| `FileSystemMountEnabled` cannot be turned off (L502-L508) | **417** | `UnsatisfiedExpect` | `The request not satisfied expect FileSystemMountEnabled are not supported to be closed` | Not repairable: once enabled, mounting cannot be disabled |
| FileSystemMount API not opened for the current user (L513-L518) | **417** | `UnsatisfiedExpect` | `The request not satisfied expect This api is not open to current user` | Not repairable: whitelist-controlled |
| `NewNodeGroupName` uniqueness conflict (L532-L535) | **417** | `IntegrityError` | `{raw db exception message}` | Auto-repairable: append a timestamp / short-hash suffix to the original `NewNodeGroupName` and retry |
| `enable_node_group_file_system_mount` path: cluster already has CPFS mounted | **417** | `UnsatisfiedExpect` | `The request not satisfied expect CPFS` | Not repairable: mount already exists |
| `enable_node_group_file_system_mount` path: image does not support Cloud Assistant | **417** | `UnsatisfiedExpect` | `The request not satisfied expect custom_msg` (Images does not support assistant cloud.) | Auto-repairable: call `ListImages` to pick a same-platform `ImageId` that supports Cloud Assistant |
| `enable_node_group_file_system_mount` path: node state not eligible | **417** | `UnsatisfiedExpect` | `节点{ids}状态不符合，要求是[使用中、等等]` | Not repairable: must wait for state-machine transitions |
| Other unknown exceptions (fallback, L555-L557) | 500 | — | `Internal error {exception}` | Not repairable: depends on underlying services, human intervention required |

On success (synchronous change, e.g. description update): HTTP 200, Body: `{"RequestId": ...}`.
On success (asynchronous change, e.g. KeyPairName/LoginPassword/FileSystemMount): HTTP 200, Body: `{"TaskId": "<task-id>", "RequestId": ...}`.

### 1.11 `ChangeNodeGroup`

Source: `src/modules/transaction_manager/api/app/node_change_group.py` → `change_nodegroup(args_obj)` (L530)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Repairability & auto-completion suggestion |
|---|---|---|---|---|
| Pydantic validation failure | 400 | — | `参数校验失败: <pydantic 错误>` | Not repairable: Pydantic failures are mostly parameter type / format errors |
| `Nodes` count > 500 (L530-L555) | 400 | — | `The number of nodes cannot exceed 500.` | Auto-repairable: split `Nodes` into batches of `≤500` and call sequentially |
| RAM Role inconsistent | 400 | — | `RAM Role not consistent` | Not repairable: source / target group RAM Role conflict; manual alignment required |
| `target_node_group_id` empty | 400 | — | `target_node_group_id is empty` | Not repairable: migration target is user intent |
| `node_ids` empty | 400 | — | `node_ids cannot be empty` | Not repairable: migration subjects are user intent |
| `node_ids` contains duplicates | 400 | — | `node_ids not unique` | Auto-repairable: deduplicate `node_ids` and retry |
| Node / hyper-node does not exist | 400 | — | `nodes may not exist: {ids}` | Not repairable: the user-supplied `node_ids` is wrong |
| Input contains tray nodes | 400 | — | `tray node id not valid: {ids}` | Auto-repairable: call `ListClusterNodes` to identify and remove tray nodes, then retry |
| Source nodes spread across multiple groups | 400 | — | `source nodes must be in one group` | Not repairable: the user must split into multiple calls |
| Source or target group does not exist | 400 | — | `group does not exist` | Not repairable: resource identifier error |
| Source / target groups not in the same cluster | 400 | — | `not in same cluster` | Not repairable: the API does not support cross-cluster migration |
| Source / target group machine types differ | 400 | — | `not in same machine type` | Not repairable: machine-type constraint |
| Source / target group disk types differ | 400 | — | `not in same disk type` | Not repairable: disk-type constraint |
| `file_mount_enabled` differs | 400 | — | `file_mount not same` | Not repairable: mount attribute constraint |
| `Serverless` / `ExclusiveDpuServerlessCluster` not supported | 400 | — | `cluster type {type} not supported` | Not repairable: cluster type not supported |
| `netarch 7.0` not supported (CustomException) | 400 | `InvalidParameter` | `The specified parameter netarch is not valid.` | Not repairable: network architecture constraint |
| Node not in Using state | 400 | — | `Node not in Using state` | Not repairable: the node must first be brought to Using state |
| Hyper-node not in Using state | 400 | — | `Hypernode not in Using state` | Not repairable: the hyper-node must first be brought to Using state |
| ACK node requires Cloud Assistant support | 400 | — | `ACK node requires cloud assistant support` | Not repairable: image capability constraint |
| ACK cluster shrink node count exceeds the limit | 400 | — | `ACK shrinking nodes exceeds limit` | Not repairable: wait for concurrent shrinks to finish; involves quota |
| Node / hyper-node state machine forbids the operation (`StateMachineException`) | **417** | `UnsatisfiedExpect` | `The status of the hypernode or node does not meet the condition of {action}` | Not repairable: must wait for state-machine transitions |
| Other unknown exceptions (fallback) | 500 | — | `Internal error` | Not repairable: depends on underlying services, human intervention required |

On success: HTTP 200, Body: `{"TaskId": "<task-id>", "RequestId": ...}`.

### 1.12 `ListMachineTypes`

Source: `src/modules/transaction_manager/api/app/private_cluster.py` → `private_list_machine_type(args_obj)` (L72)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Repairability & auto-completion suggestion |
|---|---|---|---|---|
| Pydantic validation failure | 400 | — | `参数校验失败: <pydantic 错误>` | Not repairable: Pydantic failures are mostly parameter type / format errors |
| Other unknown exceptions (fallback) | 500 | — | `Internal error` | Not repairable: depends on underlying services, human intervention required |

**No business-level error branches**; all normal business failures go through the generic 500 fallback. On success: HTTP 200, Body: `{"MachineTypes": [...], "RequestId": ...}`.

### 1.13 `ListImages`

Source: `src/modules/transaction_manager/api/app/private_cluster.py` → `private_list_system_image(args)` (L370)

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Repairability & auto-completion suggestion |
|---|---|---|---|---|
| Pydantic validation failure (`Platform`/`Architecture` split errors) | 400 | — | `参数校验失败: <pydantic 错误>` | Not repairable: `Platform`/`Architecture` must be supplied by the user per spec |
| Other unknown exceptions (fallback) | 500 | — | `Internal error` | Not repairable: depends on underlying services, human intervention required |

**No business-level error branches**. On success: HTTP 200, Body: `{"Images": [...], "RequestId": ...}`.

### 1.14 `DescribeTask`

Source: `src/modules/task_manager/api/service/describe_task.py` → `Describe_task(action_params, ...)` (L161)

Note: the `task_manager` entrypoint (`common/views.py`) differs from `transaction_manager`; `DescribeTask` returns the `{"ErrorCodeInfo": {...}}` structure produced by `make_error_code_body`, which the upper view unwraps per POP version.

| Trigger condition | HTTP | ErrorCode | ErrorMessage | Repairability & auto-completion suggestion |
|---|---|---|---|---|
| Other business exceptions (L278-L286) | **200** | `""` (empty string) | `str(e)` (raw exception message); note ErrorCodeInfo.HttpStatusCode=200 is the current code behavior | Not repairable: internal exception; check `ErrorCodeInfo.Success=False` and investigate manually |
| `TaskId` missing (`params_check` decorator) | **400** | `MissingParameter` | `TaskId is mandatory for this action.` | Auto-repairable: extract `TaskId` from a preceding `ExtendCluster/ShrinkCluster/ChangeNodeGroup/UpdateNodeGroup/DeleteNode` response |
| Parameter type error / JSON parse error / database error | **400** | `InvalidParameter` | `The specified parameter {paramName} is not valid.` | Not repairable: parameter block format error; fix the calling code |
| Task does not exist | **400** | `Resource.NotFound` | `The task {TaskId} is not found.` (from `RESOURCE_NOT_FOUND_MESSAGE` % ("task", task_id)) | Not repairable: `TaskId` wrong or the task has been GC'd |

On success: HTTP 200, Body: `{TaskType, TaskState, CreateTime, UpdateTime, Message, Steps, NodeIds, ClusterName, ClusterId, (Fault,) RequestId}`.

---

## 2. Cross-API Common Error Code Map

Aggregated by HTTP status code for frontend / script classification:

### 2.1 HTTP 400 — Request Parameter Errors

| ErrorCode | Typical source | Notes |
|---|---|---|
| `MissingParameter` | All CustomException triggers | Required parameter missing |
| `InvalidParameter` | All CustomException triggers | Invalid parameter value / no resource permission |
| `Resource.NotFound` | `CustomException(..., RESOURCE_NOT_FOUND)` branches or DescribeTask | Resource (cluster / node / node group / task) does not exist (business layer) |
| `DeprecatedImage` | ExtendCluster / UpdateNodeGroup | Image deprecated |
| `CustomImageError` | Extend/Create/UpdateNodeGroup | Custom image anomaly |
| `IpReserveFailed` | Extend internal branch | VPC IP reservation failure |
| `ExceedLimit` | Extend internal branch | Spec limit exceeded |
| `DpuMissingIpAllocationPolicy` | Extend internal branch | DPU missing IP allocation policy |
| `InvalidNodeId.NotFound` | DeleteNode | Node does not exist (fixed-string error code) |
| `ChargeTypeViolation` | DeleteNode | Non-pay-as-you-go nodes cannot be released |
| `IncorrectNodeStatus` | DeleteNode | Node state does not allow release |
| (empty) "参数校验失败" | Pydantic validation of all eflo APIs | Body contains only `ErrorMessage` |

### 2.2 HTTP 403 — Permission / Business Constraint Forbidden

| ErrorCode | Typical source |
|---|---|
| `PermissionError` | CreateNodeGroup (cluster type vs node pool mismatch) |
| `ObjectNotExists` | A few branches return "not exist" as a permission failure |
| `ChargeTypeViolation` | DeleteNode |
| `IncorrectNodeStatus` | DeleteNode |
| `InvalidAccount.PermissionDenied` | Gateway layer (api_router) |

### 2.3 HTTP 404 — Resource Not Found (framework layer)

| ErrorCode | Typical source |
|---|---|
| `RESOURCE_NOT_FOUND` (from `public_common/error_code.py`) | ListClusters / DescribeCluster / ListClusterNodes |
| `RESOURCE_NOT_FOUND` (from the http=404 ObjectDoesNotExist early-exit branch in `public_common/exception/custom_exceptions.py`) | DescribeNode, DeleteNode node-not-exist |
| `InvalidAccount.NotFound` | Gateway layer (api_router) |

> The business-layer `CustomException(..., RESOURCE_NOT_FOUND)` maps to **HTTP 400**, which must be distinguished from the framework-layer `ErrorInfo` 404.

### 2.4 HTTP 410 — Insufficient Quota

| ErrorCode | Typical source |
|---|---|
| `InsufficientQuota` | ExtendCluster new-purchase phase |

### 2.5 HTTP 417 — Business Expectation Not Satisfied

| ErrorCode | Typical source |
|---|---|
| `UnsatisfiedExpect` | Extend/Shrink/Change/Create/UpdateNodeGroup state machine, image / disk incompatibility, whitelist restrictions, etc. |
| `IntegrityError` | NodeGroupName uniqueness conflicts and task DB write conflicts in Create/UpdateNodeGroup |

**Special case**: `StateMachineException` (`inner_state_machine` in `public_common/common.py`) is also caught by each action and returned as `UnsatisfiedExpect`, with fixed wording:

```
The status of the hypernode or node does not meet the condition of {action}
```

### 2.6 HTTP 500 — Internal Errors

| ErrorCode | Typical source |
|---|---|
| `InternalError` | The `except Exception` fallback of all actions |
| `InternalDependencyError` (`DEPENDENCY_ERROR`) | Failure of underlying dependent services (ECS/VPC/Lingxiao) |

The `ErrorMessage` for HTTP 500 is usually `Internal error` or `Internal error {exception}`; some actions return `internal error` (lowercase, e.g. DescribeNode).

---

## 3. Idempotency and Retry Notes

Per the source implementation, the following APIs have explicit idempotency / reentrancy handling:

### 3.1 `DeleteNode` (naturally idempotent)

- Source: `delete_node.py` L98-L110
- Once the node has entered the `Releasing` state (`account_id` prefix changed to `system-`), a second call returns HTTP 200 directly, `{"HttpCode": 200, "success": true, "RequestId": ...}`.
- If the node does not exist (and is not `Releasing`), returns HTTP 404 `InvalidNodeId.NotFound`.

### 3.2 `ExtendCluster` / `ShrinkCluster` / `ChangeNodeGroup` (async tasks queryable)

- All three APIs return a `TaskId`; **the business side should use `ClientToken` or compare `TaskId`s for idempotency control** — the source has no built-in ClientToken dedup, and repeated calls create duplicate tasks.
- The node / hyper-node state machine (`inner_state_machine`) returns 417 on a second attempt, preventing concurrent operations on the same resource.

### 3.3 `CreateNodeGroup` / `UpdateNodeGroup`

- `NodeGroupName` is a unique key; duplicate creation returns HTTP 417 `IntegrityError`.
- Updating key pair / password / file-system mount, etc., creates async tasks; repeated calls likewise create duplicate tasks — **the caller must ensure idempotency**.

### 3.4 Read APIs (`List*` / `Describe*`)

- Read APIs are all side-effect-free and safe to retry.
- `DescribeTask` returns `TaskState` for polling; the internal exception branch at code L278-L286 returns HTTP 200 + `ErrorCodeInfo.Success=False` — **callers must check `ErrorCodeInfo` and must not rely on HTTP 200 alone**.

---

## 4. Version Notes

This document **targets only `Version=2022-12-15` (1215)**.

- Request header: `x-acs-eflo-pop-version: 2022-12-15`
- Required parameters uniformly use `ClusterId` (instead of `EnvName + ClusterName`).
- Response structure: business data is flattened directly under the root object, plus `NextToken` / `HttpCode` / `RequestId` (never wrapped in a `Data` field).
- Exception responses: uniformly generated by `entry_view`, structured as `{HttpCode, ErrorCode, ErrorMessage}`, returned with `status=http_status_code`.

Differences and compatibility logic of other versions (0706 / 0425) are out of scope; callers needing to adapt to other versions should consult the `eflo-controller-v1` source directly.
