# Routine Load Detailed Guide

## Table of Contents

1. [Overview](#overview)
2. [Creation Syntax](#creation-syntax)
3. [Kafka Parameter Configuration](#kafka-parameter-configuration)
4. [Data Formats](#data-formats)
5. [Concurrency and Performance Tuning](#concurrency-and-performance-tuning)
6. [Management and Monitoring](#management-and-monitoring)
7. [Best Practices](#best-practices)
8. [Common Issues](#common-issues)

---

## Overview

Routine Load is a long-running consumer task that continuously pulls data from Kafka (or Pulsar) and writes it to StarRocks. The FE splits the job into multiple sub-tasks and dispatches them to BEs.

**Key characteristics:**
- Runs continuously; no need to manually trigger each ingestion
- Guarantees exactly-once semantics (based on Kafka offsets + StarRocks transactions)
- Supports CSV, JSON, and Avro (v3.0.1+) formats
- Supports UPSERT / DELETE on Primary Key tables
- Auto-pauses on excessive errors and can be resumed

**How it works:**
```
FE (RoutineLoadMgr) -> splits into tasks (each task corresponds to one or more Kafka partitions)
    -> dispatches to BE -> BE consumes a batch from Kafka -> writes to StarRocks -> commits offset
    -> FE schedules the next round of tasks
```

---

## Creation Syntax

**Basic syntax:**

```sql
CREATE ROUTINE LOAD <database>.<job_name> ON <table_name>
[COLUMNS TERMINATED BY "<separator>"]
[COLUMNS (<column_list>)]
[WHERE <predicate>]
[PARTITION (<partition_list>)]
PROPERTIES
(
    "desired_concurrent_number" = "3",
    "max_error_number" = "1000",
    "max_batch_interval" = "20",
    "max_batch_rows" = "200000",
    "format" = "json",
    ...
)
FROM KAFKA
(
    "kafka_broker_list" = "broker1:9092,broker2:9092",
    "kafka_topic" = "my_topic",
    "property.group.id" = "starrocks_consumer_group",
    "property.kafka_default_offsets" = "OFFSET_END"
);
```

**CSV example:**

```sql
CREATE ROUTINE LOAD mydb.kafka_csv_load ON user_behavior
COLUMNS TERMINATED BY ","
COLUMNS (user_id, item_id, behavior_type, ts_str, event_time = str_to_date(ts_str, '%Y-%m-%d %H:%i:%s'))
WHERE behavior_type IN ('buy', 'cart')
PROPERTIES
(
    "desired_concurrent_number" = "5",
    "max_error_number" = "1000",
    "max_batch_interval" = "15",
    "strict_mode" = "true"
)
FROM KAFKA
(
    "kafka_broker_list" = "kafka1:9092,kafka2:9092,kafka3:9092",
    "kafka_topic" = "user_behavior_topic",
    "property.kafka_default_offsets" = "OFFSET_END"
);
```

**JSON example:**

```sql
CREATE ROUTINE LOAD mydb.kafka_json_load ON user_behavior
COLUMNS (user_id, item_id, behavior_type, event_time)
PROPERTIES
(
    "desired_concurrent_number" = "3",
    "format" = "json",
    "jsonpaths" = '["$.uid", "$.iid", "$.action", "$.ts"]',
    "max_error_number" = "500"
)
FROM KAFKA
(
    "kafka_broker_list" = "kafka1:9092",
    "kafka_topic" = "user_events",
    "property.kafka_default_offsets" = "OFFSET_END"
);
```

**Avro example (v3.0.1+):**

```sql
CREATE ROUTINE LOAD mydb.kafka_avro_load ON user_behavior
PROPERTIES
(
    "format" = "avro",
    "confluent.schema.registry.url" = "http://schema-registry:8081",
    "desired_concurrent_number" = "3"
)
FROM KAFKA
(
    "kafka_broker_list" = "kafka1:9092",
    "kafka_topic" = "user_events_avro"
);
```

---

## Kafka Parameter Configuration

### PROPERTIES Parameters

| Parameter | Default | Description |
|------|--------|------|
| `desired_concurrent_number` | 3 | Desired number of concurrent tasks |
| `max_batch_interval` | 10s | Maximum consumption time per task |
| `max_batch_rows` | 200000 | Maximum number of rows per task |
| `max_batch_size` | 100MB | Maximum data volume per task |
| `max_error_number` | 0 | Allowed number of error rows; exceeding causes PAUSE |
| `strict_mode` | false | Strict mode |
| `timezone` | Session timezone | Timezone |
| `format` | csv | Data format: csv / json / avro |
| `jsonpaths` | Auto | JSON field extraction paths |
| `strip_outer_array` | false | JSON outer-array unwrapping |
| `partial_update` | false | Partial column update. **Not a DELETE switch** — enabling this when the goal is DELETE handling is a misconfiguration; DELETE is signaled exclusively via the `__op` column / batch header. |
| `merge_condition` | None | Conditional update expression |

### FROM KAFKA Parameters

| Parameter | Required | Description |
|------|------|------|
| `kafka_broker_list` | Yes | List of Kafka broker addresses |
| `kafka_topic` | Yes | Topic to consume |
| `kafka_partitions` | No | Specific partitions to consume (default all) |
| `kafka_offsets` | No | Starting offset per partition |
| `property.group.id` | No | Consumer group ID |
| `property.kafka_default_offsets` | No | Default starting position: `OFFSET_BEGINNING` / `OFFSET_END` |
| `property.security.protocol` | No | `SASL_PLAINTEXT` / `SASL_SSL` |
| `property.sasl.mechanism` | No | `PLAIN` / `SCRAM-SHA-256`, etc. |
| `property.sasl.jaas.config` | No | SASL authentication configuration |

### Kafka SSL/SASL Authentication Example

```sql
FROM KAFKA
(
    "kafka_broker_list" = "kafka1:9093",
    "kafka_topic" = "secure_topic",
    "property.security.protocol" = "SASL_SSL",
    "property.sasl.mechanism" = "PLAIN",
    "property.sasl.jaas.config" =
        "org.apache.kafka.common.security.plain.PlainLoginModule required username='user' password='pass';"
)
```

---

## Data Formats

### CSV
- Default column separator is `\t`; modify via `COLUMNS TERMINATED BY`
- Each Kafka message is one CSV row
- Column mapping and transformation are the same as Stream Load

### JSON
- Each Kafka message is a JSON object
- Use `jsonpaths` to map fields precisely
- Supports nested field extraction

### Avro (v3.0.1+)
- Requires Schema Registry
- Auto-maps by field name
- Set `confluent.schema.registry.url` to the Schema Registry address
- Supports basic types and logical types (DATE, TIMESTAMP, etc.)

---

## Concurrency and Performance Tuning

### Computing Actual Concurrency

```
actual_concurrent = min(
    alive_be_number,
    kafka_partition_number,
    desired_concurrent_number,
    max_routine_load_task_concurrent_num    -- FE parameter, default 5
)
```

**Important:** Setting `desired_concurrent_number` higher than the Kafka partition count is pointless — extra tasks idle.

### Troubleshooting Insufficient Consumption Rate

Inspect the per-task execution in the BE logs:

```
# Search in the BE log
grep "routine load task" be.INFO
# Pay attention to the left_bytes field:
# left_bytes < 0 -> the per-round data volume hit the cap; increase max_batch_size
# left_bytes >= 0 -> consumption time ran out; increase max_batch_interval or routine_load_task_consume_second
```

### Tuning Steps

1. **Raise concurrency:** Increase `desired_concurrent_number` (not exceeding the Kafka partition count)
2. **Enlarge batches:** Increase `max_batch_size` and `max_batch_rows`
3. **Increase consumption time:** Increase `max_batch_interval`
4. **FE parameters:** Increase `max_routine_load_task_concurrent_num` (default 5) and `max_routine_load_task_num_per_be` (default 16)
5. **Expand Kafka partitions:** If the concurrency bottleneck is the Kafka partition count, expand Kafka partitions

### Key FE Parameters

| Parameter | Default | Description |
|------|--------|------|
| `max_routine_load_task_concurrent_num` | 5 | Maximum concurrent tasks per Routine Load |
| `max_routine_load_task_num_per_be` | 16 | Maximum Routine Load tasks per BE |
| `max_routine_load_batch_size` | 4GB | Maximum data volume per task |
| `routine_load_task_consume_second` | 15s | Maximum consumption duration per task |
| `routine_load_task_timeout_second` | 60s | Overall timeout per task |

---

## Management and Monitoring

### Viewing Task State

```sql
-- List all Routine Load jobs
SHOW ROUTINE LOAD FROM mydb;

-- View details of a specific job
SHOW ROUTINE LOAD FOR mydb.kafka_csv_load;

-- View running tasks
SHOW ROUTINE LOAD TASK WHERE JobName = "kafka_csv_load";
```

**Task states:**
- `NEED_SCHEDULE`: waiting to be scheduled
- `RUNNING`: running normally
- `PAUSED`: paused due to errors (resumable)
- `STOPPED`: manually stopped (not resumable)
- `CANCELLED`: cancelled due to errors (not resumable)

**Key monitoring fields:**
- `ReasonOfStateChanged`: reason for the state change (check when PAUSED)
- `ErrorLogUrls`: URLs of error logs
- `OtherMsg`: information such as Kafka offset lag
- `Statistics`: rows and bytes consumed

### Operation Commands

```sql
-- Pause
PAUSE ROUTINE LOAD FOR mydb.kafka_csv_load;

-- Resume
RESUME ROUTINE LOAD FOR mydb.kafka_csv_load;

-- Stop (not resumable)
STOP ROUTINE LOAD FOR mydb.kafka_csv_load;

-- Modify parameters
ALTER ROUTINE LOAD FOR mydb.kafka_csv_load
PROPERTIES ("desired_concurrent_number" = "5");

-- Modify Kafka offsets
ALTER ROUTINE LOAD FOR mydb.kafka_csv_load
FROM KAFKA ("kafka_offsets" = "0:12345,1:23456,2:34567");
```

---

## Best Practices

### Job Design
- One Routine Load job corresponds to one Kafka topic and one table
- Set `desired_concurrent_number` to the Kafka partition count (but not above the BE count)
- Set `max_error_number` based on business tolerance; in production, prefer > 0 to avoid frequent PAUSE

### Latency Control
- `max_batch_interval` controls the maximum latency (default 10s)
- Lowering this value reduces latency but increases the frequency of small-batch writes
- Recommended range: 10~30s (balances latency and compaction pressure)

### Error Handling
- After PAUSED, check `ReasonOfStateChanged` and `ErrorLogUrls`
- Common PAUSE reasons:
  - Data format errors exceeding `max_error_number`
  - Kafka offsets out of range (data was cleaned up)
  - Target table was dropped
- After fixing, resume with `RESUME ROUTINE LOAD`

### Offset Management
- StarRocks manages offsets on its own (does not rely on the Kafka consumer group)
- `OFFSET_END`: consume from the latest (recommended for new jobs)
- `OFFSET_BEGINNING`: consume from the beginning (when backfill is needed)
- Specify exact offsets: `ALTER ROUTINE LOAD ... FROM KAFKA ("kafka_offsets" = "0:12345")`

---

## Common Issues

| Issue | Cause | Resolution |
|------|------|---------|
| Task state is PAUSED | Error rows exceeded `max_error_number` | Check `ErrorLogUrls`, fix the data, then RESUME |
| Kafka lag keeps growing | Insufficient consumption rate | Follow the tuning steps to raise concurrency/batch size |
| Task is RUNNING but no data | Kafka topic has no new messages, or offsets are out of range | Check Kafka data and offsets |
| `No partitions have data available` | Kafka partition has no data | Normal; wait for new data |
| JSON parsing failure | `jsonpaths` is misconfigured | Verify that `jsonpaths` matches the actual JSON structure |
| Avro parsing failure | Schema Registry connection issue | Check the Schema Registry URL and network connectivity |
| Error on creation: `max_routine_load_task_num_per_be exceeded` | BE task count is maxed out | Stop unused Routine Loads or increase this parameter |
