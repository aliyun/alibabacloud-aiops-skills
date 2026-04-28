# SOP: Cluster health diagnosis

**Covers:** `HealthCheck.ClusterStatusRed`, `HealthCheck.ClusterStatusYellow`, `HealthCheck.NodeDisconnected`, `HealthCheck.PendingTasksCritical/Warning`, `HealthCheck.MasterReelection`

> **Related:** If the instance stays `activating` for a long time, the change never finishes, and **cluster Red / unassigned shards** persist together, read [sop-activating-change-stuck.md](sop-activating-change-stuck.md) for **cross-layer causality** and reporting requirements in addition to engine steps in this SOP.

> **Report polish (optional):** [acceptance-criteria.md](acceptance-criteria.md) **§6.1** — Red vs Yellow wording (`unassigned_primary_shards`), primary vs **replica shard** count arithmetic, `unassigned.reason` (incl. optional `INDEX_CREATED` for scoring), affected-index scope, post-remediation `curl` checks, and **scoped** wording when excluding disk/node/CPU. **§6.3** — JVM / breaker / fielddata headline vs GC-only framing.

---

## Diagnosis entry: cluster state decision tree

```
ClusterStatus metric
├── 2 (Red)   → [P0 immediate] primary unassigned — partial data unavailable
├── 1 (Yellow) → [P1 within ~30m] replica unassigned — available but data-loss risk
└── 0 (Green) → OK

ClusterDisconnectedNodeCount metric
└── > 0     → [P0 immediate] node disconnected
```

---

## 1. Cluster status Red (`HealthCheck.ClusterStatusRed`)

### Trigger conditions

- `ClusterStatus == 2` for 2 minutes, or  
- Logs contain `UnavailableShardsException`

### Diagnosis steps

**Step 1 — Find Red indices**

```bash
GET _cat/indices?v&health=red
```

**Step 2 — Why shards are unassigned**

```bash
GET _cat/shards?v&h=index,shard,prirep,state,node,unassigned.reason&s=state
GET _cluster/allocation/explain        # full reason for one representative unassigned shard
# With body — specific shard:
GET _cluster/allocation/explain
{
  "index": "my_index",
  "shard": 0,
  "primary": true
}
```

**Step 3 — Interpret `unassigned.reason`**

| unassigned.reason | Meaning | Mitigation |
|-------------------|---------|------------|
| `NODE_LEFT` | Node left cluster | → see **Section 3 — Node disconnected** |
| `ALLOCATION_FAILED` | Allocation failed more than 5 times | `POST _cluster/reroute?retry_failed=true` |
| `ALLOCATION_DISABLED` | Allocation disabled cluster-wide | `PUT _cluster/settings {"persistent":{"cluster.routing.allocation.enable":"all"}}` |
| `NO_VALID_SHARD_COPY` | No valid shard copy | Data likely lost — restore from snapshot |
| `DISK_THRESHOLD_EXCEEDED` | Disk watermark | → [sop-disk-storage.md](sop-disk-storage.md) |
| `DECIDERS_THROTTLED` | Recovery throttled | Wait / tune throttling / `reroute` as appropriate |
| `DECIDERS_NO` + `box_type` | Hot/warm `box_type` mismatch | Remove `routing.allocation.require.box_type` on the index or add matching nodes |
| `AWAITING_INFO` | Waiting on snapshot | Wait for snapshot or cancel the snapshot job |

**Step 4 — Special cases**

**A. Hot/warm (`box_type`) mismatch**

```bash
GET _cat/nodeattrs?v&h=host,attr,value
PUT /index_name/_settings
{
  "index.routing.allocation.require.box_type": null
}
```

**B. Synonym configuration blocking allocation**

Example errors:

```text
IOException while reading synonyms_path_path: /path/to/file.txt
IllegalArgumentException: term: xxx analyzed to a token with position increment != 1 (got: 2)
```

**Scenario 1 — file path dependency**

```bash
POST /index_name/_close
# Fix synonym file path or remove the dependency
POST /index_name/_open
```

**Scenario 2 — stopword vs synonym conflict** (real case)

- **Root cause:** The synonym file contains terms that are removed by a stop filter (e.g. `"perche à selfie"` where `à` is dropped), producing `position increment != 1`.
- **Remediation:**
  1. Inspect the synonym file for stopword overlap.
  2. Remove or change synonym rules that conflict with stopwords.
  3. Or reorder analysis so the stop filter runs **after** the synonym filter (product-dependent).

**C. Blocked by snapshot**

```bash
GET _snapshot/_status
DELETE _snapshot/repo_name/snapshot_name   # cancel if appropriate
```

**Step 5 — If data cannot be recovered (destructive — confirm with user)**

```bash
POST _cluster/reroute
{
  "commands": [{
    "allocate_empty_primary": {
      "index": "index_name",
      "shard": 0,
      "node": "node_name",
      "accept_data_loss": true
    }
  }]
}
```

### Common causal chains

```text
Node OOM → node leaves → primary missing → Red
Disk full → read-only / allocation blocked → Red
Resize / rolling change in progress → migration not done → temporary Red (often expected; wait)
```

> **vs. change stuck / `activating`:** The last line above is often **expected temporary Red** while migration or rolling progresses. If **`DescribeInstance` stays `activating` far longer than normal**, change records show no progress, and the cluster stays **persistently** Red, treat it as **control-plane orchestration crossed with engine allocation** — use engine steps here **and** [sop-activating-change-stuck.md](sop-activating-change-stuck.md) for cross-layer narrative and evidence.

---

## 2. Cluster status Yellow (`HealthCheck.ClusterStatusYellow`)

### Trigger conditions

- `ClusterStatus == 1` for ~30 minutes, often with **replica** shards `UNASSIGNED`

### Diagnosis steps

**Step 1 — Unassigned replica shards**

```bash
GET _cat/shards?v&h=index,shard,prirep,state,unassigned.reason | grep UNASSIGNED
```

**Step 2 — Allocation explain**

```bash
GET _cluster/allocation/explain
```

### Common causes

| Cause | Clues | Mitigation |
|-------|-------|------------|
| Too few nodes (`replicas >= node count`) | explain: `not enough nodes` | Add nodes or lower `number_of_replicas` |
| Per-index `total_shards_per_node` too low for primaries + replicas | explain often shows **`shards_limit`** and/or **`same_shard`** (order can vary by version); Yellow with **replica** `UNASSIGNED`, primaries started | **Prefer** relax/remove or raise `index.routing.allocation.total_shards_per_node`. **If the cap stays 1**, scaling to **3** data nodes often **still** Yellow — need **(nodes × cap) ≥** shard copies for that index (2p + 1r ⇒ **4** copies) **or** a higher cap / fewer replicas / reindex. **≥4** data nodes is the usual minimum **only when** cap stays **1** for that pattern |
| Change / scale-out in progress | events / actions in `Executing` | Wait (often normal); if **`activating` persists** with no progress → [sop-activating-change-stuck.md](sop-activating-change-stuck.md) |
| Disk watermarks | disk-related explain | Free disk / adjust thresholds — [sop-disk-storage.md](sop-disk-storage.md) |
| Routing / awareness filters | explain shows filter predicates | Review `routing.allocation.*` settings |
| `same_shard` (replica on same node as primary) | explain | Temporarily set replicas to 0 then back to 1 (use with care) |

**Temporary mitigation (reduces redundancy)**

```bash
PUT /index_name/_settings
{
  "index.number_of_replicas": 0
}
# After disk/node issues are fixed, raise replicas again (e.g. 1)
```

### Normal Yellow vs abnormal Yellow

- **Normal Yellow:** during change / scaling; usually clears when the task completes.
- **Abnormal Yellow:** persists **> ~30 minutes** — investigate actively.
- **Long `activating` + Yellow/Red with no progress:** add cross-layer analysis per [sop-activating-change-stuck.md](sop-activating-change-stuck.md); do not only say “wait for the change to finish”.

---

## 3. Node disconnected (`HealthCheck.NodeDisconnected`)

### Trigger conditions

- `ClusterDisconnectedNodeCount > 0` for ~1 minute

### Diagnosis steps

**Step 1 — Which node**

```bash
GET _cat/nodes?v&h=name,ip,heapPercent,cpu,load_1m,diskAvailInBytes,node.role
```

**Step 2 — Logs: when and why**

On the master / node logs, search for:

- `removed` — node removed from cluster  
- `node-left` — identify the node  
- `ERROR` / `WARN` + disconnected node IP — errors just before leave

**Step 3 — Log keywords → cause**

| Log pattern | Likely cause | Next step |
|-------------|--------------|-----------|
| `OutOfMemoryError` / `java.lang.OOM` | JVM OOM | [sop-memory-gc.md](sop-memory-gc.md) |
| `Data too large` / `CircuitBreakingException` | Circuit breaker | [sop-memory-gc.md](sop-memory-gc.md) |
| `rejected` + `write` / `search` | Thread pool saturated | [sop-write-performance.md](sop-write-performance.md) / [sop-query-thread-pool.md](sop-query-thread-pool.md) |
| `watermark` + disk | Disk pressure | [sop-disk-storage.md](sop-disk-storage.md) |
| `Connection refused` / `network` | Network partition | Check host / VPC connectivity |
| `IOException` + `disk` | Disk I/O errors | Check disk health |
| *(no clear error)* | Host / heartbeat timeout | Check host metrics; restart node if needed |

**Step 4 — Restart the node (or process) if required, then watch recovery**

After the underlying issue is addressed, restart the failed node per your change process, then monitor shard recovery:

```bash
GET _cat/recovery?v&active_only=true&h=index,shard,time,type,stage,source_node,target_node
```

### Frequent root causes (from 150+ cases)

1. **Node OOM** (most common): heap pressure → long GC pauses → heartbeat timeout → node leaves  
2. **Slow disk I/O:** writes + merges saturate I/O → heartbeat timeout  
3. **CPU pegged:** no CPU for heartbeat handling → timeout  
4. **Too many shards:** e.g. **> ~50k** shards → slow cluster-state application → node appears offline (details below)  
5. **ILM backlog:** ILM work saturates generic thread pool → instability  
6. **Recovery concurrency too high:** small nodes + aggressive recovery settings → generic pool full → node leaves

### Special case: recovery concurrency too high

**Typical pattern:**

- During resize / change, cold nodes drop and cluster goes Red  
- Logs: `rejected execution of TransportReplicationAction`  
- Generic thread pool queue full

**Chain:**

```text
Manually raised recovery concurrency (e.g. concurrent_recoveries = 128)
  → small node size (e.g. 4c16g cold)
  → generic queue full, high CPU
  → heartbeat lag → master marks node disconnected
```

**Mitigation:**

1. Reset recovery-related settings to defaults (Elasticsearch generally discourages changing these):

```bash
PUT _cluster/settings
{
  "persistent": {
    "cluster.routing.allocation.node_concurrent_recoveries": null,
    "cluster.routing.allocation.node_initial_primaries_recoveries": null,
    "cluster.routing.allocation.node_concurrent_incoming_recoveries": null,
    "cluster.routing.allocation.node_concurrent_outgoing_recoveries": null
  }
}
```

2. Restart affected nodes.  
3. **Note:** Raising these rarely improves migration speed proportionally and can destabilize the cluster.

### Special case: too many shards → node disconnect

**Typical pattern:**

- **50k+** shards; nodes flap offline  
- Master log: `cluster state applier task [...] took [57.9s] which is above the warn threshold of [30s]`  
- `no master connection` style messages

**Chain:**

```text
Very high shard count
  → long IndicesClusterStateService / applier latency (tens of seconds)
  → heartbeat lag
  → master marks node disconnected
```

**Checks:**

```bash
GET _cluster/health?filter_path=active_shards,unassigned_shards,number_of_pending_tasks
GET _cat/pending_tasks?v
# Search master logs for "cluster state applier task" duration warnings
```

**Guidelines:**

- Roughly **≤ 20 shards per GB heap** on a data node (e.g. 16 GB heap → ~320 shards per node guideline)  
- **≤ ~1000 shards per node** as a practical ceiling  
- **≤ ~50k total shards** per cluster as a soft target

**Mitigation:**

- Drop expired indices (especially many small log indices)  
- Merge / shrink where possible — see [sop-configuration.md](sop-configuration.md) for Shrink-related guidance  
- Split clusters if the workload allows

### After a node leaves

```text
Node leaves
  → shard rerouting (Yellow; Red if primaries affected)
  → higher I/O / network (recovery)
  → risk of cascading failures if the cluster was already hot
```

---

## 4. Pending tasks backlog (`HealthCheck.PendingTasksCritical/Warning`)

### Trigger conditions

- **Critical:** `pending_tasks > node_count × 50` for ~5 minutes  
- **Warning:** `pending_tasks > node_count × 20` for ~10 minutes

### Diagnosis steps

**Step 1 — Inspect pending tasks**

```bash
GET _cluster/pending_tasks
GET _cat/pending_tasks?v
```

**Step 2 — Task flavor**

| Dominant task type | Likely cause | Mitigation |
|--------------------|--------------|------------|
| Many `put-mapping` | Mapping explosion / too many fields | Cap dynamic fields / redesign mappings |
| Many `create-index` | Runaway index creation | Reduce dynamic index churn |
| Many ILM-related | ILM backlog | Temporarily `POST _ilm/stop`, reduce shards / fix ILM, then `POST _ilm/start` |
| Many `shard-started` | Nodes joining/leaving often | Fix node stability (Section 3) |
| Master CPU high | Undersized dedicated master | Scale dedicated master tier |

**Step 3 — Temporary relief (ILM pile-up)**

```bash
POST _ilm/stop
GET _ilm/status
# After remediation
POST _ilm/start
```

---

## 5. Master re-election (`HealthCheck.MasterReelection`)

### Trigger conditions

- Monitoring shows the **elected master node id** changed

### Diagnosis steps

**Step 1 — Current master**

```bash
GET _cat/master?v
GET _cat/nodes?v&h=name,ip,node.role,master
```

**Step 2 — Election in logs**

Search for: `elected-as-master`, `master node changed`, `new_master`

**Step 3 — Typical drivers**

1. Previous master **OOM** — memory metrics + OOM logs on old master  
2. Previous master **CPU saturated**  
3. **Long GC pauses** — no heartbeat during GC  
4. **Network partition** — subset of nodes cannot reach master → new election

**Step 4 — Dedicated master topology**

```bash
GET _cat/nodes?v&h=name,ip,node.role
# Role includes `m` → master-eligible
# Only one `m` in production → single point of failure risk
```

> **Practice:** Use **dedicated master nodes** in production (often **3** master-eligible nodes that do not hold data) instead of data nodes also being master-eligible.

---

## Appendix: Quick command reference (cluster health)

```bash
GET _cluster/health?pretty
GET _cat/health?v

GET _cat/nodes?v&h=name,ip,heapPercent,cpu,load_1m,disk.used_percent,node.role

GET _cat/shards?v&s=state&h=index,shard,prirep,state,node,unassigned.reason

GET _cluster/allocation/explain

POST _cluster/reroute?retry_failed=true

PUT _cluster/settings
{
  "persistent": {
    "cluster.routing.allocation.enable": "all"
  }
}

GET _cat/recovery?v&active_only=true
```
