# Amazon Redshift

**分类**: AWS 云数仓（基于 PostgreSQL）
**文件数**: 51 个 SQL 文件
**总行数**: 4862 行

## 概述与定位

Amazon Redshift 是 AWS 推出的全托管云数据仓库服务，基于 ParAccel（PostgreSQL 8.0.2 分叉）演化而来。它将 MPP（大规模并行处理）架构与列式存储相结合，面向 PB 级数据的交互式分析查询。Redshift 是云数仓赛道的先行者（2012 年发布），凭借"按需付费 + 与 AWS 生态深度集成"的模式迅速成为最广泛使用的云数仓之一。

## 历史与演进

- **2012 年**：Redshift 正式发布（GA），基于 ParAccel 的列式 MPP 引擎，提供 PostgreSQL 8.x 兼容的 SQL 接口。
- **2015 年**：引入 Redshift Spectrum，支持直接查询 S3 上的数据而无需加载到集群本地。
- **2018 年**：引入弹性调整（Elastic Resize）、并发扩展（Concurrency Scaling）、结果集缓存。
- **2019 年**：发布 AQUA（Advanced Query Accelerator），在存储层嵌入硬件加速查询处理。
- **2020 年**：引入 RA3 节点类型，实现计算与存储分离（托管存储基于 S3）。
- **2021 年**：Redshift Serverless 发布，用户无需管理集群即可按查询量付费。
- **2022 年**：引入 SUPER 半结构化数据类型、多数仓数据共享（Data Sharing）。
- **2023-2025 年**：增强 MERGE 支持、增量物化视图刷新、零 ETL 集成（Aurora/DynamoDB 到 Redshift 自动复制）。

## 核心设计思路

1. **列式存储 + MPP**：数据按列存储并自动压缩，查询被分发到多个计算节点并行执行。
2. **分布键与排序键**：DISTKEY 控制数据在节点间的分布策略（减少数据倾斜和网络传输），SORTKEY 控制磁盘上的物理排序（加速范围扫描和 Zone Map 裁剪）。
3. **深度 AWS 集成**：COPY 命令从 S3/DynamoDB/EMR 批量加载数据，UNLOAD 导出到 S3，Spectrum 联邦查询 S3 数据湖。
4. **计算存储分离**：RA3 节点类型使用托管存储（Redshift Managed Storage），热数据缓存在本地 SSD，冷数据自动落到 S3。

## 独特特色

| 特性 | 说明 |
|---|---|
| **DISTKEY / SORTKEY** | 建表时指定 `DISTKEY(col)` 和 `SORTKEY(col1, col2)`，直接控制数据的物理分布和排序，是查询调优的核心手段。 |
| **COPY from S3** | 高吞吐批量加载命令，支持 CSV/JSON/Parquet/ORC 格式，自动并行从 S3 多个文件加载到多个切片。 |
| **SUPER 类型** | 半结构化数据类型，存储 JSON/数组/对象，支持 PartiQL 语法查询（如 `s.address.city`），无需预定义 schema。 |
| **Redshift Spectrum** | 在 SQL 中直接查询 S3 上的外部表（Parquet/ORC/CSV），与本地表 JOIN，实现数据湖与数仓的联邦查询。 |
| **Concurrency Scaling** | 查询并发超过集群能力时自动弹出临时集群处理溢出查询，用户无感知。 |
| **Zone Map** | 自动维护每个 1MB 磁盘块的 min/max 元数据，配合 SORTKEY 实现高效的块级过滤。 |
| **Data Sharing** | 多个 Redshift 集群/Serverless 实例之间实时共享数据，无需复制或 ETL。 |

## 已知不足

- **PostgreSQL 兼容性有限**：基于 PG 8.x 分叉，不支持 PG 的许多现代特性——无存储过程（仅 UDF）、无触发器、无 GIN/GiST 索引、无数组类型。
- **UPDATE/DELETE 开销大**：列式存储下行级更新代价高，频繁小批量写入性能差，需定期 VACUUM 回收空间。
- **主键/外键不强制**：约束仅作为优化器提示，不实际校验数据完整性，可能导致数据质量问题。
- **存储过程支持较晚**：2018 年才引入 PL/pgSQL 存储过程，功能仍不如原生 PostgreSQL 完备。
- **SORTKEY 选择困难**：Compound SORTKEY 只对前缀列有效，Interleaved SORTKEY 的 VACUUM 开销大，调优需仔细权衡。

## 对引擎开发者的参考价值

- **DISTKEY/SORTKEY 模型**：将数据分布和物理排序决策暴露为 DDL 语法，是分布式查询引擎设计中数据布局策略的经典实现。
- **Zone Map 过滤**：每个存储块自动维护列的 min/max，在查询时进行块级剪枝——实现简单但效果显著，值得任何列存引擎借鉴。
- **COPY 的并行加载架构**：将外部文件切分后并行加载到多个计算切片的 pipeline 设计，对批量导入优化有重要参考。
- **SUPER 类型与 PartiQL**：在列存引擎中支持半结构化数据的存储与查询，展示了严格 schema 与灵活 schema 的折中方案。
- **Concurrency Scaling 弹性模型**：查询溢出时自动启动临时计算资源的架构，对云原生数仓的弹性设计有参考价值。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/redshift.md) | **基于 PG 8.x 分叉的列式存储 MPP 引擎**——DISTKEY 控制数据在计算节点间的分布（减少 Shuffle），SORTKEY 控制磁盘上的物理排序（加速 Zone Map 裁剪）。DISTKEY/SORTKEY 选择是 Redshift 调优的第一步（对比 BigQuery 的分区+聚集和 Greenplum 的 DISTRIBUTED BY）。约束声明但不强制执行。 |
| [改表](../ddl/alter-table/redshift.md) | **ALTER 能力受限**——ADD COLUMN 可以但不支持 ADD COLUMN WITH DEFAULT（需重建表），MODIFY TYPE 限制多（列式存储下类型变更代价高）。对比 PG 的 DDL 事务性可回滚和 BigQuery 同样不支持 MODIFY COLUMN TYPE（需 CTAS 重建）——Redshift 在 Schema 演进上较保守。 |
| [索引](../ddl/indexes/redshift.md) | **无传统 B-tree 索引——SORTKEY 是唯一的查询加速手段**。Compound SORTKEY 只对前缀列有效（类似复合索引最左前缀原则），Interleaved SORTKEY 对所有列均有效但 VACUUM 开销大。Zone Map 自动维护每个 1MB 块的 min/max 元数据。对比 BigQuery 的分区+聚集和 ClickHouse 的稀疏索引。 |
| [约束](../ddl/constraints/redshift.md) | **PK/FK/UNIQUE 声明但不强制校验数据完整性**——仅作为优化器提示（优化器利用 PK 信息消除冗余 JOIN）。这是 Serverless/MPP 数仓的普遍选择（BigQuery/Snowflake 同理）。NOT NULL 约束是唯一强制执行的约束。对比 PG/MySQL 的约束强制执行和 Oracle 的 ENABLE/DISABLE 灵活管理。 |
| [视图](../ddl/views/redshift.md) | **LATE BINDING VIEW 允许底层表结构变更而不失效**——普通视图在底层表 ALTER 后可能报错，LATE BINDING VIEW 延迟绑定 Schema 提升灵活性。物化视图(2019+) 支持增量自动刷新。对比 Oracle 的 Fast Refresh+Query Rewrite（最强实现）和 BigQuery 的自动增量刷新+智能查询重写。 |
| [序列与自增](../ddl/sequences/redshift.md) | **IDENTITY 自增列是唯一的自增方案**——无独立 SEQUENCE 对象（PG 8.x 分叉的限制）。分布式环境下 IDENTITY 不保证连续（有间隙）。对比 PG 的 IDENTITY/SERIAL/SEQUENCE 三种选择（功能更丰富）和 BigQuery 的 GENERATE_UUID()（无自增列）。 |
| [数据库/Schema/用户](../ddl/users-databases/redshift.md) | **PG 兼容权限模型 + Datashare 跨集群数据共享**——Datashare 允许多个 Redshift 集群/Serverless 实例之间实时共享数据（无需复制或 ETL），是 Redshift 的差异化优势。对比 BigQuery 的 Authorized View 和 Snowflake 的 Data Sharing——Redshift 的 Datashare 延迟最低。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/redshift.md) | **存储过程内 EXECUTE 执行动态 SQL（PL/pgSQL 子集）**——2018 年才引入存储过程，动态 SQL 功能不如原生 PG 完善。无 format() 安全引用工具。对比 PG 的 EXECUTE format()（防注入更安全）和 Oracle 的 EXECUTE IMMEDIATE——Redshift 的动态 SQL 是最基础的。 |
| [错误处理](../advanced/error-handling/redshift.md) | **EXCEPTION WHEN 块是 PL/pgSQL 子集**——支持基本异常捕获和 RAISE EXCEPTION 抛出错误。功能弱于原生 PG（无 GET STACKED DIAGNOSTICS）。对比 Oracle 的命名异常+RAISE_APPLICATION_ERROR（最成熟）和 SQL Server 的 TRY...CATCH——Redshift 的错误处理够用但不丰富。 |
| [执行计划](../advanced/explain/redshift.md) | **EXPLAIN 文本输出 + SVL/STL 系统视图分析**——SVL_QUERY_REPORT 和 STL_EXPLAIN 提供分布式执行的 Slice 级详情（每个计算切片的行数、耗时）。对比 PG 的 EXPLAIN ANALYZE（更直观）和 BigQuery 的 Console Execution Details——Redshift 的系统视图是调优核心工具。 |
| [锁机制](../advanced/locking/redshift.md) | **表级锁为主，默认序列化隔离级别**——MVCC 快照隔离保证读不阻塞写。序列化隔离是默认（对比 PG 默认 READ COMMITTED）。列式存储下行级锁意义不大——DML 操作粒度为文件块。对比 PG 的行级锁高并发和 BigQuery 的 DML 配额限制。 |
| [分区](../advanced/partitioning/redshift.md) | **无原生分区表语法——SORTKEY + DISTKEY 是物理优化的替代方案**。Spectrum 外部表支持 Hive 分区（S3 路径按分区键组织），实现数据湖上的分区裁剪。对比 PG 的声明式分区（RANGE/LIST/HASH）和 BigQuery 的 PARTITION BY——Redshift 的分区概念与传统不同。 |
| [权限](../advanced/permissions/redshift.md) | **PG 兼容 GRANT/REVOKE 权限模型**——支持 Schema 级、表级、列级权限。Datashare 跨集群安全共享——消费者集群只能读取共享数据不能修改。对比 PG 的 RLS 行级安全（Redshift 不支持 RLS）和 BigQuery 的 Row/Column Access Policy——Redshift 缺少行级安全策略。 |
| [存储过程](../advanced/stored-procedures/redshift.md) | **PL/pgSQL 子集(2018+ 才引入)——功能弱于原生 PostgreSQL**。不支持游标、不支持 RETURN TABLE、异常处理受限。2018 前完全无存储过程。对比 PG 的 PL/pgSQL 多语言生态和 Oracle 的 PL/SQL Package（最强过程语言）——Redshift 过程化能力在数仓中偏弱。 |
| [临时表](../advanced/temp-tables/redshift.md) | **CREATE TEMP TABLE（PG 兼容）会话级可见**——临时表也遵循 DISTKEY/SORTKEY 语法（可优化临时表查询性能）。ETL 常用模式：创建临时表暂存中间结果再合并到目标表。对比 SQL Server 的 #temp 和 BigQuery 的 _SESSION.table_name——Redshift 临时表使用习惯与 PG 一致。 |
| [事务](../advanced/transactions/redshift.md) | **默认序列化隔离级别——比大多数数据库默认级别更高**（对比 PG/MySQL 默认 READ COMMITTED/REPEATABLE READ）。ACID 事务支持。自动提交模式默认开启。对比 BigQuery 的多语句事务(2020+) 和 Snowflake 的自动提交——Redshift 事务模型最接近 PG。 |
| [触发器](../advanced/triggers/redshift.md) | **不支持触发器**——PG 8.x 分叉时就移除了触发器支持（MPP 环境下触发器的分布式语义复杂）。ETL 逻辑通过存储过程或外部调度工具实现。对比 PG 的完整触发器支持和 BigQuery 的 Pub/Sub + Cloud Functions 替代方案。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/redshift.md) | **DELETE 在列式存储下是标记删除（延迟回收）**——已删除行在磁盘上标记为不可见，需 VACUUM DELETE ONLY 回收空间。TRUNCATE 立即释放存储且性能极快。对比 PG 的 VACUUM 回收死元组和 BigQuery 的分区级 DELETE——Redshift 需定期 VACUUM 维护性能。 |
| [插入](../dml/insert/redshift.md) | **COPY 命令从 S3 批量加载是推荐的数据导入方式**——自动并行从 S3 多个文件加载到多个 Slice，吞吐量比 INSERT 高 10 倍以上。支持 CSV/JSON/Parquet/ORC 格式。对比 BigQuery 的 LOAD JOB（免费）和 Databricks 的 COPY INTO（幂等性优势）——COPY 是 AWS 数据管道核心。 |
| [更新](../dml/update/redshift.md) | **UPDATE 在列式存储下实际是 DELETE + INSERT**——旧行标记删除、新行追加写入。频繁小批量更新性能差（需定期 VACUUM 回收）。对比 PG 的行级原地更新和 BigQuery 的分区级重写——Redshift 的 UPDATE 代价最高，适合批量更新而非高频小事务。 |
| [Upsert](../dml/upsert/redshift.md) | **MERGE(2023+ 才引入)——之前需 staging 表 + DELETE + INSERT 模拟**。经典 Redshift Upsert：`DELETE FROM target USING staging; INSERT INTO target SELECT * FROM staging`。对比 PG 9.5+ 的 ON CONFLICT（更早更简洁）和 Oracle 9i 的 MERGE（首创）——Redshift 的 MERGE 到来最晚。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/redshift.md) | **LISTAGG 字符串聚合（Oracle 风格而非 PG 的 string_agg）**——APPROXIMATE COUNT(DISTINCT) 基于 HyperLogLog 近似去重。MEDIAN 内置函数（对比 PG 需 PERCENTILE_CONT 模拟）。无 FILTER 子句（对比 PG 的条件聚合）。GROUPING SETS/CUBE/ROLLUP 标准支持。 |
| [条件函数](../functions/conditional/redshift.md) | **PG + Oracle 混合函数风格**——同时支持 PG 的 COALESCE/NULLIF 和 Oracle 的 NVL/NVL2/DECODE。DECODE 与 Oracle 兼容。这种混合风格源于 ParAccel 时代——降低 Oracle 迁移成本。对比 PG 坚持标准（无 DECODE）和 SQL Server 的 IIF。 |
| [日期函数](../functions/date-functions/redshift.md) | **DATEADD/DATEDIFF/DATE_TRUNC 混合了 SQL Server 和 PG 风格**——DATEADD(month, 3, date) 类似 SQL Server，DATE_TRUNC 类似 PG。GETDATE() 返回当前时间（SQL Server 风格，对比 PG 的 NOW()）。INTERVAL 类型支持有限（对比 PG 的丰富 INTERVAL 运算）。 |
| [数学函数](../functions/math-functions/redshift.md) | **完整数学函数 + APPROXIMATE PERCENTILE 近似计算**——基于 T-Digest 算法，大数据量下性能优于精确计算。GREATEST/LEAST 内置。对比 PG 的 NUMERIC 任意精度（Redshift 限制 38 位）和 BigQuery 的 SAFE_DIVIDE（独有安全语法）。 |
| [字符串函数](../functions/string-functions/redshift.md) | **|| 拼接运算符（PG 兼容）**——REGEXP_REPLACE/REGEXP_SUBSTR 正则函数。SPLIT_PART 按分隔符提取第 N 段。LISTAGG 替代 PG 的 string_agg。对比 MySQL 中 || 是逻辑 OR（最大方言陷阱）和 SQL Server 用 + 拼接——Redshift 保持 PG 风格。 |
| [类型转换](../functions/type-conversion/redshift.md) | **CAST / :: 运算符（PG 风格）**——但隐式转换比原生 PG 更宽松（VARCHAR 自动转数字等），降低迁移门槛但可能隐藏类型问题。无 TRY_CAST 安全转换（对比 SQL Server/BigQuery 的安全转换）。对比 PG 的严格类型——Redshift 在类型安全上做了妥协。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/redshift.md) | **WITH 标准 CTE + 递归 CTE（PG 兼容）**——优化器自动决定 CTE 物化/内联。无 PG 的可写 CTE（DML in WITH）。无 MATERIALIZED/NOT MATERIALIZED 提示。对比 PG 12+ 的物化控制和 BigQuery 的优化器自动决定——Redshift CTE 功能基础但够用。 |
| [全文搜索](../query/full-text-search/redshift.md) | **无内置全文搜索**——需依赖 Amazon OpenSearch 等外部服务。LIKE/ILIKE 可做基础模式匹配但无索引加速。对比 PG 的 tsvector+GIN（最强内置实现）和 BigQuery 的 SEARCH INDEX(2023+)——Redshift 在全文搜索上完全依赖外部生态。 |
| [连接查询](../query/joins/redshift.md) | **DISTKEY 优化 co-located JOIN 是 Redshift 调优的核心**——两表 DISTKEY 相同时 JOIN 无需 Shuffle（本地化执行），性能提升数倍。Hash/Merge/Nested Loop 三种算法由优化器选择。对比 BigQuery 的自动选择和 Greenplum 的 DISTRIBUTED BY——DISTKEY 设计直接决定 JOIN 性能。 |
| [分页](../query/pagination/redshift.md) | **LIMIT/OFFSET（PG 兼容）标准分页**——列式存储下深分页问题较轻（分析场景少有深分页需求）。对比 PG/MySQL 的深分页性能问题和 BigQuery 按扫描量计费下 OFFSET 无意义——Redshift 分页使用场景主要在 BI 工具连接中。 |
| [行列转换](../query/pivot-unpivot/redshift.md) | **无原生 PIVOT/UNPIVOT 语法**——需手写 CASE + GROUP BY 模拟。对比 Oracle 11g/SQL Server/BigQuery/DuckDB 均有原生 PIVOT 和 PG 需 crosstab 扩展——Redshift 在行列转换上缺乏原生支持，是分析查询的短板。 |
| [集合操作](../query/set-operations/redshift.md) | **UNION/INTERSECT/EXCEPT 完整支持（PG 兼容）**——ALL 变体均可用。对比 MySQL 直到 8.0.31 才支持 INTERSECT/EXCEPT 和 Oracle 使用 MINUS 而非 EXCEPT——Redshift 继承了 PG 完整的集合操作。 |
| [子查询](../query/subquery/redshift.md) | **关联子查询和标量子查询支持**——优化器尝试将子查询转为 JOIN。MPP 环境下关联子查询可能触发 Broadcast（性能敏感）。对比 PG 的 LATERAL 子查询（Redshift 不支持 LATERAL）和 Oracle 的标量子查询缓存——Redshift 子查询优化依赖 PG 8.x 基线。 |
| [窗口函数](../query/window-functions/redshift.md) | **完整窗口函数（PG 兼容）+ WLM 查询队列管理**——列式存储下窗口函数聚合性能优异。WLM 控制查询优先级和资源分配。无 QUALIFY（对比 BigQuery/DuckDB）。无 GROUPS 帧类型（PG 11+ 独有）。对比 SQL Server 的 Batch Mode 窗口加速——Redshift 依靠列存的聚合优势。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/redshift.md) | **递归 CTE 或预建数字表生成日期序列**——无 PG 的 generate_series（PG 8.x 分叉限制）。数字表方案性能更优但需预先维护。对比 PG 的 generate_series（原生最简洁）和 BigQuery 的 GENERATE_DATE_ARRAY——Redshift 日期填充方案较冗长。 |
| [去重](../scenarios/deduplication/redshift.md) | **ROW_NUMBER + CTE 是标准去重方案**——列式存储下全表扫描+窗口函数去重性能可接受。无 PG 的 DISTINCT ON。对比 BigQuery/DuckDB 的 QUALIFY ROW_NUMBER()（无需子查询包装）——Redshift 去重方案中规中矩。 |
| [区间检测](../scenarios/gap-detection/redshift.md) | **窗口函数 LAG/LEAD 检测相邻行间隙**——无 generate_series 需用递归 CTE 或数字表生成完整序列后 EXCEPT 检测缺失。对比 PG 的 generate_series+LEFT JOIN（最直观）和 Teradata 的 sys_calendar 系统日历表。 |
| [层级查询](../scenarios/hierarchical-query/redshift.md) | **递归 CTE 是唯一的层级查询方案（PG 兼容）**——无 Oracle 的 CONNECT BY、无 PG 的 ltree 扩展、无 SQL Server 的 hierarchyid 类型。对比 PG 的递归 CTE+ltree 组合和 Oracle 的 CONNECT BY+SYS_CONNECT_BY_PATH——Redshift 层级查询功能最基础。 |
| [JSON 展开](../scenarios/json-flatten/redshift.md) | **SUPER 类型 + PartiQL 语法是 Redshift 的半结构化方案**——`SELECT s.address.city FROM t` 点号路径访问无需解析函数。JSON_EXTRACT_PATH_TEXT 传统 JSON 函数仍可用。对比 PG 的 JSONB+GIN 索引（最强实现）和 Snowflake 的 VARIANT+FLATTEN——SUPER 类型的 PartiQL 是 AWS 生态统一语言。 |
| [迁移速查](../scenarios/migration-cheatsheet/redshift.md) | **PG 8.x 子集——许多 PG 现代特性不可用**。DISTKEY/SORTKEY 物理设计是迁移核心学习点。无索引、无触发器、无 generate_series、约束不强制——迁移时需处理这些差异。从 PG 迁入需移除不支持的语法，从 Oracle 迁入可利用 NVL/DECODE 兼容。 |
| [TopN 查询](../scenarios/ranking-top-n/redshift.md) | **ROW_NUMBER + 窗口函数是分组 TopN 标准方案**——全局 TopN 直接 ORDER BY + LIMIT。无 QUALIFY（对比 BigQuery/DuckDB）。无 FETCH FIRST WITH TIES（对比 PG 13+）。列式存储下排序性能优异（SORTKEY 加速）。 |
| [累计求和](../scenarios/running-total/redshift.md) | **SUM() OVER(ORDER BY ...) 标准累计求和**——列式存储下聚合运算天然高效（数据连续存储，Cache 友好）。MPP 架构下窗口函数在各节点并行计算。对比 PG（单机高效但无分布式并行）和 BigQuery（Slot 自动扩展）。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/redshift.md) | **MERGE(2023+ 才引入)——之前用经典 staging 表模式**：创建临时 staging 表、COPY 数据、DELETE+INSERT 同步。这是 Redshift 十年来的标准 SCD 模式。对比 Oracle 的 MERGE（9i 首创）和 SQL Server 的 Temporal Tables（自动历史版本）。 |
| [字符串拆分](../scenarios/string-split-to-rows/redshift.md) | **SPLIT_PART + 递归 CTE 或数字表展开**——SPLIT_PART(str, delim, N) 提取第 N 段，结合数字表逐段提取展开。方案较繁琐。对比 PG 14 的 string_to_table（一行搞定）和 SQL Server 的 STRING_SPLIT——无原生字符串拆分为行的函数。 |
| [窗口分析](../scenarios/window-analytics/redshift.md) | **完整窗口函数（PG 兼容）+ 列式存储天然加速**——ROWS/RANGE 帧支持。无 GROUPS 帧（PG 11+ 独有）、无 QUALIFY（BigQuery/DuckDB 独有）、无 FILTER（PG 独有）。列式存储使聚合窗口函数性能优于行存引擎。WLM 可为分析查询分配专用资源。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/redshift.md) | **SUPER 类型是 Redshift 的半结构化数据方案**——存储 JSON/数组/对象，PartiQL 语法查询。无原生 ARRAY/STRUCT 列类型（对比 PG 原生 ARRAY、BigQuery 的 STRUCT/ARRAY、DuckDB 的 LIST/STRUCT/MAP）——SUPER 类型是对半结构化数据的折中方案。 |
| [日期时间](../types/datetime/redshift.md) | **DATE/TIMESTAMP/TIMESTAMPTZ 三种时间类型——无 TIME 纯时间类型**（PG 8.x 分叉限制）。TIMESTAMPTZ 存储 UTC 自动转换。微秒精度。对比 PG 的完整时间类型（含 TIME/INTERVAL）和 BigQuery 四种时间类型——Redshift 时间类型基本够用但缺 TIME 和 INTERVAL。 |
| [JSON](../types/json/redshift.md) | **SUPER 类型 + PartiQL 查询是 Redshift 的 JSON 方案**——SUPER 内部以优化的二进制格式存储（非文本），PartiQL 语法 `s.array[0].key` 自然导航嵌套结构。对比 PG 的 JSONB+GIN 索引（最强实现）和 Snowflake 的 VARIANT——SUPER 与 AWS PartiQL 生态绑定。 |
| [数值类型](../types/numeric/redshift.md) | **SMALLINT/INT/BIGINT/REAL/DOUBLE/DECIMAL(38) PG 兼容**——DECIMAL 精度最高 38 位（对比 PG 的 NUMERIC 无上限和 BigQuery 的 BIGNUMERIC 76 位）。列式存储下数值类型自动压缩（Run-Length、Delta 编码），存储效率高。 |
| [字符串类型](../types/string/redshift.md) | **VARCHAR(65535) 默认最大长度**——远大于传统 VARCHAR 但有上限（对比 PG 的 TEXT 无限制）。CHAR 定长类型（填充空格）。列式存储下字符串自动压缩（LZO/ZSTD）。对比 BigQuery 的 STRING（无长度限制极简设计）——Redshift 保留 PG 传统但有上限约束。 |
