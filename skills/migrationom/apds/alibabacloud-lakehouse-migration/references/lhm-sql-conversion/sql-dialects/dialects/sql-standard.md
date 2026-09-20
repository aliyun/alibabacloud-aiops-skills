# SQL 标准

**分类**: ISO/IEC 9075 SQL 标准
**文件数**: 51 个 SQL 文件
**总行数**: 4736 行

> **关键人物**：[Codd, Chamberlin](../docs/people/founders-of-sql.md)（SQL 理论与语言奠基人）、[Markus Winand](../docs/people/markus-winand.md)（现代 SQL 布道者）

## 概述与定位

SQL 标准（ISO/IEC 9075）是由国际标准化组织（ISO）和国际电工委员会（IEC）联合发布的关系型数据库查询语言规范。它定义了 SQL 语言的语法、语义和数据模型，是所有关系型数据库实现的共同参考基准。SQL 标准不是一个数据库产品，而是一份规范性文档——各数据库厂商在此基础上实现自己的 SQL 方言，同时添加各自的扩展。理解 SQL 标准对于跨数据库迁移和引擎开发至关重要。

## 历史与演进

> 每个版本的详细特性分析、引擎支持矩阵和实现建议，见 [SQL 标准版本详解](../docs/sql-standards/)。

| 版本 | 年份 | 核心新增 | 详细页面 |
|------|------|---------|---------|
| SQL-86/89 | 1986/1989 | 基本 DDL/DML、约束（PK/FK/CHECK） | [详解](../docs/sql-standards/sql-86-89.md) |
| SQL-92 | 1992 | JOIN 语法、CASE WHEN、子查询、VARCHAR/TIMESTAMP | [详解](../docs/sql-standards/sql-92.md) |
| SQL:1999 | 1999 | 递归 CTE、BOOLEAN、LATERAL、ROLE、触发器 | [详解](../docs/sql-standards/sql-1999.md) |
| SQL:2003 | 2003 | **窗口函数**、MERGE、IDENTITY、SEQUENCE、FILTER | [详解](../docs/sql-standards/sql-2003.md) |
| SQL:2006 | 2006 | XML 增强（XQuery 集成） | [详解](../docs/sql-standards/sql-2006.md) |
| SQL:2008 | 2008 | FETCH FIRST 分页、TRUNCATE、MERGE 增强 | [详解](../docs/sql-standards/sql-2008.md) |
| SQL:2011 | 2011 | **时态表**（System-Versioned）、PERIOD | [详解](../docs/sql-standards/sql-2011.md) |
| SQL:2016 | 2016 | **JSON 支持**、LISTAGG、MATCH_RECOGNIZE | [详解](../docs/sql-standards/sql-2016.md) |
| SQL:2023 | 2023 | ANY_VALUE、GREATEST/LEAST、**图查询 SQL/PGQ** | [详解](../docs/sql-standards/sql-2023.md) |

## 核心设计思路

SQL 标准基于**关系模型**（E.F. Codd 1970 年提出）设计，核心思想是用声明式语言描述"要什么数据"而非"如何获取数据"。标准分为多个部分（Part）：Part 1 是框架概述，Part 2（Foundation）是核心 SQL 语法，Part 4 是 SQL/PSM（存储过程），Part 9 是 SQL/MED（外部数据管理），Part 10 是 SQL/OLB（对象语言绑定），Part 14 是 SQL/XML，Part 15 是多维数组，Part 16 是 SQL/PGQ（属性图查询）。标准通过"Feature ID"（如 F302 = INTERSECT、T611 = Elementary OLAP operations）精确标识每个特性。

## 独特特色

- **窗口函数框架**（SQL:2003）：`ROW_NUMBER() / RANK() / DENSE_RANK() / NTILE() OVER (PARTITION BY ... ORDER BY ... ROWS/RANGE BETWEEN ...)`——这一完整框架被几乎所有现代数据库采纳。
- **CTE 与递归**（SQL:1999）：`WITH RECURSIVE cte AS (...)` 为层级查询提供了标准化方案。
- **MERGE 语句**（SQL:2003）：`MERGE INTO ... USING ... WHEN MATCHED/NOT MATCHED` 标准化的 Upsert 操作。
- **时态表**（SQL:2011）：`FOR SYSTEM_TIME AS OF timestamp` 查询历史数据的标准语法。
- **JSON 支持**（SQL:2016）：`JSON_VALUE()`, `JSON_QUERY()`, `JSON_TABLE()` 标准化 JSON 处理。
- **FETCH FIRST 分页**（SQL:2008）：`OFFSET n ROWS FETCH FIRST m ROWS ONLY` 替代各方言的 LIMIT/TOP 语法。
- **图查询 SQL/PGQ**（SQL:2023）：`GRAPH_TABLE` 和路径模式匹配，将图查询纳入 SQL 标准。

## 已知不足

- 标准文档不免费公开（ISO 标准需付费购买），限制了开发者的直接参考。
- 各数据库对标准的实现程度差异巨大——没有任何数据库完整实现了 Full SQL 标准。
- 标准的演进速度远慢于行业需求——许多重要特性（如 LIMIT、UPSERT、JSON）在标准化前已被各方言广泛实现。
- 部分标准特性（如 SIMILAR TO、时态表、多态表函数）采纳率极低，实际工程参考价值有限。
- 标准未涵盖许多实际重要的领域：分布式事务、分区表、全文搜索、向量类型等。
- SQL/PGQ（图查询）的采纳仍处于极早期，主流数据库尚未完整实现。

## 对引擎开发者的参考价值

SQL 标准是数据库引擎开发的首要参考文档。窗口函数的框架规范（ROWS vs RANGE vs GROUPS、EXCLUDE 子句、frame 边界规则）为实现提供了精确的语义定义。SQL:2011 的时态表规范（SYSTEM_TIME 和 APPLICATION_TIME 的双时态模型）为时态数据库引擎设计提供了理论框架。Feature ID 体系为引擎的合规性测试提供了清晰的检查清单。理解标准与各方言的差异也是构建跨数据库兼容层（如 ORM、SQL 转换器）的基础。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/sql-standard.md) | **ANSI/ISO SQL 标准 CREATE TABLE 语法**——定义了列定义、数据类型、DEFAULT 值和 GENERATED ALWAYS/BY DEFAULT AS IDENTITY（SQL:2003）自增列。各引擎的偏离：MySQL 的 AUTO_INCREMENT（非标准）、PostgreSQL 的 SERIAL（非标准快捷方式）、BigQuery 的 STRUCT/ARRAY 列类型（标准外扩展）。对比各引擎实现，CREATE TABLE 是标准覆盖最广但各方言扩展最多的语句。 |
| [改表](../ddl/alter-table/sql-standard.md) | **ALTER TABLE ADD/DROP/ALTER COLUMN 标准定义**——SQL 标准仅定义基本的列增删改语法。各引擎的扩展：MySQL 的 MODIFY/CHANGE COLUMN（非标准）、PostgreSQL 的 ALTER COLUMN TYPE（标准扩展）、Oracle 的 DDL 自动提交（标准未规定 DDL 事务性）。标准未覆盖：Online DDL、分区变更、列重命名等。 |
| [索引](../ddl/indexes/sql-standard.md) | **SQL 标准未定义索引——完全由实现决定**。CREATE INDEX 不在 SQL 标准中。各引擎自行设计：PostgreSQL（B-tree/GIN/GiST/BRIN）、MySQL（B-tree/FULLTEXT/SPATIAL）、BigQuery（无传统索引）。索引是 SQL 标准最大的"留白"之一——查询优化的核心手段完全依赖实现。 |
| [约束](../ddl/constraints/sql-standard.md) | **PK/FK/CHECK/UNIQUE/NOT NULL 标准定义**——约束是 SQL 标准最完整的领域之一。DEFERRABLE（延迟约束）在 SQL:1992 定义。各引擎差异：MySQL（CHECK 8.0.16 才真正生效）、BigQuery/Snowflake（NOT ENFORCED 仅作提示）、PostgreSQL（完整执行+延迟约束）。约束的"执行 vs 不执行"是 OLTP vs OLAP 引擎的分水岭。 |
| [视图](../ddl/views/sql-standard.md) | **CREATE VIEW 标准 + WITH CHECK OPTION**——WITH CHECK OPTION 确保通过可更新视图的 INSERT/UPDATE 不违反视图 WHERE 条件。标准未定义物化视图（MATERIALIZED VIEW 是各引擎的扩展）。对比 PostgreSQL（REFRESH MATERIALIZED VIEW）和 BigQuery（自动增量刷新），物化视图是标准的重要缺失。 |
| [序列与自增](../ddl/sequences/sql-standard.md) | **GENERATED ALWAYS AS IDENTITY（SQL:2003）+ SEQUENCE（SQL:2003）**——标准定义了两种 ID 生成机制。各引擎偏离：MySQL 的 AUTO_INCREMENT（非标准但最早广泛使用）、PostgreSQL 的 SERIAL（非标准快捷方式，PG 10 后推荐 IDENTITY）。SQL:2003 的 IDENTITY 语法现已被 PostgreSQL/Db2/Firebird 等广泛采纳。 |
| [数据库/Schema/用户](../ddl/users-databases/sql-standard.md) | **CREATE SCHEMA/ROLE/GRANT 标准权限模型**——标准定义了 SCHEMA 命名空间和 ROLE 基于角色的权限。各引擎差异：MySQL（Database=Schema）、Oracle（Schema=User）、PostgreSQL（Schema 与 User 解耦）。标准未定义 Database 概念（各引擎自行实现）。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/sql-standard.md) | **EXECUTE IMMEDIATE / PREPARE（SQL/PSM 标准）**——SQL/PSM（Part 4）定义了过程化 SQL 中的动态 SQL 语法。各引擎差异：PostgreSQL 的 EXECUTE（PL/pgSQL，非 PSM 标准）、Oracle 的 EXECUTE IMMEDIATE（接近标准）、Db2 的 PREPARE/EXECUTE（最接近标准）。 |
| [错误处理](../advanced/error-handling/sql-standard.md) | **DECLARE HANDLER / SIGNAL / RESIGNAL（SQL/PSM 标准）**——SQLSTATE 五字符错误码是标准定义的错误标识体系。各引擎差异：PostgreSQL 的 EXCEPTION WHEN（非 PSM 但 SQLSTATE 兼容）、SQL Server 的 TRY...CATCH（非标准）、Db2 的 DECLARE HANDLER（最接近标准）。 |
| [执行计划](../advanced/explain/sql-standard.md) | **SQL 标准未定义 EXPLAIN——完全由实现决定**。EXPLAIN 是最广泛使用却不在标准中的 SQL 语句之一。各引擎实现差异巨大：PostgreSQL（EXPLAIN ANALYZE 最详细）、MySQL（EXPLAIN FORMAT=TREE）、Db2（EXPLAIN 表方式存储）、BigQuery（无 EXPLAIN，Console 面板）。 |
| [锁机制](../advanced/locking/sql-standard.md) | **隔离级别标准定义——READ UNCOMMITTED/READ COMMITTED/REPEATABLE READ/SERIALIZABLE**。标准以"现象"（Dirty Read/Non-Repeatable Read/Phantom）定义隔离级别，未规定实现机制（锁 vs MVCC）。各引擎实现：PostgreSQL（MVCC，RC/RR/SERIALIZABLE）、Oracle（Undo MVCC，RC/SERIALIZABLE）、MySQL InnoDB（MVCC+锁，四级都支持）。 |
| [分区](../advanced/partitioning/sql-standard.md) | **SQL 标准未定义分区——完全由实现决定**。PARTITION BY 在 DDL 中不属于标准。各引擎自行设计：PostgreSQL（声明式 RANGE/LIST/HASH）、Oracle（分区最丰富）、BigQuery（按列 PARTITION BY）。分区是标准的又一重要"留白"。 |
| [权限](../advanced/permissions/sql-standard.md) | **GRANT/REVOKE 标准语法 + ROLE 角色**——SQL 标准定义了细粒度的 GRANT 权限和 ROLE 角色机制。标准未覆盖：行级安全（RLS，各引擎自行实现）、列级安全、标签安全（LBAC）。对比 PostgreSQL 的 RLS 和 BigQuery 的 GCP IAM，权限的细粒度控制超出了标准范围。 |
| [存储过程](../advanced/stored-procedures/sql-standard.md) | **SQL/PSM 标准（CREATE PROCEDURE/FUNCTION）**——Part 4 定义了过程化 SQL 的完整框架（变量、IF/WHILE、CURSOR、异常处理）。各引擎偏离严重：Oracle 的 PL/SQL（最早也最完整，非 PSM）、PostgreSQL 的 PL/pgSQL（受 PL/SQL 影响，非 PSM）、Db2 的 SQL PL（最接近 PSM 标准）。PSM 标准的采纳率远低于核心 SQL 标准。 |
| [临时表](../advanced/temp-tables/sql-standard.md) | **DECLARE LOCAL TEMPORARY TABLE（SQL 标准）**——标准定义了会话级临时表。各引擎差异：PostgreSQL 的 CREATE TEMP TABLE（非 DECLARE）、Oracle 的 CREATE GLOBAL TEMPORARY TABLE（元数据持久）、Db2 的 DECLARE GLOBAL TEMPORARY TABLE（最接近标准）。临时表的创建方式是各引擎差异最大的领域之一。 |
| [事务](../advanced/transactions/sql-standard.md) | **BEGIN/COMMIT/ROLLBACK/SAVEPOINT 标准事务**——标准定义了事务控制语句和四个隔离级别。各引擎差异：MySQL 的 START TRANSACTION（非标准 BEGIN）、PostgreSQL 的 DDL 事务性（标准未明确规定）、Oracle 的隐式事务开始（无显式 BEGIN）。标准未定义分布式事务协议（2PC 等由实现决定）。 |
| [触发器](../advanced/triggers/sql-standard.md) | **CREATE TRIGGER 标准（SQL:1999）——BEFORE/AFTER/INSTEAD OF**。标准定义了行级和语句级触发器、REFERENCING NEW/OLD 引用、触发条件（WHEN）。各引擎差异：MySQL（仅 BEFORE/AFTER 行级）、PostgreSQL（完整 + 事件触发器扩展）、BigQuery/Snowflake（无触发器）。触发器在云数仓中普遍缺失。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/sql-standard.md) | **DELETE FROM ... WHERE 标准语法**。TRUNCATE TABLE 在 SQL:2008 标准化。各引擎扩展：PostgreSQL 的 DELETE RETURNING（非标准）、MySQL 的多表 DELETE（非标准）、Db2 的 FINAL TABLE（DML 即查询）。 |
| [插入](../dml/insert/sql-standard.md) | **INSERT INTO ... VALUES/SELECT 标准语法**。多行 INSERT（一条 VALUES 多组值）在较新标准中定义。各引擎扩展：PostgreSQL 的 INSERT RETURNING（非标准）、Oracle 的 INSERT ALL（非标准多表插入）、BigQuery 的流式/批量加载（非标准）。 |
| [更新](../dml/update/sql-standard.md) | **UPDATE ... SET ... WHERE 标准语法**。标准定义了基本的单表 UPDATE。各引擎扩展：PostgreSQL 的 UPDATE FROM（多表关联更新，非标准）、MySQL 的多表 UPDATE（非标准）、Db2 的 FINAL TABLE（UPDATE 即查询）。 |
| [Upsert](../dml/upsert/sql-standard.md) | **MERGE（SQL:2003 标准）完整语法**——`MERGE INTO target USING source ON condition WHEN MATCHED/NOT MATCHED` 是标准化的 Upsert。各引擎偏离：PostgreSQL 的 ON CONFLICT（非标准但更简洁）、MySQL 的 ON DUPLICATE KEY UPDATE（非标准）、Firebird 的 UPDATE OR INSERT（非标准）。MERGE 的标准化推动了 Upsert 操作的跨引擎一致性。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/sql-standard.md) | **COUNT/SUM/AVG/MIN/MAX + LISTAGG（SQL:2016）标准**。FILTER 子句（SQL:2003）允许 `SUM(x) FILTER (WHERE condition)` 条件聚合。各引擎差异：MySQL（无 FILTER 子句，用 IF/CASE 替代）、BigQuery（COUNTIF 替代 FILTER）、PostgreSQL（FILTER 子句原生支持）。ANY_VALUE（SQL:2023）解决 GROUP BY 中非聚合列问题。 |
| [条件函数](../functions/conditional/sql-standard.md) | **CASE/COALESCE/NULLIF（SQL:1992 标准）**——CASE 是 SQL 标准中最重要的条件表达式。COALESCE 返回第一个非 NULL 值。各引擎扩展：Oracle 的 DECODE/NVL（非标准）、MySQL 的 IF/IFNULL（非标准）、BigQuery 的 SAFE_ 前缀（非标准）。标准条件函数被所有引擎完整支持。 |
| [日期函数](../functions/date-functions/sql-standard.md) | **EXTRACT / CURRENT_DATE / CURRENT_TIMESTAMP 标准**——EXTRACT(YEAR FROM date) 是标准的日期部分提取语法。各引擎扩展：MySQL 的 DATE_FORMAT/STR_TO_DATE（非标准）、PostgreSQL 的 date_trunc/age（非标准）、Db2 的 Labeled Durations（非标准）。标准日期函数是各引擎差异最大的领域之一。 |
| [数学函数](../functions/math-functions/sql-standard.md) | **ABS/MOD/POWER/SQRT 标准数学函数**。GREATEST/LEAST 在 SQL:2023 才标准化（各引擎早已支持）。数学函数是标准覆盖最完整且各引擎差异最小的领域。 |
| [字符串函数](../functions/string-functions/sql-standard.md) | **\|\| 拼接 / SUBSTRING / TRIM / UPPER / LOWER 标准**——\|\| 是 SQL 标准的字符串拼接运算符。各引擎偏离：MySQL 的 CONCAT 函数（\|\| 默认为 OR 运算符）、BigQuery 的 CONCAT 函数（无 \|\|）。TRIM 标准语法 `TRIM(LEADING/TRAILING/BOTH char FROM str)` 被各引擎广泛支持。 |
| [类型转换](../functions/type-conversion/sql-standard.md) | **CAST（SQL:1992 标准）**——`CAST(expr AS type)` 是唯一的标准类型转换语法。各引擎扩展：PostgreSQL 的 :: 运算符（非标准但极简洁）、Oracle 的 TO_NUMBER/TO_DATE（非标准）、BigQuery 的 SAFE_CAST（非标准安全转换）。标准无 TRY_CAST/SAFE_CAST 概念。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/sql-standard.md) | **WITH [RECURSIVE]（SQL:1999 标准）**——递归 CTE 是 SQL:1999 的重要贡献，为层级查询提供了标准化方案。各引擎差异：Derby（不支持 CTE）、MySQL 8.0（CTE 较晚引入）、Oracle（CONNECT BY 是非标准替代）。递归 CTE 现已被除 Derby 外的所有主流引擎支持。 |
| [全文搜索](../query/full-text-search/sql-standard.md) | **SQL 标准未定义全文搜索——完全由实现决定**。各引擎自行设计：PostgreSQL（tsvector+GIN）、MySQL（InnoDB FULLTEXT）、HANA（FUZZY Search）、BigQuery（SEARCH INDEX 2023+）。全文搜索是标准的重要缺失领域。 |
| [连接查询](../query/joins/sql-standard.md) | **INNER/LEFT/RIGHT/FULL/CROSS/NATURAL JOIN 标准**——SQL:1992 定义了完整的 JOIN 语法体系。LATERAL（SQL:1999）允许子查询引用前面的 FROM 项。各引擎差异：MySQL（不支持 FULL JOIN，LATERAL 8.0+ 支持）、Derby（无 LATERAL）。JOIN 是标准覆盖最完整且各引擎合规性最高的领域之一。 |
| [分页](../query/pagination/sql-standard.md) | **FETCH FIRST N ROWS ONLY / OFFSET（SQL:2008 标准）**——`OFFSET 10 ROWS FETCH FIRST 5 ROWS ONLY` 是标准分页语法，源自 Db2 的实现。各引擎差异：MySQL/PostgreSQL 的 LIMIT/OFFSET（非标准但更简洁、更广泛使用）、SQL Server 的 TOP（非标准）。标准语法虽正式但 LIMIT 的实际采用率更高。 |
| [行列转换](../query/pivot-unpivot/sql-standard.md) | **SQL 标准未定义 PIVOT/UNPIVOT——由实现决定**。各引擎自行实现：Oracle（PIVOT 11g+ 原生）、BigQuery（PIVOT 2021+ 原生）、SQL Server（PIVOT 原生）。多数引擎仍需 CASE+GROUP BY 手动实现。PIVOT 是标准应该但尚未纳入的常用功能。 |
| [集合操作](../query/set-operations/sql-standard.md) | **UNION/INTERSECT/EXCEPT + ALL/DISTINCT 标准**——SQL:1992 定义了完整的集合操作语法。各引擎差异：Oracle 的 MINUS（= EXCEPT，非标准命名）、MySQL 8.0（INTERSECT/EXCEPT 较新）、ClickHouse（UNION 默认 ALL，与标准 DISTINCT 默认相反）。集合操作命名是少数引擎间差异的领域之一。 |
| [子查询](../query/subquery/sql-standard.md) | **标量/关联/IN/EXISTS/ANY/ALL 标准子查询**——SQL 标准定义了完整的子查询语义。各引擎差异主要在优化能力：MySQL 5.x（子查询性能差，8.0 大幅改善）、PostgreSQL（子查询展开优化成熟）。子查询的标准语义被各引擎完整支持，差异在于优化策略。 |
| [窗口函数](../query/window-functions/sql-standard.md) | **OVER(PARTITION BY ... ORDER BY ...)(SQL:2003 标准)**——窗口函数框架是 SQL:2003 最重要的贡献之一。ROW_NUMBER/RANK/DENSE_RANK/NTILE/LAG/LEAD + ROWS/RANGE/GROUPS 帧。各引擎差异：MySQL 8.0（窗口函数最晚引入）、BigQuery（QUALIFY 子句是非标准扩展）、Derby（仅基本排名函数）。SQL:2011 增加了 GROUPS 帧和 EXCLUDE 子句。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/sql-standard.md) | **标准未定义序列生成函数——递归 CTE 可模拟**。各引擎扩展：PostgreSQL 的 generate_series（最简洁）、BigQuery 的 GENERATE_DATE_ARRAY、HANA 的 SERIES_GENERATE_DATE、H2 的 SYSTEM_RANGE。标准未定义序列生成是跨引擎迁移的常见痛点。 |
| [去重](../scenarios/deduplication/sql-standard.md) | **SELECT DISTINCT / ROW_NUMBER 标准去重**——ROW_NUMBER() OVER(PARTITION BY key ORDER BY ...) 是标准的精确去重方案。各引擎扩展：PostgreSQL 的 DISTINCT ON（非标准但最简洁）、BigQuery 的 QUALIFY（非标准但更简洁）、TDengine 的 UNIQUE 函数。 |
| [区间检测](../scenarios/gap-detection/sql-standard.md) | **窗口函数 LAG/LEAD（SQL:2003）标准**——LAG/LEAD 比较相邻行是标准的间隙检测方案。各引擎扩展：TimescaleDB 的 gapfill（内置间隙填充）、TDengine 的 INTERVAL+FILL（时序间隙检测）。标准方案通用但时序引擎有更优雅的内置解决方案。 |
| [层级查询](../scenarios/hierarchical-query/sql-standard.md) | **WITH RECURSIVE（SQL:1999 标准）**——递归 CTE 是标准的层级查询方案。各引擎差异：Oracle 的 CONNECT BY（非标准但更早更直观）、HANA 的 HIERARCHY 函数（非标准但性能更好）、Derby（不支持递归 CTE）。SQL:2023 的 SQL/PGQ 引入了图查询作为层级处理的新标准方案。 |
| [JSON 展开](../scenarios/json-flatten/sql-standard.md) | **JSON_TABLE/JSON_VALUE/JSON_QUERY（SQL:2016 标准）**——SQL:2016 标准化了 JSON 处理函数。各引擎差异：PostgreSQL 的 jsonb_array_elements（非标准但更早）、MySQL 8.0 的 JSON_TABLE（遵循标准）、BigQuery 的 JSON_QUERY_ARRAY+UNNEST（部分标准）。JSON 是标准化最晚但最急需的领域之一。 |
| [迁移速查](../scenarios/migration-cheatsheet/sql-standard.md) | **各方言对标准的偏离点汇总**。核心偏离：分页（LIMIT vs FETCH FIRST vs TOP）、字符串拼接（\|\| vs CONCAT）、自增（AUTO_INCREMENT vs SERIAL vs IDENTITY）、Upsert（ON CONFLICT vs ON DUPLICATE KEY vs MERGE）、NULL 处理（Oracle 的 ''=NULL）、类型命名（INT vs INTEGER vs INT64）。 |
| [TopN 查询](../scenarios/ranking-top-n/sql-standard.md) | **ROW_NUMBER + FETCH FIRST（SQL:2008）**——标准组合方案：ROW_NUMBER() 排名 + FETCH FIRST N ROWS ONLY 截取。各引擎扩展：BigQuery 的 QUALIFY（最简洁非标准方案）、TDengine 的 TOP 函数（内置 TopN）、MySQL 的 LIMIT（非标准但最广泛使用）。 |
| [累计求和](../scenarios/running-total/sql-standard.md) | **SUM() OVER(ORDER BY ...)(SQL:2003 窗口函数标准)**——标准的累计求和方案。所有支持窗口函数的引擎写法一致，是跨引擎迁移最无痛的场景之一。TDengine 的 CSUM（非标准内置函数）是唯一显著偏离标准的实现。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/sql-standard.md) | **MERGE（SQL:2003 标准）**——标准 MERGE 可实现 SCD Type 1/2。SQL:2011 的时态表（SYSTEM_TIME）是 SCD 的标准化终极方案。各引擎差异：Db2/HANA（时态表支持最好）、PostgreSQL（无原生时态表）、BigQuery（Time Travel 是非标准替代）。 |
| [字符串拆分](../scenarios/string-split-to-rows/sql-standard.md) | **SQL 标准未定义字符串拆分函数——各引擎自行实现**。各引擎方案：PostgreSQL 的 string_to_array+unnest（最简洁）、BigQuery 的 SPLIT+UNNEST（类似）、MySQL 的 JSON_TABLE（间接方案）、Derby（需 Java UDF）。字符串拆分是标准的明显缺失。 |
| [窗口分析](../scenarios/window-analytics/sql-standard.md) | **ROWS/RANGE/GROUPS 帧（SQL:2003/2011 标准）**——ROWS 按物理行计数，RANGE 按值范围，GROUPS（SQL:2011）按组计数。EXCLUDE 子句（SQL:2011）排除当前行/组/边界值。各引擎差异：MySQL 8.0（不支持 GROUPS/EXCLUDE）、PostgreSQL 12+（GROUPS 支持）、HANA（GROUPS 支持）。窗口函数框架是 SQL 标准最精密的设计之一。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/sql-standard.md) | **ARRAY / ROW 类型（SQL:1999/2003 标准）**——ARRAY 存储同类元素集合，ROW 存储异构字段组合。各引擎差异：PostgreSQL（ARRAY 原生支持最好）、BigQuery（ARRAY/STRUCT 一等公民）、MySQL（不支持 ARRAY/ROW 列类型）。标准定义了但大多数引擎仅部分实现。 |
| [日期时间](../types/datetime/sql-standard.md) | **DATE/TIME/TIMESTAMP/INTERVAL（SQL:1992 标准）**——DATE 仅日期，TIME 仅时间，TIMESTAMP 含两者。INTERVAL 支持日期算术。各引擎偏离：Oracle 的 DATE 含时间（非标准）、MySQL 的 DATETIME/TIMESTAMP 语义混淆、BigQuery 的四种时间类型（DATE/TIME/DATETIME/TIMESTAMP）。时间类型是各引擎差异最混乱的领域。 |
| [JSON](../types/json/sql-standard.md) | **JSON_TABLE/JSON_VALUE/JSON_QUERY（SQL:2016 标准）**——SQL:2016 首次标准化 JSON 数据类型和函数。SQL:2023 增强了 JSON_SERIALIZE/JSON 构造函数。各引擎差异：PostgreSQL 的 JSONB（非标准但功能最强）、MySQL 8.0 的 JSON（遵循部分标准）、BigQuery 的 JSON 类型（2022+ 支持）。JSON 标准化仍在快速演进中。 |
| [数值类型](../types/numeric/sql-standard.md) | **INTEGER/SMALLINT/BIGINT/DECIMAL/FLOAT/DOUBLE PRECISION（标准）**——DECIMAL(p,s) 定点精确，FLOAT/DOUBLE 浮点近似。各引擎偏离：MySQL 的 TINYINT/MEDIUMINT（非标准）、BigQuery 的 INT64/FLOAT64（非标准命名）、Db2 的 DECFLOAT（非标准十进制浮点）。数值类型命名是跨引擎迁移的常见困扰。 |
| [字符串类型](../types/string/sql-standard.md) | **CHARACTER/VARCHAR/CLOB（SQL 标准）**——CHARACTER(n) 定长填充，VARCHAR(n) 变长，CLOB 大对象。各引擎偏离：PostgreSQL 的 TEXT（非标准但推荐，无长度限制）、BigQuery 的 STRING（无长度限制，非标准命名）、MySQL 的 utf8 vs utf8mb4（编码混乱）。字符串类型是标准与实际使用差距最大的领域之一。 |
