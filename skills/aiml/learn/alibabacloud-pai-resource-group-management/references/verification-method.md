# Verification Method — PAI ResourceGroup

## V1 — Verify list-resource-groups

```bash
aliyun paistudio list-resource-groups --region "${REGION_ID}" --page-number 1 --page-size 5
```

**Pass when:** HTTP 200 with `ResourceGroups[]` and `TotalCount >= 0`. Each item has `ResourceGroupId`, `Name`, `ResourceType`, `Status`.

## V2 — Verify get-resource-group

```bash
aliyun paistudio get-resource-group --region "${REGION_ID}" --resource-group-id "${RESOURCE_GROUP_ID}"
```

**Pass when:** Response echoes the requested `ResourceGroupId` and includes `Name`, `ResourceType`, `Status`, `GmtCreatedTime`. For VPC-bound RGs, `UserVpc.{VpcId,SwitchId,SecurityGroupId}` is populated.

## V3 — Verify create-resource-group

After `create-resource-group`, re-run V1 and assert the new `ResourceGroupId` appears with `Status` ∈ `{Initializing, Running}` and the user-supplied `Name`, `ResourceType` match.

## V4 — Verify update-resource-group

After `update-resource-group`, re-run V2 and assert the changed fields (`Name`, `Description`, `UserVpc`) match the new values. For unbind: assert `UserVpc` is empty / null.

## V5 — Verify list-resource-group-machine-groups

```bash
aliyun paistudio list-resource-group-machine-groups --region "${REGION_ID}" --resource-group-id "${RESOURCE_GROUP_ID}" --page-size 5
```

**Pass when:** HTTP 200 with `MachineGroups[]` (may be empty for a freshly-created RG before purchase).

## V6 — Verify get-resource-group-machine-group

```bash
aliyun paistudio get-resource-group-machine-group --region "${REGION_ID}" --resource-group-id "${RESOURCE_GROUP_ID}" --machine-group-id "${MACHINE_GROUP_ID}"
```

**Pass when:** Response echoes the requested `MachineGroupID` and includes `Cpu`, `Memory`, `Gpu`, `GpuType`, `EcsSpec`, `EcsCount`, `Status`, `GmtCreatedTime`.

## V7 — Metrics (DEPRECATED)

> ⚠️ `get-resource-group-total`, `get-resource-group-request`, `get-user-view-metrics`, and `get-node-metrics` are **deprecated** and are NOT supported by this skill. Skip this verification step. If the user requests metrics or pending-request aggregates, inform them that these APIs have been deprecated.

## V8 — Verify delete-resource-group

Precondition (the agent MUST verify before issuing `delete-resource-group`):

```bash
aliyun paistudio list-resource-group-machine-groups \
  --region "${REGION_ID}" --resource-group-id "${RESOURCE_GROUP_ID}" --page-size 1
# Pass: TotalCount == 0. If non-zero, STOP — instruct the user to release MachineGroups
# via the PAI Console (Resource Pool → Machine Group → unsubscribe / release). This skill MUST NOT call
# `delete-resource-group-machine-group` or `delete-machine-group`.
```

Then, after the confirmation gate and successful `delete-resource-group`:

```bash
aliyun paistudio get-resource-group --region "${REGION_ID}" --resource-group-id "${RESOURCE_GROUP_ID}"
# Expect non-zero exit and a "ResourceGroupNotFound" / 404-style error.
```

## Cross-check with documentation

| Verification | Source |
| --- | --- |
| ResourceGroup status enum | https://help.aliyun.com/zh/pai/user-guide/ai-computing-resource-management/ |
| MachineGroup payment / spec fields | Yuque API spec (auth required): https://aliyuque.antfin.com/pai/api-doc/bic3z5 |
| RAM action mapping | https://help.aliyun.com/zh/pai/user-guide/configure-custom-ram-authorization-policy |
| Public PAI OpenAPI portal | https://next.api.aliyun.com/document/PaiStudio/2022-01-12/overview |
