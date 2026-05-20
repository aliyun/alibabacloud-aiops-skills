# Ecosystem Connectors Guide

## Table of Contents

1. [Connector Selection](#connector-selection)
2. [Flink Connector](#flink-connector)
3. [Flink CDC](#flink-cdc)
4. [Kafka Connector](#kafka-connector)
5. [Spark Connector](#spark-connector)
6. [Spark Load](#spark-load)
7. [Other Tools](#other-tools)

---

## Connector Selection

| Scenario | Recommended solution | Rationale |
|------|---------|------|
| Flink real-time stream writes | Flink Connector | Native integration; exactly-once supported |
| MySQL/PG CDC real-time sync | Flink CDC + Flink Connector | End-to-end CDC; auto schema sync |
| Kafka Connect ecosystem | Kafka Connector (Sink) | Zero-code configuration; SMT support |
| Spark batch ETL | Spark Connector | Native integration; distributed writes |
| First-time migration of large Hive tables | Spark Load | Preprocessing on a Spark cluster; TB scale |
| Simple full MySQL migration | DataX / SMT | Lightweight; easy to configure |
| Multi-source sync in the cloud | CloudCanal | SaaS-based; no operations required |

---

## Flink Connector

### Overview

StarRocks provides an official Flink Connector (`starrocks-connector-for-apache-flink`) that writes Flink DataStream / Table API data to StarRocks via the Stream Load protocol.

### Maven Dependency

```xml
<dependency>
    <groupId>com.starrocks</groupId>
    <artifactId>flink-connector-starrocks</artifactId>
    <version>${connector.version}</version>
</dependency>
```

For the version compatibility matrix, see the [official documentation](https://docs.starrocks.io/zh/loading/Flink-connector-starrocks).

### Flink SQL Example

```sql
-- Create the StarRocks sink table
CREATE TABLE sr_sink (
    user_id BIGINT,
    user_name STRING,
    score INT,
    PRIMARY KEY (user_id) NOT ENFORCED
) WITH (
    'connector' = 'starrocks',
    'jdbc-url' = 'jdbc:mysql://fe_host:9030',
    'load-url' = 'fe_host:8030',
    'database-name' = 'mydb',
    'table-name' = 'user_table',
    'username' = 'root',
    'password' = '',
    'sink.buffer-flush.max-rows' = '50000',
    'sink.buffer-flush.max-bytes' = '67108864',
    'sink.buffer-flush.interval-ms' = '5000',
    'sink.properties.format' = 'json',
    'sink.properties.strip_outer_array' = 'true'
);

-- Read from Kafka and write to StarRocks
INSERT INTO sr_sink
SELECT user_id, user_name, score FROM kafka_source;
```

### Key Parameters

| Parameter | Default | Description |
|------|--------|------|
| `sink.buffer-flush.max-rows` | 50000 | Flush is triggered when this many rows are buffered |
| `sink.buffer-flush.max-bytes` | 64MB | Flush is triggered when this many bytes are buffered |
| `sink.buffer-flush.interval-ms` | 300000 | Scheduled flush interval (ms) |
| `sink.max-retries` | 3 | Number of retries on failure |
| `sink.semantic` | at-least-once | Semantics: `at-least-once` / `exactly-once` |
| `sink.properties.format` | csv | Data format: csv / json |
| `sink.properties.partial_update` | false | Partial column update |
| `sink.parallelism` | Flink default | Sink parallelism |

### Exactly-Once Configuration

```sql
'sink.semantic' = 'exactly-once',
'sink.label-prefix' = 'flink_load'
```

You must also enable Flink Checkpoint; StarRocks implements 2PC via the Stream Load Transaction Interface.

### Performance Tuning

- **Enlarge buffers:** `sink.buffer-flush.max-bytes = 128MB` to reduce flush frequency
- **Adjust interval:** `sink.buffer-flush.interval-ms = 10000` to balance latency and throughput
- **Parallelism (cap, not just target):** `sink.parallelism` should be **≤ the Kafka partition count** of the source topic — extra sinks idle, and over-parallelizing high-throughput CDC accelerates tablet version buildup. The Kafka partition count is the natural ceiling; match it as the upper bound, do not exceed it.
- **Format choice:** JSON is more flexible but slower; CSV is faster (use CSV for high throughput)

---

## Flink CDC

### Overview

Flink CDC is a Flink-based Change Data Capture framework that can sync changes from MySQL, PostgreSQL, Oracle, MongoDB, and other databases to StarRocks in real time.

### Typical Architecture

```
MySQL (binlog) -> Flink CDC Source -> Flink Connector -> StarRocks (Primary Key Table)
```

### Flink SQL Example (MySQL CDC -> StarRocks)

```sql
-- MySQL CDC Source
CREATE TABLE mysql_source (
    id BIGINT,
    name STRING,
    age INT,
    update_time TIMESTAMP(3),
    PRIMARY KEY (id) NOT ENFORCED
) WITH (
    'connector' = 'mysql-cdc',
    'hostname' = 'mysql_host',
    'port' = '3306',
    'username' = 'cdc_user',
    'password' = 'cdc_pass',
    'database-name' = 'source_db',
    'table-name' = 'user_table',
    'server-time-zone' = 'Asia/Shanghai'
);

-- StarRocks sink (Primary Key table)
CREATE TABLE sr_sink (
    id BIGINT,
    name STRING,
    age INT,
    update_time TIMESTAMP(3),
    PRIMARY KEY (id) NOT ENFORCED
) WITH (
    'connector' = 'starrocks',
    'jdbc-url' = 'jdbc:mysql://fe_host:9030',
    'load-url' = 'fe_host:8030',
    'database-name' = 'target_db',
    'table-name' = 'user_table',
    'username' = 'root',
    'password' = '',
    'sink.properties.format' = 'json',
    'sink.properties.strip_outer_array' = 'true'
);

-- Real-time sync
INSERT INTO sr_sink SELECT * FROM mysql_source;
```

### Caveats
- The target table must be a **Primary Key** table
- The Flink Connector automatically handles INSERT / UPDATE / DELETE events. **Under the hood it still uses StarRocks' `__op` contract, which is a binary pair you must state in full**: literal column `__op`, with **`__op=0` → UPSERT** and **`__op=1` → DELETE**. Both mappings must appear in the response (RowKind `+I` / `+U` → `__op=0`; RowKind `-D` → `__op=1`) — explaining only the DELETE side is incomplete. This holds whether the question is about DELETE or UPSERT; users need both values to debug "DELETE not applied" and the symmetric "UPSERT silently overwritten" failures.
- Enable Flink Checkpoint to guarantee consistency
- The full phase may consume a lot of memory; size the Flink TaskManager memory appropriately

---

## Kafka Connector

### Overview

The StarRocks Kafka Connector is a Kafka Connect sink connector that writes data from a Kafka topic to StarRocks.

### Configuration Example

```json
{
    "name": "starrocks-sink",
    "config": {
        "connector.class": "com.starrocks.connector.kafka.StarRocksSinkConnector",
        "topics": "user_events",
        "starrocks.http.url": "fe_host:8030",
        "starrocks.jdbc.url": "jdbc:mysql://fe_host:9030",
        "starrocks.username": "root",
        "starrocks.password": "",
        "starrocks.database.name": "mydb",
        "starrocks.table.name": "user_events",
        "key.converter": "org.apache.kafka.connect.json.JsonConverter",
        "value.converter": "org.apache.kafka.connect.json.JsonConverter",
        "value.converter.schemas.enable": "false",
        "sink.properties.format": "json",
        "sink.properties.strip_outer_array": "true",
        "sink.buffer-flush.max-bytes": "67108864",
        "sink.buffer-flush.interval-ms": "5000"
    }
}
```

### Supported Data Formats
- **JSON**: most common
- **CSV**: high-throughput scenarios
- **Avro**: with Schema Registry (v3.0+)
- **Protobuf**: with Schema Registry (v3.0+)

### vs Routine Load

| Dimension | Kafka Connector | Routine Load |
|------|----------------|-------------|
| Deployment | Requires a Kafka Connect cluster | Built into StarRocks |
| Management | Kafka Connect REST API | SQL commands |
| Formats | JSON/CSV/Avro/Protobuf | JSON/CSV/Avro |
| Flexibility | SMT transformation chain supported | SET/WHERE supported |
| Applicable scenarios | Existing Kafka Connect ecosystem | Pure SQL management |

---

## Spark Connector

### Overview

The StarRocks Spark Connector enables batch writes from Spark to StarRocks, using Stream Load under the hood.

### DataFrame Example

```scala
df.write
  .format("starrocks")
  .option("starrocks.fe.http.url", "fe_host:8030")
  .option("starrocks.fe.jdbc.url", "jdbc:mysql://fe_host:9030")
  .option("starrocks.user", "root")
  .option("starrocks.password", "")
  .option("starrocks.table.identifier", "mydb.target_table")
  .option("starrocks.write.properties.format", "csv")
  .option("starrocks.write.buffer.size", "104857600")
  .option("starrocks.write.flush.interval.ms", "10000")
  .mode("append")
  .save()
```

### Spark SQL Example

```sql
CREATE TABLE sr_table
USING starrocks
OPTIONS (
    "starrocks.fe.http.url" = "fe_host:8030",
    "starrocks.fe.jdbc.url" = "jdbc:mysql://fe_host:9030",
    "starrocks.user" = "root",
    "starrocks.password" = "",
    "starrocks.table.identifier" = "mydb.target_table"
);

INSERT INTO sr_table SELECT * FROM hive_table WHERE dt = '2024-01-01';
```

---

## Spark Load

### Overview

Spark Load uses an external Spark cluster for ETL preprocessing, suitable for TB-scale first-time bulk migration.

**Note:** Spark Load does not support Primary Key tables.

### Create the Spark Resource

```sql
CREATE EXTERNAL RESOURCE "spark_resource"
PROPERTIES (
    "type" = "spark",
    "spark.master" = "yarn",
    "spark.submit.deployMode" = "cluster",
    "spark.executor.memory" = "4g",
    "spark.yarn.queue" = "default",
    "working_dir" = "hdfs://namenode/tmp/starrocks_spark_load",
    "broker" = "hdfs_broker"
);
```

### Submit Spark Load

```sql
LOAD LABEL mydb.spark_migration
(
    DATA INFILE("hdfs://namenode/hive/warehouse/source_table/*")
    INTO TABLE target_table
    FORMAT AS "parquet"
)
WITH RESOURCE "spark_resource"
PROPERTIES ("timeout" = "86400");
```

### Applicable Scenarios
- First-time full migration of large Hive tables (TB scale)
- Need to build a global BITMAP dictionary
- An existing Spark/YARN cluster is available

---

## Other Tools

### DataX

Alibaba's open-source offline data sync tool, which writes via the StarRocksWriter plugin.

```json
{
    "writer": {
        "name": "starrockswriter",
        "parameter": {
            "username": "root",
            "password": "",
            "database": "mydb",
            "table": "target_table",
            "loadUrl": ["fe_host:8030"],
            "jdbcUrl": "jdbc:mysql://fe_host:9030",
            "column": ["col1", "col2", "col3"],
            "loadProps": {
                "format": "json",
                "strip_outer_array": true
            }
        }
    }
}
```

### CloudCanal

Cloud data sync SaaS service supporting:
- MySQL / PostgreSQL / Oracle -> StarRocks real-time sync
- Integrated full + incremental
- No code; configure via the web console
- Automatic schema migration

### SMT (StarRocks Migration Tool)

StarRocks's official migration tool:
- Automatically converts other databases' DDL to StarRocks DDL
- Automatically generates DataX configuration files
- Supports MySQL, PostgreSQL, Oracle, and Hive
