# Google Cloud Spanner

**分类**: 全球分布式数据库（Google）
**文件数**: 51 个 SQL 文件
**总行数**: 5017 行

> **关键人物**：[Jeff Dean, Sanjay Ghemawat](../docs/people/cockroachdb-spanner.md)（Spanner 论文）

## 概述与定位

Google Cloud Spanner 是 Google 开发的全球分布式关系型数据库，也是业界首个实现外部一致性（external consistency）的商用系统。Spanner 定位于需要全球多区域部署、强一致事务和极高可用性的关键业务场景，如金融交易、全球用户系统和游戏后端。它提供关系模型和 SQL 查询能力，同时保持近乎无限的水平扩展。

## 历史与演进

- **2007 年**：Google 内部开始 Spanner 项目，目标替代 Bigtable 在需要事务场景的不足。
- **2012 年**：发表具有里程碑意义的 Spanner 论文，首次公开 TrueTime 机制。
- **2013 年**：发表 F1 论文，展示 Spanner 如何承载 Google AdWords 核心业务。
- **2017 年**：Cloud Spanner GA，作为全托管服务对外开放。
- **2019 年**：引入 GoogleSQL 方言增强和查询优化器改进。
- **2022 年**：推出 PostgreSQL 接口模式，提供 PG 兼容的连接方式。
- **2023-2025 年**：支持自动缩容、更灵活的实例配置、向量搜索和 AI 集成。

## 核心设计思路

Spanner 最核心的创新是 **TrueTime**——通过 GPS 时钟和原子钟提供全球一致的时间参考，使分布式事务无需额外通信即可获得外部一致性。数据以 Split 为单位分布，每个 Split 通过 Paxos 协议跨区域复制。Schema 设计高度强调**父子表交错**（INTERLEAVE IN PARENT），将相关数据物理共置以减少分布式 JOIN 开销。**不支持自增主键**是一个刻意的设计决策——要求用户使用 UUID 或复合主键避免写热点。

## 独特特色

- **TrueTime 与外部一致性**：提供比 SERIALIZABLE 更强的一致性保证——事务的提交顺序与真实时间一致。
- **INTERLEAVE IN PARENT**：`CREATE TABLE Orders (...) INTERLEAVE IN PARENT Customers ON DELETE CASCADE` 将子表数据与父表物理交错存储。
- **无自增主键**：刻意不支持 AUTO_INCREMENT/SERIAL，强制使用 UUID 或应用生成的分散 ID。
- **GoogleSQL 方言**：在标准 SQL 基础上提供 STRUCT、ARRAY 等丰富类型和函数。
- **Stale Read**：`SELECT ... WITH (EXACT_STALENESS = '10s')` 允许读取略旧的快照以降低延迟。
- **变更流 (Change Streams)**：追踪数据变更用于下游消费。
- **多区域配置**：支持区域级、双区域和多区域实例配置，SLA 最高达 99.999%。

## 已知不足

- **仅限 Google Cloud**：无法在其他云或本地私有化部署（模拟器仅用于开发测试）。
- 不支持自增主键，对习惯 AUTO_INCREMENT 的开发者有较大学习成本。
- 无存储过程和触发器，服务端逻辑需在应用层实现。
- 强一致跨区域写入的延迟受物理距离限制（通常数百毫秒）。
- DDL 操作是长时运行任务，无法在事务中执行。
- 成本相对较高，按节点小时和存储容量计费。
- PostgreSQL 接口模式的兼容性有限，许多 PG 特性不支持。

## 对引擎开发者的参考价值

Spanner 的 TrueTime 机制是分布式系统时钟理论的工程化突破，展示了硬件时钟如何解决分布式因果序问题。INTERLEAVE IN PARENT 的数据共置策略对所有分布式数据库的 Schema 设计都有深刻启示。其论文对分布式事务、半同步复制和全球一致性的讨论是数据库领域的经典参考。不支持自增主键的设计哲学体现了分布式场景下的范式转变。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/spanner.md) | **全球分布式，无自增**——INTERLEAVE IN PARENT 实现父子表数据物理共置，是 Spanner 独有的 Schema 设计范式。UUID 或 bit-reversed sequence 替代自增避免写热点。GoogleSQL 方言支持 STRUCT/ARRAY。对比 CockroachDB 的 unique_rowid() 和 TiDB 的 AUTO_RANDOM，Spanner 的 INTERLEAVE 共置策略对跨表查询优化效果最显著。 |
| [改表](../ddl/alter-table/spanner.md) | **Schema 变更是长时间运行任务**——DDL 操作不能在事务中执行，每个 DDL 以后台任务形式异步完成。ADD/DROP COLUMN 不阻塞读写但变更不可回滚。对比 CockroachDB 的事务性 DDL 和 TiDB 的 Online DDL，Spanner 的 DDL 模型最保守但保证了全球一致性。 |
| [索引](../ddl/indexes/spanner.md) | **分布式二级索引 + STORING 覆盖列 + INTERLEAVE 共置索引**——INTERLEAVE IN 可将索引数据与父表物理共置，减少跨 Split 读取。STORING 子句避免回表。NULL_FILTERED 索引排除 NULL 减少存储。对比 CockroachDB 的 STORING 和 PG 的 INCLUDE，Spanner 的 INTERLEAVE 索引是独有的共置优化。 |
| [约束](../ddl/constraints/spanner.md) | **PK/FK/CHECK/UNIQUE 完整强制执行**——分布式事务保证跨 Split 的约束一致性。INTERLEAVE 关系自带级联删除（ON DELETE CASCADE/NO ACTION）。CHECK 约束在写入时实时校验。对比 BigQuery（NOT ENFORCED）和 TiDB（FK 实验性），Spanner 是云数据库中约束执行最严格的。 |
| [视图](../ddl/views/spanner.md) | **普通视图支持，无物化视图**——视图在查询时展开执行，无预计算能力。分析加速需依赖 BigQuery 联邦查询或应用层缓存。对比 BigQuery 的自动刷新物化视图和 PG 的 MATERIALIZED VIEW，Spanner 的物化视图缺失是分析场景的短板。 |
| [序列与自增](../ddl/sequences/spanner.md) | **刻意不支持 AUTO_INCREMENT**——bit-reversed SEQUENCE（2023+）将自增值的位反转产生分散的键，兼顾唯一性和分布均匀性。GENERATE_UUID() 是另一选择。对比 CockroachDB 的 unique_rowid() 和 TiDB 的 AUTO_RANDOM，Spanner 的 bit-reversed 策略最体现分布式 ID 设计哲学。 |
| [数据库/Schema/用户](../ddl/users-databases/spanner.md) | **Instance→Database→Schema 三级命名 + IAM 权限**——权限完全基于 Google Cloud IAM，无 SQL GRANT/REVOKE。FGAC 支持行/列级权限。多区域实例 SLA 最高 99.999%。对比 CockroachDB 的 PG 兼容 RBAC 和 BigQuery 的 GCP IAM，Spanner 的权限模型最深度绑定 Google Cloud。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/spanner.md) | **无服务端动态 SQL**——所有查询通过客户端 SDK（Go/Java/Python/Node.js）构建和提交。Parameterized Query 支持参数化但不支持动态表名/列名。对比 PG 的 PL/pgSQL EXECUTE 和 BigQuery 的 EXECUTE IMMEDIATE，Spanner 将所有逻辑推到应用层是其无服务器哲学的体现。 |
| [错误处理](../advanced/error-handling/spanner.md) | **无过程式错误处理，gRPC 错误码**——事务冲突返回 ABORTED 错误码，客户端库自动重试。DEADLINE_EXCEEDED 表示查询超时。所有错误处理在应用层完成。对比 PG 的 EXCEPTION WHEN 和 Oracle 的 PL/SQL 异常处理，Spanner 完全没有服务端过程式编程能力。 |
| [执行计划](../advanced/explain/spanner.md) | **EXPLAIN 展示分布式执行计划 + Query Statistics**——可看到 Split 级别的扫描范围和数据传输。Query Statistics 表提供历史查询性能指标。对比 CockroachDB 的 EXPLAIN (DISTSQL) 和 BigQuery 的 Console Execution Details，Spanner 的 EXPLAIN 输出紧凑但信息密度高。 |
| [锁机制](../advanced/locking/spanner.md) | **TrueTime + 2PL（Paxos）= 外部一致性**——这是比 SERIALIZABLE 更强的一致性保证，事务的提交顺序与真实物理时间一致。读写事务使用悲观锁，只读事务无锁。Stale Read 允许读取稍旧快照降低延迟。对比 CockroachDB 的 HLC SERIALIZABLE 和 TiDB 的 Percolator SI，Spanner 的 TrueTime 外部一致性是业界最强。 |
| [分区](../advanced/partitioning/spanner.md) | **Split 自动分片（基于负载），无手动分区**——数据按主键范围自动分裂/合并，完全由系统管理。用户无法手动指定分区策略。INTERLEAVE 实现逻辑上的共置。对比 CockroachDB 的 Range 自动分片和 TiDB 的 Region+手动分区双层，Spanner 的纯自动分片最简单但用户可控性最低。 |
| [权限](../advanced/permissions/spanner.md) | **IAM + Fine-Grained Access Control（FGAC）**——Database-level 和 Table-level 权限通过 IAM Role 管理。FGAC 支持行级和列级访问控制。无 SQL GRANT/REVOKE 语法。对比 PG 的 RLS 行级安全和 BigQuery 的 Column-level Security，Spanner 的权限模型声明式但绑定 GCP。 |
| [存储过程](../advanced/stored-procedures/spanner.md) | **无存储过程**——所有业务逻辑在应用层实现。这是 Spanner 的刻意设计——无状态的全球分布式数据库不适合运行用户代码。对比 OceanBase 的完整 PL/SQL 和 CockroachDB 的 PL/pgSQL（有限），Spanner 在过程式编程方面是所有主流数据库中最受限的。 |
| [临时表](../advanced/temp-tables/spanner.md) | **无临时表支持**——所有表都是全球分布的持久化表。临时数据需在应用层管理。对比 PG/MySQL 的标准临时表和 BigQuery 的 _SESSION 临时表，Spanner 的设计哲学不包含临时状态。 |
| [事务](../advanced/transactions/spanner.md) | **TrueTime 外部一致性（全球最强一致性保证）**——读写事务在全球范围内保证线性一致。只读事务可指定时间戳读取历史快照。Stale Read 降低跨区域延迟。对比 CockroachDB 的 SERIALIZABLE 和 OceanBase 的 Paxos 强一致，Spanner 的外部一致性是基于硬件（GPS+原子钟）的独有能力。 |
| [触发器](../advanced/triggers/spanner.md) | **无触发器，Change Streams 替代**——Change Streams 追踪表或数据库级别的数据变更，下游通过 Dataflow/Pub/Sub 消费。对比 CockroachDB 的 CHANGEFEED 和 BigQuery 的 Cloud Functions，Spanner 的 Change Streams 与 Google Cloud 生态深度集成。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/spanner.md) | **DELETE + WHERE 标准语法**——分布式事务保证跨 Split 删除的原子性。不支持 TRUNCATE。大批量删除建议使用分区化删除或 Mutation API 批量操作。对比 BigQuery 的分区级 DELETE 和 CockroachDB 的 DELETE+RETURNING，Spanner 的删除语法简单但大批量操作需关注事务大小限制。 |
| [插入](../dml/insert/spanner.md) | **INSERT / INSERT OR UPDATE + Mutation API 批量写入**——INSERT OR UPDATE 是 Spanner 的原生 Upsert 语法。Mutation API 绕过 SQL 层直接写入存储，吞吐量更高。对比 BigQuery 的批量 LOAD JOB 和 CockroachDB 的 IMPORT，Spanner 的 Mutation API 是高吞吐写入的推荐路径。 |
| [更新](../dml/update/spanner.md) | **UPDATE 标准语法 + 分布式事务**——跨 Split 更新通过 TrueTime 外部一致性保证。更新主键值需要 DELETE+INSERT（主键不可修改）。对比 CockroachDB（支持主键更新但触发迁移）和 BigQuery（UPDATE 必须带 WHERE），Spanner 的主键不可变设计最严格。 |
| [Upsert](../dml/upsert/spanner.md) | **INSERT OR UPDATE（原生 Upsert）**——语法简洁，整行替换语义。不支持标准 SQL 的 MERGE INTO（仅部分条件 Upsert）。对比 CockroachDB 的 UPSERT/ON CONFLICT 和 BigQuery 的 MERGE，Spanner 的 INSERT OR UPDATE 最简洁但缺少 MERGE 的条件灵活性。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/spanner.md) | **标准聚合 + ARRAY_AGG + 分布式并行聚合**——APPROX_COUNT_DISTINCT 提供 HyperLogLog 近似计数。COUNTIF 条件计数。函数集与 BigQuery 高度一致（共享 GoogleSQL 方言）。对比 BigQuery 的完整分析函数和 PG 的 FILTER 子句，Spanner 的聚合函数集足够完整但偏向 OLTP 场景。 |
| [条件函数](../functions/conditional/spanner.md) | **IF/CASE/COALESCE/IFNULL（GoogleSQL 方言）**——IF() 函数与 BigQuery 一致。COALESCE/NULLIF 标准 SQL。对比 PG 仅有 CASE/COALESCE 和 BigQuery 的 SAFE_ 前缀，Spanner 共享 GoogleSQL 的条件函数但无 SAFE_ 系列。 |
| [日期函数](../functions/date-functions/spanner.md) | **DATE_TRUNC/DATE_ADD/DATE_DIFF/EXTRACT（GoogleSQL）**——与 BigQuery 的日期函数基本一致。TIMESTAMP 强制 UTC 存储。GENERATE_DATE_ARRAY 生成日期序列。对比 PG 的 date_trunc/INTERVAL 运算和 MySQL 的 DATE_FORMAT，Spanner 的日期函数是 GoogleSQL 风格。 |
| [数学函数](../functions/math-functions/spanner.md) | **完整数学函数（GoogleSQL）**——SAFE_DIVIDE/SAFE_NEGATE 等 SAFE_ 前缀函数避免除零报错。IEEE_DIVIDE 返回 Infinity/NaN。对比 BigQuery 的完整 SAFE_ 系列和 PG 的严格除零报错，Spanner 共享 BigQuery 的安全函数设计。 |
| [字符串函数](../functions/string-functions/spanner.md) | **CONCAT/SUBSTR/REGEXP_EXTRACT（GoogleSQL 同 BigQuery）**——SPLIT 返回 ARRAY 可直接 UNNEST。REGEXP 基于 re2 引擎（线性时间）。对比 PG 的 `\|\|` 拼接/regexp_replace 和 MySQL 的 CONCAT，Spanner 的字符串函数与 BigQuery 几乎完全一致。 |
| [类型转换](../functions/type-conversion/spanner.md) | **CAST / SAFE_CAST（同 BigQuery）+ 严格类型**——SAFE_CAST 转换失败返回 NULL 而非报错。类型系统严格，隐式转换极少。对比 MySQL 的宽松隐式转换和 PG 的 `::` 运算符，Spanner 继承了 GoogleSQL 的严格类型+安全转换哲学。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/spanner.md) | **WITH 标准 + 递归 CTE 支持**——与 BigQuery CTE 语法一致。递归 CTE 有深度限制。CTE 物化/内联由优化器自动决定。对比 PG 的成熟 CTE 和 BigQuery 的自动优化，Spanner 的 CTE 实现标准完整。 |
| [全文搜索](../query/full-text-search/spanner.md) | **SEARCH INDEX + TOKENIZE 全文搜索（2023+）**——CREATE SEARCH INDEX 创建全文索引，SEARCH() 函数执行搜索。支持多语言分词。对比 BigQuery 的 SEARCH INDEX 和 PG 的 tsvector+GIN（最成熟），Spanner 的全文搜索是近期新增能力。 |
| [连接查询](../query/joins/spanner.md) | **分布式 JOIN + INTERLEAVE 共置优化**——INTERLEAVE 父子表的 JOIN 在本地 Split 完成，无需跨节点传输。非共置表的 JOIN 通过 HASH JOIN 或 Broadcast JOIN 实现。对比 OceanBase 的 Tablegroup 共置和 CockroachDB 的 Lookup JOIN，Spanner 的 INTERLEAVE 共置 JOIN 是设计层面最优雅的方案。 |
| [分页](../query/pagination/spanner.md) | **LIMIT/OFFSET 标准，Keyset 分页推荐**——深度分页建议使用 Keyset 方式（WHERE pk > last_pk LIMIT N）避免跨 Split 收集和排序。Stale Read 可减少分页查询的延迟。对比 CockroachDB 的 AS OF SYSTEM TIME 分页和 BigQuery（无分页优化需求），Spanner 推荐 Keyset 分页是分布式场景的最佳实践。 |
| [行列转换](../query/pivot-unpivot/spanner.md) | **无原生 PIVOT**——需用 CASE+GROUP BY 或 ARRAY_AGG 模拟。对比 BigQuery 的原生 PIVOT（2021+）和 Oracle 的 PIVOT/UNPIVOT，Spanner 缺乏行列转换语法糖。 |
| [集合操作](../query/set-operations/spanner.md) | **UNION/INTERSECT/EXCEPT 完整支持**——ALL/DISTINCT 修饰符标准。分布式执行时集合操作需要跨 Split 合并。对比 BigQuery（UNION DISTINCT 是默认）和 PG（长期完整支持），Spanner 的集合操作与 GoogleSQL 一致。 |
| [子查询](../query/subquery/spanner.md) | **关联子查询 + IN/EXISTS（GoogleSQL）**——优化器可将子查询转为 JOIN。ARRAY 子查询（SELECT ARRAY(...)）是 GoogleSQL 的独特语法。对比 PG 的成熟子查询优化和 BigQuery 的 ARRAY 子查询，Spanner 的子查询能力与 BigQuery 一致。 |
| [窗口函数](../query/window-functions/spanner.md) | **完整窗口函数 + QUALIFY 支持（GoogleSQL）**——QUALIFY 直接过滤窗口函数结果，无需子查询包装。ROWS/RANGE 帧完整。对比 BigQuery 的 QUALIFY（相同）和 PG/MySQL（无 QUALIFY），Spanner 共享 GoogleSQL 的 QUALIFY 优势。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/spanner.md) | **GENERATE_DATE_ARRAY + UNNEST（同 BigQuery）**——`UNNEST(GENERATE_DATE_ARRAY('2024-01-01','2024-12-31'))` 生成日期序列，比递归 CTE 更直观。对比 PG 的 generate_series 和 TiDB 的递归 CTE，Spanner 的 GoogleSQL 方案与 BigQuery 共享同一语法。 |
| [去重](../scenarios/deduplication/spanner.md) | **ROW_NUMBER+CTE 或 QUALIFY 去重**——QUALIFY ROW_NUMBER() OVER(...) = 1 无需子查询，是最简去重写法。对比 PG 的 DISTINCT ON 和 TiDB 的 ROW_NUMBER+CTE，Spanner 的 QUALIFY 使去重最简洁。 |
| [区间检测](../scenarios/gap-detection/spanner.md) | **GENERATE_DATE_ARRAY + 窗口函数**——生成完整日期序列后 LEFT JOIN 检测缺失值，或用 LAG/LEAD 检测间隙。对比 TimescaleDB 的 time_bucket_gapfill 和 CockroachDB 的 generate_series，Spanner 使用 GoogleSQL 标准方法。 |
| [层级查询](../scenarios/hierarchical-query/spanner.md) | **递归 CTE 支持**——WITH RECURSIVE 标准语法，有递归深度限制。无 Oracle 的 CONNECT BY。对比 Oracle/达梦 的 CONNECT BY 和 CockroachDB 的递归 CTE，Spanner 采用标准 SQL 方案。 |
| [JSON 展开](../scenarios/json-flatten/spanner.md) | **JSON_EXTRACT/JSON_QUERY + UNNEST 展开**——JSON 类型（2022+）支持 JSON_VALUE/JSON_QUERY 标准函数。ARRAY 类型的 UNNEST 用于展开 JSON 数组。对比 PG 的 jsonb_array_elements 和 BigQuery 的 JSON_QUERY_ARRAY+UNNEST，Spanner 的 JSON 处理与 GoogleSQL 一致。 |
| [迁移速查](../scenarios/migration-cheatsheet/spanner.md) | **三大核心差异：INTERLEAVE 共置 + TrueTime + GoogleSQL 方言**——无自增主键、无存储过程/触发器、DDL 是异步任务。仅限 Google Cloud。PG 接口模式兼容性有限。对比 CockroachDB（PG 兼容+多云）和 TiDB（MySQL 兼容+开源），Spanner 的学习成本最高但一致性保证最强。 |
| [TopN 查询](../scenarios/ranking-top-n/spanner.md) | **ROW_NUMBER + LIMIT 或 QUALIFY**——QUALIFY ROW_NUMBER() OVER(PARTITION BY g ORDER BY v DESC) <= N 是最简 TopN 写法。对比 BigQuery 的 QUALIFY（相同）和 TiDB 的 ROW_NUMBER+CTE，Spanner 的 QUALIFY 使 TopN 查询最简洁。 |
| [累计求和](../scenarios/running-total/spanner.md) | **SUM() OVER 标准 + 分布式并行**——窗口函数在分布式环境下自动并行化。对比 BigQuery 的 Slot 自动扩展和 PG 的单机窗口函数，Spanner 的窗口函数适合 OLTP 规模的累计计算。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/spanner.md) | **INSERT OR UPDATE + 事务**——原生 Upsert 语法简洁。SCD Type 2 需多条 SQL 组合在事务中完成。无标准 MERGE INTO。对比 BigQuery 的 MERGE（完整 SCD 支持）和 CockroachDB 的 UPSERT，Spanner 的 INSERT OR UPDATE 简洁但缺少 MERGE 灵活性。 |
| [字符串拆分](../scenarios/string-split-to-rows/spanner.md) | **SPLIT + UNNEST 展开（同 BigQuery）**——`SELECT val FROM UNNEST(SPLIT('a,b,c', ',')) AS val` 一行搞定。对比 PG 的 string_to_array+unnest 和 TiDB 的递归 CTE，Spanner 的 SPLIT+UNNEST 是最简洁的字符串拆分方案之一。 |
| [窗口分析](../scenarios/window-analytics/spanner.md) | **完整窗口函数 + QUALIFY 支持（GoogleSQL）**——移动平均、同环比、占比等分析场景完整覆盖。QUALIFY 简化了窗口结果过滤。对比 BigQuery（完全相同的 GoogleSQL 窗口能力）和专用 OLAP 引擎，Spanner 的窗口分析适合 OLTP 附带的分析需求。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/spanner.md) | **ARRAY/STRUCT 支持（同 BigQuery）+ INTERLEAVE 父子表**——STRUCT 可作为列类型和查询中的匿名复合值。ARRAY 不能嵌套 ARRAY 但 ARRAY<STRUCT<...>> 可以。INTERLEAVE 提供了另一种表间数据组织方式。对比 BigQuery 的 STRUCT/ARRAY（完全一致）和 PG 的 COMPOSITE TYPE/ARRAY，Spanner 的复合类型设计源自 Dremel/Protocol Buffers 传统。 |
| [日期时间](../types/datetime/spanner.md) | **DATE/TIMESTAMP（UTC 强制），无 TIME/INTERVAL**——TIMESTAMP 存储精度为纳秒，强制 UTC 时区。不支持 TIME 和 INTERVAL 类型（与 BigQuery 不同）。对比 BigQuery 的四种时间类型和 PG 的完整时间体系，Spanner 的时间类型最精简。 |
| [JSON](../types/json/spanner.md) | **JSON 类型（2022+）+ JSON_EXTRACT 路径查询**——支持 JSON_VALUE/JSON_QUERY/JSON_QUERY_ARRAY 标准函数。JSON 列可创建生成列（Generated Column）用于索引。对比 PG 的 JSONB+GIN 索引和 BigQuery 的原生 JSON，Spanner 的 JSON 支持较新但基本功能完整。 |
| [数值类型](../types/numeric/spanner.md) | **INT64/FLOAT32/FLOAT64/NUMERIC/BOOL（GoogleSQL）**——仅一种整数类型 INT64（无 INT32/INT16），与 BigQuery 一致。NUMERIC 精度 38 位小数 9 位。FLOAT32（2023+）新增。对比 BigQuery 的 BIGNUMERIC（76 位）和 PG 的 INTEGER/BIGINT/NUMERIC，Spanner 的数值类型极简但精度覆盖大多数场景。 |
| [字符串类型](../types/string/spanner.md) | **STRING 无长度限制（最大 10MB），BYTES 二进制**——与 BigQuery 的 STRING/BYTES 完全一致。无 VARCHAR(n)/CHAR(n) 区分。对比 PG 的 TEXT/VARCHAR 和 MySQL 的 VARCHAR(n)，Spanner 的字符串类型延续 GoogleSQL 的极简设计。 |
