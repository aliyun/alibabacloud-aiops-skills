# Flink SQL

**分类**: 流批一体计算引擎
**文件数**: 51 个 SQL 文件
**总行数**: 5042 行

> **关键人物**：[Stephan Ewen](../docs/people/flink-creators.md)（TU Berlin → Ververica）

## 概述与定位

Flink SQL 是 Apache Flink 流批一体计算引擎的 SQL 层，是当前**实时流计算领域最成熟的 SQL 引擎**。与 Spark SQL 以批处理为核心再扩展到流不同，Flink 从设计之初就以流处理为第一优先级（Stream-first），批处理被视为流处理的特例（有界流）。

Flink SQL 的核心价值在于：让用户用标准 SQL 编写实时数据管道，无需学习底层的 DataStream API。一条 `INSERT INTO sink SELECT ... FROM source` 语句就能启动一个持续运行的流处理作业。这极大降低了实时计算的门槛，使得 SQL 分析师也能构建实时数据管道。

## 历史与演进

| 时间 | 里程碑 |
|------|--------|
| 2010 | 柏林工业大学（TU Berlin）启动 Stratosphere 研究项目 |
| 2014 | 进入 Apache 孵化器，更名为 Flink（德语"敏捷"） |
| 2016 | 阿里巴巴 fork 出 Blink 分支，在内部大规模部署用于双十一实时大屏 |
| 2019 | Flink 1.9：合并 Blink 回主线，Table API / SQL 大幅增强 |
| 2021 | Flink 1.13：引入窗口 TVF（Table-Valued Function），统一窗口语法 |
| 2023 | Flink 1.18+：持续增强批模式、Materialized Table、流式 Lakehouse 集成 |

## 核心设计思路

- **流优先（Stream-first）**：Flink 的执行模型基于持续运行的算子图（DAG），数据以事件的形式在算子间流动。批处理只是将数据源标记为"有界"的流处理。这一设计使得 Flink SQL 在表达流式语义时非常自然，但也导致一些批处理场景下的功能和性能不如 Spark SQL。
- **事件时间 + Watermark**：Flink 区分事件时间（Event Time，数据自带的时间戳）和处理时间（Processing Time，系统当前时间）。Watermark 是 Flink 处理乱序数据的核心机制——它声明"不会再有早于此时间戳的数据到达"，从而触发窗口计算。这一设计使 Flink 能正确处理延迟到达的数据。
- **Connector 架构**：Flink SQL 通过 `WITH (...)` 子句在 DDL 中声明数据源和目标的连接参数（如 Kafka topic、JDBC URL）。Connector 是 Flink SQL 的"输入输出接口"，支持 Kafka、MySQL CDC、HBase、Elasticsearch、FileSystem 等数十种外部系统。
- **时间窗口 TVF**：Flink 1.13+ 引入的窗口表值函数（`TUMBLE(TABLE t, DESCRIPTOR(ts), INTERVAL '1' HOUR)`），替代了旧的 GROUP BY TUMBLE() 语法，使窗口成为 FROM 子句中的一等公民，支持窗口 JOIN、窗口 TopN 等复合操作。

## 独特特色

- **WATERMARK 定义**：在 DDL 中直接声明水印策略，如 `WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND`。这是 Flink SQL 独有的语法，将流式语义嵌入了 SQL DDL。
- **PROCTIME()**：虚拟列函数，声明处理时间属性。`proc_time AS PROCTIME()` 为表添加一个总是返回当前系统时间的虚拟列，用于处理时间窗口。
- **窗口 TVF 家族**：TUMBLE（滚动窗口）、HOP（滑动窗口）、SESSION（会话窗口）、CUMULATE（累积窗口）。四种窗口覆盖了绝大多数实时聚合场景。CUMULATE 是 Flink 独创——在一个大窗口内按步长逐步扩展，适合"每分钟更新的小时累计"场景。
- **Temporal Join（时态 Join）**：`FOR SYSTEM_TIME AS OF` 语法实现的版本化 Join，将流数据与维表的历史版本关联。例如将订单流与汇率表的历史版本 Join，获取下单时刻的汇率。这是流处理独有的语义需求。
- **Lookup Join**：流表与外部维表（如 MySQL、HBase）的点查 Join。Flink 运行时对每条流数据发起维表查询，支持缓存和异步 I/O 优化。这一模式在实时数仓中极为常见。
- **Interval Join**：基于时间区间的流流 Join，如 `ON a.ts BETWEEN b.ts - INTERVAL '5' MINUTE AND b.ts + INTERVAL '5' MINUTE`。限制 Join 的时间范围以控制状态大小。
- **MATCH_RECOGNIZE**：SQL 标准中的复杂事件处理（CEP）语法，用正则表达式匹配事件序列。例如检测"连续三次登录失败后成功"的模式。Flink 是少数完整实现此语法的引擎之一。
- **Changelog 语义**：Flink SQL 内部用四种消息类型编码数据变更——INSERT、UPDATE_BEFORE、UPDATE_AFTER、DELETE。这使得 Flink 可以在流上表达完整的关系代数操作（包括 GROUP BY 聚合的更新），而不仅仅是追加。这一设计是 Flink SQL 区别于大多数流引擎的关键。
- **Connector WITH 子句**：`CREATE TABLE t (...) WITH ('connector' = 'kafka', 'topic' = 'orders', ...)`。将外部系统的连接信息内嵌在 DDL 中，使得一条 SQL 就能完整描述一个数据管道的输入输出。
- **Paimon 集成**：Apache Paimon（原 Flink Table Store）是 Flink 原生的数据湖表格式。支持流式写入 + 批量读取，Changelog 语义天然对齐。`CREATE TABLE ... WITH ('connector'='paimon')`。对标 Delta Lake/Iceberg 但更适合流处理场景。
- **State TTL**：`'table.exec.state.ttl' = '1h'` 控制算子状态的过期时间。防止 JOIN/聚合的状态无限增长导致 OOM。这是 Flink SQL 生产化的关键配置——设短了丢数据，设长了 OOM。
- **Mini-batch 优化**：`'table.exec.mini-batch.enabled' = 'true'` 将单条处理变为微批处理，减少状态访问次数和下游输出频率。对高 QPS 场景性能提升 3-10×。
- **Unaligned Checkpoint**：允许在 backpressure 时仍然完成 checkpoint，避免长时间阻塞导致 checkpoint 超时失败。对生产稳定性至关重要。

## 已知的设计不足与历史包袱

- **无传统 UPDATE/DELETE**：Flink SQL 的 DML 只有 `INSERT INTO`。数据修正需要通过发送 Changelog 消息（UPDATE_BEFORE + UPDATE_AFTER）实现，对普通 SQL 用户来说概念陌生。
- **无索引**：Flink 是计算引擎而非存储引擎，不管理持久化数据，因此索引概念不适用。
- **无存储过程/触发器**：不支持过程式编程，所有逻辑必须用声明式 SQL 或底层 DataStream API 表达。
- **批模式功能弱于 Spark**：虽然 Flink 支持批处理，但生态成熟度（数据源支持、优化器完善度、社区经验）远不及 Spark SQL。大多数用户在批场景中仍选择 Spark。
- **状态管理复杂**：流作业需要维护状态（如窗口聚合的中间结果、Join 的双侧缓存）。状态过大会导致 Checkpoint 超时和恢复缓慢。State TTL 配置不当会导致结果不正确或 OOM。这是 Flink SQL 运维中最常见的痛点。
- **调试困难**：流作业持续运行，错误可能在运行数小时后才显现。日志分散在多个 TaskManager，没有简单的"断点调试"手段。SQL 层的错误信息有时不够明确，需要深入理解底层执行模型才能诊断。

## 兼容生态

Flink SQL 语法主体兼容 ANSI SQL，扩展了流式语义（WATERMARK、窗口 TVF、MATCH_RECOGNIZE）。通过 HiveCatalog 可以集成 Hive Metastore，读写 Hive 表。Flink CDC（Change Data Capture）生态支持从 MySQL、PostgreSQL、MongoDB 等数据库实时捕获变更并以 SQL 方式处理。

## 对引擎开发者的参考价值

- **流式 SQL 语义设计**：如何将"持续变化的数据流"映射到关系代数的"表"概念上？Flink 通过 Dynamic Table（动态表）理论给出了答案——流是表的 Changelog，表是流的快照。这一理论框架是流式 SQL 领域最重要的学术贡献。
- **Watermark 机制**：Watermark 解决了事件时间下的乱序和延迟问题，是流处理引擎的核心机制。Flink 的 Watermark 传播和对齐策略是这一领域的标杆实现。
- **Changelog 编码**：用 INSERT/UPDATE_BEFORE/UPDATE_AFTER/DELETE 四种消息编码关系操作的变更，使得流引擎可以在流上执行 GROUP BY 聚合并持续更新结果。这一设计被 Materialize、RisingWave 等新兴流数据库所借鉴。
- **State TTL**：为流式 Join 和聚合的状态设置过期时间（Time-To-Live），在正确性和资源消耗之间做权衡。这是流引擎独有的设计维度，TTL 配置策略值得深入研究。

---

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/flink.md) | **流表二象性是核心设计——WITH 子句将 Connector 定义嵌入 DDL**。`CREATE TABLE t (..., WATERMARK FOR ts AS ts - INTERVAL '5' SECOND) WITH ('connector'='kafka', 'topic'='orders')` 一条 DDL 同时定义 Schema、时间语义和外部系统连接。WATERMARK 声明是 Flink SQL 独有的流式语义语法。对比 Spark（USING 指定数据源格式）和 BigQuery（固定存储格式），Flink 将外部系统连接信息内嵌 DDL 是最彻底的声明式设计。 |
| [改表](../ddl/alter-table/flink.md) | **ALTER TABLE 主要用于修改 Connector 属性——Schema 变更有限**。可动态修改 WITH 子句中的 Connector 参数（如 Kafka topic、并行度）。列的增删改受限于 Connector 支持。对比 Snowflake（ALTER 瞬时元数据操作）和 Hive（ADD/REPLACE COLUMNS），Flink 的 ALTER 侧重运行时参数调整而非 Schema 演进。 |
| [索引](../ddl/indexes/flink.md) | **无索引概念——Flink 是计算引擎不管理持久化存储**。查询性能由 State Backend（RocksDB/堆内存）和 Connector 的底层存储决定。对比 BigQuery（无索引但有分区+聚集）和 ClickHouse（稀疏索引+跳数索引），Flink 作为纯计算引擎无需也无法创建索引。 |
| [约束](../ddl/constraints/flink.md) | **PK 声明 NOT ENFORCED——用于去重/JOIN 优化而非数据完整性**。PK 告诉 Flink 优化器哪些列唯一，使流式去重（ROW_NUMBER=1）和 Upsert Sink 按主键更新成为可能。对比 BigQuery/Snowflake（PK NOT ENFORCED 作优化器提示）和 PG（PK 强制执行），Flink 的 PK 对流处理语义至关重要——决定了 Changelog 的 Update/Delete 键。 |
| [视图](../ddl/views/flink.md) | **TEMPORARY VIEW 用于构建流处理管道——无物化视图**。视图是 SQL 片段的命名引用，多个流处理作业可复用同一视图定义。Materialized Table(实验性)探索流式物化视图。对比 BigQuery（物化视图自动增量刷新）和 ClickHouse（物化视图=INSERT 触发器），Flink 的流处理管道本身就是"持续计算的物化视图"——INSERT INTO sink SELECT ... FROM source 即是。 |
| [序列与自增](../ddl/sequences/flink.md) | **无 SEQUENCE/自增——流处理以事件时间/处理时间驱动而非行号**。流数据的唯一标识通常来自源系统（如 Kafka offset+partition）。对比 BigQuery（GENERATE_UUID）和 Snowflake（AUTOINCREMENT），Flink 的流处理范式下自增 ID 概念不适用。 |
| [数据库/Schema/用户](../ddl/users-databases/flink.md) | **Catalog(Hive/JDBC/Paimon)+Database 二级命名空间**——通过 Catalog 插件接入不同元数据后端。HiveCatalog 最常用，可直接读写 Hive 表。对比 Spark（Catalog.Database.Table 三级）和 BigQuery（Project.Dataset.Table），Flink 的 Catalog 插件化使其可接入任意元数据系统但无内置权限管理。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/flink.md) | **无动态 SQL——通过 SQL Client/Gateway/REST API 提交作业**。作业一旦提交就持续运行，不支持运行时修改 SQL。对比 Snowflake（EXECUTE IMMEDIATE）和 MaxCompute（Script Mode），Flink 的流处理作业是"部署后持续运行"的模式，与传统动态 SQL 的"按需执行"范式根本不同。 |
| [错误处理](../advanced/error-handling/flink.md) | **无过程式错误处理——作业级容错依赖 Checkpoint/Savepoint**。Checkpoint 定期快照 State，作业失败后从最近 Checkpoint 恢复（Exactly-Once 语义）。Savepoint 是手动触发的可移植 Checkpoint。对比 BigQuery（BEGIN...EXCEPTION）和 Snowflake（EXCEPTION 块），Flink 的容错是分布式流处理独有的 Checkpoint 机制——不是 SQL 层的错误处理，而是系统级的故障恢复。 |
| [执行计划](../advanced/explain/flink.md) | **EXPLAIN 展示流处理算子拓扑——可查看 State 大小和并行度**。EXPLAIN 输出包含 Source→Transform→Sink 的算子链、State Backend 配置和并行度设置。对比 Spark（EXPLAIN EXTENDED 四阶段变换）和 BigQuery（Console 执行详情），Flink 的 EXPLAIN 侧重流处理 DAG 的 State 管理和资源分配。 |
| [锁机制](../advanced/locking/flink.md) | **无锁——流处理引擎通过 Checkpoint 保证 Exactly-Once 语义**。Two-Phase Commit(2PC)协议保证端到端一致性：Source 精确消费 + Sink 精确写入。Unaligned Checkpoint 在 backpressure 下仍能完成快照。对比 Snowflake（乐观并发）和 PG（行级悲观锁），Flink 的一致性保证完全基于 Checkpoint 而非锁。 |
| [分区](../advanced/partitioning/flink.md) | **PARTITION BY 用于 FileSystem Sink 的目录分区——非传统查询分区**。`INSERT INTO sink PARTITION(dt) SELECT ...` 将数据按分区列写入不同目录。流处理中的"分区"更多指时间窗口而非存储分区。对比 BigQuery（分区用于查询裁剪省钱）和 Hive（分区=目录核心概念），Flink 的分区仅在 Sink 端（写入）有意义。 |
| [权限](../advanced/permissions/flink.md) | **无内置权限系统——依赖外部 Catalog 和部署平台的安全机制**。HiveCatalog 继承 Hive Ranger 权限，JDBC Catalog 继承数据库权限。对比 Snowflake（RBAC+DAC 最完善）和 BigQuery（GCP IAM），Flink 在权限管理上最弱——纯计算引擎不管理数据访问控制。 |
| [存储过程](../advanced/stored-procedures/flink.md) | **无存储过程——流处理引擎定位下所有逻辑用声明式 SQL 表达**。复杂逻辑需通过底层 DataStream API（Java/Scala/Python）实现。对比 Snowflake（多语言存储过程）和 Oracle（PL/SQL），Flink 将"过程式逻辑"推到编程 API 层。 |
| [临时表](../advanced/temp-tables/flink.md) | **CREATE TEMPORARY TABLE 定义流/批数据源——核心使用模式**。几乎所有 Flink SQL 作业都通过 TEMPORARY TABLE 定义 Source/Sink。对比 BigQuery（_SESSION 临时表）和 Snowflake（TEMPORARY 表会话结束清理），Flink 的 TEMPORARY TABLE 是数据管道的核心组件而非辅助工具。 |
| [事务](../advanced/transactions/flink.md) | **Exactly-Once 语义基于 Two-Phase Commit(2PC)——非传统 ACID 事务**。Flink 保证每条数据恰好处理一次：Source 端通过 Checkpoint 记录消费位点，Sink 端通过 2PC 保证原子写入。对比 Snowflake（ACID 自动提交）和 PG（完整事务隔离级别），Flink 的事务语义是流处理独有的"端到端 Exactly-Once"——概念不同于传统 ACID。 |
| [触发器](../advanced/triggers/flink.md) | **无触发器——流处理本身即事件驱动**。每条数据到达即触发计算，这是流处理的本质——整个系统就是一个"触发器"。对比 ClickHouse（物化视图=INSERT 触发器）和 Snowflake（Streams+Tasks 变更捕获），Flink 的流处理管道天然替代了触发器的事件驱动需求。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/flink.md) | **不支持传统 DELETE——数据修正通过 Retract(撤回)流实现**。Flink 内部用 UPDATE_BEFORE+UPDATE_AFTER 消息对编码变更，DELETE 消息标记行删除。这是 Changelog 语义的核心——流上的"删除"不是修改已有数据，而是发送新的删除消息。对比 BigQuery（DELETE 重写分区）和 ClickHouse（Lightweight Delete 标记删除），Flink 的删除语义最独特——它是流上的消息而非存储上的操作。 |
| [插入](../dml/insert/flink.md) | **INSERT INTO 是唯一的 DML——启动持续运行的流处理作业**。`INSERT INTO sink SELECT ... FROM source` 不是执行一次的语句，而是部署一个持续运行的数据管道。支持 STATEMENT SET 同时启动多条 INSERT（共享 Source 读取）。对比 BigQuery（INSERT 是一次性操作）和 Spark（DataFrame write 一次性写入），Flink 的 INSERT INTO 语义最独特——它是"部署"而非"执行"。 |
| [更新](../dml/update/flink.md) | **不支持传统 UPDATE——通过 Upsert/Retract 流语义替代**。GROUP BY 聚合的结果更新通过 UPDATE_BEFORE(旧值撤回)+UPDATE_AFTER(新值发送)消息对实现。Upsert 模式只发送最新值（需要 PK）。对比 BigQuery/Snowflake（UPDATE 标准）和 ClickHouse（25.7+ 标准 UPDATE），Flink 的更新语义完全基于 Changelog 消息流。 |
| [Upsert](../dml/upsert/flink.md) | **Upsert Sink 按 PK 自动更新——非标准 MERGE 语句**。Sink Connector 声明 `'sink.buffer-flush.max-rows'` 等参数控制 Upsert 行为。PK 声明（NOT ENFORCED）告诉 Sink 按哪些列做 Upsert。对比 BigQuery/Snowflake（MERGE INTO 标准 SQL）和 Doris（Unique 模型 INSERT 即 Upsert），Flink 的 Upsert 是 Connector 级别的配置而非 SQL 语法。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/flink.md) | **窗口 TVF 聚合是 Flink 独有——TUMBLE/HOP/SESSION/CUMULATE 四种时间窗口**。CUMULATE 是 Flink 独创（在大窗口内按步长逐步扩展，如"每分钟更新的小时累计"）。Mini-batch 优化将单条聚合变为微批处理，减少 State 访问和下游输出。对比 BigQuery 的 APPROX_COUNT_DISTINCT 和 ClickHouse 的 -If/-State 组合后缀，Flink 的聚合函数围绕流式窗口设计。 |
| [条件函数](../functions/conditional/flink.md) | **IF/CASE/COALESCE 标准支持**——行为与标准 SQL 一致。对比 BigQuery 的 SAFE_ 前缀（行级安全）和 Snowflake 的 IFF（简洁条件），Flink 的条件函数标准简洁无独有扩展。 |
| [日期函数](../functions/date-functions/flink.md) | **CURRENT_TIMESTAMP/PROCTIME()/ROWTIME 是流处理时间语义的核心**——PROCTIME() 返回处理时间（系统当前时间），event_time 列声明 WATERMARK 后成为 ROWTIME（事件时间）。这两种时间属性决定了窗口计算的触发时机。对比 BigQuery 的 DATE_TRUNC（标准日期函数）和 Snowflake 的 DATEADD，Flink 的时间函数与流式语义深度绑定。 |
| [数学函数](../functions/math-functions/flink.md) | **基础数学函数（ABS/CEIL/FLOOR/ROUND/POWER 等）标准支持**——流处理场景下数学函数使用频率不如聚合和窗口函数。对比 BigQuery 的 SAFE_DIVIDE 和 ClickHouse 的向量化执行极快，Flink 的数学函数标准但无独有扩展。 |
| [字符串函数](../functions/string-functions/flink.md) | **CONCAT/SUBSTR/REGEXP 标准支持——REGEXP_EXTRACT/REGEXP_REPLACE 用于流数据清洗**。流处理中字符串函数常用于实时 ETL 数据清洗和格式转换。对比 BigQuery 的 SPLIT 返回 ARRAY 和 ClickHouse 的 extractAll 批量正则，Flink 的字符串函数标准简洁。 |
| [类型转换](../functions/type-conversion/flink.md) | **CAST/TRY_CAST 标准支持——TRY_CAST 在流处理中尤为重要**。流数据质量不可控，TRY_CAST 避免因一条脏数据导致整个流作业失败（对比 CAST 失败直接报错可能导致作业崩溃）。对比 BigQuery 的 SAFE_CAST 和 Snowflake 的 TRY_CAST，Flink 的 TRY_CAST 在流处理场景中是必需品而非可选项。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/flink.md) | **WITH 标准支持——用于简化复杂流处理管道的 SQL 可读性**。流处理中 CTE 常用于将多步转换拆分为可读的逻辑层。无递归 CTE（流处理场景不适用）。对比 BigQuery（递归 CTE 有迭代限制）和 PG（完整递归 CTE），Flink 的 CTE 是非递归的流处理辅助工具。 |
| [全文搜索](../query/full-text-search/flink.md) | **无全文搜索能力——流处理引擎不管理持久化索引**。LIKE/REGEXP 可用于流数据的模式匹配过滤。对比 BigQuery（SEARCH INDEX 2023+）和 Doris（CLucene 倒排索引），Flink 的文本过滤是逐条处理而非索引加速。 |
| [连接查询](../query/joins/flink.md) | **四种流处理特有 JOIN 类型——Regular/Interval/Temporal/Lookup JOIN**。Interval JOIN 基于时间窗口限制 JOIN 范围（控制 State 大小）。Temporal JOIN(`FOR SYSTEM_TIME AS OF`)关联维表历史版本。Lookup JOIN 运行时点查外部维表（MySQL/HBase）。对比 Spark（Broadcast/Sort-Merge/Shuffle Hash）和 BigQuery（全自动 Broadcast/Shuffle），Flink 的 JOIN 类型为流处理独有设计——State TTL 控制是关键配置。 |
| [分页](../query/pagination/flink.md) | **不适用于流处理——流数据无"页"概念**。批模式下支持 LIMIT 但不支持 OFFSET。对比 BigQuery（LIMIT/OFFSET 标准）和 Snowflake（LIMIT/OFFSET+FETCH FIRST），Flink 的流处理范式下分页不适用。 |
| [行列转换](../query/pivot-unpivot/flink.md) | **无原生 PIVOT/UNPIVOT——CASE+GROUP BY 或 JSON 函数替代**。CROSS JOIN UNNEST(array_col) 支持列转行（ARRAY 展开）。对比 BigQuery/Snowflake 的原生 PIVOT 和 Spark 的 PIVOT(3.4+)，Flink 缺乏行转列语法糖。 |
| [集合操作](../query/set-operations/flink.md) | **UNION ALL 是流合并（多个流合为一个流），INTERSECT/EXCEPT 仅批模式**——流处理中 UNION ALL 是最常用的集合操作（合并多个数据源）。INTERSECT/EXCEPT 需要全量数据才能计算，不适合无界流。对比 BigQuery（完整 ALL/DISTINCT 变体）和 ClickHouse（完整支持），Flink 的集合操作受流处理语义限制。 |
| [子查询](../query/subquery/flink.md) | **IN/EXISTS 子查询支持——流处理下有限制（需管理 State）**。关联子查询在流处理中会产生持续运行的 State，State TTL 配置至关重要。对比 PG（成熟子查询优化）和 Spark（Catalyst 去关联化），Flink 的子查询在流处理中需要特别关注 State 膨胀问题。 |
| [窗口函数](../query/window-functions/flink.md) | **OVER 窗口+TVF 窗口双体系——TVF 窗口(TUMBLE/HOP/SESSION/CUMULATE)是 Flink 独有**。TVF 窗口在 FROM 子句中声明，支持窗口 JOIN、窗口 TopN 等复合操作。CUMULATE 窗口是 Flink 独创——在大窗口内按步长逐步扩展。对比 BigQuery/Snowflake 的 QUALIFY+标准窗口函数和 Spark 的完整窗口函数，Flink 的 TVF 窗口为流处理独有设计。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/flink.md) | **不适用于流处理场景——流数据按时间到达，不存在"缺失日期"**。批模式下可用 VALUES 构造辅助序列。对比 BigQuery 的 GENERATE_DATE_ARRAY+UNNEST 和 ClickHouse 的 WITH FILL，Flink 的流处理范式下日期填充概念不适用。 |
| [去重](../scenarios/deduplication/flink.md) | **ROW_NUMBER()=1 是 Flink 流式去重的标准模式——State 自动管理已见主键**。`SELECT * FROM (SELECT *, ROW_NUMBER() OVER(PARTITION BY id ORDER BY proc_time) AS rn FROM t) WHERE rn = 1` 持续去重流数据。State TTL 控制去重窗口大小。对比 BigQuery/Snowflake 的 QUALIFY（批处理去重最简）和 ClickHouse 的 ReplacingMergeTree（存储层去重），Flink 的流式去重是唯一能处理无界数据流的方案。 |
| [区间检测](../scenarios/gap-detection/flink.md) | **Interval JOIN 检测时间区间——流处理独有的时间窗口匹配**。两个流之间的时间区间 JOIN 可检测事件间隔异常。MATCH_RECOGNIZE 可用正则表达式检测事件序列模式。对比 ClickHouse 的 WITH FILL 和 PG 的 generate_series+LEFT JOIN，Flink 的区间检测基于流式事件时间语义。 |
| [层级查询](../scenarios/hierarchical-query/flink.md) | **不适用于流处理场景——递归 CTE 需要全量数据不适合无界流**。层级数据处理需在批模式下或通过底层 DataStream API 实现。对比 PG（长期支持递归 CTE）和 Spark（3.4+ 递归 CTE），Flink 的流处理范式下层级查询概念不适用。 |
| [JSON 展开](../scenarios/json-flatten/flink.md) | **JSON_VALUE/JSON_QUERY 路径查询+CROSS JOIN UNNEST 展开 JSON 数组**——流数据（如 Kafka JSON 消息）的 JSON 解析是最高频操作。`JSON_VALUE(payload, '$.user.name')` 提取字段，`CROSS JOIN UNNEST(JSON_QUERY(payload, '$.items' RETURNING ARRAY<ROW<...>>))` 展开数组。对比 Snowflake 的 LATERAL FLATTEN（最优雅）和 BigQuery 的 JSON_QUERY_ARRAY+UNNEST，Flink 的 JSON 处理针对流数据实时解析场景优化。 |
| [迁移速查](../scenarios/migration-cheatsheet/flink.md) | **流批一体 SQL 语法，但三大核心差异必须理解**——WITH Connector 定义（DDL 内嵌连接信息）、时间语义（WATERMARK/PROCTIME 流处理独有）、Changelog 语义（INSERT/UPDATE_BEFORE/UPDATE_AFTER/DELETE 四种消息）。从批处理 SQL 迁移到 Flink 的最大挑战是理解"持续运行的查询"和"State 管理"。对比 Spark SQL（批处理为主扩展到流）和 BigQuery（纯批处理），Flink 的流式 SQL 范式需要根本性的思维转换。 |
| [TopN 查询](../scenarios/ranking-top-n/flink.md) | **ROW_NUMBER 流式 TopN——State 自动维护实时排名**。`WHERE rn <= N` 持续输出每个分组的 TopN 结果，排名变化时自动发送 Retract+更新消息。这是真正的"实时 TopN 排行榜"。对比 BigQuery/Snowflake 的 QUALIFY（批处理 TopN）和 ClickHouse 的 LIMIT BY（每组限行），Flink 是唯一能持续维护实时 TopN 排名的引擎。 |
| [累计求和](../scenarios/running-total/flink.md) | **CUMULATE 窗口或 SUM() OVER(ROWS UNBOUNDED PRECEDING) 实现流式累计**——CUMULATE 窗口是 Flink 独创：在一个大窗口内按步长逐步扩展（如"每分钟更新的小时累计"）。SUM() OVER 用于无界累计。对比 BigQuery（SUM() OVER 标准批处理）和 ClickHouse（runningAccumulate），Flink 的 CUMULATE 窗口是流式累计的最优方案。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/flink.md) | **Temporal JOIN(`FOR SYSTEM_TIME AS OF`)是流处理独有的维表关联模式**——将流数据与维表的"当时版本"关联（如下单时刻的汇率）。Lookup JOIN 实时查询外部维表（MySQL/HBase/Redis）。Paimon 表支持 Changelog 语义的流式维表。对比 BigQuery/Snowflake 的 MERGE INTO（批处理 SCD）和 Spark+Delta 的 MERGE+CDF，Flink 的 Temporal JOIN 是实时 SCD 的唯一原生方案。 |
| [字符串拆分](../scenarios/string-split-to-rows/flink.md) | **UNNEST+SPLIT 展开字符串为行——标准 SQL UNNEST 语法**。`SELECT val FROM t, UNNEST(STRING_TO_ARRAY(str, ',')) AS val` 或 `CROSS JOIN UNNEST(...)` 展开。对比 Snowflake 的 SPLIT_TO_TABLE（最简）和 Hive 的 SPLIT+LATERAL VIEW EXPLODE（最冗长），Flink 的 UNNEST 方案接近标准 SQL。 |
| [窗口分析](../scenarios/window-analytics/flink.md) | **TVF 窗口(TUMBLE/HOP/SESSION/CUMULATE) 是流处理独有的窗口分析体系**。传统 OVER 窗口也支持但在流处理中需管理 State。TVF 窗口支持窗口 JOIN、窗口 TopN、窗口去重等复合操作。对比 BigQuery/Snowflake（QUALIFY+WINDOW 命名子句批处理最强）和 Spark（完整窗口函数批处理），Flink 的 TVF 窗口是流式分析的独有范式。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/flink.md) | **ARRAY/MAP/ROW 原生支持——ROW 类型替代 STRUCT（Flink 命名差异）**。UNNEST 展开 ARRAY/MAP 为行。ROW 类型可嵌套使用（`ROW<name STRING, address ROW<city STRING>>`）。对比 BigQuery 的 STRUCT/ARRAY（命名为 STRUCT）和 Hive 的 STRUCT（Hive 命名），Flink 用 ROW 替代 STRUCT 是 SQL 标准的选择。 |
| [日期时间](../types/datetime/flink.md) | **TIMESTAMP/TIMESTAMP_LTZ 两种类型——与流处理时间语义深度绑定**。TIMESTAMP(无时区)用于事件时间字段（声明 WATERMARK 后成为 ROWTIME），TIMESTAMP_LTZ(本地时区)用于处理时间。对比 BigQuery 的四种时间类型和 Snowflake 的三种 TIMESTAMP，Flink 的两种 TIMESTAMP 是为流处理时间语义设计的最简类型系统。 |
| [JSON](../types/json/flink.md) | **JSON_VALUE/JSON_QUERY 标准路径查询——无 JSON 索引（纯计算引擎）**。流数据中 JSON 解析是最高频操作（Kafka 消息通常为 JSON 格式）。对比 PG 的 JSONB+GIN 索引和 Snowflake 的 VARIANT（原生存储），Flink 的 JSON 处理是逐条实时解析而非索引加速。 |
| [数值类型](../types/numeric/flink.md) | **TINYINT-BIGINT/FLOAT/DOUBLE/DECIMAL 标准 SQL 类型系统**——与 Hive/Spark 的类型系统高度兼容。DECIMAL 最大精度 38 位。对比 BigQuery 的 INT64（单一整数极简）和 ClickHouse 的 Int8-256（最细粒度），Flink 的数值类型是标准 SQL 完整集。 |
| [字符串类型](../types/string/flink.md) | **STRING/VARCHAR/CHAR 标准 SQL 类型——STRING 是 VARCHAR(MAX) 的简写**。UTF-8 编码。对比 BigQuery 的 STRING（无长度极简）和 PG 的 VARCHAR(n)/TEXT，Flink 的字符串类型设计标准简洁，STRING 是最常用类型。 |
