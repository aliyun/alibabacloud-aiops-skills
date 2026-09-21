# CockroachDB

**分类**: 分布式数据库（兼容 PostgreSQL）
**文件数**: 51 个 SQL 文件
**总行数**: 4696 行

> **关键人物**：[Spencer Kimball](../docs/people/cockroachdb-spanner.md)（前 Google, GIMP 创建者）

## 概述与定位

CockroachDB 是 Cockroach Labs 于 2015 年开源的分布式 SQL 数据库，兼容 PostgreSQL 协议和大部分语法。其命名源自蟑螂的生存韧性——设计目标是构建一个"杀不死"的数据库：自动分片、自动故障恢复、跨地域强一致。CockroachDB 定位于需要全球部署、零停机和强一致事务保证的云原生应用场景。

## 历史与演进

- **2014 年**：前 Google 工程师（曾参与 Spanner 项目）创立 Cockroach Labs。
- **2015 年**：项目开源，基于 Go 语言实现，底层存储采用 RocksDB。
- **2017 年**：1.0 GA，支持分布式 ACID 事务和自动负载均衡。
- **2019 年**：19.x 引入 CDC（Change Data Capture）和成本优化器。
- **2020 年**：20.x 推出多区域（Multi-Region）抽象，简化全球部署。
- **2021 年**：21.x 引入 REGIONAL BY ROW 行级地域策略。
- **2022 年**：22.x 切换底层存储引擎为 Pebble（自研 Go LSM 引擎）。
- **2023-2025 年**：23.x/24.x 持续增强 PG 兼容性、物理集群复制、AI 向量能力。

## 核心设计思路

CockroachDB 将数据存储为有序 KV 对，按 Range（默认 512 MB）自动分片。每个 Range 通过 Raft 共识协议维护多副本。事务模型基于 MVCC + 分布式时间戳排序，**默认使用 SERIALIZABLE 隔离级别**（这是其区别于多数分布式数据库的显著特征）。混合逻辑时钟（HLC）提供跨节点的因果一致时间戳。SQL 层兼容 PostgreSQL 线协议，使用基于成本的优化器生成分布式执行计划。

## 独特特色

- **默认 SERIALIZABLE**：开箱即用的最严格隔离级别，避免所有读写异常。
- **unique_rowid()**：内置函数生成全局唯一、大致有序的 ID，替代自增序列避免热点。
- **CHANGEFEED**：原生 CDC 能力，`CREATE CHANGEFEED FOR table INTO 'kafka://...'` 实现实时数据流出。
- **多区域抽象**：`ALTER DATABASE SET PRIMARY REGION`、`REGIONAL BY ROW`、`GLOBAL TABLE` 等声明式地域策略。
- **自动 Range 分裂/合并/再平衡**：无需人工干预分片管理。
- **AS OF SYSTEM TIME**：支持历史时间点读取，用于无锁备份和分析查询。
- **Pebble 存储引擎**：自研 Go 实现的 LSM-Tree 引擎，消除了 CGo 跨语言开销。

## 已知不足

- 严格的 SERIALIZABLE 隔离在高并发写冲突场景下事务重试率较高。
- 与 PostgreSQL 的兼容性虽在持续改进，但存储过程（PL/pgSQL）支持仍在完善阶段。
- 跨地域部署时写延迟受限于多数派提交的 RTT。
- 不支持 PostgreSQL 扩展生态（如 PostGIS 等，需使用内置空间功能）。
- 批量导入性能相比专有分析型数据库有差距。
- 许可证从 Apache 2.0 改为 BSL（Business Source License），影响部分开源使用场景。

## 对引擎开发者的参考价值

CockroachDB 的工程实践展示了如何在分布式环境中实现 SERIALIZABLE 隔离（并发控制与时间戳排序的平衡）、基于 HLC 的分布式时钟方案、以及声明式多区域数据放置的抽象设计。其从 RocksDB 迁移到自研 Pebble 引擎的决策过程也为存储引擎选型提供了重要经验。CHANGEFEED 的实现展示了如何将 CDC 作为数据库原生能力提供。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/cockroachdb.md) | **PG 兼容但 SERIAL 行为不同**——SERIAL 映射到 unique_rowid()（全局唯一大致有序的 64 位 ID），而非 PG 的 SEQUENCE。数据按 Range（默认 512MB）自动分片，无需手动配置。Multi-Region 抽象（REGIONAL BY ROW/GLOBAL TABLE）声明式控制数据地域分布。对比 TiDB 的 AUTO_RANDOM 和 Spanner 的 INTERLEAVE IN PARENT，CockroachDB 的 unique_rowid() 最接近透明替代自增。 |
| [改表](../ddl/alter-table/cockroachdb.md) | **在线 Schema 变更（无锁）**——DDL 以分布式事务方式原子执行，不阻塞读写。ADD/DROP COLUMN、ADD INDEX 等均在线完成。底层通过 Schema 版本化和回填（Backfill）实现。对比 PG 的 CONCURRENTLY 建索引和 TiDB 的 Online DDL，CockroachDB 的 Schema 变更最接近"零停机"但大表回填可能耗时较长。 |
| [索引](../ddl/indexes/cockroachdb.md) | **分布式 LSM（Pebble）索引 + STORING 覆盖列**——STORING 子句将额外列存储在索引中避免回表（等同 PG 的 INCLUDE）。部分索引（21.1+）支持 WHERE 条件过滤。GIN 索引支持 JSONB 和数组查询。对比 PG 的 B-Tree/GIN/GiST 丰富索引类型和 TiDB 的分布式 B-Tree，CockroachDB 的索引种类较少但 STORING 覆盖列在分布式场景下减少跨节点回表。 |
| [约束](../ddl/constraints/cockroachdb.md) | **PK/FK/CHECK/UNIQUE 完整强制执行**——分布式环境下约束通过分布式事务保证一致性。外键约束跨 Range 检查可能增加延迟。对比 TiDB（FK 仅实验性）和 BigQuery（NOT ENFORCED），CockroachDB 是分布式数据库中约束执行最严格的之一。 |
| [视图](../ddl/views/cockroachdb.md) | **普通视图支持，无物化视图**——视图定义存储在系统表中，查询时展开执行。不支持 MATERIALIZED VIEW，分析场景需应用层缓存。对比 PG 的 MATERIALIZED VIEW 和 BigQuery 的自动刷新物化视图，CockroachDB 在物化视图方面是短板。 |
| [序列与自增](../ddl/sequences/cockroachdb.md) | **SERIAL 映射到 unique_rowid()，SEQUENCE 支持但分布式性能差**——SEQUENCE 在分布式环境下需要跨节点协调，可能成为热点。推荐 gen_random_uuid() 或 unique_rowid() 替代。对比 PG 的 SEQUENCE（单机高效）和 Spanner 的 bit-reversed sequence，CockroachDB 在 ID 生成上做了分布式优化但牺牲了连续性。 |
| [数据库/Schema/用户](../ddl/users-databases/cockroachdb.md) | **PG 兼容权限模型 + 多租户 Cluster 级隔离**——Database/Schema/Table 三级命名空间。GRANT/REVOKE/CREATE ROLE 标准 PG 语法。Multi-Tenant 通过 Cluster 级别隔离（非共享存储）。对比 OceanBase 的租户级隔离和 TiDB 的 Resource Control，CockroachDB 的多租户隔离粒度较粗但安全性最高。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/cockroachdb.md) | **PL/pgSQL（23.1+）有限支持**——支持 EXECUTE 动态 SQL 和基本的 PL/pgSQL 控制流。功能仍在完善中，不及 PG 原生 PL/pgSQL 完整。对比 PG 的成熟 PL/pgSQL 和 TiDB（无过程式语言），CockroachDB 在补齐 PG 兼容性的关键缺失。 |
| [错误处理](../advanced/error-handling/cockroachdb.md) | **EXCEPTION WHEN（PG 兼容）+ 自动事务重试**——SERIALIZABLE 隔离下事务冲突返回 40001 错误码，应用需重试。CockroachDB 推荐在 SAVEPOINT cockroach_restart 中包装事务以启用自动重试。对比 TiDB 的悲观模式减少重试和 Spanner 的客户端库自动重试，CockroachDB 的重试机制对应用开发者要求较高。 |
| [执行计划](../advanced/explain/cockroachdb.md) | **EXPLAIN ANALYZE (DISTSQL) 展示分布式执行拓扑**——可看到数据在节点间的流动路径、Range 访问和网络开销。支持 EXPLAIN (VEC) 查看向量化执行计划。对比 PG 的单机 EXPLAIN 和 TiDB 的 cop 算子信息，CockroachDB 的 DISTSQL 计划对分布式性能调优最有价值。 |
| [锁机制](../advanced/locking/cockroachdb.md) | **默认 SERIALIZABLE 隔离——最严格的并发控制**——通过 MVCC + 分布式时间戳排序实现。高并发写冲突场景下事务重试率较高。支持 FOR UPDATE 悲观锁和 SELECT FOR SHARE。无间隙锁（Gap Lock）。对比 TiDB 的 SI 默认隔离和 PG 的 READ COMMITTED 默认，CockroachDB 的 SERIALIZABLE 默认避免了所有读写异常但牺牲了部分并发性能。 |
| [分区](../advanced/partitioning/cockroachdb.md) | **PARTITION BY 实现地理分区（Geo-Partitioning）**——声明式将数据绑定到特定 Region 或 Zone，控制副本放置。REGIONAL BY ROW 按行级别决定数据所在区域。GLOBAL TABLE 将表复制到所有区域加速读取。对比 Spanner 的多区域配置和 TiDB 的 Placement Rules，CockroachDB 的 Multi-Region 抽象最声明化——用 SQL 而非配置文件控制数据分布。 |
| [权限](../advanced/permissions/cockroachdb.md) | **PG 兼容 RBAC + GRANT/REVOKE 标准**——支持 Database/Schema/Table/Column 多级别权限控制。创建用户用 CREATE USER/ROLE 标准语法。对比 TiDB 的 MySQL 兼容权限和 Spanner 的 IAM 权限，CockroachDB 的权限模型对 PG 开发者零学习成本。 |
| [存储过程](../advanced/stored-procedures/cockroachdb.md) | **PL/pgSQL（23.1+）有限支持 + UDF**——支持 CREATE FUNCTION，CREATE PROCEDURE 在较新版本引入。不支持 PG 的所有 PL/pgSQL 特性（如游标、BULK 操作）。对比 PG 的完整 PL/pgSQL 和 OceanBase 的 PL/SQL Package，CockroachDB 的过程式编程能力在快速追赶但仍有差距。 |
| [临时表](../advanced/temp-tables/cockroachdb.md) | **TEMPORARY TABLE 会话级**——临时表数据存储在内存中，会话结束自动清理。对跨节点查询的临时表访问有一定限制。对比 PG 的灵活临时表和 Oracle 的 GTT，CockroachDB 的临时表实现较基础。 |
| [事务](../advanced/transactions/cockroachdb.md) | **分布式 ACID 默认 SERIALIZABLE**——基于 HLC（混合逻辑时钟）+ MVCC 实现。AS OF SYSTEM TIME 支持历史快照读取。每个事务有 timestamp 和 priority，冲突时高优先级事务推进低优先级事务重试。对比 TiDB 的 Percolator SI 和 Spanner 的 TrueTime 外部一致性，CockroachDB 选择了最严格的标准隔离级别作为默认。 |
| [触发器](../advanced/triggers/cockroachdb.md) | **不支持触发器，用 CHANGEFEED（CDC）替代**——`CREATE CHANGEFEED FOR table INTO 'kafka://...'` 原生将数据变更流推送到 Kafka/S3 等外部系统。对比 PG/MySQL 的传统触发器和 Spanner 的 Change Streams，CockroachDB 的 CHANGEFEED 是更现代的事件驱动方案。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/cockroachdb.md) | **DELETE + RETURNING（PG 兼容）**——分布式并行删除跨 Range 自动执行。大批量删除建议使用 DELETE ... LIMIT + 循环避免大事务。RETURNING 子句返回被删除的行。对比 PG 的单机删除和 BigQuery 的分区级 DELETE，CockroachDB 保持了 PG 的 DELETE 语义但需注意分布式事务大小限制。 |
| [插入](../dml/insert/cockroachdb.md) | **INSERT + ON CONFLICT（PG 兼容）+ IMPORT 批量导入**——IMPORT INTO 从 CSV/Parquet 文件批量导入，跳过正常事务路径提升吞吐。ON CONFLICT 支持 DO UPDATE/DO NOTHING。对比 PG 的 COPY 命令和 TiDB 的 Lightning 导入，CockroachDB 的 IMPORT 针对分布式场景优化但文件需可从所有节点访问。 |
| [更新](../dml/update/cockroachdb.md) | **UPDATE + RETURNING（PG 兼容）**——分布式事务保证跨 Range 更新原子性。更新主键值会触发行的跨 Range 迁移。对比 PG 的单机 UPDATE 和 BigQuery（UPDATE 必须带 WHERE），CockroachDB 保持了完整的 PG UPDATE 语义。 |
| [Upsert](../dml/upsert/cockroachdb.md) | **UPSERT 简写 + ON CONFLICT DO UPDATE（PG 兼容）**——CockroachDB 独有的 UPSERT 关键字是 ON CONFLICT DO UPDATE 的简写形式，更简洁。对比 PG 的 ON CONFLICT（需指定冲突列）和 TiDB 的 ON DUPLICATE KEY UPDATE，CockroachDB 的 UPSERT 语法最简洁。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/cockroachdb.md) | **PG 兼容聚合 + 分布式下推**——COUNT/SUM/AVG/string_agg/array_agg 等完整支持。分布式聚合自动拆分为 Partial + Final 两阶段下推到各节点并行执行。对比 PG 的单机聚合和 TiDB 的 TiFlash MPP 聚合，CockroachDB 的分布式聚合透明但无列存加速。 |
| [条件函数](../functions/conditional/cockroachdb.md) | **CASE/COALESCE/NULLIF/IF（PG 兼容）**——IF() 函数是 CockroachDB 的扩展（PG 原生无 IF 函数）。COALESCE/NULLIF 标准 SQL。对比 PG 仅有 CASE/COALESCE 和 MySQL 的 IF/IFNULL，CockroachDB 在 PG 基础上增加了 IF 函数便利性。 |
| [日期函数](../functions/date-functions/cockroachdb.md) | **PG 兼容日期函数 + HLC 时钟保证时序**——date_trunc/extract/age/now() 等完整支持。cluster_logical_timestamp() 返回 HLC 时间戳用于分布式排序。对比 PG 的 now()（单机时钟）和 Spanner 的 TrueTime，CockroachDB 的 HLC 在无需原子钟的情况下提供因果一致的时间戳。 |
| [数学函数](../functions/math-functions/cockroachdb.md) | **PG 兼容数学函数**——ABS/CEIL/FLOOR/ROUND/MOD/POWER 等完整支持。除零行为与 PG 一致（报错而非返回 NULL）。对比 MySQL 的除零返回 NULL 和 BigQuery 的 SAFE_DIVIDE，CockroachDB 遵循 PG 的严格错误处理。 |
| [字符串函数](../functions/string-functions/cockroachdb.md) | **PG 兼容字符串函数 + `\|\|` 拼接**——concat/substring/regexp_replace/split_part 等完整支持。`\|\|` 运算符标准 SQL 拼接。对比 MySQL 的 CONCAT() 函数和 BigQuery 的 SPLIT 返回 ARRAY，CockroachDB 保持了 PG 的字符串处理风格。 |
| [类型转换](../functions/type-conversion/cockroachdb.md) | **CAST/:: 运算符（PG 兼容）+ 严格类型**——类型系统严格，隐式转换少于 MySQL。`::` 运算符是 PG 风格的类型转换简写。对比 MySQL 的宽松隐式转换和 BigQuery 的 SAFE_CAST，CockroachDB 遵循 PG 的严格类型哲学。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/cockroachdb.md) | **递归 CTE 完整支持（PG 兼容）**——WITH RECURSIVE 支持层级查询和序列生成。CTE 可被优化器物化或内联。对比 TiDB（5.1+ CTE）和 PG（CTE 最成熟），CockroachDB 的 CTE 功能与 PG 基本一致。 |
| [全文搜索](../query/full-text-search/cockroachdb.md) | **全文搜索索引（20.2+）+ GIN 索引**——支持 tsvector/tsquery 全文搜索（PG 兼容）。GIN 索引加速 JSONB 和全文搜索查询。对比 PG 的 tsvector+GIN（最成熟）和 TiDB（不支持全文搜索），CockroachDB 在分布式环境下提供了基本的全文搜索能力。 |
| [连接查询](../query/joins/cockroachdb.md) | **Lookup/Hash/Merge JOIN + 分布式自动优化**——优化器自动选择 JOIN 策略。Lookup JOIN 用于小表与大表的键值查找。Hash JOIN 用于大表等值 JOIN。对比 TiDB 的 TiFlash MPP JOIN 和 OceanBase 的 Tablegroup 共置 JOIN，CockroachDB 的 JOIN 优化更依赖优化器的自动决策。 |
| [分页](../query/pagination/cockroachdb.md) | **LIMIT/OFFSET（PG 兼容）+ AS OF SYSTEM TIME 减少锁争用**——深度分页同样有性能问题。AS OF SYSTEM TIME 快照读可避免与写事务的锁冲突，适合分页查询。对比 PG 的单机分页和 BigQuery（按扫描量计费不受分页影响），CockroachDB 的 AS OF SYSTEM TIME 是分布式分页的独特优化。 |
| [行列转换](../query/pivot-unpivot/cockroachdb.md) | **无原生 PIVOT**——需用 CASE+GROUP BY 模拟。与 PG 相同（PG 通过 tablefunc 扩展的 crosstab 支持）。对比 BigQuery/Snowflake 的原生 PIVOT 和 Oracle 的 PIVOT/UNPIVOT，CockroachDB 缺乏行列转换语法糖。 |
| [集合操作](../query/set-operations/cockroachdb.md) | **UNION/INTERSECT/EXCEPT 完整支持（PG 兼容）**——ALL/DISTINCT 修饰符标准。分布式执行时集合操作需要跨节点合并。对比 PG（长期完整支持）和 MySQL 8.0（较晚引入），CockroachDB 继承了 PG 的完整集合操作。 |
| [子查询](../query/subquery/cockroachdb.md) | **关联子查询 + EXISTS/IN（PG 兼容）+ 分布式优化**——优化器可将子查询提升为 JOIN。SERIALIZABLE 隔离保证子查询的一致性快照。对比 PG 的成熟子查询优化和 TiDB 的分布式下推，CockroachDB 的子查询优化受益于其先进的基于成本的优化器。 |
| [窗口函数](../query/window-functions/cockroachdb.md) | **完整窗口函数（PG 兼容）+ 分布式排序**——ROW_NUMBER/RANK/DENSE_RANK/LAG/LEAD/SUM OVER 等全部支持。无 QUALIFY 子句。分布式排序需要跨节点数据传输，大数据量窗口函数有额外开销。对比 PG（单机排序高效）和 BigQuery 的 QUALIFY（简化窗口过滤），CockroachDB 的窗口函数完整但分布式排序是性能关注点。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/cockroachdb.md) | **generate_series（PG 兼容）生成日期序列**——`generate_series('2024-01-01'::DATE, '2024-12-31'::DATE, '1 day')` 一行搞定，与 PG 完全一致。对比 TiDB（需递归 CTE）和 BigQuery 的 GENERATE_DATE_ARRAY，CockroachDB 的 generate_series 是最简洁的日期序列方案之一。 |
| [去重](../scenarios/deduplication/cockroachdb.md) | **ROW_NUMBER+CTE 或 DISTINCT ON（PG 兼容）**——DISTINCT ON 是 PG/CockroachDB 独有的简洁去重语法，无需窗口函数包装。对比 BigQuery 的 QUALIFY 和 TiDB 的 ROW_NUMBER+CTE，CockroachDB 的 DISTINCT ON 在去重场景下更优雅。 |
| [区间检测](../scenarios/gap-detection/cockroachdb.md) | **generate_series + 窗口函数（PG 兼容）**——用 generate_series 生成完整序列后 LEFT JOIN 检测缺失值。对比 TimescaleDB 的 time_bucket_gapfill（原生填充）和 Teradata 的 sys_calendar，CockroachDB 使用 PG 标准方法。 |
| [层级查询](../scenarios/hierarchical-query/cockroachdb.md) | **递归 CTE（PG 兼容）**——WITH RECURSIVE 标准层级遍历。无 Oracle 的 CONNECT BY 语法。递归深度受配置限制。对比 Oracle/达梦的 CONNECT BY 和 PG 的递归 CTE，CockroachDB 采用标准 SQL 方案。 |
| [JSON 展开](../scenarios/json-flatten/cockroachdb.md) | **JSONB + GIN 索引（PG 兼容）+ json_each/json_array_elements**——JSONB 类型支持 GIN 索引加速路径查询。jsonb_array_elements 展开 JSON 数组为行。对比 PG（JSONB 最成熟）和 BigQuery 的 JSON_QUERY_ARRAY+UNNEST，CockroachDB 的 JSON 处理继承了 PG 的完整能力。 |
| [迁移速查](../scenarios/migration-cheatsheet/cockroachdb.md) | **PG 兼容但关键差异在分布式语义**——SERIAL 行为不同（unique_rowid 非 SEQUENCE）、默认 SERIALIZABLE 隔离、事务重试需求、不支持 PG 扩展（如 PostGIS）。对比 YugabyteDB（更深的 PG 兼容，直接 fork PG 查询层）和 TiDB（MySQL 兼容），CockroachDB 的 PG 兼容度高但 SERIALIZABLE 默认对应用影响最大。 |
| [TopN 查询](../scenarios/ranking-top-n/cockroachdb.md) | **ROW_NUMBER/RANK + LIMIT（PG 兼容）**——无 QUALIFY 子句，需子查询包装。分布式 TopN 优化器可将 LIMIT 下推到各节点减少传输。对比 BigQuery/Snowflake 的 QUALIFY 和 Teradata 的 QUALIFY，CockroachDB 需要标准的子查询方式。 |
| [累计求和](../scenarios/running-total/cockroachdb.md) | **SUM() OVER（PG 兼容）+ 分布式窗口函数**——窗口函数需要全局排序，大数据量时跨节点传输可能成为瓶颈。对比 PG 的单机窗口（排序高效）和 BigQuery 的 Slot 自动扩展，CockroachDB 的窗口函数适合中等数据量的 OLTP 场景。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/cockroachdb.md) | **UPSERT 简写方便，无 MERGE 语句**——CockroachDB 的 UPSERT 关键字是最简洁的 SCD Type 1 方案。SCD Type 2 需要多条 SQL 组合。对比 Oracle/BigQuery 的 MERGE INTO（完整 SCD 支持）和 PG 的 ON CONFLICT，CockroachDB 的 UPSERT 语法简洁但缺少 MERGE 的灵活性。 |
| [字符串拆分](../scenarios/string-split-to-rows/cockroachdb.md) | **regexp_split_to_table / string_to_array+unnest（PG 兼容）**——与 PG 完全一致的字符串拆分展开方案。regexp_split_to_table 可直接按正则拆分为行。对比 BigQuery 的 SPLIT+UNNEST 和 TiDB（需递归 CTE），CockroachDB 继承了 PG 的优雅字符串处理。 |
| [窗口分析](../scenarios/window-analytics/cockroachdb.md) | **完整窗口函数（PG 兼容）+ 分布式排序开销需关注**——移动平均、同环比、累计等分析场景完整覆盖。分布式排序在大数据量下可能成为性能瓶颈。对比 PG（单机排序高效）和专用 OLAP 引擎（ClickHouse/Snowflake），CockroachDB 的窗口分析适合 OLTP 规模数据，海量分析场景建议结合 CHANGEFEED 导出到 OLAP 系统。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/cockroachdb.md) | **ARRAY 类型（PG 兼容），无自定义复合类型**——支持 INT[]/TEXT[] 等数组类型和 UNNEST 展开。不支持 PG 的 CREATE TYPE 自定义复合类型。对比 PG 的 ARRAY/COMPOSITE/hstore 和 BigQuery 的 STRUCT/ARRAY，CockroachDB 的复合类型支持介于两者之间。 |
| [日期时间](../types/datetime/cockroachdb.md) | **TIMESTAMP/DATE/TIME/INTERVAL（PG 兼容）+ HLC 分布式时钟**——TIMESTAMPTZ 带时区（推荐）。cluster_logical_timestamp() 返回 HLC 时间用于分布式排序和 AS OF SYSTEM TIME 查询。对比 PG 的 now()（单机时钟）和 Spanner 的 TrueTime（原子钟），CockroachDB 的 HLC 是软件层面的分布式时钟方案。 |
| [JSON](../types/json/cockroachdb.md) | **JSONB + GIN 索引（PG 兼容）+ JSON 路径查询**——JSONB 支持 @>（包含）、->（访问）、->>（文本提取）操作符。GIN 索引加速 JSONB 路径查询。对比 PG 的 JSONB（功能最强）和 BigQuery 的原生 JSON 类型，CockroachDB 的 JSONB 能力继承自 PG 但部分高级操作可能有差异。 |
| [数值类型](../types/numeric/cockroachdb.md) | **INT/FLOAT/DECIMAL（PG 兼容），无 UNSIGNED**——INT 默认为 INT8（64 位），不同于 PG 的 INT 默认 INT4（32 位）。DECIMAL 精度最高 38 位。不支持 MySQL 的 UNSIGNED 修饰符。对比 PG 的 INT4 默认和 BigQuery 的 INT64 唯一整数类型，CockroachDB 的 INT 默认宽度差异需注意。 |
| [字符串类型](../types/string/cockroachdb.md) | **STRING/VARCHAR/TEXT（PG 兼容），UTF-8 默认**——STRING 是 CockroachDB 推荐的字符串类型（等同 TEXT）。不支持 PG 的 CHAR 定长类型的填充行为。UTF-8 是唯一支持的编码。对比 PG 的 TEXT/VARCHAR/CHAR 和 MySQL 的 utf8mb4 字符集体系，CockroachDB 的字符串类型更简洁。 |
