# dedup-semantic (semantic dedup)

> Remove records whose meaning is the same even though the wording differs.

## Function

The `dedup-semantic` node deduplicates at the semantic level. It maps the text into
a vector representation with an AI model and compares the distance between vectors
to judge semantic similarity. Records within the distance threshold are treated as
semantic duplicates and one representative record survives.

Unlike exact and fuzzy dedup, which match literally, semantic dedup recognizes
texts that read differently but mean the same thing (for example "What's the
weather today?" versus "How is the climate today?"). It is the fine-grained dedup
stage for building a high-quality dataset.

**Use cases**:

- Dedup text that is worded differently but semantically identical
- Cross-language semantic dedup in multilingual scenarios
- Fine-grained dedup for high-quality AI training datasets
- Usually the last dedup stage, after exact and fuzzy dedup

## Node configuration

```json
{
  "id": "node_1",
  "type": "dedup-semantic",
  "parameters": {
    "field": "<field-name>",
    "threshold": "<distance-threshold>",
    "model": "<model-name>",
    "output": "<output-column-list>",
    "global": true,
    "workspace": "<workspace>",
    "dataset": "<dataset>",
    "column_name": "<dataset-column-name>"
  }
}
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `field` | String | **Yes** | - | The field to dedup on; must be a text type |
| `threshold` | String | No | `"0.1"` | Vector-distance threshold (0 to 1); smaller is stricter |
| `model` | String | No | `"embedding-multilang-v3"` | Embedding model name |
| `output` | String | No | `*` | Output columns of the node, comma separated. `*` (default) keeps every column including derived ones. When set, only the listed columns are emitted |
| `global` | Boolean | No | `false` | Whether to enable global dedup |
| `workspace` | String | Conditionally required | - | Workspace of the Dataset (required when `global` is `true`) |
| `dataset` | String | Conditionally required | - | Dataset name (required when `global` is `true`) |
| `column_name` | String | No | Same as `field` | The Dataset column used for semantic dedup (optional when `global` is set) |

> **Threshold guidance**:
>
> | Threshold | Strictness | Description |
> |-----------|-----------|-------------|
> | `"0.05"` | Very strict | Filters only near-synonymous wording |
> | **`"0.1"`** | **Recommended default** | Suits most semantic-dedup scenarios |
> | `"0.15"` to `"0.2"` | Loose | May drop related but non-synonymous text |
> | `"0.3"` and above | Far too loose | Not recommended |

## Input and output

**Input requirements**:

- Any columns emitted by the upstream node
- The field named by `field` must be present and of a text type

**Output columns**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| Columns named by `output` | - | Pass-through | `*` keeps every raw input column |
| `__dedup_emb` | array(double) | Added | The text embedding vector (reusable by a downstream clustering node) |
| `__dedup_rid` | bigint | Added | In-batch row identifier (internal use) |

> **Tip**: the `__dedup_emb` column can be reused directly by a downstream
> `semantic-cluster` node, avoiding a second embedding computation.

**Row-count change**:

M -> N (M >= N) - semantically similar records form one cluster and one row survives
per cluster, so the output row count is at most the input row count.

## Effect preview

**Before** (5 rows):

| question | input | output |
|----------|-------|--------|
| What is machine learning? | Please explain | Machine learning is... |
| What is the definition of machine learning? | Overview | ML trains models from data... |
| How do I get started with Python programming? | Guide | Start with the official tutorial... |
| How can a complete beginner learn Python? | Getting started | Learn the basic syntax first... |
| What is deep learning? | In brief | Deep learning is a subset of machine learning... |

**After** (3 rows) - `field = "question"`, `threshold = "0.1"`:

| question | input | output | __dedup_emb | __dedup_rid |
|----------|-------|--------|------------|------------|
| What is machine learning? | Please explain | Machine learning is... | [0.12, -0.34, ...] | 1 |
| How do I get started with Python programming? | Guide | Start with the official tutorial... | [0.56, 0.78, ...] | 3 |
| What is deep learning? | In brief | Deep learning is a subset of machine learning... | [-0.11, 0.45, ...] | 5 |

> The two machine-learning questions are semantically equivalent (vector distance
> < 0.1), so they form one cluster and one row survives; the two Python questions
> behave the same way. 5 rows become 3. `__dedup_emb` can be reused directly by a
> downstream `semantic-cluster` node.

## Examples

### Example 1: in-batch semantic dedup

```json
{
  "id": "n4",
  "type": "dedup-semantic",
  "parameters": {
    "field": "question",
    "threshold": "0.1"
  }
}
```

### Example 2: global semantic dedup

```json
{
  "id": "n4",
  "type": "dedup-semantic",
  "parameters": {
    "field": "question",
    "threshold": "0.1",
    "global": true,
    "workspace": "my-ws",
    "dataset": "my-ds"
  }
}
```

Semantic dedup across batches, compared against the Dataset's historical vectors.

### Example 3: the complete three-stage dedup pipeline

```json
{
  "nodes": [
    { "id": "n1", "type": "project", "parameters": { "question": "a", "input": "b", "output": "c" } },
    { "id": "n2", "type": "dedup-exact", "parameters": { "field": "question" } },
    { "id": "n3", "type": "dedup-fuzzy", "parameters": { "field": "question", "threshold": "3", "global": true, "workspace": "my-ws", "dataset": "my-ds" } },
    { "id": "n4", "type": "dedup-semantic", "parameters": { "field": "question", "threshold": "0.1", "global": true, "workspace": "my-ws", "dataset": "my-ds" } }
  ]
}
```

Exact -> fuzzy -> semantic, dedup stage by stage.

### Example 4: custom model

```json
{
  "id": "n4",
  "type": "dedup-semantic",
  "parameters": {
    "field": "question",
    "threshold": "0.05",
    "model": "text-embedding-v3",
    "global": true,
    "workspace": "my-ws",
    "dataset": "my-ds",
    "column_name": "question"
  }
}
```

## Notes

**Recommended usage**:
- **Strongly prefer running it after `dedup-exact` and `dedup-fuzzy`** - semantic
  dedup computes embeddings (GPU inference), so the earlier dedup stages cut both
  the workload and the cost substantially
- Recommended pipeline order: `dedup-exact` -> `dedup-fuzzy` -> `dedup-semantic`
  (three-stage dedup)
- The default threshold `"0.1"` suits most scenarios; a smaller value is stricter

**Best practices**:
- The `__dedup_emb` derived column can be reused directly by a downstream
  `semantic-cluster` node, avoiding a second embedding computation
- Global dedup suits incremental ingestion and requires the Dataset to have a
  vector index enabled
- There is no need to call `embedding` before `dedup-semantic` - this node already
  generates embeddings internally

**Edge cases**:

| Case | Behavior |
|------|----------|
| `field` is missing | Validation fails |
| `threshold` falls outside [0, 1] | Validation fails |
| `global` is `true` but `workspace` or `dataset` is missing | Validation fails |
| The embedding model is unavailable | Runtime error |
| The `field` value is NULL | The row is excluded from dedup and from the output |
| The input is empty | An empty result set is returned normally |

## Related nodes

| Node | Relationship |
|------|--------------|
| `dedup-exact` | Run exact dedup first to shrink the input to semantic dedup |
| `dedup-fuzzy` | Run near dedup first as well |
| `semantic-cluster` | Can reuse the `__dedup_emb` column for clustering without recomputing embeddings |
