# TimescaleDB

**分类**: 时序数据库（PostgreSQL 扩展）
**文件数**: 51 个 SQL 文件
**总行数**: 4382 行

## 概述与定位

TimescaleDB 是 Timescale 公司基于 PostgreSQL 扩展机制开发的时序数据库，以 PostgreSQL 扩展（Extension）的形式安装，完整保留 PostgreSQL 的全部 SQL 能力。它定位于 IoT 监控、DevOps 可观测性、金融行情等需要高效时序数据处理的场景。与专有时序数据库不同，TimescaleDB 的核心优势是"时序能力 + 完整 SQL"——用户不需要学习新的查询语言或放弃关系型数据库的事务和 JOIN 能力。

## 历史与演进

- **2017 年**：Timescale 公司成立并开源 TimescaleDB，作为 PG 扩展发布。
- **2018 年**：引入 Continuous Aggregates（持续聚合物化视图）。
- **2019 年**：支持多节点分布式部署（Multi-Node，后续已弃用）。
- **2020 年**：引入原生列式压缩（Compression），大幅降低存储成本。
- **2021 年**：推出 Timescale Cloud 托管服务和数据分层（Data Tiering）。
- **2022 年**：Continuous Aggregates 支持实时刷新和层级嵌套。
- **2023-2025 年**：引入 Hypercore 列存引擎、自动压缩策略优化和向量搜索能力。

## 核心设计思路

TimescaleDB 的核心抽象是 **hypertable**——一个对用户透明的自动分区表。创建 hypertable 后，数据按时间维度自动分成多个 chunk（时间分片），每个 chunk 是一个独立的 PG 表。查询时 TimescaleDB 利用 chunk 排除（类似分区裁剪）只扫描相关时间段。这种设计使插入性能不会随数据量增长而退化。由于完全基于 PG 扩展 API，所有 PG 功能（JOIN、CTE、窗口函数、事务、扩展生态）均可直接使用。

## 独特特色

- **hypertable**：`SELECT create_hypertable('metrics', 'time')` 将普通表转为自动按时间分区的超级表。
- **time_bucket()**：`time_bucket('5 minutes', time)` 灵活的时间桶聚合函数，替代 `date_trunc` 支持任意间隔。
- **Continuous Aggregates**：`CREATE MATERIALIZED VIEW ... WITH (timescaledb.continuous)` 自动增量刷新的物化视图。
- **原生压缩**：`ALTER TABLE metrics SET (timescaledb.compress)` 列式压缩旧数据，压缩率可达 90%+。
- **数据保留策略**：`SELECT add_retention_policy('metrics', INTERVAL '90 days')` 自动删除过期数据。
- **数据分层**：将冷数据自动迁移到低成本对象存储。
- **完整 PG 兼容**：JOIN、子查询、CTE、窗口函数、PostGIS 等全部可用。

## 已知不足

- 仅支持时间维度作为主分区维度，非时序场景收益有限。
- 压缩后的 chunk 不支持直接 UPDATE/DELETE（需先解压）。
- 多节点分布式方案已弃用，水平扩展依赖 Timescale Cloud 的方案。
- Continuous Aggregates 在高基数分组场景下刷新开销较大。
- 与 PG 大版本升级的兼容性需要等待扩展适配。
- 社区版（Apache 2.0）和企业版（Timescale License）功能有差异。

## 对引擎开发者的参考价值

TimescaleDB 展示了如何在不修改数据库内核的情况下通过扩展机制实现专有场景优化——这是 PostgreSQL 扩展生态的极致体现。hypertable 的自动分区和 chunk 管理设计、Continuous Aggregates 的增量物化视图实现、以及列式压缩在 PG 行存引擎上的叠加方式对扩展开发者有直接参考价值。time_bucket 函数的设计也启发了其他数据库的时间聚合函数实现。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/timescaledb.md) | **PG 扩展——Hypertable 自动按时间分片**。`SELECT create_hypertable("metrics", "time")` 将普通 PG 表转为自动分区的超级表，数据按时间分成 Chunk（每个 Chunk 是独立 PG 表）。插入性能不随数据量增长而退化。对比 PostgreSQL（手动声明式分区）和 InfluxDB（专有时序数据库），TimescaleDB 在保持完整 SQL 的同时提供时序优化。 |
| [改表](../ddl/alter-table/timescaledb.md) | **PG 兼容 ALTER + Hypertable 透明管理**——ALTER TABLE 对 Hypertable 透明执行，变更自动应用到所有 Chunk。对比 PostgreSQL（ALTER 标准）和 TDengine（ALTER 超级表自动同步子表），TimescaleDB 继承 PG 的 DDL 事务性。 |
| [索引](../ddl/indexes/timescaledb.md) | **B-tree/GIN/GiST（PG 兼容）+ 时间列自动索引**——Hypertable 的时间列自动创建 B-tree 索引。Chunk 级别的索引使查询只扫描相关时间段。对比 PostgreSQL（需手动创建索引）和 InfluxDB（时间列自动索引），TimescaleDB 在时间维度上自动优化。 |
| [约束](../ddl/constraints/timescaledb.md) | **PK/FK/CHECK（PG 兼容）——唯一约束需包含时间列**。Hypertable 的唯一索引/主键必须包含分区列（时间列），这是分区表约束的通用限制。对比 PostgreSQL（分区表约束同样需包含分区键）和 TDengine（TIMESTAMP 主键必须），TimescaleDB 的约束限制源于 PG 分区表机制。 |
| [视图](../ddl/views/timescaledb.md) | **Continuous Aggregate（连续聚合）——独有增量物化视图**。`CREATE MATERIALIZED VIEW ... WITH (timescaledb.continuous)` 定义自动增量刷新的时序聚合视图。仅重算新增数据，效率远高于全量刷新。对比 PostgreSQL（REFRESH MATERIALIZED VIEW 全量刷新）和 BigQuery（物化视图自动增量），TimescaleDB 的 Continuous Aggregate 是时序场景下最优雅的预聚合方案。 |
| [序列与自增](../ddl/sequences/timescaledb.md) | **SERIAL/IDENTITY（PG 兼容）**——时序场景通常以 TIMESTAMP 为主键，自增序列使用较少。对比 PostgreSQL（SERIAL/IDENTITY 标准）和 TDengine（TIMESTAMP 必须为主键），TimescaleDB 的序列能力完全继承 PG。 |
| [数据库/Schema/用户](../ddl/users-databases/timescaledb.md) | **PG 兼容权限 + Hypertable 透明集成**——权限管理完全继承 PG 的 GRANT/REVOKE 体系。Hypertable 在权限层面与普通表无差异。对比 PostgreSQL（权限管理完整）和 TDengine（独立用户权限体系），TimescaleDB 完全融入 PG 生态。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/timescaledb.md) | **EXECUTE（PL/pgSQL 兼容）**——完整继承 PG 的动态 SQL 能力。对比 PostgreSQL（EXECUTE 原生）和 TDengine（无动态 SQL），TimescaleDB 的过程化能力完全来自 PG。 |
| [错误处理](../advanced/error-handling/timescaledb.md) | **EXCEPTION WHEN（PL/pgSQL 兼容）**——完整继承 PG 的异常处理。对比 PostgreSQL（EXCEPTION WHEN 原生）和 TDengine（无过程式错误处理），TimescaleDB 的错误处理与 PG 一致。 |
| [执行计划](../advanced/explain/timescaledb.md) | **EXPLAIN ANALYZE（PG 兼容）+ Chunk 裁剪信息**——执行计划中显示 Chunk 排除（Chunk Exclusion）信息，帮助识别时间范围过滤的效果。对比 PostgreSQL 的 EXPLAIN ANALYZE（分区裁剪信息）和 InfluxDB（无标准执行计划），TimescaleDB 的 Chunk 裁剪信息对时序查询优化至关重要。 |
| [锁机制](../advanced/locking/timescaledb.md) | **PG 兼容锁 + Chunk 级别并发**——不同 Chunk 上的写入互不阻塞，时序数据按时间追加写入天然分散到不同 Chunk。对比 PostgreSQL（表级/行级锁）和 TDengine（VNODE 级别并发），TimescaleDB 的 Chunk 级并发是时序写入性能的关键。 |
| [分区](../advanced/partitioning/timescaledb.md) | **Hypertable 自动按时间分 Chunk（核心功能）+ 空间分区可选**——时间维度自动分片是核心特性，可选第二维度（如 device_id）做空间分区。`chunk_time_interval` 控制每个 Chunk 的时间跨度。对比 PostgreSQL（手动声明式分区）和 TDengine（超级表按 Tag 分组），TimescaleDB 的自动分片对用户完全透明。 |
| [权限](../advanced/permissions/timescaledb.md) | **PG 兼容 RBAC**——完全继承 PG 的权限体系。对比 PostgreSQL（RBAC 完整）和 TDengine（简单用户权限），TimescaleDB 的权限管理与 PG 一致。 |
| [存储过程](../advanced/stored-procedures/timescaledb.md) | **PL/pgSQL（PG 兼容）+ Jobs 定时任务（独有）**——`SELECT add_job("my_func", "1 hour")` 注册定时任务，自动执行数据维护（如压缩、聚合刷新、数据保留）。对比 PostgreSQL 的 pg_cron（需额外安装）和 TDengine（无定时任务），TimescaleDB 的 Jobs 是数据生命周期管理的核心能力。 |
| [临时表](../advanced/temp-tables/timescaledb.md) | **TEMPORARY TABLE（PG 兼容）**——完全继承 PG 的临时表能力。对比 PostgreSQL（CREATE TEMP TABLE 标准）和 TDengine（无临时表），TimescaleDB 的临时表与 PG 一致。 |
| [事务](../advanced/transactions/timescaledb.md) | **ACID（PG 兼容）+ DDL 事务性**——完整 ACID 事务和 DDL 可事务回滚。对比 PostgreSQL（ACID+DDL 事务性）和 TDengine（无传统事务），TimescaleDB 保留了 PG 的事务优势，这是它区别于专有时序数据库的核心差异。 |
| [触发器](../advanced/triggers/timescaledb.md) | **PG 兼容触发器 + Chunk 级别执行**——触发器对 Hypertable 透明执行，在每个 Chunk 上自动生效。对比 PostgreSQL（触发器完整）和 TDengine（Stream 流式计算替代），TimescaleDB 完全继承 PG 触发器能力。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/timescaledb.md) | **DELETE（PG 兼容）+ drop_chunks() 按时间范围高效删除（独有）**——`SELECT drop_chunks("metrics", INTERVAL "90 days")` 直接删除整个 Chunk（比逐行 DELETE 快几个数量级）。`add_retention_policy` 可自动定期清理过期数据。对比 PostgreSQL（DROP PARTITION 类似但需手动管理）和 TDengine（KEEP 参数自动过期），TimescaleDB 的 drop_chunks 是时序数据生命周期管理的核心。 |
| [插入](../dml/insert/timescaledb.md) | **INSERT（PG 兼容）+ Hypertable 自动路由到 Chunk**——INSERT 根据时间戳自动路由到正确的 Chunk，对用户完全透明。批量 INSERT 和 COPY 均支持。对比 PostgreSQL（分区表需手动或触发器路由）和 TDengine（INSERT 多行/多表批量语法独特），TimescaleDB 的写入路由完全自动化。 |
| [更新](../dml/update/timescaledb.md) | **UPDATE（PG 兼容）**——标准 UPDATE 语法。注意：压缩后的 Chunk 不支持直接 UPDATE（需先解压）。对比 PostgreSQL（UPDATE 标准）和 TDengine（相同时间戳 INSERT 覆盖），TimescaleDB 的 UPDATE 受压缩状态影响。 |
| [Upsert](../dml/upsert/timescaledb.md) | **ON CONFLICT（PG 兼容）——时序 Upsert 常见场景**。`INSERT ... ON CONFLICT (time, device_id) DO UPDATE` 处理时序数据的迟到更新或重复写入。对比 PostgreSQL（ON CONFLICT 原生）和 TDengine（INSERT 相同时间戳自动覆盖），TimescaleDB 的 Upsert 继承 PG 语法。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/timescaledb.md) | **PG 兼容 + time_bucket 时间桶聚合（独有核心函数）**——`SELECT time_bucket('5 minutes', time), AVG(value) FROM metrics GROUP BY 1` 按任意时间间隔聚合。对比 PostgreSQL 的 date_trunc（仅支持固定间隔如 hour/day）和 BigQuery 的 TIMESTAMP_TRUNC，time_bucket 支持任意间隔（如 5 分钟、15 秒）是时序分析的核心优势。 |
| [条件函数](../functions/conditional/timescaledb.md) | **CASE/COALESCE（PG 兼容）**——完全继承 PG 的条件函数。对比 PostgreSQL（相同函数集）和 TDengine（基础 CASE 支持），TimescaleDB 条件函数与 PG 完全一致。 |
| [日期函数](../functions/date-functions/timescaledb.md) | **PG 兼容 + time_bucket/time_bucket_gapfill（独有）**——time_bucket_gapfill 自动填充缺失的时间桶并支持 locf()（上一个值填充）和 interpolate()（线性插值）。对比 PostgreSQL 的 generate_series+LEFT JOIN（手动填充）和 TDengine 的 FILL（类似功能），TimescaleDB 的 gapfill 是最优雅的时序缺失值处理方案。 |
| [数学函数](../functions/math-functions/timescaledb.md) | **PG 兼容数学函数**——完整数学函数集。对比 PostgreSQL（相同函数集）和 TDengine（基础数学+SPREAD/TWA 时序独有），TimescaleDB 数学函数与 PG 一致。 |
| [字符串函数](../functions/string-functions/timescaledb.md) | **PG 兼容字符串函数**——完整字符串函数集。对比 PostgreSQL（相同函数集）和 TDengine（基础字符串函数），TimescaleDB 字符串函数与 PG 一致。 |
| [类型转换](../functions/type-conversion/timescaledb.md) | **CAST/::（PG 兼容）**——完全继承 PG 的类型转换体系。对比 PostgreSQL（:: 运算符简洁）和 TDengine（CAST 基础），TimescaleDB 类型转换与 PG 一致。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/timescaledb.md) | **WITH + 递归 CTE（PG 兼容）**——完全继承 PG 的 CTE 能力。对比 PostgreSQL（WITH RECURSIVE 标准）和 TDengine（不支持 CTE），TimescaleDB 的 CTE 能力是它优于专有时序数据库的关键差异。 |
| [全文搜索](../query/full-text-search/timescaledb.md) | **tsvector/tsquery（PG 兼容）**——完全继承 PG 全文搜索。时序数据的日志文本可利用全文索引加速搜索。对比 PostgreSQL（tsvector+GIN 最成熟）和 TDengine（无全文搜索），TimescaleDB 的全文搜索是时序+关系混合查询的优势。 |
| [连接查询](../query/joins/timescaledb.md) | **PG 兼容 JOIN + Hypertable JOIN 优化**——Hypertable 与普通表的 JOIN 透明执行，Chunk 排除减少扫描。对比 PostgreSQL（JOIN 标准）和 TDengine（JOIN 支持有限），TimescaleDB 的 JOIN 能力是它优于专有时序数据库的核心差异。 |
| [分页](../query/pagination/timescaledb.md) | **LIMIT/OFFSET（PG 兼容）**——标准分页语法。对比 PostgreSQL（LIMIT/OFFSET 标准）和 TDengine（LIMIT/OFFSET+SLIMIT/SOFFSET），TimescaleDB 的分页与 PG 一致。 |
| [行列转换](../query/pivot-unpivot/timescaledb.md) | **crosstab（PG 兼容 tablefunc）**——通过 tablefunc 扩展实现行列转换。时序数据的宽表/窄表转换在 IoT 场景中常见。对比 PostgreSQL（需安装 tablefunc）和 TDengine（无 PIVOT），TimescaleDB 与 PG 方案一致。 |
| [集合操作](../query/set-operations/timescaledb.md) | **UNION/INTERSECT/EXCEPT（PG 兼容）**——完整集合操作。对比 PostgreSQL（集合操作完整）和 TDengine（仅 UNION/UNION ALL），TimescaleDB 继承 PG 完整集合操作能力。 |
| [子查询](../query/subquery/timescaledb.md) | **关联子查询（PG 兼容）**——完整子查询能力。对比 PostgreSQL（优化器成熟）和 TDengine（子查询支持有限），TimescaleDB 的子查询能力完整。 |
| [窗口函数](../query/window-functions/timescaledb.md) | **完整窗口函数（PG 兼容）+ 时序分析增强**——LAG/LEAD 用于比较前后时间点，SUM/AVG OVER(ORDER BY time) 计算时序累计/移动平均。对比 PostgreSQL（窗口函数完整）和 TDengine（STATE/SESSION/EVENT_WINDOW 独有），TimescaleDB 的窗口函数是标准 SQL 窗口与时序分析的结合。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/timescaledb.md) | **time_bucket_gapfill + locf/interpolate（独有）——原生时序填充**。`SELECT time_bucket_gapfill('1 hour', time), locf(avg(temp)) FROM metrics GROUP BY 1` 自动填充缺失时间桶并用上一个值补充。对比 PostgreSQL 的 generate_series+LEFT JOIN（手动）和 TDengine 的 FILL(PREV)（类似），TimescaleDB 的 gapfill+locf/interpolate 是最优雅的时序填充方案。 |
| [去重](../scenarios/deduplication/timescaledb.md) | **ROW_NUMBER + CTE（PG 兼容）**——标准去重方案。时序场景下常按 (device_id, time) 去重保留最新值。对比 PostgreSQL（DISTINCT ON 更简洁）和 TDengine（UNIQUE 函数独有），TimescaleDB 使用 PG 通用去重方案。 |
| [区间检测](../scenarios/gap-detection/timescaledb.md) | **time_bucket_gapfill 原生间隙检测（独有）**——gapfill 自动识别缺失的时间桶，无需手动生成完整序列对比。对比 PostgreSQL 的 generate_series+LEFT JOIN（手动检测）和 TDengine 的 INTERVAL+FILL（类似），TimescaleDB 的 gapfill 是最自动化的间隙检测方案。 |
| [层级查询](../scenarios/hierarchical-query/timescaledb.md) | **递归 CTE（PG 兼容）**——完全继承 PG 的层级查询能力。时序场景下层级查询较少使用。对比 PostgreSQL（WITH RECURSIVE 标准）和 TDengine（不支持层级查询），TimescaleDB 的递归 CTE 能力来自 PG。 |
| [JSON 展开](../scenarios/json-flatten/timescaledb.md) | **json_each/json_array_elements（PG 兼容）**——JSONB+GIN 可存储和查询 IoT 设备的 JSON 元数据。对比 PostgreSQL（JSONB 最强）和 TDengine（TAG 支持 JSON），TimescaleDB 继承 PG 完整 JSONB 能力。 |
| [迁移速查](../scenarios/migration-cheatsheet/timescaledb.md) | **PG 完全兼容是基础，Hypertable + Continuous Aggregate + 压缩是核心增值**。关键差异：create_hypertable 将普通表转为时序表；time_bucket/gapfill 是时序核心函数；Continuous Aggregate 替代定时刷新的物化视图；压缩后 Chunk 不可直接 UPDATE/DELETE；数据保留策略自动清理过期数据。 |
| [TopN 查询](../scenarios/ranking-top-n/timescaledb.md) | **ROW_NUMBER + LIMIT（PG 兼容）**——标准 TopN 方案。时序场景下常取每个设备的最新 N 条记录。对比 PostgreSQL（DISTINCT ON 更简洁取最新一条）和 BigQuery（QUALIFY），TimescaleDB 使用 PG 通用 TopN 方案。 |
| [累计求和](../scenarios/running-total/timescaledb.md) | **SUM() OVER（PG 兼容）+ 时序累计**——标准窗口累计。时序场景下用于计算设备的累计流量/能耗等指标。对比各主流引擎写法一致。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/timescaledb.md) | **ON CONFLICT（PG 兼容）**——标准 Upsert 实现 SCD。对比 PostgreSQL（ON CONFLICT 原生）和 Oracle（MERGE），TimescaleDB 继承 PG 的 Upsert 能力。 |
| [字符串拆分](../scenarios/string-split-to-rows/timescaledb.md) | **string_to_array + unnest（PG 兼容）**——方案与 PostgreSQL 一致。对比 PostgreSQL（相同方案）和 TDengine（不支持字符串拆分），TimescaleDB 继承 PG 的拆分能力。 |
| [窗口分析](../scenarios/window-analytics/timescaledb.md) | **PG 兼容窗口函数 + time_bucket 时间桶分析（独有优势）**——time_bucket 与窗口函数结合实现滑动时间窗口分析（如每 5 分钟的移动平均）。对比 PostgreSQL（date_trunc 仅固定间隔）和 TDengine（SLIDING 滑动窗口独有），TimescaleDB 的 time_bucket+窗口函数组合兼具灵活性和标准 SQL 语法。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/timescaledb.md) | **ARRAY / 复合类型（PG 兼容）**——完全继承 PG 的类型系统。对比 PostgreSQL（ARRAY 原生）和 TDengine（无 ARRAY），TimescaleDB 可用 ARRAY 存储多传感器值。 |
| [日期时间](../types/datetime/timescaledb.md) | **TIMESTAMP/TIMESTAMPTZ（PG 兼容）——时序核心类型**。TIMESTAMPTZ（带时区）是 Hypertable 分区列的推荐类型。对比 PostgreSQL（TIMESTAMPTZ 推荐）和 TDengine（TIMESTAMP 纳秒精度），TimescaleDB 的时间类型与 PG 一致，推荐使用 TIMESTAMPTZ 确保时区安全。 |
| [JSON](../types/json/timescaledb.md) | **JSON/JSONB + GIN 索引（PG 兼容）**——JSONB 可存储 IoT 设备的动态元数据和半结构化传感器数据。对比 PostgreSQL（JSONB+GIN 最强）和 TDengine（TAG 支持 JSON），TimescaleDB 的 JSONB 能力完全继承 PG。 |
| [数值类型](../types/numeric/timescaledb.md) | **INT/BIGINT/NUMERIC/FLOAT（PG 兼容）**——标准数值类型。时序场景下 FLOAT/DOUBLE PRECISION 常用于传感器数据。对比 PostgreSQL（相同类型体系）和 TDengine（无 DECIMAL），TimescaleDB 数值类型与 PG 一致。 |
| [字符串类型](../types/string/timescaledb.md) | **TEXT/VARCHAR（PG 兼容）**——TEXT 推荐，无长度限制。对比 PostgreSQL（TEXT 推荐）和 TDengine（NCHAR/BINARY/VARCHAR），TimescaleDB 字符串类型与 PG 一致。 |
