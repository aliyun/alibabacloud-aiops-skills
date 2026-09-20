# Databricks SQL

**分类**: Lakehouse 平台（基于 Spark）
**文件数**: 51 个 SQL 文件
**总行数**: 5095 行

## 概述与定位

Databricks SQL 是 Databricks Lakehouse 平台的 SQL 分析层，构建在 Apache Spark 之上，以 Delta Lake 开放表格式为存储基础。它提出了"Lakehouse"范式——在数据湖的低成本开放存储之上叠加数据仓库的事务性和治理能力，消除传统"数据湖 + 数据仓库"双层架构的复杂性。Databricks SQL 兼具大数据规模的弹性计算和交互式数仓的低延迟查询能力。

## 历史与演进

- **2013 年**：Databricks 由 Apache Spark 创始团队成立，最初以 Spark 作为统一大数据分析引擎。
- **2017 年**：Delta Lake 项目启动，在 Parquet 之上增加 ACID 事务、Schema 演进和时间旅行能力。
- **2020 年**：Databricks SQL（原名 SQL Analytics）发布，提供专门的 SQL 计算端点和 BI 工具集成。
- **2021 年**：Unity Catalog 发布，提供跨工作区的统一数据治理、细粒度权限和数据血缘追踪。
- **2022 年**：Photon 引擎（C++ 向量化执行引擎）成为 Databricks SQL 的默认加速器。
- **2023 年**：引入 Liquid Clustering（替代传统分区和 ZORDER）、Predictive I/O 优化。
- **2024-2025 年**：增强 Serverless 计算、AI Functions（LLM 内置 SQL 函数）、UniForm（Delta/Iceberg/Hudi 统一兼容）。

## 核心设计思路

1. **开放格式底座**：所有数据以 Delta Lake 格式（Parquet + 事务日志）存储在客户自有的对象存储中（S3/ADLS/GCS），无供应商锁定。
2. **计算存储分离**：SQL Warehouse 按需启停，数据持久化在对象存储，弹性扩缩容无数据搬运。
3. **ACID on 数据湖**：Delta Lake 提供表级 ACID 事务、MERGE/UPDATE/DELETE 支持、Schema Evolution 和 Time Travel。
4. **统一治理**：Unity Catalog 提供从表、列到行级别的权限控制，以及自动化的数据血缘追踪。

## 独特特色

| 特性 | 说明 |
|---|---|
| **Delta Lake ACID** | 在 Parquet 之上通过事务日志实现 ACID 事务，支持并发写入冲突检测、乐观并发控制。 |
| **Unity Catalog** | 跨工作区的三级命名空间（Catalog.Schema.Table）、列级权限、标签分类和自动血缘。 |
| **Liquid Clustering** | 替代传统静态分区的自适应聚类策略，数据写入时自动优化布局，无需 ZORDER 手动维护。 |
| **Photon 引擎** | C++ 编写的向量化执行引擎，替代 Spark JVM 执行，扫描和聚合性能提升数倍。 |
| **Time Travel** | `SELECT * FROM t VERSION AS OF 5` 或 `TIMESTAMP AS OF '2024-01-01'` 查询历史版本数据。 |
| **MERGE INTO** | 完整的 CDC（变更数据捕获）语法，支持 WHEN MATCHED / WHEN NOT MATCHED / WHEN NOT MATCHED BY SOURCE。 |
| **AI Functions** | `ai_generate_text()`、`ai_classify()` 等 SQL 函数直接在查询中调用大语言模型。 |

## 已知不足

- **冷启动延迟**：SQL Warehouse 从暂停状态恢复需要数十秒到数分钟，不适合极低延迟的在线查询场景。
- **小文件问题**：高频小批量写入会产生大量小 Parquet 文件，需定期 OPTIMIZE 合并（虽有 Auto Optimize，但仍需关注）。
- **存储过程有限**：Databricks SQL 的过程化编程能力依赖 Notebooks/Python UDF，纯 SQL 存储过程支持不如传统数仓。
- **成本控制复杂**：DBU（Databricks Unit）定价模型加上底层云存储/网络费用，总成本估算对用户不够透明。
- **索引能力弱**：无传统 B-tree 索引，依赖 Liquid Clustering、Bloom Filter 和文件级统计信息进行查询加速。

## 对引擎开发者的参考价值

- **Delta Lake 事务日志设计**：用 JSON 事务日志（+ Checkpoint）实现在不可变文件之上的 ACID 语义，对数据湖引擎的事务实现有核心参考。
- **Photon 向量化引擎**：从 JVM 切换到 C++ 向量化执行的实践，展示了在保持上层 SQL 兼容的前提下替换执行层的可行路径。
- **Liquid Clustering 自适应布局**：运行时根据数据分布自动调整物理布局的策略，对列存引擎的自适应分区设计有启发。
- **Unity Catalog 治理模型**：跨工作区的统一元数据 + 细粒度权限 + 自动血缘的设计，对多租户引擎的 Catalog 层设计有参考价值。
- **开放格式互操作（UniForm）**：使同一份数据同时对 Delta/Iceberg/Hudi 客户端可读的元数据转换层设计，对存储格式兼容层有借鉴意义。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/databricks.md) | **Delta Lake 是默认存储格式——Parquet + 事务日志实现 ACID**。Unity Catalog 治理三级命名空间（Catalog.Schema.Table）。CTAS（CREATE TABLE AS SELECT）是数据转换的核心模式。对比 BigQuery 的无索引设计和 Snowflake 的微分区自动管理，Databricks 需用户理解 Delta Lake 物理层。 |
| [改表](../ddl/alter-table/databricks.md) | **Delta Lake Schema Evolution 自动处理新增列**——`mergeSchema` 选项在写入时自动合并 Schema 差异，无需手动 ALTER。ADD/CHANGE COLUMN 标准支持。对比 BigQuery 不支持 MODIFY COLUMN TYPE（需重建表）和 PG 的 DDL 事务性可回滚，Databricks 的 Schema Evolution 是 Lakehouse 模式的核心优势。 |
| [索引](../ddl/indexes/databricks.md) | **无传统 B-tree 索引——Data Skipping + Z-ORDER + Liquid Clustering 替代**。Data Skipping 自动维护文件级 min/max 统计信息。Z-ORDER 通过 OPTIMIZE 命令重排数据布局。**Liquid Clustering(2023+) 是自适应替代方案**——写入时自动优化布局无需手动 OPTIMIZE。对比 BigQuery 的分区+聚集和 ClickHouse 的稀疏索引。 |
| [约束](../ddl/constraints/databricks.md) | **CHECK/NOT NULL 约束在 Delta Lake 上实际执行**——写入时违反约束会报错（对比 BigQuery/Redshift 约束仅作提示）。PK/FK 为信息性声明不强制校验——优化器可利用但不保证完整性。对比 PG/MySQL 的 PK/FK 强制执行和 Snowflake 的约束不强制执行模式。 |
| [视图](../ddl/views/databricks.md) | **VIEW/TEMPORARY VIEW 标准支持**，Dynamic View 实现行/列级安全——视图定义中嵌入权限逻辑（`CASE WHEN is_member('group') THEN col ELSE 'MASKED' END`）。无传统物化视图——Delta Live Tables（DLT）声明式 ETL 管道是替代方案。对比 Oracle 的 Fast Refresh+Query Rewrite（功能最强）和 BigQuery 的自动增量刷新。 |
| [序列与自增](../ddl/sequences/databricks.md) | **GENERATED ALWAYS AS IDENTITY 是 Delta Lake 的自增列方案**——Spark 分布式环境下序列号不保证连续（有间隙）。无独立 SEQUENCE 对象。对比 PG 的 IDENTITY/SERIAL/SEQUENCE 三种选择和 BigQuery 的 GENERATE_UUID()（无自增列），Databricks 的自增方案受分布式架构限制。 |
| [数据库/Schema/用户](../ddl/users-databases/databricks.md) | **Unity Catalog 提供跨工作区的统一数据治理**——三级命名空间（Catalog.Schema.Table）、列级权限、标签分类和自动数据血缘追踪。对比 BigQuery 的 Project.Dataset.Table + GCP IAM 和 Snowflake 的 Account.Database.Schema——Unity Catalog 的血缘追踪是差异化优势。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/databricks.md) | **无纯 SQL 动态 SQL**——Python/Scala Notebook 是动态逻辑的标准实现方式。Spark SQL 本身不支持 EXECUTE IMMEDIATE 或 PREPARE/EXECUTE。对比 PG/Oracle 的过程式动态 SQL 和 BigQuery 的 EXECUTE IMMEDIATE(2019+)——Databricks 将动态逻辑完全推到 Notebook 层。 |
| [错误处理](../advanced/error-handling/databricks.md) | **无过程式错误处理**——错误在 Notebook 单元格级别捕获（Python try/except 或 Scala try/catch）。SQL 层面无 TRY/CATCH 或 EXCEPTION WHEN。对比 PG/Oracle/SQL Server 丰富的过程式错误处理——Databricks 的错误处理完全依赖宿主语言，与 SQLite 的嵌入式模式类似。 |
| [执行计划](../advanced/explain/databricks.md) | **EXPLAIN EXTENDED 显示逻辑和物理执行计划**——Spark UI 提供可视化 DAG 视图、Stage 详情和 Shuffle 统计。Photon 引擎加速时执行计划会标注 Photon 算子。对比 PG 的 EXPLAIN ANALYZE（更精确的行数统计）和 BigQuery 的 Console Execution Details（按 Slot 度量）。 |
| [锁机制](../advanced/locking/databricks.md) | **Delta Lake 采用乐观并发控制 + 冲突检测**——并发写入同一表时通过事务日志检测冲突，冲突时后提交的事务重试或失败。无行级锁（文件级粒度）。对比 PG/MySQL 的行级锁高并发和 BigQuery 的 DML 配额限制——Delta Lake 的乐观并发适合批量 ETL 而非高频 OLTP。 |
| [分区](../advanced/partitioning/databricks.md) | **PARTITIONED BY 传统静态分区 + Liquid Clustering(2023+) 自适应替代**——Liquid Clustering 在写入时自动优化数据布局，无需手动 OPTIMIZE/ZORDER。对比 BigQuery 的 PARTITION BY + CLUSTER BY（需用户显式选择列）和 Snowflake 的微分区自动管理——Liquid Clustering 是最智能的分区方案之一。 |
| [权限](../advanced/permissions/databricks.md) | **Unity Catalog RBAC + Row/Column Filter + Data Lineage**——细粒度权限控制到列级别，行过滤器实现行级安全（类似 PG 的 RLS）。自动数据血缘追踪从表到列级别——无需手动维护血缘关系。对比 BigQuery 的 GCP IAM + Row/Column Access Policy 和 PG 的 RLS——Unity Catalog 的血缘追踪是独特优势。 |
| [存储过程](../advanced/stored-procedures/databricks.md) | **无 SQL 存储过程**——Python UDF、Notebook 和 Delta Live Tables 是过程化逻辑的替代方案。SQL UDF 可定义简单函数。对比 PG 的 PL/pgSQL 多语言过程和 Oracle 的 PL/SQL Package——Databricks 将复杂逻辑推到 Notebook/Python 层，符合数据工程师的工作模式。 |
| [临时表](../advanced/temp-tables/databricks.md) | **CREATE TEMPORARY VIEW 是会话级临时对象**——不创建物理数据，仅定义视图逻辑。Delta 表可通过 CACHE TABLE 缓存到内存加速重复查询。对比 PG/SQL Server 的 CREATE TEMP TABLE（创建物理临时数据）和 BigQuery 的 _SESSION.table_name——Databricks 偏向使用 TEMP VIEW 而非 TEMP TABLE。 |
| [事务](../advanced/transactions/databricks.md) | **Delta Lake ACID 事务是在数据湖上实现事务性的核心创新**——通过 JSON 事务日志（_delta_log）记录每次写操作的文件变更。**Time Travel 支持版本查询**——`SELECT * FROM t VERSION AS OF 5` 或 `TIMESTAMP AS OF '2024-01-01'`。对比 BigQuery 的 Time Travel(7 天) 和 Snowflake 的 Time Travel(最长 90 天)。 |
| [触发器](../advanced/triggers/databricks.md) | **无触发器**——Delta Live Tables（DLT）声明式 ETL 管道是替代方案——定义数据流转规则而非事件触发逻辑。对比 PG/Oracle 的完整触发器支持和 BigQuery 的 Pub/Sub + Cloud Functions 替代方案——Databricks 的 DLT 是更现代的数据管道设计模式。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/databricks.md) | **DELETE 在 Delta Lake 上是标记删除**——旧文件保留直到 VACUUM 清理（默认 7 天保留期，与 Time Travel 相关）。`VACUUM table_name RETAIN 168 HOURS` 清理旧版本文件释放存储。对比 PG 的 VACUUM 回收死元组和 BigQuery 的分区级 DELETE（重写整个分区），Delta Lake 的 DELETE 机制类似 LSM-Tree。 |
| [插入](../dml/insert/databricks.md) | **INSERT INTO/INSERT OVERWRITE 是标准写入方式**——INSERT OVERWRITE 覆盖分区数据（ETL 常用模式）。COPY INTO 从云存储批量加载文件（幂等，不重复导入已处理文件）。对比 BigQuery 的 LOAD JOB（免费）和 Redshift 的 COPY from S3——COPY INTO 的幂等性是 Databricks 的独特优势。 |
| [更新](../dml/update/databricks.md) | **UPDATE 在 Delta Lake 上重写受影响的文件**——列存格式下 UPDATE 代价比行存高（需重写整个 Parquet 文件）。Photon 引擎（C++ 向量化）加速 UPDATE 过程中的数据扫描和重写。对比 PG 的行级原地更新和 BigQuery 的分区级重写——Delta Lake 的 UPDATE 粒度介于两者之间（文件级）。 |
| [Upsert](../dml/upsert/databricks.md) | **MERGE INTO 是 Delta Lake 上功能完整的 CDC 语法**——WHEN MATCHED / WHEN NOT MATCHED / WHEN NOT MATCHED BY SOURCE 三分支覆盖所有 SCD 场景。对比 BigQuery 的 MERGE（DML 配额限制）和 PG 15+ 的 MERGE（较晚引入但功能类似），Databricks 的 MERGE 是 Lakehouse 数据管道的核心操作。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/databricks.md) | **GROUPING SETS/CUBE/ROLLUP 完整多维聚合**——collect_list/collect_set 将分组值收集为数组（Spark 独有，对比 PG 的 array_agg、BigQuery 的 ARRAY_AGG）。无 FILTER 子句（对比 PG 的条件聚合语法）。APPROX_COUNT_DISTINCT 近似去重计数（HyperLogLog）。 |
| [条件函数](../functions/conditional/databricks.md) | **IF/CASE/COALESCE/NVL/NVL2 混合风格**——IF(cond, true_val, false_val) 函数式条件（Spark 兼容，与 MySQL 的 IF() 相同）。NVL/NVL2 来自 Oracle 兼容性。COALESCE 标准。对比 PG 坚持标准 CASE（无 IF 函数）和 SQL Server 的 IIF——Databricks 兼容多种方言风格。 |
| [日期函数](../functions/date-functions/databricks.md) | **date_format/date_add/datediff 是 Spark SQL 日期函数标准**——格式化使用 Java SimpleDateFormat 模式（`yyyy-MM-dd`，对比 MySQL 的 `%Y-%m-%d` 和 Oracle 的 `YYYY-MM-DD`）。TIMESTAMP_NTZ(无时区) 是近年新增类型。对比 PG 的 INTERVAL 运算符（更自然）。 |
| [数学函数](../functions/math-functions/databricks.md) | **完整数学函数库（Spark 兼容）**——GREATEST/LEAST 内置、除零返回 NULL（与 MySQL 行为相同，对比 PG/Oracle 报错）。PERCENTILE_APPROX 近似百分位数。对比 BigQuery 的 SAFE_DIVIDE（独有安全语法）和 PG 的 NUMERIC 任意精度运算。 |
| [字符串函数](../functions/string-functions/databricks.md) | **concat/concat_ws/regexp_extract 是 Spark 风格字符串函数**——concat_ws 自动跳过 NULL（与 SQL Server 的 CONCAT_WS 功能相同）。regexp_extract 基于 Java 正则引擎（对比 BigQuery 基于 re2 线性时间引擎、PG 基于 POSIX 正则）。`\|\|` 拼接运算符也支持。 |
| [类型转换](../functions/type-conversion/databricks.md) | **TRY_CAST(Spark 3.4+) 终于支持安全类型转换**——失败返回 NULL 而非报错（对比 SQL Server 的 TRY_CAST 更早、BigQuery 的 SAFE_CAST 功能相同）。CAST 标准转换。类型系统与 Spark 一致——STRING/INT/BIGINT/DOUBLE/DECIMAL/ARRAY/MAP/STRUCT。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/databricks.md) | **WITH 标准 CTE + 递归 CTE(Spark 3.4+ 才支持)**——递归 CTE 到达较晚（对比 PG/Oracle/SQL Server 早已支持）。优化器自动决定 CTE 物化/内联。对比 PG 的可写 CTE（DML in WITH，Spark 不支持）和 BigQuery 的 CTE（优化器自动决定物化策略，功能接近）。 |
| [全文搜索](../query/full-text-search/databricks.md) | **无内置全文搜索**——需依赖外部搜索引擎（Elasticsearch/OpenSearch）或 Delta Lake 的 Bloom Filter 索引实现模糊过滤。对比 PG 的 tsvector+GIN（最强内置实现）和 BigQuery 的 SEARCH INDEX(2023+)——Databricks 在全文搜索上是空白。 |
| [连接查询](../query/joins/databricks.md) | **Broadcast/Sort-Merge/Shuffle Hash 三种 JOIN 策略（Spark 引擎决定）**——小表自动 Broadcast（广播到所有节点避免 Shuffle），大表间用 Sort-Merge 或 Shuffle Hash。对比 PG 的 Hash/Merge/Nested Loop（单机优化）和 BigQuery 的自动选择——Databricks 的 JOIN 策略可通过 Hint 手动干预。 |
| [分页](../query/pagination/databricks.md) | **LIMIT + ORDER BY 是唯一分页方式**——不支持 OFFSET（对比 PG/MySQL 的 LIMIT/OFFSET 和 SQL Server 的 OFFSET...FETCH）。分布式环境下 LIMIT 需将所有数据汇聚到 Driver 节点排序取 TopN。大结果集建议导出到文件而非分页查询。 |
| [行列转换](../query/pivot-unpivot/databricks.md) | **PIVOT/UNPIVOT 原生支持(Spark 兼容)**——`SELECT * FROM t PIVOT (SUM(amount) FOR year IN (2023, 2024))`。对比 Oracle 11g（最早引入 PIVOT）和 DuckDB 的 PIVOT ANY（自动检测值）——Databricks 的 PIVOT 需枚举值列表（动态 PIVOT 需 Notebook 逻辑）。 |
| [集合操作](../query/set-operations/databricks.md) | **UNION/INTERSECT/EXCEPT 完整支持（Spark 兼容）**——UNION 默认去重（SQL 标准行为），UNION ALL 保留重复。对比 MySQL 直到 8.0.31 才支持 INTERSECT/EXCEPT 和 Oracle 使用 MINUS 而非 EXCEPT——Databricks 的集合操作完整且标准。 |
| [子查询](../query/subquery/databricks.md) | **关联子查询支持（Spark 兼容）**——Spark 优化器会尝试将关联子查询转为 JOIN。EXISTS/IN/NOT EXISTS 标准支持。对比 PG 的 LATERAL 子查询（Spark 不支持 LATERAL JOIN 关键字但 UNNEST 替代部分场景）和 MySQL 5.x 的子查询性能噩梦。 |
| [窗口函数](../query/window-functions/databricks.md) | **完整窗口函数 + Photon 引擎向量化加速**——ROW_NUMBER/RANK/LAG/LEAD/FIRST_VALUE/LAST_VALUE 完整。Photon C++ 引擎将窗口函数性能提升数倍。无 QUALIFY 子句（对比 BigQuery/Snowflake/DuckDB——需子查询包装窗口过滤）。无 GROUPS 帧类型（PG/SQLite 独有）。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/databricks.md) | **sequence() + explode() 生成日期序列（Spark 兼容）**——`SELECT explode(sequence(DATE'2024-01-01', DATE'2024-12-31', INTERVAL 1 DAY))` 一行搞定。对比 PG 的 generate_series（功能相同但语法不同）和 BigQuery 的 GENERATE_DATE_ARRAY+UNNEST——Databricks 的 sequence+explode 模式与 Spark 生态一致。 |
| [去重](../scenarios/deduplication/databricks.md) | **ROW_NUMBER + 窗口函数是 SQL 层去重方案**——DataFrame API 的 dropDuplicates() 提供编程式替代。对比 PG 的 DISTINCT ON（最简写法）和 BigQuery/DuckDB 的 QUALIFY ROW_NUMBER()（无需子查询包装）——Databricks 无 QUALIFY 需子查询嵌套。 |
| [区间检测](../scenarios/gap-detection/databricks.md) | **sequence() + 窗口函数检测间隙**——sequence() 生成完整序列后 EXCEPT 实际数据，或用 LAG/LEAD 比较相邻行。对比 PG 的 generate_series+LEFT JOIN（更直观）和 Teradata 的 sys_calendar 系统日历表（独有）。 |
| [层级查询](../scenarios/hierarchical-query/databricks.md) | **递归 CTE(Spark 3.4+) 是层级查询方案**——到达较晚（对比 PG/Oracle/SQL Server 早已支持递归 CTE）。Spark 3.4 前需用 DataFrame API 的 graphX 或迭代循环模拟。对比 Oracle 的 CONNECT BY（更简洁的原创语法）和 SQL Server 的 hierarchyid 类型。 |
| [JSON 展开](../scenarios/json-flatten/databricks.md) | **from_json + explode 是 Spark 风格 JSON 展开**——from_json 将 JSON 字符串解析为 STRUCT/ARRAY，explode 展开为行。可直接查询 JSON 文件——`SELECT * FROM json.'/path/to/data.json'`。对比 PG 的 JSONB+json_array_elements 和 Snowflake 的 LATERAL FLATTEN——Databricks 的文件直查是独特优势。 |
| [迁移速查](../scenarios/migration-cheatsheet/databricks.md) | **Spark SQL 兼容 + Delta Lake 扩展是核心差异**——函数命名与 Spark 一致（date_format 而非 TO_CHAR）、ARRAY/MAP/STRUCT 原生类型、Notebook 工作流模式。从传统数仓迁入需适应 Delta Lake ACID 事务模型、OPTIMIZE/VACUUM 维护和 Liquid Clustering 物理布局策略。 |
| [TopN 查询](../scenarios/ranking-top-n/databricks.md) | **ROW_NUMBER + 窗口函数是分组 TopN 标准方案**——全局 TopN 直接 ORDER BY + LIMIT。无 QUALIFY 子句（对比 BigQuery/DuckDB 一行搞定分组 TopN）。无 FETCH FIRST WITH TIES（对比 PG 13+/SQL Server 包含并列行）。 |
| [累计求和](../scenarios/running-total/databricks.md) | **SUM() OVER(ORDER BY ...) 标准累计求和（Spark 兼容）**——Photon 引擎向量化加速窗口函数执行。分布式环境下窗口函数在分区内并行计算。对比 PG（单机高效但无分布式并行）和 BigQuery（Slot 自动扩展无需人工优化）。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/databricks.md) | **MERGE INTO 是 Delta Lake 上 SCD 的核心实现**——WHEN MATCHED / WHEN NOT MATCHED / WHEN NOT MATCHED BY SOURCE 覆盖 Type 1/2/3。Time Travel 可回溯查询变更前的历史数据辅助验证。对比 Oracle 的 MERGE 多分支（首创）和 SQL Server 的 Temporal Tables（自动历史版本）。 |
| [字符串拆分](../scenarios/string-split-to-rows/databricks.md) | **split() + explode() 是 Spark 风格字符串拆分**——`SELECT explode(split('a,b,c', ','))` 一行完成。对比 PG 14 的 string_to_table（一行搞定）和 MySQL 的递归 CTE+SUBSTRING_INDEX（最繁琐）——Databricks 的 split+explode 模式简洁且与 Spark 生态一致。 |
| [窗口分析](../scenarios/window-analytics/databricks.md) | **完整窗口函数 + Photon C++ 引擎向量化加速**——ROW_NUMBER/RANK/LAG/LEAD/SUM OVER 等完整。无 QUALIFY 子句、无 FILTER 子句、无 GROUPS 帧类型。Photon 引擎将窗口函数性能提升数倍。对比 PG（FILTER+GROUPS 独有）和 BigQuery（QUALIFY 无需子查询包装）。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/databricks.md) | **ARRAY/MAP/STRUCT 原生类型是 Spark 的核心优势**——`ARRAY(1,2,3)`、`MAP('key','val')`、`STRUCT(name STRING, age INT)` 一等公民。explode() 展开数组/Map 为行。对比 BigQuery 的 STRUCT/ARRAY（功能相似但语法不同）和 PG 的原生 ARRAY+运算符——Databricks 的 MAP 类型是独特优势（PG 需 hstore 扩展）。 |
| [日期时间](../types/datetime/databricks.md) | **DATE/TIMESTAMP/TIMESTAMP_NTZ 三种时间类型**——TIMESTAMP 含时区（UTC 存储），TIMESTAMP_NTZ 无时区（Spark 3.4+）。对比 PG 的 TIMESTAMP WITH/WITHOUT TZ 和 BigQuery 的四种时间类型（DATE/TIME/DATETIME/TIMESTAMP）——Databricks 的 TIMESTAMP_NTZ 是较新引入填补无时区时间戳需求。 |
| [JSON](../types/json/databricks.md) | **from_json/to_json 是 Spark 风格 JSON 处理**——from_json 将字符串解析为强类型 STRUCT/ARRAY，比文本解析更高效。可直接读取 JSON 文件作为表查询。对比 PG 的 JSONB+GIN 索引（查询优化最强）和 BigQuery 的 JSON 类型+点号访问——Databricks 的 JSON 处理偏向 ETL 解析而非查询优化。 |
| [数值类型](../types/numeric/databricks.md) | **TINYINT/SMALLINT/INT/BIGINT + FLOAT/DOUBLE/DECIMAL（Spark 兼容）**——DECIMAL 最高精度 38 位。完整数值类型覆盖。对比 PG 的 NUMERIC（无精度上限）和 BigQuery 的 INT64（只有一种整数类型）——Databricks 的数值类型体系与传统数据库最接近。 |
| [字符串类型](../types/string/databricks.md) | **STRING 无长度限制（Spark 兼容），UTF-8 编码**——无 VARCHAR(n)/CHAR(n)/TEXT 区分（极简设计，与 BigQuery 的 STRING 相同）。BINARY 类型存储二进制数据。对比 PG 的 TEXT=VARCHAR（无性能差异）和 MySQL 的 utf8/utf8mb4 混淆——Databricks 的 STRING 设计最简洁。 |
