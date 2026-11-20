# Result shapes and chart bindings

Describe the query result: aliases, field types, query name,
time field, dimensions, numeric values, series cardinality, and instant/range mode.
Output field names identify bindings; renaming them requires updating the query
and every consumer.

- Wide time table: one time column and numeric columns; linepro binds each numeric column.
- Grouped long table: time + category + value; aggpro can turn category values into series.
- Native metric series: timestamp/value samples with labels; linepro uses metric mode.
- Category/value rows: use bars, or composition charts when non-negative values represent parts of a whole.
- Scalar or reduced series: statpro; gauges also need a meaningful range.
- Exact multi-column records: tablepro. Extra numeric columns are not automatically distinct series.

A query's series count follows label matchers and aggregation dimensions; selecting
one metric name does not guarantee one series. Range/instant and table/time_series
are separate choices. Transformations may change the input contract; validate their
output against the display binding. See [chart index](../charts/charts.md).

## Table-result bindings

`queryOptionMap` is keyed by query name and binds returned fields to a chart. The
following settings are shared by the specified chart types; other bindings and
chart-specific defaults are documented on each chart page. Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `isTimeSeries` | boolean | Yes, except aggpro crossover | — | For linepro, aggpro, scatterchart, box and colorblockpro: `true` uses time positions; `false` uses category or other non-time positions. |
| `queryOptionMap.<queryName>.xAxisKey` | string | Yes | None | For scatterchart and box: the time or category column. |
