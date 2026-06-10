# Acceptance Criteria — PAI Quota

## Product / action

- ✅ `aliyun paistudio list-quotas`, `aliyun paistudio create-quota`, `aliyun paistudio scale-quota`.
- ✅ `aliyun aiworkspace create-workspace-resource --option Attach` for binding.
- ❌ `aliyun pai list-quotas` (wrong product prefix — plugin is `paistudio`).
- ❌ `aliyun paistudio ScaleQuota` (PascalCase — CLI uses kebab-case).
- ❌ `aliyun paistudio bind-quota` (no such command — use `aliyun aiworkspace create-workspace-resource`).

## Required parameters

- ✅ Always pass `--region "${REGION_ID}"` (no implicit region inference).
- ✅ `create-quota` (root) requires `--quota-name`, `--resource-type`, `--resource-group-ids`, `--min`.
- ✅ `create-quota` (child) requires `--quota-name`, `--parent-quota-id`, `--min`.
- ✅ `update-quota`, `scale-quota`, `delete-quota` require `--quota-id`.
- ✅ `aiworkspace create-workspace-resource` requires `--workspace-id`, `--option Attach`, `--resources`.
- ❌ Calling `create-quota` with both `--parent-quota-id` AND `--resource-group-ids` for a child quota (child takes RG from its parent).

## Enums

- ✅ `--resource-type ECS`, `--resource-type Lingjun`, `--resource-type ACS`.
- ✅ `--allocate-strategy ByNodeSpecs` or `ByMachineGroupIds`.
- ✅ `--queue-strategy` is one of: `PaiStrategyIntelligent` (auto/intelligent), `PaiStrategyStrictFIFO` (FIFO), `PaiStrategyBalance` (fair/balanced), `PaiStrategyRoundRobin` (round-robin).
- ❌ `--queue-strategy PaiStrategyFifo` / `PaiStrategyFair` / `PaiStrategyRR` (legacy aliases — not accepted).
- ❌ `--resource-type lingjun` (case-sensitive; must be `Lingjun`).
- ❌ `--resource-type` derived from user input alone — MUST be read from `get-resource-group` (root) or `get-quota` on parent (child).
- ❌ `--allocate-strategy by-node-specs` (PascalCase, not kebab-case).

## `--min` JSON

- ✅ `--min '{"NodeSpecs":[{"NodeSpec":"ecs.gn7i-c8g1.2xlarge","Count":2}]}'` — single-quoted, valid JSON, PascalCase keys.
- ❌ `--min '{"nodeSpecs":[{"nodeSpec":"...","count":2}]}'` (camelCase keys rejected).
- ❌ `--min "NodeSpecs=[{NodeSpec=ecs...,Count=2}]"` (key=value DSL is not supported — must be JSON).

## `--min` NodeSpec availability (Step C validation)

- ✅ Agent calls `list-node-types` (scoped by `--resource-group-ids` for root, `--quota-id` for child) before `create-quota`.
- ✅ Every `NodeSpec` in `--min` JSON exists in the `list-node-types` response.
- ✅ Every `Count` in `--min` JSON ≤ the bindable count returned for that NodeSpec.
- ✅ Agent presents the availability table (NodeType / Available / Requested) to the user before `CONFIRM-CREATE`.
- ❌ Passing a `NodeSpec` that does not exist in `list-node-types` results — agent MUST refuse.
- ❌ Requesting a `Count` exceeding the available bindable nodes — agent MUST refuse.
- ❌ Skipping `list-node-types` validation and directly invoking `create-quota`.

## `--resource-group-ids` list flag

- ✅ `--resource-group-ids rg-aaa rg-bbb` (space-separated repeated values).
- ❌ `--resource-group-ids "rg-aaa,rg-bbb"` (CSV string is NOT accepted by `create-quota` / `scale-quota`; only `list-nodes` accepts CSV).

## VPC mutability (`--quota-config.UserVpc`)

- ✅ Lingjun quota: `update-quota --quota-config '{"UserVpc":{"SwitchId":"vsw-new"}}'` — adding an extra vSwitch only.
- ❌ Lingjun quota: changing `UserVpc.VpcId`, `SecurityGroupId`, `DefaultRoute`, `ExtendedCIDRs`, `RoleArn`, or `DefaultForwardInfo` via `update-quota` (all immutable post-create).
- ❌ ECS quota: any `update-quota --quota-config '{"UserVpc":...}'` modification — VPC is frozen at create time. Delete-and-recreate (or fix at the source ResourceGroup layer).

## Destructive operations (update / scale / delete / detach)

- ✅ Print resolved plan + `--cli-dry-run` output + active workloads from `list-quota-workloads`, then ask for `CONFIRM <QUOTA_ID>` before running.
- ✅ Scale-down below current usage requires `CONFIRM-FORCE <QUOTA_ID>` (with the `-FORCE` suffix).
- ❌ Running `delete-quota` directly after the user says "yes" / "go" / "sure".
- ❌ Batching multiple `delete-quota` calls under one confirmation token — each child and the root require their own token.
- ❌ Skipping the workload check before `scale-quota` (down) or `delete-quota`.

## Workspace binding

- ✅ `aiworkspace create-workspace-resource --option Attach --resources '[{"ProductType":"PAI","ResourceType":"ECS","WorkspaceId":"ws-x","Quotas":[{"Id":"quota-x"}]}]'`
- ✅ For Lingjun quotas use `"ResourceType":"Lingjun"` inside `--resources`.
- ❌ Omitting `--option Attach` (defaults to `CreateAndAttach` which expects a new resource payload, not an existing quota id).
- ❌ Using camelCase inside `--resources` JSON (must be PascalCase: `ProductType`, `ResourceType`, `WorkspaceId`, `Quotas`).

## Tool selection

- ✅ All Quota operations through `aliyun paistudio <action>`; all workspace-binding operations through `aliyun aiworkspace <action>`.
- ❌ Falling back to MCP `pai_list_quotas` / `aiw_list_workspaces`, raw curl, Python SDK, Java SDK, Terraform, or web-console clicks.

## Cross-skill prerequisite (root `create-quota` / root `scale-quota`)

- ✅ Before `create-quota` (root) and before `scale-quota` (when `--resource-group-ids` changes), call the **`pai-resource-group-management`** skill (or `aliyun paistudio list-resource-groups` + `get-resource-group`) to enumerate and inspect every candidate RG.
- ✅ Print a per-RG validation table showing `ClusterId`, `GpuType`, and (for ECS) `UserVpc.{VpcId,SwitchId,SecurityGroupId}` before issuing the create/scale call.
- ❌ Issuing `create-quota --resource-group-ids rg-aaa rg-bbb` without first calling `get-resource-group` on each id.
- ❌ Trusting user-supplied RG IDs without verification — a wrong / non-existent RG ID surfaces as an opaque CLI error after the homogeneity step is skipped.

## RG homogeneity (root `create-quota` / root `scale-quota`)

All RGs in the FINAL `--resource-group-ids` set MUST share the following invariants. STOP and surface the offending field if any differ.

**Step A — ResourceType must match (cross-cutting):**

- ✅ All RGs in the set have the SAME `ResourceType`; the agent derives `--resource-type` from that shared value (never from user input).
- ✅ For child quota creation, `--resource-type` is derived from the parent quota's `ResourceType` via `get-quota`.
- ✅ For `scale-quota`, the post-scale RG set's `ResourceType` matches the existing root quota's `ResourceType`.
- ❌ Asking the user what `--resource-type` to pass — the agent reads it from the source data.
- ❌ Accepting a user-supplied `--resource-type` that conflicts with the source RG / parent quota `ResourceType`.
- ❌ Mixing `ECS` + `Lingjun`, `ECS` + `ACS`, or `Lingjun` + `ACS` RGs in the same `--resource-group-ids` set.
- ❌ Silently dropping the non-matching RG to make `ResourceType` line up.

**Step B — Per-ResourceType invariants (after Step A passes):**

| Scenario | Required identical fields |
| --- | --- |
| **Lingjun** | `ClusterId`, `GpuType` |
| **ECS** | `ClusterId`, `GpuType`, `UserVpc.VpcId`, `UserVpc.SwitchId`, `UserVpc.SecurityGroupId` |
| **ACS** | `ClusterId`, `GpuType` |

- ✅ Reject the request when `rg-aaa.ClusterId != rg-bbb.ClusterId` (cross-cluster Quota is forbidden).
- ✅ Reject the request when `rg-aaa.GpuType != rg-bbb.GpuType` (mixed-GPU Quota is forbidden).
- ✅ (ECS) Reject when `rg-aaa.UserVpc.VpcId != rg-bbb.UserVpc.VpcId` or vSwitch / SecurityGroup differ.
- ❌ Silently dropping a non-conforming RG from `--resource-group-ids` to make the call succeed.
- ❌ Suggesting the user mutate ECS-RG VPC in-place — ECS RG VPC change requires the unbind-then-rebind two-step in the `pai-resource-group-management` skill.

## Candidate resolution & confirmation (`create-quota`)

Applies to BOTH root creates (resolving `--resource-group-ids`) and child creates (resolving `--parent-quota-id`).

- ✅ When the user supplies RG **ID(s)**, verify them via `aliyun paistudio list-resource-groups --resource-group-ids "rg-aaa,rg-bbb"` (CSV filter, exact match).
- ✅ When the user supplies an **exact** RG name, use `--name "${RG_NAME}"` filter.
- ✅ When the user supplies a **substring / partial / fuzzy** RG name (filter not applicable), paginate `list-resource-groups --page-number 1..N --page-size 100` end-to-end and match client-side.
- ✅ When the user supplies parent quota **ID**, verify via `list-quotas --quota-ids "${PARENT_QUOTA_ID}"`.
- ✅ When the user supplies an **exact** parent quota name, use `--quota-name "${NAME}" --layout-mode Tree`.
- ✅ When the user supplies a **substring / partial / fuzzy** parent quota name, paginate `list-quotas` end-to-end (`--page-size 100`) and match client-side.
- ✅ Print the resolved candidate set as a table (`ResourceGroupId / Name / ResourceType / ClusterId / GpuType / UserVpc` for RGs; `QuotaId / QuotaName / ResourceType / ParentQuotaId` for parent quotas), then obtain the **`CONFIRM-CREATE <QUOTA_NAME>`** token before invoking `create-quota`.
- ✅ When `MatchCount > 1` for a name lookup, list every match and refuse to guess — ask the user to disambiguate by ID.
- ❌ Calling `create-quota` directly with user-supplied IDs without resolving them via `list-resource-groups` / `list-quotas` first.
- ❌ Stopping pagination after the first page when the lookup is by substring / partial name.
- ❌ Auto-picking the first match when `MatchCount > 1` — ambiguity MUST go back to the user.
- ❌ Accepting plain `yes` / `ok` / `go` / `sure` as the candidate-set confirmation — only the literal `CONFIRM-CREATE <QUOTA_NAME>` token is valid.