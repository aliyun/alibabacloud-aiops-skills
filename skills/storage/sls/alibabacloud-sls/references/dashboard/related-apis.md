# CLI commands and related APIs

Use the [Dashboard object model](model/dashboard.md) and chart references for JSON semantics.

## Commands

Use [dashboard reads and writes](workflows/publish.md) and the [source guides](index.md#data-and-interaction).
For service errors or request fields, see the official [read](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getdashboard)
and [update](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-updatedashboard) references.

## Subscription operations

See the [subscription workflow](integrations/subscriptions.md) and
[configuration fields](model/subscription.md).

## Dashboard parameters

`dashboardName` identifies the dashboard in JSON; create, get, update and delete use
`--dashboard`. Update replaces configuration: include
the content to preserve. [Editing tools](workflows/edit.md) can help compare or combine
configuration; [Dashboard operations](workflows/publish.md) describe file input and request fields.
