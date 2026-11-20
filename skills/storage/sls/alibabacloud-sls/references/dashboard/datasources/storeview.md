# StoreView

A named StoreView identifies a set of log or metric sources by Project, region,
name and type.

Use `aliyun sls query --logstore VIEW_NAME` for log and Metric StoreView queries.
Keep the View's own Project, region and name.

## Discovery and queries

- Use `aliyun sls store-view list` and `store-view get` to inspect existing views.
- Log view index discovery reads `indexes[]` and `storeViewErrors[]`,
  preserving member source/field differences without inferring uniform indexing;
  see [index inspection](../../index/manage-index-config.md#read-an-index).
- Use the view name for discovery sampling and query verification.
  Preserve the saved Dashboard datasource type and View coordinates.

Use the [Logstore query example](logstore.md) with `--logstore VIEW_NAME` and the
view's Project. For a log view, use a log query; for a metric view, use metric SQL
such as `* | select promql_query('up') from metrics limit 100`. SQL row limits belong
in SQL; raw search uses line/offset parameters.
Querying member stores separately changes the scope and may omit view filters.
Further command details are in [StoreView queries](../../query/query-execution.md#storeview).

Member index errors and differing field types can affect query and filter behavior.
A query with selected control values can show their effect on the view.

## MetricsQL StoreView entries

`metricsql_storeview` is a SQL-mode identifier found in saved Dashboard JSON.
Its `project`, `logstore` and `region` locate the view; `logstore` is the view name,
not a member Metricstore. A non-empty `tokenQuery` takes precedence over `query`.
The SQL text determines returned columns, limits and any embedded PromQL step;
query-level `interval` and `limit` do not replace those SQL settings.

For PromQL in a new Plan, use `metricstore_storeview`. Edit saved
`metricsql_storeview` entries directly in Dashboard JSON, preserving their identity.

Official sources:
- [Overview](https://help.aliyun.com/zh/sls/dataset-storeview-overview)
- [Log views](https://help.aliyun.com/zh/sls/cross-logstore-query-and-analysis)
- [Metric views](https://help.aliyun.com/zh/sls/cross-metricstore-query)
