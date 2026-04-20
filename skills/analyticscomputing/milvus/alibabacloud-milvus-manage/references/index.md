# Index Management — Detailed Reference

## Create Index

```python
index_params = client.prepare_index_params()

# Vector index
index_params.add_index(
    field_name="embedding",
    index_type="HNSW",               # See index types table below
    metric_type="COSINE",            # "COSINE", "L2", "IP"
    params={"M": 16, "efConstruction": 256}
)

# Optional: scalar index
index_params.add_index(
    field_name="text",
    index_type=""                    # Auto-select for scalars
)

client.create_index(
    collection_name="my_collection",
    index_params=index_params
)
```

## Common Index Types

| Index Type | For | Key Params | Notes |
|------------|-----|------------|-------|
| `AUTOINDEX` | Dense vectors | Auto-tuned | Recommended for most cases |
| `FLAT` | Dense vectors | None | Brute force, 100% recall |
| `IVF_FLAT` | Dense vectors | `nlist` | Good balance |
| `IVF_SQ8` | Dense vectors | `nlist` | Compressed, less memory |
| `HNSW` | Dense vectors | `M`, `efConstruction` | High recall, more memory |
| `DISKANN` | Dense vectors | None | Disk-based, large datasets |
| `SPARSE_INVERTED_INDEX` | Sparse vectors | `drop_ratio_build` | For sparse vectors |
| `SPARSE_WAND` | Sparse vectors | `drop_ratio_build` | Faster sparse search |

## Metric Types

| Metric | Description | Use With |
|--------|-------------|----------|
| `"COSINE"` | Cosine similarity (larger = more similar) | Dense vectors |
| `"L2"` | Euclidean distance (smaller = more similar) | Dense vectors |
| `"IP"` | Inner product (larger = more similar) | Dense & Sparse vectors |
| `"BM25"` | BM25 relevance scoring | Full-text search (sparse vectors from built-in tokenizer) |

## Other Index Operations

```python
# List indexes
indexes = client.list_indexes(collection_name="my_collection")

# Describe an index
info = client.describe_index(collection_name="my_collection", index_name="my_index")

# Drop an index
client.drop_index(collection_name="my_collection", index_name="my_index")
```

## Guidance

- `AUTOINDEX` is recommended for most use cases.
- An index is required before loading a collection.
- After creating an index, load the collection before searching.
- Sparse vectors only support `"IP"` metric type.
- For full-text search, use `"BM25"` metric type with `SPARSE_INVERTED_INDEX` or `SPARSE_WAND`.
