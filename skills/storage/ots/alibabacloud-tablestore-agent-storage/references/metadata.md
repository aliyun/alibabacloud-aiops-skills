# Metadata Reference

This document covers all metadata-related features in the `tablestore-agent-storage` SDK:
- **MetadataField / MetadataFieldType**: Define metadata fields when creating a knowledge base
- **EmbeddingConfiguration**: Custom Embedding model configuration
- **MetadataFilter**: Filter documents by metadata fields during retrieval

---

## 1. Metadata Field Definition (When Creating a Knowledge Base)

### Supported MetadataFieldType Types

| Type | Description |
|------|-------------|
| `string` | String |
| `long` | Integer |
| `double` | Floating point |
| `boolean` | Boolean |
| `date` | Date (format: `YYYY-MM-DD HH:mm:ss`) |
| `string_list` | String list |
| `long_list` | Integer list |
| `double_list` | Floating point list |
| `boolean_list` | Boolean list |
| `date_list` | Date list |

### Define Metadata Fields When Creating a Knowledge Base

**Dict style:**
```python
client.create_knowledge_base({
    "knowledgeBaseName": "my_kb",
    "description": "Knowledge base with subspace support",
    "subspace": True,
    "tags": ["production", "docs"],
    "metadata": [
        {"name": "author", "type": "string"},
        {"name": "created_date", "type": "date"},
        {"name": "version", "type": "long"},
        {"name": "score", "type": "double"},
        {"name": "is_public", "type": "boolean"},
        {"name": "categories", "type": "string_list"}
    ]
})
```

**Model style (recommended, with type hints):**
```python
from tablestore_agent_storage import (
    CreateKnowledgeBaseRequest, MetadataField, MetadataFieldType,
    EmbeddingConfiguration
)

request = CreateKnowledgeBaseRequest(
    knowledge_base_name="my_kb",
    description="My knowledge base",
    subspace=True,
    tags=["production"],
    metadata=[
        MetadataField(name="author", type=MetadataFieldType.STRING),
        MetadataField(name="created_date", type=MetadataFieldType.DATE),
        MetadataField(name="version", type=MetadataFieldType.LONG),
        MetadataField(name="score", type=MetadataFieldType.DOUBLE),
        MetadataField(name="is_public", type=MetadataFieldType.BOOLEAN),
        MetadataField(name="categories", type=MetadataFieldType.STRING_LIST),
    ]
)
client.create_knowledge_base(request)
```

### EmbeddingConfiguration (Custom Embedding Model)

You can specify a custom Embedding model when creating a knowledge base. If not configured, the default model is used:

```python
from tablestore_agent_storage import EmbeddingConfiguration, CreateKnowledgeBaseRequest

embedding_config = EmbeddingConfiguration(
    provider="openai",                              # Model provider
    url="https://api.openai.com/v1/embeddings",     # Embedding API URL
    api_key="your-api-key",                         # API Key
    model="text-embedding-3-small",                 # Model name
    dimension=1536                                  # Vector dimension
)

request = CreateKnowledgeBaseRequest(
    knowledge_base_name="my_kb",
    embedding_configuration=embedding_config
)
client.create_knowledge_base(request)
```

### Attach Metadata When Uploading Documents

```python
# upload_documents (local files)
client.upload_documents({
    "knowledgeBaseName": "my_kb",
    "documents": [
        {"filePath": "/path/to/report.pdf", "metadata": {"author": "aliyun", "version": 2}}
    ]
})

# add_documents (OSS path)
client.add_documents({
    "knowledgeBaseName": "my_kb",
    "documents": [
        {"ossKey": "oss://bucket/docs/file.pdf", "metadata": {"author": "aliyun", "version": 1}}
    ]
})
```

> **Note:** The metadata fields of a document must match the field names and types defined in the `metadata` parameter when creating the knowledge base; otherwise, the write will be ineffective.

---

## 2. Metadata Filter (During Retrieval)

`MetadataFilter` is used to precisely filter documents by metadata fields during knowledge base retrieval, narrowing the search scope and improving result accuracy.

### Quick Import

```python
from tablestore_agent_storage import MetadataFilter
```

---

### Operator Overview

| Operator | Method | Applicable Types |
|----------|--------|-----------------|
| Equals | `MetadataFilter.equals(key, value)` | string / long / double / boolean |
| Not equals | `MetadataFilter.not_equals(key, value)` | string / long / double / boolean |
| Greater than | `MetadataFilter.greater_than(key, value)` | long / double |
| Greater than or equals | `MetadataFilter.greater_than_or_equals(key, value)` | long / double |
| Less than | `MetadataFilter.less_than(key, value)` | long / double |
| Less than or equals | `MetadataFilter.less_than_or_equals(key, value)` | long / double |
| In list | `MetadataFilter.in_list(key, ["a", "b"])` | string |
| Not in list | `MetadataFilter.not_in_list(key, ["a", "b"])` | string |
| Starts with | `MetadataFilter.starts_with(key, value)` | string |
| String contains | `MetadataFilter.string_contains(key, value)` | string |
| List contains | `MetadataFilter.list_contains(key, value)` | string_list |
| AND | `MetadataFilter.and_all(filter1, filter2, ...)` | Combination |
| OR | `MetadataFilter.or_all(filter1, filter2, ...)` | Combination |

---

### Code Examples

### Single Condition Filtering

```python
# Equals
author_filter = MetadataFilter.equals("author", "aliyun")

# Not equals
not_draft_filter = MetadataFilter.not_equals("status", "draft")

# Numeric comparison
version_filter = MetadataFilter.greater_than_or_equals("version", 2)
score_filter = MetadataFilter.less_than("score", 0.5)

# String prefix matching
prefix_filter = MetadataFilter.starts_with("title", "Alibaba Cloud")

# String contains
contains_filter = MetadataFilter.string_contains("content", "tablestore")

# List membership check (whether the field value is in the given list)
category_filter = MetadataFilter.in_list("category", ["cloud", "ai", "database"])
not_in_filter = MetadataFilter.not_in_list("tag", ["deprecated", "archived"])

# List field contains (field type is string_list, check if the list contains a value)
list_contains_filter = MetadataFilter.list_contains("tags", "production")
```

### Combined Filtering (AND)

All conditions must be satisfied simultaneously:

```python
combined_filter = MetadataFilter.and_all(
    MetadataFilter.equals("author", "aliyun"),
    MetadataFilter.greater_than("version", 1),
    MetadataFilter.in_list("category", ["cloud", "ai"])
)
```

### Combined Filtering (OR)

Any one condition is satisfied:

```python
or_filter = MetadataFilter.or_all(
    MetadataFilter.equals("author", "aliyun"),
    MetadataFilter.equals("author", "alibaba")
)
```

### Nested Combination (AND + OR)

```python
# (author == "aliyun" OR author == "alibaba") AND version > 1
nested_filter = MetadataFilter.and_all(
    MetadataFilter.or_all(
        MetadataFilter.equals("author", "aliyun"),
        MetadataFilter.equals("author", "alibaba")
    ),
    MetadataFilter.greater_than("version", 1)
)
```

### Builder Chaining (AND)

```python
filter_by_builder = (
    MetadataFilter.builder()
    .equals("author", "aliyun")
    .greater_than("version", 1)
    .in_list("category", ["cloud", "ai"])
    .build_and()
)
```

### Builder Chaining (OR)

```python
or_filter_by_builder = (
    MetadataFilter.builder()
    .equals("author", "aliyun")
    .equals("author", "alibaba")
    .build_or()
)
```

---

### Using filter in retrieve

### Dict Style

```python
from tablestore_agent_storage import MetadataFilter

combined_filter = MetadataFilter.and_all(
    MetadataFilter.equals("author", "aliyun"),
    MetadataFilter.greater_than("version", 1)
)

client.retrieve({
    "knowledgeBaseName": "my_kb",
    "retrievalQuery": {"text": "your question", "type": "TEXT"},
    "retrievalConfiguration": {
        "searchType": ["DENSE_VECTOR", "FULL_TEXT"],
        "denseVectorSearchConfiguration": {"numberOfResults": 10},
        "fullTextSearchConfiguration": {"numberOfResults": 10},
        "rerankingConfiguration": {
            "type": "RRF",
            "numberOfResults": 10,
            "rrfConfiguration": {
                "denseVectorSearchWeight": 1.0,
                "fullTextSearchWeight": 1.0,
                "k": 60
            }
        },
        "filter": combined_filter.to_dict()   # Call .to_dict() to serialize
    }
})
```

### Model Style (Recommended)

```python
from tablestore_agent_storage import (
    RetrieveRequest, RetrievalQuery, RetrievalQueryType,
    RetrievalConfiguration, SearchType,
    DenseVectorSearchConfiguration, FulltextSearchConfiguration,
    RerankingConfiguration, RerankingType, RRFConfiguration,
    MetadataFilter
)

combined_filter = MetadataFilter.and_all(
    MetadataFilter.equals("author", "aliyun"),
    MetadataFilter.greater_than("version", 1)
)

request = RetrieveRequest(
    knowledge_base_name="my_kb",
    subspace=["finance"],
    retrieval_query=RetrievalQuery(text="quarterly report", type=RetrievalQueryType.TEXT),
    retrieval_configuration=RetrievalConfiguration(
        search_types=[SearchType.DENSE_VECTOR, SearchType.FULL_TEXT],
        dense_vector_search_configuration=DenseVectorSearchConfiguration(number_of_results=10),
        fulltext_search_configuration=FulltextSearchConfiguration(number_of_results=10),
        reranking_configuration=RerankingConfiguration(
            type=RerankingType.RRF,
            number_of_results=10,
            rrf_configuration=RRFConfiguration(
                dense_vector_search_weight=1.0,
                full_text_search_weight=1.0,
                k=60
            )
        ),
        filter=combined_filter   # Pass MetadataFilter object directly
    )
)
result = client.retrieve(request)
```

---

### Notes

- In Dict style, the `filter` field requires calling `.to_dict()` for serialization; in Model style, pass the `MetadataFilter` object directly
- Filter fields must be pre-defined via the `metadata` parameter when creating the knowledge base; otherwise, filtering will not take effect
- Numeric types (`long` / `double`) only support numeric comparison operators, not string operators
- `string_list` type fields use `list_contains` to check if the list contains a value; `in_list` checks if the field value is in a given candidate list
- `and_all` / `or_all` support arbitrary nesting levels for building complex filtering logic
