# extend (field extension)

> Compute a new column or overwrite an existing one with an expression.

## Function

The `extend` node evaluates an expression on every row and appends the result as a
new column, or overwrites a column of the same name. All built-in SQL functions
are available (string, math, regular-expression, date functions, and so on).

Each record is computed independently and the row count does not change.

**Use cases**:

- Regular-expression extraction: pull specific content out of the raw text (such
  as just the user's question)
- Type conversion: turn a string into a number
- Concatenation: combine several fields into a new derived field
- Data cleaning: strip whitespace, normalize formats

## Node configuration

```json
{
  "id": "node_1",
  "type": "extend",
  "parameters": {
    "<field-name>": "<expression>",
    "<field-name>": "<expression>"
  }
}
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `<field-name>` | String | **Yes** | - | The key is the target column, the value is the expression. At least one entry is required. An existing column is overwritten; a new name is appended |

> **Supported functions**: every built-in SQL function can be used, including but
> not limited to:
> - String functions: `concat`, `substr`, `regexp_extract`, `replace`, `trim`,
>   `lower`, `upper`
> - Math functions: `abs`, `ceil`, `floor`, `round`
> - Type conversion: `cast`, `try_cast`
> - Conditional functions: `if`, `case when`, `coalesce`, `nullif`

## Input and output

**Input requirements**:

- Any columns emitted by the upstream node
- Every field referenced by the expression must exist in the input

**Output columns**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| All input columns | — | Pass-through | Every upstream column is kept |
| Every key in `parameters` | Determined by the expression | Added or overwritten | A column of the same name is overwritten; a new name is appended |

**Row-count change**:

M → N (M = N) — the row count does not change; each row is computed
independently.

## Examples

### Example 1: regular-expression extraction

```json
{
  "id": "n2",
  "type": "extend",
  "parameters": {
    "question": "regexp_extract(question, 'User question: (.*)', 1)"
  }
}
```

Extracts the content after the `User question:` prefix from `question` and
overwrites the original `question` column.

### Example 2: add derived columns

```json
{
  "id": "n2",
  "type": "extend",
  "parameters": {
    "summary": "concat(question, ' - ', output)",
    "q_len": "length(question)"
  }
}
```

Adds the two derived columns `summary` and `q_len`.

### Example 3: pipeline composition

```json
{
  "nodes": [
    {
      "id": "n1", "type": "project",
      "parameters": { "question": "a", "input": "b", "output": "c" }
    },
    {
      "id": "n2", "type": "extend",
      "parameters": { "question": "regexp_extract(question, 'User question: (.*)', 1)" }
    },
    {
      "id": "n3", "type": "where",
      "parameters": { "filter": "length(question) > 10" }
    }
  ]
}
```

Map, transform, filter — the basic composition pattern.

## Notes

**Recommended usage**:
- Use it for derived-field computation: regular-expression extraction, string
  handling, type conversion, JSON field extraction
- Reusing an existing column name overwrites that column, which is handy for
  in-place transformation such as cleaning or formatting
- It pairs naturally with `where`: compute a derived column with `extend`, then
  filter on it with `where`

**Best practices**:
- Expressions support all SQL scalar functions (`regexp_extract`, `length`,
  `json_extract`, and so on)
- One `extend` node can define several derived columns at once; there is no need
  to split it into multiple nodes
- A JSON result produced by an LLM can be unpacked into concrete fields with
  `extend` plus `json_extract`

**Edge cases**:

| Case | Behavior |
|------|----------|
| `parameters` is empty | Validation fails; at least one expression is required |
| A field referenced by the expression does not exist | Runtime error |
| A dot-notation name is used as a column that the source does not actually expose | Parse or runtime error; a quoted dot-notation column only works when the LogStore exposes that flattened name as a real column, as trace LogStores do for `attributes.*`. Otherwise read the raw JSON column with `json_extract_scalar` |
| The expression has a syntax error | Runtime error reporting the parse failure |
| The column name collides with an existing column | The existing column is overwritten (by design, for in-place transformation) |

## Related nodes

| Node | Relationship |
|------|--------------|
| `project` | `extend` is normally used right after `project` to extend fields |
| `where` | A new column computed by `extend` can be used as the `where` condition |
| `llm-call` | A derived field produced by `extend` can be fed into the LLM |
