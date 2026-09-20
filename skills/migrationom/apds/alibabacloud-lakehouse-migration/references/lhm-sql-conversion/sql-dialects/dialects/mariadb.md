# MariaDB

**分类**: MySQL 兼容分支
**文件数**: 51 个 SQL 文件
**总行数**: 4792 行

> **关键人物**：[Monty Widenius](../docs/people/monty-widenius.md)（MySQL/MariaDB 创始人）、[Sergei Golubchik](../docs/people/mariadb-community.md)（MariaDB 首席架构师）

## 概述与定位

MariaDB 是 MySQL 的社区驱动分叉，由 MySQL 原始创始人 Michael "Monty" Widenius 于 2009 年创建。它定位为 MySQL 的"增强型替代品"（drop-in replacement），在保持协议级和 SQL 级兼容的前提下，独立推进许多 MySQL 未能实现或推迟实现的特性。MariaDB 既适用于 OLTP 场景，也通过 ColumnStore 存储引擎涵盖分析型负载，形成了"一个内核、多引擎"的混合定位。

## 历史与演进

- **2009 年**：Monty 在 Oracle 收购 Sun/MySQL 之前启动 MariaDB 分叉，初始代码基于 MySQL 5.1。
- **2012 年**：MariaDB 5.5 成为第一个被多数 Linux 发行版默认采用的版本（替换 MySQL）。
- **2013 年**：10.0 引入多源复制（multi-source replication）与并行复制，开始与 MySQL 版本号脱钩。
- **2017 年**：10.2 支持窗口函数与 CTE，比 MySQL 8.0 更早交付。
- **2018 年**：10.3 引入 SEQUENCE 引擎、系统版本表（System-Versioned Tables）与 INTERSECT/EXCEPT。
- **2021 年**：10.5+ 引入 RETURNING 子句、INVISIBLE 列、IF NOT EXISTS 对更多语句的支持。
- **2023 年**：10.11 成为长期支持版本，引入 WITHOUT OVERLAPS 约束、UUID v7 函数。
- **2024-2025 年**：11.x 系列持续推进原子 DDL、向量索引预研、增强 JSON 表函数。

## 核心设计思路

1. **引擎可插拔**：InnoDB（默认）、Aria（崩溃安全 MyISAM 替代）、Spider（分片联邦）、ColumnStore（列存分析）、SEQUENCE（虚拟序列引擎）等多引擎共存。
2. **SQL 标准优先**：在 MySQL 滞后时率先实现标准语法——窗口函数、CTE、INTERSECT/EXCEPT、NATURAL FULL OUTER JOIN。
3. **向后兼容**：协议、复制格式与 MySQL 保持最大程度兼容，方便用户无缝切换。
4. **社区开放**：所有新特性默认贡献到开源主干；不存在仅商业版可用的功能。

## 独特特色

| 特性 | 说明 |
|---|---|
| **SEQUENCE 引擎（10.3+）** | `SELECT * FROM seq_1_to_100` 即可生成序列，无需建表，用于日期填充、批量测试极为方便。 |
| **系统版本表** | `WITH SYSTEM VERSIONING` 使表自动记录所有行的历史版本，支持 `FOR SYSTEM_TIME AS OF` 时间旅行查询。 |
| **RETURNING** | INSERT/DELETE/REPLACE 语句可附加 `RETURNING` 子句，一步返回受影响行，减少额外 SELECT。 |
| **INVISIBLE 列** | 列可标记为 `INVISIBLE`，`SELECT *` 不返回，但可显式引用，适合审计字段与内部字段。 |
| **WITHOUT OVERLAPS** | 主键/唯一键中使用 `WITHOUT OVERLAPS` 即可在数据库层面防止时间区间重叠，原生实现 temporal 约束。 |
| **Oracle 兼容模式** | `SET sql_mode='ORACLE'` 后可直接执行 PL/SQL 风格代码，包括 `%ROWTYPE`、包变量、异常处理。 |
| **多源复制** | 一个从库同时从多个主库复制，适合数据汇聚场景。 |

## 已知不足

- **生态分裂**：与 MySQL 的差异逐版本扩大，部分 ORM/驱动（如特定版本的 MySQL Connector）可能出现兼容问题。
- **Group Replication 缺失**：MariaDB 使用 Galera Cluster 实现多主同步复制，但与 MySQL 的 Group Replication/InnoDB Cluster 不兼容。
- **文档与社区体量**：相比 MySQL/PostgreSQL，中文技术社区资料相对较少。
- **ColumnStore 成熟度**：列存引擎功能在快速迭代中，与专业 OLAP 引擎相比仍有差距。
- **JSON 函数滞后**：部分 JSON 路径操作（如 JSON_TABLE）引入晚于 MySQL 8.0。

## 对引擎开发者的参考价值

- **SEQUENCE 引擎的实现**：通过虚拟存储引擎生成序列值，是"引擎即函数"设计的优秀范例，值得嵌入式引擎参考。
- **系统版本表架构**：在存储引擎层透明维护行版本，对实现时间旅行查询（temporal query）的引擎有直接借鉴意义。
- **WITHOUT OVERLAPS 约束**：将区间不重叠校验下沉到索引层，展示了约束检查与索引结构耦合的设计路径。
- **Oracle 兼容模式**：通过 sql_mode 切换语法解析器行为，是多方言兼容的可行实现方案。
- **RETURNING 子句实现**：在 DML 执行路径中插入结果集返回节点，对减少客户端往返有参考价值。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/mariadb.md) | **MySQL 分叉保持协议兼容——兼容 ENGINE 可插拔架构**。独立新增 SEQUENCE(10.3+) 引擎（`SELECT * FROM seq_1_to_100` 直接生成序列，MySQL 无此功能）、虚拟列增强。对比 MySQL 的 AUTO_INCREMENT 和 PG 的 IDENTITY——MariaDB 的 SEQUENCE 引擎是独有创新。 |
| [改表](../ddl/alter-table/mariadb.md) | **Online DDL 改进——INSTANT ADD COLUMN 秒级完成**。ALGORITHM=INSTANT/INPLACE/COPY 显式指定。对比 MySQL 8.0 的 INSTANT DDL（功能接近）和 PG 的 DDL 事务性可回滚——MariaDB 在 Online DDL 上领先或持平 MySQL。 |
| [索引](../ddl/indexes/mariadb.md) | **InnoDB/Aria 引擎索引与 MySQL 高度兼容**——B-tree 聚簇索引。Mroonga 引擎提供 CJK 全文索引增强。对比 MySQL 索引体系和 PG 的 GiST/GIN/BRIN 四框架——MariaDB 索引功能与 MySQL 一致。 |
| [约束](../ddl/constraints/mariadb.md) | **CHECK 约束 10.2+ 真正执行——早于 MySQL 8.0.16**。MariaDB 在约束语义上比 MySQL 更早做正确的事。对比 PG/Oracle 始终强制执行——MariaDB 领先 MySQL 但晚于 PG。 |
| [视图](../ddl/views/mariadb.md) | **与 MySQL 兼容视图——无物化视图**。对比 PG 的 REFRESH MATERIALIZED VIEW 和 Oracle 的 Fast Refresh+Query Rewrite——MariaDB（同 MySQL）物化视图是空白。 |
| [序列与自增](../ddl/sequences/mariadb.md) | **SEQUENCE 对象(10.3+) 是 MariaDB 独有的 MySQL 系增强**——独立序列对象。AUTO_INCREMENT 与 MySQL 完全兼容。对比 PG 的 IDENTITY/SEQUENCE（更早更完善）——MariaDB 填补了 MySQL 缺少 SEQUENCE 的空白。 |
| [数据库/Schema/用户](../ddl/users-databases/mariadb.md) | **user@host 权限模型（同 MySQL）+ 角色(10.0.5+，早于 MySQL 8.0)**。对比 PG/Oracle 的纯用户+角色模型——MariaDB 在角色支持上领先 MySQL 约 3 年。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/mariadb.md) | **PREPARE/EXECUTE（同 MySQL）+ EXECUTE IMMEDIATE(10.2+) 简化**——借鉴 Oracle 语法。对比 Oracle 的 EXECUTE IMMEDIATE 和 PG 的 EXECUTE format()——MariaDB 的 EXECUTE IMMEDIATE 是 MySQL 系独有简化。 |
| [错误处理](../advanced/error-handling/mariadb.md) | **DECLARE HANDLER（同 MySQL）+ SIGNAL/RESIGNAL**。Oracle 兼容模式可用命名异常。对比 PG 的 EXCEPTION WHEN——MariaDB 错误处理与 MySQL 一致但 Oracle 模式是独特扩展。 |
| [执行计划](../advanced/explain/mariadb.md) | **EXPLAIN ANALYZE(10.1+，早于 MySQL 8.0.18)**。EXPLAIN FORMAT=JSON 结构化输出。对比 PG 的 EXPLAIN ANALYZE（最详细）——MariaDB 在执行计划工具上领先 MySQL。 |
| [锁机制](../advanced/locking/mariadb.md) | **InnoDB 行锁+间隙锁（同 MySQL）+ Aria 引擎崩溃安全**——Aria 是 MyISAM 崩溃安全替代。对比 PG 的 MVCC 无间隙锁——MariaDB 并发控制与 MySQL 相同。 |
| [分区](../advanced/partitioning/mariadb.md) | **RANGE/LIST/HASH/KEY 分区（同 MySQL）+ SYSTEM_TIME 分区独有**——系统版本表可按时间自动分区历史数据。对比 MySQL 的分区和 PG 的声明式分区——SYSTEM_TIME 分区是 MariaDB 独有创新。 |
| [权限](../advanced/permissions/mariadb.md) | **user@host 模型 + 角色(10.0.5+，早于 MySQL 8.0)**——领先 MySQL 约 3 年。对比 PG/Oracle 早已支持角色——MariaDB 在权限上追赶标准。 |
| [存储过程](../advanced/stored-procedures/mariadb.md) | **PL/SQL 兼容模式(sql_mode=ORACLE) 是 MariaDB 独特卖点**——可执行 PL/SQL 风格代码。对比 Oracle 原生 PL/SQL 和 PG 的 PL/pgSQL——MariaDB 的 Oracle 兼容降低迁移门槛。 |
| [临时表](../advanced/temp-tables/mariadb.md) | **CREATE TEMPORARY TABLE（同 MySQL）+ Aria 引擎崩溃安全临时表**。对比 MySQL 的 MEMORY/InnoDB 临时表和 PG 的 CREATE TEMP TABLE——MariaDB 临时表与 MySQL 一致。 |
| [事务](../advanced/transactions/mariadb.md) | **InnoDB MVCC（同 MySQL）——默认 RR + XA 分布式事务**。DDL 隐式提交不可回滚。对比 PG 的 DDL 事务性可回滚——MariaDB 事务语义继承 MySQL。 |
| [触发器](../advanced/triggers/mariadb.md) | **FOR EACH ROW 行级触发器（同 MySQL）——无 INSTEAD OF/语句级触发器**。对比 PG 的完整触发器——MariaDB 触发器限制与 MySQL 相同。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/mariadb.md) | **DELETE+LIMIT 分批删除（同 MySQL）**——TRUNCATE 不可回滚。对比 PG 的 DELETE...RETURNING——MariaDB 删除功能与 MySQL 一致。 |
| [插入](../dml/insert/mariadb.md) | **INSERT...SET + RETURNING(10.5+) 独有**——RETURNING 借鉴 PG 一步获取插入结果。LOAD DATA 批量导入。对比 PG 的 RETURNING（更早）和 MySQL（无 RETURNING）——MariaDB 填补了 MySQL 短板。 |
| [更新](../dml/update/mariadb.md) | **多表 UPDATE JOIN（同 MySQL）+ UPDATE...RETURNING(10.5+)**——RETURNING 是 MySQL 系独有增强。对比 PG 的 UPDATE...RETURNING（更早）——MariaDB 的 RETURNING 填补 MySQL 空白。 |
| [Upsert](../dml/upsert/mariadb.md) | **ON DUPLICATE KEY UPDATE（同 MySQL）+ INSERT...RETURNING**。无标准 MERGE。对比 PG 的 ON CONFLICT（更灵活）——MariaDB Upsert 与 MySQL 一致。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/mariadb.md) | **GROUP_CONCAT（同 MySQL）——无 GROUPING SETS/CUBE/ROLLUP/FILTER**。对比 PG 的完整多维聚合——MariaDB 聚合函数与 MySQL 一致。 |
| [条件函数](../functions/conditional/mariadb.md) | **IF()/CASE（同 MySQL）+ DECODE（Oracle 兼容模式可用）**。对比 MySQL 无 DECODE 和 Oracle 原生 DECODE——MariaDB Oracle 模式是独特扩展。 |
| [日期函数](../functions/date-functions/mariadb.md) | **DATE_FORMAT（同 MySQL）日期函数完全兼容**。对比 PG 的 to_char 和 Oracle 的 TO_DATE——MariaDB 日期函数继承 MySQL 风格。 |
| [数学函数](../functions/math-functions/mariadb.md) | **与 MySQL 兼容完整数学函数**。GREATEST/LEAST 内置，除零返回 NULL。对比 PG/Oracle 除零报错——MariaDB 与 MySQL 数学函数一致。 |
| [字符串函数](../functions/string-functions/mariadb.md) | **CONCAT（同 MySQL）+ || 在 sql_mode=ORACLE 时为拼接**——标准模式 || 是逻辑 OR（同 MySQL），Oracle 模式 || 是拼接。对比 PG/Oracle || 始终是拼接——sql_mode 切换解决方言差异。 |
| [类型转换](../functions/type-conversion/mariadb.md) | **CAST/CONVERT（同 MySQL）——隐式转换宽松**。无 TRY_CAST。对比 PG 严格类型和 SQL Server 的 TRY_CAST——MariaDB 类型转换与 MySQL 相同。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/mariadb.md) | **递归 CTE(10.2+，早于 MySQL 8.0)**——领先 MySQL 约 1 年。无可写 CTE。对比 PG 的可写 CTE 和 MySQL 8.0 CTE——MariaDB 在 CTE 上领先 MySQL。 |
| [全文搜索](../query/full-text-search/mariadb.md) | **InnoDB FULLTEXT + Mroonga 引擎 CJK 分词更强**——Mroonga 对中日韩分词优于 InnoDB ngram。对比 PG 的 tsvector+GIN——MariaDB 的 Mroonga 是 CJK 搜索优势。 |
| [连接查询](../query/joins/mariadb.md) | **无 FULL OUTER JOIN（同 MySQL）**——需 UNION 模拟。对比 PG 完整支持——MariaDB 继承 MySQL 的 JOIN 限制。 |
| [分页](../query/pagination/mariadb.md) | **LIMIT/OFFSET（同 MySQL）+ LIMIT...ROWS EXAMINED 独有**——限制扫描行数防止全表扫描。对比 MySQL 标准 LIMIT——ROWS EXAMINED 是实用的查询保护功能。 |
| [行列转换](../query/pivot-unpivot/mariadb.md) | **无原生 PIVOT（同 MySQL）**——CASE+GROUP BY 模拟。对比 Oracle/BigQuery/DuckDB 原生 PIVOT——MariaDB 继承 MySQL 行列转换短板。 |
| [集合操作](../query/set-operations/mariadb.md) | **INTERSECT/EXCEPT(10.3+) 早于 MySQL 8.0.31 约 5 年**。对比 PG 始终完整——MariaDB 在集合操作上领先 MySQL。 |
| [子查询](../query/subquery/mariadb.md) | **优化器改进优于早期 MySQL**——semi-join 优化等更早引入。对比 MySQL 5.x 子查询性能噩梦——MariaDB 优化器在某些场景优于同期 MySQL。 |
| [窗口函数](../query/window-functions/mariadb.md) | **窗口函数 10.2+ 支持（早于 MySQL 8.0）**——完整窗口函数集。无 QUALIFY。对比 MySQL 8.0 和 PG 8.4——MariaDB 窗口函数比 MySQL 更早交付。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/mariadb.md) | **seq_1_to_N 序列引擎是 MariaDB 独有的最简日期填充方案**——无需递归 CTE。对比 MySQL 需递归 CTE 和 PG 的 generate_series——MariaDB 序列引擎方案最简洁。 |
| [去重](../scenarios/deduplication/mariadb.md) | **ROW_NUMBER+CTE 去重或 DELETE+JOIN 自连接**。对比 PG 的 DISTINCT ON 和 BigQuery 的 QUALIFY——MariaDB 去重方案中规中矩。 |
| [区间检测](../scenarios/gap-detection/mariadb.md) | **窗口函数(10.2+)+seq 序列引擎辅助检测间隙**——seq 引擎替代递归 CTE 生成序列。对比 PG 的 generate_series——MariaDB seq 引擎是间隙检测的独特优势。 |
| [层级查询](../scenarios/hierarchical-query/mariadb.md) | **递归 CTE(10.2+) 标准层级查询**——无 CONNECT BY。对比 PG 递归 CTE+ltree 和 MySQL 8.0 递归 CTE——MariaDB 层级查询与 MySQL 一致。 |
| [JSON 展开](../scenarios/json-flatten/mariadb.md) | **JSON_TABLE(10.6+)+JSON_EXTRACT**——JSON_TABLE 引入晚于 MySQL 8.0。JSON 内部存储为 LONGTEXT（非二进制，效率低于 MySQL）。对比 PG 的 JSONB+GIN——MariaDB JSON 实现在 MySQL 系中反而落后。 |
| [迁移速查](../scenarios/migration-cheatsheet/mariadb.md) | **与 MySQL 高度兼容但 10.6+ 差异扩大**——JSON 存储差异、CHECK 行为差异、SEQUENCE 独有、系统版本表独有。迁移需逐项验证。 |
| [TopN 查询](../scenarios/ranking-top-n/mariadb.md) | **ROW_NUMBER(10.2+)+CTE 分组 TopN**——无 QUALIFY。对比 BigQuery/DuckDB QUALIFY 无需子查询——MariaDB TopN 方案与 MySQL 一致。 |
| [累计求和](../scenarios/running-total/mariadb.md) | **SUM() OVER(10.2+) 累计求和——早于 MySQL 8.0**。对比 PG 8.4 起即支持——MariaDB 在窗口函数上位于 PG 和 MySQL 之间。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/mariadb.md) | **无 MERGE——ON DUPLICATE KEY UPDATE 是唯一 Upsert 方案**。对比 Oracle MERGE（首创）和 PG 15+ MERGE——MariaDB 与 MySQL 一样缺少标准 MERGE。 |
| [字符串拆分](../scenarios/string-split-to-rows/mariadb.md) | **无原生拆分函数**——JSON_TABLE(10.6+) 或递归 CTE 模拟。seq 引擎+SUBSTRING_INDEX 是独有简洁方案。对比 PG 14 string_to_table——MariaDB 字符串拆分较繁琐。 |
| [窗口分析](../scenarios/window-analytics/mariadb.md) | **10.2+ 窗口函数完整——早于 MySQL 8.0**。ROWS/RANGE 帧完整。无 QUALIFY/FILTER/GROUPS。对比 PG 的 FILTER+GROUPS——MariaDB 窗口分析与 MySQL 持平。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/mariadb.md) | **无 ARRAY/STRUCT（同 MySQL）**——JSON 替代。对比 PG 原生 ARRAY 和 BigQuery STRUCT/ARRAY——MariaDB 复合类型依赖 JSON。 |
| [日期时间](../types/datetime/mariadb.md) | **DATETIME vs TIMESTAMP 选择困惑（同 MySQL）**——TIMESTAMP 有 2038 年问题。对比 PG TIMESTAMPTZ——MariaDB 时间类型限制与 MySQL 相同。 |
| [JSON](../types/json/mariadb.md) | **JSON 别名 LONGTEXT（非二进制）——不如 MySQL 二进制 JSON**。JSON_TABLE(10.6+) 晚于 MySQL。对比 PG JSONB+GIN（最强）——MariaDB JSON 在 MySQL 系中反而落后。 |
| [数值类型](../types/numeric/mariadb.md) | **与 MySQL 兼容数值——DECIMAL 精确+UNSIGNED 保留**。UNSIGNED 仍完整支持（MySQL 8.0 废弃趋势中）。对比 PG 无 UNSIGNED——MariaDB 数值类型与 MySQL 兼容。 |
| [字符串类型](../types/string/mariadb.md) | **utf8=utf8mb3 只支持 3 字节（同 MySQL 历史坑）**——必须用 utf8mb4。对比 PG UTF-8 默认完整——MariaDB 继承 MySQL utf8 编码陷阱。 |
