# Container (CS) Onboarding

## Default Region Scope (Hard Requirement)

CS keeps a **single-region default**, recommending the current workspace's region, plus an explicit multiple-regions option. This **overrides** both the all-regions default in [CloudResource Query Region Handling](integration-common.md#cloudresource-query-region-handling) and the CrossRegion "all regions" recommendation in [Resource Scope Selection Gate](integration-common.md#resource-scope-selection-gate-hard-requirement) Step 1: the clusters CS onboards are never taken from an unscoped query. The one exception is the region distribution in step 1 below, which yields region names with counts only — never a candidate cluster list.

1. **For onboarding, always run the region distribution discovery before asking the region question**, even when a runtime context workspace already pins a region. One query, aggregated locally per [CloudResource Aggregation](integration-common.md#cloudresource-aggregation-hard-requirement):

    ```bash
    aliyun cms2 entity query --source CloudResource --from <from> --to <to> \
      --sql ".entity with(domain='acs', type='acs.ack.cluster') | project region_id | limit 0, 1000" \
      | tail -n +3 | sort | uniq -c | sort -rn
    ```

    `tail -n +3` drops the CLI's `# ... truncated=` metadata line and the column header so that `uniq -c` counts values only; read the metadata line separately to confirm the 1000-row cap did not truncate. It is unscoped by design — that is what makes the other regions visible. A request like 「将未接入的集群接入云监控」 names no region, so offering only the workspace's region silently drops every cluster living elsewhere and the user has no way to notice. Present every region holding clusters with its count, and repeat the query for `acs.asi.cluster` when ASI clusters may exist.
2. The **recommended** region is the runtime context workspace's region, or the region holding the most clusters when there is none. **For onboarding, recommended means pre-selected, not confirmed — ask the region question and wait for the answer**, including when a runtime context workspace already pins one region; a read-only [fleet audit](#fleet-audit-for-container-clusters) may apply the recommendation directly and state the coverage. Do not try to resolve a workspace first — the [Workspace Selection Gate](integration-common.md#workspace-selection-gate-hard-requirement) needs a target region as input, so it runs after the region is confirmed.
3. `workspaceRegion` is the confirmed region of the batch being processed; restrict every `aliyun cms2 entity query --source CloudResource` call for that batch to it, carrying the region as a `where region_id = '<workspaceRegion>'` predicate under `--sql` per [General Conventions](integration-common.md#general-conventions). `--region` remains correct in `--entity-type` mode.
4. Clusters outside the confirmed region(s) are out of scope: do not look up their policies, resolve workspaces for their regions, or list them in the plan or confirmation. If an earlier step already surfaced them, state once that they are out of scope and drop them.

## CS Onboarding Workflow

Follow [Standard Onboarding](integration-common.md#standard-onboarding) with these CS-specific requirements.

1. **Order**: the addon is settled first — steps 2–4, all read-only — because its `Feature:CrossRegion` keyword decides whether step 5 offers one region or several. Nothing about the region is asked before step 5, and the workspace follows in step 8, once the region is confirmed.
2. **Addon discovery**: build the scoped set with the projection in [Addon Selection Gate](integration-common.md#addon-selection-gate-hard-requirement) Step 0, using `--entity-type acs.ack.cluster` (`acs.asi.cluster` for ASI), then narrow it to `scene=container`. Both halves matter: the entity type alone still returns the APM addons that bind to clusters, several of which carry their own `GroupMode:true` under `policyType: CS`. Never scope by a name keyword.
3. **Addon Selection Gate**: apply [Addon Selection Gate](integration-common.md#addon-selection-gate-hard-requirement) to the scoped set. For ACK, expect exactly one `GroupMode:true` addon after step 2, per [ACK Addon Hierarchy](#ack-addon-hierarchy-hard-requirement): re-check that scoping first if the count is not one; only a set that is already `scene=container` and still not one goes to rule 4. Never override the gate by picking an addon name.
4. **Addon schema and dependency pre-check**: `aliyun cms2 integration addon get --addon-name <selected-addon-name> --env-type <environments[].name> -o json`, then again for every enabled child addon, per [Addon Values Defaults](integration-common.md#addon-values-defaults-hard-requirement) and [Release values for the entry addon](#release-values-for-the-entry-addon). The entry addon's result also carries `keywords` (read `Feature:CrossRegion` for step 5) and `dependencies.services`: run [Addon Release Dependency Pre-Check](integration-common.md#addon-release-dependency-pre-check-hard-requirement) here rather than at release time, so an unactivated service surfaces before the user is asked to confirm anything instead of stranding a batch between policy creation and release creation.
5. **Resource Scope Selection Gate**: apply [Resource Scope Selection Gate](integration-common.md#resource-scope-selection-gate-hard-requirement), including its mandatory scope confirmation checkpoint, **before running any scoped `aliyun cms2 entity query` for clusters**. Run the region distribution discovery of [Default Region Scope](#default-region-scope-hard-requirement) step 1 first; its counts are what the region options are built from. Then ask both questions in one prompt and wait for the answer:

    Phrase both questions and their options in the answer language per [Output Language and Terminology](../SKILL.md#output-language-and-terminology).

    | Question | Options |
    |----------|---------|
    | Onboarding region（接入地域） | every region the discovery found, each with its cluster count, the recommended one pre-selected per [Default Region Scope](#default-region-scope-hard-requirement); plus a multi-region option（多地域）when the addon lacks `Feature:CrossRegion` — each extra region then becomes an independent batch with its own workspace, policy, and release |
    | Onboarding scope（接入范围） | all clusters in the region（全部集群）/ explicit cluster ID list（指定集群 ID 列表）/ resource group（资源组）/ tags（标签） |

    Concrete values (cluster IDs, `rg-` ID, tag key + match mode + values) are collected only after the mode is chosen, per the gate's Step 3 — never pre-filled from an inventory you queried early. The chosen mode filters the candidate clusters; each surviving cluster is still onboarded individually via `bindResource.clusterId`.
6. **Scoped cluster discovery**: run the gate's scoped query within `workspaceRegion` for `acs.ack.cluster`, plus `acs.asi.cluster` when ASI clusters may be in scope, with an explicit time range. For the all-clusters mode — the other scope modes carry their filter in `--sql` per the gate:

    ```bash
    aliyun cms2 entity query --source CloudResource --from <from> --to <to> \
      --sql ".entity with(domain='acs', type='acs.ack.cluster') | where region_id='<workspaceRegion>' | project instance_name, instance_id, region_id, status | limit 0, 1000"
    ```

    Reuse the `--from`/`--to` pair computed at the start of the task, and keep the projection and the output-mode handling per [CloudResource Aggregation](integration-common.md#cloudresource-aggregation-hard-requirement) and [General Conventions](integration-common.md#general-conventions).

    When both entity types are queried, the same cluster can surface through both: **de-duplicate by `instance_id`**, or the duplicate is onboarded twice against the [uniqueness constraint](#ack-uniqueness-constraint).

    **MANDATORY FIELD EXTRACTION CHECKPOINT** — resolve the four fields by header per [General Conventions](integration-common.md#general-conventions) and state them for every target cluster before proceeding to step 7:

    | Field | Usage |
    |-------|-------|
    | cluster name | Display, policy naming (`ACK:{clusterName}`) |
    | cluster ID | `bindResource.clusterId`, `--bind-resource-id` — from `instance_id`, never `__entity_id__` ([Policy Lookup Rules](#policy-lookup-rules)) |
    | region | Must equal `workspaceRegion`; used as `--region` |
    | status | Only `running` clusters can be onboarded |

7. **Existing Policy Reuse Gate — uniqueness check first**: resolve the existing CS policy of every candidate cluster before asking the user to confirm anything. Pick **one** of the two lookup shapes by batch size and never run both — an unfiltered `aliyun cms2 integration policy list --policy-type CS` on top of the per-cluster lookups answers the same question twice:

    | Candidate clusters | Lookup |
    |--------------------|--------|
    | up to ~10 | one `aliyun cms2 integration policy list --policy-type CS --bind-resource-id <clusterId>` per cluster |
    | more | one `aliyun cms2 integration policy list --policy-type CS --max-results 100 -o json`, paginated to completion, then matched locally on `bindResource.clusterId` |

    A match means the cluster is already onboarded under that policy per the [uniqueness constraint](#ack-uniqueness-constraint): never create a second policy for it — report it as already onboarded, and add the target addon release under the existing policy only if the user asks for it and no healthy release already covers it. Clusters with no match take the new-policy path. Apply [Existing Policy Reuse Gate](integration-common.md#existing-policy-reuse-gate-hard-requirement).
8. **Workspace and confirmation** (new-policy path only) — both settled once per batch, never per cluster:

    - **Workspace**: the runtime context one when its region equals `workspaceRegion`, otherwise resolved through the [Workspace Selection Gate](integration-common.md#workspace-selection-gate-hard-requirement) with `workspaceRegion` as the target region.
    - **Confirmation**: build the release values from the step 4 schema first, then show the fields listed in [ACK Workspace Confirmation](#ack-workspace-confirmation-hard-requirement) and wait for an explicit answer before `aliyun cms2 integration policy create`. Several clusters are covered by one prompt, laid out per [Batch confirmation](#batch-confirmation-single-prompt).

    This is the write confirmation, not a second scope question: `bindResource.clusterId` is the `instance_id` extracted in step 6.
9. **Create policy** (new-policy path): name it per [Policy Name Defaulting](integration-common.md#policy-name-defaulting-hard-requirement), set `policyType=CS`, `bindResource.clusterId=<clusterId>`. Pass `--region <workspaceRegion>`, which equals the cluster's `region_id` from step 6.
10. **Addon Release Region Requirement**: run the [pre-check](integration-common.md#addon-release-region-requirement-hard-pre-check) before creating the addon release. Policy region and target region are both `workspaceRegion`, so it should pass without `Feature:CrossRegion`; a mismatch means the region scope was broken earlier — abort and fix the scope. The service dependency pre-check already ran in step 4 and is not repeated per cluster; redo it only if the selected addon changed.
11. **Create addon release**: with the values confirmed in step 8 (built per [Addon Values Defaults](integration-common.md#addon-values-defaults-hard-requirement)), `aliyun cms2 integration addon-release create` (flags from `--help`). Build the body per [Addon Release Create Body Shape](integration-common.md#addon-release-create-body-shape) — for CS the cluster comes from the policy's `bindResource`, so the body carries no `entityRules`.

    The addon name and the values were already confirmed in step 8, so nothing is asked here — a second prompt per cluster would turn an N-cluster batch into 2N prompts.

12. **Verify addon release status**: query `aliyun cms2 integration addon-release list --policy-id <policyId> -o json` **without** `--addon-name`, and identify the children by exclusion, per step 3 of [Determining Onboarding & Monitoring Status](integration-common.md#determining-onboarding--monitoring-status). Expect the entry release beside one per enabled child; further releases, such as a `-umodel` variant of a child, can appear alongside them, so judge each on its own `conditions` per [Rules for Determining Addon Release Status](integration-common.md#rules-for-determining-addon-release-status) rather than treating the set as fixed. Every release must reach `Success`. If `Installing`, wait and re-check. If `Failed`, report the failing release's `addonName` together with its conditions.

13. **Verify ClusterCollector health**: query collector status as described in [Collector Status Check](#collector-status-check). CS policies always require at least one healthy ClusterCollector. Report both the addon release status and collector health in the final result.

## ACK Addon Hierarchy (Hard Requirement)

After step 2's `scene=container` narrowing, expect exactly one candidate to carry `GroupMode:true` — the entry addon, which the gate's rule 3 then auto-selects. If the count is not one, re-check step 2's scoping before anything else: APM addons that bind the same entity type also carry `GroupMode:true` and must not remain in the set. Only a scoped set that is already `scene=container` and still not one goes to rule 4. Never settle it by guessing from addon names or aliases. Take the child set from that addon's own schema as fetched in step 4, per [Addon Values Defaults](integration-common.md#addon-values-defaults-hard-requirement), never from a list reproduced in this document, and settle the result by the fan-out check in step 12.

**Never make a child addon the target of the release.** Creating the release on `cs-default` alone delivers that child's slice and silently drops every other capability the entry addon fans out — events, control-plane logs, Ingress logs — along with the SLS storage fields (`store.storageTarget`, `store.project`) that only `cloud-acs-ack` exposes. Select a child addon only when the user explicitly asks for that one capability by itself. After the entry already exists, opening a missing child is `aliyun cms2 integration addon-release create` with that child's `addonName` on the same policy, per [Addon Release Config Update](integration-common.md#addon-release-config-update-hard-requirement) — not a second entry, and not an update of the gated parent.

Nothing in `environments` tells a child apart from the entry addon: parent and children carry the same `policyType`, `bindEntity.entityType`, `singleEntityMode`, and `dependencies.services`. Nor does the catalog metadata — several children share the entry addon's own `scene` and can read more on-topic than it does. Judge on `GroupMode:true` and `weight` per [Addon Selection Gate](integration-common.md#addon-selection-gate-hard-requirement), never on how on-topic the keywords read.

**ASI works differently**: the `acs.asi.cluster` scoped set holds no `GroupMode:true` addon, so there is no entry addon to auto-select. `asi-default` is the base metrics addon there; `asi-audit-log` and the `asi-*` feature addons are separate opt-ins, not children of it.

### Release values for the entry addon

Composing the body is not CS-specific: follow [Addon Values Defaults](integration-common.md#addon-values-defaults-hard-requirement) and [Addon Release Create Body Shape](integration-common.md#addon-release-create-body-shape).

**Do not look for `feePackage` in the entry addon's schema.** It belongs to `cs-default` and therefore lands at `addons.cs-default.values.feePackage`, yet [ACK Workspace Confirmation](#ack-workspace-confirmation-hard-requirement) and [Batch confirmation](#batch-confirmation-single-prompt) both require it in the values summary — searching only the entry schema ends in reporting it absent. Cross-account CS (`entityUserId` set, [Cross-Account Onboarding](integration-common.md#cross-account-onboarding)) must use `CS_Pro`; `CS_Basic` causes creation to fail.

### Changing settings on an existing CS release

Follow [Addon Release Config Update](integration-common.md#addon-release-config-update-hard-requirement), taking the update targets from step 12's release list — CS children are found by exclusion, and a `-umodel` variant is its own release with its own config. The gated entry is not an update target: field changes go to the child `releaseName`; close a child with `aliyun cms2 integration addon-release delete`; open a child with `aliyun cms2 integration addon-release create` on that child's `addonName`. Do not also update the parent.

## Multi-Cluster Batch Onboarding (Hard Requirement)

All clusters in one batch share one region and one workspace, since the confirmed region scope is per batch. If the user chose multiple regions, each region is its own batch — see [Cross-region batch](#cross-region-batch-explicit-user-request-only). Within a batch, do not group by region and do not resolve additional workspaces.

### Batch execution flow

1. Confirm the region and cluster scope once for the whole batch (workflow step 5).
2. From the scope-filtered query (workflow step 6), keep the clusters with `status=running`.
3. Run the workflow step 7 uniqueness check across the whole batch, drop the clusters that already have a CS policy, and state which ones were dropped and why.
4. Run workflow step 8 once for the batch: resolve the shared workspace, then ask the [Batch confirmation](#batch-confirmation-single-prompt).
5. After that single approval, run workflow steps 9–13 per remaining cluster against the shared workspace, with no further prompt. A per-cluster failure pauses the batch and is reported; it never passes silently.

### Batch confirmation (single prompt)

One prompt covers the whole batch: it shares one region, one workspace, one addon, and one set of release values, so the only thing varying per cluster is its name and ID. Confirming the policy and the release separately for each cluster would cost 2N prompts for N clusters and ask the same question every time.

The prompt carries a per-cluster row for the varying fields and states the shared ones once:

| Part | Content |
|------|---------|
| Per-cluster rows | cluster name, cluster ID (`instance_id`), status — one row per cluster to onboard, plus the policy name `ACK:{clusterName}` each will get |
| Shared, stated once | target region, selected workspace, target account UID, addon name |
| Release parameters | values summary built from the step 4 addon schema, `feePackage` explicitly among them |
| Dependencies | the services checked in step 4 and their activation state |
| Excluded clusters | the ones dropped in batch steps 2 and 3, each with its reason (`status` other than `running`, or an existing CS policy) — listed so the user sees the batch is not the full inventory, not as onboarding targets |

Restate the confirmed region and scope from workflow step 5 alongside it; do not re-ask them. A single-cluster batch uses the same prompt shape.

### Cross-region batch (explicit user request only)

Triggered when the user picks the multiple-regions option in step 5 or names several regions upfront. Treat each region as an independent batch: resolve that region's own workspace via the [Workspace Selection Gate](integration-common.md#workspace-selection-gate-hard-requirement) and rerun the full workflow for it. Never onboard a cluster into a workspace from a different region.

## Collector Status Check

CS policies always require at least one ClusterCollector. `aliyun cms2 integration collector list --collector-type ClusterCollector` (flags from `--help`). Normalize each returned collector's state per [Determining Onboarding & Monitoring Status](integration-common.md#determining-onboarding--monitoring-status), judging each on its own `workloads[]`.

## ACK Uniqueness Constraint

An ACK instance can only be onboarded once, in one workspace under one policy. Use `aliyun cms2 integration policy list --policy-type CS --bind-resource-id <cluster-id>` to directly locate its policy without further filtering.

## ACK Workspace Confirmation (Hard Requirement)

Because an ACK/CS cluster can only be onboarded once, before `aliyun cms2 integration policy create` show these ACK-specific fields and wait for explicit user confirmation:

- cluster name
- cluster ID
- target account UID
- target region
- selected workspace
- addon name
- addon release values summary, `feePackage` included — the release is created right after the policy, so it is confirmed here rather than in a second prompt

Several clusters are confirmed together in one prompt, per [Batch confirmation](#batch-confirmation-single-prompt); the fields above are what that prompt must carry.

**Special case**: The uniqueness constraint is scoped per account. After a cluster is onboarded under its owning account, a Resource Directory delegated administrator account can still onboard the same cluster under the administrator account. Cross-account duplicate onboarding is allowed.

## Policy Lookup Rules

`--bind-resource-id` is CS-only, per [Policy Lookup Rules](integration-common.md#policy-lookup-rules). The two failures below are what confusing `__entity_id__` with `instance_id` actually looks like — the correct value for `bindResource.clusterId` and `--bind-resource-id` is `instance_id`:

| Symptom | Root Cause |
|---------|-----------|
| "The cluster does not exist" when creating CS policy | Used `__entity_id__` instead of `instance_id` as `--bind-resource-id` |
| Fleet audit reports a `running` cluster as not onboarded, but later finds it onboarded | Compared `__entity_id__` against policy `bindResource.clusterId` instead of `instance_id` |

## Fleet Audit for Container Clusters

**Read-only path.** This section covers requests that only ask for the current state ("check all container clusters", "哪些集群没接入"). Once the request also asks to onboard ("将未接入的集群接入云监控"), it is an onboarding task: run [CS Onboarding Workflow](#cs-onboarding-workflow), where step 5's [Resource Scope Selection Gate](integration-common.md#resource-scope-selection-gate-hard-requirement) settles the region and cluster scope instead of the region default below. An audit table is never a confirmed scope — see [Unonboarded Resource Follow-up](integration-common.md#unonboarded-resource-follow-up).

Do not only list existing policies. Run both sides of the comparison:

1. Settle the region coverage first: default to the recommended region per [Default Region Scope](#default-region-scope-hard-requirement), and widen only when the user asks for other regions or all regions. State the coverage in the result.
2. List CS policies: `aliyun cms2 integration policy list --policy-type CS --max-results 100 -o json`, paginating to completion, then drop policies outside the confirmed region(s) so both sides of the comparison share one scope.
3. For each retained CS policy, query addon releases and ClusterCollector status as described above.
4. Query CloudResource for container cluster resource types with the same region filter, once per confirmed region:
    - `aliyun cms2 entity query --source CloudResource --from <from> --to <to> --entity-type acs.ack.cluster --region <region> -o json`
    - `aliyun cms2 entity query --source CloudResource --from <from> --to <to> --entity-type acs.asi.cluster --region <region> -o json`
5. **Compare on `instance_id`, never `__entity_id__`** ([Policy Lookup Rules](#policy-lookup-rules)): match CloudResource `instance_id` against policy `bindResource.clusterId`, de-duplicating across both entity types as in workflow step 6.
    - In both sets: evaluate release and collector status.
    - In CloudResource only: report as not onboarded or historical resource, and include the CloudResource `status`; any status other than `running` is itself the blocking reason.
    - In policy only: report as policy exists but the resource was not found in CloudResource during the selected time range.

## CS Teardown Verification

Follow [Post-Delete Verification](integration-common.md#post-delete-verification); CS adds no catch of its own.
