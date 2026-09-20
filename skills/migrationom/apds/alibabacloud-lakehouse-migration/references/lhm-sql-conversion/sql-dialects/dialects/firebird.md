# Firebird

**分类**: 传统关系型数据库（InterBase 开源分支）
**文件数**: 51 个 SQL 文件
**总行数**: 4276 行

## 概述与定位

Firebird 是一款源自 Borland InterBase 6.0 开源代码的关系型数据库管理系统。它以"零管理"著称——单个数据库文件即可运行，无需专职 DBA，特别适合嵌入式应用、中小型业务系统与 ISV（独立软件供应商）分发场景。Firebird 同时提供嵌入式（Embedded）和客户端/服务器两种部署模式，是少数能在桌面应用到企业服务之间平滑切换的数据库。

## 历史与演进

- **2000 年**：Borland 将 InterBase 6.0 以开源许可发布，Firebird 社区随即分叉并独立开发。
- **2004 年**：Firebird 1.5 引入新的执行架构（Super Server / Classic Server 双模式），显著提升并发能力。
- **2008 年**：Firebird 2.1 支持全局临时表（Global Temporary Tables）、EXECUTE BLOCK、递归 CTE。
- **2012 年**：Firebird 2.5 引入完善的监控表（MON$* 系统表），可实时查看连接、事务与 SQL 统计。
- **2016 年**：Firebird 3.0 实现多线程 SuperServer、对称多处理（SMP）支持、包（Package）与窗口函数。
- **2023 年**：Firebird 4.0 增加 INT128/DECFLOAT 类型、时区支持、内联窗口帧、复制（Replication）功能。
- **2024 年**：Firebird 5.0 引入并行查询执行、多租户支持（Multi-tenancy）、改进的优化器统计。

## 核心设计思路

1. **MGA 架构**：采用多版本并发控制（Multi-Generational Architecture），每个事务看到一致的数据库快照，读不阻塞写。
2. **单文件数据库**：整个数据库存储在一个或少数几个文件中（.fdb/.gdb），便于备份、迁移和分发。
3. **嵌入式与服务器双模**：同一份数据库文件可被嵌入式库（fbembed）直接打开，也可通过网络服务端访问。
4. **SQL 标准导向**：Firebird 的 SQL 方言高度遵循 SQL 标准，PSQL（过程化 SQL）语法简洁且功能完备。

## 独特特色

| 特性 | 说明 |
|---|---|
| **EXECUTE BLOCK** | 在不创建存储过程的前提下，直接在客户端执行一段 PSQL 代码块，等同于匿名块。 |
| **Generators（序列）** | Firebird 的 Generator 是服务器级原子序列，通过 `GEN_ID()` / `NEXT VALUE FOR` 获取值，事务回滚不影响序列值。 |
| **FIRST/SKIP** | Firebird 早期分页语法，`SELECT FIRST 10 SKIP 20 ...`，先于 SQL 标准的 FETCH/OFFSET 实现。 |
| **UPDATE OR INSERT** | 原生的 upsert 语句，根据 MATCHING 子句自动判断更新或插入，语法比标准 MERGE 更简洁。 |
| **可选式触发器** | 触发器可同时绑定多个事件（BEFORE INSERT OR UPDATE OR DELETE），用一个触发器体处理多种操作。 |
| **PSQL 包（Package）** | 3.0+ 支持包头（Header）和包体（Body）分离，提供模块化封装与接口抽象。 |
| **监控虚拟表** | `MON$STATEMENTS`、`MON$TRANSACTIONS` 等虚拟表可实时查询当前 SQL 执行状态，无需外部工具。 |

## 已知不足

- **社区体量小**：相比主流数据库，Firebird 的用户社区与第三方生态（ORM、连接池、云托管）明显偏小。
- **分区表缺失**：至 5.0 仍无原生表分区功能，大表管理需依赖手动拆表或外部方案。
- **并行查询起步晚**：5.0 才引入并行查询执行，早期版本仅支持单线程查询。
- **JSON 支持有限**：Firebird 目前没有原生 JSON 数据类型，JSON 操作需通过 UDF 或字符串函数模拟。
- **集群与高可用**：原生复制功能（4.0+）仍相对基础，缺乏自动故障转移与读写分离的成熟方案。
- **云生态薄弱**：主流云平台未提供 Firebird 托管服务，部署和运维需自行管理。

## 对引擎开发者的参考价值

- **MGA 并发模型**：Firebird 的多版本实现比 PostgreSQL 更早成熟，其"记录级版本链"设计对嵌入式 MVCC 引擎有直接借鉴价值。
- **嵌入式部署架构**：单文件数据库 + 零配置运行的设计，是 DuckDB、SQLite 等嵌入式数据库的先行者。
- **EXECUTE BLOCK 实现**：在不注册持久对象的情况下执行过程化代码，其解析-编译-执行的管道设计值得参考。
- **Generator 的事务无关性**：序列值在事务回滚后不回收的设计，是实现全局唯一 ID 生成器的经典方案。
- **UPDATE OR INSERT 语义**：MATCHING 子句驱动的冲突检测逻辑比 MERGE 更轻量，对简化 upsert 实现有启发。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/firebird.md) | **嵌入式/服务器双模式 + 单文件数据库**——整个数据库存储在一个 .fdb 文件中，嵌入模式下无需服务器进程。IDENTITY（3.0+）支持 SQL 标准自增列。对比 SQLite（类似单文件嵌入式）和 PostgreSQL（需要服务器进程），Firebird 是少数同时支持嵌入式和 C/S 模式的完整 RDBMS。 |
| [改表](../ddl/alter-table/firebird.md) | **ALTER 标准，大部分操作在线执行**——ADD/DROP COLUMN、RENAME COLUMN（3.0+）支持。DDL 是事务性的（可回滚）。对比 PostgreSQL（DDL 事务性原生）和 MySQL（DDL 自动提交），Firebird 保持了 DDL 的事务安全。 |
| [索引](../ddl/indexes/firebird.md) | **B-tree 索引 + 表达式索引（3.0+）**——表达式索引支持在计算表达式上建索引（如 `CREATE INDEX idx ON t COMPUTED BY (UPPER(name))`）。对比 PostgreSQL（表达式索引早已支持）和 MySQL（表达式索引 8.0+），Firebird 在 3.0 版本补齐了这一能力。 |
| [约束](../ddl/constraints/firebird.md) | **PK/FK/CHECK/UNIQUE 完整 + 延迟约束（3.0+）**——DEFERRABLE 约束可在事务提交时才校验。对比 PostgreSQL（延迟约束原生支持）和 MySQL InnoDB（不支持延迟约束），Firebird 3.0 的延迟约束提升了复杂事务的灵活性。 |
| [视图](../ddl/views/firebird.md) | **普通视图 + 可更新视图，无物化视图**——可更新视图允许通过视图执行 INSERT/UPDATE/DELETE。对比 PostgreSQL（物化视图原生）和 MySQL（可更新视图类似），Firebird 缺少物化视图但可更新视图功能完整。 |
| [序列与自增](../ddl/sequences/firebird.md) | **Generator（传统）= SEQUENCE（SQL 标准别名）+ IDENTITY（3.0+）**——Generator 是 Firebird 的原始序列实现，通过 `GEN_ID(gen, 1)` 获取值；SEQUENCE 是 SQL 标准别名，通过 `NEXT VALUE FOR seq` 获取。**事务回滚不影响序列值**——这是全局唯一 ID 生成器的经典设计。对比 PostgreSQL 的 SERIAL/IDENTITY 和 Oracle 的 SEQUENCE，Firebird 的 Generator 是最早的事务无关序列实现之一。 |
| [数据库/Schema/用户](../ddl/users-databases/firebird.md) | **单 Schema（无多 Schema 支持）+ ROLE 权限**——整个数据库只有一个默认 Schema，无法创建额外命名空间。用户信息存储在 SEC$USERS 虚拟表中。对比 PostgreSQL（多 Schema 支持）和 MySQL（Database = Schema），Firebird 的单 Schema 设计是嵌入式定位的简化选择。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/firebird.md) | **EXECUTE STATEMENT 动态 SQL（PSQL 内）**——在 PSQL 存储过程中执行动态构建的 SQL 字符串。支持 WITH AUTONOMOUS TRANSACTION 在独立事务中执行。对比 PostgreSQL 的 EXECUTE（PL/pgSQL）和 Oracle 的 EXECUTE IMMEDIATE，Firebird 的 EXECUTE STATEMENT 功能类似但语法独特。 |
| [错误处理](../advanced/error-handling/firebird.md) | **WHEN ... DO 异常处理（PSQL）+ GDSCODE/SQLCODE**——`WHEN GDSCODE unique_key_violation DO ...` 捕获特定引擎错误码。支持 EXCEPTION 自定义异常。对比 PostgreSQL 的 EXCEPTION WHEN（按 SQLSTATE 捕获）和 Oracle 的 EXCEPTION WHEN（预定义异常名），Firebird 使用 GDSCODE（引擎特有错误码）作为异常标识。 |
| [执行计划](../advanced/explain/firebird.md) | **SET PLAN ON 显示执行计划**——PSQL 中设置后自动显示后续查询的执行计划。5.0+ 支持 EXPLAIN 语句。对比 PostgreSQL 的 EXPLAIN ANALYZE（即时输出+实际执行统计）和 MySQL 的 EXPLAIN，Firebird 的执行计划功能在持续完善中。 |
| [锁机制](../advanced/locking/firebird.md) | **MGA（Multi-Generational Architecture）——MVCC 先驱**。每条记录维护版本链，读事务看到一致快照，读不阻塞写。版本链存储在数据页中（与 PostgreSQL 的多版本元组类似）。对比 PostgreSQL（类似 MGA 但实现不同）和 Oracle（Undo Log MVCC），Firebird 的 MGA 是 MVCC 最早的成熟实现之一，比 PostgreSQL 的多版本更早。 |
| [分区](../advanced/partitioning/firebird.md) | **无分区支持**——至 5.0 仍无原生表分区。大表管理需手动拆表或通过视图联合多表。对比 PostgreSQL（声明式分区完整）和 MySQL（RANGE/LIST/HASH 分区），分区缺失是 Firebird 的主要限制之一。 |
| [权限](../advanced/permissions/firebird.md) | **GRANT/REVOKE 标准 + ROLE + 对象级权限精细控制**——支持对表、视图、存储过程、Generator 等对象的细粒度权限。ROLE 可嵌套授权。对比 PostgreSQL（RBAC 灵活）和 MySQL（权限模型较简单），Firebird 的权限体系标准且精细。 |
| [存储过程](../advanced/stored-procedures/firebird.md) | **PSQL 过程语言 + Selectable Stored Procedures（返回结果集）**——`SELECT * FROM my_procedure(:param)` 可将存储过程当作表查询，是 Firebird 独特的特性。**EXECUTE BLOCK** 支持匿名块执行（无需注册过程）。对比 PostgreSQL 的 RETURNS TABLE（类似表函数）和 Oracle 的 REF CURSOR，Firebird 的 Selectable SP 语法更直观。 |
| [临时表](../advanced/temp-tables/firebird.md) | **GTT 全局临时表（2.1+）+ ON COMMIT DELETE/PRESERVE**——ON COMMIT DELETE ROWS（事务级）或 ON COMMIT PRESERVE ROWS（会话级）。对比 PostgreSQL 的 CREATE TEMP TABLE 和 Oracle 的 GTT，Firebird 的 GTT 语义与 Oracle 一致。 |
| [事务](../advanced/transactions/firebird.md) | **MVCC 先驱——版本链存储 + 快照隔离**。Firebird 的 MGA 是数据库界最早的 MVCC 成熟实现之一。快照隔离保证每个事务看到一致的数据库状态。需注意：长事务会阻止旧版本回收（版本链增长），需定期清理。对比 PostgreSQL（VACUUM 处理死元组）和 Oracle（Undo 段自动管理），Firebird 的版本链需要关注 sweep 操作。 |
| [触发器](../advanced/triggers/firebird.md) | **BEFORE/AFTER 行级触发器 + Database 级触发器（DDL 事件）**——Database 级触发器可在 CONNECT/DISCONNECT/TRANSACTION START 等事件上触发，用于审计和安全。**多事件触发器**：一个触发器可同时绑定 INSERT OR UPDATE OR DELETE。对比 PostgreSQL（行级+语句级+事件触发器）和 MySQL（仅 BEFORE/AFTER 行级），Firebird 的 Database 级和多事件触发器是独特设计。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/firebird.md) | **DELETE 标准 + RETURNING（2.1+）**——RETURNING 返回被删除行数据，无需额外查询。对比 PostgreSQL（RETURNING 原生）和 Oracle（无 DELETE RETURNING），Firebird 较早引入了 RETURNING 特性。 |
| [插入](../dml/insert/firebird.md) | **INSERT ... RETURNING（2.1+）+ MERGE（3.0+）**——RETURNING 返回插入行数据（含 Generator 生成的 ID）。对比 PostgreSQL（INSERT RETURNING 原生）和 MySQL（需 LAST_INSERT_ID()），Firebird 的 RETURNING 在 Upsert 场景中特别有用。 |
| [更新](../dml/update/firebird.md) | **UPDATE ... RETURNING（2.1+）+ UPDATE OR INSERT（2.1+）**——UPDATE OR INSERT 是 Firebird 独有的 Upsert 语法，通过 MATCHING 子句指定冲突检测列。对比 PostgreSQL 的 ON CONFLICT（类似但语法不同）和 MySQL 的 ON DUPLICATE KEY UPDATE，Firebird 的 UPDATE OR INSERT 语法是最简洁的 Upsert 之一。 |
| [Upsert](../dml/upsert/firebird.md) | **UPDATE OR INSERT（2.1+，独有语法）+ MERGE（3.0+）**——`UPDATE OR INSERT INTO t (id, name) VALUES (1, 'x') MATCHING (id)` 根据 MATCHING 列自动判断更新或插入。MERGE（3.0+）遵循 SQL 标准。对比 PostgreSQL 的 ON CONFLICT（需指定约束名或列）和 MySQL 的 REPLACE INTO（先删后插语义不同），Firebird 的 UPDATE OR INSERT 以 MATCHING 子句驱动冲突检测，实现最轻量。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/firebird.md) | **LIST() 聚合（= STRING_AGG）+ 基本聚合完整**——`LIST(col, ',')` 拼接字符串，功能等价于 PostgreSQL 的 string_agg 和 BigQuery 的 STRING_AGG。无 GROUPING SETS/CUBE/ROLLUP（需多次查询 UNION 模拟）。对比 PostgreSQL（GROUPING SETS 完整）和 Oracle（LISTAGG），Firebird 的 LIST 命名独特但高级聚合缺失。 |
| [条件函数](../functions/conditional/firebird.md) | **CASE/COALESCE/NULLIF + IIF（2.0+）**——IIF(condition, true_val, false_val) 是三元条件函数（类似 SQL Server 的 IIF）。对比 MySQL 的 IF（类似功能）和 PostgreSQL（无 IIF，需用 CASE），Firebird 的 IIF 是便捷的条件表达式。 |
| [日期函数](../functions/date-functions/firebird.md) | **DATEADD/DATEDIFF + EXTRACT 标准**——`DATEADD(3 MONTH TO date_col)` 语法清晰。DATEDIFF(DAY, start, end) 计算间隔。对比 PostgreSQL 的 INTERVAL 算术（更灵活）和 Db2 的 Labeled Durations（更自然），Firebird 的日期函数命名直观。 |
| [数学函数](../functions/math-functions/firebird.md) | **完整数学函数**——MOD/CEIL/FLOOR/ROUND/POWER/SQRT/LOG/LN 标准集合。4.0+ 增加了 INT128/DECFLOAT 类型的高精度数学运算。对比各主流引擎数学函数基本一致。 |
| [字符串函数](../functions/string-functions/firebird.md) | **\|\| 拼接 + SUBSTRING/POSITION/TRIM 标准**——遵循 SQL 标准命名（SUBSTRING 而非 SUBSTR，POSITION 而非 INSTR）。对比 PostgreSQL（标准命名相同）和 Oracle（INSTR/SUBSTR 命名），Firebird 的字符串函数严格遵循 SQL 标准。 |
| [类型转换](../functions/type-conversion/firebird.md) | **CAST 标准，无 TRY_CAST**——转换失败时直接报错。对比 SQL Server 的 TRY_CAST（失败返回 NULL）和 BigQuery 的 SAFE_CAST（失败返回 NULL），Firebird 缺少安全转换函数，需在应用层处理异常。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/firebird.md) | **WITH + 递归 CTE（2.1+，早期支持）**——Firebird 是较早支持递归 CTE 的数据库之一。对比 PostgreSQL（WITH RECURSIVE 较早支持）和 MySQL 8.0（CTE 较晚引入），Firebird 在 CTE 支持上有时间优势。 |
| [全文搜索](../query/full-text-search/firebird.md) | **无内置全文搜索**——需依赖外部搜索引擎或 UDF 扩展。对比 PostgreSQL 的 tsvector+GIN（内置最成熟）和 MySQL 的 InnoDB FULLTEXT，全文搜索缺失是 Firebird 的明显短板。 |
| [连接查询](../query/joins/firebird.md) | **JOIN 完整（INNER/LEFT/RIGHT/FULL）+ NATURAL JOIN**——所有标准 JOIN 类型支持。无 LATERAL（需用关联子查询替代）。对比 PostgreSQL（LATERAL 支持）和 MySQL 8.0（LATERAL 支持），Firebird 缺少 LATERAL 但标准 JOIN 完整。 |
| [分页](../query/pagination/firebird.md) | **FIRST/SKIP（独有语法）+ FETCH FIRST/OFFSET（3.0+）**——`SELECT FIRST 10 SKIP 20 * FROM t` 是 Firebird 早期独有的分页语法，先于 SQL 标准的 FETCH/OFFSET。3.0+ 同时支持标准 `OFFSET 20 ROWS FETCH FIRST 10 ROWS ONLY`。对比 MySQL 的 LIMIT/OFFSET 和 Db2 的 FETCH FIRST（SQL 标准源头），Firebird 提供新旧两种分页语法。 |
| [行列转换](../query/pivot-unpivot/firebird.md) | **无原生 PIVOT**——需使用 CASE+GROUP BY 手动实现。对比 Oracle（PIVOT 原生）和 BigQuery（PIVOT 原生），Firebird 缺少行列转换语法糖。 |
| [集合操作](../query/set-operations/firebird.md) | **UNION/INTERSECT/EXCEPT 完整**——ALL/DISTINCT 修饰符支持。对比 PostgreSQL（集合操作完整）和 MySQL 8.0（INTERSECT/EXCEPT 较新），Firebird 的集合操作功能完整。 |
| [子查询](../query/subquery/firebird.md) | **关联子查询 + IN/EXISTS 标准**——优化器支持子查询展开。对比 PostgreSQL（优化器更成熟）和 MySQL 8.0（子查询优化改善），Firebird 的子查询优化能力在持续提升中。 |
| [窗口函数](../query/window-functions/firebird.md) | **完整窗口函数（3.0+）+ ROWS/RANGE 帧**——ROW_NUMBER/RANK/DENSE_RANK/LAG/LEAD/NTILE 全面支持。4.0+ 增加了内联窗口帧增强。对比 PostgreSQL（窗口函数 8.4+ 支持）和 MySQL 8.0（窗口函数同期引入），Firebird 3.0 的窗口函数引入是重大升级。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/firebird.md) | **递归 CTE 生成日期序列**——无 generate_series 内置函数，需用递归 CTE 逐日生成日期序列。对比 PostgreSQL 的 generate_series（更简洁）和 Db2（同为递归 CTE），Firebird 方案通用但较冗长。 |
| [去重](../scenarios/deduplication/firebird.md) | **ROW_NUMBER（3.0+）+ CTE 去重**——3.0 之前需用子查询和 MIN/MAX 替代。对比 PostgreSQL 的 DISTINCT ON（更简洁）和 BigQuery 的 QUALIFY（最简洁），Firebird 使用通用去重方案。 |
| [区间检测](../scenarios/gap-detection/firebird.md) | **窗口函数（3.0+）+ 递归 CTE**——递归 CTE 生成参考序列，LAG/LEAD 窗口函数比较相邻行。3.0 之前版本受限于无窗口函数。对比 PostgreSQL 的 generate_series（更直接）和 BigQuery 的 GENERATE_DATE_ARRAY，Firebird 的方案功能等价但较复杂。 |
| [层级查询](../scenarios/hierarchical-query/firebird.md) | **递归 CTE（2.1+）**——Firebird 较早支持递归 CTE，是层级查询的唯一选择（无 CONNECT BY）。对比 Oracle（CONNECT BY + 递归 CTE）和 PostgreSQL（仅递归 CTE），Firebird 在递归层级查询上有早期实践经验。 |
| [JSON 展开](../scenarios/json-flatten/firebird.md) | **无原生 JSON 支持（5.0+ 计划中）**——当前需将 JSON 存储为字符串，通过 UDF 或应用层解析。对比 PostgreSQL 的 JSONB+GIN（最强 JSON 支持）和 MySQL 8.0（JSON 类型原生），JSON 缺失是 Firebird 的重要功能短板。 |
| [迁移速查](../scenarios/migration-cheatsheet/firebird.md) | **MGA/MVCC 先驱 + PSQL 过程语言 + 单文件部署是核心特色**。关键差异：单文件数据库便于分发和备份；EXECUTE BLOCK 匿名块独有；UPDATE OR INSERT 独有语法；FIRST/SKIP 分页独有；Generator 事务无关；无分区表；无 JSON；社区和生态较小。 |
| [TopN 查询](../scenarios/ranking-top-n/firebird.md) | **ROW_NUMBER（3.0+）+ FIRST/SKIP**——`SELECT FIRST 10 * FROM t ORDER BY col DESC` 是 Firebird 独有的简洁 TopN 语法。3.0+ 也支持标准 FETCH FIRST。对比 MySQL 的 LIMIT 和 PostgreSQL 的 LIMIT，Firebird 的 FIRST/SKIP 语法虽独特但功能等价。 |
| [累计求和](../scenarios/running-total/firebird.md) | **SUM() OVER（3.0+）**——3.0 引入窗口函数后才支持标准累计求和。3.0 之前需用关联子查询模拟（性能差）。对比各主流引擎写法一致，Firebird 3.0 补齐了窗口函数能力。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/firebird.md) | **MERGE（3.0+）+ UPDATE OR INSERT**——UPDATE OR INSERT 是 Firebird 独有的简洁 Upsert 实现 SCD Type 1。MERGE（3.0+）支持标准的多条件分支。对比 PostgreSQL 的 ON CONFLICT 和 Oracle 的 MERGE，Firebird 的 UPDATE OR INSERT 在简单 Upsert 场景下最简洁。 |
| [字符串拆分](../scenarios/string-split-to-rows/firebird.md) | **递归 CTE + SUBSTRING 模拟**——无内置 SPLIT 函数，需递归 CTE 逐段截取分隔符之间的子串。对比 PostgreSQL 的 string_to_array+unnest（一行搞定）和 BigQuery 的 SPLIT+UNNEST，Firebird 的字符串拆分方案最复杂。 |
| [窗口分析](../scenarios/window-analytics/firebird.md) | **完整窗口函数（3.0+）**——移动平均、排名、占比等分析场景全覆盖。4.0+ 增加了窗口帧增强和新函数。对比 PostgreSQL（窗口函数完整）和 MySQL 8.0（窗口函数同期），Firebird 3.0 的窗口函数引入使其分析能力大幅提升。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/firebird.md) | **无 ARRAY/STRUCT 列类型**——Firebird 不支持结构化列类型。需用多列或关联表替代。对比 PostgreSQL（ARRAY 原生）和 BigQuery（STRUCT/ARRAY 一等公民），Firebird 的类型系统较为简单。 |
| [日期时间](../types/datetime/firebird.md) | **DATE/TIME/TIMESTAMP 标准，无 INTERVAL 类型**——DATE 仅日期，TIME 仅时间，TIMESTAMP 含两者。4.0+ 增加了时区支持（TIMESTAMP WITH TIME ZONE）。无 INTERVAL 类型，日期算术用 DATEADD/DATEDIFF 函数。对比 PostgreSQL（INTERVAL 类型灵活）和 Oracle（INTERVAL 类型支持），Firebird 通过函数替代 INTERVAL 类型。 |
| [JSON](../types/json/firebird.md) | **无原生 JSON 支持（5.0+ 计划中）**——JSON 数据需存储为 VARCHAR/BLOB TEXT 并用外部工具解析。对比 PostgreSQL 的 JSONB（最强 JSON 支持）和 MySQL 8.0（JSON 原生），JSON 缺失是 Firebird 的重要限制。 |
| [数值类型](../types/numeric/firebird.md) | **SMALLINT/INTEGER/BIGINT/DECIMAL/FLOAT/DOUBLE 标准 + INT128/DECFLOAT（4.0+）**——4.0 引入 128 位整数（INT128）和 IEEE 754 十进制浮点（DECFLOAT），大幅提升数值精度。对比 Db2 的 DECFLOAT（功能类似）和 PostgreSQL 的 NUMERIC（任意精度），Firebird 4.0 在高精度数值上有显著提升。 |
| [字符串类型](../types/string/firebird.md) | **VARCHAR/CHAR/BLOB SUB_TYPE TEXT + 字符集声明**——每个列可独立指定字符集（如 `VARCHAR(100) CHARACTER SET UTF8`）。BLOB SUB_TYPE TEXT 存储大文本。对比 PostgreSQL 的 TEXT（无长度限制，UTF-8 默认）和 MySQL 的 utf8mb4，Firebird 的每列独立字符集声明提供了最细粒度的编码控制。 |
