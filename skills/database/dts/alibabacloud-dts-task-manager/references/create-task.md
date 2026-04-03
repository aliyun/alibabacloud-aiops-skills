# Create Data Migration/Synchronization Task (Interactive)

## Supported Database Engines

### Supported as Source

| Engine Name | API EngineName | Description |
|------------|---------------|-------------|
| MySQL | MySQL | RDS MySQL, self-managed MySQL |
| PolarDB for MySQL | polardb | PolarDB MySQL engine |
| PostgreSQL | PostgreSQL | RDS PostgreSQL, self-managed PostgreSQL |
| PolarDB for PostgreSQL | polardb_pg | PolarDB PostgreSQL engine |
| SQL Server | SQLServer | RDS SQL Server, self-managed SQL Server |
| Oracle | Oracle | Self-managed Oracle |
| PolarDB (Oracle compatible) | polardb_o | PolarDB Oracle-compatible engine |
| PolarDB-X 2.0 | polardb-x | PolarDB-X 2.0 distributed database |
| PolarDB-X 1.0 | DRDS | PolarDB-X 1.0 / DRDS |
| MariaDB | MariaDB | RDS MariaDB, self-managed MariaDB |
| TiDB | TiDB | Self-managed TiDB |
| DB2 LUW | DB2 | IBM DB2 for LUW |
| DMS LogicDB | dmslogicdb | DMS logical database |
| DB2 iSeries (AS/400) | as400 | IBM AS/400 |
| AnalyticDB MySQL 3.0 | ADB30 | AnalyticDB MySQL 3.0 |
| AnalyticDB PostgreSQL | GREENPLUM | AnalyticDB PostgreSQL / Greenplum |
| Tair/Redis | Redis | ApsaraDB for Redis/Tair, self-managed Redis |
| MongoDB | MongoDB | ApsaraDB for MongoDB, self-managed MongoDB |
| Data Delivery | DataDelivery | DTS data delivery |

### Supported as Destination

| Engine Name | API EngineName | Description |
|------------|---------------|-------------|
| MySQL | MySQL | RDS MySQL, self-managed MySQL |
| PolarDB for MySQL | polardb | PolarDB MySQL engine |
| PostgreSQL | PostgreSQL | RDS PostgreSQL, self-managed PostgreSQL |
| PolarDB for PostgreSQL | polardb_pg | PolarDB PostgreSQL engine |
| Oracle | Oracle | Self-managed Oracle |
| PolarDB-X 2.0 | polardb-x | PolarDB-X 2.0 distributed database |
| PolarDB-X 1.0 | DRDS | PolarDB-X 1.0 / DRDS |
| AnalyticDB MySQL 3.0 | ADB30 | AnalyticDB MySQL 3.0 |
| AnalyticDB PostgreSQL | GREENPLUM | AnalyticDB PostgreSQL / Greenplum |
| ClickHouse | ClickHouse | Open-source columnar database |
| SelectDB | selectdb | SelectDB |
| Doris | Doris | Apache Doris |
| DuckDB | DuckDB | Embedded analytical database |
| Tair/Redis | Redis | ApsaraDB for Redis/Tair, self-managed Redis |
| Lindorm | lindorm | Lindorm multi-model database |
| Tablestore | Tablestore | Table Store |
| Kafka | Kafka | Message Queue for Apache Kafka, self-managed Kafka |
| RocketMQ | RocketMQ | Message Queue for Apache RocketMQ |
| DataHub | DataHub | Streaming data service |

**Note**: The API EngineName column values are used for the `--SourceEndpointEngineName` and `--DestinationEndpointEngineName` parameters in CreateDtsInstance.

### Engine Selection Pagination

Source engine priority display: MySQL, PostgreSQL, MongoDB, SQL Server
Subsequent pages: Oracle, Tair/Redis, PolarDB for MySQL, MariaDB -> TiDB, PolarDB-X 2.0, ADB MySQL 3.0, PolarDB for PostgreSQL -> DB2 LUW, PolarDB-X 1.0, PolarDB (Oracle compatible), ADB PostgreSQL -> AS/400, DMS LogicDB, Data Delivery

Destination engine priority display: MySQL, PostgreSQL, Kafka, ClickHouse
Subsequent pages: Tair/Redis, ADB MySQL 3.0, Doris, SelectDB -> PolarDB for MySQL, DuckDB, Lindorm, Tablestore -> Oracle, RocketMQ, DataHub, ADB PostgreSQL -> PolarDB for PostgreSQL, PolarDB-X 2.0, PolarDB-X 1.0

## Creation Workflow

### Step 1: Task Type

Ask the task type (if not specified in parameters): Data Migration (MIGRATION) or Data Synchronization (SYNC)

### Step 2: Source Database Information

**2a. Source engine type** - Display with pagination (see "Engine Selection Pagination" above), priority: MySQL, PostgreSQL, MongoDB, SQL Server

**2b. Source access method**:
- Alibaba Cloud RDS / managed database instance (InstanceType=RDS)
- Public IP self-managed (InstanceType=other)
- Alibaba Cloud ECS self-managed (InstanceType=ECS)
- Express Connect / VPN Gateway / Smart Access Gateway (InstanceType=dg)

Select Other to show: Cloud Enterprise Network CEN (InstanceType=CEN)

**Access method to API parameter mapping**:

| Access Method | InstanceType Value | Required Connection Parameters |
|--------------|-------------------|-------------------------------|
| Managed instance (RDS) | RDS | InstanceID |
| PolarDB managed instance | POLARDB | InstanceID |
| Managed Kafka instance | KAFKA | InstanceID |
| Public IP self-managed | other | IP + Port |
| ECS self-managed | ECS | IP + Port |
| Express Connect / VPN Gateway / SAG | dg | IP + Port |
| Cloud Enterprise Network CEN | CEN | IP + Port |

**Important**: PolarDB and Kafka use their own dedicated InstanceType values (`POLARDB`, `KAFKA`), not `RDS`. Only RDS MySQL/PostgreSQL/SQL Server/MariaDB/MongoDB/Redis use `RDS` as InstanceType.

**2c. Source connection information:**

**If "Alibaba Cloud RDS / managed database instance" is selected**:

Use aliyun CLI to query instance list for user selection:

For MySQL/PostgreSQL/SQL Server/MariaDB RDS:
```bash
aliyun rds DescribeDBInstances --RegionId <region> --Engine <MySQL|PostgreSQL|SQLServer|MariaDB> --PageSize 50 --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills 2>&1
```

For MongoDB:
```bash
aliyun dds DescribeDBInstances --RegionId <region> --PageSize 50 --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills 2>&1
```

For Redis/Tair:
```bash
aliyun r-kvstore DescribeInstances --RegionId <region> --PageSize 50 --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills 2>&1
```

For PolarDB (InstanceType=POLARDB):
```bash
aliyun polardb DescribeDBClusters --RegionId <region> --PageSize 50 --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills 2>&1
```
Extract `DBClusterId` and `DBClusterDescription` from `Items.DBCluster[]` for user selection.

For Kafka (InstanceType=KAFKA):
```bash
aliyun alikafka GetInstanceList --RegionId <region> --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills 2>&1
```
Extract `InstanceId` and `Name` from `InstanceList.InstanceVO[]` for user selection.

For other managed instances, extract instance IDs and descriptions (instance name, IP, status) from the returned JSON for user selection.

**If "Public IP self-managed", "ECS self-managed", "Express Connect/VPN/SAG", or "CEN" is selected**:

Collect connection information (consolidate into as few rounds as possible):
- IP address and port (format: 1.2.3.4:3306)
- Database username
- Database password

**RDS instances also require username and password.**

**2d. SSL encrypted connection (optional):**

After collecting connection information, ask whether SSL encrypted connection is needed: No SSL (default) or SSL encryption required.

If SSL is needed, collect certificate information:
- CA certificate file path
- Client certificate file path (optional, required for mutual SSL/mTLS)
- Client key file path (optional, required for mutual SSL/mTLS)

Read certificate file contents and pass via the Reserved parameter in ConfigureDtsJob:

Source SSL: `{"srcSslEnabled":"true","srcSslCaCert":"PEM_CONTENT","srcSslClientCert":"PEM_CONTENT","srcSslClientKey":"PEM_CONTENT"}`
Destination SSL: `{"destSslEnabled":"true","destSslCaCert":"PEM_CONTENT","destSslClientCert":"PEM_CONTENT","destSslClientKey":"PEM_CONTENT"}`

Note: Escape newlines in certificate content with `\n`. **Never display certificates and keys in output.**

### Step 3: Destination Database Information

Similar collection workflow as the source database:
- Destination engine type (select from supported destination engine list)
- Access method (managed instance/public IP/ECS/Express Connect VPN/CEN)
- If managed instance, list instance list for selection
- Connection information (username, password, etc.) — **Kafka managed instances do NOT require username/password**
- SSL encrypted connection (optional)

**Kafka destination specifics**:
When Kafka is selected as destination, collect additional Kafka-specific settings:
- Target topic name (or use auto-generated from db/table name)
- Message format: canal_json (recommended), avro, or default
- Compression type: lz4 (recommended), snappy, gzip, or none
- Partition strategy: none / primary_key / table_pk
- Producer acks: 1 (recommended), 0, or all
- Topic mode: single topic (0) or per-table topic (2)

### Step 4: Migration Objects

Ask: Full database migration (migrate all databases and tables) or Specific databases/tables (user inputs database and table names)

If "Specific databases/tables" is selected, collect:
- Source database name(s) to migrate/sync
- Table name(s) to migrate/sync (multiple tables separated by commas, * for all tables)

### Step 4b: Destination Database and Table Name Mapping

**Database name mapping**: Ask for destination database name - Same as source (recommended) or Map to a different database name

**Table name mapping**: Ask whether table name mapping is needed - Not needed (recommended) or Map table names
If table name mapping is needed, collect mapping relationships (format: source_table:dest_table, multiple separated by commas)

**DbList JSON construction rules**:

Full database migration with same name: `{"mydb":{"name":"mydb","all":true}}`
Database name mapping: `{"source_db":{"name":"target_db","all":true}}`
Specific tables without table name mapping: `{"mydb":{"name":"target_db","Table":{"t1":{"name":"t1","all":true}}}}`
Specific tables with table name mapping: `{"src_db":{"name":"dst_db","Table":{"src_t1":{"name":"dst_t1","all":true},"src_t2":{"name":"dst_t2","all":true}}}}`

### Step 5: Migration Types

Multi-select:
- Schema migration (StructureInitialization)
- Full data migration (DataInitialization)
- Incremental migration (DataSynchronization)

All selected by default.

**Engine-specific constraints**:
- **Kafka as destination**: StructureInitialization must be `false` (Kafka has no schema concept). Default to DataInitialization + DataSynchronization only.

### Step 6: Instance Class

Select: micro (micro spec, for testing), small, medium, large

### Step 7: Summary and Create

Display all configuration information to the user (**password fields must show as `******`**), then proceed with creation.

### Step 8: Execute Creation

**8a. Create DTS instance:**
```bash
aliyun dts CreateDtsInstance \
  --RegionId <region> \
  --Type <MIGRATION|SYNC> \
  --SourceEndpointEngineName <MySQL|PostgreSQL|MongoDB|...> \
  --DestinationEndpointEngineName <MySQL|PostgreSQL|MongoDB|...> \
  --SourceRegion <region> \
  --DestinationRegion <region> \
  --InstanceClass <micro|small|medium|large> \
  --PayType PostPaid \
  --ClientToken <uuid> \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

Extract `InstanceId` (i.e., DtsInstanceId) and `JobId` from the response.

**Idempotency**: `--ClientToken` uses a UUID (e.g., generated by `uuidgen`) to ensure timeout retries do not create duplicate instances and incur extra charges. The same ClientToken returns the same result within 24 hours.

**8b. Configure task:**
```bash
aliyun dts ConfigureDtsJob \
  --RegionId <region> \
  --DtsInstanceId <instance-id> \
  --DtsJobId <job-id> \
  --DtsJobName "<auto-generated: sync/migration-source_engine-dest_engine-date>" \
  --JobType <MIGRATION|SYNC> \
  --SourceEndpointInstanceType <other|RDS|ECS|dg|CEN> \
  --SourceEndpointEngineName <engine-name> \
  --SourceEndpointRegion <region> \
  --SourceEndpointInstanceID "<rds-instance-id>" \
  --SourceEndpointUserName "<username>" \
  --SourceEndpointPassword '<password>' \
  --DestinationEndpointInstanceType <other|RDS|ECS|dg|CEN> \
  --DestinationEndpointEngineName <engine-name> \
  --DestinationEndpointRegion <region> \
  --DestinationEndpointIP "<ip>" \
  --DestinationEndpointPort "<port>" \
  --DestinationEndpointUserName "<username>" \
  --DestinationEndpointPassword '<password>' \
  --StructureInitialization <true|false> \
  --DataInitialization <true|false> \
  --DataSynchronization <true|false> \
  --DbList '<json>' \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

Notes:
- RDS instances (InstanceType=RDS) use `--SourceEndpointInstanceID`, no IP/Port needed
- PolarDB instances use InstanceType=`POLARDB` with `--SourceEndpointInstanceID`
- Kafka managed instances use InstanceType=`KAFKA` with `--DestinationEndpointInstanceID`, no username/password needed
- Self-managed (other), ECS, Express Connect/VPN (dg), CEN use `--SourceEndpointIP` + `--SourceEndpointPort`
- MongoDB requires `--SourceEndpointDatabaseName`
- Wrap passwords in single quotes, **never display in output**
- If SSL is enabled, add SSL configuration JSON in the `--Reserved` parameter
- **Never display certificate content and keys in output**

### Kafka Destination: Reserve Parameter

When the destination is Kafka, the `--Reserve` parameter is **required** and carries Kafka-specific configuration as a JSON string:

```json
{
  "targetTableMode": "0",
  "kafkaRecordFormat": "canal_json",
  "destKafka.compression.type": "lz4",
  "destKafkaPartitionKey": "none",
  "destKafka.acks": "1",
  "dbListCaseChangeMode": "default",
  "maxRetryTime": 43200,
  "retry.blind.seconds": 600,
  "destTopic": "<topic-name>",
  "destSSL": "0",
  "destSchemaRegistry": "no",
  "a2aFlag": "2.0",
  "autoStartModulesAfterConfig": "none"
}
```

**Key fields**:

| Field | Values | Description |
|-------|--------|-------------|
| `targetTableMode` | `"0"` = single topic, `"2"` = per-table topic | How data is written to Kafka topics |
| `kafkaRecordFormat` | `"canal_json"` / `"avro"` / `"default"` | Message serialization format |
| `destKafka.compression.type` | `"lz4"` / `"snappy"` / `"gzip"` / `"none"` | Kafka producer compression |
| `destKafkaPartitionKey` | `"none"` / `"primary_key"` / `"table_pk"` | Partition routing strategy |
| `destKafka.acks` | `"0"` / `"1"` / `"all"` | Kafka producer acknowledgment level |
| `destTopic` | topic name string | Target Kafka topic (for single-topic mode) |
| `destSSL` | `"0"` / `"1"` | Whether to enable SSL for Kafka connection |
| `destSchemaRegistry` | `"no"` / `"yes"` | Whether to use schema registry (for Avro) |
| `maxRetryTime` | integer (seconds) | Max retry duration on failure (default: 43200 = 12h) |
| `autoStartModulesAfterConfig` | `"none"` / `"all"` | Whether to auto-start after configuration |

### Complete Example: PolarDB to Kafka Sync

**8a. Create DTS instance:**
```bash
aliyun dts CreateDtsInstance \
  --RegionId cn-hangzhou \
  --Type SYNC \
  --SourceEndpointEngineName POLARDB \
  --DestinationEndpointEngineName KAFKA \
  --SourceRegion cn-hangzhou \
  --DestinationRegion cn-hangzhou \
  --InstanceClass small \
  --PayType PostPaid \
  --ClientToken "$(uuidgen)" \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**8b. Configure task:**
```bash
aliyun dts ConfigureDtsJob \
  --RegionId cn-hangzhou \
  --DtsInstanceId <instance-id> \
  --DtsJobId <job-id> \
  --DtsJobName "sync-polardb-kafka-20260402" \
  --JobType SYNC \
  --SourceEndpointInstanceType POLARDB \
  --SourceEndpointEngineName POLARDB \
  --SourceEndpointRegion cn-hangzhou \
  --SourceEndpointInstanceID "<polardb-cluster-id>" \
  --SourceEndpointUserName "dts" \
  --SourceEndpointPassword '<password>' \
  --DestinationEndpointInstanceType KAFKA \
  --DestinationEndpointEngineName KAFKA \
  --DestinationEndpointRegion cn-hangzhou \
  --DestinationEndpointInstanceID "<kafka-instance-id>" \
  --StructureInitialization false \
  --DataInitialization true \
  --DataSynchronization true \
  --DbList '{"dts":{"name":"dts_dts1","all":true}}' \
  --Reserve '{"targetTableMode":"0","kafkaRecordFormat":"canal_json","destKafka.compression.type":"lz4","destKafkaPartitionKey":"none","destKafka.acks":"1","dbListCaseChangeMode":"default","maxRetryTime":43200,"retry.blind.seconds":600,"destTopic":"dts_dts1","destSSL":"0","destSchemaRegistry":"no","a2aFlag":"2.0","autoStartModulesAfterConfig":"none"}' \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Key points of this example**:
- Source InstanceType is `POLARDB` (not `RDS`), EngineName is `POLARDB` (uppercase)
- Destination InstanceType is `KAFKA`, EngineName is `KAFKA` (uppercase)
- Kafka destination uses InstanceID only — no IP/Port, no username/password
- `StructureInitialization` must be `false` for Kafka
- `--Reserve` carries all Kafka-specific settings (topic, format, compression, acks, etc.)
- DbList maps source database `dts` to destination name `dts_dts1`, which matches `destTopic`
- Password is wrapped in single quotes, **never displayed in output**

**8c. Start task:**
```bash
aliyun dts StartDtsJob \
  --RegionId <region> \
  --DtsInstanceId <instance-id> \
  --DtsJobId <job-id> \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**8d. Output results:** Display DTS instance ID, task ID, and the command to check status.

If creation or configuration fails, display the error message and release the created instance (to avoid charges).
