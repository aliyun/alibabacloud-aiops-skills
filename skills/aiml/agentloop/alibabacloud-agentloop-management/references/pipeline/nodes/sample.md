# sample (random sampling)

> Randomly sample a given ratio or number of records, optionally per group.

## Function

The `sample` node samples the input data randomly in two modes:

1. **Global sampling**: sample a given ratio (`ratio`) or number (`n`) of records
   from the whole dataset
2. **Per-group sampling**: group by the given column (`by`) and sample
   independently inside each group

It is often combined with an upstream `semantic-cluster` for "diversity sampling":
cluster first, then sample per cluster, so downsampling preserves semantic
diversity.

**Use cases**:

- Fast downsampling of large datasets
- Diversity sampling combined with `semantic-cluster`
- Even sampling across a dimension such as category, label, or cluster ID
- Volume control before AI processing (reducing LLM invocation cost)

## Node configuration

```json
{
  "id": "node_1",
  "type": "sample",
  "parameters": {
    "ratio": "<sampling-rate>",
    "n": <sample-count>,
    "by": "<grouping-column>",
    "output": "<output-column-list>"
  }
}
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `ratio` | String/Number | One of the two | - | Sampling rate in (0, 1]; `0.1` means 10%. Mutually exclusive with `n` |
| `n` | Integer | One of the two | - | Number of records to sample. Mutually exclusive with `ratio` |
| `by` | String | No | - | Grouping columns, comma separated. Enables per-group sampling |
| `output` | String | No | `*` | Output columns of the node, comma separated. `*` (default) keeps every column including derived ones. When set, only the listed columns are emitted |

> **Choosing between `ratio` and `n`**:
>
> | Scenario | Recommended parameter | Description |
> |----------|----------------------|-------------|
> | "Give me 10% of the data" | `ratio: 0.1` | The output scales with the input |
> | "Give me 100 records" | `n: 100` | Fixed output size |
> | "One row per group" | `by: "__cluster_id", n: 1` | Diversity sampling together with clustering |
> | "Keep 20% of each group" | `by: "category", ratio: 0.2` | Even sampling per category |

## Input and output

**Input requirements**:

- Any columns emitted by the upstream node
- When `by` is set, the named grouping columns must be present

**Output columns**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| Columns controlled by `output` | — | Pass-through | `*` keeps every column; when set, only the listed columns are emitted |

> This node produces no derived columns; it only drops rows. `output` controls the
> node's final output columns.

**Row-count change**:

M → N (M ≥ N) — the sampled output row count is at most the input row count.

## Effect preview

**Before** (6 rows):

| question | output | __cluster_id |
|----------|--------|-------------|
| What is machine learning? | Machine learning is… | 0 |
| What types of machine learning exist? | Supervised / unsupervised / reinforcement… | 0 |
| How do I learn Python? | Start with the official tutorial… | 1 |
| Which Python libraries are there? | NumPy, Pandas… | 1 |
| What is deep learning? | Deep learning is… | 2 |
| What is a neural network? | A neural network has several layers… | 2 |

**After** (3 rows) — `n = 1`, `by = "__cluster_id"`:

| question | output | __cluster_id |
|----------|--------|-------------|
| What types of machine learning exist? | Supervised / unsupervised / reinforcement… | 0 |
| How do I learn Python? | Start with the official tutorial… | 1 |
| What is deep learning? | Deep learning is… | 2 |

> One random row per cluster, so 6 rows become 3. This node produces no derived
> columns; it only drops rows.

## Examples

### Example 1: global 10% random sample

```json
{
  "id": "n5",
  "type": "sample",
  "parameters": {
    "ratio": 0.1
  }
}
```

### Example 2: global sample of a fixed size

```json
{
  "id": "n5",
  "type": "sample",
  "parameters": {
    "n": 100
  }
}
```

### Example 3: cluster plus per-group sampling (recommended)

```json
{
  "nodes": [
    { "id": "n4", "type": "semantic-cluster", "parameters": { "field": "__dedup_emb", "n": 100 } },
    { "id": "n5", "type": "sample", "parameters": { "by": "__cluster_id", "n": 1 } }
  ]
}
```

100 clusters with one row each yields roughly 100 diverse samples.

### Example 4: per-category sampling

```json
{
  "id": "n5",
  "type": "sample",
  "parameters": {
    "by": "category",
    "ratio": 0.2
  }
}
```

### Example 5: multi-dimensional grouping

```json
{
  "id": "n5",
  "type": "sample",
  "parameters": {
    "by": "category,difficulty",
    "n": 10
  }
}
```

## Notes

**Recommended usage**:
- **Use it before LLM processing** — downsampling first keeps AI invocation cost
  under control
- Combine it with `semantic-cluster` for diversity sampling:
  `semantic-cluster` → `sample` (grouping by `by = "__cluster_id"`)
- `ratio` fits "keep a percentage" scenarios and `n` fits "fixed count"
  scenarios; the two are mutually exclusive

**Best practices**:
- Recommended diversity sampling: `sample` with `n = 1` and
  `by = "__cluster_id"`, taking one representative row per cluster
- Stratified even sampling: use `by` on a category or label column so each group
  is sampled independently
- Sampling is random, so results can differ between runs

**Edge cases**:

| Case | Behavior |
|------|----------|
| Neither `ratio` nor `n` is set | Validation fails |
| Both `ratio` and `n` are set | Validation fails |
| `ratio` falls outside (0, 1] | Validation fails |
| `n` ≤ 0 | Validation fails |
| A column named by `by` does not exist | Runtime error |
| `n` is greater than the row count | All rows are returned |
| The input is empty | An empty result set is returned normally |

## Related nodes

| Node | Relationship |
|------|--------------|
| `semantic-cluster` | Cluster first, then sample per cluster for diversity sampling |
| `llm-call` | Sample before LLM processing to control AI invocation cost |
