# Apache Impala

**分类**: Hadoop SQL 引擎（Cloudera）
**文件数**: 51 个 SQL 文件
**总行数**: 4626 行

## 概述与定位

Apache Impala 是 Cloudera 开发的 Hadoop 生态实时 SQL 查询引擎，旨在为 HDFS 和 HBase 上的数据提供低延迟的交互式分析能力。与 Hive 的 MapReduce/Tez 批处理模式不同，Impala 使用常驻守护进程（impalad）和 MPP 架构直接在数据节点上执行查询，跳过了 MapReduce 的调度开销，将查询延迟从分钟级降低到秒级。Impala 共享 Hive Metastore，使得同一份数据可被 Hive、Spark 和 Impala 共同访问。

## 历史与演进

- **2012 年**：Cloudera 发布 Impala 1.0 Beta，定位为 Hadoop 上的"实时 SQL"引擎。
- **2013 年**：Impala 1.0 GA，支持 HDFS/HBase 查询、UDF、Parquet 格式原生支持。
- **2015 年**：Impala 2.x 引入多租户资源管理（Admission Control）、COMPUTE STATS 优化器增强。
- **2017 年**：Impala 成为 Apache 顶级项目，增加 Kudu 表支持（可变数据存储）。
- **2019 年**：Impala 3.x 增强 ACID 支持（通过 Hive ACID 表）、改进窗口函数和分析功能。
- **2022 年**：Impala 4.x 引入 Iceberg 表支持、虚拟仓库部署（Impala on K8s）、存算分离。
- **2024-2025 年**：持续推进云原生部署、增强对 Iceberg V2 的支持、改进并发查询性能。

## 核心设计思路

1. **常驻进程 MPP**：每个数据节点运行 impalad 守护进程，查询到达后直接并行执行，无需启动 MapReduce 作业。
2. **共享 Hive Metastore**：与 Hive 共享表元数据，`INVALIDATE METADATA` / `REFRESH` 命令同步元数据变更。
3. **代码生成**：使用 LLVM 进行运行时代码生成（Codegen），为每个查询生成针对具体 schema 的优化机器码。
4. **多存储后端**：支持 HDFS（Parquet/ORC/Text）、Kudu（可变列存）、HBase（KV 存储）和 S3/ADLS 等多种存储。

## 独特特色

| 特性 | 说明 |
|---|---|
| **Kudu 表** | 原生集成 Apache Kudu，在 Hadoop 生态中提供可变列式存储，支持实时 INSERT/UPDATE/DELETE，弥补 HDFS 不可变的不足。 |
| **COMPUTE STATS** | `COMPUTE STATS table_name` 收集表和列的统计信息（行数、NDV、NULL 比例等），是优化器生成高效计划的关键。 |
| **INVALIDATE METADATA** | 当外部工具（Hive/Spark）修改了表结构或数据后，通过此命令强制 Impala 重新加载元数据缓存。 |
| **LLVM 代码生成** | 运行时为每个查询生成特化的 C++ 代码，消除解释执行的开销，对扫描密集型查询性能提升显著。 |
| **Admission Control** | 内置的资源准入控制，基于队列限制并发查询数和内存使用，避免集群过载。 |
| **分区裁剪** | 深度优化的分区裁剪逻辑，配合 Parquet 的行组统计信息实现多层过滤（分区级 + 文件级 + 行组级）。 |
| **Parquet 原生支持** | Impala 是 Parquet 格式的最早采用者之一，在读取和写入 Parquet 文件方面有深度优化。 |

## 已知不足

- **不支持 UPDATE/DELETE（HDFS 表）**：对 HDFS 上的 Parquet/ORC 表不支持行级更新和删除，仅 Kudu 表支持。
- **SQL 功能受限**：不支持存储过程、触发器、游标；CTE 支持较晚；JSON 处理能力有限。
- **元数据同步开销**：频繁 INVALIDATE METADATA 在大规模集群（数万表）上可能导致 Catalogd 压力过大。
- **容错能力弱**：查询执行期间如有节点故障，整个查询失败（无重试机制），不适合超长运行的批处理查询。
- **生态萎缩**：随着 Spark SQL、Trino/Presto 和云数仓的崛起，Impala 的独立部署用户逐渐减少。
- **资源争用**：与 HDFS DataNode 共享节点资源，高并发查询时可能与 HDFS I/O 和 YARN 作业产生资源冲突。

## 对引擎开发者的参考价值

- **LLVM 运行时代码生成**：Impala 是 OLAP 引擎中最早大规模使用 LLVM Codegen 的项目之一，其 Expr Codegen 和 Scan Codegen 的实现对查询引擎加速有核心参考。
- **常驻进程 vs 作业调度**：与 Hive 的按需启动模式对比，Impala 的常驻进程模式展示了延迟与资源利用率的权衡。
- **Metastore 缓存一致性**：INVALIDATE / REFRESH 的两级缓存失效策略，对分布式 Catalog 的一致性设计有实践参考。
- **多存储后端抽象**：通过统一的 ScanNode 抽象层对接 HDFS/Kudu/HBase/S3 等不同存储，对插件化存储后端的设计有借鉴。
- **Admission Control 模型**：基于队列的资源准入控制（而非严格的资源隔离），是轻量级多租户管理的实用方案。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/impala.md) | **多存储后端建表——STORED AS 指定格式**（Parquet/ORC/Text/Avro），`CREATE TABLE ... STORED AS PARQUET` 是最佳实践。**Kudu 表**通过专用语法创建，支持主键排序和可变数据。EXTERNAL TABLE 引用已有 HDFS 数据。对比 Hive（相同 STORED AS 语法但延迟更高）和 BigQuery（无存储格式选择），Impala 在 Hadoop 生态中提供最灵活的存储格式控制。 |
| [改表](../ddl/alter-table/impala.md) | **ADD/DROP/CHANGE COLUMN——Kudu 表支持更多 ALTER**。HDFS 表的 ALTER 主要修改元数据（如添加分区、修改表属性），不触碰数据文件。Kudu 表支持 ALTER COLUMN 类型变更。对比 Hive（类似元数据 ALTER）和传统 RDBMS（ALTER 实际修改数据），Impala 的 ALTER 反映了"元数据与数据分离"的 Hadoop 架构特征。 |
| [索引](../ddl/indexes/impala.md) | **无传统索引**——HDFS 查询引擎依赖 Parquet 行组统计信息（min/max/bloom filter）和分区裁剪替代索引。**Kudu 表主键排序**提供有序扫描能力。对比 BigQuery（同样无传统索引，用分区+聚集替代）和 ClickHouse（稀疏索引），Impala 的"无索引"设计源于 HDFS 不可变文件的特性。 |
| [约束](../ddl/constraints/impala.md) | **Kudu 表 PK/NOT NULL，HDFS 表无约束**——Kudu 表主键强制唯一且非空，是 Kudu 存储引擎的底层保证。HDFS 表无任何约束（文件级存储无法校验）。对比 BigQuery（NOT ENFORCED 约束）和 PostgreSQL（完整约束执行），Impala 的约束能力完全取决于底层存储后端。 |
| [视图](../ddl/views/impala.md) | **普通视图（元数据级），无物化视图**。视图定义存储在 Hive Metastore 中，Hive 和 Impala 可共享。对比 BigQuery（物化视图自动增量刷新）和 PostgreSQL（REFRESH MATERIALIZED VIEW），Impala 缺少预计算视图能力，需依赖 ETL 预处理。 |
| [序列与自增](../ddl/sequences/impala.md) | **无 SEQUENCE/自增**——Hadoop 生态中无全局递增序列概念。替代方案：`UUID()` 生成唯一标识符，或 ROW_NUMBER() 在查询时生成序号。对比 BigQuery（GENERATE_UUID()）和 PostgreSQL（SERIAL/IDENTITY），Impala 在 ID 生成上完全依赖函数或外部工具。 |
| [数据库/Schema/用户](../ddl/users-databases/impala.md) | **共享 Hive Metastore 元数据 + Ranger/Sentry 权限**——Database = Hive 中的 Database，元数据对 Hive/Spark/Impala 共享。权限通过 Apache Ranger（或已弃用的 Sentry）统一管理。对比 PostgreSQL（独立权限体系）和 BigQuery（GCP IAM），Impala 的权限融入 Hadoop 生态的统一安全框架。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/impala.md) | **无动态 SQL**——Impala 定位为查询引擎而非过程化编程平台，不提供存储过程或动态 SQL 能力。对比 PostgreSQL（EXECUTE 动态 SQL）和 BigQuery（EXECUTE IMMEDIATE），Impala 的查询-only 设计简化了引擎但限制了灵活性。 |
| [错误处理](../advanced/error-handling/impala.md) | **无过程式错误处理**——查询失败时整个查询中止并返回错误信息，无 TRY/CATCH 机制。对比 PostgreSQL 的 EXCEPTION WHEN 和 BigQuery 的 SAFE_ 前缀函数，Impala 的错误处理完全由客户端应用层负责。 |
| [执行计划](../advanced/explain/impala.md) | **EXPLAIN + PROFILE 双工具**——EXPLAIN 显示 MPP 执行计划（扫描节点、JOIN 策略、Exchange 操作），PROFILE 显示查询完成后的实际资源消耗（CPU 时间、IO 字节、内存峰值、各节点耗时）。对比 PostgreSQL 的 EXPLAIN ANALYZE（合一工具）和 BigQuery（Console 面板），Impala 的 PROFILE 粒度是 MPP 引擎中最细的之一。 |
| [锁机制](../advanced/locking/impala.md) | **无行级锁**——HDFS 表是不可变文件（追加写入），无锁需求。**Kudu 表有 MVCC**，支持并发读写的快照隔离。对比 PostgreSQL（行级 MVCC 锁）和 BigQuery（无用户可见锁），Impala 的锁模型完全取决于底层存储：HDFS 无锁，Kudu 有 MVCC。 |
| [分区](../advanced/partitioning/impala.md) | **PARTITIONED BY（同 Hive）+ COMPUTE STATS 统计信息收集**——`COMPUTE STATS table_name` 收集行数、NDV、NULL 比例等统计信息，是优化器生成高效计划的**关键步骤**。`INVALIDATE METADATA` / `REFRESH` 同步外部修改的元数据。对比 PostgreSQL（自动 ANALYZE 收集统计）和 BigQuery（自动管理），Impala 需要手动 COMPUTE STATS 是运维中常见遗漏。 |
| [权限](../advanced/permissions/impala.md) | **Ranger/Sentry 集成，与 Hive 共享权限策略**——在 Ranger 中配置的 HDFS/Hive 权限对 Impala 自动生效。支持列级和行级过滤策略。对比 PostgreSQL 的 GRANT/REVOKE（数据库内权限）和 BigQuery 的 GCP IAM，Impala 的权限管理完全外部化到 Hadoop 安全框架。 |
| [存储过程](../advanced/stored-procedures/impala.md) | **无存储过程——UDF（C++/Java）替代**。用户可编写 C++ UDF 获得原生性能，或 Java UDF 利用 JVM 生态。UDA（User-Defined Aggregate）支持自定义聚合。对比 PostgreSQL 的 PL/pgSQL（完整过程语言）和 BigQuery（SQL + JS 存储过程），Impala 的 UDF 方案更偏向编译型扩展。 |
| [临时表](../advanced/temp-tables/impala.md) | **无传统临时表**——Hive Metastore 共享架构下无会话级临时表概念。替代方案：创建普通表后手动删除，或使用 HDFS 临时目录。对比 PostgreSQL 的 CREATE TEMP TABLE 和 BigQuery 的 _SESSION.table，Impala 缺乏临时表是查询引擎定位的局限。 |
| [事务](../advanced/transactions/impala.md) | **Kudu 表支持 INSERT/UPDATE/DELETE（行级可变）；HDFS 表仅追加写入（INSERT INTO/OVERWRITE）**。HDFS 表的 INSERT OVERWRITE 是原子操作（替换整个分区）。Hive ACID 表在较新版本中也可查询。对比 BigQuery（按扫描量计费的 DML）和 PostgreSQL（完整 ACID），Impala 的事务能力取决于存储后端选择。 |
| [触发器](../advanced/triggers/impala.md) | **无触发器**——查询引擎定位不提供事件驱动能力。替代方案：Kafka + 流处理框架实现数据变更事件处理。对比 PostgreSQL（完整触发器）和 BigQuery（无触发器，用 Cloud Functions 替代），Impala 的事件处理完全由外部系统负责。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/impala.md) | **DELETE 仅 Kudu 表支持**——HDFS 上的 Parquet/ORC 文件不可变，无法行级删除。Kudu 表通过 MVCC 实现行级 DELETE。对比 BigQuery（DELETE 重写分区）和 ClickHouse（异步 Mutation DELETE），Impala 的 DELETE 能力完全取决于 Kudu 存储后端。 |
| [插入](../dml/insert/impala.md) | **INSERT INTO / INSERT OVERWRITE（同 Hive）+ Kudu INSERT**——INSERT OVERWRITE 替换整个表或分区（原子操作）。Kudu 表支持标准 INSERT 行级写入。对比 Hive（INSERT OVERWRITE 通过 MapReduce 执行，慢）和 BigQuery（流式/批量 INSERT），Impala 的 INSERT 在 HDFS 上是文件追加操作，速度远快于 Hive。 |
| [更新](../dml/update/impala.md) | **UPDATE 仅 Kudu 表支持 + UPSERT 原生**——HDFS 表无法 UPDATE（不可变文件）。Kudu 表的 UPSERT 语句在 Hadoop 生态中是**独有特性**——根据主键自动判断 INSERT 或 UPDATE。对比 PostgreSQL 的 ON CONFLICT（功能类似但语法不同）和 BigQuery（必须用 MERGE），Impala 的 UPSERT 语法是 Kudu 场景下最简洁的。 |
| [Upsert](../dml/upsert/impala.md) | **UPSERT（仅 Kudu 表，原生语法）**——`UPSERT INTO kudu_table VALUES (...)` 直接使用，无需 MERGE 或 ON CONFLICT 包装。对比 PostgreSQL 的 ON CONFLICT（需指定冲突列）和 MySQL 的 ON DUPLICATE KEY UPDATE（需唯一键），Impala 的 UPSERT 是最简洁的原生 Upsert 实现之一。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/impala.md) | **GROUPING SETS/ROLLUP/CUBE（3.x+）+ NDV 近似计数**——NDV() 使用 HyperLogLog 算法估算不同值数量，比 COUNT(DISTINCT) 快得多但有误差。APPX_MEDIAN 近似中位数。对比 BigQuery 的 APPROX_COUNT_DISTINCT（类似 HLL）和 PostgreSQL（无内置近似计数），Impala 的 NDV 是大数据分析场景的重要优化。 |
| [条件函数](../functions/conditional/impala.md) | **IF/CASE/COALESCE/NVL/IFNULL**——IF 和 NVL 都可用（兼容 Hive 和 Oracle 风格）。对比 MySQL 的 IF（相同语法）和 PostgreSQL（无 IF 函数），Impala 在条件函数上兼顾了多种方言习惯。 |
| [日期函数](../functions/date-functions/impala.md) | **FROM_UNIXTIME/UNIX_TIMESTAMP/DATE_ADD（Hive 兼容）**——FROM_UNIXTIME 将 Unix 时间戳转为字符串，DATE_ADD 加减天数。格式化字符串遵循 Java SimpleDateFormat 规范。对比 PostgreSQL 的 to_char/date_trunc（更灵活）和 MySQL 的 DATE_FORMAT，Impala 的日期函数与 Hive 生态一致。 |
| [数学函数](../functions/math-functions/impala.md) | **完整数学函数**——MOD/CEIL/FLOOR/ROUND/POWER/SQRT/LOG/LN 等标准集合。对比各主流引擎数学函数基本一致，Impala 在数学函数上无特殊差异。 |
| [字符串函数](../functions/string-functions/impala.md) | **CONCAT/SUBSTR/REGEXP_REPLACE（Hive 兼容）**——使用 CONCAT 函数拼接（非 \|\| 运算符）。REGEXP_REPLACE/REGEXP_EXTRACT 基于 Java 正则引擎。对比 PostgreSQL 的 \|\| 拼接和 BigQuery 的 re2 正则引擎（线性时间），Impala 的字符串函数与 Hive 生态对齐。 |
| [类型转换](../functions/type-conversion/impala.md) | **CAST 标准，隐式转换较宽松**——字符串到数值的隐式转换在 WHERE 条件中自动执行。失败时返回 NULL（而非报错）。对比 PostgreSQL（严格类型检查）和 MySQL（宽松隐式转换），Impala 的隐式转换宽松度介于两者之间。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/impala.md) | **WITH 标准 + 递归 CTE（4.x+）**——递归 CTE 引入较晚，早期版本需用自连接或应用层替代。对比 PostgreSQL（WITH RECURSIVE 支持很早）和 MySQL 8.0（CTE 从 8.0 开始），Impala 的递归 CTE 是 4.x 版本的重要补充。 |
| [全文搜索](../query/full-text-search/impala.md) | **无全文搜索能力**——需依赖外部搜索引擎（如 Solr/Elasticsearch）。对比 PostgreSQL 的 tsvector+GIN（内置最成熟）和 BigQuery 的 SEARCH INDEX（2023+），Impala 不提供文本搜索功能。 |
| [连接查询](../query/joins/impala.md) | **Broadcast/Partitioned Hash JOIN + JOIN 策略提示**——`/* +BROADCAST */` / `/* +SHUFFLE */` 提示强制选择 JOIN 策略。小表 Broadcast JOIN（广播到所有节点），大表 Partitioned Hash JOIN（按 JOIN 键重分布）。对比 BigQuery（优化器自动选择）和 PostgreSQL（Nested Loop/Hash/Merge JOIN），Impala 提供显式 JOIN 策略控制，在 MPP 引擎中较为独特。 |
| [分页](../query/pagination/impala.md) | **LIMIT/OFFSET 标准**——MPP 引擎下 LIMIT 不减少扫描量（与 BigQuery 类似），但限制返回行数。对比 BigQuery（LIMIT 不影响扫描成本）和 PostgreSQL（LIMIT 可减少实际处理量），Impala 的 LIMIT 行为是大数据引擎的通用特征。 |
| [行列转换](../query/pivot-unpivot/impala.md) | **无原生 PIVOT**——需使用 CASE + GROUP BY 手动实现。对比 BigQuery（PIVOT 原生 2021+）和 Oracle（PIVOT 11g+），Impala 缺乏行列转换语法糖。 |
| [集合操作](../query/set-operations/impala.md) | **UNION/INTERSECT/EXCEPT（3.x+）**——INTERSECT 和 EXCEPT 在 3.x 才引入，早期版本需用 JOIN/NOT EXISTS 模拟。对比 PostgreSQL（INTERSECT/EXCEPT 早已支持）和 MySQL 8.0（INTERSECT/EXCEPT 较新），Impala 的集合操作是逐步完善的。 |
| [子查询](../query/subquery/impala.md) | **IN/EXISTS 子查询（2.x+）+ 关联子查询**——子查询支持在 2.x 才逐步完善，早期版本限制较多。对比 PostgreSQL（子查询优化成熟）和 MySQL 8.0（子查询优化大幅改善），Impala 的子查询能力持续提升中。 |
| [窗口函数](../query/window-functions/impala.md) | **完整窗口函数（2.0+）+ ROWS/RANGE 帧**——ROW_NUMBER/RANK/DENSE_RANK/LAG/LEAD/NTILE 等完整支持。MPP 架构下窗口函数可利用多节点并行排序。对比 PostgreSQL（窗口函数完整）和 BigQuery（QUALIFY 子句更简洁），Impala 的窗口函数在 MPP 并行下性能优势明显。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/impala.md) | **无 generate_series**——需使用辅助表（预创建的日期维度表）或应用层生成日期序列。4.x+ 可用递归 CTE 生成。对比 PostgreSQL 的 generate_series（最简洁）和 BigQuery 的 GENERATE_DATE_ARRAY，Impala 在日期生成上较为不便。 |
| [去重](../scenarios/deduplication/impala.md) | **ROW_NUMBER + CTE 去重**——标准窗口函数去重模式，MPP 并行排序加速。对比 PostgreSQL 的 DISTINCT ON（更简洁）和 BigQuery 的 QUALIFY（最简洁），Impala 的去重方案是通用写法。 |
| [区间检测](../scenarios/gap-detection/impala.md) | **窗口函数 LAG/LEAD 检测间隙**——无 generate_series 辅助，需纯靠窗口函数比较相邻行。对比 PostgreSQL 的 generate_series + LEFT JOIN（更完整）和 BigQuery（GENERATE_DATE_ARRAY），Impala 的间隙检测方案较为基础。 |
| [层级查询](../scenarios/hierarchical-query/impala.md) | **递归 CTE（4.x+）**——4.x 之前版本无法做递归层级查询，需应用层递归或预计算扁平化表。对比 PostgreSQL（WITH RECURSIVE 早已支持）和 Oracle（CONNECT BY），Impala 的递归能力是较新补充。 |
| [JSON 展开](../scenarios/json-flatten/impala.md) | **GET_JSON_OBJECT/JSON_EXTRACT（Hive 兼容）**——从 JSON 字符串中提取路径值，无原生 JSON_TABLE 展开为行。对比 PostgreSQL 的 jsonb_array_elements（可展开为行）和 BigQuery 的 JSON_QUERY_ARRAY+UNNEST，Impala 的 JSON 处理能力有限。 |
| [迁移速查](../scenarios/migration-cheatsheet/impala.md) | **Hive 兼容查询引擎，Kudu/HDFS 双模式是核心差异**。关键注意：HDFS 表不可变（无 UPDATE/DELETE）；Kudu 表可变但需 Kudu 集群；COMPUTE STATS 是性能必需；INVALIDATE METADATA 同步外部变更；无存储过程/触发器；容错能力弱（节点故障查询失败）。 |
| [TopN 查询](../scenarios/ranking-top-n/impala.md) | **ROW_NUMBER + LIMIT 标准**——MPP 并行排序使 TopN 在大数据集上高效。对比 PostgreSQL（单机排序）和 BigQuery（QUALIFY 更简洁），Impala 的 TopN 利用 MPP 并行。 |
| [累计求和](../scenarios/running-total/impala.md) | **SUM() OVER 标准 + MPP 并行**——MPP 架构下窗口函数可利用多节点并行计算。对比各主流引擎写法一致，Impala 的 MPP 并行是性能优势。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/impala.md) | **UPSERT（Kudu 表）/ INSERT OVERWRITE（HDFS 表）**——Kudu 表的 UPSERT 是最简洁的 SCD Type 1 实现；HDFS 表需用 INSERT OVERWRITE 整体替换分区。对比 PostgreSQL 的 ON CONFLICT 和 BigQuery 的 MERGE，Impala 的方案因存储后端而异。 |
| [字符串拆分](../scenarios/string-split-to-rows/impala.md) | **无原生拆分展开函数**——需编写 C++/Java UDF 或在应用层处理。对比 PostgreSQL 的 string_to_array+unnest（一行搞定）和 BigQuery 的 SPLIT+UNNEST，Impala 在字符串拆分上是明显短板。 |
| [窗口分析](../scenarios/window-analytics/impala.md) | **完整窗口函数（2.0+）+ MPP 并行**——移动平均、占比、排名等分析场景全覆盖。MPP 架构下大数据集窗口分析性能优越。对比 PostgreSQL（单机窗口函数）和 BigQuery（QUALIFY 简化过滤），Impala 的窗口分析在 Hadoop 生态中性能领先。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/impala.md) | **ARRAY/MAP/STRUCT（Parquet/ORC 嵌套类型）**——Impala 支持查询 Parquet/ORC 文件中的嵌套结构，可直接 SELECT nested.field 或 UNNEST(array_col)。对比 BigQuery（STRUCT/ARRAY 一等公民）和 PostgreSQL（ARRAY 原生，无 MAP），Impala 的复合类型来自文件格式的嵌套模式支持。 |
| [日期时间](../types/datetime/impala.md) | **TIMESTAMP（纳秒精度）/ DATE（3.x+），无 TIME/INTERVAL**——TIMESTAMP 存储纳秒精度时间戳但不含时区信息。DATE 类型在 3.x 才引入。对比 PostgreSQL（DATE/TIME/TIMESTAMP/INTERVAL 完整）和 BigQuery（四种时间类型），Impala 的时间类型较简单。 |
| [JSON](../types/json/impala.md) | **GET_JSON_OBJECT 路径查询，无原生 JSON 类型**——JSON 数据存储为 STRING 类型，通过函数提取路径值。对比 PostgreSQL 的 JSONB（原生类型+GIN 索引）和 BigQuery（JSON 类型 2022+），Impala 的 JSON 支持较为基础。 |
| [数值类型](../types/numeric/impala.md) | **TINYINT-BIGINT/FLOAT/DOUBLE/DECIMAL(38) 标准**——DECIMAL(precision, scale) 最大 38 位精度。对比 PostgreSQL 的 NUMERIC（任意精度）和 BigQuery 的 BIGNUMERIC（76 位），Impala 的 DECIMAL 精度对大多数场景足够。 |
| [字符串类型](../types/string/impala.md) | **STRING 无长度限制 + VARCHAR/CHAR**——STRING 是推荐类型（无长度约束），VARCHAR(n)/CHAR(n) 可选。对比 BigQuery 的 STRING（类似无长度限制）和 PostgreSQL 的 TEXT（类似），Impala 的 STRING 设计与 Hadoop 生态一致。 |
