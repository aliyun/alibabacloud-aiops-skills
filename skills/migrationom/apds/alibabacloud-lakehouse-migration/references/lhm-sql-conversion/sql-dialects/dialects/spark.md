# Spark SQL

**分类**: 大数据计算引擎
**文件数**: 51 个 SQL 文件
**总行数**: 4707 行

> **关键人物**：[Matei Zaharia](../docs/people/spark-databricks.md)（Spark 创始人，ACM 博士论文奖）、[Michael Armbrust](../docs/people/spark-databricks.md)（Spark SQL 核心设计者，Catalyst 优化器）、[Reynold Xin](../docs/people/spark-databricks.md)（Tungsten 引擎，Photon）

## 概述与定位

Spark SQL 是 Apache Spark 大数据统一计算引擎的 SQL 层。它不是一个独立的数据库，而是运行在 Spark 之上的 SQL 接口——既可以查询 Hive 表、Parquet/ORC 文件，也可以查询 JDBC 数据源、Kafka 流等。Spark SQL 的独特价值在于**SQL 与编程 API 的无缝融合**：一个 DataFrame 既可以用 SQL 查询，也可以用 Python/Scala/Java API 操作，两者可以自由混合。

Spark SQL 的定位是"大数据批处理与流处理的统一 SQL 层"。通过 Catalyst 优化器和 Tungsten 执行引擎，它在保持 Hive 兼容性的同时，大幅超越了 Hive 的执行性能。

## 历史与演进

| 时间 | 里程碑 |
|------|--------|
| 2009 | UC Berkeley AMPLab 启动 Spark 项目，最初定位为 MapReduce 的替代品 |
| 2014 | Apache Spark 成为顶级项目；Spark SQL 随 Spark 1.0 发布，引入 DataFrame API |
| 2015 | Spark 1.3 推出 DataFrame API（取代 SchemaRDD），Spark 1.6 引入 Dataset API |
| 2016 | Spark 2.0：统一 DataFrame 和 Dataset，引入 Structured Streaming |
| 2020 | Spark 3.0：AQE（Adaptive Query Execution）自适应查询执行、ANSI SQL 模式（默认关闭）、动态分区裁剪 |
| 2022 | Spark 3.3+：持续增强 ANSI 兼容性、DSv2 Data Source API、Pandas API on Spark |
| 2024 | Spark 4.0：ANSI 模式默认开启、Variant 类型、IDENTIFIER 子句、Collation 支持 |

## 核心设计思路

- **Catalyst 优化器**：Spark SQL 的核心。它将 SQL/DataFrame 操作统一编译为逻辑计划，然后经过规则优化（Rule-Based，如常量折叠、谓词下推）和代价优化（Cost-Based，如 Join 策略选择），最终生成物理执行计划。Catalyst 的可扩展架构允许外部开发者注入自定义优化规则。
- **Tungsten 执行引擎**：绕过 JVM 的对象模型，直接操作二进制内存布局（off-heap memory），结合 Whole-Stage Code Generation（将整个 Stage 编译为单个 Java 函数）大幅减少虚函数调用和内存开销。
- **Hive 兼容但超越**：Spark SQL 默认使用 Hive Metastore 管理表元数据，兼容 Hive SQL 语法（STORED AS、PARTITIONED BY、LATERAL VIEW 等），但在执行性能上通常比 Hive 快 10-100 倍。
- **批流一体**：Structured Streaming 将流数据视为不断追加的 DataFrame，用户可以用相同的 SQL/DataFrame API 处理批数据和流数据。虽然流处理能力不如 Flink SQL 专业，但统一的编程模型降低了学习成本。

## 独特特色

- **USING 子句指定数据源格式**：`CREATE TABLE t USING PARQUET` / `USING DELTA` / `USING JSON`。这是 Spark SQL 对 Hive 的 `STORED AS` 的扩展，通过 DataSource API 支持任意数据源插件。
- **DataFrame API 与 SQL 互通**：`df = spark.sql("SELECT ...")`、`df.createOrReplaceTempView("v")`、`spark.sql("SELECT * FROM v")`。SQL 查询结果可以立即用 API 操作，反之亦然。这种互通性在数据工程中非常实用。
- **AQE 自适应查询执行**：Spark 3.0+ 的标志性特性。在运行时根据实际数据统计信息动态调整执行计划——自动合并过小的 Shuffle 分区、自动将 Sort-Merge Join 转为 Broadcast Hash Join、自动处理数据倾斜。AQE 解决了 CBO 在统计信息不准确时的局限性。
- **Delta Lake / Iceberg 集成**：通过 Delta Lake 或 Apache Iceberg 插件，Spark SQL 获得了 ACID 事务、Time Travel、MERGE/UPDATE/DELETE 等原本缺失的能力。Delta Lake 几乎已成为 Databricks 平台的标配存储层。
- **Broadcast Hint**：`SELECT /*+ BROADCAST(small_table) */ ...` 提示优化器将小表广播到所有 Executor，避免 Shuffle Join。这是 Spark SQL 中最常用的性能优化手段之一。
- **Pandas UDF（Arrow UDF）**：通过 Apache Arrow 实现的向量化 Python UDF，性能比传统 Python UDF 快 10-100 倍。用户可以用 Pandas API 编写批处理逻辑，Spark 自动将其向量化执行。

## 已知的设计不足与历史包袱

- **无原生 UPDATE/DELETE**：原生 Spark SQL（不使用 Delta/Iceberg）不支持行级 UPDATE/DELETE。只能通过 INSERT OVERWRITE 重写整个分区。这一限制使得原生 Spark SQL 无法胜任数据修正和 SCD（缓慢变化维）场景，必须依赖 Lakehouse 层。
- **无存储过程/触发器**：Spark SQL 是纯查询引擎，不支持过程式编程。复杂逻辑需要在 Spark 应用程序（Python/Scala/Java）中实现。
- **ANSI 模式默认关闭**（4.0 之前）：默认情况下，整数溢出不报错、类型隐式转换宽松，这导致了大量隐式 bug。Spark 4.0 才将 ANSI 模式默认开启，但大量存量代码依赖非 ANSI 行为。
- **JVM 启动延迟**：Spark 基于 JVM，SparkSession 初始化、Driver/Executor 启动需要数秒甚至数十秒。对于小查询（毫秒级延迟需求），Spark SQL 并不适合。
- **小查询性能差**：Spark 的 Stage 调度、Shuffle、序列化等开销在处理小数据集时尤为明显。一个在 PostgreSQL 中 10ms 完成的查询，在 Spark SQL 中可能需要数秒。Spark SQL 的优势仅在数据量足够大时才能体现。

## 兼容生态

Spark SQL 高度兼容 Hive SQL 语法，是 Hive 的事实上的继任执行引擎。通过 Hive Metastore 集成可以无缝读写 Hive 表。Spark SQL 也通过 JDBC/ODBC（Spark Thrift Server）对外提供 SQL 服务。与 Delta Lake、Iceberg、Hudi 等 Lakehouse 格式的集成构成了现代数据湖仓的核心栈。

## 对引擎开发者的参考价值

- **Catalyst 优化器架构**：规则优化（Rule-Based Optimization）+ 代价优化（Cost-Based Optimization）的分层设计，加上 TreeNode 模式匹配的变换框架，是现代 SQL 优化器的教科书级参考。许多新兴引擎（如 Apache Calcite）受其影响。
- **Tungsten 内存管理**：证明了在 JVM 之上通过 off-heap 内存管理和代码生成可以达到接近 C++ 引擎的性能。Whole-Stage CodeGen 将操作符融合为单个函数的思路，被后续引擎广泛采用。
- **AQE 运行时重优化**：在查询执行过程中收集实际统计信息并动态调整计划的做法，解决了传统 CBO 依赖准确统计信息的固有缺陷。这一思路代表了查询优化器的未来方向。

---

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/spark.md) | **USING 子句是 Spark SQL 对 Hive STORED AS 的关键扩展**——`USING PARQUET/DELTA/ICEBERG/JSON` 通过 DataSource API 支持任意数据源插件。DataFrame API 和 SQL DDL 双接口互通：`df.write.saveAsTable("t")` 等价于 CREATE TABLE。ANSI 模式 4.0 才默认开启，之前类型溢出不报错是隐式 bug 根源。对比 Hive（STORED AS 固定格式列表）和 BigQuery（Capacitor 格式固定），Spark 的 DataSource 插件化最灵活。 |
| [改表](../ddl/alter-table/spark.md) | **Delta Lake 支持 Schema Evolution（自动合并 Schema）**——原生 Spark Hive 表的 ALTER 仅支持 ADD COLUMNS，不能改列类型。Delta Lake 的 `mergeSchema` 选项可在写入时自动演进 Schema。对比 Snowflake（ALTER 瞬时但不支持改类型）和 Hive（ADD/REPLACE COLUMNS），Spark+Delta 的 Schema Evolution 是最灵活的方案。 |
| [索引](../ddl/indexes/spark.md) | **无传统索引——Data Skipping(Delta Lake)+Z-ORDER 是物理优化的核心**。Delta Lake 自动收集每个文件的列级 min/max 统计信息（Data Skipping），Z-ORDER 多维排序优化多列过滤。对比 ClickHouse（稀疏索引+跳数索引）和 BigQuery（CLUSTER BY 最多 4 列），Spark+Delta 的 Z-ORDER 在多维分析场景中效果最佳。 |
| [约束](../ddl/constraints/spark.md) | **CHECK/NOT NULL 约束(Delta Lake 3.0+)写入时强制执行，PK/FK 仅声明不强制**——Delta Lake 的 CHECK 约束在写入时实际校验（不同于 BigQuery/Snowflake 的 NOT ENFORCED），这是 Lakehouse 引擎中约束支持最强的。对比 BigQuery/Snowflake（所有约束 NOT ENFORCED）和 PG（全部强制执行），Spark+Delta 在约束执行力度上介于二者之间。 |
| [视图](../ddl/views/spark.md) | **TEMPORARY VIEW(会话级)+GLOBAL TEMPORARY VIEW(SparkSession 级)**——GLOBAL TEMP VIEW 存储在 `global_temp` 数据库中，跨 SQL 会话可见但 SparkSession 结束后消失。无物化视图（需 Delta Lake 的 `OPTIMIZE` 或手动 CTAS 缓存）。对比 BigQuery（物化视图自动增量刷新）和 Snowflake（物化视图自动维护），Spark 的视图最为简单。 |
| [序列与自增](../ddl/sequences/spark.md) | **无 SEQUENCE，`monotonically_increasing_id()` 生成非连续唯一 ID**——返回值在分区内递增但跨分区不连续（高位编码分区 ID）。不适合作为业务主键。对比 BigQuery 的 GENERATE_UUID() 和 Snowflake 的 AUTOINCREMENT，Spark 的 ID 生成方案最受限——分布式环境下不保证顺序、不保证连续、甚至不保证跨作业唯一。 |
| [数据库/Schema/用户](../ddl/users-databases/spark.md) | **Catalog.Database.Table 三级命名空间**——通过 Catalog Plugin API 支持多种元数据后端（Hive Metastore、Unity Catalog、Iceberg Catalog）。Unity Catalog(Databricks)提供跨 Workspace 的统一数据治理。对比 BigQuery 的 Project.Dataset.Table 和 Snowflake 的 Database.Schema.Object，Spark 的 Catalog 插件化使其可接入任意元数据系统。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/spark.md) | **无 SQL 层动态 SQL——用 DataFrame API 在 Python/Scala/Java 中构建动态查询**。`spark.sql(f"SELECT ... WHERE col = '{val}'")` 是最常用的动态查询模式。对比 Snowflake（EXECUTE IMMEDIATE）和 MaxCompute（Script Mode），Spark 将动态逻辑完全推到编程语言层，SQL 本身是静态的。 |
| [错误处理](../advanced/error-handling/spark.md) | **无 SQL 层错误处理——异常在 Scala/Python 应用层 try/catch/except 处理**。ANSI 模式关闭时（4.0 前默认），类型溢出、除零等静默返回错误值而非报错——这是 Spark SQL 最大的数据质量隐患。对比 BigQuery（SAFE_ 前缀行级安全）和 Snowflake（EXCEPTION 块），Spark 的错误处理完全依赖编程语言而非 SQL。 |
| [执行计划](../advanced/explain/spark.md) | **EXPLAIN EXTENDED/FORMATTED 展示 Catalyst 优化器的完整变换过程**——可查看 Parsed→Analyzed→Optimized→Physical 四阶段计划变换。Spark UI 提供 DAG 可视化和 Stage/Task 级别的执行指标。AQE(3.0+)使执行计划在运行时动态调整，EXPLAIN 显示的是初始计划。对比 BigQuery（无 EXPLAIN，Console 查看执行详情）和 ClickHouse（EXPLAIN PIPELINE 展示执行管道），Spark 的 EXPLAIN 信息量最丰富但也最复杂。 |
| [锁机制](../advanced/locking/spark.md) | **无行级锁——Delta Lake 提供乐观并发控制+冲突检测**。两个并发写入同一 Delta 表的操作在提交时检测冲突：不相交的分区写入自动成功，重叠写入报 ConcurrentAppendException。对比 Snowflake（乐观并发自动管理）和 BigQuery（DML 配额限制并发），Delta Lake 的乐观并发模型适合 ETL 管线但不适合高并发 OLTP。 |
| [分区](../advanced/partitioning/spark.md) | **PARTITIONED BY 继承 Hive 目录分区，Bucket 分桶优化 JOIN**——分区用于数据管理和裁剪（按日期/地区），分桶用于 Join 优化（预分配 hash 桶避免 Shuffle）。动态分区裁剪(DPP 3.0+)在运行时根据 JOIN 条件自动裁剪分区。对比 BigQuery（分区列是普通列）和 Snowflake（自动微分区无需管理），Spark 继承了 Hive 的分区=目录模型并增加了分桶优化。 |
| [权限](../advanced/permissions/spark.md) | **无内置权限系统——依赖 Ranger 或 Unity Catalog(Databricks)**。Storage-Based Authorization 基于 HDFS 文件权限。Unity Catalog 提供细粒度的表/列/行级权限和数据血缘。对比 Snowflake（RBAC+DAC 内置完善）和 BigQuery（完全基于 GCP IAM），开源 Spark 的权限管理最为薄弱。 |
| [存储过程](../advanced/stored-procedures/spark.md) | **无存储过程——UDF(Scala/Python/Java) 和 Pandas UDF 替代**。Pandas UDF（Arrow UDF）通过 Apache Arrow 实现向量化 Python UDF，性能比传统 Python UDF 快 10-100 倍。对比 Snowflake（多语言存储过程最强）和 Hive（UDF/UDAF/UDTF Java 接口），Spark 的 Pandas UDF 是大数据生态中最高效的用户自定义函数方案。 |
| [临时表](../advanced/temp-tables/spark.md) | **CREATE TEMP VIEW 会话级，CACHE TABLE 将数据缓存到内存/磁盘**——CACHE TABLE 是 Spark 独有的性能优化：`CACHE TABLE t AS SELECT ...` 将查询结果物化到内存。UNCACHE TABLE 释放缓存。对比 BigQuery（_SESSION 临时表）和 Snowflake（TEMPORARY+TRANSIENT），Spark 的 CACHE TABLE 兼具临时表和物化视图的功能。 |
| [事务](../advanced/transactions/spark.md) | **原生 Spark SQL 无事务保证——Delta Lake 提供完整 ACID 事务**。Delta Lake 基于 Write-Ahead Log（事务日志）实现 Serializable 隔离级别。Time Travel 通过 `VERSION AS OF` / `TIMESTAMP AS OF` 查询历史版本。对比 BigQuery（多语句事务有 DML 配额）和 Snowflake（ACID 自动提交），Delta Lake 是 Lakehouse 事务的事实标准。 |
| [触发器](../advanced/triggers/spark.md) | **无触发器——Structured Streaming 流式处理替代事件驱动**。Structured Streaming 将流数据视为不断追加的 DataFrame，可用相同的 SQL/API 处理。Delta Lake 的 Change Data Feed(CDF)提供表级变更追踪。对比 ClickHouse（物化视图=INSERT 触发器）和 Snowflake（Streams+Tasks），Spark 的流处理方案功能更强但运维更复杂。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/spark.md) | **DELETE 仅 Delta Lake/Iceberg 表支持，原生 Spark 表不支持行级删除**——原生表只能 INSERT OVERWRITE 整个分区来"删除"数据。Delta Lake 的 DELETE 通过重写受影响的文件实现（非原地删除）。Vacuum 命令清理过期文件。对比 BigQuery（DELETE 重写整个分区）和 ClickHouse（Lightweight Delete 22.8+），Spark 的行级删除完全依赖 Lakehouse 层。 |
| [插入](../dml/insert/spark.md) | **INSERT INTO/OVERWRITE 继承 Hive，DataFrame write API 更常用**——`df.write.mode("overwrite").saveAsTable("t")` 是 Spark 数据工程的标准写入模式。INSERT OVERWRITE 保持 Hive 的幂等语义。对比 BigQuery（批量加载免费）和 Snowflake（COPY INTO 批量加载），Spark 的 DataFrame write API 在编程灵活性上无可匹敌。 |
| [更新](../dml/update/spark.md) | **UPDATE 仅 Delta Lake/Iceberg 表支持，原生 Spark 表完全不支持行级更新**——这是原生 Spark SQL 最大的功能缺陷。Delta Lake 的 UPDATE 通过 Copy-on-Write 重写文件实现。对比 BigQuery/Snowflake（UPDATE 标准但重写微分区）和 Hive ACID（delta 文件记录变更），Spark 必须依赖 Lakehouse 层才能行级变更。 |
| [Upsert](../dml/upsert/spark.md) | **MERGE INTO(Delta Lake/Iceberg)功能完整——WHEN MATCHED/NOT MATCHED/NOT MATCHED BY SOURCE 三分支**。Delta Lake 的 MERGE 是 SCD(缓慢变化维)实现的标准方案。对比 BigQuery（MERGE 是唯一 Upsert）和 ClickHouse（ReplacingMergeTree 合并时去重），Spark+Delta 的 MERGE 在功能完整性上与 Snowflake 并列最强。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/spark.md) | **GROUPING SETS/CUBE/ROLLUP 完整，collect_list/collect_set 继承 Hive**——APPROX_COUNT_DISTINCT(HyperLogLog)提供近似去重。percentile_approx 大数据集百分位数计算。对比 BigQuery 的 COUNTIF（条件计数，替代 FILTER 子句）和 ClickHouse 的 -If/-State 组合后缀（最灵活），Spark 的聚合函数集与 Hive 高度兼容。 |
| [条件函数](../functions/conditional/spark.md) | **IF/CASE/COALESCE/NVL/NVL2 继承 Hive 兼容**——NVL2(expr, val_if_not_null, val_if_null) 是 Oracle 风格的三元 NULL 判断。ANSI 模式关闭时条件表达式的类型提升规则宽松（可能静默丢精度）。对比 BigQuery 的 SAFE_ 前缀（行级安全）和 Snowflake 的 IFF（简洁条件），Spark 保持 Hive 函数集。 |
| [日期函数](../functions/date-functions/spark.md) | **date_format/date_add/datediff 继承 Hive 命名惯例**——`make_date(year, month, day)` 和 `make_timestamp()` 是 Spark 独有的日期构造函数（Hive 无）。Spark 4.0+ 的 TIMESTAMP_NTZ 类型引入后，日期函数的时区行为更明确。对比 BigQuery 的 GENERATE_DATE_ARRAY（日期序列生成）和 Snowflake 的 DATE_TRUNC，Spark 的日期函数在 Hive 基础上逐步扩展。 |
| [数学函数](../functions/math-functions/spark.md) | **完整数学函数继承 Hive（ABS/CEIL/FLOOR/ROUND/POWER 等）**——ANSI 模式关闭时整数溢出不报错（静默回绕），这是历史上最大的数据质量陷阱。4.0 默认开启 ANSI 后溢出会报错。对比 BigQuery 的 SAFE_DIVIDE（独有安全除法）和 PG 的严格类型系统，Spark 在 4.0 之前的数学运算安全性最差。 |
| [字符串函数](../functions/string-functions/spark.md) | **concat/concat_ws/regexp_extract/replace/split 继承 Hive**——split 返回 ARRAY 配合 explode/posexplode 展开为行。REGEXP 基于 Java 正则引擎（支持回溯，对比 BigQuery 的 re2 线性时间引擎可能有性能风险）。对比 Snowflake 的 SPLIT_PART（按位置提取）和 PG 的 string_to_array，Spark 的字符串函数完全 Hive 风格。 |
| [类型转换](../functions/type-conversion/spark.md) | **CAST 标准，try_cast(3.4+) 安全转换——失败返回 NULL 而非报错**。3.4 之前无安全转换函数（Hive 也没有），脏数据导致整个查询失败。ANSI 模式下 CAST 失败报错（4.0 前默认不报错）。对比 BigQuery 的 SAFE_CAST（长期可用）和 Snowflake 的 TRY_CAST（长期可用），Spark 的安全转换引入较晚。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/spark.md) | **WITH 标准语法 + 递归 CTE(3.4+)**——3.4 之前不支持递归 CTE（需 DataFrame API 迭代实现）。CTE 物化/内联由 Catalyst 优化器自动决策。对比 Hive（3.1+ 才支持递归 CTE）和 BigQuery（递归 CTE 有迭代限制），Spark 的递归 CTE 引入也较晚。 |
| [全文搜索](../query/full-text-search/spark.md) | **无任何全文搜索能力**——纯计算引擎不管理持久化索引。只能用 LIKE/RLIKE 全量扫描。对比 BigQuery（SEARCH INDEX 2023+）和 Doris（倒排索引 2.0+ 基于 CLucene），Spark 的文本检索需借助外部 Elasticsearch 或 Solr。 |
| [连接查询](../query/joins/spark.md) | **Broadcast/Sort-Merge/Shuffle Hash JOIN 三种策略，AQE 运行时自动切换**——AQE(3.0+)是标志性特性：运行时根据实际数据统计自动将 Sort-Merge JOIN 转为 Broadcast Hash JOIN（无需用户 Hint）。`/*+ BROADCAST(t) */` Hint 可强制广播小表。对比 Hive（更依赖 MAPJOIN Hint）和 BigQuery（全自动无 Hint），Spark 的 AQE 在自动化和可控性之间取得最佳平衡。 |
| [分页](../query/pagination/spark.md) | **LIMIT+ORDER BY 标准，无 OFFSET**——DataFrame API 的 `take(n)` / `head(n)` 是更常用的取样方式。批处理引擎下分页是罕见需求。对比 BigQuery（LIMIT/OFFSET 标准）和 Snowflake（LIMIT/OFFSET+FETCH FIRST），Spark 的分页能力在 SQL 层最为简单。 |
| [行列转换](../query/pivot-unpivot/spark.md) | **PIVOT/UNPIVOT(3.4+) 原生支持，stack() 函数早期替代**——PIVOT 需要枚举值列表（不支持动态 PIVOT）。stack() 是 Spark 独有的列转行函数。对比 BigQuery/Snowflake 的原生 PIVOT（2021+）和 ClickHouse（无 PIVOT 需 sumIf 模拟），Spark 3.4+ 的 PIVOT/UNPIVOT 功能完整。 |
| [集合操作](../query/set-operations/spark.md) | **UNION/INTERSECT/EXCEPT ALL/DISTINCT 完整支持**——UNION ALL 是默认（性能最优，不去重），UNION DISTINCT 触发额外的去重步骤。对比 ClickHouse（UNION 默认 ALL 与标准相反）和 Hive（2.0+ 才完整），Spark 的集合操作标准完备。 |
| [子查询](../query/subquery/spark.md) | **关联子查询(2.0+)完整支持，Catalyst 善于自动转为 JOIN**——IN/EXISTS/NOT EXISTS/标量子查询均支持。Catalyst 优化器可将关联子查询去关联化（Decorrelation）并转为高效的 Semi/Anti Join。对比 MySQL 5.x 的子查询性能噩梦和 BigQuery 的自动转 JOIN，Spark 的子查询优化在 2.0+ 后达到主流水平。 |
| [窗口函数](../query/window-functions/spark.md) | **完整窗口函数继承 Hive，ROWS/RANGE 帧支持完整**——ROW_NUMBER/RANK/LAG/LEAD/SUM OVER 等全部支持。Tungsten 引擎对窗口函数有专门的代码生成优化。无 QUALIFY 子句（需子查询包装）。对比 BigQuery/Snowflake 的 QUALIFY 和 ClickHouse（21.1+ 才支持），Spark 的窗口函数功能完整但缺乏 QUALIFY 扩展。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/spark.md) | **sequence() 函数(2.4+) 生成日期序列+explode 展开**——`explode(sequence(date'2024-01-01', date'2024-12-31', interval 1 day))` 是 Spark 独有的简洁方案。对比 BigQuery 的 GENERATE_DATE_ARRAY+UNNEST（同样简洁）和 Hive（无等价函数需辅助表），Spark 的 sequence() 在大数据引擎中最早提供了日期序列生成能力。 |
| [去重](../scenarios/deduplication/spark.md) | **ROW_NUMBER+窗口函数 SQL 去重，dropDuplicates() DataFrame API 更简洁**——`df.dropDuplicates(["id"])` 是 Spark 独有的 API 级去重（无需写 SQL）。对比 BigQuery/Snowflake 的 QUALIFY（SQL 最简去重）和 ClickHouse 的 ReplacingMergeTree（存储层去重），Spark 的双接口（SQL+API）使去重灵活度最高。 |
| [区间检测](../scenarios/gap-detection/spark.md) | **sequence()+窗口函数检测——sequence() 生成期望序列与实际数据对比**。对比 ClickHouse 的 WITH FILL（独有语法自动填充）和 PG 的 generate_series+LEFT JOIN，Spark 的 sequence() 提供了比 Hive 更优雅的方案。 |
| [层级查询](../scenarios/hierarchical-query/spark.md) | **递归 CTE 3.4+ 才支持——之前需 DataFrame API 迭代（graphX 或手动循环）**。3.4 之前的替代方案是用 Python/Scala 循环调用 `spark.sql()` 逐层查询并 UNION。对比 Hive（3.1+ 递归 CTE）和 PG（长期支持递归 CTE），Spark 的递归能力引入最晚。 |
| [JSON 展开](../scenarios/json-flatten/spark.md) | **from_json(schema)+explode 展开 JSON 数组，schema_of_json 自动推断结构**——`from_json(col, schema)` 将 JSON 字符串解析为 STRUCT/ARRAY，然后 explode 展开。schema_of_json 可从样本数据自动推断 Schema。对比 Snowflake 的 LATERAL FLATTEN（最优雅，无需预定义 Schema）和 BigQuery 的 JSON_QUERY_ARRAY+UNNEST，Spark 的 JSON 处理更灵活但需要更多代码。 |
| [迁移速查](../scenarios/migration-cheatsheet/spark.md) | **Hive 兼容语法是基础，但 Delta Lake 是推荐路径**——原生 Spark 表无 UPDATE/DELETE/MERGE，必须使用 Delta Lake/Iceberg。DataFrame API 比 SQL 更强大（支持动态 Schema、复杂 ETL）。ANSI 模式 4.0 前默认关闭需注意类型安全。对比 BigQuery/Snowflake（标准 SQL 完整）和 Hive（INSERT OVERWRITE 范式），迁移到 Spark 需同时理解 SQL 和 DataFrame 两种范式。 |
| [TopN 查询](../scenarios/ranking-top-n/spark.md) | **ROW_NUMBER+窗口函数+LIMIT 标准模式——无 QUALIFY 子句需子查询包装**。简单 TopN 可直接 ORDER BY+LIMIT。DataFrame API 的 `groupBy().agg().orderBy().limit(n)` 更简洁。对比 BigQuery/Snowflake 的 QUALIFY（单行表达式最简）和 ClickHouse 的 LIMIT BY（每组限行），Spark 的 TopN 在 SQL 层不够简洁但 API 层灵活。 |
| [累计求和](../scenarios/running-total/spark.md) | **SUM() OVER(ORDER BY ...) 标准窗口累计——分布式并行计算**。Tungsten 引擎对窗口函数的代码生成优化使大数据集累计计算高效。对比 BigQuery（Slot 自动扩展）和 ClickHouse（runningAccumulate 状态函数），Spark 的 Whole-Stage CodeGen 在窗口计算中优势明显。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/spark.md) | **MERGE INTO(Delta Lake/Iceberg) 是 SCD 的标准实现**——WHEN MATCHED/NOT MATCHED/NOT MATCHED BY SOURCE 三分支完整覆盖 SCD Type 1/2/3。Delta Lake 的 Change Data Feed(CDF)可追踪变更历史。对比 BigQuery 的 MERGE+Time Travel 和 Snowflake 的 MERGE+Streams，Spark+Delta 的 MERGE+CDF 功能最完整。 |
| [字符串拆分](../scenarios/string-split-to-rows/spark.md) | **split()+explode()/posexplode() 展开——继承 Hive 但语法更简洁**。`SELECT explode(split(str, ','))` 不需要 LATERAL VIEW 包装（Spark 简化了 Hive 的冗长语法）。posexplode 同时返回位置索引和值。对比 BigQuery 的 SPLIT+UNNEST 和 Snowflake 的 SPLIT_TO_TABLE，Spark 的方案简洁度适中。 |
| [窗口分析](../scenarios/window-analytics/spark.md) | **完整窗口函数+ROWS/RANGE 帧支持，Tungsten 代码生成优化**——移动平均、同环比、占比计算均可实现。无 QUALIFY 过滤（需子查询）、无 WINDOW 命名子句。对比 BigQuery/Snowflake（QUALIFY+WINDOW 命名子句最强）和 Hive（功能相同但执行更慢），Spark 的窗口分析性能最优但语法扩展不足。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/spark.md) | **ARRAY/MAP/STRUCT 原生支持（继承 Hive），explode/posexplode 展开**——与 Hive 不同的是 Spark 简化了 LATERAL VIEW 语法，可直接 `SELECT explode(arr) FROM t`。Schema 推断（`schema_of_json`、`from_avro`）使复合类型处理更灵活。对比 BigQuery 的 STRUCT/ARRAY 一等公民和 Snowflake 的 VARIANT，Spark 的复合类型在编程 API 层最强大。 |
| [日期时间](../types/datetime/spark.md) | **DATE/TIMESTAMP/TIMESTAMP_NTZ(3.4+) 三种类型**——TIMESTAMP_NTZ（无时区）是 3.4 才引入的关键改进，之前所有 TIMESTAMP 都带时区转换（易混淆）。无 TIME 类型（纯时间无日期）。对比 BigQuery 的四种时间类型（最完整）和 Snowflake 的三种 TIMESTAMP（NTZ/LTZ/TZ），Spark 3.4+ 的日期类型体系才追上主流。 |
| [JSON](../types/json/spark.md) | **无 JSON 原生类型——from_json/to_json 序列化，schema_of_json 自动推断 Schema**。JSON 数据存储为 STRING，查询时通过 from_json 解析为 STRUCT/ARRAY。Spark 4.0 引入 Variant 类型（半结构化，类似 Snowflake VARIANT）。对比 PG 的 JSONB+GIN 索引和 Snowflake 的 VARIANT（原生存储），Spark 的 JSON 处理在 4.0 之前需要显式 Schema 定义。 |
| [数值类型](../types/numeric/spark.md) | **TINYINT-BIGINT/FLOAT/DOUBLE/DECIMAL 继承 Hive 标准**——ANSI 模式关闭时整数溢出静默回绕（不报错），4.0 才修复这一危险默认值。DECIMAL 最大精度 38 位。对比 BigQuery 的 BIGNUMERIC(76,38)（精度最高）和 ClickHouse 的 Decimal256（256 位），Spark 的 DECIMAL 精度是标准水平。 |
| [字符串类型](../types/string/spark.md) | **STRING 无长度限制（继承 Hive），VARCHAR/CHAR 3.1+ 引入但仅做语义标记**——VARCHAR(n) 和 CHAR(n) 在 Spark 中不实际截断或填充（与 Hive 不同），仅作为 Schema 文档。Spark 4.0 引入 Collation 支持（大小写不敏感排序等）。对比 PG 的 VARCHAR(n)/TEXT 严格区分和 BigQuery 的 STRING（极简无长度），Spark 的字符串类型设计最宽松。 |
