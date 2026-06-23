# Milvus Data Reading Interface

## Dependencies

```
pip install "pymilvus==3.0.0"
```

## Connection

```python
from pymilvus import MilvusClient

# Milvus Lite (local file)
client = MilvusClient(uri="./milvus.db")

# Milvus Server
client = MilvusClient(uri="http://localhost:19530", token="")

# Zilliz Cloud
client = MilvusClient(
    uri="https://<cluster_id>.api.gcp-us-west1.zillizcloud.com:19530",
    token="<api_key>"
)

# Verify Collection exists
if not client.has_collection("<collection_name>"):
    raise Exception(f"Collection '<collection_name>' not found")
```

## List All Collections

When the user does not know which Collection to migrate, first list all Collections on the source for selection:

```python
from pymilvus import MilvusClient

client = MilvusClient(uri="<uri>", token="<token>")
collections = client.list_collections()
# Returns: ["product_vector", "user_embedding", "order_items"]
```

The Agent presents the Collection list to the user via AskUserQuestion for selection. After the user selects one, proceed to the "Get Schema" section to retrieve detailed information about that Collection.

## Get Schema

```python
# Collection metadata
col_info = client.describe_collection(collection_name="<collection_name>")

# Field list
for f in col_info["fields"]:
    field_name = f.get("name", f.get("field_name", ""))
    raw_type = f.get("type", f.get("data_type", "UNKNOWN"))
    # pymilvus returns DataType enum objects; use .name to get the string
    data_type = raw_type.name if hasattr(raw_type, "name") else str(raw_type)
    is_primary = f.get("is_primary", False)
    dim = f.get("params", {}).get("dim") or f.get("dim")
    max_length = f.get("params", {}).get("max_length") or f.get("max_length")
    # data_type values: INT64, VARCHAR, FLOAT_VECTOR, BINARY_VECTOR, BOOL, FLOAT, DOUBLE, JSON, ARRAY ...

# Whether dynamic fields are enabled
enable_dynamic = col_info.get("enable_dynamic_field", False)

# Total row count
stats = client.get_collection_stats(collection_name="<collection_name>")
total_count = int(stats.get("row_count", 0))

# Index info (distance metric)
index_names = client.list_indexes(collection_name="<collection_name>")
if index_names:
    idx_info = client.describe_index(collection_name="<collection_name>", index_name=index_names[0])
    distance_metric = str(idx_info.get("metric_type", ""))  # COSINE, L2, IP
    index_type = idx_info.get("index_type")

# Collection-level TTL detection
_props = col_info.get("properties")
ttl_seconds = int(_props.get("collection.ttl.seconds", 0)) if isinstance(_props, dict) else 0
# ttl_seconds > 0 indicates source has Collection-level TTL configured
# Note: properties may be None, empty dict {}, or empty list []; must handle defensively
```

## Search Iterator (vector nearest-neighbor traversal, not for migration use)

> This interface is for vector similarity search, **not for data migration**. For migration scenarios, use the `query_iterator` below for full data export. Search Iterator requires a query vector and only returns nearest-neighbor results; it cannot traverse all data.

```python
iterator = collection.search_iterator(
    data=[query_vector],
    anns_field="embedding",
    param={"metric_type": "COSINE", "params": {"nprobe": 10}},
    batch_size=1000,
    output_fields=["*"],
)
```

## Dynamic Field Discovery

Milvus dynamic fields (`enable_dynamic_field=True`) are not in the `describe_collection` fields array and need to be discovered by sampling:

> **Sampling requirement**: MUST sample at least 100 records (or all data, whichever is smaller) to discover dynamic fields. Sampling only a few records (e.g. 1~10) may miss low-frequency dynamic fields.

```python
declared_names = {f["name"] for f in col_info["fields"]}

# MUST sample at least 100 records to cover low-frequency dynamic fields
sample_size = min(100, total_count)
sample = client.query(
    collection_name="<collection_name>",
    filter="",
    limit=sample_size,
    output_fields=["*"],  # Must use "*" to return dynamic fields
)

dynamic_fields = {}  # {field_name: inferred_type}
for row in sample:
    for key, value in row.items():
        if key in declared_names or key.startswith("$"):
            continue  # Skip declared fields and internal $meta
        if key not in dynamic_fields and value is not None:
            # Type inference: bool→BOOL, int→INT64, float→DOUBLE, str→VARCHAR, list/dict→JSON
            dynamic_fields[key] = type(value).__name__
```

## Data Scan (query_iterator)

> **Dual API coexistence**: Schema retrieval uses `MilvusClient` (new API), but `query_iterator` **only exists in** the legacy `Collection` API. The migration script must mix both APIs: `MilvusClient` for connection validation and schema retrieval, `Collection` for data scanning. This is a known limitation of pymilvus, not a code error.

```python
from pymilvus import connections, Collection
import warnings

# query_iterator requires the legacy API (Collection object), not MilvusClient directly
conn_alias = "_vt_milvus"
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    connections.connect(alias=conn_alias, uri="<uri>", token="<token>")

collection = Collection("<collection_name>", using=conn_alias)
collection.load()

# Output fields: dynamic field scenarios must use ["*"]; otherwise dynamic fields are silently dropped
if collection.schema.enable_dynamic_field:
    output_fields = ["*"]
else:
    output_fields = [f.name for f in collection.schema.fields]

# Checkpoint resume: scan starting from a specific primary key onward
expr = None
if resume_pk is not None:
    pk_field = collection.schema.primary_field.name
    if isinstance(resume_pk, str):
        expr = f'{pk_field} > "{resume_pk}"'
    else:
        expr = f"{pk_field} > {resume_pk}"

iterator = collection.query_iterator(
    batch_size=1000,    # Records per batch, recommended 500~2000
    expr=expr,
    output_fields=output_fields,
)

try:
    while True:
        result = iterator.next()  # list[dict]
        if not result:
            break
        # Each item in result is a dict containing primary key + output_fields
        # In dynamic field scenarios, dict contains declared fields + dynamic fields
        process_batch(result)
        # Update cursor: result[-1][primary_field]
finally:
    iterator.close()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        connections.disconnect(conn_alias)
```

## Incremental Migration (Expression Filter)

Milvus incremental migration works by appending a timestamp filter condition to the `query_iterator`'s `expr`. Milvus has no built-in `updated_at` field; **the user must have a custom timestamp field in the schema** (e.g. `update_time`, type `INT64` storing epoch milliseconds, or `VARCHAR` storing ISO strings).

```python
# incremental_field: timestamp field name in Milvus (e.g. "update_time")
# incremental_since: start value, type must match field type (INT64 → number, VARCHAR → string)

# Combine checkpoint expr and incremental expr
conditions = []

if resume_pk is not None:
    pk_field = collection.schema.primary_field.name
    if isinstance(resume_pk, str):
        conditions.append(f'{pk_field} > "{resume_pk}"')
    else:
        conditions.append(f"{pk_field} > {resume_pk}")

if incremental_field and incremental_since is not None:
    if isinstance(incremental_since, str):
        conditions.append(f'{incremental_field} >= "{incremental_since}"')
    else:
        conditions.append(f"{incremental_field} >= {incremental_since}")

expr = " and ".join(conditions) if conditions else None

iterator = collection.query_iterator(
    batch_size=1000,
    expr=expr,
    output_fields=output_fields,
)
```

### Incremental Migration Notes

| Item | Description |
|------|-------------|
| `incremental_field` | Must be an existing field in the source collection. Milvus has no auto-timestamp; the application must maintain it at write time |
| Field type | `INT64` storing epoch milliseconds/seconds is most common; `VARCHAR` storing ISO strings also works (string lexicographic order must match time order) |
| expr combination | Checkpoint `pk > cursor` and incremental `field >= since` are joined with `and`; the two are orthogonal |
| No timestamp field | If the Milvus collection has no timestamp field, incremental migration is impossible. Must clearly inform the user and suggest full migration |
| `total_count` | In incremental mode, `get_collection_stats` returns the full row count; progress display should use "N records scanned" instead of percentage |

## Dynamic Fields and Lindorm Compatibility

Lindorm search engine supports ES-compatible **dynamic mapping**:

- When writing a field not declared in the mapping, Lindorm auto-infers the type and updates the mapping
- VARCHAR → `text`, numbers → `float`, date strings → `date`
- **Migration strategy**: Only declare source schema fields in DDL; dynamic fields are not written to the mapping and are auto-inferred by Lindorm at write time

| Source field | Milvus type | Lindorm auto-inferred type |
|-------------|------------|---------------------------|
| id | INT64 (declared) | long |
| vector | FLOAT_VECTOR (declared) | knn_vector(128) |
| title | dynamic | text |
| category | dynamic | text |
| price | dynamic | float |
| updated_at | dynamic | date |

**Export note**: `query_iterator` must use `output_fields=["*"]` to return dynamic fields; an explicit field list silently drops them.

## Rate Limiting

| Item | Description |
|------|-------------|
| Zilliz Cloud | QPS limits per CU tier; exceeding returns `Rate limit` (HTTP 429) |
| Self-hosted Milvus | No default rate limiting; configurable via proxy `maxTaskNum` |
| Migration recommendation | batch_size=1000; mind rate limits with concurrent writes; use exponential backoff retry on 429 |

## Collection-Level TTL Detection

Milvus supports Collection-level TTL, where the entire Collection expires uniformly after a specified number of seconds.

```python
# Read from describe_collection properties (properties may be None/empty dict/empty list)
_props = col_info.get("properties")
ttl_seconds = int(_props.get("collection.ttl.seconds", 0)) if isinstance(_props, dict) else 0
```

| Item | Description |
|------|-------------|
| Configuration | `collection.set_properties({"collection.ttl.seconds": N})` |
| Reading | `describe_collection()` returns `properties` dict |
| Semantics | Entire Collection expires uniformly, not per-row |
| Migration conversion | Convert to Lindorm row-level TTL: `expire_time = int(time.time()) + N`. See `references/02-ops/ttl-config.md` |

> `properties` may be `None`, empty dict `{}`, or empty list `[]` (when no properties are set); handle defensively.

## Key Notes

| Item | Description |
|------|-------------|
| Port | Default gRPC 19530, RESTful 9091 |
| `query_iterator` | Based on primary key ordering, ensures complete traversal without duplicates or gaps |
| Dynamic fields | `output_fields` must use `["*"]`; explicit field list silently drops dynamic fields |
| Checkpoint | Record the last item's primary key value; resume with `expr="{pk} > {cursor}"` |
| Milvus Lite | `uri` is a local file path (e.g. `./milvus.db`), no token needed |
| Batch size | `batch_size` recommended 500~2000; too large causes timeout |
| BINARY_VECTOR | See "Binary Vector (BINARY_VECTOR) Handling" section below |

## Binary Vector (BINARY_VECTOR) Handling

Milvus `BINARY_VECTOR` uses `bytes` type storage, compressing every 8 dimensions into 1 byte. `query_iterator` returns binary vectors as Python `bytes` objects, which need conversion before writing to Lindorm or exporting to CSV.

### Lindorm Compatibility

Lindorm `knn_vector` supports `data_type: "binary"`, dimension must be a multiple of 8. Vector field definition in DDL:

```json
{
  "type": "knn_vector",
  "dimension": 128,
  "data_type": "binary",
  "method": {
    "engine": "lvector",
    "name": "hnsw",
    "space_type": "hamming"
  }
}
```

> `BINARY_VECTOR` only supports `hamming` distance metric. Milvus `HAMMING` / `JACCARD` both map to Lindorm's `hamming`.

### Data Conversion

```python
import json

def binary_vector_to_int_list(bvec, dim):
    """Convert Milvus bytes-type binary vector to int list for Lindorm _bulk write and CSV export.
    bvec: bytes object, length = dim // 8
    dim: original dimension (e.g. 128)
    Returns: list[int], each element is 0~255, length = dim // 8
    """
    return list(bvec)

# During migration write: use int list directly as vector value for Lindorm
doc["embedding"] = binary_vector_to_int_list(row["embedding"], dim=128)

# During CSV export: serialize as JSON array string
csv_val = json.dumps(binary_vector_to_int_list(row["embedding"], dim=128))
# Result e.g.: [255, 0, 128, 64, ...]
```

### CSV Export Header

Binary vector column typed header format: `embedding:knn_vector:128:hamming` (dimension is the original bit dimension, not byte count).
