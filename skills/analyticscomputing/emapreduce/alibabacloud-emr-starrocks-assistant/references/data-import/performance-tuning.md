# Ingestion Performance Tuning Guide

## Table of Contents

1. [Performance Baselines](#performance-baselines)
2. [Memory Optimization](#memory-optimization)
3. [Concurrency Optimization](#concurrency-optimization)
4. [Timeout Configuration](#timeout-configuration)
5. [Compaction Management](#compaction-management)
6. [Key FE Parameters](#key-fe-parameters)
7. [Key BE Parameters](#key-be-parameters)
8. [Resource Isolation](#resource-isolation)
9. [Ingestion Method Performance Comparison](#ingestion-method-performance-comparison)

---

## Performance Baselines

**Typical throughput reference** (per BE; not absolute; varies with hardware/network/data characteristics):

| Ingestion method | Typical throughput | Bottleneck factors |
|---------|---------|---------|
| Stream Load (CSV) | 50~200 MB/s | Network, BE CPU |
| Stream Load (JSON) | 20~80 MB/s | JSON parsing CPU overhead |
| Broker Load (Parquet) | 30~150 MB/s/BE | Storage read speed, network |
| Broker Load (CSV) | 20~100 MB/s/BE | CSV parsing, network |
| Routine Load | 5~50 MB/s/task | Kafka consumption rate, task count |
| INSERT INTO SELECT | Depends on source | Source-table scan speed, memory |

**Key factors influencing throughput:**
- File format: Parquet/ORC > CSV > JSON
- Column count and types: more/complex columns (JSON/BITMAP) write more slowly
- Target table model: Duplicate > Primary Key > Aggregate
- Indexes: Bloom Filter / Bitmap indexes add write overhead
- Compaction state: writes slow down when versions are piling up

---

## Memory Optimization

### BE Ingestion Memory Management

Ingestion uses the BE's `load` memory pool, which shares physical memory with the `query` memory pool.

**Global limits:**

| Parameter | Default | Description |
|------|--------|------|
| `load_process_max_memory_limit_percent` | 30% | Ingestion memory as a percentage of BE total memory |
| `load_process_max_memory_limit_bytes` | 100 GB | Absolute upper bound for ingestion memory |
| `enable_new_load_on_memory_limit_exceeded` | true | Whether new ingestion is allowed when memory is exhausted |

**Effective memory cap = min(BE total memory x 90% x 90% x 30%, 100GB)**

**Per-task limit:**

| Ingestion method | Control parameter | Default |
|---------|---------|--------|
| Stream Load | HTTP Header `exec_mem_limit` | 2 GB |
| Broker Load | PROPERTIES `exec_mem_limit` | 2 GB |
| Routine Load | PROPERTIES `exec_mem_limit` | 2 GB (per task) |
| INSERT INTO | Session `exec_mem_limit` | 2 GB |

**Tuning recommendations:**
- Increase `exec_mem_limit` to 4~8 GB when ingesting large data volumes
- When running multiple ingestion tasks in parallel, ensure the total memory does not exceed the limit
- If BE OOM happens frequently, reduce `load_process_max_memory_limit_percent`

### Write Buffer

| Parameter | Default | Description |
|------|--------|------|
| `write_buffer_size` | 100 MB | Size of an in-memory data block; flushed to disk when full |

- **Too small** -> frequent flushes, many small files, hurts query performance
- **Too large** -> risk of RPC timeout (`tablet_writer_rpc_timeout_sec`)
- Keep the default at 100 MB; in extreme cases adjust to 50~200 MB

---

## Concurrency Optimization

### Parallel Stream Loads

- Multiple Stream Loads can be submitted simultaneously; the BE handles them in parallel threads automatically
- Parallel ingestion into different partitions works best (no lock contention)
- Parallel ingestion into the same tablet of the same partition incurs lock waits
- Recommended concurrency: `min(BE count x 2, target table partition count)`

### Broker Load Concurrency

| Parameter | Default | Description |
|------|--------|------|
| `max_broker_load_job_concurrency` | 5 | Number of Broker Load jobs running simultaneously |

- Each Broker Load is internally parallelized (work spread across BEs)
- Raise concurrency when there are many independent ingestion jobs

### Routine Load Concurrency

See the concurrency and performance tuning section of [routine-load.md](routine-load.md).

Core formula:
```
actual_concurrent = min(alive_be_number, kafka_partition_number,
                        desired_concurrent_number, max_routine_load_task_concurrent_num)
```

### Transaction Concurrency

| Parameter | Default | Description |
|------|--------|------|
| `max_running_txn_num_per_db` | 1000 | Maximum concurrent transactions per database |

- Each ingestion task occupies one transaction
- In high-frequency ingestion scenarios, watch out for hitting this limit
- New ingestions queue up when the limit is exceeded

---

## Timeout Configuration

### Timeout Parameters by Ingestion Method

| Ingestion method | Timeout parameter | Default | How to set |
|---------|---------|--------|---------|
| Stream Load | `timeout` | 600s | HTTP Header |
| Broker Load | `timeout` | 14400s (4h) | PROPERTIES |
| Routine Load | `routine_load_task_timeout_second` | 60s | FE parameter |
| INSERT INTO | `query_timeout` | 300s | Session variable |

### FE-Side Timeout Parameters

| Parameter | Default | Description |
|------|--------|------|
| `stream_load_default_timeout_second` | 600 | Default timeout for Stream Load |
| `max_stream_load_timeout_second` | 259200 (3 days) | Maximum timeout for Stream Load |
| `broker_load_default_timeout_second` | 14400 | Default timeout for Broker Load |
| `max_load_timeout_second` | 259200 | Global maximum timeout |
| `insert_load_default_timeout_second` | 3600 | Default timeout for INSERT |

### BE-Side Timeout Parameters

| Parameter | Default | Description |
|------|--------|------|
| `streaming_load_rpc_max_alive_time_sec` | 1200 | Stream Load write process timeout |
| `tablet_writer_rpc_timeout_sec` | 600 | Data write RPC timeout |
| `broker_write_timeout_seconds` | 131072 | Broker write timeout |

### Timeout Estimation Formula

```
recommended timeout = data volume (MB) / expected throughput (MB/s) x safety factor (1.5~2)
```

---

## Compaction Management

### Why Compaction Affects Ingestion

Each ingestion generates a new tablet version. If the ingestion frequency exceeds the compaction rate, versions pile up:
- More than 1000 versions -> new ingestion is rejected (`TOO_MANY_VERSION`)
- Queries slow down when versions pile up (must merge multiple versions)

### Key BE Parameters

| Parameter | Default | Description |
|------|--------|------|
| `cumulative_compaction_num_threads_per_disk` | 1 | Cumulative compaction threads per disk |
| `base_compaction_num_threads_per_disk` | 1 | Base compaction threads per disk |
| `max_cumulative_compaction_num_singleton_deltas` | 1000 (≤v3.1) / **500** (v3.2+) | Version threshold that triggers base compaction |
| `tablet_max_versions` | 1000 | Maximum tablet versions (writes rejected above this) |

### Tuning Recommendations

| Scenario | Tuning direction |
|------|---------|
| High-frequency Stream Load (sub-second) | Batch to one ingestion every 10~30s; increase compaction threads |
| Routine Load continuous writes | Increase `max_batch_interval` to 15~30s |
| Large-batch Broker Load | Usually no tuning needed; a single load generates only one version |
| Multi-table high-frequency writes simultaneously | Increase compaction thread count (2~4 per disk) |

### Monitoring Compaction State

```sql
-- Check the number of tablet versions
SHOW TABLET FROM table_name;

-- Tablets with too many versions
SELECT * FROM information_schema.be_tablets
WHERE num_version > 500
ORDER BY num_version DESC;
```

---

## Key FE Parameters

| Parameter | Default | Description | Tuning scenario |
|------|--------|------|---------|
| `max_running_txn_num_per_db` | 1000 | Maximum concurrent transactions per DB | High-frequency ingestion reporting "transactions full" |
| `desired_max_waiting_jobs` | 1024 | Maximum queued jobs | Many Broker Loads queueing |
| `max_broker_load_job_concurrency` | 5 | Maximum concurrent Broker Loads | Many parallel Broker Loads |
| `label_keep_max_second` | 259200 (3 days) | Historical label retention time | Label conflicts |
| `max_routine_load_task_concurrent_num` | 5 | Maximum concurrent tasks per job | Slow Routine Load consumption |
| `max_routine_load_task_num_per_be` | 16 | Maximum tasks per BE | Many Routine Load jobs |
| `stream_load_default_timeout_second` | 600 | Default Stream Load timeout | Timeouts on large files |

---

## Key BE Parameters

| Parameter | Default | Description | Tuning scenario |
|------|--------|------|---------|
| `load_process_max_memory_limit_percent` | 30 | Ingestion memory percentage | BE OOM |
| `write_buffer_size` | 100 MB | Write buffer size | Too many small files / RPC timeouts |
| `streaming_load_max_mb` | 102400 | Maximum file size for Stream Load | Large-file ingestion |
| `streaming_load_rpc_max_alive_time_sec` | 1200 | Write process timeout | Timeouts when writing large files |
| `cumulative_compaction_num_threads_per_disk` | 1 | Compaction threads | Version buildup |
| `load_error_log_reserve_hours` | 48 | Error log retention | Investigating historical errors |
| `routine_load_thread_pool_size` | 10 | Routine Load thread pool | Many Routine Load jobs |

---

## Resource Isolation

### Resource Contention Between Ingestion and Queries

Ingestion and queries share the BE's CPU, memory, and IO resources. Under heavy load, they affect each other.

**Isolation strategies:**

1. **Time-based isolation**: schedule large-batch ingestion during off-peak hours
2. **Resource Group (v3.1+)**: assign ingestion and queries to different resource groups

```sql
-- Create a resource group dedicated to ingestion
CREATE RESOURCE GROUP load_rg
TO (user = 'load_user')
WITH (
    'cpu_weight' = '4',
    'mem_limit' = '30%',
    'type' = 'normal'
);

-- Create a resource group dedicated to queries
CREATE RESOURCE GROUP query_rg
TO (user = 'query_user')
WITH (
    'cpu_weight' = '6',
    'mem_limit' = '50%',
    'type' = 'normal'
);
```

3. **BE node isolation**: in shared-data architecture, use different CN groups for ingestion and queries

---

## Ingestion Method Performance Comparison

| Dimension | Stream Load | Broker Load | Routine Load | INSERT SELECT |
|------|------------|-------------|-------------|---------------|
| Throughput ceiling | High | High (parallel across BEs) | Medium | Medium |
| Latency | Low (sync) | High (async, queued) | Low~medium | Low (sync) |
| CPU overhead | Medium | Medium | Low~medium | Depends on SQL |
| Memory overhead | Medium | Medium | Low (small batches) | High (possibly full-table scan) |
| Version generation | 1 per run | 1 per run | 1 per batch | 1 per run |
| Suitable for high frequency | Yes, when batched | No | Yes (long-running) | No |
