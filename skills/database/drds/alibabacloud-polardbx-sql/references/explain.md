---
title: PolarDB-X EXPLAIN Execution Plan Diagnostics
---

# PolarDB-X EXPLAIN Execution Plan Diagnostics

PolarDB-X provides a rich set of EXPLAIN command variants for viewing and analyzing SQL execution plans. Unlike MySQL, PolarDB-X execution plans are divided into two layers: **CN (Compute Node) logical plans** and **DN (Data Node) physical plans**.

## Full Syntax

```sql
EXPLAIN {option} <SQL statement>
```

Supported options: `LOGICALVIEW` | `LOGIC` | `SIMPLE` | `DETAIL` | `EXECUTE` | `PHYSICAL` | `OPTIMIZER` | `SHARDING` | `COST` | `ANALYZE` | `BASELINE` | `JSON_PLAN`

## Common Options

### EXPLAIN (Default)

View the CN layer logical execution plan:

```sql
EXPLAIN SELECT * FROM t_order WHERE buyer_id = 12345;
```

Key parameters in the output:
- `HitCache`: Whether PlanCache was hit (true/false).
- `TemplateId`: Globally unique identifier for the query plan.
- `Source`: Plan source (e.g., PLAN_CACHE).
- `WorkloadType`: Workload type (e.g., TP, AP).

### EXPLAIN EXECUTE

View the physical execution plan pushed down to DN (similar to MySQL's EXPLAIN), for quickly diagnosing index usage:

```sql
EXPLAIN EXECUTE SELECT * FROM t_order WHERE buyer_id = 12345;
```

Aggregates execution plan information from all DNs by default, with differences noted in the Extra column:
- `Same plan` / `Different plan` indicates whether execution plans are consistent across DNs.
- `Scan rows` shows scan row count statistics.

### EXPLAIN ANALYZE

Actually executes the SQL and collects runtime statistics (note: this will actually execute the query):

```sql
EXPLAIN ANALYZE SELECT * FROM t_order WHERE buyer_id = 12345;
```

Outputs additional `rowCount`, execution time, and other runtime information for comparing estimated vs. actual row counts.

### EXPLAIN SHARDING

View the shard scan pattern of a query on DNs to determine if a full-shard scan is occurring:

```sql
EXPLAIN SHARDING SELECT * FROM t_order WHERE buyer_id = 12345;
```

If all shards are being scanned, the query condition does not hit the partition key — consider adding a GSI.

### EXPLAIN COST

View cost estimation for each operator and WORKLOAD type identification:

```sql
EXPLAIN COST SELECT * FROM t_order WHERE buyer_id = 12345;
```

### EXPLAIN PHYSICAL

View execution mode, Fragment dependencies, and parallelism:

```sql
EXPLAIN PHYSICAL SELECT * FROM t_order WHERE buyer_id = 12345;
```

## DN-Level EXPLAIN Variants

Requires a newer version (polardb-2.5.0_5.4.20+).

### EXPLAIN DIFF_EXECUTE

Shows only DN execution plans with differences, for quickly locating problematic DNs:

```sql
EXPLAIN DIFF_EXECUTE SELECT * FROM t_order WHERE buyer_id = 12345;
```

### EXPLAIN ALL_EXECUTE

Shows detailed execution plans for all DNs:

```sql
EXPLAIN ALL_EXECUTE SELECT * FROM t_order WHERE buyer_id = 12345;
```

### EXPLAIN TREE_EXECUTE

Displays DN execution plans in a tree structure:

```sql
EXPLAIN TREE_EXECUTE SELECT * FROM t_order WHERE buyer_id = 12345;
```

### EXPLAIN JSON_EXECUTE

Outputs DN optimizer information in JSON format:

```sql
EXPLAIN JSON_EXECUTE SELECT * FROM t_order WHERE buyer_id = 12345;
```

### EXPLAIN ANALYZE_EXECUTE

Actually executes the SQL and shows DN-level execution statistics:

```sql
EXPLAIN ANALYZE_EXECUTE SELECT * FROM t_order WHERE buyer_id = 12345;
```

## HINT Assistance

```sql
-- View DN execution plans at the physical sub-table level
/*+TDDL:EXPLAIN_EXECUTE_PHYTB_LEVEL=2*/
EXPLAIN EXECUTE SELECT * FROM t_order WHERE buyer_id = 12345;
```

## Diagnostic Recommendations

- If `EXPLAIN` shows a full-shard scan, check whether the query condition includes the partition key or GSI key.
- If `EXPLAIN EXECUTE` shows `Different plan`, data skew may be causing some DNs to choose different execution plans.
- If estimated row counts differ significantly from actual row counts, consider running `ANALYZE TABLE` to refresh statistics.
- If `EXPLAIN SHARDING` shows too many shards being scanned, consider optimizing the partition strategy or adding a GSI.
