# MaxCompute

**分类**: 阿里云大数据平台
**文件数**: 51 个 SQL 文件
**总行数**: 4134 行

> **关键人物**：[关涛](../docs/people/maxcompute-hologres.md)（MaxCompute 技术负责人）

## 概述与定位

MaxCompute（原 ODPS）是阿里云自研的 Serverless 大数据计算平台。在阿里内部每天处理 EB 级数据，是双十一数据分析的核心引擎。对外提供按量付费（SQL 扫描量）或预留 CU（计算单元）两种模式。

**定位**：不是通用数据库，而是**批处理为主的数据仓库**。与 BigQuery 定位最接近（Serverless + 按扫描计费），但生态绑定阿里云。

## 历史与演进

| 时间 | 事件 | 技术意义 |
|------|------|---------|
| 2010 | ODPS 在阿里内部启动 | 替代 Hadoop MapReduce 的自研计算平台 |
| 2014 | 作为阿里云服务对外开放 | 与 BigQuery (2010)、Redshift (2012) 同期的云数仓 |
| 2016 | 更名 MaxCompute，SQL 2.0 | 从 Hive 兼容方言升级为更接近标准 SQL |
| 2018 | 事务表 (Transactional Table) | Hive 风格引擎首次支持行级 UPDATE/DELETE |
| 2020 | Delta Table、Schema Evolution | 追赶 Delta Lake/Iceberg 的数据湖能力 |
| 2022 | MCQA 秒级交互查询 | 从纯批处理向交互式分析扩展 |
| 2024 | Lakehouse 集成、JSON 原生类型 | 存算分离、与 Hudi/Delta/Iceberg 互通 |

## 核心架构（对引擎开发者）

MaxCompute 的内部架构分为三层，每层都有值得学习的设计：

### 存储层：盘古 (Pangu) + AliORC

- **盘古**：阿里自研的分布式文件系统（类似 HDFS 但更适合云场景），是 MaxCompute 的存储底座
- **AliORC**：基于 Apache ORC 优化的列式文件格式，增加了：
  - C++ Arrow 内存格式支持（加速向量化计算）
  - 自适应字典编码（根据数据特征自动选择编码方式）
  - 异步预读 + I/O 模式管理（减少存储延迟影响）
  - 增强的谓词下推（在 I/O 层面跳过不需要的数据）
- **对引擎开发者的启示**：列式存储格式的性能差异主要来自编码策略和 I/O 优化，而非格式本身。AliORC 在 ORC 基础上的优化方向值得参考。

### 计算层：伏羲 (Fuxi) 调度 + 向量化引擎

- **伏羲**：阿里自研的分布式资源管理和任务调度系统（类似 YARN 但更轻量），负责将 SQL 编译后的 DAG 分配到计算节点
- **查询优化器**：基于 Apache Calcite 框架实现 RBO + CBO + HBO（History-Based Optimization）三层优化
  - HBO 利用历史执行统计信息优化后续查询——这是超越传统 CBO 的创新点
  - Adaptive Join：运行时在 Hash Join 和 Merge Join 之间动态切换
- **对引擎开发者的启示**：HBO（基于历史执行的优化）在反复执行的 ETL 场景中效果显著，值得投资。

### 元数据层：BigMeta

- 单集群管理上亿张表、上百亿分区和列的元数据
- **对引擎开发者的启示**：大规模元数据管理（千万级表）是大数据引擎的隐藏瓶颈，Hive Metastore 的单点问题在 MaxCompute 中通过自研 BigMeta 解决。

## SQL 方言设计分析

MaxCompute SQL 的设计处于 Hive SQL 和标准 SQL 之间，有几个值得注意的设计选择：

### 类型系统：1.0 vs 2.0

```sql
-- 1.0 类型系统（默认，Hive 兼容）：只有 BIGINT/DOUBLE/STRING/BOOLEAN/DATETIME
-- 2.0 类型系统（需开启）：增加 TINYINT/SMALLINT/INT/FLOAT/VARCHAR/CHAR/DECIMAL/TIMESTAMP/BINARY/ARRAY/MAP/STRUCT/JSON
SET odps.sql.type.system.odps2 = true;
```

**设计分析**：两套类型系统并存是历史包袱。1.0 的极简类型系统（所有整数都是 BIGINT，所有字符串都是 STRING）虽然简化了实现，但导致了：
- 从 MySQL/PostgreSQL 迁移时的类型映射困难
- 精度损失（所有整数占 8 字节，浪费存储）
- 2.0 修正了这个问题，但默认关闭以保持兼容性

### INSERT OVERWRITE：核心写入模式

```sql
-- 这是 MaxCompute 最重要的写入操作（不是 UPDATE/DELETE）
INSERT OVERWRITE TABLE orders PARTITION(dt='2024-01-15')
SELECT * FROM staging_orders WHERE dt = '2024-01-15';
```

**设计分析**：INSERT OVERWRITE 的语义是**原子性替换整个分区的数据**。这是 Hive 族引擎的核心设计——不做行级更新，而是重写整个分区。优势是实现简单（文件级替换）且幂等（重跑不会产生重复数据）。代价是无法做行级变更（2.0 事务表补充了这个能力）。

### 分区列不是普通列

```sql
CREATE TABLE orders (id BIGINT, amount DECIMAL(10,2))
PARTITIONED BY (dt STRING, region STRING);  -- dt 和 region 不在数据文件中！
```

**设计分析**：分区列值编码在目录路径中（`/orders/dt=2024-01-15/region=cn/`），不存储在数据文件中。这与 BigQuery/Snowflake 的分区设计不同——后者的分区列是普通列。MaxCompute 的设计来自 Hive，优势是分区裁剪可以在文件系统层面完成（不需要读取数据文件），代价是分区列和普通列的行为不一致。

### LIFECYCLE：存储治理的 DDL 化

```sql
CREATE TABLE logs (...) LIFECYCLE 90;  -- 90 天后自动删除
```

**设计分析**：将 TTL 作为表级 DDL 属性是 MaxCompute 的独创。对比其他引擎：
- ClickHouse：TTL 在表引擎中定义（`TTL timestamp + INTERVAL 90 DAY`）
- BigQuery：`partition_expiration_days` 选项
- Hive：无内置 LIFECYCLE 语法，仅有 `partition.retention.period` TBLPROPERTIES（分区级），整表 TTL 需外部调度
- MaxCompute 的 LIFECYCLE 对整个表或分区生效，是数据治理最简洁的方案

## 独特特色

| 特性 | 说明 | 对比其他引擎 |
|---|---|---|
| **LIFECYCLE** | `CREATE TABLE t (...) LIFECYCLE 90` | ClickHouse TTL、BigQuery partition_expiration 的简化版 |
| **事务表 + Time Travel** | ACID 表支持 `SELECT * FROM t TIMESTAMP AS OF '...'` | 类似 Delta Lake / Iceberg |
| **Tunnel 批量导入** | 高吞吐 SDK 级数据通道，支持断点续传 | 类似 BigQuery Storage Write API |
| **MCQA 加速** | 对小查询自动使用交互式引擎 | 类似 BigQuery BI Engine |
| **Quota Group** | 多租户计算资源配额隔离 | 类似 Snowflake Virtual Warehouse |
| **Script Mode** | 多语句脚本模式，支持变量和流程控制 | 类似 BigQuery Scripting |
| **JSON 列存** | JSON 类型数据自动推断公共 schema，按列式存储各字段。查询时自动列裁剪——只读取被引用的 JSON 字段。非公共 schema 部分用 BINARY 存储。需开启 `odps.sql.type.json.enable=true`。 | 类似 Snowflake VARIANT 自动列化、Hologres JSONB 列存 |
| **AliORC + 谓词下推** | 存储层自适应编码 + I/O 优化 | 超越标准 ORC 的读取性能 |

## 已知的设计不足与历史包袱

1. 两套类型系统并存
1.0 类型系统（BIGINT/STRING 为主）和 2.0 类型系统需要手动切换，导致同一项目内不同表可能使用不同类型系统，类型转换行为不一致。

2. SQL 兼容性差异大
- `INSERT INTO table VALUES(...)` 的 VALUES 子句在某些场景下行为与标准 SQL 不同
- `SELECT 1;` 不合法（需要 `SELECT 1 FROM dual;` 或使用 VALUES 语法）
- 字符串比较默认大小写敏感（与 MySQL 默认不敏感相反）
- 这些差异使得从 MySQL/PostgreSQL 迁移有较高学习成本

3. 普通表不支持 UPDATE/DELETE
只有事务表（Transactional Table）才支持行级变更。普通表（绝大多数存量表）只能用 INSERT OVERWRITE 整个分区来"更新"数据。对 CDC 和实时数据湖场景不友好。

4. 生态绑定阿里云
无法在其他云或本地部署。对比 Snowflake（多云）、BigQuery（GCP 专有但有 Omni）、Databricks（多云），MaxCompute 的供应商锁定更强。

5. 批处理延迟
传统作业模式下最快也需要数秒启动，不适合毫秒级交互查询。MCQA 在一定程度上缓解了这个问题，但仍不如 Hologres（同是阿里云产品，定位实时数仓）。

6. 存储过程支持弱
Script Mode 提供了变量和流程控制，但远不如 PL/SQL 或 PL/pgSQL 强大。复杂的 ETL 流程通常需要依赖 DataWorks 调度平台。

## 与同类引擎的关键对比

| 维度 | MaxCompute | BigQuery | Snowflake | Hive | Databricks |
|------|-----------|---------|-----------|------|-----------|
| 部署模式 | 阿里云专有 | GCP 专有 | 多云 | 开源 | 多云 |
| 计费模式 | CU 预留/按量 | 按扫描量 | 按 Warehouse 时间 | 集群资源 | DBU |
| 存储格式 | AliORC | Capacitor | 微分区 | ORC/Parquet | Delta Lake |
| 行级 UPDATE | 事务表(2018+) | 支持 | 支持 | ACID 表(0.14+) | Delta(2017+) |
| LIFECYCLE/TTL | ✅ 原生 | ✅ partition_expiration | ❌ 需手动 | ❌ 需调度 | ❌ 需手动 |
| 交互式查询 | MCQA | BI Engine | 默认交互式 | LLAP | Photon |
| 元数据规模 | 亿级表 | 大规模 | 大规模 | MetaStore 瓶颈 | Unity Catalog |

## 对引擎开发者的参考价值

1. LIFECYCLE（TTL）作为 DDL 属性
将数据过期策略声明在建表语句中，是目前最简洁的存储治理方案。避免了维护外部定时任务的运维成本。建议新引擎在 CREATE TABLE 语法中原生支持 TTL/LIFECYCLE。

2. HBO（History-Based Optimization）
基于历史执行统计优化后续查询，是对 CBO 的有力补充。在 ETL 管线中同一查询反复执行，HBO 可以利用上一次的 runtime statistics 生成更优的执行计划。

3. 两套类型系统的教训
类型系统一旦发布就极难更改。MaxCompute 1.0 的极简类型（一切整数都是 BIGINT）简化了早期实现，但 2.0 需要引入第二套类型系统来修正，增加了长期维护成本。**新引擎应从第一天就使用完整的类型系统**。

4. 事务表的增量实现
在 Hive 风格的不可变文件之上叠加事务能力（delta file + compaction），是数据湖引擎事务化的通用模式。MaxCompute、Hive ACID、Delta Lake、Iceberg 都采用了类似架构。

5. 分区与数据治理的深度绑定
MaxCompute 的分区不只是查询优化手段，还是数据治理的核心单元——LIFECYCLE、INSERT OVERWRITE、权限控制都以分区为粒度。这种"分区即管理单元"的设计在大数据场景中非常实用。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/maxcompute.md) | **分区=目录是核心设计**——分区列不在数据文件中，编码在目录路径中（继承 Hive）。LIFECYCLE DDL 化是独创（对比 Hive 无内置 TTL）。两套类型系统(1.0/2.0)并存是历史包袱。事务表(2.0+)才支持 PK 声明和 UPDATE/DELETE。 |
| [改表](../ddl/alter-table/maxcompute.md) | **ADD COLUMNS 追加式，不支持 MODIFY COLUMN TYPE**——Schema 变更保守，复杂类型变更需 CTAS 重建表。分区增删是最常用的 ALTER 操作。对比 Snowflake（同样不支持改列类型）和 Hive（ADD/REPLACE COLUMNS），MaxCompute 的限制在 Hive 系引擎中属于典型。 |
| [索引](../ddl/indexes/maxcompute.md) | **无任何索引（纯批处理引擎）**——完全依赖分区裁剪 + AliORC 谓词下推实现数据跳过。对比 BigQuery（同样无索引但有 CLUSTER BY）和 ClickHouse（稀疏索引+跳数索引），MaxCompute 是物理优化手段最少的引擎之一。MCQA 交互查询模式部分弥补了缺陷。 |
| [约束](../ddl/constraints/maxcompute.md) | **PK 仅 2.0+ 事务表可声明，且 NOT ENFORCED**——无 FK、无 CHECK、无 UNIQUE 约束。普通表（绝大多数存量表）完全无约束能力。对比 BigQuery/Snowflake（PK/FK 声明但不强制）和 Hive（3.0+ 类似），MaxCompute 的约束最为简陋。 |
| [视图](../ddl/views/maxcompute.md) | **普通 VIEW 标准支持，物化视图 2.0+ 引入**——物化视图支持自动增量刷新和查询改写。对比 BigQuery（物化视图自动刷新+智能改写最成熟）和 Hive（3.0+ 物化视图），MaxCompute 的物化视图在阿里云生态中与 DataWorks 调度深度集成。 |
| [序列与自增](../ddl/sequences/maxcompute.md) | **无 SEQUENCE/AUTO_INCREMENT**——批处理引擎无法维护全局递增序列。推荐 UUID() 或 ROW_NUMBER() OVER() 生成代理键。对比 BigQuery（同样无自增，推荐 GENERATE_UUID）和 Snowflake（AUTOINCREMENT 不保证连续），大数据引擎普遍放弃自增语义。 |
| [数据库/Schema/用户](../ddl/users-databases/maxcompute.md) | **Project→Schema(3.0+)→Table 三级命名空间**——Project 是资源隔离和计费的基本单元（类似 BigQuery 的 Project.Dataset）。权限基于阿里云 RAM + MaxCompute ACL + Label Security 三层体系。对比 Snowflake 的 Database.Schema.Object 和 Hive 的 Database=目录，MaxCompute 的 Project 隔离粒度更粗。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/maxcompute.md) | **Script Mode(2.0+) 支持多语句脚本**——类似 BigQuery Scripting，支持变量声明、IF/LOOP 流程控制。不是传统存储过程，而是提交一个脚本作业整体执行。对比 Hive（无任何脚本能力）和 Snowflake（JS/SQL/Python 存储过程），MaxCompute 的 Script Mode 介于二者之间。 |
| [错误处理](../advanced/error-handling/maxcompute.md) | **无过程式错误处理，作业级别全部失败或全部成功**——失败作业需在 DataWorks 调度层配置重试策略。Script Mode 也没有 TRY/CATCH 语义。对比 BigQuery（BEGIN...EXCEPTION）和 Snowflake（EXCEPTION 块），MaxCompute 的错误处理最为原始。 |
| [执行计划](../advanced/explain/maxcompute.md) | **EXPLAIN 展示 Fuxi DAG 执行计划**——可查看 Map/Reduce/Join 阶段划分和数据分布。HBO（History-Based Optimization）利用历史执行统计优化后续查询——这是超越传统 CBO 的创新。对比 Spark 的 EXPLAIN EXTENDED 和 BigQuery 的 Console Execution Details，MaxCompute 的 HBO 在反复执行的 ETL 场景中优势明显。 |
| [锁机制](../advanced/locking/maxcompute.md) | **无行级锁（批处理引擎），表/分区级并发控制**——同一分区不能同时被多个作业写入。事务表(2.0+)通过 MVCC 实现读写隔离。对比 BigQuery（DML 配额限制并发）和 ClickHouse（Part 级原子写入），MaxCompute 的并发模型以分区为粒度。 |
| [分区](../advanced/partitioning/maxcompute.md) | **PARTITIONED BY 继承 Hive，分区是成本控制的核心**——分区裁剪直接减少扫描量（按量计费模式下=省钱）。支持多级分区（如 dt/hour 二级），动态分区插入自动创建分区目录。对比 BigQuery（分区列是普通列）和 Snowflake（自动微分区无需管理），MaxCompute 的分区需要用户显式管理。 |
| [权限](../advanced/permissions/maxcompute.md) | **RAM+ACL+Policy 三层权限，Label Security 实现列级安全**——RAM 控制云账号访问，ACL 控制表/分区级权限，Label Security 为列设置安全等级（L0-L4）。对比 BigQuery（完全基于 GCP IAM）和 Snowflake（RBAC+DAC），MaxCompute 的 Label Security 列级控制在大数据引擎中较为独特。 |
| [存储过程](../advanced/stored-procedures/maxcompute.md) | **Script Mode 脚本替代传统存储过程**——支持变量、IF/LOOP 控制流，但无参数化过程、无包（Package）、无游标。复杂 ETL 通常依赖 DataWorks 调度编排多个脚本。对比 Snowflake（多语言存储过程最强）和 Hive（仅 UDF/UDAF/UDTF），MaxCompute 的过程式能力有限。 |
| [临时表](../advanced/temp-tables/maxcompute.md) | **TEMPORARY TABLE 会话级，VOLATILE TABLE 作业级**——VOLATILE TABLE 在单个作业内有效，作业结束自动清理。对比 BigQuery（_SESSION.table_name 引用临时表）和 Snowflake（TEMPORARY+TRANSIENT 不同 Time Travel），MaxCompute 的 VOLATILE TABLE 是独有的作业级临时表设计。 |
| [事务](../advanced/transactions/maxcompute.md) | **ACID 事务(2.0+) 基于 Delta 文件 + Compaction**——事务表支持 Time Travel（`SELECT ... AS OF TIMESTAMP`）。非事务表（绝大多数存量表）只有 INSERT OVERWRITE 的分区级原子性。对比 Delta Lake/Iceberg 的事务模型和 BigQuery 的多语句事务，MaxCompute 在 Hive 系引擎中较早实现了行级事务。 |
| [触发器](../advanced/triggers/maxcompute.md) | **不支持触发器**——批处理引擎无事件驱动机制。替代方案：DataWorks 调度定时触发、MaxCompute 物化视图增量刷新。对比 ClickHouse（物化视图=INSERT 触发器）和 Snowflake（Streams+Tasks），MaxCompute 依赖外部调度系统。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/maxcompute.md) | **DELETE 仅 ACID 事务表(2.0+)支持，普通表只能 DROP PARTITION**——普通表删除数据的唯一方式是丢弃整个分区然后重写。这是 Hive 系引擎的根本限制：不可变文件不支持行级删除。对比 BigQuery（DELETE 必须带 WHERE，重写整个分区）和 ClickHouse（Lightweight Delete 22.8+），MaxCompute 对普通表的限制最严格。 |
| [插入](../dml/insert/maxcompute.md) | **INSERT OVERWRITE 是核心写入模式（非 INSERT INTO）**——原子性替换整个分区数据，天然幂等（重跑不产生重复）。Tunnel SDK 提供高吞吐批量导入通道，支持断点续传。对比 BigQuery（批量加载免费，DML 计费）和 Hive（INSERT OVERWRITE 语义相同），MaxCompute 的 Tunnel 是专有的高性能数据通道。 |
| [更新](../dml/update/maxcompute.md) | **UPDATE 仅 ACID 事务表(2.0+)支持，普通表完全不支持行级更新**——普通表（绝大多数存量表）只能用 INSERT OVERWRITE 重写整个分区来"更新"。这对 CDC 和实时数据湖场景不友好。对比 BigQuery/Snowflake（UPDATE 标准但重写微分区）和 Hive ACID（3.0+ 类似限制），MaxCompute 需要表级别升级为事务表才能行级变更。 |
| [Upsert](../dml/upsert/maxcompute.md) | **MERGE INTO 仅 ACID 事务表(2.0+)，普通表用 INSERT OVERWRITE 全量替代**——MERGE 语法标准（WHEN MATCHED/NOT MATCHED），但仅限事务表。普通表的"Upsert"只能全分区重写：先 JOIN 新旧数据再 INSERT OVERWRITE。对比 BigQuery（MERGE 是唯一 Upsert 方案）和 ClickHouse（ReplacingMergeTree 合并时去重），MaxCompute 的两种表类型对 Upsert 的体验截然不同。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/maxcompute.md) | **GROUPING SETS/CUBE/ROLLUP 完整，COLLECT_LIST/COLLECT_SET 收集数组**——继承 Hive 的多维聚合能力。PERCENTILE_APPROX 近似百分位数用于大数据集。对比 BigQuery 的 APPROX_COUNT_DISTINCT（HyperLogLog）和 ClickHouse 的 -If/-State 组合后缀，MaxCompute 的聚合函数集更接近 Hive 标准。 |
| [条件函数](../functions/conditional/maxcompute.md) | **IF/CASE/COALESCE/NVL 继承 Hive 兼容**——NVL 是 Oracle 风格的 NULL 替换（Hive 引入），标准 SQL 推荐 COALESCE。2.0 类型系统下条件函数的类型推导更严格。对比 BigQuery 的 SAFE_ 前缀（行级错误安全）和 Snowflake 的 IFF/DECODE，MaxCompute 保持 Hive 函数集不引入独有扩展。 |
| [日期函数](../functions/date-functions/maxcompute.md) | **DATEADD/DATEDIFF/DATE_FORMAT 继承 Hive 但有扩展**——TO_DATE/TO_CHAR 是 MaxCompute 独有的日期转换函数对。1.0 类型系统只有 DATETIME（无 DATE/TIMESTAMP 区分），2.0 才引入完整日期类型。对比 BigQuery 的四种时间类型严格区分和 Snowflake 的 DATE_TRUNC，MaxCompute 的日期函数在两套类型系统间行为不一致是痛点。 |
| [数学函数](../functions/math-functions/maxcompute.md) | **完整数学函数集（ABS/CEIL/FLOOR/ROUND/POWER 等）**——与 Hive 兼容但增加了部分函数（如 LOG2/LN）。除零行为：1.0 类型系统返回 NULL，2.0 类型系统可配置是否报错。对比 BigQuery 的 SAFE_DIVIDE（独有安全除法）和 PG 的除零报错，MaxCompute 的行为取决于类型系统版本。 |
| [字符串函数](../functions/string-functions/maxcompute.md) | **CONCAT/SUBSTR/REGEXP_EXTRACT 继承 Hive**——SPLIT 返回 ARRAY，配合 LATERAL VIEW EXPLODE 展开为行。REGEXP 基于 Java 正则引擎（支持回溯，对比 BigQuery 的 re2 线性时间引擎）。对比 Snowflake 的 SPLIT_PART（按位置提取）和 PG 的 string_to_array，MaxCompute 的字符串处理完全 Hive 风格。 |
| [类型转换](../functions/type-conversion/maxcompute.md) | **CAST 标准，TRY_CAST(2.0+) 安全转换——失败返回 NULL 而非报错**。TRY_CAST 是 MaxCompute 对 Hive 的重要扩展（Hive 无此函数）。1.0 类型系统的隐式转换极为宽松（一切变 BIGINT/DOUBLE/STRING），2.0 更严格。对比 BigQuery 的 SAFE_CAST 和 Snowflake 的 TRY_CAST，MaxCompute 的安全转换能力在 2.0 后才追上主流。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/maxcompute.md) | **WITH 标准 + 递归 CTE 支持**——递归 CTE 有迭代深度限制。CTE 是否物化由优化器自动决策。对比 Hive（3.1+ 才支持递归 CTE）和 BigQuery（同样自动决策物化），MaxCompute 的 CTE 能力较为完整。 |
| [全文搜索](../query/full-text-search/maxcompute.md) | **无全文搜索能力**——无倒排索引、无 SEARCH 函数。只能用 LIKE/REGEXP 模糊匹配（全表扫描）。对比 BigQuery（SEARCH INDEX 2023+）和 Doris（倒排索引 2.0+），MaxCompute 在文本检索场景需借助外部搜索引擎（如 OpenSearch）。 |
| [连接查询](../query/joins/maxcompute.md) | **Map/Reduce/Broadcast JOIN 继承 Hive，MAPJOIN Hint 强制小表广播**——`/*+ MAPJOIN(small) */` 是最常用的性能优化手段。HBO 优化器可根据历史执行统计自动选择 JOIN 策略。对比 Spark 的 AQE 运行时自动转换 Broadcast JOIN 和 BigQuery 的全自动 JOIN 策略，MaxCompute 更依赖用户 Hint 但 HBO 提供了自动化路径。 |
| [分页](../query/pagination/maxcompute.md) | **LIMIT + ORDER BY，无 OFFSET 支持**——批处理引擎定位下分页需求罕见。大结果集建议导出到 OSS 或通过 Tunnel 下载。对比 BigQuery（LIMIT/OFFSET 标准但按扫描量计费不受 OFFSET 影响）和 Snowflake（LIMIT/OFFSET 完整），MaxCompute 的分页能力是大数据引擎中最简的。 |
| [行列转换](../query/pivot-unpivot/maxcompute.md) | **LATERAL VIEW EXPLODE 继承 Hive，无 PIVOT/UNPIVOT 语法**——列转行用 LATERAL VIEW EXPLODE(array_col)，行转列只能用 CASE+GROUP BY 手动实现。对比 BigQuery/Snowflake 的原生 PIVOT（2021+）和 Spark 的 PIVOT/UNPIVOT（3.4+），MaxCompute 在行列转换上缺乏语法糖。 |
| [集合操作](../query/set-operations/maxcompute.md) | **UNION ALL/DISTINCT、INTERSECT、EXCEPT 完整支持**——语义与标准 SQL 一致。UNION DISTINCT 是默认行为（与 SQL 标准一致）。对比 ClickHouse（UNION 默认 ALL，与标准相反）和 Hive（2.0+ 才完整），MaxCompute 的集合操作标准完备。 |
| [子查询](../query/subquery/maxcompute.md) | **IN/EXISTS 子查询完整支持，关联子查询可优化**——优化器可将部分关联子查询转为 Semi Join/Anti Join。对比 MySQL 5.x 的子查询性能问题和 BigQuery 的善于自动转 JOIN，MaxCompute 的子查询优化在 HBO 加持下效果良好。 |
| [窗口函数](../query/window-functions/maxcompute.md) | **完整窗口函数继承 Hive，ROWS/RANGE 帧支持**——ROW_NUMBER/RANK/DENSE_RANK/LAG/LEAD/SUM OVER 等全部支持。无 QUALIFY 子句（需子查询包装去重/TopN）。对比 BigQuery/Snowflake 的 QUALIFY（最简去重写法）和 ClickHouse（21.1+ 才支持窗口函数），MaxCompute 的窗口函数成熟但缺乏现代扩展。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/maxcompute.md) | **无 generate_series 函数，需辅助日期表或 LATERAL VIEW POSEXPLODE**——批处理场景下通常预建日期维表 LEFT JOIN 填充。对比 BigQuery 的 GENERATE_DATE_ARRAY+UNNEST（一行搞定）和 Spark 的 sequence()+explode()，MaxCompute 的日期序列生成最为繁琐。 |
| [去重](../scenarios/deduplication/maxcompute.md) | **ROW_NUMBER+窗口函数标准去重模式**——`WHERE rn=1` 子查询包装是唯一方案。大数据量下去重性能依赖分区裁剪和 AliORC 谓词下推。对比 BigQuery/Snowflake 的 QUALIFY（无需子查询）和 ClickHouse 的 ReplacingMergeTree（存储层自动去重），MaxCompute 的去重写法标准但冗长。 |
| [区间检测](../scenarios/gap-detection/maxcompute.md) | **LAG/LEAD 窗口函数检测连续性**——标准方案，无独有优化。批处理场景下全量扫描分区数据。对比 ClickHouse 的 WITH FILL（自动填充缺失行）和 PG 的 generate_series+LEFT JOIN，MaxCompute 的区间检测方案通用但无特殊语法支持。 |
| [层级查询](../scenarios/hierarchical-query/maxcompute.md) | **递归 CTE 支持层级遍历**——有迭代深度限制。无 Oracle 的 CONNECT BY 语法。对比 Hive（3.1+ 才支持递归 CTE）和 Oracle/达梦（CONNECT BY START WITH），MaxCompute 采用标准 SQL 递归 CTE 方案。 |
| [JSON 展开](../scenarios/json-flatten/maxcompute.md) | **GET_JSON_OBJECT/JSON_EXTRACT 继承 Hive 路径查询**——JSON 列存(2024+)自动推断公共 Schema 按列式存储，查询时自动列裁剪。对比 Snowflake 的 LATERAL FLATTEN（最优雅）和 BigQuery 的 JSON_QUERY_ARRAY+UNNEST，MaxCompute 的 JSON 列存是其独有的性能优化。 |
| [迁移速查](../scenarios/migration-cheatsheet/maxcompute.md) | **Hive 兼容是基础，但三大差异需注意**——两套类型系统(1.0/2.0)的切换、LIFECYCLE 独有语义、事务表 vs 普通表的能力差异。从 MySQL/PG 迁移学习成本高（INSERT OVERWRITE 思维、分区=目录模型）。对比 BigQuery（INT64/STRING 独特类型命名）和 Snowflake（VARIANT 半结构化设计差异），MaxCompute 的迁移复杂度主要在 Hive 范式的理解。 |
| [TopN 查询](../scenarios/ranking-top-n/maxcompute.md) | **ROW_NUMBER+子查询+LIMIT 标准模式**——无 QUALIFY 子句，必须用子查询包装窗口函数过滤。对比 BigQuery/Snowflake 的 QUALIFY（单行表达式）和 ClickHouse 的 LIMIT BY（每组限行独有语法），MaxCompute 的 TopN 写法标准但不够简洁。 |
| [累计求和](../scenarios/running-total/maxcompute.md) | **SUM() OVER(ORDER BY ...) 标准窗口累计**——Fuxi 引擎自动并行化窗口计算，大数据量下性能稳定。对比 BigQuery（Slot 自动扩展）和 ClickHouse（runningAccumulate 状态函数），MaxCompute 的累计计算依赖批处理调度。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/maxcompute.md) | **MERGE INTO(ACID 事务表) 或 INSERT OVERWRITE(普通表) 实现 SCD**——事务表支持标准 MERGE 的 WHEN MATCHED/NOT MATCHED 语法实现 SCD Type 1/2。普通表只能全分区重写，SCD 逻辑在 SQL 中实现但效率低。对比 BigQuery 的 MERGE+Time Travel 和 Snowflake 的 MERGE+Streams，MaxCompute 的事务表方案最接近标准。 |
| [字符串拆分](../scenarios/string-split-to-rows/maxcompute.md) | **SPLIT+LATERAL VIEW EXPLODE 继承 Hive 独有写法**——`LATERAL VIEW EXPLODE(SPLIT(str, ',')) t AS val` 是标准模式。对比 BigQuery 的 SPLIT+UNNEST（更简洁）和 Snowflake 的 SPLIT_TO_TABLE（一步到位），MaxCompute 的 LATERAL VIEW EXPLODE 语法更冗长但语义清晰。 |
| [窗口分析](../scenarios/window-analytics/maxcompute.md) | **完整窗口函数继承 Hive，移动平均/同环比/占比计算均支持**——ROWS/RANGE 帧完整。无 QUALIFY 过滤（需子查询）、无 WINDOW 命名子句。对比 BigQuery/Snowflake（QUALIFY+WINDOW 命名子句最强）和 Hive（功能相同），MaxCompute 的窗口分析成熟但缺乏现代语法扩展。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/maxcompute.md) | **ARRAY/MAP/STRUCT 原生支持（需 2.0 类型系统）**——1.0 类型系统下复合类型不可用，是两套类型系统最大的功能差异之一。LATERAL VIEW EXPLODE 展开 ARRAY/MAP。对比 BigQuery 的 STRUCT/ARRAY 一等公民（无需开关）和 Snowflake 的 VARIANT（半结构化），MaxCompute 的复合类型需要显式开启 2.0 类型系统。 |
| [日期时间](../types/datetime/maxcompute.md) | **1.0 仅 DATETIME 一种类型，2.0 引入 DATE/TIMESTAMP 完整体系**——1.0 的 DATETIME 语义模糊（既非纯日期也非时间戳），2.0 才与标准 SQL 对齐。对比 BigQuery 的四种时间类型严格区分和 Snowflake 的三种 TIMESTAMP，MaxCompute 的日期类型在 2.0 后才达到主流水平。 |
| [JSON](../types/json/maxcompute.md) | **GET_JSON_OBJECT 路径查询（继承 Hive），JSON 列存(2024+)独创**——JSON 列存自动推断公共 Schema 按列式存储各字段，查询时只读取被引用字段（自动列裁剪）。对比 Snowflake 的 VARIANT 自动列化和 ClickHouse 的实验性 JSON 类型，MaxCompute 的 JSON 列存是最新的半结构化优化方案。 |
| [数值类型](../types/numeric/maxcompute.md) | **2.0 类型系统才有完整数值类型（TINYINT-BIGINT/FLOAT/DOUBLE/DECIMAL）**——1.0 仅 BIGINT 和 DOUBLE 两种数值类型（一切整数=BIGINT），导致精度浪费和存储膨胀。对比 BigQuery 的 INT64 单一整数类型（极简但够用）和 ClickHouse 的 Int8-256/UInt8-256（最丰富），MaxCompute 的类型系统演进是教训。 |
| [字符串类型](../types/string/maxcompute.md) | **STRING 无长度限制（继承 Hive），VARCHAR(n)/CHAR(n) 需 2.0 类型系统**——1.0 下所有文本都是 STRING，无长度约束。2.0 引入 VARCHAR/CHAR 但实践中较少使用（STRING 已成惯例）。对比 BigQuery 的 STRING（无长度限制极简设计）和 PG 的 VARCHAR(n)/TEXT，MaxCompute 的 STRING 设计在大数据场景中反而是优势。 |
