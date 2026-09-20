# TDSQL

**分类**: 分布式数据库（腾讯云，兼容 MySQL）
**文件数**: 51 个 SQL 文件
**总行数**: 6083 行

## 概述与定位

TDSQL 是腾讯云自主研发的分布式数据库，兼容 MySQL 协议和语法，定位于金融、政务等对数据一致性和高可用要求极高的核心业务场景。TDSQL 脱胎于腾讯内部的分布式数据库实践，已在微信支付、腾讯金融等业务中大规模验证。它提供自动分片、分布式事务和强同步复制能力，支持从单机 MySQL 平滑迁移到分布式架构。

## 历史与演进

- **2007 年**：腾讯内部开始分布式数据库研发，服务于 QQ 和财付通等业务。
- **2014 年**：TDSQL 金融级分布式版本在微信支付上线。
- **2017 年**：作为腾讯云产品对外发布，服务外部金融客户。
- **2019 年**：推出 TDSQL-C（云原生版本，类 Aurora 架构）。
- **2020 年**：引入 Oracle 兼容模式（TDSQL PG 版）。
- **2022 年**：TDSQL 金融版通过多项金融行业认证。
- **2023-2025 年**：统一品牌为 TDSQL，持续增强分布式能力和多模兼容。

## 核心设计思路

TDSQL 分布式版采用 Shared-Nothing 架构，由三个核心组件构成：**SQL 引擎（Proxy）** 负责 SQL 解析、路由和分布式事务协调；**数据节点（SET）** 是 MySQL 实例组，每组通过强同步（半同步增强）复制保证数据不丢失；**管理节点** 负责集群调度。数据通过 **shardkey** 进行水平拆分，SQL 引擎透明地将查询路由到正确的数据节点。分布式事务基于两阶段提交（2PC）+ 全局时间戳实现。

## 独特特色

- **shardkey 分片**：建表时通过 `shardkey = column` 指定分片键，透明水平拆分。
- **广播表**：`CREATE TABLE t (...) shardkey=noshardkey_allset` 将小维度表复制到所有节点，优化 JOIN 性能。
- **强同步复制**：基于 MySQL 半同步改进，保证主备切换时 RPO=0。
- **分布式事务**：跨 SET 事务使用 2PC 保证 ACID，对应用透明。
- **全局唯一字段 (auto_increment)**：分布式场景下保证自增 ID 全局唯一（但不保证连续）。
- **TDSQL-C 云原生版**：计算存储分离的云原生架构，类似 Aurora，支持秒级扩缩容。
- **SQL 审计与合规**：内置完整的 SQL 审计日志和操作审计。

## 已知不足

- 分片表的跨分片 JOIN 和聚合查询性能受限，需要合理设计 shardkey。
- 非分片键查询需要广播到所有节点，性能退化明显。
- 与 MySQL 的兼容性在分布式特性（如全局 AUTO_INCREMENT、跨分片外键）上存在限制。
- 部分 MySQL 存储过程和触发器在分布式场景下行为可能不同。
- 仅在腾讯云上以托管服务方式提供，无法私有化部署开源版。
- 分布式版的运维复杂度高于单机 MySQL，需要理解分片和路由机制。

## 对引擎开发者的参考价值

TDSQL 展示了基于 MySQL 生态构建分布式数据库的工程路径：SQL Proxy 透明路由层的设计、shardkey 分片策略与广播表的组合优化、以及强同步复制在金融场景的实践。其从中间件模式（分库分表）演进到统一分布式数据库的历程，对理解分布式数据库架构演进有参考意义。TDSQL-C 的存算分离设计则展示了另一条云原生路径。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/tdsql.md) | **MySQL 兼容 + shardkey 分片键指定**——`CREATE TABLE t (...) shardkey=user_id` 透明水平拆分数据到多个 SET 节点。**广播表**通过 `shardkey=noshardkey_allset` 将小维度表复制到所有节点以优化 JOIN。对比 MySQL（单机建表）和 YugabyteDB（哈希分片自动），TDSQL 的 shardkey 设计让开发者显式控制数据分布。 |
| [改表](../ddl/alter-table/tdsql.md) | **Online DDL（MySQL 兼容）+ 分布式 DDL 原子性**——DDL 变更在所有 SET 节点上原子执行，避免部分节点变更成功部分失败的不一致。对比 MySQL（单机 Online DDL）和 CockroachDB（分布式 DDL 原生），TDSQL 在分布式 DDL 一致性上有专门保障。 |
| [索引](../ddl/indexes/tdsql.md) | **InnoDB B-tree 索引（MySQL 兼容）+ 全局二级索引**——全局二级索引跨所有分片维护，支持非 shardkey 列的高效查询。对比 MySQL（单机索引）和 YugabyteDB（分布式 LSM 索引），TDSQL 的全局二级索引解决了分布式场景下非分片键查询的性能问题。 |
| [约束](../ddl/constraints/tdsql.md) | **PK/FK/CHECK（MySQL 兼容），分布式约束有限制**——主键必须包含 shardkey（确保分片内唯一性），跨分片外键不支持。对比 MySQL（约束无限制）和 YugabyteDB（分布式约束强一致），TDSQL 在约束设计上权衡了分布式一致性与性能。 |
| [视图](../ddl/views/tdsql.md) | **MySQL 兼容视图**——视图查询透明路由到相关分片。对比 MySQL（单机视图）和 BigQuery（物化视图自动增量刷新），TDSQL 视图功能与 MySQL 一致，无物化视图支持。 |
| [序列与自增](../ddl/sequences/tdsql.md) | **AUTO_INCREMENT + 分布式全局唯一自增**——通过全局 ID 生成服务保证跨分片的自增 ID 全局唯一（不保证连续）。对比 MySQL 主从（需 auto_increment_offset 避免冲突）和 Spanner（bit-reversed sequence 避免热点），TDSQL 的全局自增在金融场景下经过大规模验证。 |
| [数据库/Schema/用户](../ddl/users-databases/tdsql.md) | **MySQL 兼容权限 + 分片实例管理**——权限在 Proxy 层统一管理，用户对分片透明。对比 MySQL（单机权限）和 CockroachDB（分布式权限原生），TDSQL 通过 SQL Proxy 层实现权限的集中管控。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/tdsql.md) | **PREPARE/EXECUTE（MySQL 兼容）**——Proxy 层自动将动态 SQL 路由到正确的分片。对比 MySQL（单机 PREPARE/EXECUTE）和 PostgreSQL 的 EXECUTE（PL/pgSQL），TDSQL 的动态 SQL 在分布式场景下透明执行。 |
| [错误处理](../advanced/error-handling/tdsql.md) | **DECLARE HANDLER（MySQL 兼容）**——存储过程内的错误处理。注意：分布式场景下跨分片错误的回滚行为可能与单机 MySQL 有差异。对比 MySQL（单机错误处理）和 PostgreSQL 的 EXCEPTION WHEN（PL/pgSQL），TDSQL 的错误处理与 MySQL 一致。 |
| [执行计划](../advanced/explain/tdsql.md) | **EXPLAIN（MySQL 兼容）+ 分布式执行计划展示**——显示查询在 Proxy 层的路由决策和各 SET 节点的执行计划。对比 MySQL（单机 EXPLAIN）和 CockroachDB（分布式 EXPLAIN），TDSQL 的分布式执行计划帮助识别跨分片查询的性能瓶颈。 |
| [锁机制](../advanced/locking/tdsql.md) | **InnoDB 行锁（MySQL 兼容）+ 分布式锁管理**——跨分片事务使用全局锁协调。单分片事务的锁行为与 MySQL 一致。对比 MySQL（单机行锁）和 Spanner（分布式 TrueTime 锁），TDSQL 的分布式锁通过 2PC 协调跨分片一致性。 |
| [分区](../advanced/partitioning/tdsql.md) | **ShardKey 分片（分布式层）+ PARTITION（MySQL 兼容）双层**——第一层通过 shardkey 水平拆分到多个 SET，第二层在每个 SET 内可再用 MySQL PARTITION BY 进一步分区。对比 MySQL（仅 PARTITION）和 YugabyteDB（仅分片），TDSQL 的双层数据分布策略提供更细粒度的数据管理。 |
| [权限](../advanced/permissions/tdsql.md) | **MySQL 兼容权限模型**——GRANT/REVOKE 在 Proxy 层统一执行。SQL 审计日志记录所有操作。对比 MySQL（相同权限模型）和 PostgreSQL 的 RLS（行级安全），TDSQL 在金融场景下内置了完整的审计合规能力。 |
| [存储过程](../advanced/stored-procedures/tdsql.md) | **MySQL 兼容存储过程（分片限制）**——存储过程在单个 SET 节点上执行，跨分片逻辑需要应用层处理或通过 Proxy 路由。对比 MySQL（存储过程无限制）和 CockroachDB（分布式存储过程受限），TDSQL 的存储过程在分布式场景下有作用域限制。 |
| [临时表](../advanced/temp-tables/tdsql.md) | **TEMPORARY TABLE（MySQL 兼容）**——临时表在 Proxy 层当前连接中可见。对比 MySQL（单机临时表）和 PostgreSQL（CREATE TEMP TABLE），TDSQL 的临时表行为与 MySQL 一致。 |
| [事务](../advanced/transactions/tdsql.md) | **分布式事务（XA/2PC）+ 强一致性**——跨分片事务通过两阶段提交 + 全局时间戳保证 ACID。强同步复制确保每个 SET 的主备切换 RPO=0。对比 MySQL（单机事务）和 Spanner（TrueTime 分布式事务），TDSQL 的分布式事务在微信支付等金融场景中经过大规模验证。 |
| [触发器](../advanced/triggers/tdsql.md) | **MySQL 兼容触发器（分片限制）**——触发器在单个 SET 节点上执行，跨分片触发行为不支持。对比 MySQL（触发器无限制）和 PostgreSQL（触发器功能更完整），TDSQL 的触发器在分布式场景下有作用域限制。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/tdsql.md) | **DELETE（MySQL 兼容）+ 分布式路由**——包含 shardkey 条件的 DELETE 直接路由到目标分片；不含 shardkey 的 DELETE 广播到所有分片执行。对比 MySQL（单机 DELETE）和 CockroachDB（分布式 DELETE 透明），TDSQL 的 DELETE 路由策略要求开发者了解 shardkey 以优化性能。 |
| [插入](../dml/insert/tdsql.md) | **INSERT（MySQL 兼容）+ ShardKey 路由写入**——INSERT 语句根据 shardkey 值自动路由到目标分片。批量 INSERT 多行时，不同 shardkey 值的行被分发到不同分片并行写入。对比 MySQL（单机 INSERT）和 CockroachDB（自动路由），TDSQL 的 shardkey 路由对写入性能至关重要。 |
| [更新](../dml/update/tdsql.md) | **UPDATE（MySQL 兼容）+ 跨分片更新透明**——UPDATE 根据 WHERE 条件路由到相关分片。注意：不允许 UPDATE shardkey 列本身（会改变数据分布），需先 DELETE 再 INSERT。对比 MySQL（UPDATE 任意列）和 CockroachDB（可 UPDATE 主键），TDSQL 对 shardkey 列的更新限制是分布式设计的必要约束。 |
| [Upsert](../dml/upsert/tdsql.md) | **ON DUPLICATE KEY UPDATE（MySQL 兼容）**——基于唯一键/主键冲突自动转为 UPDATE。分布式场景下唯一键必须包含 shardkey。对比 MySQL（ON DUPLICATE KEY UPDATE 无限制）和 PostgreSQL 的 ON CONFLICT（功能类似），TDSQL 的 Upsert 受分片键约束。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/tdsql.md) | **MySQL 兼容聚合 + 分布式聚合下推**——Proxy 层将 SUM/COUNT/AVG 等聚合下推到各分片执行，再合并结果。部分聚合（如 GROUP_CONCAT）可能需要在 Proxy 层完成合并。对比 MySQL（单机聚合）和 CockroachDB（分布式聚合原生），TDSQL 的聚合下推优化是分布式查询性能的关键。 |
| [条件函数](../functions/conditional/tdsql.md) | **IF/CASE（MySQL 兼容）**——条件函数在各分片本地执行，无分布式特殊行为。对比 MySQL（相同函数）和 PostgreSQL（无 IF 函数），TDSQL 的条件函数与 MySQL 一致。 |
| [日期函数](../functions/date-functions/tdsql.md) | **MySQL 兼容日期函数**——DATE_FORMAT/STR_TO_DATE/DATE_ADD/DATEDIFF 等。对比 MySQL（相同函数集）和 PostgreSQL（不同命名），TDSQL 日期函数与 MySQL 完全一致。 |
| [数学函数](../functions/math-functions/tdsql.md) | **MySQL 兼容数学函数**——完整数学函数集，在各分片本地执行。对比 MySQL（相同函数集），TDSQL 数学函数无分布式特殊行为。 |
| [字符串函数](../functions/string-functions/tdsql.md) | **MySQL 兼容字符串函数**——CONCAT/SUBSTR/REPLACE/TRIM 等。GROUP_CONCAT 在分布式场景下需注意合并行为。对比 MySQL（相同函数）和 PostgreSQL（\|\| 拼接为主），TDSQL 字符串函数与 MySQL 一致。 |
| [类型转换](../functions/type-conversion/tdsql.md) | **CAST/CONVERT（MySQL 兼容）**——MySQL 风格隐式转换在各分片本地执行。对比 MySQL（相同行为）和 PostgreSQL（严格类型检查），TDSQL 继承 MySQL 的宽松转换。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/tdsql.md) | **递归 CTE（MySQL 8.0 兼容）**——Proxy 层处理 CTE 查询的分布式路由。对比 MySQL 8.0（CTE 原生）和 PostgreSQL（CTE 支持更早），TDSQL 的 CTE 与 MySQL 8.0 对齐。 |
| [全文搜索](../query/full-text-search/tdsql.md) | **InnoDB FULLTEXT（MySQL 兼容）**——全文索引在各分片本地维护。跨分片的全文搜索需要 Proxy 层合并结果并可能影响排名。对比 MySQL（单机 FULLTEXT）和 Elasticsearch（专用搜索引擎），TDSQL 的全文搜索在分布式场景下功能有限。 |
| [连接查询](../query/joins/tdsql.md) | **MySQL 兼容 JOIN + 跨分片 JOIN 自动路由**——相同 shardkey 的表 JOIN 在分片内本地执行（最优）；不同 shardkey 的表需要 Proxy 层汇聚数据（性能退化）；广播表 JOIN 总是本地执行。对比 MySQL（单机 JOIN）和 CockroachDB（分布式 JOIN 透明），TDSQL 的 JOIN 性能取决于 shardkey 设计。 |
| [分页](../query/pagination/tdsql.md) | **LIMIT/OFFSET（MySQL 兼容）**——分布式场景下 `LIMIT M, N` 需要每个分片返回 M+N 行再在 Proxy 层合并排序，深度分页性能退化明显。对比 MySQL（单机 LIMIT）和 CockroachDB（分布式分页），TDSQL 的深度分页是分布式数据库的普遍瓶颈。 |
| [行列转换](../query/pivot-unpivot/tdsql.md) | **无原生 PIVOT（同 MySQL）**——需使用 CASE + GROUP BY 手动实现。对比 MySQL（同样无 PIVOT）和 Oracle（PIVOT 原生），TDSQL 继承 MySQL 局限。 |
| [集合操作](../query/set-operations/tdsql.md) | **UNION（MySQL 兼容）+ 分布式 UNION**——UNION 在 Proxy 层合并各分片结果。UNION DISTINCT 需要全局去重（可能成本较高）。对比 MySQL（单机 UNION）和 PostgreSQL（UNION/INTERSECT/EXCEPT 完整），TDSQL 的分布式 UNION 在大数据量下需关注性能。 |
| [子查询](../query/subquery/tdsql.md) | **MySQL 兼容子查询 + 分布式下推优化**——Proxy 层尽可能将子查询下推到分片执行。不可下推的子查询需要在 Proxy 层汇聚数据。对比 MySQL 8.0（子查询优化改善）和 CockroachDB（分布式优化器），TDSQL 的子查询下推是性能关键。 |
| [窗口函数](../query/window-functions/tdsql.md) | **MySQL 8.0 兼容窗口函数**——窗口函数在分布式场景下可能需要 Proxy 层全局排序。对比 MySQL 8.0（单机窗口函数）和 PolarDB（并行窗口函数），TDSQL 的窗口函数在跨分片场景下需关注排序开销。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/tdsql.md) | **递归 CTE（MySQL 兼容）**——生成日期序列方案与 MySQL 8.0 一致。对比 PostgreSQL 的 generate_series（更简洁）和 BigQuery 的 GENERATE_DATE_ARRAY，TDSQL 沿用 MySQL 递归 CTE 方式。 |
| [去重](../scenarios/deduplication/tdsql.md) | **ROW_NUMBER + CTE（MySQL 兼容）**——分布式场景下去重需要全局 ROW_NUMBER 排序，可能涉及跨分片数据汇聚。对比 MySQL 8.0（单机去重）和 PostgreSQL 的 DISTINCT ON（更简洁），TDSQL 的去重方案与 MySQL 一致但需考虑分布式排序开销。 |
| [区间检测](../scenarios/gap-detection/tdsql.md) | **窗口函数 LAG/LEAD（MySQL 兼容）**——分布式场景下窗口函数可能需要全局排序。对比 MySQL 8.0（单机窗口函数）和 PostgreSQL 的 generate_series（可生成完整序列对比），TDSQL 方案与 MySQL 一致。 |
| [层级查询](../scenarios/hierarchical-query/tdsql.md) | **递归 CTE（MySQL 兼容）**——递归查询在分布式场景下可能涉及跨分片数据访问。对比 MySQL 8.0（单机递归 CTE）和 Oracle（CONNECT BY），TDSQL 的层级查询与 MySQL 8.0 一致。 |
| [JSON 展开](../scenarios/json-flatten/tdsql.md) | **JSON_TABLE（MySQL 兼容）**——JSON_TABLE 在各分片本地执行，展开性能与单机 MySQL 一致。对比 MySQL 8.0（JSON_TABLE 原生）和 PostgreSQL 的 jsonb_array_elements，TDSQL 的 JSON 处理与 MySQL 一致。 |
| [迁移速查](../scenarios/migration-cheatsheet/tdsql.md) | **MySQL 兼容是基础，ShardKey 分片设计是核心差异**。关键注意：shardkey 选择直接决定查询性能和数据分布均匀度；广播表用于小维度表 JOIN 优化；主键/唯一键必须包含 shardkey；跨分片 JOIN 和聚合性能受限；不允许 UPDATE shardkey 列；分布式事务有额外延迟。 |
| [TopN 查询](../scenarios/ranking-top-n/tdsql.md) | **ROW_NUMBER + LIMIT（MySQL 兼容）**——分布式 TopN 需要 Proxy 层全局排序。包含 shardkey 条件的 TopN 可路由到单分片执行。对比 MySQL 8.0（单机 TopN）和 BigQuery（QUALIFY 更简洁），TDSQL 的 TopN 性能取决于是否可路由到单分片。 |
| [累计求和](../scenarios/running-total/tdsql.md) | **SUM() OVER(ORDER BY ...)（MySQL 兼容）**——跨分片累计求和需要全局排序。对比 MySQL 8.0（单机窗口函数）和各主流引擎（写法一致），TDSQL 在跨分片场景下窗口函数有额外开销。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/tdsql.md) | **ON DUPLICATE KEY UPDATE（MySQL 兼容）**——唯一键须含 shardkey 才能实现分片内 Upsert。对比 MySQL（ON DUPLICATE KEY UPDATE 无限制）和 PostgreSQL 的 ON CONFLICT，TDSQL 的 Upsert 受分片键约束。 |
| [字符串拆分](../scenarios/string-split-to-rows/tdsql.md) | **JSON_TABLE 或递归 CTE（MySQL 兼容）**——方案与 MySQL 8.0 一致。对比 PostgreSQL 的 string_to_array+unnest（更简洁）和 BigQuery 的 SPLIT+UNNEST，TDSQL 的拆分方案较复杂。 |
| [窗口分析](../scenarios/window-analytics/tdsql.md) | **MySQL 8.0 兼容窗口函数**——分布式场景下窗口分析可能涉及全局排序，shardkey 相关的分区窗口可在分片内高效执行。对比 MySQL 8.0（单机窗口函数）和 PolarDB（并行窗口函数），TDSQL 的窗口分析性能取决于数据分布。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/tdsql.md) | **无 ARRAY/STRUCT 列类型（同 MySQL）**——需用 JSON 存储结构化数据。对比 MySQL（同样无 ARRAY/STRUCT）和 PostgreSQL（ARRAY 原生），TDSQL 继承 MySQL 类型系统局限。 |
| [日期时间](../types/datetime/tdsql.md) | **DATETIME/TIMESTAMP（MySQL 兼容）**——DATETIME 无时区，TIMESTAMP 有 UTC 转换。shardkey 使用 DATETIME 类型时需注意时区一致性。对比 MySQL（DATETIME/TIMESTAMP 经典区分）和 PostgreSQL（TIMESTAMPTZ 更清晰），TDSQL 时间类型与 MySQL 一致。 |
| [JSON](../types/json/tdsql.md) | **JSON（MySQL 兼容）+ JSON_TABLE**——JSON 二进制存储。分布式场景下 JSON 查询在各分片本地执行。对比 MySQL 8.0（JSON 原生）和 PostgreSQL 的 JSONB+GIN（查询性能更强），TDSQL 的 JSON 能力与 MySQL 对齐。 |
| [数值类型](../types/numeric/tdsql.md) | **MySQL 兼容数值类型**——TINYINT/SMALLINT/INT/BIGINT/DECIMAL/FLOAT/DOUBLE 完整体系。shardkey 列推荐使用整数类型以优化哈希分布。对比 MySQL（相同类型体系）和 PostgreSQL（无 UNSIGNED），TDSQL 在数值类型上与 MySQL 一致。 |
| [字符串类型](../types/string/tdsql.md) | **utf8mb4 推荐（MySQL 兼容）**——VARCHAR(n)/CHAR(n)/TEXT/LONGTEXT 标准体系。shardkey 列使用字符串类型时哈希分布的均匀性取决于值的分布。对比 MySQL（utf8mb4 推荐）和 PostgreSQL（UTF-8 原生），TDSQL 字符集行为与 MySQL 一致。 |
