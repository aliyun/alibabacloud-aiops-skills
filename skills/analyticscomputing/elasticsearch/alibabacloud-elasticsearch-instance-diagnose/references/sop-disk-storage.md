# SOP: Disk watermarks and IO bottlenecks

**Covers:** `ResourceMonitor.DiskUsageWarning` (P1), `ResourceMonitor.DiskUsageCritical` (P0), `ResourceMonitor.DiskIOBottleneck` (P1), and **`DiskWatermarkConfigAnomaly`**-class cases (P0/P1; see **Section 3**)

CMS metric names are examples — align thresholds with [health-events-catalog.md](health-events-catalog.md) and your deployment.

---

## Diagnosis decision tree

```
Disk space (e.g. NodeDiskUtilization)
├── max > ~95% → DiskUsageCritical (P0); flood-stage / read-only imminent or active
├── max > ~85% → DiskUsageWarning (P1); plan cleanup / expansion
├── Logs contain "watermark" → watermark path
└── Utilization looks fine but writes fail → MUST check watermark settings (absolute-byte injection)

Cluster watermark settings (_cluster/settings)
├── Watermarks use absolute values (e.g. "19605mb") → misconfiguration risk (P1); compare to free space
├── Watermark percentages extremely low (e.g. < ~5%) → misconfiguration (P1); easy write block
└── _all/_settings has read_only_allow_delete: true → flood protection active (P0)

Disk performance (use multiple signals)
├── IO utilization (NodeStatsDataDiskUtil) near 100% → device saturated
├── Bandwidth rate (NodeStatsDataDiskIoCloudDiskBaseBandwidthRate) near 100% → throughput cap
└── IOPS rate (NodeStatsDataDiskIoCloudDiskBaseIopsRate) near 100% → random-IO cap
→ Any one near 100% supports an IO bottleneck diagnosis (combine with workload context)

Write failures
├── Logs: "index read-only" / blocks.read_only_allow_delete → flood-stage protection
└── Disk % normal + bad watermarks → config-driven block (disk not “actually full”)
```

---

## 1. Disk usage warning (`DiskUsageWarning`, ~85%+)

### Response time

Within **~2 hours** by policy — treat as **urgent** in practice to avoid escalation to Critical.

### Steps

**Step 1 — Per-node disk**

```bash
GET _cat/allocation?v
GET _cat/nodes?v&h=name,ip,disk.used_percent,disk.avail,disk.total
```

**Step 2 — Largest indices**

```bash
GET _cat/indices?v&s=store.size:desc&h=health,status,index,docs.count,store.size,pri.store.size
```

**Step 3 — Cleanup options**

| Action | How | Notes |
|--------|-----|-------|
| Drop expired indices | `DELETE /old_index_name` | Confirm with the app owner |
| Drop `.monitoring-*` | `DELETE /.monitoring-*` | Loses built-in monitoring history in-cluster |
| Lower replicas | `PUT /index/_settings` → `number_of_replicas: 0` | Temporary; reduces redundancy |
| Prune old snapshots | `GET _cat/snapshots` then `DELETE /_snapshot/repo/snap` | Confirm backups are not needed |
| Expand disk | Console / provider API | Brief impact during resize |

**Step 4 — Alerting** so the next incident is not a surprise.

---

## 2. Critical disk usage (`DiskUsageCritical`, ~95%+)

### Treat as immediate (~5 minutes)

**Elasticsearch disk-based shard routing / flood behavior (typical defaults):**

- Above **~85%** free space low: stop **allocating new shards** to the node (low watermark).  
- Above **~90%**: try to **relocate shards away** (high watermark).  
- Above **~95%** (flood stage): indices on that node may get **`read_only_allow_delete`**.

**Step 1 — Confirm read-only blocks**

```bash
GET _all/_settings?filter_path=*.settings.index.blocks
# or per index
GET /your_index/_settings
```

**Step 2 — Free space urgently**

```bash
DELETE /old_index_name
DELETE /.monitoring-*
PUT /big_index/_settings
{
  "index.number_of_replicas": 0
}
```

**Step 3 — Clear read-only after free space is healthy (often below ~85% on that path)**

```bash
PUT _all/_settings
{
  "index.blocks.read_only_allow_delete": null
}
```

> **Important:** After disk pressure drops, **`read_only_allow_delete` is not always cleared automatically** — you usually must run the command above (Elasticsearch 7.x behavior).

**Step 4 — Temporary watermark relief (buys time only)**

```bash
PUT _cluster/settings
{
  "transient": {
    "cluster.routing.allocation.disk.watermark.low": "95%",
    "cluster.routing.allocation.disk.watermark.high": "98%",
    "cluster.routing.allocation.disk.watermark.flood_stage": "99%"
  }
}
```

> Raising watermarks can **unblock writes briefly** — you must **still reclaim disk** and **revert** to sane defaults afterward.

---

## 3. Disk watermark misconfiguration (`DiskWatermarkConfigAnomaly`, P0/P1)

> **When:** Disk **utilization % looks fine** but watermarks or flood-stage still block writes.

### vs “disk actually full”

| | Disk actually full | Watermark misconfiguration |
|---|-------------------|----------------------------|
| Utilization | High (~85–95%+) | Can be **~1–5%** |
| Root cause | Data growth / retention | `transient` / `persistent` **absolute-byte** watermarks (or absurd %) |
| Typical source | Logs / indices | Scripts, drills, bad copy-paste |
| Trap | Low | **High** if you only glance at `% used` |

### Example chain (absolute-byte flood)

```text
Script sets transient watermarks to absolute free-space requirements
  → flood_stage requires > 19605 MB free
  → only ~19632 MB free (~27 MB headroom)
  → small writes trip flood_stage → read_only_allow_delete on indices
  → writes fail while CMS “disk %” still looks ~4%
```

### Extended write-failure tree

```text
Write failures
├── High disk % (> ~85%) → Sections 1–2 (real capacity)
└── Normal disk % → MUST also:
    ├── GET _cluster/settings?include_defaults=true&filter_path=**.watermark
    │   ├── Absolute-byte watermarks → misconfiguration
    │   └── Absurdly low % watermarks → misconfiguration
    ├── GET _all/_settings?filter_path=*.settings.index.blocks
    │   └── read_only_allow_delete: true → flood already applied
    └── transient vs persistent
        ├── transient → may reset on full-cluster restart; often script residue
        └── persistent → must be cleared explicitly
```

### Steps

**Step 1 — Inspect watermarks**

```bash
GET _cluster/settings?include_defaults=true&filter_path=**.watermark,**.flood_stage
```

Distinguish **absolute** values (`19605mb`, `500gb`) from **percentages** (`85%`). Absolute-byte watermarks on small volumes are a common foot-gun.

**Step 2 — Index blocks**

```bash
GET _all/_settings?filter_path=*.settings.index.blocks
```

If you see `read_only_allow_delete: true`, flood-stage protection is in effect.

**Step 3 — Compare free space to thresholds**

```bash
GET _cat/allocation?v&bytes=mb
```

Compare `disk.avail` to the effective watermark / flood thresholds.

**Step 4 — Remediate**

| Finding | Order | Action |
|---------|-------|--------|
| Bad transient watermarks | 1 | Reset: `PUT _cluster/settings` with `transient` keys set to `null` for `cluster.routing.allocation.disk.watermark.{low,high,flood_stage}` |
| Indices read-only | 2 | `PUT _all/_settings` → `index.blocks.read_only_allow_delete`: `null` (after space / config fixed) |
| Find who set it | 3 | Audit change tickets, automation, load tests |
| Verify | 4 | Test index/write paths |

> **Elasticsearch 7.x:** `read_only_allow_delete` from flood stage often **persists** until cleared manually even after disk recovers.

---

## 4. Disk IO bottleneck (`DiskIOBottleneck`, P1)

### Criteria (example)

- `NodeStatsDataDiskUtil` **> ~80%** for **~5+ minutes**, or  
- Logs show growing write latency / IO wait  

### vs disk space

- **High watermark / flood:** capacity (free space).  
- **IO bottleneck:** performance; disk can be half empty and still saturated.

### Three dimensions (recommended)

> Do not rely on **IO Util alone** — combine **utilization**, **bandwidth %**, and **IOPS %**.

| Dimension | Meaning | CMS utilization metric | Raw / rate metrics | Bottleneck hint |
|-----------|---------|------------------------|--------------------|-----------------|
| **IO Util** | Device busy % | `NodeStatsDataDiskUtil` | — | Near **100%** |
| **Throughput** | MB/s vs cap | `NodeStatsDataDiskIoCloudDiskBaseBandwidthRate` | `NodeStatsDataDiskIoMbPerS` (MiB/s) | Near **100%** |
| **IOPS** | Ops/s vs cap | `NodeStatsDataDiskIoCloudDiskBaseIopsRate` | `NodeStatsDataDiskIo` (count) | Near **100%** |

**If any of the three nears 100%,** narrow the shape of load:

- **IO Util high**, bandwidth/IOPS % not maxed → weak device / heavy queueing / mixed workload.  
- **Bandwidth % maxed**, IO util not maxed → large sequential reads/writes (merge, snapshot, recovery).  
- **IOPS % maxed** → many small random IOs (many shards, chatty queries, small writes).

> Effective caps depend on **disk SKU + size + instance type** (often **min(disk limit, instance limit)**). CMS **%** metrics encode that — you usually do not hand-compute ceilings.

#### CMS metric catalog (namespace `acs_elasticsearch`)

> Discover fields with `DescribeMetricMetaList --Namespace acs_elasticsearch` (Alibaba Cloud Monitor).

| Category | Metric | Unit | Notes |
|----------|--------|------|-------|
| **IO Util** | `NodeStatsDataDiskUtil` | % | Busy time |
| **Throughput — absolute** | `NodeStatsDataDiskIoMbPerS` | MiB/s | Total |
| | `NodeStatsDataDiskRm` / `NodeStatsDataDiskWm` | MiB/s | Read / write |
| **Throughput — %** | `NodeStatsDataDiskIoCloudDiskBaseBandwidthRate` | % | Node-level vs baseline |
| | `NodeStatsDataDiskIoSingleDiskMaxThroughputRate` | % | Per-disk |
| | `NodeStatsDataDiskRmCloudDiskBaseBandwidthRate` | % | Read vs baseline |
| | `NodeStatsDataDiskWmCloudDiskBaseBandwidthRate` | % | Write vs baseline |
| | `NodeStatsDataDiskIoNetworkBaseBandwidthRate` | % | IO network baseline % |
| **IOPS — absolute** | `NodeStatsDataDiskIo` | count | Total IOPS |
| | `NodeStatsDataDiskR` / `NodeStatsDataDiskW` | count | Read / write IOPS |
| **IOPS — %** | `NodeStatsDataDiskIoCloudDiskBaseIopsRate` | % | Node-level |
| | `NodeStatsDataDiskIoSingleDiskMaxIopsRate` | % | Per-disk |
| | `NodeStatsDataDiskRSingleDiskMaxIopsRate` | % | Read |
| | `NodeStatsDataDiskWSingleDiskMaxIopsRate` | % | Write |
| **Queue** | `DiskAverageQueueSize` | count | Avg queue depth |

> **Practical triage:** start with **`NodeStatsDataDiskUtil`**, **`NodeStatsDataDiskIoCloudDiskBaseBandwidthRate`**, **`NodeStatsDataDiskIoCloudDiskBaseIopsRate`** — whichever pegs first drives the story; then use split read/write metrics.

### Causes and mitigations

**Cause A — Heavy ingest**

- Throttle at the source; larger bulk batches (fewer round-trips); relax `refresh_interval` when safe:

```bash
PUT /index_name/_settings
{
  "refresh_interval": "30s"
}
```

**Cause B — Frequent merges (common)**

- Hot threads show **merge** stacks. Short-term:

```bash
PUT _cluster/settings
{
  "transient": {
    "indices.merge.scheduler.max_thread_count": 1
  }
}
```

- Longer term: review `index.merge.policy.*` (e.g. `segments_per_tier`) with version docs — trade merge cost vs segment count.

**Cause C — Hitting disk / instance ceilings**

- **Ceiling ≈ min(disk SKU limit, instance type disk limit).**  
- Example pitfall: upgraded ESSD tier but **no gain** because the **instance** throughput cap dominates.  
- **Order:** confirm which side is saturated from CMS vs quotas → scale **instance** and/or **disk** → if both maxed, **add nodes** to spread IO.

**Cause D — Bad hardware / media errors**

- Logs: `IOException`, `EIO` → replace disk / escalate to infrastructure support.

### Example chain (slow IO → node leaves)

```text
Sustained high IO → slow translog / fsync → slow heartbeat handling → node marked offline
Mitigation: cap merge concurrency + reduce ingest pressure (+ fix disk tier if capped)
```

---

## 5. Data disk vs system disk (field note; not a separate catalog line)

### Data volume full

- **Signals:** watermark logs + high data-disk metrics.  
- **Mitigate:** Sections 1–2.

### Root / system volume full (rare, severe)

- **Signals:** data disk OK but JVM/host misbehaves (cannot write temp files, logs).  
- **Common causes:** core dumps under `/var/crash` or `/tmp`, container image sprawl, huge system logs.  
- **Mitigate:** host cleanup by **SRE / infrastructure**; monitor root mount (e.g. `/` or `/dev/vda1`) in host monitoring, not only Elasticsearch data paths.

---

## 6. Disk issues during changes

### 6.1 High disk + change stuck (`activating`)

Typical story: **disk pressure → user triggers restart → change hangs in `activating`**.

1. Relieve disk (delete / resize / temporary watermark relief per policy).  
2. Let nodes come back cleanly.  
3. If the change is still stuck, use [sop-activating-change-stuck.md](sop-activating-change-stuck.md) and escalate per your support model.

### 6.2 Recovery bandwidth too high → node / FS hang

**Pattern** (cold-tier resize case): new nodes cannot join; shell `cd` into `logs` hangs; cluster stays Yellow/Red.

```text
indices.recovery.max_bytes_per_sec set very high (e.g. 300MB/s)
  → exceeds disk SKU sustained throughput (e.g. ~250MB/s)
  → block layer stalls → filesystem appears hung
  → Elasticsearch cannot flush logs / data → bootstrap fails
```

**Mitigation:**

1. Roll back the change / restore service on surviving nodes if required.  
2. Lower recovery bandwidth to a safe value for the disk class:

```bash
PUT _cluster/settings
{
  "persistent": {
    "indices.recovery.max_bytes_per_sec": "100mb"
  }
}
```

3. Retry the change in a **low-traffic** window.  
4. If on a low baseline disk SKU, plan upgrade to a higher baseline (e.g. ESSD PL1+) per product guidance.

---

## Appendix: Quick commands (disk)

```bash
GET _cat/allocation?v
GET _cat/nodes?v&h=name,ip,disk.used_percent,disk.avail,disk.total

GET _cat/indices?v&s=store.size:desc

DELETE /index_name

GET _all/_settings?filter_path=*.settings.index.blocks
PUT _all/_settings
{
  "index.blocks.read_only_allow_delete": null
}

PUT _cluster/settings
{
  "transient": {
    "cluster.routing.allocation.disk.watermark.low": "95%",
    "cluster.routing.allocation.disk.watermark.high": "98%"
  }
}

PUT _cluster/settings
{
  "transient": {
    "cluster.routing.allocation.disk.watermark.low": null,
    "cluster.routing.allocation.disk.watermark.high": null,
    "cluster.routing.allocation.disk.watermark.flood_stage": null
  }
}

PUT /large_index/_settings
{
  "index.number_of_replicas": 0
}

PUT _cluster/settings
{
  "transient": {
    "indices.merge.scheduler.max_thread_count": 1
  }
}
```
