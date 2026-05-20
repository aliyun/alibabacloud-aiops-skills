# StarRocks SQL Development Guide

## Required Information Checklist

Before giving SQL recommendations, collect the following information. Proactively ask for any missing items:

| Information | Purpose | Example |
|------|------|------|
| **Business requirement** | Understand the query goal | DAU statistics, period-over-period calculation, Top-N ranking, deduplication count |
| **Tables and columns involved** | Write correct SQL | Table names, key columns, table model (Primary Key / Duplicate) |
| **Data size** | Decide optimization strategy | Fact table with 1 billion rows, dimension table with 1 million rows |
| **Query frequency and latency requirements** | Decide whether to use a materialized view | 100 QPS, < 200ms required |
| **Existing SQL (for tuning scenarios)** | Locate performance issues | User provides current SQL |
| **Cluster version** | Determine feature availability | v3.1 / v3.2 / v3.3 |
| **Existing indexes and partition info** | Confirm pruning and index availability | Partition column, sort key, Bitmap index |

## SQL Development Decision Flow

```
Step 1: Understand the requirement -> Clarify the query goal and output format
    |
Step 2: Choose a query pattern -> Simple query / JOIN / subquery / CTE / window function
    |
Step 3: Write SQL -> Follow best practices (see sql/query-writing.md)
    |
Step 4: Choose functions -> Pick functions based on computation needs (see sql/functions-guide.md)
    |
Step 5: Consider acceleration -> Is a materialized view needed (see sql/materialized-views.md)
    |
Step 6: Tune and verify -> EXPLAIN the execution plan (see sql/sql-tuning-checklist.md)
```

## Query Pattern Quick Reference

| Scenario | Recommended pattern | Key rationale |
|------|---------|---------|
| Simple filtering and aggregation | Direct `SELECT ... WHERE ... GROUP BY` | Simplest and most efficient |
| Multi-table JOIN | `JOIN` (prefer Colocate > Shuffle > Broadcast) | Clear semantics; optimizer can optimize |
| Layered, complex queries | `WITH (CTE)` | Better readability; avoids redundant computation |
| Ranking / Top-N | Window function `ROW_NUMBER() OVER(...)` | Supports per-group ranking |
| Period-over-period calculation | `LAG() / LEAD()` window functions | Reference previous/next rows directly |
| Cumulative sum | `SUM() OVER(ORDER BY ... ROWS ...)` | Window aggregation |
| Exact deduplication | `COUNT(DISTINCT col)` | Low-cardinality scenarios (< 10 million) |
| Approximate deduplication (large cardinality) | `APPROX_COUNT_DISTINCT` or `BITMAP` / `HLL` | Billion-level cardinality, error tolerated |
| Unnest / array expansion | `unnest()` / `LATERAL JOIN` | Semi-structured data expansion |
| Accelerate high-frequency repeated queries | Async materialized view | Pre-computation + automatic rewrite |
| Cross-source queries | External Catalog | Federated query against Hive/Iceberg, etc. |

## JOIN Strategy Quick Reference

| Scenario | Recommended strategy | Notes |
|------|---------|------|
| Large table JOIN small table (right side ≤ `broadcast_row_limit`, default 15M rows) | Broadcast Join | Small table broadcast to all BEs |
| Large table JOIN large table | Shuffle Join | Redistribute by JOIN key |
| Frequently joined co-bucketed tables | Colocate Join | Local JOIN, zero network overhead |
| Large table JOIN dimension table (high frequency) | Dictionary + `dict_mapping()` | Sub-second in-memory dictionary lookup |

## StarRocks-specific Anti-Patterns

These are pitfalls that show up under the StarRocks execution model — generic SQL hygiene (`SELECT *`, `NOT IN` NULL semantics, `UNION` vs `UNION ALL`, OFFSET pagination) still applies but is not repeated here.

| Anti-pattern | Consequence | Correct approach |
|--------|------|---------|
| Function on the partition column: `WHERE date_format(dt, '%Y%m') = '202401'` | Partition pruning fails; full table scan | `WHERE dt >= '2024-01-01' AND dt < '2024-02-01'` |
| `COUNT(DISTINCT col)` on billion-level cardinality | Memory blowup, extremely slow | `APPROX_COUNT_DISTINCT` or BITMAP |
| Implicit type conversion `WHERE varchar_col = 123` | Sort-key/zone-map pruning invalidated; full table scan | Match types: `WHERE varchar_col = '123'` |
| Window function `PARTITION BY` a low-cardinality column | Huge per-partition data; memory pressure | Choose a partition column with appropriate cardinality |
| Async MV defined with non-deterministic functions (`now()`, `rand()`) | Refresh produces inconsistent data; query rewrite disabled | Use deterministic expressions; pass time via base-table column |
| Stale statistics on large table → Optimizer mis-chooses Broadcast → OOM | `ANALYZE TABLE` (or wait for auto-collection); verify in `EXPLAIN` |
| `ORDER BY` writes the sort-key prefix wrong (skipped/reordered columns) | Cannot use the sorted scan; extra TopN sort | Match the leading sort-key columns in order |
| Calling `dict_mapping()` against a stale/`UNSTABLE` dictionary | Returns NULL or old values | `SHOW DICTIONARY`; `REFRESH DICTIONARY` |

## Reference File Index

When you need detailed rules on a topic, read the corresponding file:

| Topic | Reference file | Contents |
|------|--------------|---------|
| Query writing | [sql/query-writing.md](sql/query-writing.md) | JOIN/CTE/subquery conventions, WHERE optimization, aggregation optimization |
| Window functions | [sql/window-functions.md](sql/window-functions.md) | Ranking/offset/aggregate window functions, frame definitions, typical scenarios |
| Materialized views | [sql/materialized-views.md](sql/materialized-views.md) | Sync/async MVs, Query Rewrite, refresh strategies, operations |
| Function guide | [sql/functions-guide.md](sql/functions-guide.md) | Aggregate/string/date/JSON/array/BITMAP/HLL functions |
| Advanced features | [sql/advanced-sql.md](sql/advanced-sql.md) | External Catalog, UDF, Resource Group, Dictionary |
| SQL tuning | [sql/sql-tuning-checklist.md](sql/sql-tuning-checklist.md) | Statistics, execution plans, partition pruning, Join tuning, session variables |

## Output Template

When giving SQL recommendations, use the following structured format:

```markdown
## SQL Solution

### 1. Requirement Understanding
**Goal:** {Describe in one sentence what the query should achieve}
**Tables involved:** {Table names and key columns}

### 2. Query Approach
**Pattern:** {Direct query / JOIN / CTE / window function / materialized view}
**Rationale:** {Why this pattern was chosen}

### 3. SQL Statement

​```sql
-- Complete SQL statement, with comments on key parts
​```

### 4. Execution Plan Verification

​```sql
EXPLAIN VERBOSE <your_sql>;
​```

**Check points:**
- Partition pruning: {effective or not}
- JOIN strategy: {Broadcast / Shuffle / Colocate}
- Estimated rows: {reasonable or not}

### 5. Performance Optimization Suggestions
- {Whether statistics need to be updated}
- {Whether a materialized view is needed for acceleration}
- {Session variable adjustment suggestions}

### 6. Caveats
- {Version requirements, known limitations, data type considerations, etc.}
```
