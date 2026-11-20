# Dashboards

Configure charts, queries, controls and scheduled reports for Alibaba Cloud SLS.
The dashboard's destination Project/Region and its query sources are separate
settings. Chart `title` is a stable ID; `display.basicOptions.displayName` is the
visible title.

## Scenarios

| Request | Reference |
| --- | --- |
| Explain settings or review configuration | [Consult](workflows/consult.md) |
| Create a dashboard | [Create](workflows/create.md) |
| Edit charts and controls | [Edit](workflows/edit.md) |
| Read, save or delete a dashboard | [Dashboard operations](workflows/publish.md) |
| Manage scheduled reports | [Subscriptions](integrations/subscriptions.md) |
| Investigate data or display issues | [Diagnose](workflows/diagnose.md) |

## Tools

The CLI handles cloud operations. Scripts in `scripts/dashboard/` provide local Plan
construction, validation, diff and chart merging. A [Plan](model/plan.md) is an optional
input format for creating standard grid dashboards. Edit existing dashboards in
Dashboard JSON.

## Related documents

| Topic | Reference |
| --- | --- |
| Configuration fields and chart examples | [Reference index](index.md), [examples](charts/examples.md) |
| Sources and query fields | [Datasource modes](datasources/overview.md) |
| Local validation and update comparisons | [Validation tools](validation/checks.md) |
| CLI request fields and APIs | [Commands and APIs](related-apis.md) |
| Caller permissions | [RAM permissions](ram-policies.md) |
| Command or environment issues | [Common troubleshooting](../troubleshooting.md) |
| Tool, configuration or subscription issues | [Dashboard troubleshooting](troubleshooting.md) |
