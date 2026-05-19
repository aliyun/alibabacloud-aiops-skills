# MaxCompute SQL 常用模式模板

面向 text2sql 场景，提供 MaxCompute 常用 **DQL（SELECT 查询）** 模板。生成 SQL 时优先匹配这些模式，而非从零构造。

**模板使用约定**：

- `${bizdate}` 是 MaxCompute 调度系统的日期变量（当前业务日期）。生成 SQL 时按用户意图替换为具体日期字符串（如 `'2024-01-15'`）或 `TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyy-mm-dd')`（昨天）。
- 模板中的列名（`order_id`、`user_id` 等）为占位符，请替换为目标表的真实列；尽量列出明确列名而非 `SELECT *`。当外层模板必须保留源表所有列（如 PIVOT 输出、纯翻页透传）时可保留 `*`。

---

## 1. 每组取Top N（每组前N）

自然语言示例："每个部门薪资最高的3个人"

```sql
SELECT employee_id, name, department, salary
FROM (
    SELECT employee_id, name, department, salary,
           ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rn
    FROM employees
    WHERE ds = '${bizdate}'
) tmp
WHERE rn <= 3;
```

**注意**: 不要用 `GROUP BY + LIMIT`，MaxCompute的LIMIT是全局的。必须用窗口函数。子查询里只 SELECT 后续会用到的业务列 + `rn`，外层不要返回 `rn` 给最终结果。

---

## 2. 去重保留最新一条

自然语言示例："每个用户保留最近一条订单"

```sql
SELECT order_id, user_id, amount, create_time
FROM (
    SELECT order_id, user_id, amount, create_time,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY create_time DESC) AS rn
    FROM orders
    WHERE ds = '${bizdate}'
) tmp
WHERE rn = 1;
```

**变体 — 按多列去重**:
```sql
SELECT user_id, product_id, qty, update_time
FROM (
    SELECT user_id, product_id, qty, update_time,
           ROW_NUMBER() OVER (PARTITION BY user_id, product_id ORDER BY update_time DESC) AS rn
    FROM user_products
    WHERE ds = '${bizdate}'
) tmp
WHERE rn = 1;
```

---

## 3. 累计求和 / 运行总计

自然语言示例："按日期累计销售额"

```sql
SELECT
    ds,
    daily_amount,
    SUM(daily_amount) OVER (ORDER BY ds ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_amount
FROM daily_sales
WHERE ds >= '2024-01-01' AND ds <= '2024-01-31';
```

**注意**: 必须显式指定 `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`，不要依赖默认frame。

---

## 4. 同比 / 环比

自然语言示例："每月销售额及环比增长率"

```sql
SELECT
    month_id,
    amount,
    LAG(amount, 1) OVER (ORDER BY month_id) AS prev_month_amount,
    ROUND((amount - LAG(amount, 1) OVER (ORDER BY month_id))
          / LAG(amount, 1) OVER (ORDER BY month_id) * 100, 2) AS mom_growth_pct
FROM monthly_sales
ORDER BY month_id
LIMIT 10000;
```

**同比（去年同期）**:
```sql
SELECT
    month_id,
    amount,
    LAG(amount, 12) OVER (ORDER BY month_id) AS same_month_last_year,
    ROUND((amount - LAG(amount, 12) OVER (ORDER BY month_id))
          / LAG(amount, 12) OVER (ORDER BY month_id) * 100, 2) AS yoy_growth_pct
FROM monthly_sales
ORDER BY month_id
LIMIT 10000;
```

---

## 5. 连续N天活跃

自然语言示例："连续登录3天以上的用户"

```sql
SELECT user_id, MIN(ds) AS start_date, MAX(ds) AS end_date, COUNT(*) AS consecutive_days
FROM (
    SELECT user_id, ds,
           DATEADD(TO_DATE(ds, 'yyyy-mm-dd'),
                   -ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY ds), 'dd') AS grp
    FROM (
        SELECT DISTINCT user_id, ds
        FROM user_login
        WHERE ds >= '2024-01-01' AND ds <= '2024-01-31'
    ) t1
) t2
GROUP BY user_id, grp
HAVING COUNT(*) >= 3;
```

**核心思路**: 日期减去行号，连续日期会得到相同的grp值。

> ⚠️ **前提**：模板假设 `ds` 是 ISO 格式（`'2024-01-15'`）。若实际表 `ds` 是紧凑格式（`'20240115'`），把 `TO_DATE(ds, 'yyyy-mm-dd')` 改为 `TO_DATE(ds, 'yyyymmdd')`，并相应调整 WHERE 范围字面量为 `'20240101'/'20240131'`。

---

## 6. 行转列 (PIVOT)

自然语言示例："每个用户各类型订单的总金额"

> ⚠️ 部分 project 不支持 PIVOT —— **如执行报 "unsupported syntax" 错误，回退到方式二 CASE WHEN**。UNPIVOT 已正式可用。

**方式一: PIVOT**
```sql
SELECT *
FROM (
    SELECT user_id, order_type, amount
    FROM orders
    WHERE ds = '${bizdate}'
) src
PIVOT (
    SUM(amount)
    FOR order_type IN ('food' AS food, 'drink' AS drink, 'other' AS other_type)
) pvt;
-- PIVOT 限制：
--   * PIVOT (...) 顶层必须是聚合函数，不能再嵌一层普通函数（写 ROUND(SUM(amount),2) 报错）
--   * 聚合函数内部允许标量表达式（如 SUM(amount * rate)）
--   * 不能混入窗口函数 / 表函数；IN 列表的值必须是常量字面量
```

**方式二: CASE WHEN (推荐，类型值不确定或 PIVOT 不可用时)**
```sql
SELECT
    user_id,
    SUM(CASE WHEN order_type = 'food' THEN amount ELSE 0 END) AS food_amount,
    SUM(CASE WHEN order_type = 'drink' THEN amount ELSE 0 END) AS drink_amount
FROM orders
WHERE ds = '${bizdate}'
GROUP BY user_id;
```

---

## 7. 列转行 (UNPIVOT)

自然语言示例："将月度指标列转为行"

**方式一: UNPIVOT (推荐)**
```sql
SELECT user_id, metric_name, metric_value
FROM monthly_metrics
UNPIVOT (
    metric_value FOR metric_name IN (revenue, cost, profit)
) unpvt
WHERE ds = '${bizdate}';
```

**方式二: UNION ALL (备选)**
```sql
SELECT user_id, 'revenue' AS metric_name, revenue AS metric_value FROM monthly_metrics WHERE ds = '${bizdate}'
UNION ALL
SELECT user_id, 'cost', cost FROM monthly_metrics WHERE ds = '${bizdate}'
UNION ALL
SELECT user_id, 'profit', profit FROM monthly_metrics WHERE ds = '${bizdate}';
```

---

## 8. 数组展开 (LATERAL VIEW)

自然语言示例："展开用户标签数组"

```sql
SELECT t.user_id, tag.tag_value
FROM user_tags t
LATERAL VIEW EXPLODE(t.tags) tag AS tag_value
WHERE t.ds = '${bizdate}';
```

**带索引的展开**:
```sql
SELECT t.user_id, tag.pos AS tag_index, tag.val AS tag_value
FROM user_tags t
LATERAL VIEW POSEXPLODE(t.tags) tag AS pos, val
WHERE t.ds = '${bizdate}';
```

**OUTER (保留无标签用户)**:
```sql
SELECT t.user_id, tag.tag_value
FROM user_tags t
LATERAL VIEW OUTER EXPLODE(t.tags) tag AS tag_value
WHERE t.ds = '${bizdate}';
```

---

## 9. JSON字段提取（JSON 提取）

自然语言示例："从JSON日志中提取用户行为"

```sql
-- 提取单层字段
SELECT
    GET_JSON_OBJECT(log_content, '$.user_id') AS user_id,
    GET_JSON_OBJECT(log_content, '$.action') AS action,
    GET_JSON_OBJECT(log_content, '$.timestamp') AS event_time
FROM raw_logs
WHERE ds = '${bizdate}';

-- 提取嵌套字段
SELECT
    GET_JSON_OBJECT(log_content, '$.user.name') AS user_name,
    GET_JSON_OBJECT(log_content, '$.user.age') AS user_age
FROM raw_logs
WHERE ds = '${bizdate}';

-- 提取JSON数组元素
SELECT
    GET_JSON_OBJECT(log_content, '$.items[0].name') AS first_item_name
FROM raw_logs
WHERE ds = '${bizdate}';
```

---

## 10. MAP操作

自然语言示例："从属性MAP中提取指定键"

```sql
-- 提取MAP值
SELECT user_id, properties['city'] AS city
FROM user_profiles
WHERE ds = '${bizdate}';

-- MAP展开为行
SELECT t.user_id, kv.key AS prop_key, kv.value AS prop_value
FROM user_profiles t
LATERAL VIEW EXPLODE(t.properties) kv AS key, value
WHERE t.ds = '${bizdate}';

-- 字符串解析为MAP再提取
SELECT
    STR_TO_MAP(params, '&', '=')['source'] AS traffic_source
FROM page_views
WHERE ds = '${bizdate}';
```

---

## 11. 分区动态获取（最新分区）

自然语言示例："查询最新分区的数据"

```sql
-- 方式一: MAX_PT (推荐)
SELECT user_id, name, status
FROM dim_users
WHERE ds = MAX_PT('project_name.dim_users');

-- 方式二: 子查询
SELECT user_id, name, status
FROM dim_users
WHERE ds = (SELECT MAX(ds) FROM dim_users WHERE ds <= '${bizdate}');
```

---

## 12. EXISTS / NOT EXISTS 改写

自然语言示例："查找没有下过单的用户"

**方式一: LEFT ANTI JOIN (推荐)**
```sql
SELECT u.*
FROM users u
LEFT ANTI JOIN orders o ON u.user_id = o.user_id AND o.ds = '${bizdate}'
WHERE u.ds = '${bizdate}';
```

**方式二: NOT EXISTS**
```sql
SELECT u.*
FROM users u
WHERE u.ds = '${bizdate}'
  AND NOT EXISTS (
    SELECT 1 FROM orders o WHERE o.user_id = u.user_id AND o.ds = '${bizdate}'
  );
```

**"有下单记录的用户" — LEFT SEMI JOIN**
```sql
SELECT u.*
FROM users u
LEFT SEMI JOIN orders o ON u.user_id = o.user_id AND o.ds = '${bizdate}'
WHERE u.ds = '${bizdate}';
```

---

## 13. N日留存 / Cohort Retention

自然语言示例："各日新用户的次日 / 7日 / 30日留存"。

```sql
-- 关键：cohort_ds 必须用"全量历史 MIN(ds)"求出，否则把老用户首次活跃日截断到分析窗口起点，
-- 会把老用户误算成"新用户"。先求 cohort，再过滤 cohort_ds 落入分析窗口。
WITH cohort_full AS (
    -- 全量历史下每个用户的首次活跃日（不限分析窗口）
    SELECT user_id, MIN(ds) AS cohort_ds
    FROM events
    GROUP BY user_id
),
cohort AS (
    -- 仅保留首次活跃日落在分析窗口内的（即真正的"新用户"）
    SELECT user_id, cohort_ds
    FROM cohort_full
    WHERE cohort_ds >= '20240101' AND cohort_ds <= '20240131'
),
active AS (
    -- 分析窗口 + 30 日观察期内的活跃记录（去重到天粒度）
    SELECT DISTINCT user_id, ds
    FROM events
    WHERE ds >= '20240101' AND ds <= '20240301'
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
GROUP BY c.cohort_ds
ORDER BY c.cohort_ds;
```

**关键点**：
- `cohort_ds` 求**全量历史**最小值，再过滤窗口落点 —— 否则老用户首次活跃日被截到窗口起点，会被误算成"新用户"
- `DATEDIFF(active_day, cohort_day, 'dd')` 算 N 日偏移，按 N 分桶 `COUNT(DISTINCT)`
- `ds` 是 `'yyyymmdd'` 格式则用 `TO_DATE(..., 'yyyymmdd')`；ISO `'YYYY-MM-DD'` 用 `'yyyy-mm-dd'`

---

## 14. 区间查找 / Range Join

自然语言示例："查找每个事件所属的时间段"

```sql
-- Hint 里的表名必须用实际别名 p（被广播侧），不是原表名 time_periods
SELECT /*+ RANGEJOIN(p, 86400) */
    e.event_id, e.event_time, p.period_name
FROM events e
JOIN time_periods p
    ON e.event_time >= p.start_time AND e.event_time < p.end_time
WHERE e.ds = '${bizdate}';
```

**注意**: Range Join 需要加 Hint 优化性能。`RANGEJOIN(table, N)` 中的 N 是预估匹配范围，**单位与连接列同单位**——若列是 BIGINT 秒时间戳则 N 单位为秒（86400=1天），若列是毫秒时间戳则 N 也是毫秒。

---

## 15. 多维聚合 (GROUPING SETS / CUBE / ROLLUP)

自然语言示例："按区域、产品分别统计，同时要总计"

```sql
SELECT
    region,
    product,
    SUM(amount) AS total,
    GROUPING(region) AS g_region,
    GROUPING(product) AS g_product
FROM sales
WHERE ds = '${bizdate}'
GROUP BY GROUPING SETS ((region, product), (region), ())
ORDER BY region, product
LIMIT 10000;
```

- `GROUPING(col) = 0` 表示该列在当前分组中（参与分组）；`= 1` 表示该列被聚合（NULL 占位）
- `GROUPING_ID(a, b, ...)` 把多个 GROUPING() 合并为一个 bitmap 整数
- `CUBE(a, b)` = 所有组合 `(a,b), (a), (b), ()`
- `ROLLUP(a, b)` = 层次组合 `(a,b), (a), ()`

---

## 16. 翻页查询

自然语言示例："查第3页，每页10条"

MaxCompute支持 `LIMIT ... OFFSET ...`，也可用 ROW_NUMBER 实现更灵活的分页。

```sql
WITH ranked AS (
    SELECT order_id, user_id, amount, create_time,
           ROW_NUMBER() OVER (ORDER BY order_id) AS rn
    FROM orders
    WHERE ds = '${bizdate}'
)
SELECT order_id, user_id, amount, create_time
FROM ranked
WHERE rn BETWEEN 21 AND 30
ORDER BY rn
LIMIT 10;
```

**核心思路**: ROW_NUMBER 编号后用 BETWEEN 取指定范围。页码 P、每页 N 条时：`WHERE rn BETWEEN (P-1)*N+1 AND P*N`。

---

## 17. CTE 多层复杂查询

自然语言示例："高价值用户的订单统计"

当查询包含多层嵌套、同一逻辑被引用多次时，优先用 WITH...AS 提高可读性。

```sql
WITH high_value_users AS (
    SELECT user_id, SUM(amount) AS total
    FROM orders
    WHERE ds >= '2024-01-01' AND ds <= '2024-01-31'
    GROUP BY user_id
    HAVING SUM(amount) > 10000
),
user_orders AS (
    SELECT o.user_id, o.order_id, o.amount, o.ds
    FROM orders o
    JOIN high_value_users h ON o.user_id = h.user_id
    WHERE o.ds >= '2024-01-01' AND o.ds <= '2024-01-31'
)
SELECT user_id, COUNT(*) AS order_count, SUM(amount) AS total_amount
FROM user_orders
GROUP BY user_id
ORDER BY total_amount DESC
LIMIT 100;
```

**递归CTE**: `WITH RECURSIVE cte AS (基础查询 UNION ALL 递归查询) SELECT * FROM cte;`

递归 CTE 运行约束（不写终止条件直接生成不可运行 SQL）：
- 仅 **offline 模式**默认可用；**MCQA / MCQA2 拒绝**（编译期报 `rcte.session.mode`）。在 MCQA 下用前先 `SET odps.mcqa.disable=true;`
- 默认最大迭代 10，硬上限 100，更大值被截断；调大用 `SET odps.sql.rcte.max.iterate.num=100;`
- 递归分支必须有**收敛终止条件**（如 `WHERE level < 10`），否则即使迭代上限也会撞上限直接报错
