# Core Flink SQL Concepts

## Core Concepts and Terminology

### Streaming Data and Real-Time Computing

| Concept | Description |
|---------|-------------|
| **Stream Data** | A continuously produced, unbounded data stream, such as logs, sensor readings, and transaction records |
| **Real-Time Computing** | Processes data and emits results as soon as data arrives, unlike offline or delayed Batch Computing |
| **Event Time and Processing Time** | Event Time is when data was actually produced; Processing Time is when the system processes it. Windows and Watermarks rely on Event Time |

### Tables and SQL

| Concept | Description |
|---------|-------------|
| **Flink SQL** | An SQL engine based on Apache Calcite that supports DDL (table definitions), DQL (queries), and DML (writes) |
| **Source Table** | An input to the data flow that reads from an external system such as Kafka or MySQL CDC |
| **Lookup Table (Dimension Table)** | A reference table for joining dimension data, such as user profiles or product catalogs; it enriches streaming data through a Join |
| **Sink Table (Result Table)** | The output of the data flow, writing results to systems such as Hologres, Paimon, or MySQL |
| **Dynamic Table** | Flink's abstraction of stream data as a table that changes over time; SQL queries continuously produce updates |

### Windows

| Window type | Description | Typical use |
|-------------|-------------|-------------|
| **Tumbling Window** | Fixed-size, contiguous, non-overlapping time windows | Calculate PV/UV every five minutes |
| **Sliding Window** | Fixed-size, overlapping time windows | Refresh statistics for the latest ten minutes every minute |
| **Session Window** | Windows separated automatically by a Session Gap | Analyze user-session behavior |
| **OVER Window** | An aggregate Window Function evaluated for each row | Moving averages and cumulative values |

### Watermarks

**Definition:** A timestamp mechanism for handling out-of-order events. A Watermark tells Flink that it no longer waits for events earlier than that timestamp.

**Key setting:**

- `WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND` allows five seconds of out-of-order data.
- Excessive Watermark delay postpones output; insufficient delay may discard late data.

### State

| State type | Description |
|------------|-------------|
| **Keyed State** | State partitioned by key, with independent State for each key |
| **Operator State** | Operator-level State that is not partitioned by key |

**State Backend:**

- Alibaba Cloud Flink includes the proprietary **Gemini** State storage engine, which offers higher performance than open-source RocksDB.
- State compression and incremental Checkpoints can significantly reduce storage and I/O overhead.

### Checkpoints and Savepoints

| Concept | Description | Difference |
|---------|-------------|------------|
| **Checkpoint** | A globally consistent snapshot created periodically by Flink for failure recovery | Generated automatically and managed by the system |
| **Savepoint** | A user-triggered State snapshot for job upgrades, migration, and State reuse | Created manually and retained persistently |

**Recommended practices:**

- Always enable Checkpoints for production jobs. The default interval is 60 seconds; adjust it to business requirements.
- Create a Savepoint before upgrading a stateful job so its State can be rolled back.
- Alibaba Cloud Flink supports **State compatibility checks** that automatically determine whether old and new State are compatible.

### CDC (Change Data Capture)

**Definition:** Capture incremental database changes (INSERT/UPDATE/DELETE) for real-time data synchronization.

- **Flink CDC:** CDC components supporting databases such as MySQL, PostgreSQL, and MongoDB.
- **CDAS (CREATE DATABASE AS):** whole-database synchronization that automatically discovers and synchronizes Tables in a Database.
- **CTAS (CREATE TABLE AS):** synchronization for one table or sharded tables.
- Supports automatic **Schema Evolution** synchronization.

## Key Architecture Components

| Component | Description |
|-----------|-------------|
| **JobManager (JM)** | Coordinates the Job, including scheduling, Checkpoint coordination, and recovery. Alibaba Cloud Flink includes high availability and avoids a single point of failure |
| **TaskManager (TM)** | Executes Job computation and maintains State; CPU and memory can be configured at operator level |
| **Resource Queue** | Manages resource quotas and isolates resources among users |
| **Session Cluster** | Shares JobManager resources and supports rapid debugging in development or test environments |
| **Catalog** | Manages metadata and allows registered Table schemas to be reused instead of repeating `CREATE TABLE` |

## Official Documentation

- [Engine Versions](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/engine-version)
