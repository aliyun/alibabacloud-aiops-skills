# SLS Metricstore

Specify region, project and name. Use `metricstore` for bare PromQL and
`metricsql` for full SQL. Both serialize the resource name into chartQueries[].logstore.

Discover metric names and labels before defining matchers or grouping dimensions:

    python3 scripts/sls.py metrics --type metricstore --region REGION --project PROJECT --name STORE --from START --to END --keyword request
    python3 scripts/sls.py labels --type metricstore --region REGION --project PROJECT --name STORE --from START --to END --metric http_requests_total

Metric-name lookups are bounded; label values and cardinality are sampled. Candidate
search uses local filtering. Do not interpret an empty short-window sample as proof
that a metric does not exist.

## Query behavior

For `datasource=metricstore`, use `queryType=range` for trends and `instant` for a
point-in-time result. Query-level `interval` sets the bare range PromQL step and
supports token substitution; omit it for automatic selection. Instant queries do
not use it. SQL containing `promql_query` or `promql_query_range` retains its own
function, step and `LIMIT`; query-level `interval` and `limit` do not replace them.

Dynamic variable candidate queries against `metricstore` execute bare PromQL as
instant queries regardless of the chart's `queryType`. SQL-wrapped candidate
queries retain their SQL function. Read [variables](../features/variables.md) when
configuring candidate queries.

For bare PromQL, query `limit` caps rows across all series and samples, not series
count or `maxDataPoints`. Read [time and limits](../queries/time-and-limits.md) for
step selection and result budgets.

## Results and legends

`format=time_series` groups samples by metric and labels and aligns them by time;
use it for native series in `linepro`. `format=table` returns `time`, label columns
and `value` for `tablepro` and other tabular consumers.

`legendFormat` changes displayed series names, not field names or query binding
keys. For example, `{{service}} - {{instance}}` substitutes returned label values;
absent labels become empty strings. Keep enough labels in both the PromQL grouping
and the template to distinguish series. Read the
[query parameter table](../model/dashboard.md#query-parameters) for shared fields
and defaults.

Keep fixed matchers when adding token or Adhoc controls. See
[PromQL](../queries/promql.md) for expressions and
[MetricsQL](../queries/metricsql.md) for full SQL embedding.
