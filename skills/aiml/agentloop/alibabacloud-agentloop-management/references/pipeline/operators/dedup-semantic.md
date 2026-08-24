# dedup-semantic (semantic deduplication)

> Use embedding-vector distance to remove records whose meaning is the same even
> though the wording differs.

## Function

Uses an ML model to generate embedding vectors for the given field and judges
semantic similarity by the distance between vectors. Records whose distance falls
within the threshold are treated as semantic duplicates, and a representative record
is kept.

Unlike literal matching (exact or fuzzy deduplication), semantic deduplication can
recognize text that is worded differently but means the same thing (for example
"What is the weather like today?" versus "How is the climate today?"), which makes it
the fine-grained deduplication stage for building high-quality datasets.

**Use cases**:

- Deduplicating text that is worded differently but semantically identical
- Cross-language semantic deduplication in multilingual scenarios
- Fine-grained deduplication of high-quality AI training datasets
- Usually the final deduplication stage, after exact and fuzzy deduplication

## Syntax

```
| dedup-semantic -field=<column> [-threshold=<distance>] [-model=<embedding_model>] [-global -workspace=<workspace> -dataset=<dataset> [-column_name=<name>]]
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `-field` | Field | **Yes** | - | Name of the field to deduplicate on; must be a text column |
| `-threshold` | String | No | `'0.1'` | Vector-distance threshold (0 to 1); the smaller, the stricter |
| `-model` | String | No | `'embedding-multilang-v3'` | Embedding model name |
| `-global` | Bool | No | `false` | Whether to enable global deduplication (across batches, incrementally against a Dataset) |
| `-workspace` | String | Conditionally required | - | Workspace holding the Dataset (required when `-global` is set) |
| `-dataset` | String | Conditionally required | - | Dataset name (required when `-global` is set) |
| `-column_name` | String | No | Same as `-field` | The Dataset column used for semantic deduplication (optional when `-global` is set) |

> **Threshold guidance**:
>
> | Threshold | Strictness | Description |
> |-----------|-----------|-------------|
> | `0.05` | Very strict | Filters out only near-synonymous wording |
> | **`0.1`** | **Recommended default** | Suits most semantic-deduplication scenarios |
> | `0.15~0.2` | Looser | May drop related but non-synonymous text; use with care |
> | `0.3+` | Too loose | Not recommended; likely to drop a lot of valid data |

## Input and output

**Input**:

- Any columns emitted by the upstream operator
- The field named by `-field` must be present and be a text column (varchar)
- In global mode, if `-column_name` is given, that column must exist in the Dataset,
  be a text column (varchar), and have a vector index enabled

**Output**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| All input columns | - | Input | Every upstream column passes through |
| `__dedup_emb` | array(double) | Derived | The text embedding vector (downstream operators such as clustering and sampling can reuse it directly) |
| `__dedup_rid` | bigint | Derived | In-batch row identifier (generated inside the operator, used to join deduplication results back) |

> **Tip**: downstream operators (such as `semantic-cluster`) can reuse the
> `__dedup_emb` column directly, avoiding a second embedding computation.

**Input-to-output relationship**:

M:N (M >= N) - records whose vector distance is within the threshold form one cluster
and collapse into a single row (a representative record), so the output row count is
less than or equal to the input row count.

## Effect preview

**Before** (5 rows):

| question | input | output |
|----------|-------|--------|
| What is machine learning? | Please explain | Machine learning is... |
| What is the definition of machine learning? | Overview | ML trains models from data... |
| How do I get started with Python programming? | Guide | Start with the official tutorial... |
| How can a complete beginner learn Python? | Getting started | Learn the basic syntax first... |
| What is deep learning? | In brief | Deep learning is a subset of machine learning... |

**After** (3 rows) - `| dedup-semantic -field=question -threshold='0.1'`:

| question | input | output | __dedup_emb | __dedup_rid |
|----------|-------|--------|------------|------------|
| What is machine learning? | Please explain | Machine learning is... | [0.12, -0.34, ...] | 1 |
| How do I get started with Python programming? | Guide | Start with the official tutorial... | [0.56, 0.78, ...] | 3 |
| What is deep learning? | In brief | Deep learning is a subset of machine learning... | [-0.11, 0.45, ...] | 5 |

> The two machine-learning questions are semantically equivalent (vector distance
> below 0.1) and form one cluster; the two Python questions behave the same way. The
> output goes from 5 rows to 3, and `semantic-cluster` downstream can reuse
> `__dedup_emb` directly.

## Examples

### Example 1: semantic deduplication within the batch

```
* | project question,input,output
  | dedup-semantic -field=question -threshold='0.1'
```

Uses the default model to semantically deduplicate the `question` field.

### Example 2: global semantic deduplication (recommended)

```
* | project question,input,output
  | dedup-semantic -field=question -threshold='0.1' -global -workspace='my-ws' -dataset='my-ds'
```

Deduplicates across batches against the historical vectors in the Dataset. A good fit
for a continuously running data Pipeline.

### Example 3: custom model and Dataset column

```
* | project question,input,output
  | dedup-semantic -field=question -threshold='0.05' -model='text-embedding-v3' -global -workspace='my-ws' -dataset='my-ds' -column_name='question'
```

### Example 4: full three-stage deduplication pipeline

```
* | project question,input,output
  | dedup-exact -field=question
  | dedup-fuzzy -field=question -threshold='3' -global -workspace='my-ws' -dataset='my-ds'
  | dedup-semantic -field=question -threshold='0.1' -global -workspace='my-ws' -dataset='my-ds'
```

Exact, then fuzzy, then semantic - deduplicating stage by stage, equivalent to the
full L1 through L5 deduplication logic of the original CTE pipeline.

---

> **Everything below this line is the internal implementation spec, aimed at the
> development and engineering teams. Hide it when publishing user documentation.**

## Design notes

- **Algorithm**: `embedding(text, model)` maps text into a high-dimensional vector
  space, where semantically close texts produce vectors that are close together. The
  deduplication function judges semantic similarity by vector distance (cosine or L2),
  and records within the threshold are treated as duplicates.
- **Synthetic row identifier (`__dedup_rid`)**: to save memory, the semantic
  deduplication function accepts `(emb_array, id_array)` but returns only the IDs of
  the surviving records (not the full embeddings). The operator generates a
  batch-unique row identifier `__dedup_rid` in the first CTE via `row_number() OVER
  (ORDER BY {{field}})` and uses it as the join-back handle, so users do not need to
  supply an external ID column.
- **Window-function stability**: the `_sem_embedding` CTE is referenced several times
  (as `m1` and `m2` inside `NOT EXISTS`, for example). If the engine re-executes the
  CTE instead of materializing it, a `row_number()` without `ORDER BY` could assign
  different numbers to the same row. `ORDER BY {{field}}` makes the window ordering
  deterministic. Semantic deduplication usually runs after exact deduplication, so
  `{{field}}` values are not identical and tie-breaking instability does not arise.
- **Embedding cost**: embedding generation is compute-intensive, so run it after exact
  and fuzzy deduplication to reduce how much data has to be embedded.
- **Global mode**: a single `semhash_dedup_with_dataset` call performs three things at
  once - in-batch deduplication, cross-batch comparison, and the Dataset write. The
  function stores embedding vectors rather than IDs internally, so the synthetic ID
  does not affect the cross-batch logic.
- **In-batch mode (interim solution)**: the `semhash_dedup` function is not
  implemented yet, so in-batch vector deduplication currently uses a pure-SQL `NOT
  EXISTS` pattern. The logic: a record is dropped if another record is semantically
  similar (`cosine_similarity >= 1 - threshold`) and has a smaller `__dedup_rid` - that
  is, each similar cluster keeps the row with the smallest rid. Complexity is O(N^2),
  which suits small batches that have already passed exact and fuzzy deduplication.
  Switch back to the function call once `semhash_dedup` ships.

## SQL implementation template

### In-batch mode (default)

Used when `-global` is not enabled.

> **Interim solution**: the `semhash_dedup` function is not implemented yet, so this
> currently uses a pure-SQL `NOT EXISTS` approach. Replace it once the function ships.

```sql
set session enable_remote_functions = true;
WITH
-- Step 1: generate the embedding vector plus a synthetic row identifier
_sem_embedding AS (
    SELECT 
        embedding({{field}}, '{{model}}') AS __dedup_emb,
        row_number() OVER (ORDER BY {{field}}) AS __dedup_rid
        ##otherColumns##
    FROM ##sourceTable##
    WHERE {{field}} IS NOT NULL
),
-- Step 2: in-batch semantic dedup (NOT EXISTS pattern)
-- A record is dropped when another record is semantically similar (cosine_similarity >= 1 - threshold)
-- and has a smaller rid; each similar cluster keeps the record with the smallest rid
_sem_dedup AS (
    SELECT m1.*
    FROM _sem_embedding m1
    WHERE NOT EXISTS (
        SELECT 1
        FROM _sem_embedding m2
        WHERE m1.__dedup_rid != m2.__dedup_rid
          AND cosine_similarity(m1.__dedup_emb, m2.__dedup_emb) >= 1.0 - {{threshold}}
          AND m2.__dedup_rid < m1.__dedup_rid
    )
)
-- Output: user columns plus derived columns (always appended)
SELECT * FROM _sem_dedup
```

### Global mode (`-global` enabled)

Layers cross-batch global deduplication on top of in-batch deduplication.

```sql
set session enable_remote_functions = true;
WITH
-- Step 1: generate the embedding vector plus a synthetic row identifier
_sem_embedding AS (
    SELECT 
        embedding({{field}}, '{{model}}') AS __dedup_emb,
        row_number() OVER (ORDER BY {{field}}) AS __dedup_rid
        ##otherColumns##
    FROM ##sourceTable##
    WHERE {{field}} IS NOT NULL
),
-- Step 2: global semantic dedup
-- semhash_dedup_with_dataset performs all of the following at once:
--   a) in-batch semantic dedup
--   b) comparison against the historical vectors in the Dataset
--   c) writing the new vectors into the Dataset
_sem_valid_rids AS (
    SELECT 
        semhash_dedup_with_dataset(
            array_agg(__dedup_emb), 
            array_agg(cast(__dedup_rid as varchar)), 
            '{{workspace}}', '{{dataset}}',
            '{{column_name}}', 
            '{{threshold}}'
        ) AS valid_rids
    FROM _sem_embedding
),
-- Step 3: join back to the original data
_sem_dedup AS (
    SELECT m1.*
    FROM _sem_embedding m1
    JOIN (
        SELECT rid FROM _sem_valid_rids, UNNEST(valid_rids) AS m(rid)
    ) m2 ON cast(m1.__dedup_rid as varchar) = m2.rid
)
-- Output: user columns plus derived columns (always appended)
SELECT * FROM _sem_dedup
```

## Template variables

| Template variable | Parameter | Default | Description |
|-------------------|-----------|---------|-------------|
| `{{field}}` | `-field` | - | Name of the field to deduplicate on |
| `{{threshold}}` | `-threshold` | `'0.1'` | Vector-distance threshold |
| `{{model}}` | `-model` | `'embedding-multilang-v3'` | Embedding model name |
| `{{workspace}}` | `-workspace` | - | Workspace holding the Dataset (global mode) |
| `{{dataset}}` | `-dataset` | - | Dataset name (global mode) |
| `{{column_name}}` | `-column_name` | Same as `{{field}}` | The vector column in the Dataset (global mode) |
| `##sourceTable##` | Resolved by the engine | - | The upstream CTE name or base query table |
| `##otherColumns##` | Derived by the engine | - | Pass-through macro for non-derived columns; commas and duplicate column names are handled automatically afterwards |

## Dependent functions

| Signature | Description |
|-----------|-------------|
| `embedding(text, model) -> array(double)` | Generate a text embedding vector |
| `cosine_similarity(vec1, vec2) -> double` | Cosine similarity of two vectors (used by the interim in-batch solution) |
| `semhash_dedup(emb_array, id_array, threshold) -> array(varchar)` | In-batch semantic dedup, returning the surviving record IDs (**not implemented yet**; replaces the `NOT EXISTS` approach once it ships) |
| `semhash_dedup_with_dataset(emb_array, id_array, workspace, dataset, column, threshold) -> array(varchar)` | Cross-batch semantic dedup, including the automatic Dataset write |

## Edge cases

| Case | Handling |
|------|----------|
| The `-field` column does not exist | The engine raises a parameter-validation error |
| The `-field` value is NULL | Filtered by the `WHERE` clause; NULL rows take no part in deduplication and do not appear in the output |
| The input is empty (0 rows) | An empty result set is returned normally |
| `-threshold` falls outside [0, 1] | The engine raises a parameter-validation error |
| The embedding model is unavailable | The engine raises a runtime error asking you to check the model name |
| `-global` is set but `-workspace` or `-dataset` is missing | The engine raises a parameter-validation error |
| The `semhash_dedup` function is not implemented yet | In-batch mode uses the pure-SQL `NOT EXISTS` plus `cosine_similarity` approach (O(N^2)); run exact and fuzzy deduplication first to reduce the data volume |
