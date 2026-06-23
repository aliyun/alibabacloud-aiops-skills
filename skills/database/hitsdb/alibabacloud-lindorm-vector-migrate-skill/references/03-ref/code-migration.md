# Application Code Migration Advice

After migration completes, application code needs to switch from the source to Lindorm. Lindorm search engine is Elasticsearch REST API compatible (port 30070) and can be accessed via ES clients like `elasticsearch-py`, but the following differences require code changes.

## Connection Layer Changes

| Source | Original connection | Change to |
|--------|-------------------|-----------|
| Milvus | `pymilvus` / `connections.connect(uri=...)` | `elasticsearch-py` / `Elasticsearch(hosts=["http://<host>:30070"])` |
| Elasticsearch | `elasticsearch-py` / `Elasticsearch(hosts=...)` | Only modify `hosts` and `port` (9200 → 30070) |
| Qdrant | `qdrant-client` / `QdrantClient(url=...)` | `elasticsearch-py` / `Elasticsearch(hosts=["http://<host>:30070"])` |
| Lindorm | `elasticsearch-py` | No changes needed (if port differs, change to 30070) |

## Query Syntax Changes

### Milvus → Lindorm

| Milvus operation | Lindorm equivalent |
|-----------------|-------------------|
| `collection.search(data=[vec], anns_field="vec", param={"metric_type": "COSINE"}, limit=10)` | `es.search(index="<index>", body={"size": 10, "query": {"knn": {"vec": {"vector": vec, "k": 10}}}})` |
| `collection.query(expr="id > 100", output_fields=["*"])` | `es.search(index="<index>", body={"query": {"range": {"id": {"gt": 100}}}})` |
| `collection.insert(data)` | `es.index(index="<index>", body=doc)` or `_bulk` batch write |
| `collection.delete(expr="id in [1,2,3]")` | `es.delete_by_query(index="<index>", body={"query": {"terms": {"id": [1,2,3]}}})` |
| `connections.connect(uri=...)` + `Collection(name)` | `Elasticsearch(hosts=["http://<host>:30070"])` |

### Elasticsearch → Lindorm

| Difference | Description |
|-----------|-------------|
| Port | 9200 → 30070 |
| `dense_vector` field | Named `knn_vector` in Lindorm; KNN query syntax is the same |
| `_source.excludes` | Vector fields were excluded during migration; query results do not contain vector values (does not affect retrieval) |
| PIT API | Lindorm does not support Point-in-Time; use scroll API for deep pagination (`_search?scroll=5m` + `_search/scroll` for pagination) |
| `nested` query | Lindorm supports `nested` type; syntax is compatible |

### Qdrant → Lindorm

| Qdrant operation | Lindorm equivalent |
|-----------------|-------------------|
| `client.search(collection, query_vector=vec, limit=10)` | `es.search(index="<index>", body={"size": 10, "query": {"knn": {"<vector_field>": {"vector": vec, "k": 10}}}})` |
| `client.scroll(collection, limit=100, with_payload=True)` | `es.search(index="<index>", body={"size": 100, "query": {"match_all": {}}})` + scroll API pagination |
| `client.upsert(collection, points=[...])` | `bulk(es, actions)` batch write |
| `client.retrieve(collection, ids=[...])` | `es.mget(index="<index>", body={"ids": [...]})` |
| `client.delete(collection, points_selector=...)` | `es.delete_by_query(index="<index>", body={"query": {"terms": {"_id": [...]}}})` |

## KNN Vector Search Syntax

Standard Lindorm KNN query:

```python
resp = es.search(
    index="<index_name>",
    body={
        "size": 10,
        "query": {
            "knn": {
                "<vector_field>": {
                    "vector": [0.1, 0.2, ...],  # Query vector
                    "k": 10,                      # Return Top-K
                }
            }
        },
        # Optional: exclude vector values from response to save bandwidth
        # "_source": {"excludes": ["<vector_field>"]},
    }
)
hits = resp["hits"]["hits"]
for hit in hits:
    doc_id = hit["_id"]
    score = hit["_score"]
    doc = hit["_source"]
```

Vector + scalar hybrid search (pre-filter):

```python
body = {
    "size": 10,
    "query": {
        "bool": {
            "must": [
                {"knn": {"<vector_field>": {"vector": vec, "k": 10}}}
            ],
            "filter": [
                {"term": {"category": "electronics"}},
                {"range": {"price": {"lte": 100}}}
            ]
        }
    }
}
```

## Migration Checklist

The Agent MUST select the corresponding migration template based on the source type (see source-specific checklists below) and present **concrete code replacement examples** to the user. MUST NOT provide only generic advice (e.g. "replace client with Lindorm").

### Milvus → Lindorm Migration Checklist

| # | Change item | Milvus original code | Lindorm replacement code |
|---|------------|---------------------|-------------------------|
| 1 | Dependency replacement | `from pymilvus import connections, Collection` | `from elasticsearch import Elasticsearch` |
| 2 | Connection initialization | `connections.connect(uri="http://milvus:19530", token="xxx")` | `es = Elasticsearch(["http://<host>:30070"], http_auth=("user", "pass"), request_timeout=30)` |
| 3 | Vector search | `collection.search(data=[vec], anns_field="vec", param={"metric_type":"COSINE"}, limit=10, output_fields=["title"])` | `es.search(index="idx", body={"size":10, "query":{"knn":{"vec":{"vector":vec,"k":10}}}, "_source":{"includes":["title"]}})` |
| 4 | Hybrid search | `collection.search(data=[vec], ..., expr="category=='electronics'")` | `es.search(index="idx", body={"size":10, "query":{"bool":{"must":[{"knn":{"vec":{"vector":vec,"k":10}}}], "filter":[{"term":{"category":"electronics"}}]}}})` |
| 5 | Scalar query | `collection.query(expr="id > 100", output_fields=["*"])` | `es.search(index="idx", body={"query":{"range":{"id":{"gt":100}}}})` |
| 6 | Single insert | `collection.insert([{"id":1, "vec":[...]}])` | `es.index(index="idx", id="1", body={"id":1, "vec":[...]})` |
| 7 | Batch write | `collection.insert(data_list)` | `from elasticsearch.helpers import bulk; bulk(es, actions)` |
| 8 | Delete | `collection.delete(expr="id in [1,2,3]")` | `es.delete_by_query(index="idx", body={"query":{"terms":{"id":[1,2,3]}}})` |
| 9 | Paginated traversal | `query_iterator` | `es.search(scroll="5m", ...)` + `es.scroll(scroll_id=sid)` |
| 10 | Primary key type | INT64 / VARCHAR | `_id` is always string; use `str(pk)` conversion in application code |

### Elasticsearch → Lindorm Migration Checklist

| # | Change item | ES original code | Lindorm replacement code |
|---|------------|-----------------|-------------------------|
| 1 | Connection initialization | `Elasticsearch(["http://es:9200"])` | `Elasticsearch(["http://<host>:30070"], http_auth=("user","pass"))` |
| 2 | Vector field type | `"type": "dense_vector", "dims": 128, "similarity": "cosine"` | `"type": "knn_vector", "dimension": 128, "data_type": "float", "method": {"engine":"lvector","name":"hnsw","space_type":"cosinesimil"}` |
| 3 | KNN search | `es.search(body={"knn":{"field":"vec","query_vector":vec,"k":10}})` (ES 8.x) | `es.search(body={"query":{"knn":{"vec":{"vector":vec,"k":10}}}})` |
| 4 | Deep pagination | `es.open_point_in_time(index="idx")` (PIT) | `es.search(scroll="5m", ...)` + `es.scroll()` (Lindorm does not support PIT) |
| 5 | Port | `9200` | `30070` |
| 6 | Authentication | `http_auth` or `api_key` | `http_auth=(username, password)` (Basic Auth) |

> **Note**: ES source migration is the simplest. If application code already uses `elasticsearch-py 7.x` with compatible query syntax, only host/port/auth and vector field type name need changing.

### Qdrant → Lindorm Migration Checklist

| # | Change item | Qdrant original code | Lindorm replacement code |
|---|------------|---------------------|-------------------------|
| 1 | Dependency replacement | `from qdrant_client import QdrantClient` | `from elasticsearch import Elasticsearch` |
| 2 | Connection initialization | `client = QdrantClient(url="http://qdrant:6333", api_key="xxx")` | `es = Elasticsearch(["http://<host>:30070"], http_auth=("user","pass"))` |
| 3 | Vector search | `client.search(collection_name="col", query_vector=vec, limit=10)` | `es.search(index="col", body={"size":10, "query":{"knn":{"vector":{"vector":vec,"k":10}}}})` |
| 4 | Filtered search | `client.search(..., query_filter=Filter(must=[FieldCondition(key="cat", match=MatchValue(value="electronics"))]))` | `es.search(body={"query":{"bool":{"must":[{"knn":{"vector":{"vector":vec,"k":10}}}],"filter":[{"term":{"cat":"electronics"}}]}}})` |
| 5 | Batch write | `client.upsert(collection_name="col", points=[PointStruct(id=1, vector=vec, payload={...})])` | `bulk(es, [{"_index":"col","_id":"1","_source":{"vector":vec,...}}])` |
| 6 | Query by ID | `client.retrieve(collection_name="col", ids=[1,2,3])` | `es.mget(index="col", body={"ids":["1","2","3"]})` |
| 7 | Delete | `client.delete(collection_name="col", points_selector=PointIdsList(points=[1,2]))` | `es.delete_by_query(index="col", body={"query":{"terms":{"_id":["1","2"]}}})` |
| 8 | Paginated traversal | `client.scroll(collection_name="col", limit=100)` | `es.search(scroll="5m", body={"size":100,"query":{"match_all":{}}})` + `es.scroll()` |
| 9 | Multi-vector | Named Vectors: `client.search(..., using="text_vec")` | Each named vector is an independent `knn_vector` field: `{"knn":{"text_vec":{"vector":vec,"k":10}}}` |

### Lindorm → Lindorm (Cross-Instance) Migration Checklist

| # | Change item | Description |
|---|------------|-------------|
| 1 | Connection address | Change `hosts` to target instance address; keep port `30070` |
| 2 | Authentication | Update `http_auth` with target instance username/password |
| 3 | Index name | If target index name differs, update all `index` parameters |
| 4 | Other | Query syntax and field types are fully compatible; no changes needed |

### Common Changes (applicable to all sources)

1. **Dependency replacement**: `pymilvus` / `qdrant-client` → `elasticsearch==7.17.13` (no replacement needed if ES source already uses it)
2. **Connection initialization**: Change hosts, port (30070)
3. **Authentication**: Switch to HTTP Basic Auth (`http_auth=(username, password)`). Note: `elasticsearch==7.17.13` uses `http_auth` parameter; version 8.x uses `basic_auth`
4. **Write interface**: Use `_bulk` API or `es.index()` uniformly
5. **Vector search**: Change to `knn` query syntax
6. **Scalar queries**: Change to ES `bool` / `term` / `range` queries
7. **Pagination**: Use scroll API (Lindorm does not support Milvus query_iterator or ES PIT)
8. **Primary key type**: Lindorm document `_id` is always a string; application code with integer primary keys needs `str()` conversion

> After migration, it is recommended to verify the write and search pipeline with a small batch of data before switching completely.
>
> For more Lindorm search engine usage, refer to `references/03-ref/official-refs.md`.

## Key Notes

| Item | Description |
|------|-------------|
| Port | Lindorm search engine fixed at 30070 |
| KNN syntax | Use `knn` query, not ES 8.x's `knn` section |
| Deep pagination | PIT not supported; use scroll API instead |
| `_id` type | Always string; integer primary keys need `str()` conversion |
| Vector field storage | `_source.excludes` excludes vector fields; query results do not contain vector values |
