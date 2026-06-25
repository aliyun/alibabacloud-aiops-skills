# Manual Workflow: Step-by-Step Execution

> **⛔ FOR DEVELOPMENT REFERENCE ONLY — DO NOT USE THESE COMMANDS ⛔**
>
> This document describes the internal API calls made by `health-inspect.py`.
> It exists for developers maintaining the script, NOT for AI agents executing inspections.
>
> **AI agents: ALWAYS use `bash scripts/run-inspect.sh` instead. NEVER call the commands below directly.**
>
> **All `aliyun` commands below use plugin mode (kebab-case action and parameter names). Every command that calls a cloud API MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-health-inspect/{session-id}`.**

## Step 0: Auto-Discover Instance Region

> **Important**: If the user has not provided a Region, auto-discover the instance Region first.

```bash
python3 scripts/find-instance-region.py {DBInstanceId}
```

## Step 1: Get Instance Basic Information & Configuration Risk Assessment

```bash
aliyun dds describe-db-instance-attribute \
  --region {RegionId} \
  --db-instance-id {DBInstanceId}
```

**Key fields to extract:**
- `DBInstanceType` — Instance type (sharding / replicate)
- `EngineVersion` — MongoDB major version
- `CurrentKernelVersion` — Kernel minor version
- `StorageEngine` — Storage engine (WiredTiger / RocksDB)
- `StorageType` — Storage type
- `DBInstanceStatus` — Instance status
- `LockMode` — Lock status (Unlock / ManualLock / LockByExpiration / LockByRestoration / LockByDiskQuota)
- `ChargeType` — Charge type (PostPaid=pay-as-you-go / PrePaid=subscription)
- `ExpireTime` — Expiry time (subscription only)
- `ZoneId` — Availability zone ID (comma-separated = multi-AZ)
- `MaxConnections` / `MaxIOPS` — Connection / IOPS limits
- Node lists:
  - Sharding: `MongosList.MongosAttribute[]` + `ShardList.ShardAttribute[]` + `ConfigserverList.ConfigserverAttribute[]`
  - ReplicaSet: Identified via monitoring data NodeId

### Configuration Risk Assessment Logic

Based on `describe-db-instance-attribute` response, apply these risk rules:

| Check Item | Logic | Risk Level |
|-----------|-------|------------|
| Instance Status | `DBInstanceStatus == "Running"` → ✅; other → 🔴 | Normal/Critical |
| Architecture | Display only, no risk judgment | ✅ Info |
| Storage Engine | Display only (WiredTiger / RocksDB) | ✅ Info |
| Disk Type | `StorageType` contains "local" → ⚠️; "cloud" → ✅ | Normal/Warning |
| Charge Mode/Expiry | Pay-as-you-go → ✅ (remind balance); Subscription & `ExpireTime - now < 30d` → ⚠️; `< 7d` → 🔴 | Normal/Warning/Critical |
| AZ Deployment | `ZoneId` contains comma or multi-Zone → ✅; Single Zone → ⚠️ | Normal/Warning |
| Lock Status | `LockMode == "Unlock"` → ✅; other → 🔴 (with reason) | Normal/Critical |
| MongoDB Version | `EngineVersion` < 4.4 → ⚠️ (suggest upgrade); >= 4.4 → ✅ | Normal/Warning |
| Node Specs | Display node count and spec summary per type | ✅ Info |

## Step 2: Query Resource Usage (Last N Days)

> **Time format**: `describe-db-instance-performance` uses ISO 8601: `yyyy-MM-ddTHH:mmZ`

**Node-level monitoring metric keys (verified):**

| Key | Return Value | Multi-value (`&` separated) |
|-----|--------------|-----------------------------|
| `CpuUsage` | CPU usage (%) | Single |
| `MemoryUsage` | Memory usage (%) | Single |
| `MongoDB_Connections` | Current connections | Single (absolute) |
| `DiskUsage` | Disk usage (%) | Single |
| `IOPSUsage` | IOPS usage (%) | Single |
| `MongoDB_IOPS` | IOPS absolute | total & read & write |
| `MongoDB_MbpsUsage` | Disk bandwidth usage (%) | total & read & write |
| `MongoDB_DetailedSpaceUsage` | Space usage (MB) | total & data & log |
| `MongoDB_Network` | Network traffic | bytes_in & bytes_out & requests |
| `MongoDB_Opcounters` | Operation stats (ops/s) | insert & query & update & delete & getmore & command |

```bash
# Single node CPU
aliyun dds describe-db-instance-performance \
  --region {RegionId} \
  --db-instance-id {DBInstanceId} \
  --node-id {NodeId} \
  --key CpuUsage \
  --start-time "{StartTime}" \
  --end-time "{EndTime}"
```

**Performance data parsing:**

API returns `PerformanceKeys.PerformanceKey[].PerformanceValues.PerformanceValue[]`:
- Each `PerformanceValue.Value` is a string
- Single-value keys: `float(value)` directly
- Multi-value keys: split by `&` and take corresponding index (e.g., `MongoDB_IOPS` read = parts[1])

**Calculating average and peak:**
- Average = sum of all data point Values / number of data points
- Peak = maximum Value among all data points
- Connection usage = peak connections / MaxConnections × 100%

## Step 3: Space Usage TOP 20 Collection (DAS API)

### 3.1 Create Storage Analysis Task

```bash
aliyun das create-storage-analysis-task \
  --instance-id {DBInstanceId} \
  --endpoint das.cn-shanghai.aliyuncs.com
```

Returns `Data.TaskId`.

### 3.2 Wait for Task Completion and Get Results

```bash
aliyun das get-storage-analysis-result \
  --instance-id {DBInstanceId} \
  --task-id {TaskId} \
  --endpoint das.cn-shanghai.aliyuncs.com
```

**Extract TOP 20 collection info:**
Sort by total space and take top 20, including:
- Database name / Collection name
- Total space / Data space / Index space
- Document count / Average document size
- Whether sharded (Sharding instances)

> **Degradation**: If DAS does not support MongoDB space analysis for the current account or region, display "Not supported / Data unavailable" for this section without affecting other items.

## Step 4: Current Sessions (DAS API)

```bash
aliyun das get-mongo-db-current-op \
  --instance-id {DBInstanceId} \
  --node-id {NodeId} \
  --endpoint das.cn-shanghai.aliyuncs.com
```

**Fields to extract:**
- `SessionStat.TotalCount` / `ActiveCount` / `LongestSecsRunning`
- `SessionList[]`: each session's `Op` / `SecsRunning` / `Ns` / `Client` / `Desc`

## Step 5: Slow Log Statistics

```bash
# Sharding: query per Shard NodeId
# ReplicaSet: query at instance level
aliyun dds describe-slow-log-records \
  --region {RegionId} \
  --db-instance-id {DBInstanceId} \
  --node-id {NodeId} \
  --start-time "{StartTime}" \
  --end-time "{EndTime}" \
  --page-size 30 --page-number 1
```

> **Time format**: `yyyy-MM-ddTHH:mmZ`, max 24-hour window per query. The script aggregates by day.

**Slow log return fields:**
- `DBName` — Database name
- `SQLText` — Slow operation summary
- `QueryTimes` — Execution time (ms)
- `ExecutionStartTime` — Execution start time
- `ReturnRowCounts` / `KeysExamined` / `DocsExamined`

## Step 6: Alert History (CloudMonitor)

```bash
aliyun cms describe-alert-history-list \
  --namespace acs_mongodb \
  --start-time {StartTimeMillis} \
  --end-time {EndTimeMillis} \
  --page-size 100
```

> **Degradation**: If the instance region has CMS namespace naming differences, the script falls back to `acs_mongodb_replicate`; if still no results, display "No alerts / Data unavailable".
