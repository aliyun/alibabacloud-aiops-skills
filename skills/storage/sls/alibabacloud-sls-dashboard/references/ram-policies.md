# RAM permissions for SLS dashboards

These permissions apply to the CLI or script caller. Grant only the actions needed
for the requested task, including its preflight reads and readback. Dashboard
permissions do not grant access to the data shown in its charts.

## Required permissions

API names and RAM actions are not always identical. The resource scopes below
follow the [SLS authorization catalog](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-ram).

| API | CLI Command | RAM Action | Resource Permission |
| --- | --- | --- | --- |
| ListDashboard | `list-dashboard` | `log:ListDashboard` | Dashboard ARN with `dashboard/*` |
| GetDashboard | `get-dashboard` | `log:GetDashboard` | Dashboard ARN |
| CreateDashboard | `create-dashboard` | `log:CreateDashboard` | `*` |
| UpdateDashboard | `update-dashboard` | `log:UpdateDashboard` | Dashboard ARN |
| DeleteDashboard | `delete-dashboard` | `log:DeleteDashboard` | `*` |
| ListLogStores | `list-log-stores` | `log:ListLogStores` | Logstore ARN with `logstore/*` |
| GetLogStore | `get-log-store` | `log:GetLogStore` | Logstore ARN |
| GetIndex | `get-index` | `log:GetIndex` | Logstore ARN |
| GetLogsV2 | `get-logs-v2` | `log:GetLogStoreLogs` | Logstore ARN for a physical store |
| ListMetricStores | `list-metric-stores` | `log:ListMetricStores` | Metricstore ARN with `metricstore/*` |
| GetMetricStore | `get-metric-store` | `log:GetMetricStore` | Metricstore ARN |
| ListStoreViews | `list-store-views` | `log:ListStoreViews` | `*` |
| GetStoreView | `get-store-view` | `log:GetStoreView` | `*` |
| GetStoreViewIndex | `get-store-view-index` | `log:GetStoreViewIndex` | `*` |

Replace placeholders in these ARN forms:

- Dashboard: `acs:log:<region-id>:<account-id>:project/<project-name>/dashboard/<dashboard-name>`.
- Logstore: `acs:log:<region-id>:<account-id>:project/<project-name>/logstore/<store-name>`.
- Metricstore metadata: `acs:log:<region-id>:<account-id>:project/<project-name>/metricstore/<store-name>`.
- Job: `acs:log:<region-id>:<account-id>:project/<project-name>/job/<job-name>`.

Actions documented with `Resource: "*"` are not restricted to the command's
`--project`. Do not present them as Project-scoped permissions. GetLogsV2 query
authorization uses `log:GetLogStoreLogs`, not `log:GetLogsV2`; see its
[API reference](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getlogsv2).

## Minimum dashboard read policy

For listing and inspecting dashboards in one Project:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["log:ListDashboard", "log:GetDashboard"],
      "Resource": "acs:log:<region-id>:<account-id>:project/<project-name>/dashboard/*"
    }
  ]
}
```

For a known dashboard, omit ListDashboard and replace `dashboard/*` with its exact
name. For updates, add `log:UpdateDashboard` to that dashboard's resource scope.

## Optional dashboard creation and deletion

Add only the requested write action. Creation and deletion use `Resource: "*"`
in the authorization catalog. For creation:

```json
{
  "Version": "1",
  "Statement": [
    {"Effect": "Allow", "Action": ["log:CreateDashboard"], "Resource": "*"}
  ]
}
```

Deletion requires `log:DeleteDashboard` instead. Keep the read permissions above
for preflight and verification; do not add deletion merely to support updates.

## Optional source discovery and queries

For index inspection and query verification on a physical store:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["log:GetIndex", "log:GetLogStoreLogs"],
      "Resource": "acs:log:<region-id>:<account-id>:project/<source-project>/logstore/<store-name>"
    }
  ]
}
```

Omit GetIndex for metric queries. SQL and SQL calls to `promql_query` or
`promql_query_range` through GetLogsV2 use the query permission above. Add discovery
and metadata actions from the table only when needed; Metricstore metadata has its
own ARN form.

Source Projects can differ from the dashboard's Project. StoreView metadata/index
permissions alone do not establish query access to the view and its sources. For
view queries, use the documented access requirements and the denied action
and resource rather than assuming a physical-store ARN applies:
[log StoreViews](https://help.aliyun.com/zh/sls/cross-logstore-query-and-analysis),
[metric StoreViews](https://help.aliyun.com/zh/sls/cross-metricstore-query).

## Optional report subscription permissions

Subscriptions are Report Jobs. The
[Job authorization guidance](https://help.aliyun.com/zh/sls/authorized-ram-user-operation-alarm)
documents `log:ListJobs` and `log:GetJob` on Project Job resources. For listing
subscriptions, use:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["log:ListJobs"],
      "Resource": "acs:log:<region-id>:<account-id>:project/<project-name>/job/*"
    }
  ]
}
```

For Job management, that guide provides `log:*` on the Project's `job/*` resources.
This is a broader Job-management grant, not a Report-only or minimum-action policy;
it can cover other jobs in the Project. Have the permission owner select a
policy for the requested report operations. Do not infer RAM
write actions solely from the API names CreateJob/UpdateJob/DeleteJob.

Subscription changes also read the dashboard and, when applicable, StoreView
metadata. Include those reads from the table. See
[subscriptions](integrations/subscriptions.md) for delivery limitations.

## System policies

| Policy Name | Scope |
| --- | --- |
| `AliyunLogReadOnlyAccess` | Read-only access across SLS resources |
| `AliyunLogFullAccess` | Full SLS access, including operations beyond dashboards |

These are broader alternatives, not defaults for this skill.

## Permission errors

On an authorization failure, report the operation, denied action/resource and
request ID when available. An access failure does not mean the resource is absent.
Do not change profiles or broaden RAM policies unless the user requests it. Keep
credentials out of diagnostic output; use the configured authentication.
