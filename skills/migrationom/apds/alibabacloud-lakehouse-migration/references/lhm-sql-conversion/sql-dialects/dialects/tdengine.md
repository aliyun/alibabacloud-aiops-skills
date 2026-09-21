# TDengine

**分类**: 时序数据库（涛思数据）
**文件数**: 51 个 SQL 文件
**总行数**: 4093 行

## 概述与定位

TDengine 是涛思数据（TAOS Data）于 2019 年开源的高性能时序数据库，专门为 IoT、工业互联网和运维监控等海量时序数据场景设计。与通用关系型数据库不同，TDengine 围绕"一个设备/采集点一张表"的数据模型重新设计了存储引擎和查询语言，追求极致的写入速度和查询性能。它内置了流式计算、缓存和数据订阅能力，目标是替代"时序数据库 + 消息队列 + 缓存"的传统架构组合。

## 历史与演进

- **2017 年**：涛思数据公司成立，启动 TDengine 研发。
- **2019 年 7 月**：TDengine 开源，首日获得 GitHub 数千 Star。
- **2020 年**：2.0 引入集群支持和多副本复制。
- **2021 年**：增强 SQL 兼容性和用户自定义函数（UDF）。
- **2022 年**：3.0 重大重构——引入存储计算分离、流计算引擎和 Vnode/Mnode 新架构。
- **2023-2025 年**：持续优化分布式性能、增强 SQL 兼容性和云服务能力。

## 核心设计思路

TDengine 的数据模型围绕**超级表（Super Table）、子表（Sub Table）和标签（Tag）** 三层抽象设计。超级表定义数据 Schema 和标签 Schema；每个采集点（设备/传感器）对应一张子表，子表通过标签值与超级表关联。查询时可按标签过滤子表（类似维度筛选），也可对超级表做聚合（自动跨所有子表计算）。存储引擎针对时序数据优化——数据按时间戳排序、列式存储、高效压缩，每个子表的最新值自动缓存（替代 Redis 的角色）。

## 独特特色

- **超级表/子表/标签模型**：`CREATE STABLE meters (ts TIMESTAMP, voltage FLOAT) TAGS (location NCHAR(64), groupId INT)` 定义设备模板。
- **INTERVAL/SLIDING/FILL**：`SELECT AVG(voltage) FROM meters INTERVAL(10m) SLIDING(5m) FILL(PREV)` 滑动窗口聚合并自动填充缺失值。
- **CSUM/TWA/IRATE**：内置时序专用函数——累积求和（CSUM）、时间加权平均（TWA）、瞬时变化率（IRATE）。
- **数据订阅**：消费者组模式订阅数据变更，替代外部消息队列。
- **流式计算**：`CREATE STREAM` 定义实时流计算管道，支持滑动窗口和事件窗口。
- **数据保留策略**：`CREATE DATABASE ... KEEP 365` 自动过期删除。
- **最新值缓存**：每个子表的最新一行数据自动缓存在内存中，用 `LAST_ROW()` 查询。

## 已知不足

- SQL 语法与标准 SQL 差异较大——不支持 JOIN（3.0 开始有限支持）、子查询能力有限。
- 不支持事务（ACID），无法用于需要事务保证的通用 OLTP 场景。
- UPDATE 和 DELETE 能力有限（3.0 开始改善，但仍非核心设计目标）。
- 每个数据库所有表必须共享相同的时间精度（毫秒/微秒/纳秒）。
- 标签值修改需要整表操作，动态标签管理不够灵活。
- 非时序查询场景（如全文搜索、复杂关联分析）需要借助外部系统。

## 对引擎开发者的参考价值

TDengine 的"一设备一表"数据模型是时序数据库领域的独特设计——通过超级表+标签将设备元数据与时序数据绑定，避免了通用数据库中高基数 GROUP BY 的性能问题。其列式存储 + 时间排序 + 针对性压缩的存储引擎设计展示了领域特化的存储优化。内置流计算和数据订阅的"一站式"设计思路也代表了从单一数据库向数据平台演进的趋势。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/tdengine.md) | **超级表+子表+标签三层模型**——`CREATE STABLE meters (ts TIMESTAMP, voltage FLOAT) TAGS (location NCHAR(64), groupId INT)` 定义设备模板，每个采集点一张子表。`INSERT INTO d001 USING meters TAGS ("Beijing", 1) VALUES (...)` 自动建表并写入。对比 TimescaleDB（Hypertable 单表模型）和 InfluxDB（measurement+tag 模型），TDengine 的一设备一表模型在高基数场景下写入性能极高。 |
| [改表](../ddl/alter-table/tdengine.md) | **ALTER ADD TAG/COLUMN——超级表变更自动同步到所有子表**。修改超级表 Schema 后，已存在的子表自动继承变更。对比 TimescaleDB（ALTER 对 Hypertable 透明）和 PostgreSQL（ALTER 标准），TDengine 的超级表 Schema 同步是独特设计。 |
| [索引](../ddl/indexes/tdengine.md) | **SMA 预计算索引（独有）+ Tag 索引 + 时间列自动索引**——SMA（Small Materialized Aggregation）在写入时预计算 MIN/MAX/SUM 等聚合值，查询时直接读取预计算结果。Tag 索引加速按标签过滤。对比 TimescaleDB（Continuous Aggregate 类似预计算）和 InfluxDB（TSI 索引），TDengine 的 SMA 是写入时预聚合的独特优化。 |
| [约束](../ddl/constraints/tdengine.md) | **无传统约束——TIMESTAMP 主键必须**。每张表的第一列必须是 TIMESTAMP 类型且为主键。无 FK/CHECK/UNIQUE 约束（时序追加写入模型不需要传统约束）。对比 PostgreSQL（完整约束）和 TimescaleDB（PG 约束继承），TDengine 的约束模型完全面向时序场景。 |
| [视图](../ddl/views/tdengine.md) | **CREATE STREAM 流式计算替代传统视图**——`CREATE STREAM s INTO result_table AS SELECT ... FROM meters INTERVAL(1m)` 定义实时流计算管道，结果自动写入目标表。对比 PostgreSQL（CREATE VIEW 标准）和 TimescaleDB（Continuous Aggregate），TDengine 用流式计算替代了视图和物化视图的角色。 |
| [序列与自增](../ddl/sequences/tdengine.md) | **无 SEQUENCE——TIMESTAMP 主键天然有序**。时序数据以时间戳为主键，不需要自增序列。对比 PostgreSQL 的 SERIAL/IDENTITY 和 TimescaleDB（SERIAL 可选），TDengine 完全以时间戳驱动数据排序。 |
| [数据库/Schema/用户](../ddl/users-databases/tdengine.md) | **Database 级别隔离 + VNODE 分片 + 用户权限**——每个 Database 可配置独立的数据保留策略（KEEP）、时间精度和副本数。数据在 VNODE 间自动分片。对比 PostgreSQL（Database/Schema 二级）和 TimescaleDB（PG 权限继承），TDengine 的 Database 级隔离专为多租户时序场景设计。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/tdengine.md) | **无动态 SQL**——时序引擎定位不提供过程化编程。对比 PostgreSQL 的 EXECUTE 和 TimescaleDB（PG 能力继承），TDengine 将过程化逻辑委托给应用层。 |
| [错误处理](../advanced/error-handling/tdengine.md) | **无过程式错误处理**——错误通过客户端 API 返回。UDF（C/Python）内可做错误处理。对比 PostgreSQL 的 EXCEPTION WHEN 和 TimescaleDB（PG 能力继承），TDengine 的错误处理完全依赖客户端。 |
| [执行计划](../advanced/explain/tdengine.md) | **EXPLAIN 查看执行计划**——显示查询的超级表扫描、Tag 过滤和 VNODE 分布信息。对比 PostgreSQL 的 EXPLAIN ANALYZE（更详细）和 TimescaleDB（Chunk 裁剪信息），TDengine 的执行计划帮助识别 Tag 过滤和 VNODE 扫描范围。 |
| [锁机制](../advanced/locking/tdengine.md) | **无行级锁——时序追加写入 + VNODE 级别并发**。时序数据按时间戳追加写入，不同 VNODE 的写入互不阻塞。对比 PostgreSQL（行级 MVCC 锁）和 TimescaleDB（Chunk 级并发），TDengine 的无锁追加写入是极高写入吞吐的基础。 |
| [分区](../advanced/partitioning/tdengine.md) | **自动按时间分 VNODE（核心）+ 超级表按 Tag 分组**——数据按时间范围自动分配到不同 VNODE，按 Tag 值将子表分组到相同 VNODE。对比 TimescaleDB（Hypertable 按时间分 Chunk）和 InfluxDB（shard 按时间分片），TDengine 的 VNODE 分片兼顾时间和标签两个维度。 |
| [权限](../advanced/permissions/tdengine.md) | **用户 + 权限管理——READ/WRITE/ALL**。简单的三级权限模型。对比 PostgreSQL 的 RBAC（细粒度）和 TimescaleDB（PG 权限继承），TDengine 的权限模型简洁但功能有限。 |
| [存储过程](../advanced/stored-procedures/tdengine.md) | **无存储过程——UDF（C/Python）支持**。用户可用 C 或 Python 编写自定义函数注册到 TDengine。对比 PostgreSQL 的 PL/pgSQL（完整过程语言）和 TimescaleDB（PG 能力继承），TDengine 通过 UDF 提供有限的可编程性。 |
| [临时表](../advanced/temp-tables/tdengine.md) | **无临时表**——时序引擎不提供临时表概念。中间结果需通过子查询或应用层处理。对比 PostgreSQL（CREATE TEMP TABLE）和 TimescaleDB（PG 能力继承），TDengine 缺少临时表。 |
| [事务](../advanced/transactions/tdengine.md) | **无传统事务——时序追加写入 + 最终一致性**。不支持 BEGIN/COMMIT/ROLLBACK，每条写入操作独立执行。对比 PostgreSQL（完整 ACID）和 TimescaleDB（ACID 事务），事务缺失是 TDengine 区别于关系型数据库的核心差异——这是时序引擎为写入吞吐做出的设计取舍。 |
| [触发器](../advanced/triggers/tdengine.md) | **Stream 流式计算替代触发器**——CREATE STREAM 定义实时流处理管道，数据写入时自动触发计算。对比 PostgreSQL（BEFORE/AFTER 触发器）和 ksqlDB（持续查询），TDengine 用流式计算实现了类似触发器的事件驱动能力。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/tdengine.md) | **DELETE 按时间范围删除——不支持条件删除单行**。`DELETE FROM meters WHERE ts < "2024-01-01"` 按时间范围批量删除。对比 PostgreSQL（任意条件 DELETE）和 TimescaleDB 的 drop_chunks（按 Chunk 高效删除），TDengine 的删除以时间范围为单位。 |
| [插入](../dml/insert/tdengine.md) | **INSERT 多行/多表批量写入（独有高效语法）**——`INSERT INTO d001 VALUES (...) (...) d002 VALUES (...) (...)` 一条语句同时写入多张子表多行数据。对比 PostgreSQL（INSERT 多行但单表）和 TimescaleDB（INSERT 标准），TDengine 的多表批量 INSERT 是极高写入吞吐的关键语法。 |
| [更新](../dml/update/tdengine.md) | **相同时间戳 INSERT 覆盖——时序 Upsert 语义**。INSERT 相同主键（时间戳）的数据自动覆盖旧值，无需显式 UPDATE 语句。对比 PostgreSQL 的 UPDATE（显式更新）和 TimescaleDB 的 ON CONFLICT（PG Upsert），TDengine 的时序覆盖写入是最简洁的 Upsert 实现。 |
| [Upsert](../dml/upsert/tdengine.md) | **INSERT 相同时间戳自动覆盖——时序天然 Upsert**。无需 MERGE 或 ON CONFLICT 语法，INSERT 即 Upsert。对比 PostgreSQL 的 ON CONFLICT（需指定冲突列）和 Impala 的 UPSERT（Kudu 原生），TDengine 的时间戳覆盖是最自然的时序 Upsert。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/tdengine.md) | **APERTURE/CSUM/DERIVATIVE/IRATE——时序专有聚合函数**。CSUM 累积求和，TWA 时间加权平均，IRATE 瞬时变化率，DERIVATIVE 导数计算。对比 PostgreSQL（需窗口函数手动计算）和 TimescaleDB（PG 函数+time_bucket），TDengine 的内置时序聚合函数是其核心竞争力。 |
| [条件函数](../functions/conditional/tdengine.md) | **IF/CASE 基础支持**——3.0+ 引入 CASE WHEN 标准语法。对比 PostgreSQL（CASE/COALESCE/NULLIF 完整）和 TimescaleDB（PG 函数继承），TDengine 的条件函数较基础。 |
| [日期函数](../functions/date-functions/tdengine.md) | **NOW/TIMETRUNCATE/TIMEDIFF——时序时间函数**。TIMETRUNCATE 按指定精度截断时间戳（类似 date_trunc）。NOW() 返回当前时间用于实时查询。对比 PostgreSQL 的 date_trunc（功能类似）和 TimescaleDB 的 time_bucket（更灵活），TDengine 的时间函数专为时序场景设计。 |
| [数学函数](../functions/math-functions/tdengine.md) | **基础数学函数 + SPREAD/TWA 时序计算（独有）**——SPREAD 计算最大值与最小值的差值，TWA 时间加权平均。对比 PostgreSQL（完整数学函数但无 SPREAD/TWA）和 TimescaleDB（需窗口函数手动计算），TDengine 的时序数学函数是领域特化优势。 |
| [字符串函数](../functions/string-functions/tdengine.md) | **CONCAT/SUBSTR/LENGTH 基础函数**——字符串处理能力有限，时序场景下字符串操作需求较少。对比 PostgreSQL（完整字符串函数）和 TimescaleDB（PG 函数继承），TDengine 的字符串函数是最精简的。 |
| [类型转换](../functions/type-conversion/tdengine.md) | **CAST 基础转换**——支持基本类型间的转换。对比 PostgreSQL 的 :: 运算符（更简洁）和 TimescaleDB（PG 转换继承），TDengine 的类型转换功能基础。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/tdengine.md) | **不支持 CTE**——无 WITH 子句，复杂查询需用嵌套子查询。对比 PostgreSQL（WITH RECURSIVE 完整）和 TimescaleDB（PG CTE 继承），CTE 缺失限制了 TDengine 的查询表达能力。 |
| [全文搜索](../query/full-text-search/tdengine.md) | **不支持全文搜索**——时序引擎不提供文本搜索能力。对比 PostgreSQL 的 tsvector+GIN 和 TimescaleDB（PG 全文搜索继承），TDengine 缺少文本搜索。 |
| [连接查询](../query/joins/tdengine.md) | **JOIN 有限支持——超级表+子表 JOIN，无复杂 JOIN**。3.0 开始支持基本 JOIN，但不支持 FULL/CROSS JOIN 和复杂多表关联。对比 PostgreSQL（完整 JOIN 支持）和 TimescaleDB（PG JOIN 继承），TDengine 的 JOIN 是时序数据库中最大的 SQL 局限之一。 |
| [分页](../query/pagination/tdengine.md) | **LIMIT/OFFSET + SLIMIT/SOFFSET 超级表分组分页（独有）**——SLIMIT 限制返回的子表数量，SOFFSET 跳过前 N 个子表。对比 PostgreSQL（仅 LIMIT/OFFSET）和 TimescaleDB（PG 分页标准），TDengine 的 SLIMIT/SOFFSET 是超级表模型的独有分页维度。 |
| [行列转换](../query/pivot-unpivot/tdengine.md) | **无 PIVOT 支持**——需应用层处理行列转换。对比 Oracle（PIVOT 原生）和 BigQuery（PIVOT 原生），TDengine 缺少行列转换能力。 |
| [集合操作](../query/set-operations/tdengine.md) | **UNION/UNION ALL 支持——无 INTERSECT/EXCEPT**。对比 PostgreSQL（UNION/INTERSECT/EXCEPT 完整）和 TimescaleDB（PG 集合操作继承），TDengine 的集合操作有限。 |
| [子查询](../query/subquery/tdengine.md) | **嵌套子查询支持（有限）**——支持基本的嵌套子查询，但不支持关联子查询和复杂嵌套。对比 PostgreSQL（关联子查询完整）和 TimescaleDB（PG 子查询继承），TDengine 的子查询能力是时序数据库的通用限制。 |
| [窗口函数](../query/window-functions/tdengine.md) | **STATE_WINDOW/SESSION_WINDOW/EVENT_WINDOW——时序窗口（独有）**。STATE_WINDOW 按状态值分组（值变化时开启新窗口），SESSION_WINDOW 按时间间隙分组（超过阈值开启新窗口），EVENT_WINDOW 按条件表达式分组。对比 PostgreSQL（ROWS/RANGE 帧标准窗口）和 TimescaleDB（PG 窗口函数），TDengine 的时序窗口是传统 SQL 窗口函数的领域特化替代。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/tdengine.md) | **FILL(PREV/NEXT/LINEAR/VALUE)——时序填充（独有核心功能）**。`SELECT AVG(temp) FROM meters INTERVAL(1h) FILL(PREV)` 自动用上一个值填充缺失时间桶。对比 TimescaleDB 的 time_bucket_gapfill+locf（类似）和 PostgreSQL（需手动 LEFT JOIN），TDengine 的 FILL 语法是最简洁的内置时序填充方案。 |
| [去重](../scenarios/deduplication/tdengine.md) | **UNIQUE 函数（独有）——按列去重取最新值**。`SELECT UNIQUE(voltage) FROM meters` 按指定列去重保留时间最新的行。对比 PostgreSQL 的 DISTINCT ON（类似但语法不同）和 BigQuery 的 QUALIFY，TDengine 的 UNIQUE 函数是时序去重的独特简洁方案。 |
| [区间检测](../scenarios/gap-detection/tdengine.md) | **INTERVAL + FILL 检测时序间隙（独有）**——FILL(NONE) 跳过空桶，FILL(NULL) 显示空桶为 NULL，比较两者可识别数据间隙。对比 TimescaleDB 的 time_bucket_gapfill（类似自动检测）和 PostgreSQL 的 generate_series+LEFT JOIN，TDengine 的 INTERVAL+FILL 是最简洁的间隙检测方案。 |
| [层级查询](../scenarios/hierarchical-query/tdengine.md) | **不支持层级查询**——无递归 CTE、无 CONNECT BY。层级关系需在应用层处理。对比 PostgreSQL（WITH RECURSIVE）和 TimescaleDB（PG 递归 CTE），TDengine 的查询能力聚焦时序而非关系建模。 |
| [JSON 展开](../scenarios/json-flatten/tdengine.md) | **TAG 为 JSON 类型时可查询 + JSON_EXTRACT**——TAG 列支持 JSON 类型，可通过 `->` 或 json_extract 路径查询。对比 PostgreSQL 的 JSONB+GIN（功能最强）和 TimescaleDB（PG JSONB 继承），TDengine 的 JSON 支持聚焦于 TAG 元数据场景。 |
| [迁移速查](../scenarios/migration-cheatsheet/tdengine.md) | **超级表/子表模型 + 时序语法 + 无事务是核心差异**。关键注意：一设备一表模型与关系模型完全不同；INTERVAL/SLIDING/FILL 是核心时序查询语法；无事务、无 CTE、JOIN 有限；STATE/SESSION/EVENT_WINDOW 替代标准窗口函数；CSUM/TWA/IRATE 等时序函数独有；SLIMIT/SOFFSET 超级表分页独有。 |
| [TopN 查询](../scenarios/ranking-top-n/tdengine.md) | **TOP/BOTTOM 函数（独有）——取极值行**。`SELECT TOP(voltage, 10) FROM meters` 返回 voltage 最大的 10 行（含完整行数据）。对比 PostgreSQL 的 ROW_NUMBER+LIMIT（需子查询包装）和 BigQuery 的 QUALIFY，TDengine 的 TOP/BOTTOM 是最简洁的 TopN 实现。 |
| [累计求和](../scenarios/running-total/tdengine.md) | **CSUM 累计求和函数（独有）**——`SELECT CSUM(flow) FROM meters` 直接计算累计求和。对比 PostgreSQL 的 SUM() OVER(ORDER BY ...)（标准窗口函数）和 TimescaleDB（PG 窗口函数继承），TDengine 的 CSUM 是最简洁的累计求和实现。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/tdengine.md) | **不适用**——时序引擎不处理维度表维护。维度数据管理需在外部关系数据库中完成。对比 PostgreSQL 的 ON CONFLICT/MERGE 和 TimescaleDB（PG Upsert 继承），TDengine 不涉及 SCD 场景。 |
| [字符串拆分](../scenarios/string-split-to-rows/tdengine.md) | **不支持字符串拆分展开**——需在应用层处理。对比 PostgreSQL 的 string_to_array+unnest 和 TimescaleDB（PG 拆分继承），TDengine 缺少字符串拆分能力。 |
| [窗口分析](../scenarios/window-analytics/tdengine.md) | **INTERVAL/STATE/SESSION/EVENT_WINDOW——时序窗口分析（独有）**。四种窗口类型覆盖时序分析的核心场景：INTERVAL 定时聚合，STATE 状态变化分组，SESSION 会话间隙分组，EVENT 条件触发分组。对比 PostgreSQL 的 ROWS/RANGE 帧（标准窗口）和 TimescaleDB（PG 窗口+time_bucket），TDengine 的时序窗口类型是领域特化的独特设计。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/tdengine.md) | **无 ARRAY/STRUCT——TAG 支持 JSON 类型**。TAG 列可使用 JSON 存储设备元数据的灵活属性。对比 PostgreSQL 的 ARRAY（原生）和 BigQuery 的 STRUCT/ARRAY，TDengine 仅通过 JSON TAG 提供半结构化数据支持。 |
| [日期时间](../types/datetime/tdengine.md) | **TIMESTAMP 纳秒精度（核心类型）——无 DATE/TIME**。每个数据库创建时指定时间精度（毫秒/微秒/纳秒），所有表共享相同精度。对比 PostgreSQL（DATE/TIME/TIMESTAMP/INTERVAL 完整）和 TimescaleDB（PG 时间类型继承），TDengine 以单一 TIMESTAMP 类型覆盖所有时间需求。 |
| [JSON](../types/json/tdengine.md) | **JSON TAG 类型 + json_extract 路径查询**——仅 TAG 列支持 JSON 类型，数据列不支持。对比 PostgreSQL 的 JSONB（任意列可用+GIN 索引）和 TimescaleDB（PG JSONB 继承），TDengine 的 JSON 限于设备元数据场景。 |
| [数值类型](../types/numeric/tdengine.md) | **TINYINT-BIGINT/FLOAT/DOUBLE/BOOL——无 DECIMAL**。缺少定点十进制类型，金融场景不适用。对比 PostgreSQL 的 NUMERIC（任意精度定点）和 TimescaleDB（PG 类型继承），TDengine 的数值类型面向 IoT 传感器数据（浮点数为主）。 |
| [字符串类型](../types/string/tdengine.md) | **NCHAR（Unicode）/BINARY/VARCHAR（3.0+）**——NCHAR 存储 Unicode 字符串（4 字节/字符），BINARY 存储原始字节。VARCHAR 在 3.0 引入。对比 PostgreSQL 的 TEXT（无长度限制）和 TimescaleDB（PG 字符串继承），TDengine 的字符串类型面向 IoT 场景设计。 |
