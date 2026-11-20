# SLS Metricstore

Specify region, project and name. Use `metricstore` for bare PromQL and
`metricsql` for full SQL. Both use `chartQueries[].logstore` for the resource name.

The CLI can list metric names and matching series labels:

```sh
aliyun sls promql label-values --project PROJECT --metric-store STORE \
  --label __name__ --from now-1h --to now
aliyun sls promql series --project PROJECT --metric-store STORE \
  --match http_requests_total --from now-1h --to now
```

These results describe the selected time window and limits. Existing queries,
metric definitions and prior results can also supply metric and label information.
For command details and returned fields, see [PromQL execution](../../query/query-execution.md#promql).

## Query parameters

Paths are relative to `chart.search.chartQueries[]` for Metricstore queries.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryType` | string | For Metricstore PromQL | — | range for series; instant for a point-in-time result. |
| `interval` | string or number | For explicit range step | Automatic | Sampling step for bare range PromQL; see time and result limits below. |
| `limit` | number | No | 10000 for Metricstore PromQL | Metricstore result row count across series and samples, not series count or maxDataPoints; SQL row limits belong in SQL. |
| `format` | string | No | — | time_series for series; table for labels and values as columns. |
| `legendFormat` | string | No | Series labels, prefixed by metric name when present | For Metricstore, sets the displayed series name, such as {{service}}; absent labels become empty strings. Field names and query IDs stay unchanged. For prometheus, see its [query fields](prometheus.md#prometheus-datasource). |

See [time and result limits](../queries/time-and-limits.md) for step selection,
SQL-wrapped queries, candidate queries and result budgets.

## Results and legends

`format=time_series` groups samples by metric and labels and aligns them by time;
use it for native series in `linepro`. `format=table` returns `time`, label columns
and `value` for `tablepro` and other tabular consumers.

See
[PromQL](../queries/promql.md) for expressions and
[MetricsQL](../queries/metricsql.md) for full SQL embedding.
