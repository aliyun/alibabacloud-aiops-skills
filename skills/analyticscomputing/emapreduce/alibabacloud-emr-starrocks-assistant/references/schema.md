# StarRocks Table Creation Best Practices

## Required Information Checklist

Before giving recommendations, collect the following information (listed by priority). When something is missing, ask proactively:

| Information | Purpose | Example |
|------|------|------|
| **Business scenario** | Determines the table model | OLAP analysis / real-time updates / log storage / CDC sync |
| **Data volume** | Determines partition granularity and bucket count | 5 million rows/day, 1 billion total, 90-day retention |
| **Query pattern** | Determines sort key and indexes | Point lookup by user_id / time-range aggregation / multi-table JOIN |
| **Primary filter columns** | Determines partition column and sort key | Time, tenant ID, region |
| **Update requirements** | Determines the table model | Append-only / upsert by primary key / partial column updates |
| **Cluster information** | Determines bucket count and replica count | shared-nothing 3 BE / shared-data 10 CN |
| **JOIN requirements** | Whether to use Colocate | Fact table + dimension table frequent JOIN |
| **Existing DDL** (optimization scenarios) | Locate current issues | The user provides an existing CREATE TABLE statement |

## Table Creation Decision Flow

```
Step 1: Choose table model     → Based on update requirements (see schema/table-types.md)
    ↓
Step 2: Design partitioning    → Based on data volume and time dimension (see schema/partitioning.md)
    ↓
Step 3: Design bucketing       → Based on query pattern and data volume (see schema/bucketing.md)
    ↓
Step 4: Design sort key        → Based on high-frequency query filter columns (see schema/sort-key-and-indexes.md)
    ↓
Step 5: Choose indexes         → Based on non-prefix column query requirements (see schema/sort-key-and-indexes.md)
    ↓
Step 6: Set storage properties → Based on performance/space trade-offs (see schema/storage-properties.md)
        On shared-data (存算分离), see the "Shared-data properties" section there for the
        required checklist (storage_volume, datacache.*, persistent_index_type) and the
        properties that are silently stripped or rejected.
```

Detailed rules for each step are in the corresponding reference file; read as needed.

## Table Model Quick Reference

| Scenario | Recommended Model | Key Rationale |
|------|---------|---------|
| Logs / event streams / detail data | **Duplicate Key** | No update requirement, append-only writes, supports Random bucketing |
| Pre-aggregated metrics (PV/UV/GMV) | **Aggregate** | Automatic aggregation reduces storage, queries avoid GROUP BY |
| Real-time upsert / CDC sync | **Primary Key** | Delete+Insert strategy, much better query performance than Unique Key |
| Simple deduplication (no real-time updates) | **Unique Key** | merge-on-read deduplication (use Primary Key directly for new scenarios) |

## Partition and Bucketing Quick Reference

| Data Characteristics | Partitioning Strategy | Bucketing Strategy |
|---------|---------|---------|
| Time-series data (with date column) | `PARTITION BY date_trunc('day', ts)` | `HASH(business ID)` |
| High-frequency write log streams | `PARTITION BY date_trunc('hour', ts)` | `RANDOM` + `bucket_size` |
| Multi-tenant SaaS | Daily partition + tenant in sort key, or `PARTITION BY (tenant_id, region)` (LIST) | `HASH(tenant_id)` |
| Dimension tables (< 10 million rows) | No partitioning | `HASH(primary key)` |
| Very large fact tables + frequent JOIN | `PARTITION BY date_trunc('day', ts)` | `HASH(JOIN key)` + Colocate |
| No clear partition key | No partitioning | `RANDOM` + `bucket_size` |

## Common Anti-Patterns

Proactively check for and avoid these in your table design:

| Anti-Pattern | Consequence | Correct Approach |
|--------|------|---------|
| Picking a low-cardinality column (gender/status) as the bucket column | Data skew, some tablets too large | Pick a high-cardinality column (user_id/order_id) |
| Over-fine partitioning (hourly + 365-day retention) | Massive empty partitions, FE memory pressure | Match granularity to the retention period (day/month) |
| Primary Key too long (>128 bytes) | Index bloat, slower writes | Trim primary key columns; use the shortest combination that uniquely identifies a row |
| Too many sort key columns (>3) | Write performance degrades, prefix index truncated past 36 bytes | Pick the 2-3 most frequently filtered columns |
| Large tables not partitioned | No partition pruning, full table scans | Partition by time or business dimension |
| Tables in the same Colocate group with different bucket counts | Colocate Join no longer works | Tables in the same group must have identical bucket count, bucket key type, and replica count |
| Using FLOAT/DOUBLE for amounts | Precision loss | Use `DECIMAL(p, s)` |
| Using VARCHAR for fixed-length data | Wastes storage, hurts prefix index efficiency | Use `CHAR` for fixed lengths |
| Duplicate Key table using HASH bucketing without a clear query key | Cannot leverage bucket pruning, worse than Random | Switch to `RANDOM` bucketing |

## Reference File Index

When you need the detailed rules for a step, read the corresponding file:

| Topic | Reference File | Contents |
|------|--------------|---------|
| Table model selection | [schema/table-types.md](schema/table-types.md) | Detailed comparison of the four table models, syntax, constraints, selection decision tree |
| Partitioning strategy | [schema/partitioning.md](schema/partitioning.md) | Expression/Range/List/Dynamic partitioning, partition count control |
| Bucketing strategy | [schema/bucketing.md](schema/bucketing.md) | Hash/Random bucketing, bucket count calculation, Colocate Group |
| Sort key and indexes | [schema/sort-key-and-indexes.md](schema/sort-key-and-indexes.md) | Prefix index, ORDER BY, Bitmap/Bloom Filter/full-text indexes |
| Storage properties | [schema/storage-properties.md](schema/storage-properties.md) | Compression, replicas, hot/cold storage tiering, Schema Evolution |

## Output Template

When giving table creation recommendations, use the following structured format:

```markdown
## Table Design

### 1. Table Model: {Duplicate Key / Aggregate / Primary Key / Unique Key}
**Rationale:** {Why this model fits the user's scenario}

### 2. Partitioning Strategy
**Design:** {PARTITION BY ...}
**Rationale:** {Data volume, retention period, pruning benefit}
**Estimated partition count:** {Approximately N partitions}

### 3. Bucketing Strategy
**Design:** {DISTRIBUTED BY HASH(col) BUCKETS N / DISTRIBUTED BY RANDOM}
**Bucket count:** {N} (about {X} GB per tablet)
**Rationale:** {Why this bucket key and count}

### 4. Sort Key and Indexes
**Sort key:** ORDER BY (col1, col2, ...)
**Additional indexes:** {Bitmap / Bloom Filter / None}
**Rationale:** {Which high-frequency query filter conditions this matches}

### 5. Storage Properties
- Compression: {LZ4 / ZSTD / ...}
- Replicas: {N}
- Other: {As needed}

### 6. Full CREATE TABLE Statement

​```sql
CREATE TABLE ...
​```

### 7. Caveats
- {Version requirements, migration notes, follow-up optimization suggestions, etc.}
```
