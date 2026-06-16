# Alibaba Cloud Realtime Compute for Apache Flink — Connector Reference

> Flink SQL implements read/write by defining tables that map to upstream and downstream storage systems.

## Table Type Definitions

| Type | Description | Examples |
|---|---|---|
| **Source Table** | Data stream entry point; continuously reads data from external systems | Kafka, MySQL CDC |
| **Lookup Table (Dimension Table)** | Reference data table; enriches stream data dimensions via JOIN | MySQL, Redis, HBase |
| **Sink Table (Result Table)** | Data exit point; writes computation results to target systems | Hologres, Paimon, MySQL |

## Supported Connectors (Full List)

### Relational Databases

| Connector | Source | Lookup | Sink | CDC Source | Mode | Supports Update/Delete |
|---|---|---|---|---|---|---|
| **MySQL** (incl. RDS/PolarDB) | Y | Y | Y | Y | Stream | Yes |
| **Postgres CDC** (Public Preview) | Y | — | — | Y | Stream | — |
| **OceanBase** (Public Preview) | Y | Y | Y | — | Stream+Batch | Yes |
| **SelectDB** | — | — | Y | — | Stream+Batch | Yes |

### NoSQL Databases

| Connector | Source | Lookup | Sink | CDC Source | Mode | Supports Update/Delete |
|---|---|---|---|---|---|---|
| **MongoDB** | Y | Y | Y | Y | Stream | Yes |
| **HBase** | — | Y | Y | — | Stream | Yes |
| **Tablestore (OTS)** | Y | Y | Y | — | Stream | — |
| **Lindorm** | — | Y | Y | — | Stream | Yes |
| **Milvus** (Public Preview) | — | — | Y | — | Stream | Yes |

### Message Queues

| Connector | Source | Lookup | Sink | CDC Source | CDC Target | Mode |
|---|---|---|---|---|---|---|
| **Message Queue for Apache Kafka** | Y | — | Y | Y | Y | Stream |
| **Upsert Kafka** | Y | — | Y | — | Y | Stream |
| **RocketMQ** | Y | — | Y | — | — | Stream |
| **DataHub** | Y | — | Y | — | — | Stream+Batch |

### Data Warehouses

| Connector | Source | Lookup | Sink | CDC Source | Mode | Supports Update/Delete |
|---|---|---|---|---|---|---|
| **StarRocks** | Y | Y | Y | — | Stream+Batch | Yes |
| **Hologres** | Y | Y | Y | — | Stream+Batch | Yes |
| **AnalyticDB for MySQL 3.0** | Y | Y | Y | — | Stream+Batch | Yes |
| **AnalyticDB for PostgreSQL** | — | Y | Y | — | Stream+Batch | Yes |
| **ClickHouse** | — | — | Y | — | Stream+Batch | Yes |
| **Iceberg** | Y | — | Y | — | Stream+Batch | Yes |

### Data Lake & Offline Computing

| Connector | Source | Lookup | Sink | Mode | Supports Update/Delete |
|---|---|---|---|---|---|
| **Streaming Data Lakehouse Paimon** | Y | Y | Y | Stream+Batch | Yes |
| **MaxCompute** | Y | Y | Y | Stream+Batch | No (INSERT only) |
| **Hudi** (Retiring) | Y | — | Y | Stream+Batch | Yes |

### Logging / Object Storage

| Connector | Source | Lookup | Sink | CDC Source | Mode |
|---|---|---|---|---|---|
| **Simple Log Service (SLS)** | Y | — | Y | Y | Stream |
| **Object Storage Service (OSS)** | Y | — | Y | — | Stream+Batch |
| **Elasticsearch** | Y | Y | Y | — | Stream+Batch |
| **JDBC** (Generic) | Y | Y | Y | — | Stream+Batch |
| **Community CDC** | Y | — | — | — | Stream |

### Key-Value / Time-Series Databases

| Connector | Lookup | Sink | Mode |
|---|---|---|---|
| **Tair (Redis Open-Source Compatible)** | Y | Y | Stream |
| **Tair (Tair Enterprise)** | — | Y | Stream |
| **InfluxDB** (Retiring) | — | Y | Stream |

### Debugging / Utility Connectors

| Connector | Source | Lookup | Sink | Mode |
|---|---|---|---|---|
| **Faker** (Mock Data) | Y | Y | — | Stream+Batch |
| **Datagen** | Y | — | — | Stream+Batch |
| **Blackhole** | — | — | Y | Stream+Batch |
| **Print** (Console Print) | — | — | Y | Stream+Batch |

## Common Connector Examples

### MySQL CDC (Source Table)

```sql
CREATE TEMPORARY TABLE mysql_orders (
    order_id   BIGINT,
    user_id    BIGINT,
    amount     DECIMAL(10,2),
    order_time TIMESTAMP(3),
    PRIMARY KEY (order_id) NOT ENFORCED
) WITH (
    'connector'  = 'mysql-cdc',
    'hostname'   = 'mysql-server',
    'port'       = '3306',
    'username'   = '${db_user}',
    'password'   = '${db_password}',
    'database-name' = 'order_db',
    'table-name'    = 'orders',
    'scan.startup.mode' = 'initial'
);
```

### Kafka (Source Table + Sink Table)

```sql
-- Source table
CREATE TEMPORARY TABLE kafka_source (
    message STRING
) WITH (
    'connector' = 'kafka',
    'topic'     = 'input_topic',
    'properties.bootstrap.servers' = 'broker1:9092',
    'properties.group.id' = 'flink-consumer',
    'format'    = 'json',
    'scan.startup.mode' = 'latest-offset'
);

-- Sink table
CREATE TEMPORARY TABLE kafka_sink (
    result STRING
) WITH (
    'connector'  = 'kafka',
    'topic'      = 'output_topic',
    'properties.bootstrap.servers' = 'broker1:9092',
    'format'     = 'json'
);
```

### Hologres (Sink Table)

```sql
CREATE TEMPORARY TABLE hologres_sink (
    window_start TIMESTAMP(3),
    uv           BIGINT,
    pv           BIGINT,
    PRIMARY KEY (window_start) NOT ENFORCED
) WITH (
    'connector'  = 'hologres',
    'dbname'     = 'your_db',
    'tablename'  = 'realtime_metrics',
    'username'   = '${ak}',
    'password'   = '${sk}',
    'mutateType' = 'insertOrUpdate'   -- upsert mode
);
```

### Paimon (Sink Table)

```sql
CREATE TEMPORARY TABLE paimon_sink (
    id        BIGINT,
    name      STRING,
    price     DECIMAL(10,2),
    PRIMARY KEY (id) NOT ENFORCED
) WITH (
    'connector'   = 'paimon',
    'warehouse'   = 'oss://your-bucket/warehouse',
    'database-name' = 'default',
    'table-name'  = 'orders'
);
```

### HBase/Kafka Lookup Table

```sql
-- HBase lookup table
CREATE TEMPORARY TABLE hbase_dim (
    rowkey STRING,
    info   ROW<name STRING, age INT>,
    PRIMARY KEY (rowkey) NOT ENFORCED
) WITH (
    'connector'        = 'hbase',
    'zookeeper.quorum' = 'hbase-zk:2181',
    'table-name'       = 'user_info',
    'lookup.cache'     = 'PARTIAL',
    'lookup.cache.ttl' = '1h'
);
```

## Custom Connectors

If you need to use a connector not built into the platform, you can add one via the following steps:
1. Package the custom Connector as a JAR
2. Console → **Resource Management** → **Upload Additional Dependency Files**
3. Declare the custom Connector in the SQL `WITH` clause

## Common Connector Issues

| Issue | Troubleshooting Direction |
|---|---|
| Kafka consumption latency / backpressure | Check Kafka partition count, consumer parallelism |
| MySQL CDC full-snapshot phase is slow | Adjust `scan.fetch.size`, `debezium.snapshot.fetch.size` |
| Hologres Sink writes are slow | Check write mode, batch size, primary key constraints |
| JDBC lookup table join timeout | Enable `lookup.cache` to reduce direct connection frequency |
| Connector version incompatibility | Cross-reference the engine version and connector support matrix |

## Official Documentation Links

- [Supported Connectors](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/supported-connectors)
- [Connector Documentation Home](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/connectors/)
- [Managing Custom Connectors](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/manage-custom-connectors)
- [Data Formats](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/data-format/)
