# Elasticsearch REST API catalog (`curl`)

Use `curl` directly against the Elasticsearch data plane.

```bash
export ES_ENDPOINT="<host:9200 or http://host:9200>"
export ES_USERNAME="elastic"
export ES_PASSWORD="<elasticsearch-admin-password>"

# Generic template (HTTP)
curl -sS -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/<endpoint>?pretty"
```

> If the cluster only serves **HTTPS**, switch to `https://` and add CA options or `-k` for testing only.

---

## Cluster layer

| Endpoint | Purpose |
|----------|---------|
| `GET /_cluster/health` | Cluster health (green/yellow/red) |
| `GET /_cluster/stats` | Cluster statistics (nodes/shards/disk/JVM) |
| `GET /_cluster/settings` | Cluster dynamic settings |
| `GET /_cluster/pending_tasks` | Master pending tasks |
| `POST /_cluster/allocation/explain` | Explain unassigned shards (requires unassigned shards) |

---

## Node layer

| Endpoint | Purpose |
|----------|---------|
| `GET /_cat/nodes?v` | Node list (IP, CPU, heap, load) |
| `GET /_cat/nodes?v&s=cpu:desc` | Nodes sorted by CPU |
| `GET /_nodes/hot_threads?threads=3` | Hot threads (when CPU is high) |
| `GET /_nodes/stats/thread_pool` | Thread pool queue / rejected |
| `GET /_nodes/stats/breaker` | Circuit breaker trips |
| `GET /_nodes/stats/jvm` | JVM / GC stats |

> **Version note**
> - The `?local` flag on `GET /_cat/nodes` was deprecated in 7.x and removed in 8.0 — **do not use it**.
> - Other node APIs are compatible across 6.x / 7.x / 8.x.

---

## Index and shard layer

| Endpoint | Purpose |
|----------|---------|
| `GET /_cat/indices?v&s=pri.store.size:desc` | Indices by primary store size |
| `GET /_cat/indices?v&s=pri:desc` | Indices by primary shard count |
| `GET /_cat/shards?v&s=state` | Shards including unassigned reasons |
| `GET /_cat/allocation?v&bytes=gb` | Per-node allocation and disk |
| `GET /_cat/fielddata?v&s=size:desc` | Fielddata memory (6.x may need extra settings) |
| `GET /_cat/recovery?v&active_only=true` | Active shard recovery |

---

## Task layer

| Endpoint | Purpose |
|----------|---------|
| `GET /_cat/tasks?v&detailed=true` | Running tasks with descriptions |
| `GET /_tasks?detailed=true` | Task details (search/write timeouts) |

---

## Snapshots and ILM

| Endpoint | Purpose |
|----------|---------|
| `GET /_snapshot/_status` | In-flight snapshot operations |
| `GET /_cat/snapshots/<repo>?v` | Snapshot list (repository required) |
| `GET /_ilm/status` | ILM status (**Elasticsearch 7.0+** only) |

---

## Version compatibility

| ES version | Compatible endpoints | Not supported | Notes |
|------------|----------------------|---------------|--------|
| **7.x – 8.x** | 18 / 18 (100%) | — | Full |
| **6.x** | 17 / 18 (94%) | `_ilm/status` | ILM introduced in 7.0 |

**Notes**
- `_ilm/status`: ILM is not available on 6.x.
- Do not use `?local` on `_cat/nodes` on 8.x.
- `_cat/fielddata` on 6.x may require additional settings to return data.

---

## Scenario quick map

| Scenario class | Primary endpoints |
|----------------|-------------------|
| Cluster Red/Yellow, unassigned shards | `POST /_cluster/allocation/explain` + `GET /_cat/shards` |
| Sustained high CPU, hot threads | `GET /_nodes/hot_threads` + `GET /_cat/nodes` |
| JVM pressure, GC | `GET /_nodes/stats/jvm` + `GET /_nodes/stats/breaker` |
| Thread pool saturation / rejections | `GET /_nodes/stats/thread_pool` |
| Disk pressure, large indices | `GET /_cat/allocation` + `GET /_cat/indices` |
| Slow search/write, timeouts | `GET /_cat/tasks` + `GET /_tasks?detailed=true` |
| Snapshot failures | `GET /_snapshot/_status` + `GET /_cat/snapshots/<repo>` |
| Master backlog | `GET /_cluster/pending_tasks` |
| ILM issues | `GET /_ilm/status` |
