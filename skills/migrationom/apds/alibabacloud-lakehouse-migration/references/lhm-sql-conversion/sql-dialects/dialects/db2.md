# IBM Db2

**分类**: 传统关系型数据库（IBM）
**文件数**: 51 个 SQL 文件
**总行数**: 4539 行

## 概述与定位

IBM Db2 是关系型数据库领域的奠基者之一，其前身 System R 是 SQL 语言的发源地。Db2 涵盖从大型机（z/OS）到分布式系统（LUW: Linux/Unix/Windows）的完整产品线，长期服务于银行、保险、航空等对数据一致性和可靠性要求极高的行业。在 SQL 标准化进程中，Db2 团队深度参与了 ANSI/ISO SQL 标准的制定，许多 SQL 特性（窗口函数、CTE、MERGE）都在 Db2 中率先实现或验证。

## 历史与演进

- **1983 年**：Db2 for MVS（大型机版本）发布，成为第一款商用 SQL 关系数据库之一。
- **1993 年**：Db2 for Common Servers（后更名 Db2 LUW）发布，覆盖 Unix/Windows 平台。
- **2001 年**：Db2 8 引入 MQT（Materialized Query Table）与自动统计信息维护。
- **2006 年**：Db2 9 成为首个同时支持关系型和 XML 原生存储的数据库（pureXML）。
- **2009 年**：Db2 9.7 引入 Oracle 兼容模式，支持 PL/SQL 语法与 Oracle 数据类型映射。
- **2016 年**：Db2 11.1 引入 BLU Acceleration（内存列存加速）、自适应压缩。
- **2019 年**：Db2 11.5 引入 AI 驱动的自优化功能和 Db2 on Cloud 托管服务。
- **2023-2025 年**：持续增强 JSON 支持、REST API 接口、与 watsonx.data 的 Lakehouse 集成。

## 核心设计思路

1. **SQL 标准旗手**：Db2 是 SQL 标准最严格的追随者之一，FETCH FIRST、LATERAL、MERGE、窗口函数等均率先实现标准语法。
2. **平台分层**：z/OS 版本面向大型机事务处理，LUW 版本面向分布式系统，二者 SQL 方言高度一致但底层架构不同。
3. **自动化管理**：自动存储管理（Automatic Storage）、自动内存调优（STMM）、自动统计收集，减少 DBA 手动干预。
4. **混合负载**：BLU Acceleration 使同一张表同时支持行存 OLTP 查询和列存分析查询，无需数据搬运。

## 独特特色

| 特性 | 说明 |
|---|---|
| **FETCH FIRST n ROWS ONLY** | Db2 最早实现的标准分页语法，后被 SQL:2008 标准采纳，现已被 PostgreSQL/Oracle 等广泛支持。 |
| **Labeled Durations** | `CURRENT_DATE + 3 MONTHS` 这样的日期运算语法，比大多数数据库的 INTERVAL 写法更直观。 |
| **MQT（物化查询表）** | 物化视图的 Db2 实现，支持 REFRESH DEFERRED/IMMEDIATE，可被优化器自动路由。 |
| **FINAL TABLE** | `SELECT * FROM FINAL TABLE (INSERT INTO t VALUES (...))` 在 DML 中嵌套取回受影响行，无需 RETURNING。 |
| **pureXML** | 原生 XML 存储引擎，XML 数据以树形结构存储而非 CLOB，支持 XQuery 和 SQL/XML 混合查询。 |
| **Oracle 兼容模式** | 通过 `DB2_COMPATIBILITY_VECTOR` 参数启用，支持 PL/SQL 语法、Oracle 数据类型、NVL/DECODE 等函数。 |
| **时态查询** | 支持 BUSINESS_TIME 和 SYSTEM_TIME 双时态表，可进行 `FOR SYSTEM_TIME AS OF` 时间旅行查询。 |

## 已知不足

- **学习曲线陡峭**：z/OS 与 LUW 版本的差异、复杂的权限模型与 bufferpool 管理对新手不友好。
- **社区活跃度低**：相比 PostgreSQL/MySQL，Db2 的开源社区和第三方工具生态明显薄弱。
- **许可成本高**：企业版许可费用高昂，社区版（Community Edition）有数据容量和核心数限制。
- **JSON 支持起步晚**：原生 JSON 数据类型和 JSON_TABLE 的引入显著落后于 PostgreSQL 和 MySQL。
- **云原生步伐偏慢**：虽有 Db2 on Cloud，但在 Kubernetes 原生部署和 Serverless 模式上落后于云数仓竞品。

## 对引擎开发者的参考价值

- **FINAL TABLE 设计**：将 DML 语句当作表表达式使用的概念（"数据变更即查询"）比 RETURNING 更通用，对引擎的执行计划树设计有深刻启发。
- **SQL 标准实现参考**：Db2 的窗口函数、MERGE、LATERAL 实现几乎严格对齐 ISO SQL 标准文本，可作为标准合规性测试的基准。
- **Labeled Durations 解析**：将时间单位关键字（DAYS/MONTHS/YEARS）作为后缀运算符处理的解析器设计，比 INTERVAL 字面量更灵活。
- **BLU 列存加速**：在同一表上同时维护行存和列存副本的混合存储引擎设计，对 HTAP 引擎有重要参考。
- **pureXML 存储模型**：将层次化数据以原生树结构存储（而非序列化为文本）的做法，对 JSON 原生存储引擎的设计有借鉴意义。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/db2.md) | **ORGANIZE BY ROW/COLUMN 行列混存**——BLU Acceleration 使同一张表同时支持行存 OLTP 和列存分析查询。IDENTITY 自增列标准实现。**隐式 Schema**（不需要显式 CREATE SCHEMA）。对比 PostgreSQL（仅行存）和 HANA（ROW/COLUMN 建表时指定），Db2 的 BLU 列存是在行存基础上透明叠加的，无需用户选择。 |
| [改表](../ddl/alter-table/db2.md) | **ALTER 后需 REORG 才生效（独特设计）**——部分 ALTER 操作（如 DROP COLUMN）将表标记为"需重组"状态，需执行 `REORG TABLE` 完成物理变更。在线重组支持（INPLACE REORG）。对比 PostgreSQL（ALTER 即时生效，DDL 可事务回滚）和 MySQL（Online DDL 即时），Db2 的 REORG 需求是架构遗留特征，需 DBA 关注。 |
| [索引](../ddl/indexes/db2.md) | **MDC 多维聚集索引（独有设计）+ 块索引**——MDC（Multi-Dimensional Clustering）按多个维度组织数据存储，自动维护数据聚集。块索引（Block Index）在块级别跟踪维度值，扫描时跳过不相关块。对比 BigQuery 的 CLUSTER BY（仅 4 列）和 ClickHouse 的稀疏索引，Db2 的 MDC 是多维数据组织的先驱设计。 |
| [约束](../ddl/constraints/db2.md) | **CHECK/PK/FK/UNIQUE 完整 + 信息性约束（Informational Constraints）**——信息性约束标注 NOT ENFORCED 但告知优化器约束关系，用于查询优化（如 JOIN 消除）。对比 BigQuery（NOT ENFORCED 约束类似设计）和 PostgreSQL（约束必须执行），Db2 的信息性约束是"不执行但利用"的先驱，后被云数仓广泛借鉴。 |
| [视图](../ddl/views/db2.md) | **MQT（物化查询表）自动路由 + REFRESH IMMEDIATE/DEFERRED**——REFRESH IMMEDIATE 在基表变更时自动同步，REFRESH DEFERRED 手动刷新。优化器可自动将查询路由到 MQT（Query Rewrite）。对比 BigQuery（物化视图自动增量刷新+自动重写）和 PostgreSQL（REFRESH MATERIALIZED VIEW 手动），Db2 的 MQT 自动路由功能与 Oracle 的 Query Rewrite 并列最强。 |
| [序列与自增](../ddl/sequences/db2.md) | **IDENTITY + SEQUENCE 标准实现**——缓存策略成熟（CACHE n 预分配序列值减少锁竞争）。CYCLE/NO CYCLE 选项控制溢出行为。对比 PostgreSQL 的 SERIAL/IDENTITY（CACHE 默认 1，性能较低）和 Oracle 的 SEQUENCE（CACHE 默认 20），Db2 的序列缓存调优经验最丰富。 |
| [数据库/Schema/用户](../ddl/users-databases/db2.md) | **Instance → Database → Schema 三级架构 + LBAC 标签安全**——LBAC（Label-Based Access Control）基于安全标签对行和列进行细粒度访问控制，SECADM 安全管理员角色专门管理安全策略。对比 PostgreSQL 的 RLS（行级安全策略）和 Oracle 的 VPD，Db2 的 LBAC 是最早的标签安全实现之一，在政府和军事场景中广泛使用。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/db2.md) | **PREPARE/EXECUTE + EXECUTE IMMEDIATE + 嵌入式 SQL 传统**——Db2 是嵌入式 SQL（Embedded SQL）的发源地，EXEC SQL 语法在 C/COBOL 中使用。SQL PL 中 EXECUTE IMMEDIATE 支持动态 DDL/DML。对比 PostgreSQL 的 EXECUTE（PL/pgSQL）和 Oracle 的 EXECUTE IMMEDIATE，Db2 的嵌入式 SQL 历史最悠久。 |
| [错误处理](../advanced/error-handling/db2.md) | **DECLARE HANDLER + SQLSTATE/SQLCODE + GET DIAGNOSTICS**——GET DIAGNOSTICS 获取错误详细信息（行数、消息文本等），是 SQL 标准的完整实现。对比 PostgreSQL 的 EXCEPTION WHEN + GET STACKED DIAGNOSTICS 和 SQL Server 的 TRY...CATCH + ERROR_MESSAGE()，Db2 的 GET DIAGNOSTICS 是标准合规性最强的实现。 |
| [执行计划](../advanced/explain/db2.md) | **db2expln/db2advis 工具链 + EXPLAIN 表方式存储计划**——执行计划存储在 EXPLAIN_* 系统表中，可用 SQL 查询分析历史计划。db2advis 工具自动推荐索引。对比 PostgreSQL 的 EXPLAIN ANALYZE（即时输出）和 Oracle 的 EXPLAIN PLAN + DBMS_XPLAN，Db2 的"计划存表"方式便于历史分析和自动化调优。 |
| [锁机制](../advanced/locking/db2.md) | **CS/RR/UR/RS 四隔离级别 + Currently Committed**——Currently Committed（CC）允许读者看到已提交的最新版本而非等待锁释放，减少锁等待。锁升级从行→表自动触发。对比 PostgreSQL 的 MVCC（读不阻塞写天然不等待）和 Oracle（Undo MVCC），Db2 的 CC 是在传统锁模型上的创新优化。 |
| [分区](../advanced/partitioning/db2.md) | **DISTRIBUTE BY HASH + ORGANIZE BY 数据分布 + DPF 分布式分区**——DPF（Database Partitioning Feature）支持跨多个物理节点的数据分布。DISTRIBUTE BY HASH 控制节点间分布，ORGANIZE BY 控制节点内数据组织（行/列/MDC）。对比 PostgreSQL（声明式分区）和 CockroachDB（自动分片），Db2 的 DPF 是最早的关系数据库分布式分区实现之一。 |
| [权限](../advanced/permissions/db2.md) | **LBAC 标签安全（行/列级）+ SECADM 安全管理员角色**——LBAC 安全标签可同时对行和列进行访问控制。SECADM 是独立于 DBA 的安全管理角色（权限分离）。对比 PostgreSQL 的 RLS（仅行级）和 Oracle 的 VPD（仅行级），Db2 的 LBAC 是行+列双维度安全控制的先驱。 |
| [存储过程](../advanced/stored-procedures/db2.md) | **SQL PL 过程语言 + COMPOUND 语句**——SQL PL 遵循 SQL/PSM 标准。COMPOUND 语句（BEGIN ... END）可嵌套使用。Package 概念管理编译后的 SQL 计划。对比 PostgreSQL 的 PL/pgSQL（类似但非标准）和 Oracle 的 PL/SQL（最丰富），Db2 的 SQL PL 在标准合规性上最强。 |
| [临时表](../advanced/temp-tables/db2.md) | **DECLARE GLOBAL TEMPORARY TABLE（会话级）+ CGTT（12.1+）**——DGTT 通过 DECLARE 创建（不在 catalog 中注册），CGTT（Created Global Temporary Table）通过 CREATE 创建（元数据持久）。对比 PostgreSQL 的 CREATE TEMP TABLE（类似 CGTT）和 Oracle 的 GTT（元数据持久），Db2 的 DGTT/CGTT 双模式提供灵活选择。 |
| [事务](../advanced/transactions/db2.md) | **ACID 完整 + Currently Committed 避免锁等待**——CC 模式下读者不等待写者释放锁，直接读取行的最近已提交版本。日志管理极成熟（循环日志/归档日志/在线备份）。对比 PostgreSQL 的 MVCC（天然读不阻塞写）和 Oracle 的 Undo MVCC，Db2 的 CC 是在传统锁模型基础上实现类 MVCC 语义的创新。 |
| [触发器](../advanced/triggers/db2.md) | **BEFORE/AFTER/INSTEAD OF 完整 + 行级/语句级**——支持 NEW TABLE/OLD TABLE 在语句级触发器中引用变更集合。对比 PostgreSQL（完整触发器 + REFERENCING NEW TABLE/OLD TABLE）和 MySQL（仅 BEFORE/AFTER 行级），Db2 的触发器功能完整且标准。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/db2.md) | **DELETE 标准 + TRUNCATE 即时释放空间**。TRUNCATE 可在事务内使用（与 Oracle 的 DDL 自动提交不同）。对比 PostgreSQL（TRUNCATE 可事务回滚）和 Oracle（TRUNCATE 是 DDL 不可回滚），Db2 的 TRUNCATE 行为介于两者之间。 |
| [插入](../dml/insert/db2.md) | **INSERT + SELECT + LOAD 批量导入 + NOT LOGGED INITIALLY**——LOAD 工具直接写入数据页（跳过日志），速度极快。NOT LOGGED INITIALLY 选项使 INSERT 跳过事务日志（恢复时该表标记为不可恢复）。对比 PostgreSQL 的 COPY（高效但仍写 WAL）和 BigQuery 的 LOAD JOB（免费），Db2 的 LOAD 是最高效的传统 RDBMS 批量加载方式之一。 |
| [更新](../dml/update/db2.md) | **UPDATE 标准 + 可更新游标**——通过 `UPDATE ... WHERE CURRENT OF cursor_name` 在游标定位处更新。对比 PostgreSQL（可更新游标类似）和 MySQL（可更新游标），Db2 的可更新游标在批处理场景中有传统优势。 |
| [Upsert](../dml/upsert/db2.md) | **MERGE 标准实现完整（业界最早支持之一）**——`MERGE INTO ... USING ... WHEN MATCHED/NOT MATCHED` 是 SQL:2003 标准的核心实现。**FINAL TABLE** 语法可嵌套 `SELECT * FROM FINAL TABLE (INSERT INTO t VALUES (...))` 在 DML 中取回受影响行。对比 PostgreSQL 的 ON CONFLICT（更简洁但非标准 MERGE）和 Oracle 的 MERGE（功能对等），Db2 的 MERGE + FINAL TABLE 组合提供了最强大的 DML-as-Query 能力。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/db2.md) | **LISTAGG + GROUPING SETS/CUBE/ROLLUP 完整**——LISTAGG 实现字符串拼接聚合（SQL:2016 标准）。GROUPING SETS 多维汇总。对比 PostgreSQL 的 string_agg（功能类似但名称不同）和 BigQuery 的 STRING_AGG，Db2 的 LISTAGG 遵循 SQL 标准命名。 |
| [条件函数](../functions/conditional/db2.md) | **CASE/DECODE/NULLIF/COALESCE 标准**——DECODE 在 Oracle 兼容模式下可用。CASE 是 SQL 标准实现。对比 PostgreSQL（无 DECODE）和 Oracle（DECODE 原生），Db2 通过兼容模式支持 DECODE。 |
| [日期函数](../functions/date-functions/db2.md) | **DATE/TIME/TIMESTAMP 严格分类 + Labeled Durations + 特殊寄存器**——`CURRENT_DATE + 3 MONTHS` 是 Db2 独有的 **Labeled Durations** 语法，比 INTERVAL 写法更直观。特殊寄存器（CURRENT DATE/CURRENT TIMESTAMP）等价于其他引擎的 NOW()。对比 PostgreSQL 的 `INTERVAL '3 months'`（标准 INTERVAL）和 Oracle 的 ADD_MONTHS，Db2 的 Labeled Durations 是最自然的日期算术语法。 |
| [数学函数](../functions/math-functions/db2.md) | **完整数学函数 + DECFLOAT 十进制浮点**——DECFLOAT 类型支持 IEEE 754 十进制浮点运算，避免二进制浮点的精度问题。对比 PostgreSQL 的 NUMERIC（定点十进制）和 BigQuery 的 NUMERIC/BIGNUMERIC，Db2 的 DECFLOAT 是浮点与定点之间的独特中间方案。 |
| [字符串函数](../functions/string-functions/db2.md) | **\|\| 拼接标准 + REGEXP_LIKE/REPLACE（10.5+）**——正则函数引入较晚（10.5+），但语法遵循 SQL 标准（REGEXP_LIKE 谓词）。对比 PostgreSQL 的 ~ 正则运算符（更简洁）和 Oracle 的 REGEXP_LIKE（语法一致），Db2 的正则支持虽晚但标准。 |
| [类型转换](../functions/type-conversion/db2.md) | **CAST 标准 + DECFLOAT 十进制浮点独有**——CAST 是 SQL 标准实现。DECFLOAT 类型转换在金融计算场景中重要。对比 PostgreSQL 的 :: 运算符（更简洁）和 Oracle 的 TO_NUMBER/TO_DATE，Db2 的 CAST 严格遵循标准。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/db2.md) | **WITH 标准 + 递归 CTE（业界最早支持之一）**——Db2 是递归 CTE 的先驱实现者，SQL:1999 标准的 WITH RECURSIVE 部分受 Db2 影响。对比 PostgreSQL（WITH RECURSIVE 较早支持）和 Oracle（12c 才原生 WITH RECURSIVE），Db2 在 CTE 领域有历史领先地位。 |
| [全文搜索](../query/full-text-search/db2.md) | **TEXT SEARCH INDEX（Net Search Extender），需单独安装**——非内置组件，需额外安装 NSE 扩展。支持语言感知分词和模糊匹配。对比 PostgreSQL 的 tsvector+GIN（内置）和 HANA 的 FUZZY Search（内置），Db2 的全文搜索需要额外部署，是已知短板。 |
| [连接查询](../query/joins/db2.md) | **JOIN 完整 + LATERAL（9.7+）支持**——LATERAL 允许子查询引用前面 FROM 项的列。Db2 对 LATERAL 的支持较早。对比 PostgreSQL（LATERAL 9.3+ 支持）和 MySQL 8.0（LATERAL 较新），Db2 在 LATERAL 支持上与 PG 并列领先。 |
| [分页](../query/pagination/db2.md) | **FETCH FIRST N ROWS ONLY（最早实现之一）+ OFFSET（11.1+）**——`FETCH FIRST 10 ROWS ONLY` 是 Db2 首创的分页语法，后被 SQL:2008 标准采纳，现被 PostgreSQL/Oracle/SQL Server 广泛支持。对比 MySQL 的 LIMIT（非标准但更简洁）和 Oracle 的 ROWNUM（非标准），Db2 的 FETCH FIRST 是 SQL 标准分页的源头。 |
| [行列转换](../query/pivot-unpivot/db2.md) | **无原生 PIVOT——CASE+GROUP BY 模拟**。对比 Oracle（PIVOT 11g+ 原生）和 BigQuery（PIVOT 2021+ 原生），Db2 缺少行列转换语法糖，需手动编写 CASE 表达式。 |
| [集合操作](../query/set-operations/db2.md) | **UNION/INTERSECT/EXCEPT 完整（最早标准实现之一）**——ALL/DISTINCT 修饰符完整支持。Db2 的集合操作实现是 SQL 标准的参考基准。对比 PostgreSQL（同样完整）和 MySQL 8.0（INTERSECT/EXCEPT 较新），Db2 在集合操作上有历史领先优势。 |
| [子查询](../query/subquery/db2.md) | **关联子查询优化好 + 标量子查询支持**——Db2 优化器对子查询展开（Subquery Flattening）和去关联化（Decorrelation）有成熟实现。对比 PostgreSQL（优化器成熟）和 MySQL 8.0（子查询优化大幅改善），Db2 的子查询优化器历来表现优秀。 |
| [窗口函数](../query/window-functions/db2.md) | **早期支持（7.x+）——OLAP 函数名称**。Db2 是窗口函数的先驱实现者，RANK/DENSE_RANK/ROW_NUMBER 等函数在 SQL:2003 标准之前就已在 Db2 中可用。对比 PostgreSQL（窗口函数 8.4+ 支持）和 MySQL 8.0（窗口函数最晚加入），Db2 在窗口函数领域有深厚的历史积累。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/db2.md) | **递归 CTE 生成日期序列（CTE 先驱）**——Db2 作为递归 CTE 的先驱，用递归 CTE 生成日期序列是标准手法。对比 PostgreSQL 的 generate_series（更简洁）和 HANA 的 SERIES_GENERATE_DATE（内置函数），Db2 使用递归 CTE 的通用方式。 |
| [去重](../scenarios/deduplication/db2.md) | **ROW_NUMBER + CTE 去重**——标准窗口函数去重模式。Db2 作为 ROW_NUMBER 的先驱实现者，此模式在 Db2 中使用最自然。对比 PostgreSQL 的 DISTINCT ON（更简洁）和 BigQuery 的 QUALIFY（最简洁），Db2 使用通用去重方案。 |
| [区间检测](../scenarios/gap-detection/db2.md) | **窗口函数 LAG/LEAD + 递归 CTE**——双工具检测数据间隙。递归 CTE 生成参考序列，窗口函数比较相邻行。对比 PostgreSQL 的 generate_series（更直接）和 BigQuery 的 GENERATE_DATE_ARRAY，Db2 方案利用了其在递归 CTE 和窗口函数上的双重优势。 |
| [层级查询](../scenarios/hierarchical-query/db2.md) | **递归 CTE（最早实现之一），无 CONNECT BY**——Db2 不支持 Oracle 的 CONNECT BY 语法，递归 CTE 是唯一选择。但 Db2 的递归 CTE 实现最为成熟。对比 Oracle（CONNECT BY + 递归 CTE）和 PostgreSQL（仅递归 CTE），Db2 在递归 CTE 上有最深厚的实践经验。 |
| [JSON 展开](../scenarios/json-flatten/db2.md) | **JSON_TABLE（11.1+）+ BSON 存储支持**——JSON_TABLE 遵循 SQL:2016 标准。BSON 存储模式以二进制 JSON 格式存储，查询性能优于文本 JSON。对比 PostgreSQL 的 JSONB+GIN（性能最强）和 Oracle 的 JSON_TABLE（标准实现），Db2 的 JSON 支持起步较晚但遵循标准。 |
| [迁移速查](../scenarios/migration-cheatsheet/db2.md) | **REORG 要求 + LBAC 安全 + 嵌入式 SQL 传统是核心差异**。关键注意：部分 ALTER 后需 REORG 才生效；LBAC 标签安全需专门规划；嵌入式 SQL 代码需预编译；Labeled Durations 日期语法独特；FINAL TABLE DML 语法独有；z/OS 和 LUW 版本间有细微差异。 |
| [TopN 查询](../scenarios/ranking-top-n/db2.md) | **ROW_NUMBER + FETCH FIRST（标准语法）**——`FETCH FIRST 10 ROWS ONLY` 是 Db2 首创且被 SQL 标准采纳的分页语法。对比 MySQL 的 LIMIT（更简洁但非标准）和 BigQuery（LIMIT 标准），Db2 的 FETCH FIRST 是 TopN 的标准化源头。 |
| [累计求和](../scenarios/running-total/db2.md) | **SUM() OVER 标准（早期窗口函数支持）**——Db2 7.x 就支持窗口函数，是业界最早的实现之一。对比 PostgreSQL 8.4+（窗口函数较早）和 MySQL 8.0（窗口函数最晚），Db2 在窗口函数上有最深的历史。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/db2.md) | **MERGE 标准实现（早期支持）**——Db2 的 MERGE 实现是 SQL:2003 标准的核心参考。时态表（SYSTEM_TIME）可自动记录历史版本，实现最优雅的 SCD Type 2。对比 PostgreSQL 的 ON CONFLICT（SCD Type 1 简洁）和 HANA 的时态表（类似设计），Db2 的 MERGE + 时态表组合是 SCD 的标准方案。 |
| [字符串拆分](../scenarios/string-split-to-rows/db2.md) | **XMLTABLE + 递归 CTE 模拟**——无内置 SPLIT 函数，需用 XMLTABLE 将字符串包装为 XML 再展开，或递归 CTE 逐段截取。对比 PostgreSQL 的 string_to_array+unnest（一行搞定）和 BigQuery 的 SPLIT+UNNEST，Db2 的字符串拆分方案较复杂。 |
| [窗口分析](../scenarios/window-analytics/db2.md) | **窗口函数完整（早期支持）+ OLAP 函数集**——移动平均、同环比、占比计算全覆盖。Db2 的窗口函数实现是 SQL 标准的参考基准。对比 PostgreSQL（功能对等）和 BigQuery（QUALIFY 简化过滤），Db2 在窗口分析上有最深厚的标准积累。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/db2.md) | **ROW 类型 + ARRAY（10.5+）+ 结构化类型（Structured Types）**——ROW 类型类似 SQL 标准的复合类型，ARRAY 支持数组列。结构化类型（CREATE TYPE ... UNDER）支持继承。对比 PostgreSQL 的 ARRAY+复合类型（原生支持）和 BigQuery 的 STRUCT/ARRAY，Db2 的类型系统遵循 SQL:1999 标准的 UDT 定义。 |
| [日期时间](../types/datetime/db2.md) | **DATE/TIME/TIMESTAMP 严格分离 + TIMESTAMP(12) 皮秒精度**——DATE 仅日期，TIME 仅时间，TIMESTAMP 含两者。TIMESTAMP(12) 支持皮秒级精度（12 位小数秒）。对比 PostgreSQL（TIMESTAMP 最大微秒精度）和 BigQuery（TIMESTAMP 微秒精度），Db2 的皮秒精度在需要超高时间精度的场景中独特。 |
| [JSON](../types/json/db2.md) | **JSON_TABLE/JSON_VALUE（11.1+）+ BSON 存储**——BSON 格式以二进制存储 JSON 数据，查询性能优于纯文本。JSON_TABLE 遵循 SQL:2016 标准。对比 PostgreSQL 的 JSONB+GIN（二进制+索引，最强）和 Oracle 的 JSON 类型，Db2 的 JSON 支持较晚但遵循标准。 |
| [数值类型](../types/numeric/db2.md) | **DECFLOAT 十进制浮点（独有优势）+ INTEGER/DECIMAL 标准**——DECFLOAT(16)/DECFLOAT(34) 是 IEEE 754 十进制浮点，避免了 FLOAT/DOUBLE 的二进制精度问题，又比 DECIMAL 更灵活（浮动小数点）。对比 PostgreSQL 的 NUMERIC（定点十进制）和 BigQuery 的 NUMERIC（固定精度），Db2 的 DECFLOAT 是金融计算中精度与灵活性的最佳平衡。 |
| [字符串类型](../types/string/db2.md) | **VARCHAR/CLOB + CCSID 字符集管理**——CCSID（Coded Character Set Identifier）是 IBM 的字符集编码标识系统，支持 EBCDIC 和 Unicode 转换。大型机 z/OS 环境中 CCSID 管理至关重要。对比 PostgreSQL 的 UTF-8（默认编码）和 MySQL 的 utf8mb4/charset，Db2 的 CCSID 系统反映了大型机时代的字符集管理传统。 |
