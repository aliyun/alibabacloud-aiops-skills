# Verification Method — PAI Node

## V1 — Verify list-nodes

```bash
aliyun paistudio list-nodes \
  --region "${REGION_ID}" \
  --resource-group-ids "${RESOURCE_GROUP_ID}" \
  --page-number 1 --page-size 5
```

**Pass when:** HTTP 200 with `Nodes[]` and `TotalCount >= 0`. Each item has `NodeName`, `Status`, `EcsSpec`, `MachineGroupId`.

## V2 — Verify single-node inspection (via list-nodes)

> `get-node` is not yet available. Use `list-nodes --node-names` to inspect a single node. All three of `--region`, `--resource-group-ids`, `--page-size 1` are **mandatory** for single-node lookup.

```bash
aliyun paistudio list-nodes \
  --region "${REGION_ID}" \
  --resource-group-ids "${RESOURCE_GROUP_ID}" \
  --node-names "${NODE_NAME}" \
  --page-number 1 --page-size 1
```

**Pass when:** Response returns exactly 1 node matching `NodeName` and includes `Status`, `EcsSpec`, `Cpu`, `Memory`, `Gpu`, `GpuType`, `MachineGroupId`, `ZoneId`, `GmtCreatedTime`.

## V3 — Per-node GPU metrics — NOT VERIFIABLE via this skill

`get-node-gpu-metrics` is NOT in the public `aliyun paistudio` CLI. There is no skill-side verification path for per-node GPU metrics. Verification, when needed, is done by the user against the **PAI 控制台** ResourceGroup / Quota aggregate dashboards.

**Forbidden as verification substitutes** (all violate the skill's node-as-black-box boundary):

- `nvidia-smi` via SSH / `kubectl exec`.
- `kubectl top node` / `kubectl describe node`.
- Prometheus node-exporter / DCGM-exporter direct query.
- SDK / `curl` / MCP against an internal metrics endpoint.

If node-level metrics are genuinely required, escalation is **three-way only**: 平台**运维**团队 / Lingjun 运维工单 / 账号经理.

## V4 — Cross-reference (node ↔ MachineGroup ↔ RG)

```bash
# 1. Read the node's MachineGroupId (via list-nodes)
MG=$(aliyun paistudio list-nodes --region "${REGION_ID}" --resource-group-ids "${RESOURCE_GROUP_ID}" --node-names "${NODE_NAME}" --page-number 1 --page-size 1 --cli-query 'Nodes[0].MachineGroupId')

# 2. Confirm the MachineGroup belongs to the RG
aliyun paistudio get-resource-group-machine-group --region "${REGION_ID}" --resource-group-id "${RESOURCE_GROUP_ID}" --machine-group-id "${MG}"
```

**Pass when:** Step 2 returns HTTP 200 and echoes both `--resource-group-id` and `--machine-group-id`. A non-found error means the node is mis-attributed; re-run V1 to find the correct RG.

## Cross-check with documentation

| Verification | Source |
| --- | --- |
| Node status enum | https://help.aliyun.com/zh/pai/user-guide/ai-computing-resource-management/ |
| Per-node GPU metrics | NOT available in `aliyun paistudio` CLI — see V3 above. Use PAI 控制台 ResourceGroup / Quota dashboards. |
| RAM action mapping | https://help.aliyun.com/zh/pai/user-guide/configure-custom-ram-authorization-policy |
| Public PAI OpenAPI portal | https://next.api.aliyun.com/document/PaiStudio/2022-01-12/overview |
