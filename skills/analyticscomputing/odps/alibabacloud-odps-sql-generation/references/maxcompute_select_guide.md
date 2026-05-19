# MaxCompute SELECT 方言规则

生成 MaxCompute SELECT 查询前读取此文件。覆盖 MaxCompute 与标准 SQL 的差异：不工作的写法、函数名映射、分区规则、类型陷阱、扩展语法、SET 参数。每条规则附触发的实际报错信息或 MaxCompute 的设计原因，遇到边界情况时按"为什么"判断而非死搬。

> 组合方式：自然语言转 SELECT 时，用 `text2sql_principles.md` 做逻辑规划（意图、结果粒度、表列映射、输出契约），最终 SQL 一次性写成 MaxCompute 可执行语法，不先生成 ANSI SQL 中间稿。

> 示例说明：本文档为了突出方言语法，部分示例使用 `SELECT *`。text2sql 最终输出仍应遵守 `text2sql_principles.md`：除非用户明确要求透传所有列，或模板语义必须保留全列，否则列出明确字段。

---

## 一、不工作的写法（会直接报错）

以下写法在 MaxCompute 上会报错。每条都附错误码和原因。

### 1. ORDER BY 默认要求带 LIMIT

`odps.sql.validate.orderby.limit=true` 是默认值；当 SQL 包含 `ORDER BY` 时必须配合 `LIMIT`，否则提交校验会报错。**不要在没有 ORDER BY / 没有 Top-N / 没有"最大/最小/排名"语义的查询上无故添加 LIMIT** — 多余的 LIMIT 会改变结果集大小，破坏题意。可通过下述方式关闭：

- 项目级：`SETPROJECT odps.sql.validate.orderby.limit=false;`
- 会话级：`SET odps.sql.validate.orderby.limit=false;`

注：`ORDER BY` 不能与 `DISTRIBUTE BY` / `SORT BY` 同时出现。

```sql
-- DON'T（默认模式下报错）
SELECT * FROM orders WHERE dt = '2024-01-15' ORDER BY amount DESC;

-- DO
SELECT * FROM orders WHERE dt = '2024-01-15' ORDER BY amount DESC LIMIT 100;
```

### 2. 类型转换只能用 `CAST`，无 `::type` 简写

```sql
-- DON'T
SELECT col::BIGINT FROM t;

-- DO
SELECT CAST(col AS BIGINT) FROM t;
```

### 3. 取前 N 行用 `LIMIT`，无 `SELECT TOP N`

```sql
-- DON'T
SELECT TOP 10 * FROM t;

-- DO
SELECT * FROM t LIMIT 10;
```

### 4. 大小写不敏感匹配用 `LOWER + LIKE`，无 `ILIKE`

```sql
-- DON'T
SELECT * FROM t WHERE name ILIKE '%张%';

-- DO
SELECT * FROM t WHERE LOWER(name) LIKE '%张%';
```

### 5. 字符串拼接用 CONCAT 或 ||

`+` 是数值运算符，不能用于字符串拼接。

```sql
SELECT CONCAT('a', 'b');   -- 返回 'ab'
SELECT 'a' || 'b';         -- 返回 'ab'
```

### 6. NULL 判断只用 `IS NULL`

```sql
-- DON'T
SELECT * FROM t WHERE col = NULL;

-- DO
SELECT * FROM t WHERE col IS NULL;
```

### 7. WHERE 不能引用 SELECT 别名

```sql
-- DON'T
SELECT amount * 0.1 AS tax FROM orders WHERE tax > 10;

-- DO
SELECT amount * 0.1 AS tax FROM orders WHERE amount * 0.1 > 10;
-- 或用子查询
SELECT * FROM (SELECT amount * 0.1 AS tax FROM orders) tmp WHERE tax > 10;
```

### 8. SUM(布尔表达式) 不工作

MaxCompute 没有隐式 bool→int 转换，`SUM(condition)` 报 `function sum cannot match any overloaded functions with (BOOLEAN)`。改用 `CASE WHEN` 或 `COUNT_IF`。

```sql
-- DON'T: SUM(bool) 不工作
SELECT SUM(status = 'A') FROM orders;
SELECT SUM(gender_id = 1) FROM superhero;

-- DO: 用 CASE WHEN 或 COUNT_IF
SELECT SUM(CASE WHEN status = 'A' THEN 1 ELSE 0 END) FROM orders;
SELECT SUM(CASE WHEN gender_id = 1 THEN 1 ELSE 0 END) FROM superhero;
```

---

## 二、函数名称规则

以下列出MaxCompute函数与其他数据库的差异。标注"均可"表示多种写法都支持。

### 日期时间

当需要**当前时间**时，写 `GETDATE()`、`NOW()` 或 `CURRENT_TIMESTAMP()` 均可：
```sql
SELECT GETDATE();            -- 返回 DATETIME
SELECT NOW();                -- 返回 DATETIME
SELECT CURRENT_TIMESTAMP();  -- 返回 TIMESTAMP（需加括号）
```

当需要**日期格式化**时，**推荐 `TO_CHAR(d, fmt)`**（跨类型默认可用）。`DATE_FORMAT` 存在但需要 SET 前置条件：

| 输入类型 | DATE_FORMAT 前置条件 | TO_CHAR |
|---|---|---|
| TIMESTAMP | `SET odps.sql.type.system.odps2=true;` | ✓ 默认可用 |
| STRING / DATE / DATETIME | `SET odps.sql.hive.compatible=true;` | ✓ 默认可用 |

```sql
-- 推荐（默认可用）
SELECT TO_CHAR(create_time, 'yyyy-mm-dd');

-- DATE_FORMAT 需先 SET
SET odps.sql.hive.compatible=true;
SELECT DATE_FORMAT(create_time, 'yyyy-MM-dd');
```

**注意格式串风格不同**：
- `TO_CHAR` 用 Oracle 风格小写 `yyyy-mm-dd hh:mi:ss`（`mi`=分）
- `DATE_FORMAT` 用 Java SimpleDateFormat 风格 `yyyy-MM-dd HH:mm:ss`（`HH`=24h，`mm`=分；非 Hive 模式 `mm`=月）

当需要**字符串转日期**时，写 `TO_DATE(s, fmt)`：
```sql
-- DON'T
SELECT STR_TO_DATE('2024-01-15', '%Y-%m-%d');

-- DO
SELECT TO_DATE('2024-01-15', 'yyyy-mm-dd');
```

**日期加减**用 `DATEADD(date, delta, unit)`；MaxCompute 没有 `DATE_ADD ... INTERVAL`：
```sql
-- DON'T
SELECT DATE_ADD(create_time, INTERVAL 7 DAY);

-- DO
SELECT DATEADD(create_time, 7, 'dd');
```

当需要**日期差**时，写 `DATEDIFF(d1, d2, unit)`，第三个参数可选（默认天）：
```sql
SELECT DATEDIFF(end_date, start_date, 'dd');   -- 显式指定天
SELECT DATEDIFF(end_date, start_date);         -- 默认也是天
```

当需要**提取年月日时**时，写 `YEAR(d)` / `MONTH(d)` / `DAY(d)` / `HOUR(d)` 或 `DATEPART(d, unit)`：
```sql
SELECT YEAR(create_time), MONTH(create_time), DAY(create_time);
-- 或
SELECT DATEPART(create_time, 'yyyy'), DATEPART(create_time, 'mm');
```

当需要**日期截断**时，写 `DATETRUNC(d, unit)` 或 `DATE(d)` / `TO_DATE(d)`：
```sql
SELECT DATETRUNC(create_time, 'mm');  -- 截断到月（返回月初）
SELECT DATETRUNC(create_time, 'dd');  -- 截断到天
SELECT DATE(create_time);             -- 截断到天（简写）
SELECT TO_DATE(create_time);          -- 截断到天（简写）
```
注意：默认模式下 `TRUNC` 是数值截断函数（如 `TRUNC(125.815, 0)` → 125.0），不能用于日期。Hive兼容模式下 `TRUNC(d, unit)` 可用于日期。

> 易混淆函数：
> - **`DATETRUNC(d, unit)`** — DQL 用的日期截断函数（本节）
> - **`TRUNC_TIME(d, unit)`** — DDL `AUTO PARTITIONED BY` 专用，**仅在建表语句里用**
>
> 两个函数名差一个下划线，单位也不同（DATETRUNC 用短名 `'dd'`，TRUNC_TIME 用长名 `'day'`）。

其他日期函数：
- `UNIX_TIMESTAMP(d)` — 转Unix时间戳
- `FROM_UNIXTIME(ts)` — Unix时间戳转日期（仅1个参数，格式化需配合TO_CHAR）
- `LAST_DAY(d)` — 月末日期（返回STRING）
- `LASTDAY(d)` — 月末日期（返回DATETIME，经典函数）
- `WEEKDAY(d)` — 星期几（0=周一, 6=周日）
- `WEEKOFYEAR(d)` — ISO周数

### 字符串

当需要**分组拼接**时，写 `WM_CONCAT(sep, col)`（分隔符在前）：
```sql
SELECT WM_CONCAT(',', name) FROM t GROUP BY dept;
SELECT WM_CONCAT(',', name) WITHIN GROUP (ORDER BY name) FROM t GROUP BY dept;  -- 排序拼接
-- GROUP_CONCAT 不可用
-- STRING_AGG 在引擎中可执行（PostgreSQL 风格 STRING_AGG(col, sep)），但官方文档未列出，推荐用 WM_CONCAT
```

当需要**查找子串位置**时，`INSTR(str, sub)` 和 `LOCATE(sub, str)` 均可，注意参数顺序相反：
```sql
SELECT INSTR(name, 'abc');    -- 大串在前，子串在后
SELECT LOCATE('abc', name);   -- 子串在前，大串在后
```

当需要**正则提取**时，`REGEXP_EXTRACT` 和 `REGEXP_SUBSTR` 均可：
```sql
SELECT REGEXP_EXTRACT(text, '(\\d+)', 1);              -- 提取捕获组
SELECT REGEXP_SUBSTR(text, '\\d+');                     -- 返回匹配子串
SELECT REGEXP_SUBSTR(text, '\\d+', 1, 2);              -- 第2次匹配，从位置1开始
```

当需要**字符串分割**时，写 `SPLIT(str, sep)` 返回ARRAY，取指定段用 `SPLIT_PART(str, sep, index)`：
```sql
SELECT SPLIT('a,b,c', ',');            -- 返回 ARRAY ['a','b','c']
SELECT SPLIT_PART('a,b,c', ',', 2);   -- 返回 'b'
```

### 聚合与条件

**NULL 替换**用 `NVL(expr, default)` 或 `COALESCE`；MaxCompute 没注册 `IFNULL`：
```sql
-- DON'T
SELECT IFNULL(amount, 0) FROM orders;

-- DO
SELECT NVL(amount, 0) FROM orders;
```

当需要**条件计数**时，除了 `SUM(CASE WHEN)` 外，也可用 `COUNT_IF(condition)`：
```sql
SELECT COUNT_IF(status = 'active') FROM users;  -- 等价于 SUM(CASE WHEN ... THEN 1 ELSE 0 END)
```

当需要**按条件取极值对应的值**时，用 `MAX_BY` / `MIN_BY`：
```sql
-- 找出每个部门薪资最高的员工名
SELECT dept, MAX_BY(name, salary) AS top_earner FROM emp GROUP BY dept;
-- 找出每个用户最近一笔订单金额
SELECT user_id, MAX_BY(amount, create_time) AS latest_amount FROM orders GROUP BY user_id;
```

当需要**收集为数组**时，写 `COLLECT_LIST` 或 `COLLECT_SET`（官方文档化）：
```sql
SELECT COLLECT_LIST(product_id) FROM orders GROUP BY user_id;   -- 含重复
SELECT COLLECT_SET(product_id) FROM orders GROUP BY user_id;    -- 去重
-- ARRAY_AGG 在引擎中可执行，但官方文档未列出，推荐用 COLLECT_LIST
```

### JSON

**默认推荐：`GET_JSON_OBJECT(json_str, path)`** —— 直接对 STRING 求值，**不需要任何 SET**，是 text2sql 最稳的默认方案。
```sql
-- DO
SELECT GET_JSON_OBJECT(log, '$.user_id');
SELECT GET_JSON_OBJECT(log, '$.user.name');                -- 嵌套
SELECT GET_JSON_OBJECT(log, '$.items[0].id');              -- 数组元素

-- DON'T
SELECT log->>'user_id';                    -- PostgreSQL 风格不支持
SELECT JSON_EXTRACT(log_str, '$.k');       -- 第一参数必须是 JSON 类型而非 STRING（报 0130121）
```

**JSON 类型路径（`JSON_EXTRACT` / JSON 字面量 / `CAST(... AS JSON)`）**——需要先**显式启用 JSON 类型系统**：
```sql
SET odps.sql.type.json.enable=true;
SELECT JSON_EXTRACT(CAST(log_str AS JSON), '$.k') FROM t;  -- 先 CAST 成 JSON 再 _EXTRACT
SELECT JSON '{"a": 1}' AS j;                                -- JSON 字面量
```
不开启时直接 `JSON_EXTRACT(STRING, ...)` 报 `ODPS-0130121: invalid type STRING of argument 1 for function json_extract, expect JSON`。

当需要**批量提取JSON多个字段**时，用 `JSON_TUPLE` 配合 `LATERAL VIEW` 更高效：
```sql
SELECT t.id, j.user_id, j.action
FROM logs t
LATERAL VIEW JSON_TUPLE(t.log, 'user_id', 'action') j AS user_id, action;
```

### 类型转换

类型转换只用 `CAST(expr AS type)`，目标类型用 MaxCompute 类型名（不是 MySQL 风格的 CHAR/SIGNED 等）：
```sql
CAST(col AS STRING)         -- 转字符串（不是 CAST AS CHAR / CAST AS TEXT）
CAST(col AS BIGINT)         -- 转整数（不是 CAST AS SIGNED / CAST AS INTEGER）
CAST(col AS DOUBLE)         -- 转浮点
CAST(col AS DECIMAL(10,2))  -- 转精确数值
```

---

## 三、日期格式字符串

MaxCompute日期格式中，**`mm`是月份，`mi`是分钟**。这是最容易出错的地方。

```sql
-- 正确的格式字符串
TO_CHAR(d, 'yyyy-mm-dd')           -- 2024-01-15（mm=月）
TO_CHAR(d, 'yyyy-mm-dd hh:mi:ss')  -- 2024-01-15 14:30:00（mi=分）
TO_CHAR(d, 'yyyymmdd')             -- 20240115

-- DON'T: 把分钟写成mm
TO_CHAR(d, 'yyyy-mm-dd hh:mm:ss')  -- 错误！mm是月份，会输出 2024-01-15 14:01:00
```

格式字符对照: `yyyy`=年, `mm`=月, `dd`=日, `hh`=时, `mi`=分, `ss`=秒

### 三套时间单位（重要：函数间不通用）

MaxCompute 同时存在三套时间单位字符串，必须按函数选用，**混用会报错**：

| 函数 | 接受的单位 | 备注 |
|------|-----------|------|
| `DATEADD/DATEDIFF` | `yyyy/year`, `quarter/q`, `mm/month/mon`, `week/w`, `dd/day`, `hh/hour`, `mi`, `ss`, `ff3` (毫秒), `ff6` (微秒) | 短名/长名均可 |
| `DATEPART` | **稳定支持**：`yyyy/year`, `mm/month`, `dd/day`, `hh/hour`, `mi`, `ss`, `ff3` (毫秒)；不要用 `quarter/q`、`week/w`、`ff6` | 比 DATEADD 子集更窄 |
| `TO_CHAR/TO_DATE` 格式串 | `yyyy/mm/dd/hh/mi/ss` | **仅短名**（`mm`=月、`mi`=分） |
| `TRUNC_TIME` | `year/month/day/hour` | **仅长名**，`'dd'`/`'mm'` 会报错 |
| `DATETRUNC` | `yyyy/mm/dd/hh/mi/ss/ff3`，`quarter/week` 也可用 | 短名（与 DATEADD 一致），覆盖范围比 TRUNC_TIME 宽 |

```sql
-- DON'T: TRUNC_TIME 不接受短名
TRUNC_TIME(event_time, 'dd')   -- 报错：invalid datePart

-- DO
TRUNC_TIME(event_time, 'day')  -- 正确
DATETRUNC(event_time, 'dd')    -- 正确（DATETRUNC 用短名）
```

---

## 四、分区表规则

### 查询分区表时，WHERE中必须包含分区列条件

```sql
-- DON'T: 全表扫描，会被拒绝执行
SELECT * FROM orders;

-- DO
SELECT * FROM orders WHERE dt = '2024-01-15';
SELECT * FROM orders WHERE dt >= '2024-01-01' AND dt <= '2024-01-31';
```

### 分区过滤位置取决于 JOIN 类型

放 WHERE 还是 ON **不影响分区剪裁**（CBO 会下推），但**影响 JOIN 语义**：

- **INNER JOIN**：放 WHERE 或 ON 等价，推荐 WHERE，更直观。
- **LEFT/RIGHT OUTER JOIN**：**保留侧**过滤放 WHERE；**非保留侧**（NULL 补齐侧）过滤**必须放 ON**——放 WHERE 会过滤掉 JOIN 不上时补齐的 NULL 行，使 OUTER 退化成 INNER。
- **LEFT SEMI / LEFT ANTI JOIN**：右表（被检查存在性的表）过滤**必须放 ON**——SEMI/ANTI 不输出右表列，WHERE 引用右表列会报错。

```sql
-- INNER JOIN: 推荐 WHERE
SELECT a.order_id, b.name
FROM orders a JOIN users b ON a.user_id = b.user_id
WHERE a.dt = '2024-01-15' AND b.dt = '2024-01-15';

-- LEFT JOIN: 右表分区过滤必须放 ON
SELECT a.order_id, b.name
FROM orders a LEFT JOIN users b
  ON a.user_id = b.user_id AND b.dt = '2024-01-15'
WHERE a.dt = '2024-01-15';

-- LEFT ANTI JOIN: 右表分区过滤必须放 ON
SELECT u.user_id
FROM users u
LEFT ANTI JOIN orders o
  ON u.user_id = o.user_id AND o.ds = '${bizdate}'
WHERE u.ds = '${bizdate}';
```

### 全表扫描需显式设置

分区表没有分区过滤时，MaxCompute默认拒绝执行。如确需全表扫描：

```sql
SET odps.sql.allow.fullscan=true;
SELECT * FROM partitioned_table;
```

### 分区列通常是STRING类型，即使表示日期

分区值的具体格式由建表时定义，**format 不是 MaxCompute 强制的，必须看实际表 schema/sample**。两种常见格式都合法：

```sql
-- 紧凑格式（MaxCompute 调度系统 ${bizdate} 默认产出，最常见）
WHERE dt = '20240115'
WHERE dt >= '20240101' AND dt <= '20240131'

-- ISO 格式（部分项目约定）
WHERE dt = '2024-01-15'
```

字符串字典序比较对两种格式都成立。生成 SQL 前如不确定，先用 `SHOW PARTITIONS table_name` 或读 sample 数据确认。

> 本文档其他章节示例为简洁可读，多用 `'2024-01-15'` 写法；text2sql 实际生成时**以目标表的真实分区格式为准**。

### 获取最新分区数据时，用 MAX_PT

```sql
SELECT * FROM dim_users WHERE dt = MAX_PT('project_name.dim_users');
```

---

## 五、类型陷阱

### STRING 与数值比较显式 CAST

```sql
-- DON'T: 隐式转换可能精度丢失
SELECT * FROM t WHERE string_col > 2;

-- DO
SELECT * FROM t WHERE CAST(string_col AS BIGINT) > 2;
```

### DECIMAL(precision, scale) 需要 odps2 模式

`DECIMAL(p,s)` 带精度的 DECIMAL 类型默认 project 模式下报错（"precision and scale is not currently supported"），需要 `SET odps.sql.decimal.odps2=true;` 启用。

```sql
SET odps.sql.decimal.odps2=true;
SELECT CAST(1.1 AS DECIMAL(10,2));   -- 启用后可用
```

### DECIMAL 与 DOUBLE 不要混合运算

```sql
-- DON'T: 2.2是DOUBLE字面量，会导致整个表达式降级为DOUBLE
SELECT CAST(1.1 AS DECIMAL(10,2)) + 2.2;

-- DO: 所有操作数统一为DECIMAL
SELECT CAST(1.1 AS DECIMAL(10,2)) + CAST(2.2 AS DECIMAL(10,2));
```

### 整数字面量默认是 INT 类型（溢出 INT 值域才升 BIGINT），参与 DECIMAL 运算需 CAST

> 来源：[MaxCompute 2.0 数据类型版本] 文档原文："整型常量的语义会默认为 INT 类型……如果常量过长，超过了 INT 的值域而又没有超过 BIGINT 的值域，则会作为 BIGINT 类型处理"。

```sql
-- DON'T: 100 是 INT，与 DECIMAL 列相除的精度行为不可靠
SELECT amount / 100 FROM orders;

-- DO: 显式 CAST 为 DECIMAL，避免精度截断
SELECT amount / CAST(100 AS DECIMAL(10,2)) FROM orders;
```

金额推荐 `DECIMAL(18,2)`，单价推荐 `DECIMAL(18,4)`。

---

## 六、MaxCompute特有函数

本章列出第二章函数映射之外的MaxCompute特有函数。

### 数组操作
```sql
ARRAY_CONTAINS(tags, 'vip')           -- 判断包含
SIZE(arr_col)                          -- 数组长度
SORT_ARRAY(arr_col)                    -- 排序
ARRAY_DISTINCT(arr_col)                -- 去重
ARRAY_JOIN(arr_col, ',')               -- 拼接为字符串
```

### MAP操作
```sql
properties['city']                     -- 下标取值
MAP_KEYS(map_col)                      -- 提取所有键
MAP_VALUES(map_col)                    -- 提取所有值
STR_TO_MAP('k1=v1&k2=v2', '&', '=')  -- 字符串转MAP
```

### 其他
```sql
DECODE(status, 1, 'A', 2, 'B', 'unknown')  -- 类似CASE WHEN简写
APPROX_DISTINCT(user_id)              -- 近似去重（大数据场景）
CONCAT_WS(',', a, b, c)               -- 分隔符拼接（**任一参数 NULL 整体返回 NULL**，与 MySQL/Hive 不同）
REGEXP_COUNT(s, '\\d+')               -- 正则匹配计数
GREATEST(a, b, c) / LEAST(a, b, c)    -- 最大/最小值
MEDIAN(col)                           -- 中位数（任意数值列）
PERCENTILE(int_col, 0.5)              -- 百分位精确算法（**官方文档限 BIGINT；DOUBLE 输入会静默截断为整数，DECIMAL 报错**）
PERCENTILE_APPROX(numeric_col, 0.5)   -- 百分位近似算法（DOUBLE 等数值列均可，**保留小数**，DOUBLE 场景推荐用此）
```

---

## 七、DQL扩展语法

### QUALIFY — 窗口函数结果过滤，避免嵌套子查询

```sql
-- DON'T: 用子查询包装
SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC) AS rn FROM emp
) tmp WHERE rn = 1;

-- DO: 用QUALIFY更简洁
SELECT * FROM emp
QUALIFY ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC) = 1;
```

### LEFT SEMI JOIN / LEFT ANTI JOIN — 代替 EXISTS / NOT EXISTS

```sql
-- 当需要 EXISTS 语义时，写 LEFT SEMI JOIN
SELECT a.* FROM users a LEFT SEMI JOIN orders b ON a.id = b.user_id;

-- 当需要 NOT EXISTS 语义时，写 LEFT ANTI JOIN
SELECT a.* FROM users a LEFT ANTI JOIN orders b ON a.id = b.user_id;
```

### PIVOT / UNPIVOT

```sql
-- 行转列
SELECT * FROM t
PIVOT (SUM(amount) FOR category IN ('food' AS food, 'drink' AS drink)) AS pvt;

-- 列转行
SELECT * FROM t
UNPIVOT INCLUDE NULLS (value FOR metric IN (revenue, cost, profit)) AS unpvt;
```

### Hint（小表广播 / MAPJOIN）

```sql
SELECT /*+ MAPJOIN(small) */ * FROM big JOIN small ON big.id = small.id;
```

**何时加**：右表（被广播表）小到能放进单 worker 内存（默认阈值 128MB，由 `odps.optimizer.auto.mapjoin.threshold` 控制），且 CBO 没自动选 MAPJOIN 时。CBO 默认会自动判断小表广播，多数情况下**不需要显式 Hint**。显式 Hint 在小表超阈值时反而触发 `ODPS-0123065: Join exception ... small table exceeds`，此时应去掉 Hint 或调大 `odps.sql.mapjoin.memory.max`。非等值 JOIN / 笛卡尔积场景必须加 Hint（CBO 不会自动加）。

其他Hint: `SKEWJOIN`(倾斜)、`RANGEJOIN`(范围)、`DYNAMICFILTER`(动态过滤)、`DISTMAPJOIN`(分布式MapJoin)、`CONDITIONALJOIN`(条件JOIN)、`SELECTIVITY`(选择率)、`MATERIALIZE`(物化子查询)

### LIKE ANY / LIKE ALL — 多模式匹配

```sql
SELECT * FROM t WHERE name LIKE ANY ('%张%', '%李%', '%王%');
SELECT * FROM t WHERE tags LIKE ALL ('%vip%', '%active%');
```

### WINDOW 命名窗口

```sql
SELECT user_id, SUM(amount) OVER w AS total, ROW_NUMBER() OVER w AS rn
FROM orders WHERE dt = '2024-01-15'
WINDOW w AS (PARTITION BY user_id ORDER BY create_time);
```

### 集合操作

```sql
SELECT * FROM t1 UNION ALL SELECT * FROM t2;    -- 合并(含重复，推荐)
SELECT * FROM t1 UNION SELECT * FROM t2;         -- 合并(去重，代价高)
SELECT * FROM t1 INTERSECT SELECT * FROM t2;     -- 交集
SELECT * FROM t1 MINUS SELECT * FROM t2;         -- 差集 (MINUS = EXCEPT)
```

### LIMIT

```sql
SELECT * FROM t LIMIT 10;
SELECT * FROM t LIMIT 10 OFFSET 20;
```

### 其他扩展语法速查

| 语法 | 示例 |
|------|------|
| SELECT * EXCEPT | `SELECT * EXCEPT (password) FROM users` |
| SELECT * REPLACE | `SELECT * REPLACE (UPPER(name) AS name) FROM t` |
| IS NOT DISTINCT FROM | `WHERE col1 IS NOT DISTINCT FROM col2`（NULL安全等值） |
| VALUES 行构造器 | `SELECT * FROM (VALUES (1,'a'),(2,'b')) AS t(id,name)` |
| TABLESAMPLE(百分比) | `SELECT * FROM t TABLESAMPLE(10 PERCENT)` |
| TABLESAMPLE(桶采样) | `SELECT * FROM t TABLESAMPLE(BUCKET 1 OUT OF 10 ON id)` |
| WITH RECURSIVE\*\* | `WITH RECURSIVE cte AS (... UNION ALL ...) SELECT * FROM cte` |
| DISTRIBUTE BY + SORT BY | `SELECT * FROM t DISTRIBUTE BY key SORT BY key`（局部排序） |
| CLUSTER BY | `SELECT * FROM t CLUSTER BY key`（等价DISTRIBUTE+SORT同列） |
| UNNEST + LATERAL VIEW | `SELECT t.id, elem FROM t LATERAL VIEW EXPLODE(t.arr) u AS elem`（**MaxCompute 不支持 PG 风格的 `UNNEST(...) AS u(col)` 列别名，会报 `ODPS-0130071: column alias is not supported in unnest`**） |
| Lambda (TRANSFORM) | `SELECT TRANSFORM(arr, x -> x * 2) FROM t` |
| Lambda (FILTER) | `SELECT FILTER(arr, x -> x > 0) FROM t` |
| WITHIN GROUP | `SELECT WM_CONCAT(',', name) WITHIN GROUP (ORDER BY id) FROM t` |
| ZORDER BY | `INSERT OVERWRITE TABLE t [PARTITION (...)] SELECT ... FROM src ZORDER BY col1, col2`（**ZORDER BY 跟在 FROM 子句末尾，列名不带括号**；只能用于 INSERT；2–4 列；与 ORDER BY/CLUSTER BY/SORT BY 互斥；SELECT 单独使用报 `ODPS-0130071: ZORDER BY only support insert`；全局模式需 `SET odps.sql.default.zorder.type=global;`） |
| STRUCT | `SELECT STRUCT(user_id, name) AS info FROM t` |
| 时间旅行(按时间)*  | `SELECT * FROM t TIMESTAMP AS OF '2024-01-01 00:00:00'` |
| 时间旅行(按版本)*  | `SELECT * FROM t VERSION AS OF 3` |
| NATURAL JOIN | `SELECT * FROM t1 NATURAL JOIN t2` |
| FILTER 聚合 | `SELECT COUNT(*) FILTER (WHERE status='active') FROM t` |
| TRANSFORM 脚本 | `SELECT TRANSFORM(c1,c2) USING 'python x.py' AS (o1,o2) FROM t` |
| 三级命名空间 | `project.schema.table` |

\* 时间旅行（TIMESTAMP/VERSION AS OF）仅支持 Transactional Table 2.0 / Iceberg / Delta 等具备版本化能力的表；普通 ODPS 表上使用会报错。

\*\* WITH RECURSIVE：offline 模式默认可用，**MCQA / MCQA2 模式拒绝**（编译期报 `rcte.session.mode`）。需要在 MCQA 下用，先 `SET odps.mcqa.disable=true;`。迭代次数上限由 `odps.sql.rcte.max.iterate.num` 控制（默认 10，硬上限 100）。

---

## 八、正则表达式

正则规范因模式而异：
- **默认（legacy）模式**：MaxCompute 自定义正则规范（Java 兼容子集）
- **Hive 兼容模式**（`SET odps.sql.hive.compatible=true;`）：完整 Java 正则规范

SQL 字符串中反斜杠必须**双重转义**（客户端提交时统一规则）。

```sql
-- \d 在SQL中写成 \\d
SELECT * FROM t WHERE col RLIKE '\\d{4}-\\d{2}-\\d{2}';
SELECT REGEXP_EXTRACT(text, '(1[3-9]\\d{9})', 1) AS phone FROM t;
SELECT REGEXP_REPLACE(str, '[^0-9]', '') AS digits_only FROM t;
```

`\d` `\w` `\s` 可用，`*?` `+?` 非贪婪可用，`(?=...)` 前向断言可用。

---

## 九、窗口函数Frame

### 当使用累计求和、移动平均时，必须显式指定 ROWS frame

默认 frame 行为依赖模式，做**累计聚合 / 移动平均**时必须显式指定 ROWS（否则 Hive vs 非 Hive 模式下结果不同）：
- Hive 兼容模式（`SET odps.sql.hive.compatible=true`）：默认 `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`
- 非 Hive 模式 + ORDER BY + 聚合函数（AVG/COUNT/MAX/MIN/STDDEV/SUM）：默认 `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`

> 注：ROW_NUMBER / RANK / DENSE_RANK 等位置类窗口函数**不需要**显式 ROWS 子句。仅累计/移动聚合需要。

```sql
-- DON'T: 依赖默认RANGE frame
SELECT SUM(amount) OVER (ORDER BY dt) FROM t;

-- DO: 显式指定ROWS
SELECT SUM(amount) OVER (ORDER BY dt ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) FROM t;

-- 移动平均: 显式指定窗口大小
SELECT AVG(amount) OVER (ORDER BY dt ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) FROM t;
```

ROWS=物理行计数，RANGE=逻辑值范围（重复值同组），GROUPS=按组（SQL:2011标准）。

支持EXCLUDE: `EXCLUDE CURRENT ROW` / `EXCLUDE GROUP` / `EXCLUDE TIES` / `EXCLUDE NO OTHERS`

---

## 十、SQL 数量限制

以下限制经常触发报错，生成SQL时需注意不要超出。

**SQL 文本与执行计划规模：**
| 限制项 | 上限 | 超限后果 |
|--------|------|---------|
| SQL 语句长度 | 2 MB | 解析失败（ODPS-0130161）|
| 执行计划大小 | 1 MB | `The Size of Plan is too large`（ODPS-0010000），需拆 SQL |
| 作业最长运行时间 | 24h 默认 / 72h 上限 | 可用 `SET odps.sql.job.max.time.hours=72;` |

**集合与 JOIN：**
| 限制项 | 上限 | 备注 |
|--------|------|------|
| 单 SELECT 窗口函数数 | 建议 ≤ 5 | 软建议非硬限制；超出可能触发 SQL 规模超限（ODPS-0130071/0130161） |
| UNION ALL 表数 | 256 张 | |
| MAPJOIN 小表数 | 128 张 | 总内存 ≤ 512 MB |
| IN 参数数 | 建议 ≤ 1,024 | 过多严重影响编译性能 |
| WHERE 条件数 | 256 | |
| 子查询嵌套层级 | 建议 ≤ 8 层 | |
| SELECT DISTINCT 列数 | ≤ 256 | |

**子查询返回行数：**
| 限制项 | 上限 | 超限后果 |
|--------|------|---------|
| 分区裁剪子查询返回行 | 硬上限 9,999，建议 ≤1,000 | ODPS-0130111 `Subquery partition pruning exception` |

**对象与分区规模：**
| 限制项 | 上限 |
|--------|------|
| 单表分区数 | 60,000 |
| 分区层级 | 6 级 |
| 单表列数 | 1,200 |
| 单查询最大分区扫描数 | 10,000 |

**结果与数据：**
| 限制项 | 上限 | 备注 |
|--------|------|------|
| SELECT 屏显输出行 | 10,000 | 需完整结果用 INSERT OVERWRITE 落表 |
| 单元格（单列单行）大小 | 8 MB | |

---

## 十一、运算符差异

| 运算 | MaxCompute | 标准 SQL |
|------|-----------|---------|
| 字符串拼接 | `CONCAT(a, b)` 或 `a \|\| b` | `a + b`（部分DB） |
| DOUBLE 比较 | 有精度问题，建议 CAST 为 DECIMAL | 同 |
| 位左移 | `SHIFTLEFT(a, n)` | `a << n` |
| 位右移 | `SHIFTRIGHT(a, n)` | `a >> n` |
| 整除 | `a DIV b` | 无标准 |
| 正则匹配 | `col RLIKE pattern` | `col REGEXP pattern` |

**百分比/比率计算**: 整数除法会截断为0，必须 `CAST(... AS DOUBLE)` 或 `CAST(... AS DECIMAL)`。详见第五章类型陷阱。

---

## 十二、数据类型

**特有类型:**
- `DATETIME` — 不带时区的日期时间，字面量: `DATETIME '2024-01-01 00:00:00'`
- `TIMESTAMP_NTZ` — 无时区的Timestamp（区别于DATETIME和TIMESTAMP）
- `STRING` — 不限长字符串，大多数场景使用STRING而非VARCHAR
- `JSON` — JSON类型，支持可选schema: `JSON<name:STRING, age:INT>`
- `VECTOR(type, dim)` — AI向量类型
- `BLOB` — 二进制大对象
- `GEOGRAPHY` — 地理空间类型

**复杂类型:**
- `ARRAY<STRING>` — 数组
- `MAP<STRING, INT>` — 键值对
- `STRUCT<name:STRING, age:INT>` — 结构体

**字面量:**
```sql
DATETIME '2024-01-01 00:00:00'
JSON '{"key": "value"}'           -- 需先 `SET odps.sql.type.json.enable=true;` 启用 JSON 类型
INTERVAL '1' DAY                  -- 需先 `SET odps.sql.type.system.odps2=true;` 启用 INTERVAL_DAY_TIME 类型
INTERVAL '1-2' YEAR TO MONTH      -- 同上，需 odps2 启用 INTERVAL_YEAR_MONTH 类型
CURRENT_DATE() / CURRENT_TIMESTAMP()
-- 注：CURRENT_DATE 无括号形式需先 `SET odps.sql.hive.compatible=true;`；
--     LOCALTIMESTAMP 在 MaxCompute 不可用，请使用 CURRENT_TIMESTAMP() 代替；
--     `CURRENT_TIMESTAMP()` 默认返回 `TIMESTAMP`；若 `SET odps.sql.timestamp.function.ntz=true`，则返回 `TIMESTAMP_NTZ`
```

---

## 十三、常用 SET 参数速查表

会话级参数，写在 SQL 前用 `SET key=value;`。仅列文本生成会用到的；运行期资源调优类（mapper/reducer memory 等）见 sql_common_errors.md。

### 兼容性 / 方言开关

| 参数 | 默认 | 用途 |
|------|------|------|
| `odps.sql.type.system.odps2` | false | odps2 严格类型系统；启用后 TINYINT / TIMESTAMP / INTERVAL 等类型才能使用。未启用时报错信息会明确提示 `set odps.sql.type.system.odps2=true to use it`（**注**：`DECIMAL(p,s)` 不归这个开关，见下） |
| `odps.sql.decimal.odps2` | false | 启用 `DECIMAL(p,s)` 精度+刻度；不开时只支持无参 `DECIMAL`，写 `DECIMAL(10,2)` 会报 `precision and scale is not currently supported` |
| `odps.sql.type.json.enable` | false | 启用 JSON 类型系统（JSON 字面量 / `CAST AS JSON` / `JSON_EXTRACT`）；不开时 `JSON_EXTRACT(STRING, ...)` 报 0130121 |
| `odps.sql.hive.compatible` | false | Hive 兼容模式，启用后部分 Hive 语法（如 TRUNC(d, 'MM')）可用 |
| `odps.sql.allow.fullscan` | false | 允许分区表全表扫描（无分区过滤时使用，慎用） |
| `odps.sql.allow.cartesian` | false | 允许笛卡尔积 JOIN（兜底，优先用 mapjoin） |
| `odps.sql.validate.orderby.limit` | true | 强制 ORDER BY 必须配 LIMIT；设为 false 可解除 |
| `odps.sql.submit.mode` | — | 设为 `script` 启用过程式扩展（变量/IF/LOOP/SQL UDF/TEMPORARY TABLE） |
| `odps.sql.step.script.mode` | false | 配合 `submit.mode=script` 启用 step-script-mode；TEMPORARY TABLE 需要这个 + submit.mode=script 双开关 |
| `odps.sql.timestamp.function.ntz` | false | `CURRENT_TIMESTAMP()` 返回 `TIMESTAMP_NTZ` 而非 `TIMESTAMP` |

### 限制开关

| 参数 | 默认 | 用途 |
|------|------|------|
| `odps.sql.udf.strict.mode` | true | UDF 严格模式；公有云常见同义参数为 `odps.function.strictmode`（不同环境/版本参数名可能不同）；脏值 CAST 失败时设为 false 让无效行**转 NULL**（不是丢弃整行） |
| `odps.sql.udf.timeout` | 600 | UDF 超时秒数，范围 0-3600 |
| `odps.sql.rcte.max.iterate.num` | 10 | 递归 CTE 最大迭代次数，硬上限 100 |
| `odps.mcqa.disable` | false | 关闭 MCQA 查询加速（含 UDF 或 DML 时需要） |
| `odps.sql.job.max.time.hours` | 24 | 作业最长运行时间（小时），上限 72 |

### 优化器 Hint（Hint 形式优先于 SET）

| 参数 | 默认 | 用途 |
|------|------|------|
| `odps.optimizer.auto.mapjoin.threshold` | 134217728 (128MB) | 自动 MAPJOIN 小表阈值（字节）；设为 0 禁用自动 MAPJOIN |
| `odps.sql.mapjoin.memory.max` | — | MAPJOIN 内存上限（MB），常见 1024-4096 |
| `odps.sql.mapper.split.size` | 256 | 单个 mapper 输入数据量（MB），降低可减少 instance 数 |

> odps2 与 Hive 兼容模式不互斥：odps2 控制类型系统，Hive 兼容控制 SQL 语法。两者都可同时开启。
