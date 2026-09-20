# ClickHouse

**分类**: 列式分析数据库
**文件数**: 51 个 SQL 文件
**总行数**: 6690 行

> **关键人物**：[Alexey Milovidov](../docs/people/alexey-milovidov.md)（ClickHouse 创始人 & CTO）

## 概述与定位

ClickHouse 是一款开源的列式 OLAP 数据库，以**极致的查询性能**闻名。它的设计目标是在商用硬件上实现亿级行数据的亚秒级聚合查询。ClickHouse 不试图成为通用数据库，而是专注于分析场景——大批量写入、低频更新、高速聚合查询。

与 BigQuery/Snowflake 等无服务器云数仓不同，ClickHouse 是一个**可自托管的引擎**，用户需要自行管理集群（虽然 ClickHouse Cloud 提供了托管方案）。这意味着更大的控制权，也意味着更高的运维成本。ClickHouse 在日志分析、用户行为分析、实时监控等场景中被广泛采用。

## 历史与演进

| 时间 | 里程碑 |
|------|--------|
| 2008 | Yandex 为 Metrica（网站分析服务，类似 Google Analytics）启动内部项目 |
| 2016 | 在 Apache 2.0 许可下开源，迅速获得社区关注 |
| 2019 | Yandex 分拆 ClickHouse 团队，后成立 ClickHouse Inc. |
| 2021 | ClickHouse Inc. 获得融资，推出 ClickHouse Cloud 托管服务 |
| 2024 | 持续增强：SharedMergeTree（云原生存储引擎）、实验性事务支持、JSON 类型改进 |

## 核心设计思路

- **INSERT-only 哲学**：ClickHouse 的核心假设是数据主要通过大批量 INSERT 写入，极少更新或删除。传统的 UPDATE/DELETE 在早期版本中是异步 Mutation（后台重写数据分片），而非原地修改。这一哲学使得写入路径极为简单高效，但 OLTP 式的行级修改代价高昂。
- **MergeTree 引擎家族**：MergeTree 是 ClickHouse 的基石存储引擎。数据写入时先进入内存缓冲区，然后 flush 为不可变的有序 Part（数据分片），后台 Merge 线程持续将小 Part 合并为大 Part。这一设计类似 LSM-Tree，但针对列式分析做了大量优化。
- **列式存储 + 向量化执行**：每列独立存储和压缩，查询时只读取必要列。执行引擎采用向量化（Vectorized）模式，一次处理一批行（Block）而非逐行处理，最大化 CPU Cache 和 SIMD 指令的利用率。
- **稀疏索引**：ClickHouse 不使用 B-Tree 索引，而是每隔 N 行（默认 8192）记录一个 ORDER BY 列的索引标记（Mark）。查询时通过二分查找快速定位到包含目标数据的 Granule（颗粒），跳过无关数据。这比 B-Tree 更节省空间，但只对 ORDER BY 前缀列有效。

## 独特特色

- **MergeTree 引擎家族**：不同变体解决不同问题——`ReplacingMergeTree` 在 Merge 时按主键去重；`SummingMergeTree` 自动聚合数值列；`AggregatingMergeTree` 保存预聚合中间状态；`CollapsingMergeTree` 通过 +1/-1 标记实现逻辑删除。引擎选择是 ClickHouse 数据建模的核心决策。
- **ORDER BY = 物理布局**：建表时的 `ORDER BY (col1, col2)` 不仅定义排序，更决定了数据的物理存储顺序和稀疏索引结构。这与 RDBMS 中 ORDER BY 仅影响查询结果截然不同。选择正确的 ORDER BY 是 ClickHouse 性能优化的关键。
- **Nullable 默认关闭**：列默认不允许 NULL，`Nullable(T)` 需要显式声明。非 Nullable 列占用更少存储且查询更快，因为不需要额外的 null bitmap。这是性能优先的设计取舍。
- **LowCardinality 类型**：`LowCardinality(String)` 自动对低基数字符串（如国家、状态码）进行字典编码，通常可将存储和查询性能提升 2-10 倍。这是 ClickHouse 独有的类型级优化。
- **组合函数后缀**：聚合函数支持 `-If`（条件聚合）、`-State`（保存中间状态）、`-Merge`（合并中间状态）等后缀组合。例如 `sumIf(amount, status = 'paid')` 或 `quantileState(0.99)(latency)`。这种组合式设计使得复杂聚合无需子查询。
- **FINAL 关键字**：`SELECT ... FROM t FINAL` 在查询时强制应用 Merge 逻辑（如 ReplacingMergeTree 去重），保证看到最终一致的数据。代价是查询变慢。
- **物化视图 = INSERT 触发器**：ClickHouse 的物化视图在 INSERT 时自动触发，将增量数据写入目标表。它本质上是一个"INSERT 触发器 + 目标表"的组合，用于实时预聚合。
- **WITH FILL / LIMIT BY**：`ORDER BY date WITH FILL FROM ... TO ...` 自动填充缺失的日期行；`LIMIT N BY col` 每组最多返回 N 行——这些是 ClickHouse 独有的 SQL 扩展，简化了常见分析查询。
- **Projections（21.6+）**：预计算的物化聚合——在表定义中声明 `PROJECTION p (SELECT a, SUM(b) GROUP BY a)`，写入时自动维护。查询时优化器自动选择 Projection 或原始数据。对比 Oracle 物化视图 Query Rewrite、StarRocks Rollup。
- **标准 SQL UPDATE（25.7+）**：支持标准 `UPDATE t SET col=val WHERE ...` 语法，基于 lightweight patch-part 机制，比传统 mutation 快数千倍。这是 ClickHouse 历史上最大的 DML 改进。
- **SharedMergeTree（Cloud）**：存算分离版的 MergeTree，数据持久化在对象存储（S3），计算节点无状态。ClickHouse Cloud 的核心架构，对标 Snowflake 的三层分离。
- **向量化执行引擎**：列批处理（column-at-a-time），利用 SIMD 指令（SSE4.2/AVX2/AVX-512）加速计算。这是 ClickHouse 查询性能的核心技术基础。

## 已知的设计不足与历史包袱

- **无传统事务**：ClickHouse 长期没有 ACID 事务支持。直到 25.x 版本引入实验性事务，但仍不适合 OLTP 场景。多表原子写入（"要么全成功要么全失败"）在生产中仍需谨慎。
- **UPDATE/DELETE 的历史包袱**：早期 UPDATE/DELETE 是异步 Mutation，提交后后台执行，不保证即时可见。25.7 版本引入了"轻量级删除"（Lightweight Delete）和标准 UPDATE 语法，但底层仍是重写 Part，不是原地修改。
- **无 JOIN 索引**：ClickHouse 的 JOIN 性能有限，大表 JOIN 大表容易 OOM。推荐做法是将维表加载到内存（Dictionary）或预 JOIN 后写入宽表。
- **最终一致性**：在 ReplacingMergeTree 等引擎中，Merge 完成前可能看到重复数据。必须使用 FINAL 或手动去重来保证查询正确性，这增加了应用层复杂度。
- **无存储过程/触发器**：不支持过程式编程，复杂逻辑必须在应用层或调度系统中实现。

## 兼容生态

ClickHouse 有自己的 SQL 方言，语法与 MySQL/PostgreSQL 有较多差异。但提供了 MySQL/PostgreSQL 兼容协议端口，支持 JDBC/ODBC 连接。内置多种外部表引擎（MySQL、PostgreSQL、S3、HDFS、Kafka）可直接查询外部数据源。

## 对引擎开发者的参考价值

- **稀疏索引设计**：每 8192 行一个 Mark 的稀疏索引，在存储开销和查询加速之间取得了极佳平衡。这一设计证明了 OLAP 场景下不需要 B-Tree 级别的精确索引。
- **Codec 压缩链**：支持多种编解码器的链式组合（如 `CODEC(Delta, ZSTD)`），先做 Delta 编码再压缩，针对时序数据可获得极高压缩比。这种可组合压缩架构值得借鉴。
- **向量化执行引擎**：Block-based 批处理 + SIMD 指令利用，是现代分析引擎的标准实践。ClickHouse 的实现是这一领域的重要参考。
- **MergeTree 合并策略**：不同 MergeTree 变体在 Merge 时执行不同语义（去重/求和/聚合/折叠），将业务逻辑嵌入存储层。这种"存储引擎即业务逻辑"的设计思路独具特色。

---

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/clickhouse.md) | **MergeTree 引擎家族是建表的核心决策**——ReplacingMergeTree(按主键去重)、SummingMergeTree(自动求和)、AggregatingMergeTree(预聚合)等变体将业务逻辑嵌入存储层。`ORDER BY` 不仅定义排序，更决定物理存储布局和稀疏索引结构。Nullable 默认关闭（性能优先）。对比 BigQuery/Snowflake（用户无需选择存储引擎）和 Doris（四种数据模型类似思路），ClickHouse 将引擎选择权完全交给用户。 |
| [改表](../ddl/alter-table/clickhouse.md) | **ADD/DROP COLUMN 轻量级（纯元数据），MODIFY COLUMN TYPE 触发异步 Mutation 重写**——Mutation 在后台重写所有 Part，期间旧数据仍可查询。`ALTER TABLE ... UPDATE/DELETE` 也是 Mutation 操作（25.7 前）。对比 Snowflake（ALTER 纯元数据瞬时完成）和 Hive（ADD/REPLACE COLUMNS），ClickHouse 的 Mutation 机制使重型变更不阻塞查询但完成时间不确定。 |
| [索引](../ddl/indexes/clickhouse.md) | **稀疏索引(每 8192 行一个 Mark)替代 B-Tree——空间开销极小但只对 ORDER BY 前缀列有效**。跳数索引(Data Skipping Index)：minmax/set/bloom_filter/tokenbf_v1 等辅助过滤非排序列。Projections(21.6+)预计算物化聚合，查询时优化器自动选择。对比 BigQuery（无索引仅分区+聚集）和 Snowflake（自动微分区 Pruning），ClickHouse 的索引体系在 OLAP 引擎中最丰富。 |
| [约束](../ddl/constraints/clickhouse.md) | **ASSUME 约束仅作优化器提示不实际校验——比 NOT ENFORCED 更极端**。`ASSUME` 告诉优化器"相信这个条件恒成立"用于裁剪。CHECK 约束有限支持（仅部分引擎）。无 PK/FK/UNIQUE 约束。对比 BigQuery/Snowflake（PK/FK 声明 NOT ENFORCED 至少有元数据意义）和 PG（全部强制执行），ClickHouse 的约束系统最简陋——OLAP 引擎定位下约束不是优先项。 |
| [视图](../ddl/views/clickhouse.md) | **物化视图=INSERT 触发器+目标表——实时预聚合的利器**。INSERT 新数据时自动触发物化视图计算并写入目标表（增量处理，不重算全量）。目标表可以是 AggregatingMergeTree（保存中间聚合状态）。对比 BigQuery（物化视图自动增量刷新+查询改写）和 Oracle（Query Rewrite 功能最强），ClickHouse 的物化视图本质是"INSERT 触发器"，设计哲学截然不同。 |
| [序列与自增](../ddl/sequences/clickhouse.md) | **无 SEQUENCE/AUTO_INCREMENT——分布式写入环境下全局递增序列不实际**。推荐 generateUUIDv4() 生成唯一标识，或使用 rowNumberInBlock()/rowNumberInAllBlocks() 生成块内行号。对比 BigQuery（GENERATE_UUID）和 Snowflake（AUTOINCREMENT 不保证连续），ClickHouse 完全放弃了自增语义。 |
| [数据库/Schema/用户](../ddl/users-databases/clickhouse.md) | **RBAC 权限模型(20.x+) + ON CLUSTER 分布式 DDL**——`CREATE TABLE ... ON CLUSTER c` 在集群所有节点上同时创建表。GRANT/REVOKE 标准 SQL 语法。Row Policy 支持行级安全过滤。对比 Snowflake（RBAC 最完善+FUTURE GRANTS）和 BigQuery（完全基于 GCP IAM），ClickHouse 的 RBAC 简洁实用但缺乏细粒度列级安全。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/clickhouse.md) | **无存储过程/动态 SQL——所有过程化逻辑必须在应用层实现**。ClickHouse 定位是纯分析查询引擎，不提供任何过程式编程能力。对比 Snowflake（多语言存储过程最强）和 MaxCompute（Script Mode），ClickHouse 在过程式能力方面与 Hive 并列最弱。 |
| [错误处理](../advanced/error-handling/clickhouse.md) | **无过程式错误处理——查询级别错误直接返回给客户端**。toTypeOrNull/toTypeOrZero 系列函数提供行级安全转换（失败返回 NULL 或 0）。对比 BigQuery 的 SAFE_ 前缀和 Snowflake 的 EXCEPTION 块，ClickHouse 的错误安全函数用后缀命名（toInt32OrNull）而非前缀，但覆盖范围相似。 |
| [执行计划](../advanced/explain/clickhouse.md) | **EXPLAIN PIPELINE/AST/SYNTAX 三种模式——PIPELINE 展示向量化执行管道最独特**。EXPLAIN PIPELINE 展示实际的算子管道和线程并行度。EXPLAIN AST 展示语法树。EXPLAIN SYNTAX 展示优化后的 SQL 重写。对比 Spark（EXPLAIN EXTENDED 四阶段变换）和 BigQuery（无 EXPLAIN），ClickHouse 的 EXPLAIN PIPELINE 对理解向量化执行最有价值。 |
| [锁机制](../advanced/locking/clickhouse.md) | **无行级锁——Part 级别原子写入，最终一致性**。INSERT 创建新 Part（原子操作），后台 Merge 线程合并 Part。ReplacingMergeTree 在 Merge 完成前可能看到重复数据——必须用 FINAL 或手动去重保证正确性。对比 Snowflake（乐观并发自动管理）和 PG（行级悲观锁 MVCC），ClickHouse 的最终一致性模型需要应用层适应。 |
| [分区](../advanced/partitioning/clickhouse.md) | **PARTITION BY 按月/日/表达式分区 + TTL 自动过期删除**——`TTL timestamp + INTERVAL 90 DAY` 在表级或列级声明数据过期策略，过期数据自动删除。Part 管理透明：`SYSTEM OPTIMIZE TABLE` 手动触发合并。对比 BigQuery（partition_expiration_days 类似 TTL）和 Hive（无内置 TTL 需外部调度），ClickHouse 的 TTL 是与 MaxCompute LIFECYCLE 并列的最优雅数据过期方案。 |
| [权限](../advanced/permissions/clickhouse.md) | **RBAC(20.x+) 标准 GRANT/REVOKE + Row Policy 行级过滤**——Row Policy `CREATE ROW POLICY ... USING condition` 透明地为不同用户过滤不同行。对比 BigQuery（Row Access Policy）和 Snowflake（Row Access Policy+Column Security），ClickHouse 的 Row Policy 功能等价但配置更简洁。 |
| [存储过程](../advanced/stored-procedures/clickhouse.md) | **无存储过程/触发器——逻辑在应用层或 Airflow/Dagster 等调度系统实现**。ClickHouse 的哲学是"做好一件事"——极致查询性能，过程式逻辑不在 scope 内。对比 Snowflake（多语言存储过程）和 Oracle（PL/SQL 最强大），ClickHouse 完全没有过程式编程能力。 |
| [临时表](../advanced/temp-tables/clickhouse.md) | **无传统临时表——用 Memory 引擎表或 CTE 替代**。`CREATE TABLE tmp ENGINE = Memory AS SELECT ...` 创建内存表（会话结束后不自动清理）。CTE(`WITH ... AS`)是更常用的临时结果集方案。对比 BigQuery（_SESSION 临时表）和 Snowflake（TEMPORARY 表会话结束清理），ClickHouse 缺乏会话级自动清理的临时表。 |
| [事务](../advanced/transactions/clickhouse.md) | **无传统 ACID 事务——最终一致性是默认模型**。每次 INSERT 是原子的（整个 Part 要么成功要么失败），但多表写入无原子性保证。25.x 引入实验性事务支持（BEGIN/COMMIT/ROLLBACK），但仍不适合 OLTP。对比 Snowflake（ACID 自动提交）和 PG（完整事务隔离级别），ClickHouse 在事务支持上最弱——这是 OLAP 引擎的有意取舍。 |
| [触发器](../advanced/triggers/clickhouse.md) | **无传统触发器——物化视图充当 INSERT 触发器角色**。物化视图在 INSERT 时自动触发，将增量数据写入目标表。这是 ClickHouse 独有的设计：将触发器语义融入物化视图。对比 Snowflake（Streams+Tasks 变更捕获）和 PG（BEFORE/AFTER 触发器完整），ClickHouse 用物化视图统一了触发器和预聚合两种需求。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/clickhouse.md) | **Lightweight Delete(22.8+) 标记删除——旧版 `ALTER TABLE ... DELETE` 是异步 Mutation**。Lightweight Delete 通过 mask 位标记行为已删除，查询时过滤；后台 Mutation 稍后物理删除。25.7+ 标准 DELETE 语法基于 lightweight patch-part。对比 BigQuery（DELETE 重写整个分区）和 Snowflake（DELETE 重写微分区+Time Travel 恢复），ClickHouse 的删除从异步 Mutation 演进到近实时标记删除。 |
| [插入](../dml/insert/clickhouse.md) | **大批量 INSERT 是设计核心——每次 INSERT 创建一个不可变 Part**。建议每次插入至少数千行（避免小 Part 过多导致 Merge 压力）。Buffer 表(`ENGINE = Buffer`)缓冲小写入后批量刷入目标表。对比 BigQuery（批量加载免费）和 Snowflake（COPY INTO 批量加载），ClickHouse 对写入粒度有明确的最佳实践——小批量高频写入是反模式。 |
| [更新](../dml/update/clickhouse.md) | **25.7+ 支持标准 `UPDATE t SET col=val WHERE ...` 语法——基于 lightweight patch-part 机制**。25.7 之前只有 `ALTER TABLE ... UPDATE`（异步 Mutation，后台重写 Part）。标准 UPDATE 比传统 Mutation 快数千倍。对比 BigQuery/Snowflake（UPDATE 标准但重写微分区）和 Hive ACID（delta 文件），ClickHouse 的标准 UPDATE 是 OLAP 引擎行级更新的重大突破。 |
| [Upsert](../dml/upsert/clickhouse.md) | **ReplacingMergeTree 在后台 Merge 时按主键去重——无标准 MERGE 语句**。Merge 完成前可能看到重复数据，查询时加 FINAL 关键字强制去重（代价是性能下降）。CollapsingMergeTree 用 +1/-1 标记实现逻辑删除和更新。对比 BigQuery/Snowflake 的 MERGE INTO（标准 SQL）和 Doris（Unique 模型天然 Upsert），ClickHouse 将 Upsert 语义嵌入存储引擎而非 SQL 语法。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/clickhouse.md) | **-If/-State/-Merge/-Array 组合后缀是 ClickHouse 最独特的设计**——`sumIf(amount, status='paid')` 条件聚合无需 CASE WHEN；`quantileState(0.99)(latency)` 保存中间状态供后续 Merge。quantile/quantileExact/quantileTDigest 等百分位数函数族最丰富。对比 BigQuery 的 COUNTIF（专用函数名）和 PG 的 FILTER 子句，ClickHouse 的组合后缀设计最灵活、可扩展性最强。 |
| [条件函数](../functions/conditional/clickhouse.md) | **if(cond, then, else) 函数式语法——支持 CASE WHEN 但社区更推荐 multiIf**。`multiIf(c1, v1, c2, v2, ..., default)` 替代嵌套 CASE WHEN，向量化执行效率更高。对比 Snowflake 的 IFF（三元简洁条件）和 BigQuery 的 SAFE_ 前缀，ClickHouse 的 multiIf 在多条件场景下代码最紧凑。 |
| [日期函数](../functions/date-functions/clickhouse.md) | **toYYYYMM/toStartOfMonth/toStartOfHour 等便捷函数——针对分析场景优化命名**。时区处理完善：`toDateTime(ts, 'Asia/Shanghai')` 内置时区转换。`toRelativeHourNum` 等相对时间函数用于时间差计算。对比 BigQuery 的 DATE_TRUNC（标准命名）和 PG 的 date_trunc，ClickHouse 的日期函数命名更直观但非标准。 |
| [数学函数](../functions/math-functions/clickhouse.md) | **完整数学函数+向量化执行极快——SIMD 指令加速计算**。除零返回 inf/nan（IEEE 754 标准），不报错。intDiv/intDivOrZero 提供整数除法和安全除法。对比 BigQuery 的 SAFE_DIVIDE（返回 NULL）和 PG 的除零报错，ClickHouse 遵循 IEEE 754 标准的除零行为最特殊。 |
| [字符串函数](../functions/string-functions/clickhouse.md) | **函数库最丰富——extractAll 正则批量提取，replaceRegexpAll 正则批量替换**。splitByChar/splitByString 按字符/字符串拆分返回 Array。multiSearchAllPositions 多模式并行搜索。对比 BigQuery 的 REGEXP_EXTRACT（re2 线性时间引擎）和 Snowflake 的 SPLIT_PART，ClickHouse 的字符串函数数量在所有引擎中最多。 |
| [类型转换](../functions/type-conversion/clickhouse.md) | **toInt32/toString 显式转换命名——toTypeOrNull/toTypeOrZero 安全转换**。`accurateCast(val, 'Int32')` 严格模式（溢出报错），`toInt32OrNull(val)` 安全模式（失败返回 NULL）。对比 BigQuery 的 SAFE_CAST（统一前缀命名）和 Snowflake 的 TRY_CAST（标准 SQL），ClickHouse 的类型转换函数命名自成体系但覆盖最全。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/clickhouse.md) | **WITH 子句支持但默认内联展开（非物化）**——CTE 每次引用都会重新计算，不像 PG 可以 MATERIALIZED 强制物化。递归 CTE 24.x+ 支持。对比 BigQuery（优化器自动决策物化/内联）和 PG（支持 MATERIALIZED/NOT MATERIALIZED Hint），ClickHouse 的 CTE 物化控制最弱。 |
| [全文搜索](../query/full-text-search/clickhouse.md) | **tokenbf_v1/ngrambf_v1 布隆过滤索引——非传统全文搜索但对日志分析有效**。tokenbf_v1 基于空格分词的 Bloom Filter，ngrambf_v1 基于 n-gram 的 Bloom Filter。`hasToken(text, 'error')` 利用 tokenbf_v1 加速关键词搜索。对比 BigQuery（SEARCH INDEX+SEARCH() 2023+）和 Doris（CLucene 倒排索引），ClickHouse 的布隆过滤方案轻量但功能有限。 |
| [连接查询](../query/joins/clickhouse.md) | **Hash/Sort Merge JOIN——大表 JOIN 大表容易 OOM，推荐 Dictionary 替代**。Dictionary 将维表加载到内存（类似 Broadcast 但持久化），`dictGet('dict', 'attr', key)` 函数替代 JOIN。Global IN/JOIN 在分布式场景避免子查询重复执行。对比 Snowflake（JOIN 全自动优化）和 BigQuery（Broadcast/Shuffle 自动选择），ClickHouse 的 JOIN 是最大短板——推荐预 JOIN 宽表或 Dictionary。 |
| [分页](../query/pagination/clickhouse.md) | **LIMIT N OFFSET M 标准 + LIMIT N BY col 每组限行（独有语法）**——`LIMIT 3 BY category` 每个 category 返回最多 3 行，无需窗口函数。对比 BigQuery/Snowflake 的 QUALIFY ROW_NUMBER()（需窗口函数）和 PG 的 DISTINCT ON，ClickHouse 的 LIMIT BY 是分组限行最简洁的语法。 |
| [行列转换](../query/pivot-unpivot/clickhouse.md) | **无原生 PIVOT——用 sumIf/countIf 组合函数后缀实现行转列**。`sumIf(amount, status='A') AS sum_a` 替代 PIVOT 语法。这种模式虽然冗长但与 ClickHouse 的组合函数后缀设计一脉相承。对比 BigQuery/Snowflake 的原生 PIVOT 和 Spark 的 PIVOT(3.4+)，ClickHouse 缺乏 PIVOT 语法糖。 |
| [集合操作](../query/set-operations/clickhouse.md) | **UNION ALL 完整，UNION DISTINCT/INTERSECT/EXCEPT 支持**——注意 ClickHouse 中 UNION 默认是 UNION DISTINCT（与 SQL 标准一致但社区常犯错）。对比 BigQuery（UNION 默认 DISTINCT 标准）和 Hive（2.0+ 才完整），ClickHouse 的集合操作标准完备。 |
| [子查询](../query/subquery/clickhouse.md) | **IN 子查询+JOIN 子查询标准支持，Global IN/JOIN 是分布式独有**——`WHERE id GLOBAL IN (SELECT ...)` 在分布式场景避免子查询在每个 Shard 重复执行。对比 PG 的成熟子查询优化和 Spark 的 Catalyst 去关联化，ClickHouse 的子查询优化较基础，复杂关联子查询建议改写为 JOIN。 |
| [窗口函数](../query/window-functions/clickhouse.md) | **21.1+ 引入窗口函数，功能逐版本完善——性能不如原生聚合函数**。ROW_NUMBER/RANK/LAG/LEAD/SUM OVER 等基本完整。窗口函数打破了 ClickHouse 的向量化执行模型（需要跨行状态），性能开销大于等价的聚合方案。无 QUALIFY 子句。对比 BigQuery/Snowflake（QUALIFY 最简去重）和 Hive（0.11+ 大数据窗口函数先驱），ClickHouse 的窗口函数引入最晚且性能不是强项。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/clickhouse.md) | **WITH FILL 是 ClickHouse 独有的最简日期填充语法**——`ORDER BY date WITH FILL FROM '2024-01-01' TO '2024-12-31'` 自动在结果中插入缺失的日期行。对比 BigQuery 的 GENERATE_DATE_ARRAY+UNNEST 和 PG 的 generate_series，ClickHouse 的 WITH FILL 无需辅助表或函数，直接在 ORDER BY 子句中声明填充规则。 |
| [去重](../scenarios/deduplication/clickhouse.md) | **ReplacingMergeTree 在后台 Merge 时自动去重——存储层去重是独有设计**。查询时加 FINAL 强制在查询阶段去重（但性能下降）。`argMax(val, version)` 聚合函数是另一种去重方案——按版本字段取最新值。对比 BigQuery/Snowflake 的 QUALIFY（查询层去重最简）和 PG 的 DISTINCT ON，ClickHouse 是唯一将去重嵌入存储引擎的主流数据库。 |
| [区间检测](../scenarios/gap-detection/clickhouse.md) | **WITH FILL+窗口函数检测——WITH FILL 自动填充缺失值后用窗口函数比较**。numbers() 表函数生成数字序列用于辅助。对比 PG 的 generate_series+LEFT JOIN 和 Spark 的 sequence()+explode()，ClickHouse 的 WITH FILL 方案最独特。 |
| [层级查询](../scenarios/hierarchical-query/clickhouse.md) | **24.x+ 才支持递归 CTE——旧版本需在应用层迭代查询**。这是 ClickHouse 长期的重大功能缺失。对比 PG（长期支持递归 CTE）和 Hive（3.1+ 支持），ClickHouse 引入递归 CTE 最晚。替代方案：在应用层多次查询逐层展开。 |
| [JSON 展开](../scenarios/json-flatten/clickhouse.md) | **JSONExtract 系列函数精确指定类型——Nested 列比 JSON 解析更高效**。`JSONExtractString(json, 'name')` 显式指定返回类型。实验性 JSON 类型自动推断 Schema。**Nested 列**（`Nested(name String, value Int)`)是 ClickHouse 独有的结构化嵌套——比 JSON 查询快数量级。对比 Snowflake 的 LATERAL FLATTEN（最优雅）和 BigQuery 的 JSON_QUERY_ARRAY+UNNEST，ClickHouse 推荐用 Nested 列替代 JSON 存储。 |
| [迁移速查](../scenarios/migration-cheatsheet/clickhouse.md) | **三大核心差异：ENGINE 选择决定数据模型、ORDER BY 决定物理布局和性能、无传统事务需适应最终一致性**。从 RDBMS 迁移的最大思维转换：不做行级 UPDATE/DELETE（25.7+ 前），用 INSERT+Merge 替代。Nullable 默认关闭需显式声明。对比 BigQuery/Snowflake（标准 SQL 友好）和 PG（OLTP 完整），ClickHouse 的迁移学习曲线最陡。 |
| [TopN 查询](../scenarios/ranking-top-n/clickhouse.md) | **LIMIT N BY col 每组取 TopN——ClickHouse 独有的最简分组 TopN 语法**。`SELECT * FROM t ORDER BY score DESC LIMIT 3 BY category` 无需窗口函数。ROW_NUMBER(21.1+) 亦可但性能不如 LIMIT BY。对比 BigQuery/Snowflake 的 QUALIFY ROW_NUMBER()（需窗口函数）和 PG 的 DISTINCT ON+ORDER BY，ClickHouse 的 LIMIT BY 是分组 TopN 最简洁的方案。 |
| [累计求和](../scenarios/running-total/clickhouse.md) | **窗口函数(21.1+) SUM() OVER 标准累计，或 runningAccumulate 状态函数**——runningAccumulate 是 ClickHouse 独有的函数，将 -State 中间状态逐行合并。21.1 之前无窗口函数时 runningAccumulate 是唯一方案。对比 BigQuery/Snowflake（SUM() OVER 标准）和 Spark（Tungsten 代码生成优化），ClickHouse 的向量化执行在聚合场景中性能最强但窗口函数不是强项。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/clickhouse.md) | **ReplacingMergeTree 版本字段实现 SCD——无 MERGE 语句**。`ReplacingMergeTree(version)` 在 Merge 时保留每个主键的最新版本。SCD Type 2 需要应用层插入新版本行并设置版本号。对比 BigQuery/Snowflake 的 MERGE INTO（标准 SQL SCD）和 Doris（Unique 模型 Upsert），ClickHouse 将 SCD 语义嵌入存储引擎而非 SQL 语法。 |
| [字符串拆分](../scenarios/string-split-to-rows/clickhouse.md) | **splitByChar/splitByString+arrayJoin 展开——简洁高效**。`SELECT arrayJoin(splitByChar(',', str))` 一行搞定。arrayJoin 是 ClickHouse 独有的"数组炸行"函数（类似 Hive 的 LATERAL VIEW EXPLODE 但语法更简洁）。对比 Snowflake 的 SPLIT_TO_TABLE（最简）和 Hive 的 SPLIT+LATERAL VIEW EXPLODE（最冗长），ClickHouse 的方案简洁度仅次于 Snowflake。 |
| [窗口分析](../scenarios/window-analytics/clickhouse.md) | **21.1+ 窗口函数支持，ROWS/RANGE 帧支持，功能逐版本增强**——移动平均、同环比计算可实现。性能不如等价的聚合方案（窗口函数打破了向量化执行的列批处理模型）。无 QUALIFY、无 WINDOW 命名子句。对比 BigQuery/Snowflake（QUALIFY+WINDOW 命名子句最强）和 Spark（Tungsten 代码生成优化窗口），ClickHouse 的窗口分析是功能最新、性能非最优的模块。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/clickhouse.md) | **Array/Map/Tuple/Nested 四种复合类型——Nested 是 ClickHouse 独有设计**。`Nested(name String, value Int)` 在物理存储上展开为多个平行 Array 列，查询效率远高于 JSON。arrayJoin 展开 Array 为行。对比 BigQuery 的 STRUCT/ARRAY（CROSS JOIN UNNEST）和 Snowflake 的 VARIANT（半结构化），ClickHouse 的 Nested 列在性能上最优但灵活性不如 VARIANT。 |
| [日期时间](../types/datetime/clickhouse.md) | **Date/Date32/DateTime/DateTime64 分级精度——时区作为列类型参数内置**。`DateTime64(3, 'Asia/Shanghai')` 在列定义中直接指定精度（毫秒/微秒/纳秒）和时区。Date32 扩展了 Date 的范围（1900-2299）。对比 BigQuery 的四种时间类型（DATE/TIME/DATETIME/TIMESTAMP）和 Snowflake 的三种 TIMESTAMP，ClickHouse 的时区作为类型参数的设计最独特。 |
| [JSON](../types/json/clickhouse.md) | **JSONExtract 函数族查询 String 列中的 JSON，实验性 JSON 类型自动列化**——实验性 JSON 类型自动推断 Schema 并按列式存储子字段（类似 Snowflake VARIANT 的自动列化）。生产环境推荐用 Nested 列替代 JSON。对比 PG 的 JSONB+GIN 索引（索引能力最强）和 Snowflake 的 VARIANT（查询语法最优雅），ClickHouse 的 JSON 支持正在快速演进。 |
| [数值类型](../types/numeric/clickhouse.md) | **Int8-Int256/UInt8-UInt256 整数类型最丰富——包含无符号类型和 256 位大整数**。Decimal32/64/128/256 精确十进制数。Float32/Float64 IEEE 754 浮点。LowCardinality(T) 对低基数类型自动字典编码（存储和查询性能提升 2-10 倍）。对比 BigQuery 的 INT64（单一整数极简）和 PG 的有符号整数系列，ClickHouse 的数值类型粒度最细——从 1 字节到 32 字节整数全覆盖。 |
| [字符串类型](../types/string/clickhouse.md) | **String 无长度限制 + FixedString(N) 定长 + LowCardinality(String) 字典编码**——LowCardinality 是 ClickHouse 独有的类型级优化：对国家码、状态码等低基数字符串自动字典编码，查询性能提升数倍。FixedString 适用于固定长度数据（如 MD5/UUID）。对比 BigQuery 的 STRING（极简无长度）和 PG 的 VARCHAR(n)/TEXT，ClickHouse 的 LowCardinality 是字符串存储优化的标杆。 |
