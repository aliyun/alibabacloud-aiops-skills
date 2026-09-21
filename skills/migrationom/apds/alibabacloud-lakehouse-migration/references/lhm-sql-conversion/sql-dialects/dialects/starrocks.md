# StarRocks

**分类**: MPP 分析数据库
**文件数**: 51 个 SQL 文件
**总行数**: 4301 行

> **关键人物**：[李超等](../docs/people/doris-starrocks-founders.md)（2020 分叉）

## 概述与定位

StarRocks 是一款高性能 MPP 分析数据库，2020 年从 Apache Doris 分叉而来（最初名为 DorisDB），由 StarRocks Inc. 主导开发。StarRocks 定位于"极速统一分析"——在一个引擎中同时满足实时分析、Ad-hoc 查询、多维报表和数据湖分析需求。它以向量化执行引擎、CBO 优化器和灵活的存储模型为核心竞争力，在中国互联网、电商、游戏和金融行业有快速增长的用户群。

## 历史与演进

- **2020 年**：从 Apache Doris 分叉，以 DorisDB 品牌独立开发，重构优化器和执行引擎。
- **2021 年**：更名为 StarRocks，开源（Apache 2.0 许可），1.x 版本引入全新 CBO 优化器。
- **2022 年**：2.x 版本引入 Primary Key 模型（实时更新）、外部表支持（Hive/Iceberg/Hudi）、资源组。
- **2023 年**：3.x 版本引入存算分离架构、共享数据（Shared-Data）模式、物化视图增强、数据湖分析加速。
- **2024-2025 年**：推进 AI 集成（向量索引）、增强半结构化数据处理（JSON/Struct/Map/Array）、Pipe 持续数据加载。

## 核心设计思路

1. **FE + BE 架构**：FE（Frontend）负责 SQL 解析、CBO 优化和元数据管理，BE（Backend）负责数据存储和向量化执行。
2. **四种数据模型**：Duplicate Key（明细保留）、Aggregate Key（预聚合）、Unique Key（唯一键最新值）、Primary Key（主键实时更新），每种模型对应不同的写入和查询模式。
3. **全面向量化**：从存储层扫描到所有算子（JOIN、聚合、排序、窗口函数）均基于列式向量化执行，利用 SIMD 指令加速。
4. **CBO 优化器**：自研的基于 Cascades 框架的成本优化器，支持 Join Reorder、子查询去关联、相关子查询优化等高级变换。

## 独特特色

| 特性 | 说明 |
|---|---|
| **四种数据模型** | Duplicate Key（全量明细）、Aggregate Key（SUM/MAX/MIN/REPLACE 预聚合）、Unique Key（去重取最新）、Primary Key（支持实时 UPDATE/DELETE）。 |
| **物化视图** | 支持同步和异步物化视图，CBO 可自动改写查询命中物化视图，支持基于外部表的物化视图。 |
| **向量化执行** | 全链路向量化——扫描、表达式计算、聚合、JOIN、排序均在列式向量上操作，减少虚函数调用和内存拷贝。 |
| **存算分离（Shared-Data）** | 数据持久化在对象存储（S3/OSS/GCS），BE 节点无状态可弹性伸缩，本地 SSD 作缓存层。 |
| **多源联邦查询** | 通过 Catalog 机制直接查询 Hive/Iceberg/Hudi/Delta Lake/MySQL/PostgreSQL/Elasticsearch 等数据源。 |
| **Global Runtime Filter** | 跨 Fragment 的全局 Runtime Filter，在分布式 JOIN 中将 Build 侧的 Filter 广播到所有 Probe 侧节点。 |
| **Pipe 持续加载** | `CREATE PIPE` 实现从对象存储到 StarRocks 的持续自动数据加载，类似 Snowpipe。 |

## 已知不足

- **多语句事务（4.0+）**：StarRocks 4.0 引入多语句事务支持，支持 BEGIN/COMMIT/ROLLBACK，实现多表原子写入。这是从分析引擎向 HTAP 演进的关键一步。
- **ASOF JOIN（4.0+）**：时序近似匹配 JOIN，按时间戳找到 ≤ 当前行的最近匹配。对时序分析（股票报价匹配、IoT 传感器对齐）原生支持。对标 DuckDB ASOF JOIN、ClickHouse asofJoin。
- **JSON 一等公民（4.0+）**：JSON 类型查询性能提升 3-15×，无需 ETL 展平即可高效分析。内部自动列式存储 JSON 子字段。
- **事务支持有限（4.0 前）**：4.0 之前不支持多语句事务，每次数据导入（Load）是一个原子操作。
- **与 Doris 的竞争混淆**：与 Apache Doris 同源且功能高度重合，社区用户在选型时经常困惑。
- **存储过程缺失**：不支持存储过程、触发器和游标，复杂业务逻辑需在应用层实现。
- **单表规模限制**：虽然是 MPP 架构，但单表数据规模超过数百亿行后，分桶和分区策略的调优难度增大。
- **UPDATE/DELETE 模型限制**：仅 Primary Key / Unique Key 模型支持行级变更，Duplicate / Aggregate 模型不支持。

## 对引擎开发者的参考价值

- **Cascades CBO 实现**：StarRocks 的优化器基于 Columbia/Cascades 框架，其 Rule 设计和 Cost Model 实现对自研优化器有直接参考。
- **全链路向量化实践**：从 Scan 到 Sink 所有算子均基于列式批处理的实现，展示了彻底向量化的性能收益和工程挑战。
- **Primary Key 模型**：基于 Delete + Insert 的实时更新模型（Merge-on-Read / Merge-on-Write），对实时可变列存表的设计有参考。
- **Global Runtime Filter**：跨节点广播 Bloom Filter / Min-Max Filter 的分布式实现，是优化星型模型查询的关键技术。
- **存算分离 + 缓存层**：数据在对象存储、BE 本地 SSD 作为 Cache 的分层存储设计，对云原生分析引擎有直接参考。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/starrocks.md) | **PRIMARY KEY 作为独立模型是 StarRocks 与 Doris 的核心差异**——Primary Key 模型基于 Delete+Insert 语义支持实时 UPDATE/DELETE（对比 Doris Unique Key 的 Merge-on-Read 旧方案）。四种模型：Duplicate Key（明细）、Aggregate Key（预聚合）、Unique Key（去重取最新）、Primary Key（实时更新）。DISTRIBUTED BY HASH 指定分桶。对比 ClickHouse（MergeTree 引擎家族）和 BigQuery（用户无需选择模型），StarRocks 的 Primary Key 模型在实时更新场景中性能最优。 |
| [改表](../ddl/alter-table/starrocks.md) | **Fast Schema Evolution(3.0+) 毫秒级列增删改——比 Doris Light Schema Change 更快**。纯元数据操作，不触发数据重写。ROLLUP 物化索引和物化视图可通过 ALTER 动态管理。对比 Snowflake（ALTER 瞬时元数据操作）和 ClickHouse（ADD/DROP 轻量但 MODIFY 异步 Mutation），StarRocks 的 Fast Schema Evolution 在 MPP 引擎中与 Snowflake 并列最快。 |
| [索引](../ddl/indexes/starrocks.md) | **Short Key 前缀索引+Bitmap+Bloom Filter+倒排索引+Zone Map 自动五层体系**——Zone Map 自动为每列维护 min/max 元数据（无需手动创建）。倒排索引(3.1+)支持全文检索。对比 Doris（索引体系类似但 Zone Map 需手动）和 ClickHouse（稀疏索引+跳数索引），StarRocks 的 Zone Map 自动化程度最高。 |
| [约束](../ddl/constraints/starrocks.md) | **无传统 PK/FK/UNIQUE/CHECK 约束——数据模型替代约束功能**。Primary Key/Unique Key 模型通过 Key 列自动保证唯一性。对比 BigQuery/Snowflake（PK/FK NOT ENFORCED 有元数据意义）和 Doris（相同设计），StarRocks 与 Doris 一样用数据模型替代约束声明。 |
| [视图](../ddl/views/starrocks.md) | **同步/异步物化视图(2.5+)——CBO 自动查询改写是核心优势**。异步物化视图支持基于外部表（Hive/Iceberg/Hudi）的增量刷新。CBO 可透明改写查询命中物化视图。对比 BigQuery（物化视图自动刷新+智能改写）和 Doris（ROLLUP 自动路由），StarRocks 的异步物化视图支持外部表是独有优势。 |
| [序列与自增](../ddl/sequences/starrocks.md) | **AUTO_INCREMENT(3.0+) 支持——分布式环境下不保证全局连续**。与 Doris 的 AUTO_INCREMENT 类似但版本略早。UUID 是通用替代方案。对比 BigQuery（无自增仅 UUID）和 Snowflake（AUTOINCREMENT 不保证连续），StarRocks 的自增实现标准。 |
| [数据库/Schema/用户](../ddl/users-databases/starrocks.md) | **MySQL 协议兼容+RBAC+Resource Group 资源隔离**——Resource Group 按 CPU/Memory/IO 配额隔离不同业务负载。External Catalog(3.0+)权限管理可控制外部数据源访问。对比 Snowflake（Virtual Warehouse 计算隔离最彻底）和 Doris（WorkloadGroup 类似），StarRocks 的 Resource Group 在 MPP 引擎中资源隔离最细粒度。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/starrocks.md) | **无存储过程/动态 SQL——与 Doris/ClickHouse 相同的 OLAP 引擎定位**。所有过程化逻辑在应用层或调度系统实现。对比 Snowflake（多语言存储过程+EXECUTE IMMEDIATE）和 MaxCompute（Script Mode），StarRocks 在过程式能力方面最弱。 |
| [错误处理](../advanced/error-handling/starrocks.md) | **无过程式错误处理——查询或导入失败返回错误码**。Stream Load 返回详细错误信息。对比 BigQuery（BEGIN...EXCEPTION）和 Snowflake（EXCEPTION 块），StarRocks 完全没有 SQL 层错误处理。 |
| [执行计划](../advanced/explain/starrocks.md) | **EXPLAIN+EXPLAIN ANALYZE 展示 Pipeline 执行引擎详细信息**——可查看 Pipeline 并行度、Runtime Filter 传播和 CBO 代价估算。EXPLAIN ANALYZE 实际执行并展示真实指标。对比 Spark（EXPLAIN EXTENDED 四阶段变换）和 ClickHouse（EXPLAIN PIPELINE），StarRocks 的 EXPLAIN ANALYZE 提供最真实的执行反馈。 |
| [锁机制](../advanced/locking/starrocks.md) | **无行级锁——Primary Key 模型基于 Delete+Insert 语义实现并发控制**。每次导入生成新版本，读取时取最新版本。4.0+ 多语句事务引入后并发控制增强。对比 Snowflake（乐观并发自动管理）和 PG（行级悲观锁 MVCC），StarRocks 的并发模型以导入任务为粒度。 |
| [分区](../advanced/partitioning/starrocks.md) | **PARTITION BY RANGE+DISTRIBUTED BY HASH 双层 + Expression 分区(3.1+)**——Expression 分区支持 `PARTITION BY date_trunc('month', dt)` 自动按表达式创建分区（无需手动枚举范围）。动态分区自动创建和清理。对比 Doris（RANGE+HASH 双层相同）和 BigQuery（单层分区），StarRocks 的 Expression 分区是对 Doris 的重要改进。 |
| [权限](../advanced/permissions/starrocks.md) | **MySQL 兼容权限+RBAC+External Catalog 权限管理**——External Catalog 权限可控制对 Hive/Iceberg/Hudi 等外部数据源的访问。对比 Snowflake（RBAC+DAC+FUTURE GRANTS 最完善）和 Doris（MySQL 兼容权限类似），StarRocks 的 External Catalog 权限管理是独有优势。 |
| [存储过程](../advanced/stored-procedures/starrocks.md) | **无存储过程——OLAP 引擎定位不提供过程式编程**。与 Doris/ClickHouse 相同。对比 Snowflake（多语言存储过程最强）和 Oracle（PL/SQL），StarRocks 完全没有过程式编程。 |
| [临时表](../advanced/temp-tables/starrocks.md) | **无临时表——OLAP 引擎定位下无会话级临时存储**。替代方案：CTE 或短生命周期普通表。对比 BigQuery（_SESSION 临时表）和 Snowflake（TEMPORARY+TRANSIENT），StarRocks 缺乏临时表支持。 |
| [事务](../advanced/transactions/starrocks.md) | **4.0+ 引入多语句事务(BEGIN/COMMIT/ROLLBACK)——从分析引擎向 HTAP 演进的关键一步**。4.0 之前每次导入是一个原子操作（与 Doris 相同）。多语句事务支持多表原子写入。对比 Snowflake（ACID 长期支持）和 Doris（无多语句事务），StarRocks 4.0 的事务能力在 MPP 引擎中领先。 |
| [触发器](../advanced/triggers/starrocks.md) | **不支持触发器**——替代方案：异步物化视图自动刷新、Pipe 持续加载。对比 ClickHouse（物化视图=INSERT 触发器）和 Snowflake（Streams+Tasks），StarRocks 用物化视图和 Pipe 覆盖了触发器的主要场景。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/starrocks.md) | **DELETE(Primary Key 模型)实时删除——Duplicate/Aggregate 模型不支持行级删除**。Primary Key 模型通过标记删除实现，查询时自动过滤。对比 Doris（Unique 模型 DELETE）和 ClickHouse（Lightweight Delete 22.8+），StarRocks 的 Primary Key 模型删除性能最优（Merge-on-Write 写入时即完成合并）。 |
| [插入](../dml/insert/starrocks.md) | **INSERT INTO+Stream Load/Broker Load+Pipe(3.2+) 持续导入**——Pipe 实现从对象存储(S3/OSS/GCS)到 StarRocks 的持续自动加载，类似 Snowflake Snowpipe。Stream Load 通过 HTTP 接口实时推送。对比 Snowflake（COPY INTO+Snowpipe 最成熟）和 Doris（Stream Load 类似），StarRocks 的 Pipe 是 MPP 引擎中最接近 Snowpipe 的方案。 |
| [更新](../dml/update/starrocks.md) | **UPDATE(Primary Key 模型)+Partial Update 部分列更新**——Partial Update 只更新指定列，避免全行重写（宽表场景性能提升显著）。Duplicate/Aggregate 模型不支持行级更新。对比 BigQuery/Snowflake（UPDATE 标准但重写微分区）和 Doris（Partial Column Update 2.0+ 类似），StarRocks 和 Doris 的 Partial Update 是 MPP 引擎独有的优化。 |
| [Upsert](../dml/upsert/starrocks.md) | **Primary Key 模型天然 Upsert——INSERT 即按主键覆盖旧行**。无需 MERGE 语句，写入时即完成去重和更新。Primary Key 的 Merge-on-Write 确保查询时无需额外合并。对比 BigQuery/Snowflake（MERGE INTO 标准 SQL）和 Doris（Unique 模型 INSERT 即 Upsert），StarRocks 的 Primary Key 模型在 Upsert 性能上领先 Doris 的 Unique Key（Merge-on-Write vs Merge-on-Read）。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/starrocks.md) | **GROUPING SETS/CUBE/ROLLUP 完整+bitmap_union/hll_union 预聚合**——bitmap_union 基于 Roaring Bitmap 实现精确去重计数（与 Doris 相同）。hll_union 提供 HyperLogLog 近似去重。对比 BigQuery 的 APPROX_COUNT_DISTINCT 和 ClickHouse 的 -If/-State 组合后缀（最灵活），StarRocks 的 bitmap/hll 预聚合在广告和用户分析场景中与 Doris 并列。 |
| [条件函数](../functions/conditional/starrocks.md) | **IF/CASE/COALESCE 兼容 MySQL 语法**——行为与 MySQL 完全一致。对比 BigQuery 的 SAFE_ 前缀和 Snowflake 的 IFF，StarRocks 的条件函数完全 MySQL 风格。 |
| [日期函数](../functions/date-functions/starrocks.md) | **DATE_FORMAT/DATE_ADD/DATEDIFF 兼容 MySQL 命名**——与 Doris 的日期函数集几乎完全相同（同源）。对比 BigQuery 的 DATE_TRUNC（标准命名）和 Snowflake 的 DATEADD/DATEDIFF，StarRocks 的日期函数对 MySQL 用户零学习成本。 |
| [数学函数](../functions/math-functions/starrocks.md) | **完整数学函数集——向量化执行加速计算**。除零行为与 MySQL 一致（返回 NULL）。对比 BigQuery 的 SAFE_DIVIDE 和 PG 的除零报错，StarRocks 继承了 MySQL 的宽松错误处理。 |
| [字符串函数](../functions/string-functions/starrocks.md) | **CONCAT/SUBSTR/REGEXP 兼容 MySQL——与 Doris 函数集几乎相同**。SPLIT_PART 按位置提取。对比 BigQuery 的 SPLIT 返回 ARRAY 和 Snowflake 的 SPLIT_PART，StarRocks 的字符串函数对 MySQL 用户最友好。 |
| [类型转换](../functions/type-conversion/starrocks.md) | **CAST 标准（MySQL 兼容），隐式转换规则与 MySQL 一致**——无 TRY_CAST 安全转换函数。对比 BigQuery 的 SAFE_CAST 和 Snowflake 的 TRY_CAST，StarRocks 缺乏安全转换函数（与 Doris 相同的短板）。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/starrocks.md) | **WITH 标准+递归 CTE 完整支持**——CBO 优化器可对 CTE 做自动物化决策。对比 Doris（2.1+ 才支持递归 CTE）和 PG（长期支持），StarRocks 的递归 CTE 引入时间与 Doris 相近。 |
| [全文搜索](../query/full-text-search/starrocks.md) | **倒排索引全文搜索(3.1+)+ngram bloom filter 模糊匹配**——ngram bloom filter 支持 LIKE '%keyword%' 加速（对比 ClickHouse 的 ngrambf_v1 类似思路）。对比 BigQuery（SEARCH INDEX 2023+）和 Doris（CLucene 倒排索引 2.0+），StarRocks 的全文搜索引入稍晚但 ngram bloom filter 是独有的模糊匹配优化。 |
| [连接查询](../query/joins/starrocks.md) | **Broadcast/Shuffle/Colocate/Bucket JOIN+Global Runtime Filter 跨节点加速**——Global Runtime Filter 在 Build 侧动态生成 Bloom Filter/Min-Max Filter 并广播到所有 Probe 侧节点（跨 Fragment 全局传播）。Colocate Join 预分配相同分桶到同节点避免 Shuffle。对比 Doris（Runtime Filter 类似但全局传播不如 StarRocks 彻底）和 Spark（AQE 运行时自动切换），StarRocks 的 Global Runtime Filter 在星型模型查询中效果最显著。 |
| [分页](../query/pagination/starrocks.md) | **LIMIT/OFFSET 完全兼容 MySQL 语法**——与 Doris 相同，深度分页性能退化。对比 BigQuery（按扫描量计费不受 OFFSET 影响）和 TiDB（分布式分页需 Keyset），StarRocks 的分页最接近单机 MySQL。 |
| [行列转换](../query/pivot-unpivot/starrocks.md) | **无原生 PIVOT/UNPIVOT——需 CASE+GROUP BY 手动实现**。UNNEST(3.1+)支持 ARRAY 展开为行。对比 BigQuery/Snowflake 的原生 PIVOT 和 Doris（同样无 PIVOT），StarRocks 缺乏行转列语法糖。 |
| [集合操作](../query/set-operations/starrocks.md) | **UNION/INTERSECT/EXCEPT ALL/DISTINCT 完整支持**——与 Doris 功能相同。对比 ClickHouse（UNION 默认 DISTINCT）和 Hive（2.0+ 才完整），StarRocks 的集合操作标准完备。 |
| [子查询](../query/subquery/starrocks.md) | **IN/EXISTS 子查询完整，CBO 自动去关联化优化**——Cascades 框架 CBO 可将关联子查询转为 Semi/Anti Join，优化质量领先 Doris 的 Nereids。对比 Spark（Catalyst 去关联化）和 PG（成熟子查询优化），StarRocks 的 CBO 在 MPP 引擎中子查询优化最强。 |
| [窗口函数](../query/window-functions/starrocks.md) | **完整窗口函数+Pipeline 引擎优化——向量化执行加速窗口计算**。ROW_NUMBER/RANK/LAG/LEAD/SUM OVER 等全部支持。无 QUALIFY 子句。对比 BigQuery/Snowflake 的 QUALIFY 和 ClickHouse（窗口函数性能不如聚合函数），StarRocks 的 Pipeline 引擎使窗口函数性能优于 ClickHouse。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/starrocks.md) | **无 generate_series——需预建辅助日期表 LEFT JOIN 填充**。与 Doris 相同的限制。对比 BigQuery 的 GENERATE_DATE_ARRAY+UNNEST 和 ClickHouse 的 WITH FILL（独有语法最简），StarRocks 的日期序列生成最为繁琐。 |
| [去重](../scenarios/deduplication/starrocks.md) | **Primary Key 模型写入时即去重——查询无需额外处理（Merge-on-Write）**。对比 Doris Unique Key 的 Merge-on-Read（查询时才合并）和 ClickHouse（ReplacingMergeTree 合并时去重需 FINAL），StarRocks 的 Primary Key 去重效率最高——写入稍慢但查询零额外开销。ROW_NUMBER+CTE 也可用于查询层去重。 |
| [区间检测](../scenarios/gap-detection/starrocks.md) | **LAG/LEAD 窗口函数检测连续性——标准方案，Pipeline 引擎加速**。对比 ClickHouse 的 WITH FILL（独有语法最简洁）和 PG 的 generate_series+LEFT JOIN，StarRocks 用通用窗口函数实现。 |
| [层级查询](../scenarios/hierarchical-query/starrocks.md) | **递归 CTE 完整支持**——对比 Doris（2.1+ 才支持）和 ClickHouse（24.x+ 才支持），StarRocks 的递归 CTE 引入时间适中。 |
| [JSON 展开](../scenarios/json-flatten/starrocks.md) | **JSON_EXTRACT+json_each(3.1+)展开 JSON 对象+UNNEST 展开数组**——json_each 将 JSON 对象展开为 key-value 行。JSON 一等公民(4.0+)：查询性能提升 3-15 倍，内部自动列式存储 JSON 子字段（Flat JSON 优化）。对比 Snowflake 的 LATERAL FLATTEN（最优雅）和 Doris 的 Variant+倒排索引，StarRocks 4.0 的 JSON 列化性能最强。 |
| [迁移速查](../scenarios/migration-cheatsheet/starrocks.md) | **MySQL 协议兼容+Doris 同源——与 Doris 的核心差异在三点**：Primary Key 模型（vs Doris Unique Key）实时更新更强、存算分离 Shared-Data 架构更成熟、CBO 优化器质量更高。数据模型选择+物化视图策略是迁移核心概念。对比 TiDB（MySQL 高度兼容但 HTAP）和 Doris（功能高度重合），StarRocks 和 Doris 的选型是中国 OLAP 市场最常见的困惑。 |
| [TopN 查询](../scenarios/ranking-top-n/starrocks.md) | **ROW_NUMBER+窗口函数标准模式——无 QUALIFY 需子查询包装**。Pipeline 引擎对 TopN 有专门的算子优化。对比 BigQuery/Snowflake 的 QUALIFY（最简）和 ClickHouse 的 LIMIT BY（每组限行独有语法），StarRocks 的 TopN 在执行层优化但 SQL 语法不够简洁。 |
| [累计求和](../scenarios/running-total/starrocks.md) | **SUM() OVER(ORDER BY ...) 标准窗口累计——Pipeline 引擎加速**。向量化执行使大数据集累计计算高效。对比 BigQuery（Slot 自动扩展）和 ClickHouse（runningAccumulate 状态函数），StarRocks 的 Pipeline 引擎在窗口累计场景中性能优于 ClickHouse。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/starrocks.md) | **Primary Key 模型天然 Upsert 替代 MERGE——INSERT 即按主键覆盖**。SCD Type 1 直接 INSERT 覆盖。SCD Type 2 需应用层逻辑。无标准 MERGE INTO 语句。对比 BigQuery/Snowflake（MERGE INTO 标准 SCD）和 Doris（Unique 模型 Upsert 类似），StarRocks 的 SCD 实现简单但 Type 2 不够优雅。 |
| [字符串拆分](../scenarios/string-split-to-rows/starrocks.md) | **UNNEST+SPLIT(3.1+) 展开字符串为行——语法比 Doris 更简洁**。`SELECT val FROM t, UNNEST(SPLIT(str, ',')) AS val` 标准 UNNEST 语法（无需 LATERAL VIEW）。对比 Snowflake 的 SPLIT_TO_TABLE（最简）和 Doris 的 EXPLODE_SPLIT+LATERAL VIEW，StarRocks 的 UNNEST 方案更接近标准 SQL。 |
| [窗口分析](../scenarios/window-analytics/starrocks.md) | **完整窗口函数+Pipeline 引擎向量化优化**——移动平均、同环比、占比计算均可实现。无 QUALIFY、无 WINDOW 命名子句。对比 BigQuery/Snowflake（QUALIFY+WINDOW 命名最强）和 Doris（同源但 Pipeline 引擎较旧），StarRocks 的窗口分析执行性能在 MPP 引擎中领先。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/starrocks.md) | **ARRAY/MAP/STRUCT(2.5+)+UNNEST+LATERAL JOIN 展开——语法比 Doris 的 LATERAL VIEW EXPLODE 更标准**。UNNEST 是 SQL 标准语法，对比 Hive/Doris 的 LATERAL VIEW EXPLODE（非标准），StarRocks 的复合类型处理更接近标准 SQL。对比 BigQuery 的 CROSS JOIN UNNEST 和 Snowflake 的 VARIANT，StarRocks 的复合类型在 MPP 引擎中最标准。 |
| [日期时间](../types/datetime/starrocks.md) | **DATE/DATETIME(微秒精度)——与 Doris 类型系统几乎相同（同源）**。无 TIME 类型（纯时间无日期）、无 INTERVAL 类型。对比 BigQuery 的四种时间类型和 Snowflake 的三种 TIMESTAMP，StarRocks 的日期类型较为简洁但缺少专用类型。 |
| [JSON](../types/json/starrocks.md) | **JSON 类型(2.2+)+Flat JSON 自动列化加速——4.0+ 性能提升 3-15 倍**。Flat JSON 自动检测高频 JSON 字段并按列式存储（类似 Snowflake VARIANT 自动列化），查询时自动列裁剪。对比 PG 的 JSONB+GIN 索引（索引最强）和 Snowflake 的 VARIANT（查询最优雅），StarRocks 4.0 的 Flat JSON 在 JSON 查询性能上处于领先水平。 |
| [数值类型](../types/numeric/starrocks.md) | **TINYINT-LARGEINT(128位)+FLOAT/DOUBLE+DECIMAL(38)**——LARGEINT 128 位整数与 Doris 相同。DECIMAL 最大精度 38 位（对比 Doris 的 27 位更高，与 BigQuery NUMERIC 38 位持平）。对比 ClickHouse 的 Int8-256/Decimal256（最细粒度）和 BigQuery 的 INT64（极简），StarRocks 的数值类型精度优于 Doris。 |
| [字符串类型](../types/string/starrocks.md) | **VARCHAR(1048576)/CHAR+STRING(3.0+) 无长度限制**——VARCHAR 最大 1MB（对比 Doris 的 65533 字节更大）。STRING 类型(3.0+)取消长度限制。UTF-8 编码。对比 BigQuery 的 STRING（极简无长度）和 Doris（STRING 2.1+ 才引入），StarRocks 的 VARCHAR 上限更高且 STRING 类型引入更早。 |
