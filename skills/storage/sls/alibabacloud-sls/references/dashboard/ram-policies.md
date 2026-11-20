# RAM permissions for SLS dashboards

These permissions apply to the caller performing cloud operations. The required actions
depend on the operations selected for the task. Dashboard
permissions do not grant access to the data shown in its charts.

For CLI command names and arguments, see [commands and related APIs](related-apis.md).

## Required permissions

API names and RAM actions are not always identical. The resource scopes below
follow the [SLS authorization catalog](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-ram).

| API | RAM action | Resource |
| --- | --- | --- |
| GetProject | `log:GetProject` | Project ARN |
| ListDashboard | `log:ListDashboard` | Dashboard ARN with `dashboard/*` |
| GetDashboard | `log:GetDashboard` | Dashboard ARN |
| CreateDashboard | `log:CreateDashboard` | `*` |
| UpdateDashboard | `log:UpdateDashboard` | Dashboard ARN |
| DeleteDashboard | `log:DeleteDashboard` | `*` |
| ListLogStores | `log:ListLogStores` | Logstore ARN with `logstore/*` |
| GetLogStore | `log:GetLogStore` | Logstore ARN |
| GetIndex | `log:GetIndex` | Logstore ARN |
| GetLogsV2 | `log:GetLogStoreLogs` | Logstore ARN for a physical store |
| ListMetricStores | `log:ListMetricStores` | Metricstore ARN with `metricstore/*` |
| GetMetricStore | `log:GetMetricStore` | Metricstore ARN |
| ListStoreViews | `log:ListStoreViews` | `*` |
| GetStoreView | `log:GetStoreView` | `*` |
| GetStoreViewIndex | `log:GetStoreViewIndex` | `*` |

Replace placeholders in these ARN forms:

- Project: `acs:log:<region-id>:<account-id>:project/<project-name>`.
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

Use the [subscription authorization guidance](https://help.aliyun.com/zh/sls/authorized-ram-user-operation-alarm)
for the requested operation. Subscription permissions use Project Job resources;
viewing the dashboard alone does not grant permission to schedule delivery.
Subscription management and datasource reads require their respective permissions.

## System policies

| Policy | Scope |
| --- | --- |
| `AliyunLogReadOnlyAccess` | Read-only access across SLS resources |
| `AliyunLogFullAccess` | Full SLS access, including operations beyond dashboards |

These are broader alternatives, not defaults for dashboard operations.

## Permission errors

On an authorization failure, report the failed operation, denied action and resource,
and request ID when available. An access failure does not mean the resource is absent.
Do not switch profiles or broaden permissions unless the user requests that change.
Follow the [credential safety rules](../../SKILL.md#safety-rules).
