# Apache Doris

**分类**: MPP 分析数据库（Apache）
**文件数**: 51 个 SQL 文件
**总行数**: 4391 行

> **关键人物**：[百度 Palo → Apache Doris](../docs/people/doris-starrocks-founders.md)

## 概述与定位

Apache Doris 是一款开源的 MPP 分析数据库，源自百度内部的 Palo 项目，2018 年捐赠给 Apache 基金会。Doris 定位于实时分析场景——亚秒级查询响应、高并发低延迟的 OLAP 查询，兼顾批量数据导入和实时数据摄取。它与 StarRocks 同源（StarRocks 是 2020 年从 Doris 分叉），二者在架构和 SQL 方言上有大量相似之处。Doris 在中国互联网、金融、电信行业有广泛应用。

## 历史与演进

- **2012 年**：百度内部启动 Palo 项目，面向广告报表等实时分析场景。
- **2018 年**：Palo 捐赠给 Apache 基金会，更名为 Apache Doris（孵化器项目）。
- **2020 年**：StarRocks（原 DorisDB）从 Doris 分叉，开始独立发展。
- **2022 年**：Apache Doris 毕业成为顶级项目，1.x 版本引入向量化执行引擎、Bitmap 索引增强。
- **2023 年**：Doris 2.0 引入倒排索引、存算分离架构（预览）、Merge-on-Write 优化 Unique 模型。
- **2024-2025 年**：增强存算分离（Cloud-Native）、自动物化视图、多目录联邦查询（Multi-Catalog）、半结构化数据变体类型（Variant）。

## 核心设计思路

1. **FE + BE 架构**：Frontend（FE）负责 SQL 解析、优化和元数据管理，Backend（BE）负责数据存储和查询执行，二者均可水平扩展。
2. **四种数据模型**：Duplicate（明细）、Aggregate（预聚合）、Unique（唯一键去重）、Primary Key（主键实时更新），根据业务场景选择。
3. **MPP 向量化执行**：基于列式内存布局的向量化执行引擎，配合 Pipeline 执行模型，充分利用 CPU 缓存和 SIMD 指令。
4. **MySQL 协议兼容**：使用 MySQL 客户端/驱动即可连接 Doris，降低了迁移和接入成本。

## 独特特色

| 特性 | 说明 |
|---|---|
| **四种数据模型** | Duplicate（全量明细）、Aggregate（写入时预聚合）、Unique（唯一键最新值）——根据查询模式选择最优模型。 |
| **ROLLUP** | 在基础表上创建 ROLLUP 物化索引，预计算特定维度组合的聚合结果，优化器自动命中最优 ROLLUP。 |
| **物化视图** | 支持同步和异步物化视图，优化器可透明路由查询到物化视图，加速聚合类查询。 |
| **Multi-Catalog** | 通过 Catalog 机制直接查询 Hive/Iceberg/Hudi/Elasticsearch/MySQL/PostgreSQL 等外部数据源，无需 ETL。 |
| **Stream Load** | 通过 HTTP PUT 接口实时推送 JSON/CSV 数据到 Doris，支持事务性写入和 exactly-once 语义。 |
| **Light Schema Change** | 列的增删改可在秒级完成，无需数据重写，对在线业务友好。 |
| **Variant 类型（2.1+）** | 半结构化数据类型，写入时自动推断 schema 并按列存储。对 JSON 分析场景性能远优于 STRING + JSON 函数。对标 Snowflake VARIANT。 |
| **倒排索引（2.0+）** | 基于 CLucene 的倒排索引，支持全文检索、等值/范围过滤加速。对日志分析场景（替代 Elasticsearch）极有价值。 |
| **Nereids 优化器（2.0+）** | 全新的 Cascades 框架 CBO 优化器，替代旧的 RBO 优化器。支持更复杂的查询重写和代价估算。 |
| **AUTO_INCREMENT（2.1+）** | Unique Key Merge-on-Write 表支持自增列，对从 MySQL 迁移的用户友好。 |
| **Runtime Filter** | 运行时动态生成 Bloom Filter / IN 谓词下推到扫描侧，减少 JOIN 的数据量，对星型模型查询效果显著。 |

## 已知不足

- **事务能力有限**：不支持标准的 BEGIN/COMMIT/ROLLBACK 多语句事务，每个导入任务是一个原子操作。
- **存储过程/触发器缺失**：不支持传统 RDBMS 的存储过程、触发器和游标，过程化逻辑需在应用层实现。
- **UPDATE/DELETE 限制**：仅 Unique/Primary Key 模型支持行级更新和删除，Aggregate/Duplicate 模型不支持。
- **单表数据规模**：虽然支持分区和分桶，但单表超过数百亿行时性能调优难度增加。
- **与 StarRocks 的差异化**：二者功能高度重合，社区和用户在选型时容易产生困惑。

## 对引擎开发者的参考价值

- **多数据模型设计**：在建表时选择 Duplicate/Aggregate/Unique 模型的设计，将查询优化前置到 DDL 阶段，对分析引擎的数据建模有启发。
- **ROLLUP 自动路由**：优化器根据查询的维度和度量自动选择最优 ROLLUP 的实现，对物化视图匹配算法有参考。
- **Runtime Filter 实现**：在 Hash Join 的 Build 侧动态生成 Filter 并下推到 Probe 侧扫描的机制，是分布式 JOIN 优化的实用技术。
- **FE/BE 分离架构**：元数据和计算的解耦设计（FE 管理 + BE 执行），对分布式数据库的架构分层有参考。
- **Light Schema Change**：列元数据变更不触发数据重写的实现（仅修改 FE 元数据 + BE 文件 Footer），对在线 DDL 设计有借鉴。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/doris.md) | **四种数据模型是建表的核心决策**——Duplicate（全量明细）、Aggregate（写入时预聚合 SUM/MAX/MIN/REPLACE）、Unique（唯一键最新值）、Primary Key（Merge-on-Write 实时更新 2.0+）。模型选择决定了写入、查询和存储行为。DISTRIBUTED BY HASH 指定分桶键控制数据分布。对比 ClickHouse（MergeTree 引擎家族类似思路）和 BigQuery/Snowflake（用户无需选择数据模型），Doris 将查询优化前置到 DDL 阶段。 |
| [改表](../ddl/alter-table/doris.md) | **Light Schema Change(1.2+) 秒级完成列增删改——不触发数据重写**。仅修改 FE 元数据和 BE 文件 Footer，对在线业务零影响。ROLLUP 物化索引可通过 ALTER TABLE ADD ROLLUP 动态添加。对比 Snowflake（ALTER 瞬时元数据操作）和 ClickHouse（ADD/DROP 轻量但 MODIFY 重写），Doris 的 Light Schema Change 在 MPP 分析引擎中最实用。 |
| [索引](../ddl/indexes/doris.md) | **Short Key 前缀索引+Bloom Filter+Bitmap+倒排索引(2.0+) 四层索引体系**——Short Key 自动取建表前 36 字节作前缀索引。倒排索引(2.0+)基于 CLucene 实现，支持全文检索和等值/范围加速（对标 Elasticsearch）。Bitmap 索引适合低基数列（如性别、状态码）。对比 ClickHouse（稀疏索引+跳数索引）和 BigQuery（无索引仅分区+聚集），Doris 的索引体系在 OLAP 引擎中最丰富。 |
| [约束](../ddl/constraints/doris.md) | **无传统 PK/FK/UNIQUE/CHECK 约束——数据模型替代约束功能**。Unique 模型通过 Key 列自动去重替代 UNIQUE 约束，Aggregate 模型通过预聚合替代 CHECK+聚合逻辑。对比 BigQuery/Snowflake（PK/FK NOT ENFORCED 至少有元数据意义）和 PG（全部强制执行），Doris 用数据模型而非约束声明来表达数据语义。 |
| [视图](../ddl/views/doris.md) | **同步物化视图(ROLLUP)+异步物化视图(2.0+)——CBO 自动路由查询命中最优视图**。ROLLUP 是预计算特定维度组合的聚合结果。Nereids CBO(2.0+)可透明改写查询命中物化视图，无需用户修改 SQL。对比 BigQuery（物化视图自动刷新+智能改写）和 ClickHouse（物化视图=INSERT 触发器），Doris 的 ROLLUP 自动路由在 MPP 引擎中最成熟。 |
| [序列与自增](../ddl/sequences/doris.md) | **AUTO_INCREMENT(2.1+) 仅 Unique Key Merge-on-Write 表支持**——对从 MySQL 迁移的用户友好。其他模型用 UUID 替代。对比 BigQuery（无自增仅 GENERATE_UUID）和 Snowflake（AUTOINCREMENT 不保证连续），Doris 的 AUTO_INCREMENT 限制在特定表模型上是其独特约束。 |
| [数据库/Schema/用户](../ddl/users-databases/doris.md) | **MySQL 协议完全兼容——用 mysql 客户端即可连接**。RBAC 权限模型（GRANT/REVOKE 标准 SQL）。WorkloadGroup 资源组实现多租户 CPU/IO/Memory 隔离。对比 Snowflake（RBAC 最完善+Virtual Warehouse 隔离）和 BigQuery（GCP IAM 无 SQL GRANT），Doris 的 MySQL 协议兼容大幅降低了接入门槛。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/doris.md) | **无存储过程/动态 SQL——MySQL 协议仅作查询入口**。所有过程化逻辑在应用层或调度系统实现。对比 Snowflake（多语言存储过程+EXECUTE IMMEDIATE）和 MaxCompute（Script Mode），Doris 在过程式能力方面与 ClickHouse/StarRocks 同样简陋。 |
| [错误处理](../advanced/error-handling/doris.md) | **无过程式错误处理——查询或导入失败返回错误码和信息**。Stream Load 返回 HTTP 状态码和详细错误 JSON。对比 BigQuery（BEGIN...EXCEPTION）和 Snowflake（EXCEPTION 块），Doris 完全没有 SQL 层的错误处理机制。 |
| [执行计划](../advanced/explain/doris.md) | **EXPLAIN 展示 Fragment/Exchange 分布式执行信息**——可查看数据在 BE 节点间的分发策略（Broadcast/Shuffle/Bucket Shuffle）。Nereids CBO(2.0+)的执行计划比旧优化器更优且信息更丰富。对比 Spark（EXPLAIN EXTENDED 四阶段变换）和 ClickHouse（EXPLAIN PIPELINE 向量化管道），Doris 的 EXPLAIN 侧重分布式 Fragment 划分。 |
| [锁机制](../advanced/locking/doris.md) | **无行级锁——Unique/Primary Key 模型通过 MVCC 版本管理实现并发控制**。每次导入生成新版本，读取时取最新版本。Duplicate/Aggregate 模型追加写入无冲突。对比 Snowflake（乐观并发自动管理）和 PG（行级悲观锁 MVCC），Doris 的并发模型以导入任务为粒度。 |
| [分区](../advanced/partitioning/doris.md) | **PARTITION BY RANGE + DISTRIBUTED BY HASH 双层数据管理——Doris 独有设计**。分区用于时间维度裁剪（如按天/月），分桶用于同节点内数据分布和并行扫描。动态分区(Dynamic Partition)可自动创建和清理分区。对比 BigQuery（单层分区+聚集）和 ClickHouse（PARTITION BY+ORDER BY），Doris 的分区+分桶双层是 MPP 引擎的典型设计（StarRocks 同理）。 |
| [权限](../advanced/permissions/doris.md) | **MySQL 兼容权限模型 + RBAC 角色**——GRANT/REVOKE 语法与 MySQL 完全一致。Row Policy 支持行级过滤。对比 Snowflake（RBAC+DAC+FUTURE GRANTS 最完善）和 BigQuery（GCP IAM），Doris 的权限系统对 MySQL 用户最友好但功能不如 Snowflake。 |
| [存储过程](../advanced/stored-procedures/doris.md) | **无存储过程——OLAP 引擎定位不提供过程式编程**。与 ClickHouse/StarRocks 一样，复杂逻辑在应用层或 Airflow 等调度系统实现。对比 Snowflake（多语言存储过程最强）和 Oracle（PL/SQL 最完善），Doris 完全没有过程式编程能力。 |
| [临时表](../advanced/temp-tables/doris.md) | **无临时表——OLAP 引擎定位下无会话级临时存储需求**。替代方案：CTE（查询级）或建立短生命周期的普通表（需手动清理）。对比 BigQuery（_SESSION 临时表）和 Snowflake（TEMPORARY+TRANSIENT），Doris 缺乏临时表支持。 |
| [事务](../advanced/transactions/doris.md) | **Import 事务原子性——每次 Stream Load/Broker Load 是一个原子操作**。不支持标准 BEGIN/COMMIT/ROLLBACK 多语句事务。多表原子写入需通过 Group Commit(2.1+)或应用层协调。对比 Snowflake（ACID 自动提交）和 PG（完整事务隔离级别），Doris 的事务粒度是单次导入任务。 |
| [触发器](../advanced/triggers/doris.md) | **不支持触发器**——替代方案：物化视图自动刷新（同步/异步）、外部调度系统触发。对比 ClickHouse（物化视图=INSERT 触发器）和 Snowflake（Streams+Tasks），Doris 用物化视图自动路由部分替代了触发器的数据同步需求。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/doris.md) | **DELETE 标准语法(Unique/Primary Key 模型)——Duplicate/Aggregate 模型不支持行级删除**。Batch Delete 通过导入数据时标记删除行实现批量删除。Primary Key Merge-on-Write(2.0+)的删除性能远优于旧 Unique 模型。对比 BigQuery（DELETE 重写整个分区）和 ClickHouse（Lightweight Delete 22.8+），Doris 的删除能力受限于数据模型选择。 |
| [插入](../dml/insert/doris.md) | **Stream Load(HTTP PUT) 是推荐的数据导入方式——支持事务性写入和 exactly-once**。INSERT INTO 适合少量数据，大批量用 Stream Load/Broker Load/Routine Load。Stream Load 支持 JSON/CSV 格式直接推送。对比 BigQuery（批量加载免费）和 Snowflake（COPY INTO+Snowpipe），Doris 的 Stream Load 是最轻量的实时导入方案（纯 HTTP 接口）。 |
| [更新](../dml/update/doris.md) | **UPDATE 仅 Unique/Primary Key 模型支持——Partial Column Update(2.0+)可只更新部分列**。Partial Column Update 避免了全行重写，对宽表场景性能提升显著。Duplicate/Aggregate 模型不支持行级更新。对比 BigQuery/Snowflake（UPDATE 标准）和 ClickHouse（25.7+ 标准 UPDATE），Doris 的 Partial Column Update 是独有的优化。 |
| [Upsert](../dml/upsert/doris.md) | **Unique 模型天然 Upsert——按 Key 列自动替换旧行（INSERT 即 Upsert）**。无需 MERGE 语句，每次 INSERT 按主键覆盖。Primary Key Merge-on-Write(2.0+)写入时即合并，查询无需额外去重。对比 BigQuery/Snowflake（MERGE INTO 标准 SQL）和 ClickHouse（ReplacingMergeTree 合并时去重），Doris 的 Unique 模型使 Upsert 最简单——INSERT 就是 Upsert。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/doris.md) | **GROUPING SETS/CUBE/ROLLUP 完整 + BITMAP_UNION 精确去重是独有优势**。BITMAP 类型存储整数集合的 Roaring Bitmap，BITMAP_UNION 在预聚合模型中实现精确去重计数（对比 HyperLogLog 近似去重更准确）。HLL_UNION 提供近似去重。对比 BigQuery 的 APPROX_COUNT_DISTINCT（HyperLogLog）和 ClickHouse 的 -If/-State 组合后缀，Doris 的 BITMAP 精确去重在广告/用户分析场景中最实用。 |
| [条件函数](../functions/conditional/doris.md) | **IF/CASE/COALESCE/NVL 兼容 MySQL 语法**——行为与 MySQL 完全一致，包括 IF() 函数（非标准 SQL 但 MySQL 常用）。对比 BigQuery 的 SAFE_ 前缀（行级安全）和 Snowflake 的 IFF（简洁条件），Doris 的条件函数完全 MySQL 风格。 |
| [日期函数](../functions/date-functions/doris.md) | **DATE_FORMAT/DATE_ADD/DATEDIFF 兼容 MySQL 命名**——NOW()/CURDATE()/UNIX_TIMESTAMP() 等 MySQL 函数完整支持。DATEV2/DATETIMEV2 是推荐的新日期类型（内部表示更高效）。对比 BigQuery 的 DATE_TRUNC（标准命名）和 Snowflake 的 DATEADD/DATEDIFF（标准命名），Doris 的日期函数对 MySQL 用户零学习成本。 |
| [数学函数](../functions/math-functions/doris.md) | **完整数学函数集（ABS/CEIL/FLOOR/ROUND/POWER 等）**——除零行为与 MySQL 一致（返回 NULL）。对比 BigQuery 的 SAFE_DIVIDE（独有安全除法）和 PG 的除零报错，Doris 继承了 MySQL 的宽松错误处理。 |
| [字符串函数](../functions/string-functions/doris.md) | **CONCAT/SUBSTR/REGEXP 兼容 MySQL 语法**——SPLIT_PART 按位置提取分隔片段。REGEXP_EXTRACT/REGEXP_REPLACE 正则处理。对比 BigQuery 的 SPLIT 返回 ARRAY 和 Snowflake 的 SPLIT_PART（相同语法），Doris 的字符串函数对 MySQL 用户最友好。 |
| [类型转换](../functions/type-conversion/doris.md) | **CAST 标准（MySQL 兼容），隐式转换规则与 MySQL 一致**——字符串到数字的隐式转换行为与 MySQL 相同（可能产生意外结果）。无 TRY_CAST 安全转换函数。对比 BigQuery 的 SAFE_CAST 和 Snowflake 的 TRY_CAST，Doris 缺乏安全转换函数是短板。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/doris.md) | **WITH 标准 + 递归 CTE(2.1+)**——Nereids CBO(2.0+)可对 CTE 做更优的优化决策。2.1 之前不支持递归 CTE，层级查询需多次自连接。对比 PG（长期支持递归 CTE）和 Hive（3.1+ 才支持），Doris 的递归 CTE 引入时间适中。 |
| [全文搜索](../query/full-text-search/doris.md) | **倒排索引(2.0+) 基于 CLucene 实现全文搜索——MATCH_ANY/MATCH_ALL 查询语法**。支持分词、等值过滤和范围过滤加速。可在建表时或事后添加倒排索引。对标 Elasticsearch 的日志分析场景。对比 BigQuery（SEARCH INDEX+SEARCH() 2023+）和 ClickHouse（Bloom Filter 索引轻量但有限），Doris 的倒排索引在 OLAP 引擎中全文搜索能力最强。 |
| [连接查询](../query/joins/doris.md) | **Broadcast/Shuffle/Bucket Shuffle JOIN + Colocate Join 优化**——Colocate Join 将关联表的相同分桶数据放在同一 BE 节点，避免 Shuffle（零网络传输）。Runtime Filter 动态生成 Bloom Filter 下推到扫描侧减少 JOIN 数据量。对比 Spark（AQE 运行时自动切换 JOIN 策略）和 BigQuery（全自动 Broadcast/Shuffle），Doris 的 Colocate Join 是预规划的本地化 JOIN 优化。 |
| [分页](../query/pagination/doris.md) | **LIMIT/OFFSET 完全兼容 MySQL 语法**——MPP 引擎下深度分页（大 OFFSET）性能退化与 MySQL 类似。对比 BigQuery（按扫描量计费不受 OFFSET 影响）和 TiDB（分布式分页需 Keyset 优化），Doris 的分页语法和行为最接近单机 MySQL。 |
| [行列转换](../query/pivot-unpivot/doris.md) | **无原生 PIVOT/UNPIVOT——需 CASE+GROUP BY 手动实现**。LATERAL VIEW EXPLODE(1.2+)支持列转行（ARRAY 展开为多行）。对比 BigQuery/Snowflake 的原生 PIVOT 和 Spark 的 PIVOT/UNPIVOT(3.4+)，Doris 缺乏行转列语法糖。 |
| [集合操作](../query/set-operations/doris.md) | **UNION/INTERSECT/EXCEPT ALL/DISTINCT 完整支持**——语义与标准 SQL 一致。对比 ClickHouse（UNION 默认 DISTINCT）和 Hive（2.0+ 才完整），Doris 的集合操作标准完备。 |
| [子查询](../query/subquery/doris.md) | **IN/EXISTS 子查询完整支持，Nereids CBO(2.0+)优化关联子查询**——Nereids 可将关联子查询去关联化并转为 Semi/Anti Join。对比 Spark（Catalyst 去关联化）和 MySQL 5.x（子查询性能噩梦），Doris 的 Nereids 优化器在子查询优化上追上了主流水平。 |
| [窗口函数](../query/window-functions/doris.md) | **完整窗口函数支持——Pipeline 执行模型+向量化加速**。ROW_NUMBER/RANK/LAG/LEAD/SUM OVER 等全部支持。无 QUALIFY 子句（需子查询包装）。对比 BigQuery/Snowflake 的 QUALIFY 和 ClickHouse（21.1+ 才支持窗口函数），Doris 的窗口函数成熟但缺乏 QUALIFY 扩展。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/doris.md) | **无 generate_series 函数——需预建日期辅助表或在应用层生成**。批量分析场景下通常维护一张日期维表 LEFT JOIN 填充。对比 BigQuery 的 GENERATE_DATE_ARRAY+UNNEST（一行搞定）和 ClickHouse 的 WITH FILL（独有语法），Doris 的日期序列生成最为繁琐。 |
| [去重](../scenarios/deduplication/doris.md) | **Unique 模型天然去重（按 Key 列保留最新行）——存储层去重是独有优势**。ROW_NUMBER+CTE 也可用于查询层去重。Primary Key Merge-on-Write(2.0+)在写入时即去重，查询无需额外处理。对比 ClickHouse（ReplacingMergeTree 合并时去重需 FINAL）和 BigQuery/Snowflake（QUALIFY 查询层去重），Doris 的 Unique 模型去重最彻底（写入即保证唯一）。 |
| [区间检测](../scenarios/gap-detection/doris.md) | **LAG/LEAD 窗口函数检测连续性——标准方案，无独有优化**。对比 ClickHouse 的 WITH FILL（独有语法最简洁）和 PG 的 generate_series+LEFT JOIN，Doris 用通用窗口函数实现。 |
| [层级查询](../scenarios/hierarchical-query/doris.md) | **递归 CTE(2.1+) 支持层级遍历**——2.1 之前需多次自连接或应用层迭代。对比 PG（长期支持递归 CTE）和 Oracle（CONNECT BY 最早），Doris 的递归 CTE 引入时间适中。 |
| [JSON 展开](../scenarios/json-flatten/doris.md) | **JSON_EXTRACT 路径查询 + JSONB 二进制类型(2.1+) + LATERAL VIEW EXPLODE(1.2+)**——JSONB 以二进制格式存储，查询效率远高于字符串解析。倒排索引(2.0+)可加速 JSON 字段过滤。Variant 类型(2.1+)自动推断 Schema 按列存储。对比 Snowflake 的 LATERAL FLATTEN（最优雅）和 ClickHouse 的 Nested（最高效），Doris 的 Variant+倒排索引组合是 JSON 分析的独特方案。 |
| [迁移速查](../scenarios/migration-cheatsheet/doris.md) | **MySQL 协议兼容降低接入门槛，但三大核心差异必须理解**——数据模型选择（Duplicate/Unique/Aggregate/Primary Key）、分区+分桶双层数据管理、无标准事务（Import 事务）。从 MySQL 迁移需要转变思维：建表时就要考虑查询模式。对比 TiDB（MySQL 高度兼容但分布式差异）和 ClickHouse（ENGINE 选择+ORDER BY 布局），Doris 的 MySQL 协议兼容使连接最简单但 DDL 设计差异最大。 |
| [TopN 查询](../scenarios/ranking-top-n/doris.md) | **ROW_NUMBER+窗口函数标准模式——无 QUALIFY 需子查询包装**。简单 TopN 可直接 ORDER BY+LIMIT。对比 BigQuery/Snowflake 的 QUALIFY（最简）和 ClickHouse 的 LIMIT BY（每组限行独有语法），Doris 的 TopN 写法标准但不够简洁。 |
| [累计求和](../scenarios/running-total/doris.md) | **SUM() OVER(ORDER BY ...) 标准窗口累计——MPP 并行加速大数据集**。Pipeline 执行模型和向量化引擎使累计计算高效。对比 BigQuery（Slot 自动扩展）和 ClickHouse（runningAccumulate 状态函数），Doris 的 MPP 并行在累计场景中性能良好。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/doris.md) | **Unique 模型天然 Upsert 替代 MERGE——INSERT 即 Upsert**。SCD Type 1 直接 INSERT 覆盖旧值。SCD Type 2 需要应用层逻辑插入新版本行。无标准 MERGE INTO 语句。对比 BigQuery/Snowflake 的 MERGE INTO（标准 SQL SCD）和 ClickHouse（ReplacingMergeTree 版本字段），Doris 的 SCD 实现最简单（INSERT 即 Upsert）但 Type 2 不够优雅。 |
| [字符串拆分](../scenarios/string-split-to-rows/doris.md) | **EXPLODE_SPLIT+LATERAL VIEW(1.2+) 拆分展开字符串为行**——`LATERAL VIEW EXPLODE_SPLIT(str, ',') t AS val` 是 Doris 独有的组合函数（将 SPLIT+EXPLODE 合为一步）。对比 Snowflake 的 SPLIT_TO_TABLE（最简）和 Hive 的 SPLIT+LATERAL VIEW EXPLODE（两步），Doris 的 EXPLODE_SPLIT 简洁度适中。 |
| [窗口分析](../scenarios/window-analytics/doris.md) | **完整窗口函数+MPP 并行分析——Pipeline 引擎和向量化执行加速**。移动平均、同环比、占比计算均可实现。无 QUALIFY、无 WINDOW 命名子句。对比 BigQuery/Snowflake（QUALIFY+WINDOW 命名子句最强）和 StarRocks（同源但 Pipeline 引擎更新），Doris 的窗口分析性能好但语法扩展不足。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/doris.md) | **ARRAY/MAP/STRUCT(2.0+) + EXPLODE+LATERAL VIEW 展开**——2.0 之前不支持复合类型，这是 Doris 的历史短板。EXPLODE 展开 ARRAY/MAP 为行，配合 LATERAL VIEW 关联原始行。对比 BigQuery 的 STRUCT/ARRAY 一等公民和 Snowflake 的 VARIANT（半结构化），Doris 的复合类型引入较晚但功能在追赶。 |
| [日期时间](../types/datetime/doris.md) | **DATE/DATETIME(微秒精度) + DATEV2/DATETIMEV2(推荐的新内部表示)**——DATEV2 使用更紧凑的内部编码（4 字节 vs 旧版 DATE 的 8 字节），性能更好。无 TIME 类型（纯时间无日期）、无 INTERVAL 类型。对比 BigQuery 的四种时间类型和 Snowflake 的三种 TIMESTAMP，Doris 的日期类型较为简洁但缺少专用的时间和间隔类型。 |
| [JSON](../types/json/doris.md) | **JSON 字符串存储 + JSONB(2.1+) 二进制存储 + 倒排索引加速 JSON 查询**——JSONB 以二进制格式存储，查询效率远高于 JSON 字符串解析。倒排索引可对 JSON 字段建立索引加速过滤。Variant 类型(2.1+)自动推断 Schema 按列存储 JSON 子字段。对比 PG 的 JSONB+GIN 索引（索引最强）和 Snowflake 的 VARIANT（查询最优雅），Doris 的 JSONB+倒排索引组合在日志分析场景中性能优异。 |
| [数值类型](../types/numeric/doris.md) | **TINYINT-LARGEINT(128位) + FLOAT/DOUBLE + DECIMAL(27,9)**——LARGEINT 128 位整数是 Doris 独有的（对比 ClickHouse 的 Int128/Int256 和 PG 最大 BIGINT 64 位）。DECIMAL 最大精度 27 位（对比 BigQuery NUMERIC 38 位和 ClickHouse Decimal256）。对比 BigQuery 的 INT64 单一整数和 ClickHouse 的 Int8-256（最细粒度），Doris 的 LARGEINT 适合存储超大 ID。 |
| [字符串类型](../types/string/doris.md) | **VARCHAR(65533)/CHAR + STRING(2.1+) 无长度限制**——2.1 之前 VARCHAR 最大 65533 字节是重要限制。STRING 类型(2.1+)取消了长度限制。UTF-8 编码。对比 BigQuery 的 STRING（无长度限制极简）和 PG 的 TEXT 无长度限制，Doris 的 STRING 类型引入较晚但解决了 VARCHAR 长度限制问题。 |
