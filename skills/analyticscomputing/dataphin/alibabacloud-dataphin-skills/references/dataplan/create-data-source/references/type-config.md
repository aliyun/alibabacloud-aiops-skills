# 数据源 Type 枚举与 ConfigItemList Key 清单

> 本文件由 `scripts/split-large-skills.ts` 从 `alibabacloud-dataphin-create-data-source/SKILL.md` 抽离，遵循 agent-skills-spec 渐进披露原则（L3 资源）。

---

## Type 枚举与 Key 清单

> **✓ verified**：已实战验证，Key 列表可信
> **⚠ unverified**：仅来自 OpenAPI 元数据枚举，具体 Key 列表未验证，**请查阅该 Type 的阿里云 OpenAPI 文档末尾“补充说明”章节再填写**

### Type 枚举完整速查表（87 种）

服务端 `listDataSourceType` 返回的全量数据源类型枚举。`Conn` 列为是否支持 `check-data-source-connectivity-by-id` 连通性测试；`适用场景` 中 OFFLINE_PIPELINE = 离线集成、STREAMING_PIPELINE = 实时集成、DATAPHIN_STREAMING = 实时研发、DATAPHIN_UNIQUALITY = 质量、DATAPHIN_META_CENTER = 元数据/资产、DATAPHIN_ONESERVICE = 数据服务、OFFLINE_COMPUTE = 离线计算、DATA_PREVIEW = 数据预览、LABEL_PLATFORM = 标签平台、KNOWLEDGE_GRAPH = 知识图谱。

| Type | 展示名 | 结构 | Conn | 适用场景 |
|------|--------|------|------|----------|
| `MAX_COMPUTE` | MaxCompute | BIGDATA | ✓ | OFFLINE_PIPELINE, STREAMING_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, LABEL_PLATFORM |
| `HDFS` | HDFS | FILE | ✓ | OFFLINE_PIPELINE |
| `LOG_HUB` | Log Service (SLS) | MQ | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING |
| `POLARDB` | PolarDB | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_UNIQUALITY |
| `HBASE_0_9_4` | HBase 0.9.4 | NOSQL | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_ONESERVICE, LABEL_PLATFORM |
| `HBASE_1_1_X` | HBase 1.1.x | NOSQL | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_ONESERVICE, LABEL_PLATFORM |
| `HBASE_2_X` | HBase 2.x | NOSQL | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_ONESERVICE, LABEL_PLATFORM |
| `DRDS` | PolarDB-X (原DRDS) | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_META_CENTER, DATAPHIN_UNIQUALITY |
| `HIVE` | Hive | BIGDATA | ✓ | OFFLINE_PIPELINE, STREAMING_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_UNIQUALITY, DATAPHIN_META_CENTER, DATAPHIN_ONESERVICE, DATA_PREVIEW |
| `FTP` | FTP | FILE | ✓ | OFFLINE_PIPELINE |
| `ELASTIC_SEARCH` | Elasticsearch | NOSQL | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_ONESERVICE, LABEL_PLATFORM, DATAPHIN_META_CENTER |
| `KAFKA_9_11` | Kafka | MQ | ✓ | OFFLINE_PIPELINE, STREAMING_PIPELINE, DATAPHIN_STREAMING, LABEL_PLATFORM |
| `MYSQL` | MySQL | RELATIVE | ✓ | OFFLINE_PIPELINE, STREAMING_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE, DATAPHIN_META_CENTER, DATA_PREVIEW, LABEL_PLATFORM |
| `MONGODB` | MongoDB | NOSQL | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_ONESERVICE |
| `OSS` | OSS | FILE | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING |
| `HANA` | SAP HANA | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_UNIQUALITY, DATAPHIN_META_CENTER, DATAPHIN_ONESERVICE |
| `ROCKET_MQ` | RocketMQ | MQ | ✕ | DATAPHIN_STREAMING |
| `SQL_SERVER` | Microsoft SQL Server | RELATIVE | ✓ | OFFLINE_PIPELINE, STREAMING_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE, DATAPHIN_META_CENTER, DATA_PREVIEW |
| `DATAHUB` | DataHub | MQ | ✓ | OFFLINE_PIPELINE, STREAMING_PIPELINE, DATAPHIN_STREAMING, LABEL_PLATFORM |
| `TABLE_STORE` | Tablestore | NOSQL | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, LABEL_PLATFORM |
| `POSTGRE_SQL` | PostgreSQL | RELATIVE | ✓ | OFFLINE_PIPELINE, STREAMING_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE, DATAPHIN_META_CENTER, DATA_PREVIEW, LABEL_PLATFORM |
| `ALIYUN_HBASE` | Aliyun HBase | NOSQL | ✓ | DATAPHIN_STREAMING |
| `HOLOGRES` | Hologres | BIGDATA | ✓ | OFFLINE_PIPELINE, STREAMING_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE, DATAPHIN_META_CENTER, DATA_PREVIEW, LABEL_PLATFORM |
| `ANALYTICDB` | AnalyticDB for MySQL 2.0 | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE |
| `REDIS` | Redis | NOSQL | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING |
| `ADB_FOR_MYSQL_V3` | AnalyticDB for MySQL 3.0 | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE, DATAPHIN_META_CENTER, DATA_PREVIEW |
| `ADB_FOR_PG` | AnalyticDB for PostgreSQL | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE, LABEL_PLATFORM |
| `OCEANBASE` | OceanBase | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE, DATAPHIN_META_CENTER, DATA_PREVIEW |
| `LINDORM` | Lindorm | NOSQL | ✓ | OFFLINE_PIPELINE, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE |
| `ORACLE` | Oracle | RELATIVE | ✓ | OFFLINE_PIPELINE, STREAMING_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE, DATAPHIN_META_CENTER, DATA_PREVIEW, LABEL_PLATFORM |
| `VERTICA` | Vertica | RELATIVE | ✓ | OFFLINE_PIPELINE |
| `DB2` | IBM DB2 | RELATIVE | ✓ | OFFLINE_PIPELINE, STREAMING_PIPELINE, DATAPHIN_UNIQUALITY, DATAPHIN_META_CENTER |
| `TERA_DATA` | Teradata | RELATIVE | ✓ | OFFLINE_PIPELINE |
| `INFLUXDB` | InfluxDB | NOSQL | ✓ | OFFLINE_PIPELINE |
| `IMPALA` | Impala | BIGDATA | ✓ | OFFLINE_PIPELINE, DATAPHIN_ONESERVICE |
| `CLICKHOUSE` | ClickHouse | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE, DATAPHIN_META_CENTER, DATA_PREVIEW |
| `TDH_INCEPTOR` | TDH Inceptor | BIGDATA | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE |
| `API` | API | HALF_STRUCTURE | ✕ | OFFLINE_PIPELINE, DATAPHIN_ONESERVICE, LABEL_PLATFORM |
| `KUDU` | Kudu | BIGDATA | ✓ | OFFLINE_PIPELINE |
| `DAMENG` | DM (达梦) | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE, DATAPHIN_META_CENTER, DATA_PREVIEW |
| `GBASE_8A` | GBase 8a | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_ONESERVICE |
| `KINGBASE_ES` | KingbaseES | RELATIVE | ✓ | OFFLINE_PIPELINE |
| `TIDB` | TiDB | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING |
| `GOLDENDB` | GoldenDB | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_UNIQUALITY |
| `SAPTABLE` | SAP TABLE | HALF_STRUCTURE | ✓ | OFFLINE_PIPELINE |
| `OPENGAUSS` | openGauss | RELATIVE | ✓ | OFFLINE_PIPELINE, OFFLINE_COMPUTE, DATAPHIN_META_CENTER, LABEL_PLATFORM |
| `STARROCKS` | StarRocks | BIGDATA | ✓ | OFFLINE_PIPELINE, STREAMING_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE, DATAPHIN_META_CENTER, DATA_PREVIEW |
| `HUDI` | Hudi | BIGDATA | ✕ | DATAPHIN_STREAMING |
| `DORIS` | Doris | BIGDATA | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE, DATAPHIN_META_CENTER, DATA_PREVIEW |
| `GREENPLUM` | Greenplum | BIGDATA | ✓ | OFFLINE_PIPELINE, DATAPHIN_META_CENTER, DATA_PREVIEW, LABEL_PLATFORM |
| `ARGODB` | ArgoDB | BIGDATA | ✓ | OFFLINE_PIPELINE, DATAPHIN_UNIQUALITY |
| `DW_OPENAPI` | Dataworks-公共云元数据库 | APPLICATION | ✕ | (DataWorks 平台专用) |
| `QBI_OPENAPI` | Quick BI-OpenAPI | APPLICATION | ✕ | (Quick BI 平台专用) |
| `SALESFORCE` | Salesforce | HALF_STRUCTURE | ✓ | OFFLINE_PIPELINE |
| `TDENGINE` | TDengine | BIGDATA | ✓ | OFFLINE_PIPELINE, DATAPHIN_ONESERVICE |
| `AMAZONS3` | Amazon S3 | FILE | ✓ | OFFLINE_PIPELINE |
| `PAIMON` | Paimon | BIGDATA | ✓ | DATAPHIN_STREAMING |
| `SELECTDB` | SelectDB | BIGDATA | ✓ | OFFLINE_PIPELINE, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE, DATAPHIN_META_CENTER, DATA_PREVIEW |
| `PRESTO` | Presto | NOSQL | ✓ | OFFLINE_COMPUTE |
| `GAUSSDB` | GaussDB(DWS) | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_STREAMING, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE |
| `DATABRICKS` | Databricks | BIGDATA | ✓ | OFFLINE_PIPELINE, STREAMING_PIPELINE, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE |
| `RABBITMQ` | RabbitMQ | MQ | ✕ | DATAPHIN_STREAMING |
| `AWS_MYSQL` | Amazon RDS for MySQL | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, DATAPHIN_META_CENTER |
| `AWS_POSTGRE_SQL` | Amazon RDS for PostgreSQL | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, DATAPHIN_META_CENTER |
| `AWS_SQL_SERVER` | Amazon RDS for SQL Server | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, DATAPHIN_META_CENTER |
| `AWS_ORACLE` | Amazon RDS for Oracle | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, DATAPHIN_META_CENTER |
| `AWS_DB2` | Amazon RDS for DB2 | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_UNIQUALITY, DATAPHIN_META_CENTER |
| `AWS_REDSHIFT` | Amazon Redshift | BIGDATA | ✓ | OFFLINE_PIPELINE, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, DATAPHIN_META_CENTER |
| `TDSQL_FOR_MYSQL` | TDSQL for MySQL | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_UNIQUALITY, DATAPHIN_META_CENTER, DATA_PREVIEW |
| `DOLPHINDB` | DolphinDB | BIGDATA | ✓ | OFFLINE_PIPELINE, DATAPHIN_ONESERVICE, DATAPHIN_META_CENTER |
| `TRINO` | Trino | NOSQL | ✓ | OFFLINE_COMPUTE |
| `EASY_SEARCH` | Easysearch | NOSQL | ✓ | OFFLINE_PIPELINE |
| `GBASE_8C` | GBase 8c | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_ONESERVICE |
| `POLARDB_X2` | PolarDB-X 2.0 | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_UNIQUALITY, DATAPHIN_ONESERVICE, OFFLINE_COMPUTE |
| `LARK_BASE` | 飞书多维表格 | HALF_STRUCTURE | ✓ | OFFLINE_PIPELINE |
| `OPENSEARCH` | OpenSearch | NOSQL | ✓ | OFFLINE_PIPELINE, DATAPHIN_ONESERVICE |
| `SNOWFLAKE` | Snowflake | BIGDATA | ✓ | OFFLINE_PIPELINE |
| `DLFV3` | Data Lake Formation | BIGDATA | ✓ | OFFLINE_PIPELINE |
| `NEO4J` | Neo4j | HALF_STRUCTURE | ✓ | KNOWLEDGE_GRAPH |
| `OUSHUDB` | OushuDB | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_UNIQUALITY, OFFLINE_COMPUTE |
| `TDSQL_FOR_PG` | TDSQL for PostgreSQL | RELATIVE | ✓ | OFFLINE_PIPELINE, DATAPHIN_META_CENTER |
| `ALI_DING_DOC` | 阿里钉 AI 表格 | HALF_STRUCTURE | ✕ | OFFLINE_PIPELINE |
| `DATAWORKS_DWTSP` | Dataworks-代码元数据库 | APPLICATION | ✓ | (DataWorks 平台专用) |
| `DATAWORKS_DWPHOENIX` | Dataworks-节点元数据库 | APPLICATION | ✓ | (DataWorks 平台专用) |
| `DATAWORKS_DWBIZTENANT` | Dataworks-租户元数据库 | APPLICATION | ✓ | (DataWorks 平台专用) |
| `DATAWORKS_DWDQC` | Dataworks-数据质量元数据库 | APPLICATION | ✓ | (DataWorks 平台专用) |
| `QUICKBI_PUBLICMETADATA` | Quick BI-公共元数据库 | APPLICATION | ✓ | (Quick BI 平台专用) |

> 本表与 CLI `--help` 中 `--type` / `--type-list` / `--support-data-source-type-list` / `ProdDataSourceCreate.Type` 等字段的 `allowed:` 清单走同一份 `scripts/data-source-types.ts` 数据源，保持完全一致。如需追加/修改枚举值，请仅在该文件中改动后执行：`npm run generate:commands && npm run generate:manual && npm run generate:pdf`。

### ✓ MYSQL

#### 公网（PUBLIC）

```bash
dataphin platform create-data-source \
  --tenant-id <tenant-id> \
  --prod-data-source-create '{
    "Type": "MYSQL",
    "Name": "<datasource-name>",
    "Description": "<description>",
    "CheckActivity": true,
    "ConfigItemList": [
      { "Key": "jdbc.url",      "Value": "jdbc:mysql://<host>:<port>/<db>?allowUrlInLocalInfile=false&autoDeserialize=false&allowLocalInfile=false&allowLoadLocalInfile=false" },
      { "Key": "jdbc.username", "Value": "<your-db-username>" },
      { "Key": "jdbc.password", "Value": "<your-db-password>" },
      { "Key": "version",       "Value": "<mysql-version>" },
      { "Key": "deploy.type",   "Value": "PUBLIC" },
      { "Key": "access.type",   "Value": "PUBLIC" }
    ]
  }'
```

#### VPC（RDS 实例）

```bash
dataphin platform create-data-source \
  --tenant-id <tenant-id> \
  --prod-data-source-create '{
    "Type": "MYSQL",
    "Name": "<datasource-name>",
    "Description": "<description>",
    "CheckActivity": true,
    "ConfigItemList": [
      { "Key": "jdbc.url",        "Value": "jdbc:mysql://<vpc-host>:<port>/<db>?allowUrlInLocalInfile=false&autoDeserialize=false&allowLocalInfile=false&allowLoadLocalInfile=false" },
      { "Key": "jdbc.username",   "Value": "<your-db-username>" },
      { "Key": "jdbc.password",   "Value": "<your-db-password>" },
      { "Key": "version",         "Value": "<mysql-version>" },
      { "Key": "deploy.type",     "Value": "RDS" },
      { "Key": "access.type",     "Value": "VPC" },
      { "Key": "vpc.id",          "Value": "<vpc-id>" },
      { "Key": "vpc.region.id",   "Value": "<region-id>" },
      { "Key": "vpc.instance.id", "Value": "<rds-instance-id>" }
    ]
  }'
```

> ❗ **JDBC URL 安全参数**：MySQL 的 jdbc.url 必须追加 `?allowUrlInLocalInfile=false&autoDeserialize=false&allowLocalInfile=false&allowLoadLocalInfile=false`，否则服务端返回 `DATASOURCE_CONNECT_URL_NOT_SAFE_V2` 错误拒绝创建。

### ✓ MAX_COMPUTE

最小必填骨架：

```jsonc
{
  "Type": "MAX_COMPUTE",
  "Name": "dp_mc",
  "CheckActivity": true,
  "ConfigItemList": [
    { "Key": "maxcompute.access.id", "Value": "<ak_id>" },
    { "Key": "maxcompute.access.key", "Value": "<ak_secret>" },
    { "Key": "maxcompute.endpoint", "Value": "<endpoint>" },
    { "Key": "maxcompute.project", "Value": "<odps_project_name>" },   // odps 即 MaxCompute 旧称，project 名需与 MaxCompute 控制台一致
    { "Key": "deploy.type", "Value": "RDS" }
  ]
}
```

> ❗ **踩坑警告**：早期 skill 写的是 `jdbc.username`/`jdbc.password`，这是**计算源**的 Key，不是数据源。MaxCompute **数据源**正确 Key 为 `maxcompute.access.id` / `maxcompute.access.key`，若用错 Key，页面上 AccessKey / AccessSecret 显示为空。
>
> 💡 **术语**：ODPS（Open Data Processing Service）是 MaxCompute 的旧名称，在配置项、API 参数、文档中仍可能出现 `odps` 字样（如 `odps_project_name`、`odps.endpoint`），均指 MaxCompute。


### ✓ STARROCKS / DORIS / SELECTDB

StarRocks 和 Doris 共享相同的 ConfigItemList 结构（StarRocks 是 Apache Doris 的分支）。Type 枚举值分别为 `STARROCKS` 和 `DORIS`（均为连写全大写，**不是** `STAR_ROCKS`）。

```bash
dataphin platform create-data-source \
  --tenant-id <tenant-id> \
  --prod-data-source-create '{
    "Type": "STARROCKS",           # 或 "DORIS"、"SELECTDB"
    "Name": "<datasource-name>",
    "Description": "<description>",
    "CheckActivity": true,
    "ConfigItemList": [
      { "Key": "jdbc.url",        "Value": "jdbc:mysql:loadbalance://<fe1-host>:<query-port>,<fe2-host>:<query-port>,<fe3-host>:<query-port>/<database>" },
      { "Key": "fenodes",         "Value": "<fe1-host>:<http-port>,<fe2-host>:<http-port>,<fe3-host>:<http-port>" },
      { "Key": "load.url",        "Value": "<fe1-host>:<http-port>,<fe2-host>:<http-port>,<fe3-host>:<http-port>" },
      { "Key": "jdbc.username",   "Value": "<your-db-username>" },
      { "Key": "jdbc.password",   "Value": "<your-db-password>" },
      { "Key": "deploy.type",     "Value": "RDS" },
      { "Key": "access.type",     "Value": "PUBLIC" },
      { "Key": "connectTimeout",  "Value": "900000" },
      { "Key": "socketTimeout",   "Value": "1800000" },
      { "Key": "reconnectTimes",  "Value": "1" }
    ]
  }'
```

> **关键点**：
> - `jdbc.url` 支持两种格式：
>   - 负载均衡（多 FE）：`jdbc:mysql:loadbalance://fe1:9030,fe2:9030,fe3:9030/db`
>   - 单节点：`jdbc:mysql://host:9030/db`
> - ⚠ **`fenodes` 和 `load.url` 必须同时填写**，值相同（FE 的 HTTP 端口列表）。`fenodes` 是页面展示 "Load URL" 的实际 Key；仅填 `load.url` 会导致页面 Load URL 字段显示为空
> - 查询端口（JDBC）通常为 `9030`/`9031`，HTTP 端口通常为 `8030`/`8041`（以实际集群为准）
> - `deploy.type` 推荐 `RDS`（与页面保存行为一致）
> - 无需 `version` 字段（与 MySQL 不同）
> - 无需 MySQL 的安全参数后缀

---

### ✓ POSTGRE_SQL

PostgreSQL 数据源。Type 枚举值为 `POSTGRE_SQL`（注意下划线，**不是** `POSTGRESQL`）。

#### 自建（ECS）

```bash
dataphin platform create-data-source \
  --tenant-id <tenant-id> \
  --prod-data-source-create '{
    "Type": "POSTGRE_SQL",
    "Name": "<datasource-name>",
    "Description": "<description>",
    "CheckActivity": true,
    "ConfigItemList": [
      { "Key": "jdbc.url",             "Value": "jdbc:postgresql://<host>:<port>/<database>" },
      { "Key": "jdbc.username",        "Value": "<your-db-username>" },
      { "Key": "jdbc.password",        "Value": "<your-db-password>" },
      { "Key": "jdbc.database.schema", "Value": "public" },
      { "Key": "deploy.type",          "Value": "ECS" },
      { "Key": "access.type",          "Value": "PUBLIC" }
    ]
  }'
```

> **关键点**：
> - JDBC URL 格式：`jdbc:postgresql://host:port/database`，端口通常 `5432`
> - `jdbc.database.schema` 建议填写（通常 `public`），不填可能导致元数据探测异常
> - 服务端会自动从 JDBC URL 解析出 `jdbc.database` 字段（无需手动传）
> - 自建用 `deploy.type=ECS`，阿里云 RDS 用 `deploy.type=RDS`
> - 无需 `version` 字段（与 MySQL 不同）
> - 无需 MySQL 的安全参数后缀

---

### ✓ CLICKHOUSE

ClickHouse 数据源。Type 枚举值为 `CLICKHOUSE`（连写全大写，**不是** `CLICK_HOUSE`）。

#### 阿里云 ClickHouse 服务（公网）

```bash
dataphin platform create-data-source \
  --tenant-id <tenant-id> \
  --prod-data-source-create '{
    "Type": "CLICKHOUSE",
    "Name": "<datasource-name>",
    "Description": "<description>",
    "CheckActivity": true,
    "ConfigItemList": [
      { "Key": "jdbc.url",             "Value": "jdbc:clickhouse://<host>:<port>/<database>" },
      { "Key": "jdbc.username",        "Value": "<your-db-username>" },
      { "Key": "jdbc.password",        "Value": "<your-db-password>" },
      { "Key": "jdbc.database.schema", "Value": "<database>" },
      { "Key": "deploy.type",          "Value": "RDS" },
      { "Key": "access.type",          "Value": "PUBLIC" }
    ]
  }'
```

#### 自建（ECS）

仅需把 `deploy.type` 由 `RDS` 改为 `ECS`，`jdbc.url` 改成自建实例的 host:port，其余 Key 完全一致。

> **关键点**：
> - JDBC URL 格式：`jdbc:clickhouse://host:port/database`
> - **端口选择**：HTTP 协议端口 `8123`（普通 JDBC）；HTTPS/SSL 端口 `8443`。阿里云 ClickHouse 服务两个端口都开放，推荐使用 `8123`（除非要求 SSL）
> - `jdbc.database.schema` 推荐填写，值通常与 URL 中 database 同名（ClickHouse 中 database 与 schema 概念合一）
> - 阿里云 ClickHouse 服务用 `deploy.type=RDS`，自建用 `ECS`，纯公网开放可用 `PUBLIC`
> - 无需 `version` 字段（与 MySQL 不同），无需 MySQL 的安全参数后缀
> - ClickHouse JDBC Driver 服务端预置无需上传

---

### ✓ HANA

SAP HANA 数据源。Type 枚举值为 `HANA`。

```bash
dataphin platform create-data-source \
  --tenant-id <tenant-id> \
  --prod-data-source-create '{
    "Type": "HANA",
    "Name": "<datasource-name>",
    "Description": "<description>",
    "CheckActivity": true,
    "ConfigItemList": [
      { "Key": "jdbc.url",             "Value": "jdbc:sap://<host>:<port>?databaseName=<database>" },
      { "Key": "jdbc.username",        "Value": "<your-db-username>" },
      { "Key": "jdbc.password",        "Value": "<your-db-password>" },
      { "Key": "jdbc.database.schema", "Value": "<schema-name>" },
      { "Key": "deploy.type",          "Value": "ECS" },
      { "Key": "access.type",          "Value": "PUBLIC" }
    ]
  }'
```

> **关键点**：
> - JDBC URL 格式：`jdbc:sap://host:port?databaseName=<db>`（注意是 `?databaseName=` 查询参数，不是路径形式）
> - 端口通常为 `30015`（生产）或 `39041`（HXE Express），**不是** PostgreSQL/MySQL 的常规端口
> - `jdbc.database.schema` 必填（与 SQL Server 类似），不填会导致元数据探测失败
> - 服务端会自动从 URL 的 `databaseName=` 参数解析出 `jdbc.database` 字段作为独立配置项
> - 驱动依赖：SAP HANA JDBC Driver（`ngdbc`），服务端预置无需上传

---

### 其他数据源类型 ConfigItemList Key 完整参考

> 来源：[CreateDataSource 官方文档 § ConfigItemList 参数 Key 说明](https://next.api.aliyun.com/document/dataphin-public/2023-06-30/CreateDataSource#configitemlist-%E5%8F%82%E6%95%B0-key-%E8%AF%B4%E6%98%8E)

#### MYSQL

| Key | 必填 | 说明 |
|-----|------|------|
| `jdbc.url` | 是 | JDBC 连接串 |
| `jdbc.username` | 是 | 数据库用户名 |
| `jdbc.password` | 是 | 数据库密码 |
| `version` | 是 | MySQL 版本枚举：`MYSQL_5_1_43`（MySQL5.1.43）/ `MYSQL_5_X`（MySQL5.6/5.7）/ `MYSQL_8_X`（MySQL8.0.x）/ `MYSQL_8_4_X`（MySQL8.4.x）/ `RDS_MYSQL`（RDS MySQL） |
| `deploy.type` | 是 | 部署类型：PUBLIC（公网）/ RDS（阿里云）/ ECS（自建） |
| `access.type` | 是 | 访问方式：PUBLIC / VPC |
| `vpc.id` | 否 | VPC 环境下需要 |
| `vpc.region.id` | 否 | VPC 环境下需要 |
| `vpc.instance.id` | 否 | VPC 环境下需要 |

#### DRDS / POSTGRE_SQL / ORACLE / VERTICA / ANALYTICDB / ADB_FOR_MYSQL_V3（AnalyticDB for MySQL）/ ADB_FOR_PG（AnalyticDB for PostgreSQL）

此组共享相同 Key 结构：

| Key | 必填 | 说明 |
|-----|------|------|
| `jdbc.url` | 是 | JDBC 连接串 |
| `jdbc.username` | 是 | |
| `jdbc.password` | 是 | |
| `jdbc.database.schema` | 推荐 | 如有 schema 最好填写（如 `public`、`dbo`），不填可能导致元数据探测异常 |
| `deploy.type` | 是 | PUBLIC / RDS / ECS |
| `access.type` | 是 | PUBLIC / VPC |
| `vpc.id` | 是 | VPC 环境下需要 |
| `vpc.region.id` | 是 | VPC 环境下需要 |
| `vpc.instance.id` | 是 | VPC 环境下需要 |

#### SQL_SERVER

| Key | 必填 | 说明 |
|-----|------|------|
| `jdbc.url` | 是 | 如 `jdbc:sqlserver://host:1433;DatabaseName=xxx;` |
| `jdbc.username` | 是 | |
| `jdbc.password` | 是 | |
| `jdbc.database.schema` | 是 | schema 名称（如 `dbo`），不填会导致元数据探测失败 |
| `deploy.type` | 是 | PUBLIC / RDS / ECS |
| `access.type` | 是 | PUBLIC / VPC |
| `vpc.id` | 否 | VPC 环境下需要 |
| `vpc.region.id` | 否 | VPC 环境下需要 |
| `vpc.instance.id` | 否 | VPC 环境下需要 |

#### DB2

| Key | 必填 | 说明 |
|-----|------|------|
| `jdbc.url` | 是 | |
| `jdbc.username` | 是 | |
| `jdbc.password` | 是 | |

#### POLARDB

| Key | 必填 | 说明 |
|-----|------|------|
| `jdbc.url` | 是 | |
| `jdbc.username` | 是 | |
| `jdbc.password` | 是 | |
| `jdbc.database.schema` | 是 | |
| `deploy.type` | 是 | PUBLIC / RDS / ECS |
| `access.type` | 是 | PUBLIC / VPC |
| `vpc.id` | 否 | VPC 环境下需要 |
| `vpc.region.id` | 否 | VPC 环境下需要 |
| `vpc.instance.id` | 否 | VPC 环境下需要 |
| `backend.db.type` | 是 | backend 数据库类型：MYSQL / POSTGRE_SQL |

#### HIVE

| Key | 必填 | 说明 |
|-----|------|------|
| `hive.version` | 是 | Hive 版本枚举（来自页面下拉框）：`CDH5_HIVE_1_1_0`（CDH5.x Hive 1.1.0）/ `EMR3_HIVE_2_3_5`（Aliyun EMR3.x Hive 2.3.5）/ `EMR5_HIVE_3_1_0`（Aliyun EMR5.x Hive 3.1.x）/ `CDH6_HIVE_2_1_1`（CDH6.x Hive 2.1.1）/ `FusionInsight8_HIVE_3_1_0`（FusionInsight 8.x）/ `CDP7_HIVE_3_1_3`（CDP7.x Hive 3.1.3）/ `ASINFO_DP5_HIVE_3_1_0`（亚信DP5.x）/ `Amazon_EMR` |
| `hadoop.namenode` | 是 | 支持 host/IP，例: host=192.168.1.1,webUiPort=50070,ipcPort=8020 |
| `hadoop.kerberos.switch` | 是 | hadoop 集群是否开启 kerberos 认证 |
| `kerberos.config` | 是 | Kerberos 配置方式: kdc 或 krb |
| `hadoop.kdc.address` | 否 | 如有 krb5.config.file 可不写 |
| `hadoop.kerberos.krb5.config.file` | 否 | 如有 kdc.address 可不写 |
| `hive.kerberos.switch` | 是 | TRUE / FALSE，hive 是否开启 kerberos |
| `hive.kerberos.keytab.file` | 否 | kerberos 开启时需要 |
| `hive.kerberos.keytab.filename` | 否 | |
| `hive.kerberos.principal` | 否 | hive principal |
| `hive.jdbc.url` | 是 | hive 连接串（暂不支持 ZK 方式 <v2.9.2） |
| `hive.jdbc.username` | 否 | kerberos 认证时可不填 |
| `hive.jdbc.password` | 否 | kerberos 认证时可不填 |
| `meta.type` | 是 | 元数据类型：DB / HMS |
| `hive.meta.db.type` | 否 | meta.type=DB 时必填，MYSQL / POSTGRE_SQL |
| `hive.meta.jdbc.url` | 否 | metastore 数据库连接信息 |
| `hive.meta.jdbc.username` | 否 | |
| `hive.meta.jdbc.password` | 否 | |
| `hms.kerberos.keytab.file` | 否 | HMS 连接信息 |
| `hms.kerberos.keytab.filename` | 否 | |
| `hms.kerberos.principal` | 否 | |
| `hms.hive.site.file` | 否 | |
| `hms.hive.site.filename` | 否 | |
| `hdfs.kerberos.switch` | 是 | TRUE / FALSE，HDFS 是否开启 kerberos |
| `hdfs.kerberos.keytab.file` | 否 | HDFS principal 认证文件 ID |
| `hdfs.kerberos.keytab.filename` | 否 | |
| `hdfs.kerberos.principal` | 否 | 如 xxx/master@DATAPHIN.COM |

#### HDFS

| Key | 必填 | 说明 |
|-----|------|------|
| `hdfs.defaultFs` | 是 | defaultFs 地址，如 namenode:8020 |
| `hdfs.kerberos.switch` | 是 | TRUE / FALSE |
| `hdfs.kerberos.keytab.file` | 否 | kerberos 开启时必填 |
| `hdfs.kerberos.keytab.filename` | 否 | kerberos 开启时必填 |
| `hdfs.kerberos.principal` | 否 | kerberos 开启时必填，如 xxx/master@DATAPHIN.COM |
| `hadoop.kdc.address` | 否 | 如有 krb5.config.file 可不写 |
| `hadoop.kerberos.krb5.config.file` | 否 | 如有 kdc.address 可不写 |
| `hadoop.kerberos.krb5.config.filename` | 是 | krb5.config 文件名称 |

#### HBASE_0_9_4 / HBASE_1_1_X

| Key | 必填 | 说明 |
|-----|------|------|
| `hbase.cluster` | 是 | HBase 集群连接串，支持 ZK |
| `hbase.connection.param` | 否 | 连接参数 |
| `hbase.kerberos.switch` | 是 | TRUE / FALSE |
| `hbase.kerberos.keytab.file` | 否 | kerberos 开启时需要 |
| `hbase.kerberos.principal` | 否 | |
| `hadoop.kdc.address` | 否 | 如有 krb5.config.file 可不写 |
| `hadoop.kerberos.krb5.config.file` | 否 | 如有 kdc.address 可不写 |

#### LOG_HUB（阿里云 SLS）

| Key | 必填 | 说明 |
|-----|------|------|
| `endPoint` | 是 | SLS endpoint |
| `accessId` | 是 | 阿里云 AK ID |
| `accessKey` | 是 | 阿里云 AK Secret |
| `projectName` | 是 | SLS project 名称 |

#### FTP

| Key | 必填 | 说明 |
|-----|------|------|
| `ftp.protocol` | 是 | 协议类型 |
| `ftp.host` | 是 | |
| `ftp.port` | 是 | |
| `ftp.username` | 是 | |
| `ftp.password` | 是 | |

#### ELASTIC_SEARCH

| Key | 必填 | 说明 |
|-----|------|------|
| `url` | 是 | ES 连接地址 |
| `username` | 是 | |
| `password` | 是 | |

#### MONGODB

| Key | 必填 | 说明 |
|-----|------|------|
| `mongodb.jdbc.url` | 是 | MongoDB 连接串 |
| `mongodb.jdbc.username` | 是 | |
| `mongodb.jdbc.password` | 是 | |

#### OSS

| Key | 必填 | 说明 |
|-----|------|------|
| `endpoint` | 是 | OSS endpoint |
| `bucket` | 是 | OSS bucket |
| `accessId` | 是 | 阿里云 AK ID |
| `accessKey` | 是 | 阿里云 AK Secret |
| `CNAME` | 否 | 自定义域名 |

#### STARROCKS / DORIS

StarRocks 和 Doris 共享相同 Key 结构：

| Key | 必填 | 说明 |
|-----|------|------|
| `jdbc.url` | 是 | JDBC 连接串，支持 `jdbc:mysql:loadbalance://` 多节点或 `jdbc:mysql://` 单节点 |
| `fenodes` | 是 | FE 的 HTTP 端口列表，格式 `host:port,host:port`。**页面展示 Load URL 的实际 Key** |
| `load.url` | 是 | 与 `fenodes` 同值，用于 Stream Load。**必须与 `fenodes` 同时填写** |
| `jdbc.username` | 是 | 数据库用户名 |
| `jdbc.password` | 是 | 数据库密码 |
| `deploy.type` | 是 | RDS（推荐）/ PUBLIC / ECS |
| `access.type` | 是 | PUBLIC / VPC |
| `connectTimeout` | 否 | 连接超时（毫秒），默认 900000（15 分钟） |
| `socketTimeout` | 否 | Socket 超时（毫秒），默认 1800000（30 分钟） |
| `reconnectTimes` | 否 | 连接重试次数，默认 1，范围 0~10 |

#### HANA / TERA_DATA

官方文档未单独列出 Key 说明，实际验证后 Key 结构与 POSTGRE_SQL 一致：

| Key | 必填 | 说明 |
|-----|------|------|
| `jdbc.url` | 是 | HANA 格式：`jdbc:sap://host:port?databaseName=<db>`；TERA_DATA 格式：`jdbc:teradata://host/DATABASE=<db>` |
| `jdbc.username` | 是 | |
| `jdbc.password` | 是 | |
| `jdbc.database.schema` | 是 | HANA 必填（服务端读元数据依赖此字段） |
| `deploy.type` | 是 | PUBLIC / RDS / ECS |
| `access.type` | 是 | PUBLIC / VPC |

> HANA 实战验证说明见 上方 § `✓ HANA` 章节。

#### CLICKHOUSE

实际验证后 Key 结构与 POSTGRE_SQL 共享组一致：

| Key | 必填 | 说明 |
|-----|------|------|
| `jdbc.url` | 是 | 格式 `jdbc:clickhouse://host:port/database`；HTTP 端口默认 `8123`，HTTPS 端口默认 `8443` |
| `jdbc.username` | 是 | |
| `jdbc.password` | 是 | |
| `jdbc.database.schema` | 推荐 | 一般与 URL 中 database 同名（ClickHouse 中 database 与 schema 概念合一） |
| `deploy.type` | 是 | PUBLIC / RDS（阿里云 ClickHouse 服务）/ ECS（自建） |
| `access.type` | 是 | PUBLIC / VPC |
| `vpc.id` / `vpc.region.id` / `vpc.instance.id` | 否 | VPC 反向访问时需要 |

> CLICKHOUSE 实战验证说明见 上方 § `✓ CLICKHOUSE` 章节。

---

> **deploy.type 通用规则**：私有化环境通常使用 `RDS` 或 `ECS`；公共云需要反向 VPC 打通时使用 `RDS` + `access.type=VPC`；纯公网访问用 `PUBLIC`。
