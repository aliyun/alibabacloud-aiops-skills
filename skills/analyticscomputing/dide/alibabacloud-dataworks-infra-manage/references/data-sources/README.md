# DataWorks Data Source Reference

Supports a total of **50** data source types (verified through API testing).

> **Note**: The following types do not currently support OpenAPI, please configure through the console (Support will be added in future versions): `hdfs`

---

## Workspace Mode and Data Source Configuration

> **Important**: Workspace mode (Simple Mode / Standard Mode) directly affects the number and configuration of data sources. Workspace mode must be confirmed before creating data sources.

### Query Workspace Mode

```bash
aliyun dataworks-public GetProject --user-agent AlibabaCloud-Agent-Skills --Id <PROJECT_ID> 2>/dev/null | jq '.Project | {Id, Name, DevEnvironmentEnabled}'
```

- `DevEnvironmentEnabled: false` → Simple Mode
- `DevEnvironmentEnabled: true` → Standard Mode

### Simple Mode vs Standard Mode

| Dimension | Simple Mode | Standard Mode |
|-----------|-------------|---------------|
| Number of environments | 1 (Production environment) | 2 (Development + Production) |
| Number of data sources | 1 | 2 (Physically isolated) |
| Data source name | Any | Dev/Prod can share the same name |
| envType | Only `Prod` | `Dev` + `Prod` |
| Code editing | Edit production code directly | Edit only in development environment |
| Release process | Submit and schedule directly | Submit → Publish → Schedule |

### Data Source Creation Strategy

#### Simple Mode Workspace

Only need to create **1 data source**, `envType` fixed as `Prod`:

```json
{
  "envType": "Prod",
  "instanceId": "rm-xxxxx",
  "database": "prod_db",
  "username": "root",
  "password": "<PASSWORD>"
}
```

#### Standard Mode Workspace

Must create **2 data sources** (Physically isolated), can use the same name:

**Production environment data source**:
```json
{
  "envType": "Prod",
  "instanceId": "rm-prod-xxxxx",
  "database": "prod_db",
  "username": "root",
  "password": "<PASSWORD>"
}
```

**Development environment data source** (same name):
```json
{
  "envType": "Dev",
  "instanceId": "rm-dev-xxxxx",
  "database": "dev_db",
  "username": "dev_user",
  "password": "<PASSWORD>"
}
```

### Physical Isolation Approaches (Standard Mode)

Standard Mode requires dev/prod data sources to be **physically isolated**. Recommended approaches:

| Isolation approach | Description | Applicable scenarios |
|--------------------|-------------|----------------------|
| Different instances | Dev uses `rm-dev-xxx`, Prod uses `rm-prod-xxx` | **Recommended**, Complete isolation |
| Same instance, different databases | Dev uses `dev_db`, Prod uses `prod_db` | Cost-sensitive scenarios |

> **Best practice**: Before creating data sources, confirm the workspace mode first. For Standard Mode, guide users to create both development and production data sources.

---

## Cross-Account Data Source Quick Reference

### Data Source Types Supporting Cross-Account

| Type | Type | Connection Mode | authType | Cross-account specific parameters |
|------|------|-----------------|----------|-----------------------------------|
| MaxCompute | maxcompute | UrlMode | RamRole | project, endpointMode |
| Hologres | hologres | InstanceMode | RamRole | instanceId, database |
| MySQL | mysql | InstanceMode | - | instanceId, username, password |
| PostgreSQL | postgresql | InstanceMode | - | instanceId, username, password |
| PolarDB | polardb | InstanceMode | - | clusterId, dbType, username, password |
| SQLServer | sqlserver | InstanceMode | - | instanceId, username, password |
| AnalyticDB MySQL | analyticdb_for_mysql | InstanceMode | - | instanceId, username, password |
| AnalyticDB PostgreSQL | analyticdb_for_postgresql | InstanceMode | - | instanceId, username, password |
| StarRocks | starrocks | InstanceMode | - | instanceId, instanceType, username, password |

### Cross-Account Common Parameters

All cross-account data sources require:
- `crossAccountOwnerId`: Alibaba Cloud UID of the target account
- `crossAccountRoleName`: RAM role name in the target account

### Configuration Differences

**MaxCompute / Hologres**:
- Must set `authType: RamRole`
- Does not require `username` and `password`

**Other types** (MySQL/PostgreSQL/SQLServer/PolarDB/AnalyticDB/StarRocks):
- Does not require setting `authType`
- Must provide `username` and `password`
- PolarDB uses `clusterId` instead of `instanceId`
- StarRocks must provide `instanceType` (`emr-olap` or `serverless`)

### Detailed Configuration Documentation

For detailed cross-account configuration of each data source type, please refer to the corresponding documentation:
- [maxcompute.md](maxcompute.md)
- [hologres.md](hologres.md)
- [mysql.md](mysql.md)
- [postgresql.md](postgresql.md)
- [polardb.md](polardb.md)
- [sqlserver.md](sqlserver.md)
- [analyticdb_for_mysql.md](analyticdb_for_mysql.md)
- [analyticdb_for_postgresql.md](analyticdb_for_postgresql.md)
- [starrocks.md](starrocks.md)

---

## Type List

### Relational Databases (18)

| Type | Name | UrlMode | InstanceMode | Notes |
|------|------|---------|-------------|-------|
| mysql | MySQL | Yes | Yes | |
| postgresql | PostgreSQL | Yes | Yes | |
| oracle | Oracle | Yes | No | Uses jdbcUrl format |
| sqlserver | SQL Server | Yes | Yes | |
| polardb | PolarDB MySQL | Yes | Yes | Requires dbType |
| polardbo | PolarDB for Oracle | Yes | Yes | InstanceMode requires instanceId/regionId |
| polardb-x-2-0 | PolarDB-X 2.0 | Yes | Yes | InstanceMode requires instanceId/regionId |
| apsaradb_for_oceanbase | OceanBase | Yes | Yes | InstanceMode requires instanceId/tenant/regionId, UrlMode requires dbMode |
| mariadb | MariaDB | Yes | No | |
| dm | DM (Dameng) | Yes | No | Does not require the database field |
| db2 | DB2 | Yes | No | Requires jdbcDriver parameter |
| tidb | TiDB | Yes | No | |
| vertica | Vertica | Yes | No | |
| gbase8a | GBase 8a | Yes | No | |
| kingbasees | KingbaseES | Yes | No | |
| saphana | SAP HANA | Yes | No | |
| drds | DRDS | Yes | Yes | |
| snowflake | Snowflake | Yes | No | Requires accountUrl |

### Big Data Engines (13)

| Type | Name | UrlMode | InstanceMode | Notes |
|------|------|---------|-------------|-------|
| maxcompute | MaxCompute | Yes | No | Requires project parameter |
| hologres | Hologres | No | Yes | Only supports InstanceMode |
| hive | Hive | Yes | No | Requires version/metaType/metastoreUris |
| clickhouse | ClickHouse | Yes | No | |
| starrocks | StarRocks | Yes | Yes | InstanceMode requires instanceType |
| doris | Doris | Yes | No | Requires loadAddress |
| selectdb | SelectDB | Yes | No | Requires loadAddress |
| analyticdb_for_mysql | AnalyticDB MySQL | Yes | Yes | |
| analyticdb_for_postgresql | AnalyticDB PostgreSQL | Yes | Yes | |
| redshift | Amazon Redshift | Yes | No | |
| hbase | HBase | Yes | No | Uses hbaseConfig |
| lindorm | Lindorm | Yes | No | Uses seedserver/namespace |
| dlf | Data Lake Formation | No | Yes | Requires catalogId/catalogName/catalogType |

### Storage Services (4)

| Type | Name | UrlMode | InstanceMode | Notes |
|------|------|---------|-------------|-------|
| oss | OSS | Yes | No | RamRole authentication recommended |
| s3 | Amazon S3 | Yes | No | |
| ftp | FTP | Yes | No | protocol uses lowercase |
| ssh | SSH | Yes | No | Only supports connection string mode |

### NoSQL Databases (7)

| Type | Name | UrlMode | InstanceMode | Notes |
|------|------|---------|-------------|-------|
| tablestore | Tablestore | Yes | No | Requires regionId |
| memcache | Memcache | Yes | No | Uses proxy/port |
| milvus | Milvus | Yes | Yes | UrlMode uses endpoint |
| mongodb | MongoDB | Yes | Yes | Requires authDb and engineVersion |
| redis | Redis | Yes | Yes | Supports InstanceMode and UrlMode, SSL authentication optional |
| elasticsearch | Elasticsearch | Yes | Yes | Supports InstanceMode and UrlMode, anonymous authentication optional |
| graph_database | Graph Database | Yes | No | Connection string mode (host/port) |

### Message Services (3)

| Type | Name | UrlMode | InstanceMode | Notes |
|------|------|---------|-------------|-------|
| datahub | DataHub | Yes | No | Requires regionId |
| loghub | LogHub (SLS) | Yes | No | Requires regionId |
| kafka | Kafka | Yes | Yes | version uses "2.0" or "3.4" |

### SaaS Services (5)

| Type | Name | UrlMode | InstanceMode | Notes |
|------|------|---------|-------------|-------|
| restapi | REST API | Yes | No | |
| opensearch | OpenSearch | No | Yes | Only supports InstanceMode |
| salesforce | Salesforce | Yes | No | Uses OAuth, requires refreshToken |
| httpfile | HttpFile | Yes | No | HTTP file data source |
| bigquery | BigQuery | Yes | No | Requires bigQueryProjectId, bigQueryAuth |

---

## Connection Modes

| Mode | Applicable Scenarios | Common Required Fields |
|------|----------------------|------------------------|
| **UrlMode** | Self-hosted database, Known IP/port | address, database, username, password |
| **InstanceMode** | Alibaba Cloud managed instance (RDS, etc.) | instanceId, regionId, database, username, password |

> **Special types**: Oracle uses `jdbcUrl` (not address+database), MaxCompute uses `project`+`endpointMode`, OSS uses `bucket`+`endpoint`+`authType`. See examples for each type below.

---

## ConnectionProperties Examples

### MySQL (UrlMode)

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": 3306}],
  "database": "mydb",
  "username": "root",
  "password": "<PASSWORD>"
}
```

### MySQL (InstanceMode - Same-account)

```json
{
  "envType": "Prod",
  "instanceId": "rm-xxxxx",
  "regionId": "cn-shanghai",
  "database": "mydb",
  "username": "root",
  "password": "<PASSWORD>"
}
```

### MySQL (Cross-account)

```json
{
  "envType": "Prod",
  "instanceId": "rm-xxxxx",
  "regionId": "cn-shanghai",
  "database": "mydb",
  "username": "root",
  "password": "<PASSWORD>",
  "crossAccountOwnerId": "1234567890",
  "crossAccountRoleName": "CrossAccountRole"
}
```

### PostgreSQL (UrlMode)

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": 5432}],
  "database": "mydb",
  "username": "postgres",
  "password": "<PASSWORD>"
}
```

### Oracle (UrlMode)

> **Note**: Oracle uses `jdbcUrl` format, not the common `address` + `database` structure.

```json
{
  "envType": "Prod",
  "jdbcUrl": "jdbc:oracle:thin:@192.168.1.100:1521:ORCL",
  "username": "system",
  "password": "<PASSWORD>"
}
```

### Hologres (InstanceMode)

```json
{
  "envType": "Prod",
  "instanceId": "hgpostcn-cn-xxxxx",
  "regionId": "cn-shanghai",
  "database": "mydb",
  "authType": "PrimaryAccount"
}
```

### MaxCompute

> **Note**: The MaxCompute data source field name is `project` (not `maxComputeProject`), and does not support `Executor` identity. It is recommended to use `endpointMode: SelfAdaption` for adaptive mode.

```json
{
  "envType": "Prod",
  "project": "my_mc_project",
  "regionId": "cn-shanghai",
  "endpointMode": "SelfAdaption",
  "authType": "PrimaryAccount"
}
```

### ClickHouse (UrlMode)

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": 8123}],
  "database": "default",
  "username": "default",
  "password": "<PASSWORD>"
}
```

### OSS

> **Note**: OSS field names are `bucket` (not `bucketName`), `endpoint` (not `endPoint`), and requires `authType` and `regionId`. **RamRole authentication is recommended** (not Ak mode).

```json
{
  "envType": "Prod",
  "regionId": "cn-shanghai",
  "endpoint": "http://oss-cn-shanghai.aliyuncs.com",
  "bucket": "my-bucket",
  "authType": "RamRole",
  "authIdentity": "123456789"
}
```

### Hive (UrlMode)

> **Note**: Hive UrlMode requires `version`, `metaType`, `metastoreUris`, `loginMode` and other mandatory fields.

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": 10000}],
  "database": "default",
  "version": "2.3.9",
  "metaType": "HiveMetastore",
  "metastoreUris": "thrift://192.168.1.100:9083",
  "loginMode": "Anonymous",
  "securityProtocol": "authTypeNone"
}
```

### PolarDB MySQL (UrlMode)

> **Note**: PolarDB requires the `dbType` parameter to specify the database type.

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": 3306}],
  "database": "mydb",
  "username": "root",
  "password": "<PASSWORD>",
  "dbType": "mysql"
}
```

### DM (Dameng) (UrlMode)

> **Note**: DM does not require the `database` field.

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": 5236}],
  "username": "mockuser",
  "password": "<PASSWORD>"
}
```

### DB2 (UrlMode)

> **Note**: DB2 requires the `jdbcDriver` parameter. Possible values: `db2_1`, `db2_2`, `as400_1`.

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": 50000}],
  "database": "mydb",
  "username": "db2admin",
  "password": "<PASSWORD>",
  "jdbcDriver": "db2_1"
}
```

### StarRocks/Doris/SelectDB (UrlMode)

> **Note**: These types require the `loadAddress` parameter for data import.

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": 9030}],
  "loadAddress": [{"host": "192.168.1.100", "port": 8030}],
  "database": "mydb",
  "username": "root",
  "password": "<PASSWORD>"
}
```

### HBase (UrlMode)

> **Note**: HBase uses the `hbaseConfig` object instead of `address`.

```json
{
  "envType": "Prod",
  "hbaseConfig": {
    "hbase.zookeeper.quorum": "192.168.1.100:2181",
    "hbaseVersion": "0.9.4"
  },
  "securityProtocol": "authTypeNone"
}
```

### Lindorm (UrlMode)

> **Note**: Lindorm uses `seedserver`/`namespace` instead of `address`/`database`.

```json
{
  "envType": "Prod",
  "seedserver": "ld-xxx.lindorm.rds.aliyuncs.com:30020",
  "namespace": "default",
  "username": "root",
  "password": "<PASSWORD>"
}
```

### Memcache (UrlMode)

> **Note**: Memcache uses `proxy`/`port` instead of `address`.

```json
{
  "envType": "Prod",
  "proxy": "192.168.1.100",
  "port": "11211",
  "username": "mockuser",
  "password": "<PASSWORD>"
}
```

### Milvus (UrlMode)

> **Note**: Milvus UrlMode uses `endpoint` instead of `host`/`port`.

```json
{
  "envType": "Prod",
  "endpoint": "http://192.168.1.100:19530",
  "database": "default",
  "username": "root",
  "password": "<PASSWORD>",
  "authType": "USERNAME_PASSWORD"
}
```

### Tablestore (UrlMode)

> **Note**: Tablestore requires the `regionId` parameter.

```json
{
  "envType": "Prod",
  "regionId": "cn-shanghai",
  "endpoint": "https://myinstance.cn-shanghai.ots.aliyuncs.com",
  "instanceName": "myinstance",
  "accessId": "<AK_ID>",
  "accessKey": "<AK_SECRET>"
}
```

### DataHub (UrlMode)

> **Note**: DataHub requires the `regionId` parameter.

```json
{
  "envType": "Prod",
  "regionId": "cn-shanghai",
  "endpoint": "http://dh-cn-shanghai.aliyuncs.com",
  "project": "my_project",
  "accessId": "<AK_ID>",
  "accessKey": "<AK_SECRET>"
}
```

### LogHub (UrlMode)

> **Note**: LogHub requires the `regionId` parameter.

```json
{
  "envType": "Prod",
  "regionId": "cn-shanghai",
  "endpoint": "cn-shanghai.log.aliyuncs.com",
  "project": "my_project",
  "accessId": "<AK_ID>",
  "accessKey": "<AK_SECRET>"
}
```

### S3 (UrlMode)

> **Note**: S3 uses `accessId`/`accessKey` (not accessKey/secretKey).

```json
{
  "envType": "Prod",
  "regionId": "us-east-1",
  "endpoint": "http://s3.amazonaws.com",
  "bucket": "my-bucket",
  "accessId": "<AK_ID>",
  "accessKey": "<AK_SECRET>"
}
```

### FTP (UrlMode)

> **Note**: The `protocol` parameter uses lowercase values: `ftp`, `sftp`, `ftps`.

```json
{
  "envType": "Prod",
  "protocol": "ftp",
  "host": "192.168.1.100",
  "port": "21",
  "username": "ftpuser",
  "password": "<PASSWORD>"
}
```

### OpenSearch (InstanceMode)

> **Note**: OpenSearch only supports InstanceMode.

```json
{
  "envType": "Prod",
  "regionId": "cn-shanghai",
  "instanceType": "vectorSearchVersion",
  "instanceId": "ha-xxxxx",
  "username": "admin",
  "password": "<PASSWORD>"
}
```

### AnalyticDB MySQL (UrlMode)

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": 3306}],
  "database": "mydb",
  "username": "root",
  "password": "<PASSWORD>"
}
```

### AnalyticDB PostgreSQL (UrlMode)

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": 5432}],
  "database": "mydb",
  "username": "postgres",
  "password": "<PASSWORD>"
}
```

### Snowflake (UrlMode)

> **Note**: Snowflake requires the `accountUrl` parameter with the full account URL.

```json
{
  "envType": "Prod",
  "accountUrl": "xy12345.snowflakecomputing.com",
  "database": "mydb",
  "securityProtocol": "authTypeClientPassword",
  "username": "myuser",
  "password": "<PASSWORD>",
  "warehouseName": "my_warehouse"
}
```

### MongoDB (UrlMode)

> **Note**: MongoDB requires `authDb` (authorization database) and `engineVersion` parameters.

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": "27017"}],
  "database": "mydb",
  "username": "root",
  "password": "<PASSWORD>",
  "authDb": "admin",
  "engineVersion": "5.x"
}
```

### Kafka (UrlMode)

> **Note**: Kafka UrlMode uses the `address` parameter, and `version` only supports "2.0" or "3.4".

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": "9092"}],
  "version": "2.0",
  "securityProtocol": "authTypeNone"
}
```

### DRDS (UrlMode)

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": "3306"}],
  "database": "mydb",
  "username": "root",
  "password": "<PASSWORD>"
}
```

### DLF (InstanceMode)

> **Note**: DLF only supports InstanceMode, requires catalog-related parameters.

```json
{
  "envType": "Prod",
  "authType": "PrimaryAccount",
  "database": "db1",
  "catalogId": "clg-paimon-xxx",
  "catalogName": "xxx",
  "catalogType": "Paimon",
  "endpoint": "http://cn-hangzhou-vpc.dlf.aliyuncs.com"
}
```

### Graph Database (UrlMode)

> **Note**: Graph Database uses connection string mode with host/port.

```json
{
  "host": "127.0.0.1",
  "port": "5432",
  "username": "xxxxx",
  "password": "xxxxx",
  "envType": "Dev"
}
```

### BigQuery (UrlMode)

> **Note**: BigQuery requires `bigQueryProjectId` (project ID) and `bigQueryAuth` (credential file ID).

```json
{
  "bigQueryProjectId": "bigquery_id",
  "bigQueryAuth": "123",
  "envType": "Prod"
}
```

### PolarDB-O (InstanceMode / UrlMode)

> **Note**: PolarDB-O supports both InstanceMode and UrlMode. InstanceMode requires `instanceId` and `regionId`.

```json
{
  "envType": "Prod",
  "regionId": "cn-beijing",
  "instanceId": "pc-xxxxx",
  "database": "my_database",
  "username": "my_username",
  "password": "<PASSWORD>"
}
```

### PolarDB-X 2.0 (InstanceMode / UrlMode)

> **Note**: PolarDB-X 2.0 supports both InstanceMode and UrlMode. InstanceMode requires `instanceId` and `regionId`.

```json
{
  "envType": "Prod",
  "regionId": "cn-beijing",
  "instanceId": "pxc-xxxxx",
  "database": "my_database",
  "username": "my_username",
  "password": "<PASSWORD>"
}
```

### OceanBase (apsaradb_for_oceanbase) (InstanceMode / UrlMode)

> **Note**: OceanBase supports both modes. InstanceMode requires `instanceId`, `tenant`, `regionId`. UrlMode requires `dbMode` (mysql/oracle).

```json
{
  "envType": "Prod",
  "instanceId": "ob5nj51ns6qjr4",
  "tenant": "t5nnecr8dppi8",
  "regionId": "cn-shanghai",
  "database": "my_database",
  "username": "aliyun",
  "password": "<PASSWORD>"
}
```

---

## Environment Types

| Value | Description |
|-------|-------------|
| Dev | Development environment |
| Prod | Production environment |

---

> For full configuration of each data source type, please refer to `<type>.md` (e.g., `mysql.md`, `hologres.md`)
