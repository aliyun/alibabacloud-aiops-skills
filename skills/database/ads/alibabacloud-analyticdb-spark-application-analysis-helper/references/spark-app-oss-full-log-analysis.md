# Spark Application OSS Full Log Deep Analysis

When tail logs retrieved via `GetSparkAppLog` are insufficient to diagnose a failure, pull the complete logs from OSS for in-depth analysis.

---

## 1. Overview

The `GetSparkAppLog` API returns at most 500 lines of the application's tail log. For complex issues—such as executor failures, data skew, or errors that occurred early in execution—the tail log may not contain enough context. In these cases, you can retrieve the **complete log files** stored in OSS, including both driver and executor logs.

---

## 2. Prerequisites

### 2.1 Obtain ApplicationLogPath

Before accessing OSS logs, use `GetSparkAppInfo` to retrieve the `LogRootPath` for the application:

```bash
aliyun adb get-spark-app-info \
  --api-version 2021-12-01 \
  --region cn-beijing \
  --app-id s202401011200xx1234ab000**** \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper
```

The response includes:
- `Data.Detail.LogRootPath` — the OSS root path (includes bucket and cluster-id)
- `Data.Detail.LastAttemptId` — the log directory name (note: this is **not** the same as AppId)

**ApplicationLogPath format**:

```
oss://<bucket>/spark-logs/<cluster-id>/<last-attempt-id>/
```

Example:
 - `Data.Detail.LogRootPath` is `oss://adb-spark-logs-cn-beijing/spark-logs/amv-bp1xxxxxxxxx****`
 - `Data.Detail.LastAttemptId` is `s202401011200xx1234ab000****-0001`

Complete log path:
```
oss://adb-spark-logs-cn-beijing/spark-logs/amv-bp1xxxxxxxxx****/s202401011200xx1234ab000****-0001/
```

### 2.2 OSS Permissions

Accessing OSS logs requires the following RAM permissions:

| Action | Description |
|--------|-------------|
| `oss:ListObjects` | List files in the OSS bucket/directory |
| `oss:GetObject` | Read file content from OSS |

If you encounter `AccessDenied` errors, refer to [ram-policies.md](ram-policies.md) for the required permission configuration.

---

## 3. Log Directory Structure

Under `ApplicationLogPath`, the log files are organized as follows:

```
<LogRootPath>/<LastAttemptId>/
├── driver/
│   ├── stdout            # Driver standard output
│   └── stderr            # Driver standard error (most exceptions appear here)
├── 1/
│   ├── stdout            # Executor-1 standard output
│   └── stderr            # Executor-1 standard error (most exceptions appear here)
├── 2/
│   ├── stdout            # Executor-2 standard output
│   └── stderr            # Executor-2 standard error (most exceptions appear here)
├── <executor-id>/
│   ├── stdout
│   └── stderr
└── <LastAttemptId>.0     # event log (JSON lines format)
```

**Key directories**:

| Path | Content | When to Use |
|------|---------|-------------|
| `driver/stderr` | Driver exception stack traces, OOM errors, task failures | Primary source for most failure diagnoses |
| `driver/stdout` | Application print output, progress logs | Secondary; useful for debugging application logic |
| `<executor-id>/stderr` | Executor-level exceptions, shuffle errors, OOM | Essential for executor failure or data skew analysis |
| `<LastAttemptId>.0` | Spark event log (JSON lines format) | For detailed stage/task analysis via Spark UI |

---

## 4. Complete Operation Flow

```
1. GetSparkAppInfo → extract LogRootPath and LastAttemptId
2. aliyun ossutil ls → list log files under <LogRootPath>/<LastAttemptId>/ (with -e endpoint)
3. aliyun ossutil cat → read specific log files (with -e endpoint)
4. Analyze driver and executor logs to identify root cause
```

### 4.1 Step 1 — Get LogRootPath

```bash
aliyun adb get-spark-app-info \
  --api-version 2021-12-01 \
  --region cn-beijing \
  --app-id s202401011200xx1234ab000**** \
  --db-cluster-id amv-bp1xxxxxxxxx**** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper
```

Extract `Data.Detail.LogRootPath` and `Data.Detail.LastAttemptId` from the response. The full log directory path is `<LogRootPath>/<LastAttemptId>/`.

### 4.2 Step 2 — List Log Files

Use `aliyun ossutil ls` to enumerate all log files under the application's OSS prefix:

> **Important**: The `aliyun ossutil` command requires the `-e` (endpoint) parameter to specify the OSS endpoint for the bucket's region. Without it, the CLI may default to a different region's endpoint, resulting in a `403 AccessDenied` error. The endpoint format is `oss-<region>.aliyuncs.com` (e.g., `oss-cn-beijing.aliyuncs.com` for Beijing region).

```bash
aliyun ossutil ls oss://adb-spark-logs-cn-hangzhou/spark-logs/amv-bp1xxxxxxxxx****/s202401011200xx1234ab000****-0001/ -e oss-cn-hangzhou.aliyuncs.com
```

This returns a listing of all available log files, including driver and executor logs.

**Example output**:

```
2024-01-15 10:32:00  125640  oss://adb-spark-logs-cn-hangzhou/spark-logs/amv-bp1xxxxxxxxx****/s202401011200xx1234ab000****-0001/driver/stderr
2024-01-15 10:32:00   32768  oss://adb-spark-logs-cn-hangzhou/spark-logs/amv-bp1xxxxxxxxx****/s202401011200xx1234ab000****-0001/driver/stdout
2024-01-15 10:45:23   98304  oss://adb-spark-logs-cn-hangzhou/spark-logs/amv-bp1xxxxxxxxx****/s202401011200xx1234ab000****-0001/1/stderr
2024-01-15 10:45:23   16384  oss://adb-spark-logs-cn-hangzhou/spark-logs/amv-bp1xxxxxxxxx****/s202401011200xx1234ab000****-0001/1/stdout
```

### 4.3 Step 3 — Read Specific Log Files

Use `aliyun ossutil cat` to read the content of a specific log file:

```bash
# Read driver stderr (most common source of error information)
aliyun ossutil cat oss://adb-spark-logs-cn-hangzhou/spark-logs/amv-bp1xxxxxxxxx****/s202401011200xx1234ab000****-0001/driver/stderr -e oss-cn-hangzhou.aliyuncs.com

# Read executor stderr for a specific executor
aliyun ossutil cat oss://adb-spark-logs-cn-hangzhou/spark-logs/amv-bp1xxxxxxxxx****/s202401011200xx1234ab000****-0001/1/stderr -e oss-cn-hangzhou.aliyuncs.com

# Read driver stdout for application output
aliyun ossutil cat oss://adb-spark-logs-cn-hangzhou/spark-logs/amv-bp1xxxxxxxxx****/s202401011200xx1234ab000****-0001/driver/stdout -e oss-cn-hangzhou.aliyuncs.com
```

---

## 5. Analysis Techniques

### 5.1 Comparing Driver and Executor Logs

When diagnosing distributed failures, it is essential to correlate driver and executor logs:

| Symptom | Driver Log | Executor Log | Likely Root Cause |
|---------|-----------|-------------|-------------------|
| Task failed with OOM | `TaskSetManager: Lost task X.Y` | `OutOfMemoryError: Java heap space` | Executor memory insufficient for data partition |
| Executor lost | `ExecutorLostFailure` | Process crashed or killed | Executor OOM or resource pressure |
| Shuffle fetch failed | `ShuffleFetchFailedException` | Executor exited or unresponsive | Network issue or executor failure during shuffle |
| Data skew | Some tasks take much longer | One executor shows high CPU/memory usage | Uneven data distribution across partitions |
| Slow stage | `Stage X took N seconds` | Some executors idle while others at 100% | Skewed key distribution or insufficient parallelism |

### 5.2 Identifying Data Skew

Look for these patterns in the logs:

1. **In the driver log**: Tasks in the same stage have vastly different durations (e.g., one task takes 30 minutes while others complete in 10 seconds).
2. **In executor logs**: One executor shows significantly higher memory usage or GC overhead compared to others.
3. **Log entries to search for**:
   - `Task X.Y finished in N ms` — compare durations across tasks in the same stage
   - `GC time (ms)` — excessive GC time indicates memory pressure on a specific executor

### 5.3 Executor Failure Analysis

When an executor fails:

1. Check the **driver log** for `ExecutorLostFailure` or `Removing executor X` messages to identify which executor was lost.
2. Navigate to the corresponding `executor/<id>/stderr` file on OSS for the root cause.
3. Common causes:
   - OOM (heap or off-heap)
   - Container killed by resource manager (exceeded memory limits)
   - Disk full on the executor node
   - Network partition

---

## 6. Important Notes

- **Read-only access**: This Skill only supports `oss:ListObjects` and `oss:GetObject`. It **MUST NOT** delete, modify, or overwrite any files on OSS. See the high-risk operation safety constraints in [SKILL.md](../SKILL.md).
- **Log retention**: OSS logs follow the same 30-day retention policy as `GetSparkAppLog`. If the LogRootPath directory is empty or returns `NoSuchKey`, the logs may have expired.
- **Large log files**: Some executor stderr files can be very large (hundreds of MB). Use `aliyun ossutil cat` with caution; consider piping to `head`/`tail` or downloading for local analysis if needed.
- **Event log format**: The `<LastAttemptId>.0` file is in Spark event log format (JSON lines — one JSON object per line). While it can be viewed via `ossutil cat`, it is typically too large and structured for manual reading. Use `event_log_analyzer.py` or Spark UI for analysis.
