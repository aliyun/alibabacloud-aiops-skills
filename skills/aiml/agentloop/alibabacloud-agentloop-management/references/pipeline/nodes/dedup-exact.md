# dedup-exact (exact dedup)

> Remove fully identical text records, keeping one per group.

## Function

The `dedup-exact` node deduplicates on an exact match of the given field. Texts
that are fully identical are treated as duplicates, and each duplicate group keeps
the single record with the longest text (the most informative one).

It is a good first dedup stage in a Pipeline: cheap to compute and able to strip
large amounts of fully duplicated data quickly.

**Use cases**:

- Fully identical text entries produced by logging or data collection
- Redundant records caused by repeated submission or repeated pushes
- A preprocessing step before fuzzy or semantic dedup, cutting the data volume and
  compute cost of the later nodes

## Node configuration

```json
{
  "id": "node_1",
  "type": "dedup-exact",
  "parameters": {
    "field": "<field-name>",
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
| `output` | String | No | `*` | Output columns of the node, comma separated. `*` (default) keeps every column including derived ones. When set, only the listed columns are emitted |
| `global` | Boolean | No | `false` | Whether to enable global dedup (across batches, incrementally against the Dataset) |
| `workspace` | String | Conditionally required | - | Workspace of the Dataset (required when `global` is `true`) |
| `dataset` | String | Conditionally required | - | Dataset name (required when `global` is `true`) |

## Input and output

**Input requirements**:

- Any columns emitted by the upstream node
- The field named by `field` must be present and of a text type

**Output columns**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| Columns controlled by `output` | — | Pass-through / added | `*` keeps every column (including derived ones); when set, only the listed columns are emitted |
| `__dedup_hash` | bigint | Added | Text fingerprint used to identify text uniqueness |
| `__dedup_weight` | integer | Added | Text length; dedup keeps the longest text |
| `__dedup_rnk` | integer | Added | Rank within the group (always 1 after dedup) |

**Row-count change**:

M → N (M ≥ N) — fully identical texts collapse into one row, so the output row
count is at most the input row count.

## Effect preview

**Before** (5 rows):

| question | input | output |
|----------|-------|--------|
| What is machine learning? | Please explain | Machine learning is a branch of AI… |
| What is machine learning? | Please explain in detail | Machine learning (ML) trains models from data… |
| How do I learn Python? | Getting-started guide | Start with the official tutorial… |
| What is deep learning? | In brief | Deep learning is a subset of machine learning… |
| How do I learn Python? | Beginner | Learn the basic syntax first… |

**After** (3 rows) — `field = "question"`:

| question | input | output | __dedup_hash | __dedup_weight | __dedup_rnk |
|----------|-------|--------|-------------|---------------|-------------|
| What is machine learning? | Please explain in detail | Machine learning (ML) trains models from data… | 8832749102 | 25 | 1 |
| How do I learn Python? | Getting-started guide | Start with the official tutorial… | 5561023847 | 22 | 1 |
| What is deep learning? | In brief | Deep learning is a subset of machine learning… | 3347891256 | 22 | 1 |

> Each of the two identical-`question` groups keeps one row (the longest text),
> so 5 rows become 3. When `output` is unset (the default `*`), every column is
> kept including the derived ones; when it names concrete columns, only those are
> emitted.

## Examples

### Example 1: exact dedup within the batch

```json
{
  "id": "n2",
  "type": "dedup-exact",
  "parameters": {
    "field": "question"
  }
}
```

Dedups the current batch on `question` and keeps every column.

### Example 2: global exact dedup

```json
{
  "id": "n2",
  "type": "dedup-exact",
  "parameters": {
    "field": "question",
    "global": true,
    "workspace": "my-ws",
    "dataset": "my-ds"
  }
}
```

On top of the in-batch dedup, it also compares exactly against the Dataset
history and keeps only records that are genuinely new.

### Example 3: choose the output columns

```json
{
  "id": "n2",
  "type": "dedup-exact",
  "parameters": {
    "field": "question",
    "output": "question,answer,model"
  }
}
```

The node emits only the three columns `question`, `answer`, and `model` (derived
columns are allowed in the list; this node's derived columns are excluded when not
listed).

### Example 4: pipeline composition (exact then fuzzy)

```json
{
  "nodes": [
    { "id": "n1", "type": "project", "parameters": { "question": "a", "input": "b", "output": "c" } },
    { "id": "n2", "type": "dedup-exact", "parameters": { "field": "question" } },
    { "id": "n3", "type": "dedup-fuzzy", "parameters": { "field": "question", "threshold": "3" } }
  ]
}
```

Exact dedup removes the fully identical rows first, then fuzzy dedup removes the
slightly different ones.

## Notes

**Recommended usage**:
- Exact dedup is the cheapest, so **use it as the first step of the dedup
  pipeline**: strip the exact duplicates before fuzzy or semantic dedup
- Recommended pipeline order: `dedup-exact` → `dedup-fuzzy` → `dedup-semantic`,
  converging the volume stage by stage
- Global dedup (`global = true`) suits incremental ingestion, keeping the Dataset
  free of duplicates

**Best practices**:
- For a multi-field scenario (dedup on both `question` and `output`), chain
  several `dedup-exact` nodes
- Rows with a NULL value do not take part in dedup and do not appear in the
  output; handle NULLs upstream if they must be kept
- The longest text wins within a group, so make sure `field` really carries text
  content and an empty string does not win by accident

**Edge cases**:

| Case | Behavior |
|------|----------|
| `field` is missing | Validation fails |
| The field named by `field` does not exist | Runtime error |
| The `field` value is NULL | The row is excluded from dedup and from the output |
| `global` is `true` but `workspace` or `dataset` is missing | Validation fails |
| The Dataset does not exist or is unreachable | Runtime error |
| The input is empty | An empty result set is returned normally |

## Related nodes

| Node | Relationship |
|------|--------------|
| `dedup-fuzzy` | Follow exact dedup with fuzzy dedup to converge the data stage by stage |
| `dedup-semantic` | The three-stage exact → fuzzy → semantic dedup pipeline |
| `project` | Normally used after `project` so that the `field` column is ready |
