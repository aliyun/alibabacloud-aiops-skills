# Qdrant Data Reading Interface

Qdrant provides a complete REST API (port 6333); all operations can be performed via `curl`.

## Connection and Verification

```bash
# Local
curl -s http://localhost:6333/collections

# Qdrant Cloud (requires API Key)
curl -s -H "api-key: <api_key>" \
  "https://<cluster_id>.qdrant.io:6333/collections"
```

### List All Collections (Index Selection)

The `/collections` endpoint above also returns the list of all Collections. When the user does not know which Collection to migrate, use this endpoint to list all source Collections for selection:

```json
{
  "result": {
    "collections": [
      {"name": "product_vector"},
      {"name": "user_embedding"},
      {"name": "order_items"}
    ]
  }
}
```

The Agent extracts the `name` list from `result.collections` and presents it to the user via AskUserQuestion for selection. After the user selects one, proceed to the "Get Schema" section to retrieve detailed information about that Collection.

## Get Schema (Collection Info)

```bash
curl -s "http://localhost:6333/collections/<collection_name>"
```

Response structure:

```json
{
  "result": {
    "status": "green",
    "points_count": 100000,
    "vectors_count": 100000,
    "config": {
      "params": {
        "vectors": {
          "size": 128,
          "distance": "Cosine"
        }
      }
    },
    "payload_schema": {
      "title": { "type": "keyword" },
      "price": { "type": "float" },
      "category": { "type": "keyword" },
      "updated_at": { "type": "datetime" }
    }
  }
}
```

### Fields the Agent should focus on when extracting

| Field | Description |
|-------|-------------|
| `config.params.vectors` | Single-vector mode: `{size, distance}`. Multi-vector mode: dict, each key is a named vector |
| `config.params.vectors.distance` | `Cosine` / `Euclid` / `Dot` |
| `points_count` | Total point count |
| `payload_schema` | Qdrant auto-inferred type mapping, may be incomplete |

### Multi-Vector Mode (Named Vectors)

Qdrant supports multiple named vectors in a single Collection. Detection method:

```python
vectors_config = info["result"]["config"]["params"]["vectors"]

if isinstance(vectors_config, dict) and "size" not in vectors_config:
    # Multi-vector mode: vectors_config is {name: {size, distance}, ...}
    # e.g.: {"image": {"size": 512, "distance": "Cosine"}, "text": {"size": 128, "distance": "Cosine"}}
    named_vectors = vectors_config
else:
    # Single-vector mode: vectors_config is {size, distance}
    named_vectors = None
```

**Multi-vector mode handling rules**:

1. **DDL mapping**: Each named vector maps to an independent `knn_vector` field in Lindorm, with the field name matching the vector name (Lindorm search engine supports multiple `knn_vector` fields per index, each independently configurable for dimension, algorithm, and space_type)
2. **Data scan**: scroll returns `point.vector` as dict `{name: [values]}`; split into multiple fields for writing to Lindorm
3. **CSV export**: Each named vector is exported as an independent `knn_vector` column, with column name matching the vector name
4. **Pre-check**: When multi-vector mode is detected, MUST display all vector names with their dimensions and distance metrics, and confirm via AskUserQuestion whether the user wants to migrate all named vectors (user can choose to exclude some)

```
Multi-vector mode (Named Vectors) detected in Qdrant, total 2 vectors:

  Vector Name   Dimension   Distance Metric
  ────────────────────────────────────────
  image         512         Cosine
  text          128         Cosine

Each named vector will be mapped to an independent knn_vector field in Lindorm. After confirmation, DDL with multiple vector fields will be generated.
```

### Distance Metric Mapping

| Qdrant | Lindorm `space_type` |
|--------|----------------------|
| `Cosine` | `cosinesimil` |
| `Euclid` | `l2` |
| `Dot` | `innerproduct` |

## Data Scan (Scroll API)

```bash
# First request (no authentication)
curl -s "http://localhost:6333/collections/<collection_name>/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 1000,
    "with_payload": true,
    "with_vector": true
  }'

# First request (Qdrant Cloud, with API Key authentication)
curl -s -H "api-key: <api_key>" \
  "https://<cluster_id>.qdrant.io:6333/collections/<collection_name>/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 1000,
    "with_payload": true,
    "with_vector": true
  }'

# Pagination (with offset)
curl -s -H "api-key: <api_key>" \
  "http://localhost:6333/collections/<collection_name>/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 1000,
    "offset": <next_offset>,
    "with_payload": true,
    "with_vector": true
  }'
```

Response structure:

```json
{
  "result": {
    "points": [
      {
        "id": 1,
        "vector": [0.1, 0.2, ...],
        "payload": {"title": "...", "price": 99.9}
      },
      {
        "id": 2,
        "vector": [0.3, 0.4, ...],
        "payload": {"title": "...", "price": 59.9}
      }
    ],
    "next_page_offset": 1001
  }
}
```

### Agent Scan Loop Key Points

1. `with_vector: true` must be set; otherwise vector data is not returned
2. `with_payload: true` returns all payload; can also pass a field list to return only specified fields
3. Vectors are not in `payload`; must inject from `point.vector` into doc
4. `id` can be int or str (UUID); offset type must match
5. Multi-vector mode: `vector` is dict `{name: [values]}`; split into multiple fields and inject into doc (e.g. `doc["image"] = point["vector"]["image"]`, `doc["text"] = point["vector"]["text"]`); single-vector mode: `doc["embedding"] = point["vector"]` directly
6. End loop when `next_page_offset` is null
7. `limit` recommended 500~1000

### Incremental Migration (Filter)

Filter by adding a Range condition on a timestamp field in the payload via the `filter` parameter:

```bash
# Numeric timestamp (epoch milliseconds/seconds) — Qdrant Cloud needs -H "api-key: <api_key>"
curl -s "http://localhost:6333/collections/<collection_name>/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 1000,
    "offset": <offset>,
    "with_payload": true,
    "with_vector": true,
    "filter": {
      "must": [{
        "key": "<incremental_field>",
        "range": {"gte": <incremental_since>}
      }]
    }
  }'

# ISO 8601 string (Qdrant datetime type)
curl -s "http://localhost:6333/collections/<collection_name>/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 1000,
    "with_payload": true,
    "with_vector": true,
    "filter": {
      "must": [{
        "key": "<incremental_field>",
        "range": {"gte": "2025-01-01T00:00:00Z"}
      }]
    }
  }'
```

### Incremental Migration Notes

| Item | Description |
|------|-------------|
| `incremental_field` | An existing field in payload. Qdrant has no auto-timestamp; the application must maintain it at write time |
| Field type | Numeric uses `range`; datetime strings also use `range` (Qdrant auto-recognizes) |
| `payload_schema` | Can confirm field existence and inferred type via collection info |
| Relationship with checkpoint | `offset` (Point ID) controls pagination position; `filter` controls data scope; the two are orthogonal |
| No timestamp field | If payload has no time field, incremental migration is impossible; must clearly inform user |

## Checkpoint Resume

Checkpoint cursor is the ID of the last Point (int or str UUID). On resume, pass `offset=cursor`.

> **offset semantics**: Qdrant scroll's `offset` parameter is **exclusive** — when a Point ID is passed, the results start from the **next** Point after that ID, not including the offset itself. Therefore, directly using the last Point's ID as `offset` is correct and won't produce duplicate data.

Qdrant scroll sorts by ID, ensuring complete traversal without duplicates or gaps.

## Rate Limiting

| Item | Description |
|------|-------------|
| Qdrant Cloud | Limited by cluster tier; exceeding returns `429` |
| Self-hosted Qdrant | No default rate limiting; excessive writes cause WAL pressure |
| Migration recommendation | batch_size=1000; mind WAL write rate with concurrent upserts |

## Key Notes

| Item | Description |
|------|-------------|
| Port | REST 6333, gRPC 6334 |
| Vector location | Not in `payload`; must inject from `point.vector` |
| Point ID | Can be int or str (UUID); scroll's offset type must match |
| Multi-vector | `vectors` is a dict (named vectors); each key is a vector name, mapping to independent `knn_vector` fields in Lindorm (see "Multi-vector Mode" section above) |
| `payload_schema` | Qdrant auto-inferred type mapping, may be incomplete |
| `datetime` type | Qdrant payload `datetime` type stores ISO 8601 strings (e.g. `2025-01-01T00:00:00Z`). When mapping to Lindorm `date` type, DDL MUST use multi-format compatible `format`: `"yyyy-MM-dd HH:mm:ss\|\|strict_date_optional_time\|\|epoch_millis"` to ensure ISO 8601 values with timezone are parsed correctly |
| Batch size | `limit` recommended 500~1000 |
| Qdrant Cloud | Requires `api-key` Header |
| Filter | scroll supports `filter` parameter (must/should/must_not), optional |

## Dependencies

All examples in this document use `curl` (no additional dependencies). If using the Python SDK, install:

```
qdrant-client==1.18.0
```

Install: `pip install "qdrant-client==1.18.0"`
