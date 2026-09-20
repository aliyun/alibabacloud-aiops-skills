# PolarDB

**分类**: 云原生数据库（阿里云，兼容 MySQL）
**文件数**: 51 个 SQL 文件
**总行数**: 3925 行

## 概述与定位

PolarDB 是阿里云自主研发的云原生关系型数据库，采用计算与存储分离的共享存储架构。PolarDB 提供 MySQL 版、PostgreSQL 版和分布式版（PolarDB-X）三个产品形态，覆盖从兼容性迁移到分布式扩展的完整场景。其核心优势在于：在保持与 MySQL/PG 高度兼容的同时，利用云原生存储实现快速弹性扩展、秒级只读副本扩容和按用量计费。

## 历史与演进

- **2017 年**：PolarDB MySQL 版首次公开预览，采用共享存储架构。
- **2018 年**：PolarDB MySQL 版 GA，支持最大 100TB 存储和 16 个只读节点。
- **2019 年**：推出 PolarDB PostgreSQL 版（基于 PG 11）。
- **2020 年**：PolarDB-X（分布式版）GA，支持水平拆分和分布式事务。
- **2021 年**：开源 PolarDB for PostgreSQL，引入 HTAP 能力（列存索引）。
- **2022 年**：Serverless 弹性版发布，实现按需自动扩缩容。
- **2023-2025 年**：增强全局索引、多主架构探索、向量检索和 AI 集成。

## 核心设计思路

PolarDB 的核心创新是**共享存储架构**：一个读写主节点和多个只读节点共享同一份分布式存储（PolarStore/PolarFS）。只读节点通过物理复制（Redo Log Shipping）保持与主节点的数据一致，延迟通常在毫秒级。这种架构避免了传统主从复制的数据冗余，只读副本可秒级创建且不占额外存储空间。存储层使用 RDMA 网络和 NVMe SSD 实现接近本地存储的 IO 性能。

## 独特特色

- **共享存储零冗余**：只读节点不复制数据，共享同一存储卷，存储成本仅为传统方案的 1/N。
- **秒级只读扩展**：新增只读节点无需数据拷贝，秒级可用。
- **全局索引**（分布式版）：在分布式场景下提供跨分片的全局唯一索引。
- **并行查询**：单条 SQL 可利用多核并行执行，加速 OLAP 类查询。
- **列存索引 (IMCI)**：In-Memory Column Index 提供实时分析能力。
- **Serverless 弹性**：CPU/内存可按秒级自动扩缩，空闲时自动暂停降低成本。
- **POLARDB_AUDIT_LOG**：内置审计日志，满足合规需求。

## 已知不足

- **仅阿里云可用**：无法在其他云平台或本地部署（开源版 PolarDB-PG 除外）。
- 共享存储架构下写入仍是单主节点瓶颈，写扩展需要分布式版本。
- 与 MySQL/PG 原生版本的兼容性在极少数边缘特性上存在差异。
- 分布式版（PolarDB-X）的使用复杂度高于单机版。
- 跨可用区部署的存储延迟比同区域部署有明显增加。
- 部分高级功能（如列存索引）需要特定规格实例才能使用。

## 对引擎开发者的参考价值

PolarDB 的共享存储架构是云原生数据库设计的重要范式之一，展示了如何利用分布式文件系统和 RDMA 网络实现存算分离。其物理复制 + 共享存储的只读扩展方案比传统逻辑复制更高效。列存索引（IMCI）在行存引擎上叠加分析能力的思路也被越来越多的数据库借鉴。PolarFS 的设计论文对分布式存储系统开发者有重要参考价值。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/polardb.md) | **共享存储架构下的 MySQL 兼容建表**——语法与 MySQL 完全一致，但底层数据存储在 PolarStore 分布式文件系统上，读写节点和只读节点共享同一份数据。**IMCI 列存索引**可在建表后添加，实现行存 OLTP + 列存 OLAP 混合查询。对比 MySQL（单机存储）和 Aurora（类似共享存储），PolarDB 在存储层透明替换的同时保持 SQL 100% 兼容。 |
| [改表](../ddl/alter-table/polardb.md) | **Online DDL（MySQL 兼容）+ Parallel DDL 加速**——大表 DDL 可利用多核并行执行（如并行创建索引），比原生 MySQL 的 Online DDL 更快。对比 MySQL（Online DDL 单线程构建）和 Aurora（类似 MySQL DDL），PolarDB 的 Parallel DDL 是对 MySQL DDL 性能的显著增强。 |
| [索引](../ddl/indexes/polardb.md) | **InnoDB B-tree/全文索引（MySQL 兼容）+ 并行索引构建**——CREATE INDEX 可利用多核并行加速。IMCI 列存索引提供分析加速（非传统 B-tree，而是列式内存索引）。对比 MySQL（单线程索引构建）和 PostgreSQL（CREATE INDEX CONCURRENTLY），PolarDB 的并行索引构建显著降低大表索引创建时间。 |
| [约束](../ddl/constraints/polardb.md) | **PK/FK/CHECK/UNIQUE（MySQL 兼容）**——CHECK 约束从 MySQL 8.0.16 开始真正生效，PolarDB 同步支持。共享存储架构下约束在所有节点一致执行。对比 MySQL 8.0（CHECK 生效）和 PostgreSQL（CHECK 历来生效），PolarDB 在约束行为上与 MySQL 8.0 对齐。 |
| [视图](../ddl/views/polardb.md) | **MySQL 兼容视图，无原生物化视图**——视图定义透明，查询时自动路由到只读节点执行。缺少物化视图意味着分析型预计算需要借助 IMCI 或外部 ETL。对比 MySQL（同样无物化视图）和 PostgreSQL（REFRESH MATERIALIZED VIEW），PolarDB 的 IMCI 列存索引部分弥补了物化视图的缺失。 |
| [序列与自增](../ddl/sequences/polardb.md) | **AUTO_INCREMENT（MySQL 兼容）+ 全局自增保证**——共享存储架构下多节点写入时自增 ID 全局唯一且递增（不保证连续）。对比 MySQL 主从复制（自增 ID 需 auto_increment_offset 避免冲突）和 Aurora（类似全局自增），PolarDB 在分布式场景下的自增 ID 管理更可靠。 |
| [数据库/Schema/用户](../ddl/users-databases/polardb.md) | **MySQL 兼容权限模型**——Database = Schema，用户权限通过 GRANT/REVOKE 管理。共享存储下读写和只读节点共享同一份用户权限数据。对比 MySQL（相同权限模型）和 PostgreSQL（Schema 与 Database 解耦），PolarDB 的权限行为与 MySQL 一致。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/polardb.md) | **PREPARE/EXECUTE（MySQL 兼容）**——存储过程内使用 PREPARE 和 EXECUTE 执行动态 SQL。对比 MySQL（相同语法）和 PostgreSQL 的 EXECUTE（PL/pgSQL），PolarDB 的动态 SQL 与 MySQL 一致。 |
| [错误处理](../advanced/error-handling/polardb.md) | **DECLARE HANDLER（MySQL 兼容）**——DECLARE CONTINUE/EXIT HANDLER FOR SQLEXCEPTION 捕获异常。对比 MySQL（相同语法）和 PostgreSQL 的 EXCEPTION WHEN（PL/pgSQL，更灵活），PolarDB 的错误处理与 MySQL 存储过程模型一致。 |
| [执行计划](../advanced/explain/polardb.md) | **EXPLAIN ANALYZE（MySQL 兼容）+ 并行查询计划展示**——显示 Parallel Query 的并行度和工作线程分配。EXPLAIN FORMAT=TREE 展示更直观的执行树。对比 MySQL 8.0（EXPLAIN ANALYZE 较新）和 PostgreSQL（EXPLAIN ANALYZE 最成熟），PolarDB 在执行计划中额外显示并行查询信息。 |
| [锁机制](../advanced/locking/polardb.md) | **InnoDB 行锁（MySQL 兼容）+ 共享存储全局一致性读**——只读节点通过 Redo Log Shipping 保持与主节点的数据一致性，延迟毫秒级。对比 MySQL 主从（逻辑复制，延迟可能较大）和 Aurora（类似物理复制），PolarDB 的共享存储确保只读节点看到最新数据。 |
| [分区](../advanced/partitioning/polardb.md) | **RANGE/LIST/HASH 分区（MySQL 兼容）+ 分区表并行扫描**——大分区表查询可自动利用多核并行扫描不同分区。AUTO 分区功能可自动按值创建新分区。对比 MySQL（分区标准，单线程扫描）和 Oracle（分区功能最丰富），PolarDB 的并行分区扫描是对 MySQL 分区性能的显著增强。 |
| [权限](../advanced/permissions/polardb.md) | **MySQL 兼容权限模型**——GRANT/REVOKE 标准语法。阿里云 RAM 权限体系叠加数据库内权限实现细粒度控制。对比 MySQL（相同权限模型）和 PostgreSQL 的 RLS（行级安全），PolarDB 的权限模型与 MySQL 一致，云上安全通过 RAM 增强。 |
| [存储过程](../advanced/stored-procedures/polardb.md) | **MySQL 兼容存储过程**——CREATE PROCEDURE/FUNCTION 标准语法。功能范围与 MySQL 一致（无 Package，功能弱于 PL/pgSQL/PL/SQL）。对比 MySQL（存储过程功能有限）和 PostgreSQL 的 PL/pgSQL（功能丰富），PolarDB 继承了 MySQL 存储过程的局限性。 |
| [临时表](../advanced/temp-tables/polardb.md) | **TEMPORARY TABLE（MySQL 兼容）**——CREATE TEMPORARY TABLE 创建会话级临时表，仅当前连接可见。对比 MySQL（相同行为）和 PostgreSQL（CREATE TEMP TABLE），PolarDB 的临时表行为与 MySQL 一致。 |
| [事务](../advanced/transactions/polardb.md) | **InnoDB MVCC（MySQL 兼容）+ 共享存储强一致**——事务隔离级别（READ COMMITTED/REPEATABLE READ/SERIALIZABLE）与 MySQL 一致。共享存储层通过物理复制保证读写节点和只读节点之间的事务一致性。对比 MySQL 主从（异步复制可能丢数据）和 Aurora（类似强一致），PolarDB 在事务一致性上超越原生 MySQL。 |
| [触发器](../advanced/triggers/polardb.md) | **MySQL 兼容触发器**——BEFORE/AFTER 行级触发器，功能范围与 MySQL 一致。对比 MySQL（触发器功能基础）和 PostgreSQL（BEFORE/AFTER/INSTEAD OF + 行级/语句级），PolarDB 继承 MySQL 触发器的局限。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/polardb.md) | **DELETE（MySQL 兼容）+ Parallel DML 加速**——大表 DELETE 可利用多核并行执行，显著减少操作时间。对比 MySQL（单线程 DELETE）和 PostgreSQL（无并行 DML），PolarDB 的 Parallel DML 是对 MySQL DML 性能的核心增强。 |
| [插入](../dml/insert/polardb.md) | **INSERT（MySQL 兼容）+ Parallel INSERT 加速**——批量 INSERT 可并行写入多个页面。LOAD DATA 批量导入也支持并行。对比 MySQL（单线程 INSERT）和 BigQuery（批量加载免费），PolarDB 的 Parallel INSERT 在大批量写入场景下优势明显。 |
| [更新](../dml/update/polardb.md) | **UPDATE（MySQL 兼容）+ Parallel DML**——多核并行更新大批量行。对比 MySQL（单线程 UPDATE）和 PostgreSQL（无并行 DML），PolarDB 的并行 UPDATE 减少大批量更新的等待时间。 |
| [Upsert](../dml/upsert/polardb.md) | **ON DUPLICATE KEY UPDATE（MySQL 兼容）**——基于唯一键/主键冲突自动转为 UPDATE。REPLACE INTO 也可用（先删后插语义）。对比 MySQL（相同语法）和 PostgreSQL 的 ON CONFLICT（功能类似但语法不同），PolarDB 的 Upsert 与 MySQL 一致。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/polardb.md) | **MySQL 兼容聚合 + 并行聚合加速**——GROUP BY 聚合查询可利用多核并行执行。GROUP_CONCAT 拼接字符串。对比 MySQL（GROUP_CONCAT 原生，单线程聚合）和 PostgreSQL 的 string_agg（功能类似），PolarDB 的并行聚合在大数据量下显著提速。 |
| [条件函数](../functions/conditional/polardb.md) | **IF/CASE/IFNULL/NULLIF/COALESCE（MySQL 兼容）**——IF(expr, val_true, val_false) 是 MySQL 特有的三元函数。CASE WHEN 标准语法同时支持。对比 MySQL（IF 函数原生）和 PostgreSQL（无 IF 函数，需用 CASE），PolarDB 的条件函数与 MySQL 一致。 |
| [日期函数](../functions/date-functions/polardb.md) | **MySQL 兼容日期函数**——DATE_FORMAT/STR_TO_DATE/DATE_ADD/DATEDIFF 等 MySQL 风格函数。对比 MySQL（相同函数集）和 PostgreSQL 的 to_char/date_trunc（不同命名），PolarDB 的日期函数与 MySQL 完全一致。 |
| [数学函数](../functions/math-functions/polardb.md) | **MySQL 兼容数学函数**——MOD/CEIL/FLOOR/ROUND/TRUNCATE/POWER/SQRT 完整。对比 MySQL（相同函数集）和 PostgreSQL（函数名相同但行为可能有微小差异），PolarDB 的数学函数与 MySQL 对齐。 |
| [字符串函数](../functions/string-functions/polardb.md) | **MySQL 兼容字符串函数**——CONCAT/CONCAT_WS/SUBSTR/LOCATE/REPLACE/TRIM。CONCAT 函数拼接（而非 \|\| 运算符）。对比 MySQL（CONCAT 函数是主要拼接方式）和 PostgreSQL（\|\| 运算符为主），PolarDB 的字符串处理与 MySQL 一致。 |
| [类型转换](../functions/type-conversion/polardb.md) | **CAST/CONVERT（MySQL 兼容）**——MySQL 风格隐式转换较宽松（如字符串自动转数值），需注意潜在的数据精度问题。对比 MySQL（宽松隐式转换）和 PostgreSQL（严格类型检查），PolarDB 继承了 MySQL 的转换行为。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/polardb.md) | **递归 CTE（MySQL 8.0 兼容）**——WITH RECURSIVE 支持层级查询和数据生成。对比 MySQL 8.0（CTE 是 8.0 重要新特性）和 PostgreSQL（CTE 支持更早），PolarDB 的 CTE 能力与 MySQL 8.0 对齐。 |
| [全文搜索](../query/full-text-search/polardb.md) | **InnoDB FULLTEXT 索引（MySQL 兼容）+ ngram 中文分词**——ngram parser 支持 CJK 语言的全文检索。对比 MySQL（InnoDB FULLTEXT + ngram 原生）和 PostgreSQL 的 tsvector+GIN（分词更灵活），PolarDB 的全文搜索与 MySQL 一致。 |
| [连接查询](../query/joins/polardb.md) | **MySQL 兼容 JOIN + Parallel Hash JOIN 加速**——大表 JOIN 自动利用多核并行执行 Hash JOIN，显著提升分析查询性能。对比 MySQL（Hash JOIN 8.0+ 支持，单线程）和 PostgreSQL（Parallel Hash JOIN 原生），PolarDB 的并行 JOIN 是对 MySQL JOIN 性能的核心增强。 |
| [分页](../query/pagination/polardb.md) | **LIMIT/OFFSET（MySQL 兼容）**——标准分页语法。深度分页时推荐使用 Keyset Pagination（基于上一页最后 ID 过滤）。对比 MySQL（LIMIT/OFFSET 标准）和 PostgreSQL（相同语法），PolarDB 的分页与 MySQL 一致。 |
| [行列转换](../query/pivot-unpivot/polardb.md) | **无原生 PIVOT（同 MySQL）**——需使用 CASE + GROUP BY 手动实现行列转换。对比 MySQL（同样无 PIVOT）和 Oracle/BigQuery（原生 PIVOT 支持），PolarDB 继承了 MySQL 在行列转换上的局限。 |
| [集合操作](../query/set-operations/polardb.md) | **UNION/INTERSECT/EXCEPT（MySQL 8.0 兼容）**——INTERSECT 和 EXCEPT 是 MySQL 8.0.31+ 新增。对比 MySQL 8.0（INTERSECT/EXCEPT 较新）和 PostgreSQL（早已支持），PolarDB 同步了 MySQL 的集合操作更新。 |
| [子查询](../query/subquery/polardb.md) | **MySQL 兼容子查询优化 + 并行加速**——MySQL 8.0 的子查询优化（如 Derived Table Merge）在 PolarDB 中可用，并行查询可进一步加速。对比 MySQL 8.0（子查询优化大幅改善）和 PostgreSQL（优化器更成熟），PolarDB 的并行加速弥补了 MySQL 优化器的部分差距。 |
| [窗口函数](../query/window-functions/polardb.md) | **MySQL 8.0 兼容窗口函数 + 并行执行**——ROW_NUMBER/RANK/DENSE_RANK/LAG/LEAD 等完整支持。并行查询下窗口函数可利用多核加速。对比 MySQL 8.0（窗口函数完整，单线程）和 PostgreSQL（并行查询原生），PolarDB 的并行窗口函数是对 MySQL 的重要增强。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/polardb.md) | **递归 CTE 生成日期序列（MySQL 兼容）**——`WITH RECURSIVE dates AS (SELECT '2024-01-01' AS d UNION ALL SELECT d + INTERVAL 1 DAY FROM dates WHERE d < '2024-12-31')` 生成日期序列。对比 PostgreSQL 的 generate_series（更简洁）和 BigQuery 的 GENERATE_DATE_ARRAY，PolarDB 沿用 MySQL 递归 CTE 方式。 |
| [去重](../scenarios/deduplication/polardb.md) | **ROW_NUMBER + CTE（MySQL 兼容）**——MySQL 8.0 的窗口函数 + CTE 实现标准去重模式。对比 PostgreSQL 的 DISTINCT ON（更简洁）和 BigQuery 的 QUALIFY（最简洁），PolarDB 的去重方案与 MySQL 8.0 一致。 |
| [区间检测](../scenarios/gap-detection/polardb.md) | **窗口函数 LAG/LEAD（MySQL 兼容）**——检测序列中的间隙和重叠。对比 PostgreSQL 的 generate_series（可生成完整序列对比）和 MySQL 8.0（仅窗口函数），PolarDB 方案与 MySQL 一致。 |
| [层级查询](../scenarios/hierarchical-query/polardb.md) | **递归 CTE（MySQL 兼容）**——WITH RECURSIVE 实现 parent-child 层级遍历。对比 MySQL 8.0（递归 CTE 是唯一选择）和 Oracle（CONNECT BY + 递归 CTE），PolarDB 在层级查询上与 MySQL 8.0 对齐。 |
| [JSON 展开](../scenarios/json-flatten/polardb.md) | **JSON_TABLE（MySQL 兼容）**——将 JSON 数组展开为关系行。JSON_EXTRACT/JSON_VALUE 路径查询。对比 MySQL 8.0（JSON_TABLE 原生）和 PostgreSQL 的 jsonb_array_elements（PG 特有），PolarDB 的 JSON 处理与 MySQL 一致。 |
| [迁移速查](../scenarios/migration-cheatsheet/polardb.md) | **MySQL 高度兼容是基础，计算存储分离 + 并行查询是核心增值**。关键差异：共享存储架构使只读扩展秒级完成；Parallel Query 对分析查询加速显著；IMCI 列存索引补充 OLAP 能力；Serverless 弹性按需扩缩。迁移时 SQL 几乎零改动，但需理解存储和并行特性以充分利用。 |
| [TopN 查询](../scenarios/ranking-top-n/polardb.md) | **ROW_NUMBER + LIMIT（MySQL 兼容）**——标准 TopN 方案，并行查询可加速排序。对比 MySQL 8.0（相同方案，单线程排序）和 BigQuery（QUALIFY 更简洁），PolarDB 的并行排序是 TopN 性能增值。 |
| [累计求和](../scenarios/running-total/polardb.md) | **SUM() OVER(ORDER BY ...)（MySQL 兼容）+ 并行执行**——标准窗口累计，并行查询可加速大表计算。对比 MySQL 8.0（单线程窗口函数）和各主流引擎（写法一致），PolarDB 的并行窗口函数是性能差异化。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/polardb.md) | **ON DUPLICATE KEY UPDATE（MySQL 兼容）**——基于唯一键冲突实现 SCD Type 1。Type 2 需要额外的版本管理逻辑。对比 MySQL（相同语法）和 PostgreSQL 的 ON CONFLICT（功能类似），PolarDB 的 Upsert 方案与 MySQL 一致。 |
| [字符串拆分](../scenarios/string-split-to-rows/polardb.md) | **JSON_TABLE 或递归 CTE（MySQL 兼容）**——MySQL 8.0 可用 JSON_TABLE 将 JSON 数组展开，或递归 CTE 逐字符拆分。对比 PostgreSQL 的 string_to_array+unnest（最简洁）和 BigQuery 的 SPLIT+UNNEST，PolarDB 的拆分方案与 MySQL 一致但较复杂。 |
| [窗口分析](../scenarios/window-analytics/polardb.md) | **MySQL 兼容窗口函数 + 并行加速**——移动平均、同环比、占比计算全覆盖。并行查询对大表窗口分析加速明显。对比 MySQL 8.0（单线程窗口函数）和 PostgreSQL（并行查询原生），PolarDB 的并行窗口分析是核心增值。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/polardb.md) | **无 ARRAY/STRUCT 列类型（同 MySQL）**——需用 JSON 类型存储结构化/数组数据。对比 MySQL（同样无 ARRAY/STRUCT）和 PostgreSQL（ARRAY 原生支持），PolarDB 继承了 MySQL 的类型系统局限，JSON 是替代方案。 |
| [日期时间](../types/datetime/polardb.md) | **DATETIME/TIMESTAMP（MySQL 兼容）**——DATETIME 无时区（存储字面量），TIMESTAMP 有时区转换（UTC 存储）。对比 MySQL（DATETIME vs TIMESTAMP 是经典困惑点）和 PostgreSQL（TIMESTAMP vs TIMESTAMPTZ 更清晰），PolarDB 的时间类型行为与 MySQL 一致。 |
| [JSON](../types/json/polardb.md) | **JSON 二进制存储（MySQL 兼容）+ 多值索引**——MySQL 8.0 的 JSON 类型以二进制格式高效存储。Multi-Valued Index 可对 JSON 数组中的值建索引。对比 MySQL 8.0（多值索引原生）和 PostgreSQL 的 JSONB+GIN（功能更强），PolarDB 同步了 MySQL 的 JSON 多值索引能力。 |
| [数值类型](../types/numeric/polardb.md) | **MySQL 兼容数值类型**——TINYINT/SMALLINT/MEDIUMINT/INT/BIGINT/DECIMAL/FLOAT/DOUBLE 完整体系。UNSIGNED 修饰符（MySQL 特有，SQL 标准无此概念）可用。对比 MySQL（相同类型体系）和 PostgreSQL（无 UNSIGNED、无 MEDIUMINT），PolarDB 在数值类型上与 MySQL 一致。 |
| [字符串类型](../types/string/polardb.md) | **utf8mb4 推荐（MySQL 兼容）**——utf8mb4 是 MySQL 中真正的 4 字节 UTF-8 编码（MySQL 的 utf8 是 3 字节截断版本）。VARCHAR(n)/CHAR(n)/TEXT/LONGTEXT 标准体系。对比 MySQL（utf8mb4 推荐）和 PostgreSQL（UTF-8 原生完整支持），PolarDB 的字符集行为与 MySQL 一致。 |
