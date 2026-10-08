# PromQL

Use bare PromQL, without `* |`, for ordinary Metricstore trends and current values.
Use exact Metricstore names, metric names and metric-specific labels. Matchers
select series; aggregation with `by`/`without` determines which label dimensions
remain. Each remaining label combination identifies a series.

## Contents

- [Counters and gauges](#counters-and-gauges)
- [Latency and ratios](#latency-and-ratios)
- [TopN and result shape](#topn-and-result-shape)
- [Prometheus datasource](#prometheus-datasource)

## Counters and gauges

For counters:

| Function | Purpose |
| --- | --- |
| `rate(counter[5m])` | Average per-second increase over the five-minute window; useful for throughput trends. |
| `irate(counter[5m])` | Per-second increase from the last two samples in the window; useful for fast-changing throughput. |
| `increase(counter[5m])` | Increase over the five-minute window, rather than a per-second rate. |

All three account for counter resets. Apply the function before aggregating
independently resetting counters, for example:

```promql
sum by (service) (rate(http_requests_total[5m]))
```

This gives requests per second for each service. Gauges represent levels; use them
directly or aggregate them according to the measure. Do not sum cumulative counter
samples in a chart reducer and label the result request volume.

Use regex matchers (`=~`, `!~`) for multi-select tokens, with an explicit All value.
Keep fixed constraints in the query and verify labels separately for each metric.

## Latency and ratios

For a classic histogram of request durations measured in seconds, compute the
95th percentile from bucket rates while retaining the `le` bucket boundary label:

```promql
histogram_quantile(0.95, sum by (le) (rate(request_duration_seconds_bucket[5m])))
```

The result is in seconds. To return a separate percentile for each service, retain
both `service` and `le` in `sum by (service, le)`. Removing `le` destroys the bucket
structure needed for this calculation. Do not average per-instance percentiles to
obtain a combined percentile.

For a request-weighted mean latency in milliseconds, divide total duration rate by
total observation-count rate, then convert seconds to milliseconds:

```promql
1000 * sum(rate(request_duration_seconds_sum[5m]))
  / sum(rate(request_duration_seconds_count[5m]))
```

Use the `_sum` and `_count` of the same duration metric, with identical scope
matchers and windows. Require a positive summed count rate; exclude zero-count
results rather than treating them as zero latency.
This weights by request count, unlike an average of per-instance means. For per-service
means, preserve the same service labels in both aggregations.

For any ratio, align numerator and denominator labels and scope, handle zero
denominators, and state the output scale. Keep a `0..1` ratio for decimal-percent
formatting, or multiply by `100` and use an ordinary numeric percentage display;
do not apply both conversions.

## TopN and result shape

Rank instances by request rate, rather than by their cumulative counter values:

```promql
topk(10, sum by (instance) (rate(http_requests_total[5m])))
```

An instant query selects up to ten instances at one evaluation time. A range query
reevaluates TopN at every step: the ten-instance bound applies per step, not to the
whole time window. Choose instant mode for a snapshot ranking and range mode to
follow the leaders over time.

Query aggregation such as `sum`, `avg` or `max` combines series at each evaluation
time. Chart reducers such as `last`, `mean` or `max` summarize returned samples
within a series. A query-level `max` does not take the maximum over the whole time
window, and chart reduction does not replace query grouping.

For `metricstore`, `queryType=range` selects a time range with a step;
`queryType=instant` selects one evaluation time. Either can return multiple series.
`format=time_series` retains labeled series; `format=table` exposes labels and
values for tabular consumers. Native series use `linepro`, not the `aggpro`
category pivot. Legend label placeholders use double braces, such as `{{service}}`;
legend naming does not filter or aggregate data.

Read [time, step and result limits](time-and-limits.md) when choosing windows and
steps. Metric StoreView uses the SLS metric HTTP API; its time and metadata semantics
are documented in [SLS query behavior](../datasources/api.md). For full SQL embedding,
read [MetricsQL](metricsql.md).

## Prometheus datasource

Saved queries with `datasource="prometheus"` identify a Prometheus instance, not an
SLS Metricstore. This section describes their Dashboard JSON fields; the bundled
Plan and query commands do not support this source. See [tool support](../datasources/overview.md#other-dashboard-json-sources).

Paths are relative to `chart.search.chartQueries[]`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `name` | string | Yes | None | Query ID used by chart bindings. |
| `datasource` | string | Yes | None | prometheus. |
| `regionId` | string | For an explicit instance | None | Instance region. |
| `clusterId` | string | For an explicit instance | None | Prometheus instance ID, not an SLS Logstore name. |
| `expr / tokenQuery / query` | string | Yes | None | PromQL expression; non-empty expr takes precedence over tokenQuery, then query. |
| `range` | boolean | No | true | true returns range samples; false evaluates at one time. |
| `instant` | boolean | No | false | true overrides range and forces an instant query; use range for new entries. |
| `format` | string | No | time_series | time_series returns numeric series fields; table exposes labels as columns. |
| `interval` | string | No | Automatic | Range evaluation step, such as 60s or 1m. |
| `legendFormat` | string | No | Metric name and labels | Series-name template using {{label}}. Missing labels leave empty text; a wholly empty name uses the default. Applies to time_series, not table. |

With `time_series`, the result has `time` and one numeric field per series. Unlike
Metricstore, the formatted series name is also that field's name: bind the
returned name, not an assumed `value` field. Retain labels that distinguish series.

With `table`, each sample is a row with `Time`, label columns and `Value`.
Multiple table queries use value columns such as `Value #A` and `Value #B`.
`range=false` gives one sample per series; it does not combine multiple series.

Example query entry; replace the instance ID and use metric and label names from
that instance:

```json
{
  "name": "A",
  "datasource": "prometheus",
  "regionId": "cn-hangzhou",
  "clusterId": "<prometheus-instance-id>",
  "expr": "sum by (service) (rate(http_requests_total[5m]))",
  "range": true,
  "format": "time_series",
  "interval": "60s",
  "legendFormat": "{{service}}"
}
```
