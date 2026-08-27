# ECS Host Onboarding

## ECS Onboarding Workflow

Follow [Standard Onboarding](integration-common.md#standard-onboarding) with these ECS-specific requirements.

1. **Addon discovery**: build the scoped set with the projection in [Addon Selection Gate](integration-common.md#addon-selection-gate-hard-requirement) Step 0, using `--entity-type acs.ecs.instance`, then narrow it to `scene=host`. Never scope by a name keyword. Expect exactly one candidate in that set to carry `GroupMode:true` — the entry addon, which the gate's rule 3 then auto-selects. If the count is not one, apply rule 4 and ask the user; never settle it by guessing from addon names.
2. **Addon Selection Gate**: apply [Addon Selection Gate](integration-common.md#addon-selection-gate-hard-requirement) to the set from step 1.
3. **Addon schema**: read the entry addon's schema and build `values` per [Addon Values Defaults](integration-common.md#addon-values-defaults-hard-requirement), also reading the node-collector signal configs declared by those children, per [NodeCollector](#nodecollector). Take the child set from that schema, never from the Step 1 candidate set, and settle the result by the fan-out check in step 12. Enabling the monitor child is not a bundle of every collector it can run: those collectors are separate switches on that child's own `.fields`. Do not infer the set from the child `alias`, from Skill markdown, or from a subset of keys already written into `values`. `--env-type` is that section's `environments[].name` for `policyType: ECS`.
4. **Resource Scope Selection Gate**: apply [Resource Scope Selection Gate](integration-common.md#resource-scope-selection-gate-hard-requirement) with entity type `acs.ecs.instance` for both the region discovery and the scoped query.
5. **Scoped resource verification**: verify concrete IDs per [Resource Identity Verification](integration-common.md#resource-identity-verification).
6. **Multi-Region Grouping Gate**: apply [Multi-Region Resource Grouping Gate](integration-common.md#multi-region-resource-grouping-gate-hard-requirement); each group it produces runs steps 7–14 independently.
7. **Workspace Selection Gate**: apply [Workspace Selection Gate](integration-common.md#workspace-selection-gate-hard-requirement).
8. **Existing Policy Reuse Gate**: apply [Existing Policy Reuse Gate](integration-common.md#existing-policy-reuse-gate-hard-requirement) with its ECS filters.
9. **Create policy** (if needed): name it per [Policy Name Defaulting](integration-common.md#policy-name-defaulting-hard-requirement) with `policyType=ECS`.
10. **Addon Release Region Requirement**: run the [pre-check](integration-common.md#addon-release-region-requirement-hard-pre-check) before creating the addon release.
11. **Create addon release**: build `values` per [Addon Values Defaults](integration-common.md#addon-values-defaults-hard-requirement), set the resource scope in the body's `entityRules`, both shaped per [Addon Release Create Body Shape](integration-common.md#addon-release-create-body-shape), then execute:

    ```bash
    aliyun cms2 integration addon-release create --policy-id <policyId> --body '<requestBody>' < /dev/null
    ```

    Show the planned addon release (policy ID, addon name, resource scope, values summary) and wait for explicit user confirmation before executing.

12. **Verify addon release status**: list the policy's releases per step 3 of [Determining Onboarding & Monitoring Status](integration-common.md#determining-onboarding--monitoring-status), then judge only the group under the release just created — the policy may already hold an earlier entry release whose children are a separate set.

    Every child left enabled must appear in that group (see [Addon Values Defaults](integration-common.md#addon-values-defaults-hard-requirement)). Expect `ecs-loong-collector` whenever `cloud-acs-ecs-audit` or `cloud-acs-ecs-runtime-security` is enabled — both install that probe. Require each enabled child to be present, never that the group match `values.addons` one for one.

    Judge every release **in that group** on its own `conditions`, per [Rules for Determining Addon Release Status](integration-common.md#rules-for-determining-addon-release-status): each must reach `Success`. If `Installing`, wait and re-check. If `Failed`, report the failing release's `addonName` together with its conditions. A release outside the group belongs to an earlier onboarding and its state is not this step's verdict — report it separately if it is unhealthy.

13. **Verify ClusterCollector health**: query collector status as described in [Collector Status Check](#collector-status-check).

14. **Verify NodeCollector health** (if required): decide from the [NodeCollector signals](#nodecollector) whether the release set needs node-level collection, then query it as described there.

## Collector Status Check

### ClusterCollector

```bash
aliyun cms2 integration collector list --policy-id <policyId> --collector-type ClusterCollector
```

ECS ClusterCollector is `metric-agent`, one per VPC the covered instances live in, so a policy normally returns several; normalize each state per [Determining Onboarding & Monitoring Status](integration-common.md#determining-onboarding--monitoring-status).

### NodeCollector

Query NodeCollector only when node-level collection is required by the release set:

```bash
aliyun cms2 integration collector list --policy-id <policyId> --collector-type NodeCollector
```

Treat these as node-collector signals unless product documentation says otherwise:
- `cloud-acs-ecs-monitor`, whether named in `values.addons` or enabled by the entry schema's default per [Addon Values Defaults](integration-common.md#addon-values-defaults-hard-requirement)
- `ecs-node-exporter`, `ecs-loong-collector`, `cloud-acs-ecs-gpu`
- any other child whose schema declares exporter switches under `install.<exporter>.enable` — read those keys per [Addon Values Defaults](integration-common.md#addon-values-defaults-hard-requirement)

NodeCollector returns one collector per enabled exporter.

If node collection is required and no NodeCollector is returned, classify as `MISSING_NODE_COLLECTOR`; unhealthy states classify as `NODE_COLLECTOR_NOT_READY`.

The workload namespace is `{vpcId}-{policyId}` truncated to 63 characters, so match it by prefix instead of comparing the full policy ID.

## Changing Collection Settings on an Existing ECS Release

Switching an exporter on or off, editing a listen port, or changing the scrape interval follows [Addon Release Config Update](integration-common.md#addon-release-config-update-hard-requirement). Two ECS specifics:

1. **The exporters belong to `cloud-acs-ecs-monitor`, not to `cloud-acs-ecs`** — same for `cloud-acs-ecs-audit` and `cloud-acs-ecs-runtime-security`. Take the switch keys from that child's own schema per [Addon Values Defaults](integration-common.md#addon-values-defaults-hard-requirement). Cloud-service metrics are another switch on that same child, not an implied side-effect of enabling the child. Since `values` replaces the stored config wholesale, a body that names only the keys being changed drops every omitted key from stored `config` — it does not keep them and does not restore schema `defaultValue` (these exporters default to enabled). Send the child's live `config` whole.
2. **Give the uninstall time before reading the data plane as a failure.** `acs-process-exporter` stayed listed with `state: Success` 20 minutes after the switch, its `cloud-acs-ecs-monitor-<instanceId>-process-exporter` workloads reading one `UnInstall`, one blank, and three still `ActiveRunning`.

## Fleet Audit for ECS

**Read-only path.** If the request also asks to onboard what is missing ("将未接入的 ECS 接入云监控"), it is an onboarding task: run [ECS Onboarding Workflow](#ecs-onboarding-workflow), taking the region and scope from the [Resource Scope Selection Gate](integration-common.md#resource-scope-selection-gate-hard-requirement) instead of the all-regions audit default below.

When the user asks to check "ECS CloudMonitor onboarding", "ECS monitoring access", "all ECS policies", or similar ECS fleet status, distinguish two modes:

- **Policy-side health check**: evaluate existing ECS integration policies and their releases/collectors. This proves whether configured ECS onboarding policies are healthy.
- **Inventory coverage check**: compare ECS CloudResource inventory against release scopes. This is required before claiming all ECS instances are onboarded.

### Policy-side health check

1. List all ECS policies: `aliyun cms2 integration policy list --policy-type ECS --max-results 100 -o json`, paginating to completion.
2. For each policy, query all releases **without** `--addon-name`, so that the children the entry addon fanned out are evaluated too: `aliyun cms2 integration addon-release list --policy-id <policyId> --max-results 100 -o json`.
3. If a policy has no releases, classify it only as `NO_RELEASE`; do not query or require collectors for that policy.
4. Evaluate every release using [Rules for Determining Addon Release Status](integration-common.md#rules-for-determining-addon-release-status).
5. If any release is not `Success`, classify the policy as `RELEASE_NOT_READY` and include the addon names and failed condition summaries.
6. For policies with successful releases, query ClusterCollector. Empty result means `MISSING_CLUSTER_COLLECTOR`; any non-healthy state means `CLUSTER_COLLECTOR_NOT_READY`.
7. Query NodeCollector per [NodeCollector](#nodecollector) and apply the classifications defined there.
8. Assign each policy to exactly one highest-priority category: `QUERY_FAILED` → `NO_RELEASE` → `RELEASE_NOT_READY` → `MISSING_CLUSTER_COLLECTOR` → `CLUSTER_COLLECTOR_NOT_READY` → `MISSING_NODE_COLLECTOR` → `NODE_COLLECTOR_NOT_READY` → `OK`.

### Inventory coverage check

1. Apply [CloudResource Query Region Handling](integration-common.md#cloudresource-query-region-handling) before querying CloudResource.
2. Query CloudResource for `acs.ecs.instance` in the selected time range, with the region coverage that rule settles: `aliyun cms2 entity query --source CloudResource --from <from> --to <to> --entity-type acs.ecs.instance -o json`.
3. Expand each release's scope per step 3 of [Determining Onboarding & Monitoring Status](integration-common.md#determining-onboarding--monitoring-status).
4. Compare CloudResource `instance_id` with healthy release scopes:
    - In both sets: covered by a healthy ECS onboarding release.
    - In CloudResource only: not covered by any healthy release, unless it is deleted/historical and the user requested only active instances.
    - In release scope only: policy/release scope exists but the instance was not found in CloudResource during the selected time range.
5. If CloudResource returns zero rows, an empty body, or no entity details, mark inventory as `Unknown` / `InventoryUnavailable`; do not claim there are no ECS instances or that all ECS instances are onboarded.

## ECS Teardown Verification

Follow [Post-Delete Verification](integration-common.md#post-delete-verification), with one ECS-specific catch: deleting a `cloud-acs-ecs` release does not cascade to the children it fanned out. They outlive the parent, still pointing at a `parentAddonReleaseId` that no longer resolves, so list the policy's releases **without** `--addon-name` and delete each survivor on its own before calling the teardown complete.
