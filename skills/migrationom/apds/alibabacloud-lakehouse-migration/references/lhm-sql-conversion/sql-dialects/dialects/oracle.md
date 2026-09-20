# Oracle

**分类**: 传统关系型数据库
**文件数**: 51 个 SQL 文件
**总行数**: 8199 行

> **关键人物**：[Larry Ellison](../docs/people/larry-ellison.md)（Oracle 创始人, 首个商业 SQL 数据库）

## 概述与定位

Oracle Database 是企业级关系型数据库的标杆，也是 SQL 语言实际演进的最大推动力。在 SQL 标准委员会讨论一个特性之前，Oracle 往往已经实现并在生产中验证了多年。窗口函数、物化视图、Flashback、多租户 — 这些后来被标准化或被其他数据库借鉴的功能，几乎都是 Oracle 先行。

Oracle 的定位极为明确：**为最苛刻的企业级工作负载提供最完善的功能集**。它的客户是银行、电信、政府 — 这些场景对数据一致性、高可用、安全合规的要求远超一般 Web 应用。Oracle 的许可费极高（按 CPU 核心计价），但对这些客户而言，数据库不可用一小时的损失远超许可费。

## 历史与演进

- **1977**: Larry Ellison、Bob Miner、Ed Oates 创立 Software Development Laboratories（后更名 Oracle）
- **1979**: Oracle V2 发布 — 第一个商业 SQL 关系型数据库（V1 从未发布）
- **1983**: Oracle V3 用 C 语言重写，实现跨平台可移植
- **1984**: Oracle V4 引入读一致性（Read Consistency）— 这是 Oracle MVCC 的起点
- **1988**: Oracle V6 引入行锁和 PL/SQL — 奠定了 Oracle 生态的两块基石
- **1992**: Oracle 7 引入存储过程、触发器、共享连接池
- **1999**: Oracle 8i — "i"代表 Internet，引入 Java VM、物化视图
- **2001**: Oracle 9i — 引入 Oracle RAC（Real Application Clusters）
- **2003**: Oracle 10g — "g"代表 Grid，引入 ASM（自动存储管理）、Flashback Database
- **2007**: Oracle 11g — 窗口函数增强、Result Cache、Real Application Testing
- **2013**: Oracle 12c — "c"代表 Cloud，引入多租户架构（CDB/PDB）、自增列（IDENTITY）
- **2018**: Oracle 18c/19c — 自治数据库概念，19c 成为长期支持版
- **2024**: Oracle 23ai — "ai"代表 AI，引入 AI Vector Search、JSON Relational Duality

Oracle 的版本命名史就是一部 IT 潮流史：Internet → Grid → Cloud → AI。

## 核心设计思路

**功能完备主义**：Oracle 的设计哲学是"如果某个功能有用，就在内核中实现它"。不依赖第三方扩展，不留给用户自己解决。这导致 Oracle 的功能集远超其他数据库，但也带来了极高的系统复杂度。

**PL/SQL 生态**：PL/SQL 不仅是一门存储过程语言，它是一个完整的应用开发平台。Package（包）将过程、函数、类型、常量封装为模块；自治事务允许在事务内部开启独立事务（审计日志的关键需求）；批量绑定（FORALL/BULK COLLECT）解决了逐行处理的性能问题。

**Undo-based MVCC**：Oracle 不像 PostgreSQL 那样在表中保留旧版本元组，而是将旧数据写入 Undo 表空间。读操作需要旧版本时，从 Undo 中重建。优点是表不会膨胀（无需 VACUUM），缺点是 Undo 空间耗尽时会报 `ORA-01555: snapshot too old`。

**Shared Pool 缓存**：SQL 语句解析结果缓存在共享池中，相同 SQL 文本可以复用执行计划。这是 Oracle 推荐使用绑定变量的根本原因 — 不同字面量导致硬解析，浪费 CPU 和共享池空间。

## 独特特色（其他引擎没有的）

- **`'' = NULL`**：Oracle 中空字符串等于 NULL，这与 SQL 标准和所有其他数据库都不同。这个 45 年的历史决定至今无法更改，因为无数应用依赖此行为
- **`CONNECT BY`**：层级查询的原创语法（`START WITH ... CONNECT BY PRIOR`），比标准 CTE 递归更早、对某些场景更简洁
- **PL/SQL Package**：将相关过程、函数、类型打包为一个逻辑单元，支持 public/private 可见性，是大型数据库应用架构的基石
- **自治事务（`PRAGMA AUTONOMOUS_TRANSACTION`）**：在事务内部开启独立事务，提交/回滚互不影响。审计日志的标准方案
- **Flashback 技术族**：Flashback Query（查询过去某时刻的数据）、Flashback Table（恢复误删的表）、Flashback Database（整库时间回退）— 基于 Undo 的时间旅行
- **物化视图（最完善实现）**：支持增量刷新（Fast Refresh）、Query Rewrite（优化器自动路由查询到物化视图），这两个能力其他数据库至今追赶
- **Bitmap 索引**：低基数列（性别、状态）的专用索引，多列交叉过滤时效率极高
- **`DECODE` 函数**：Oracle 版的 CASE 表达式，更紧凑但可读性争议大
- **DUAL 表**：单行单列的虚拟表，`SELECT sysdate FROM DUAL` — Oracle 的经典写法
- **`RATIO_TO_REPORT`**：窗口函数，直接计算占比，无需手写除法
- **`KEEP (DENSE_RANK FIRST/LAST)`**：在分组聚合中同时获取极值对应的其他列值
- **Virtual Private Database (VPD)**：在 SQL 解析层自动追加 WHERE 条件实现行级隔离，比 PostgreSQL RLS 更早、实现层次更深

## 已知的设计不足与历史包袱

- **`'' = NULL`**：这是 Oracle 最大的历史包袱。`LENGTH('') IS NULL` 为 true，`'' || 'abc' = 'abc'` — 空字符串在连接中消失。迁移到其他数据库时这是最大的痛点
- **不支持 DDL 回滚**：`CREATE TABLE` 是立即提交的，无法在事务中回滚。这一点不如 PostgreSQL
- **DUAL 表要求**：不能写 `SELECT 1+1`，必须写 `SELECT 1+1 FROM DUAL`（23ai 终于可以省略）
- **NUMBER 万能类型**：Oracle 的 NUMBER 类型不区分整数/浮点/定点，内部统一用变长十进制存储。灵活但牺牲了存储效率和计算性能
- **VARCHAR2 默认字节语义**：`VARCHAR2(100)` 默认是 100 字节而非 100 字符，中文可能只存 33 个。需要显式指定 `VARCHAR2(100 CHAR)`
- **许可证费用极高**：Enterprise Edition 按处理器核心收费，高级功能（RAC、Partitioning、In-Memory）需单独购买 Option Pack
- **客户端部署复杂**：历史上需要安装 Oracle Client / Instant Client，配置 tnsnames.ora。虽然近年简化了，但仍比 MySQL/PostgreSQL 的轻量客户端重得多
- **ALTER TABLE 限制**：不能直接缩短列长度、修改列类型的限制比其他数据库更多

## 兼容生态

Oracle 兼容性是中国国产数据库的主要赛道：
- **达梦（DM）**：中国最成熟的 Oracle 兼容数据库，政府/军工市场主导
- **人大金仓（KingbaseES）**：Oracle + PostgreSQL 双兼容模式
- **OceanBase Oracle 模式**：蚂蚁集团的分布式数据库，同时提供 MySQL 和 Oracle 兼容模式
- **GaussDB（华为）**：Oracle 兼容为主要目标之一
- **TDSQL（腾讯）**：部分 Oracle 兼容

Oracle 兼容生态的存在本身说明了一个问题：**Oracle 的锁定效应极强**，大量存量 PL/SQL 代码使迁移成本极高。

## 对引擎开发者的参考价值

- **标量子查询缓存**：Oracle 会缓存标量子查询的输入→输出映射，相同输入直接返回缓存结果。这对关联子查询的性能提升巨大，但其他数据库几乎都没实现
- **物化视图 Query Rewrite**：优化器自动检测查询是否可以从物化视图中回答，无需修改 SQL。这需要深入的查询等价性判断逻辑
- **Edition-Based Redefinition（EBR）**：在线应用升级方案 — 新旧版本代码通过"版本"隔离，同时运行。这是数据库领域独一无二的零停机升级设计
- **Flashback 架构**：基于 Undo 日志的时间旅行查询，不需要额外的历史表。这个设计对时态数据库和审计需求有极高参考价值
- **自适应游标共享（ACS）**：同一 SQL 根据绑定变量的不同值使用不同执行计划，解决了"绑定变量 vs. 执行计划偏斜"的经典矛盾
- **Result Cache**：SQL 结果集缓存在 SGA 中，DML 变更自动失效。这是数据库层面的查询缓存，比应用层缓存更精准

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/oracle.md) | **`''=NULL` 是 Oracle 最大的历史包袱**——空字符串等于 NULL，影响 LENGTH('')、字符串拼接等所有行为，迁移到任何其他数据库都是核心痛点。NUMBER 万能类型不区分整数/浮点/定点（灵活但牺牲存储效率）。IDENTITY(12c+) 终于替代了 SEQUENCE+触发器的自增方案。 |
| [改表](../ddl/alter-table/oracle.md) | **DDL 自动提交（隐式 COMMIT）不可回滚**——CREATE/ALTER/DROP 执行即生效（对比 PostgreSQL DDL 可在事务中回滚是最大优势）。列类型修改限制多——不能直接缩短列长度，有数据时类型变更受限。Edition-Based Redefinition（EBR）是 Oracle 独有的零停机升级方案。 |
| [索引](../ddl/indexes/oracle.md) | **Bitmap 索引是 Oracle 独有的低基数列专用索引**——性别、状态等少量不同值的列用 Bitmap 索引，多条件交叉查询效率极高（位运算 AND/OR）。函数索引成熟（对比 PG 的表达式索引功能相似）。IOT（索引组织表）将数据按主键物理排序存储（类似 SQL Server 聚集索引）。 |
| [约束](../ddl/constraints/oracle.md) | **延迟约束（DEFERRABLE INITIALLY DEFERRED）+ 不可见约束（INVISIBLE）是企业级约束管理最完善的实现**——延迟约束在事务结束时统一检查（解决循环外键），不可见约束可临时禁用检查而不删除。对比 PG 的 EXCLUDE 排斥约束（独有）和 BigQuery 的 NOT ENFORCED（仅作提示）。 |
| [视图](../ddl/views/oracle.md) | **物化视图 Fast Refresh + Query Rewrite 是业界最强实现**——增量刷新仅同步变更数据（需物化视图日志），Query Rewrite 让优化器自动将查询路由到物化视图（无需改 SQL）。对比 PG 的 REFRESH MATERIALIZED VIEW（手动全量刷新）和 BigQuery 的自动增量刷新（简单但灵活度不及 Oracle）。 |
| [序列与自增](../ddl/sequences/oracle.md) | **IDENTITY(12c+) 终于简化了自增列**——之前需 SEQUENCE+BEFORE INSERT 触发器（Oracle 特有的繁琐方案）。SEQUENCE 对象支持 CACHE/NOCACHE/CYCLE/ORDER 精细控制，缓存策略在 RAC 环境下尤为重要（跨实例序列号间隙）。对比 MySQL 的 AUTO_INCREMENT（最简方案）。 |
| [数据库/Schema/用户](../ddl/users-databases/oracle.md) | **多租户 CDB/PDB(12c+) 是数据库虚拟化的首创**——一个容器数据库（CDB）承载多个可插拔数据库（PDB），每个 PDB 逻辑隔离。VPD（Virtual Private Database）在 SQL 解析层自动追加 WHERE 条件实现行级隔离（比 PG 的 RLS 更早且实现层次更深）。对比 PG 的 Database.Schema 二级命名。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/oracle.md) | **EXECUTE IMMEDIATE + DBMS_SQL 双体系**——EXECUTE IMMEDIATE 简洁适合大多数场景，DBMS_SQL 支持动态列数的复杂场景。绑定变量文化深入——Oracle 的 Shared Pool 缓存执行计划要求必须用绑定变量避免硬解析。对比 MySQL 的 PREPARE/EXECUTE（冗长）和 PG 的 EXECUTE format()（安全引用更优雅）。 |
| [错误处理](../advanced/error-handling/oracle.md) | **EXCEPTION 命名异常 + RAISE_APPLICATION_ERROR 自定义错误码(-20000~-20999)**——命名异常（NO_DATA_FOUND、TOO_MANY_ROWS 等）可读性极强。RAISE_APPLICATION_ERROR 抛出自定义错误码和消息。对比 PG 的 EXCEPTION WHEN（功能相当）和 MySQL 的 DECLARE HANDLER（功能最弱），Oracle 过程式错误处理最成熟。 |
| [执行计划](../advanced/explain/oracle.md) | **DBMS_XPLAN + AWR + SQL Monitor 组成业界最强调优工具链**——DBMS_XPLAN.DISPLAY_CURSOR 显示实际执行计划，AWR 存储历史性能数据（对比 PG 的 pg_stat_statements 类似但功能弱），SQL Monitor 实时监控长查询的每个阶段。对比 BigQuery 无传统 EXPLAIN（通过 Console 查看），Oracle 的调优工具链深度无出其右。 |
| [锁机制](../advanced/locking/oracle.md) | **读永不阻塞写（Undo-based MVCC）**——读操作从 Undo 表空间重建旧版本，不需要加锁（对比 SQL Server 默认锁式并发读阻塞写）。无锁升级（对比 SQL Server 行→页→表锁自动升级）。代价是 ORA-01555: snapshot too old——Undo 空间耗尽时长事务读失败。对比 PG 的 VACUUM 回收死元组是不同的 MVCC 代价。 |
| [分区](../advanced/partitioning/oracle.md) | **分区类型业界最丰富**——RANGE/LIST/HASH/COMPOSITE（组合分区）/INTERVAL（自动创建新分区）/REFERENCE（外键关联分区）。但需单独购买 Partitioning Option（费用高昂）。对比 PG 的声明式分区（免费但类型较少）和 MySQL 分区键必须在主键中（最大限制）。 |
| [权限](../advanced/permissions/oracle.md) | **VPD（Virtual Private Database）+ Fine-Grained Auditing 是企业级权限最完善的实现**——VPD 在 SQL 解析层自动追加 WHERE 条件（对应用透明），FGA 记录特定列的访问审计。对比 PG 的 RLS（声明式策略更简洁）和 SQL Server 的 DENY（显式拒绝，Oracle 无对应机制）。 |
| [存储过程](../advanced/stored-procedures/oracle.md) | **PL/SQL Package 是数据库过程式编程的最高形态**——将过程、函数、类型、常量封装为模块，支持 public/private 可见性。BULK COLLECT/FORALL 批量绑定解决逐行处理的性能问题（10-100 倍提升）。自治事务（PRAGMA AUTONOMOUS_TRANSACTION）在事务内开启独立事务——审计日志的标准方案。对比 PG 无 Package、MySQL 过程化能力最弱。 |
| [临时表](../advanced/temp-tables/oracle.md) | **全局临时表（GTT）需预先定义结构（CREATE GLOBAL TEMPORARY TABLE）**——与其他数据库按需创建不同，Oracle GTT 是持久 Schema 对象，仅数据会话/事务级隔离。Private Temp Table(18c+) 终于支持按需创建但来得太晚。对比 PG 的 CREATE TEMP TABLE（无需预定义）和 SQL Server 的 #temp（存 tempdb）。 |
| [事务](../advanced/transactions/oracle.md) | **无显式 BEGIN——DML 语句自动开启事务**（对比 PG/MySQL/SQL Server 需 BEGIN 或依赖自动提交）。自治事务（PRAGMA AUTONOMOUS_TRANSACTION）是 Oracle 独有——在事务内开启独立子事务。Flashback 技术族实现时间旅行查询。仅支持 READ COMMITTED 和 SERIALIZABLE（对比 PG 的 SSI 无锁可串行化更先进）。 |
| [触发器](../advanced/triggers/oracle.md) | **COMPOUND 触发器(11g+) 统一了行级和语句级触发逻辑**——BEFORE STATEMENT/BEFORE EACH ROW/AFTER EACH ROW/AFTER STATEMENT 四个时机在一个触发器体中定义，解决了 mutating table 问题。INSTEAD OF 触发器用于可更新视图。对比 PG 触发器完整但无 COMPOUND、MySQL 仅支持行级触发器。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/oracle.md) | **Flashback Table 可恢复误删的表**——`FLASHBACK TABLE t TO BEFORE DROP` 从回收站恢复（对比 PG/MySQL 无此安全网）。TRUNCATE+REUSE STORAGE 保留空间避免重新分配。Flashback Query 可查询删除前的数据。对比 SQL Server 的 Temporal Tables（自动历史版本）和 BigQuery 的 Time Travel（7 天快照）。 |
| [插入](../dml/insert/oracle.md) | **INSERT ALL 多表插入是 Oracle 独有**——一条 INSERT 同时写入多张表（条件分发或无条件全写）。Direct-Path INSERT `/*+ APPEND */` 跳过 Buffer Cache 直接写入数据文件（批量加载性能极佳但产生排他锁）。对比 PG 的 COPY 命令（批量加载最快方式）和 MySQL 的 LOAD DATA INFILE。 |
| [更新](../dml/update/oracle.md) | **MERGE 语句提供最完善的更新能力**——WHEN MATCHED/WHEN NOT MATCHED 多分支，支持 DELETE 子句（匹配后删除）。可更新 JOIN 视图——通过视图直接 UPDATE 底层表（有键保留约束）。对比 PG 的 UPDATE...FROM（语法简洁）和 MySQL 的 UPDATE JOIN（直觉式但非标准）。 |
| [Upsert](../dml/upsert/oracle.md) | **MERGE 是 Oracle 首创(9i)，功能业界最完整**——支持 WHEN MATCHED THEN UPDATE/DELETE、WHEN NOT MATCHED THEN INSERT 多分支，可在单语句中实现复杂的 CDC 逻辑。对比 PG 的 ON CONFLICT(9.5+)（更简洁但功能较少）、MySQL 的 ON DUPLICATE KEY UPDATE（仅基于唯一索引）和 SQL Server 的 MERGE（有已知竞态条件 Bug）。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/oracle.md) | **KEEP(DENSE_RANK FIRST/LAST) 是 Oracle 独有的聚合语法**——在分组聚合中同时获取极值对应的其他列值，无需子查询。LISTAGG(11g+) 字符串聚合（对比 MySQL 的 GROUP_CONCAT 有截断陷阱、PG 的 string_agg）。统计聚合函数丰富（REGR_*、CORR、STDDEV 等），适合分析场景。 |
| [条件函数](../functions/conditional/oracle.md) | **DECODE 是 Oracle 经典的条件函数**——`DECODE(col, val1, result1, val2, result2, default)` 比 CASE 更紧凑但可读性争议大。NVL2(expr, not_null_val, null_val) 比 CASE WHEN IS NULL 简洁。LNNVL 用于 WHERE 子句处理 NULL 三值逻辑。对比 MySQL 的 IF()（简洁非标准）和 SQL Server 的 IIF(2012+)。 |
| [日期函数](../functions/date-functions/oracle.md) | **日期格式依赖 NLS_DATE_FORMAT 会话设置是重大隐患**——`TO_CHAR(sysdate)` 的输出因环境而异，生产环境必须显式指定格式串。隐式转换（字符串自动转日期）是性能和正确性的双重大坑。对比 PG 的 INTERVAL 运算符（更自然）和 BigQuery 的 DATE_TRUNC/DATE_DIFF（标准函数名）。 |
| [数学函数](../functions/math-functions/oracle.md) | **NUMBER 内部十进制运算无精度丢失**——Oracle 的 NUMBER 类型使用变长十进制存储，金融计算不会出现 IEEE 754 浮点误差。代价是计算性能低于原生二进制浮点。对比 PG 的 NUMERIC（任意精度，类似实现）和 BigQuery 的 NUMERIC(38,9)（固定精度但够用）。 |
| [字符串函数](../functions/string-functions/oracle.md) | **`''=NULL` 在字符串操作中处处是坑**——`LENGTH('') IS NULL` 为 true、`'' \|\| 'abc' = 'abc'`（空字符串在拼接中消失）。这使得从其他数据库迁移到 Oracle（或反向）时字符串处理逻辑几乎都要重写。对比 PG/MySQL/SQL Server 中空字符串是独立于 NULL 的值。 |
| [类型转换](../functions/type-conversion/oracle.md) | **隐式类型转换多且不可控是 Oracle 的设计隐患**——`WHERE varchar2_col = 123` 可能将 varchar2_col 隐式转为数字导致索引失效（与 MySQL 同类问题）。TO_NUMBER/TO_DATE 格式串必须与数据精确匹配否则报错。对比 PG 的严格类型（不做隐式转换更安全）和 BigQuery 的 SAFE_CAST（失败返回 NULL）。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/oracle.md) | **WITH 子句 + `/*+ MATERIALIZE */` 提示控制 CTE 物化策略**——强制物化可避免重复执行代价高昂的子查询。递归 CTE 支持。对比 PG 12+ 的 MATERIALIZED/NOT MATERIALIZED 提示（功能相同但语法更标准）和 PG 的可写 CTE（Oracle 无法在 WITH 中执行 DML）。 |
| [全文搜索](../query/full-text-search/oracle.md) | **Oracle Text 是功能最完善的数据库内置全文搜索**——CONTAINS 支持布尔查询、NEAR 近邻搜索、FUZZY 模糊匹配、STEM 词干提取。但索引异步更新（需 CTX_DDL.SYNC_INDEX 或自动同步策略）。对比 PG 的 tsvector+GIN（同步更新但功能略少）和 MySQL 的 InnoDB FULLTEXT（功能基础）。 |
| [连接查询](../query/joins/oracle.md) | **旧式 `(+)` 外连接语法是 Oracle 最大的历史包袱之一**——应始终使用标准 LEFT/RIGHT JOIN。LATERAL(12c+) 和 CROSS APPLY(12c+) 终于支持关联表表达式（对比 SQL Server 2005 的 CROSS APPLY 更早、PG 9.3 的 LATERAL JOIN 更早）。支持所有标准 JOIN 类型。 |
| [分页](../query/pagination/oracle.md) | **12c 前分页需 ROWNUM 嵌套三层是经典痛点**——`SELECT * FROM (SELECT t.*, ROWNUM rn FROM (SELECT ... ORDER BY ...) t WHERE ROWNUM <= 20) WHERE rn > 10`。12c+ 终于支持标准 FETCH FIRST N ROWS ONLY / OFFSET M ROWS（对比 PG/MySQL 的 LIMIT/OFFSET 始终简洁）。 |
| [行列转换](../query/pivot-unpivot/oracle.md) | **原生 PIVOT/UNPIVOT(11g) 是业界最早引入此语法的数据库**——后被 SQL Server、BigQuery、DuckDB 等借鉴。PIVOT 需枚举值列表（不支持动态 PIVOT，需动态 SQL）。对比 DuckDB 的 PIVOT ANY（自动检测值）和 Snowflake 的 PIVOT 语法（简洁但功能接近）。 |
| [集合操作](../query/set-operations/oracle.md) | **用 MINUS 而非 SQL 标准 EXCEPT**——Oracle 的历史命名选择（功能完全相同）。UNION ALL/UNION DISTINCT、INTERSECT 完整。集合操作可嵌套括号控制执行顺序。对比 PG 的 EXCEPT（标准命名）和 MySQL 8.0.31 才支持 INTERSECT/EXCEPT（最晚）。 |
| [子查询](../query/subquery/oracle.md) | **标量子查询缓存是 Oracle 独有的优化**——缓存标量子查询的输入→输出映射，相同输入直接返回缓存结果，对关联子查询性能提升巨大。优化器自动展开关联子查询能力强。对比 PG 的优化器成熟度高但无此缓存机制、MySQL 5.x 子查询性能噩梦（8.0 修复）。 |
| [窗口函数](../query/window-functions/oracle.md) | **Oracle 8i 首创窗口函数（业界最早，1999 年）**——比 SQL:2003 标准更早。RATIO_TO_REPORT 直接计算占比（独有），KEEP(DENSE_RANK FIRST/LAST) 获取极值对应行值，IGNORE NULLS 选项跳过 NULL 值。对比 PG 8.4 支持（晚 9 年）、MySQL 8.0 支持（晚 15 年）。无 QUALIFY 子句（Teradata 首创）。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/oracle.md) | **无 generate_series，需 CONNECT BY LEVEL 模拟**——`SELECT DATE '2024-01-01' + LEVEL - 1 FROM DUAL CONNECT BY LEVEL <= 365`。语法不如 PG 的 generate_series 直观，但功能等价。对比 BigQuery 的 GENERATE_DATE_ARRAY（返回数组需 UNNEST）和 MariaDB 的 seq_1_to_N 序列引擎（最简洁）。 |
| [去重](../scenarios/deduplication/oracle.md) | **ROW_NUMBER + ROWID 直接定位物理行实现高效删除**——Oracle 的 ROWID 是行的物理地址，DELETE WHERE ROWID IN (...) 无需额外索引查找。对比 PG 的 DISTINCT ON（最简写法）和 BigQuery/DuckDB 的 QUALIFY ROW_NUMBER()（无需子查询包装）。 |
| [区间检测](../scenarios/gap-detection/oracle.md) | **窗口函数 LAG/LEAD + CONNECT BY LEVEL 填充完整序列**——CONNECT BY 生成期望序列后 MINUS 实际数据即可检测缺失。对比 PG 的 generate_series+LEFT JOIN（更直观）和 Teradata 的 sys_calendar 系统日历表（独有，无需生成）。 |
| [层级查询](../scenarios/hierarchical-query/oracle.md) | **CONNECT BY 是层级查询的原创语法（先于 SQL 标准递归 CTE）**——`START WITH parent IS NULL CONNECT BY PRIOR id = parent_id` 比递归 CTE 更简洁。SYS_CONNECT_BY_PATH 生成完整路径字符串（独有）。LEVEL 伪列表示当前深度。对比 PG 的递归 CTE+ltree 扩展和 SQL Server 的 hierarchyid 类型。 |
| [JSON 展开](../scenarios/json-flatten/oracle.md) | **JSON_TABLE(12c+) 是最早支持 SQL 标准 JSON 表函数的数据库**——将 JSON 数据转为关系表的功能在 2014 年即可用（对比 PG 17 才支持 JSON_TABLE）。Duality View(23ai) 是革命性设计——同一数据同时提供关系视图和 JSON 文档视图，读写互通。对比 PG 的 JSONB+GIN（索引最强）。 |
| [迁移速查](../scenarios/migration-cheatsheet/oracle.md) | **`''=NULL` + DDL 自动提交 + PL/SQL Package 依赖使迁移极难**——空字符串处理逻辑几乎全部需要重写，存储过程 Package 无法直接移植到任何其他数据库。CONNECT BY→递归 CTE、DECODE→CASE、NUMBER→具体类型 均需逐一转换。Oracle 的锁定效应在主流数据库中最强。 |
| [TopN 查询](../scenarios/ranking-top-n/oracle.md) | **FETCH FIRST N ROWS WITH TIES(12c+) 包含并列行**——12c 前需 ROWNUM 嵌套 `WHERE ROWNUM <= N`（仅适合不排序的简单场景），排序 TopN 需三层嵌套。对比 PG 13+ 的 WITH TIES、BigQuery/DuckDB 的 QUALIFY（最简洁，无需子查询）。 |
| [累计求和](../scenarios/running-total/oracle.md) | **窗口函数 + MODEL 子句可做更复杂的行间计算**——MODEL 子句是 Oracle 独有的电子表格式计算（将查询结果视为多维数组，可引用其他行的值）。SUM() OVER 标准累计求和。对比 PG（窗口函数完整但无 MODEL）和 BigQuery（无 MODEL 但 Slot 自动扩展）。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/oracle.md) | **MERGE 多分支 + Flashback 历史查询辅助验证**——MERGE 的 WHEN MATCHED THEN UPDATE/DELETE + WHEN NOT MATCHED THEN INSERT 覆盖 SCD Type 1/2/3 全部场景。Flashback Query 可回溯验证历史数据变更正确性。对比 SQL Server 的 Temporal Tables（自动历史版本）和 BigQuery 的 Time Travel（7 天快照）。 |
| [字符串拆分](../scenarios/string-split-to-rows/oracle.md) | **无原生 split 函数，需 CONNECT BY + REGEXP_SUBSTR 组合技巧**——`SELECT REGEXP_SUBSTR(str, '[^,]+', 1, LEVEL) FROM DUAL CONNECT BY LEVEL <= REGEXP_COUNT(str, ',')+1`。这是 Oracle 字符串拆分的经典写法但可读性差。对比 PG 14 的 string_to_table（一行搞定）、MySQL 的递归 CTE 方案同样繁琐。 |
| [窗口分析](../scenarios/window-analytics/oracle.md) | **窗口函数种类业界最多**——RATIO_TO_REPORT（直接算占比）、KEEP(DENSE_RANK FIRST/LAST)（极值对应行值）、IGNORE NULLS（跳过 NULL）均为 Oracle 独有。MODEL 子句做电子表格式行间引用计算（唯一无二）。对比 PG 的 FILTER+GROUPS 帧（独有维度不同）和 Teradata 的 QUALIFY（首创过滤窗口结果）。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/oracle.md) | **VARRAY + 嵌套表 + OBJECT TYPE 构成完整的 PL/SQL 集合类型体系**——VARRAY 固定大小数组，嵌套表（Nested Table）无限大小集合，OBJECT TYPE 支持面向对象的类型继承。但仅在 PL/SQL 中功能完整，SQL 层面使用不如 PG 的原生 ARRAY 或 BigQuery 的 STRUCT/ARRAY 直观。 |
| [日期时间](../types/datetime/oracle.md) | **DATE 类型含时间到秒级——这是 Oracle 最容易混淆的设计**——`DATE` 不是纯日期（对比 PG/MySQL/BigQuery 的 DATE 是纯日期），且默认显示格式受 NLS_DATE_FORMAT 控制（不同环境可能不同）。TIMESTAMP 精确到纳秒。INTERVAL YEAR TO MONTH 和 INTERVAL DAY TO SECOND 两种区间类型完善。 |
| [JSON](../types/json/oracle.md) | **JSON_TABLE 是 Oracle 最早的 SQL 标准 JSON 表函数实现(12c+)**——将 JSON 数据映射为关系行列。Duality View(23ai) 是革命性设计——同一数据同时提供关系视图和 JSON 文档视图，读写互通。对比 PG 的 JSONB+GIN（索引最强）和 Snowflake 的 VARIANT（半结构化更灵活）。 |
| [数值类型](../types/numeric/oracle.md) | **NUMBER 万能类型不区分整数/浮点/定点**——`NUMBER(10)` 整数、`NUMBER(10,2)` 定点、`NUMBER` 任意精度，统一用变长十进制存储。灵活但存储效率和计算性能低于专用类型（对比 PG 的 INT/BIGINT 固定宽度二进制存储更高效、BigQuery 只有 INT64 一种整数更极简）。 |
| [字符串类型](../types/string/oracle.md) | **`''=NULL` 是 Oracle 45 年的历史包袱**——空字符串等于 NULL 影响所有字符串操作（LENGTH/拼接/比较），迁移时几乎所有字符串逻辑需要重写。VARCHAR2(N) 默认字节语义——`VARCHAR2(100)` 是 100 字节不是 100 字符，中文可能只存 33 个，需显式 `VARCHAR2(100 CHAR)`。对比 PG 默认字符语义更安全。 |
