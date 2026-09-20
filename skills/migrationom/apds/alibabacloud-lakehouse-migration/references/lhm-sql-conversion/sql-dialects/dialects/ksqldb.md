# ksqlDB

**分类**: 流处理 SQL（Kafka）
**文件数**: 51 个 SQL 文件
**总行数**: 4208 行

## 概述与定位

ksqlDB 是 Confluent 公司开发的流处理 SQL 引擎，构建在 Apache Kafka Streams 之上。它让开发者可以用 SQL 语法对 Kafka 中持续流动的数据进行实时处理——无需编写 Java/Scala 代码。ksqlDB 定位于实时数据管道、事件驱动应用和流式 ETL 场景。其核心理念是将 Kafka Topic 抽象为 STREAM（不可变事件流）和 TABLE（可变状态表），用声明式 SQL 表达流处理逻辑。

## 历史与演进

- **2017 年**：Confluent 发布 KSQL 项目，首次将 SQL 引入 Kafka 流处理。
- **2019 年**：重命名为 ksqlDB，引入 Pull Query（点查询）能力和连接器集成。
- **2020 年**：增强物化视图和 REST API，向"事件流数据库"方向演进。
- **2021 年**：引入变量、ASSERT 语句和 Lambda 函数。
- **2022 年**：增强 JOIN 能力和性能优化。
- **2023-2025 年**：改进状态存储、增强容错能力，Confluent Cloud 全托管版持续演进。

## 核心设计思路

ksqlDB 的核心抽象是**STREAM 与 TABLE 的二元模型**。STREAM 表示不可变的事件序列（每条记录是一个追加事件），TABLE 表示可变的当前状态（相同 Key 的新记录覆盖旧记录）。所有数据存储在 Kafka Topic 中，ksqlDB 本身不管理持久化存储——它是 Kafka 之上的一个有状态流处理应用。查询分为 **Push Query**（`EMIT CHANGES`，持续推送结果）和 **Pull Query**（点查物化视图的当前状态）。

## 独特特色

- **STREAM vs TABLE**：`CREATE STREAM` 定义不可变事件流，`CREATE TABLE` 定义可变状态表——二者可相互转换。
- **EMIT CHANGES**：`SELECT * FROM stream EMIT CHANGES` 持续推送查询结果，实现实时监控。
- **Push/Pull 双模查询**：Push Query 订阅变更流，Pull Query 查询物化视图当前状态。
- **流式 JOIN**：支持 Stream-Stream、Stream-Table、Table-Table 多种 JOIN 模式，带时间窗口约束。
- **窗口聚合**：`WINDOW TUMBLING/HOPPING/SESSION` 支持滚动、跳跃和会话窗口。
- **连接器集成**：`CREATE SOURCE/SINK CONNECTOR` 直接管理 Kafka Connect 连接器。
- **Kafka 原生**：底层使用 Kafka Topic 存储数据，继承 Kafka 的持久性、分区和副本机制。

## 已知不足

- 不是通用关系型数据库——不支持 UPDATE/DELETE、事务、索引、外键等传统 SQL 特性。
- 查询能力有限：不支持子查询、CTE、复杂聚合和多层嵌套 JOIN。
- Pull Query 仅支持对物化视图的 Key 查找和简单过滤，不支持全表扫描。
- 状态存储（RocksDB）在大状态场景下可能成为性能瓶颈。
- 依赖 Kafka 集群，部署和运维复杂度包含 Kafka 本身。
- Schema 管理依赖 Confluent Schema Registry，增加了组件依赖。

## 对引擎开发者的参考价值

ksqlDB 展示了如何将 SQL 语义映射到流处理模型——STREAM/TABLE 二元抽象、Push/Pull 双模查询、以及流式 JOIN 的时间窗口语义是流 SQL 引擎设计的核心问题。其在 Kafka Streams 之上构建 SQL 层的方式展示了如何在已有流处理框架上叠加声明式查询能力。EMIT CHANGES 的持续查询模型也为理解流式物化视图提供了直观的参考。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/ksqldb.md) | **STREAM/TABLE 二元模型——Kafka Topic 绑定**。`CREATE STREAM events (...) WITH (KAFKA_TOPIC='events', VALUE_FORMAT='JSON')` 定义不可变事件流，`CREATE TABLE state (...) WITH (...)` 定义可变状态表。二者共享 Kafka 存储但语义不同。对比 PostgreSQL（CREATE TABLE 标准）和 Materialize（SOURCE 定义数据源），ksqlDB 的 STREAM/TABLE 二元抽象是流处理 SQL 的核心概念。 |
| [改表](../ddl/alter-table/ksqldb.md) | **不支持 ALTER 修改 Schema——需重建 STREAM/TABLE**。Schema 变更需先 DROP 再 CREATE（可能丢失消费偏移量）。对比 PostgreSQL（ALTER 灵活）和 Materialize（ALTER 能力有限），ksqlDB 的 Schema 演进最受限。 |
| [索引](../ddl/indexes/ksqldb.md) | **无索引——Kafka Streams 引擎按 KEY 分区**。数据通过 KEY 进行分区存储，Pull Query 按 KEY 查找使用 RocksDB 状态存储。对比 PostgreSQL（B-tree/GIN 索引）和 Materialize（INDEX 内存维护），ksqlDB 的"索引"由 Kafka 分区和 RocksDB 状态存储隐式提供。 |
| [约束](../ddl/constraints/ksqldb.md) | **无约束支持——数据校验在 Producer 端**。Schema Registry 提供 Schema 级别的类型校验，但无 PK/FK/CHECK 约束。对比 PostgreSQL（完整约束）和 Materialize（无约束），ksqlDB 的数据质量完全依赖上游 Producer。 |
| [视图](../ddl/views/ksqldb.md) | **CSAS/CTAS 持续查询 = 流式物化视图**——`CREATE TABLE result AS SELECT ... FROM stream GROUP BY ...` 创建持续更新的物化视图，数据变更时自动增量更新。对比 PostgreSQL（REFRESH MATERIALIZED VIEW 手动）和 Materialize（增量物化视图类似），ksqlDB 的持续查询是最自然的流式物化视图实现。 |
| [序列与自增](../ddl/sequences/ksqldb.md) | **无自增——KEY 来自 Kafka 消息 Key**。记录的唯一标识由 Kafka Producer 设定的 Message Key 决定。对比 PostgreSQL 的 SERIAL/IDENTITY 和 BigQuery 的 GENERATE_UUID()，ksqlDB 的 KEY 管理完全在 Kafka 生态中。 |
| [数据库/Schema/用户](../ddl/users-databases/ksqldb.md) | **无 Schema 概念——STREAM/TABLE 扁平命名**。所有对象在同一命名空间中。权限通过 Kafka ACL 或 Confluent RBAC 管理。对比 PostgreSQL（Database/Schema 二级）和 Materialize（Cluster/Database/Schema），ksqlDB 的命名空间最简单。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/ksqldb.md) | **无动态 SQL——REST API/CLI 提交查询**。查询通过 HTTP REST API 或 CLI 提交。对比 PostgreSQL 的 EXECUTE 和 BigQuery 的 EXECUTE IMMEDIATE，ksqlDB 不提供过程化编程能力。 |
| [错误处理](../advanced/error-handling/ksqldb.md) | **无过程式错误处理——Dead Letter Queue 异常消息**。处理失败的消息可路由到 DLQ（Dead Letter Queue）Topic 而非中断整个流处理。对比 PostgreSQL 的 EXCEPTION WHEN 和 BigQuery 的 SAFE_ 前缀，ksqlDB 的 DLQ 机制是流处理领域的标准错误处理模式。 |
| [执行计划](../advanced/explain/ksqldb.md) | **EXPLAIN 展示 Kafka Streams 拓扑**——显示查询对应的 Kafka Streams 处理拓扑图（Source/Processor/Sink 节点），而非传统的关系代数执行计划。对比 PostgreSQL 的 EXPLAIN ANALYZE（关系代数计划）和 Materialize（Differential Dataflow 计划），ksqlDB 的 EXPLAIN 反映了底层 Kafka Streams 架构。 |
| [锁机制](../advanced/locking/ksqldb.md) | **无锁——Kafka Streams 引擎分区级并行**。每个分区由单一线程处理，无锁竞争。并发度由 Kafka Topic 的分区数决定。对比 PostgreSQL（行级 MVCC 锁）和 Materialize（无锁 MVCC 快照），ksqlDB 的无锁模型源于 Kafka Streams 的分区隔离。 |
| [分区](../advanced/partitioning/ksqldb.md) | **Kafka 分区透传 + PARTITION BY 重分区**——STREAM/TABLE 继承底层 Kafka Topic 的分区。`PARTITION BY` 可重新分区数据（触发数据 Shuffle）。对比 PostgreSQL 的 PARTITION BY（逻辑分区）和 TDengine（VNODE 分片），ksqlDB 的分区直接映射 Kafka 物理分区。 |
| [权限](../advanced/permissions/ksqldb.md) | **ACL 集成 Kafka 权限 + RBAC（Confluent Platform）**——权限管理与 Kafka 的 ACL 或 Confluent Platform 的 RBAC 集成。对比 PostgreSQL 的 GRANT/REVOKE 和 Materialize 的 RBAC，ksqlDB 的权限管理完全外部化到 Kafka 安全框架。 |
| [存储过程](../advanced/stored-procedures/ksqldb.md) | **无存储过程**——流处理引擎定位不提供过程化编程。自定义逻辑通过 UDF/UDAF（Java 实现）扩展。对比 PostgreSQL 的 PL/pgSQL 和 Materialize（无存储过程），ksqlDB 通过 Java UDF 提供有限的可编程性。 |
| [临时表](../advanced/temp-tables/ksqldb.md) | **无临时表——所有查询结果持久化到 Kafka Topic**。CSAS/CTAS 创建的结果都写入 Kafka Topic（永久存储）。对比 PostgreSQL 的 CREATE TEMP TABLE 和 Materialize（TEMPORARY VIEW），ksqlDB 中不存在"临时"概念——一切皆 Kafka Topic。 |
| [事务](../advanced/transactions/ksqldb.md) | **Exactly-Once 语义（Kafka 事务）——非传统 ACID**。通过 Kafka 事务保证流处理的精确一次语义（每条消息恰好处理一次），但不支持传统 BEGIN/COMMIT/ROLLBACK。对比 PostgreSQL（完整 ACID）和 Materialize（Strict Serializable），ksqlDB 的"事务"概念是流处理领域的 Exactly-Once 保证。 |
| [触发器](../advanced/triggers/ksqldb.md) | **无触发器——持续查询本身即事件驱动**。CSAS/CTAS 持续查询在数据到达时自动执行，本质上就是"永久触发器"。对比 PostgreSQL（BEFORE/AFTER 触发器）和 TDengine（Stream 替代触发器），ksqlDB 的持续查询模型天然是事件驱动的。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/ksqldb.md) | **TOMBSTONE（NULL 值）标记删除——TABLE 语义**。发送 KEY 对应的 NULL 值消息（Kafka Tombstone）表示删除该 KEY。对比 PostgreSQL 的 DELETE（行级删除）和 Materialize（DELETE 支持 TABLE），ksqlDB 的删除语义来自 Kafka 的日志压缩（Log Compaction）机制。 |
| [插入](../dml/insert/ksqldb.md) | **INSERT INTO 写入 STREAM/TABLE（Kafka Topic）**——`INSERT INTO stream VALUES (...)` 将数据写入底层 Kafka Topic。对比 PostgreSQL 的 INSERT（写入磁盘表）和 Materialize（INSERT INTO TABLE），ksqlDB 的 INSERT 实质是向 Kafka Topic 发送消息。 |
| [更新](../dml/update/ksqldb.md) | **TABLE 语义按 KEY 更新最新值——非传统 UPDATE 语句**。向 TABLE 的底层 Topic 发送相同 KEY 的新消息即为"更新"。无显式 UPDATE 语句。对比 PostgreSQL 的 UPDATE（显式更新）和 Materialize（UPDATE 支持 TABLE），ksqlDB 的更新语义完全由 Kafka 的 KEY 覆盖机制实现。 |
| [Upsert](../dml/upsert/ksqldb.md) | **TABLE 语义天然 Upsert——按 KEY 覆盖**。TABLE 中相同 KEY 的新消息自动覆盖旧值，INSERT 即 Upsert。对比 PostgreSQL 的 ON CONFLICT 和 TDengine（时间戳覆盖），ksqlDB 的 TABLE 模型天然就是 Upsert 语义。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/ksqldb.md) | **COUNT/SUM/AVG + 窗口聚合（TUMBLING/HOPPING/SESSION）**——聚合必须在窗口内进行（流数据无终态）。`WINDOW TUMBLING (SIZE 1 HOUR)` 定义滚动窗口。对比 PostgreSQL（无窗口化聚合概念）和 Materialize（增量聚合），ksqlDB 的聚合与流式窗口深度绑定。 |
| [条件函数](../functions/conditional/ksqldb.md) | **CASE/WHEN/IF 基础条件函数**。对比 PostgreSQL（CASE/COALESCE/NULLIF 完整）和 MySQL 的 IF，ksqlDB 的条件函数覆盖基本场景。 |
| [日期函数](../functions/date-functions/ksqldb.md) | **TIMESTAMPADD/TIMESTAMPDIFF + FROM_UNIXTIME**——面向事件时间处理。ROWTIME 伪列提供事件时间。对比 PostgreSQL 的 date_trunc/extract 和 TimescaleDB 的 time_bucket，ksqlDB 的日期函数面向流式事件时间处理。 |
| [数学函数](../functions/math-functions/ksqldb.md) | **基础数学函数**——ABS/CEIL/FLOOR/ROUND 等。对比 PostgreSQL（完整数学函数）和 TDengine（基础+时序函数），ksqlDB 的数学函数覆盖基本需求。 |
| [字符串函数](../functions/string-functions/ksqldb.md) | **CONCAT/SUBSTRING/TRIM 基础函数**。对比 PostgreSQL（完整字符串函数）和 MySQL（CONCAT 为主），ksqlDB 的字符串函数覆盖基本需求。 |
| [类型转换](../functions/type-conversion/ksqldb.md) | **CAST 标准 + Schema Registry 类型绑定**——Schema Registry 定义 Avro/Protobuf/JSON Schema，类型在 Schema 层面管理。对比 PostgreSQL 的 CAST/:: 和 BigQuery 的 SAFE_CAST，ksqlDB 的类型系统与 Schema Registry 深度绑定。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/ksqldb.md) | **不支持 CTE——用嵌套查询或多步 CSAS 替代**。复杂查询拆分为多个 CSAS 步骤（每步创建中间 STREAM/TABLE）。对比 PostgreSQL（WITH 标准）和 Materialize（WITH 支持），CTE 缺失需通过多步物化替代。 |
| [全文搜索](../query/full-text-search/ksqldb.md) | **不支持全文搜索**——流处理引擎不提供文本搜索。对比 PostgreSQL 的 tsvector+GIN 和 Elasticsearch（专用搜索引擎），ksqlDB 缺少文本搜索能力。 |
| [连接查询](../query/joins/ksqldb.md) | **STREAM-STREAM / STREAM-TABLE / TABLE-TABLE JOIN（流特有）**——Stream-Stream JOIN 必须带 WITHIN 时间窗口约束（两个事件必须在指定时间内到达）。Stream-Table JOIN 用最新的 TABLE 状态丰富流事件。对比 PostgreSQL（标准 JOIN）和 Materialize（增量 JOIN），ksqlDB 的流式 JOIN 语义是流处理领域的核心抽象。 |
| [分页](../query/pagination/ksqldb.md) | **不支持传统分页——Push Query 无终态，LIMIT 仅 Pull Query**。Push Query（EMIT CHANGES）持续输出无法分页。Pull Query 支持 LIMIT 限制返回行数。对比 PostgreSQL 的 LIMIT/OFFSET 和 BigQuery 的 LIMIT，ksqlDB 的分页受限于流处理模型。 |
| [行列转换](../query/pivot-unpivot/ksqldb.md) | **不支持 PIVOT**——流处理引擎不提供行列转换。对比 Oracle（PIVOT 原生）和 BigQuery（PIVOT 原生），ksqlDB 缺少行列转换能力。 |
| [集合操作](../query/set-operations/ksqldb.md) | **不支持 UNION/INTERSECT/EXCEPT**——合并多个 STREAM 需通过 INSERT INTO 写入同一目标 STREAM。对比 PostgreSQL（集合操作完整）和 Materialize（UNION ALL 增量维护），ksqlDB 用 INSERT INTO 替代 UNION。 |
| [子查询](../query/subquery/ksqldb.md) | **不支持子查询——用多步 CSAS 替代**。每个中间步骤创建一个 STREAM/TABLE，后续步骤从中间结果读取。对比 PostgreSQL（子查询完整）和 Materialize（子查询支持），ksqlDB 用多步物化替代子查询。 |
| [窗口函数](../query/window-functions/ksqldb.md) | **TUMBLING/HOPPING/SESSION 窗口（流处理独有）——无标准 OVER 子句**。`SELECT ... FROM stream WINDOW TUMBLING (SIZE 1 HOUR)` 定义流式窗口。无 ROW_NUMBER/LAG/LEAD 等标准 OLAP 窗口函数。对比 PostgreSQL 的 OVER（标准分析窗口）和 TDengine 的 STATE/SESSION_WINDOW，ksqlDB 的窗口模型完全面向流处理。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/ksqldb.md) | **不适用——流处理场景无静态日期填充需求**。流数据按事件到达时间处理。对比 PostgreSQL 的 generate_series 和 TimescaleDB 的 gapfill，ksqlDB 的流模型不涉及静态数据填充。 |
| [去重](../scenarios/deduplication/ksqldb.md) | **LATEST_BY_OFFSET 去重 + TABLE 语义按 KEY 自动去重**——LATEST_BY_OFFSET(col) 取同 KEY 最新偏移量的值。TABLE 语义天然按 KEY 保留最新记录。对比 PostgreSQL 的 DISTINCT ON 和 BigQuery 的 QUALIFY，ksqlDB 的 TABLE 语义提供最自然的按 KEY 去重。 |
| [区间检测](../scenarios/gap-detection/ksqldb.md) | **STREAM-STREAM JOIN WITHIN 时间窗口**——通过 WITHIN 子句检测两个事件流之间的时间间隙。对比 PostgreSQL 的 LAG/LEAD 窗口函数和 TimescaleDB 的 gapfill，ksqlDB 的间隙检测基于流式 JOIN 的时间窗口约束。 |
| [层级查询](../scenarios/hierarchical-query/ksqldb.md) | **不支持层级查询**——流处理引擎不处理层级关系。对比 PostgreSQL（WITH RECURSIVE）和 Oracle（CONNECT BY），ksqlDB 不涉及层级数据建模。 |
| [JSON 展开](../scenarios/json-flatten/ksqldb.md) | **EXTRACTJSONFIELD + 结构化 Schema 自动映射**——JSON 格式的 Kafka 消息可自动映射为 STRUCT 类型字段。EXPLODE(array) 可展开数组。对比 PostgreSQL 的 jsonb_array_elements 和 BigQuery 的 JSON_QUERY_ARRAY+UNNEST，ksqlDB 的 Schema Registry 自动映射是最自然的 JSON 处理方式。 |
| [迁移速查](../scenarios/migration-cheatsheet/ksqldb.md) | **STREAM/TABLE 是核心概念——非传统 SQL，Kafka 原生**。关键差异：STREAM vs TABLE 二元模型；Push Query（EMIT CHANGES）vs Pull Query；无 UPDATE/DELETE/事务/索引；WINDOW 替代标准窗口函数；无 CTE/子查询；所有数据持久化到 Kafka Topic；Schema 由 Schema Registry 管理。 |
| [TopN 查询](../scenarios/ranking-top-n/ksqldb.md) | **TOPK/TOPKDISTINCT 聚合函数（独有）**——`SELECT TOPK(col, 5) FROM stream WINDOW ...` 在流式窗口内取 Top K 值。对比 PostgreSQL 的 ROW_NUMBER+LIMIT 和 TDengine 的 TOP（类似），ksqlDB 的 TOPK 是流处理场景下的便捷 TopN 实现。 |
| [累计求和](../scenarios/running-total/ksqldb.md) | **窗口聚合 SUM——无标准 OVER 子句**。累计需通过 TABLE 语义维护 SUM 状态。对比 PostgreSQL 的 SUM() OVER(ORDER BY ...) 和 TDengine 的 CSUM，ksqlDB 的累计求和通过 TABLE 聚合状态实现。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/ksqldb.md) | **TABLE 语义天然维护最新值——SCD Type 1 自动实现**。TABLE 按 KEY 自动覆盖旧值，天然实现 SCD Type 1。对比 PostgreSQL 的 ON CONFLICT/MERGE 和 BigQuery 的 MERGE，ksqlDB 的 TABLE 模型是最自然的维度最新值维护。 |
| [字符串拆分](../scenarios/string-split-to-rows/ksqldb.md) | **不支持原生字符串拆分展开**——SPLIT(str, delimiter) 返回 ARRAY，但无 EXPLODE 展开为多行（部分版本支持 EXPLODE）。对比 PostgreSQL 的 string_to_array+unnest 和 BigQuery 的 SPLIT+UNNEST，ksqlDB 的字符串拆分能力有限。 |
| [窗口分析](../scenarios/window-analytics/ksqldb.md) | **TUMBLING/HOPPING/SESSION 窗口聚合——流式独有分析模式**。窗口结果持续更新并写入 Kafka Topic。GRACE PERIOD 允许迟到事件在窗口关闭后仍被处理。对比 PostgreSQL 的 ROWS/RANGE 帧（静态分析）和 TDengine 的 INTERVAL/SESSION（类似流式窗口），ksqlDB 的窗口分析是最纯粹的流式实现。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/ksqldb.md) | **ARRAY/MAP/STRUCT 类型 + Schema Registry 定义**——STRUCT 嵌套类型由 Avro/Protobuf Schema 定义。EXPLODE(array) 可展开数组。对比 BigQuery 的 STRUCT/ARRAY（一等公民）和 PostgreSQL 的 ARRAY，ksqlDB 的复合类型与 Schema Registry 深度绑定。 |
| [日期时间](../types/datetime/ksqldb.md) | **TIMESTAMP 毫秒精度 + 事件时间 ROWTIME**——ROWTIME 伪列提供每条记录的事件时间戳。对比 PostgreSQL 的 TIMESTAMP/TIMESTAMPTZ 和 TDengine 的 TIMESTAMP（纳秒），ksqlDB 的时间类型面向事件流处理。 |
| [JSON](../types/json/ksqldb.md) | **JSON 序列化格式 + EXTRACTJSONFIELD 路径查询**——JSON 是 Kafka 消息最常见的序列化格式。WITH (VALUE_FORMAT='JSON') 指定 JSON 反序列化。对比 PostgreSQL 的 JSONB（原生类型+索引）和 Materialize（JSONB PG 兼容），ksqlDB 的 JSON 处理在 Kafka 序列化层面进行。 |
| [数值类型](../types/numeric/ksqldb.md) | **INT/BIGINT/DOUBLE/DECIMAL 基础类型**——类型系统与 Kafka Schema Registry 的类型映射对齐。对比 PostgreSQL（完整数值类型）和 TDengine（无 DECIMAL），ksqlDB 的数值类型覆盖基本需求。 |
| [字符串类型](../types/string/ksqldb.md) | **VARCHAR/STRING 标准 + Schema Registry 管理**——字符串类型由 Schema Registry 定义和校验。对比 PostgreSQL 的 TEXT 和 BigQuery 的 STRING，ksqlDB 的字符串类型通过 Schema Registry 实现类型安全。 |
