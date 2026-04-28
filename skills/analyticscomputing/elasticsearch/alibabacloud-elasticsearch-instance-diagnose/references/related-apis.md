# Related APIs

Complete list of Alibaba Cloud OpenAPIs and Elasticsearch REST APIs used by this skill.

---

## Control plane (OpenAPI)

OpenAPI **action names** follow the official Alibaba Cloud API (PascalCase), e.g. [Elasticsearch API](https://api.aliyun.com/document/elasticsearch/2017-06-13/overview) and [CloudMonitor (CMS) API](https://api.aliyun.com/document/Cms/2019-01-01/overview). Use the **Aliyun CLI plugin** subcommands (lowercase-hyphenated) when showing shell examples.

### Elasticsearch OpenAPI

| Product | API action | Description | Entry point |
|---------|------------|-------------|-------------|
| elasticsearch | DescribeInstance | Instance details (status, version, cluster-related fields) | `check_es_instance_health.py` / `openapi_cli_collect.py` |
| elasticsearch | ListInstance | List instances | `aliyun elasticsearch list-instance` |
| elasticsearch | ListSearchLog | Instance logs (instance, slow, GC, etc.) | `check_es_instance_health.py` / `openapi_cli_collect.py` |
| elasticsearch | ListActionRecords | Change / action records | `aliyun elasticsearch list-action-records` |
| elasticsearch | ListAllNode | Cluster node information | `aliyun elasticsearch list-all-node` |

### Alibaba Cloud Monitor (CMS) OpenAPI

| Product | API action | Description | Entry point |
|---------|------------|-------------|-------------|
| cms | DescribeMetricList | Time-series metrics | `check_es_instance_health.py` / `openapi_cli_collect.py` |
| cms | DescribeSystemEventAttribute | System events | `check_es_instance_health.py` / `openapi_cli_collect.py` |
| cms | DescribeMetricMetaList | Metric metadata (available metric catalog) | `aliyun cms describe-metric-meta-list` |

---

## Data plane (Elasticsearch REST API)

### Cluster health and state

| API | Endpoint | Description | Invocation |
|-----|----------|-------------|--------------|
| Cluster health | `GET /_cluster/health` | Cluster health (green/yellow/red) | `curl` |
| Cluster stats | `GET /_cluster/stats` | Cluster statistics | `curl` |
| Pending tasks | `GET /_cluster/pending_tasks` | Master pending tasks | `curl` |
| Allocation explain | `POST /_cluster/allocation/explain` | Unassigned shard reasons | `curl` |

### Nodes

| API | Endpoint | Description | Invocation |
|-----|----------|-------------|--------------|
| Nodes stats | `GET /_nodes/stats` | Node stats (CPU/memory/disk) | `curl` |
| Hot threads | `GET /_nodes/hot_threads` | Hot thread stacks | `curl` |
| Nodes JVM | `GET /_nodes/stats/jvm` | JVM statistics | `curl` |
| Thread pools | `GET /_nodes/stats/thread_pool` | Thread pool stats | `curl` |
| Circuit breakers | `GET /_nodes/stats/breaker` | Breaker trips | `curl` |
| Cat nodes | `GET /_cat/nodes` | Node overview | `curl` |
| Cat nodes CPU | `GET /_cat/nodes?h=name,cpu,load_1m` | CPU-oriented view | `curl` |

### Indices and shards

| API | Endpoint | Description | Invocation |
|-----|----------|-------------|--------------|
| Cat indices | `GET /_cat/indices` | Index list | `curl` |
| Cat indices by size | `GET /_cat/indices?s=store.size:desc` | Indices sorted by size | `curl` |
| Cat shards | `GET /_cat/shards` | Shard layout | `curl` |
| Cat allocation | `GET /_cat/allocation` | Disk / shard allocation | `curl` |

### Tasks and recovery

| API | Endpoint | Description | Invocation |
|-----|----------|-------------|--------------|
| Tasks | `GET /_tasks` | Running tasks | `curl` |
| Tasks detailed | `GET /_tasks?detailed=true` | Detailed tasks | `curl` |
| Cat tasks | `GET /_cat/tasks` | Task overview | `curl` |
| Cat recovery | `GET /_cat/recovery` | Shard recovery | `curl` |

### Snapshots and ILM

| API | Endpoint | Description | Invocation |
|-----|----------|-------------|--------------|
| Snapshot status | `GET /_snapshot/_status` | In-flight snapshots | `curl` |
| ILM status | `GET /_ilm/status` | ILM status (Elasticsearch 7.0+) | `curl` |

---

## Dependencies

```
aliyun CLI >= 3.3.1
elasticsearch>=7,<9   # client library if used by tooling (optional for curl-only path)
```

---

## Permissions

See [ram-policies.md](ram-policies.md).
