# Validation Rules — PAI Quota

## 1. Mandatory Candidate Resolution & Confirmation (`create-quota`)

**[MUST] Before issuing `create-quota`, every user-supplied identifier (ResourceGroup ID/name, Parent Quota ID/name) MUST be resolved against the live API and the resolved candidate set MUST be re-confirmed by the user.** This applies to BOTH root Quota creation (resolving `--resource-group-ids`) and child Quota creation (resolving `--parent-quota-id`). The agent MUST NOT pass unverified IDs to `create-quota`.

### Resolution rules

| Input given by user | Preferred lookup (filter) | Fallback when no filter exists / partial match |
| --- | --- | --- |
| ResourceGroup **ID(s)** (`rg-xxx`) | `aliyun paistudio list-resource-groups --resource-group-ids "rg-aaa,rg-bbb"` (CSV filter, exact match). | If the filter rejects the value or returns 0 rows, paginate the full RG list and match locally. |
| ResourceGroup **name** (exact) | `aliyun paistudio list-resource-groups --name "${RG_NAME}"` (the API treats `--name` as an exact-match filter). | If the user only knows a substring / pattern / partial name, the filter is **NOT applicable** — paginate `list-resource-groups` end-to-end (`--page-number 1..N --page-size 100`) and match the name client-side. |
| Parent Quota **ID** | `aliyun paistudio list-quotas --quota-ids "${PARENT_QUOTA_ID}"`. | Paginate full list. |
| Parent Quota **name** (exact) | `aliyun paistudio list-quotas --quota-name "${PARENT_QUOTA_NAME}" --layout-mode Tree`. | If the user gives a substring or doesn't know the exact name, paginate `list-quotas` end-to-end and match client-side. |

### Pagination rules (when no usable filter exists)

```bash
# Full enumeration template — repeat with --page-number 1..N until TotalCount is fully consumed.
aliyun paistudio list-resource-groups \
  --region "${REGION_ID}" --page-number 1 --page-size 100 \
  --output cols=ResourceGroupId,Name,ResourceType,ClusterId,GpuType,UserVpc

aliyun paistudio list-quotas \
  --region "${REGION_ID}" --page-number 1 --page-size 100 --layout-mode Tree --verbose true \
  --output cols=QuotaId,QuotaName,ResourceType,ParentQuotaId
```

- The agent MUST keep paginating until **every** page has been read; never stop after the first page when the user-supplied value is ambiguous.
- The agent MUST NOT silently pick "the first match" — even when exactly one candidate is found, the candidate must be presented to the user for confirmation.

### Mandatory secondary confirmation (after candidates are resolved)

1. **Print the resolved candidate set** as a table: for RGs include `ResourceGroupId / Name / ResourceType / ClusterId / GpuType / UserVpc`; for Quotas include `QuotaId / QuotaName / ResourceType / ParentQuotaId`. If pagination was used, also print `TotalScanned / MatchCount`.
2. **Highlight ambiguity** explicitly when `MatchCount > 1` (multiple RGs or Quotas share the same name) — list every match and refuse to guess.
3. **Ask the user verbatim**: `The resolved <ResourceGroup|Parent Quota> candidate set is shown above. Please confirm to proceed with create-quota. Type "CONFIRM-CREATE <QUOTA_NAME>" to continue; any other input cancels.`
4. **Only proceed** if the user replies with the exact token `CONFIRM-CREATE <QUOTA_NAME>` (the new Quota's intended name). Plain `yes` / `ok` / `go` / `sure` MUST be treated as cancellation.
5. **Never auto-resolve cross-product**: do NOT silently expand a single user-supplied substring into multiple RGs / Quotas — re-prompt the user to disambiguate first.
6. **Idempotency window**: the `CONFIRM-CREATE` token is valid for the immediately following `create-quota` call only.
7. **Composes with homogeneity validation** (§2 below): for root creates, the homogeneity table MUST be printed alongside the candidate set so the user confirms a *valid* set in one round.

> Read-only listings (the lookup queries themselves) do NOT require confirmation. The `CONFIRM-CREATE <QUOTA_NAME>` gate is **separate** from the destructive `CONFIRM <QUOTA_ID>` / `CONFIRM-FORCE <QUOTA_ID>` gates and is required even though `create-quota` is itself non-destructive — because mis-resolved IDs would silently bind the new Quota to the wrong source.

---

## 2. Homogeneity Validation (root `create-quota` / root `scale-quota`)

**[MUST] All RGs in `--resource-group-ids` MUST be compatible.** Reject the request and STOP if any of the following invariants fail across the set of selected RGs.

### Step A — ResourceType must match (cross-cutting invariant)

Every RG in the set MUST share the SAME `ResourceType`. The agent MUST **read** this value from the `get-resource-group` response and **automatically derive** the `--resource-type` flag for `create-quota` from it. The agent MUST NOT ask the user for `--resource-type`, and MUST NOT accept a user-supplied `--resource-type` that conflicts with the actual RG data. Mixing types is forbidden.

| Allowed combinations | Forbidden combinations |
| --- | --- |
| All `Lingjun` + `--resource-type Lingjun` | One `ECS` RG + one `Lingjun` RG |
| All `ECS` + `--resource-type ECS` | One `ECS` RG + one `ACS` RG |
| All `ACS` + `--resource-type ACS` | One `Lingjun` RG + one `ACS` RG |

If any RG in the requested set has a different `ResourceType` from the others, STOP, surface every offending RG with its `ResourceType`, and refuse to proceed. Do NOT silently drop a non-matching RG, and do NOT "upgrade" / "downgrade" the `ResourceType` to coerce the call.

### Step B — Per-ResourceType invariants (apply only after Step A passes)

| Scenario | Invariant (must be identical across all RGs) |
| --- | --- |
| **Lingjun** (`--resource-type Lingjun`) | `ClusterId` AND `GpuType` |
| **ECS** (`--resource-type ECS`) | `ClusterId` AND `GpuType` AND `UserVpc.VpcId` AND `UserVpc.SwitchId` AND `UserVpc.SecurityGroupId` |
| **ACS** (`--resource-type ACS`) | `ClusterId` AND `GpuType` |

If any invariant differs, STOP, print the offending field + per-RG values, and instruct the user to either (a) pick a homogeneous subset, or (b) align the RGs first via the `pai-resource-group-management` skill. Do NOT silently drop RGs from the request.

Print the full validation table (RG -> ResourceType / ClusterId / GpuType / UserVpc) before issuing the create call.

### Scale-quota additional rule

When `scale-quota` adds or replaces source RGs, the agent MUST re-run the same homogeneity validation against the FINAL post-scale RG set. Additionally, the shared `ResourceType` MUST match the existing root quota's `ResourceType` (post-create, the root quota's `ResourceType` is immutable). Cross-type / cross-cluster / cross-VPC scale is forbidden.

---

## 3. NodeSpec Availability Validation (Step C)

**[MUST] After the homogeneity check passes, and before issuing `create-quota`, the agent MUST call `list-node-types` to enumerate available node specs and their bindable counts.**

```bash
# For root quota creation (scope by ResourceGroupIds)
aliyun paistudio list-node-types \
  --region "${REGION_ID}" \
  --resource-group-ids "${RESOURCE_GROUP_IDS_CSV}"

# For child quota creation (scope by parent QuotaId)
aliyun paistudio list-node-types \
  --region "${REGION_ID}" \
  --quota-id "${PARENT_QUOTA_ID}"
```

### Validation rules

1. **Existence check** — every `NodeSpec` in the user's `--min` JSON MUST appear in the `list-node-types` response. If a user-supplied NodeSpec is not found, STOP and refuse:
   ```
   NodeSpec "<USER_SPEC>" does not exist in the available node types for the selected ResourceGroup(s).
   Available specs: <list from API response>
   ```
2. **Capacity check** — the `Count` requested for each NodeSpec MUST NOT exceed the bindable count returned by `list-node-types`. If it does, STOP and refuse:
   ```
   Requested Count (<N>) for NodeSpec "<SPEC>" exceeds the available bindable count (<M>).
   Please reduce the count to at most <M>.
   ```
3. **Present the availability table** to the user before asking for `CONFIRM-CREATE`:
   ```
   | NodeType | Available (bindable) | Requested |
   | --- | --- | --- |
   | ecs.gn7i-c8g1.2xlarge | 10 | 2 |
   | ecs.gn6v-c8g1.16xlarge | 4 | 0 (not requested) |
   ```

Only proceed to the `CONFIRM-CREATE` gate if all NodeSpec values pass both checks.

---

## 4. VPC Update Constraints (`--quota-config.UserVpc`)

| Quota type | Mutable via `update-quota` | Immutable post-create |
| --- | --- | --- |
| **Lingjun** | `UserVpc.SwitchId` (extend only — add extra vSwitches) | `VpcId`, `SecurityGroupId`, `DefaultRoute`, `ExtendedCIDRs`, `RoleArn`, `DefaultForwardInfo` |
| **ECS** | None — VPC settings are frozen at create time | All `UserVpc` fields. To change, delete the quota and recreate it (or change at the source ResourceGroup layer via `pai-resource-group-management`). |

---

## 5. Confirmation Gate Details

### Two-Step Confirmation Gate (Update / Scale / Delete / Detach)

1. **Print the resolved plan** — target `QuotaId`, action, current value, target value, full diff of every field being changed, and blast radius (active workloads, child Quotas affected, workspaces bound).
2. **Run `--cli-dry-run`** for the exact command first and print the resolved request payload. Use `list-quota-workloads` and `list-quota-active-user-usages` to surface in-flight workloads before any scale-down or delete.
3. **Ask the user verbatim**: `Please confirm the <update|scale|delete|detach> operation above. Type "CONFIRM <QUOTA_ID>" to proceed; any other input cancels.`
4. **Only proceed** if the user replies with the exact token `CONFIRM <QUOTA_ID>`. Plain "yes" / "ok" / "go" / "sure" MUST be treated as cancellation.
5. **Never batch** — each `QuotaId` is confirmed individually. For tree-wide deletion, each child requires its own `CONFIRM <CHILD_QUOTA_ID>`, and the root requires a final `CONFIRM <ROOT_QUOTA_ID>`.
6. **Scale-down rule**: when `scale-quota` reduces `Min` below current usage, require `CONFIRM-FORCE <QUOTA_ID>` (note the `-FORCE` suffix). A regular `CONFIRM` is rejected.
7. **Idempotency window**: a confirmation token is valid for the immediately following CLI call only.

> Read-only steps (`list-quotas`, `get-quota`, `list-quota-workloads`, `list-quota-active-user-usages`, `aiworkspace list-resources`, `list-workspaces`) do NOT require confirmation. `create-quota` and `aiworkspace create-workspace-resource --option Attach` do NOT require this gate, but the agent MUST summarize resolved parameters before submission.
