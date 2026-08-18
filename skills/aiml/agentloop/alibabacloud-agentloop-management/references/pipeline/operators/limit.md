# limit (row limit)

> Cap the number of output records; equivalent to SQL `LIMIT`.

## Function

The `limit` operator truncates the upstream result directly, letting only the first
`n` records flow on. It performs no field computation and adds no derived columns,
which makes it one of the lightest volume-reduction operators.

**Use cases**:

- Preview query results to shorten debugging and validation cycles
- Impose a hard cap before an expensive operator
- Take a handful of samples for rule validation or troubleshooting

## Syntax

```
| limit <count>
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `<count>` | Integer | Yes | - | Upper bound on output records; must be a positive integer |

## Input and output

**Input**:

- Any columns emitted by the upstream operator

**Output**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| All input columns | — | Input | Every upstream column passes through; only the row count is limited |

**Input-to-output relationship**:

M:N (M ≥ N) — `N = min(M, count)`.

## Examples

### Example 1: limit the output to the first 5 rows

```
* | project question,input,output
  | limit 5
```

### Example 2: dedup, then cap

```
* | project question,input,output
  | dedup-exact -field=question
  | limit 100
```

---

> **Everything below this line is the internal implementation spec, aimed at the
> development and engineering teams. Hide it when publishing user documentation.**

## Design notes

- `limit` is a built-in SPL capability, so the API translation layer only validates
  the parameter and maps the syntax (`n -> limit n`).
- This operator does not support the `output` wrapper and does not introduce
  `_get_required_fields()`.
- The preview API can use `limit` as a default tail node to avoid an unbounded scan.

## SQL implementation template

```sql
SELECT * FROM ##sourceTable##
LIMIT {{count}}
```

## Template variables

| Template variable | Parameter | Default | Description |
|-------------------|-----------|---------|-------------|
| `{{count}}` | `<count>` | - | Upper bound on output records |
| `##sourceTable##` | Resolved by the engine | - | The upstream CTE name or base query table |

## Dependent functions

None (only the SQL `LIMIT` syntax).

## Edge cases

| Case | Handling |
|------|----------|
| `<count>` is missing | Parameter validation fails |
| `<count>` is not an integer | Parameter validation fails |
| `<count>` ≤ 0 | Parameter validation fails |
| The input is empty | An empty result set is returned normally |
