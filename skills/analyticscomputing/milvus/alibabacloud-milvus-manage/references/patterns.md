# Common Patterns

> **Note:** All patterns below use `<USER_URI>` and `<USER_TOKEN>` as connection placeholders. Always ask the user for their actual connection details before writing code. For local development, use Milvus Lite (`uri="./milvus.db"`) only if the user explicitly requests it.

## RAG Pipeline Pattern

```python
from pymilvus import MilvusClient, DataType, model

# 1. Connect (ask user for URI and credentials)
client = MilvusClient(uri="<USER_URI>", token="<USER_TOKEN>")

# 2. Set up embedding model
embedding_fn = model.dense.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# 3. Create collection (dim must match embedding model output)
schema = client.create_schema(auto_id=True, enable_dynamic_field=True)
schema.add_field("id", DataType.INT64, is_primary=True)
schema.add_field("text", DataType.VARCHAR, max_length=2048)
schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=384)  # all-MiniLM-L6-v2 outputs 384-dim
schema.add_field("source", DataType.VARCHAR, max_length=256)

index_params = client.prepare_index_params()
index_params.add_index(field_name="embedding", index_type="AUTOINDEX", metric_type="COSINE")

client.create_collection(collection_name="knowledge_base", schema=schema, index_params=index_params)

# 4. Insert documents — generate real vectors from text chunks
chunks = ["Milvus is a vector database...", "RAG combines retrieval and generation..."]
vectors = embedding_fn.encode_documents(chunks)

client.insert("knowledge_base", data=[
    {"text": chunk, "embedding": vec, "source": "doc1.pdf"}
    for chunk, vec in zip(chunks, vectors)
])

# 5. Retrieve relevant context — use the SAME embedding model
query = "What is a vector database?"
query_vectors = embedding_fn.encode_queries([query])

results = client.search(
    collection_name="knowledge_base",
    data=query_vectors,
    limit=5,
    output_fields=["text", "source"],
    search_params={"metric_type": "COSINE"}
)
```

## Quick Semantic Search Pattern

```python
from pymilvus import MilvusClient, model

# Simplest possible setup (Milvus Lite for local dev)
client = MilvusClient(uri="./search.db")
embedding_fn = model.dense.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# Prepare data — vectors come from embedding model
texts = ["first document", "second document", "third document"]
vectors = embedding_fn.encode_documents(texts)

client.create_collection(collection_name="docs", dimension=384)
client.insert("docs", data=[
    {"id": i, "vector": vec, "text": txt}
    for i, (vec, txt) in enumerate(zip(vectors, texts))
])

# Search — encode query with the same model
query_vectors = embedding_fn.encode_queries(["search query"])
results = client.search("docs", data=query_vectors, limit=10, output_fields=["text"])
```

## Hybrid Search Pattern (Dense + Sparse)

```python
from pymilvus import MilvusClient, DataType, AnnSearchRequest, RRFRanker

# Ask user for connection details
client = MilvusClient(uri="<USER_URI>", token="<USER_TOKEN>")

# Schema with both dense and sparse vectors
schema = client.create_schema(auto_id=True)
schema.add_field("id", DataType.INT64, is_primary=True)
schema.add_field("text", DataType.VARCHAR, max_length=2048)
schema.add_field("dense_embedding", DataType.FLOAT_VECTOR, dim=768)
schema.add_field("sparse_embedding", DataType.SPARSE_FLOAT_VECTOR)

index_params = client.prepare_index_params()
index_params.add_index(field_name="dense_embedding", index_type="AUTOINDEX", metric_type="COSINE")
index_params.add_index(field_name="sparse_embedding", index_type="SPARSE_INVERTED_INDEX", metric_type="IP")

client.create_collection(collection_name="hybrid_col", schema=schema, index_params=index_params)

# Search with both vectors and fuse results
# dense_query_vector and sparse_query_vector come from your respective embedding models
req1 = AnnSearchRequest(data=[dense_query_vector], anns_field="dense_embedding",
                         param={"metric_type": "COSINE"}, limit=20)
req2 = AnnSearchRequest(data=[sparse_query_vector], anns_field="sparse_embedding",
                         param={"metric_type": "IP"}, limit=20)

results = client.hybrid_search(
    collection_name="hybrid_col",
    reqs=[req1, req2],
    ranker=RRFRanker(k=60),
    limit=10,
    output_fields=["text"]
)
```

## Full-Text Search Pattern (BM25)

```python
from pymilvus import MilvusClient, DataType, Function, FunctionType

# Ask user for connection details
client = MilvusClient(uri="<USER_URI>", token="<USER_TOKEN>")

schema = client.create_schema(auto_id=True)
schema.add_field("id", DataType.INT64, is_primary=True)
schema.add_field("title", DataType.VARCHAR, max_length=512)
schema.add_field("body", DataType.VARCHAR, max_length=4096, enable_analyzer=True)
schema.add_field("body_sparse", DataType.SPARSE_FLOAT_VECTOR)

schema.add_function(Function(
    name="body_bm25",
    input_field_names=["body"],
    output_field_names=["body_sparse"],
    function_type=FunctionType.BM25,
))

index_params = client.prepare_index_params()
index_params.add_index(field_name="body_sparse", index_type="AUTOINDEX", metric_type="BM25")

client.create_collection(collection_name="articles", schema=schema, index_params=index_params)

# Insert — only provide text, sparse vector is auto-generated by BM25 function
client.insert("articles", data=[
    {"title": "Intro to ML", "body": "Machine learning is a subset of artificial intelligence..."},
])

# Search with raw text — no embedding model needed, Milvus handles BM25 tokenization
results = client.search(
    collection_name="articles",
    data=["machine learning fundamentals"],
    anns_field="body_sparse",
    limit=10,
    output_fields=["title", "body"]
)
```
