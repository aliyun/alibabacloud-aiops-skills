# embedding (vector generation)

> Generate an embedding vector for the given text field.

## Function

The `embedding` node calls an AI model to map a text field into a high-dimensional
dense vector. The resulting vector can be used directly by downstream tasks such
as semantic retrieval, clustering, and vector-index construction.

Each record is embedded independently and the row count does not change.

**Use cases**:

- Provide the vector input needed by downstream nodes such as
  `semantic-cluster` and `sample`
- Build an embedding column in the Dataset (for example `question_embedding`)
- Build a vector-search index

## Node configuration

```json
{
  "id": "node_1",
  "type": "embedding",
  "parameters": {
    "field": "<field-name>",
    "model": "<model-name>",
    "as": "<output-column-name>",
    "output": "<output-column-list>"
  }
}
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `field` | String | **Yes** | - | The text field to vectorize |
| `model` | String | No | `"embedding-multilang-v3"` | Embedding model name |
| `as` | String | No | `"{field}_embedding"` | Name of the embedding output column; the default appends the `_embedding` suffix |
| `output` | String | No | `*` | Output columns of the node, comma separated. `*` (default) keeps every column including derived ones. When set, only the listed columns are emitted |

## Input and output

**Input requirements**:

- Any columns emitted by the upstream node
- The field named by `field` must be present and of a text type

**Output columns**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| Columns controlled by `output` | — | Pass-through / added | `*` keeps every column (including derived ones); when set, only the listed columns are emitted |
| `{as}` | array(double) | Added | The text embedding vector |

**Row-count change**:

M → N (M = N) — a 1:1 transformation that neither adds nor drops rows.

> **Note**: rows whose `field` value is NULL are dropped.

## Effect preview

**Before** (3 rows):

| question | input | output |
|----------|-------|--------|
| What is machine learning? | Please explain | Machine learning is… |
| How do I learn Python? | Getting started | Start with the official tutorial… |
| What is deep learning? | In brief | Deep learning is… |

**After** (3 rows) — `field = "question"`:

| question | input | output | question_embedding |
|----------|-------|--------|--------------------|
| What is machine learning? | Please explain | Machine learning is… | [0.12, -0.34, 0.56, …] |
| How do I learn Python? | Getting started | Start with the official tutorial… | [0.78, 0.23, -0.11, …] |
| What is deep learning? | In brief | Deep learning is… | [-0.45, 0.67, 0.89, …] |

> The row count is unchanged (3 → 3) and every row gains an embedding vector
> column. The column is named `{field}_embedding` by default and can be renamed
> with the `as` parameter.

## Examples

### Example 1: basic vectorization

```json
{
  "id": "n3",
  "type": "embedding",
  "parameters": {
    "field": "question"
  }
}
```

The output column is named `question_embedding` automatically.

### Example 2: custom output column and model

```json
{
  "id": "n3",
  "type": "embedding",
  "parameters": {
    "field": "content",
    "as": "content_vec",
    "model": "text-embedding-v3"
  }
}
```

### Example 3: pipeline composition (dedup then vectorize)

```json
{
  "nodes": [
    { "id": "n1", "type": "project", "parameters": { "question": "a", "output": "c" } },
    { "id": "n2", "type": "dedup-exact", "parameters": { "field": "question" } },
    { "id": "n3", "type": "embedding", "parameters": { "field": "question" } }
  ]
}
```

Dedup first, then embed, which reduces the vectorization workload.

### Example 4: vectorize several fields separately

```json
{
  "nodes": [
    { "id": "n1", "type": "project", "parameters": { "question": "a", "input": "b", "output": "c" } },
    { "id": "n2", "type": "embedding", "parameters": { "field": "question" } },
    { "id": "n3", "type": "embedding", "parameters": { "field": "output", "as": "output_embedding" } }
  ]
}
```

One call handles one field; chain nodes to cover several fields.

## Notes

**Recommended usage**:
- **Use it after dedup or sampling** — embedding generation is a remote GPU
  inference call, so reducing the volume first cuts cost significantly
- If an upstream `dedup-semantic` already ran, reuse its `__dedup_emb` derived
  column instead of calling `embedding` again
- Vectorize several fields by chaining several `embedding` nodes (one field each)

**Best practices**:
- The default model `embedding-multilang-v3` suits general multilingual use
- Rename the output column with `as` (default `{field}_embedding`) to avoid
  collisions with existing columns
- NULL rows are dropped; handle NULLs upstream if they must be kept

**Edge cases**:

| Case | Behavior |
|------|----------|
| `field` is missing | Validation fails |
| The `field` value is NULL | The row is dropped and does not appear in the output |
| The model name is invalid | Runtime error |
| The text exceeds the model limit | Decided by the model (truncation or error) |
| The `as` column name collides with an input column | Runtime error |
| The input is empty | An empty result set is returned normally |

## Related nodes

| Node | Relationship |
|------|--------------|
| `semantic-cluster` | The vector column produced by `embedding` can feed `semantic-cluster` |
| `dedup-semantic` | `dedup-semantic` already generates embeddings internally, so there is no need to call `embedding` before it |
