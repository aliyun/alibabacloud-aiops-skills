# Apache Hive

**分类**: Hadoop 数仓（Apache）
**文件数**: 51 个 SQL 文件
**总行数**: 4629 行

## 概述与定位

Apache Hive 是大数据 SQL 化的开创者，首次让非 Java 程序员可以用 SQL 查询 Hadoop 上的海量数据。它的核心贡献不在于执行引擎本身（底层先后依赖 MapReduce、Tez、LLAP），而在于**定义了大数据 SQL 的语法标准和元数据管理模式**——Hive Metastore 至今仍是 Hadoop 生态中最重要的元数据服务。

Hive 的定位是"数据仓库基础设施"：它定义了表、分区、存储格式之间的映射关系，提供了 SQL 到分布式计算的编译能力。虽然在实时查询场景中已被 Spark SQL、Presto/Trino 等引擎超越，但 Hive 的元数据模型和 SQL 方言影响深远。

## 历史与演进

| 时间 | 里程碑 |
|------|--------|
| 2007 | Facebook 内部项目启动，目标是让分析师用 SQL 查询 HDFS 数据 |
| 2010 | 成为 Apache 顶级项目 |
| 2013 | Stinger Initiative（Hive 0.13）：引入 ORC 格式、Vectorized Query、Cost-Based Optimizer |
| 2016 | Hive 2.0：LLAP（Live Long And Process）常驻执行守护进程，大幅降低延迟 |
| 2018 | Hive 3.0：完整 ACID 事务支持（基于 ORC + Delta 文件），废弃索引功能 |
| 2020+ | 社区活跃度下降，但 Hive Metastore 作为独立服务持续被 Spark/Presto/Trino/Flink 等引擎依赖 |

## 核心设计思路

- **Schema-on-Read**：Hive 的核心理念是"先存储后定义结构"。数据以文件形式存放在 HDFS 上，建表时通过 SerDe（序列化/反序列化器）告诉 Hive 如何解读文件内容。这意味着同一份数据可以用不同 Schema 查询——表结构不绑定存储格式。
- **分区 = 目录**：`PARTITIONED BY (dt STRING)` 意味着每个分区值对应 HDFS 上的一个子目录（如 `/warehouse/t/dt=2024-01-01/`）。分区裁剪就是跳过不相关的目录。这一简单直接的映射关系使得分区管理透明且可预测。
- **SerDe 可插拔序列化**：Hive 通过 SerDe 接口支持任意数据格式——CSV、JSON、Avro、ORC、Parquet 等。用户甚至可以实现自定义 SerDe 读取特殊格式。这种可插拔设计是 Hive 能处理多样数据格式的关键。
- **INSERT OVERWRITE 为主要写入模式**：Hive 传统上不支持行级 UPDATE/DELETE，而是通过 `INSERT OVERWRITE` 整体重写分区。这一设计与 HDFS 的"一次写入多次读取"特性吻合——HDFS 不支持随机写入，重写整个分区反而是最高效的方式。
- **外部表概念**：`CREATE EXTERNAL TABLE` 不管理数据生命周期——DROP TABLE 只删除元数据不删除文件。这使得 Hive 可以安全地叠加在已有数据之上，不影响其他系统对数据的访问。

## 独特特色

- **STORED AS 子句**：`STORED AS ORC`、`STORED AS PARQUET` 直接在建表语句中声明存储格式，将物理存储选择提升为 DDL 级别的一等概念。这一设计被后来的 Spark SQL 完全继承。
- **PARTITIONED BY (目录级分区)**：分区列不存储在数据文件中，而是编码在目录路径里。这使得添加/删除分区非常轻量（仅操作元数据和目录），但也导致了小文件问题——分区过多会产生大量小文件。
- **INSERT OVERWRITE**：幂等写入——无论执行多少次，结果相同。这一特性天然适合批处理 ETL：失败重试不会产生重复数据。
- **LATERAL VIEW explode**：将数组列展开为多行的标准方式。`LATERAL VIEW explode(tags) t AS tag` 是 Hive 对嵌套数据的标志性处理手法。
- **SORT BY / DISTRIBUTE BY / CLUSTER BY**：Hive 区分了全局排序（ORDER BY）、Reducer 内排序（SORT BY）、数据分发（DISTRIBUTE BY）和分发+排序（CLUSTER BY），反映了底层 MapReduce 的执行模型。
- **UDF/UDAF/UDTF 接口**：三级用户自定义函数接口——标量函数(UDF)、聚合函数(UDAF)、表生成函数(UDTF)。虽然 API 设计较老旧，但定义了大数据 SQL 自定义函数的基本范式。

## 已知的设计不足与历史包袱

- **早期无 UPDATE/DELETE**：Hive 3.0 之前完全不支持行级更新和删除。即使 3.0+ 支持 ACID 表，也必须使用 ORC 格式且配置事务管理器，性能远不及传统 RDBMS。
- **无索引（3.0 废弃）**：Hive 曾有有限的索引支持，但效果不佳，在 3.0 版本正式废弃。替代方案是依赖 ORC/Parquet 的内置 min/max 统计信息和 Bloom Filter。
- **MapReduce 延迟高**：传统 MapReduce 执行引擎启动一个简单查询可能需要 30-60 秒。虽然 Tez 和 LLAP 大幅改善了延迟，但 Hive 的"批处理基因"使得它在交互式查询场景中仍然不够快。
- **Metastore 单点问题**：Hive Metastore 基于关系数据库（通常是 MySQL/PostgreSQL），在大规模集群中可能成为瓶颈。分区数过多（数万级别）会导致 Metastore 操作缓慢。
- **CTE 不支持递归**：Hive 的 WITH 子句仅用于查询重用，不支持递归 CTE，无法用 SQL 直接表达层级查询。
- **ACID 性能有限**：Hive ACID 通过 Delta 文件 + Compaction 实现，读取时需要合并 base 文件和多个 delta 文件，性能开销大，不适合高并发事务场景。

## 兼容生态

Hive SQL 方言是大数据领域的"通用语"。以下引擎高度兼容或直接复用 Hive 语法：
- **Spark SQL**：默认兼容 Hive 语法，可直接读写 Hive Metastore 中的表
- **Databricks**：基于 Spark SQL，继承 Hive 兼容性
- **MaxCompute（阿里云）**：早期版本几乎完全兼容 Hive SQL
- **Impala**：共享 Hive Metastore，SQL 语法高度兼容
- **Flink SQL**：通过 HiveCatalog 集成 Hive Metastore，支持读写 Hive 表
- **Presto/Trino**：通过 Hive Connector 访问 Hive Metastore 管理的数据

## 对引擎开发者的参考价值

- **分区 = 目录的设计模式**：将逻辑分区映射为物理目录结构，简单、透明、可预测。这一模式被 Delta Lake、Iceberg、Hudi 等现代 Lakehouse 格式继承并改进（它们用 manifest 文件替代了目录列表以解决小文件和原子性问题）。
- **SerDe 架构**：将数据格式的序列化/反序列化抽象为可插拔接口，使存储引擎与查询引擎解耦。这一思想影响了后续几乎所有大数据 SQL 引擎的数据源抽象设计。
- **INSERT OVERWRITE 的幂等写入**：在分布式系统中，幂等操作是故障恢复的基础。INSERT OVERWRITE 通过"整体替换"而非"增量追加"天然实现幂等性，这一模式至今仍是批处理 ETL 的最佳实践。

---

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/hive.md) | **STORED AS 子句定义了大数据存储格式标准**——`STORED AS ORC/PARQUET/AVRO` 将物理存储选择提升为 DDL 一等概念，被 Spark/MaxCompute 完全继承。外部表(`EXTERNAL TABLE`) vs 管理表决定 DROP TABLE 时是否删除数据文件。SerDe 可插拔架构使 Hive 能处理任意数据格式。对比 BigQuery（Capacitor 格式固定）和 Snowflake（微分区自动管理），Hive 将存储格式选择权完全交给用户。 |
| [改表](../ddl/alter-table/hive.md) | **ADD/REPLACE COLUMNS 追加式变更，MSCK REPAIR TABLE 修复分区元数据**——MSCK 是 Hive 独有的元数据同步机制：当 HDFS 上已有分区目录但 Metastore 中没有记录时修复。对比 BigQuery（不支持改列类型需 CTAS）和 Spark（Delta Lake 的 Schema Evolution 更灵活），Hive 的 ALTER 能力原始但分区管理功能实用。 |
| [索引](../ddl/indexes/hive.md) | **3.0 版本正式废弃索引功能**——早期索引实现效果不佳，被 ORC/Parquet 内置的 Predicate Pushdown（min/max 统计信息+Bloom Filter）替代。这是大数据引擎的普遍选择：列式存储格式自带的数据跳过能力使传统 B-Tree 索引不再必要。对比 ClickHouse（稀疏索引 8192 行一标记）和 Doris（Short Key+Bloom Filter+倒排索引），Hive 在数据跳过手段上最为简单。 |
| [约束](../ddl/constraints/hive.md) | **PK/FK/UNIQUE/NOT NULL 声明(3.0+)但全部 NOT ENFORCED**——仅作元数据提示供优化器使用（如 JOIN 消除冗余），写入时不校验。这一模式后来被 BigQuery、Snowflake 等云数仓完全采用。对比 PostgreSQL/MySQL 的强制约束和 ClickHouse 的 ASSUME 约束，Hive 开创了"约束仅作提示"的大数据范式。 |
| [视图](../ddl/views/hive.md) | **普通视图标准支持，物化视图(3.0+)支持自动查询重写**——物化视图可声明式定义，优化器自动将匹配的查询路由到物化视图。对比 BigQuery（自动增量刷新+智能改写最成熟）和 Oracle（Query Rewrite 功能最强），Hive 的物化视图是开源大数据引擎中的先行者。 |
| [序列与自增](../ddl/sequences/hive.md) | **无 SEQUENCE/AUTO_INCREMENT**——HDFS 不可变文件系统无法维护全局递增计数器。推荐 ROW_NUMBER() OVER() 或 UUID 生成代理键。对比 BigQuery（GENERATE_UUID）和 Snowflake（AUTOINCREMENT 不保证连续），Hive 开创了大数据引擎"放弃自增"的惯例。 |
| [数据库/Schema/用户](../ddl/users-databases/hive.md) | **Database=HDFS 目录，HMS(Hive Metastore)是元数据管理的事实标准**——HMS 至今仍被 Spark/Presto/Trino/Flink 等引擎依赖。权限通过 Ranger/Sentry 外部组件管理（非 SQL GRANT）。对比 Snowflake 的 Database.Schema.Object 和 BigQuery 的 Project.Dataset.Table，Hive 的 Database 映射直接对应文件系统目录。Metastore 在大规模集群中是隐藏瓶颈（分区数过多导致操作缓慢）。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/hive.md) | **无任何动态 SQL 能力**——HiveQL 编译为 MapReduce/Tez/Spark 作业，不支持运行时构建 SQL。对比 MaxCompute（Script Mode 2.0+）和 Snowflake（EXECUTE IMMEDIATE），Hive 在过程式能力方面最弱。复杂逻辑需在 Oozie/Airflow 调度层拼接 HiveQL 字符串。 |
| [错误处理](../advanced/error-handling/hive.md) | **无过程式错误处理，作业级别全部失败或全部成功**——MapReduce/Tez 作业失败后由调度系统（Oozie/Airflow）负责重试。对比 BigQuery（BEGIN...EXCEPTION）和 Snowflake（EXCEPTION 块），Hive 完全没有 SQL 层的错误处理机制。INSERT OVERWRITE 的幂等性部分弥补了这一缺陷——失败重跑不会产生重复数据。 |
| [执行计划](../advanced/explain/hive.md) | **EXPLAIN 展示 MapReduce/Tez DAG 执行计划**——可查看 Map/Reduce 阶段划分、数据分发策略和谓词下推情况。CBO(0.14+) 基于 Apache Calcite 实现代价估算。对比 Spark 的 EXPLAIN EXTENDED（AQE 运行时重优化）和 BigQuery（Console 的 Execution Details），Hive 的 EXPLAIN 输出以 MapReduce 任务结构为核心。 |
| [锁机制](../advanced/locking/hive.md) | **ACID 表(3.0+)支持行级锁，非 ACID 表完全无锁**——ACID 表通过 ZooKeeper 管理锁状态，并发 DML 可能等待锁释放。非 ACID 表同一分区的并发写入可能导致数据不一致。对比 BigQuery（DML 配额限制并发）和 Snowflake（乐观并发自动管理），Hive 的锁机制仅限于 ACID 表且依赖外部 ZooKeeper。 |
| [分区](../advanced/partitioning/hive.md) | **PARTITIONED BY 是 Hive 的核心设计——分区列编码在目录路径中**（`/t/dt=2024-01-01/`），不存储在数据文件中。分区裁剪在文件系统层面完成（跳过目录），动态分区插入自动创建子目录。MSCK REPAIR TABLE 同步 HDFS 新增目录到 Metastore。对比 BigQuery（分区列是普通列）和 Snowflake（自动微分区无需管理），Hive 的分区=目录模型被 Delta Lake/Iceberg/Hudi 继承并改进。 |
| [权限](../advanced/permissions/hive.md) | **无内置权限系统，依赖 Ranger/Sentry 外部集成**——Storage-Based Authorization 基于 HDFS 文件权限控制访问。Ranger 提供细粒度的表/列/行级权限策略。对比 BigQuery（完全基于 GCP IAM）和 Snowflake（RBAC+DAC 内置），Hive 的权限管理是大数据生态中最分散的——需要独立部署和管理 Ranger 集群。 |
| [存储过程](../advanced/stored-procedures/hive.md) | **无存储过程，UDF/UDAF/UDTF 三级自定义函数替代**——UDF（标量）、UDAF（聚合）、UDTF（表生成）通过 Java 编写并注册。API 设计较老旧但定义了大数据 SQL 自定义函数的基本范式，被 Spark/MaxCompute 继承。对比 Snowflake（JS/SQL/Python 多语言存储过程）和 Oracle（PL/SQL 最强大），Hive 完全没有过程式编程能力。 |
| [临时表](../advanced/temp-tables/hive.md) | **CREATE TEMPORARY TABLE 会话级，数据和元数据随会话结束清理**——临时表不注册到 Metastore，对其他会话不可见。对比 BigQuery（_SESSION.table_name 引用）和 Snowflake（TEMPORARY+TRANSIENT 不同 Time Travel 保留），Hive 的临时表实现简单直接。 |
| [事务](../advanced/transactions/hive.md) | **ACID 事务(3.0+)仅限 ORC 格式，基于 Delta 文件+Compaction**——读取时需合并 base 文件和多个 delta 文件，性能开销大。必须配置事务管理器且仅 ORC 格式支持。对比 Delta Lake/Iceberg（格式无关的事务层）和 BigQuery（透明事务），Hive ACID 的格式绑定和性能限制使其不适合高并发场景。非 ACID 表仍是主流用法。 |
| [触发器](../advanced/triggers/hive.md) | **不支持触发器**——批处理引擎无事件驱动机制。替代方案：Oozie/Airflow 调度定时触发、Hive 物化视图增量刷新。对比 ClickHouse（物化视图=INSERT 触发器）和 Snowflake（Streams+Tasks），Hive 完全依赖外部调度系统。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/hive.md) | **DELETE 仅 ACID 表支持，非 ACID 表只能 DROP PARTITION 丢弃整个分区**——这是 HDFS 不可变文件系统的根本限制。ACID 表的 DELETE 通过写入 delta 文件标记删除行，后台 Compaction 才真正物理删除。对比 BigQuery（DELETE 必须带 WHERE，重写整个分区）和 ClickHouse（Lightweight Delete 22.8+ 标记删除），Hive 对非 ACID 表的限制最严格。 |
| [插入](../dml/insert/hive.md) | **INSERT OVERWRITE 是核心写入模式——原子性替换整个分区，天然幂等**。LOAD DATA 将文件直接移动到表目录（不做转换，零计算开销）。动态分区插入（`INSERT OVERWRITE TABLE t PARTITION(dt) SELECT ...`）自动按分区列值创建目录。对比 BigQuery（批量加载免费）和 Snowflake（COPY INTO 从云存储批量加载），Hive 的 INSERT OVERWRITE 幂等性是批处理 ETL 的最佳实践。 |
| [更新](../dml/update/hive.md) | **UPDATE 仅 ACID 表(3.0+)支持，非 ACID 表完全不支持行级更新**——ACID 表的 UPDATE 写入 delta 文件记录变更，读取时合并。性能远不及 RDBMS 的行级原地更新。对比 BigQuery/Snowflake（UPDATE 重写微分区）和 ClickHouse（ALTER TABLE UPDATE 异步 Mutation），Hive 的行级更新是后来补充的能力，不是设计初衷。 |
| [Upsert](../dml/upsert/hive.md) | **MERGE INTO 仅 ACID 表(2.2+)，非 ACID 表用 INSERT OVERWRITE 全量替代**——MERGE 语法标准（WHEN MATCHED/NOT MATCHED），但仅限 ORC 格式的 ACID 表。非 ACID 表的"Upsert"需要先 JOIN 新旧数据再 INSERT OVERWRITE 整个分区。对比 BigQuery（MERGE 是唯一 Upsert）和 ClickHouse（ReplacingMergeTree 合并时去重），Hive 的 MERGE 受 ACID 表限制最大。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/hive.md) | **GROUPING SETS/CUBE/ROLLUP 完整支持，collect_list/collect_set 收集数组**——Hive 是大数据引擎中最早提供多维聚合的。PERCENTILE_APPROX 用于大数据集近似百分位。对比 BigQuery 的 APPROX_COUNT_DISTINCT（HyperLogLog）和 ClickHouse 的 -If/-State 组合后缀（最灵活），Hive 的聚合函数集定义了大数据 SQL 的基础标准。 |
| [条件函数](../functions/conditional/hive.md) | **IF/CASE/COALESCE/NVL 标准集，ASSERT_TRUE 数据校验独有**——`ASSERT_TRUE(condition)` 在条件不满足时抛出异常终止查询，用于数据质量检查。NVL 是 Oracle 风格的 NULL 替换。对比 BigQuery 的 SAFE_ 前缀（错误返回 NULL 不终止）和 Snowflake 的 IFF（简洁条件），Hive 的 ASSERT_TRUE 是防御式编程的独特工具。 |
| [日期函数](../functions/date-functions/hive.md) | **date_format/datediff/add_months 基础集，unix_timestamp 互转是核心**——`unix_timestamp(string, format)` 和 `from_unixtime(long, format)` 是 Hive 日期处理的标志性函数对。对比 BigQuery 的四种时间类型严格区分和 Snowflake 的 DATE_TRUNC/DATEADD（标准命名），Hive 的日期函数命名（全小写下划线风格）定义了大数据 SQL 的函数命名惯例。 |
| [数学函数](../functions/math-functions/hive.md) | **基础数学函数完整（ABS/CEIL/FLOOR/ROUND/POWER 等）**——除零返回 NULL（不报错），与 MySQL 行为一致。对比 BigQuery 的 SAFE_DIVIDE（独有安全除法）和 PG 的除零报错，Hive 的宽松错误处理风格被 Spark/MaxCompute 继承。 |
| [字符串函数](../functions/string-functions/hive.md) | **concat/concat_ws 拼接，regexp_extract/replace 正则，split 返回 ARRAY**——split() 返回 ARRAY 配合 LATERAL VIEW EXPLODE 展开为行，是 Hive 的标志性字符串处理模式。对比 BigQuery 的 SPLIT+UNNEST 和 Snowflake 的 SPLIT_TO_TABLE，Hive 的 LATERAL VIEW EXPLODE 语法更冗长但被整个 Hive 系生态继承。 |
| [类型转换](../functions/type-conversion/hive.md) | **CAST 标准转换，隐式转换规则较宽松**——STRING 到 NUMBER 的隐式转换不报错（返回 NULL），与 MySQL 行为类似。无 TRY_CAST 安全转换（MaxCompute 2.0+/Spark 3.4+ 才引入）。对比 BigQuery 的 SAFE_CAST 和 PG 的严格类型系统，Hive 的宽松隐式转换容易产生隐式 bug。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/hive.md) | **WITH 标准语法 + 递归 CTE(3.1+)**——3.1 之前不支持递归 CTE，层级查询需多次自连接（性能极差）。CTE 主要用于简化长 HiveQL 查询的可读性。对比 BigQuery（递归 CTE 有迭代次数限制）和 PG（长期完整支持递归 CTE），Hive 的递归 CTE 引入较晚。 |
| [全文搜索](../query/full-text-search/hive.md) | **无任何全文搜索能力**——无倒排索引、无 SEARCH 函数、无 FULLTEXT INDEX。只能用 LIKE/REGEXP 全表扫描。对比 BigQuery（SEARCH INDEX 2023+）和 Doris（倒排索引 2.0+ 基于 CLucene），Hive 的文本检索需完全借助外部 Elasticsearch。 |
| [连接查询](../query/joins/hive.md) | **Map/Reduce Side JOIN 反映底层执行模型**——小表 Broadcast JOIN（MAPJOIN Hint `/*+ MAPJOIN(small) */`）、大表 Sort-Merge JOIN、默认 Reduce Side JOIN。Hive 的 JOIN 策略直接映射到 MapReduce 的 Map 和 Reduce 阶段。对比 Spark（AQE 运行时自动切换）和 BigQuery（全自动 Broadcast/Shuffle），Hive 更依赖用户 Hint 指定 JOIN 策略。 |
| [分页](../query/pagination/hive.md) | **LIMIT+ORDER BY 标准，无 OFFSET 支持**——分页需用 ROW_NUMBER() 窗口函数模拟。批处理引擎定位下分页是罕见需求。对比 BigQuery（LIMIT/OFFSET 标准但按扫描量计费）和 Snowflake（LIMIT/OFFSET+FETCH FIRST），Hive 的分页能力最为原始。 |
| [行列转换](../query/pivot-unpivot/hive.md) | **LATERAL VIEW EXPLODE 是 Hive 的标志性语法——将数组展开为行**。`LATERAL VIEW explode(tags) t AS tag` 定义了大数据 SQL 处理嵌套数据的基本范式。行转列（PIVOT）无原生支持，需 CASE+GROUP BY。对比 BigQuery/Snowflake 的原生 PIVOT 和 Spark 的 stack() 函数，Hive 只有列转行（EXPLODE）而无行转列语法。 |
| [集合操作](../query/set-operations/hive.md) | **UNION ALL 长期支持，UNION DISTINCT/INTERSECT/EXCEPT 2.0+ 才引入**——早期 Hive 只支持 UNION ALL，缺乏完整集合操作是重要短板。对比 PG（长期完整支持所有集合操作）和 BigQuery（完整支持 ALL/DISTINCT 变体），Hive 的集合操作在 2.0 后才追上标准。 |
| [子查询](../query/subquery/hive.md) | **IN/EXISTS 子查询 0.13+ 引入，关联子查询支持有限**——早期 Hive 不支持子查询是最大的 SQL 兼容性缺陷。0.13+ 通过 Stinger Initiative 增强了子查询支持。对比 PG/MySQL 8.0 的完整子查询优化和 BigQuery 的自动子查询转 JOIN，Hive 的子查询优化仍较初级。 |
| [窗口函数](../query/window-functions/hive.md) | **完整窗口函数支持(0.11+)——Hive 是大数据 SQL 引擎中窗口函数的先驱**。ROW_NUMBER/RANK/LAG/LEAD/SUM OVER 等在 Hive 0.11 即可用，比 MySQL 8.0（2018 年）早了数年。无 QUALIFY 子句（需子查询包装）。对比 BigQuery/Snowflake 的 QUALIFY 和 ClickHouse（21.1+ 才支持），Hive 的窗口函数虽然引入早但缺乏现代扩展。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/hive.md) | **无 generate_series，需 LATERAL VIEW POSEXPLODE 或预建数字表**——常见方案是创建辅助日期维表 LEFT JOIN 填充缺失日期。对比 BigQuery 的 GENERATE_DATE_ARRAY+UNNEST（一行搞定）和 Spark 的 sequence()+explode()（2.4+），Hive 的日期序列生成最为繁琐。 |
| [去重](../scenarios/deduplication/hive.md) | **ROW_NUMBER+分区窗口函数去重——标准模式但在 MapReduce 上执行慢**。Tez/LLAP 执行引擎大幅改善了去重查询的性能。对比 BigQuery/Snowflake 的 QUALIFY（无需子查询包装）和 ClickHouse 的 ReplacingMergeTree（存储层自动去重），Hive 的去重写法冗长且依赖执行引擎选择。 |
| [区间检测](../scenarios/gap-detection/hive.md) | **LAG/LEAD 窗口函数检测连续性——标准方案，无独有优化**。对比 ClickHouse 的 WITH FILL（自动填充缺失行独有语法）和 PG 的 generate_series+LEFT JOIN（更优雅），Hive 用通用窗口函数实现。 |
| [层级查询](../scenarios/hierarchical-query/hive.md) | **递归 CTE 3.1+ 才支持，之前需多次自连接（性能极差）**——3.1 之前处理层级数据是 Hive 的重大短板，通常需要编写 MapReduce/Spark 程序迭代。对比 Oracle 的 CONNECT BY（最早支持层级查询）和 PG 的递归 CTE（长期支持），Hive 引入递归 CTE 最晚。 |
| [JSON 展开](../scenarios/json-flatten/hive.md) | **get_json_object 路径查询（`$.key`），json_tuple 批量提取多字段**——json_tuple 一次提取多个字段比多次 get_json_object 更高效。LATERAL VIEW EXPLODE 展开 JSON 数组（需先解析为 ARRAY）。对比 Snowflake 的 LATERAL FLATTEN（最优雅）和 BigQuery 的 JSON_QUERY_ARRAY+UNNEST，Hive 的 JSON 处理需要更多手动步骤。 |
| [迁移速查](../scenarios/migration-cheatsheet/hive.md) | **HiveQL 类 SQL 但差异大——三大核心概念必须理解**：分区=目录（分区列不在数据文件中）、STORED AS 存储格式选择、ACID 表 vs 非 ACID 表的能力差异。INSERT OVERWRITE 替代 UPDATE/DELETE 的思维转换是最大挑战。对比 BigQuery/Snowflake（标准 SQL 更友好）和 Spark SQL（Hive 兼容但 Delta Lake 推荐），从 RDBMS 迁移到 Hive 的学习成本最高。 |
| [TopN 查询](../scenarios/ranking-top-n/hive.md) | **ROW_NUMBER+窗口函数+LIMIT 标准模式**——无 QUALIFY 子句，必须子查询包装。简单 TopN 可直接 ORDER BY+LIMIT，分组 TopN 需窗口函数。对比 BigQuery/Snowflake 的 QUALIFY（单行表达式）和 ClickHouse 的 LIMIT BY（每组限行独有语法），Hive 的 TopN 写法标准但不够简洁。 |
| [累计求和](../scenarios/running-total/hive.md) | **SUM() OVER(ORDER BY ...) 标准窗口累计(0.11+)——Hive 是大数据窗口函数先驱**。在 MapReduce 上执行窗口累计性能较差，Tez/LLAP 引擎大幅改善。对比 BigQuery（Slot 自动扩展）和 ClickHouse（runningAccumulate 状态函数更高效），Hive 的累计计算在底层引擎升级后才实用。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/hive.md) | **MERGE INTO(ACID 表 2.2+) 或 INSERT OVERWRITE 全量覆盖实现 SCD**——非 ACID 表的 SCD 只能全分区重写（读取旧数据+JOIN 新数据+INSERT OVERWRITE），ETL 脚本复杂。对比 BigQuery 的 MERGE+Time Travel 和 Snowflake 的 MERGE+Streams，Hive 的 SCD 实现在 ACID 表上才够用。 |
| [字符串拆分](../scenarios/string-split-to-rows/hive.md) | **SPLIT+LATERAL VIEW EXPLODE 是 Hive 定义的标志性写法**——`LATERAL VIEW explode(split(str, ',')) t AS val` 被 Spark/MaxCompute 完全继承。对比 BigQuery 的 SPLIT+UNNEST（更简洁）和 Snowflake 的 SPLIT_TO_TABLE（一步到位），Hive 的写法更冗长但语义最清晰，成为大数据 SQL 的事实标准。 |
| [窗口分析](../scenarios/window-analytics/hive.md) | **完整窗口函数(0.11+)——Hive 在大数据生态中率先支持窗口分析**。移动平均、同环比、占比计算均可实现。无 QUALIFY 子句、无 WINDOW 命名子句。对比 BigQuery/Snowflake（QUALIFY+WINDOW 命名子句最强）和 MySQL 8.0（窗口函数引入最晚），Hive 的窗口函数虽然先驱但功能未再演进。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/hive.md) | **ARRAY/MAP/STRUCT 原生支持——定义了大数据 SQL 的复合类型标准**。LATERAL VIEW EXPLODE 展开 ARRAY/MAP 为行，是 Hive 处理嵌套数据的基本范式。对比 BigQuery 的 STRUCT/ARRAY 一等公民（CROSS JOIN UNNEST）和 Snowflake 的 VARIANT（半结构化），Hive 的复合类型设计被整个大数据生态（Spark/MaxCompute/Flink）继承。 |
| [日期时间](../types/datetime/hive.md) | **仅 DATE/TIMESTAMP 两种类型，无 TIME 类型，无时区支持**——TIMESTAMP 始终按 UTC 存储，无时区转换能力。这是 Hive 类型系统的重要缺陷。对比 BigQuery 的四种时间类型（DATE/TIME/DATETIME/TIMESTAMP）和 Snowflake 的三种 TIMESTAMP（NTZ/LTZ/TZ），Hive 的日期类型最为简陋。 |
| [JSON](../types/json/hive.md) | **无 JSON 原生类型——通过 get_json_object/json_tuple 函数查询 STRING 列中的 JSON**。json_tuple 一次提取多字段比逐个 get_json_object 更高效。对比 PG 的 JSONB+GIN 索引（功能最强）和 Snowflake 的 VARIANT（原生存储），Hive 将 JSON 视为纯文本处理，每次查询都需要解析。 |
| [数值类型](../types/numeric/hive.md) | **TINYINT-BIGINT/FLOAT/DOUBLE/DECIMAL 标准完整**——DECIMAL 默认精度 DECIMAL(10,0)，最大 DECIMAL(38,18)。与标准 SQL 类型命名一致。对比 BigQuery 的 INT64 单一整数类型（极简）和 ClickHouse 的 Int8-256/UInt8-256（最丰富含无符号），Hive 的数值类型是大数据引擎的基准。 |
| [字符串类型](../types/string/hive.md) | **STRING 无长度限制是核心类型，VARCHAR(n)/CHAR(n) 0.12+ 引入但较少使用**——STRING 的设计理念是"存储什么就是什么"（Schema-on-Read），不做长度校验。对比 PG 的 VARCHAR(n)/TEXT 严格区分和 BigQuery 的 STRING（无长度限制极简设计），Hive 的 STRING 设计在大数据场景中被证明是务实选择，被 Spark/MaxCompute 完全继承。 |
