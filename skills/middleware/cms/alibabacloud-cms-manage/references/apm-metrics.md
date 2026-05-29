# APM Metric Catalog

> Companion to [alerting.md](alerting.md). All `aliyun cms2 alert rule` APM commands consume these tables.

## Group → Filter / GroupBy Mapping

When constructing `queryConfig.filterList` / `groupBy`, look up the metric's `group` first.

| Group | displayNameCn | Default Filters (dim → type) | groupBy |
|-------|---------------|-------------------------------|--------|
| `apm.host` | 主机监控 (Host) | `rootIp` → ALL | `["rootIp"]` |
| `apm.jvm` | JVM监控 (JVM) | `rootIp` → ALL | `["rootIp"]` |
| `apm.txn` | 应用提供服务统计 (Inbound RPC) | `rpc` → ALL, `rpcType` → ALL | `["rpc","rpcType"]` |
| `apm.txn_type` | 应用依赖服务统计 (Outbound RPC) | `rpcType` → ALL, `destId` → ALL | `["rpcType","destId"]` |
| `apm.pod` | 容器监控 (Pod) | `rootIp` → ALL | `["rootIp"]` |
| `apm.exception` | 异常监控 (Exception) | `rpc` → ALL, `excepName` → ALL | `["rpc","excepName"]` |
| `apm.httpcode` | HTTP状态码 (HTTP status) | `rpc` → ALL, `status` → ALL | `["rpc","status"]` |
| `apm.db` | 数据库指标 (Database) | `endpoint` → ALL | `["endpoint"]` |
| `apm.threadpool` | 线程池监控 (Thread pool) | `ThreadPoolType` → ALL, `ThreadPoolName` → ALL, `rootIp` → ALL | `["ThreadPoolType","ThreadPoolName","rootIp"]` |
| `apm.threadpoolv2` | 新版线程池 (Thread pool v2) | `thread_pool_usage` → ALL, `thread_name_pattern` → ALL, `rootIp` → ALL | `["thread_pool_usage","thread_name_pattern","rootIp"]` |
| `apm.connectionpool` | 连接池监控 (Connection pool) | `pool_type` → ALL, `rootIp` → ALL | `["pool_type","rootIp"]` |
| `apm.scheduler` | 定时任务 (Scheduled task) | `rpc` → ALL | `["rpc"]` |
| `apm.httpclient` | Web依赖 (HTTP client) | `destId` → ALL, `endpoint` → DISABLED | `["destId"]` |

> **Default rule**: All dims default to `ALL` (traverse) unless user specifies a concrete filter value (then use `EQ`).
> **filterList[].type**: `EQ` | `NE` | `ALL` | `DISABLED` | `CONTAIN` | `EXCLUDES` | `=~` | `!~`

---

## User Intent → Metric Quick Reference

Match user intent first; only fall back to the full registry if not listed here.

| User Intent (zh-CN) | measureCode | Group | Unit |
|---------------------|-------------|-------|------|
| CPU 使用率 / CPU usage | `appstat.jvm.SystemCpuUsage` | apm.host | % |
| 内存使用率 / Memory usage | `appstat.jvm.SystemMemUsage` | apm.host | % |
| JVM 堆内存使用率 / Heap usage | `appstat.jvm.HeapUsedRatio` | apm.jvm | % |
| FullGC 次数 / Full GC count | `appstat.jvm.gc.OldGcCountInstant` | apm.jvm | count |
| 线程总数 / Thread count | `appstat.jvm.ThreadCount` | apm.jvm | number |
| 调用次数 / QPS | `appstat.transaction.count` | apm.txn | count |
| 响应时间 / RT | `appstat.transaction.rt` | apm.txn | ms |
| 错误率 / Error rate | `appstat.transaction.errorrate` | apm.txn | % |
| 慢调用 / Slow calls | `appstat.transaction.slowcount` | apm.txn | count |
| Pod CPU 使用量 / Pod CPU | `appstat.pod.SystemCpuTotal` | apm.pod | core |
| Pod 内存使用量 / Pod memory | `appstat.pod.SystemMemUsage` | apm.pod | MB |
| 数据库 RT / DB RT | `appstat.database.rt` | apm.db | ms |
| 异常次数 / Exception count | `appstat.exception.count` | apm.exception | count |
| 线程池使用率 / Thread pool usage | `appstat.threadpool.threadpoolusedpercent` | apm.threadpool | % |
| 连接池连接数 / Active connections | `appstat.connectionpool.active_connection_count` | apm.connectionpool | number |

> **CRITICAL**: `appstat.jvm.cpu` does NOT exist. CPU is in `apm.host` group → `appstat.jvm.SystemCpuUsage`.

---

## Full Metric Registry

### `apm.host` — Node/Host (CPU, Memory, Disk, Load, Network)

`appstat.host.InstanceCount`(JVM instances) `appstat.jvm.SystemCpuUsage`(CPU%) `appstat.jvm.SystemCpuUser`(CPU user%) `appstat.jvm.SystemDiskFree`(free disk MB) `appstat.jvm.SystemDiskUsage`(disk%) `appstat.jvm.SystemLoad`(load) `appstat.jvm.SystemMemFree`(free mem MB) `appstat.jvm.SystemMemUsage`(mem%) `appstat.jvm.SystemNetInBytes`(net in MB) `appstat.jvm.SystemNetInErrs`(in errors) `appstat.jvm.SystemNetInPackets`(in packets) `appstat.jvm.SystemNetOutBytes`(net out MB) `appstat.jvm.SystemNetOutErrs`(out errors) `appstat.jvm.SystemNetOutPackets`(out packets)

### `apm.jvm` — JVM (Heap, GC, Threads, Metaspace)

Heap/Metaspace: `appstat.jvm.HeapUsedRatio`(%) `appstat.jvm.heap_total`(MB) `appstat.jvm.heap_used`(MB) `appstat.jvm.METASPACE`(MB) `appstat.jvm.non_heap_committed`(MB) `appstat.jvm.non_heap_init`(MB) `appstat.jvm.non_heap_max`(MB) `appstat.jvm.non_heap_used`(MB)

GC: `appstat.jvm.GcPsMarkSweepCount` `appstat.jvm.GcPsScavengeCount` `appstat.jvm.gc.OldGcCount` `appstat.jvm.gc.OldGcCountInstant` `appstat.jvm.gc.OldGcTime`(ms) `appstat.jvm.gc.OldGcTimeInstant`(ms) `appstat.jvm.gc.YoungGcCount` `appstat.jvm.gc.YoungGcCountInstant` `appstat.jvm.gc.YoungGcTime`(ms) `appstat.jvm.gc.YoungGcTimeInstant`(ms)

Threads: `appstat.jvm.ThreadCount` `appstat.jvm.ThreadBlockedCount` `appstat.jvm.ThreadDeadlockCount` `appstat.jvm.ThreadNewCount` `appstat.jvm.ThreadRunnableCount` `appstat.jvm.ThreadTerminatedCount` `appstat.jvm.ThreadTimedWaitCount` `appstat.jvm.ThreadWaitCount`

### `apm.txn` — Transaction/RPC

`appstat.transaction.count`(count) `appstat.transaction.error`(count) `appstat.transaction.errorrate`(%) `appstat.transaction.rt`(ms) `appstat.transaction.slowcount`(count)

### `apm.txn_type` — Inbound/Outbound

In: `appstat.incall.count` `appstat.incall.error` `appstat.incall.errorrate`(%) `appstat.incall.rt`(ms)
Out: `appstat.outcall.count` `appstat.outcall.error` `appstat.outcall.errorrate`(%) `appstat.outcall.rt`(ms) `appstat.outcall.slowcount`

### `apm.pod` — Pod resource

`appstat.pod.SystemCpuSystem`(core) `appstat.pod.SystemCpuTotal`(core) `appstat.pod.SystemCpuUser`(core) `appstat.pod.SystemMemUsage`(MB) `appstat.pod.SystemNetInBytes`(MB) `appstat.pod.SystemNetInDrop` `appstat.pod.SystemNetInErrs` `appstat.pod.SystemNetInPackets` `appstat.pod.SystemNetOutBytes`(MB) `appstat.pod.SystemNetOutDrop` `appstat.pod.SystemNetOutErrs` `appstat.pod.SystemNetOutPackets`

### `apm.db` / `apm.txn_db` — Database

`appstat.database.count` `appstat.database.errcount` `appstat.database.rt`(ms) `appstat.database.slowcount`
`appstat.sql.count` `appstat.sql.error` `appstat.sql.rt`(ms)

### `apm.exception` / `apm.httpcode` / `apm.httpclient`

`appstat.exception.count` `appstat.exception.rt`(ms)
`appstat.status.count`
`appstat.httpclient.count` `appstat.httpclient.rt`(ms) `appstat.httpclient.errorrate`(%)

### `apm.connectionpool`

`appstat.connectionpool.active_connection_count` `appstat.connectionpool.max_connection_count` `appstat.connectionpool.max_idle_connection_count` `appstat.connectionpool.min_idle_connection_count` `appstat.connectionpool.pending_request_count`

### `apm.threadpool` (v1)

`appstat.threadpool.threadcorepoolsize` `appstat.threadpool.threadmaxpoolsize` `appstat.threadpool.threadpoolactivecount` `appstat.threadpool.threadpoolqueuesize` `appstat.threadpool.threadpoolsize` `appstat.threadpool.threadpooltaskcount` `appstat.threadpool.threadpoolusedpercent`(%)

### `apm.threadpoolv2`

`appstat.threadpoolv2.max_thread_count` `..._max` `appstat.threadpoolv2.active_thread_count` `..._max` `appstat.threadpoolv2.completed_task_count` `appstat.threadpoolv2.current_thread_count` `..._max` `appstat.threadpoolv2.queue_size` `appstat.threadpoolv2.rejected_task_count` `appstat.threadpoolv2.scheduled_task_count` `appstat.threadpoolv2.used_percent`(%)

### `apm.scheduler`

`appstat.scheduler.count` `appstat.scheduler.delay`(ms) `appstat.scheduler.error` `appstat.scheduler.rt`(ms)

### `apm.saehost` — SAE host

CPU/Mem/Disk/Net: `appstat.infra.sae.SystemCpu`(%) `appstat.infra.sae.SystemDiskRate`(%) `appstat.infra.sae.SystemDiskRead`(B) `appstat.infra.sae.SystemDiskWrite`(B) `appstat.infra.sae.SystemDiskIopsRead` `appstat.infra.sae.SystemDiskIopsWrite` `appstat.infra.sae.SystemLoad` `appstat.infra.sae.SystemMemRate`(%) `appstat.infra.sae.SystemMemTotal`(MB) `appstat.infra.sae.SystemMemUsed`(MB) `appstat.infra.sae.SystemNetRecv`(B) `appstat.infra.sae.SystemNetTran`(B) `appstat.infra.sae.SystemNetRecvDrop` `appstat.infra.sae.SystemNetRecvError` `appstat.infra.sae.SystemNetRecvPacket` `appstat.infra.sae.SystemNetTranDrop` `appstat.infra.sae.SystemNetTranError` `appstat.infra.sae.SystemNetTranPacket`

---

## baseUnit / displayUnit Mapping (PatchAlertRule)

When patching `condition.compareList[].baseUnit/displayUnit` post-CREATE:

| baseUnit | displayUnit | Applicable Metrics |
|----------|-------------|--------------------|
| `percent` | `%` | CPU utilization: `SystemCpuUsage`, `SystemCpuUser`, `infra.sae.SystemCpu` |
| `ratio` | `%` | Usage / error rate: `HeapUsedRatio`, `SystemDiskUsage`, `SystemMemUsage`, `transaction.errorrate`, `threadpoolusedpercent`, `used_percent`, `incall.errorrate`, `outcall.errorrate`, `SystemDiskRate`, `SystemMemRate` |
| `byte` | `MB` | Memory / disk / network bytes: `heap_total`, `heap_used`, `non_heap_*`, `METASPACE`, `SystemDiskFree`, `SystemMemFree`, `SystemNet*Bytes`, `pod.SystemMem*`, `pod.SystemNet*Bytes`, `sae.SystemMem*` |
| `(none)` | `次` / `count` | `GcCount`, `transaction.count`, `.error`, `.slowcount` |
| `(none)` | `毫秒` / `ms` | `GcTime`, `transaction.rt`, `database.rt`, `scheduler.rt` |
| `(none)` | `个` / `number` | `ThreadCount`, `InstanceCount`, `SystemLoad` |
| `(none)` | `核` / `core` | `pod.SystemCpu*` |

> **⚠️ Threshold value — no conversion**: write the user-provided percentage / number as-is (20% → `20`, 80% → `80`). `baseUnit/displayUnit` only drive console rendering and **do not participate in threshold value conversion**.

```json
// User intent: error rate > 20% critical alert
"conditionConfig": {"thresholdList": [{"severity": "CRITICAL", "threshold": 20}]}
// PatchAlertRule:
"condition": {"compareList": [{"valueLevelList": [{"level": "CRITICAL", "value": 20}], "baseUnit": "ratio", "displayUnit": "%"}]}
```

---

## Metric Validation Rule

When user provides a measureCode or describes intent:

1. Match against **User Intent → Metric Quick Reference** first.
2. If exact key provided → validate against **Full Metric Registry**.
3. If NOT found → **STOP**. Show closest matches and use `ask_user_question` for confirmation. Never create with an unverified metric — silent failure in console.
4. If found → note the correct group; use `ask_user_question` only when ambiguous.
