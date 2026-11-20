# PromQL Functions for SQL Analysis

SLS documents the following seven signatures, including overloads. Each function returns a
table. Use the fixed source table `metrics`.
For the expression itself, see [PromQL expressions](promql.md).

The expression, selector, label name, and step arguments are strings. A selector argument
accepts one series selector. For the two-argument `promql_label_values`, the selector comes first.

| Signature | Purpose | Example |
| --- | --- | --- |
| `promql_query(expression)` | Instant query evaluated at the selected query time range's end time. | `* \| SELECT promql_query('up') FROM metrics` |
| `promql_query_range(expression, step)` | Query the selected start/end interval using the specified step. | `* \| SELECT promql_query_range('up', '5m') FROM metrics` |
| `promql_labels()` | Return label names. | `* \| SELECT promql_labels() FROM metrics` |
| `promql_labels(selector)` | Return label names for the matching series. | `* \| SELECT promql_labels('up') FROM metrics` |
| `promql_label_values(label_name)` | Return values of the specified label. | `* \| SELECT promql_label_values('__name__') FROM metrics` |
| `promql_label_values(selector, label_name)` | Return values of the specified label for the matching series. | `* \| SELECT promql_label_values('up', 'instance') FROM metrics` |
| `promql_series(selector)` | Return matching time series. | `* \| SELECT promql_series('up') FROM metrics` |

`promql_labels`, `promql_label_values`, and `promql_series` default to the five-minute interval
ending at the selected end time: `[EndTime - 5 minutes, EndTime]`.

## Returned tables

### Instant and range queries

`promql_query` and `promql_query_range` return:

| Column | Type | Description |
| --- | --- | --- |
| `metric` | `varchar` | Metric name; it may be empty when grouping is used. |
| `labels` | `map<varchar, varchar>` | Labels. |
| `time` | `bigint` | Time. |
| `value` | `double` | Value at that time. |

### Label names and values

Both overloads of `promql_labels` and `promql_label_values` return one `label` column of type
`varchar`. It contains label names for `promql_labels` and label values for `promql_label_values`.

### Series

`promql_series` returns one `series` column of type `map<varchar, varchar>`, representing the
matching time series. The official example includes `__name__`, `instance`, and `job` entries.

Source: [Time-series query and analysis syntax — SQL + PromQL](https://help.aliyun.com/zh/sls/time-metric-data-query-and-analysis-syntax).
