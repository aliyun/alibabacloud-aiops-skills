# 达梦 (DamengDB)

**分类**: 国产数据库（兼容 Oracle）
**文件数**: 51 个 SQL 文件
**总行数**: 4829 行

## 概述与定位

达梦数据库（DamengDB/DM）是武汉达梦数据库股份有限公司研发的国产商业关系型数据库，始于中国最早的数据库学术研究。达梦定位于替代 Oracle 的国产化场景，高度兼容 Oracle SQL 语法、PL/SQL 过程语言和数据字典视图。它是中国信创产业中份额领先的国产数据库之一，广泛应用于政府、金融、电力、交通等关键行业。

## 历史与演进

- **1988 年**：华中科技大学冯裕才教授启动中国第一个自主数据库研究项目。
- **2000 年**：达梦公司成立，将学术成果产品化。
- **2005 年**：DM4 发布，具备企业级 RDBMS 基本能力。
- **2010 年**：DM6 增强集群和高可用支持。
- **2014 年**：DM7 发布，全面引入 Oracle 兼容能力，支持 PL/SQL。
- **2019 年**：DM8 发布，引入列存、读写分离集群和分布式支持。
- **2022-2025 年**：随信创政策推进快速增长，持续完善分布式和云化能力。

## 核心设计思路

达梦采用单机为主的传统 RDBMS 架构，支持多种部署形态：单机、主备、读写分离集群（DM MPP Cluster）和数据守护（Data Guard）。SQL 引擎以 Oracle 兼容为首要目标，实现了 DMSQL 过程语言（兼容 PL/SQL）、包（Package）、同义词（Synonym）、DBLink 等 Oracle 核心特性。存储引擎支持行存和列存两种格式。安全方面通过了多项国家安全认证，支持透明数据加密和强制访问控制。

## 独特特色

- **Oracle 高度兼容**：支持 PL/SQL（DMSQL 方言）、Package、同义词、DBLink、MERGE INTO、序列和伪列（ROWNUM/ROWID）。
- **IDENTITY 列**：类似 SQL Server 的自增列语法 `IDENTITY(1, 1)`，也支持序列。
- **DMSQL 过程语言**：兼容 PL/SQL 的存储过程、函数、触发器和包。
- **兼容多种数据字典视图**：实现 DBA_TABLES、DBA_COLUMNS 等 Oracle 风格的系统视图。
- **达梦数据守护**：类似 Oracle Data Guard 的主备同步方案。
- **HUGE TABLE**：列存引擎用于分析型查询，支持 MPP 并行计算。
- **国密算法支持**：内置 SM2/SM3/SM4 国密加密算法。

## 已知不足

- 闭源商业软件，社区版功能受限，许可证费用较高。
- Oracle 兼容虽广但并非 100%，复杂 PL/SQL 程序迁移仍需调整。
- 生态工具和第三方驱动支持不如 MySQL/PostgreSQL 丰富。
- 分布式部署（DM MPP）的成熟度和易用性与专门的分布式数据库有差距。
- 国际化程度低，文档和社区以中文为主，海外几乎无用户基础。
- 性能调优工具和诊断能力相比 Oracle 原生产品仍有差距。

## 对引擎开发者的参考价值

达梦是中国持续时间最长的自主数据库项目，其 Oracle 兼容层的实现（从 SQL 语法到 PL/SQL 解释器到数据字典视图的完整复现）对理解数据库兼容性工程有重要参考。DMSQL 过程语言引擎的设计展示了如何在自研内核上兼容 PL/SQL 的控制流、异常处理和包机制。IDENTITY 与 SEQUENCE 并存的 ID 生成策略也体现了多方言兼容的设计取舍。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/dameng.md) | **Oracle 高度兼容的建表语法**——NUMBER/VARCHAR2/CLOB 类型体系完整复现，支持 IDENTITY(1,1) 自增列（借鉴 SQL Server 语法）与 SEQUENCE 双模式。''=NULL 行为继承自 Oracle——空字符串等价于 NULL，迁移时需注意。**HUGE TABLE** 列存引擎可在建表时指定，用于分析型查询。对比 Oracle 原生建表几乎 1:1 兼容，对比 PG/MySQL 类型映射需调整。 |
| [改表](../ddl/alter-table/dameng.md) | **DDL 自动提交**（同 Oracle）——ALTER TABLE 隐式提交当前事务，不可回滚。支持 ADD/MODIFY/DROP COLUMN，语法与 Oracle 一致。对比 PostgreSQL（DDL 可事务性回滚）和 MySQL（Online DDL），达梦保持了 Oracle 的 DDL 事务语义。 |
| [索引](../ddl/indexes/dameng.md) | **B-tree/Bitmap/函数索引三件套**——完整复现 Oracle 索引体系。Bitmap 索引适合低基数列的 OLAP 查询，函数索引支持基于表达式的加速。对比 PostgreSQL 的 GIN/GiST（更灵活）和 MySQL InnoDB（仅 B-tree+全文），达梦在索引类型丰富度上对齐 Oracle。 |
| [约束](../ddl/constraints/dameng.md) | **PK/FK/CHECK/UNIQUE 完整支持**，延迟约束（DEFERRABLE INITIALLY DEFERRED）可在事务提交时才校验。对比 Oracle（完整延迟约束）和 MySQL InnoDB（不支持延迟约束），达梦在约束行为上忠实复现 Oracle。 |
| [视图](../ddl/views/dameng.md) | **物化视图支持 REFRESH FAST/COMPLETE/ON COMMIT**——增量刷新需要物化视图日志（同 Oracle MV Log）。Calculation-free 视图定义与 Oracle 兼容。对比 PostgreSQL（REFRESH MATERIALIZED VIEW 手动，无增量）和 BigQuery（自动增量），达梦的物化视图在 Oracle 迁移场景下最平滑。 |
| [序列与自增](../ddl/sequences/dameng.md) | **SEQUENCE + IDENTITY 并存**——SEQUENCE 兼容 Oracle（CURRVAL/NEXTVAL 伪列），IDENTITY 兼容 SQL Server 语法 `IDENTITY(1,1)`。这种双模式设计使从 Oracle 或 SQL Server 迁移都相对顺畅。对比 PostgreSQL 的 SERIAL/IDENTITY 和 MySQL 的 AUTO_INCREMENT 单一模式。 |
| [数据库/Schema/用户](../ddl/users-databases/dameng.md) | **Schema = 用户**（同 Oracle）——创建用户即创建同名 Schema，用户拥有 Schema 内所有对象。支持多租户（Tablespace 隔离）。对比 PostgreSQL（Schema 与用户解耦）和 MySQL（Database = Schema），达梦的命名空间模型完全对齐 Oracle。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/dameng.md) | **EXECUTE IMMEDIATE 完整实现**——支持 USING 绑定变量和 INTO 输出变量，语法与 Oracle PL/SQL 一致。DMSQL 过程语言中可自由拼接动态 DDL/DML。对比 PostgreSQL 的 EXECUTE（PL/pgSQL，需 format() 拼接）和 SQL Server 的 sp_executesql。 |
| [错误处理](../advanced/error-handling/dameng.md) | **EXCEPTION WHEN ... THEN 异常处理**——支持预定义异常（NO_DATA_FOUND、TOO_MANY_ROWS 等）和自定义异常（RAISE_APPLICATION_ERROR），与 Oracle PL/SQL 异常模型一致。对比 PostgreSQL 的 EXCEPTION WHEN（PL/pgSQL，类似但异常码体系不同）和 SQL Server 的 TRY...CATCH。 |
| [执行计划](../advanced/explain/dameng.md) | **EXPLAIN 文本输出 + DM Performance Monitor 图形化工具**。支持查看索引使用、分区裁剪和并行执行信息。对比 Oracle 的 EXPLAIN PLAN + DBMS_XPLAN（功能最丰富）和 PostgreSQL 的 EXPLAIN ANALYZE（更直观），达梦的诊断工具在持续完善中。 |
| [锁机制](../advanced/locking/dameng.md) | **MVCC + 行级锁**（同 Oracle）——读不阻塞写，写不阻塞读。支持 SELECT FOR UPDATE 显式行锁。对比 Oracle（相同模型）和 PostgreSQL（MVCC 但实现不同：Oracle/达梦用 Undo Log，PG 用多版本元组），达梦的锁行为迁移自 Oracle 无缝衔接。 |
| [分区](../advanced/partitioning/dameng.md) | **RANGE/LIST/HASH 分区完整支持**——支持组合分区（如 RANGE-HASH）、间隔分区（INTERVAL）和自动列表分区。对比 Oracle（功能最完整，含 Reference 分区）和 PostgreSQL 10+（声明式分区，类型较少），达梦的分区实现在国产数据库中覆盖最广。 |
| [权限](../advanced/permissions/dameng.md) | **GRANT/REVOKE 标准权限 + 三权分立安全策略**——系统管理员(DBA)、安全管理员(SSO)、审计管理员(AUDITOR) 权限完全分离，这是国产数据库为满足等保要求的独特设计。对比 Oracle（DBA 角色权限集中）和 PostgreSQL（RBAC 灵活但无强制三权分立），达梦的安全模型在政企合规场景中有明确优势。 |
| [存储过程](../advanced/stored-procedures/dameng.md) | **DMSQL 过程语言完整兼容 PL/SQL**——支持 Package（包头+包体分离）、Cursor、BULK COLLECT、FORALL 批量操作。Oracle 存储过程迁移到达梦通常只需少量修改。对比 PostgreSQL 的 PL/pgSQL（缺少 Package 和 BULK COLLECT）和 MySQL（存储过程功能较弱），达梦在过程语言兼容度上仅次于 Oracle 本身。 |
| [临时表](../advanced/temp-tables/dameng.md) | **全局临时表（GTT）**——ON COMMIT DELETE ROWS（事务级）或 ON COMMIT PRESERVE ROWS（会话级），与 Oracle 语义一致。对比 PostgreSQL 的 CREATE TEMP TABLE（会话级，自动删除）和 SQL Server 的 #temp（局部临时表），达梦的 GTT 迁移自 Oracle 零改动。 |
| [事务](../advanced/transactions/dameng.md) | **MVCC + READ COMMITTED 默认隔离级别**（同 Oracle），DDL 自动提交。支持 SERIALIZABLE 隔离和 Savepoint。对比 Oracle（相同模型）和 PostgreSQL（READ COMMITTED 默认但 DDL 可回滚），达梦的事务行为是 Oracle 的忠实复现。 |
| [触发器](../advanced/triggers/dameng.md) | **BEFORE/AFTER/INSTEAD OF 触发器完整支持**——行级和语句级均可。支持 NEW/OLD 引用变化前后数据。对比 Oracle（完整模型）和 MySQL（仅 BEFORE/AFTER 行级），达梦的触发器兼容度对 Oracle 迁移友好。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/dameng.md) | **DELETE + TRUNCATE 标准支持**。TRUNCATE 不触发触发器且不可回滚（同 Oracle DDL 语义）。对比 PostgreSQL（TRUNCATE 可在事务中回滚）和 MySQL（TRUNCATE 重建表），达梦的 DELETE/TRUNCATE 行为与 Oracle 一致。 |
| [插入](../dml/insert/dameng.md) | **INSERT ALL/INSERT FIRST 多表条件插入**——一条语句将数据分发到多张表，Oracle 独有特性在达梦中完整实现。对比 PostgreSQL（无 INSERT ALL，需多条语句）和 MySQL（无对应功能），这是 Oracle 迁移的重要兼容点。 |
| [更新](../dml/update/dameng.md) | **UPDATE 标准语法**，支持子查询更新和关联 UPDATE。对比 Oracle（相同语法）和 PostgreSQL（UPDATE FROM 语法扩展），达梦与 Oracle 的 UPDATE 行为一致。 |
| [Upsert](../dml/upsert/dameng.md) | **MERGE INTO 完整实现**——WHEN MATCHED/NOT MATCHED/NOT MATCHED BY SOURCE 全支持，与 Oracle MERGE 语法一致。对比 PostgreSQL 的 ON CONFLICT（更简洁但功能不同）和 MySQL 的 ON DUPLICATE KEY UPDATE（仅基于唯一键），达梦的 MERGE 是 Oracle 用户的无缝迁移路径。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/dameng.md) | **LISTAGG + GROUPING SETS/CUBE/ROLLUP**——Oracle 风格的高级聚合完整支持。LISTAGG 实现字符串拼接聚合，GROUPING SETS 实现多维汇总。对比 PostgreSQL 的 string_agg（功能类似但名称不同）和 MySQL（8.0 才支持窗口函数），达梦在聚合函数覆盖上对齐 Oracle。 |
| [条件函数](../functions/conditional/dameng.md) | **DECODE/NVL/NVL2 三件套**——Oracle 特有的条件函数在达梦中完整可用，同时也支持标准 CASE/COALESCE。DECODE 在 Oracle 迁移中最常见，NVL2(expr, val_not_null, val_null) 比 COALESCE 更灵活。对比 PostgreSQL（无 DECODE/NVL，需改写为 CASE）和 MySQL 的 IFNULL。 |
| [日期函数](../functions/date-functions/dameng.md) | **TO_DATE/TO_CHAR 格式模型完整兼容 Oracle**——'YYYY-MM-DD HH24:MI:SS' 等格式字符串与 Oracle 一致。ADD_MONTHS/MONTHS_BETWEEN/LAST_DAY 等 Oracle 日期函数均可用。对比 PostgreSQL 的 to_date/to_char（格式模型相似但有差异）和 MySQL 的 DATE_FORMAT/STR_TO_DATE（不同的格式字符）。 |
| [数学函数](../functions/math-functions/dameng.md) | **Oracle 兼容数学函数体系**——MOD/CEIL/FLOOR/ROUND/TRUNC/POWER/SQRT 等。TRUNC 同时用于数值截断和日期截断（同 Oracle 双重用途）。对比 PostgreSQL（TRUNC 仅数值，日期用 date_trunc）和 MySQL（TRUNCATE 函数名不同）。 |
| [字符串函数](../functions/string-functions/dameng.md) | **\|\| 拼接运算符（Oracle 标准）**，需确认 **''=NULL 行为**——若继承 Oracle 语义则空字符串等于 NULL，`'' \|\| 'abc'` 返回 'abc' 而非 NULL。INSTR/SUBSTR/REPLACE/TRIM 函数名与 Oracle 一致。对比 PostgreSQL（''≠NULL，行为不同）和 MySQL（CONCAT 函数拼接），''=NULL 是 Oracle 迁移中最容易出错的差异点。 |
| [类型转换](../functions/type-conversion/dameng.md) | **CAST + TO_NUMBER/TO_DATE/TO_CHAR 三件套**——Oracle 风格的显式转换函数完整支持。隐式转换规则也尽可能对齐 Oracle（如字符串自动转数值）。对比 PostgreSQL 的 :: 运算符（更简洁）和 MySQL 的宽松隐式转换（更激进），达梦在类型转换行为上优先兼容 Oracle。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/dameng.md) | **WITH + 递归 CTE 支持**。递归 CTE 可替代 CONNECT BY 实现层级查询，但达梦同时保留了 CONNECT BY 语法。对比 Oracle（WITH RECURSIVE 和 CONNECT BY 并存）和 PostgreSQL（仅 WITH RECURSIVE），达梦在 CTE 层面与 Oracle 保持双路径兼容。 |
| [全文搜索](../query/full-text-search/dameng.md) | **内置全文索引引擎**——无需外部搜索服务即可实现中文和英文全文检索。对比 PostgreSQL 的 tsvector+GIN（最成熟的内置方案）和 Oracle Text（功能丰富但配置复杂），达梦的全文搜索在国产数据库中具备独立能力。 |
| [连接查询](../query/joins/dameng.md) | **完整 JOIN + Oracle 专有 (+) 外连接语法**——WHERE t1.id = t2.id(+) 等价于 LEFT JOIN，Oracle 遗留代码可直接运行。标准 INNER/LEFT/RIGHT/FULL/CROSS JOIN 均支持。对比 PostgreSQL（不支持 (+) 语法）和 MySQL（不支持 FULL JOIN），达梦在 JOIN 兼容性上覆盖最广。 |
| [分页](../query/pagination/dameng.md) | **ROWNUM（Oracle 兼容）+ LIMIT/OFFSET（扩展）双模式**——ROWNUM 伪列在 WHERE 中限制行数（Oracle 经典分页），同时支持更现代的 LIMIT/OFFSET 语法。对比 Oracle（仅 ROWNUM 和 FETCH FIRST）和 PostgreSQL（仅 LIMIT/OFFSET），达梦提供了最灵活的分页选择。 |
| [行列转换](../query/pivot-unpivot/dameng.md) | **PIVOT/UNPIVOT 原生支持**（Oracle 11g+ 兼容）——直接在 SQL 中进行行列转换，需要枚举 PIVOT 值。对比 PostgreSQL（需 crosstab 扩展函数）和 MySQL（无原生 PIVOT），达梦的 PIVOT 实现对 Oracle 迁移透明。 |
| [集合操作](../query/set-operations/dameng.md) | **UNION/INTERSECT/MINUS**——使用 MINUS 而非 EXCEPT（Oracle 命名传统），功能等价。对比 PostgreSQL/MySQL（使用 EXCEPT 关键字）和 Oracle（MINUS），达梦在集合操作命名上保持 Oracle 一致性。 |
| [子查询](../query/subquery/dameng.md) | **关联子查询 + 标量子查询**——优化器可将部分子查询转为 JOIN。支持 IN/EXISTS/NOT EXISTS/ANY/ALL 完整集合。对比 Oracle（相同能力）和 MySQL 5.x（子查询优化曾有性能问题，8.0 已修复），达梦的子查询优化水平持续提升中。 |
| [窗口函数](../query/window-functions/dameng.md) | **完整窗口函数（Oracle 兼容）**——ROW_NUMBER/RANK/DENSE_RANK/NTILE/LAG/LEAD 及 ROWS/RANGE 帧支持。对比 Oracle（窗口函数先驱，功能最全）和 MySQL 8.0（后来者，功能完整），达梦在窗口函数实现上对齐 Oracle 标准。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/dameng.md) | **CONNECT BY LEVEL 生成日期序列**（Oracle 经典手法）或递归 CTE——`SELECT LEVEL FROM DUAL CONNECT BY LEVEL <= 365` 生成连续整数再转日期。对比 PostgreSQL 的 generate_series（更直观）和 BigQuery 的 GENERATE_DATE_ARRAY，达梦保留了 Oracle 的层级查询生成方式。 |
| [去重](../scenarios/deduplication/dameng.md) | **ROW_NUMBER + ROWID 去重**——ROWID 伪列提供物理行标识（同 Oracle），可精确定位重复行并删除。对比 PostgreSQL 的 ctid（类似但不完全等价）和 MySQL 的无 ROWID（需自增列），Oracle 用户可直接复用去重模式。 |
| [区间检测](../scenarios/gap-detection/dameng.md) | **窗口函数 LAG/LEAD + CONNECT BY 辅助**——双路径检测数据间隙。CONNECT BY LEVEL 生成参考序列与实际数据比对。对比 PostgreSQL 的 generate_series + 窗口函数和 BigQuery 的 GENERATE_DATE_ARRAY，达梦的间隙检测灵活度高。 |
| [层级查询](../scenarios/hierarchical-query/dameng.md) | **CONNECT BY / 递归 CTE 双支持**——`START WITH ... CONNECT BY PRIOR parent_id = id` 是 Oracle 经典层级语法，达梦完整支持 LEVEL 伪列、SYS_CONNECT_BY_PATH、CONNECT_BY_ISLEAF。对比 PostgreSQL（仅递归 CTE）和 MySQL 8.0（仅递归 CTE），达梦在层级查询上兼容度最高。 |
| [JSON 展开](../scenarios/json-flatten/dameng.md) | **JSON_TABLE / JSON_VALUE / JSON_QUERY**——SQL:2016 标准 JSON 函数实现，可将 JSON 数组展开为关系行。对比 PostgreSQL 的 jsonb_array_elements（PG 特有函数）和 Oracle 12c+（相同标准函数），达梦的 JSON 处理遵循标准路径。 |
| [迁移速查](../scenarios/migration-cheatsheet/dameng.md) | **Oracle 迁移是达梦核心卖点**——PL/SQL 存储过程、Package、Synonym、DBLink、数据字典视图（DBA_TABLES 等）均可直接迁移或少量调整。关键差异：部分高级 PL/SQL 特性（如 Advanced Queuing）可能不完整；国密加密替代 Oracle 的标准加密。 |
| [TopN 查询](../scenarios/ranking-top-n/dameng.md) | **ROWNUM + ROW_NUMBER 双路径**——`WHERE ROWNUM <= N` 是 Oracle 经典 TopN（但需注意与 ORDER BY 的交互），ROW_NUMBER OVER(ORDER BY ...) 更精确。对比 PostgreSQL 的 LIMIT（更直观）和 MySQL 的 LIMIT（相同），达梦提供新旧两种方式。 |
| [累计求和](../scenarios/running-total/dameng.md) | **SUM() OVER(ORDER BY ...)** 标准窗口累计，Oracle 兼容实现。对比各主流引擎写法一致，达梦在窗口函数语义上无差异。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/dameng.md) | **MERGE INTO 实现 SCD Type 1/2**——WHEN MATCHED 更新当前记录，WHEN NOT MATCHED 插入新记录。对比 Oracle（相同 MERGE 语法）和 PostgreSQL 的 ON CONFLICT（更简洁但功能不同），达梦的 MERGE 在维度表维护上与 Oracle 等价。 |
| [字符串拆分](../scenarios/string-split-to-rows/dameng.md) | **CONNECT BY + REGEXP_SUBSTR 拆分字符串**——Oracle 经典模式 `REGEXP_SUBSTR(str, '[^,]+', 1, LEVEL)` 逐段提取。对比 PostgreSQL 的 string_to_array + unnest（更简洁）和 BigQuery 的 SPLIT + UNNEST，达梦保留了 Oracle 的正则拆分传统。 |
| [窗口分析](../scenarios/window-analytics/dameng.md) | **完整窗口函数**——移动平均、同环比、占比计算等分析场景全覆盖。ROWS/RANGE 帧规范与 Oracle 一致。对比 PostgreSQL（功能对等）和 MySQL 8.0（功能完整但无 QUALIFY），达梦窗口分析能力对齐 Oracle。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/dameng.md) | **VARRAY / 嵌套表（Nested Table）**——Oracle 风格的集合类型，可作为存储过程参数和表列使用。对比 PostgreSQL 的 ARRAY（原生更灵活）和 MySQL（无集合类型），达梦的集合类型主要为 Oracle PL/SQL 迁移服务。 |
| [日期时间](../types/datetime/dameng.md) | **DATE 类型含时间部分**（同 Oracle）——DATE 存储年月日时分秒，这与 SQL 标准（DATE 仅含日期）不同。TIMESTAMP 提供更高精度。对比 PostgreSQL（DATE 仅日期，TIMESTAMP 含时间）和 MySQL（DATE 仅日期），Oracle/达梦的 DATE 含时间是迁移中常见困惑点。 |
| [JSON](../types/json/dameng.md) | **JSON 类型 + JSON_TABLE/JSON_VALUE/JSON_QUERY**——遵循 SQL:2016 标准 JSON 函数。对比 PostgreSQL 的 JSONB（二进制存储 + GIN 索引，查询性能更强）和 Oracle 的 JSON（类似标准实现），达梦的 JSON 功能在持续完善中。 |
| [数值类型](../types/numeric/dameng.md) | **NUMBER(p,s) / INTEGER / DECIMAL**——NUMBER 是 Oracle 风格的统一数值类型，精度最高 38 位。对比 Oracle 的 NUMBER（相同语义）和 PostgreSQL 的 NUMERIC（功能等价但名称不同），达梦在数值类型上完全对齐 Oracle。 |
| [字符串类型](../types/string/dameng.md) | **VARCHAR / VARCHAR2 / CLOB**——VARCHAR2 是 Oracle 兼容类型名（与 VARCHAR 行为相同），CLOB 存储大文本。注意 ''=NULL 行为：若开启 Oracle 兼容模式则空字符串等于 NULL。对比 PostgreSQL 的 TEXT（无长度限制更简洁）和 MySQL 的 VARCHAR(n)（需指定长度），达梦同时支持 Oracle 和标准命名。 |
