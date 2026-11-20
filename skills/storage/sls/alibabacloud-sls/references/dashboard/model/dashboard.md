# Dashboard object model

A dashboard has `displayName`, `description`, `attribute.type` (`grid`/`free`) and
`charts[]`. Grid provides 24 columns; free provides custom positioning. Empty layout settings
are interpreted as free. See [layout](../features/layout.md).
`dashboardName` identifies it remotely. A chart's `title` is its stable
ID; `display.basicOptions.displayName` is its visible title.
For Plan input fields, see [name mapping](plan.md#name-mapping).

Chart IDs such as `request-trend` identify panels across edits. Visible titles are
separate labels. Chart type identifiers are case-sensitive, including `facetPro`
and `imagePro`; see [chart types](../charts/charts.md).

New chart examples and Plan builds use `display.version=2`, the chart configuration marker.

`display` contains layout, field bindings, styles, local variables and actions.
`search` contains queries, time settings and transformations. A query's `name` is
its unique binding key within the chart; `displayName` is a label.

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

## Query parameters

Parameters belong to each `chart.search.chartQueries[]` entry.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `name` | string | Yes | None | Unique query ID within the chart; used by bindings and actions. |
| `displayName` | string | No | name | Query label. |
| `datasource` | string | Yes | None | Datasource mode; see [datasource modes](../datasources/overview.md), including [builtin simulated data](../datasources/builtin.md). |
| `project` | string | No | Current Project | With dataSourceType=mixed, selects the source Project; an omitted or empty value uses the current Project. With current, queries use the current Project. |
| `logstore` | string | Yes for SLS queries | None | Source Logstore, Metricstore, or StoreView name. |
| `region` | string | For resource location | — | Source region. |
| `query / tokenQuery` | string | Yes for SLS queries | None | SLS query text; a non-empty tokenQuery takes precedence over query. Builtin needs no query text. |
| `hide` | boolean | No | false | Exclude the query from normal chart requests. |


See [datasource modes](../datasources/overview.md) and
[query time](../queries/time-and-limits.md) for mode-specific constraints. Metric query fields are listed under
[Metricstore parameters](../datasources/metricstore.md#query-parameters).
