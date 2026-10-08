# Dashboard object model

A dashboard has `displayName`, `description`, `attribute.type` (`grid`/`free`) and
`charts[]`. For new dashboards, explicitly set the recommended layout `grid`; use
`free` only when a custom layout is needed. Existing empty layout settings are
validated as `free` with a warning. See [layout](../features/layout.md).
`dashboardName` identifies it remotely. A chart's `title` is its stable
ID; `display.basicOptions.displayName` is its visible title.
For Plan input fields, see [name mapping](plan.md#name-mapping).

Use lowercase stable IDs for new charts, such as `request-trend`; preserve existing
IDs during edits. Visible titles may use normal capitalization. Keep `type` spelling
exactly as listed in [chart types](../charts/charts.md), including `facetPro` and `imagePro`.

New chart examples use `display.version=2`, the chart configuration marker.

`display` contains layout, field bindings, styles, local variables and actions.
`search` contains queries, time settings and transformations. A query's `name` is
its unique binding key within the chart; `displayName` is a label. Preserve
`query` and `tokenQuery` during unrelated edits.

SLS query coordinates are project, logstore (also used for Metricstore/view names) and
region. The datasource type determines the query mode; SQL limits and grouping belong in
SQL.

Current filter, token, and time selections need not change saved JSON. Publishing a dashboard
does not grant access to its source projects. Destination coordinates do not replace
each chart's source coordinates. See [results](result-shapes.md), [variables](../features/variables.md)
and [time](../queries/time-and-limits.md).

## Query container

Parameters belong to `chart.search`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `chartQueries` | object[] | Yes for data charts and imagePro | None | Queries in order; use an array even for one query. For imagePro, include [builtin data](../charts/imagepro.md#examples) so the image displays. |
| `dataSourceType` | string | No | — | current or mixed; mixed allows explicit resources per query and dynamic candidate queries. |
| `transformers` | object[] | No | [] | Ordered result transformations; each receives the preceding output. |

Use `chartQueries` and `transformers` for new configuration. Preserve legacy
configuration during unrelated edits; do not generate `subSearch`, `tokenQueryMap`,
or `transformations` as substitutes.

## Query parameters

Parameters belong to each `chart.search.chartQueries[]` entry.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `name` | string | Yes | None | Unique query ID within the chart; used by bindings and actions. |
| `displayName` | string | No | name | Query label. |
| `datasource` | string | Yes | None | Datasource mode; see [datasource modes](../datasources/overview.md), including [builtin simulated data](../datasources/builtin.md). |
| `project` | string | Yes for SLS queries | None | Source project, independent of the dashboard destination. |
| `logstore` | string | Yes for SLS queries | None | Source Logstore, Metricstore, or StoreView name. |
| `region` | string | For resource location | — | Source region. |
| `query / tokenQuery` | string | Yes for SLS queries | None | SLS query text; a non-empty tokenQuery takes precedence over query. Builtin needs no query text. |
| `hide` | boolean | No | false | Exclude the query from normal chart requests. |
| `queryType` | string | For Metricstore PromQL | — | range for series; instant for a point-in-time result. |
| `interval` | string or number | For explicit range step | Automatic | For metricstore, sets the bare range PromQL step, not the step in SQL containing promql_query/promql_query_range; unused for instant queries. Preserve the source mode's supported representation. |
| `limit` | number | No | 10000 for Metricstore PromQL | Metricstore result row count across series and samples, not series count or maxDataPoints; SQL row limits belong in SQL. |
| `format` | string | No | — | time_series for series; table for labels and values as columns. |
| `legendFormat` | string | No | Series labels, prefixed by metric name when present | For Metricstore, sets the displayed series name, such as {{service}}; absent labels become empty strings. Field names and query IDs stay unchanged. For prometheus, see its [query fields](../queries/promql.md#prometheus-datasource). |

See [datasource modes](../datasources/overview.md) and
[query time](../queries/time-and-limits.md) for mode-specific constraints.
