# Trino

**分类**: 分布式查询引擎
**文件数**: 51 个 SQL 文件
**总行数**: 4552 行

> **关键人物**：[Traverso, Sundstrom, Phillips](../docs/people/trino-founders.md)（Facebook Presto 创始人）

## 概述与定位

Trino（原 PrestoSQL）是一款开源的分布式 SQL 查询引擎，最初由 Facebook 的 Martin Traverso、Dain Sundstrom、David Phillips 和 Eric Hwang 于 2012 年创建。Trino 的核心理念是"一个引擎查所有数据"——通过 Connector 插件化架构，用统一的 ANSI SQL 查询分布在不同系统中的数据（Hive、MySQL、PostgreSQL、Kafka、Elasticsearch、S3 等），无需将数据搬运到统一的数仓中。Trino 不存储数据，它是纯粹的计算引擎。

## 历史与演进

- **2012 年**：Facebook 内部启动 Presto 项目，解决 Hive MapReduce 查询延迟过高的问题。
- **2013 年**：Presto 开源（Apache 许可），迅速在 Netflix、Uber、Airbnb 等公司获得采用。
- **2019 年**：创始团队离开 Facebook 成立 Starburst 公司，将项目更名为 PrestoSQL（后更名 Trino），与 Facebook 维护的 PrestoDB 正式分道。
- **2020 年**：正式更名为 Trino（商标原因），社区版本号重置。
- **2022 年**：引入 Fault-Tolerant Execution（容错执行模式），支持中间结果落盘和任务重试。
- **2023 年**：增强 Iceberg/Delta Lake/Hudi 连接器、改进动态过滤、引入多语句查询支持。
- **2024-2025 年**：持续优化大规模查询（ETL 场景）的稳定性、增强物化视图和缓存层。

## 核心设计思路

1. **Connector 架构**：每个数据源通过实现 Connector SPI 接口接入 Trino，SQL 引擎与存储完全解耦。一条 SQL 可 JOIN 来自不同数据源的表。
2. **MPP 管道式执行**：查询被拆分为多个 Stage，Stage 内多个 Task 分布到 Worker 节点并行执行，数据以管道流（Pipeline）方式在算子间流动，无需落盘中间结果（Fault-Tolerant 模式除外）。
3. **联邦查询**：用 `catalog.schema.table` 三级命名空间引用不同数据源的表，可在一条 SQL 中跨数据源 JOIN。
4. **ANSI SQL 兼容**：SQL 方言高度遵循 ANSI SQL 标准，支持复杂查询（窗口函数、CTE、LATERAL、UNNEST、Lambda）。

## 独特特色

| 特性 | 说明 |
|---|---|
| **Connector 架构** | 插件化数据源接入——Hive、Iceberg、Delta Lake、MySQL、PostgreSQL、MongoDB、Kafka、Elasticsearch 等数十种 Connector。 |
| **联邦查询** | `SELECT * FROM hive.db.t1 JOIN mysql.db.t2 ON ...`，在一条 SQL 中 JOIN 不同数据源的表。 |
| **UNNEST** | `SELECT * FROM t CROSS JOIN UNNEST(array_col) AS u(element)` 将数组/Map 展开为行，是处理嵌套数据的核心手段。 |
| **Lambda 表达式** | `transform(array, x -> x * 2)` / `filter(array, x -> x > 0)` 等高阶函数，对数组/Map 进行函数式操作。 |
| **动态过滤** | Join 的 Build 侧运行时生成过滤条件下推到 Probe 侧的 TableScan，减少大表扫描量。 |
| **Fault-Tolerant Execution** | 中间结果可落盘（Spill to Exchange），Task 失败后可重试而非整个查询失败，适合 ETL 级长查询。 |
| **Session 属性** | 通过 `SET SESSION property = value` 灵活控制查询行为（如 `join_distribution_type`、`task_concurrency`）。 |

## 已知不足

- **不存储数据**：Trino 是纯计算引擎，查询性能受限于底层数据源的 I/O 和格式，对于非列式格式（如 CSV、JSON）查询效率较低。
- **UPDATE/DELETE 有限**：仅部分 Connector（如 Iceberg、Hive ACID、JDBC）支持行级变更，大部分 Connector 只支持 SELECT/INSERT。
- **存储过程/触发器缺失**：作为查询引擎不支持存储过程、触发器等过程化编程特性。
- **资源管理较弱**：内置的资源组（Resource Groups）功能相对基础，不如专业数仓的 Workload Management 精细。
- **Coordinator 单点**：Coordinator 是单点（虽有故障恢复机制），在超大规模集群中可能成为瓶颈。
- **元数据缓存一致性**：对频繁变更的数据源，Connector 的元数据缓存可能导致查询到过期的 schema 或统计信息。

## 对引擎开发者的参考价值

- **Connector SPI 设计**：通过定义清晰的 Service Provider Interface（Metadata、SplitManager、PageSourceProvider、PageSinkProvider），实现数据源的完全可插拔，是查询引擎插件化的教科书级实现。
- **联邦查询的执行计划**：跨数据源 JOIN 的优化（数据源下推、跨源谓词推断）对联邦查询引擎设计有直接参考。
- **管道式执行模型**：数据在算子间以 Page 为单位流水线式传递（无全量中间物化），对低延迟查询引擎的执行模型设计有参考。
- **Dynamic Filtering 实现**：在分布式 JOIN 中，Build 侧完成后向 Probe 侧注入运行时过滤器的机制，对分布式查询优化有重要借鉴。
- **UNNEST 与 Lambda 的类型系统**：在 SQL 类型系统中支持函数类型（Lambda）和集合展开（UNNEST）的设计，对引擎的类型系统扩展有参考。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/trino.md) | **Connector 插件化架构是 Trino 的核心设计**——通过实现 Connector SPI 接入任意数据源（Hive/Iceberg/MySQL/PG/Kafka/Elasticsearch 等数十种）。CTAS 是跨数据源数据迁移的标准操作。对比 BigQuery 的单一引擎和 PG 的 Foreign Data Wrapper——Trino 的联邦查询能力最强。 |
| [改表](../ddl/alter-table/trino.md) | **ALTER 能力完全取决于底层 Connector**——Hive Connector 支持 ADD COLUMN，Iceberg Connector 支持 Schema Evolution，JDBC Connector 透传 ALTER 到底层数据库。Trino 本身不存储数据，DDL 语义由数据源决定。对比 PG/MySQL 的统一 ALTER 语义——Trino 的 ALTER 是异构的。 |
| [索引](../ddl/indexes/trino.md) | **无自有索引——纯计算引擎不存储数据**。查询加速依赖底层数据源的索引（PG 的 B-tree、Elasticsearch 的倒排索引等）。Dynamic Filtering 是 Trino 自有的运行时优化——Build 侧生成过滤条件下推到 Probe 侧的 TableScan。对比 BigQuery 的分区+聚集和 DuckDB 的 Zone Maps。 |
| [约束](../ddl/constraints/trino.md) | **无约束执行——纯查询引擎不保证数据完整性**。元数据（表 schema、分区信息）从 Connector 获取仅供优化器参考。数据完整性由底层数据源保证。对比 PG/MySQL 的约束强制执行和 BigQuery 的 NOT ENFORCED——Trino 不参与约束管理。 |
| [视图](../ddl/views/trino.md) | **视图定义存储在 Connector 中——Trino 本身不持久化视图元数据**。可创建跨 Catalog 的视图（JOIN 不同数据源的表）。对比 PG 的视图存储在 pg_catalog 和 BigQuery 的 Authorized View——Trino 的视图语义取决于 Connector。 |
| [序列与自增](../ddl/sequences/trino.md) | **无 SEQUENCE/自增——纯查询引擎不维护状态**。唯一标识符由底层数据源生成或使用 UUID() 函数。对比 PG 的 IDENTITY/SEQUENCE 和 BigQuery 的 GENERATE_UUID()——Trino 将序列生成完全委托给数据源。 |
| [数据库/Schema/用户](../ddl/users-databases/trino.md) | **Catalog.Schema.Table 三级命名空间是联邦查询的基础**——每个 Catalog 对应一个 Connector（如 `hive.db.table`、`mysql.db.table`），一条 SQL 可 JOIN 不同 Catalog 的表。对比 BigQuery 的 Project.Dataset.Table 和 PG 的 Database.Schema.Table——Trino 的 Catalog 映射数据源。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/trino.md) | **无动态 SQL/存储过程——纯查询引擎定位**。复杂逻辑通过调度工具（Airflow/dbt）编排 SQL 查询实现。对比 PG 的 PL/pgSQL 和 Oracle 的 PL/SQL——Trino 将所有过程化逻辑推到外部编排层。 |
| [错误处理](../advanced/error-handling/trino.md) | **无过程式错误处理——查询级错误直接返回客户端**。TRY() 函数可将表达式错误转为 NULL（类似 BigQuery 的 SAFE_ 前缀）。对比 PG 的 EXCEPTION WHEN 和 SQL Server 的 TRY...CATCH——Trino 的 TRY() 是行级错误处理的简洁方案。 |
| [执行计划](../advanced/explain/trino.md) | **EXPLAIN ANALYZE 显示分布式 Stage/Fragment 执行详情**——每个 Stage 的 Worker 数、处理行数、CPU/Wall 时间、网络传输量。对比 PG 的 EXPLAIN ANALYZE（单机视角）和 BigQuery 的 Console Execution Details——Trino 的分布式执行计划信息对调优至关重要。 |
| [锁机制](../advanced/locking/trino.md) | **无锁——纯查询引擎不管理并发**。并发控制由底层数据源负责。Resource Groups 控制 Trino 侧的查询并发和资源分配。对比 PG 的行级锁 MVCC 和 BigQuery 的 DML 配额——Trino 将并发语义委托给数据源。 |
| [分区](../advanced/partitioning/trino.md) | **分区语义透传到 Connector**——Hive/Iceberg 的 PARTITIONED BY 在 Trino 中可用，分区裁剪由 Connector 实现。Dynamic Filtering 在 JOIN 时自动生成分区裁剪条件。对比 PG 的声明式分区和 BigQuery 的 PARTITION BY——Trino 的分区完全取决于底层数据格式。 |
| [权限](../advanced/permissions/trino.md) | **内置 RBAC + 可集成 Apache Ranger**——Catalog/Schema/Table 三级权限控制。System Access Control 插件化设计。对比 PG 的 GRANT/REVOKE+RLS 和 BigQuery 的 GCP IAM——Trino 的权限系统可通过插件扩展适配企业安全策略。 |
| [存储过程](../advanced/stored-procedures/trino.md) | **无存储过程——纯 SQL 查询引擎定位**。所有过程化逻辑通过外部工具（dbt、Airflow、Python）实现。对比 PG 的 PL/pgSQL 多语言过程和 Oracle 的 PL/SQL Package——Trino 专注于查询而非过程化编程。 |
| [临时表](../advanced/temp-tables/trino.md) | **无临时表——用 CTAS（CREATE TABLE AS SELECT）+ DROP TABLE 模拟**。中间结果存储到 Connector 的表中。对比 PG 的 CREATE TEMP TABLE 和 SQL Server 的 #temp——Trino 无会话级临时存储概念，所有数据持久化在 Connector 中。 |
| [事务](../advanced/transactions/trino.md) | **事务能力取决于 Connector**——Iceberg Connector 支持 ACID，Hive Connector 事务能力有限，JDBC Connector 透传底层事务。Trino 本身不提供跨 Connector 的分布式事务。对比 PG 的完整 ACID 和 BigQuery 的多语句事务——Trino 的事务是异构的。 |
| [触发器](../advanced/triggers/trino.md) | **无触发器——纯查询引擎不支持事件驱动逻辑**。对比 PG 的完整触发器支持和 BigQuery 的 Pub/Sub 替代方案——Trino 的联邦查询定位使触发器无意义（数据变更发生在底层数据源）。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/trino.md) | **DELETE 能力取决于 Connector**——Iceberg/Delta Connector 支持行级 DELETE，Hive Connector 仅支持分区级 DELETE，JDBC Connector 透传 DELETE 到底层数据库。对比 PG 的统一 DELETE 语义——Trino 的 DELETE 是异构的。 |
| [插入](../dml/insert/trino.md) | **INSERT INTO / CTAS 是跨 Connector 数据迁移利器**——`INSERT INTO iceberg.db.target SELECT * FROM mysql.db.source` 一条 SQL 完成跨数据源迁移。CTAS 创建新表同时写入数据。对比 PG 的 COPY 和 BigQuery 的 LOAD JOB——Trino 的跨源 INSERT 是联邦查询的核心价值。 |
| [更新](../dml/update/trino.md) | **UPDATE 能力取决于 Connector**——Iceberg/Delta Connector 支持行级 UPDATE，大部分 Connector 仅支持 SELECT/INSERT。对比 PG 的统一 UPDATE 语义——Trino 作为查询引擎，DML 能力受 Connector 限制是设计取舍。 |
| [Upsert](../dml/upsert/trino.md) | **MERGE 仅部分 Connector 支持（Iceberg/Delta/Hive ACID）**——非通用 DML 操作。MERGE 的功能完整度取决于 Connector 实现。对比 PG 15+ 的 MERGE（通用）和 Oracle 的 MERGE（首创）——Trino 的 MERGE 可用性因数据源而异。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/trino.md) | **GROUPING SETS/CUBE/ROLLUP 完整多维聚合**——approx_distinct 基于 HyperLogLog 近似去重计数（大数据量下性能远优于精确 COUNT DISTINCT）。无 FILTER 子句（对比 PG 的条件聚合）。对比 BigQuery 的 APPROX_COUNT_DISTINCT——Trino 的近似聚合函数丰富。 |
| [条件函数](../functions/conditional/trino.md) | **IF/CASE/COALESCE/NULLIF/TRY 标准条件函数**——TRY() 将表达式错误转为 NULL（独有设计，对比 BigQuery 的 SAFE_ 前缀和 SQL Server 的 TRY_CAST）。IF() 函数式条件（非 PG 标准但便捷）。类型系统严格——不做隐式转换。 |
| [日期函数](../functions/date-functions/trino.md) | **date_trunc/date_add/date_diff + INTERVAL 类型**——日期函数命名接近 PG 风格。INTERVAL 支持但运算能力不如 PG 丰富。对比 PG 的 `+ INTERVAL '3 months'` 自然语法和 SQL Server 的 DATEADD 函数式调用——Trino 日期函数中规中矩。 |
| [数学函数](../functions/math-functions/trino.md) | **完整数学函数 + infinity/NaN 严格处理**——IEEE 754 浮点特殊值有明确语义（对比 MySQL 返回 NULL、PG 报错）。GREATEST/LEAST 内置。对比 BigQuery 的 SAFE_DIVIDE 和 SQL Server 2022 才加入 GREATEST/LEAST——Trino 数学函数完整且语义明确。 |
| [字符串函数](../functions/string-functions/trino.md) | **|| 拼接运算符 + regexp_extract/replace + split 返回 ARRAY**——split 返回 ARRAY 类型可直接 UNNEST 展开。Lambda 表达式 `transform(array, x -> x*2)` 做函数式操作。对比 PG 的 regexp_match 和 BigQuery 的 SPLIT——Trino 的 Lambda+ARRAY 组合极其强大。 |
| [类型转换](../functions/type-conversion/trino.md) | **CAST + TRY_CAST 安全转换——类型系统严格不做隐式转换**。TRY_CAST 失败返回 NULL。对比 PG 无内置 TRY_CAST（需自定义函数）和 BigQuery 的 SAFE_CAST——Trino 的类型安全性与 PG 接近但多了 TRY_CAST 便利。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/trino.md) | **WITH 标准 CTE + 递归 CTE 支持**——优化器自动决定物化/内联。无可写 CTE（DML in WITH）。对比 PG 的可写 CTE（独有）和 MySQL 8.0 的 CTE（功能接近）——Trino 的 CTE 功能标准完整。 |
| [全文搜索](../query/full-text-search/trino.md) | **无内置全文搜索——通过 Elasticsearch Connector 实现**。`SELECT * FROM elasticsearch.index.docs WHERE match(content, 'query')` 利用 ES 的全文搜索能力。对比 PG 的 tsvector+GIN（内置）和 BigQuery 的 SEARCH INDEX——Trino 的联邦方案让最专业的引擎处理全文搜索。 |
| [连接查询](../query/joins/trino.md) | **Broadcast/Partitioned JOIN + 跨 Connector JOIN 是联邦查询的核心**——小表自动 Broadcast，大表 Partitioned（Shuffle）。Dynamic Filtering 自动将 Build 侧过滤条件下推到 Probe 侧。对比 BigQuery 的自动选择和 Redshift 的 DISTKEY 优化——Trino 的跨源 JOIN 是独有能力。 |
| [分页](../query/pagination/trino.md) | **LIMIT/OFFSET 标准 + FETCH FIRST 亦支持**——分布式环境下 LIMIT 需汇聚到 Coordinator 排序。对比 PG/MySQL 的标准分页和 BigQuery 按扫描量计费——Trino 的分页在交互式查询中常用。 |
| [行列转换](../query/pivot-unpivot/trino.md) | **无原生 PIVOT/UNPIVOT 语法**——需手写 CASE + GROUP BY 模拟。对比 Oracle 11g/BigQuery/DuckDB 的原生 PIVOT——Trino 在行列转换上缺乏原生支持，是分析查询的短板。 |
| [集合操作](../query/set-operations/trino.md) | **UNION/INTERSECT/EXCEPT 完整支持**——ALL 变体均可用。跨 Connector 集合操作（不同数据源的表可做 UNION）。对比 MySQL 直到 8.0.31 才支持 INTERSECT/EXCEPT——Trino 的集合操作完整且支持跨源。 |
| [子查询](../query/subquery/trino.md) | **关联子查询 + IN/EXISTS + 优化器自动去关联**——Trino 优化器将关联子查询转为 JOIN 以利用分布式并行。对比 PG 的 LATERAL 子查询（Trino 也支持）和 Oracle 的标量子查询缓存——Trino 的去关联优化对分布式执行至关重要。 |
| [窗口函数](../query/window-functions/trino.md) | **完整窗口函数 + 分布式排序**——ROW_NUMBER/RANK/LAG/LEAD 完整。分布式环境下窗口函数需在各节点间 Shuffle 数据（按 PARTITION BY 列分布）。无 QUALIFY 子句（对比 BigQuery/DuckDB）。对比 PG 的 FILTER+GROUPS 和 SQL Server 的 Batch Mode——Trino 窗口函数完整但无独特扩展。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/trino.md) | **SEQUENCE() + UNNEST 生成日期序列**——`SELECT * FROM UNNEST(SEQUENCE(DATE '2024-01-01', DATE '2024-12-31', INTERVAL '1' DAY))` 生成日期序列。对比 PG 的 generate_series 和 BigQuery 的 GENERATE_DATE_ARRAY——Trino 的 SEQUENCE+UNNEST 模式功能等价。 |
| [去重](../scenarios/deduplication/trino.md) | **ROW_NUMBER + CTE 去重标准方案**——无 QUALIFY（对比 BigQuery/DuckDB）、无 DISTINCT ON（PG 独有）。对比 PG 的 DISTINCT ON（最简写法）——Trino 去重需标准子查询包装。 |
| [区间检测](../scenarios/gap-detection/trino.md) | **窗口函数 LAG/LEAD 检测相邻行间隙**——SEQUENCE()+UNNEST 生成完整序列后 EXCEPT 检测缺失。对比 PG 的 generate_series+LEFT JOIN 和 Teradata 的 sys_calendar——Trino 间隙检测方案标准。 |
| [层级查询](../scenarios/hierarchical-query/trino.md) | **递归 CTE 标准支持**——无 Oracle 的 CONNECT BY、无 PG 的 ltree 扩展。递归深度由查询超时和资源限制控制。对比 PG 的递归 CTE+ltree 和 SQL Server 的 hierarchyid——Trino 层级查询功能基础但对分析场景足够。 |
| [JSON 展开](../scenarios/json-flatten/trino.md) | **json_extract/json_parse + UNNEST+CAST 展开 JSON 数组**——Trino 的 JSON 处理风格独特：先 json_parse 转为 JSON 类型，再 CAST 为 ARRAY/MAP/ROW 强类型。对比 PG 的 JSONB+GIN 索引和 Snowflake 的 LATERAL FLATTEN——Trino 的 JSON 处理强调类型安全。 |
| [迁移速查](../scenarios/migration-cheatsheet/trino.md) | **联邦查询引擎——SQL 方言最接近 ANSI 标准**。DML 能力因 Connector 而异（Iceberg 最完整，Hive 次之，JDBC 透传）。ROW 类型对应其他引擎的 STRUCT（命名不同）。从任何数据库迁入 Trino 主要适配 Connector 配置而非 SQL 语法。 |
| [TopN 查询](../scenarios/ranking-top-n/trino.md) | **ROW_NUMBER + 窗口函数是分组 TopN 标准方案**——全局 TopN 直接 ORDER BY + LIMIT。无 QUALIFY（对比 BigQuery/DuckDB）。分布式排序后 LIMIT 在 Coordinator 汇聚。对比 PG 的 DISTINCT ON 和 SQL Server 的 TOP WITH TIES。 |
| [累计求和](../scenarios/running-total/trino.md) | **SUM() OVER 标准累计求和——分布式并行计算**。窗口函数在各 Worker 节点按 PARTITION BY 列并行执行。对比 PG（单机高效）和 BigQuery（Slot 自动扩展）——Trino 的分布式窗口函数适合大数据量。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/trino.md) | **MERGE 仅 Iceberg/Delta Connector 支持——非通用操作**。SCD 实现取决于底层数据源能力。对比 Oracle 的 MERGE（通用且首创）和 SQL Server 的 Temporal Tables——Trino 的 SCD 能力受 Connector 限制。 |
| [字符串拆分](../scenarios/string-split-to-rows/trino.md) | **split() + UNNEST 展开——函数式风格字符串拆分**。`SELECT val FROM UNNEST(split('a,b,c', ',')) AS t(val)` 一行完成。对比 PG 14 的 string_to_table 和 MySQL 的递归 CTE——Trino 的 split+UNNEST 简洁且风格一致。 |
| [窗口分析](../scenarios/window-analytics/trino.md) | **完整窗口函数 + 分布式计算**——ROWS/RANGE 帧支持。无 QUALIFY/FILTER/GROUPS（对比 BigQuery 的 QUALIFY 和 PG 的 FILTER+GROUPS）。分布式排序和窗口计算在 Worker 节点并行执行。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/trino.md) | **ARRAY/MAP/ROW 原生复合类型 + UNNEST 展开**——ROW 类型对应其他引擎的 STRUCT（Trino 命名不同）。Lambda 表达式 `transform(array, x -> x*2)` 做函数式操作。对比 BigQuery 的 STRUCT/ARRAY 和 DuckDB 的 LIST/STRUCT/MAP——Trino 的 ROW 命名独特但功能等价。 |
| [日期时间](../types/datetime/trino.md) | **DATE/TIME/TIMESTAMP WITH TIME ZONE + INTERVAL 类型**——TIMESTAMP 默认不含时区（对比 BigQuery 的 TIMESTAMP 默认含时区）。INTERVAL 支持但运算不如 PG 丰富。对比 PG 的 TIMESTAMPTZ 和 Oracle 的 DATE 含时间到秒——Trino 时间类型完整。 |
| [JSON](../types/json/trino.md) | **JSON 类型 + json_extract 路径查询——无 JSON 索引**（纯查询引擎不维护索引）。JSON 处理强调 CAST 到强类型（ARRAY/MAP/ROW）后操作。对比 PG 的 JSONB+GIN 索引（最强实现）和 Snowflake 的 VARIANT——Trino 的 JSON 处理依赖底层数据源索引。 |
| [数值类型](../types/numeric/trino.md) | **TINYINT/SMALLINT/INT/BIGINT/REAL/DOUBLE/DECIMAL(38 位)——严格类型不做隐式转换**。类型不匹配需显式 CAST。对比 PG 的严格类型（类似）和 MySQL 的宽松隐式转换——Trino 在类型安全上与 PG 接近。 |
| [字符串类型](../types/string/trino.md) | **VARCHAR/CHAR + UTF-8 默认——无 TEXT 别名**。VARCHAR 无长度限制（对比 PG 的 TEXT=VARCHAR 无差异）。VARBINARY 二进制类型。对比 PG 的 TEXT 别名和 BigQuery 的 STRING——Trino 字符串类型简洁但不提供 TEXT 便利别名。 |
