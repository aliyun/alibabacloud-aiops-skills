# SOP: Query performance and thread pools

**Covers:** `ThreadPool.SearchRejected` (P0), `ThreadPool.SearchQueueHigh` (P0), `Performance.SearchLatencyHigh` (P1), `Performance.LongRunningTask` (P1)

*(Frequency notes in parentheses refer to internal case statistics — tune to your catalog.)*

---

## Diagnosis decision tree

```
Query symptoms
├── HTTP 429 on search → SearchRejected (pool reject)
├── High search queue → SearchQueueHigh (backlog)
├── Latency above SLO → SearchLatencyHigh
└── Task running > ~10m → LongRunningTask

Key signals
├── GET _nodes/stats/thread_pool → search.queue / search.rejected
├── GET _tasks?detailed=true → long-running search tasks
└── SEARCHSLOW logs → slow query bodies / timings
```

> **Co‑stress vs strict causality:** Wide / high-QPS searches (e.g. `match_all` on a large index) typically **raise CPU, search queue/rejections, and GC pressure in the same window**. Describe these as **co-occurring or mutually reinforcing** under one workload — not a fixed chain like “rejected → therefore GC rose first,” unless timestamps prove ordering.  
> **CPU rubric alignment:** When **`_tasks`** / slow logs show a hot index + heavy `*search*`, state explicitly that **NodeCPU / `hot_threads` and `search` pool saturation are the same overload story** (see [sop-cpu-load.md](sop-cpu-load.md)). If CMS or the rule catalog already fires **CPU at P0** and/or **`ThreadPool.Search*` at P0** ([health-events-catalog.md](health-events-catalog.md)), keep the **headline severity** aligned — e.g. **“resource overload (CPU + search path)”** — rather than narrating only secondary signals as **P1-only**.  
> **CMS time alignment:** Add **one sentence** on whether **`NodeCPUUtilization` (or equivalent CMS window)** overlaps the period of **`search` queue / reject** pressure — including the case where **CPU mean is no longer high** but **CPU peaked in the same window** as rejects (common after the queue drains).

---

## Report narrative: search pool vs GC / CPU headlines

**Audience:** Authors of **human-written** diagnosis summaries (and agent prose). This section does **not** change CMS thresholds or rule engines; it fixes **headline ordering** and **explicit evidence gaps** when **read-path** overload is plausible. Aligns with [acceptance-criteria.md](acceptance-criteria.md) section **6.2** (read-heavy CPU + search pool) and section **6.5** (search pool vs GC-only headline). For write-path vs GC ordering, see [sop-write-performance.md](sop-write-performance.md) and acceptance-criteria section **6.4**.

### Query-bound overload: what to lead with

- When the workload is **read-heavy** (high concurrent search, terms / high-QPS patterns, **`ThreadPool.SearchRejected`** or queue stress), the **primary** storyline should be **`search` pool saturation / query concurrency exceeding pool capacity** — **not** a **GC-only** headline. **`ThreadPool.SearchRejected`** (or catalog-equivalent) should appear **first or co-equal** with resource signals.
- **Old GC + CPU spikes** often **co-occur** or form a **second wave** with concurrent search and segment merge load — they are **not** wrong as evidence, but **misleading as the sole lead** when the incident is **query-bound** and **`thread_pool.search` has not been ruled out**.
- **Production caveat:** The same CMS signals can still support a **legitimately GC-primary** or **breaker-primary** story if engine APIs show **heap / breaker / mapping** issues **without** search-pool saturation. Separate **what CMS proved** from **what still needs** `GET /_nodes/stats/thread_pool` (or `_cat/thread_pool`).

### When engine REST evidence is incomplete

If **`GET /_nodes/stats/thread_pool`** or **`_cat/thread_pool`** was **not** successfully collected (timeouts, unstable public path, firewall), but **GC / CPU** findings exist from **CMS or the rule engine**:

**Suggested wording (Chinese — adapt to facts):**

> 在引擎 API 未完整采集前：若规则引擎或监控已出现 **`ThreadPool.SearchRejected`** 或 **线程池饱和类事件**，应优先按 **「查询并发打满 `search` 池」** 排查；当前因超时/网络未能用 **`/_nodes/stats/thread_pool`** 证实 **`search.rejected` / queue**，以下 **GC / CPU** 为 **监控侧风险画像**，需在 **VPC 内或白名单稳定路径** 上补 **`thread_pool.search`**、**`/_tasks`**、**`/_nodes/hot_threads`** 后再定主次因果。

If **`ThreadPool.SearchRejected`** (or equivalent) **did not** fire in the **same window**, still add **one explicit line** that **`search` pool reject/queue remains unverified** (do not invent rejects):

> **待补证：** **`search` 池是否拒绝或排队**（读路径过载时通常为首要排查点之一），需引擎层 **`/_nodes/stats/thread_pool`** 或 **`_cat/thread_pool`**。

Self-limiting discipline for failures: [es-api-call-failures.md](es-api-call-failures.md).

### Executive summary: parallel P0 / P1 lines

- If the rule engine reports **`JVMMemory.GCTimeRatioTooHigh` (P0-class)** **and** **`ThreadPool.SearchRejected`** (exact priority depends on catalog; some snapshots emit P1), the **human-facing** summary should still **mention both** when the catalog treats search rejects as incident-class.
- Opening bullets must **not** read as **“the only P0 is Old GC”** when **search-path** rules also fired. Order: **search pool / reject / query concurrency** **first or co-equal**; GC/CPU as **co-stress, cascade, or pending confirmation** after `thread_pool` + `_tasks`.

**Quantification (mirrors [sop-write-performance.md](sop-write-performance.md) §2):** For rubric-style reports, add **one line of numbers** from **`GET _nodes/stats/thread_pool`**: per-node **`search.rejected`** and **`search.completed`**, optional **reject share** (roughly `rejected / (rejected + completed)`). **`rejected` is cumulative** since node start (see §1 **Inspect**). When aligning to CMS, cite rule/event names (e.g. **`ThreadPool.SearchRejected`**) alongside API stats.

**Both `search` and `write` show `rejected` (cumulative):** Compare **magnitudes** on the **same node(s)**. When **`search.rejected` ≫ `write.rejected`** and the case is **query-saturation** (high QPS search, **`ThreadPool.SearchRejected`** in scope), the **first storyline** is **`search` pool / query concurrency** — link to **terms / wide query / slow query**, **`_tasks`** / **`hot_threads`**, and **hot index name** when confirmed. **`write.rejected`** stays **valid** as **secondary or parallel** (bulk backfill, catch-up indexing); **do not** open with **write** ahead of **search** in the **executive summary** or **first P0 bullet** unless **timelines** or **paired deltas** show **write** was the dominant stressor in the window. See [acceptance-criteria.md](acceptance-criteria.md) **§6.5** (*P0 / executive order vs `search` ≫ `write`*).

**Different nodes in slow logs vs pool-rejection logs:** A **SEARCHSLOW** / **fetch** entry may attribute latency to **node A** while an **INSTANCELOG** line at **another timestamp** shows **`search` pool** pressure on **node B** — not necessarily a mistake: **fetch** runs where the **shard copy** lives; **pool saturation** can concentrate on the **busiest data node** for that window; **routing** and **replica** choice shift over time. **Reconcile** with **`GET /_cat/shards/{index}`** and **time ordering**; add **one explicit sentence** in the report so reviewers do not treat the two as contradictory. See [acceptance-criteria.md](acceptance-criteria.md) **§6.2** (*Slow-log node vs search-pool node*).

### Customer-facing references to SKILL / engine APIs

| Audience | Preferred phrasing |
|----------|---------------------|
| **External / 对客** | **引擎层必查清单（见 SKILL 文档第 5 节）**、**第 5–7 节** — avoid **§**-style section markers in PDFs or customer email. |
| **Internal** | **“SKILL.md section 5”** in prose is fine without the **§** symbol. |

The health-check script’s footer uses the same **no-§** convention.

### Evidence closure checklist

1. **Rules / CMS:** Did **`ThreadPool.SearchRejected`** (or a metric/event with the same meaning) fire in the report window? State **yes / no** explicitly.
2. **Engine (stable path):** **`GET /_nodes/stats/thread_pool`** with **`filter_path`** for **`search`**; **`GET /_tasks?detailed=true&actions=*search*`** when CPU or reject signals exist.
3. **Narrative:** If (1) is yes or engine shows **`search.rejected` / queue**, do **not** deliver a **GC-only** conclusion for a **read-heavy** incident — tie **GC/CPU** to **co-occurring search load** when evidence supports it (see **Co‑stress** note at the top of this document).

---

## 1. Search thread-pool queue buildup (`SearchQueueHigh`, P0)

### Inspect

```bash
GET _nodes/stats/thread_pool?filter_path=nodes.*.thread_pool.search,nodes.*.name
# queue = current depth; rejected = cumulative rejects (since node process start unless reset)
```

**Counter semantics:** `search.rejected` is **cumulative** for the node process (until restart). Do **not** treat the current value as “rejects only inside the diagnosis window” unless you have a **delta** between two samples or a known reset. **`queue == 0`** can still follow a burst where **`rejected` increased** — the pool drained after the spike.

### Root causes

**A — Slow queries holding workers**

- **Signals:** few tasks tie up `search` workers; queue grows behind them  
- **Check:** `GET _tasks?detailed=true&actions=*search*`  
- **Mitigate:** `POST _tasks/{task_id}/_cancel`, then fix the query  

**B — QPS exceeds capacity**

- **Signals:** queue grows roughly linearly with traffic  
- **Mitigate:** throttle / shed load at the client or gateway; **scale out** nodes  

**C — CPU starved**

- **Signals:** high CPU **and** high search queue  
- **Mitigate:** [sop-cpu-load.md](sop-cpu-load.md)  

### Note: search queue size is not a tuning knob

On typical Elasticsearch builds the **search** queue has a **fixed** upper bound (often **1000**). Unlike some write-side pools, you usually **cannot** “fix” saturation by raising the search queue — you must **reduce work per query**, **reduce concurrency**, or **add capacity**.

---

## 2. Search thread-pool rejections (`SearchRejected`, P0)

### Symptoms

- Clients: **`HTTP 429 Too Many Requests`** on search paths  
- Logs: `rejected execution of search` (wording varies by version)  

### `_cat/thread_pool` vs `_nodes/stats/thread_pool`

Either **`GET _cat/thread_pool`** or **`GET _nodes/stats/thread_pool?filter_path=...search...`** is valid engine evidence for the **`search`** pool. For **`rejected`**, both surface the **same node-level cumulative semantics** (see §1 counter note); use one or both if reviewers ask for **source parity**.

### Immediate response

**1. Capture what is running (while the incident is live)**

```bash
GET _nodes/hot_threads
GET _tasks?detailed=true&actions=*search*
```

**2. Cancel runaway searches**

```bash
POST _tasks/{task_id}/_cancel
```

**3. Check gateway / vendor QoS (if applicable)**

```bash
# Alibaba Cloud Elasticsearch — QoS limiter metrics (if exposed in your build)
GET _qos/limiter/metric
```

### Node skew (`rejected` higher on one node)

Uneven **`search.rejected`** can come from **one client entry path**, shard / routing skew, or **query coordination** landing more often on certain nodes. The elected master participates in **coordination / routing** (and may receive client searches depending on topology) — it does **not** imply “the master executes all shard searches.” Treat one hot node as a **lead**, then confirm with **`_cat/shards`**, **`_tasks`**, and node roles.

**Hot node + layout (wording):** When **`_cat/shards`** shows **extreme primary/replica skew** and **`search.rejected`**, **heap**, or **GC** concentrate on the **same node**, treat that node as the **hot node** in the narrative — the chain can be **internally consistent**. Describe **skew** as **one amplifier of local engine work** on that side (**merge / refresh / indexing** when those paths are active), **together with** read-side concentration (**coordinator / single client URL / `preference=_primary` / routing**, time-skewed peaks). **Coordinator + ingress can still bias index-level work** toward one node even when replicas exist — this is **not** the same as “all reads hit primaries only.” **Do not** imply that **default read traffic** is routed **only** to primaries; **replicas serve queries** unless clients opt out. **`_cat/shards` + per-node `rejected`** stay **facts**; the bullets above are **hypotheses to narrow** with `_tasks`, client settings, and query parameters.

**Placement wording:** Use **one convention** everywhere — e.g. **“all primaries on {node}”**, **“6 / 6 primaries on {node}”**, or **“every `p` row on {node}”** — avoid mixing **“almost all”** in the title with **“all”** in tables unless you document a real exception shard.

**CPU vs `rejected` on different nodes:** Per-node **CPU max** and **rejected** need not align at the **same instant** (peaks can occur at **different minutes**), and one node may host **other hot indices or system work**. When CMS shows **higher CPU on node X** but **higher `search.rejected` on node Y**, say so explicitly — avoid implying “the hottest CPU node must always be the highest-reject node” for the whole window.

---

## 3. Slow queries (`Performance.SearchLatencyHigh`, P1)

### Three-step triage

**Step 1 — Search Profiler**

Use Kibana Search Profiler, or add `"profile": true` to the search body:

```bash
GET /index_name/_search
{
  "profile": true,
  "query": {
    "match": { "field": "value" }
  }
}
```

Inspect shard query breakdown (`shards.*.query`, etc.) for dominant query types.

**Step 2 — Slow logs**

Filter `SEARCHSLOW` (or equivalent) for high `took` / `search_time_ms` (e.g. **> 1000 ms** as a starting filter — align to your SLO).

**Step 3 — Baseline**

- Versus yesterday / last week same window?  
- All queries slow, or only certain indices / patterns?  

---

## 4. Common slow query patterns and mitigations

### 4.1 Wildcard-style queries (often worst)

- **Issue:** `wildcard`, `prefix`, `regexp` can scan huge posting lists.  
- **Worst:** leading wildcards (e.g. `*foo`) — effectively full-term scans.  
- **Mitigations:**  
  - `prefix` → **completion** suggester or **edge n-gram** indexing where appropriate  
  - `wildcard` → structured filters / `match` where possible  
  - `regexp` → narrower `term` / `terms` / keyword patterns where possible  

### 4.2 Deep paging (`from` + `size`)

- **Issue:** each shard must fetch **`from + size`** ordered hits; cost scales with shards.  
- **Guard:** default **`index.max_result_window` is 10000** (`from + size` cap).  
- **Mitigations:**  
  - Live paging → **`search_after`**  
  - Export / scan → **`scroll`** or **PIT + search_after** (modern ES)  
  - Avoid raising `max_result_window` as a “fix” — it hides the real cost  

### 4.3 Aggregations

- **Issue:** high-cardinality `terms` aggs (e.g. raw `user_id`, `ip`) burn CPU / heap.  
- **Mitigations:**  
  - Lower **`size`** (return fewer buckets)  
  - **`execution_hint: map`** where it fits **low-cardinality** workloads (check version docs)  
  - Never aggregate on **`text`** — use **`keyword`** (or `doc_values`)  
  - Prefer indexed fields over heavy **`script`** aggs  
- **Never aggregate on `_id` or `text` for production traffic** — fielddata / heap explosions: [sop-memory-gc.md](sop-memory-gc.md)  

### 4.4 Script queries

- **Issue:** scripts bypass most index structures.  
- **Mitigations:** precompute at index time; **Painless** (not legacy Groovy); avoid hot loops in scripts.  

### 4.5 Numeric `term` queries

- **Issue:** building doc-id sets for numeric `term` can be expensive at scale.  
- **When:** you only need exact match, not range / sort on that numeric.  
- **Mitigation:** add a **`keyword`** (or string) parallel field for equality filters.  

### 4.6 `nested` / `parent-child`

- **Issue:** nested docs multiply work; parent-child is often **several×** heavier than nested.  
- **Mitigation:** model as **`object`** / flattened structures when business rules allow.  

### 4.7 Highlighting

- **Issue:** huge **`fragment_size`** → CPU / memory on highlight.  
- **Mitigation:** smaller fragments or highlight off-cluster.  

### 4.8 Huge time ranges

- **Issue:** scanning years of data every request.  
- **Mitigation:** bound time filters; batch by window.  

### 4.9 Unbounded `range` queries

- **Issue:** e.g. `{"range": {"date": {"lte": "2024-01-01"}}}` with **no lower bound** — cost grows forever with data.  
- **Mitigation:** always set **both** bounds when possible.  

### 4.10 Massive hit counts

- **Issue:** very broad query → **`hits.total`** in the millions; even `size: 10` can be expensive if every shard scores huge sets.  
- **Mitigations:** tighten filters; **`track_total_hits: false`** or a capped integer; existence checks → **`size: 0`** + **`terminate_after`** where appropriate.  

### 4.11 `refresh_interval` vs query cost

- **Issue:** very low **`refresh_interval`** (e.g. **1s**) → many small segments → more segment files to query / more merge pressure on small nodes.  
- **Inspect:**

```bash
GET {index}/_settings?filter_path=**.refresh_interval
GET _cat/segments/{index}?v&h=index,shard,segment,size
```

Many small segments per shard (rule-of-thumb **> ~50** per shard) suggests excessive refresh / merge pressure — validate against your workload.

| Scenario | Suggested `refresh_interval` | Notes |
|----------|------------------------------|-------|
| Logs / high ingest, relaxed search freshness | **30s–60s** | Fewer segments, better bulk throughput |
| Near-real-time dashboards | **5s–10s** | Balance freshness vs cost |
| Bulk load window | **`-1`** (disabled) | After bulk: `POST {index}/_refresh`, then restore interval |
| Small nodes (e.g. 2c4g / 4c8g) | **≥ 30s** typical | Avoid 1s refresh on tiny flavors |

```bash
PUT {index}/_settings
{
  "index.refresh_interval": "30s"
}

PUT {index}/_settings
{
  "index.refresh_interval": "-1"
}
POST {index}/_refresh
PUT {index}/_settings
{
  "index.refresh_interval": "30s"
}
```

---

## 5. Long-running tasks (`LongRunningTask`, P1)

| Task kind | Duration | Notes |
|-----------|----------|-------|
| `delete_by_query` | can exceed **30m** on large data | prefer off-peak |
| `reindex` | hours possible | tune `scroll_size` / slices per docs |
| `_update_by_query` | same class as delete_by_query | same cautions |
| Snapshot / restore | depends on data + network | usually expected; watch progress |
| Scroll | leaks if clients omit `clear_scroll` | monitor open contexts |

### Inspect / cancel / scroll hygiene

```bash
GET _tasks?detailed=true&nodes=*
GET _tasks/{task_id}
POST _tasks/{task_id}/_cancel

GET /_nodes/stats/indices/search?filter_path=nodes.*.indices.search.scroll_*
DELETE /_search/scroll
{
  "scroll_id": ["scroll_id_1", "scroll_id_2"]
}
```

---

## Appendix: Quick commands (query)

```bash
GET _cat/thread_pool?v&h=name,node_name,active,queue,rejected
GET _nodes/stats/thread_pool?filter_path=nodes.*.thread_pool.search,nodes.*.name

GET _nodes/hot_threads

GET _tasks?detailed=true&actions=*search*
POST _tasks/{task_id}/_cancel

# Profiling: use a JSON body (not inline on the GET line)
GET /index_name/_search
{
  "profile": true,
  "query": { "match_all": {} }
}

GET _nodes/stats/indices/search?filter_path=nodes.*.indices.search
# query_total, query_time_in_millis, fetch_total, fetch_time_in_millis
```
