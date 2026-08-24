# SPL operator definition document template

> **How to use**: copy this template, replace the `{...}` placeholders, and delete this
> guidance block.
>
> **This document is the implementation**, and it serves three audiences at once:
> - **Development team**: defines and maintains the operator's functional boundary,
>   parameter semantics, and roadmap
> - **Engineering team**: implements the operator from the SQL template and variable
>   mapping (function registration, parameter parsing, SQL rendering, execution)
> - **End users**: learn what the operator does, its syntax, and its best practices
>   (everything above the divider is the user documentation)

---

<!-- ============================== -->
<!-- User documentation below (published publicly) -->
<!-- ============================== -->

# {operator-name} ({display name})

> {One-sentence description of what it does, under 30 words}

## Function

{2 to 3 paragraphs:}
{1. What problem this operator solves}
{2. The core principle in one sentence}

**Use cases**:

- {Case 1}
- {Case 2}
- {Case 3}

## Syntax

```
| {operator-name} -field=<column> [{optional-params}] [as <name>]
```

> **Instruction primitives**: `as` and `by` are SPL instruction primitives (similar to
> SQL keywords). They carry **no `-` prefix**, are separated from their value by a space
> (not `=`), and **must come after every `-` parameter (at the very end)**.
> Examples: `| llm-call -prompt='...' -fields=question as eval`,
> `| sample -n=10 by category`

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `-field` | Field | **Yes** | - | {Description of the primary operand field} |
| {`-param`} | {Type} | {Yes/No} | {default} | {Description} |
| `as` | Field | No | {default} | {Output column name - an instruction primitive, without the `-` prefix} |

> {Guidance on parameter usage or selection, when threshold-style parameters exist}
> **Parameter categories**: names with a `-` prefix are ordinary parameters
> (`-key=value`); names without it are instruction primitives (`key value`). The current
> instruction primitives are `as` (output column naming) and `by` (grouping columns).

## Input and output

**Input**:

- {Where the data comes from, the required fields, and their type requirements}

**Output**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| All input columns | - | Input | Every upstream column passes through |
| `__{prefix}_{col}` | {type} | Derived | {Semantic description} |

> **`Source` enum values**: `Input` (an upstream data column passing through) and
> `Derived` (a new column the operator produces, always appended). Narrow the output by
> appending a `project` operator later in the pipeline.

**Input-to-output relationship**:

{M:N constraint} - {one sentence describing how the row count changes}.

> Common patterns: `M:N (M >= N)` for dedup/filter ; `M:N (M = N)` for 1:1
> transformation/labeling ; `M:N (M <= N)` for expansion/augmentation

## Effect preview

**Before** ({N} rows):

| {col1} | {col2} | {col3} |
|--------|--------|--------|
| {sample data row 1} |
| {sample data row 2} |
| {sample data row 3} |

**After** ({M} rows) - `| {operator-name} -field=<column> {params}`:

| {col1} | {col2} | {col3} | {derived column} |
|--------|--------|--------|------------------|
| {result data row 1} |
| {result data row 2} |

> {One sentence summarizing the transformation: row-count change, meaning of the new
> columns, typical use}

## Examples

### Example 1: {simplest usage}

```
* | {operator-name} -field=<column>
```

{One sentence describing the effect}

### Example 2: {typical usage}

```
* | {operator-name} -field=<column> -{param}=<value>
```

### Example 3: {advanced usage / pipeline composition}

```
* | {operator-A} ...
  | {operator-name} -field=<column> -{param}=<value>
  | {operator-B} ...
```

---

<!-- ============================== -->
<!-- Internal implementation spec below (not published) -->
<!-- ============================== -->

> **Everything below this line is the internal implementation spec, aimed at the
> development and engineering teams. Hide it when publishing user documentation.**

## Design notes

{Design decisions, a detailed explanation of the algorithm, the relationship with
related operators, the roadmap, and so on}

## SQL implementation template

> **Conventions**:
> - Each template is **one complete SQL statement** (WITH ... SELECT) that can run on
>   its own
> - A template that uses remote functions (`prompt_simhash`, `embedding`, and so on)
>   must declare `set session enable_remote_functions = true;` before the WITH clause
> - `##sourceTable##` is the upstream data-source placeholder, which the execution
>   engine resolves to the upstream CTE name or the base query table
> - `##otherColumns##` is the pass-through macro for non-derived columns and comes
>   **after** the derived columns. The engine derives it from the upstream and downstream
>   columns, handling comma joining and duplicate column names (when the upstream has a
>   column of the same name, the current operator's derived column wins)
> - Name CTEs with the operator prefix (`_exact_`, `_fuzzy_`, and so on) to avoid name
>   collisions when operators are chained
> - SELECT layout in the first CTE: **derived columns first, `##otherColumns##` last**,
>   never `SELECT *`. This resolves column-name collisions when the same operator appears
>   several times in one pipeline

### {Mode A name} ({trigger condition})

```sql
set session enable_remote_functions = true;
WITH
-- Step 1: {description of the processing step}
_{prefix}_step1 AS (
    SELECT 
        {function}({{field}}) AS __{prefix}_{ext_col1},
        {function}({{field}}) AS __{prefix}_{ext_col2}
        ##otherColumns##
    FROM ##sourceTable##
    WHERE {{field}} IS NOT NULL
),
-- Step 2: {description of the processing step}
_{prefix}_step2 AS (
    ...
)
-- Output
SELECT * FROM _{prefix}_step2
```

### {Mode B name} ({trigger condition})

```sql
...
```

## Template variables

| Template variable | Parameter | Default | Description |
|-------------------|-----------|---------|-------------|
| `{{field}}` | `-field` | - | The primary operand field name |
| `##sourceTable##` | Resolved by the engine | - | The upstream data source: the base query table for the first operator, the previous operator's output CTE afterwards |
| `##otherColumns##` | Derived by the engine | - | Pass-through macro for non-derived columns; commas and duplicate column names are handled automatically afterwards |
| {`{{var}}`} | {`-param`} | {default} | {Description} |

## Dependent functions

| Signature | Description |
|-----------|-------------|
| `{function_name}({args})` | {What it does} |

## Edge cases

| Case | Handling |
|------|----------|
| The `-field` column does not exist | {Handling} |
| The `-field` value is NULL | {Handling} |
| The input is empty | {Handling} |
| {Other edge case} | {Handling} |
