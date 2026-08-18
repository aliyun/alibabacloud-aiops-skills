# project (field selection)

> Select and rename fields from the upstream data, emitting only the declared
> columns.

## Function

The `project` operator picks the fields it needs from the upstream data and can
rename them to the internal Pipeline field names. The output contains only the
declared columns; undeclared columns are dropped.

As the first operator of a pipeline, `project` declares explicitly which fields the
Pipeline uses and which raw column each one comes from. Every later operator works
on the field names defined by `project`, decoupled from the raw column names.

**Use cases**:

- Extract the needed columns from a raw log or data table and rename them to the
  Pipeline's standard field names
- Drop unneeded columns to reduce the amount of transferred data
- Normalize field-naming differences between data sources

## Syntax

```
| project <new>=<old>, <field>, ...
```

`<new>=<old>` renames the raw column `old` to `new`; `<field>` selects that column
under its original name.

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `<new>=<old>` | Field mapping | At least one | - | Select the raw column `old` and rename it to `new` |
| `<field>` | Field | - | - | Select the column under its original name, equivalent to `field=field` |

## Input and output

**Input**:

- Any columns emitted by the upstream operator; every selected raw column must
  exist

**Output**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| Every declared column | Same as the raw column | Mapping | Only the declared columns are emitted; undeclared columns are dropped |

**Input-to-output relationship**:

M:N (M = N) — the row count does not change; only columns are selected and renamed.

## Examples

### Example 1: declare the schema at the start of the pipeline

```
* | project question=a, input=b, output=c
```

Maps the raw columns `a`, `b`, and `c` to the standard Pipeline fields `question`,
`input`, and `output`.

### Example 2: select columns and continue processing

```
* | project question,input,output
  | dedup-exact -field=question
```

Selects the three columns under their original names, then dedups on `question`.

---

> **Everything below this line is the internal implementation spec, aimed at the
> development and engineering teams. Hide it when publishing user documentation.**

## Design notes

- **Native SLS SPL instruction**: `project` is a built-in SPL capability with no CTE
  wrapper and no remote-function dependency, so the API translation layer only
  validates the parameters and maps the syntax. For syntax details see the
  [SLS SPL documentation](https://help.aliyun.com/zh/sls/field-operation-instructions).
- **Rename workaround**: the translation layer does not emit `project new=old`
  directly (there are low-level compatibility problems when the mapped value is a
  non-varchar intermediate field). When a rename exists (`new != old`) it expands
  into two stages: first `extend new1=old1, new2=old2` (the renamed entries only),
  then `project new1, new2, ...` (every declared field). Without a rename it emits a
  single `project field1, field2`. See `ProjectNode._build_workaround_parts()`
  (Python) or `buildWorkaroundParts()` (Go).
- **No output wrapper**: the `project` node overrides `to_spl_parts()` to skip the
  API layer's shared `output` parameter wrapping (it is a projection itself) and does
  not introduce `_get_required_fields()`.

## SQL implementation template

The native instruction passes through; there is no CTE template:

```
# without a rename
project {{field1}}, {{field2}}, ...

# with a rename (two-stage workaround)
extend {{new1}}={{old1}}, {{new2}}={{old2}} | project {{new1}}, {{new2}}, ...
```

## Dependent functions

None (only the native SLS SPL `project` and `extend` instructions).

## Edge cases

| Case | Handling |
|------|----------|
| The field mapping is empty | Parameter validation fails; at least one field selection is required |
| A field name or mapped value is an empty string or not a string | Parameter validation fails |
| The raw column referenced by a mapping does not exist | Runtime error reporting the missing field |
| Several new columns map to the same raw column | Allowed; produces multiple columns with identical content |
| The input is empty | An empty result set is returned normally |
