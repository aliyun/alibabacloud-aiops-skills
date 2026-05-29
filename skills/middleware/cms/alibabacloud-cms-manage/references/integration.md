# Integration Module

## Core Concepts

```
Addon Catalog  →  Integration Policy  →  Addon Release
```

## Onboarding Workflow

### Prerequisites

- **workspace name**: default format `default-cms-{userId}-{regionId}`, used for policy creation and cross-account userId extraction
- **region**: target region (e.g. `cn-hangzhou`)
- **resource ID**: required for instance-scoped onboarding; verify before creating policy/release
- **cluster ID**: required for container scenarios; ID shape alone does not prove ACK/CS identity

### Standard Onboarding

```bash
# 1. Discover addon (output includes full workflow + body template)
aliyun cms2 integration addon list -o text
aliyun cms2 integration addon --addon-name <addon-name>

# 2. For concrete resource IDs, run Resource Identity Verification below

# 3-5. Follow the Workflow section in addon output:
#   create policy → create release → verify
```

### Choosing an Onboarding Method

| Scenario | Recommended Addon | Notes |
|----------|------------------|-------|
| Batch onboarding for multiple cloud services | `cloud-batch-metrics` | Configure multiple products at once |
| Single service or custom scope | Product-specific addon | Discover via `integration addon list` |

## Key Business Constraints

### Resource Identity Verification

Before creating or updating policy/release for concrete resource IDs, verify them with `entity query --source CloudResource` (see [SKILL.md](../SKILL.md) global conventions). For ACK/CS onboarding specifically: a 32-character hex string is only a format hint — confirm ACK/Kubernetes identity from the query result before policy creation.

### Cross-Account Onboarding

**Detection**:

1. Extract current userId from workspace name (format `default-cms-{userId}-{regionId}`), or ask the user
2. Run `entity query --source CloudResource` to verify the target instance and get its `user_id` column
3. `user_id` ≠ current userId → cross-account scenario

**Handling**:

1. Run `aliyun cms2 integration addon get --addon-name <name>`, check if `keywords` contains `Feature:CrossAccount`
2. Supported → set `entityUserId` in the policy's entityGroup, continue onboarding
3. Not supported → **do not abort immediately**, execute fallback search:
   - `integration addon list` to find all addons with the same `entityType`
   - `integration addon get` each to check for `Feature:CrossAccount`
   - Found → switch to that addon and continue
   - None found → abort, prompt user to switch to the target account's credentials

### Scope Mode Skips Region Validation

Scope modes (all instances, resource group, tags) auto-resolve regions — no manual validation needed.
Region validation in the onboarding flow **only applies** when specifying individual instance IDs or names.

## Teardown

**Order**: delete addon release first → then delete policy (reverse of creation order).

## Metadata Query Mapping

| What You Need | How to Get It |
|--------------|---------------|
| **Resource metadata** (entityType, supported scopes, etc.) | Infer from instance properties via `entity query --source CloudResource` |
| **Resource instance details** (ID, region, tags, etc.) | `entity query --source CloudResource` directly |
| **Metric metadata** (name, type, dimensions) | `meta query`; verify with `metric promql labels` / `label-values` / `series` |
| **Prometheus instance by policy** | `aliyun cms2 integration storage list --policy-id <policy-id> --storage-type Prometheus` |

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
