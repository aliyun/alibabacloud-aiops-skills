# Collection Management — Detailed Reference

## Supported Data Types

### Scalar Types

| DataType | Notes |
|----------|-------|
| `DataType.BOOL` | Boolean |
| `DataType.INT8` / `INT16` / `INT32` / `INT64` | Integers |
| `DataType.FLOAT` / `DOUBLE` | Floating point |
| `DataType.VARCHAR` | String (requires `max_length`) |
| `DataType.JSON` | JSON object |
| `DataType.ARRAY` | Array (requires `element_type`, `max_capacity`) |

### Vector Types

| DataType | Notes |
|----------|-------|
| `DataType.FLOAT_VECTOR` | Float32 vector (requires `dim`) |
| `DataType.FLOAT16_VECTOR` | Float16 vector (requires `dim`) |
| `DataType.BFLOAT16_VECTOR` | BFloat16 vector (requires `dim`) |
| `DataType.BINARY_VECTOR` | Binary vector (requires `dim`) |
| `DataType.SPARSE_FLOAT_VECTOR` | Sparse vector (no `dim` needed) |
| `DataType.INT8_VECTOR` | Int8 vector (requires `dim`) |

## add_field Parameters

```python
schema.add_field(
    field_name="my_field",
    datatype=DataType.VARCHAR,
    is_primary=False,
    auto_id=False,
    max_length=256,          # Required for VARCHAR
    dim=768,                 # Required for vector types (except sparse)
    element_type=DataType.INT64,  # Required for ARRAY
    max_capacity=100,        # Required for ARRAY
    nullable=False,
    default_value=None,
    is_partition_key=False,
    description=""
)
```

## All Collection Operations

```python
# List all collections
collections = client.list_collections()

# Describe a collection
info = client.describe_collection(collection_name="my_collection")

# Check if collection exists
exists = client.has_collection(collection_name="my_collection")

# Rename a collection
client.rename_collection(old_name="old_name", new_name="new_name")

# Drop a collection
client.drop_collection(collection_name="my_collection")

# Truncate a collection (delete all data, keep schema and index)
client.truncate_collection(collection_name="my_collection")

# Load collection into memory (required before search/query)
client.load_collection(collection_name="my_collection")

# Release collection from memory
client.release_collection(collection_name="my_collection")

# Get load state
state = client.get_load_state(collection_name="my_collection")

# Get collection statistics
stats = client.get_collection_stats(collection_name="my_collection")
```

## Function (Embedding Function)

> **Requires Milvus ≥ 2.6.** Embedding functions are not available on earlier versions.

Functions allow Milvus to automatically generate vector embeddings from scalar fields during insert and search, eliminating the need to manually compute vectors.

### Imports

```python
from pymilvus import MilvusClient, DataType, Function, FunctionType
```

### Function Parameters

```python
Function(
    name="my_embedding_func",           # Unique identifier for this function
    function_type=FunctionType.TEXTEMBEDDING,  # Function type
    input_field_names=["text_field"],    # Scalar field(s) to embed
    output_field_names=["vector_field"], # Vector field(s) to store embeddings
    params={
        "provider": "aliyun_milvus",    # Embedding model provider
        "model_name": "text-embedding-v4"  # Model name
    }
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | String | Unique identifier for this embedding function |
| `function_type` | FunctionType | Type of function, e.g. `FunctionType.TEXTEMBEDDING` |
| `input_field_names` | List[str] | Scalar field names to use as input (e.g. VARCHAR fields) |
| `output_field_names` | List[str] | Vector field names to store generated embeddings |
| `params` | Dict | Provider-specific parameters (provider, model_name, dim, etc.) |

### Adding Function to Schema

```python
schema.add_function(my_function)
```

### Complete Example: Text Embedding + Multimodal Embedding

```python
from pymilvus import MilvusClient, DataType, Function, FunctionType

PYMILVUS_GRPC_OPTIONS = {
    "grpc.primary_user_agent": "AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage"
}

client = MilvusClient(
    uri="http://<endpoint>:19530",
    token="root:password",
    grpc_options=PYMILVUS_GRPC_OPTIONS,
)

schema = client.create_schema()

# Define fields
schema.add_field("id", DataType.INT64, is_primary=True, auto_id=False)
schema.add_field("document", DataType.VARCHAR, max_length=9000)
schema.add_field("mm_value", DataType.VARCHAR, max_length=9000, nullable=True)
schema.add_field("dense", DataType.FLOAT_VECTOR, dim=1024)
schema.add_field("dense_mm", DataType.FLOAT_VECTOR, dim=1024)

# Text embedding function
text_embedding_function = Function(
    name="text_embedding_func",
    function_type=FunctionType.TEXTEMBEDDING,
    input_field_names=["document"],
    output_field_names=["dense"],
    params={
        "provider": "aliyun_milvus",
        "model_name": "text-embedding-v4"
    }
)

# Multimodal embedding function
mm_embedding_function = Function(
    name="mm_embedding_func",
    function_type=FunctionType.TEXTEMBEDDING,
    input_field_names=["document"],
    output_field_names=["dense_mm"],
    params={
        "provider": "aliyun_milvus",
        "model_name": "qwen3-vl-embedding",
        "dim": "1024"
    }
)

# Add functions to schema
schema.add_function(text_embedding_function)
schema.add_function(mm_embedding_function)

# Create indexes
index_params = client.prepare_index_params()
index_params.add_index(field_name="dense", index_type="AUTOINDEX", metric_type="COSINE")
index_params.add_index(field_name="dense_mm", index_type="AUTOINDEX", metric_type="COSINE")

# Create collection
client.create_collection(
    collection_name="my_collection",
    schema=schema,
    index_params=index_params
)
```

### Search with Function (Text/URL as Input)

When a collection has embedding functions, search `data` accepts raw text or URLs instead of vectors:

```python
# Text search via text embedding function
results = client.search(
    collection_name="my_collection",
    data=["How does Milvus handle semantic search?"],  # Raw text, not vector
    anns_field="dense",
    limit=5,
    output_fields=["document", "mm_value"],
)

# Image URL search via multimodal embedding function
results = client.search(
    collection_name="my_collection",
    data=["https://example.com/image.jpeg"],  # Image URL, not vector
    anns_field="dense_mm",
    limit=5,
    output_fields=["document", "mm_value"],
)
```

### Insert with Function

When inserting data, only provide the scalar input fields — vector fields are auto-generated by the function:

```python
client.insert("my_collection", [
    {"id": 1, "document": "A description of an image.", "mm_value": "https://example.com/image.jpeg"},
    {"id": 2, "document": "Vector embeddings convert text into numeric data.", "mm_value": "https://example.com/another.jpeg"},
    {"id": 3, "document": "Semantic search helps users find relevant info."},  # mm_value is nullable
])
```

### Supported Providers and Models

| Provider | Model Name           | Description |
|----------|----------------------|-------------|
| `aliyun_milvus` | `text-embedding-v4`  | Alibaba Cloud text embedding |
| `aliyun_milvus` | `text-embedding-v3`  | Alibaba Cloud text embedding |
| `aliyun_milvus` | `text-embedding-v2`  | Alibaba Cloud text embedding |
| `aliyun_milvus` | `qwen3-vl-embedding` | Alibaba Cloud multimodal (vision-language) embedding, requires `dim` param |

### Key Notes

- The `input_field_names` field must reference an existing scalar field (typically VARCHAR) in the schema.
- The `output_field_names` field must reference an existing vector field in the schema with matching `dim`.
- For multimodal models like `qwen3-vl-embedding`, the `dim` parameter in `params` is optional — if omitted, it defaults to the `dim` of the corresponding vector field in `output_field_names`.
- Multiple functions can be added to a single schema, each mapping different input/output field pairs.
- When searching, set `anns_field` to the specific vector field corresponding to the desired embedding function.

## Guidance

- Quick create is best for prototyping; use custom schema for production.
- A collection must be **loaded** before search or query operations.
- Before dropping a collection, confirm with the user — this deletes all data.
- Use `enable_dynamic_field=True` to allow inserting fields not defined in the schema.
- Use `truncate_collection` to clear all data while preserving the collection structure.
