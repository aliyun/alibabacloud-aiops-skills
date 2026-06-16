# Alibaba Cloud Realtime Compute for Apache Flink — Core Concepts

## Product Overview

Alibaba Cloud Realtime Compute for Apache Flink is an all-in-one **real-time big data analytics platform** built on Apache Flink, providing end-to-end **sub-second** real-time data analysis capabilities. Core features:

- **Fully Managed Serverless**: Ready to use out of the box; no need to build your own cluster
- **100% Apache Flink Compatible**: Supports smooth migration from open-source Flink to the cloud
- **Standard SQL Lowers the Development Barrier**: Built-in rich connectors and functions
- **Enterprise-Grade Enhanced Engine**: Approximately **2x performance improvement** over open-source Flink (based on the proprietary state storage engine **Gemini** + SQL operator optimizations)

## Core Comparison with Open-Source Apache Flink

| Dimension | Open-Source Flink | Realtime Compute for Apache Flink |
|---|---|---|
| Performance | Community performance | Nexmark benchmark reaches **2x** open-source (Gemini state storage + SQL operator optimizations) |
| Elasticity | None built-in | Smart scaling, fine-grained CU-level tuning |
| Development Platform | None | All-in-one web console: development, debugging, deployment, and O&M across the full lifecycle |
| Connectors | Requires manual integration | **30+** ready to use out of the box |
| O&M Monitoring | None built-in | Visual console + multi-dimensional metrics + smart diagnostics + alerts |
| High Availability | Depends on user configuration | Same-city HA, multiple regions available, full-chain automatic fault tolerance |
| Technical Support | Community | 24/7 technical support, 99.9% SLA |

## Core Concept Terminology

### Stream Data & Real-Time Computing

| Concept | Description |
|---|---|
| **Stream Data** | Continuously generated, unbounded data streams, such as logs, sensor readings, transaction records |
| **Real-Time Computing** | Data is processed and results are output immediately upon arrival, as opposed to batch computing (offline/delayed processing) |
| **Event Time vs Processing Time** | Event Time = when the data was actually generated (Processing Time = when the system receives it). Windows and watermarks rely on Event Time |

### Tables & SQL

| Concept | Description |
|---|---|
| **Flink SQL** | SQL engine based on Apache Calcite, supporting DDL (table creation), DQL (queries), DML (writes) |
| **Source Table** | Data stream entry point; reads data from external systems (Kafka, MySQL CDC, etc.) |
| **Lookup Table (Dimension Table)** | Reference table for associating dimensional information (e.g. user profiles, product catalogs); enriches stream data via JOIN |
| **Sink Table (Result Table)** | Data output point; writes computation results to target systems (Hologres, Paimon, MySQL, etc.) |
| **Dynamic Table** | Flink abstracts stream data as a table that changes over time; SQL queries continuously produce updated results |

### Windows

| Window Type | Description | Use Case |
|---|---|---|
| **Tumbling Window** | Fixed-size, non-overlapping, contiguous time windows | PV/UV statistics every 5 minutes |
| **Sliding Window** | Fixed-size, overlapping time windows | Last 10 minutes of data, refreshed every 1 minute |
| **Session Window** | Windows automatically grouped by session gaps | User session behavior analysis |
| **OVER Window** | Aggregate window function; row-by-row computation | Moving averages, cumulative values |

### Watermark

**Definition**: A timestamp mechanism for handling out-of-order events. A watermark tells Flink "no longer wait for events before this timestamp."

**Key Parameters**:
- `WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND` — Allows 5 seconds of out-of-order tolerance
- Excessively large watermark delays cause delayed output; excessively small values cause data loss

### State

| State Type | Description |
|---|---|
| **Keyed State** | State grouped by key; each key maintains its own state independently |
| **Operator State** | Operator-level state; not partitioned by key |

**State Backend**:
- Cloud Flink includes **Gemini**, a proprietary state storage engine that outperforms open-source RocksDB
- Supports state compression and incremental checkpoints, significantly reducing storage and I/O overhead

### Checkpoint & Savepoint

| Concept | Description | Difference |
|---|---|---|
| **Checkpoint** | Globally consistent snapshots automatically created by Flink at regular intervals; used for failure recovery | Auto-generated, system-managed |
| **Savepoint** | User-triggered state snapshots; used for job upgrades, migration, and state reuse | Manually created, persistently retained |

**Best Practices**:
- Always enable Checkpoint for production jobs (default interval 60s; adjust based on business needs)
- Create a Savepoint before upgrading jobs to ensure state can be rolled back
- Cloud Flink supports **state compatibility checks**, automatically determining whether old and new version states are compatible

### CEP (Complex Event Processing)

**Definition**: Complex Event Processing, used to detect and match complex event patterns in stream data (e.g. "User A → User B → User C" sequences).

**API**: Flink CEP (Java/Scala), using Pattern API to describe event sequences, time constraints, and filter conditions.

**Use Cases**: Risk control detection, anomaly alerting, business rule engines.

### CDC (Change Data Capture)

**Definition**: Captures incremental database changes (INSERT/UPDATE/DELETE) to enable real-time data synchronization.

- **Flink CDC**: Enterprise-grade CDC component supporting MySQL, PostgreSQL, MongoDB, etc.
- **CDAS (Create Database As Statement)**: Full-database sync; automatically discovers and syncs all tables in a database
- **CTAS (Create Table As Statement)**: Single-table / sharded-table sync
- Supports **automatic schema evolution sync**

## Development Methods

| Type | Language/API | Use Case |
|---|---|---|
| **SQL Job** | Flink SQL (DDL + DML) | Data pipelines, real-time ETL, real-time dashboards, metric computation |
| **JAR Job** | Java (DataStream / Table API) | Complex business logic, custom operators, CEP |
| **Python Job** | PyFlink | Data analysis, ML integration, quick onboarding for Python teams |
| **YAML Job** | Data Ingestion YAML | Data sync scenarios (declarative configuration) |

## Key Architecture Components

| Component | Description |
|---|---|
| **JobManager (JM)** | Job coordinator: scheduling, checkpoint coordination, failure recovery. Cloud Flink includes built-in HA with no single point of failure |
| **TaskManager (TM)** | Job executor: runs computation logic, maintains state. CPU/Memory configurable at the operator level |
| **Resource Queue** | Multi-user resource isolation mechanism for resource quota management |
| **Session Cluster** | Shares JM resources; suitable for rapid debugging in dev/test environments |
| **Catalog** | Metadata management; auto-registers table structures to avoid manual CREATE TABLE |

## Official Documentation Links

- [Product Overview](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/)
- [Features](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/product-function-custom-node-sc-normal)
- [Comparison with Open-Source Flink](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/what-is-alibaba-cloud-realtime-compute-for-apache-flink)
- [Engine Version Overview](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/engine-version)
