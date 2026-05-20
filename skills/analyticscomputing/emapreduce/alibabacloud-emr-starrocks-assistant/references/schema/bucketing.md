# Detailed Bucketing Strategy Guide

## Table of Contents

1. [Bucketing Overview](#bucketing-overview)
2. [Hash Bucketing](#hash-bucketing)
3. [Random Bucketing](#random-bucketing)
4. [Choosing Bucket Count](#choosing-bucket-count)
5. [Colocate Group](#colocate-group)
6. [Selection Decision](#selection-decision)

---

## Bucketing Overview

Bucketing further splits the data inside each Partition into Tablets (data shards). Each Tablet is the smallest unit of data management and scheduling in StarRocks.

**Core roles of bucketing:**
- Determines the physical distribution of data across BE nodes
- Affects query parallelism (each Tablet can be processed by a single thread)
- Affects write throughput (number of Tablets = upper bound of write parallelism)

**Two bucketing strategies:**
- **Hash bucketing**: Assigns to Tablets based on the hash value of the specified columns; rows with the same hash always end up in the same Tablet
- **Random bucketing**: Distributes data randomly across Tablets; writes are even but there is no locality

---

## Hash Bucketing

**Syntax:**
```sql
DISTRIBUTED BY HASH(column1[, column2, ...]) [BUCKETS num]
```

**Principles for choosing bucket columns:**

| Principle | Description | Counter-example |
|------|------|------|
| **High cardinality** | NDV (number of distinct values) should be much larger than the bucket count; recommend ≥ 1000 × number of BEs | gender (only 2 values), status (few enum values) |
| **Query filter column** | Pick a column used in WHERE equality conditions to enable bucket pruning | Picking a column that queries never use |
| **JOIN key** | For Colocate Join, the bucket column must be a column in JOIN ON | JOIN key and bucket key do not match |
| **Even distribution** | Data is evenly distributed on this column to avoid hot Tablets | user_id, but 90% of rows belong to the same user |

**Bucket pruning example:**
```sql
-- Bucket column is user_id
-- The following query can scan only 1 Tablet (bucket pruning takes effect)
SELECT * FROM orders WHERE user_id = 12345;

-- The following query must scan all Tablets (bucket pruning does not apply)
SELECT * FROM orders WHERE user_id > 10000;
```

**Multi-column bucketing:**
```sql
DISTRIBUTED BY HASH(user_id, order_date) BUCKETS 32
```
- Multi-column hashing can improve data dispersion
- But all bucket columns must appear in WHERE simultaneously for bucket pruning
- Single-column bucketing is generally recommended unless a single column lacks cardinality

**Full example:**
```sql
CREATE TABLE user_orders (
    order_id BIGINT NOT NULL,
    user_id INT NOT NULL,
    order_date DATE NOT NULL,
    product_id INT,
    quantity INT,
    amount DECIMAL(12,2)
)
PRIMARY KEY(order_id, order_date, user_id)
PARTITION BY date_trunc('day', order_date)
DISTRIBUTED BY HASH(user_id) BUCKETS 32
ORDER BY (user_id, order_date)
PROPERTIES ("enable_persistent_index" = "true");
```

---

## Random Bucketing

**Version:** RANDOM bucketing introduced in **v3.1+**; `bucket_size` auto-split in **v3.2+**. Not available on v2.5.

**Syntax:**
```sql
DISTRIBUTED BY RANDOM [BUCKETS num]
```

**Core characteristics:**
- Random data distribution; writes are perfectly balanced
- No bucket pruning (every query scans all Tablets)
- No Colocate Join support
- Only supports Duplicate Key tables

**Auto-Split (v3.2+):**
```sql
-- After enabling bucket_size, Tablets automatically split by size
DISTRIBUTED BY RANDOM
PROPERTIES ("bucket_size" = "1073741824")  -- Each Tablet splits after reaching 1 GB
```

**Full example:**
```sql
CREATE TABLE nginx_access_log (
    log_time DATETIME NOT NULL,
    request_method VARCHAR(8),
    request_path VARCHAR(512),
    status_code INT,
    response_time_ms INT,
    client_ip VARCHAR(64),
    user_agent VARCHAR(512)
)
DUPLICATE KEY(log_time, request_method)
PARTITION BY date_trunc('hour', log_time)
DISTRIBUTED BY RANDOM
PROPERTIES (
    "bucket_size" = "1073741824",
    "compression" = "ZSTD"
);
```

**When to choose Random:**
- Append-only Duplicate Key tables for logs/event streams
- No clear high-frequency equality query column
- Write throughput is the priority and Colocate is not needed
- Data volume is uncertain and you want Tablets to grow automatically

---

## Choosing Bucket Count

### Automatic (recommended)

From v2.5.7+, omitting the `BUCKETS` clause lets StarRocks calculate the bucket count automatically:

```sql
-- Automatic bucket count
DISTRIBUTED BY HASH(user_id)
-- Equivalent to omitting BUCKETS; StarRocks calculates based on partition data volume and number of BEs
```

### Manual

**Goal: 1–10 GB per Tablet**

| Information | Calculation |
|------|---------|
| Single-partition data volume | Daily increment × replica count (e.g., 3 replicas for shared-nothing) |
| Tablet count | Single-partition data volume / target Tablet size (recommend 1–5 GB) |
| Lower bound | ≥ Number of BE nodes (ensure each BE has at least 1 Tablet) |
| Upper bound | Avoid Tablets that are too small (< 100 MB wastes resources) |

**Rule of thumb:**
```
BUCKETS = MAX(number of BEs, CEIL(single-partition data volume in GB / target Tablet size in GB))

Example:
- 3 BEs, 30 GB daily increment (3 replicas = 90 GB physical)
- Target Tablet size 3 GB
- BUCKETS = MAX(3, CEIL(90/3)) = 30
```

**Common scale reference:**

| BE Count | Daily Data Volume | Recommended Bucket Count | Notes |
|-------|----------|---------|------|
| 3 | < 1 GB | 3-8 | At least equal to the number of BEs |
| 3 | 1-10 GB | 8-16 | |
| 3 | 10-100 GB | 16-48 | |
| 10 | 10-100 GB | 16-64 | |
| 10 | 100 GB - 1 TB | 48-128 | |
| 50+ | > 1 TB | 128-256 | Large-scale clusters |

**Dynamic growth (v3.2+, Random bucketing only):**
```sql
PROPERTIES ("bucket_size" = "1073741824")  -- 1 GB
```
- New partitions start with a small number of Tablets and split automatically as data grows
- Suitable when data volume is uncertain or grows rapidly

---

## Colocate Group

**Purpose:** Schedule data with the same hash value across multiple tables to the same BE nodes, enabling local JOIN (no network shuffle).

**Syntax:**
```sql
-- Create a Colocate group (the first table defines the CGS)
CREATE TABLE fact_orders (
    order_id BIGINT,
    user_id INT NOT NULL,
    dt DATE NOT NULL,
    amount DECIMAL(12,2)
)
DUPLICATE KEY(order_id, user_id, dt)
PARTITION BY date_trunc('day', dt)
DISTRIBUTED BY HASH(user_id) BUCKETS 32
PROPERTIES ("colocate_with" = "order_group");

-- Join the same Colocate group (must match the CGS)
CREATE TABLE fact_payments (
    payment_id BIGINT,
    user_id INT NOT NULL,
    dt DATE NOT NULL,
    pay_amount DECIMAL(12,2)
)
DUPLICATE KEY(payment_id, user_id, dt)
PARTITION BY date_trunc('day', dt)
DISTRIBUTED BY HASH(user_id) BUCKETS 32  -- Must use the same bucket count!
PROPERTIES ("colocate_with" = "order_group");
```

**Colocate Group Schema (CGS) constraints:**

All tables joining the same Colocate group must satisfy:

| Property | Requirement |
|------|------|
| Bucket key type | Exactly the same (type, count, and order) |
| Bucket count | Exactly the same |
| Replica count | Exactly the same |
| Same database | Yes |

> Note: The bucket column names can differ, but their data types and positions must match.

**View Colocate group status:**
```sql
SHOW PROC '/colocation_group';
```
- `IsStable = true`: Colocate Join works normally
- `IsStable = false`: Tablets are being repaired/migrated; Colocate Join falls back to a regular Join

**Management operations:**
```sql
-- Move a table to another Colocate group
ALTER TABLE fact_orders SET ("colocate_with" = "new_group");

-- Remove from the Colocate group
ALTER TABLE fact_orders SET ("colocate_with" = "");
```

**Limitations:**
- Cannot be used together with Random bucketing
- Cannot be used on temporary tables
- Spark Load is not supported for ingesting into Colocate tables

---

## Selection Decision

```
Does the query have a clear equality filter column?
├── Yes → Is that column's cardinality high enough (>= 1000 × number of BEs)?
│   ├── Yes → Is Colocate Join needed?
│   │   ├── Yes → HASH(JOIN key) + colocate_with (unified across all related tables)
│   │   └── No → HASH(filter column) BUCKETS N
│   └── No → Is there a column combination that raises cardinality?
│       ├── Yes → HASH(col1, col2)
│       └── No → RANDOM (if Duplicate Key table)
│                → HASH(highest-cardinality column) (non Duplicate Key table)
└── No → Is the table type Duplicate Key?
    ├── Yes → RANDOM + bucket_size (recommended)
    └── No → HASH(first primary key column or highest-cardinality column)
```

**Quick reference:**

| Scenario | Bucketing Strategy | Rationale |
|------|---------|------|
| E-commerce orders, queried by user_id | `HASH(user_id)` | Bucket pruning + high cardinality |
| Nginx logs | `RANDOM` + `bucket_size` | No clear query key, even writes |
| Fact table JOIN dimension table | `HASH(join_key)` + Colocate | Local JOIN eliminates Shuffle |
| User table synced via CDC | `HASH(user_id)` | Primary Key table queried by primary key |
| IoT sensor data | `HASH(device_id)` | Queried by device |
| Small dimension tables | `HASH(primary_key)` | Set the bucket count to the minimum |
