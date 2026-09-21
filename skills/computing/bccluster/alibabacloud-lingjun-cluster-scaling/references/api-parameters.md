# API Parameters Reference (Condensed Edition)

> **⚠️ This document has been condensed (2026-05 governance)** — the original per-API parameter tables (§1-15) have been migrated to their corresponding "single sources of truth" (see the redirect table below). This file keeps 2 items that are **unique to this repo**:
> 1. **§A** [ListNodeGroups response field trap](#a-listnodegroups-groupsgroupid-field-trap) — `Groups[].GroupId` ≠ `NodeGroupId`, plus a field-naming comparison table across adjacent APIs
> 2. **§B** [Agent parameter-completion priority decision tree](#b-parameter-completion-priority-agent-decision-tree) — 6 overview-level strategies

> **⚠️ Region Required (MANDATORY)** ｜ Every `aliyun eflo-controller` command example in this file **must** explicitly carry `--region <region>` (`<region>` given explicitly by the user via HITL; defaulting / reusing / persisting via environment variable is **strictly forbidden**). The endpoint is auto-derived by the aliyun CLI from `--region`; an explicit `--endpoint` is **neither needed nor desired** (see [SKILL.md §B-6 Region Required](../SKILL.md)). This rule does **not** apply to `aliyun bssopenapi` and `aliyun ecs` commands.

---

## Redirect Table (indexed by API category)

| API category | Source of truth | Notes |
| --- | --- | --- |
| ListClusters / DescribeCluster / ListClusterNodes (read-only) | [cluster-query.md](../workflows/cluster-query/cluster-query.md) | Full JSON response examples + field explanations |
| ExtendCluster (mutating, async) | [../workflows/extend-cluster/schema.yaml](../workflows/extend-cluster/schema.yaml) | `cli_top_level_args` + `NodeGroups[]` field-level contract + Path A/B decision |
| ShrinkCluster (mutating, async) | [../workflows/shrink-cluster/schema.yaml](../workflows/shrink-cluster/schema.yaml) | Includes `forbidden_user_facing_phrases` ("data loss" style phrasing strictly banned) |
| BssOpenApi CreateInstance (node purchase, async) | [../workflows/create-instance/schema.yaml](../workflows/create-instance/schema.yaml) | `Period↔StageNum` coupling + full `Parameter.N` commodity attribute list |
| DescribeNode / DeleteNode (node) | [node-operations.md](../workflows/node-operations/node-operations.md) + [delete-node.yaml](../workflows/delete-node/schema.yaml) | Includes `Networks[]` inner structure + RDMA inference ban |
| ChangeNodeGroup (migration, async) | [../workflows/change-node-group/schema.yaml](../workflows/change-node-group/schema.yaml) | Includes `preflight_checks` (same cluster / same machine type) |
| CreateNodeGroup | [create-node-group.md](../workflows/create-node-group/create-node-group.md) + [create-node-group.yaml](../workflows/create-node-group/schema.yaml) | `--node-group` nested JSON / template vs flag vs inherited field disambiguation |
| UpdateNodeGroup | [update-node-group.md](../workflows/update-node-group/update-node-group.md) + [update-node-group.yaml](../workflows/update-node-group/schema.yaml) | delta update; `NewNodeGroupName` server-side required; `forbidden_cli_flags` 8-item hallucination list |
| DeleteNodeGroup (delete empty group, sync, irreversible) | [../workflows/delete-node-group/schema.yaml](../workflows/delete-node-group/schema.yaml) | `--cluster-id` mandatory (missing → 403); group must have NodeCount=0; ambiguity 3-way self-check |
| ListNodeGroups / DescribeNodeGroup (read-only) | [node-group-query.md](../workflows/node-group-query/node-group-query.md) | Includes the `Groups[].GroupId` ≠ `NodeGroupId` field trap + full JSON examples |
| DeleteHyperNode (release hyper node) | [delete-hyper-node.md](../workflows/delete-hyper-node/delete-hyper-node.md) + [../workflows/delete-hyper-node/schema.yaml](../workflows/delete-hyper-node/schema.yaml) | Irreversible + contained-node-count disclosure + subscription ABORT |
| ListHyperNodes / ListClusterHyperNodes / ListFreeHyperNodes / DescribeHyperNode (4 read-only) | [hyper-node-query.md](../workflows/hyper-node-query/hyper-node-query.md) | Includes the 6 OperatingState display mapping + semantic differences of the 3 list-* APIs |
| ListMachineTypes / ListImages / ECS DescribeImages | [../workflows/machine-image-query/machine-image-query.md](../workflows/machine-image-query/machine-image-query.md) | Machine types + system images + custom images |
| DescribeTask (async task query) | [SKILL.md §Task Monitoring](../SKILL.md) + [edge-cases.md §1.5](edge-cases.md#15-long-running-async-task-ux-client-experience) | Dual-mode UX + `pending-tasks.json` schema |

> **The final source for real CLI flags and required / optional lists**: the measured output of `aliyun <ns> <action> --help` + the `cli_top_level_args` sections of each mutating-schema yaml. **Never** treat this document's historical wording or other documents' condensed tables as authoritative.

---

## §A. ListNodeGroups `Groups[].GroupId` Field Trap (MANDATORY)<a id="a-listnodegroups-groupsgroupid-field-trap"></a>

> ⚠️ **Request parameter vs response field name asymmetry**: the request side uses `--node-group-id` (corresponding field `NodeGroupId`), but in the `list-node-groups` response body the node-group list field is named **`Groups[].GroupId`**, **not** `Groups[].NodeGroupId`. When parsing the response the Agent must read `.Groups[].GroupId`; downstream `--node-group-id` inputs should also be taken from that field. Misusing `Groups[].NodeGroupId` yields `null` and creates a false "node group not found" impression.

### Response Structure Example

```json
{
  "RequestId": "...",
  "NextToken": "...",
  "Groups": [
    {
      "GroupId": "ng-xxxxx",
      "GroupName": "...",
      "ClusterId": "i114578350683260641xxxx",
      "MachineType": "efg1.nvga1",
      "ZoneId": "cn-wulanchabu-b",
      "ImageId": "i190257070586432110xxxx",
      "NodeCount": 4
    }
  ]
}
```

### Adjacent API Field-Naming Comparison (keep them straight, avoid cross-wiring)

| API | List field | Node-group ID field |
| --- | --- | --- |
| `list-node-groups` | `Groups[]` | **`GroupId`** ⚠️ |
| `describe-node-group` | top-level object | `NodeGroupId` |
| `list-cluster-nodes` (node view) | `Nodes[]` | `NodeGroupId` |
| `extend-cluster` / `shrink-cluster` (request body) | `NodeGroups[]` | `NodeGroupId` |

> 💡 `lib/query-zh.sh`'s `_lj_render_node_group_list` / `_lj_render_node_group_describe` already tolerate both namings via `(.Groups // .NodeGroups // [])`; documentation examples and Agent custom parsing must still follow this section's comparison table exactly.

---

## §B. Parameter-Completion Priority (Agent Decision Tree)<a id="b-parameter-completion-priority-agent-decision-tree"></a>

> 🎯 Whenever parameters need to be completed, the Agent **MUST** decide in the following order. This tree is the **overview-level abstraction** of each mutating-schema's `required_user_confirmed` / `forbidden_inference` / `optional_with_default` sections; no single schema repeats it in full.

```
1. Already in context → reuse (Region / ClusterId / NodeGroupId preferred)
2. Required missing  → read-only query first (list-*) → present results as options → user picks
3. Optional missing  → follow the corresponding mutating-schema yaml's `optional_with_default` / `merged_form_template`
              and present one merged form at once; the user replies in one sentence; per-item interrogation is banned, and describing "skip" as "use default X/Y/Z" is banned
              (triggers [edge-cases.md §4.5 V6 default-value hallucination](edge-cases.md#45-skill-self-violation-not-retryable))
4. Sensitive params  → display as ******, wrap in single quotes at CLI execution time
              (`LoginPassword` etc., see SKILL.md §A.1 Rule 10 V8 security hard rule)
5. Billing params  → mandatory second confirmation before any charge is incurred (`ProductCode` / `SubscriptionType` / `Period` /
              `RenewalStatus` / `BillingCycle` / `PaymentRatio`)
6. High-risk ops  → before anything irreversible the user must reply "confirm"
              (`shrink-cluster` / `delete-node` / `delete-hyper-node`)
```

### "Skip / Explicit Default / Custom" Field Semantics Disambiguation

| Field type | Actual effect of "skip" | Typical fields | Source of truth |
| --- | --- | --- | --- |
| **Template fields** | CLI omits the field → the node-group template is **persisted empty** → later `change-node-group` / expansion validation requires the source node's physical config to match, otherwise it fails | `SystemDisk` / `DataDisk` / `LoginPassword` / `KeyPairName` / `UserData` / `NodeGroupDescription` / `RamRoleName` | [create-node-group.yaml](../workflows/create-node-group/schema.yaml) `optional_with_default` section |
| **Flag fields** | API default (usually `false`), equivalent to "explicit default" | `FileSystemMountEnabled` / `VirtualGpuEnabled` / `IgnoreFailedNodeTasks` | same as above |
| **Inherited fields** | when the user explicitly picks "inherit cluster network config" in HITL, take the ground-truth injection path; skipping on the pretext of "inherit" is **strictly forbidden** (semantic fraud, handled at V3 level) | `VpcId` / `VSwitchId` / `SecurityGroupId` | [extend-cluster.yaml](../workflows/extend-cluster/schema.yaml) `inherit_cluster_network_policy` section |

---

## Related References

- [SKILL.md](../SKILL.md) — Skill main document
- [detailed-rules.md](detailed-rules.md) — Skill global hard rules + Feature 1-11 workflow index
- [../workflows/](../workflows/README.md) — field-level contracts for the 8 mutating actions (**source of truth**)
- [cluster-query.md](../workflows/cluster-query/cluster-query.md) — cluster read-only query tutorial (with JSON examples)
- [extend-cluster.md](../workflows/extend-cluster/extend-cluster.md) — expansion workflow (async mutating + 3-round merged form)
- [shrink-cluster.md](../workflows/shrink-cluster/shrink-cluster.md) — shrink workflow (async mutating + strict "confirm")
- [node-operations.md](../workflows/node-operations/node-operations.md) — node operation detailed flows
- [create-node-group.md](../workflows/create-node-group/create-node-group.md) — node group creation (sync mutating + 3-round merged form)
- [node-group-query.md](../workflows/node-group-query/node-group-query.md) — node group read-only query (list + describe)
- [update-node-group.md](../workflows/update-node-group/update-node-group.md) — node group field update (sync mutating + delta semantics)
- [hyper-node-query.md](../workflows/hyper-node-query/hyper-node-query.md) — hyper node read-only query (list + list-cluster + list-free + describe)
- [delete-hyper-node.md](../workflows/delete-hyper-node/delete-hyper-node.md) — hyper node release (sync mutating + irreversible + contained-node-count disclosure)
- [../workflows/machine-image-query/machine-image-query.md](../workflows/machine-image-query/machine-image-query.md) — machine type / image query details
- [error-codes.md](error-codes.md) — error code classification and handling
- [edge-cases.md](edge-cases.md) — edge scenarios + counter-example case library
