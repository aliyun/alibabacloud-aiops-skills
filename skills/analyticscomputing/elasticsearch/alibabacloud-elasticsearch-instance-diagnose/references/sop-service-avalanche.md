# SOP: Node “unavailable” vs search-pool meltdown (service avalanche)

**Covers:** `ServiceAvalanche.SearchServiceDown` (P0), `ServiceAvalanche.AllShardsFailed` (P0), `ServiceAvalanche.CPUInducedUnavailability` (P0)

> **Why this SOP exists:** It targets **“the node looks dead but the process is still up.”** CMS may **not** increment `ClusterDisconnectedNodeCount`, and you may **not** see `NODE_LEFT` / `removed` in `INSTANCELOG` — the usual **node-offline** playbook fails. You need **cross-signals** (CMS CPU still reporting + search pool rejects + `all shards failed`) to pin **CPU overload → search thread-pool exhaustion → cascading search failures**.

---

## Diagnosis entry: “node offline” vs meltdown

```
User: "node offline / ES unavailable"  OR  intermittent ES API timeouts
├── Control plane DescribeInstance.status
│   ├── active → control plane OK → continue to engine
│   ├── activating → change in flight (scale/restart/upgrade); wait or see sop-activating-change-stuck.md
│   └── inactive / invalid → platform issue → open a ticket with your cloud provider
│
├── CMS NodeCPUUtilization still reporting?
│   ├── Yes → 【process likely alive】 at OS level
│   │   ├── CPU > ~80% sustained → ★ ServiceAvalanche (core scenario in this SOP)
│   │   └── CPU normal but API bad → network / security group / allowlist
│   └── Gaps / no points → 【process may be dead】
│       ├── INSTANCELOG "removed" / "left" → real node departure → [sop-cluster-health.md](sop-cluster-health.md)
│       └── CMS SystemEvent node events → [sop-cluster-health.md](sop-cluster-health.md)
│
├── ES API call pattern (during diagnosis)
│   ├── All calls time out consistently → often network / allowlist (not avalanche)
│   ├── Intermittent success + timeout + CPU > ~80% → ★ suspected avalanche
│   └── Connection refused → process/port down → [sop-cluster-health.md](sop-cluster-health.md)
│
└── INSTANCELOG contains "all shards failed"?
    ├── Yes + high CPU → ★ avalanche (strong)
    ├── Yes + normal CPU → often allocation / shard issues → [sop-cluster-health.md](sop-cluster-health.md)
    └── No → other paths (query, gateway, client bugs)
```

---

## 1. Core scenario: CPU overload → search pool meltdown

### What “service avalanche” means here

**Definition:** OS process is up, CMS still shows points, but **search is effectively unusable** — searches fail with `SearchPhaseExecutionException: all shards failed` (wording varies). To the app this feels like **node down**.

**Mechanism:** Not “node left cluster,” but **search worker pool saturation + queue overflow + timeouts + cascade**.

### When to call it confirmed (example)

| Signal | Example threshold | CMS / logs |
|--------|-------------------|------------|
| Sustained CPU | avg **> ~80%** for **≥ ~10 min** | `NodeCPUUtilization` |
| Search rejects | `rejected` rising | `SearchThreadpoolRejected` |
| Cascade in logs | burst of **all shards failed** | `INSTANCELOG` |

### vs true node loss

| | Real node offline | Service avalanche (this SOP) |
|---|-------------------|------------------------------|
| Control-plane status | may go `activating` | often stays **active** |
| CMS CPU series | **stops** or is missing | **continues** (often **80%+**) |
| CMS `ClusterStatus` | may go Red | may stay Green / sparse |
| INSTANCELOG | `node left` / `removed` | **no** clean leave |
| INSTANCELOG | no mass `all shards failed` | **many** `all shards failed` |
| `ClusterDisconnectedNodeCount` | **> 0** | often **0** |
| REST `_cluster/health` | sometimes **refused** | often **timeouts** (intermittent) |
| Call pattern | all fail same way | **some succeed, some time out** |

> **Key discriminator:** **CPU metrics still arriving** from the node, at high values, **plus** `all shards failed` → treat as avalanche, not “host gone.” **Intermittent** timeouts + high CPU support overload; **uniform** timeouts lean network/ACL; **refused** leans dead process/port.

---

## 2. Entry signal: intermittent Elasticsearch API timeouts

> **When:** During diagnosis, REST calls **sometimes** return, **sometimes** time out, while CMS shows **CPU > ~80%**.

### Why intermittent timeouts fit overload

- TCP can connect; process listens.  
- Internal **`search` pool** is saturated → work queues → latency blows up.  
- Some requests finish before the client timeout; others do not → **jittery** success/failure.  
- That pattern differs from **“every call times out the same way”** (often path/network).

### Branching checklist

```
Intermittent timeouts
├── CMS NodeCPUUtilization (last ~10m)
│   ├── Sustained > ~80% → highly suspicious → gather evidence in Section 3 Step 2
│   ├── < ~50% → deprioritize avalanche; look at network instability
│   └── sparse points → tighten CMS window / resolution; re-sample
├── DescribeInstance.status
│   ├── active → continue engine analysis
│   └── not active → not this avalanche path
└── INSTANCELOG "rejected" / "all shards failed"
    ├── rejected lines → pool overflow (strong)
    └── none yet → capture hot_threads in brief windows when API responds
```

### Collection tactics when the API is flaky

1. **Longer client timeouts:** e.g. `--connect-timeout 20 --max-time 60`.  
2. **Light calls first:** `_cat/nodes`, `_cluster/health`.  
3. **Retry heavy calls** (`_nodes/hot_threads`, `_nodes/stats/thread_pool`) up to **~3** times.  
4. **Log success ratio** as a severity side-channel.

---

## 3. Four-step diagnosis

### Step 1 — Is the process actually gone?

**Goal:** separate **real** departure from **meltdown**.

```bash
# 1) Control plane
aliyun elasticsearch describe-instance --region <region> --instance-id <id>
# status active → usually OK at CP layer

# 2) CMS CPU last ~5 minutes (points exist?)
aliyun cms describe-metric-list \
  --namespace "acs_elasticsearch" \
  --metric-name "NodeCPUUtilization" \
  --dimensions '[{"instanceId":"<id>"}]' \
  --start-time "<5_min_ago_ms>" \
  --end-time "<now_ms>" \
  --period 60
# Points on both data nodes → likely alive at process level
# No points on a node → suspect real loss / agent gap

# 3) Leave events in INSTANCELOG
aliyun elasticsearch list-search-log \
  --region <region> --instance-id <id> \
  --type INSTANCELOG \
  --query "removed OR left OR disconnect" \
  --begin-time "<start_ms>" --end-time "<end_ms>"
# empty → no classic "node left" story
```

**Rule:** CMS CPU **present** + **no** `removed/left` → **not** classic offline → **Step 2**.  
CMS CPU **absent** + leave logs → **real offline** → [sop-cluster-health.md](sop-cluster-health.md).

### Step 2 — Prove the avalanche chain (CPU → pool → search failure)

```bash
# 1) CPU trend (~30m) — when did it cross ~80%?
aliyun cms describe-metric-list \
  --namespace "acs_elasticsearch" \
  --metric-name "NodeCPUUtilization" \
  --dimensions '[{"instanceId":"<id>"}]' \
  --start-time "<30_min_ago_ms>" --end-time "<now_ms>" --period 60

# 2) Search pool rejects
aliyun cms describe-metric-list \
  --namespace "acs_elasticsearch" \
  --metric-name "SearchThreadpoolRejected" \
  --dimensions '[{"instanceId":"<id>"}]' \
  --start-time "<30_min_ago_ms>" --end-time "<now_ms>" --period 60

# 3) Write pool rejects (ingest also melting?)
aliyun cms describe-metric-list \
  --namespace "acs_elasticsearch" \
  --metric-name "WriteThreadpoolRejected" \
  --dimensions '[{"instanceId":"<id>"}]' \
  --start-time "<30_min_ago_ms>" --end-time "<now_ms>" --period 60

# 4) "all shards failed" in INSTANCELOG
aliyun elasticsearch list-search-log \
  --region <region> --instance-id <id> \
  --type INSTANCELOG \
  --query "shards" \
  --begin-time "<start_ms>" --end-time "<end_ms>"
```

**Example “confirmed” triad:**

1. CPU avg **> ~80%** for **≥ ~10 min**  
2. `SearchThreadpoolRejected` **> 0** (rising)  
3. `INSTANCELOG` shows **`all shards failed`** burst  

### Step 3 — Find the trigger (index / traffic / query)

**3.1 Index from rejected / slow paths**

```bash
aliyun elasticsearch list-search-log \
  --region <region> --instance-id <id> \
  --type INSTANCELOG \
  --query "rejected" \
  --begin-time "<start_ms>" --end-time "<end_ms>"
# path like "/my-index/_search" → hot index
```

**3.2 Thread-pool excerpt (`EsRejectedExecutionException`)**

Example block (shape varies by version):

```text
QueueResizingEsThreadPoolExecutor[
  name = <node>/search,
  pool size = 4,
  active threads = 4,
  queued tasks = 1005,
  queue capacity = 1000,
  task execution EWMA = 371μs
]
```

| Field | Healthy-ish | Meltdown-ish | Meaning |
|-------|-------------|--------------|---------|
| active | < pool | **= pool** | all workers busy |
| queued | low | **> capacity** | queue overflow |
| EWMA | low μs | high μs | slower per-task work |
| completed | rising | stalls | throughput collapse |

**3.3 `Caused by` under `all shards failed`**

| `Caused by` | Meaning | Next |
|-------------|---------|------|
| `EsRejectedExecutionException` | pool saturated | CPU / QPS / capacity |
| `TaskCancelledException` (parent cancelled) | timeout cascade | parent timeouts / load |
| `CircuitBreakingException` | breaker | [sop-memory-gc.md](sop-memory-gc.md) |
| `NodeNotConnectedException` | shard/node channel dead | real disconnect path → [sop-cluster-health.md](sop-cluster-health.md) |

**3.4 Elasticsearch APIs (when REST is reachable)**

```bash
curl -sS --connect-timeout 10 --max-time 30 \
  -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_nodes/hot_threads?threads=3"

curl -sS --connect-timeout 10 --max-time 30 \
  -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_tasks?detailed=true&actions=*search*"

curl -sS --connect-timeout 10 --max-time 30 \
  -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_nodes/stats/thread_pool?filter_path=nodes.*.thread_pool.search,nodes.*.name"
```

Deeper query tuning: [sop-query-thread-pool.md](sop-query-thread-pool.md), [sop-cpu-load.md](sop-cpu-load.md).

### Step 4 — Report template

```markdown
## Conclusion: service avalanche (not physical node loss)

**Instance:** {instance_id} ({region})
**Topology:** {node_count} × {spec} (search workers ≈ {pool_size} — verify with _cat/thread_pool)
**Window:** {begin} ~ {end}

### Differentiation
- Control plane: active
- CMS CPU: continuous points (process likely alive)
- Leave logs: none
- Verdict: **meltdown**, not host-down

### Evidence chain
1. CPU inflection at {time}: {before}% → {after}%
2. Search rejects on {node}: {count}
3. `all shards failed` burst at {time}; indices: {index}
4. Root `Caused by`: {text}

### Chain sketch
{trigger} → CPU ~{cpu}% for {duration}m
  → search pool full (active {active}/{pool}, queue {queue}/{cap})
    → rejects ({n})
      → parent cancels → shard failures cascade
        → `all shards failed` → user-visible outage

### Trigger hypothesis
- Hot index: {index}
- Driver: {QPS spike / slow query / load test}
- EWMA: {a}μs → {b}μs

### Actions
{concrete steps}
```

---

## 4. Remediation

### Emergency (P0)

**1) Cut read traffic to the hot index / cluster** (fastest)

- Pause or slash client QPS; stop abusive load tests; route reads to a standby if you have one; enable gateway throttling.

**2) Cancel huge searches** (when `_tasks` works)

```bash
curl -sS -u "${ES_USERNAME}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_tasks?detailed=true&actions=*search*"
curl -sS -u "${ES_USERNAME}:${ES_PASSWORD}" \
  -X POST "http://${ES_ENDPOINT#http://}/_tasks/{task_id}/_cancel"
```

**3) Watch recovery**

- CPU should fall within **~1–2 min** after load drops.  
- When `search` queue drains, new searches succeed; `all shards failed` stops.

### Short term (days)

- **Scale vCPU/RAM** — search worker count tracks allocated processors (exact formula is **version/vendor-specific**; on small 7.x-style clusters a **2 vCPU** node often maps to **~4** `search` workers — easy to saturate).  
- **Add data nodes** to spread QPS.  
- Add **coordinating-only** nodes if reduce-phase / fan-out is the bottleneck.

### Long term

- Query hygiene: wildcards, huge aggs, deep paging, scripts — see [sop-query-thread-pool.md](sop-query-thread-pool.md).  
- **Capacity:** rough stress thinking: sustainable QPS scales with **workers / p95 latency**; keep **steady CPU < ~60%**, spikes **< ~80%** if possible.

---

## 5. Load-test checklist

### Before the test

| Check | Guidance | How |
|-------|------------|-----|
| SKU | prefer **≥ 4c16g** class nodes | `DescribeInstance` |
| Count | **≥ 3** nodes incl. coordinators if used | `DescribeInstance` |
| Search workers | know baseline (see `_cat/thread_pool`) | `GET _cat/thread_pool?v&h=node_name,name,active,queue,rejected` |
| Replicas | **≥ 1** for hot indices | `_cat/indices` |
| `refresh_interval` | consider **30s** during soak | `GET /{index}/_settings` |

### During the test

| Metric | Safe band | Danger | CMS |
|--------|-----------|--------|-----|
| CPU avg | < ~60% | > ~80% | `NodeCPUUtilization` |
| Search rejected | 0 | > 0 | `SearchThreadpoolRejected` |
| Heap | < ~75% | > ~85% | `NodeHeapMemoryUtilization` |
| GC overhead | low | high | GC logs |
| Latency | < ~2× baseline | > ~5× | EWMA / APM |

### Ramp strategy

```text
Baseline → 50% → 75% → 100% → 120% → target QPS
Hold each step ≥ ~5m; require CPU < ~60% and rejected = 0 before advancing
If CPU > ~80% OR rejected > 0 → drop back one step immediately
```

---

## 6. Case study: 2000 QPS load test → meltdown

**Cluster:** 2 × **2c8g** (search workers ≈ **4** in observed build)

**Timeline:**

```text
T+0:  2000 QPS to index simple-ppt
T+4m: CPU ~5% → 80%+
T+10m: CPU ~85%+, GC overhead visible (~277ms/s class)
T+21m: search queue 1005 > 1000 → EsRejectedExecutionException (~385 rejects)
T+26m: burst of "all shards failed", EWMA ~67μs → ~371μs
T+26m: users report "node offline"
```

**Differentiation:** `DescribeInstance` active; CMS CPU still reporting; no `removed/left`; `rejected` + `all shards failed` present.

**Conclusion:** 2c nodes with **4** search workers cannot carry **2000 QPS** for that workload → CPU peg → pool meltdown.

**Mitigation:** stop test → recovery → retest on **4c16g** (or more nodes) with ramp rules above.

---

## Appendix: quick commands

```bash
aliyun elasticsearch describe-instance --region <region> --instance-id <id>

aliyun cms describe-metric-list --namespace "acs_elasticsearch" \
  --metric-name "NodeCPUUtilization" \
  --dimensions '[{"instanceId":"<id>"}]' \
  --start-time "<5_min_ago_ms>" --end-time "<now_ms>" --period 60

aliyun elasticsearch list-search-log --region <region> --instance-id <id> \
  --type INSTANCELOG --query "removed OR left OR disconnect" \
  --begin-time "<start_ms>" --end-time "<end_ms>"

aliyun cms describe-metric-list --namespace "acs_elasticsearch" \
  --metric-name "SearchThreadpoolRejected" \
  --dimensions '[{"instanceId":"<id>"}]' \
  --start-time "<start_ms>" --end-time "<end_ms>" --period 60

aliyun elasticsearch list-search-log --region <region> --instance-id <id> \
  --type INSTANCELOG --query "shards" \
  --begin-time "<start_ms>" --end-time "<end_ms>"

aliyun elasticsearch list-search-log --region <region> --instance-id <id> \
  --type INSTANCELOG --query "rejected" \
  --begin-time "<start_ms>" --end-time "<end_ms>"

curl -sS --connect-timeout 10 --max-time 30 \
  -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_nodes/hot_threads?threads=3"
curl -sS --connect-timeout 10 --max-time 30 \
  -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_tasks?detailed=true&actions=*search*"
curl -sS --connect-timeout 10 --max-time 30 \
  -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_nodes/stats/thread_pool?filter_path=nodes.*.thread_pool.search,nodes.*.name"
```
