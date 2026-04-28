# SOP: JVM memory, GC, and circuit breakers

**Covers:** `ResourceMonitor.OldGenMemoryWarning` (P0), `ResourceMonitor.OldGenMemoryCritical` (P0), `ResourceMonitor.MemoryRapidGrowth` (P1), `ResourceMonitor.OldGCFrequent` (P1), `ResourceMonitor.GCTimeRatioHigh` (P0), `HighAvailability.CircuitBreakerTriggered` (P0), `ResourceMonitor.OOM` (P0)

CMS / catalog names may differ — align thresholds with [health-events-catalog.md](health-events-catalog.md).

---

## Diagnosis decision tree

```
NodeHeapMemoryUtilization (example)
├── avg > ~95% → OldGenMemoryCritical (P0); OOM imminent
├── avg > ~85% → OldGenMemoryWarning (P0); elevated OOM risk
└── rises > ~30% within ~30m → MemoryRapidGrowth (P1); trend alert

JVMGCOldCollectionCount (per minute)
└── max > ~5 / min → OldGCFrequent (P1)

JVMGCOldCollectionDuration
└── GC time / wall time > ~30% → GCTimeRatioHigh (P0)

Master log keywords
├── OutOfMemoryError / OOM → ResourceMonitor.OOM (P0)
├── Data too large / CircuitBreakingException → circuit breaker (P0)
└── Killed / OOM killer → OS killed the process
```

> **Headline priority (heap / GC vs breakers):** Cluster **Green** does not rule out **JVM pressure**. When rules or logs point to **fielddata**, **`CircuitBreakingException`**, or **artificially low `indices.breaker.*` limits** in **`_cluster/settings`** (**transient** and **persistent**), treat **settings + `_nodes/stats/breaker` (`tripped`) + query/mapping** as the **primary** story — not **Old GC frequency alone** (GC is often a **parallel** or **downstream** signal unless isolated as the driver).  
> **Per-node heap skew:** Uneven **heap percent** across data nodes should be read with **`_nodes/stats/breaker`**, **`_nodes/stats/indices/fielddata`**, **`_cat/shards`** / hot indices, and **query shape** — not **only** “bad shard counts” without breaker and workload context.

> **Co-occurrence with `ThreadPool.WriteRejected` / bulk saturation:** If **`_nodes/stats/thread_pool`** shows **`write` / `bulk` `rejected`** and **`hot_threads`** or traffic points at **ingest**, do **not** headline **Old GC alone** ahead of the write path — use the **causal chain or dual-P0 ordering** in [sop-write-performance.md](sop-write-performance.md) **§2** (*Evidence interpretation: bulk QPS → write pool*). Old GC / `GCTimeRatioTooHigh` remains **P0-class** but is often **downstream** of indexing + merges + retries.

> **Collector names in prose:** Alibaba Cloud ES 7.x often ships **JDK 11** with **G1**, but the **actual** collector is **JVM / image dependent**. Do **not** assert **G1** vs **CMS** from version alone — confirm via **`GET _nodes/stats/jvm`** (`gc.collectors.*`) or node **GC logs**; otherwise write **“old-generation / Old GC”** or **“old GC (collector per JVM stats)”**.

---

## 1. Old-gen memory warning (`OldGenMemoryWarning`, ~85%+)

### Act first (before deep analysis)

**1. Clear caches (often fastest)**

```bash
POST _cache/clear
POST _cache/clear?fielddata=true
# Or per index
POST /index_name/_cache/clear?fielddata=true&query_cache=true&request_cache=true
```

**2. Heap snapshot from the API**

```bash
GET _nodes/stats/jvm?filter_path=nodes.*.jvm.mem,nodes.*.name
# heap_used_percent, old_gen_used_bytes (names vary by version)
```

**3. Fielddata footprint**

```bash
GET _nodes/stats/indices/fielddata?fields=*&filter_path=nodes.*.indices.fielddata
```

### Root causes

**A — Fielddata too large**

- **Signals:** slow logs show **aggregations on `text`** fields  
- **Effect:** fielddata stays on-heap until evicted / cleared  
- **Mitigate:**

```bash
POST /index_name/_cache/clear?fielddata=true
PUT _cluster/settings
{
  "persistent": {
    "indices.fielddata.cache.size": "20%"
  }
}
```

(`indices.fielddata.cache.size` behavior depends on version — confirm in your distribution.)

- **Proper fix:** avoid **`text`** for aggs; use a **`keyword`** sub-field or `doc_values` where appropriate.

**B — Huge aggregations**

- **Signals:** hot threads in agg paths; long-running `_tasks` with search/agg  
- **Mitigate:** cancel runaway tasks; reduce cardinality, bucket count, `size`; consider `execution_hint: map` where supported  

**C — Oversized result sets**

- **Signals:** very large `size`, deep `from + size` (e.g. > 10k)  
- **Mitigate:** cap `size`; use **scroll** or **search_after**  

**D — Very large `terms` queries**

- **Signals:** `terms` with huge ID lists (tens of thousands); hot threads with `TermsQuery` / `TermInSetQuery`  
- **Effect:** large bitsets on heap (default `index.max_terms_count` is **65536**)  
- **Mitigate:**

```bash
GET _tasks?detailed=true&actions=*search*
POST _tasks/{task_id}/_cancel

GET {index}/_settings?filter_path=**.max_terms_count

PUT {index}/_settings
{
  "index.max_terms_count": 10000
}
```

- **Proper fix:** **batch** terms lists (e.g. **< ~1000** per request) or use **`ids`** where applicable.

> **Example:** tens of thousands of IDs in one `terms` query → high heap churn and GC → slow cluster. Fix: smaller batches + app-side chunking.

**E — Undersized heap for the workload**

- **Signals:** “normal” traffic but heap pegged  
- **Mitigate:** scale node RAM / heap per vendor guidance  

---

## 2. Old-gen memory critical (`OldGenMemoryCritical`, ~95%+)

### Emergency sequence

```text
1. POST _cache/clear (all tiers you can afford to drop)
2. Cancel long searches: GET _tasks → POST _tasks/{id}/_cancel
3. Restart affected nodes if still unstable (plan brief outage)
4. After stabilization, find the recurring driver (queries, mappings, breakers)
```

**Cancel large searches**

```bash
GET _tasks?detailed=true&actions=*search*
POST _tasks/{task_id}/_cancel
```

**Restart**

- Use console / automation for the specific node.  
- After restart, confirm `heapPercent` trends flat, not climbing endlessly.  

---

## 3. Frequent old GC (`OldGCFrequent`, P1)

### Criteria (example)

- `JVMGCOldCollectionCount` **max > ~5 / minute**

### Causes

| Cause | Clues | Mitigation |
|-------|-------|------------|
| Old gen pegged (> ~75%) | heap trend | Sections 1–2 |
| Large fielddata | node stats | clear + mapping fix |
| Heavy aggs | slow logs | optimize / throttle |
| G1 never “full” enough to reclaim certain structures | rare JVM / TL patterns | upgrade path or vendor-guided Full GC |

**G1 / `ThreadLocal` stale-entry churn**

G1 may not run a “classic” full GC often; some `ThreadLocal` / weak-reference cleanup paths need a full collection cycle. See **Pattern A** in [sop-cpu-load.md](sop-cpu-load.md) (single-node management thread hot + `expungeStaleEntry`).

---

## 4. High GC time ratio (`GCTimeRatioHigh`, P0)

### Criteria (example)

- **Old GC duration / wall time > ~30%**  
- Users see slow responses; long STW pauses  

### Chain

```text
Old-gen pressure → frequent old-gen collections → long pauses
  → heartbeat lag → node leaves cluster
  → client timeouts / connection errors
```

### Quick check

```bash
GET _nodes/stats/jvm?filter_path=nodes.*.jvm.gc,nodes.*.name
# collection_count, collection_time_in_millis
```

---

## 5. Circuit breaker tripped (`CircuitBreakerTriggered`, P0)

### Symptoms

- Logs like:

```text
CircuitBreakingException[[parent] Data too large, data for [...] would be [XXX], which is larger than the limit of [YYY]]
```

- Requests fail with **HTTP 429** or **503**

### Breaker types

| Breaker | Role | Setting | Typical default (JVM %) |
|---------|------|---------|------------------------|
| `parent` | Ceiling for breaker accounting | `indices.breaker.total.limit` | ~95% |
| `fielddata` | Fielddata heap | `indices.breaker.fielddata.limit` | **~40%** (lowering below ~40% is risky) |
| `request` | Single in-flight request structure | `indices.breaker.request.limit` | ~60% |
| `in_flight_requests` | **All** in-flight HTTP request bytes | `network.breaker.inflight_requests.limit` | **~100%** |
| `accounting` | Long-lived accounting | `indices.breaker.accounting.limit` | — |

> **`request` vs `in_flight_requests` (important)**  
> - **`request`:** one heavy query (huge agg, large `size`, wide fields). Fix: **smaller query**, fewer buckets, better mapping.  
> - **`in_flight_requests`:** **aggregate** traffic from **many concurrent** requests. Fix: **lower client concurrency**, queueing, **more nodes** — **not** “split one big query into many small concurrent queries” (that usually **raises** concurrency and makes this worse).  
> - If the log shows **`[in_flight_requests]`**, do **not** default to “shard the query into more parallel clients.”

> **Breaker limits in `_cluster/settings` (MUST when JVM/breaker rules fire):** Always pull **both** **transient** and **persistent** (and defaults when using `include_defaults=true`) — e.g. `GET _cluster/settings?include_defaults=true` and read **`indices.breaker.*`** / **`network.breaker.*`** (use `filter_path` if you need a smaller payload). Mis-tuning often appears as **`indices.breaker.fielddata.limit`** set to a **very small JVM fraction** (e.g. **~1–5%**); **`indices.breaker.request.limit`** is **frequently lowered at the same time** (e.g. **~5%**) — cite **both** when present.  
> **Severity:** A low **`fielddata.limit` alone** is a **configuration risk**. If **`_nodes/stats/breaker`** shows **`tripped` > 0** for **`fielddata`** / **`request`** / **`parent`**, or logs show **`CircuitBreakingException`**, elevate the narrative to **incident-grade** (typically **P0**-class alongside query relief) — **not** only a **P2 “potential risk”** footnote.  
> **`tripped` vs current heap:** **`tripped`** is a **cumulative** counter (trips **since JVM start**). A **large** **`parent.tripped`** (e.g. **183**) reflects **historical** breaker events and **past** heap pressure peaks — it can **coexist** with **moderate current heap** from **`_cat/nodes`**. When both appear in one report, add **one sentence** so readers do not read “**tripped** high” and “heap **~50%** now” as contradictory.  
> **Index-level closure:** Tie symptoms to **concrete indices** (`_cat/shards`, **`GET {index}/_mapping`**) — especially **`text` fields with `fielddata: true`**, **large `terms` / `cardinality` aggs**, or deep paging — so remediation is query- and mapping-specific.

```bash
GET _cluster/settings?include_defaults=true
# Inspect persistent, transient, and defaults for indices.breaker.* and network.breaker.*
```

If `fielddata` limit is **below ~40%** of JVM **without** a deliberate vendor exception, treat as misconfiguration and restore recommended values after change approval.

### Response steps

**Step 1 — Breaker stats**

```bash
GET _nodes/stats/breaker
```

**Step 2 — Map `name` to action**

- **`fielddata`** → text-field aggs / huge fielddata → `POST _cache/clear?fielddata=true`  
- **`parent`** → overall pressure → `POST _cache/clear` + load relief  
- **`request`** → single huge request → rewrite query (size, aggs, fields)  
- **`in_flight_requests`** → too much **parallel** traffic:  
  1. **Throttle clients** / shrink pools / add queue depth server-side  
  2. **Scale out** nodes  
  3. Only if a **single** request is proven huge, tune that query — avoid fan-out that increases concurrency  
  4. Raising `network.breaker.inflight_requests.limit` is rarely the right first move (often already at JVM %)  

**Step 3 — Corroborate**

```bash
GET _tasks?detailed=true
# plus slow logs around the trip time
```

### Example (e-commerce, coordinating node)

- Traffic spike with heavy **agg** at ~15:00  
- Heap already ~80%  
- **`parent`** trips  
- Mitigation: throttle + clear fielddata + larger nodes  

---

## 6. OOM (`ResourceMonitor.OOM`, P0)

### Symptoms

- `java.lang.OutOfMemoryError: Java heap space` in logs  
- Node may have restarted on its own  
- Host: `/var/log/messages` (or journal) for **OOM killer** lines  

### Steps

**Step 1 — Is the node back?**

```bash
GET _cat/nodes?v&h=name,ip,heapPercent
```

**Step 2 — If not healthy, restart** the process / node per runbook.

**Step 3 — After restart,** if heap climbs again immediately → sustained leak or abusive query pattern.

**Step 4 — Heap histogram (when permitted on host)**

```bash
jmap -histo:live {pid} | head -50
```

### Prevention

- Enable **heap dump on OOM:** `-XX:+HeapDumpOnOutOfMemoryError`  
- Alert at **~85%** heap (`OldGenMemoryWarning` class)  
- **Very small** flavors (e.g. **2 vCPU / 4 GB**) are a poor fit for production Elasticsearch — overhead dominates.  

---

## Appendix: Quick commands (memory / GC)

```bash
GET _nodes/stats/jvm?filter_path=nodes.*.jvm.mem,nodes.*.name

GET _nodes/stats/jvm?filter_path=nodes.*.jvm.gc,nodes.*.name

GET _nodes/stats/indices/fielddata?fields=*

GET _nodes/stats/breaker

POST _cache/clear

POST /index_name/_cache/clear?fielddata=true

GET _tasks?detailed=true&actions=*search*
POST _tasks/{task_id}/_cancel

GET _cat/nodes?v&h=name,ip,heapPercent,heapCurrent,heapMax,ram.percent
```
