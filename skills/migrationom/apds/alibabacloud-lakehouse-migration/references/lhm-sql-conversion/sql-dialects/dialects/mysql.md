# MySQL

**分类**: 传统关系型数据库
**文件数**: 51 个 SQL 文件
**总行数**: 8956 行

> **关键人物**：[Monty Widenius](../docs/people/monty-widenius.md)（MySQL 创始人, MariaDB 创始人）

## 概述与定位

MySQL 是全球最流行的开源关系型数据库，Web 应用的事实标准后端。从 LAMP 时代起，它就占据了互联网数据库的统治地位。MySQL 的核心竞争力不是功能最全，而是**上手最快、生态最广、读性能极强**。绝大多数 Web 开发者的第一个数据库就是 MySQL，这决定了它的设计哲学：宁可牺牲严格性，也要降低入门门槛。

在定位光谱上，MySQL 处于 SQLite（嵌入式）和 Oracle（企业级）之间：它是第一个让"免费 + 足够好"成为现实的服务端数据库。即使在 PostgreSQL 近年强势崛起后，MySQL 仍然在高并发 OLTP（电商、社交、游戏）场景中保持优势，尤其在中国互联网公司中占有率压倒性领先。

## 历史与演进

- **1995**: Monty Widenius 和 David Axmark 发布 MySQL 1.0，名字来源于 Monty 的女儿 My
- **2000**: 采用 GPL 双许可模式，奠定开源商业化先河
- **2005**: MySQL 5.0 引入存储过程、触发器、视图，开始追赶企业级功能
- **2008**: Sun Microsystems 以 10 亿美元收购 MySQL AB
- **2010**: Oracle 收购 Sun，社区恐慌，Monty 分叉创建 MariaDB
- **2013**: MySQL 5.6 引入 GTID 复制、全文索引（InnoDB）、EXPLAIN FORMAT=JSON
- **2016**: MySQL 5.7 引入 JSON 类型、Generated Columns、Group Replication
- **2018**: MySQL 8.0 — 里程碑版本：CTE、窗口函数、原子 DDL、角色、降序索引、不可见索引
- **2023**: MySQL 8.1+ 进入 Innovation Release 模式，与 LTS 并行
- **2024-2025**: MySQL 9.x 继续迭代，VECTOR 类型实验性支持

MySQL 的版本历史有一个显著特点：**功能追赶周期长**。窗口函数（SQL:2003 标准）直到 2018 年 8.0 才加入，比 PostgreSQL 晚了 7 年，比 Oracle 晚了 15 年。

## 核心设计思路

**可插拔存储引擎架构**是 MySQL 最独特的设计决策。SQL 解析层与存储层彻底分离，通过 Handler API 对接不同引擎：
- **InnoDB**（默认）：事务、行锁、MVCC、崩溃恢复 — 几乎等于"MySQL 本身"
- **MyISAM**（遗留）：表锁、无事务、全文索引先驱 — 2024 年已无正当使用理由
- **MEMORY**：纯内存哈希/B-tree，临时结果集处理
- **NDB Cluster**：分布式存储，MySQL Cluster 专用

这套架构在理论上很优雅，但实际上 InnoDB 已经"赢者通吃"。8.0 后系统表也迁入 InnoDB，MyISAM 成为纯遗留。

**宽松类型转换**：MySQL 默认允许隐式转换（字符串→数字、超范围截断），这在严格模式关闭时会静默丢失数据。这是"易用性优先"的典型体现，也是无数线上 Bug 的根源。

**user@host 权限模型**：权限绑定到 `'user'@'host'` 对而非单独用户，同一用户名从不同主机连接可以有不同权限。这在多数据中心场景有用，但概念上比其他数据库复杂。

## 独特特色（其他引擎没有的）

- **`ENGINE = xxx` 子句**：建表时指定存储引擎，全行业独此一家
- **`ON UPDATE CURRENT_TIMESTAMP`**：列级自动更新时间戳，声明式解决"最后修改时间"需求
- **`AUTO_INCREMENT`**：最简单的自增主键实现，无需单独的 SEQUENCE 对象
- **`GROUP_CONCAT()`**：行转列聚合函数，比标准 `LISTAGG` 更早出现，深入人心
- **`REPLACE INTO`**：先删后插的 UPSERT 变体（会触发 DELETE 触发器，慎用）
- **`INSERT ... SET col=val`**：用赋值语法代替 VALUES 列表，可读性更好
- **`INSERT ... ON DUPLICATE KEY UPDATE`**：真正的 UPSERT，比 `REPLACE` 更安全
- **`LAST_INSERT_ID()`**：连接级别的自增 ID 获取，无竞态
- **`STRAIGHT_JOIN`**：强制优化器按书写顺序连接，调优利器
- **多值 INSERT（早期支持）**：`INSERT INTO t VALUES (1,'a'), (2,'b')` — MySQL 很早就支持批量插入

## 已知的设计不足与历史包袱

- **`utf8` 不是 UTF-8**：MySQL 的 `utf8` 字符集只支持 3 字节（BMP），存不了 emoji。必须用 `utf8mb4`。这是 MySQL 历史上最臭名昭著的设计失误，至今仍在困扰迁移项目
- **CHECK 约束是摆设（8.0.16 前）**：语法接受但不执行，静默忽略。直到 8.0.16 才真正生效
- **不支持 FULL OUTER JOIN**：至今不支持，需要 `UNION` 模拟
- **DDL 隐式提交**：`CREATE TABLE`、`ALTER TABLE` 会自动提交当前事务，无法回滚 DDL
- **`ONLY_FULL_GROUP_BY` 曾默认关闭**：允许 SELECT 非聚合列不出现在 GROUP BY 中，结果不确定。5.7+ 才默认开启
- **不支持物化视图**：需要手工维护或用第三方方案
- **存储过程弱于 PL/SQL**：无 Package、无自治事务、调试困难
- **MERGE 语句不支持**：标准 SQL MERGE 在 MySQL 中用 `INSERT ... ON DUPLICATE KEY UPDATE` 替代
- **隐式类型转换**：`WHERE varchar_col = 123` 会导致全表扫描（索引失效），这是最常见的性能陷阱
- **Online DDL 限制**：虽然 8.0 改进很大，但部分 ALTER 仍需要拷贝表

## 兼容生态

MySQL 协议和 SQL 方言是数据库行业被兼容最多的目标：
- **TiDB**（PingCAP）：分布式 NewSQL，MySQL 协议兼容，目标替代分库分表
- **OceanBase**（蚂蚁）：MySQL 模式 + Oracle 模式双兼容
- **PolarDB**（阿里云）：MySQL 兼容的云原生数据库，计算存储分离
- **TDSQL**（腾讯）：金融级分布式 MySQL 兼容数据库
- **StarRocks / Doris**：OLAP 引擎，使用 MySQL 协议作为查询入口
- **MariaDB**：直接分叉，高度兼容但已在 10.6+ 出现不可忽略的差异
- **Vitess**（YouTube/PlanetScale）：MySQL 分片中间件

这个生态说明一个事实：**兼容 MySQL 是新数据库获取用户的最快路径**。

## 对引擎开发者的参考价值

- **写入路径**：InnoDB 的 Change Buffer（延迟二级索引更新）、redo log（WAL）+ undo log（MVCC 回滚）的双日志架构是教科书级设计
- **MVCC 实现**：基于 Read View 的快照读算法 — 每个事务维护一个活跃事务 ID 列表，判断行版本可见性。与 PostgreSQL 的元组版本化形成鲜明对比
- **间隙锁（Gap Lock）**：InnoDB 在 RR 隔离级别下使用间隙锁防止幻读，这是一个独特的并发控制策略，带来了特有的死锁模式
- **Buffer Pool 管理**：LRU 变体（young/old 分区）防止全表扫描冲刷热数据
- **Binlog 复制**：基于逻辑日志的主从复制架构，Statement/Row/Mixed 三种格式各有取舍
- **索引组织表**：InnoDB 的聚簇索引结构（数据按主键物理排序）与堆表组织（PostgreSQL）的对比，是存储引擎设计的核心抉择

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/mysql.md) | **ENGINE 可插拔架构是 MySQL 独有设计**——InnoDB 已成为唯一合理选择（8.0 系统表迁入 InnoDB），但 ENGINE 子句仍是全行业独此一家的 DDL 语法。AUTO_INCREMENT 自增最简实现（对比 PG 的 SERIAL/IDENTITY、Oracle 的 SEQUENCE）。`utf8` 只支持 3 字节不含 emoji 是历史最大坑，必须用 `utf8mb4`。 |
| [改表](../ddl/alter-table/mysql.md) | **Online DDL 三种算法（INSTANT/INPLACE/COPY）是 8.0 的核心改进**——INSTANT ADD COLUMN 毫秒级完成（对比 PG 11 前需重写全表）。但部分 ALTER 仍需 COPY 表，生产环境常用 pt-osc/gh-ost 第三方工具规避锁。DDL 隐式提交事务——不可回滚（对比 PG 的 DDL 事务性可回滚）。 |
| [索引](../ddl/indexes/mysql.md) | **InnoDB 聚簇索引是核心设计**——数据按主键物理排序存储（对比 PG 的堆表组织），主键查询极快但二级索引需"回表"读取完整行。8.0 新增函数索引和不可见索引（INVISIBLE INDEX 用于安全测试删除索引的影响）。无 GiST/GIN/BRIN 等高级索引框架（PG 独有）。 |
| [约束](../ddl/constraints/mysql.md) | **CHECK 约束 8.0.16 前是历史笑话**——语法接受但完全不执行，静默忽略。8.0.16+ 才真正生效（对比 PG/Oracle 始终强制执行）。外键在 InnoDB 中完整支持但有性能开销，高并发互联网场景常在应用层保证参照完整性而非依赖 FK。 |
| [视图](../ddl/views/mysql.md) | **MERGE/TEMPTABLE 两种算法决定性能**——MERGE 将视图条件合并到外层查询（高效），TEMPTABLE 先物化视图结果再查询（慢）。无物化视图（对比 PG REFRESH MATERIALIZED VIEW、Oracle Fast Refresh+Query Rewrite），需手工维护汇总表或用第三方方案。 |
| [序列与自增](../ddl/sequences/mysql.md) | **AUTO_INCREMENT 是最简自增实现**——无需单独的 SEQUENCE 对象（对比 PG/Oracle/MariaDB 均有独立 SEQUENCE）。innodb_autoinc_lock_mode 三种模式影响高并发插入性能：0=传统锁、1=连续（默认）、2=交错（binlog 安全需 ROW 格式）。8.0 修复了重启后自增值回退的经典 Bug。 |
| [数据库/Schema/用户](../ddl/users-databases/mysql.md) | **user@host 双维度权限模型是 MySQL 独有设计**——同一用户名从不同主机连接可有不同权限，比其他数据库的纯用户模型概念更复杂。8.0 引入角色（ROLE）简化权限管理（对比 PG/Oracle 早已支持）。Database=Schema 一级命名空间（对比 PG 的 Database.Schema 二级、BigQuery 的 Project.Dataset 三级）。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/mysql.md) | **PREPARE/EXECUTE 是 MySQL 动态 SQL 的唯一方式**——存储过程内可用但语法冗长（对比 Oracle 的 EXECUTE IMMEDIATE 更简洁）。无匿名块（对比 PG 的 DO $$ ... $$、Oracle 的 DECLARE/BEGIN）。动态 SQL 的绑定变量通过 `?` 占位符实现（对比 PG 的 `$1`）。 |
| [错误处理](../advanced/error-handling/mysql.md) | **DECLARE HANDLER (CONTINUE/EXIT) 是 MySQL 的过程式错误处理**——CONTINUE 处理后继续执行、EXIT 处理后退出块。功能远弱于 Oracle 的命名异常/RAISE_APPLICATION_ERROR 和 PG 的 EXCEPTION WHEN 块。无 SQLSTATE 精细分类（对比 PG 的标准错误码体系和 GET STACKED DIAGNOSTICS）。 |
| [执行计划](../advanced/explain/mysql.md) | **EXPLAIN ANALYZE（8.0.18+）是里程碑改进**——实际执行查询并显示真实行数和耗时（之前只有估算行数）。支持 JSON 和 TREE 格式输出。对比 PG 的 EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) 功能接近，但 MySQL 缺少 pg_stat_statements 级别的历史查询统计。 |
| [锁机制](../advanced/locking/mysql.md) | **InnoDB 的间隙锁（Gap Lock）是 RR 隔离级别下防幻读的独特方案**——锁定索引记录之间的"间隙"，这带来了 MySQL 特有的死锁模式。Next-Key Lock = 行锁 + 间隙锁。对比 PG 使用 SSI（Serializable Snapshot Isolation）无锁防幻读，MySQL 的方案锁冲突更频繁但实现更成熟。 |
| [分区](../advanced/partitioning/mysql.md) | **分区键必须包含在主键/唯一索引中是 MySQL 最大的分区限制**——无法按日期分区同时保持 ID 唯一（对比 PG/Oracle 无此限制）。支持 RANGE/LIST/HASH/KEY 四种分区方式。分区数上限约 8192。对比 BigQuery/Snowflake 的自动分区裁剪，MySQL 需手动管理分区。 |
| [权限](../advanced/permissions/mysql.md) | **user@host 模型是 MySQL 独有的双维度权限体系**——同一用户名从 localhost 和远程有不同权限。8.0 引入 ROLE 简化管理（对比 PG/Oracle 早已支持），Partial Revokes 允许在全局 GRANT 基础上撤销特定数据库权限。无行级安全策略 RLS（对比 PG 的 ROW LEVEL SECURITY 和 BigQuery 的 Row Access Policy）。 |
| [存储过程](../advanced/stored-procedures/mysql.md) | **DELIMITER 变更是 MySQL 存储过程的最大尴尬**——因为 SQL 层不识别过程体内的分号。无 Package（对比 Oracle PL/SQL 的包封装）、无匿名块（对比 PG 的 DO 块）、无 BULK COLLECT/FORALL 批量绑定。过程化能力在主流数据库中最弱，调试困难，复杂逻辑建议放在应用层。 |
| [临时表](../advanced/temp-tables/mysql.md) | **CREATE TEMPORARY TABLE 会话级可见**——可选 MEMORY 或 InnoDB 引擎。MEMORY 引擎表存在内存中速度快但不支持 BLOB/TEXT 且受 max_heap_table_size 限制。对比 PG 的 ON COMMIT DROP/DELETE ROWS 选项和 Oracle 的 GTT（全局临时表需预定义结构），MySQL 临时表使用简单但功能较少。 |
| [事务](../advanced/transactions/mysql.md) | **InnoDB MVCC 基于 Read View 实现快照读**——与 PG 的元组版本化形成鲜明对比（MySQL 用 Undo Log 存旧版本，无需 VACUUM）。默认 REPEATABLE READ（历史原因，PG/Oracle 默认 READ COMMITTED）。DDL 隐式提交事务——CREATE/ALTER/DROP 无法回滚（对比 PG 的 DDL 事务性是最大优势之一）。 |
| [触发器](../advanced/triggers/mysql.md) | **只支持行级 FOR EACH ROW 触发器**——无语句级触发器（对比 PG/Oracle 支持 FOR EACH STATEMENT），无 INSTEAD OF 触发器（对比 SQL Server/PG），无 DDL 触发器/事件触发器（对比 PG 9.3+ 的 Event Trigger 和 Oracle 的 DDL Trigger）。每个表每个事件只能有一个触发器（8.0 前限制，8.0 允许多个）。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/mysql.md) | **DELETE + LIMIT 是 MySQL 独有的安全删除方式**——可分批删除避免长事务锁表。TRUNCATE 不可回滚（DDL 隐式提交）且不触发触发器。对比 PG 的 DELETE...RETURNING（返回被删行）和 Oracle 的 Flashback Table（误删恢复），MySQL 缺少这些安全网。 |
| [插入](../dml/insert/mysql.md) | **INSERT...SET col=val 是 MySQL 独有的赋值式插入语法**——比 VALUES 列表可读性更好。LOAD DATA INFILE 是批量导入的最快方式（比 INSERT 快 20 倍以上）。Multi-row VALUES 早期即支持。对比 PG 的 COPY 和 Oracle 的 INSERT ALL 多表插入（独有），MySQL 的批量加载方案较单一。 |
| [更新](../dml/update/mysql.md) | **多表 UPDATE JOIN 是 MySQL 的直觉式更新语法**——`UPDATE t1 JOIN t2 ON... SET t1.col=t2.col`（对比 PG 的 UPDATE...FROM 语法）。SET 子句从左到右求值，后面的列可引用前面刚赋的值。对比 PG 的 UPDATE...RETURNING（返回更新后行），MySQL 无法在一条语句中获取更新结果。 |
| [Upsert](../dml/upsert/mysql.md) | **ON DUPLICATE KEY UPDATE 是 MySQL 的推荐 UPSERT 方案**——基于唯一索引冲突触发更新（对比 PG 的 ON CONFLICT 更灵活可指定约束名）。REPLACE INTO 先删后插——会触发 DELETE 触发器、重置自增 ID、级联删除 FK，生产环境慎用。不支持标准 MERGE 语句（对比 Oracle/SQL Server/PG 15+）。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/mysql.md) | **GROUP_CONCAT 默认 1024 字节截断是常见陷阱**——需 `SET group_concat_max_len` 调大。无 GROUPING SETS/CUBE/ROLLUP（8.0+ 有限支持）、无 FILTER 子句（对比 PG 的 `COUNT(*) FILTER(WHERE...)` 优雅条件聚合）。不支持 LISTAGG（标准函数，Oracle/Snowflake 支持）。 |
| [条件函数](../functions/conditional/mysql.md) | **IF(cond, true_val, false_val) 是 MySQL 独有的函数式条件**——比 CASE WHEN 简洁但非标准。`\|\|` 是逻辑 OR 而非字符串拼接（对比 PG/Oracle/SQLite 中 `\|\|` 是拼接），这是**最大的方言陷阱之一**——从 PG 迁移到 MySQL 的 SQL 经常因此出错。需用 CONCAT() 替代。 |
| [日期函数](../functions/date-functions/mysql.md) | **DATE_FORMAT 使用 % 格式符**——`DATE_FORMAT(dt, '%Y-%m-%d')`（对比 PG 的 to_char、Oracle 的 TO_DATE 格式串各不相同）。NOW() 返回语句开始时间（非事务开始时间）。无 INTERVAL 类型（对比 PG 的丰富 INTERVAL 运算），日期加减用 DATE_ADD/DATE_SUB 函数而非运算符。 |
| [数学函数](../functions/math-functions/mysql.md) | **数学函数库完整**，GREATEST/LEAST 内置（对比 SQL Server 2022 才引入）。除零返回 NULL 而非报错（对比 PG/Oracle 报错）。UNSIGNED 整数类型正在废弃中——8.0 不推荐 UNSIGNED BIGINT 的运算，因为减法结果可能溢出。 |
| [字符串函数](../functions/string-functions/mysql.md) | **CONCAT 中任何参数为 NULL 则整体返回 NULL**——这是 MySQL 的标准行为但极易踩坑（对比 Oracle 中 NULL 在拼接中被忽略）。`\|\|` 不是拼接运算符是逻辑 OR（对比 PG/Oracle/SQLite 中 `\|\|` 是拼接），这是跨方言迁移最大的差异之一。CONCAT_WS 可安全跳过 NULL（独有语法糖）。 |
| [类型转换](../functions/type-conversion/mysql.md) | **隐式类型转换极宽松是 MySQL 的双刃剑**——`WHERE varchar_col = 123` 会将 varchar_col 隐式转为数字导致全表扫描（索引失效），这是最常见的性能陷阱。无 TRY_CAST 安全转换（对比 SQL Server 的 TRY_CAST、Snowflake 的 TRY_CAST、BigQuery 的 SAFE_CAST）。8.0 严格模式缩小了隐式转换范围。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/mysql.md) | **8.0 才引入 CTE（比 PG/Oracle/SQL Server 晚了多年）**。早期版本 CTE 总是物化（无法优化为内联），8.0.14+ 优化器可选择内联。递归 CTE 仅支持 UNION ALL（不支持 UNION DISTINCT，对比 PG 两者都支持）。无 PG 的可写 CTE（INSERT/UPDATE/DELETE in WITH）。 |
| [全文搜索](../query/full-text-search/mysql.md) | **InnoDB FULLTEXT（5.6+）内置全文搜索**——支持 BOOLEAN MODE（AND/OR/NOT）和 NATURAL LANGUAGE MODE。ngram 解析器支持中文/日文/韩文分词（对比 PG 的 tsvector+GIN 更灵活可扩展）。无 BM25 排序（对比 DuckDB FTS5、SQLite FTS5），相关性排序算法较基础。 |
| [连接查询](../query/joins/mysql.md) | **不支持 FULL OUTER JOIN 是 MySQL 至今的缺陷**——需用 LEFT JOIN + RIGHT JOIN + UNION 模拟。8.0.18+ 引入 Hash Join（之前仅 Nested Loop）大幅改善大表连接性能。无 LATERAL JOIN（对比 PG 9.3+、SQL Server 的 CROSS APPLY）。无 NATURAL FULL OUTER JOIN（对比 MariaDB 支持）。 |
| [分页](../query/pagination/mysql.md) | **LIMIT/OFFSET 是 MySQL 最早普及的分页语法**（PG 也支持，Oracle 12c 前需 ROWNUM 嵌套）。深分页 O(offset) 性能问题严重——LIMIT 100000, 10 仍需扫描前 10 万行。优化方案：Keyset 分页（WHERE id > last_id ORDER BY id LIMIT 10）或延迟关联（先查主键再回表）。 |
| [行列转换](../query/pivot-unpivot/mysql.md) | **无原生 PIVOT/UNPIVOT 语法**——必须手写 CASE + GROUP BY 模拟（对比 Oracle 11g/SQL Server/BigQuery/Snowflake/DuckDB 均有原生 PIVOT）。动态 PIVOT 更复杂，需用 PREPARE/EXECUTE 拼接动态 SQL。这是 MySQL 在分析查询上的明显短板。 |
| [集合操作](../query/set-operations/mysql.md) | **INTERSECT/EXCEPT 直到 8.0.31 才加入**——此前 MySQL 是唯一不支持 INTERSECT 的主流数据库（对比 PG/Oracle/SQL Server/MariaDB 10.3+ 早已支持）。UNION ALL/DISTINCT 完整。对比 Oracle 使用 MINUS 而非 EXCEPT（非标准命名）。 |
| [子查询](../query/subquery/mysql.md) | **5.x 子查询性能噩梦已在 8.0 修复**——早期 MySQL 将 IN 子查询转为 EXISTS 关联子查询导致灾难性性能。8.0 的 semijoin 优化（FirstMatch/LooseScan/Materialization/DuplicateWeedout）彻底解决了这一历史问题。对比 PG 的子查询优化器成熟度一直领先。 |
| [窗口函数](../query/window-functions/mysql.md) | **8.0 才支持窗口函数（比 PG 8.4 晚 9 年，比 Oracle 8i 晚 15 年）**——ROW_NUMBER/RANK/DENSE_RANK/NTILE/LAG/LEAD/FIRST_VALUE/LAST_VALUE 完整。无 QUALIFY 子句（对比 BigQuery/Snowflake/DuckDB 的 QUALIFY 无需子查询包装）。无 GROUPS 帧类型（对比 PG 11+）。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/mysql.md) | **无 generate_series 是 MySQL 日期填充的最大障碍**——需递归 CTE（8.0+）或预建数字辅助表模拟。对比 PG 的 `generate_series(date,date,interval)` 原生支持和 BigQuery 的 GENERATE_DATE_ARRAY，MySQL 方案最冗长。MariaDB 的 seq_1_to_N 序列引擎是更优替代。 |
| [去重](../scenarios/deduplication/mysql.md) | **ROW_NUMBER()+CTE 是 8.0+ 的标准去重写法**——`DELETE FROM t WHERE id IN (SELECT id FROM (SELECT id, ROW_NUMBER() OVER(PARTITION BY key ORDER BY ts DESC) rn FROM t) WHERE rn > 1)`。5.x 需用 DELETE+JOIN 自连接。对比 PG 的 DISTINCT ON 一行搞定去重、BigQuery/DuckDB 的 QUALIFY 无需嵌套。 |
| [区间检测](../scenarios/gap-detection/mysql.md) | **LAG/LEAD 窗口函数（8.0+）是间隙检测的标准方案**——比较相邻行时间差即可。5.x 时代需用用户变量 `@prev` 模拟窗口函数（可读性极差且有不确定行为风险）。对比 PG 的 generate_series 填充+LEFT JOIN 方案更直观。 |
| [层级查询](../scenarios/hierarchical-query/mysql.md) | **递归 CTE（8.0+）是 MySQL 层级查询的唯一方案**——无 Oracle 的 CONNECT BY（更简洁的原创语法）。5.x 时代只能用多次自连接（深度固定）或应用层迭代。对比 PG 的 ltree 扩展提供路径运算、SAP HANA 的 HIERARCHY 函数原生层级导航。 |
| [JSON 展开](../scenarios/json-flatten/mysql.md) | **JSON_TABLE（8.0.4+）是 MySQL JSON 处理的亮点**——将 JSON 数据转为关系表，功能接近 SQL 标准（对比 Oracle 12c 最早支持 JSON_TABLE）。对比 PG 的 JSONB+GIN 索引（最强 JSON 实现）和 Snowflake 的 LATERAL FLATTEN（独有语法），MySQL 的 JSON_TABLE 功能完整但 JSON 索引支持较弱。 |
| [迁移速查](../scenarios/migration-cheatsheet/mysql.md) | **迁移核心陷阱：隐式类型转换（索引失效）、utf8mb4 字符集、GROUP BY 语义差异（ONLY_FULL_GROUP_BY）、`\|\|` 是 OR 非拼接、DDL 隐式提交不可回滚、无 FULL OUTER JOIN**。从 PG 迁入需注意类型严格度差异；从 Oracle 迁入注意 ''=NULL 差异和 PL/SQL 到存储过程的重写。 |
| [TopN](../scenarios/ranking-top-n/mysql.md) | **ROW_NUMBER()+子查询是 8.0+ 的 TopN 标准写法**——5.x 需用用户变量 `@rank` 模拟排名（有不确定性）。无 QUALIFY 子句（对比 BigQuery/Snowflake/DuckDB 一行搞定分组 TopN）。无 FETCH FIRST WITH TIES（对比 PG 13+/Oracle 12c+ 包含并列行）。 |
| [累计求和](../scenarios/running-total/mysql.md) | **SUM() OVER(ORDER BY ...) 是 8.0+ 的标准累计求和**——默认帧 RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW。5.x 时代靠用户变量 `@running := @running + amount` 模拟（有不确定求值顺序风险）。对比 PG 8.4 起即支持窗口函数，MySQL 在此领域晚到十年。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/mysql.md) | **无 MERGE 语句是 MySQL 处理 SCD 的最大短板**——需用 ON DUPLICATE KEY UPDATE 模拟 Type 1 SCD、INSERT...ON DUPLICATE KEY+触发器模拟 Type 2 SCD。对比 Oracle 的 MERGE 多分支（首创 9i）、BigQuery/Snowflake 的 MERGE WHEN NOT MATCHED BY SOURCE 功能更完善。 |
| [字符串拆分](../scenarios/string-split-to-rows/mysql.md) | **无原生字符串拆分为行的函数**——需递归 CTE+SUBSTRING_INDEX 逐段提取（8.0+ 方案），或 JSON_TABLE 将逗号分隔转 JSON 数组再展开。对比 PG 14 的 string_to_table 一行搞定、SQL Server 的 STRING_SPLIT、ClickHouse 的 splitByChar+arrayJoin，MySQL 方案最繁琐。 |
| [窗口分析](../scenarios/window-analytics/mysql.md) | **8.0 提供完整窗口函数集**——ROW_NUMBER/RANK/DENSE_RANK/NTILE/LAG/LEAD/FIRST_VALUE/LAST_VALUE/NTH_VALUE 以及完整的 ROWS/RANGE 帧子句。无 GROUPS 帧类型（PG 11+ 独有）。无 QUALIFY 子句。无 FILTER 子句（PG 独有的条件聚合语法）。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/mysql.md) | **无原生 ARRAY/MAP/STRUCT 类型**——只能用 JSON 类型模拟复合结构（对比 PG 的原生 ARRAY+运算符、ClickHouse 的 Array/Map/Tuple、BigQuery 的 STRUCT/ARRAY 一等公民）。JSON 列上可建多值索引（8.0.17+），但查询语法不如原生复合类型直观。 |
| [日期时间](../types/datetime/mysql.md) | **DATETIME vs TIMESTAMP 的选择是经典困惑**——TIMESTAMP 有 2038 年溢出问题（32 位 Unix 时间戳）且存储为 UTC 自动转换时区，DATETIME 无时区转换且范围到 9999 年。微秒精度需显式指定 `DATETIME(6)`（默认秒级）。对比 PG 的 TIMESTAMPTZ（无 2038 问题）和 BigQuery 的四种时间类型严格区分。 |
| [JSON](../types/json/mysql.md) | **JSON 类型内部以二进制格式存储（非文本）**——查询时无需重新解析，性能优于 MariaDB 的 LONGTEXT 别名。8.0.17+ 引入多值索引（Multi-Valued Index）可索引 JSON 数组元素。Partial Update 优化避免全量重写 JSON 文档。对比 PG 的 JSONB+GIN 索引（最强 JSON 实现）和 BigQuery 的 JSON 类型（2022+）。 |
| [数值类型](../types/numeric/mysql.md) | **UNSIGNED 整数类型正在废弃趋势中**——UNSIGNED BIGINT 减法可能溢出，8.0 不推荐使用。DECIMAL 使用 BCD（Binary-Coded Decimal）存储保证精确计算（对比 Oracle 的 NUMBER 万能类型、PG 的 NUMERIC 任意精度）。TINYINT-BIGINT 五种整数类型选择多（对比 BigQuery 只有 INT64 一种）。 |
| [字符串类型](../types/string/mysql.md) | **utf8 不是 UTF-8 是 MySQL 历史最大坑**——`utf8` 只支持 3 字节（BMP 平面），存不了 emoji/生僻字，必须用 `utf8mb4`（真正的 UTF-8）。TEXT 类型有索引限制（需指定前缀长度）且不能设默认值（5.7 前）。对比 PG 的 TEXT=VARCHAR 无性能差异、BigQuery 的 STRING 无长度限制极简设计。 |
