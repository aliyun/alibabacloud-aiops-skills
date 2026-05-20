# Spark Application Data Skew and Performance Diagnosis

Quantitative analysis of data skew, straggler tasks, shuffle spill, and small file problems using Spark Event Log metrics.

---

## 1. Overview

This document provides a **quantitative diagnosis** workflow for the following Spark performance problems:

- **Data Skew** — uneven data distribution across partitions causing a few tasks to become bottlenecks
- **Straggler Tasks** — a small number of tasks that take disproportionately long to complete
- **Shuffle Spill** — excessive memory pressure causing intermediate data to be spilled to disk
- **Small File Problems** — writing or reading an excessive number of small files, degrading performance

### Relationship to Other Diagnosis Documents

| Document | Role | When to Use |
|----------|------|-------------|
| [spark-app-tail-log-diagnosis.md](spark-app-tail-log-diagnosis.md) | **Qualitative triage** — identifies error patterns from tail logs | First step for any failed or slow application |
| [spark-app-oss-full-log-analysis.md](spark-app-oss-full-log-analysis.md) | **Full log retrieval** — reads complete driver/executor logs from OSS | When tail log is insufficient for diagnosis |
| **This document** | **Quantitative analysis** — measures skew, spill, and straggler metrics from Event Log | When tail log suggests data skew, long tail tasks, or shuffle spill (see disambiguation in [spark-app-tail-log-diagnosis.md](spark-app-tail-log-diagnosis.md) Section 5.2) |

### Prerequisites

- **OSS read access**: You need `oss:ListObjects` and `oss:GetObject` permissions to read the Event Log from OSS. See [ram-policies.md](ram-policies.md) for required permission configuration.
- **Completed application**: Event logs are only available after the application has completed (or failed). Running applications do not have complete event logs.
- **Python 3.8+**: The analysis script requires Python 3.8 or later.

---

## 2. Workflow

```
1. Obtain Event Log path via GetSparkAppInfo
2. Download and analyze Event Log using event_log_analyzer.py
3. Interpret analysis results (summary, skewed stages, abnormal tasks, spill, small file risk)
4. Diagnose root cause and recommend actions using decision trees (Section 4)
```

### 2.1 Step 1 — Obtain Event Log Path

Use `GetSparkAppInfo` to retrieve the `LogRootPath` and `LastAttemptId` for the target application. These two fields are required to construct the Event Log file path.

```bash
aliyun adb get-spark-app-info \
  --api-version 2021-12-01 \
  --app-id s202401011200xx1234ab000**** \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --region cn-beijing \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper
```

> **Note**: `--region` is **required**.

From the response, extract:

| Field | Description |
|-------|-------------|
| `Data.Detail.LogRootPath` | OSS root path for the cluster's Spark logs (includes bucket and cluster-id) |
| `Data.Detail.LastAttemptId` | Log directory name for this application attempt (not the same as AppId) |

**Event Log path format**:

```
{LogRootPath}/{LastAttemptId}/{LastAttemptId}.0
```

**Example**:

- `Data.Detail.LogRootPath` = `oss://adb-spark-logs-cn-beijing/spark-logs/amv-bp1xxxxxxxxx****`
- `Data.Detail.LastAttemptId` = `s202401011200xx1234ab000****-0001`

Event Log path:

```
oss://adb-spark-logs-cn-beijing/spark-logs/amv-bp1xxxxxxxxx****/s202401011200xx1234ab000****-0001/s202401011200xx1234ab000****-0001.0
```

The `.0` file is a JSON lines file containing Spark events (SparkListenerLogStart, SparkListenerStageSubmitted, SparkListenerTaskEnd, etc.), with one JSON object per line.

### 2.2 Step 2 — Download and Analyze Event Log

Pipe the Event Log from OSS into the analysis script:

```bash
aliyun ossutil cat oss://<bucket>/spark-logs/<cluster-id>/<attempt-id>/<attempt-id>.0 \
  -e oss-<region>.aliyuncs.com \
  | python3 scripts/event_log_analyzer.py --output-format text
```

**Parameter explanation**:

| Parameter | Description |
|-----------|-------------|
| `aliyun ossutil cat <path>` | Reads the Event Log file content from OSS |
| `-e oss-<region>.aliyuncs.com` | **Required** — OSS endpoint for the bucket's region. Omitting this may cause `403 AccessDenied` errors. Example: `-e oss-cn-beijing.aliyuncs.com` |
| `python3 scripts/event_log_analyzer.py` | Analyzes the Event Log and outputs structured metrics |
| `--output-format text` | Output format: `text` (human-readable) or `json` (machine-readable) |

**Alternative: download to local disk first** (recommended for large Event Logs):

```bash
# Download the Event Log to local disk
aliyun ossutil cp oss://<bucket>/spark-logs/<cluster-id>/<attempt-id>/<attempt-id>.0 \
  /tmp/<attempt-id>.0 \
  -e oss-<region>.aliyuncs.com

# Analyze locally
cat /tmp/<attempt-id>.0 | python3 scripts/event_log_analyzer.py --output-format text
```

### 2.3 Step 3 — Interpret Analysis Results

The script outputs a structured report with the following sections:

#### 2.3.1 Summary

```text
=== Summary ===
Total Stages: 12
Total Tasks:  2400
Skewed Stages: 2
Abnormal Tasks: 15
Spill Stages: 1
Small File Risk: No
```

| Field | Description |
|-------|-------------|
| Total Stages | Number of stages in the application |
| Total Tasks | Total number of tasks across all stages |
| Skewed Stages | Number of stages with data skew detected (see Section 3.1) |
| Abnormal Tasks | Number of tasks with abnormal duration or shuffle read (see Section 3.2) |
| Spill Stages | Number of stages with disk spill detected (see Section 3.3) |
| Small File Risk | Whether small file risk is detected (see Section 3.4) |

#### 2.3.2 Stage Metrics

For each stage, the script reports:

```text
=== Stage Metrics ===
Stage 3 (join at MyJob.scala:45):
  Tasks: 200 | Duration: median=12s, max=340s | Duration Skew Ratio: 28.3
  Shuffle Read: median=5MB, max=512MB | Shuffle Read Skew Ratio: 102.4
  Shuffle Write: total=1.2GB
  Disk Spill: 256MB
  GC Time: median=0.5s, max=45s
  Skewed: YES (Severe)
```

| Metric | Description |
|--------|-------------|
| Tasks | Number of tasks in the stage |
| Duration (median / max) | Task duration statistics |
| Duration Skew Ratio | `max / median` — values above threshold indicate duration skew |
| Shuffle Read (median / max) | Shuffle read bytes per task |
| Shuffle Read Skew Ratio | `max / median` — values above threshold indicate data skew |
| Shuffle Write (total) | Total shuffle write bytes for the stage |
| Disk Spill | Total disk spill bytes for the stage |
| GC Time (median / max) | JVM garbage collection time per task |

#### 2.3.3 Skewed Stages

Stages where the shuffle read skew ratio or duration skew ratio exceeds the defined thresholds (Section 3.1):

```text
=== Skewed Stages ===
Stage 3: Severe skew — shuffle_read_skew_ratio=102.4 (max=512MB, median=5MB)
Stage 7: Moderate skew — duration_skew_ratio=6.2 (max=78s, median=12.6s)
```

#### 2.3.4 Abnormal Tasks

Individual tasks that deviate significantly from the stage median:

```text
=== Abnormal Tasks ===
Stage 3, Task 42: duration=340s (median=12s, 28.3x), shuffle_read=512MB (median=5MB, 102.4x), gc_time=45s
Stage 3, Task 87: duration=180s (median=12s, 15.0x), shuffle_read=256MB (median=5MB, 51.2x), gc_time=22s
```

#### 2.3.5 Spill Stages

Stages with non-zero disk spill:

```text
=== Spill Stages ===
Stage 3: disk_spill=256MB (Critical)
```

#### 2.3.6 Small File Risk

Detection of potential small file problems:

```text
=== Small File Risk ===
Stage 11 (write at MyJob.scala:120): numTasks=500, avg_output=2MB — RISK DETECTED
```

### 2.4 Step 4 — Diagnose Root Cause and Recommend Actions

Based on the analysis results, follow the appropriate decision tree in Section 4 to diagnose the root cause and determine recommended actions. Use the thresholds in Section 3 to classify severity, then consult the decision trees and the Recommended Actions Reference Table (Section 5) for specific configuration changes or code modifications.

### Quick Reference: Quantitative Thresholds

| Metric | Threshold | Severity | Description |
|--------|-----------|----------|-------------|
| Shuffle Read Skew Ratio (max/median) | > 10 AND max > 100 MB | Severe | Single partition > 10× median shuffle data and exceeds 100 MB; typically causes OOM or extreme task duration |
| Shuffle Read Skew Ratio (max/median) | > 5 | Moderate | Noticeable data imbalance; performance degradation likely but may not cause failures |
| Duration Skew Ratio (max/median) | > 10 AND max duration > 5 min | Severe | One task > 10× median duration and exceeds 5 minutes; critical bottleneck |
| Duration Skew Ratio (max/median) | > 5 | Moderate | Some tasks noticeably slower than median, but gap not extreme |
| Task Duration | > median × 5 | Abnormal | Individual task takes > 5× the stage median duration |
| Task Shuffle Read Bytes | > median × 5 | Abnormal | Individual task reads > 5× the stage median shuffle bytes |
| Task GC Time | > median × 10 | Abnormal | Individual task GC > 10× median, indicating memory pressure |
| Disk Spill | > 1 GB | Critical | Severe memory pressure; may cause disk-full errors; immediate action required |
| Disk Spill | > 100 MB | Warning | Moderate memory pressure; impacts performance but may not cause failures |
| Disk Spill | > 0 | Info | Minor spill detected; monitor but may not need immediate action |
| Small File Risk | numTasks > 100 AND avg output < 10 MB | Risk | Many tasks each producing small output; degrades downstream read performance |

For detailed analysis logic and remediation steps, see sections below.

---

## 3. Quantitative Thresholds and Definitions

### 3.1 Data Skew Thresholds

| Metric | Skew Level | Threshold | Description |
|--------|------------|-----------|-------------|
| Shuffle Read Skew Ratio (max / median) | Severe | > 10 AND max > 100 MB | A single partition contains more than 10× the median shuffle data and exceeds 100 MB. This typically causes OOM or extremely long task durations. |
| Shuffle Read Skew Ratio (max / median) | Moderate | > 5 | Data distribution is noticeably uneven but not catastrophic. Performance degradation is likely but may not cause failures. |
| Duration Skew Ratio (max / median) | Severe | > 10 AND max duration > 5 min | One task takes more than 10× the median duration and exceeds 5 minutes. Indicates a critical bottleneck. |
| Duration Skew Ratio (max / median) | Moderate | > 5 | Some tasks are noticeably slower than the median, but the gap is not extreme. |

> **Fallback calculation**: When the median shuffle read is 0 (e.g., most tasks have no shuffle read), the skew ratio uses `max / (mean + 1)` instead of `max / median` to avoid division by zero.

### 3.2 Abnormal Task Thresholds

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Task Duration | > median × 5 | A task takes more than 5× the median duration of all tasks in the same stage. |
| Task Shuffle Read Bytes | > median × 5 | A task reads more than 5× the median shuffle bytes of all tasks in the same stage. |
| Task GC Time | > median × 10 | A task spends more than 10× the median GC time, indicating memory pressure. |

A task is flagged as **abnormal** if it exceeds **any** of the above thresholds.

### 3.3 Shuffle Spill Severity

| Level | Threshold | Description |
|-------|-----------|-------------|
| Critical | Disk Spill > 1 GB | Severe memory pressure. Spilling this much data to disk causes significant I/O overhead and may lead to disk-full errors. Immediate action required. |
| Warning | Disk Spill > 100 MB | Moderate memory pressure. Spill impacts performance but may not cause failures. Tune at next opportunity. |
| Info | Disk Spill > 0 | Minor spill detected. May not need immediate action but should be monitored. |

### 3.4 Small File Risk

| Condition | Threshold | Description |
|-----------|-----------|-------------|
| Small File Risk | numTasks > 100 AND avg output < 10 MB | A stage with many tasks each producing a small amount of output. This is especially relevant for write stages — it indicates that the output will consist of many small files, degrading downstream read performance. |

---

## 4. Diagnosis Decision Tree

Use the following decision trees to determine the root cause and recommended actions based on the analysis results from Section 2.

### 4.1 Data Skew Decision Tree

```
Skew detected (shuffle_read_skew_ratio > threshold)?
├── YES: Severe skew (ratio > 10 AND max > 100MB)
│   ├── Is this a JOIN stage?
│   │   ├── One side is small (< autoBroadcastJoinThreshold) → Broadcast Join
│   │   │   └── Set spark.sql.autoBroadcastJoinThreshold=10485760 (10MB)
│   │   └── Both sides are large → Salting (random prefix on skew key)
│   │       └── Add random prefix: withColumn("salt", concat(col("key"), lit("_"), (rand()*N).cast("int")))
│   ├── Is this a GROUP BY / aggregation stage?
│   │   └── Two-phase aggregation (partial agg with salted key, then final agg on original key)
│   └── General case
│       ├── Enable AQE (spark.sql.adaptive.enabled=true)
│       ├── Increase spark.sql.shuffle.partitions
│       └── Manual repartition before the skewed operation
├── YES: Moderate skew (ratio > 5)
│   ├── Check if AQE is enabled
│   │   ├── Not enabled → Enable AQE first (spark.sql.adaptive.enabled=true)
│   │   └── Enabled but not helping → Increase spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes
│   └── Increase spark.sql.shuffle.partitions
└── NO: Not a skew issue → check other causes (straggler, spill, small files)
```

### 4.2 Straggler Task Decision Tree

```
Abnormal task detected (duration > median × N, no obvious data skew)?
├── Check GC Time
│   ├── GC time > 30% of task duration → Memory pressure
│   │   ├── Increase spark.executor.memory
│   │   └── Tune GC: -XX:+UseG1GC -XX:InitiatingHeapOccupancyPercent=35
│   │       (via spark.executor.extraJavaOptions)
│   └── GC time normal → Not memory-related
├── Check Shuffle Spill
│   ├── Spill detected → See Spill Decision Tree (4.3)
│   └── No spill → Resource contention or data locality issue
├── Enable speculation
│   └── spark.speculation=true, spark.speculation.multiplier=1.5
└── Check executor node resource utilization
    └── Other processes competing for CPU, memory, or disk I/O on the same node
```

### 4.3 Shuffle Spill Decision Tree

```
Disk spill detected?
├── Critical (> 1GB)
│   ├── Increase spark.executor.memory
│   ├── Increase spark.sql.shuffle.partitions (reduce per-partition data)
│   └── Check for data skew (skew concentrates data in few partitions)
│       └── If skew detected → See Data Skew Decision Tree (4.1)
├── Warning (> 100MB)
│   ├── Increase spark.sql.shuffle.partitions
│   └── Enable compression: spark.shuffle.compress=true
└── Info (> 0)
    └── Monitor — may not need immediate action
```

### 4.4 Small File Decision Tree

```
Small file risk detected (avg output < 10MB, numTasks > 100)?
├── Writing stage
│   ├── Use .coalesce(N) before write to reduce output files
│   │   └── df.coalesce(100).write.parquet(path)
│   ├── Use .repartition(N) if data distribution matters
│   │   └── df.repartition(100).write.parquet(path)
│   └── Enable AQE coalesce: spark.sql.adaptive.coalescePartitions.enabled=true
└── Reading stage (small input files)
    ├── Increase spark.sql.files.maxPartitionBytes (default 128MB)
    └── Pre-process input data by compacting small files into larger ones
```

---

## 5. Recommended Actions Reference Table

| Scenario | Action | Configuration / Code | Notes |
|----------|--------|---------------------|-------|
| Data Skew — Join (small table) | Broadcast Join | `spark.sql.autoBroadcastJoinThreshold=10485760` (10MB) | Only when one side fits in memory |
| Data Skew — Join (large tables) | Salting | `withColumn("salt", concat(col("key"), lit("_"), (rand()*N).cast("int")))` | Requires two-pass join and union |
| Data Skew — GroupBy | Two-phase Aggregation | First partial agg with salted key, then final agg on original key | Reduces per-partition load |
| Data Skew — General | Enable AQE | `spark.sql.adaptive.enabled=true` | Spark 3.0+ only |
| Data Skew — AQE Tuning | Adjust skew threshold | `spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes=256m` | Default 256MB |
| Data Skew — General | Increase partitions | `spark.sql.shuffle.partitions=2000` | More partitions = smaller per-partition data |
| Straggler — GC pressure | Tune GC | `-XX:+UseG1GC -XX:InitiatingHeapOccupancyPercent=35` | Via `spark.executor.extraJavaOptions` |
| Straggler — General | Enable speculation | `spark.speculation=true` | Re-launches slow tasks on other executors |
| Straggler — Speculation tuning | Adjust multiplier | `spark.speculation.multiplier=1.5` | Task is straggler if duration > multiplier × median |
| Shuffle Spill — Critical | Increase memory | `spark.executor.memory=8g` | Reduce spill to disk |
| Shuffle Spill — Warning | More partitions | `spark.sql.shuffle.partitions=2000` | Smaller per-partition data |
| Shuffle Spill — General | Enable compression | `spark.shuffle.compress=true` | Default is true; use `spark.io.compression.codec=lz4` for speed |
| Small Files — Write | Coalesce | `df.coalesce(100).write.parquet(path)` | Reduces output file count |
| Small Files — Write | Repartition | `df.repartition(100).write.parquet(path)` | Use when data distribution matters (coalesce does not shuffle) |
| Small Files — AQE | Auto coalesce | `spark.sql.adaptive.coalescePartitions.enabled=true` | Spark 3.0+ |
| Small Files — Read | Increase partition bytes | `spark.sql.files.maxPartitionBytes=256m` | Allows multiple small files per task |

For detailed error descriptions and additional context, refer to the relevant sections in [spark-app-common-errors.md](spark-app-common-errors.md):
- **Data Skew** — Section 2
- **Shuffle Spill / Disk Overflow** — Section 8.2
- **Small Files (Write)** — Section 9.1
- **Small Files (Read)** — Section 9.2
- **Straggler Tasks** — Section 12

---

## 6. Important Notes

- **Event Log availability**: Event logs are only available after the application completes (or fails). Running applications do not have complete event logs.
- **Log retention**: OSS logs follow a 30-day retention policy. After 30 days, the event log file will be deleted. If the Event Log path returns `NoSuchKey`, the logs may have expired.
- **Large event logs**: For applications with many stages and tasks, the event log can be hundreds of MB. Streaming large files via `ossutil cat` may be slow or unstable. For very large logs, consider downloading to local disk first (see Step 2.2 alternative method).
- **AQE compatibility**: AQE (Adaptive Query Execution) recommendations only apply to Spark 3.0 and later versions. ADB Spark runs Spark 3.x by default, but verify the Spark version if AQE features are not working as expected.
- **Threshold calibration**: The default thresholds (skew ratio > 5, duration > median × 5) are starting points. For workloads with naturally variable task sizes, you may need to increase these thresholds to reduce false positives. Conversely, for latency-sensitive workloads, lower thresholds may be appropriate.
- **Median = 0 handling**: When the median value is 0 (e.g., most tasks have no shuffle read), the skew ratio calculation uses `max / (mean + 1)` as a fallback to avoid division by zero.
- **Read-only access**: This Skill only supports `oss:ListObjects` and `oss:GetObject`. It **MUST NOT** delete, modify, or overwrite any files on OSS. See the high-risk operation safety constraints in [SKILL.md](../SKILL.md).
