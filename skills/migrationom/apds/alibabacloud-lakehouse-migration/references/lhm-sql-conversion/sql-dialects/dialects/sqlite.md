# SQLite

**分类**: 嵌入式数据库
**文件数**: 51 个 SQL 文件
**总行数**: 6216 行

> **关键人物**：[D. Richard Hipp](../docs/people/richard-hipp.md)（SQLite 创始人, 公有领域）

## 概述与定位

SQLite 是全球部署量最大的数据库引擎，没有之一。每一部智能手机、每一个浏览器、每一个操作系统内核中都嵌入了 SQLite。保守估计全球活跃的 SQLite 数据库超过**万亿个** — 比所有其他数据库的总和多出几个数量级。

SQLite 的定位与 MySQL/PostgreSQL 完全不同：它不是客户端-服务器架构的"数据库服务"，而是一个**嵌入到应用程序进程中的 SQL 引擎**。没有独立的服务进程、没有网络协议、没有用户管理 — 数据库就是一个文件。这种极简主义使 SQLite 成为了"应用程序的文件格式"（官方定位），而非传统意义上的数据库服务器。

## 历史与演进

- **2000**: D. Richard Hipp 在 General Dynamics 为美国海军导弹驱逐舰项目开发 SQLite — 需求是一个不依赖 DBA 的嵌入式数据库
- **2001**: SQLite 1.0 使用 gdbm 作为后端存储
- **2004**: SQLite 3.0 — 完全重写，引入清单类型系统（manifest typing）、BLOB 支持、UTF-8/16
- **2010**: SQLite 3.7.0 — 引入 WAL（Write-Ahead Logging）模式，并发读性能飞跃
- **2013**: SQLite 被美国国会图书馆选为推荐的数字存档格式
- **2015**: SQLite 3.9.0 — 引入 JSON1 扩展和 FTS5（全文搜索第五代）
- **2018**: SQLite 3.25.0 — 引入窗口函数
- **2021**: SQLite 3.37.0 — 引入 STRICT 模式（可选的严格类型检查）
- **2022**: SQLite 3.39.0 — 引入 RIGHT JOIN 和 FULL OUTER JOIN
- **2023**: SQLite 3.41+ — JSONB 格式支持、数学函数内置化

SQLite 的许可模式独特：**公有领域（Public Domain）**。不是 MIT，不是 BSD，不是 GPL — 是完全放弃著作权。这意味着任何人可以用于任何目的，无需署名、无需开源、无任何限制。这是 SQLite 能被嵌入到所有商业产品中的关键原因。

## 核心设计思路

**极简主义**是 SQLite 的第一原则。整个引擎约 15 万行 C 代码（含注释约 20 万行），单一源文件编译（amalgamation），零外部依赖。与 PostgreSQL（约 150 万行）和 MySQL（约 400 万行）相比，SQLite 的代码量小了一到两个数量级。

**文件即数据库**：一个 SQLite 数据库就是一个跨平台的磁盘文件。可以用 `cp` 备份，用 U 盘传输，用 `rsync` 同步。文件格式保证向后兼容 — 2004 年创建的数据库文件在最新版本中仍可读写。

**动态类型**：SQLite 不强制列类型约束。你可以在 INTEGER 列中存入字符串，在 TEXT 列中存入数字。类型是值的属性而非列的属性。这与所有其他 SQL 数据库的静态类型系统根本不同。SQLite 使用**类型亲和性（Type Affinity）**规则决定如何存储值：INTEGER、REAL、TEXT、BLOB、NUMERIC 五种亲和性。

**无服务器**：没有独立的数据库服务进程，引擎直接链接到应用程序中。这消除了进程间通信开销，也消除了 DBA 的角色 — SQLite 的管理成本为零。

## 独特特色（其他引擎没有的）

- **动态类型 / 类型亲和性**：值的类型由值本身决定而非列定义。`CREATE TABLE t(x)` 不指定类型完全合法，x 列可以存储任意类型
- **`INTEGER PRIMARY KEY` = rowid**：声明为 `INTEGER PRIMARY KEY` 的列直接映射到 B-tree 的 rowid，无需额外索引，读写性能最优
- **`WITHOUT ROWID` 表**：覆盖索引式存储，适合复合主键且无需 rowid 的场景，减少存储开销
- **STRICT 模式（3.37+）**：`CREATE TABLE t(...) STRICT` 开启严格类型检查，不再允许类型混存。这是 SQLite 向传统数据库靠拢的可选安全网
- **FTS5 虚拟表**：内置的全文搜索引擎，支持 BM25 排序、前缀查询、近邻搜索，通过虚拟表接口透明集成
- **`ATTACH DATABASE`**：同一连接中挂载多个数据库文件，跨库查询 `SELECT * FROM db2.table1`。这是 SQLite 独有的多库能力
- **WAL 模式**：Write-Ahead Logging 允许并发读不阻塞写，写不阻塞读。性能提升巨大但仍限制为单写者
- **单文件部署**：整个数据库（Schema、数据、索引）存储在一个跨平台文件中，无需安装、配置、启停
- **公有领域许可**：世界上主流软件中少有的完全无版权限制的项目
- **`EXPLAIN` / `EXPLAIN QUERY PLAN`**：两种执行计划输出 — 底层字节码和人类可读的查询计划
- **虚拟表框架**：允许用 C 代码实现任意数据源的 SQL 查询接口（CSV 文件、操作系统信息、外部 API 等）
- **Authorizer API**：在 SQL 解析阶段逐语句审计和拦截，可以精确控制哪些操作被允许

## 已知的设计不足与历史包袱

- **单写者限制**：同一时刻只允许一个写事务。在 WAL 模式下读写可并发，但多写者仍需排队。这是 SQLite 最大的架构限制，也是它不适合高并发 Web 应用的根本原因
- **无 GRANT/REVOKE**：没有用户系统和权限管理。安全性完全依赖文件系统权限和 Authorizer API
- **无存储过程**：不支持服务端过程式编程（PL/SQL、PL/pgSQL 等）。逻辑必须在应用层实现
- **ALTER TABLE 能力弱**：3.35 前不支持 `DROP COLUMN`，至今不支持修改列类型、修改列名的某些场景。复杂表结构变更需要"建新表→拷贝数据→删旧表→重命名"的标准流程
- **无原生 DECIMAL 类型**：没有精确小数类型。`DECIMAL(10,2)` 语法被接受但实际存储为 REAL（浮点数），金融计算需要用整数（分为单位）或字符串
- **3.39 前无 RIGHT/FULL JOIN**：直到 2022 年才支持 RIGHT JOIN 和 FULL OUTER JOIN，之前只能通过调换表顺序或 UNION 模拟
- **无 LATERAL**：不支持 LATERAL JOIN / LATERAL 子查询
- **并发连接有限**：进程级文件锁限制了并发度，网络文件系统（NFS）上的 SQLite 行为不可靠
- **无 ALTER COLUMN**：不能修改已有列的类型或约束
- **日期时间无原生类型**：日期存储为 TEXT（ISO 8601）、REAL（Julian Day）或 INTEGER（Unix 时间戳），靠函数库处理

## 兼容生态

SQLite 的兼容生态围绕"分布式化"和"OLAP 化"两个方向：
- **DuckDB**：嵌入式 OLAP 引擎，被称为"分析领域的 SQLite"。SQL 方言高度接近 PostgreSQL 但部署模式像 SQLite，可以直接读取 SQLite 文件
- **Turso / libSQL**：SQLite 的分叉，增加了服务器模式、复制、多写者支持，将 SQLite 从嵌入式推向边缘计算
- **LiteFS**（Fly.io）：基于 FUSE 的 SQLite 复制方案，将 SQLite 用于分布式部署
- **rqlite**：基于 Raft 共识的分布式 SQLite
- **Litestream**：SQLite 的连续增量备份到 S3
- **cr-sqlite**：基于 CRDT 的多主 SQLite 复制

这个生态说明了一个趋势：**SQLite 正在从"嵌入式小数据库"扩展到"边缘计算和分布式场景的基础组件"**。

## 对引擎开发者的参考价值

- **类型亲和性系统**：SQLite 的五级亲和性（INTEGER/REAL/TEXT/BLOB/NUMERIC）和类型推断规则是动态类型 SQL 引擎的参考实现。如何在灵活性和安全性之间取舍，SQLite 给出了一个极端答案
- **B-tree 页面格式**：SQLite 的文件格式是数据库存储引擎的教科书案例 — 页面头、单元格指针、溢出页、自由链表，所有细节在官方文档中完全公开
- **WAL 实现**：Write-Ahead Log 的单文件实现，支持 checkpoint、busy-timeout、WAL 索引的共享内存映射。是理解 WAL 机制的最简洁参考
- **Authorizer API**：在 SQL 编译阶段逐操作授权检查的回调机制。这种设计允许宿主应用精确控制 SQL 能力（例如禁止 DELETE、只允许 SELECT 特定表），对多租户嵌入式场景极有价值
- **虚拟表框架**：通过 `xConnect/xBestIndex/xFilter` 等回调接口将任意数据源包装为 SQL 可查询的表。FTS5、JSON、CSV 都基于此框架实现，是可扩展查询引擎的设计模板
- **测试策略**：SQLite 拥有 1 亿行测试代码（测试代码量是产品代码的 600 倍以上），覆盖率达到 100% MC/DC。这是数据库引擎质量保证的极致标杆

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/sqlite.md) | **动态类型是 SQLite 最独特的设计**——类型是值的属性而非列的属性，INTEGER 列可存字符串。`INTEGER PRIMARY KEY` 直接映射 B-tree rowid（读写性能最优）。STRICT 模式(3.37+) 可选启用严格类型检查（向传统数据库靠拢）。WITHOUT ROWID 覆盖索引式存储适合复合主键场景。对比 PG/MySQL 等静态类型系统完全不同。 |
| [改表](../ddl/alter-table/sqlite.md) | **ALTER TABLE 能力严重受限**——3.35 前不支持 DROP COLUMN，至今无 ALTER COLUMN TYPE/RENAME COLUMN（部分支持）。复杂变更需"建新表→拷贝数据→删旧表→重命名"标准流程。对比 PG 的 DDL 事务性可回滚、MySQL 的 Online DDL（INSTANT/INPLACE/COPY），SQLite 的 ALTER 是主流数据库中最弱的。 |
| [索引](../ddl/indexes/sqlite.md) | **B-tree 索引是唯一的索引类型**——无 GiST/GIN/BRIN（PG 独有）、无 Bitmap（Oracle 独有）、无 Columnstore（SQL Server 独有）。部分索引 `WHERE condition` 支持（与 PG 相同）。表达式索引(3.9+) 可索引计算列。索引在文件级与表共存，简洁但功能有限。 |
| [约束](../ddl/constraints/sqlite.md) | **CHECK/UNIQUE/NOT NULL 约束支持完整**——但外键需 `PRAGMA foreign_keys=ON` 手动启用（默认关闭，这是历史兼容性决定）。对比 PG/Oracle/MySQL（外键默认强制执行）和 BigQuery/Snowflake（约束 NOT ENFORCED 仅作提示），SQLite 外键默认关闭是独特设计。 |
| [视图](../ddl/views/sqlite.md) | **普通视图支持，无物化视图**——需用触发器+表手动模拟物化视图。INSTEAD OF 触发器可使视图可更新。对比 PG 的 REFRESH MATERIALIZED VIEW（手动刷新）、Oracle 的 Fast Refresh+Query Rewrite（最强实现）和 BigQuery 的自动增量刷新，SQLite 视图功能最基础。 |
| [序列与自增](../ddl/sequences/sqlite.md) | **INTEGER PRIMARY KEY 自动成为 rowid 别名**——无需额外自增机制（自带 rowid 分配）。AUTOINCREMENT 关键字可选——保证单调递增（不复用已删除的 ID），但有轻微性能开销。无独立 SEQUENCE 对象（对比 PG/Oracle/MariaDB 均有）。对比 MySQL 的 AUTO_INCREMENT 功能接近但实现不同。 |
| [数据库/Schema/用户](../ddl/users-databases/sqlite.md) | **无用户系统、无 GRANT/REVOKE**——安全性完全依赖文件系统权限。Authorizer API 在 SQL 解析阶段逐操作审计和拦截（可精确控制允许的操作，对多租户嵌入式场景极有价值）。ATTACH DATABASE 独有——同一连接挂载多个数据库文件跨库查询 `db2.table1`。对比所有服务端数据库的用户权限模型。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/sqlite.md) | **无服务端动态 SQL**——SQLite 无存储过程和过程式语言，所有动态 SQL 由宿主语言（C/Python/Java）构建和执行。对比 PG 的 EXECUTE format()、Oracle 的 EXECUTE IMMEDIATE、MySQL 的 PREPARE/EXECUTE——SQLite 将所有逻辑推到应用层，这是嵌入式定位的必然选择。 |
| [错误处理](../advanced/error-handling/sqlite.md) | **无过程式错误处理**——错误码（SQLITE_CONSTRAINT、SQLITE_BUSY 等）由 C API 返回，应用层处理。无 TRY/CATCH、无 EXCEPTION WHEN、无 DECLARE HANDLER。对比 PG/Oracle/SQL Server 丰富的过程式错误处理，SQLite 的错误处理完全在应用层——与嵌入式定位一致。 |
| [执行计划](../advanced/explain/sqlite.md) | **EXPLAIN QUERY PLAN 提供人类可读的查询计划树**——显示扫描类型（SCAN/SEARCH）、使用的索引、连接顺序。EXPLAIN 显示底层虚拟机字节码（SQLite 将 SQL 编译为字节码执行，独有架构）。对比 PG 的 EXPLAIN ANALYZE（更详细含实际行数/耗时）和 SQL Server 的图形化执行计划。 |
| [锁机制](../advanced/locking/sqlite.md) | **文件级锁有 5 种状态（UNLOCKED→SHARED→RESERVED→PENDING→EXCLUSIVE）**——精细控制并发读写。WAL 模式下读写可并发（写不阻塞读），但**单写者是架构限制**——同一时刻只允许一个写事务。对比 PG/MySQL 的行级锁支持高并发写入，SQLite 不适合多写者场景。 |
| [分区](../advanced/partitioning/sqlite.md) | **无内置分区支持**——ATTACH DATABASE 可模拟分库（挂载多个数据库文件，按时间或业务拆分）。对比 PG 的声明式分区（RANGE/LIST/HASH）、MySQL 的分区表、BigQuery 的自动分区裁剪——SQLite 的"分区"完全靠应用层文件管理实现。 |
| [权限](../advanced/permissions/sqlite.md) | **无 GRANT/REVOKE 权限系统**——安全性依赖文件系统权限（谁能读写文件谁就有全部权限）。**Authorizer API 是精细权限控制的独有方案**——注册回调函数，在 SQL 编译阶段逐操作审计（可禁止 DELETE、只允许 SELECT 特定表等）。对比所有服务端数据库的 SQL 级权限模型。 |
| [存储过程](../advanced/stored-procedures/sqlite.md) | **无存储过程——逻辑完全在应用层实现**。可通过 C API 注册自定义函数（sqlite3_create_function）扩展 SQL 能力——FTS5、JSON 函数都基于此机制。宏（MACRO，DuckDB 概念）在 SQLite 中不存在。对比 PG 的 PL/pgSQL 多语言过程、Oracle 的 PL/SQL Package——SQLite 将复杂逻辑推到应用层是设计哲学。 |
| [临时表](../advanced/temp-tables/sqlite.md) | **CREATE TEMP TABLE 存储在临时文件**——连接级可见，连接关闭自动销毁。临时数据库可通过 `PRAGMA temp_store=MEMORY` 存在内存中。对比 PG 的 ON COMMIT DROP/DELETE ROWS 选项和 SQL Server 的 #temp/#\#temp 双级别临时表（存 tempdb），SQLite 临时表最简单直接。 |
| [事务](../advanced/transactions/sqlite.md) | **文件级锁 + WAL 模式是 SQLite 事务的核心**——BEGIN IMMEDIATE 在开始时获取写锁避免死锁（默认 BEGIN DEFERRED 延迟获取可能死锁）。**单写者是最大限制**——多线程并发写入必须排队。对比 PG 的 MVCC 行级锁、MySQL 的 InnoDB 行锁——SQLite 的并发模型只适合读多写少场景。 |
| [触发器](../advanced/triggers/sqlite.md) | **BEFORE/AFTER/INSTEAD OF 触发器功能完整**——FOR EACH ROW 行级触发器（无语句级触发器，对比 PG/Oracle 支持语句级）。INSTEAD OF 触发器使视图可更新。无 DDL 触发器/事件触发器（对比 PG 9.3+ 的 Event Trigger）。触发器是 SQLite 中实现业务逻辑的主要数据库端手段。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/sqlite.md) | **DELETE + LIMIT 是非标准但实用的扩展**——分批删除避免长时间持有写锁（对比 MySQL 同样支持 DELETE LIMIT）。无 TRUNCATE 语句（用 `DELETE FROM t` 替代，SQLite 会优化为快速路径）。无 RETURNING 子句（对比 PG 的 DELETE...RETURNING）。对比 Oracle 的 Flashback Table（误删恢复）。 |
| [插入](../dml/insert/sqlite.md) | **INSERT OR REPLACE/IGNORE 是 SQLite 独有的冲突处理语法**——OR REPLACE 在冲突时先删后插（注意会触发 DELETE 触发器），OR IGNORE 静默跳过冲突行。批量 INSERT `INSERT INTO t VALUES (...), (...), ...` 支持。无 RETURNING 子句（对比 PG 的 INSERT...RETURNING 一步获取自增 ID）。对比 MySQL 的 LOAD DATA INFILE（批量导入更快）。 |
| [更新](../dml/update/sqlite.md) | **UPDATE + LIMIT 非标准但支持**——限制更新行数避免长事务。UPDATE FROM(3.33+) 多表更新——`UPDATE t1 SET col=t2.val FROM t2 WHERE t1.id=t2.id`（与 PG 语法相同）。对比 MySQL 的 UPDATE JOIN（语法不同）和 Oracle 的 MERGE（功能更强）。SQLite 的 UPDATE 功能在 3.33+ 后接近主流水平。 |
| [Upsert](../dml/upsert/sqlite.md) | **ON CONFLICT DO UPDATE(3.24+) 是标准 UPSERT 方案**——语法与 PG 9.5+ 的 ON CONFLICT 相同。旧方案 INSERT OR REPLACE 会先删后插（重置 rowid、触发 DELETE 触发器，副作用多——应优先使用 ON CONFLICT）。对比 MySQL 的 ON DUPLICATE KEY UPDATE 和 Oracle/SQL Server 的 MERGE。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/sqlite.md) | **基础聚合函数完整**——SUM/AVG/COUNT/MIN/MAX/GROUP_CONCAT 均支持。无 GROUPING SETS/CUBE/ROLLUP（对比 PG/Oracle/SQL Server 完整支持多维聚合）。无 FILTER 子句（对比 PG 的条件聚合语法）。GROUP_CONCAT 无截断问题（对比 MySQL 默认 1024 字节截断）。 |
| [条件函数](../functions/conditional/sqlite.md) | **CASE/COALESCE/NULLIF/IIF(3.32+) 标准支持**——IIF(cond, true_val, false_val) 在 3.32+ 引入（与 SQL Server 的 IIF 相同）。无布尔类型——条件表达式返回 0/1 整数。对比 PG 的原生布尔类型和 MySQL 的 IF() 函数（更早）。动态类型下条件函数的类型推断更灵活。 |
| [日期函数](../functions/date-functions/sqlite.md) | **date()/time()/strftime() 函数族处理日期但无原生日期类型**——日期存储为 TEXT（ISO 8601）、REAL（Julian Day）或 INTEGER（Unix 时间戳），靠函数解析和计算。对比 PG 的 DATE/TIMESTAMP/INTERVAL（原生类型+丰富运算）和 BigQuery 的四种时间类型严格区分——SQLite 的日期处理是最灵活也最无约束的。 |
| [数学函数](../functions/math-functions/sqlite.md) | **内置数学函数(3.35+) 是较新添加**——之前 abs() 和 random() 是仅有的内置数学函数，其他需加载 math 扩展。3.35+ 内置 sin/cos/log/exp/pow 等标准函数。无 DECIMAL 精确运算（所有浮点计算使用 IEEE 754 双精度）。对比 PG 的 NUMERIC 任意精度和 Oracle 的 NUMBER 十进制精确。 |
| [字符串函数](../functions/string-functions/sqlite.md) | **`\|\|` 拼接标准**（与 PG/Oracle 相同，对比 MySQL 中 `\|\|` 是逻辑 OR）。SUBSTR/INSTR/LENGTH/REPLACE 基础函数完整。**无内置正则表达式**（需加载 REGEXP 扩展，对比 PG 的 regexp_match/replace 和 MySQL 的 REGEXP 内置）。LIKE 大小写不敏感（默认 ASCII，需 COLLATE NOCASE 或 ICU 扩展支持 Unicode）。 |
| [类型转换](../functions/type-conversion/sqlite.md) | **CAST 支持但动态类型下隐式转换极宽松**——`'123' + 0` 自动转数字、数字自动转字符串。无 TRY_CAST（对比 SQL Server/BigQuery 的安全转换）。类型亲和性规则（INTEGER/REAL/TEXT/BLOB/NUMERIC）决定存储格式。对比 PG 的严格类型（不做隐式转换）——SQLite 处于另一个极端。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/sqlite.md) | **递归 CTE(3.8.3+) 是标准实现**——SQLite 日期填充、层级查询、字符串拆分等场景都依赖递归 CTE（因为缺少 generate_series 等辅助函数）。性能良好——SQLite 优化器虽简单但对递归 CTE 处理高效。对比 PG 的可写 CTE（独有）和 MySQL 8.0 的 CTE（功能接近但来得晚）。 |
| [全文搜索](../query/full-text-search/sqlite.md) | **FTS5 虚拟表是嵌入式数据库中最强的全文搜索实现**——支持 BM25 排序算法、前缀查询、近邻搜索（NEAR）、自定义分词器。通过虚拟表接口透明集成——`SELECT * FROM fts_table WHERE fts_table MATCH 'query'`。对比 PG 的 tsvector+GIN（功能更强但配置更复杂）和 MySQL 的 InnoDB FULLTEXT（功能较基础）。 |
| [连接查询](../query/joins/sqlite.md) | **RIGHT JOIN 和 FULL OUTER JOIN 直到 3.39(2022) 才支持**——之前只有 LEFT JOIN 和 INNER JOIN。无 LATERAL JOIN / CROSS APPLY（对比 PG 9.3+ 的 LATERAL 和 SQL Server 2005 的 CROSS APPLY）。SQLite 的 JOIN 算法以 Nested Loop 为主（优化器简单但对小数据集足够），无 Hash Join/Merge Join。 |
| [分页](../query/pagination/sqlite.md) | **LIMIT/OFFSET 标准分页**——语法简洁高效。SQLite 的单文件单进程模型下分页性能稳定。无 FETCH FIRST WITH TIES（对比 PG 13+/SQL Server 的 TOP WITH TIES）。深分页性能问题相对较轻——SQLite 的 B-tree 直接定位效率高于客户端-服务器架构的网络开销。 |
| [行列转换](../query/pivot-unpivot/sqlite.md) | **无原生 PIVOT/UNPIVOT 语法**——需手写 CASE + GROUP BY 模拟（与 PG 相同）。JSON 函数可辅助动态列构建但不如原生 PIVOT 直观。对比 Oracle 11g/SQL Server/BigQuery/DuckDB 均有原生 PIVOT 语法——SQLite 在分析查询上功能有限，符合其嵌入式 OLTP 定位。 |
| [集合操作](../query/set-operations/sqlite.md) | **UNION/INTERSECT/EXCEPT 完整支持**——从早期版本即可用（对比 MySQL 直到 8.0.31 才支持 INTERSECT/EXCEPT）。支持 ALL 变体。SQLite 的集合操作实现虽简单但完整度不输主流数据库，是 SQLite 功能覆盖度较高的领域之一。 |
| [子查询](../query/subquery/sqlite.md) | **标量/表子查询支持完整，无 LATERAL 子查询**——优化器简单但够用：自动将子查询扁平化（flatten）为 JOIN。对比 PG 的 LATERAL 子查询（9.3+，高级用法）和 MySQL 5.x 子查询性能噩梦（8.0 修复）——SQLite 子查询优化中规中矩，对嵌入式场景的数据规模足够。 |
| [窗口函数](../query/window-functions/sqlite.md) | **3.25+(2018) 支持完整窗口函数集**——ROW_NUMBER/RANK/DENSE_RANK/NTILE/LAG/LEAD/FIRST_VALUE/LAST_VALUE/NTH_VALUE。ROWS/RANGE/GROUPS(3.28+) 三种帧类型均支持。无 QUALIFY 子句（对比 BigQuery/Snowflake/DuckDB）。无 FILTER 子句（对比 PG）。对 SQLite 的嵌入式定位而言窗口函数覆盖度很高。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/sqlite.md) | **无 generate_series，需递归 CTE 生成日期序列**——`WITH RECURSIVE dates AS (SELECT '2024-01-01' AS d UNION ALL SELECT date(d,'+1 day') FROM dates WHERE d < '2024-12-31')` 是标准方案。对比 PG 的 generate_series（一行搞定）和 MariaDB 的 seq_1_to_N（最简洁），SQLite 日期填充方案较冗长。 |
| [去重](../scenarios/deduplication/sqlite.md) | **ROW_NUMBER+CTE 或 rowid 直接定位删除**——SQLite 的 rowid 是行的物理标识符，`DELETE FROM t WHERE rowid NOT IN (SELECT MIN(rowid) FROM t GROUP BY key)` 直接按物理行删除效率高。对比 PG 的 DISTINCT ON（最简写法）和 BigQuery/DuckDB 的 QUALIFY（无需子查询包装）。 |
| [区间检测](../scenarios/gap-detection/sqlite.md) | **窗口函数 LAG/LEAD(3.25+) 检测相邻行间隙**——3.25 前无窗口函数需用自连接模拟（可读性差）。递归 CTE 填充完整序列后 EXCEPT 实际数据也可检测缺失。对比 PG 的 generate_series+LEFT JOIN（最直观）和 Teradata 的 sys_calendar 系统日历表（独有）。 |
| [层级查询](../scenarios/hierarchical-query/sqlite.md) | **递归 CTE(3.8.3+) 是唯一的层级查询方案**——无 Oracle 的 CONNECT BY（更简洁的原创语法）、无 PG 的 ltree 扩展（路径运算）、无 SQL Server 的 hierarchyid 类型。SQLite 的递归 CTE 实现简洁高效，对嵌入式场景的层级数据处理足够。 |
| [JSON 展开](../scenarios/json-flatten/sqlite.md) | **json_each/json_tree 表值函数是 SQLite JSON 展开的核心**——`SELECT * FROM json_each('[1,2,3]')` 将 JSON 数组展开为行。json_tree 递归展开嵌套结构。JSONB(3.45+) 二进制格式提升查询性能。对比 PG 的 JSONB+GIN 索引（最强实现）和 BigQuery 的 JSON_QUERY_ARRAY+UNNEST。 |
| [迁移速查](../scenarios/migration-cheatsheet/sqlite.md) | **动态类型 + 无存储过程 + ALTER 受限是迁移核心差异**——从 SQLite 迁出时需为每列指定明确类型、将应用层逻辑迁移到存储过程、处理 ALTER TABLE 语法差异。从服务端数据库迁入 SQLite 需注意单写者限制、无用户权限、无外键默认强制执行。文件即数据库的部署模型与服务端完全不同。 |
| [TopN 查询](../scenarios/ranking-top-n/sqlite.md) | **ROW_NUMBER(3.25+) + CTE 是窗口函数时代的 TopN 方案**——3.25 前只能 ORDER BY + LIMIT（无法分组 TopN）。无 QUALIFY 子句（对比 BigQuery/DuckDB 无需子查询包装）。无 FETCH FIRST WITH TIES（对比 PG 13+/SQL Server 包含并列行）。 |
| [累计求和](../scenarios/running-total/sqlite.md) | **SUM() OVER(ORDER BY ...) 在 3.25+(2018) 引入**——之前 SQLite 无窗口函数，累计求和只能用关联子查询 `SELECT (SELECT SUM(amount) FROM t t2 WHERE t2.id <= t1.id)` 模拟（性能差）。对比 PG 8.4(2009) 起即支持——SQLite 窗口函数比 PG 晚近十年但实现完整。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/sqlite.md) | **无 MERGE 语句**——需用 INSERT OR REPLACE（先删后插，有副作用）或 ON CONFLICT DO UPDATE(3.24+，推荐) 模拟 SCD Type 1。Type 2 SCD 需应用层逻辑处理（插入新版本行+更新旧版本结束时间）。对比 Oracle 的 MERGE 多分支和 SQL Server 的 Temporal Tables（自动历史版本）。 |
| [字符串拆分](../scenarios/string-split-to-rows/sqlite.md) | **无原生字符串拆分函数**——json_each 可将 JSON 数组 `'["a","b","c"]'` 展开为行。也可用递归 CTE 逐字符解析（冗长）。对比 PG 14 的 string_to_table（一行搞定）、SQL Server 的 STRING_SPLIT 和 MySQL 同样无原生方案——SQLite 和 MySQL 在字符串拆分上同为最弱。 |
| [窗口分析](../scenarios/window-analytics/sqlite.md) | **3.25+ 窗口函数实现完整度令人惊讶**——ROWS/RANGE/GROUPS(3.28+) 三种帧类型均支持（GROUPS 帧仅 PG 和 SQLite 支持）。NTH_VALUE 支持。无 QUALIFY 子句、无 FILTER 子句。对嵌入式数据库而言窗口函数覆盖度极高，体现了 SQLite "小而全"的设计哲学。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/sqlite.md) | **无 ARRAY/STRUCT/MAP 原生类型**——JSON 字符串是唯一的复合数据表示方式。动态类型系统下列可存储任意类型但无结构约束。对比 PG 的原生 ARRAY+运算符、BigQuery 的 STRUCT/ARRAY 一等公民、DuckDB 的 LIST/STRUCT/MAP——SQLite 在复合类型上依赖 JSON 模拟。 |
| [日期时间](../types/datetime/sqlite.md) | **无原生日期类型——日期以 TEXT/REAL/INTEGER 三种方式存储**——TEXT 存 ISO 8601 字符串（人类可读）、REAL 存 Julian Day Number（精确计算）、INTEGER 存 Unix 时间戳（紧凑）。date()/strftime() 函数处理所有格式。对比 PG/MySQL/BigQuery 的原生日期类型——SQLite 的方案灵活但缺乏类型安全。 |
| [JSON](../types/json/sqlite.md) | **json_each/json_tree 表值函数是 SQLite JSON 处理的核心**——json_each 展开数组/对象，json_tree 递归遍历嵌套结构。JSONB(3.45+) 引入二进制 JSON 存储提升查询性能。json_patch 合并两个 JSON 对象。对比 PG 的 JSONB+GIN 索引（最强实现）和 MySQL 的 JSON（二进制存储+多值索引），SQLite 的 JSON 功能在嵌入式引擎中领先。 |
| [数值类型](../types/numeric/sqlite.md) | **INTEGER 和 REAL 是仅有的两种数值存储类**——INTEGER 可变长（1-8 字节自适应），REAL 是 IEEE 754 双精度浮点。**无原生 DECIMAL 精确类型**——金融计算需用 INTEGER（以分为单位）或字符串模拟。对比 PG 的 NUMERIC 任意精度、Oracle 的 NUMBER 十进制精确——SQLite 精确运算是最大缺失。 |
| [字符串类型](../types/string/sqlite.md) | **TEXT 类型无长度限制**——无 VARCHAR(n)/CHAR(n)/TEXT 区分（对比 MySQL 的 TEXT 有索引限制、PG 的 TEXT=VARCHAR 无差异但有 VARCHAR(n) 约束）。COLLATE NOCASE 实现大小写不敏感比较（默认区分大小写）。UTF-8 编码（也支持 UTF-16）。极简设计符合嵌入式定位。 |
