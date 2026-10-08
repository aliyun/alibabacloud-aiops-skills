# Legend

Use when identifying series, comparing summary values, or controlling series visibility.
Parameters belong to `display.legendOption` on charts that support legends.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `show` | boolean | No | false | Show the legend. |
| `mode` | string | No | list | list shows labels; table supports statistic columns where available. |
| `position` | string | No | bottom | top, right, bottom, or left of the plot. |
| `sortOrder` | string | No | none | none, asc, or desc; orders legend entries, not query rows. |
| `actionMode` | string | No | toggle | single isolates the clicked series; toggle changes only that series' visibility. |
| `maxContent` | number | No | 30 | Maximum legend width or height as a percentage of panel space; 0–60. |
| `calcs` | string[] | No | [] | Statistics per series. Use with table mode on supported charts; see reducers below. |

## Calculations

Use `first`, `last`, `firstNotNull`, `lastNotNull`, `min`, `max`, `mean`,
`total`, `count`, `range`, `difference`, `differencePercent`, `distinctCount`,
`minAboveZero`, or `step` where supported. See [reducer meanings](reducers.md).
These summarize returned samples, which may be limited by the query.

Line, bar, histogram, and grouped line/bar charts support summary columns.
Pie charts support `value` and `percent` instead of time-series reductions.
`radarchart`, `funnelpro`, and the state timeline `timelinepro` support only basic
legend settings, without `mode` or `calcs`.
Use `mode="table", calcs=["min","max","mean"]` to compare multiple services.

For native Metricstore series, query `legendFormat` uses label placeholders such as
`{{service}}`. Retain labels that distinguish series; formatting does not change field
names or query IDs. For `datasource="prometheus"`, formatted series names are also field
names; see [Prometheus queries](../queries/promql.md#prometheus-datasource).
