# PostgreSQL

**分类**: 传统关系型数据库
**文件数**: 51 个 SQL 文件
**总行数**: 9047 行

> **关键人物**：[Michael Stonebraker](../docs/people/michael-stonebraker.md)（POSTGRES 创始人, 图灵奖 2014）

## 概述与定位

PostgreSQL 是当今功能最完善的开源关系型数据库，也是最忠实于 SQL 标准的主流实现。如果说 MySQL 的哲学是"够用就好"，PostgreSQL 的哲学就是**"做就做对"**。它在类型系统、可扩展性、并发控制、查询能力等维度上全面领先，是学术研究成果转化为工业实践的典范。

PostgreSQL 的定位近年发生了显著变化：从"那个功能更强但更难用的 MySQL 替代品"，变成了**数据库领域的事实标准接口**。CockroachDB、YugabyteDB、Greenplum、甚至 DuckDB 都选择兼容 PostgreSQL 而非 MySQL，原因很简单 — PostgreSQL 的类型系统和 SQL 方言更完整、更严谨，兼容它意味着更高的功能覆盖度。

## 历史与演进

- **1986**: Michael Stonebraker 在 UC Berkeley 启动 Postgres 项目（post-Ingres），研究面向对象关系模型
- **1994**: Andrew Yu 和 Jolly Chen 添加 SQL 语言支持，改名 Postgres95
- **1996**: 正式更名 PostgreSQL，采用 BSD 许可证，社区接管开发
- **2000s**: 逐步补齐企业级功能 — WAL（8.0）、自动清理（8.1）、热备份（8.2）
- **2010**: PG 9.0 引入流复制和热备，结束"不适合生产"的偏见
- **2012**: PG 9.2 引入 JSON 类型和索引覆盖扫描
- **2014**: PG 9.4 引入 JSONB — 二进制 JSON 存储，改变了文档数据库的竞争格局
- **2016**: PG 9.6 引入并行查询，分析性能飞跃
- **2017**: PG 10 引入声明式分区、逻辑复制 — 版本号改为主版本制
- **2020**: PG 13 引入增量排序、B-tree 去重
- **2022**: PG 15 引入 MERGE 语句（终于支持标准 SQL MERGE）
- **2024**: PG 17 增量备份、改进 VACUUM
- **2025**: PG 18 预计引入异步 I/O 和进一步并行改进

PostgreSQL 的演进节奏极其稳定：**每年一个大版本，从不跳票**。这种可预测性在开源项目中极为罕见。

## 核心设计思路

**可扩展性至上**是 PostgreSQL 的第一设计原则。几乎所有子系统都可以通过扩展机制定制：
- **Extension 框架**：`CREATE EXTENSION` 一键加载功能模块（PostGIS、pg_trgm、hstore 等），无需重编译
- **自定义类型**：不仅能定义新类型，还能为其定义运算符、索引策略、类型转换规则
- **自定义索引方法**：GiST、GIN、BRIN、SP-GiST 框架允许第三方实现全新索引结构
- **自定义函数语言**：PL/pgSQL 只是起点，可加载 PL/Python、PL/V8（JavaScript）、PL/Rust

**类型严格**：PostgreSQL 不做隐式类型转换。`WHERE int_col = '123'` 在 MySQL 中正常，在 PostgreSQL 中需要显式转换。这避免了大量隐式转换导致的索引失效问题。

**DDL 事务性**：`CREATE TABLE`、`ALTER TABLE`、`DROP TABLE` 都可以在事务中执行并回滚。这是 PostgreSQL 相对于 MySQL 和 Oracle 的重大优势，使得数据库迁移脚本可以做到原子性。

**MVCC 元组版本化**：每个 UPDATE 不是原地修改，而是写入新版本元组并标记旧版本为死亡。这带来了极好的读写并发（读永不阻塞写），但代价是需要 VACUUM 回收死元组。

## 独特特色（其他引擎没有的）

- **JSONB + GIN 索引**：二进制 JSON 存储 + 倒排索引，使 PostgreSQL 成为唯一能与 MongoDB 正面竞争的关系型数据库
- **`::` 类型转换运算符**：`'2024-01-01'::date`，比 `CAST(x AS date)` 简洁得多
- **`$$` Dollar Quoting**：`$$函数体$$`，彻底解决字符串中单引号转义问题
- **`RETURNING` 子句**：INSERT/UPDATE/DELETE 直接返回被影响的行，避免额外查询
- **`FILTER` 子句**：`COUNT(*) FILTER (WHERE status = 'active')`，条件聚合的优雅写法
- **`generate_series()`**：生成整数/时间序列的表函数，填充日期维度的利器
- **部分索引**：`CREATE INDEX ON t(col) WHERE status = 'active'`，只索引满足条件的行
- **EXCLUDE 约束**：基于 GiST 索引的排斥约束，可表达"时间区间不重叠"等复杂业务规则
- **Row Level Security (RLS)**：行级安全策略，多租户数据隔离的内核级方案
- **Advisory Locks**：应用层分布式锁，无需额外中间件
- **可写 CTE**：`WITH deleted AS (DELETE FROM t RETURNING *) INSERT INTO archive SELECT * FROM deleted`
- **`DISTINCT ON`**：按指定列去重并保留整行，比 `ROW_NUMBER()` 子查询简洁

## 已知的设计不足与历史包袱

- **VACUUM 是永恒的话题**：元组版本化的 MVCC 要求定期回收死元组。虽然 autovacuum 已经很成熟，但大表的 VACUUM 仍会消耗显著 I/O，长事务会阻止 VACUUM 回收
- **无原生连接池**：PostgreSQL 的进程模型（每连接一个进程）在高并发短连接场景下需要 PgBouncer 等外部连接池。MySQL 的线程模型在这方面天然优势
- **无 PACKAGE（Oracle 有）**：PL/pgSQL 没有 Package 概念，无法将相关函数/过程/类型打包为一个逻辑单元
- **PG 11 前 ADD COLUMN WITH DEFAULT 需重写全表**：这个问题持续了 20 年，直到 PG 11 才修复。在此之前，给大表加有默认值的列是噩梦
- **无 TRY_CAST**：直到目前仍无内置的安全类型转换函数，需要自定义函数包装异常处理
- **XID 回卷风险**：32 位事务 ID 在极高写入量下可能回卷，需要定期 VACUUM FREEZE。PG 近年版本持续改进这个问题
- **逻辑复制限制**：不复制 DDL、不支持所有数据类型，仍在逐版本完善
- **升级需要 pg_upgrade 或逻辑复制**：不支持小版本间的原地滚动升级（与 MySQL 类似）

## 兼容生态

PostgreSQL 协议已成为新一代数据库的"通用语言"：
- **CockroachDB**：分布式 SQL，PostgreSQL 协议兼容，强一致性
- **YugabyteDB**：分布式 SQL，PostgreSQL 兼容，Google Spanner 开源替代
- **Greenplum**：基于 PostgreSQL 的 MPP 分析型数据库
- **Amazon Redshift**：最早基于 PostgreSQL 8.x 分叉的云数据仓库
- **openGauss**（华为）：基于 PostgreSQL 的国产数据库
- **Hologres**（阿里云）：HSAP 引擎，PostgreSQL 协议
- **TimescaleDB**：PostgreSQL Extension，时序数据专用
- **Materialize**：流式物化视图，PostgreSQL 协议
- **DuckDB**：嵌入式 OLAP，SQL 方言高度接近 PostgreSQL
- **Supabase**：基于 PostgreSQL 的 Firebase 替代品

## 对引擎开发者的参考价值

- **TOAST（The Oversized-Attribute Storage Technique）**：大值自动压缩/离线存储，对应用完全透明。这是处理变长大字段的优雅方案
- **GIN/GiST 索引框架**：通用倒排索引（GIN）和通用搜索树（GiST）是可扩展索引的教科书实现，支撑了全文搜索、JSONB 查询、地理空间等完全不同的索引需求
- **SSI（Serializable Snapshot Isolation）**：PostgreSQL 9.1 实现了基于快照隔离的可串行化，无需传统的两阶段锁，性能远优于锁式 SERIALIZABLE
- **Extension 架构**：hook 机制 + 共享内存 + SPI（Server Programming Interface）组成的扩展框架，允许在不修改内核的情况下添加新数据类型、索引方法、查询计划节点甚至安全策略
- **进程模型 vs 线程模型**：PostgreSQL 坚持多进程架构（每连接一进程），稳定性极强但内存开销大。这与 MySQL 的多线程模型形成对照，是数据库架构设计的经典权衡
- **规则系统（Rule System）**：虽然实际中已被触发器取代，但其"查询重写"的设计思想影响了物化视图刷新等后续特性

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/postgres.md) | **IDENTITY(10+) 是标准自增列替代传统 SERIAL**——SERIAL 实际创建隐式 SEQUENCE 对象且 DROP TABLE 不自动清理，IDENTITY 符合 SQL 标准且生命周期绑定列。TEXT=VARCHAR 无性能差异（底层相同 varlena 存储），无需纠结选择。DDL 可在事务中执行并回滚（对比 MySQL/Oracle DDL 隐式提交不可回滚）。 |
| [改表](../ddl/alter-table/postgres.md) | **DDL 事务性可回滚是 PostgreSQL 相对 MySQL/Oracle 的最大优势**——迁移脚本可做到原子性，失败自动回滚无残留。ADD COLUMN WITH DEFAULT 在 PG 11+ 秒级完成（之前需重写全表，大表操作是噩梦）。对比 MySQL 的 Online DDL（INSTANT/INPLACE/COPY 三种算法）和 Oracle 的 DDL 自动提交。 |
| [索引](../ddl/indexes/postgres.md) | **GiST/GIN/BRIN/SP-GiST 四大索引框架是 PostgreSQL 可扩展性的标杆**——GIN 支撑全文搜索和 JSONB 查询，GiST 支撑地理空间（PostGIS），BRIN 适合时序数据（极小索引大表）。部分索引 `WHERE status='active'` 只索引满足条件的行。CREATE INDEX CONCURRENTLY 不锁表（对比 MySQL 的 Online DDL 仍有锁阶段）。 |
| [约束](../ddl/constraints/postgres.md) | **EXCLUDE 排斥约束是 PostgreSQL 独有**——基于 GiST 索引实现"时间区间不重叠"等复杂业务规则，无需触发器。CHECK/FK/UNIQUE 完整强制执行（对比 BigQuery/Snowflake/Redshift 约束仅作优化器提示）。延迟约束（DEFERRABLE）支持事务结束时统一检查，解决循环外键问题。 |
| [视图](../ddl/views/postgres.md) | **物化视图 REFRESH MATERIALIZED VIEW CONCURRENTLY 不阻塞读**——但无自动增量刷新（需手动或 pg_cron 定时刷新）。对比 Oracle 的 Fast Refresh+Query Rewrite（最强实现）和 BigQuery 的自动增量刷新+智能查询重写，PostgreSQL 物化视图功能中等。安全屏障视图（security_barrier）防止信息泄漏。 |
| [序列与自增](../ddl/sequences/postgres.md) | **IDENTITY(10+) 是推荐的自增方案**——GENERATED ALWAYS/BY DEFAULT 两种模式。传统 SERIAL 仍可用但有隐式 SEQUENCE 清理问题。独立 SEQUENCE 对象支持 CACHE/CYCLE/OWNED BY 精细控制。对比 MySQL 的 AUTO_INCREMENT（最简实现）和 Oracle 的 SEQUENCE（缓存策略更成熟），PG 方案最标准。 |
| [数据库/Schema/用户](../ddl/users-databases/postgres.md) | **Database.Schema 二级命名空间**支持 Schema 多租户隔离——同一数据库不同 Schema 互不干扰。RLS（Row Level Security）行级安全策略是内核级多租户方案（对比 Oracle VPD 更早但实现层次相似）。pg_hba.conf 认证链控制连接级安全。对比 MySQL 的 Database=Schema 一级、BigQuery 的 Project.Dataset.Table 三级。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/postgres.md) | **EXECUTE format() 是 PL/pgSQL 动态 SQL 的核心**——`format('%I.%I', schema, table)` 安全引用标识符防注入（对比 Oracle 的 DBMS_ASSERT 和 MySQL 的 PREPARE/EXECUTE 无类似安全工具）。DO $$ ... $$ 匿名块可直接执行动态逻辑无需创建存储过程（对比 MySQL 无匿名块）。 |
| [错误处理](../advanced/error-handling/postgres.md) | **EXCEPTION WHEN 块 + SQLSTATE 标准错误码**是最规范的过程式错误处理——GET STACKED DIAGNOSTICS 可获取完整错误上下文（消息、行号、约束名）。对比 Oracle 的命名异常/RAISE_APPLICATION_ERROR（功能相当）和 MySQL 的 DECLARE HANDLER（功能较弱、无精细分类）。 |
| [执行计划](../advanced/explain/postgres.md) | **EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) 是业界最实用的执行计划工具之一**——BUFFERS 显示缓存命中/未命中（直接定位 I/O 瓶颈），FORMAT JSON 适合程序化解析。pg_stat_statements 扩展提供历史查询统计（对比 MySQL 缺少同等功能），auto_explain 自动记录慢查询计划。 |
| [锁机制](../advanced/locking/postgres.md) | **Advisory Locks 是 PostgreSQL 独有的应用层分布式锁**——无需额外中间件即可实现跨会话协调。MVCC 元组版本化保证读永不阻塞写（对比 SQL Server 默认锁式并发读阻塞写）。无锁升级机制（对比 SQL Server 的行→页→表锁自动升级），避免了升级导致的意外阻塞。 |
| [分区](../advanced/partitioning/postgres.md) | **声明式分区(10+) 取代了旧的继承+触发器方案**——支持 RANGE/LIST/HASH 三种分区方式。分区可拥有独立索引、独立 VACUUM。分区键无需包含在主键中（对比 MySQL 分区键必须在主键/唯一索引中——最大限制）。对比 Oracle 分区类型最丰富（COMPOSITE/INTERVAL）但需单独购买 Option。 |
| [权限](../advanced/permissions/postgres.md) | **RLS（Row Level Security）是内核级行级安全策略**——`CREATE POLICY` 定义每个角色可见的行，多租户隔离无需应用层 WHERE 过滤。GRANT/REVOKE 完整标准支持。对比 Oracle VPD（实现更早、层次更深）和 SQL Server 的 DENY（显式拒绝优先于 GRANT，PostgreSQL 无 DENY）。 |
| [存储过程](../advanced/stored-procedures/postgres.md) | **PL/pgSQL + PL/Python/PL/V8/PL/Rust 多语言生态**是 PostgreSQL 可扩展性的体现——可在数据库内运行 Python 机器学习、JavaScript 业务逻辑。$$ Dollar Quoting 彻底解决字符串转义。无 Package 概念（对比 Oracle PL/SQL 的包封装是最大差距）。对比 MySQL 无匿名块、需 DELIMITER 变更（最大尴尬）。 |
| [临时表](../advanced/temp-tables/postgres.md) | **ON COMMIT DROP/DELETE ROWS/PRESERVE ROWS 三种行为选项**——无需预定义结构，CREATE TEMP TABLE 按需创建。对比 Oracle 的 GTT（全局临时表需预先定义结构）和 SQL Server 的 #temp（存储在 tempdb 是核心资源）。临时表对 RLS 策略不生效——需注意安全隐患。 |
| [事务](../advanced/transactions/postgres.md) | **SSI（Serializable Snapshot Isolation, 9.1+）是无锁可串行化的学术突破**——基于快照隔离检测读写冲突，性能远优于传统两阶段锁式 SERIALIZABLE。DDL 事务性——CREATE/ALTER/DROP 可在事务中回滚（对比 MySQL/Oracle DDL 隐式提交）。Savepoint 支持事务内部分回滚。 |
| [触发器](../advanced/triggers/postgres.md) | **BEFORE/AFTER/INSTEAD OF 触发器完整**——支持行级（FOR EACH ROW）和语句级（FOR EACH STATEMENT）双模式。事件触发器(9.3+) 可在 DDL 操作（CREATE/ALTER/DROP）时触发——用于审计和策略强制执行。对比 MySQL 仅支持行级触发器、SQL Server 无 BEFORE 触发器。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/postgres.md) | **RETURNING 子句返回被删除的行**——一次操作完成删除+审计，避免额外 SELECT。USING 子句支持多表关联删除。所有 DML 均可在事务中回滚（对比 MySQL 的 TRUNCATE 不可回滚）。对比 Oracle 的 Flashback Table（误删恢复）方案不同但目标相似。 |
| [插入](../dml/insert/postgres.md) | **RETURNING 子句是 INSERT 的独有优势**——`INSERT...RETURNING id` 一步获取自增 ID 无需额外查询（对比 MySQL 的 LAST_INSERT_ID()）。COPY 命令批量导入性能远超逐行 INSERT（二进制模式更快）。可写 CTE 支持 `WITH ins AS (INSERT...RETURNING *) SELECT...`。 |
| [更新](../dml/update/postgres.md) | **UPDATE...FROM 多表更新语法**——`UPDATE t1 SET col=t2.val FROM t2 WHERE t1.id=t2.id`（对比 MySQL 的 UPDATE JOIN 语法风格不同）。RETURNING 返回更新后的行。MVCC 下 UPDATE 实际创建新版本元组（对比 Oracle 的 Undo-based 原地更新+旧版本写 Undo）。 |
| [Upsert](../dml/upsert/postgres.md) | **ON CONFLICT DO UPDATE(9.5+) 是最灵活的 UPSERT 实现**——可指定冲突列 `ON CONFLICT(col)` 或约束名 `ON CONFLICT ON CONSTRAINT pk_name`。EXCLUDED 伪表引用待插入值。对比 MySQL 的 ON DUPLICATE KEY UPDATE（只能基于唯一索引）和 Oracle/SQL Server 的 MERGE（功能更全但语法更重）。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/postgres.md) | **FILTER 子句是 PostgreSQL 最优雅的条件聚合语法**——`COUNT(*) FILTER (WHERE status='active')` 比 CASE WHEN 更简洁可读（对比 MySQL/Oracle 无 FILTER 子句，需用 CASE 模拟）。GROUPING SETS/CUBE/ROLLUP 完整支持多维聚合。string_agg 聚合字符串（对比 MySQL 的 GROUP_CONCAT 有截断陷阱）。 |
| [条件函数](../functions/conditional/postgres.md) | **标准 CASE + 原生布尔类型**是 PostgreSQL 条件逻辑的基础——布尔值是一等类型可直接 `WHERE is_active`（对比 MySQL 无原生布尔用 TINYINT 模拟）。COALESCE/NULLIF 标准。无 MySQL 的 IF() 函数和 SQL Server 的 IIF()（非标准但简洁），PostgreSQL 坚持标准 CASE 语法。 |
| [日期函数](../functions/date-functions/postgres.md) | **INTERVAL 类型是 PostgreSQL 日期运算的核心**——`date + INTERVAL '3 months'` 自然语法（对比 MySQL 的 DATE_ADD 函数式调用）。generate_series(timestamp, timestamp, interval) 生成时间序列是日期填充利器。age() 计算两个日期的差值返回 INTERVAL。对比 BigQuery 的四种时间类型严格区分方案。 |
| [数学函数](../functions/math-functions/postgres.md) | **NUMERIC 任意精度运算是金融计算的基础**——无精度上限（对比 Oracle NUMBER 38 位、BigQuery NUMERIC 38 位）。除零报错（对比 MySQL 返回 NULL、BigQuery SAFE_DIVIDE 返回 NULL）。GREATEST/LEAST 内置（对比 SQL Server 2022 才引入）。完整数学函数库包括三角函数和统计函数。 |
| [字符串函数](../functions/string-functions/postgres.md) | **`\|\|` 是标准字符串拼接运算符**（对比 MySQL 中 `\|\|` 是逻辑 OR——最大方言陷阱之一）。regexp_match/regexp_replace 基于 POSIX 正则（对比 BigQuery 基于 re2 线性时间引擎）。string_agg 聚合（对比 MySQL 的 GROUP_CONCAT 默认 1024 字节截断）。format() 函数支持 C 风格格式化输出。 |
| [类型转换](../functions/type-conversion/postgres.md) | **`::` 类型转换运算符**比 `CAST(x AS type)` 简洁得多——`'2024-01-01'::date` 是 PostgreSQL 特色语法。严格类型系统不做隐式转换（对比 MySQL 隐式转换导致索引失效）。无 TRY_CAST 安全转换（对比 SQL Server/Snowflake/BigQuery 的 SAFE_CAST），需自定义函数包装异常处理。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/postgres.md) | **可写 CTE 是 PostgreSQL 独有的强大特性**——`WITH del AS (DELETE FROM t RETURNING *) INSERT INTO archive SELECT * FROM del` 一条语句完成归档。MATERIALIZED/NOT MATERIALIZED 提示(12+) 控制 CTE 物化策略。对比 MySQL 8.0 CTE 无法包含 DML，Oracle 需 /*+ MATERIALIZE */ 提示。 |
| [全文搜索](../query/full-text-search/postgres.md) | **tsvector/tsquery + GIN 索引是关系型数据库中最强的内置全文搜索**——支持多语言分词、权重排序、短语搜索。pg_trgm 扩展提供模糊匹配和 LIKE/ILIKE 加速。对比 MySQL 的 InnoDB FULLTEXT（功能基础）和 BigQuery 的 SEARCH INDEX（2023+，更简单）。 |
| [连接查询](../query/joins/postgres.md) | **LATERAL JOIN(9.3+) 是标准 SQL 的正式实现**——允许右侧子查询引用左侧表的列（对比 SQL Server 的 CROSS APPLY 更早但语法非标准）。支持所有 JOIN 类型包括 FULL OUTER JOIN（对比 MySQL 至今不支持 FULL OUTER JOIN）。Hash/Merge/Nested Loop 三种 JOIN 算法由优化器自动选择。 |
| [分页](../query/pagination/postgres.md) | **LIMIT/OFFSET 标准分页**——FETCH FIRST N ROWS WITH TIES(13+) 包含并列行。深分页性能问题与 MySQL 相同（OFFSET 越大越慢），推荐 Keyset 分页 `WHERE id > last_id ORDER BY id LIMIT N`。对比 Oracle 12c 前需 ROWNUM 三层嵌套，PostgreSQL 分页语法最简洁。 |
| [行列转换](../query/pivot-unpivot/postgres.md) | **无原生 PIVOT/UNPIVOT 语法**——需用 tablefunc 扩展的 crosstab() 函数实现（安装和使用都比原生语法复杂）。对比 Oracle 11g/SQL Server/BigQuery/DuckDB 均有原生 PIVOT 语法，这是 PostgreSQL 在分析查询上的短板。CASE+GROUP BY 手写是常见替代方案。 |
| [集合操作](../query/set-operations/postgres.md) | **UNION/INTERSECT/EXCEPT 全部支持 ALL 变体**——完整符合 SQL 标准。对比 MySQL 直到 8.0.31 才支持 INTERSECT/EXCEPT（此前是唯一不支持的主流数据库），Oracle 使用 MINUS 而非标准 EXCEPT。PostgreSQL 的集合操作自始至终最完整。 |
| [子查询](../query/subquery/postgres.md) | **LATERAL 子查询(9.3+) 允许子查询引用外层表列**——对 Top-N-per-group 和表值函数调用极有用。ANY/ALL/EXISTS 标准支持。优化器成熟度在子查询展开和去关联上一直领先（对比 MySQL 5.x 子查询性能噩梦，8.0 才修复）。 |
| [窗口函数](../query/window-functions/postgres.md) | **8.4 起即支持窗口函数**（比 MySQL 8.0 早 9 年），**GROUPS 帧类型(11+) 是 PostgreSQL 独有**——按逻辑分组而非物理行定义帧。FILTER 子句可用于窗口聚合。WINDOW 命名子句支持复用。无 QUALIFY 子句（对比 BigQuery/Snowflake/DuckDB 无需子查询过滤窗口结果）。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/postgres.md) | **generate_series(date, date, interval) 是最简洁的日期序列生成方案**——原生表函数，无需递归 CTE 或辅助表。对比 MySQL 需递归 CTE（8.0+）、Oracle 需 CONNECT BY LEVEL、BigQuery 用 GENERATE_DATE_ARRAY。LEFT JOIN 填充缺失日期一行完成。 |
| [去重](../scenarios/deduplication/postgres.md) | **DISTINCT ON 是 PostgreSQL 独有的去重写法**——`SELECT DISTINCT ON (key) * FROM t ORDER BY key, ts DESC` 一行搞定分组取最新。对比 MySQL/Oracle 需 ROW_NUMBER()+子查询包装，BigQuery/DuckDB 的 QUALIFY 也较简洁但语义不同。ROW_NUMBER+CTE 方案同样可用。 |
| [区间检测](../scenarios/gap-detection/postgres.md) | **generate_series 填充完整序列 + LEFT JOIN 检测缺失**——比窗口函数 LAG/LEAD 方案更直观。对比 MySQL 需递归 CTE 生成序列（冗长）、Teradata 有 sys_calendar 系统日历表（独有）。窗口函数辅助方案适合非等间隔数据。 |
| [层级查询](../scenarios/hierarchical-query/postgres.md) | **递归 CTE 是 SQL 标准的层级查询方案**——无 Oracle 的 CONNECT BY（更简洁但非标准）。ltree 扩展提供路径运算（`@>` 祖先包含、`~` 模式匹配），适合物化路径模式。对比 SQL Server 的 hierarchyid 数据类型是另一种物化方案。 |
| [JSON 展开](../scenarios/json-flatten/postgres.md) | **JSONB + GIN 索引是关系型数据库中最强的 JSON 实现**——支持 `@>` 包含查询、`->>` 路径提取，GIN 索引加速复杂 JSON 查询。json_to_recordset 将 JSON 数组展开为关系表。JSON_TABLE(17+) 终于支持 SQL 标准语法。对比 Snowflake 的 VARIANT+FLATTEN（语法更简洁）和 MySQL 的 JSON_TABLE（无索引优势）。 |
| [迁移速查](../scenarios/migration-cheatsheet/postgres.md) | **类型严格是迁移的核心注意点**——从 MySQL 迁入需处理隐式转换差异（`WHERE int_col = '123'` 在 PG 需显式转换）。DDL 可回滚是优势——迁移脚本原子性更高。`\|\|` 是拼接（MySQL 中是 OR）、TEXT=VARCHAR（MySQL 中有差异）、SERIAL→IDENTITY 升级。 |
| [TopN 查询](../scenarios/ranking-top-n/postgres.md) | **DISTINCT ON 分组取一是最简写法**——无需窗口函数和子查询。FETCH FIRST N ROWS WITH TIES(13+) 包含并列行。对比 BigQuery/DuckDB 的 QUALIFY 无需子查询包装、MySQL 8.0 需 ROW_NUMBER+嵌套。PostgreSQL 方案最多样化。 |
| [累计求和](../scenarios/running-total/postgres.md) | **SUM() OVER(ORDER BY ...) 是标准累计求和**——8.4 起即支持窗口函数（比 MySQL 8.0 早近十年）。默认帧 RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW。GROUPS 帧(11+) 提供按逻辑分组的高级帧定义。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/postgres.md) | **MERGE(15+) 是标准 SCD 实现**——到达较晚（对比 Oracle 9i 首创、SQL Server 2008 支持）。15 之前用 INSERT...ON CONFLICT DO UPDATE 模拟 Type 1 SCD。可写 CTE 可组合 INSERT+UPDATE 实现 Type 2 SCD（对比 Oracle MERGE 多分支功能更完整）。 |
| [字符串拆分](../scenarios/string-split-to-rows/postgres.md) | **string_to_table(14+) 是最简洁的字符串拆分函数**——一行搞定（对比 MySQL 需递归 CTE+SUBSTRING_INDEX 最繁琐）。regexp_split_to_table 支持正则分隔。unnest(string_to_array()) 是 14 前的标准方案。对比 SQL Server 的 STRING_SPLIT（简洁但无序号）。 |
| [窗口分析](../scenarios/window-analytics/postgres.md) | **窗口函数实现最完整**——FILTER 子句可条件聚合、GROUPS 帧(11+) 独有、NTH_VALUE 支持获取第 N 行值。WINDOW 命名子句可复用帧定义。对比 MySQL 无 FILTER/GROUPS/QUALIFY，SQL Server 无 NTH_VALUE/GROUPS，PostgreSQL 在窗口函数上仅缺 QUALIFY。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/postgres.md) | **原生 ARRAY 类型 + 运算符（`@>`包含、`&&`重叠）**是 PostgreSQL 独有的关系型数据库特性——可直接 `WHERE tags @> ARRAY['sql']`。自定义复合类型（CREATE TYPE）可定义结构化列。hstore 扩展提供键值存储。对比 BigQuery 的 STRUCT/ARRAY 一等公民、DuckDB 的 LIST/STRUCT/MAP。 |
| [日期时间](../types/datetime/postgres.md) | **TIMESTAMP WITH TIME ZONE 内部存储 UTC，显示时自动转换**——无 MySQL 的 2038 年问题（对比 MySQL TIMESTAMP 是 32 位 Unix 时间戳）。INTERVAL 类型支持丰富的日期运算（`+ INTERVAL '1 month'`）。对比 BigQuery 严格区分四种时间类型、Oracle 的 DATE 含时间到秒级（易混淆）。 |
| [JSON](../types/json/postgres.md) | **JSONB + GIN 索引是业界最强的 JSON 实现**——支持 `@>` 包含查询、jsonpath 路径表达式(12+)、部分更新 `jsonb_set()`。JSON_TABLE(17+) 终于支持 SQL 标准。对比 MySQL 的 JSON（二进制存储但索引弱）、Snowflake 的 VARIANT（更灵活但无 GIN 级索引）、Oracle 的 Duality View(23ai)。 |
| [数值类型](../types/numeric/postgres.md) | **NUMERIC 任意精度无上限**——金融计算不会溢出（对比 Oracle NUMBER 38 位、BigQuery BIGNUMERIC 76 位）。SMALLINT/INT/BIGINT 标准整数类型。无 UNSIGNED（对比 MySQL 的 UNSIGNED 正在废弃趋势中）。FLOAT/DOUBLE PRECISION 遵循 IEEE 754。 |
| [字符串类型](../types/string/postgres.md) | **TEXT = VARCHAR 无性能差异**——底层相同 varlena 存储，无需纠结选择（对比 MySQL 的 TEXT 有索引限制、不能设默认值）。默认字符语义（非字节语义，对比 Oracle VARCHAR2 默认字节语义是中文大坑）。排序规则（Collation）灵活可按列指定。 |
