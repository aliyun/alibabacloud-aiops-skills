# DuckDB

**分类**: 嵌入式 OLAP
**文件数**: 51 个 SQL 文件
**总行数**: 4880 行

> **关键人物**：[Raasveldt & Mühleisen](../docs/people/duckdb-founders.md)（CWI, 2025 荷兰 ICT 奖）

## 概述与定位

DuckDB 是一款嵌入式列式分析数据库，常被称为"分析领域的 SQLite"。由 CWI（荷兰国家数学与计算机科学研究中心）的 Mark Raasveldt 和 Hannes Mühleisen 于 2018 年创建，DuckDB 以进程内嵌入方式运行——无需安装服务器、无需配置网络，直接作为库链接到 Python/R/Java/Node.js 应用中。它采用 PostgreSQL 兼容的 SQL 方言，并在此基础上引入了大量便利的语法糖，使交互式数据分析极为高效。

## 历史与演进

- **2018 年**：DuckDB 项目在 CWI 启动，目标是创建一个嵌入式 OLAP 数据库（对标 SQLite 之于 OLTP）。
- **2019 年**：DuckDB 0.1 发布，初步实现列式存储和向量化执行引擎。
- **2019 年**：DuckDB Labs 公司成立（CWI spin-off）。
- **2020 年**：0.2 版本增加 Parquet 读写、Python API 集成。
- **2021 年**：引入扩展（Extension）系统，支持 httpfs（远程文件读取）、spatial（地理空间）等扩展。
- **2022 年**：0.5+ 版本引入 PIVOT/UNPIVOT、GROUP BY ALL、COLUMNS(*) 等语法创新。
- **2023 年**：0.9 版本引入新的存储格式（v2）、增强并行执行、Iceberg/Delta Lake 扩展。
- **2024-2025 年**：1.0 稳定版发布，存储格式冻结，增强多线程、大于内存的数据集支持、社区扩展生态。

## 核心设计思路

1. **嵌入式进程内**：DuckDB 作为库运行在应用进程中，零网络开销、零配置部署，适合数据科学家、分析师和 CI/CD 管道。
2. **向量化引擎**：采用 Morsel-Driven Parallelism 的向量化执行模型，数据以 Vector（向量）为单位在算子间流动，充分利用 CPU 缓存。
3. **PostgreSQL 方言 + 语法糖**：基础 SQL 语法兼容 PostgreSQL，同时添加了大量分析友好的创新语法。
4. **外部数据直查**：可直接查询 CSV/Parquet/JSON 文件（本地或 S3），无需先导入，`SELECT * FROM 'data.parquet'` 即可工作。

## 独特特色

| 特性 | 说明 |
|---|---|
| **PIVOT / UNPIVOT** | 原生的行列转换语法，`PIVOT t ON year USING SUM(amount)` 比手写 CASE WHEN 简洁数倍。 |
| **GROUP BY ALL** | 自动将 SELECT 中非聚合列加入 GROUP BY，`SELECT dept, SUM(salary) FROM t GROUP BY ALL` 无需重复列出分组列。 |
| **COLUMNS(*)** | 对所有列或匹配的列批量应用表达式：`SELECT MIN(COLUMNS(*)) FROM t` 计算每列的最小值。 |
| **直接文件查询** | `SELECT * FROM 'file.parquet'` 或 `FROM read_csv('data.csv')` 直接查询外部文件，无需建表。 |
| **FROM-first 语法** | 支持 `FROM t SELECT col` 的语法顺序，以及省略 SELECT 的 `FROM t`（等价于 `SELECT * FROM t`）。 |
| **List/Struct/Map 类型** | 原生支持复合类型，`[1, 2, 3]` 为 LIST，`{'a': 1}` 为 STRUCT，配合 Lambda 函数进行元素级操作。 |
| **扩展系统** | 可通过 `INSTALL ext; LOAD ext;` 动态加载扩展（httpfs、spatial、postgres_scanner、sqlite_scanner 等）。 |

## 已知不足

- **单机限制**：DuckDB 是单进程数据库，不支持分布式查询和多节点扩展，数据规模受限于单机资源。
- **并发写入受限**：同一时刻仅支持一个写入连接（多读单写），不适合多用户并发写入场景。
- **无服务端模式**：不提供网络服务器，不能作为独立的数据库服务部署（需嵌入到应用中）。
- **存储过程缺失**：不支持存储过程和触发器，复杂的过程化逻辑需通过宿主语言（Python/Java 等）实现。
- **生态尚在发展**：虽然增长迅速，但与 PostgreSQL/MySQL 相比，企业级工具链（备份、监控、权限管理）仍不完善。

## 对引擎开发者的参考价值

- **Morsel-Driven Parallelism**：DuckDB 的论文级向量化执行模型——将数据切分为 Morsel（小批量），由多线程工作者动态获取并处理——是现代 OLAP 引擎并行执行的标杆实现。
- **语法创新（GROUP BY ALL / COLUMNS）**：展示了在不破坏标准兼容性的前提下通过语法糖大幅提升开发者体验的可能性，对 SQL 方言设计有重要参考。
- **嵌入式架构设计**：零配置、单文件存储、进程内运行的设计模式，对嵌入式数据库引擎的架构选型有直接参考。
- **外部数据直查管道**：将文件路径作为表引用直接解析的设计，简化了数据导入流程，对查询引擎的数据源抽象有启发。
- **扩展系统设计**：通过动态加载共享库扩展引擎功能（新数据源、新函数、新文件格式）的插件架构，对引擎的可扩展性设计有参考价值。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/duckdb.md) | **嵌入式 OLAP 列式存储引擎——分析领域的 SQLite**。PG 兼容 SQL 方言 + 大量语法糖（GROUP BY ALL、COLUMNS(*)、FROM-first）。零配置单文件部署。对比 SQLite（嵌入式 OLTP）和 PG（服务端 OLTP）——DuckDB 填补了嵌入式 OLAP 的空白。 |
| [改表](../ddl/alter-table/duckdb.md) | **ALTER 支持有限——ADD/DROP/RENAME COLUMN 基本操作**。嵌入式场景无在线 DDL 需求（无并发连接）。对比 PG 的 DDL 事务性可回滚和 MySQL 的 Online DDL——DuckDB 的 ALTER 简单但对嵌入式场景足够。 |
| [索引](../ddl/indexes/duckdb.md) | **ART 索引（自适应基数树）是 DuckDB 独特的索引结构**——但列式引擎主要靠 Zone Maps（min/max 统计信息）自动过滤。大多数分析查询无需手动创建索引。对比 PG 的 GiST/GIN/BRIN 四框架和 BigQuery 的无索引设计——DuckDB 的 ART 索引是折中方案。 |
| [约束](../ddl/constraints/duckdb.md) | **PK/UNIQUE/CHECK 约束实际执行（写入时校验）**——FK 约束声明支持但执行能力在持续完善中。对比 BigQuery/Redshift 的约束仅作提示和 PG/MySQL 的完整强制执行——DuckDB 在约束执行上趋向严格，符合其"做正确的事"的设计哲学。 |
| [视图](../ddl/views/duckdb.md) | **普通视图支持，无物化视图**——嵌入式 OLAP 场景下数据通常从文件直接读取，物化视图需求不强。对比 PG 的 REFRESH MATERIALIZED VIEW 和 Oracle 的 Fast Refresh+Query Rewrite——DuckDB 的定位使物化视图优先级较低。 |
| [序列与自增](../ddl/sequences/duckdb.md) | **SEQUENCE + 自动递增（PG 兼容语法）**——支持 GENERATED ALWAYS AS IDENTITY。对比 PG 的 IDENTITY/SERIAL/SEQUENCE 三种选择和 SQLite 的 INTEGER PK=rowid——DuckDB 继承了 PG 的序列模型，功能完整。 |
| [数据库/Schema/用户](../ddl/users-databases/duckdb.md) | **ATTACH 多数据库（类似 SQLite）无用户权限系统**——嵌入式引擎运行在应用进程中，安全性由应用层控制。可同时 ATTACH SQLite 文件、PostgreSQL 数据库和 Parquet 文件。对比 SQLite 的 ATTACH DATABASE 和 PG 的 RBAC 权限模型——DuckDB 的多源 ATTACH 是独特能力。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/duckdb.md) | **无存储过程/动态 SQL**——MACRO（宏）可定义简单的参数化表达式替代。Python/R API 集成是复杂逻辑的实现方式。对比 PG 的 PL/pgSQL 和 Oracle 的 PL/SQL——DuckDB 将过程化逻辑推到宿主语言层，与 SQLite 定位类似。 |
| [错误处理](../advanced/error-handling/duckdb.md) | **无过程式错误处理**——错误通过 C++/Python/R API 返回。无 TRY/CATCH、无 EXCEPTION WHEN。对比 PG/Oracle 的过程式错误处理——DuckDB 的错误处理完全在应用层，与嵌入式定位一致。 |
| [执行计划](../advanced/explain/duckdb.md) | **EXPLAIN ANALYZE 带实际行数和执行时间**——Profile 模式提供可视化的管道执行详情（每个算子的行数、耗时、内存使用）。对比 PG 的 EXPLAIN (ANALYZE, BUFFERS)（功能接近）和 BigQuery 无传统 EXPLAIN——DuckDB 的 Profile 可视化适合交互式数据分析调试。 |
| [锁机制](../advanced/locking/duckdb.md) | **MVCC 乐观并发，单写者 + 多读者（类似 SQLite）**——同一时刻仅一个写入连接，多个读取连接不受影响。无锁竞争和死锁问题。对比 PG/MySQL 的行级锁高并发写入和 SQLite 的文件级锁——DuckDB 的单写者模型适合分析场景（读多写少）。 |
| [分区](../advanced/partitioning/duckdb.md) | **Hive 分区读取支持——直接查询按目录分区的 Parquet 文件**。内部存储通过 Row Groups 实现数据分片。对比 PG 的声明式分区和 BigQuery 的 PARTITION BY——DuckDB 的分区主要面向外部文件读取而非内部数据管理。 |
| [权限](../advanced/permissions/duckdb.md) | **无权限系统——安全性依赖文件系统权限**（与 SQLite 相同）。嵌入式定位下应用进程拥有全部数据库权限。对比 PG 的 RBAC+RLS 和 Oracle 的 VPD——DuckDB 将安全责任推到应用层，符合嵌入式架构。 |
| [存储过程](../advanced/stored-procedures/duckdb.md) | **无存储过程——MACRO（宏）替代简单逻辑**。`CREATE MACRO add(a,b) AS a+b` 定义可复用表达式。Table MACRO 可返回表结果。对比 PG 的 PL/pgSQL 函数和 Oracle 的 PL/SQL Package——DuckDB 的 MACRO 轻量但功能有限，复杂逻辑仍需宿主语言。 |
| [临时表](../advanced/temp-tables/duckdb.md) | **CREATE TEMP TABLE 支持，会话级可见**——嵌入式场景下临时表主要用于中间计算暂存。对比 PG 的 ON COMMIT DROP/DELETE ROWS 和 SQL Server 的 #temp——DuckDB 临时表功能基础但足够。 |
| [事务](../advanced/transactions/duckdb.md) | **ACID 事务 + MVCC + 单写者模型（类 SQLite）**——保证数据一致性但并发写入受限。WAL 模式持久化。对比 PG 的 MVCC 行级锁高并发和 BigQuery 的 DML 配额限制——DuckDB 的事务模型在嵌入式场景下足够安全。 |
| [触发器](../advanced/triggers/duckdb.md) | **无触发器支持**——嵌入式 OLAP 场景下触发器需求不强。对比 PG 的完整触发器和 SQLite 的 BEFORE/AFTER/INSTEAD OF——DuckDB 将事件驱动逻辑推到应用层处理。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/duckdb.md) | **DELETE 标准支持，批量操作在列式引擎下高效**——Row Groups 粒度的标记删除。对比 PG 的行级删除+VACUUM 和 Redshift 的 DELETE 标记+VACUUM——DuckDB 的列式 DELETE 在批量场景下性能优异。 |
| [插入](../dml/insert/duckdb.md) | **INSERT + COPY 标准导入，可直接导入 Parquet/CSV/JSON 文件**——`INSERT INTO t SELECT * FROM read_parquet('*.parquet')` 一行完成。外部文件直接作为数据源是 DuckDB 的核心特色。对比 PG 的 COPY（仅 CSV/文本）和 BigQuery 的 LOAD JOB——DuckDB 的多格式直查最灵活。 |
| [更新](../dml/update/duckdb.md) | **UPDATE 标准支持——但列式存储下行级更新非最优场景**（需重写受影响的 Row Groups）。批量 UPDATE 性能可接受。对比 PG 的行级原地更新（OLTP 优势）和 Redshift 的 DELETE+INSERT——DuckDB 的 UPDATE 适合分析场景的偶尔更新。 |
| [Upsert](../dml/upsert/duckdb.md) | **ON CONFLICT DO UPDATE(0.9+) 是 PG 兼容 UPSERT 语法**——INSERT OR REPLACE 先删后插（SQLite 风格）。对比 PG 9.5+ 的 ON CONFLICT（功能相同）和 MySQL 的 ON DUPLICATE KEY UPDATE——DuckDB 同时支持 PG 和 SQLite 两种 UPSERT 风格。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/duckdb.md) | **FILTER 子句支持条件聚合（与 PG 相同）**——`COUNT(*) FILTER (WHERE status='active')`。GROUPING SETS/CUBE/ROLLUP 完整多维聚合。list_agg/string_agg 字符串聚合。对比 MySQL 无 FILTER 子句和 Oracle 无 FILTER——DuckDB 继承了 PG 的优雅条件聚合。 |
| [条件函数](../functions/conditional/duckdb.md) | **CASE/COALESCE/NULLIF/IF 标准条件函数**——IF(cond, true_val, false_val) 函数式条件（非 PG 标准但便捷）。对比 PG 坚持标准 CASE（无 IF 函数）和 MySQL 的 IF()——DuckDB 在标准基础上添加便捷函数。 |
| [日期函数](../functions/date-functions/duckdb.md) | **date_trunc/date_part/date_diff + INTERVAL 类型（PG 兼容）**——`date + INTERVAL '3 months'` 自然运算。对比 MySQL 的 DATE_ADD 函数式调用和 SQL Server 的 DATEADD——DuckDB 继承了 PG 的 INTERVAL 运算符风格，日期处理自然优雅。 |
| [数学函数](../functions/math-functions/duckdb.md) | **完整数学函数 + GREATEST/LEAST 内置**——除零返回 NULL（与 MySQL 行为相同，对比 PG/Oracle 报错）。对比 SQL Server 2022 才加入 GREATEST/LEAST 和 BigQuery 的 SAFE_DIVIDE——DuckDB 数学函数覆盖完整。 |
| [字符串函数](../functions/string-functions/duckdb.md) | **|| 拼接运算符（PG 兼容）+ regexp_extract/replace + string_split**——string_split 返回 LIST 类型可直接 UNNEST 展开为行。对比 PG 的 regexp_match 和 MySQL 的 CONCAT()（|| 是逻辑 OR）——DuckDB 字符串函数完整且风格接近 PG。 |
| [类型转换](../functions/type-conversion/duckdb.md) | **CAST / :: 运算符（PG 风格）+ TRY_CAST 安全转换**——TRY_CAST 失败返回 NULL（对比 PG 无内置 TRY_CAST 需自定义函数、SQL Server 的 TRY_CAST 最早）。对比 BigQuery 的 SAFE_CAST（功能相同）——DuckDB 在类型转换安全性上优于 PG。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/duckdb.md) | **递归 CTE 完整支持 + 优化器自动决定物化/内联**——对比 PG 12+ 的 MATERIALIZED/NOT MATERIALIZED 提示和 MySQL 8.0 的 CTE（来得晚且初期总是物化）——DuckDB 的 CTE 优化器智能且无需用户干预。 |
| [全文搜索](../query/full-text-search/duckdb.md) | **fts 扩展提供全文搜索（基于 BM25 排序算法）**——通过 `INSTALL fts; LOAD fts;` 动态加载。对比 PG 的 tsvector+GIN（功能更强且内置）和 SQLite 的 FTS5（同为嵌入式全文搜索）——DuckDB 的 FTS 是扩展而非内置，功能在发展中。 |
| [连接查询](../query/joins/duckdb.md) | **ASOF JOIN 是 DuckDB 的独特创新**——`SELECT * FROM trades ASOF JOIN quotes ON trades.ts >= quotes.ts` 按时间戳找到最近匹配行，时序数据分析利器。LATERAL JOIN（PG 兼容）。Hash/Merge/Nested Loop 三种 JOIN 算法。对比 PG/MySQL 无 ASOF JOIN——DuckDB 的时序查询能力独特。 |
| [分页](../query/pagination/duckdb.md) | **LIMIT/OFFSET 标准 + FETCH FIRST 亦支持**——嵌入式场景下分页性能稳定（无网络开销）。对比 PG/MySQL 的深分页性能问题和 BigQuery 按扫描量计费——DuckDB 的分页在交互式分析中自然高效。 |
| [行列转换](../query/pivot-unpivot/duckdb.md) | **PIVOT/UNPIVOT 原生支持（0.8+）是 DuckDB 的分析亮点**——`PIVOT t ON year USING SUM(amount)` 比手写 CASE WHEN 简洁数倍。支持动态 PIVOT（自动检测值列表）。对比 Oracle 11g（最早引入 PIVOT）和 PG（无原生 PIVOT 需 crosstab 扩展）——DuckDB 的 PIVOT 功能最先进。 |
| [集合操作](../query/set-operations/duckdb.md) | **UNION/INTERSECT/EXCEPT + ALL 变体完整支持**——UNION BY NAME 按列名而非位置合并（DuckDB 独有便利语法）。对比 MySQL 直到 8.0.31 才支持 INTERSECT/EXCEPT——DuckDB 集合操作完整且有独特扩展。 |
| [子查询](../query/subquery/duckdb.md) | **LATERAL 子查询支持（PG 兼容）+ 优化器自动展开**——关联子查询自动转为 JOIN。对比 PG 9.3+ 的 LATERAL（功能相同）和 MySQL（不支持 LATERAL）——DuckDB 继承了 PG 的 LATERAL 能力。 |
| [窗口函数](../query/window-functions/duckdb.md) | **QUALIFY 子句是 DuckDB 窗口函数的最大亮点**——`SELECT * FROM t QUALIFY ROW_NUMBER() OVER(PARTITION BY g ORDER BY v) = 1` 无需子查询包装。WINDOW 命名子句复用帧定义。对比 PG/MySQL/Oracle 均不支持 QUALIFY（需子查询包装）和 BigQuery/Snowflake（同样支持 QUALIFY）。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/duckdb.md) | **generate_series 原生支持（PG 兼容）+ RANGE 函数生成序列**——`SELECT * FROM generate_series(DATE '2024-01-01', DATE '2024-12-31', INTERVAL '1 day')` 一行搞定。对比 MySQL 需递归 CTE（冗长）和 BigQuery 的 GENERATE_DATE_ARRAY——DuckDB 日期填充与 PG 同样简洁。 |
| [去重](../scenarios/deduplication/duckdb.md) | **QUALIFY ROW_NUMBER() 是最简洁的去重写法**——`SELECT * FROM t QUALIFY ROW_NUMBER() OVER(PARTITION BY key ORDER BY ts DESC) = 1` 无需子查询。DISTINCT ON（PG 兼容）也可用。对比 PG 的 DISTINCT ON 和 MySQL 需 ROW_NUMBER+子查询——DuckDB 的 QUALIFY 去重最简洁。 |
| [区间检测](../scenarios/gap-detection/duckdb.md) | **generate_series + 窗口函数检测间隙**——与 PG 方案完全相同。对比 MySQL 需递归 CTE 生成序列和 Teradata 的 sys_calendar 系统日历表——DuckDB 继承了 PG 的 generate_series 优势。 |
| [层级查询](../scenarios/hierarchical-query/duckdb.md) | **递归 CTE 标准实现**——无 Oracle 的 CONNECT BY、无 PG 的 ltree 扩展。对比 PG 的递归 CTE+ltree 和 SQL Server 的 hierarchyid 类型——DuckDB 层级查询功能基础但对分析场景足够。 |
| [JSON 展开](../scenarios/json-flatten/duckdb.md) | **json_extract/json_each + 可直接查询 JSON 文件**——`SELECT * FROM read_json('data.json')` 直接将 JSON 文件作为表查询。对比 PG 的 JSONB+GIN 索引（查询优化最强）和 Snowflake 的 FLATTEN——DuckDB 的文件直查是嵌入式引擎的独特优势。 |
| [迁移速查](../scenarios/migration-cheatsheet/duckdb.md) | **PG 兼容语法 + 列式引擎——适合从 PG 迁移分析负载**。GROUP BY ALL/COLUMNS(*)/QUALIFY 等语法糖是 PG 没有的增强。外部文件直查（Parquet/CSV/JSON）无需导入。对比 PG（服务端 OLTP+OLAP）和 BigQuery（云 OLAP）——DuckDB 是本地分析的最佳选择。 |
| [TopN 查询](../scenarios/ranking-top-n/duckdb.md) | **QUALIFY ROW_NUMBER() 是分组 TopN 最简写法**——无需子查询包装。DISTINCT ON（PG 兼容）可分组取一。对比 PG 的 DISTINCT ON 和 MySQL 需 ROW_NUMBER+子查询嵌套——DuckDB 在 TopN 场景上提供最简语法。 |
| [累计求和](../scenarios/running-total/duckdb.md) | **SUM() OVER 标准累计求和——列式引擎聚合极快**。Morsel-Driven Parallelism 向量化执行模型充分利用多核 CPU。对比 PG（单机行存）和 BigQuery（分布式列存）——DuckDB 在单机列式聚合性能上可与分布式引擎媲美。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/duckdb.md) | **INSERT OR REPLACE + MERGE(0.9+) 双方案**——MERGE 支持 WHEN MATCHED/WHEN NOT MATCHED 标准语法。对比 PG 15+ 的 MERGE（较晚引入）和 Oracle 9i 的 MERGE（首创）——DuckDB 的 MERGE 功能完整但到达时间适中。 |
| [字符串拆分](../scenarios/string-split-to-rows/duckdb.md) | **string_split + UNNEST 是字符串拆分的标准方案**——`SELECT UNNEST(string_split('a,b,c', ','))` 一行完成。regexp_split_to_table（PG 兼容）也可用。对比 PG 14 的 string_to_table 和 MySQL 无原生拆分——DuckDB 的方案简洁且风格与 PG 接近。 |
| [窗口分析](../scenarios/window-analytics/duckdb.md) | **完整窗口函数 + QUALIFY + WINDOW 命名子句**——QUALIFY 无需子查询过滤窗口结果。FILTER 子句条件聚合。ROWS/RANGE 帧完整。对比 PG（FILTER+GROUPS 独有但无 QUALIFY）和 BigQuery（QUALIFY 有但无 FILTER）——DuckDB 的窗口分析功能在嵌入式引擎中最完整。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/duckdb.md) | **LIST/STRUCT/MAP/UNION 原生复合类型**——`[1,2,3]` 为 LIST、`{'a':1}` 为 STRUCT，语法极自然。Lambda 函数 `list_transform(l, x -> x*2)` 做元素级操作。UNION 类型存储多种类型值。对比 PG 的 ARRAY（无 MAP/UNION）和 BigQuery 的 STRUCT/ARRAY——DuckDB 复合类型最丰富。 |
| [日期时间](../types/datetime/duckdb.md) | **DATE/TIME/TIMESTAMP/INTERVAL 完整 + 纳秒精度**——TIMESTAMP_NS 纳秒精度（对比 PG 的微秒、MySQL 的微秒）。INTERVAL 运算符（PG 风格）自然优雅。对比 BigQuery 的四种时间类型和 Oracle 的 DATE 含时间到秒（易混淆）——DuckDB 时间类型精度最高。 |
| [JSON](../types/json/duckdb.md) | **原生 JSON 类型 + 可直接查询 JSON 文件**——`SELECT * FROM 'data.json'` 直接将文件作为表。json_extract 路径查询。对比 PG 的 JSONB+GIN 索引（查询优化最强）和 Snowflake 的 VARIANT——DuckDB 的 JSON 处理偏向文件直查而非索引优化。 |
| [数值类型](../types/numeric/duckdb.md) | **TINYINT 到 HUGEINT(128 位) 覆盖所有整数需求**——HUGEINT 128 位整数是 DuckDB 独有（对比 PG 最大 BIGINT 64 位）。DECIMAL 精确定点。FLOAT/DOUBLE IEEE 754 浮点。对比 BigQuery 只有 INT64 一种整数和 Oracle 的 NUMBER 万能类型——DuckDB 数值类型最丰富。 |
| [字符串类型](../types/string/duckdb.md) | **VARCHAR 无长度限制 + 正则内置**——无 VARCHAR(n) 长度约束（极简设计）。BLOB 二进制类型。正则函数内置（对比 SQLite 需扩展加载）。对比 PG 的 TEXT=VARCHAR（无性能差异）和 BigQuery 的 STRING——DuckDB 字符串处理与 PG 接近但更简洁。 |
