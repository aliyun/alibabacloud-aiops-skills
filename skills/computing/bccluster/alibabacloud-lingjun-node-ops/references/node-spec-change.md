# Node Spec Change (F5) - change-node-types

Change a node's **NodeType** (DPU/storage mode) in-place. `NodeType` is **NOT** a machine type (`MachineType`, e.g. `efg2.C48eNH3ebn`) - it is one of **9 logical values** describing the storage/networking mode. The current value is read from `describe-node.NodeType` (e.g. `cpfs-enhanced`).

## NodeType enum (server-side `NodeTypeMap`, exactly 9)

| Category | Single-tenant | Multi-tenant (ASI/ACS) | zeroLeni variant |
|---|---|---|---|
| CPFS enhanced | `cpfs-enhanced` | `cpfs-enhanced-multi-tenant` | `zeroLeni-cpfs` |
| EBS enhanced | `ebs-enhanced` | `ebs-enhanced-multi-tenant` | `zeroLeni-ebs` |
| Balanced | `balanced` | `balanced-multi-tenant` | `zeroLeni-balanced` |

Any other value -> `The node_type <value> is not supported.` Do **NOT** validate against `list-machine-types` / `describe-node-type` - those are machine-spec catalogs and have nothing to do with this parameter.

## Transition matrix (what a node may change TO)

Allowed transitions depend on the cluster `minimum_vdpu_version` and tenant model (single vs ASI/ACS):

**Single-tenant:**
- vdpu >= 1.6.1: `cpfs-enhanced <-> ebs-enhanced`; `zeroLeni-cpfs <-> zeroLeni-ebs` (identity transitions also allowed)
- vdpu >= 1.6.2: adds `balanced` - `cpfs-enhanced` / `ebs-enhanced` / `balanced` mutually interchangeable; same for the three `zeroLeni-*`

**Multi-tenant (ASI/ACS):**
- vdpu >= 1.6.1: `cpfs-enhanced-multi-tenant <-> ebs-enhanced-multi-tenant`; `zeroLeni-cpfs <-> zeroLeni-ebs`
- vdpu >= 1.6.2: adds `balanced-multi-tenant` / `zeroLeni-balanced`, each trio mutually interchangeable

Cross rules: **single-tenant <-> multi-tenant never interchangeable; zeroLeni <-> non-zeroLeni never interchangeable.**

## Other server-side conditions

- Node vdpu must satisfy the cluster `minimum_vdpu_version`, and spec change requires vdpu > 1.6.0; below 1.6.1 the node must be in the `ChangeNodeTypeWhiteList` whitelist.
- Target NodeType must have a spec entry in the server-side `DpuResourceSpec` table and an ECS-side disk quota record.
- Nodes must be `OperatingState=Using`, all in the **same node group**, **<= 10** per call, no duplicates.
- If a node's current disk count / ENI / high-density ENI count exceeds the target type's quota, that node returns `RESOURCE_INSUFFICIENT`.

## CLI

```bash
safe_aliyun aliyun eflo-controller change-node-types \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --node-ids <NodeId1> [<NodeId2> ...] \
  --node-type <NodeType from the 9-value enum>
```

| Flag | Required | Notes |
|---|---|---|
| `--region` / `--endpoint` | [OK] | per [endpoint-routing.md](endpoint-routing.md) |
| `--node-ids` | [OK] | space-separated; **server-enforced <=10**, same node group |
| `--node-type` | [OK] | one of the 9 enum values. **`forbidden_inference`** - HITL pick from the enum table above based on `describe-node.NodeType` |

## Pre-Check (mandatory)

For every selected `NodeId`:

1. `describe-node` returns `OperatingState`, current `NodeType`, and `NodeGroupId`.
2. Reject if `OperatingState != Using` (server requires exactly `Using`).
3. Reject if nodes span multiple `NodeGroupId`.
4. Compare current `NodeType` against requested `--node-type`:
   - identical -> no-op, **skip** the row (identity transitions are technically allowed but pointless).
   - different -> check it against the transition matrix (tenant model + vdpu version); if not allowed, refuse with explanation instead of submitting.
5. Validate `--node-type`  in  the 9-value enum - never against `list-machine-types`.

## Workflow

1. List nodes -> HITL pick (<=10 per batch, same node group).
2. HITL pick `--node-type` from the enum (`forbidden_inference`), guided by each node's current `NodeType`.
3. Show **Spec Change Warning Box** (task success != change success; `RESOURCE_INSUFFICIENT` may reject individual nodes) + confirmation table + the closing prompt (see `render.confirm_prompt` in `lib/core/i18n.sh`) in one message.
4. User replies the confirmation word (see `render.confirm_word` in `lib/core/i18n.sh`) -> submit via `safe_mutate_oneshot`.
5. Submit -> record `TaskId`.
6. On-demand `describe-task` status checks reported in the reply body (terminal watch mode via `lj_poll.sh` only on explicit user request).
7. **For each node** call `describe-node` and compare **`NodeType`** (not `MachineType`) against the requested target.

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `The node_type xxx is not supported.` | value outside the 9-value enum (e.g. a MachineType was passed) | pick from the NodeType enum |
| `The specified parameter xxx is not valid.` | gateway/param rejection of an invalid `--node-type` | same as above |
| `The node_ids are not in the same group.` | mixed node groups in one call | split per node group |
| `RESOURCE_INSUFFICIENT` (per node) | disk / ENI / dense-ENI count exceeds target quota | report per-node, HITL decision |
| vdpu / whitelist rejection (`These nodes are not support change node type`) | cluster vdpu <= 1.6.0 or node not whitelisted | explain, no retry |

## Verification rule (hard)

The Agent's completion report **must** include a per-node table:

| NodeId | TaskState | Pre `NodeType` | Post `NodeType` | Result |
|---|---|---|---|---|
| e01-cn-aaa | execution_success | cpfs-enhanced | ebs-enhanced | [OK] |
| e01-cn-bbb | execution_success | cpfs-enhanced | cpfs-enhanced | [WARN] task ok, NodeType unchanged |

A row whose `Post NodeType` does not match the request **must not** be reported as a successful node spec change.
