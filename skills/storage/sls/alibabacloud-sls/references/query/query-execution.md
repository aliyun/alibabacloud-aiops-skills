# Query Execution

This page covers CLI command selection, arguments, and result fields. Query syntax is described
in [MetricStore query and analysis](metric-store/README.md), [index search](index-search.md),
[SQL analysis](sql/README.md), and [SPL](spl/README.md).

- [Logstore](#logstore)
- [MetricStore](#metricstore): SQL analysis, PromQL + SQL, and native PromQL
- [StoreView](#storeview)
- [Result precision](#result-precision)

Select the target's [region and endpoint](../regions.md). `query` accepts either
`--time-range` or `--from` and `--to`; PromQL gives `--time-range` precedence when
both forms are supplied. Place `--format json` after the full command path when saving
or parsing the response.

## Logstore

For field types and matching rules, use the [Logstore index read](../index/manage-index-config.md#read-an-index)
with the same target.

Retrieve logs using the target Project, store, and time range:

```bash
aliyun sls query \
  --project example-project --logstore app-logs \
  --from 2026-09-08T00:00:00Z --to 2026-09-08T01:00:00Z \
  --query '*' --format json
```

For ordinary log search, add `--line 20`; the next page uses `--offset 20`.
Use the same absolute time range for all pages.
For SQL analysis, replace the query with `* | SELECT count(*) AS total` and use
SQL `LIMIT` to select result rows. These are changes to the example above, not
standalone commands. See [index search](index-search.md), [SQL analysis](sql/README.md),
or [SPL](spl/README.md) for each mode's behavior.

## MetricStore

| Task | Command |
| --- | --- |
| SQL or PromQL + SQL analysis | `aliyun sls query` |
| Instant PromQL query | `aliyun sls promql query` |
| PromQL range query | `aliyun sls promql range` |

Specify the MetricStore name with `--logstore` for `query`, or `--metric-store` for `promql`.

For SQL analysis, use `--logstore app-metrics` and a query such as
`* | SELECT __name__, __value__ FROM "app-metrics.prom" LIMIT 10` in the
[Logstore query example](#logstore).
For PromQL + SQL, use a statement such as `* | SELECT promql_query('up') FROM metrics`.

For the SQL source tables and metric fields, see [metric query syntax](metric-store/README.md).

### PromQL

Instant query at the selected end time:

```bash
aliyun sls promql query \
  --project example-project --metric-store app-metrics \
  --from now-5m --to now --query 'up'
```

Range query with a one-minute step:

```bash
aliyun sls promql range \
  --project example-project --metric-store app-metrics \
  --from now-1h --to now --query 'up' --step 1m --limit 20
```

For range queries, `--limit` caps the number of returned time series, not the samples per
series.

The same PromQL group also provides discovery commands. Each takes the common target and
time arguments above:

| Command | Result field |
| --- | --- |
| `promql labels` | `labels` |
| `promql label-values` | `values` |
| `promql series` | `series` |

### MetricStore result fields

| Command | Result structure |
| --- | --- |
| `query` | `data` contains SQL result rows; `meta` contains query status. |
| `promql query` | `type: "instant"`; `results` contains metric, labels, time, and value. |
| `promql range` | `type: "range"`; each item in `results` has metric, labels, `times`, and `vals`. |

In range results, `times[i]` corresponds to `vals[i]`. Metric values are represented as
strings. PromQL commands also retain `meta` and may include `warnings`.

## StoreView

Use the Project that owns the StoreView and pass the view name through `--logstore`
on `query`. StoreView metadata commands use `--store-view`.
If the view's type or source stores are unknown, inspect its configuration:

```bash
aliyun sls store-view get \
  --project example-project --store-view app-view
```

The returned `storeType` identifies a `logstore` or `metricstore` view. Choose the corresponding
log or metric query syntax, then submit the statement through `query`.

For a `logstore` view, use [StoreView index inspection](../index/manage-index-config.md#read-an-index).
Use the source index configurations with the
[Logstore mode-selection rules](entry.md#2-choose-a-query-mode).

Use `--logstore app-view` in the [Logstore query example](#logstore). Choose log or metric syntax
according to the view's type; see the [metric query reference](metric-store/README.md).

StoreView queries return rows in `data` and query status in `meta`. Use `--line` and `--offset`
for ordinary log search, and SQL `LIMIT` for SQL result selection.

## Result precision

If `meta.progress` is not `Complete`, the query result is imprecise. Use the status and the task
requirements to decide how to proceed. A `Complete` result may still contain only the rows
selected by the query's result limit.
