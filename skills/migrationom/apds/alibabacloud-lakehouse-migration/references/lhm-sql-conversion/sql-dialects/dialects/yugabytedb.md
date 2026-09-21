# YugabyteDB

**分类**: 分布式数据库（兼容 PostgreSQL）
**文件数**: 51 个 SQL 文件
**总行数**: 4726 行

## 概述与定位

YugabyteDB 是 Yugabyte 公司于 2017 年开源的分布式 SQL 数据库，核心设计目标是提供与 PostgreSQL 完全兼容的分布式数据库体验。它采用 Google Spanner 的分布式架构理念，同时复用 PostgreSQL 的查询层代码实现高度 PG 兼容。YugabyteDB 定位于需要水平扩展、高可用和全球分布的 OLTP 应用，特别适合从单机 PostgreSQL 向分布式架构迁移的场景。

## 历史与演进

- **2016 年**：前 Facebook 和 Oracle 工程师创立 Yugabyte 公司。
- **2017 年**：YugabyteDB 开源，初期仅提供 Cassandra 兼容的 YCQL API。
- **2018 年**：引入 YSQL API，直接集成 PostgreSQL 查询层实现 SQL 兼容。
- **2019 年**：2.0 GA，YSQL 基于 PG 11 fork 实现全面 SQL 支持。
- **2021 年**：2.8+ 引入跨地域部署增强和读副本（Read Replica）。
- **2022 年**：升级到 PG 11.2 兼容层，增强 xCluster 异步复制。
- **2023-2024 年**：基于 PG 15 的查询层升级，增强连接管理和性能优化。
- **2025 年**：持续推进 PG 兼容性和 YugabyteDB Anywhere/Managed 云服务。

## 核心设计思路

YugabyteDB 采用两层架构：**YB-TServer**（Tablet Server）管理数据存储，**YB-Master** 管理元数据和集群协调。数据按表分成多个 **Tablet**（类似 Spanner 的 Split），每个 Tablet 通过 Raft 共识协议维护多副本。存储层使用 DocDB（基于 RocksDB 改造的文档存储引擎），支持 MVCC 和分布式事务。独特之处在于提供**双 API**：YSQL（兼容 PostgreSQL）和 YCQL（兼容 Cassandra Query Language），共享同一底层存储引擎。

## 独特特色

- **YSQL/YCQL 双 API**：同一集群通过不同端口同时提供 PostgreSQL 兼容和 Cassandra 兼容接口。
- **哈希分片 + Range 分片**：默认使用哈希分片均匀分布数据，也支持 Range 分片用于范围查询优化。
- **Tablet 分裂与合并**：数据增长时 Tablet 自动分裂，支持手动和自动触发。
- **高度 PG 兼容**：直接复用 PostgreSQL 查询层代码，支持 PG 扩展、存储过程、触发器。
- **Colocated Tables**：`CREATE DATABASE ... WITH COLOCATED = true` 将小表共置于单一 Tablet 减少开销。
- **xCluster 复制**：跨集群异步复制用于异地灾备和读扩展。
- **地理分区**：`TABLESPACE` 机制控制数据的地域放置。

## 已知不足

- 哈希分片默认策略下范围查询（如 `BETWEEN`、`ORDER BY` 主键）性能不如 Range 分片。
- 与 PostgreSQL 的兼容虽高但并非 100%，部分扩展和高级特性可能不支持。
- YCQL API 功能更新速度慢于 YSQL，部分用户反馈 YCQL 的定位逐渐模糊。
- 分布式事务在高冲突场景下延迟高于单机 PostgreSQL。
- 集群最小部署需要 3 节点，对小规模应用有一定门槛。
- 全局二级索引在分布式场景下的性能开销需要关注。

## 对引擎开发者的参考价值

YugabyteDB 展示了如何通过 fork PostgreSQL 查询层快速获得 SQL 兼容性，同时将存储引擎替换为分布式方案的工程策略。其双 API 设计（SQL + NoSQL 共享存储）是多模数据库架构的有益探索。Tablet 的哈希 vs Range 分片选择、Colocated Tables 的小表优化策略、以及 DocDB 存储引擎的设计对分布式存储开发者有直接参考意义。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/yugabytedb.md) | **PG 兼容语法 + HASH/RANGE 分片选择**——默认使用哈希分片（均匀分布数据），可显式指定 `ASC/DESC` 创建 Range 分片（优化范围查询）。**Colocated Tables** 将小表共置于单一 Tablet 减少分布式开销。DocDB 存储引擎（基于 RocksDB）替换了 PG 的 Heap 存储。对比 PostgreSQL（单机 Heap 存储）和 CockroachDB（Range 分片默认），YugabyteDB 的哈希分片在写入均衡上更优但范围扫描需额外规划。 |
| [改表](../ddl/alter-table/yugabytedb.md) | **PG 兼容 ALTER + 在线 Schema 变更**——DDL 在分布式集群上协调执行。ADD COLUMN 对分布式表透明扩展。对比 PostgreSQL（单机 DDL 事务性）和 CockroachDB（在线 Schema 变更），YugabyteDB 的分布式 DDL 对应用透明。 |
| [索引](../ddl/indexes/yugabytedb.md) | **LSM 分布式索引（PG 兼容语法）+ COVERING（=INCLUDE）**——索引存储在 DocDB 的 LSM-Tree 中（非 PG 的 B-tree），COVERING INDEX 将额外列存入索引避免回表查询。对比 PostgreSQL 的 B-tree INCLUDE（PG 11+，功能类似）和 CockroachDB（类似 LSM 索引），YugabyteDB 的 COVERING INDEX 是分布式场景下减少网络往返的关键优化。 |
| [约束](../ddl/constraints/yugabytedb.md) | **PK/FK/CHECK/UNIQUE 分布式强一致**——约束在所有 Tablet 副本上通过 Raft 一致性保证。外键约束跨 Tablet 时通过分布式事务校验。对比 PostgreSQL（单机约束校验）和 BigQuery（NOT ENFORCED 约束），YugabyteDB 在分布式场景下真正执行约束，保证数据完整性。 |
| [视图](../ddl/views/yugabytedb.md) | **普通视图 + 物化视图（PG 兼容）**——物化视图 REFRESH 在分布式集群上执行。对比 PostgreSQL（物化视图原生）和 CockroachDB（无物化视图），YugabyteDB 的物化视图能力继承 PG。 |
| [序列与自增](../ddl/sequences/yugabytedb.md) | **SERIAL/IDENTITY/SEQUENCE（PG 兼容）+ 分布式序列**——序列值通过 YB-Master 集中管理，保证全局唯一但可能有性能热点。`ysql_sequence_cache_method` 参数可调整缓存策略。对比 PostgreSQL（单机序列高效）和 Spanner（bit-reversed sequence 避免热点），YugabyteDB 的序列在高并发场景下需关注缓存配置。 |
| [数据库/Schema/用户](../ddl/users-databases/yugabytedb.md) | **PG 兼容权限模型 + Tablet Server 集群管理**——数据库和 Schema 命名空间与 PG 一致，权限通过 GRANT/REVOKE 管理。YCQL API 使用独立的 Keyspace/Table 命名空间。对比 PostgreSQL（单机权限管理）和 CockroachDB（分布式权限），YugabyteDB 的双 API 意味着两套命名空间体系共存。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/yugabytedb.md) | **EXECUTE（PL/pgSQL 兼容）**——存储过程内动态 SQL 通过 PG 查询层执行，DocDB 存储层透明处理分布式路由。对比 PostgreSQL（EXECUTE 原生）和 CockroachDB（PL/pgSQL 部分支持），YugabyteDB 的动态 SQL 能力继承 PG。 |
| [错误处理](../advanced/error-handling/yugabytedb.md) | **EXCEPTION WHEN（PL/pgSQL 兼容）**——分布式事务中的异常捕获可能涉及跨 Tablet 回滚。对比 PostgreSQL（单机异常处理）和 CockroachDB（PL/pgSQL 部分支持），YugabyteDB 的错误处理继承 PG 但分布式事务异常语义需关注。 |
| [执行计划](../advanced/explain/yugabytedb.md) | **EXPLAIN ANALYZE（PG 兼容）+ Dist 分布式信息**——执行计划中显示 Tablet 扫描范围、网络往返次数和 DocDB 读写统计。对比 PostgreSQL（单机 EXPLAIN ANALYZE）和 CockroachDB（分布式 EXPLAIN），YugabyteDB 的执行计划额外展示分布式层信息，帮助识别跨 Tablet 查询瓶颈。 |
| [锁机制](../advanced/locking/yugabytedb.md) | **行级锁 + 分布式锁（Raft 一致性）+ Wait-on-Conflict（2.20+）**——Wait-on-Conflict 模式下冲突事务排队等待而非立即中止，减少事务重试。对比 PostgreSQL（行级锁 + MVCC）和 CockroachDB（乐观并发 + 重试），YugabyteDB 的 Wait-on-Conflict 是对分布式锁冲突处理的重要改进。 |
| [分区](../advanced/partitioning/yugabytedb.md) | **PARTITION BY（PG 兼容）+ SPLIT INTO TABLETS 分片**——PG 声明式分区用于逻辑分区，SPLIT INTO N TABLETS 控制物理分片数量。对比 PostgreSQL（仅逻辑分区）和 CockroachDB（自动分片），YugabyteDB 提供逻辑分区和物理分片的双层控制。 |
| [权限](../advanced/permissions/yugabytedb.md) | **PG 兼容 RBAC + 行级安全（RLS）**——RLS 策略在分布式场景下在各 Tablet 本地执行。对比 PostgreSQL（RLS 原生）和 CockroachDB（无 RLS），YugabyteDB 继承了 PG 的行级安全能力。 |
| [存储过程](../advanced/stored-procedures/yugabytedb.md) | **PL/pgSQL（PG 兼容）**——存储过程在 YSQL 查询层执行，数据访问透明路由到 DocDB。对比 PostgreSQL（PL/pgSQL 完整）和 CockroachDB（PL/pgSQL 部分支持），YugabyteDB 的存储过程兼容度紧随 PG 内核版本。 |
| [临时表](../advanced/temp-tables/yugabytedb.md) | **TEMPORARY TABLE（PG 兼容）**——临时表存储在本地 TServer 而非分布式 DocDB，访问速度更快。对比 PostgreSQL（临时表在本地）和 CockroachDB（临时表支持），YugabyteDB 的临时表设计避免了分布式开销。 |
| [事务](../advanced/transactions/yugabytedb.md) | **分布式 ACID（Raft + MVCC）+ Snapshot/Serializable 隔离**——Snapshot Isolation（默认）使用混合时间戳（Hybrid Time）保证跨 Tablet 一致读。Serializable 使用悲观锁避免写偏斜。对比 PostgreSQL（单机 MVCC）和 Spanner（TrueTime 外部一致性），YugabyteDB 的混合时间戳是无需原子钟的分布式一致性方案。 |
| [触发器](../advanced/triggers/yugabytedb.md) | **PG 兼容触发器**——触发器在 YSQL 查询层执行，跨 Tablet 数据操作时触发器行为与单机 PG 一致。对比 PostgreSQL（触发器完整）和 CockroachDB（触发器有限支持），YugabyteDB 的触发器兼容度继承 PG。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/yugabytedb.md) | **DELETE ... RETURNING（PG 兼容）+ 分布式并行**——DELETE 在相关 Tablet 上并行执行。DocDB 使用墓碑标记（tombstone）删除数据，后台压缩时清理。对比 PostgreSQL（DELETE 产生死元组需 VACUUM）和 CockroachDB（类似 LSM tombstone），YugabyteDB 的删除机制由 LSM 压缩处理回收。 |
| [插入](../dml/insert/yugabytedb.md) | **INSERT ... RETURNING + ON CONFLICT（PG 兼容）**——INSERT 根据主键哈希自动路由到目标 Tablet。批量 INSERT 按主键分组并行写入不同 Tablet。对比 PostgreSQL（单机 INSERT）和 CockroachDB（类似分布式 INSERT），YugabyteDB 的 INSERT 路由对应用透明。 |
| [更新](../dml/update/yugabytedb.md) | **UPDATE ... RETURNING（PG 兼容）+ 分布式事务**——UPDATE 在 DocDB 中是删除旧版本 + 插入新版本的操作（LSM 特性）。跨 Tablet UPDATE 通过分布式事务保证一致性。对比 PostgreSQL（行内更新或 HOT 更新）和 CockroachDB（类似 LSM 更新），YugabyteDB 的 UPDATE 语义由 DocDB 的 LSM 存储决定。 |
| [Upsert](../dml/upsert/yugabytedb.md) | **ON CONFLICT（PG 兼容）+ 分布式 Upsert**——ON CONFLICT 在目标 Tablet 上原子执行。分布式场景下冲突检测在单个 Tablet 内完成（主键/唯一约束保证在同一 Tablet）。对比 PostgreSQL（ON CONFLICT 原生）和 CockroachDB（类似 ON CONFLICT），YugabyteDB 的 Upsert 利用哈希分片的局部性优化冲突检测。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/yugabytedb.md) | **PG 兼容聚合 + 分布式聚合下推**——SUM/COUNT/AVG 等聚合可下推到各 Tablet 执行，YSQL 层合并中间结果。string_agg/FILTER 子句均可用。对比 PostgreSQL（单机聚合）和 CockroachDB（分布式聚合），YugabyteDB 的聚合下推减少网络数据传输。 |
| [条件函数](../functions/conditional/yugabytedb.md) | **CASE/COALESCE/NULLIF（PG 兼容）**——条件函数在各 Tablet 本地执行，无分布式特殊行为。对比 PostgreSQL（相同函数）和 MySQL 的 IF（YugabyteDB 无 IF 函数），YSQL 的条件函数与 PG 完全一致。 |
| [日期函数](../functions/date-functions/yugabytedb.md) | **PG 兼容日期函数**——date_trunc/extract/age/INTERVAL 算术完整支持。对比 PostgreSQL（相同函数集）和 MySQL（不同命名），YugabyteDB 日期函数与 PG 一致。 |
| [数学函数](../functions/math-functions/yugabytedb.md) | **PG 兼容数学函数**——完整数学函数集，在各 Tablet 本地执行。对比 PostgreSQL（相同函数集）和 MySQL（函数名微差），YugabyteDB 数学函数与 PG 一致。 |
| [字符串函数](../functions/string-functions/yugabytedb.md) | **PG 兼容字符串函数 + \|\| 拼接**——substring/position/overlay/trim 等标准函数。对比 PostgreSQL（相同函数集）和 MySQL（CONCAT 函数为主），YugabyteDB 字符串处理与 PG 一致。 |
| [类型转换](../functions/type-conversion/yugabytedb.md) | **CAST/:: 运算符（PG 兼容）**——PG 风格的 `col::integer` 简洁转换。对比 PostgreSQL（:: 运算符原生）和 MySQL（CAST/CONVERT），YugabyteDB 的类型转换与 PG 完全一致。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/yugabytedb.md) | **WITH + 递归 CTE（PG 兼容）**——递归 CTE 在 YSQL 层执行，每次迭代可能涉及跨 Tablet 数据访问。对比 PostgreSQL（单机递归 CTE）和 CockroachDB（分布式递归 CTE），YugabyteDB 的 CTE 能力继承 PG。 |
| [全文搜索](../query/full-text-search/yugabytedb.md) | **tsvector/tsquery + GIN 索引（PG 兼容）**——GIN 索引在 DocDB LSM 存储上实现，全文搜索在各 Tablet 本地执行后合并结果。对比 PostgreSQL（tsvector+GIN 最成熟）和 Elasticsearch（专用搜索引擎），YugabyteDB 的全文搜索继承 PG 能力并分布式化。 |
| [连接查询](../query/joins/yugabytedb.md) | **PG 兼容 JOIN + Batched Nested Loop 分布式优化**——Batched NL 将多个行的查找合并为一次批量请求减少 RPC 往返。相同分片键的表 JOIN 可在 Tablet 内本地完成（Colocated Tables 进一步优化小表 JOIN）。对比 PostgreSQL（单机 JOIN 无 RPC 开销）和 CockroachDB（类似分布式 JOIN），YugabyteDB 的 Batched NL 是对分布式 Nested Loop JOIN 的关键优化。 |
| [分页](../query/pagination/yugabytedb.md) | **LIMIT/OFFSET（PG 兼容）+ Keyset 分页推荐**——分布式场景下 OFFSET 深度分页性能退化（需跨 Tablet 排序和跳过），推荐使用 `WHERE id > last_id ORDER BY id LIMIT N` 的 Keyset 分页。对比 PostgreSQL（单机 OFFSET 性能尚可）和 CockroachDB（同样推荐 Keyset），Keyset 分页在分布式数据库中是通用最佳实践。 |
| [行列转换](../query/pivot-unpivot/yugabytedb.md) | **crosstab（PG 兼容 tablefunc）**——通过 tablefunc 扩展实现行列转换。对比 PostgreSQL（需安装 tablefunc）和 Oracle（PIVOT 原生），YugabyteDB 与 PG 方案一致。 |
| [集合操作](../query/set-operations/yugabytedb.md) | **UNION/INTERSECT/EXCEPT（PG 兼容）**——集合操作在 YSQL 层合并各 Tablet 结果。对比 PostgreSQL（单机集合操作）和 CockroachDB（分布式集合操作），YugabyteDB 的集合操作语义与 PG 一致。 |
| [子查询](../query/subquery/yugabytedb.md) | **关联子查询（PG 兼容）+ 分布式优化**——YSQL 优化器继承 PG 的子查询展开能力。分布式场景下子查询可能涉及跨 Tablet 数据访问。对比 PostgreSQL（优化器成熟）和 CockroachDB（分布式优化器），YugabyteDB 的子查询优化随 PG 内核版本升级而增强。 |
| [窗口函数](../query/window-functions/yugabytedb.md) | **完整窗口函数（PG 兼容）**——分布式场景下窗口函数可能需要将数据汇聚到单节点排序。对比 PostgreSQL（单机窗口函数高效）和 CockroachDB（分布式窗口函数），YugabyteDB 的窗口函数在大数据量跨 Tablet 排序时需关注性能。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/yugabytedb.md) | **generate_series（PG 兼容）**——方案与 PostgreSQL 完全一致。generate_series 在 YSQL 层本地执行。对比 PostgreSQL（generate_series 原生）和 BigQuery（GENERATE_DATE_ARRAY），YugabyteDB 继承 PG 的日期生成方式。 |
| [去重](../scenarios/deduplication/yugabytedb.md) | **DISTINCT ON / ROW_NUMBER（PG 兼容）**——DISTINCT ON 是 PG 独有的简洁去重语法。分布式场景下 DISTINCT ON 可能需要全局排序。对比 PostgreSQL（DISTINCT ON 高效）和 MySQL（无 DISTINCT ON），YugabyteDB 继承 PG 特性但需关注分布式排序开销。 |
| [区间检测](../scenarios/gap-detection/yugabytedb.md) | **generate_series + 窗口函数（PG 兼容）**——方案与 PostgreSQL 一致。对比 PostgreSQL（相同方案）和 Oracle（CONNECT BY 生成序列），YugabyteDB 的间隙检测方案继承 PG。 |
| [层级查询](../scenarios/hierarchical-query/yugabytedb.md) | **递归 CTE（PG 兼容）**——分布式场景下递归查询每次迭代可能涉及跨 Tablet 数据访问，深层递归性能需关注。对比 PostgreSQL（单机递归 CTE 高效）和 Oracle（CONNECT BY + 递归 CTE），YugabyteDB 在层级查询上继承 PG 能力。 |
| [JSON 展开](../scenarios/json-flatten/yugabytedb.md) | **json_each/json_array_elements（PG 兼容）**——JSONB + GIN 索引可在分布式场景下高效查询 JSON 数据。对比 PostgreSQL（JSONB+GIN 最成熟）和 MySQL 的 JSON_TABLE，YugabyteDB 继承 PG 的 JSONB 能力。 |
| [迁移速查](../scenarios/migration-cheatsheet/yugabytedb.md) | **PG 高度兼容是基础，分布式分片 + Raft 一致性是核心差异**。关键注意：哈希分片默认下范围查询需要扫描所有 Tablet；Colocated Tables 优化小表 JOIN；全局二级索引有网络开销；序列在高并发下需调整缓存；YCQL API 适合 Cassandra 场景但功能更新慢于 YSQL。 |
| [TopN 查询](../scenarios/ranking-top-n/yugabytedb.md) | **ROW_NUMBER + LIMIT（PG 兼容）**——分布式 TopN 需要全局排序。哈希分片下 ORDER BY 主键的 TopN 需要跨所有 Tablet 排序。对比 PostgreSQL（单机 TopN 高效）和 BigQuery（QUALIFY 更简洁），YugabyteDB 的 TopN 在分布式场景下需关注排序开销。 |
| [累计求和](../scenarios/running-total/yugabytedb.md) | **SUM() OVER(ORDER BY ...)（PG 兼容）**——窗口累计在分布式场景下可能需要全局排序。对比 PostgreSQL（单机窗口函数高效）和各主流引擎（写法一致），YugabyteDB 需关注跨 Tablet 排序开销。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/yugabytedb.md) | **ON CONFLICT（PG 兼容）**——分布式 Upsert 在目标 Tablet 上原子执行。对比 PostgreSQL（ON CONFLICT 原生）和 Oracle（MERGE），YugabyteDB 的 Upsert 利用哈希分片的局部性。 |
| [字符串拆分](../scenarios/string-split-to-rows/yugabytedb.md) | **string_to_array + unnest（PG 兼容）**——方案与 PostgreSQL 一致。对比 PostgreSQL（相同方案）和 BigQuery 的 SPLIT+UNNEST，YugabyteDB 继承 PG 的拆分方式。 |
| [窗口分析](../scenarios/window-analytics/yugabytedb.md) | **完整窗口函数（PG 兼容）+ 分布式排序**——移动平均、占比等分析场景全覆盖。大数据量窗口分析可能涉及跨 Tablet 数据汇聚和排序。对比 PostgreSQL（单机窗口函数高效）和 CockroachDB（类似分布式限制），YugabyteDB 的窗口分析功能完整但需关注分布式排序开销。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/yugabytedb.md) | **ARRAY / 复合类型（PG 兼容）**——支持数组列和 CREATE TYPE 复合类型。DocDB 以文档格式存储复合类型。对比 PostgreSQL（ARRAY 原生核心特性）和 MySQL（无 ARRAY），YugabyteDB 继承 PG 类型系统灵活性。 |
| [日期时间](../types/datetime/yugabytedb.md) | **DATE/TIMESTAMP/TIMESTAMPTZ/INTERVAL（PG 兼容）**——TIMESTAMPTZ 在分布式场景下基于 Hybrid Time 保证全局一致的时间戳排序。对比 PostgreSQL（TIMESTAMPTZ 标准）和 Spanner（TrueTime 时间戳），YugabyteDB 的 Hybrid Time 是无原子钟环境下的分布式时间方案。 |
| [JSON](../types/json/yugabytedb.md) | **JSON/JSONB + GIN 索引（PG 兼容）**——JSONB 在 DocDB 中以文档格式存储，GIN 索引在 LSM 存储上实现。对比 PostgreSQL（JSONB+GIN 最成熟）和 CockroachDB（类似 JSONB 支持），YugabyteDB 的 JSONB 能力继承 PG 并分布式化。 |
| [数值类型](../types/numeric/yugabytedb.md) | **INT/BIGINT/NUMERIC/FLOAT（PG 兼容）**——标准数值类型体系。DocDB 存储层对定长类型有编码优化。对比 PostgreSQL（相同类型体系）和 MySQL（UNSIGNED 类型），YugabyteDB 数值类型与 PG 完全一致。 |
| [字符串类型](../types/string/yugabytedb.md) | **TEXT/VARCHAR（PG 兼容）+ UTF-8**——TEXT 无长度限制，VARCHAR(n) 指定最大长度。对比 PostgreSQL（TEXT 推荐）和 MySQL（utf8mb4 推荐），YugabyteDB 字符串类型与 PG 一致。 |
