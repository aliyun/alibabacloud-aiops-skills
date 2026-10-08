# Plan v1

A Plan describes new dashboard content. Start from a [template](../../assets/plans/logstore-overview.json)
and replace its example sources and queries. Complete Dashboard JSON can be
validated directly without a Plan.

For a small configuration of a common chart, choose a
[single-chart example](../charts/examples.md).

## Required structure

| Location | Fields |
| --- | --- |
| Root | `version: 1`, `dashboard`, `sources[]`, `charts[]`; optional `controls[]` |
| dashboard | `displayName`; optional `description`, `layout` (`grid`, recommended and default; `free` only for a custom layout) |
| sources[] | `id`, `type`, `region`, `project`, `name`; use a [supported source type](../datasources/overview.md) |
| charts[] | `id`, `title`, `type`, `layout: {x,y,w,h}` |
| charts[].queries[] | `name`, `source` (a sources[].id), `query`; optional `fields`, `hide` |
| queries[].fields[] | `name` and `type`: `time`, `number`, `string`, `boolean`, `object` or `unknown` |

For new charts, use lowercase letters/digits separated by hyphens for `charts[].id`,
such as `request-trend`. The visible title in `charts[].title` may use normal capitalization;
see [name mapping](#name-mapping).
Source, chart and control IDs are unique within their lists; query names are unique
within a chart. Field names must match query output aliases. Layout uses non-negative
integer x/y and positive integer w/h; grid charts fit within 24 columns without overlap.
Sources and queries may be empty for static content.
For imagePro, the builder adds a builtin query when `queries` is omitted or empty;
see [image configuration](../charts/imagepro.md).

PromQL queries support `queryType` (`range` by default, or `instant`), `interval`
(default `60s`), `limit` (default `10000`), `format` (`time_series` by default, or
`table`) and optional `legendFormat`. These options apply to metricstore and
metricstore_storeview. SQL queries put limits and grouping in the query itself.

## Name mapping

Plan names map to [Dashboard JSON](dashboard.md) as follows:

| Plan field | Dashboard JSON field | Meaning |
| --- | --- | --- |
| `charts[].id` | `charts[].title` | Stable chart ID used to identify the chart during edits. |
| `charts[].title` | `charts[].display.basicOptions.displayName` | Visible panel title; an explicit `display.basicOptions.displayName` overrides it. |
| `charts[].queries[].name` | `charts[].search.chartQueries[].name` | Query ID within the chart; used by bindings such as `display.queryOptionMap.<queryName>`. |

## Chart options

- `display`: explicit presentation and field bindings; supplied options override
  defaults. Supply complete arrays when changing list-valued options. `layout`
  sets the final position and size.
- `search`: time and request settings, such as start/end/timeSpanType or interval.
  Put queries in `queries` and transformations in `transformers`, not inside search.
- `transformers`: ordered [result transformations](../features/transformations.md).
- `actions`: [click interactions](../features/actions.md), saved as display.actionOptions.
- `config`: chart-specific input from the table below. Other display options belong
  in `display`, not config.

| Chart/input | charts[].config |
| --- | --- |
| statpro, table reduction | `stat: {mode:"calculate", valueFields:["value"], reducer:"first"}` |
| statpro, individual rows | `stat: {mode:"allValues", valueFields:["value"], labelField:"label", limit:10}` |
| statpro, metric series | `stat: {reducer:"lastNotNull"}` |
| piepro, categories | `pie: {mode:"categoryValue", categoryField:"category", valueField:"value"}`; optional `concatFields` |
| piepro, table reduction | `pie: {mode:"dataCalculation", calculation:{mode:"calculate", valueFields:["value"], reducer:"total"}}` |
| piepro, metric series | `pie: {reducer:"lastNotNull"}` |
| burgauge | `gauge: {data, range, labelMode}` for tables; `gauge: {data:{reducer}, range}` for metric series; see [gauge configuration](../charts/burgauge.md#plan-configuration) |
| aggpro, grouped time table | `agg: {valueField:"value", aggField:"category"}`; declare one time field, a numeric value and a string category |

Replace sample field names with query output aliases and choose result limits. Row modes
select one value field and a label field; reduction modes need a reducer. Common
reducers include first, lastNotNull, min, max, mean and total; choose according to the
measure. Table configurations for piepro, burgauge and aggpro use one query. When piepro
reduces multiple table fields, select all numeric result fields. Without an explicit
stat config, statpro selects numeric fields and uses lastNotNull.

linepro uses declared time/category and numeric fields, or explicit queryOptionMap
bindings. A category axis uses isTimeSeries=false and one query. tablepro needs no
extra config. timeseriesPro needs one algorithm query and allows empty display.
facetPro needs one algorithm query and the [facet display configuration](../charts/facetPro.md#query-and-display).
Other charts need the display options shown in their [chart reference](../charts/charts.md).

## Controls

Every control has `id`, `mode` (`filter`, `token`, `adhoc`) and `key`; `label` is
optional. Render it in one droplistpro chart using `control: "CONTROL_ID"` and a
normal layout, without chart-level queries.

| Mode/input | Configuration |
| --- | --- |
| Static filter/token | `values` (unique strings), optional `aliases` aligned with values, and `defaults` containing selected values |
| Dynamic filter/token | `query` with the same shape as a chart query; omit values/defaults. For tokens, `valueField` selects the returned candidate column |
| filter | `source` identifies a log source; key is the field to filter |
| token | Consumers reference `${{key}}`; optional multiSelect, includeAll, allValue and customTemplate |
| adhoc | `source` identifies a metric source; use letters, digits and underscores for the key. Omit candidate queries, values, defaults and token options |

`includeAll=true` requires an explicit allValue. Multi-select token formatting
must match its consumer query; metric regex matchers commonly use `.*` for All.
A dynamic query's source must match the control source when both are provided.
`inheritFilter` controls whether eligible log-backed candidate queries inherit
filters. It does not enable token substitution in other charts.

Example static token in controls[]:

```json
{"id":"environment","mode":"token","key":"env","label":"Environment","values":["prod","test"],"defaults":["prod"]}
```

Its droplist chart uses `control:"environment"`. A log query consumes it as
`env: "${{env}}" | select count(*) as requests` when env is a valid indexed field.
The [filter/token Plan](../../assets/plans/filter-token-overview.json) combines
candidate lookup, both control modes, and their consumer charts. See
[variables](../features/variables.md) for the query effects, multi-select
formatting, candidate dependencies, and Adhoc scope.

## Build

```sh
python3 scripts/dashboard.py build --plan plan.json --output dashboard.json
```

Optional `--facts facts.json` can be repeated. Each facts file must match its Plan
source's id/type/region/project/name. See [source facts](source-facts.md).
The complete input schema is [plan.schema.json](../contracts/plan.schema.json).
