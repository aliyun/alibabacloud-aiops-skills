# dedup-fuzzy (near dedup)

> Remove records whose text is highly similar but not identical.

## Function

The `dedup-fuzzy` node deduplicates on an approximate match of the given field. It
compares how literally similar the texts are, treats records above the similarity
threshold as near duplicates, and keeps only the longest text in each group.

It catches typos, punctuation differences, and whitespace differences, which makes
it a good fit for filtering repeated submissions or template-generated similar
text.

**Use cases**:

- Duplicated data with minor differences (typos, punctuation changes, whitespace
  differences)
- Template-generated similar text (near-identical output from small prompt tweaks)
- Quasi-duplicates in a crawler or collection pipeline caused by formatting
  differences

## Node configuration

```json
{
  "id": "node_1",
  "type": "dedup-fuzzy",
  "parameters": {
    "field": "<field-name>",
    "threshold": "<threshold>",
    "output": "<output-column-list>",
    "global": true,
    "workspace": "<workspace>",
    "dataset": "<dataset>"
  }
}
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `field` | String | **Yes** | - | The field to dedup on; must be a text type |
| `threshold` | String | No | `"3"` | Similarity threshold (a non-negative integer string); smaller is stricter |
| `output` | String | No | `*` | Output columns of the node, comma separated. `*` (default) keeps every column including derived ones. When set, only the listed columns are emitted |
| `global` | Boolean | No | `false` | Whether to enable global dedup |
| `workspace` | String | Conditionally required | - | Workspace of the Dataset (required when `global` is `true`) |
| `dataset` | String | Conditionally required | - | Dataset name (required when `global` is `true`) |

> **Threshold guidance**:
>
> | Threshold | Strictness | Description |
> |-----------|-----------|-------------|
> | `"0"` | Exact match | Equivalent to `dedup-exact` |
> | `"1"` to `"2"` | Very strict | Filters only single-character differences |
> | **`"3"`** | **Recommended default** | Suits most text-dedup scenarios |
> | `"5"` to `"7"` | Loose | May drop text with meaningful differences; use with care |

## Input and output

**Input requirements**:

- Any columns emitted by the upstream node
- The field named by `field` must be present and of a text type

**Output columns**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| Columns controlled by `output` | - | Pass-through / added | `*` keeps every column (including derived ones); when set, only the listed columns are emitted |
| `__dedup_hash` | bigint | Added | Text fingerprint |
| `__dedup_weight` | integer | Added | Text length |
| `__dedup_rnk` | integer | Added | Rank within the cluster (always 1 after dedup) |

**Row-count change**:

M -> N (M >= N) - similar texts are grouped into one cluster and one row survives
per cluster, so the output row count is at most the input row count.

## Effect preview

**Before** (5 rows):

| question | input | output |
|----------|-------|--------|
| What is machine learning? | Please explain | Machine learning is... |
| What is machine learning, exactly? | Explain in detail | Machine Learning (ML) is... |
| How do I learn Python? | Getting started | Start with the official tutorial... |
| How can I learn Python? | Guide | Learn the basic syntax first... |
| What is deep learning? | In brief | Deep learning is a subset of machine learning... |

**After** (3 rows) - `field = "question"`, `threshold = "3"`:

| question | input | output | __dedup_hash | __dedup_weight | __dedup_rnk |
|----------|-------|--------|-------------|---------------|-------------|
| What is machine learning, exactly? | Explain in detail | Machine Learning (ML) is... | 8832749102 | 34 | 1 |
| How do I learn Python? | Getting started | Start with the official tutorial... | 5561023847 | 22 | 1 |
| What is deep learning? | In brief | Deep learning is a subset of machine learning... | 3347891256 | 22 | 1 |

> The two machine-learning questions are highly similar (fingerprint distance
> <= 3), so they form one cluster and the longest one survives; the two Python
> questions behave the same way. 5 rows become 3.

## Examples

### Example 1: in-batch near dedup (default threshold)

```json
{
  "id": "n3",
  "type": "dedup-fuzzy",
  "parameters": {
    "field": "question"
  }
}
```

Near-dedups `question` with the default threshold `"3"`.

### Example 2: adjust the threshold

```json
{
  "id": "n3",
  "type": "dedup-fuzzy",
  "parameters": {
    "field": "question",
    "threshold": "5"
  }
}
```

Loosens the threshold to 5, removing more near-duplicate text.

### Example 3: global near dedup

```json
{
  "id": "n3",
  "type": "dedup-fuzzy",
  "parameters": {
    "field": "question",
    "threshold": "3",
    "global": true,
    "workspace": "my-ws",
    "dataset": "my-ds"
  }
}
```

Global dedup across batches, comparing approximately against the Dataset history.

### Example 4: pipeline composition (exact then fuzzy)

```json
{
  "nodes": [
    { "id": "n1", "type": "project", "parameters": { "question": "a", "input": "b" } },
    { "id": "n2", "type": "dedup-exact", "parameters": { "field": "question" } },
    { "id": "n3", "type": "dedup-fuzzy", "parameters": { "field": "question", "threshold": "3", "global": true, "workspace": "my-ws", "dataset": "my-ds" } }
  ]
}
```

## Notes

**Recommended usage**:
- **Use it after `dedup-exact`**: strip the fully identical rows first so that
  near dedup handles only the small differences, which reduces SimHash work
- Recommended pipeline order: `dedup-exact` -> `dedup-fuzzy` -> `dedup-semantic`
- The default threshold `"3"` suits most text-dedup scenarios; a smaller value is
  stricter

**Best practices**:
- Threshold `"0"` is equivalent to exact dedup, `"3"` suits everyday use, and
  values above `"5"` may drop text with meaningful differences
- Global dedup suits incremental cross-batch ingestion
- Rows whose field value is NULL do not take part in dedup and do not appear in
  the output

**Edge cases**:

| Case | Behavior |
|------|----------|
| `field` is missing | Validation fails |
| `threshold` is negative or non-numeric | Validation fails |
| `threshold` is too large (>= 64) | Every record falls into one cluster and only one row survives |
| `global` is `true` but `workspace` or `dataset` is missing | Validation fails |
| The `field` value is NULL | The row is excluded from dedup and from the output |
| The input is empty | An empty result set is returned normally |

## Related nodes

| Node | Relationship |
|------|--------------|
| `dedup-exact` | Run `dedup-exact` before `dedup-fuzzy` to strip the exact duplicates and cut compute cost |
| `dedup-semantic` | Follow near dedup with semantic dedup for the full three-stage pipeline |
