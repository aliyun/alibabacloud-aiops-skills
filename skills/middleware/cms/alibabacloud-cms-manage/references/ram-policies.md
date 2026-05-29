# RAM Policy Reference

> Per-module list of required RAM Actions (API granularity, **no `*` wildcard**),
> derived from the OpenAPI calls actually issued by `aliyun cms2`.
> Four cloud services are involved: CMS (CloudMonitor 2024-03-30 / 2019-01-01),
> Tag (2018-08-28), ResourceCenter (2022-12-01), ResourceManager
> (2020-03-31, RAM prefix is `ram:`).
> The `Resource` field follows the principle of least privilege: control-plane
> calls should be bound to a concrete workspace / instance / policy ARN;
> data-plane queries (list / describe) typically require
> `acs:cms:*:<accountId>:*` to enumerate.

## Modules Excluded from This Document (do not re-add)

The following modules are **intentionally excluded**. When rescanning the source
for refreshes, **do not** re-add them to this document.
Common reason: **they do not consume any OpenAPI RAM Action** — either pure
local commands (no OpenAPI call), or calls to non-CMS APIs whose authorization
is managed by the user on the target product side (out of CMS Skill scope).

| Module | Reason for exclusion |
|--------|----------------------|
| `migrate dump` / `migrate push` | Pure local TSDB read + Prometheus Remote Write; uses the instance's bearer token; consumes no RAM Action |
| `event-hub list` / `event-hub get` | SLS GetLogs API; uses SLS credentials; consumes no CMS RAM Action |
| `configure` | Local credential configuration; no OpenAPI call |
| `commands` | Local static command discovery; no OpenAPI call |
| `update-beta` | Beta self-update; does not consume CMS OpenAPI RAM Actions |

> Maintenance note: if a future script/agent rescans the source to refresh
> this file, preserve this section and skip the modules above. Do not
> re-generate sections just because keywords like `tag.aliyuncs.com` /
> `RemoteWrite` / `sls.aliyuncs.com` appear in the code.

## Generic Policy Template (trim Resource as needed)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [ "cms:ListPrometheusInstances" ],
      "Resource": "acs:cms:*:<accountId>:*"
    }
  ]
}
```

---

## 1. `metric basic` Module (CloudMonitor 2019-01-01 data plane)

Source: `pkg/client/cms_basic_options.go`, `pkg/app/cmsbasic/service.go`.
Forwarded through the `cms-20240330` client's `CallApi` with `Version=2019-01-01`.

| CLI subcommand | RAM Action |
|----------------|------------|
| `metric basic points` | `cms:DescribeMetricList` |
| `metric basic latest` | `cms:DescribeMetricLast` |
| `metric basic range`  | `cms:DescribeMetricData` |
| `metric basic top`    | `cms:DescribeMetricTop`  |
| `metric basic export` | `cms:BatchExport`        |
| `metric basic cursor` | `cms:Cursor`             |

---

## 2. `meta` Module (CMS 2024-03-30)

Source: `pkg/command/metricmeta/metric_meta.go`.

| CLI subcommand | RAM Action |
|----------------|------------|
| `meta metrics`    | `cms:DescribeMetricMetaList` |
| `meta namespaces` | `cms:DescribeProductMeta`    |

---

## 3. `prometheus instance` Module (CMS 2024-03-30)

Source: `pkg/app/prometheus/prometheus_instance_service.go`.

| CLI subcommand | RAM Action |
|----------------|------------|
| `prometheus instance create` | `cms:CreatePrometheusInstance` |
| `prometheus instance get`    | `cms:GetPrometheusInstance`    |
| `prometheus instance update` | `cms:UpdatePrometheusInstance` |
| `prometheus instance delete` | `cms:DeletePrometheusInstance` |
| `prometheus instance list`   | `cms:ListPrometheusInstances`  |

---

## 4. `prometheus view` Module (CMS 2024-03-30)

Source: `pkg/app/prometheus/prometheus_view_service.go`.

| CLI subcommand | RAM Action |
|----------------|------------|
| `prometheus view create` | `cms:CreatePrometheusView` |
| `prometheus view get`    | `cms:GetPrometheusView`    |
| `prometheus view update` | `cms:UpdatePrometheusView` |
| `prometheus view delete` | `cms:DeletePrometheusView` |
| `prometheus view list`   | `cms:ListPrometheusViews`  |

---

## 5. `metric promql` Module (Prometheus data-plane HTTP)

Source: `pkg/client/promql_http.go`, `pkg/app/prometheus/promql_service.go`.

The data-plane endpoints `/api/v1/query`, `/api/v1/query_range`, `/api/v1/labels`,
`/api/v1/label/<name>/values`, `/api/v1/series` are authorized by the instance's
own bearer token (or SLS MetricStore BasicAuth) and **do not consume RAM Actions**.

Only the prerequisite step requires a RAM permission to obtain the instance
endpoint / authToken:

| Prerequisite call | RAM Action |
|-------------------|------------|
| Resolve instance endpoint / authToken | `cms:GetPrometheusInstance` |

---

## 6. `prometheus recording-rule` Module (CMS 2024-03-30)

Source: `pkg/app/recordingrule/service.go`. The underlying SDK request is named
`AggTaskGroup`; the corresponding RAM Actions are `cms:RecordingRule*`.

| CLI subcommand | RAM Action |
|----------------|------------|
| `prometheus recording-rule create` | `cms:CreateRecordingRule`        |
| `prometheus recording-rule get`    | `cms:GetRecordingRule`           |
| `prometheus recording-rule update` | `cms:UpdateRecordingRule`        |
| `prometheus recording-rule start`  | `cms:UpdateRecordingRuleStatus`  |
| `prometheus recording-rule stop`   | `cms:UpdateRecordingRuleStatus`  |
| `prometheus recording-rule delete` | `cms:DeleteRecordingRule`        |
| `prometheus recording-rule list`   | `cms:ListRecordingRules`         |

---

## 7. `alert` Module (CMS 2024-03-30)

Source: `pkg/command/alert/*.go`, `pkg/command/notificationchannel/*.go`,
`pkg/command/alerthistory/*.go`, `pkg/command/alerttemplate/*.go`.

### 7.1 Alert Rules (`alert rule`)

| CLI subcommand | RAM Action |
|----------------|------------|
| `alert rule create`  | `cms:ManageAlertRules`  |
| `alert rule get`     | `cms:QueryAlertRules`   |
| `alert rule update`  | `cms:ManageAlertRules`  |
| `alert rule patch`   | `cms:ManageAlertRules` (default) or `cms:PatchAlertRule` (`--use-patch-api`) |
| `alert rule delete`  | `cms:ManageAlertRules`  |
| `alert rule list`    | `cms:QueryAlertRules`   |
| `alert rule enable`  | `cms:EnableAlertRules`  |
| `alert rule disable` | `cms:DisableAlertRules` |

### 7.2 Notification Channels (top-level command)

| CLI subcommand | RAM Action |
|----------------|------------|
| `notification-channel contact list` | `cms:ListContacts`      |
| `notification-channel robot list`   | `cms:ListAlertRobots`   |
| `notification-channel webhook list` | `cms:ListAlertWebhooks` |

### 7.3 Alert Rule Templates (`alert template`)

> The five backing APIs are visibility=Private POP endpoints, reachable via
> the standard CMS gateway.

| CLI subcommand | RAM Action |
|----------------|------------|
| `alert template list`   | `cms:ListAlertRuleTemplate`   |
| `alert template get`    | `cms:GetAlertRuleTemplate`    |
| `alert template create` | `cms:CreateAlertRuleTemplate` |
| `alert template update` | `cms:UpdateAlertRuleTemplate` |
| `alert template delete` | `cms:DeleteAlertRuleTemplate` |
| `alert template apply`  | `cms:GetAlertRuleTemplate` + `cms:ManageAlertRules` |

### 7.4 Alert History

| CLI subcommand | RAM Action |
|----------------|------------|
| `alert history list` | `cms:ListAlertHistories` |

---

## 8. `integration` Module (CMS 2024-03-30)

Source: `pkg/app/integration/policy_service.go`, `addon_service.go`,
`addon_release_service.go`.

### 8.1 IntegrationPolicy

| CLI subcommand | RAM Action |
|----------------|------------|
| `integration policy create`       | `cms:CreateIntegrationPolicy` |
| `integration policy get`          | `cms:GetIntegrationPolicy`    |
| `integration policy update`       | `cms:UpdateIntegrationPolicy` |
| `integration policy delete`       | `cms:DeleteIntegrationPolicy` |
| `integration policy list`         | `cms:ListIntegrationPolicies` |

### 8.1b Integration Sub-resources (read-only)

| CLI subcommand | RAM Action |
|----------------|------------|
| `integration storage list`         | `cms:ListIntegrationPolicyStorageRequirements`     |
| `integration dashboard list`       | `cms:ListIntegrationPolicyDashboards`              |
| `integration resource list`        | `cms:ListIntegrationPolicyResources`               |
| `integration job-target list`      | `cms:ListIntegrationPolicyCollectorJobTargets`     |
| `integration service-monitor list` | `cms:ListIntegrationPolicyServiceMonitors`         |
| `integration pod-monitor list`     | `cms:ListIntegrationPolicyPodMonitors`             |
| `integration custom-job list`      | `cms:ListIntegrationPolicyCustomScrapeJobRules`    |

### 8.2 AddonRelease

| CLI subcommand | RAM Action |
|----------------|------------|
| `integration addon-release create` | `cms:CreateAddonRelease` |
| `integration addon-release get`    | `cms:GetAddonRelease`    |
| `integration addon-release list`   | `cms:ListAddonReleases`  |
| `integration addon-release update` | `cms:UpdateAddonRelease` |
| `integration addon-release delete` | `cms:DeleteAddonRelease` |

### 8.3 Addon Metadata (read-only catalog)

| CLI subcommand | RAM Action |
|----------------|------------|
| `integration addon list` | `cms:ListAddons`                                          |
| `integration addon get`  | `cms:GetAddon` + `cms:GetAddonSchema` + `cms:GetAddonCodeTemplate` |

---

## 9. `workspace` Module (CMS 2024-03-30)

Source: `pkg/app/workspace/service.go`, `pkg/command/workspace/workspace_ctl.go`.

| CLI subcommand | RAM Action |
|----------------|------------|
| `workspace create` | `cms:GetCloudResource` + `cms:CreateCloudResource` + `cms:PutWorkspace` + `cms:GetUModel` + `cms:CreateUModel` + `cms:GetEntityStore` + `cms:CreateEntityStore` |
| `workspace get`    | `cms:GetWorkspace`    |
| `workspace list`   | `cms:ListWorkspaces`  |
| `workspace update` | `cms:PutWorkspace`    |
| `workspace delete` | `cms:DeleteWorkspace` |

> `workspace create` first checks and initializes the CloudResource
> (`GetCloudResource` → `CreateCloudResource`), then creates the Workspace
> (`PutWorkspace`), and finally initializes the UModel
> (`GetUModel` → `CreateUModel`) and EntityStore
> (`GetEntityStore` → `CreateEntityStore`). Pre-existing resources
> (`CloudResourceAlreadyExists`, `UModelAlreadyExist`,
> `EntityStoreAlreadyExists`) are treated as success.

---

## 10. `entity query` Module (CMS 2024-03-30)

Source: `pkg/command/entity/query.go`, `pkg/app/cloudresource/service.go`,
`pkg/app/entitystore/service.go`.

Use `--source` to choose the data source:

| CLI subcommand | RAM Action |
|----------------|------------|
| `entity query --source=CloudResource` | `cms:GetCloudResource` + `cms:GetCloudResourceData` |
| `entity query --source=EntityStore`   | `cms:GetEntityStoreData`   |

---

## 11. `apm` / `rum` Modules (CMS 2024-03-30)

Source: `pkg/app/service/service.go`, `pkg/app/serviceobservability/service.go`.
APM and RUM share the Service / ServiceObservability APIs and are distinguished
by `obsType`.

### 11.1 Application Service (`apm service` / `rum service`)

| CLI subcommand | RAM Action |
|----------------|------------|
| `apm service create` / `rum service create` | `cms:CreateService` |
| `apm service get` / `rum service get`       | `cms:GetService`    |
| `apm service update` / `rum service update` | `cms:UpdateService` |
| `apm service delete` / `rum service delete` | `cms:DeleteService` |
| `apm service list` / `rum service list`     | `cms:ListServices`  |

### 11.2 Service Configuration (`apm configuration` / `rum configuration`)

| CLI subcommand | RAM Action |
|----------------|------------|
| `apm configuration get` / `rum configuration get`       | `cms:GetServiceObservability`    |
| `apm configuration create` / `rum configuration create` | `cms:CreateServiceObservability` |

---

## 12. `tag` Module (Tag 2018-08-28)

Source: `pkg/command/tag/tag.go`.

| CLI subcommand | RAM Action |
|----------------|------------|
| `tag bind`   | `tag:TagResources`      |
| `tag unbind`  | `tag:UntagResources`    |
| `tag list`   | `tag:ListTagResources`  |

---

## 13. `resource-group` Module (ResourceManager 2020-03-31)

Source: `pkg/command/resourcegroup/resource_group.go`.

| CLI subcommand | RAM Action |
|----------------|------------|
| `resource-group list` | `ram:ListResourceGroups` |

> ResourceManager's RAM authorization prefix is `ram:` (not `resourcemanager:`).

---

## 14. Cross-Account Proxy

Source: `pkg/client/proxy.go`. Any subcommand invoked with `--member-account-id`
is forwarded through the master account's `ProxyApiForMemberAccount`, so the
following additional RAM Action is required:

| Call | RAM Action |
|------|------------|
| `*` any subcommand with `--member-account-id` | `cms:ProxyApiForMemberAccount` |

The proxied target API (cms / tag / resourcemanager) must also be authorized
in the member account's RAM role for the corresponding Action (see the
per-module sections above).

---

## Minimal Authorization Examples

### Read-only Observability / Diagnostics (SRE)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cms:DescribeMetricList",
        "cms:DescribeMetricLast",
        "cms:DescribeMetricData",
        "cms:DescribeMetricTop",
        "cms:Cursor",
        "cms:BatchExport",
        "cms:DescribeMetricMetaList",
        "cms:DescribeProductMeta",
        "cms:GetPrometheusInstance",
        "cms:ListPrometheusInstances",
        "cms:GetPrometheusView",
        "cms:ListPrometheusViews",
        "cms:GetRecordingRule",
        "cms:ListRecordingRules",
        "cms:QueryAlertRules",
        "cms:ListContacts",
        "cms:ListAlertRobots",
        "cms:ListAlertWebhooks",
        "cms:ListAlertHistories",
        "cms:ListAlertRuleTemplate",
        "cms:GetAlertRuleTemplate",
        "cms:GetIntegrationPolicy",
        "cms:ListIntegrationPolicies",
        "cms:ListIntegrationPolicyResources",
        "cms:ListIntegrationPolicyDashboards",
        "cms:ListIntegrationPolicyCollectorJobTargets",
        "cms:ListIntegrationPolicyServiceMonitors",
        "cms:ListIntegrationPolicyPodMonitors",
        "cms:ListIntegrationPolicyCustomScrapeJobRules",
        "cms:ListIntegrationPolicyStorageRequirements",
        "cms:GetAddonRelease",
        "cms:ListAddonReleases",
        "cms:ListAddons",
        "cms:GetAddon",
        "cms:GetAddonSchema",
        "cms:GetAddonCodeTemplate",
        "cms:GetWorkspace",
        "cms:ListWorkspaces",
        "cms:GetCloudResource",
        "cms:GetCloudResourceData",
        "cms:GetEntityStoreData",
        "cms:GetService",
        "cms:ListServices",
        "cms:GetServiceObservability"
      ],
      "Resource": "acs:cms:*:<accountId>:*"
    }
  ]
}
```

### Onboarding / Mutation (Integration Engineer)

Append to the read-only policy:

```json
{
  "Effect": "Allow",
  "Action": [
    "cms:CreateIntegrationPolicy",
    "cms:UpdateIntegrationPolicy",
    "cms:DeleteIntegrationPolicy",
    "cms:CreateAddonRelease",
    "cms:UpdateAddonRelease",
    "cms:DeleteAddonRelease",
    "cms:CreatePrometheusInstance",
    "cms:UpdatePrometheusInstance",
    "cms:DeletePrometheusInstance",
    "cms:CreatePrometheusView",
    "cms:UpdatePrometheusView",
    "cms:DeletePrometheusView",
    "cms:CreateRecordingRule",
    "cms:UpdateRecordingRule",
    "cms:UpdateRecordingRuleStatus",
    "cms:DeleteRecordingRule",
    "cms:ManageAlertRules",
    "cms:PatchAlertRule",
    "cms:EnableAlertRules",
    "cms:DisableAlertRules",
    "cms:CreateAlertRuleTemplate",
    "cms:UpdateAlertRuleTemplate",
    "cms:DeleteAlertRuleTemplate",
    "cms:PutWorkspace",
    "cms:DeleteWorkspace",
    "cms:GetCloudResource",
    "cms:CreateCloudResource",
    "cms:GetUModel",
    "cms:CreateUModel",
    "cms:GetEntityStore",
    "cms:CreateEntityStore",
    "cms:CreateService",
    "cms:UpdateService",
    "cms:DeleteService",
    "cms:CreateServiceObservability"
  ],
  "Resource": "acs:cms:*:<accountId>:*"
}
```

### Cross-Account Proxy (master account uses `--member-account-id`)

```json
{
  "Effect": "Allow",
  "Action": [ "cms:ProxyApiForMemberAccount" ],
  "Resource": "acs:cms:*:<masterAccountId>:*"
}
```

### Tag Management (for `tag` subcommands)

```json
{
  "Effect": "Allow",
  "Action": [
    "tag:TagResources",
    "tag:UntagResources",
    "tag:ListTagResources"
  ],
  "Resource": "*"
}
```

### Resource Group Lookup (for `resource-group` subcommands)

```json
{
  "Effect": "Allow",
  "Action": [
    "ram:ListResourceGroups"
  ],
  "Resource": "*"
}
```
