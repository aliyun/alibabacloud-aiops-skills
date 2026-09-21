# Materialize

**分类**: 流式物化视图（兼容 PostgreSQL）
**文件数**: 51 个 SQL 文件
**总行数**: 4756 行

## 概述与定位

Materialize 是一个流式物化视图数据库，兼容 PostgreSQL 协议。它的核心能力是让用户用标准 SQL 定义物化视图，然后系统自动对这些视图进行**增量维护**——当上游数据变更时，视图结果在毫秒级内更新，无需完整重算。Materialize 定位于需要低延迟实时分析的场景，如实时仪表盘、监控告警、实时特征工程和事件驱动业务逻辑。

## 历史与演进

- **2019 年**：Materialize 公司成立，核心团队来自 Timely Dataflow 和 Differential Dataflow 研究项目。
- **2020 年**：首个公开版本发布，展示增量物化视图能力。
- **2021 年**：引入 SOURCE 和 SINK 连接器，支持 Kafka、PostgreSQL CDC 等数据源。
- **2022 年**：推出 Materialize Cloud 托管服务，引入 SUBSCRIBE 持续查询。
- **2023 年**：增强多集群隔离、RBAC 权限管理和性能优化。
- **2024-2025 年**：持续增强 PG 兼容性、WebSocket 接口和企业级功能。

## 核心设计思路

Materialize 的底层引擎基于 **Timely Dataflow** 和 **Differential Dataflow** 两个 Rust 研究框架。核心理念是将 SQL 查询编译为数据流图（Dataflow Graph），其中每个操作符（Filter、Join、Aggregate 等）维护增量状态。当输入数据发生变更时，变更沿数据流图传播，每个操作符只处理变化的部分（差分计算），而非重算整个结果集。这使得复杂的多表 JOIN 和聚合也能在毫秒级完成增量更新。

## 独特特色

- **增量物化视图**：`CREATE MATERIALIZED VIEW` 定义的视图自动增量维护，数据变更后结果即时更新。
- **SOURCE/SINK**：`CREATE SOURCE FROM KAFKA ...` 和 `CREATE SINK ... INTO KAFKA ...` 连接外部数据流。
- **SUBSCRIBE**：`SUBSCRIBE TO view` 持续接收物化视图的变更事件（类似 CDC）。
- **PG 兼容**：使用 `psql` 或任意 PG 客户端连接，支持标准 SQL（JOIN、CTE、窗口函数等）。
- **Differential Dataflow**：底层差分数据流引擎支持任意复杂 SQL 的增量计算。
- **时间概念**：严格的事件时间处理，保证物化视图的一致性。
- **多集群隔离**：不同工作负载可部署在独立的计算集群中。

## 已知不足

- 不是通用 OLTP 数据库——不直接支持 INSERT/UPDATE/DELETE 到用户表（数据需从 SOURCE 导入）。
- 对于不断增长的无界数据集，某些物化视图的内存消耗可能不可控。
- 与 PostgreSQL 的兼容性有限：不支持存储过程、触发器、用户自定义类型等。
- 首次创建物化视图时需要全量计算一次快照，大数据集可能耗时较长。
- 生态系统和社区规模相比 PostgreSQL/MySQL 较小。
- 部分复杂窗口函数和高级 SQL 特性尚未完全支持。

## 对引擎开发者的参考价值

Materialize 是增量计算理论（Differential Dataflow）在数据库中的最完整实现，展示了如何将任意 SQL 查询转换为增量维护的数据流图。其差分数据流引擎的设计——在有向无环图中传播"变更集合"（differences）而非完整数据——是流式计算和物化视图领域的前沿研究成果。SOURCE/SINK 的抽象设计也为理解数据库与流处理系统的边界提供了参考。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/materialize.md) | **流式物化视图引擎——SOURCE 定义数据源（Kafka/PG CDC）**。`CREATE SOURCE FROM KAFKA CONNECTION ...` 从 Kafka 读取数据，`CREATE SOURCE FROM POSTGRES CONNECTION ...` 从 PG CDC 读取。TABLE 可直接 INSERT。对比 PostgreSQL（CREATE TABLE 标准）和 ksqlDB（STREAM/TABLE 绑定 Kafka），Materialize 的 SOURCE 抽象将外部数据流统一为关系表。 |
| [改表](../ddl/alter-table/materialize.md) | **ALTER 能力有限——SOURCE/SINK 属性修改**。对比 PostgreSQL（ALTER 灵活）和 ksqlDB（不支持 ALTER），Materialize 的 ALTER 主要用于修改连接属性。 |
| [索引](../ddl/indexes/materialize.md) | **INDEX 加速查询（内存中维护）——非传统 B-tree**。`CREATE INDEX ON view(col)` 在内存中维护物化视图的索引结构，加速 Pull Query。对比 PostgreSQL 的 B-tree/GIN（磁盘索引）和 ksqlDB（RocksDB 状态存储），Materialize 的索引是增量维护的内存结构。 |
| [约束](../ddl/constraints/materialize.md) | **无约束支持**——流处理定位不提供传统约束。数据质量由上游 SOURCE 保证。对比 PostgreSQL（完整约束）和 ksqlDB（同样无约束），Materialize 不执行数据完整性校验。 |
| [视图](../ddl/views/materialize.md) | **MATERIALIZED VIEW——核心功能，Differential Dataflow 增量维护**。`CREATE MATERIALIZED VIEW v AS SELECT ... JOIN ... GROUP BY ...` 定义增量物化视图，数据变更后毫秒级更新结果。支持任意复杂 SQL（包括多表 JOIN 和聚合）的增量计算。对比 PostgreSQL（REFRESH MATERIALIZED VIEW 全量刷新）和 BigQuery（自动增量但受限于单表），Materialize 的增量物化视图是最完整的——任意 SQL 查询都可增量维护。 |
| [序列与自增](../ddl/sequences/materialize.md) | **无 SEQUENCE/自增**——数据来自外部 SOURCE，无自增需求。对比 PostgreSQL 的 SERIAL/IDENTITY 和 ksqlDB（KEY 来自 Kafka），Materialize 不管理数据生成。 |
| [数据库/Schema/用户](../ddl/users-databases/materialize.md) | **Cluster/Database/Schema 三级命名空间 + RBAC**——Cluster 隔离计算资源，Database/Schema 组织对象。RBAC 权限管理（PG 兼容语法）。对比 PostgreSQL（Database/Schema 二级）和 ksqlDB（扁平命名），Materialize 的 Cluster 层提供工作负载隔离。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/materialize.md) | **无动态 SQL**——查询引擎定位不提供过程化编程。对比 PostgreSQL 的 EXECUTE 和 BigQuery 的 EXECUTE IMMEDIATE，Materialize 的查询是声明式的。 |
| [错误处理](../advanced/error-handling/materialize.md) | **无过程式错误处理**——SOURCE 读取错误通过系统日志和监控报告。对比 PostgreSQL 的 EXCEPTION WHEN 和 ksqlDB 的 DLQ，Materialize 的错误处理依赖运维监控。 |
| [执行计划](../advanced/explain/materialize.md) | **EXPLAIN 展示 Differential Dataflow 数据流计划**——显示查询编译后的数据流图（Filter/Map/Join/Reduce 操作符）。对比 PostgreSQL 的 EXPLAIN ANALYZE（关系代数计划）和 ksqlDB（Kafka Streams 拓扑），Materialize 的执行计划反映了 Differential Dataflow 的增量计算图。 |
| [锁机制](../advanced/locking/materialize.md) | **无锁——MVCC 快照读**。所有查询读取物化视图的一致快照，增量更新在后台异步执行。对比 PostgreSQL（行级 MVCC 锁）和 ksqlDB（分区级并行无锁），Materialize 的无锁快照读保证了查询和更新互不阻塞。 |
| [分区](../advanced/partitioning/materialize.md) | **无传统分区——数据流分片自动管理**。Differential Dataflow 引擎自动管理数据分片和并行计算。对比 PostgreSQL（声明式分区）和 ksqlDB（Kafka 分区透传），Materialize 的数据分布完全由引擎内部管理。 |
| [权限](../advanced/permissions/materialize.md) | **RBAC 权限模型（PG 兼容语法）**——GRANT/REVOKE 标准 SQL 权限管理。对比 PostgreSQL（RBAC 完整）和 ksqlDB（Kafka ACL 外部化），Materialize 的权限管理使用 PG 兼容语法，DBA 无学习成本。 |
| [存储过程](../advanced/stored-procedures/materialize.md) | **无存储过程**——流式引擎定位不提供过程化编程。对比 PostgreSQL 的 PL/pgSQL 和 ksqlDB（Java UDF），Materialize 不支持可编程扩展。 |
| [临时表](../advanced/temp-tables/materialize.md) | **TEMPORARY VIEW 支持**——会话级临时视图。对比 PostgreSQL 的 CREATE TEMP TABLE 和 ksqlDB（无临时表），Materialize 提供临时视图但不提供临时表。 |
| [事务](../advanced/transactions/materialize.md) | **Strict Serializable 一致性（最强级别）**——物化视图在任意时间点提供全局一致的快照读取。这是所有数据库中最强的一致性保证。对比 PostgreSQL（Serializable 隔离级别）和 ksqlDB（Exactly-Once 语义），Materialize 的 Strict Serializable 保证了物化视图的跨表一致性。 |
| [触发器](../advanced/triggers/materialize.md) | **无触发器——物化视图即增量触发**。MATERIALIZED VIEW 在上游数据变更时自动增量更新，本质上是"永久运行的触发器"。SUBSCRIBE 可订阅视图变更流。对比 PostgreSQL（BEFORE/AFTER 触发器）和 ksqlDB（持续查询），Materialize 的物化视图增量维护是最自然的事件驱动机制。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/materialize.md) | **DELETE 支持（TABLE 类型）——SOURCE 数据不可删除**。用户创建的 TABLE 支持 DELETE，但 SOURCE 导入的数据由上游控制。对比 PostgreSQL（任意表可 DELETE）和 ksqlDB（Tombstone 标记删除），Materialize 的 DELETE 仅对 TABLE 类型有效。 |
| [插入](../dml/insert/materialize.md) | **INSERT INTO TABLE 支持——SOURCE 由外部推送**。用户可直接 INSERT 到 TABLE，SOURCE 的数据由外部系统（Kafka/PG CDC）推送。对比 PostgreSQL（INSERT 标准）和 ksqlDB（INSERT INTO 写入 Kafka），Materialize 区分了用户可控数据（TABLE）和外部数据（SOURCE）。 |
| [更新](../dml/update/materialize.md) | **UPDATE 支持（TABLE 类型）**——标准 UPDATE 语法对用户 TABLE 有效。对比 PostgreSQL（UPDATE 标准）和 ksqlDB（无显式 UPDATE），Materialize 的 TABLE 支持标准 DML 操作。 |
| [Upsert](../dml/upsert/materialize.md) | **Upsert Source（Kafka Key 语义）+ ENVELOPE UPSERT**——`CREATE SOURCE ... ENVELOPE UPSERT` 将 Kafka 消息按 Key 语义解释为 Upsert（新值覆盖旧值）。对比 PostgreSQL 的 ON CONFLICT 和 ksqlDB（TABLE 天然 Upsert），Materialize 的 ENVELOPE UPSERT 在 SOURCE 层面实现 Upsert 语义。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/materialize.md) | **PG 兼容聚合——增量维护聚合结果**。SUM/COUNT/AVG/string_agg 等聚合在物化视图中增量维护（仅处理变更数据）。对比 PostgreSQL（聚合需全量计算）和 ksqlDB（窗口聚合），Materialize 的增量聚合是 Differential Dataflow 的核心能力。 |
| [条件函数](../functions/conditional/materialize.md) | **CASE/COALESCE/NULLIF（PG 兼容）**——完全继承 PG 条件函数。对比 PostgreSQL（相同函数集）和 ksqlDB（CASE/IF 基础），Materialize 的条件函数与 PG 一致。 |
| [日期函数](../functions/date-functions/materialize.md) | **PG 兼容日期函数 + mz_now() 逻辑时间**——mz_now() 返回 Materialize 的逻辑时间戳（非物理时钟），用于 Temporal Filter 实现滑动时间窗口。对比 PostgreSQL 的 now()（物理时钟）和 ksqlDB 的 ROWTIME（事件时间），Materialize 的 mz_now() 是增量计算中时间管理的关键。 |
| [数学函数](../functions/math-functions/materialize.md) | **PG 兼容数学函数**——完整数学函数集。对比 PostgreSQL（相同函数集）和 ksqlDB（基础数学函数），Materialize 数学函数与 PG 一致。 |
| [字符串函数](../functions/string-functions/materialize.md) | **PG 兼容字符串函数 + \|\| 拼接**——完整字符串函数集。对比 PostgreSQL（相同函数集）和 ksqlDB（基础字符串函数），Materialize 字符串函数与 PG 一致。 |
| [类型转换](../functions/type-conversion/materialize.md) | **CAST/:: 运算符（PG 兼容）**——PG 风格 `col::integer` 简洁转换。对比 PostgreSQL（:: 运算符原生）和 ksqlDB（CAST 标准），Materialize 类型转换与 PG 一致。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/materialize.md) | **WITH 标准支持（PG 兼容）**——CTE 在物化视图定义中可用。对比 PostgreSQL（WITH RECURSIVE 完整）和 ksqlDB（不支持 CTE），Materialize 的 CTE 支持是其 SQL 兼容性的重要优势。 |
| [全文搜索](../query/full-text-search/materialize.md) | **无全文搜索**——需依赖外部搜索引擎。对比 PostgreSQL 的 tsvector+GIN 和 Elasticsearch，Materialize 不提供文本搜索。 |
| [连接查询](../query/joins/materialize.md) | **JOIN 自动增量维护——Differential Dataflow 核心优势**。多表 JOIN 的物化视图在上游任意表变更时自动增量更新结果。这是 Materialize 最核心的技术优势——传统系统需全量重算的多表 JOIN 在这里毫秒级增量完成。对比 PostgreSQL（JOIN 需实时计算）和 BigQuery（物化视图不支持 JOIN），Materialize 的增量 JOIN 维护是行业领先的能力。 |
| [分页](../query/pagination/materialize.md) | **LIMIT/OFFSET（PG 兼容）——物化视图毫秒级响应**。查询物化视图时直接返回预计算结果，延迟极低。对比 PostgreSQL（查询需实时计算）和 BigQuery（按扫描量计费），Materialize 的物化视图使分页查询近乎零延迟。 |
| [行列转换](../query/pivot-unpivot/materialize.md) | **无原生 PIVOT——CASE+GROUP BY 模拟**。对比 Oracle（PIVOT 原生）和 BigQuery（PIVOT 原生），Materialize 与 PG 一样缺少原生 PIVOT。 |
| [集合操作](../query/set-operations/materialize.md) | **UNION ALL/EXCEPT ALL（增量维护）**——集合操作在物化视图中自动增量维护。对比 PostgreSQL（集合操作标准但需实时计算）和 ksqlDB（不支持 UNION），Materialize 的增量集合操作是独特优势。 |
| [子查询](../query/subquery/materialize.md) | **关联子查询（PG 兼容）+ 增量维护**——子查询在物化视图中可增量计算。对比 PostgreSQL（子查询实时计算）和 ksqlDB（不支持子查询），Materialize 的子查询可被增量物化。 |
| [窗口函数](../query/window-functions/materialize.md) | **窗口函数支持（PG 兼容）+ 增量维护**——ROW_NUMBER/RANK/LAG/LEAD 等窗口函数在物化视图中可增量维护。对比 PostgreSQL（窗口函数实时计算）和 ksqlDB（无标准窗口函数），Materialize 的增量窗口函数维护是前沿技术。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/materialize.md) | **generate_series（PG 兼容）**——可生成日期序列用于物化视图定义。对比 PostgreSQL（generate_series 标准）和 ksqlDB（不适用），Materialize 继承 PG 的序列生成能力。 |
| [去重](../scenarios/deduplication/materialize.md) | **DISTINCT ON/ROW_NUMBER（PG 兼容）+ 增量去重**——物化视图中的去重在上游数据变更时自动增量更新。对比 PostgreSQL 的 DISTINCT ON（实时计算）和 ksqlDB（TABLE 按 KEY 去重），Materialize 的增量去重是物化视图的自然能力。 |
| [区间检测](../scenarios/gap-detection/materialize.md) | **窗口函数（PG 兼容）**——LAG/LEAD 检测数据间隙，结果在物化视图中增量维护。对比 PostgreSQL（窗口函数实时计算）和 TimescaleDB 的 gapfill，Materialize 的间隙检测结果可实时物化。 |
| [层级查询](../scenarios/hierarchical-query/materialize.md) | **递归 CTE（有限支持）+ 增量维护**——WITH RECURSIVE 在 Materialize 中有限支持，递归物化视图可增量维护层级关系。对比 PostgreSQL（WITH RECURSIVE 完整）和 ksqlDB（不支持层级查询），Materialize 的递归能力在持续增强中。 |
| [JSON 展开](../scenarios/json-flatten/materialize.md) | **jsonb_each/jsonb_array_elements（PG 兼容）**——JSONB 函数继承 PG 能力。对比 PostgreSQL 的 JSONB+GIN（功能最强）和 ksqlDB 的 EXTRACTJSONFIELD，Materialize 继承 PG 的 JSONB 展开能力。 |
| [迁移速查](../scenarios/migration-cheatsheet/materialize.md) | **PG 兼容 SQL + 流式物化视图是核心差异**。关键注意：数据通过 SOURCE 导入（非直接 INSERT 到表）；MATERIALIZED VIEW 是核心功能（增量维护任意 SQL）；SUBSCRIBE 订阅视图变更；Strict Serializable 一致性最强；不支持存储过程/触发器；mz_now() 逻辑时间用于 Temporal Filter。 |
| [TopN 查询](../scenarios/ranking-top-n/materialize.md) | **ROW_NUMBER + LIMIT（PG 兼容）+ 物化视图实时排名**——TopN 物化视图在数据变更时自动更新排名结果，实现实时排行榜。对比 PostgreSQL（TopN 需实时计算）和 BigQuery（QUALIFY 简洁但非实时），Materialize 的增量 TopN 物化是实时排行的理想方案。 |
| [累计求和](../scenarios/running-total/materialize.md) | **SUM() OVER（PG 兼容）+ 增量计算**——窗口累计在物化视图中增量维护。对比 PostgreSQL（SUM() OVER 实时计算）和 TDengine 的 CSUM，Materialize 的增量累计是物化视图的自然能力。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/materialize.md) | **Temporal Filter + 物化视图增量维护**——使用 mz_now() Temporal Filter 过滤历史版本，物化视图自动维护最新维度值。对比 PostgreSQL 的 ON CONFLICT/MERGE 和 BigQuery 的 MERGE，Materialize 的 Temporal Filter 是 SCD 的独特实现方式。 |
| [字符串拆分](../scenarios/string-split-to-rows/materialize.md) | **regexp_split_to_table（PG 兼容）**——继承 PG 的字符串拆分函数。对比 PostgreSQL（string_to_array+unnest）和 ksqlDB（不支持拆分），Materialize 继承 PG 的拆分能力。 |
| [窗口分析](../scenarios/window-analytics/materialize.md) | **窗口函数（PG 兼容）+ 增量维护是核心优势**——移动平均、排名、占比等分析在物化视图中增量维护，上游数据变更后毫秒级更新分析结果。对比 PostgreSQL（窗口函数实时计算）和 BigQuery（窗口函数按需计算），Materialize 的增量窗口分析是实时 BI 仪表盘的理想后端。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/materialize.md) | **LIST/MAP/RECORD 类型（PG 兼容扩展）**——LIST 对应 PG 的 ARRAY，MAP 是 Materialize 独有的键值对类型，RECORD 对应 PG 的复合类型。对比 PostgreSQL 的 ARRAY（原生）和 ksqlDB 的 ARRAY/MAP/STRUCT，Materialize 的类型系统扩展了 PG 并增加了 MAP。 |
| [日期时间](../types/datetime/materialize.md) | **TIMESTAMP/DATE/TIME/INTERVAL（PG 兼容）+ mz_now()**——mz_now() 是 Materialize 的逻辑时间，用于 Temporal Filter 实现时间窗口。对比 PostgreSQL（now() 物理时钟）和 ksqlDB（ROWTIME 事件时间），mz_now() 是增量计算框架中管理时间的关键概念。 |
| [JSON](../types/json/materialize.md) | **JSONB（PG 兼容）+ jsonb_each/array_elements 展开**——JSONB 存储和查询能力继承 PG。SOURCE 的 JSON 格式数据自动解析为 JSONB。对比 PostgreSQL 的 JSONB+GIN（索引加速）和 ksqlDB（JSON 序列化格式），Materialize 的 JSONB 在物化视图中可增量维护。 |
| [数值类型](../types/numeric/materialize.md) | **INT/BIGINT/FLOAT/DOUBLE/NUMERIC（PG 兼容）**——标准数值类型体系。对比 PostgreSQL（相同类型体系）和 ksqlDB（INT/BIGINT/DOUBLE/DECIMAL），Materialize 数值类型与 PG 一致。 |
| [字符串类型](../types/string/materialize.md) | **TEXT/VARCHAR（PG 兼容）+ UTF-8**——TEXT 推荐，无长度限制。对比 PostgreSQL（TEXT 推荐）和 ksqlDB（VARCHAR/STRING），Materialize 字符串类型与 PG 一致。 |
