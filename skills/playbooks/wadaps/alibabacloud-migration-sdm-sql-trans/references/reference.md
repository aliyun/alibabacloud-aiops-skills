# Synapse → Hologres Reference

## Data Type Mapping

### Numeric Types

| Synapse | Hologres | Notes |
|---------|----------|-------|
| `BIGINT` | `BIGINT` | Same |
| `INT` / `INTEGER` | `INT` / `INTEGER` | Same |
| `SMALLINT` | `SMALLINT` | Same |
| `TINYINT` | `SMALLINT` | No TINYINT in PG; SMALLINT is smallest integer type |
| `BIT` | `BOOLEAN` | `0/1` → `TRUE/FALSE`; update comparisons accordingly |
| `DECIMAL(p,s)` / `NUMERIC(p,s)` | `DECIMAL(p,s)` / `NUMERIC(p,s)` | Same |
| `MONEY` | `NUMERIC(19,4)` | |
| `SMALLMONEY` | `NUMERIC(10,4)` | |
| `FLOAT` | `DOUBLE PRECISION` / `FLOAT8` | |
| `REAL` | `REAL` / `FLOAT4` | Same |

### String Types

| Synapse | Hologres | Notes |
|---------|----------|-------|
| `CHAR(n)` | `CHAR(n)` | Same |
| `VARCHAR(n)` | `VARCHAR(n)` | Same |
| `VARCHAR(MAX)` | `TEXT` | |
| `NCHAR(n)` | `CHAR(n)` | Hologres is UTF-8 natively, N prefix unnecessary |
| `NVARCHAR(n)` | `VARCHAR(n)` | |
| `NVARCHAR(MAX)` | `TEXT` | |
| `TEXT` (deprecated T-SQL) | `TEXT` | |
| `NTEXT` (deprecated T-SQL) | `TEXT` | |

### Date/Time Types

| Synapse | Hologres | Notes |
|---------|----------|-------|
| `DATE` | `DATE` | Same |
| `TIME` | `TIME` | Same |
| `DATETIME` | `TIMESTAMP` | |
| `DATETIME2` | `TIMESTAMP` | |
| `SMALLDATETIME` | `TIMESTAMP` | |
| `DATETIMEOFFSET` | `TIMESTAMPTZ` | |

### Binary Types

| Synapse | Hologres | Notes |
|---------|----------|-------|
| `BINARY(n)` | `BYTEA` | |
| `VARBINARY(n)` | `BYTEA` | |
| `VARBINARY(MAX)` | `BYTEA` | |
| `IMAGE` | `BYTEA` | |

### Other Types

| Synapse | Hologres | Notes |
|---------|----------|-------|
| `UNIQUEIDENTIFIER` | `UUID` | |
| `XML` | `TEXT` or `JSONB` | Depends on usage; Hologres has no native XML type |
| `SQL_VARIANT` | No equivalent | Redesign needed; use `TEXT` + type column, or `JSONB` |
| `GEOGRAPHY` / `GEOMETRY` | PostGIS extension | If available: `GEOMETRY` / `GEOGRAPHY` |
| `HIERARCHYID` | No equivalent | Redesign with `LTREE` extension or materialized path pattern |
| `ROWVERSION` / `TIMESTAMP` (T-SQL legacy) | No equivalent | Use trigger-based versioning or `xmin` system column |

---

## Function Mapping

### Date & Time Functions

| Synapse | Hologres | Example |
|---------|----------|---------|
| `GETDATE()` | `CURRENT_TIMESTAMP` or `NOW()` | |
| `SYSDATETIME()` | `CURRENT_TIMESTAMP` | |
| `GETUTCDATE()` | `NOW() AT TIME ZONE 'UTC'` | |
| `CURRENT_TIMESTAMP` | `CURRENT_TIMESTAMP` | Same |
| `DATEADD(year, n, d)` | `d + INTERVAL 'n year'` | `DATEADD(year,1,'2024-01-01')` → `'2024-01-01'::date + INTERVAL '1 year'` |
| `DATEADD(quarter, n, d)` | `d + INTERVAL 'n month' * 3` | Or `d + n * INTERVAL '3 month'` |
| `DATEADD(month, n, d)` | `d + INTERVAL 'n month'` | |
| `DATEADD(week, n, d)` | `d + INTERVAL 'n week'` | |
| `DATEADD(day, n, d)` | `d + INTERVAL 'n day'` or `d + n` | For DATE type, `d + n` works directly |
| `DATEADD(hour, n, d)` | `d + INTERVAL 'n hour'` | |
| `DATEADD(minute, n, d)` | `d + INTERVAL 'n minute'` | |
| `DATEADD(second, n, d)` | `d + INTERVAL 'n second'` | |
| `DATEDIFF(day, a, b)` | `(b::date - a::date)` | Returns integer (days) |
| `DATEDIFF(month, a, b)` | `(EXTRACT(YEAR FROM b) - EXTRACT(YEAR FROM a)) * 12 + EXTRACT(MONTH FROM b) - EXTRACT(MONTH FROM a)` | Integer months |
| `DATEDIFF(year, a, b)` | `EXTRACT(YEAR FROM b) - EXTRACT(YEAR FROM a)` | Integer years |
| `DATEDIFF(hour, a, b)` | `EXTRACT(EPOCH FROM (b::timestamp - a::timestamp))::bigint / 3600` | T-SQL counts hour boundaries crossed; this gives elapsed hours. Use `FLOOR()` to match boundary semantics |
| `DATEDIFF(minute, a, b)` | `EXTRACT(EPOCH FROM (b::timestamp - a::timestamp))::bigint / 60` | Same caveat: elapsed minutes vs boundary crossings |
| `DATEDIFF(second, a, b)` | `EXTRACT(EPOCH FROM (b::timestamp - a::timestamp))::bigint` | Elapsed seconds; matches T-SQL for whole-second timestamps |
| `DATEPART(year, d)` | `EXTRACT(YEAR FROM d)` | Returns double; cast to INT if needed |
| `DATEPART(month, d)` | `EXTRACT(MONTH FROM d)` | |
| `DATEPART(day, d)` | `EXTRACT(DAY FROM d)` | |
| `DATEPART(hour, d)` | `EXTRACT(HOUR FROM d)` | |
| `DATEPART(weekday, d)` | `EXTRACT(DOW FROM d)` | PG: Sunday=0; T-SQL: depends on @@DATEFIRST |
| `DATEPART(week, d)` | `EXTRACT(WEEK FROM d)` | ISO week numbering in PG |
| `DATEPART(quarter, d)` | `EXTRACT(QUARTER FROM d)` | |
| `DATENAME(month, d)` | `TO_CHAR(d, 'Month')` | Returns full month name |
| `DATENAME(weekday, d)` | `TO_CHAR(d, 'Day')` | Returns full day name |
| `EOMONTH(d)` | `(DATE_TRUNC('month', d) + INTERVAL '1 month - 1 day')::date` | Last day of month |
| `EOMONTH(d, n)` | `(DATE_TRUNC('month', d + n * INTERVAL '1 month') + INTERVAL '1 month - 1 day')::date` | With offset |
| `ISDATE(expr)` | No direct equivalent | Use `CASE WHEN expr::date IS NOT NULL THEN 1 ELSE 0 END` with TRY/CATCH pattern |
| `SWITCHOFFSET(dt, tz)` | `dt AT TIME ZONE tz` | |
| `TODATETIMEOFFSET(dt, tz)` | `dt AT TIME ZONE tz` | |

### String Functions

| Synapse | Hologres | Notes |
|---------|----------|-------|
| `LEN(s)` | `LENGTH(s)` | `LEN` trims trailing spaces; `LENGTH` does not. Use `LENGTH(RTRIM(s))` for exact parity |
| `DATALENGTH(s)` | `OCTET_LENGTH(s)` | Byte length |
| `CHARINDEX(sub, str)` | `POSITION(sub IN str)` | Or `STRPOS(str, sub)` |
| `CHARINDEX(sub, str, start)` | `POSITION(sub IN SUBSTRING(str FROM start)) + start - 1` | Requires adjustment for start offset |
| `PATINDEX(pattern, str)` | Use `POSITION` with regex: `(SELECT CASE WHEN str ~ pattern THEN ... END)` | Complex; may need PL/pgSQL |
| `SUBSTRING(s, i, n)` | `SUBSTRING(s FROM i FOR n)` | Or `SUBSTR(s, i, n)` |
| `LEFT(s, n)` | `LEFT(s, n)` | Same |
| `RIGHT(s, n)` | `RIGHT(s, n)` | Same |
| `LTRIM(s)` | `LTRIM(s)` | Same |
| `RTRIM(s)` | `RTRIM(s)` | Same |
| `TRIM(s)` | `TRIM(s)` | Same |
| `UPPER(s)` | `UPPER(s)` | Same |
| `LOWER(s)` | `LOWER(s)` | Same |
| `REPLACE(s, old, new)` | `REPLACE(s, old, new)` | Same |
| `REPLICATE(s, n)` | `REPEAT(s, n)` | |
| `REVERSE(s)` | `REVERSE(s)` | Same |
| `SPACE(n)` | `REPEAT(' ', n)` | |
| `STUFF(s, start, len, rep)` | `OVERLAY(s PLACING rep FROM start FOR len)` | |
| `CONCAT(a, b, ...)` | `CONCAT(a, b, ...)` | **Keep as-is**; both treat NULL as empty string |
| `CONCAT_WS(sep, a, b, ...)` | `CONCAT_WS(sep, a, b, ...)` | Same; both skip NULLs |
| `STRING_AGG(expr, sep)` | `STRING_AGG(expr, sep)` | Same; `WITHIN GROUP (ORDER BY ...)` → use `ORDER BY` inside the aggregate |
| `QUOTENAME(s)` | `QUOTE_IDENT(s)` | |
| `UNICODE(s)` | `ASCII(s)` | For first character's code point |
| `NCHAR(n)` | `CHR(n)` | |
| `CHAR(n)` | `CHR(n)` | |
| `ASCII(s)` | `ASCII(s)` | Same |
| `FORMAT(val, fmt)` | `TO_CHAR(val, fmt)` | Format tokens differ between T-SQL and PG |
| `STR(float, len, dec)` | `TO_CHAR(float, format)` | Build format string from len/dec |

### Null Handling

| Synapse | Hologres | Notes |
|---------|----------|-------|
| `ISNULL(a, b)` | `COALESCE(a, b)` | `COALESCE` accepts multiple args |
| `NULLIF(a, b)` | `NULLIF(a, b)` | Same |
| `COALESCE(a, b, ...)` | `COALESCE(a, b, ...)` | Same |

### Conditional / Logic

| Synapse | Hologres | Notes |
|---------|----------|-------|
| `IIF(cond, t, f)` | `CASE WHEN cond THEN t ELSE f END` | |
| `CHOOSE(idx, v1, v2, ...)` | `(ARRAY[v1, v2, ...])[idx]` | Or use CASE |
| `CASE ... END` | `CASE ... END` | Same |

### Math Functions

| Synapse | Hologres | Notes |
|---------|----------|-------|
| `ABS(n)` | `ABS(n)` | Same |
| `CEILING(n)` | `CEIL(n)` | |
| `FLOOR(n)` | `FLOOR(n)` | Same |
| `ROUND(n, d)` | `ROUND(n, d)` | Same |
| `POWER(n, p)` | `POWER(n, p)` | Same |
| `SQRT(n)` | `SQRT(n)` | Same |
| `SIGN(n)` | `SIGN(n)` | Same |
| `RAND()` | `RANDOM()` | |
| `LOG(n)` | `LN(n)` | T-SQL `LOG` = natural log; PG `LOG` = base-10 |
| `LOG10(n)` | `LOG(n)` | PG `LOG(n)` = base-10 |
| `LOG(base, n)` | `LOG(base, n)` | Same (2-arg form) |
| `EXP(n)` | `EXP(n)` | Same |
| `PI()` | `PI()` | Same |
| `SQUARE(n)` | `n * n` or `POWER(n, 2)` | No built-in `SQUARE` in PG |

### Type Conversion

| Synapse | Hologres | Notes |
|---------|----------|-------|
| `CAST(expr AS type)` | `CAST(expr AS type)` | Same syntax, but use Hologres types |
| `CONVERT(type, expr)` | `CAST(expr AS type)` | |
| `CONVERT(VARCHAR, date, style)` | `TO_CHAR(date, format)` | Map T-SQL style codes to PG format tokens (see below) |
| `TRY_CAST(expr AS type)` | No direct equivalent | Use PL/pgSQL `BEGIN...EXCEPTION` block or conditional logic |
| `TRY_CONVERT(type, expr)` | No direct equivalent | Same as above |
| `PARSE(str AS type USING culture)` | `TO_DATE` / `TO_NUMBER` / `TO_TIMESTAMP` | |
| `TRY_PARSE(...)` | Same with error handling | |
| `expr::type` | `expr::type` | PG cast syntax; same in Hologres |

#### CONVERT Style Codes → TO_CHAR Formats

| T-SQL Style | Meaning | PG TO_CHAR Format |
|-------------|---------|-------------------|
| 101 | MM/DD/YYYY | `'MM/DD/YYYY'` |
| 102 | YYYY.MM.DD | `'YYYY.MM.DD'` |
| 103 | DD/MM/YYYY | `'DD/MM/YYYY'` |
| 104 | DD.MM.YYYY | `'DD.MM.YYYY'` |
| 105 | DD-MM-YYYY | `'DD-MM-YYYY'` |
| 108 | HH:MI:SS | `'HH24:MI:SS'` |
| 110 | MM-DD-YYYY | `'MM-DD-YYYY'` |
| 112 | YYYYMMDD | `'YYYYMMDD'` |
| 120 | YYYY-MM-DD HH:MI:SS | `'YYYY-MM-DD HH24:MI:SS'` |
| 121 | YYYY-MM-DD HH:MI:SS.mmm | `'YYYY-MM-DD HH24:MI:SS.MS'` |
| 126 | ISO8601 | `'YYYY-MM-DD"T"HH24:MI:SS'` |

### Aggregate / Window Functions

| Synapse | Hologres | Notes |
|---------|----------|-------|
| `COUNT / SUM / AVG / MIN / MAX` | Same | Same |
| `ROW_NUMBER() OVER(...)` | Same | Same |
| `RANK() OVER(...)` | Same | Same |
| `DENSE_RANK() OVER(...)` | Same | Same |
| `NTILE(n) OVER(...)` | Same | Same |
| `LAG / LEAD` | Same | Same |
| `FIRST_VALUE / LAST_VALUE` | Same | Same (but LAST_VALUE needs frame clause) |
| `PERCENT_RANK / CUME_DIST` | Same | Same |
| `PERCENTILE_CONT / PERCENTILE_DISC` | Same | PG uses `WITHIN GROUP (ORDER BY ...)` syntax |
| `STRING_AGG(col, sep) WITHIN GROUP (ORDER BY ...)` | `STRING_AGG(col, sep ORDER BY ...)` | PG puts ORDER BY inside the function call |
| `COUNT_BIG(*)` | `COUNT(*)` | PG COUNT already returns BIGINT |
| `APPROX_COUNT_DISTINCT(col)` | `COUNT(DISTINCT col)` | Or use HyperLogLog extension if available |

### System & Metadata Functions

| Synapse | Hologres | Notes |
|---------|----------|-------|
| `@@ROWCOUNT` | `GET DIAGNOSTICS var = ROW_COUNT` | PL/pgSQL only |
| `@@IDENTITY` / `SCOPE_IDENTITY()` | `LASTVAL()` or `RETURNING id` | Prefer `RETURNING` clause |
| `@@ERROR` | Exception handling via `BEGIN...EXCEPTION` | |
| `NEWID()` | `gen_random_uuid()` | PG 13+ |
| `OBJECT_ID('table')` | `'table'::regclass` | Returns OID |
| `HASHBYTES('SHA2_256', data)` | `DIGEST(data, 'sha256')` | Requires pgcrypto; wrap with `ENCODE(..., 'hex')` |
| `DB_NAME()` | `CURRENT_DATABASE()` | |
| `SCHEMA_NAME()` | `CURRENT_SCHEMA` | |
| `SUSER_NAME()` | `CURRENT_USER` | |
| `USER_NAME()` | `SESSION_USER` | |

### JSON Functions

| Synapse | Hologres | Notes |
|---------|----------|-------|
| `JSON_VALUE(json, '$.key')` | `json_col->>'key'` | Or `jsonb_extract_path_text(json_col, 'key')` |
| `JSON_QUERY(json, '$.obj')` | `json_col->'obj'` | Or `jsonb_extract_path(json_col, 'obj')` |
| `ISJSON(str)` | `(str::jsonb IS NOT NULL)` wrapped in a safe check | |
| `JSON_MODIFY(json, path, val)` | `jsonb_set(json_col::jsonb, '{key}', '"val"')` | |
| `OPENJSON(json)` | `jsonb_array_elements(json_col::jsonb)` | For arrays |
| `OPENJSON(json) WITH (col type '$.path')` | `jsonb_to_recordset(json_col::jsonb) AS t(col type)` | |
| `FOR JSON PATH` | `json_agg(json_build_object(...))` | |
| `FOR JSON AUTO` | `json_agg(row_to_json(t))` | |

---

## DDL Property Mapping

### Table Properties

| Synapse Property | Hologres Equivalent |
|------------------|-------------------|
| `DISTRIBUTION = HASH(col)` | `CALL set_table_property('schema.table', 'distribution_key', 'col')` |
| `DISTRIBUTION = HASH(c1, c2)` | `CALL set_table_property('schema.table', 'distribution_key', 'c1,c2')` |
| `DISTRIBUTION = ROUND_ROBIN` | Default (no distribution_key set) |
| `DISTRIBUTION = REPLICATE` | `CALL set_table_property('schema.table', 'distribution_key', '')` |
| `CLUSTERED COLUMNSTORE INDEX` | `CALL set_table_property('schema.table', 'orientation', 'column')` |
| `HEAP` | `CALL set_table_property('schema.table', 'orientation', 'row')` |
| `CLUSTERED INDEX(col)` | `CALL set_table_property('schema.table', 'clustering_key', 'col')` |
| `PARTITION (col RANGE RIGHT FOR VALUES (...))` | `PARTITION BY LIST(col)` or `PARTITION BY RANGE(col)` in CREATE TABLE |

### Hologres-Specific Properties

Common set_table_property calls:

```sql
-- Bitmap index (for low-cardinality columns)
CALL set_table_property('t', 'bitmap_columns', 'col1,col2');

-- Dictionary encoding (for string columns)
CALL set_table_property('t', 'dictionary_encoding_columns', 'col1,col2');

-- TTL (time-to-live) in seconds
CALL set_table_property('t', 'time_to_live_in_seconds', '86400');

-- Segment key (for column-store sorting within shard)
CALL set_table_property('t', 'segment_key', 'col');

-- Event time column (for incremental data)
CALL set_table_property('t', 'event_time_column', 'col');
```

---

## Constructs With No Direct Equivalent

| Synapse Construct | Recommended Approach |
|-------------------|---------------------|
| `TRY_CAST` / `TRY_CONVERT` | PL/pgSQL function with `BEGIN...EXCEPTION WHEN OTHERS THEN RETURN NULL; END` |
| Temp tables `#temp` | CTE (preferred for queries), `CREATE TEMPORARY TABLE` (for procedures) |
| Table variables `@t` | CTE or `CREATE TEMPORARY TABLE` |
| `MERGE` | `INSERT ... ON CONFLICT DO UPDATE` (upsert) |
| `OUTPUT` clause in DML | `RETURNING` clause |
| `CROSS APPLY` | `CROSS JOIN LATERAL` |
| `OUTER APPLY` | `LEFT JOIN LATERAL ... ON TRUE` |
| `PIVOT` | `CASE + aggregate` or `crosstab()` from tablefunc extension |
| `UNPIVOT` | `LATERAL` + `VALUES` or `unnest` |
| `OPTION (LABEL = ...)` | Remove; use `/*+ label */` comment if needed |
| `WITH (NOLOCK)` | Remove; Hologres uses MVCC |
| `@@ROWCOUNT` after DML | `GET DIAGNOSTICS row_cnt = ROW_COUNT;` in PL/pgSQL |
| `WAITFOR DELAY` | `pg_sleep(seconds)` |
| `CURSOR` (T-SQL style) | PG cursor with `DECLARE ... CURSOR FOR ...` |
| `sp_rename` | `ALTER TABLE ... RENAME TO ...` / `ALTER TABLE ... RENAME COLUMN ... TO ...` |
| `SET NOCOUNT ON` | Not needed; PG doesn't send row counts by default in functions |
