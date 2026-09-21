# Azure Synapse

**分类**: Azure 云数仓（基于 T-SQL）
**文件数**: 51 个 SQL 文件
**总行数**: 5000 行

## 概述与定位

Azure Synapse Analytics（前身为 Azure SQL Data Warehouse）是微软推出的云原生分析平台，将大规模数据仓库、数据湖集成、大数据分析和数据集成管道统一在一个服务中。其 SQL 引擎基于 T-SQL 方言，采用 MPP 架构处理 PB 级数据分析。Synapse 的核心优势是与 Azure 生态系统的深度集成——Azure Data Lake、Power BI、Azure ML 等服务可无缝协作。

## 历史与演进

- **2016 年**：Azure SQL Data Warehouse（SQL DW）正式发布，基于 MPP 架构提供 T-SQL 云数仓服务。
- **2018 年**：引入 Gen2 架构，支持无限存储扩展与自适应缓存（Adaptive Caching），计算存储分离。
- **2019 年**：品牌升级为 Azure Synapse Analytics，增加 Spark 池、Pipeline 集成和统一工作区（Synapse Studio）。
- **2020 年**：Synapse Serverless SQL pool 发布，支持按查询付费直接查询 Data Lake 中的文件。
- **2021 年**：引入 Synapse Link，实现从 Cosmos DB/Dataverse/SQL Server 到 Synapse 的近实时数据同步。
- **2023-2025 年**：增强与 Microsoft Fabric 的融合、改进 Lakehouse 格式支持（Delta Lake/Iceberg）、扩展 T-SQL 函数集。

## 核心设计思路

1. **MPP + T-SQL**：采用控制节点（Control Node）+ 计算节点（Compute Node）架构，SQL 查询被优化器拆分为分布式执行计划。
2. **数据分布策略**：建表时通过 `DISTRIBUTION = HASH(col) | ROUND_ROBIN | REPLICATE` 控制数据在计算节点间的分布方式。
3. **计算存储分离**：数据持久化在 Azure Storage 中，计算节点可独立扩缩容，暂停时仅收存储费用。
4. **统一分析平台**：Dedicated SQL pool（数仓）、Serverless SQL pool（数据湖查询）、Spark pool（大数据处理）在同一工作区共存。

## 独特特色

| 特性 | 说明 |
|---|---|
| **DISTRIBUTION** | `DISTRIBUTION = HASH(col)` 按哈希分布、`ROUND_ROBIN` 轮询分布、`REPLICATE` 全节点复制——三种策略直接影响 JOIN 性能。 |
| **CTAS（CREATE TABLE AS SELECT）** | 在 Synapse 中 CTAS 是最重要的数据转换模式，比 INSERT...SELECT 更高效，自动并行化。 |
| **PolyBase** | 通过外部表语法直接查询 Azure Blob Storage/ADLS/S3 中的 Parquet/CSV/ORC 文件，无需加载到数仓。 |
| **Result Set Caching** | 查询结果自动缓存在控制节点，相同查询直接返回缓存结果，无需重新执行分布式计划。 |
| **Workload Management** | 通过 Workload Groups 和 Workload Classifiers 对查询进行分类、资源分配和优先级排序。 |
| **Materialized Views** | 支持分布式物化视图，优化器可自动利用物化视图加速查询，无需手动改写 SQL。 |
| **Serverless SQL Pool** | 按查询扫描数据量付费，直接查询 Data Lake 文件，适合探索性分析和低频查询场景。 |

## 已知不足

- **T-SQL 子集限制**：与 SQL Server 的 T-SQL 并非完全兼容——不支持游标、触发器、跨数据库查询、部分系统函数。
- **索引受限**：不支持 B-tree 索引，仅支持列存储索引（Clustered Columnstore Index），行存索引仅用于 Heap 表。
- **UPDATE/DELETE 限制**：不支持带 FROM 子句的 UPDATE（需使用 CTAS + RENAME 模式替代），DML 操作限制较多。
- **唯一约束不强制**：主键和唯一约束仅为优化器提示，数据完整性需在 ETL 层保证。
- **暂停与恢复延迟**：Dedicated SQL pool 暂停/恢复需要数分钟，不如 Serverless 模式即时。
- **学习曲线**：分布策略选择、CTAS 模式、PolyBase 外部表配置对初学者有一定门槛。

## 对引擎开发者的参考价值

- **三种分布策略设计**：HASH/ROUND_ROBIN/REPLICATE 三种分布模式覆盖了分布式数仓的主要数据放置策略，对 MPP 引擎的数据分区设计有直接参考。
- **CTAS 优先的 ETL 模式**：将"建新表替换旧表"作为首选数据变换模式（而非 UPDATE in-place），对列存引擎的不可变数据设计有启发。
- **PolyBase 联邦查询**：通过统一的 SQL 语法查询异构数据源的外部表抽象，对查询引擎的联邦化改造有参考价值。
- **计算存储分离实践**：数据持久化在对象存储、计算节点无状态可伸缩的架构，是云原生数仓的标准范式。
- **Workload Management**：查询分类与资源隔离的机制设计，对多租户数仓引擎的资源调度有参考意义。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/synapse.md) | **Azure MPP 数仓（T-SQL 方言）——DISTRIBUTION 策略决定数据分布**。HASH/ROUND_ROBIN/REPLICATE 三种策略直接影响 JOIN 性能。CTAS 是首选转换模式。对比 Redshift 的 DISTKEY 和 Greenplum 的 DISTRIBUTED BY——Synapse 三种分布策略覆盖最全。 |
| [改表](../ddl/alter-table/synapse.md) | **ALTER 受限——不支持大部分在线变更**。CTAS+RENAME 是 Schema 变更标准模式。对比 PG DDL 事务性可回滚和 SQL Server ALTER（更全）——Synapse 在 Schema 演进上最保守。 |
| [索引](../ddl/indexes/synapse.md) | **Clustered Columnstore Index 是默认存储**——所有表默认列存。Heap/Rowstore 可选用于小维表。对比 SQL Server 行存默认+可选 Columnstore——Synapse 列存优先适合分析。 |
| [约束](../ddl/constraints/synapse.md) | **PK/FK/UNIQUE 声明但不强制（同 BigQuery/Redshift）**——仅优化器提示。数据完整性需 ETL 层保证。对比 PG/MySQL 强制执行——Synapse 约束不强制是 MPP 数仓普遍选择。 |
| [视图](../ddl/views/synapse.md) | **普通视图+物化视图（自动刷新+查询重写）**——RESULT_SET_CACHING 缓存查询结果。对比 Oracle Fast Refresh+Query Rewrite（最强）和 BigQuery 自动增量刷新——Synapse 物化视图在云数仓中较完善。 |
| [序列与自增](../ddl/sequences/synapse.md) | **IDENTITY 自增列——无 SEQUENCE**（T-SQL 子集）。分布式 IDENTITY 不保证连续。对比 SQL Server IDENTITY+SEQUENCE 和 PG 三种选择——Synapse 自增功能基础。 |
| [数据库/Schema/用户](../ddl/users-databases/synapse.md) | **T-SQL 兼容权限+Azure AD 集成身份验证+RLS 行级安全**。对比 SQL Server DENY 和 BigQuery GCP IAM——Synapse 权限是 T-SQL+Azure 云原生混合。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/synapse.md) | **sp_executesql/EXEC 动态 SQL（T-SQL 兼容）**。对比 SQL Server 完整动态 SQL——Synapse 动态 SQL 是 T-SQL 子集但覆盖常见场景。 |
| [错误处理](../advanced/error-handling/synapse.md) | **TRY...CATCH 错误处理（T-SQL 兼容）**。对比 SQL Server 完整 TRY...CATCH+XACT_ABORT 和 PG EXCEPTION WHEN——Synapse 错误处理继承 T-SQL。 |
| [执行计划](../advanced/explain/synapse.md) | **EXPLAIN 分布式 MPP 计划+DMV 性能视图**——DMV 提供查询历史、等待统计、数据倾斜信息。对比 SQL Server 图形化执行计划——Synapse DMV 是 MPP 调优核心工具。 |
| [锁机制](../advanced/locking/synapse.md) | **无行级锁（MPP 列存）——Workload Groups/Classifiers 控制资源分配**。对比 SQL Server 行级锁和 BigQuery DML 配额——Synapse 并发模型面向分析负载。 |
| [分区](../advanced/partitioning/synapse.md) | **DISTRIBUTION 三种策略是核心物理设计**——HASH 优化 JOIN，REPLICATE 复制小维表，ROUND_ROBIN 均匀分布。对比 Redshift DISTKEY 和 Greenplum DISTRIBUTED BY——Synapse 分布策略最灵活。 |
| [权限](../advanced/permissions/synapse.md) | **T-SQL 兼容权限+Azure AD+RLS 行级安全**。对比 SQL Server DENY 和 PG RLS——Synapse 权限完整。 |
| [存储过程](../advanced/stored-procedures/synapse.md) | **T-SQL 存储过程（功能子集）——不支持嵌套/递归/游标**。对比 SQL Server 完整 T-SQL 和 PG PL/pgSQL——Synapse 过程化受 MPP 限制。 |
| [临时表](../advanced/temp-tables/synapse.md) | **#temp（T-SQL 兼容）+CETAS 导出到外部存储**。对比 SQL Server #temp 和 PG CREATE TEMP TABLE——CETAS 是云原生数据导出方案。 |
| [事务](../advanced/transactions/synapse.md) | **ACID（受限）——不支持嵌套事务，DDL 事务有限**。对比 SQL Server 完整事务和 PG DDL 事务性——Synapse 事务为分析负载优化。 |
| [触发器](../advanced/triggers/synapse.md) | **不支持触发器**——MPP 列存下触发器不适用。对比 SQL Server AFTER/INSTEAD OF 和 PG 完整触发器——Synapse 将事件逻辑推到 Pipeline。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/synapse.md) | **DELETE（T-SQL 兼容）——大批量删除建议 CTAS+RENAME**。列存 DELETE 是标记删除。对比 SQL Server OUTPUT DELETED 和 Redshift VACUUM——CTAS 模式是列存最佳实践。 |
| [插入](../dml/insert/synapse.md) | **INSERT+COPY INTO（推荐批量加载）+PolyBase 外部表查询**——COPY INTO 从 Azure Blob/ADLS 并行加载。对比 Redshift COPY from S3 和 BigQuery LOAD JOB——Synapse COPY INTO+PolyBase 是 Azure 数据管道核心。 |
| [更新](../dml/update/synapse.md) | **UPDATE（T-SQL 兼容）——大表建议 CTAS 重建**。不支持 UPDATE...FROM。对比 SQL Server UPDATE...FROM 和 PG 行级更新——Synapse UPDATE 限制最多。 |
| [Upsert](../dml/upsert/synapse.md) | **MERGE（T-SQL 兼容）适用于维度表更新**——WHEN MATCHED/NOT MATCHED 标准。对比 SQL Server MERGE（有 Bug）和 Oracle MERGE（首创）——Synapse MERGE 功能标准。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/synapse.md) | **STRING_AGG+APPROX_COUNT_DISTINCT（T-SQL 兼容）**。GROUPING SETS/CUBE/ROLLUP 标准。对比 SQL Server STRING_AGG(2017+) 和 PG FILTER 子句——Synapse 聚合与 SQL Server 对齐。 |
| [条件函数](../functions/conditional/synapse.md) | **IIF/CASE/COALESCE（T-SQL 兼容）**。对比 SQL Server IIF/CHOOSE 和 PG 标准 CASE——Synapse 条件函数继承 T-SQL。 |
| [日期函数](../functions/date-functions/synapse.md) | **DATEADD/DATEDIFF/EOMONTH（T-SQL 兼容）**。FORMAT() 不可用。对比 SQL Server FORMAT（CLR 依赖）和 PG INTERVAL——Synapse 日期函数是 T-SQL 子集。 |
| [数学函数](../functions/math-functions/synapse.md) | **T-SQL 兼容数学函数**。GREATEST/LEAST 支持。对比 PG NUMERIC 任意精度——Synapse 数学函数与 SQL Server 对齐。 |
| [字符串函数](../functions/string-functions/synapse.md) | **STRING_SPLIT/CONCAT_WS（T-SQL 兼容）**。+ 拼接。对比 SQL Server 完整字符串函数和 PG || 拼接——Synapse 字符串函数继承 T-SQL。 |
| [类型转换](../functions/type-conversion/synapse.md) | **TRY_CAST/TRY_CONVERT 安全转换（T-SQL 兼容）**——失败返回 NULL。对比 PG 无 TRY_CAST——Synapse 继承 T-SQL 安全转换优势。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/synapse.md) | **WITH+递归 CTE（有限制，T-SQL 兼容）**——递归深度受 MPP 限制。对比 SQL Server MAXRECURSION 和 PG 可写 CTE——Synapse CTE 是 T-SQL 子集。 |
| [全文搜索](../query/full-text-search/synapse.md) | **不支持全文搜索**——需 Azure Cognitive Search。对比 SQL Server CONTAINS/FREETEXT 和 PG tsvector+GIN——Synapse 全文搜索依赖外部服务。 |
| [连接查询](../query/joins/synapse.md) | **Broadcast/Shuffle/Replicated JOIN——分布策略决定性能**。REPLICATE 表 JOIN 无需 Shuffle。对比 Redshift DISTKEY 和 BigQuery 自动选择——Synapse JOIN 性能与 DISTRIBUTION 紧密耦合。 |
| [分页](../query/pagination/synapse.md) | **OFFSET...FETCH（T-SQL 兼容）标准分页**。对比 SQL Server TOP WITH TIES 和 PG LIMIT/OFFSET——Synapse 分页继承 T-SQL。 |
| [行列转换](../query/pivot-unpivot/synapse.md) | **PIVOT/UNPIVOT 原生（T-SQL 兼容）**——列名需静态指定。对比 Oracle 11g（最早）和 DuckDB PIVOT ANY（动态）——Synapse 继承 SQL Server PIVOT。 |
| [集合操作](../query/set-operations/synapse.md) | **UNION/INTERSECT/EXCEPT 完整（T-SQL 兼容）**。对比 MySQL 8.0.31 才支持——Synapse 集合操作完整。 |
| [子查询](../query/subquery/synapse.md) | **关联子查询（T-SQL 兼容）**——MPP 下可能触发 Broadcast。对比 SQL Server Adaptive Join 和 PG LATERAL——Synapse 子查询是 T-SQL 子集。 |
| [窗口函数](../query/window-functions/synapse.md) | **完整窗口函数（T-SQL 兼容）+列存加速**。无 QUALIFY/FILTER/GROUPS。对比 SQL Server Batch Mode 和 PG FILTER+GROUPS——Synapse 利用列存+MPP 并行优势。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/synapse.md) | **递归 CTE 或数字表（T-SQL 兼容）**——无 generate_series。对比 PG generate_series 和 BigQuery GENERATE_DATE_ARRAY——Synapse 日期填充与 SQL Server 一致。 |
| [去重](../scenarios/deduplication/synapse.md) | **ROW_NUMBER+CTE 去重（T-SQL 兼容）**。对比 PG DISTINCT ON 和 BigQuery QUALIFY——Synapse 去重方案标准。 |
| [区间检测](../scenarios/gap-detection/synapse.md) | **窗口函数 LAG/LEAD 检测间隙（T-SQL 兼容）**。对比 PG generate_series+LEFT JOIN——Synapse 间隙检测与 SQL Server 一致。 |
| [层级查询](../scenarios/hierarchical-query/synapse.md) | **递归 CTE（有限制）标准层级查询**——受 MPP 架构限制。对比 SQL Server hierarchyid 和 Oracle CONNECT BY——Synapse 层级查询功能基础。 |
| [JSON 展开](../scenarios/json-flatten/synapse.md) | **OPENJSON（T-SQL 兼容）展开 JSON**——JSON 存为 NVARCHAR 无专用类型。对比 SQL Server OPENJSON+CROSS APPLY 和 PG JSONB+GIN——Synapse JSON 继承 T-SQL 限制。 |
| [迁移速查](../scenarios/migration-cheatsheet/synapse.md) | **T-SQL 子集——DISTRIBUTION 策略+列存是核心差异**。不支持游标/触发器/部分系统函数。CTAS 模式替代 UPDATE/DELETE。从 SQL Server 迁入需适配 DISTRIBUTION。 |
| [TopN 查询](../scenarios/ranking-top-n/synapse.md) | **ROW_NUMBER+TOP TopN（T-SQL 兼容）**。无 QUALIFY。对比 SQL Server TOP WITH TIES——Synapse TopN 继承 T-SQL。 |
| [累计求和](../scenarios/running-total/synapse.md) | **SUM() OVER（T-SQL 兼容）+列存加速 MPP 并行**。对比 SQL Server Batch Mode 和 PG 单机——Synapse 利用列存+MPP 双重优势。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/synapse.md) | **MERGE（T-SQL 兼容）+CTAS 重建替代大规模变更**。对比 SQL Server Temporal Tables 和 Oracle MERGE——CTAS 是列存引擎 SCD 最佳实践。 |
| [字符串拆分](../scenarios/string-split-to-rows/synapse.md) | **STRING_SPLIT（T-SQL 兼容）字符串拆分**。对比 SQL Server STRING_SPLIT 和 PG 14 string_to_table——Synapse 继承 T-SQL 原生拆分。 |
| [窗口分析](../scenarios/window-analytics/synapse.md) | **完整窗口函数（T-SQL 兼容）+MPP 并行**。无 QUALIFY/FILTER/GROUPS。对比 PG FILTER+GROUPS 和 BigQuery QUALIFY——Synapse 利用分布式列存优势。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/synapse.md) | **无原生数组/结构体——JSON 替代（T-SQL 兼容）**。对比 SQL Server 同无原生复合类型和 BigQuery STRUCT/ARRAY——Synapse 继承 T-SQL 复合类型限制。 |
| [日期时间](../types/datetime/synapse.md) | **datetime2/date/time（T-SQL 兼容）**——datetime2 100ns 精度推荐。对比 SQL Server 旧 datetime 3.33ms 精度——Synapse 时间类型与 SQL Server 对齐。 |
| [JSON](../types/json/synapse.md) | **JSON 存为 NVARCHAR 无专用类型（T-SQL 兼容）**——OPENJSON 解析。无 JSON 索引。对比 PG JSONB+GIN 和 MySQL JSON（二进制）——Synapse JSON 继承 SQL Server 文本存储限制。 |
| [数值类型](../types/numeric/synapse.md) | **T-SQL 兼容数值——DECIMAL/FLOAT**。对比 SQL Server 完整数值和 PG NUMERIC 任意精度——Synapse 数值是 T-SQL 子集。 |
| [字符串类型](../types/string/synapse.md) | **VARCHAR/NVARCHAR（T-SQL 兼容）+Collation 排序规则**——Collation 影响比较和排序。对比 SQL Server Collation 体系和 PG UTF-8 默认——Synapse 继承 T-SQL Collation 复杂性。 |
