# Filters, tokens and Adhoc

| Mode | Effect | Suitable use |
| --- | --- | --- |
| filter | Append a field predicate to a supported log search | Proven indexed log dimensions |
| token | Replace explicit placeholders in a query or supported resource/content field | Query or content parameter |
| adhoc | Add metric label matchers | User-selected metric label/operator/value |

A token consumer must contain the matching placeholder. For multiple selected metric
labels, use a regex matcher with a pipe-joined value and allValue='.*'; an exact matcher
does not interpret that list. Sampled label values do not provide a complete dynamic
list. Labels must be valid for the queried metrics.

Static values, aliases and default flags align by index. Plan defaults name declared
values; the builder converts them to flags. Dynamic candidates come from an explicit
query and valueField when needed. The current Plan disallows sampled static defaults
in dynamic controls.

Dependent option queries must consume parent tokens and must not form a cycle.
`search.isInheritFilter` lets log-backed candidate queries inherit other field
filters. It does not control normal chart filtering, token substitution or Adhoc.

Adhoc binds a metric resource and obtains current labels; it has no token
placeholder, static candidates or preset token defaults. Its metric-query scope can
be dashboard-wide; a Plan reference does not restrict it to a subset of panels.
Keep fixed resource constraints in queries; controls add optional filters.

Each Plan `controls[]` definition requires one visible `droplistpro` chart with
`control` set to the control's `id`. `display.fixedTop` places eligible controls in
the top variable area. Chart-local selectors use [local variables](local-variables.md).
For [StoreViews](../datasources/storeview.md), test the selected filter or Adhoc
control against the view.

For the saved JSON parameters, see [dropdown controls](../charts/droplistpro.md).

## Examples

The JSON examples below are `controls[]` entries in a [Plan](../model/plan.md).
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
candidates, replace `values` and `defaults` with a candidate `query`, as shown in
the complete Plan below.

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

### Complete Plan

[filter-token-overview.json](../../assets/plans/filter-token-overview.json)
contains a dynamic request-method filter, a static time-bucket token, a request
count, and a trend chart. Replace its example source coordinates with the target
Logstore, and verify that `request_method` supports search and SQL analysis.

The method filter affects both data charts. The interval token affects only the
trend query, which contains its placeholder; it does not change the request count.
The candidate query returns at most 1,000 methods, not an unbounded catalog.

```sh
python3 scripts/dashboard.py build --plan assets/plans/filter-token-overview.json --output dashboard.json
```
