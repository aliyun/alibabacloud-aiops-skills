# SPL for charts

Use SPL for extraction, typed filtering and scan aggregation. Indexed predicates before
the first pipe narrow the input; query-time extraction does not create a persistent index.
Ordinary scanned fields are text, while reserved time fields remain numeric.
For quoting, regex and conversions, see [SPL syntax](../../query/spl/README.md#basic-syntax)
and [scan field types](../../query/spl/README.md#types-in-scan-execution).

## Extraction and field cleanup

Expand a JSON string in `content`, then retain fields from the expanded object:

```spl
* | parse-json content
  | project __time__, status, requestId, errorMessage
```

For regex extraction, renaming and derived fields, see the
[pipeline commands](../../query/spl/README.md#high-frequency-commands).

## Aggregation and sorting

SPL uses `stats output = aggregate(...) by dimension`, followed by `sort` and `limit`.
Preparing derived fields with `extend` makes their types and reuse explicit; aggregate
arguments can also contain expressions. See [stats](../../query/spl/commands/stats.yaml)
and [pipeline order](../../query/spl/README.md#typical-pipeline-order) for details.

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

For CLI execution and result precision, see [query execution](../../query/query-execution.md#logstore).
SPL string rules and JSON escaping both apply when embedding expressions in Dashboard JSON.
[Scan SQL](sql.md#scan-sql) is a separate query form.
Log-view predefined processing has its own supported operators; query-time SPL
operators are not automatically available there.

[Official SPL documentation](https://help.aliyun.com/zh/sls/user-guide/spl-overview)
