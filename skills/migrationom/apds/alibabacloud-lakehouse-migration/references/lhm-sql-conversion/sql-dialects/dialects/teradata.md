# Teradata

**分类**: 老牌 MPP 数仓
**文件数**: 51 个 SQL 文件
**总行数**: 4474 行

## 概述与定位

Teradata 是数据仓库领域的先驱和老牌领导者，自 1979 年以来专注于大规模并行处理（MPP）数据仓库。其核心理念是"一切靠 SQL"——通过强大的优化器和数据分布策略在 TB/PB 级数据上实现高性能分析查询。Teradata 在全球大型企业（银行、电信、零售、航空）中拥有深厚的客户基础，许多 SQL 分析特性（如 QUALIFY 子句）源自 Teradata 的首创。

## 历史与演进

- **1979 年**：Teradata Corporation 成立，是最早的 MPP 关系数据库公司之一。
- **1984 年**：Teradata DBC/1012 发布，是第一款商用并行数据库系统。
- **1999 年**：Teradata V2R3 引入 QUALIFY 子句，比 SQL 标准的类似功能早了十余年。
- **2007 年**：从 NCR 独立上市，引入 Teradata Active Data Warehousing 概念。
- **2010 年**：引入列分区（Column Partitioning）、时态表（Temporal Tables）与 PERIOD 数据类型。
- **2016 年**：Teradata 16.x 引入 QueryGrid（跨平台联邦查询）、JSON 数据类型。
- **2019 年**：Vantage 品牌发布，统一数据仓库、数据湖和分析功能在一个平台上。
- **2023-2025 年**：VantageCloud Lake（云原生对象存储架构）、ClearScape Analytics（内置 AI/ML 函数）、增强开放格式支持。

## 核心设计思路

1. **PRIMARY INDEX 分布**：每张表必须有 Primary Index（PI），数据通过 PI 的哈希值均匀分布到 AMP（Access Module Processor）节点上，PI 的选择是 Teradata 调优的核心。
2. **Shared-Nothing MPP**：每个 AMP 拥有独立的 CPU、内存和磁盘，完全不共享，通过 BYNET 高速互联网络交换数据。
3. **优化器驱动**：Teradata 优化器以其对复杂查询（多表 JOIN、嵌套子查询、窗口函数）的高质量计划生成著称。
4. **工作负载管理（TASM）**：Teradata Active System Management 提供细粒度的工作负载分类、优先级和资源分配。

## 独特特色

| 特性 | 说明 |
|---|---|
| **PRIMARY INDEX** | `CREATE TABLE t (...) PRIMARY INDEX (col)` 控制数据在 AMP 上的哈希分布，是性能调优的第一要素。 |
| **QUALIFY（首创）** | `QUALIFY ROW_NUMBER() OVER(...) = 1` 直接过滤窗口函数结果，无需嵌套子查询——Teradata 最早实现此语法。 |
| **COLLECT STATISTICS** | 收集列和索引的详细统计信息，Teradata 优化器高度依赖统计信息来选择最优执行计划。 |
| **PERIOD 类型** | 原生的时间区间数据类型 `PERIOD(DATE, DATE)` 和 `PERIOD(TIMESTAMP, TIMESTAMP)`，支持区间交集、包含等操作。 |
| **时态表** | 支持 VALIDTIME（业务时间）和 TRANSACTIONTIME（系统时间）双时态表，原生支持 `AS OF`、`BETWEEN...AND` 时态查询。 |
| **NORMALIZE** | `NORMALIZE` 语句可自动合并重叠或相邻的 PERIOD 区间，是 Teradata 独有的区间操作语法。 |
| **QueryGrid** | 跨平台联邦查询框架，可在 Teradata SQL 中直接查询 Hadoop/Spark/Oracle/Azure 等外部数据源。 |

## 已知不足

- **许可成本极高**：Teradata 是市场上最昂贵的数仓解决方案之一，按 TCore（Teradata Core）或 TB 计费。
- **供应商锁定严重**：PI 分布模型、QUALIFY、PERIOD 等特有语法使迁移到其他平台的成本很高。
- **云原生步伐偏慢**：虽然推出了 VantageCloud，但在弹性扩缩容和 Serverless 体验上落后于 Snowflake/Databricks。
- **学习曲线陡峭**：PI 选择、JOIN 策略（Product Join、Merge Join、Hash Join）、空间管理对初学者要求较高。
- **社区和生态薄弱**：闭源产品，技术资料主要来自 Teradata 官方，中文社区和第三方工具生态明显不足。
- **JSON/半结构化支持较晚**：原生 JSON 类型和 JSON 函数的引入落后于竞品。

## 对引擎开发者的参考价值

- **QUALIFY 子句设计**：将窗口函数结果过滤提升为一等子句（与 WHERE/HAVING 平级），消除了嵌套子查询的需要，对 SQL 方言设计有重要启发。
- **PRIMARY INDEX 哈希分布**：将数据分布策略作为 DDL 的核心部分（而非可选属性），展示了数据放置对查询性能的决定性影响。
- **PERIOD 类型与 NORMALIZE**：原生的时间区间类型和区间合并操作，对时态数据建模和时序数据库的类型系统有直接参考。
- **COLLECT STATISTICS 模型**：精细化的统计信息收集（支持列组合、采样统计、直方图）对基于成本的优化器的统计子系统设计有参考。
- **TASM 工作负载管理**：基于规则的查询分类 + 优先级队列 + 资源限制的多维度工作负载管理，对多租户引擎的调度设计有参考价值。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/teradata.md) | **MPP 架构先驱——PRIMARY INDEX 决定数据哈希分布**。每张表必须有 PI，数据通过 PI 哈希值均匀分布到 AMP 节点。SET 表不允许重复行（Teradata 独有），MULTISET 允许重复。对比 Redshift DISTKEY 和 Greenplum DISTRIBUTED BY——Teradata 的 PI 概念影响了所有后来的 MPP 设计。 |
| [改表](../ddl/alter-table/teradata.md) | **ALTER 在线变更——但 PRIMARY INDEX 变更需重建表**（全表数据重分布）。对比 PG DDL 事务性可回滚和 Greenplum 分布键变更同样需重建——PI 选择需建表时仔细规划。 |
| [索引](../ddl/indexes/teradata.md) | **PI 决定数据分布+SI（Secondary Index）加速非 PI 查询+Join Index 预物化 JOIN 结果**。Join Index 是 Teradata 独有的物化连接索引——预先计算并存储 JOIN 结果加速常用查询。对比 PG B-tree/GIN 和 BigQuery 分区+聚集——Teradata 的 Join Index 是独特设计。 |
| [约束](../ddl/constraints/teradata.md) | **PK/FK/UNIQUE/CHECK 约束完整执行——NOT NULL 是默认**（与其他数据库默认 NULL 相反）。这是 Teradata 的独有行为需特别注意。对比 PG/MySQL/Oracle 默认允许 NULL——Teradata 的 NOT NULL 默认是迁移时的隐性差异。 |
| [视图](../ddl/views/teradata.md) | **Join Index 物化连接视图是 Teradata 独有设计**——预计算 JOIN 结果持久化存储，优化器自动路由查询。Hash Index 加速非 PI 等值查询。对比 Oracle 物化视图 Query Rewrite 和 SQL Server Indexed View——Join Index 粒度更细。 |
| [序列与自增](../ddl/sequences/teradata.md) | **IDENTITY 自增列——无独立 SEQUENCE 对象**。对比 PG IDENTITY/SEQUENCE 和 MySQL AUTO_INCREMENT——Teradata 自增功能基础。 |
| [数据库/Schema/用户](../ddl/users-databases/teradata.md) | **Database=Schema=权限容器——三者是同一概念**。Space 配额管理控制每个数据库的存储空间。对比 PG Database.Schema 二级和 BigQuery Project.Dataset.Table 三级——Teradata 的命名空间模型独特。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/teradata.md) | **CALL DBC.SYSEXECSQL 或应用层 BTEQ/TPT 执行动态 SQL**。对比 PG EXECUTE format() 和 Oracle EXECUTE IMMEDIATE——Teradata 动态 SQL 偏向外部工具。 |
| [错误处理](../advanced/error-handling/teradata.md) | **HANDLER 声明+SIGNAL/RESIGNAL 标准错误处理**。对比 PG EXCEPTION WHEN 和 Oracle 命名异常——Teradata 错误处理符合 SQL 标准。 |
| [执行计划](../advanced/explain/teradata.md) | **EXPLAIN 输出详尽英文描述（可读性极强）**——每个步骤用自然语言描述执行策略。Query Log 提供历史查询性能分析。对比 PG EXPLAIN ANALYZE 和 BigQuery Console——Teradata 的英文描述式 EXPLAIN 在业界独特。 |
| [锁机制](../advanced/locking/teradata.md) | **行级哈希锁+LOCKING 子句显式指定（独有语法）**——`LOCKING TABLE t FOR ACCESS` 显式指定锁级别。对比 PG MVCC 和 SQL Server WITH(NOLOCK)——Teradata 的 LOCKING 子句是更正式的锁控制语法。 |
| [分区](../advanced/partitioning/teradata.md) | **PPI（Partitioned PI）+RANGE_N/CASE_N 函数分区**——PPI 在 PI 分布基础上再按分区键分片，RANGE_N 函数定义范围分区边界。对比 PG 声明式分区和 Oracle INTERVAL 分区——Teradata 的 PPI 将分布和分区结合的设计独特。 |
| [权限](../advanced/permissions/teradata.md) | **数据库级权限继承+Profile 管理+Access Logging**——权限自动从父数据库继承到子对象。Access Logging 记录所有数据访问审计。对比 PG RBAC 和 Oracle VPD——Teradata 的权限继承和审计适合合规性要求高的场景。 |
| [存储过程](../advanced/stored-procedures/teradata.md) | **SPL（Stored Procedure Language）——编译式存储过程**。不同于 PG/Oracle 的解释式过程，SPL 编译后执行效率更高。对比 PG PL/pgSQL（解释式）和 Oracle PL/SQL（编译式）——Teradata SPL 是编译式的。 |
| [临时表](../advanced/temp-tables/teradata.md) | **VOLATILE（会话级）/GLOBAL TEMPORARY 表**——VOLATILE 表无需预定义结构（对比 Oracle GTT 需预定义）。对比 PG CREATE TEMP TABLE 和 SQL Server #temp——Teradata 的 VOLATILE 表最灵活。 |
| [事务](../advanced/transactions/teradata.md) | **ANSI/Teradata 两种事务模式**——ANSI 模式：每条语句自动提交；Teradata 模式：BT(Begin Transaction)/ET(End Transaction) 显式事务。对比 PG/MySQL 的 BEGIN/COMMIT 和 Oracle 无显式 BEGIN——Teradata 的双模式事务是独有设计。 |
| [触发器](../advanced/triggers/teradata.md) | **BEFORE/AFTER 行级+语句级触发器完整**。对比 PG 完整触发器和 MySQL 仅行级——Teradata 触发器功能完整。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/teradata.md) | **DELETE/DEL 标准+FastPath DELETE 批量高效**——DEL 是 DELETE 的 Teradata 缩写。对比 PG DELETE...RETURNING 和 Oracle Flashback——Teradata DELETE 批量性能优异。 |
| [插入](../dml/insert/teradata.md) | **INSERT/INS 标准+FastLoad/TPT 批量导入**——TPT（Teradata Parallel Transporter）是企业级并行数据加载工具。对比 PG COPY 和 Redshift COPY from S3——TPT 是 Teradata 数据管道的核心工具。 |
| [更新](../dml/update/teradata.md) | **UPDATE/UPD 标准+MERGE 支持**——UPD 是 UPDATE 的缩写。对比 PG UPDATE...FROM 和 Oracle MERGE——Teradata UPDATE 功能完整。 |
| [Upsert](../dml/upsert/teradata.md) | **MERGE 标准实现+UPDATE...ELSE INSERT（独有 Upsert 语法）**——`UPDATE t SET... WHERE...; .IF ACTIVITYCOUNT=0 THEN INSERT INTO t...;` 是 Teradata 独有的条件插入模式。对比 PG ON CONFLICT 和 Oracle MERGE——Teradata 的 UPDATE...ELSE INSERT 是独特替代方案。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/teradata.md) | **GROUPING SETS/CUBE/ROLLUP 完整+QUALIFY 子句（Teradata 首创）**——QUALIFY 在聚合函数中也可用于过滤窗口结果。对比 PG 无 QUALIFY 和 BigQuery/DuckDB 借鉴了 QUALIFY——Teradata 是 QUALIFY 语法的原创者。 |
| [条件函数](../functions/conditional/teradata.md) | **CASE/NULLIF/COALESCE/NVL+ZEROIFNULL（独有）**——ZEROIFNULL 将 NULL 转为 0（对比标准 COALESCE(col,0)）。NVL 来自 Oracle 兼容。对比 PG 标准 COALESCE——ZEROIFNULL 是 Teradata 独有便捷函数。 |
| [日期函数](../functions/date-functions/teradata.md) | **DATE 内部以 YYYMMDD 整数格式存储（独有设计）**——可直接做整数运算（date1-date2 返回天数差）。INTERVAL 类型完善。对比 PG DATE/TIMESTAMP 和 Oracle DATE（含时间到秒）——Teradata 的整数日期存储是独特历史设计。 |
| [数学函数](../functions/math-functions/teradata.md) | **完整数学函数**。对比 PG NUMERIC 任意精度和 BigQuery SAFE_DIVIDE——Teradata 数学函数完整。 |
| [字符串函数](../functions/string-functions/teradata.md) | **|| 拼接运算符+REGEXP_REPLACE/SUBSTR 标准**。对比 PG regexp_match 和 MySQL CONCAT()——Teradata 字符串函数标准完整。 |
| [类型转换](../functions/type-conversion/teradata.md) | **CAST 标准+FORMAT 格式化（独有关键字）**——`SELECT col (FORMAT 'YYYY-MM-DD')` 是 Teradata 独有的列级格式化语法。对比 PG to_char() 和 SQL Server CONVERT——Teradata 的 FORMAT 关键字更简洁但非标准。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/teradata.md) | **WITH+递归 CTE+QUALIFY 过滤窗口结果（Teradata 首创）**——QUALIFY 使 CTE+窗口函数组合更简洁。对比 PG 需子查询包装和 BigQuery 借鉴的 QUALIFY——Teradata 是 QUALIFY 语法的发明者。 |
| [全文搜索](../query/full-text-search/teradata.md) | **无内置全文搜索**——需外部工具。对比 PG tsvector+GIN 和 Oracle Text——Teradata 在全文搜索上是空白。 |
| [连接查询](../query/joins/teradata.md) | **Hash/Merge/Product JOIN+All-AMP 操作分析**——Product JOIN（笛卡尔积）是性能杀手需避免。EXPLAIN 明确标注 All-AMP 操作（全 AMP 参与）。对比 PG Hash/Merge/Nested Loop 和 BigQuery 自动选择——Teradata 的 JOIN 策略分析是 MPP 调优核心。 |
| [分页](../query/pagination/teradata.md) | **QUALIFY ROW_NUMBER() 分页+TOP/SAMPLE**——QUALIFY 使分页无需子查询。SAMPLE 随机采样。对比 PG LIMIT/OFFSET 和 SQL Server OFFSET...FETCH——Teradata 的 QUALIFY 分页最简洁。 |
| [行列转换](../query/pivot-unpivot/teradata.md) | **无原生 PIVOT**——CASE+GROUP BY 模拟。对比 Oracle/BigQuery/DuckDB 原生 PIVOT——Teradata 在行列转换上缺乏原生支持。 |
| [集合操作](../query/set-operations/teradata.md) | **UNION/INTERSECT/EXCEPT/MINUS 完整**——同时支持 EXCEPT 和 MINUS（Oracle 风格别名）。对比 Oracle 只有 MINUS 和 PG 只有 EXCEPT——Teradata 两种命名都支持。 |
| [子查询](../query/subquery/teradata.md) | **关联子查询优化——Teradata 优化器是业界最强之一**。对复杂多表 JOIN 和嵌套子查询的执行计划选择优于大多数引擎。对比 PG 优化器和 Oracle 优化器——Teradata 优化器是其核心竞争力。 |
| [窗口函数](../query/window-functions/teradata.md) | **窗口函数早期即支持+QUALIFY 首创过滤窗口结果**——后被 BigQuery/Snowflake/DuckDB 借鉴。对比 PG 8.4(2009) 和 MySQL 8.0(2018)——Teradata 在窗口函数和 QUALIFY 上都是先驱。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/teradata.md) | **sys_calendar.calendar 系统日历表是 Teradata 独有**——内置日历表包含每天的属性（工作日/周末/季度等），无需 generate_series。对比 PG generate_series 和 MySQL 递归 CTE——系统日历表是最优雅的日期填充方案。 |
| [去重](../scenarios/deduplication/teradata.md) | **QUALIFY ROW_NUMBER()=1 是 Teradata 首创的去重写法**——无需子查询包装。对比 PG DISTINCT ON 和 MySQL ROW_NUMBER+子查询——Teradata 的 QUALIFY 去重最简洁（后被 BigQuery/DuckDB 采纳）。 |
| [区间检测](../scenarios/gap-detection/teradata.md) | **窗口函数+sys_calendar 系统日历表检测间隙**——日历表提供完整日期序列无需生成。对比 PG generate_series 和 Vertica TIMESERIES——Teradata 日历表方案独特。 |
| [层级查询](../scenarios/hierarchical-query/teradata.md) | **递归 CTE 标准层级查询**。无 CONNECT BY（Oracle 独有）。对比 PG 递归 CTE+ltree——Teradata 层级查询标准。 |
| [JSON 展开](../scenarios/json-flatten/teradata.md) | **JSON_TABLE/JSON Shredding(16.20+)**——JSON Shredding 将 JSON 数据拆分为关系列。对比 PG JSONB+GIN 和 Oracle JSON_TABLE(12c+)——Teradata JSON 支持到达较晚。 |
| [迁移速查](../scenarios/migration-cheatsheet/teradata.md) | **PI 数据分布+QUALIFY+日期整数存储是迁移核心差异**。PI 选择影响查询性能、QUALIFY 需在其他引擎中用子查询替代、DATE 整数存储需类型转换。迁移出 Teradata 代价高——供应商锁定严重。 |
| [TopN 查询](../scenarios/ranking-top-n/teradata.md) | **QUALIFY ROW_NUMBER() 首创 TopN——无需子查询**。TOP N 也支持。对比 BigQuery/DuckDB 借鉴的 QUALIFY 和 PG DISTINCT ON——Teradata 的 QUALIFY TopN 最简洁。 |
| [累计求和](../scenarios/running-total/teradata.md) | **SUM() OVER 标准+MPP 并行计算**。对比 PG 单机和 BigQuery Slot 扩展——Teradata 利用 MPP 并行加速。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/teradata.md) | **MERGE+Temporal 表（Temporal Qualifier）实现 SCD**——双时态表（VALIDTIME+TRANSACTIONTIME）原生支持时间维度管理。对比 SQL Server Temporal Tables 和 Oracle Flashback——Teradata 的双时态表是时态数据管理的最完整实现。 |
| [字符串拆分](../scenarios/string-split-to-rows/teradata.md) | **STRTOK/REGEXP_SPLIT+CROSS JOIN 展开字符串**——STRTOK 类似 SPLIT_PART。对比 PG 14 string_to_table 和 SQL Server STRING_SPLIT——Teradata 字符串拆分功能基础。 |
| [窗口分析](../scenarios/window-analytics/teradata.md) | **窗口函数完整+QUALIFY 首创+MPP 并行**——QUALIFY 消除了窗口分析中的子查询嵌套。对比 PG FILTER+GROUPS 和 BigQuery QUALIFY——Teradata 是 QUALIFY 的发明者且窗口分析功能业界最早。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/teradata.md) | **PERIOD（时态区间）类型是 Teradata 独有**——`PERIOD(DATE, DATE)` 原生支持区间交集、包含、重叠检测。NORMALIZE 自动合并相邻区间。对比 PG 无原生 PERIOD 类型和 SQL Server 无 PERIOD——Teradata 的时态类型是时序数据建模的参考标准。 |
| [日期时间](../types/datetime/teradata.md) | **DATE 以 YYYMMDD 整数存储（独有设计）+TIMESTAMP+PERIOD 时态类型**——DATE 整数存储允许直接算术运算。PERIOD 类型原生支持区间操作。对比 PG DATE（纯日期类型）和 Oracle DATE（含时间到秒）——Teradata 的日期/时态类型体系独特。 |
| [JSON](../types/json/teradata.md) | **JSON/JSON_TABLE(16.20+)+JSON Shredding**——JSON Shredding 将 JSON 拆为关系列提升查询性能。对比 PG JSONB+GIN（最强）和 Oracle JSON_TABLE（最早标准）——Teradata JSON 到达较晚但 Shredding 是独特优化。 |
| [数值类型](../types/numeric/teradata.md) | **BYTEINT（1 字节整数，独有）/SMALLINT/INTEGER/BIGINT/DECIMAL/FLOAT/NUMBER**——BYTEINT 是 Teradata 独有的 1 字节整数类型（-128 到 127）。NUMBER 类型兼容 Oracle。对比 PG 无 BYTEINT 和 Oracle NUMBER 万能类型——Teradata 数值类型丰富且包含独有类型。 |
| [字符串类型](../types/string/teradata.md) | **VARCHAR/CHAR/CLOB+CHARACTER SET 显式指定字符集**——`VARCHAR(100) CHARACTER SET UNICODE` 显式指定。对比 PG UTF-8 默认和 MySQL utf8/utf8mb4 混淆——Teradata 的 CHARACTER SET 语法更明确。 |
