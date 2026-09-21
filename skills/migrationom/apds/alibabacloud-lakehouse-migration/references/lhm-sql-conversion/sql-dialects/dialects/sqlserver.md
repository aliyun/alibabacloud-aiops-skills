# SQL Server

**分类**: 传统关系型数据库
**文件数**: 51 个 SQL 文件
**总行数**: 7792 行

> **关键人物**：[Jim Gray](../docs/people/sql-server-people.md)（图灵奖 1998）、[Pat Selinger](../docs/people/sql-server-people.md)（查询优化器）

## 概述与定位

SQL Server 是微软的企业级关系型数据库，也是 Windows 生态中数据库的默认选择。它的核心竞争力在于**与微软技术栈的深度集成** — .NET、Azure、Active Directory、SSIS/SSAS/SSRS、Visual Studio、Power BI。对于已经投入微软生态的企业，SQL Server 几乎是唯一合理的选择。

在技术层面，SQL Server 的优化器和执行引擎长期处于行业顶尖。它在某些领域甚至领先于 Oracle：Columnstore 索引（2012 年引入，早于 Oracle In-Memory）、In-Memory OLTP（Hekaton 引擎）、TRY_CAST/TRY_CONVERT（安全类型转换的先驱）。2017 年 SQL Server 登陆 Linux，标志着微软承认了开源和多平台的不可逆趋势。

## 历史与演进

- **1989**: 微软与 Sybase 合作在 OS/2 上发布 SQL Server 1.0
- **1993**: SQL Server 4.21 移植到 Windows NT，开始与 Sybase 分道扬镳
- **1996**: SQL Server 6.5 — 完全独立于 Sybase 的代码基
- **1998**: SQL Server 7.0 — 全新存储引擎，彻底重写
- **2000**: SQL Server 2000 — 成熟的企业级产品，XML 支持，联合数据库
- **2005**: SQL Server 2005 — 里程碑式重构：CLR 集成、SNAPSHOT 隔离、Service Broker、SSIS 取代 DTS、Management Studio 取代 Enterprise Manager
- **2008**: SQL Server 2008 — MERGE 语句、空间数据类型、数据压缩、Change Data Capture
- **2012**: SQL Server 2012 — Columnstore 索引（只读）、AlwaysOn AG、窗口函数增强（ROWS/RANGE）
- **2014**: SQL Server 2014 — In-Memory OLTP（Hekaton）、可更新 Columnstore
- **2016**: SQL Server 2016 — Temporal Tables、JSON 支持、Dynamic Data Masking、Row-Level Security、R 集成
- **2017**: SQL Server 2017 — **登陆 Linux**，Python 集成，Graph 查询
- **2019**: SQL Server 2019 — Intelligent Query Processing、Big Data Clusters、加速数据库恢复（ADR）
- **2022**: SQL Server 2022 — Ledger 表、GREATEST/LEAST/STRING_AGG、Azure 深度集成

SQL Server 的演进节奏清晰：每 2-3 年一个大版本，每个版本都有明确的主打特性。

## 核心设计思路

**T-SQL 过程语言**：Transact-SQL 是 SQL Server 的过程式扩展，与 Oracle 的 PL/SQL 对应。T-SQL 与标准 SQL 的偏离较大 — `IF...ELSE` 代替 `IF...THEN...END IF`，变量用 `@` 前缀声明，没有 `ELSIF`（需要嵌套 IF 或 CASE）。

**聚集索引=物理排序**：SQL Server 的表默认按聚集索引物理排序（堆表需要显式创建）。这意味着主键查询极快（等同于 InnoDB），但也意味着插入顺序不是物理顺序。与 PostgreSQL 的纯堆表模型形成鲜明对比。

**悲观并发（默认锁式隔离）**：SQL Server 默认的 READ COMMITTED 使用**锁**而非快照 — 读操作会加共享锁，读阻塞写、写阻塞读。这与 Oracle/PostgreSQL 的 MVCC 默认行为截然不同。要获得快照语义需要启用 RCSI（Read Committed Snapshot Isolation）。

**CROSS APPLY 创新**：SQL Server 2005 引入的 `CROSS APPLY` / `OUTER APPLY` 是对标准 `LATERAL JOIN` 的独立创新，允许右侧表表达式引用左侧表的列。这比 SQL:2003 标准的 LATERAL 更早被广泛使用。

## 独特特色（其他引擎没有的）

- **聚集索引（Clustered Index）**：表数据按聚集索引物理存储的架构，使 SQL Server 的主键范围扫描极快
- **`CROSS APPLY` / `OUTER APPLY`**：比 LATERAL JOIN 更早普及的关联表表达式，拆分 JSON、调用表值函数的标准手段
- **`OUTPUT` 子句**：INSERT/UPDATE/DELETE/MERGE 返回被影响的行，支持 `INSERTED` 和 `DELETED` 伪表（可同时获取修改前后的值）
- **`SET XACT_ABORT ON`**：错误自动回滚整个事务，避免部分提交。其他数据库需要手动处理
- **`TRY_CAST` / `TRY_CONVERT`**：转换失败返回 NULL 而非报错 — SQL Server 在安全类型转换上领先其他数据库多年
- **Temporal Tables（系统版本化时态表）**：自动记录行的历史版本，`FOR SYSTEM_TIME AS OF` 查询任意时间点数据
- **In-Memory OLTP（Hekaton）**：无锁、无 latch 的内存优化表和原生编译存储过程
- **Columnstore 索引**：列式存储与行式存储在同一引擎中共存，HTAP 的先驱实现
- **`DENY` 权限**：显式拒绝权限（优先级高于 GRANT），其他数据库只有 GRANT/REVOKE，缺少显式否定
- **Dynamic Data Masking**：列级数据脱敏，无需修改查询即可隐藏敏感数据
- **`GO` 批分隔符**：不是 SQL 语句而是客户端指令，将脚本分割为独立执行批次
- **`TOP` + `WITH TIES`**：`SELECT TOP 5 WITH TIES` 包含排名并列的额外行
- **`@@IDENTITY` / `SCOPE_IDENTITY()` / `@@ROWCOUNT`**：会话级别的元数据变量体系

## 已知的设计不足与历史包袱

- **默认锁式并发**：READ COMMITTED 默认用锁实现，读阻塞写、写阻塞读。新项目应始终启用 RCSI，但大量遗留系统未启用，导致阻塞和死锁频发
- **无 BEFORE 触发器**：只有 AFTER 和 INSTEAD OF 触发器，无法在操作前拦截并修改数据（Oracle/PostgreSQL 都有 BEFORE 触发器）
- **MERGE 有已知 Bug**：SQL Server 的 MERGE 语句有多个文档记录的竞态条件 Bug，微软多年未修复。生产环境中许多 DBA 建议避免使用 MERGE
- **`FORMAT()` 依赖 CLR 性能差**：`FORMAT(date, 'yyyy-MM-dd')` 内部调用 .NET CLR，性能比 `CONVERT` 差 10-50 倍
- **无 USING 子句**：JOIN 不支持 `USING(col)`，必须写完整的 `ON a.col = b.col`
- **`GREATEST` / `LEAST` 来得太晚**：2022 才加入，之前需要用 CASE 或 IIF 模拟
- **WINDOW 子句支持晚**：命名窗口定义（`WINDOW w AS (...)`) 支持较晚
- **字符串聚合晚到**：`STRING_AGG` 在 2017 才引入，之前需要 `FOR XML PATH` 的黑魔法
- **排序规则（Collation）混乱**：数据库级别的默认排序规则会影响字符串比较和索引行为，不同排序规则的列 JOIN 会报错
- **`datetime` 精度问题**：旧的 `datetime` 类型精度只有 3.33ms，必须用 `datetime2` 才有 100ns 精度

## 兼容生态

SQL Server 的兼容生态相对封闭：
- **Azure SQL Database**：SQL Server 的云托管版本，功能子集
- **Azure SQL Managed Instance**：更完整的云上 SQL Server，支持跨数据库查询
- **Azure Synapse Analytics**：SQL Server 方言的云数据仓库，MPP 架构
- **Amazon RDS for SQL Server**：AWS 上托管的 SQL Server 实例
- **Babelfish for Aurora PostgreSQL**：AWS 的 T-SQL 兼容层，运行在 PostgreSQL 之上 — 一个有趣的逆向兼容尝试

SQL Server 兼容生态窄的原因：T-SQL 与标准 SQL 的偏离度较大，且微软的许可模式不鼓励第三方兼容。

## 对引擎开发者的参考价值

- **锁升级机制**：SQL Server 的锁从行锁→页锁→表锁的自动升级策略是并发控制的经典实现。当单个事务锁定超过阈值（默认 5000 行）时自动升级，平衡了并发度和锁管理开销
- **Batch Mode 执行**：Columnstore 索引引入的批处理执行模式一次处理约 900 行而非逐行处理，CPU 效率提升 10-100 倍。2019 起 Batch Mode 可用于行存储表（Batch Mode on Rowstore）
- **RCSI / SNAPSHOT 隔离**：在传统锁式引擎上叠加 MVCC 的实现方案 — tempdb 作为版本存储。这展示了如何在不重写存储引擎的情况下添加快照隔离
- **Always Encrypted**：客户端加密、服务端无法解密的列级加密方案。密钥只在客户端驱动中存在，DBA 也无法看到明文。这是数据库安全的前沿设计
- **Intelligent Query Processing（IQP）**：自适应连接（Adaptive Join）、内存授予反馈（Memory Grant Feedback）、交错执行（Interleaved Execution）— SQL Server 2019 的查询优化器在运行时动态调整执行策略
- **Accelerated Database Recovery（ADR）**：基于持久化版本存储的快速恢复方案，将崩溃恢复时间从"与长事务成正比"降低到常数级别

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/sqlserver.md) | **聚集索引 = 物理排序是 SQL Server 的核心架构**——表数据按聚集索引物理存储（默认基于主键），主键范围扫描极快（对比 PG 的纯堆表模型需额外索引扫描）。IDENTITY 自增列。Temporal Tables(2016+) 自动记录行的历史版本——`FOR SYSTEM_TIME AS OF` 查询任意时间点数据，是 SCD 的内核级方案。 |
| [改表](../ddl/alter-table/sqlserver.md) | **DDL 不可回滚（与 Oracle 相同）**——CREATE/ALTER/DROP 执行即生效。在线索引重建、在线列添加等操作需 Enterprise Edition（标准版锁表）。对比 PG 的 DDL 事务性可回滚（最大优势），SQL Server 的 ALTER 在功能上较完整但缺乏原子性保障。 |
| [索引](../ddl/indexes/sqlserver.md) | **Columnstore 索引(2012+) 是列式存储在 OLTP 引擎中的先驱实现**——行存和列存在同一引擎中共存（HTAP 先驱），2019+ Batch Mode on Rowstore 将批处理执行扩展到行存表。Filtered Index（条件索引）类似 PG 的部分索引。INCLUDE 覆盖列避免回表查询。对比 PG 的 GiST/GIN/BRIN 框架（索引类型更丰富）。 |
| [约束](../ddl/constraints/sqlserver.md) | **WITH CHECK/NOCHECK 可暂停约束检查**——`ALTER TABLE t NOCHECK CONSTRAINT fk_name` 临时禁用外键检查（批量导入常用），但禁用后优化器不再信任约束信息（影响查询计划）。灵活但易被滥用导致数据质量问题。对比 PG 的 DEFERRABLE 约束（事务结束时检查）和 Oracle 的 DISABLE/ENABLE 约束（类似机制）。 |
| [视图](../ddl/views/sqlserver.md) | **Indexed View（索引视图）是 SQL Server 的物化视图实现**——视图上创建唯一聚集索引后自动维护物化数据。SCHEMABINDING 保护底层表结构不被随意修改。对比 Oracle 的物化视图（Fast Refresh+Query Rewrite 功能最强）和 PG 的 REFRESH MATERIALIZED VIEW（手动刷新，无自动维护）。 |
| [序列与自增](../ddl/sequences/sqlserver.md) | **IDENTITY + SEQUENCE(2012+) 双方案**——IDENTITY 绑定列（简单），SEQUENCE 独立对象可跨表共享。SCOPE_IDENTITY() 返回当前作用域的自增值（避免 @@IDENTITY 跨触发器混乱）。对比 PG 的 IDENTITY/SERIAL/SEQUENCE（三种选择更灵活）和 MySQL 的 AUTO_INCREMENT（最简但无独立 SEQUENCE）。 |
| [数据库/Schema/用户](../ddl/users-databases/sqlserver.md) | **DENY 显式拒绝权限是 SQL Server 独有**——DENY 优先级高于 GRANT，可精确阻止特定操作（对比 PG/Oracle 只有 GRANT/REVOKE 无显式否定）。Active Directory 集成身份验证（Windows 认证）实现单点登录。Database.Schema.Table 三级命名空间。Dynamic Data Masking(2016+) 列级数据脱敏无需改查询。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/sqlserver.md) | **sp_executesql 参数化查询是 T-SQL 动态 SQL 的推荐方式**——比 EXEC() 安全（支持参数绑定防注入，且可复用执行计划）。EXEC() 简单但无参数绑定，易导致 SQL 注入和硬解析。对比 Oracle 的 EXECUTE IMMEDIATE（更简洁）和 PG 的 EXECUTE format()（安全引用标识符）。 |
| [错误处理](../advanced/error-handling/sqlserver.md) | **TRY...CATCH 块是 T-SQL 错误处理的核心**——但 CATCH 块内不能直接 ROLLBACK 到 Savepoint（需配合 XACT_ABORT）。SET XACT_ABORT ON 使错误自动回滚整个事务（推荐始终开启）。对比 PG 的 EXCEPTION WHEN（可在块内回滚到 Savepoint）和 Oracle 的命名异常+RAISE_APPLICATION_ERROR（最成熟）。 |
| [执行计划](../advanced/explain/sqlserver.md) | **图形化执行计划是 SQL Server 的独特优势**——SSMS 中可视化查看每个算子的行数、成本、内存授予。Live Query Statistics(2016+) 实时监控正在执行的查询进度。对比 PG 的 EXPLAIN ANALYZE（文本+JSON，功能强但无内置图形化）和 Oracle 的 DBMS_XPLAN+SQL Monitor（工具链最深）。 |
| [锁机制](../advanced/locking/sqlserver.md) | **默认锁式并发（READ COMMITTED 用锁实现）是 SQL Server 最大的并发控制差异**——读阻塞写、写阻塞读（对比 PG/Oracle 的 MVCC 读永不阻塞写）。锁升级行→页→表（5000 行阈值自动升级）。WITH(NOLOCK) 脏读文化盛行但有数据不一致风险。推荐开启 RCSI（Read Committed Snapshot Isolation）获得快照语义。 |
| [分区](../advanced/partitioning/sqlserver.md) | **Partition Function + Partition Scheme 两步设计逻辑清晰**——Function 定义分区边界，Scheme 映射到文件组。但分区功能需 Enterprise Edition（标准版不可用，对比 PG/MySQL 免费）。对比 Oracle 分区类型最丰富（COMPOSITE/INTERVAL）和 BigQuery 的自动分区裁剪（无需管理）。 |
| [权限](../advanced/permissions/sqlserver.md) | **DENY 显式拒绝是 SQL Server 独有的权限机制**——DENY 优先级高于 GRANT，可精确阻止特定操作（对比 PG/Oracle 无 DENY，只能通过不 GRANT 来拒绝）。Dynamic Data Masking(2016+) 列级数据脱敏。Row-Level Security(2016+) 行级安全策略（对比 PG 的 RLS 更早但功能接近）。 |
| [存储过程](../advanced/stored-procedures/sqlserver.md) | **T-SQL 过程式编程功能完整**——变量 @var、IF/ELSE、WHILE 循环、游标、临时表。Natively Compiled 存储过程（Hekaton 引擎）将 T-SQL 编译为本机代码，性能极致但语法子集受限。对比 Oracle 的 PL/SQL Package（最强封装）和 PG 的多语言过程（PL/Python/PL/V8）。 |
| [临时表](../advanced/temp-tables/sqlserver.md) | **#temp 本地 + ##temp 全局 + 表变量 @t 三种临时数据方案**——#temp 存储在 tempdb（会话级可见），表变量 @t 存储在内存但统计信息弱（行数估算始终为 1）。tempdb 是 SQL Server 核心共享资源——高并发临时表操作可能产生 tempdb 争用。对比 PG 的 CREATE TEMP TABLE（无共享 tempdb 争用问题）。 |
| [事务](../advanced/transactions/sqlserver.md) | **SET XACT_ABORT ON 是 SQL Server 事务管理的第一条规则**——未开启时错误不自动回滚（部分提交），这是许多 Bug 的根源。默认锁式并发——强烈推荐开启 RCSI 获得快照读。对比 PG 的 SSI（无锁可串行化）和 Oracle 的 Undo-based MVCC（读永不阻塞写），SQL Server 并发模型需额外配置才能达到同等水平。 |
| [触发器](../advanced/triggers/sqlserver.md) | **无 BEFORE 触发器是 SQL Server 的重要限制**——只有 AFTER 和 INSTEAD OF 触发器（对比 PG/Oracle 支持 BEFORE 触发器可在操作前拦截修改）。INSTEAD OF 触发器用于可更新视图。INSERTED/DELETED 伪表可同时访问变更前后的数据。对比 PG 的事件触发器(9.3+) 可监控 DDL 操作。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/sqlserver.md) | **OUTPUT DELETED.* 返回被删除的行**——比 PG 的 RETURNING 更强大，可同时访问 DELETED 伪表。TOP(N) 限制每次删除行数（分批删除避免长事务），类似 MySQL 的 DELETE LIMIT。对比 Oracle 的 Flashback Table（误删恢复）方案不同——SQL Server 需依赖备份或 Temporal Tables。 |
| [插入](../dml/insert/sqlserver.md) | **OUTPUT INSERTED.* 返回插入后的行（含自增值）**——一步完成插入+获取自增 ID（对比 MySQL 的 LAST_INSERT_ID() 需额外调用）。BULK INSERT 从文件批量导入。对比 PG 的 INSERT...RETURNING（功能相似）和 Oracle 的 INSERT ALL 多表插入（独有）。 |
| [更新](../dml/update/sqlserver.md) | **OUTPUT INSERTED/DELETED 可同时获取更新前后值**——`OUTPUT DELETED.col AS old_val, INSERTED.col AS new_val` 一步完成审计。对比 PG 的 UPDATE...RETURNING 只能获取更新后值（无 DELETED 伪表），Oracle 的 MERGE 可配合 RETURNING 但语法更复杂。 |
| [Upsert](../dml/upsert/sqlserver.md) | **MERGE 有多个已知竞态条件 Bug（微软多年未修复）**——在高并发场景下可能出现唯一键冲突、幻读等问题。许多 SQL Server 专家建议生产环境避免使用 MERGE，改用 INSERT+UPDATE 组合。对比 PG 的 ON CONFLICT（实现可靠）和 Oracle 的 MERGE（首创且无已知 Bug），SQL Server 的 MERGE 是罕见的"官方承认有 Bug 但不修复"案例。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/sqlserver.md) | **STRING_AGG 直到 2017 才加入**——之前需用 `FOR XML PATH('')` 黑魔法拼接字符串（可读性极差）。GROUPING SETS/CUBE/ROLLUP 完整支持。无 FILTER 子句（对比 PG 的 `COUNT(*) FILTER(WHERE...)` 更优雅），需用 CASE WHEN 模拟条件聚合。对比 MySQL 的 GROUP_CONCAT（更早但有截断问题）。 |
| [条件函数](../functions/conditional/sqlserver.md) | **IIF(2012+) 是 T-SQL 简洁条件表达式**——`IIF(cond, true_val, false_val)` 比 CASE WHEN 更紧凑。CHOOSE(index, val1, val2, ...) 按位置选值（独有）。对比 MySQL 的 IF()（功能相同但更早）和 PG 坚持标准 CASE（无简洁替代）。COALESCE/NULLIF/ISNULL 标准支持。 |
| [日期函数](../functions/date-functions/sqlserver.md) | **DATEADD/DATEDIFF/EOMONTH 语义清晰**——函数式调用 `DATEADD(month, 3, date)` 明确指定单位（对比 PG 的 `+ INTERVAL '3 months'` 更自然）。FORMAT() 依赖 .NET CLR 性能比 CONVERT 差 10-50 倍——生产环境应避免 FORMAT()。EOMONTH 返回月末日期（独有便捷函数）。 |
| [数学函数](../functions/math-functions/sqlserver.md) | **GREATEST/LEAST 直到 2022 才加入**——之前需用 CASE WHEN 或 IIF 模拟（对比 PG/MySQL/Oracle 早已内置）。完整数学函数库。除零报错（对比 MySQL 返回 NULL）。对比 BigQuery 的 SAFE_DIVIDE（除零返回 NULL，独有安全语法）。 |
| [字符串函数](../functions/string-functions/sqlserver.md) | **STRING_SPLIT(2016+) 原生字符串拆分为行**——简洁但早期版本不保证顺序，enable_ordinal(2022+) 增加序号列。CONCAT_WS 自动跳过 NULL。TRANSLATE(2017+) 字符替换。`+` 用于字符串拼接（对比 PG/Oracle 用 `\|\|`、MySQL 用 CONCAT()），`+` 与 NULL 拼接结果为 NULL。 |
| [类型转换](../functions/type-conversion/sqlserver.md) | **TRY_CAST/TRY_CONVERT 是安全类型转换的先驱**——转换失败返回 NULL 而非报错，SQL Server 在此领域领先其他数据库多年。对比 BigQuery 的 SAFE_CAST（功能相同，命名不同）和 PG 至今无内置 TRY_CAST（需自定义函数包装异常）。CONVERT 支持格式化日期输出（style 参数）。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/sqlserver.md) | **WITH 标准 CTE + MAXRECURSION 防无限递归**——`OPTION (MAXRECURSION 100)` 限制递归深度（默认 100），防止死循环。对比 PG 的可写 CTE（INSERT/UPDATE/DELETE in WITH，SQL Server 不支持）和 MySQL 的 CTE（8.0 才引入，功能较基础）。 |
| [全文搜索](../query/full-text-search/sqlserver.md) | **CONTAINS/FREETEXT + Full-Text Index 提供内置全文搜索**——需配置 Full-Text Catalog 和填充索引。CONTAINS 支持布尔查询、近邻搜索、加权项。对比 PG 的 tsvector+GIN（无需独立 Catalog，集成更紧密）和 Oracle Text（功能最完善但异步更新）。 |
| [连接查询](../query/joins/sqlserver.md) | **CROSS APPLY / OUTER APPLY 比 SQL 标准的 LATERAL JOIN 更早普及**——2005 年引入（对比 PG 9.3/2013 的 LATERAL）。用于拆分 JSON、调用表值函数、Top-N-per-group。WITH(NOLOCK) 脏读提示文化盛行——性能换一致性，但可读到未提交数据。支持所有标准 JOIN 类型。 |
| [分页](../query/pagination/sqlserver.md) | **OFFSET...FETCH(2012+) 是 SQL 标准分页语法**——`ORDER BY col OFFSET 10 ROWS FETCH NEXT 10 ROWS ONLY`。TOP N WITH TIES 包含并列行（独有便捷语法）。2012 前需 ROW_NUMBER() 子查询嵌套。深分页性能问题与 PG/MySQL 相同——推荐 Keyset 分页。 |
| [行列转换](../query/pivot-unpivot/sqlserver.md) | **原生 PIVOT/UNPIVOT 语法**——列名需静态指定（不支持动态 PIVOT，需动态 SQL 拼接列名）。对比 Oracle 11g 最早引入 PIVOT、DuckDB 的 PIVOT ANY（自动检测值）和 Snowflake 的 PIVOT（功能类似但语法略不同）。PG 无原生 PIVOT（需 crosstab 扩展）。 |
| [集合操作](../query/set-operations/sqlserver.md) | **UNION/INTERSECT/EXCEPT 完整支持**——符合 SQL 标准（对比 Oracle 用 MINUS 而非 EXCEPT）。UNION ALL 无去重、EXCEPT ALL 保留重复项（完整 ALL 变体支持）。对比 MySQL 直到 8.0.31 才支持 INTERSECT/EXCEPT（最晚引入）。 |
| [子查询](../query/subquery/sqlserver.md) | **优化器自动展开关联子查询能力强**——Adaptive Join(2017+) 在运行时根据实际行数动态选择 Hash/Nested Loop（Intelligent Query Processing 的一部分）。对比 PG 优化器成熟度一直领先、Oracle 的标量子查询缓存（独有优化），SQL Server 的 IQP 是近年最大的优化器创新。 |
| [窗口函数](../query/window-functions/sqlserver.md) | **Batch Mode(2019+) 将窗口函数性能提升 2-10 倍**——一次处理约 900 行而非逐行处理。2012 版窗口函数大幅增强（ROWS/RANGE 帧）。无 NTH_VALUE 函数（对比 PG/Oracle 支持）、无 GROUPS 帧类型（PG 11+ 独有）、无 QUALIFY 子句（BigQuery/Snowflake/DuckDB 独有）。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/sqlserver.md) | **无 generate_series，需递归 CTE 或预建数字表模拟**——递归 CTE 生成日期序列（受 MAXRECURSION 限制，默认 100）。对比 PG 的 generate_series（原生最简洁）、BigQuery 的 GENERATE_DATE_ARRAY 和 MariaDB 的 seq_1_to_N 序列引擎。数字表方案性能更优但需预先维护。 |
| [去重](../scenarios/deduplication/sqlserver.md) | **ROW_NUMBER() + CTE DELETE 直接去重语法简洁**——`WITH cte AS (SELECT ROW_NUMBER() OVER(...) rn FROM t) DELETE FROM cte WHERE rn > 1` 直接在 CTE 上执行 DELETE（SQL Server 独有能力）。对比 PG 的 DISTINCT ON（最简写法）和 BigQuery/DuckDB 的 QUALIFY（无需子查询）。 |
| [区间检测](../scenarios/gap-detection/sqlserver.md) | **窗口函数 LAG/LEAD + 数字表填充**——用预建数字表（Numbers Table）生成完整序列后 EXCEPT 实际数据检测缺失。对比 PG 的 generate_series（无需维护数字表）和 Teradata 的 sys_calendar（系统日历表独有）。递归 CTE 也可用但受 MAXRECURSION 限制。 |
| [层级查询](../scenarios/hierarchical-query/sqlserver.md) | **递归 CTE + hierarchyid 数据类型是 SQL Server 的独有组合**——hierarchyid 以紧凑二进制格式编码层级路径，支持 GetAncestor()/IsDescendantOf() 方法，查询和存储效率都优于字符串路径。对比 Oracle 的 CONNECT BY（语法更简洁）和 PG 的 ltree 扩展（路径运算符）。 |
| [JSON 展开](../scenarios/json-flatten/sqlserver.md) | **OPENJSON + CROSS APPLY 展开 JSON 数组**——`CROSS APPLY OPENJSON(json_col)` 将 JSON 转为关系行。FOR JSON PATH 生成 JSON 输出。但 JSON 存为 NVARCHAR 无专用类型（对比 PG 的 JSONB 二进制存储+GIN 索引更高效）。对比 Oracle 的 JSON_TABLE（标准语法更早）和 Snowflake 的 FLATTEN（语法更简洁）。 |
| [迁移速查](../scenarios/migration-cheatsheet/sqlserver.md) | **T-SQL 偏离 SQL 标准大是迁移核心困难**——IF/ELSE 非标准、@变量前缀、GO 批分隔符、TOP 非标准分页。Collation 差异影响字符串比较和排序——不同 Collation 列 JOIN 报错。默认锁式并发行为与 PG/Oracle 的 MVCC 不同需适配。MERGE 有已知 Bug 需避免。 |
| [TopN 查询](../scenarios/ranking-top-n/sqlserver.md) | **TOP N WITH TIES 是 SQL Server 独有的便捷 TopN 语法**——包含并列行无需窗口函数。CROSS APPLY + ROW_NUMBER 实现分组 TopN（利用 APPLY 的关联表表达式能力）。对比 BigQuery/DuckDB 的 QUALIFY（最简洁无需子查询）和 PG 13+ 的 FETCH FIRST WITH TIES。 |
| [累计求和](../scenarios/running-total/sqlserver.md) | **Batch Mode(2019+) 将窗口函数性能提升 2-10 倍**——SUM() OVER 标准累计求和。2019 前行存表窗口函数性能较差（逐行处理），Batch Mode on Rowstore 彻底改变了这一局面。对比 PG 8.4 起即高效支持窗口函数、MySQL 8.0 才引入窗口函数。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/sqlserver.md) | **Temporal Tables(2016+) 是 SCD 的内核级最佳方案**——系统自动维护历史版本表，`FOR SYSTEM_TIME AS OF` 查询任意时间点数据。MERGE 语句可实现 SCD 但有已知 Bug（建议谨慎）。对比 Oracle 的 Flashback+MERGE（功能组合强大）和 BigQuery 的 MERGE+Time Travel（7 天限制）。 |
| [字符串拆分](../scenarios/string-split-to-rows/sqlserver.md) | **STRING_SPLIT(2016+) 原生字符串拆分为行**——简洁好用但早期版本不保证顺序。enable_ordinal(2022+) 增加序号列解决排序问题。对比 PG 14 的 string_to_table（功能相似）、MySQL 无原生拆分函数（需递归 CTE 最繁琐）。 |
| [窗口分析](../scenarios/window-analytics/sqlserver.md) | **Batch Mode(2019+) 大幅提升窗口函数性能**——ROW_NUMBER/RANK/LAG/LEAD/SUM OVER 均受益。GROUPS 帧类型和 NTH_VALUE 缺失（PG 11+ 独有）。无 QUALIFY 子句（BigQuery/Snowflake/DuckDB 独有）。无 FILTER 子句（PG 独有条件聚合）。整体窗口函数功能完整但在帧类型和语法糖上不及 PG。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/sqlserver.md) | **无原生数组/结构体类型**——需用 Table-Valued Parameter（TVP）传递表格数据到存储过程，或用 JSON 字符串模拟复合结构。对比 PG 的原生 ARRAY+运算符、BigQuery 的 STRUCT/ARRAY 一等公民、DuckDB 的 LIST/STRUCT/MAP——SQL Server 在复合类型上是主流数据库中最弱的。 |
| [日期时间](../types/datetime/sqlserver.md) | **旧 datetime 精度仅 3.33ms 是历史设计缺陷**——必须使用 datetime2（100ns 精度，范围 0001-9999 年）。datetimeoffset 带时区偏移。date/time 独立类型。对比 PG 的 TIMESTAMPTZ（微秒精度+自动时区转换）和 MySQL 的 DATETIME/TIMESTAMP（TIMESTAMP 有 2038 年问题）。 |
| [JSON](../types/json/sqlserver.md) | **JSON 存储为 NVARCHAR 无专用数据类型**——查询时需解析字符串，无法建立 JSON 专用索引（对比 PG 的 JSONB 二进制存储+GIN 索引性能远超）。OPENJSON 解析 JSON、JSON_VALUE/JSON_QUERY 提取值。FOR JSON PATH/AUTO 生成 JSON 输出。对比 MySQL 的 JSON（二进制存储但索引有限）和 BigQuery 的 JSON 类型(2022+)。 |
| [数值类型](../types/numeric/sqlserver.md) | **DECIMAL/NUMERIC 精确定点计算**——MONEY/SMALLMONEY 类型便捷（自动格式化货币符号）但有精度陷阱（乘除运算可能丢失精度，不如 DECIMAL 安全）。INT/BIGINT/SMALLINT/TINYINT 标准整数类型。对比 Oracle 的 NUMBER 万能类型（灵活但低效）和 PG 的 NUMERIC 任意精度（无上限）。 |
| [字符串类型](../types/string/sqlserver.md) | **Collation（排序规则）影响字符串比较、索引和排序**——不同 Collation 的列 JOIN 会报错，这是 SQL Server 独有的迁移痛点。VARCHAR(max)/NVARCHAR(max) 替代 TEXT/NTEXT（已废弃）。NVARCHAR 使用 UTF-16（对比 PG 的 UTF-8 默认），N 前缀字面量 `N'文字'` 是中文处理的常见遗漏。 |
