# SPL Queries

## Purpose and features

SPL (SLS Processing Language) processes data through a sequence of pipeline commands. In log
queries, it supports filtering, extracting structured information, computing fields, selecting
fields, and aggregation. Data processing also uses SPL.

SPL query execution can use indexes when the referenced fields have field indexes with
analytics enabled (`doc_value: true`); otherwise it uses scan execution. The search before the first pipe can
still use existing indexes to reduce the input.

## Basic syntax

```text
index_search_statement | spl_command | spl_command ...
```

`spl_pipeline` denotes one or more `spl_command` stages joined by pipes.

The first part is the index-search condition. Use `*` when no indexed filter is needed.
Each subsequent command processes the preceding stage's result. A trailing semicolon is optional.

For example, filter using the indexed `Status` field, then filter an unindexed `ClientIp`:

```spl
Status:200 | where ClientIp = '192.168.1.1'
```

String constants use single quotes. Field names containing special characters use double
quotes:

```spl
* | project-away "user-agent"
```

In ordinary SPL string literals, backslashes are preserved: `\n` is literal text, not a newline.
Regex uses the RE2 engine; back-references and lookaround are not supported.


A pipeline stage is a command with its own parameters and expressions. SPL pipelines and SQL
statements are separate forms: do not append a SQL statement after SPL commands or vice versa.
SPL can also use named datasets as inputs; `$<dataset-name>` references one. `--` starts a
single-line comment.

Field names in scan queries are case-insensitive. Other SPL processing scenarios use
case-sensitive names. Quote the complete field name when it contains punctuation, including
`"__tag__:hostname"` and `"__tag__:__path__"`. Reserved names such as `__time__`, `__source__`,
and `__topic__` do not require quotes.

For an actual newline in an expression, use `chr(10)`, for example:

```spl
* | extend x=split(column, chr(10))
```

See the [string functions](functions/string.yaml) for text processing.
`extend` can also create structured fields such as arrays, maps, and JSON; see
[array functions](functions/array.yaml), [map functions](functions/map.yaml), and
[lambda expressions](functions/lambda.yaml).

## Typical Pipeline Order

```text
where -> parse -> extend -> project
```

Filters that depend on extracted or computed fields belong after the corresponding
`parse` or `extend` stage.

For aggregation in SPL queries:

```text
where -> parse -> extend -> stats -> sort -> limit
```

## High-Frequency Commands

### `where`
Filters rows by a boolean expression.

```spl
* | where status = '500'
* | where cast(status as BIGINT) >= 500
```

### `extend`
Computes new fields; use this for complex expressions.

```spl
* | extend latency_ms = try_cast(latency as BIGINT)
```

### `parse-json` / `parse-regexp` / `parse-csv` / `parse-kv`
Extracts structured fields from semi-structured text fields.

### `stats`
Performs aggregation.

```spl
* | stats pv = count(*) by ip
* | extend latency_ms = try_cast(latency as BIGINT) | stats avg_latency = avg(latency_ms) by api
```

Although `stats` can do aggregation, in query & analysis scenarios, unless the user explicitly requests SPL or the context is already a scan/pipeline workflow, default to SQL for analysis.

### `sort` / `limit`
Sorts rows and limits the result size.

### `project` / `project-away` / `project-rename`

- `project`: retain selected fields and optionally rename them.
- `project-away`: remove selected fields.
- `project-rename`: rename selected fields.

## High-Frequency Functions

The categories follow the [official SPL function overview](https://help.aliyun.com/zh/sls/spl-instructions-and-functions/).
The table lists representative functions for SPL. Aggregate functions are used in `stats`.

| Category | Representative functions | Purpose | Details |
| --- | --- | --- | --- |
| Aggregate functions | `count`, `sum`, `avg`, `max` | Count records and calculate totals, averages, and maxima in `stats`. | [Local details](functions/aggregate.yaml) · [stats](https://help.aliyun.com/zh/sls/aggregation-instructions) · [Functions](https://help.aliyun.com/zh/sls/aggregate-function) |
| Approximate functions | `approx_distinct`, `approx_percentile` | Estimate distinct counts and percentiles in `stats`. | [Local details](functions/approximate.yaml) · [stats](https://help.aliyun.com/zh/sls/aggregation-instructions) · [Functions](https://help.aliyun.com/zh/sls/approximate-functions) |
| Date and time functions | `date_format`, `date_parse`, `date_diff`, `from_unixtime` | Format or parse time, calculate time differences, and convert Unix timestamps. | [Local details](functions/datetime.yaml) · [Reference](https://help.aliyun.com/zh/sls/date-and-time-functions-1) |
| String functions | `concat`, `split_part`, `replace`, `lower` | Join text, extract a delimited part, replace text, and normalize case. | [Local details](functions/string.yaml) · [Reference](https://help.aliyun.com/zh/sls/string-functions-1) |
| Regular expression functions | `regexp_like` | Test whether text matches a regular expression. | [Local details](functions/regex.yaml) · [Reference](https://help.aliyun.com/zh/sls/regular-expression-functions-1) |
| JSON functions | `json_extract_scalar` | Extract a scalar value from JSON by path. | [Local details](functions/json.yaml) · [Reference](https://help.aliyun.com/zh/sls/json-functions) |
| Data type conversion functions | `cast` | Convert values to the type needed by an expression. | [Local details](functions/type_conversion.yaml) · [Reference](https://help.aliyun.com/zh/sls/data-type-conversion-functions) |
| Conditional expressions | `if`, `coalesce` | Choose a value by condition or use the first non-null value. | [Local details](functions/conditional.yaml) · [Reference](https://help.aliyun.com/zh/sls/conditional-expressions) |


Other function details: [math](functions/math.yaml), [operators](functions/operators.yaml),
[arrays](functions/array.yaml), [maps](functions/map.yaml), [lambda expressions](functions/lambda.yaml),
[URLs](functions/url.yaml), [encoding](functions/encoding.yaml), [hashes](functions/hash.yaml),
and [IP geolocation](functions/ip_geo.yaml).

## Types in scan execution

Ordinary scanned fields are text (`varchar`), including fields that also have indexes.
Convert text before numeric comparison or arithmetic:

```spl
Status:200 | where cast(RT as bigint) > 50
```

After a field is converted with `extend`, subsequent stages use its new type. The reserved
time fields `__time__` and `__time_ns_part__` remain `INTEGER` or `BIGINT`, as described in the
[general reference](https://help.aliyun.com/zh/sls/spl-general-reference).

## Handling Dotted Field Names

If a field name contains `.`, first determine whether it is a JSON sub-key's index representation rather than the actual field name.
Common alternative:

```spl
* | where json_extract_scalar(fieldA, '$.xxx') = 'value'
```

## Scan limits

A single scan returns when any of the following occurs:

- It reaches the requested number of results.
- It reaches the per-request scan limit, documented as 100,000 logs by default after indexed filtering.
- It has scanned for 45 seconds.

### Aggregated SPL results

For SPL query analysis, `sort` and `limit` order and select result rows. See
[aggregation commands](https://help.aliyun.com/zh/sls/aggregation-instructions).

The [basic SPL syntax reference](https://help.aliyun.com/zh/sls/basic-spl-syntax) describes additional
script and runtime limits by execution scenario.

## Command details

- [where](commands/where.yaml)
- [extend](commands/extend.yaml)
- [parse-json](commands/parse-json.yaml)
- [parse-regexp](commands/parse-regexp.yaml)
- [parse-csv](commands/parse-csv.yaml)
- [parse-kv](commands/parse-kv.yaml)
- [stats](commands/stats.yaml)
- [sort](commands/sort.yaml)
- [limit](commands/limit.yaml)
- [project](commands/project.yaml)
- [project-away](commands/project-away.yaml)
- [project-rename](commands/project-rename.yaml)
- [pack-fields](commands/pack-fields.yaml)

## References

- [Scan query syntax and limits](https://help.aliyun.com/zh/sls/scan-query-syntax)
- [Basic SPL syntax](https://help.aliyun.com/zh/sls/basic-spl-syntax)
- [SPL commands and functions](https://help.aliyun.com/zh/sls/spl-instructions-and-functions/)
- [SPL general reference](https://help.aliyun.com/zh/sls/spl-general-reference)
