# where (filtering)

> Filter rows by a condition expression, keeping only the records that satisfy it.

## Function

The `where` node evaluates a condition on every row and keeps only the rows whose
expression evaluates to `true`, discarding the rest.

All boolean expressions and comparison operators are supported, and built-in
functions can be used.

**Use cases**:

- Filter out low-quality data (text that is too short, empty fields)
- Select a specific category of data by business condition
- Filter on an upstream computation result (for example records whose AI score is
  below a threshold)

## Node configuration

```json
{
  "id": "node_1",
  "type": "where",
  "parameters": {
    "filter": "<boolean-expression>"
  }
}
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `filter` | String | **Yes** | - | The filter expression; it must evaluate to a boolean. `AND`/`OR`/`NOT` combinations are supported |

> **Supported operators**: `=`, `!=`, `>`, `<`, `>=`, `<=`, `LIKE`, `IN`,
> `IS NULL`, `IS NOT NULL`, `BETWEEN`, `AND`, `OR`, `NOT`

## Input and output

**Input requirements**:

- Any columns emitted by the upstream node
- Every field referenced by the expression must exist in the input

**Output columns**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| All input columns | — | Pass-through | The column structure is unchanged; only rows are filtered |

**Row-count change**:

M → N (M ≥ N) — the output row count is at most the input row count.

## Examples

### Example 1: filter by text length

```json
{
  "id": "n3",
  "type": "where",
  "parameters": {
    "filter": "length(question) > 10"
  }
}
```

Keeps only records whose `question` field is longer than 10.

### Example 2: combined conditions

```json
{
  "id": "n3",
  "type": "where",
  "parameters": {
    "filter": "length(question) > 10 AND output IS NOT NULL"
  }
}
```

Requires both the length condition and the non-null condition.

### Example 3: filter on an AI score

```json
{
  "nodes": [
    { "id": "n1", "type": "project", "parameters": { "question": "a", "output": "c" } },
    { "id": "n2", "type": "llm-call", "parameters": { "prompt": "@eval/prompt.md", "fields": "question,output", "format": "json", "as": "eval" } },
    { "id": "n3", "type": "where", "parameters": { "filter": "json_extract_scalar(eval, '$.score') >= '3'" } }
  ]
}
```

Score with AI first, then drop the low-score records.

### Example 4: filter on document statistics

```json
{
  "nodes": [
    { "id": "n1", "type": "project", "parameters": { "question": "a", "output": "c" } },
    { "id": "n2", "type": "doc-stats", "parameters": { "field": "question" } },
    { "id": "n3", "type": "where", "parameters": { "filter": "json_extract_scalar(__doc_stats, '$.doc_len_char') > '10'" } }
  ]
}
```

Compute document statistics, then drop text that is too short.

## Notes

**Recommended usage**:
- Use it for condition-based row filtering: data-quality screening, LLM-score
  filtering, length and format checks
- It pairs naturally with `extend`, `doc-stats`, and `llm-call`: compute or label
  first, then filter on the result
- All SQL boolean expressions are supported (`AND`, `OR`, `NOT`, comparisons,
  function calls)

**Best practices**:
- Filter an LLM evaluation result: `json_extract_scalar(eval, '$.score') >= 4`
- Filter by text length: `length(question) > 10`
- Compound condition: `length(question) > 5 AND category = 'tech'`

**Edge cases**:

| Case | Behavior |
|------|----------|
| `filter` is missing or empty | Validation fails; a filter condition is mandatory |
| A field referenced by the expression does not exist | Runtime error |
| The expression does not evaluate to a boolean | Runtime error |
| The expression has a syntax error | Runtime error |
| No row satisfies the condition | An empty dataset is emitted; later nodes handle the empty input normally |

## Related nodes

| Node | Relationship |
|------|--------------|
| `extend` | Compute a derived column with `extend`, then filter on it with `where` |
| `doc-stats` | Compute text metrics first, then filter on them with `where` |
| `llm-call` | Evaluate or label with AI first, then filter on the result with `where` |
