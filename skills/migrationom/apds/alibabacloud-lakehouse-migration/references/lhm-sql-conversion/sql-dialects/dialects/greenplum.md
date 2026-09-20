# Greenplum

**分类**: MPP 数据库（基于 PostgreSQL）
**文件数**: 51 个 SQL 文件
**总行数**: 4448 行

## 概述与定位

Greenplum 是基于 PostgreSQL 的大规模并行处理（MPP）分析数据库，由 Greenplum Inc. 于 2005 年推出，后被 EMC/Pivotal 收购，现为 VMware Tanzu 产品线的一部分，同时维护开源版本。Greenplum 通过将 PostgreSQL 实例作为 Segment 节点组成分布式集群，在保留完整 PostgreSQL SQL 能力的同时提供 PB 级数据分析能力。它在传统企业数仓、政府、电信等行业有大量部署。

## 历史与演进

- **2005 年**：Greenplum Database 1.0 发布，基于 PostgreSQL 8.2，引入 MPP 分布式执行框架。
- **2010 年**：被 EMC 收购，后整合到 Pivotal 产品线中。
- **2015 年**：Greenplum 开源（Apache 2.0 许可），社区版开始独立发展。
- **2017 年**：Greenplum 5.x 升级底层 PostgreSQL 内核到 8.3+，增强 ORCA 优化器。
- **2019 年**：Greenplum 6.x 基于 PostgreSQL 9.4 内核，引入 JSONB、并行化 VACUUM、Zstandard 压缩。
- **2022 年**：Greenplum 7.x 升级到 PostgreSQL 12 内核，支持 JIT 编译、分区表增强。
- **2024-2025 年**：持续推进云原生部署（Kubernetes）、存算分离架构和 Iceberg 集成。

## 核心设计思路

1. **基于 PostgreSQL 的 MPP**：每个 Segment 是一个完整的 PostgreSQL 实例，Master 节点负责 SQL 解析和计划分发，Segment 节点并行执行。
2. **DISTRIBUTED BY**：建表时必须指定分布键，数据按哈希分布到各 Segment，分布键选择直接影响 JOIN 性能和数据倾斜。
3. **ORCA 优化器**：自主研发的基于成本的查询优化器（Pivotal Query Optimizer），支持动态分区裁剪、子查询去关联等高级优化。
4. **外部表生态**：gpfdist（高速并行数据加载）、PXF（Platform Extension Framework）支持 HDFS、S3、Hive 等外部数据源的联邦查询。

## 独特特色

| 特性 | 说明 |
|---|---|
| **DISTRIBUTED BY** | 建表必须指定 `DISTRIBUTED BY (col)` 或 `DISTRIBUTED RANDOMLY`，控制数据在 Segment 间的分片策略。 |
| **gpfdist** | 高速并行数据加载服务器，将文件切分后从多个 Segment 同时读取，加载速度远超单点 COPY。 |
| **列式存储（AO 表）** | 支持 Append-Optimized 列存表，配合 Zlib/Zstandard/LZ4 压缩，适合大规模分析查询。 |
| **ORCA 优化器** | 独立于 PostgreSQL 原生优化器的高级优化器，对复杂多表 JOIN 和子查询有更好的执行计划选择。 |
| **资源队列/组** | 通过 Resource Queues 或 Resource Groups 实现多租户资源隔离，控制 CPU、内存和并发上限。 |
| **PXF 联邦查询** | 通过 PXF 连接器查询 HDFS/Hive/HBase/S3/JDBC 外部数据源，无需 ETL 导入。 |
| **MADlib 机器学习** | Apache MADlib 在 Greenplum 中提供并行化的机器学习算法（回归、分类、聚类等），在数据库内完成模型训练。 |

## 已知不足

- **PostgreSQL 版本滞后**：底层 PG 内核版本长期落后于社区版 PostgreSQL，新特性（如 MERGE、JSON_TABLE）引入较慢。
- **行级更新开销大**：AO 列存表不支持高效行级 UPDATE/DELETE，需要通过标记删除 + VACUUM 或 Heap 表替代。
- **分布键变更困难**：分布键一旦选定，变更需重建表并重新分布数据，对大表代价极高。
- **单点 Master**：Master 节点是单点，虽可配置 Standby Master，但高可用切换仍需人工干预或脚本。
- **社区活跃度下降**：被 VMware 收购后开源社区活跃度有所下降，与新一代云原生数仓竞品相比创新步伐放慢。

## 对引擎开发者的参考价值

- **PostgreSQL MPP 改造路径**：Greenplum 展示了如何在不大改 PostgreSQL 内核的前提下通过 Motion 节点实现分布式执行，对基于开源 RDBMS 构建 MPP 系统有直接参考。
- **ORCA 优化器架构**：独立进程的基于 Memo 的优化器设计（DXL 中间表示），对自研查询优化器有重要借鉴。
- **gpfdist 并行加载模型**：外部服务进程将文件切分并行推送到多个 Segment 的架构，对分布式批量数据导入有参考价值。
- **资源管理模型**：Resource Groups 基于 Linux cgroups 的 CPU/内存隔离实现，对数据库多租户资源管理有实践参考。
- **列存与行存混合**：在同一数据库中同时支持 Heap 行存表和 AO 列存表的设计，对混合负载引擎的存储层有启发。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/greenplum.md) | **PG 内核 MPP——DISTRIBUTED BY 决定数据分布**。`DISTRIBUTED BY (col)` 哈希分布或 `DISTRIBUTED RANDOMLY` 随机分布。分布键选择直接影响 JOIN 性能和数据倾斜。对比 Redshift 的 DISTKEY 和 Synapse 的 DISTRIBUTION——Greenplum 的 DISTRIBUTED BY 是 PG 系 MPP 的标准模式。 |
| [改表](../ddl/alter-table/greenplum.md) | **ALTER（PG 兼容）——分布键变更需重分布全表数据**（代价极高）。对比 PG DDL 事务性可回滚和 Redshift ALTER 同样受限——Greenplum 分布键选择需在建表时仔细规划。 |
| [索引](../ddl/indexes/greenplum.md) | **B-tree/Bitmap/GIN/GiST（PG 兼容）——Bitmap 索引适合 OLAP 低基数列**。继承 PG 的索引框架。对比 Redshift 无传统索引和 PG 的完整索引体系——Greenplum 保留了 PG 的索引能力。 |
| [约束](../ddl/constraints/greenplum.md) | **PK/FK/CHECK（PG 兼容）——分布式约束有限制**（UNIQUE 约束必须包含分布键）。对比 PG 无此限制和 Redshift 约束不强制——Greenplum 约束在分布式环境下有折中。 |
| [视图](../ddl/views/greenplum.md) | **普通视图（PG 兼容）——无物化视图自动刷新**。对比 PG REFRESH MATERIALIZED VIEW（手动刷新）和 Oracle Fast Refresh——Greenplum 视图功能基础。 |
| [序列与自增](../ddl/sequences/greenplum.md) | **SERIAL/SEQUENCE（PG 兼容）——分布式序列不保证连续**（各 Segment 预分配范围有间隙）。对比 PG 单机 SEQUENCE（连续）——Greenplum 序列受分布式架构限制。 |
| [数据库/Schema/用户](../ddl/users-databases/greenplum.md) | **PG 兼容权限+Resource Queue/Group 多租户资源管理**——基于 Linux cgroups 隔离 CPU/内存。对比 PG 无内置资源管理和 BigQuery Slot 预留——Greenplum 的资源隔离适合多租户企业环境。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/greenplum.md) | **EXECUTE 动态 SQL（PL/pgSQL 兼容）**。对比 PG EXECUTE format()——Greenplum 动态 SQL 继承 PG 能力。 |
| [错误处理](../advanced/error-handling/greenplum.md) | **EXCEPTION WHEN（PL/pgSQL 兼容）**。对比 PG 完整错误处理——Greenplum 错误处理继承 PG。 |
| [执行计划](../advanced/explain/greenplum.md) | **EXPLAIN ANALYZE 带 Slice/Motion 分布式信息**——显示数据在 Segment 间的 Motion（Broadcast/Redistribute）操作。对比 PG 单机 EXPLAIN 和 Redshift SVL 系统视图——Greenplum 的 Motion 信息对 MPP 调优关键。 |
| [锁机制](../advanced/locking/greenplum.md) | **PG 兼容锁+分布式锁管理+MVCC**——两阶段锁协议保证分布式一致性。对比 PG 单机 MVCC 和 Redshift 表级锁——Greenplum 继承 PG 锁机制并扩展到分布式。 |
| [分区](../advanced/partitioning/greenplum.md) | **PARTITION BY（PG 兼容）——大表分区是 OLAP 标准做法**。支持 RANGE/LIST 分区。AO 列存表+分区组合是大表最佳实践。对比 PG 声明式分区和 BigQuery PARTITION BY——Greenplum 分区继承 PG 但版本可能滞后。 |
| [权限](../advanced/permissions/greenplum.md) | **PG 兼容 RBAC+Resource Queue 查询资源控制**——限制并发查询数和内存使用。对比 PG 无资源管理和 Synapse Workload Management——Greenplum 资源管理适合企业多租户。 |
| [存储过程](../advanced/stored-procedures/greenplum.md) | **PL/pgSQL+PL/Python+PL/R（PG 兼容多语言）**——PL/Python 和 PL/R 支持在数据库内运行机器学习（MADlib 库并行化 ML 算法）。对比 PG 的多语言过程和 Oracle PL/SQL——Greenplum 的 PL/R+MADlib 是数据库内 ML 的独特优势。 |
| [临时表](../advanced/temp-tables/greenplum.md) | **CREATE TEMP TABLE（PG 兼容）**。对比 PG ON COMMIT 选项和 SQL Server #temp——Greenplum 临时表继承 PG 语法。 |
| [事务](../advanced/transactions/greenplum.md) | **ACID（PG 兼容）+分布式两阶段提交**——保证跨 Segment 的事务一致性。对比 PG 单机 ACID 和 Redshift 序列化隔离——Greenplum 的分布式事务基于 2PC 协议。 |
| [触发器](../advanced/triggers/greenplum.md) | **PG 兼容触发器（有限制）**——OLAP 场景下触发器少用。AO 列存表不支持触发器。对比 PG 完整触发器和 Redshift 无触发器——Greenplum 触发器仅 Heap 表可用。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/greenplum.md) | **DELETE（PG 兼容）+TRUNCATE 释放空间**。AO 列存表 DELETE 是标记删除需 VACUUM。对比 PG VACUUM 和 Redshift 列存 DELETE——Greenplum 与 PG 的 VACUUM 机制一致。 |
| [插入](../dml/insert/greenplum.md) | **INSERT/COPY（PG 兼容）+gpfdist/gpload 并行加载（独有工具）**——gpfdist 高速并行数据加载服务器，将文件切分后多 Segment 同时读取。对比 PG COPY（单点加载）和 Redshift COPY from S3——gpfdist 的并行加载速度远超 COPY。 |
| [更新](../dml/update/greenplum.md) | **UPDATE（PG 兼容）——分布键列更新需重分布全表数据**（代价极高，应避免）。对比 PG 行级更新和 Redshift DELETE+INSERT——Greenplum 分布键 UPDATE 是特有限制。 |
| [Upsert](../dml/upsert/greenplum.md) | **ON CONFLICT（PG 兼容）——分布式约束有限制**（UNIQUE 必须含分布键）。MERGE 支持取决于底层 PG 内核版本。对比 PG ON CONFLICT 和 Oracle MERGE——Greenplum Upsert 受分布式约束限制。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/greenplum.md) | **PG 兼容聚合+MEDIAN/PERCENTILE_CONT（分析增强）**——MPP 并行聚合性能优异。GROUPING SETS/CUBE/ROLLUP 完整。对比 PG 单机聚合——Greenplum 利用 MPP 并行加速。 |
| [条件函数](../functions/conditional/greenplum.md) | **CASE/COALESCE/NULLIF（PG 兼容）**。对比 PG 完整条件函数——Greenplum 条件函数与 PG 一致。 |
| [日期函数](../functions/date-functions/greenplum.md) | **PG 兼容日期函数+generate_series**。对比 PG 丰富 INTERVAL 运算——Greenplum 日期函数继承 PG。 |
| [数学函数](../functions/math-functions/greenplum.md) | **PG 兼容数学函数**。MPP 并行计算。对比 PG NUMERIC 任意精度——Greenplum 数学函数继承 PG。 |
| [字符串函数](../functions/string-functions/greenplum.md) | **PG 兼容字符串函数+|| 拼接**。对比 PG regexp_match/replace——Greenplum 字符串函数继承 PG。 |
| [类型转换](../functions/type-conversion/greenplum.md) | **CAST/::（PG 兼容）**严格类型。无 TRY_CAST。对比 PG 严格类型和 SQL Server TRY_CAST——Greenplum 类型转换继承 PG。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/greenplum.md) | **WITH+递归 CTE（PG 兼容）**。无可写 CTE。对比 PG 可写 CTE——Greenplum CTE 继承 PG 基础版本。 |
| [全文搜索](../query/full-text-search/greenplum.md) | **tsvector/tsquery（PG 兼容）+GPText 扩展（Solr 集成）**——GPText 基于 Apache Solr 提供企业级全文搜索。对比 PG tsvector+GIN（内置）——Greenplum 的 GPText 扩展提供更强的全文搜索能力。 |
| [连接查询](../query/joins/greenplum.md) | **Broadcast/Redistribute Motion JOIN——MPP 分布式**。相同分布键 JOIN 可避免 Redistribute（本地化执行）。对比 Redshift DISTKEY 优化和 PG 单机 JOIN——Greenplum 的 Motion 类型对 JOIN 性能影响关键。 |
| [分页](../query/pagination/greenplum.md) | **LIMIT/OFFSET（PG 兼容）——大表分页代价高**（MPP 需汇聚到 Master 排序）。对比 PG 标准分页——Greenplum 大表分页需注意性能。 |
| [行列转换](../query/pivot-unpivot/greenplum.md) | **crosstab（PG 兼容 tablefunc 扩展）**——无原生 PIVOT。对比 Oracle/BigQuery/DuckDB 原生 PIVOT 和 PG 相同局限——Greenplum 继承 PG 行列转换短板。 |
| [集合操作](../query/set-operations/greenplum.md) | **UNION/INTERSECT/EXCEPT 完整（PG 兼容）**。对比 MySQL 8.0.31 才支持——Greenplum 继承 PG 完整集合操作。 |
| [子查询](../query/subquery/greenplum.md) | **关联子查询（PG 兼容）+ORCA 优化器 MPP 优化**——ORCA 对复杂子查询的执行计划选择优于 PG 原生优化器。对比 PG 优化器和 Trino 去关联——Greenplum ORCA 是自主研发的高级优化器。 |
| [窗口函数](../query/window-functions/greenplum.md) | **完整窗口函数（PG 兼容）+MPP 并行计算**。无 QUALIFY/FILTER/GROUPS。对比 PG FILTER+GROUPS 和 BigQuery QUALIFY——Greenplum 窗口函数利用 MPP 并行优势。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/greenplum.md) | **generate_series（PG 兼容）原生日期序列**。对比 MySQL 递归 CTE 和 BigQuery GENERATE_DATE_ARRAY——Greenplum 继承 PG generate_series。 |
| [去重](../scenarios/deduplication/greenplum.md) | **ROW_NUMBER/DISTINCT ON（PG 兼容）去重**。对比 PG DISTINCT ON（最简）和 BigQuery QUALIFY——Greenplum 继承 PG 去重方案。 |
| [区间检测](../scenarios/gap-detection/greenplum.md) | **generate_series+窗口函数检测间隙（PG 兼容）**。对比 PG 完整方案——Greenplum 间隙检测与 PG 一致。 |
| [层级查询](../scenarios/hierarchical-query/greenplum.md) | **递归 CTE 标准层级查询（PG 兼容）**。无 CONNECT BY/ltree。对比 PG 递归 CTE+ltree——Greenplum 层级查询继承 PG。 |
| [JSON 展开](../scenarios/json-flatten/greenplum.md) | **json_each/json_array_elements（PG 兼容）**。JSONB+GIN 索引支持取决于 PG 内核版本。对比 PG JSONB+GIN——Greenplum JSON 能力随 PG 内核版本升级。 |
| [迁移速查](../scenarios/migration-cheatsheet/greenplum.md) | **PG 兼容但 DISTRIBUTED BY 和 MPP 特性是核心差异**。分布键选择、AO 列存表、gpfdist 并行加载是迁移核心学习点。从 PG 迁入需适配 DISTRIBUTED BY 和资源管理配置。 |
| [TopN 查询](../scenarios/ranking-top-n/greenplum.md) | **ROW_NUMBER+LIMIT TopN（PG 兼容）**。DISTINCT ON 也可用。对比 BigQuery QUALIFY——Greenplum TopN 继承 PG 方案。 |
| [累计求和](../scenarios/running-total/greenplum.md) | **SUM() OVER（PG 兼容）+MPP 并行计算**。对比 PG 单机和 BigQuery Slot 扩展——Greenplum 利用 MPP 并行加速窗口函数。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/greenplum.md) | **ON CONFLICT/MERGE（PG 兼容，取决于底层 PG 版本）**。GP 7.x 基于 PG 12 支持更多特性。对比 PG 15+ MERGE 和 Oracle MERGE——Greenplum SCD 能力随 PG 内核升级。 |
| [字符串拆分](../scenarios/string-split-to-rows/greenplum.md) | **regexp_split_to_table/string_to_array+unnest（PG 兼容）**。对比 PG 14 string_to_table——Greenplum 字符串拆分继承 PG 方案。 |
| [窗口分析](../scenarios/window-analytics/greenplum.md) | **完整窗口函数（PG 兼容）+MPP 并行计算**。无 QUALIFY/FILTER/GROUPS。对比 PG FILTER+GROUPS 和 BigQuery QUALIFY——Greenplum 窗口函数利用 MPP 并行优势。分析 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/greenplum.md) | **ARRAY/复合类型（PG 兼容）**。对比 PG 原生 ARRAY+运算符——Greenplum 继承 PG 复合类型。 |
| [日期时间](../types/datetime/greenplum.md) | **DATE/TIME/TIMESTAMP/INTERVAL（PG 兼容）完整时间类型**。对比 PG 时间类型——Greenplum 时间类型与 PG 一致。 |
| [JSON](../types/json/greenplum.md) | **JSON/JSONB+GIN 索引（PG 兼容，版本相关）**。GP 6.x 基于 PG 9.4 支持 JSONB。对比 PG JSONB+GIN（最强）——Greenplum JSON 能力随 PG 内核版本。 |
| [数值类型](../types/numeric/greenplum.md) | **INT/FLOAT/NUMERIC（PG 兼容）标准数值**。对比 PG NUMERIC 任意精度——Greenplum 数值类型继承 PG。 |
| [字符串类型](../types/string/greenplum.md) | **TEXT/VARCHAR/CHAR（PG 兼容）+UTF-8**。TEXT=VARCHAR 无性能差异。对比 PG TEXT 设计——Greenplum 字符串类型继承 PG。 |
