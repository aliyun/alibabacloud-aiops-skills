# Dedup operator family

## Overview

The dedup operator family provides three granularities of data deduplication, aimed at
the data-cleaning stage of an AI data-processing Pipeline.

> **Detailed operator definitions**: each operator has its own definition document (with
> the full syntax, parameters, SQL templates, and edge-case handling); this file is the
> family overview.
>
> | Operator | Definition document | One-sentence description |
> |----------|--------------------|--------------------------|
> | `dedup-exact` | [dedup-exact.md](./dedup-exact.md) | Exact SimHash fingerprint matching to remove identical text |
> | `dedup-fuzzy` | [dedup-fuzzy.md](./dedup-fuzzy.md) | SimHash Hamming distance to remove highly similar text |
> | `dedup-semantic` | [dedup-semantic.md](./dedup-semantic.md) | Embedding-vector distance to remove semantically identical text |

The three operators are ordered from coarse to fine deduplication granularity:

| Operator | Granularity | Core principle | Typical use |
|----------|-------------|----------------|-------------|
| `dedup-exact` | Exact dedup | Exact SimHash fingerprint match | Removing identical text |
| `dedup-fuzzy` | Fuzzy dedup | SimHash Hamming distance | Removing text with small variations (typos, punctuation differences, and so on) |
| `dedup-semantic` | Semantic dedup | Embedding-vector distance | Removing text that means the same thing but is worded differently |

Every operator supports two run modes:
- **In-batch mode** (default): deduplicates only within the current batch
- **Global mode** (`-global`): incremental cross-batch deduplication against a Dataset
  (addressed by `-workspace` and `-dataset`), automatically writing the new data into the
  Dataset

---

## Design decision: why three separate operators

### Option comparison

| Dimension | Option A: one operator with a mode parameter | Option B: three separate operators ✅ recommended |
|-----------|--------------------------------------------|------------------------------------------------|
| **Atomicity** | ❌ One operator carries three behaviors, violating single responsibility | ✅ Each operator has one clear responsibility |
| **Composability** | ❌ Combined modes need mutual-exclusion validation inside, raising complexity | ✅ Freely composed in the pipeline, orchestrated as the user needs |
| **UI rendering** | ❌ The configuration panel needs conditional show/hide, complicating interaction | ✅ Each drag-and-drop node has a clean configuration (3 to 6 parameters) |
| **Parameter simplicity** | ❌ Parameter explosion (around 15), heavy cognitive load | ✅ Few parameters per operator, each with clear semantics |
| **Learning cost** | ⚠️ Learned in one pass, but the parameter documentation is long | ✅ Progressive learning, used as needed |
| **Independent testing** | ❌ Needs mocks for the different mode combinations | ✅ Each operator's behavior is verified independently |
| **SPL consistency** | ❌ Conflicts with the SPL "one instruction, one capability" philosophy | ✅ Fully aligned with the SPL design philosophy |

### Recommended option

**Option B: three separate operators.** The main reasons:

1. **Aligned with the SPL philosophy**: every SLS SPL instruction (`project`,
   `project-away`, `project-rename`, and so on) has a single capability, and dedup
   operators should follow the same principle
2. **UI friendly**: in drag-and-drop orchestration, each node has a clear purpose and a
   clean configuration, so users understand what a node does at a glance
3. **Flexible orchestration**: users can compose deduplication strategies freely to match
   their data-quality needs (exact only, exact plus semantic, all three stages, and so on)
4. **Progressive adoption**: newcomers start with `dedup-exact` and advanced users
   introduce semantic deduplication gradually

Users chain the operators in a pipeline for multi-stage deduplication:

```
* | dedup-exact -field=question
  | dedup-fuzzy -field=question -threshold='3' -global -workspace='my-ws' -dataset='my-ds'
  | dedup-semantic -field=question -threshold='0.1' -global -workspace='my-ws' -dataset='my-ds'
```

> **Additional note**: if "one-click three-stage deduplication" turns out to be a frequent
> request, a `dedup-auto` syntactic-sugar operator could be added that expands internally
> into the three separate operators, while the underlying implementation still rests on
> the three atomic operators.

---

## 1. dedup-exact (exact deduplication)

### 1.1 What it does

Deduplicates exactly by **text SimHash fingerprint**. It computes a SimHash fingerprint
for the given field, treats records with identical fingerprints as duplicates, and keeps
the record with the longest text (the most information) in each group.

**Use cases**:
- Identical text records in logs or data
- Duplicate entries produced by data collection
- A preprocessing step before fuzzy or semantic deduplication, cutting the later compute
  cost

### 1.2 Syntax

```
| dedup-exact -field=<column> [-output=<fields>] [-global -workspace=<workspace> -dataset=<dataset>]
```

### 1.3 Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `-field` | Field | **Yes** | - | Name of the field to deduplicate on |
| `-output` | FieldList | No | `*` | The output column list; `*` keeps every input column |
| `-global` | Bool | No | false | Whether to enable global deduplication (across batches, incrementally against a Dataset) |
| `-workspace` | String | Conditionally required | - | Workspace holding the Dataset (required when `-global` is set) |
| `-dataset` | String | Conditionally required | - | Dataset name (required when `-global` is set) |

### 1.4 Input and output

- **Input**: any columns emitted by the upstream operator; the field named by `-field`
  must be present and be a text column
- **Output**: the column structure follows `-output`, plus the operator's derived
  columns: `__dedup_hash` (the SimHash fingerprint, bigint), `__dedup_weight` (text
  length, integer), and `__dedup_rnk` (rank within the cluster, integer)
- **Input-to-output relationship**: the output row count is less than or equal to the
  input row count (fully duplicated records are removed)

### 1.5 Examples

**Example 1: exact deduplication within the batch**

```
* | dedup-exact -field=question
```

**Example 2: global exact deduplication (across batches)**

```
* | dedup-exact -field=question -global -workspace='my-ws' -dataset='my-ds'
```

### 1.6 SQL implementation template

#### In-batch mode (default)

```sql
set session enable_remote_functions = true;
WITH
-- Step 1: project the user columns and compute the SimHash fingerprint and text weight
_exact_feature AS (
    SELECT 
        {{output}},
        prompt_simhash({{field}}) AS __dedup_hash,
        length({{field}}) AS __dedup_weight
    FROM __input__
    WHERE {{field}} IS NOT NULL
),
-- Step 2: group and order by fingerprint, keeping the longest text per group
_exact_ranked AS (
    SELECT 
        *,
        row_number() OVER (
            PARTITION BY __dedup_hash 
            ORDER BY __dedup_weight DESC
        ) AS __dedup_rnk
    FROM _exact_feature
)
SELECT * FROM _exact_ranked WHERE __dedup_rnk = 1
```

#### Global mode (`-global`)

```sql
set session enable_remote_functions = true;
WITH
-- Step 1: project the user columns and compute the SimHash fingerprint and text weight
_exact_feature AS (
    SELECT 
        {{output}},
        prompt_simhash({{field}}) AS __dedup_hash,
        length({{field}}) AS __dedup_weight
    FROM __input__
    WHERE {{field}} IS NOT NULL
),
-- Step 2: in-batch exact dedup plus cross-batch global dedup
-- simhash_dedup(..., '0') runs exact in-batch dedup first (Hamming distance = 0)
-- simhash_dedup_with_dataset(..., '0') then compares exactly against the Dataset history
-- simhash_dataset_upsert writes this batch's new data into the Dataset
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
_exact_result AS (
    SELECT 
        m1.*,
        row_number() OVER (
            PARTITION BY m1.__dedup_hash 
            ORDER BY m1.__dedup_weight DESC
        ) AS __dedup_rnk
    FROM _exact_feature m1
    JOIN _exact_global_hashes m2 ON m1.__dedup_hash = m2.hash
)
SELECT * FROM _exact_result WHERE __dedup_rnk = 1
```

---

## 2. dedup-fuzzy (fuzzy deduplication)

### 2.1 What it does

Deduplicates approximately by **SimHash Hamming distance**. It computes a SimHash
fingerprint for the given field and judges text similarity by the Hamming distance
between fingerprints (the number of differing bits). Records within the threshold are
treated as near-duplicates, and each group keeps the record with the highest weight (the
longest text).

**How it works**: SimHash maps text to a fixed-length binary fingerprint, and a smaller
Hamming distance between two fingerprints means more similar text. A threshold of 0 is
equivalent to exact deduplication, and a threshold of 3 corresponds to roughly 90%+ text
similarity.

**Use cases**:
- Duplicate data with small variations (typos, punctuation differences, whitespace
  differences, and so on)
- Similar text produced by templates
- Removing highly similar but non-identical records in bulk

### 2.2 Syntax

```
| dedup-fuzzy -field=<column> [-threshold=<hamming_distance>] [-output=<fields>] [-global -workspace=<workspace> -dataset=<dataset>]
```

### 2.3 Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `-field` | Field | **Yes** | - | Name of the field to deduplicate on |
| `-threshold` | String | No | `'3'` | Hamming-distance threshold; the smaller, the stricter. `0` is an exact match, `3` allows a 3-bit difference (recommended), `5` is looser |
| `-output` | FieldList | No | `*` | The output column list; `*` keeps every input column |
| `-global` | Bool | No | false | Whether to enable global deduplication |
| `-workspace` | String | Conditionally required | - | Workspace holding the Dataset (required when `-global` is set) |
| `-dataset` | String | Conditionally required | - | Dataset name (required when `-global` is set) |

> **Threshold guidance**:
> - `1~2`: very strict, filtering only single-character differences
> - `3`: the recommended default, suiting most text-deduplication scenarios
> - `5~7`: looser, may drop text with meaningful differences; use with care

### 2.4 Input and output

- **Input**: any columns emitted by the upstream operator; the field named by `-field`
  must be present and be a text column
- **Output**: the column structure follows `-output`, plus the operator's derived
  columns: `__dedup_hash` (the SimHash fingerprint, bigint), `__dedup_weight` (text
  length, integer), and `__dedup_rnk` (rank within the cluster, integer)
- **Input-to-output relationship**: the output row count is less than or equal to the
  input row count (duplicated records are removed)

### 2.5 Examples

**Example 1: fuzzy deduplication within the batch (default threshold of 3)**

```
* | dedup-fuzzy -field=question
```

**Example 2: fuzzy deduplication with a looser threshold**

```
* | dedup-fuzzy -field=question -threshold='5'
```

**Example 3: global fuzzy deduplication (across batches)**

```
* | dedup-fuzzy -field=question -threshold='3' -global -workspace='my-ws' -dataset='my-ds'
```

### 2.6 SQL implementation template

#### In-batch mode (default)

```sql
set session enable_remote_functions = true;
WITH
-- Step 1: project the user columns and compute the SimHash fingerprint and text weight
_fuzzy_feature AS (
    SELECT 
        {{output}},
        prompt_simhash({{field}}) AS __dedup_hash,
        length({{field}}) AS __dedup_weight
    FROM __input__
    WHERE {{field}} IS NOT NULL
),
-- Step 2: fuzzy in-batch dedup based on the Hamming-distance threshold
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
_fuzzy_result AS (
    SELECT 
        m1.*,
        row_number() OVER (
            PARTITION BY m1.__dedup_hash 
            ORDER BY m1.__dedup_weight DESC
        ) AS __dedup_rnk
    FROM _fuzzy_feature m1
    JOIN _fuzzy_surviving m2 ON m1.__dedup_hash = m2.hash
)
SELECT * FROM _fuzzy_result WHERE __dedup_rnk = 1
```

#### Global mode (`-global`)

```sql
set session enable_remote_functions = true;
WITH
-- Step 1: project the user columns and compute the SimHash fingerprint and text weight
_fuzzy_feature AS (
    SELECT 
        {{output}},
        prompt_simhash({{field}}) AS __dedup_hash,
        length({{field}}) AS __dedup_weight
    FROM __input__
    WHERE {{field}} IS NOT NULL
),
-- Step 2: fuzzy in-batch dedup plus cross-batch global dedup
-- simhash_dedup runs fuzzy in-batch dedup first
-- simhash_dedup_with_dataset then compares approximately against the Dataset history
-- simhash_dataset_upsert writes this batch's surviving data into the Dataset
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
_fuzzy_result AS (
    SELECT 
        m1.*,
        row_number() OVER (
            PARTITION BY m1.__dedup_hash 
            ORDER BY m1.__dedup_weight DESC
        ) AS __dedup_rnk
    FROM _fuzzy_feature m1
    JOIN _fuzzy_surviving m2 ON m1.__dedup_hash = m2.hash
)
SELECT * FROM _fuzzy_result WHERE __dedup_rnk = 1
```

---

## 3. dedup-semantic (semantic deduplication)

### 3.1 What it does

Deduplicates by **text embedding-vector distance**. It uses an ML model to generate a
vector representation (an embedding) of the given field and judges semantic similarity by
the distance between vectors. Records within the threshold are treated as semantic
duplicates, and a representative record is kept.

**How it works**: text is mapped into a high-dimensional vector space where semantically
close texts sit close together. Setting a vector-distance threshold therefore identifies
text that is worded differently but means the same thing.

**Use cases**:
- Deduplicating text that is worded differently but semantically identical (for example
  "What is the weather like today?" versus "How is the climate today?")
- Cross-language semantic deduplication in multilingual scenarios
- Fine-grained deduplication when building a high-quality dataset
- Usually the final deduplication stage, after exact and fuzzy deduplication

### 3.2 Syntax

```
| dedup-semantic -field=<column> [-threshold=<distance>] [-model=<embedding_model>] [-output=<fields>] [-global -workspace=<workspace> -dataset=<dataset> [-column_name=<name>]]
```

### 3.3 Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `-field` | Field | **Yes** | - | Name of the field to deduplicate on |
| `-threshold` | String | No | `'0.1'` | Vector-distance threshold; the smaller, the stricter. `0` means identical, `0.1` allows roughly 10% semantic difference |
| `-model` | String | No | `'embedding-multilang-v3'` | Embedding model name |
| `-output` | FieldList | No | `*` | The output column list; `*` keeps every input column |
| `-global` | Bool | No | false | Whether to enable global deduplication |
| `-workspace` | String | Conditionally required | - | Workspace holding the Dataset (required when `-global` is set) |
| `-dataset` | String | Conditionally required | - | Dataset name (required when `-global` is set) |
| `-column_name` | String | No | Same as `-field` | The Dataset column storing the vector (optional when `-global` is set) |

> **Threshold guidance**:
> - `0.05`: very strict, filtering only near-synonymous wording
> - `0.1`: the recommended default, suiting most semantic-deduplication scenarios
> - `0.15~0.2`: looser, may drop related but non-synonymous text; use with care
> - `0.3+`: too loose, essentially not recommended

### 3.4 Input and output

- **Input**: any columns emitted by the upstream operator; the field named by `-field`
  must be present and be a text column
- **Output**: the column structure follows `-output`, with a row count less than or equal
  to the input
- **Derived columns**: `__dedup_emb` (the embedding vector, `array(double)`) and
  `__dedup_rid` (the in-batch row identifier, `bigint`)

> **Note**: downstream operators (cluster sampling, semantic search, and so on) can reuse
> the `__dedup_emb` column, avoiding a second embedding computation.

### 3.5 Examples

**Example 1: semantic deduplication within the batch**

```
* | dedup-semantic -field=question -threshold='0.1'
```

**Example 2: global semantic deduplication (the recommended usage)**

```
* | dedup-semantic -field=question -threshold='0.1' -global -workspace='my-ws' -dataset='my-ds'
```

**Example 3: custom model and Dataset column**

```
* | dedup-semantic -field=question -threshold='0.05' -model='text-embedding-v3' -global -workspace='my-ws' -dataset='my-ds' -column_name='question'
```

### 3.6 SQL implementation template

#### In-batch mode

> **Interim solution**: the `semhash_dedup` function is not implemented yet, so this
> currently uses a pure-SQL `NOT EXISTS` approach. Replace it once the function ships.

```sql
set session enable_remote_functions = true;
WITH
-- Step 1: project the user columns, generate the embedding vector, and add a synthetic row identifier
_sem_embedding AS (
    SELECT 
        {{output}},
        embedding({{field}}, '{{model}}') AS __dedup_emb,
        row_number() OVER (ORDER BY {{field}}) AS __dedup_rid
    FROM __input__
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
SELECT * FROM _sem_dedup
```

#### Global mode (`-global`)

```sql
set session enable_remote_functions = true;
WITH
-- Step 1: project the user columns, generate the embedding vector, and add a synthetic row identifier
_sem_embedding AS (
    SELECT 
        {{output}},
        embedding({{field}}, '{{model}}') AS __dedup_emb,
        row_number() OVER (ORDER BY {{field}}) AS __dedup_rid
    FROM __input__
    WHERE {{field}} IS NOT NULL
),
-- Step 2: cross-batch global semantic dedup
-- semhash_dedup_with_dataset performs all of the following at once:
--   a) in-batch semantic dedup
--   b) semantic comparison against the historical vectors in the Dataset
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
SELECT * FROM _sem_dedup
```

---

## Pipeline composition examples

### The full three-stage deduplication pipeline

```
serviceName:my_app and * 
| dedup-exact -field=question
| dedup-fuzzy -field=question -threshold='3' -global -workspace='my-ws' -dataset='my-ds'
| dedup-semantic -field=question -threshold='0.1' -global -workspace='my-ws' -dataset='my-ds'
```

Equivalent to the full **L1 through L5** deduplication logic of the original CTE
pipeline.

### Flexible composition examples

**Exact deduplication only** (fast, zero cost):

```
* | dedup-exact -field=content
```

**Exact plus semantic (skipping fuzzy)**:

```
* | dedup-exact -field=question
  | dedup-semantic -field=question -threshold='0.15' -global -workspace='my-ws' -dataset='my-ds'
```

**Fuzzy deduplication only, global**:

```
* | dedup-fuzzy -field=question -threshold='5' -global -workspace='my-ws' -dataset='my-ds'
```

**Deduplicating several fields separately**:

```
* | dedup-exact -field=question
  | dedup-exact -field=output
```

---

## Mapping to the original CTE Pipeline

| Original CTE stage | Operator | Description |
|--------------------|----------|-------------|
| L0_data | `project` (the field-selection operator) | Extracts the key fields from the raw logs; outside the dedup operators' scope |
| L1_data (SimHash features) | Step 1 inside `dedup-exact` | SimHash fingerprint computation, done automatically inside exact/fuzzy |
| L2_data (exact dedup) | `dedup-exact` | GROUP BY dedup on the SimHash fingerprint |
| L3_data (fuzzy dedup) | `dedup-fuzzy -global` | SimHash Hamming-distance dedup plus global Dataset dedup |
| L4_data (embedding) | Step 1 inside `dedup-semantic` | Embedding generation, done automatically inside semantic |
| L5_data (semantic dedup) | `dedup-semantic -global` | Vector-distance semantic dedup plus global Dataset dedup |

---

## Template variables

The execution engine substitutes the variables in the SQL templates at runtime:

| Template variable | Source | Description |
|-------------------|--------|-------------|
| `{{field}}` | The `-field` parameter | The column to deduplicate on |
| `{{output}}` | The `-output` parameter, `*` by default | **The output columns**, placed in the SELECT of the first CTE. `*` keeps every input column; naming fields keeps only those. Derived columns are computed independently in the same SELECT, so the final `SELECT *` naturally covers both groups without duplication |
| `{{threshold}}` | The `-threshold` parameter or its default | The distance or threshold |
| `{{model}}` | The `-model` parameter or its default | The embedding model name |
| `{{workspace}}` | The `-workspace` parameter | Workspace holding the Dataset |
| `{{dataset}}` | The `-dataset` parameter | Dataset name |
| `{{column_name}}` | The `-column_name` parameter or the `-field` value | The Dataset column name |
| `__input__` | Resolved by the execution engine | The upstream operator's output (a CTE name), or the base query for the first operator |

---

## Internal column naming convention

Every derived column that a dedup operator adds is prefixed with `__dedup_` to avoid
colliding with user data columns. **Derived columns are always appended at the end of the
output** and are independent of the user columns that `-output` controls:

| Derived column | Type | Produced by | Meaning |
|----------------|------|-------------|---------|
| `__dedup_hash` | bigint | exact, fuzzy | The text fingerprint, identifying text uniqueness |
| `__dedup_weight` | integer | exact, fuzzy | Text length (the dedup weight, so the longest text survives) |
| `__dedup_rnk` | integer | exact, fuzzy | Rank within the group (always 1 after deduplication, marking the row as the group's best pick) |
| `__dedup_emb` | array(double) | semantic | The embedding vector (reusable downstream) |
| `__dedup_rid` | bigint | semantic | The in-batch row identifier (generated inside the operator, used to join deduplication results back) |

> **SQL template convention**: `{{output}}` sits in the SELECT of the first CTE so the
> column projection happens there, avoiding unnecessary column IO, while derived columns
> are computed independently in the same SELECT. Later CTEs inherit them naturally with
> `SELECT *`, and the final `SELECT *` emits every column without duplication. Users can
> strip the derived columns downstream with `project-away -wildcard "__dedup_*"`.

---

## SLS SQL functions relied on

| Function | Operators | Description |
|----------|-----------|-------------|
| `prompt_simhash(text)` | exact, fuzzy | Compute the SimHash fingerprint of the text |
| `simhash_dedup(sh_array, weight_array, threshold)` | fuzzy | Fuzzy in-batch SimHash dedup |
| `simhash_dedup_with_dataset(sh_array, workspace, dataset, threshold)` | exact (global), fuzzy (global) | Cross-batch SimHash dedup |
| `simhash_dataset_upsert(sh_array, workspace, dataset)` | exact (global), fuzzy (global) | Write SimHash fingerprints into the Dataset |
| `embedding(text, model)` | semantic | Generate a text embedding vector |
| `cosine_similarity(vec1, vec2)` | semantic (batch) | Cosine similarity of two vectors (used by the interim solution) |
| `semhash_dedup(emb_array, id_array, threshold)` | semantic (batch) | In-batch semantic dedup (**not implemented yet**; replaces the `NOT EXISTS` approach once it ships) |
| `semhash_dedup_with_dataset(emb_array, id_array, workspace, dataset, column, threshold)` | semantic (global) | Cross-batch semantic dedup, including the automatic Dataset write |
