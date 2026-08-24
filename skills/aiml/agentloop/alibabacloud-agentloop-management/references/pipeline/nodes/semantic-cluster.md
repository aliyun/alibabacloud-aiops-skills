# semantic-cluster (semantic clustering)

> Assign a cluster ID to each row from its embedding vector.

## Function

The `semantic-cluster` node clusters the given embedding-vector column, putting
semantically close records into the same cluster. Each record receives a cluster
number (`__cluster_id`); no data is filtered, only a grouping label is added.

It is usually combined with a downstream `sample` node for "diversity sampling":
cluster first, then sample within each cluster.

**Use cases**:

- Combine with `sample` for representative sampling with guaranteed diversity
- Data-distribution analysis: observe the size and spread of the semantic clusters
- Semantic grouping: gather similar records for batch processing

## Node configuration

```json
{
  "id": "node_1",
  "type": "semantic-cluster",
  "parameters": {
    "field": "<embedding-vector-column>",
    "n": <cluster-count>,
    "output": "<output-column-list>"
  }
}
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `field` | String | **Yes** | - | The embedding-vector column to cluster on; must be array(double) |
| `n` | Integer | **Yes** | - | Number of clusters (a positive integer) |
| `output` | String | No | `*` | Output columns of the node, comma separated. `*` (default) keeps every column including derived ones. When set, only the listed columns are emitted |

> **Cluster-count guidance**:
>
> | Data volume | Recommended `n` range |
> |-------------|----------------------|
> | < 100 | 5 to 10 |
> | 100 to 1,000 | 10 to 50 |
> | 1,000 to 10,000 | 50 to 100 |
> | > 10,000 | 100 to 500 |

## Input and output

**Input requirements**:

- Any columns emitted by the upstream node
- The embedding-vector column named by `field` must be present and of type
  array(double)
- Normally placed after `embedding` or after `dedup-semantic` (which emits
  `__dedup_emb`)

**Output columns**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| Columns controlled by `output` | - | Pass-through / added | `*` keeps every column (including derived ones); when set, only the listed columns are emitted |
| `__cluster_id` | bigint | Added | Cluster number (starting at 0) |

**Row-count change**:

M -> N (M = N) - a 1:1 transformation that adds a cluster label without adding or
dropping rows.

## Effect preview

**Before** (6 rows):

| question | __dedup_emb |
|----------|------------|
| What is machine learning? | [0.12, -0.34, ...] |
| What types of machine learning exist? | [0.15, -0.30, ...] |
| How do I learn Python? | [0.78, 0.23, ...] |
| Which Python libraries are there? | [0.75, 0.20, ...] |
| What is deep learning? | [-0.11, 0.45, ...] |
| What is a neural network? | [-0.09, 0.42, ...] |

**After** (6 rows) - `field = "__dedup_emb"`, `n = 3`:

| question | __dedup_emb | __cluster_id |
|----------|------------|-------------|
| What is machine learning? | [0.12, -0.34, ...] | 0 |
| What types of machine learning exist? | [0.15, -0.30, ...] | 0 |
| How do I learn Python? | [0.78, 0.23, ...] | 1 |
| Which Python libraries are there? | [0.75, 0.20, ...] | 1 |
| What is deep learning? | [-0.11, 0.45, ...] | 2 |
| What is a neural network? | [-0.09, 0.42, ...] | 2 |

> The row count is unchanged (6 -> 6) and every row gains a `__cluster_id`.
> Semantically close records land in the same cluster. Downstream, a `sample` node
> with `by = "__cluster_id"` can take one row per cluster for diversity sampling.

## Examples

### Example 1: basic clustering

```json
{
  "id": "n5",
  "type": "semantic-cluster",
  "parameters": {
    "field": "question_embedding",
    "n": 10
  }
}
```

Clusters the data into 10 clusters on `question_embedding`.

### Example 2: cluster plus per-group sampling (diversity sampling)

```json
{
  "nodes": [
    { "id": "n1", "type": "project", "parameters": { "question": "a", "output": "c" } },
    { "id": "n2", "type": "embedding", "parameters": { "field": "question" } },
    { "id": "n3", "type": "semantic-cluster", "parameters": { "field": "question_embedding", "n": 100 } },
    { "id": "n4", "type": "sample", "parameters": { "by": "__cluster_id", "n": 1 } }
  ]
}
```

100 clusters with one row each yields roughly 100 diverse representative samples.

### Example 3: reuse the vector column from dedup-semantic

```json
{
  "nodes": [
    { "id": "n1", "type": "project", "parameters": { "question": "a", "input": "b", "output": "c" } },
    { "id": "n2", "type": "dedup-exact", "parameters": { "field": "question" } },
    { "id": "n3", "type": "dedup-semantic", "parameters": { "field": "question", "threshold": "0.1" } },
    { "id": "n4", "type": "semantic-cluster", "parameters": { "field": "__dedup_emb", "n": 100 } },
    { "id": "n5", "type": "sample", "parameters": { "by": "__cluster_id", "n": 1 } }
  ]
}
```

Reuses the `__dedup_emb` column emitted by `dedup-semantic`, avoiding a second
embedding computation.

## Notes

**Recommended usage**:
- **Combine it with `sample` for diversity sampling** - cluster first, then sample
  per cluster to get both downsampling and semantic diversity
- Typical pipeline: `dedup-semantic` -> `semantic-cluster` -> `sample` (reusing
  `__dedup_emb` directly)
- Pick `n` from the data scale: 5-10 for hundreds of rows, 50-100 for thousands,
  100-500 for tens of thousands

**Best practices**:
- The input must be an embedding-vector column (type `array(double)`), coming
  either from the `embedding` node or from `dedup-semantic`'s `__dedup_emb`
- This node only labels the cluster ID and does not change the row count;
  downsampling happens in the downstream `sample` node
- Do not set `n` too high (clustering performance suffers) or too low (clusters
  grow so large that diversity becomes meaningless)

**Edge cases**:

| Case | Behavior |
|------|----------|
| `field` is missing | Validation fails |
| `n` is missing or <= 0 | Validation fails |
| `field` is not array(double) | Runtime error |
| `n` is greater than the row count | Handled by the engine; the effective cap is the row count |
| The embedding dimensions are inconsistent | Runtime error |
| The input is empty | An empty result set is returned normally |

## Related nodes

| Node | Relationship |
|------|--------------|
| `sample` | Follow clustering with `sample by __cluster_id` for diversity sampling |
| `embedding` | The vector column must be produced by `embedding` or `dedup-semantic` first |
| `dedup-semantic` | Its `__dedup_emb` column can be reused directly as the clustering input |
