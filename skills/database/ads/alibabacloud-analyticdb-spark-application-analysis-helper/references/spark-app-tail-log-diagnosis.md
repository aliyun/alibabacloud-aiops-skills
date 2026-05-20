# Spark Application Tail Log Quick Diagnosis

Use the `GetSparkAppLog` API to retrieve the tail logs of a Spark application and quickly identify the root cause of a failure.

---

## 1. Overview

Tail logs are the **first step** in diagnosing a failed Spark application. Most runtime failures (OOM, exceptions, timeouts) leave clear error traces in the last few hundred lines of the driver log. `GetSparkAppLog` returns up to 500 lines from the end of the log, which is usually sufficient for a quick diagnosis.

---

## 2. Workflow

```
1. Retrieve application info and confirm analysis intent
2. Call GetSparkAppLog to retrieve tail log
3. Locate errors: scan LogContent from bottom up using keyword table (Section 4)
4. Classify error: match extracted error against known patterns in spark-app-common-errors.md (Section 5)
5. If tail log is insufficient, proceed to OSS full log analysis
```

### 2.1 Step 1 — Retrieve Application Info and Confirm Analysis Intent

Before pulling logs, retrieve the application's metadata to understand its context. Note that the application may **not** be in `FAILED` state — for example, SQL errors executed on `interactive` (long-running) resource groups will surface within an application that remains in `RUNNING` or `SUCCEEDED` state.

```bash
aliyun adb get-spark-app-info \
  --api-version 2021-12-01 \
  --app-id s202401011200xx1234ab000**** \
  --region cn-beijing \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper
```

> **Note**: `--region` is **required**.

After retrieving the application info, present the following key fields to the user for confirmation:
- **AppName** / **AppId** — to verify this is the correct application
- **State** — current application state (may be `RUNNING`, `SUCCEEDED`, `FAILED`, etc.)
- **ResourceGroupName** — whether it runs on an `interactive` (long-running) or `batch` resource group
- **Duration** / **SubmittedTime** — execution timing context

**Ask the user to confirm** that this is indeed the application they want to analyze before proceeding to log retrieval. This is important because:
1. On `interactive` resource groups, a single long-running Spark application serves multiple SQL statements. The application itself may be healthy while individual SQL executions within it have failed.
2. The user may have provided an incorrect AppId or the error may originate from a different application.

### 2.2 Step 2 — Retrieve Tail Log

Call `GetSparkAppLog` to fetch the last N lines (up to 500):

```bash
# Get the tail log
aliyun adb get-spark-app-log \
  --region cn-beijing \
  --api-version 2021-12-01 \
  --app-id s202401011200xx1234ab000**** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-spark-application-analysis-helper
```

> **Note**: `--region` is **required**.

**Key Response Fields**:

| Field | Description |
|-------|-------------|
| `Data.LogContent` | Multi-line log text; the actual log output |
| `Data.LogSize` | Total log size in bytes; **0 means no valid log** |

---

## 3. Log Output Interpretation Guide

The `LogContent` field contains the raw text of the application log. Follow these steps to extract the most useful information:

1. **Start from the bottom**: Errors almost always appear in the last few dozen lines. Scroll to the end first.
2. **Look for exception stack traces**: Java/Scala exceptions produce multi-line stack traces starting with the exception class name.
3. **Identify the root cause**: The first exception in a chain is typically the root cause; subsequent exceptions are often side effects.

### 3.1 Example Log Output Structure

```
24/01/15 10:32:15 INFO SparkContext: Running Spark version 3.3.2
24/01/15 10:32:16 INFO ResourceUtils: Starting...
...
24/01/15 10:45:23 ERROR Executor: Exception in task 37.0
java.lang.OutOfMemoryError: Java heap space
    at java.util.Arrays.copyOf(Arrays.java:3210)
    ...
24/01/15 10:45:24 ERROR SparkUncaughtExceptionHandler: Uncaught exception in thread executor-heartbeat-1
java.lang.OutOfMemoryError: Java heap space
    ...
24/01/15 10:45:30 INFO SparkContext: SparkContext stopped
```

In this example, the root cause (`OutOfMemoryError`) appears near the end.

---

## 4. Error Location Keywords

Use the following keywords to **locate** error-relevant lines in `LogContent`. This step extracts the error context (exception class, stack trace, surrounding log lines) — it does NOT determine the final root cause. Classification happens in the next step (Section 5).

**How to use**: Scan `LogContent` from bottom to top. When a keyword matches, extract the full exception block (exception line + stack trace + 3-5 surrounding context lines) as the "error summary".

| Keyword | Priority |
|---------|----------|
| `OutOfMemoryError` / `OOM` | High |
| `Exit code 137` / `OOMKilled` | High |
| `FetchFailedException` / `Failed to connect` | High |
| `No space left on device` | High |
| `Task not serializable` / `NotSerializableException` | High |
| `Pod exceeded memory limit` | High |
| `Exception` (with ERROR level) | High |
| `killed` / `KILLED` | Medium |
| `timeout` / `TimeoutException` | Medium |
| `Connection refused` / `SocketTimeoutException` | Medium |
| `AccessDenied` / `403` | Medium |
| `ClassNotFoundException` / `NoSuchMethodError` | Medium |
| `ShuffleFetchFailedException` | Medium |
| `KryoException` / `Buffer overflow` | Medium |
| `CartesianProduct` / `BroadcastNestedLoopJoin` | Medium |
| `AnalysisException` | Medium |
| `SparkException` | Medium |
| `Python worker exited` / `EOFException` | High |
| `Planning took` / `listing leaf files` | Low |
| `WARN TaskSetManager` / `Killing attempt` | Low |

**Tip**: Scan from bottom to top by priority (High → Medium → Low). Stop at the first High-priority match and extract the full error block. If only Low-priority keywords match, extract the surrounding context for further analysis.

---

## 5. Error Classification

After extracting the error summary from Section 4, classify it against the structured knowledge base in [spark-app-common-errors.md](spark-app-common-errors.md).

### 5.1 Classification Process

```
Error Summary (from Step 4)
    ↓
Compare against each category's "Typical Log Snippet" in spark-app-common-errors.md
    ↓
Match? → Use that category's "Root Cause" and "Recommended Actions"
No match? → Proceed to OSS full log analysis for deeper investigation
```

### 5.2 Multi-signal Disambiguation

Some keywords appear in multiple error categories. Use the following disambiguation rules:

| Ambiguous Signal | Additional Context | Classified As |
|-----------------|-------------------|---------------|
| `OutOfMemoryError` | In driver log + `collect()` or broadcast in stack | **1.1 Driver OOM** |
| `OutOfMemoryError` | In executor log + shuffle/groupByKey in stack | **1.2 Executor OOM** |
| `Exit code 137` (no JVM OOM in log) | Pod status shows `OOMKilled` | **1.3 Pod OOM Killed** |
| `OutOfMemoryError` + skewed task durations | One task >> others in same stage | **2. Data Skew** (causing OOM) |
| `FetchFailedException` | Upstream executor lost / exit code 137 | **1.3 Pod OOM Killed** (upstream) |
| `FetchFailedException` | `No space left on device` | **8.2 Shuffle Spill / Disk Overflow** |
| `FetchFailedException` | `Connection refused` / network reset | **5. Network / Connection Timeout** |
| `SparkException: Job aborted` | Nested exception is the real cause | Classify by the **nested** exception |
| `Task not serializable` | Nested `java.io.NotSerializableException` with closure class in stack | **10.1 NotSerializableException** |
| `listing leaf files` / `Planning took` | Spark UI or log shows tens of thousands of input files or tasks | **9.2 Reading Excessive Small Files** |
| `WARN TaskSetManager` + task duration >> stage median | No obvious skew in input data size per task; executor node may have resource contention | **12. Straggler Tasks / Long Tail Tasks** |
| `Python worker exited` / `EOFException` | No exit code 137 in log; Python process crashed within container | **13. Python Worker Crash (PySpark EOFException)** |
| `Python worker exited` + `Exit code 137` / `OOMKilled` | Container-level OOM killed the entire pod | **1.3 Pod OOM Killed** |

### 5.3 Confidence and Escalation

- **High confidence**: Error summary directly matches a single category's log pattern → provide diagnosis immediately.
- **Medium confidence**: Error matches multiple categories or the signal is ambiguous → present top 2 candidates to user with reasoning, ask for confirmation.
- **Low confidence**: No clear match in knowledge base → recommend OSS full log analysis or ask user for additional context (e.g., "Was this a batch job or interactive SQL?").

---

## 6. Important Notes

- **Log retention**: Application logs are retained for **30 days**. After 30 days, the log file is deleted and `GetSparkAppLog` will return an empty `LogContent`.
- **LogSize = 0**: If `Data.LogSize` is 0, there is no valid log for this application. This can happen when:
  - The application was submitted but never started executing
  - The log retention period has expired
  - The application crashed before producing any log output
- **Maximum line count**: The `LogLength` parameter accepts values 1–500 (default 300). If 500 lines are insufficient to diagnose the issue, proceed to [OSS Full Log Deep Analysis](spark-app-oss-full-log-analysis.md) for complete log retrieval.
