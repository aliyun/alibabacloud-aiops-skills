# {type} ({display name})

> {One-sentence function description, at most about 15 words}

## Function

{2-3 paragraphs:}
{1. What problem this node solves}
{2. Its core capability in one sentence}

**Use cases**:

- {Case 1}
- {Case 2}

## Node configuration

```json
{
  "id": "node_1",
  "type": "{type}",
  "parameters": {
    ...
  }
}
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `{param}` | {Type} | {Yes/No} | {default} | {description} |
| `output` | String | No | `*` | Output columns of the node, comma separated. `*` (default) keeps every column including derived ones. When set, only the listed columns are emitted |

> **Note**: nodes that do not support `output` (such as project, extend, and
> where) omit the `output` row.
> {Parameter guidance or selection advice, if any}

## Design principle: the `output` parameter

### Orthogonal SPL, cohesive API

- **SPL layer**: capabilities stay orthogonal. The operator itself has no
  `-output` parameter; output-column selection is done by a separate `project`
  operator.
- **API layer**: the user experience is cohesive. Every node exposes an `output`
  parameter so the user can control the output columns on a single operator.

### API to SPL translation rules

- When `output` is unset or `*`: no extra transformation from API to SPL.
- When `output` names a concrete field list: the API-to-SPL translation inserts a
  `project` before and after the operator.
  - **Leading project**: a performance optimization. It merges the fields the
    operator needs with the `output` fields (deduplicated) so only the necessary
    columns are scanned, reducing columnar IO.
  - **Trailing project**: the final output projection.

**Example** (`dedup-exact` with `field=question` and
`output=question,answer,model`):

```
| project question,answer,model
| dedup-exact -field=question
| project question,answer,model
```

> **Note**: the leading project must merge the operator's mandatory field columns
> with the output columns and deduplicate them.

### `output` semantics

- **Old semantics**: a selection projection over the raw input columns.
- **New semantics**: control over the node's **final output columns** (including
  operator-derived columns). `*` (the default) passes every column through.

## Input and output

**Input requirements**:

- {Data source, mandatory fields, field-type requirements}

**Output columns**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| Columns controlled by `output` | - | Pass-through / added | `output=*` keeps every column (including derived ones); when set, only the listed columns are emitted |
| `{derived column}` | {type} | Added | {semantics} |

> **`output` semantics**: controls the node's final output columns, so derived
> columns can be kept or excluded selectively. `*` passes every column through.

**Row-count change**:

{Describe the M -> N relationship}

## Effect preview

**Before** ({N} rows):

| {col1} | {col2} | {col3} |
|--------|--------|--------|
| {sample row 1} |
| {sample row 2} |
| {sample row 3} |

**After** ({M} rows) - `{parameter description}`:

| {col1} | {col2} | {col3} | {derived column} |
|--------|--------|--------|------------------|
| {result row 1} |
| {result row 2} |

> {One sentence summarizing the transformation: row-count change, meaning of the
> new columns, typical use}

## Examples

### Example 1: {minimal usage}

```json
{
  "id": "node_1",
  "type": "{type}",
  "parameters": {
    ...
  }
}
```

{One sentence describing the effect}

### Example 2: {typical usage}

```json
{
  "id": "node_1",
  "type": "{type}",
  "parameters": {
    ...
  }
}
```

### Example 3: {pipeline composition}

```json
{
  "nodes": [
    { "id": "n1", "type": "...", "parameters": { ... } },
    { "id": "n2", "type": "{type}", "parameters": { ... } }
  ]
}
```

## Notes

**Recommended usage**:
- {Where it belongs in the pipeline and what it pairs with}
- {Typical composition patterns with other operators}

**Best practices**:
- {Parameter selection advice}
- {Performance and cost optimization advice}
- {Common techniques}

**Edge cases**:

| Case | Behavior |
|------|----------|
| {edge case} | {handling strategy} |

## Related nodes

| Node | Relationship |
|------|--------------|
| `{related-type}` | {how they work together} |
