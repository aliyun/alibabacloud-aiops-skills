# TiDB

**分类**: 分布式数据库（兼容 MySQL）
**文件数**: 51 个 SQL 文件
**总行数**: 4374 行

> **关键人物**：[刘奇, 黄东旭](../docs/people/tidb-founders.md)（PingCAP）

## 概述与定位

TiDB 是 PingCAP 于 2015 年开源的分布式关系型数据库，目标是在一套系统中同时满足 OLTP 与 OLAP 工作负载（HTAP）。它在 SQL 层高度兼容 MySQL 协议与语法，使现有 MySQL 应用可以低成本迁移；在存储层则采用分布式 KV 引擎 TiKV 和列存引擎 TiFlash 实现水平扩展与实时分析。TiDB 定位于需要弹性伸缩、强一致事务和实时分析的互联网与金融场景。

## 历史与演进

- **2015 年**：PingCAP 成立并启动 TiDB 项目，受 Google Spanner/F1 论文启发。
- **2017 年**：TiDB 1.0 GA，基本实现 MySQL 兼容与分布式事务。
- **2019 年**：3.0 引入 TiFlash 列存引擎，正式支持 HTAP 场景。
- **2020 年**：4.0 推出 TiDB Dashboard、Placement Rules、BR 备份恢复。
- **2021 年**：5.0 引入 MPP 计算框架，TiFlash 可独立承担分析查询。
- **2022 年**：6.0 引入 Placement Rules in SQL、热点小表缓存、Top SQL。
- **2023-2024 年**：7.x 持续增强资源管控（Resource Control）、全局排序、TiDB Serverless。
- **2025 年**：8.x 强化多租户隔离、向量搜索和 AI 集成能力。

## 核心设计思路

TiDB 采用计算与存储分离的分层架构：**TiDB Server** 负责 SQL 解析和优化（无状态，可水平扩展）；**TiKV** 以 Region 为单位管理数据、通过 Multi-Raft 协议实现强一致复制；**PD (Placement Driver)** 负责元数据管理和调度。事务模型基于 Percolator（乐观/悲观两种模式），提供 Snapshot Isolation 默认隔离级别。TiFlash 作为列存副本通过 Raft Learner 实时同步数据，查询优化器可自动选择行存或列存路径。

## 独特特色

- **AUTO_RANDOM**：用随机位替代自增 ID 的高位，避免写热点集中在单一 Region。
- **TiFlash 列存引擎**：通过 `ALTER TABLE t SET TIFLASH REPLICA 1` 即可为任意表创建列存副本，优化器自动路由分析查询。
- **MPP 框架**：TiFlash 节点之间可协作完成分布式 Join 和聚合，无需额外 OLAP 引擎。
- **Placement Rules in SQL**：用 `ALTER TABLE ... PLACEMENT POLICY` 控制数据的地域分布与副本策略。
- **资源管控**：通过 Resource Control 实现多租户间 CPU/IO 配额管理。
- **AUTO_ID_CACHE**：控制自增 ID 缓存粒度，在分布式场景下平衡性能与连续性。
- **TTL 表**：支持行级 TTL，到期数据自动清理。
- **向量搜索（8.4+）**：`VECTOR` 数据类型 + `VEC_COSINE_DISTANCE()` 等函数 + HNSW 向量索引。原生支持 AI embedding 存储和 ANN 查询，无需外部向量数据库。
- **全局索引 GA（8.5+）**：分区表上的全局二级索引，解决了分区表跨分区查询需要扫描所有分区的问题。
- **快速建表（8.5+）**：`CREATE TABLE` 和 `ADD INDEX` 性能大幅提升（10x+），通过批量 DML 和并行 DDL。
- **外键正式支持（6.6+）**：从实验特性升级为 GA，支持 CASCADE/SET NULL/RESTRICT。分布式外键有性能代价但保证完整性。

## 已知不足

- 与 MySQL 的兼容性仍有差异：不支持存储过程（仅实验性）、外键约束为实验特性、触发器不支持。
- 自增 ID 不保证全局连续，跨 TiDB 实例可能出现间隙和乱序。
- 全文索引不支持（需借助外部搜索引擎）。
- 单行大事务有大小限制（默认 6 MB TxnTotalSizeLimit）。
- 部分 MySQL 内置函数和系统变量尚未实现。
- TiFlash 同步存在短暂延迟，对实时性要求极高的分析场景需注意。

## 对引擎开发者的参考价值

TiDB 的架构设计为 SQL 引擎开发提供了重要参考：Raft 共识在数据库中的工程实现（Multi-Raft 分裂/合并/调度）、Percolator 分布式事务模型的生产化改进（悲观锁扩展）、行列混存的 HTAP 路由决策、以及计算层无状态设计对弹性伸缩的支撑。AUTO_RANDOM 的热点打散思路和 Placement Rules 的数据放置抽象对分布式系统设计有普遍借鉴意义。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/tidb.md) | **MySQL 兼容但分布式差异大**——AUTO_RANDOM 替代 AUTO_INCREMENT 避免写热点集中在单一 Region。TiFlash 列存副本通过 `SET TIFLASH REPLICA` 透明加速分析查询。外键 6.6+ 才实验性支持，聚簇索引默认开启。对比 CockroachDB 的 unique_rowid() 和 Spanner 的 UUID 策略，TiDB 的 AUTO_RANDOM 对 MySQL 用户最友好。 |
| [改表](../ddl/alter-table/tidb.md) | **Online DDL 无锁变更**——基于分布式 Schema 版本协议，DDL 变更在多个 TiDB Server 间原子生效。支持 ADD/DROP COLUMN、ADD INDEX 等在线操作。对比 MySQL 的 pt-osc/gh-ost 工具链，TiDB 内置 Online DDL 更简洁；但 MODIFY COLUMN TYPE 限制较多，复杂类型变更可能需要重建表。 |
| [索引](../ddl/indexes/tidb.md) | **分布式索引存储在 TiKV 中**——索引数据也按 Region 分片和 Raft 复制。聚簇索引（5.0+）将行数据直接存储在主键索引中减少回表。全局索引仍在演进中，分区表的非分区键索引需关注。对比 MySQL 的 InnoDB B+Tree，TiDB 索引的分布式特性使扫描可跨节点并行，但点查可能需跨节点 RPC。 |
| [约束](../ddl/constraints/tidb.md) | **PK/UNIQUE 强制执行，FK 为实验特性**——外键约束 6.6+ 才引入且默认不启用，生产环境需谨慎使用。CHECK 约束 7.2+ 支持但默认不强制。对比 MySQL 的完整约束支持，TiDB 在分布式一致性与功能完备性之间做了取舍——跨 Region 的外键校验代价高昂。 |
| [视图](../ddl/views/tidb.md) | **普通视图兼容 MySQL，无物化视图**——TiFlash 列存副本在实践中替代了物化视图的部分场景：为分析查询自动路由到列存，无需手动维护聚合表。对比 PG 的 MATERIALIZED VIEW（需手动 REFRESH）和 BigQuery 的自动刷新物化视图，TiDB 用 TiFlash 实现了另一种"透明加速"范式。 |
| [序列与自增](../ddl/sequences/tidb.md) | **AUTO_INCREMENT 兼容但不保证全局连续**——跨 TiDB Server 的 ID 缓存导致间隙和乱序。AUTO_RANDOM 用随机位填充高位避免热点。AUTO_ID_CACHE=1 可保证单节点连续但牺牲性能。对比 Snowflake 的 AUTOINCREMENT（不保证连续）和 CockroachDB 的 unique_rowid()，分布式场景下全局连续自增几乎不可能。 |
| [数据库/Schema/用户](../ddl/users-databases/tidb.md) | **MySQL 兼容权限模型 + RBAC 角色**——GRANT/REVOKE 语法完全兼容 MySQL。Placement Rules in SQL 可控制数据的地域分布。Resource Control（7.0+）实现多租户 CPU/IO 配额。对比 MySQL 的单机权限模型，TiDB 额外提供了分布式数据放置和资源隔离能力。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/tidb.md) | **PREPARE/EXECUTE 兼容 MySQL**——支持服务端预处理语句，执行计划缓存提升重复查询性能。不支持存储过程内的动态 SQL（因为不支持存储过程）。对比 PG 的 PL/pgSQL EXECUTE 和 Oracle 的 EXECUTE IMMEDIATE，TiDB 仅支持客户端侧动态 SQL。 |
| [错误处理](../advanced/error-handling/tidb.md) | **分布式事务错误需应用层重试**——TiDB 的乐观事务在提交阶段才检测冲突，冲突时返回错误码需应用重试。5.0+ 默认切换为悲观事务减少了重试需求。不支持 MySQL 的 DECLARE HANDLER（因无存储过程）。对比 CockroachDB 的自动事务重试和 Spanner 的客户端库自动重试，TiDB 在悲观模式下行为更接近传统 MySQL。 |
| [执行计划](../advanced/explain/tidb.md) | **EXPLAIN ANALYZE 展示分布式算子细节**——可看到 TiKV Coprocessor 下推情况、TiFlash 路由决策和 Region 访问统计。TiDB Dashboard 提供图形化 SQL 诊断。对比 MySQL 的 EXPLAIN 仅展示单机计划，TiDB 额外显示 cop[tikv]/cop[tiflash] 等分布式执行信息。 |
| [锁机制](../advanced/locking/tidb.md) | **乐观/悲观双事务模型**——5.0+ 默认悲观事务，锁存储在 TiKV 的内存中。乐观事务适合低冲突场景（写入快但提交可能失败）。FOR UPDATE 在悲观模式下与 MySQL 行为一致。对比 MySQL 的纯悲观锁和 CockroachDB 的 SERIALIZABLE 默认隔离，TiDB 提供了更灵活的选择。 |
| [分区](../advanced/partitioning/tidb.md) | **MySQL 兼容分区 + TiKV Region 分片双层体系**——RANGE/LIST/HASH 分区用于逻辑数据管理，Region 自动分裂/合并处理物理数据分布。两者互补：分区便于批量清理过期数据，Region 保证负载均衡。对比 MySQL 仅有分区、CockroachDB 的 Geo-Partitioning，TiDB 的双层设计更适合大规模数据管理。 |
| [权限](../advanced/permissions/tidb.md) | **MySQL 兼容权限 + RBAC 角色 + 资源管控**——完整支持 GRANT/REVOKE/CREATE ROLE。Resource Control（7.0+）按资源组限制 CPU/IO，实现多租户隔离。对比 MySQL 仅有权限控制、PG 的 RLS 行级安全，TiDB 在权限之上增加了资源层面的隔离。 |
| [存储过程](../advanced/stored-procedures/tidb.md) | **不支持存储过程/函数/触发器**——这是 TiDB 与 MySQL 兼容性最大的差异点。分布式环境下存储过程的事务语义和一致性保证实现复杂，PingCAP 选择优先保证核心功能稳定。对比 OceanBase（双模兼容存储过程）和 CockroachDB（PL/pgSQL 23.1+），TiDB 在过程式编程方面最弱。 |
| [临时表](../advanced/temp-tables/tidb.md) | **LOCAL/GLOBAL TEMPORARY TABLE（5.3+）**——LOCAL 临时表仅当前事务可见，GLOBAL 临时表 Schema 持久但数据会话级。与 MySQL 的 CREATE TEMPORARY TABLE 语义有差异。对比 PG 的 ON COMMIT DROP/DELETE ROWS 和 Oracle 的 GTT，TiDB 的实现更接近 SQL 标准。 |
| [事务](../advanced/transactions/tidb.md) | **分布式 ACID 事务基于 Percolator 协议**——默认 Snapshot Isolation 隔离级别。悲观模式（默认）在 DML 执行时即加锁，乐观模式延迟到提交阶段。大事务有 6MB TxnTotalSizeLimit 限制。对比 CockroachDB 的 SERIALIZABLE 默认和 Spanner 的 TrueTime 外部一致性，TiDB 的 SI 隔离级别在性能和一致性间取得平衡。 |
| [触发器](../advanced/triggers/tidb.md) | **不支持触发器**——分布式场景下触发器的执行位置（哪个 TiDB Server）和事务语义难以保证。替代方案：应用层逻辑、TiCDC 变更数据捕获。对比 MySQL/PG 的完整触发器支持和 CockroachDB 的 CHANGEFEED CDC，TiDB 选择了 TiCDC 作为数据变更响应的主要机制。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/tidb.md) | **DELETE 兼容 MySQL 语法**——支持 DELETE ... LIMIT 限制批量删除行数，避免大事务超限。分布式并行删除可跨 Region 并发执行。大批量删除建议分批进行以避免 GC 压力。对比 MySQL 的单机删除和 BigQuery 的分区级标记删除，TiDB 需关注事务大小限制。 |
| [插入](../dml/insert/tidb.md) | **INSERT/REPLACE/LOAD DATA 兼容 MySQL**——分布式并行写入自动路由到目标 Region。LOAD DATA 支持分布式并行导入（7.0+ Lightning 模式）。INSERT 语句的自增值在多 TiDB Server 间可能不连续。对比 MySQL 的单机写入和 BigQuery 的批量加载免费模式，TiDB 的写入路径更适合高吞吐 OLTP。 |
| [更新](../dml/update/tidb.md) | **UPDATE 兼容 MySQL 语法**——分布式事务保证跨 Region 更新的原子性。更新主键值会导致数据在 Region 间迁移（性能开销大）。批量 UPDATE 受事务大小限制。对比 MySQL 的行级原地更新和 BigQuery 的分区重写，TiDB 在分布式场景下尽可能保持 MySQL 的更新语义。 |
| [Upsert](../dml/upsert/tidb.md) | **ON DUPLICATE KEY UPDATE / REPLACE INTO 兼容 MySQL**——不支持标准 SQL 的 MERGE 语句。REPLACE INTO 实际是 DELETE+INSERT，在分布式场景下可能有性能影响。对比 PG 的 ON CONFLICT DO UPDATE 和 CockroachDB 的 UPSERT 简写，TiDB 的 Upsert 语法完全 MySQL 风格。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/tidb.md) | **MySQL 兼容聚合 + TiFlash 列存加速**——GROUP_CONCAT、COUNT(DISTINCT) 等完整支持。TiFlash MPP 框架下聚合查询可跨节点并行，性能远超单机 MySQL。APPROX_COUNT_DISTINCT 提供近似去重计数。对比 ClickHouse 的 -If 组合聚合和 BigQuery 的 APPROX_COUNT_DISTINCT，TiDB 在 HTAP 场景下同时服务 OLTP 和 OLAP 聚合。 |
| [条件函数](../functions/conditional/tidb.md) | **IF/CASE/COALESCE/IFNULL/NULLIF 兼容 MySQL**——行为与 MySQL 完全一致，包括 IF() 函数（非标准 SQL 但 MySQL 常用）。对比 PG 仅有 CASE/COALESCE（无 IF 函数）和 Oracle 的 DECODE/NVL，TiDB 保持了 MySQL 的函数集。 |
| [日期函数](../functions/date-functions/tidb.md) | **MySQL 兼容日期函数集**——DATE_FORMAT/STR_TO_DATE/DATEDIFF/DATE_ADD 等完整支持。TIMESTAMP 精度支持到微秒（6 位）。TiDB 特有的 TIDB_PARSE_TSO() 可解析 TSO 时间戳。对比 PG 的 date_trunc/to_char 和 BigQuery 的 DATE_TRUNC/FORMAT_DATE，TiDB 沿用 MySQL 的日期函数命名体系。 |
| [数学函数](../functions/math-functions/tidb.md) | **MySQL 兼容数学函数**——ABS/CEIL/FLOOR/ROUND/MOD/POWER 等完整支持。除零行为与 MySQL 一致（返回 NULL 而非报错）。对比 PG 的除零报错和 BigQuery 的 SAFE_DIVIDE，TiDB 继承了 MySQL 的宽松错误处理。 |
| [字符串函数](../functions/string-functions/tidb.md) | **MySQL 兼容字符串函数**——CONCAT/SUBSTRING/REPLACE/REGEXP_REPLACE 等完整支持。CONCAT() 接受多参数（MySQL 风格），不同于 PG 的 `\|\|` 双参数拼接。对比 BigQuery 的 SPLIT 返回 ARRAY 和 PG 的 string_to_array，TiDB 的字符串处理完全 MySQL 风格。 |
| [类型转换](../functions/type-conversion/tidb.md) | **CAST/CONVERT 兼容 MySQL**——隐式类型转换行为与 MySQL 一致（比 PG 更宽松）。字符串到数字的隐式转换可能导致意外结果（与 MySQL 相同的陷阱）。对比 PG 的严格类型系统和 BigQuery 的 SAFE_CAST，TiDB 保持了 MySQL 的宽松转换语义，迁移友好但需注意类型安全。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/tidb.md) | **递归 CTE（5.1+）兼容标准 SQL**——WITH RECURSIVE 支持层级查询和序列生成。CTE 可被优化器内联或物化，自动决策。对比 MySQL 8.0 的 CTE（基本功能相同）和 PG 的 MATERIALIZED/NOT MATERIALIZED hint，TiDB 的 CTE 优化更接近自动化。 |
| [全文搜索](../query/full-text-search/tidb.md) | **不支持 FULLTEXT 索引**——这是与 MySQL 的重要差异。TiDB 的分布式 KV 存储架构不适合倒排索引实现。替代方案：集成 Elasticsearch 或使用 LIKE/REGEXP（性能差）。对比 MySQL 的 InnoDB FULLTEXT 和 PG 的 tsvector+GIN，TiDB 在全文搜索场景需借助外部系统。 |
| [连接查询](../query/joins/tidb.md) | **Hash/Index/Merge JOIN + TiFlash MPP 加速**——优化器自动选择 JOIN 策略，支持 Hint 手动指定。TiFlash MPP 模式下大表 JOIN 可跨 TiFlash 节点并行，性能接近专用 OLAP 引擎。对比 MySQL 仅有 Nested Loop/Hash JOIN 和 BigQuery 的 Broadcast/Shuffle JOIN，TiDB 的 HTAP 双引擎路由是独特优势。 |
| [分页](../query/pagination/tidb.md) | **LIMIT/OFFSET 兼容 MySQL，分布式分页有额外开销**——深度分页（大 OFFSET）需要从多个 TiKV Region 收集数据后排序截取，性能随 OFFSET 增大退化。推荐 Keyset 分页（WHERE id > last_id LIMIT N）。对比 MySQL 单机分页和 BigQuery 按扫描量计费不受 OFFSET 影响，TiDB 的分布式分页需特别优化。 |
| [行列转换](../query/pivot-unpivot/tidb.md) | **无原生 PIVOT/UNPIVOT**——需用 CASE+GROUP BY 模拟，与 MySQL 相同。对比 BigQuery/Snowflake 的原生 PIVOT 和 Oracle 的 PIVOT/UNPIVOT，TiDB 缺乏行列转换的语法糖。 |
| [集合操作](../query/set-operations/tidb.md) | **UNION/INTERSECT/EXCEPT 完整支持**——UNION ALL/DISTINCT 标准。INTERSECT 和 EXCEPT 在较新版本中引入（早期仅支持 UNION）。对比 MySQL 8.0（同样较晚引入 INTERSECT/EXCEPT）和 PG（长期完整支持），TiDB 已追上标准 SQL 的集合操作能力。 |
| [子查询](../query/subquery/tidb.md) | **关联子查询优化 + 分布式下推**——优化器可将部分子查询转为 Semi Join 或 Anti Join 下推到 TiKV。IN/EXISTS/NOT EXISTS 均支持。对比 MySQL 5.x 的子查询性能问题（8.0 已修复）和 PG 的成熟子查询优化，TiDB 的分布式子查询优化持续改进中。 |
| [窗口函数](../query/window-functions/tidb.md) | **完整窗口函数支持**——ROW_NUMBER/RANK/DENSE_RANK/NTILE/LAG/LEAD/SUM OVER 等全部支持。ROWS/RANGE 帧规范完整。无 QUALIFY 子句（需子查询包装）。对比 MySQL 8.0（功能相同但单机执行）和 BigQuery/Snowflake 的 QUALIFY，TiDB 的窗口函数可通过 TiFlash MPP 并行加速。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/tidb.md) | **递归 CTE（5.1+）生成日期序列**——无 generate_series 函数，需用 WITH RECURSIVE 模拟。对比 PG 的 generate_series（一行搞定）和 BigQuery 的 GENERATE_DATE_ARRAY+UNNEST，TiDB 的日期序列生成略显繁琐但功能等价。 |
| [去重](../scenarios/deduplication/tidb.md) | **ROW_NUMBER+CTE 标准去重模式**——分布式并行执行，大数据量去重性能优于单机 MySQL。TiFlash 列存可加速包含聚合的去重查询。对比 PG 的 DISTINCT ON（更简洁）和 BigQuery 的 QUALIFY（最简），TiDB 需要标准的子查询包装。 |
| [区间检测](../scenarios/gap-detection/tidb.md) | **LAG/LEAD 窗口函数检测连续性**——兼容 MySQL 写法。分布式执行时窗口函数需要全局排序，大数据集下可能成为瓶颈。对比 PG 的 generate_series+LEFT JOIN 和 TimescaleDB 的 time_bucket_gapfill，TiDB 用通用窗口函数实现。 |
| [层级查询](../scenarios/hierarchical-query/tidb.md) | **递归 CTE（5.1+）支持层级遍历**——无 Oracle 的 CONNECT BY 语法。递归深度有限制（默认 1000 层）。对比 Oracle/达梦的 CONNECT BY START WITH 和 PG 的递归 CTE，TiDB 采用标准 SQL 方案。 |
| [JSON 展开](../scenarios/json-flatten/tidb.md) | **JSON_TABLE（7.0+）+ JSON_EXTRACT（MySQL 兼容）**——JSON_TABLE 将 JSON 数组展开为关系行，7.0 之前需用多层 JSON_EXTRACT 模拟。多值索引（6.6+）可加速 JSON 数组元素查询。对比 PG 的 jsonb_array_elements（成熟完善）和 BigQuery 的 JSON_QUERY_ARRAY+UNNEST，TiDB 的 JSON 处理能力在快速追赶。 |
| [迁移速查](../scenarios/migration-cheatsheet/tidb.md) | **MySQL 高度兼容是核心卖点，但三大差异不可忽略**——不支持存储过程/触发器/FULLTEXT 索引。AUTO_INCREMENT 行为不同（不保证连续）。大事务有大小限制。对比 OceanBase 的 MySQL 兼容（含存储过程）和 CockroachDB 的 PG 兼容，TiDB 的 MySQL 兼容度在分布式数据库中最高但非 100%。 |
| [TopN 查询](../scenarios/ranking-top-n/tidb.md) | **ROW_NUMBER+CTE+LIMIT 标准模式**——无 QUALIFY 子句，需子查询包装。TiDB 优化器对 TopN 有专门的 TopN 下推优化（减少数据传输）。对比 BigQuery/Snowflake 的 QUALIFY（单行表达式）和 MySQL 的 LIMIT（无窗口函数分组 TopN 能力），TiDB 的 TopN 实现标准但高效。 |
| [累计求和](../scenarios/running-total/tidb.md) | **SUM() OVER 标准窗口函数**——TiFlash MPP 可加速大规模累计计算。分布式执行时窗口帧的数据需要跨节点传输。对比 MySQL 8.0（单机执行）和 BigQuery（Slot 自动扩展），TiDB 的 HTAP 能力使累计分析可在同一集群完成。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/tidb.md) | **ON DUPLICATE KEY UPDATE（MySQL 兼容），无 MERGE**——不支持标准 SQL 的 MERGE INTO 语句。SCD Type 2 需要应用层逻辑或多条 SQL 组合实现。对比 PG 的 ON CONFLICT 和 OceanBase Oracle 模式的 MERGE，TiDB 的 SCD 实现受限于 MySQL 语法。 |
| [字符串拆分](../scenarios/string-split-to-rows/tidb.md) | **JSON_TABLE（7.0+）或递归 CTE 模拟**——7.0 之前无原生拆分展开函数，需用递归 CTE 逐字符拆分。JSON_TABLE 引入后可先将字符串转为 JSON 数组再展开。对比 PG 的 string_to_array+unnest（优雅简洁）和 BigQuery 的 SPLIT+UNNEST，TiDB 的字符串拆分是短板。 |
| [窗口分析](../scenarios/window-analytics/tidb.md) | **完整窗口函数 + TiFlash MPP 加速**——移动平均、同环比、占比计算等分析场景完整覆盖。TiFlash 列存引擎对窗口函数的执行效率远高于 TiKV 行存。对比 MySQL 8.0（功能相同但单机限制）和专用 OLAP 引擎（ClickHouse/Snowflake），TiDB 的 HTAP 定位使其可在一套系统内完成 OLTP 和窗口分析。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/tidb.md) | **无 ARRAY/STRUCT/MAP 类型**——与 MySQL 相同，用 JSON 类型替代复合数据需求。无法像 PG 那样定义自定义复合类型。对比 PG 的 ARRAY/COMPOSITE TYPE 和 BigQuery 的 STRUCT/ARRAY 一等公民，TiDB 的类型系统局限于 MySQL 的关系型范式。 |
| [日期时间](../types/datetime/tidb.md) | **DATETIME/TIMESTAMP/DATE/TIME 兼容 MySQL**——TIMESTAMP 支持微秒精度（6 位小数）。TIMESTAMP 有 2038 年问题（与 MySQL 相同），DATETIME 范围到 9999 年。TiDB 特有的 TSO（时间戳 Oracle）为分布式事务提供全局时序。对比 PG 的 TIMESTAMPTZ（推荐带时区）和 BigQuery 的 TIMESTAMP（UTC 强制），TiDB 沿用 MySQL 的时区处理模型。 |
| [JSON](../types/json/tidb.md) | **JSON 二进制存储（MySQL 兼容）+ 多值索引（6.6+）**——JSON 列以二进制格式存储，支持 JSON_EXTRACT/->/->>/JSON_SET 等 MySQL 兼容操作符。多值索引可对 JSON 数组元素建立索引加速查询。对比 PG 的 JSONB+GIN 索引（功能最强）和 BigQuery 的原生 JSON 类型，TiDB 的 JSON 功能追随 MySQL 版本演进。 |
| [数值类型](../types/numeric/tidb.md) | **MySQL 兼容数值类型全集**——TINYINT/SMALLINT/MEDIUMINT/INT/BIGINT/FLOAT/DOUBLE/DECIMAL 均支持。UNSIGNED 修饰符兼容但非 SQL 标准。DECIMAL 精度最高 65 位。对比 BigQuery 的 INT64 单一整数类型（极简）和 PG 的无 UNSIGNED，TiDB 完整保留了 MySQL 的数值类型选择。 |
| [字符串类型](../types/string/tidb.md) | **utf8mb4 推荐（同 MySQL）**——VARCHAR/CHAR/TEXT/BLOB 等完整支持。CHARSET/COLLATE 兼容 MySQL 的字符集体系。utf8mb4_general_ci 和 utf8mb4_unicode_ci 排序规则行为与 MySQL 一致。对比 PG 的 TEXT 无长度限制和 BigQuery 的 STRING（极简），TiDB 保留了 MySQL 的字符集配置复杂性。 |
