# SOP: High CPU load and uneven node load

**Covers:** `ResourceMonitor.CPUSustainedHigh` (P0), `ResourceMonitor.CPUPeakHigh` (P1), `CapacityPlanning.LoadImbalance` (P1)

CMS metric ↔ finding names may differ by catalog version — cross-check [health-events-catalog.md](health-events-catalog.md).

---

## Diagnosis decision tree

```
NodeCPUUtilization (example CMS family)
├── Any node avg > ~80% sustained → CPUSustainedHigh (P0), treat as urgent
├── Any node max > ~95% (spike) → CPUPeakHigh (P1), respond within ~30m
└── Coefficient of variation (CV) of per-node avg CPU > ~0.3 → LoadImbalance (P1)

NodeLoad_1m
└── High load but CPU not high → often IO wait; correlate with disk / queue metrics
```

> **Read-heavy overload:** When **`_tasks?detailed=true&actions=*search*`** shows sustained heavy search on specific indices and **`search` thread_pool** queue/rejected rises together with **NodeCPU**, say so in one line — **CPU spike and search rejects share the same query load**, not two unrelated incidents. Co‑stress wording: [sop-query-thread-pool.md](sop-query-thread-pool.md) (note after the decision tree). Use the **highest priority** already fired by metrics/rules (often **P0** CPU and/or **P0** search pool per catalog) for the summary band.

> **CMS CPU looks “low” vs heavy `search.rejected`:** Before finalizing the story, add **one short reconciliation** (especially for external readers): **(1)** whether the **load burst** sat mostly **early** in the report window while CMS shows a **whole-window** max/mean; **(2)** that **`NodeCPUUtilization` (or the catalog’s CPU metric)** is scoped to **this instance’s data nodes** — not a cluster rollup or wrong `Dimensions`; **(3)** optional **`GET _nodes/stats/os`** (process CPU) near the burst — **sub-minute** spikes can sit **between** coarse CMS samples. If **(1–3)** hold, it is **legitimate** to conclude **thread-pool / reject saturation without prolonged high CMS CPU** — but if a check fails, **fix the metric or window wording** instead of forcing the claim.

> **Per-node CPU % “lower” on the node that logs show as `search` hotspot:** Table **means** (e.g. **5 min** buckets) can **rank nodes differently** from **minute-of-peak** behavior or **thread-pool saturation** (queue/reject, `EsRejectedExecutionException` in logs). Prefer **time-aligned** evidence (**slow logs**, **thread_pool**, **hot_threads** at spike) for **which node** was search-bound; **CPU imbalance** rows are **supporting**, not a contradiction when **granularity** differs. See [acceptance-criteria.md](acceptance-criteria.md) **§6.2** (*Per-node CPU % vs search “hot” node*).

---

## 1. Three-step triage (any high-CPU scenario)

**Step 1 — Hot threads (capture while the issue is live)**

```bash
GET _nodes/hot_threads
# Thread name; stack frames: search / index / merge / GC
```

Prefer **`hot_threads` while CMS CPU is elevated** or immediately after a spike is reported. If the call **times out**, returns **thin stacks**, or the spike already ended while **`_nodes/stats/thread_pool`** / **`_tasks`** still show search overload, state **time-skewed or degraded hot_threads evidence** — do not claim “no search CPU work” for the whole incident window.

**Step 2 — Running tasks**

```bash
GET _tasks?detailed=true
GET _cat/tasks?v
# action, running_time_in_nanos (very long tasks)
```

**Step 3 — Slow logs**

Filter logs for `took_millis`, `query_time_in_millis`, or slow-log channels (`SEARCHSLOW` / `INDEXINGSLOW`).

---

## 2. Sustained high CPU (`CPUSustainedHigh`, P0)

### Criteria (example)

- Average CPU **> ~80%** for **> ~10 minutes** (tune to your alerts)

### Root-cause paths

**Path A — Traffic spike**

- **Signals:** `ClusterQueryQPS` / `ClusterIndexQPS` (or access logs) step up  
- **Check:** large `body_size` requests  
- **Mitigate:** throttle / rate-limit, scale out nodes urgently  

**Path B — Slow queries blocking**

- **Signals:** hot threads dominated by **search** stacks; `_tasks` shows long-running search  
- **Common anti-patterns** (see [sop-query-thread-pool.md](sop-query-thread-pool.md) for tuning detail):  
  - `wildcard` / `prefix` / `regexp` (leading wildcards are worst)  
  - Heavy `aggregations` (high cardinality)  
  - Deep `from + size` paging (e.g. > 10k)  
  - `nested` / `parent-child`  
  - Oversized `highlight` `fragment_size`  
  - Numeric fields queried as full-text; prefer `keyword` where appropriate  
- **Mitigate:** `POST _tasks/{task_id}/_cancel` for runaway tasks; fix queries  

**Path C — Heavy indexing**

- **Signals:** hot threads show **index** / **bulk**; high ingest QPS  
- **Mitigate:** lower **parallel** bulk pressure and client retries; tune **per-bulk payload** (avoid oversized single bulks — see [sop-write-performance.md](sop-write-performance.md) **§2**); relax `refresh_interval` where safe  
- **If CPU / GC spike with `write.rejected`:** align the **report narrative** with [sop-write-performance.md](sop-write-performance.md) **§2** (write-path first or dual P0 with ingest before JVM-only headline)  

**Path D — Frequent merges**

- **Signals:** hot threads show **merge**  
- **Mitigate (temporary):** cap merge scheduler threads (impacts indexing latency):

```bash
PUT _cluster/settings
{
  "transient": {
    "indices.merge.scheduler.max_thread_count": 1
  }
}
```

### Emergency order of operations

```text
1. Throttle / shed load (often fastest)
2. Cancel huge tasks (GET _tasks → POST _tasks/{id}/_cancel)
3. Scale out if needed
4. Deeper root-cause and query/index design work
```

---

## 3. Very high CPU spikes (`CPUPeakHigh`, P1)

### Criteria (example)

- CPU **max > ~95%** even if the average stays lower  

### vs `CPUSustainedHigh`

| | CPUPeakHigh | CPUSustainedHigh |
|---|-------------|------------------|
| Average | often < ~80% | > ~80% |
| Peak | > ~95% | often also > ~95% |
| Duration | short burst | ~10m+ |
| Risk | heartbeat / latency spikes | higher chance of node loss / overload cascade |

### Focus

- Spikes are often **one huge query** or **merge**  
- **Hot threads** must be captured **during** the spike; evidence disappears after  
- Also review: BKD range queries, large aggs, heavy `script` queries  

---

## 4. Uneven load across nodes (`LoadImbalance`, P1)

### Criteria (example)

- Per-node CPU **CV = stddev / mean > ~0.3** for **~10+ minutes**  

### Typical pattern

- A few nodes at **80%+** CPU, others **below ~30%**  
- Hot traffic pinned to specific nodes  

### Causes and mitigations

**Cause A — Shard skew**

- **Verify:**

```bash
GET _cat/shards?v&s=node&h=index,shard,prirep,state,docs,store,node
GET _cat/nodes?v&h=name,ip,cpu,heapPercent,diskAvailInBytes,shards
```

- If shards of **hot indices** pile on the hot CPUs → rebalance  
- **Mitigate — move a shard:**

```bash
POST _cluster/reroute
{
  "commands": [{
    "move": {
      "index": "hot_index",
      "shard": 0,
      "from_node": "node_hot",
      "to_node": "node_cool"
    }
  }]
}
```

**Cause B — Skew *inside* shards (segment / doc locality)**

- **Pattern:** shard **count** looks balanced, but one node still burns CPU; hot threads point at one shard  
- **Mitigation:** `forcemerge` can compact segments and sometimes smooth read patterns — **use off-peak**; understand IO cost and [Elasticsearch guidance](https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-forcemerge.html) for your version  

```bash
POST hot_index/_forcemerge?max_num_segments=1
```

**Cause C — No ingest-only / coordinating tier**

- **Pattern:** large QPS differences by node for request handling  
- **Mitigate:** add **coordinating** (client) nodes so data nodes focus on data  

**Cause D — Custom `_routing` skew**

- **Pattern:** custom routing concentrates docs in a few shards  
- **Mitigate:** review routing keys and shard/key design with the application team  

---

## 5. Single-node CPU hot spots (field experience; not a separate V4.5 catalog line)

### Pattern A — JVM `ThreadLocal` / stale-entry churn

**Typical signals**

- Only **1–2** nodes at **80%+** CPU; peers ~**40%**  
- Hot threads: **`management`** thread ~**100%** CPU  
- Stack traces mention **`ThreadLocal`** / **`expungeStaleEntry`**

**Mechanism (simplified)**

- Many stale `ThreadLocal` entries; **G1** may not clean aggressively → **`ThreadLocalMap.expungeStaleEntry`** dominates CPU.

**Confirm**

```bash
GET _nodes/hot_threads
# e.g.:
# 100% cpu usage by thread 'elasticsearch[node][management][T#3]'
#   at java.lang.ThreadLocal$ThreadLocalMap.expungeStaleEntry(...)
```

**Mitigation**

- **Short term:** coordinated **Full GC** or node restart **only** with vendor / SRE guidance  
- **Long term:** upgrade to a **7.10+** line where your distribution documents ThreadLocal / JVM fixes (major upgrades need a full migration plan)  

### Pattern B — Huge search; coordinating node melts

**Typical signals**

- Hot node is often the **coordinating** node for the request  
- Heavy **query reduce** / coordination cost  
- Not explained by shard placement alone  

**Check**

```bash
GET _tasks?detailed=true&actions=*search*
# action, node, running_time
```

---

## Appendix: Quick commands (CPU)

```bash
GET _nodes/hot_threads

GET _tasks?detailed=true
GET _cat/tasks?v

POST _tasks/{task_id}/_cancel

GET _cat/nodes?v&h=name,ip,cpu,load_1m,heapPercent,disk.used_percent

GET _cat/shards?v&s=node&h=index,shard,prirep,docs,store,node

PUT _cluster/settings
{
  "transient": {
    "indices.merge.scheduler.max_thread_count": 1
  }
}

POST _cluster/reroute
{
  "commands": [{
    "move": {
      "index": "index_name",
      "shard": 0,
      "from_node": "node_hot",
      "to_node": "node_cool"
    }
  }]
}
```
