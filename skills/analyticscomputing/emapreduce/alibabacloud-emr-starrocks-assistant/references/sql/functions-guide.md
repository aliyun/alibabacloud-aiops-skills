# Common Functions Guide

## Table of Contents

1. [Aggregate Functions](#aggregate-functions)
2. [String Functions](#string-functions)
3. [Date Functions](#date-functions)
4. [JSON Functions](#json-functions)
5. [Array and MAP Functions](#array-and-map-functions)
6. [Conditional Functions](#conditional-functions)
7. [Type Conversion](#type-conversion)
8. [BITMAP and HLL Functions](#bitmap-and-hll-functions)

---

## Aggregate Functions

### Basic Aggregates

| Function | Description | Example |
|------|------|------|
| `COUNT(*)` | Total number of rows | `SELECT COUNT(*) FROM orders` |
| `COUNT(col)` | Number of non-NULL rows | `SELECT COUNT(amount) FROM orders` |
| `COUNT(DISTINCT col)` | Exact deduplication count | `SELECT COUNT(DISTINCT user_id) FROM events` |
| `SUM(col)` | Sum | `SELECT SUM(amount) FROM orders` |
| `AVG(col)` | Average | `SELECT AVG(amount) FROM orders` |
| `MIN(col)` / `MAX(col)` | Minimum/maximum | `SELECT MIN(price), MAX(price) FROM products` |
| `GROUP_CONCAT(col [, sep])` | String concatenation | `SELECT GROUP_CONCAT(name, ',') FROM users GROUP BY dept` |

### Approximate Deduplication

```sql
-- APPROX_COUNT_DISTINCT: approximate deduplication (~2-3% error, much faster than COUNT DISTINCT)
SELECT APPROX_COUNT_DISTINCT(user_id) FROM events
WHERE dt = '2024-01-15';

-- HLL (HyperLogLog): pre-define an HLL column when creating the table
-- DDL: uv HLL HLL_UNION
-- During ingestion, convert with hll_hash()
-- Query:
SELECT HLL_UNION_AGG(uv) FROM events_agg WHERE dt = '2024-01-15';

-- BITMAP: exact deduplication; works for INT-type values
-- DDL: uv BITMAP BITMAP_UNION
-- During ingestion, convert with to_bitmap()
-- Query:
SELECT BITMAP_UNION_COUNT(uv) FROM events_agg WHERE dt = '2024-01-15';
```

### Deduplication Function Comparison

| Method | Precision | Cardinality limit | Performance | Use case |
|------|------|---------|------|---------|
| `COUNT(DISTINCT)` | Exact | < 10 million | Slow | Low-cardinality exact deduplication |
| `APPROX_COUNT_DISTINCT` | ~2-3% error | Unlimited | Fast | High-cardinality approximate deduplication |
| `BITMAP_UNION_COUNT` | Exact | INT range | Medium | High-cardinality exact deduplication (requires pre-built BITMAP column) |
| `HLL_UNION_AGG` | ~1% error | Unlimited | Fastest | Very high cardinality approximate deduplication |

### Other Aggregate Functions

```sql
-- PERCENTILE_APPROX: approximate percentile (P50/P95/P99)
SELECT PERCENTILE_APPROX(response_time, 0.99) AS p99
FROM request_logs WHERE dt = '2024-01-15';

-- ARRAY_AGG: aggregate into an array
SELECT user_id, ARRAY_AGG(order_id) AS order_list
FROM orders GROUP BY user_id;

-- MULTI_DISTINCT_COUNT: multi-column distinct count
SELECT MULTI_DISTINCT_COUNT(user_id, device_id) FROM events;
```

---

## String Functions

### Common String Operations

| Function | Description | Example | Result |
|------|------|------|------|
| `CONCAT(s1, s2, ...)` | String concatenation | `CONCAT('Hello', ' ', 'World')` | `'Hello World'` |
| `CONCAT_WS(sep, s1, s2)` | Join with separator | `CONCAT_WS('-', '2024', '01', '15')` | `'2024-01-15'` |
| `SUBSTRING(s, pos, len)` | Substring | `SUBSTRING('Hello World', 1, 5)` | `'Hello'` |
| `LENGTH(s)` | String length | `LENGTH('Hello')` | `5` |
| `UPPER(s)` / `LOWER(s)` | Case conversion | `UPPER('hello')` | `'HELLO'` |
| `TRIM(s)` | Strip leading/trailing spaces | `TRIM('  hello  ')` | `'hello'` |
| `REPLACE(s, old, new)` | Replace | `REPLACE('Hello', 'l', 'r')` | `'Herro'` |
| `SPLIT(s, delim)` | Split into array | `SPLIT('a,b,c', ',')` | `['a','b','c']` |
| `REGEXP_EXTRACT(s, pat, idx)` | Regex extract | `REGEXP_EXTRACT('abc123', '(\d+)', 1)` | `'123'` |
| `REGEXP_REPLACE(s, pat, rep)` | Regex replace | `REGEXP_REPLACE('a1b2', '\d', '')` | `'ab'` |

### String Matching

```sql
-- LIKE: wildcard match
WHERE name LIKE 'John%'        -- prefix match (can use the index)
WHERE name LIKE '%John%'       -- contains match (cannot use the index)

-- REGEXP: regular expression match
WHERE email REGEXP '^[a-z]+@.*\\.com$'

-- LOCATE / INSTR: find substring position
SELECT LOCATE('World', 'Hello World');  -- returns 7
```

---

## Date Functions

### Date Retrieval and Conversion

| Function | Description | Example | Result |
|------|------|------|------|
| `NOW()` | Current datetime | `SELECT NOW()` | `2024-01-15 10:30:00` |
| `CURDATE()` | Current date | `SELECT CURDATE()` | `2024-01-15` |
| `DATE(dt)` | Extract the date part | `DATE('2024-01-15 10:30:00')` | `2024-01-15` |
| `YEAR(dt)` | Extract year | `YEAR('2024-01-15')` | `2024` |
| `MONTH(dt)` | Extract month | `MONTH('2024-01-15')` | `1` |
| `DAY(dt)` | Extract day | `DAY('2024-01-15')` | `15` |
| `HOUR(dt)` | Extract hour | `HOUR('2024-01-15 10:30:00')` | `10` |
| `DAYOFWEEK(dt)` | Day of week (1=Sunday) | `DAYOFWEEK('2024-01-15')` | `2` (Monday) |

### Date Arithmetic

```sql
-- DATE_ADD / DATE_SUB: add/subtract dates
SELECT DATE_ADD('2024-01-15', INTERVAL 7 DAY);     -- 2024-01-22
SELECT DATE_SUB('2024-01-15', INTERVAL 1 MONTH);   -- 2023-12-15

-- DATEDIFF: difference in days
SELECT DATEDIFF('2024-01-15', '2024-01-01');        -- 14

-- TIMESTAMPDIFF: time difference (multiple units supported)
SELECT TIMESTAMPDIFF(HOUR, '2024-01-15 00:00:00', '2024-01-15 10:30:00');  -- 10

-- DATE_TRUNC: date truncation (commonly used for grouping)
SELECT DATE_TRUNC('month', '2024-01-15');           -- 2024-01-01
SELECT DATE_TRUNC('week', '2024-01-15');            -- 2024-01-15 (Monday)
SELECT DATE_TRUNC('hour', '2024-01-15 10:35:00');   -- 2024-01-15 10:00:00
```

### Date Formatting

```sql
-- DATE_FORMAT: date to string
SELECT DATE_FORMAT('2024-01-15', '%Y-%m-%d');  -- '2024-01-15'
SELECT DATE_FORMAT(NOW(), '%Y-%m-%d %H:%i:%s');

-- STR_TO_DATE: string to date
SELECT STR_TO_DATE('15/01/2024', '%d/%m/%Y');  -- 2024-01-15

-- Common format specifiers
-- %Y 4-digit year  %m 2-digit month  %d 2-digit day
-- %H 24-hour       %i minute         %s second
-- %T equivalent to %H:%i:%s
```

### Time Zone Handling

```sql
-- CONVERT_TZ: time zone conversion
SELECT CONVERT_TZ('2024-01-15 10:00:00', 'UTC', 'Asia/Shanghai');
-- Result: 2024-01-15 18:00:00

-- UNIX_TIMESTAMP / FROM_UNIXTIME
SELECT UNIX_TIMESTAMP('2024-01-15 00:00:00');  -- timestamp
SELECT FROM_UNIXTIME(1705248000);               -- datetime
```

---

## JSON Functions

### JSON Parsing and Querying

```sql
-- Creating and querying JSON columns
-- Use the JSON type when creating the table: json_data JSON

-- Use the -> operator (returns JSON)
SELECT json_data -> 'name' FROM table;

-- Use the ->> operator (returns string)
SELECT json_data ->> 'name' FROM table;

-- JSON_QUERY: extract a JSON sub-object
SELECT JSON_QUERY(json_data, '$.address') FROM users;

-- JSON_VALUE: extract a scalar value
SELECT JSON_VALUE(json_data, '$.age') FROM users;

-- JSON_EXISTS: check whether a path exists
SELECT * FROM users WHERE JSON_EXISTS(json_data, '$.phone');

-- JSON_LENGTH: get array length
SELECT JSON_LENGTH(json_data, '$.tags') FROM products;
```

### JSON Construction

```sql
-- PARSE_JSON: string to JSON
SELECT PARSE_JSON('{"name": "John", "age": 30}');

-- JSON_OBJECT: construct a JSON object
SELECT JSON_OBJECT('name', name, 'age', age) FROM users;

-- JSON_ARRAY: construct a JSON array
SELECT JSON_ARRAY(1, 2, 3);
```

### JSON Expansion

```sql
-- json_each / json_each_text: expand a JSON object's key-value pairs
SELECT jt.key, jt.value
FROM products,
LATERAL json_each(CAST(json_data AS JSON)) AS jt;

-- Unnest a JSON array
SELECT *
FROM orders,
LATERAL unnest(CAST(JSON_QUERY(json_data, '$.items') AS ARRAY<JSON>)) AS t(item);
```

---

## Array and MAP Functions

### Array Functions

```sql
-- Array construction
SELECT [1, 2, 3];                          -- ARRAY literal
SELECT ARRAY_GENERATE(1, 10);              -- generates [1,2,...,10]

-- Array access
SELECT arr[1] FROM t;                      -- first element (1-based)

-- Array operations
SELECT ARRAY_LENGTH([1, 2, 3]);            -- 3
SELECT ARRAY_CONTAINS([1, 2, 3], 2);       -- true
SELECT ARRAY_APPEND([1, 2], 3);            -- [1, 2, 3]
SELECT ARRAY_REMOVE([1, 2, 3, 2], 2);      -- [1, 3]
SELECT ARRAY_DISTINCT([1, 2, 2, 3]);       -- [1, 2, 3]
SELECT ARRAY_SORT([3, 1, 2]);              -- [1, 2, 3]
SELECT ARRAY_SLICE([1, 2, 3, 4], 2, 3);   -- [2, 3]
SELECT ARRAY_CONCAT([1, 2], [3, 4]);       -- [1, 2, 3, 4]
SELECT ARRAY_JOIN([1, 2, 3], ',');         -- '1,2,3'

-- Unnest an array (pivot)
SELECT order_id, tag
FROM orders, unnest(tags) AS t(tag);

-- Array aggregation
SELECT user_id, ARRAY_AGG(product_id) FROM orders GROUP BY user_id;
SELECT ARRAY_UNIQUE_AGG(tag) FROM products GROUP BY category;

-- Lambda expressions (array transformations)
SELECT ARRAY_MAP(x -> x * 2, [1, 2, 3]);           -- [2, 4, 6]
SELECT ARRAY_FILTER(x -> x > 2, [1, 2, 3, 4]);     -- [3, 4]
SELECT ARRAY_SUM(ARRAY_MAP(x -> x * x, [1,2,3]));  -- 14
```

### MAP Functions

```sql
-- MAP construction
SELECT MAP{'key1': 'value1', 'key2': 'value2'};
SELECT MAP_FROM_ARRAYS(['k1','k2'], ['v1','v2']);

-- MAP access
SELECT map_col['key1'] FROM t;

-- MAP operations
SELECT MAP_KEYS(map_col) FROM t;           -- get all keys
SELECT MAP_VALUES(map_col) FROM t;         -- get all values
SELECT MAP_SIZE(map_col) FROM t;           -- number of key-value pairs
SELECT MAP_CONTAINS_KEY(map_col, 'k1');    -- whether a key exists

-- MAP aggregation
SELECT MAP_AGG(key_col, value_col) FROM t GROUP BY group_col;
```

---

## Conditional Functions

### CASE / IF / COALESCE

```sql
-- CASE WHEN: multi-branch condition
SELECT
    order_id,
    CASE
        WHEN amount > 10000 THEN 'large'
        WHEN amount > 1000 THEN 'medium'
        ELSE 'small'
    END AS order_level
FROM orders;

-- IF: simple binary choice
SELECT IF(status = 'paid', amount, 0) AS paid_amount FROM orders;

-- IFNULL / COALESCE: NULL handling
SELECT COALESCE(phone, email, 'unknown') AS contact FROM users;
SELECT IFNULL(amount, 0) AS amount FROM orders;

-- NULLIF: returns NULL when two values are equal
SELECT NULLIF(a, b) FROM t;  -- NULL when a = b, otherwise a
-- Commonly used to avoid division by zero:
SELECT total / NULLIF(count, 0) AS avg_value FROM stats;
```

---

## Type Conversion

### CAST Function

```sql
-- Basic type conversion
CAST(value AS INT)
CAST(value AS BIGINT)
CAST(value AS DOUBLE)
CAST(value AS VARCHAR)
CAST(value AS DATE)
CAST(value AS DATETIME)
CAST(value AS DECIMAL(10, 2))
CAST(value AS JSON)
CAST(value AS ARRAY<INT>)

-- Common caveats
-- 1. String to numeric: invalid characters return NULL (no error)
SELECT CAST('abc' AS INT);  -- NULL

-- 2. Precision loss
SELECT CAST(1.999 AS INT);  -- 1 (truncated, not rounded)

-- 3. Use DECIMAL for monetary computations to avoid floating-point precision issues
SELECT CAST(0.1 + 0.2 AS DECIMAL(10,2));  -- 0.30 (exact)
SELECT 0.1 + 0.2;  -- 0.30000000000000004 (floating-point error)

-- 4. Date string conversion
SELECT CAST('2024-01-15' AS DATE);       -- standard format converts directly
SELECT CAST('20240115' AS DATE);          -- compact format also supported
```

---

## BITMAP and HLL Functions

### BITMAP Functions (Exact Deduplication)

```sql
-- Define a BITMAP column at table creation
-- CREATE TABLE: uv BITMAP BITMAP_UNION

-- Convert to BITMAP during ingestion
-- Stream Load: to_bitmap(user_id)
-- INSERT: INSERT INTO ... SELECT ..., to_bitmap(user_id) ...

-- Query
SELECT BITMAP_UNION_COUNT(uv) FROM table WHERE dt = '2024-01-15';

-- Intersection (users active on both days)
SELECT BITMAP_INTERSECT_COUNT(uv) FROM table WHERE dt IN ('2024-01-14', '2024-01-15');

-- Compute retention rate
SELECT
    BITMAP_UNION_COUNT(CASE WHEN dt = '2024-01-14' THEN uv END) AS day1_users,
    BITMAP_COUNT(
        BITMAP_AND(
            BITMAP_UNION(CASE WHEN dt = '2024-01-14' THEN uv END),
            BITMAP_UNION(CASE WHEN dt = '2024-01-15' THEN uv END)
        )
    ) AS retained_users
FROM user_bitmap_table;
```

### HLL Functions (Approximate Deduplication)

```sql
-- Define an HLL column at table creation
-- CREATE TABLE: uv HLL HLL_UNION

-- Convert to HLL during ingestion
-- Stream Load: hll_hash(user_id)

-- Query
SELECT HLL_UNION_AGG(uv) FROM table WHERE dt = '2024-01-15';
-- About 1% error

-- HLL's advantage: distinct counts can be merged across different dimensions
SELECT
    region,
    HLL_UNION_AGG(uv) AS uv
FROM table
GROUP BY region;
```
