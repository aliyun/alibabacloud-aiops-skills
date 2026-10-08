# SQL over SLS metrics

`metricsql` accepts complete SQL rather than bare PromQL. Use it when SQL must
split labels into columns, join or aggregate returned data, rank rows or rename
fields. Resource coordinates still identify the SLS Metricstore. For
bare PromQL trends, use [PromQL](promql.md) with `metricstore`.

## Embedded PromQL

`promql_query('expression')` provides instant results.
`promql_query_range('expression', 'step')` provides range results and requires an
explicit step. Use `from metrics` in the inner query, then select the fields needed
by the chart:

```sql
* | select time,
           element_at(labels, 'instance') as instance,
           value
    from (
      select promql_query_range('avg by (instance) (rate(http_requests_total[5m]))', '60s')
      from metrics
    )
    order by time
    limit 10000
```

The embedded result exposes `time`, `value` and a `labels` map. Use
`element_at(labels, 'instance')` to return the instance label as a column. The
five-minute `[5m]` window controls the rate calculation; the `60s` step controls
how often the expression is evaluated. `avg by (instance)` averages the rates of
series sharing an instance; it does not compute their total. Use `sum by (instance)`
when the intended measure is the total request rate for each instance.

The outer query returns a long table with `time`, `instance` and `value`. Bind those
fields to time, series category and value; keep `order by time` for trends. Set the row
budget to cover the expected time points × series. Read [time, step and result
limits](time-and-limits.md) for shared window and budget guidance.

## Direct metric-table queries

To read stored samples without an embedded PromQL function, use the quoted
`"<metricstore>.prom"` table and its fixed fields:

| Field | Meaning |
| --- | --- |
| `__name__` | Metric name. |
| `__labels__` | Map of label names to values. |
| `__value__` | Numeric sample value. |
| `__time_nano__` | Sample timestamp in nanoseconds. |

```sql
* | select __time_nano__ / 1000000000 as time,
           element_at(__labels__, 'instance') as instance,
           __value__ as value
    from "my_metricstore.prom"
    where __name__ = 'up'
    order by time
    limit 10000
```

Replace `my_metricstore` with the Metricstore name and retain the double
quotes around the whole table identifier. The division converts nanoseconds to
seconds; `element_at` extracts a label from the map. Filter `__name__` to the
metric you need.

## Result contract and filtering

Return stable aliases matching the Plan and chart bindings. SQL determines the
columns, grouping, ordering and `LIMIT`; PromQL query-level `format`/`queryType`
fields do not configure this mode. Put range step in `promql_query_range` itself.

Token substitution requires placeholders in SQL or its embedded expression. Adhoc
label injection applies only to eligible embedded PromQL expressions. Direct
metric-table queries need explicit SQL predicates for label filtering; adhoc
controls do not generate those predicates.

Public product documentation excludes SQL on metric StoreViews;
`metricsql_storeview` is not generated as a new supported query source. For saved
entries using that identifier, see [MetricsQL StoreView entries](../datasources/storeview.md#metricsql-storeview-entries).
