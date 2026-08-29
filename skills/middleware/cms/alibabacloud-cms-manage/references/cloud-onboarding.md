# Cloud Service Onboarding

## Cloud Onboarding Workflow

Follow [Standard Onboarding](integration-common.md#standard-onboarding) with these Cloud-specific requirements.

1. **Addon discovery**: scope the candidates by the target service's entity type per [Addon Discovery for Cloud Services](#addon-discovery-for-cloud-services).
2. **Addon Selection Gate**: apply [Addon Selection Gate](integration-common.md#addon-selection-gate-hard-requirement) to the scoped set. For batch onboarding of multiple cloud services, see [Choosing an Onboarding Method](#choosing-an-onboarding-method).
3. **Addon schema**: read the entry addon's schema and build `values` per [Addon Values Defaults](integration-common.md#addon-values-defaults-hard-requirement), reading `environments[].name` for `--env-type`, `environments[].policyType` for the policy, and `environments[].policies.bindEntity.entityType` for the scoped query. Take the child set from that schema, never from a remembered product list, and settle the result by the fan-out check in step 12.
4. **Resource Scope Selection Gate**: apply [Resource Scope Selection Gate](integration-common.md#resource-scope-selection-gate-hard-requirement) with the addon's `environments[].policies.bindEntity.entityType` from step 3 as the entity type for both the region discovery and the scoped query.
5. **Scoped resource verification**: verify concrete IDs per [Resource Identity Verification](integration-common.md#resource-identity-verification).
6. **Multi-Region Grouping Gate**: apply [Multi-Region Resource Grouping Gate](integration-common.md#multi-region-resource-grouping-gate-hard-requirement); each group it produces runs steps 7–12 independently.
7. **Workspace Selection Gate**: apply [Workspace Selection Gate](integration-common.md#workspace-selection-gate-hard-requirement).
8. **Existing Policy Reuse Gate**: apply [Existing Policy Reuse Gate](integration-common.md#existing-policy-reuse-gate-hard-requirement) with its Cloud filters.
9. **Create policy** (if needed): name it per [Policy Name Defaulting](integration-common.md#policy-name-defaulting-hard-requirement), setting `policyType` from the addon's `environments[].policyType`.
10. **Addon Release Region Requirement**: run the [pre-check](integration-common.md#addon-release-region-requirement-hard-pre-check) before creating the addon release.
11. **Create addon release**: build `values` per [Addon Values Defaults](integration-common.md#addon-values-defaults-hard-requirement), set the resource scope in the body's `entityRules`, both shaped per [Addon Release Create Body Shape](integration-common.md#addon-release-create-body-shape). `aliyun cms2 integration addon-release create` (flags from `--help`). Show the planned addon release (policy ID, addon name, resource scope, values summary) and wait for explicit user confirmation before executing.

12. **Verify addon release status**: `aliyun cms2 integration addon-release list --policy-id <policyId> -o json`, **without** `--addon-name` so that any child releases the addon fanned out are evaluated too.

    Judge every release the policy returns on its own `conditions`, per [Rules for Determining Addon Release Status](integration-common.md#rules-for-determining-addon-release-status): each must reach `Success`. If `Installing`, wait and re-check. If `Failed`, report the failing release's `addonName` together with its conditions.

## Addon Discovery for Cloud Services

Build the candidate set with the projection in [Addon Selection Gate](integration-common.md#addon-selection-gate-hard-requirement) Step 0, using the target service's entity type resolved below.

Unlike CS (`scene=container`) and ECS (`scene=host`), cloud services share no single `scene`. So never carry over a fixed `scene` from those two workflows. The entity type on its own usually leaves a set small enough to take straight to the gate; narrow further only when it does not, and then by the `scene` the candidates themselves report.

### Resolving the entity type

**Never derive an entity type from the service name or the addon name.** The product segment is often a different name (`cloud-acs-serverless` binds `acs.sae.application`), the resource segment is often not `instance` (`cloud-acs-privatelink-epsrv` binds `acs.privatelink.vpcendpointservice`), and it is sometimes more than two segments (`cloud-acs-adb-datawarehouse` binds `acs.adb.cluster.mysql.datawarehouse`) — and a wrong guess returns an empty candidate set that looks exactly like "no addon exists".

**Resolve it from CloudResource by probing the product prefix**, which enumerates every granularity the account actually owns under that product:

```bash
aliyun cms2 entity query --source CloudResource --from <from> --to <to> \
  --sql ".entity with(domain='acs') | where __entity_type__ like 'acs.<productCode>.%' | project __entity_type__ | limit 0, 500" \
  | tail -n +3 | sort -u
```

Keep the `project` stage before `limit` per [CloudResource Aggregation](integration-common.md#cloudresource-aggregation-hard-requirement). `tail -n +3` drops the CLI's `# ... truncated=` metadata line and the column header so that only values are sorted; read that metadata line separately to confirm the 500-row cap did not cut the result short.

`acs.alikafka.%` returns `acs.alikafka.consumergroup`, `acs.alikafka.instance`, and `acs.alikafka.topic` — pick the granularity the addon monitors, generally the instance-level one. An instance ID the user named, resolved through the same source, and the Step 1a inventory of the [batch workflow](batch-onboarding-workflow.md) are equally valid origins.

**An empty result means the account owns nothing of that granularity, which is a valid onboarding answer** — not a reason to fall back to keyword search. The inventory holds `acs.kms.key` and `acs.kms.secret` but no `acs.kms.instance`, which is what `cloud-acs-kms` binds, so that addon has nothing to onboard here and reporting the absence is correct.

### Keyword search fallback

**Applies only when no entity type can be resolved from CloudResource** ([Addon Selection Gate](integration-common.md#addon-selection-gate-hard-requirement)). It matches case-insensitive substrings across name, alias, description, and keywords, so it over-collects both ways: a short token reaches far past the service (often by hitting the `Cross` inside `Feature:CrossAccount`/`Feature:CrossRegion`), and an accurate one still pulls in neighbours.

Read each candidate's `environments[].policies.bindEntity.entityType` with `aliyun cms2 integration addon get` and drop everything bound to another resource type before applying the gate — `aliyun cms2 integration addon list` strips `policies` to `{}`, so the binding is invisible in the list output.

Two addons legitimately sharing one entity type is a real ambiguity rather than a scoping failure: `cloud-acs-swas` and `cloud-acs-swas-metrics` both bind `acs.swas.instance` with identical `scene`, `weight`, and keywords, and both carry `GroupMode:true`. Rule 4 applies — ask.

## Changing Settings on an Existing Cloud Release

Follow [Addon Release Config Update](integration-common.md#addon-release-config-update-hard-requirement). What makes its child-release trap easy to hit here is that a Cloud entry addon declares almost nothing of its own — typically only `addons.<child>` fields. So the setting the user names is nearly always in a child, and its `fieldPath`s come from that child's own `aliyun cms2 integration addon get` with the child's `--env-type`. The same field often repeats on every engine child (`enableHighResolutionMonitor` on `cloud-rds`); a phrase that names it is a broadcast — update each hitting child release, not only the one whose `config` already shows the key. Do not wait for those children to pick up an entry-only write, and do not send one. Close a child with `aliyun cms2 integration addon-release delete`; open a child with `aliyun cms2 integration addon-release create` on that child's `addonName`. Leftover closed children in the unfiltered list are not present.

## Choosing an Onboarding Method

- **Batch onboarding for multiple cloud services** — addon `cloud-batch-metrics` (`aliyun cms2 integration addon list --search "BatchCloud:CloudMetric"`). Run the [batch workflow](batch-onboarding-workflow.md), whose [6c](batch-onboarding-workflow.md#6c-resolve-the-user-policy-and-create-the-addonrelease) composes `values` from the selected products rather than leaving it empty. When creating/updating a release, validate `entityRules.entityTypes` against those products' `environments[].policies.bindEntity.entityType`; `aliyun cms2 integration addon get --addon-name cloud-batch-metrics` returns no `entityTypes` of its own. Products actually onboarded come from `values.addons`, not from `entityRules`.
- **Single service or custom scope** — use the product-specific addon, discovered per [Addon Discovery for Cloud Services](#addon-discovery-for-cloud-services).

## Fleet Audit for Cloud Service Resources

**Read-only path**, triggered by "all RDS instances", "each SLB", "all cloud service resources", and similar fleet-wide status questions for Cloud sub-types. If the request also asks to onboard what is missing ("将未接入的 RDS 接入云监控"), it is an onboarding task instead: run [Cloud Onboarding Workflow](#cloud-onboarding-workflow), taking the region and scope from the [Resource Scope Selection Gate](integration-common.md#resource-scope-selection-gate-hard-requirement) rather than the all-regions default below.

Never answer from the policy list alone. Run both sides where the inventory is available, and keep them apart in the report — a healthy release proves onboarding, the inventory only shows what exists:

1. Identify the target addon from the service/resource name per [Addon Discovery for Cloud Services](#addon-discovery-for-cloud-services), never by guessing from resource IDs or old naming patterns. Then run `aliyun cms2 integration addon get --addon-name <targetAddonName> -o json` and read `addon.environments[].policies.bindEntity.entityType` and `addon.environments[].policyType`.
2. List candidate policies by addon name: `aliyun cms2 integration policy list --addon-name <targetAddonName> --max-results 100 -o json`, paginating to completion.
3. Optionally cross-check by Cloud sub-type: `aliyun cms2 integration policy list --policy-type <policyType> --max-results 100 -o json`.
    - Policies returned only by `--policy-type` are not onboarding evidence unless `aliyun cms2 integration addon-release list --policy-id <policyId>` returns a healthy release for `targetAddonName`.
    - If a policy has no release for the target addon, report it as "policy exists but target addon release missing" rather than onboarded.
4. For each target addon release, evaluate status using [Rules for Determining Addon Release Status](integration-common.md#rules-for-determining-addon-release-status) and determine coverage from the release scope (`regionIds`, `instanceIds`, `resourceGroupId`, `tags`, or `entityQueries[].spl`).
5. Apply [CloudResource Query Region Handling](integration-common.md#cloudresource-query-region-handling) — for an audit that means all regions unless the user limited them — then query CloudResource for the addon's entity type in the selected time range and compare `instance_id` against the release scopes:
    - In both sets: report the resource as covered by the healthy release.
    - In CloudResource only: report as not covered by any healthy release, unless it is a deleted/historical resource and the user only wants active resources.
    - In release scope only: report as policy/release scope exists but the resource was not found in CloudResource during the selected time range.
6. Zero rows, an empty body, or no entity details from CloudResource proves neither that the resources are absent nor that they are all onboarded. Mark the inventory side `Unknown` / `InventoryUnavailable`, keep reporting release coverage, and state the region and time-window limitation in the final answer. A known instance ID from a release scope also returning zero rows is strong evidence that the inventory is unavailable for this audit.

## Cloud Teardown Verification

Follow [Post-Delete Verification](integration-common.md#post-delete-verification), with one Cloud-specific catch: deleting a Cloud entry release does not cascade to the children it fanned out. They outlive the parent, and their `parentAddonReleaseId` is cleared rather than left dangling, so do not use a leftover parent pointer as the survivor signal — list the policy's releases **without** `--addon-name` and delete each survivor on its own before calling the teardown complete.
