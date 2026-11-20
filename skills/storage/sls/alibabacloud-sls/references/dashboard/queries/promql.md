# PromQL

Use bare PromQL, without `* |`, for ordinary Metricstore trends and current values.
Use the actual Metricstore, metric names and metric-specific labels.
For expression semantics, see [PromQL queries](../../query/metric-store/promql.md);
for CLI arguments and results, see [PromQL execution](../../query/query-execution.md#promql).

## Counters and gauges

For a counter throughput trend, use a rate before aggregation:

```promql
sum by (service) (rate(http_requests_total[5m]))
```

This gives requests per second for each service. Gauges represent levels and can be used
directly. Summing cumulative counter samples in a chart reducer does not give request volume.
For resets and the choice of rate or increase, see [counters and gauges](../../query/metric-store/promql.md#counters-and-gauges).

Use regex matchers (`=~`, `!~`) for multi-select tokens, with an explicit All value.
Keep fixed constraints in the query and verify labels separately for each metric.

## Latency and ratios

For histogram percentiles and request-weighted means, use the
[latency expressions](../../query/metric-store/promql.md#latency-and-ratios), with display
units matching the expression's output. Keep a `0..1` ratio for decimal-percent
formatting, or multiply by `100` and use an ordinary numeric percentage display;
do not apply both conversions.

## TopN and result shape

For [TopN expressions](../../query/metric-store/promql.md#topn-and-evaluation-time), instant
mode gives a snapshot ranking; range mode reselects at each step and may show more than
N distinct series over the whole window.

Query aggregation combines series per evaluation. Chart reducers such as `last`, `mean`
or `max` summarize samples within each series; they do not replace query grouping.

Use [Metricstore query parameters](../datasources/metricstore.md#query-parameters)
to select instant/range results and table/series output.

Read [time, step and result limits](time-and-limits.md) when choosing windows and
steps. For Metric StoreView queries, see [StoreView](../datasources/storeview.md).
For full SQL embedding, read [MetricsQL](metricsql.md).
