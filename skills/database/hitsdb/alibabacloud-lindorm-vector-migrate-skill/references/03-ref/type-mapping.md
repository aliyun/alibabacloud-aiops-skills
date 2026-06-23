# Type Mapping and DDL Generation

## Distance Metric Mapping

| Source | Lindorm `space_type` |
|--------|----------------------|
| **Milvus** COSINE | cosinesimil |
| **Milvus** L2 | l2 |
| **Milvus** IP (inner product) | innerproduct |
| **ES** cosine | cosinesimil |
| **ES** dot_product | innerproduct |
| **ES** l2_norm | l2 |
| **Lindorm** cosinesimil | cosinesimil |
| **Lindorm** l2 | l2 |
| **Lindorm** innerproduct | innerproduct |
| **Qdrant** Cosine | cosinesimil |
| **Qdrant** Euclid | l2 |
| **Qdrant** Dot | innerproduct |

Unrecognized distance metrics fall back to `cosinesimil`.

## DDL Generation Rules

The Agent generates a Lindorm PUT index body (ES-compatible mapping JSON) based on the source schema.

### When iterating source fields

1. **Skip** the following fields:
   - `_id` (ES metadata field)
   - Milvus dynamic fields (`is_dynamic=True`) → Lindorm dynamic mapping auto-infers
   - User-excluded fields
2. **Vector fields** (mapped to `knn_vector`): Build complete vector field definition (type, dimension, data_type, method) and add to `_source.excludes`
3. **Scalar fields**: Convert types per mapping table. `date` type:
   - **ES/Lindorm source**: Preserve original `format` (e.g. `strict_date_optional_time`)
   - **CSV/Milvus/Qdrant source**: MUST use multi-format compatible `format`, e.g. `"yyyy-MM-dd HH:mm:ss||strict_date_optional_time||epoch_millis"`, to avoid write failures when actual data format doesn't match a single format
4. **Unknown types**: Fall back to `keyword`

### Vector Field Definition Template

```json
{
  "type": "knn_vector",
  "dimension": 128,
  "data_type": "float",
  "method": {
    "engine": "lvector",
    "name": "hnsw",
    "space_type": "cosinesimil",
    "parameters": {"m": 24, "ef_construction": 500}
  }
}
```

- `dimension`: Obtained from source schema; defaults to 128 if unknown
- `data_type`: `FLOAT_VECTOR` uses `"float"`; `BINARY_VECTOR` uses `"binary"` (binary vector, dimension must be a multiple of 8)
- `method.name`: User-selected index method (hnsw / ivfpq / ivfbq)
- `method.space_type`: Obtained from distance metric mapping table
- `method.parameters`: Optional; HNSW commonly uses `{"m": 24, "ef_construction": 500}`

### Settings Construction

| Setting | Condition | Value |
|---------|-----------|-------|
| `index.knn` | Always | `true` |
| `index.number_of_shards` | User specified shard count | User-specified value (cannot be modified after creation) |
| `index.knn_routing` | User specified routing field | `true` (requires shard count > 1) |
| `index.doc_ttl.field` | TTL enabled (source detection or manual config) | TTL field name (default `expire_time`) |
| `index.doc_ttl.unit` | TTL enabled | `s` or `ms` (default `s`) |

### `_source.excludes`

All vector field names are added to the excludes list to reduce storage overhead. Only added when vector fields exist.

### Complete DDL Structure

```json
{
  "settings": {
    "index": {
      "knn": true,
      "number_of_shards": 3,
      "knn_routing": true,
      "doc_ttl.field": "expire_time",
      "doc_ttl.unit": "s"
    }
  },
  "mappings": {
    "_source": {"excludes": ["embedding"]},
    "properties": {
      "embedding": { "...knn_vector definition..." },
      "expire_time": {"type": "long"},
      "title": {"type": "text"},
      "category": {"type": "keyword"},
      "price": {"type": "float"},
      "updated_at": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss||strict_date_optional_time||epoch_millis"}
    }
  }
}
```

## Vector Index Methods

| Method | Features | Requires offline build | Parameters example |
|--------|----------|----------------------|-------------------|
| hnsw | Online indexing, queryable immediately after write | No | `{"m": 24, "ef_construction": 500}` |
| ivfpq | PQ compression, for over one million records | Yes | `{"nlist": 256, "m": 96}` |
| ivfbq | BQ compression, high compression ratio | Yes | `{"nlist": 256}` |

> IVFPQ requires write row count > `nlist`; server minimum effective nlist=256.

## Cross-Source Comparison

### Authentication Method Comparison

| Database | Authentication | SDK | Default port |
|----------|---------------|-----|-------------|
| Milvus/Zilliz | Token (user:pass or API Key) | pymilvus==3.0.0 | 19530 (gRPC) |
| Elasticsearch | Basic Auth / API Key / Bearer | elasticsearch==7.17.13 | 9200 |
| Qdrant | API Key (Header) | qdrant-client==1.18.0 | 6333 (REST) / 6334 (gRPC) |
| Lindorm (search engine) | HTTP Basic Auth | elasticsearch==7.17.13 | 30070 |
| Lindorm (wide table SQL) | MySQL username/password | pymysql | 33060 |

### Pagination/Traversal Mechanism Comparison

| Database | Recommended export method | Checkpoint resume method | Recommended batch size |
|----------|--------------------------|-------------------------|----------------------|
| Milvus/Zilliz | query_iterator | Record last primary key value | 500~2000 |
| Elasticsearch | search_after + PIT (default); fall back to Scroll API when elasticsearch-py 7.x connects to ES 8.x | PIT: record last sort values; Scroll: record last `_id` | 1000~5000 |
| Qdrant | scroll / scroll_batches | Record last Point ID | 500~1000 |
| Lindorm | scroll API (PIT not supported) | Record last `_id` | 1000~5000 |

### Complete Field Type Mapping Table (each source → Lindorm)

| Source type | | | Lindorm Search Engine | Lindorm SQL |
|------------|----------|----------|----------------------|-------------|
| Milvus | ES / Lindorm | Qdrant Payload / CSV header | | |
| INT64 | long | integer / long | long | BIGINT |
| INT32 | integer | integer | integer | INT |
| INT16 / INT8 | short / byte | — | short / byte | — |
| VARCHAR | keyword / text | keyword / text | keyword / text | VARCHAR |
| FLOAT_VECTOR | dense_vector | knn_vector (CSV) | knn_vector | VARCHAR |
| BINARY_VECTOR | dense_vector (byte) | — | knn_vector (binary) | — |
| BOOL | boolean | bool / boolean | boolean | BOOLEAN |
| FLOAT | float | float | float | FLOAT |
| DOUBLE | double | double | double | DOUBLE |
| JSON | object | object / keyword (CSV) | object | JSON |
| ARRAY | keyword | keyword (CSV) | keyword | — |
| — | date | date | date | TIMESTAMP |
| — | — | datetime | date | TIMESTAMP |
| — | nested | — | (not supported, skip) | — |

> CSV source types are declared by the user in the header (`column_name:type`), with identity mapping to Lindorm search engine types.
> Qdrant vector fields are not in payload; DDL needs manual addition. In multi-vector mode, each named vector maps to an independent `knn_vector` field.

## Special Handling

| Scenario | Handling |
|----------|----------|
| Milvus dynamic fields | Not declared in DDL; Lindorm dynamic mapping auto-infers types |
| ES `_id` | Not written to mapping properties; used as document `_id` during writes |
| Qdrant vectors | Not in payload; DDL needs manual vector field addition |
| Excluded fields | Not declared in DDL; filtered from `_source` during writes |
| Unknown types | Fall back to `keyword` (scalar) or error |
| date fields | ES/Lindorm source: preserve original `format`; CSV/Milvus/Qdrant source: use multi-format compatible `"yyyy-MM-dd HH:mm:ss\|\|strict_date_optional_time\|\|epoch_millis"` |
| Milvus ARRAY | Lindorm search engine does not support `keyword[]` array type; during migration, serialize arrays to JSON strings (e.g. `["a","b"]` → `'["a","b"]'`, using `json.dumps()`). Do not use comma concatenation (e.g. `"a,b"`) to avoid data loss when elements contain commas |
| Qdrant multi-vector | In Qdrant Named Vectors mode, each named vector maps to an independent `knn_vector` field in Lindorm with the vector name as field name. DDL needs to generate an independent vector field definition for each named vector (dimension, data_type, method each configured independently) |
