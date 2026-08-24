# where (conditional filtering)

> Filter rows by a boolean expression, keeping only the records that satisfy it.

## Function

The `where` operator evaluates a condition on every row and keeps only the rows
whose expression evaluates to `true`, discarding the rest. The column structure is
unchanged and no derived columns are added.

All SQL boolean expressions and comparison operators are supported, and built-in
functions can be combined into complex conditions.

**Use cases**:

- Filter out low-quality data (text that is too short, empty fields)
- Select a specific category of data by business condition
- Filter on an upstream computation result (for example records whose AI score is
  below a threshold)

## Syntax

```
| where <boolean-expression>
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `<boolean-expression>` | Expression | Yes | - | The filter condition; must evaluate to a boolean. `AND`/`OR`/`NOT` combinations are supported |

> **Supported operators**: `=`, `!=`, `>`, `<`, `>=`, `<=`, `LIKE`, `IN`,
> `IS NULL`, `IS NOT NULL`, `BETWEEN`, `AND`, `OR`, `NOT`

## Input and output

**Input**:

- Any columns emitted by the upstream operator
- Every field referenced by the expression must exist in the input

**Output**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| All input columns | - | Input | The column structure is unchanged; only rows are filtered |

**Input-to-output relationship**:

M:N (M >= N) - only rows where the expression is `true` survive, so the output row
count is at most the input row count.

## Examples

### Example 1: filter by text length

```
* | project question,input,output
  | where length(question) > 10
```

Keeps only records whose `question` field is longer than 10.

### Example 2: combined conditions

```
* | project question,input,output
  | where length(question) > 10 AND output IS NOT NULL
```

### Example 3: filter on an AI score

```
* | project question=a, output=c
  | llm-call -prompt='@eval/prompt.md' -fields=question,output -format=json as eval
  | where json_extract_long(eval, '$.score') >= 3
```

Score with AI first, then drop the low-score records.

---

> **Everything below this line is the internal implementation spec, aimed at the
> development and engineering teams. Hide it when publishing user documentation.**

## Design notes

- **Native SLS SPL instruction**: `where` is a built-in SPL capability with no CTE
  wrapper and no remote-function dependency. The API translation layer only
  validates the parameter (`filter` is mandatory and must not be blank) and passes
  the condition straight through as `where <filter>`. For syntax details see the
  [SLS SPL documentation](https://help.aliyun.com/zh/sls/field-operation-instructions).
- **Unknown parameters are rejected**: the translation layer uses
  `KNOWN_KEYS = {"filter"}` to reject anything other than `filter`.
- It pairs naturally with `extend`, `doc-stats`, and `llm-call`: compute or label
  first, then filter on the result.

## SQL implementation template

The native instruction passes through; there is no CTE template:

```
where {{filter}}
```

## Dependent functions

None (only the native SLS SPL `where` instruction).

## Edge cases

| Case | Handling |
|------|----------|
| The filter condition is missing or blank | Parameter validation fails; a filter condition is mandatory |
| A field referenced by the expression does not exist | Runtime error |
| The expression does not evaluate to a boolean | Runtime error |
| The expression has a syntax error | Runtime error |
| No row satisfies the condition | An empty dataset is emitted; later operators handle the empty input normally |
