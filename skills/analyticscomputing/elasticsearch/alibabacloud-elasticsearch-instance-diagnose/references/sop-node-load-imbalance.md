# SOP: Per-node load imbalance

**Covers:** `HealthCheck.LoadUnbalanced`

**Reason codes:**

- `Balancing.NodeCPUUnbalanced` — uneven CPU  
- `Balancing.NodeTrafficUnbalanced` — uneven query / index traffic  
- `Balancing.NodeDataUnbalanced` — uneven data placement  
- `Balancing.NodeDiskUnbalanced` — uneven disk utilization  
- `Balancing.NodeMemoryUnbalanced` — uneven heap / memory pressure  

---

## Diagnosis entry: imbalance decision tree

```
Three dimensions (CV = coefficient of variation = stddev / mean)
│
├── Traffic imbalance
│   ├── Per-node NodeQPS CV > ~0.3 → uneven search load
│   └── Per-node NodeIndexQPS CV > ~0.3 → uneven write load
│
├── Data imbalance
│   ├── Per-node shard count CV > ~0.3 → shard skew (very common)
│   ├── Per-node document count CV > ~0.5 → doc skew
│   └── Per-node stored size CV > ~0.3 → storage skew
│
└── Resource imbalance
    ├── Per-node NodeCPUUtilization CV > ~0.3 → CPU skew
    ├── Per-node NodeHeapMemoryUtilization CV > ~0.3 → heap skew
    └── Per-node NodeDiskUtilization CV > ~0.3 → disk skew
```

**Severity heuristic**

- Resource skew **and** any hot node **> ~80%** → treat as **P0** (overload / failure risk)  
- Resource skew but hot nodes **< ~80%** → **P1** (latent risk)  
- Traffic / data skew only, resources healthy → **P2** (optimize when convenient)  

---

## Time-series CV and peak windows

> The diagnosis engine may compute several CV flavors so short spikes are not washed out by daily averages:

| CV flavor | Meaning | Use |
|-----------|---------|-----|
| **CV (avg)** | CV of per-node **means** | Overall trend; can hide short spikes |
| **CV (max)** | CV of per-node **maxes** | Catches peak-window skew |
| **Peak-window CV** | CV across nodes at each timestamp; take **max** | Pinpoints the worst clock time |

**Effective CV** ≈ `max(CV_avg, CV_max, peak_window_CV)`.

If the report shows **peak-window CV ≫ average CV**, the skew is **time-localized** — inspect traffic / tasks in that window.

---

## 1. Shard-count skew (most common driver)

> **Shard skew is the single most common upstream cause of uneven CPU / heap / disk — check it first.**

### 1.1 Quick commands

```bash
GET _cat/nodes?v&h=name,ip,cpu,heap.percent,disk.used_percent,shards&s=shards:desc
GET _cat/allocation?v
# If one node owns far more shards than peers → placement skew
```

### 1.2 Typical causes

| Cause | How you know | Mitigation |
|-------|--------------|------------|
| New nodes not drained/rebalanced | new nodes have far fewer shards | enable rebalance; manual `reroute` |
| Allocation rules | review `cluster.routing.allocation.*` | relax / fix filters |
| Index created when cluster was tiny | old indices lopsided | reindex / shrink / reroute |
| Hot indices packed on few nodes | `_cat/shards` shows concentration | move hot shards |

### 1.3 Rebalance / move

```bash
PUT _cluster/settings
{
  "transient": {
    "cluster.routing.rebalance.enable": "all"
  }
}

POST _cluster/reroute
{
  "commands": [{
    "move": {
      "index": "hot_index",
      "shard": 0,
      "from_node": "node_many_shards",
      "to_node": "node_few_shards"
    }
  }]
}
```

> **`reroute` scope:** `POST _cluster/reroute` issues **allocator-respecting moves** — it is **not** a supported pattern to “flip primary vs replica by hand” just to **even out primary counts** for load. Durable fixes for shard / primary skew are usually **new index settings + reindex**, **shrink** (when applicable), **node add/remove + rebalance**, and fixing **allocation / awareness** rules. Use **`move`** only under **change control**, in a **maintenance window**, after **`_cat/shards`** / explain confirm the plan — **do not** treat ad-hoc primary/replica swaps as a routine performance knob.

---

## 2. Traffic imbalance

### 2.1 Trigger (example)

- Per-node QPS / index QPS **CV > ~0.3** for **~10+ minutes**

### 2.2 Steps

**Step 1 — Node-level traffic proxies**

```bash
GET _cat/nodes?v&h=name,ip,cpu,load_1m,search,search.total,indexing
GET _cat/thread_pool?v&h=node_name,name,active,queue,rejected&s=name
```

**Step 2 — Index-level hot spots**

```bash
GET _cat/indices?v&h=index,pri,rep,docs.count,store.size,search.query_current,indexing.index_current&s=search.query_current:desc
```

**Step 3 — Shard placement for hot indices**

```bash
GET _cat/shards/{hot_index}?v&h=index,shard,prirep,state,docs,store,node
```

### 2.3 Causes and fixes

| Cause | Clues | Mitigation |
|-------|-------|------------|
| No coordinating tier | data nodes take client traffic | add **coordinating** / client nodes |
| Sticky clients | few nodes get all connections | load-balance / shuffle client endpoints |
| Hot shards | shards of hot index on few nodes | reroute or increase shards (plan carefully) |
| Custom `_routing` | doc skew + query skew | redesign routing / keys |
| Multi-zone + awareness | coordinators per zone see uneven ingress | see **Section 2.5** |

### 2.4 Commands (illustrative)

```bash
# After adding coordinators, point clients at the full coordinator pool

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

### 2.5 Multi–availability-zone: uneven **coordinator** load

**Background:** With `cluster.routing.allocation.awareness.attributes: zone`, primaries and replicas spread across zones.

**How skew appears:**

```text
Clients reach Elasticsearch via a VPC endpoint / proxy
  → the proxy prefers coordinators in the **same zone** as the client
  → if **clients** cluster in zone K, zone-K coordinators absorb most traffic
```

**Checks**

```bash
GET _cluster/settings?filter_path=**.awareness*
# e.g. awareness.attributes = zone

GET _cat/nodeattrs?v&h=node,attr,value&s=attr
# inspect zone attrs

GET _cat/nodes?v&h=name,ip,cpu,load_1m,node.role&s=node.role
# focus on nodes without `d` (no data role) if those are your coordinators
```

**Mitigations**

| Option | Notes | When |
|--------|-------|------|
| Spread clients across zones | best if you control deploy topology | preferred |
| Private connectivity to **all** coordinators | bypasses zone-sticky proxy | requires network design |
| More coordinators in hot zones | when traffic mix cannot change | capacity fix |

> **Example:** many app VMs in zone **K**; coordinators in **K / H / G**. Proxy sends K clients to K-only coordinators → K coordinators run hot. Fix: rebalance **clients** across zones or widen coordinator access.

---

## 3. Data imbalance

### 3.1 Trigger (example)

- Shard count, document count, or stored-size **CV > ~0.3** (tune to your catalog)

### 3.2 Steps

```bash
GET _cat/nodes?v&h=name,ip,disk.total,disk.used,disk.avail,disk.used_percent,shards
GET _cat/allocation?v
GET _cat/shards?v&s=node&h=index,shard,prirep,state,docs,store,node
GET _cat/nodes?v&h=name,shards
GET _cat/indices?v&h=index,pri,rep,docs.count,store.size&s=store.size:desc
GET {index}/_settings?include_defaults=true&filter_path=**.number_of_shards,**.number_of_replicas
```

### 3.3 Patterns

#### Type A — Shard count skew

**Signs:** one node has many more shards than others.

**Mitigate:** rebalance + `reroute` as in **Section 1**.

#### Type B — Doc count skew **inside one index**

**Signs:** same index, shard doc counts differ a lot (`_cat/shards/{index}&s=docs:desc`).

**Causes:** custom routing, uneven IDs / hashing.

**Mitigate:** better routing key; `index.routing_partition_size` where appropriate; reindex if needed.

```bash
GET _cat/shards/{index}?v&h=shard,prirep,docs,store,node&s=docs:desc
```

#### Type C — Stored size skew

**Signs:** large gap in **disk used** per node.

**Causes:** huge shards on few nodes; retention; snapshot footprint.

```bash
GET _cat/allocation?v
GET _cat/indices?v&h=index,store.size&s=store.size:desc
```

**Mitigate:**

```bash
POST _cluster/reroute
{
  "commands": [{
    "move": {
      "index": "large_index",
      "shard": 0,
      "from_node": "node_full",
      "to_node": "node_empty"
    }
  }]
}

DELETE old_index_*
```

Optional: nudge disk routing — align with [sop-disk-storage.md](sop-disk-storage.md) before changing watermarks:

```bash
PUT _cluster/settings
{
  "transient": {
    "cluster.routing.allocation.disk.watermark.low": "85%",
    "cluster.routing.allocation.disk.watermark.high": "90%"
  }
}
```

---

## 4. Resource-level imbalance

Cross-links: [sop-cpu-load.md](sop-cpu-load.md) (CPU / hot threads), [sop-memory-gc.md](sop-memory-gc.md) (fielddata / breakers), [sop-disk-storage.md](sop-disk-storage.md) (disk / flood).

### 4.1 CPU skew

**Trigger (example):** per-node CPU **CV > ~0.3** and max node **> ~10%** (sanity floor).

```bash
GET _cat/nodes?v&h=name,ip,cpu,load_1m,load_5m,load_15m&s=cpu:desc
GET _nodes/hot_threads
GET _tasks?detailed=true
GET _cat/tasks?v
```

| Cause | Clues | Mitigation |
|-------|-------|------------|
| Shard skew | hot node has more shards | reroute |
| Hot segments inside shards | even shard counts but skewed CPU | `forcemerge` off-peak (see ES docs); see [sop-cpu-load.md](sop-cpu-load.md) |
| Missing coordinators | one node coordinates most queries | add coordinators |
| Monster queries | hot threads = search | optimize / cancel tasks |

```bash
POST {hot_index}/_forcemerge?max_num_segments=1
```

Use **forcemerge** only with maintenance windows — IO heavy.

### 4.2 Heap skew

**Trigger (example):** heap **CV > ~0.3**.

```bash
GET _cat/nodes?v&h=name,ip,heap.percent,heap.current,heap.max,ram.percent&s=heap.percent:desc
GET _nodes/stats/indices?human&filter_path=nodes.*.indices.fielddata,nodes.*.indices.query_cache,nodes.*.indices.segments
GET _cat/fielddata?v&s=size:desc
```

| Cause | Clues | Mitigation |
|-------|-------|------------|
| Fielddata skew | `_cat/fielddata` dominated by one node | fix aggs; clear caches — [sop-memory-gc.md](sop-memory-gc.md) |
| Query cache | large `query_cache` on some nodes | tune cache limits / queries |
| Segment memory | `segments` stats skewed | merge policy / forcemerge |

### 4.3 Disk skew

**Trigger (example):** disk **CV > ~0.3**.

```bash
GET _cat/nodes?v&h=name,ip,disk.total,disk.used,disk.avail,disk.used_percent&s=disk.used_percent:desc
GET _cat/allocation?v
GET _cat/indices?v&h=index,store.size&s=store.size:desc
GET _cat/shards/{large_index}?v&h=shard,prirep,store,node
```

**Mitigate:** reroute large shards first. Watermark tuning **only** with governance — defaults and danger cases are in [sop-disk-storage.md](sop-disk-storage.md).

```bash
PUT _cluster/settings
{
  "persistent": {
    "cluster.routing.allocation.disk.watermark.low": "80%",
    "cluster.routing.allocation.disk.watermark.high": "85%",
    "cluster.routing.allocation.disk.watermark.flood_stage": "90%"
  }
}

POST _cluster/reroute
{
  "commands": [{
    "move": {
      "index": "large_index",
      "shard": 0,
      "from_node": "node_disk_full",
      "to_node": "node_disk_free"
    }
  }]
}
```

---

## 5. End-to-end workflow

### 5.1 One-pass command bundle

```bash
GET _cat/nodes?v&h=name,ip,cpu,heap.percent,disk.used_percent,load_1m,shards&s=cpu:desc
GET _cat/allocation?v
GET _cat/thread_pool?v&h=node_name,name,active,queue,rejected&s=queue:desc
GET _cat/indices?v&h=index,pri,rep,docs.count,store.size&s=store.size:desc
```

### 5.2 Priority

```text
1. [Urgent] Resource skew + any node > ~85% → reroute / relieve hot nodes now
2. [High] Traffic skew + any node CPU > ~70% → coordinators / hot shard moves
3. [Normal] Data skew only, resources OK → plan rebalance; not always urgent
4. [Watch] Mild skew (CV < ~0.5, resources < ~60%) → document and monitor
```

### 5.3 Causal sketch

```text
Traffic skew
├── no coordinators → data nodes take client work → CPU skew
├── sticky clients → few nodes get connections → CPU skew
└── hot shards → queries hit same nodes → CPU / IO skew

Data skew
├── allocation rules → new nodes underfilled → disk skew
├── custom routing → doc hotspots → shard hotspots
└── huge indices localized → disk / IO skew

Resource skew
├── shard count skew → uneven work → CPU / heap skew
├── hot segments → query concentration → CPU skew
└── uneven fielddata → heap skew
```

---

## Appendix: Quick commands (imbalance)

```bash
GET _cat/nodes?v&h=name,ip,cpu,heap.percent,disk.used_percent,load_1m,shards&s=cpu:desc
GET _cat/allocation?v
GET _cat/shards?v&s=node&h=index,shard,prirep,docs,store,node
GET _cat/thread_pool?v&h=node_name,name,active,queue,rejected
GET _cat/nodes?v&h=name,search,indexing
GET _cat/fielddata?v&s=size:desc
GET _nodes/stats/indices?human&filter_path=nodes.*.indices.fielddata
GET _nodes/hot_threads
PUT _cluster/settings
{
  "transient": {
    "cluster.routing.rebalance.enable": "all"
  }
}
POST _cluster/reroute
{
  "commands": [{
    "move": {
      "index": "index_name",
      "shard": 0,
      "from_node": "node_from",
      "to_node": "node_to"
    }
  }]
}
PUT _cluster/settings
{
  "persistent": {
    "cluster.routing.allocation.disk.watermark.low": "80%",
    "cluster.routing.allocation.disk.watermark.high": "85%"
  }
}
```
