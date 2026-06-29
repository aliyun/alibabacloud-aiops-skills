# SPL Usage Guide

## 1. SPL Scope

- This skill covers only SPL for scan queries within the query & analysis context
- Does not cover Logtail collection processing, write processors, real-time consumption, data transformation, or other non-query scenarios

## 2. Basic Syntax

```text
<data-source> | <spl-cmd> | <spl-cmd> | ...
```

- In query & analysis, the common data source is `*`
- For scan queries, `<data-source>` can also be an index search statement
- If `<data-source>` is an index search statement, it filters data first, then passes results to subsequent SPL commands
- SPL cannot follow SQL in a pipeline, and vice versa
- Trailing semicolons are optional

## 3. Must-Know Rules for SPL

- Fields are `VARCHAR` by default
- Always `cast()` / `try_cast()` before numeric comparison or arithmetic
- String constants use single quotes
- Field names containing `.` `:` `-` or spaces must be double-quoted
- In non-scan scenarios, field names are case-sensitive by default
- SPL does not process escape sequences; `\n` is a literal, not a newline
- Regex uses RE2 engine — back-references and lookaround are not supported

## 4. Recommended Pipeline Order

```text
where -> parse -> extend -> project
```

For scan aggregation scenarios:

```text
where -> parse -> extend -> stats -> sort -> limit
```

## 5. High-Frequency Commands

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

Key limitations:
- Aggregate functions inside `stats` can only operate directly on fields, not on expressions
- If you need `sum(cast(bytes as BIGINT))`, compute the field in `extend` first, then aggregate
- Although `stats` can do aggregation, in query & analysis scenarios, unless the user explicitly requests SPL or the context is already a scan/pipeline workflow, default to SQL for analysis

### `sort` / `limit`
Sorts and truncates aggregation results.

## 6. When to Prefer Scan Query SPL

- The target field has no index but ad-hoc analysis is needed
- Row-level `parse` / `extend` / `stats` pipeline processing is required
- More flexible filtering is needed in a scan scenario to replace index search

If only standard aggregation is needed and the field has both index and statistics, prefer standard SQL — do not default to SQL SCAN.
If some filter conditions can be expressed in index search syntax, pre-filter before `|`, then append SPL.

## 7. Handling Dotted Field Names

If a field name contains `.`, first determine whether it is a JSON sub-key's index representation rather than the actual field name.
Common alternative:

```spl
* | where json_extract_scalar(fieldA, '$.xxx') = 'value'
```

## Source YAMLs

- `./spl/overview.yaml`
- `./spl/where.yaml`
- `./spl/extend.yaml`
- `./spl/parse-json.yaml`
- `./spl/parse-regexp.yaml`
- `./spl/parse-csv.yaml`
- `./spl/parse-kv.yaml`
- `./spl/stats.yaml`
- `./spl/sort.yaml`
- `./spl/limit.yaml`
