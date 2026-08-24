# dedup-fuzzy (fuzzy deduplication)

> Use the SimHash Hamming distance to remove records whose text is highly similar
> but not identical.

## Function

Computes a SimHash fingerprint for the given field and judges text similarity by the
Hamming distance between fingerprints (the number of differing bits). Records whose
Hamming distance falls within the threshold are treated as near-duplicates, and each
group keeps only the record with the highest weight (the longest text).

The SimHash Hamming distance reflects how far two texts differ literally: the smaller
the distance, the more similar the texts. A threshold of 0 is equivalent to exact
deduplication, while a threshold of 3 corresponds to roughly 90%+ text similarity,
which is a good fit for filtering out typos, punctuation differences, whitespace
differences, and other small variations.

**Use cases**:

- Duplicate data with small variations (typos, punctuation changes, whitespace
  differences)
- Similar text produced by templates (near-identical output from prompt tweaks)
- Near-duplicate data caused by formatting differences in crawling or collection
  pipelines

## Syntax

```
| dedup-fuzzy -field=<column> [-threshold=<hamming_distance>] [-global -workspace=<workspace> -dataset=<dataset>]
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `-field` | Field | **Yes** | - | Name of the field to deduplicate on; must be a text column |
| `-threshold` | String | No | `'3'` | Hamming-distance threshold (a non-negative integer); the smaller, the stricter |
| `-global` | Bool | No | `false` | Whether to enable global deduplication (across batches, incrementally against a Dataset) |
| `-workspace` | String | Conditionally required | - | Workspace holding the Dataset (required when `-global` is set) |
| `-dataset` | String | Conditionally required | - | Dataset name (required when `-global` is set) |

> **Threshold guidance**:
>
> | Threshold | Strictness | Description |
> |-----------|-----------|-------------|
> | `0` | Exact match | Equivalent to `dedup-exact`; removes only identical text |
> | `1~2` | Very strict | Filters out only single-character differences |
> | **`3`** | **Recommended default** | Suits most text-deduplication scenarios |
> | `5~7` | Looser | May drop text with meaningful differences; use with care |
> | `8+` | Too loose | Not recommended; likely to drop a lot of valid data |

## Input and output

**Input**:

- Any columns emitted by the upstream operator
- The field named by `-field` must be present and be a text column (varchar)

**Output**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| All input columns | - | Input | Every upstream column passes through |
| `__dedup_hash` | bigint | Derived | The text fingerprint, identifying text uniqueness |
| `__dedup_weight` | integer | Derived | Text length, the basis for the dedup weight (the longest text in a cluster wins) |
| `__dedup_rnk` | integer | Derived | Rank within the cluster (always 1 after deduplication, marking the row as the cluster's best pick) |

**Input-to-output relationship**:

M:N (M >= N) - records whose Hamming distance is within the threshold form one
cluster and collapse into a single row (the longest text in each cluster), so the
output row count is less than or equal to the input row count.

## Effect preview

**Before** (5 rows):

| question | input | output |
|----------|-------|--------|
| What is machine learning? | Please explain | Machine learning is... |
| What is machine learning?? | Please explain in detail | Machine learning (Machine Learning) is... |
| How do I learn Python? | Getting started | Start with the official tutorial... |
| How can I learn Python? | Guide | Learn the basic syntax first... |
| What is deep learning? | In brief | Deep learning is a subset of machine learning... |

**After** (3 rows) - `| dedup-fuzzy -field=question -threshold='3'`:

| question | input | output | __dedup_hash | __dedup_weight | __dedup_rnk |
|----------|-------|--------|-------------|---------------|-------------|
| What is machine learning?? | Please explain in detail | Machine learning (Machine Learning) is... | 8832749102 | 26 | 1 |
| How do I learn Python? | Getting started | Start with the official tutorial... | 5561023847 | 22 | 1 |
| What is deep learning? | In brief | Deep learning is a subset of machine learning... | 3347891256 | 22 | 1 |

> The two machine-learning questions have a fingerprint Hamming distance within 3, so
> they form one cluster and the longest text survives; the two Python questions behave
> the same way. The output goes from 5 rows to 3.

## Examples

### Example 1: fuzzy deduplication within the batch (default threshold)

```
* | project question,input,output
  | dedup-fuzzy -field=question
```

Applies the default threshold of 3 to fuzzy-deduplicate the `question` field.

### Example 2: adjusting the threshold

```
* | project question,input,output
  | dedup-fuzzy -field=question -threshold='5'
```

Relaxes the threshold to 5, filtering more near-duplicate text.

### Example 3: global fuzzy deduplication

```
* | project question,input,output
  | dedup-fuzzy -field=question -threshold='3' -global -workspace='my-ws' -dataset='my-ds'
```

Deduplicates across batches, comparing against the historical data in the Dataset.

### Example 4: exact plus fuzzy cascade

```
* | project question,input,output
  | dedup-exact -field=question
  | dedup-fuzzy -field=question -threshold='3' -global -workspace='my-ws' -dataset='my-ds'
```

Remove full duplicates quickly first (exact deduplication is cheaper to compute), then
fuzzy-deduplicate, shrinking the input that `simhash_dedup` has to process.

---

> **Everything below this line is the internal implementation spec, aimed at the
> development and engineering teams. Hide it when publishing user documentation.**

## Design notes

- **Algorithm**: `simhash_dedup(sh_array, weight_array, threshold)` takes a batch of
  SimHash fingerprints and weights, groups fingerprints whose Hamming distance is
  within the threshold into one cluster, keeps the highest-weight fingerprint as each
  cluster's representative, and returns the array of surviving fingerprints.
- **Relationship with dedup-exact**: `dedup-fuzzy -threshold='0'` is equivalent to
  `dedup-exact`, but `dedup-exact` uses a lighter `row_number()` implementation, so
  running it first is recommended to shrink the input to `dedup-fuzzy`.
- **Global mode**: `simhash_dedup` deduplicates within the batch first, then
  `simhash_dedup_with_dataset` compares against the Dataset history across batches,
  and finally `simhash_dataset_upsert` writes the new data into the Dataset. All
  three steps complete atomically inside one nested SQL statement.
- **Join-back strategy**: `simhash_dedup` returns surviving fingerprints (not row
  IDs), so the original data is joined back on the fingerprint. If a fingerprint maps
  to several rows (because the upstream did not run exact deduplication),
  `row_number()` guarantees that exactly one row per fingerprint is emitted.

## SQL implementation template

### In-batch mode (default)

Used when `-global` is not enabled.

```sql
set session enable_remote_functions = true;
WITH
-- Step 1: compute the SimHash fingerprint and the text weight
_fuzzy_feature AS (
    SELECT 
        prompt_simhash({{field}}) AS __dedup_hash,
        length({{field}}) AS __dedup_weight
        ##otherColumns##
    FROM ##sourceTable##
    WHERE {{field}} IS NOT NULL
),
-- Step 2: fuzzy in-batch dedup based on Hamming distance
-- simhash_dedup clusters fingerprints within the threshold and keeps the highest-weight fingerprint per cluster
_fuzzy_surviving AS (
    SELECT hash FROM (
        SELECT 
            simhash_dedup(
                array_agg(__dedup_hash), 
                array_agg(cast(__dedup_weight as integer)), 
                '{{threshold}}'
            ) AS sh_array
        FROM _fuzzy_feature
    ), UNNEST(sh_array) AS m(hash)
),
-- Step 3: join back to the original data, keeping the longest text per surviving fingerprint
_fuzzy_dedup AS (
    SELECT * FROM (
        SELECT 
            m1.*,
            row_number() OVER (PARTITION BY m1.__dedup_hash ORDER BY m1.__dedup_weight DESC) AS __dedup_rnk
        FROM _fuzzy_feature m1
        JOIN _fuzzy_surviving m2 ON m1.__dedup_hash = m2.hash
    ) WHERE __dedup_rnk = 1
)
-- Output: user columns plus derived columns (always appended)
SELECT * FROM _fuzzy_dedup
```

### Global mode (`-global` enabled)

Layers cross-batch global deduplication on top of in-batch deduplication.

```sql
set session enable_remote_functions = true;
WITH
-- Step 1: compute the SimHash fingerprint and the text weight
_fuzzy_feature AS (
    SELECT 
        prompt_simhash({{field}}) AS __dedup_hash,
        length({{field}}) AS __dedup_weight
        ##otherColumns##
    FROM ##sourceTable##
    WHERE {{field}} IS NOT NULL
),
-- Step 2: fuzzy in-batch dedup plus global dedup
-- simhash_dedup: fuzzy in-batch dedup
-- simhash_dedup_with_dataset: fuzzy comparison against the Dataset history
-- simhash_dataset_upsert: write the surviving fingerprints into the Dataset
_fuzzy_surviving AS (
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
                        '{{threshold}}'
                    ),
                    '{{workspace}}', '{{dataset}}',
                    '{{threshold}}'
                ) AS sh_array
            FROM _fuzzy_feature
        )
    ), UNNEST(sh_array) AS m(hash)
),
-- Step 3: join back to the original data, keeping the longest text per surviving fingerprint
_fuzzy_dedup AS (
    SELECT * FROM (
        SELECT 
            m1.*,
            row_number() OVER (PARTITION BY m1.__dedup_hash ORDER BY m1.__dedup_weight DESC) AS __dedup_rnk
        FROM _fuzzy_feature m1
        JOIN _fuzzy_surviving m2 ON m1.__dedup_hash = m2.hash
    ) WHERE __dedup_rnk = 1
)
-- Output: user columns plus derived columns (always appended)
SELECT * FROM _fuzzy_dedup
```

## Template variables

| Template variable | Parameter | Default | Description |
|-------------------|-----------|---------|-------------|
| `{{field}}` | `-field` | - | Name of the field to deduplicate on |
| `{{threshold}}` | `-threshold` | `'3'` | Hamming-distance threshold |
| `{{workspace}}` | `-workspace` | - | Workspace holding the Dataset (global mode) |
| `{{dataset}}` | `-dataset` | - | Dataset name (global mode) |
| `##sourceTable##` | Resolved by the engine | - | The upstream CTE name or base query table |
| `##otherColumns##` | Derived by the engine | - | Pass-through macro for non-derived columns; commas and duplicate column names are handled automatically afterwards |

## Dependent functions

| Signature | Description |
|-----------|-------------|
| `prompt_simhash(text) -> bigint` | Compute the SimHash fingerprint of the text |
| `simhash_dedup(sh_array, weight_array, threshold) -> array(bigint)` | Fuzzy in-batch dedup; clusters by Hamming distance and returns the surviving fingerprints |
| `simhash_dedup_with_dataset(sh_array, workspace, dataset, threshold) -> array(bigint)` | Cross-batch fuzzy dedup (global mode) |
| `simhash_dataset_upsert(sh_array, workspace, dataset) -> void` | Write fingerprints into the Dataset (global mode) |

## Edge cases

| Case | Handling |
|------|----------|
| The `-field` column does not exist | The engine raises a parameter-validation error reporting the missing field |
| The `-field` value is NULL | Filtered by the `WHERE` clause; NULL rows take no part in deduplication and do not appear in the output |
| The input is empty (0 rows) | An empty result set is returned normally |
| `-threshold` is negative or not a number | The engine raises a parameter-validation error |
| `-threshold` is too large (>= 64) | Every record falls into one cluster and only one row survives; the engine may emit a warning |
| Several rows share a fingerprint and have the same text length | `row_number()` picks one non-deterministically |
| `-global` is set but `-workspace` or `-dataset` is missing | The engine raises a parameter-validation error |
| The Dataset does not exist or is unreachable | The engine raises a runtime error |
