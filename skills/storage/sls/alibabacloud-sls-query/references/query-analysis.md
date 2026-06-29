# Query & Analysis Routing

## 1. Three Core Capabilities

- **Query**: no aggregation; returns log-level results
- Index search handles efficient log filtering with relatively limited syntax
- If matched logs need further row-level processing (field addition/removal, filtering, parse/extend/project), that belongs to SPL, not index search itself
- **Analysis**: involves aggregation — typically uses aggregate functions, GROUP BY, statistical calculations
- **Index search**: typical query syntax for filtering logs and returning raw results. Example: `status: 200 and method: GET`
- **SQL analysis**: typical analysis syntax for aggregation, grouping, statistics. Example: `status: 200 | SELECT count(*) AS pv FROM log`
- **SPL**: primarily supplements query capabilities — handles complex filtering in scan mode, row-level processing, field manipulation, and `stats` aggregation when needed. Example: `* | where status = '500' | extend latency_ms = cast(latency as BIGINT) | project latency_ms`

## 2. Selection Rules

- For query scenarios, prefer index search: highest efficiency, but limited syntax
- If a query scenario requires complex condition filtering or row-level processing (parse-json/parse-regexp/parse-kv/extend): use SPL as a supplement to index search
- For analysis scenarios, prefer SQL: suitable for count/sum/avg/GROUP BY/top-N/window analysis
- Prefer standard SQL first; only consider SQL SCAN if the target field lacks an index
- Although SPL supports `stats`, `sort`, `limit` and other aggregation commands, unless the user explicitly requests SPL or the problem is inherently a scan/pipeline scenario, default to generating SQL for analysis

## 3. Pipeline Layering Rules

- Whenever a statement contains `|`, everything before the first `|` is the index search
- This index search applies to both subsequent SPL and SQL
- Its purpose is to narrow the data range quickly using the index before further processing
- Any filter condition expressible in index search syntax should be placed before `|`
- For SQL: pre-filtering is often the key to faster execution — avoid placing filterable conditions only in the SQL portion
- For SPL: same principle — pre-filter with index search first, then do row-level processing

## 4. Prerequisites

- Both query and analysis depend on index configuration
- SQL requires the field to have statistics enabled (`doc_value: true`)
- Index and statistics typically apply only to data written after configuration; historical data requires re-indexing
- Query-type Logstores do not support statistics, therefore do not support SQL analysis
- SCAN is not "fully index-free" — the query portion still relies on available indexes and must meet minimum index conditions

## 5. Time Range

- Do not default to putting time conditions inside the query / SQL
- Time range is specified via `--from` / `--to` flags as Unix timestamps (seconds)
- `__time__` in SQL is better suited for formatting and grouping, not as the primary filter

## 6. Index Search Key Rules

- Case-insensitive
- Supports `AND` / `OR` / `NOT`
- Range queries only work on `long` / `double` field types
- Wildcard queries cannot start with `*` (prefix wildcard)
- Phrase exact match uses `#"..."`
- `key: *` means the field exists and is non-empty

## 7. SQL Key Reminders

- Syntax: `query statement | analysis statement`
- SLS SQL is based on Presto SQL
- In Logstore scenarios the default table name is `log`
- SQL does not support `LIMIT count OFFSET offset` syntax; use `LIMIT offset, count` instead for pagination (e.g., `LIMIT 20, 20` for rows 21–40)
- Default result cap is 100 rows; use `LIMIT` to retrieve more
- SQL cannot be followed by SPL
- If a filter condition can be expressed in index search before `|`, prefer pre-filtering — do not place it only in the SQL

## 8. SCAN Mode

- A fallback for analyzing fields without indexes — not the preferred approach
- Query scenarios: prefer index search first, then SPL
- Analysis scenarios: prefer standard SQL first, then SQL SCAN
- Typical syntax: `* | set session mode = scan; SELECT count(1) AS pv, api FROM log GROUP BY api`
- Limitations:
  - The query portion is still affected by index availability
  - All fields are treated as `varchar`
  - Per-shard scan row count and total scan rows are limited
  - Performance is significantly lower than index-based analysis
  - Best suited for ad-hoc analysis or recovery scenarios, not default generation

## 9. Common Response Templates

### Log Retrieval Only
```text
status: 500 and service: payment
```

### Count Errors
```sql
status: 500 | SELECT count(*) AS error_count FROM log
```

### Hourly Aggregation
```sql
status: 500 | SELECT date_format(__time__, '%Y-%m-%d %H:00:00') AS hour, count(*) AS error_count FROM log GROUP BY hour ORDER BY hour
```

### Pre-filter with Index, then SPL Processing
```spl
status: 500 and service: payment | where cast(latency as BIGINT) > 1000 | extend latency_ms = cast(latency as BIGINT) | project service, latency_ms, message
```

## Source YAMLs

- `./query_analysis/overview.yaml`
- `./query_analysis/indexSearch.yaml`
- `./query_analysis/indexConfig.yaml`
- `./query_analysis/sql.yaml`
