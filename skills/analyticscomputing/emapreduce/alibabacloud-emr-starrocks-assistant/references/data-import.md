# StarRocks Data Ingestion Best Practices

## Required Information Checklist

Before recommending an ingestion approach, gather the following information. If any item is missing, proactively ask:

| Information | Purpose | Example |
|------|------|------|
| **Data source** | Determines the ingestion method | Local file / Kafka / HDFS / S3 / OSS / MySQL CDC / Hive |
| **Data format** | Determines the ingestion method and parameters | CSV / JSON / Parquet / ORC / Avro |
| **Data volume** | Determines the ingestion method and concurrency | 100MB per batch / 50GB daily increment / continuous 100K rows/sec |
| **Latency requirement** | Determines sync vs async | Second-level visibility / minute-level / hourly batch |
| **Update pattern** | Determines whether to use Primary Key | Append-only / UPSERT by primary key / partial column update / contains DELETE |
| **Target table info** | Matches ingestion constraints | Table model, partitioning/bucketing, column list |
| **Cluster version** | Determines feature availability | v3.1 / v3.2 / v3.3 (FILES(), Pipe, etc. require v3.1+) |
| **Cluster size** | Determines concurrency and memory parameters | 3 BE x 64GB / shared-data 10 CN |

## Ingestion Method Selection Decision Flow

```
Step 1: Identify the data source
    ├─ Kafka / Pulsar → Step 2a
    ├─ Local file → Step 2b
    ├─ HDFS / S3 / OSS / Azure / GCS → Step 2c
    ├─ MySQL / PostgreSQL (CDC) → Step 2d
    └─ StarRocks internal table / external table → Step 2e

Step 2a: Kafka/Pulsar streaming data
    ├─ Native SQL management, simple scenarios → Routine Load (see data-import/routine-load.md)
    └─ Existing Flink/Kafka Connect pipeline → Flink Connector / Kafka Connector (see data-import/connectors.md)

Step 2b: Local file
    ├─ Single file < 10GB → Stream Load (see data-import/stream-load.md)
    └─ Single file > 10GB → Split and Stream Load, or upload to object storage and use Broker Load

Step 2c: HDFS / object storage
    ├─ < tens of GB + one-time ingestion → Broker Load (see data-import/broker-load.md)
    ├─ Tens of GB ~ TB scale → Broker Load or INSERT INTO SELECT FROM FILES()
    ├─ Need to continuously watch for new files → Pipe + AUTO_INGEST (see data-import/insert-and-pipe.md)
    └─ TB-scale first-time bulk migration (Hive) → Spark Load

Step 2d: CDC real-time sync
    ├─ Flink CDC → Flink Connector (recommended, see data-import/connectors.md)
    ├─ Debezium + Kafka → Routine Load or Kafka Connector
    └─ Canal / DataX / CloudCanal → Corresponding tool (see data-import/connectors.md)

Step 2e: Internal/external table
    └─ INSERT INTO target_table SELECT ... FROM source
```

Detailed configuration and examples for each step are in the corresponding reference file. Read on demand.

## Ingestion Method Quick Reference

| Ingestion method | Data source | Format | Data volume | Sync/Async | Latency | Applicable scenarios |
|---------|---------|------|--------|----------|--------|---------|
| **Stream Load** | Local file / HTTP | CSV, JSON | < 10GB | Sync | Immediate | Batch ingestion of local files |
| **Broker Load** | HDFS / S3 / OSS / GCS / Azure | CSV, JSON, Parquet, ORC | Tens to hundreds of GB | Async | Minutes to hours | Large-scale offline ingestion |
| **Routine Load** | Kafka / Pulsar | CSV, JSON, Avro | Continuous stream | Long-running | Seconds to minutes | Kafka streaming consumption |
| **INSERT INTO** | SQL / external table / FILES() | Multiple | Flexible | Sync | Immediate | Small data / cross-table ingestion |
| **Pipe** | HDFS / S3 | Parquet, ORC | 100GB to TB+ | Async, continuous | Minutes | Large-scale continuous file ingestion |
| **Spark Load** | Hive / HDFS | CSV, Parquet, ORC | Tens of GB to TB | Async | Hours | First-time bulk migration |
| **Flink Connector** | Flink data stream | Multiple | Continuous stream | Long-running | Seconds | Flink ecosystem integration / CDC |
| **Kafka Connector** | Kafka | CSV, JSON, Avro, Protobuf | Continuous stream | Long-running | Seconds to minutes | Kafka Connect ecosystem |

## Format Selection Guide

| Data format | Applicable scenarios | Caveats |
|---------|---------|---------|
| **CSV** | General-purpose, small files, Stream Load | Watch the delimiter, NULL values (`\N`), and escape characters |
| **JSON** | Nested structures, API data | Slower than CSV; prefer CSV for large files |
| **Parquet** | Large batches, columnar-storage optimized | Recommended for Broker Load / Pipe / FILES(), with automatic column mapping |
| **ORC** | Hive ecosystem data | Same as Parquet; watch column-name case matching |
| **Avro** | Kafka + Schema Registry | Supported only by Routine Load and Kafka Connector (v3.0.1+) |

## Common Anti-Patterns

Proactively check for and avoid the following when designing an ingestion plan:

| Anti-pattern | Consequence | Correct approach |
|--------|------|---------|
| Any high-frequency small-batch write — `INSERT INTO VALUES`, Routine Load with too-short `max_batch_interval`, Flink/Kafka Connector with too-short `sink.buffer-flush.interval-ms`, or high-throughput CDC (e.g. > 10K events/sec) without tuned flush sizes | Tablet version buildup (TOO_MANY_VERSION), compaction pressure | Batch the data and use Stream Load for one-shot loads; for streaming, raise `max_batch_interval` (Routine Load, ≥ 10s) or `sink.buffer-flush.interval-ms` (Flink/Kafka Connector, ≥ 5s) and watch compaction. Always proactively warn about TOO_MANY_VERSION in CDC scenarios with high event rates. |
| Stream Load ingesting an oversized file in one shot (>10GB) | Timeout, out-of-memory, costly retries | Split into multiple files < 5GB and ingest in batches |
| Routine Load without `max_error_number` set | Dirty data causes the task to PAUSE and cannot auto-resume | Set a reasonable `max_error_number` based on business tolerance |
| Running ingestion alongside large queries without resource isolation | Memory/CPU contention, both sides slow | Off-peak scheduling or isolation via Resource Group |
| Broker Load without a timeout (default 4h) | Large-file ingestion times out and must restart | Estimate based on data volume and set `timeout` |
| Ingesting JSON without specifying `jsonpaths` | Case mismatch in field names leads to all NULL | Use `jsonpaths` to map fields precisely |
| Primary Key table without `partial_update` set | Full-column updates cause write amplification | Update only changed columns; use `partial_update = true` |
| Routine Load `desired_concurrent_number` far exceeds Kafka partition count | Extra tasks idle and waste resources | `desired_concurrent_number ≤ Kafka partition count` |
| Ingesting CSV without specifying `column_separator` | The default `\t` doesn't match the actual delimiter, leading to garbled data | Explicitly specify `column_separator` |

## Reference File Index

When you need detailed configuration and examples for a specific ingestion method, read the corresponding file:

| Topic | Reference file | Contents |
|------|--------------|---------|
| Stream Load | [data-import/stream-load.md](data-import/stream-load.md) | HTTP syntax, parameter details, CSV/JSON examples, data transformation, multi-table ingestion |
| Broker Load | [data-import/broker-load.md](data-import/broker-load.md) | SQL syntax, storage system configuration, format parameters, timeout and memory tuning |
| Routine Load | [data-import/routine-load.md](data-import/routine-load.md) | Creation syntax, Kafka parameters, concurrency tuning, Avro configuration, monitoring |
| INSERT & Pipe | [data-import/insert-and-pipe.md](data-import/insert-and-pipe.md) | INSERT INTO usage, FILES() function, Pipe continuous ingestion, AUTO_INGEST |
| Ecosystem connectors | [data-import/connectors.md](data-import/connectors.md) | Flink/Kafka/Spark Connector, CDC solutions, DataX/CloudCanal |
| Performance tuning | [data-import/performance-tuning.md](data-import/performance-tuning.md) | Memory, concurrency, timeout, compaction, FE/BE parameters, resource isolation |
| Primary Key updates | [data-import/primary-key-updates.md](data-import/primary-key-updates.md) | UPSERT/DELETE modes, partial column update, conditional update |

## Output Template

When providing an ingestion recommendation, use the following structured format:

```markdown
## Ingestion Plan

### 1. Recommended ingestion method: {Stream Load / Broker Load / Routine Load / ...}
**Rationale:** {Why this method fits the user's data source, volume, and latency requirement}

### 2. Data format and preprocessing
**Source format:** {CSV / JSON / Parquet / ...}
**Preprocessing:** {Whether format conversion, field mapping, or data cleaning is required}

### 3. Key parameter configuration
| Parameter | Recommended value | Description |
|------|--------|------|
| ... | ... | ... |

### 4. Sample ingestion statement

​```sql
-- Complete ingestion statement or command
​```

### 5. Performance estimate
- **Estimated throughput:** {X MB/s or X 10K rows/sec}
- **Resource consumption:** {Memory / CPU / network}
- **Caveats:** {Version requirements, known limitations, compaction impact}

### 6. Monitoring and operations
- **Task state:** {SHOW LOAD / SHOW ROUTINE LOAD / SHOW PIPES}
- **Key metrics:** {Monitoring items to watch}
- **Error handling:** {Common issues and how to handle them}
```

## Scope Note

"Slow ingestion" splits into two cases — designing a new ingestion pipeline requires performance design (this topic) vs. a previously healthy ingestion suddenly slowing down requires troubleshooting cluster-level issues (-> [diagnostics.md](diagnostics.md)).
