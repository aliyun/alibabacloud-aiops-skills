# Common ADB Spark Errors and Solutions

A structured reference of common business-side errors encountered in ADB Spark applications, with typical log patterns and recommended remediation actions.

---

## 1. Out of Memory (OOM) Errors

### 1.1 Driver OOM

| Item | Detail |
|------|--------|
| **Error Type** | Driver OOM (`java.lang.OutOfMemoryError: Java heap space`) |
| **Typical Log Snippet** | `java.lang.OutOfMemoryError: Java heap space` in `driver/stderr` |
| **Root Cause** | The driver JVM exhausted its heap memory. Common causes: collecting large amounts of data to the driver (e.g., `collect()` on a large DataFrame), broadcasting oversized variables, or insufficient `spark.driver.memory` configuration. |
| **Recommended Actions** | 1. Increase `spark.driver.memory` in the Spark application configuration.<br>2. Avoid `collect()` on large datasets; use `take()` or write to storage instead.<br>3. Reduce broadcast variable size.<br>4. Enable `spark.driver.memoryOverhead` if off-heap memory is also needed. |

### 1.2 Executor OOM

| Item | Detail |
|------|--------|
| **Error Type** | Executor OOM (`java.lang.OutOfMemoryError: Java heap space`) |
| **Typical Log Snippet** | `Executor: Exception in task X.Y` followed by `java.lang.OutOfMemoryError: Java heap space` in `executor/<id>/stderr` |
| **Root Cause** | An executor JVM ran out of heap memory. Common causes: large shuffle partitions, wide transformations (e.g., `groupByKey` on high-cardinality keys), or insufficient `spark.executor.memory`. |
| **Recommended Actions** | 1. Increase `spark.executor.memory` in the Spark application configuration.<br>2. Optimize data partitioning — increase the number of shuffle partitions (`spark.sql.shuffle.partitions`).<br>3. Replace `groupByKey` with `reduceByKey` or `aggregateByKey` to reduce shuffle data volume.<br>4. Enable `spark.executor.memoryOverhead` for off-heap allocation. |

### 1.3 Pod OOM Killed (Exit Code 137)

| Item | Detail |
|------|--------|
| **Error Type** | Pod OOM Killed (Kubernetes OOMKilled, exit code 137) |
| **Typical Log Snippet** | `Container killed by Kubernetes due to exceeding memory limits` or `Command exited with code 137`; pod status shows `OOMKilled`; Spark log may show `ExecutorLostFailure (executor X exited caused by one of the running tasks) Reason: Container in pod '<pod-name>' exited from status code 137` |
| **Root Cause** | ADB Spark runs on Kubernetes. Each driver/executor runs as a Pod with a container memory limit. When the total memory usage of a JVM process (heap + off-heap + native memory + overhead) exceeds the Pod's container memory limit, Kubernetes OOM Killer terminates the container with SIGKILL (exit code 137). This differs from JVM OOM — the JVM itself may not throw `OutOfMemoryError` because the OS kills the process before the JVM can report the error. Common causes:<br>- `spark.executor.memoryOverhead` (or `spark.driver.memoryOverhead`) is too low for off-heap usage (e.g., native libraries, direct buffers, Python/PySpark worker processes).<br>- PySpark applications with heavy pandas/numpy usage consuming native memory beyond JVM tracking.<br>- Large shuffle or compression buffers allocated in native memory. |
| **Recommended Actions** | 1. Increase `spark.executor.memoryOverhead` (default is typically 10% of executor memory or 384MB, whichever is larger). For PySpark workloads, set to at least 30-50% of `spark.executor.memory`.<br>2. Increase `spark.driver.memoryOverhead` if the driver pod is killed.<br>3. Monitor per-pod memory usage — the effective container limit is `spark.executor.memory` + `spark.executor.memoryOverhead`.<br>4. For PySpark with large pandas operations, consider using Apache Arrow with bounded batches or switching to Spark-native DataFrame APIs.<br>5. Reduce off-heap memory pressure: lower `spark.shuffle.file.buffer`, `spark.unsafe.sorter.spill.reader.buffer.size`, or disable off-heap memory (`spark.memory.offHeap.enabled=false`) if not strictly needed.<br>6. Check if custom native libraries (JNI) are leaking memory — profile with tools like `jemalloc` or `pmap` if feasible. |

---

## 2. Data Skew

| Item | Detail |
|------|--------|
| **Error Type** | Data Skew |
| **Typical Log Snippet** | Driver log shows tasks in the same stage with vastly different durations: `Task 0 finished in 120000 ms` while `Task 1 finished in 500 ms`; executor log for the slow task shows high GC overhead or OOM. |
| **Root Cause** | Uneven data distribution across partitions. A small number of partitions contain disproportionately large amounts of data, causing a few tasks to become bottlenecks while others complete quickly. |
| **Recommended Actions** | 1. **Repartition**: Use `.repartition(N)` to redistribute data more evenly.<br>2. **Salting key**: Add a random prefix (salt) to the skew key to distribute data across multiple partitions, then aggregate in two passes.<br>3. **Broadcast join**: If one side of the join is small enough, use broadcast join to avoid shuffle entirely (`spark.sql.autoBroadcastJoinThreshold`).<br>4. **Increase shuffle partitions**: Raise `spark.sql.shuffle.partitions` to create more, smaller partitions.<br>5. **Enable AQE (Adaptive Query Execution)**: Set `spark.sql.adaptive.enabled=true` (Spark 3.0+). AQE can automatically detect and split skewed partitions during shuffle. Fine-tune with `spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes` (default 256MB).<br>6. **Quantitative analysis**: Use `event_log_analyzer.py` to parse the Spark Event Log and quantify skew severity. The skew ratio is defined as `max_partition_size / median_partition_size`. Severity levels: **severe** (skew ratio > 10 and max partition > 100MB), **moderate** (skew ratio > 5). See [spark-app-data-skew-diagnosis.md](spark-app-data-skew-diagnosis.md) for the complete diagnosis workflow. |

---

## 3. Dependency / Class Loading Errors

### 3.1 ClassNotFoundException

| Item | Detail |
|------|--------|
| **Error Type** | `java.lang.ClassNotFoundException` |
| **Typical Log Snippet** | `java.lang.ClassNotFoundException: com.example.MyCustomClass` in `driver/stderr` or `executor/<id>/stderr` |
| **Root Cause** | A required class is not found on the classpath. The JAR containing the class was not included in the Spark application's dependencies, or the class path is misconfigured. |
| **Recommended Actions** | 1. Verify that the required JAR is included in the application's `spark.jars` or `spark.submit.pyFiles` configuration.<br>2. Check that the JAR is accessible at the specified OSS path.<br>3. Ensure the JAR version matches the Scala/Spark version of the cluster. |

### 3.2 NoSuchMethodError

| Item | Detail |
|------|--------|
| **Error Type** | `java.lang.NoSuchMethodError` |
| **Typical Log Snippet** | `java.lang.NoSuchMethodError: com.example.MyClass.myMethod()Ljava/lang/String;` |
| **Root Cause** | A method exists at compile time but not at runtime. This typically indicates a JAR version conflict — the runtime classpath contains a different version of a dependency than expected. |
| **Recommended Actions** | 1. Check for JAR version conflicts — list all JARs on the classpath and look for duplicate classes.<br>2. Use `spark.driver.userClassPathFirst=true` and `spark.executor.userClassPathFirst=true` to prioritize user-provided JARs over Spark's bundled dependencies.<br>3. Align dependency versions with the Spark version running on the cluster. |

---

## 4. Permission Errors

### 4.1 OSS Access Denied

| Item | Detail |
|------|--------|
| **Error Type** | OSS Access Denied (`AccessDenied` / HTTP 403) |
| **Typical Log Snippet** | `com.aliyun.oss.OSSException: Access denied` or `Status Code: 403` when reading/writing OSS paths |
| **Root Cause** | The Spark application's RAM role or the executing user lacks the required OSS permissions (`oss:GetObject`, `oss:PutObject`, `oss:ListObjects`) on the target bucket. |
| **Recommended Actions** | 1. Verify the RAM role attached to the ADB cluster has the necessary OSS permissions.<br>2. Check the OSS bucket policy — it may restrict cross-account or cross-VPC access.<br>3. If using cross-account access, ensure the bucket owner has granted the appropriate permissions via bucket policy or RAM role. |

---

## 5. Network / Connection Timeout Errors

| Item | Detail |
|------|--------|
| **Error Type** | Connection Timeout / Connection Refused |
| **Typical Log Snippet** | `java.net.ConnectException: Connection refused` or `java.net.SocketTimeoutException: connect timed out` |
| **Root Cause** | The Spark application cannot reach an external data source or service. Common causes: VPC/security group misconfiguration, the target service is down, or DNS resolution failure. |
| **Recommended Actions** | 1. **Check VPC and security group**: Ensure the ADB cluster's VPC allows outbound traffic to the target service's port.<br>2. **Check data source reachability**: Verify the target service (RDS, Kafka, etc.) is running and accessible from the ADB cluster's VPC.<br>3. **Check ENI configuration**: For data sources requiring ENI access, ensure the ENI is correctly configured for the ADB cluster.<br>4. **Check NAT Gateway**: If accessing the public internet, ensure the NAT Gateway and SNAT entries are properly configured.<br>5. **Increase timeout**: If the connection is valid but slow, increase `spark.network.timeout` and `spark.executor.heartbeatInterval`. |

---

## 6. Resource Insufficient Errors

| Item | Detail |
|------|--------|
| **Error Type** | Resource Provisioning Timeout |
| **Typical Log Snippet** | `Resource provisioning timeout` in the application message, or the application stays in `STARTING` state for an extended period before failing. |
| **Root Cause** | The ADB cluster's resource group does not have enough available resources (CPU, memory) to start the Spark application. This can occur when too many applications are running concurrently or the resource group capacity is too small. |
| **Recommended Actions** | 1. **Check resource group capacity**: Use `GetSparkAppInfo` to check the current resource group and its utilization.<br>2. **Reduce resource requests**: Lower `spark.driver.memory`, `spark.executor.memory`, or `spark.executor.instances` to fit within available capacity.<br>3. **Adjust queue priority**: If using job queues, increase the application's priority to get resources sooner.<br>4. **Scale the resource group**: Contact the cluster administrator to expand the resource group capacity.<br>5. **Schedule off-peak**: Resubmit the application during lower-utilization periods. |

---

## 7. SQL Parsing / Execution Errors

### 7.1 AnalysisException

| Item | Detail |
|------|--------|
| **Error Type** | `org.apache.spark.sql.AnalysisException` |
| **Typical Log Snippet** | `AnalysisException: Table or view not found: my_table` or `AnalysisException: cannot resolve 'unknown_col' given input columns` |
| **Root Cause** | The SQL statement references a table, view, or column that does not exist or is not accessible. This can be caused by typos, incorrect catalog/database references, or missing table definitions. |
| **Recommended Actions** | 1. Verify the table name and column names in the SQL statement.<br>2. Check the catalog and database context — use `USE catalog.database` or fully qualified names (`catalog.database.table`).<br>3. Ensure the table has been created before the Spark application runs.<br>4. If referencing an external table, verify the data source connection is valid. |

### 7.2 Query Execution Error

| Item | Detail |
|------|--------|
| **Error Type** | `org.apache.spark.sql.ExecutionException` |
| **Typical Log Snippet** | `ExecutionException: Job aborted due to stage failure` followed by task failure details |
| **Root Cause** | The SQL query failed during execution. This is a generic error that wraps the actual cause — check the nested exception for the specific failure reason (OOM, data skew, shuffle failure, etc.). |
| **Recommended Actions** | 1. Read the full stack trace to identify the nested exception (the actual root cause).<br>2. Cross-reference the nested exception with the appropriate section in this document (OOM, data skew, etc.).<br>3. If the error is related to a specific operator, check the query plan for inefficient joins or missing optimizations. |

---

## 8. Shuffle Fetch Failed / Shuffle Spill

### 8.1 FetchFailedException (Executor Lost / Connection Reset / File Not Found)

| Item | Detail |
|------|--------|
| **Error Type** | `FetchFailedException` |
| **Typical Log Snippet** | `org.apache.spark.shuffle.FetchFailedException: Failed to connect to executor <host>:<port>` or `FetchFailedException: File not found: shuffle_<id>_<mapIdx>_<reduceIdx>.data` or `Failed connect to <host>:<port> Connection refused` |
| **Root Cause** | An executor in the shuffle read phase cannot fetch shuffle data from an upstream executor. Common causes: the upstream executor was lost (OOMKilled, preemption, or node failure), the upstream executor experienced a long GC pause causing the connection to be reset, a transient network issue between executors, or the shuffle index/data files were deleted before the downstream task could read them. |
| **Recommended Actions** | 1. Increase shuffle fetch retry count: raise `spark.shuffle.io.maxRetries` (default 3) and `spark.shuffle.io.retryWait` (default 5s).<br>2. Enable the External Shuffle Service (`spark.shuffle.service.enabled=true`) so shuffle files survive executor termination.<br>3. Increase shuffle partitions (`spark.sql.shuffle.partitions`) to reduce per-partition data volume and lower per-fetch failure impact.<br>4. Check for executor loss events in the driver log — if executors are being killed due to OOM, address the OOM issue first (see Section 1).<br>5. If the cluster is under heavy load, consider increasing `spark.network.timeout` (default 120s). |

### 8.2 Shuffle Spill / Disk Overflow

| Item | Detail |
|------|--------|
| **Error Type** | Shuffle Data Exceeds Disk Capacity / Spill Failure |
| **Typical Log Snippet** | `No space left on device` in executor logs, or `ExternalShuffleBlockResolver` errors, or `org.apache.spark.memory.SparkOutOfMemoryError: Unable to acquire memory for shuffle spill` |
| **Root Cause** | The shuffle data volume exceeds the available disk space on an executor, causing spill operations to fail. This typically occurs when the shuffle write phase generates far more data than expected (e.g., due to data skew or an exploding join), and the executor's local disk cannot accommodate the intermediate files. |
| **Recommended Actions** | 1. Check disk usage on executor nodes — if the local disk is full, clean up stale shuffle files or increase disk capacity.<br>2. Increase the number of shuffle partitions (`spark.sql.shuffle.partitions`) to distribute shuffle data across more tasks and reduce per-task spill volume.<br>3. Reduce shuffle data volume by pre-filtering or pre-aggregating data before the shuffle stage.<br>4. Enable `spark.shuffle.compress=true` (default) and consider using a faster compression codec (`spark.io.compression.codec=lz4`).<br>5. If using Kubernetes, ensure the executor pod's ephemeral storage limit is sufficient (`spark.kubernetes.executor.limit.volumes`).<br>6. **Quantitative spill analysis**: Use `event_log_analyzer.py` to measure per-stage spill volume. Severity levels: **Critical** (disk spill > 1GB), **Warning** (> 100MB), **Info** (> 0). High spill often co-occurs with data skew — check if skewed partitions are concentrating data on a few executors.<br>7. **Check for co-occurring data skew**: If spill is concentrated in specific stages, cross-reference with the data skew analysis (Section 2) to determine if skew is the underlying cause. |

---

## 9. Small Files Problem

### 9.1 Writing Excessive Small Files

| Item | Detail |
|------|--------|
| **Error Type** | Small File Proliferation on Write |
| **Typical Log Snippet** | Spark UI shows a large number of output files each smaller than 1MB; `hdfs dfs -count <path>` or `ossutil ls <path>` reveals thousands of tiny files; downstream reads show excessive partition listing time. |
| **Root Cause** | The write operation produces an excessive number of small files. Common causes: the number of shuffle partitions is too high relative to the data volume, missing `coalesce()` or `repartition()` before writing, high-cardinality partition columns causing each partition to contain very few rows, or frequent append-mode writes each producing a new batch of small files. |
| **Recommended Actions** | 1. Use `.coalesce(N)` or `.repartition(N)` before writing to control the number of output files.<br>2. Note: `spark.sql.files.maxRecordsPerFile` limits the maximum records per output file — setting it causes Spark to **split large files** into smaller ones. Do NOT use this to reduce small file count; it has the opposite effect. Use `.coalesce(N)` or `.repartition(N)` instead.<br>3. Use ADB Spark's automatic small-file compaction feature if available.<br>4. Reduce the number of partition columns or lower partition column cardinality.<br>5. For append writes, periodically run a compaction job to merge small files.<br>6. **Quantitative detection**: Use `event_log_analyzer.py` to detect small file risk. The tool flags stages where `numTasks > 100` and average output per task < 10MB. See [spark-app-data-skew-diagnosis.md](spark-app-data-skew-diagnosis.md) for thresholds and decision tree. |

### 9.2 Reading Excessive Small Files

| Item | Detail |
|------|--------|
| **Error Type** | Small File Read Performance Degradation |
| **Typical Log Snippet** | Spark UI shows an unusually large number of tasks (e.g., tens of thousands) with each task processing a very small amount of data (< 1MB); the job spends a disproportionate amount of time in `FileListing` or partition discovery; driver log shows `Listing leaf files and directories` with high latency. |
| **Root Cause** | The input data consists of a very large number of small files, causing Spark to spawn one task per file (or per partition). The overhead of scheduling, deserializing, and managing these tasks outweighs the actual computation. Additionally, file listing on OSS can be slow for directories with many small files. |
| **Recommended Actions** | 1. Increase `spark.sql.files.maxPartitionBytes` (default 128MB) to allow Spark to read multiple small files within a single partition/task.<br>2. Set `spark.sql.files.openCostInBytes` to a higher value to make the planner prefer fewer, larger partitions.<br>3. Pre-process the input data by compacting small files into larger ones.<br>4. Use `spark.sql.hive.convertMetastoreOrc` / `spark.sql.hive.convertMetastoreParquet` to leverage native data source readers that handle file listing more efficiently.<br>5. If the data is partitioned, consider using partition pruning to reduce the number of files scanned. |

---

## 10. Serialization Errors (Kryo / Java)

### 10.1 Java Serialization — NotSerializableException

| Item | Detail |
|------|--------|
| **Error Type** | `java.io.NotSerializableException` |
| **Typical Log Snippet** | `org.apache.spark.SparkException: Task not serializable` followed by `java.io.NotSerializableException: com.example.MyNonSerializableClass` |
| **Root Cause** | A closure (e.g., a lambda function or `map`/`filter` operation) references an object that does not implement the `Serializable` interface. When Spark attempts to serialize the closure to send it to executors, the referenced non-serializable object causes the serialization to fail. |
| **Recommended Actions** | 1. Avoid referencing non-serializable objects inside closures — extract only the needed primitive values or serializable objects.<br>2. If the object must be shared across tasks, use `sc.broadcast()` to broadcast it as a read-only variable (broadcast variables are serialized separately and sent once per executor).<br>3. Make the referenced class implement `java.io.Serializable`.<br>4. If the object is only used for its fields, extract the fields into local variables before the closure. |

### 10.2 Kryo Serialization Exception

| Item | Detail |
|------|--------|
| **Error Type** | Kryo Serialization Error |
| **Typical Log Snippet** | `com.esotericsoftware.kryo.KryoException: Class is not registered: com.example.MyClass` or `com.esotericsoftware.kryo.KryoException: Buffer overflow` |
| **Root Cause** | Kryo serialization fails because: (1) the class is not registered with Kryo (`spark.kryo.classesToRegister` is not configured), causing Kryo to fall back to a less efficient serializer or throw an error; (2) the serialization buffer is too small for the object being serialized (`spark.kryoserializer.buffer.max` is insufficient). |
| **Recommended Actions** | 1. Register custom classes with Kryo: set `spark.kryo.classesToRegister` to a comma-separated list of class names, or use `spark.kryo.registrator` to specify a custom `KryoRegistrator` class.<br>2. Increase the Kryo serialization buffer: raise `spark.kryoserializer.buffer.max` (default 64MB) — e.g., set to `256m` for large objects.<br>3. If the buffer overflow persists, also increase `spark.kryoserializer.buffer` (default 64KB) for the initial buffer size.<br>4. For large read-only objects, use `sc.broadcast()` instead of including them in closures — broadcast variables are serialized only once per executor.<br>5. If Kryo issues are intractable, switch to Java serialization by removing `spark.serializer=org.apache.spark.serializer.KryoSerializer` (note: this may reduce performance). |

---

## 11. Cartesian Product / Data Explosion

### 11.1 Implicit Cartesian Product (Missing Join Condition)

| Item | Detail |
|------|--------|
| **Error Type** | Implicit Cross Join / Cartesian Product |
| **Typical Log Snippet** | Spark physical plan shows `CartesianProduct` or `BroadcastNestedLoopJoin` where a `SortMergeJoin` or `ShuffleHashJoin` was expected; task execution time is extremely long; shuffle write volume far exceeds the input data volume. |
| **Root Cause** | The SQL statement joins two tables without a proper join condition, or the join condition is incorrect/incomplete (e.g., referencing the wrong column or missing a join key). Spark falls back to a Cartesian product, generating `N × M` rows from two tables of size N and M. This is especially dangerous with large tables. |
| **Recommended Actions** | 1. Review the SQL statement to ensure all `JOIN` clauses have a valid `ON` condition with the correct columns.<br>2. Set `spark.sql.crossJoin.enabled=false` (Spark 3.x default) to explicitly prevent implicit Cartesian products — Spark will throw an error instead of silently executing a cross join.<br>3. If a cross join is intentional, use the explicit `CROSS JOIN` syntax and set `spark.sql.crossJoin.enabled=true`.<br>4. Examine the query plan (`EXPLAIN`) before running the job to verify the join strategy. |

### 11.2 Data Explosion (Many-to-Many Join)

| Item | Detail |
|------|--------|
| **Error Type** | Join Data Explosion |
| **Typical Log Snippet** | Shuffle write volume spikes dramatically after a join stage (e.g., input is 1GB but shuffle write exceeds 100GB); Spark UI shows a single stage producing an abnormally large number of output records; tasks may eventually fail with OOM or disk spill errors. |
| **Root Cause** | A many-to-many join on a key with a large number of duplicate values on both sides of the join. For example, joining on a low-cardinality key (e.g., a status field with only a few distinct values) causes each row on one side to match many rows on the other side, resulting in a combinatorial explosion of output rows. |
| **Recommended Actions** | 1. Verify that the join key has appropriate cardinality — avoid joining on low-cardinality columns.<br>2. Pre-aggregate or deduplicate one or both sides of the join before joining (e.g., using `GROUP BY` or `DISTINCT`).<br>3. If the join is meant to be a lookup, ensure the lookup side has unique keys — use `row_number()` or `DISTINCT` to deduplicate.<br>4. Add additional join conditions to narrow the matching criteria.<br>5. Monitor shuffle write metrics in Spark UI to detect data explosion early during development. |

---

## 12. Straggler Tasks / Long Tail Tasks

| Item | Detail |
|------|--------|
| **Error Type** | Straggler / Long Tail Tasks |
| **Typical Log Snippet** | Spark UI shows a stage where most tasks complete in seconds but a few tasks take minutes or hours; the 75th percentile task duration is close to the median, but the max duration is >10x the 75th percentile; individual straggler tasks show significantly higher shuffle read/write bytes than the average.<br>`event_log_analyzer.py` output shows task duration > median × 5 (configurable via `--duration-threshold`) without proportional increase in shuffle read bytes. |
| **Root Cause** | A small number of tasks in a stage take disproportionately long to complete. Root causes include: (1) data skew — a few partitions contain far more data than others (see Section 2 for partition-level skew analysis); (2) resource contention on the executor's node — other processes competing for CPU, memory, or disk I/O; (3) long GC pauses on the straggler executor (check GC logs); (4) speculative execution is not enabled, so the slow task is never re-attempted on a different executor. |
| **Recommended Actions** | 1. Enable speculative execution: set `spark.speculation=true` so Spark can launch duplicate attempts of slow tasks on other executors.<br>2. Tune speculation thresholds: adjust `spark.speculation.multiplier` (default 1.5 — a task is considered a straggler if its duration exceeds this multiplier times the median task duration) and `spark.speculation.quantile` (default 0.75 — speculation starts after this fraction of tasks in a stage have completed).<br>3. Check for data skew — if straggler tasks have significantly more shuffle read data, refer to Section 2 (Data Skew) for remediation.<br>4. Inspect the executor's node for resource bottlenecks — check CPU load, memory pressure, and disk I/O using node-level metrics or Kubernetes pod resource usage.<br>5. If GC pauses are the bottleneck, tune GC settings (e.g., switch to G1GC with `-XX:+UseG1GC`, increase `spark.executor.memory`, or reduce `spark.memory.fraction`).<br>6. **Quantitative straggler detection**: Use `event_log_analyzer.py` to automatically identify straggler tasks. The tool flags tasks where duration exceeds median × N (default 5) or shuffle read bytes exceed median × N. Key distinction from data skew: straggler tasks have high duration ratio but **normal** shuffle read ratio (no data-volume-based skew).<br>7. **Cross-reference with GC metrics**: Check the GC time ratio (`gc_time / duration`) for flagged tasks. If GC time > 30% of task duration, the straggler is likely caused by memory pressure rather than external factors. |

---

## 13. Python Worker Crash (PySpark EOFException)

| Item | Detail |
|------|--------|
| **Error Type** | Python Worker Unexpected Exit (`org.apache.spark.SparkException: Python worker exited unexpectedly (crashed)`) |
| **Typical Log Snippet** | Driver log shows `SparkException: Python worker exited unexpectedly (crashed)` at `BasePythonRunner$ReaderIterator`; nested `Caused by: java.io.EOFException` at `DataInputStream.readInt` and `PythonRunner$$anon$3.read`; executor stderr may contain Python-level errors (MemoryError, unhandled exceptions, or native library crash traces). |
| **Root Cause** | The Python worker process (forked by each executor to run PySpark UDFs / `map` / `flatMap` operations) crashed or was killed, while the JVM executor process was still alive and attempting to communicate with it. The broken pipe/socket causes an `EOFException` when the JVM tries to read data from the Python side.<br><br>**This is NOT the same as Pod OOMKilled (Section 1.3):** the Kubernetes container itself is NOT killed — only the Python child process within the container dies. No exit code 137, no `OOMKilled` pod status.<br><br>Common causes:<br>- **Python memory exhaustion**: The Python worker allocated too much native memory (e.g., large lists/dicts in a UDF) and was killed by the Linux OOM Killer targeting the Python process specifically, while the container's total memory remained within cgroup limits.<br>- **Unhandled Python exception**: User code in `map()`/`flatMap()`/UDF threw an exception that was not caught (e.g., `KeyError`, `TypeError`, `ValueError`).<br>- **Native library crash**: Python extension modules (numpy, pandas, scipy, custom C extensions) triggered a segmentation fault (SIGSEGV) or abort (SIGABRT).<br>- **Python environment mismatch**: Missing or incompatible Python dependencies on the executor; Python version incompatibility between driver and executor. |
| **Recommended Actions** | 1. **Check executor stderr**: Navigate to the executor's stderr log via OSS (see [OSS Full Log Deep Analysis](spark-app-oss-full-log-analysis.md)) — Python errors appear in executor stderr, not driver log. Look for `MemoryError`, `Segmentation fault`, or unhandled exception tracebacks.<br>2. **If Python MemoryError**: The Python worker allocated more memory than available. Reduce per-partition data volume by increasing `spark.sql.shuffle.partitions` or using more partitions in `sc.parallelize()`. Alternatively, increase `spark.executor.memoryOverhead` to give more off-heap headroom for Python processes.<br>3. **If segmentation fault (SIGSEGV)**: A native library in the Python environment crashed. Verify that all Python packages are compatible with the executor's OS/architecture. Pin package versions and test locally with the same environment.<br>4. **If unhandled Python exception**: Add defensive error handling (`try`/`except`) in UDF/map functions to catch expected exceptions and return sentinel values instead of crashing the worker.<br>5. **Check Python dependency configuration**: Ensure `spark.submit.pyFiles` or `--py-files` includes all required `.py`/`.zip`/`.egg` dependencies, and that external packages are installed on all executor nodes.<br>6. **Distinction from Pod OOMKilled**: If the container was NOT OOMKilled (no exit code 137), the issue is Python-specific rather than container-level memory exhaustion. Focus on Python memory usage patterns and exception handling rather than increasing container memory limits. |
