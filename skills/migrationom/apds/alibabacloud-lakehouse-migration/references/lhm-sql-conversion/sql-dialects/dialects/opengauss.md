# openGauss

**分类**: 开源数据库（华为，基于 PostgreSQL）
**文件数**: 51 个 SQL 文件
**总行数**: 4877 行

## 概述与定位

openGauss 是华为于 2020 年开源的关系型数据库，源自华为内部的 GaussDB 产品，基于 PostgreSQL 9.2 内核深度改造。openGauss 定位于企业级核心交易系统，特别强调高性能、高可用和安全合规。它针对华为鲲鹏（ARM）处理器做了深度优化，同时也支持 x86 架构，是中国信创生态的重要数据库选项。

## 历史与演进

- **2011 年**：华为内部启动 GaussDB 项目，基于 PostgreSQL 内核开发。
- **2019 年**：GaussDB 作为华为云服务商用，积累金融和政企客户。
- **2020 年 6 月**：以 openGauss 品牌正式开源，采用木兰宽松许可证。
- **2021 年**：openGauss 2.0 引入内存表（MOT）引擎和 AI4DB 能力。
- **2022 年**：3.0 推出 Sharding 分布式方案和数据库运维 AI 工具。
- **2023 年**：5.0 引入分布式强一致事务和列存引擎增强。
- **2024-2025 年**：持续完善生态工具链和多模数据支持。

## 核心设计思路

openGauss 在 PostgreSQL 内核基础上做了大量底层改造：线程化架构（替代 PG 的多进程模型，减少上下文切换开销）、NUMA-Aware 内存分配（针对多路服务器优化）、以及增量检查点机制。存储引擎支持行存（Astore/Ustore）和列存（CStore），Ustore 采用 Undo Log 实现就地更新，减少存储膨胀。安全方面内置全密态数据库能力和透明数据加密。

## 独特特色

- **MOT (Memory-Optimized Table)**：内存优化表引擎，采用乐观并发控制和 Lock-Free 索引，极端 OLTP 场景下可达数百万 TPS。
- **AI4DB**：内置 AI 调优能力——自动索引推荐、慢 SQL 诊断、负载预测和参数自调优。
- **鲲鹏优化**：针对 ARM 架构的 SIMD 指令、原子操作和缓存行优化。
- **Ustore 引擎**：基于 Undo Log 的就地更新存储引擎，解决 PG 原生 MVCC 的 Bloat 问题。
- **全密态计算**：数据在计算过程中保持加密状态，防止 DBA 窥探敏感数据。
- **DB4AI**：数据库内置机器学习算法，支持 `CREATE MODEL` 语法直接在库内训练模型。
- **WDR 报告**：Workload Diagnosis Report 类似 Oracle AWR，提供全面的性能诊断。

## 已知不足

- 基于 PG 9.2 内核分叉较早，缺少 PG 后续版本的大量新特性（如逻辑复制增强、JIT 编译等）。
- 与最新 PostgreSQL 的兼容性存在差距，部分 PG 扩展不能直接使用。
- 社区规模相比 PostgreSQL/MySQL 较小，第三方工具和文档资源有限。
- MOT 内存表不支持所有 SQL 特性（如部分 DDL 操作和复杂约束）。
- 线程模型虽提升了短连接性能，但在超高并发场景下线程调度也有瓶颈。
- 国际社区参与度有限，文档和社区交流以中文为主。

## 对引擎开发者的参考价值

openGauss 展示了如何在 PostgreSQL 基础上进行深度内核改造：从多进程到多线程架构的迁移经验、NUMA-Aware 内存管理的实践、Ustore 引擎对 MVCC Bloat 问题的解决方案、以及 MOT 内存引擎的 Lock-Free 并发控制设计。其 AI4DB 集成（将机器学习嵌入数据库调优流程）代表了数据库自治化的一个方向。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/opengauss.md) | **行存（Astore/Ustore）和列存（CStore）可选**——建表时通过 `WITH (ORIENTATION=COLUMN)` 指定列存，适合分析型查询；Ustore 引擎使用 Undo Log 就地更新，解决 PG 原生的表膨胀问题。**MOT 内存表**通过 `CREATE FOREIGN TABLE ... SERVER mot_server` 创建，极端 OLTP 可达百万 TPS。对比 PostgreSQL（仅行存）和 SAP HANA（行列混存），openGauss 在存储引擎多样性上超越 PG 原生。 |
| [改表](../ddl/alter-table/opengauss.md) | **PG 兼容 ALTER + 在线变更支持**。DDL 可在事务中回滚（继承 PG 优势）。列存表的 ALTER 有额外限制（如不支持部分列类型变更）。对比 PostgreSQL（DDL 事务性原生）和 Oracle（DDL 自动提交），openGauss 保留了 PG 的事务安全特性。 |
| [索引](../ddl/indexes/opengauss.md) | **B-tree/GIN/GiST（PG 兼容）+ Ubtree（独有优化）**——Ubtree 是 openGauss 针对 Ustore 引擎优化的 B-tree 变体，减少索引膨胀。列存表自动使用 CU（Compression Unit）级 min/max 索引加速裁剪。对比 PostgreSQL 的 B-tree（标准实现）和达梦的 Bitmap 索引，openGauss 的 Ubtree 是存储引擎层的深度优化。 |
| [约束](../ddl/constraints/opengauss.md) | **PK/FK/CHECK/UNIQUE 完整支持**（PG 兼容）。MOT 内存表的约束支持有限制（如不支持外键和部分复杂 CHECK）。对比 PostgreSQL（约束功能完整）和 MySQL InnoDB（CHECK 约束 8.0 才真正生效），openGauss 在行存表上约束能力对齐 PG。 |
| [视图](../ddl/views/opengauss.md) | **物化视图（PG 兼容）+ REFRESH 标准**。支持 REFRESH MATERIALIZED VIEW 手动刷新。对比 PostgreSQL（REFRESH MATERIALIZED VIEW CONCURRENTLY 支持并发刷新）和 BigQuery（自动增量刷新），openGauss 的物化视图能力跟随 PG 内核版本。 |
| [序列与自增](../ddl/sequences/opengauss.md) | **SERIAL/IDENTITY/SEQUENCE（PG 兼容）**三种自增方式均支持。分布式部署下序列的全局唯一性由协调节点保证。对比 PostgreSQL（SERIAL/IDENTITY 标准）和 Oracle（SEQUENCE + CURRVAL/NEXTVAL），openGauss 的序列能力与 PG 对齐。 |
| [数据库/Schema/用户](../ddl/users-databases/opengauss.md) | **PG 兼容权限 + 三权分立 + 行级安全（RLS）**——三权分立将系统管理、安全审计和审计管理权限分离。行级安全策略（RLS）可控制不同用户看到不同行。对比 PostgreSQL 的 RLS（原生支持）和达梦的三权分立（类似设计），openGauss 在 PG 的 RLS 基础上增加了等保安全模型。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/opengauss.md) | **EXECUTE（PL/pgSQL 兼容）+ Oracle 兼容 EXECUTE IMMEDIATE**——A 数据库兼容模式下（`dbcompatibility='A'`）支持 EXECUTE IMMEDIATE 语法。对比 PostgreSQL（仅 EXECUTE）和 Oracle（EXECUTE IMMEDIATE 原生），openGauss 通过兼容模式扩展了动态 SQL 选项。 |
| [错误处理](../advanced/error-handling/opengauss.md) | **EXCEPTION WHEN（PL/pgSQL 兼容）**——捕获 SQLSTATE 异常码，支持 RAISE 抛出自定义异常。A 数据库兼容模式下可使用 Oracle 风格异常名。对比 PostgreSQL（EXCEPTION WHEN 原生）和 Oracle（PL/SQL EXCEPTION），openGauss 的错误处理基于 PG 体系并可扩展。 |
| [执行计划](../advanced/explain/opengauss.md) | **EXPLAIN ANALYZE（PG 兼容）+ AI 调优建议（独有）**——AI4DB 模块可自动分析慢 SQL 并推荐索引、参数调整。WDR 报告（类似 Oracle AWR）提供全面的性能诊断。对比 PostgreSQL 的 EXPLAIN ANALYZE（无 AI 建议）和 Oracle 的 AWR + SQL Tuning Advisor，openGauss 在 AI 辅助调优上是 PG 生态的独特扩展。 |
| [锁机制](../advanced/locking/opengauss.md) | **MVCC（PG 兼容）+ Ustore 优化**——Ustore 引擎使用 Undo Log 避免多版本元组堆积，减少 VACUUM 压力。Astore 引擎保持 PG 原生多版本元组行为。对比 PostgreSQL（多版本元组 + VACUUM 维护）和 Oracle（Undo Log MVCC），openGauss 的 Ustore 借鉴了 Oracle 的 MVCC 策略以解决 PG 的表膨胀痛点。 |
| [分区](../advanced/partitioning/opengauss.md) | **RANGE/LIST/HASH/INTERVAL 分区（PG 兼容 + 增强）**——INTERVAL 分区在 RANGE 基础上自动按间隔创建新分区（如按月自动扩展），这是超越原生 PG 的增强。对比 PostgreSQL 10+（声明式分区，无 INTERVAL）和 Oracle（INTERVAL 分区原生），openGauss 在分区功能上向 Oracle 靠拢。 |
| [权限](../advanced/permissions/opengauss.md) | **PG 兼容 RBAC + 三权分立 + 数据脱敏**——内置数据脱敏策略可对敏感列自动遮蔽（如手机号中间四位用 * 替代），无需应用层处理。对比 PostgreSQL（无内置脱敏）和 Oracle 的 Data Redaction（功能类似），openGauss 的脱敏能力是国产安全增值。 |
| [存储过程](../advanced/stored-procedures/opengauss.md) | **PL/pgSQL + Oracle 兼容模式（A 数据库兼容）**——设置 `dbcompatibility='A'` 后支持 Oracle 风格的存储过程语法、Package 和自治事务。对比 PostgreSQL（仅 PL/pgSQL，无 Package）和金仓（PG/Oracle 双模式），openGauss 的 A 兼容模式专注 Oracle 过程语言迁移。 |
| [临时表](../advanced/temp-tables/opengauss.md) | **TEMPORARY TABLE（PG 兼容）**——CREATE TEMP TABLE 创建会话级临时表，事务结束后可选保留或删除数据。A 兼容模式下可用 Oracle 风格 GTT 语法。对比 PostgreSQL（CREATE TEMP TABLE 标准）和 Oracle（CREATE GLOBAL TEMPORARY TABLE），openGauss 根据兼容模式适配语法。 |
| [事务](../advanced/transactions/opengauss.md) | **MVCC + DDL 事务性（PG 优势保留）**——DDL 可在事务中回滚。Ustore 引擎支持更高效的事务回滚（Undo Log 直接回退）。对比 PostgreSQL（DDL 事务性原生）和 Oracle（DDL 自动提交），openGauss 保留了 PG 的事务安全特性并在 Ustore 上优化了回滚性能。 |
| [触发器](../advanced/triggers/opengauss.md) | **BEFORE/AFTER/INSTEAD OF（PG 兼容）**——行级和语句级触发器均支持。A 兼容模式下触发器语法可接近 Oracle 风格。对比 PostgreSQL（触发器功能完整）和 MySQL（仅 BEFORE/AFTER 行级），openGauss 的触发器能力对齐 PG。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/opengauss.md) | **DELETE ... RETURNING（PG 兼容）**——删除后立即返回被删除行数据。Ustore 引擎下 DELETE 通过 Undo Log 实现更高效的空间回收。对比 PostgreSQL（RETURNING 原生，需 VACUUM 回收）和 Oracle（无 DELETE RETURNING），openGauss 的 Ustore 在删除密集场景下有优势。 |
| [插入](../dml/insert/opengauss.md) | **INSERT ... RETURNING + ON CONFLICT**——RETURNING 返回新插入行，ON CONFLICT 实现原子性 Upsert。列存表的 INSERT 批量写入性能优于行存。对比 PostgreSQL（ON CONFLICT 原生）和 MySQL 的 ON DUPLICATE KEY UPDATE（功能类似），openGauss 的 INSERT 能力对齐 PG。 |
| [更新](../dml/update/opengauss.md) | **UPDATE ... RETURNING（PG 兼容）**——Ustore 引擎下 UPDATE 是就地更新（in-place update），避免 PG 原生的 HOT 更新限制和表膨胀。对比 PostgreSQL（UPDATE 产生新版本元组）和 Oracle（就地更新 + Undo），openGauss Ustore 的 UPDATE 效率更接近 Oracle。 |
| [Upsert](../dml/upsert/opengauss.md) | **ON CONFLICT（PG 兼容）+ MERGE（Oracle 兼容）**——PG 模式用 ON CONFLICT，A 兼容模式用 MERGE INTO 标准语法。对比 PostgreSQL（仅 ON CONFLICT）和 Oracle（仅 MERGE），openGauss 在 Upsert 场景下提供双路径。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/opengauss.md) | **PG 兼容聚合 + LISTAGG（Oracle 兼容）**——A 兼容模式下 LISTAGG(col, ',') WITHIN GROUP (ORDER BY ...) 可用。标准 string_agg 在 PG 模式下可用。对比 PostgreSQL 的 string_agg（原生）和 Oracle 的 LISTAGG（原生），openGauss 根据兼容模式选择函数名。 |
| [条件函数](../functions/conditional/opengauss.md) | **CASE/COALESCE（PG）+ DECODE/NVL（Oracle 兼容）**——A 兼容模式下 DECODE 和 NVL 可直接使用。对比 PostgreSQL（无 DECODE/NVL）和 Oracle（DECODE/NVL 原生），openGauss 的兼容模式降低了 Oracle 迁移中条件函数的改写工作。 |
| [日期函数](../functions/date-functions/opengauss.md) | **PG 兼容 + Oracle 兼容日期函数**——PG 模式下 date_trunc/extract/age 标准，A 兼容模式下 TO_DATE/TO_CHAR/ADD_MONTHS 可用。对比 PostgreSQL（INTERVAL 运算灵活）和 Oracle（格式模型丰富），openGauss 按兼容模式切换日期函数行为。 |
| [数学函数](../functions/math-functions/opengauss.md) | **PG 兼容数学函数**——MOD/CEIL/FLOOR/ROUND/POWER/SQRT 完整。A 兼容模式下 TRUNC 可用于日期截断。对比 PostgreSQL（相同函数集）和 Oracle（TRUNC 双用途），openGauss 的数学函数在 PG 模式下与原生一致。 |
| [字符串函数](../functions/string-functions/opengauss.md) | **PG 兼容 + Oracle 兼容字符串函数**——PG 模式下 \|\| 拼接、substring/position 标准；A 兼容模式下 INSTR/SUBSTR/REPLACE 等 Oracle 函数可用。对比 PostgreSQL（\|\| 拼接标准）和 Oracle（\|\| 拼接 + ''=NULL），openGauss A 兼容模式下的空字符串行为需确认。 |
| [类型转换](../functions/type-conversion/opengauss.md) | **CAST/:: 运算符（PG）+ TO_NUMBER/TO_DATE（Oracle 兼容）**——PG 模式用 `col::integer` 简洁转换，A 兼容模式用 TO_NUMBER/TO_DATE/TO_CHAR 格式化转换。对比 PostgreSQL 的 ::（简洁独有）和 Oracle 的 TO_* 函数，openGauss 两套转换体系均可使用。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/opengauss.md) | **WITH + 递归 CTE（PG 兼容）**——递归 CTE 用于层级查询。A 兼容模式下 CONNECT BY 也可使用。对比 PostgreSQL（WITH RECURSIVE 原生）和 Oracle（CONNECT BY + WITH RECURSIVE），openGauss 在 CTE 上保持 PG 能力并可扩展。 |
| [全文搜索](../query/full-text-search/opengauss.md) | **tsvector/tsquery（PG 兼容）+ zhparser 中文分词**——继承 PG 全文搜索引擎，zhparser 扩展提供中文分词能力。对比 PostgreSQL（tsvector+GIN 最成熟）和 Elasticsearch（专用搜索引擎），openGauss 在中文全文搜索上通过 zhparser 填补了 PG 原生的中文短板。 |
| [连接查询](../query/joins/opengauss.md) | **JOIN（PG 兼容）+ LATERAL 支持**——完整的 INNER/LEFT/RIGHT/FULL/CROSS JOIN 和 LATERAL 子查询。列存表上 JOIN 可利用向量化执行加速。对比 PostgreSQL（LATERAL 原生）和 MySQL（LATERAL 8.0+ 支持），openGauss 的列存向量化 JOIN 是分析查询的性能增值。 |
| [分页](../query/pagination/opengauss.md) | **LIMIT/OFFSET（PG 兼容）**——标准分页语法。A 兼容模式下 ROWNUM 伪列也可使用。对比 PostgreSQL（LIMIT/OFFSET 标准）和 Oracle（ROWNUM + FETCH FIRST），openGauss 按模式提供不同分页方式。 |
| [行列转换](../query/pivot-unpivot/opengauss.md) | **crosstab（PG 兼容 tablefunc）**——通过 tablefunc 扩展实现行列转换。对比 PostgreSQL（需安装 tablefunc 扩展）和 Oracle（PIVOT 原生 11g+），openGauss 与 PG 方案一致，无原生 PIVOT 语法。 |
| [集合操作](../query/set-operations/opengauss.md) | **UNION/INTERSECT/EXCEPT（PG 兼容）**——ALL/DISTINCT 修饰符完整。A 兼容模式下 MINUS 关键字也可用。对比 PostgreSQL（EXCEPT 标准）和 Oracle（MINUS 传统），openGauss 按模式接受不同关键字。 |
| [子查询](../query/subquery/opengauss.md) | **关联子查询（PG 兼容）**——继承 PG 优化器的子查询展开能力。列存表上子查询可利用列式扫描减少 I/O。对比 PostgreSQL（优化器成熟）和 MySQL 8.0（子查询优化大幅改善），openGauss 的列存加速是子查询性能的独特优势。 |
| [窗口函数](../query/window-functions/opengauss.md) | **完整窗口函数（PG 兼容）**——ROW_NUMBER/RANK/DENSE_RANK/NTILE/LAG/LEAD + ROWS/RANGE 帧。列存表上窗口函数可利用向量化执行加速分析查询。对比 PostgreSQL（窗口函数完整）和 Oracle（功能对等），openGauss 在窗口函数计算上有列存加速优势。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/opengauss.md) | **generate_series（PG 兼容）**——生成日期序列并 LEFT JOIN 填充缺失值，方案与 PostgreSQL 完全一致。对比 PostgreSQL（generate_series 原生）和 BigQuery（GENERATE_DATE_ARRAY），openGauss 继承了 PG 的日期生成方式。 |
| [去重](../scenarios/deduplication/opengauss.md) | **DISTINCT ON / ROW_NUMBER（PG 兼容）**——DISTINCT ON 是 PG 独有的简洁去重语法，一行完成保留每组第一条记录。对比 PostgreSQL（DISTINCT ON 原创）和 Oracle（需 ROW_NUMBER 子查询），openGauss 继承了 PG 这一生产力特性。 |
| [区间检测](../scenarios/gap-detection/opengauss.md) | **generate_series + 窗口函数**——生成完整序列与实际数据对比检测缺失值和间隙。对比 PostgreSQL（相同方案）和 Oracle（CONNECT BY 生成序列），openGauss 的方案与 PG 一致。 |
| [层级查询](../scenarios/hierarchical-query/opengauss.md) | **递归 CTE（PG）+ CONNECT BY（Oracle 兼容）**——A 兼容模式下支持 CONNECT BY PRIOR 语法，PG 模式用 WITH RECURSIVE。对比 PostgreSQL（仅递归 CTE）和 Oracle（CONNECT BY + 递归 CTE），openGauss 在 A 兼容模式下提供 Oracle 层级查询能力。 |
| [JSON 展开](../scenarios/json-flatten/opengauss.md) | **json_each/json_array_elements（PG 兼容）**——JSONB 配合 GIN 索引实现高效 JSON 查询和展开。对比 PostgreSQL（JSONB+GIN 最成熟）和 Oracle 的 JSON_TABLE（SQL 标准），openGauss 继承 PG 的 JSONB 能力。 |
| [迁移速查](../scenarios/migration-cheatsheet/opengauss.md) | **PG 兼容 + Oracle 兼容 + 国产安全认证是核心差异**。关键注意：基于 PG 9.2 内核分叉，部分 PG 新版特性缺失；MOT 内存表有功能限制；Ustore 与 Astore 行为差异需评估；三权分立和数据脱敏是安全增值特性。 |
| [TopN 查询](../scenarios/ranking-top-n/opengauss.md) | **ROW_NUMBER + LIMIT（PG 兼容）**——标准 TopN 方案与 PG 一致。列存表上 TopN 查询可利用向量化扫描加速。对比 PostgreSQL（相同方案）和 BigQuery（QUALIFY 更简洁），openGauss 的列存加速是 TopN 性能增值。 |
| [累计求和](../scenarios/running-total/opengauss.md) | **SUM() OVER(ORDER BY ...)** 标准窗口累计，PG 兼容。列存向量化执行可加速大表分析。对比各主流引擎写法一致。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/opengauss.md) | **ON CONFLICT（PG）+ MERGE（Oracle 兼容）**——PG 模式用 ON CONFLICT 实现 SCD Type 1，A 兼容模式用 MERGE 实现 SCD Type 1/2。对比 PostgreSQL（仅 ON CONFLICT）和 Oracle（仅 MERGE），openGauss 提供双路径维度维护。 |
| [字符串拆分](../scenarios/string-split-to-rows/opengauss.md) | **string_to_array + unnest（PG 兼容）**——一行拆分字符串为多行，方案与 PostgreSQL 一致。对比 PostgreSQL（相同方案）和 Oracle（CONNECT BY + REGEXP_SUBSTR），openGauss 继承 PG 简洁拆分方式。 |
| [窗口分析](../scenarios/window-analytics/opengauss.md) | **完整窗口函数（PG 兼容）**——移动平均、同环比、占比计算全覆盖。列存引擎的向量化执行对分析型窗口计算有显著加速。对比 PostgreSQL（功能对等）和 Oracle（功能对等），openGauss 的列存加速是窗口分析的性能差异化优势。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/opengauss.md) | **ARRAY / 复合类型（PG 兼容）**——支持数组列和 CREATE TYPE 自定义复合类型。对比 PostgreSQL（ARRAY 原生核心特性）和 MySQL（无 ARRAY 列类型），openGauss 继承了 PG 的类型系统灵活性。 |
| [日期时间](../types/datetime/opengauss.md) | **DATE/TIMESTAMP/INTERVAL（PG 兼容）**——DATE 仅日期（PG 语义），INTERVAL 支持灵活的日期算术。A 兼容模式下 DATE 行为可能包含时间部分（对齐 Oracle）。对比 PostgreSQL（DATE 仅日期）和 Oracle（DATE 含时间），openGauss 的 DATE 行为取决于兼容模式设置。 |
| [JSON](../types/json/opengauss.md) | **JSON/JSONB + GIN 索引（PG 兼容）**——JSONB 二进制存储支持高效路径查询。注意基于 PG 9.2 分叉，部分较新的 JSONB 函数可能需要确认支持情况。对比 PostgreSQL（JSONB 功能最完整）和 Oracle（JSON 类型较新），openGauss 的 JSONB 能力取决于内核版本同步程度。 |
| [数值类型](../types/numeric/opengauss.md) | **INTEGER/NUMERIC（PG 兼容）**——INT/BIGINT/NUMERIC(p,s)/FLOAT/DOUBLE PRECISION 标准类型体系。A 兼容模式下 NUMBER(p,s) 也可用。对比 PostgreSQL（NUMERIC 任意精度）和 Oracle（NUMBER 统一类型），openGauss 按模式接受不同类型名。 |
| [字符串类型](../types/string/opengauss.md) | **TEXT/VARCHAR（PG 兼容）**——TEXT 无长度限制（推荐），VARCHAR(n) 指定最大长度。A 兼容模式下 VARCHAR2 也可用。对比 PostgreSQL（TEXT 推荐）和 Oracle（VARCHAR2 推荐），openGauss 的字符串类型随兼容模式适配。 |
