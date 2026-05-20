# Window and Analytic Functions

## Table of Contents

1. [Window Function Overview](#window-function-overview)
2. [Ranking Functions](#ranking-functions)
3. [Offset Functions](#offset-functions)
4. [Aggregate Window Functions](#aggregate-window-functions)
5. [Window Frame Definition](#window-frame-definition)
6. [Typical Business Scenarios](#typical-business-scenarios)
7. [Performance Caveats](#performance-caveats)

---

## Window Function Overview

Window functions compute over a result set without changing the row count. Basic syntax:

```sql
function_name(args) OVER (
    [PARTITION BY partition_columns]
    [ORDER BY sort_columns [ASC|DESC]]
    [window_frame]
)
```

| Component | Purpose | Required |
|------|------|---------|
| `PARTITION BY` | Group rows; each group computed independently | Optional (omitted: the entire result set is one partition) |
| `ORDER BY` | Order within the group | Required for ranking/offset functions; optional for aggregates |
| `window_frame` | Defines the rows used in computation | Optional (has a default) |

---

## Ranking Functions

### ROW_NUMBER()

Generates a sequential, unique number for each row; does not handle ties.

```sql
-- Salary ranking within each department (ties get different numbers)
SELECT
    department,
    employee_name,
    salary,
    ROW_NUMBER() OVER(PARTITION BY department ORDER BY salary DESC) AS rn
FROM employees;

-- Example result:
-- Sales | Zhang San | 15000 | 1
-- Sales | Li Si     | 15000 | 2  <- Same salary, different number
-- Sales | Wang Wu   | 12000 | 3
```

### RANK()

Ties receive the same rank; the next rank skips ahead.

```sql
SELECT
    department,
    employee_name,
    salary,
    RANK() OVER(PARTITION BY department ORDER BY salary DESC) AS rnk
FROM employees;

-- Example result:
-- Sales | Zhang San | 15000 | 1
-- Sales | Li Si     | 15000 | 1  <- Tied at 1
-- Sales | Wang Wu   | 12000 | 3  <- Skips 2
```

### DENSE_RANK()

Ties receive the same rank; the next rank does not skip.

```sql
SELECT
    department,
    employee_name,
    salary,
    DENSE_RANK() OVER(PARTITION BY department ORDER BY salary DESC) AS dense_rnk
FROM employees;

-- Example result:
-- Sales | Zhang San | 15000 | 1
-- Sales | Li Si     | 15000 | 1  <- Tied at 1
-- Sales | Wang Wu   | 12000 | 2  <- Continues at 2 (no skip)
```

### Ranking Function Comparison

| Function | Tie handling | Continuity | Typical scenario |
|------|---------|--------|---------|
| `ROW_NUMBER()` | No tie handling | Continuous | Pagination, deduplication (take first per group) |
| `RANK()` | Ties share rank | Non-continuous | Competition rankings |
| `DENSE_RANK()` | Ties share rank | Continuous | Top-N categories (top 3 may include more than 3 people) |

---

## Offset Functions

### LAG() / LEAD()

Access data N rows before or after the current row.

```sql
-- LAG: access the previous row (period-over-period calculation)
SELECT
    dt,
    revenue,
    LAG(revenue, 1) OVER(ORDER BY dt) AS prev_day_revenue,       -- previous day
    LAG(revenue, 7) OVER(ORDER BY dt) AS prev_week_revenue,      -- same day last week
    LAG(revenue, 1, 0) OVER(ORDER BY dt) AS prev_day_or_zero     -- third argument: default value
FROM daily_stats;

-- LEAD: access the next row
SELECT
    dt,
    revenue,
    LEAD(revenue, 1) OVER(ORDER BY dt) AS next_day_revenue
FROM daily_stats;
```

### FIRST_VALUE() / LAST_VALUE()

Get the value of the first or last row in the window.

```sql
-- Each user's first and most recent order amount
SELECT
    user_id,
    order_date,
    amount,
    FIRST_VALUE(amount) OVER(
        PARTITION BY user_id ORDER BY order_date
    ) AS first_order_amount,
    LAST_VALUE(amount) OVER(
        PARTITION BY user_id ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS last_order_amount
FROM orders;
```

> **Note:** The default frame for `LAST_VALUE` is `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`. You must explicitly specify `UNBOUNDED FOLLOWING` to retrieve the true last row.

### NTH_VALUE()

Get the value of the Nth row in the window.

```sql
-- Find the second-highest-paid employee in each department
SELECT
    department,
    employee_name,
    salary,
    NTH_VALUE(salary, 2) OVER(
        PARTITION BY department ORDER BY salary DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS second_highest
FROM employees;
```

---

## Aggregate Window Functions

Standard aggregate functions (SUM, AVG, COUNT, MIN, MAX) can all be used as window functions.

```sql
SELECT
    dt,
    revenue,
    -- Cumulative sum
    SUM(revenue) OVER(ORDER BY dt) AS cumulative_revenue,
    -- Rolling average (last 7 days)
    AVG(revenue) OVER(
        ORDER BY dt ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_avg,
    -- Rolling maximum
    MAX(revenue) OVER(
        ORDER BY dt ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_max,
    -- Group total (for computing share)
    SUM(revenue) OVER(PARTITION BY region) AS region_total,
    -- Share
    ROUND(revenue * 100.0 / SUM(revenue) OVER(PARTITION BY region), 2) AS pct_of_region
FROM daily_stats;
```

---

## Window Frame Definition

### Syntax

```sql
{ROWS | RANGE} BETWEEN frame_start AND frame_end

-- frame_start / frame_end can be:
--   UNBOUNDED PRECEDING   -- the first row of the partition
--   N PRECEDING           -- N rows before the current row
--   CURRENT ROW           -- the current row
--   N FOLLOWING           -- N rows after the current row
--   UNBOUNDED FOLLOWING   -- the last row of the partition
```

### ROWS vs RANGE

| Type | Meaning | Use case |
|------|------|---------|
| `ROWS` | Physical row count | Rolling window (last 7 rows) |
| `RANGE` | Value range | Value-range window (last 7 days, including all rows for the same day) |

```sql
-- ROWS: exact physical row count
SUM(revenue) OVER(ORDER BY dt ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
-- Meaning: previous 6 rows + current row = 7 rows

-- RANGE: by value range (rows with the same dt form a group)
SUM(revenue) OVER(ORDER BY dt RANGE BETWEEN INTERVAL 6 DAY PRECEDING AND CURRENT ROW)
-- Meaning: all rows where dt is in [current dt - 6 days, current dt]
```

### Default Frame

| ORDER BY present? | Default frame |
|--------------|-----------|
| No ORDER BY | `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING` (entire partition) |
| With ORDER BY | `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` (from partition start to current row) |

---

## Typical Business Scenarios

### Scenario 1: Top-N Query

```sql
-- Top 3 best-selling products in each category
WITH ranked AS (
    SELECT
        category,
        product_name,
        sales,
        ROW_NUMBER() OVER(PARTITION BY category ORDER BY sales DESC) AS rn
    FROM product_sales
)
SELECT category, product_name, sales
FROM ranked
WHERE rn <= 3;
```

### Scenario 2: Period-Over-Period Calculation

```sql
-- Day-over-day and week-over-week
SELECT
    dt,
    revenue,
    -- Day-over-day
    ROUND(
        (revenue - LAG(revenue, 1) OVER(ORDER BY dt))
        * 100.0 / LAG(revenue, 1) OVER(ORDER BY dt),
        2
    ) AS day_over_day_pct,
    -- Week-over-week
    ROUND(
        (revenue - LAG(revenue, 7) OVER(ORDER BY dt))
        * 100.0 / LAG(revenue, 7) OVER(ORDER BY dt),
        2
    ) AS week_over_week_pct
FROM daily_revenue
WHERE dt BETWEEN '2024-01-01' AND '2024-01-31';
```

### Scenario 3: Cumulative Computation

```sql
-- Month-to-date cumulative sales and completion progress
SELECT
    dt,
    revenue,
    SUM(revenue) OVER(
        PARTITION BY DATE_TRUNC('month', dt)
        ORDER BY dt
    ) AS mtd_revenue,  -- Month-to-Date
    ROUND(
        SUM(revenue) OVER(PARTITION BY DATE_TRUNC('month', dt) ORDER BY dt)
        * 100.0 / monthly_target,
        2
    ) AS completion_pct
FROM daily_revenue
JOIN monthly_targets ON DATE_TRUNC('month', daily_revenue.dt) = monthly_targets.month;
```

### Scenario 4: Per-Group Deduplication (Latest Row per Group)

```sql
-- Most recent order per user
WITH latest AS (
    SELECT *,
        ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY order_time DESC) AS rn
    FROM orders
)
SELECT * FROM latest WHERE rn = 1;
```

### Scenario 5: Consecutive Event Detection

```sql
-- Detect users who logged in for 3 consecutive days
WITH daily_logins AS (
    SELECT DISTINCT user_id, DATE(login_time) AS login_date
    FROM login_logs
),
numbered AS (
    SELECT
        user_id,
        login_date,
        login_date - INTERVAL ROW_NUMBER() OVER(
            PARTITION BY user_id ORDER BY login_date
        ) DAY AS group_id
    FROM daily_logins
)
SELECT user_id, MIN(login_date) AS start_date, COUNT(*) AS consecutive_days
FROM numbered
GROUP BY user_id, group_id
HAVING COUNT(*) >= 3;
```

### Scenario 6: Share Analysis

```sql
-- Share of each region's revenue relative to the total
SELECT
    region,
    revenue,
    ROUND(
        revenue * 100.0 / SUM(revenue) OVER(),  -- no PARTITION BY = global total
        2
    ) AS pct_of_total,
    ROUND(
        SUM(revenue) OVER(ORDER BY revenue DESC)
        * 100.0 / SUM(revenue) OVER(),
        2
    ) AS cumulative_pct  -- cumulative share (Pareto analysis)
FROM regional_stats
ORDER BY revenue DESC;
```

---

## Performance Caveats

### Choosing PARTITION BY

| Scenario | Suggestion |
|------|------|
| PARTITION BY column with very low cardinality (e.g., gender) | Large per-partition data; high memory pressure |
| PARTITION BY column with extremely high cardinality (e.g., billion-level user_id) | Too many partitions; high scheduling overhead |
| Recommended cardinality | Similar to GROUP BY; thousands to millions is optimal |

### Avoid Redundant Computation

```sql
-- Anti-pattern: same window definition repeated multiple times
SELECT
    dt,
    SUM(x) OVER(PARTITION BY region ORDER BY dt),
    AVG(x) OVER(PARTITION BY region ORDER BY dt),
    COUNT(x) OVER(PARTITION BY region ORDER BY dt)
FROM t;

-- Correct: StarRocks automatically merges computations on identical window definitions
-- The above pattern incurs no extra cost in StarRocks (the optimizer merges them)
-- However, using the WINDOW clause improves readability:
SELECT
    dt,
    SUM(x) OVER w,
    AVG(x) OVER w,
    COUNT(x) OVER w
FROM t
WINDOW w AS (PARTITION BY region ORDER BY dt);
```

### Window Function vs GROUP BY

```sql
-- If you don't need to keep the original rows, use GROUP BY (more efficient)
SELECT region, SUM(revenue) FROM sales GROUP BY region;

-- If you need to keep original rows + aggregate values, use a window function
SELECT region, dt, revenue,
       SUM(revenue) OVER(PARTITION BY region) AS region_total
FROM sales;
```
