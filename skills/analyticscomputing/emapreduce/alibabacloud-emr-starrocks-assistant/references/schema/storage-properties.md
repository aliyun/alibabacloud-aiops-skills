# Detailed Storage Properties Guide

## Table of Contents

1. [Compression Algorithms](#compression-algorithms)
2. [Replicas and Write Strategy](#replicas-and-write-strategy)
3. [Storage Media and Hot/Cold Storage Tiering](#storage-media-and-hotcold-storage-tiering)
4. [Fast Schema Evolution](#fast-schema-evolution)
5. [Compaction Control](#compaction-control)
6. [Hybrid Row-Column Storage](#hybrid-row-column-storage)
7. [Other Useful Properties](#other-useful-properties)

---

## Compression Algorithms

**Configuration:**
```sql
PROPERTIES ("compression" = "algorithm name")
```

| Algorithm | Compression Ratio | Speed | Applicable Scenario |
|------|-------|------|---------|
| **LZ4** (default) | Medium | Fastest | Most scenarios; prioritizes query performance |
| **ZSTD** | High | Fairly fast | Storage-space sensitive, cold data, log tables |
| **zlib** | Highest | Slowest | Extreme storage optimization (impacts query performance) |
| **Snappy** | Low | Fast | Compatibility needs |

**ZSTD level configuration (v3.1.8+):**
```sql
-- Levels 1-22; higher numbers give higher compression but slower speed; default 3
PROPERTIES ("compression" = "zstd(3)")
```

**Selection recommendations:**
- Online query tables → **LZ4** (default is fine)
- Log/archive tables with infrequent queries → **ZSTD**
- Extremely storage-cost sensitive → **ZSTD(9)** or **zlib**
- Generally no change is needed; LZ4 is a safe default

---

## Replicas and Write Strategy

### Replica Count

```sql
PROPERTIES ("replication_num" = "3")  -- Default 3
```

| Configuration | Applicable Scenario |
|------|---------|
| `3` (default) | Production environments, ensures high availability |
| `1` | Dev/test environments; shared-data clusters (data is redundant in object storage) |
| `2` | Rarely used |

### Write Acknowledgement Strategy

```sql
PROPERTIES ("write_quorum" = "MAJORITY")
```

| Strategy | Meaning | Applicable Scenario |
|------|------|---------|
| `MAJORITY` (default) | Return success once the majority of replicas have written | Production environments (recommended) |
| `ONE` | Return success once any replica succeeds | Write performance priority (risk of data loss) |
| `ALL` | Return success only after all replicas succeed | Extremely strict data consistency |

### Replica Sync Mode

```sql
PROPERTIES ("replicated_storage" = "true")
```

| Mode | Meaning | Default by Version |
|------|------|---------|
| `true` | Single-Leader write, synced to Followers (low CPU usage) | v3.0+ (recommended) |
| `false` | All replicas write independently (high CPU usage) | v2.5 |

---

## Storage Media and Hot/Cold Storage Tiering

### Storage Media

```sql
PROPERTIES (
    "storage_medium" = "SSD",           -- Initially stored on SSD
    "storage_cooldown_ttl" = "7 DAY"    -- Migrate to HDD after 7 days
)
```

### Cooldown Strategy

| Property | Description |
|------|------|
| `storage_medium` | `SSD` or `HDD` |
| `storage_cooldown_ttl` | Cool down after partition upper-bound time + TTL (e.g., `"30 DAY"`) |
| `storage_cooldown_time` | Cool down at an absolute time (e.g., `"2025-06-01 00:00:00"`) |

**Limitations:**
- Only applies to Range / List partitioned tables
- The partition column must be a date type
- Primary Key tables do not support hot/cold storage tiering
- **Silently ignored in shared-data** — `PropertyAnalyzer` strips both `storage_cooldown_time` and `storage_cooldown_ttl` when `RunMode.isSharedDataMode()` is true. Use `datacache.partition_duration` (see *Shared-data properties* below) for the equivalent effect.

**Full example:**
```sql
CREATE TABLE hot_cold_table (
    dt DATE NOT NULL,
    user_id BIGINT,
    data VARCHAR(256)
)
DUPLICATE KEY(dt, user_id)
PARTITION BY date_trunc('day', dt)
DISTRIBUTED BY HASH(user_id) BUCKETS 16
PROPERTIES (
    "storage_medium" = "SSD",
    "storage_cooldown_ttl" = "7 DAY",
    "replication_num" = "3"
);
```

---

## Shared-data (存算分离) properties

Shared-data clusters keep data files in object storage and cache hot data on CN local disk. This changes which `PROPERTIES` are meaningful at `CREATE TABLE`.

### Properties to **set**

| Property | Values | Default | Version | Purpose |
|---|---|---|---|---|
| `storage_volume` | volume name (string) | the cluster's default volume | v3.1+ | Which object-storage backend the table writes to; omit to use the cluster default |
| `datacache.enable` | `true` / `false` | `true` | v3.1+ | Local-disk cache for hot reads; leave on unless intentionally bypassing |
| `datacache.partition_duration` | e.g. `"7 DAY"`, `"3 MONTH"`, `"12 HOUR"` | unset (cache evicts purely by LRU) | v3.1+ | Treat partitions whose upper bound is within this window as hot — they stay cached and are reloaded if evicted. **Set this to match the user's stated query window** (e.g. "queries the last 90 days" → `"90 DAY"`). Setting it smaller than the query window means in-window queries miss the cache; do not default to a generic "hot window" like 30 days when the user has given a concrete number. |
| `enable_persistent_index` | `true` / `false` | `true` (PK tables) | — | Required for Primary Key tables; persists the PK index across restarts |
| `persistent_index_type` | `LOCAL` / `CLOUD_NATIVE` | v3.2: `LOCAL`; v3.3+: `CLOUD_NATIVE` on shared-data | v3.1.4+ (LOCAL), v3.3+ (CLOUD_NATIVE on object storage) | `CLOUD_NATIVE` stores the PK index on object storage — survives CN rebalance without rebuild; the right default for shared-data |

### Properties to **omit** (and why)

| Property | What happens |
|---|---|
| `enable_async_write_back` | **Disabled since v3.1.4** — setting it (any value) throws `AnalysisException: enable_async_write_back is disabled since version 3.1.4` |
| `storage_cooldown_time` / `storage_cooldown_ttl` | Silently stripped in shared-data; use `datacache.partition_duration` instead |
| `storage_medium` | Meaningless on shared-data — there's no SSD/HDD tier choice; the cache disk is what it is |
| `replicated_storage` | Single-leader replication is a shared-nothing concept; not applicable |

### Properties that **still apply but behave differently**

- `replication_num`: not ignored — `PropertyAnalyzer` validates it against the **CN node count** (not BE). Defaults to 3 cluster-wide; lower it if you have fewer CNs than 3.
- `fast_schema_evolution`: defaults to `true` on shared-data v3.3+; you do not need to set it.

### Minimal Primary-Key-on-shared-data checklist (v3.3+)

```sql
CREATE TABLE orders (
    order_id  BIGINT NOT NULL,
    user_id   BIGINT,
    create_time DATETIME NOT NULL,
    amount    DECIMAL(18,2),
    status    VARCHAR(32)
)
PRIMARY KEY (order_id, create_time)
PARTITION BY date_trunc('day', create_time)
DISTRIBUTED BY HASH(order_id) BUCKETS 12
ORDER BY (create_time, order_id)
PROPERTIES (
    -- "storage_volume"             = "my_oss_vol",   -- omit to use cluster default
    "datacache.enable"              = "true",
    "datacache.partition_duration"  = "90 DAY",       -- last 90 days stays in cache
    "enable_persistent_index"       = "true",
    "persistent_index_type"         = "CLOUD_NATIVE", -- v3.3+ default; explicit for clarity
    "compression"                   = "LZ4"
);
```

---

## Fast Schema Evolution

**Function:** Accelerates ADD/DROP COLUMN operations and reduces resource usage.

```sql
PROPERTIES ("fast_schema_evolution" = "true")
```

| Version | Default |
|------|-------|
| v3.2+ (shared-nothing) | `false` (must be enabled manually) |
| v3.3+ (shared-data) | `true` (enabled by default) |

**Effects when enabled:**
- ADD COLUMN: Completes in seconds, no need to rewrite data files
- DROP COLUMN: Marked for deletion, cleaned up asynchronously in the background

**Recommendation:** Enable for tables whose columns change frequently.

---

## Compaction Control

### Forbidden Compaction Windows

```sql
PROPERTIES (
    "base_compaction_forbidden_time_ranges" = "* 8-20 * * *"
)
```

**Format:** Quartz cron (minute hour day month day-of-week)

| Configuration | Meaning |
|------|------|
| `"* 8-20 * * *"` | Forbid Base Compaction daily from 8:00 to 20:59 |
| `"* 0-6 * * 1-5"` | Forbid weekdays from midnight to 6 a.m. |

**Applicable scenarios:**
- Avoid Compaction competing for IO during daytime business peaks
- Note: During the forbidden window, at most 500 ingestion operations are allowed (Cumulative Compaction still runs)

### Compaction-Related Properties

```sql
-- Partition TTL (v3.1.7+): automatically delete expired partitions
PROPERTIES ("partition_ttl" = "90 DAY")

-- Equivalent to the start parameter of Dynamic Partition, but more concise
```

---

## Hybrid Row-Column Storage

**Version:** v3.2.3+ (Preview feature)

**Purpose:** Support efficient columnar analytical queries and row-based point lookups simultaneously.

**Prerequisites:**
```sql
-- FE configuration
ADMIN SET FRONTEND CONFIG ("enable_experimental_rowstore" = "true");
```

**Syntax:**
```sql
CREATE TABLE user_profile (
    user_id BIGINT NOT NULL,
    name VARCHAR(64),
    email VARCHAR(128),
    age INT,
    balance DECIMAL(12,2)
)
PRIMARY KEY(user_id)
DISTRIBUTED BY HASH(user_id) BUCKETS 16
PROPERTIES ("store_type" = "column_with_row");
```

**Applicable scenarios:**
- Tables with both primary-key point lookups (SELECT * WHERE id = ?) and analytical aggregation queries
- API services and reporting analytics sharing a single table

**Limitations:**
- Only supports Primary Key tables
- Row data is stored in the hidden column `__row`, adding storage overhead
- Maximum 1 MB per row
- v3.2.4+ supports BITMAP, HLL, JSON, ARRAY, MAP, STRUCT types

---

## Other Useful Properties

### StarRocks-specific column types

| Type | When to use |
|------|---------|
| `HLL` | Approximate `COUNT(DISTINCT)` with O(1) memory; combine with `hll_union_agg()` |
| `BITMAP` | Exact `COUNT(DISTINCT)` on integer / dictionary-encoded keys; combine with `bitmap_union_count()` |
| `PERCENTILE` | Pre-aggregated percentile state for Aggregate tables; query via `percentile_approx_raw()` |
| `JSON` | Native binary JSON; faster than `VARCHAR` for `->`/`json_query()` extraction |
| `ARRAY<T>` / `MAP<K,V>` / `STRUCT` | Multi-value / nested fields; query with `[idx]`, `element_at()`, `unnest()` |
| `agg_state(<func>)` | (v3.1+) Pre-aggregated state column on Aggregate tables; finalize via `<func>_union` / `<func>_merge` |

### Table-Level Comment

```sql
CREATE TABLE my_table (...)
COMMENT "Business purpose description"
PROPERTIES (...);
```

### Per-Partition Bucket Override

```sql
-- Different partitions can have different bucket counts (only when manually creating Range Partitions)
PARTITION BY RANGE(dt) (
    PARTITION p_old VALUES LESS THAN ("2024-01-01") DISTRIBUTED BY HASH(id) BUCKETS 8,
    PARTITION p_new VALUES LESS THAN ("2025-01-01") DISTRIBUTED BY HASH(id) BUCKETS 32
)
```

### Tablet Size Inspection

```sql
-- View the table's Tablet distribution and sizes
SHOW TABLET FROM table_name;

-- View statistics
SHOW TABLE STATS table_name;

-- View partition information
SHOW PARTITIONS FROM table_name;
```
