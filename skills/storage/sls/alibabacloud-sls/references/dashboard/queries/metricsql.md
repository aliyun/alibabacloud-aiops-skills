# SQL over SLS metrics

`metricsql` accepts complete SQL rather than bare PromQL. Use it when SQL must
split labels into columns, join or aggregate returned data, rank rows or rename
fields. Resource coordinates still identify the SLS Metricstore. For
bare PromQL trends, use [PromQL](promql.md) with `metricstore`.

## Embedded PromQL

`promql_query('expression')` provides instant results.
`promql_query_range('expression', 'step')` provides range results and requires an
explicit step. Use `from metrics` in the inner query, then select the fields needed
by the chart. Full signatures and returned columns are in the
[PromQL SQL functions](../../query/metric-store/promql-functions.md):

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

The embedded result exposes `time`, `value` and a `labels` map;
`element_at(labels, 'instance')` returns the instance label as a column.
Here `[5m]` is the rate window and `60s` is the evaluation step. `avg by (instance)`
averages rates; use `sum by (instance)` when the intended measure is their total.

The outer query returns a long table with `time`, `instance` and `value`. Bind those
fields to time, series category and value; keep `order by time` for trends. Set the row
budget to cover the expected time points × series. Read [time, step and result
limits](time-and-limits.md) for shared window and budget guidance.

## Direct metric-table queries

Direct SQL reads the quoted `"<metricstore>.prom"` table. Its fields are described in
[metric SQL](../../query/metric-store/README.md#sql-analysis). A
[time-and-label example](../../query/metric-store/README.md#time-and-label-columns)
returns Unix seconds, an instance label and a numeric value for chart bindings.

## Result contract and filtering

Return stable aliases matching the Plan and chart bindings. SQL determines the
columns, grouping, ordering and `LIMIT`; PromQL query-level `format`/`queryType`
fields do not configure this mode. Put range step in `promql_query_range` itself.

Token substitution requires placeholders in SQL or its embedded expression. Adhoc
label injection applies only to eligible embedded PromQL expressions. Direct
metric-table queries need explicit SQL predicates for label filtering; adhoc
controls do not generate those predicates.

For saved `metricsql_storeview` entries, see
[MetricsQL StoreView entries](../datasources/storeview.md#metricsql-storeview-entries).
