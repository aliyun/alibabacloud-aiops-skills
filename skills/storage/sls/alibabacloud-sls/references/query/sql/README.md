# SQL Analysis

## Purpose and features

SQL analysis computes results over the logs selected by an `index_search_statement`. It supports
selecting columns, calculations, aggregation, grouping, sorting, nested queries, and joins.
This page describes indexed SQL analysis for Logstores. See [SQL SCAN](sql-scan.md) for
scan-analysis syntax.

For field types, analytics settings and Logstore prerequisites, see
[indexed SQL requirements](../../index/index-configuration.md#indexed-sql-analysis);
[historical coverage](../../index/index-configuration.md#configuration-changes-and-historical-data) depends on when the index settings took effect.

## Basic syntax

```sql
index_search_statement | SELECT expressions
FROM log
WHERE row_condition
GROUP BY grouping_expressions
HAVING group_condition
ORDER BY ordering_expressions
LIMIT count
```

Include clauses as needed. `log` refers to the current Logstore; the `FROM` clause can be
omitted when analyzing that Logstore. Use `*` before the pipe when no search filter is needed.
Where an existing index can express the required filter, put it before `|` to reduce the data
passed to analysis.

String literals use single quotes. Field names containing special characters or reserved
words use double quotes. For example, `'status'` is text, while `"status"` identifies a column.
Quote a dotted field name as one identifier, such as `"properties.agent_version"`.

## Examples

Count records by status:

```sql
* | SELECT status, count(*) AS pv
GROUP BY status
```

Find the ten most frequently requested paths, excluding URL query parameters:

```sql
* | SELECT split_part(request_uri, '?', 1) AS path, count(1) AS pv
GROUP BY path
ORDER BY pv DESC
LIMIT 10
```

Count errors by hour:

```sql
status:500 | SELECT date_format(__time__, '%Y-%m-%d %H:00:00') AS hour,
                    count(*) AS error_count
FROM log
GROUP BY hour
ORDER BY hour
```

## High-Frequency Functions

The categories follow the [official SQL function catalog](https://help.aliyun.com/zh/sls/sql-function/).
The table lists representative functions rather than every function or overload.

`example_output`, where provided, shows a SQL result row or a list of result rows with typed values.
`example_input` supplies sample rows for examples whose results depend on log data.

| Category | Representative functions | Purpose | Details |
| --- | --- | --- | --- |
| Aggregate functions | `count`, `sum`, `avg`, `max_by` | Count records, calculate totals and averages, and retrieve values associated with extrema. | [Local reference](functions/aggregate.yaml), [Reference](https://help.aliyun.com/zh/sls/aggregate-function) |
| Approximate functions | `approx_distinct`, `approx_percentile` | Estimate distinct counts and percentiles such as P95/P99. | [Local reference](functions/approximate.yaml), [Reference](https://help.aliyun.com/zh/sls/approximate-functions) |
| Date and time functions | `date_format`, `date_parse`, `date_add`, `date_trunc`, `date_diff`, `from_unixtime` | Format or parse time, add intervals, align time buckets, calculate differences, and convert Unix timestamps. | [Local reference](functions/datetime.yaml), [Reference](https://help.aliyun.com/zh/sls/date-and-time-functions-1) |
| String functions | `concat`, `split_part`, `replace`, `lower` | Join text, extract a delimited part, replace text, and normalize case. | [Local reference](functions/string.yaml), [Reference](https://help.aliyun.com/zh/sls/string-functions-1) |
| Period comparison functions | `compare` | Compare a result with an earlier time period, such as a day or week earlier. | [Local reference](functions/comparison.yaml), [Reference](https://help.aliyun.com/zh/sls/interval-valued-and-periodicity-valued-comparison-functions) |
| Regular expression functions | `regexp_like`, `regexp_extract_all` | Test a pattern or extract all matching substrings. | [Local reference](functions/regex.yaml), [Reference](https://help.aliyun.com/zh/sls/regular-expression-functions-1) |
| JSON functions | `json_extract_scalar`, `json_parse`, `json_array_length` | Extract scalar values, parse JSON text, and count array elements. | [Local reference](functions/json.yaml), [Reference](https://help.aliyun.com/zh/sls/json-functions) |
| Data type conversion functions | `cast` | Convert values to the type needed by an expression. | [Local reference](functions/type_conversion.yaml), [Reference](https://help.aliyun.com/zh/sls/data-type-conversion-functions) |
| Conditional expressions | `if`, `coalesce`, `TRY` | Choose values by condition, handle NULL, and recover from expression evaluation errors. | [Local reference](functions/conditional.yaml), [Reference](https://help.aliyun.com/zh/sls/conditional-expressions) |

Other categories: [arrays](functions/array.yaml), [binary](functions/binary.yaml),
[bitwise](functions/bitwise.yaml), [colors](functions/color.yaml),
[unit conversion](functions/conversion.yaml), [encoding](functions/encoding.yaml),
[geographic](functions/geo.yaml), [geospatial](functions/geospatial.yaml),
[hash](functions/hash.yaml), [HyperLogLog](functions/hyperloglog.yaml),
[IP geolocation](functions/ip_geo.yaml), [lambda](functions/lambda.yaml),
[Map](functions/map.yaml), [math](functions/math.yaml), [mobile numbers](functions/mobile.yaml),
[operators](functions/operators.yaml), [statistics](functions/statistical.yaml),
[URL](functions/url.yaml), [windows](functions/window.yaml),
[window funnels](functions/window_funnel.yaml).

For statement structure, see the [SQL clause reference](https://help.aliyun.com/zh/sls/sql-syntax/).

## Result limits and pagination

Assess [result precision](../query-execution.md#result-precision) separately from row limits.

Omitting `LIMIT` is equivalent to `LIMIT 100` for the returned row count. This limits result
rows, not the logs used to calculate an aggregate. A `Complete` response with 100 rows does
not establish that all result rows were returned.

Use:

- `LIMIT count` to select the first result rows.
- `LIMIT offset, count` to select a result page; the offset starts at 0.
- `LIMIT ALL` to return all result rows without the default 100-row limit.

```sql
* | SELECT request_uri, request_time
ORDER BY request_time DESC
LIMIT 100, 100
```

For repeatable pages, keep the search condition, query time range, and `ORDER BY` unchanged;
include a tie-breaker when the ordering columns can have equal values.

The documented bounds for numeric limits are:

| Form | Bounds |
| --- | --- |
| `LIMIT count` | `count`: 0–1,000,000 |
| `LIMIT offset, count` | `offset`: 0–1,000,000; `count`: 0–10,000; their sum must not exceed 1,000,000 |

The offset form is for final results and is not supported inside a subquery. SLS uses this
comma-separated form rather than `LIMIT count OFFSET offset`.

`LIMIT ALL` removes the default 100-row cap; execution and response-size limits still apply. The
[official indexed-analysis limits](https://help.aliyun.com/zh/sls/query-and-analyze-logs-in-index-mode/)
include a maximum result size of 100 MB. Calculation completeness and the number of rows
returned are separate concerns.

## Related queries

[StoreViews](https://help.aliyun.com/zh/sls/dataset-storeview-overview) provide joint queries over
associated Logstores or MetricStores. SQL can also join log data with configured external
sources; see [Logstore and MySQL joins](https://help.aliyun.com/zh/sls/join-queries-on-a-logstore-and-a-mysql-database).

## References

- [SQL syntax and examples](https://help.aliyun.com/zh/sls/sql-syntax-and-functions/)
- [Indexed analysis requirements and limits](https://help.aliyun.com/zh/sls/query-and-analyze-logs-in-index-mode/)
- [LIMIT](https://help.aliyun.com/zh/sls/limit-clause)
