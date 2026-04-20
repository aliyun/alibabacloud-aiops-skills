# Lindorm SQL 语法参考

以下收录了常用的 DDL 和 DML 语句。

## 重要约束
> **此约束具有最高优先级，必须严格遵守。**
1. **禁止推测和联想**：只能基于本 Skill 文档中明确记载的内容回答用户问题，严禁推测、联想或生成文档中不存在的 SQL 语法、参数、功能或配置。
2. **不确定时必须声明**：如果文档中没有相关信息，必须明确告知用户“当前文档未收录此内容”，并引导用户查阅官方文档。
3. **禁止混淆来源**：不得将其他数据库（如 MySQL、HBase、PostgreSQL）的语法或特性当作 Lindorm 的功能来回答。
4. **代码示例需要出处**：生成的代码示例必须基于文档中的模板，参数和语法必须与文档一致。

## 执行步骤
1. 当用户提到的 SQL 语句已收录在下方文档中时，优先使用收录的信息回复用户。
2. 如果用户提到的 SQL 语句未收录在下方文档中时，查询官方文档回复用户。
   - **DDL**: https://help.aliyun.com/zh/lindorm/developer-reference/wide-table-ddl/
   - **DML**: https://help.aliyun.com/zh/lindorm/developer-reference/wide-table-dml/
   - **DCL**：https://help.aliyun.com/zh/lindorm/developer-reference/wide-table-dcl/
3. 如果用户提到的 SQL 语句既未收录在下方文档中，也未找到官方文档中的相关信息时，必须明确告知用户“当前文档未收录此内容”。

## DDL 语句

> 详细建表语法、数据类型、表属性请参考 table-design.md

### CREATE TABLE - 创建表

**基本语法**:
```sql
CREATE TABLE [IF NOT EXISTS] table_name (
    column_name data_type [NOT NULL],
    ...
    PRIMARY KEY (column_name [, column_name]...)
)
[WITH (option = value, ...)]
```

**示例 - 基础建表**:
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

**示例 - 复合主键**:
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

**示例 - 带表属性**:
```sql
CREATE TABLE IF NOT EXISTS logs (
    log_id VARCHAR NOT NULL,
    level VARCHAR,
    message VARCHAR,
    created_at TIMESTAMP,
    PRIMARY KEY (log_id)
) WITH (
    TTL = '604800',           -- 7天过期
    COMPRESSION = 'ZSTD',     -- ZSTD压缩
    NUMREGIONS = 10           -- 预分10个Region
);
```

**示例 - 预分区建表**:
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

**示例 - 指定分区键**:
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

### 常用表属性

| 属性 | 类型 | 说明 | 示例 |
|------|------|------|------|
| TTL | INT | 数据有效期(秒) | TTL = '86400' (1天) |
| COMPRESSION | STRING | 压缩算法: SNAPPY/ZSTD/LZ4 | COMPRESSION = 'ZSTD' |
| NUMREGIONS | INT | 预分区数量 | NUMREGIONS = 16 |
| STARTKEY | STRING | 分区起始Key | STARTKEY = '0' |
| ENDKEY | STRING | 分区结束Key | ENDKEY = 'z' |
| SPLITKEYS | STRING | 自定义分区点 | SPLITKEYS = 'a,m,z' |
| MUTABILITY | STRING | 索引写入模式 | MUTABILITY = 'MUTABLE_LATEST' |
| CONSISTENCY | STRING | 一致性级别 | CONSISTENCY = 'strong' |

### ALTER TABLE - 修改表

**添加列**:
```sql
ALTER TABLE user_profile ADD COLUMN email VARCHAR;
ALTER TABLE user_profile ADD COLUMN phone VARCHAR, address VARCHAR;
```

**修改 TTL**:
```sql
ALTER TABLE logs SET TTL = '2592000';  -- 改为30天
ALTER TABLE logs SET TTL = '';          -- 取消TTL，数据不过期
```

### DROP TABLE - 删除表

```sql
DROP TABLE IF EXISTS table_name;
```

### TRUNCATE TABLE - 清空表

```sql
TRUNCATE TABLE table_name;
```

### CREATE INDEX - 创建索引

**二级索引**:
```sql
-- 在建表时创建
CREATE TABLE orders (
    order_id VARCHAR NOT NULL,
    user_id VARCHAR,
    status VARCHAR,
    amount DOUBLE,
    PRIMARY KEY (order_id),
    INDEX idx_user USING KV (user_id),
    INDEX idx_status USING KV (status) INCLUDE (amount)
);

-- 单独创建二级索引
CREATE INDEX idx_user USING KV ON orders (user_id);
```

**搜索索引**:

> ⚠️ **重要**：搜索索引需先在控制台开通（宽表引擎 → 搜索索引 → 立即开通），否则创建会报 `SERVER INTERNAL ERROR`。详见 [table-design.md](table-design.md#搜索索引开通条件)。

```sql
-- 基础搜索索引
CREATE INDEX idx_search USING SEARCH ON orders (status);

-- 带分词器的搜索索引
CREATE INDEX idx_text USING SEARCH ON articles (
  title(type=text, analyzer=ik),
  content(type=text, analyzer=ik)
);

-- 分词查询
SELECT * FROM articles WHERE MATCH(content) AGAINST('关键词');
```

### SHOW / DESCRIBE - 查看信息

```sql
-- 查看所有表
SHOW TABLES;

-- 查看表结构
DESCRIBE table_name;

-- 查看建表语句
SHOW CREATE TABLE table_name;

-- 查看索引
SHOW INDEX FROM table_name;
```

---

## DML 语句

### UPSERT - 插入/更新数据

UPSERT 是 Lindorm 推荐的写入方式，如果主键存在则更新，不存在则插入。

**单条写入**:
```sql
UPSERT INTO user_profile (user_id, nickname, age) 
VALUES ('u001', '张三', 25);
```

**带时间戳写入** (使用 HINT):
```sql
-- 指定写入数据的时间戳（毫秒）
UPSERT /*+ _l_ts_(1704067200000) */ INTO user_profile (user_id, nickname, age) 
VALUES ('u001', '张三', 25);
```

**批量写入** (PreparedStatement):
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

### SELECT - 查询数据

**基本查询**:
```sql
SELECT * FROM user_profile WHERE user_id = 'u001';
```

**指定列查询** (推荐):
```sql
SELECT user_id, nickname, age FROM user_profile WHERE user_id = 'u001';
```

**范围查询**:
```sql
SELECT * FROM user_profile 
WHERE user_id >= 'u001' AND user_id < 'u100';
```

**排序与分页**:
```sql
SELECT * FROM user_profile 
ORDER BY user_id 
LIMIT 100 OFFSET 0;
```

**条件查询**:
```sql
SELECT * FROM user_profile 
WHERE age > 25 AND age < 35;

SELECT * FROM user_profile 
WHERE nickname LIKE '张%';

SELECT * FROM user_profile 
WHERE user_id IN ('u001', 'u002', 'u003');
```

**聚合查询**:
```sql
SELECT COUNT(*) FROM user_profile;
SELECT MAX(age), MIN(age), AVG(age) FROM user_profile;
```

**HINT 使用**:
```sql
-- 强制允许低效查询（全表扫描）
SELECT /*+ _l_allow_filtering_ */ * FROM user_profile;

-- 指定操作超时时间（毫秒）
SELECT /*+ _l_operation_timeout_(30000) */ * FROM user_profile WHERE age > 25;

-- 强制使用索引
SELECT /*+ _l_force_index_('idx_name') */ * FROM user_profile WHERE name = 'test';

-- 忽略索引
SELECT /*+ _l_ignore_index_ */ * FROM user_profile WHERE name = 'test';
```

### UPDATE - 更新数据

**重要**: UPDATE 必须指定完整的主键条件。

```sql
-- 正确: 指定完整主键
UPDATE user_profile SET age = 26 WHERE user_id = 'u001';

-- 错误: 不支持批量更新
UPDATE user_profile SET age = 26 WHERE age > 25;  -- 会报错
```

### DELETE - 删除数据

**单行删除**:
```sql
DELETE FROM user_profile WHERE user_id = 'u001';
```

**复合主键删除**:
```sql
DELETE FROM order_detail WHERE order_id = 'o001' AND item_seq = 1;
```

### JSON 数据写入与查询

> 数据类型定义请参考 [table-design.md](table-design.md)

**写入方式**:
```sql
-- 方式 1: 直接写入 JSON 字符串
UPSERT INTO tb(p1, c2) VALUES(1, '{"k1": 4, "k2": {"k3": {"k4": 4}}}');

-- 方式 2: 使用 json_object 函数
UPSERT INTO tb(p1, c2) VALUES(2, json_object('k1', 2, 'k2', '2'));
-- 等价于：UPSERT INTO tb(p1,c2) VALUES(2,'{"k1":2,"k2":"2"}');

-- 方式 3: 使用 json_array 函数
UPSERT INTO tb(p1, c2) VALUES(3, json_array(1, 2, json_object('k1', 3, 'k2', '3')));
-- 等价于：UPSERT INTO tb(p1,c2) VALUES(3,'[1,2,{"k1":3,"k2":"3"}]');
```

**查询 JSON 字段**:
```sql
-- 获取 JSON 对象中的值 (SELECT 子句)
SELECT p1, json_extract(c2, '$.k1') AS k1_value FROM tb WHERE p1 = 1;

-- 嵌套路径查询
SELECT json_extract(c2, '$.k2.k3.k4') FROM tb WHERE p1 = 4;

-- 数组索引访问
SELECT json_extract(c2, '$[2].k2') FROM tb WHERE p1 = 3;

-- WHERE 条件过滤
SELECT * FROM tb 
WHERE p1 >= 1 AND p1 < 4 
AND json_extract(c2, '$.k2') > '0';
```

---

## 常用函数

### 字符串函数

> 要求宽表引擎 2.5.1.1+

| 函数 | 说明 | 示例 |
|------|------|------|
| `CONCAT(s1, s2, ...)` | 拼接多个字符串 | `SELECT CONCAT('a','b','c')` → `abc` |
| `LENGTH(s)` | 计算字符串长度 | `SELECT LENGTH('hello')` → `5` |
| `LOWER(s)` | 转为小写 | `SELECT LOWER('ABC')` → `abc` |
| `UPPER(s)` | 转为大写 | `SELECT UPPER('abc')` → `ABC` |
| `TRIM(s)` | 删除前后空格 | `SELECT TRIM('  ab  ')` → `ab` |
| `SUBSTR(s, pos[, len])` | 截取子串 | `SELECT SUBSTR('hello', 2, 3)` → `ell` |
| `REPLACE(s, from, to)` | 替换子串 | `SELECT REPLACE('abc', 'b', 'x')` → `axc` |
| `REVERSE(s)` | 返回逆序字符串 | `SELECT REVERSE('abc')` → `cba` |
| `MD5(s)` | 计算 MD5 哈希 | `SELECT MD5('abc')` → `900150983cd24fb0...` |
| `SHA256(s)` | 计算 SHA256 哈希 | `SELECT SHA256('abc')` → `ba7816bf8f01cfea...` |
| `START_WITH(s, prefix)` | 判断前缀 | `SELECT START_WITH('hello', 'he')` → `true` |

**正则表达式函数**:
```sql
-- REGEXP_REPLACE: 正则替换，支持指定开始位置
SELECT REGEXP_REPLACE('abcbc', 'b', 'x', 2);  -- axcxc

-- REGEXP_SUBSTR: 正则提取子串
SELECT REGEXP_SUBSTR('abc123def', '[0-9]+');  -- 123

-- MATCH: 判断是否匹配正则
SELECT * FROM table WHERE MATCH(column, 'pattern');
```

### 聚合函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `COUNT(*)` | 统计行数 | `SELECT COUNT(*) FROM table` |
| `COUNT(column)` | 统计非 NULL 值个数 | `SELECT COUNT(name) FROM table` |
| `SUM(column)` | 求和（仅数值类型） | `SELECT SUM(amount) FROM orders` |
| `AVG(column)` | 平均值（仅数值类型） | `SELECT AVG(price) FROM products` |
| `MAX(column)` | 最大值 | `SELECT MAX(score) FROM results` |
| `MIN(column)` | 最小值 | `SELECT MIN(score) FROM results` |

**高级聚合函数** (宽表引擎 2.7.9+):
```sql
-- HEAD: 返回第一个非 NULL 值，支持排序
SELECT HEAD(temperature ORDER BY time) FROM sensor;  -- 最早的温度
SELECT HEAD(temperature ORDER BY time DESC) FROM sensor;  -- 最新的温度

-- GROUP_CONCAT: 分组拼接字符串
SELECT region, GROUP_CONCAT(device_id) FROM sensor GROUP BY region;
-- 结果: north-cn | dev1,dev2,dev3

-- GROUP_CONCAT 带排序和分隔符
SELECT region, GROUP_CONCAT(device_id ORDER BY time SEPARATOR '|') 
FROM sensor GROUP BY region;
-- 结果: north-cn | dev1|dev2|dev3

-- GROUP_CONCAT 去重
SELECT region, GROUP_CONCAT(DISTINCT device_id) FROM sensor GROUP BY region;
```

### 时间函数

> 要求宽表引擎 2.7.8+，Lindorm SQL 2.8.7.0+

| 函数 | 说明 | 示例 |
|------|------|------|
| `DATE_FORMAT(ts, format)` | 格式化时间戳 | 见下方示例 |
| `FROM_UNIXTIME(seconds)` | Unix 时间戳转 TIMESTAMP | `SELECT FROM_UNIXTIME(1704067200)` |
| `UNIX_TIMESTAMP(ts)` | TIMESTAMP 转 Unix 时间戳 | `SELECT UNIX_TIMESTAMP('2024-01-01 00:00:00')` |
| `DATEDIFF(ts1, ts2)` | 计算日期差(天) | `SELECT DATEDIFF('2024-01-05', '2024-01-01')` → `4` |

**DATE_FORMAT 格式说明符**:
```sql
SELECT DATE_FORMAT('2024-01-15 17:30:45', '%Y-%m-%d %H:%i:%s');
-- 2024-01-15 17:30:45

SELECT DATE_FORMAT('2024-01-15 17:30:45', '%Y年%m月%d日 %H:%i');
-- 2024年01月15日 17:30

SELECT DATE_FORMAT('2024-01-15 17:30:45', 'at %T on %b %D, %Y');
-- at 17:30:45 on JAN 15th, 2024
```

| 格式符 | 说明 | 示例 |
|--------|------|------|
| `%Y` | 四位年份 | 2024 |
| `%y` | 两位年份 | 24 |
| `%m` | 两位月份 | 01-12 |
| `%d` | 两位日期 | 01-31 |
| `%H` | 24小时制小时 | 00-23 |
| `%h` | 12小时制小时 | 01-12 |
| `%i` | 分钟 | 00-59 |
| `%s` / `%S` | 秒 | 00-59 |
| `%T` | 时间 (HH:mm:ss) | 17:30:45 |
| `%D` | 带序数的日期 | 1st, 2nd, 15th |
| `%b` | 月份缩写 | Jan, Feb |
| `%M` | 月份全称 | January |
| `%W` | 星期全称 | Monday |
| `%a` | 星期缩写 | Mon |
| `%p` | AM/PM | AM |

**FROM_UNIXTIME 示例**:
```sql
-- Unix 时间戳转 TIMESTAMP
SELECT FROM_UNIXTIME(1704067200);  -- 2024-01-01 08:00:00 (+08:00时区)

-- 支持毫秒精度（使用小数）
SELECT FROM_UNIXTIME(1704067200.123);  -- 2024-01-01 08:00:00.123

-- 同时格式化输出
SELECT FROM_UNIXTIME(1704067200, '%Y-%m-%d');  -- 2024-01-01
```


**常用 JSON 函数**:

**构造函数**:
- `json_object(key1, value1, ...)`: 构建 JSON 对象
  ```sql
  SELECT json_object('name', 'Alice', 'age', 25);
  -- {"name": "Alice", "age": 25}
  ```
- `json_array(value1, value2, ...)`: 构建 JSON 数组
  ```sql
  SELECT json_array('Java', 'Python', 'Go');
  -- ["Java", "Python", "Go"]
  ```

**提取函数**:
- `json_extract(json_doc, path)`: 提取 JSON 值（返回 JSON 类型）
  ```sql
  SELECT json_extract('{"name": "Alice"}', '$.name');
  -- "Alice"
  ```
- `json_extract_string(json_doc, path)`: 提取并转换为 VARCHAR 类型
  ```sql
  SELECT json_extract_string('{"name": "Alice"}', '$.name');
  -- Alice (VARCHAR)
  ```
- `json_extract_long(json_doc, path)`: 提取并转换为 BIGINT 类型
  ```sql
  SELECT json_extract_long('{"id": 123456}', '$.id');
  -- 123456 (BIGINT)
  ```
- `json_extract_double(json_doc, path)`: 提取并转换为 DOUBLE 类型
  ```sql
  SELECT json_extract_double('{"score": 95.5}', '$.score');
  -- 95.5 (DOUBLE)
  ```

**路径语法**:
- `$.key`: 访问对象的 key
- `$[index]`: 访问数组的索引（从 0 开始）
- `$.key1.key2`: 嵌套访问
- `$[*]`: 通配符匹配所有数组元素

**包含检查函数**:
- `json_contains(target, candidate[, path])`: 检查是否包含指定值
  ```sql
  -- 检查数组是否包含某个元素
  SELECT json_contains('["Java", "Python"]', '"Java"');
  -- 1 (true)
  
  -- 检查对象是否包含某个属性
  SELECT json_contains('{"a": 1, "b": 2}', '{"a": 1}');
  -- 1 (true)
  
  -- 检查指定路径
  SELECT json_contains('{"skills": ["Java", "Python"]}', '"Java"', '$.skills');
  -- 1 (true)
  
  -- WHERE 条件中使用
  SELECT * FROM table WHERE json_contains(data, '"active"', '$.status');
  ```

**更新函数**:
- `json_set(json_doc, path, value[, path, value]...)`: 插入或更新值
  ```sql
  SELECT json_set('{"a": 1}', '$.b', 2);
  -- {"a": 1, "b": 2}
  ```
- `json_insert(json_doc, path, value)`: 仅在路径不存在时插入
  ```sql
  SELECT json_insert('{"a": 1}', '$.b', 2);
  -- {"a": 1, "b": 2}
  ```
- `json_replace(json_doc, path, value)`: 仅在路径存在时更新
  ```sql
  SELECT json_replace('{"a": 1}', '$.a', 10);
  -- {"a": 10}
  ```
- `json_remove(json_doc, path[, path]...)`: 删除指定路径的值
  ```sql
  SELECT json_remove('{"a": 1, "b": 2}', '$.b');
  -- {"a": 1}
  ```

**注意事项**:
- 如果在 JSON 列中写入非 JSON 对象或字符串，会报错
- 不同数据类型比较规则与 MySQL 相同

---

## 特殊语法

### HINT 语法详解

HINT 是 SQL 的补充语法，可以改变 SQL 的执行方式。HINT 必须紧跟在 `INSERT`、`UPSERT`、`DELETE`、`SELECT` 关键字之后。

> 要求宽表引擎 2.3.1+

**基本语法**:
```sql
/*+ hint1, hint2, ... */
```

#### HINT 参数列表

| HINT | 类型 | 说明 | 支持语句 |
|------|------|------|----------|
| `_l_operation_timeout_(N)` | INT | DML 操作超时时间，单位毫秒，默认 120000 | UPSERT, DELETE, UPDATE, SELECT |
| `_l_allow_filtering_` | - | 允许低效全表扫描查询 | SELECT |
| `_l_force_index_('idx')` | STRING | 强制使用指定索引 | SELECT |
| `_l_ignore_index_` | - | 忽略索引，直接查表 | SELECT |
| `_l_ts_(N)` | BIGINT | 指定写入/查询的时间戳（毫秒） | UPSERT, SELECT |
| `_l_versions_(N)` | INT | 返回最新 N 个版本的数据 | SELECT |
| `_l_ts_min_(N)` | BIGINT | 过滤结果，返回时间戳 >= N 的数据 | SELECT |
| `_l_ts_max_(N)` | BIGINT | 过滤结果，返回时间戳 < N 的数据 | SELECT |
| `_l_hot_only_` / `_l_hot_only_(true)` | BOOLEAN | 仅查询热存储数据 | SELECT |

#### 超时与性能控制

```sql
-- 设置操作超时时间 30 秒
SELECT /*+ _l_operation_timeout_(30000) */ COUNT(*) FROM big_table;

-- 允许全表扫描（当 WHERE 条件不包含主键时）
SELECT /*+ _l_allow_filtering_ */ * FROM users WHERE age > 30;

-- 组合使用
SELECT /*+ _l_operation_timeout_(30000), _l_allow_filtering_ */ * 
FROM users WHERE age > 30;
```

#### 索引控制

```sql
-- 强制使用指定索引
SELECT /*+ _l_force_index_('idx_user_name') */ * FROM users WHERE name = 'test';

-- 忽略索引，直接查主表（用于性能对比）
SELECT /*+ _l_ignore_index_ */ * FROM users WHERE name = 'test';
```

**注意**: `_l_force_index_` 和 `_l_ignore_index_` 不能同时使用

#### 多版本数据管理

Lindorm 支持每列存储多个版本的数据，通过时间戳标识版本（时间戳越大版本越新）。

**创建多版本表**:
```sql
-- VERSIONS='5' 表示每列最多保留 5 个版本
CREATE TABLE sensor_data (
    device_id VARCHAR,
    temperature DOUBLE,
    PRIMARY KEY(device_id)
) WITH (VERSIONS='5');

-- 修改已有表的版本数
ALTER TABLE sensor_data SET 'VERSIONS' = '10';
```

**写入指定时间戳**:
```sql
-- 指定时间戳写入（毫秒）
UPSERT /*+ _l_ts_(1704067200000) */ INTO sensor_data(device_id, temperature) 
VALUES ('dev001', 25.5);

UPSERT /*+ _l_ts_(1704067260000) */ INTO sensor_data(device_id, temperature) 
VALUES ('dev001', 26.0);  -- 同一设备，新版本
```

**查询多版本数据**:
```sql
-- 查询指定时间戳的数据
SELECT /*+ _l_ts_(1704067200000) */ device_id, temperature 
FROM sensor_data WHERE device_id = 'dev001';

-- 查询最新 N 个版本
SELECT /*+ _l_versions_(3) */ device_id, temperature, temperature_l_ts 
FROM sensor_data WHERE device_id = 'dev001';

-- 查询时间戳范围 [min, max)
SELECT /*+ _l_ts_min_(1704067200000), _l_ts_max_(1704153600000) */ 
    device_id, temperature, temperature_l_ts 
FROM sensor_data WHERE device_id = 'dev001';
```

**查看列的时间戳**: 在列名后加 `_l_ts` 后缀
```sql
-- temperature_l_ts 返回 temperature 列的时间戳
SELECT /*+ _l_versions_(2) */ device_id, temperature, temperature_l_ts 
FROM sensor_data;
```

#### 热数据查询

当开通冷存储功能后，可使用 HINT 仅查询热存储中的数据：

```sql
-- 仅查询热数据
SELECT /*+ _l_hot_only_ */ * FROM sensor_data WHERE device_id = 'dev001';
SELECT /*+ _l_hot_only_(true) */ * FROM sensor_data WHERE device_id = 'dev001';

-- 查询所有数据（包括冷数据），与不使用 HINT 等价
SELECT /*+ _l_hot_only_(false) */ * FROM sensor_data WHERE device_id = 'dev001';
```

**注意**: 不支持单独查询冷数据

### 动态列

Lindorm 支持动态列，无需预定义即可写入新列。

```sql
-- 写入动态列
UPSERT INTO user_profile (user_id, _dyn_col_name1) VALUES ('u001', 'value1');

-- 查询动态列
SELECT user_id, _dyn_col_name1 FROM user_profile WHERE user_id = 'u001';
```

### TTL 相关

```sql
-- 查看表的 TTL 设置
SHOW CREATE TABLE table_name;

-- 修改 TTL
ALTER TABLE table_name SET TTL = '86400';

-- 取消 TTL（数据永不过期）
ALTER TABLE table_name SET TTL = '';
```

**注意**: Lindorm 不支持行级 TTL，TTL 是表级别的属性。

---

## SQL 注意事项

### 与 MySQL 的差异

| 特性 | MySQL | Lindorm SQL |
|------|-------|-------------|
| 写入语句 | INSERT/UPDATE | UPSERT (推荐) |
| UPDATE 范围 | 支持批量 | 仅单行 |
| 自增主键 | 支持 | 不支持 |
| 外键 | 支持 | 不支持 |
| 事务 | ACID | 单行原子性 |
| JOIN | 支持 | 不支持 |

### 性能建议

1. **主键查询最快**: 尽量使用主键作为查询条件
2. **避免全表扫描**: 无索引列 WHERE 会被低效查询拦截，需创建索引或用 `/*+ _l_allow_filtering_ */`
3. **限制返回行数**: 使用 LIMIT 避免大量数据返回
4. **使用 PreparedStatement**: 批量操作必用
5. **选择性 SELECT**: 只查询需要的列
6. **子查询用派生表**: WHERE IN/EXISTS 子查询需确保子查询中的过滤列有索引
7. **后缀模糊用搜索索引**: LIKE 前缀 `xxx%` 用二级索引即可，后缀模糊 `%xxx` 需搜索索引（SEARCH）

### 窗口函数

⚠️ **有限支持**：官方兼容性文档标注窗口函数为"暂不支持"，语法不报错但可能存在**正确性或稳定性风险**（服务端计算开销较大）。实测 ROW_NUMBER/RANK/DENSE_RANK/LEAD/SUM OVER/AVG OVER 在当前版本可正常执行，LAG 在低版本存在解析器 bug。生产环境**谨慎使用**，建议优先用计算引擎（OLAP）处理窗口计算。

```sql
-- ROW_NUMBER: 按分组编号
SELECT id, user_name, amount,
       ROW_NUMBER() OVER (PARTITION BY user_name ORDER BY amount DESC) AS rn
FROM orders;

-- RANK: 排名
SELECT id, user_name, amount,
       RANK() OVER (ORDER BY amount DESC) AS rnk
FROM orders;

-- SUM OVER: 分组累计求和
SELECT id, user_name, amount,
       SUM(amount) OVER (PARTITION BY user_name) AS user_total
FROM orders;

-- LEAD/LAG: 前后行引用
SELECT id, amount,
       LAG(amount) OVER (ORDER BY id) AS prev_amt,
       LEAD(amount) OVER (ORDER BY id) AS next_amt
FROM orders;
```

### 子查询

Lindorm SQL 支持派生表（FROM 子句中的子查询），WHERE IN/EXISTS 子查询需索引支持：

```sql
-- 派生表（推荐，无索引也可用）
SELECT * FROM (
    SELECT user_name, SUM(amount) AS total FROM orders GROUP BY user_name
) AS t WHERE total > 4000;

-- WHERE IN 子查询（需子查询中过滤列有索引）
SELECT * FROM orders
WHERE user_name IN (SELECT name FROM users WHERE city = '杭州');

-- 标量子查询（需索引支持）
SELECT id, user_name,
       (SELECT COUNT(*) FROM orders o2 WHERE o2.user_name = orders.user_name) AS order_cnt
FROM orders;
```

> 详见 [sql-usage-notes.md](sql-usage-notes.md) 中的子查询支持章节。

### 保留关键字

以下关键字不能作为表名或列名使用：

```
SELECT, FROM, WHERE, AND, OR, NOT, IN, LIKE, BETWEEN, 
IS, NULL, TRUE, FALSE, CREATE, ALTER, DROP, TABLE, 
INDEX, PRIMARY, KEY, VALUES, UPSERT, UPDATE, DELETE,
INSERT, INTO, SET, ORDER, BY, ASC, DESC, LIMIT, OFFSET
```

如需使用保留字，请用双引号括起：
```sql
CREATE TABLE "order" ("select" VARCHAR, PRIMARY KEY("select"));
```
