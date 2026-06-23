# Elasticsearch Data Reading Interface

## Connection and Verification

```bash
# No authentication
curl -s http://localhost:9200/

# With Basic Auth
curl -s -u elastic:password https://my-cluster.es.io:9243/
```

Extract version number from response; PIT API requires `>= 7.10`:

```json
{
  "version": {
    "number": "8.15.0"
  }
}
```

### ES Version and Pagination Method Auto-Detection

The Agent MUST auto-detect the ES version and elasticsearch-py version during the pre-check phase to decide whether to use PIT or Scroll:

```python
import elasticsearch

# 1. Get ES server version
es_info = es_client.info()
es_version = es_info["version"]["number"]  # e.g. "8.15.0"
es_major = int(es_version.split(".")[0])    # e.g. 8

# 2. Get elasticsearch-py client version
py_es_version = elasticsearch.__version__   # e.g. (7, 17, 13)
py_es_major = py_es_version[0]              # e.g. 7

# 3. Decision logic
if es_major < 7 or (es_major == 7 and int(es_version.split(".")[1]) < 10):
    use_scroll = True   # ES < 7.10 does not support PIT
    reason = "ES version < 7.10, PIT API not supported"
elif es_major >= 8 and py_es_major == 7:
    use_scroll = True   # elasticsearch-py 7.x connecting to ES 8.x has PIT cursor bug
    reason = "elasticsearch-py 7.x connecting to ES 8.x has PIT cursor bug"
else:
    use_scroll = False  # Use PIT + search_after
    reason = "Using PIT + search_after (recommended)"
```

> The Agent MUST display the detection result in pre-check output: `"ES version: {es_version}, elasticsearch-py version: {py_es_version}, pagination method: {reason}"`

## Get Schema (Index Mapping)

```bash
curl -s -u elastic:password "http://localhost:9200/<index_name>/_mapping"
```

Response structure:

```json
{
  "<index_name>": {
    "mappings": {
      "properties": {
        "title": { "type": "text", "analyzer": "ik_max_word" },
        "category": { "type": "keyword" },
        "price": { "type": "float" },
        "embedding": {
          "type": "dense_vector",
          "dims": 128,
          "similarity": "cosine"
        },
        "updated_at": { "type": "date", "format": "strict_date_optional_time" },
        "metadata": { "type": "object", "properties": { ... } },
        "tags": { "type": "nested", "properties": { ... } }
      }
    }
  }
}
```

### Fields the Agent should focus on when extracting

| Field type | Handling |
|------------|----------|
| `dense_vector` | Vector field. Extract `dims` (dimension) and `similarity` (distance metric: `cosine` / `dot_product` / `l2_norm`) |
| `nested` | **Not supported for migration**; must inform user and skip, record to `skipped_fields` |
| `date` | Preserve `format`, pass to DDL generation |
| `object` | Recursively traverse `properties` (see example below) |
| Other | `keyword` / `text` / `long` / `integer` / `float` / `double` / `boolean` etc. map directly |

### `object` Type Recursive Traversal

ES `object` type sub-fields maintain their original nested structure in Lindorm; DDL recursively generates `properties`. During writes, the nested JSON object in `_source` is passed as-is; Lindorm handles it automatically.

```python
def flatten_mapping(properties, prefix="", skipped=None):
    """Recursively traverse ES mapping properties, generating Lindorm-compatible mapping.
    object types preserve nested structure, nested types are skipped.
    """
    if skipped is None:
        skipped = []
    result = {}
    for field_name, field_def in properties.items():
        full_name = f"{prefix}{field_name}"
        field_type = field_def.get("type")

        if field_type == "nested":
            skipped.append(full_name)
            continue

        if field_type == "object" or (field_type is None and "properties" in field_def):
            # object type: recursively process sub-fields, preserve nested structure
            sub_props = flatten_mapping(field_def["properties"], skipped=skipped)
            if sub_props:
                result[field_name] = {"properties": sub_props}
            continue

        # Scalar/vector fields: convert according to type mapping table
        result[field_name] = convert_field_type(field_def)
    return result
```

**Example**:

Source mapping:
```json
{
  "metadata": {
    "type": "object",
    "properties": {
      "author": {"type": "keyword"},
      "stats": {
        "properties": {
          "views": {"type": "long"},
          "likes": {"type": "long"}
        }
      }
    }
  }
}
```

Generated Lindorm DDL properties:
```json
{
  "metadata": {
    "properties": {
      "author": {"type": "keyword"},
      "stats": {
        "properties": {
          "views": {"type": "long"},
          "likes": {"type": "long"}
        }
      }
    }
  }
}
```

When writing, the `metadata` field in `_source` is passed as-is (e.g. `{"metadata": {"author": "Alice", "stats": {"views": 100, "likes": 5}}}`); Lindorm automatically maps to sub-fields.

### Document Count

```bash
curl -s -u elastic:password "http://localhost:9200/<index_name>/_count" \
  -H "Content-Type: application/json" \
  -d '{"query": {"match_all": {}}}'
```

Response: `{"count": 100000, ...}`

## List All Indices

When the user does not know which index to migrate, first list all source indices for selection:

```bash
curl -s -u elastic:password "http://localhost:9200/_cat/indices?format=json&h=index,docs.count,store.size,health,status"
```

Response:

```json
[
  {"index": "test_es_all_fields", "docs.count": "120000", "store.size": "45.2mb", "health": "green", "status": "open"},
  {"index": "test_es_ecommerce", "docs.count": "120000", "store.size": "38.7mb", "health": "green", "status": "open"},
  {"index": "test_es_object", "docs.count": "120000", "store.size": "52.1mb", "health": "green", "status": "open"},
  {"index": ".kibana_1", "docs.count": "50", "store.size": "1.2mb", "health": "green", "status": "open"}
]
```

The Agent filters out system indices starting with `.` (e.g. `.kibana`) and presents the remaining index list to the user via AskUserQuestion for selection.

## Data Scan (PIT + search_after)

> Requires ES >= 7.10. Recommended deep pagination method, more friendly than the scroll API.

> **Version compatibility warning**: When using `elasticsearch-py==7.17.13` with **ES 8.x**, PIT has a known bug — the `pit_id` format changed in ES 8.x responses, and the 7.x client cannot parse it correctly, causing cursor deadlock (e.g. stuck at `[999]`), repeated writes of the same batch, and migrated count continuously increasing beyond 100%. **When this version combination is detected, MUST switch to Scroll API** (see "Scroll API Fallback" below). Other version combinations (e.g. elasticsearch-py 8.x with ES 8.x, or any version with ES 7.x) continue using PIT + search_after.

### Step 1: Create Point In Time

```bash
curl -s -u elastic:password -X POST \
  "http://localhost:9200/<index_name>/_pit?keep_alive=5m"
```

Response: `{"id": "<pit_id>"}`

### Step 2: Batch Query

```bash
# First query (no search_after)
curl -s -u elastic:password "http://localhost:9200/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "size": 1000,
    "pit": {"id": "<pit_id>", "keep_alive": "5m"},
    "sort": [{"_shard_doc": "asc"}],
    "query": {"match_all": {}},
    "track_total_hits": false
  }'

# Subsequent queries (with search_after)
curl -s -u elastic:password "http://localhost:9200/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "size": 1000,
    "pit": {"id": "<pit_id>", "keep_alive": "5m"},
    "sort": [{"_shard_doc": "asc"}],
    "query": {"match_all": {}},
    "track_total_hits": false,
    "search_after": [<sort value from last item of previous batch>]
  }'
```

Response structure:

```json
{
  "pit_id": "<possibly updated pit_id>",
  "hits": {
    "hits": [
      {
        "_id": "doc_001",
        "_source": {"title": "...", "price": 99.9, "embedding": [0.1, 0.2, ...]},
        "sort": [1718000000000]
      }
    ]
  }
}
```

### Agent Scan Loop Key Points

1. `pit_id` may be updated each time; take the latest from the response
2. `_id` is metadata, not in `_source`; must inject from `hit["_id"]` into doc
3. `sort` value is used for checkpoint resume, record as cursor
4. End loop when `hits` is empty
5. `size` recommended 1000~5000

### Step 3: Close PIT

```bash
curl -s -u elastic:password -X DELETE "http://localhost:9200/_pit" \
  -H "Content-Type: application/json" \
  -d '{"id": "<pit_id>"}'
```

> PIT automatically expires after 5 minutes even without closing, but close promptly to release memory.

### Scroll API Fallback (ES < 7.10 or elasticsearch-py 7.x with ES 8.x)

Applicable scenarios:
- ES version < 7.10 (PIT not supported)
- **elasticsearch-py==7.17.13 with ES 8.x** (PIT cursor deadloop bug)

> **ES 8.x Scroll sort key limitation**: ES 8.x disables `_id` field fielddata access by default (`indices.id_field_data.enabled=false`). Using `sort: [{"_id": "asc"}]` directly returns 400 `Fielddata access on the _id field is disallowed`. Two solutions:
>
> 1. **Recommended**: Choose a **unique and ordered keyword field** as the sort key (e.g. business primary key `id`, `article_id`, etc.). The Agent retrieves the field list via `GET /<index>/_mapping` during pre-checks, preferring fields with `type: keyword` and unique values. If no unique keyword field exists, report error telling the user to manually specify one or use solution 2.
> 2. Temporarily enable source setting: `PUT /<index>/_settings {"index.id_field_data.enabled": true}` (requires source write permissions and impacts source performance)
>
> Examples below use `<sort_field>` as a placeholder for the sort key. In script implementation, select an appropriate field based on `type: keyword` field value ranges (e.g. `title`, `id`).
>
> Checkpoint cursor type changes accordingly: cursor is the sort field value from the last document (string). On resume, add `<sort_field> > cursor` filter condition to the first query.

```bash
# First query (<sort_field> replaced with the selected unique keyword field name, e.g. title, id)
curl -s -u elastic:password "http://localhost:9200/<index_name>/_search?scroll=5m" \
  -H "Content-Type: application/json" \
  -d '{"size": 1000, "query": {"match_all": {}}, "sort": [{"<sort_field>": "asc"}]}'

# Pagination
curl -s -u elastic:password "http://localhost:9200/_search/scroll" \
  -H "Content-Type: application/json" \
  -d '{"scroll": "5m", "scroll_id": "<scroll_id>"}'

# Close
curl -s -u elastic:password -X DELETE "http://localhost:9200/_search/scroll" \
  -H "Content-Type: application/json" \
  -d '{"scroll_id": "<scroll_id>"}'
```

**Scroll API scan loop key points**:

1. Sort by `<sort_field>` (cannot use `_id` on ES 8.x), ensuring ordered traversal
2. `_id` is metadata, not in `_source`; must inject from `hit["_id"]` into doc
3. Checkpoint resume: cursor is the `<sort_field>` value of the last document (string). On resume, add `<sort_field> > cursor` filter condition to the first query; subsequent scroll pages automatically return data after the cursor
4. ES 7.x can still use `_id` as the sort key (compatibility mode); cursor remains the `_id` string
5. End loop when `hits` is empty
6. Scroll context auto-expires after 5 minutes; close promptly when done
7. `size` recommended 1000~5000

| Comparison | search_after + PIT | Scroll API |
|-----------|-------------------|------------|
| Memory friendly | High | Holds old segments |
| Checkpoint resume | Record last sort values | Record last sort key value (ES 8.x cannot use `_id`, need `<sort_field>`) |
| Parallel support | PIT supports slicing | Requires manual Sliced Scroll |
| Official recommendation | Recommended | No longer recommended for deep pagination |
| ES 8.x compatibility | Requires elasticsearch-py 8.x; ES-py 7.x with ES 8.x has cursor bug | ES 7.x with any py version; ES 8.x needs unique keyword field as sort key |

## Incremental Migration (Range Filter)

Incremental migration modifies the query's `query` clause, replacing `match_all` with a `range` filter on a timestamp/date field. Pagination and checkpoint resume mechanisms are identical to full migration.

**PIT + search_after method**:

```bash
curl -s -u elastic:password "http://localhost:9200/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "size": 1000,
    "pit": {"id": "<pit_id>", "keep_alive": "5m"},
    "sort": [{"_shard_doc": "asc"}],
    "query": {
      "range": {"<incremental_field>": {"gte": "<incremental_since>"}}
    },
    "track_total_hits": false
  }'
```

**Scroll API method** (fallback scenario):

```bash
# <sort_field> replaced with the selected unique keyword field name (cannot use _id on ES 8.x)
curl -s -u elastic:password "http://localhost:9200/<index_name>/_search?scroll=5m" \
  -H "Content-Type: application/json" \
  -d '{
    "size": 1000,
    "query": {
      "range": {"<incremental_field>": {"gte": "<incremental_since>"}}
    },
    "sort": [{"<sort_field>": "asc"}]
  }'
```

- `incremental_field`: Source date/timestamp field name (e.g. `updated_at`, `created_at`)
- `incremental_since`: Start value, ISO 8601 string or epoch milliseconds (matching field format)
- When both are `None`, degrades to full migration (`match_all`)

### Incremental Migration Notes

| Item | Description |
|------|-------------|
| `incremental_field` | Must be an existing field on the source, typically `date` type |
| `incremental_since` | Value format must match the field's storage format |
| `gte` vs `gt` | Use `gte` (inclusive); PIT uses `search_after` to avoid duplicates; Scroll uses `<sort_field> > cursor` filter (cannot use `_id` on ES 8.x) |
| `total_count` | In incremental mode, `_count` returns the filtered count, not full count |
| Relationship with checkpoint | cursor controls pagination position, range filter controls data scope; the two are orthogonal |
| ES has no TTL field | If source documents have no update timestamp field, incremental migration is impossible; must inform user |

## Checkpoint Resume

Checkpoint cursor type depends on the pagination method and ES version:
- **PIT + search_after**: cursor is the `sort` value of the last item in the last batch (list). On resume, pass `search_after=cursor`
- **Scroll API (ES 7.x)**: cursor is the `_id` string of the last item. On resume, add `_id > cursor` filter to the first query
- **Scroll API (ES 8.x)**: cursor is the `<sort_field>` value of the last item (string). On resume, add `<sort_field> > cursor` filter to the first query

## ILM Policy Detection (TTL)

ES manages index lifecycle through ILM (Index Lifecycle Management). During migration pre-checks, detect whether the index is associated with an ILM policy.

```bash
# 1. Read index settings, check if associated with ILM policy
curl -s -u elastic:password "http://localhost:9200/<index_name>/_settings"
```

Extract `index.lifecycle.name` from response:

```json
{
  "<index_name>": {
    "settings": {
      "index": {
        "lifecycle": {
          "name": "my_ilm_policy"
        }
      }
    }
  }
}
```

```bash
# 2. Read ILM policy details, extract delete phase min_age
curl -s -u elastic:password "http://localhost:9200/_ilm/policy/<policy_name>"
```

Extract delete phase `min_age` from response:

```json
{
  "<policy_name>": {
    "policy": {
      "phases": {
        "delete": {
          "min_age": "30d",
          "actions": {
            "delete": {}
          }
        }
      }
    }
  }
}
```

| Field | Description |
|-------|-------------|
| `index.lifecycle.name` | ILM policy name; absence indicates the index is not associated with ILM |
| `phases.delete.min_age` | Minimum age before deletion (e.g. `30d`, `7d`, `1h`) |
| No delete phase | Policy does not include a delete action; no TTL migration needed |

### min_age Time Unit Parsing

| Suffix | Meaning | Conversion |
|--------|---------|------------|
| `d` | Days | × 86400 |
| `h` | Hours | × 3600 |
| `m` | Minutes | × 60 |
| `s` | Seconds | × 1 |

> After detecting ILM delete phase, convert to Lindorm row-level TTL: `expire_time = document_timestamp + min_age_seconds`. See `references/02-ops/ttl-config.md`.

## Rate Limiting

| Item | Description |
|------|-------------|
| Write throttling | Returns `429 Too Many Requests` when write queue is full |
| Scroll limit | Maximum 500 concurrent scroll contexts |
| PIT limit | keep_alive consumes memory; recommended 5m, close promptly |
| Migration recommendation | Use `search_after + PIT`, bulk write size=1000~5000 |

## Key Notes

| Item | Description |
|------|-------------|
| `_id` | ES metadata field, not in `_source`; must inject from `hit["_id"]` into doc |
| `_sort` | Internal sort field for checkpoint resume; do not write to target |
| PIT keep_alive | Recommended 5m; too long consumes memory |
| `track_total_hits: false` | Performance optimization; does not count total hits (PIT mode only) |
| `nested` fields | Recommend skipping during migration |
| PIT cursor | `sort` value is a list (e.g. `[1718000000000, "doc_id_123"]`); use directly as `search_after` checkpoint |
| Scroll cursor | ES 7.x: `_id` string, resume by adding `_id > cursor` filter. ES 8.x: `<sort_field>` value (cannot use `_id`), resume by adding `<sort_field> > cursor` filter |
| Batch size | `size` recommended 1000~5000 |
| Scroll API | Prefer PIT + search_after for deep pagination; MUST fall back to Scroll API when elasticsearch-py 7.x connects to ES 8.x, and cannot use `_id` as sort key on ES 8.x — must use a unique keyword field |
