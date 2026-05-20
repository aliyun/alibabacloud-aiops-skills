# Detailed Table Model Guide

## Table of Contents

1. [Duplicate Key Table](#duplicate-key-table)
2. [Aggregate Table](#aggregate-table)
3. [Unique Key Table](#unique-key-table)
4. [Primary Key Table](#primary-key-table)
5. [Selection Decision Tree](#selection-decision-tree)
6. [Unique Key → Primary Key](#unique-key-primary-key)

---

## Duplicate Key Table

**Applicable scenarios:** Logs, event streams, detail data, append-only writes without update requirements.

**Core characteristics:**
- Allows duplicate rows; pure append-only writes
- The default StarRocks table type
- Supports Random bucketing (v3.1+), suitable for log scenarios with no clear query key
- Best query performance (no merge overhead)

**Syntax example:**

```sql
-- Basic usage
CREATE TABLE event_log (
    event_time DATETIME NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    user_id BIGINT,
    page_url VARCHAR(256),
    duration INT
)
DUPLICATE KEY(event_time, event_type)
PARTITION BY date_trunc('day', event_time)
DISTRIBUTED BY RANDOM
PROPERTIES ("bucket_size" = "1073741824");

-- Specify the sort key (v3.3+ supports an ORDER BY different from DUPLICATE KEY)
CREATE TABLE access_log (
    dt DATE NOT NULL,
    user_id BIGINT NOT NULL,
    action VARCHAR(32),
    ip VARCHAR(64),
    response_time INT
)
DUPLICATE KEY(dt, user_id)
ORDER BY (user_id, dt)
PARTITION BY date_trunc('day', dt)
DISTRIBUTED BY HASH(user_id) BUCKETS 32;
```

**Relationship between DUPLICATE KEY and ORDER BY:**
- Before v3.3: The sort key is determined by DUPLICATE KEY columns; the two are equivalent
- From v3.3: ORDER BY can be independent of DUPLICATE KEY; ORDER BY determines the physical storage order

**When to choose:**
- Data is append-only, never updated or deleted
- Need to retain all raw detail
- Logs, tracking events, behavioral events, and similar scenarios

---

## Aggregate Table

**Applicable scenarios:** Pre-aggregated metrics (PV, UV, total amount); queries are primarily GROUP BY.

**Core characteristics:**
- Multiple rows with the same key columns are automatically aggregated into one row
- Reduces storage and scan volume at query time
- Does not retain detail data

**Supported aggregate functions:**

| Function | Purpose | Value Column Type |
|------|------|---------|
| `SUM` | Sum | Numeric types |
| `MAX` | Maximum | Numeric/date |
| `MIN` | Minimum | Numeric/date |
| `REPLACE` | Replace with the latest value | Any type |
| `REPLACE_IF_NOT_NULL` | Replace when not NULL | Any type |
| `HLL_UNION` | Approximate distinct count | HLL type |
| `BITMAP_UNION` | Exact distinct count | BITMAP type |
| `PERCENTILE_UNION` | Percentile merge | PERCENTILE type |

**Syntax example:**

```sql
CREATE TABLE daily_stats (
    dt DATE NOT NULL,
    site_id INT NOT NULL,
    city VARCHAR(32) NOT NULL,
    pv BIGINT SUM DEFAULT "0",
    uv BITMAP BITMAP_UNION,
    max_duration INT MAX DEFAULT "0",
    revenue DECIMAL(18,2) SUM DEFAULT "0"
)
AGGREGATE KEY(dt, site_id, city)
PARTITION BY date_trunc('day', dt)
DISTRIBUTED BY HASH(site_id) BUCKETS 16;
```

**Limitations:**
- Value columns cannot be used as WHERE filters (they have been aggregated)
- Bitmap indexes are not supported on value columns
- Cannot query original detail data

**When to choose:**
- Queries always GROUP BY the same dimensions
- Acceptable to lose detail
- Need extreme query performance and storage efficiency

---

## Unique Key Table

**Applicable scenarios:** Deduplication by primary key (legacy; recommend Primary Key for new scenarios).

**Core characteristics:**
- Merge-on-Read: merges multiple versions at query time, keeping the latest
- Extra query overhead (merge required)
- Equivalent to an Aggregate table with REPLACE aggregation on all value columns

**Syntax example:**

```sql
CREATE TABLE orders (
    order_id BIGINT NOT NULL,
    create_time DATE NOT NULL,
    order_state INT,
    total_price DECIMAL(12,2)
)
UNIQUE KEY(order_id, create_time)
PARTITION BY date_trunc('day', create_time)
DISTRIBUTED BY HASH(order_id) BUCKETS 32;
```

**Why it is not recommended:**
- Query performance is 3-10x worse than Primary Key (merge-on-read vs delete+insert)
- Does not support partial column updates
- Primary Key is better across every dimension

**When to choose:**
- You already have a Unique Key table running stably and are not migrating yet
- For new scenarios, always recommend Primary Key

---

## Primary Key Table

**Applicable scenarios:** Real-time updates, CDC sync, and OLTP-to-OLAP scenarios with frequent upserts.

**Core characteristics:**
- Delete+Insert strategy, no merge-on-read overhead
- Supports partial column updates (Partial Update)
- Query performance close to Duplicate Key
- Persistent primary key index with controlled memory footprint

**Syntax example:**

```sql
CREATE TABLE realtime_orders (
    order_id BIGINT NOT NULL,
    dt DATE NOT NULL,
    merchant_id INT NOT NULL,
    user_id INT NOT NULL,
    status TINYINT,
    amount DECIMAL(12,2),
    update_time DATETIME
)
PRIMARY KEY (order_id, dt, merchant_id)
PARTITION BY date_trunc('day', dt)
DISTRIBUTED BY HASH(merchant_id) BUCKETS 32
ORDER BY (dt, merchant_id)
PROPERTIES (
    "enable_persistent_index" = "true"
);
```

**Primary key constraints:**
- The primary key must include the partition column and the bucket column
- Maximum primary key length: 128 bytes (can be raised via `primary_key_limit_size`, but not recommended)
- Primary key columns only support: BOOLEAN, TINYINT, SMALLINT, INT, BIGINT, LARGEINT, DATE, DATETIME, VARCHAR/STRING
- FLOAT, DOUBLE, and DECIMAL are not supported as primary key columns

**Persistent index types:**

| Type | Configuration | Applicable Scenario |
|------|------|---------|
| In-memory (not recommended) | `enable_persistent_index = false` | Sufficient memory and small data volume |
| Local disk | `enable_persistent_index = true` + `persistent_index_type = LOCAL` | shared-nothing cluster (recommended) |
| Cloud-native | `persistent_index_type = CLOUD_NATIVE` | shared-data cluster (recommended) |

**Primary key index memory estimation formula:**
```
Memory usage ≈ (primary_key_size + 8) × row_count × 50%
```
- `primary_key_size`: Sum of bytes of all primary key columns
- `8`: Internal pointer per row
- `50%`: Memory optimization coefficient for the persistent index (hot data cache ratio)

**Partial column update:**
```sql
-- Update only the status and update_time columns
UPDATE realtime_orders 
SET status = 3, update_time = now() 
WHERE order_id = 12345 AND dt = '2024-01-01' AND merchant_id = 100;
```

**When to choose:**
- Data needs upsert (insert or update)
- CDC real-time sync from MySQL/PostgreSQL
- Need partial column updates
- Need real-time row deletion

---

## Selection Decision Tree

```
Does the data need updates/deletes?
├── No → Need pre-aggregation?
│   ├── Yes → Aggregate table
│   └── No → Duplicate Key table
└── Yes → Primary Key table
    (Unless you already have a Unique Key table running stably, Unique Key is no longer recommended)
```

**Detailed comparison:**

| Dimension | Duplicate Key | Aggregate | Unique Key | Primary Key |
|------|:---:|:---:|:---:|:---:|
| Append writes | Best | Good | Good | Good |
| Upsert | Not supported | Not supported | Supported | Best |
| Partial column update | Not supported | Not supported | Not supported | Supported |
| Delete | Not supported | Not supported | Not supported | Supported |
| Query performance | Best | Good (less data after aggregation) | Poor (merge-on-read) | Good |
| Write performance | Best | Good | Good | Good (low persistent-index overhead) |
| Random bucketing | Supported (v3.1+) | Not supported | Not supported | Not supported |
| Storage efficiency | Retains all detail | Best (after aggregation) | Average | Good |
| Applicable versions | All versions | All versions | All versions | v2.4+ (recommend v3.0+) |

---

## Migration Guide

### Unique Key → Primary Key

```sql
-- Original Unique Key table
CREATE TABLE orders_old (
    order_id BIGINT,
    dt DATE,
    status INT,
    amount DECIMAL(12,2)
) UNIQUE KEY(order_id, dt)
DISTRIBUTED BY HASH(order_id) BUCKETS 32;

-- Migrate to a Primary Key table
CREATE TABLE orders_new (
    order_id BIGINT NOT NULL,
    dt DATE NOT NULL,
    status INT,
    amount DECIMAL(12,2)
) PRIMARY KEY(order_id, dt)
DISTRIBUTED BY HASH(order_id) BUCKETS 32
PROPERTIES ("enable_persistent_index" = "true");

-- Migrate the data
INSERT INTO orders_new SELECT * FROM orders_old;
```

**Migration caveats:**
- Primary Key columns must be declared `NOT NULL`
- The primary key must include the partition column and the bucket column
- Validate query performance improvements in a test environment first
- After migration, you can take advantage of new features such as partial column updates
