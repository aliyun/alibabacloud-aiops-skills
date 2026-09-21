# Vertica

**分类**: 列式分析数据库
**文件数**: 51 个 SQL 文件
**总行数**: 4692 行

## 概述与定位

Vertica 是由数据库领域传奇人物 Michael Stonebraker（图灵奖得主）联合创办的列式分析数据库，最初基于其学术项目 C-Store 的研究成果。Vertica 的核心理念是用 Projections（投影）完全替代传统索引：数据以排序后的列存副本形式存储，查询直接扫描最优的 Projection 而无需维护额外索引。现隶属于 OpenText（原 Micro Focus/HP），在电信、金融、广告技术等分析密集型行业有广泛部署。

## 历史与演进

- **2005 年**：Vertica Systems 成立，基于 C-Store 研究项目开发商用列式数据库。
- **2007 年**：Vertica 1.0 发布，以 Projections 为核心的列式存储 + MPP 架构。
- **2011 年**：被 HP 收购，整合到 HP Vertica Analytics Platform 产品线中。
- **2015 年**：引入 Flex Tables（schema-on-read 半结构化数据）、原生支持 Parquet/ORC 外部表。
- **2017 年**：Vertica 9.x 引入 Eon 模式（计算存储分离架构），数据持久化在 S3/HDFS/GCS。
- **2020 年**：增加机器学习库（ML 函数）、改进 Kafka 集成和流式数据摄取。
- **2023 年**：Vertica 23.x 引入 Vertica Accelerator（云全托管服务）、向量搜索、增强 JSON 处理。
- **2024-2025 年**：被 OpenText 收购后继续推进云原生和 AI/ML 集成。

## 核心设计思路

1. **Projections 替代索引**：数据以多个 Projection（排序+列存副本）形式存储，每个 Projection 可有不同的排序键和列组合，优化器自动选择最佳 Projection 响应查询。
2. **SEGMENTED BY**：数据通过 `SEGMENTED BY HASH(col) ALL NODES` 分布到集群各节点，支持 UNSEGMENTED（全复制）策略。
3. **WOS/ROS 架构**：写入先进入 Write Optimized Store（WOS，内存行存），后台 Moveout 将数据转为 Read Optimized Store（ROS，磁盘列存）。
4. **混合负载支持**：通过资源池（Resource Pools）实现 OLTP 级小查询和 OLAP 级大扫描的并发共存。

## 独特特色

| 特性 | 说明 |
|---|---|
| **Projections** | 替代传统索引的核心概念：每个 Projection 是表的一个排序列存副本，可覆盖不同的查询模式，数据库自动维护一致性。 |
| **SEGMENTED BY** | `SEGMENTED BY HASH(col) ALL NODES` 控制数据分片，`UNSEGMENTED ALL NODES` 实现小维表全复制。 |
| **Flex Tables** | Schema-on-read 的半结构化表，`CREATE FLEX TABLE` 后直接加载 JSON/CSV，通过 `MapKeys()` 等函数动态提取列。 |
| **Eon 模式** | 计算存储分离架构，数据存储在 S3/GCS/HDFS，计算节点无状态可弹性伸缩，支持子集群（Subclusters）隔离。 |
| **Tuple Mover** | 后台自动将 WOS 数据合并到 ROS、合并小 ROS 容器，类似 LSM-Tree 的 Compaction 但针对列存优化。 |
| **Database Designer** | 内置自动设计工具，基于查询负载和数据特征自动推荐最优的 Projection 组合。 |
| **原生分析函数** | 丰富的分析函数集（时间序列插值 `TIMESERIES`、模式匹配 `MATCH`、事件会话 `CONDITIONAL_TRUE_EVENT`）。 |

## 已知不足

- **许可成本高**：企业版按节点/TB 计费，成本较高；社区版有 1TB 和 3 节点限制。
- **Projection 管理复杂**：多个 Projection 的存储开销和维护成本随数据量增长显著增加，需要仔细权衡。
- **写入延迟**：虽有 WOS 缓冲，但列存转换（Moveout）过程会消耗资源，不适合高频小事务写入。
- **生态系统较窄**：与主流 BI 工具的集成良好，但 ORM、应用框架和中文社区支持有限。
- **DELETE 性能**：列存表的 DELETE 是逻辑标记删除，实际空间回收需 Mergeout，大规模删除后查询性能可能下降。

## 对引擎开发者的参考价值

- **Projections 模型**：用数据的物理排序副本替代索引的设计思路，彻底消除了索引维护开销和索引-表双重读取的问题，对列存引擎设计有深远影响。
- **WOS/ROS 写入路径**：先行存缓冲再列存持久化的两阶段写入模式，与 LSM-Tree 有异曲同工之处，对实时列存引擎的写入优化有直接参考。
- **Database Designer**：基于查询负载自动推荐物理设计的工具化思路，对自适应物理设计（Adaptive Physical Design）的研究有参考价值。
- **Eon 模式存算分离**：无状态计算节点 + 共享存储 + 子集群隔离的架构，是云原生列存数据库的参考范式。
- **Flex Tables 实现**：在列存引擎中支持 schema-on-read 的做法——通过 __raw__ 列存储原始数据并动态提取——对半结构化数据处理有启发。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/vertica.md) | **列式存储 MPP——Projection 物理设计完全替代传统索引**。每个 Projection 是表的一个排序列存副本，可有不同排序键。K-Safety 配置容错副本数。对比 PG B-tree 索引和 BigQuery 分区+聚集——Vertica 的 Projection 模型消除了索引维护开销。 |
| [改表](../ddl/alter-table/vertica.md) | **ALTER 在线——但 Projection 需同步刷新**（新增列后需 refresh Projection）。对比 PG DDL 事务性可回滚和 Redshift ALTER 受限——Vertica 的 ALTER 与 Projection 维护绑定。 |
| [索引](../ddl/indexes/vertica.md) | **无传统索引——Projection 排序完全替代 B-tree**。每个 Projection 按不同列排序，优化器自动选择最优 Projection。Flattened Table 优化嵌套查询。对比 PG GiST/GIN/BRIN 和 BigQuery 无索引——Vertica 的 Projection 是独特的"多排序副本"设计。 |
| [约束](../ddl/constraints/vertica.md) | **PK/FK/UNIQUE/CHECK 声明不强制（优化器提示）**——与 BigQuery/Redshift 类似。ENFORCE 选项可启用约束检查但有性能开销。对比 PG 强制执行和 Snowflake NOT ENFORCED——Vertica 默认不强制但可选启用。 |
| [视图](../ddl/views/vertica.md) | **普通视图+LIVE AGGREGATE Projection 替代物化视图**——LIVE AGGREGATE Projection 自动维护聚合结果，查询时透明使用。对比 Oracle Fast Refresh+Query Rewrite 和 PG REFRESH MATERIALIZED VIEW——Vertica 的 LIVE AGGREGATE 是实时物化的优雅实现。 |
| [序列与自增](../ddl/sequences/vertica.md) | **AUTO_INCREMENT+SEQUENCE 标准自增**。对比 PG IDENTITY/SEQUENCE 和 MySQL AUTO_INCREMENT——Vertica 同时支持两种方案。 |
| [数据库/Schema/用户](../ddl/users-databases/vertica.md) | **Schema 命名空间+RBAC 权限管理**。对比 PG Database.Schema 和 Oracle VPD——Vertica 权限模型标准。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/vertica.md) | **存储过程内 EXECUTE+PL/vSQL 过程语言**——PL/vSQL 类似 PG 的 PL/pgSQL。对比 PG PL/pgSQL 和 Oracle PL/SQL——Vertica 的 PL/vSQL 是 PG 风格的过程语言。 |
| [错误处理](../advanced/error-handling/vertica.md) | **EXCEPTION WHEN（PL/vSQL）+RAISE EXCEPTION**。对比 PG EXCEPTION WHEN——Vertica 错误处理与 PG 风格一致。 |
| [执行计划](../advanced/explain/vertica.md) | **EXPLAIN ANALYZE 带 Projection 选择和分布信息**——显示查询使用了哪个 Projection、数据在节点间的分布情况。对比 PG EXPLAIN ANALYZE 和 Greenplum Slice/Motion——Vertica 的 Projection 信息对查询优化关键。 |
| [锁机制](../advanced/locking/vertica.md) | **MVCC Snapshot Isolation——无行级锁（OLAP 优化）**。WOS/ROS 架构下写入先进 WOS（内存行存）再转为 ROS（磁盘列存）。对比 PG 行级锁 MVCC 和 BigQuery 无用户可见锁——Vertica 的 WOS/ROS 架构是列存写入的独特方案。 |
| [分区](../advanced/partitioning/vertica.md) | **PARTITION BY 表级分区+Projection 排序分区组合**——分区裁剪+Projection 排序双重优化。对比 PG 声明式分区和 BigQuery PARTITION BY——Vertica 的分区与 Projection 组合提供更灵活的物理设计。 |
| [权限](../advanced/permissions/vertica.md) | **RBAC+Schema 级权限+数据收集审计**。对比 PG RBAC+RLS 和 Oracle VPD——Vertica 权限管理标准完整。 |
| [存储过程](../advanced/stored-procedures/vertica.md) | **PL/vSQL（PG 风格）+EXTERNAL 多语言过程**——EXTERNAL 函数支持 C++/Java/Python/R 等语言。对比 PG PL/Python 和 Oracle PL/SQL——Vertica 的 EXTERNAL 函数扩展能力强。 |
| [临时表](../advanced/temp-tables/vertica.md) | **LOCAL/GLOBAL TEMPORARY TABLE+ON COMMIT PRESERVE/DELETE**——功能与 PG/Oracle 临时表类似。对比 PG ON COMMIT 选项和 SQL Server #temp——Vertica 临时表功能完整。 |
| [事务](../advanced/transactions/vertica.md) | **ACID+Snapshot Isolation+自动提交默认开启**。对比 PG 的 MVCC 和 Redshift 序列化隔离——Vertica 事务模型适合分析负载。 |
| [触发器](../advanced/triggers/vertica.md) | **不支持触发器**——列存 OLAP 引擎下触发器不适用。对比 PG 完整触发器和 Oracle COMPOUND 触发器——Vertica 将事件逻辑推到应用层。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/vertica.md) | **DELETE 标记删除（列式）+PURGE 真正回收空间**——Tuple Mover 后台合并标记删除的数据。对比 PG VACUUM 和 Redshift VACUUM DELETE——Vertica 的 Tuple Mover 类似 LSM-Tree Compaction。 |
| [插入](../dml/insert/vertica.md) | **COPY 批量加载（推荐方式）+INSERT 逐行较慢**——列式引擎下 COPY 批量写入效率远超逐行 INSERT。对比 PG COPY 和 Redshift COPY from S3——Vertica COPY 支持多种格式和并行加载。 |
| [更新](../dml/update/vertica.md) | **UPDATE 在列式存储下实际是 DELETE+INSERT**——旧行标记删除、新行追加。频繁 UPDATE 需定期 Mergeout。对比 PG 行级原地更新和 Redshift 相同机制——列存 UPDATE 代价高是普遍特征。 |
| [Upsert](../dml/upsert/vertica.md) | ****MERGE 标准实现 SCD**。对比 Oracle MERGE 多分支和 SQL Server Temporal Tables——Vertica MERGE 功能标准。**——WHEN MATCHED/NOT MATCHED 完整。对比 PG 15+ MERGE（较晚引入）和 Oracle MERGE（首创）——Vertica MERGE 功能标准。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/vertica.md) | **GROUPING SETS/CUBE/ROLLUP 完整+APPROXIMATE COUNT HyperLogLog**——列存下聚合性能极优。对比 PG FILTER 子句和 BigQuery APPROX_COUNT_DISTINCT——Vertica 聚合利用列存优势。 |
| [条件函数](../functions/conditional/vertica.md) | **CASE/COALESCE/NULLIF/NVL/DECODE（PG+Oracle 混合风格）**。DECODE 兼容 Oracle。对比 PG 标准 COALESCE 和 Redshift 同样的混合风格——Vertica 条件函数覆盖广。 |
| [日期函数](../functions/date-functions/vertica.md) | **DATE_TRUNC/TIMESTAMPADD/TIMESTAMPDIFF+INTERVAL 类型**——TIMESERIES 子句（独有）可原生填充时间序列。对比 PG generate_series 和 BigQuery GENERATE_DATE_ARRAY——Vertica TIMESERIES 是时序数据的独特语法。 |
| [数学函数](../functions/math-functions/vertica.md) | **完整数学函数+APPROXIMATE MEDIAN/PERCENTILE 近似计算**。列存下数学运算利用向量化。对比 PG NUMERIC 任意精度和 BigQuery SAFE_DIVIDE——Vertica 数学函数完整。 |
| [字符串函数](../functions/string-functions/vertica.md) | **|| 拼接+REGEXP_REPLACE/SUBSTR 标准**。对比 PG regexp_match 和 MySQL CONCAT()——Vertica 字符串函数标准完整。 |
| [类型转换](../functions/type-conversion/vertica.md) | **CAST/:: 运算符（PG 风格）+TRY_CAST 安全转换**——失败返回 NULL。对比 PG 无 TRY_CAST 和 SQL Server TRY_CAST——Vertica 兼具 PG 语法和安全转换能力。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/vertica.md) | **WITH+**递归 CTE 标准层级查询**。对比 PG 递归 CTE+ltree 和 Oracle CONNECT BY——Vertica 层级查询标准。支持**。对比 PG 可写 CTE 和 MySQL 8.0 CTE——Vertica CTE 功能标准。 |
| [全文搜索](../query/full-text-search/vertica.md) | **Text Search 内置+STEM/TOKENIZE 函数**——支持词干提取和分词。对比 PG tsvector+GIN（更完善）和 BigQuery SEARCH INDEX——Vertica 内置基本文本搜索。 |
| [连接查询](../query/joins/vertica.md) | **Hash/Merge JOIN+Projection 排序优化 co-located JOIN**——Projection 排序与 SEGMENTED BY 配合可实现本地化 JOIN（无需 Shuffle）。对比 Redshift DISTKEY 优化和 Greenplum DISTRIBUTED BY——Vertica 的 Projection 排序是 JOIN 优化的独特手段。 |
| [分页](../query/pagination/vertica.md) | **LIMIT/OFFSET 标准分页**。对比 PG 标准分页和 BigQuery 按扫描量计费——Vertica 分页标准。 |
| [行列转换](../query/pivot-unpivot/vertica.md) | **无原生 PIVOT**——CASE+GROUP BY 模拟。对比 Oracle/BigQuery/DuckDB 原生 PIVOT——Vertica 缺乏原生行列转换。 |
| [集合操作](../query/set-operations/vertica.md) | **UNION/INTERSECT/EXCEPT 完整支持**。对比 MySQL 8.0.31 才支持——Vertica 集合操作完整。 |
| [子查询](../query/subquery/vertica.md) | **关联子查询+标量子查询优化**。Vertica 优化器自动展开。对比 PG 优化器和 Oracle 标量子查询缓存——Vertica 子查询优化标准。 |
| [窗口函数](../query/window-functions/vertica.md) | **完整窗口函数+ROWS/RANGE 帧——分析查询是核心场景**。列存下窗口函数聚合性能极优。无 QUALIFY/FILTER/GROUPS。对比 PG FILTER+GROUPS 和 BigQuery QUALIFY——Vertica 窗口函数利用列存优势但缺少语法扩展。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/vertica.md) | **TIMESERIES 子句是 Vertica 独有的时序数据填充语法**——`SELECT * FROM t TIMESERIES ts AS '1 day' OVER(PARTITION BY id ORDER BY time)` 原生填充缺失时间点。对比 PG generate_series 和 BigQuery GENERATE_DATE_ARRAY——TIMESERIES 是最优雅的时序填充方案。 |
| [去重](../scenarios/deduplication/vertica.md) | **ROW_NUMBER+CTE 去重（OLAP 标准方式）**。对比 PG DISTINCT ON 和 BigQuery QUALIFY——Vertica 去重方案标准。 |
| [区间检测](../scenarios/gap-detection/vertica.md) | **TIMESERIES+窗口函数检测间隙**——TIMESERIES 原生填充完整时序后检测缺失。对比 PG generate_series 和 Teradata sys_calendar——Vertica TIMESERIES 是间隙检测的独特优势。 |
| [层级查询](../scenarios/hierarchical-query/vertica.md) | **递归 CTE 标准层级查询**。对比 PG 递归 CTE+ltree 和 Oracle CONNECT BY——Vertica 层级查询标准。 |
| [JSON 展开](../scenarios/json-flatten/vertica.md) | **MAPJSONEXTRACTOR/FJSONPARSER+Flex Table 无 Schema 导入**——Flex Table 先导入原始 JSON 到 __raw__ 列，再动态提取结构化列。对比 PG JSONB+GIN 和 Snowflake VARIANT——Vertica 的 Flex Table 是 schema-on-read 的独特实现。 |
| [迁移速查](../scenarios/migration-cheatsheet/vertica.md) | **Projection 物理设计+列式存储+无触发器是迁移核心差异**。Projection 替代索引的概念需重新理解。WOS/ROS 写入路径。Database Designer 可自动推荐 Projection 设计。从行存数据库迁入需适配列存特性。 |
| [TopN 查询](../scenarios/ranking-top-n/vertica.md) | **ROW_NUMBER+LIMIT 标准 TopN**。对比 BigQuery QUALIFY 和 PG DISTINCT ON——Vertica TopN 方案标准。 |
| [累计求和](../scenarios/running-total/vertica.md) | **SUM() OVER 标准+列式存储聚合极高效**——列存下数据连续存储，CPU Cache 命中率高。对比 PG 行存和 BigQuery Slot 扩展——Vertica 列式聚合性能优异。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/vertica.md) | ****MERGE 标准实现 SCD**。对比 Oracle MERGE 多分支和 SQL Server Temporal Tables——Vertica MERGE 功能标准。**——WHEN MATCHED/NOT MATCHED 完整。对比 PG 15+ MERGE（较晚引入）和 Oracle MERGE（首创）——Vertica MERGE 功能标准。 |
| [字符串拆分](../scenarios/string-split-to-rows/vertica.md) | **MAPDELIMITEDEXTRACTOR+Flex Table 或 REGEXP 字符串拆分**——Flex Table 可直接解析分隔文本。对比 PG 14 string_to_table 和 SQL Server STRING_SPLIT——Vertica 的 Flex Table 提供独特的半结构化处理方案。 |
| [窗口分析](../scenarios/window-analytics/vertica.md) | **完整窗口函数——分析查询是 Vertica 的核心场景**。TIMESERIES 子句（独有时序填充）。MATCH/EVENT_NAME 模式匹配（独有分析函数）。CONDITIONAL_TRUE_EVENT 事件会话分析。对比 PG FILTER+GROUPS 和 BigQuery QUALIFY——Vertica 在分析函数上有独特扩展。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/vertica.md) | **ROW 复合类型+ARRAY(10.0+)+Flex Table 半结构化**——ROW 类似 PG 复合类型。Flex Table 的 __raw__ 列存储任意格式原始数据。对比 PG 原生 ARRAY 和 BigQuery STRUCT/ARRAY——Vertica 的 Flex Table 是独特的半结构化方案。 |
| [日期时间](../types/datetime/vertica.md) | **DATE/TIME/TIMESTAMP/TIMESTAMPTZ/INTERVAL 完整时间类型**。TIMESERIES 子句利用时间类型做时序分析。对比 PG 完整时间类型和 Teradata DATE 整数存储——Vertica 时间类型标准完整。 |
| [JSON](../types/json/vertica.md) | **Flex Table 无 Schema JSON 导入+JSON 函数解析**——先导入再查询的 schema-on-read 模式。对比 PG JSONB+GIN（schema-on-write 但索引最强）和 Snowflake VARIANT（灵活度更高）——Vertica 的 Flex Table 适合探索性分析。 |
| [数值类型](../types/numeric/vertica.md) | **INT/FLOAT/NUMERIC(最高 1024 位精度)+APPROXIMATE 近似函数**——NUMERIC 精度可达 1024 位（远超 PG 和 Oracle）。APPROXIMATE 函数提供近似计算。对比 PG NUMERIC 任意精度和 BigQuery BIGNUMERIC 76 位——Vertica 数值精度业界最高。 |
| [字符串类型](../types/string/vertica.md) | **VARCHAR(65000)/CHAR/LONG VARCHAR+UTF-8 默认**。VARCHAR 最大 65000 字节。对比 PG TEXT（无长度限制）和 BigQuery STRING——Vertica 字符串有长度上限但对分析场景足够。 |
