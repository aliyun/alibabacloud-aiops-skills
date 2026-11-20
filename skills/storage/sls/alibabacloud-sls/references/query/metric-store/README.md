# MetricStore Query and Analysis

MetricStore supports three query forms:

| Form | Description |
| --- | --- |
| [PromQL](#promql) | Query and analyze time-series data using Prometheus query syntax. |
| [SQL analysis](#sql-analysis) | Query and analyze stored metric data using SQL. |
| [PromQL + SQL analysis](#promql--sql-analysis) | Use SLS PromQL functions within SQL queries. |

## PromQL

For counters, latency, ratios and TopN, see [PromQL expressions](promql.md).
PromQL uses the standard open-source syntax; see the
[Prometheus query documentation](https://prometheus.io/docs/prometheus/latest/querying/basics/).

## SQL analysis

Metric SQL uses the same SQL syntax as log analysis, but its source table must be
`"<metric_store_name>.prom"`. Keep the double quotes around the table name.

| Field | Description |
| --- | --- |
| `__value__` | Metric value. |
| `__time_nano__` | Sample timestamp in nanoseconds. |
| `__labels__` | Metric labels; use `element_at(__labels__, 'key')` to access a label value. |
| `__name__` | Metric name. |

Select metric data:

```sql
* | SELECT *
FROM "my_metric_store.prom"
WHERE __name__ != ''
```

Sum the values of `http_request_count` for a particular domain:

```sql
* | SELECT sum(__value__)
FROM "my_metric_store.prom"
WHERE __name__ = 'http_request_count'
  AND element_at(__labels__, 'domain') = 'www.example.com'
```

Group the same calculation by hour:

```sql
* | SELECT sum(__value__), date_trunc('hour', __time_nano__/1000000) AS t
FROM "my_metric_store.prom"
WHERE __name__ = 'http_request_count'
  AND element_at(__labels__, 'domain') = 'www.example.com'
GROUP BY t
ORDER BY t DESC
```

Replace `my_metric_store` with the actual MetricStore name. The metric data representation
is described in the [official metric schema](https://help.aliyun.com/zh/sls/metric#section-s08-djk-ea8).

### Time and label columns

For output in numeric Unix seconds, divide `__time_nano__` by `1000000000`.
`element_at` extracts a label from the map:

```sql
* | select __time_nano__ / 1000000000 as time,
           element_at(__labels__, 'instance') as instance,
           __value__ as value
    from "my_metric_store.prom"
    where __name__ = 'up'
    order by time
    limit 10000
```

## PromQL + SQL analysis

Use the SLS PromQL functions in SQL. For these functions, the source table is fixed to `metrics`.

| Function | Purpose |
| --- | --- |
| `promql_query(expression)` | Instant query at the selected end time. |
| `promql_query_range(expression, step)` | Query the selected query time range with a specified step. |
| `promql_labels()` | List label names. |
| `promql_labels(selector)` | List label names for matching series. |
| `promql_label_values(label_name)` | List values of a label. |
| `promql_label_values(selector, label_name)` | List label values for matching series. |
| `promql_series(selector)` | List matching time series. |

```sql
* | SELECT promql_query_range('up', '5m') FROM metrics
```

This queries `up` over the selected query time range with a five-minute step. These functions return
tables that can be used in nested SQL queries. See [PromQL functions](promql-functions.md)
for all seven documented signatures, examples, and returned columns.

## Limit

For PromQL and PromQL + SQL, the official documentation specifies a maximum of 11,000 time points.

Source: [Time-series query and analysis syntax](https://help.aliyun.com/zh/sls/time-metric-data-query-and-analysis-syntax).
