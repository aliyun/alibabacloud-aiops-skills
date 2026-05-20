# Detailed Partitioning Strategy Guide

## Table of Contents

1. [Partitioning Overview](#partitioning-overview)
2. [Expression Partition (Recommended)](#expression-partition)
3. [Range Partition](#range-partition)
4. [List Partition](#list-partition)
5. [Dynamic Partition](#dynamic-partition)
6. [Partition Count Control](#partition-count-control)
7. [When Not to Partition](#when-not-to-partition)

---

## Partitioning Overview

Partitioning splits table data into subsets (Partitions) by column values; each Partition is managed independently. Core benefits:
- **Query pruning**: When WHERE conditions hit the partition column, only the relevant partitions are scanned
- **Lifecycle management**: Automatically clean up expired data via partition TTL or Dynamic Partition
- **Parallel ingestion**: Different partitions can be written in parallel without interfering with each other

**Principles for choosing partition columns:**
- Prefer a time column (the most common filter dimension)
- Columns that frequently appear in query WHERE conditions
- Columns with a natural monotonically increasing characteristic over time

---

## Expression Partition

**Recommended for most scenarios.** Partitions that do not yet exist are created automatically at ingest time; no manual DDL is required.

**Syntax:**

```sql
-- Automatic daily partitioning (most common)
PARTITION BY date_trunc('day', event_time)

-- Automatic hourly partitioning (high-frequency write scenarios)
PARTITION BY date_trunc('hour', event_time)

-- Automatic monthly partitioning (historical / cold data)
PARTITION BY date_trunc('month', event_time)

-- Automatic yearly partitioning
PARTITION BY date_trunc('year', event_time)
```

**Full CREATE TABLE example:**

```sql
CREATE TABLE user_behavior (
    event_time DATETIME NOT NULL,
    user_id BIGINT,
    action VARCHAR(32),
    item_id BIGINT,
    amount DECIMAL(10,2)
)
DUPLICATE KEY(event_time, user_id)
PARTITION BY date_trunc('day', event_time)
DISTRIBUTED BY HASH(user_id) BUCKETS 32;
```

> Expression partitioning accepts **only one partition column**. Mixing `date_trunc(...)` with other columns (e.g. `PARTITION BY (tenant_id, date_trunc('day', dt))`) is **not supported** in any version through 3.5. For tenant+time use LIST partitioning on the tenant column, or put tenant in the sort key with daily expression partitioning.

**Advantages:**
- No need to pre-create partitions; created automatically at ingest time
- Lower operational burden
- Supports DATE/DATETIME columns
- v3.4+: also supports `time_slice()` and direct column reference (`PARTITION BY dt`)

---

## Range Partition

Manually define partition boundaries. Suitable for scenarios that need precise control over partition ranges.

**Syntax 1: VALUES LESS THAN (open right boundary)**

```sql
PARTITION BY RANGE (dt) (
    PARTITION p20240101 VALUES LESS THAN ("2024-01-02"),
    PARTITION p20240102 VALUES LESS THAN ("2024-01-03"),
    PARTITION p20240103 VALUES LESS THAN ("2024-01-04")
)
```

**Syntax 2: Fixed range (left-closed, right-open)**

```sql
PARTITION BY RANGE (dt) (
    PARTITION p202401 VALUES [("2024-01-01"), ("2024-02-01")),
    PARTITION p202402 VALUES [("2024-02-01"), ("2024-03-01")),
    PARTITION p202403 VALUES [("2024-03-01"), ("2024-04-01"))
)
```

**Syntax 3: Batch creation**

```sql
-- Batch creation by month
PARTITION BY RANGE (dt) (
    START ("2024-01-01") END ("2025-01-01") EVERY (INTERVAL 1 MONTH)
)

-- Batch creation by day
PARTITION BY RANGE (dt) (
    START ("2024-01-01") END ("2024-04-01") EVERY (INTERVAL 1 DAY)
)

-- Numeric partitioning
PARTITION BY RANGE (age) (
    START ("0") END ("100") EVERY ("10")
)
```

**When to choose Range over Expression:**
- Need uneven partition intervals (e.g., monthly for history, daily for recent data)
- Need a MAXVALUE catch-all partition
- The partition column is not a time type

---

## List Partition

**Version:** v3.0+ introduced; stable from v3.1+. Not available on v2.5.

Partition by discrete values; suitable for enumerated dimensions.

**Automatic creation syntax (recommended):**

```sql
-- Automatic partitioning by city
PARTITION BY (city)

-- Multi-column List partitioning
PARTITION BY (country, city)
```

**Manual definition syntax:**

```sql
PARTITION BY LIST (region) (
    PARTITION p_cn VALUES IN ("cn-shanghai", "cn-beijing", "cn-hangzhou"),
    PARTITION p_us VALUES IN ("us-east", "us-west"),
    PARTITION p_eu VALUES IN ("eu-west", "eu-central")
)
```

**When to choose:**
- Queries filter by enumerated dimensions such as tenant/region/business line
- Data has clear classification dimensions
- Different partitions may have different lifecycles

---

## Dynamic Partition

Automatically creates future partitions and deletes expired ones, reducing operational burden.

**Core properties:**

| Property | Required | Description | Example |
|------|------|------|------|
| `dynamic_partition.enable` | No | Switch, default true | `"true"` |
| `dynamic_partition.time_unit` | Yes | Granularity | `DAY` / `HOUR` / `WEEK` / `MONTH` / `YEAR` |
| `dynamic_partition.start` | No | Number of historical days to retain (negative); no deletion by default | `"-30"` |
| `dynamic_partition.end` | Yes | Number of future days to pre-create (positive) | `"3"` |
| `dynamic_partition.prefix` | No | Partition name prefix, default "p" | `"p"` |
| `dynamic_partition.buckets` | No | Bucket count per partition; defaults to the table-level setting | `"32"` |
| `dynamic_partition.history_partition_num` | No | Number of historical partitions to create, default 0 | `"0"` |
| `dynamic_partition.replication_num` | No | Replica count for new partitions; defaults to the table-level setting | `"3"` |
| `dynamic_partition.start_day_of_week` | No | Starting day for WEEK granularity, 1=Monday, default 1 | `"1"` |
| `dynamic_partition.start_day_of_month` | No | Starting day for MONTH granularity, 1-28, default 1 | `"1"` |

**Full example:**

```sql
CREATE TABLE site_access (
    event_day DATE NOT NULL,
    site_id INT,
    city VARCHAR(32),
    pv BIGINT DEFAULT "0"
)
DUPLICATE KEY(event_day, site_id, city)
PARTITION BY RANGE(event_day) ()  -- Initially no partitions; Dynamic Partition creates them automatically
DISTRIBUTED BY HASH(site_id) BUCKETS 32
PROPERTIES (
    "dynamic_partition.enable" = "true",
    "dynamic_partition.time_unit" = "DAY",
    "dynamic_partition.start" = "-30",
    "dynamic_partition.end" = "3",
    "dynamic_partition.prefix" = "p",
    "dynamic_partition.buckets" = "32"
);
```

**Partition naming rules:**
- DAY → `p20240101`
- HOUR → `p2024010108` (requires a DATETIME column, not DATE)
- WEEK → `p2024_01` (week 1)
- MONTH → `p202401`
- YEAR → `p2024`

**Check interval:** FE parameter `dynamic_partition_check_interval_seconds`, default 600 seconds.

**Modify an existing table:**
```sql
ALTER TABLE site_access SET (
    "dynamic_partition.start" = "-60",
    "dynamic_partition.end" = "7"
);
```

> Note: Dynamic Partition applies only to Range Partition tables. Expression Partition creates partitions automatically by nature, so Dynamic Partition is not needed.

---

## Partition Count Control

**Key constraints:**

| Metric | Recommended Upper Limit | Consequence If Exceeded |
|------|---------|---------|
| Total partitions per table | < 100,000 | FE metadata memory pressure |
| Data volume per partition | ≤ 100 GB | Affects compaction and recovery if too large |
| Tablets per partition | ≤ 20,000 (including replicas) | Too many tablets increase scheduling overhead |
| Typical partition count range | 10² ~ 10⁴ | Balances pruning effectiveness and metadata overhead |

**Granularity selection reference:**

| Granularity | Applicable Scenario | Partitions per Year | Advantages | Risks |
|------|---------|----------|------|------|
| **Day** (default recommendation) | Most BI/reporting scenarios | ~365 | Moderate query pruning precision, convenient TTL management | Not precise enough for "last 3 hours" pruning |
| **Hour** | Daily increment > 2 tablets' capacity; IoT high-frequency writes | ~8,760 | Hotspot isolation, precise pruning | Partition count grows fast; pair with a short retention period |
| **Month** | Historical archives, long retention periods (year-scale) | 12 | Very little metadata | Coarse pruning precision |
| **Year** | Extremely long historical data | 1 | Suitable for scenarios that only query by year | A single partition may grow too large |

**Rule of thumb:**
```
Estimated partition count = retention days / partition granularity in days

Example: 90-day retention, daily partitioning → 90 partitions (healthy)
Example: 365-day retention, hourly partitioning → 8,760 partitions (on the high side, prefer daily)
```

---

## When Not to Partition

You may skip partitioning in the following cases:
- Dimension tables (total data volume < 10 million rows / < 10 GB)
- Configuration tables, dictionary tables, and other static small tables
- Tables without a time dimension or natural partition key

When not partitioned, the entire table acts as a single partition; queries scan all tablets.
