# embedding (vector generation)

> Generate an embedding vector for a text field, providing the vector
> representation that semantic search, deduplication, and clustering need
> downstream.

## Function

Calls the configured embedding model to map a text field into a high-dimensional
dense vector (`array(double)`). The resulting vector can be used directly for
semantic-similarity comparison, clustering, vector search, and other downstream
tasks.

Each record is embedded independently, so the input and output row counts match (a
1:1 transformation).

**Use cases**:

- Provide vector input to downstream operators such as semantic dedup
  (`dedup-semantic`), clustering (`semantic-cluster`), and sampling (`sample`)
- Build embedding columns in a Dataset (for example `question_embedding` or
  `output_embedding`)
- Build a vector-search index

## Syntax

```
| embedding -field=<column> [-model=<model>] [as <name>]
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `-field` | Field | **Yes** | - | The text field to embed; must be a varchar column |
| `-model` | String | No | `'embedding-multilang-v3'` | Embedding model name |
| `as` | Field | No | `{field}_embedding` | Name of the embedding output column; the default appends the `_embedding` suffix (an instruction primitive, without the `-` prefix) |

> **Model selection reference**:
>
> | Model | Dimensions | Description |
> |-------|------------|-------------|
> | `embedding-multilang-v3` | 1024 | **Default**; multilingual, suitable for general use |
> | `text-embedding-v3` | — | Optional alternative model, configured on demand |

## Input and output

**Input**:

- Any columns emitted by the upstream operator
- The field named by `-field` must be present and be a text column (varchar)

**Output**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| All input columns | — | Input | Every upstream column passes through |
| `{{as}}` | array(double) | Derived | The text embedding vector |

**Input-to-output relationship**:

M:N (M = N) — a 1:1 transformation; each row is embedded independently and no rows
are added or dropped.

> **Note**: rows whose `-field` value is NULL are filtered out and do not appear in
> the output. Handle NULLs upstream if they must be kept.

## Effect preview

**Before** (3 rows):

| question | input | output |
|----------|-------|--------|
| What is machine learning? | Please explain | Machine learning is… |
| How do I learn Python? | Getting started | Start with the official tutorial… |
| What is deep learning? | In brief | Deep learning is… |

**After** (3 rows) — `| embedding -field=question`:

| question | input | output | question_embedding |
|----------|-------|--------|--------------------|
| What is machine learning? | Please explain | Machine learning is… | [0.12, -0.34, 0.56, …] (1024 dims) |
| How do I learn Python? | Getting started | Start with the official tutorial… | [0.78, 0.23, -0.11, …] (1024 dims) |
| What is deep learning? | In brief | Deep learning is… | [-0.45, 0.67, 0.89, …] (1024 dims) |

> The row count is unchanged (3 → 3) and every row gains a `question_embedding`
> vector column (the default name is the field name plus `_embedding`). Downstream
> operators such as `semantic-cluster` and `dedup-semantic` can consume the vector
> directly.

## Examples

### Example 1: basic embedding

```
* | project question,input,output
  | embedding -field=question
```

Embeds the `question` field; the output column is named `question_embedding`
automatically.

### Example 2: custom output column and model

```
* | project content
  | embedding -field=content -model='text-embedding-v3' as content_vec
```

### Example 3: pipeline composition (dedup → embedding)

```
* | project question,input,output
  | dedup-exact -field=question
  | dedup-fuzzy -field=question -threshold='3'
  | embedding -field=question
```

Deduplicating first and embedding afterwards reduces the amount of vectorization
work.

### Example 4: embedding several fields separately

```
* | project question,input,output
  | embedding -field=question
  | embedding -field=input as input_embedding
  | embedding -field=output as output_embedding
```

Each call handles exactly one field; chain the operator to cover several fields.

---

> **Everything below this line is the internal implementation spec, aimed at the
> development and engineering teams. Hide it when publishing user documentation.**

## Design notes

- **Relationship with dedup-semantic**: `dedup-semantic` already generates
  embeddings internally (it emits the `__dedup_emb` derived column), so there is no
  need to call `embedding` before it. The `embedding` operator exists mainly to
  (1) produce the final vector columns written to a Dataset (`question_embedding` and
  friends) and (2) supply vectors for non-dedup scenarios such as retrieval and
  classification.
- **Single-field design**: each call handles one field. Cover several fields by
  chaining calls (see Example 4). The optimizer may fold consecutive `embedding`
  calls into a single SQL execution (several `embedding` function calls inside the
  same CTE).
- **Performance considerations**: embedding generation is a remote function call
  (network IO plus GPU inference), so prefer calling it after deduplication and
  sampling to reduce the work.
- **NULL handling**: the current implementation filters NULL rows with `WHERE`. To
  keep NULL rows and set the embedding to NULL instead, switch to a `CASE WHEN`
  expression (see the alternative template).

## SQL implementation template

### Standard mode

```sql
set session enable_remote_functions = true;
WITH
_emb_data AS (
    SELECT 
        embedding({{field}}, '{{model}}') AS {{as}}
        ##otherColumns##
    FROM ##sourceTable##
    WHERE {{field}} IS NOT NULL
)
SELECT * FROM _emb_data
```

## Template variables

| Template variable | Parameter | Default | Description |
|-------------------|-----------|---------|-------------|
| `{{field}}` | `-field` | - | The text field name |
| `{{model}}` | `-model` | `'embedding-multilang-v3'` | Embedding model name |
| `{{as}}` | `as` | `{field}_embedding` | Output column name. When rendering, the engine appends the `_embedding` suffix to the `-field` value to form the default name |
| `##sourceTable##` | Resolved by the engine | - | The upstream CTE name or base query table |
| `##otherColumns##` | Derived by the engine | - | Pass-through macro for non-derived columns; commas and duplicate column names are handled automatically afterwards |

## Dependent functions

| Signature | Description |
|-----------|-------------|
| `embedding(text, model) → array(double)` | Generate a text embedding vector with the given model (remote function) |

## Edge cases

| Case | Handling |
|------|----------|
| The `-field` column does not exist | The engine raises a parameter-validation error reporting the missing field |
| The `-field` value is NULL | Standard mode: filtered by `WHERE`, so the NULL row does not appear in the output |
| The input is empty (0 rows) | An empty result set is returned normally |
| The model name is invalid | The `embedding` function raises a runtime error asking you to check the model name |
| The text exceeds the model length limit | Handled by the `embedding` function (truncate or error); the exact behavior depends on the model |
| The `as` column name collides with an input column | The engine raises a column-name conflict error asking you to pick another name |
