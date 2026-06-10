# `list-nodes` — Filters, Display & Pagination Parameters

This file enumerates the optional parameters accepted by `aliyun paistudio list-nodes`. SKILL.md keeps only the primary scope (`--resource-group-ids` vs `--quota-id`) and the high-level workflow; consult this file when the user requests a specific filter, sort order, or output mode.

## 1. Filters (all optional)

| Parameter | Format | Notes |
| --- | --- | --- |
| `NodeTypes` | CSV, e.g. `"ecs.gn7i-c8g1.2xlarge,ecs.gn6v-c8g1.16xlarge"` | ECS spec / node type filter. Validated against a regex pattern by the backend. |
| `AcceleratorType` | String | e.g. `GPU`, `CPU`. |
| `GPUType` | String | e.g. `A100`, `V100`. |
| `NodeStatuses` | CSV: `Running`, `Initializing`, `Stopped`, `Failed`, etc. | PascalCase only. |
| `OrderStatuses` | CSV | Order lifecycle filter. |
| `MachineGroupIds` | CSV | Narrow to specific MachineGroups. |
| `NodeNames` | CSV | Filter by exact node names. |
| `ReasonCodes` | CSV: `CordonByUser`, `Expired`, `Recovering` | Only these three values are accepted by the backend. |
| `FilterByQuotaId` | String | Secondary filter (only when scoping by RG). |
| `FilterByResourceGroupIds` | CSV | Secondary filter (only when scoping by Quota). |
| `ResourceGroupName` | String | Filter by RG name. |
| `HyperZone` | String | Lingjun zone filter. |
| `AvailabilityZone` | String (JSON key: `AvailableZone`) | AZ filter. |
| `PaymentType` | String | e.g. `PostPaid`, `PrePaid`. |
| `DiskPL` | String | Disk performance level. |
| `HyperNodeTypes` | String | L20A hyper-node type filter. |
| `HyperNode` | String | Specific hyper-node. |
| `CliqueID` | String | Clique-level filter. |
| `WorkspaceId` | Numeric string | Filter nodes within a workspace. **Must contain only digits** (validated by backend). |
| `WorkloadNum` | Integer pointer | Verbose-only: filter by workload count. |
| `PodNum` | Integer pointer | Verbose-only: filter by pod count. |

## 2. Display & pagination

| Parameter | Default | Notes |
| --- | --- | --- |
| `Verbose` | `false` | `true` to include usage/allocation info. **Agent MUST ask user before enabling** (see SKILL.md Step 7.1). |
| `LayoutMode` | `List` | `Tree` or `List`. |
| `SortBy` | `NodeName` | One of: `QuotaId`, `ResourceGroupId`, `ResourceGroupName`, `NodeType`, `NodeName`, `CPU`, `Memory`, `GPU`, `GmtCreatedTime`, `GmtExpiredTime`, `RequestCPU`, `RequestMemory`, `RequestGPU`, `WorkloadNum`, `PodNum`, `MachineGroupId`, `HyperZone`, `AvailabilityZone`, `HyperNode`, `CliqueID`, `HealthRate`, `DiskPL`, `DiskCapacity`, etc. |
| `PageNumber` | `1` | 1-based. |
| `PageSize` | `50` | Max `100`. For **single-node lookup** (`--node-names "<one-name>"`), **MUST be collapsed to `1`** — see §2.1 below. |
| `Order` | `desc` | `asc` or `desc`. |

### 2.1 Single-node lookup — pagination collapse rule

When the user is asking about exactly **one** node by name (`--node-names "<one-name>"`), the call MUST be issued as:

```bash
aliyun paistudio list-nodes --region "${REGION_ID}" \
  --resource-group-ids "${RG_ID}" \
  --node-names "${NODE_NAME}" \
  --page-number 1 --page-size 1
```

- `--region`, `--resource-group-ids`, and `--page-size 1` are **all mandatory** — none may be omitted.
- `--page-size 50` / `--page-size 100` for single-node lookup is **incorrect**: it over-fetches, masks the exactly-one-match assertion, and produces noisier output. Reserve large page sizes for enumeration (multi-node listing) only.
- If the user does not know the owning RG, the agent MUST resolve it inline before calling `list-nodes` — do NOT drop `--resource-group-ids` to avoid the lookup. Resolution path: call `aliyun paistudio list-resource-groups --region "${REGION_ID}"` (with the per-command `--user-agent` flag from SKILL.md §0 appended), match the user-supplied RG name (case-sensitive, exact match) against `ResourceGroups[].Name`, and use the corresponding `ResourceGroupId`. Zero hits → ask the user to recheck the name; multiple hits → ask the user to disambiguate by ID. Do NOT fabricate an ID, do NOT route through SDK / curl / MCP / kubectl / SSH.

## 3. CSV vs space-separated reminder

Unlike `create-quota --resource-group-ids` (space-separated), **every list-like filter above on `list-nodes` is CSV** — wrap multi-values in a single quoted string with comma separators:

```bash
# ✅ correct
aliyun paistudio list-nodes --resource-group-ids "rg-a,rg-b" --node-names "node-1,node-2"

# ❌ wrong — space-separated is rejected by list-nodes
aliyun paistudio list-nodes --resource-group-ids rg-a rg-b
```
