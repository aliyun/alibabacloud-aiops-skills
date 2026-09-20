# OceanBase

**分类**: 分布式数据库（兼容 MySQL/Oracle）
**文件数**: 51 个 SQL 文件
**总行数**: 4951 行

> **关键人物**：[阳振坤](../docs/people/oceanbase-founders.md)（TPC-C 打破 Oracle 纪录）

## 概述与定位

OceanBase 是蚂蚁集团自主研发的分布式关系型数据库，定位于金融级核心系统的在线交易处理（OLTP）场景。它以超大规模、高可用和强一致为核心竞争力，同时提供 MySQL 和 Oracle 双兼容模式，降低传统数据库用户的迁移成本。OceanBase 已在支付宝核心交易系统中经受多年双十一验证，连续刷新 TPC-C 和 TPC-H 基准测试世界纪录。

## 历史与演进

- **2010 年**：蚂蚁金服内部立项，目标替换 Oracle 处理海量支付交易。
- **2014 年**：OceanBase 0.5 上线支付宝核心账务系统。
- **2017 年**：1.x 发布，支持多租户和 MySQL 兼容模式。
- **2019 年**：2.x 引入 Oracle 兼容模式，打破 TPC-C 世界纪录。
- **2021 年**：3.x 开源社区版，引入 HTAP 能力和备份恢复增强。
- **2023 年**：4.x 统一架构（单机分布式一体化），大幅降低小规模部署成本。
- **2024-2025 年**：持续强化多模数据处理、向量检索和 AI 集成。

## 核心设计思路

OceanBase 采用 Shared-Nothing 架构，数据按分区（Partition）分布在多个 OBServer 节点上。每个分区通过 Paxos 协议维护多副本强一致，保证 RPO=0。**多租户**是一等公民概念——同一集群可划分多个 Tenant，每个租户拥有独立的资源配额和兼容模式（MySQL 或 Oracle）。存储层采用 LSM-Tree 结构实现高效写入，基线数据与增量数据分离（Major/Minor Compaction）。事务引擎支持两阶段提交实现跨分区事务。

## 独特特色

- **双模兼容**：同一集群中不同租户可分别运行 MySQL 模式和 Oracle 模式，SQL 语法、数据类型、PL 过程语言各自兼容。
- **Tablegroup**：将频繁 JOIN 的表分区绑定到同一节点，减少分布式事务开销。
- **Primary Zone**：控制 Leader 副本的优先分布区域，优化就近读写。
- **LSM-Tree 存储**：写入性能优异，后台 Compaction 合并，支持数据压缩达到高存储效率。
- **原生多租户**：租户间资源硬隔离（CPU/Memory/IO），单集群可服务数百租户。
- **全局时间戳服务 GTS**：确保跨分区读的全局一致性快照。
- **表级恢复与物理备份**：支持细粒度的 PITR（Point-in-Time Recovery）。

## 已知不足

- Oracle 兼容模式虽覆盖面广，但部分高级 PL/SQL 包和特性仍有差异。
- LSM-Tree 的后台 Compaction 可能导致写放大和周期性 IO 抖动。
- 社区版功能相比企业版有所裁剪（如部分高可用和运维工具）。
- 小规模部署（3 节点以下）相比单机数据库仍有一定运维复杂度，4.x 版本正在改善。
- 生态工具和第三方驱动兼容性不如 MySQL/PostgreSQL 原生生态丰富。
- 分区表数量极多时元数据管理开销增大。

## 对引擎开发者的参考价值

OceanBase 是少数将 Paxos 共识协议工程化落地到金融核心场景的数据库，其多租户资源隔离设计、LSM-Tree 在 OLTP 场景的调优经验、以及双模兼容的 SQL 引擎实现（同一优化器框架适配两套语法体系）对数据库内核开发者极具参考价值。Tablegroup 概念展示了分布式数据库中数据协同放置（co-location）对性能的关键影响。

## 全部模块

### DDL — 数据定义

| 模块 | 特色与分析 |
|---|---|
| [建表](../ddl/create-table/oceanbase.md) | **MySQL/Oracle 双兼容模式在租户级切换**——同一集群中不同租户可分别运行 MySQL 或 Oracle SQL 方言。Tablegroup 将频繁 JOIN 的表分区绑定到同一节点减少分布式事务开销。Primary Zone 控制 Leader 副本优先分布区域。对比 TiDB（仅 MySQL 兼容）和 KingbaseES（PG/Oracle 双模），OceanBase 是唯一同时兼容 MySQL 和 Oracle 的分布式数据库。 |
| [改表](../ddl/alter-table/oceanbase.md) | **Online DDL 无锁变更**——基于分布式 Schema 变更协议实现在线 ADD/DROP/MODIFY COLUMN。LSM-Tree 存储层使 Schema 变更可与后台 Compaction 协同完成。对比 MySQL 的 pt-osc 和 TiDB 的内置 Online DDL，OceanBase 的 Schema 变更延迟更低但 Compaction 期间可能有 IO 抖动。 |
| [索引](../ddl/indexes/oceanbase.md) | **全局/局部索引 + LSM-Tree 存储**——全局索引跨分区维护唯一性，局部索引仅在分区内有效。LSM-Tree 结构使写入性能优于传统 B-Tree 但读取可能需要多层合并。4.x+ 支持聚集索引。对比 TiDB 的分布式 B-Tree 索引和 CockroachDB 的 LSM 索引+STORING，OceanBase 的索引设计更贴近传统 RDBMS 但底层是 LSM。 |
| [约束](../ddl/constraints/oceanbase.md) | **PK/FK/CHECK/UNIQUE 完整支持（双模兼容）**——MySQL 模式和 Oracle 模式各自遵循对应的约束语义。外键约束在分布式场景下跨分区检查可能有性能影响。对比 TiDB（FK 仅实验性）和 BigQuery（NOT ENFORCED），OceanBase 的约束执行力度更强。 |
| [视图](../ddl/views/oceanbase.md) | **普通视图双模兼容，无物化视图**——MySQL 模式和 Oracle 模式的视图语法各自兼容原生数据库。缺少物化视图是分析场景的短板。对比 PG/Oracle 的完整物化视图和 BigQuery 的自动增量刷新物化视图，OceanBase 在这方面有待增强。 |
| [序列与自增](../ddl/sequences/oceanbase.md) | **AUTO_INCREMENT（MySQL 模式）+ SEQUENCE（Oracle 模式）**——分布式环境下 AUTO_INCREMENT 通过全局 ID 服务保证唯一但不保证连续。Oracle 模式的 SEQUENCE 支持 CACHE/NOCACHE/CYCLE 等标准属性。对比 TiDB 的 AUTO_RANDOM（打散热点）和 Spanner 的 UUID 策略，OceanBase 在双模式下提供了最丰富的 ID 生成选择。 |
| [数据库/Schema/用户](../ddl/users-databases/oceanbase.md) | **租户级 MySQL/Oracle 模式切换是独有设计**——每个租户拥有独立的资源配额（CPU/Memory/IO）、兼容模式和用户权限体系。系统租户管理集群级操作。对比 TiDB 的 Resource Control 和 CockroachDB 的多租户 Cluster，OceanBase 的租户隔离粒度最细，源自蚂蚁金服多租户实践。 |

### Advanced — 高级特性

| 模块 | 特色与分析 |
|---|---|
| [动态 SQL](../advanced/dynamic-sql/oceanbase.md) | **PREPARE/EXECUTE（MySQL 模式）+ EXECUTE IMMEDIATE（Oracle 模式）**——双模式下动态 SQL 语法各自兼容原生数据库。Oracle 模式支持 PL/SQL 块内的动态 SQL。对比 TiDB（无存储过程内动态 SQL）和达梦（Oracle 兼容 EXECUTE IMMEDIATE），OceanBase 的双模动态 SQL 覆盖面最广。 |
| [错误处理](../advanced/error-handling/oceanbase.md) | **DECLARE HANDLER（MySQL 模式）+ EXCEPTION WHEN（Oracle 模式）**——两种错误处理范式在各自租户模式下完整可用。Oracle 模式支持自定义异常和 RAISE_APPLICATION_ERROR。对比 TiDB（不支持过程式错误处理）和 KingbaseES（PG/Oracle 双模），OceanBase 的错误处理兼容性源自其完整的存储过程支持。 |
| [执行计划](../advanced/explain/oceanbase.md) | **EXPLAIN 展示分布式 Exchange/Partition 信息**——可看到数据在分区间的 Exchange 算子和并行度。支持 EXPLAIN EXTENDED 查看优化器改写过程。对比 TiDB 的 cop[tikv/tiflash] 算子和 CockroachDB 的 DISTSQL 计划，OceanBase 的执行计划更接近传统 Oracle 的输出格式。 |
| [锁机制](../advanced/locking/oceanbase.md) | **行级锁 + MVCC + 分布式两阶段锁**——跨分区事务使用 2PL 保证强一致。读操作基于 MVCC 快照不阻塞写。GTS（全局时间戳服务）确保跨分区读一致性。对比 TiDB 的 Percolator 乐观/悲观双模和 CockroachDB 的 HLC+SERIALIZABLE，OceanBase 的锁模型更传统但在金融场景中久经验证。 |
| [分区](../advanced/partitioning/oceanbase.md) | **PARTITION BY（MySQL 兼容）+ 自动分片双层体系**——手动分区用于业务逻辑（如按时间 RANGE），自动分片处理负载均衡。支持二级分区（如 RANGE-HASH 组合）。Tablegroup 绑定多表分区实现数据共置。对比 TiDB 的 Region 自动分片和 CockroachDB 的 Geo-Partitioning，OceanBase 的 Tablegroup 共置策略对金融场景的多表 JOIN 优化效果显著。 |
| [权限](../advanced/permissions/oceanbase.md) | **MySQL/Oracle 双兼容权限模型**——MySQL 模式使用 GRANT/REVOKE 标准语法，Oracle 模式支持 PROFILE、ROLE 和对象级权限。租户间权限完全隔离。对比 TiDB 的 MySQL 兼容权限和 KingbaseES 的三权分立，OceanBase 在权限体系上最接近原生 MySQL/Oracle 体验。 |
| [存储过程](../advanced/stored-procedures/oceanbase.md) | **MySQL/Oracle 双兼容存储过程 + PL/SQL Package**——Oracle 模式支持 Package/Body、游标、批量操作（BULK COLLECT/FORALL）等高级 PL/SQL 特性。MySQL 模式支持标准存储过程。对比 TiDB（不支持存储过程）和 CockroachDB（PL/pgSQL 有限），OceanBase 的过程式编程能力最完整。 |
| [临时表](../advanced/temp-tables/oceanbase.md) | **TEMPORARY TABLE（MySQL 兼容）**——会话级临时表，事务结束后数据可保留或删除。Oracle 模式支持 ON COMMIT PRESERVE/DELETE ROWS 标准语义。对比 PG 的灵活临时表和 Oracle 的 GTT，OceanBase 在各自模式下忠实还原原生行为。 |
| [事务](../advanced/transactions/oceanbase.md) | **分布式 ACID 事务基于 Paxos 多副本一致性**——跨分区事务通过两阶段提交保证原子性，Paxos 协议保证 RPO=0。默认 READ COMMITTED 隔离级别。对比 TiDB 的 Percolator SI 和 Spanner 的 TrueTime 外部一致性，OceanBase 的 Paxos 一致性在支付宝双十一中经受了极端验证。 |
| [触发器](../advanced/triggers/oceanbase.md) | **MySQL/Oracle 双兼容触发器**——BEFORE/AFTER/INSTEAD OF 均支持（Oracle 模式）。MySQL 模式支持标准触发器语法。对比 TiDB（不支持触发器）和 CockroachDB（不支持），OceanBase 是少数支持触发器的分布式数据库，源自其 Oracle 兼容定位。 |

### DML — 数据操作

| 模块 | 特色与分析 |
|---|---|
| [删除](../dml/delete/oceanbase.md) | **DELETE 双模兼容 + 分布式并行**——MySQL 模式支持 DELETE ... LIMIT，Oracle 模式支持 DELETE ... RETURNING。分区级删除可并行执行。LSM-Tree 的标记删除在后台 Compaction 时真正回收空间。对比 MySQL 的单机删除和 BigQuery 的分区级标记删除，OceanBase 的 LSM 删除模式写入快但空间回收延迟。 |
| [插入](../dml/insert/oceanbase.md) | **INSERT 双模兼容 + 批量导入优化**——MySQL 模式支持 INSERT ... ON DUPLICATE KEY UPDATE，Oracle 模式支持 INSERT ALL 多表插入。旁路导入（Direct Load）跳过 MemTable 直接写入 SSTable 加速批量导入。对比 TiDB 的 Lightning 导入和 BigQuery 的免费 LOAD JOB，OceanBase 的旁路导入在金融批处理场景效果显著。 |
| [更新](../dml/update/oceanbase.md) | **UPDATE 双模兼容 + 分布式事务**——跨分区 UPDATE 通过 2PC 保证原子性。Oracle 模式支持 UPDATE ... RETURNING。更新主键值可能导致数据跨分区迁移。对比 TiDB 的分布式 UPDATE 和 BigQuery（UPDATE 必须带 WHERE），OceanBase 的行为更接近传统 RDBMS。 |
| [Upsert](../dml/upsert/oceanbase.md) | **ON DUPLICATE KEY UPDATE（MySQL 模式）+ MERGE INTO（Oracle 模式）**——双模式提供了两种 Upsert 范式。MERGE INTO 支持完整的 WHEN MATCHED/NOT MATCHED/NOT MATCHED BY SOURCE 语义。对比 TiDB（仅 MySQL 的 ON DUPLICATE KEY）和 CockroachDB（PG 的 ON CONFLICT），OceanBase 的 MERGE 实现最接近标准 SQL。 |

### Functions — 内置函数

| 模块 | 特色与分析 |
|---|---|
| [聚合函数](../functions/aggregate/oceanbase.md) | **MySQL/Oracle 聚合函数双兼容**——MySQL 模式支持 GROUP_CONCAT，Oracle 模式支持 LISTAGG/GROUPING SETS/CUBE/ROLLUP。分布式并行聚合自动下推到各分区节点。对比 TiDB（仅 MySQL 聚合）和达梦（仅 Oracle 聚合），OceanBase 在聚合函数覆盖面上最广。 |
| [条件函数](../functions/conditional/oceanbase.md) | **IF（MySQL 模式）/ DECODE（Oracle 模式）双兼容**——CASE/COALESCE/NULLIF 在两种模式下均可用。Oracle 模式的 DECODE 和 NVL/NVL2 完整支持。对比 PG（无 IF/DECODE）和 BigQuery（SAFE_ 前缀设计），OceanBase 的条件函数选择取决于租户模式。 |
| [日期函数](../functions/date-functions/oceanbase.md) | **MySQL/Oracle 日期函数双兼容**——MySQL 模式的 DATE_FORMAT/STR_TO_DATE 和 Oracle 模式的 TO_CHAR/TO_DATE 各自独立实现。日期类型语义也因模式而异（Oracle 的 DATE 含时间，MySQL 的 DATE 纯日期）。对比 BigQuery 的统一日期函数和 PG 的 date_trunc/to_char，OceanBase 的日期处理复杂度最高但兼容性最强。 |
| [数学函数](../functions/math-functions/oceanbase.md) | **MySQL/Oracle 数学函数双兼容**——基础函数（ABS/CEIL/FLOOR/ROUND）在两种模式下行为一致。Oracle 模式额外支持 TRUNC（截断）等函数。除零处理行为因模式而异。对比 TiDB（MySQL 风格）和达梦（Oracle 风格），OceanBase 根据租户模式自动切换。 |
| [字符串函数](../functions/string-functions/oceanbase.md) | **MySQL/Oracle 字符串函数双兼容**——MySQL 模式用 CONCAT() 函数，Oracle 模式用 `\|\|` 拼接运算符。Oracle 模式的空字符串 '' 等同 NULL（Oracle 独有语义）。对比 TiDB（CONCAT 函数）和达梦（`\|\|` 拼接），OceanBase 在各自模式下忠实还原原生行为。 |
| [类型转换](../functions/type-conversion/oceanbase.md) | **CAST（MySQL 模式）/ TO_NUMBER/TO_DATE/TO_CHAR（Oracle 模式）**——类型转换函数因模式完全不同。隐式转换规则也因模式而异（MySQL 宽松，Oracle 相对严格）。对比 PG 的 `::` 运算符和 BigQuery 的 SAFE_CAST，OceanBase 的类型转换行为完全取决于租户模式选择。 |

### Query — 查询

| 模块 | 特色与分析 |
|---|---|
| [CTE](../query/cte/oceanbase.md) | **WITH + 递归 CTE 支持**——两种模式下均支持标准 CTE 语法。Oracle 模式还可使用 CONNECT BY 替代递归 CTE 进行层级查询。对比 TiDB（5.1+ CTE）和 MySQL 8.0（基本 CTE），OceanBase 的 Oracle 模式提供了更多层级查询选项。 |
| [全文搜索](../query/full-text-search/oceanbase.md) | **全文索引支持（4.x+）**——支持中文全文检索，填补了分布式数据库中全文搜索的空白。对比 TiDB（不支持 FULLTEXT）和 CockroachDB（GIN 索引），OceanBase 是少数在分布式环境下提供全文索引的数据库。 |
| [连接查询](../query/joins/oceanbase.md) | **Hash/Nested Loop/Merge JOIN + 分布式 JOIN 优化**——Tablegroup 共置策略使同组表的 JOIN 在本地完成，避免跨节点数据传输。分布式 JOIN 自动选择广播或重分布策略。对比 TiDB 的 TiFlash MPP JOIN 和 CockroachDB 的 Lookup JOIN，OceanBase 的 Tablegroup 共置 JOIN 在金融多表关联场景性能最优。 |
| [分页](../query/pagination/oceanbase.md) | **LIMIT（MySQL 模式）/ ROWNUM+FETCH FIRST（Oracle 模式）**——双模式提供不同的分页语法。分布式场景下深度分页同样有性能退化问题。对比 TiDB 的 LIMIT/OFFSET 和达梦的 ROWNUM，OceanBase 的分页语法完全取决于租户模式。 |
| [行列转换](../query/pivot-unpivot/oceanbase.md) | **无原生 PIVOT（MySQL 模式），PIVOT/UNPIVOT（Oracle 模式）**——Oracle 模式完整支持 PIVOT/UNPIVOT 语法。MySQL 模式需用 CASE+GROUP BY 模拟。对比 BigQuery/Snowflake 的原生 PIVOT 和 TiDB（无 PIVOT），OceanBase 的 Oracle 模式提供了标准行列转换能力。 |
| [集合操作](../query/set-operations/oceanbase.md) | **UNION/INTERSECT/EXCEPT 完整支持**——Oracle 模式额外支持 MINUS（等同 EXCEPT）。分布式执行时集合操作可并行化。对比 TiDB 的完整集合操作和 MySQL 8.0（较晚引入 INTERSECT/EXCEPT），OceanBase 在两种模式下均提供完整的集合操作能力。 |
| [子查询](../query/subquery/oceanbase.md) | **关联子查询双模兼容**——优化器可将子查询转为 Semi/Anti Join 下推到各分区。Oracle 模式支持 ROWNUM 伪列用于子查询限制行数。对比 TiDB 的子查询下推优化和 PG 的成熟子查询处理，OceanBase 的优化器在 TPC-H 基准测试中表现优异。 |
| [窗口函数](../query/window-functions/oceanbase.md) | **完整窗口函数（MySQL/Oracle 双兼容）**——ROW_NUMBER/RANK/DENSE_RANK/NTILE/LAG/LEAD 等全部支持。Oracle 模式额外支持 KEEP(DENSE_RANK FIRST/LAST) 等高级分析函数。对比 TiDB（MySQL 兼容窗口函数）和达梦（Oracle 兼容），OceanBase 在两种模式下均提供完整窗口分析能力。 |

### Scenarios — 实战场景

| 模块 | 特色与分析 |
|---|---|
| [日期填充](../scenarios/date-series-fill/oceanbase.md) | **递归 CTE / CONNECT BY（Oracle 模式）生成日期序列**——Oracle 模式可用 CONNECT BY LEVEL <= N 快速生成序列，MySQL 模式使用递归 CTE。对比 PG 的 generate_series 和 BigQuery 的 GENERATE_DATE_ARRAY，OceanBase 的 Oracle 模式提供了最简洁的序列生成语法。 |
| [去重](../scenarios/deduplication/oceanbase.md) | **ROW_NUMBER+CTE 标准去重**——分布式并行执行，大数据量去重可利用分区并行。Oracle 模式可结合 ROWID 直接删除重复行（非 CTE 方案）。对比 PG 的 DISTINCT ON 和 BigQuery 的 QUALIFY，OceanBase 提供多种去重方案选择。 |
| [区间检测](../scenarios/gap-detection/oceanbase.md) | **窗口函数 LAG/LEAD 检测间隙**——双模式下窗口函数行为一致。Oracle 模式可结合 CONNECT BY 生成完整序列后 LEFT JOIN 检测。对比 TimescaleDB 的 time_bucket_gapfill 和 Teradata 的 sys_calendar，OceanBase 使用通用方法。 |
| [层级查询](../scenarios/hierarchical-query/oceanbase.md) | **递归 CTE + CONNECT BY（Oracle 模式）双方案**——Oracle 模式的 CONNECT BY START WITH ... PRIOR 语法对 Oracle 用户零迁移成本。MySQL 模式使用标准递归 CTE。对比 TiDB（仅递归 CTE）和达梦（Oracle 兼容 CONNECT BY），OceanBase 在 Oracle 模式下保留了完整的层级查询能力。 |
| [JSON 展开](../scenarios/json-flatten/oceanbase.md) | **JSON_TABLE/JSON_EXTRACT 双模兼容**——MySQL 模式使用 ->/->> 操作符和 JSON_TABLE，Oracle 模式使用 JSON_VALUE/JSON_QUERY。JSON 处理能力在持续增强中。对比 PG 的 jsonb_array_elements（最成熟）和 BigQuery 的 JSON_QUERY_ARRAY+UNNEST，OceanBase 的 JSON 功能随版本快速演进。 |
| [迁移速查](../scenarios/migration-cheatsheet/oceanbase.md) | **MySQL/Oracle 双兼容是核心卖点**——租户级模式切换使同一集群可同时服务 MySQL 和 Oracle 应用。分布式透明对应用层无感知。Tablegroup 和 Primary Zone 是需要额外学习的分布式概念。对比 TiDB（仅 MySQL）和 CockroachDB（仅 PG），OceanBase 的双模兼容在国产化替代 Oracle 场景中独具优势。 |
| [TopN 查询](../scenarios/ranking-top-n/oceanbase.md) | **ROW_NUMBER + LIMIT/ROWNUM（双模兼容）**——MySQL 模式用 LIMIT，Oracle 模式用 ROWNUM 或 FETCH FIRST。无 QUALIFY 子句。对比 BigQuery/Snowflake 的 QUALIFY 和 Teradata 的 QUALIFY（首创），OceanBase 需要子查询包装但功能完整。 |
| [累计求和](../scenarios/running-total/oceanbase.md) | **SUM() OVER 标准窗口函数**——分布式环境下窗口函数需要全局排序，性能取决于数据分布。对比 TiDB 的 TiFlash 加速和 BigQuery 的 Slot 自动扩展，OceanBase 的窗口函数在 OLTP 引擎上执行，大数据量分析场景可能需要额外优化。 |
| [缓慢变化维](../scenarios/slowly-changing-dim/oceanbase.md) | **ON DUPLICATE KEY（MySQL 模式）+ MERGE INTO（Oracle 模式）**——Oracle 模式的 MERGE 支持完整的 SCD Type 1/2 实现。MySQL 模式需多条 SQL 组合。对比 TiDB（无 MERGE）和 BigQuery 的 MERGE，OceanBase 的 Oracle 模式在 SCD 场景下最灵活。 |
| [字符串拆分](../scenarios/string-split-to-rows/oceanbase.md) | **JSON_TABLE 或递归 CTE 模拟**——MySQL 模式用 JSON_TABLE 将字符串转数组后展开，Oracle 模式可用 CONNECT BY+REGEXP_SUBSTR 逐段提取。对比 PG 的 string_to_array+unnest 和 BigQuery 的 SPLIT+UNNEST，OceanBase 的字符串拆分因模式而异。 |
| [窗口分析](../scenarios/window-analytics/oceanbase.md) | **完整窗口函数（双模兼容）**——移动平均、同环比、占比计算等在两种模式下均可实现。Oracle 模式额外支持 KEEP/FIRST_VALUE/LAST_VALUE 等高级分析函数。对比 TiDB 的 TiFlash 加速分析和专用 OLAP 引擎，OceanBase 的窗口分析在 OLTP 场景中足够使用但非其核心优势。 |

### Types — 数据类型

| 模块 | 特色与分析 |
|---|---|
| [复合类型](../types/array-map-struct/oceanbase.md) | **无 ARRAY/STRUCT 类型，JSON 替代**——两种模式均不支持原生复合类型。Oracle 模式在 PL/SQL 中支持 TABLE/RECORD 类型，但 SQL 层面无 VARRAY。对比 PG 的 ARRAY/COMPOSITE 和 BigQuery 的 STRUCT/ARRAY，OceanBase 在复合类型方面受限于 MySQL/Oracle 的 SQL 层类型系统。 |
| [日期时间](../types/datetime/oceanbase.md) | **DATETIME/TIMESTAMP（MySQL 模式）+ DATE/TIMESTAMP（Oracle 模式）**——Oracle 模式的 DATE 包含时间部分（与 MySQL 的纯日期 DATE 不同），这是模式切换时最常见的陷阱。对比 PG 的 TIMESTAMPTZ（推荐带时区）和 BigQuery 的四种时间类型，OceanBase 的日期语义完全取决于租户模式。 |
| [JSON](../types/json/oceanbase.md) | **JSON 类型（MySQL 兼容）+ JSON_TABLE**——MySQL 模式支持 JSON 二进制存储和多值索引。Oracle 模式的 JSON 处理通过 JSON_VALUE/JSON_QUERY 标准函数。对比 PG 的 JSONB+GIN 索引（功能最强）和 BigQuery 的原生 JSON，OceanBase 的 JSON 能力随 MySQL/Oracle 各自版本演进。 |
| [数值类型](../types/numeric/oceanbase.md) | **MySQL/Oracle 兼容数值类型**——MySQL 模式提供 INT/BIGINT/DECIMAL 等，Oracle 模式提供 NUMBER/BINARY_FLOAT/BINARY_DOUBLE。NUMBER 类型在 Oracle 模式下的精度行为与 Oracle 一致。对比 BigQuery 的 INT64/NUMERIC 极简类型和 TiDB 的 MySQL 全集，OceanBase 的数值类型覆盖两套体系。 |
| [字符串类型](../types/string/oceanbase.md) | **VARCHAR（MySQL 模式）/ VARCHAR2（Oracle 模式）双兼容**——Oracle 模式的 VARCHAR2 长度语义（BYTE vs CHAR）与 Oracle 一致。MySQL 模式的 utf8mb4 字符集配置与 MySQL 相同。对比 PG 的 TEXT 和 BigQuery 的 STRING，OceanBase 的字符串类型因模式而完全不同。 |
