# sample (sampling)

> Randomly sample a given proportion or number of records, either globally or within
> groups.

## Function

Randomly samples the input data in one of two modes:

1. **Global sampling**: randomly samples a given proportion (`-ratio`) or number
   (`-n`) of records from the data as a whole
2. **Grouped sampling**: groups the data by the given columns (`by`) and independently
   samples a given proportion (`-ratio`) or number (`-n`) of records within each group

It is commonly combined with the upstream `semantic-cluster` operator to achieve
"diversity sampling" — cluster first, then sample per cluster, so downsampling keeps
semantic diversity.

**Use cases**:

- Fast downsampling of large-scale data
- Combined with `semantic-cluster` for representative sampling with a diversity
  guarantee
- Grouped sampling: even sampling across category, label, or cluster ID
- Controlling the data volume before AI processing (reducing LLM call cost)

## Syntax

```
| sample [-ratio=<ratio> | -n=<count>] [by <group_columns>]
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `-ratio` | Double | One of the two | - | Sampling rate in (0, 1]; `0.1` samples 10%. Mutually exclusive with `-n` |
| `-n` | Integer | One of the two | - | Number of rows to sample; `10` samples 10 rows. Mutually exclusive with `-ratio` |
| `by` | FieldList | No | - | Grouping columns, comma-separated (an instruction primitive, without the `-` prefix). Enables grouped sampling, with independent sampling inside each group |

> **Choosing between `-ratio` and `-n`**:
>
> | Intent | Recommended parameter | Description |
> |--------|----------------------|-------------|
> | "Give me 10% of the data" | `-ratio=0.1` | The output size scales with the input size |
> | "Give me 100 rows" | `-n=100` | A fixed output size, independent of the input size |
> | "One row per group" | `-n=1 by __cluster_id` | Diversity sampling together with `semantic-cluster` |
> | "Keep 20% of each group" | `-ratio=0.2 by category` | Even sampling per category |

## Input and output

**Input**:

- Any columns emitted by the upstream operator
- When `by` is used, the named grouping columns must all be present

**Output**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| All input columns | — | Input | Every upstream column passes through |

> This operator adds no derived columns; it only filters rows.

**Input-to-output relationship**:

M:N (M ≥ N) — after random sampling the output row count is less than or equal to the
input row count.

Exact output size:
- Global with `-ratio`: N = ceil(M × ratio)
- Global with `-n`: N = min(n, M)
- Grouped with `-n`: N = Σ min(n, rows in group)
- Grouped with `-ratio`: N = Σ ceil(rows in group × ratio)

## Effect preview

**Before** (6 rows):

| question | output | __cluster_id |
|----------|--------|-------------|
| What is machine learning? | Machine learning is… | 0 |
| What types of machine learning are there? | Supervised / unsupervised / reinforcement… | 0 |
| How do I learn Python? | Start with the official tutorial… | 1 |
| Which Python libraries are available? | NumPy, Pandas… | 1 |
| What is deep learning? | Deep learning is… | 2 |
| What is a neural network? | A neural network has several layers… | 2 |

**After** (3 rows) — `| sample -n=1 by __cluster_id`:

| question | output | __cluster_id |
|----------|--------|-------------|
| What types of machine learning are there? | Supervised / unsupervised / reinforcement… | 0 |
| How do I learn Python? | Start with the official tutorial… | 1 |
| What is deep learning? | Deep learning is… | 2 |

> One random row per cluster, so 6 rows become 3. The operator adds no derived
> columns; it only filters rows. Because the selection is random, each run may return
> a different result.

## Examples

### Example 1: global random sampling at 10%

```
* | project question,input,output
  | sample -ratio=0.1
```

Randomly takes 10% of the data as a whole.

### Example 2: global sampling of a fixed number of rows

```
* | project question,input,output
  | sample -n=100
```

Randomly takes 100 rows.

### Example 3: clustering plus grouped sampling (diversity sampling, recommended)

```
* | project question,input,output,__dedup_emb
  | semantic-cluster -field=__dedup_emb -n=100
  | sample -n=1 by __cluster_id
```

Clusters into 100 clusters and takes one row per cluster, producing 100 semantically
diverse representative samples.

### Example 4: sampling grouped by category

```
* | project question,input,output,category
  | sample -ratio=0.2 by category
```

Groups by the `category` column and randomly keeps 20% of each group.

### Example 5: multi-dimensional grouped sampling

```
* | project question,input,output,category,difficulty
  | sample -n=10 by category,difficulty
```

Groups by the `(category, difficulty)` combination and takes 10 rows per group.

### Example 6: full Pipeline

```
* | project question,input,output
  | dedup-exact -field=question
  | dedup-fuzzy -field=question -threshold='3'
  | dedup-semantic -field=question -threshold='0.1'
  | semantic-cluster -field=__dedup_emb -n=100
  | sample -n=1 by __cluster_id
  | llm-call -prompt='@eval/prompt.md' -fields=question,output as eval
```

Three-stage deduplication → clustering → grouped sampling → AI evaluation.

---

> **Everything below this line is the internal implementation spec, aimed at the
> development and engineering teams. Hide it when publishing user documentation.**

## Design notes

- **Relationship with `semantic-cluster`**: `sample` handles filtering and
  downsampling (M:N) and `semantic-cluster` handles group labeling (1:1). The two
  compose orthogonally to produce "diversity sampling". Splitting them keeps each
  operator atomic: `sample` can be used alone for random sampling and
  `semantic-cluster` alone for analysis.
- **`-ratio` and `-n` are mutually exclusive**: they offer different sampling modes.
  `-ratio` samples proportionally (the output scales with the input) and `-n` samples a
  fixed quantity. Specifying both is rejected to avoid ambiguity.
- **Randomness**: sampling uses `rand()`, so each run may return a different result.
- **No remote-function dependency**: every computation uses built-in SQL functions
  (`row_number`, `rand`, `count`, `ceil`), so `enable_remote_functions` is not
  required.
- **Stratified-sampling note for the future**: `sample` is currently positioned as
  "uniform random sampling", where `-ratio` applies the same rate to all data or all
  groups. A possible future requirement is applying different sampling rates per
  stratum based on a weight column (for example a frequency column `cnt`) —
  downsampling frequent strata and oversampling rare ones — so that each stratum
  represents the population proportionally. Expressing "bucketing rules plus
  differentiated rates" as parameters is fairly complex, so it is better implemented as
  a separate operator (such as `sample-stratified`) or by precomputing bucket labels
  upstream with `eval` and composing them in the pipeline, rather than layered into
  this operator.

## SQL implementation template

### Global sampling with `-ratio`

```sql
WITH
_sp_data AS (
    SELECT 
        row_number() OVER (ORDER BY rand()) AS __sp_rn,
        count(*) OVER () AS __sp_total
        ##otherColumns##
    FROM ##sourceTable##
)
SELECT * FROM _sp_data
WHERE __sp_rn <= cast(ceil(__sp_total * {{ratio}}) as bigint)
```

### Global sampling with `-n`

```sql
WITH
_sp_data AS (
    SELECT 
        row_number() OVER (ORDER BY rand()) AS __sp_rn
        ##otherColumns##
    FROM ##sourceTable##
)
SELECT * FROM _sp_data
WHERE __sp_rn <= {{n}}
```

### Grouped sampling with `-n` (used together with `semantic-cluster`)

```sql
WITH
_sp_data AS (
    SELECT 
        row_number() OVER (PARTITION BY {{by}} ORDER BY rand()) AS __sp_rn
        ##otherColumns##
    FROM ##sourceTable##
)
SELECT * FROM _sp_data
WHERE __sp_rn <= {{n}}
```

### Grouped sampling with `-ratio`

```sql
WITH
_sp_grouped AS (
    SELECT 
        row_number() OVER (PARTITION BY {{by}} ORDER BY rand()) AS __sp_rn,
        count(*) OVER (PARTITION BY {{by}}) AS __sp_group_total
        ##otherColumns##
    FROM ##sourceTable##
)
SELECT * FROM _sp_grouped
WHERE __sp_rn <= cast(ceil(__sp_group_total * {{ratio}}) as bigint)
```

## Template variables

| Template variable | Parameter | Default | Description |
|-------------------|-----------|---------|-------------|
| `{{ratio}}` | `-ratio` | - | Sampling rate (mutually exclusive with `{{n}}`) |
| `{{n}}` | `-n` | - | Number of rows to sample (mutually exclusive with `{{ratio}}`) |
| `{{by}}` | `by` | - | Grouping column names (comma-separated for several columns, such as `col1, col2`). When absent, the global-mode template is used |
| `##sourceTable##` | Resolved by the engine | - | The upstream CTE name or base query table |
| `##otherColumns##` | Derived by the engine | - | Pass-through macro for non-derived columns; commas and duplicate column names are handled automatically afterwards |

## Dependent functions

| Signature | Used by | Description |
|-----------|---------|-------------|
| `rand() → double` | All modes | Generates a random number in [0, 1), used by `ORDER BY rand()` for random ordering (built-in SQL) |
| `row_number() OVER ([PARTITION BY col] ORDER BY rand()) → bigint` | All modes | Window function producing a randomly ordered row number (built-in SQL) |
| `count(*) OVER ([PARTITION BY col]) → bigint` | `-ratio` modes | Window function computing the total or per-group row count (built-in SQL) |

## Edge cases

| Case | Handling |
|------|----------|
| Neither `-ratio` nor `-n` is given | The engine raises a parameter-validation error asking for at least one of them |
| Both `-ratio` and `-n` are given | The engine raises a parameter-validation error noting that they are mutually exclusive |
| `-ratio` falls outside (0, 1] | The engine raises a parameter-validation error |
| `-n` ≤ 0 | The engine raises a parameter-validation error |
| A column named by `by` does not exist | The engine raises a parameter-validation error |
| The input is empty (0 rows) | An empty result set is returned normally |
| `-n` exceeds the row count (global) | All rows are returned |
| `-n` exceeds a group's row count (grouped) | That group returns all of its rows |
| `-ratio=1.0` | All rows are returned (equivalent to no sampling) |
