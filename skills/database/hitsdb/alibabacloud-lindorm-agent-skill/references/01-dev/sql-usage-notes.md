# Lindorm SQL Usage Notes

## Table of Contents

- [Compatibility Differences from MySQL](#compatibility-differences-from-mysql)
- [Troubleshooting Unexpected Query Results](#troubleshooting-unexpected-query-results)
- [SQL Usage Notes](#sql-usage-notes)
- [HASH Sharding Notes](#hash-sharding-notes)
- [Cold and Hot Data Separation Notes](#cold-and-hot-data-separation-notes)
- [Compaction and Storage Management](#compaction-and-storage-management)

---

## Compatibility Differences from MySQL

Lindorm SQL is compatible with some features and syntax of MySQL 5.7 and 8.0. However, because the product architecture is different, some syntax or features are not fully supported.

### Lexical Element Differences

| Item | Lindorm SQL | MySQL |
|------|-------------|-------|
| Case sensitivity | Database object identifiers are strictly case-sensitive | Configurable |
| Identifier quoting | Must use backticks \` | Multiple quoting methods are supported |
| String constants | Only single quotes ' are supported | Both single quotes and double quotes are supported |

### Unsupported Data Types

- BIT type
- MEDIUMINT type
- REAL type
- All TEXT types
- DATETIME type
- UNSIGNED types other than BIGINT UNSIGNED

> For integer types such as TINYINT, INTEGER, and BIGINT, specifying an explicit length limit is not supported.

### Transaction Support

Lindorm does not support multi-row transactions, which means transactional operations that read or write multiple rows at once are not supported.

### INSERT Semantic Differences

In Lindorm SQL, INSERT is essentially UPSERT. For data with the same primary key, fields or columns involved in the write statement are directly overwritten.

> For UPDATE statements in traditional databases that use equality filters on the complete primary key, it is recommended to use INSERT instead for better performance.

**INSERT limits**:
- INSERT statements must explicitly specify the list of fields to be written.
- The field list must include at least one non-primary-key column.

### DELETE/UPDATE Limits

DELETE and UPDATE statements must specify a WHERE condition. The WHERE filter condition must clearly specify equality conditions for all primary keys so that exactly one row can be located.

> If the WHERE filter condition can locate a batch of rows, the statement cannot be executed by default. To perform batch delete or update, contact Lindorm technical support to enable the required system parameters.

**Batch operation notes**:
- Atomicity cannot be guaranteed for batch delete or update operations.
- Batch operations first query and then delete or update. Make sure the WHERE condition can efficiently hit an index whenever possible.
- Large delete operations affect performance in some query scenarios. If TTL can be configured, prefer using TTL to expire data.

### SELECT Limits

- JOIN is not supported. INNER JOIN, LEFT JOIN, and RIGHT JOIN are all unsupported and return `JOIN is not allowed in Lindorm SQL`.
- UNION and UNION ALL are not supported.
- INTERSECT and MINUS/EXCEPT are not supported. MINUS returns a syntax error. INTERSECT and EXCEPT do not return syntax errors, but trigger low-efficiency query interception at runtime and are not practically usable.

### Subquery Support

Lindorm SQL provides limited support for subqueries. The support depends on the subquery form and whether indexes are created:

| Subquery Form | Without Index | With Secondary Index | Description |
|-----------|--------|-----------|------|
| Derived table (FROM clause) | ✅ Supported | ✅ Supported | `SELECT * FROM (SELECT ...) AS t` |
| Derived table + WHERE | ✅ Supported | ✅ Supported | Outer WHERE filters the derived table result |
| Multi-level nested derived table | ✅ Supported | ✅ Supported | Multiple nested FROM subqueries |
| Scalar subquery (SELECT column) | ❌ Low-efficiency interception | ✅ Supported | `(SELECT COUNT(*) FROM ...) AS cnt` |
| WHERE IN subquery | ❌ Low-efficiency interception | ✅ Supported | The filter columns in the subquery must have indexes |
| WHERE EXISTS subquery | ❌ Low-efficiency interception | ✅ Supported | The filter columns in the subquery must have indexes |

> **Key note**: The failure of WHERE IN, EXISTS, and scalar subqueries is not caused by unsupported syntax. It happens because full table scans without indexes are rejected by the **low-efficiency query interception** mechanism. After secondary indexes are created, these statements can execute normally.

**Official documentation**: https://help.aliyun.com/zh/lindorm/user-guide/compatibility-comparison-between-lindorm-sql-and-mysql

### Window Function Support

⚠️ **Limited support**: Official compatibility documentation marks window functions as "not supported yet". The syntax does not return an error, but there may be **correctness or stability risks** because server-side computation is expensive. Tests show that ROW_NUMBER, RANK, DENSE_RANK, LEAD, SUM OVER, and AVG OVER can run correctly in the current version. LAG has a parser bug in earlier versions where `LAG(...) AS alias` returns an error. Use window functions **with caution** in production. Prefer using the compute engine (OLAP) for window calculations.

| Window Function | Description | Example |
|---------|------|------|
| `ROW_NUMBER()` | Row number | `ROW_NUMBER() OVER (PARTITION BY col ORDER BY col)` |
| `RANK()` | Ranking. Equal values share the same rank and leave gaps. | `RANK() OVER (ORDER BY col DESC)` |
| `DENSE_RANK()` | Ranking. Equal values share the same rank without gaps. | `DENSE_RANK() OVER (ORDER BY col)` |
| `SUM() OVER` | Cumulative sum | `SUM(amount) OVER (PARTITION BY user_id)` |
| `AVG() OVER` | Cumulative average | `AVG(score) OVER (PARTITION BY class_id)` |
| `LEAD(col, offset)` | Following row | `LEAD(amount, 1) OVER (ORDER BY id)` |
| `LAG(col, offset)` | Previous row | `LAG(amount, 1) OVER (ORDER BY id)` |

### Low-efficiency Query Interception

Lindorm intercepts queries that may cause full table scans by default and returns the error `DoNotRetryIOException: Detect inefficient query`.

**Trigger scenario**: Columns in the WHERE condition have no indexes and data cannot be located by primary key.

**Solutions**:

1. **Create a secondary index** (recommended): Create a secondary index for columns in the WHERE condition.
   ```sql
   CREATE INDEX idx_region ON orders (region) INCLUDE (user_name, amount);
   -- After that, WHERE region = 'east-cn' can use the index.
   ```
2. **Use HINT to allow full table scans** (use with caution because it may affect performance):
   ```sql
   SELECT /*+ _l_allow_filtering_ */ * FROM orders WHERE region = 'east-cn';
   ```
3. **Add a primary key range condition**:
   ```sql
   SELECT * FROM orders WHERE id >= 1 AND id < 100 AND region = 'east-cn';
   ```

> **Index availability time**: After an index is created, wait until index building is complete before it takes effect. Secondary indexes (KV) take about 10 seconds, and search indexes (SEARCH) take about 30 seconds. Queries executed immediately may still return low-efficiency query errors.

> Index type selection: Secondary indexes (KV) support equality, range, and prefix LIKE queries. Suffix LIKE queries such as `%xxx` require search indexes (SEARCH). See [table-design.md](table-design.md).

### LIKE and Range Queries

Secondary indexes (KV) support range queries and LIKE prefix matching:

| Query Type | Secondary Index (KV) | Search Index (SEARCH) |
|---------|-------------|-----------------|
| Equality `=` | ✅ | ✅ |
| IN | ✅ | ✅ |
| Range `> < >= <=` | ✅ | ✅ |
| BETWEEN | ✅ | ✅ |
| LIKE prefix `'xxx%'` | ✅ | ✅ |
| LIKE single character `'xxx_'` | ✅ | ✅ |
| LIKE suffix `'%xxx'` | ❌ | ✅ |
| LIKE contains `'%xxx%'` | ❌ | ✅ |
| Multidimensional query | ❌ | ✅ |

```sql
-- Secondary index: supports equality, range, and LIKE prefix queries.
CREATE INDEX idx_amount ON orders (amount) INCLUDE (user_name, product);
-- After that, these queries can all use the index:
-- WHERE amount = 3999
-- WHERE amount > 1000
-- WHERE amount BETWEEN 1000 AND 5000
-- WHERE product LIKE 'phone%'

-- Search index: supports suffix fuzzy matching, multidimensional queries, and analyzer queries.
-- ⚠️ Search indexes must be enabled in the console first. Otherwise, SERVER INTERNAL ERROR is returned.
CREATE INDEX idx_search USING SEARCH ON orders (region, product, amount);
-- Supported: WHERE product LIKE '%phone%'
-- Supported: WHERE region = 'east-cn' AND amount > 1000
```

### Analyzer Query (MATCH AGAINST)

Search indexes support analyzer queries by using the `MATCH ... AGAINST` syntax:

```sql
-- Create a search index with an analyzer.
CREATE INDEX idx_text USING SEARCH ON articles (
  content(type=text, analyzer=ik)
);

-- Analyzer query: matches records that contain "feature introduction".
SELECT * FROM articles WHERE MATCH(content) AGAINST('feature introduction');
-- Matches records that contain "feature", "introduction", or "feature introduction".
```

**Supported analyzers**: `standard` (default), `ik` (recommended for Chinese), `english`, `whitespace`, and `comma`.

> For details, see [table-design.md](table-design.md#search-index-enablement-conditions).

### ALTER TABLE Limits

- Adding and deleting columns are supported, but renaming columns is not supported.
- Modifying column definitions is not supported, including column type, precision, default value, and other attributes.
- Adding or removing indexes through ALTER TABLE statements is not supported.
- Modifying the primary key of a table is not supported.

### Other Unsupported Syntax

- RENAME TABLE
- REPLACE
- SELECT ... FOR SHARE
- Explicit transaction syntax, such as START TRANSACTION, COMMIT, and ROLLBACK
- CREATE TABLE AS SELECT
- Table import and export syntax, such as IMPORT and LOAD
- EXPLAIN ANALYZE
- FOREIGN KEY
- Unique indexes (UNIQUE INDEX)

---

## Troubleshooting Unexpected Query Results

The storage model of the Lindorm wide table engine is based on LSM-Tree. Data writes are visible immediately. Data does not become visible only after a delay. If query results are unexpected, troubleshoot based on the following causes.

### 1. Data Was Not Written Correctly or the Query Was Issued Before the Write

If the write path has issues, data write delays or write failures may occur. Add HINT parameters to the query condition to specify that the write timestamp of returned data should be included in query results. Use the timestamp to determine whether the query happened before the write.

### 2. STRING Fields Contain Abnormal Stop Characters or Invisible Characters

If STRING fields contain invisible characters, query results may be unexpected.

**Troubleshooting method**: Use a range query to confirm whether similar issues exist, such as `WHERE orderID > "1000" LIMIT 1`.

> Lindorm does not support stop characters in the middle of STRING fields. Stop characters at the end are normal.

### 3. Column Names in Query Conditions Are Incorrect

- **Column name case error**: Lindorm column names are case-sensitive.
- **Column family not specified**: If the multi-family feature is used, the family must be specified in query conditions, such as `WHERE meta:column1=xxx`.

### 4. The Table Has TTL Configured and Data Has Expired at Query Time

The unit of TTL is seconds (s), and the unit of timestamps is milliseconds (ms).

**Common issues**:
- If an earlier timestamp is specified during data writing and the difference between that timestamp and the current time is greater than the TTL value, the data may be cleaned up during writing.
- If timestamp usage does not follow time semantics and custom version numbers are used instead, such as small numbers like 1, 2, 3, and 4, data is very likely to expire and be cleaned up.
- If large custom timestamps or version numbers are used, such as microsecond or nanosecond timestamps, data may fail to expire and be cleaned up correctly.

### 5. Cell TTL Is Configured and Data Has Expired at Query Time

The unit of Cell TTL is milliseconds (ms). If Cell TTL is configured on a KV, its expiration time is `min{expiration time configured on the Cell, expiration time configured on the table property}`.

### 6. The Timestamp of the Delete Request Is Unreasonable

Delete requests support setting timestamps or version numbers. The value indicates that data in the row or column before the specified time or version is deleted.

- If the timestamp of the delete request is smaller than the timestamp or version number of the written data, the row is not deleted.
- If the delete request has a large timestamp or version number, the delete request continues to take effect after submission, and subsequently written data may be deleted immediately.

> SQL access does not support setting delete timestamps.

### 7. The VERSIONS Table Property Is Set to 0

A VERSIONS value of 0 means data in the table is not retained. Any written data is deleted and cannot be queried.

**Solution**: Drop and recreate the table, or change the VERSIONS property to a value greater than or equal to 1.

### 8. A Table with the IMMUTABLE Property Is Updated

IMMUTABLE means the table supports only whole-row writes, where one row is written by one UPSERT statement. Updates and deletes are not allowed.

---

## SQL Usage Notes

### SELECT * Limits for Dynamic Columns

Tables with dynamic columns enabled may contain a large number of dynamic columns, and the table schema is not fixed. Full table scans on such tables cause heavy I/O consumption.

**Solution**: Add a LIMIT clause to the SELECT statement to limit the number of returned results, such as `SELECT * FROM test LIMIT 10`.

### Common Table Property Units

| Property | Unit | Description |
|------|------|------|
| TTL | Seconds (s) | Data validity period |
| COMPACTION_MAJOR_PERIOD | Milliseconds (ms) | Major Compaction period |
| Timestamp | Milliseconds (ms) | Data version time |
| Cell TTL | Milliseconds (ms) | Expiration time of a single KV |

---

## HASH Sharding Notes

The primary key HASH sharding feature uses a HASH function to distribute data across different shards or regions, avoiding data skew and uneven load.

### DDL Limits

- The HASH function expression must be placed at the beginning.
    - Incorrect: `PRIMARY KEY(p1, hash32(p1), p2)`
    - Correct: `PRIMARY KEY(hash32(p1), p1, p2)`
- When a HASH algorithm is used for a column in the primary key or an index, that column must be specified as a primary key column or index column.
- Primary key columns with a HASH algorithm specified cannot be modified.
- After primary key HASH sharding is used, data import through bulkload is not supported.

### DML Limits

**Write data**: You do not need to add HASH-related parameters to SQL statements. The system automatically generates and fills HASH values.

**Query data**:
- Values of all primary key columns that use the HASH algorithm must be specified. Otherwise, the system cannot calculate HASH values, which causes a full table scan.
- For primary key columns that use the HASH algorithm, query conditions must be equality conditions. Range queries are not supported.

```sql
-- Recommended usage.
SELECT * FROM t1 WHERE p1=1 AND p2=1;

-- Not recommended: the value of primary key column p1 is not specified, which causes a full table scan.
SELECT * FROM t1 WHERE p2=1;

-- Incorrect: range queries on HASH columns are not supported.
SELECT * FROM t1 WHERE p2=1 AND p1>2 AND p1<8;
```

---

## Cold and Hot Data Separation Notes

### When Data Enters Cold Storage

Lindorm asynchronously archives cold data from hot storage to cold storage through the Compaction mechanism:

- The default system trigger time is half of the cold-hot boundary.
- The minimum is 1 day.
- The maximum is half of the Major Compaction period, which is 20 days by default.

For example, if the cold-hot boundary is 3 days, a Compaction archive task is automatically triggered every 1.5 days by default.

### Manually Trigger Compaction

You can manually trigger Compaction by using `major_compact 'tableName'`.

> The `major_compact` command increases I/O load and is not recommended for frequent use.

If data has not entered cold storage after Compaction is executed, the data may not have been written to disk yet. Perform a flush operation first.

### Cold and Hot Data Separation by Custom Time Column

- If a row does not contain a custom time column, the row is retained in hot storage and is not separated into cold storage.
- If updated cold data is not the custom time column, the updated data remains cold data.
- If the updated data is in the custom time column, cold and hot data must be repartitioned based on the newly written time value.

### Cold and Hot Data Separation by Timestamp

Because updated data records a new timestamp, cold data becomes hot data after it is updated.

### HOT_ONLY Query Notes

Query statements can use `HOT_ONLY` or `_l_hot_only_` to query only hot data. However, because archiving data to cold storage is triggered periodically, some cold data may remain in hot storage and appear in query results.

**Solution**: Add a hot data time range to query conditions:

```sql
SELECT /*+ _l_hot_only_(true), _l_ts_min_(1000), _l_ts_max_(2001) */ * FROM test WHERE p1>1;
```

### Inconsistent Cold Data Between Index Tables and Primary Tables

The cold data archiving processes of primary tables and index tables are independent and triggered periodically. This can cause inconsistent data remaining in hot storage between primary tables and index tables, resulting in inconsistent cold data being queried.

**Solution**: Add the hot data time range to query conditions.

### Triggering Compaction Immediately After Cold and Hot Data Separation Is Enabled

Cold data transfer is triggered when the current time minus the generation time of the oldest file is greater than the cold data archive period.

---

## Compaction and Storage Management

### Purpose of Compaction

- Cleans up expired data (TTL).
- Cleans up delete markers left by delete operations.
- Archives cold and hot data.
- Compresses data to reduce space usage.

### Automatic Compaction Trigger Period

The default automatic trigger period is 20 days. In TTL scenarios, the default period is `min(TTL value, 20 days)`.

**Modify trigger period**:

```sql
-- Change the automatic trigger period to 2 days. The unit is milliseconds.
ALTER TABLE <tableName> SET 'COMPACTION_MAJOR_PERIOD'='172800000';
```

### Impact of Compaction on Business

Compaction consumes CPU when processing data. When CPU resources are sufficient, it has little impact on business and can help improve read performance and release storage space.

**Monitor Compaction status**: In instance monitoring, view Wide Table Engine Metrics > Cluster Load > Compaction Queue Length. If the value keeps growing or remains unchanged, a large number of queued tasks may exist.

**Optimization recommendations**:
- If CPU utilization is less than 40%, Wide Table 2.6.5 and later support automatically adjusting parameters based on load. Upgrade to a later minor version.
- If CPU utilization is greater than 40%, increase the number of wide table engine nodes.

### Storage Keeps Increasing After TTL Is Configured

Use instance monitoring to view the Compaction queue length and confirm whether tasks are backlogged. If there is a large backlog, data cleanup may be delayed.

If there are no queued tasks and the read/write load is low, manually execute Compaction or adjust the Major Compaction period.

### Handling Disk Capacity Limits

- Scale out hot storage capacity.
- Use `DROP TABLE` to directly delete useless tables and immediately release storage space.
- Use `TRUNCATE TABLE` to clear table data and immediately release storage space.

> Do not use DELETE to directly delete data. Lindorm delete operations directly write Delete Markers, which are fully cleaned up only when the next Compaction operation is triggered.

### Unable to Delete Data After Disk Capacity Reaches the Limit

After disk capacity reaches the limit, the system forbids all data writes, including delete markers. If delete markers cannot be written, data that needs to be deleted cannot be cleaned up by Compaction.

### Compression Algorithm and Encoding Method

Set the table compression algorithm COMPRESSION to ZSTD and the encoding method DATA_BLOCK_ENCODING to INDEX, and then execute Major Compact to reduce storage space.

```sql
ALTER TABLE <tablename> SET 'COMPRESSION' = 'ZSTD','DATA_BLOCK_ENCODING' = 'INDEX';
ALTER TABLE <tablename> COMPACT;
```

> If the table is created through SQL, these settings are configured by default and do not need to be set again.

