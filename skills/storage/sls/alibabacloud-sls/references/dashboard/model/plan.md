# Plan v1

A Plan is an optional input format for creating a standard grid dashboard from
source, query, chart and control settings. To edit an existing dashboard, modify
its Dashboard JSON directly. The generated Dashboard JSON can be customized
before creation.
These templates show source, query, chart and control configurations:

| Task | Template |
| --- | --- |
| Six common charts with minimal configuration | [Standard dashboard](../assets/plans/standard-charts.json) |
| Logstore overview | [Logstore](../assets/plans/logstore-overview.json) |
| Metric trends | [Metricstore](../assets/plans/metricstore-overview.json) |
| Named view | [StoreView](../assets/plans/storeview-overview.json) |
| Filters and tokens | [Controls](../assets/plans/filter-token-overview.json) |

For a small configuration of a common chart, choose a
[single-chart example](../charts/examples.md).

## Contents

- [Required structure](#required-structure)
- [Choose a chart](#choose-a-chart)
- [Name mapping](#name-mapping)
- [Chart options](#chart-options)
- [Controls](#controls) and [examples](#control-examples)
- [Build](#build)

## Required structure

Plan-defined objects accept the fields declared in
[plan.schema.json](../contracts/plan.schema.json); undeclared fields are rejected.
Chart `display` and `search` carry Dashboard configuration options described in
[Chart options](#chart-options).

| Location | Fields |
| --- | --- |
| Root | `version: 1`, `dashboard`, `sources[]`, `charts[]`; optional `controls[]` |
| dashboard | `displayName`; optional `description` |
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
The builder sets `display.version=2` unless explicitly supplied in `display`.
Sources and queries may be empty for static content.
For imagePro, the builder adds a builtin query when `queries` is omitted or empty;
see [image configuration](../charts/imagepro.md).

PromQL queries support `queryType` (`range` by default, or `instant`), `interval`
(default `60s`), `limit` (default `10000`), `format` (`time_series` by default, or
`table`) and optional `legendFormat`. These options apply to metricstore and
metricstore_storeview. SQL queries put limits and grouping in the query itself.

## Choose a chart

Choose `type`, write the query, then supply the fields and `config` in the table.
`queries[].fields` describes the query's returned columns and aliases, not the
source's raw fields. For example, `count(*) as requests` produces
`{"name":"requests","type":"number"}`.

The [standard dashboard](../assets/plans/standard-charts.json) contains all six
examples below, sharing one source. Replace its source coordinates and adapt the
queries to your data; its SQL assumes `service` and numeric-convertible `status` fields.

For **SQL or other tabular results**, choose the returned fields and chart configuration:

| Goal / type | Returned fields | Configuration |
| --- | --- | --- |
| Show a number: `statpro` | Declare the numeric fields to display | Omit config for `lastNotNull`, or select fields and a [calculation](../charts/statpro.md#plan-configuration). |
| Show a trend: `linepro` | One `time` field and numeric fields; if there is no time field, one `string` field provides a category axis | Omit config. The builder selects the time/category field and all declared numeric fields. A category axis uses one query. |
| Show proportions: `piepro` | One query returning `service:string`, `requests:number` | Bind the category and value fields; see [pie configuration](../charts/piepro.md#plan-configuration). |
| Show one trend per service: `aggpro` | One query returning one time field, `service:string`, `requests:number` | Bind the value and category fields; see [grouped trends](../charts/aggpro.md#plan-configuration). |
| Show a value within a range: `burgauge` | One query returning `error_percent:number` | Select the value and its range; see [gauge configuration](../charts/burgauge.md#plan-configuration). |
| Show rows and columns: `tablepro` | Query result columns; field declarations are optional | Omit config. |

`lastNotNull` selects the last non-null returned value; `total` adds returned values.
For a single-row aggregate, the default displays that row's value. Order multi-row
results when the last value matters. Gauge ranges use the data's units: 0–100 fits
the example percentage query; a ratio from 0 to 1 needs a 0–1 range.

For **native Metricstore PromQL with `format=time_series`**, the result already
contains time, values and series labels. Omit `fields`:

| Type | Config |
| --- | --- |
| `linepro` | Omit config. |
| `statpro` | Omit config for `lastNotNull`; see [stat configuration](../charts/statpro.md#plan-configuration). |
| `piepro` | One query; see [pie configuration](../charts/piepro.md#plan-configuration). |
| `burgauge` | Select a fixed range matching the metric; see [gauge configuration](../charts/burgauge.md#plan-configuration). |

Additional modes and parameters: [stat](../charts/statpro.md#plan-configuration),
[pie](../charts/piepro.md#plan-configuration), [gauge](../charts/burgauge.md#plan-configuration),
[grouped trends](../charts/aggpro.md#plan-configuration).

For controls, use [controls](#controls) with `droplistpro`. A `dashboardrow` has no
queries or config. Markdown and images use their content options in `display`.
For other chart types and custom field mappings, edit the generated Dashboard JSON
using the [chart references](../charts/charts.md).

## Name mapping

Plan names map to [Dashboard JSON](dashboard.md) as follows:

| Plan field | Dashboard JSON field | Meaning |
| --- | --- | --- |
| `charts[].id` | `charts[].title` | Stable chart ID used to identify the chart during edits. |
| `charts[].title` | `charts[].display.basicOptions.displayName` | Visible panel title; an explicit `display.basicOptions.displayName` overrides it. |
| `charts[].queries[].name` | `charts[].search.chartQueries[].name` | Query ID within the chart; used by bindings such as `display.queryOptionMap.<queryName>`. |

## Chart options

- `display`: presentation options such as units, colors and labels; supplied options override
  defaults. Supply complete arrays when changing list-valued options. `layout`
  sets the final position and size.
- `search`: time and request settings, such as start/end/timeSpanType or interval.
  Put queries in `queries` and transformations in `transformers`, not inside search.
- `transformers`: ordered [result transformations](../features/transformations.md).
- `actions`: [click interactions](../features/actions.md), saved as display.actionOptions.
- `config`: chart-specific input from [Choose a chart](#choose-a-chart). Other display options belong
  in `display`, not config.

## Controls

Plan defaults name selected values; Dashboard JSON stores aligned boolean selection flags.

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

## Control examples

The JSON examples below are `controls[]` entries in this Plan.
Source `logs` refers to a declared Logstore with the indexed fields used by the
example.

### Field filter: request method

```json
{
  "id": "request-method",
  "mode": "filter",
  "key": "request_method",
  "label": "Request method",
  "source": "logs",
  "values": ["GET", "POST"],
  "defaults": ["GET"]
}
```

A consumer needs no variable placeholder:

```sql
* | select count(*) as requests
```

Selecting GET adds the search predicate `request_method: GET` before SQL
aggregation. Selecting GET and POST includes either method. For query-derived
candidates, replace `values` and `defaults` with a candidate `query`, in the [control template](../assets/plans/filter-token-overview.json).

### Numeric token: time bucket

```json
{
  "id": "interval",
  "mode": "token",
  "key": "interval",
  "label": "Time bucket",
  "values": ["60", "300", "600"],
  "aliases": ["1 minute", "5 minutes", "10 minutes"],
  "defaults": ["60"]
}
```

```sql
* | select __time__ - __time__ % ${{interval|60}} as time,
    count(*) as requests
    group by time order by time limit 10000
```

Selecting 300 produces five-minute buckets. `${{interval|60}}` uses 60 when no
value is supplied. This numeric substitution is unquoted; restrict its choices
to positive integer bucket widths.

### Multi-select token: metric labels

```json
{
  "id": "service",
  "mode": "token",
  "key": "service",
  "values": ["checkout", "search"],
  "defaults": ["checkout"],
  "multiSelect": true,
  "includeAll": true,
  "allValue": ".*",
  "customTemplate": "<%= data.join(\"|\") %>"
}
```

```promql
sum by (service) (rate(http_requests_total{service=~"${{service|.*}}"}[5m]))
```

Selecting both values substitutes `checkout|search`; All substitutes `.*`.
These example values contain no regex metacharacters; verify the substitution
format for the labels in your query.


## Build

Plan construction requires the `jsonschema` package (`python3 -m pip install jsonschema`).

```sh
python3 scripts/dashboard/dashboard.py build --plan plan.json --output dashboard.json
```

The complete input schema is [plan.schema.json](../contracts/plan.schema.json).
