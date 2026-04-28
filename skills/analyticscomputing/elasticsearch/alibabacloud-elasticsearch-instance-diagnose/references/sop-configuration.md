# SOP: Configuration safety and API health

**Covers:** `ConfigSafety.DangerousClusterConfig` (P1), `ConfigSafety.DangerousIndexConfig` (P1), `ApiHealth.HighErrorRate` (P1), `CapacityPlanning.SlowRecovery` (P2)

*(Event IDs aligned with catalog **V4.5+**.)*

---

## 1. Dangerous cluster settings (`ConfigSafety.DangerousClusterConfig`, P1)

### Trigger conditions (any one)

- `cluster.routing.allocation.cluster_concurrent_rebalance > 16`
- `cluster.routing.allocation.node_concurrent_recoveries > 8`
- `indices.recovery.max_bytes_per_sec > 200MB`

### Why it is risky

These are often raised during data migration to speed it up. **Too high** values tend to:

1. Saturate the **generic** thread pool → pending tasks pile up → nodes drop  
2. Saturate node **CPU / I/O** → heartbeat timeouts → nodes drop  
3. Trigger **cascading failures** → cluster Red

### Typical cases

**Case 1 — cold tier resize, `rebalance=128`**

- Before the change, `cluster_concurrent_rebalance=128` was set to speed migration  
- Many shards move at once → CPU / I/O saturated → node leaves → Red  

**Case 2 — node loss with `recovery=200mb`**

- `max_bytes_per_sec=200mb` to speed recovery  
- Network + I/O saturated together → heartbeat timeout → node leaves  

### Diagnosis steps

**Step 1 — Inspect current settings**

```bash
GET _cluster/settings?include_defaults=true&filter_path=*.cluster.routing.allocation*,*.indices.recovery*
```

**Step 2 — Compare to safe thresholds**

| Setting | Risky if | Suggested default | Off-peak ceiling |
|---------|----------|-------------------|------------------|
| `cluster_concurrent_rebalance` | > 16 | 2 | 8 |
| `node_concurrent_recoveries` | > 8 | 2 | 4 |
| `recovery.max_bytes_per_sec` | > 200MB | 40mb | 100mb |

**Step 3 — Restore safer settings**

```bash
PUT _cluster/settings
{
  "persistent": {
    "cluster.routing.allocation.cluster_concurrent_rebalance": "2",
    "cluster.routing.allocation.node_concurrent_recoveries": "2",
    "indices.recovery.max_bytes_per_sec": "40mb"
  }
}
```

### Tuning guidance

- **Peak hours:** keep defaults (rebalance `2`, recovery concurrency `2`, recovery rate `40mb`).  
- **Off-peak migration:** you may raise modestly, but stay **below** the ceilings in the table.  
- **Before peak returns:** reset to defaults.

---

## 2. Dangerous index settings (`ConfigSafety.DangerousIndexConfig`, P1)

### Trigger conditions (any one)

- Ngram tokenizer: `max_gram > 100` or `min_gram = 0`  
- Small index (stored size under ~10 GB) with **primary shard count > 10**  
- **Zero replicas** and **no usable snapshot** (data-loss risk)

### Case A — bad Ngram settings

**Example:** write timeouts with `min_gram=0`, `max_gram=1024`.

- `min_gram=0` can produce empty tokens → `ArrayIndexOutOfBoundsException`  
- `max_gram=1024` explodes tokens per term → high CPU on indexing, timeouts  

**Inspect tokenizer settings**

```bash
GET /index_name/_settings?filter_path=*.analysis.tokenizer
```

**Safer Ngram example** (adjust names to your mapping; `min_gram` must be **≥ 1**; `max_gram` often **≤ ~20**, never **> 100**):

```json
{
  "analysis": {
    "tokenizer": {
      "ngram_tokenizer": {
        "type": "ngram",
        "min_gram": 2,
        "max_gram": 10
      }
    }
  }
}
```

**Fix (requires reindex)**

```bash
# 1. Create new index with corrected analysis
PUT /new_index { ... }

# 2. Reindex
POST _reindex
{
  "source": {"index": "old_index"},
  "dest": {"index": "new_index"}
}

# 3. Swap alias
POST _aliases
{
  "actions": [
    {"remove": {"index": "old_index", "alias": "alias_name"}},
    {"add": {"index": "new_index", "alias": "alias_name"}}
  ]
}

# 4. Delete old index
DELETE /old_index
```

### Case B — too many primaries on a small index

**Find candidates**

```bash
GET _cat/indices?v&s=store.size:asc&h=health,index,pri,rep,docs.count,store.size
# Look for store.size < ~10GB but pri > 10
```

**Why it hurts**

- Each shard is a Lucene index (~**50–100MB** heap per shard is a common rule-of-thumb band)  
- Many tiny shards slow the master and increase GC pressure  

**Mitigation — reduce primary count (Shrink)**

Shrink requires the index to be **read-only** and (for a single target shard layout) primaries typically co-located per Elasticsearch shrink rules — follow product docs for your version.

```bash
# Step 1: Route to one node and block writes
PUT /old_index/_settings
{
  "index.routing.allocation.require._name": "target_node",
  "index.blocks.write": true
}

# Step 2: Shrink
POST /old_index/_shrink/new_index
{
  "settings": {
    "index.number_of_shards": 2,
    "index.number_of_replicas": 1
  }
}

# Step 3: After verification, delete old index and point aliases as needed
```

### Case C — zero replicas and no snapshot

**Risk:** if a node holding the only copy goes away, data can be **lost permanently**.

**Check**

```bash
GET _cat/indices?v&h=index,rep&s=rep:asc
# indices with rep=0
GET _cat/snapshots?v
# confirm backup coverage
```

**Mitigation**

```bash
PUT /index_name/_settings
{
  "index.number_of_replicas": 1
}
# and/or schedule snapshot policies
```

---

## 3. High Elasticsearch API error rate (`ApiHealth.HighErrorRate`, P1)

### Trigger conditions

- HTTP **5xx** rate **> ~5%** for **~3 minutes**  
- APIs such as `_cat/indices`, `_cat/nodes` **repeatedly** fail  

### Diagnosis steps

**Step 1 — Probe key APIs**

```bash
GET _cat/health?v
GET _cat/nodes?v
GET _cat/indices?v
GET _cluster/stats
```

**Step 2 — Elasticsearch logs**

Filter **ERROR** on master / data nodes. Watch for `NullPointerException`, `NumberFormatException`, `IllegalStateException`, etc.

**Step 3 — Error pattern → cause**

| Exception / pattern | Likely cause | Action |
|---------------------|--------------|--------|
| `NullPointerException` | Metadata glitch / version bug | Restart affected nodes; escalate if cluster-wide |
| `NumberFormatException` | Counter overflow (known-class bugs in some versions) | Upgrade or restart |
| `IllegalStateException` | Bad index lifecycle state | `POST /index/_close` then `POST /index/_open` |
| `CircuitBreakingException` | Memory pressure | [sop-memory-gc.md](sop-memory-gc.md) |

**Examples**

- `_cat/indices` NPE on a specific build → often **node restart** after vendor guidance  
- Brand-new cluster: `_cat` empty/errors until cluster formation finishes → **wait**  

**Step 4 — Emergency mitigation**

```bash
# Node-level issues: restart the affected node (console / automation)

# Index state issues:
POST /problem_index/_close
POST /problem_index/_open
```

---

## 4. Slow data migration / recovery (`CapacityPlanning.SlowRecovery`, P2)

### Trigger conditions

- Recovery throughput stays **below roughly half** of the configured cap **and** estimated completion **exceeds ~4 hours** (tune thresholds to your SLOs)

### Diagnosis steps

**Step 1 — Active recovery**

```bash
GET _cat/recovery?v&active_only=true&h=index,shard,time,type,stage,source_node,target_node,bytes_total,bytes_percent
GET _cat/recovery?v&active_only=true&h=index,shard,time,stage,translog_ops,translog_ops_percent
```

**Step 2 — Rough ETA**

```text
ETA ≈ remaining_bytes / observed_throughput
Example: 500 GB left at 40 MB/s → on the order of hours (validate live)
```

**Step 3 — Tune migration speed to the window**

**Speed up off-peak** (only if the cluster has headroom — stay under **Section 1** safety caps):

```bash
PUT _cluster/settings
{
  "transient": {
    "indices.recovery.max_bytes_per_sec": "100mb"
  }
}
```

Use `200mb` only with extreme care and monitoring; the **danger** threshold in Section 1 is **> 200MB**.

**Slow down during peak** (protect latency)

```bash
PUT _cluster/settings
{
  "transient": {
    "indices.recovery.max_bytes_per_sec": "40mb"
  }
}
```

**Pause rebalance** (if deferrable)

```bash
PUT _cluster/settings
{
  "transient": {
    "cluster.routing.rebalance.enable": "none"
  }
}

# Re-enable off-peak
PUT _cluster/settings
{
  "transient": {
    "cluster.routing.rebalance.enable": "all"
  }
}
```

### Examples

- **~1.5 TB** at **~100 MB/s** → many hours can still be **normal**; no action if within SLO  
- Migration “stuck” with cap **10 MB/s** → raising toward **40–100 MB/s** during a safe window often helps  

---

## Appendix: Quick commands (configuration and API health)

```bash
GET _cluster/settings?include_defaults=true

PUT _cluster/settings
{
  "persistent": {
    "cluster.routing.allocation.cluster_concurrent_rebalance": "2",
    "cluster.routing.allocation.node_concurrent_recoveries": "2",
    "indices.recovery.max_bytes_per_sec": "40mb"
  }
}

GET /index_name/_settings?filter_path=*.analysis

GET _cat/indices?v&s=store.size:asc&h=health,index,pri,rep,docs.count,store.size

GET _cat/snapshots?v

GET _cluster/health
GET _cat/health?v
GET _cat/indices?v

GET _cat/recovery?v&active_only=true
```
