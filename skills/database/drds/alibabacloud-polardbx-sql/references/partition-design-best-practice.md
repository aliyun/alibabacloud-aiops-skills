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

1. **Higher equality query ratio is better**: The proportion of SQL templates where this field appears as an equality condition (WHERE col = ?)
2. **Higher cardinality is better**: The field should have sufficiently many distinct values with no obvious hotspots on certain values
3. **Primary key/unique key bonus**: Primary keys and unique keys inherently have the highest cardinality, never produce hotspots, and have the most even distribution; selecting them as partition keys naturally maintains global uniqueness

### Analysis Method

From SQL Insight results, evaluate each candidate field:

| Analysis Dimension | Evaluation Method |
|---------|---------|
| Query ratio | Count the proportion of SQL templates with equality conditions on this field |
| Write condition | Whether all UPDATE operations use this field |
| Cardinality | Confirm the field's distinct value count and distribution evenness from a business perspective |
| Hotspot risk | Assess whether a few values dominate a large portion of data |

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

### When to Use Direct Migration vs. Three-Step Method

Choose the migration approach based on whether the table has unique indexes on non-partition-key columns:

| Scenario | Approach |
|----------|----------|
| Partition key = primary key, **no** other unique indexes | **Direct migration**: ALTER to target partitions, then create GSI |
| Table has unique indexes on **non-partition-key** columns | **Three-step method**: 1 partition → create UGSI → target partitions |

**Direct migration example** (partition key = primary key, no other unique constraints):

```sql
-- order_id is both PK and partition key, buyer_id/seller_id are not unique → safe to migrate directly
ALTER TABLE t_order PARTITION BY KEY(order_id) PARTITIONS 256;

CREATE CLUSTERED INDEX cg_i_buyer ON t_order (buyer_id)
  PARTITION BY KEY(buyer_id) PARTITIONS 256;
CREATE GLOBAL INDEX g_i_seller ON t_order (seller_id)
  PARTITION BY KEY(seller_id) PARTITIONS 256;
```

### Three-Step Method (When Non-Partition-Key Unique Indexes Exist)

> **Applicable when**: The table has unique indexes on columns other than the partition key (e.g., unique constraint on exchange_account_id while partitioning by account_id).

**Core idea**: First convert to a partitioned table with 1 partition (preserving uniqueness), then create GSI/UGSI, finally change to the target partition count.

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

### Rollback Plan

Each step should have a rollback plan in case of issues:

| Step | Rollback Action |
|------|---------|
| Step 1 failure | Table is still a single table, no rollback needed |
| Step 2 failure | Drop created GSIs: `DROP INDEX gsi_name ON table_name` |
| Step 3 failure | Revert to 1 partition: `ALTER TABLE account PARTITION BY HASH(account_id) PARTITIONS 1` |

### Risks of Direct Migration

If you directly execute `ALTER TABLE ... PARTITION BY HASH(account_id) PARTITIONS 256` and then create GSIs:
- During the interval between ALTER PARTITION and CREATE GSI, unique keys that don't include the partition key cannot guarantee global uniqueness
- Duplicate data may be written during this interval, causing subsequent UGSI creation to fail
- Duplicate data must be cleaned up before UGSI can be created

## Complete Example Summary

Using the account table as an example:

```
Original table: Single table
Partition key: account_id (primary key, highest cardinality, no hotspots)
Partition algorithm: HASH
Partition count: 256
Global indexes:
  - UGSI on exchange_account_id (unique key protection)
  - GSI on address (high-frequency query optimization)
  - GSI on kw_location (high-frequency query optimization)

Migration workflow:
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
