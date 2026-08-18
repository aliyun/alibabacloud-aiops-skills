# dedup-exact (exact deduplication)

> Match SimHash fingerprints exactly to remove records whose text is identical.

## Function

Computes a SimHash fingerprint for the given field, treats records with identical
fingerprints as duplicates, and keeps only the record with the longest text (the
most information) in each group.

SimHash is a locality-sensitive hashing algorithm that maps text of any length to a
fixed-length binary fingerprint. Identical text always produces the identical
fingerprint, so exact fingerprint matching is enough to decide that two texts are
duplicates.

**Use cases**:

- Identical text entries produced by logging or data collection
- Redundant records caused by repeated submissions or repeated pushes
- A preprocessing step before fuzzy or semantic deduplication, cutting the data
  volume and compute cost of the later operators

## Syntax

```
| dedup-exact -field=<column> [-global -workspace=<workspace> -dataset=<dataset>]
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `-field` | Field | **Yes** | - | Name of the field to deduplicate on; must be a text column |
| `-global` | Bool | No | `false` | Whether to enable global deduplication (across batches, incrementally against a Dataset) |
| `-workspace` | String | Conditionally required | - | Workspace holding the Dataset (required when `-global` is set) |
| `-dataset` | String | Conditionally required | - | Dataset name (required when `-global` is set) |

## Input and output

**Input**:

- Any columns emitted by the upstream operator
- The field named by `-field` must be present and be a text column (varchar)

**Output**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| All input columns | — | Input | Every upstream column passes through |
| `__dedup_hash` | bigint | Derived | The text fingerprint, identifying text uniqueness |
| `__dedup_weight` | integer | Derived | Text length, the basis for the dedup weight (the longest text in a group wins) |
| `__dedup_rnk` | integer | Derived | Rank within the group (always 1 after deduplication, marking the row as the group's best pick) |

**Input-to-output relationship**:

M:N (M ≥ N) — records sharing a fingerprint collapse into one row (the longest text
in each group), so the output row count is less than or equal to the input row count.

## Effect preview

**Before** (5 rows):

| question | input | output |
|----------|-------|--------|
| What is machine learning? | Please explain | Machine learning is a branch of artificial intelligence… |
| What is machine learning? | Please explain in detail | Machine learning (ML) trains models from data… |
| How do I learn Python? | Getting-started guide | Start with the official tutorial… |
| What is deep learning? | In brief | Deep learning is a subset of machine learning… |
| How do I learn Python? | For beginners | Learn the basic syntax first… |

**After** (3 rows) — `| dedup-exact -field=question`:

| question | input | output | __dedup_hash | __dedup_weight | __dedup_rnk |
|----------|-------|--------|-------------|---------------|-------------|
| What is machine learning? | Please explain in detail | Machine learning (ML) trains models from data… | 8832749102 | 25 | 1 |
| How do I learn Python? | Getting-started guide | Start with the official tutorial… | 5561023847 | 22 | 1 |
| What is deep learning? | In brief | Deep learning is a subset of machine learning… | 3347891256 | 22 | 1 |

> Both groups of records with an identical `question` keep a single row (the one with
> the longest text), so the output goes from 5 rows to 3. The derived columns
> `__dedup_hash`, `__dedup_weight`, and `__dedup_rnk` are available to downstream
> operators for reference or filtering.

## Examples

### Example 1: exact deduplication within the batch

```
* | project question,input,output
  | dedup-exact -field=question
```

Deduplicates the current batch on the `question` field and keeps every column.

### Example 2: global exact deduplication

```
* | project question,input,output
  | dedup-exact -field=question -global -workspace='my-ws' -dataset='my-ds'
```

On top of in-batch deduplication, compares the fingerprints against the historical
data in the Dataset, keeps only records that are genuinely new, and writes the new
data into the Dataset.

### Example 3: pipeline composition

```
* | project question,input,output
  | dedup-exact -field=question
  | dedup-fuzzy -field=question -threshold='3'
```

Remove exact duplicates first, then remove near-duplicates that differ slightly,
converging the data step by step.

---

> **Everything below this line is the internal implementation spec, aimed at the
> development and engineering teams. Hide it when publishing user documentation.**

## Design notes

- **Algorithm**: `prompt_simhash(text)` generates a 64-bit SimHash fingerprint for
  the text, and identical text produces the identical fingerprint. `PARTITION BY
  __dedup_hash` groups records that share a fingerprint, then Top-1 by descending
  text length keeps the longest text (the most information).
- **Relationship with dedup-fuzzy**: `dedup-exact` is equivalent to `dedup-fuzzy
  -threshold='0'`, but the implementation is lighter (no `simhash_dedup` aggregate
  call), which makes it a good leading step for quickly shrinking the data volume.
- **Global mode**: `simhash_dedup_with_dataset` compares the batch's unique
  fingerprints against the Dataset history with exact matching (threshold `'0'`),
  then `simhash_dataset_upsert` writes the surviving fingerprints into the Dataset.
- **Output column contract**: the operator emits every input column plus the derived
  columns (`__dedup_hash`, `__dedup_weight`, `__dedup_rnk`). Narrow the output by
  appending a `project` later in the pipeline.

## SQL implementation template

### In-batch mode (default)

Used when `-global` is not enabled.

```sql
set session enable_remote_functions = true;
WITH
-- Step 1: compute the SimHash fingerprint and the text weight
_exact_feature AS (
    SELECT 
        prompt_simhash({{field}}) AS __dedup_hash,
        length({{field}}) AS __dedup_weight
        ##otherColumns##
    FROM ##sourceTable##
    WHERE {{field}} IS NOT NULL
),
-- Step 2: group by fingerprint and keep the longest text per group
_exact_dedup AS (
    SELECT * FROM (
        SELECT 
            *,
            row_number() OVER (PARTITION BY __dedup_hash ORDER BY __dedup_weight DESC) AS __dedup_rnk
        FROM _exact_feature
    ) WHERE __dedup_rnk = 1
)
-- Output: user columns plus derived columns (always appended)
SELECT * FROM _exact_dedup
```

### Global mode (`-global` enabled)

Layers cross-batch global deduplication on top of in-batch deduplication.

```sql
set session enable_remote_functions = true;
WITH
-- Step 1: compute the SimHash fingerprint and the text weight
_exact_feature AS (
    SELECT 
        prompt_simhash({{field}}) AS __dedup_hash,
        length({{field}}) AS __dedup_weight
        ##otherColumns##
    FROM ##sourceTable##
    WHERE {{field}} IS NOT NULL
),
-- Step 2: in-batch dedup plus global dedup
-- simhash_dedup(..., '0'): exact in-batch dedup (Hamming distance = 0)
-- simhash_dedup_with_dataset(..., '0'): exact comparison against the Dataset history
-- simhash_dataset_upsert: write the new fingerprints into the Dataset
_exact_global_hashes AS (
    SELECT hash FROM (
        SELECT 
            sh_array,
            simhash_dataset_upsert(sh_array, '{{workspace}}', '{{dataset}}')
        FROM (
            SELECT 
                simhash_dedup_with_dataset(
                    simhash_dedup(
                        array_agg(__dedup_hash), 
                        array_agg(cast(__dedup_weight as integer)), 
                        '0'
                    ),
                    '{{workspace}}', '{{dataset}}',
                    '0'
                ) AS sh_array
            FROM _exact_feature
        )
    ), UNNEST(sh_array) AS m(hash)
),
-- Step 3: join back to the original data, keeping the longest text per surviving fingerprint
_exact_dedup AS (
    SELECT * FROM (
        SELECT 
            m1.*,
            row_number() OVER (PARTITION BY m1.__dedup_hash ORDER BY m1.__dedup_weight DESC) AS __dedup_rnk
        FROM _exact_feature m1
        JOIN _exact_global_hashes m2 ON m1.__dedup_hash = m2.hash
    ) WHERE __dedup_rnk = 1
)
-- Output: user columns plus derived columns (always appended)
SELECT * FROM _exact_dedup
```

## Template variables

| Template variable | Parameter | Default | Description |
|-------------------|-----------|---------|-------------|
| `{{field}}` | `-field` | - | Name of the field to deduplicate on |
| `{{workspace}}` | `-workspace` | - | Workspace holding the Dataset (global mode) |
| `{{dataset}}` | `-dataset` | - | Dataset name (global mode) |
| `##sourceTable##` | Resolved by the engine | - | The upstream CTE name or base query table |
| `##otherColumns##` | Derived by the engine | - | Pass-through macro for non-derived columns; commas and duplicate column names are handled automatically afterwards |

## Dependent functions

| Signature | Description |
|-----------|-------------|
| `prompt_simhash(text) → bigint` | Compute the SimHash fingerprint of the text |
| `simhash_dedup(sh_array, weight_array, threshold) → array(bigint)` | In-batch SimHash dedup, returning the surviving fingerprints (used in global mode) |
| `simhash_dedup_with_dataset(sh_array, workspace, dataset, threshold) → array(bigint)` | Cross-batch SimHash dedup (used in global mode) |
| `simhash_dataset_upsert(sh_array, workspace, dataset) → void` | Write fingerprints into the Dataset (used in global mode) |

## Edge cases

| Case | Handling |
|------|----------|
| The `-field` column does not exist | The engine raises a parameter-validation error reporting the missing field |
| The `-field` value is NULL | Filtered by the `WHERE` clause; NULL rows take no part in deduplication and do not appear in the output |
| The input is empty (0 rows) | An empty result set is returned normally |
| Several rows share a fingerprint and have the same text length | `row_number()` picks one non-deterministically (the result is stable but no specific row is guaranteed) |
| `-global` is set but `-workspace` or `-dataset` is missing | The engine raises a parameter-validation error |
| The Dataset does not exist or is unreachable | The engine raises a runtime error; check the workspace and dataset configuration |
