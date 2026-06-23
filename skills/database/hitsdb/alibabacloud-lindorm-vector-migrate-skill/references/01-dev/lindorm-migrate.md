# Lindorm Data Reading Interface

Lindorm search engine is ES API compatible (port 30070); accessible via `curl` or any HTTP client.

## Connection and Verification

```bash
# VPC address
curl -s -u <username>:<password> \
  "http://<instance_id>-proxy-search-vpc.lindorm.aliyuncs.com:30070/"

# Public address
curl -s -u <username>:<password> \
  "http://<instance_id>-proxy-search-pub.lindorm.aliyuncs.com:30070/"
```

### Address Format

| Type | Address | Port |
|------|---------|------|
| VPC | `<instance_id>-proxy-search-vpc.lindorm.aliyuncs.com` | 30070 |
| Public | `<instance_id>-proxy-search-pub.lindorm.aliyuncs.com` | 30070 |
| Wide table (MySQL protocol) | `<instance_id>-proxy-lindorm-pub.lindorm.aliyuncs.com` | 33060 |
| AI engine | `<instance_id>-proxy-ai-pub.lindorm.aliyuncs.com` | 9002 |

## Get Schema

```bash
curl -s -u <username>:<password> \
  "http://<host>:30070/<index_name>/_mapping"
```

Lindorm mapping is similar to ES, but the vector field type is **`knn_vector`** (not ES's `dense_vector`), and the distance metric is in `method.space_type`:

```json
{
  "<index_name>": {
    "mappings": {
      "properties": {
        "embedding": {
          "type": "knn_vector",
          "dimension": 128,
          "data_type": "float",
          "method": {
            "engine": "lvector",
            "name": "hnsw",
            "space_type": "cosinesimil",
            "parameters": {"m": 24, "ef_construction": 500}
          }
        },
        "title": {"type": "text"},
        "category": {"type": "keyword"}
      }
    }
  }
}
```

### Fields the Agent should focus on when extracting vector fields

| Field | Description |
|-------|-------------|
| `type` | `knn_vector` (Lindorm-specific) or `dense_vector` (ES compatibility mode) |
| `dimension` | Dimension (note: Lindorm uses `dimension`, not ES's `dims`) |
| `method.space_type` | Distance metric: `cosinesimil` / `l2` / `innerproduct` |
| `method.name` | Index algorithm: `hnsw` / `ivfpq` / `ivfbq` |
| `method.engine` | Fixed `lvector` |

### Distance Metric Mapping

| Lindorm `space_type` | Standard name |
|----------------------|---------------|
| `cosinesimil` | COSINE |
| `l2` | L2 |
| `innerproduct` | IP |

## Document Count

```bash
curl -s -u <username>:<password> "http://<host>:30070/<index_name>/_count" \
  -H "Content-Type: application/json" \
  -d '{"query": {"match_all": {}}}'
```

## Data Scan (Scroll API)

> **Lindorm does not support PIT API**; Scroll API must be used.

### First Query

```bash
curl -s -u <username>:<password> "http://<host>:30070/<index_name>/_search?scroll=5m" \
  -H "Content-Type: application/json" \
  -d '{
    "size": 1000,
    "query": {"match_all": {}},
    "sort": [{"_id": "asc"}]
  }'
```

Extract `_scroll_id` and `hits` from response:

```json
{
  "_scroll_id": "<scroll_id>",
  "hits": {
    "hits": [
      {
        "_id": "doc_001",
        "_source": {"title": "...", "embedding": [0.1, 0.2, ...]},
        "sort": ["doc_001"]
      }
    ]
  }
}
```

### Pagination

```bash
curl -s -u <username>:<password> "http://<host>:30070/_search/scroll" \
  -H "Content-Type: application/json" \
  -d '{"scroll": "5m", "scroll_id": "<scroll_id>"}'
```

### Close Scroll

```bash
curl -s -u <username>:<password> -X DELETE "http://<host>:30070/_search/scroll" \
  -H "Content-Type: application/json" \
  -d '{"scroll_id": "<scroll_id>"}'
```

### Agent Scan Loop Key Points

1. Sort by `_id`, ensuring ordered traversal
2. Checkpoint resume: cursor is the `_id` string of the last item. On resume, add `_id > cursor` filter to the first query; subsequent scroll pages automatically return data after the cursor
3. End loop when `hits` is empty
4. Scroll context auto-expires after 5 minutes

## Incremental Migration (Range Filter)

Same as ES, replace the scroll query's `match_all` with a `range` filter:

```bash
curl -s -u <username>:<password> "http://<host>:30070/<index_name>/_search?scroll=5m" \
  -H "Content-Type: application/json" \
  -d '{
    "size": 1000,
    "query": {
      "range": {"<incremental_field>": {"gte": "<incremental_since>"}}
    },
    "sort": [{"_id": "asc"}]
  }'
```

### Incremental Migration Notes

| Item | Description |
|------|-------------|
| `incremental_field` | An existing date type field on the Lindorm source |
| `incremental_since` | Value format must match the field's storage format |
| Scroll + range | Scroll API supports range queries, fully compatible with full migration scroll mechanism |
| Relationship with checkpoint | cursor (`_id` string) controls pagination position; range filter controls data scope; the two are orthogonal |

## Cluster Info (Storage Capacity)

```bash
# Cluster stats
curl -s -u <username>:<password> "http://<host>:30070/_cluster/stats"

# Index list
curl -s -u <username>:<password> "http://<host>:30070/_cat/indices?format=json&h=index,docs.count,store.size,health,status"

# Cluster health
curl -s -u <username>:<password> "http://<host>:30070/_cluster/health"
```

### List All Indices (Index Selection)

When the user does not know which index to migrate, first list all source indices for selection. The `_cat/indices` response above example:

```json
[
  {"index": "product_vector", "docs.count": "500000", "store.size": "1.2gb", "health": "green", "status": "open"},
  {"index": "user_embedding", "docs.count": "200000", "store.size": "890mb", "health": "green", "status": "open"}
]
```

The Agent filters out system indices starting with `.` and presents the remaining index list to the user via AskUserQuestion for selection.

## Read Index Settings (TTL Detection)

Read index settings during migration pre-checks to detect if row-level TTL is configured:

```bash
curl -s -u <username>:<password> "http://<host>:30070/<index_name>/_settings"
```

Extract `index.doc_ttl.field` and `index.doc_ttl.unit` from response:

```json
{
  "<index_name>": {
    "settings": {
      "index": {
        "knn": "true",
        "doc_ttl.field": "expire_time",
        "doc_ttl.unit": "s"
      }
    }
  }
}
```

| Field | Description |
|-------|-------------|
| `doc_ttl.field` | TTL field name; this field stores the expiration timestamp (absolute time) for each row |
| `doc_ttl.unit` | Time unit: `s` (second-level timestamp) or `ms` (millisecond-level timestamp) |
| No `doc_ttl` | Index has no row-level TTL configured |

> After detecting `doc_ttl`, pass through the same configuration to the target during migration. See `references/02-ops/ttl-config.md`.

## IVFPQ/IVFBQ Offline Index Building

HNSW is queryable immediately after write. IVFPQ/IVFBQ require manually triggering a build after all data is written. Build command, status polling, and response parsing are detailed in `references/03-ref/bulk-write.md` (IVFPQ/IVFBQ offline index building section).

## Rate Limiting

| Item | Description |
|------|-------------|
| Write throttling | QPS limits per instance tier; exceeding returns error |
| Scroll context | Concurrent scroll context count is limited (depends on instance tier); close promptly when done |
| Whitelist | IP whitelist must be configured before public network access |
| Migration recommendation | Check instance tier before migration; batch_size=500~1000; use exponential backoff on errors |

## Key Notes

| Item | Description |
|------|-------------|
| Port | Search engine fixed at 30070 |
| PIT not supported | Must use Scroll API; cannot use `open_point_in_time` |
| Vector field | `knn_vector` (not `dense_vector`); dimension key is `dimension` |
| Distance metric | In `method.space_type` (not `similarity`) |
| Scroll cursor | Sort by `_id`; cursor is the `_id` string of the last item |
| `scroll="5m"` | Scroll context auto-expires after 5 minutes |
| HNSW | Queryable immediately after write; no offline build needed |
| IVFPQ/IVFBQ | Requires calling `_plugins/_vector/index/build` after write to trigger build |
