# Apache Derby

**分类**: Java 嵌入式数据库（Apache）
**文件数**: 51 个 SQL 文件
**总行数**: 4021 行

## 概述与定位

Apache Derby 是一个纯 Java 实现的开源关系型数据库，是 Apache 软件基金会的顶级项目。Derby 的设计目标是提供零管理、零配置的嵌入式数据库体验——只需将一个 JAR 文件加入 Java 应用的 classpath 即可使用。它同时支持嵌入式模式和网络服务器模式。Derby 的另一个身份是 Java DB——曾随 JDK 6-8 捆绑发布，使其成为 Java 开发者最容易获取的数据库。

## 历史与演进

- **1996 年**：Cloudscape 公司开发 JBMS 数据库（Derby 的前身）。
- **1999 年**：Informix 收购 Cloudscape。
- **2001 年**：IBM 收购 Informix，将 Cloudscape 纳入 IBM 产品线。
- **2004 年**：IBM 将 Cloudscape 代码捐赠给 Apache 基金会，命名为 Derby。
- **2006 年**：Sun 将 Derby 以"Java DB"身份捆绑在 JDK 6 中。
- **2011 年**：10.8 版本引入 BOOLEAN 类型和增强的 SQL 标准支持。
- **2019 年**：10.15 引入 SEQUENCE 和 OFFSET/FETCH 分页。
- **2022-2025 年**：10.16/10.17 持续维护，保持与新 JDK 版本的兼容性。

## 核心设计思路

Derby 的核心设计哲学是**简单和标准**。它严格遵循 SQL 标准和 JDBC 规范，不追求扩展性而追求正确性。存储引擎基于传统的 B-Tree 索引和堆文件（Heap File）组织，使用 WAL（Write-Ahead Logging）保证事务持久性。并发控制支持行级锁和表级锁。Derby 可通过**Java 存储过程**扩展——用户可以用 Java 方法实现存储过程和函数，通过 `CALL` 语句调用。

## 独特特色

- **MERGE 语句**（10.11+）：支持标准 SQL MERGE（UPSERT），`MERGE INTO target USING source ON condition WHEN MATCHED/NOT MATCHED`。
- **Java 存储过程**：`CREATE PROCEDURE procName ... LANGUAGE JAVA PARAMETER STYLE JAVA EXTERNAL NAME 'pkg.Class.method'` 用 Java 类实现存储过程。
- **SYSCS_UTIL 系统工具**：`CALL SYSCS_UTIL.SYSCS_SET_DATABASE_PROPERTY(...)` 等系统过程管理数据库属性。
- **零配置嵌入**：`jdbc:derby:mydb;create=true` 自动创建并连接数据库，无需安装或配置。
- **内置网络服务器**：可选启动 Derby Network Server 提供远程 JDBC 访问。
- **GENERATED ALWAYS AS IDENTITY**：标准 SQL 自增列语法。
- **XML 数据类型**：内置 XML 类型和 XMLPARSE/XMLSERIALIZE/XMLEXISTS 函数。

## 已知不足

- SQL 功能集相比现代数据库较为保守——窗口函数支持有限，不支持 CTE 的递归形式。
- 不支持 JSON 数据类型和相关函数。
- 性能不适合高并发或大数据量的生产场景。
- 社区活跃度低，版本更新缓慢，新特性引入非常保守。
- 不支持 FULL OUTER JOIN（仅在较新版本中部分支持）。
- 不支持 CREATE TABLE AS SELECT（CTAS）。
- 从 JDK 9 开始不再随 JDK 捆绑，获取便利性下降。

## 对引擎开发者的参考价值

Derby 的代码库是学习传统 RDBMS 实现的良好教材——完整的 SQL 解析器（基于 JavaCC）、基于成本的查询优化器、B-Tree 存储引擎、WAL 日志管理和锁管理器都在一个纯 Java 代码库中清晰实现。Java 存储过程的集成方式展示了如何将宿主语言方法嵌入 SQL 引擎。SYSCS_UTIL 系统过程的设计为数据库管理接口提供了一种内省式的参考模式。Derby 对 SQL 标准的严格遵循也使其成为 SQL 标准合规性测试的良好参考。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/derby.md) | **Apache Java 嵌入式数据库——纯 Java 实现 + ANSI SQL 子集**。`jdbc:derby:mydb;create=true` 自动创建数据库，零配置嵌入。SQL 功能集保守但正确，严格遵循 ANSI SQL 标准子集。对比 H2（多兼容模式、功能更丰富）和 SQLite（C 实现、更轻量），Derby 以标准合规性和 Java 原生集成为核心优势。 |
| [改表](../ddl/alter-table/derby.md) | **ALTER ADD/DROP COLUMN——无 MODIFY/CHANGE COLUMN**。不支持修改列类型或重命名列，需要重建表。对比 PostgreSQL（ALTER COLUMN TYPE 支持）和 H2（ALTER 更灵活），Derby 的 ALTER 是所有主流数据库中最受限的之一。 |
| [索引](../ddl/indexes/derby.md) | **仅 B-tree 索引——无其他索引类型**。无 Hash 索引、无全文索引、无表达式索引。对比 H2（B-tree+Hash+Lucene 全文）和 PostgreSQL（B-tree/GIN/GiST/BRIN），Derby 的索引类型最为单一。 |
| [约束](../ddl/constraints/derby.md) | **PK/FK/CHECK/UNIQUE 标准支持且强制执行**——约束实现严格遵循 SQL 标准。对比 PostgreSQL（约束完整）和 MySQL 8.0（CHECK 从 8.0.16 真正生效），Derby 在约束正确性上表现可靠。 |
| [视图](../ddl/views/derby.md) | **普通视图，无物化视图**。视图定义标准。对比 H2（同样无物化视图）和 PostgreSQL（物化视图原生），Derby 缺少预计算视图但对嵌入式场景影响不大。 |
| [序列与自增](../ddl/sequences/derby.md) | **IDENTITY + SEQUENCE（10.6+）+ GENERATED ALWAYS/BY DEFAULT**——严格遵循 SQL 标准的自增列语法。SEQUENCE 在 10.6 版本引入。对比 PostgreSQL 的 SERIAL/IDENTITY 和 MySQL 的 AUTO_INCREMENT，Derby 的自增实现是 SQL 标准最严格的参考之一。 |
| [数据库/Schema/用户](../ddl/users-databases/derby.md) | **Schema = 用户 + 内置身份验证 + LDAP 集成**——默认 Schema 与用户名相同。内置身份验证或通过 LDAP 外部认证。对比 PostgreSQL（Schema 与用户解耦）和 H2（内置用户权限），Derby 的 Schema=用户模型与 Oracle 类似。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/derby.md) | **无动态 SQL——Java JDBC PreparedStatement 替代**。Derby 无内置过程语言，动态 SQL 通过 Java JDBC API 实现。对比 PostgreSQL 的 PL/pgSQL EXECUTE 和 H2（同样依赖 Java），Derby 将过程化能力完全委托给宿主语言。 |
| [错误处理](../advanced/error-handling/derby.md) | **无过程式错误处理——SQL 异常由 Java 处理**。SQLSTATE 错误码通过 JDBC SQLException 传播到应用层。对比 PostgreSQL 的 EXCEPTION WHEN 和 SQL Server 的 TRY...CATCH，Derby 的错误处理完全依赖 Java。 |
| [执行计划](../advanced/explain/derby.md) | **EXPLAIN 通过 derby.language.logStatementText 属性**——不使用标准 EXPLAIN 语句，而是通过系统属性 `CALL SYSCS_UTIL.SYSCS_SET_RUNTIMESTATISTICS(1)` 启用运行时统计。对比 PostgreSQL 的 EXPLAIN ANALYZE（即时输出）和 H2 的 EXPLAIN ANALYZE，Derby 的执行计划获取方式非标准且较繁琐。 |
| [锁机制](../advanced/locking/derby.md) | **行级锁 + 表级锁 + 锁升级 + 死锁检测**——传统的基于锁的并发控制（非 MVCC）。锁升级在行锁数量超过阈值时自动触发。对比 PostgreSQL（MVCC 读不阻塞写）和 H2（MVStore MVCC），Derby 的锁模型较为传统，高并发下读写可能互相阻塞。 |
| [分区](../advanced/partitioning/derby.md) | **无分区支持**——嵌入式定位，大数据量场景不适用。对比 PostgreSQL（声明式分区完整）和 H2（同样无分区），分区缺失对 Derby 的目标场景影响不大。 |
| [权限](../advanced/permissions/derby.md) | **GRANT/REVOKE 标准 + 内置身份验证**——支持表、列、过程级别的权限控制。对比 PostgreSQL（RBAC 完整）和 H2（内置用户权限），Derby 的权限模型标准且可靠。 |
| [存储过程](../advanced/stored-procedures/derby.md) | **Java 存储过程（EXTERNAL NAME）——无 SQL 过程语言**。`CREATE PROCEDURE p ... LANGUAGE JAVA PARAMETER STYLE JAVA EXTERNAL NAME 'pkg.Class.method'` 将 Java 方法注册为存储过程。**SYSCS_UTIL** 系统过程提供数据库管理接口。对比 PostgreSQL 的 PL/pgSQL（完整过程语言）和 H2（Java UDF 类似），Derby 的 Java 存储过程是嵌入式数据库的经典扩展模式。 |
| [临时表](../advanced/temp-tables/derby.md) | **DECLARE GLOBAL TEMPORARY TABLE 会话级**——通过 DECLARE 创建（不在 catalog 中注册），会话结束时自动删除。与 Db2 的 DGTT 语法一致（IBM 传承）。对比 PostgreSQL 的 CREATE TEMP TABLE 和 H2 的 CREATE TEMP TABLE，Derby 的 DECLARE 语法是 IBM 系统的传统。 |
| [事务](../advanced/transactions/derby.md) | **ACID 完整 + READ COMMITTED 默认 + Savepoint**——基于锁的事务隔离（非 MVCC）。Savepoint 支持部分回滚。对比 PostgreSQL（MVCC + ACID）和 H2（MVCC + ACID），Derby 在事务正确性上可靠但并发性能受限于锁模型。 |
| [触发器](../advanced/triggers/derby.md) | **BEFORE/AFTER 行级/语句级触发器**——触发器体可调用 Java 存储过程。语句级触发器可通过 REFERENCING NEW TABLE/OLD TABLE 引用变更集合。对比 PostgreSQL（触发器功能完整）和 H2（Java 触发器），Derby 的触发器功能标准且完整。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/derby.md) | **DELETE 标准 + TRUNCATE（10.11+）**——TRUNCATE 在 10.11 才引入，之前仅支持 DELETE。对比 PostgreSQL（TRUNCATE 早已支持）和 H2（TRUNCATE 标准），Derby 的 TRUNCATE 引入较晚。 |
| [插入](../dml/insert/derby.md) | **INSERT 标准 + 批量 INSERT**——INSERT INTO ... VALUES (...), (...) 多行插入。不支持 INSERT RETURNING 或 INSERT ... SELECT IDENTITY。对比 PostgreSQL 的 INSERT RETURNING 和 MySQL 的 LAST_INSERT_ID()，Derby 获取自增 ID 需通过 JDBC getGeneratedKeys()。 |
| [更新](../dml/update/derby.md) | **UPDATE 标准**——标准 UPDATE SET WHERE 语法。支持可更新游标（UPDATE WHERE CURRENT OF）。对比 PostgreSQL（UPDATE FROM 扩展语法）和 MySQL（多表 UPDATE），Derby 的 UPDATE 严格遵循标准。 |
| [Upsert](../dml/upsert/derby.md) | **MERGE 标准（10.11+）——之前需 INSERT+UPDATE 两步操作**。`MERGE INTO target USING source ON condition WHEN MATCHED/NOT MATCHED` 标准语法。10.11 之前需应用层判断后选择 INSERT 或 UPDATE。对比 PostgreSQL 的 ON CONFLICT（更简洁）和 H2 的 MERGE KEY（更简洁），Derby 的 MERGE 是标准但引入较晚。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/derby.md) | **基础聚合（COUNT/SUM/AVG/MIN/MAX）——无 STRING_AGG/LISTAGG**。缺少字符串拼接聚合是 Derby 的明显短板，需 Java UDF 或应用层实现。无 GROUPING SETS/CUBE/ROLLUP。对比 PostgreSQL 的 string_agg（内置）和 H2 的 STRING_AGG，Derby 的聚合函数是主流数据库中最少的。 |
| [条件函数](../functions/conditional/derby.md) | **CASE/COALESCE/NULLIF 标准**——无 IF/IIF/DECODE/NVL 等便捷函数，需用 CASE 表达式替代。对比 MySQL 的 IF（三元函数）和 Oracle 的 DECODE，Derby 严格遵循标准但缺少便捷函数。 |
| [日期函数](../functions/date-functions/derby.md) | **YEAR/MONTH/DAY 提取函数 + TIMESTAMPADD/TIMESTAMPDIFF**——日期提取使用函数（而非 EXTRACT 标准语法）。TIMESTAMPADD/TIMESTAMPDIFF 是 JDBC 标准函数。对比 PostgreSQL 的 EXTRACT/date_trunc（更灵活）和 MySQL 的 DATE_ADD/DATEDIFF，Derby 的日期函数遵循 JDBC 传统。 |
| [数学函数](../functions/math-functions/derby.md) | **基础数学函数（ABS/MOD/SQRT 等）**——函数集较少，无 POWER/LOG/LN 等（需 Java UDF）。对比 PostgreSQL（完整数学函数）和 H2（完整数学函数），Derby 的数学函数是最精简的。 |
| [字符串函数](../functions/string-functions/derby.md) | **\|\| 拼接 + SUBSTR/LENGTH/TRIM 标准**——函数集遵循 SQL 标准但数量有限。无 REPLACE（需应用层处理）。对比 PostgreSQL 的 replace/regexp_replace（丰富）和 H2（函数更丰富），Derby 的字符串函数集是最小的主流数据库之一。 |
| [类型转换](../functions/type-conversion/derby.md) | **CAST 标准，无 TRY_CAST**——转换失败时报错。对比 SQL Server 的 TRY_CAST（失败返回 NULL）和 BigQuery 的 SAFE_CAST，Derby 缺少安全转换函数。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/derby.md) | **不支持 CTE——Derby 最大局限之一**。无 WITH 子句、无递归查询，需用子查询或临时表替代。对比 PostgreSQL（WITH RECURSIVE 完整）和 H2（CTE 标准支持），CTE 缺失严重限制了 Derby 的查询灵活性和递归能力。 |
| [全文搜索](../query/full-text-search/derby.md) | **无全文搜索**——需依赖外部搜索引擎或 Java UDF。对比 H2（Lucene 集成）和 PostgreSQL 的 tsvector+GIN，Derby 缺少任何文本搜索能力。 |
| [连接查询](../query/joins/derby.md) | **INNER/LEFT/RIGHT/FULL JOIN 标准，无 LATERAL**——所有标准 JOIN 类型支持（包括 FULL JOIN）。对比 PostgreSQL（LATERAL 支持）和 MySQL 8.0（LATERAL 支持），Derby 缺少 LATERAL 但标准 JOIN 完整。 |
| [分页](../query/pagination/derby.md) | **FETCH FIRST N ROWS ONLY + OFFSET（10.5+），无 LIMIT 语法**——遵循 SQL:2008 标准分页语法（与 Db2 一致，IBM 传承）。对比 MySQL 的 LIMIT/OFFSET（非标准但更简洁）和 PostgreSQL（LIMIT 和 FETCH FIRST 均支持），Derby 严格使用标准分页语法。 |
| [行列转换](../query/pivot-unpivot/derby.md) | **无原生 PIVOT**——需 CASE+GROUP BY 手动实现。对比 Oracle（PIVOT 原生）和 BigQuery（PIVOT 原生），Derby 缺少行列转换语法。 |
| [集合操作](../query/set-operations/derby.md) | **UNION/INTERSECT/EXCEPT 完整**——ALL/DISTINCT 修饰符支持。对比 PostgreSQL（集合操作完整）和 MySQL 8.0（INTERSECT/EXCEPT 较新），Derby 的集合操作功能完整且标准。 |
| [子查询](../query/subquery/derby.md) | **关联子查询 + IN/EXISTS 标准**——无 CTE 支持意味着复杂查询需依赖深层子查询嵌套。对比 PostgreSQL（CTE + 子查询灵活）和 H2（CTE 支持），Derby 的查询表达能力受限于 CTE 缺失。 |
| [窗口函数](../query/window-functions/derby.md) | **ROW_NUMBER（10.4+）——窗口函数支持有限**。仅支持 ROW_NUMBER/RANK/DENSE_RANK 等基本排名函数，不支持 LAG/LEAD/NTILE 和 ROWS/RANGE 帧。对比 PostgreSQL（窗口函数完整）和 H2（窗口函数完整），Derby 的窗口函数是主流数据库中最受限的。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/derby.md) | **无 generate_series、无 CTE——需辅助表**。只能预建日期维度表或通过 Java 应用层生成日期序列。对比 PostgreSQL 的 generate_series（最简洁）和 H2 的 SYSTEM_RANGE，Derby 在日期生成上最为不便。 |
| [去重](../scenarios/deduplication/derby.md) | **ROW_NUMBER（10.4+）+ 子查询去重**——无 CTE 需用子查询包装。对比 PostgreSQL 的 DISTINCT ON（最简洁）和 H2（ROW_NUMBER+CTE），Derby 的去重因无 CTE 而更繁琐。 |
| [区间检测](../scenarios/gap-detection/derby.md) | **自连接检测（窗口函数支持不完整）**——无 LAG/LEAD 函数，需通过自连接比较相邻行。对比 PostgreSQL 的 LAG/LEAD（窗口函数直接检测）和 BigQuery 的 GENERATE_DATE_ARRAY，Derby 的间隙检测方案最原始。 |
| [层级查询](../scenarios/hierarchical-query/derby.md) | **无递归 CTE——Derby 最大限制之一**。层级遍历只能通过应用层递归查询或预计算扁平化表实现。对比 PostgreSQL（WITH RECURSIVE 标准）和 Oracle（CONNECT BY），Derby 无法在 SQL 层面做层级查询。 |
| [JSON 展开](../scenarios/json-flatten/derby.md) | **无 JSON 支持（功能缺失）**——无 JSON 数据类型、无 JSON 函数。JSON 数据只能存为字符串并在 Java 层解析。对比 PostgreSQL 的 JSONB（最强 JSON 支持）和 H2 的 JSON（2.0+ 支持），JSON 缺失是 Derby 的重要限制。 |
| [迁移速查](../scenarios/migration-cheatsheet/derby.md) | **Java 嵌入式定位——功能较少，无 CTE/JSON 是主要限制**。关键差异：无 CTE（递归查询不可能）；无 JSON；窗口函数有限；无 MODIFY COLUMN；无 STRING_AGG/LISTAGG；FETCH FIRST 标准分页；Java 存储过程替代 SQL 过程语言；SYSCS_UTIL 系统过程管理数据库。 |
| [TopN 查询](../scenarios/ranking-top-n/derby.md) | **ROW_NUMBER（10.4+）+ FETCH FIRST**——`FETCH FIRST 10 ROWS ONLY` 直接分页，或 ROW_NUMBER 排序后取前 N。对比 MySQL 的 LIMIT 和 PostgreSQL 的 LIMIT，Derby 使用 SQL 标准分页语法。 |
| [累计求和](../scenarios/running-total/derby.md) | **窗口函数支持有限**——基本 ROW_NUMBER/RANK 可用，但 SUM() OVER(ORDER BY ...) 支持取决于版本。早期版本需用关联子查询模拟。对比 PostgreSQL（SUM() OVER 标准）和 H2（SUM() OVER 完整），Derby 的窗口函数限制影响分析场景。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/derby.md) | **MERGE（10.11+）**——10.11 引入标准 MERGE 语法实现 SCD Type 1。10.11 之前需应用层判断 INSERT 或 UPDATE。对比 PostgreSQL 的 ON CONFLICT 和 H2 的 MERGE KEY，Derby 的 MERGE 引入较晚但遵循标准。 |
| [字符串拆分](../scenarios/string-split-to-rows/derby.md) | **无拆分函数——需 Java UDF**。无内置 SPLIT 函数，无递归 CTE（不能用 CTE 逐段截取），只能通过 Java UDF 实现。对比 PostgreSQL 的 string_to_array+unnest（一行搞定）和 Firebird（递归 CTE 模拟），Derby 在字符串拆分上最受限。 |
| [窗口分析](../scenarios/window-analytics/derby.md) | **窗口函数支持有限——ROW_NUMBER/RANK 等基本函数**。无 LAG/LEAD/NTILE/SUM() OVER 完整支持。对比 PostgreSQL（窗口函数完整）和 H2（窗口函数完整），Derby 的窗口分析能力是主流数据库中最受限的。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/derby.md) | **无 ARRAY/STRUCT/MAP 类型**——Derby 的类型系统最为精简，不支持任何集合或结构化列类型。对比 PostgreSQL（ARRAY 原生）和 H2（ARRAY 支持），Derby 缺少复合类型。 |
| [日期时间](../types/datetime/derby.md) | **DATE/TIME/TIMESTAMP 标准，无 INTERVAL**——三种时间类型严格遵循 SQL 标准。日期算术需用 TIMESTAMPADD/TIMESTAMPDIFF 函数。对比 PostgreSQL（INTERVAL 类型灵活）和 Firebird（DATEADD/DATEDIFF 函数），Derby 通过 JDBC 标准函数处理日期算术。 |
| [JSON](../types/json/derby.md) | **无 JSON 支持**——JSON 数据只能存为 VARCHAR/CLOB 字符串，需 Java 层解析。对比 PostgreSQL 的 JSONB（最强）和 H2 的 JSON（2.0+ 支持），JSON 缺失是 Derby 最大的类型短板。 |
| [数值类型](../types/numeric/derby.md) | **SMALLINT/INTEGER/BIGINT/DECIMAL/FLOAT/DOUBLE 标准**——数值类型遵循 SQL 标准定义。DECIMAL 最大 31 位精度。对比 PostgreSQL 的 NUMERIC（任意精度）和 Db2 的 DECFLOAT，Derby 的数值类型标准但精简。 |
| [字符串类型](../types/string/derby.md) | **VARCHAR/CHAR/CLOB 标准 + UTF-8**——VARCHAR 最大 32672 字节，CLOB 存储大文本。默认 UTF-8 编码。对比 PostgreSQL 的 TEXT（无长度限制）和 MySQL 的 utf8mb4，Derby 的字符串类型标准但 VARCHAR 长度上限较低。 |
