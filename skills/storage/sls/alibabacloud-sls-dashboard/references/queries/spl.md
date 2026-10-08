# SLS SPL

Use SPL for extraction, typed filtering, JSON expansion, field cleanup and scan
aggregation when indexed SQL does not provide the required fields. Retain the initial
search scope: indexed predicates go before the first pipe; subsequent SPL stages process
rows in order; derived fields are available to later stages. Query-time extraction does
not create a persistent index.

## Contents

- [Types, strings and regular expressions](#types-strings-and-regular-expressions)
- [Extraction and field cleanup](#extraction-and-field-cleanup)
- [Aggregation and sorting](#aggregation-and-sorting)
- [Execution and chart binding](#execution-and-chart-binding)

## Types, strings and regular expressions

Ordinary log fields are `VARCHAR`; `__time__` and `__time__ns_part__` are `BIGINT`.
Convert ordinary fields before numeric comparison or aggregation, using
`cast(field as BIGINT)`, `cast(field as DOUBLE)` or `try_cast` for the intended
numeric type.

Use single quotes for strings and double quotes for special field names, such as
`"properties.agent_version"`. SPL does not expand string escapes: `'\n'` contains
a literal backslash and `n`. Use `chr(10)` when an expression needs a newline.

Regular expressions use RE2, which does not support lookarounds or backreferences. Use
single backslashes in a raw SPL pattern, as in `'(\d+)\s(\w+)'`. Escape each backslash
when embedding the query in a JSON string.

## Extraction and field cleanup

Expand a JSON string in `content`, then retain fields from the expanded object:

```spl
* | parse-json content
  | project __time__, status, requestId, errorMessage
```

Extract a numeric code and the following word from `message`:

```spl
* | parse-regexp message, '(\d+)\s(\w+)' as code, method
  | project __time__, code, method, message
```

Rename fields with `project-rename new=old`, remove unwanted fields with
`project-away`, and keep an explicit output set with `project`:

```spl
* | project-rename source=__source__
  | project-away __raw__
  | project __time__, source, status, message
```

Use `extend` for derived detail columns, for example to remove URL query parameters:

```spl
* | extend path = split_part(request_uri, '?', 1)
  | project __time__, path, status, request_time
```

## Aggregation and sorting

SLS SPL uses `stats output = aggregate(field) by dimension`, not SQL `AS` or
`GROUP BY`. Use `count(*)` for row counts; other aggregate arguments must be fields,
not embedded expressions. Compute conversions, arithmetic, extracted values and
time buckets before `stats`. Use SPL `sort`, not SQL `ORDER BY`, and establish
output columns with `stats` or `project` before sorting and limiting.

For the 20 services with the most server errors, convert status before filtering,
then sort the counts before limiting:

```spl
* | extend status_num = try_cast(status as BIGINT)
  | where status_num >= 500
  | stats errors = count(*) by service
  | sort errors desc
  | limit 20
```

For latency stored in milliseconds, convert once and aggregate the resulting field:

```spl
* | extend latency_ms = try_cast(latency as BIGINT)
  | stats avg_latency = avg(latency_ms), max_latency = max(latency_ms) by api
  | sort avg_latency desc
  | limit 20
```

For a minute trend, compute numeric second buckets before grouping and sort by time:

```spl
* | extend time = __time__ - __time__ % 60
  | stats logs = count(*) by time
  | sort time asc
  | limit 10000
```

Bind `time` as the time field and `logs` as the numeric value. The limit caps
output rows, not scanned rows. Read [time, step and result limits](time-and-limits.md)
when selecting the query window, bucket size and row budget.

## Execution and chart binding

Use bounded detail output for inspection and explicit aggregation for TopN and
trends. Match output names to chart bindings and table `fieldOptions[].name`.
Preserve fixed constraints when adding token templates, and narrow scans with
available indexed predicates and a bounded query window.

Use `--language spl` for query verification and report partial scan progress.
[Scan SQL](sql.md#scan-sql) uses `set session mode=scan; SELECT ...`, not SPL syntax.
Log-view predefined processing has its own supported operators; query-time SPL
operators are not automatically available there.

[Official SPL documentation](https://help.aliyun.com/zh/sls/user-guide/spl-overview)
