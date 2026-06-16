# Integration Module

## Core Concepts

```
Addon Catalog  →  Integration Policy  →  Addon Release
```

## Onboarding State Semantics

For integration/onboarding status checks, do NOT treat the following as proof that a resource is onboarded:

- CloudResource exists: only proves the cloud resource exists or was observed.
- EntityStore has an entity: only proves an entity was once ingested into a workspace.
- Integration policy exists: only proves a resource scope/entityGroup is bound.

### Determining Onboarding & Monitoring Status

Follow this flow to check whether a resource is onboarded and its monitoring status:

1. **Identify matching addons** — the input may be a resource type name or a resource instance ID/name.
    - Resource type name → `integration addon list --search <typeName>` to find matching addons (may return multiple).
    - Resource instance ID/name → `entity query --source CloudResource` to resolve the resource type, then query matching addons by type.
    - If multiple plausible addons match the same resource type/capability, follow [Addon Selection Gate](#addon-selection-gate-hard-requirement) before continuing.
2. **Find candidate policies**: `integration policy list --addon-name <targetAddonName>` to list all policies that may cover the target addon. For ACK/CS, see [Special case — ACK](#determining-onboarding--monitoring-status) for a more direct query path and follow [Policy Lookup Rules](#policy-lookup-rules). For Cloud sub-types such as RDS, SLB, and ALB, `--addon-name` is the primary lookup path; `--policy-type <addon.environments[].policyType>` may be used as a cross-check, but every returned policy must still be verified with a target addon release before it can count as onboarding evidence.
3. **Check addon releases under each policy**: `integration addon-release list --policy-id <policyId> --addon-name <targetAddonName>` to find all releases of the target addon under the policy.
    1. **Policy type is `Default`**: if `policy.policyType == "Default"`, this is the default policy. The target addon release status directly reflects the resource onboarding status.
    2. **Policy type is not `Default`**: first check whether the target addon release has a non-empty `parentAddonReleaseId`.
        - **Has parent**: call `integration addon-release list --policy-id <policyId> --parent-addon-release-id <id>` to get the final target addon release with its covered resource detail list. Resources in this list are onboarded; their status is determined by this final addon release. Resources not in the list are not covered by this policy.
        - **No parent**: the release itself is the status carrier. Determine the covered scope from the release first: `entityRules.entityRules` fields such as `regionIds`, `instanceIds`, `resourceGroupId`, and `tags`, then `entityRules.entityQueries[].spl` when present. For Cloud sub-types, a healthy release plus this release scope is the primary onboarding evidence; `entity query --source EntityStore` is optional for expanding already ingested entity details and is not required to prove onboarding. If the release does not include scope details, fall back to policy scope: `Cloud` and its sub-types use `entityGroup`; `CS` uses `bindResource`.
4. **Check collector status** (per policy):
    - **CS or ECS policy type**: `integration collector list --policy-id <policyId> --collector-type ClusterCollector`. Normalize collector state by collector deployment type:
        - `O11Y_ADDON`: healthy when `state=Success` or its conditions evaluate to Ready/Success.
        - `ACK_ADDON`: healthy when `state=active`.
        - Any `Failed`, `UnInstallFailed`, `inactive`, failed condition, or missing required collector is unhealthy.
        - A collector is **required** when the policy's addon releases expect it: CS policies always require at least one ClusterCollector. ECS policies require ClusterCollector only after at least one addon release exists under the policy; if a policy has no releases, classify it as `NO_RELEASE` and do not also classify it as a missing collector.
    - **ECS policy type**: additionally query `integration collector list --policy-id <policyId> --collector-type NodeCollector` only when the ECS addon releases require node-level collection. Apply the same collector state normalization. If any required node collector is unhealthy, the corresponding VPC (namespace pattern: `{vpcId}-{policyId}`) is unhealthy.
    - **Cloud and its sub-types**: no collectors; skip this step.

Evaluate addon release status using [Rules for Determining Addon Release Status](#rules-for-determining-addon-release-status). A resource is considered successfully onboarded only when the required addon(s) for the requested monitoring capability have a healthy release (status = Success) and the required collectors are healthy. A policy without addon releases, or with only unrelated addon releases, does not constitute successful onboarding.

### Unonboarded Resource Follow-up

When a status check or fleet audit identifies concrete active resource(s) that are not onboarded to CloudMonitor, ask the user whether to onboard this resource or these resources to CloudMonitor before proceeding further.

- Ask only for concrete active resources that are not covered by any healthy release, have no matching policy/release, or are otherwise classified as not onboarded.
- Do not ask for resources whose inventory status is `Unknown` / `InventoryUnavailable`, resources that only appear historical/deleted, or cases where the user explicitly asked for audit/reporting only.
- If the user agrees, continue with [Standard Onboarding](#standard-onboarding) using the detected resource type and verified resource IDs as inputs. Still apply all required gates: [Addon Selection Gate](#addon-selection-gate-hard-requirement), [CloudResource Query Region Handling](#cloudresource-query-region-handling), [Resource Scope Selection Gate](#resource-scope-selection-gate-hard-requirement), [Workspace Selection Gate](#workspace-selection-gate-hard-requirement), and write-command confirmation.
- If multiple resources are not onboarded, ask whether to onboard all of them or only a selected subset; do not silently choose a subset.

**Optional metric data-plane check**: when the user asks whether metrics are actually queryable, or when stronger end-to-end validation is useful, verify data-plane results separately from onboarding status:

1. For the target addon release found above, run `integration storage list --policy-id <policyId> --addon-release-name <addonReleaseName> --storage-type Prometheus`; if needed, fall back to policy-level storage lookup and choose the entry for the target release.
2. Read `status.instanceId` from the storage result and use it as `--prometheus-id`.
3. Use `metric promql labels`, `label-values`, or `series` only to discover selectors; verify actual samples with `metric promql query` or `query-range`, and inspect returned data, warnings, and any `slsStatus`.
4. Missing or delayed samples may indicate data-plane lag or metric collection issues, but the base onboarding decision remains the healthy addon release plus healthy required collectors described above.

**Special case — ACK**: an ACK instance can only be onboarded once, in one workspace under one policy. Use `integration policy list --policy-type CS --bind-resource-id <cluster-id>` to directly locate its policy without further filtering.

**Note**: addons with `-umodel` suffix provide UModel infrastructure monitoring capabilities. They do **not** count as evidence of base CloudMonitor onboarding, and their failure should be reported as UModel capability degradation rather than base onboarding failure unless the user explicitly asks to check UModel.

### CloudResource Query Region Handling

Before any `entity query --source CloudResource` inventory, resource discovery, or fleet coverage query, apply the global rule from [SKILL.md](../SKILL.md#global-conventions): do not derive regions from workspace/onboarding/policy/release regions, prior commands, CLI defaults, or existing policies. If the user does not explicitly limit the query to specific regions, omit the region parameter and query all regions. Only add a region parameter when the user explicitly asks for limited regional coverage. Always state the final region coverage.

### Policy-scoped Kubernetes Resources

Use `integration resource list` for Kubernetes resources managed by a policy (`ListIntegrationPolicyResources`). It requires `--policy-id` and `--kind`.

```bash
aliyun cms2 integration resource list --policy-id <policyId> --kind Namespace -o json
```

If no policy exists, report the missing `policyId`; do not fabricate one. Do not use `entity query --source CloudResource --entity-type acs.k8s.namespace`, which queries raw CloudResource metadata instead of policy-scoped resources.

### Fleet Audit for Container Clusters

When the user asks to check "all container clusters", "each ACK cluster", or similar fleet-wide onboarding status, do not only list existing policies. Run both sides of the comparison:

1. List all CS policies: `aliyun cms2 integration policy list --policy-type CS --max-results 100 -o json`, paginating to completion.
2. For each CS policy, query addon releases and ClusterCollector status as described above.
3. Apply [CloudResource Query Region Handling](#cloudresource-query-region-handling) before querying CloudResource; CS-policy-derived regions do not limit inventory coverage unless the user explicitly requests that limitation.
4. Query CloudResource for container cluster resource types. By default, omit the region parameter to query all regions; append a region parameter only when the user explicitly limits the audit to specific regions:
    - `aliyun cms2 entity query --source CloudResource --from <from> --to <to> --entity-type acs.ack.cluster -o json`
    - `aliyun cms2 entity query --source CloudResource --from <from> --to <to> --entity-type acs.asi.cluster -o json`
5. Compare CloudResource `instance_id` with policy `bindResource.clusterId`:
    - In both sets: evaluate release and collector status.
    - In CloudResource only: report as not onboarded or historical resource, and include CloudResource `status` such as `running`, `unavailable`, `delete_failed`, or `create_failed`.
    - In policy only: report as policy exists but the resource was not found in CloudResource during the selected time range.

For CloudResource fleet queries, de-duplicate by `instance_id`; the same cluster can appear through both `acs.ack.cluster` and `acs.asi.cluster` sources for some ASI scenarios.

### Fleet Audit for ECS

When the user asks to check "ECS CloudMonitor onboarding", "ECS monitoring access", "all ECS policies", or similar ECS fleet status, distinguish two modes:

- **Policy-side health check**: evaluate existing ECS integration policies and their releases/collectors. This proves whether configured ECS onboarding policies are healthy.
- **Inventory coverage check**: compare ECS CloudResource inventory against release scopes. This is required before claiming all ECS instances are onboarded.

**Policy-side health check**:

1. List all ECS policies: `aliyun cms2 integration policy list --policy-type ECS --max-results 100 -o json`, paginating to completion.
2. For each policy, query all releases: `aliyun cms2 integration addon-release list --policy-id <policyId> --max-results 100 -o json`.
3. If a policy has no releases, classify it only as `NO_RELEASE`; do not query or require collectors for that policy.
4. Evaluate every release using [Rules for Determining Addon Release Status](#rules-for-determining-addon-release-status).
5. If any release is not `Success`, classify the policy as `RELEASE_NOT_READY` and include the addon names and failed condition summaries.
6. For policies with successful releases, query ClusterCollector: `aliyun cms2 integration collector list --policy-id <policyId> --collector-type ClusterCollector -o json`. Empty result means `MISSING_CLUSTER_COLLECTOR`; any non-healthy state means `CLUSTER_COLLECTOR_NOT_READY`.
7. Query NodeCollector only when node-level collection is required by the release set. Treat these addon names/configs as node-collector signals unless product documentation says otherwise:
    - `cloud-acs-ecs` when its config enables `cloud-acs-ecs-monitor`
    - `cloud-acs-ecs-monitor` (can also be activated as a sub-feature of `cloud-acs-ecs`)
    - `ecs-node-exporter`
    - `ecs-loong-collector`
    - `metric-agent`
    - `cloud-acs-ecs-gpu`
    - config values containing enabled `nodeExporter`, `processExporter`, or `windowsExporter`

   If node collection is required and no NodeCollector is returned, classify as `MISSING_NODE_COLLECTOR`; unhealthy states classify as `NODE_COLLECTOR_NOT_READY`.
8. Assign each policy to exactly one highest-priority category: `QUERY_FAILED` → `NO_RELEASE` → `RELEASE_NOT_READY` → `MISSING_CLUSTER_COLLECTOR` → `CLUSTER_COLLECTOR_NOT_READY` → `MISSING_NODE_COLLECTOR` → `NODE_COLLECTOR_NOT_READY` → `OK`.

**Inventory coverage check**:

1. Apply [CloudResource Query Region Handling](#cloudresource-query-region-handling) before querying CloudResource.
2. Query CloudResource for `acs.ecs.instance` in the selected time range. By default, omit the region parameter to query all regions: `aliyun cms2 entity query --source CloudResource --from <from> --to <to> --entity-type acs.ecs.instance -o json`. If the user explicitly limits the audit to specific regions, add the corresponding region parameter.
3. Expand release scopes from `entityRules.entityRules.regionIds`, `instanceIds`, `resourceGroupId`, `tags`, and `entityQueries[].spl` when present.
4. Compare CloudResource `instance_id` with healthy release scopes:
    - In both sets: covered by a healthy ECS onboarding release.
    - In CloudResource only: not covered by any healthy release, unless it is deleted/historical and the user requested only active instances.
    - In release scope only: policy/release scope exists but the instance was not found in CloudResource during the selected time range.
5. If CloudResource returns zero rows, an empty body, or no entity details, mark inventory as `Unknown` / `InventoryUnavailable`; do not claim there are no ECS instances or that all ECS instances are onboarded.

### Fleet Audit for Cloud Service Resources

When the user asks to check "all RDS instances", "each SLB", "all cloud service resources", or similar fleet-wide onboarding status for Cloud sub-types, do not only list existing policies. Run both sides where the resource inventory is available, and clearly separate authoritative onboarding evidence from inventory completeness:

1. Identify the target addon from the service/resource name:
    - Run `aliyun cms2 integration addon list --search <serviceName> -o json`; do not guess addon names from resource IDs or old naming patterns.
    - Apply [Addon Selection Gate](#addon-selection-gate-hard-requirement) before assigning `targetAddonName`.
    - Run `aliyun cms2 integration addon get --addon-name <targetAddonName> -o json` and read `addon.environments[].policies.bindEntity.entityType` and `addon.environments[].policyType`.
2. List candidate policies by addon name: `aliyun cms2 integration policy list --addon-name <targetAddonName> --max-results 100 -o json`, paginating to completion.
3. Optionally cross-check by Cloud sub-type: `aliyun cms2 integration policy list --policy-type <policyType> --max-results 100 -o json`.
    - Policies returned only by `--policy-type` are not onboarding evidence unless `integration addon-release list --policy-id <policyId> --addon-name <targetAddonName>` returns a healthy release.
    - If a policy has no release for the target addon, report it as "policy exists but target addon release missing" rather than onboarded.
4. For each target addon release, evaluate status using [Rules for Determining Addon Release Status](#rules-for-determining-addon-release-status) and determine coverage from the release scope (`regionIds`, `instanceIds`, `resourceGroupId`, `tags`, or `entityQueries[].spl`). Cloud sub-types do not require collectors.
5. Apply [CloudResource Query Region Handling](#cloudresource-query-region-handling), query CloudResource for the addon's entity type in the selected time range, then compare `instance_id` against the release scopes. By default, omit the region parameter to query all regions; add a region parameter only when the user explicitly limits the audit to specific regions:
    - In both sets: report the resource as covered by the healthy release.
    - In CloudResource only: report as not covered by any healthy release, unless it is a deleted/historical resource and the user only wants active resources.
    - In release scope only: report as policy/release scope exists but the resource was not found in CloudResource during the selected time range.
6. If CloudResource returns success with zero rows, an empty body, or no entity details, do not conclude that no resources exist and do not conclude that all resources are onboarded. Mark the inventory side as `Unknown` / `InventoryUnavailable`, continue reporting release coverage, and state the region coverage and time-window limitation in the final answer. If a known instance ID from a release scope also returns zero rows, treat this as strong evidence that CloudResource inventory is unavailable for this audit.

## Onboarding Workflow

All user choices in this module follow the structured choice presentation rule in [SKILL.md](../SKILL.md#global-conventions).

### Addon Selection Gate (Hard Requirement)

After addon discovery, if more than one plausible addon can satisfy the requested resource type or monitoring capability, stop before running any command that depends on a chosen `addonName` and ask the user to choose the target addon. This includes read-only commands such as `addon get`, `policy list --addon-name`, and `addon-release list --addon-name`; do not pick one silently by name, rank, weight, or perceived default.

If discovery or fallback search returns exactly one clear candidate whose metadata matches the requested resource type or monitoring capability, you may use it and state the selected addon and matching evidence. If the single candidate is ambiguous or incomplete, ask for confirmation.

When asking, show only decision-useful differences: addon name, description/alias, environment or policy type, main capability, and likely side effects. You may recommend one, but must wait for explicit selection.

### Prerequisites

- **workspace name**: required for policy creation; see [Workspace Selection Gate](#workspace-selection-gate-hard-requirement) below
- **onboarding region**: target policy/release region (e.g. `cn-hangzhou`)
- **CloudResource query region handling**: resource discovery/listing defaults to all regions by omitting the region parameter; add a region parameter only when the user explicitly limits the query to specific regions
- **onboarding resource scope**: required before policy/release creation; see [Resource Scope Selection Gate](#resource-scope-selection-gate-hard-requirement) below
- **resource ID**: required for instance-scoped onboarding; verify before creating policy/release
- **cluster ID**: required for container scenarios; ID shape alone does not prove ACK/CS identity

### Standard Onboarding

```bash
# 1. Discover addon candidates
aliyun cms2 integration addon list -o text

# 2. Apply the Addon Selection Gate above before using a discovered addon name.
# 3. Fetch the selected addon (output includes full workflow + body template)
aliyun cms2 integration addon get --addon-name <selected-addon-name>

# 4. For inventory/resource discovery, apply CloudResource query region handling: omit region by default; add it only for explicit regional limits.
# 5. For concrete resource IDs, run Resource Identity Verification below.
# 6. Confirm or collect the onboarding resource scope via the Resource Scope Selection Gate.

# 7-9. Follow the Workflow section in addon output:
#   create policy → create release → verify
```

**Mandatory gate before creating or updating addon release:** run the **Addon Release Region Requirement (Hard Pre-Check)** below. If the check fails, stop and report the error to the user.

### Choosing an Onboarding Method

- **Batch onboarding for multiple cloud services** — use addon `cloud-batch-metrics`.
    - Query available cloud products/services via `integration addon list --search "BatchCloud:CloudMetric"`.
    - When creating or updating an addon release (`integration addon-release create` / `update`), the following values must be validated against the `entityTypes` field returned by this query; do not use any value not present in the results:
        - `entityQueries[].entityTypes`
        - `type` values within `entityQueries[].spl`
        - `entityRules[].entityTypes`
- **Single service or custom scope** — use the product-specific addon. Discover via `integration addon list`.

## Key Business Constraints

### Resource Scope Selection Gate (Hard Requirement)

Before creating any integration policy or addon release, if the user did not explicitly specify the onboarding resource scope, you MUST stop and ask the user to confirm or choose the target scope before continuing.

Treat the scope as explicit only when the user has clearly selected one of the supported modes and provided the required values for that mode:

- all resources/all instances
- specific regions, via `regionIds`
- resource group, via `resourceGroupId`
- tag filter, via `tags`
- specific resource IDs, via `instanceIds` or equivalent resource identity fields
- bound resource for ACK/CS, via `bindResource` fields such as `clusterId`
- custom query scope, via `entityQueries` or `spl`

When asking for confirmation, show the resource type/addon, target region or regions, selected workspace if known, and the exact scope mode and values that will be placed in the policy or addon release body, including `bindResource` for ACK/CS policies. Do not infer a broad scope such as all resources from an omitted scope field.

### Workspace Selection Gate (Hard Requirement)

Before creating any integration policy or addon release, if the user did not explicitly provide a workspace name, you MUST:

1. Determine the target region from verified resource metadata.
2. Run `aliyun cms2 workspace list --region <targetRegion> -o json` and apply the pagination rules in [SKILL.md](../SKILL.md#pagination--query-failure-handling) before treating the workspace list as complete.
3. Present available workspace names to the user. If the list is long, present a concise candidate set but state that pagination was completed; include candidates most relevant to the target resource or default naming pattern first.
4. Wait for the user to explicitly choose one workspace.

If the user already provided a workspace name, still verify it exists in the target region before using it. You may stop pagination early only after an exact `workspaceName` match is found. If no exact match is found after complete pagination, report the mismatch and ask for the correct workspace name.

Do not create a policy using a default workspace unless the user explicitly chooses that exact workspace after seeing the candidate workspace list.

### ACK Workspace Confirmation (Hard Requirement)

Because an ACK/CS cluster can only be onboarded once (see [special case](#determining-onboarding--monitoring-status)), before `integration policy create` show these ACK-specific fields and wait for explicit user confirmation:

- cluster name
- cluster ID
- target account UID
- target region
- selected workspace
- addon name

**Special case**: The uniqueness constraint is scoped per account. After a cluster is onboarded under its owning account, a Resource Directory delegated administrator account can still onboard the same cluster under the administrator account. Cross-account duplicate onboarding is allowed.

### Policy Type Classification

The `policyType` field on integration policies has the following top-level categories: **Default**, **CS**, **ECS**, **Cloud**, **Client**, **Flink**. Types like RDS, SLB, etc. are sub-types under the **Cloud** category, declared individually by each addon. To discover available sub-types, check the `environments.*.policyType` field in `integration addon list` results.

### Policy Lookup Rules

- `--bind-resource-id` only applies to ACK/CS policies (`policy-type=CS`) and must be used with `--policy-type CS`.
- ECS and Cloud sub-types must be located through candidate policy lookup such as `--addon-name` or `--policy-type`, then verified by target addon release and release scope. Do not use `--bind-resource-id` for ECS or Cloud sub-types.

### Resource Identity Verification

Before creating or updating policy/release for concrete resource IDs, verify them with `entity query --source CloudResource` (see [SKILL.md](../SKILL.md) global conventions). For ACK/CS onboarding specifically: a 32-character hex string is only a format hint — confirm ACK/Kubernetes identity from the query result before policy creation.

### Cross-Account Onboarding

**Detection**:

1. Extract current userId from workspace name (format `default-cms-{userId}-{regionId}`), or ask the user
2. Run `entity query --source CloudResource` to verify the target instance and get its `user_id` column
3. `user_id` ≠ current userId → cross-account scenario

**Handling**:

1. Run `aliyun cms2 integration addon get --addon-name <name>`, check only the response path `addon.keywords`, that is, the `keywords` field inside the `addon` object, for `Feature:CrossAccount`
2. Supported → set `entityUserId` in the policy's entityGroup, continue onboarding
3. Not supported → **do not abort immediately**, execute fallback search:
    - `integration addon list` to find all addons with the same `entityType`
    - `integration addon get` each and check only `addon.keywords` for `Feature:CrossAccount`
    - Found → apply [Addon Selection Gate](#addon-selection-gate-hard-requirement); switch only after explicit user confirmation unless exactly one clear candidate matches the requested capability
    - None found → abort, prompt user to switch to the target account's credentials

### Addon Release Region Requirement (Hard Pre-Check)

**This is a mandatory pre-check before `integration addon-release create` or `addon-release update`.** It applies regardless of resource scope mode (all instances, resource group, tags, or individual IDs). You **must** execute this check and abort on violation — never skip it.

**Pre-check steps:**

1. Get the target policy (`integration policy get --policy-id <policyId>`) and determine its region from the explicit region field in the policy response; do not infer region from workspace name. Let this be `policyRegion`.
2. Run `aliyun cms2 integration addon get --addon-name <addonName> -o json` and check `addon.keywords`.
3. If `addon.keywords` contains `Feature:CrossRegion`, the release region may differ from the policy region — proceed.
4. If `addon.keywords` does **not** contain `Feature:CrossRegion`, enforce **all** of the following constraints:
    - The CLI `--region` parameter must equal `policyRegion`.
    - The request body `entityRules[].regionIds` (if present) must only contain `policyRegion`; specifying any other region is a cross-region violation.

**On violation — stop immediately and report to the user:**

> The workspace/policy is in `{policyRegion}`, but the target resources are in `{targetRegion}`. The addon `{addonName}` does not support cross-region integration (`Feature:CrossRegion` not found in addon keywords). You cannot integrate `{targetRegion}` resources through a `{policyRegion}` policy.

**Fallback**: search for a cross-region alternative before aborting — run `aliyun cms2 integration addon list` to find addons with the same `entityType`, then check each addon's `addon.keywords` for `Feature:CrossRegion`. If found, apply [Addon Selection Gate](#addon-selection-gate-hard-requirement) and switch only after explicit user confirmation unless exactly one clear candidate matches the requested capability; if none found, suggest the user use a workspace in `{targetRegion}`.

## Rules for Determining Addon Release Status

`integration addon-release get` / `integration addon-release list` responses include `conditions` for each AddonRelease. Evaluate status using the following rules (checked in order). For `addon-release list -o json`, do not read a top-level `.status` field as the release status; derive status from `conditions`.

| Status       | Condition Rule |
|--------------|---------------|
| Uninstalled  | `type=UnInstalled, status=True` |
| Uninstalling | `type=UnInstalled, status=Unknown` |
| Success      | `type=Ready, status=True` |
| Failed       | Any condition has `status=False` |
| Installing   | None of the above matched |

## Teardown

Read `aliyun cms2 integration policy delete --help` and `aliyun cms2 integration addon-release delete --help` before deleting in the current session to confirm the exact flags; policy deletion and addon-release deletion have different scopes.

Before running any delete command, follow the global write confirmation rule in [SKILL.md](../SKILL.md).

**Whole-resource teardown**: when the user asks to remove CloudMonitor onboarding for a resource and a single matching integration policy is identified, prefer deleting the integration policy:

```bash
aliyun cms2 integration policy delete --policy-id <policyId>
```

The CLI documents this operation as cascading to addon releases under the policy, so separate addon-release deletion is not required for whole-policy teardown.

**Single-addon teardown**: when the user asks to remove only one addon/capability under an existing policy, delete the target addon release instead of deleting the policy:

```bash
aliyun cms2 integration addon-release delete --policy-id <policyId> --release-name <releaseName>
```

or, for all releases of one addon under the policy when the user explicitly wants batch deletion:

```bash
aliyun cms2 integration addon-release delete --policy-id <policyId> --addon-name <addonName> --force
```

**Post-delete verification**:

1. For ACK/CS policy deletion, query `integration policy list --policy-type CS --bind-resource-id <clusterId>` as described in [Policy Lookup Rules](#policy-lookup-rules) and expect zero matching policies. For ECS or Cloud sub-types, re-run the same candidate-policy lookup used before deletion, then inspect remaining target addon releases and their scopes. Deletion is verified when no remaining healthy release covers the original target resource/scope; do not expect zero policies for the addon globally.
2. Cross-check with `integration policy get --policy-id <policyId>`; `The integration policy is not exist` is positive deletion evidence.
3. If checking releases under the deleted policy, `integration addon-release list --policy-id <policyId>` returning `Environment/Policy is not exist` is positive evidence that addon releases/environment were removed.
4. Treat deletion as eventually consistent: if the delete command succeeds but the first list query still returns the old policy, wait briefly and retry the list/get verification 2-3 times before reporting failure.
5. In the final answer, distinguish confirmed control-plane deletion from any possible cluster-side cleanup lag or residual collector resources.

## Grafana Dashboard Rules

> To be migrated to the grafana module skill once implemented.

**Before generating panels**, query metric metadata via `meta query --meta-format PROM_BASIC`:

- **metric type → PromQL**: `counter` → `rate()` / `increase()`; `gauge` → raw value or aggregation
- **dimensions → template variables**: label keys become Grafana variables (`$instance_id`, etc.) and `legendFormat`

**Alibaba Cloud dashboard rules**:

- Data source `uid` must use placeholder `"${DS_PROMETHEUS}"` — never hardcode
- Declare `DS_PROMETHEUS` in the top-level `__inputs`
- Prefer `$__rate_interval` over fixed ranges

```json
{
  "__inputs": [
    {"name": "DS_PROMETHEUS", "label": "Prometheus", "type": "datasource",
      "pluginId": "prometheus", "pluginName": "Prometheus"}
  ],
  "panels": [
    {"datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"}}
  ]
}
```
