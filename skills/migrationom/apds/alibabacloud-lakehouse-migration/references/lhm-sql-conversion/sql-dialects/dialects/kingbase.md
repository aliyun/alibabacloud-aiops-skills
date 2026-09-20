# 人大金仓 (KingbaseES)

**分类**: 国产数据库（兼容 PostgreSQL/Oracle）
**文件数**: 51 个 SQL 文件
**总行数**: 5407 行

## 概述与定位

人大金仓（KingbaseES）是北京人大金仓信息技术股份有限公司研发的国产商业关系型数据库，基于 PostgreSQL 内核开发并大幅扩展。KingbaseES 的核心定位是同时兼容 PostgreSQL 和 Oracle 两种生态，帮助用户从 Oracle 或 PostgreSQL 平滑迁移。它是中国信创产业的核心数据库产品之一，在政府、军工、金融、能源等安全敏感领域有广泛部署，特别强调安全合规能力。

## 历史与演进

- **1999 年**：中国人民大学数据库研究团队启动金仓数据库项目。
- **2003 年**：人大金仓公司成立，产品化开发加速。
- **2008 年**：KingbaseES V6 通过国家信息安全认证。
- **2012 年**：V7 引入 Oracle 兼容模式增强。
- **2017 年**：V8 基于 PostgreSQL 9.6 内核重构，大幅提升 PG/Oracle 双兼容能力。
- **2020 年**：随信创政策推动，市场份额快速增长。
- **2022-2025 年**：持续增强分布式能力、安全特性和 ARM 平台支持。

## 核心设计思路

KingbaseES 基于 PostgreSQL 内核深度改造，核心设计目标是**双模兼容**——在 PG 兼容的基础上额外提供 Oracle 兼容层。通过设置 `ora_compatible` 参数可在 PG 模式和 Oracle 模式之间切换，Oracle 模式下支持 PL/SQL（KES PL/SQL 方言）、Package、同义词和 Oracle 风格数据字典。安全方面实现了**三权分立**（系统管理员、安全管理员、审计管理员权限分离）和**强制访问控制**（MAC），满足国家等级保护要求。

## 独特特色

- **PG/Oracle 双模兼容**：通过兼容模式开关，同一内核支持 PostgreSQL 和 Oracle 两套 SQL 方言。
- **三权分立安全模型**：系统管理员（sso）、安全管理员（sao）、审计管理员（aud）权限完全分离，防止权限滥用。
- **强制访问控制 (MAC)**：支持基于安全标签的行级强制访问控制，满足国家等级保护三级/四级要求。
- **PL/SQL 兼容**：Oracle 模式下支持 Package、Cursor、动态 SQL、异常处理等 PL/SQL 核心特性。
- **透明数据加密 (TDE)**：支持表空间级和列级透明加密。
- **国密算法支持**：内置 SM2/SM3/SM4 国密加密算法。
- **审计增强**：细粒度审计到语句级别，支持审计策略的灵活配置。

## 已知不足

- 闭源商业软件，社区版功能受限，开发者获取和试用不够便捷。
- Oracle 兼容模式覆盖面有限，复杂 PL/SQL 程序（特别是高级包和类型）迁移可能需要调整。
- 基于较早版本 PostgreSQL 分叉，部分 PG 新版本特性缺失。
- 国际化程度低，文档和技术支持以中文为主。
- 性能调优和监控工具成熟度与 PostgreSQL 原生生态有差距。
- 分布式方案的成熟度相比专门的分布式数据库有待提升。

## 对引擎开发者的参考价值

KingbaseES 的 PG/Oracle 双模兼容实现展示了在同一查询引擎内通过兼容模式开关适配不同 SQL 方言的工程方法。其三权分立安全模型和强制访问控制（MAC）的实现对数据库安全子系统设计有直接参考意义——这些安全特性在商用数据库中并不常见但在政企场景中至关重要。在 PG 内核上叠加 Oracle 兼容层的实践也为理解数据库内核扩展提供了一个有价值的案例。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/kingbase.md) | **PG/Oracle 双模兼容建表**——通过 `ora_compatible` 参数切换模式，PG 模式下 TEXT/VARCHAR/SERIAL 标准语法，Oracle 模式下 NUMBER/VARCHAR2/CHAR 类型可用。IDENTITY 和 SERIAL 均支持自增。对比 PostgreSQL（原生语法）和达梦（偏向 Oracle），金仓是唯一同时覆盖 PG 和 Oracle 建表语法的国产数据库。 |
| [改表](../ddl/alter-table/kingbase.md) | **PG 兼容 ALTER 语法 + Oracle 模式 DDL**。PG 模式下 DDL 可在事务中回滚（继承 PG 优势），Oracle 模式下 DDL 自动提交。对比 PostgreSQL（DDL 事务性是核心优势）和 Oracle（DDL 自动提交），金仓根据模式切换行为，迁移双方代码均可适配。 |
| [索引](../ddl/indexes/kingbase.md) | **B-tree/GIN/GiST（PG 继承）+ 位图索引（Oracle 兼容）**——GIN 索引加速全文搜索和 JSONB 查询，GiST 支持几何/范围类型，位图索引适合低基数列分析。对比 PostgreSQL（GIN/GiST 是核心竞争力）和 Oracle（位图索引成熟），金仓合并了两个生态的索引类型优势。 |
| [约束](../ddl/constraints/kingbase.md) | **PK/FK/CHECK/UNIQUE 完整 + 延迟约束**（DEFERRABLE），继承 PostgreSQL 的约束体系。Oracle 模式下约束语法也可用。对比 PostgreSQL（延迟约束原生支持）和 MySQL InnoDB（不支持延迟约束），金仓在约束能力上对齐 PG 水平。 |
| [视图](../ddl/views/kingbase.md) | **物化视图 + REFRESH CONCURRENTLY**——并发刷新时不阻塞查询（PG 9.4+ 特性继承）。Oracle 模式下可用 Oracle 风格的物化视图语法。对比 PostgreSQL（REFRESH MATERIALIZED VIEW CONCURRENTLY 原生）和 Oracle（REFRESH FAST 增量），金仓在物化视图上保持 PG 能力。 |
| [序列与自增](../ddl/sequences/kingbase.md) | **SEQUENCE/SERIAL/IDENTITY 三种自增方式**——SERIAL（PG 传统）、IDENTITY（SQL 标准/PG 10+）、SEQUENCE（Oracle 兼容）。Oracle 模式下 CURRVAL/NEXTVAL 伪列可用。对比 PostgreSQL（SERIAL 和 IDENTITY）和 Oracle（SEQUENCE + CURRVAL/NEXTVAL），金仓在 ID 生成策略上覆盖最广。 |
| [数据库/Schema/用户](../ddl/users-databases/kingbase.md) | **PG 兼容权限体系 + 三权分立安全模型**——系统管理员(sso)、安全管理员(sao)、审计管理员(aud) 职责分离。Schema 与用户解耦（继承 PG 设计）。对比 PostgreSQL（无三权分立）和达梦（三权分立 + Schema=用户），金仓在 PG 灵活性基础上叠加了等保安全要求。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/kingbase.md) | **PL/pgSQL EXECUTE + Oracle 模式 EXECUTE IMMEDIATE**——PG 模式下用 `EXECUTE format('SELECT %I ...', col)` 安全拼接，Oracle 模式下用 `EXECUTE IMMEDIATE sql_str USING bind_var`。对比 PostgreSQL（仅 EXECUTE）和 Oracle（仅 EXECUTE IMMEDIATE），金仓是唯一同时支持两种动态 SQL 语法的引擎。 |
| [错误处理](../advanced/error-handling/kingbase.md) | **EXCEPTION WHEN（PL/pgSQL）+ Oracle 模式异常处理**——PG 模式下捕获 SQLSTATE 异常码，Oracle 模式下支持 NO_DATA_FOUND/TOO_MANY_ROWS 等预定义异常。对比 PostgreSQL 的 EXCEPTION WHEN（PG 原生）和 Oracle 的 EXCEPTION WHEN（PL/SQL 原生），两种写法在金仓中均可用。 |
| [执行计划](../advanced/explain/kingbase.md) | **EXPLAIN ANALYZE（PG 兼容）**——显示实际执行时间、行数估计偏差和缓冲区使用。支持 FORMAT JSON/YAML 输出。对比 PostgreSQL（EXPLAIN ANALYZE 是行业标杆）和 Oracle 的 EXPLAIN PLAN + DBMS_XPLAN，金仓继承了 PG 的执行计划可读性优势。 |
| [锁机制](../advanced/locking/kingbase.md) | **MVCC（PG 多版本元组模型）+ 行级锁**——读不阻塞写，写不阻塞读。继承 PG 的锁类型（AccessShareLock 到 AccessExclusiveLock 8 级）。对比 PostgreSQL（相同模型）和 Oracle（Undo Log MVCC），金仓的 MVCC 实现与 PG 一致，需注意表膨胀和 VACUUM 管理。 |
| [分区](../advanced/partitioning/kingbase.md) | **声明式分区（PG 10+ 风格）**——RANGE/LIST/HASH 分区，支持多级子分区。对比 PostgreSQL（声明式分区原生）和 Oracle（分区功能最丰富），金仓的分区能力紧随 PG 内核版本演进。 |
| [权限](../advanced/permissions/kingbase.md) | **PG RBAC + 三权分立 + 强制访问控制（MAC）**——MAC 基于安全标签对行级数据进行强制分级访问，是满足等保三级/四级的核心能力。对比 PostgreSQL 的 RLS（行级安全，声明式策略）和 Oracle 的 VPD（Virtual Private Database），金仓的 MAC 是国产数据库中安全级别最高的实现之一。 |
| [存储过程](../advanced/stored-procedures/kingbase.md) | **PL/pgSQL + PL/SQL 双模式是金仓核心卖点**——PG 模式下编写 PL/pgSQL 存储过程，Oracle 模式下编写 PL/SQL 兼容过程，支持 Package（包头+包体）。对比 PostgreSQL（仅 PL/pgSQL，无 Package）和 Oracle（完整 PL/SQL），金仓在过程语言上是两个生态的桥梁。 |
| [临时表](../advanced/temp-tables/kingbase.md) | **CREATE TEMPORARY TABLE（PG 兼容）**——会话级或事务级临时表，事务结束后自动清理。Oracle 模式下可用 GTT 语法。对比 PostgreSQL（CREATE TEMP TABLE 标准）和 Oracle（CREATE GLOBAL TEMPORARY TABLE），金仓两种语法均可使用。 |
| [事务](../advanced/transactions/kingbase.md) | **MVCC + DDL 事务性（PG 核心优势保留）**——CREATE TABLE、ALTER TABLE 等 DDL 可在事务中回滚，这是 PG 相比 Oracle/MySQL 的重要优势。对比 PostgreSQL（DDL 事务性原生）和 Oracle（DDL 自动提交不可回滚），金仓保留了 PG 的事务安全特性。 |
| [触发器](../advanced/triggers/kingbase.md) | **BEFORE/AFTER/INSTEAD OF + 行级/语句级**——继承 PG 完整的触发器体系。Oracle 模式下触发器语法也可兼容。对比 PostgreSQL（触发器功能完整）和 MySQL（仅 BEFORE/AFTER 行级），金仓触发器能力对齐 PG。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/kingbase.md) | **DELETE ... RETURNING（PG 兼容）**——删除后立即返回被删除行的数据，无需额外查询。对比 PostgreSQL（RETURNING 是 PG 独创特性）和 Oracle（无 RETURNING on DELETE，需用 PL/SQL），金仓继承了 PG 这一生产力特性。 |
| [插入](../dml/insert/kingbase.md) | **INSERT ... RETURNING + ON CONFLICT Upsert**——RETURNING 返回新插入行数据（含自增 ID），ON CONFLICT 实现原子性 Upsert。对比 PostgreSQL（ON CONFLICT 原生）和 MySQL 的 ON DUPLICATE KEY UPDATE（功能类似但语法不同），金仓的 INSERT 能力完全对齐 PG。 |
| [更新](../dml/update/kingbase.md) | **UPDATE ... RETURNING + UPDATE FROM**——RETURNING 返回更新后数据，UPDATE FROM 支持多表关联更新（PG 扩展语法）。对比 PostgreSQL（相同能力）和 Oracle（需子查询或 MERGE），金仓的 UPDATE 灵活度继承 PG。 |
| [Upsert](../dml/upsert/kingbase.md) | **ON CONFLICT（PG 兼容）+ MERGE（Oracle 兼容）双路径**——PG 模式用 `INSERT ... ON CONFLICT (key) DO UPDATE`，Oracle 模式用 `MERGE INTO ... USING ... WHEN MATCHED/NOT MATCHED`。对比 PostgreSQL（仅 ON CONFLICT）和 Oracle（仅 MERGE），金仓在 Upsert 场景下迁移门槛最低。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/kingbase.md) | **string_agg（PG）/ LISTAGG（Oracle）双兼容 + GROUPING SETS/CUBE/ROLLUP**——PG 模式用 string_agg(col, ',')，Oracle 模式用 LISTAGG(col, ',') WITHIN GROUP (ORDER BY ...)。对比 PostgreSQL 的 string_agg（原生）和 Oracle 的 LISTAGG（原生），金仓同时支持两种字符串聚合函数。 |
| [条件函数](../functions/conditional/kingbase.md) | **CASE/COALESCE（PG 标准）+ DECODE/NVL（Oracle 模式）**——PG 模式下用 COALESCE(a, b) 处理 NULL，Oracle 模式下用 NVL(a, b) 和 DECODE(col, val1, res1, default)。对比 PostgreSQL（无 DECODE/NVL）和 Oracle（DECODE 是经典函数），金仓的条件函数同时覆盖两个生态。 |
| [日期函数](../functions/date-functions/kingbase.md) | **PG + Oracle 日期函数双兼容**——PG 模式用 date_trunc/extract/age，Oracle 模式用 TO_DATE/TO_CHAR/ADD_MONTHS/MONTHS_BETWEEN。对比 PostgreSQL（INTERVAL 运算灵活）和 Oracle（格式模型丰富），金仓在日期处理上无需改写迁移代码。 |
| [数学函数](../functions/math-functions/kingbase.md) | **PG 兼容数学函数**——MOD/CEIL/FLOOR/ROUND/TRUNC/POWER/SQRT 完整支持。Oracle 模式下 TRUNC 可用于日期截断（同 Oracle 双重用途）。对比 PostgreSQL（date_trunc 单独函数）和 Oracle（TRUNC 双用途），金仓按模式切换行为。 |
| [字符串函数](../functions/string-functions/kingbase.md) | **\|\| 拼接（SQL 标准/PG 兼容）+ Oracle 兼容函数**——SUBSTR/INSTR/REPLACE 等 Oracle 函数在 Oracle 模式下可用。PG 模式下用 substring/position/overlay。对比 PostgreSQL（\|\| 拼接，NULL 传播）和 Oracle（\|\| 拼接，''=NULL），金仓按模式决定空字符串行为。 |
| [类型转换](../functions/type-conversion/kingbase.md) | **CAST/:: 运算符（PG 兼容）+ TO_NUMBER/TO_DATE/TO_CHAR（Oracle 兼容）**——PG 模式用 `col::integer` 简洁转换，Oracle 模式用 `TO_NUMBER(str, 'FM999.99')` 格式化转换。对比 PostgreSQL 的 ::（简洁独有）和 Oracle 的 TO_* 函数（格式模型强大），金仓两套转换体系均可使用。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/kingbase.md) | **WITH + 递归 CTE（PG 兼容）**——递归 CTE 是 PG 层级查询的标准手段，Oracle 模式下可选用 CONNECT BY。对比 PostgreSQL（WITH RECURSIVE 原生）和 Oracle（CONNECT BY + WITH RECURSIVE），金仓在 CTE 层面继承 PG 全部能力。 |
| [全文搜索](../query/full-text-search/kingbase.md) | **tsvector/tsquery（PG 兼容）**——继承 PG 的全文搜索引擎，支持中文分词（需 zhparser/pg_jieba 扩展）。GIN 索引加速全文检索。对比 PostgreSQL（tsvector+GIN 是内置全文搜索最成熟方案）和 Oracle Text（功能更丰富但配置复杂），金仓的全文搜索能力与 PG 对等。 |
| [连接查询](../query/joins/kingbase.md) | **JOIN 完整 + LATERAL 支持**——LATERAL 允许子查询引用前面 FROM 项的列（PG 9.3+ 特性）。对比 PostgreSQL（LATERAL 原生）和 MySQL 8.0（LATERAL 后来支持），金仓继承了 PG 的 LATERAL 能力。Oracle 模式下 (+) 外连接语法也可兼容。 |
| [分页](../query/pagination/kingbase.md) | **LIMIT/OFFSET（PG）+ ROWNUM（Oracle 兼容）双模式**——PG 模式用标准 LIMIT/OFFSET，Oracle 模式下 ROWNUM 伪列可用。对比 PostgreSQL（LIMIT/OFFSET 标准）和 Oracle（ROWNUM + FETCH FIRST），金仓提供两种分页路径。 |
| [行列转换](../query/pivot-unpivot/kingbase.md) | **crosstab（PG 扩展）+ PIVOT（Oracle 兼容模式）**——PG 模式用 tablefunc 扩展的 crosstab 函数，Oracle 模式下可用 PIVOT/UNPIVOT 语法。对比 PostgreSQL（需安装 tablefunc 扩展）和 Oracle（PIVOT 原生 11g+），金仓在行列转换上提供双路径选择。 |
| [集合操作](../query/set-operations/kingbase.md) | **UNION/INTERSECT/EXCEPT（PG 兼容）**——ALL/DISTINCT 修饰符完整支持。Oracle 模式下 MINUS 关键字也可识别。对比 PostgreSQL（EXCEPT 标准）和 Oracle（MINUS 传统），金仓同时接受两种关键字。 |
| [子查询](../query/subquery/kingbase.md) | **关联子查询 + 优化器自动转换**——继承 PG 优化器的子查询展开（Subquery Flattening）能力。对比 PostgreSQL（优化器成熟）和 MySQL 8.0（子查询优化大幅改善），金仓的子查询优化水平紧随 PG 内核。 |
| [窗口函数](../query/window-functions/kingbase.md) | **完整窗口函数（PG 兼容）**——ROW_NUMBER/RANK/DENSE_RANK/NTILE/LAG/LEAD + ROWS/RANGE/GROUPS 帧。WINDOW 命名子句可复用窗口定义。对比 PostgreSQL（窗口函数完整）和 Oracle（功能对等），金仓在窗口函数上无功能差异。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/kingbase.md) | **generate_series（PG 兼容）**——`generate_series('2024-01-01'::date, '2024-12-31'::date, '1 day')` 生成日期序列并 LEFT JOIN 填充缺失日期。对比 PostgreSQL 的 generate_series（相同函数）和 BigQuery 的 GENERATE_DATE_ARRAY（类似但语法不同），金仓继承了 PG 最直观的日期生成方式。 |
| [去重](../scenarios/deduplication/kingbase.md) | **DISTINCT ON（PG 独有优势）+ ROW_NUMBER**——`SELECT DISTINCT ON (id) * FROM t ORDER BY id, ts DESC` 一行语句保留每组最新记录，比 ROW_NUMBER 子查询包装更简洁。对比 PostgreSQL（DISTINCT ON 原创）和 Oracle/MySQL（无 DISTINCT ON，需子查询），这是 PG 生态的生产力特性。 |
| [区间检测](../scenarios/gap-detection/kingbase.md) | **generate_series + 窗口函数**——生成完整序列与实际数据做 LEFT JOIN/EXCEPT 检测缺失值，LAG/LEAD 窗口函数检测不连续区间。对比 PostgreSQL（相同方案）和 Oracle（需 CONNECT BY 生成序列），金仓的方案继承 PG 简洁性。 |
| [层级查询](../scenarios/hierarchical-query/kingbase.md) | **递归 CTE（PG）+ CONNECT BY（Oracle 兼容模式）**——PG 模式用 `WITH RECURSIVE` 标准递归，Oracle 模式下 `START WITH ... CONNECT BY PRIOR` 语法可直接运行。对比 PostgreSQL（仅递归 CTE）和 Oracle（CONNECT BY 原生），金仓在层级查询上是唯一双路径的 PG 衍生数据库。 |
| [JSON 展开](../scenarios/json-flatten/kingbase.md) | **json_each/json_array_elements（PG 兼容）**——JSONB 类型配合 GIN 索引可高效查询和展开 JSON 数据。对比 PostgreSQL（JSONB+GIN 是 JSON 处理最强方案之一）和 Oracle 的 JSON_TABLE（SQL 标准），金仓继承了 PG 的 JSONB 生态优势。 |
| [迁移速查](../scenarios/migration-cheatsheet/kingbase.md) | **PG + Oracle 双兼容是核心卖点**——从 PG 迁移几乎零成本（内核兼容），从 Oracle 迁移通过 ora_compatible 模式降低改造量。关键差异：三权分立安全模型需额外配置、国密算法替代标准加密、部分 PG 新版特性可能缺失（取决于内核版本）。 |
| [TopN 查询](../scenarios/ranking-top-n/kingbase.md) | **ROW_NUMBER + LIMIT（PG 兼容）**——`SELECT * FROM (SELECT *, ROW_NUMBER() OVER(...) rn FROM t) WHERE rn <= N` 或直接 `ORDER BY ... LIMIT N`。对比 PostgreSQL（相同方案）和 BigQuery（QUALIFY 更简洁），金仓的 TopN 方案与 PG 一致。 |
| [累计求和](../scenarios/running-total/kingbase.md) | **SUM() OVER(ORDER BY ...)** 标准窗口累计，PG 兼容实现。语法和语义与所有主流引擎一致。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/kingbase.md) | **ON CONFLICT（PG）+ MERGE（Oracle 兼容）**——PG 模式用 `INSERT ... ON CONFLICT DO UPDATE` 实现 SCD Type 1，Oracle 模式用 `MERGE INTO` 实现 SCD Type 1/2。对比 PostgreSQL（仅 ON CONFLICT）和 Oracle（仅 MERGE），金仓在维度表维护上提供双路径。 |
| [字符串拆分](../scenarios/string-split-to-rows/kingbase.md) | **string_to_array + unnest（PG 兼容）**——`SELECT unnest(string_to_array('a,b,c', ','))` 一行拆分字符串为多行。对比 PostgreSQL（相同方案）和 BigQuery 的 SPLIT+UNNEST（类似），金仓继承了 PG 简洁的字符串拆分能力。 |
| [窗口分析](../scenarios/window-analytics/kingbase.md) | **完整窗口函数（PG 兼容）**——移动平均、同环比、占比、排名等分析场景全覆盖。WINDOW 命名子句减少重复定义。对比 PostgreSQL（功能对等）和 Oracle（功能对等），金仓在窗口分析上无功能差距。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/kingbase.md) | **ARRAY / 复合类型（PG 兼容）**——支持 `INTEGER[]` 数组列、CREATE TYPE 自定义复合类型。Oracle 模式下 VARRAY 也可兼容。对比 PostgreSQL（ARRAY 是核心特性）和 MySQL（无 ARRAY 列类型），金仓继承了 PG 的类型系统灵活性。 |
| [日期时间](../types/datetime/kingbase.md) | **DATE/TIMESTAMP/TIMESTAMPTZ/INTERVAL（PG 兼容）**——DATE 仅日期（不含时间，与 Oracle 不同！），INTERVAL 支持算术运算。Oracle 模式下 DATE 可包含时间部分。对比 PostgreSQL（DATE 仅日期）和 Oracle（DATE 含时间），金仓按模式切换 DATE 语义，迁移时需关注。 |
| [JSON](../types/json/kingbase.md) | **JSON/JSONB + GIN 索引（PG 兼容）**——JSONB 二进制存储支持高效路径查询和 GIN 索引加速。对比 PostgreSQL（JSONB 是 JSON 处理标杆）和 Oracle（JSON 存储为 OSON 格式），金仓的 JSONB 能力完整继承 PG，查询性能对等。 |
| [数值类型](../types/numeric/kingbase.md) | **INTEGER/NUMERIC（PG）+ NUMBER（Oracle 兼容）**——PG 模式下使用 INT/BIGINT/NUMERIC(p,s)，Oracle 模式下 NUMBER(p,s) 可用。对比 PostgreSQL（NUMERIC 任意精度）和 Oracle（NUMBER 统一数值类型），金仓根据模式接受不同的类型名。 |
| [字符串类型](../types/string/kingbase.md) | **TEXT/VARCHAR（PG）+ VARCHAR2（Oracle 兼容）**——PG 模式下 TEXT 无长度限制（推荐使用），Oracle 模式下 VARCHAR2(n) 可用。对比 PostgreSQL（TEXT 是推荐字符串类型）和 Oracle（VARCHAR2 是推荐类型），金仓的字符串类型随模式适配。 |
