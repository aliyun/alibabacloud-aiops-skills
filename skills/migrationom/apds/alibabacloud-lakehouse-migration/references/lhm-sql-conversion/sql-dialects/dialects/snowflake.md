# Snowflake

**分类**: 云原生数仓
**文件数**: 51 个 SQL 文件
**总行数**: 5306 行

> **关键人物**：[Dageville, Cruanes, Żukowski](../docs/people/snowflake-founders.md)（Oracle/VectorWise 出身）

## 概述与定位

Snowflake 是云原生数据仓库的领导者，以**存储与计算完全分离**的架构著称。不同于传统数仓绑定特定硬件或虚拟机，Snowflake 在 AWS/Azure/GCP 之上构建了独立的三层架构，实现了真正的弹性伸缩。其核心理念是"零管理"——用户无需关心索引创建、数据分布、VACUUM 或统计信息收集，引擎自动处理一切物理优化。

Snowflake 的定位已从纯数仓演化为"Data Cloud"平台，通过 Secure Data Sharing、Snowpark、Marketplace 等能力，将自身定义为数据协作与数据应用的基础设施。

## 历史与演进

| 时间 | 里程碑 |
|------|--------|
| 2012 | Benoit Dageville（Oracle 前核心工程师）和 Thierry Cruanes 联合创立 Snowflake |
| 2014 | 产品正式 GA，首次在 AWS 上提供云原生数仓服务 |
| 2018 | 支持 Azure，开启多云战略；推出 Time Travel 和零拷贝 CLONE |
| 2020 | 史上最大软件 IPO（市值一度超 $700 亿）；推出 Data Cloud 概念 |
| 2022 | Snowpark（Python/Java/Scala 编程框架）GA，拓展数据工程和 ML 场景 |
| 2023 | 推出 Snowflake Cortex（AI/LLM 集成）、Unistore（混合事务/分析）、Iceberg Tables |

## 核心设计思路

- **三层分离架构**：Cloud Services 层（优化器、元数据、安全）、Compute 层（Virtual Warehouse）、Storage 层（微分区存储于云对象存储）。三层独立伸缩，互不影响。关闭 Warehouse 时只消耗极少量 Cloud Services 费用。
- **微分区自动管理**：数据自动按插入顺序组织成 50-500 MB 的不可变微分区（Micro-partition），每个分区记录列级 min/max/count 等元数据。查询时通过**分区裁剪**（Pruning）跳过无关分区，效果类似索引但无需手动创建或维护。
- **零管理哲学**：没有索引、没有 VACUUM、没有手动统计信息收集。这降低了运维复杂度，但也意味着用户无法针对特定查询模式做精细的物理优化——必须信任引擎的自动决策。
- **Time Travel**：所有数据变更保留历史版本（Enterprise 版最长 90 天），可以通过 `AT(TIMESTAMP => ...)` 或 `BEFORE(STATEMENT => ...)` 查询任意历史时间点的数据。这一能力建立在微分区不可变性之上。

## 独特特色

- **VARIANT 半结构化类型**：原生支持 JSON/Avro/XML/Parquet 数据加载到 VARIANT 列，查询时用 `:` 和 `[]` 操作符访问嵌套字段（如 `v:user.name::STRING`）。无需预定义 Schema，实现了 Schema-on-Read 与 Schema-on-Write 的平衡。
- **QUALIFY 子句**：在 `WHERE`/`HAVING` 之后直接过滤窗口函数结果，如 `QUALIFY ROW_NUMBER() OVER(...) = 1`。这消除了传统方案中必须用子查询包装的痛点，是 Snowflake 对 SQL 标准的有价值扩展。
- **零拷贝 CLONE**：`CREATE TABLE t2 CLONE t1` 不复制数据，仅复制元数据指针。底层基于 Copy-on-Write（COW）机制，修改 t2 时才产生新分区。可以在秒级别克隆 TB 级表用于测试。
- **Time Travel + UNDROP**：误删表可以用 `UNDROP TABLE t` 恢复；误操作可以 `SELECT ... AT(TIMESTAMP => '...')` 查看历史数据并恢复。这极大降低了人为误操作的风险。
- **FLATTEN 函数**：将 VARIANT 中的数组/对象展开为行，配合 LATERAL 实现嵌套数据的关系化查询。
- **三种 TIMESTAMP 类型**：TIMESTAMP_NTZ（无时区）、TIMESTAMP_LTZ（本地时区）、TIMESTAMP_TZ（带时区偏移量）。虽然语义精确，但增加了认知负担——新用户经常混淆三者。
- **Virtual Warehouse 弹性计算**：计算资源按 T-Shirt 尺寸（XS 到 6XL）配置，可以随时启停和扩缩，不同团队使用不同 Warehouse 实现资源隔离和成本分摊。
- **Secure Data Sharing**：无需复制数据即可跨账户共享表和视图，消费方直接查询提供方的数据，解决了传统 ETL 数据交换的延迟和成本问题。
- **Dynamic Tables（2024 GA）**：声明式数据管道——`CREATE DYNAMIC TABLE ... AS SELECT ...`，系统自动增量刷新。替代了传统的 Task + Stream 组合，大幅简化 ETL 管道。支持从 Iceberg 表读取和写入。
- **Hybrid Tables（2024 GA Azure）**：在 Snowflake 中支持 OLTP 式操作——行级 INSERT/UPDATE/DELETE 低延迟。Hybrid Tables 既能高并发点操作，又能与普通分析表 JOIN。打破了"数仓不能做 OLTP"的边界。
- **Cortex AI SQL（2025 预览）**：将生成式 AI 直接嵌入 SQL——`CORTEX.COMPLETE()`（LLM 调用）、`CORTEX.EMBED()`（向量化）、`CORTEX.SENTIMENT()`（情感分析）。对标 BigQuery AI Functions。
- **Iceberg Tables**：原生 Snowflake-managed Iceberg 表，数据以 Parquet 格式存储在用户的对象存储中（S3/Azure/GCS）。支持 Spark/Trino 等外部引擎直接读取——消除供应商锁定。
- **Snowpark**：DataFrame API（Python/Java/Scala），在 Snowflake 计算层执行代码。对标 Spark DataFrame，但运行在 Snowflake 基础设施上。

## 已知的设计不足与历史包袱

- **约束不执行**：PRIMARY KEY、FOREIGN KEY、UNIQUE 均声明为 `NOT ENFORCED`，仅用于文档和优化器提示。这与 BigQuery 类似，是云数仓在高吞吐写入与约束校验之间的取舍。
- **无索引**：完全依赖微分区裁剪。对于高基数列（如 UUID）的点查询，无法通过索引加速，只能靠 CLUSTER BY 改善数据布局。但 CLUSTER BY 是后台异步操作，不保证即时生效。
- **事务隔离仅 READ COMMITTED**：不支持 REPEATABLE READ 或 SERIALIZABLE。对于需要强隔离级别的场景，应用层必须自行处理。
- **存储过程能力有限**：支持 JavaScript、SQL Script、Python、Java 编写存储过程，但功能和调试体验远不及 Oracle PL/SQL 或 SQL Server T-SQL。缺乏包（Package）、物化变量等高级抽象。
- **三种 TIMESTAMP 增加认知负担**：TIMESTAMP_NTZ/LTZ/TZ 的隐式转换规则复杂，TIMESTAMP_TYPE_MAPPING 参数影响默认行为，经常导致时区相关的 bug。

## 兼容生态

Snowflake SQL 语法主体兼容 ANSI SQL，同时借鉴了 Oracle（如 QUALIFY）、PostgreSQL（如 :: 类型转换）等方言的特性。支持 ODBC/JDBC/Python Connector/Go Driver。通过 External Functions 可调用 AWS Lambda/Azure Functions，通过 Snowpark 支持 Python/Java/Scala DataFrame API。

## 对引擎开发者的参考价值

- **微分区架构**：不可变微分区 + 列级元数据（min/max/count/null_count）的设计，证明了在云对象存储之上可以实现高效的分区裁剪，无需传统索引。这一思路被后来的 Delta Lake、Iceberg 等 Lakehouse 格式借鉴。
- **Metadata-based 查询优化**：`COUNT(*)`、`MIN()`、`MAX()` 等聚合在分区元数据层直接完成，无需扫描数据。这种"元数据即索引"的策略是零管理架构的核心支撑。
- **CLONE 的 COW 实现**：基于不可变分区的 Copy-on-Write 克隆机制，在存储层实现 O(1) 复制。这一技术对数据库分支（Database Branching）功能有重要参考意义。

---

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/snowflake.md) | **微分区自动管理是核心设计——用户无需选择分区列或创建索引**。数据自动组织为 50-500MB 不可变微分区，列级 min/max 元数据支持自动 Pruning。VARIANT 列原生存储半结构化数据（JSON/Avro/XML）。CLUSTER BY 仅作优化提示（后台异步重组织），不保证即时生效。对比 BigQuery（需用户显式选择分区列）和 Hive（分区=目录需手动管理），Snowflake 的零管理哲学最彻底。 |
| [改表](../ddl/alter-table/snowflake.md) | **ALTER 操作瞬时完成（纯元数据操作），无锁无停机**——ADD/DROP COLUMN、RENAME、SET COMMENT 等毫秒级执行。但**不支持 MODIFY COLUMN TYPE**（需 CTAS 重建），CLUSTER BY 变更后台异步重组织。对比 BigQuery（同样不支持改列类型）和 ClickHouse（ALTER 异步 Mutation），Snowflake 的元数据操作速度最快但 Schema 演进受限。 |
| [索引](../ddl/indexes/snowflake.md) | **无用户创建的传统索引——自动微分区 Pruning + Search Optimization Service(SOS)**。SOS 是付费的查询加速服务，为高基数列（如 UUID）的等值/IN 查询建立内部搜索结构。对比 BigQuery（SEARCH INDEX 全文搜索 2023+）和 ClickHouse（稀疏索引+跳数索引），Snowflake 用付费服务替代了手动索引创建。 |
| [约束](../ddl/constraints/snowflake.md) | **PK/FK/UNIQUE 全部 NOT ENFORCED——仅作元数据提示供优化器使用**。NOT NULL 是唯一实际执行的约束。优化器利用 PK/FK 声明消除冗余 JOIN（Join Elimination）。对比 BigQuery（同样 NOT ENFORCED）和 PG/MySQL（强制执行），Snowflake 的约束设计是云数仓在高吞吐写入与完整性校验之间的典型取舍。 |
| [视图](../ddl/views/snowflake.md) | **物化视图自动增量维护，Secure View 隐藏底层定义**——物化视图在基表变更后自动增量刷新（Enterprise 版）。Secure View 确保视图定义对查询用户不可见（防止通过 EXPLAIN 推断底层数据结构）。对比 BigQuery（物化视图自动刷新+智能查询改写）和 PG（REFRESH MATERIALIZED VIEW 需手动），Snowflake 的物化视图自动化程度高但查询改写能力不如 Oracle。 |
| [序列与自增](../ddl/sequences/snowflake.md) | **AUTOINCREMENT/IDENTITY + SEQUENCE 对象双方案**——AUTOINCREMENT 不保证连续（多节点并行写入时有间隙），SEQUENCE 独立对象可跨表共享。对比 BigQuery（无自增，仅 GENERATE_UUID）和 PG（SERIAL/IDENTITY 保证连续），Snowflake 的自增设计兼顾了分布式架构和 SQL 标准兼容性。 |
| [数据库/Schema/用户](../ddl/users-databases/snowflake.md) | **Database.Schema.Object 三级命名空间 + RBAC 最完善的云数仓**——FUTURE GRANTS 可自动授权未来创建的新对象（避免权限管理滞后）。Account 级别支持 Org-level 管理。对比 BigQuery（完全基于 GCP IAM 无 SQL GRANT）和 Hive（依赖外部 Ranger），Snowflake 的内置 RBAC 是云数仓中最成熟的。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/snowflake.md) | **Snowflake Scripting + EXECUTE IMMEDIATE 支持多语言动态 SQL**——SQL Script、JavaScript、Python、Scala、Java 均可编写存储过程。EXECUTE IMMEDIATE 动态执行 SQL 字符串。对比 BigQuery（EXECUTE IMMEDIATE 2019+）和 MaxCompute（Script Mode），Snowflake 的多语言支持在云数仓中最丰富。 |
| [错误处理](../advanced/error-handling/snowflake.md) | **EXCEPTION 块(Snowflake Scripting) + SQLCODE/SQLERRM 捕获错误**——BEGIN...EXCEPTION WHEN OTHER THEN... 语法类似 PL/SQL。支持自定义异常和条件处理。对比 BigQuery（BEGIN...EXCEPTION WHEN ERROR 更简单）和 Hive（无任何错误处理），Snowflake 的错误处理是云数仓中最接近 Oracle PL/SQL 的。 |
| [执行计划](../advanced/explain/snowflake.md) | **EXPLAIN 文本输出 + Query Profile 图形化分析**——Query Profile 在 Web UI 中可视化展示算子树、数据分布和 Warehouse 资源消耗。可识别 Pruning 效果、Spilling（内存溢出到磁盘）和 Remote Disk I/O。对比 BigQuery（无 EXPLAIN 仅 Console 执行详情）和 Spark（EXPLAIN EXTENDED 信息量最大），Snowflake 的 Query Profile 可视化体验最佳。 |
| [锁机制](../advanced/locking/snowflake.md) | **自动并发控制，无用户可见锁——乐观并发 + 微分区不可变性**。并发写入同一表时后提交者可能因冲突失败（Statement-level retry 自动重试）。对比 BigQuery（DML 配额限制并发）和 PG（行级悲观锁），Snowflake 的乐观并发模型适合分析负载但不适合高并发 OLTP。 |
| [分区](../advanced/partitioning/snowflake.md) | **自动微分区(Micro-Partition)——用户无需管理，CLUSTER BY 仅作优化提示**。每个微分区 50-500MB，不可变，列级 min/max/count/null_count 元数据自动维护。CLUSTER BY 声明后后台 Automatic Clustering 服务持续重组织数据（Enterprise 版付费）。对比 BigQuery（需用户选择分区列）和 Hive（分区=目录需显式管理），Snowflake 的分区管理自动化程度最高。 |
| [权限](../advanced/permissions/snowflake.md) | **RBAC+DAC 双模型——FUTURE GRANTS 自动授权新对象是独有亮点**。RBAC（基于角色的访问控制）+ DAC（自主访问控制）结合。Row Access Policy 实现行级安全，Column-level Security 实现列级安全。对比 BigQuery（GCP IAM 无 SQL GRANT）和 PG（RLS 行级安全），Snowflake 的权限系统在功能完整性上领先。 |
| [存储过程](../advanced/stored-procedures/snowflake.md) | **JavaScript/SQL/Python/Scala/Java 五种语言编写存储过程**——多语言支持是 Snowflake 的独有优势。存储过程可访问 Snowflake API、执行 DDL/DML、调用外部函数。对比 Oracle（PL/SQL 功能最强但仅一种语言）和 BigQuery（SQL+JavaScript），Snowflake 的多语言灵活度最高。 |
| [临时表](../advanced/temp-tables/snowflake.md) | **TEMPORARY+TRANSIENT 表——Time Travel 保留期不同是关键区别**。TEMPORARY 表会话结束后清理（0-1 天 Time Travel），TRANSIENT 表持久存储但无 Fail-safe（0-1 天 Time Travel）。对比 BigQuery（_SESSION 临时表事务结束清理）和 PG（ON COMMIT DROP/DELETE ROWS），Snowflake 的 TRANSIENT 表是低成本存储的独有选择。 |
| [事务](../advanced/transactions/snowflake.md) | **ACID 事务，自动提交默认开启**——READ COMMITTED 是唯一隔离级别（不支持 REPEATABLE READ/SERIALIZABLE）。每条 DML 自动提交，可通过 `BEGIN TRANSACTION` 开启多语句事务。对比 PG（支持所有隔离级别）和 BigQuery（多语句事务有 DML 配额），Snowflake 的事务设计偏向分析负载而非高并发 OLTP。 |
| [触发器](../advanced/triggers/snowflake.md) | **无触发器——Streams+Tasks 替代事件驱动**。Stream 捕获表的变更数据（INSERT/UPDATE/DELETE），Task 定时或事件触发执行 SQL。Dynamic Tables(2024 GA)进一步简化了声明式数据管道。对比 ClickHouse（物化视图=INSERT 触发器）和 PG（BEFORE/AFTER 触发器完整），Snowflake 的 Streams+Tasks 模型更适合 ETL 管道。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/snowflake.md) | **DELETE 标准语法，Time Travel 可恢复误删数据(1-90天)**——UNDROP TABLE 可恢复整表删除。DELETE 内部重写受影响的微分区（非原地删除）。对比 BigQuery（DELETE 必须带 WHERE）和 ClickHouse（Lightweight Delete 标记删除），Snowflake 的 Time Travel+UNDROP 是误操作恢复最强的方案。 |
| [插入](../dml/insert/snowflake.md) | **INSERT + COPY INTO 批量加载(S3/Azure/GCS) + Snowpipe 流式摄取**——COPY INTO 是推荐的批量导入方式（直接从云存储加载，性能最优）。Snowpipe 自动监听云存储新文件并持续加载。对比 BigQuery（批量加载免费，Storage Write API exactly-once）和 Hive（LOAD DATA 文件移动），Snowflake 的 COPY INTO+Snowpipe 是云数仓中最成熟的数据摄取方案。 |
| [更新](../dml/update/snowflake.md) | **UPDATE 标准语法+多表 UPDATE（FROM 子句关联其他表）**——内部重写受影响的微分区。多表 UPDATE 语法 `UPDATE t SET ... FROM s WHERE t.id = s.id` 简化了关联更新。对比 BigQuery（UPDATE 不支持多表 FROM）和 PG（UPDATE...FROM 相同语法），Snowflake 的多表 UPDATE 在云数仓中最实用。 |
| [Upsert](../dml/upsert/snowflake.md) | **MERGE INTO 标准完整实现——WHEN MATCHED/NOT MATCHED/NOT MATCHED BY SOURCE**。不支持 ON CONFLICT/ON DUPLICATE KEY（非 MySQL/PG 语法）。MERGE 配合 Streams 可实现 CDC 增量同步。对比 BigQuery（MERGE 是唯一 Upsert，WHEN NOT MATCHED BY SOURCE 可实现 SCD）和 ClickHouse（无 MERGE 语句），Snowflake 的 MERGE 功能与 BigQuery 并列最完整。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/snowflake.md) | **LISTAGG（Oracle 风格字符串聚合）+ ARRAY_AGG（返回原生 ARRAY）**——GROUPING SETS/CUBE/ROLLUP 完整。APPROX_COUNT_DISTINCT(HyperLogLog)提供近似去重。LISTAGG 是 Snowflake 对 Oracle 用户的友好设计（对比 PG 的 STRING_AGG 和 MySQL 的 GROUP_CONCAT）。对比 ClickHouse 的 -If 组合聚合（最灵活）和 BigQuery 的 COUNTIF（条件计数），Snowflake 的聚合函数覆盖 Oracle+标准 SQL 两大风格。 |
| [条件函数](../functions/conditional/snowflake.md) | **IFF(condition, true_val, false_val) 简洁三元条件——对比标准 CASE WHEN 更简洁**。DECODE(Oracle 风格多值匹配)、NVL/NVL2(Oracle 风格 NULL 处理)均支持。对比 BigQuery 的 SAFE_ 前缀（错误返回 NULL）和 ClickHouse 的 multiIf（函数式条件），Snowflake 对 Oracle 用户的兼容性最强。 |
| [日期函数](../functions/date-functions/snowflake.md) | **DATE_TRUNC/DATEADD/DATEDIFF 标准命名，LAST_DAY 快速获取月末**——TO_DATE/TO_TIMESTAMP 支持灵活的格式化字符串解析。TIMESTAMPDIFF/TIMESTAMPADD 提供 MySQL 风格兼容。对比 BigQuery 的 GENERATE_DATE_ARRAY（日期序列生成）和 Hive 的 unix_timestamp 互转风格，Snowflake 的日期函数在标准 SQL 和多方言兼容之间取得最佳平衡。 |
| [数学函数](../functions/math-functions/snowflake.md) | **GREATEST/LEAST 内置，完整数学函数集**——DIV0/DIV0NULL 是 Snowflake 独有的安全除法函数：DIV0 除零返回 0，DIV0NULL 除零返回 NULL。对比 BigQuery 的 SAFE_DIVIDE（除零返回 NULL）和 PG 的除零报错，Snowflake 提供了两种除零处理策略供用户选择。 |
| [字符串函数](../functions/string-functions/snowflake.md) | **SPLIT_PART(str, delim, n) 按位置提取分隔片段——比 Hive/Spark 的 split()[n] 更直观**。STRTOK 类似但语义略有差异。REGEXP_REPLACE/REGEXP_SUBSTR 正则完整（PCRE 风格）。对比 BigQuery 的 SPLIT 返回 ARRAY（需 UNNEST 展开）和 PG 的 split_part（相同语法），Snowflake 的字符串处理在简洁性上领先。 |
| [类型转换](../functions/type-conversion/snowflake.md) | **TRY_CAST 安全转换 + :: 运算符(PG 风格简写)**——`col::INT` 等价于 `CAST(col AS INT)`。TRY_TO_NUMBER/TRY_TO_DATE 等 TRY_ 系列函数提供细粒度安全转换。隐式转换规则适度（比 MySQL 严格、比 PG 宽松）。对比 BigQuery 的 SAFE_CAST（统一前缀）和 Hive（无安全转换），Snowflake 的 TRY_ 函数族覆盖最广。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/snowflake.md) | **WITH 标准 + 递归 CTE + RESULT_SCAN 缓存上一查询结果**——`RESULT_SCAN(LAST_QUERY_ID())` 可将上一条查询的结果当作临时表引用，无需重复执行。对比 BigQuery（递归 CTE 有迭代限制）和 PG（标准递归 CTE），Snowflake 的 RESULT_SCAN 是独有的便捷功能。 |
| [全文搜索](../query/full-text-search/snowflake.md) | **无传统全文索引——LIKE/REGEXP/CONTAINS + Search Optimization Service(SOS)**。SOS（付费）为 LIKE 模式匹配和子字符串搜索建立内部搜索加速结构。对比 BigQuery（SEARCH INDEX+SEARCH() 2023+）和 Doris（倒排索引 2.0+ 基于 CLucene），Snowflake 的全文搜索是付费增值服务而非内置能力。 |
| [连接查询](../query/joins/snowflake.md) | **JOIN 完整标准支持 + LATERAL FLATTEN 展开半结构化数据是标志性语法**——`LATERAL FLATTEN(input => v:items)` 将 VARIANT 中的数组/对象展开为行。JOIN 策略由优化器全自动选择（无用户 Hint）。对比 BigQuery 的 CROSS JOIN UNNEST（展开 ARRAY）和 Hive 的 LATERAL VIEW EXPLODE，Snowflake 的 LATERAL FLATTEN 是处理半结构化数据最优雅的方案。 |
| [分页](../query/pagination/snowflake.md) | **LIMIT/OFFSET 标准 + FETCH FIRST N ROWS ONLY（ANSI 语法）均支持**——两种分页语法完全等价。对比 BigQuery（LIMIT/OFFSET 但按扫描量计费不受 OFFSET 影响）和 Hive（无 OFFSET 需 ROW_NUMBER 模拟），Snowflake 的分页语法兼容性最强。 |
| [行列转换](../query/pivot-unpivot/snowflake.md) | **PIVOT/UNPIVOT 原生支持——PIVOT ANY（动态值检测）是独有亮点**。PIVOT 可手动枚举值列表或使用 ANY 自动检测。对比 BigQuery 的 PIVOT（需枚举值）和 Spark 的 PIVOT/UNPIVOT(3.4+)，Snowflake 的 PIVOT ANY 自动化程度最高。 |
| [集合操作](../query/set-operations/snowflake.md) | **UNION/INTERSECT/EXCEPT + ALL 变体完整支持**——语义与 SQL 标准完全一致。对比 ClickHouse（UNION 默认 ALL 与标准相反）和 Hive（2.0+ 才完整），Snowflake 的集合操作标准完备。 |
| [子查询](../query/subquery/snowflake.md) | **关联子查询优化成熟，标量子查询完整支持**——优化器善于将子查询去关联化并转为 JOIN。对比 MySQL 5.x 的子查询性能噩梦和 BigQuery 的自动转 JOIN，Snowflake 的子查询优化在云数仓中属于领先水平。 |
| [窗口函数](../query/window-functions/snowflake.md) | **完整窗口函数 + QUALIFY 子句（同 BigQuery）——最大亮点**。`QUALIFY ROW_NUMBER() OVER(...) = 1` 无需子查询包装即可过滤窗口函数结果。WINDOW 命名子句支持。ROWS/RANGE 帧完整。对比 MySQL/PG/Oracle（均不支持 QUALIFY）和 ClickHouse（21.1+ 才支持窗口函数），Snowflake 的 QUALIFY 与 BigQuery 共同引领了这一语法扩展。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/snowflake.md) | **GENERATOR(ROWCOUNT=>N)+ROW_NUMBER 或 TABLE(GENERATOR()) 生成日期序列**——`SELECT DATEADD(day, ROW_NUMBER() OVER(...)-1, '2024-01-01') FROM TABLE(GENERATOR(ROWCOUNT=>365))` 虽然冗长但灵活。对比 BigQuery 的 GENERATE_DATE_ARRAY+UNNEST（一行搞定）和 Spark 的 sequence()+explode()，Snowflake 的日期序列生成语法较为繁琐。 |
| [去重](../scenarios/deduplication/snowflake.md) | **QUALIFY ROW_NUMBER() OVER(...) = 1 是最简去重写法——无需子查询包装**。对比 BigQuery（同样支持 QUALIFY）和 Hive/Spark（必须子查询包装），Snowflake 的 QUALIFY 使去重代码量减少 50%。 |
| [区间检测](../scenarios/gap-detection/snowflake.md) | **GENERATOR+窗口函数检测间隙——GENERATOR 生成期望序列与实际数据对比**。对比 ClickHouse 的 WITH FILL（独有语法最简洁）和 PG 的 generate_series+LEFT JOIN，Snowflake 的方案灵活但不如专用函数简洁。 |
| [层级查询](../scenarios/hierarchical-query/snowflake.md) | **递归 CTE + 部分 CONNECT BY 兼容**——Snowflake 支持 Oracle 的 CONNECT BY/START WITH/PRIOR 语法（部分兼容），降低了 Oracle 迁移成本。对比 PG（仅标准递归 CTE）和 Oracle（CONNECT BY 完整），Snowflake 在 Oracle 兼容层级查询方面最友好。 |
| [JSON 展开](../scenarios/json-flatten/snowflake.md) | **LATERAL FLATTEN 展开 VARIANT 中的数组/对象——Snowflake 独有的最优雅 JSON 展开语法**。`LATERAL FLATTEN(input => v:items) f` 直接展开嵌套结构，`f.value:name::STRING` 访问字段。对比 BigQuery 的 JSON_QUERY_ARRAY+UNNEST（需两步）和 Hive 的 get_json_object（需手动解析），Snowflake 的 FLATTEN 在半结构化数据处理上无出其右。 |
| [迁移速查](../scenarios/migration-cheatsheet/snowflake.md) | **三大核心差异：VARIANT 半结构化类型、自动微分区（无索引）、约束 NOT ENFORCED**。零拷贝 CLONE 可秒级创建测试环境。Time Travel+UNDROP 防误操作。三种 TIMESTAMP 类型的时区处理需特别注意。对比 BigQuery（INT64/STRING 独特类型命名）和 ClickHouse（ENGINE 选择是核心），Snowflake 的迁移重点在于适应零管理哲学。 |
| [TopN 查询](../scenarios/ranking-top-n/snowflake.md) | **QUALIFY ROW_NUMBER() OVER(...) <= N 是最简 TopN——无需嵌套子查询**。`SELECT * FROM t QUALIFY ROW_NUMBER() OVER(PARTITION BY g ORDER BY v DESC) <= 3` 一行搞定分组 TopN。对比 BigQuery（同样 QUALIFY）和 ClickHouse 的 LIMIT BY（每组限行独有语法），Snowflake 和 BigQuery 的 QUALIFY 方案并列最优雅。 |
| [累计求和](../scenarios/running-total/snowflake.md) | **SUM() OVER(ORDER BY ...) 标准窗口累计——Warehouse 弹性扩展计算资源**。可通过扩大 Warehouse 尺寸（XS→XL）线性提升复杂窗口计算的性能。对比 BigQuery（Slot 自动扩展，用户无需手动调整）和 ClickHouse（runningAccumulate 状态函数），Snowflake 的资源控制在灵活性上最强。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/snowflake.md) | **MERGE+Streams 变更捕获+Time Travel 辅助——SCD 完整方案**。Stream 自动记录表的 INSERT/UPDATE/DELETE 变更，定时 Task 触发 MERGE 应用变更。Time Travel 可查询任意历史时间点数据用于审计。对比 BigQuery 的 MERGE+Time Travel（7 天）和 Spark+Delta 的 MERGE+CDF，Snowflake 的 Streams+Tasks+Time Travel 三件套是最成熟的 SCD 基础设施。 |
| [字符串拆分](../scenarios/string-split-to-rows/snowflake.md) | **SPLIT_TO_TABLE(str, delim) 一步到位——Snowflake 独有的最简拆分展开函数**。或用 LATERAL FLATTEN(SPLIT(str, delim)) 实现。对比 BigQuery 的 SPLIT+UNNEST（两步）和 Hive 的 SPLIT+LATERAL VIEW EXPLODE（最冗长），Snowflake 的 SPLIT_TO_TABLE 是字符串拆分最简洁的方案。 |
| [窗口分析](../scenarios/window-analytics/snowflake.md) | **完整窗口函数 + QUALIFY 过滤 + WINDOW 命名子句——云数仓中窗口分析最强**。WINDOW w AS (PARTITION BY g ORDER BY v) 定义命名窗口，多个窗口函数可复用。QUALIFY 直接过滤窗口函数结果。对比 BigQuery（同样 QUALIFY+WINDOW 命名）和 Hive/Spark（无 QUALIFY 无命名），Snowflake 和 BigQuery 在窗口分析语法上并列领先。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/snowflake.md) | **VARIANT/ARRAY/OBJECT 半结构化原生支持——Schema-on-Read 与 Schema-on-Write 的平衡**。VARIANT 列可存储任意 JSON 结构无需预定义 Schema，查询时用 `:` 和 `[]` 操作符访问字段。内部自动将常见字段列化存储（自动 Schema 检测）以提升查询性能。对比 BigQuery 的 STRUCT/ARRAY（需预定义 Schema）和 ClickHouse 的 Nested（半结构化支持有限），Snowflake 的 VARIANT 是半结构化数据处理的标杆。 |
| [日期时间](../types/datetime/snowflake.md) | **DATE/TIME + 三种 TIMESTAMP(NTZ/LTZ/TZ)——语义精确但认知负担大**。TIMESTAMP_NTZ（无时区）、TIMESTAMP_LTZ（本地时区）、TIMESTAMP_TZ（带时区偏移量）。`TIMESTAMP_TYPE_MAPPING` 参数影响 TIMESTAMP 的默认映射。对比 BigQuery（四种时间类型）和 PG（TIMESTAMP/TIMESTAMPTZ 两种），Snowflake 的三种 TIMESTAMP 区分最精确但也最容易混淆。 |
| [JSON](../types/json/snowflake.md) | **VARIANT 类型原生存储 JSON，`:` 路径访问无需解析函数**——`v:user.name::STRING` 直接点号访问嵌套字段。FLATTEN 展开数组/对象。内部自动列化存储提升查询性能。对比 PG 的 JSONB+GIN 索引（索引能力更强）和 BigQuery 的 JSON 类型(2022+)，Snowflake 的 VARIANT 在查询语法优雅性上领先。 |
| [数值类型](../types/numeric/snowflake.md) | **NUMBER(38,N) 是默认数值类型——所有 INT/INTEGER/BIGINT 都是 NUMBER(38,0) 的别名**。FLOAT/DOUBLE 是 IEEE 754 浮点。NUMBER 精度最高 38 位，足以覆盖绝大多数场景。对比 BigQuery 的 INT64/NUMERIC/BIGNUMERIC（分离整数和定点数）和 ClickHouse 的 Int8-256（最细粒度），Snowflake 用统一的 NUMBER 类型简化了类型选择。 |
| [字符串类型](../types/string/snowflake.md) | **VARCHAR 默认最大 16MB，UTF-8 默认编码，COLLATE 支持**——VARCHAR 不指定长度时默认 16MB（实际按使用量存储）。COLLATION 支持大小写不敏感比较（如 `COLLATE 'en-ci'`）。对比 PG 的 TEXT 无长度限制和 BigQuery 的 STRING（无长度极简设计），Snowflake 的 VARCHAR 默认长度足够大且支持排序规则配置。 |
