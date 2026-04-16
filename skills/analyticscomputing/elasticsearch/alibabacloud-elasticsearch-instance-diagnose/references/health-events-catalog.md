# Elasticsearch health event catalog

> **18 event codes / 49 reason codes** across **8** categories. Each row: **reason code** under its **event code**.

---

## Quick nav: TOP 15 by case frequency


| Rank | Reason code | Event code | Priority | Threshold (summary) | SOP |
| --- | --- | --- | --- | --- | --- |
| 1 | `CPU.PeakUsageHigh` | `HealthCheck.CPULoadHigh` | P1 | P99 > 95% for 3m | [sop-cpu-load.md](sop-cpu-load.md) |
| 2 | `JVMMemory.OldGenUsageCritical` | `HealthCheck.JVMMemoryPressure` | P0 | avg > **85%** for 2m | [sop-memory-gc.md](sop-memory-gc.md) |
| 3 | `Node.Disconnected` | `HealthCheck.ClusterUnhealthy` | P0 | disconnected nodes > 0 for 10m | [sop-cluster-health.md](sop-cluster-health.md) |
| 4 | `CPU.PersistUsageHigh` | `HealthCheck.CPULoadHigh` | P0/P1 | avg > **70%** (P0) / > **60%** (P1) for 10m | [sop-cpu-load.md](sop-cpu-load.md) |
| 5 | `JVMMemory.GCRateTooHigh` | `HealthCheck.JVMMemoryPressure` | P1 | Old GC > **1/min** for 10m | [sop-memory-gc.md](sop-memory-gc.md) |
| 6 | `Disk.UsageCritical` | `HealthCheck.DiskUsageHigh` | P0 | max > **85%** for 5m | [sop-disk-storage.md](sop-disk-storage.md) |
| 7 | `JVMMemory.OldGenUsageHigh` | `HealthCheck.JVMMemoryPressure` | P1 | avg > **75%** for 5m | [sop-memory-gc.md](sop-memory-gc.md) |
| 8 | `ThreadPool.WriteRejected` | `HealthCheck.ThreadPoolSaturation` | P0 | write rejected > 0.1/s and TPS > 1/s | [sop-write-performance.md](sop-write-performance.md) |
| 9 | `JVMMemory.GCTimeRatioTooHigh` | `HealthCheck.JVMMemoryPressure` | P0 | GC time / wall clock > **10%** for 5m | [sop-memory-gc.md](sop-memory-gc.md) |
| 10 | `ThreadPool.WriteQueueHigh` | `HealthCheck.ThreadPoolSaturation` | P0 | write queue > threads×80% for 5m | [sop-write-performance.md](sop-write-performance.md) |
| 11 | `ThreadPool.SearchRejected` | `HealthCheck.ThreadPoolSaturation` | P0 | search rejected > 0.1/s and QPS > 1/s for 5m | [sop-query-thread-pool.md](sop-query-thread-pool.md) |
| 12 | `Balancing.NodeCPUUnbalanced` | `HealthCheck.LoadUnbalanced` | P1 | CPU CV > **0.3** for 10m | [sop-cpu-load.md](sop-cpu-load.md) |
| 13 | `Disk.UsageHigh` | `HealthCheck.DiskUsageHigh` | P1 | max > **75%** for 10m | [sop-disk-storage.md](sop-disk-storage.md) |
| 14 | `ThreadPool.SearchQueueHigh` | `HealthCheck.ThreadPoolSaturation` | P0 | search queue > threads×80% for 5m | [sop-query-thread-pool.md](sop-query-thread-pool.md) |
| 15 | `Cluster.StatusRed` | `HealthCheck.ClusterUnhealthy` | P0 | ClusterStatus == 2 for 2m | [sop-cluster-health.md](sop-cluster-health.md) |


---

## 1. Cluster health (3 reason codes)

**Event code:** `HealthCheck.ClusterUnhealthy`


| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `Cluster.StatusRed` | **P0** | `ClusterStatus == 2` for **2m** | 1 | `ClusterStatus` | Node loss / disk full / allocation misconfiguration |
| `Cluster.StatusYellow` | P1 | `ClusterStatus == 1` for **30m** | 2 | `ClusterStatus` | Too few nodes / disk pressure / change in progress |
| `Node.Disconnected` | **P0** | `ClusterDisconnectedNodeCount > 0` for **10m** | 3 | `ClusterDisconnectedNodeCount` | OOM / CPU pegged / disk full / network |


> **Log-based (no CMS rule):** `Cluster.UnavailableShards` — `UnavailableShardsException` in logs, primary inactive; same **event code** `HealthCheck.ClusterUnhealthy`.

**Metric source:** `ClusterStatus`, `ClusterDisconnectedNodeCount` from CMS (`fetch_metrics_batch`).

---

## 2. Master stability (3 reason codes)

**Event code:** `HealthCheck.MasterStabilityRisk`


| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `Master.TasksPendingCritically` | **P0** | `pending_tasks > node_count×50` for **3m** | 4 | metric TBD | Small master / huge shard count / ILM backlog |
| `Master.TasksPendingHigh` | P1 | `pending_tasks > 50` for **5m** | 5 | same | Same, early warning |
| `Master.ElectionTooMany` | **P0** | Master elections > 0 in 1h | 6 | same | Master OOM / network / CPU pegged / long GC pauses |


> **Metric status:** `ClusterPendingTasksCount`, `MasterElectionCount` not in CMS yet — collect via ES API (`GET _cluster/pending_tasks`, `GET _cat/master`).

---

## 3. Service availability (1 reason code)

**Event code:** `HealthCheck.ClusterRequestError`


| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `Cluster.RequestErrorTooHigh` | P1 | HTTP 5xx rate > **5%** and QPS > 1/s for **3m** | 7 | ClusterRequest5xxQPS | Version bug / resource exhaustion / metadata issues |


> Historical typo `Cluster.RequstErrorTooHigh` may appear in older exports; canonical name: **`Cluster.RequestErrorTooHigh`**.

---

## 4. Resource anomalies (17 reason codes)

### 4.1 JVM memory pressure

**Event code:** `HealthCheck.JVMMemoryPressure`


| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `JVMMemory.OldGenUsageHigh` | P1 | heap avg > **75%** for **5m** | 8 | `NodeHeapMemoryUtilization` | Small heap / heavy queries / fielddata / leak |
| `JVMMemory.OldGenUsageCritical` | **P0** | heap avg > **85%** for **2m** | 9 | `NodeHeapMemoryUtilization` | Same, more urgent |
| `JVMMemory.HeapGrowthRateFast` | P1 | +9% in 3m and +15% in 15m | 10 | `NodeHeapMemoryUtilization` | Bulk queries / leak / traffic spike |
| `JVMMemory.GCRateTooHigh` | P1 | Old GC > **1/min** for **10m** | 17 | `JVMGCOldCollectionCount` | Heap pressure / fielddata / large aggs |
| `JVMMemory.GCTimeRatioTooHigh` | **P0** | GC time / wall clock > **10%** for **5m** | 18 | `JVMGCOldCollectionDuration` | Old Gen pressure / frequent Full GC |
| `JVMMemory.GCDurationTooLong` | **P0** | avg GC duration > 5000ms | 19 | `JVMGCOldCollectionDuration` | Bad G1 tuning / large heap objects |
| `JVMMemory.FielddataCacheTooLarge` | P1 | Fielddata > 30% heap | 20 | metric TBD | text field aggs / unbounded fielddata |
| `JVMMemory.BreakerTripped` | **P0** | breaker trips ≥ 5 per 5m | 35 | metric TBD | Huge result sets / fielddata blow-up / heavy aggs |
| `JVMMemory.BreakerLimitConfigLow` | P2 | `indices.breaker.fielddata.limit` < 40% (settings check, ES API) | — | `GET /_cluster/settings` | Limit below recommendation — small aggs can trip |
| `JVMMemory.OOM` | **P0** | `OutOfMemoryError` in logs | — | instance logs | OldGen full / fielddata explosion |


### 4.2 High CPU

**Event code:** `HealthCheck.CPULoadHigh`


| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `CPU.PeakUsageHigh` | P1 | CPU P99 > **95%** for **3m** | 11 | `NodeCPUUtilization` | Heavy queries / ingest / GC / imbalance |
| `CPU.PersistUsageHigh` (P0) | **P0** | CPU avg > **70%** for **10m** | 12 | `NodeCPUUtilization` | Sustained load — node loss risk |
| `CPU.PersistUsageHigh` (P1) | P1 | CPU avg > **60%** for **10m** | 12 | `NodeCPUUtilization` | Same, warning band |
| `CPU.UsageGrowthRateFast` | P0 | +9% in 3m and +15% in 15m | 15 | `NodeCPUUtilization` | Slow requests / burst traffic |


> `CPU.PersistUsageHigh` uses dual thresholds: avg > 70% → P0, 60–70% → P1 (same **reason_code**, different **priority**).

### 4.3 Disk utilization

**Event code:** `HealthCheck.DiskUsageHigh`


| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `Disk.UsageHigh` | P1 | max > **75%** for **10m** | 13 | `NodeDiskUtilization` | Data growth / snapshots not cleaned |
| `Disk.UsageCritical` | **P0** | max > **85%** for **5m** | 14 | `NodeDiskUtilization` | Near ES flood-stage (~95%) read-only |
| `Disk.UsagePredictiveRisk` | P1 | `predict_linear` shows < 5% free in 24h | 22 | `NodeDiskUtilization` | Upward trend |
| `Disk.IndexReadOnly` | **P0** | block count > 0 | 36 | ClusterIndexWritesBlocked | Disk ≥95% auto read-only |
| `Disk.WatermarkAbsoluteFloodBreached` | **P0** | free bytes < absolute `flood_stage` | — | ES API: `_cluster/settings` + `_cat/allocation` | Absolute watermark tripped |
| `Disk.WatermarkAbsoluteFloodMarginLow` | P1 | free space barely above flood_stage (margin < 500MB) | — | ES API: same | Absolute watermark, tiny margin |
| `Disk.WatermarkAbsoluteValue` | P1 | watermarks configured as absolute bytes (not %) | — | ES API: `_cluster/settings` | Non-default — does not scale with disk growth |


### 4.4 Disk IO

**Event code:** `HealthCheck.DiskIOBottleneck`


| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `Disk.IOPerformancePoor` | **P0** | IO util > **90%** for **5m** | 19 | `NodeStatsDataDiskUtil` | Slow disk / bad disk / heavy write / merges |
| `Disk.IOBandwidthThrottling` | **P0** | disk bandwidth util > **90%** for **5m** | 16 | NodeStatsDataDiskIoCloudDiskBaseBandwidthRate | Cloud disk cap / concentrated write |


> IO rule priority was P1 → updated to **P0** (rule #19).

### 4.5 File descriptors

**Event code:** `HealthCheck.SystemFileDescriptorsHigh`


| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `System.FileDescriptorsUsageHigh` | **P0** | open_fd / max_fd > **90%** for **10m** | 21 | metric TBD | Too many connections / shards / leaks |


---

## 5. Performance bottlenecks (10 reason codes)

### 5.1 Thread pool saturation

**Event code:** `HealthCheck.ThreadPoolSaturation`


| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `ThreadPool.SearchQueueHigh` | **P0** | search queue > threads×80% (or > 100) for **5m** | 23 | SearchThreadpoolQueue | Slow queries / high QPS / low CPU headroom |
| `ThreadPool.SearchRejected` | **P0** | search rejected > 0.1/s and QPS > 1/s for **5m** | 24 | SearchThreadpoolRejected | Queue full — new searches rejected |
| `ThreadPool.WriteQueueHigh` | **P0** | write queue > threads×80% (or > 100) for **5m** | 25 | WriteThreadpoolQueue | Heavy ingest / slow disk / low CPU |
| `ThreadPool.WriteRejected` | **P0** | write rejected > 0.1/s and TPS > 1/s for **5m** | 26 | WriteThreadpoolRejected | Queue full — writes rejected (HTTP 429) |
| `ThreadPool.GenericQueueHigh` | P1 | generic queue > threads×80% for **10m** | 27 | metric TBD | High recovery concurrency / `node_concurrent_recoveries` too high |


### 5.2 High latency

**Event code:** `HealthCheck.LatencyHigh`


| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `Latency.IndexingSlow` | **P0** | indexing latency > 1000ms and QPS > 5/s for **1m** | 28 | ClusterIndexingLatency | Slow disk / CPU / aggressive refresh |
| `Latency.SearchSlow` | **P0** | search latency > 2000ms and QPS > 5/s for **1m** | 29 | ClusterSearchLatency | Slow queries / CPU / memory / cold data |
| `Latency.SearchTaskRunningLong` | P1 | search task runtime > 5 minutes | 30 | metric TBD | delete_by_query / reindex / heavy aggs |
| `Latency.RefreshSlow` | P1 | refresh > 1000ms for **5m** | 31 | metric TBD | Too many segments / many fields / complex mappings |


### 5.3 Slow recovery

**Event code:** `HealthCheck.RecoverySlow`


| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `Recovery.SlowWarning` | Info | recovery rate < 50% of configured cap or ETA > 4h | 45 | metric TBD | Low recovery throttle / slow disk / limited bandwidth |


---

## 6. Capacity planning (6 reason codes)

### 6.1 Shard misconfiguration

**Event code:** `HealthCheck.ShardMisconfigured`


| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `Shard.SegmentCountTooMany` | P1 | segments > 100 per node for **30m** | 32 | metric TBD | Rare forcemerge / short refresh interval |
| `Shard.TotalCountTooMany` | P1 | total shards > nodes×CPU×20 for **1h** | 41 | `ClusterShardCount` | Too many indices / shards per index |
| `Shard.SizeUnreasonable` | P2 | avg shard < 10GB or > 50GB for **1h** | 42 | metric TBD | Wrong shard count / bad sizing |
| `Shard.DocumentNearLimit` | **P0** | docs per shard > 2B (Lucene ~2.1B cap) for **30m** | 43 | metric TBD | No rollover / ILM |
| `Shard.NodeCountTooHigh` | P1 | shards per node > 1000 for **30m** | 44 | metric TBD | Too many shards / too few nodes |


### 6.2 Load imbalance

**Event code:** `HealthCheck.LoadUnbalanced`

> Imbalance spans **traffic**, **data placement**, and **resource levels**. See [sop-node-load-imbalance.md](sop-node-load-imbalance.md).

| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `Balancing.NodeCPUUnbalanced` | P1 | CPU CV > **0.3** for **10m** | 40 | `NodeCPUUtilization` | Hot shards / no coordinating nodes / skew |
| `Balancing.NodeTrafficUnbalanced` | P1 | QPS/TPS CV > **0.3** for **10m** | — | thread pool active/queue | No coordinating nodes / uneven clients / routing skew |
| `Balancing.NodeDataUnbalanced` | P2 | shard count or store CV > **0.3** for **30m** | — | `_cat/allocation` | New nodes / large index concentration / routing skew |
| `Balancing.NodeDiskUnbalanced` | P1/P0 | disk util CV > **0.3**, hot node >75% (P1) / >85% (P0) | — | `NodeDiskUtilization` | Large shards on few nodes / old data |
| `Balancing.NodeMemoryUnbalanced` | P1 | heap util CV > **0.3** and max node > **75%** for **10m** | — | `NodeHeapMemoryUtilization` | Fielddata skew / hot query caches |


---

## 7. High-availability risk (4 reason codes)

### 7.1 Cluster scale

**Event code:** `HealthCheck.ClusterScaleLow`


| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `Scale.NodesInsufficient` | P1 | total nodes < 3 for **10m** | 33 | `ClusterNodeCount` | Nodes lost / under-provisioned |
| `Scale.MasterEligibleNodesInsufficient` | P1 | master-eligible < 3 for **5m** | 39 | metric TBD | No dedicated masters / master nodes down |


### 7.2 Missing replication

**Event code:** `HealthCheck.ReplicationMissing`


| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `Replication.MissingReplicas` | P1 | index with 0 replicas and no snapshot | 37 | metric TBD | Manual setting / leftover during resize |


### 7.3 Backup failure

**Event code:** `HealthCheck.BackupFailure`


| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `Backup.SnapshotFailed` | **P0** | auto snapshot status == 2 (failed) | 34 | `ClusterAutoSnapshotLatestStatus` | Space / permissions / cluster load |
| `Backup.SnapshotOutdated` | P2 | no successful snapshot for **24h** | 38 | metric TBD | Policy missing / repeated failures |


---

## 8. Configuration risk (3 reason codes)

**Event code:** `HealthCheck.ConfigurationRisk`


| Reason code | Priority | Trigger | Rule # | Key metrics | Typical root cause |
| ----------- | -------- | ------- | ------ | ----------- | ------------------ |
| `Config.JVMGCStrategyNotOptimal` | Info | Old GC rate > 1/min for **30m** | 46 | `JVMGCOldCollectionCount` | CMS instead of G1 / wrong heap sizing |
| `Config.RiskClusterSettings` | P1 | `concurrent_rebalance > 16` or `concurrent_recoveries > 8` or `recovery > 200MB/s` | 47 | metric TBD | Ops tuned migration too hot for nodes |
| `Config.RiskndexSettings` | P1 | Ngram `max_gram > 100`, or too many shards on small index, or 0 replicas without snapshot | 48 | metric TBD | Bad Ngram / shard planning |


---

## Appendix A: Threshold cheat sheet (health script subset)

Thresholds implemented in `scripts/check_es_instance_health.py` (baseline 20260318) may differ slightly from CMS-only rule numbers below — use the script `THRESHOLDS` for ground truth.


| Metric | Warning (P1) | Critical (P0) | reason_code |
| ----------- | ------------- | ------------- | ----------- |
| Heap utilization | avg > **75%** | avg > **85%** | `JVMMemory.OldGenUsageHigh` / `Critical` |
| CPU sustained | avg > **60%** | avg > **70%** | `CPU.PersistUsageHigh` |
| CPU peak | — | max ≥ **95%** (with sustained avg ≤ 60%) | `CPU.PeakUsageHigh` (P0); 80–94% band → P1 |
| Disk utilization | max > **75%** | max > **85%** | `Disk.UsageHigh` / `Critical` |
| Disk IO util | — | max > **90%** | `Disk.IOPerformancePoor` |
| Old GC rate | > **1/min** (max in window) | — | `JVMMemory.GCRateTooHigh` |
| GC time ratio | — | > **10%** of wall time | `JVMMemory.GCTimeRatioTooHigh` |
| CPU imbalance CV | CV > **0.3** (with CPU floor) | — | `Balancing.NodeCPUUnbalanced` |


---

## Appendix B: How metrics are collected

### Available via CMS `fetch_metrics_batch`

> References: [Basic metrics (Alibaba Cloud Help)](https://help.aliyun.com/zh/es/user-guide/basic-metrics) |
> [Cluster metrics guide](https://help.aliyun.com/zh/es/user-guide/metrics-and-exception-handling-suggestions)

```
ClusterStatus                   Cluster health (0=Green, 1=Yellow, 2=Red)
ClusterAutoSnapshotLatestStatus Snapshot status (-1=none/0=ok/1=running/2=failed)
ClusterDisconnectedNodeCount    Disconnected node count
ClusterNodeCount                Node count
ClusterShardCount               Total shard count
ClusterQueryQPS                 Cluster search QPS
ClusterIndexQPS                 Cluster indexing QPS
ClusterSearchLatency            Avg search latency (ms)
ClusterIndexingLatency          Avg indexing latency (ms)
ClusterSlowSearchingCount       Slow query count
NodeCPUUtilization              Node CPU (%)
NodeHeapMemoryUtilization       Node heap (%)
NodeDiskUtilization             Node disk (%)
NodeFreeStorageSpace            Free storage (MiB)
NodeLoad_1m                     1m load
NodeStatsDataDiskUtil           Disk IO utilization (%)
NodeStatsDataDiskRm             Disk read bandwidth (MiB/s)
NodeStatsDataDiskWm             Disk write bandwidth (MiB/s)
NodeStatsDataDiskR              Read IOPS
NodeStatsDataDiskW              Write IOPS
JVMGCOldCollectionCount         Old GC count (per sample bucket)
JVMGCOldCollectionDuration      Old GC duration ms (per sample bucket)
NodeStatsFullGcCollectionCount  Full GC count
NodeStatsExceptionLogCount      Exception log count
...
```

### Requires additional ES API (for deeper diagnosis)

```bash
# Thread pools (ThreadPool.*)
GET _nodes/stats/thread_pool?filter_path=nodes.*.thread_pool

# Breakers (JVMMemory.BreakerTripped)
GET _nodes/stats/breaker

# Heap / mem (JVMMemory.FielddataCacheTooLarge)
GET _nodes/stats/jvm?filter_path=nodes.*.jvm.mem

# Running tasks (Latency.SearchTaskRunningLong)
GET _tasks?detailed=true

# Pending tasks (Master.TasksPending*)
GET _cluster/pending_tasks

# Shard states (Cluster.StatusRed/Yellow)
GET _cat/shards?v&s=state&h=index,shard,prirep,state,node,unassigned.reason

# Unassigned reason
GET _cluster/allocation/explain

# Recovery (Recovery.SlowWarning)
GET _cat/recovery?v&active_only=true

# Snapshots (Backup.*)
GET _cat/snapshots?v

# ILM (often tied to Master.TasksPending*)
GET _ilm/status

# Read-only blocks (Disk.IndexReadOnly / watermarks)
GET _all/_settings?filter_path=*.settings.index.blocks
# or
GET _cat/indices?v&h=index,status,health

# Watermarks (Disk.WatermarkAbsolute*)
GET _cluster/settings?include_defaults=true&filter_path=**.watermark,**.flood_stage
GET _cat/allocation?format=json&bytes=b
```
