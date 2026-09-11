> Loaded on demand — copy-pasteable DQL templates for common analytics shapes. Skip unless the agent is generating a SELECT from scratch and wants a template to start from.

# MaxCompute SQL common pattern templates

For text2sql scenarios, this file provides MaxCompute **DQL (SELECT query)** templates. When generating SQL, prefer matching one of these patterns over building from scratch. For partition discovery (latest partition value, partition format), see [partition-guide.md](partition-guide.md). For dialect rules, see [maxcompute-select-guide.md](maxcompute-select-guide.md).

**Template conventions**:

- Values such as `'<partition-value>'`, `'<start-date>'`, `'<end-date>'`, and `<row-count>` are explicit placeholders, not MaxCompute scheduler variables. Replace them with values from authoritative context or user confirmation before execution. If the date, time zone, business calendar, metric formula, threshold, or requested row count is missing, ask instead of guessing.
- Table and column names in templates (`orders`, `order_id`, `user_id`, …) are placeholders — replace them with verified identifiers; prefer explicit columns over `SELECT *`. When the outer template must preserve all source columns (PIVOT output, pure paging passthrough, etc.) `*` is acceptable.
- Match the user's requested output. Do not add an arbitrary `LIMIT`, metric definition, threshold, or date merely to make a template executable.

---

## 1. Top-N per group

NL example: "Top 3 highest-paid people per department".

```sql
SELECT employee_id, name, department, salary
FROM (
    SELECT employee_id, name, department, salary,
           ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rn
    FROM employees
    WHERE ds = '<partition-value>'
) tmp
WHERE rn <= 3;
```

**Note**: Do NOT use `GROUP BY + LIMIT` — MaxCompute's `LIMIT` is global. You must use a window function. In the inner subquery, only `SELECT` the business columns you will actually use plus `rn`; do not return `rn` in the final result.

---

## 2. Dedup, keep latest row

NL example: "Keep each user's most recent order".

```sql
SELECT order_id, user_id, amount, create_time
FROM (
    SELECT order_id, user_id, amount, create_time,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY create_time DESC) AS rn
    FROM orders
    WHERE ds = '<partition-value>'
) tmp
WHERE rn = 1;
```

**Variant — dedup by multiple columns**:
```sql
SELECT user_id, product_id, qty, update_time
FROM (
    SELECT user_id, product_id, qty, update_time,
           ROW_NUMBER() OVER (PARTITION BY user_id, product_id ORDER BY update_time DESC) AS rn
    FROM user_products
    WHERE ds = '<partition-value>'
) tmp
WHERE rn = 1;
```

---

## 3. Cumulative sum / running total

NL example: "Cumulative sales by date".

```sql
SELECT
    ds,
    daily_amount,
    SUM(daily_amount) OVER (ORDER BY ds ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_amount
FROM daily_sales
WHERE ds >= '<start-date>' AND ds <= '<end-date>';
```

**Note**: You must explicitly specify `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`; do not rely on the default frame.

---

## 4. Year-over-year / month-over-month

NL example: "Monthly sales and MoM growth rate".

Use wording and established business definitions to resolve ratio versus
percentage, zero-denominator handling, rounding, and calendar alignment. Ask
only for choices that remain unknown and would change the requested result. Add
a row limit only when the user requested bounded output.

Use the `LAG(1)` form below only when the input contains exactly one row for
every consecutive calendar month. If months can be missing or duplicated,
build a verified month series first or self-join on a verified previous-month
key.

```sql
SELECT
    month_id,
    amount,
    LAG(amount, 1) OVER (ORDER BY month_id) AS prev_month_amount,
    ROUND((amount - LAG(amount, 1) OVER (ORDER BY month_id))
          / LAG(amount, 1) OVER (ORDER BY month_id)
          * <confirmed-scale-factor>, <confirmed-decimal-places>) AS mom_growth
FROM monthly_sales;
```

Add `ORDER BY month_id LIMIT <row-count>` only when bounded ordered output is
requested. For unbounded ordered output, follow the validation and cost guidance
in [maxcompute-select-guide.md](maxcompute-select-guide.md).

**Year-over-year (same month last year)** — use this `LAG(12)` form only when
the input contains exactly one row for every consecutive calendar month. If
months can be missing or duplicated, build a verified month series first or
self-join on a verified same-month-last-year key.

```sql
SELECT
    month_id,
    amount,
    LAG(amount, 12) OVER (ORDER BY month_id) AS same_month_last_year,
    ROUND((amount - LAG(amount, 12) OVER (ORDER BY month_id))
          / LAG(amount, 12) OVER (ORDER BY month_id)
          * <confirmed-scale-factor>, <confirmed-decimal-places>) AS yoy_growth
FROM monthly_sales;
```

Add bounded ordering only when requested, as described for the MoM pattern.

---

## 5. Consecutive N days active

NL example: "Users who logged in for 3+ consecutive days".

```sql
SELECT user_id, MIN(ds) AS start_date, MAX(ds) AS end_date, COUNT(*) AS consecutive_days
FROM (
    SELECT user_id, ds,
           DATEADD(TO_DATE(ds, 'yyyy-mm-dd'),
                   -ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY ds), 'dd') AS grp
    FROM (
        SELECT DISTINCT user_id, ds
        FROM user_login
        WHERE ds >= '<start-date>' AND ds <= '<end-date>'
    ) t1
) t2
GROUP BY user_id, grp
HAVING COUNT(*) >= 3;
```

**Core idea**: subtract the row number from the date — consecutive dates collapse to the same `grp` value.

> **Precondition**: confirm the partition format from table metadata. This template uses ISO dates; for compact dates, use `TO_DATE(ds, 'yyyymmdd')` and supply compact range values.

---

## 6. Row-to-column (PIVOT)

NL example: "Total amount per order type, per user".

Use PIVOT only when the verified project supports it. If execution returns an unsupported-syntax error, use the CASE WHEN form below when it preserves the requested semantics.

**Method 1: PIVOT**
```sql
SELECT *
FROM (
    SELECT user_id, order_type, amount
    FROM orders
    WHERE ds = '<partition-value>'
) src
PIVOT (
    SUM(amount)
    FOR order_type IN ('<type-a>' AS type_a, '<type-b>' AS type_b)
) pvt;
-- PIVOT restrictions:
--   * The top level of PIVOT (...) must be an aggregate function — you cannot wrap another regular function (e.g. ROUND(SUM(amount),2) errors)
--   * Scalar expressions inside the aggregate are allowed (e.g. SUM(amount * rate))
--   * Cannot mix in window functions / table functions; values in the IN list must be constant literals
```

**Method 2: CASE WHEN**
```sql
SELECT
    user_id,
    SUM(CASE WHEN order_type = '<type-a>' THEN amount ELSE 0 END) AS type_a_amount,
    SUM(CASE WHEN order_type = '<type-b>' THEN amount ELSE 0 END) AS type_b_amount
FROM orders
WHERE ds = '<partition-value>'
GROUP BY user_id;
```

---

## 7. Column-to-row (UNPIVOT)

NL example: "Turn monthly metric columns into rows".

**Method 1: UNPIVOT when supported**
```sql
SELECT user_id, metric_name, metric_value
FROM monthly_metrics
UNPIVOT (
    metric_value FOR metric_name IN (revenue, cost, profit)
) unpvt
WHERE ds = '<partition-value>';
```

**Method 2: UNION ALL (alternative)**
```sql
SELECT user_id, 'revenue' AS metric_name, revenue AS metric_value FROM monthly_metrics WHERE ds = '<partition-value>'
UNION ALL
SELECT user_id, 'cost', cost FROM monthly_metrics WHERE ds = '<partition-value>'
UNION ALL
SELECT user_id, 'profit', profit FROM monthly_metrics WHERE ds = '<partition-value>';
```

---

## 8. Array explode (LATERAL VIEW)

NL example: "Explode the user-tags array".

```sql
SELECT t.user_id, tag.tag_value
FROM user_tags t
LATERAL VIEW EXPLODE(t.tags) tag AS tag_value
WHERE t.ds = '<partition-value>';
```

**Explode with index**:
```sql
SELECT t.user_id, tag.pos AS tag_index, tag.val AS tag_value
FROM user_tags t
LATERAL VIEW POSEXPLODE(t.tags) tag AS pos, val
WHERE t.ds = '<partition-value>';
```

**OUTER (preserve users with no tags)**:
```sql
SELECT t.user_id, tag.tag_value
FROM user_tags t
LATERAL VIEW OUTER EXPLODE(t.tags) tag AS tag_value
WHERE t.ds = '<partition-value>';
```

---

## 9. JSON field extraction

NL example: "Extract user behavior from a JSON log".

```sql
-- Extract a single-level field
SELECT
    GET_JSON_OBJECT(log_content, '$.user_id') AS user_id,
    GET_JSON_OBJECT(log_content, '$.action') AS action,
    GET_JSON_OBJECT(log_content, '$.timestamp') AS event_time
FROM raw_logs
WHERE ds = '<partition-value>';

-- Extract a nested field
SELECT
    GET_JSON_OBJECT(log_content, '$.user.name') AS user_name,
    GET_JSON_OBJECT(log_content, '$.user.age') AS user_age
FROM raw_logs
WHERE ds = '<partition-value>';

-- Extract an element of a JSON array
SELECT
    GET_JSON_OBJECT(log_content, '$.items[0].name') AS first_item_name
FROM raw_logs
WHERE ds = '<partition-value>';
```

---

## 10. MAP operations

NL example: "Extract a specific key from a property MAP".

```sql
-- Extract a MAP value
SELECT user_id, properties['city'] AS city
FROM user_profiles
WHERE ds = '<partition-value>';

-- Explode a MAP into rows
SELECT t.user_id, kv.key AS prop_key, kv.value AS prop_value
FROM user_profiles t
LATERAL VIEW EXPLODE(t.properties) kv AS key, value
WHERE t.ds = '<partition-value>';

-- Parse a string into a MAP and extract
SELECT
    STR_TO_MAP(params, '&', '=')['source'] AS traffic_source
FROM page_views
WHERE ds = '<partition-value>';
```

---

## 11. Latest partition

For dynamically resolving the latest partition value, see [partition-guide.md](partition-guide.md). Use `aliyun maxc meta latest-partition <table> --json` for inspection. Use `MAX_PT('project.table')` only when its level-1 lexicographic ordering and completeness semantics match the verified table design.

---

## 12. EXISTS / NOT EXISTS rewrite

NL example: "Find users who have not placed any orders".

**Method 1: LEFT ANTI JOIN**
```sql
SELECT u.*
FROM users u
LEFT ANTI JOIN orders o ON u.user_id = o.user_id AND o.ds = '<partition-value>'
WHERE u.ds = '<partition-value>';
```

**Method 2: NOT EXISTS**
```sql
SELECT u.*
FROM users u
WHERE u.ds = '<partition-value>'
  AND NOT EXISTS (
    SELECT 1 FROM orders o WHERE o.user_id = u.user_id AND o.ds = '<partition-value>'
  );
```

**"Users who placed at least one order" — LEFT SEMI JOIN**
```sql
SELECT u.*
FROM users u
LEFT SEMI JOIN orders o ON u.user_id = o.user_id AND o.ds = '<partition-value>'
WHERE u.ds = '<partition-value>';
```

---

## 13. N-day retention / cohort retention

NL example: "Daily new-user cohorts and their next-day / 7-day / 30-day retention".

Before using this pattern, confirm the authoritative definition of first activity, qualifying return activity, cohort date, observation window, and N-day semantics. Prefer a governed first-activity table. If none exists, derive first activity only from an explicitly bounded history window that the user accepts, and disclose that users active before the boundary may be misclassified.

```sql
-- <first-active-table> must be the authoritative source confirmed for this metric.
WITH cohort AS (
    SELECT user_id, cohort_ds
    FROM <first-active-table>
    WHERE cohort_ds >= '<cohort-start>' AND cohort_ds <= '<cohort-end>'
),
active AS (
    -- Bound the scan to the confirmed cohort and observation window.
    SELECT DISTINCT user_id, ds
    FROM events
    WHERE ds >= '<cohort-start>' AND ds <= '<observation-end>'
)
SELECT
    c.cohort_ds,
    COUNT(DISTINCT c.user_id) AS cohort_size,
    COUNT(DISTINCT CASE WHEN DATEDIFF(TO_DATE(a.ds, 'yyyymmdd'), TO_DATE(c.cohort_ds, 'yyyymmdd'), 'dd') = 1
                        THEN a.user_id END) AS d1_retained,
    COUNT(DISTINCT CASE WHEN DATEDIFF(TO_DATE(a.ds, 'yyyymmdd'), TO_DATE(c.cohort_ds, 'yyyymmdd'), 'dd') = 7
                        THEN a.user_id END) AS d7_retained,
    COUNT(DISTINCT CASE WHEN DATEDIFF(TO_DATE(a.ds, 'yyyymmdd'), TO_DATE(c.cohort_ds, 'yyyymmdd'), 'dd') = 30
                        THEN a.user_id END) AS d30_retained
FROM cohort c
LEFT JOIN active a ON c.user_id = a.user_id
GROUP BY c.cohort_ds;
```

**Key points**:
- Use a governed first-activity table when available. A bounded-history derivation is acceptable only when its boundary is explicit and its left-censoring risk is disclosed.
- `DATEDIFF(active_day, cohort_day, 'dd')` gives the N-day offset; bucket by N with `COUNT(DISTINCT)`.
- Confirm whether retention means activity on exactly day N or within days 1 through N. The example uses exact-day retention.
- Confirm the partition format before choosing `TO_DATE(..., 'yyyymmdd')` or `TO_DATE(..., 'yyyy-mm-dd')`.
- Add ordered output only when requested. Pair `ORDER BY c.cohort_ds` with a user-requested bound, or follow the verified unbounded-order guidance in [maxcompute-select-guide.md](maxcompute-select-guide.md).

---

## 14. Range lookup / range join

NL example: "Find which time period each event belongs to".

```sql
-- The table name in the hint must be the actual alias p (the broadcast side), NOT the original table name time_periods
SELECT /*+ RANGEJOIN(p, <confirmed-range-width>) */
    e.event_id, e.event_time, p.period_name
FROM events e
JOIN time_periods p
    ON e.event_time >= p.start_time AND e.event_time < p.end_time
WHERE e.ds = '<partition-value>';
```

**Note**: In `RANGEJOIN(table, N)`, N is the confirmed estimated match range in the same unit as the join column. Do not infer the unit or range width from the column name.

---

## 15. Multi-dimensional aggregation (GROUPING SETS / CUBE / ROLLUP)

NL example: "Statistics by region and product, plus a grand total".

```sql
SELECT
    region,
    product,
    SUM(amount) AS total,
    GROUPING(region) AS g_region,
    GROUPING(product) AS g_product
FROM sales
WHERE ds = '<partition-value>'
GROUP BY GROUPING SETS ((region, product), (region), ())
ORDER BY region, product
LIMIT <row-count>;
```

- `GROUPING(col) = 0` means the column is in the current group (participating in grouping); `= 1` means it is being aggregated (NULL placeholder).
- `GROUPING_ID(a, b, ...)` packs multiple `GROUPING()` results into a single bitmap integer.
- `CUBE(a, b)` = all combinations `(a,b), (a), (b), ()`.
- `ROLLUP(a, b)` = hierarchical combinations `(a,b), (a), ()`.

---

## 16. Pagination

NL example: "Page 3, 10 per page".

MaxCompute supports `LIMIT ... OFFSET ...`; you can also use `ROW_NUMBER` for more flexible paging.

```sql
WITH ranked AS (
    SELECT order_id, user_id, amount, create_time,
           ROW_NUMBER() OVER (ORDER BY order_id) AS rn
    FROM orders
    WHERE ds = '<partition-value>'
)
SELECT order_id, user_id, amount, create_time
FROM ranked
WHERE rn BETWEEN 21 AND 30
ORDER BY rn
LIMIT 10;
```

**Core idea**: `ROW_NUMBER` indexes the rows; `BETWEEN` selects the page range. For page P with N rows per page: `WHERE rn BETWEEN (P-1)*N+1 AND P*N`.

---

## 17. Multi-level CTE for complex queries

NL example: "Order statistics for users above a confirmed value threshold".

When a query has many nested levels or the same logic is referenced multiple times, prefer `WITH ... AS` for readability.

```sql
WITH high_value_users AS (
    SELECT user_id, SUM(amount) AS total
    FROM orders
    WHERE ds >= '<start-date>' AND ds <= '<end-date>'
    GROUP BY user_id
    HAVING SUM(amount) > <confirmed-value-threshold>
),
user_orders AS (
    SELECT o.user_id, o.order_id, o.amount, o.ds
    FROM orders o
    JOIN high_value_users h ON o.user_id = h.user_id
    WHERE o.ds >= '<start-date>' AND o.ds <= '<end-date>'
)
SELECT user_id, COUNT(*) AS order_count, SUM(amount) AS total_amount
FROM user_orders
GROUP BY user_id
ORDER BY total_amount DESC
LIMIT <row-count>;
```

**Recursive CTE**: `WITH RECURSIVE cte AS (base_query UNION ALL recursive_query) SELECT * FROM cte;`

Recursive CTE runtime constraints:
- Query acceleration does not support recursive CTEs. Do not disable MCQA preemptively. Fall back to batch execution only after the returned error identifies this incompatibility and the user accepts the execution-mode change.
- The default maximum is 10 iterations and the documented maximum is 100. Change `odps.sql.rcte.max.iterate.num` only when the requested recursion depth requires it.
- The recursive branch must have a **converging termination condition** (e.g. `WHERE level < 10`); otherwise even hitting the iteration cap raises an error.

Official reference: [Common table expressions](https://www.alibabacloud.com/help/en/maxcompute/user-guide/common-table-expressions-1).
