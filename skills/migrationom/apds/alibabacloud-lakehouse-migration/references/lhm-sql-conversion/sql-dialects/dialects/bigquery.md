# BigQuery

**分类**: Google 云数仓
**文件数**: 51 个 SQL 文件
**总行数**: 6290 行

> **关键人物**：[Sergey Melnik](../docs/people/bigquery-dremel.md)（Dremel 论文第一作者）

## 概述与定位

BigQuery 是 Google Cloud 提供的无服务器（Serverless）云数据仓库。用户无需管理服务器、索引或连接池，只需编写 SQL 即可分析 PB 级数据。其核心计费模型是**按扫描数据量付费**（on-demand）或按预留 Slot 付费（flat-rate），这一商业模式直接影响了 SQL 层的设计取舍——没有索引、没有手动调优旋钮，一切由平台透明管理。

BigQuery 的定位是"零运维分析"：将传统 DBA 的工作（分区规划、统计信息收集、查询计划调优）全部内化到引擎中，用户只关注 SQL 本身。这使得它特别适合数据分析师和数据科学家，但也意味着对习惯了 RDBMS 精细控制的工程师来说，可操作空间有限。

## 历史与演进

| 时间 | 里程碑 |
|------|--------|
| 2010 | Google 发表 Dremel 论文，描述列式存储+树状调度的大规模查询架构 |
| 2011 | BigQuery 作为 Google Cloud 服务公开发布，初期仅支持类 SQL 方言（Legacy SQL） |
| 2016 | 引入**标准 SQL**（Standard SQL），语法向 ANSI SQL 靠拢，Legacy SQL 逐步弃用 |
| 2019 | BI Engine 发布，提供内存加速层；支持 BigQuery ML（在 SQL 中训练模型） |
| 2021 | BigQuery Omni 发布，支持在 AWS/Azure 上查询数据（多云架构） |
| 2023 | 持续增强：支持 SEARCH INDEX 全文索引、Apache Iceberg 外部表、向量搜索 |

## 核心设计思路

- **无服务器哲学**：没有实例、没有连接池、没有 VACUUM。用户提交 SQL，平台分配 Slot（计算单元）执行查询，完成后释放。这决定了 BigQuery 没有索引——因为索引是有状态的服务器端优化，与无服务器模型冲突。
- **列式存储 Capacitor**：底层存储格式 Capacitor 按列组织数据，支持嵌套结构（STRUCT/ARRAY），这是 Dremel 论文的核心思想。列式存储使得 `SELECT a, b FROM t` 只扫描两列而非整行，直接降低按扫描量计费的成本。
- **Slot 执行模型**：查询被拆分为多个 Stage，每个 Stage 由多个 Slot 并行执行。Slot 是 CPU + 内存 + I/O 的封装单元。用户无法控制 Slot 分配策略，但可以通过预留（Reservation）保证并发。
- **STRUCT/ARRAY 一等公民**：BigQuery 原生支持嵌套数据结构，不需要 JSON 序列化。`STRUCT<name STRING, age INT64>` 是正式的列类型，查询时可以直接 `t.address.city` 点号访问。这一设计源于 Google 内部 Protocol Buffers 的数据模型传统。

## 独特特色

- **按扫描量计费**：on-demand 模式下每 TB 扫描约 $5-$6.25，这使得 `SELECT *` 成为最昂贵的反模式。用户必须养成只选必要列的习惯——计费模型直接塑造了 SQL 编写风格。
- **INT64/STRING 类型命名**：不使用 INTEGER/VARCHAR，而是 INT64、FLOAT64、STRING、BOOL，命名风格来自 Google 内部类型系统，与标准 SQL 的 INTEGER/DECIMAL 不同。
- **SAFE_ 前缀函数**：`SAFE_DIVIDE(a, b)` 在除零时返回 NULL 而非报错；几乎所有函数都有 SAFE_ 版本。这是 BigQuery 独有的安全函数设计，避免了分析查询因脏数据中断。
- **分区 + 聚集代替索引**：通过 `PARTITION BY date_col` 和 `CLUSTER BY col1, col2` 实现数据裁剪，这是 BigQuery 唯一的物理优化手段。分区裁剪减少扫描量（省钱），聚集排序加速过滤（省时间）。
- **约束 NOT ENFORCED**：BigQuery 支持 PRIMARY KEY / FOREIGN KEY 声明，但标注 `NOT ENFORCED`——仅作为元数据提示供优化器使用，不实际校验数据。这是无服务器架构下的妥协：强制约束需要事务性写入，与高吞吐 INSERT 冲突。
- **TABLE_SUFFIX 通配符表**：`SELECT * FROM project.dataset.events_*` 配合 `_TABLE_SUFFIX` 可以跨多表查询，这是 BigQuery 处理按日分表（日期后缀）的独特方式。
- **GENERATE_UUID()**：内置 UUID 生成函数，在无自增列的环境下提供唯一标识符。
- **BI Engine**：内存加速层，对高频查询自动缓存列式数据到内存，使 BI 仪表盘查询从秒级降到毫秒级。使用向量化处理和字典/RLE 编码。
- **BQML（BigQuery ML）**：在 SQL 中训练和推理 ML 模型——`CREATE MODEL`, `ML.PREDICT`, `ML.EVALUATE`。支持线性回归、决策树、深度学习、时间序列预测。不需要导出数据到外部 ML 平台。
- **向量搜索**：`VECTOR_SEARCH()` 函数 + 向量索引（TreeAH，基于 Google ScaNN 算法）。支持 `GENERATED ALWAYS AS AI.EMBED()` 自动生成 embedding 列。对 AI 语义搜索场景原生支持。
- **AI SQL 函数（2025）**：`AI.GENERATE`（文本/图片/视频生成）、`AI.IF`（语义条件判断）、`AI.CLASSIFY`（分类）、`AI.SCORE`（评分）——将 LLM 能力直接集成到 SQL 查询中。
- **SEARCH INDEX（2023+）**：全文搜索索引 + `SEARCH()` 函数，基于 Log-structured 存储，无需外部搜索引擎即可实现文本检索。

## 已知的设计不足与历史包袱

- **DML 并发限制**：同一表的 UPDATE/DELETE/MERGE 操作受严格的并发配额限制（每表每天上千次级别），不适合高频小事务写入。BigQuery 本质是分析引擎，不是 OLTP 数据库。
- **无自增列**：没有 AUTO_INCREMENT 或 SERIAL，需要用 `GENERATE_UUID()` 或 `ROW_NUMBER()` 模拟。
- **无索引**：唯一的物理优化是分区和聚集，无法为特定查询模式创建 B-Tree 或 Hash 索引。
- **约束不执行**：PK/FK 仅作元数据提示，不保证数据完整性，应用层必须自行保证。
- **Scripting 有限**：虽然支持 BEGIN...END 脚本块和存储过程，但功能远不及 PL/pgSQL 或 T-SQL，缺乏游标、包（Package）等高级特性。
- **无触发器**：无法在数据变更时自动执行逻辑，需要借助外部服务（Cloud Functions、Pub/Sub）实现类似功能。
- **STRUCT 嵌套字段不可直接 UPDATE**：不能 `UPDATE t SET t.address.city = 'X'`，必须整体替换整个 STRUCT 值。

## 兼容生态

BigQuery 标准 SQL 语法自成一体，与 PostgreSQL/MySQL 不兼容。但其 INFORMATION_SCHEMA 设计借鉴了 ANSI 标准，支持 ODBC/JDBC 连接。生态集成主要通过 Google Cloud 平台（Dataflow、Dataproc、Looker、Vertex AI）。

## 对引擎开发者的参考价值

- **Dremel 列式执行**：树状调度架构（Root Server → Intermediate → Leaf）是分布式查询引擎的经典参考，论文影响了 Apache Drill、Impala 等多个开源项目。
- **Capacitor 存储格式**：支持嵌套结构的列式存储设计，证明了不必将嵌套数据扁平化即可高效查询，这一思路后来被 Parquet/ORC 的嵌套支持所借鉴。
- **Slot-based 计费模型**：将计算资源量化为 Slot 并按使用付费，是云数仓商业模式的重要创新。这一模型要求引擎内部能精确度量每个查询的资源消耗。

---

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/bigquery.md) | **无索引是核心设计选择**——用 PARTITION(日期/整数)+CLUSTER(最多4列) 替代。约束 NOT ENFORCED 仅作优化器提示。STRUCT/ARRAY 一等公民鼓励反范式嵌套设计。对比 Snowflake 的微分区自动管理，BigQuery 需要用户显式选择分区列。 |
| [改表](../ddl/alter-table/bigquery.md) | ALTER 能力有限：不支持 MODIFY COLUMN TYPE（需重建表），不能改分区/聚集策略。对比 Snowflake（同样不支持）和 ClickHouse（异步 mutation），BigQuery 在 Schema 演进上最保守。变通：CTAS 重建表。 |
| [索引](../ddl/indexes/bigquery.md) | **唯一没有传统索引的主流数仓之一**。2023+ 的 SEARCH INDEX 是全文搜索索引（非 B-tree），基于 Log-structured 存储。分区裁剪 + 聚集跳过 = BigQuery 的"索引"。对比 ClickHouse 的稀疏索引和 Snowflake 的微分区 pruning。 |
| [约束](../ddl/constraints/bigquery.md) | PK/FK/UNIQUE 都是 NOT ENFORCED——写入时不检查！仅用于优化器消除冗余 JOIN。这是 Serverless 数仓的普遍选择（Snowflake 同理）。对比 PostgreSQL/MySQL 强制执行约束的 OLTP 模型。 |
| [视图](../ddl/views/bigquery.md) | 物化视图是亮点：**自动增量刷新 + 智能查询重写**（查询普通表时自动使用物化视图加速）。Authorized View 实现跨 Dataset 安全数据共享。对比 PG 的 REFRESH MATERIALIZED VIEW（手动）和 Oracle 的 Query Rewrite（功能最强）。 |
| [序列与自增](../ddl/sequences/bigquery.md) | 无自增列——Serverless 架构无法维护全局递增序列。推荐 GENERATE_UUID()。对比 Snowflake（AUTOINCREMENT 不保证连续）和 Spanner（bit-reversed sequence 避免热点）。 |
| [数据库/Schema/用户](../ddl/users-databases/bigquery.md) | **Project.Dataset.Table 三级命名**，Dataset = 其他引擎的 Schema/Database。权限完全基于 GCP IAM（无 SQL GRANT/REVOKE），Row/Column Access Policy 实现细粒度控制。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/bigquery.md) | EXECUTE IMMEDIATE(2019+) 支持 Scripting 模式——BEGIN...END 块内可以用变量、IF/WHILE、异常处理。对比 Snowflake（JS/SQL/Python 存储过程）功能相当。 |
| [错误处理](../advanced/error-handling/bigquery.md) | BEGIN...EXCEPTION WHEN ERROR 脚本级错误捕获。SAFE_ 前缀函数是 BigQuery 独有的行级错误处理设计（SAFE_CAST 返回 NULL 而非报错）。对比 SQL Server TRY_CAST、Snowflake TRY_TO_*。 |
| [执行计划](../advanced/explain/bigquery.md) | **无传统 EXPLAIN 语句**——通过 Console 的 Execution Details 面板查看。显示 Slot 消耗、Shuffle 字节数、阶段耗时。--dry_run 预估扫描量和费用。对比传统引擎的 EXPLAIN ANALYZE。 |
| [锁机制](../advanced/locking/bigquery.md) | **无用户可见锁**。DML 并发限制（同表同时约 5 个 DML）是通过配额而非锁实现的。每次 DML 创建表的新快照（MVCC）。对比 PostgreSQL 的行级锁和 Snowflake 的乐观并发。 |
| [分区](../advanced/partitioning/bigquery.md) | **分区是省钱的核心**——按扫描量计费，分区裁剪直接减少账单。支持日期/时间戳/整数范围三种分区。require_partition_filter 选项防止意外全表扫描。<1GB 的小表不建议分区。 |
| [权限](../advanced/permissions/bigquery.md) | 完全基于 GCP IAM，无 SQL GRANT/REVOKE。Row Access Policy（行级安全）和 Column-level Security（列级安全）通过 policy tags 实现。对比 PG 的 RLS 和 Oracle 的 VPD，BigQuery 的方案更声明式。 |
| [存储过程](../advanced/stored-procedures/bigquery.md) | CREATE PROCEDURE 支持 SQL 和 JavaScript(2023+)。功能弱于 PL/pgSQL/PL/SQL——无游标、无 BULK COLLECT、无包。Remote Functions 可调用 Cloud Functions 扩展能力。 |
| [临时表](../advanced/temp-tables/bigquery.md) | CREATE TEMP TABLE 会话级，通过 _SESSION.table_name 引用。多语句事务内的临时表在事务结束后销毁。对比 SQL Server 的 #temp 和 Oracle 的 GTT。 |
| [事务](../advanced/transactions/bigquery.md) | 多语句事务(2020+) 支持 BEGIN/COMMIT/ROLLBACK，但**不是 OLTP 事务**——有 DML 并发限制，每次 DML 创建快照，适合 ETL 管线而非高并发写入。对比 Snowflake（类似限制）和 RDBMS（高并发 ACID）。 |
| [触发器](../advanced/triggers/bigquery.md) | 不支持。替代方案：Pub/Sub + Cloud Functions（事件驱动），Scheduled Queries（定时），BigQuery Data Transfer（ETL）。对比 ClickHouse 的物化视图触发器和 Snowflake 的 Streams+Tasks。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/bigquery.md) | DELETE 必须带 WHERE（无裸 DELETE FROM t）。分区级 DELETE 高效（整分区标记删除），行级 DELETE 重写整个分区。DML 配额限制写入频率。对比 ClickHouse 的异步 mutation。 |
| [插入](../dml/insert/bigquery.md) | **批量加载（LOAD JOB）免费**，DML INSERT 按扫描量计费。Storage Write API 替代旧版 insertAll（exactly-once 语义）。流式数据进入 streaming buffer 后立即可查但不能 UPDATE/DELETE。 |
| [更新](../dml/update/bigquery.md) | UPDATE 必须带 WHERE。**STRUCT 嵌套字段不能直接 UPDATE**（需重构整个 STRUCT）。每次 UPDATE 内部重写受影响的分区。对比 Snowflake（同样重写微分区）和 RDBMS（行级原地更新）。 |
| [Upsert](../dml/upsert/bigquery.md) | MERGE INTO 是唯一的 UPSERT 方案（不支持 ON CONFLICT/ON DUPLICATE KEY）。MERGE 的 WHEN NOT MATCHED BY SOURCE 可实现 SCD。DML 配额限制：同一表避免高频 MERGE。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/bigquery.md) | APPROX_COUNT_DISTINCT（HyperLogLog，默认行为！精确版需要 COUNT(DISTINCT)）、APPROX_TOP_COUNT、COUNTIF（条件计数，替代 FILTER 子句）。STRING_AGG 标准，ARRAY_AGG 返回原生 ARRAY。对比 PG 的 FILTER 子句和 ClickHouse 的 -If 组合函数。 |
| [条件函数](../functions/conditional/bigquery.md) | **SAFE_ 前缀是 BigQuery 最优雅的设计之一**——几乎每个函数都有 SAFE_ 版本（SAFE_CAST、SAFE_DIVIDE、SAFE.SUBSTR），转换失败返回 NULL 而非报错。对比 SQL Server TRY_CAST（单独函数名）和 ClickHouse toTypeOrNull（后缀约定）。 |
| [日期函数](../functions/date-functions/bigquery.md) | DATE/DATETIME/TIMESTAMP/TIME 四种类型严格区分。DATETIME 无时区，TIMESTAMP 有时区（UTC 存储）。DATE_TRUNC/DATE_DIFF/DATE_ADD 标准。GENERATE_DATE_ARRAY 生成日期序列（替代 PG 的 generate_series）。 |
| [数学函数](../functions/math-functions/bigquery.md) | SAFE_DIVIDE(a,b) 除零返回 NULL（独有语法），IEEE_DIVIDE 返回 Infinity/NaN（IEEE 754 标准）。GREATEST/LEAST 内置。对比 PG 的 除零报错 和 Oracle 的 除零报错。 |
| [字符串函数](../functions/string-functions/bigquery.md) | SPLIT(str, sep) 返回 ARRAY（可直接 UNNEST）。REGEXP_EXTRACT/REPLACE 基于 re2 引擎（线性时间复杂度，不支持回溯）。CONTAINS_SUBSTR 大小写不敏感搜索。FORMAT 格式化输出。 |
| [类型转换](../functions/type-conversion/bigquery.md) | SAFE_CAST 是核心——ETL 中数据质量不可控时，SAFE_CAST 避免整个查询因一行脏数据而失败。PARSE_DATE/PARSE_TIMESTAMP 解析字符串为日期。对比 PG（无内置 TRY_CAST）和 MySQL（宽松隐式转换）。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/bigquery.md) | 标准 WITH 语法 + 递归 CTE。BigQuery 对 CTE 的物化/内联由优化器自动决定，无 MATERIALIZED hint。递归 CTE 有迭代次数限制。 |
| [全文搜索](../query/full-text-search/bigquery.md) | SEARCH INDEX(2023+) + SEARCH() 函数实现全文搜索。基于 Log-structured 存储，与 BigQuery 列式引擎集成。对比 PG 的 tsvector+GIN（最成熟）和 ES（专用引擎）。 |
| [连接查询](../query/joins/bigquery.md) | **CROSS JOIN UNNEST(array_col) 是 BigQuery 的标志性语法**——将 ARRAY 列展开为行。支持所有标准 JOIN 类型。无 LATERAL 关键字（用 UNNEST 替代）。Broadcast/Shuffle JOIN 由优化器自动选择。 |
| [分页](../query/pagination/bigquery.md) | LIMIT/OFFSET 标准。**没有分页优化的必要**——BigQuery 按扫描量计费，无论 OFFSET 多大，扫描量不变。大结果集建议 EXPORT 到 GCS 而非分页。 |
| [行列转换](../query/pivot-unpivot/bigquery.md) | **PIVOT/UNPIVOT 原生支持**（2021+）。PIVOT 需要枚举值（不支持动态 PIVOT）。对比 Snowflake 的 PIVOT ANY（动态值检测）和 DuckDB 的自动 PIVOT。 |
| [集合操作](../query/set-operations/bigquery.md) | UNION ALL/DISTINCT、INTERSECT ALL/DISTINCT、EXCEPT ALL/DISTINCT 完整。UNION DISTINCT 是默认（与 SQL 标准一致）。对比 ClickHouse（UNION 默认 ALL，与标准相反）。 |
| [子查询](../query/subquery/bigquery.md) | 关联子查询、IN/EXISTS/NOT EXISTS、标量子查询均支持。优化器善于将子查询转为 JOIN。对比 MySQL 5.x 的子查询性能噩梦（已在 8.0 修复）。 |
| [窗口函数](../query/window-functions/bigquery.md) | **QUALIFY 子句是最大亮点**——`SELECT * FROM t QUALIFY ROW_NUMBER() OVER(...) = 1` 无需子查询包装。完整 ROWS/RANGE 帧支持。WINDOW 命名子句支持。对比 MySQL/PG/Oracle（均不支持 QUALIFY）。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/bigquery.md) | `UNNEST(GENERATE_DATE_ARRAY('2024-01-01','2024-12-31'))` 生成日期序列——比 PG 的 generate_series 更直观。LEFT JOIN 填充缺失日期。 |
| [去重](../scenarios/deduplication/bigquery.md) | `QUALIFY ROW_NUMBER() OVER(PARTITION BY id ORDER BY ts DESC) = 1` ——BigQuery 中最简的去重写法，其他引擎需要子查询包装。 |
| [区间检测](../scenarios/gap-detection/bigquery.md) | LAG/LEAD 窗口函数 + GENERATE_DATE_ARRAY 检测连续区间和缺失值。 |
| [层级查询](../scenarios/hierarchical-query/bigquery.md) | 递归 CTE 支持，有迭代深度限制。无 CONNECT BY（Oracle 独有）。 |
| [JSON 展开](../scenarios/json-flatten/bigquery.md) | JSON_QUERY_ARRAY + UNNEST 展开 JSON 数组。对比 PG 的 jsonb_array_elements 和 Snowflake 的 FLATTEN。 |
| [迁移速查](../scenarios/migration-cheatsheet/bigquery.md) | 关键差异：INT64 非 INT、STRING 非 VARCHAR、无索引、DML 配额、STRUCT 嵌套设计范式不同。详见 [BigQuery 迁移指南](../docs/bigquery-migration-guide.md)。 |
| [TopN](../scenarios/ranking-top-n/bigquery.md) | QUALIFY 让 TopN 成为单行表达式——`QUALIFY ROW_NUMBER() OVER(PARTITION BY g ORDER BY v DESC) <= 3`。 |
| [累计求和](../scenarios/running-total/bigquery.md) | SUM() OVER(ORDER BY ...) 标准。大数据量下 Slot 自动扩展，无需人工优化。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/bigquery.md) | MERGE INTO 实现 SCD Type 1/2。Time Travel（7天快照）可用于审计和回溯。 |
| [字符串拆分](../scenarios/string-split-to-rows/bigquery.md) | `SELECT val FROM UNNEST(SPLIT('a,b,c', ',')) AS val` ——SPLIT 返回 ARRAY + UNNEST 展开，一行搞定。 |
| [窗口分析](../scenarios/window-analytics/bigquery.md) | 完整窗口函数 + QUALIFY 过滤 + WINDOW 命名子句。移动平均、同环比、占比计算示例完整。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/bigquery.md) | **STRUCT/ARRAY 是 BigQuery 的核心设计**——来自 Dremel 对嵌套数据的原生支持。鼓励将关联数据嵌套在 STRUCT 中而非 JOIN（反范式但查询高效）。ARRAY 不能嵌套 ARRAY，但 ARRAY<STRUCT<ARRAY<T>>> 可以。 |
| [日期时间](../types/datetime/bigquery.md) | **四种时间类型严格区分**：DATE(纯日期)、TIME(纯时间)、DATETIME(日期+时间，无时区)、TIMESTAMP(UTC 时间戳，带时区)。DATETIME 对应 MySQL 的 DATETIME，TIMESTAMP 对应 PG 的 TIMESTAMPTZ。 |
| [JSON](../types/json/bigquery.md) | JSON 类型(2022+) 存储半结构化数据。路径访问用 JSON_VALUE/JSON_QUERY（SQL 标准函数），也支持点表示法 `json_col.key`。对比 PG JSONB（GIN 索引更强）和 Snowflake VARIANT（更灵活）。 |
| [数值类型](../types/numeric/bigquery.md) | **非标准类型命名但语义清晰**：INT64(=BIGINT)、FLOAT64(=DOUBLE)、NUMERIC(38,9 固定精度)、BIGNUMERIC(76,38 超高精度)。只有一种整数类型——避免了 MySQL 的 TINYINT/SMALLINT/MEDIUMINT/INT/BIGINT 选择困难。 |
| [字符串类型](../types/string/bigquery.md) | STRING 无长度限制（最大 10MB/值），BYTES 存储二进制。无 VARCHAR(n)/CHAR(n)/TEXT 区分——极简设计。REGEXP 函数基于 re2 引擎（保证线性时间，不会正则爆炸）。 |
