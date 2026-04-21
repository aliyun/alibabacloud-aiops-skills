---
title: PolarDB-X Partition Design Best Practices
---

# PolarDB-X Partition Design Best Practices

Partition scheme design is the most critical aspect of using PolarDB-X distributed database, directly impacting system performance, scalability, and cost. This document provides principles for selecting partition keys, partition counts, partition algorithms, as well as GSI creation strategies and safe migration workflows.

## Partition Design Steps Overview

```
1. Collect SQL access pattern data (SQL Insight or alternatives)
2. Analyze SQL templates, calculate query ratio for each field
3. Select partition key
4. Determine whether GSIs are needed and which to create
5. Choose partition algorithm
6. Determine partition count
7. Design migration workflow (ensuring continuity of uniqueness constraints and query performance)
```

## Step 1: Collect SQL Access Patterns

The core basis for partition design is **the table's actual SQL access patterns** — which fields are queried frequently and the read/write ratio. There are several ways to obtain this data:

### Method 1: SQL Insight (Strongly Recommended)

SQL Insight is the most accurate and effortless method, **strongly recommended to enable**.

- Enable via: [SQL Insight Documentation](https://help.aliyun.com/zh/polardb/polardb-for-xscale/sql-explorer)
- If cost is a concern, enable for a period (e.g., one week) to collect data, then disable
- Search for the target table name, sort SQL templates by execution count
- Recommend exporting to CSV for reference
- **Key data**: Execution count, returned rows, read/write ratio for each SQL template

### Method 2: Slow Query Logs + Application Code Analysis

- Review slow query logs via the console to find high-frequency slow queries for the table
- Combine with application code (ORM mappings, DAO layer, SQL files) to catalog all SQL templates for the table
- Annotate each SQL's call frequency (high/medium/low) and read/write type from the code

### Method 3: Business Team Provides SQL Patterns

Have the business development team list all query and write patterns for the table.

> **Note**: This method has the lowest accuracy; actual business scenarios often differ significantly from descriptions. If this is the only option, pay special attention to:
> - List all WHERE condition fields for every SQL
> - Distinguish the approximate QPS level for each SQL (e.g., thousands per second vs. a few per hour)
> - Clarify write operation (INSERT/UPDATE/DELETE) condition fields and frequency

### Data Quality Impact on Partition Design

| Data Source | Accuracy | Impact on Partition Design |
|---------|--------|----------------|
| SQL Insight | Highest | Can precisely quantify each field's query ratio for optimal decisions |
| Slow query + code analysis | Medium | Covers main scenarios but may miss some SQL or misjudge frequency |
| Business team verbal description | Lower | Partition scheme may not be precise enough; monitor and adjust after go-live |

Regardless of method, the goal is to obtain a **SQL template inventory for the table**, including query fields, execution frequency, and returned rows for each template.

## Step 2: Partition Key Selection

### Basic Principles

Partition key selection requires **comprehensive multi-dimensional analysis** — evaluate every candidate field on ALL dimensions below, then choose the one that scores best overall. Do NOT recommend based on a single dimension alone.

1. **Equality query ratio**: The proportion of SQL templates where this field appears as an equality condition (WHERE col = ?)
2. **Cardinality**: The field should have sufficiently many distinct values for even data distribution across partitions
3. **Hotspot risk**: Assess whether a few values dominate a large portion of data. Even a high-cardinality field can have skew (e.g., buyer_id in order tables — some buyers generate far more orders than others)
4. **Primary key / unique key status**: PKs/UKs inherently have the highest cardinality (unique per row), never produce hotspots, and guarantee the most even distribution; selecting them as partition keys also naturally maintains global uniqueness
5. **Semantic analysis**: Infer likely query patterns from the table type and field meaning. For example, order_id in an order table will certainly be queried frequently (order detail lookups, payment callbacks, status checks), even if the user only mentions buyer_id queries

### Analysis Method

From SQL Insight results, evaluate each candidate field:

| Analysis Dimension | Evaluation Method |
|---------|---------|
| Query ratio | Count the proportion of SQL templates with equality conditions on this field |
| Write condition | Whether all UPDATE operations use this field |
| Cardinality | Confirm the field's distinct value count and distribution evenness from a business perspective |
| Hotspot risk | Assess whether a few values dominate a large portion of data |
| PK/UK status | Whether the field is a primary key or unique key (highest cardinality, zero hotspot) |
| Semantic analysis | Infer query patterns from table type and field meaning (e.g., order_id in an order table is certainly queried frequently) |

### Tips for Identifying Hotspots

- Fields whose names contain words like "base", "parent", "group", "type", "category" typically have few distinct values and are prone to hotspots
- Verify data distribution with: `SELECT col, COUNT(*) FROM table GROUP BY col ORDER BY COUNT(*) DESC LIMIT 20;`

### Example Analysis

Using the account table as an example, SQL Insight results show:

| Candidate Field | Equality Query Ratio | Cardinality | Has Hotspots | Is PK/UK |
|---------|------------|--------|----------|-------------|
| account_id | ~33% | Very high (PK) | No | Primary Key |
| base_account_id | ~75% | Low (thousands) | Yes, obvious | No |
| kw_location | ~30% | High | No | No |
| address | ~50% | High | No | No |

**Conclusion**: Although base_account_id has the highest query ratio, its low cardinality and obvious hotspots make it unsuitable as a partition key. account_id as the primary key has the highest cardinality and no hotspots, making it the better partition key.

### Example Analysis 2 — Order Table (nuanced case: both candidates have high cardinality)

The user states "most queries filter by buyer_id, primary key is order_id". Comprehensive multi-dimensional analysis:

| Candidate Field | Equality Query Ratio | Cardinality | Hotspot Risk | Is PK/UK | Semantic Analysis |
|---------|------------|--------|----------|-------------|---------|
| order_id | High — inferred from semantics: order detail lookups, status checks, payment callbacks are core operations of any order system | Highest (PK, unique per row) | None | Primary Key | Core identifier of an order table; query frequency is certainly high |
| buyer_id | High — user explicitly states most queries filter by this | High (millions of buyers) | Potential — some active buyers may generate disproportionately many orders, causing data skew | No | Buyer dimension queries are frequent, but buyer_id distribution depends on business characteristics |

**Comprehensive conclusion**: Both fields have high query ratios. However, order_id scores better on cardinality (unique per row vs. millions of distinct values), hotspot risk (zero vs. potential skew), and PK status. **Recommendation: order_id as partition key + Clustered GSI on buyer_id** to optimize buyer-dimension queries. Always recommend collecting actual SQL access pattern data (SQL Insight or alternatives) to verify the analysis before finalizing.

> **Note**: This is a common pattern where the user mentions only one query dimension. Semantic analysis reveals that other dimensions (order_id lookups) are also frequent. Do not assume that unmentioned fields have low query frequency — always analyze from the table's business semantics.

## Step 3: GSI Selection

### Basic Principles

**Write volume assessment (the core basis for GSI strategy)**:

| Write Volume | GSI Strategy |
|--------|---------|
| Very high (more than half of cluster capacity) | Avoid GSI, consider CO_HASH and other alternatives |
| Not high (vast majority of workloads) | Can freely create GSIs |

> SQL Insight is the most accurate way to assess write volume.

### GSI Type Selection

| Scenario | GSI Type | Reason |
|------|---------|------|
| Few records per value (single digits), few returned rows | Regular GSI | Low table lookback cost, no need to duplicate all columns |
| One-to-many, many records per value | Clustered GSI | Reduces table lookback cost |
| Need to ensure global uniqueness | Global Unique Index (UGSI) | e.g., unique key fields |
| Only a few extra columns needed | Regular GSI + COVERING | More space-efficient than Clustered |

### Fields Unsuitable for GSI

- Fields with very low cardinality (e.g., gender, province — very few distinct values)
- Time/date fields (local indexes usually suffice)

### Composite Query Optimization

If a field **always appears in combination with other fields** in high-frequency SQL and never appears alone, there's no need to create a standalone GSI for it.

### Example Analysis (continued, account table)

- Write volume: thousands per hour, very low compared to queries -> can freely create GSIs
- kw_location: query ratio ~30%, few records per value -> **Regular GSI**
- address: query ratio ~50%, few records per value -> **Regular GSI**
- exchange_account_id: unique key -> **Global Unique Index (UGSI)**
- base_account_id: although query ratio ~75%, it always appears in combination with kw_location or address in high-frequency SQL, never alone -> **Do not create GSI**

### GSI Maintenance

Use the index diagnostic feature (`INSPECT INDEX`) to periodically check for redundant and unused GSIs:
- [Index Diagnostics Documentation](https://help.aliyun.com/zh/polardb/polardb-for-xscale/index-diagnostics)

## Step 4: Partition Algorithm Selection

### Common Partition Algorithms

| Partition Algorithm | Applicable Scenario | Usage Percentage |
|---------|---------|---------|
| Single-level HASH/KEY | Vast majority of workloads | ~90% |
| Single-level CO_HASH | Order-type multi-dimensional queries, high write volume making GSI impractical | Small |
| Single-level HASH + secondary RANGE(time) | Need time-based data cleanup | Small |
| Single-level LIST + secondary HASH | Multi-tenant scenarios | Small |

> PolarDB-X supports 7x7+7=56 partition strategies, but most workloads can choose from the above.
> Detailed documentation: [Partition Strategy Overview](https://help.aliyun.com/zh/polardb/polardb-for-xscale/overview-secondary-partitions)

### Difference Between HASH and KEY

| Scenario | Description |
|------|------|
| Single-field partition key | HASH and KEY are equivalent, either works |
| Multi-field partition key | There are differences, see [documentation](https://help.aliyun.com/zh/polardb/polardb-for-xscale/partition-table-types-and-policies#32d96a8d6c203) |

**Multi-field partition key best practices**:
- Very few workloads need multiple fields as HASH partition keys; pick the one with the highest cardinality from candidates
- Multi-column KEY partition is most common in **hotspot splitting** scenarios: the partition key consists of one business column + primary key, e.g., `PARTITION BY KEY(some_column, pk)`
  - Reference: [Hotspot Splitting Documentation](https://help.aliyun.com/zh/polardb/polardb-for-xscale/hot-data-partition-splitting)

## Step 5: Partition Count Selection

### Basic Principles

1. **256 is appropriate for the vast majority of workloads**
2. Partition count should be **several times the number of DN nodes**; too few can lead to data skew, and scaling may require repartitioning
3. Single partition data volume under 100 million rows provides a better operational experience (DDL duration, etc.)
4. Don't set too many; 256 partitions have been proven to handle billions of rows without issues
5. No need for precise calculation; approximate is fine

## Step 6: Migration Workflow Design

### Single Table to Partitioned Table: How It Works

Converting a single table to a partitioned table is an Online DDL. Core steps:

1. Create a temporary Clustered Global Secondary Index on the original table (partition key is the target partition key)
2. Incremental data is dual-written to both the primary table and temporary GSI via distributed transactions (write RT increases somewhat during migration)
3. Full data is backfilled from the primary table to the temporary GSI (incremental dual-write and full backfill proceed simultaneously; data is consistent once backfill completes)
4. The primary table and temporary GSI are swapped (lock-free operation)
5. The old table is cleaned up after the swap

**Key characteristics**:
- No table locking, the process is Online
- Write performance decreases somewhat during migration
- Long transactions (>=15s) may be interrupted
- Read operations are virtually unaffected

### Uniqueness Constraint Handling

When converting a single table to a partitioned table, unique indexes become local indexes:
- **Includes partition key** -> Remains globally unique after migration
- **Does not include partition key** -> Only unique within partition after migration (risk of data duplication)

> Single tables cannot create global indexes, so you cannot pre-create UGSI on a single table to solve this.

### Choosing a Migration Workflow

The migration workflow depends on whether the table has **unique keys that do not include the partition key**. Check this condition first:

```
Does the table have unique keys (other than PK) that do NOT include the partition key?
  ├── NO  → Use the Standard Two-Step Method (simpler, covers most cases)
  └── YES → Use the Three-Step Method (protects uniqueness constraints)
```

> **Common "NO" scenarios** (use Two-Step): partition key is the primary key and there are no other unique keys; or all unique keys already include the partition key.
>
> **Common "YES" scenarios** (use Three-Step): the table has a unique key on a non-partition-key field (e.g., partition key is `account_id`, but there's a unique key on `exchange_account_id`).

### Standard Two-Step Method

Applicable when there are **no unique keys at risk** — i.e., the partition key is the primary key and there are no other unique keys, or all unique keys already include the partition key.

**Step 1: Convert single table to a partitioned table with the target partition count**

```sql
ALTER TABLE t_order PARTITION BY HASH(order_id) PARTITIONS 256;
```

**Step 2: Create required global indexes**

```sql
CREATE CLUSTERED INDEX cgsi_buyer_id
  ON t_order (buyer_id)
  PARTITION BY KEY(buyer_id) PARTITIONS 256;

CREATE GLOBAL INDEX gsi_seller_id
  ON t_order (seller_id) COVERING(amount, status)
  PARTITION BY KEY(seller_id) PARTITIONS 256;
```

**Rollback Plan**:

| Step | Rollback Action |
|------|---------|
| Step 1 failure | Table is still a single table, no rollback needed |
| Step 2 failure | Drop created GSIs: `DROP INDEX gsi_name ON table_name` |

### Three-Step Method (Protecting Uniqueness Constraints)

Required when the table has **unique keys that do not include the partition key**. The core idea: first convert to a partitioned table with 1 partition (preserving uniqueness), then create GSI/UGSI, finally change to the target partition count.

**Why is this needed?** When converting a single table to a multi-partition table, unique indexes become local indexes. If a unique key does not include the partition key, it can only guarantee uniqueness within each partition, not globally. If you directly convert to the target partition count, there is a window between the partition change and UGSI creation where duplicate data may be written, causing subsequent UGSI creation to fail.

**Step 1: Convert single table to a partitioned table with 1 partition**

```sql
ALTER TABLE account PARTITION BY HASH(account_id) PARTITIONS 1;
```

At this point:
- The table is now a partitioned table and can create global indexes
- With only 1 partition, all unique keys remain globally unique (same as when it was a single table)

**Step 2: Create required global indexes and global unique indexes**

```sql
-- Global Unique Index (ensuring exchange_account_id global uniqueness)
CREATE GLOBAL UNIQUE INDEX ugsi_exchange_account_id
  ON account (exchange_account_id)
  PARTITION BY HASH(exchange_account_id) PARTITIONS 256;

-- Regular Global Index (optimizing address queries)
CREATE GLOBAL INDEX gsi_address
  ON account (address)
  PARTITION BY HASH(address) PARTITIONS 256;

-- Regular Global Index (optimizing kw_location queries)
CREATE GLOBAL INDEX gsi_kw_location
  ON account (kw_location)
  PARTITION BY HASH(kw_location) PARTITIONS 256;
```

At this point, exchange_account_id's uniqueness is guaranteed by the Global Unique Index — uniqueness constraints are never lost throughout the process.

**Step 3: Change to the target partition count**

```sql
ALTER TABLE account PARTITION BY HASH(account_id) PARTITIONS 256;
```

**Rollback Plan**:

| Step | Rollback Action |
|------|---------|
| Step 1 failure | Table is still a single table, no rollback needed |
| Step 2 failure | Drop created GSIs: `DROP INDEX gsi_name ON table_name` |
| Step 3 failure | Revert to 1 partition: `ALTER TABLE account PARTITION BY HASH(account_id) PARTITIONS 1` |

## Complete Example Summary

### Example 1: Order table (no unique keys at risk — Two-Step Method)

```
Original table: Single table t_order
Partition key: order_id (primary key, no other unique keys)
Partition algorithm: HASH
Partition count: 256
Global indexes:
  - Clustered GSI on buyer_id (highest-frequency query optimization)
  - GSI on seller_id + COVERING (lower-frequency query optimization)

Migration workflow (Two-Step):
  1. ALTER TABLE t_order PARTITION BY HASH(order_id) PARTITIONS 256;
  2. CREATE CLUSTERED INDEX cgsi_buyer_id ON t_order(buyer_id) ...;
     CREATE GLOBAL INDEX gsi_seller_id ON t_order(seller_id) COVERING(...) ...;
```

### Example 2: Account table (has unique keys at risk — Three-Step Method)

```
Original table: Single table account
Partition key: account_id (primary key, highest cardinality, no hotspots)
Unique key: exchange_account_id (does NOT include partition key — at risk)
Partition algorithm: HASH
Partition count: 256
Global indexes:
  - UGSI on exchange_account_id (unique key protection)
  - GSI on address (high-frequency query optimization)
  - GSI on kw_location (high-frequency query optimization)

Migration workflow (Three-Step):
  1. ALTER TABLE account PARTITION BY HASH(account_id) PARTITIONS 1;
  2. CREATE GLOBAL UNIQUE INDEX ugsi_exchange_account_id ...;
     CREATE GLOBAL INDEX gsi_address ...;
     CREATE GLOBAL INDEX gsi_kw_location ...;
  3. ALTER TABLE account PARTITION BY HASH(account_id) PARTITIONS 256;
```

## FAQ

**Q: Do only large tables need partitioning?**

No. Tables with high access volume also benefit from partitioning, as it allows more nodes to share the traffic.

**Q: Do partitioned tables support foreign keys?**

Partitioned tables support foreign keys, but it's an experimental feature not recommended for production environments. It's recommended to drop foreign key constraints beforehand.

**Q: Does converting a single table to a partitioned table lock the table?**

No. The migration process is Online.

**Q: Should all queries hit the partition key or GSI?**

No. Partition design is pragmatic work. Low-ratio SQL is not important regardless of how many shards it crosses. When a single-table SQL becomes a cross-shard SQL:
- Response time increase is usually limited (generally within 1x), because queries to each shard are parallelized
- Total cost = per-query cost x QPS; low QPS means limited total cost increase

**Q: Does GSI significantly impact performance? Is it safe to use?**

- For **read-heavy** scenarios, some additional write cost is acceptable
- Even for high write volumes, GSI is the only universal solution for multi-dimensional queries. When there's no other way to implement multi-dimensional queries, use GSI and configure appropriate machine resources

**Q: What is the business impact during migration?**

| Impact | Degree |
|--------|------|
| Read/write IO overhead | Some additional overhead |
| Additional write locks | Yes, minimal impact for read-heavy tables |
| Long transaction (>=15s) interruption risk | Exists |
| Table locking | No |
| Impact on read operations | Virtually none |
