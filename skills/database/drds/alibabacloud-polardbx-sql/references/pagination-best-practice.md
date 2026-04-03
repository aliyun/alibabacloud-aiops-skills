---
title: PolarDB-X Efficient Pagination Query Best Practices
---

# PolarDB-X Efficient Pagination Query Best Practices

Pagination is a common database operation. This document describes how to efficiently perform paging in PolarDB-X distributed databases, meeting the following goals:

- Traverse all data in a large table (billions of rows), returning a fixed batch size (e.g., 1000 rows)
- Traverse in data write-time order
- Constant paging performance that doesn't degrade as page numbers increase
- No data omissions

## Why LIMIT M, N Is Not Suitable for Deep Pagination

### Cost in Standalone Databases

The cost of `LIMIT M, N` is **O(M+N)**. The database cannot directly locate the Mth row; it must scan from the first row, skip M rows, and return the next N rows.

```sql
-- Get 1000 rows after the 10000th row
SELECT * FROM t1 ORDER BY gmt_create LIMIT 10000, 1000;
-- Actually scans 10000 + 1000 = 11000 records
```

The deeper you page, the more data needs to be scanned, and the worse the performance.

### Even Higher Cost in Distributed Databases

In distributed databases, `LIMIT M, N` requires **each shard** to return the first M+N rows to the coordinator node for merge sorting:

```sql
-- During distributed execution, each shard needs to execute:
SELECT * FROM t1 ORDER BY gmt_create LIMIT 0, 11000;
-- Results from all shards are aggregated at the CN node for sorting, then the final 1000 rows are selected
```

Total cost = O(M+N) x network transfer overhead. The amplification effect of network transfer is even more significant with many shards.

> For scenarios with small data volumes, low concurrency, and modest performance requirements, using `LIMIT M, N` directly is fine. For performance-sensitive scenarios, use the methods described below.

## Efficient Pagination: Keyset Pagination (Cursor Pagination)

Core idea: **Record the sort value of the last row in each batch and use it as the starting condition in the WHERE clause for the next batch**, avoiding scanning data that has already been paged through.

### Scenario 1: Tables Using New Sequence (AUTO Mode Default)

In AUTO mode databases, auto-increment primary keys default to New Sequence, which is **globally ordered** — the ID value represents the chronological order of data writes.

```sql
-- First batch
SELECT * FROM t1 ORDER BY id LIMIT 1000;

-- Record the id value of the last row as last_id, then for each subsequent batch:
SELECT * FROM t1 WHERE id > last_id ORDER BY id LIMIT 1000;
```

Since `id` is an ordered index, the database can directly locate the scan starting position. The cost is only the 1000 rows in the result set, regardless of which page you're on.

> You can check the table's auto-increment strategy with `SHOW SEQUENCES` and the database mode with `SHOW CREATE DATABASE`.

### Scenario 2: Sort Columns May Have Duplicates (e.g., Time Columns, Group Sequence IDs)

For tables with Group Sequence (mode=drds), ID order doesn't represent write time; or when sorting by a time column where time values may be duplicated.

**Incorrect approach** (will lose data or have duplicates):

```sql
-- Wrong: when gmt_create has duplicates, > will lose data, >= will have duplicates
SELECT * FROM t1 WHERE gmt_create > ? ORDER BY gmt_create LIMIT 1000;
```

**Correct approach**: Use `(sort_column, id)` combination as the cursor, with tuple comparison or equivalent conditions:

```sql
-- Method 1: Tuple comparison (recommended, supported by PolarDB-X)
SELECT * FROM t1
WHERE (gmt_create, id) > (?, ?)
ORDER BY gmt_create, id
LIMIT 1000;

-- Method 2: Equivalent expansion (for databases that don't support tuple comparison)
SELECT * FROM t1
WHERE gmt_create >= ?
  AND (gmt_create > ? OR id > ?)
ORDER BY gmt_create, id
LIMIT 1000;
```

Both methods are equivalent. In PolarDB-X, **tuple comparison (Method 1) is recommended**.

### Complete Traversal Workflow

```
1. First batch query: SELECT * FROM t1 ORDER BY gmt_create, id LIMIT 1000;
2. Record the last row's gmt_create and id
3. Each subsequent batch: SELECT * FROM t1 WHERE (gmt_create, id) > (last_gmt_create, last_id) ORDER BY gmt_create, id LIMIT 1000;
4. When the result set is empty, traversal is complete
```

## Per-Shard Traversal (Advanced Scenario)

When queries don't include the partition key, pagination queries are cross-partition. Performance is usually fine at low concurrency. But in the following extreme scenarios, you can traverse shard by shard:

- Many shards (e.g., >= 256)
- Very high stability requirements with no tolerance for unpredictable factors
- No strict data ordering requirements

### Steps

1. Get the table's topology information:

```sql
SHOW TOPOLOGY FROM t1;
```

2. Use HINT to specify a shard and paginate within a single shard:

```sql
/*+TDDL:NODE('partition_name')*/
SELECT * FROM t1 WHERE (gmt_create, id) > (?, ?) ORDER BY gmt_create, id LIMIT 1000;
```

3. Outer loop iterates through all shards.

## Index Requirements

The sort columns for pagination queries **must have appropriate indexes**; otherwise, each query requires a full table scan and sort:

| Sort Method | Required Index |
|---------|---------|
| `ORDER BY id` | Primary key index (usually exists) |
| `ORDER BY gmt_create, id` | `(gmt_create, id)` composite index |
| `ORDER BY c1, gmt_create, id` (with WHERE c1 = ?) | `(c1, gmt_create, id)` composite index |

```sql
-- Example: Create a composite index for pagination queries
ALTER TABLE t1 ADD INDEX idx_page (gmt_create, id);

-- With filter conditions
ALTER TABLE t1 ADD INDEX idx_page_c1 (c1, gmt_create, id);
```

## Java Application Considerations

### JDBC Parameter Settings

| Parameter | Setting | Reason |
|------|------|------|
| `netTimeoutForStreamingResults` | `0` | Avoid streaming read timeouts |
| `socketTimeout` | Set as needed (milliseconds) | Avoid long queries being disconnected |

### Statement Settings

| Setting | Value | Reason |
|--------|---|------|
| `setFetchSize` | `Integer.MIN_VALUE` | Enable streaming reads to avoid loading the entire result set into memory (OOM) |
| `autocommit` | `true` | Avoid pagination queries creating long transactions |

### Java Code Example

```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;

public class PaginationExample {
    public static void main(String[] args) throws Exception {
        String url = "jdbc:mysql://<host>:3306/<database>"
            + "?netTimeoutForStreamingResults=0&socketTimeout=600000";
        String user = "<user>";
        String password = "<password>";

        boolean first = true;
        Object lastGmtCreate = null;
        long lastId = -1;
        int totalRows = 0;

        while (true) {
            try (Connection conn = DriverManager.getConnection(url, user, password)) {
                PreparedStatement ps;
                if (first) {
                    ps = conn.prepareStatement(
                        "SELECT * FROM t1 ORDER BY gmt_create, id LIMIT 1000");
                    first = false;
                } else {
                    ps = conn.prepareStatement(
                        "SELECT * FROM t1 "
                        + "WHERE gmt_create >= ? AND (gmt_create > ? OR id > ?) "
                        + "ORDER BY gmt_create, id LIMIT 1000");
                    ps.setObject(1, lastGmtCreate);
                    ps.setObject(2, lastGmtCreate);
                    ps.setLong(3, lastId);
                }

                ResultSet rs = ps.executeQuery();
                lastGmtCreate = null;
                lastId = -1;

                while (rs.next()) {
                    totalRows++;
                    lastGmtCreate = rs.getObject("gmt_create");
                    lastId = rs.getLong("id");
                    // Process row data...
                }

                if (lastId == -1) {
                    // No more data, traversal complete
                    break;
                }
            }
        }
        System.out.println("Total rows: " + totalRows);
    }
}
```

## Data Export Scenario

If the purpose of pagination is data export, it's recommended to use PolarDB-X's open-source **Batch Tool**, which has more extensive export optimizations built for PolarDB-X:

- [Batch Tool Documentation](https://help.aliyun.com/zh/polardb/polardb-for-xscale/use-batch-tool-to-export-and-import-data)

## Method Comparison

| Method | Performance | Applicable Scenarios | Notes |
|------|------|---------|---------|
| `LIMIT M, N` | O(M+N), poor deep pagination | Shallow pagination, small data, low concurrency | Even higher cost in distributed systems |
| Keyset pagination (id) | O(N), constant | AUTO mode tables, traverse in write order | Requires globally ordered id |
| Keyset pagination (sort_col, id) | O(N), constant | Sort columns with possible duplicates | Requires (sort_col, id) composite index |
| Per-shard traversal | O(N), constant | Many shards, relaxed ordering requirements | Requires SHOW TOPOLOGY + HINT |
| Batch Tool | Internally optimized | Data export | Dedicated tool with richer features |

## FAQ

**Q: Why not use LIMIT M, N + OFFSET?**

The cost of `LIMIT M, N` is O(M+N), and deep pagination performance degrades severely with large datasets. Keyset pagination cost is always O(N), regardless of the page number.

**Q: Can tuple comparison `(gmt_create, id) > (?, ?)` use indexes?**

Yes. In PolarDB-X, if there's a `(gmt_create, id)` composite index, tuple comparison can leverage the index for range scans.

**Q: Can I skip ORDER BY when sorting?**

No. In both standalone and distributed databases, the return order is undefined without `ORDER BY`. In distributed databases, the order of data returned from different shards is random — you must explicitly specify `ORDER BY`.

**Q: Why should autocommit be set to true?**

Pagination traversal is a long-running process. If pagination queries run within a transaction, it creates a long transaction that consumes database resources and may cause issues. Keeping `autocommit=true` ensures each query is independent.
