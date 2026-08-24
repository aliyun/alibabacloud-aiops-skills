# extend (field extension)

> Compute a new column or overwrite an existing one with an expression.

## Function

The `extend` operator evaluates an expression on every row and appends the result
as a new column; when the column name matches an existing column, the original is
overwritten. All built-in SQL functions are available (string, math,
regular-expression, date functions, and so on).

Each record is computed independently and the row count does not change.

**Use cases**:

- Regular-expression extraction: pull specific content out of the raw text (such
  as just the user's question)
- Type conversion: turn a string into a number
- Concatenation: combine several fields into a new derived field
- Data cleaning: strip whitespace, normalize formats

## Syntax

```
| extend <col>=<expr>, <col>=<expr>, ...
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `<col>=<expr>` | Field=Expression | At least one | - | `col` is the target column and `expr` is the expression. An existing column is overwritten; a new name is appended |

> **Supported functions**: every built-in SQL function can be used, including but
> not limited to:
> - String functions: `concat`, `substr`, `regexp_extract`, `replace`, `trim`,
>   `lower`, `upper`
> - Math functions: `abs`, `ceil`, `floor`, `round`
> - Type conversion: `cast`, `try_cast`
> - Conditional functions: `if`, `case when`, `coalesce`, `nullif`

## Input and output

**Input**:

- Any columns emitted by the upstream operator
- Every field referenced by the expression must exist in the input

**Output**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| All input columns | - | Input | Every upstream column passes through |
| Every declared target column | Determined by the expression | Added or overwritten | A column of the same name is overwritten; a new name is appended |

**Input-to-output relationship**:

M:N (M = N) - the row count does not change and each row is computed
independently; the column count stays the same or grows.

## Examples

### Example 1: regular-expression extraction (in-place overwrite)

```
* | project question=a
  | extend question=regexp_extract(question, 'User question: (.*)', 1)
```

Extracts the content after the `User question:` prefix from `question` and
overwrites the original `question` column.

### Example 2: add derived columns

```
* | project question,output
  | extend summary=concat(question, ' - ', output), q_len=length(question)
```

A single `extend` adds both the `summary` and `q_len` derived columns.

### Example 3: pipeline composition

```
* | project question=a, input=b, output=c
  | extend question=regexp_extract(question, 'User question: (.*)', 1)
  | where length(question) > 10
```

Map, transform, filter - the basic composition pattern.

---

> **Everything below this line is the internal implementation spec, aimed at the
> development and engineering teams. Hide it when publishing user documentation.**

## Design notes

- **Native SLS SPL instruction**: `extend` is a built-in SPL capability with no CTE
  wrapper and no remote-function dependency. The API translation layer only
  validates the parameters (at least one non-empty column/expression pair) and
  concatenates them into `extend col1=expr1, col2=expr2`. For syntax details see the
  [SLS SPL documentation](https://help.aliyun.com/zh/sls/field-operation-instructions).
- **Same-name overwrite semantics**: a target column that matches an existing column
  overwrites it. This is by design, for in-place transformation (cleaning,
  formatting).
- **Relationship with project**: when `project` includes a rename, the translation
  layer's workaround emits a leading `extend new=old` segment automatically (see the
  design notes in `project.md`).

## SQL implementation template

The native instruction passes through; there is no CTE template:

```
extend {{col1}}={{expr1}}, {{col2}}={{expr2}}, ...
```

## Dependent functions

None (only the native SLS SPL `extend` instruction).

## Edge cases

| Case | Handling |
|------|----------|
| The expression set is empty | Parameter validation fails; at least one expression is required |
| A column name or expression is an empty string or not a string | Parameter validation fails |
| A field referenced by the expression does not exist | Runtime error |
| The expression has a syntax error | Runtime error reporting the parse failure |
| The column name collides with an existing column | The existing column is overwritten (by design, for in-place transformation) |
| The input is empty | An empty result set is returned normally |
