# SAP HANA

**分类**: 内存数据库（SAP）
**文件数**: 51 个 SQL 文件
**总行数**: 4410 行

## 概述与定位

SAP HANA 是 SAP 推出的内存计算平台，其核心是一个以列式存储为主、行列混存的关系数据库引擎。HANA 最初为加速 SAP 商业套件（ERP、BW）的实时分析而设计，后逐步发展为独立的通用数据库平台。它将 OLTP 与 OLAP 统一在同一引擎中，消除传统架构中从操作型系统到分析型系统的 ETL 延迟，是"实时企业"理念的技术支撑。

## 历史与演进

- **2010 年**：SAP HANA 1.0 发布，定位为 BW（Business Warehouse）加速器，纯内存列式存储。
- **2013 年**：HANA SPS06 引入行存引擎和应用服务器（XS Engine），从纯分析扩展到 OLTP 场景。
- **2015 年**：SAP S/4HANA 发布，HANA 成为 SAP 新一代 ERP 套件的唯一数据库平台。
- **2016 年**：HANA 2.0 引入多租户数据库容器（MDC）、动态分层（Dynamic Tiering）、SQLScript 增强。
- **2019 年**：引入 HANA Cloud，提供完全托管的云端 HANA 实例，支持数据湖和联邦查询。
- **2022 年**：增强 JSON Document Store、Graph Engine、空间数据处理与机器学习集成（PAL/APL）。
- **2024-2025 年**：持续推进向量引擎（用于 AI 应用）、改进多模型处理和云原生弹性。

## 核心设计思路

1. **内存优先**：热数据常驻内存，列式压缩使内存利用率极高；冷数据可下沉到磁盘或 Native Storage Extension。
2. **行列混存**：行存引擎（Row Store）处理事务型写密集负载，列存引擎（Column Store）处理分析型读密集负载，同一数据库共存。
3. **计算下推**：通过 SQLScript 将业务逻辑下推到数据库层执行，减少应用层与数据库之间的数据搬运。
4. **多模型引擎**：在同一平台上提供关系、图（Graph）、文档（JSON）、空间（Spatial）和文本搜索能力。

## 独特特色

| 特性 | 说明 |
|---|---|
| **SQLScript** | HANA 专有的过程化语言，强调声明式逻辑（表变量、CE 函数），编译器可自动并行化执行。 |
| **行列混存** | 建表时通过 `COLUMN` 或 `ROW` 关键字选择存储类型，也可在运行时为列存表添加行存二级索引。 |
| **FUZZY Search** | 内置模糊搜索引擎，`CONTAINS(..., FUZZY(0.8))` 支持拼写容错、语义相似度匹配，无需外部搜索引擎。 |
| **Hierarchy Functions** | 原生层级导航函数 `HIERARCHY()`、`HIERARCHY_DESCENDANTS()`，可直接对 parent-child 关系进行递归展开和聚合。 |
| **Calculation View** | 可视化建模工具定义的虚拟视图，底层由列引擎优化执行，是 SAP BW/4HANA 的核心数据模型。 |
| **系列数据处理** | 内置时间序列分析函数（`SERIES_GENERATE`、`SERIES_FILTER`），支持等间距时间序列的自动对齐与插值。 |
| **多租户容器（MDC）** | 一个 HANA 系统可包含多个独立数据库容器，共享内存和进程，实现资源隔离。 |

## 已知不足

- **SAP 生态深度绑定**：HANA 的最佳实践和工具链高度依赖 SAP 生态系统，非 SAP 用户的独立使用体验相对薄弱。
- **许可成本极高**：HANA 的内存许可模式按 GB 计费，是市场上最昂贵的数据库之一。
- **第三方生态有限**：虽然提供 ODBC/JDBC 驱动，但 ORM 框架、BI 工具对 HANA 方言的支持不如主流数据库完善。
- **SQLScript 学习成本**：其声明式风格（表变量、无游标设计）与传统 PL/SQL 差异大，迁移存量代码需大量重写。
- **开源社区缺失**：HANA 是闭源商业产品，缺少社区版和开源替代方案，技术讨论和知识分享集中在 SAP 官方渠道。

## 对引擎开发者的参考价值

- **行列混存架构**：在同一引擎中协调行存和列存的事务一致性，对 HTAP 数据库设计有核心参考意义。
- **SQLScript 的声明式编译**：将过程化代码中的表变量操作自动转化为关系代数并行执行图，是"将逻辑下推到引擎"的典范。
- **FUZZY 搜索引擎集成**：将模糊文本搜索作为 SQL 谓词的一部分而非独立服务，展示了搜索与查询引擎融合的可能性。
- **Hierarchy 函数设计**：以函数而非递归 CTE 的方式处理层级数据，减少了递归查询的优化难度。
- **内存管理策略**：HANA 的列存压缩算法（字典编码、游程编码、聚类编码）和 Delta/Main 合并策略对内存引擎设计有直接借鉴。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/saphana.md) | **内存列存默认（ROW/COLUMN 可选）**——`CREATE COLUMN TABLE` 创建列存表（分析默认），`CREATE ROW TABLE` 创建行存表（OLTP 写入密集）。热数据常驻内存，冷数据通过 Native Storage Extension 下沉磁盘。Delta Store 缓冲写入，Main Store 存储压缩列数据。对比 PostgreSQL（仅行存）和 BigQuery（仅列存），HANA 在同一引擎中同时支持行列混存是 HTAP 架构的典范。 |
| [改表](../ddl/alter-table/saphana.md) | **ALTER 在线执行，列存/行存表各有限制**——列存表不支持某些列类型变更（需重建），行存表的 ALTER 更灵活。ALTER TABLE ... COLUMN/ROW 可转换存储类型（但代价较大）。对比 PostgreSQL（ALTER 操作灵活）和 Oracle（ALTER 较完整），HANA 的 ALTER 限制源于列存和行存的不同物理组织。 |
| [索引](../ddl/indexes/saphana.md) | **列存表自动索引（无需手动创建）**——列存引擎自动维护字典编码和反向索引，大多数查询无需手动建索引。行存表支持 B-tree 和 Fulltext 索引。对比 BigQuery（无索引，用分区+聚集替代）和 PostgreSQL（需手动创建索引），HANA 的列存自动索引消除了索引调优工作。 |
| [约束](../ddl/constraints/saphana.md) | **PK/FK/UNIQUE/CHECK 完整支持且强制执行**。列存和行存表均支持完整约束。对比 BigQuery（NOT ENFORCED 约束）和 Snowflake（约束不执行），HANA 作为 HTAP 引擎实际执行约束保证数据完整性。 |
| [视图](../ddl/views/saphana.md) | **Calculation View（图形化建模）+ SQL View，无传统物化视图**——Calculation View 通过 SAP BW 建模工具定义，底层由列引擎优化执行，是 S/4HANA 的核心数据模型。SQL View 标准但功能较弱。对比 BigQuery（物化视图自动增量刷新）和 Oracle（完整物化视图），HANA 用 Calculation View 替代了物化视图的角色。 |
| [序列与自增](../ddl/sequences/saphana.md) | **SEQUENCE + GENERATED ALWAYS AS IDENTITY**——标准 SQL 自增列语法。SEQUENCE 支持 CYCLE/CACHE 选项。对比 PostgreSQL 的 SERIAL/IDENTITY 和 MySQL 的 AUTO_INCREMENT，HANA 的序列实现遵循 SQL 标准。 |
| [数据库/Schema/用户](../ddl/users-databases/saphana.md) | **Multi-Tenant 数据库容器（MDC）+ Schema = 用户命名空间**——一个 HANA 系统可包含多个独立数据库容器（System + Tenant DB），共享内存和进程。XS Advanced 提供应用服务器功能。对比 PostgreSQL（Database/Schema 二级）和 Oracle（Multitenant CDB/PDB），HANA 的 MDC 实现多租户资源隔离。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/saphana.md) | **EXEC/EXECUTE IMMEDIATE + SQLScript 过程语言**——SQLScript 是 HANA 专有的声明式过程语言，强调表变量而非游标。EXEC 执行动态 SQL 字符串。对比 PostgreSQL 的 PL/pgSQL EXECUTE 和 Oracle 的 PL/SQL EXECUTE IMMEDIATE，SQLScript 的声明式风格（编译器自动并行化）是其独特优势。 |
| [错误处理](../advanced/error-handling/saphana.md) | **DECLARE EXIT/CONTINUE HANDLER + SIGNAL/RESIGNAL**——SQLScript 异常处理支持 SQLEXCEPTION 和自定义条件。SIGNAL 主动抛出异常，RESIGNAL 重新抛出。对比 PostgreSQL 的 EXCEPTION WHEN/RAISE 和 SQL Server 的 TRY...CATCH/THROW，HANA 的异常处理遵循 SQL/PSM 标准。 |
| [执行计划](../advanced/explain/saphana.md) | **EXPLAIN PLAN + PlanViz 图形化工具（SAP 特色）**——PlanViz 在 SAP HANA Studio/Database Explorer 中可视化显示 Calculation Engine 执行计划，包括列引擎操作、JIT 编译状态和内存消耗。对比 PostgreSQL 的 EXPLAIN ANALYZE（文本输出）和 Oracle 的 DBMS_XPLAN，HANA 的 PlanViz 图形化是 DBA 体验的独特优势。 |
| [锁机制](../advanced/locking/saphana.md) | **MVCC（列存）+ 行锁（行存），Snapshot Isolation 默认**——列存引擎使用 MVCC 快照隔离（读不阻塞写），行存引擎使用传统行级锁。Delta Store 写入不阻塞 Main Store 读取。对比 PostgreSQL（全局 MVCC 多版本元组）和 Oracle（Undo Log MVCC），HANA 的行列混存需要两套不同的并发控制策略。 |
| [分区](../advanced/partitioning/saphana.md) | **HASH/RANGE/ROUND_ROBIN 分区 + 大表自动分区推荐**——系统可自动推荐分区策略。多级分区（如 HASH + RANGE）支持复杂数据分布。ROUND_ROBIN 用于均匀负载分布。对比 PostgreSQL（RANGE/LIST/HASH 声明式）和 Oracle（分区类型最丰富），HANA 的 ROUND_ROBIN 分区是内存引擎负载均衡的独特选择。 |
| [权限](../advanced/permissions/saphana.md) | **细粒度 Privilege 体系 + Analytic Privilege 行级安全**——Analytic Privilege 基于 Calculation View 维度值限制用户可见数据范围，是 SAP 报表场景的核心安全机制。对比 PostgreSQL 的 RLS（行级安全策略）和 Oracle 的 VPD，HANA 的 Analytic Privilege 与 SAP 业务模型深度绑定。 |
| [存储过程](../advanced/stored-procedures/saphana.md) | **SQLScript 过程语言——声明式表变量 + 编译器自动并行化**。SQLScript 避免使用游标和逐行处理，鼓励用表变量和 SQL 表达式描述逻辑，编译器将其转换为并行执行图。CE 函数（Calculation Engine Functions）可直接调用列引擎操作。对比 PostgreSQL 的 PL/pgSQL（命令式风格）和 Oracle 的 PL/SQL（命令式 + 游标），SQLScript 的声明式设计是"将逻辑下推到引擎"的典范。 |
| [临时表](../advanced/temp-tables/saphana.md) | **LOCAL/GLOBAL TEMPORARY TABLE + 列存/行存可选**——临时表可选择列存或行存引擎。LOCAL TEMPORARY 会话级，GLOBAL TEMPORARY 定义持久但数据会话级。对比 PostgreSQL 的 CREATE TEMP TABLE（仅行存）和 Oracle 的 GTT，HANA 的临时表可选列存是分析场景的优势。 |
| [事务](../advanced/transactions/saphana.md) | **MVCC Snapshot Isolation + READ COMMITTED 默认**——ACID 完整支持。内存中事务处理速度极快。列存表的 Delta Merge 操作是后台异步执行，不阻塞事务。对比 PostgreSQL（READ COMMITTED 默认）和 Oracle（READ COMMITTED 默认），HANA 的事务行为与传统 RDBMS 一致，内存加速是性能优势。 |
| [触发器](../advanced/triggers/saphana.md) | **BEFORE/AFTER 行级触发器，无语句级触发器**——触发器在行存和列存表上均可用。建议尽可能用 SQLScript 存储过程替代触发器（性能更好）。对比 PostgreSQL（行级+语句级完整）和 Oracle（行级+语句级+INSTEAD OF），HANA 的触发器功能相对有限。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/saphana.md) | **DELETE 标准 + TRUNCATE 即时**——内存引擎下 DELETE 和 TRUNCATE 都非常快。列存表的 DELETE 在 Delta Store 中标记删除，后续 Delta Merge 时物理清除。对比 PostgreSQL（DELETE 产生死元组需 VACUUM）和 BigQuery（DELETE 重写分区），HANA 的内存删除速度是传统磁盘引擎难以比拟的。 |
| [插入](../dml/insert/saphana.md) | **INSERT + UPSERT 标准 + IMPORT FROM 批量加载**——IMPORT FROM 支持 CSV/Parquet 等格式的批量导入。列存表的 INSERT 先进入 Delta Store 再合并到 Main Store。对比 PostgreSQL 的 COPY（批量加载）和 BigQuery 的 LOAD JOB（免费），HANA 的 IMPORT FROM 是内存数据库的高速加载通道。 |
| [更新](../dml/update/saphana.md) | **UPDATE 标准 + UPSERT(REPLACE) 支持**——UPSERT 语句在 HANA 中是原生关键字，根据主键自动判断插入或更新。列存表 UPDATE 在 Delta Store 中执行。对比 PostgreSQL 的 UPDATE（行内就地更新）和 BigQuery（UPDATE 重写分区），HANA 的内存 UPDATE 性能极高。 |
| [Upsert](../dml/upsert/saphana.md) | **UPSERT/REPLACE 语句原生支持（非 MERGE）**——`UPSERT table VALUES (...)` 直接使用，语法比 MERGE 更简洁。REPLACE 是 UPSERT 的别名。同时也支持标准 MERGE INTO 语法。对比 PostgreSQL 的 ON CONFLICT（需指定冲突列）和 MySQL 的 REPLACE INTO（先删后插语义不同），HANA 的 UPSERT 是最简洁的原生实现之一。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/saphana.md) | **STRING_AGG + GROUPING SETS/CUBE/ROLLUP 完整**——高级聚合全面支持。内存列存引擎下聚合计算极快（字典编码加速 GROUP BY）。对比 PostgreSQL 的 string_agg（功能类似）和 BigQuery 的 APPROX_COUNT_DISTINCT（近似聚合），HANA 的精确聚合在内存中速度可与其他引擎的近似聚合相当。 |
| [条件函数](../functions/conditional/saphana.md) | **CASE/IFNULL/NULLIF/COALESCE + MAP（类似 DECODE）**——MAP 函数 `MAP(expr, val1, res1, val2, res2, default)` 等价于 Oracle 的 DECODE，语法更清晰。对比 Oracle 的 DECODE（相同功能）和 PostgreSQL（无 MAP/DECODE，需用 CASE），HANA 的 MAP 函数是 DECODE 的改良命名。 |
| [日期函数](../functions/date-functions/saphana.md) | **ADD_DAYS/ADD_MONTHS/DAYS_BETWEEN/MONTHS_BETWEEN**——HANA 独有的日期函数命名风格，比 INTERVAL 算术更直观。LAST_DAY/NEXT_DAY 等便捷函数。对比 PostgreSQL 的 INTERVAL 算术（更灵活）和 Oracle 的 ADD_MONTHS（HANA 同名），HANA 的日期函数丰富且命名清晰。 |
| [数学函数](../functions/math-functions/saphana.md) | **完整数学函数**——MOD/CEIL/FLOOR/ROUND/POWER/SQRT/LOG/LN 标准。内存计算下数学运算性能极高。对比各主流引擎数学函数基本一致。 |
| [字符串函数](../functions/string-functions/saphana.md) | **\|\| 拼接 + LOCATE/SUBSTR/REPLACE 标准**——LOCATE 返回子串位置（类似 Oracle 的 INSTR），SUBSTR 截取子串。对比 PostgreSQL 的 position/substring（标准命名）和 MySQL 的 LOCATE（相同函数），HANA 字符串函数命名偏向 Oracle 风格。 |
| [类型转换](../functions/type-conversion/saphana.md) | **CAST + TO_DATE/TO_DECIMAL/TO_VARCHAR 显式转换**——TO_* 系列函数提供格式化转换。隐式转换规则比 PostgreSQL 严格但比 MySQL 宽松。对比 PostgreSQL 的 :: 运算符（更简洁）和 Oracle 的 TO_NUMBER/TO_DATE（HANA 类似），HANA 的类型转换函数遵循 Oracle 风格命名。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/saphana.md) | **WITH 标准 + 递归 CTE 支持**——递归 CTE 可用于层级查询。但 HANA 更推荐使用 HIERARCHY 函数（专用层级处理，性能更好）。对比 PostgreSQL（WITH RECURSIVE 原生）和 Oracle（CONNECT BY + 递归 CTE），HANA 在层级处理上有专用函数替代递归 CTE。 |
| [全文搜索](../query/full-text-search/saphana.md) | **FULLTEXT INDEX（列存内置）+ CONTAINS/FUZZY/近邻搜索**——`CONTAINS(col, FUZZY(0.8, 'similarCalculationMode=substringsearch'))` 支持拼写容错和语义模糊匹配，无需外部搜索引擎。对比 PostgreSQL 的 tsvector+GIN（精确匹配为主）和 Elasticsearch（专用搜索引擎），HANA 的 **FUZZY 搜索**是将模糊匹配融入 SQL 的独特设计。 |
| [连接查询](../query/joins/saphana.md) | **JOIN 完整 + LATERAL（2.0+）+ 内存计算加速**——所有 JOIN 类型在内存中执行，列存引擎的哈希 JOIN 利用字典编码加速。对比 PostgreSQL（磁盘 I/O 受限的 JOIN）和 BigQuery（Slot 并行 JOIN），HANA 的内存 JOIN 在中小规模数据集上延迟极低。 |
| [分页](../query/pagination/saphana.md) | **LIMIT/OFFSET 标准**——内存引擎下分页查询响应极快。对比 PostgreSQL（LIMIT/OFFSET 标准）和 Oracle（FETCH FIRST/ROWNUM），HANA 的分页语法遵循 SQL 标准。 |
| [行列转换](../query/pivot-unpivot/saphana.md) | **无原生 PIVOT——CASE+GROUP BY 或 MAP 函数**。MAP 函数可简化 CASE 表达式的编写。对比 Oracle（PIVOT 原生 11g+）和 BigQuery（PIVOT 原生 2021+），HANA 缺少原生行列转换语法。 |
| [集合操作](../query/set-operations/saphana.md) | **UNION/INTERSECT/EXCEPT 完整**——ALL/DISTINCT 修饰符支持。内存引擎下集合操作性能高效。对比 PostgreSQL（集合操作完整）和 MySQL 8.0（INTERSECT/EXCEPT 较新），HANA 的集合操作功能完整。 |
| [子查询](../query/subquery/saphana.md) | **关联子查询 + 标量子查询优化**——HANA 优化器擅长将子查询转为 JOIN。列存引擎的向量化执行加速子查询计算。对比 PostgreSQL（优化器成熟）和 MySQL 8.0（子查询优化改善），HANA 的内存+列存使子查询性能表现优异。 |
| [窗口函数](../query/window-functions/saphana.md) | **完整窗口函数 + ROWS/RANGE/GROUPS 帧**——GROUPS 帧（SQL:2011 标准）在 HANA 中支持，可按组而非行定义窗口边界。对比 PostgreSQL 12+（GROUPS 帧支持）和 MySQL 8.0（GROUPS 帧不支持），HANA 在窗口函数标准合规性上领先。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/saphana.md) | **SERIES_GENERATE_DATE 序列生成（独有函数）**——`SELECT * FROM SERIES_GENERATE_DATE('INTERVAL 1 DAY', '2024-01-01', '2024-12-31')` 直接生成日期序列表。对比 PostgreSQL 的 generate_series（类似但参数语法不同）和 BigQuery 的 GENERATE_DATE_ARRAY，HANA 的 SERIES_GENERATE 是内置的时间序列生成器。 |
| [去重](../scenarios/deduplication/saphana.md) | **ROW_NUMBER + CTE 去重**——标准窗口函数去重模式。内存引擎下排序和去重极快。对比 PostgreSQL 的 DISTINCT ON（更简洁）和 BigQuery 的 QUALIFY（最简洁），HANA 使用通用去重方案。 |
| [区间检测](../scenarios/gap-detection/saphana.md) | **SERIES_GENERATE + 窗口函数**——SERIES_GENERATE 生成完整时间序列，LEFT JOIN 检测缺失。SERIES_FILTER 可直接过滤异常间隙。对比 PostgreSQL 的 generate_series（类似）和 BigQuery 的 GENERATE_DATE_ARRAY，HANA 的 SERIES 函数族专为时序分析设计。 |
| [层级查询](../scenarios/hierarchical-query/saphana.md) | **HIERARCHY 函数（独有）+ 递归 CTE 亦支持**——`HIERARCHY(SOURCE ... JOIN PARENT)` 直接将 parent-child 关系展开为层级结构，支持 HIERARCHY_DESCENDANTS/ANCESTORS 导航。对比 PostgreSQL（仅递归 CTE）和 Oracle（CONNECT BY + 递归 CTE），HANA 的 HIERARCHY 函数以函数而非递归查询处理层级数据，减少了优化器对递归的处理难度。 |
| [JSON 展开](../scenarios/json-flatten/saphana.md) | **JSON_TABLE/JSON_QUERY/JSON_VALUE（SQL:2016 标准）**——遵循标准 JSON 函数实现，内存加速 JSON 解析。对比 PostgreSQL 的 jsonb_array_elements（PG 特有）和 BigQuery 的 JSON_QUERY_ARRAY+UNNEST，HANA 的 JSON 处理遵循标准路径。 |
| [迁移速查](../scenarios/migration-cheatsheet/saphana.md) | **内存列存 + SQLScript + Calculation View 是核心差异**。关键注意：SQLScript 声明式风格与 PL/SQL 差异大（需大量重写）；Calculation View 替代物化视图和复杂报表查询；FUZZY 搜索替代外部搜索引擎；许可按内存 GB 计费极贵；SAP 生态绑定度高。 |
| [TopN 查询](../scenarios/ranking-top-n/saphana.md) | **ROW_NUMBER + LIMIT 标准**——内存引擎下 TopN 排序极快。对比 PostgreSQL（相同方案）和 BigQuery（QUALIFY 更简洁），HANA 使用通用 TopN 方案，内存加速是性能优势。 |
| [累计求和](../scenarios/running-total/saphana.md) | **SUM() OVER 标准——内存计算极快**。列存引擎的向量化执行使窗口累计在内存中毫秒级完成。对比 PostgreSQL（磁盘 I/O 限制）和 BigQuery（Slot 并行），HANA 的内存计算在中小数据集上延迟最低。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/saphana.md) | **MERGE + 系统版本化表（Temporal Table）**——HANA 支持 SQL:2011 标准的时态表（SYSTEM_TIME），自动记录数据历史版本。`FOR SYSTEM_TIME AS OF timestamp` 查询历史数据。对比 PostgreSQL（无原生时态表）和 Db2（时态表先驱），HANA 的时态表是 SCD 最优雅的实现方式。 |
| [字符串拆分](../scenarios/string-split-to-rows/saphana.md) | **SERIES_GENERATE + SUBSTR 或 JSON_TABLE**——无内置 SPLIT 函数，需用 SERIES_GENERATE 生成位置序列再逐段截取，或将字符串包装为 JSON 数组用 JSON_TABLE 展开。对比 PostgreSQL 的 string_to_array+unnest（最简洁）和 BigQuery 的 SPLIT+UNNEST，HANA 的字符串拆分方案较复杂。 |
| [窗口分析](../scenarios/window-analytics/saphana.md) | **完整窗口函数 + SERIES 时序分析能力**——SERIES_FILTER/SERIES_GENERATE 与窗口函数结合，提供时序数据的原生分析支持。内存列存引擎使窗口分析性能极高。对比 PostgreSQL（窗口函数完整但无 SERIES 函数）和 TimescaleDB（time_bucket 时序扩展），HANA 的 SERIES 函数族是内置时序分析能力。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/saphana.md) | **无原生 ARRAY/STRUCT 列类型——用表类型（TABLE TYPE）替代**。SQLScript 中可定义表类型变量传递结果集。对比 PostgreSQL 的 ARRAY（原生列类型）和 BigQuery 的 STRUCT/ARRAY（一等公民），HANA 的集合数据处理通过表变量而非列类型实现。 |
| [日期时间](../types/datetime/saphana.md) | **DATE/TIME/TIMESTAMP/SECONDDATE 四种类型**——SECONDDATE 是 HANA 独有类型（秒精度时间戳，比 TIMESTAMP 存储更紧凑）。TIMESTAMP 支持到纳秒精度。对比 PostgreSQL（DATE/TIME/TIMESTAMP/INTERVAL 四种）和 BigQuery（DATE/TIME/DATETIME/TIMESTAMP 四种），HANA 的 SECONDDATE 是独特的紧凑时间类型。 |
| [JSON](../types/json/saphana.md) | **JSON Document Store + JSON_TABLE（SQL 标准）+ 内存加速**——JSON Document Store 可存储无 Schema 文档并通过 SQL 查询。内存计算使 JSON 解析极快。对比 PostgreSQL 的 JSONB+GIN（二进制存储+索引）和 MongoDB（原生文档存储），HANA 的 JSON 处理结合了关系引擎和文档存储的优势。 |
| [数值类型](../types/numeric/saphana.md) | **TINYINT-BIGINT/DECIMAL/FLOAT/DOUBLE + SMALLDECIMAL**——SMALLDECIMAL 是 HANA 独有的浮点十进制类型，精度由系统管理（最大 16 位有效数字），比 DECIMAL 更节省内存。对比 PostgreSQL 的 NUMERIC（任意精度）和 BigQuery 的 NUMERIC/BIGNUMERIC，HANA 的 SMALLDECIMAL 是内存引擎的存储优化。 |
| [字符串类型](../types/string/saphana.md) | **NVARCHAR（UTF-8 默认）+ VARCHAR/NCLOB，无 TEXT 别名**——NVARCHAR 是推荐的字符串类型（Unicode 支持），列存引擎自动字典编码压缩。无 TEXT 类型别名（与 PostgreSQL 不同）。对比 PostgreSQL 的 TEXT（推荐，无长度限制）和 MySQL 的 VARCHAR+utf8mb4，HANA 的 NVARCHAR 命名遵循 SQL Server 传统。 |
