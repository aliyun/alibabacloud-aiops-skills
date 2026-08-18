# project (field selection)

> Select and rename fields from the raw data, declaring the Pipeline input schema.

## Function

`project` is the first node of a Pipeline. It picks the fields you need out of the
raw data and can rename them to the internal field names used across the
Pipeline.

Through `project` the user explicitly declares which fields the Pipeline uses and
which raw column each one comes from. Every later node works on the field names
defined by `project`, decoupled from the raw column names.

**Use cases**:

- Extract the needed columns from a raw log or data table and rename them to the
  Pipeline's standard field names
- Drop unneeded columns to reduce the amount of transferred data
- Normalize field-naming differences between data sources

## Node configuration

```json
{
  "id": "node_1",
  "type": "project",
  "parameters": {
    "<new-field-name>": "<raw-field-name>",
    "<new-field-name>": "<raw-field-name>"
  }
}
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `<new-field-name>` | String | **Yes** | - | The key is the mapped field name, the value is the field name in the raw data. At least one mapping is required |

> **Note**: `parameters` is a dynamic key-value map. Each key is a field name used
> in the Pipeline and the matching value is the field name in the raw data.

> **The value is a column name, not an expression**: do not point it at a
> dot-notation subfield such as `"input": "eval_info.input"`. That fails with
> `SPLSyntaxError: bad extend expression`, with or without inner quoting, because a
> renaming mapping is translated into an assignment (see "Recommended usage") and
> the dot name does not parse in an expression position. Project the raw JSON
> column instead, then extract it in a later `extend` with
> `json_extract_scalar(eval_info, '$.input')`.

## Input and output

**Input requirements**:

- A raw data source (a Logstore or another source)
- Every raw field referenced by a value must exist in the source

**Output columns**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| Every key in `parameters` | Same as the raw field type | Mapping | Projected from the raw field and renamed |

**Row-count change**:

M → N (M = N) — the row count does not change; only columns are selected and
renamed.

## Examples

### Example 1: simple field selection

```json
{
  "id": "n1",
  "type": "project",
  "parameters": {
    "question": "question",
    "answer": "answer"
  }
}
```

The raw `question` and `answer` fields pass through under their original names.

### Example 2: field renaming

```json
{
  "id": "n1",
  "type": "project",
  "parameters": {
    "question": "user_query",
    "answer": "bot_response",
    "model": "model_name"
  }
}
```

The raw `user_query` column becomes `question`, `bot_response` becomes `answer`,
and `model_name` becomes `model`.

### Example 3: pipeline composition

```json
{
  "nodes": [
    {
      "id": "n1", "type": "project",
      "parameters": { "question": "a", "input": "b", "output": "c" }
    },
    {
      "id": "n2", "type": "dedup-exact",
      "parameters": { "field": "question" }
    }
  ]
}
```

Fields are mapped first, then the later node dedups on the mapped `question`
field.

## Notes

**Recommended usage**:
- `project` is the pipeline's first node and defines the schema the downstream
  nodes need (field selection and renaming)
- Select only the columns actually needed downstream to reduce the data the later
  nodes scan
- Rename a field with `"new-name": "old-name"` to normalize the column naming
- The translation layer rewrites for compatibility automatically: `"a":"a"`
  becomes `project a`; `"a":"b"` becomes `extend a=b | project a`

**Best practices**:
- Use `project` at the start of the pipeline to state the input schema, which
  makes the pipeline easier to read and maintain
- Follow it with `extend` for derived-field computation and then `where` for
  conditional filtering
- When the mapped value is an intermediate temporary field that may not be
  varchar, rely on the automatic rewrite path above instead of a direct
  `project a=b`, which can hit low-level compatibility problems

**Edge cases**:

| Case | Behavior |
|------|----------|
| `parameters` is empty | Validation fails; at least one field selection is required |
| The referenced raw field does not exist | Runtime error reporting the missing field |
| The value is a dot-notation subfield (`eval_info.input`) | `SPLSyntaxError: bad extend expression`; project the raw JSON column and extract with `json_extract_scalar` in a later `extend` |
| Several keys map to the same raw field | Allowed; produces multiple columns with identical content |

## Related nodes

| Node | Relationship |
|------|--------------|
| `extend` | After `project` selects the fields, `extend` can compute further transformations |
| `where` | After `project` defines the schema, `where` can filter rows by condition |
