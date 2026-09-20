# Hologres

**分类**: 阿里云实时数仓
**文件数**: 51 个 SQL 文件
**总行数**: 4482 行

> **关键人物**：[阿里云实时数仓团队](../docs/people/maxcompute-hologres.md)

## 概述与定位

Hologres 是阿里云自主研发的实时交互式分析引擎，兼容 PostgreSQL 协议和生态。它定位于"实时数仓"——在同一引擎中同时支持实时写入（毫秒级延迟）和复杂分析查询（亚秒级响应），消除传统架构中实时层（如 Flink + HBase/Redis）与离线层（如 MaxCompute/Hive）之间的数据搬运。Hologres 与 MaxCompute 深度集成，可直接加速查询 MaxCompute 离线表。

## 历史与演进

- **2018 年**：阿里巴巴内部启动 Hologres 项目，目标是解决实时分析场景下的高并发低延迟问题。
- **2020 年**：Hologres 作为阿里云公共云服务正式发布（GA），支持 PostgreSQL 11 兼容。
- **2021 年**：引入行列混存引擎、Binlog 变更捕获、与 Flink 的深度集成（实时写入）。
- **2022 年**：增强向量化执行引擎、自动物化视图、分区表增强。
- **2023 年**：引入 Serverless 计算模式、增强 JSON/半结构化数据处理、MaxCompute 外部表加速。
- **2024-2025 年**：增强存算分离架构、向量索引（AI 向量搜索）、增强与 Flink CDC 的集成。

## 核心设计思路

1. **PostgreSQL 兼容**：使用标准 PostgreSQL 客户端（psql、JDBC/ODBC）即可连接，大部分 PostgreSQL 生态工具可直接使用。
2. **行列混存**：通过 `set_table_property` 设置表的存储类型——`column`（列存，适合分析）、`row`（行存，适合点查）、`row,column`（行列混存，兼顾二者）。
3. **实时写入 + 实时查询**：写入通过 Fixed Plan 优化，毫秒级可见；查询通过向量化执行和列存加速实现亚秒级响应。
4. **MaxCompute 加速**：可直接创建 MaxCompute 外部表，通过 Hologres 引擎加速查询 MaxCompute 中的离线数据。

## 独特特色

| 特性 | 说明 |
|---|---|
| **set_table_property** | 通过 `CALL set_table_property('t', 'orientation', 'column')` 设置表的存储格式、分布键、聚簇键等物理属性。 |
| **行列混存** | 同一张表可同时维护行存和列存副本，点查走行存，分析扫描走列存，引擎自动选择。 |
| **Binlog 实时消费** | 表变更自动生成 Binlog，下游 Flink/Spark 可实时消费变更数据，构建实时数据管道。 |
| **MaxCompute 外部表** | 通过外部表映射直接查询 MaxCompute 表数据，利用 Hologres 的向量化引擎加速 MaxCompute 的离线分析。 |
| **Distribution Key** | `CALL set_table_property('t', 'distribution_key', 'col')` 指定数据分布键，等值查询和 JOIN 可利用本地化避免 Shuffle。 |
| **Clustering Key** | 数据在存储中按 Clustering Key 排序存储，范围查询可利用物理排序高效过滤。 |
| **Segment Key** | 文件级分段键，基于时间列实现文件级剪枝，适合时序数据场景。 |
| **JSONB 列存** | V1.3+ 支持 JSONB 数据的列式存储——系统自动将 JSONB 列拆分为多个强 schema 子列存储，查询时直接定位目标子列，分析性能接近原生列存。存储效率与结构化数据相当（列式压缩生效）。仅列存表支持，需 ≥1000 行触发。对比 Snowflake VARIANT 自动列化、ClickHouse JSON 类型(25.3+) 的列式推断。 |

## 已知不足

- **阿里云专有**：Hologres 仅在阿里云上可用，无法在其他云平台或本地部署。
- **PostgreSQL 兼容度不完全**：虽然兼容 PG 协议，但不支持 PG 的部分高级功能（自定义类型、扩展、物化视图的完整语义等）。
- **文档偏少**：相比 PostgreSQL/MySQL 等主流数据库，Hologres 的技术文档和社区讨论资料较少，尤其是英文资料。
- **成本较高**：实时数仓的计算和存储资源费用较高，需仔细规划实例规格和数据生命周期。
- **学习曲线**：set_table_property 的配置项较多（orientation、distribution_key、clustering_key、segment_key、bitmap_columns 等），需要理解存储层设计才能优化性能。

## 对引擎开发者的参考价值

- **行列混存引擎设计**：在同一张表上同时维护行存索引（点查优化）和列存文件（扫描优化），自动路由查询到最优存储路径，对 HTAP 引擎有核心参考。
- **set_table_property 模型**：通过函数调用而非 DDL 语法设置物理属性的设计，比在 CREATE TABLE 中堆砌关键字更灵活，对存储属性管理有借鉴。
- **Fixed Plan 写入优化**：对已知模式的 INSERT 语句跳过优化器直接生成固定执行计划，将写入延迟降到毫秒级，对高频写入引擎有参考。
- **Binlog 集成**：将变更数据捕获作为引擎内置能力而非外部组件，对数据库与流处理集成有参考。
- **外部表加速查询**：通过本地向量化引擎加速查询远端数据源的模式，对联邦查询引擎的性能优化有借鉴。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/hologres.md) | **PG 兼容实时数仓——行存/列存/行列混存通过 set_table_property 灵活选择**。`CALL set_table_property('t','orientation','column')` 设置存储格式。行列混存同时维护两种副本——点查走行存、分析走列存、引擎自动路由。对比 PG（纯行存）和 BigQuery（纯列存）——Hologres 是少有的 HTAP 混合引擎。 |
| [改表](../ddl/alter-table/hologres.md) | **ALTER 在线变更（PG 兼容）**——支持 ADD/DROP COLUMN 等基本操作。物理属性通过 set_table_property 修改而非 ALTER TABLE。对比 PG 的 DDL 事务性可回滚——Hologres 的 ALTER 功能基础但支持在线操作不阻塞查询。 |
| [索引](../ddl/indexes/hologres.md) | **Clustering Key/Segment Key/Bitmap/Dictionary 编码是 Hologres 独有的物理优化体系**——Clustering Key 控制数据物理排序、Segment Key 实现文件级时间剪枝、Bitmap 索引加速等值查询、Dictionary 编码压缩低基数列。对比 PG 的 B-tree/GIN/GiST 和 BigQuery 的分区+聚集——Hologres 的物理优化更精细。 |
| [约束](../ddl/constraints/hologres.md) | **PK 在行存表上实际执行（保证唯一性）**——列存表 PK 仅作优化器提示。其他约束（FK/CHECK/UNIQUE）支持有限。对比 PG 的完整约束强制执行和 BigQuery 的 NOT ENFORCED——Hologres 的约束执行因存储类型而异。 |
| [视图](../ddl/views/hologres.md) | **普通视图（PG 兼容）+ MaxCompute 外部表实现联邦查询**——通过外部表映射直接查询 MaxCompute 离线数据，利用 Hologres 向量化引擎加速。对比 PG 的 FDW（Foreign Data Wrapper）和 Trino 的 Connector——Hologres 的 MaxCompute 加速是阿里云生态内的核心集成点。 |
| [序列与自增](../ddl/sequences/hologres.md) | **SERIAL/BIGSERIAL（PG 兼容）分布式自增**——分布式环境下不保证连续（有间隙）。对比 PG 的 IDENTITY/SERIAL（单机连续）和 BigQuery 的 GENERATE_UUID()——Hologres 继承 PG 语法但受分布式架构限制。 |
| [数据库/Schema/用户](../ddl/users-databases/hologres.md) | **PG 兼容 GRANT/REVOKE 权限 + RAM 云权限集成**——实例级资源隔离。对比 PG 的 RLS 行级安全和 BigQuery 的 GCP IAM——Hologres 结合了 PG 的 SQL 权限模型和阿里云 RAM 的云原生身份管理。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/hologres.md) | **EXECUTE 动态 SQL（PG 兼容但功能有限）**——存储过程支持基础但不及原生 PG 完善。对比 PG 的 EXECUTE format()（防注入更安全）和 Oracle 的 EXECUTE IMMEDIATE——Hologres 的动态 SQL 覆盖基本场景。 |
| [错误处理](../advanced/error-handling/hologres.md) | **PG 兼容异常处理（功能有限）**——支持基本的 EXCEPTION WHEN 块。不支持完整的 GET STACKED DIAGNOSTICS。对比 PG 的完整过程式错误处理——Hologres 的错误处理覆盖常见场景但深度不足。 |
| [执行计划](../advanced/explain/hologres.md) | **EXPLAIN ANALYZE（PG 兼容）+ HQE/SQE 双引擎透视**——HQE（Hologres Query Engine）处理列存分析查询，SQE（Serving Query Engine）处理行存点查。执行计划显示查询路由到哪个引擎。对比 PG 的 EXPLAIN ANALYZE（单引擎）——Hologres 的双引擎选择是 HTAP 架构的核心。 |
| [锁机制](../advanced/locking/hologres.md) | **列存表无行级锁（OLAP 优化），行存表支持行锁（OLTP 场景）**——HTAP 混合架构下锁策略因存储类型而异。对比 PG 的统一行级锁 MVCC 和 BigQuery 的无用户可见锁——Hologres 的锁机制与其混合存储架构紧密耦合。 |
| [分区](../advanced/partitioning/hologres.md) | **分区表（PG 兼容）+ Segment Key 文件级时间剪枝**——分区表适合按日期范围分区，Segment Key 在分区内进一步按时间列实现文件级过滤。对比 PG 的声明式分区和 BigQuery 的 PARTITION BY——Hologres 的 Segment Key 是额外的时序优化维度。 |
| [权限](../advanced/permissions/hologres.md) | **PG 兼容 RBAC + 阿里云 RAM 身份集成**——SQL 级别的 GRANT/REVOKE 权限管理与云原生 RAM 策略结合。对比 PG 的纯 SQL 权限和 BigQuery 的 GCP IAM——Hologres 是 PG 权限+云 IAM 的混合模型。 |
| [存储过程](../advanced/stored-procedures/hologres.md) | **PG 兼容存储过程（有限支持）**——基本的 PL/pgSQL 过程支持。不支持完整的 PG 过程式编程特性（无游标、无 BULK 操作）。对比 PG 的 PL/pgSQL 多语言生态——Hologres 过程化能力满足基本 ETL 需求。 |
| [临时表](../advanced/temp-tables/hologres.md) | **TEMPORARY TABLE（PG 兼容）会话级临时表**——用于 ETL 中间结果暂存。对比 PG 的 ON COMMIT DROP/DELETE ROWS 和 SQL Server 的 #temp——Hologres 临时表继承 PG 语法。 |
| [事务](../advanced/transactions/hologres.md) | **行存表支持 ACID 事务，列存表最终一致性**——HTAP 混合架构下事务语义因存储类型而异。行存表适合 OLTP 级写入（毫秒级可见），列存表适合批量分析（写入后短暂延迟可见）。对比 PG 的统一 ACID——Hologres 在事务一致性上做了性能取舍。 |
| [触发器](../advanced/triggers/hologres.md) | **不支持触发器**——实时数仓定位下触发器需求不强。Binlog 变更捕获是替代方案——表变更自动生成 Binlog 供下游 Flink/Spark 消费。对比 PG 的完整触发器和 BigQuery 的 Pub/Sub——Hologres 的 Binlog CDC 是更现代的事件驱动方案。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/hologres.md) | **DELETE（PG 兼容）——行存表实时删除，列存表批量删除**。行存表支持高频小事务删除，列存表 DELETE 代价较高（标记删除+后台合并）。对比 PG 的统一 DELETE 语义和 BigQuery 的分区级 DELETE——Hologres 的 DELETE 性能因存储类型而异。 |
| [插入](../dml/insert/hologres.md) | **INSERT（PG 兼容）+ Fixed Plan 写入优化**——Fixed Plan 对已知模式的 INSERT 跳过优化器直接生成固定执行计划，写入延迟降到毫秒级。Binlog CDC 自动捕获变更。对比 PG 的 COPY 批量导入和 BigQuery 的 Storage Write API——Fixed Plan 是 Hologres 实时写入的核心优化。 |
| [更新](../dml/update/hologres.md) | **UPDATE（PG 兼容）——行存表支持实时高频更新**。列存表 UPDATE 代价较高（行级更新效率低）。对比 PG 的行级 MVCC 更新和 Redshift 的 DELETE+INSERT——Hologres 行存表的更新性能接近传统 OLTP 数据库。 |
| [Upsert](../dml/upsert/hologres.md) | **INSERT ON CONFLICT（PG 兼容）——行存表支持高频 Upsert**。与 PG 9.5+ 语法完全一致。行存表毫秒级 Upsert 适合实时维表更新。对比 PG 的 ON CONFLICT 和 MySQL 的 ON DUPLICATE KEY UPDATE——Hologres 的 Upsert 在实时场景下性能优异。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/hologres.md) | **PG 兼容聚合函数 + 列存向量化加速**——列存表上 SUM/COUNT/AVG 等聚合利用向量化执行引擎，性能远超行存。对比 PG（行存聚合）和 BigQuery（列存+Slot 并行）——Hologres 列存聚合性能接近专业 OLAP 引擎。 |
| [条件函数](../functions/conditional/hologres.md) | **CASE/COALESCE/NULLIF 标准条件函数（PG 兼容）**。对比 PG 的完整条件函数——Hologres 在条件函数上与 PG 完全兼容。 |
| [日期函数](../functions/date-functions/hologres.md) | **PG 兼容日期函数**——date_trunc/date_part/INTERVAL 运算完整。generate_series 支持生成日期序列。对比 PG 的丰富 INTERVAL 运算——Hologres 日期函数覆盖完整。 |
| [数学函数](../functions/math-functions/hologres.md) | **PG 兼容数学函数**——列存表上数学运算利用向量化加速。对比 PG 的 NUMERIC 任意精度——Hologres 数学函数完整且列存场景下性能优异。 |
| [字符串函数](../functions/string-functions/hologres.md) | **PG 兼容字符串函数**——|| 拼接、SUBSTR/LENGTH/REPLACE 完整。对比 PG 的 regexp_match/replace——Hologres 字符串函数覆盖主流需求。 |
| [类型转换](../functions/type-conversion/hologres.md) | **CAST / :: 类型转换运算符（PG 兼容）**——严格类型系统，不做隐式转换（与 PG 一致）。无 TRY_CAST（与 PG 相同）。对比 SQL Server 的 TRY_CAST 和 BigQuery 的 SAFE_CAST——Hologres 继承了 PG 的类型安全但缺少安全转换。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/hologres.md) | **WITH + 递归 CTE（PG 兼容）**——层级查询和日期序列生成可用递归 CTE 实现。对比 PG 的可写 CTE（Hologres 不支持 DML in WITH）——Hologres CTE 功能基础但够用。 |
| [全文搜索](../query/full-text-search/hologres.md) | **GIN 索引全文检索（PG 兼容但功能有限）**——基本的文本搜索支持。不如 PG 的 tsvector+GIN 完善（无多语言分词、无权重排序）。对比 PG 的完整全文搜索和 BigQuery 的 SEARCH INDEX——Hologres 全文搜索适合简单场景。 |
| [连接查询](../query/joins/hologres.md) | **Hash/Nested Loop JOIN（PG 兼容）+ Shuffle 分布式 JOIN**——Distribution Key 相同的表 JOIN 可避免 Shuffle（本地化执行）。对比 PG 的单机 JOIN 和 Redshift 的 DISTKEY 优化——Hologres 的 Distribution Key 设计类似 Redshift/Greenplum。 |
| [分页](../query/pagination/hologres.md) | **LIMIT/OFFSET（PG 兼容）标准分页**。对比 PG/MySQL 的标准分页——Hologres 分页语法与 PG 完全一致。 |
| [行列转换](../query/pivot-unpivot/hologres.md) | **无原生 PIVOT/UNPIVOT（与 PG 相同）**——需 CASE + GROUP BY 模拟。对比 Oracle/SQL Server/BigQuery/DuckDB 的原生 PIVOT——Hologres 继承了 PG 在行列转换上的短板。 |
| [集合操作](../query/set-operations/hologres.md) | **UNION/INTERSECT/EXCEPT 完整支持（PG 兼容）**。对比 MySQL 直到 8.0.31 才支持 INTERSECT/EXCEPT——Hologres 继承了 PG 完整的集合操作。 |
| [子查询](../query/subquery/hologres.md) | **关联子查询（PG 兼容）**——优化器自动展开关联子查询。对比 PG 的 LATERAL 子查询——Hologres 子查询能力与 PG 基础版本一致。 |
| [窗口函数](../query/window-functions/hologres.md) | **完整窗口函数（PG 兼容）+ 列存向量化加速**——ROW_NUMBER/RANK/LAG/LEAD 完整。列存表上窗口函数利用向量化执行引擎加速。对比 PG（行存窗口函数）和 BigQuery（QUALIFY 无需子查询）——Hologres 窗口函数性能在列存模式下优异。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/hologres.md) | **generate_series（PG 兼容）原生日期序列生成**——与 PG 完全相同的一行方案。对比 MySQL 需递归 CTE 和 BigQuery 的 GENERATE_DATE_ARRAY——Hologres 继承了 PG 的 generate_series 优势。 |
| [去重](../scenarios/deduplication/hologres.md) | **ROW_NUMBER + CTE 去重（PG 兼容）**——无 DISTINCT ON（Hologres 可能不完整支持 PG 的所有语法糖）。对比 PG 的 DISTINCT ON 和 BigQuery 的 QUALIFY——Hologres 去重方案标准。 |
| [区间检测](../scenarios/gap-detection/hologres.md) | **窗口函数 LAG/LEAD 检测间隙（PG 兼容）**——generate_series 生成完整序列后 LEFT JOIN 检测缺失。对比 PG 的完整方案——Hologres 间隙检测与 PG 一致。 |
| [层级查询](../scenarios/hierarchical-query/hologres.md) | **递归 CTE 标准层级查询（PG 兼容）**——无 Oracle 的 CONNECT BY。对比 PG 的递归 CTE+ltree——Hologres 层级查询功能基础。 |
| [JSON 展开](../scenarios/json-flatten/hologres.md) | **json_each/json_array_elements（PG 兼容）展开 JSON**。JSONB 列存(V1.3+) 自动将 JSONB 拆分为子列存储——查询性能接近原生列存。对比 PG 的 JSONB+GIN 索引和 Snowflake 的 VARIANT 自动列化——Hologres 的 JSONB 列存是独特的半结构化优化。 |
| [迁移速查](../scenarios/migration-cheatsheet/hologres.md) | **PG 兼容 + 行列混存 + MaxCompute 联邦是三大核心差异**。set_table_property 配置物理属性（orientation/distribution_key/clustering_key/segment_key）。Fixed Plan 写入优化。Binlog CDC 实时变更捕获。从 PG 迁入需学习 Hologres 的物理优化配置。 |
| [TopN 查询](../scenarios/ranking-top-n/hologres.md) | **ROW_NUMBER + LIMIT 是标准 TopN 方案（PG 兼容）**——无 QUALIFY（对比 BigQuery/DuckDB）。列存向量化加速排序操作。对比 PG 的 DISTINCT ON 和 SQL Server 的 TOP WITH TIES——Hologres TopN 方案中规中矩。 |
| [累计求和](../scenarios/running-total/hologres.md) | **SUM() OVER 标准累计求和（PG 兼容）+ 列存向量化加速**——列存表上窗口聚合性能优异。对比 PG（行存单机）和 BigQuery（Slot 自动扩展）——Hologres 在列存模式下累计求和性能接近专业 OLAP 引擎。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/hologres.md) | **INSERT ON CONFLICT 是 SCD Type 1 的标准方案（PG 兼容）**——行存表高频 Upsert 适合实时维表更新。无 MERGE 语句。对比 PG 15+ 的 MERGE 和 Oracle 的 MERGE 多分支——Hologres 的 Upsert 功能基础但实时性能突出。 |
| [字符串拆分](../scenarios/string-split-to-rows/hologres.md) | **string_to_array + unnest 字符串拆分（PG 兼容）**——与 PG 完全相同的方案。对比 PG 14 的 string_to_table（更简洁）和 MySQL 无原生拆分——Hologres 继承了 PG 的字符串拆分能力。 |
| [窗口分析](../scenarios/window-analytics/hologres.md) | **完整窗口函数（PG 兼容）+ HSAP 混合分析**——行存表上窗口函数适合点查级分析，列存表上利用向量化加速适合大规模分析。对比 PG（单一存储模型）和 BigQuery（QUALIFY 无需子查询）——Hologres 的双引擎窗口函数适配不同负载。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/hologres.md) | **ARRAY 类型（PG 兼容），无 STRUCT/MAP 类型**。对比 PG 的原生 ARRAY+运算符和 BigQuery 的 STRUCT/ARRAY——Hologres 复合类型功能有限，JSONB 是半结构化数据的替代方案。 |
| [日期时间](../types/datetime/hologres.md) | **DATE/TIMESTAMP/TIMESTAMPTZ（PG 兼容）**——完整时间类型。INTERVAL 类型支持。对比 PG 的完整时间类型和 BigQuery 的四种时间类型——Hologres 时间类型与 PG 一致。 |
| [JSON](../types/json/hologres.md) | **JSON/JSONB（PG 兼容）+ GIN 索引 + JSONB 列存(V1.3+)**——JSONB 列存自动将 JSONB 拆分为多个强 schema 子列，查询性能接近原生列存。对比 PG 的 JSONB+GIN（最强查询优化）和 Snowflake 的 VARIANT 自动列化——Hologres 的 JSONB 列存是独特优化。 |
| [数值类型](../types/numeric/hologres.md) | **INT/BIGINT/NUMERIC/FLOAT（PG 兼容）标准数值类型**。列存模式下数值类型自动压缩。对比 PG 的 NUMERIC 任意精度——Hologres 数值类型与 PG 一致。 |
| [字符串类型](../types/string/hologres.md) | **TEXT/VARCHAR（PG 兼容）——TEXT=VARCHAR 无性能差异**（与 PG 相同）。列存模式下字符串自动字典编码压缩。对比 PG 的 TEXT 和 BigQuery 的 STRING——Hologres 字符串类型继承 PG 设计。 |
