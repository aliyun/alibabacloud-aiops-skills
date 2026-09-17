# Flink SQL Connectors

> Flink SQL reads and writes data by defining Tables that map to upstream and downstream storage systems.

## Table Types

| Type | Description | Examples |
|------|-------------|----------|
| **Source Table** | Entry point to a data flow that continuously reads from an external system | Kafka, MySQL CDC |
| **Lookup Table (Dimension Table)** | A reference table that enriches streaming data through a Join | MySQL, Redis, HBase |
| **Sink Table (Result Table)** | Output of a data flow that writes computed results to a target system | Hologres, Paimon, MySQL |

## Supported Connectors (Complete List)

### Relational Databases

| Connector | Source | Lookup | Sink | CDC Source | Mode | Update/Delete support |
|-----------|--------|--------|------|------------|------|-----------------------|
| **MySQL** (including RDS/PolarDB) | Y | Y | Y | Y | Stream | Yes |
| **Postgres CDC** (public preview) | Y | — | — | Y | Stream | — |
| **OceanBase** (public preview) | Y | Y | Y | — | Stream+Batch | Yes |
| **SelectDB** | — | — | Y | — | Stream+Batch | Yes |

### NoSQL Databases

| Connector | Source | Lookup | Sink | CDC Source | Mode | Update/Delete support |
|-----------|--------|--------|------|------------|------|-----------------------|
| **MongoDB** | Y | Y | Y | Y | Stream | Yes |
| **HBase** | — | Y | Y | — | Stream | Yes |
| **Tablestore (OTS)** | Y | Y | Y | — | Stream | — |
| **Lindorm** | — | Y | Y | — | Stream | Yes |
| **Milvus** (public preview) | — | — | Y | — | Stream | Yes |

### Message Queues

| Connector | Source | Lookup | Sink | CDC Source | CDC Target | Mode |
|-----------|--------|--------|------|------------|------------|------|
| **Message Queue for Apache Kafka** | Y | — | Y | Y | Y | Stream |
| **Upsert Kafka** | Y | — | Y | — | Y | Stream |
| **RocketMQ** | Y | — | Y | — | — | Stream |
| **DataHub** | Y | — | Y | — | — | Stream+Batch |

### Data Warehouses

| Connector | Source | Lookup | Sink | CDC Source | Mode | Update/Delete support |
|-----------|--------|--------|------|------------|------|-----------------------|
| **StarRocks** | Y | Y | Y | — | Stream+Batch | Yes |
| **Hologres** | Y | Y | Y | — | Stream+Batch | Yes |
| **AnalyticDB for MySQL 3.0** | Y | Y | Y | — | Stream+Batch | Yes |
| **AnalyticDB for PostgreSQL** | — | Y | Y | — | Stream+Batch | Yes |
| **ClickHouse** | — | — | Y | — | Stream+Batch | Yes |
| **Iceberg** | Y | — | Y | — | Stream+Batch | Yes |

### Data Lakes and Offline Computing

| Connector | Source | Lookup | Sink | Mode | Update/Delete support |
|-----------|--------|--------|------|------|-----------------------|
| **Streaming Data Lakehouse Paimon** | Y | Y | Y | Stream+Batch | Yes |
| **MaxCompute** | Y | Y | Y | Stream+Batch | No (INSERT only) |
| **Hudi** (being discontinued) | Y | — | Y | Stream+Batch | Yes |

### Logging and Object Storage

| Connector | Source | Lookup | Sink | CDC Source | Mode |
|-----------|--------|--------|------|------------|------|
| **Simple Log Service (SLS)** | Y | — | Y | Y | Stream |
| **Object Storage Service (OSS)** | Y | — | Y | — | Stream+Batch |
| **Elasticsearch** | Y | Y | Y | — | Stream+Batch |
| **JDBC** (generic) | Y | Y | Y | — | Stream+Batch |
| **Community CDC** | Y | — | — | — | Stream |

### Key-Value and Time-Series Databases

| Connector | Lookup | Sink | Mode |
|-----------|--------|------|------|
| **Tair (Redis Open-Source compatible)** | Y | Y | Stream |
| **Tair (Tair Enterprise)** | — | Y | Stream |
| **InfluxDB** (being discontinued) | — | Y | Stream |

### Debugging and Utility Connectors

| Connector | Source | Lookup | Sink | Mode |
|-----------|--------|--------|------|------|
| **Faker** (synthetic data) | Y | Y | — | Stream+Batch |
| **Datagen** | Y | — | — | Stream+Batch |
| **Blackhole** | — | — | Y | Stream+Batch |
| **Print** (console output) | — | — | Y | Stream+Batch |

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
-- Source Table
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

-- Sink Table
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
    'mutateType' = 'insertOrUpdate'   -- Upsert mode
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
-- HBase Lookup Table
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

To use a Connector not built into the platform:

1. Package the custom Connector as a JAR.
2. In the console, go to **Resource Management → Upload Additional Dependency File**.
3. Declare the custom Connector in the SQL `WITH` clause.

## Common Connector Issues

| Issue | Investigation |
|-------|---------------|
| Kafka consumer lag or backpressure | Check the number of Kafka partitions and consumer parallelism |
| Slow MySQL CDC full-snapshot phase | Tune `scan.fetch.size` and `debezium.snapshot.fetch.size` |
| Slow Hologres Sink writes | Check the write mode, batch size, and primary-key constraints |
| JDBC Lookup Join timeout | Enable `lookup.cache` to reduce direct calls to the external database |
| Incompatible Connector version | Check the engine-version and Connector support matrix |

## Official Documentation

- [Supported Connectors](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/supported-connectors)
- [Connector Documentation](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/connectors/)
- [Manage Custom Connectors](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/manage-custom-connectors)
- [Data Formats](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/data-format/)
