# SOP: Ingest performance and write thread pools

**Covers:** `ThreadPool.WriteRejected` (P0), `ThreadPool.WriteQueueHigh` (P0), `Performance.IndexLatencyHigh` (P0), `Performance.IndexingDropped` (P0)

*(Frequency notes refer to internal case statistics — align names with your rule catalog.)*

---

## Diagnosis decision tree

```
Ingest symptoms
├── HTTP 429 "Too Many Requests" → write pool rejection (WriteRejected)
├── Ingest QPS drops > ~50% → IndexingDropped
├── Ingest latency above SLO → IndexLatencyHigh
└── Writes fail with index read-only → disk flood / blocks → [sop-disk-storage.md](sop-disk-storage.md)

Thread pools
└── GET _nodes/stats/thread_pool → write / bulk queue + rejected
```

---

## 1. Write thread-pool queue buildup (`WriteQueueHigh`, P0)

### Inspect

```bash
GET _nodes/stats/thread_pool?filter_path=nodes.*.thread_pool.write,nodes.*.name
# queue = depth now; rejected = cumulative rejects
```

### Root causes

**A — Ingest QPS exceeds capacity**

- **Signals:** `write` queue grows with traffic.  
- **Mitigate:** short term — lower client QPS; **fewer round-trips** via larger bulks **only when** each bulk stays within a safe payload (see **§2 Bulk guidelines** — avoid **oversized** single requests that time out); long term — **scale out**.

**B — Slow disk IO backs up writes**

- **Signals:** high `write` queue **and** high disk utilization (e.g. `NodeStatsDataDiskUtil`).  
- **Mitigate:** [sop-disk-storage.md](sop-disk-storage.md) (IO + watermarks).

**C — Merges steal CPU / IO**

- **Signals:** `hot_threads` shows merge; queue high without extreme QPS.  
- **Mitigate:** cap merge scheduler threads (see [sop-disk-storage.md](sop-disk-storage.md) / [sop-configuration.md](sop-configuration.md)); reduce segment pressure.

**D — `refresh_interval` too aggressive**

- **Signals:** `refresh_interval` at **1s** or **100ms** on heavy ingest.  
- **Mitigate:**

```bash
PUT /index_name/_settings
{
  "index.refresh_interval": "30s"
}
```

Tune to the freshness your product actually needs.

**E — Too few nodes for concurrent writers**

- **Signals:** (ingest QPS × payload) / node count exceeds per-node sustainable rate.  
- **Mitigate:** add nodes.

### Raising the write queue (usually a poor long-term fix)

Parameter names and supported pools **vary by version** — confirm in your distribution before applying.

```bash
PUT _cluster/settings
{
  "transient": {
    "thread_pool.write.queue_size": 1000
  }
}
```

Prefer **fewer, larger bulks** and **more capacity** over permanently huge queues.

---

## 2. Write thread-pool rejections (`WriteRejected`, P0)

### Symptoms

- Clients: **`HTTP 429 Too Many Requests`**  
- Logs: `rejected execution of ...` (wording varies)

### Immediate response

**1) Thread pool snapshot**

```bash
GET _cat/thread_pool?v&h=name,node_name,active,queue,rejected
# inspect write / bulk rows
```

**2) Pattern**

- **Sustained** buildup → cluster **over capacity** → scale or cut traffic.  
- **Spiky** rejects → tune client: **fewer parallel** bulk streams first; then adjust **docs / payload per bulk** within safe upper bounds (not “always bigger bulks”).

**3) Client-side (most direct)**

- **First:** cap **parallel** bulk workers / connections (reject storms often come from concurrency × retries).  
- Target **~5–15 MB** per bulk request (depends on doc size); **oversized** bulks risk **single-request timeouts** and long write stalls — balance **fewer requests** vs **per-request cap**.  
- Retries with **exponential backoff** on 429.

### Bulk guidelines

```text
Payload per bulk: often ~10–30 MB (adjust for doc size)
Docs per bulk: often ~500–2000 (if each doc is small)
Parallel bulks: often ≤ ~2× node count (validate under load)

Heuristic:
  - Low CPU but many rejects → too much parallelism → reduce parallel bulks / client connections
  - High CPU but slow ingest → bulks may be too small → increase docs per bulk only if each request
    stays below a safe max size (avoid monster single bulks)
```

### Evidence interpretation: bulk QPS → write pool

**When this applies:** `ThreadPool.WriteRejected` (or equivalent alerts), `_nodes/stats/thread_pool` shows **`write`** queue / **`rejected`**, and/or **`hot_threads`** shows **`TransportShardBulkAction`**, **`IndexShard`**, **`DocumentParser`**. Typical chain: **high bulk QPS → write-pool saturation** (queue buildup, **`rejected`** counters, bulk/index stacks in **`hot_threads`**, often concurrent merges).

**Primary evidence (prefer over a generic “JVM-only” story):**

| Layer | What to cite |
|-------|----------------|
| Thread pools | `GET _nodes/stats/thread_pool` — `write` **queue**, **active**, **`rejected`** |
| Hot threads | `GET _nodes/hot_threads` — **`TransportShardBulkAction`**, indexing, **`DocumentParser`** |
| Merges | Often concurrently: **`ConcurrentMergeScheduler`** / **`IndexWriter`** / Lucene merge stacks after heavy writes |

**One-line causal chain for reports:** **bulk → write-thread saturation → segment merges → CPU**. **Old GC / heap pressure** from CMS or `JVMMemory.*`-style rules may appear as **concurrent or downstream** stress from indexing+merges—treat as **additive**, not a substitute headline when **`write` / bulk** evidence is clear.

**Report ordering when `ThreadPool.WriteRejected` and JVM P0 both fire (e.g. acceptance / high-QPS-bulk scenarios):** Do **not** imply “GC first, ingest second.” Use one of:

- **Causal chain (recommended for write-queue prompts):** **write overload / `rejected` → client retries → merge + heap pressure → Old GC STW + CPU / IO spikes** — `write` path is the **first** mechanism link; put **`write.rejected` / bulk saturation in the first sentence** of the conclusion when the prompt centers on **queue full / write reject**.  
- **Dual P0 headlines:** **`ThreadPool.WriteRejected` (P0)** and **`JVMMemory.GCTimeRatioTooHigh` / Old-gen pressure (P0)** as **co-equal** critical findings; order **write / bulk** before **GC** in the body so the summary matches the one-line conclusion.

**Quantification (rubric-friendly):** Beside **“cumulative large”**, add **concrete counters** from **`_nodes/stats/thread_pool`**: per-node **`write.rejected`** and **`write.completed`** (same pool), optional **reject share** (roughly `rejected / (rejected + completed)`) on the hottest node(s). When aligning to control plane / CMS, cite **rule or event names** (e.g. **`ThreadPool.WriteRejected`**, **`HealthCheck.ThreadPoolSaturation`**) in addition to ES API stats.

**Rule-engine alignment:** `scripts/check_es_instance_health.py` **promotes `ThreadPool.WriteRejected` from P1 → P0** when **`JVMMemory.GCTimeRatioTooHigh`** is present in the same run, and includes **`completed_total` / `completed_by_node`** beside **`rejected`** for reject-share context — keep **human-written** conclusions in the same order as this subsection. Treat promotion as a **label heuristic for co-occurring P0 signals**; confirm **写入 workload** (ingest-heavy vs mixed) with **`hot_threads`** / **`_tasks`** before a strict write→GC causal chain.

**`rejected` semantics:** `thread_pool.write.rejected` (and `bulk` where present) is **cumulative since each data node JVM process started** — **not** “last 120 minutes” unless you show a **delta** between two samples. Say **“cumulative since node start”** in customer-facing summaries to avoid window misread (see also **§1 Inspect** above).

**Per-node asymmetry:** The node with the busiest **`write`** activity in **`hot_threads`** may **not** be the node with the highest **`rejected`** count—**primary shard placement, coordinating/ingest paths, and per-node stats need not align.** Add **one sentence** when both are cited to avoid false contradictions.

**Search-path hypotheses:** Under **write-only** overload, **deprioritize** fielddata / heavy-aggregation root causes. Open **`_nodes/stats/breaker`** / fielddata analysis only if **search**-path signals exist (`search` pool saturation, query rejections, documented read-heavy workload). For mixed CPU/GC symptoms, see [sop-memory-gc.md](sop-memory-gc.md).

---

## 3. High indexing latency (`IndexLatencyHigh`, P0)

### Steps

**Step 1 — Indexing stats**

```bash
GET _nodes/stats/indices/indexing?filter_path=nodes.*.indices.indexing
# index_time_in_millis / index_total ≈ avg indexing time per op (rough)
```

**Step 2 — Common drivers**

| Cause | Clues | Mitigation |
|-------|-------|------------|
| Disk IO | disk metrics high | disk tier / merge limits — [sop-disk-storage.md](sop-disk-storage.md) |
| CPU | CPU high | cheaper mappings, scale out — [sop-cpu-load.md](sop-cpu-load.md) |
| Refresh | very low `refresh_interval` | raise interval for bulk windows |
| Analysis cost | hot threads in analyzer | simplify analyzers / reduce field count |
| Translog `request` durability | fsync every op | `async` + `sync_interval` for bulk (risk tradeoff) |
| Huge documents | multi-MB docs | split fields / shrink payloads |

**Bulk-oriented index settings (example — validate for your ES version)**

```bash
PUT /index_name/_settings
{
  "index": {
    "refresh_interval": "30s",
    "translog": {
      "durability": "async",
      "sync_interval": "30s"
    },
    "merge": {
      "policy": {
        "segments_per_tier": 30,
        "max_merged_segment": "256mb"
      }
    }
  }
}
```

`async` translog is **weaker** durability than `request` — use only when the business accepts the risk.

---

## 4. Field notes (from production)

### A — `refresh_interval` and write timeouts (counter-intuitive band)

**Pattern:** very rich analysis → **large refresh batches**; on some topologies **larger nodes** use **longer effective refresh windows**, so **each refresh flushes more data** and can spike latency → **write timeouts**.

**Mitigation (example from a real case):** shorten the window so each refresh does less work:

```bash
PUT /index/_settings
{
  "index.refresh_interval": "100ms"
}
```

This **conflicts** with the usual “raise `refresh_interval` for ingest” advice — pick based on **measurement** (indexing rate, segment count, p99 write latency). See also [sop-query-thread-pool.md](sop-query-thread-pool.md) Section 4.11 for the **opposite** problem (refresh **too** fast → segment churn).

### B — ILM cold phase blocks writes

**Pattern:** log indices on ILM enter **cold** with **`read_only`** or move to **searchable snapshot / cold storage**; writes after the transition fail.

**Check**

```bash
GET /index_name/_settings
# look for index.blocks.write
```

**Mitigation**

```bash
PUT /index_name/_settings
{
  "index.blocks.write": null
}
```

Use **temporarily** to recover; fix **ILM phase timing** so active writers stay on **hot** tiers, or route writes to the **new** active index.

### C — Queue full but CPU / disk look “fine”

**Pattern:** **many** connections sending **tiny** bulks (e.g. **1–10** docs each).

**Check**

```bash
GET _cat/thread_pool?v&h=name,node_name,active,queue,rejected
GET _nodes/stats?filter_path=nodes.*.process.open_file_descriptors
```

**Mitigate:** fewer connections, **much larger** bulks (e.g. toward **500+** small docs per request when safe). **1000 bulks × 1 doc** is vastly more expensive than **1 bulk × 1000 docs**.

---

## 5. Sudden ingest collapse (`Performance.IndexingDropped`, P0)

### Branching

```text
Ingest drops
├── Same-time drop across many instances → platform / upstream (e.g. shared control plane, network path)
└── Single instance
    ├── Disk full / flood read-only → sop-disk-storage.md
    ├── Node left / shards relocating → sop-cluster-health.md
    ├── Planned change → often temporary; see sop-activating-change-stuck.md if stuck
    └── Client throttle / feature flag → check app logs
```

---

## Appendix: quick commands (ingest)

```bash
GET _cat/thread_pool?v&h=name,node_name,active,queue,rejected
GET _nodes/stats/thread_pool?filter_path=nodes.*.thread_pool.write,nodes.*.name

GET _nodes/stats/indices/indexing

GET _cat/indices?v&h=index,docs.count,indexing.index_total,indexing.index_time,indexing.index_failed

PUT /index_name/_settings
{
  "index.refresh_interval": "30s"
}

PUT /index_name/_settings
{
  "index": {
    "translog": {
      "durability": "async",
      "sync_interval": "30s"
    }
  }
}

PUT _cluster/settings
{
  "transient": {
    "indices.merge.scheduler.max_thread_count": 1
  }
}
```
