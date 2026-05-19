# Lindorm SQL 使用注意事项

## 目录

- [与 MySQL 的兼容性差异](#与-mysql-的兼容性差异)
- [查询结果不符合预期的排查](#查询结果不符合预期的排查)
- [SQL 使用注意事项](#sql-使用注意事项)
- [HASH 打散注意事项](#hash-打散注意事项)
- [冷热分离注意事项](#冷热分离注意事项)
- [Compaction 与存储管理](#compaction-与存储管理)

---

## 与 MySQL 的兼容性差异

Lindorm SQL 兼容 MySQL 5.7/8.0 的部分功能和语法，但由于产品架构不同，部分语法或功能并没有被完全支持。

### 词法要素差异

| 项目 | Lindorm SQL | MySQL |
|------|-------------|-------|
| 大小写敏感 | 数据库对象标识符严格区分大小写 | 可配置 |
| 标识符引用 | 必须用反引号 \` 引用 | 支持多种方式 |
| 字符串常量 | 只能用单引号 ' | 支持单引号和双引号 |

### 不支持的数据类型

- BIT 类型
- MEDIUMINT 类型
- REAL 类型
- 各种 TEXT 类型
- DATETIME 类型
- 除 BIGINT UNSIGNED 以外的 UNSIGNED 类型

> 对于 TINYINT、INTEGER、BIGINT 等整型类型，不支持指定具体的长度限制。

### 事务支持

Lindorm 不支持多行事务（即一次读写多行数据的事务性）。

### INSERT 语义差异

Lindorm SQL 的 INSERT 本质是 UPSERT，对于主键相同的数据会直接覆盖写入语句中涉及到的字段/列。

> 传统数据库中基于全主键的等值过滤条件进行 UPDATE 的语句建议改成使用 INSERT 语句，来取得更好的性能。

**INSERT 限制**：
- INSERT 语句需要显式指定待写入的表的字段列表
- 字段列表中必须至少指定一个非主键列

### DELETE/UPDATE 限制

DELETE 和 UPDATE 语句必须指定 WHERE 条件，且需要 WHERE 过滤条件能够明确指定所有主键的等值条件精确定位到一条数据。

> 如果 WHERE 过滤条件可以定位到一批数据，默认无法执行。若需要批量删除/更新，需联系 Lindorm 技术支持配置系统参数启用。

**批量操作注意事项**：
- 批量删除/更新时，操作的原子性无法保证
- 批量操作是先查后删/更新，请尽可能保证 WHERE 条件能够高效命中索引
- 大量删除操作会影响某些查询场景的性能，可以设置 TTL 的情况下优先通过 TTL 让数据过期

### SELECT 限制

- 不支持 JOIN（INNER JOIN / LEFT JOIN / RIGHT JOIN 均不支持，报错 `JOIN is not allowed in Lindorm SQL`）
- 不支持 UNION、UNION ALL
- 不支持 INTERSECT、MINUS/EXCEPT（MINUS 报语法错误；INTERSECT/EXCEPT 语法不报错但运行时触发低效查询拦截，实际不可用）

### 子查询支持

Lindorm SQL 对子查询提供有限支持，具体取决于子查询形式和是否创建索引：

| 子查询形式 | 无索引 | 有二级索引 | 说明 |
|-----------|--------|-----------|------|
| 派生表（FROM 子句） | ✅ 支持 | ✅ 支持 | `SELECT * FROM (SELECT ...) AS t` |
| 派生表 + WHERE | ✅ 支持 | ✅ 支持 | 外层 WHERE 过滤派生表结果 |
| 多层嵌套派生表 | ✅ 支持 | ✅ 支持 | 多层 FROM 子查询嵌套 |
| 标量子查询（SELECT 列） | ❌ 低效拦截 | ✅ 支持 | `(SELECT COUNT(*) FROM ...) AS cnt` |
| WHERE IN 子查询 | ❌ 低效拦截 | ✅ 支持 | 需子查询中的过滤列有索引 |
| WHERE EXISTS 子查询 | ❌ 低效拦截 | ✅ 支持 | 需子查询中的过滤列有索引 |

> **关键说明**：WHERE IN / EXISTS / 标量子查询的失败不是语法不支持，而是因为无索引导致全表扫描被**低效查询拦截**机制拒绝。创建二级索引后即可正常执行。

**官方文档**：https://help.aliyun.com/zh/lindorm/user-guide/compatibility-comparison-between-lindorm-sql-and-mysql

### 窗口函数支持

⚠️ **有限支持**：官方兼容性文档标注窗口函数为"暂不支持"，语法不报错但可能存在**正确性或稳定性风险**（服务端计算开销较大）。实测 ROW_NUMBER/RANK/DENSE_RANK/LEAD/SUM OVER/AVG OVER 在当前版本可正常执行，LAG 在低版本存在解析器 bug（`LAG(...) AS alias` 报错）。生产环境**谨慎使用**，建议优先用计算引擎（OLAP）处理窗口计算。

| 窗口函数 | 说明 | 示例 |
|---------|------|------|
| `ROW_NUMBER()` | 行号 | `ROW_NUMBER() OVER (PARTITION BY col ORDER BY col)` |
| `RANK()` | 排名（相同值同排名，跳号） | `RANK() OVER (ORDER BY col DESC)` |
| `DENSE_RANK()` | 排名（相同值同排名，不跳号） | `DENSE_RANK() OVER (ORDER BY col)` |
| `SUM() OVER` | 累计求和 | `SUM(amount) OVER (PARTITION BY user_id)` |
| `AVG() OVER` | 累计平均 | `AVG(score) OVER (PARTITION BY class_id)` |
| `LEAD(col, offset)` | 后续行 | `LEAD(amount, 1) OVER (ORDER BY id)` |
| `LAG(col, offset)` | 前置行 | `LAG(amount, 1) OVER (ORDER BY id)` |

### 低效查询拦截

Lindorm 默认会拦截可能导致全表扫描的查询，报错 `DoNotRetryIOException: Detect inefficient query`。

**触发场景**：WHERE 条件中的列没有索引，且无法通过主键定位数据。

**解决方案**：

1. **创建二级索引**（推荐）：对 WHERE 条件中的列创建二级索引
   ```sql
   CREATE INDEX idx_region ON orders (region) INCLUDE (user_name, amount);
   -- 之后 WHERE region = '华东' 即可走索引
   ```
2. **使用 HINT 允许全表扫描**（慎用，可能影响性能）：
   ```sql
   SELECT /*+ _l_allow_filtering_ */ * FROM orders WHERE region = '华东';
   ```
3. **添加主键范围条件**：
   ```sql
   SELECT * FROM orders WHERE id >= 1 AND id < 100 AND region = '华东';
   ```

> **索引生效时间**：建索引后需等待构建完成才能生效。二级索引(KV)约 10 秒，搜索索引(SEARCH)约 30 秒。立即查询可能仍报低效查询错误。

> 索引类型选择：二级索引（KV）支持等值/范围/前缀模糊查询；后缀模糊（`%xxx`）需搜索索引（SEARCH）。详见 [table-design.md](table-design.md)。

### LIKE 和范围查询

二级索引（KV）支持范围查询和 LIKE 前缀匹配：

| 查询类型 | 二级索引(KV) | 搜索索引(SEARCH) |
|---------|-------------|-----------------|
| 等值 `=` | ✅ | ✅ |
| IN | ✅ | ✅ |
| 范围 `> < >= <=` | ✅ | ✅ |
| BETWEEN | ✅ | ✅ |
| LIKE 前缀 `'xxx%'` | ✅ | ✅ |
| LIKE 单字符 `'xxx_'` | ✅ | ✅ |
| LIKE 后缀 `'%xxx'` | ❌ | ✅ |
| LIKE 包含 `'%xxx%'` | ❌ | ✅ |
| 多维查询 | ❌ | ✅ |

```sql
-- 二级索引：支持等值、范围、LIKE前缀
CREATE INDEX idx_amount ON orders (amount) INCLUDE (user_name, product);
-- 之后这些查询都能走索引：
-- WHERE amount = 3999
-- WHERE amount > 1000
-- WHERE amount BETWEEN 1000 AND 5000
-- WHERE product LIKE '手%'

-- 搜索索引：支持后缀模糊、多维查询、分词查询
-- ⚠️ 需先在控制台开通搜索索引功能，否则报 SERVER INTERNAL ERROR
CREATE INDEX idx_search USING SEARCH ON orders (region, product, amount);
-- 支持：WHERE product LIKE '%脑%'
-- 支持：WHERE region = '华东' AND amount > 1000
```

### 分词查询（MATCH AGAINST）

搜索索引支持分词查询，使用 `MATCH ... AGAINST` 语法：

```sql
-- 创建带分词器的搜索索引
CREATE INDEX idx_text USING SEARCH ON articles (
  content(type=text, analyzer=ik)
);

-- 分词查询：匹配包含"功能介绍"的记录
SELECT * FROM articles WHERE MATCH(content) AGAINST('功能介绍');
-- 会匹配包含"功能"、"介绍"或"功能介绍"的记录
```

**支持的分词器**：`standard`（默认）、`ik`（中文推荐）、`english`、`whitespace`、`comma`

> 详细说明见 [table-design.md](table-design.md#搜索索引开通条件)

### ALTER TABLE 限制

- 支持加列和删列，但不支持重命名列
- 不支持修改列定义（包括列类型、精度、默认值等）
- 不支持通过 ALTER TABLE 语句增减索引
- 不支持修改表的主键

### 其他不支持的语法

- RENAME TABLE
- REPLACE
- SELECT ... FOR SHARE
- 显式事务语法（START TRANSACTION, COMMIT, ROLLBACK）
- CREATE TABLE AS SELECT
- 表的导入/导出语法（IMPORT, LOAD）
- EXPLAIN ANALYZE
- FOREIGN KEY
- 唯一索引（UNIQUE INDEX）

---

## 查询结果不符合预期的排查

Lindorm 宽表引擎的存储模型是基于 LSM-Tree 实现的。数据写入是即时可见的，不会出现写入后过一段时间才可见的情况。如果查询结果不符合预期，请按以下原因排查。

### 1. 数据未正常写入或查询发起的时间在数据写入前

如果写入链路出现问题，可能导致写入延迟或无法正常写入数据。建议在查询条件中添加 HINT 参数，指定查询结果中返回数据写入的时间戳，根据该时间戳判断是否出现了查询先于写入的情况。

### 2. STRING 字段中含有非正常的停止符或不可见字符

如果 STRING 字段中包含不可见字符，可能造成查询结果不符合预期。

**排查方法**：使用范围查询确认是否存在类似问题，例如 `WHERE orderID > "1000" LIMIT 1`。

> Lindorm 不支持 STRING 字段的中间包含停止符（结尾有停止符是正常的）。

### 3. 查询条件中列名填写错误

- **列名大小写错误**：Lindorm 的列名是大小写敏感的
- **未指定列簇**：如果使用了多 family 功能，必须在查询条件中指定 family，例如 `WHERE meta:column1=xxx`

### 4. 表属性设置了 TTL，查询时数据已过期

TTL 的单位是秒（s），时间戳的单位为毫秒（ms）。

**常见问题**：
- 写入数据时指定了较早的时间戳，且该时间戳与当前时间的差值大于 TTL 设定值，可能在写入时就被清理掉
- 如果在时间戳的使用上未遵循时间语义，而是使用自定义的版本号（例如 1、2、3、4 这种比较小的数字），数据极易被过期清理
- 使用较大的自定义时间戳/版本号（如微秒或纳秒时间戳），可能造成数据无法正常过期清理

### 5. 设置了 Cell TTL，查询时数据已过期

Cell TTL 单位为毫秒（ms）。如果 KV 上设置了 Cell TTL，其过期时间为 `min{Cell 上设置的过期时间, 表属性上的过期时间}`。

### 6. 删除请求的时间戳设置不合理

删除请求支持设置时间戳/版本号，代表删除该行/该列在此时间/版本之前的数据。

- 如果删除请求的时间戳比数据写入的时间戳/版本号小，那么这行数据不会被删除
- 如果删除请求设置的时间戳/版本号较大，删除请求提交后将持续生效，后续写入的数据可能被立即删除

> SQL 访问方式不支持设置删除时间戳。

### 7. 表属性 VERSIONS 被设置为 0

VERSIONS 属性的值为 0 表示表中的数据不会保留，任何写入的数据都将被删除，无法查询。

**解决方案**：删除表并重新建表，或将 VERSIONS 属性修改为大于等于 1 的值。

### 8. 表属性为 IMMUTABLE 的表有更新

IMMUTABLE 表示该表仅支持整行写入（即一行的数据通过一条 UPSERT 语句写入），不可更新或删除。

---

## SQL 使用注意事项

### 动态列表 SELECT * 限制

开启动态列的表可能包含大量的动态列，且表的 Schema 定义不固定。对这类表进行全表扫描将会导致 IO 消耗严重。

**解决方案**：在 SELECT 语句中添加 LIMIT 子句，限制返回结果的数量，例如 `SELECT * FROM test LIMIT 10`。

### 常用表属性单位

| 属性 | 单位 | 说明 |
|------|------|------|
| TTL | 秒 (s) | 数据有效期 |
| COMPACTION_MAJOR_PERIOD | 毫秒 (ms) | Major Compaction 周期 |
| 时间戳 | 毫秒 (ms) | 数据版本时间 |
| Cell TTL | 毫秒 (ms) | 单个 KV 过期时间 |

---

## HASH 打散注意事项

主键 HASH 打散功能通过 HASH 函数将数据分散到不同的分片（Region），避免数据倾斜和负载不均等问题。

### DDL 限制

- HASH 函数表达式必须放在最前面
    - 错误：`PRIMARY KEY(p1, hash32(p1), p2)`
    - 正确：`PRIMARY KEY(hash32(p1), p1, p2)`
- 在主键列或索引中对某列使用 HASH 算法时，必须指定该列为主键列或索引列
- 已指定 HASH 算法的主键列不支持修改
- 使用主键 HASH 打散功能后，不支持使用 bulkload 方式导入数据

### DML 限制

**写入数据**：无需在 SQL 语句中添加 HASH 相关参数，系统自动生成并填充 HASH 值。

**查询数据**：
- 必须指定所有已使用 HASH 算法的主键列的值，否则系统无法计算 HASH 值，导致查询全表
- 对于使用了 HASH 算法的主键列，查询条件必须为等值查询，不支持范围查询

```sql
-- 推荐的使用方式
SELECT * FROM t1 WHERE p1=1 AND p2=1;

-- 不推荐：未指定主键列 p1 的值，会导致查询全表
SELECT * FROM t1 WHERE p2=1;

-- 错误：不支持 HASH 列的范围查询
SELECT * FROM t1 WHERE p2=1 AND p1>2 AND p1<8;
```

---

## 冷热分离注意事项

### 数据何时进入冷存储

Lindorm 通过 Compaction 机制异步将冷数据从热存储归档至冷存储：

- 系统触发时间默认为冷热分界线的一半
- 最小为 1 天
- 最大为 Major Compaction 周期的一半（默认 20 天）

例如：冷热分界线为 3 天，则默认 1.5 天自动触发一次 Compaction 归档任务。

### 手动触发 Compaction

可以通过 `major_compact 'tableName'` 手动触发 Compaction。

> `major_compact` 命令会加重 IO 负载，不建议频繁使用。

如果执行 Compaction 后数据还未进入冷存储，可能是数据还未写入磁盘，请先执行 flush 操作。

### 自定义时间列冷热分离

- 如果一行数据未写入自定义时间列，该行数据会被保留在热存储区，不会冷热分离
- 如果更新的冷数据不是自定义时间列，更新后的数据依旧是冷数据
- 如果更新的是自定义时间列中的数据，需要根据新写入的时间内容来重新划分冷热数据

### 按时间戳冷热分离

由于更新后的数据重新记录了时间戳，因此冷数据更新后变为热数据。

### HOT_ONLY 查询注意事项

查询语句可以通过设置 `HOT_ONLY` / `_l_hot_only_` 仅查询热数据。但由于数据归档至冷存储的操作是周期性触发的，部分冷数据可能会滞留在热存储，导致查询结果中包含冷数据。

**解决方案**：在查询条件中添加热数据时间范围：

```sql
SELECT /*+ _l_hot_only_(true), _l_ts_min_(1000), _l_ts_max_(2001) */ * FROM test WHERE p1>1;
```

### 索引表与主表冷数据不一致

主表和索引表的冷数据归档过程是独立的，且归档操作是周期性触发的，导致主表和索引表滞留在热存储的数据不一致，进而出现查询到的冷数据不一致的现象。

**解决方案**：在查询条件中添加热数据的时间范围。

### 开启冷热分离后立即触发 Compaction

当前时间减去最旧的文件的生成时间大于冷数据归档周期时，则会触发冷数据转存。

---

## Compaction 与存储管理

### Compaction 的作用

- 清理过期数据（TTL）
- 清理删除操作的遗留标记（deleteMarker）
- 归档冷热数据
- 压缩数据减少空间占用

### Compaction 自动触发周期

系统默认的自动触发周期为 20 天。在 TTL 场景下，默认周期为 `min(TTL 值, 20 天)`。

**修改触发周期**：

```sql
-- 将自动触发周期修改为 2 天（单位为毫秒）
ALTER TABLE <tableName> SET 'COMPACTION_MAJOR_PERIOD'='172800000';
```

### Compaction 对业务的影响

Compaction 操作处理数据时会消耗 CPU。CPU 资源充足时对业务没有太大影响，反而有助于提升读性能、释放存储空间。

**监控 Compaction 状态**：通过实例监控查看宽表引擎指标 > 集群负载 > Compaction 队列长度。如果该数值持续增长或始终持平，说明可能存在大量排队任务。

**优化建议**：
- 如果 CPU 利用率小于 40%，宽表 2.6.5 以上版本支持自动根据 load 调整参数，直接升级小版本即可
- 如果 CPU 利用率大于 40%，建议增加宽表引擎节点数量

### 已设置 TTL 但存储仍在上涨

通过实例监控查看 Compaction 队列长度，确认是否存在任务积压情况，如果积压较多就会出现数据清理滞后的现象。

如果队列无任务且读写负载较低，可以手动执行 Compaction 或调整 Major Compaction 周期。

### 磁盘容量上限处理

- 扩容热存储容量
- 通过 `DROP TABLE` 直接删除无用的表，立即释放存储空间
- 通过 `TRUNCATE TABLE` 清空表中数据，立即释放存储空间

> 请勿使用 DELETE 直接删除数据。Lindorm 的删除操作是直接写入删除标记（Delete Marker），等到下次触发 Compaction 操作才会被彻底清理。

### 磁盘容量上限后无法删除数据

磁盘达到容量上限后系统将禁止所有数据的写入，包括删除标记。删除标记无法写入将导致需删除的数据无法通过 Compaction 操作清理。

### 压缩算法和编码方式

可以将表的压缩算法 COMPRESSION 设置为 ZSTD，编码方式 DATA_BLOCK_ENCODING 设置为 INDEX，并执行 Major Compact 以减少存储空间。

```sql
ALTER TABLE <tablename> SET 'COMPRESSION' = 'ZSTD','DATA_BLOCK_ENCODING' = 'INDEX';
ALTER TABLE <tablename> COMPACT;
```

> 如果您是通过 SQL 方式创建的表，则默认已设置，无需重复设置。

