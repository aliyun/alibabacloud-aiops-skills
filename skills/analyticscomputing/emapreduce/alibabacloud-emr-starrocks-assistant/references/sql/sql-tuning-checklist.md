# SQL Tuning Checklist

## Table of Contents

1. [Collecting Statistics](#collecting-statistics)
2. [Reading Execution Plans](#reading-execution-plans)
3. [Verifying Partition Pruning](#verifying-partition-pruning)
4. [Tuning Join Strategies](#tuning-join-strategies)
5. [Verifying Predicate Pushdown](#verifying-predicate-pushdown)
6. [Low-Cardinality Dictionary Optimization](#low-cardinality-dictionary-optimization)
7. [Tuning Pipeline DOP](#tuning-pipeline-dop)
8. [Common Session Variables](#common-session-variables)
9. [Tuning Checklist Summary](#tuning-checklist-summary)

---

## Collecting Statistics

Statistics are the foundation that lets the CBO (cost-based optimizer) make correct decisions. Stale or missing statistics cause the optimizer to pick a wrong execution plan.

### View Statistics Status

```sql
-- View table-level statistics
SHOW TABLE STATS table_name;
-- Watch Updated_time for staleness (older than 1 day needs an update)

-- View column-level statistics
SHOW COLUMN STATS table_name;
-- Watch NDV (number of distinct values), MIN, MAX, NULL ratio
```

### Collect Statistics

```sql
-- Sampling collection (recommended, fast)
ANALYZE TABLE table_name;

-- Full collection (more precise but slow)
ANALYZE FULL TABLE table_name;

-- Collect for specific columns
ANALYZE TABLE table_name (col1, col2);

-- Collect histograms (for columns with data skew)
ANALYZE TABLE table_name UPDATE HISTOGRAM ON col1, col2;

-- Drop statistics
DROP STATS table_name;
```

### Auto-Collection Configuration

```sql
-- View auto-collection status
SHOW ANALYZE STATUS;

-- Auto-collection is driven by FE background tasks. Related settings:
-- enable_statistic_collect = true         -- enable auto-collection
-- statistic_auto_collect_interval = 300   -- check interval (seconds)
-- statistic_collect_interval_sec = 14400  -- minimum collection interval (seconds)
```

### When to Collect Manually

| Scenario | Action |
|------|------|
| After a large bulk load | `ANALYZE TABLE` |
| Execution plan clearly unreasonable (e.g., Broadcast of a large table) | `ANALYZE TABLE` and retry |
| After a table schema change | `ANALYZE TABLE` |
| After first ingestion into a newly created table | `ANALYZE TABLE` |
| Data distribution has changed significantly | `ANALYZE TABLE UPDATE HISTOGRAM ON ...` |

---

## Reading Execution Plans

### Basic Workflow

```sql
-- 1. View the execution plan
EXPLAIN VERBOSE <your_sql>;

-- 2. Pay attention to the following operators (read bottom-up)
-- OlapScanNode -> HashJoinNode -> AggregateNode -> SortNode -> ExchangeNode -> ResultSink
```

### Key Operators

#### OlapScanNode (Local Table Scan)

```
SCAN OLAP table_name
  partitions=3/365           <- partition pruning: 3 hit / 365 total
  rollup: mv_name            <- hit sync materialized view (rollup)
  tabletRatio=10/30          <- bucket pruning
  cardinality=1000000        <- CBO estimated rows (large deviation from actual = stale statistics)
  avgRowSize=128.0           <- average row size
  predicates: dt >= '2024-01-01'  <- predicate pushed down to the storage layer
```

**Check points:**
- `partitions` denominator much greater than the numerator -> partition pruning works
- `partitions` numerator equals the denominator -> partition pruning not applied; check the WHERE conditions
- `tabletRatio` numerator equals the denominator -> bucket pruning not applied (all tablets scanned)
- `rollup` shows an MV name -> materialized view hit
- `cardinality` is the **CBO's row estimate**. Compare it **directly** to the user-stated total table size to get the staleness ratio; a ratio > 10× means stats are stale.

**How to compute the cardinality / stale-stats ratio (read this carefully):**

Use **`cardinality` vs the user-provided total table row count**, as a direct ratio. Example: prompt says "actual table size ~500M", `cardinality=5000000` → `500M / 5M = 100×` → stats are stale by ~100×, run `ANALYZE TABLE`.

**Do NOT** try to estimate "how many rows the predicate should filter to" and compare against that guess. Two reasons:
1. You don't have runtime row counts — only the user's stated totals and the optimizer's estimate.
2. Guessing predicate selectivity from a `WHERE` clause (e.g. assuming `create_time > '2025-04-01'` matches "about one month of data") introduces order-of-magnitude errors and is unrelated to the diagnostic task. The job is to flag stats staleness, not to model selectivity.

**Independent diagnostic signals — must be reported separately:**
`partitions`/`tabletRatio` (plan-level pruning) and `cardinality` (statistics freshness) are **orthogonal**. When both look bad in the same plan (e.g. `partitions=365/365` AND `cardinality` diverges from the total table size by 10×–100×), you must list them as **two independent findings**, each with its own root cause and fix. Do **not** use cardinality deviation to "explain" pruning failure, and do not let pruning failure absorb the stale-stats finding — they need different remediations (rewrite predicate / fix type vs. `ANALYZE TABLE`). Always quantify the cardinality gap explicitly using the direct comparison (e.g. "estimate 5M vs total 500M ≈ 100×").

#### HashJoinNode

```
HASH JOIN
  join op: INNER JOIN
  distribution type: BROADCAST    <- distribution strategy
  equal join conjunct: a.id = b.id
  cardinality=5000000
```

**Check points:**
- BROADCAST on a large table -> verify the right-hand table is actually small (check cardinality)
- Should be COLOCATE but shows SHUFFLE -> check Colocate Group configuration
- BROADCAST between two large tables -> statistics may be stale; retry after ANALYZE

#### ExchangeNode

```
EXCHANGE
  distribution type: SHUFFLE       <- data redistribution type
  partition exprs: order_id
```

**Check points:**
- Many SHUFFLEs -> check if Colocate Join can eliminate them
- UNPARTITIONED -> data is funneled to a single node; may become a bottleneck

---

## Verifying Partition Pruning

### How to Check

```sql
-- In EXPLAIN output, check the partitions field of OlapScanNode
EXPLAIN VERBOSE SELECT * FROM events WHERE dt = '2024-01-15';

-- Correct: partitions=1/365 (scans only 1 partition)
-- Abnormal: partitions=365/365 (scans all partitions)
```

### Common Causes of Pruning Failure

| Cause | Example | Fix |
|------|------|---------|
| Function wraps the partition column | `WHERE YEAR(dt) = 2024` | `WHERE dt >= '2024-01-01' AND dt < '2025-01-01'` |
| Expression computation | `WHERE dt + 1 = '2024-01-16'` | `WHERE dt = '2024-01-15'` |
| Implicit type conversion | Partition column is DATE, condition uses a string | Ensure types match |
| OR condition spans partitions | `WHERE dt = '2024-01-15' OR user_id = 1` | Split into UNION ALL |
| Condition uses a non-partition column | `WHERE user_id = 12345` (partition column is dt) | Add a condition on the partition column |

---

## Tuning Join Strategies

### Judging Whether a Join Strategy Is Reasonable

```sql
EXPLAIN VERBOSE <join_query>;
-- Inspect the distribution type of HashJoinNode
```

### Tuning Methods

| Current strategy | Issue | Tuning method |
|---------|------|---------|
| BROADCAST but right-hand table is large | Broadcasting a large table causes OOM | 1. `ANALYZE TABLE` to update statistics<br>2. `SET broadcast_row_limit = N` to limit broadcast rows |
| SHUFFLE but COLOCATE is possible | Unnecessary network transfer | Ensure both tables are in the same Colocate Group |
| BROADCAST but want to force SHUFFLE | Specific scenario requires SHUFFLE | `JOIN [shuffle] table ON ...` |
| COLOCATE not actually applied | Colocate Group configuration mismatch | Verify bucket count, bucket key types, and replica count match |

### Colocate Join Prerequisites

```sql
-- 1. Both tables must be in the same Colocate Group
-- 2. Bucket key columns must match in count, type, and order
-- 3. Bucket count (BUCKETS) must be identical
-- 4. Replica count must match
-- 5. JOIN condition must include all bucket key columns

-- Check Colocate status
SHOW PROC '/colocation_group';
```

---

## Verifying Predicate Pushdown

### How to Check

```sql
EXPLAIN VERBOSE <query>;
-- Inspect the predicates field of OlapScanNode
-- Conditions appearing in predicates = pushed down to the storage layer
```

### Common Causes of Pushdown Failure

| Cause | Example | Fix |
|------|------|---------|
| Cross-table predicate | `WHERE a.x + b.y > 10` | Split into single-table conditions |
| WHERE condition on outer-table side of an OUTER JOIN | LEFT JOIN with a WHERE on the right table | Move into the ON clause |
| Non-aggregate condition in HAVING | `HAVING status = 'A'` | Move into WHERE |

---

## Low-Cardinality Dictionary Optimization

StarRocks automatically enables dictionary encoding optimization for low-cardinality string columns (e.g., status, region, gender), using integer IDs in place of string operations across Scan/Shuffle/Join/Aggregate stages.

```sql
-- Enabled automatically; usually no manual configuration needed
-- To verify: check the DictDecode-related metrics
-- in the Query Profile

-- If you suspect low-cardinality optimization isn't applied:
SET global_dict_columns = 'col1, col2';  -- specify manually

-- Disable (for troubleshooting)
SET enable_low_cardinality_optimize = false;
```

---

## Tuning Pipeline DOP

DOP (Degree of Parallelism) controls a query's parallelism.

```sql
-- View the current DOP
SHOW VARIABLES LIKE 'pipeline_dop';
-- Default 0 = automatic (CPU cores / 2)

-- Set manually
SET pipeline_dop = 8;  -- fixed parallelism

-- Temporarily adjust for a single query
SELECT /*+ SET_VAR(pipeline_dop=4) */ ...
```

### DOP Tuning Recommendations

| Scenario | Suggested DOP |
|------|---------|
| Default | 0 (auto) |
| High-concurrency small queries (QPS > 100) | 1-2 (lower per-query parallelism, improve concurrency) |
| Low-concurrency large queries | CPU core count (fully utilize resources) |
| Mixed workload | Combine with Resource Group isolation |

---

## Common Session Variables

### Query Behavior

| Variable | Default | Description |
|------|--------|------|
| `query_timeout` | 300 | Query timeout (seconds) |
| `query_mem_limit` | 0 | Per-query memory limit (0 = unlimited) |
| `pipeline_dop` | 0 | Parallelism (0 = auto) |
| `parallel_fragment_exec_instance_num` | 1 | Parallel instance count per BE |

### Optimizer Control

| Variable | Default | Description |
|------|--------|------|
| `broadcast_row_limit` | 10000000 | Broadcast Join row limit |
| `new_planner_agg_stage` | 0 | Aggregation stages (0 = auto, 1 = single-stage, 2 = two-stage) |
| `enable_materialized_view_rewrite` | true | Whether to enable MV rewrite |
| `cbo_max_reorder_node_use_exhaustive` | 4 | Use exhaustive ordering for Joins with fewer than this count |
| `disable_join_reorder` | false | Disable Join reorder |

### Resource Control

| Variable | Default | Description |
|------|--------|------|
| `resource_group` | '' | Specify the resource group |
| `enable_spill` | false | Allow intermediate results to spill to disk |
| `spill_mem_table_size` | 100MB | Memory buffer size before spilling |

### Viewing and Setting

```sql
-- View all variables
SHOW VARIABLES;

-- View a specific variable
SHOW VARIABLES LIKE '%timeout%';

-- Set a session-level variable (current connection only)
SET query_timeout = 600;

-- Set a global variable (affects all new connections)
SET GLOBAL query_timeout = 600;
```

---

## Tuning Checklist Summary

Run the following checks in order of priority:

| # | Check | Command | Expected outcome |
|---|--------|------|---------|
| 1 | Are statistics fresh | `SHOW TABLE STATS t` | Updated_time < 24h |
| 2 | Is partition pruning effective | `EXPLAIN`, view partitions | numerator << denominator |
| 3 | Is bucket pruning effective | `EXPLAIN`, view tabletRatio | numerator << denominator |
| 4 | Is the Join strategy reasonable | `EXPLAIN`, view distribution type | Large table not BROADCAST |
| 5 | Are predicates pushed down | `EXPLAIN`, view predicates | Conditions appear in ScanNode |
| 6 | Is the MV hit | `EXPLAIN`, view rollup / table | MV name shown |
| 7 | Are estimated rows accurate | `EXPLAIN`, view cardinality | Deviation from actual < 10x |
| 8 | Is DOP reasonable | Profile or SHOW VARIABLES | Matches workload |
| 9 | Is memory sufficient | query_mem in Profile | Not near mem_limit |
| 10 | Any spill | spill metrics in Profile | No spill or acceptable |

### Three-Step Tuning Method

```
1. EXPLAIN -> identify issues (pruning failed, wrong strategy, row-count deviation)
2. ANALYZE -> refresh statistics so the optimizer can make correct choices
3. SET_VAR / Hint -> fine-tune optimizer behavior (last resort)
```
