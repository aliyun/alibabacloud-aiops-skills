# Lindorm SQL Syntax Reference

The following section includes commonly used DDL and DML statements.

## Important Constraints
> **This constraint has the highest priority and must be strictly followed.**
1. **Do not infer or associate**: answer user questions only based on content explicitly documented in this Skill. Do not infer, associate, or generate SQL syntax, parameters, features, or configurations that are not present in the documentation.
2. **State uncertainty explicitly**: if the documentation does not contain relevant information, clearly tell the user "This content is not included in the current documentation" and guide the user to official documentation.
3. **Do not mix sources**: do not present syntax or features from other databases, such as MySQL, HBase, or PostgreSQL, as Lindorm features.
4. **Code examples require sources**: generated code examples must be based on templates in the documentation. Parameters and syntax must be consistent with the documentation.

## Execution Steps
1. If the SQL statement mentioned by the user is included in the documentation below, reply with the documented information first.
2. If the SQL statement mentioned by the user is not included below, query official documentation before replying.
   - **DDL**: https://help.aliyun.com/zh/lindorm/developer-reference/wide-table-ddl/
   - **DML**: https://help.aliyun.com/zh/lindorm/developer-reference/wide-table-dml/
   - **DCL**: https://help.aliyun.com/zh/lindorm/developer-reference/wide-table-dcl/
3. If the SQL statement mentioned by the user is neither included below nor found in official documentation, clearly tell the user "This content is not included in the current documentation".

## DDL Statements

> For detailed table creation syntax, data types, and table properties, see table-design.md.

### CREATE TABLE - Create Table

**Basic syntax**:
```sql
CREATE TABLE [IF NOT EXISTS] table_name (
    column_name data_type [NOT NULL],
    ...
    PRIMARY KEY (column_name [, column_name]...)
)
[WITH (option = value, ...)]
```

**Example - Basic table creation**:
```sql
CREATE TABLE IF NOT EXISTS user_profile (
    user_id VARCHAR NOT NULL,
    nickname VARCHAR,
    age INTEGER,
    balance DOUBLE,
    created_at TIMESTAMP,
    PRIMARY KEY (user_id)
);
```

**Example - Composite primary key**:
```sql
CREATE TABLE IF NOT EXISTS order_detail (
    order_id VARCHAR NOT NULL,
    item_seq INTEGER NOT NULL,
    product_name VARCHAR,
    quantity INTEGER,
    price DOUBLE,
    PRIMARY KEY (order_id, item_seq)
);
```

**Example - With table properties**:
```sql
CREATE TABLE IF NOT EXISTS logs (
    log_id VARCHAR NOT NULL,
    level VARCHAR,
    message VARCHAR,
    created_at TIMESTAMP,
    PRIMARY KEY (log_id)
) WITH (
    TTL = '604800',           -- Expire after 7 days
    COMPRESSION = 'ZSTD',     -- ZSTD compression
    NUMREGIONS = 10           -- Pre-split into 10 regions
);
```

**Example - Pre-split table creation**:
```sql
CREATE TABLE IF NOT EXISTS metrics (
    metric_id VARCHAR NOT NULL,
    value DOUBLE,
    ts TIMESTAMP,
    PRIMARY KEY (metric_id)
) WITH (
    NUMREGIONS = 8,
    STARTKEY = '0',
    ENDKEY = '9'
);
```

**Example - Specify split keys**:
```sql
CREATE TABLE IF NOT EXISTS events (
    event_id VARCHAR NOT NULL,
    event_type VARCHAR,
    payload VARCHAR,
    PRIMARY KEY (event_id)
) WITH (
    SPLITKEYS = 'a,b,c,d,e,f,g,h,i'
);
```

### Common Table Properties

| Property | Type | Description | Example |
|------|------|------|------|
| TTL | INT | Data validity period in seconds | TTL = '86400' (1 day) |
| COMPRESSION | STRING | Compression algorithm: SNAPPY/ZSTD/LZ4 | COMPRESSION = 'ZSTD' |
| NUMREGIONS | INT | Number of pre-split regions | NUMREGIONS = 16 |
| STARTKEY | STRING | Partition start key | STARTKEY = '0' |
| ENDKEY | STRING | Partition end key | ENDKEY = 'z' |
| SPLITKEYS | STRING | Custom split points | SPLITKEYS = 'a,m,z' |
| MUTABILITY | STRING | Index write mode | MUTABILITY = 'MUTABLE_LATEST' |
| CONSISTENCY | STRING | Consistency level | CONSISTENCY = 'strong' |

### ALTER TABLE - Modify Table

**Add columns**:
```sql
ALTER TABLE user_profile ADD COLUMN email VARCHAR;
ALTER TABLE user_profile ADD COLUMN phone VARCHAR, address VARCHAR;
```

**Modify TTL**:
```sql
ALTER TABLE logs SET TTL = '2592000';  -- Change to 30 days
ALTER TABLE logs SET TTL = '';          -- Cancel TTL; data never expires
```

### DROP TABLE - Drop Table

```sql
DROP TABLE IF EXISTS table_name;
```

### TRUNCATE TABLE - Truncate Table

```sql
TRUNCATE TABLE table_name;
```

### CREATE INDEX - Create Index

**Secondary index**:
```sql
-- Create during table creation
CREATE TABLE orders (
    order_id VARCHAR NOT NULL,
    user_id VARCHAR,
    status VARCHAR,
    amount DOUBLE,
    PRIMARY KEY (order_id),
    INDEX idx_user USING KV (user_id),
    INDEX idx_status USING KV (status) INCLUDE (amount)
);

-- Create a secondary index separately
CREATE INDEX idx_user USING KV ON orders (user_id);
```

**Search index**:

> ⚠️ **Important**: Search indexes must be enabled in the console first: Wide Table Engine -> Search Index -> Enable Now. Otherwise, creation may return `SERVER INTERNAL ERROR`. See [table-design.md](table-design.md#search-index-enablement-conditions).

```sql
-- Basic search index
CREATE INDEX idx_search USING SEARCH ON orders (status);

-- Search index with analyzer
CREATE INDEX idx_text USING SEARCH ON articles (
  title(type=text, analyzer=ik),
  content(type=text, analyzer=ik)
);

-- Analyzer query
SELECT * FROM articles WHERE MATCH(content) AGAINST('keyword');
```

### SHOW / DESCRIBE - View Information

```sql
-- View all databases
SHOW DATABASES;

-- View all tables
SHOW TABLES;

-- View table schema
DESCRIBE table_name;

-- View table creation statement
SHOW CREATE TABLE table_name;

-- View indexes
SHOW INDEX FROM table_name;

-- View SQL engine version. It returns VERSION, BUILD_TIME, and GIT_COMMIT.
SELECT @@VERSION;
```

### USE - Switch Database

```sql
USE database_name;
```

After switching, all subsequent SQL operations are executed in this database by default. When using a JDBC connection, you can also specify the default database in the URL, such as `jdbc:lindorm:table:url=http://<host>:33060;database=mydb`.

---

## DML Statements

### UPSERT - Insert or Update Data

UPSERT is the recommended write method in Lindorm. If the primary key exists, the row is updated; otherwise, the row is inserted.

> **INSERT semantics**: In Lindorm, INSERT and UPSERT have the same semantics. When a primary key conflict occurs, the row is overwritten instead of returning an error. When connecting through the MySQL protocol, INSERT has client-side batch optimization, so INSERT is recommended.

**Single-row write**:
```sql
UPSERT INTO user_profile (user_id, nickname, age) 
VALUES ('u001', 'Alice', 25);
```

**Write with timestamp** (using HINT):
```sql
-- Specify the timestamp of the written data in milliseconds.
UPSERT /*+ _l_ts_(1704067200000) */ INTO user_profile (user_id, nickname, age) 
VALUES ('u001', 'Alice', 25);
```

**Batch write** (PreparedStatement):
```java
String sql = "UPSERT INTO user_profile (user_id, nickname, age) VALUES (?, ?, ?)";
PreparedStatement ps = conn.prepareStatement(sql);

for (int i = 0; i < 100; i++) {
    ps.setString(1, "u" + i);
    ps.setString(2, "user_" + i);
    ps.setInt(3, 20 + i % 50);
    ps.addBatch();
}
ps.executeBatch();
```

### SELECT - Query Data

**Basic query**:
```sql
SELECT * FROM user_profile WHERE user_id = 'u001';
```

**Query specific columns** (recommended):
```sql
SELECT user_id, nickname, age FROM user_profile WHERE user_id = 'u001';
```

**Range query**:
```sql
SELECT * FROM user_profile 
WHERE user_id >= 'u001' AND user_id < 'u100';
```

**Sorting and pagination**:
```sql
SELECT * FROM user_profile 
ORDER BY user_id 
LIMIT 100 OFFSET 0;
```

**Conditional query**:
```sql
SELECT * FROM user_profile 
WHERE age > 25 AND age < 35;

SELECT * FROM user_profile 
WHERE nickname LIKE 'A%';

SELECT * FROM user_profile 
WHERE user_id IN ('u001', 'u002', 'u003');
```

**Aggregate query**:
```sql
SELECT COUNT(*) FROM user_profile;
SELECT MAX(age), MIN(age), AVG(age) FROM user_profile;
```

**HINT usage**:
```sql
-- Force low-efficiency queries, such as full table scans.
SELECT /*+ _l_allow_filtering_ */ * FROM user_profile;

-- Specify the operation timeout in milliseconds.
SELECT /*+ _l_operation_timeout_(30000) */ * FROM user_profile WHERE age > 25;

-- Force using an index.
SELECT /*+ _l_force_index_('idx_name') */ * FROM user_profile WHERE name = 'test';

-- Ignore indexes.
SELECT /*+ _l_ignore_index_ */ * FROM user_profile WHERE name = 'test';
```

### UPDATE - Update Data

**Important**: UPDATE must specify the complete primary key condition.

```sql
-- Correct: specify the complete primary key.
UPDATE user_profile SET age = 26 WHERE user_id = 'u001';

-- Incorrect: batch update is not supported.
UPDATE user_profile SET age = 26 WHERE age > 25;  -- Returns an error.
```

### DELETE - Delete Data

**Single-row delete**:
```sql
DELETE FROM user_profile WHERE user_id = 'u001';
```

**Composite primary key delete**:
```sql
DELETE FROM order_detail WHERE order_id = 'o001' AND item_seq = 1;
```

### JSON Data Write and Query

> For data type definitions, see [table-design.md](table-design.md).

**Write methods**:
```sql
-- Method 1: directly write a JSON string.
UPSERT INTO tb(p1, c2) VALUES(1, '{"k1": 4, "k2": {"k3": {"k4": 4}}}');

-- Method 2: use the json_object function.
UPSERT INTO tb(p1, c2) VALUES(2, json_object('k1', 2, 'k2', '2'));
-- Equivalent to: UPSERT INTO tb(p1,c2) VALUES(2,'{"k1":2,"k2":"2"}');

-- Method 3: use the json_array function.
UPSERT INTO tb(p1, c2) VALUES(3, json_array(1, 2, json_object('k1', 3, 'k2', '3')));
-- Equivalent to: UPSERT INTO tb(p1,c2) VALUES(3,'[1,2,{"k1":3,"k2":"3"}]');
```

**Query JSON fields**:
```sql
-- Get a value from a JSON object in the SELECT clause.
SELECT p1, json_extract(c2, '$.k1') AS k1_value FROM tb WHERE p1 = 1;

-- Nested path query.
SELECT json_extract(c2, '$.k2.k3.k4') FROM tb WHERE p1 = 4;

-- Array index access.
SELECT json_extract(c2, '$[2].k2') FROM tb WHERE p1 = 3;

-- WHERE condition filtering.
SELECT * FROM tb 
WHERE p1 >= 1 AND p1 < 4 
AND json_extract(c2, '$.k2') > '0';
```

---

## Common Functions

### String Functions

> Requires Wide Table Engine 2.5.1.1 or later.

| Function | Description | Example |
|------|------|------|
| `CONCAT(s1, s2, ...)` | Concatenates multiple strings | `SELECT CONCAT('a','b','c')` → `abc` |
| `LENGTH(s)` | Calculates string length | `SELECT LENGTH('hello')` → `5` |
| `LOWER(s)` | Converts to lowercase | `SELECT LOWER('ABC')` → `abc` |
| `UPPER(s)` | Converts to uppercase | `SELECT UPPER('abc')` → `ABC` |
| `TRIM(s)` | Removes leading and trailing spaces | `SELECT TRIM('  ab  ')` → `ab` |
| `SUBSTR(s, pos[, len])` | Extracts a substring | `SELECT SUBSTR('hello', 2, 3)` → `ell` |
| `REPLACE(s, from, to)` | Replaces a substring | `SELECT REPLACE('abc', 'b', 'x')` → `axc` |
| `REVERSE(s)` | Returns the reversed string | `SELECT REVERSE('abc')` → `cba` |
| `MD5(s)` | Calculates an MD5 hash | `SELECT MD5('abc')` → `900150983cd24fb0...` |
| `SHA256(s)` | Calculates a SHA256 hash | `SELECT SHA256('abc')` → `ba7816bf8f01cfea...` |
| `START_WITH(s, prefix)` | Checks whether the string starts with the specified prefix | `SELECT START_WITH('hello', 'he')` → `true` |

**Regular expression functions**:
```sql
-- REGEXP_REPLACE: regular expression replacement. Supports specifying the start position.
SELECT REGEXP_REPLACE('abcbc', 'b', 'x', 2);  -- axcxc

-- REGEXP_SUBSTR: extracts a substring by regular expression.
SELECT REGEXP_SUBSTR('abc123def', '[0-9]+');  -- 123

-- MATCH: checks whether a value matches a regular expression.
SELECT * FROM table WHERE MATCH(column, 'pattern');
```

### Aggregate Functions

| Function | Description | Example |
|------|------|------|
| `COUNT(*)` | Counts rows | `SELECT COUNT(*) FROM table` |
| `COUNT(column)` | Counts non-NULL values | `SELECT COUNT(name) FROM table` |
| `SUM(column)` | Calculates a sum. Numeric types only. | `SELECT SUM(amount) FROM orders` |
| `AVG(column)` | Calculates an average. Numeric types only. | `SELECT AVG(price) FROM products` |
| `MAX(column)` | Calculates the maximum value | `SELECT MAX(score) FROM results` |
| `MIN(column)` | Calculates the minimum value | `SELECT MIN(score) FROM results` |

**Advanced aggregate functions** (Wide Table Engine 2.7.9 or later):
```sql
-- HEAD: returns the first non-NULL value and supports sorting.
SELECT HEAD(temperature ORDER BY time) FROM sensor;  -- Earliest temperature.
SELECT HEAD(temperature ORDER BY time DESC) FROM sensor;  -- Latest temperature.

-- GROUP_CONCAT: concatenates strings in each group.
SELECT region, GROUP_CONCAT(device_id) FROM sensor GROUP BY region;
-- Result: north-cn | dev1,dev2,dev3

-- GROUP_CONCAT with sorting and separator.
SELECT region, GROUP_CONCAT(device_id ORDER BY time SEPARATOR '|') 
FROM sensor GROUP BY region;
-- Result: north-cn | dev1|dev2|dev3

-- GROUP_CONCAT with DISTINCT.
SELECT region, GROUP_CONCAT(DISTINCT device_id) FROM sensor GROUP BY region;
```

### Time Functions

> Requires Wide Table Engine 2.7.8 or later and Lindorm SQL 2.8.7.0 or later.

| Function | Description | Example |
|------|------|------|
| `NOW()` | Returns the current timestamp | `SELECT NOW()` → `2024-01-15 17:30:45` |
| `DATE_FORMAT(ts, format)` | Formats a timestamp | See the examples below |
| `FROM_UNIXTIME(seconds)` | Converts a Unix timestamp to TIMESTAMP | `SELECT FROM_UNIXTIME(1704067200)` |
| `UNIX_TIMESTAMP(ts)` | Converts TIMESTAMP to a Unix timestamp | `SELECT UNIX_TIMESTAMP('2024-01-01 00:00:00')` |
| `DATEDIFF(ts1, ts2)` | Calculates the date difference in days | `SELECT DATEDIFF('2024-01-05', '2024-01-01')` → `4` |

**DATE_FORMAT format specifiers**:
```sql
SELECT DATE_FORMAT('2024-01-15 17:30:45', '%Y-%m-%d %H:%i:%s');
-- 2024-01-15 17:30:45

SELECT DATE_FORMAT('2024-01-15 17:30:45', '%Y-%m-%d %H:%i');
-- 2024-01-15 17:30

SELECT DATE_FORMAT('2024-01-15 17:30:45', 'at %T on %b %D, %Y');
-- at 17:30:45 on JAN 15th, 2024
```

| Specifier | Description | Example |
|--------|------|------|
| `%Y` | Four-digit year | 2024 |
| `%y` | Two-digit year | 24 |
| `%m` | Two-digit month | 01-12 |
| `%d` | Two-digit day | 01-31 |
| `%H` | Hour in 24-hour format | 00-23 |
| `%h` | Hour in 12-hour format | 01-12 |
| `%i` | Minute | 00-59 |
| `%s` / `%S` | Second | 00-59 |
| `%T` | Time (HH:mm:ss) | 17:30:45 |
| `%D` | Day with ordinal suffix | 1st, 2nd, 15th |
| `%b` | Abbreviated month name | Jan, Feb |
| `%M` | Full month name | January |
| `%W` | Full weekday name | Monday |
| `%a` | Abbreviated weekday name | Mon |
| `%p` | AM/PM | AM |

**NOW() and INTERVAL time arithmetic**:
```sql
-- NOW(): returns the current timestamp.
SELECT NOW();  -- 2024-01-15 17:30:45

-- INTERVAL time arithmetic: adds or subtracts time periods.
SELECT NOW() - INTERVAL 24 HOUR;       -- 24 hours ago.
SELECT NOW() + INTERVAL 30 MINUTE;    -- 30 minutes later.
SELECT NOW() - INTERVAL 7 DAY;        -- 7 days ago.

-- Common INTERVAL units.
-- YEAR, MONTH, DAY, HOUR, MINUTE, SECOND
-- Combined usage.
SELECT NOW() - INTERVAL 1 DAY - INTERVAL 12 HOUR;  -- 1 day and 12 hours ago.

-- Used in WHERE conditions.
SELECT * FROM sensor WHERE ts > NOW() - INTERVAL 24 HOUR;  -- Data from the last 24 hours.
```

**FROM_UNIXTIME examples**:
```sql
-- Converts a Unix timestamp to TIMESTAMP.
SELECT FROM_UNIXTIME(1704067200);  -- 2024-01-01 08:00:00 (+08:00 time zone)

-- Supports millisecond precision by using decimals.
SELECT FROM_UNIXTIME(1704067200.123);  -- 2024-01-01 08:00:00.123

-- Formats output at the same time.
SELECT FROM_UNIXTIME(1704067200, '%Y-%m-%d');  -- 2024-01-01
```


**Common JSON functions**:

**Constructor functions**:
- `json_object(key1, value1, ...)`: builds a JSON object.
  ```sql
  SELECT json_object('name', 'Alice', 'age', 25);
  -- {"name": "Alice", "age": 25}
  ```
- `json_array(value1, value2, ...)`: builds a JSON array.
  ```sql
  SELECT json_array('Java', 'Python', 'Go');
  -- ["Java", "Python", "Go"]
  ```

**Extraction functions**:
- `json_extract(json_doc, path)`: extracts a JSON value and returns the JSON type.
  ```sql
  SELECT json_extract('{"name": "Alice"}', '$.name');
  -- "Alice"
  ```
- `json_extract_string(json_doc, path)`: extracts and converts to VARCHAR.
  ```sql
  SELECT json_extract_string('{"name": "Alice"}', '$.name');
  -- Alice (VARCHAR)
  ```
- `json_extract_long(json_doc, path)`: extracts and converts to BIGINT.
  ```sql
  SELECT json_extract_long('{"id": 123456}', '$.id');
  -- 123456 (BIGINT)
  ```
- `json_extract_double(json_doc, path)`: extracts and converts to DOUBLE.
  ```sql
  SELECT json_extract_double('{"score": 95.5}', '$.score');
  -- 95.5 (DOUBLE)
  ```

**Path syntax**:
- `$.key`: accesses the key of an object.
- `$[index]`: accesses an array index, starting from 0.
- `$.key1.key2`: accesses nested fields.
- `$[*]`: wildcard that matches all array elements.

**Containment check functions**:
- `json_contains(target, candidate[, path])`: checks whether the specified value is contained.
  ```sql
  -- Checks whether an array contains an element.
  SELECT json_contains('["Java", "Python"]', '"Java"');
  -- 1 (true)
  
  -- Checks whether an object contains a property.
  SELECT json_contains('{"a": 1, "b": 2}', '{"a": 1}');
  -- 1 (true)
  
  -- Checks the specified path.
  SELECT json_contains('{"skills": ["Java", "Python"]}', '"Java"', '$.skills');
  -- 1 (true)
  
  -- Used in WHERE conditions.
  SELECT * FROM table WHERE json_contains(data, '"active"', '$.status');
  ```

**Update functions**:
- `json_set(json_doc, path, value[, path, value]...)`: inserts or updates values.
  ```sql
  SELECT json_set('{"a": 1}', '$.b', 2);
  -- {"a": 1, "b": 2}
  ```
- `json_insert(json_doc, path, value)`: inserts only when the path does not exist.
  ```sql
  SELECT json_insert('{"a": 1}', '$.b', 2);
  -- {"a": 1, "b": 2}
  ```
- `json_replace(json_doc, path, value)`: updates only when the path exists.
  ```sql
  SELECT json_replace('{"a": 1}', '$.a', 10);
  -- {"a": 10}
  ```
- `json_remove(json_doc, path[, path]...)`: deletes values at specified paths.
  ```sql
  SELECT json_remove('{"a": 1, "b": 2}', '$.b');
  -- {"a": 1}
  ```

**Notes**:
- Writing a non-JSON object or non-JSON string into a JSON column returns an error.
- Comparison rules for different data types are the same as MySQL.

---

## Special Syntax

### HINT Syntax Details

HINT is supplementary SQL syntax that can change how SQL statements are executed. HINT must immediately follow the `INSERT`, `UPSERT`, `DELETE`, or `SELECT` keyword.

> Requires Wide Table Engine 2.3.1 or later.

**Basic syntax**:
```sql
/*+ hint1, hint2, ... */
```

#### HINT Parameter List

| HINT | Type | Description | Supported Statements |
|------|------|------|----------|
| `_l_operation_timeout_(N)` | INT | DML operation timeout in milliseconds. The default value is 120000. | UPSERT, DELETE, UPDATE, SELECT |
| `_l_allow_filtering_` | - | Allows low-efficiency full table scan queries. | SELECT |
| `_l_force_index_('idx')` | STRING | Forces the specified index to be used. | SELECT |
| `_l_ignore_index_` | - | Ignores indexes and queries the primary table directly. | SELECT |
| `_l_ts_(N)` | BIGINT | Specifies the timestamp for writes or queries in milliseconds. | UPSERT, SELECT |
| `_l_versions_(N)` | INT | Returns the latest N versions of data. | SELECT |
| `_l_ts_min_(N)` | BIGINT | Filters results and returns data with timestamp >= N. | SELECT |
| `_l_ts_max_(N)` | BIGINT | Filters results and returns data with timestamp < N. | SELECT |
| `_l_hot_only_` / `_l_hot_only_(true)` | BOOLEAN | Queries hot storage data only. | SELECT |

#### Timeout and Performance Control

```sql
-- Set the operation timeout to 30 seconds.
SELECT /*+ _l_operation_timeout_(30000) */ COUNT(*) FROM big_table;

-- Allows full table scans when the WHERE condition does not contain the primary key.
SELECT /*+ _l_allow_filtering_ */ * FROM users WHERE age > 30;

-- Combined usage.
SELECT /*+ _l_operation_timeout_(30000), _l_allow_filtering_ */ * 
FROM users WHERE age > 30;
```

#### Index Control

```sql
-- Force using the specified index.
SELECT /*+ _l_force_index_('idx_user_name') */ * FROM users WHERE name = 'test';

-- Ignore indexes and query the primary table directly for performance comparison.
SELECT /*+ _l_ignore_index_ */ * FROM users WHERE name = 'test';
```

**Note**: `_l_force_index_` and `_l_ignore_index_` cannot be used together.

#### Multi-version Data Management

Lindorm supports storing multiple versions of data for each column. Versions are identified by timestamps. A larger timestamp indicates a newer version.

**Create a multi-version table**:
```sql
-- VERSIONS='5' means that each column can retain up to five versions.
CREATE TABLE sensor_data (
    device_id VARCHAR,
    temperature DOUBLE,
    PRIMARY KEY(device_id)
) WITH (VERSIONS='5');

-- Modify the number of versions for an existing table.
ALTER TABLE sensor_data SET 'VERSIONS' = '10';
```

**Write with a specified timestamp**:
```sql
-- Write with a specified timestamp in milliseconds.
UPSERT /*+ _l_ts_(1704067200000) */ INTO sensor_data(device_id, temperature) 
VALUES ('dev001', 25.5);

UPSERT /*+ _l_ts_(1704067260000) */ INTO sensor_data(device_id, temperature) 
VALUES ('dev001', 26.0);  -- Same device, new version.
```

**Query multi-version data**:
```sql
-- Query data at a specified timestamp.
SELECT /*+ _l_ts_(1704067200000) */ device_id, temperature 
FROM sensor_data WHERE device_id = 'dev001';

-- Query the latest N versions.
SELECT /*+ _l_versions_(3) */ device_id, temperature, temperature_l_ts 
FROM sensor_data WHERE device_id = 'dev001';

-- Query a timestamp range [min, max).
SELECT /*+ _l_ts_min_(1704067200000), _l_ts_max_(1704153600000) */ 
    device_id, temperature, temperature_l_ts 
FROM sensor_data WHERE device_id = 'dev001';
```

**View column timestamps**: add the `_l_ts` suffix after the column name.
```sql
-- temperature_l_ts returns the timestamp of the temperature column.
SELECT /*+ _l_versions_(2) */ device_id, temperature, temperature_l_ts 
FROM sensor_data;
```

#### Hot Data Query

After cold storage is enabled, you can use HINT to query only data in hot storage:

```sql
-- Query hot data only.
SELECT /*+ _l_hot_only_ */ * FROM sensor_data WHERE device_id = 'dev001';
SELECT /*+ _l_hot_only_(true) */ * FROM sensor_data WHERE device_id = 'dev001';

-- Query all data, including cold data. This is equivalent to not using the HINT.
SELECT /*+ _l_hot_only_(false) */ * FROM sensor_data WHERE device_id = 'dev001';
```

**Note**: Querying cold data only is not supported.

### Dynamic Columns

Lindorm supports dynamic columns. You can write new columns without predefining them.

```sql
-- Write a dynamic column.
UPSERT INTO user_profile (user_id, _dyn_col_name1) VALUES ('u001', 'value1');

-- Query a dynamic column.
SELECT user_id, _dyn_col_name1 FROM user_profile WHERE user_id = 'u001';
```

### TTL

```sql
-- View the TTL setting of a table.
SHOW CREATE TABLE table_name;

-- Modify TTL.
ALTER TABLE table_name SET TTL = '86400';

-- Cancel TTL. Data never expires.
ALTER TABLE table_name SET TTL = '';
```

**Note**: Lindorm does not support row-level TTL. TTL is a table-level property.

---

## TSDB Time Series Engine SQL Operations

> **Connection method**: The time series engine uses the Avatica protocol and the fixed port 8242. The connection URL format is `jdbc:lindorm:tsdb:url=http://<tsdb_host>:8242`. For details, see [sql-client-guide.md](sql-client-guide.md).

### Create a Time Series Table

```sql
CREATE TABLE ts_test (
  p VARCHAR NOT NULL,
  t TIMESTAMP NOT NULL,
  v DOUBLE,
  PRIMARY KEY(p, t)
);
```

### Write Time Series Data

```sql
UPSERT INTO ts_test (p, t, v) VALUES ('cpu', '2024-01-01 10:00:00', 85.5);
```

### Time Range Query

```sql
SELECT * FROM ts_test WHERE p='cpu' AND t >= '2024-01-01 00:00:00';
```

### Specify Time Precision

Use the `-precision` parameter, which is available only for the Avatica protocol, to specify timestamp display precision. Valid values are `ms` for milliseconds, `us` for microseconds, `ns` for nanoseconds, and `rfc3339`, which is the default value.

---

## SQL Notes

### Differences from MySQL

| Feature | MySQL | Lindorm SQL |
|------|-------|-------------|
| Write statement | INSERT/UPDATE | UPSERT (recommended) |
| UPDATE scope | Batch updates supported | Single-row only |
| Auto-increment primary key | Supported | Not supported |
| Foreign key | Supported | Not supported |
| Transaction | ACID | Single-row atomicity |
| JOIN | Supported | Not supported |

### Transaction Limits

Lindorm does not support multi-row transactions, which means transactional reads and writes across multiple rows are not supported. When using ORM frameworks, transactions must be disabled. UPDATE supports only single-row updates, and the WHERE clause must specify the complete primary key.

### Connection Idle Timeout

The server actively disconnects connections that have been idle for 10 minutes. After a long period without operations, probe the connection status again.

### Low-efficiency Queries (Full Table Scan)

#### What Is a Low-efficiency Query?

If a query statement has filter conditions but those conditions cannot effectively use an existing primary key or index, the query must scan the full table. Such a query is considered a **low-efficiency query**. Lindorm detects and blocks low-efficiency queries by default.

**Error symptom**: after executing the query, the wide table engine returns the following error:

```
This query may be a full table scan and thus may have unpredictable performance
```

> Another error form: `DoNotRetryIOException: Detect inefficient query`

#### Typical Low-efficiency Query Scenarios

Assume that table `test` has a composite primary key `(p1, p2, p3)`, where `p1` is the first primary key column:

```sql
-- ❌ Low-efficiency query: the WHERE clause does not contain the first primary key column p1.
SELECT * FROM test WHERE p2 = 10;
SELECT * FROM test WHERE p3 = 'abc';
SELECT * FROM test WHERE p2 < 30 AND p3 = 'abc';

-- ✅ Efficient query: the WHERE clause contains the first primary key column p1.
SELECT * FROM test WHERE p1 = 'a' AND p2 = 10;
SELECT * FROM test WHERE p1 = 'a';
```

> **Leftmost prefix principle**: Primary keys and secondary indexes of the wide table engine follow matching rules similar to MySQL composite indexes. The system matches columns one by one starting from the first, leftmost column of the primary key or index key. If the query condition does not contain the first column, the primary key or index cannot be hit.

#### Solutions for Low-efficiency Queries

Recommended priority order:

| Priority | Solution | Description | Risk |
|--------|------|------|------|
| 1 | Optimize WHERE conditions | Include the first primary key column or satisfy the leftmost prefix principle | None |
| 2 | Modify primary key design | Redesign the primary key to match query patterns | Table rebuild required |
| 3 | Create a secondary index | Create a secondary index for query columns | Slight write performance decrease |
| 4 | Create a search index | Suitable for multi-column and multidimensional search scenarios | Additional index overhead |
| 5 | `/*+ _l_allow_filtering_ */` Hint | Force execution of a low-efficiency query | **⚠ Stability risk** |

> **Index availability time**: After an index is created, wait until index building is complete before it takes effect. Secondary indexes (KV) take about 10 seconds, and search indexes (SEARCH) take about 30 seconds. Queries executed immediately may still return low-efficiency query errors.

**Example for solution 5**:

```sql
-- Original query that returns an error.
SELECT * FROM test WHERE p2 = 10;

-- Add Hint to force execution.
SELECT /*+ _l_allow_filtering_ */ * FROM test WHERE p2 = 10;
```

> **⚠ Risk reminder**:
> - Forcing a low-efficiency query means a full table scan. When the data volume is large, the query takes a long time and consumes significant I/O and CPU resources.
> - It may affect response times of other queries on the same instance.
> - Always use it with `LIMIT` to restrict the scan range.
> - For long-term solutions, prefer creating indexes or optimizing query conditions.

Reference documentation: https://help.aliyun.com/zh/lindorm/developer-reference/sql-faq

### Performance Recommendations

1. **Primary key queries are the fastest**: Use the primary key as the query condition whenever possible.
2. **Avoid full table scans**: WHERE conditions on non-indexed columns are blocked as low-efficiency queries. See the preceding "Low-efficiency Queries (Full Table Scan)" section.
3. **Limit returned rows**: Use LIMIT to avoid returning a large amount of data.
4. **Use PreparedStatement**: It is required for batch operations.
5. **Selective SELECT**: Query only the columns you need.
6. **Use derived tables for subqueries**: For WHERE IN or EXISTS subqueries, make sure the filter columns in the subquery have indexes.
7. **Use search indexes for suffix fuzzy matching**: LIKE prefix matching such as `xxx%` can use secondary indexes, while suffix fuzzy matching such as `%xxx` requires a search index (SEARCH).

### Window Functions

⚠️ **Limited support**: Official compatibility documentation marks window functions as "not supported yet". The syntax does not return an error, but there may be **correctness or stability risks** because server-side computation is expensive. Tests show that ROW_NUMBER, RANK, DENSE_RANK, LEAD, SUM OVER, and AVG OVER can run correctly in the current version. LAG has a parser bug in earlier versions. Use window functions **with caution** in production. Prefer using the compute engine (OLAP) for window calculations.

```sql
-- ROW_NUMBER: assigns row numbers within each partition.
SELECT id, user_name, amount,
       ROW_NUMBER() OVER (PARTITION BY user_name ORDER BY amount DESC) AS rn
FROM orders;

-- RANK: ranking.
SELECT id, user_name, amount,
       RANK() OVER (ORDER BY amount DESC) AS rnk
FROM orders;

-- SUM OVER: grouped cumulative sum.
SELECT id, user_name, amount,
       SUM(amount) OVER (PARTITION BY user_name) AS user_total
FROM orders;

-- LEAD/LAG: references preceding or following rows.
SELECT id, amount,
       LAG(amount) OVER (ORDER BY id) AS prev_amt,
       LEAD(amount) OVER (ORDER BY id) AS next_amt
FROM orders;
```

### Subqueries

Lindorm SQL supports derived tables, which are subqueries in the FROM clause. WHERE IN and EXISTS subqueries require index support:

```sql
-- Derived table. Recommended and can be used even without indexes.
SELECT * FROM (
    SELECT user_name, SUM(amount) AS total FROM orders GROUP BY user_name
) AS t WHERE total > 4000;

-- WHERE IN subquery. The filter columns in the subquery must have indexes.
SELECT * FROM orders
WHERE user_name IN (SELECT name FROM users WHERE city = 'Hangzhou');

-- Scalar subquery. Index support is required.
SELECT id, user_name,
       (SELECT COUNT(*) FROM orders o2 WHERE o2.user_name = orders.user_name) AS order_cnt
FROM orders;
```

> For details, see the subquery support section in [sql-usage-notes.md](sql-usage-notes.md).

### Reserved Keywords

**Query the complete keyword list**: Use the `information_schema.KEYWORDS` system view to query all keywords in the SQL engine and whether they are **reserved keywords** or **non-reserved keywords**:

```sql
-- Query all keywords, including reserved and non-reserved markers.
SELECT * FROM information_schema.KEYWORDS;

-- Query reserved keywords only. They cannot be used as table names or column names.
SELECT * FROM information_schema.KEYWORDS WHERE RESERVED = 1;
```

The following are common reserved keywords, which cannot be used as table names or column names:

```
SELECT, FROM, WHERE, AND, OR, NOT, IN, LIKE, BETWEEN,
IS, NULL, TRUE, FALSE, CREATE, ALTER, DROP, TABLE,
INDEX, PRIMARY, KEY, VALUES, UPSERT, UPDATE, DELETE,
INSERT, INTO, SET, ORDER, BY, ASC, DESC, LIMIT, OFFSET
```

> **Note**: The preceding list contains only common reserved keywords. Query `information_schema.KEYWORDS` for the complete list. Non-reserved keywords can be used as identifiers, but avoid using them to prevent compatibility conflicts with future versions.

If you need to use reserved words, enclose them in double quotation marks:
```sql
CREATE TABLE "order" ("select" VARCHAR, PRIMARY KEY("select"));
```
