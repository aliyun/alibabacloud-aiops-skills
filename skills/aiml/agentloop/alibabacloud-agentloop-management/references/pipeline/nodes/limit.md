# limit (row limit)

> Cap the number of records a node emits; equivalent to SQL `LIMIT`.

## Function

The `limit` node truncates the data volume quickly, at the end of a pipeline or
in the middle of one, keeping only the first `n` records. It performs no field
transformation and adds no columns; it only controls the output size.

Common uses:

- Preview Pipeline results without scanning an oversized dataset
- Validate downstream node behavior quickly while debugging
- Shrink the data volume before an expensive node such as an LLM call

## Node configuration

```json
{
  "id": "node_1",
  "type": "limit",
  "parameters": {
    "n": 5
  }
}
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `n` | Integer | Yes | - | Maximum number of records to output; must be a positive integer |

## Input and output

**Input requirements**:

- Any structure emitted by the upstream node

**Output columns**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| All input columns | - | Pass-through | The column structure is unchanged; only the row count is limited |

**Row-count change**:

M -> N (M >= N) - rows are truncated only, `N = min(M, n)`.

## Examples

### Example 1: preview the first 5 rows

```json
{
  "id": "n9",
  "type": "limit",
  "parameters": {
    "n": 5
  }
}
```

### Example 2: cap the output at the end of a full pipeline

```json
{
  "nodes": [
    { "id": "n1", "type": "project", "parameters": { "question": "a", "output": "c" } },
    { "id": "n2", "type": "dedup-exact", "parameters": { "field": "question" } },
    { "id": "n3", "type": "limit", "parameters": { "n": 100 } }
  ]
}
```

## Notes

- `n` must be a positive integer; `0`, a negative value, or a non-integer fails
  validation.
- `limit` does not guarantee a business-stable order. For a deterministic result,
  order the rows explicitly upstream first.
- This node does not support the `output` parameter wrapper (same as `project`,
  `extend`, and `where`).

## Related nodes

| Node | Relationship |
|------|--------------|
| `sample` | Both reduce volume; `sample` picks rows randomly, `limit` truncates directly |
| `llm-call` | Placing a `limit` before an LLM call cuts invocation cost significantly |
