# Flink SQL Performance Diagnosis

Read when the [diagnosis entry point](README.md) leads to diagnosis of a common performance issue. Locate the issue from basic information, operator Metrics, and decision branches. See [job-observability.md](job-observability.md) for all CLI syntax and invocation guidance.

## Prerequisites

Identify the region, Workspace, Namespace, Deployment, and Job corresponding to the affected period from the job URL or existing context. Reuse configuration, topology, and runtime evidence already collected through the entry flow.

## Diagnosis Flow

### Step 1: Collect Basic Information

#### 1.1 Get Deployment Configuration

Query according to [Deployment Configuration and Runtime Instances](job-observability.md#deployment-configuration-and-runtime-instances), focusing on:

- Engine version: `engineVersion`.
- Flink configuration: `flinkConf`, especially:
  - `table.exec.mini-batch.enabled`, `table.exec.mini-batch.allow-latency`, and `table.exec.mini-batch.size`.
  - `table.exec.state.ttl`.
  - `execution.checkpointing.interval` and `execution.checkpointing.timeout`.
  - `taskmanager.memory.process.size`.
  - `parallelism.default`.
  - `table.optimizer.agg-phase-strategy`.
  - `table.exec.source.idle-timeout`.
- Resource configuration: parallelism, TM memory, and CPU.
- Job runtime and state, confirming that the configuration belongs to the affected instance.

#### 1.2 Get the Operator Topology

Query according to [Runtime Topology and Plan](job-observability.md#runtime-topology-and-plan), extracting:

- Vertex ID, name, parallelism, and state.
- Sources, intermediate operators such as Agg/Join/Window, and Sinks.
- Input edges and operator chains, establishing the mapping between later Metrics and the data flow.

#### 1.3 Inspect the Checkpoint Summary

Query according to [Checkpoint Summary](job-observability.md#checkpoint-summary), focusing on:

- Whether Checkpoints complete normally.
- Duration and State size of recent Checkpoints.
- Failures or timeouts, and whether the evidence covers the incident period.

#### 1.4 Inspect Exceptions

Query according to [Exceptions](job-observability.md#exceptions), focusing on:

- OOMs, Checkpoint timeouts, and data-format errors.
- Exception time, owning task, and key stack frames.
- Required runtime-log context, distinguishing the first exception from later failure propagation.

### Step 2: Collect Operator-Level Metrics

Follow [Vertex Metrics](job-observability.md#vertex-metrics) to query performance Metrics for relevant operators identified in step 1.2.

Focus on busy time, backpressure, idle time, and input/output rates. Example Metric IDs:

- `busyTimeMsPerSecond`
- `backPressuredTimeMsPerSecond`
- `idleTimeMsPerSecond`
- `numRecordsInPerSecond`
- `numRecordsOutPerSecond`

Select IDs from actual enumeration for the target, and associate each value with its Vertex, Subtask, and sample time. To analyze persistence over time, use [Historical Metrics](job-observability.md#specified-historical-time-and-time-range) instead of treating a current snapshot as historical evidence.

### Step 3: Diagnose with the Decision Tree

#### A. Locate the Bottleneck Operator

High busy time is evidence of a candidate bottleneck. For example, when `busyTimeMsPerSecond > 900`, verify whether processing capacity is constrained by combining throughput, backpressure, and Subtask distribution.

**A.1 Source operators**

- Check Source parallelism, upstream partition count, and actual assignment to determine effective read concurrency.
- Follow [Subtask Metrics](job-observability.md#subtask-metrics) to inspect the distribution of Source output rates.
- When some Subtasks emit no data, determine whether the partition count is below parallelism, the upstream source is empty, or downstream backpressure is responsible.
- For uneven partition load, consult pattern 8 in the [knowledge base](sql-perf-knowledge.md).

**A.2 Agg/Join operators**

- Query each Subtask's input rate and busy time, then compare their load.
- If an aggregate such as `max` is much greater than `avg`, locate the specific Subtask and its input distribution, then verify skew with knowledge-base pattern 8.
- If Subtasks are uniformly busy, determine whether MiniBatch and two-phase aggregation apply and are active; see pattern 1.
- Evaluate bottleneck parallelism against actual resources. For a Join, also consider match cardinality and output volume; do not apply aggregation optimizations directly.

**A.3 Sink operators**

- Check the downstream Sink system's write capacity, throttling, and retries.
- Verify batch size, flush, and commit settings, distinguishing slow writes from externally visible latency.
- See knowledge-base pattern 2.

#### B. Trace Backpressure

For example, when `backPressuredTimeMsPerSecond > 500`, query [Backpressure Details](job-observability.md#backpressure-details).

1. Verify the sample state, time, and aggregate and Subtask-level values.
2. Trace downstream from the affected node and compare busy time, backpressure, and throughput.
3. Treat a node with high busy time and low backpressure as a candidate blocking stage, then validate the cause against multi-input relationships, Subtask distribution, and TM resources.
4. Consult knowledge-base pattern 1.

#### C. Checkpoint Issues

When step 1.3 finds failures or timeouts:

1. Query the applicable record through [Checkpoint Details](job-observability.md#checkpoint-details).
2. Compare operator duration and State size to locate concentrations.
3. Distinguish Barrier arrival, alignment, synchronous snapshotting, and asynchronous upload, then evaluate them with backpressure and storage conditions.
4. Consult knowledge-base pattern 3.

#### D. Memory Issues

When step 1.4 finds an OOM or a terminated TM:

1. Verify the TM memory configuration from step 1.1.
2. Use [TaskManager and Subtask Mapping](job-observability.md#taskmanager-and-subtask-mapping) to identify the target process.
3. Query [TaskManager Metrics](job-observability.md#taskmanager-metrics), focusing on heap usage and limit, Direct, Managed, and process memory.
4. Determine the memory category from exceptions and logs. If the failed TM has exited, use matching historical evidence; do not infer the previous failure from current values on a replacement process.
5. Consult knowledge-base pattern 4.

#### E. Watermark Issues

When the Job emits no output or a window does not fire:

1. Query [Watermarks](job-observability.md#watermarks) for Sources and window operators and compare inputs and Subtasks.
2. `-9223372036854775808` (`Long.MIN_VALUE`) means that the Watermark is uninitialized; combine it with input evidence to determine why.
3. Check `table.exec.source.idle-timeout`, event time, and window trigger conditions.
4. Consult knowledge-base pattern 5.

#### F. No-Output Issues

When the Job is running but does not produce expected output:

1. Check whether MiniBatch is active and whether its interaction with windows and Changelog matches expectations; see knowledge-base pattern 6. A configuration combination alone does not prove a conflict.
2. Check whether State TTL is too short and affects later computation; see pattern 7.
3. Check whether Watermarks advance; see pattern 5.
4. Check whether window trigger and Sink flush/commit conditions are satisfied.

## Quick Diagnosis Map

| User description | Steps |
|------------------|-------|
| Job latency keeps increasing | 1.1, 1.2 → Step 2 → A/B |
| Checkpoint timeout | 1.1, 1.3 → C |
| TM killed / OOM | 1.1, 1.4 → D |
| Window produces no output | 1.1, 1.2 → E/F |
| Inaccurate data | 1.1 → F, verifying TTL and MiniBatch |
