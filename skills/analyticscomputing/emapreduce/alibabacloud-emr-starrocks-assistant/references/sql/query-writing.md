# Query Writing Best Practices

## Table of Contents

1. [SELECT Writing Conventions](#select-writing-conventions)
2. [JOIN Writing Conventions](#join-writing-conventions)
3. [Subquery vs JOIN vs CTE](#subquery-vs-join-vs-cte)
4. [WHERE Condition Optimization](#where-condition-optimization)
5. [GROUP BY and DISTINCT Optimization](#group-by-and-distinct-optimization)
6. [ORDER BY and LIMIT Optimization](#order-by-and-limit-optimization)
7. [UNION and UNION ALL](#union-and-union-all)
8. [Other Query Optimization Techniques](#other-query-optimization-techniques)

---

## SELECT Writing Conventions

### Select Only the Columns You Need

```sql
-- Anti-pattern: SELECT *
SELECT * FROM orders WHERE order_date = '2024-01-15';

-- Correct: select only the needed columns to reduce I/O and network transfer
SELECT order_id, user_id, amount, status
FROM orders
WHERE order_date = '2024-01-15';
```

**Reason:** StarRocks is a columnar engine that only reads the data files of the specified columns. `SELECT *` reads all columns and wastes I/O.

### Alias Conventions

```sql
-- Recommended: use meaningful aliases for both tables and columns
SELECT
    o.order_id,
    o.amount AS order_amount,
    u.name AS user_name
FROM orders AS o
JOIN users AS u ON o.user_id = u.user_id;
```

---

## JOIN Writing Conventions

### JOIN Type Selection

| JOIN type | Use case | Notes |
|-----------|---------|------|
| `INNER JOIN` | Both tables must match | Most common; returns only matching rows |
| `LEFT JOIN` | Left table is primary; right may be null | Keeps all rows from the left table |
| `RIGHT JOIN` | Right table is primary | Recommend rewriting as LEFT JOIN (readability) |
| `FULL OUTER JOIN` | Keep both tables | Lower performance; use with caution |
| `CROSS JOIN` | Cartesian product | Only for small datasets |
| `LEFT SEMI JOIN` | Existence check (similar to EXISTS) | Doesn't return right-table columns; filter only |
| `LEFT ANTI JOIN` | Non-existence check (similar to NOT EXISTS) | Doesn't return right-table columns; exclusion only |

### JOIN Distribution Strategies

StarRocks supports three JOIN distribution strategies. The optimizer selects automatically, but you can override via hints:

**1. Broadcast Join**

```sql
-- Automatically chosen when the right-side row estimate ≤ broadcast_row_limit (default 15,000,000 rows)
-- The small table is broadcast to all BE nodes
SELECT o.*, p.product_name
FROM orders o  -- large table
JOIN products p ON o.product_id = p.product_id;  -- small table, auto-broadcast
```

**2. Shuffle Join**

```sql
-- Automatically chosen when two large tables are joined
-- Both tables are redistributed to the same nodes by the JOIN key
SELECT o.*, l.line_amount
FROM orders o  -- large table
JOIN order_lines l ON o.order_id = l.order_id;  -- large table
```

**3. Colocate Join**

```sql
-- Tables in the same Colocate Group already share the same distribution
-- Local JOIN, zero network transfer, best performance
SELECT o.*, l.line_amount
FROM orders o
JOIN order_lines l ON o.order_id = l.order_id;
-- Prerequisite: both tables in the same Colocate Group with order_id as the bucket key
```

**Force a JOIN strategy with hints:**

```sql
-- Force Broadcast Join
SELECT /*+ SET_VAR(broadcast_row_limit=15000000) */ o.*, p.product_name
FROM orders o
JOIN [broadcast] products p ON o.product_id = p.product_id;

-- Force Shuffle Join
SELECT o.*, l.line_amount
FROM orders o
JOIN [shuffle] order_lines l ON o.order_id = l.order_id;

-- Force Bucket Join (local Shuffle)
SELECT o.*, l.line_amount
FROM orders o
JOIN [bucket] order_lines l ON o.order_id = l.order_id;
```

### JOIN Condition Conventions

```sql
-- Correct: JOIN conditions go in ON; filter conditions go in WHERE
SELECT o.order_id, u.name
FROM orders o
LEFT JOIN users u ON o.user_id = u.user_id
WHERE o.order_date >= '2024-01-01';  -- filter condition

-- Anti-pattern: LEFT JOIN filter condition in WHERE (effectively becomes INNER JOIN)
SELECT o.order_id, u.name
FROM orders o
LEFT JOIN users u ON o.user_id = u.user_id
WHERE u.status = 'active';  -- This filters out rows where u is NULL!

-- Correct: put right-table filter conditions in the ON clause
SELECT o.order_id, u.name
FROM orders o
LEFT JOIN users u ON o.user_id = u.user_id AND u.status = 'active';
```

### JOIN Order Optimization

```sql
-- Recommended: large table on the left, small tables on the right (helps Broadcast)
-- The optimizer usually adjusts automatically, but explicit ordering is clearer
SELECT /*+ SET_VAR(disable_join_reorder=false) */
    fact.*,
    dim1.name,
    dim2.category
FROM fact_table fact              -- largest fact table on the far left
JOIN dim_table_1 dim1 ON ...      -- smaller dimension table
JOIN dim_table_2 dim2 ON ...;     -- smaller dimension table
```

---

## Subquery vs JOIN vs CTE

### Decision Guide

| Scenario | Recommended | Reason |
|------|------|------|
| Simple existence check | `EXISTS` / `IN` | Clear semantics |
| Need to reference columns from the related table | `JOIN` | Subquery cannot return outer-table columns |
| Same result set referenced multiple times | `CTE (WITH)` | Avoids redundant computation |
| Logical layers > 2 | `CTE (WITH)` | Improves readability |
| Simple filter list | `IN (value list)` | Concise and efficient |

### CTE Writing Example

```sql
-- Use CTEs to organize a complex query in layers
WITH
-- Layer 1: filter active users
active_users AS (
    SELECT user_id, name, region
    FROM users
    WHERE last_login >= '2024-01-01'
      AND status = 'active'
),
-- Layer 2: compute per-user order statistics
user_orders AS (
    SELECT
        u.user_id,
        u.name,
        u.region,
        COUNT(*) AS order_count,
        SUM(o.amount) AS total_amount
    FROM active_users u
    JOIN orders o ON u.user_id = o.user_id
    WHERE o.order_date >= '2024-01-01'
    GROUP BY u.user_id, u.name, u.region
)
-- Final query
SELECT
    region,
    COUNT(*) AS user_count,
    SUM(order_count) AS total_orders,
    AVG(total_amount) AS avg_amount
FROM user_orders
GROUP BY region
ORDER BY total_orders DESC;
```

### Rewriting a Subquery as a JOIN

```sql
-- Anti-pattern: correlated subquery (runs once per outer row)
SELECT user_id, name,
    (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.user_id) AS order_count
FROM users u;

-- Rewrite as a JOIN (single pass)
SELECT u.user_id, u.name, COALESCE(oc.order_count, 0) AS order_count
FROM users u
LEFT JOIN (
    SELECT user_id, COUNT(*) AS order_count
    FROM orders
    GROUP BY user_id
) oc ON u.user_id = oc.user_id;
```

### Rewriting NOT IN

```sql
-- Anti-pattern: NOT IN has a NULL pitfall
SELECT * FROM orders
WHERE user_id NOT IN (SELECT user_id FROM blacklist);
-- If blacklist.user_id contains NULL, the whole result is empty!

-- Correct rewrite 1: NOT EXISTS
SELECT * FROM orders o
WHERE NOT EXISTS (
    SELECT 1 FROM blacklist b WHERE b.user_id = o.user_id
);

-- Correct rewrite 2: LEFT ANTI JOIN
SELECT o.* FROM orders o
LEFT ANTI JOIN blacklist b ON o.user_id = b.user_id;
```

---

## WHERE Condition Optimization

### Partition Pruning

Partition pruning is one of the most important optimizations, reducing scanned data by orders of magnitude.

```sql
-- Correct: reference the partition column directly; partition pruning works
SELECT * FROM events
WHERE event_date >= '2024-01-01' AND event_date < '2024-02-01';

-- Anti-pattern: wrapping the partition column in a function; partition pruning fails
SELECT * FROM events
WHERE DATE_FORMAT(event_date, '%Y-%m') = '2024-01';

-- Anti-pattern: expression computation; partition pruning fails
SELECT * FROM events
WHERE event_date - INTERVAL 7 DAY >= '2024-01-01';

-- Correct rewrite: move the computation to the constant side
SELECT * FROM events
WHERE event_date >= DATE_ADD('2024-01-01', INTERVAL 7 DAY);
```

### Bucket Pruning

```sql
-- If the table is HASH bucketed on user_id
-- Equality conditions trigger bucket pruning, scanning only matching tablets
SELECT * FROM orders WHERE user_id = 12345;  -- bucket pruning works

-- IN also supports bucket pruning
SELECT * FROM orders WHERE user_id IN (12345, 67890);  -- bucket pruning works

-- Range conditions do not support bucket pruning
SELECT * FROM orders WHERE user_id > 10000;  -- bucket pruning does not work
```

### Predicate Writing Conventions

```sql
-- 1. Avoid implicit type conversion
WHERE varchar_col = '123'     -- correct
WHERE varchar_col = 123       -- wrong: implicit conversion invalidates the index

-- 2. Avoid applying functions to columns
WHERE dt >= '2024-01-01'      -- correct
WHERE YEAR(dt) = 2024         -- wrong: cannot use the index

-- 3. LIKE prefix matching can use the sort key
WHERE name LIKE 'John%'       -- can use the prefix index
WHERE name LIKE '%John%'      -- cannot use the prefix index

-- 4. Multi-condition ordering: high selectivity first
WHERE user_id = 12345          -- high selectivity (first)
  AND status = 'active'        -- low selectivity
  AND create_date >= '2024-01-01'  -- partition pruning
```

---

## GROUP BY and DISTINCT Optimization

### GROUP BY Optimization

```sql
-- 1. Keep the GROUP BY column list short
SELECT region, COUNT(*) FROM orders GROUP BY region;  -- good

-- 2. For high-cardinality GROUP BY, consider two-stage aggregation (StarRocks enables automatically)
-- Controllable via session variable
SET new_planner_agg_stage = 2;  -- force two-stage aggregation

-- 3. Avoid GROUP BY followed by HAVING COUNT for Top-N; use a window function instead
-- Anti-pattern
SELECT region, SUM(amount)
FROM orders
GROUP BY region
HAVING SUM(amount) > 100000;

-- For Top-N, use a window function
WITH ranked AS (
    SELECT region, SUM(amount) AS total,
           ROW_NUMBER() OVER(ORDER BY SUM(amount) DESC) AS rn
    FROM orders
    GROUP BY region
)
SELECT region, total FROM ranked WHERE rn <= 10;
```

### DISTINCT Optimization

```sql
-- Low cardinality (< 10 million): COUNT(DISTINCT) is fine
SELECT COUNT(DISTINCT user_id) FROM events WHERE dt = '2024-01-15';

-- Large cardinality (billions): use approximate deduplication
SELECT APPROX_COUNT_DISTINCT(user_id) FROM events WHERE dt = '2024-01-15';
-- About 2-3% error, several times faster

-- Very high cardinality + exact precision: use a BITMAP column at table creation
-- At creation: `uv BITMAP BITMAP_UNION`
-- Query:
SELECT BITMAP_UNION_COUNT(uv) FROM events_agg WHERE dt = '2024-01-15';

-- Multi-column DISTINCT: rewrite as GROUP BY
-- Anti-pattern
SELECT DISTINCT region, category FROM products;
-- Equivalent (usually better performance)
SELECT region, category FROM products GROUP BY region, category;
```

---

## ORDER BY and LIMIT Optimization

### Basic Principles

```sql
-- 1. ORDER BY must have LIMIT (unless a global sort is truly required)
SELECT * FROM orders ORDER BY create_time DESC LIMIT 100;

-- 2. Top-N query optimization (StarRocks uses the TopN operator automatically)
SELECT * FROM orders
WHERE order_date = '2024-01-15'
ORDER BY amount DESC
LIMIT 10;

-- 3. Pagination
-- Small offset: use OFFSET directly
SELECT * FROM orders ORDER BY order_id LIMIT 20 OFFSET 100;

-- Large offset: use a WHERE cursor for pagination (avoid huge OFFSET)
SELECT * FROM orders
WHERE order_id > 10000  -- order_id of the last row on the previous page
ORDER BY order_id
LIMIT 20;
```

### Sort Key Optimization

```sql
-- If the table's sort key is (user_id, create_time)
-- The following query can leverage the sort key for acceleration
SELECT * FROM orders
WHERE user_id = 12345
ORDER BY create_time DESC
LIMIT 10;
-- Sort key prefix match + ORDER BY in the same direction as the sort key -> avoids extra sorting
```

---

## UNION and UNION ALL

```sql
-- UNION ALL: no deduplication, good performance (recommended)
SELECT user_id, 'order' AS source FROM orders WHERE dt = '2024-01-15'
UNION ALL
SELECT user_id, 'return' AS source FROM returns WHERE dt = '2024-01-15';

-- UNION: automatic deduplication, extra sorting overhead
-- Use only when deduplication is truly needed
SELECT user_id FROM orders WHERE dt = '2024-01-15'
UNION
SELECT user_id FROM returns WHERE dt = '2024-01-15';

-- Combine multiple tables then aggregate: UNION ALL first, then outer GROUP BY
SELECT source, COUNT(DISTINCT user_id)
FROM (
    SELECT user_id, 'order' AS source FROM orders
    UNION ALL
    SELECT user_id, 'return' AS source FROM returns
) t
GROUP BY source;
```

---

## Other Query Optimization Techniques

### EXISTS vs IN

```sql
-- Small result set: use IN
SELECT * FROM orders WHERE user_id IN (1, 2, 3, 4, 5);

-- Large subquery result set: use EXISTS (StarRocks auto-optimizes to Semi Join)
SELECT * FROM orders o
WHERE EXISTS (SELECT 1 FROM active_users u WHERE u.user_id = o.user_id);
```

### CASE WHEN Optimization

```sql
-- Pivot (compute multi-dimensional statistics in one SQL)
SELECT
    dt,
    COUNT(*) AS total_orders,
    COUNT(CASE WHEN status = 'paid' THEN 1 END) AS paid_count,
    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) AS cancel_count,
    SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END) AS paid_amount
FROM orders
WHERE dt >= '2024-01-01'
GROUP BY dt;
```

### LATERAL JOIN to Unnest Arrays

```sql
-- Unnest a JSON array or ARRAY column
SELECT order_id, item
FROM orders,
LATERAL unnest(split(item_ids, ',')) AS t(item);

-- Unnest an ARRAY-typed column
SELECT order_id, tag
FROM orders,
LATERAL unnest(tags) AS t(tag);
```
