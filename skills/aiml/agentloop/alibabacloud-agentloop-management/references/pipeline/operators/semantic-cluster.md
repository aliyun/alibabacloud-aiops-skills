# semantic-cluster (semantic clustering)

> Cluster data by embedding vector and assign every row the ID of the cluster it
> belongs to.

## Function

Clusters the given embedding-vector column so that semantically close records land in
the same cluster. Every record is assigned a cluster number (`__cluster_id`), and the
input and output row counts match (a 1:1 transformation). The current default
algorithm is KMeans.

Clustering itself does not filter data; it only adds a grouping marker. It is commonly
combined with the downstream `sample` operator to achieve "diversity sampling" — cluster
first, then sample within each cluster. It can also be used on its own for data
distribution analysis and semantic grouping.

**Use cases**:

- Combined with `sample` for downsampling with a diversity guarantee
- Data distribution analysis: observing the size and spread of semantic clusters
- Semantic grouping: bucketing similar records for batch processing or human review
- Clustering quality assessment: checking data diversity before and after
  deduplication or sampling

## Syntax

```
| semantic-cluster -field=<embedding_column> -n=<n_clusters>
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `-field` | Field | **Yes** | - | The embedding-vector column to cluster on; must be `array(double)` |
| `-n` | Integer | **Yes** | - | Number of clusters |

> **Cluster-count guidance**:
>
> | Data volume | Recommended `-n` | Description |
> |-------------|------------------|-------------|
> | < 100 | 5 ~ 10 | A small dataset should not have too many clusters |
> | 100 ~ 1000 | 10 ~ 50 | A medium dataset; adjust as needed |
> | 1000 ~ 10000 | 50 ~ 100 | A large dataset, balancing granularity and performance |
> | > 10000 | 100 ~ 500 | A very large dataset; too many clusters hurts clustering performance |

## Input and output

**Input**:

- Any columns emitted by the upstream operator
- The embedding-vector column named by `-field` must be present with type
  `array(double)`
- Usually placed after `embedding` or `dedup-semantic` (which emits `__dedup_emb`)

**Output**:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| All input columns | — | Input | Every upstream column passes through |
| `__cluster_id` | bigint | Derived | Cluster number (zero-based) |

**Input-to-output relationship**:

M:N (M = N) — a 1:1 transformation; each row gains a cluster marker and no rows are
added or dropped.

## Effect preview

**Before** (6 rows):

| question | __dedup_emb |
|----------|------------|
| What is machine learning? | [0.12, -0.34, …] |
| What types of machine learning are there? | [0.15, -0.30, …] |
| How do I learn Python? | [0.78, 0.23, …] |
| Which Python libraries are available? | [0.75, 0.20, …] |
| What is deep learning? | [-0.11, 0.45, …] |
| What is a neural network? | [-0.09, 0.42, …] |

**After** (6 rows) — `| semantic-cluster -field=__dedup_emb -n=3`:

| question | __dedup_emb | __cluster_id |
|----------|------------|-------------|
| What is machine learning? | [0.12, -0.34, …] | 0 |
| What types of machine learning are there? | [0.15, -0.30, …] | 0 |
| How do I learn Python? | [0.78, 0.23, …] | 1 |
| Which Python libraries are available? | [0.75, 0.20, …] | 1 |
| What is deep learning? | [-0.11, 0.45, …] | 2 |
| What is a neural network? | [-0.09, 0.42, …] | 2 |

> The row count is unchanged (6 → 6) and every row gains a `__cluster_id`.
> Semantically close records are assigned to the same cluster. Follow up with
> `sample -n=1 by __cluster_id` to take one row per cluster for diversity sampling.

## Examples

### Example 1: basic clustering

```
* | project question,input,output,question_embedding
  | semantic-cluster -field=question_embedding -n=10
```

Clusters the data into 10 clusters by `question_embedding`, giving every row a
`__cluster_id`.

### Example 2: clustering plus grouped sampling (diversity sampling)

```
* | project question,input,output,question_embedding
  | semantic-cluster -field=question_embedding -n=100
  | sample -n=1 by __cluster_id
```

Clusters into 100 clusters and takes one row per cluster, producing roughly 100
diverse representative samples. Equivalent to the L5 cluster-sampling logic of the
original pipeline.

### Example 3: three-stage dedup → clustering → sampling

```
* | project question,input,output
  | dedup-exact -field=question
  | dedup-fuzzy -field=question -threshold='3'
  | dedup-semantic -field=question -threshold='0.1'
  | semantic-cluster -field=__dedup_emb -n=100
  | sample -n=1 by __cluster_id
```

Reuses the `__dedup_emb` column emitted by `dedup-semantic` for clustering, avoiding
a second embedding computation.

### Example 4: clustering analysis only (no sampling)

```
* | project question,input,output
  | embedding -field=question
  | semantic-cluster -field=question_embedding -n=20
```

Adds only the cluster labels, for observing the semantic distribution of the data.

---

> **Everything below this line is the internal implementation spec, aimed at the
> development and engineering teams. Hide it when publishing user documentation.**

## Design notes

- **Clustering algorithm**: currently fixed to KMeans. The `cluster` function supports
  other algorithms (DBSCAN, for example), so an `-algorithm` parameter can be added
  later.
- **Relationship with `sample`**: `semantic-cluster` handles group labeling (1:1) and
  `sample` handles filtering and downsampling (M:N). The two compose orthogonally to
  produce "diversity sampling". Splitting them keeps each operator atomic:
  `semantic-cluster` can be used alone for analysis and `sample` alone for random
  sampling.
- **Synergy with dedup-semantic**: `dedup-semantic` emits the `__dedup_emb` column
  (the embedding vector), and `semantic-cluster` can consume that column directly as
  its `-field` input, avoiding a second embedding computation. This is the recommended
  combination.
- **Synthetic row identifier (`__cl_rid`)**: the assignments array returned by the
  clustering function corresponds element-by-element to the input array. The operator
  generates the internal row ID `__cl_rid` via `row_number() OVER ()` and uses it to
  join the clustering result back to the original data. The `_cl_base` CTE is
  materialized exactly once during SQL execution, so `__cl_rid` stays stable for the
  lifetime of the CTE.
- **`-n` is required**: the user states the cluster count explicitly, which avoids the
  cognitive load of an implicit computation. If the right cluster count is unclear,
  consult the guidance table or use the rule of thumb
  `ceil(row count × desired sampling rate)`.
- **Internal column**: `__cl_rid` is an internal synthetic row ID; it exists in the
  output as an implementation byproduct and is not a formal derived column. The engine
  may strip it during post-processing.

## SQL implementation template

### Standard mode

```sql
set session enable_remote_functions = true;
WITH
-- Step 1: materialize the input plus a synthetic row identifier
_cl_base AS (
    SELECT 
        row_number() OVER () AS __cl_rid
        ##otherColumns##
    FROM ##sourceTable##
),
-- Step 2: KMeans clustering
_cl_result AS (
    SELECT 
        cluster(
            array_agg({{field}}), 'kmeans', 
            concat('{"n_clusters":"', cast({{n}} as varchar), '"}')
        ) as cluster_res, 
        array_agg(__cl_rid) as rid_array 
    FROM _cl_base
),
-- Step 3: expand the clustering result into (label, rid) pairs
_cl_assignments AS (
    SELECT label, rid 
    FROM _cl_result, UNNEST(cluster_res.assignments, rid_array) AS t(label, rid) 
),
-- Step 4: join back to the original data and attach the cluster ID
_cl_output AS (
    SELECT 
        cast(m1.label as bigint) AS __cluster_id,
        m2.*
    FROM _cl_assignments m1
    JOIN _cl_base m2 ON m1.rid = m2.__cl_rid
)
-- Output
SELECT * FROM _cl_output
```

## Template variables

| Template variable | Parameter | Default | Description |
|-------------------|-----------|---------|-------------|
| `{{field}}` | `-field` | - | The embedding-vector column name |
| `{{n}}` | `-n` | - | Number of clusters |
| `##sourceTable##` | Resolved by the engine | - | The upstream CTE name or base query table |
| `##otherColumns##` | Derived by the engine | - | Pass-through macro for non-derived columns; commas and duplicate column names are handled automatically afterwards |

## Dependent functions

| Signature | Description |
|-----------|-------------|
| `cluster(emb_array, algorithm, params_json) → ROW(assignments array(integer), ...)` | The clustering function, currently using KMeans. `n_clusters` inside `params_json` sets the cluster count |

## Edge cases

| Case | Handling |
|------|----------|
| The `-field` column does not exist | The engine raises a parameter-validation error |
| The `-field` type is not `array(double)` | The engine raises a type-validation error, noting that an embedding-vector column is required |
| The input is empty (0 rows) | An empty result set is returned normally |
| The input has only 1 row | One cluster with one record, `__cluster_id = 0` |
| `-n` exceeds the row count | Handled by the `cluster` function, usually capped at the row count or reported as an error |
| `-n` ≤ 0 | The engine raises a parameter-validation error |
| The embedding dimensions are inconsistent | The `cluster` function raises an error about mismatched vector dimensions |
