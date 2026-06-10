# Verification Method — PAI Quota

## V1 — Verify list-quotas

```bash
aliyun paistudio list-quotas --region "${REGION_ID}" --page-number 1 --page-size 5
```

**Pass when:** HTTP 200 with `Quotas[]` and `TotalCount >= 0`. Each item has `QuotaId`, `QuotaName`, `ResourceType`, `Status`.

## V2 — Verify get-quota

```bash
aliyun paistudio get-quota --region "${REGION_ID}" --quota-id "${QUOTA_ID}" --verbose true
```

**Pass when:** Response echoes the requested `QuotaId` and includes `QuotaName`, `ResourceType`, `Min`, `Status`, `GmtCreatedTime`. For root quotas: `ResourceGroupIds[]` populated. For child quotas: `ParentQuotaId` populated.

## V3 — Verify create-quota (root)

After `create-quota` (root, no `--parent-quota-id`), re-run V1 filtered by `--quota-name` and assert the new `QuotaId` appears with `Status` ∈ `{Enabled, Initializing}` and the supplied `ResourceType`, `Min`, `ResourceGroupIds` match.

### V3-pre — Candidate resolution check (mandatory pre-create)

Before issuing `create-quota` for either a root or a child Quota, the agent MUST resolve every user-supplied identifier and obtain the user's `CONFIRM-CREATE <QUOTA_NAME>` token. Run the lookup that matches the user input:

```bash
# (a) RG lookup by ID set — use the CSV filter
aliyun paistudio list-resource-groups --region "${REGION_ID}" \
  --resource-group-ids "rg-aaa,rg-bbb" \
  --output cols=ResourceGroupId,Name,ResourceType,ClusterId,GpuType,UserVpc

# (b) RG lookup by exact name
aliyun paistudio list-resource-groups --region "${REGION_ID}" --name "${RG_NAME}"

# (c) RG lookup by partial / fuzzy name — paginate end-to-end
for PAGE in $(seq 1 "${LAST_PAGE}"); do
  aliyun paistudio list-resource-groups --region "${REGION_ID}" \
    --page-number "${PAGE}" --page-size 100 \
    --output cols=ResourceGroupId,Name,ResourceType,ClusterId,GpuType,UserVpc
done

# (d) Parent quota lookup by ID
aliyun paistudio list-quotas --region "${REGION_ID}" --quota-ids "${PARENT_QUOTA_ID}"

# (e) Parent quota lookup by exact name
aliyun paistudio list-quotas --region "${REGION_ID}" --quota-name "${PARENT_QUOTA_NAME}" --layout-mode Tree

# (f) Parent quota lookup by partial / fuzzy name — paginate end-to-end
for PAGE in $(seq 1 "${LAST_PAGE}"); do
  aliyun paistudio list-quotas --region "${REGION_ID}" --layout-mode Tree --verbose true \
    --page-number "${PAGE}" --page-size 100 \
    --output cols=QuotaId,QuotaName,ResourceType,ParentQuotaId
done
```

**Pass when:** every input maps to exactly one resolved candidate per the user's intent, the candidate table is printed, and the user has replied with `CONFIRM-CREATE <QUOTA_NAME>`. Otherwise STOP — do NOT proceed to V3 / V4 / V3a.

### V3a — Pre-create homogeneity check (cross-skill prerequisite)

Before issuing `create-quota` (root) or `scale-quota` with a new `--resource-group-ids` set, run via the **`pai-resource-group-management`** skill:

```bash
for RG in rg-aaa rg-bbb; do
  aliyun paistudio get-resource-group --region "${REGION_ID}" --resource-group-id "${RG}" \
    --output cols=ResourceGroupId,ResourceType,ClusterId,GpuType,UserVpc
done
```

**Pass conditions** (evaluated in order):

1. **Step A — ResourceType homogeneity.** Every RG in the set returns the SAME `ResourceType`, AND that value equals the `--resource-type` flag passed (for `create-quota`) or the existing root quota's `ResourceType` (for `scale-quota`). If any RG's `ResourceType` differs (e.g. one returns `ECS`, another returns `Lingjun`), STOP — cross-type quotas are forbidden. Surface every offending RG with its `ResourceType` and refuse to proceed to Step B.
2. **Step B — Per-ResourceType invariants.** Every RG returns identical `ClusterId` AND `GpuType`. For `ResourceType=ECS`, additionally `UserVpc.VpcId`, `UserVpc.SwitchId`, and `UserVpc.SecurityGroupId` are identical across all RGs.

If either step fails, STOP and surface the offending field — do NOT proceed to V3 / V6.

## V4 — Verify create-quota (child)

After `create-quota` (child, with `--parent-quota-id`), re-run V1 with `--layout-mode Tree --parent-quota-id ${PARENT_QUOTA_ID}` and assert the new child appears under the parent subtree.

## V5 — Verify update-quota

After `update-quota`, re-run V2 and assert the changed fields (`QuotaName`, `Description`, `Labels`, `QueueStrategy`, `QuotaConfig`) match the new values.

## V6 — Verify scale-quota

After `scale-quota`, re-run V2 and assert `Min` equals the supplied target (absolute, not delta). Re-run `list-quota-workloads` to confirm in-flight workloads were not preempted unexpectedly.

```bash
aliyun paistudio list-quota-workloads --region "${REGION_ID}" --quota-id "${QUOTA_ID}" --page-size 20
```

## V7 — Verify workspace attach (`create-workspace-resource --option Attach`)

```bash
aliyun aiworkspace list-resources --region "${REGION_ID}" --workspace-id "${WORKSPACE_ID}" --resource-type ECS
```

**Pass when:** The attached `QuotaId` appears under the workspace's resource list with the correct `ResourceType`.

## V8 — Verify workspace detach (`delete-workspace-resource`)

```bash
aliyun aiworkspace list-resources --region "${REGION_ID}" --workspace-id "${WORKSPACE_ID}"
```

**Pass when:** The detached `QuotaId` / `ResourceId` is no longer present in the workspace's resource list.

## V9 — Verify delete-quota

```bash
aliyun paistudio get-quota --region "${REGION_ID}" --quota-id "${QUOTA_ID}"
# Expect non-zero exit and a "QuotaNotFound" / 404-style error.
```

## Cross-check with documentation

| Verification | Source |
| --- | --- |
| Quota status / `ResourceType` enums | https://help.aliyun.com/zh/pai/user-guide/ai-computing-resource-management/ |
| `QueueStrategy` enum | `PaiStrategyIntelligent` (auto/intelligent), `PaiStrategyStrictFIFO` (FIFO), `PaiStrategyBalance` (fair/balanced), `PaiStrategyRoundRobin` (round-robin). Yuque API spec (auth required): https://aliyuque.antfin.com/pai/api-doc/pgmtpuwcv6k9vo7q |
| RAM action mapping | https://help.aliyun.com/zh/pai/user-guide/configure-custom-ram-authorization-policy |
| Public PAI OpenAPI portal | https://next.api.aliyun.com/document/PaiStudio/2022-01-12/overview |
| Public AIWorkSpace OpenAPI portal | https://next.api.aliyun.com/document/AIWorkSpace/2021-02-04/overview |
