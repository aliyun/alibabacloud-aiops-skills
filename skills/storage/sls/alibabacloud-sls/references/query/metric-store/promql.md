# PromQL expressions

Label matchers select series; aggregation with `by` or `without` determines which
dimensions remain. Each remaining label combination identifies a series.
An instant query evaluates at one time; a range query repeats evaluation at each step.
A range selector such as `[5m]` controls the input window at each evaluation;
the query step controls the spacing between evaluations.

## Counters and gauges

| Expression | Meaning |
| --- | --- |
| `rate(counter[5m])` | Average per-second increase over the five-minute window. |
| `irate(counter[5m])` | Per-second increase from the last two samples; useful for fast-changing counters. |
| `increase(counter[5m])` | Increase over the window, rather than a per-second rate. |

These functions account for counter resets. Apply them before aggregating independently
resetting counters, for example requests per second by service:

```promql
sum by (service) (rate(http_requests_total[5m]))
```

Gauges represent levels and can be used directly or aggregated for the intended measure.

## Latency and ratios

For a classic histogram of durations in seconds, retain the `le` bucket boundary label
when combining bucket rates to calculate P95:

```promql
histogram_quantile(0.95, sum by (le) (rate(request_duration_seconds_bucket[5m])))
```

The result is in seconds. Retain both `service` and `le` for a percentile per service.
Removing `le` loses the classic histogram's bucket structure. Averaging per-instance
percentiles does not produce a combined percentile.

For a request-weighted mean latency in milliseconds:

```promql
1000 * sum(rate(request_duration_seconds_sum[5m]))
  / sum(rate(request_duration_seconds_count[5m]))
```

Use the same duration metric, scope matchers and window for `_sum` and `_count`.
A positive summed count rate is needed for a meaningful mean; exclude zero-count results.
This weights by request count rather than averaging per-instance means. Per-service means
retain the same service labels in both aggregations.

For other ratios, align numerator and denominator labels, scope and windows, and account
for zero denominators. For percentage output, choose a fraction or multiply by `100`.

## TopN and evaluation time

Rank by request rate rather than cumulative counter values:

```promql
topk(10, sum by (instance) (rate(http_requests_total[5m])))
```

An instant query selects up to ten instances at that evaluation time. A range query
reevaluates TopN at every step, so the whole range may contain more than ten instances.
Query aggregations such as `sum`, `avg` and `max` combine series at each evaluation time;
they do not summarize each series over the entire query window.

For SLS metric SQL and embedded PromQL, see [MetricStore queries](README.md).
For CLI arguments and returned fields, see [PromQL execution](../query-execution.md#promql).

## References

- [Prometheus functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [Prometheus operators](https://prometheus.io/docs/prometheus/latest/querying/operators/)
