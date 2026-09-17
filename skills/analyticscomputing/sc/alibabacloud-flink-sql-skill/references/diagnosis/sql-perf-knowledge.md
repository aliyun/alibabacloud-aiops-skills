# Flink SQL Performance-Issue Pattern Knowledge Base

Read when the [diagnosis entry point](README.md) calls for performance knowledge, or when [common performance diagnosis](sql-perf-diagnosis.md) needs patterns and optimization conditions. Knowledge-only queries do not require online evidence. Obtain data for an actual diagnosis through [job-observability.md](job-observability.md).

This document preserves symptoms, candidate causes, verification points, and configuration for eight issue categories. Metric names, thresholds, and configuration values are examples, not a fixed Metric dictionary or a default tuning recipe. Verify the target version, actual root cause, and semantics before optimizing; implementation requires separate authorization.

---

## Pattern 1: Backpressure

### Symptoms

- Operator `busyTimeMsPerSecond` is near or equal to 1,000.
- An upstream operator's `backPressuredTimeMsPerSecond` exceeds 500.
- An operator appears red for backpressure in the Flink Web UI.
- Source lag grows continuously.

### Common Causes

1. **Excessive Agg/Join computation:** stateful operators such as GroupAggregate and Regular Join lack processing capacity.
2. **Data skew:** one Subtask handles far more data than other Subtasks.
3. **Sink write bottleneck:** a downstream storage system such as MySQL or HBase cannot write fast enough.
4. **Insufficient resources:** parallelism is too low, or TM memory/CPU is insufficient.
5. **Slow State access:** in large-State workloads, a backend such as RocksDB may be limited by State access, caches, compaction, or disk I/O.

### Verification

Required evidence: runtime topology; throughput, busy time, and backpressure by Vertex/Subtask; TM CPU/memory/GC; and evidence from Sink calls, State access, or threads.

- High busy time does not necessarily mean insufficient CPU. Distinguish computation, Join-output amplification, State access, GC, and external calls.
- A downstream regression should align with upstream backpressure in time and path. Inspect each input of a multi-input operator; when only some Subtasks are busy, see pattern 8.
- A constrained Sink requires write, retry, throttling, or commit evidence. Upstream backpressure alone does not prove an external failure.

Validation objective: measure throughput, backlog, backpressure, and result correctness together after optimization.

### Optimizations and Applicability

1. **MiniBatch and two-phase aggregation:** evaluate only when supported by the aggregate functions, target version, and actual Plan. The table below gives examples.
2. **Bottleneck parallelism:** adjust according to available resources and input partitions; it cannot directly solve a single hot key.
3. **SQL rewrite:** remove unnecessary computation and filter or project earlier. A Lookup Join is not semantically equivalent to a stream-stream Join.
4. **Sink batching:** balance batch size and flush interval against throughput, latency, memory, and commit semantics.

### Key Configuration

| Option | Description | Example / applicability |
|--------|-------------|-------------------------|
| `table.exec.mini-batch.enabled` | Enable MiniBatch | `true` |
| `table.exec.mini-batch.allow-latency` | MiniBatch latency | `5s` |
| `table.exec.mini-batch.size` | MiniBatch size | `5000` |
| `table.optimizer.agg-phase-strategy` | Aggregation strategy | `TWO_PHASE` |

---

## Pattern 2: Accumulating Latency

### Symptoms

- Source lag grows continuously.
- Source `numRecordsOutPerSecond` is stable, but downstream operators cannot keep up.
- Users report steadily increasing data latency.
- Latency grows without a Job failover.

### Common Causes

1. **Propagated downstream backpressure:** a slow downstream operator prevents Source consumption.
2. **Insufficient source partitions:** Kafka has fewer partitions than parallel Subtasks, leaving some idle.
3. **Slow Sink writes:** the downstream storage system is the bottleneck.
4. **Input surge:** upstream volume suddenly exceeds processing capacity.
5. **GC pauses:** frequent Full GC interrupts processing.

### Verification

Required evidence: source backlog/consumer position when reported; Source and Sink input/output; end-to-end latency; Subtask assignment; GC; and external calls.

- Distinguish source backlog, event-time lag, processing delay, and externally visible Sink delay.
- Compare input growth with processing capacity to distinguish a traffic burst, insufficient effective Source concurrency, and persistent downstream blocking.
- When processing rate is normal but visibility is delayed, check time triggers, batch flushes, and transaction commits rather than only raising parallelism.

Validation objective: determine whether backlog converges and latency improves while resources and commit semantics remain correct.

### Optimizations and Applicability

1. **Bottleneck parallelism:** evaluate after identifying the constrained operator; see pattern 1 for backpressure analysis.
2. **Sink batching and flushing:** tune batch size for throughput constraints, or flush/commit conditions for visibility delays.
3. **Source partitions and parallelism:** check assignment and effective read concurrency. Adding partitions requires evaluation of external-system and ordering semantics.
4. **GC and heap configuration:** use GC logs, allocation rate, and the target JDK; do not choose a collector from latency alone.

### Key Configuration

| Option | Description | Example / applicability |
|--------|-------------|-------------------------|
| `taskmanager.memory.process.size` | TM process memory | Tune using the memory category, State Backend, buffers, and GC |
| `parallelism.default` | Default parallelism | Evaluate with partition assignment, operator capacity, resources, and load |

---

## Pattern 3: Checkpoint Issues

### Symptoms

- Checkpoint timeout (`CheckpointException: Checkpoint expired`).
- Checkpoint duration grows continuously.
- The Job restarts after consecutive Checkpoint failures.
- Checkpoint State size grows abnormally.

### Common Causes

1. **Large State:** one operator's State makes snapshots slow.
2. **Barrier alignment delay:** backpressure slows Barrier propagation.
3. **Disk I/O bottleneck:** disk I/O is insufficient for an incremental RocksDB Checkpoint.
4. **State compatibility issue:** State schema becomes incompatible after an SQL upgrade. Distinguish restore failure from failure of a running snapshot.
5. **Topology or exchange change:** a new network exchange or uneven load can affect Barrier propagation. Operator-chain splitting alone does not establish the cause.

### Verification

Required evidence: Checkpoint summary and individual details; failure reason/logs; State Backend, restore source, and configuration; and backpressure, I/O, and resources in the same time window.

- Slow Barrier arrival, slow input alignment, slow synchronous snapshotting, and slow asynchronous upload are different phases and should not all be addressed by increasing the timeout.
- Full State, incremental upload, and bytes written by the current snapshot have different semantics. A small upload does not prove that State is small.
- For restore failure, separately verify the Savepoint, State mapping, schema, and serializer compatibility; runtime snapshot-duration conclusions do not apply directly.

Validation objective: evaluate completion rate, duration, snapshot load, and recovery objectives together.

### Optimizations and Applicability

1. **Timeout and interval:** first rule out a persistent failure, then balance snapshot load, completion rate, and recovery objectives.
2. **Unaligned Checkpoints:** evaluate under backpressure and verify compatibility with exactly-once, the target version, other options, and added overhead.
3. **Incremental Checkpoints:** evaluate only when supported by the State Backend.
4. **State TTL:** bound State retention according to pattern 7; do not change result correctness merely to shorten snapshots.

### Key Configuration

| Option | Description | Example / applicability |
|--------|-------------|-------------------------|
| `execution.checkpointing.interval` | Checkpoint interval | For example `3 min`; balance snapshot load and recovery objectives |
| `execution.checkpointing.timeout` | Checkpoint timeout | For example `10 min`; do not hide a failure by increasing it |
| `execution.checkpointing.unaligned.enabled` | Unaligned Checkpoints | Evaluate under backpressure, checking support and added overhead |
| `state.backend.incremental` | Incremental Checkpoints | Evaluate `true` when the backend supports it |
| `execution.checkpointing.tolerable-failed-checkpoints` | Tolerable failures | Set from fault-tolerance objectives; this does not replace fixing failures |

---

## Pattern 4: OOM / Memory Issues

### Symptoms

- A TaskManager is killed. Exit codes such as 137/143 are only clues; use events or logs to distinguish OOM, cancellation, and other termination causes.
- `java.lang.OutOfMemoryError: Java heap space`.
- `java.lang.OutOfMemoryError: Direct buffer memory`.
- `Could not allocate managed memory`.
- TMs restart frequently.

### Common Causes

1. **Heap pressure:** excessive on-heap State, object allocation, caches, or MiniBatch buffering; identify the actual memory source.
2. **Managed Memory pressure:** insufficient managed-memory budget for operators or the State Backend; evaluate backend configuration and Metrics.
3. **Direct Memory pressure:** constrained or unreleased off-heap allocation from networking, Connectors, or other components.
4. **Data skew raises memory usage on one TM.**
5. **Oversized batch buffers:** if the target version supports `table.exec.mini-batch.segment-size`, inspect its actual value and effectiveness; do not assume one universal default.

### Verification

Required evidence: events, exceptions, and GC logs from the failed TM; Heap, Non-Heap, Direct, Managed, and process memory; effective configuration; State, caches, and Subtask distribution.

- Use exceptions and events from the failed process to distinguish JVM OOM, container limits, and other exits; an exit code is not the root cause.
- Locate pressure within Heap, Direct, Managed, and the total budget, and use GC to distinguish retained data, transient allocation, caches, and native memory.
- For an anomaly on one TM, also distinguish operator load, hot State, machine differences, and external calls. Current values from a replacement process do not explain an earlier failure.

Validation objective: after tuning, verify memory peak/stability, GC, throughput, and the total configured budget.

### Optimizations and Applicability

1. **Resource budget:** tune process memory and Managed/Off-Heap allocation for the constrained category without crowding out other categories.
2. **Batch buffers:** evaluate MiniBatch segment size when supported by the target version. Values below are examples only.
3. **Hot-key handling:** verify load according to pattern 8. Salting or staged computation must preserve merge, primary-key, and update semantics.
4. **State Backend:** a disk-backed backend can reduce some on-heap State but still consumes cache and Managed/Native memory. Check restore compatibility before switching.

### Key Configuration

| Option | Description | Example / applicability |
|--------|-------------|-------------------------|
| `taskmanager.memory.process.size` | Total TM process memory | For example `4096m`; evaluate against actual category and load |
| `taskmanager.memory.managed.fraction` | Managed Memory fraction | `0.4` |
| `table.exec.mini-batch.segment-size` | MiniBatch segment size | For example `256mb`; evaluate only when supported by the target version |
| `taskmanager.memory.task.off-heap.size` | Task Off-Heap memory | `256m` |

---

## Pattern 5: Watermark Issues

### Symptoms

- A window does not fire and produces no output.
- A Watermark is `-9223372036854775808` (`Long.MIN_VALUE`).
- The Watermark of some Subtasks lags far behind.
- Data is marked late and dropped.

### Common Causes

1. **No data on one Source partition:** if that input still participates in Watermark computation, it may hold back the downstream Watermark.
2. **Idle input is not detected:** the downstream operator still waits for a Watermark from an empty input.
3. **Out-of-order or late data:** event time is behind the Watermark; whether data is discarded depends on operator and late-data semantics.
4. **Time-zone issue:** event time was parsed with the wrong time zone.
5. **Uneven progress among inputs:** Watermarks from Sources differ significantly. When alignment is enabled, also inspect its waiting behavior.

### Verification

Required evidence: Watermarks for Source/downstream operators; Subtask activity and input/output; event time, time zone, idle detection, window, and late-data configuration.

- Distinguish no input, valid idleness, input whose event time does not advance, and waiting for the slower side of a multi-input operator.
- Verify event-time generation, time zone, out-of-order allowance, and idle detection. Increasing out-of-order tolerance also increases waiting.
- If output remains invisible after a window fires, distinguish batch flush and Sink commit; do not attribute a later-stage issue to Watermarks.

Validation objective: when changing idle detection or out-of-order tolerance, verify correctness for reactivated inputs and late data.

### Optimizations and Applicability

1. **Source idle detection:** set an appropriate idle timeout and evaluate late-data risk when an input becomes active again.
2. **Out-of-order tolerance:** balance correctness and waiting using the observed distribution, for example `WATERMARK FOR event_time AS event_time - INTERVAL '30' SECOND`.
3. **Partitioning and time zone:** inspect assignment, activity, and time parsing. Not every partition must produce continuously.

### Key Configuration

| Option | Description | Example / applicability |
|--------|-------------|-------------------------|
| `table.exec.source.idle-timeout` | Source idle timeout | `5s` |
| `table.local-time-zone` | Local time zone | `Asia/Shanghai` |
| `pipeline.auto-watermark-interval` | Watermark emission interval | `200ms` |

---

## Pattern 6: MiniBatch Behavior and Compatibility

### Symptoms

- Window results are incorrect after MiniBatch is enabled.
- Computation errors appear when an EventTime Window and MiniBatch are enabled together.
- `INSERT INTO ... SELECT ...` produces no output after MiniBatch is enabled.
- Results are unexpected after enabling `table.optimizer.distinct-agg.split.enabled`.

### Common Causes

1. **Changed buffering and trigger timing:** inspect the actual Plan to determine whether MiniBatch is active and when the window fires; do not automatically classify the combination as a conflict.
2. **Different Changelog behavior:** within-batch merging can reduce intermediate updates. Distinguish an expected optimization from an incorrect final result.
3. **Version-specific or execution-path issue:** verify the version, Distinct-splitting Plan, and data conditions; concurrent enablement alone does not prove a bug.

### Verification

Required evidence: effective MiniBatch/Distinct-split configuration; actual Plan; version; input/output or Changelog; Watermarks and window triggers; and available sample inputs and results.

- Options must be effective in the target version and actual Plan. Enabling optimizations together is not proof of a conflict.
- Distinguish batch/time-trigger latency, intermediate Changelog merging, and incorrect final results using primary keys and input/output examples.
- For Distinct splitting, inspect aggregation phases. A ProcessingTime Window is not an equivalent substitute for an EventTime Window.

Validation objective: comparisons must cover both final results and performance.

### Optimizations and Applicability

1. **Controlled comparison:** after obtaining relevant evidence and authorization, compare final results, throughput, and latency with MiniBatch disabled and enabled.
2. **Optimization combinations:** inspect support conditions and the actual Plan for windows, Changelog, and Distinct splitting; do not universally require disabling optimizations.
3. **Version selection:** evaluate a version containing a relevant fix only when official information and observed trigger conditions match, then verify restore compatibility.

### Key Configuration

| Option | Description | Notes |
|--------|-------------|-------|
| `table.exec.mini-batch.enabled` | MiniBatch switch | Verify against the target version and Plan; do not always disable it |
| `table.exec.mini-batch.allow-latency` | MiniBatch latency | Avoid excessive values |
| `table.optimizer.distinct-agg.split.enabled` | Distinct Agg splitting | Verify the version, aggregation type, and actual split Plan |

---

## Pattern 7: State TTL Issues

### Symptoms

- TopN results contain duplicates or omissions.
- A GroupAggregate COUNT suddenly decreases.
- ChangelogNormalize emits duplicate INSERT records.
- Records expected to be UPDATEs become INSERTs.

### Common Causes

1. **TTL too short:** State expires before it is no longer needed.
2. **State lacks a cleanup boundary:** State may grow with keys or history and create memory, disk, or snapshot pressure. An absent TTL does not necessarily mean unbounded growth.
3. **TTL conflicts with business semantics:** for example, daily aggregation with a one-hour TTL.
4. **Incorrect ChangelogNormalize TTL:** primary-key State is lost, producing duplicate INSERTs.

### Verification

Required evidence: SQL/primary keys and State-access semantics; effective TTL; State and Checkpoint history; input update/late-data span; and unexpected output examples.

- The required State-retention range depends on later access, lateness, and update conditions, not merely a calendar day or week. Verify whether global and operator-level TTLs are effective.
- Align unexpected output with input intervals to test whether State had expired when needed. Growth can also come from key cardinality, Join relationships, or delayed cleanup.
- Verify TopN rankings, aggregate accumulation, ChangelogNormalize primary-key updates, and stream-stream Join matches separately; smaller State alone is not sufficient.

Validation objective: cover late input, long-interval updates, and results after recovery, rather than only measuring smaller State.

### Optimizations and Applicability

1. **Set TTL:** derive it from required update, late-data, and backfill spans. For example, `SET 'table.exec.state.ttl' = '36h';` is illustrative, not a default.
2. **Operator-level TTL:** when supported by the target version, use the documented SQL Hint or configuration for each operator and verify it in the Plan.
3. **Correctness boundaries:** retain ranking and update relationships for TopN, primary-key State required by later updates for ChangelogNormalize, and a business-defined correlation range for stream-stream Joins. Do not substitute an arbitrary TTL.

### Key Configuration

| Option | Description | Example / applicability |
|--------|-------------|-------------------------|
| `table.exec.state.ttl` | State expiration | Derive from business semantics |

---

## Pattern 8: Data Skew

### Symptoms

- One Subtask's `busyTimeMsPerSecond` approaches 1,000 while other Subtasks remain low.
- Subtask Metrics are highly uneven; for example, aggregate `max` is much greater than `avg`, requiring identification of the concrete instance.
- Some Subtasks process much more slowly than others.
- Overall throughput is far below theoretical capacity.

### Common Causes

1. **Uneven key distribution:** some keys carry far more data than others, such as popular products or large customers.
2. **Concentrated NULLs:** all NULL keys route to one Subtask.
3. **Poor GroupBy key:** a low-cardinality grouping key is used.
4. **Uneven Join-key distribution:** keys are skewed in a large-table Join.
5. **Uneven Source partitions:** Kafka partitions carry materially different volumes.

### Verification

Required evidence: topology and partition keys; per-Subtask input/output, busy time, State, and resources; Source partition assignment; and TM mapping.

- Uneven input and equal input with slower processing are different problems. For the latter, inspect the TM, external calls, and State access.
- Distinguish Source partition skew, hot keys, and many-to-many Join output amplification. Low cardinality or concentrated NULLs require actual distribution evidence.
- Aggregates only reveal differences; locate the cause in a concrete Subtask and key/partition. Higher parallelism does not automatically split one hot key.

Validation objective: compare distribution improvement, total throughput, network/State cost, and result consistency.

### Optimizations and Applicability

1. **Two-phase aggregation:** when applicable, let the optimizer create local/global aggregation. Manual salting is a separate rewrite whose merge semantics must be verified.
2. **NULL and hot keys:** filter NULL only when the business does not require it. For salting, check Join replication cost, primary keys, and update semantics.
3. **Parallelism and partitions:** evaluate load distribution across different keys. For uneven sources, inspect partition assignment or the producer strategy.

### Key Configuration

| Option | Description | Example / applicability |
|--------|-------------|-------------------------|
| `table.optimizer.agg-phase-strategy` | Aggregation-phase strategy | `TWO_PHASE` |
| `table.exec.mini-batch.enabled` | MiniBatch (with two-phase aggregation) | `true` |
