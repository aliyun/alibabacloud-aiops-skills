# 方言索引

按数据库方言浏览所有模块。点击方言名称查看该方言的全部 SQL 文件。

## 传统关系型数据库

| 方言 | 说明 | 文件数 |
|---|---|---|
| [MySQL](mysql.md) | 最流行的开源关系型数据库 | 51 |
| [PostgreSQL](postgres.md) | 最先进的开源关系型数据库 | 51 |
| [SQLite](sqlite.md) | 嵌入式数据库 | 51 |
| [Oracle](oracle.md) | 企业级商业数据库 | 51 |
| [SQL Server](sqlserver.md) | 微软商业数据库 | 51 |
| [MariaDB](mariadb.md) | MySQL 开源分支 | 51 |
| [Firebird](firebird.md) | 开源数据库（InterBase 分支） | 51 |
| [IBM Db2](db2.md) | IBM 企业级数据库 | 51 |
| [SAP HANA](saphana.md) | SAP 内存数据库 | 51 |

## 大数据 / 分析型引擎

| 方言 | 说明 | 文件数 |
|---|---|---|
| [BigQuery](bigquery.md) | Google 云数仓 | 51 |
| [Snowflake](snowflake.md) | 云原生数仓 | 51 |
| [ClickHouse](clickhouse.md) | 列式分析数据库 | 51 |
| [Hive](hive.md) | Hadoop 数仓 | 51 |
| [Spark SQL](spark.md) | 大数据计算引擎 | 51 |
| [Flink SQL](flink.md) | 流批一体引擎 | 51 |
| [StarRocks](starrocks.md) | MPP 分析数据库 | 51 |
| [Doris](doris.md) | Apache MPP 分析数据库 | 51 |
| [Trino](trino.md) | 分布式查询引擎 | 51 |
| [DuckDB](duckdb.md) | 嵌入式 OLAP | 51 |
| [MaxCompute](maxcompute.md) | 阿里云大数据平台 | 51 |
| [Hologres](hologres.md) | 阿里云实时数仓 | 51 |

## 云数仓

| 方言 | 说明 | 文件数 |
|---|---|---|
| [Redshift](redshift.md) | AWS 云数仓 | 51 |
| [Azure Synapse](synapse.md) | 微软云数仓 | 51 |
| [Databricks SQL](databricks.md) | Lakehouse 平台 | 51 |
| [Greenplum](greenplum.md) | MPP 数据库（基于 PostgreSQL） | 51 |
| [Impala](impala.md) | Hadoop SQL 引擎 | 51 |
| [Vertica](vertica.md) | 列式分析数据库 | 51 |
| [Teradata](teradata.md) | 老牌 MPP 数仓 | 51 |

## 分布式 / NewSQL

| 方言 | 说明 | 文件数 |
|---|---|---|
| [TiDB](tidb.md) | 分布式数据库（兼容 MySQL） | 51 |
| [OceanBase](oceanbase.md) | 分布式数据库（兼容 MySQL/Oracle） | 51 |
| [CockroachDB](cockroachdb.md) | 分布式数据库（兼容 PostgreSQL） | 51 |
| [Spanner](spanner.md) | Google 全球分布式数据库 | 51 |
| [YugabyteDB](yugabytedb.md) | 分布式数据库（兼容 PostgreSQL） | 51 |
| [PolarDB](polardb.md) | 阿里云云原生数据库 | 51 |
| [openGauss](opengauss.md) | 华为开源数据库 | 51 |
| [TDSQL](tdsql.md) | 腾讯云分布式数据库 | 51 |

## 国产数据库

| 方言 | 说明 | 文件数 |
|---|---|---|
| [达梦](dameng.md) | 国产数据库（兼容 Oracle） | 51 |
| [人大金仓](kingbase.md) | 国产数据库（兼容 PostgreSQL/Oracle） | 51 |

## 时序数据库

| 方言 | 说明 | 文件数 |
|---|---|---|
| [TimescaleDB](timescaledb.md) | 时序数据库（PostgreSQL 扩展） | 51 |
| [TDengine](tdengine.md) | 时序数据库（涛思数据） | 51 |

## 流处理

| 方言 | 说明 | 文件数 |
|---|---|---|
| [ksqlDB](ksqldb.md) | Kafka 流处理 SQL | 51 |
| [Materialize](materialize.md) | 流式物化视图 | 51 |

## 嵌入式 / 轻量

| 方言 | 说明 | 文件数 |
|---|---|---|
| [H2](h2.md) | Java 嵌入式数据库 | 51 |
| [Derby](derby.md) | Apache Java 嵌入式数据库 | 51 |

## SQL 标准

| 方言 | 说明 | 文件数 |
|---|---|---|
| [SQL 标准](sql-standard.md) | SQL-86 ~ SQL:2023 标准演进 | 51 |

## 如何选择数据库

**OLTP 场景**（高并发读写、事务要求高）：MySQL/PostgreSQL 是首选开源方案，Oracle/SQL Server 是传统企业选择。
需要水平扩展时考虑 TiDB（兼容 MySQL）或 CockroachDB（兼容 PostgreSQL）。

**OLAP 场景**（大数据分析、报表查询）：ClickHouse 适合实时分析，Snowflake/BigQuery 适合云原生数仓，
Hive/Spark SQL 适合已有 Hadoop 生态的环境，DuckDB 适合单机嵌入式分析。

**混合负载（HTAP）**：TiDB、OceanBase、PolarDB 在 HTAP 方向上投入较大，
但真实 HTAP 的成熟度仍在演进中，大多数生产环境仍然是 OLTP + OLAP 分离架构。

## 兼容性族谱

迁移成本从低到高排序：
- **MySQL 兼容族**：MySQL → MariaDB/TiDB/OceanBase(MySQL模式)/PolarDB/TDSQL 迁移成本最低
- **PostgreSQL 兼容族**：PostgreSQL → CockroachDB/YugabyteDB/Greenplum/Redshift/TimescaleDB 迁移相对容易
- **Oracle 兼容族**：Oracle → 达梦/人大金仓/OceanBase(Oracle模式) 有专门的兼容层
- **Hive/Spark 族**：Hive ↔ Spark SQL ↔ Databricks ↔ Flink SQL 语法相近但细节差异不少
- **跨族迁移**（如 MySQL → PostgreSQL 或 Oracle → MySQL）需要全面审查 SQL 语法、数据类型、函数调用

## 横向对比

| 特性维度 | SQLite | ClickHouse | BigQuery | 传统 RDBMS (MySQL/PG/Oracle) |
|---|---|---|---|---|
| **架构模型** | 文件级嵌入式数据库，零配置，单写多读 | 分布式列式数据库，多节点集群，批量写入优化 | Serverless 云数仓，按查询量计费，无需运维 | 客户端-服务器架构，需安装和配置 |
| **适用场景** | 嵌入式应用、移动端、IoT、小型 Web 应用 | 实时分析、日志分析、时序数据、OLAP 场景 | 云端大数据分析、BI 报表、按需查询 | OLTP 业务系统、Web 应用后端 |
| **数据规模** | MB~GB 级（单文件限制） | TB~PB 级（分布式存储） | PB 级（Serverless 自动扩展） | GB~TB 级（单实例） |
| **成本模型** | 免费开源，零运维成本 | 开源自建或云托管 | 按扫描数据量和存储量计费 | 开源或商业许可 + 硬件成本 |
| **SQL 兼容性** | SQL 标准子集，独特的动态类型 | SQL-like 语法，有独特扩展 | GoogleSQL（标准 SQL + 扩展） | 各方言独立演进 |
