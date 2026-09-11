> Loaded on demand — MaxCompute dialect divergences from standard SQL (functions, types, syntax, SET params). Skip unless the agent is generating a SELECT or debugging a syntax/type error.

# MaxCompute SELECT dialect rules

Read this file before generating a MaxCompute SELECT query. It covers selected MaxCompute differences from standard SQL: unsupported patterns, function-name mapping, type traps, extension syntax, and SET parameters. Runtime errors and current official documentation take precedence when a project or version differs.

> **How this fits with the other files**: when converting natural language to a SELECT, [text2sql-principles.md](text2sql-principles.md) handles logical planning (intent, granularity, schema mapping, output contract); the final SQL is written directly as MaxCompute-executable syntax — do not produce an intermediate ANSI-SQL draft. For partition format, partition discovery, and full-scan policy, see [partition-guide.md](partition-guide.md). For ready-made query templates, see [sql-query-patterns.md](sql-query-patterns.md).

> **About the examples**: to highlight dialect syntax, some examples in this file use `SELECT *`. The text2sql output should still follow [text2sql-principles.md](text2sql-principles.md): unless the user explicitly asks for all columns, or template semantics require all columns, list explicit field names.

Values in angle brackets are unresolved placeholders. Replace them from verified schema, date, and business context before execution. Preserve the user's requested output shape and row count; do not invent a limit or business rule.

---

## 1. Patterns that do not work

The following patterns error out on MaxCompute. Each entry includes the error code and reason.

### 1.1 `ORDER BY` requires `LIMIT` by default

`odps.sql.validate.orderby.limit=true` is the default; when SQL contains `ORDER BY` it must be paired with `LIMIT`, otherwise submission validation fails. Do not add a gratuitous `LIMIT`: it changes the requested result. Use the user's row count for ranked or bounded output. If the user requires an unbounded ordered result and accepts the resource cost, disable the check for that session only:

- Session level: `SET odps.sql.validate.orderby.limit=false;`

Note: `ORDER BY` cannot coexist with `DISTRIBUTE BY` / `SORT BY`.

```sql
-- DON'T (default mode errors)
SELECT * FROM orders WHERE dt = '<partition-value>' ORDER BY amount DESC;

-- DO for a user-requested bounded result
SELECT * FROM orders WHERE dt = '<partition-value>' ORDER BY amount DESC LIMIT <row-count>;
```

### 1.2 Type cast: `CAST` only, no `::type` shorthand

```sql
-- DON'T
SELECT col::BIGINT FROM t;

-- DO
SELECT CAST(col AS BIGINT) FROM t;
```

### 1.3 Top N rows: `LIMIT`, no `SELECT TOP N`

```sql
-- DON'T
SELECT TOP 10 * FROM t;

-- DO
SELECT * FROM t LIMIT 10;
```

### 1.4 Case-insensitive match: `LOWER + LIKE`, no `ILIKE`

```sql
-- DON'T
SELECT * FROM t WHERE name ILIKE '%zhang%';

-- DO
SELECT * FROM t WHERE LOWER(name) LIKE '%zhang%';
```

### 1.5 String concatenation: `CONCAT` or `||`

`+` is the numeric operator and cannot concatenate strings.

```sql
SELECT CONCAT('a', 'b');   -- returns 'ab'
SELECT 'a' || 'b';         -- returns 'ab'
```

### 1.6 NULL test: `IS NULL` only

```sql
-- DON'T
SELECT * FROM t WHERE col = NULL;

-- DO
SELECT * FROM t WHERE col IS NULL;
```

### 1.7 `WHERE` cannot reference SELECT aliases

```sql
-- DON'T
SELECT amount * 0.1 AS tax FROM orders WHERE tax > 10;

-- DO
SELECT amount * 0.1 AS tax FROM orders WHERE amount * 0.1 > 10;
-- or use a subquery
SELECT * FROM (SELECT amount * 0.1 AS tax FROM orders) tmp WHERE tax > 10;
```

### 1.8 `SUM(boolean expression)` does not work

MaxCompute has no implicit `bool→int` conversion; `SUM(condition)` errors with `function sum cannot match any overloaded functions with (BOOLEAN)`. Use `CASE WHEN` or `COUNT_IF` instead.

```sql
-- DON'T: SUM(bool) does not work
SELECT SUM(status = 'A') FROM orders;
SELECT SUM(gender_id = 1) FROM superhero;

-- DO: use CASE WHEN or COUNT_IF
SELECT SUM(CASE WHEN status = 'A' THEN 1 ELSE 0 END) FROM orders;
SELECT SUM(CASE WHEN gender_id = 1 THEN 1 ELSE 0 END) FROM superhero;
```

---

## 2. Function-name mapping

This section lists MaxCompute function differences vs. other databases. "Either works" indicates that multiple spellings are supported.

### Date / time

For the **current time**, `GETDATE()`, `NOW()`, and `CURRENT_TIMESTAMP()` all work:
```sql
SELECT GETDATE();            -- returns DATETIME
SELECT NOW();                -- returns DATETIME
SELECT CURRENT_TIMESTAMP();  -- returns TIMESTAMP (parentheses required)
```

For **date formatting**, **prefer `TO_CHAR(d, fmt)`** (works across input types by default). `DATE_FORMAT` exists but has SET preconditions:

| Input type | `DATE_FORMAT` precondition | `TO_CHAR` |
|---|---|---|
| TIMESTAMP | `SET odps.sql.type.system.odps2=true;` | ✓ default |
| STRING / DATE / DATETIME | `SET odps.sql.hive.compatible=true;` | ✓ default |

```sql
-- TO_CHAR without a compatibility SET switch
SELECT TO_CHAR(create_time, 'yyyy-mm-dd');

-- DATE_FORMAT requires SET first
SET odps.sql.hive.compatible=true;
SELECT DATE_FORMAT(create_time, 'yyyy-MM-dd');
```

**Note the format-string conventions differ**:
- `TO_CHAR` uses Oracle-style lowercase `yyyy-mm-dd hh:mi:ss` (`mi`=minute).
- `DATE_FORMAT` uses Java SimpleDateFormat style `yyyy-MM-dd HH:mm:ss` (`HH`=24h, `mm`=minute; in non-Hive mode `mm`=month).

For **string→date**, use `TO_DATE(s, fmt)`:
```sql
-- DON'T
SELECT STR_TO_DATE('2024-01-15', '%Y-%m-%d');

-- DO
SELECT TO_DATE('2024-01-15', 'yyyy-mm-dd');
```

**Date arithmetic** uses `DATEADD(date, delta, unit)`; MaxCompute has no `DATE_ADD ... INTERVAL`:
```sql
-- DON'T
SELECT DATE_ADD(create_time, INTERVAL 7 DAY);

-- DO
SELECT DATEADD(create_time, 7, 'dd');
```

For **date difference**, use `DATEDIFF(d1, d2, unit)`; the third argument is optional (default day):
```sql
SELECT DATEDIFF(end_date, start_date, 'dd');   -- explicit day
SELECT DATEDIFF(end_date, start_date);         -- default also day
```

For **extracting year/month/day/hour**, use `YEAR(d)` / `MONTH(d)` / `DAY(d)` / `HOUR(d)` or `DATEPART(d, unit)`:
```sql
SELECT YEAR(create_time), MONTH(create_time), DAY(create_time);
-- or
SELECT DATEPART(create_time, 'yyyy'), DATEPART(create_time, 'mm');
```

For **date truncation**, use `DATETRUNC(d, unit)` or `DATE(d)` / `TO_DATE(d)`:
```sql
SELECT DATETRUNC(create_time, 'mm');  -- truncate to month (returns first of month)
SELECT DATETRUNC(create_time, 'dd');  -- truncate to day
SELECT DATE(create_time);             -- truncate to day (shorthand)
SELECT TO_DATE(create_time);          -- truncate to day (shorthand)
```
Note: in default mode `TRUNC` is the numeric truncation function (e.g. `TRUNC(125.815, 0)` → 125.0), not for dates. In Hive-compatible mode `TRUNC(d, unit)` works on dates.

> Easily confused functions:
> - **`DATETRUNC(d, unit)`** — DQL date-truncation function (this section).
> - **`TRUNC_TIME(d, unit)`** — DDL `AUTO PARTITIONED BY` only, **used only inside CREATE TABLE statements**.
>
> Their names differ by one underscore and the units differ (`DATETRUNC` uses short names like `'dd'`, `TRUNC_TIME` uses long names like `'day'`).

Other date functions:
- `UNIX_TIMESTAMP(d)` — to Unix timestamp
- `FROM_UNIXTIME(ts)` — Unix timestamp to date (single argument; format with `TO_CHAR`)
- `LAST_DAY(d)` — month-end date (returns STRING)
- `LASTDAY(d)` — month-end date (returns DATETIME, the classic function)
- `WEEKDAY(d)` — day of week (0=Mon, 6=Sun)
- `WEEKOFYEAR(d)` — ISO week number

### Strings

For **group concatenation**, use `WM_CONCAT(sep, col)` (separator first):
```sql
SELECT WM_CONCAT(',', name) FROM t GROUP BY dept;
SELECT WM_CONCAT(',', name) WITHIN GROUP (ORDER BY name) FROM t GROUP BY dept;  -- ordered
-- GROUP_CONCAT is unavailable
```

For **substring position**, both `INSTR(str, sub)` and `LOCATE(sub, str)` work — note the argument order is reversed:
```sql
SELECT INSTR(name, 'abc');    -- haystack first, needle second
SELECT LOCATE('abc', name);   -- needle first, haystack second
```

For **regex extraction**, both `REGEXP_EXTRACT` and `REGEXP_SUBSTR` work:
```sql
SELECT REGEXP_EXTRACT(text, '(\\d+)', 1);              -- extract capture group
SELECT REGEXP_SUBSTR(text, '\\d+');                     -- return matched substring
SELECT REGEXP_SUBSTR(text, '\\d+', 1, 2);              -- 2nd match starting at position 1
```

For **string split**, use `SPLIT(str, sep)` (returns ARRAY); take a specific segment with `SPLIT_PART(str, sep, index)`:
```sql
SELECT SPLIT('a,b,c', ',');            -- returns ARRAY ['a','b','c']
SELECT SPLIT_PART('a,b,c', ',', 2);   -- returns 'b'
```

### Aggregation and conditional

**NULL replacement** uses `NVL(expr, default)` or `COALESCE`; `IFNULL` is not registered in MaxCompute:
```sql
-- DON'T
SELECT IFNULL(amount, 0) FROM orders;

-- DO
SELECT NVL(amount, 0) FROM orders;
```

For **conditional count**, besides `SUM(CASE WHEN)`, you can use `COUNT_IF(condition)`:
```sql
SELECT COUNT_IF(status = 'active') FROM users;  -- equivalent to SUM(CASE WHEN ... THEN 1 ELSE 0 END)
```

For **value-at-extreme**, use `MAX_BY` / `MIN_BY`:
```sql
-- Top earner per department
SELECT dept, MAX_BY(name, salary) AS top_earner FROM emp GROUP BY dept;
-- Most recent order amount per user
SELECT user_id, MAX_BY(amount, create_time) AS latest_amount FROM orders GROUP BY user_id;
```

For **collect into array**, use `COLLECT_LIST` or `COLLECT_SET` (officially documented):
```sql
SELECT COLLECT_LIST(product_id) FROM orders GROUP BY user_id;   -- with duplicates
SELECT COLLECT_SET(product_id) FROM orders GROUP BY user_id;    -- deduplicated
```

### JSON

For a JSON value stored as `STRING`, `GET_JSON_OBJECT(json_str, path)` operates directly on the column and needs no JSON-type SET switch.
```sql
-- DO
SELECT GET_JSON_OBJECT(log, '$.user_id');
SELECT GET_JSON_OBJECT(log, '$.user.name');                -- nested
SELECT GET_JSON_OBJECT(log, '$.items[0].id');              -- array element

-- DON'T
SELECT log->>'user_id';                    -- PostgreSQL syntax not supported
SELECT JSON_EXTRACT(log_str, '$.k');       -- first arg must be JSON type, not STRING (raises 0130121)
```

**JSON-type path (`JSON_EXTRACT` / JSON literal / `CAST(... AS JSON)`)** — requires explicitly enabling the JSON type system:
```sql
SET odps.sql.type.json.enable=true;
SELECT JSON_EXTRACT(CAST(log_str AS JSON), '$.k') FROM t;  -- CAST to JSON first, then _EXTRACT
SELECT JSON '{"a": 1}' AS j;                                -- JSON literal
```
Without it, `JSON_EXTRACT(STRING, ...)` raises `ODPS-0130121: invalid type STRING of argument 1 for function json_extract, expect JSON`.

For extracting multiple JSON fields, `JSON_TUPLE` with `LATERAL VIEW` is also available:
```sql
SELECT t.id, j.user_id, j.action
FROM logs t
LATERAL VIEW JSON_TUPLE(t.log, 'user_id', 'action') j AS user_id, action;
```

### Type cast

Use `CAST(expr AS type)` only; the target type uses MaxCompute type names (not MySQL-style CHAR/SIGNED):
```sql
CAST(col AS STRING)         -- to string (NOT CAST AS CHAR / CAST AS TEXT)
CAST(col AS BIGINT)         -- to integer (NOT CAST AS SIGNED / CAST AS INTEGER)
CAST(col AS DOUBLE)         -- to float
CAST(col AS DECIMAL(10,2))  -- to fixed-point
```

---

## 3. Date format strings

In MaxCompute date format strings, **`mm` is month and `mi` is minute**. This is the most common mistake.

```sql
-- Correct format strings
TO_CHAR(d, 'yyyy-mm-dd')           -- 2024-01-15 (mm=month)
TO_CHAR(d, 'yyyy-mm-dd hh:mi:ss')  -- 2024-01-15 14:30:00 (mi=minute)
TO_CHAR(d, 'yyyymmdd')             -- 20240115

-- DON'T: writing minute as mm
TO_CHAR(d, 'yyyy-mm-dd hh:mm:ss')  -- WRONG! mm is month, outputs 2024-01-15 14:01:00
```

Format-character cheat: `yyyy`=year, `mm`=month, `dd`=day, `hh`=hour, `mi`=minute, `ss`=second.

### Three time-unit kits (important: not interchangeable across functions)

MaxCompute has three time-unit string conventions; you must pick by function — **mixing them errors out**:

| Function | Accepted units | Notes |
|---|---|---|
| `DATEADD` / `DATEDIFF` | `yyyy/year`, `quarter/q`, `mm/month/mon`, `week/w`, `dd/day`, `hh/hour`, `mi`, `ss`, `ff3` (ms), `ff6` (μs) | short or long names work |
| `DATEPART` | **stable**: `yyyy/year`, `mm/month`, `dd/day`, `hh/hour`, `mi`, `ss`, `ff3` (ms); avoid `quarter/q`, `week/w`, `ff6` | narrower subset than DATEADD |
| `TO_CHAR` / `TO_DATE` format string | `yyyy/mm/dd/hh/mi/ss` | **short names only** (`mm`=month, `mi`=minute) |
| `TRUNC_TIME` | `year/month/day/hour` | **long names only**; `'dd'` / `'mm'` errors |
| `DATETRUNC` | `yyyy/mm/dd/hh/mi/ss/ff3`, also `quarter/week` | short names (consistent with DATEADD); broader than TRUNC_TIME |

```sql
-- DON'T: TRUNC_TIME does not accept short names
TRUNC_TIME(event_time, 'dd')   -- error: invalid datePart

-- DO
TRUNC_TIME(event_time, 'day')  -- correct
DATETRUNC(event_time, 'dd')    -- correct (DATETRUNC uses short names)
```

---

## 4. Type traps

### `STRING` vs numeric: explicit `CAST`

```sql
-- DON'T: implicit conversion may lose precision
SELECT * FROM t WHERE string_col > 2;

-- DO
SELECT * FROM t WHERE CAST(string_col AS BIGINT) > 2;
```

### `DECIMAL(precision, scale)` requires DECIMAL 2.0 configuration

`DECIMAL(p,s)` (precision/scale-bearing DECIMAL) errors when DECIMAL 2.0 is not
enabled. Current public documentation enables both the ODPS 2.0 type system and
DECIMAL 2.0; verify project policy before changing session settings.

```sql
SET odps.sql.type.system.odps2=true;
SET odps.sql.decimal.odps2=true;
SELECT CAST(1.1 AS DECIMAL(10,2));   -- works after enabling
```

### Do not mix `DECIMAL` with `DOUBLE`

```sql
-- DON'T: 2.2 is a DOUBLE literal, demoting the whole expression to DOUBLE
SELECT CAST(1.1 AS DECIMAL(10,2)) + 2.2;

-- DO: keep all operands as DECIMAL
SELECT CAST(1.1 AS DECIMAL(10,2)) + CAST(2.2 AS DECIMAL(10,2));
```

### Preserve governed precision in DECIMAL arithmetic

Literal types and DECIMAL result precision depend on the project's data-type
and DECIMAL settings. Do not assume an integer literal is incompatible with a
DECIMAL expression or that one cast shape is universally correct.

```sql
-- Exact precision requirements come from the verified amount type and metric definition
SELECT amount / 100 FROM orders;
```

Choose any explicit precision and scale from the governed table schema,
currency or measurement standard, or explicit user confirmation. When the
result type matters, verify it with `query explain` or a bounded validation
query in the active project. Do not impose a universal currency precision.

---

## 5. MaxCompute-specific functions

This chapter lists MaxCompute-specific functions beyond the function-name mappings in §2.

### Array operations
```sql
ARRAY_CONTAINS(tags, 'vip')           -- contains check
SIZE(arr_col)                          -- array length
SORT_ARRAY(arr_col)                    -- sort
ARRAY_DISTINCT(arr_col)                -- dedup
ARRAY_JOIN(arr_col, ',')               -- join into string
```

### MAP operations
```sql
properties['city']                     -- subscript access
MAP_KEYS(map_col)                      -- all keys
MAP_VALUES(map_col)                    -- all values
STR_TO_MAP('k1=v1&k2=v2', '&', '=')  -- string to MAP
```

### Other
```sql
DECODE(status, 1, 'A', 2, 'B', 'unknown')  -- shorthand similar to CASE WHEN
APPROX_DISTINCT(user_id)              -- approximate distinct; use only when approximation is acceptable
CONCAT_WS(',', a, b, c)               -- separator-joined concat (**any NULL arg → whole result NULL**, unlike MySQL/Hive)
REGEXP_COUNT(s, '\\d+')               -- regex match count
GREATEST(a, b, c) / LEAST(a, b, c)    -- max / min value
MEDIAN(col)                           -- median (any numeric column)
PERCENTILE(int_col, 0.5)              -- exact percentile (**docs say BIGINT only; DOUBLE input is silently truncated to int, DECIMAL errors**)
PERCENTILE_APPROX(numeric_col, 0.5)   -- approximate percentile (any numeric, preserves decimals); use only when approximation is acceptable
```

---

## 6. DQL extension syntax

### `QUALIFY` — filter window-function results without nesting

```sql
-- Equivalent subquery form
SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC) AS rn FROM emp
) tmp WHERE rn = 1;

-- QUALIFY form
SELECT * FROM emp
QUALIFY ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC) = 1;
```

### `LEFT SEMI JOIN` / `LEFT ANTI JOIN` — replace `EXISTS` / `NOT EXISTS`

```sql
-- For EXISTS semantics, use LEFT SEMI JOIN
SELECT a.* FROM users a LEFT SEMI JOIN orders b ON a.id = b.user_id;

-- For NOT EXISTS semantics, use LEFT ANTI JOIN
SELECT a.* FROM users a LEFT ANTI JOIN orders b ON a.id = b.user_id;
```

### Filter placement vs. JOIN type (WHERE vs. ON)

Place predicates according to the intended row semantics; do not assume the
optimizer treats every `WHERE` and `ON` predicate identically for pruning.

- **INNER JOIN**: a deterministic single-side filter can usually be written in `ON`, `WHERE`, or a filtered subquery without changing matched-row semantics. Prefer the placement that makes source filtering and intent clear.
- **LEFT / RIGHT OUTER JOIN**: to restrict preserved-side output rows, use `WHERE` or pre-filter that input. Put a non-preserved-side match condition in `ON` or pre-filter that input when unmatched preserved rows must remain; moving it to `WHERE` removes NULL-padded misses and changes the result.
- **LEFT SEMI / LEFT ANTI JOIN**: put right-side existence conditions in `ON` or a right-side subquery because right-side columns are not part of the output.

```sql
-- INNER JOIN with a post-join filter
SELECT a.order_id, b.name
FROM orders a JOIN users b ON a.user_id = b.user_id
WHERE a.dt = '<partition-value>' AND b.dt = '<partition-value>';

-- LEFT JOIN: right-side filter MUST go in ON
SELECT a.order_id, b.name
FROM orders a LEFT JOIN users b
  ON a.user_id = b.user_id AND b.dt = '<partition-value>'
WHERE a.dt = '<partition-value>';

-- LEFT ANTI JOIN: right-side filter MUST go in ON
SELECT u.user_id
FROM users u
LEFT ANTI JOIN orders o
  ON u.user_id = o.user_id AND o.ds = '<partition-value>'
WHERE u.ds = '<partition-value>';
```

### `PIVOT` / `UNPIVOT`

```sql
-- Row to column
SELECT * FROM t
PIVOT (SUM(amount) FOR category IN ('food' AS food, 'drink' AS drink)) AS pvt;

-- Column to row
SELECT * FROM t
UNPIVOT INCLUDE NULLS (value FOR metric IN (revenue, cost, profit)) AS unpvt;
```

### Hints (small-table broadcast / MAPJOIN)

```sql
SELECT /*+ MAPJOIN(small) */ * FROM big JOIN small ON big.id = small.id;
```

**When to add**: only after table statistics or an execution error shows that the broadcast side fits the current environment and the optimizer did not choose the desired plan. Do not assume a fixed threshold or raise memory settings without evidence. If a hint fails, classify the returned error before changing the plan or session settings.

Other hints: `SKEWJOIN` (skew), `RANGEJOIN` (range), `DYNAMICFILTER` (dynamic filter), `DISTMAPJOIN` (distributed map join), `CONDITIONALJOIN` (conditional JOIN), `SELECTIVITY` (selectivity), `MATERIALIZE` (materialize subquery).

### `LIKE ANY` / `LIKE ALL` — multi-pattern match

```sql
SELECT * FROM t WHERE name LIKE ANY ('%zhang%', '%li%', '%wang%');
SELECT * FROM t WHERE tags LIKE ALL ('%vip%', '%active%');
```

### `WINDOW` named window

```sql
SELECT user_id, SUM(amount) OVER w AS total, ROW_NUMBER() OVER w AS rn
FROM orders WHERE dt = '<partition-value>'
WINDOW w AS (PARTITION BY user_id ORDER BY create_time);
```

### Set operations

```sql
SELECT * FROM t1 UNION ALL SELECT * FROM t2;    -- merge and preserve duplicates
SELECT * FROM t1 UNION SELECT * FROM t2;         -- merge and remove duplicates
SELECT * FROM t1 INTERSECT SELECT * FROM t2;     -- intersection
SELECT * FROM t1 MINUS SELECT * FROM t2;         -- difference (MINUS = EXCEPT)
```

### `LIMIT`

```sql
SELECT * FROM t LIMIT 10;
SELECT * FROM t LIMIT 10 OFFSET 20;
```

### Other extension syntax cheat sheet

| Syntax | Example |
|---|---|
| `SELECT * EXCEPT` | `SELECT * EXCEPT (password) FROM users` |
| `SELECT * REPLACE` | `SELECT * REPLACE (UPPER(name) AS name) FROM t` |
| `IS NOT DISTINCT FROM` | `WHERE col1 IS NOT DISTINCT FROM col2` (NULL-safe equality) |
| `VALUES` row constructor | `SELECT * FROM (VALUES (1,'a'),(2,'b')) AS t(id,name)` |
| `TABLESAMPLE` (percent) | `SELECT * FROM t TABLESAMPLE(10 PERCENT)` |
| `TABLESAMPLE` (bucket) | `SELECT * FROM t TABLESAMPLE(BUCKET 1 OUT OF 10 ON id)` |
| `WITH RECURSIVE`\*\* | `WITH RECURSIVE cte AS (... UNION ALL ...) SELECT * FROM cte` |
| `DISTRIBUTE BY` + `SORT BY` | `SELECT * FROM t DISTRIBUTE BY key SORT BY key` (local sort) |
| `CLUSTER BY` | `SELECT * FROM t CLUSTER BY key` (= DISTRIBUTE+SORT same column) |
| `UNNEST` + `LATERAL VIEW` | `SELECT t.id, elem FROM t LATERAL VIEW EXPLODE(t.arr) u AS elem` (**MaxCompute does NOT support PG-style `UNNEST(...) AS u(col)` column aliases — raises `ODPS-0130071: column alias is not supported in unnest`**) |
| Lambda (`TRANSFORM`) | `SELECT TRANSFORM(arr, x -> x * 2) FROM t` |
| Lambda (`FILTER`) | `SELECT FILTER(arr, x -> x > 0) FROM t` |
| `WITHIN GROUP` | `SELECT WM_CONCAT(',', name) WITHIN GROUP (ORDER BY id) FROM t` |
| `STRUCT` | `SELECT STRUCT(user_id, name) AS info FROM t` |
| Time travel (by time)\* | `SELECT * FROM t TIMESTAMP AS OF '2024-01-01 00:00:00'` |
| Time travel (by version)\* | `SELECT * FROM t VERSION AS OF 3` |
| `FILTER` aggregate | `SELECT COUNT(*) FILTER (WHERE status='active') FROM t` |
| `TRANSFORM` script | `SELECT TRANSFORM(c1,c2) USING 'python x.py' AS (o1,o2) FROM t` |
| Three-level namespace | `project.schema.table` |

\* Time travel (`TIMESTAMP/VERSION AS OF`) is supported only by versioned tables (Transactional Table 2.0 / Iceberg / Delta). Using it on a regular ODPS table errors out.

\*\* `WITH RECURSIVE`: query acceleration does not support recursive CTEs. Fall back to batch execution only when the returned error identifies this restriction and the user accepts the mode change. The default iteration limit is 10 and the documented maximum is 100. See [Common table expressions](https://www.alibabacloud.com/help/en/maxcompute/user-guide/common-table-expressions-1).

---

## 7. Regular expressions

Regex grammar varies by mode:
- **Default (legacy) mode**: MaxCompute-custom regex spec (Java-compatible subset).
- **Hive-compatible mode** (`SET odps.sql.hive.compatible=true;`): full Java regex spec.

In SQL string literals, backslashes must be **double-escaped** (uniform client-submission rule).

```sql
-- \d in SQL is written as \\d
SELECT * FROM t WHERE col RLIKE '\\d{4}-\\d{2}-\\d{2}';
SELECT REGEXP_EXTRACT(text, '(1[3-9]\\d{9})', 1) AS phone FROM t;
SELECT REGEXP_REPLACE(str, '[^0-9]', '') AS digits_only FROM t;
```

`\d` `\w` `\s` work, `*?` `+?` non-greedy work, `(?=...)` lookahead works.

---

## 8. Window function frames

### Cumulative and moving window frames

The default frame depends on mode; for **cumulative aggregation / moving average** you must specify `ROWS` explicitly (otherwise results differ between Hive and non-Hive modes):
- Hive-compatible mode (`SET odps.sql.hive.compatible=true`): default `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`.
- Non-Hive mode + `ORDER BY` + aggregate (`AVG` / `COUNT` / `MAX` / `MIN` / `STDDEV` / `SUM`): default `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`.

> Note: `ROW_NUMBER` / `RANK` / `DENSE_RANK` and other position-class window functions **do not need** an explicit `ROWS` clause. Only cumulative / moving aggregates need it.

```sql
-- DON'T: rely on default RANGE frame
SELECT SUM(amount) OVER (ORDER BY dt) FROM t;

-- DO: explicit ROWS
SELECT SUM(amount) OVER (ORDER BY dt ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) FROM t;

-- Moving average: explicit window size
SELECT AVG(amount) OVER (ORDER BY dt ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) FROM t;
```

`ROWS` = physical row count, `RANGE` = logical value range (duplicates collapse), `GROUPS` = by group (SQL:2011 standard).

`EXCLUDE` is supported: `EXCLUDE CURRENT ROW` / `EXCLUDE GROUP` / `EXCLUDE TIES` / `EXCLUDE NO OTHERS`.

---

## 9. SQL quantity limits

The following values are documented public-cloud limits. Check the current [MaxCompute SQL limits](https://www.alibabacloud.com/help/en/maxcompute/user-guide/maxcompute-sql-limits) and [SELECT syntax](https://www.alibabacloud.com/help/en/maxcompute/user-guide/select-syntax) when an environment-specific setting or a newer product version may differ.

**SQL text and execution plan size:**

| Limit | Cap | Consequence |
|---|---|---|
| SQL statement length | 2 MB | Parse failure (`ODPS-0130161`) |
| Execution plan size | 1 MB | `The Size of Plan is too large` (`ODPS-0010000`); split SQL |
| Job max runtime | 24h default / 72h cap | Raise the session value only when the longer run is required, supported, and accepted |

**Set operations and JOINs:**

| Limit | Cap | Notes |
|---|---|---|
| `UNION ALL` table count | 256 | |
| `MAPJOIN` small-table count | 128 | total memory ≤ 512 MB |
| `IN` argument count | recommended ≤ 1,024 | documented recommendation, not a hard limit |

**Subquery return rows:**

| Limit | Cap | Consequence |
|---|---|---|
| Partition-pruning subquery returned rows | 1,000 | reduce the subquery result or use a different pruning strategy |

**Object and partition scale:**

| Limit | Cap |
|---|---|
| Partitions per table | 60,000 |
| Partition levels | 6 |
| Columns per table | 1,200 |
| Max partitions scanned per query | 10,000 |

**Result and data:**

| Limit | Cap | Notes |
|---|---|---|
| `SELECT` screen output | 10,000 rows and 10 MB | this is a display/return limit; do not create a destination table without explicit user authorization |
| Cell size (single column × single row) | 8 MB | |

---

## 10. Operator differences

| Operation | MaxCompute | Standard SQL |
|---|---|---|
| String concat | `CONCAT(a, b)` or `a \|\| b` | `a + b` (some DBs) |
| `DOUBLE` comparison | precision issues; cast to `DECIMAL` | same |
| Bit shift left | `SHIFTLEFT(a, n)` | `a << n` |
| Bit shift right | `SHIFTRIGHT(a, n)` | `a >> n` |
| Integer division | `a DIV b` | no standard |
| Regex match | `col RLIKE pattern` | `col REGEXP pattern` |

**Percentage / ratio calculation**: `/` returns a quotient; when both operands
are `BIGINT`, MaxCompute returns `DOUBLE`. `DIV` is the operator that discards
the fractional part. Use `DIV` only for an intentional integer quotient. For
governed exact-decimal ratios, choose and verify DECIMAL precision and scale as
described in §4.

---

## 11. Data types

**Specific types:**
- `DATETIME` — date+time without time zone; literal: `DATETIME '2024-01-01 00:00:00'`
- `TIMESTAMP_NTZ` — Timestamp without time zone (different from `DATETIME` and `TIMESTAMP`)
- `STRING` — unbounded string
- `JSON` — JSON type, supports optional schema: `JSON<name:STRING, age:INT>`
- `VECTOR(type, dim)` — AI vector type
- `BLOB` — binary large object
- `GEOGRAPHY` — geospatial type

**Complex types:**
- `ARRAY<STRING>` — array
- `MAP<STRING, INT>` — key-value
- `STRUCT<name:STRING, age:INT>` — struct

**Literals:**
```sql
DATETIME '2024-01-01 00:00:00'
JSON '{"key": "value"}'           -- requires `SET odps.sql.type.json.enable=true;`
INTERVAL '1' DAY                  -- requires `SET odps.sql.type.system.odps2=true;` to enable INTERVAL_DAY_TIME
INTERVAL '1-2' YEAR TO MONTH      -- ditto, requires odps2 to enable INTERVAL_YEAR_MONTH
CURRENT_DATE() / CURRENT_TIMESTAMP()
-- Note: CURRENT_DATE without parentheses requires `SET odps.sql.hive.compatible=true;`;
--       LOCALTIMESTAMP is unavailable in MaxCompute, use CURRENT_TIMESTAMP();
--       CURRENT_TIMESTAMP() returns TIMESTAMP by default;
--       with `SET odps.sql.timestamp.function.ntz=true`, it returns TIMESTAMP_NTZ.
```

---

## 12. Common SET parameters cheat sheet

Session-level parameters; written before the SQL with `SET key=value;`. Only parameters relevant to text generation are listed; runtime resource-tuning parameters (mapper / reducer memory, etc.) are in [sql-common-errors.md](sql-common-errors.md).

### Compatibility / dialect switches

| Parameter | Default | Purpose |
|---|---|---|
| `odps.sql.type.system.odps2` | false | ODPS 2.0 type system; required for types such as `TINYINT`, `TIMESTAMP`, and `INTERVAL`, and part of the documented DECIMAL 2.0 configuration. It does not alone enable configurable DECIMAL precision and scale. |
| `odps.sql.decimal.odps2` | false | Enable DECIMAL 2.0 together with `odps.sql.type.system.odps2`; without it, configurable `DECIMAL(p,s)` raises `precision and scale is not currently supported` |
| `odps.sql.type.json.enable` | false | Enable JSON type system (JSON literal / `CAST AS JSON` / `JSON_EXTRACT`); without it `JSON_EXTRACT(STRING, ...)` raises 0130121 |
| `odps.sql.hive.compatible` | false | Hive compatibility mode; enables Hive syntax like `TRUNC(d, 'MM')` |
| `odps.sql.allow.fullscan` | false | Allow partitioned-table full scan (no partition filter) — use with care |
| `odps.sql.allow.cartesian` | false | Allow a Cartesian-product JOIN only when the requested semantics and bounded cost justify it; use MAPJOIN only with a verified broadcast side |
| `odps.sql.validate.orderby.limit` | true | Force `ORDER BY` to be paired with `LIMIT`; `false` disables the check |
| `odps.sql.submit.mode` | — | Set to `script` to enable procedural extensions (variables / IF / LOOP / SQL UDF / TEMPORARY TABLE) |
| `odps.sql.step.script.mode` | false | Combined with `submit.mode=script` enables step-script-mode; TEMPORARY TABLE needs both switches |
| `odps.sql.timestamp.function.ntz` | false | Make `CURRENT_TIMESTAMP()` return `TIMESTAMP_NTZ` instead of `TIMESTAMP` |

### Limit switches

| Parameter | Default | Purpose |
|---|---|---|
| `odps.sql.udf.strict.mode` | true | UDF strict mode; the public-cloud common synonym is `odps.function.strictmode` (the parameter name varies by environment / version). For a dirty `CAST` failure, consider the verified parameter only after safer filtering or diagnostic options and after confirming that cast-failure `NULL` values preserve the requested semantics. |
| `odps.sql.udf.timeout` | 600 | UDF timeout seconds, range 0–3600 |
| `odps.sql.rcte.max.iterate.num` | 10 | Recursive-CTE max iterations; hard cap 100 |
| `odps.mcqa.disable` | false | Disable query acceleration only when the returned error identifies an incompatible feature and the user accepts batch execution |
| `odps.sql.job.max.time.hours` | 24 | Job max runtime hours, cap 72 |

> odps2 and Hive-compatible mode are not mutually exclusive: odps2 controls the type system, Hive-compatible controls SQL syntax. Both can be enabled simultaneously.
